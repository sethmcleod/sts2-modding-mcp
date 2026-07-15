# Timeline Epochs (custom-character metaprogression)

Give a custom character the base-game **Timeline** experience: 7 "chapters" (epochs) that
reveal one-by-one as the player hits milestones, each unlocking a slice of the character's
cards/relics/potions. Hand-rolled on base APIs + Harmony — no RitsuLib. Scaffold the whole
system with `generate_epoch_progression`; this guide explains how the pieces fit and the
pitfalls that will bite you if you don't.

Base-game namespaces you'll touch: `EpochModel`/`StoryModel`/`EpochEra`/`EpochSlotData` in
`MegaCrit.Sts2.Core.Timeline`; concrete base epochs in `…Timeline.Epochs`;
`SaveManager`/`EpochState`/`ProgressState`/`SerializableEpoch` in `…Saves`;
`ProgressSaveManager` in `…Saves.Managers`; `UnlockState` in `…Unlocks`;
`NTimelineScreen` in `…Nodes.Screens.Timeline`.

## The five building blocks

1. **Epoch classes.** One `EpochModel` subclass per chapter (`Id`, `Era`, `EraPosition`,
   `StoryId`, `GetTimelineExpansion()`, `QueueUnlocks()`). Chapter 1 is the "gateway": its
   `GetTimelineExpansion()` returns chapters 2-N (so revealing it opens their slots) and its
   `QueueUnlocks()` calls `QueueTimelineExpansion(...)`. Chapters 2-N each declare what they
   unlock. Loc lives in a `epochs` table: `{Id}.title/.description/.unlockInfo`, plus
   `.unlockText` only if you DON'T override `UnlockText` (gating chapters build it from their
   content via `CreateCardUnlockText`/`…Relic…`/`…Potion…`). Story name key
   `STORY_{STORYID_UPPER}`.

2. **Registration (reflection).** The base epoch registry is a source-generated static, so a
   mod injects into private statics: add your types to `EpochModel._epochTypeDictionary`,
   `_typeToIdDictionary`, `_allEpochs`, then null out the `_allEpochIds` cache (its getter
   rebuilds from `_allEpochs` — no AllEpochIds patch needed), and add your story to
   `StoryModel._storyTypeDictionary`. Cache the `FieldInfo`s and **throw loudly** if one is
   missing so a game update fails fast instead of silently disabling epochs. Guard so it runs
   once. Call from your mod's `Initialize` in a try/catch (a break disables only epochs).

3. **Content gating** — see the big pitfall below. Override your character's **pools**.

4. **Award patches** — Harmony postfixes that grant epochs on milestones.

5. **Config toggle** — enable/disable the whole system.

## The reveal state machine (memorize this)

`EpochState` order: `None < NoSlot < NotObtained < ObtainedNoSlot < Obtained < Revealed`.
`NTimelineScreen.InitScreen` (the full rebuild, run on every open) draws a slot for **every
state except `ObtainedNoSlot`**. So:

| State | On the Timeline | Meaning |
|---|---|---|
| absent (no entry) | not shown | never earned/slotted |
| `NotObtained` | visible, **locked** | slot exists, not earned |
| `ObtainedNoSlot` | **hidden** | earned but not yet placed on the timeline |
| `Obtained` | visible, click-to-reveal | earned, awaiting the reveal click |
| `Revealed` | visible, complete | revealed; **content unlocks here** |

`ProgressState.FixMissingSlots` (runs on save load) creates `NotObtained` slots for a
Revealed epoch's `GetTimelineExpansion()` children, and promotes `ObtainedNoSlot`→`Obtained`.
Useful helpers on `SaveManager`/`ProgressState`: `ObtainEpochOverride(id, state)`,
`UnlockSlot(id)`, `RevealEpoch(id)`, `IsEpochRevealed(id)`, `HasEpoch(id)`.

## Awarding epochs on milestones

BaseLib PREFIXES the vanilla epoch-bookkeeping methods on `ProgressSaveManager`
(`ObtainCharUnlockEpoch`, `CheckFifteenElitesDefeatedEpoch`, `CheckFifteenBossesDefeatedEpoch`)
with `return !(Character is ICustomModel)` — their hardcoded per-character switch would throw
for your character. So the vanilla body is skipped, but **Harmony still runs your POSTFIXES**.
Award from postfixes (guarded on `player.Character is YourCharacter`) by invoking the reflected
private `TryObtainEpochMidRun(EpochModel, Player)` / `TryObtainEpochPostRun(EpochModel,
SerializablePlayer, SerializableRun)`. Typical mapping (mirrors base characters):

- Ch2/3/4 ← `ObtainCharUnlockEpoch(player, act)` act 0/1/2 (clear Act 1/2/3)
- Ch5 ← `CheckFifteenElitesDefeatedEpoch` (15 elites), Ch6 ← `CheckFifteenBossesDefeatedEpoch`
- Ch7 ← `CheckAscensionOneCompleted` (Ascension 1; not BaseLib-skipped — vanilla body no-ops
  for your char)
- Ch1 ← `PostRunUnlockCharacterEpochCheck` (finish any run). Attach Ch1's slot with a postfix
  on `NeowEpoch.GetTimelineExpansion` that appends it, so the gateway appears early as a
  locked slot.

## Pitfalls (every one of these cost real debugging)

1. **The real content gate is the POOLS, not the "unlock epoch id" methods.** Postfixing
   `SaveManager.GetCard/Relic/PotionUnlockEpochIds` only feeds the *unlock-count statistic*
   (`GetTotalUnlockedCards = revealed × 3`). Actual run availability comes from
   `UnlockState(ProgressState)` = epochs with `State == Revealed`, consumed by the pools'
   `GetUnlockedCards`/`GetUnlockedRelics`/`GetUnlockedPotions`. **Base pools default to
   ungated**, so you MUST override them on your character's pools. For cards, override the
   protected virtual `CardPoolModel.FilterThroughEpochs(UnlockState, cards)`; for relics/potions
   override `GetUnlockedRelics`/`GetUnlockedPotions`. Keep an item unless it's gated and its
   epoch isn't revealed. (Your custom character is always in `UnlockState.Characters`, so its
   pool is otherwise always available — nothing is gated until you add these overrides.)

2. **`UnlockState.IsEpochRevealed<T>()` works for your registered custom epochs.** Build a
   content-id → `us => us.IsEpochRevealed<YourChapterNEpoch>()` map with one compile-time-generic
   lambda per gating chapter (no reflection). Sourced from each epoch's content lists so there's
   a single source of truth.

3. **Never force-reveal every epoch up front.** It's tempting to `ObtainEpochOverride(id,
   Revealed)` for all chapters on a fresh save "so nothing is locked." Don't: it bypasses the
   progression AND causes a **duplicate-tile bug**. `NTimelineScreen.AddEpochSlots` has **no
   dedup** — any epoch already drawn by `InitScreen` gets a SECOND tile when the gateway's
   `QueueTimelineExpansion(children)` runs on reveal. Leave children hidden
   (`ObtainedNoSlot`/absent) until their parent is revealed. Back-out-and-return "fixes" the
   duplicate (a full `InitScreen` rebuild) — that self-heal is the tell.

4. **Config-toggle "hide" = a PREFIX on `AddEpochSlots`.** To hide your epochs when the feature
   is disabled, Harmony-PREFIX `NTimelineScreen.AddEpochSlots(List<EpochSlotData> slotsToAdd)`
   and `slotsToAdd.RemoveAll(s => s.Model is YourEpochBase)`. Both the full rebuild and the
   reveal animation funnel through it. It's display-only and never touches saved state, so
   re-enabling restores prior progress exactly. (The prefix runs before the async body reads the
   list, so mutating the list works.)

5. **`EpochState` render semantics** (the table above): `ObtainedNoSlot` is the only "hidden"
   state, so it's what you want for earned-but-not-yet-revealed children, and for a clean reset
   you REMOVE entries (setting `NotObtained` would show 2-N as locked slots up front).

6. **Dynamic slot placement.** Hardcoding `Era`/`EraPosition` collides with base-game and other
   mods' epoch cells (a collision makes your cell render *their* epoch). Assign cells lazily:
   on first access (all mods have registered by then), scan every OTHER registered epoch's
   `(Era, EraPosition)` and hand each of yours a free cell (skip your own types to avoid
   recursion); cache for the session. Slots persist by Id, so cross-mod shifts are cosmetic.

7. **Register loud.** Cache the reflected `FieldInfo`s and throw a clear exception if a name is
   gone — a silent no-op leaves you debugging "why don't my epochs show" after a game patch.

8. **Milestone earn ≠ content unlock.** Earning sets `Obtained`; content needs `Revealed`,
   which happens when the player clicks through the reveal screen (matching base). Don't gate
   content on `IsEpochObtained`.

## Testing the progression

The MCPTest bridge exposes two generic RPCs for driving/asserting epoch state headlessly
(`test_mod/Code/BridgeHandler.cs`):

- `set_epoch {id, state}` — set one epoch's state by full model id (an `EpochState` name, or
  `"remove"`); on `"Revealed"` it also `UnlockSlot`s the epoch's expansion children, mirroring
  the in-game reveal.
- `get_epoch_state {prefix}` — per-epoch `state`/`visible`/`revealed`, and per card/relic/potion
  `unlocked` (passes the pools' `GetUnlocked*` gating for current progress) / `discovered` (seen
  in the compendium). This lets a test tell **locked** vs **unlocked-but-unseen** vs **seen**
  apart — the three distinct compendium treatments.

The test runner (`run_suite.py`) adds an `epoch_state` expect + drives reveals via the generic
`{bridge: "set_epoch", params: {...}}` do-action. A full regression walks fresh → reveal Ch1 →
reveal each of 2-N, asserting each chapter's content flips locked→unlocked while the rest stay
gated. Note: content ids carry a type prefix (`CARD.…`, `RELIC.…`, `POTION.…`) while epoch ids
are bare. See `get_modding_guide` topic `testing`.

## Scaffold it

`generate_epoch_progression` emits all of the above — epoch base + chapter classes,
registration, the gating helper, the award/gating/portrait/Neow/hide patches, the config
toggle, the three pool-override snippets, and localization — parameterized by your mod
namespace, character, and pools, with `// TODO`s where you fill in each chapter's content and
milestone criteria. Related: `get_modding_guide` topics `mod_config_integration`,
`reflection_patterns`, `advanced_harmony`, `pools`.

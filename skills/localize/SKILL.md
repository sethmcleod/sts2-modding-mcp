---
name: localize
description: Propagate changes in an STS2 mod's English localization to the other 15 locales. Use after any edit to eng/ card, power, relic, potion, keyword, or hover-tip text, or when the user asks to "update the other languages".
---

# Reflect English localization changes across all locales

English is the source of truth. The user edits `<Mod>/localization/eng/` (directly or
through the card skill); this skill mirrors those edits into the other 15 locale
directories: deu, esp, fra, ind, ita, jpn, kor, pol, ptb, rus, spa, tha, tur, zhs, zht.
Never edit `eng/` yourself. If English itself looks inconsistent (for example a card was
reworded but its `_POWER` twin was not), report it and wait; do not repair it silently.

## 1. Find the exact delta

Diff the English files against the last state the locales mirror. Usually that is
`git diff -- <Mod>/localization/eng/`; if English was committed since the last sync,
diff against the commit of the last sync instead. Classify every change:

- **Pure rename** (new key, identical description): carry the old translation verbatim,
  author only a new title.
- **Number-only change**: swap the number in place. Replace the LAST `]N[` occurrence
  when the string holds more than one number.
- **New or reworded text**: compose from donors (step 3).
- **Removed keys**: delete from every locale.

## 2. Set up the reference material

You need an extracted copy of the base game's `res://localization/` and the per-language
glossaries.

The dump is the GDRE recovery at `~/code/sts2-modding-mcp/recovered/localization`, rebuilt
by the `recover_game_project` MCP tool. Use that path, not a scratchpad copy: a scratchpad
dump is reaped by tmp cleanup mid-session, and a hand-copied one goes stale silently.

**Verify before every use: 16 language directories, each holding about 46 json files, and
15 `glossary_*.json` files.** Short counts make the collision and terminology checks pass
vacuously, which has hidden real errors before. A dump missing a language is the specific
trap: a stale copy once held only 14, silently dropping `ind` and `zht`, so those two got
no base-game donors at all. Rebuild the dump with `recover_game_project` and the glossaries
with `scripts/loc_glossary.py --base <dump> --out <dir>` whenever a count is short.

Not every locale has base-game donors for a given clause, but all 16 ship with the game, so
a missing one always means a broken dump rather than a language the game does not support.

## 3. Compose from donors, never translate fresh

The central rule: when the same clause already exists in a locale, reuse it exactly.
Sources, in order of preference:

1. **The base game's own translation** of the same clause. Grep the English dump for the
   phrase ("equal to damage dealt", "played an extra time", "discard any number"), then
   read the same key in each target language. Real donors used before: Fisticuffs,
   Piercing Wail, The Hunt, Duplicator, Gambler's Brew, Nightmare, Ashen Strike, Expose,
   Steady, Blood Vial, Anodyne.
2. **The mod's own strings** in that locale: a reworded card usually shares clauses with
   its neighbors (the Ferment scaffold, "gain N Antitoxin", a Siphon clause reused by a
   relic).

Only author genuinely new phrasing when no donor exists, and keep it in the locale's
established register (esp uses "Infliges/Obtienes", spa "Inflige/Gana", and so on; read
neighboring strings first).

## 4. Title rules

- Check every new title against the base game AND the mod in that locale. A collision
  with either is a bug even when English has none.
- No two mod entries in one locale may share a title, potions and hover tips included.
- A rename that changes the concept needs new titles even though the text is unchanged:
  a "Reduction" card renamed "Water Down" cannot keep cooking-reduction titles, because
  concentrating is the opposite of diluting.
- Prefer a culturally native term over a literal translation when one lands (ja picked
  the royal poison-taster for "Taste Test"). Never reuse a word another mod entry
  already owns in that language.

## 5. Format invariants the checkers enforce

- SmartFormat placeholder names must match English per string. When either side has a
  `{X:plural:...}` block, only the SET of names must match, so a locale may hoist or
  repeat a placeholder. Russian uses `plural(ru)` with three branches; ind, tha, jpn,
  kor, zhs, zht do not pluralize and may drop the block.
- BBCode tags (`[gold]`, `[blue]`, `[green]`, `[purple]`, `[red]`) must match as a
  multiset per string, order free.
- `_POWER.description` omits the count (numberless); `_POWER.smartDescription` carries
  `[blue]{Amount}[/blue]`. This is a base-game convention.
- Gold-wrapped game terms must use the base game's own word; the glossary check
  enforces stems. Do not fight a glossary false positive by rewording a correct
  translation: verify against the base dump first, and if the glossary entry is wrong,
  fix `scripts/loc_glossary.py` (ALIASES / AMBIGUOUS / OVERRIDES) instead.
- zht spaces around Latin digits and placeholders; zhs and jpn do not.
- Write files sorted by key, `indent=2`, `ensure_ascii=False`, trailing newline.

## 6. Verify, all of it, every time

Run from the mod repo root:

```bash
python3 scripts/check_localization.py --glossary <glossary-dir>
python3 scripts/check_name_collisions.py --base <dump>/localization
./scripts/dev.sh lint
```

Plus two checks the scripts do not cover: no duplicate titles within any locale
(compare `.title` values across cards, powers, relics, potions, and hover tips), and no
locale string left as a byte-identical copy of the English for newly authored keys.
Known noise: `check_mod_terms.py` flags word-order reorderings in zhs/zht/jpn/kor as
inconsistent terms; verify the flagged string contains both terms correctly and move on.

## 7. Finish

Report what changed and which donors carried the new strings. Do not run a publish; the
game may be running, and the user publishes.

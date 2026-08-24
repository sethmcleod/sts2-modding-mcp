---
name: changelog
description: Write or edit a CHANGELOG.md entry for an STS2 mod. Use for any player-visible change that needs an entry, for curating the Unreleased section before a release, and for rewriting entries into the official patch-note voice.
---

# Write a changelog entry

Every change a player can see needs one line in `CHANGELOG.md` under `## [Unreleased]`.
That includes content, balance, bug fixes, text and art. The `## [Unreleased]` section
you curate becomes the release note and the Steam Workshop update note, so it sits next
to real Mega Crit patch notes and must read like them.

## The voice overrides the repo's general prose rules

The repo's writing rules (simplified technical English, no contractions, one instruction
per sentence) do **not** apply to `CHANGELOG.md`. This file matches the official Slay the
Spire 2 patch notes instead. The house ban on em dashes still holds.

The best source for the current voice ships inside the game:
`res://localization/eng/patch_notes/<date>.md`. Extract it with `extract_game_assets`.
Those files are verbatim and always current. Read one before a large release.

## Draft from the commits, then rewrite for players

```sh
scripts/dev.sh changelog    # prints a draft from the commits after the last tag
```

The command writes no files. It groups the commits into Added, Fixed, Changed and Other.
Paste the lines that matter under `## [Unreleased]`, then rewrite each one in language a
player understands. `feat: rework infuse enchantments` becomes
`Reworked Infuse: enchantments now match the card type and stack.`

Delete the lines that only concern development: build, CI, test and most chores. **Say
which ones you dropped** rather than dropping them silently.

## Entry grammar

- **Start with a past-tense verb.** `Added`, `Removed`, `Renamed`, `Reworked`, `Buffed`,
  `Nerfed`, `Changed`, `Moved`, `Updated`, `Fixed`. A leading verb makes like changes
  group and scan.
- **Name the entity with its kind.** `Nerfed Meat Cleaver relic:`, `Buffed Demon Form card:`.
- **Use the arrow for every value change.** `damage increased from 28(36) -> 30(38)`,
  `rarity decreased from Rare -> Uncommon`. Stat arrows write `X(Y)` with no space.
  Quoted card text keeps the in-game spacing, `15 (20)`.
- **A rework quotes both full texts**, `"old text" -> "new text"`, in the exact wording
  the card shows in game. A cost move rides along as `Cost decreased from 1 -> 0`.
- **The verb follows the player's benefit, not the number.** A raised requirement is a
  nerf even though the number went up. The official notes do the same.
- **One line per change.** Use sub-bullets when one entity changed in several ways. Never
  append rationale, decision points, or before-and-after prose. The quoted new text is the
  description.
- **Do not state what did not change**, and do not restate what the name already implies.
  Write `Renamed Drain Dry to Draining Strike`, not a sentence explaining that the effect
  is the same.
- **Do not bold entity names.** The in-game notes wrap them in `[b]...[/b]`; a Keep a
  Changelog file does not.
- Bug fixes read `Fixed X`, `X now properly does Y`, or `X no longer does Y`.

## Two rules that decide whether an entry exists at all

**Only changelog a bug that actually shipped.** A bug introduced and fixed inside the same
unreleased cycle gets no entry, because no player ever saw it. Check the shipped version
before you write the line:

```sh
git cat-file -e "<last tag>:<path>"   # did the file exist at the tag?
git show "<last tag>:<path>"          # what did it do there?
```

**During a large pre-release cycle, consolidate card renames and reworks into one line.**
When the Changed section already carries a line such as "Added, removed, reworked and
renamed many cards", that line covers every card. Do not add per-card entries under it.
Relics, potions, keywords, mechanics, config and economy changes still get their own lines.

Cosmetic placeholder-art tweaks get no entry unless the change is sweeping or it changes
file sizes meaningfully.

## Late commits fold into the version they belong to

When commits land after a release was cut prematurely, their entries belong in that
version's section, not in a new `## [Unreleased]`.

A released section is the published Workshop note for that version. Do not change its
meaning after release. A stylistic touch-up is fine, and if the note is already posted,
update it there too.

The release mechanics themselves are in the repo's `RELEASING.md` and the **release** skill.

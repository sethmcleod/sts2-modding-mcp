# Dev workflow for a standard STS2 mod repo

This guide describes how to work in a mod repo that follows the standard layout (the
layout used by [sts2-mod-template](https://github.com/sethmcleod/sts2-mod-template)). The
repo's own docs are the primary record: start at its README.md, and read its
CONTRIBUTING.md for the conventions. This guide covers what is common to every repo built
on that layout.

For entity-specific guidance use the other guides (`cards`, `relics`, `events`, ...). For
live-game testing hazards see `testing` and `troubleshooting`. If the shared agent skills
are installed (`skills/install.sh` in this toolkit), prefer the **card**, **playtest**,
**getting-started**, and **run-history** skills over improvising a procedure.

## The standard layout

| Path | What it holds |
|---|---|
| `<Mod>Code/` | all C#; namespaces mirror folders |
| `<Mod>Code/MainFile.cs` | entry point; the `ModId` const is the single source of the mod id |
| `<Mod>/` | everything that ships in the `.pck`: images, scenes, `localization/eng/*.json` |
| `<Mod>.json` | the mod manifest the game reads (id, version, dependencies) |
| `cards.csv` | the plain-text design sheet, one row per card |
| `scripts/dev.sh` | the command hub (below) |
| `docs/` | worked examples, troubleshooting, backlog |

Model ids derive from the mod id: class `MyCard` in mod `MyMod` becomes `MYMOD-MY_CARD`.
BaseLib auto-discovers model subclasses from the assembly; `[Pool(...)]` attributes assign
pools. There is no per-entity registration list to maintain.

## Commands

```sh
scripts/dev.sh publish      # build → godot import → publish → verify pck  (asset/loc changes)
scripts/dev.sh publish-fast # code-only changes (skips godot import)
scripts/dev.sh lint         # offline three-way-sync check (no game needed)
scripts/dev.sh changelog    # draft CHANGELOG entries from commits since the last tag
scripts/dev.sh release <patch|minor|major|X.Y.Z>   # bump + roll changelog + package zip
scripts/dev.sh doctor       # ✓/✗ every prerequisite
```

`dotnet build` must pass with 0 errors. The localization analyzer runs as part of the
build. It makes sure that each power has the `.title`, `.description`, and
`.smartDescription` keys. A build alone does not validate the loc JSON against the code;
only `lint` and a publish do.

A working copy can carry a local, gitignored regression suite at `scripts/tests/`. Run
it with `python3 scripts/tests/run_suite.py [--group G] [name] [--fresh]`, and control
the game process with `--game start|stop|restart`. The suite needs this toolkit's bridge
mods installed, and it is never part of the mod repo itself.

## Rules that apply to every repo on this layout

- **Three-way update rule**: a card is in the code, the localization, and `cards.csv`. If
  you change one of the three, change all three. `scripts/dev.sh lint` checks it offline.
- **Every numeric value lives in a `(base, upgradeDelta)` builder pair** in the card
  constructor, never inline in `OnPlay`. The loc text uses `{Var:diff()}` tokens, never a
  literal number that a builder holds.
- **Description and tooltip code must not read `Owner` without an `IsMutable` guard.** A
  canonical model (in the compendium) throws. See the `troubleshooting` guide,
  "CanonicalModelException".
- **Keep mod assets under `res://<Mod>/`**, never at base-game `res://` paths. A path
  collision silently replaces the base-game asset for every mod in the session.
- **Publish first, then start or restart the game.** A publish over a live game breaks
  that session's asset loads (see `troubleshooting`).
- Each change a player can see gets a `CHANGELOG.md` entry under `## [Unreleased]`,
  written for players in the base game's patch-note voice.

## Live-game checks

The full hazard catalog is in the `testing` guide. The short list:

- Use a spare save profile (Profile 3 by convention), never a real one.
- Never abandon a run during a combat; use the `die` console command instead.
- Spawn custom entities with the full model id (`card MYMOD-MY_CARD`); a bare display
  name does nothing and reports no error. `dump` in the console lists model ids.
- Hot reload (tiers 2/3) works only from the main menu, before the first combat of the
  session.

## Optional local CLAUDE.md

Mod repos on this layout do not commit agent instructions. If you want a `CLAUDE.md` in
your working copy, copy `docs/mod-repo-CLAUDE.md.example` from this toolkit into the repo
root and keep it out of version control (`.claude/` and `CLAUDE.md` belong in your global
gitignore, or the repo's, if the repo does not already ignore them).

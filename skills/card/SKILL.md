---
name: card
description: Add a new card to an STS2 mod. Change the numbers, cost, text, or mechanics of an existing card. Use this skill when you create a card or when you edit a card. A card lives in three files that must stay in sync (the C# class, the localization JSON, and cards.csv). A change to one file without the other two files makes the mod go out of sync. This skill covers the full loop through lint, publish, and a regression scenario.
---

# Add or change a card

This skill applies to any STS2 mod repo that follows the standard layout: a `<Mod>Code/`
directory for C#, a `<Mod>/` directory for assets and localization, and a `cards.csv`
design sheet at the repo root. Find the mod's identity first:

- The mod id is the `ModId` const in `<Mod>Code/MainFile.cs`, and the `id` field of the
  `<Mod>.json` manifest at the repo root.
- The model-id prefix is the upper-case mod id plus a hyphen, for example `MYMOD-`.

Below, `<Mod>` means that mod name and `<MODID>-` means that prefix.

A card is defined in **three places that must stay in sync**. If you change one place,
change all three places:

1. **Code**. The card class is at `<Mod>Code/Cards/<Rarity>/<Name>.cs`. Every numeric
   value is a `(base, upgradeDelta)` builder pair.
2. **Localization**. The file `<Mod>/localization/eng/cards.json` holds the on-card text.
3. **cards.csv**. This is the plain-text design sheet. Its columns are
   `Card,Rarity,Type,Cost,Description`.

The command `scripts/dev.sh lint` runs offline and checks this three-way sync. Use it as
the fast check of your work. The repo's CONTRIBUTING.md gives the rules behind the
conventions, and its docs directory usually has a worked example.

## How to add a card

1. **Pick the display name first.** The class name gives all the other names
   automatically. For example, in a mod with id `MyMod`, the class name `DoubleDose`
   gives:
   - the model id `MYMOD-DOUBLE_DOSE`,
   - the portrait `double_dose.png`,
   - the loc keys `MYMOD-DOUBLE_DOSE.title` and `MYMOD-DOUBLE_DOSE.description`.

   Make the name correct before you write the files.
2. **Copy another card** from the same rarity folder. Use the copy as your start
   point. The `using` imports and the `namespace` line must agree with the folder. A copy
   makes them correct with no more work. Keep every number in the `With*` builders in the
   constructor, for example `WithDamage(3, 1)`. Do not write a number directly in
   `OnPlay`.
3. **Add the two loc keys** to `cards.json` in alphabetical order. Use `{Var:diff()}`
   tokens. The tokens let the game show the upgrade preview. Never write a number directly
   if a builder holds that number. Put keyword names and zone names in `[gold]…[/gold]`.
   Add a `\n` between sentences. Use the same words as the base game (the repo's
   CONTRIBUTING.md gives the card-text conventions).
4. **Add the cards.csv row.** Use the format `base (upgraded)`. Write plain text with no
   `[gold]` tags. Put the description in quotation marks if it contains a comma.
5. **Add the portrait.** Use a 1000×760 PNG at
   `<Mod>/images/card_portraits/big/<name>.png`. For an early version, copy any other
   portrait as a placeholder.

## How to change an existing card

Find the three files for the card. Change all three files together:
- the number or the text in the card class builders,
- the related keys in `cards.json`,
- the row in `cards.csv`.

If the change alters the behavior or the numbers, and the repo has a regression suite,
you must also change the **regression scenario** (see below). If you change a number but
you do not change the test, a regression can go into a release.

## How to rename a card

A rename touches more files than any other change. The class name gives the model id, the
loc keys, and the portrait filename, so all of them change together. Before you edit,
find every reference to the old name:

```sh
grep -rn "OldName" <Mod>Code <Mod>/localization cards.csv scripts/tests
```

Then change the class name and file name, the loc keys, the csv row, the portrait
filename, references from other cards, and any test scenario. Run the grep again after
the edit. Zero hits on the old name means the rename is complete.

## How to retire a card

Remove all of its pieces together: the class file, the loc keys, the csv row, the
portrait, and any test scenario. A leftover loc key or csv row fails the lint. A leftover
reference from another card fails the build.

## Verify

Run these commands in this order. Do not stop after a successful build. A build does not
check the loc file or the csv file. Only the pck and the lint check them.

```sh
scripts/dev.sh lint       # three-way sync + numeric cross-check, offline, fast
scripts/dev.sh publish    # build → import → publish → verify pck
```

Then check the card in the live game. Spawn the card from the dev console. Use the **full
model id**, not the display name. A bare name does nothing, and the console gives no error
message.

```
card MYMOD-DOUBLE_DOSE
```

The **playtest** skill drives the game safely. It covers the fresh process, the spare
save profile, and the return to the main menu. Use that skill. Do not make a new
procedure.

## Add a test

If the working copy has a local regression suite (a `scripts/tests/` directory), copy
the most similar scenario in `scripts/tests/cards/`. Change the copy to spawn the card,
to play the card, and to assert the outcome. A scenario is a small JSON file with `do`
and `expect` steps. The runner polls each `expect` step until it is true. The suite's
README gives the assertion vocabulary and the special behaviors of the bridge.

```sh
python3 scripts/tests/run_suite.py <name>   # run just your scenario while iterating
```

A new card or a changed card is complete only when these three conditions are true:
- The `lint` passes.
- The game shows the card correctly.
- A scenario covers the card (when the repo has a suite).

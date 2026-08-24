---
name: getting-started
description: Orient someone new to an STS2 mod repo: how to get set up, where things live, and how to make a first change. Use for a vague request such as "help me contribute" or "where do I start".
---

# Getting started with an STS2 mod repo

The repo's own documents are the record. Point at them, do not restate them: `README.md`
for the tour and the document map, `BUILD.md` for prerequisites and commands,
`CONTRIBUTING.md` for the rules a change must follow.

## First move

```sh
scripts/dev.sh doctor   # a checkmark or a cross for each prerequisite
```

Fix any cross before anything else. The output names the problem.

## The loop

```sh
scripts/dev.sh lint     # fast offline check, run after every edit
scripts/dev.sh publish  # build the mod and install it into the game
```

Then look at the change in the game. **Publish before you launch, never over a running
game.** The **playtest** skill carries that rule and the rest of the live-game hazards.

## The rule that prevents most mistakes

A card lives in three files: the C# class, the localization JSON, and `cards.csv`. Change
one, change all three. `scripts/dev.sh lint` checks it offline, `CONTRIBUTING.md` explains
why, and the **card** skill walks the procedure.

## Which skill next

**card** for a card change. **playtest** for anything that touches the running game.
**run-history** for balance work on finished runs. **changelog** for a `CHANGELOG.md`
entry. **release** for shipping.

## For someone new to code

Offer to explain, not just to do. Show the diff and say what each part does in a sentence
or two, then point at the matching section of `CONTRIBUTING.md` so they can read the rule
behind it. Small, complete, verified changes teach more than large ones.

## Framework knowledge lives in the guides

`get_modding_guide` carries 51 topics. Start with `getting_started`, then `dev_workflow`
for the loop and `project_structure` for the layout.

---
name: playtest
description: Run an STS2 mod against the live Slay the Spire 2 game safely. Use this skill to run a regression suite, to spawn a card and check it by hand, or to verify a change in a real run. Use it for any task that needs the live game. The game has three hazards that cost real time. A publish over a live process corrupts the asset loads of that process. A test on the wrong save profile changes real progress. If you abandon a run during a combat, every later combat fails to initialize until you restart the game. This skill gives the safe loop and the recovery steps.
---

# Playtest against the live game

The suite and the manual checks drive a **real live game** through the bridge (MCPTest on
:21337, GodotExplorer on :27020). The toolkit's `testing` and `troubleshooting` guides
document the mechanics and the failure modes (`get_modding_guide`). This skill is the
safe procedure. Follow it. Do not drive the game without it.

## Before you touch the game

- **Check the environment.** If the repo has a `scripts/dev.sh doctor` command, it prints
  a ✓ or a ✗ for each prerequisite. It checks the SDK, the installed mods, the bridge
  response, and the Steam process. Start here if something is not correct.
- **Every bridge-driven run needs a spare save profile, including a manual run.** The
  convention is **Profile 3**. A suite selects the profile itself, but `bridge_start_run`
  and console fixtures use the profile that is active in the game. Confirm the active
  profile before you start a run by hand. A test run on a real profile pollutes the Run
  History and the progression of that save.
- **Confirm that the save profile is a spare profile.** A suite starts runs and abandons
  runs many times. Settings tests can also lock and unlock content. Thus the suite must
  run on the spare profile, never Profile 1. If you point the suite at a real save, it
  changes the progression of that save.

## The most important rule, never publish over a live game

Godot keeps the `.pck` file of the mod open while the game runs. If you replace that file
under the live process, every later asset load from it fails. Combat then shows **no
background**. The game later throws `AssetLoadException` or `NullReferenceException`. No
file is corrupted, but the session is no longer usable.

Follow this order. **Publish first.** **Then start or restart the game.** Do not use the
opposite order. If you already published over a live game, restart the game. Also restart
the game if a run behaves in an unusual way.

## How to run a suite

When the working copy has a local regression suite (a `scripts/tests/` directory with a
`run_suite.py`), run it from the repo root:

```sh
python3 scripts/tests/run_suite.py                  # everything
python3 scripts/tests/run_suite.py --group cards    # one group while iterating
python3 scripts/tests/run_suite.py <name>           # scenarios whose filename contains <name>
python3 scripts/tests/run_suite.py --changed        # only the groups your uncommitted edits can affect
python3 scripts/tests/run_suite.py --fresh          # force a game restart first, when state is suspect
python3 scripts/tests/run_suite.py --game start|stop|restart   # game process control
```

The runner starts the game if the game is not up. The runner restarts the game if the game
becomes stuck. Thus you usually do not control the process yourself. Use `--fresh` when a
change that passed before starts to fail with no change in the code. The cause is almost
always old process state. This problem happens in practice.

## How to drive the game by hand

- Spawn custom entities with a **full model id**, for example `card MYMOD-MY_CARD`, not
  the display name. A bare name does nothing, but the console still reports success. To
  find a model id, use the console command `dump`, then read the game log.
- To end a combat, use `die`. **Never abandon a run during a combat.** If you abandon a
  run during a combat, every later combat in that process fails to initialize. Each later
  fight loads only in part until you restart the game. The suite obeys this rule. You must
  also obey it.
- The target index for the console `power` and `damage` commands has an offset of one from
  `play_card`. The value `0` is the player. The value `1` is the first enemy.
- **Hot reload** (tier 2 and tier 3) works only from the main menu, and only **before the
  first combat** in the session. After the first combat, `ModelIdSerializationCache`
  locks. Then you must restart the game.
- On macOS, a screen transition can stall while the game window does not have the focus.
  The reset procedure of the runner (`die` and ForceClick) does not need the focus.

## When you are done

Leave the game in the usual condition between sessions. That condition is **the main menu
at 100% game speed**. A suite runs at a higher speed. If you ran a suite, set the speed
back to 100%. If you raised the speed by hand, set it back to 100%.

Exit any live run correctly:
- Use Save and Quit.
- Then abandon the run from the main menu.
- Never abandon a live run directly, because the macOS death screen stalls.

The correct end state has three conditions. The game is at the main menu. The speed is
100%. No run is in progress.

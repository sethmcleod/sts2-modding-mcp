# Backlog

Improvements that are not scheduled. Each entry records its evidence, so a later reader
can check whether the problem still exists. No entry is a commitment.

## Bridge

### 1. The bridge cannot see enchantments

**Status:** ready
**Evidence:** there are zero `enchant` matches in `test_mod/Code/BridgeHandler.cs`. Hand
cards serialize `name`, `type`, `energy_cost` and `upgraded` only

The bridge shows no enchantment state. A test can assert an enchantment only by its
effect, and an assertion cannot read the power stacks of an enemy, so some enchantments
have no direct assertion at all. An addition of `enchantment` and `enchantment_amount` to
the hand-card payload closes this gap.

### 2. The test engine does not detect a stale game process after a publish

**Status:** idea
**Evidence:** a publish under a live game corrupts its asset loads (see the
`troubleshooting` guide); observed 2026-07-16 as a score of 22/42 on code that scored
42/42 before a republish

The game keeps the pck file open. If a publish replaces the pck while the game runs,
every later asset load from the pck throws, and the diagnosis takes a lot of time. The
suite can refuse to run when the pck on disk is newer than the game process start time,
or restart the game automatically in that case.

## Server tools

### 3. `list_game_audio` and `list_game_vfx` always return an empty result

**Status:** ready
**Evidence:** `_load_fmod_data()` at `sts2mcp/server.py` looks for `fmod_dump.json` in
two paths. It finds no file in either path, and it returns `{"events": []}` with no
message

Each query returns 0 results, but the tool reports "563 FMOD events across 12 banks".
`get_setup_status` reports the ready state, because it never checks this data. The repo
contains no `fmoddumper` mod.

Two workarounds are available now:

- `grep -rhoE '"event:/[^"]*"' decompiled` recovers 369 event paths.
- An extracted copy of the game (see `extract_game_assets`) has the actual banks under
  `banks/desktop/`. The string table uses prefix compression, so `strings` gives
  fragments of the paths, not the full paths.

There is a smaller related problem. `get_baselib_reference` shows an `fmod_audio` topic,
and `get_modding_guide` shows an `audio` topic. The server rejects both topics as
unknown.

## AutoSlay

### 4. AutoSlay plays no music at all, and it ignores `max_floor`

**Status:** idea; both problems are cosmetic
**Evidence:** measurement on 2026-07-16 during a run (floor 29, act 2):
`AudioManagerProxy.music_track`, `MusicControllerProxy._musicEv`, `._currentTrack` and
`._ambienceEv` were all null

`AutoSlayer` sets `NonInteractiveMode.AutoSlayerCheck = () => IsActive`. Every method on
`NRunMusicController` returns immediately when `NonInteractiveMode.IsActive` is true, and
`StopMusic` is one of these methods. Thus an AutoSlay run has no act music and no
ambience. This behavior is probably correct for a headless CI run, but balance batches
that a person watches need the music. A Harmony prefix can force `AutoSlayerCheck` to
false for the music controller only, which restores the music and keeps the suppression
of the SFX and the VFX.

There is a second problem. `bridge_autoslay_configure` reports `applied: {max_floor: 2}`,
but the next run logs `Config maxFloor = 49`. Thus the override does not reach
`AutoSlayConfig`, and a short test run is not possible.

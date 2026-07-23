# Audio Modding (FMOD)

## How STS2 Audio Works
STS2 uses **FMOD Studio** via the GodotFmod GDExtension (utopia-rise `fmod-gdextension`). All game audio — music, SFX, voice lines, ambience — lives in FMOD **banks** loaded at startup. Sounds are addressed by **event path** (e.g. `event:/sfx/heal`) or GUID. The game has 500+ events across its banks.

Three layers matter to modders:

1. **`NAudioManager`** (`MegaCrit.Sts2.Core.Nodes.Audio`) — the game's C# audio facade. Easiest and safest.
2. **`FmodServer`** — the GDExtension singleton (`Godot.Engine.GetSingleton("FmodServer")`). Full FMOD Studio API surface.
3. **FMOD Studio banks** — build your own `.bank` in FMOD Studio and load it at runtime for fully custom audio.

## Finding Event Paths
Use the `list_game_audio` MCP tool to search events, buses, banks, and global parameters:
```
list_game_audio(query="merchant")          # merchant voice lines
list_game_audio(query="music", category="all")
```
The index is dumped live from the running game's loaded banks (via the MCPTest bridge's `fmod_dump` method) and cached to `fmod_dump.json`. Each event entry includes its path, GUID, length in ms, streaming flag, and local parameters (name/min/max/default).

## Playing Existing Game Sounds

### Via NAudioManager (recommended)
```csharp
using MegaCrit.Sts2.Core.Nodes.Audio;

// One-shot SFX (volume 0..1)
NAudioManager.Instance?.PlayOneShot("event:/sfx/heal", 1f);

// One-shot with FMOD parameters
NAudioManager.Instance?.PlayOneShot("event:/sfx/attack",
    new Dictionary<string, float> { ["intensity"] = 0.8f }, 1f);

// Looping events (e.g. ambient monster sfx)
NAudioManager.Instance?.PlayLoop("event:/sfx/monster/hover", usesLoopParam: true);
NAudioManager.Instance?.StopLoop("event:/sfx/monster/hover");

// Set a parameter on a playing looped event
NAudioManager.Instance?.SetParam("event:/sfx/monster/hover", "speed", 2f);

// Music
NAudioManager.Instance?.PlayMusic("event:/music/act1");
NAudioManager.Instance?.UpdateMusicParameter("phase", "combat");
NAudioManager.Instance?.StopMusic();
```
Note: `NAudioManager` calls are no-ops when the game's TestMode is on.

### Via FmodServer directly
```csharp
using Godot;

var fmod = Engine.GetSingleton("FmodServer");
fmod.Call("play_one_shot", "event:/sfx/heal");
fmod.Call("play_one_shot_with_params", "event:/sfx/attack",
    new Godot.Collections.Dictionary { ["intensity"] = 0.8f });

// Controllable instance
var instance = fmod.Call("create_event_instance", "event:/music/act1").AsGodotObject();
instance.Call("start");
instance.Call("set_parameter_by_name", "phase", 1f, false);
instance.Call("stop", 0);   // 0 = allow fadeout, 1 = immediate
instance.Call("release");
```
Useful `FmodServer` methods (verified in the shipped extension): `play_one_shot`, `play_one_shot_with_params`, `play_one_shot_attached`, `create_event_instance`, `create_event_instance_with_guid`, `check_event_path`, `get_event`, `get_all_event_descriptions`, `get_all_banks`, `load_bank`, `wait_for_all_loads`, `load_file_as_sound`, `load_file_as_music`, `create_sound_instance`, `pause_all_events`, `mute_all_events`.

FmodServer calls must run on the **main thread** (dispatch via `CallDeferred` or a captured `SynchronizationContext` if you're on a worker thread).

## Custom Audio

### Option A: Custom FMOD bank (full-featured)
Build a bank in **FMOD Studio** (match the game's FMOD version — check `libfmodstudio` in the game install), copy it with your mod, and load it:
```csharp
var bank = fmod.Call("load_bank", "/absolute/path/to/MyMod.bank", 0); // 0 = LOAD_BANK_NORMAL
fmod.Call("wait_for_all_loads");
fmod.Call("play_one_shot", "event:/MyMod/my_sound");
```
Your events then work everywhere game events do, including parameters and buses.

### Option B: Raw audio files (experimental)
`FmodServer` can load raw files into FMOD's core system:
```csharp
fmod.Call("load_file_as_sound", "/path/to/sound.ogg");
var snd = fmod.Call("create_sound_instance", "/path/to/sound.ogg").AsGodotObject();
```
The bridge mod's `fmod_test` method (actions: `probe`, `play_existing`, `load_file`, `play_fmod_file`) exists specifically to experiment with this path — playback of raw files through the studio system has known rough edges. Prefer Option A for anything shipping.

## Replacing Existing Sounds
There is no supported bank-override mechanism. The practical approach is a Harmony patch redirecting the call site:
```csharp
[HarmonyPatch(typeof(NAudioManager), nameof(NAudioManager.PlayOneShot),
    new[] { typeof(string), typeof(float) })]
static class SfxRedirect
{
    static void Prefix(ref string path)
    {
        if (path == "event:/sfx/heal") path = "event:/MyMod/better_heal";
    }
}
```

## Volume / Buses
Master, SFX, BGM, and ambience volumes go through `NAudioManager.SetMasterVol` / `SetSfxVol` / `SetBgmVol` / `SetAmbienceVol` (note: the game squares the 0–1 slider value before applying). Buses (`bus:/`, `bus:/master`, ...) can be fetched with `fmod.Call("get_bus", "bus:/master/sfx")` and support volume/mute/pause.

## Debugging
- `fmod_test` bridge method, action `probe` — lists FmodServer's audio methods to confirm the extension API at runtime.
- `fmod_dump` bridge method — full dump of banks/events/buses/global parameters (this feeds `list_game_audio`).
- `check_event_path` returns whether an event path exists before you try to play it.

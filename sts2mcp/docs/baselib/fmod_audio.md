# BaseLib: FMOD Audio

BaseLib provides two audio systems:

1. **`BaseLib.Utils.FmodAudio`**: direct access to the game's FMOD engine (the `FmodServer` GDExtension singleton). Play the game's 563 FMOD events, load custom files/banks, replace game sounds, control buses and snapshots.
2. **`BaseLib.Audio.ModAudio`** (+ `AutoModAudio`, `ModSound`): Godot-native `AudioStreamPlayer` playback for audio files shipped in your mod's PCK (`res://` paths). Respects the player's volume settings automatically.

> **Stability note:** `FmodAudio` is marked `[Obsolete]` in BaseLib source: "not guaranteed to continue to exist in its current state, and is not recommended for use." It works today, but pin your BaseLib version or prefer `ModAudio` where possible.

> **Key constraint:** the FMOD GDExtension loads files via OS file access, so `FmodAudio.PlayFile`/`LoadBank` need **absolute disk paths**: audio packed inside a mod PCK (`res://`) is *not* reachable by FmodAudio. Use `ModAudio` for PCK audio, or ship loose files next to your DLL for FmodAudio.

## FmodAudio (BaseLib.Utils)

```csharp
using BaseLib.Utils;

// Existing game sound (fire-and-forget)
FmodAudio.PlayEvent("event:/sfx/heal");

// Custom file (absolute path; wav/ogg/mp3)
FmodAudio.PlayFile(Path.Combine(modDir, "sounds", "boom.wav"));

// Replace a game sound (no Harmony patch needed)
FmodAudio.RegisterFileReplacement("event:/sfx/ui/clicks/ui_click",
    Path.Combine(modDir, "sounds", "click.wav"));

// Custom FMOD Studio bank (built with FMOD Studio 2.03.x; strings bank first)
FmodAudio.LoadBank(Path.Combine(modDir, "banks", "MyMod.strings.bank"));
FmodAudio.LoadBank(Path.Combine(modDir, "banks", "MyMod.bank"));
FmodAudio.PlayEvent("event:/mods/mymod/my_sound");
```

All methods handle the `FmodServer` singleton lookup, caching, and error logging internally; failures return `false`/`null` and log via `BaseLibMain.Logger`.

### Event playback
- `PlayEvent(string eventPath) -> bool`: fire-and-forget one-shot
- `PlayEvent(string eventPath, Dictionary<string, float> parameters) -> bool`: with event parameters (e.g. `{ "EnemyImpact_Intensity", 2f }`)
- `PlayEvent(string eventPath, int cooldownMs) -> bool`: silently skips if the same event played within `cooldownMs` (good for on-every-card-play triggers)
- `PlayEventByGuid(string guid) -> bool`: play by GUID instead of path
- `CreateEventInstance(string eventPath) -> GodotObject?`: controllable instance; call `start`, `stop`, `set_volume`, `set_pitch`, `set_paused`, `set_parameter_by_name`, then `release` via `.Call(...)`
- `EventExists(string eventPath) -> bool`

```csharp
var loop = FmodAudio.CreateEventInstance("event:/sfx/ambience/act1_ambience");
loop?.Call("start");
// later:
loop?.Call("stop", 0);   // 0 = allow fadeout, 1 = immediate
loop?.Call("release");
```

### Custom file playback
- `PlayFile(string absolutePath, float volume = 1.0f, float pitch = 1.0f) -> GodotObject?`: loads into memory on first use, cached after. Returns the FmodSound handle (`play`, `stop`, `set_volume`, `set_pitch`, `set_paused`, `is_playing`, `release` via `.Call(...)`)
- `PlayFile(string absolutePath, int cooldownMs, float volume = 1.0f, float pitch = 1.0f) -> GodotObject?`
- `PlayMusic(string absolutePath, float volume = 1.0f, float pitch = 1.0f) -> GodotObject?`: streams from disk instead of loading into memory; use for tracks longer than ~10s
- `PreloadFile(string absolutePath) -> bool`: load without playing (avoid first-play hitch)
- `PreloadMusic(string absolutePath) -> bool`: prepare a streaming load
- `CreateSoundInstance(string absolutePath) -> GodotObject?`: raw FmodSound handle for manual control
- `UnloadFile(string absolutePath)`

### Banks
- `LoadBank(string bankPath) -> bool`: must be built with FMOD Studio **2.03.x**; load your `.strings.bank` before content banks
- `UnloadBank(string bankPath)`

### Sound replacement registry
Registers a single shared Harmony prefix on `NAudioManager.PlayOneShot(string, float)` so multiple mods can swap sounds without conflicting patches. Last registration wins per event path.

- `RegisterReplacement(string originalEvent, Func<string, float, bool> handler)`: handler receives `(eventPath, volume)`; return `true` to suppress the original, `false` to let it play
- `RegisterFileReplacement(string originalEvent, string replacementFilePath)`: event → custom file
- `RegisterEventReplacement(string originalEvent, string replacementEvent)`: event → other event
- `RemoveReplacement(string originalEvent)` / `ClearReplacements()`

```csharp
FmodAudio.RegisterReplacement("event:/sfx/block_gain", (path, volume) =>
{
    if (volume > 0.5f) { FmodAudio.PlayFile(bigBlockWav, volume); return true; }
    return false; // let the original play for small blocks
});
```

### Sound pools (random selection, no back-to-back repeats)
- `CreatePool(string poolName, params string[] soundPaths)`: entries may be `event:/...` paths or absolute file paths
- `AddToPool(string poolName, params string[] soundPaths)`
- `PlayPool(string poolName, float volume = 1.0f, float pitch = 1.0f) -> GodotObject?`: returns the FmodSound handle for file entries, `null` for events
- `PlayPool(string poolName, int cooldownMs, float volume = 1.0f, float pitch = 1.0f) -> GodotObject?`
- `RemovePool(string poolName)`

### Snapshots (global mixer effects)
- `StartSnapshot(string snapshotPath) -> GodotObject?`: e.g. `"snapshot:/pause"` (the game's pause ducking)
- `StopSnapshot(GodotObject? snapshot, bool allowFadeout = true)`

### Bus control
Common bus paths: `bus:/master`, `bus:/master/sfx`, `bus:/master/music`, `bus:/master/ambience`, `bus:/master/sfx/Reverb`, `bus:/master/sfx/chorus`.

- `GetBus(string busPath) -> GodotObject?`
- `SetBusVolume(string busPath, float volume)` / `GetBusVolume(string busPath) -> float`
- `SetBusMute(string busPath, bool muted)`
- `SetBusPaused(string busPath, bool paused)`
- `BusExists(string busPath) -> bool`

### Global parameters
The game drives adaptive music with global FMOD parameters (e.g. `Progress`, which has labels like `"Enemy"`, `"Merchant"`, `"Elite"`).

- `SetGlobalParameter(string name, float value)`
- `SetGlobalParameterByLabel(string name, string label)`
- `GetGlobalParameter(string name) -> float`

### Global mute/pause
- `MuteAll()` / `UnmuteAll()`
- `PauseAll()` / `UnpauseAll()`

### DSP & diagnostics
- `SetDspBufferSize(int bufferLength, int numBuffers)`: larger buffers reduce crackling, add latency (default ~1024 × 4)
- `GetDspBufferSettings() -> (int bufferLength, int numBuffers)`
- `GetPerformanceData() -> Variant`: CPU/memory/channel stats from FMOD

### Teardown
- `UnloadAll()`: unloads all files and banks loaded through the helper, clears replacements, cooldowns, and pools

## ModAudio (BaseLib.Audio)

Godot-native playback using pooled `AudioStreamPlayer` nodes. Works with `res://` paths from your mod's PCK, applies the player's Master/BGM/Ambience volume settings, and ties sounds to the right scene node (SFX to `NCombatRoom`, otherwise `NRun`, else the scene root).

```csharp
using BaseLib.Audio;

public enum ModAudio.SoundType { Sfx, Music, Ambience }
```

- `ModAudio.PlaySound(ModSound sound, float volumeAdd = 0f, float volumeMult = 1f, float pitchVariation = 0f, float basePitch = 1f, Node? targetNode = null) -> AudioStreamPlayer?`
  - `volumeAdd` is in dB; `pitchVariation` picks a random pitch centered on `basePitch`
  - Music/Ambience: only one active at a time, so playing a new track stops the old one; replaying the same file is a no-op
  - Sfx: pooled, capped by `BaseLibConfig.SfxPlayerLimit`
- `ModAudio.PlaySoundGlobal(ModSound sound, ...)`: attached to the scene root, survives leaving the run
- `ModAudio.PlaySoundInRun(ModSound sound, ...)`: attached to `NRun`, stops when the run scene exits
- `ModAudio.UpdateVolumes()`: re-apply settings volumes to active music/ambience players

### ModSound
```csharp
var sound = new ModSound("res://MyMod/audio/boop.ogg");                       // Sfx by default
var music = new ModSound("res://MyMod/audio/theme.ogg", ModAudio.SoundType.Music);

sound.Play(volumeAdd: -3f, pitchVariation: 0.1f);   // convenience wrapper for PlaySound

// Strings implicitly convert to ModSound (cached):
ModAudio.PlaySound("res://MyMod/audio/boop.ogg");
```
- `ModSound(string file, ModAudio.SoundType soundType = SoundType.Sfx)`
- `Play(float volumeAdd = 0f, float volumeMult = 1f, float pitchVariation = 0f, float basePitch = 1f) -> AudioStreamPlayer?`
- `GetOrLoadStream() -> AudioStream?`: streams under 15s are cached
- `static SetSoundDefaultVolumeOffset(string file, float offset)`: per-file default dB offset

### AutoModAudio
Folder-based helper so you can play files by short name:
```csharp
static readonly AutoModAudio Audio = new("res://MyMod/audio");

Audio.PlaySfx("boop.ogg");
Audio.PlayMusic("theme.ogg", volume: -3f);
Audio.PlayAmbience("wind.ogg");
```
- `AutoModAudio(string folder)`
- `PlaySfx(string path, float volume = 0f, float volumeMult = 1f, float pitchVariation = 0f, float basePitch = 1f) -> AudioStreamPlayer?`
- `PlayMusic(...)` / `PlayAmbience(...)`: same signature

## Which one should I use?

| Need | Use |
|------|-----|
| Play an existing game sound/event | `FmodAudio.PlayEvent` |
| Replace a game sound | `FmodAudio.RegisterFileReplacement` / `RegisterEventReplacement` |
| Play audio shipped in your PCK (`res://`) | `ModAudio` / `AutoModAudio` |
| Play loose files on disk through FMOD | `FmodAudio.PlayFile` / `PlayMusic` |
| Full FMOD features (layering, adaptive music, bus routing) | `FmodAudio.LoadBank` with a custom FMOD Studio 2.03.x bank |
| Mess with the game's mixer (buses, snapshots, global params) | `FmodAudio` bus/snapshot/parameter methods |

See the `audio` modding guide (`get_modding_guide` topic `audio`) for a full walkthrough including finding event paths with `list_game_audio` and building custom banks.

# Hot Reload

Hot reload lets you iterate on a mod without restarting the game. The MCP builds
your project, deploys the DLL (and PCK if the project has one) to the game's mods
folder, then tells the in-game MCPTest bridge to load the new assembly, re-apply
Harmony patches, re-register entities in ModelDb, reload localization, and remount
resources, all while the game keeps running. A typical code change is visible
in the current combat within seconds.

```
hot_reload_project (Python)                MCPTest mod (C# inside game)
  build_and_deploy_project()  ──deploy──>  <game_dir>/mods/<MyMod>/
  bridge_client.hot_reload()  ──TCP 21337──> BridgeHandler.HotReload()
```

## The Three Tiers

The bridge implements three reload tiers. Higher tiers are supersets of lower ones.

| Tier | What it does | When to use |
|------|--------------|-------------|
| 1 | Harmony patches only | Changed only patch code (`Patches/` folder or `*Patch*.cs` files) |
| 2 (default) | Tier 1 + entity models re-registered in ModelDb + pool refresh + localization reload + live instance refresh | Changed cards/relics/powers/potions/monsters or other `AbstractModel` subclasses |
| 3 | Tier 2 + PCK resource remount (`ProjectSettings.LoadResourcePack`) | Changed images, audio, scenes, shaders, or other packed resources |

Tier details:

- **Tier 1** loads the new assembly into a *collectible* `AssemblyLoadContext`, applies
  its `[HarmonyPatch]` attributes under a fresh Harmony ID, then unpatches the previous
  hot-reload Harmony instance and unloads the old ALC. Because the ALC is collectible,
  repeated tier 1 reloads do not accumulate memory. Type identity does not matter for
  patch-only reloads, which is what makes the collectible ALC safe here.
- **Tier 2** loads into the *default* ALC instead, so cross-ALC type identity breaks
  `ModelDb` injection, entity cloning, and runtime casts. The build step stamps a unique
  assembly name (e.g. `MyMod_hr14523045`) so the default ALC accepts the new version
  alongside old ones. It then updates `Mod.assembly` references in `ModManager`,
  invalidates the `ReflectionHelper._modTypes` cache, registers new entity IDs in the
  network `ModelIdSerializationCache`, transactionally replaces the mod's
  `AbstractModel` entries in `ModelDb._contentById` (with rollback on failure),
  clears ModelDb cached enumerables, unfreezes and re-registers pools, reloads
  localization, verifies every injected entity is resolvable (including a
  `ToMutable()` sanity check on cards to catch `PowerVar<T>` failures early),
  and refreshes live `NCard`/`NRelic`/`NPower` instances in the scene tree plus
  mutable card/relic instances in the current run.
- **Tier 3** additionally remounts the deployed `.pck` via
  `ProjectSettings.LoadResourcePack()` and re-triggers the localization reload so
  PCK-shipped loc files take effect. Requesting tier 3 without a `pck_path` completes
  as tier 2 with a warning.

### Automatic tier detection

`hot_reload_project` (and the `watch_project` file watcher) picks the tier from the
changed file set when you don't pass one explicitly:

- `.cs` files only under `Patches/` or named `*Patch*` → tier 1
- Other `.cs` files → tier 2
- Localization JSON (path contains `localization`) → tier 2, or tier 3 when the
  project ships a PCK (PCK-backed loc requires a remount)
- Any resource file (`.png`, `.jpg`, `.webp`, `.wav`, `.ogg`, `.mp3`, `.tscn`,
  `.tres`, `.gd`, `.gdc`, `.shader`, `.res`, `.scn`, or data JSON) → tier 3
- `mod_manifest.json`, `mod_config.json`, and `launchSettings.json` are ignored

When no changed-file list is available, the default is tier 3 for PCK projects and
tier 2 otherwise. Tier values are clamped to 1–3.

## MCP Tools

### hot_reload_project (preferred)

Build + deploy + hot reload in one project-aware step. Finds the deployed DLL and
PCK automatically and stamps the assembly version so the default ALC accepts it.

```
hot_reload_project with:
  project_dir: "path/to/MyMod"
  mods_dir: "<game_dir>/mods"
  # optional:
  tier: 2                  # override auto-detection
  configuration: "Debug"
  mod_name: "MyMod"        # install name override
  build_pck_first: true    # force/skip PCK rebuild
  auto_detect_pools: true  # default; bridge discovers [Pool(typeof(...))] via reflection
  pool_registrations: [{"pool_type": "SharedRelicPool", "model_type": "MyRelic"}]
```

Pool discovery has three modes:

- `pool_registrations` provided → used as-is (explicit)
- omitted with `auto_detect_pools: true` (default) → the C# bridge reflects over the
  compiled assembly for `[Pool(typeof(...))]` attributes, so it is 100% accurate
- omitted with `auto_detect_pools: false` → an explicit empty list is sent, disabling
  bridge-side auto-discovery

The result merges the build/deploy output with a `hot_reload` key (the bridge's full
result, below) and `hot_reload_inputs` (the exact `dll_path`, `pck_path`, `tier`, and
pool registrations that were sent). `success` is true only when both the build and
the in-game reload succeeded.

For continuous reload-on-save, use `watch_project` instead. It watches the project
tree, debounces 1.5s, auto-detects the tier from what changed, and only rebuilds the
PCK when resource files actually changed.

### bridge_hot_reload (low-level)

Talks directly to the bridge with explicit paths. Use when you built/deployed
yourself and just want the in-game reload step.

```
bridge_hot_reload with:
  dll_path: "<game_dir>/mods/MyMod/MyMod_hr14523045.dll"   # required
  tier: 2                                                   # 1 | 2 | 3, default 2
  pck_path: "<game_dir>/mods/MyMod/MyMod.pck"               # tier 3 only
  pool_registrations: [...]                                 # omit for auto-discovery
```

The Python client retries up to 3 times with backoff (1s, 2s) on transient errors:
"already in progress", "bridge not running", "bridge timed out".

### bridge_hot_reload_progress

Reloads run on the game's main thread and can take a few seconds. Poll this from a
second connection to see where a long reload is:

```json
{"step": "reloading_entities", "in_progress": true, "mod_key": "MyMod"}
```

Step names, in order: `starting`, `loading_assembly`, `patching_harmony`,
`updating_mod_reference`, `invalidating_reflection_cache`, `registering_entity_ids`,
`reloading_entities`, `clearing_modeldb_caches`, `refreshing_pools`,
`reloading_localization`, `remounting_pck`, `verifying_entities`,
`refreshing_live_instances`. When idle, `step` is empty and `in_progress` is false.

### Related tools

- `bridge_reload_history`: the last reload results with timings, entity counts,
  errors, and warnings. First stop when debugging a failed reload.
- `bridge_refresh_live_instances`: standalone scene-tree refresh (runs automatically
  during tier 2+ reloads).
- `bridge_reload_localization`: reload loc tables only, no rebuild.
- `bridge_hot_swap_patches`: legacy patches-only swap; tier 1 supersedes it.

## Raw JSON-RPC Protocol (non-MCP usage)

Any tool or editor plugin can drive hot reload directly, because the bridge speaks
newline-delimited JSON-RPC over TCP on `127.0.0.1:21337`. Send one JSON object
terminated by `\n`, read one JSON line back.

### `hot_reload`

Request:

```json
{"method": "hot_reload", "id": 1, "params": {
  "dll_path": "E:/SteamLibrary/steamapps/common/Slay the Spire 2/mods/MyMod/MyMod_hr14523045.dll",
  "tier": 3,
  "pck_path": "E:/SteamLibrary/steamapps/common/Slay the Spire 2/mods/MyMod/MyMod.pck",
  "pool_registrations": [{"pool_type": "SharedRelicPool", "model_type": "MyRelic"}]
}}
```

- `dll_path` (string, required): absolute path to the built DLL, must exist on disk
- `tier` (int, optional, default 2, clamped 1–3)
- `pck_path` (string, optional): only used when tier ≥ 3
- `pool_registrations` (array, optional): omit entirely for reflection-based
  auto-discovery; send `[]` to disable pool registration

Response (`result` fields):

```json
{"id": 1, "result": {
  "success": true,
  "tier": 3,
  "assembly_name": "MyMod_hr14523045, Version=1.0.0.0, ...",
  "patch_count": 4,
  "entities_removed": 3,
  "entities_injected": 2,
  "pools_unfrozen": 1,
  "pool_registrations_applied": 1,
  "localization_reloaded": true,
  "pck_reloaded": true,
  "live_instances_refreshed": 5,
  "mutable_check_passed": 2,
  "mutable_check_failed": 0,
  "alc_collectible": false,
  "total_ms": 2140,
  "step_timings": {"step1_assembly_load": 310, "step2_harmony_patch": 95, "...": 0},
  "timestamp": "2026-07-23T12:00:00.0000000Z",
  "changed_entities": [
    {"name": "MyCard", "action": "injected", "id": "cards/my_card"},
    {"name": "MyOldCard", "action": "removed"},
    {"name": "MyRelic", "action": "unchanged"}
  ],
  "actions": ["assembly_loaded", "harmony_staged", "entities_reregistered", "..."],
  "errors": [],
  "warnings": []
}}
```

`success` is `errors.Count == 0`. Entities whose type signature hash is unchanged
are kept as-is and reported with `action: "unchanged"` instead of being
re-instantiated. If a reload is already running, the response is
`{"error": "Hot reload already in progress. ..."}`: reloads are serialized by a lock.

### `hot_reload_progress`

```json
{"method": "hot_reload_progress", "id": 2}
```

```json
{"id": 2, "result": {"step": "patching_harmony", "in_progress": true, "mod_key": "MyMod"}}
```

Note: `hot_reload` itself blocks its TCP connection until done, so poll progress
from a separate connection. Use a generous client timeout (the Python client uses
30s for `hot_reload`).

Other related methods on the same port: `reload_history`, `refresh_live_instances`,
`reload_localization`, `hot_swap_patches` (takes `{"dll_path": ...}`).

## How Re-registration Works

For tier 2+, the bridge treats the reload as a transaction:

1. **Snapshot**: every `AbstractModel` entry belonging to the mod (matched by
   normalized assembly name, ignoring the `_hr######` version-stamp suffix) is
   snapshotted from `ModelDb._contentById`, along with the serialization cache.
2. **Stage**: new instances are constructed from the new assembly's model types,
   sorted so dependencies inject first (Powers before Cards, Monsters before
   Encounters). Types whose signature hash matches the old version are skipped and
   the existing instance is kept.
3. **Commit**: old entries are removed and staged entries inserted. If any staging
   step failed, nothing is committed and the snapshot is restored (entities, mod
   assembly references, reflection cache, serialization cache), and any staged
   Harmony patches and collectible ALC are cleaned up.
4. **Verify**: each injected type is checked against `ModelDb.Contains`, and
   injected cards get a `ToMutable()` smoke test.

## How Harmony Re-patching Works

Each mod gets its own hot-reload session keyed by normalized assembly name. On each
reload the bridge:

1. Creates a fresh Harmony instance with a unique ID
   (`com.mcptest.hotreload.<modKey>.<ticks>`) and runs `PatchAll` on the new assembly.
   This is separate from MCPTest's own Harmony instance, so bridge functionality is
   never disturbed.
2. On success, unpatches the *previous* hot-reload Harmony instance for this mod.
3. Sweeps `Harmony.GetAllPatchedMethods()` and removes any remaining patches whose
   declaring assembly is an old version of this mod (stale patches from the original
   mod load or earlier reloads). Other mods' patches are untouched.

If patching the new assembly throws, the staged instance is unpatched and the old
patches stay active.

## Known Limitations

- **Dependency DLLs are not hot-reloaded.** Shared libraries next to your mod DLL
  (e.g. BaseLib) are loaded into the default ALC once. If the on-disk version later
  differs from the loaded one, the reload reports a `dep_stale_*` warning. A game
  restart is required for dependency changes. (`GodotSharp`, `0Harmony`, and `sts2`
  are never touched.)
- **Memory accumulates at tier 2+.** Default-ALC assemblies can't be unloaded, so
  each reload adds a version-stamped assembly. Fine for an iteration session;
  restart the game occasionally during very long sessions.
- **Type identity changes across reloads.** Code holding `typeof(MyCard)` references
  from an *old* assembly won't equal the new type. The bridge compensates inside
  ModelDb/pools, but exotic reflection in your own mod may need care.
- **Struct/field layout of live run state is not migrated.** Live and run instances
  are refreshed to fresh ModelDb models, but deeply customized saved state may not
  reflect signature changes until a new run/encounter.
- **One reload at a time.** Concurrent requests get "Hot reload already in progress"
  (the MCP client auto-retries).
- **PCK remount is additive.** Godot mounts the new PCK over the old one; removed
  resource files may still resolve until restart.
- **Localization in PCKs needs tier 3.** Loose-file loc JSON reloads at tier 2;
  PCK-shipped loc requires the remount.

## Troubleshooting

- **`"Bridge not running"`**: the game isn't running or MCPTest isn't loaded. See
  the `bridge_setup` guide. The bridge only starts once the game reaches the main menu.
- **`dll_not_found`**: the `dll_path` doesn't exist. With `hot_reload_project` this
  usually means the deploy step failed; check the build output in the result.
- **`inject_<Type>: ...` errors**: an entity constructor threw. The whole entity
  commit is rolled back; the game keeps the previous versions. Check
  `bridge_reload_history` and `bridge_get_game_log` for the exception.
- **`ToMutable_<Card>` warnings**: the card injected but can't materialize, usually
  a `PowerVar<T>` referencing a power that wasn't reloaded or registered. Reload at
  tier 2 with the power's file included, or check injection order.
- **Entities reload but don't appear in pools**: pool registration didn't happen.
  Verify `[Pool(typeof(...))]` attributes exist (auto-discovery reads the compiled
  assembly), or pass `pool_registrations` explicitly.
- **New art/audio not showing**: you reloaded at tier 2; resource changes need
  tier 3 (and a PCK rebuild, which `hot_reload_project` handles when it detects
  resource changes).
- **`dep_stale_*` warning**: a shared dependency DLL changed on disk; restart the
  game to pick it up.
- **Reload seems hung**: poll `bridge_hot_reload_progress`; assembly load and PCK
  remount can take a few seconds on large mods. The Python client times out at 30s
  and retries transient failures automatically.
- **Everything else**: `bridge_reload_history` keeps per-step timings, actions,
  errors, and warnings for recent reloads, and `bridge_get_game_log` shows the
  `[HotReload]` log lines from inside the game.

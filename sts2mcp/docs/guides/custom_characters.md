# Creating Custom Characters

End-to-end workflow for building a new playable character. For the full `CustomCharacterModel` API surface (every override, visual path, and pool model property), see `get_baselib_reference` topic `custom_character`: this guide covers the practical pipeline.

## Prerequisites

- **BaseLib is required.** Custom characters subclass `BaseLib.Abstracts.CustomCharacterModel`, which auto-registers via `ModelDbCustomCharacters.Register()`. Reference the `Alchyr.Sts2.BaseLib` NuGet package in your `.csproj` (use `create_mod_project` with BaseLib enabled, or `csproj_baselib_template`).
- A character is a bundle of: a C# model class + three pool models, a set of character-specific cards/relics/potions, Godot scenes and image assets packed into a `.pck`, and localization entries.

## Workflow Overview

```
1. create_mod_project           → Project skeleton with BaseLib
2. generate_character           → C# CustomCharacterModel + pool classes
3. scaffold_character_assets    → Godot scene files, localization JSON, image checklist
4. generate_card / generate_relic → Starter deck and starter relic content
5. build_pck                    → Pack scenes/images/localization into .pck
6. build_mod + install_mod      → Compile DLL and deploy to mods/
7. launch_game                  → Test at character select
```

## Step 1: Generate the Character Class

```
generate_character(
    mod_namespace="MyMod",
    mod_name="MyMod",                 # resource folder name for res:// paths
    class_name="MyCharacter",           # PascalCase
    starting_hp=80,
    starting_gold=99,
    color="0.5f, 0.0f, 0.5f",        # or hex: '"ff6644"'
    gender="Neutral",                 # Neutral | Masculine | Feminine (combat pronouns)
    card_hue=0.75,                    # HSV hue for card frame tint (0.75 = purple)
    starter_cards=["StrikeMyCharacter", "StrikeMyCharacter", "StrikeMyCharacter", "StrikeMyCharacter",
                   "DefendMyCharacter", "DefendMyCharacter", "DefendMyCharacter", "DefendMyCharacter",
                   "MySkill", "MyPower"],
    starter_relics=["MyStarterRelic"],
)
```

This produces one file (`Code/Characters/MyCharacter.cs`) containing **four classes**:

- `MyCharacter : CustomCharacterModel`: stats, colors, gender, starter deck/relics, all `res://` asset path overrides (pre-wired to the paths `scaffold_character_assets` creates), a programmatic `CustomEnergyCounter`, animation delays, and a `SetupCustomAnimationStates` stub.
- `MyCharacterCardPool : CustomCardPoolModel`: card frame hue/saturation/value, deck entry color, energy icon paths.
- `MyCharacterRelicPool : CustomRelicPoolModel` and `MyCharacterPotionPool : CustomPotionPoolModel`: energy color name and lab outline color.

It also returns a `localization` dict (`characters.json` entries): merge these into your mod's localization files.

If you skip `starter_cards`/`starter_relics`, the generated class contains TODO stubs; fill them with `ModelDb.Card<T>()` / `ModelDb.Relic<T>()` entries (typically 10 cards, 1 relic).

## Step 2: Scaffold the Asset Skeleton

```
scaffold_character_assets(
    mod_name="MyMod",
    class_name="MyCharacter",
    output_dir="E:/mods/MyMod",
    sprite_size=300,
)
```

Creates `MyMod/Characters/MyCharacter/` with 7 placeholder `.tscn` scenes plus localization:

| File | Purpose |
|------|---------|
| `mycharacter.tscn` | Combat visuals: the `NCreatureVisuals` scene with `Visuals` (Sprite2D), `Bounds`, `CenterPos`, `IntentPos`, `OrbPos` nodes |
| `mycharacter_energy_counter.tscn` | Energy orb scene (only needed if you use the scene-based counter, Option B) |
| `char_select_bg_mycharacter.tscn` | Character select background |
| `mycharacter_rest_site.tscn` | Rest site (campfire) display |
| `mycharacter_merchant.tscn` | Merchant screen display |
| `card_trail_mycharacter.tscn` | Card play trail particle effect |
| `mycharacter_icon.tscn` | Character icon scene |
| `localization/eng/characters.json` | Title, description, and pronoun keys |

It also returns an **image checklist**: PNGs you must create yourself (the scenes reference them):

- `mycharacter.png`: combat sprite (≥ sprite_size px; replace with Spine for full quality)
- `char_select_bg.png` (1920x1080), `char_select_mycharacter.png`, `char_select_mycharacter_locked.png`
- `character_icon_mycharacter.png` (~64x64) + `_outline.png`, `icon.png`, `map_marker_mycharacter.png`
- `energy_counters/mycharacter_orb_layer_0..4.png`: 5 stacked layers (background/shadow, orb body, inner glow, highlight, foreground overlay)
- `ui/mycharacter_energy_icon.png` (~48x48) and `ui/text_mycharacter_energy_icon.png` (~16x16): card cost energy icons
- `hands/multiplayer_hand_mycharacter_point/rock/paper/scissors.png`: multiplayer RPS gestures (optional)

Use `get_character_asset_paths(char_id, mod_name)` any time you need the exact `res://` path for a category (combat visuals, character select, icons, energy layers, SFX event names, required Spine animation names, localization keys).

For generating placeholder or real images, see `get_modding_guide` topic `image_generation`.

## Step 3: Create the Card Pool Content

Character-specific cards, relics, and potions register into the pools via attribute:

```csharp
[Pool(typeof(MyCharacterCardPool))]
public class StrikeMyCharacter : CustomCardModel { ... }

[Pool(typeof(MyCharacterRelicPool))]
public class MyStarterRelic : CustomRelicModel { ... }

[Pool(typeof(MyCharacterPotionPool))]
public class VolatileBrew : CustomPotionModel { ... }
```

Generate them with `generate_card` / `generate_relic` / `generate_potion` (BaseLib variants) and set the pool attribute. Every class named in `StartingDeck`/`StartingRelics` must exist, or the character crashes on select. Fill the pool with enough cards for rewards to function (aim for a spread of commons/uncommons/rares).

## Step 4: Energy Counter

The generated class uses the programmatic option by default:

```csharp
public override CustomEnergyCounter? CustomEnergyCounter =>
    new CustomEnergyCounter(
        i => $"res://MyMod/Characters/MyCharacter/energy_counters/mycharacter_orb_layer_" + i + ".png",
        Color, Color.Lightened(0.3f));   // primary + secondary glow colors
```

Supply the 5 layer PNGs (indices 0-4). Alternatively, comment that out and use the scene-based option: `CustomEnergyCounterPath => ".../mycharacter_energy_counter.tscn"` (the scaffolded scene).

## Step 5: Animation and Audio

- The scaffolded combat scene uses a static `Sprite2D`. For full quality, replace it with a Spine sprite; required animations: `idle_loop`, `attack`, `cast`, `hurt`, `die`, `relaxed_loop` (rest site).
- `SetupCustomAnimationStates(MegaSprite)`: the generated stub calls `SetupAnimationState(controller, "Idle", hitName: "Hit")` for a standard idle/hit state machine.
- The game auto-derives FMOD event paths from the character ID (`event:/sfx/characters/mycharacter/mycharacter_attack`, `_cast`, `_die`, `_select`). These do not exist in the game's banks for custom characters, so register replacements with BaseLib:

```csharp
FmodAudio.RegisterFileReplacement(
    "event:/sfx/characters/mycharacter/mycharacter_attack", "path/to/attack.wav");
```

## Step 6: Localization

Both `generate_character` and `scaffold_character_assets` emit `characters.json` entries:

```json
{
  "mycharacter.title": "MyCharacter",
  "mycharacter.titleObject": "the MyCharacter",
  "mycharacter.pronounSubject": "they",
  "mycharacter.pronounObject": "them",
  "mycharacter.possessiveAdjective": "their",
  "mycharacter.pronounPossessive": "theirs",
  "MYCHARACTER.title": "MYCHARACTER",
  "MYCHARACTER.description": "A new character joins the Spire."
}
```

Place under `MyMod/localization/eng/` so it gets packed into the PCK. See `get_modding_guide` topic `localization` for the loading mechanics.

## Step 7: Build and Deploy

```
1. validate_mod(project_dir)                 → catch missing assets/classes
2. build_mod(project_dir)                    → compile the DLL
3. build_pck(source_dir="E:/mods/MyMod/MyMod",
             output_path="E:/mods/MyMod/mymod.pck",
             res_prefix="MyMod")             → pack scenes, PNGs, localization
4. install_mod(project_dir)                  → copy DLL + PCK + manifest to mods/
5. launch_game()
```

The PCK builder converts `.png` to `.ctex` with import remaps and packs `.tscn`/`.json`/`.tres` as-is. No Godot install is needed. The `res_prefix` must match the `mod_name` used in the generated asset paths (`res://MyMod/...`). See `get_modding_guide` topic `building` for the full pipeline.

## Step 8: Test In-Game

- The character appears on the character select screen (with your `char_select_bg` and portrait). Start a run and verify: starting deck contents, starting relic, HP/gold, energy orb rendering, combat sprite position/bounds, map marker and path color, rest site and merchant displays.
- With the bridge mod running, use `bridge_get_run_state` and the other `bridge_*` tools to drive automated playtests; `hot_reload_project` speeds up iteration on card logic.
- Common failure: a missing `res://` asset path crashes at character select or combat load. Cross-check with `get_character_asset_paths` and verify the PCK contains the file via `list_pck`.

## Optional: Unlock Progression

- `UnlocksAfterRunAs`: gate the character behind completing a run as another character (null = always unlocked).
- `generate_epoch_progression`: scaffold base-game-style Timeline chapter epochs that reveal on milestones and gate the character's content.

## Related

- `get_baselib_reference` topic `custom_character`: full API reference (all visual path overrides, pool model properties, `ExtraAssetPaths`, Architect VFX)
- `get_modding_guide` topics: `cards`, `relics`, `pools`, `localization`, `building`, `image_generation`, `timeline_epochs`

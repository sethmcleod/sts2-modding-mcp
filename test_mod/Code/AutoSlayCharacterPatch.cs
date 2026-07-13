using System;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay;
using MegaCrit.Sts2.Core.Nodes.Screens.CharacterSelect;

namespace MCPTest;

/// <summary>
/// The stock AutoSlayer selects a RANDOM unlocked character (PlayMainMenuAsync: _random.NextItem of the
/// buttons where !IsLocked), so bridge_autoslay_start's `character` param was silently ignored — it would
/// often play the wrong character. This makes the char-select report only the requested character as
/// unlocked during a targeted AutoSlay, so the random pick can only land on it (and it bypasses unlock
/// gating for testing). No effect outside AutoSlay or when no character was requested.
/// </summary>
[HarmonyPatch(typeof(NCharacterSelectButton), nameof(NCharacterSelectButton.IsLocked), MethodType.Getter)]
public static class ForceAutoSlayCharacterPatch
{
    public static void Postfix(NCharacterSelectButton __instance, ref bool __result)
    {
        var target = BridgeHandler.AutoSlayCharacter;
        if (!AutoSlayer.IsActive || string.IsNullOrEmpty(target))
            return;

        var name = __instance.Character?.GetType().Name;
        var isTarget = name != null && name.Equals(target, StringComparison.OrdinalIgnoreCase);
        __result = !isTarget; // only the requested character is selectable; all others read as locked
    }
}

/// <summary>
/// The stock AutoSlayer QUITS the whole game (NGame.GetTree().Quit) in RunAsync's finally at the end of
/// every run — it's built for one-shot CI smoke tests. That makes multi-run balance batches impossible:
/// run 1 kills the game. Suppress the quit so the game stays alive and the bridge can drive consecutive runs.
/// </summary>
[HarmonyPatch(typeof(AutoSlayer), "QuitGame")]
public static class KeepGameAliveAfterAutoSlayPatch
{
    public static bool Prefix() => false; // skip the Quit; run already ended, game returns to menu/game-over
}

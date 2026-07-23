using System;
using System.Collections.Generic;
using System.Text.Json;
using Godot;
using GodotEngine = Godot.Engine;

namespace MCPTest;

/// <summary>
/// Walks the FmodServer GDExtension singleton (utopia-rise fmod-gdextension) and dumps
/// every loaded bank's events, buses, and the global parameters into the schema that
/// the MCP server's _list_game_audio expects (fmod_dump.json).
/// Must run on the main thread (dispatch via MainThreadDispatcher.Invoke).
/// </summary>
public static class FmodDumper
{
    public static object Dump(JsonElement root)
    {
        GodotObject? server = null;
        try { server = GodotEngine.GetSingleton("FmodServer"); }
        catch (Exception ex) { return new { success = false, error = $"FmodServer singleton not available: {ex.Message}" }; }
        if (server == null)
            return new { success = false, error = "FmodServer singleton is null" };

        var events = new List<Dictionary<string, object?>>();
        var buses = new List<Dictionary<string, object?>>();
        var banks = new List<Dictionary<string, object?>>();
        var globalParameters = new List<Dictionary<string, object?>>();
        var warnings = new List<string>();
        // Bank walking can race a bank that is still streaming in.
        var seenEventKeys = new HashSet<string>();
        var seenBusKeys = new HashSet<string>();

        try
        {
            TryCall(server, "wait_for_all_loads");
        }
        catch { }

        // ── Banks (and their events + buses) ────────────────────────────
        var allBanks = TryCall(server, "get_all_banks");
        if (allBanks is { } banksVariant && banksVariant.VariantType == Variant.Type.Array)
        {
            foreach (var bankVariant in banksVariant.AsGodotArray())
            {
                if (bankVariant.Obj is not GodotObject bank) continue;
                string bankPath = Str(TryCall(bank, "get_path"));
                string resPath = Str(TryCall(bank, "get_godot_res_path"));
                var bankEvents = new List<Dictionary<string, object?>>();

                var descList = TryCall(bank, "get_description_list");
                if (descList is { } dl && dl.VariantType == Variant.Type.Array)
                {
                    foreach (var descVariant in dl.AsGodotArray())
                    {
                        var ev = ReadEventDescription(descVariant, warnings);
                        if (ev == null) continue;
                        bankEvents.Add(ev);
                        string key = Str(ev.GetValueOrDefault("guid")) + "|" + Str(ev.GetValueOrDefault("path"));
                        if (seenEventKeys.Add(key))
                            events.Add(ev);
                    }
                }
                else
                {
                    warnings.Add($"Bank '{resPath}': get_description_list unavailable");
                }

                var busList = TryCall(bank, "get_bus_list");
                if (busList is { } bl && bl.VariantType == Variant.Type.Array)
                {
                    foreach (var busVariant in bl.AsGodotArray())
                    {
                        var bus = ReadBus(busVariant);
                        if (bus == null) continue;
                        string key = Str(bus.GetValueOrDefault("guid")) + "|" + Str(bus.GetValueOrDefault("path"));
                        if (seenBusKeys.Add(key))
                            buses.Add(bus);
                    }
                }

                banks.Add(new Dictionary<string, object?>
                {
                    ["path"] = bankPath.Length > 0 ? bankPath : resPath,
                    ["guid"] = Str(TryCall(bank, "get_guid")),
                    ["godot_res_path"] = resPath,
                    ["event_count"] = bankEvents.Count,
                    ["loading_state"] = ToClr(TryCall(bank, "get_loading_state")),
                });
            }
        }
        else
        {
            warnings.Add("FmodServer.get_all_banks unavailable or returned non-array");
        }

        // ── Any events not attributed to an enumerated bank ─────────────
        var allDescs = TryCall(server, "get_all_event_descriptions");
        if (allDescs is { } ad && ad.VariantType == Variant.Type.Array)
        {
            foreach (var descVariant in ad.AsGodotArray())
            {
                var ev = ReadEventDescription(descVariant, warnings);
                if (ev == null) continue;
                string key = Str(ev.GetValueOrDefault("guid")) + "|" + Str(ev.GetValueOrDefault("path"));
                if (seenEventKeys.Add(key))
                    events.Add(ev);
            }
        }

        // ── Buses not surfaced through any bank's get_bus_list ──────────
        var allBuses = TryCall(server, "get_all_buses");
        if (allBuses is { } ab && ab.VariantType == Variant.Type.Array)
        {
            foreach (var busVariant in ab.AsGodotArray())
            {
                var bus = ReadBus(busVariant);
                if (bus == null) continue;
                string key = Str(bus.GetValueOrDefault("guid")) + "|" + Str(bus.GetValueOrDefault("path"));
                if (seenBusKeys.Add(key))
                    buses.Add(bus);
            }
        }

        // ── Global parameters ───────────────────────────────────────────
        var globalDescs = TryCall(server, "get_global_parameter_desc_list");
        if (globalDescs is { } gd && gd.VariantType == Variant.Type.Array)
        {
            foreach (var paramVariant in gd.AsGodotArray())
            {
                var param = ReadParameter(paramVariant);
                if (param != null)
                    globalParameters.Add(param);
            }
        }

        return new
        {
            success = true,
            events,
            buses,
            banks,
            global_parameters = globalParameters,
            warnings,
        };
    }

    private static Dictionary<string, object?>? ReadEventDescription(Variant descVariant, List<string> warnings)
    {
        if (descVariant.Obj is not GodotObject desc) return null;
        var ev = new Dictionary<string, object?>
        {
            ["path"] = Str(TryCall(desc, "get_path")),
            ["guid"] = Str(TryCall(desc, "get_guid")),
        };
        var length = TryCall(desc, "get_length");
        if (length is { } len && len.VariantType == Variant.Type.Int)
            ev["length_ms"] = len.AsInt64();
        var isStream = TryCall(desc, "is_stream");
        if (isStream is { } s && s.VariantType == Variant.Type.Bool && s.AsBool())
            ev["is_stream"] = true;
        var isSnapshot = TryCall(desc, "is_snapshot");
        if (isSnapshot is { } sn && sn.VariantType == Variant.Type.Bool && sn.AsBool())
            ev["is_snapshot"] = true;
        var isOneShot = TryCall(desc, "is_one_shot");
        if (isOneShot is { } os && os.VariantType == Variant.Type.Bool && os.AsBool())
            ev["is_one_shot"] = true;

        var parameters = TryCall(desc, "get_parameters");
        if (parameters is { } ps && ps.VariantType == Variant.Type.Array)
        {
            var paramList = new List<Dictionary<string, object?>>();
            foreach (var paramVariant in ps.AsGodotArray())
            {
                var param = ReadParameter(paramVariant);
                if (param != null)
                    paramList.Add(param);
            }
            if (paramList.Count > 0)
                ev["parameters"] = paramList;
        }
        return ev;
    }

    private static Dictionary<string, object?>? ReadBus(Variant busVariant)
    {
        if (busVariant.Obj is not GodotObject bus) return null;
        var entry = new Dictionary<string, object?>
        {
            ["path"] = Str(TryCall(bus, "get_path")),
            ["guid"] = Str(TryCall(bus, "get_guid")),
        };
        var volume = TryCall(bus, "get_volume");
        if (volume is { } v && (v.VariantType == Variant.Type.Float || v.VariantType == Variant.Type.Int))
            entry["volume"] = v.AsDouble();
        return entry;
    }

    /// <summary>
    /// A parameter description is either an FmodParameterDescription object (getter methods)
    /// or a Dictionary, depending on the extension version. Normalize both to the
    /// name/minimum/maximum/default_value keys _list_game_audio reads.
    /// </summary>
    private static Dictionary<string, object?>? ReadParameter(Variant paramVariant)
    {
        if (paramVariant.Obj is GodotObject paramObj)
        {
            var param = new Dictionary<string, object?>
            {
                ["name"] = Str(TryCall(paramObj, "get_name")),
                ["minimum"] = TryCall(paramObj, "get_minimum")?.AsDouble() ?? 0.0,
                ["maximum"] = TryCall(paramObj, "get_maximum")?.AsDouble() ?? 0.0,
                ["default_value"] = TryCall(paramObj, "get_default_value")?.AsDouble() ?? 0.0,
            };
            var isGlobal = TryCall(paramObj, "is_global");
            if (isGlobal is { } g && g.VariantType == Variant.Type.Bool && g.AsBool())
                param["is_global"] = true;
            var isDiscrete = TryCall(paramObj, "is_discrete");
            if (isDiscrete is { } d && d.VariantType == Variant.Type.Bool && d.AsBool())
                param["is_discrete"] = true;
            return param;
        }

        if (paramVariant.VariantType == Variant.Type.Dictionary)
        {
            var dict = paramVariant.AsGodotDictionary();
            var param = new Dictionary<string, object?>();
            foreach (var key in dict.Keys)
                param[key.AsString()] = ToClr(dict[key]);
            // Older extension builds use FMOD's own field casing.
            if (!param.ContainsKey("default_value") && param.ContainsKey("defaultvalue"))
                param["default_value"] = param["defaultvalue"];
            param.TryAdd("name", "");
            param.TryAdd("minimum", 0.0);
            param.TryAdd("maximum", 0.0);
            param.TryAdd("default_value", 0.0);
            return param;
        }

        return null;
    }

    private static Variant? TryCall(GodotObject obj, string method)
    {
        try
        {
            if (!obj.HasMethod(method)) return null;
            return obj.Call(method);
        }
        catch { return null; }
    }

    private static string Str(object? value) => value?.ToString() ?? "";

    private static string Str(Variant? value)
    {
        if (value is not { } v || v.VariantType == Variant.Type.Nil) return "";
        return v.AsString();
    }

    private static object? ToClr(Variant? value)
    {
        if (value is not { } v) return null;
        return v.VariantType switch
        {
            Variant.Type.Nil => null,
            Variant.Type.Bool => v.AsBool(),
            Variant.Type.Int => v.AsInt64(),
            Variant.Type.Float => v.AsDouble(),
            Variant.Type.String or Variant.Type.StringName => v.AsString(),
            _ => v.ToString(),
        };
    }
}

"""Offline tests for generator output shape and updated API signatures."""

import pytest


def assert_valid_cs(source: str, expected_class: str = ""):
    assert source, "Source is empty"
    assert "namespace " in source, "Missing namespace declaration"
    assert "class " in source or "static class " in source, "Missing class declaration"
    assert source.count("{") == source.count("}"), "Brace mismatch"
    if expected_class:
        assert expected_class in source


def assert_generator_result(result: dict, expect_source: bool = True):
    assert isinstance(result, dict)
    if expect_source:
        assert "source" in result
        assert_valid_cs(result["source"])
    if "file_name" in result:
        assert "." in result["file_name"]


class TestGenerateEvent:
    def test_default_choices_match_current_event_api(self, mod_gen):
        result = mod_gen.generate_event(
            mod_namespace="TestMod",
            class_name="MysteriousAltar",
        )
        assert_generator_result(result)
        src = result["source"]
        loc = result["localization"]["events.json"]

        assert "IReadOnlyList<EventOption>" in src
        assert "new EventOption(this," in src
        assert "private Task ChoiceAccept()" in src
        assert "SetEventFinished(L10NLookup(" in src
        assert "MYSTERIOUS_ALTAR.pages.INITIAL.description" in loc
        assert "MYSTERIOUS_ALTAR.pages.INITIAL.options.ACCEPT.title" in loc

    def test_custom_choices_preserve_labels(self, mod_gen):
        result = mod_gen.generate_event(
            mod_namespace="TestMod",
            class_name="DarkShrine",
            is_shared=True,
            choices=[
                {"label": "Pray", "method_name": "ChoicePray", "effect_description": "Gain 1 max HP"},
                {"label": "Desecrate", "method_name": "ChoiceDesecrate"},
            ],
        )
        src = result["source"]
        loc = result["localization"]["events.json"]
        assert "IsShared => true" in src
        assert "ChoicePray" in src
        assert loc["DARK_SHRINE.pages.INITIAL.options.PRAY.title"] == "Pray"
        assert loc["DARK_SHRINE.pages.RESULTS.PRAY.description"].startswith("TODO:")


class TestGenerateOrb:
    def test_basic_orb_matches_current_orb_api(self, mod_gen):
        result = mod_gen.generate_orb(
            mod_namespace="TestMod",
            class_name="PlasmaOrb",
            passive_amount=2,
            evoke_amount=5,
        )
        assert_generator_result(result)
        src = result["source"]
        assert "public override decimal PassiveVal" in src
        assert "public override decimal EvokeVal" in src
        assert "public override async Task Passive" in src
        assert "public override async Task<IEnumerable<Creature>> Evoke" in src
        assert "public override Color DarkenedColor" in src

    def test_orb_localization_uses_smart_description(self, mod_gen):
        result = mod_gen.generate_orb(
            mod_namespace="TestMod",
            class_name="VoidOrb",
            passive_description="Deal 3 damage to all enemies.",
            evoke_description="Deal 9 damage to all enemies.",
        )
        loc = result["localization"]["orbs.json"]
        assert "VOID_ORB.smartDescription" in loc
        assert "Deal 3 damage" in loc["VOID_ORB.smartDescription"]
        assert "Passive: {Passive}. Evoke: {Evoke}." == loc["VOID_ORB.description"]


class TestGenerateEnchantment:
    def test_default_mentions_current_card_property(self, mod_gen):
        result = mod_gen.generate_enchantment(
            mod_namespace="TestMod",
            class_name="FlameEnchantment",
        )
        assert_generator_result(result)
        assert "The enchanted card is available as Card." in result["source"]

    def test_damage_hook_uses_enchant_damage_additive(self, mod_gen):
        result = mod_gen.generate_enchantment(
            mod_namespace="TestMod",
            class_name="SharpEnchantment",
            trigger_hook="ModifyDamageAdditive",
        )
        src = result["source"]
        assert "EnchantDamageAdditive" in src
        assert "EnchantmentStatus.Normal" in src
        assert "EnchantedCard" not in src

    def test_after_card_played_uses_current_signature(self, mod_gen):
        result = mod_gen.generate_enchantment(
            mod_namespace="TestMod",
            class_name="EchoEnchantment",
            trigger_hook="AfterCardPlayed",
        )
        src = result["source"]
        assert "AfterCardPlayed(PlayerChoiceContext context, CardPlay cardPlay)" in src
        assert "cardPlay.Card != Card" in src


class TestGenerateGameAction:
    def test_default_action_matches_game_action_base(self, mod_gen):
        result = mod_gen.generate_game_action(
            mod_namespace="TestMod",
            class_name="ChainLightningAction",
        )
        assert_generator_result(result, expect_source=True)
        src = result["source"]
        assert "public override ulong OwnerId" in src
        assert "protected override async Task ExecuteAction()" in src
        assert "public override INetAction ToNetAction()" in src
        assert "private readonly ulong _ownerId;" in src

    def test_custom_params_are_stored(self, mod_gen):
        result = mod_gen.generate_game_action(
            mod_namespace="TestMod",
            class_name="BurstAction",
            description="Plays a card twice",
            parameters=[
                {"name": "cardIndex", "type": "int"},
                {"name": "playCount", "type": "int"},
            ],
        )
        src = result["source"]
        assert "int cardIndex" in src
        assert "int playCount" in src
        assert "_cardIndex = cardIndex;" in src
        assert "Plays a card twice" in src


class TestGenerateNetMessage:
    def test_net_message_uses_packet_reader_writer(self, mod_gen):
        result = mod_gen.generate_net_message(
            mod_namespace="TestMod",
            class_name="TestMessage",
            fields=[
                {"name": "Data", "type": "string"},
                {"name": "Amount", "type": "int"},
            ],
        )
        assert_generator_result(result)
        src = result["source"]
        assert "Serialize(PacketWriter writer)" in src
        assert "Deserialize(PacketReader reader)" in src
        assert "public NetTransferMode Mode" in src
        assert "public LogLevel LogLevel" in src
        assert "writer.WriteString(Data);" in src
        assert "Amount = reader.ReadInt();" in src


class TestGenerateSettingsPanel:
    def test_settings_panel_emits_project_edits(self, mod_gen):
        result = mod_gen.generate_settings_panel(
            mod_namespace="TestMod",
            class_name="ModSettings",
            mod_id="testmod",
        )
        assert_generator_result(result)
        src = result["source"]
        assert "public static void Initialize()" in src
        assert "NGame.Instance?.GetTree()" in src
        assert result["project_edits"][0]["type"] == "ensure_using"
        assert result["project_edits"][1]["type"] == "insert_text"


class TestGenerateCustomTooltip:
    def test_custom_tooltip_is_now_a_helper(self, mod_gen):
        result = mod_gen.generate_custom_tooltip(
            mod_namespace="TestMod",
            tag_name="fury",
            title="Fury",
            tooltip_description="At end of turn, deal damage equal to Fury stacks.",
        )
        assert_generator_result(result)
        src = result["source"]
        assert "HoverTip Create()" in src
        assert 'new LocString(Table, TitleKey)' in src
        assert 'new LocString(Table, DescriptionKey)' in src
        assert "IEnumerable<IHoverTip> AsSingleTip()" in src
        assert result["folder"] == "Code/Tooltips"
        assert result["localization"]["tooltips.json"]["tooltips"]["FURY.title"] == "Fury"
        assert result["localization"]["tooltips.json"]["tooltips"]["FURY.description"] == (
            "At end of turn, deal damage equal to Fury stacks."
        )

    def test_custom_tooltip_usage_targets_extra_hover_tips(self, mod_gen):
        result = mod_gen.generate_custom_tooltip(
            mod_namespace="TestMod",
            tag_name="resonance",
            title="Resonance",
            tooltip_description="Stacks of Resonance amplify orb effects.",
        )
        assert "ExtraHoverTips" in result["usage"]
        assert "ResonanceTooltip.AsSingleTip()" in result["usage"]


class TestExistingGenerators:
    def test_generate_card(self, mod_gen):
        result = mod_gen.generate_card(
            mod_namespace="TestMod",
            class_name="TestStrike",
            card_type="Attack",
            damage=6,
            energy_cost=1,
        )
        assert_generator_result(result)
        assert "CardModel" in result["source"] or "CustomCardModel" in result["source"]

    def test_generate_relic(self, mod_gen):
        result = mod_gen.generate_relic(
            mod_namespace="TestMod",
            class_name="TestRelic",
            trigger_hook="BeforeCombatStart",
        )
        assert_generator_result(result)
        assert "BeforeCombatStart" in result["source"]

    def test_generate_power(self, mod_gen):
        result = mod_gen.generate_power(
            mod_namespace="TestMod",
            class_name="TestPower",
            power_type="Buff",
            trigger_hook="AfterTurnEnd",
        )
        assert_generator_result(result)

    def test_generate_potion(self, mod_gen):
        result = mod_gen.generate_potion(
            mod_namespace="TestMod",
            class_name="TestPotion",
            block=10,
        )
        assert_generator_result(result)

    def test_generate_save_data(self, mod_gen):
        result = mod_gen.generate_save_data(
            mod_namespace="TestMod",
            mod_id="testmod",
        )
        assert_generator_result(result)
        assert "JsonSerializer" in result["source"]

    def test_generate_test_scenario(self, mod_gen):
        result = mod_gen.generate_test_scenario(
            scenario_name="Strength build test",
            relics=["Vajra"],
            cards=["Bash", "HeavyBlade"],
            gold=500,
            hp=999,
            powers=[{"name": "StrengthPower", "stacks": 10}],
            fight="AXEBOTS_NORMAL",
            godmode=True,
        )
        assert result["command_count"] == len(result["commands"])
        assert "godmode" in result["combined"]

    def test_generate_vfx_scene(self, mod_gen):
        result = mod_gen.generate_vfx_scene(node_name="FlameExplosion")
        assert "[gd_scene" in result["scene"]
        assert result["file_name"].endswith(".tscn")


class TestGenerateEpochProgression:
    def _gen(self, mod_gen, **kw):
        return mod_gen.generate_epoch_progression(
            mod_namespace="TestMod",
            character_class="Sage",
            card_pool_class="SageCardPool",
            relic_pool_class="SageRelicPool",
            potion_pool_class="SagePotionPool",
            **kw,
        )

    def test_emits_valid_files_and_all_chapters(self, mod_gen):
        result = self._gen(mod_gen)
        assert_generator_result(result, expect_source=False)
        files = result["files"]
        # base + epochs + registration + gating + EpochPatches (no pool isolation)
        assert len(files) == 5
        for path, src in files.items():
            assert_valid_cs(src)  # brace balance etc. on every generated file
        assert result["components"]["epochs"] == [f"Sage{k}Epoch" for k in range(1, 8)]

    def test_avoids_the_double_reveal_antipattern(self, mod_gen):
        src = "\n".join(self._gen(mod_gen)["files"].values())
        # never force-reveal-all (the RevealAllIfFresh bug); hide via the AddEpochSlots prefix instead
        assert "RevealAllIfFresh" not in src
        assert "HideWhenDisabled" in src
        assert "RemoveAll(s => s.Model is SageEpoch)" in src

    def test_content_gating_and_registration(self, mod_gen):
        result = self._gen(mod_gen)
        src = "\n".join(result["files"].values())
        # gating uses compile-time-generic reveal checks per chapter
        assert "us.IsEpochRevealed<Sage2Epoch>()" in src
        # the real gate is the pools (snippet), not the stat ids
        assert "EpochGating.CardUnlocked" in result["pool_overrides_snippet"]
        # reflection registration into the base private statics
        assert "_epochTypeDictionary" in src and "_allEpochs" in src
        # gateway opens the rest
        assert "Get<Sage7Epoch>()" in src

    def test_no_pool_isolation(self, mod_gen):
        # pool isolation is intentionally out of scope for the generator
        result = self._gen(mod_gen)
        src = "\n".join(result["files"].values())
        assert "PoolPatches" not in result["files"] and "PoolPatches" not in str(result["components"])
        assert "CharacterCardPools" not in src and "Kaleidoscope" not in src
        assert "KeepPoolsSeparate" not in result["config_snippet"]

    def test_localization_shape(self, mod_gen):
        loc = self._gen(mod_gen)["localization"]
        assert "SAGE-SAGE1_EPOCH.title" in loc["epochs.json"]
        assert "SAGE-ENABLE_EPOCHS.title" in loc["settings_ui.json"]
        assert "SAGE-KEEP_POOLS_SEPARATE.title" not in loc["settings_ui.json"]

    def test_num_epochs_param(self, mod_gen):
        result = self._gen(mod_gen, num_epochs=3)
        assert result["components"]["epochs"] == ["Sage1Epoch", "Sage2Epoch", "Sage3Epoch"]
        for src in result["files"].values():
            assert_valid_cs(src)

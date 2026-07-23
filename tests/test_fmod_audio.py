"""Tests for the FMOD audio index: _load_fmod_data (file + live-bridge fallback) and _list_game_audio."""

import json

import pytest

from sts2mcp import server


SAMPLE_DATA = {
    "events": [
        {
            "path": "event:/sfx/merchant/hello",
            "guid": "{aaaa-1111}",
            "length_ms": 1200,
            "is_stream": False,
            "parameters": [
                {"name": "pitch", "minimum": 0.0, "maximum": 2.0, "default_value": 1.0},
            ],
        },
        {"path": "event:/music/act2_theme", "guid": "{bbbb-2222}", "is_stream": True},
    ],
    "buses": [
        {"path": "bus:/master/sfx", "guid": "{cccc-3333}", "volume": 1.0},
    ],
    "banks": [
        {"path": "bank:/Master", "guid": "{dddd-4444}", "godot_res_path": "res://audio/Master.bank", "event_count": 2},
    ],
    "global_parameters": [
        {"name": "combat_intensity", "minimum": 0.0, "maximum": 1.0, "default_value": 0.0},
    ],
}


@pytest.fixture(autouse=True)
def reset_fmod_cache():
    server._fmod_data = None
    yield
    server._fmod_data = None


def _results_text(query, category="events"):
    out = server._list_game_audio(query, category)
    return out[0].text


class TestListGameAudio:
    @pytest.fixture(autouse=True)
    def use_sample_data(self):
        server._fmod_data = SAMPLE_DATA

    def test_event_search_by_path(self):
        text = _results_text("merchant")
        assert "Found 1 results" in text
        assert "event:/sfx/merchant/hello" in text

    def test_event_includes_parameters(self):
        text = _results_text("merchant")
        payload = json.loads(text.split("\n\n", 1)[1])
        assert payload[0]["parameters"] == [
            {"name": "pitch", "min": 0.0, "max": 2.0, "default": 1.0}
        ]

    def test_stream_flag_surfaced(self):
        text = _results_text("act2")
        payload = json.loads(text.split("\n\n", 1)[1])
        assert payload[0]["is_stream"] is True

    def test_bus_and_bank_and_global_param_search(self):
        assert "bus:/master/sfx" in _results_text("sfx", "buses")
        assert "res://audio/Master.bank" in _results_text("master", "banks")
        assert "combat_intensity" in _results_text("combat", "global_parameters")

    def test_all_category_spans_everything(self):
        payload = json.loads(_results_text("", "all").split("\n\n", 1)[1])
        assert len(payload) == 5

    def test_no_dump_hint_absent_when_data_exists(self):
        assert "No FMOD dump" not in _results_text("merchant")


class TestLoadFmodData:
    def test_loads_from_dump_file(self, tmp_path, monkeypatch):
        dump = tmp_path / "fmod_dump.json"
        dump.write_text(json.dumps(SAMPLE_DATA), encoding="utf-8")
        monkeypatch.setattr(server, "_fmod_dump_candidates", lambda: [str(dump)])
        assert server._load_fmod_data() == SAMPLE_DATA

    def test_live_bridge_fallback_writes_cache(self, tmp_path, monkeypatch):
        cache = tmp_path / "fmod_dump.json"
        monkeypatch.setattr(server, "_fmod_dump_candidates", lambda: [str(cache)])
        from sts2mcp import bridge_client
        monkeypatch.setattr(bridge_client, "fmod_dump", lambda timeout=30.0: {"success": True, **SAMPLE_DATA})

        data = server._load_fmod_data()
        assert data == SAMPLE_DATA
        assert json.loads(cache.read_text(encoding="utf-8")) == SAMPLE_DATA

    def test_bridge_unavailable_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "_fmod_dump_candidates", lambda: [str(tmp_path / "missing.json")])
        from sts2mcp import bridge_client
        monkeypatch.setattr(bridge_client, "fmod_dump", lambda timeout=30.0: {"error": "Bridge not running"})

        data = server._load_fmod_data()
        assert data == {"events": [], "buses": [], "banks": [], "global_parameters": []}
        # An empty result must not be cached in memory — a later call with the game running should retry.
        assert server._fmod_data is None

    def test_empty_result_mentions_missing_dump(self, tmp_path, monkeypatch):
        monkeypatch.setattr(server, "_fmod_dump_candidates", lambda: [str(tmp_path / "missing.json")])
        from sts2mcp import bridge_client
        monkeypatch.setattr(bridge_client, "fmod_dump", lambda timeout=30.0: {"error": "Bridge not running"})
        assert "No FMOD dump" in _results_text("anything")

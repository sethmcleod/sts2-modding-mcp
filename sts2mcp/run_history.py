"""Offline reader for the game's Run History compendium.

The game writes one JSON file per finished run to
<save root>/SlayTheSpire2/**/saves/history/<id>.run. Each file holds the
RunHistory schema: per-floor player stats (damage taken, HP healed, gold),
per-combat turn counts, card choices with picked/skipped flags, enchantments,
rest-site choices, potions used, and the final deck and relics. The in-game
Run History screen shows only part of this data, so this module reads the
files directly. No live game or bridge is needed.
"""

from __future__ import annotations

import json
import platform
from collections import Counter
from pathlib import Path
from typing import Any


def _save_roots() -> list[Path]:
    home = Path.home()
    if platform.system() == "Darwin":
        roots = [home / "Library/Application Support/SlayTheSpire2"]
    elif platform.system() == "Windows":
        roots = [home / "AppData/Roaming/SlayTheSpire2"]
    else:
        roots = [home / ".local/share/SlayTheSpire2"]
    return [r for r in roots if r.exists()]


def _short(model_id: Any) -> str:
    if not model_id:
        return str(model_id)
    return str(model_id).split(".")[-1]


def _card_name(card: Any) -> str:
    if not isinstance(card, dict):
        return _short(card)
    name = _short(card.get("id"))
    level = int(card.get("current_upgrade_level") or 0)
    if level:
        name += "+" * level
    enchant = card.get("enchantment")
    if isinstance(enchant, dict) and enchant.get("id"):
        name += f"[{_short(enchant['id'])}]"
    return name


def find_run_files(profile: str | None = None) -> list[Path]:
    """Return every .run file, newest first. profile filters by path substring."""
    files: list[Path] = []
    for root in _save_roots():
        files.extend(root.glob("**/saves/history/*.run"))
    if profile:
        files = [f for f in files if profile.lower() in str(f).lower()]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def summarize_run(d: dict, path: Path) -> dict:
    """One-line stats for a run: identity, outcome, damage economy, combat pace."""
    player = d["players"][0]
    pid = player["id"]
    dmg = heal = turns = fights = 0
    kind_turns: dict[str, list[int]] = {"monster": [], "elite": [], "boss": []}
    for act in d.get("map_point_history", []):
        for mp in act:
            st = next((e for e in mp["player_stats"] if e["player_id"] == pid), None)
            if st:
                dmg += st.get("damage_taken", 0)
                heal += st.get("hp_healed", 0)
            for room in mp.get("rooms") or []:
                t = room.get("turns_taken", 0)
                if t:
                    turns += t
                    fights += 1
                    kind_turns.setdefault(room.get("room_type", ""), []).append(t)
    return {
        "file": str(path),
        "character": _short(player["character"]),
        "seed": d.get("seed"),
        "ascension": d.get("ascension"),
        "win": d.get("win"),
        "abandoned": d.get("was_abandoned"),
        "killed_by": _short(d.get("killed_by_encounter")),
        "minutes": round(d.get("run_time", 0) / 60),
        "build": d.get("build_id"),
        "acts": [_short(a) for a in d.get("acts", [])],
        "damage_taken": dmg,
        "hp_healed": heal,
        "fights": fights,
        "total_turns": turns,
        "avg_turns": {
            k: round(sum(v) / len(v), 1) for k, v in kind_turns.items() if v
        },
        "deck_size": len(list(player.get("deck", []))),
        "relic_count": len(list(player.get("relics", []))),
    }


def analyze_run(d: dict) -> dict:
    """Full per-floor breakdown, card-choice log, and final deck for one run."""
    player = d["players"][0]
    pid = player["id"]
    floors = []
    choices = []
    offered: Counter = Counter()
    picked: Counter = Counter()
    rest_sites = []
    potions_used: Counter = Counter()
    floor_no = 0
    for act_index, act in enumerate(d.get("map_point_history", [])):
        for mp in act:
            floor_no += 1
            st = next((e for e in mp["player_stats"] if e["player_id"] == pid), None)
            if st is None:
                continue
            rooms = mp.get("rooms") or []
            floors.append({
                "floor": floor_no,
                "act": act_index + 1,
                "type": mp.get("map_point_type"),
                "hp": f"{st.get('current_hp')}/{st.get('max_hp')}",
                "damage_taken": st.get("damage_taken", 0),
                "hp_healed": st.get("hp_healed", 0),
                "gold": st.get("current_gold"),
                "turns": sum(r.get("turns_taken", 0) for r in rooms) or None,
                "encounters": [
                    _short(r.get("model_id")) for r in rooms
                    if r.get("room_type") in ("monster", "elite", "boss")
                ],
                "cards_gained": [_card_name(c) for c in st.get("cards_gained", [])],
                "cards_removed": [_card_name(c) for c in st.get("cards_removed", [])],
                "cards_upgraded": [_short(u) for u in st.get("upgraded_cards", [])],
                "cards_enchanted": [
                    f"{_card_name(e.get('card'))} <- {_short(e.get('enchantment'))}"
                    for e in st.get("cards_enchanted", [])
                ],
            })
            reward = st.get("card_choices", [])
            if reward:
                names = [_card_name(o.get("card")) for o in reward]
                took = [_card_name(o.get("card")) for o in reward if o.get("was_picked")]
                for n in names:
                    offered[n.rstrip("+")] += 1
                for n in took:
                    picked[n.rstrip("+")] += 1
                choices.append({"floor": floor_no, "picked": took, "offered": names})
            for rc in st.get("rest_site_choices", []):
                rest_sites.append({"floor": floor_no, "choice": rc})
            for p in st.get("potion_used", []):
                potions_used[_short(p)] += 1

    result = summarize_run(d, Path("."))
    result.pop("file", None)
    result.update({
        "floors": floors,
        "card_choices": choices,
        "pick_rates": {
            n: {"offered": c, "picked": picked.get(n, 0)}
            for n, c in offered.most_common()
        },
        "rest_sites": rest_sites,
        "potions_used": dict(potions_used.most_common()),
        "final_deck": dict(sorted(
            Counter(_card_name(c) for c in player.get("deck", [])).items())),
        "relics": [_short(r) for r in player.get("relics", [])],
    })
    return result


def read_run_history(
    profile: str | None = None,
    seed: str | None = None,
    character: str | None = None,
    limit: int = 5,
    detail: str = "summary",
) -> dict:
    """Entry point for the read_run_history tool."""
    files = find_run_files(profile)
    runs = []
    for f in files:
        d = _load(f)
        if d is None or not d.get("players"):
            continue
        if seed and d.get("seed") != seed:
            continue
        if character and character.lower() not in _short(
                d["players"][0].get("character", "")).lower():
            continue
        runs.append((f, d))
        if len(runs) >= limit:
            break
    if not runs:
        return {"runs": [], "note": "no matching .run files found"}
    if detail == "full":
        return {"runs": [analyze_run(d) | {"file": str(f)} for f, d in runs]}
    return {"runs": [summarize_run(d, f) for f, d in runs]}

"""Auto-extract a combatant entry for api/game_data/characters.py::CHARACTERS.

Reads from the unpacked client (output/):
  - db/char_base@char_base.json — display class, attribute, grade (authoritative)
  - db/char_base@char_combatant.json — base stats (authoritative)
  - db/char_base@combatant_level.json — per-level ATK/DEF/HP deltas
  - db/char_base@combatant_ascend.json — per-ascend ATK/DEF/HP deltas
  - db/potential_node@potential_node_effect.json — node_50 / node_60 stat types
  - text/en/text.json — English combatant name

Stats are reported at level=60, ascend=5 to match the convention used in
CHARACTERS (the same convention used by build_scaling_tables.py / scaling.py).

Usage:
    python scripts/extract_combatant.py <output_dir> <res_id> [<res_id> ...]

Example:
    python scripts/extract_combatant.py C:/Users/soste/Downloads/output 1055
"""
from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.client_db import table, table_by_id, text_index  # noqa: E402
from entry_format import format_entry  # noqa: E402

# link_char_growth_material_id is "c_{class_key}_{color_key}".
GROWTH_CLASS_TO_CLASS = {
    "controller": "Controller",
    # The client renamed "knight" to "vanguard" in late September 2026. The old key stays for older dumps.
    "knight": "Vanguard",
    "vanguard": "Vanguard",
    "striker": "Striker",
    "ranger": "Ranger",
    "hunter": "Hunter",
    "psionic": "Psionic",
}

GROWTH_COLOR_TO_ATTRIBUTE = {
    "orange": "Instinct",
    "blue": "Justice",
    "purple": "Void",
    "red": "Passion",
    "green": "Order",
}

RARITY_TO_GRADE = {
    "RARITY_SSR": 5,
    "RARITY_SR": 4,
    "RARITY_R": 3,
}

# Potential nodes sit in numbered slots, and their effect ids read "<res_id>_<slot>_<branch>_<step>".
# Slots 5 and 6 are the two the app records as node_50 and node_60.
NODE_SLOTS = {5: "node_50", 6: "node_60"}

# The tree layout names the same two slots by branch instead.
NODE_LAYOUT_SLOTS = {"5_0": "node_50", "6_0": "node_60"}

NODE_STAT_TO_LABEL = {
    "S_CRI_INC_ADD": "CRate",
    "S_CRI_DMG_RATE_INC_ADD": "CDmg",
    "S_ATK_INC_RATE_OUT": "ATK%",
    "S_DEF_INC_RATE_OUT": "DEF%",
    "S_HP_INC_RATE_OUT": "HP%",
}

ENTRY_KEYS = ("name", "grade", "attribute", "class", "base_atk", "base_def", "base_hp",
              "base_crit_rate", "base_crit_dmg", "base_weak_ego_dmg_rate", "node_50", "node_60")

BASE_TABLE = "char_base@char_base.json"
COMBATANT_TABLE = "char_base@char_combatant.json"
LEVEL_TABLE = "char_base@combatant_level.json"
ASCEND_TABLE = "char_base@combatant_ascend.json"
NODE_EFFECT_TABLE = "potential_node@potential_node_effect.json"
NODE_LAYOUT_TABLE = "potential_node@potential_node.json"
NODE_TYPE_TABLE = "potential_node_type_define@potential_node_type_define.json"

_NODE_ID = re.compile(r"^(\d+)_(\d+)_\d+_\d+$")

# Stats in CHARACTERS are stored at this level/ascend (matches scaling.py / optimizer).
_CANONICAL_LEVEL = 60
_CANONICAL_ASCEND = 5


def _parse_growth_material(growth_id: str) -> tuple[str, str]:
    parts = growth_id.split("_")
    if len(parts) != 3 or parts[0] != "c":
        raise ValueError(f"unexpected link_char_growth_material_id: {growth_id!r}")
    klass = GROWTH_CLASS_TO_CLASS.get(parts[1])
    if klass is None:
        raise ValueError(f"unmapped class key in {growth_id!r}: {parts[1]!r}")
    attr = GROWTH_COLOR_TO_ATTRIBUTE.get(parts[2])
    if attr is None:
        raise ValueError(f"unmapped color key in {growth_id!r}: {parts[2]!r}")
    return klass, attr


def _effect_nodes(output_dir: Path, res_id: int) -> dict[str, str]:
    """The two recorded potential nodes, read from the effect rows the game actually applies."""
    found: dict[str, str] = {}
    for row in table(NODE_EFFECT_TABLE, output_dir):
        row_id = str(row.get("id", ""))
        if not row_id.startswith(f"{res_id}_") or row.get("node_type") != "NODE_STAT_ADD":
            continue
        match = _NODE_ID.match(row_id)
        if match is None:
            continue
        key = NODE_SLOTS.get(int(match.group(2)))
        label = NODE_STAT_TO_LABEL.get(row.get("link_stat_list_id", ""))
        if key and label:
            found.setdefault(key, label)
    return found


def _layout_nodes(output_dir: Path, res_id: int) -> dict[str, str]:
    """
    The same two nodes, read from the tree layout instead.

    The layout says which node type sits in each slot, and the type says which stat it grants. It is
    the only source for a character the effect table has not caught up with, but it disagrees with the
    effect rows across the original 10xx roster, so it is a fallback rather than the answer.
    """
    types = table_by_id(NODE_TYPE_TABLE, output_dir)
    found: dict[str, str] = {}
    for row in table(NODE_LAYOUT_TABLE, output_dir):
        key = NODE_LAYOUT_SLOTS.get(str(row.get("node_num", "")))
        if key is None or str(row.get("link_char_combatant_id")) != str(res_id):
            continue
        stat = types.get(str(row.get("link_potential_node_type_define_id")), {}).get("link_stat_list_id", "")
        label = NODE_STAT_TO_LABEL.get(stat)
        if label:
            found.setdefault(key, label)
    return found


def resolve_nodes(output_dir: Path, res_id: int) -> tuple[dict[str, str | None], bool]:
    """
    The stat each of a character's two recorded potential nodes grants.

    Args:
        output_dir: Root of the unpacked client.
        res_id: Combatant res_id.

    Returns:
        `node_50` and `node_60`, each a stat label or None, and whether the tree layout had to be
        used because the effect rows were missing. The layout agrees with the effect rows for every
        character released since 30047, but it is the weaker source, so the caller should say so.
    """
    found = _effect_nodes(output_dir, res_id)
    if len(found) == len(NODE_SLOTS):
        return {key: found.get(key) for key in NODE_SLOTS.values()}, False
    layout = _layout_nodes(output_dir, res_id)
    merged = {key: found.get(key) or layout.get(key) for key in NODE_SLOTS.values()}
    return merged, bool(layout) and merged != {key: found.get(key) for key in NODE_SLOTS.values()}


def _build_level_scaling(level_rows: list[dict]) -> dict[str, dict[str, dict]]:
    """Return {group: {level_str: {ATK, DEF, HP}}} with cumulative deltas."""
    from collections import defaultdict
    by_group: dict[str, list] = defaultdict(list)
    for row in level_rows:
        by_group[row["group"]].append(row)
    out: dict[str, dict[str, dict]] = {}
    for group, rows in by_group.items():
        rows.sort(key=lambda r: int(r["level"]))
        cum_atk = cum_def = cum_hp = 0
        out[group] = {}
        for r in rows:
            cum_atk += int(r["stat1_value"])
            cum_def += int(r["stat2_value"])
            cum_hp += int(r["stat3_value"])
            out[group][r["level"]] = {"ATK": cum_atk, "DEF": cum_def, "HP": cum_hp}
    return out


def _build_ascend_scaling(ascend_rows: list[dict]) -> dict[str, list[dict]]:
    """Return {group: [cumulative {ATK, DEF, HP} per ascend index 0..N]}."""
    from collections import defaultdict
    by_group: dict[str, list] = defaultdict(list)
    for row in ascend_rows:
        by_group[row["group"]].append(row)
    out: dict[str, list[dict]] = {}
    for group, rows in by_group.items():
        rows.sort(key=lambda r: int(r["ascend"]))
        cum_atk = cum_def = cum_hp = 0
        out[group] = []
        for r in rows:
            cum_atk += int(r["stat1_value"])
            cum_def += int(r["stat2_value"])
            cum_hp += int(r["stat3_value"])
            out[group].append({"ATK": cum_atk, "DEF": cum_def, "HP": cum_hp})
    return out


def _scale_stats(
    base_atk: int, base_def: int, base_hp: int,
    level_group: str, ascend_group: str,
    level_scaling: dict, ascend_scaling: dict,
    level: int = _CANONICAL_LEVEL,
    ascend: int = _CANONICAL_ASCEND,
) -> tuple[int, int, int]:
    """Return (atk, def, hp) scaled to the requested level/ascend."""
    lvl_table = level_scaling.get(level_group, {})
    lvl_bonus = lvl_table.get(str(level), {"ATK": 0, "DEF": 0, "HP": 0})

    asc_table = ascend_scaling.get(ascend_group, [])
    if asc_table:
        eff_ascend = max(0, min(ascend, len(asc_table) - 1))
        asc_bonus = asc_table[eff_ascend]
    else:
        asc_bonus = {"ATK": 0, "DEF": 0, "HP": 0}

    return (
        base_atk + lvl_bonus["ATK"] + asc_bonus["ATK"],
        base_def + lvl_bonus["DEF"] + asc_bonus["DEF"],
        base_hp + lvl_bonus["HP"] + asc_bonus["HP"],
    )


@lru_cache(maxsize=None)
def _scaling_tables(root: str) -> tuple[dict, dict]:
    """Both growth tables for one unpacked client, built once and reused across res_ids."""
    output_dir = Path(root)
    return (
        _build_level_scaling(table(LEVEL_TABLE, output_dir)),
        _build_ascend_scaling(table(ASCEND_TABLE, output_dir)),
    )


def extract(output_dir: Path, res_id: int) -> tuple[dict, list[str]]:
    """
    Build a CHARACTERS entry for one combatant.

    Args:
        output_dir: Root of the unpacked client.
        res_id: Combatant res_id.

    Returns:
        The entry, with every key CHARACTERS uses, and the names of the fields a human still has to
        settle. `node_50` / `node_60` land there when the client has no effect rows for them, whether
        they came back empty or were filled in from the weaker tree layout.

    Raises:
        KeyError: If the combatant or its English name is missing from the client.
        ValueError: If its growth material or rarity is one this script does not know.
    """
    level_scaling, ascend_scaling = _scaling_tables(str(output_dir))
    nodes, from_layout = resolve_nodes(output_dir, res_id)

    base_row = table_by_id(BASE_TABLE, output_dir).get(str(res_id))
    if base_row is None:
        raise KeyError(f"res_id {res_id} not found in {BASE_TABLE}")
    stat_row = table_by_id(COMBATANT_TABLE, output_dir).get(str(res_id))
    if stat_row is None:
        raise KeyError(f"res_id {res_id} not found in {COMBATANT_TABLE}")

    name = text_index(output_dir).get(f"char_base@name@{res_id}")
    if name is None:
        raise KeyError(f"no English name for res_id {res_id} in text.json")

    klass, attribute = _parse_growth_material(base_row["link_char_growth_material_id"])

    grade = RARITY_TO_GRADE.get(base_row["rarity"])
    if grade is None:
        raise ValueError(f"unmapped rarity: {base_row['rarity']!r}")

    raw_atk = int(stat_row["s_atk"])
    raw_def = int(stat_row["s_def"])
    raw_hp = int(stat_row["s_hp"])
    level_group = stat_row["link_combatant_level_group"]
    ascend_group = stat_row["link_combatant_ascend_group"]

    scaled_atk, scaled_def, scaled_hp = _scale_stats(
        raw_atk, raw_def, raw_hp,
        level_group, ascend_group,
        level_scaling, ascend_scaling,
    )

    entry = {
        "name": name,
        "grade": grade,
        "attribute": attribute,
        "class": klass,
        "base_atk": scaled_atk,
        "base_def": scaled_def,
        "base_hp": scaled_hp,
        "base_crit_rate": float(stat_row["s_cri"]),
        "base_crit_dmg": float(stat_row["s_cri_dmg_rate"]),
        "base_weak_ego_dmg_rate": float(stat_row["s_weak_ego_dmg_rate"]),
        **nodes,
    }
    unfilled = [key for key in NODE_SLOTS.values() if nodes[key] is None]
    if from_layout:
        unfilled += [key for key in NODE_SLOTS.values() if nodes[key] is not None]
    return entry, unfilled


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python scripts/extract_combatant.py <output_dir> <res_id> [<res_id> ...]",
              file=sys.stderr)
        return 2
    output_dir = Path(argv[1])
    for raw in argv[2:]:
        res_id = int(raw)
        entry, unfilled = extract(output_dir, res_id)
        print(format_entry(res_id, entry, ENTRY_KEYS, f"TODO: confirm {', '.join(unfilled)}" if unfilled else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Auto-extract a partner entry for api/game_data/partners.py::PARTNERS.

Name, grade, class, ego name and cost, and the unconditional stat bonuses all come straight out of
the client. The passive description is templated by comparing its five limit break texts: a number
that is the same at every limit break stays as it is, and one that changes becomes a placeholder.
A placeholder whose five values match a stat bonus is named after that stat, which is how `{ATK%}`
gets its name. Anything left over is named `V1`, `V2` and so on for a human to rename.

Usage:
    python scripts/extract_partner.py <output_dir> <res_id> [<res_id> ...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.client_db import table_by_id, text_index  # noqa: E402
from entry_format import format_entry  # noqa: E402

GROWTH_MATERIAL_TO_CLASS = {
    "s_controller": "Controller",
    "s_hunter": "Hunter",
    "s_ranger": "Ranger",
    "s_striker": "Striker",
    # The client renamed "s_knight" to "s_vanguard" in late September 2026. The old key stays for older dumps.
    "s_knight": "Vanguard",
    "s_vanguard": "Vanguard",
    "s_psionic": "Psionic",
}

RARITY_TO_GRADE = {
    "RARITY_SSR": 5,
    "RARITY_SR": 4,
    "RARITY_R": 3,
}

# `opt_multiple_link` on an EFF_STAT_UP_PARTNER row reads "<stat key>_<value>". These three are the
# only stat keys any partner passive in the client uses.
NB_STAT_TO_LABEL = {
    "atk_inc_rate": "ATK%",
    "def_inc_rate": "DEF%",
    "hp_inc_rate": "HP%",
}

# Partner passives are curated at five limit breaks, E0 through E4.
LIMIT_BREAKS = 5

# Class 1 rows are the half of a passive that always applies. Class 2 rows are the extra it grants
# when the assigned combatant matches its class, and are covered by the same display text.
UNCONDITIONAL_CLASS = "1"
CONDITIONAL_CLASS = "2"

# Newer partners get their own passive shard alongside the shared one, so both have to be read.
PASSIVE_SHARDS = "partner_passive*@partner_passive.json"
NB_EFF_SHARDS = "partner_passive*@nb_eff.json"

PARTNER_BASE_TABLE = "partner_base@char_base.json"
PARTNER_DETAIL_TABLE = "partner_base@char_partner.json"
PARTNER_CARD_TABLE = "card(partner)@card.json"
PARTNER_CARD_EFFECT_TABLE = "card(partner)@skill_eff.json"

# What an ego costs when the client has no card row to read it from. Most SSR egos cost 3.
DEFAULT_EGO_COST = 3

ENTRY_KEYS = ("name", "grade", "class", "passive_name", "passive_desc", "values", "stats", "ego_name", "ego_cost", "ego_desc")

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_ID_TOKEN = re.compile(r"[\w.]+")
_STAT_OPTION = re.compile(r"(.+)_(-?\d+(?:\.\d+)?)")

# The client wraps numbers and keywords in its own display markup: <cc>16</> for a highlighted value
# and $Fracture$ for a keyword. Neither means anything outside its UI, and the curated table has
# neither, so both come off.
_MARKUP = re.compile(r"<[^>]*>")

# Keywords read "$Fracture$", sometimes with a variant suffix as in "$Virutoxin#1$". Only the name
# itself survives into the curated table.
_KEYWORD = re.compile(r"\$([^$]*)\$")
_KEYWORD_VARIANT = re.compile(r"#\d+$")

# An ego description reads "#result_ev_0# $AP$", where the trailing number picks an entry out of the
# card's own list of effects and the value comes from that effect.
_RUNTIME_VALUE = re.compile(r"#result_\w*?_?(\d+)#")

# "#during_ev_0_0#" is the value of an effect that only runs while the ego is active. The first
# number picks the linked effect, the second picks which of its during-effect slots to read.
_DURING_VALUE = re.compile(r"#during_ev_(\d+)_(\d+)#")

# Tokens that name something rather than carry a value. The table words this the same way throughout.
_NAMED_TOKENS = {"#own_char#": "the assigned Combatant"}

# Anything still fenced in hashes after all that has no value to read from, so it needs a human.
_ANY_TOKEN = re.compile(r"#[^#\s]+#")

# The client uses both typographic single quotes where an apostrophe belongs.
_APOSTROPHES = {"\u2018": "'", "\u2019": "'"}

_SHARD_CACHE: dict[tuple[str, str], dict[str, dict]] = {}


def _shard_index(db: Path, pattern: str) -> dict[str, dict]:
    """
    Rows from every client file matching `pattern`, keyed by id.

    Newer partners get their own shard beside the shared table, so a lookup has to span all of them.

    Args:
        db: The client's `db` folder.
        pattern: A glob over that folder.

    Returns:
        id -> row, cached so repeated lookups do not re-read the files.
    """
    key = (str(db), pattern)
    if key not in _SHARD_CACHE:
        index: dict[str, dict] = {}
        for path in sorted(db.glob(pattern)):
            index.update(table_by_id(path.name, db.parent))
        _SHARD_CACHE[key] = index
    return _SHARD_CACHE[key]


def resolve_ego_description(description: str, card: dict, output_dir: Path) -> tuple[str, bool]:
    """
    Fill an ego description's placeholders in from the card's own effect rows.

    `#result_ev_0#` means "the value of the first effect this card links to". Licinia's hand written
    entry reads "Gain 1 AP" and "3 Paralytic Poison", which is exactly what her card's two effects say.

    Args:
        description: The normalised description, still holding its placeholders.
        card: The card row, whose `link_skill_eff_id` lists the effects in order.
        output_dir: Root of the unpacked client.

    Returns:
        The description with every placeholder it could fill in replaced, and whether any are left.
    """
    effects = table_by_id(PARTNER_CARD_EFFECT_TABLE, output_dir)
    linked = [effects.get(eff_id, {}) for eff_id in _ID_TOKEN.findall(card.get("link_skill_eff_id", ""))]

    def effect_value(match: re.Match) -> str:
        index = int(match.group(1))
        value = linked[index].get("eff_value") if index < len(linked) else None
        return value or match.group(0)

    def during_value(match: re.Match) -> str:
        index, slot = int(match.group(1)), int(match.group(2))
        if index >= len(linked):
            return match.group(0)
        during = linked[index].get(f"during_eff_{slot}_link_skill_eff_id", "none")
        return effects.get(during, {}).get("eff_value") or match.group(0)

    filled = _RUNTIME_VALUE.sub(effect_value, description)
    filled = _DURING_VALUE.sub(during_value, filled)
    for token, replacement in _NAMED_TOKENS.items():
        filled = filled.replace(token, replacement)
    return filled, bool(_ANY_TOKEN.search(filled))


def _text(catalogue: dict[str, str], key: str) -> str | None:
    """One entry from the text catalogue, normalised, or None when the key is not in it."""
    raw = catalogue.get(key)
    return normalise(raw) if raw else None


def normalise(text: str) -> str:
    """
    Turn a client description into the plain text the curated table holds.

    The client separates clauses with `<br>`, highlights numbers with `<cc>...</>`, marks keywords by
    wrapping them in `$`, and uses a typographic apostrophe. None of that survives into `partners.py`.

    Args:
        text: A raw description from the text catalogue.

    Returns:
        The same text with line breaks as newlines and the markup removed.
    """
    for quote, plain in _APOSTROPHES.items():
        text = text.replace(quote, plain)
    flat = _MARKUP.sub("", text.replace("<br>", "\n"))
    return _KEYWORD.sub(lambda match: _KEYWORD_VARIANT.sub("", match.group(1)), flat).strip()


def _number(text: str) -> float | int:
    """A number from the client's text, kept as an int unless it was written with a decimal point."""
    value = float(text)
    return value if "." in text else int(value)


def passive_stats(db: Path, res_id: int) -> dict[str, tuple]:
    """
    The stat bonuses a partner's passive grants unconditionally, one value per limit break.

    These are read from the structured effect rows rather than the display text, so they carry the
    right stat name and need no parsing of prose.

    Args:
        db: The client's `db` folder.
        res_id: Partner res_id.

    Returns:
        Stat label -> five values, E0 first. Empty when the client has no effect rows for the partner.
    """
    passives = _shard_index(db, PASSIVE_SHARDS)
    effects = _shard_index(db, NB_EFF_SHARDS)
    collected: dict[str, list] = {}
    for level in range(1, LIMIT_BREAKS + 1):
        row = passives.get(f"{res_id}_c{UNCONDITIONAL_CLASS}_lv{level}")
        if row is None:
            continue
        for eff_id in _ID_TOKEN.findall(row.get("link_nb_eff_id", "")):
            effect = effects.get(eff_id)
            if effect is None or effect.get("nb_eff") != "EFF_STAT_UP_PARTNER":
                continue
            match = _STAT_OPTION.fullmatch(effect.get("opt_multiple_link", ""))
            if match is None:
                continue
            label = NB_STAT_TO_LABEL.get(match.group(1))
            if label:
                collected.setdefault(label, []).append(_number(match.group(2)))
    return {label: tuple(values) for label, values in collected.items() if len(values) == LIMIT_BREAKS}


def templatize_descriptions(descriptions: list[str], stats: dict[str, tuple]) -> tuple[str, dict[str, tuple]]:
    """
    Collapse a passive's five limit break texts into one template plus the values behind it.

    Args:
        descriptions: The passive text at each limit break, E0 first.
        stats: Stat label -> five values, used to give a placeholder a meaningful name.

    Returns:
        The templated description and its placeholder values.

    Raises:
        ValueError: If there are not five descriptions, or they differ anywhere other than in their numbers.
    """
    if len(descriptions) != LIMIT_BREAKS:
        raise ValueError(f"expected {LIMIT_BREAKS} descriptions, got {len(descriptions)}")
    literals = [_NUMBER.split(text) for text in descriptions]
    numbers = [_NUMBER.findall(text) for text in descriptions]
    if len({tuple(parts) for parts in literals}) != 1:
        raise ValueError("descriptions differ outside their numbers, so they cannot share one template")

    values: dict[str, tuple] = {}
    tokens: list[str] = []
    for column in range(len(numbers[0])):
        column_values = tuple(_number(numbers[level][column]) for level in range(LIMIT_BREAKS))
        if len(set(column_values)) == 1:
            tokens.append(numbers[0][column])
            continue
        name = next((label for label, v in stats.items() if tuple(v) == column_values and label not in values), None)
        if name is None:
            name = f"V{len(values) + 1}"
        values[name] = column_values
        tokens.append(f"{{{name}}}")

    parts = literals[0]
    rendered = parts[0]
    for token, part in zip(tokens, parts[1:]):
        rendered += token + part
    return rendered, values


def partner_row(db: Path, res_id: int) -> dict | None:
    """
    A partner's row from `partner_base@char_partner.json`.

    Args:
        db: The client's `db` folder.
        res_id: Partner res_id.

    Returns:
        The row, or None when the client does not list the partner there yet. A partner can go live
        before that table catches up - Emilie arrived that way - so callers have to handle None.
    """
    return table_by_id(PARTNER_DETAIL_TABLE, db.parent).get(str(res_id))


def passive_rows(db: Path, res_id: int, passive_class: str = UNCONDITIONAL_CLASS) -> list[dict | None]:
    """
    A partner's five passive rows for one of its halves, E0 first.

    Args:
        db: The client's `db` folder.
        res_id: Partner res_id.
        passive_class: "1" for the half that always applies, "2" for the class matching bonus.

    Returns:
        One row per limit break, None where the client has no row for it.
    """
    passives = _shard_index(db, PASSIVE_SHARDS)
    return [passives.get(f"{res_id}_c{passive_class}_lv{level}") for level in range(1, LIMIT_BREAKS + 1)]


def _passive_description(db: Path, text: dict[str, str], res_id: int, stats: dict[str, tuple]) -> tuple[str, dict[str, tuple], bool]:
    """
    The passive description with its changing numbers turned into placeholders.

    Args:
        db: The client's `db` folder.
        text: The English text catalogue.
        res_id: Partner res_id.
        stats: Stat bonuses, used to name the placeholders.

    Returns:
        The description, its values, and the fields a human still has to deal with. Where the five
        texts cannot share one template the E0 text is returned verbatim, which is right at E0 and
        wrong at the other four, so that counts as unfilled.
    """
    # The curated table holds both halves of a passive, in order: what always applies, then the extra
    # a matching combatant class earns. Licinia's hand written entry is exactly those two joined up.
    texts = []
    for always, matching in zip(passive_rows(db, res_id, UNCONDITIONAL_CLASS), passive_rows(db, res_id, CONDITIONAL_CLASS)):
        clauses = [text.get(row.get("description", "")) for row in (always, matching) if row]
        clauses = [normalise(clause) for clause in clauses if clause]
        if not clauses:
            return "TODO: passive desc", {}, ["passive_desc", "values"]
        texts.append("\n".join(clauses))
    try:
        desc, values = templatize_descriptions(texts, stats)
    except ValueError as exc:
        print(f"  [warn] {res_id}: {exc}; keeping the E0 text with no placeholders", file=sys.stderr)
        return texts[0], {}, ["passive_desc", "values"]
    # A `V1` style name means the value matched no stat bonus, so it still needs a meaningful name.
    unnamed = ["values"] if any(name.startswith("V") and name[1:].isdigit() for name in values) else []
    return desc, values, unnamed


def extract(output_dir: Path, res_id: int) -> tuple[dict, list[str]]:
    """
    Build a PARTNERS entry for one partner.

    Args:
        output_dir: Root of the unpacked client.
        res_id: Partner res_id.

    Returns:
        The entry, with every key PARTNERS uses, and the names of the fields the client could not
        supply. Those fields still hold something renderable so the entry stays valid Python, but the
        list is the authority on what a human still has to fill in.

    Raises:
        KeyError: If the partner or its English name is missing from the client.
        ValueError: If its growth material or rarity is one this script does not know.
    """
    db = output_dir / "db"
    text = text_index(output_dir)

    base_row = table_by_id(PARTNER_BASE_TABLE, output_dir).get(str(res_id))
    if base_row is None:
        raise KeyError(f"res_id {res_id} missing from {PARTNER_BASE_TABLE}")

    name = text.get(f"char_base@name@{res_id}")
    if name is None:
        raise KeyError(f"no English name for partner res_id {res_id}")

    growth = base_row.get("link_char_growth_material_id", "")
    klass = GROWTH_MATERIAL_TO_CLASS.get(growth)
    if klass is None:
        raise ValueError(f"unmapped growth material: {growth!r}")

    grade = RARITY_TO_GRADE.get(base_row.get("rarity", ""))
    if grade is None:
        raise ValueError(f"unmapped rarity: {base_row.get('rarity')!r}")

    unfilled: list[str] = []

    def supplied(key: str, value, placeholder):
        """Take the client's value, or record the field as needing a human and use a placeholder."""
        if value:
            return value
        unfilled.append(key)
        return placeholder

    # The card and passive ids follow "p_<res_id>" and "tactic_passive_<res_id>". Falling back to
    # those lets a partner the detail table has not caught up with still resolve its ego and passive.
    row = partner_row(db, res_id) or {}
    card_id = row.get("link_card_id") or f"p_{res_id}"
    passive_group = row.get("link_partner_passive_group") or f"tactic_passive_{res_id}"
    card = table_by_id(PARTNER_CARD_TABLE, output_dir).get(card_id, {})
    cost = card.get("cost", "")

    stats = passive_stats(db, res_id)
    passive_desc, values, passive_unfilled = _passive_description(db, text, res_id, stats)
    unfilled += passive_unfilled

    ego_desc = _text(text, f"card@desc@{card_id}")
    if ego_desc:
        ego_desc, leftover = resolve_ego_description(ego_desc, card, output_dir)
        if leftover:
            unfilled.append("ego_desc")

    return {
        "name": name,
        "grade": grade,
        "class": klass,
        "passive_name": supplied("passive_name", _text(text, f"partner_passive@name@{res_id}") or _text(text, f"partner_passive@name@{passive_group}"), "TODO: passive name"),
        "passive_desc": passive_desc,
        "values": values,
        "stats": supplied("stats", stats, {}),
        "ego_name": supplied("ego_name", _text(text, f"card@name@{card_id}"), "TODO: ego name"),
        "ego_cost": int(cost) if cost.isdigit() else supplied("ego_cost", None, DEFAULT_EGO_COST),
        "ego_desc": supplied("ego_desc", ego_desc, "TODO: ego desc"),
    }, unfilled


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python scripts/extract_partner.py <output_dir> <res_id> [<res_id> ...]",
              file=sys.stderr)
        return 2
    output_dir = Path(argv[1])
    for raw in argv[2:]:
        res_id = int(raw)
        entry, unfilled = extract(output_dir, res_id)
        print(format_entry(res_id, entry, ENTRY_KEYS, f"TODO: review {', '.join(unfilled)}" if unfilled else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

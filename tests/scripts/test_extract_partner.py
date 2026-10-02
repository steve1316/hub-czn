"""Tests for scripts/extract_partner.py.

Name, grade, class, ego cost and the unconditional stat bonuses come straight from the client, so
they are checked against the curated table. The passive description is templated from its five limit
break texts, and that templating is checked on its own because it is the only guessing the script does.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import extract_partner  # noqa: E402

from api.client_db import client_output_dir, have_client_db, have_client_text  # noqa: E402
from api.game_data.partners import PARTNERS  # noqa: E402

OUTPUT_DIR = client_output_dir()

needs_client = pytest.mark.skipif(
    not (have_client_db() and have_client_text()),
    reason="game client DB or its text catalogue not available",
)

# Partners whose `stats` cannot be derived because the client does not list their passive's effect rows yet. Emilie (30118)
# was one until late September 2026, when the client caught up and matched her hand-written values exactly.
STATS_EXCEPTIONS: set[int] = set()


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Templating a passive description


def test_a_placeholder_is_named_after_the_stat_it_matches():
    descs = [f"Increase the assigned Combatant's Attack by {v}%." for v in (16, 18, 20, 22, 24)]
    desc, values = extract_partner.templatize_descriptions(descs, {"ATK%": (16, 18, 20, 22, 24)})
    assert desc == "Increase the assigned Combatant's Attack by {ATK%}%."
    assert values == {"ATK%": (16, 18, 20, 22, 24)}


def test_numbers_that_do_not_change_are_left_alone():
    descs = [f"+10% to Critical Chance.\nAttack +{v}%." for v in (16, 18, 20, 22, 24)]
    desc, values = extract_partner.templatize_descriptions(descs, {"ATK%": (16, 18, 20, 22, 24)})
    assert desc == "+10% to Critical Chance.\nAttack +{ATK%}%."
    assert values == {"ATK%": (16, 18, 20, 22, 24)}


def test_an_unrecognised_value_gets_a_numbered_placeholder():
    descs = [f"Deal {v}% extra damage." for v in (25, 32, 38, 44, 50)]
    desc, values = extract_partner.templatize_descriptions(descs, {})
    assert desc == "Deal {V1}% extra damage."
    assert values == {"V1": (25, 32, 38, 44, 50)}


def test_a_named_and_an_unnamed_value_can_share_one_description():
    descs = [f"Attack +{a}%, then deal {b}% more." for a, b in zip((16, 18, 20, 22, 24), (25, 32, 38, 44, 50))]
    desc, values = extract_partner.templatize_descriptions(descs, {"ATK%": (16, 18, 20, 22, 24)})
    assert desc == "Attack +{ATK%}%, then deal {V2}% more."
    assert values == {"ATK%": (16, 18, 20, 22, 24), "V2": (25, 32, 38, 44, 50)}


def test_decimals_stay_decimals():
    descs = [f"Heal {v}%." for v in (1.5, 2.0, 2.5, 3.0, 3.5)]
    _desc, values = extract_partner.templatize_descriptions(descs, {})
    assert values == {"V1": (1.5, 2.0, 2.5, 3.0, 3.5)}


def test_descriptions_that_differ_outside_their_numbers_are_rejected():
    # Templating these anyway would silently produce a description that is wrong at four of the five
    # limit breaks, which no test downstream would catch.
    descs = ["Attack +16%.", "Attack +18%.", "Attack +20%.", "Defense +22%.", "Attack +24%."]
    with pytest.raises(ValueError):
        extract_partner.templatize_descriptions(descs, {})


def test_the_wrong_number_of_limit_breaks_is_rejected():
    with pytest.raises(ValueError):
        extract_partner.templatize_descriptions(["Attack +16%.", "Attack +18%."], {})


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Against the real client


@needs_client
def test_passive_stats_reproduce_every_curated_partner():
    # Every `stats` block in PARTNERS was curated by hand. Deriving them all again from the client is
    # what says the derivation can be trusted to write a new entry unattended.
    wrong = []
    for res_id, partner in PARTNERS.items():
        if not partner or res_id in STATS_EXCEPTIONS:
            continue
        want = {label: tuple(values) for label, values in (partner.get("stats") or {}).items()}
        got = extract_partner.passive_stats(OUTPUT_DIR / "db", res_id)
        if got != want:
            wrong.append((res_id, partner["name"], got, want))
    assert not wrong, f"derived stats disagree with the curated table: {wrong}"


@needs_client
def test_the_stats_exceptions_really_are_underivable():
    # An exception is only justified while the client still cannot supply the entry. Once it can,
    # this fails and the entry should go back to being derived like every other one.
    for res_id in STATS_EXCEPTIONS:
        assert not extract_partner.passive_stats(OUTPUT_DIR / "db", res_id), (
            f"{res_id} can be derived from the client now, so it no longer needs an exception"
        )


@needs_client
def test_partner_row_is_none_when_the_client_does_not_list_the_partner():
    # Emilie went live before partner_base@char_partner listed her, so callers must handle None
    # rather than get a fabricated row back.
    assert extract_partner.partner_row(OUTPUT_DIR / "db", 999999) is None
    assert extract_partner.partner_row(OUTPUT_DIR / "db", 30116) is not None


@needs_client
def test_ivy_1025_class_and_grade():
    """Ivy: Psionic / grade 5 - anchor for s_psionic to Psionic, RARITY_SSR to 5."""
    entry, _ = extract_partner.extract(OUTPUT_DIR, 1025)
    expected = PARTNERS[1025]
    assert entry["name"] == expected["name"]
    assert entry["class"] == expected["class"]
    assert entry["grade"] == expected["grade"]


@needs_client
def test_solia_1058_class_and_grade():
    """Solia: Ranger / grade 5 - anchor for s_ranger to Ranger."""
    entry, _ = extract_partner.extract(OUTPUT_DIR, 1058)
    expected = PARTNERS[1058]
    assert entry["name"] == expected["name"]
    assert entry["class"] == expected["class"]


@needs_client
def test_arwen_20001_class_and_grade():
    """Arwen: Controller / grade 4 - anchor for s_controller to Controller, RARITY_SR to 4."""
    entry, _ = extract_partner.extract(OUTPUT_DIR, 20001)
    expected = PARTNERS[20001]
    assert entry["class"] == expected["class"]
    assert entry["grade"] == expected["grade"]


@needs_client
def test_clara_30095_emits_required_fields():
    """Clara: should emit every PARTNERS field, whatever the client could fill in."""
    entry, _ = extract_partner.extract(OUTPUT_DIR, 30095)
    assert set(extract_partner.ENTRY_KEYS).issubset(entry.keys())
    assert entry["name"] == "Clara"
    # Clara is a Knight-class partner per partner_base@char_partner.json
    assert entry["class"] == "Vanguard"


@needs_client
def test_every_extracted_passive_renders_with_no_leftover_placeholder():
    # test_partner_data's placeholder check is the gate a new entry has to pass. Catching it here
    # means the script never writes an entry that breaks the suite.
    checked = 0
    for res_id, partner in PARTNERS.items():
        if not partner:
            continue
        try:
            entry, _ = extract_partner.extract(OUTPUT_DIR, res_id)
        except (KeyError, ValueError):
            continue  # Not every partner the app knows is still in the client.
        placeholders = set(re.findall(r"\{([^}]+)\}", entry["passive_desc"]))
        assert placeholders <= set(entry["values"]), f"{res_id} {entry['name']}: {placeholders - set(entry['values'])}"
        checked += 1
    assert checked > 20, f"only {checked} partners were checked, so this is not covering much"


# //////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////
# Cleaning up client display text


def test_normalise_removes_the_clients_display_markup():
    raw = "Increase Attack by <cc>16</>%.<br>When $Fracture$ is applied, inflict $Virutoxin#1$."
    assert extract_partner.normalise(raw) == "Increase Attack by 16%.\nWhen Fracture is applied, inflict Virutoxin."


@pytest.mark.parametrize("quote", ["\u2018", "\u2019"])
def test_normalise_replaces_both_typographic_apostrophes(quote):
    # The client uses the opening quote as an apostrophe in some strings and the closing one in others.
    assert extract_partner.normalise(f"the Combatant{quote}s Attack") == "the Combatant's Attack"


@needs_client
def test_ego_descriptions_resolve_every_value_the_client_can_supply():
    # An ego description arrives full of tokens the client fills in at battle time. Anything left
    # unresolved has to be reported rather than shipped, or it reaches the UI as "#during_ev_0_0#".
    for res_id, partner in PARTNERS.items():
        if not partner:
            continue
        try:
            entry, unfilled = extract_partner.extract(OUTPUT_DIR, res_id)
        except (KeyError, ValueError):
            continue
        assert ("#" in entry["ego_desc"]) == ("ego_desc" in unfilled), (
            f"{res_id} {entry['name']}: unresolved token not reported - {entry['ego_desc']!r}"
        )


@needs_client
def test_a_during_effect_value_is_read_from_the_cards_own_effect():
    # Eunie's ego reads "#during_ev_0_0# Ammo Transfer", which is the during-effect of her card's
    # first linked effect. Leaving it unresolved would put the raw token in front of the user.
    entry, _ = extract_partner.extract(OUTPUT_DIR, 30114)
    assert "1 Ammo Transfer for each defeated" in entry["ego_desc"]
    assert "#" not in entry["ego_desc"]


@needs_client
def test_licinia_is_reproduced_from_the_client():
    # Licinia was written by hand from the game. Deriving her again and landing on the same words is
    # the check that the markup stripping, the clause ordering and the ego values are all right.
    entry, _ = extract_partner.extract(OUTPUT_DIR, 30116)
    assert entry["ego_desc"] == "Gain 1 AP\n3 Paralytic Poison to all enemies"
    assert entry["ego_name"] == "Blossoming Venom"
    assert entry["passive_name"] == "Poison-Laced Atonement"
    # Both halves of the passive, in the order the curated entry has them.
    assert entry["passive_desc"].startswith("Increase the assigned Combatant's Attack by {ATK%}%.\nWhen Fracture is applied")
    assert "inflict 1 Virutoxin on the target." in entry["passive_desc"]


@needs_client
def test_licinia_renders_back_to_her_in_game_numbers_at_e0():
    # The curated entry hardcodes "+10%" and "4%", which are the E0 values. Substituting the derived
    # placeholders at E0 has to land on exactly those, or the templating has shifted something.
    entry, _ = extract_partner.extract(OUTPUT_DIR, 30116)
    rendered = entry["passive_desc"]
    for name, values in entry["values"].items():
        rendered = rendered.replace("{" + name + "}", str(values[0]))
    assert "Attack by 16%." in rendered
    assert "+10% to Critical Chance" in rendered
    assert "by 4% (max 4 stacks)" in rendered

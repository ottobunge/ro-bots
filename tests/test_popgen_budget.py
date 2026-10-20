"""Budget-tiered builds + the farmer archetype (criterion: competent players).

The operator directive: some players go for expensive builds, others for
cheaper ones, and some create characters for farming. The budget tier selects
the sidecar equipment_order prefix; the farmer archetype flips the playstyle
to 'farming' over the item-yield-focused class paths.
"""

import json
from typing import Any

import pytest

from robots.app.agent_runtime import load_manifest
from robots.popgen import (
    BUDGET_TIERS,
    FARMER_BUILDS,
    PopulationSpec,
    budget_tier_legs,
    generate_population,
)
from tests.test_popgen import make_spec

NOVICE_ORDER: list[dict[str, Any]] = [
    {"order": 1, "id": 2302, "name": "Cotton Shirt [1]", "price_z": "given at creation (NPC 10z)"},
    {"order": 2, "id": 1201, "name": "Knife [3]", "price_z": 50},
    {
        "order": 3,
        "id": 501,
        "name": "Red Potion",
        "price_z": "10z (iRO NPC) / 50z (server item_db Buy)",
    },
]
SPREAD_ORDER: list[dict[str, Any]] = [
    {"order": 1, "id": 1201, "name": "Knife [3]", "price_z": 50},
    {"order": 2, "id": 1103, "name": "Falchion", "price_z": 300},
    {"order": 3, "id": 1103, "name": "Expensive Blade", "price_z": 2000},
]


class TestBudgetTierLegs:
    def test_thrifty_takes_cheap_prefix(self) -> None:
        assert budget_tier_legs(SPREAD_ORDER, "thrifty") == [SPREAD_ORDER[0]]

    def test_standard_cuts_before_luxury(self) -> None:
        assert budget_tier_legs(SPREAD_ORDER, "standard") == SPREAD_ORDER[:2]

    def test_luxurious_keeps_everything(self) -> None:
        assert budget_tier_legs(SPREAD_ORDER, "luxurious") == SPREAD_ORDER

    def test_free_legs_never_break_the_prefix(self) -> None:
        # "given at creation"/quest legs have no numeric price: always affordable.
        assert budget_tier_legs(NOVICE_ORDER, "thrifty") == NOVICE_ORDER

    def test_unknown_tier_rejected(self) -> None:
        with pytest.raises(ValueError, match="budget tier"):
            budget_tier_legs(NOVICE_ORDER, "rich")


class TestSpecValidation:
    def test_bad_weights_rejected(self) -> None:
        with pytest.raises(ValueError, match="budget_tier_weights"):
            PopulationSpec(
                friend_groups=1,
                friends_per_group=(2, 2),
                solo_agents=0,
                seed=1,
                budget_tier_weights=(0.5, 0.5, 0.5),
            )

    def test_bad_farmer_share_rejected(self) -> None:
        with pytest.raises(ValueError, match="farmer_share"):
            PopulationSpec(
                friend_groups=1,
                friends_per_group=(2, 2),
                solo_agents=0,
                seed=1,
                farmer_share=1.5,
            )


class TestPopulationDistribution:
    def test_all_thrifty(self) -> None:
        pop = generate_population(make_spec(seed=7, budget_tier_weights=(1.0, 0.0, 0.0)))
        assert {p.budget_tier for p in pop.personas} == {"thrifty"}

    def test_all_luxurious(self) -> None:
        pop = generate_population(make_spec(seed=7, budget_tier_weights=(0.0, 0.0, 1.0)))
        assert {p.budget_tier for p in pop.personas} == {"luxurious"}

    def test_equal_weights_yield_every_tier(self) -> None:
        pop = generate_population(make_spec(seed=4, budget_tier_weights=(1 / 3, 1 / 3, 1 / 3)))
        assert len(pop.personas) >= 6
        assert {p.budget_tier for p in pop.personas} == set(BUDGET_TIERS)

    def test_tiers_deterministic(self) -> None:
        first = generate_population(make_spec(seed=3))
        second = generate_population(make_spec(seed=3))
        assert [p.budget_tier for p in first.personas] == [p.budget_tier for p in second.personas]

    def test_default_farmer_share_keeps_sidecar_playstyles(self) -> None:
        pop = generate_population(make_spec(seed=7))
        assert all(p.playstyle != "farming" for p in pop.personas)
        assert all(p.budget_tier in BUDGET_TIERS for p in pop.personas)


class TestFarmerArchetype:
    def test_full_farmer_share(self) -> None:
        pop = generate_population(make_spec(seed=7, farmer_share=1.0))
        assert pop.personas
        for persona in pop.personas:
            assert persona.playstyle == "farming"
            assert persona.build in FARMER_BUILDS

    def test_partial_farmer_share_is_deterministic(self) -> None:
        first = generate_population(make_spec(seed=5, farmer_share=0.5))
        second = generate_population(make_spec(seed=5, farmer_share=0.5))
        farmers = [p for p in first.personas if p.playstyle == "farming"]
        assert farmers
        assert {p.persona_id for p in farmers} == {
            p.persona_id for p in second.personas if p.playstyle == "farming"
        }
        non_farmers = [p for p in first.personas if p.playstyle != "farming"]
        assert all(p.build not in FARMER_BUILDS or p.playstyle != "farming" for p in non_farmers)


class TestArtifactIntegration:
    def test_persona_row_and_summary_carry_tiers(self) -> None:
        pop = generate_population(
            make_spec(seed=7, budget_tier_weights=(1.0, 0.0, 0.0), farmer_share=1.0)
        )
        row = pop.summary()["personas"][0]
        assert row["budget_tier"] == "thrifty"
        assert row["playstyle"] == "farming"
        summary_tiers = pop.summary()["budget_tiers"]
        assert summary_tiers["thrifty"] == len(pop.personas)
        assert sum(summary_tiers.values()) == len(pop.personas)
        assert pop.summary()["farmers"] == len(pop.personas)

    def test_manifest_rows_keep_exact_schema(self, tmp_path: Any) -> None:
        pop = generate_population(make_spec(seed=7, farmer_share=1.0))
        for row in pop.manifest["accounts"]:
            assert set(row) == {"persona_id", "account", "password", "char_name", "pincode"}
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(pop.manifest))
        entries = load_manifest(path)
        assert set(entries) == {p.persona_id for p in pop.personas}

"""Real ruleset catalogs retain unknown market prices in the build consumer."""

from pathlib import Path

import pytest

from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.mechanics_yaml import YamlMechanics
from robots.app.builds import BuildAuthor
from robots.society.models import Attitude, Playstyle, SocietyPersona


@pytest.mark.parametrize("ruleset", ["pre-re", "re"])
def test_real_catalog_unknown_prices_cannot_be_claimed_affordable(ruleset: str) -> None:
    mechanics = YamlMechanics(Path("rathena/db"), ruleset=ruleset)
    weapons = mechanics.items_for_slot("weapon")
    assert weapons
    assert all(item.price_tier is None for item in weapons)
    model = ScriptedDecisionModel(
        answers={
            "class_path": {"choice": "Swordsman"},
            "stat_emphasis": {"choice": "str"},
            "equip_ambition": {"score": 2.0},
        }
    )
    persona = SocietyPersona(
        persona_id="catalog-test",
        name="CatalogTest",
        playstyle=Playstyle.MELEE,
        attitude=Attitude.GRINDER,
        chattiness=0.4,
        level_band=(30, 60),
    )
    build = BuildAuthor(model).author_build(
        persona, "CatalogTest01", {"Swordsman": "melee"}, mechanics
    )
    assert build.equip_goals == {}
    assert model.calls == 1
    assert all(item.price_tier is None for item in mechanics.items_for_slot("weapon"))

"""Curated pre-renewal build templates + template-based authoring (ADR-009)."""

from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.builds import author_build_from_template
from robots.domain.build_templates import KNOWN_SLOTS, PLAYSTYLE_TEMPLATES, skill_name
from robots.society.models import Attitude, Playstyle, SocietyPersona

VALID_STATS = {"STR", "AGI", "VIT", "INT", "DEX", "LUK"}


def make_persona(playstyle: Playstyle) -> SocietyPersona:
    return SocietyPersona(
        persona_id=f"p-{playstyle.value}",
        name="Sable",
        playstyle=playstyle,
        attitude=Attitude.GRINDER,
        chattiness=0.4,
        level_band=(30, 99),
    )


# -- data integrity ---------------------------------------------------------


def test_every_playstyle_has_at_least_two_templates() -> None:
    for ps in Playstyle:
        templates = PLAYSTYLE_TEMPLATES.get(ps, ())
        assert len(templates) >= 2, f"{ps.value} has {len(templates)} templates"


def test_class_paths_start_at_novice() -> None:
    # Actual transitions/rebirth are checked against pinned sources in
    # test_classic_build_validity; tuple length is not a legality check.
    for templates in PLAYSTYLE_TEMPLATES.values():
        for t in templates:
            assert t.class_path[0] == "Novice", t.template_id


def test_stat_plans_use_valid_stats() -> None:
    # Nonlinear costs/caps are independently checked against pre-re sources.
    for templates in PLAYSTYLE_TEMPLATES.values():
        for t in templates:
            assert t.stat_plan, t.template_id
            assert set(t.stat_plan) <= VALID_STATS, t.template_id
            assert all(1 <= v <= 99 for v in t.stat_plan.values()), t.template_id


def test_equip_goal_slots_are_known_and_source_present() -> None:
    for _ps, templates in PLAYSTYLE_TEMPLATES.items():
        for t in templates:
            assert set(t.equip_goals) <= KNOWN_SLOTS, t.template_id
            assert t.source_url.startswith("http"), t.template_id
            assert t.notes, t.template_id
            assert t.milestones, t.template_id
            assert t.milestones[-1] == 99, t.template_id
            assert len(t.skill_goals) >= 6, t.template_id
            for goal in t.skill_goals:
                name, _, level = goal.rpartition(" ")
                assert name, goal
                assert level.isdigit(), goal


def test_skill_name_strips_level() -> None:
    assert skill_name("Bash 10") == "Bash"
    assert skill_name("Increase AGI 10") == "Increase AGI"


# -- author_build_from_template ---------------------------------------------


def _answers(choice: str, score: float = 2.0) -> dict:
    return {"pick_template": {"choice": choice}, "follow_closely": {"score": score}}


def test_follow_exactly_returns_template_shape_with_persona_applied() -> None:
    persona = make_persona(Playstyle.MAGE)
    templates = PLAYSTYLE_TEMPLATES[Playstyle.MAGE]
    model = ScriptedDecisionModel(answers=_answers(templates[0].template_id))
    build = author_build_from_template(persona, "Wisp", templates, model)
    assert build.build_id == "b1"
    assert build.persona_id == persona.persona_id
    assert build.char_name == "Wisp"
    assert build.class_path == templates[0].class_path
    assert build.stat_plan == templates[0].stat_plan
    assert build.equip_goals == templates[0].equip_goals
    assert build.milestone_levels == templates[0].milestones
    assert "Storm Gust" in build.skill_goals  # levels stripped from goal names


def test_custom_answer_falls_back_to_generated_build() -> None:
    persona = make_persona(Playstyle.TANK)
    model = ScriptedDecisionModel(answers=_answers("custom"))
    build = author_build_from_template(persona, "Aegis", PLAYSTYLE_TEMPLATES[Playstyle.TANK], model)
    assert build.persona_id == persona.persona_id
    assert build.char_name == "Aegis"
    assert build.class_path[0] == "Novice"
    assert build.stat_plan  # generated plan, not a template's


def test_tweak_score_shifts_stats_but_keeps_equips() -> None:
    persona = make_persona(Playstyle.MAGE)
    templates = PLAYSTYLE_TEMPLATES[Playstyle.MAGE]
    tpl = templates[0]  # INT 99 / DEX 99; mage emphasis: int, dex, agi
    model = ScriptedDecisionModel(answers=_answers(tpl.template_id, score=1.0))
    build = author_build_from_template(persona, "Wisp", templates, model)
    assert build.stat_plan["INT"] == tpl.stat_plan["INT"] - 10
    assert build.stat_plan["DEX"] == 99  # pinned classic base-stat cap
    assert build.equip_goals == tpl.equip_goals  # equips untouched at score 1


def test_free_score_drops_equips_and_regenerates_stats() -> None:
    persona = make_persona(Playstyle.MELEE)
    templates = PLAYSTYLE_TEMPLATES[Playstyle.MELEE]
    model = ScriptedDecisionModel(answers=_answers(templates[0].template_id, score=0.0))
    build = author_build_from_template(persona, "Shiv", templates, model)
    assert build.equip_goals == {}
    assert set(build.stat_plan) == {"STR", "AGI", "VIT"}  # melee emphasis
    assert build.class_path == templates[0].class_path  # class path kept


def test_unknown_template_id_falls_back_without_error() -> None:
    persona = make_persona(Playstyle.HEALER)
    model = ScriptedDecisionModel(answers=_answers("no-such-template"))
    build = author_build_from_template(
        persona, "Grace", PLAYSTYLE_TEMPLATES[Playstyle.HEALER], model
    )
    assert build.char_name == "Grace"
    assert build.class_path[0] == "Novice"


def test_every_playstyle_templates_can_be_authored_end_to_end() -> None:
    for ps in Playstyle:
        persona = make_persona(ps)
        templates = PLAYSTYLE_TEMPLATES[ps]
        for tpl in templates:
            model = ScriptedDecisionModel(answers=_answers(tpl.template_id))
            build = author_build_from_template(persona, "Test", templates, model)
            assert build.class_path == tpl.class_path
            assert build.stat_plan == tpl.stat_plan
            assert len(build.skill_goals) == len(tpl.skill_goals)

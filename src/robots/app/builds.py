"""Build authoring and item cognition (ADR-009): Clef authors a Build, Clef decides items.

- :class:`BuildAuthor`: at character creation, one SystemOne pass over the
  persona + class options + item catalog authors a :class:`Build`.
- :func:`decide_item_action`: when the bot loots/buys an item, one SystemOne
  pass with the pre-calculated digests in state answers ``item_action``:
  equip / store / sell / discard.
- :func:`note_build_progress`: build progress as an experience note feeding
  ADR-004 memory (kind ``other``, text ``build: <summary>``).
"""

from typing import TYPE_CHECKING, Any, final

from robots.domain.build import Build, BuildProgress, ItemDigest, SkillDigest
from robots.domain.build_templates import BuildTemplate, skill_name, validate_classic_stats
from robots.society.memory import ExperienceNote

if TYPE_CHECKING:
    from robots.ports import DecisionModel, MechanicsPort
    from robots.society.memory import MemoryLog
    from robots.society.models import SocietyPersona

# playstyle -> plausible stat emphases, first = default for that playstyle
STAT_EMPHASIS: dict[str, tuple[str, ...]] = {
    "tank": ("vit", "str", "agi"),
    "healer": ("int", "vit", "dex"),
    "mage": ("int", "dex", "agi"),
    "hunter": ("dex", "agi", "str"),
    "support": ("int", "vit", "dex"),
    "melee": ("str", "agi", "vit"),
}

# ambition answer band -> which price tier of item the plan aims for
AMBIGION_TIER: dict[str, int] = {"minimal": 0, "balanced": 1, "min-maxed": 3}

_AMBITION = ("minimal", "balanced", "min-maxed")

_CLASS_LINE: dict[tuple[str, str], tuple[str, ...]] = {
    ("Swordsman", "str"): ("Novice", "Swordsman", "Knight"),
    ("Swordsman", "vit"): ("Novice", "Swordsman", "Crusader"),
    ("Swordsman", "agi"): ("Novice", "Swordsman", "Knight"),
    ("Mage", "int"): ("Novice", "Mage", "Wizard"),
    ("Mage", "dex"): ("Novice", "Mage", "Sage"),
    ("Acolyte", "int"): ("Novice", "Acolyte", "Priest"),
    ("Acolyte", "vit"): ("Novice", "Acolyte", "Monk"),
}


_FIRST_CLASS: dict[str, str] = {
    "Knight": "Swordsman",
    "Crusader": "Swordsman",
    "Priest": "Acolyte",
    "Monk": "Acolyte",
    "Wizard": "Mage",
    "Sage": "Mage",
    "Hunter": "Archer",
    "Bard": "Archer",
    "Dancer": "Archer",
    "Assassin": "Thief",
    "Rogue": "Thief",
    "Blacksmith": "Merchant",
    "Alchemist": "Merchant",
}


def _class_path(cls: str, emphasis: str) -> tuple[str, ...]:
    if cls in _FIRST_CLASS:
        return ("Novice", _FIRST_CLASS[cls], cls)
    return _CLASS_LINE.get((cls, emphasis), ("Novice", cls))


def _persona_summary(persona: SocietyPersona) -> str:
    lo, hi = persona.level_band
    return (
        f"{persona.name}: playstyle {persona.playstyle.value}, attitude "
        f"{persona.attitude.value}, level band {lo}-{hi}."
    )


@final
class BuildAuthor:
    """Authors a character's Build in one SystemOne pass (Clef decides)."""

    def __init__(self, model: DecisionModel) -> None:
        self._model = model

    def author_build(
        self,
        persona: SocietyPersona,
        char_name: str,
        allowed_classes: dict[str, str],
        mechanics: MechanicsPort,
        build_id: str = "b1",
    ) -> Build:
        """Ask the decision model three questions, map answers onto a Build.

        ``allowed_classes`` maps class name -> one-line description. Equip
        goals are pulled from the mechanics catalog: per slot, the item with
        the highest required_level within the ambition's price tier that the
        persona's level band can reach. Skill goals come from the class's
        learn list. Milestones are the band's midpoint and its end.
        """
        lo, hi = persona.level_band
        request: dict[str, Any] = {
            "model": "clef",
            "state": {
                "persona": _persona_summary(persona),
                "class_options": "; ".join(f"{k} ({v})" for k, v in allowed_classes.items()),
                "level_band": f"{lo}-{hi}",
            },
            "questions": {
                "class_path": {
                    "type": "choice",
                    "instructions": "Which class path will this character take?",
                    "criteria": dict(allowed_classes),
                },
                "stat_emphasis": {
                    "type": "choice",
                    "instructions": "Which stat do I emphasize first?",
                    "criteria": {
                        s: f"Raise {s.upper()} first — fits a {persona.playstyle.value}."
                        for s in STAT_EMPHASIS.get(persona.playstyle.value, ("str",))
                    },
                },
                "equip_ambition": {
                    "type": "score",
                    "instructions": "How ambitious is my equipment plan?",
                    "criteria": ["Minimal", "Balanced", "Min-maxed"],
                },
            },
        }
        answers = self._model.decide(request)["answers"]

        cls = str(answers.get("class_path", {}).get("choice", next(iter(allowed_classes))))
        if cls not in allowed_classes:
            cls = next(iter(allowed_classes))
        emphasis = str(answers.get("stat_emphasis", {}).get("choice", ""))
        if emphasis not in STAT_EMPHASIS.get(persona.playstyle.value, ()):
            emphasis = STAT_EMPHASIS[persona.playstyle.value][0]
        score = float(answers.get("equip_ambition", {}).get("score", 1.0))
        ambition = _AMBITION[min(2, max(0, round(score)))]
        tier = AMBIGION_TIER[ambition]

        equip_goals = self._pick_equip_goals(mechanics, tier, hi)
        skill_goals = tuple(s.name for s in mechanics.skills_for_class(cls))

        milestones = (lo + (hi - lo) // 2, hi) if hi > lo else (hi,)
        return Build(
            build_id=build_id,
            persona_id=persona.persona_id,
            char_name=char_name,
            class_path=_class_path(cls, emphasis),
            stat_plan={  # primary gets the bulk, the rest a token spread
                emphasis: 90,
                **{s: 30 for s in STAT_EMPHASIS[persona.playstyle.value] if s != emphasis},
            },
            skill_goals=skill_goals,
            equip_goals=equip_goals,
            milestone_levels=milestones,
        )

    def _pick_equip_goals(
        self, mechanics: MechanicsPort, tier: int, max_level: int
    ) -> dict[str, str]:
        """Per slot: best item at/below tier whose req level the band can reach.

        Falls back to any item in the slot when none is reachable in time
        (still within the tier); a slot with no items is left out entirely.
        Unknown market tiers are excluded, not treated as free or affordable.
        """
        slots = sorted({i.slot for i in self._all_items(mechanics)})
        goals: dict[str, str] = {}
        for slot in slots:
            candidates = [
                i
                for i in mechanics.items_for_slot(slot)
                if i.price_tier is not None and i.price_tier <= tier
            ]
            reachable = [i for i in candidates if i.required_level <= max_level]
            chosen = max(reachable or candidates, key=lambda i: i.required_level, default=None)
            if chosen is not None:
                goals[slot] = chosen.name
        return goals

    @staticmethod
    def _all_items(mechanics: MechanicsPort) -> tuple[ItemDigest, ...]:
        """The whole catalog, gathered slot by slot (the port has no list-all)."""
        return tuple(
            item
            for slot in ("weapon", "armor", "garment", "shoes", "shield", "headgear")
            for item in mechanics.items_for_slot(slot)
        )


def author_build_from_template(
    persona: SocietyPersona,
    char_name: str,
    templates: tuple[BuildTemplate, ...],
    model: DecisionModel,
    build_id: str = "b1",
) -> Build:
    """Author a Build by letting the model pick one curated template (Clef decides).

    ``templates`` are the candidates for the persona's playstyle (typically a
    slice of :data:`robots.domain.build_templates.PLAYSTYLE_TEMPLATES`).  One
    pass, two questions:

    - ``pick_template`` (choice): one of the template ids, or ``"custom"`` —
      which falls back to :meth:`BuildAuthor.author_build`'s generated path.
    - ``follow_closely`` (score, 0-2): 0 = improvise freely, 1 = tweak stats,
      2 = follow exactly.  Mapped conservatively: 2 keeps the template
      verbatim; 1 keeps skills and equips but shifts stats toward the
      playstyle's emphasis spread (primary -10, secondaries +5); 0 keeps only
      the class path and skill goals, stat plan regenerates from the
      playstyle emphasis and equip goals are dropped.

    The existing :class:`BuildAuthor` authoring path is untouched.
    """
    author = BuildAuthor(model)
    summaries = {
        t.template_id: f"{t.name}: {' > '.join(t.class_path)}; {t.notes}" for t in templates
    }
    request: dict[str, Any] = {
        "model": "clef",
        "state": {
            "persona": _persona_summary(persona),
            "candidate_templates": "; ".join(f"{tid} ({txt})" for tid, txt in summaries.items()),
        },
        "questions": {
            "pick_template": {
                "type": "choice",
                "instructions": "Which curated build do I take as mine? ('custom' = roll my own)",
                "criteria": {**summaries, "custom": "Improvise my own build."},
            },
            "follow_closely": {
                "type": "score",
                "instructions": "How closely do I follow the template?",
                "criteria": ["Improvise freely", "Tweak the stats", "Follow exactly"],
            },
        },
    }
    answers = model.decide(request)["answers"]

    choice = str(answers.get("pick_template", {}).get("choice", "custom"))
    chosen = next((t for t in templates if t.template_id == choice), None)
    if chosen is None:  # 'custom' or an unknown id: fall back to the generated path
        allowed = _template_class_options(persona.playstyle.value)
        return author.author_build(persona, char_name, allowed, _NullMechanics(), build_id)

    score = float(answers.get("follow_closely", {}).get("score", 2.0))
    follow = min(2, max(0, round(score)))
    stat_plan, equip_goals = _template_adaptation(chosen, persona, follow)

    return Build(
        build_id=build_id,
        persona_id=persona.persona_id,
        char_name=char_name,
        class_path=chosen.class_path,
        stat_plan=stat_plan,
        skill_goals=tuple(skill_name(g) for g in chosen.skill_goals),
        skill_levels={skill_name(g): int(g.rsplit(" ", 1)[1]) for g in chosen.skill_goals},
        ruleset=chosen.ruleset,
        validation_issues=_template_validation_issues(chosen),
        equip_goals=equip_goals,
        milestone_levels=chosen.milestones,
    )


def _template_validation_issues(chosen: BuildTemplate) -> tuple[str, ...]:
    issues = [
        "Equipment variants, card composites and full job restrictions remain unvalidated.",
        "Stats validate only the pinned level-99 endpoint, not milestone allocations.",
        "Class paths do not validate quest, job-level or rebirth execution requirements.",
    ]
    if chosen.template_id not in {"mage-aoe-wizard", "support-battlesmith"}:
        issues.append("Skill ancestor closure and per-job point budgets remain unvalidated.")
    if chosen.template_id == "support-battlesmith":
        issues.append(
            "Cart Revolution requires quest acquisition; it is not an ordinary skill point."
        )
    if chosen.template_id == "mage-sage-bolter":
        issues.append("Linked Sage guide is Renewal, not validated Classic source evidence.")
    if chosen.template_id == "healer-fs-priest":
        issues.append("Linked Priest guide is High-Priest focused; Classic guidance is uncertain.")
    return tuple(issues)


def _template_adaptation(
    chosen: BuildTemplate, persona: SocietyPersona, follow: int
) -> tuple[dict[str, int], dict[str, str]]:
    """``follow_closely`` score -> (stat_plan, equip_goals) for the chosen template.

    2 keeps the template verbatim; 1 keeps skills and equips but shifts stats
    toward the playstyle emphasis (primary -10, secondaries +5); 0 keeps only
    class path and skills, stat plan regenerates from the playstyle emphasis
    and equip goals are dropped.
    """
    if chosen.ruleset != "classic":
        msg = "template ruleset is not classic"
        raise ValueError(msg)
    stat_plan = dict(chosen.stat_plan)
    equip_goals = dict(chosen.equip_goals)
    emphasis = STAT_EMPHASIS.get(persona.playstyle.value, ())
    if follow == 1 and emphasis:
        _tweak_classic_stats(stat_plan, emphasis)
    elif follow == 0:
        stat_plan = {s.upper(): 90 if i == 0 else 30 for i, s in enumerate(emphasis or ("str",))}
        equip_goals = {}
    validate_classic_stats(stat_plan)
    return stat_plan, equip_goals


def _tweak_classic_stats(stat_plan: dict[str, int], emphasis: tuple[str, ...]) -> None:
    primary = emphasis[0].upper()
    if primary not in stat_plan:
        return
    stat_plan[primary] = max(1, stat_plan[primary] - 10)
    for stat in emphasis[1:]:
        key = stat.upper()
        if key in stat_plan:
            stat_plan[key] = min(99, stat_plan[key] + 5)


def _template_class_options(playstyle: str) -> dict[str, str]:
    """Allowed classes for the fallback path, derived from the playstyle."""
    lines = {
        "tank": {"Crusader": "VIT shield tank line."},
        "healer": {"Priest": "Heal and buff line."},
        "mage": {"Wizard": "AoE magic damage line."},
        "hunter": {"Hunter": "Bow and falcon line."},
        "support": {"Bard": "Song and party buff line."},
        "melee": {"Assassin": "AGI katar line."},
    }
    return lines.get(playstyle, {"Swordsman": "Front-line fighter."})


class _NullMechanics:
    """Minimal MechanicsPort stand-in: no catalog, skills come from the class."""

    def skills_for_class(self, cls: str) -> tuple[SkillDigest, ...]:  # noqa: ARG002
        return ()

    def items_for_slot(self, slot: str) -> tuple[ItemDigest, ...]:  # noqa: ARG002
        return ()

    def item_by_name(self, name: str) -> ItemDigest | None:  # noqa: ARG002
        return None


def decide_item_action(
    state: dict[str, Any],
    new_item: ItemDigest,
    equipped: ItemDigest | None,
    build: Build,
    model: DecisionModel,
) -> str:
    """One SystemOne pass: equip / store / sell / discard for a looted item.

    ``state`` may carry extra context (map, zeny, ...); the item cognition
    fields are added here: both digests' text, the build goal for the slot,
    and the pre-calculated comparison, so the model never does math itself.
    """
    goal = build.goal_for_slot(new_item.slot)
    compare = (
        "no item equipped in this slot"
        if equipped is None
        else f"equipped now: {equipped.digest_text}"
    )
    fits = (
        "yes" if goal == new_item.name else (f"goal is {goal}" if goal else "no goal for this slot")
    )
    request: dict[str, Any] = {
        "model": "clef",
        "state": {
            **state,
            "new_item": new_item.digest_text,
            "equipped_item": compare,
            "build_goal_slot": goal or "none",
            "fits_build": fits,
        },
        "questions": {
            "item_action": {
                "type": "choice",
                "instructions": (
                    f"Looted/bought {new_item.name} for slot '{new_item.slot}'. "
                    "What do I do with it?"
                ),
                "criteria": {
                    "equip": "Better than current and fits my build.",
                    "store": "Keep for later per my build plan.",
                    "sell": "No value to my build; convert to zeny.",
                    "discard": "Worthless.",
                },
            },
        },
    }
    answers = model.decide(request)["answers"]
    return str(answers.get("item_action", {}).get("choice", "sell"))


def note_build_progress(log: MemoryLog, progress: BuildProgress) -> None:
    """Append the build's progress as one 'other' experience note (ADR-009)."""
    log.append(ExperienceNote(ts=0.0, kind="other", text=f"build: {progress.summary()}"))

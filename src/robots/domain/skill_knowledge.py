"""Provider-neutral public skill advice, independent of received facts and authority."""

import json
from dataclasses import asdict, dataclass
from typing import Any

from robots.domain.skills import ReceivedSkillContextReadOnly


def serialized_advice(value: object) -> bytes:
    """Count the complete compact UTF-8 section, not just its prose."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True, slots=True)
class PublicSkillCard:
    """Explicit public metadata; omitted source Type stays unknown."""

    id: int
    ruleset: str
    name: str
    aegis_name: str
    meaning: str
    declared_max_level: int
    declared_type: str | None
    revision: str
    db_path: str
    db_sha256: str
    meaning_source_path: str
    meaning_source_sha256: str
    meaning_source_lines: str


@dataclass(frozen=True, slots=True)
class PublicSkillKnowledge:
    """Immutable catalog selection; never learns skills or grants permissions."""

    ruleset: str
    cards: tuple[PublicSkillCard, ...]

    def __post_init__(self) -> None:
        if (
            self.ruleset not in ("pre-re", "renewal")
            or type(self.cards) is not tuple
            or len(self.cards) > 32
            or any(
                type(card) is not PublicSkillCard or type(card.id) is not int for card in self.cards
            )
            or len({(card.ruleset, card.id) for card in self.cards}) != len(self.cards)
        ):
            message = "invalid public skill catalog"
            raise ValueError(message)

    def decision_advice(
        self,
        context: ReceivedSkillContextReadOnly,
        *,
        max_cards: int = 8,
        max_utf8_bytes: int = 2048,
    ) -> dict[str, Any]:
        """Select only received IDs in receipt order, with explicit limited coverage."""
        _validate_budget(max_cards, max_utf8_bytes)
        catalog = {card.id: card for card in self.cards if card.ruleset == self.ruleset}
        rows = context.rows or ()
        result: dict[str, Any] = {
            "authority": "public_advice",
            "ruleset": self.ruleset,
            "coverage": "UNKNOWN" if context.rows is None else "PARTIAL",
            "uncovered_count": sum(row.id not in catalog for row in rows),
            "truncated": False,
            "cards": [],
        }
        for row in rows:
            card = catalog.get(row.id)
            if card is None:
                continue
            _append_bounded_card(result, card, max_cards, max_utf8_bytes)
        return result


def _validate_budget(max_cards: int, max_utf8_bytes: int) -> None:
    if (
        type(max_cards) is not int
        or not 0 <= max_cards <= 8
        or type(max_utf8_bytes) is not int
        or not 256 <= max_utf8_bytes <= 2048
    ):
        message = "invalid public skill advice budget"
        raise ValueError(message)


def _append_bounded_card(
    result: dict[str, Any], card: PublicSkillCard, max_cards: int, max_utf8_bytes: int
) -> None:
    if len(result["cards"]) >= max_cards:
        result["truncated"] = True
        return
    result["cards"].append(asdict(card))
    if len(serialized_advice(result)) > max_utf8_bytes:
        result["cards"].pop()
        result["truncated"] = True

"""Bounded public advice, separate from private memory and server mechanics."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import cast

_CARD_FIELDS = frozenset(
    (
        "card_id",
        "ruleset",
        "topic",
        "text",
        "source_id",
        "source_url",
        "revision",
        "retrieved_on",
        "content_sha256",
    )
)
_SOURCE_PINS = {
    "iro-classic-stats-23836": (
        "pre-re",
        "https://irowiki.org/classic/Stats",
        "23836",
        "2026-10-07",
        "a47743b06ef42426f23db233d7aea7db42f901c6b0dd3beb7dc099707ada47b0",
    ),
    "iro-renewal-stats-86935": (
        "renewal",
        "https://irowiki.org/wiki/Stats",
        "86935",
        "2026-10-07",
        "b8ed99d4ccd5f8677e57b3e9f36932a2c5657c9fd67a78a60605d0f1ea2cec33",
    ),
}


def _require(valid: bool, message: str) -> None:
    if not valid:
        raise ValueError(message)


_MAX_CATALOG_BYTES = 262144


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


@dataclass(frozen=True)
class RuleCard:
    """A public paraphrase with retained snapshot provenance, never native authority."""

    card_id: str
    ruleset: str
    topic: str
    text: str
    source_id: str
    source_url: str
    revision: str
    retrieved_on: str
    content_sha256: str
    authority: str = field(default="advice", init=False)
    mechanically_verified: bool = field(default=False, init=False)
    private_context: bool = field(default=False, init=False)


def _parse_card(value: object) -> RuleCard:
    _require(isinstance(value, dict), "card must be an object")
    if not isinstance(value, dict):
        message = "card must be an object"
        raise ValueError(message)
    _require(set(value) == _CARD_FIELDS, "invalid card fields")
    _require(
        all(isinstance(item, str) and 0 < len(item) <= 1024 for item in value.values()),
        "invalid card string",
    )
    row = cast(dict[str, str], value)
    _require(row["topic"] in ("stats", "skills", "equipment"), "unsupported topic")
    pin = _SOURCE_PINS.get(row["source_id"])
    actual = tuple(
        row[key] for key in ("ruleset", "source_url", "revision", "retrieved_on", "content_sha256")
    )
    _require(pin is not None and actual == pin, "unrecognized or mismatched source provenance")
    return RuleCard(**row)


def serialize_cards(cards: tuple[RuleCard, ...]) -> bytes:
    """Canonical UTF-8 wire payload; brackets and all provenance count."""
    return json.dumps(
        [asdict(card) for card in cards], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _validate_selection(
    ruleset: str, topics: tuple[str, ...], max_cards: int, max_utf8_bytes: int
) -> None:
    if ruleset not in ("pre-re", "renewal"):
        message = "unsupported ruleset"
        raise ValueError(message)
    if type(max_cards) is not int or not 0 <= max_cards <= 8:
        message = "max_cards must be an integer in [0, 8]"
        raise ValueError(message)
    if type(max_utf8_bytes) is not int or max_utf8_bytes < 0:
        message = "max_utf8_bytes must be a nonnegative integer"
        raise ValueError(message)
    _require(
        isinstance(topics, tuple)
        and all(
            isinstance(topic, str) and topic in ("stats", "skills", "equipment") for topic in topics
        ),
        "unsupported topic request",
    )


@dataclass(frozen=True)
class RulesKnowledge:
    """Explicit file loading only; construction does not fetch or create providers."""

    cards: tuple[RuleCard, ...]

    @classmethod
    def load(cls, path: Path) -> RulesKnowledge:
        with path.open("rb") as stream:
            raw = stream.read(_MAX_CATALOG_BYTES + 1)
        _require(len(raw) <= _MAX_CATALOG_BYTES, "catalog byte limit exceeded")
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        _require(isinstance(document, dict), "catalog must be an object")
        _require(set(document) == {"schema_version", "cards"}, "invalid catalog fields")
        _require(
            type(document["schema_version"]) is int and document["schema_version"] == 1,
            "unsupported schema_version",
        )
        rows = document["cards"]
        _require(isinstance(rows, list) and len(rows) <= 32, "invalid card count")
        cards = tuple(_parse_card(row) for row in rows)
        _require(len({card.card_id for card in cards}) == len(cards), "duplicate card_id")
        return cls(cards)

    def select(
        self,
        ruleset: str,
        *,
        topics: tuple[str, ...] = ("stats",),
        max_cards: int = 8,
        max_utf8_bytes: int = 2048,
    ) -> tuple[RuleCard, ...]:
        """Select offline public advice in catalog order."""
        _validate_selection(ruleset, topics, max_cards, max_utf8_bytes)
        selected: tuple[RuleCard, ...] = ()
        for card in self.cards:
            if card.ruleset != ruleset or card.topic not in topics:
                continue
            candidate = (*selected, card)
            if len(candidate) > max_cards or len(serialize_cards(candidate)) > max_utf8_bytes:
                break
            selected = candidate
        return selected

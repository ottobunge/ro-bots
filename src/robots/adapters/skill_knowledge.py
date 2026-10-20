"""Bounded offline public skill catalog loader; exact reviewed card bytes are pinned."""

import hashlib
import json
from pathlib import Path
from typing import Any

from robots.domain.skill_knowledge import PublicSkillCard, PublicSkillKnowledge

# Each pin covers the entire paraphrase, metadata, source paths and source hashes.
_CARD_PINS = {
    "pre-re": "bb634b66a2413f430ee3c0370361bbf944dac363599d40c2e6b349d02e76b841",
    "renewal": "52fafa384cc46836219be75bb279659fb74a7d020744c4a7b1651cbe51f2f818",
}


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            message = "duplicate public skill JSON key"
            raise ValueError(message)
        result[key] = value
    return result


def _card(row: Any) -> PublicSkillCard:
    if not isinstance(row, dict) or type(row.get("id")) is not int:
        message = "invalid public skill card"
        raise ValueError(message)
    encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    pin = _CARD_PINS.get(str(row.get("ruleset")))
    if hashlib.sha256(encoded).hexdigest() != pin:
        message = "unrecognized public skill card content or source provenance"
        raise ValueError(message)
    return PublicSkillCard(**row)


def load_skill_knowledge(path: Path, ruleset: str) -> PublicSkillKnowledge:
    """Explicit opt-in; no network, providers, YAML evaluation or private memory."""
    with path.open("rb") as stream:
        raw = stream.read(262145)
    if len(raw) > 262144:
        message = "public skill catalog byte limit exceeded"
        raise ValueError(message)
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    rows = _catalog_rows(document)
    cards = tuple(_card(row) for row in rows)
    return PublicSkillKnowledge(ruleset, cards)


def _catalog_rows(document: Any) -> list[Any]:
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "cards"}
        or type(document["schema_version"]) is not int
        or document["schema_version"] != 1
        or not isinstance(document["cards"], list)
        or len(document["cards"]) > 32
    ):
        message = "invalid public skill catalog schema"
        raise ValueError(message)
    rows: list[Any] = document["cards"]
    return rows

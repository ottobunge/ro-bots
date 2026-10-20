"""Detached historical SELF capacity; never purchasing or equipment authority."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReceivedCapacityValue:
    value: int
    receipt_sequence: int
    observed_at: float


@dataclass(frozen=True, slots=True)
class ReceivedCapacity:
    """Unscaled engine counts with independently known weight and maximum.

    Negative counts remain historical facts, not valid capacity. A complete,
    nonnegative pair still grants no expenditure permission or current freshness.
    Ordinary same-server warp preserves these session-bound historical receipts.
    """

    epoch: int
    character: str
    account_id: int
    character_id: int
    selection_epoch: int
    map_epoch: int
    sampled_at: float
    weight: ReceivedCapacityValue | None = None
    max_weight: ReceivedCapacityValue | None = None
    inventory_changed_sequence: int | None = None
    source_binding: str = "selected-self-b0-24-25"

    @property
    def complete(self) -> bool:
        return self.weight is not None and self.max_weight is not None

    @property
    def nonnegative(self) -> bool:
        return all(v is None or v.value >= 0 for v in (self.weight, self.max_weight))

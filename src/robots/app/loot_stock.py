"""Attributed pickup receipts admit small held batches, never synthetic inventory."""

from robots.adapters.native_gameplay import NativeGameplayView, ObservedPickupAck

LOOT_STOCK_SECONDS = 900.0


class LootStock:
    def __init__(self) -> None:
        self._indices: dict[int, tuple[int, float]] = {}

    @property
    def active(self) -> bool:
        return bool(self._indices)

    def admit(self, ack: ObservedPickupAck, now: float) -> None:
        self._indices[ack.inventory_index] = (ack.item_id, now)

    def held(
        self, view: NativeGameplayView, indexed: tuple[tuple[int, int, int], ...] | None, now: float
    ) -> int:
        if not view.inventory_known or indexed is None:
            return 0
        # Current inventory, not cumulative acquired_counts or the ACK tail.
        inventory = {index: (item, count) for index, item, count in indexed}
        self._indices = {
            index: (item, started)
            for index, (item, started) in self._indices.items()
            if started <= now < started + LOOT_STOCK_SECONDS
            and inventory.get(index, (None, 0))[0] == item
        }
        return sum(inventory[index][1] for index in self._indices)

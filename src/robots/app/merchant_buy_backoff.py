"""Owner-local buy patience; received offers remain the only stock evidence."""

from robots.domain.npc import NpcDialogue
from robots.domain.shop import ReceivedShopOffer

BUY_STOCK_LIMIT = 3
BUY_ITEM_ID = 1201


class MerchantBuyBackoff:
    def __init__(self) -> None:
        self._refusals: dict[tuple[str, int, int], tuple[str, int]] = {}

    @property
    def suspended(self) -> bool:
        return any(count >= BUY_STOCK_LIMIT for _, count in self._refusals.values())

    @staticmethod
    def current(offer: ReceivedShopOffer, dialog: NpcDialogue | None, epoch: int | None) -> bool:
        return dialog is not None and (
            offer.epoch == dialog.epoch == epoch
            and offer.map_name == dialog.map_name
            and offer.npc_id == dialog.npc_id
            and offer.opened_sequence == dialog.opened_sequence
            and offer.receipt_sequence > dialog.opened_sequence
        )

    def observe(
        self,
        offer: ReceivedShopOffer,
        inventory_known: bool,
        wanted: tuple[int, ...] = (BUY_ITEM_ID,),
    ) -> str | None:
        """A positive fresh observation resets the relevant consecutive refusal."""
        if inventory_known and not wanted:
            return None
        key = self._key(offer, wanted)
        if not any(row.item_id in wanted for row in offer.rows):
            return "no stock in offer"
        if not inventory_known:
            if self._refusals.get(key, (None, 0))[0] == "no stock in offer":
                self._refusals.pop(key, None)
            return "inventory stock unknown"
        self._refusals.pop(key, None)
        return None

    def evaluate(
        self,
        offer: ReceivedShopOffer,
        inventory_known: bool,
        wanted: tuple[int, ...] = (BUY_ITEM_ID,),
    ) -> tuple[str, bool] | None:
        """Give up from evaluation three; tap once until a positive observation."""
        reason = self.observe(offer, inventory_known, wanted)
        if reason is None:
            return None
        key = self._key(offer, wanted)
        previous, count = self._refusals.get(key, (reason, 0))
        first = previous != reason or count < BUY_STOCK_LIMIT
        count = min(count + 1, BUY_STOCK_LIMIT) if previous == reason else 1
        self._refusals[key] = (reason, count)
        return (reason, first) if count == BUY_STOCK_LIMIT else None

    @staticmethod
    def _key(offer: ReceivedShopOffer, wanted: tuple[int, ...]) -> tuple[str, int, int]:
        offered = {row.item_id for row in offer.rows}
        item = next((item for item in wanted if item in offered), next(iter(wanted), BUY_ITEM_ID))
        return (offer.map_name, offer.npc_id, item)

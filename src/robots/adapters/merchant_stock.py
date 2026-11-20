"""Public unequipped stock candidates; received C7 rows alone authorize an actual sale."""

from pathlib import Path

import yaml


def public_stock_ids(path: Path) -> frozenset[int]:
    """Pinned non-equipment classes without NoSell or negative sell value.

    The dealer's weapon BUY catalog does not restrict its SELL list. Per-instance
    restrictions (bound, favorite, rental) remain the server's C7 decision.
    """
    if not path.is_file():
        return frozenset()
    data = yaml.safe_load(path.read_text())
    return frozenset(
        row["Id"]
        for row in data["Body"]
        if row.get("Type") in ("Etc", "Card", "Healing", "Usable", "Delayconsume", "Cash")
        and not row.get("Trade", {}).get("NoSell", False)
        and row.get("Sell", 0) >= 0
    )


MISC_SELLABLE_IDS = public_stock_ids(
    Path(__file__).resolve().parents[3] / "rathena/db/pre-re/item_db_etc.yml"
)

PUBLIC_STOCK_IDS = MISC_SELLABLE_IDS | public_stock_ids(
    Path(__file__).resolve().parents[3] / "rathena/db/pre-re/item_db_usable.yml"
)

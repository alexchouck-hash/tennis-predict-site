"""Custom price provider adapter for Polymarket's official CLOB Market Maker (poly-market-maker)."""

from __future__ import annotations

import time
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictPriceProvider:
    """Provides machine learning fair value odds to Polymarket's poly-market-maker bot.

    Anchors the market maker's spread center to point-level tennis ML probabilities,
    ensuring resting maker orders capture spread while avoiding adverse selection.
    """

    def __init__(self, refresh_interval_sec: int = 120):
        self.refresh_interval_sec = refresh_interval_sec
        self._cache: dict[str, float] = {}
        self._last_fetch = 0.0

    def refresh(self, force: bool = False) -> None:
        """Refreshes active match forecasts from iPredictSport."""
        now = time.time()
        if not force and (now - self._last_fetch < self.refresh_interval_sec):
            return

        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            matches = data.get("matches", [])

            new_cache = {}
            for m in matches:
                p1 = str(m.get("p1_name", "")).strip().lower()
                p2 = str(m.get("p2_name", "")).strip().lower()
                p1_prob = float(m.get("p1_prob", 0.5))

                if p1:
                    new_cache[p1] = p1_prob
                if p2:
                    new_cache[p2] = 1.0 - p1_prob

            self._cache = new_cache
            self._last_fetch = now
        except (requests.RequestException, ValueError, KeyError):
            pass

    def get_target_price(self, token_or_player: str, fallback_price: float = 0.50) -> float:
        """Returns the model's calibrated probability (0.01 to 0.99) for a player or market.

        Args:
            token_or_player: Player surname or token keyword to lookup.
            fallback_price: Default price if no prediction is available.
        """
        self.refresh()
        query = token_or_player.strip().lower()

        for player_name, prob in self._cache.items():
            if query in player_name or player_name in query:
                return max(0.01, min(0.99, prob))

        return fallback_price

    def get_order_bands(
        self,
        token_or_player: str,
        half_spread: float = 0.02,
        order_size: float = 20.0,
    ) -> dict[str, Any]:
        """Calculates bid and ask quotes centered on the model fair value.

        Args:
            token_or_player: The player name or market token.
            half_spread: The distance from fair price for the inner quote level (default 2 cents).
            order_size: Size in USDC/contracts.
        """
        fair = self.get_target_price(token_or_player)
        bid = round(max(0.01, fair - half_spread), 2)
        ask = round(min(0.99, fair + half_spread), 2)

        return {
            "player": token_or_player,
            "fair_price": round(fair, 3),
            "bid_price": bid,
            "ask_price": ask,
            "order_size": order_size,
            "maker_fee_rebate": "0%",
        }


if __name__ == "__main__":
    provider = IPredictPriceProvider()
    provider.refresh(force=True)
    sample_bands = provider.get_order_bands("Alcaraz", half_spread=0.03, order_size=50.0)
    print(">> Polymarket poly-market-maker IPredictPriceProvider test:")
    print(sample_bands)

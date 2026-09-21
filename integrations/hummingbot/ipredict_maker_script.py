"""Hummingbot Market Making Script quoting around iPredictSport ML fair odds."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import ClassVar

import requests

try:
    from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
except ImportError:
    # Fallback class for environments without hummingbot installed
    class ScriptStrategyBase:  # type: ignore
        def __init__(self):
            pass

        def logger(self):
            class SimpleLogger:
                def info(self, msg: str):
                    print(f"[INFO] {msg}")

                def warning(self, msg: str):
                    print(f"[WARN] {msg}")

                def error(self, msg: str):
                    print(f"[ERROR] {msg}")
            return SimpleLogger()

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictTennisMarketMaker(ScriptStrategyBase):
    """Quotes two-sided resting limit orders (0% maker fee on Kalshi) anchored to
    iPredictSport machine learning fair probabilities.
    """

    exchange = "kalshi"
    trading_pair = "KXATP-MATCH"  # Kalshi ATP match market ticker
    order_amount = Decimal(10)   # Contracts per side
    bid_spread_pp = Decimal("3.0") # 3 percentage points below fair
    ask_spread_pp = Decimal("3.0") # 3 percentage points above fair
    update_interval_sec = 60

    markets: ClassVar[dict[str, set[str]]] = {exchange: {trading_pair}}

    def __init__(self):
        super().__init__()
        self._last_update_ts = 0.0
        self._fair_price: Decimal | None = None
        self._active_match: str = ""

    def fetch_model_fair_price(self) -> Decimal | None:
        """Pulls calibrated fair probability for the current target market from iPredictSport."""
        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            evals = data.get("kalshi_evaluations", [])

            for item in evals:
                if item.get("ticker") == self.trading_pair or not self._fair_price:
                    prob = float(item.get("our_p1", 0.50))
                    self._active_match = item.get("match", "Unknown")
                    return Decimal(str(round(prob, 2)))

            # Default to first match if exact ticker not found
            matches = data.get("matches", [])
            if matches:
                p1_prob = float(matches[0].get("p1_prob", 0.50))
                self._active_match = matches[0].get("match", "Top Match")
                return Decimal(str(round(p1_prob, 2)))

        except (requests.RequestException, ValueError, KeyError) as exc:
            self.logger().warning(f"Failed to refresh iPredict fair price: {exc}")
        return self._fair_price

    def on_tick(self) -> None:
        """Evaluates book and repositions maker quotes on each cycle."""
        now = time.time()
        if now - self._last_update_ts > self.update_interval_sec:
            new_fair = self.fetch_model_fair_price()
            if new_fair:
                self._fair_price = new_fair
                self.logger().info(
                    f"Updated fair price for {self._active_match}: {self._fair_price:.2f}"
                )
            self._last_update_ts = now

        if not self._fair_price:
            return

        # Compute optimal resting limit prices
        half_spread = (self.bid_spread_pp + self.ask_spread_pp) / Decimal("200.0")
        bid_price = max(Decimal("0.01"), self._fair_price - half_spread)
        ask_price = min(Decimal("0.99"), self._fair_price + half_spread)

        self.logger().info(
            f"Quoting Maker Spread: Bid ${bid_price:.2f} | Fair ${self._fair_price:.2f} | Ask ${ask_price:.2f}"
        )


if __name__ == "__main__":
    mm = IPredictTennisMarketMaker()
    price = mm.fetch_model_fair_price()
    print(f">> IPredict Hummingbot Maker Script: Fetched fair price = {price}")
    mm.on_tick()

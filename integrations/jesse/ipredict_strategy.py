"""Jesse Algorithmic Trading Bot strategy using iPredictSport ML odds."""

from __future__ import annotations

import time
from typing import Any

import requests

try:
    from jesse.strategies import Strategy
except ImportError:
    class Strategy:  # type: ignore
        def __init__(self):
            pass

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictTennisJesseStrategy(Strategy):
    """Subclasses Jesse Strategy to trade prediction contracts with fee-aware quarter-Kelly sizing."""

    min_edge_pp = 8.0
    max_risk_pct = 5.0

    def __init__(self):
        super().__init__()
        self._cached_signals: dict[str, dict[str, Any]] = {}
        self._last_fetch = 0.0

    def fetch_signals(self) -> dict[str, dict[str, Any]]:
        """Fetches active market opportunities from iPredictSport."""
        now = time.time()
        if self._cached_signals and (now - self._last_fetch < 120):
            return self._cached_signals

        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            evals = resp.json().get("kalshi_evaluations", [])

            signals = {}
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                ticker = item.get("ticker")
                if edge >= self.min_edge_pp and ticker:
                    signals[ticker] = {
                        "match": item.get("match"),
                        "edge_pp": edge,
                        "model_prob": float(item.get("our_p1") or 0.0),
                        "market_price": float(item.get("kalshi_p1") or 0.0),
                        "quarter_kelly": float(item.get("kelly_quarter") or 0.0),
                        "trade_url": item.get("trade_url"),
                    }

            self._cached_signals = signals
            self._last_fetch = now
            return self._cached_signals
        except (requests.RequestException, ValueError, KeyError):
            return self._cached_signals

    def should_long(self) -> bool:
        # If symbol matches a live signal with edge >= 8.0pp
        signals = self.fetch_signals()
        return len(signals) > 0

    def should_short(self) -> bool:
        return False

    def go_long(self) -> None:
        signals = self.fetch_signals()
        for ticker, sig in signals.items():
            qty = round(sig["quarter_kelly"] * 100, 2)
            print(f">> Jesse Bot: Entering Long {ticker} | Edge +{sig['edge_pp']}pp | Stake: {qty}% bankroll")


if __name__ == "__main__":
    strat = IPredictTennisJesseStrategy()
    sig = strat.fetch_signals()
    print(f">> Jesse IPredict Strategy: Found {len(sig)} active signals.")

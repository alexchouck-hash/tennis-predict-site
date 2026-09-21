"""Freqtrade external signal and data provider for iPredictSport tennis predictions."""

from __future__ import annotations

import time
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictSignalProvider:
    """Provides external quantitative sports betting and prediction market signals for Freqtrade strategies."""

    def __init__(self, min_edge_pp: float = 8.0, cache_ttl_seconds: int = 300):
        self.min_edge_pp = min_edge_pp
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cached_data: list[dict[str, Any]] = []
        self._last_fetch_time: float = 0.0

    def fetch_signals(self, force: bool = False) -> list[dict[str, Any]]:
        """Fetches and caches active prediction market signals."""
        now = time.time()
        if not force and self._cached_data and (now - self._last_fetch_time < self.cache_ttl_seconds):
            return self._cached_data

        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            evals = data.get("kalshi_evaluations", [])

            signals = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                if edge >= self.min_edge_pp:
                    ticker = item.get("ticker", "UNKNOWN")
                    # Format into a Freqtrade-compatible signal dictionary
                    signals.append({
                        "pair": f"{ticker}/USDT",
                        "match": item.get("match"),
                        "direction": "long",
                        "enter_tag": f"ipredict_edge_{edge:.1f}pp",
                        "confidence": float(item.get("our_p1", 0.0)),
                        "market_price": float(item.get("kalshi_p1", 0.0)),
                        "edge_pp": edge,
                        "stake_ratio": min(0.05, float(item.get("kelly_quarter", 0.0))),
                        "timestamp": now,
                    })

            self._cached_data = signals
            self._last_fetch_time = now
            return self._cached_data

        except (requests.RequestException, ValueError, KeyError):
            return self._cached_data

    def get_signal_for_pair(self, pair: str) -> dict[str, Any] | None:
        """Retrieves active signal for a specific pair or ticker."""
        clean_pair = pair.upper().split("/")[0]
        for sig in self.fetch_signals():
            if clean_pair in sig["pair"]:
                return sig
        return None


# Example template for Freqtrade strategy subclassing IStrategy
STRATEGY_TEMPLATE = """
# Freqtrade Strategy using iPredictSport Signals
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from ipredict_provider import IPredictSignalProvider

class IPredictTennisFreqtradeStrategy(IStrategy):
    minimal_roi = {"0": 0.20, "60": 0.10, "120": 0.05}
    stoploss = -0.15
    timeframe = "1h"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.signal_provider = IPredictSignalProvider(min_edge_pp=8.0)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Check external iPredictSport signal
        sig = self.signal_provider.get_signal_for_pair(metadata["pair"])
        dataframe["ipredict_edge"] = sig["edge_pp"] if sig else 0.0
        dataframe["ipredict_enter"] = 1 if (sig and sig["edge_pp"] >= 8.0) else 0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["ipredict_enter"] == 1),
            ["enter_long", "enter_tag"]
        ] = (1, "ipredict_edge_signal")
        return dataframe
"""

if __name__ == "__main__":
    provider = IPredictSignalProvider(min_edge_pp=5.0)
    signals = provider.fetch_signals()
    print(f">> Freqtrade IPredict Provider: Retrieved {len(signals)} active signals.")

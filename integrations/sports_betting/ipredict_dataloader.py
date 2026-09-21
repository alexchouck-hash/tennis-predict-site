"""DataLoader for georgedouzas/sports-betting.

Loads active ATP & WTA tennis matches, point-level win probabilities, and
prediction market closing prices from iPredictSport.com as pandas DataFrames.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import requests

PREDICTIONS_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictSportDataLoader:
    """Fetches and transforms iPredictSport tennis match predictions into standard DataFrames."""

    def __init__(self, feed_url: str = PREDICTIONS_FEED_URL) -> None:
        self.feed_url = feed_url

    def fetch_raw(self) -> dict[str, Any]:
        """Fetch raw JSON feed."""
        resp = requests.get(self.feed_url, timeout=12.0)
        resp.raise_for_status()
        return resp.json()

    def load_upcoming_matches(self) -> pd.DataFrame:
        """Return upcoming matches with calibrated win probabilities as a DataFrame."""
        data = self.fetch_raw()
        matches = data.get("upcoming_board", [])
        if not matches:
            return pd.DataFrame()
        df = pd.DataFrame(matches)
        df["generated_utc"] = data.get("generated_utc")
        return df

    def load_market_evaluations(self) -> pd.DataFrame:
        """Return Kalshi/Polymarket evaluations with calculated edges as a DataFrame."""
        data = self.fetch_raw()
        evals = data.get("kalshi_evaluations", [])
        if not evals:
            return pd.DataFrame()
        df = pd.DataFrame(evals)
        df["generated_utc"] = data.get("generated_utc")
        return df

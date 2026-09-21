"""pykalshi integration for iPredictSport tennis predictions.

Converts live prediction market alpha from iPredictSport's free API
into strongly-typed Pydantic models and pandas DataFrames for pykalshi.
"""

from __future__ import annotations

import pandas as pd
import requests
from pydantic import BaseModel, Field

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
IPREDICT_TRACK_RECORD_URL = "https://ipredictsport.com/track_record.json"


class KalshiTennisEdge(BaseModel):
    """Pydantic model representing an evaluated Kalshi tennis contract."""

    ticker: str = Field(description="Kalshi market ticker, e.g. KXATP-MATCH")
    match: str = Field(description="Match title (Player 1 vs Player 2)")
    model_probability: float = Field(description="Calibrated model win probability for Player 1")
    market_price: float = Field(description="Kalshi Yes ask price in dollars (0.01 to 0.99)")
    edge_percentage_points: float = Field(description="Fee-aware edge in percentage points")
    quarter_kelly_stake_pct: float = Field(description="Recommended quarter-Kelly bankroll stake %")
    trade_url: str = Field(description="Direct Kalshi trading URL")


def fetch_tennis_edges(min_edge_pp: float = 8.0) -> list[KalshiTennisEdge]:
    """Fetches and parses live positive-EV tennis edges from iPredictSport.

    Args:
        min_edge_pp: Minimum fee-aware edge in percentage points (default: 8.0).

    Returns:
        List of typed KalshiTennisEdge objects.
    """
    resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    evals = data.get("kalshi_evaluations", [])

    results: list[KalshiTennisEdge] = []
    for item in evals:
        edge = float(item.get("edge_pp") or 0.0)
        ticker = item.get("ticker")
        match = item.get("match")

        if edge >= min_edge_pp and ticker and match:
            # Skip coin-flip deadband
            prob = float(item.get("our_p1") or 0.0)
            if 0.55 <= prob < 0.60:
                continue

            results.append(
                KalshiTennisEdge(
                    ticker=ticker,
                    match=match,
                    model_probability=round(prob, 3),
                    market_price=round(float(item.get("kalshi_p1") or 0.0), 2),
                    edge_percentage_points=round(edge, 1),
                    quarter_kelly_stake_pct=round(float(item.get("kelly_quarter") or 0.0) * 100, 2),
                    trade_url=item.get("trade_url") or "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                )
            )

    return results


def get_edges_dataframe(min_edge_pp: float = 8.0) -> pd.DataFrame:
    """Returns positive expected value Kalshi tennis trades as a clean pandas DataFrame.
    Ideal for pykalshi users running exploratory data analysis or backtesting.
    """
    edges = fetch_tennis_edges(min_edge_pp=min_edge_pp)
    if not edges:
        return pd.DataFrame(
            columns=[
                "ticker",
                "match",
                "model_probability",
                "market_price",
                "edge_percentage_points",
                "quarter_kelly_stake_pct",
                "trade_url",
            ]
        )
    return pd.DataFrame([e.model_dump() for e in edges])


if __name__ == "__main__":
    df = get_edges_dataframe(min_edge_pp=5.0)
    print(">> pykalshi iPredictSport Data Feed:")
    print(f"Loaded {len(df)} qualifying +EV markets.")
    if not df.empty:
        print(df.to_string(index=False))

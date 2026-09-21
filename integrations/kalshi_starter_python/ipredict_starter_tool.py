"""Official Kalshi Starter Code integration script for iPredictSport predictions.

Designed for drop-in use within Kalshi/kalshi-starter-code-python
and Kalshi/tools-and-analysis repositories.
"""

from __future__ import annotations

from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
IPREDICT_TRACK_RECORD_URL = "https://ipredictsport.com/track_record.json"


def fetch_live_predictions() -> dict[str, Any]:
    """Retrieves live machine learning forecasts from iPredictSport.
    Zero authentication or API key required.
    """
    resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def fetch_track_record() -> dict[str, Any]:
    """Retrieves verified out-of-sample benchmark metrics and calibration data."""
    resp = requests.get(IPREDICT_TRACK_RECORD_URL, timeout=10.0)
    resp.raise_for_status()
    return resp.json()


def print_market_evaluations(min_edge_pp: float = 8.0) -> None:
    """Evaluates upcoming Kalshi tennis contracts against machine learning fair odds."""
    feed = fetch_live_predictions()
    evals = feed.get("kalshi_evaluations", [])

    print("\n========================================================")
    print("  iPredictSport + Kalshi Market Edge Scanner")
    print(f"  Filtering: Fee-Aware Edge >= {min_edge_pp:.1f}pp")
    print("  Data Source: Free & Open (https://ipredictsport.com)")
    print("========================================================\n")

    qualifying = []
    for item in evals:
        edge = float(item.get("edge_pp") or 0.0)
        ticker = item.get("ticker")
        match = item.get("match")

        if edge >= min_edge_pp and ticker and match:
            prob = float(item.get("our_p1") or 0.0)
            price = float(item.get("kalshi_p1") or 0.0)
            kelly = float(item.get("kelly_quarter") or 0.0)

            qualifying.append(item)
            print(f"[*] Match: {match}")
            print(f"    Ticker:      {ticker}")
            print(f"    Model Prob:  {prob * 100:.1f}%")
            print(f"    Kalshi Ask:  {price * 100:.0f}¢")
            print(f"    Net Edge:    +{edge:.1f}pp")
            print(f"    1/4 Kelly:   {kelly * 100:.1f}% bankroll")
            print(f"    Trade Link:  {item.get('trade_url')}\n")

    if not qualifying:
        print(f"No active markets currently exceed the {min_edge_pp:.1f}pp threshold.")
        print("Tip: Run before match sessions or lower min_edge_pp to inspect near-market contracts.")

    print("========================================================\n")


def display_model_track_record() -> None:
    """Displays verified out-of-sample model performance and Brier score metrics."""
    record = fetch_track_record()
    overall = record.get("overall", {})

    print("\n========================================================")
    print("  iPredictSport Audited Model Track Record")
    print("========================================================")
    print(f"  Out-of-Sample Matches: {overall.get('n', 'N/A')}")
    acc = overall.get("accuracy")
    if acc is not None:
        print(f"  Audited Accuracy:      {float(acc) * 100:.1f}%")
    clv = overall.get("avg_clv_pp")
    if clv is not None:
        print(f"  Average CLV vs Market: +{float(clv):.2f}pp")
    brier = overall.get("our_brier")
    if brier is not None:
        print(f"  Model Brier Score:     {float(brier):.4f}")
    print("  Public Endpoint:       https://ipredictsport.com/track_record.json")
    print("========================================================\n")


if __name__ == "__main__":
    display_model_track_record()
    print_market_evaluations(min_edge_pp=5.0)

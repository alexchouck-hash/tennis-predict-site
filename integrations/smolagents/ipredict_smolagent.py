"""Hugging Face smolagents integration for iPredictSport tennis predictions."""

from __future__ import annotations

import requests

try:
    from smolagents import tool
except ImportError:
    # Decorator fallback if smolagents is not installed
    def tool(fn):
        return fn


@tool
def get_tennis_edges(min_edge_pp: float = 8.0) -> str:
    """Fetches upcoming ATP and WTA tennis matches where iPredictSport's machine learning model detects a positive expected value (+EV) edge against live Kalshi prediction market prices.

    Args:
        min_edge_pp: The minimum edge in percentage points to filter for (default 8.0).

    Returns:
        A formatted string summary of favorable betting edges and quarter-Kelly bankroll stake sizes.
    """
    try:
        resp = requests.get("https://ipredictsport.com/predictions.json", timeout=10.0)
        resp.raise_for_status()
        evals = resp.json().get("kalshi_evaluations", [])

        out = []
        for item in evals:
            edge = float(item.get("edge_pp") or 0.0)
            if edge >= min_edge_pp:
                out.append(
                    f"Match: {item.get('match')} | Model Prob: {float(item.get('our_p1', 0))*100:.1f}% | "
                    f"Kalshi Price: {float(item.get('kalshi_p1', 0))*100:.0f}¢ | Edge: +{edge:.1f}pp | "
                    f"¼-Kelly: {float(item.get('kelly_quarter', 0))*100:.1f}%"
                )

        if not out:
            return f"No prediction market edges found exceeding {min_edge_pp}pp."

        return f"Found {len(out)} qualifying +EV tennis trading edges:\n" + "\n".join(out)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return f"Error querying iPredictSport predictions: {exc}"

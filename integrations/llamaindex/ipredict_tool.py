"""LlamaIndex FunctionTool for iPredictSport tennis predictions."""

from __future__ import annotations

from typing import Any

import requests

FEED_URL = "https://ipredictsport.com/predictions.json"


def query_tennis_predictions(min_edge_pp: float = 8.0) -> dict[str, Any]:
    """Queries live point-level machine learning predictions and positive expected value (+EV) trading edges for professional ATP and WTA tennis matches.

    Args:
        min_edge_pp: Minimum fee-aware edge in percentage points.

    Returns:
        A dictionary containing upcoming matches and evaluated positive-EV trading opportunities.
    """
    try:
        resp = requests.get(FEED_URL, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        evals = data.get("kalshi_evaluations", [])

        qualifying_edges = [
            e for e in evals
            if float(e.get("edge_pp", 0.0)) >= min_edge_pp
        ]
        return {
            "status": "success",
            "upcoming_matches_count": len(data.get("upcoming_board", [])),
            "qualifying_edges_count": len(qualifying_edges),
            "edges": qualifying_edges,
        }
    except (requests.RequestException, ValueError, KeyError) as exc:
        return {"status": "error", "message": str(exc)}


def get_llamaindex_tool():
    """Build and return a LlamaIndex FunctionTool instance."""
    try:
        from llama_index.core.tools import FunctionTool
        return FunctionTool.from_defaults(
            fn=query_tennis_predictions,
            name="tennis_prediction_market_tool",
            description="Query live ATP/WTA tennis match win probabilities and positive-EV betting edges on Kalshi.",
        )
    except ImportError:
        raise ImportError("Package 'llama-index-core' is required. Install via: pip install llama-index-core")

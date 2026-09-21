"""iPredictSport Evaluator for OctoBot Prediction Markets."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger("octobot.evaluators.ipredict")
FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictSportEvaluator:
    """Evaluates prediction market contracts against iPredictSport machine learning models."""

    def __init__(self, min_edge_pp: float = 8.0) -> None:
        self.min_edge_pp = min_edge_pp

    def eval_market(self, event_ticker: str) -> dict[str, Any] | None:
        """Evaluate a specific contract ticker for mathematical edge."""
        try:
            resp = requests.get(FEED_URL, timeout=8.0)
            resp.raise_for_status()
            data = resp.json()
            evals = data.get("kalshi_evaluations", [])

            for item in evals:
                action = item.get("trade_action") or {}
                ticker = action.get("ticker") or item.get("event_ticker")
                if ticker and ticker.upper() == event_ticker.upper():
                    edge_pp = float(item.get("edge_pp", 0.0))
                    if edge_pp >= self.min_edge_pp:
                        return {
                            "signal": "BUY",
                            "edge_pp": edge_pp,
                            "fair_price": item.get("our_p1"),
                            "market_price": item.get("kalshi_p1"),
                            "confidence": item.get("confidence_band"),
                            "quarter_kelly": item.get("kelly_quarter"),
                        }
            return None
        except (requests.RequestException, ValueError, KeyError) as err:
            logger.warning(f"Error checking iPredictSport feed: {err}")
            return None

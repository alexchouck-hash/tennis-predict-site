"""Gnosis Prediction Market Agent Tooling integration for iPredictSport ML odds."""

from __future__ import annotations

import re
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictSportAgentTool:
    """Tool for Gnosis Prediction Market Agents (gnosis/prediction-market-agent-tooling & valory-xyz/trader).

    Analyzes binary prediction market questions (e.g. 'Will Carlos Alcaraz win against Jannik Sinner?')
    and returns point-level machine learning probabilities calibrated against out-of-sample data.
    """

    tool_name = "ipredict_tennis_probability_tool"
    description = (
        "Calculates calibrated win probabilities and +EV betting edges for tennis prediction markets."
    )

    def __init__(self, feed_url: str = IPREDICT_FEED_URL):
        self.feed_url = feed_url

    def _fetch_predictions(self) -> list[dict[str, Any]]:
        """Fetches active tennis match forecasts."""
        try:
            resp = requests.get(self.feed_url, timeout=10.0)
            resp.raise_for_status()
            return resp.json().get("matches", [])
        except (requests.RequestException, ValueError, KeyError):
            return []

    def predict_market(self, question: str) -> dict[str, Any]:
        """Parses question, extracts player identities, and resolves model win probability.

        Args:
            question: The prediction market question string.

        Returns:
            Dictionary containing matched player, opponent, model probability, and trading confidence.
        """
        matches = self._fetch_predictions()
        clean_q = question.lower()

        best_match = None
        target_player = ""
        model_prob = 0.50

        for m in matches:
            p1 = str(m.get("p1_name", "")).strip()
            p2 = str(m.get("p2_name", "")).strip()
            p1_prob_raw = m.get("p1_prob")
            p1_prob = float(p1_prob_raw) if p1_prob_raw is not None else 0.50

            # Tokenize surnames
            p1_last = p1.split()[-1].lower() if p1 else ""
            p2_last = p2.split()[-1].lower() if p2 else ""

            if p1_last and re.search(rf"\b{re.escape(p1_last)}\b", clean_q):
                best_match = m
                target_player = p1
                model_prob = p1_prob
                break
            elif p2_last and re.search(rf"\b{re.escape(p2_last)}\b", clean_q):
                best_match = m
                target_player = p2
                model_prob = 1.0 - p1_prob
                break

        if not best_match:
            return {
                "status": "unresolved",
                "question": question,
                "confidence": 0.0,
                "p_yes": 0.50,
                "note": "No matching scheduled tennis match found in iPredictSport feed.",
            }

        return {
            "status": "resolved",
            "question": question,
            "target_player": target_player,
            "match": best_match.get("match"),
            "tournament": best_match.get("tournament"),
            "surface": best_match.get("surface"),
            "p_yes": round(model_prob, 3),
            "p_no": round(1.0 - model_prob, 3),
            "confidence": round(abs(model_prob - 0.50) * 2.0, 2),
            "model_source": "iPredictSport Production ML (XGBoost/LightGBM blend)",
        }


if __name__ == "__main__":
    tool = IPredictSportAgentTool()
    res = tool.predict_market("Will Alcaraz defeat his opponent?")
    print(">> Gnosis PM Agent Tooling result:")
    print(res)

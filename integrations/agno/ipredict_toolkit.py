"""Agno (formerly Phidata) Toolkit integration for iPredictSport tennis predictions."""

from __future__ import annotations

import json
from typing import Any

import requests

try:
    from agno.tools import Toolkit
except ImportError:
    try:
        from phi.tools import (
            Toolkit,  # type: ignore # Backward compatibility with Phidata
        )
    except ImportError:
        class Toolkit:  # type: ignore
            def __init__(self, name: str = "toolkit"):
                self.name = name
                self.tools: list[Any] = []

            def register(self, fn: Any) -> None:
                self.tools.append(fn)

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
IPREDICT_TRACK_RECORD_URL = "https://ipredictsport.com/track_record.json"


class IPredictSportTools(Toolkit):
    """Toolkit for Agno / Phidata agents to query live tennis predictions and prediction market alpha."""

    def __init__(self, min_edge_pp: float = 8.0):
        super().__init__(name="ipredict_sport_tools")
        self.min_edge_pp = min_edge_pp
        self.register(self.get_positive_ev_edges)
        self.register(self.get_live_predictions)
        self.register(self.get_track_record)

    def get_positive_ev_edges(self, min_edge_pp: float | None = None) -> str:
        """Fetches upcoming ATP and WTA tennis matches where the machine learning model detects
        a positive expected value (+EV) edge against live Kalshi and Polymarket order book prices.

        Args:
            min_edge_pp: Minimum fee-aware edge in percentage points (defaults to toolkit configuration).

        Returns:
            JSON formatted summary of favorable trading opportunities with quarter-Kelly staking sizes.
        """
        threshold = self.min_edge_pp if min_edge_pp is None else min_edge_pp
        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            evals = data.get("kalshi_evaluations", [])

            opportunities = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                if edge >= threshold:
                    opportunities.append({
                        "match": item.get("match"),
                        "market_ticker": item.get("ticker"),
                        "model_probability": round(float(item.get("our_p1", 0.0)), 3),
                        "kalshi_price": round(float(item.get("kalshi_p1", 0.0)), 2),
                        "edge_percentage_points": round(edge, 1),
                        "quarter_kelly_stake_pct": round(float(item.get("kelly_quarter", 0.0)) * 100, 2),
                        "kalshi_trade_url": item.get("trade_url") or "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                    })

            if not opportunities:
                return json.dumps({
                    "status": "success",
                    "count": 0,
                    "message": f"No tennis market edges found exceeding {threshold}pp."
                })

            return json.dumps({
                "status": "success",
                "count": len(opportunities),
                "opportunities": opportunities
            }, indent=2)

        except (requests.RequestException, ValueError, KeyError) as exc:
            return json.dumps({"status": "error", "message": f"Error fetching predictions: {exc}"})

    def get_live_predictions(self, search_player: str = "") -> str:
        """Retrieves active tennis match forecasts and calibrated win probabilities.

        Args:
            search_player: Optional player name filter (e.g. 'Alcaraz', 'Swiatek').

        Returns:
            JSON summary of upcoming matches, tournament, court surface, and model forecast.
        """
        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            matches = resp.json().get("matches", [])

            q = search_player.strip().lower()
            filtered = []
            for m in matches:
                p1 = str(m.get("p1_name", "")).lower()
                p2 = str(m.get("p2_name", "")).lower()
                if not q or q in p1 or q in p2:
                    filtered.append({
                        "match": m.get("match"),
                        "tournament": m.get("tournament"),
                        "surface": m.get("surface"),
                        "p1": m.get("p1_name"),
                        "p2": m.get("p2_name"),
                        "p1_win_prob": round(float(m.get("p1_prob", 0.0)), 3),
                        "model_winner": m.get("predicted_winner"),
                    })

            return json.dumps({
                "status": "success",
                "count": len(filtered),
                "matches": filtered[:20]
            }, indent=2)

        except (requests.RequestException, ValueError, KeyError) as exc:
            return json.dumps({"status": "error", "message": f"Error fetching matches: {exc}"})

    def get_track_record(self) -> str:
        """Retrieves audited historical accuracy, Brier scores, and calibration metrics.

        Returns:
            JSON model track record and benchmark comparison against Tennis Abstract.
        """
        try:
            resp = requests.get(IPREDICT_TRACK_RECORD_URL, timeout=10.0)
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
        except (requests.RequestException, ValueError, KeyError) as exc:
            return json.dumps({"status": "error", "message": f"Error fetching track record: {exc}"})


if __name__ == "__main__":
    tools = IPredictSportTools()
    print(">> Testing Agno IPredictSportTools:")
    print(tools.get_positive_ev_edges(min_edge_pp=5.0))

"""CAMEL multi-agent framework toolkit for iPredictSport tennis predictions."""

from __future__ import annotations

import json
from typing import Any

import requests

try:
    from camel.toolkits import BaseToolkit, FunctionTool
except ImportError:
    class BaseToolkit:  # type: ignore
        def __init__(self):
            pass

        def get_tools(self) -> list[Any]:
            return []

    def FunctionTool(fn: Any) -> Any:  # type: ignore
        return fn

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
IPREDICT_TRACK_RECORD_URL = "https://ipredictsport.com/track_record.json"


class IPredictSportToolkit(BaseToolkit):
    """Toolkit for CAMEL communicative agents to query live tennis odds and betting alpha."""

    def __init__(self, min_edge_pp: float = 8.0):
        super().__init__()
        self.min_edge_pp = min_edge_pp

    def get_tennis_edges(self, min_edge: float | None = None) -> str:
        """Queries live ATP/WTA tennis match evaluations for positive expected value (+EV) betting edges.

        Args:
            min_edge: Minimum edge in percentage points (e.g. 8.0 for 8%).

        Returns:
            JSON string containing favorable betting opportunities and quarter-Kelly position sizes.
        """
        threshold = min_edge if min_edge is not None else self.min_edge_pp
        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            evals = resp.json().get("kalshi_evaluations", [])

            results = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                ticker = item.get("ticker")
                match = str(item.get("match") or "").strip()

                if edge >= threshold and ticker and match and match.lower() != "none":
                    results.append({
                        "match": match,
                        "ticker": ticker,
                        "model_probability": round(float(item.get("our_p1") or 0.0), 3),
                        "market_price": round(float(item.get("kalshi_p1") or 0.0), 2),
                        "edge_percentage_points": round(edge, 1),
                        "quarter_kelly_stake_pct": round(float(item.get("kelly_quarter") or 0.0) * 100, 2),
                        "trade_url": item.get("trade_url") or "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                    })

            return json.dumps({
                "status": "success",
                "count": len(results),
                "opportunities": results
            }, indent=2)
        except (requests.RequestException, ValueError, KeyError) as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    def get_track_record(self) -> str:
        """Retrieves audited out-of-sample benchmark metrics and Brier scores.

        Returns:
            JSON string with verified accuracy, CLV, and sample counts.
        """
        try:
            resp = requests.get(IPREDICT_TRACK_RECORD_URL, timeout=10.0)
            resp.raise_for_status()
            return json.dumps(resp.json(), indent=2)
        except (requests.RequestException, ValueError, KeyError) as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    def get_tools(self) -> list[Any]:
        return [
            FunctionTool(self.get_tennis_edges),
            FunctionTool(self.get_track_record),
        ]


if __name__ == "__main__":
    tk = IPredictSportToolkit()
    print(">> CAMEL Toolkit Test:")
    print(tk.get_tennis_edges(min_edge=5.0))

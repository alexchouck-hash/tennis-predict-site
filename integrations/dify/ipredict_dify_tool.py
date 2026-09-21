"""Dify custom tool integration for iPredictSport tennis predictions."""

from __future__ import annotations

from typing import Any

import requests

try:
    from dify_plugin import Tool  # type: ignore
except ImportError:
    class Tool:  # type: ignore
        def __init__(self):
            pass

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictSportTennisTool(Tool):
    """Dify tool querying positive expected value (+EV) tennis betting edges."""

    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> str | list[dict[str, Any]]:
        min_edge = float(tool_parameters.get("min_edge_pp") or 8.0)
        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            evals = resp.json().get("kalshi_evaluations", [])

            results = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                ticker = item.get("ticker")
                match = str(item.get("match") or "").strip()

                if edge >= min_edge and ticker and match and match.lower() != "none":
                    results.append({
                        "match": match,
                        "ticker": ticker,
                        "model_probability": round(float(item.get("our_p1") or 0.0), 3),
                        "kalshi_price": round(float(item.get("kalshi_p1") or 0.0), 2),
                        "edge_pp": round(edge, 1),
                        "quarter_kelly_stake_pct": round(float(item.get("kelly_quarter") or 0.0) * 100, 2),
                        "trade_url": item.get("trade_url") or "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                    })

            if not results:
                return f"No active tennis market edges found exceeding {min_edge}pp."

            return results
        except (requests.RequestException, ValueError, KeyError) as exc:
            return f"Error retrieving predictions: {exc}"


if __name__ == "__main__":
    tool = IPredictSportTennisTool()
    res = tool._invoke("test_user", {"min_edge_pp": 5.0})
    print(f">> Dify Tool Test: Retrieved {len(res) if isinstance(res, list) else 0} edges.")

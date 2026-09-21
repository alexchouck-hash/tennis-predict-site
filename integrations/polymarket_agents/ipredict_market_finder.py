"""Polymarket Agents tool for identifying +EV tennis contracts using iPredictSport ML odds."""

from __future__ import annotations

import json
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com/events"


class PolymarketTennisEvaluator:
    """Evaluates Polymarket tennis contracts against iPredictSport machine learning predictions."""

    def __init__(self, min_edge_pp: float = 8.0, max_spread: float = 0.15):
        self.min_edge_pp = min_edge_pp
        self.max_spread = max_spread

    def fetch_ipredict_forecasts(self) -> list[dict[str, Any]]:
        """Retrieves active ATP/WTA match predictions from iPredictSport."""
        resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("matches", [])

    def fetch_polymarket_tennis_events(self) -> list[dict[str, Any]]:
        """Queries Polymarket Gamma API for active tennis events and markets."""
        try:
            params = {"tag_slug": "tennis", "active": "true", "closed": "false", "limit": 50}
            resp = requests.get(POLYMARKET_GAMMA_API, params=params, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return []

    def calculate_quarter_kelly(self, win_prob: float, ask_price: float) -> float:
        """Calculates fee-aware quarter-Kelly sizing on a binary prediction market contract."""
        if ask_price <= 0.0 or ask_price >= 1.0 or win_prob <= ask_price:
            return 0.0
        # b is payout odds: (1 - ask) / ask
        b = (1.0 - ask_price) / ask_price
        full_kelly = (win_prob * b - (1.0 - win_prob)) / b
        quarter_kelly = max(0.0, 0.25 * full_kelly)
        return min(0.05, quarter_kelly)  # Cap at 5% bankroll risk per contract

    def scan_edges(self) -> list[dict[str, Any]]:
        """Cross-references iPredictSport forecasts against Polymarket tennis events."""
        ipredict_matches = self.fetch_ipredict_forecasts()
        poly_events = self.fetch_polymarket_tennis_events()

        opportunities = []

        # Map predictions by player name tokens for fuzzy matching
        pred_map = {}
        for m in ipredict_matches:
            p1 = str(m.get("p1_name", "")).strip()
            p2 = str(m.get("p2_name", "")).strip()
            p1_prob = float(m.get("p1_prob", 0.5))
            pred_map[p1.lower()] = {"match": m.get("match"), "player": p1, "prob": p1_prob}
            pred_map[p2.lower()] = {"match": m.get("match"), "player": p2, "prob": 1.0 - p1_prob}

        for event in poly_events:
            title = event.get("title", "")
            markets = event.get("markets", [])
            for market in markets:
                question = market.get("question", "")
                outcome_prices = market.get("outcomePrices")  # JSON string e.g. "[\"0.65\", \"0.35\"]"
                clob_token_ids = market.get("clobTokenIds")

                # Parse outcome prices
                prices = []
                if isinstance(outcome_prices, str):
                    try:
                        prices = [float(p) for p in json.loads(outcome_prices)]
                    except (ValueError, json.JSONDecodeError):
                        continue
                elif isinstance(outcome_prices, list):
                    prices = [float(p) for p in outcome_prices]

                if not prices or len(prices) < 2:
                    continue

                # Match against players
                for p_name_lower, info in pred_map.items():
                    if p_name_lower in question.lower() or p_name_lower in title.lower():
                        model_prob = info["prob"]
                        market_price = prices[0]  # Assuming Yes price for outcome 0
                        edge_pp = (model_prob - market_price) * 100.0

                        if edge_pp >= self.min_edge_pp:
                            q_kelly = self.calculate_quarter_kelly(model_prob, market_price)
                            opportunities.append({
                                "event_title": title,
                                "question": question,
                                "player": info["player"],
                                "match": info["match"],
                                "model_probability": round(model_prob, 3),
                                "polymarket_price": round(market_price, 3),
                                "edge_percentage_points": round(edge_pp, 1),
                                "quarter_kelly_stake_pct": round(q_kelly * 100.0, 2),
                                "market_slug": market.get("slug"),
                                "condition_id": market.get("conditionId"),
                                "clob_token_ids": clob_token_ids,
                            })

        return opportunities


def get_polymarket_tennis_tool(min_edge_pp: float = 8.0) -> str:
    """Tool function callable by LangChain, AutoGen, or Polymarket Agent frameworks."""
    evaluator = PolymarketTennisEvaluator(min_edge_pp=min_edge_pp)
    try:
        edges = evaluator.scan_edges()
        if not edges:
            return json.dumps({
                "status": "success",
                "count": 0,
                "message": f"No Polymarket tennis edges found exceeding {min_edge_pp}pp."
            })
        return json.dumps({
            "status": "success",
            "count": len(edges),
            "opportunities": edges
        }, indent=2)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return json.dumps({"status": "error", "message": f"Scan failed: {exc}"})


if __name__ == "__main__":
    print(">> Scanning Polymarket for +EV Tennis Contracts...")
    evaluator = PolymarketTennisEvaluator(min_edge_pp=5.0)
    res = evaluator.scan_edges()
    print(f"Found {len(res)} matching opportunities.")
    if res:
        print(json.dumps(res[0], indent=2))

"""Manifold Markets automated trading bot for tennis predictions."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
MANIFOLD_API_BASE = "https://api.manifold.markets/v0"


class ManifoldTennisBot:
    """Evaluates and trades Manifold Markets tennis contracts using iPredictSport ML odds."""

    def __init__(self, api_key: str | None = None, min_edge_pp: float = 8.0, dry_run: bool = True):
        self.api_key = api_key or os.getenv("MANIFOLD_API_KEY", "")
        self.min_edge_pp = min_edge_pp
        self.dry_run = dry_run
        self.headers = {"Authorization": f"Key {self.api_key}"} if self.api_key else {}

    def fetch_predictions(self) -> list[dict[str, Any]]:
        """Retrieves active ATP/WTA predictions from iPredictSport."""
        resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("matches", [])

    def search_manifold_tennis_markets(self) -> list[dict[str, Any]]:
        """Searches Manifold for active tennis markets."""
        try:
            params = {"term": "tennis", "filter": "open", "limit": 50}
            resp = requests.get(f"{MANIFOLD_API_BASE}/search-markets", params=params, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return []

    def evaluate_markets(self) -> list[dict[str, Any]]:
        """Finds mispriced Manifold tennis markets."""
        predictions = self.fetch_predictions()
        manifold_markets = self.search_manifold_tennis_markets()

        player_map = {}
        for m in predictions:
            p1 = str(m.get("p1_name", "")).strip()
            p2 = str(m.get("p2_name", "")).strip()
            p1_prob = float(m.get("p1_prob", 0.5))
            player_map[p1.lower()] = {"match": m.get("match"), "player": p1, "prob": p1_prob}
            player_map[p2.lower()] = {"match": m.get("match"), "player": p2, "prob": 1.0 - p1_prob}

        edges = []
        for market in manifold_markets:
            question = market.get("question", "")
            market_prob = float(market.get("probability", 0.5))
            market_id = market.get("id")

            for p_name_lower, info in player_map.items():
                if p_name_lower in question.lower():
                    model_prob = info["prob"]
                    edge_pp = (model_prob - market_prob) * 100.0

                    if abs(edge_pp) >= self.min_edge_pp:
                        outcome = "YES" if edge_pp > 0 else "NO"
                        edges.append({
                            "market_id": market_id,
                            "question": question,
                            "player": info["player"],
                            "match": info["match"],
                            "model_probability": round(model_prob, 3),
                            "manifold_probability": round(market_prob, 3),
                            "edge_percentage_points": round(abs(edge_pp), 1),
                            "recommended_outcome": outcome,
                            "url": market.get("url"),
                        })

        return edges

    def place_bet(self, market_id: str, outcome: str, amount_mana: int = 50) -> dict[str, Any]:
        """Submits a bet to Manifold API (simulated if dry_run=True)."""
        if self.dry_run:
            return {"status": "simulated", "market_id": market_id, "outcome": outcome, "amount": amount_mana}

        if not self.api_key:
            raise ValueError("MANIFOLD_API_KEY required for live execution.")

        payload = {"amount": amount_mana, "contractId": market_id, "outcome": outcome}
        resp = requests.post(f"{MANIFOLD_API_BASE}/bet", json=payload, headers=self.headers, timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    def run_cycle(self) -> None:
        """Executes a full scan and trading pass."""
        print(f"[{time.strftime('%X')}] Scanning Manifold Markets against iPredictSport...")
        edges = self.evaluate_markets()
        print(f"Identified {len(edges)} qualifying edges (>= {self.min_edge_pp}pp).")

        for edge in edges:
            print(
                f"  -> {edge['question']}: Model {edge['model_probability']*100:.1f}% vs "
                f"Manifold {edge['manifold_probability']*100:.1f}% | Recommendation: {edge['recommended_outcome']} "
                f"(+{edge['edge_percentage_points']}pp)"
            )
            if not self.dry_run:
                res = self.place_bet(edge["market_id"], edge["recommended_outcome"])
                print(f"     Order response: {res.get('status', 'submitted')}")


if __name__ == "__main__":
    bot = ManifoldTennisBot(dry_run=True, min_edge_pp=5.0)
    bot.run_cycle()

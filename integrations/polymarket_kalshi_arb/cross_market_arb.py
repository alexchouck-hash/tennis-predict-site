"""Cross-platform arbitrage and statistical mispricing scanner for Polymarket and Kalshi."""

from __future__ import annotations

import json
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com/events"


class CrossMarketArbitrageScanner:
    """Scans for cross-platform arbitrage (synthetic risk-free spreads) and model-driven
    statistical discrepancies between Kalshi and Polymarket tennis order books.
    """

    def __init__(self, min_synthetic_spread: float = 0.03, min_stat_edge_pp: float = 6.0):
        self.min_synthetic_spread = min_synthetic_spread
        self.min_stat_edge_pp = min_stat_edge_pp

    def fetch_ipredict_data(self) -> dict[str, Any]:
        """Retrieves point-level machine learning odds and Kalshi evaluations."""
        resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    def fetch_polymarket_tennis(self) -> list[dict[str, Any]]:
        """Pulls open tennis events from Polymarket Gamma API."""
        try:
            params = {"tag_slug": "tennis", "active": "true", "closed": "false", "limit": 50}
            resp = requests.get(POLYMARKET_GAMMA_URL, params=params, timeout=10.0)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException:
            pass
        return []

    def scan(self) -> dict[str, list[dict[str, Any]]]:
        """Identifies pure synthetic arbitrage and cross-market statistical discrepancies."""
        feed = self.fetch_ipredict_data()
        poly_events = self.fetch_polymarket_tennis()

        kalshi_evals = feed.get("kalshi_evaluations", [])
        matches = feed.get("matches", [])

        # Build player prediction dictionary
        player_model: dict[str, dict[str, Any]] = {}
        for m in matches:
            p1 = str(m.get("p1_name", "")).strip()
            p2 = str(m.get("p2_name", "")).strip()
            raw_prob = m.get("p1_prob")
            p1_prob = float(raw_prob) if raw_prob is not None else 0.50
            player_model[p1.lower()] = {
                "player": p1,
                "opponent": p2,
                "match": m.get("match"),
                "prob": p1_prob,
            }
            player_model[p2.lower()] = {
                "player": p2,
                "opponent": p1,
                "match": m.get("match"),
                "prob": 1.0 - p1_prob,
            }

        # Build Kalshi price dictionary
        kalshi_prices: dict[str, float] = {}
        for k in kalshi_evals:
            match_name = str(k.get("match", "")).lower()
            raw_val = k.get("kalshi_p1")
            price = float(raw_val) if raw_val is not None else 0.0
            kalshi_prices[match_name] = price

        synthetic_arbs = []
        statistical_discrepancies = []

        for event in poly_events:
            title = event.get("title", "")
            for market in event.get("markets", []):
                question = market.get("question", "")
                raw_prices = market.get("outcomePrices")
                prices = []
                if isinstance(raw_prices, str):
                    try:
                        prices = [float(p) for p in json.loads(raw_prices)]
                    except (ValueError, json.JSONDecodeError):
                        continue
                elif isinstance(raw_prices, list):
                    prices = [float(p) for p in raw_prices]

                if not prices or len(prices) < 2:
                    continue

                poly_p1_price = prices[0]

                # Match with player model
                for p_name_lower, info in player_model.items():
                    if p_name_lower in question.lower() or p_name_lower in title.lower():
                        match_key = str(info["match"]).lower()
                        kalshi_price = kalshi_prices.get(match_key)

                        if kalshi_price is not None and kalshi_price > 0:
                            # 1. Pure Synthetic Arbitrage:
                            # Buy Yes on Polymarket (cost: poly_p1_price) + Buy Opponent on Kalshi (cost: 1 - kalshi_price)
                            # Total combined cost = poly_p1_price + (1.0 - kalshi_price)
                            combined_cost_1 = poly_p1_price + (1.0 - kalshi_price)
                            if combined_cost_1 < (1.0 - self.min_synthetic_spread):
                                synthetic_arbs.append({
                                    "type": "pure_synthetic_arbitrage",
                                    "match": info["match"],
                                    "leg1": f"Buy {info['player']} on Polymarket @ {poly_p1_price:.2f}",
                                    "leg2": f"Buy {info['opponent']} on Kalshi @ {(1.0 - kalshi_price):.2f}",
                                    "total_cost": round(combined_cost_1, 3),
                                    "guaranteed_payout": 1.00,
                                    "net_risk_free_profit_pct": round((1.0 - combined_cost_1) * 100.0, 2),
                                })

                            # 2. Cross-Market Discrepancy / Statistical Divergence
                            price_diff_pp = (kalshi_price - poly_p1_price) * 100.0
                            if abs(price_diff_pp) >= self.min_stat_edge_pp:
                                model_prob = info["prob"]
                                statistical_discrepancies.append({
                                    "match": info["match"],
                                    "player": info["player"],
                                    "model_fair_probability": round(model_prob, 3),
                                    "polymarket_price": round(poly_p1_price, 2),
                                    "kalshi_price": round(kalshi_price, 2),
                                    "divergence_pp": round(price_diff_pp, 1),
                                    "preferred_execution_venue": "Polymarket" if poly_p1_price < kalshi_price else "Kalshi",
                                })

        return {
            "synthetic_arbitrages": synthetic_arbs,
            "statistical_discrepancies": statistical_discrepancies,
        }


if __name__ == "__main__":
    scanner = CrossMarketArbitrageScanner()
    results = scanner.scan()
    print(">> Cross-Market Arbitrage & Discrepancy Scanner:")
    print(f"Synthetic Arbs: {len(results['synthetic_arbitrages'])}")
    print(f"Statistical Discrepancies: {len(results['statistical_discrepancies'])}")

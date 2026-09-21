"""Signal generation strategy for Kalshi auto-traders (kalshi-ai-trading-bot & Kalshi-Quant-TeleBot)."""

from __future__ import annotations

import time
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class KalshiQuantSignalEngine:
    """Quantitative signal engine for Python Kalshi trading bots."""

    def __init__(
        self,
        bankroll_usd: float = 1000.0,
        min_edge_pp: float = 8.0,
        max_spread: float = 0.15,
        max_stake_fraction: float = 0.05,
    ):
        self.bankroll_usd = bankroll_usd
        self.min_edge_pp = min_edge_pp
        self.max_spread = max_spread
        self.max_stake_fraction = max_stake_fraction

    def calculate_taker_fee(self, price: float) -> float:
        """Computes Kalshi taker fee: 0.07 * p * (1 - p). Resting maker orders pay 0.0."""
        return 0.07 * price * (1.0 - price)

    def calculate_quarter_kelly_stake(self, win_prob: float, ask_price: float) -> tuple[float, int]:
        """Calculates quarter-Kelly stake in USD and number of contracts."""
        if ask_price <= 0.0 or ask_price >= 1.0:
            return 0.0, 0

        fee = self.calculate_taker_fee(ask_price)
        net_prob = win_prob - fee
        if net_prob <= ask_price:
            return 0.0, 0

        b = (1.0 - ask_price) / ask_price
        full_kelly = (net_prob * b - (1.0 - net_prob)) / b
        quarter_kelly = max(0.0, 0.25 * full_kelly)
        clamped_fraction = min(self.max_stake_fraction, quarter_kelly)

        stake_usd = clamped_fraction * self.bankroll_usd
        contract_cost = ask_price
        contract_count = int(stake_usd // contract_cost) if contract_cost > 0 else 0

        return round(stake_usd, 2), contract_count

    def generate_orders(self) -> list[dict[str, Any]]:
        """Evaluates active board and returns executable Kalshi order payloads."""
        resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        evals = resp.json().get("kalshi_evaluations", [])

        executable_orders = []

        for item in evals:
            ticker = item.get("ticker")
            match = item.get("match")
            if not ticker or not match:
                continue

            model_prob = float(item.get("our_p1") or 0.0)
            market_price = float(item.get("kalshi_p1") or 0.0)
            edge_pp = float(item.get("edge_pp") or 0.0)

            # Rule 1: Edge floor (>= 8.0pp)
            if edge_pp < self.min_edge_pp:
                continue

            # Rule 2: Exclude coin-flip deadband [0.55, 0.60)
            if 0.55 <= model_prob < 0.60:
                continue

            stake_usd, contracts = self.calculate_quarter_kelly_stake(model_prob, market_price)
            if contracts <= 0:
                continue

            # Formulate standard Kalshi API order payload
            order = {
                "ticker": ticker,
                "action": "buy",
                "side": "yes",
                "type": "limit",
                "yes_price": round(market_price * 100),  # In cents (1-99)
                "count": contracts,
                "client_order_id": f"ipredict_{int(time.time())}_{ticker[:8]}",
                "post_only": True,  # Ensures 0% maker fee
                "metadata": {
                    "match": match,
                    "model_probability": round(model_prob, 3),
                    "edge_percentage_points": round(edge_pp, 1),
                    "stake_usd": stake_usd,
                    "partner_ref": "eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                },
            }
            executable_orders.append(order)

        return executable_orders


if __name__ == "__main__":
    engine = KalshiQuantSignalEngine(min_edge_pp=5.0)
    orders = engine.generate_orders()
    print(f">> KalshiQuantSignalEngine: Generated {len(orders)} order payloads.")
    if orders:
        print("Sample Order:", orders[0])

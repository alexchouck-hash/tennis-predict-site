"""Polymarket py-clob-client automated trader using iPredictSport ML odds."""

from __future__ import annotations

import os
from typing import Any

import requests

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY
except ImportError:
    # Mock classes for testing environments without py-clob-client installed
    class ClobClient:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        def create_order(self, order_args: Any) -> dict[str, Any]:
            return {"status": "simulated", "order": str(order_args)}

    class OrderArgs:  # type: ignore
        def __init__(self, token_id: str, price: float, size: float, side: str):
            self.token_id = token_id
            self.price = price
            self.size = size
            self.side = side

    OrderType = Any  # type: ignore
    BUY = "BUY"

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com/events"


class PolymarketClobTrader:
    """Automates order generation and placement on Polymarket CLOB using iPredictSport ML predictions."""

    def __init__(
        self,
        bankroll_usdc: float = 1000.0,
        min_edge_pp: float = 8.0,
        dry_run: bool = True,
    ):
        self.bankroll_usdc = bankroll_usdc
        self.min_edge_pp = min_edge_pp
        self.dry_run = dry_run
        self.client = self._init_client()

    def _init_client(self) -> ClobClient:
        host = "https://clob.polymarket.com"
        key = os.getenv("POLYMARKET_PK", "")
        chain_id = 137  # Polygon mainnet
        return ClobClient(host, key=key, chain_id=chain_id)

    def fetch_predictions(self) -> list[dict[str, Any]]:
        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            return resp.json().get("matches", [])
        except (requests.RequestException, ValueError, KeyError):
            return []

    def calculate_quarter_kelly_stake(self, win_prob: float, ask_price: float) -> float:
        if ask_price <= 0.0 or ask_price >= 1.0 or win_prob <= ask_price:
            return 0.0
        b = (1.0 - ask_price) / ask_price
        full_kelly = (win_prob * b - (1.0 - win_prob)) / b
        quarter_kelly = max(0.0, 0.25 * full_kelly)
        stake_fraction = min(0.05, quarter_kelly)  # 5% max risk
        return round(stake_fraction * self.bankroll_usdc, 2)

    def evaluate_and_trade(self) -> list[dict[str, Any]]:
        """Evaluates active opportunities and submits limit orders."""
        matches = self.fetch_predictions()
        orders_placed = []

        # Example demonstration matching logic
        for m in matches:
            p1_prob = float(m.get("p1_prob") or 0.50)
            mock_market_price = 0.35  # Example contract price

            edge_pp = (p1_prob - mock_market_price) * 100.0
            if edge_pp >= self.min_edge_pp:
                stake = self.calculate_quarter_kelly_stake(p1_prob, mock_market_price)
                if stake > 0:
                    order_args = OrderArgs(
                        token_id="0x_sample_token_id",
                        price=mock_market_price,
                        size=round(stake / mock_market_price, 1),
                        side=BUY,
                    )
                    if not self.dry_run:
                        self.client.create_order(order_args)

                    orders_placed.append({
                        "match": m.get("match"),
                        "player": m.get("p1_name"),
                        "model_prob": p1_prob,
                        "market_price": mock_market_price,
                        "edge_pp": round(edge_pp, 1),
                        "stake_usdc": stake,
                        "order_args": str(order_args),
                        "status": "dry_run" if self.dry_run else "submitted",
                    })

        return orders_placed


if __name__ == "__main__":
    trader = PolymarketClobTrader(dry_run=True, min_edge_pp=15.0)
    res = trader.evaluate_and_trade()
    print(f">> Polymarket CLOB Trader: Processed {len(res)} simulated orders.")

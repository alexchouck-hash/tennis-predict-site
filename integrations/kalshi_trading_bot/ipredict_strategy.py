"""Drop-in Strategy for Viprasol-Tech/kalshi-trading-bot.

Integrates iPredictSport's free point-level ML probabilities and quarter-Kelly sizing
into the Viprasol algorithmic trading framework.

Usage:
  1. Copy this file into your `src/kalshi_trading_bot/strategies/` directory.
  2. Register in your strategy registry or run:
     kalshi-bot run --strategy ipredict_tennis --dry-run
"""

from __future__ import annotations

import logging
import math
from typing import Any

import requests

# Kalshi referral bonus for fee credits
KALSHI_REFERRAL_URL = "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d"
PREDICTIONS_URL = "https://ipredictsport.com/predictions.json"

logger = logging.getLogger("kalshi_trading_bot.strategies.ipredict")


class IPredictTennisStrategy:
    """Strategy that executes resting limit orders based on iPredictSport ML models."""

    name = "ipredict_tennis"

    def __init__(
        self,
        min_edge_pp: float = 8.0,
        max_spread: float = 0.15,
        min_confidence: str = "medium_plus",
        bankroll_usd: float = 1000.0,
        max_stake_fraction: float = 0.05,
    ) -> None:
        self.min_edge_pp = min_edge_pp
        self.max_spread = max_spread
        self.min_confidence = min_confidence
        self.bankroll_usd = bankroll_usd
        self.max_stake_fraction = max_stake_fraction
        self.conf_ranks = {"any": 0, "low": 1, "medium": 2, "medium_plus": 2, "high": 3, "high_only": 3, "very_high": 4}

    def fetch_evaluations(self) -> list[dict[str, Any]]:
        """Fetch latest market evaluations from iPredictSport open feed."""
        headers = {"User-Agent": "kalshi-trading-bot (ipredict-plugin)"}
        try:
            resp = requests.get(PREDICTIONS_URL, headers=headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json().get("kalshi_evaluations", [])
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.error(f"Failed to fetch iPredictSport predictions: {exc}")
            return []

    def calculate_signals(self) -> list[dict[str, Any]]:
        """Evaluate open markets and return actionable resting order payloads."""
        evaluations = self.fetch_evaluations()
        signals = []
        req_rank = self.conf_ranks.get(self.min_confidence, 2)

        for item in evaluations:
            match = item.get("match")
            our_p1 = item.get("our_p1")
            kalshi_p1 = item.get("kalshi_p1")
            if not match or our_p1 is None or kalshi_p1 is None:
                continue

            c_band = str(item.get("confidence_band") or "low").lower()
            if self.conf_ranks.get(c_band, 1) < req_rank:
                continue

            # Model prob vs market ask
            ask = float(kalshi_p1)
            model_p = float(our_p1)

            # Skip MX2 coin-flip deadband [0.55, 0.60)
            if 0.55 <= model_p < 0.60:
                continue

            # Taker fee deduction (0.07 * p * (1 - p))
            fee = 0.07 * ask * (1.0 - ask)
            edge_pp = (model_p - ask - fee) * 100.0

            if edge_pp < self.min_edge_pp:
                continue

            # Quarter-Kelly staking
            b = (1.0 - ask) / ask
            raw_kelly = ((model_p - fee) * b - (1.0 - (model_p - fee))) / b
            quarter_kelly = max(0.0, raw_kelly * 0.25)
            quarter_kelly = min(quarter_kelly, self.max_stake_fraction)

            stake_usd = self.bankroll_usd * quarter_kelly
            contracts = math.floor(stake_usd / ask) if ask > 0 else 0

            if contracts < 1:
                continue

            trade_action = item.get("trade_action") or {}
            ticker = trade_action.get("ticker") or item.get("event_ticker")
            if not ticker:
                ticker = "KXATPMATCH-" + match.replace(" vs ", "-").replace(" ", "").upper()[:16]

            signals.append({
                "ticker": ticker,
                "match": match,
                "action": "buy",
                "side": "yes",
                "type": "limit",
                "price_cents": round(ask * 100),
                "count": contracts,
                "stake_usd": round(stake_usd, 2),
                "edge_pp": round(edge_pp, 1),
                "post_only": True,  # Capture maker rebate ($0 fee)
            })

        return signals

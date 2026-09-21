"""Discord Webhook Alert Bot for iPredictSport tennis betting edges."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ipredict.discord_bot")

KALSHI_REFERRAL_URL = os.getenv("KALSHI_REFERRAL_URL", "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d")
PREDICTIONS_FEED_URL = os.getenv("PREDICTIONS_FEED_URL", "https://ipredictsport.com/predictions.json")


def fetch_edges(min_edge_pp: float = 8.0) -> list[dict[str, Any]]:
    """Fetch positive-EV edges from iPredictSport feed."""
    try:
        resp = requests.get(PREDICTIONS_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        evals = resp.json().get("kalshi_evaluations", [])
        return [
            e for e in evals
            if float(e.get("edge_pp") or 0.0) >= min_edge_pp
            and str(e.get("confidence_band", "")).lower() in ("medium", "high", "very_high")
        ]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error(f"Error fetching edges: {exc}")
        return []


def send_discord_alert(webhook_url: str, edge: dict[str, Any]) -> bool:
    """Send formatted rich embed to Discord webhook."""
    match = edge.get("match", "Tennis Match")
    our_p = float(edge.get("our_p1", 0.5))
    kalshi_p = float(edge.get("kalshi_p1", 0.5))
    edge_pp = float(edge.get("edge_pp", 0.0))
    kelly = float(edge.get("kelly_quarter", 0.0))
    c_band = str(edge.get("confidence_band", "medium")).capitalize()

    action = edge.get("trade_action") or {}
    trade_url = action.get("url") or action.get("trade_url") or KALSHI_REFERRAL_URL

    embed = {
        "title": f"🎾 +EV Tennis Edge: {match}",
        "url": trade_url,
        "color": 0x22C55E,  # Emerald Green
        "description": f"Quantitative model detects a **+{edge_pp:.1f}pp mathematical edge** on Kalshi.",
        "fields": [
            {"name": "Model Win Prob", "value": f"**{our_p*100:.1f}%**", "inline": True},
            {"name": "Kalshi Price", "value": f"**{kalshi_p*100:.0f}¢**", "inline": True},
            {"name": "Expected Edge", "value": f"**+{edge_pp:.1f}pp**", "inline": True},
            {"name": "Confidence", "value": f"**{c_band}**", "inline": True},
            {"name": "¼-Kelly Sizing", "value": f"**{kelly*100:.1f}% of bankroll**", "inline": True},
            {"name": "Recommended Action", "value": "Place resting limit buy order", "inline": True},
            {
                "name": "🎁 Sign-Up Fee Credits",
                "value": f"[Claim Kalshi Bonus & Trade]({KALSHI_REFERRAL_URL})",
                "inline": False,
            },
        ],
        "footer": {
            "text": "Powered by iPredictSport.com | Not Financial Advice",
            "icon_url": "https://ipredictsport.com/favicon.ico",
        },
    }

    payload = {
        "username": "iPredictSport Quant Bot",
        "avatar_url": "https://ipredictsport.com/favicon.ico",
        "embeds": [embed],
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=10.0)
        res.raise_for_status()
        logger.info(f"Posted Discord alert for {match}")
        return True
    except requests.RequestException as err:
        logger.error(f"Failed to post to Discord webhook: {err}")
        return False


def main() -> None:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Set DISCORD_WEBHOOK_URL environment variable to run.")
        return

    edges = fetch_edges(min_edge_pp=8.0)
    print(f"Found {len(edges)} qualifying +EV edges.")
    for edge in edges:
        send_discord_alert(webhook_url, edge)


if __name__ == "__main__":
    main()

"""Telegram Alert Bot posting +EV tennis prediction market opportunities to channels or groups."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ipredict.telegram_bot")

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


def send_telegram_alert(bot_token: str, chat_id: str, edge: dict[str, Any]) -> bool:
    """Send formatted alert message with inline buttons via Telegram Bot API."""
    match = edge.get("match", "Match")
    our_p = float(edge.get("our_p1", 0.5))
    kalshi_p = float(edge.get("kalshi_p1", 0.5))
    edge_pp = float(edge.get("edge_pp", 0.0))
    kelly = float(edge.get("kelly_quarter", 0.0))
    c_band = str(edge.get("confidence_band", "medium")).capitalize()

    action = edge.get("trade_action") or {}
    trade_url = action.get("url") or action.get("trade_url") or KALSHI_REFERRAL_URL

    message = (
        f"🎾 <b>+EV Tennis Opportunity: {match}</b>\n\n"
        f"📊 <b>Model Win Prob:</b> <code>{our_p*100:.1f}%</code>\n"
        f"📈 <b>Kalshi Market Price:</b> <code>{kalshi_p*100:.0f}¢</code>\n"
        f"🔥 <b>Expected Edge:</b> <b>+{edge_pp:.1f}pp</b>\n"
        f"🎯 <b>Confidence:</b> {c_band}\n"
        f"💰 <b>Quarter-Kelly Stake:</b> <code>{kelly*100:.1f}% of bankroll</code>\n\n"
        f"<i>Tip: Submit resting limit orders to capture maker fee rebates ($0 taker fees).</i>"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🚀 Trade on Kalshi", "url": trade_url},
                {"text": "🎁 Claim $25 Bonus", "url": KALSHI_REFERRAL_URL},
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
        "disable_web_page_preview": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10.0)
        resp.raise_for_status()
        logger.info(f"Posted Telegram alert for {match}")
        return True
    except requests.RequestException as err:
        logger.error(f"Failed to post to Telegram: {err}")
        return False


def main() -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables to run.")
        return

    edges = fetch_edges(min_edge_pp=8.0)
    print(f"Found {len(edges)} qualifying +EV edges.")
    for edge in edges:
        send_telegram_alert(bot_token, chat_id, edge)


if __name__ == "__main__":
    main()

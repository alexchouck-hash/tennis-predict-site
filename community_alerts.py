#!/usr/bin/env python3
"""Community Alert Bot for iPredictSport: Discord & Telegram.

Broadcasts quantitative tennis predictions and positive-EV trading signals to
Discord servers and Telegram channels/groups.

Supported Alert Channels:
  1. Discord Webhook: DISCORD_WEBHOOK_URL in .env (recommended, zero-daemon)
  2. Discord Bot API: DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID in .env
  3. Telegram Bot API: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env (supports Inline Buttons)

CLI Usage:
  python scripts/community_alerts.py --dry-run           # Preview qualifying alerts without sending
  python scripts/community_alerts.py --test              # Send a mock test alert to verify credentials
  python scripts/community_alerts.py --once              # Process and send un-alerted edges right now
  python scripts/community_alerts.py --daemon            # Run continuous hourly alert loop
  python scripts/community_alerts.py --ignore-timing     # Ignore T-6h window (process all active edges)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root and .env are available
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    # Minimal fallback env parser if python-dotenv is absent
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

try:
    from tennis_predict.config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parent / "data"

SITE_URL = os.getenv("SITE_BASE", "https://ipredictsport.com").rstrip("/")
PREDICTIONS_LOCAL = REPO_ROOT / "site" / "predictions.json"
PREDICTIONS_REMOTE = f"{SITE_URL}/predictions.json"
STATE_FILE = DATA_DIR / "alerts_sent.json"

KALSHI_REFERRAL_URL = os.getenv(
    "KALSHI_REFERRAL_URL",
    "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
)


# ==============================================================================
# State & Deduplication
# ==============================================================================

def load_alert_state() -> dict[str, Any]:
    """Load sent alert history to prevent duplicate pings."""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # Prune records older than 7 days
        now_ts = time.time()
        pruned = {
            k: v for k, v in data.items()
            if isinstance(v, dict) and (now_ts - v.get("timestamp", 0)) < 7 * 86400
        }
        return pruned
    except Exception:
        return {}


def save_alert_state(state: dict[str, Any]) -> None:
    """Save sent alert history."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as err:
        print(f"[alerts] Warning: Failed to save state to {STATE_FILE}: {err}")


def make_alert_key(item: dict[str, Any]) -> str:
    """Construct unique identifier for a match pick opportunity."""
    trade_action = item.get("trade_action") or {}
    ticker = trade_action.get("ticker") or ""
    match = item.get("match") or ""
    pick = item.get("pick") or ""
    start = item.get("match_start") or ""
    return f"{ticker}:{match}:{pick}:{start}"


# ==============================================================================
# Feed Loading & Filtering
# ==============================================================================

def load_predictions() -> dict[str, Any]:
    """Load predictions from local file or HTTP fallback."""
    if PREDICTIONS_LOCAL.exists():
        try:
            return json.loads(PREDICTIONS_LOCAL.read_text(encoding="utf-8"))
        except Exception:
            pass

    req = urllib.request.Request(
        PREDICTIONS_REMOTE,
        headers={"User-Agent": "iPredictSport-Alerts/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        print(f"[alerts] Error loading predictions from {PREDICTIONS_REMOTE}: {err}")
        return {}


def parse_iso_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime safely."""
    if not dt_str:
        return None
    try:
        # Replace trailing 'Z' for fromisoformat compatibility
        clean = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def filter_qualifying_edges(
    data: dict[str, Any],
    min_edge_pp: float = 5.0,
    confidence_filter: tuple[str, ...] = ("high", "very_high"),
    ignore_timing: bool = False,
) -> list[dict[str, Any]]:
    """Filter evaluations for high-conviction positive-EV betting opportunities."""
    evals = data.get("kalshi_evaluations") or []
    qualifying = []
    now = datetime.now(timezone.utc)

    for item in evals:
        # 1. Edge & Conviction
        edge = float(item.get("edge_pp") or 0.0)
        if edge < min_edge_pp:
            continue

        conf = str(item.get("confidence_band") or "").lower()
        if confidence_filter and ("all" not in confidence_filter) and (conf not in confidence_filter):
            continue

        # 2. Decision & Kelly
        decision = str(item.get("board_decision") or "").upper()
        kelly = float(item.get("kelly_quarter") or 0.0)
        # Must be recommended BUY or positive Kelly stake
        if decision not in ("BUY", "WATCH") and kelly <= 0.0:
            continue

        # 3. Timing Window (Target T-6h: match starts in 1h to 14h)
        match_start = parse_iso_datetime(item.get("match_start"))
        if not ignore_timing and match_start:
            hours_to_start = (match_start - now).total_seconds() / 3600.0
            # Skip if match is in the past, or > 14h away (too early for liquidity)
            if hours_to_start < 0.5 or hours_to_start > 14.0:
                continue

        qualifying.append(item)

    # Sort descending by edge_pp
    qualifying.sort(key=lambda x: float(x.get("edge_pp") or 0.0), reverse=True)
    return qualifying


# ==============================================================================
# Alert Formatters: Discord & Telegram
# ==============================================================================

def format_discord_payload(item: dict[str, Any], is_update: bool = False, is_test: bool = False) -> dict[str, Any]:
    """Create rich Discord Embed payload."""
    pick = item.get("pick") or "Favorite"
    match = item.get("match") or (f"{pick} Match" if pick != "Favorite" else "Tennis Match")
    tourney = item.get("tourney") or "ATP/WTA Tour"
    surface = (item.get("surface") or "court").capitalize()
    rnd = item.get("round") or "Main Draw"
    prob = float(item.get("pick_win_prob") or 0.5) * 100.0
    ask = float(item.get("market_price") or 0.5) * 100.0
    edge = float(item.get("edge_pp") or 0.0)
    kelly = float(item.get("kelly_quarter") or 0.0) * 100.0
    conf = str(item.get("confidence_band") or "standard").replace("_", " ").title()
    start_str = item.get("match_start") or "Upcoming"

    trade_action = item.get("trade_action") or {}
    direct_url = trade_action.get("direct_trade_url") or KALSHI_REFERRAL_URL
    cta_text = trade_action.get("cta") or "Trade on Kalshi ($25 Bonus)"

    # Status badge & color
    # Green = 0x00E676 (65406), Gold = 0xFFD600 (16766464), Purple = 0x7C4DFF (8146431)
    color = 65406 if edge >= 10.0 else 16766464

    title_prefix = "🧪 [TEST ALERT] " if is_test else ("🔄 [LINE UPDATE] " if is_update else "🎾 ")
    title = f"{title_prefix}{tourney} ({surface}): {match}"

    fields = [
        {"name": "🎯 Recommended Pick", "value": f"**{pick}**", "inline": True},
        {"name": "📈 Model Fair Win %", "value": f"**{prob:.1f}%**", "inline": True},
        {"name": "🏷️ Kalshi Market Price", "value": f"{ask:.0f}¢ ({ask:.1f}%)", "inline": True},
        {"name": "💎 Edge Advantage", "value": f"**+{edge:.1f} pp**", "inline": True},
        {"name": "📊 Quarter-Kelly Stake", "value": f"**{kelly:.2f}%** bankroll" if kelly > 0 else "Flat / 1u", "inline": True},
        {"name": "🔒 Confidence Tier", "value": f"{conf}", "inline": True},
        {"name": "⏰ Scheduled Start", "value": f"`{start_str}`", "inline": True},
        {"name": "⚡ Live Order Execution", "value": f"[**{cta_text}**]({direct_url})", "inline": False},
    ]

    embed = {
        "title": title,
        "description": (
            "Positive-EV market disagreement detected against prediction market books. "
            "Model parameters calibrated on point-level Markov transition chains at T-6h depth."
        ),
        "color": color,
        "fields": fields,
        "footer": {
            "text": "iPredictSport Quantitative Analytics • Not financial advice • CFTC Rule 4.41 applies",
            "icon_url": "https://ipredictsport.com/favicon.ico",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "username": "iPredictSport Quant Bot",
        "avatar_url": "https://ipredictsport.com/favicon.ico",
        "embeds": [embed],
    }


def format_telegram_payload(
    chat_id: str,
    item: dict[str, Any],
    is_update: bool = False,
    is_test: bool = False,
) -> dict[str, Any]:
    """Create rich Telegram HTML message payload with Inline Keyboard Buttons."""
    pick = item.get("pick") or "Favorite"
    match = item.get("match") or (f"{pick} Match" if pick != "Favorite" else "Tennis Match")
    tourney = item.get("tourney") or "ATP/WTA Tour"
    surface = (item.get("surface") or "court").capitalize()
    rnd = item.get("round") or "Main Draw"
    prob = float(item.get("pick_win_prob") or 0.5) * 100.0
    ask = float(item.get("market_price") or 0.5) * 100.0
    edge = float(item.get("edge_pp") or 0.0)
    kelly = float(item.get("kelly_quarter") or 0.0) * 100.0
    conf = str(item.get("confidence_band") or "standard").replace("_", " ").title()
    start_str = item.get("match_start") or "Upcoming"

    trade_action = item.get("trade_action") or {}
    direct_url = trade_action.get("direct_trade_url") or KALSHI_REFERRAL_URL

    prefix = "🧪 <b>[TEST ALERT]</b>\n" if is_test else ("🔄 <b>[LINE UPDATE]</b>\n" if is_update else "")

    text = (
        f"{prefix}🎾 <b>iPredictSport +EV Market Alert</b>\n\n"
        f"<b>Tournament:</b> {tourney} ({surface}, {rnd})\n"
        f"<b>Match:</b> {match}\n"
        f"<b>Start Time:</b> <code>{start_str}</code>\n\n"
        f"🎯 <b>Value Pick:</b> <b>{pick}</b>\n"
        f"📈 <b>Model Fair Win %:</b> <b>{prob:.1f}%</b>\n"
        f"🏷️ <b>Market Price:</b> {ask:.0f}¢ ({ask:.1f}% implied)\n"
        f"💎 <b>Estimated Edge:</b> <b>+{edge:.1f} pp</b>\n"
        f"📊 <b>Quarter-Kelly Allocation:</b> <b>{kelly:.2f}%</b> bankroll\n"
        f"🔒 <b>Model Confidence:</b> {conf}\n\n"
        f"<i>Not financial advice. Predictions are quantitative estimates from public data.</i>"
    )

    inline_keyboard = [
        [
            {"text": "⚡ Trade on Kalshi ($25 Bonus)", "url": direct_url},
            {"text": "📊 Live Board & Stats", "url": SITE_URL},
        ]
    ]

    return {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
        "reply_markup": {"inline_keyboard": inline_keyboard},
    }


# ==============================================================================
# Dispatchers: HTTP POST to Discord & Telegram
# ==============================================================================

def send_http_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> tuple[bool, str]:
    """Execute synchronous JSON HTTP POST request using stdlib."""
    req_headers = {
        "Content-Type": "application/json",
        "User-Agent": "iPredictSport-CommunityAlerts/1.0",
    }
    if headers:
        req_headers.update(headers)

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            resp_body = resp.read().decode("utf-8")
            return True, f"HTTP {resp.status}: {resp_body[:100]}"
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8", errors="ignore")
        return False, f"HTTP {err.code}: {err.reason} - {err_msg[:200]}"
    except Exception as exc:
        return False, f"Connection error: {exc}"


def broadcast_to_discord(
    item: dict[str, Any],
    is_update: bool = False,
    is_test: bool = False,
) -> tuple[bool, str]:
    """Send alert to Discord via Webhook URL or Bot Token."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    channel_id = os.getenv("DISCORD_CHANNEL_ID", "").strip()

    payload = format_discord_payload(item, is_update=is_update, is_test=is_test)

    # 1. Prefer Webhook if provided (supports comma-separated list for multi-server broadcasting)
    if webhook_url:
        urls = [u.strip() for u in webhook_url.split(",") if u.strip()]
        all_ok = True
        msgs = []
        for u in urls:
            ok, msg = send_http_json(u, payload)
            if not ok:
                all_ok = False
            msgs.append(msg)
        return all_ok, "; ".join(msgs)

    # 2. Fall back to Bot REST API if token + channel_id configured
    if bot_token and channel_id:
        endpoint = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {"Authorization": f"Bot {bot_token}"}
        return send_http_json(endpoint, payload, headers=headers)

    return False, "Neither DISCORD_WEBHOOK_URL nor (DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID) configured."


def broadcast_to_telegram(
    item: dict[str, Any],
    is_update: bool = False,
    is_test: bool = False,
) -> tuple[bool, str]:
    """Send alert to Telegram via Bot API (supports comma-separated multiple chats)."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not bot_token or not chat_id:
        return False, "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured."

    chats = [c.strip() for c in chat_id.split(",") if c.strip()]
    all_ok = True
    msgs = []
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for cid in chats:
        payload = format_telegram_payload(cid, item, is_update=is_update, is_test=is_test)
        ok, msg = send_http_json(endpoint, payload)
        if not ok:
            all_ok = False
        msgs.append(msg)
    return all_ok, "; ".join(msgs)


# ==============================================================================
# Pipeline Execution
# ==============================================================================

def run_alerts(
    dry_run: bool = False,
    ignore_timing: bool = False,
    min_edge_pp: float = 5.0,
    confidence_bands: tuple[str, ...] = ("high", "very_high"),
) -> int:
    """Execute one scan and broadcast cycle. Returns number of alerts sent."""
    data = load_predictions()
    if not data:
        print("[alerts] No prediction data available to process.")
        return 0

    qualifying = filter_qualifying_edges(
        data,
        min_edge_pp=min_edge_pp,
        confidence_filter=confidence_bands,
        ignore_timing=ignore_timing,
    )

    if not qualifying:
        print(f"[alerts] No matching edges (min_edge={min_edge_pp}pp, conf={confidence_bands}, ignore_timing={ignore_timing}).")
        return 0

    state = load_alert_state()
    now_ts = time.time()
    alerts_sent = 0

    for item in qualifying:
        key = make_alert_key(item)
        current_edge = float(item.get("edge_pp") or 0.0)
        current_price = float(item.get("market_price") or 0.0)

        is_update = False
        if key in state:
            prev = state[key]
            prev_ts = prev.get("timestamp", 0)
            prev_edge = prev.get("edge_pp", 0.0)

            # Suppress if already sent within 24h unless edge shifted significantly (>= 5.0 pp)
            if (now_ts - prev_ts) < 86400:
                if abs(current_edge - prev_edge) < 5.0:
                    continue
                is_update = True

        action_label = "UPDATE" if is_update else "NEW"
        match_title = item.get("match") or (f"{item.get('pick')} Match" if item.get("pick") else "Tennis Match")
        print(
            f"[alerts] [{action_label}] {match_title} -> {item.get('pick')} "
            f"(Edge: +{current_edge:.1f}pp | Kelly: {float(item.get('kelly_quarter') or 0)*100:.1f}% | "
            f"Conf: {item.get('confidence_band')})"
        )

        if dry_run:
            print("         [DRY-RUN] Alert suppressed (dry-run mode).")
            continue

        # Broadcast to Discord
        d_ok, d_msg = broadcast_to_discord(item, is_update=is_update)
        print(f"         Discord broadcast: {'SUCCESS' if d_ok else 'FAILED'} ({d_msg})")

        # Broadcast to Telegram
        t_ok, t_msg = broadcast_to_telegram(item, is_update=is_update)
        print(f"         Telegram broadcast: {'SUCCESS' if t_ok else 'FAILED'} ({t_msg})")

        if d_ok or t_ok:
            state[key] = {
                "timestamp": now_ts,
                "edge_pp": current_edge,
                "market_price": current_price,
                "sent_iso": datetime.now(timezone.utc).isoformat(),
            }
            alerts_sent += 1

    if not dry_run and alerts_sent > 0:
        save_alert_state(state)

    return alerts_sent


def send_test_alert() -> None:
    """Send a simulated test alert to verify Discord and Telegram credentials."""
    sample_match = {
        "match": "Ben Shelton vs Frances Tiafoe",
        "match_start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tourney": "US Open",
        "surface": "hard",
        "round": "Semifinal",
        "our_p1": 0.622,
        "kalshi_p1": 0.480,
        "pick": "Ben Shelton",
        "pick_side": "p1",
        "pick_win_prob": 0.622,
        "market_price": 0.48,
        "market_bid": 0.46,
        "edge_pp": 14.2,
        "confidence_band": "high",
        "kelly_quarter": 0.018,
        "board_decision": "BUY",
        "trade_action": {
            "platform": "Kalshi",
            "ticker": "KXATPUSOPEN-26SEP11SHELTI",
            "direct_trade_url": f"https://kalshi.com/markets/kxatpusopen?referral={KALSHI_REFERRAL_URL.split('/r/')[-1]}",
            "referral_url": KALSHI_REFERRAL_URL,
            "cta": "Trade on Kalshi ($25 Welcome Bonus)",
        },
    }

    print("==================================================================")
    print("Testing Community Alert Integration (Discord & Telegram)")
    print("==================================================================")

    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    print(f"Discord Webhook: {'CONFIGURED' if webhook else 'MISSING'}")
    print(f"Discord Bot Token: {'CONFIGURED' if bot_token else 'MISSING'}")
    print(f"Telegram Bot Token: {'CONFIGURED' if tg_token else 'MISSING'}")
    print(f"Telegram Chat ID: {'CONFIGURED' if chat_id else 'MISSING'}")
    print("------------------------------------------------------------------")

    d_ok, d_msg = broadcast_to_discord(sample_match, is_test=True)
    print(f"Discord Dispatch: {'SUCCESS' if d_ok else 'FAILED'} -> {d_msg}")

    t_ok, t_msg = broadcast_to_telegram(sample_match, is_test=True)
    print(f"Telegram Dispatch: {'SUCCESS' if t_ok else 'FAILED'} -> {t_msg}")
    print("==================================================================")


# ==============================================================================
# CLI Entrypoint
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="iPredictSport Community Alert Bot (Discord & Telegram)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print qualifying edge alerts without sending to channels",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a mock test alert to verify Discord and Telegram credentials",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute single scan and broadcast immediately (default)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously on an interval timer",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Daemon loop sleep interval in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--min-edge",
        type=float,
        default=float(os.getenv("ALERT_MIN_EDGE_PP", "5.0")),
        help="Minimum edge in percentage points to qualify for an alert (default: 5.0)",
    )
    parser.add_argument(
        "--confidence",
        type=str,
        default=os.getenv("ALERT_CONFIDENCE", "high,very_high"),
        help="Comma-separated confidence tiers to alert on (default: 'high,very_high' or 'all')",
    )
    parser.add_argument(
        "--ignore-timing",
        action="store_true",
        help="Ignore T-6h window filter and evaluate all upcoming active rows",
    )

    args = parser.parse_args()

    if args.test:
        send_test_alert()
        return

    conf_bands = tuple(x.strip().lower() for x in args.confidence.split(",") if x.strip())

    if args.daemon:
        print(f"[alerts] Starting community alert daemon (interval: {args.interval}s, min_edge: {args.min_edge}pp)...")
        while True:
            try:
                sent = run_alerts(
                    dry_run=args.dry_run,
                    ignore_timing=args.ignore_timing,
                    min_edge_pp=args.min_edge,
                    confidence_bands=conf_bands,
                )
                print(f"[alerts] Cycle complete: {sent} alert(s) dispatched. Sleeping {args.interval}s.")
            except KeyboardInterrupt:
                print("\n[alerts] Daemon stopped by user.")
                break
            except Exception as err:
                print(f"[alerts] Unexpected error during cycle: {err}")
            time.sleep(args.interval)
        return

    # Default: single run
    run_alerts(
        dry_run=args.dry_run,
        ignore_timing=args.ignore_timing,
        min_edge_pp=args.min_edge,
        confidence_bands=conf_bands,
    )


if __name__ == "__main__":
    main()

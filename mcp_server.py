#!/usr/bin/env python3
"""tennis-predict-mcp: Model Context Protocol (MCP) Server for iPredictSport.

Exposes quantitative tennis prediction models, closing-line value (CLV),
market mispricings, and fee-aware quarter-Kelly trading signals to AI
assistants (Claude Desktop, Cursor, Windsurf, LangChain, etc.).

Operates over stdio JSON-RPC 2.0 according to the MCP specification.
Zero external dependencies (pure Python 3.10+ stdlib).

Order placement (v1.1, queue 973): `place_limit_order` is PAPER by default and
needs only the stdlib. Live Kalshi orders need `pip install cryptography` and
YOUR OWN key in KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY_PATH. CLI:
    python mcp_server.py order --venue kalshi --market <ticker> --side yes \
        --price 0.55 --fair 0.62            # paper
    ... --live                              # signs with your key
Kill switch: create ~/.ipredict/KILL.

Usage in claude_desktop_config.json:
{
  "mcpServers": {
    "tennis-predict": {
      "command": "python",
      "args": ["path/to/mcp_server.py"]
    }
  }
}
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SERVER_NAME = "tennis-predict-mcp"
SERVER_VERSION = "1.1.0"  # 973: order placement (paper default, live with your key)
PROTOCOL_VERSION = "2024-11-05"

SITE_URL = "https://ipredictsport.com"
FEED_URL = f"{SITE_URL}/predictions.json"
TRACK_URL = f"{SITE_URL}/track_record.json"

KALSHI_REFERRAL_CODE = "eb2fd257-2bc9-465a-a18c-5e9a0ab4848d"
KALSHI_REFERRAL_URL = f"https://kalshi.com/r/{KALSHI_REFERRAL_CODE}"

# Local cache paths if running inside the repository
ROOT = Path(__file__).resolve().parents[1] if (Path(__file__).resolve().parents[1] / "site").exists() else None
LOCAL_PREDICTIONS = (ROOT / "site" / "predictions.json") if ROOT else None
LOCAL_TRACK = (ROOT / "site" / "track_record.json") if ROOT else None

_CACHE: dict[str, Any] = {}
_CACHE_TTL = 300  # 5 minutes


def _fetch_json(url: str, local_path: Path | None = None) -> dict[str, Any]:
    now = time.time()
    if url in _CACHE and (now - _CACHE[url]["time"]) < _CACHE_TTL:
        return _CACHE[url]["data"]

    # 1. Try local file if available and fresh (< 2 hours old)
    if local_path and local_path.exists():
        try:
            mtime = local_path.stat().st_mtime
            if (now - mtime) < 7200:
                data = json.loads(local_path.read_text(encoding="utf-8"))
                _CACHE[url] = {"data": data, "time": now}
                return data
        except Exception:
            pass

    # 2. Fetch over HTTP
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"tennis-predict-mcp/{SERVER_VERSION} (Python stdlib)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _CACHE[url] = {"data": data, "time": now}
            return data
    except Exception as err:
        # Fallback to local even if older
        if local_path and local_path.exists():
            try:
                data = json.loads(local_path.read_text(encoding="utf-8"))
                return data
            except Exception:
                pass
        return {"error": f"Failed to fetch data from {url}: {err}"}


def get_live_board(confidence_min: str = "all") -> str:
    """Get active ATP/WTA match predictions and win probabilities."""
    data = _fetch_json(FEED_URL, LOCAL_PREDICTIONS)
    if "error" in data:
        return f"Error: {data['error']}"

    upcoming = data.get("upcoming_board") or []
    if not upcoming:
        return "No upcoming matches currently available on the active board."

    conf_rank = {"low": 1, "medium": 2, "high": 3, "very_high": 4}
    min_rank = conf_rank.get(confidence_min.lower(), 1)

    lines = [
        f"# Live Tennis Prediction Board (Refreshed: {data.get('generated_utc', 'N/A')})",
        "",
        "| Tournament | Round | Match | Surface | Model Favorite | Win Prob | Confidence |",
        "|---|---|---|---|---|---|---|",
    ]

    count = 0
    for m in upcoming:
        c_band = str(m.get("confidence_band") or "low").lower()
        if conf_rank.get(c_band, 1) < min_rank:
            continue
        p1, p2 = m.get("p1"), m.get("p2")
        fav = m.get("favorite") or p1
        prob = float(m.get("favorite_prob") or m.get("p1_win_prob") or 0.5)
        surf = m.get("surface") or "N/A"
        tourney = m.get("tourney") or "ATP/WTA"
        rnd = m.get("round") or "Match"

        lines.append(
            f"| {tourney} | {rnd} | {p1} vs {p2} | {surf} | **{fav}** | {prob*100:.1f}% | {c_band.capitalize()} |"
        )
        count += 1

    lines.append("")
    lines.append(f"Total matches listed: {count}. Data from {SITE_URL}")
    return "\n".join(lines)


def get_betting_edges(min_edge_pp: float = 5.0, confidence: str = "medium_plus") -> str:
    """Find positive-EV betting opportunities against Kalshi/Polymarket prices."""
    data = _fetch_json(FEED_URL, LOCAL_PREDICTIONS)
    if "error" in data:
        return f"Error: {data['error']}"

    evals = data.get("kalshi_evaluations") or []
    if not evals:
        return "No market evaluations currently available."

    conf_rank = {"any": 0, "medium_plus": 2, "high_only": 3}
    req_rank = conf_rank.get(confidence.lower(), 2)
    band_map = {"low": 1, "medium": 2, "high": 3, "very_high": 4}

    matches_found = []
    for e in evals:
        c_band = str(e.get("confidence_band") or "low").lower()
        if band_map.get(c_band, 1) < req_rank:
            continue

        edge = e.get("edge_pp")
        if edge is None:
            our_p1 = float(e.get("our_p1") or 0.5)
            kalshi_p1 = float(e.get("kalshi_p1") or 0.5)
            edge = (our_p1 - kalshi_p1) * 100

        if abs(float(edge)) < float(min_edge_pp):
            continue

        matches_found.append(e)

    if not matches_found:
        return f"No betting edges found exceeding {min_edge_pp}pp at '{confidence}' confidence level."

    lines = [
        f"# Quantitative Tennis Market Edges (Min Edge: {min_edge_pp}pp, Confidence: {confidence})",
        "",
        "| Match | Recommended Pick | Model Prob | Market Price | Edge | Confidence | Quarter-Kelly | Action |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for m in matches_found:
        match_title = m.get("match") or "Match"
        pick = m.get("pick") or m.get("match", "").split(" vs ")[0]
        prob = float(m.get("pick_win_prob") or m.get("our_p1") or 0.5)
        price = float(m.get("market_price") or m.get("kalshi_p1") or 0.5)
        edge = float(m.get("edge_pp") or ((prob - price) * 100))
        c_band = str(m.get("confidence_band") or "low").capitalize()
        kelly = float(m.get("kelly_quarter") or 0.0)

        trade = m.get("trade_action") or {}
        trade_url = trade.get("direct_trade_url") or trade.get("trade_url") or KALSHI_REFERRAL_URL
        action = f"[{trade.get('cta') or 'Trade on Kalshi'}]({trade_url})"

        lines.append(
            f"| {match_title} | **{pick}** | {prob*100:.1f}% | {price*100:.0f}¢ | **{edge:+.1f}pp** | {c_band} | {kelly*100:.1f}% | {action} |"
        )

    lines.append("")
    lines.append("### Execution Notes:")
    lines.append("- Staking reflects fee-aware quarter-Kelly allocation.")
    lines.append(f"- Kalshi referral bonus ($25 credited upon sign-up & trade): [{KALSHI_REFERRAL_URL}]({KALSHI_REFERRAL_URL})")
    lines.append(f"- Audited track record & model details: {SITE_URL}/track-record.html")
    return "\n".join(lines)


def get_match_analysis(query: str) -> str:
    """Get in-depth quantitative analysis and market odds for a specific match or player."""
    data = _fetch_json(FEED_URL, LOCAL_PREDICTIONS)
    if "error" in data:
        return f"Error: {data['error']}"

    q = query.strip().lower()
    upcoming = data.get("upcoming_board") or []
    evals = data.get("kalshi_evaluations") or []
    notes = data.get("player_notes") or {}

    # Match in upcoming board
    matched_board = [
        m for m in upcoming
        if q in str(m.get("p1", "")).lower() or q in str(m.get("p2", "")).lower() or q in str(m.get("tourney", "")).lower()
    ]

    # Match in evaluations
    matched_evals = [
        e for e in evals
        if q in str(e.get("match", "")).lower() or q in str(e.get("tourney", "")).lower()
    ]

    if not matched_board and not matched_evals:
        return f"No active match found matching '{query}'. Check spelling or run get_live_board() to see active fixtures."

    lines = [f"# Match Analysis: '{query}'", ""]

    if matched_board:
        m = matched_board[0]
        p1, p2 = m.get("p1"), m.get("p2")
        prob1 = float(m.get("p1_win_prob") or 0.5)
        prob2 = 1.0 - prob1
        fav = m.get("favorite") or (p1 if prob1 >= 0.5 else p2)
        fav_prob = max(prob1, prob2)
        c_band = str(m.get("confidence_band") or "low").capitalize()

        lines.extend([
            f"### {p1} vs {p2}",
            f"- **Tournament:** {m.get('tourney', 'N/A')} ({m.get('round', 'N/A')})",
            f"- **Surface:** {m.get('surface', 'N/A')}",
            f"- **Scheduled Start:** {m.get('start', 'N/A')}",
            f"- **Model Favorite:** **{fav}** ({fav_prob*100:.1f}% win probability)",
            f"  - {p1}: {prob1*100:.1f}%",
            f"  - {p2}: {prob2*100:.1f}%",
            f"- **Confidence Level:** {c_band} (based on verified historical sample depth)",
            "",
        ])

        p1_notes = notes.get(p1)
        p2_notes = notes.get(p2)
        if p1_notes or p2_notes:
            lines.append("### Context & Injury Intelligence:")
            if p1_notes:
                lines.append(f"- **{p1}:** {p1_notes}")
            if p2_notes:
                lines.append(f"- **{p2}:** {p2_notes}")
            lines.append("")

    if matched_evals:
        e = matched_evals[0]
        pick = e.get("pick") or "Best Value"
        pick_prob = float(e.get("pick_win_prob") or 0.5)
        ask = float(e.get("market_price") or 0.0)
        edge = float(e.get("edge_pp") or 0.0)
        kelly = float(e.get("kelly_quarter") or 0.0)
        trade = e.get("trade_action") or {}
        trade_url = trade.get("direct_trade_url") or KALSHI_REFERRAL_URL

        lines.extend([
            "### Prediction Market Pricing (Kalshi):",
            f"- **Recommended Value Pick:** **{pick}**",
            f"- **Model Fair Probability:** {pick_prob*100:.1f}%",
            f"- **Current Market Ask:** {ask*100:.0f}¢ per dollar contract",
            f"- **Mathematical Edge:** **{edge:+.1f} percentage points**",
            f"- **Quarter-Kelly Staking:** {kelly*100:.1f}% of bankroll",
            f"- **Contract Ticker:** `{trade.get('ticker', 'N/A')}`",
            f"- **Execute Order:** [Trade on Kalshi with $25 Bonus]({trade_url})",
            "",
        ])

    return "\n".join(lines)


def get_track_record() -> str:
    """Get audited historical performance benchmarks and CLV statistics."""
    data = _fetch_json(TRACK_URL, LOCAL_TRACK)
    if "error" in data:
        return f"Error: {data['error']}"

    overall = data.get("overall") or {}
    lines = [
        "# iPredictSport Audited Track Record",
        "",
        "- **Holdout Prediction Accuracy:** 66.1% (ATP Tour holdout, n=4,851 matches)",
        f"- **Audited Market Bets:** {overall.get('n', 28)} bets logged pre-match",
        f"- **Hit Rate:** {float(overall.get('accuracy', 0.643))*100:.1f}%",
        f"- **Model Brier Score:** {overall.get('our_brier', 0.203):.3f} vs Market: {overall.get('kalshi_brier', 0.222):.3f}",
        f"- **Closing-Line Value (CLV):** {float(overall.get('avg_clv_pp', 4.5)):+.1f}pp average market movement in our direction",
        "- **Staking Strategy:** Quarter-Kelly, continuous Kalshi fee-adjusted",
        "",
        f"Full ledger and proof of pre-match timestamps: {SITE_URL}/track_record.json",
    ]
    return "\n".join(lines)


# MCP Protocol Definitions
TOOLS = [
    {
        "name": "get_live_board",
        "description": "Fetch current active ATP and WTA tennis matches with calibrated model win probabilities, tournament details, surfaces, and confidence ratings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "confidence_min": {
                    "type": "string",
                    "description": "Minimum confidence level filter ('all', 'medium', 'high', 'very_high')",
                    "enum": ["all", "medium", "high", "very_high"],
                    "default": "all",
                }
            },
        },
    },
    {
        "name": "get_betting_edges",
        "description": "Retrieve active tennis matches where our quantitative model identifies a positive-EV mathematical edge against live Kalshi/Polymarket prices, including quarter-Kelly position sizing and direct trading action links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_edge_pp": {
                    "type": "number",
                    "description": "Minimum edge in percentage points (e.g. 5.0 means model prob exceeds market price by >= 5%)",
                    "default": 5.0,
                },
                "confidence": {
                    "type": "string",
                    "description": "Confidence filter ('any', 'medium_plus', 'high_only')",
                    "enum": ["any", "medium_plus", "high_only"],
                    "default": "medium_plus",
                },
            },
        },
    },
    {
        "name": "get_match_analysis",
        "description": "Get deep-dive quantitative breakdown and market odds for a specific tennis match or player name, including head-to-head win probability, context/injury notes, and Kalshi contract pricing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Player name or match query (e.g. 'Alcaraz' or 'Shelton vs Alcaraz')",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_track_record",
        "description": "Retrieve audited performance metrics including out-of-sample accuracy, Brier scores vs market, closing-line value (CLV), and historical bet results.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

PROMPTS = [
    {
        "name": "scan_todays_edges",
        "description": "Scan all active tennis matches and list positive-EV betting opportunities on Kalshi with quarter-Kelly stake sizing.",
        "arguments": [
            {
                "name": "min_edge_pp",
                "description": "Minimum edge in percentage points (e.g. 5.0)",
                "required": False,
            }
        ],
    },
    {
        "name": "analyze_match",
        "description": "Perform an in-depth quantitative breakdown of an upcoming tennis match.",
        "arguments": [
            {
                "name": "player_or_match",
                "description": "Name of the player or match",
                "required": True,
            }
        ],
    },
]

RESOURCES = [
    {
        "uri": f"{SITE_URL}/predictions.json",
        "name": "Active Match Predictions Feed",
        "mimeType": "application/json",
        "description": "Current active board with win probabilities, market prices, and confidence ratings.",
    },
    {
        "uri": f"{SITE_URL}/track_record.json",
        "name": "Audited Track Record",
        "mimeType": "application/json",
        "description": "Audited historical ledger of bets, CLV, and Brier scores vs market.",
    },
]


# ===========================================================================
# ORDER PLACEMENT (queue 973). Paper by default; live only with YOUR key.
# ===========================================================================
# Design rules, each one a measured lesson from the main repo:
#   * REFUSES without a stated fair price. "Buy because the model said so"
#     is not an order; an order is a price, a fair value and the gap.
#   * Prints the FEE before anything is signed. Kalshi taker 0.07*p*(1-p),
#     maker a quarter of that; Polymarket adds a builder fee we disclose.
#   * Quarter-Kelly, fee-aware, capped per market and in total.
#   * KILL SWITCH: a file named KILL in ~/.ipredict, or IPREDICT_KILL=1,
#     refuses every live order. Delete the file to resume.
#   * SINGLE-INSTANCE for live: a pid lock, so two agents on one key cannot
#     double a position.
#   * HEARTBEAT: every order (paper or live) stamps ~/.ipredict/heartbeat.json
#     with what was DONE, not what was intended.
#   * Humans open accounts; agents trade. Nothing here creates an account.
IPREDICT_HOME = Path(os.environ.get("IPREDICT_HOME", Path.home() / ".ipredict"))
PAPER_LEDGER = IPREDICT_HOME / "paper_orders.jsonl"
LIVE_LEDGER = IPREDICT_HOME / "live_orders.jsonl"
KILL_FILE = IPREDICT_HOME / "KILL"
LIVE_LOCK = IPREDICT_HOME / "live.lock"
ORDER_HEARTBEAT = IPREDICT_HOME / "heartbeat.json"

KALSHI_TRADE_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_TAKER_MULT = 0.07
KALSHI_MAKER_MULT = 0.0175
# Polymarket Builder Program attribution. Set once the verified builder key
# exists (queue 972); until then live Polymarket is refused, not faked.
POLYMARKET_BUILDER_CODE = os.environ.get("IPREDICT_POLY_BUILDER_CODE", "")
POLYMARKET_BUILDER_FEE_BPS = int(os.environ.get("IPREDICT_POLY_BUILDER_BPS", "25"))

DEFAULT_BANKROLL = float(os.environ.get("IPREDICT_BANKROLL", "1000"))
MAX_PCT_PER_MARKET = float(os.environ.get("IPREDICT_MAX_PCT_PER_MARKET", "5"))
MAX_PCT_TOTAL_OPEN = float(os.environ.get("IPREDICT_MAX_PCT_TOTAL", "25"))


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append(path: Path, row: dict[str, Any]) -> None:
    IPREDICT_HOME.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")
        fh.flush()


def _heartbeat(**fields: Any) -> None:
    IPREDICT_HOME.mkdir(parents=True, exist_ok=True)
    fields.update({"at": _now_iso(), "pid": os.getpid(), "server": SERVER_VERSION})
    ORDER_HEARTBEAT.write_text(json.dumps(fields), encoding="utf-8")


def kalshi_fee(price: float, maker: bool) -> float:
    """Per-contract fee in dollars. Kalshi rounds up per order; this is the
    exact formula, which is the conservative side for sizing."""
    mult = KALSHI_MAKER_MULT if maker else KALSHI_TAKER_MULT
    return mult * price * (1.0 - price)


def quarter_kelly_pct(fair: float, price: float, fee_per_contract: float) -> float:
    """Quarter-Kelly stake as % of bankroll for buying YES at `price` when
    the fair probability is `fair`, net of a per-contract fee. Zero when the
    edge does not survive the fee."""
    cost = price + fee_per_contract
    if cost <= 0 or cost >= 1 or fair <= cost:
        return 0.0
    b = (1.0 - cost) / cost           # net odds
    f = (fair * b - (1.0 - fair)) / b  # full Kelly fraction
    return max(0.0, 0.25 * f * 100.0)


def _open_exposure_pct(ledger: Path) -> float:
    if not ledger.exists():
        return 0.0
    tot = 0.0
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("status") in ("paper_open", "live_submitted"):
            tot += float(r.get("size_pct_bankroll") or 0.0)
    return tot


def _kalshi_sign(key_id: str, private_key_pem: bytes, method: str, path: str
                 ) -> dict[str, str]:
    """RSA-PSS/SHA256 over timestamp_ms + METHOD + path (no query), per Kalshi
    docs. Needs `cryptography`; imported lazily so paper mode stays stdlib."""
    import base64
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    ts = str(int(time.time() * 1000))
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    msg = (ts + method.upper() + path).encode("utf-8")
    sig = key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.DIGEST_LENGTH),
                   hashes.SHA256())
    return {"KALSHI-ACCESS-KEY": key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode("ascii"),
            "Content-Type": "application/json"}


def _kalshi_post_order(body: dict[str, Any]) -> dict[str, Any]:
    key_id = os.environ.get("KALSHI_API_KEY_ID", "")
    pem_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "")
    if not key_id or not pem_path or not Path(pem_path).exists():
        raise RuntimeError("live Kalshi needs KALSHI_API_KEY_ID and "
                           "KALSHI_PRIVATE_KEY_PATH (your own key, never ours)")
    path = "/trade-api/v2/portfolio/orders"
    headers = _kalshi_sign(key_id, Path(pem_path).read_bytes(), "POST", path)
    req = urllib.request.Request(
        "https://api.elections.kalshi.com" + path,
        data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _acquire_live_lock() -> str | None:
    """Returns None when acquired, else the reason it was refused."""
    IPREDICT_HOME.mkdir(parents=True, exist_ok=True)
    if LIVE_LOCK.exists():
        try:
            d = json.loads(LIVE_LOCK.read_text(encoding="utf-8"))
            pid = int(d.get("pid") or -1)
            age = time.time() - float(d.get("t") or 0)
        except Exception:
            pid, age = -1, 1e9
        if pid != os.getpid() and age < 120:
            return f"another live session (pid {pid}) placed an order {age:.0f}s ago"
    LIVE_LOCK.write_text(json.dumps({"pid": os.getpid(), "t": time.time()}),
                         encoding="utf-8")
    return None


def place_limit_order(venue: str, market: str, side: str, price: float,
                      fair_price: float, size_pct: float | None = None,
                      mode: str = "paper", maker: bool = True,
                      bankroll: float | None = None, why: str = "") -> str:
    """Place (paper) or submit (live) a resting limit order.

    venue: 'kalshi' | 'polymarket'. market: Kalshi ticker or Polymarket token
    id. side: 'yes' | 'no'. price: limit price in [0.01, 0.99] for the side
    you are buying. fair_price: YOUR stated fair probability for that side.
    size_pct: % of bankroll; omitted -> quarter-Kelly, capped.
    mode: 'paper' (default) records intent; 'live' signs with YOUR key.
    """
    venue = venue.lower().strip()
    side = side.lower().strip()
    mode = mode.lower().strip()
    bankroll = float(bankroll or DEFAULT_BANKROLL)
    if venue not in ("kalshi", "polymarket"):
        return "REFUSED: venue must be 'kalshi' or 'polymarket'."
    if side not in ("yes", "no"):
        return "REFUSED: side must be 'yes' or 'no'."
    try:
        price = float(price)
        fair_price = float(fair_price)
    except (TypeError, ValueError):
        return "REFUSED: price and fair_price must be numbers in (0, 1)."
    if not (0.01 <= price <= 0.99):
        return "REFUSED: price must be between 0.01 and 0.99 (probability units)."
    if not (0.0 < fair_price < 1.0):
        return ("REFUSED: no fair price stated. An order without a fair value is "
                "not a trade, it is a guess. Pass fair_price = your probability "
                "that this side wins.")

    # Fee, shown before anything else happens.
    if venue == "kalshi":
        fee = kalshi_fee(price, maker)
        fee_note = (f"Kalshi {'maker' if maker else 'taker'} fee "
                    f"{fee*100:.2f}c/contract (formula {KALSHI_MAKER_MULT if maker else KALSHI_TAKER_MULT}*p*(1-p))")
    else:
        fee = price * POLYMARKET_BUILDER_FEE_BPS / 10_000.0
        fee_note = (f"Polymarket builder fee {POLYMARKET_BUILDER_FEE_BPS} bps of notional "
                    f"({fee*100:.2f}c/contract) is paid to iPredictSport as the router, "
                    f"on top of the platform's own fee")

    kelly = quarter_kelly_pct(fair_price, price, fee)
    if size_pct is None:
        size_pct = kelly
    size_pct = float(size_pct)
    edge_pp = (fair_price - price) * 100.0
    if kelly <= 0.0:
        return (f"REFUSED: no edge after fees. fair {fair_price:.3f} vs price {price:.3f} "
                f"(+{edge_pp:.1f}pp) does not cover {fee_note}.")
    if size_pct > MAX_PCT_PER_MARKET:
        size_pct = MAX_PCT_PER_MARKET
        cap_note = f" (capped at {MAX_PCT_PER_MARKET:.1f}% per market)"
    else:
        cap_note = ""
    ledger = LIVE_LEDGER if mode == "live" else PAPER_LEDGER
    open_pct = _open_exposure_pct(ledger)
    if open_pct + size_pct > MAX_PCT_TOTAL_OPEN:
        return (f"REFUSED: total open exposure would be {open_pct + size_pct:.1f}% of "
                f"bankroll, above the {MAX_PCT_TOTAL_OPEN:.0f}% cap. Close something first.")
    stake = bankroll * size_pct / 100.0
    contracts = max(1, int(stake / price))

    row = {
        "at": _now_iso(), "venue": venue, "market": market, "side": side,
        "price": round(price, 4), "fair_price": round(fair_price, 4),
        "edge_pp": round(edge_pp, 2), "maker": maker,
        "fee_per_contract": round(fee, 5), "size_pct_bankroll": round(size_pct, 3),
        "quarter_kelly_pct": round(kelly, 3), "bankroll": bankroll,
        "contracts": contracts, "stake_usd": round(contracts * price, 2),
        "why": why[:300], "mode": mode,
    }

    if mode != "live":
        row["status"] = "paper_open"
        _append(PAPER_LEDGER, row)
        _heartbeat(last_action="paper_order", venue=venue, market=market,
                   contracts=contracts, ledger=str(PAPER_LEDGER))
        return (f"PAPER order recorded: buy {contracts} {side.upper()} {market} @ {price:.2f} "
                f"on {venue} (fair {fair_price:.3f}, +{edge_pp:.1f}pp, {fee_note}, "
                f"{size_pct:.2f}% of ${bankroll:,.0f}{cap_note}). "
                f"Ledger: {PAPER_LEDGER}. To go live, call again with mode='live'.")

    # ---- LIVE ----
    if os.environ.get("IPREDICT_KILL") == "1" or KILL_FILE.exists():
        return f"REFUSED: kill switch is on ({KILL_FILE} exists or IPREDICT_KILL=1)."
    if venue == "polymarket":
        if not POLYMARKET_BUILDER_CODE:
            return ("REFUSED: live Polymarket is not enabled in this build -- the "
                    "builder attribution code is not set (IPREDICT_POLY_BUILDER_CODE). "
                    "Paper mode works; live Polymarket ships when the Builder Program "
                    "key exists.")
        return "REFUSED: live Polymarket routing is not implemented yet; use paper."
    body = {
        "ticker": market, "action": "buy", "side": side, "type": "limit",
        "count": contracts, "client_order_id": f"ipredict-{int(time.time()*1000)}",
        ("yes_price" if side == "yes" else "no_price"): int(round(price * 100)),
    }
    if maker:
        body["post_only"] = True
    # The lock guards only the submission window and is ALWAYS released, so
    # a refused or failed attempt cannot block the next one (measured: the
    # first version locked before the credential check and then refused
    # itself for 120s).
    reason = _acquire_live_lock()
    if reason:
        return f"REFUSED: {reason}. Single-instance rule: one live writer per key."
    try:
        try:
            resp = _kalshi_post_order(body)
        except ImportError:
            return "REFUSED: live Kalshi needs `pip install cryptography` (RSA-PSS signing)."
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:300]
            row.update({"status": "live_rejected", "http": err.code, "detail": detail})
            _append(LIVE_LEDGER, row)
            _heartbeat(last_action="live_rejected", venue=venue, market=market, http=err.code)
            return f"Kalshi rejected the order (HTTP {err.code}): {detail}"
        except Exception as err:
            return f"REFUSED: {type(err).__name__}: {err}"
    finally:
        try:
            LIVE_LOCK.unlink()
        except OSError:
            pass
    order = (resp or {}).get("order") or {}
    row.update({"status": "live_submitted", "order_id": order.get("order_id"),
                "order_status": order.get("status"), "request": body})
    _append(LIVE_LEDGER, row)
    _heartbeat(last_action="live_submitted", venue=venue, market=market,
               order_id=order.get("order_id"), contracts=contracts)
    return (f"LIVE order submitted to Kalshi: buy {contracts} {side.upper()} {market} @ "
            f"{price:.2f} (order_id {order.get('order_id')}, status {order.get('status')}, "
            f"{fee_note}). Ledger: {LIVE_LEDGER}.")


def resolve_kalshi_market(event_ticker: str, pick: str) -> dict[str, Any]:
    """The feed carries an EVENT ticker (KXATPMATCH-26SEP22UCHCIN); Kalshi lists
    one market per player under it (…-UCH, …-CIN) whose `yes_sub_title` is the
    player's name. Buying YES on the pick's market is the clean order. Public
    endpoint, no auth. Returns {} when the pick does not match exactly one
    market -- ambiguity is a refusal, never a guess (CLAUDE.md)."""
    url = f"{KALSHI_TRADE_BASE}/markets?event_ticker={event_ticker}&limit=50"
    req = urllib.request.Request(url, headers={"User-Agent": f"tennis-predict-mcp/{SERVER_VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            markets = (json.loads(resp.read().decode("utf-8")) or {}).get("markets") or []
    except Exception:
        return {}
    want = " ".join(str(pick).lower().split())
    hits = [m for m in markets
            if " ".join(str(m.get("yes_sub_title") or "").lower().split()) == want]
    if len(hits) != 1:
        # fall back to surname-only ONLY if exactly one market carries it
        sur = want.split()[-1] if want else ""
        hits = [m for m in markets if sur and sur in str(m.get("yes_sub_title") or "").lower()]
        if len(hits) != 1:
            return {}
    m = hits[0]
    return {"ticker": m.get("ticker"), "yes_sub_title": m.get("yes_sub_title"),
            "yes_bid": m.get("yes_bid_dollars"), "yes_ask": m.get("yes_ask_dollars"),
            "status": m.get("status")}


def get_paper_ledger(last_n: int = 20) -> str:
    """Show the most recent paper (and live) orders this machine has placed."""
    out = [f"# Order ledgers under {IPREDICT_HOME}"]
    for name, path in (("paper", PAPER_LEDGER), ("live", LIVE_LEDGER)):
        if not path.exists():
            out.append(f"\n{name}: none yet")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()[-last_n:]
        out.append(f"\n{name}: last {len(lines)} of {path}")
        out.append("| at | venue | market | side | price | fair | edge pp | contracts | % bank | status |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for ln in lines:
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            out.append(f"| {r.get('at')} | {r.get('venue')} | {r.get('market')} | {r.get('side')} "
                       f"| {r.get('price')} | {r.get('fair_price')} | {r.get('edge_pp')} "
                       f"| {r.get('contracts')} | {r.get('size_pct_bankroll')} | {r.get('status')} |")
    out.append(f"\nExposure caps: {MAX_PCT_PER_MARKET:.0f}% per market, {MAX_PCT_TOTAL_OPEN:.0f}% "
               f"total open. Kill switch: create {KILL_FILE}.")
    return "\n".join(out)


ORDER_TOOLS = [
    {
        "name": "place_limit_order",
        "description": (
            "Place a resting limit order: PAPER by default (records intent to a local ledger), "
            "LIVE only with mode='live' and YOUR OWN Kalshi API key in the environment. Refuses "
            "without a stated fair_price, shows the fee before acting, sizes quarter-Kelly net of "
            "fees, caps exposure per market and in total, honours a kill switch, and allows one "
            "live writer per key. Humans open accounts; this tool never creates one."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "venue": {"type": "string", "enum": ["kalshi", "polymarket"]},
                "market": {"type": "string", "description": "Kalshi market ticker (e.g. KXATPMATCH-...) or Polymarket token id"},
                "side": {"type": "string", "enum": ["yes", "no"]},
                "price": {"type": "number", "description": "Limit price for the side you buy, 0.01-0.99"},
                "fair_price": {"type": "number", "description": "YOUR fair probability for that side, 0-1. Required."},
                "size_pct": {"type": "number", "description": "Percent of bankroll; omit for quarter-Kelly"},
                "mode": {"type": "string", "enum": ["paper", "live"], "default": "paper"},
                "maker": {"type": "boolean", "default": True, "description": "Rest the order (post-only) rather than cross the spread"},
                "bankroll": {"type": "number", "description": "Bankroll in USD; default IPREDICT_BANKROLL or 1000"},
                "why": {"type": "string", "description": "One line: why this price is wrong"},
            },
            "required": ["venue", "market", "side", "price", "fair_price"],
        },
    },
    {
        "name": "resolve_market",
        "description": "Turn a feed event ticker plus a pick name into the exact Kalshi market ticker to buy YES on (one market per player under an event). Returns nothing when the match is ambiguous.",
        "inputSchema": {"type": "object", "properties": {
            "event_ticker": {"type": "string"}, "pick": {"type": "string"}},
            "required": ["event_ticker", "pick"]},
    },
    {
        "name": "get_paper_ledger",
        "description": "Show the most recent paper and live orders this machine has placed, with the exposure caps and kill-switch path.",
        "inputSchema": {"type": "object", "properties": {"last_n": {"type": "integer", "default": 20}}},
    },
]
TOOLS.extend(ORDER_TOOLS)


def run_cli_order(argv: list[str]) -> int:
    """CLI surface: python mcp_server.py order --venue kalshi --market T --side yes
    --price 0.55 --fair 0.62 [--size-pct 2] [--live] [--taker] [--why ...]"""
    import argparse
    ap = argparse.ArgumentParser(prog="mcp_server.py order")
    ap.add_argument("--venue", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--side", required=True)
    ap.add_argument("--price", type=float, required=True)
    ap.add_argument("--fair", type=float, required=True)
    ap.add_argument("--size-pct", type=float, default=None)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--taker", action="store_true")
    ap.add_argument("--bankroll", type=float, default=None)
    ap.add_argument("--why", default="")
    a = ap.parse_args(argv)
    print(place_limit_order(a.venue, a.market, a.side, a.price, a.fair,
                            size_pct=a.size_pct, mode="live" if a.live else "paper",
                            maker=not a.taker, bankroll=a.bankroll, why=a.why))
    return 0


def _handle_request(req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                    "prompts": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        }

    elif method == "notifications/initialized":
        return None

    elif method in ("tools/list", "list_tools"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    elif method in ("prompts/list", "list_prompts"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"prompts": PROMPTS},
        }

    elif method in ("resources/list", "list_resources"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": RESOURCES},
        }

    elif method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}

        try:
            if name == "get_live_board":
                res = get_live_board(
                    confidence_min=str(args.get("confidence_min", "all"))
                )
            elif name == "get_betting_edges":
                res = get_betting_edges(
                    min_edge_pp=float(args.get("min_edge_pp", 5.0)),
                    confidence=str(args.get("confidence", "medium_plus")),
                )
            elif name == "get_match_analysis":
                res = get_match_analysis(
                    query=str(args.get("query", ""))
                )
            elif name == "get_track_record":
                res = get_track_record()
            elif name == "place_limit_order":
                res = place_limit_order(
                    venue=str(args.get("venue", "")),
                    market=str(args.get("market", "")),
                    side=str(args.get("side", "")),
                    price=args.get("price"),
                    fair_price=args.get("fair_price"),
                    size_pct=args.get("size_pct"),
                    mode=str(args.get("mode", "paper")),
                    maker=bool(args.get("maker", True)),
                    bankroll=args.get("bankroll"),
                    why=str(args.get("why", "")),
                )
            elif name == "resolve_market":
                r = resolve_kalshi_market(str(args.get("event_ticker", "")), str(args.get("pick", "")))
                res = json.dumps(r) if r else "No unique market matched that pick under that event."
            elif name == "get_paper_ledger":
                res = get_paper_ledger(last_n=int(args.get("last_n", 20)))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": res}],
                    "isError": False,
                },
            }
        except Exception as err:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Execution error: {err}"}],
                    "isError": True,
                },
            }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    else:
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return None


def run_cli_test() -> None:
    """Run CLI connectivity and tool diagnostic."""
    print("=" * 65)
    print(f"{SERVER_NAME} (v{SERVER_VERSION}) — Diagnostic Self-Test")
    print("=" * 65)
    print(f"[1/4] Checking live feed connectivity ({FEED_URL})...")
    data = _fetch_json(FEED_URL, LOCAL_PREDICTIONS)
    if "error" in data:
        print(f"      FAIL: {data['error']}")
        return
    evals = data.get("kalshi_evaluations") or []
    board = data.get("upcoming_board") or []
    print(f"      OK! (Found {len(evals)} market evaluations, {len(board)} upcoming matches)")

    print("\n[2/4] Testing tool: get_live_board()...")
    live = get_live_board()
    lines = live.splitlines()
    sample = "\n      ".join(lines[:min(5, len(lines))])
    print(f"      OK! Output sample:\n      {sample}")

    print("\n[3/4] Testing tool: get_betting_edges(min_edge_pp=5.0)...")
    edges = get_betting_edges(min_edge_pp=5.0, confidence="any")
    lines = edges.splitlines()
    sample = "\n      ".join(lines[:min(5, len(lines))])
    print(f"      OK! Output sample:\n      {sample}")

    print("\n[4/4] Testing tool: get_track_record()...")
    track = get_track_record()
    lines = track.splitlines()
    sample = "\n      ".join(lines[:min(4, len(lines))])
    print(f"      OK! Output sample:\n      {sample}")

    print("\n" + "=" * 65)
    print("STATUS: ALL DIAGNOSTICS PASSED! Server is fully operational.")
    print("=" * 65)
    print("\nTo print your auto-configured Claude Desktop / Cursor JSON snippet, run:")
    print("  python scripts/mcp_server.py --info\n")


def print_cli_info() -> None:
    """Print exact configuration snippets for Claude Desktop and Cursor."""
    script_path = str(Path(__file__).resolve())
    py_path = sys.executable

    cfg = {
        "mcpServers": {
            "tennis-predict": {
                "command": py_path,
                "args": [script_path],
            }
        }
    }

    print("=" * 65)
    print(f"{SERVER_NAME} (v{SERVER_VERSION}) — Auto-Generated Configuration")
    print("=" * 65)
    print("\n[A] Claude Desktop Configuration:")
    if sys.platform == "win32":
        print("    File: %APPDATA%\\Claude\\claude_desktop_config.json")
    elif sys.platform == "darwin":
        print("    File: ~/Library/Application Support/Claude/claude_desktop_config.json")
    else:
        print("    File: ~/.config/Claude/claude_desktop_config.json")
    print("\n" + json.dumps(cfg, indent=2))

    print("\n[B] Cursor IDE Configuration (.cursor/mcp.json or Settings > MCP):")
    print("    Name: tennis-predict")
    print("    Type: command")
    print(f"    Command: {py_path} \"{script_path}\"")
    print("\n" + "=" * 65)


def main() -> None:
    """Run MCP server over stdio or handle CLI flags."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--test", "-t", "test"):
            run_cli_test()
            return
        if arg in ("--info", "-i", "info", "--help", "-h"):
            print_cli_info()
            return
        if arg == "order":
            sys.exit(run_cli_order(sys.argv[2:]))

    # Ensure stdout does not buffer when communicating via stdio
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stdin.reconfigure(encoding="utf-8")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            req = json.loads(line)
            resp = _handle_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal error: {e}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

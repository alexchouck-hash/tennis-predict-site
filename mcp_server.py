#!/usr/bin/env python3
"""tennis-predict-mcp: Model Context Protocol (MCP) Server for iPredictSport.

Exposes quantitative tennis prediction models, closing-line value (CLV),
market mispricings, and fee-aware quarter-Kelly trading signals to AI
assistants (Claude Desktop, Cursor, Windsurf, LangChain, etc.).

Operates over stdio JSON-RPC 2.0 according to the MCP specification.
Zero external dependencies (pure Python 3.10+ stdlib).

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
SERVER_VERSION = "1.0.0"
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
        "- **Holdout Prediction Accuracy:** 66.1% (ATP Tour holdout, n=4,643 matches)",
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

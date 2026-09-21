#!/usr/bin/env python3
"""iPredictSport agent starter -- a paper-trading tennis agent in ~80 lines.

    curl -O https://ipredictsport.com/mcp_server.py      # order placement + feed
    curl -O https://ipredictsport.com/agent_starter.py   # this file
    python agent_starter.py                              # paper, no account needed
    python agent_starter.py --min-edge 8 --bankroll 500

What it does, every run: fetch the free feed, keep evaluations whose stated
edge beats --min-edge and whose confidence is at least --confidence, and place
a PAPER limit order for each at the current market price with the model's
probability as the stated fair price. Sizing is quarter-Kelly net of the Kalshi
maker fee, capped at 5% per market and 25% total (mcp_server enforces it).

To trade for real you need a Kalshi account with an API key (humans open
accounts; agents trade): set KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH,
`pip install cryptography`, and pass --live. Start at $1. Grade yourself on
closing-line value, not win rate: https://ipredictsport.com/track-record.html
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_server import place_limit_order, resolve_kalshi_market  # noqa: E402  (same directory)

FEED = "https://ipredictsport.com/predictions.json"
BANDS = {"low": 1, "medium": 2, "high": 3, "very_high": 4}


def fetch_feed() -> dict:
    req = urllib.request.Request(FEED, headers={"User-Agent": "ipredict-agent-starter/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def candidates(feed: dict, min_edge_pp: float, min_band: str) -> list[dict]:
    out, seen = [], set()
    for e in feed.get("kalshi_evaluations") or []:
        edge = float(e.get("edge_pp") or 0.0)
        band = str(e.get("confidence_band") or "low").lower()
        event = (e.get("trade_action") or {}).get("ticker")   # EVENT ticker
        price, fair, pick = e.get("market_price"), e.get("pick_win_prob"), e.get("pick")
        if not event or price is None or fair is None or event in seen:
            continue        # one order per event; the feed lists several products
        if edge < min_edge_pp or BANDS.get(band, 1) < BANDS[min_band]:
            continue
        seen.add(event)
        out.append({"event": event, "match": e.get("match"), "pick": pick,
                    "price": float(price), "fair": float(fair), "edge_pp": edge, "band": band})
    return sorted(out, key=lambda c: -c["edge_pp"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--min-edge", type=float, default=5.0, help="minimum stated edge, pp")
    ap.add_argument("--confidence", default="medium", choices=list(BANDS))
    ap.add_argument("--bankroll", type=float, default=1000.0)
    ap.add_argument("--max-orders", type=int, default=5)
    ap.add_argument("--live", action="store_true", help="sign with YOUR Kalshi key")
    a = ap.parse_args()

    feed = fetch_feed()
    picks = candidates(feed, a.min_edge, a.confidence)
    print(f"feed {feed.get('generated_utc')}: {len(picks)} candidates >= {a.min_edge}pp "
          f"at >= {a.confidence} confidence; placing up to {a.max_orders} "
          f"({'LIVE' if a.live else 'paper'})\n")
    for c in picks[: a.max_orders]:
        print(f"{c['match']}: {c['pick']} fair {c['fair']:.3f} vs {c['price']:.2f} "
              f"(+{c['edge_pp']:.1f}pp, {c['band']})")
        # One Kalshi market per player under the event; buy YES on the pick's.
        mk = resolve_kalshi_market(c["event"], c["pick"])
        if not mk:
            print("  -> skipped: could not resolve a unique market for the pick\n")
            continue
        print("  ->", place_limit_order(
            "kalshi", mk["ticker"], "yes", c["price"], c["fair"],
            mode="live" if a.live else "paper", maker=True, bankroll=a.bankroll,
            why=f"model {c['fair']:.3f} vs market {c['price']:.2f}"), "\n")
    print("ledger: python mcp_server.py order --help | ~/.ipredict/paper_orders.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Microsoft AutoGen tool integration for iPredictSport tennis predictions and market alpha."""

from __future__ import annotations

import json
from typing import Any

import requests

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"
IPREDICT_TRACK_RECORD_URL = "https://ipredictsport.com/track_record.json"


def get_tennis_betting_edges(min_edge_pp: float = 8.0) -> str:
    """Fetches upcoming ATP and WTA tennis matches where iPredictSport's machine learning model
    detects a positive expected value (+EV) edge against live Kalshi and Polymarket prediction prices.

    Args:
        min_edge_pp: Minimum fee-aware edge in percentage points (default: 8.0).

    Returns:
        JSON-formatted string with matching positive-EV opportunities and quarter-Kelly staking sizes.
    """
    try:
        resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        evals = data.get("kalshi_evaluations", [])

        opportunities = []
        for item in evals:
            edge = float(item.get("edge_pp") or 0.0)
            if edge >= min_edge_pp:
                opportunities.append({
                    "match": item.get("match"),
                    "market_ticker": item.get("ticker"),
                    "model_probability": round(float(item.get("our_p1", 0.0)), 3),
                    "market_price": round(float(item.get("kalshi_p1", 0.0)), 2),
                    "edge_percentage_points": round(edge, 1),
                    "quarter_kelly_stake_pct": round(float(item.get("kelly_quarter", 0.0)) * 100, 2),
                    "trade_url": item.get("trade_url") or "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                })

        if not opportunities:
            return json.dumps({
                "status": "success",
                "count": 0,
                "message": f"No tennis market edges found exceeding {min_edge_pp} percentage points."
            })

        return json.dumps({
            "status": "success",
            "count": len(opportunities),
            "opportunities": opportunities
        }, indent=2)

    except (requests.RequestException, ValueError, KeyError) as exc:
        return json.dumps({"status": "error", "message": f"Failed to fetch tennis predictions: {exc}"})


def get_match_prediction(player_name: str) -> str:
    """Finds machine learning win probability and match analysis for a specific tennis player.

    Args:
        player_name: The name or partial surname of the player (e.g. 'Alcaraz', 'Sinner', 'Swiatek').

    Returns:
        JSON-formatted prediction details including model probability, tournament, and surface.
    """
    try:
        resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        matches = data.get("matches", [])

        query = player_name.strip().lower()
        matched_records = []

        for m in matches:
            p1 = str(m.get("p1_name", "")).lower()
            p2 = str(m.get("p2_name", "")).lower()
            match_str = str(m.get("match", "")).lower()

            if query in p1 or query in p2 or query in match_str:
                matched_records.append({
                    "match": m.get("match"),
                    "tournament": m.get("tournament"),
                    "surface": m.get("surface"),
                    "p1": m.get("p1_name"),
                    "p2": m.get("p2_name"),
                    "p1_win_probability": round(float(m.get("p1_prob", 0.0)), 3),
                    "p2_win_probability": round(float(m.get("p2_prob", 1.0 - float(m.get("p1_prob", 0.0)))), 3),
                    "model_favorite": m.get("predicted_winner"),
                })

        if not matched_records:
            return json.dumps({
                "status": "not_found",
                "message": f"No scheduled match found for player '{player_name}'."
            })

        return json.dumps({
            "status": "success",
            "matches": matched_records
        }, indent=2)

    except (requests.RequestException, ValueError, KeyError) as exc:
        return json.dumps({"status": "error", "message": f"Query failed: {exc}"})


def get_track_record() -> str:
    """Retrieves the verified out-of-sample historical accuracy and Brier score benchmark
    of the iPredictSport production tennis model.

    Returns:
        JSON summary of audited test sets, calibration metrics, and edge performance.
    """
    try:
        resp = requests.get(IPREDICT_TRACK_RECORD_URL, timeout=10.0)
        resp.raise_for_status()
        return json.dumps(resp.json(), indent=2)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return json.dumps({"status": "error", "message": f"Could not retrieve track record: {exc}"})


def register_ipredict_tools(assistant: Any, user_proxy: Any) -> None:
    """Registers iPredictSport prediction functions with an AutoGen Assistant and UserProxy pair.
    Compatible with AutoGen 0.2 and 0.4.
    """
    try:
        from autogen import register_function

        register_function(
            get_tennis_betting_edges,
            caller=assistant,
            executor=user_proxy,
            name="get_tennis_betting_edges",
            description="Find ATP/WTA tennis matches with +EV edges against prediction markets (Kalshi/Polymarket)",
        )
        register_function(
            get_match_prediction,
            caller=assistant,
            executor=user_proxy,
            name="get_match_prediction",
            description="Look up machine learning win probability and match context for a specific tennis player",
        )
        register_function(
            get_track_record,
            caller=assistant,
            executor=user_proxy,
            name="get_track_record",
            description="Fetch audited out-of-sample accuracy, Brier scores, and calibration metrics",
        )
    except ImportError:
        # If autogen is not installed, register manually if caller has register_for_llm
        if hasattr(assistant, "register_for_llm") and hasattr(user_proxy, "register_for_execution"):
            assistant.register_for_llm(name="get_tennis_betting_edges", description="Get tennis +EV edges")(get_tennis_betting_edges)
            user_proxy.register_for_execution(name="get_tennis_betting_edges")(get_tennis_betting_edges)
            assistant.register_for_llm(name="get_match_prediction", description="Lookup player prediction")(get_match_prediction)
            user_proxy.register_for_execution(name="get_match_prediction")(get_match_prediction)
            assistant.register_for_llm(name="get_track_record", description="Fetch model track record")(get_track_record)
            user_proxy.register_for_execution(name="get_track_record")(get_track_record)


if __name__ == "__main__":
    print(">> Testing AutoGen iPredictSport Tools:")
    print("1. Scanning +EV edges:")
    print(get_tennis_betting_edges(min_edge_pp=5.0))

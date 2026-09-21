"""title: iPredictSport Tennis & Prediction Market Odds
author: iPredictSport
author_url: https://ipredictsport.com
funding_url: https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d
version: 1.0.0
license: MIT
description: Real-time ATP and WTA tennis machine learning predictions and +EV betting edges on Kalshi/Polymarket.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        min_edge_pp: float = Field(
            default=8.0,
            description="Minimum fee-aware edge in percentage points to filter betting opportunities.",
        )
        feed_url: str = Field(
            default="https://ipredictsport.com/predictions.json",
            description="Free iPredictSport JSON predictions endpoint.",
        )
        track_record_url: str = Field(
            default="https://ipredictsport.com/track_record.json",
            description="Audited out-of-sample track record endpoint.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def get_tennis_edges(
        self,
        min_edge: float | None = None,
        __event_emitter__: Callable[[dict[str, Any]], Any] | None = None,
    ) -> str:
        """Fetch live tennis matches with positive expected value (+EV) edges against Kalshi/Polymarket order books.

        :param min_edge: Minimum edge in percentage points (e.g. 8.0 for 8%).
        :return: Formatted list of matches, win probabilities, and quarter-Kelly position sizes.
        """
        threshold = min_edge if min_edge is not None else self.valves.min_edge_pp
        try:
            resp = requests.get(self.valves.feed_url, timeout=10.0)
            resp.raise_for_status()
            evals = resp.json().get("kalshi_evaluations", [])

            matches = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                if edge >= threshold:
                    matches.append(
                        f"• {item.get('match')}: Model {float(item.get('our_p1', 0))*100:.1f}% vs "
                        f"Kalshi {float(item.get('kalshi_p1', 0))*100:.0f}¢ | Edge: +{edge:.1f}pp | "
                        f"¼-Kelly: {float(item.get('kelly_quarter', 0))*100:.1f}% bankroll\n"
                        f"  Trade Link: {item.get('trade_url', 'https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d')}"
                    )

            if not matches:
                return f"No active tennis market edges found exceeding {threshold}pp threshold."

            return f"Found {len(matches)} +EV tennis market opportunities:\n\n" + "\n\n".join(matches)

        except (requests.RequestException, ValueError, KeyError) as exc:
            return f"Error querying iPredictSport predictions: {exc}"

    def get_match_forecast(self, player_name: str) -> str:
        """Lookup point-level machine learning win probability and match context for a tennis player.

        :param player_name: Name or surname of player (e.g. Alcaraz, Swiatek).
        :return: Match details, surface, and model forecast.
        """
        try:
            resp = requests.get(self.valves.feed_url, timeout=10.0)
            resp.raise_for_status()
            matches = resp.json().get("matches", [])

            q = player_name.strip().lower()
            results = []
            for m in matches:
                p1 = str(m.get("p1_name", "")).lower()
                p2 = str(m.get("p2_name", "")).lower()
                if q in p1 or q in p2:
                    results.append(
                        f"Match: {m.get('match')}\n"
                        f"Tournament: {m.get('tournament')} ({m.get('surface')})\n"
                        f"Model Winner: {m.get('predicted_winner')}\n"
                        f"Player 1 ({m.get('p1_name')}): {float(m.get('p1_prob', 0))*100:.1f}%\n"
                        f"Player 2 ({m.get('p2_name')}): {float(m.get('p2_prob', 0))*100:.1f}%"
                    )

            if not results:
                return f"No scheduled matches found for '{player_name}'."
            return "\n\n---\n\n".join(results)

        except (requests.RequestException, ValueError, KeyError) as exc:
            return f"Error querying match forecast: {exc}"

    def get_track_record(self) -> str:
        """Retrieve verified out-of-sample model track record and calibration benchmarks.

        :return: Audited accuracy, Brier scores, and closing-line value (CLV).
        """
        try:
            resp = requests.get(self.valves.track_record_url, timeout=10.0)
            resp.raise_for_status()
            overall = resp.json().get("overall", {})
            return (
                f"iPredictSport Audited Model Track Record:\n"
                f"• Evaluated Matches: {overall.get('n')}\n"
                f"• Audited Accuracy: {float(overall.get('accuracy', 0))*100:.1f}%\n"
                f"• Average Closing Line Value (CLV): +{float(overall.get('avg_clv_pp', 0)):.2f}pp vs Market\n"
                f"• Brier Score: {float(overall.get('our_brier', 0)):.4f}\n"
                f"• Verification: https://ipredictsport.com/track_record.json"
            )
        except (requests.RequestException, ValueError, KeyError) as exc:
            return f"Error retrieving track record: {exc}"


if __name__ == "__main__":
    t = Tools()
    print(">> Open WebUI Tool Test:")
    print(t.get_track_record())

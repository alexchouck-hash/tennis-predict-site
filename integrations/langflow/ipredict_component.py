"""Langflow custom component for iPredictSport tennis predictions and market alpha."""

from __future__ import annotations

from typing import Any, ClassVar

import requests

try:
    from langflow.custom import Component
    from langflow.io import FloatInput, MessageTextInput, Output
    from langflow.schema import Data
except ImportError:
    # Fallback definition if langflow is not installed
    class Component:  # type: ignore
        pass

    def FloatInput(*args, **kwargs):  # type: ignore
        return None

    def MessageTextInput(*args, **kwargs):  # type: ignore
        return None

    def Output(*args, **kwargs):  # type: ignore
        return None

    class Data:  # type: ignore
        def __init__(self, data: dict[str, Any]):
            self.data = data

IPREDICT_FEED_URL = "https://ipredictsport.com/predictions.json"


class IPredictSportComponent(Component):
    display_name = "iPredictSport Tennis & Market Alpha"
    description = (
        "Fetches point-level machine learning tennis predictions and +EV betting edges "
        "on Kalshi and Polymarket order books with quarter-Kelly staking."
    )
    icon = "tennis-ball"

    inputs: ClassVar[list[Any]] = [
        FloatInput(
            name="min_edge_pp",
            display_name="Minimum Edge (pp)",
            info="Minimum fee-aware edge in percentage points (default: 8.0)",
            value=8.0,
        ),
        MessageTextInput(
            name="player_filter",
            display_name="Player Filter",
            info="Optional filter by player name (e.g. Alcaraz, Sinner)",
            value="",
        ),
    ]

    outputs: ClassVar[list[Any]] = [
        Output(display_name="Edges Data", name="edges_data", method="build_edges"),
        Output(display_name="Summary Text", name="summary_text", method="build_summary"),
    ]

    def build_edges(self) -> list[Data]:
        min_edge = float(self.min_edge_pp or 8.0)
        filter_str = str(self.player_filter or "").strip().lower()

        try:
            resp = requests.get(IPREDICT_FEED_URL, timeout=10.0)
            resp.raise_for_status()
            evals = resp.json().get("kalshi_evaluations", [])

            results = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                match = str(item.get("match") or "").strip()

                if edge >= min_edge and match and match.lower() != "none":
                    if filter_str and filter_str not in match.lower():
                        continue

                    results.append(Data(data={
                        "match": match,
                        "ticker": item.get("ticker"),
                        "model_probability": float(item.get("our_p1") or 0.0),
                        "market_price": float(item.get("kalshi_p1") or 0.0),
                        "edge_pp": edge,
                        "quarter_kelly_pct": float(item.get("kelly_quarter") or 0.0) * 100,
                        "trade_url": item.get("trade_url") or "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d",
                    }))

            return results
        except (requests.RequestException, ValueError, KeyError):
            return []

    def build_summary(self) -> str:
        edges = self.build_edges()
        if not edges:
            return f"No tennis market edges found exceeding {self.min_edge_pp}pp."

        lines = [f"Found {len(edges)} qualifying +EV tennis trading edges:"]
        for e in edges:
            d = e.data if hasattr(e, "data") else e
            lines.append(
                f"- {d['match']}: Model {d['model_probability']*100:.1f}% vs Price {d['market_price']*100:.0f}c "
                f"| Edge: +{d['edge_pp']:.1f}pp | 1/4-Kelly: {d['quarter_kelly_pct']:.1f}%"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    comp = IPredictSportComponent()
    comp.min_edge_pp = 5.0
    comp.player_filter = ""
    print(">> Langflow Component Test:")
    print(comp.build_summary())

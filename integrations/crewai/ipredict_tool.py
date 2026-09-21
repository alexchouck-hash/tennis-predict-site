"""Native CrewAI and LangChain Tool for iPredictSport tennis predictions."""

from __future__ import annotations

import requests
from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
except ImportError:
    # Fallback to standard object if crewai is not installed in current environment
    class BaseTool:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass


class TennisPredictionInput(BaseModel):
    """Input parameters for querying tennis market edges."""
    min_edge_pp: float = Field(default=8.0, description="Minimum fee-aware edge in percentage points")
    confidence: str = Field(default="medium_plus", description="Minimum confidence filter (any, medium_plus, high_only)")


class IPredictSportTool(BaseTool):
    name: str = "iPredictSport Tennis Prediction Scanner"
    description: str = (
        "Fetches active ATP and WTA tennis match predictions, calibrated win probabilities, "
        "and positive-EV betting edges against Kalshi and Polymarket order books."
    )
    args_schema: type[BaseModel] = TennisPredictionInput

    def _run(self, min_edge_pp: float = 8.0, confidence: str = "medium_plus") -> str:
        try:
            resp = requests.get("https://ipredictsport.com/predictions.json", timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            evals = data.get("kalshi_evaluations", [])

            matches = []
            for item in evals:
                edge = float(item.get("edge_pp") or 0.0)
                if edge >= min_edge_pp:
                    matches.append(
                        f"- {item.get('match')}: Model Prob {float(item.get('our_p1', 0))*100:.1f}%, "
                        f"Kalshi Price {float(item.get('kalshi_p1', 0))*100:.0f}¢, Edge +{edge:.1f}pp, "
                        f"¼-Kelly: {float(item.get('kelly_quarter', 0))*100:.1f}%"
                    )

            if not matches:
                return f"No tennis market edges found exceeding {min_edge_pp}pp."

            return f"Found {len(matches)} +EV tennis market opportunities:\n" + "\n".join(matches)
        except (requests.RequestException, ValueError, KeyError) as exc:
            return f"Error retrieving iPredictSport predictions: {exc}"

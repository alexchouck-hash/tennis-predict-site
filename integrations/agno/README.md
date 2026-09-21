# Agno (formerly Phidata) Toolkit for iPredictSport Tennis Predictions

Supercharge your [Agno](https://github.com/agno-agi/agno) (formerly Phidata) AI agents with real-time ATP/WTA machine learning predictions, calibrated win probabilities, and +EV betting edges on prediction markets (Kalshi & Polymarket).

---

## ⚡ Installation

```bash
pip install agno requests
# Or if using legacy phidata:
# pip install phidata requests
```

---

## 🤖 Usage Example

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from ipredict_toolkit import IPredictSportTools

# Initialize an Agent equipped with the iPredictSport Toolkit
sports_quant = Agent(
    name="TennisQuant",
    model=OpenAIChat(id="gpt-4o"),
    tools=[IPredictSportTools(min_edge_pp=8.0)],
    show_tool_calls=True,
    markdown=True,
    instructions=[
        "You are an expert sports prediction market analyst.",
        "Scan the board for ATP/WTA matches where our model has an edge >= 8.0pp over Kalshi.",
        "Provide clear quarter-Kelly position sizes and include the direct trade links.",
    ],
)

# Run the agent
sports_quant.print_response(
    "What are the top prediction market opportunities in tennis today?",
    stream=True,
)
```

---

## 🛠️ Toolkit Methods

1. **`get_positive_ev_edges(min_edge_pp=8.0)`**: Queries live Kalshi and Polymarket contract pricing, compares against the machine learning fair odds, and returns qualifying positive-EV trades with fee-aware quarter-Kelly sizing.
2. **`get_live_predictions(search_player="")`**: Searches upcoming ATP and WTA match schedules for point-level ML win probability forecasts.
3. **`get_track_record()`**: Provides verified out-of-sample Brier scores, fold stability metrics, and audited ROI benchmarks.

---

## 🎁 Kalshi Bonus & Fee Credits

Sign up with our official partner link to receive trading fee credits and automated CLOB execution bonuses:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

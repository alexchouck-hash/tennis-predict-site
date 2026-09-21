# Microsoft AutoGen Integration for iPredictSport Tennis Predictions

Connect autonomous multi-agent AI teams in [Microsoft AutoGen](https://github.com/microsoft/autogen) to live ATP/WTA tennis predictions and quantitative betting edges on Kalshi and Polymarket.

---

## 🚀 Quickstart

### 1. Installation

```bash
pip install pyautogen requests
```

### 2. Multi-Agent Setup Example

```python
import autogen
from ipredict_autogen import register_ipredict_tools

# 1. Configure the LLM
config_list = [{"model": "gpt-4o", "api_key": "YOUR_OPENAI_KEY"}]
llm_config = {"config_list": config_list, "cache_seed": 42}

# 2. Define the Sports Quant Assistant Agent
quant_assistant = autogen.AssistantAgent(
    name="SportsQuantAgent",
    system_message=(
        "You are an elite quantitative sports bettor and prediction market analyst. "
        "Use your registered tools to inspect live tennis model probabilities from iPredictSport, "
        "calculate fee-aware edge against Kalshi and Polymarket order books, and recommend "
        "disciplined quarter-Kelly position sizes. Always verify the edge is >= 8.0pp before recommending action."
    ),
    llm_config=llm_config,
)

# 3. Define the User Proxy Agent for Tool Execution
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    code_execution_config={"use_docker": False},
)

# 4. Register iPredictSport Tools
register_ipredict_tools(quant_assistant, user_proxy)

# 5. Kickoff the Analysis
user_proxy.initiate_chat(
    quant_assistant,
    message="Scan today's tennis board for positive expected value (+EV) trades on Kalshi with at least 8% edge. Provide quarter-Kelly bankroll staking."
)
```

---

## 🛠️ Available Functions

| Function Name | Description | Key Arguments |
|---|---|---|
| `get_tennis_betting_edges` | Fetches active +EV betting edges against Kalshi/Polymarket order books. | `min_edge_pp: float` (default: `8.0`) |
| `get_match_prediction` | Looks up machine learning win probability and match context for a specific tennis player. | `player_name: str` |
| `get_track_record` | Retrieves audited out-of-sample Brier score benchmark, accuracy, and ROI statistics. | None |

---

## 💡 Connecting via Model Context Protocol (MCP)

AutoGen v0.4+ supports native MCP client connections. You can connect AutoGen directly to our local or remote MCP server:

```python
# AutoGen MCP Server Connection
mcp_config = {
    "server_name": "tennis-predict",
    "command": "python",
    "args": ["-m", "scripts.mcp_server"],
}
```

---

## 🎁 Kalshi Bonus & Fee Credits

Sign up with our official partner link to receive trading fee credits and automated CLOB execution bonuses:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

# CAMEL Multi-Agent Toolkit: iPredictSport Tennis & Market Alpha

Equip communicative multi-agent teams in [CAMEL](https://github.com/camel-ai/camel) with live ATP/WTA predictions and quantitative prediction market edges.

---

## 🚀 Quickstart

```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from ipredict_toolkit import IPredictSportToolkit

toolkit = IPredictSportToolkit(min_edge_pp=8.0)
agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Quant",
        content="You are a prediction market analyst. Use tools to find +EV tennis bets.",
    ),
    tools=toolkit.get_tools(),
)

response = agent.step("Scan for today's best +EV trades on Kalshi.")
print(response.msgs[0].content)
```

---

## 🎁 Kalshi Partner Bonus

Sign up with our official partner link for fee credits:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

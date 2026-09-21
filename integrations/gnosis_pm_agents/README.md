# Gnosis Prediction Market Agent Tooling Integration

Equip autonomous AI prediction agents built with [`gnosis/prediction-market-agent-tooling`](https://github.com/gnosis/prediction-market-agent-tooling) and [`valory-xyz/trader`](https://github.com/valory-xyz/trader) with calibrated tennis match forecasts from iPredictSport.

---

## ⚡ What this Tool Provides

1. **Question Disambiguation**: Extracts player surnames from natural language event titles and questions (e.g. *"Will Carlos Alcaraz win his match at Indian Wells?"*).
2. **Point-Level Machine Learning Probabilities**: Looks up the corresponding ATP/WTA match in the free `https://ipredictsport.com/predictions.json` feed and returns the win probability $p_{\text{yes}}$.
3. **Calibrated Confidence**: Quantifies directional certainty for autonomous agent decision engines.

---

## 🚀 Usage with `prediction-market-agent-tooling`

```python
from ipredict_agent_tool import IPredictSportAgentTool

tool = IPredictSportAgentTool()

# Evaluate any tennis prediction market question
prediction = tool.predict_market("Will Sinner defeat his opponent in the quarterfinals?")
print(f"Target Player: {prediction.get('target_player')}")
print(f"Model Probability (P_YES): {prediction.get('p_yes')}")
print(f"Model Confidence: {prediction.get('confidence')}")
```

---

## 🎁 Kalshi Bonus & Fee Credits

If your agents also trade on CFTC-regulated US dollar prediction markets with 0% maker fees:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

# Polymarket Agents Integration for iPredictSport Tennis Predictions

Connect autonomous prediction market agents built with [Polymarket/agents](https://github.com/Polymarket/agents) to live ATP/WTA machine learning predictions, calibrated win probabilities, and +EV betting edges.

---

## 🎯 What this does

1. **Cross-References Contracts**: Matches ATP and WTA tennis events on Polymarket's Gamma and CLOB APIs against point-level match forecasts from `https://ipredictsport.com/predictions.json`.
2. **Calculates Edge & Quarter-Kelly**: Evaluates model probability against Polymarket's Best Bid/Ask and outputs mathematically sound quarter-Kelly position sizes.
3. **Execution Ready**: Provides CLOB token IDs, condition IDs, and market slugs for automated order submission via `@polymarket/clob-client` or Python `py-clob-client`.

---

## ⚡ Quickstart

### 1. Installation

```bash
pip install requests py-clob-client
```

### 2. Autonomous Agent Integration

```python
from ipredict_market_finder import PolymarketTennisEvaluator

evaluator = PolymarketTennisEvaluator(min_edge_pp=8.0)
edges = evaluator.scan_edges()

for edge in edges:
    print(f"Contract: {edge['question']}")
    print(f"Model Prob: {edge['model_probability']*100:.1f}% vs Poly Price: {edge['polymarket_price']*100:.1f}¢")
    print(f"Edge: +{edge['edge_percentage_points']}pp | Quarter-Kelly: {edge['quarter_kelly_stake_pct']}% of bankroll")
    
    # Execute order via py-clob-client
    # client.create_order(...)
```

---

## 🎁 Kalshi & Polymarket Comparison

While Polymarket offers decentralized USDC settlement, Kalshi offers CFTC-regulated binary options with **0% maker fees**. We recommend cross-market arbitrage or executing resting limit orders on Kalshi:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

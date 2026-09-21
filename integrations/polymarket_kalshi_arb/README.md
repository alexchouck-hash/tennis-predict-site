# Cross-Platform Arbitrage Scanner (Polymarket & Kalshi)

Automated synthetic arbitrage and statistical mispricing detector designed for cross-market prediction bots (including [`ImMike/polymarket-arbitrage`](https://github.com/ImMike/polymarket-arbitrage) and [`cutupdev/Polymarket-Kalshi-Arbitrage-Bot`](https://github.com/cutupdev/Polymarket-Kalshi-Arbitrage-Bot)).

---

## ⚡ How It Works

1. **Pure Synthetic Arbitrage**:
   - Detects when:
     $$\text{Price}(\text{Player A on Polymarket}) + \text{Price}(\text{Player B on Kalshi}) < \$1.00$$
   - Buying both outcomes locks in a **guaranteed risk-free dollar settlement** on match completion regardless of who wins.
2. **Model-Guided Statistical Arbitrage**:
   - Compares the price divergence between Kalshi and Polymarket against iPredictSport's point-level machine learning fair odds.
   - Highlights the venue where the contract is most underpriced.

---

## 🚀 Quickstart

```python
from cross_market_arb import CrossMarketArbitrageScanner

scanner = CrossMarketArbitrageScanner(min_synthetic_spread=0.02, min_stat_edge_pp=5.0)
results = scanner.scan()

# Inspect pure synthetic risk-free arbs
for arb in results["synthetic_arbitrages"]:
    print(f"Risk-free Spread ({arb['net_risk_free_profit_pct']}%): {arb['leg1']} AND {arb['leg2']}")

# Inspect venue discrepancies
for disc in results["statistical_discrepancies"]:
    print(f"{disc['match']}: Model {disc['model_fair_probability']*100:.1f}% | Poly: {disc['polymarket_price']} vs Kalshi: {disc['kalshi_price']} (Buy on {disc['preferred_execution_venue']})")
```

---

## 🎁 Kalshi Fee Rebates & Bonus

Prediction market contracts on Kalshi offer **0% maker fees**. Sign up with our partner link for trading fee credits:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

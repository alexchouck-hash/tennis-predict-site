# Kalshi Quantitative Signal Strategy for Auto-Traders

Pluggable quantitative signal engine for Python-based Kalshi auto-trading bots (including [`ryanfrigo/kalshi-ai-trading-bot`](https://github.com/ryanfrigo/kalshi-ai-trading-bot), [`yllvar/Kalshi-Quant-TeleBot`](https://github.com/yllvar/Kalshi-Quant-TeleBot), and [`else24/kalshi-market-bot`](https://github.com/else24/kalshi-market-bot)).

---

## ⚡ What this Module Does

1. **Free Predictions Ingestion**: Reads calibrated ATP and WTA match probabilities from `https://ipredictsport.com/predictions.json`.
2. **Quantitative Filtering**:
   - Enforces a minimum $+8.0\text{pp}$ edge floor against live order book asks.
   - Skips high-variance $[0.55, 0.60)$ coin-flip matches.
   - Applies post-only maker pricing to avoid taker fees.
3. **Kelly Sizing**: Computes exact contract counts scaled by fee-aware quarter-Kelly.
4. **Turnkey Order Payloads**: Returns pre-formatted JSON dictionaries ready to submit directly to Kalshi's Trade API `/portfolio/orders`.

---

## 🚀 Quickstart

```python
from ipredict_signal_strategy import KalshiQuantSignalEngine

# Initialize with your portfolio settings
engine = KalshiQuantSignalEngine(
    bankroll_usd=2500.0,
    min_edge_pp=8.0,
    max_stake_fraction=0.05
)

# Generate executable order payloads
orders = engine.generate_orders()

for order in orders:
    print(f"Submitting {order['count']}x {order['ticker']} Yes @ {order['yes_price']}¢")
    # Submit via your bot's Kalshi client:
    # client.create_order(**order)
```

---

## 🎁 Kalshi Bonus & Fee Credits

Sign up with our partner link to unlock API trading and receive exclusive fee credits:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

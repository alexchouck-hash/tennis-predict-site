# Polymarket `py-clob-client` Automated Trading Engine

Connect the official Python CLOB client for Polymarket ([`Polymarket/py-clob-client`](https://github.com/Polymarket/py-clob-client)) to live ATP/WTA machine learning predictions from iPredictSport.

---

## ⚡ Features

- **Direct CLOB Integration**: Interfaces with `@polymarket/clob-client` endpoints.
- **Model Edge Calculation**: Computes mathematical divergence between Polymarket order books and point-level ML probabilities.
- **Quarter-Kelly Sizing**: Sizes orders in USDC with strict risk caps.
- **Dry-Run Mode**: Safely tests order generation before live signing on Polygon.

---

## 🚀 Usage

```python
from ipredict_poly_trader import PolymarketClobTrader

trader = PolymarketClobTrader(bankroll_usdc=1000.0, min_edge_pp=8.0, dry_run=True)
orders = trader.evaluate_and_trade()
for order in orders:
    print(f"Executed: {order['match']} -> Stake ${order['stake_usdc']}")
```

---

## 🎁 Kalshi 0% Maker Alternative

If you also trade US-regulated prediction markets with 0% maker fees:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

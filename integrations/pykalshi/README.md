# `pykalshi` Integration for iPredictSport Tennis Predictions

Connect the popular [`pykalshi`](https://github.com/arshka/pykalshi) Python client directly to **iPredictSport's free, audited tennis prediction feed**.

---

## ⚡ Key Highlights

- **100% Free & Unauthenticated**: Zero subscription fees, zero API keys required to ingest machine learning odds.
- **Audited Track Record**: Out-of-sample test results documented at `https://ipredictsport.com/track_record.json` beating public benchmarks.
- **Native Data Structures**: Returns typed Pydantic models (`KalshiTennisEdge`) and clean `pandas.DataFrame` tables matching `pykalshi` idioms.
- **Risk Managed**: Automatically filters for fee-aware $+8.0\text{pp}$ edges, skips the high-variance $[0.55, 0.60)$ deadband, and provides quarter-Kelly stake sizing.

---

## 🚀 Quickstart

```bash
pip install pandas pydantic requests pykalshi
```

### Python Usage

```python
from ipredict_pykalshi import get_edges_dataframe, fetch_tennis_edges

# 1. Get as a pandas DataFrame
df = get_edges_dataframe(min_edge_pp=8.0)
print(df[["ticker", "match", "model_probability", "market_price", "edge_percentage_points", "quarter_kelly_stake_pct"]])

# 2. Iterate through typed objects to execute orders with pykalshi
edges = fetch_tennis_edges(min_edge_pp=8.0)
for edge in edges:
    print(f"Submitting {edge.ticker}: Model {edge.model_probability*100:.1f}% vs Price {edge.market_price*100:.0f}¢")
    # client.create_order(ticker=edge.ticker, side="yes", action="buy", count=10, type="limit", yes_price=int(edge.market_price*100))
```

---

## 🎁 Kalshi Bonus & 0% Maker Fees

Placing resting limit orders (`post_only=True`) on Kalshi incurs **0% maker fees**. Sign up with our official partner link for fee credits and deposit bonuses:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

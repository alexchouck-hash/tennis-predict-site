# Custom ML Price Provider for Polymarket `poly-market-maker`

Connect Polymarket's official CLOB market maker bot ([`Polymarket/poly-market-maker`](https://github.com/Polymarket/poly-market-maker)) to live ATP/WTA machine learning fair odds from iPredictSport.

---

## 🎯 Why Market Makers Need a Predictive Center

Most CLOB market makers center their quotes around the mid-market price of the order book. In sports and fast-moving prediction markets, this leads to **adverse selection**: informed takers pick off your stale resting bids when player odds shift.

By plugging `IPredictPriceProvider` into `poly-market-maker`:
1. **Dynamic Fair Price Anchor**: Your quote ladder is anchored to calibrated point-level machine learning forecasts.
2. **Asymmetric Spreads**: If the market is priced at 45¢ but the model fair value is 55¢, your quotes will rest to buy below 55¢ and sell above 55¢, capturing inventory at positive expected value.
3. **Zero Maker Fees**: Limit orders placed via `poly-market-maker` pay 0% fees.

---

## 🚀 Quickstart

### 1. Installation

In your `poly-market-maker` environment:
```bash
pip install requests
```

### 2. Integration with `poly-market-maker`

In your `poly-market-maker` configuration or custom strategy script:

```python
from custom_ipredict_pricer import IPredictPriceProvider

# Initialize the price provider
pricer = IPredictPriceProvider(refresh_interval_sec=120)

# In your market maker quote loop:
bands = pricer.get_order_bands(token_or_player="Sinner", half_spread=0.025, order_size=50.0)
print(f"Submitting Maker Orders: Bid @ {bands['bid_price']} | Ask @ {bands['ask_price']}")

# Place orders via py-clob-client
# client.create_order(...)
```

---

## 🎁 Kalshi Bonus & Fee Credits

If you also trade CFTC-regulated US dollar contracts on Kalshi with 0% maker fees:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

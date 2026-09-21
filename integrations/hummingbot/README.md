# Hummingbot Market Making Script for iPredictSport Tennis Predictions

Provide liquidity and capture spreads on prediction markets with [Hummingbot](https://github.com/hummingbot/hummingbot), using machine learning fair value models from iPredictSport.

---

## 🎯 The Edge: 0% Maker Fees + ML Anchor

Prediction markets like Kalshi charge **0% exchange fees for maker orders** (resting limit orders). Traditional market makers face toxic flow when market sentiment changes. 

By anchoring your quote center to iPredictSport's point-level machine learning fair price:
1. You place resting bids below model fair value, and resting asks above model fair value.
2. You earn the bid-ask spread while maintaining positive expected value on fills.
3. Maker fees remain $0.00.

---

## 🚀 Quickstart

1. Place `ipredict_maker_script.py` in your Hummingbot `scripts/` directory.
2. In Hummingbot CLI:
   ```bash
   create --script-config ipredict_maker_script.py
   start
   ```

---

## 🎁 Kalshi Fee Rebates & Bonus

Sign up with our partner link for trading credits and CLOB API execution:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

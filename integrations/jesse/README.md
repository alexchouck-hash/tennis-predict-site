# Jesse Trading Bot Strategy: iPredictSport Tennis Predictions

Connect the advanced Python algorithmic trading engine [Jesse](https://github.com/jesse-ai/jesse) to point-level machine learning predictions and prediction market alpha.

---

## ⚡ Overview

- **Custom Strategy**: Subclasses `jesse.strategies.Strategy`.
- **Fee-Aware Filter**: Enforces $+8.0\text{pp}$ edge floor against live order books.
- **Quarter-Kelly Execution**: Positions dynamically scaled by statistical edge.

---

## 🚀 Usage in Jesse

Copy `ipredict_strategy.py` into your Jesse `strategies/` directory:

```bash
jesse routes
jesse live
```

---

## 🎁 Kalshi Partner Bonus

Prediction contracts trade with 0% maker fees on Kalshi. Sign up with our partner link for fee credits:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

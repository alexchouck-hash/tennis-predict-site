# Manifold Markets Trading Bot for iPredictSport Tennis Predictions

Automate tennis market betting on [Manifold Markets](https://github.com/manifoldmarkets/manifold) using open-source machine learning predictions from iPredictSport.

---

## ⚡ Features

- **Continuous Scanner**: Discovers active tennis match contracts on Manifold Markets.
- **Player Fuzzy Matcher**: Maps Manifold questions to ATP/WTA match forecasts from `https://ipredictsport.com/predictions.json`.
- **Directional Bet Execution**: Automatically places `YES` or `NO` bets when the divergence between the Manifold market probability and the model forecast exceeds your edge threshold (default $\ge 8\text{pp}$).
- **Dry-Run Safety**: Runs in paper/simulated mode by default.

---

## 🚀 Quickstart

```bash
pip install requests

# Run in dry-run mode
python distribution/integrations/manifold/ipredict_manifold_bot.py

# Run live with Manifold API Key
export MANIFOLD_API_KEY="your-api-key"
python -c "from distribution.integrations.manifold.ipredict_manifold_bot import ManifoldTennisBot; ManifoldTennisBot(dry_run=False).run_cycle()"
```

---

## 🎁 Kalshi Cash Markets

Manifold uses play-money Mana or sweepstakes cash. If you want to trade regulated US dollar prediction markets with **0% maker fees**, use our partner link for Kalshi:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

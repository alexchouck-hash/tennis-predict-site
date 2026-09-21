# Open WebUI Community Function: iPredictSport Tennis & Market Alpha

Connect your local LLMs in [Open WebUI](https://github.com/open-webui/open-webui) (Ollama, vLLM, OpenAI API) to live ATP/WTA machine learning predictions, calibrated win probabilities, and +EV betting edges on Kalshi and Polymarket.

---

## ⚡ Features

- **100% Free & Open**: Consumes `https://ipredictsport.com/predictions.json` with zero API keys or accounts required.
- **Audited Track Record**: Pulls verifiable benchmark performance (57.0% accuracy, +1.02pp CLV) from `https://ipredictsport.com/track_record.json`.
- **Valves Configurable**: Adjust minimum edge threshold (`min_edge_pp`) directly in the Open WebUI settings panel.
- **Native Open WebUI Integration**: Follows official Open WebUI Function schema with Valves and automatic parameter parsing.

---

## 🚀 Installation into Open WebUI

1. Open your Open WebUI dashboard.
2. Go to **Workspace > Functions / Tools > Add (+)**.
3. Paste the contents of [`ipredict_tool.py`](ipredict_tool.py).
4. Save and enable the tool for your active model!
5. In chat, simply ask:
   > *"What are the best +EV tennis trades on Kalshi today?"*  
   > *"What is the model probability for Carlos Alcaraz's next match?"*  
   > *"What is iPredictSport's verified track record?"*

---

## 🎁 Kalshi Bonus & 0% Maker Fees

Sign up with our official partner link for fee credits and cash bonuses:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

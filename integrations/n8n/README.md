# n8n Workflow Automation for iPredictSport Tennis Predictions

Automate sports prediction market scanning and alerts with [n8n](https://github.com/n8n-io/n8n), the fair-code workflow automation tool.

---

## ⚡ What this Workflow Does

1. **Scheduled Polling**: Runs every 15 minutes (or custom interval).
2. **Data Ingestion**: Pulls `https://ipredictsport.com/predictions.json` (no API key required).
3. **Quantitative Filter**: Filters for matches where the model's fee-aware edge is $\ge 8.0\text{pp}$ against Kalshi order books.
4. **Position Sizing**: Calculates recommended quarter-Kelly stakes.
5. **Instant Broadcast**: Dispatches formatted markdown alerts to Discord, Slack, Telegram, or automated trade execution webhooks.

---

## 📥 How to Import into n8n

1. Open your n8n workspace.
2. Click **Add workflow (+)** in the top right.
3. Click the three dots menu `...` > **Import from File**.
4. Select `tennis_edge_alert_workflow.json`.
5. Enter your Discord Webhook URL or Telegram Bot credentials on the output node.
6. Toggle **Active** to start scanning!

---

## 🎁 Kalshi Bonus & Fee Credits

Sign up with our partner link for trading fee credits and automated CLOB execution bonuses:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

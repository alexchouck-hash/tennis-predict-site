# Discord Webhook Alert Bot for Tennis Prediction Markets

Automatically posts daily +EV tennis betting edge cards into your Discord server or syndicate channels.

### Setup:
1. In your Discord server, go to **Channel Settings > Integrations > Webhooks > New Webhook**.
2. Copy the Webhook URL.
3. Run the script:
   ```bash
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   python discord_alert_bot.py
   ```

### Features:
- Embeds model win probabilities, Kalshi contract price, and positive expected value.
- Recommends fee-aware quarter-Kelly bankroll allocation.
- Includes direct trade links with embedded Kalshi referral bonus credits.

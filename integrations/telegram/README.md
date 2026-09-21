# Telegram Alert Bot for Tennis Prediction Markets

Automatically broadcasts positive-EV tennis trading opportunities and quarter-Kelly sizing into your Telegram channel or syndicate chat.

### Setup:
1. Create a bot using [@BotFather](https://t.me/BotFather) on Telegram and get your Bot Token.
2. Add the bot to your channel or group as an admin.
3. Run the alert broadcaster:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
   export TELEGRAM_CHAT_ID="@your_channel_or_chat_id"
   python telegram_alert_bot.py
   ```

### Features:
- HTML formatted edge reports with calibrated probabilities.
- Inline keyboard buttons linking directly to Kalshi trade markets with embedded partner bonuses.

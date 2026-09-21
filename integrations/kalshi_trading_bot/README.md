# iPredictSport Strategy Plugin for `Viprasol-Tech/kalshi-trading-bot`

This directory provides an official drop-in strategy connecting [Viprasol-Tech/kalshi-trading-bot](https://github.com/Viprasol-Tech/kalshi-trading-bot) to the free, point-level tennis prediction feed from [iPredictSport.com](https://ipredictsport.com).

### Installation & Usage
1. Copy `ipredict_strategy.py` into your `kalshi-trading-bot` project:
   ```bash
   cp ipredict_strategy.py path/to/kalshi-trading-bot/src/kalshi_trading_bot/strategies/
   ```
2. Import or register `IPredictTennisStrategy` in your strategy registry.
3. Test in dry-run mode:
   ```bash
   kalshi-bot run --strategy ipredict_tennis --dry-run
   ```

### Features:
- Connects to `https://ipredictsport.com/predictions.json` (zero auth, 100% free).
- Sized with fee-aware quarter-Kelly bankroll allocation.
- Uses post-only resting limit orders to capture maker rebates ($0 taker fees).

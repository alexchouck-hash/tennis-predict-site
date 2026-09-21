# Freqtrade Signal Provider for iPredictSport Tennis Predictions

Connect the leading algorithmic trading engine [Freqtrade](https://github.com/freqtrade/freqtrade) to live quantitative tennis match predictions, calibrated win probabilities, and prediction market alpha.

---

## 📈 Overview

Freqtrade users can incorporate external statistical edges into their strategies via `IPredictSignalProvider`. This module:
- Ingests free machine learning odds from `https://ipredictsport.com/predictions.json`.
- Identifies prediction market discrepancies (e.g. Kalshi and Polymarket contracts).
- Supplies trade directions, confidence metrics, and quarter-Kelly position sizes directly to Freqtrade's `populate_indicators` and `populate_entry_trend`.

---

## 🚀 Strategy Integration

Copy `ipredict_provider.py` into your Freqtrade `user_data/strategies/` directory, and integrate into your strategy:

```python
from freqtrade.strategy import IStrategy
from pandas import DataFrame
from ipredict_provider import IPredictSignalProvider


class IPredictTennisStrategy(IStrategy):
    minimal_roi = {"0": 0.20, "60": 0.10}
    stoploss = -0.10
    timeframe = "1h"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Scan for edges with at least 8.0pp advantage
        self.provider = IPredictSignalProvider(min_edge_pp=8.0, cache_ttl_seconds=300)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        sig = self.provider.get_signal_for_pair(metadata["pair"])
        dataframe["model_edge"] = sig["edge_pp"] if sig else 0.0
        dataframe["enter_signal"] = 1 if (sig and sig["edge_pp"] >= 8.0) else 0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["enter_signal"] == 1),
            ["enter_long", "enter_tag"]
        ] = (1, "ipredict_edge_entry")
        return dataframe
```

---

## 🎁 Kalshi Fee Rebates & Bonus

Prediction market contracts on Kalshi feature **0% maker fees**. Sign up with our partner link for fee credits and bonus:  
👉 **[Sign up on Kalshi (Partner Bonus)](https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d)**  
*Referral Code:* `eb2fd257-2bc9-465a-a18c-5e9a0ab4848d`

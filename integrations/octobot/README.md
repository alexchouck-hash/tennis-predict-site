# iPredictSport Evaluator for OctoBot

Connects OctoBot prediction market strategies to iPredictSport's free point-level ML tennis probabilities.

### Usage:
```python
from ipredict_evaluator import IPredictSportEvaluator

evaluator = IPredictSportEvaluator(min_edge_pp=8.0)
signal = evaluator.eval_market("KXATPMATCH-26SEP09KHABLO")

if signal and signal["signal"] == "BUY":
    print(f"Executing +EV Trade: Edge {signal['edge_pp']}pp, Fair: {signal['fair_price']}")
```

# iPredictSport DataLoader for `georgedouzas/sports-betting`

Enables users of [georgedouzas/sports-betting](https://github.com/georgedouzas/sports-betting) to load point-level ML tennis predictions and market evaluations directly into their backtesting and value-betting pipelines.

### Usage:
```python
from ipredict_dataloader import IPredictSportDataLoader

loader = IPredictSportDataLoader()
df_matches = loader.load_upcoming_matches()
df_edges = loader.load_market_evaluations()

print(f"Loaded {len(df_matches)} matches and {len(df_edges)} market evaluations.")
print(df_edges[["match", "our_p1", "kalshi_p1", "edge_pp"]].head())
```

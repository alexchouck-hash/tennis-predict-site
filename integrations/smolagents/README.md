# Hugging Face smolagents Tool for Tennis Prediction Markets

Connects Hugging Face `smolagents` (CodeAgent or ToolCallingAgent) to live tennis match ML probabilities and +EV edges.

### Usage:
```python
from smolagents import CodeAgent, HfApiModel
from ipredict_smolagent import get_tennis_edges

model = HfApiModel()
agent = CodeAgent(tools=[get_tennis_edges], model=model)

agent.run("Are there any profitable betting edges on Kalshi tennis contracts today?")
```

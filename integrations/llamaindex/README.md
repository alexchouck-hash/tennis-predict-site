# LlamaIndex Tool for Tennis Prediction Markets

Enables LlamaIndex agents, RAG pipelines, and conversational workflows to query live tennis match predictions and fee-aware +EV betting edges.

### Usage:
```python
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from ipredict_tool import get_llamaindex_tool

llm = OpenAI(model="gpt-4o")
tennis_tool = get_llamaindex_tool()

agent = ReActAgent.from_tools([tennis_tool], llm=llm, verbose=True)
response = agent.chat("What are the most mispriced tennis matches on Kalshi today?")
print(response)
```

# iPredictSport Tool for CrewAI & LangChain

Enables CrewAI and LangChain autonomous agents to evaluate tennis prediction markets and identify mispriced contracts.

### Quickstart:
```python
from crewai import Agent, Task, Crew
from ipredict_tool import IPredictSportTool

tennis_tool = IPredictSportTool()

quant_agent = Agent(
    role="Prediction Market Quantitative Trader",
    goal="Find +EV mispricings on Kalshi and Polymarket tennis contracts",
    tools=[tennis_tool],
    verbose=True,
)

task = Task(
    description="Scan today's tennis board and report the top 3 betting edges.",
    agent=quant_agent,
    expected_output="Markdown report summarizing the highest expected value bets."
)

crew = Crew(agents=[quant_agent], tasks=[task])
result = crew.kickoff()
print(result)
```

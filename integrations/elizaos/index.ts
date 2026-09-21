import { Plugin, Action, IAgentRuntime, Memory, State } from "@elizaos/core";

export const getTennisPredictionsAction: Action = {
    name: "GET_TENNIS_PREDICTIONS",
    similes: ["CHECK_TENNIS_ODDS", "GET_TENNIS_EDGES", "PREDICTION_MARKET_TENNIS"],
    description: "Fetches active ATP/WTA tennis match win probabilities and positive-EV prediction market edges from iPredictSport.",
    validate: async (_runtime: IAgentRuntime, _message: Memory) => true,
    handler: async (_runtime: IAgentRuntime, _message: Memory, _state?: State) => {
        try {
            const resp = await fetch("https://ipredictsport.com/predictions.json");
            const data = await resp.json();
            const evals = data.kalshi_evaluations || [];
            
            // Filter for high-confidence positive-EV edges
            const edges = evals.filter((e: any) => (e.edge_pp || 0) >= 8.0);
            
            return {
                text: `Found ${edges.length} high-conviction tennis prediction market edges. Top pick: ${edges[0]?.match} (Edge: +${edges[0]?.edge_pp}pp)`,
                data: edges,
            };
        } catch (err) {
            return { text: `Failed to fetch iPredictSport predictions: ${err}` };
        }
    },
    examples: [
        [
            {
                user: "{{user1}}",
                content: { text: "Are there any +EV bets on Kalshi tennis today?" },
            },
            {
                user: "{{agentName}}",
                content: {
                    text: "I checked iPredictSport's quantitative models: Frances Tiafoe vs Ben Shelton has a +11.6pp fee-aware edge on Kalshi with a recommended 3.8% quarter-Kelly bankroll stake.",
                },
            },
        ],
    ],
};

export const ipredictPlugin: Plugin = {
    name: "ipredict",
    description: "iPredictSport quantitative tennis analytics and prediction market trading plugin",
    actions: [getTennisPredictionsAction],
    evaluators: [],
    providers: [],
};

export default ipredictPlugin;

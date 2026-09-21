/**
 * iPredictSport Google Sheets Connector
 * 
 * Fetches real-time machine learning tennis predictions and positive-EV betting edges
 * directly into your Google Sheet.
 * 
 * Usage:
 *   =GET_TENNIS_EDGES(8.0)
 *   =GET_TENNIS_BOARD()
 */

const FEED_URL = "https://ipredictsport.com/predictions.json";
const KALSHI_REF_URL = "https://kalshi.com/r/eb2fd257-2bc9-465a-a18c-5e9a0ab4848d";

/**
 * Returns a table of positive-EV tennis betting opportunities from Kalshi.
 * 
 * @param {number} minEdge Minimum edge in percentage points (default: 8.0)
 * @return {Array<Array>} Two-dimensional array representing the data table
 * @customfunction
 */
function GET_TENNIS_EDGES(minEdge) {
  minEdge = minEdge || 8.0;
  
  try {
    const response = UrlFetchApp.fetch(FEED_URL, { muteHttpExceptions: true });
    const json = JSON.parse(response.getContentText());
    const evals = json.kalshi_evaluations || [];
    
    const headers = [
      "Match",
      "Model Prob",
      "Kalshi Price",
      "Edge (pp)",
      "Confidence",
      "Quarter-Kelly",
      "Kalshi Ticker",
      "Trade URL"
    ];
    
    const rows = [headers];
    
    for (let i = 0; i < evals.length; i++) {
      const e = evals[i];
      const edge = Number(e.edge_pp || 0);
      
      if (edge >= minEdge) {
        const action = e.trade_action || {};
        const tradeUrl = action.url || action.trade_url || KALSHI_REF_URL;
        const ticker = action.ticker || e.event_ticker || "";
        
        rows.push([
          e.match || "N/A",
          (Number(e.our_p1 || 0) * 100).toFixed(1) + "%",
          (Number(e.kalshi_p1 || 0) * 100).toFixed(0) + "¢",
          edge.toFixed(1) + "pp",
          String(e.confidence_band || "medium").toUpperCase(),
          (Number(e.kelly_quarter || 0) * 100).toFixed(1) + "%",
          ticker,
          tradeUrl
        ]);
      }
    }
    
    return rows.length > 1 ? rows : [["No edges found exceeding " + minEdge + "pp"]];
  } catch (err) {
    return [["Error loading iPredictSport feed: " + err.message]];
  }
}

/**
 * Returns the current active ATP and WTA tennis prediction board.
 * 
 * @return {Array<Array>} Two-dimensional array of upcoming matches
 * @customfunction
 */
function GET_TENNIS_BOARD() {
  try {
    const response = UrlFetchApp.fetch(FEED_URL, { muteHttpExceptions: true });
    const json = JSON.parse(response.getContentText());
    const upcoming = json.upcoming_board || [];
    
    const headers = [
      "Tournament",
      "Round",
      "Surface",
      "Scheduled Start (UTC)",
      "Player 1",
      "Player 2",
      "Model Favorite",
      "Win Probability",
      "Confidence"
    ];
    
    const rows = [headers];
    
    for (let i = 0; i < upcoming.length; i++) {
      const m = upcoming[i];
      rows.push([
        m.tourney || "ATP/WTA",
        m.round || "Match",
        m.surface || "N/A",
        m.start ? m.start.substring(0, 19).replace("T", " ") : "N/A",
        m.p1,
        m.p2,
        m.favorite || m.p1,
        (Number(m.favorite_prob || m.p1_win_prob || 0.5) * 100).toFixed(1) + "%",
        String(m.confidence_band || "low").toUpperCase()
      ]);
    }
    
    return rows;
  } catch (err) {
    return [["Error: " + err.message]];
  }
}

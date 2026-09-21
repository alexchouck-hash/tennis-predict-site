# Google Sheets Live Connector for Tennis Betting & Prediction Markets

Import real-time machine learning tennis predictions and +EV betting edges directly into your betting or bankroll spreadsheet.

### Quick Setup:
1. Open your Google Sheet.
2. Click **Extensions > Apps Script**.
3. Delete any default code and paste the contents of `Code.gs`.
4. Click **Save**.
5. Back in your Google Sheet, use custom formulas:
   - `=GET_TENNIS_EDGES(8.0)`: Populates a table of all Kalshi tennis contracts with $\ge 8\text{pp}$ fee-aware edge and quarter-Kelly sizing.
   - `=GET_TENNIS_BOARD()`: Populates the full schedule of upcoming ATP/WTA matches with model win percentages.

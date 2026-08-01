# Idea Proposal: Dividend & Upside Portfolio Optimizer

## 1. Overview & Concept

The goal of this experiment is to create an automated portfolio construction algorithm that selects and weights stocks from a target universe (e.g., watchlist or full market) to maximize expected returns—either via **dividend yield**, **analyst target upside**, or a hybrid combination of both—subject to risk-mitigation constraints (such as a hard single-asset exposure limit).

---

## 2. Core Components

### A. Data Inputs
1. **Dividend History & Record**: Historical payouts, dividend frequency, ex-dividend dates, and trailing/forward dividend yields.
2. **Current Market Price**: Live or end-of-day market price ($P_{\text{current}}$).
3. **Analyst Price Targets**: Consensus mean/median target price ($P_{\text{target}}$) from financial sources (e.g., Yahoo Finance).
4. **Financial Health & Risk Metrics (Optional Expansion)**: Payout ratio, debt levels, earnings stability.

### B. Objective Functions (To Maximize)
- **Option 1: Maximize Dividend Yield**: Focus on passive income generation.
- **Option 2: Maximize Analyst Upside**: Focus on capital appreciation $\frac{P_{\text{target}} - P_{\text{current}}}{P_{\text{current}}}$.
- **Option 3: Hybrid Objective**: Blended score (e.g., $w_{\text{div}} \cdot \text{Dividend Yield} + w_{\text{growth}} \cdot \text{Analyst Upside}$).

### C. Hard Constraints
1. **Single Stock Weight Limit**: No single asset can exceed $10\%$ of total portfolio value ($w_i \le 0.10$).
2. **Fully Invested / Capital Constraint**: Total weights sum to $100\%$ ($\sum w_i = 1.0$).
3. **Non-Negativity / Long-Only**: No short selling ($w_i \ge 0$).

---

## 3. Critical Critique & Analysis

### Strengths & Merits
- **Disciplined & Systematic**: Eliminates emotional bias by relying on quantitative optimization.
- **Enforced Diversification**: The $10\%$ position cap guarantees exposure across at least 10 different companies.
- **Dual-Factor Approach**: Balancing dividend yield with analyst price targets captures both cash flow and growth potential.

### Potential Risks & Blind Spots

1. **The "Yield Trap" Risk (High Dividend Hazard)**
   - Distressed companies often display artificially high dividend yields right before cutting payouts or experiencing stock collapses.
   - *Mitigation*: Filter out stocks with payout ratios $> 80-90\%$ or negative earnings before feeding them to the optimizer.

2. **Analyst Target Price Biases & Lag**
   - Analyst price targets are notoriously lagging indicators and often biased upward. Analysts tend to revise targets *after* prices fall.
   - *Mitigation*: Incorporate analyst consensus count (e.g., requires $\ge 5$ analysts) or use historical accuracy weighting.

3. **Ignore Asset Variance & Covariance (Risk/Vol Risk)**
   - Maximizing pure expected yield/upside with only a $10\%$ max weight cap will likely pick 10 highly correlated stocks (e.g., 10 REITs or 10 Bank stocks).
   - *Mitigation*: Introduce sector exposure caps (e.g., max $25\%$ per sector) or incorporate correlation/volatility matrices (Markowitz Mean-Variance / Sharpe Ratio optimization).

4. **Dividend Growth vs. Static Yield**
   - High current yield might come from a stagnant company, whereas a lower current yield company with high dividend growth rate (Dividend Aristocrats) often outperforms long-term.

---

## 4. Technical Implementation Outline (Future Step)

When ready to implement, this problem maps cleanly to **Linear Programming (LP)** or **Quadratic Programming (QP)**:

- **Tools/Libraries**: `scipy.optimize.linprog` or `cvxpy` in Python.
- **Mathematical Formulation**:
  $$\text{Maximize } \quad \mathbf{w}^T \mathbf{r}$$
  $$\text{Subject to } \quad \sum_{i=1}^N w_i = 1, \quad 0 \le w_i \le 0.10 \quad \forall i$$
  *(where $\mathbf{r}$ is the vector of expected yields/upsides and $\mathbf{w}$ is the weight vector).*

---

## 5. Next Steps for Experimentation

1. [ ] **Data Pipeline**: Build scripts to pull dividend histories & analyst targets from `yfinance`.
2. [ ] **Backtesting Framework**: Test historical portfolio performance vs benchmark (e.g., S&P 500 or SET High Dividend Index).
3. [ ] **Refine Constraints**: Add sector diversification and financial health filters (e.g., payout ratio filter).

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

### Strengths
- **Disciplined & Systematic**: Eliminates emotional bias by relying on quantitative rules.
- **Enforced Diversification**: The $10\%$ position cap guarantees exposure across at least 10 different companies.
- **Dual-Factor Approach**: Balancing dividend yield with analyst price targets captures both cash flow and growth potential.

### Problem 1: The Optimizer Produces a Trivial Solution

With only a $10\%$ max weight cap and no other competing constraints, the algorithm will simply:
1. Rank all stocks by expected yield/upside.
2. Assign $10\%$ to the top 10 stocks.
3. Assign $0\%$ to everything else.

**This is just sorting a list and picking the top 10.** You don't need `cvxpy` or any optimizer for that. Optimization only becomes meaningful when there are **competing constraints** that create trade-offs (sector caps, volatility budgets, turnover limits, minimum position sizes, etc.).

### Problem 2: Analyst Target Prices Are a Weak Signal

Academic research consistently shows analyst consensus targets have **low predictive power**. They tend to be:
- **Anchored** to recent prices (lagging, not leading).
- **Biased upward** (sell-side analysts have incentive to be bullish).
- **Herded** (analysts copy each other's targets).

Using analyst targets as the primary growth signal means building on a shaky foundation. *Mitigation*: Require minimum analyst coverage ($\ge 5$ analysts), or better yet, weight by historical accuracy of analyst predictions for each stock.

### Problem 3: No Concept of Risk

Maximizing pure expected return without penalizing risk is a recipe for a concentrated, volatile portfolio. Even with the $10\%$ cap, you could easily end up holding 10 highly correlated stocks (e.g., all energy or all REITs) that crash together.

*Mitigations*:
- **Sector exposure caps** (e.g., max $25\%$ per sector).
- **Volatility or drawdown constraints** (e.g., portfolio annualized vol $\le 15\%$).
- **Mean-Variance optimization** (maximize Sharpe Ratio instead of raw return) — this requires a covariance matrix but produces more robust portfolios.

### Problem 4: Dividend Yield Alone Is Dangerous ("Yield Trap")

A stock yielding $8\%$ might be about to cut its dividend. High yield often signals distress, not opportunity. You need safety filters **before** any optimization:
- Payout ratio $< 80\%$ (company retains enough earnings).
- Positive EPS (no loss-making companies).
- Dividend growth rate (is the company *growing* its dividend or *dying*?).
- Minimum consecutive years of dividend payment (e.g., $\ge 3$ years).

### Problem 5: No Rebalancing or Transaction Cost Model

How often do you rebalance? Monthly? Quarterly? Without modeling:
- **Transaction costs** (brokerage fees, bid-ask spread)
- **Tax implications** (capital gains on rebalancing)
- **Turnover rate** (how many trades per rebalance)

...the theoretical returns won't match reality. High-frequency rebalancing to chase yield changes will eat into returns.

---

## 4. Technical Implementation Outline (Future Step)

When ready to implement, this problem maps cleanly to **Linear Programming (LP)** or **Quadratic Programming (QP)**:

- **Tools/Libraries**: `scipy.optimize.linprog` or `cvxpy` in Python.
- **Mathematical Formulation**:
  $$\text{Maximize } \quad \mathbf{w}^T \mathbf{r}$$
  $$\text{Subject to } \quad \sum_{i=1}^N w_i = 1, \quad 0 \le w_i \le 0.10 \quad \forall i$$
  *(where $\mathbf{r}$ is the vector of expected yields/upsides and $\mathbf{w}$ is the weight vector).*

However, **don't jump to optimization first**. See the recommended approach below.

---

## 5. Recommended Approach (Phased)

### Phase 1: Simple Scoring Model (Start Here)
Rank stocks by a blended score, filtered by financial health:
```
score = 0.5 × dividend_yield + 0.5 × analyst_upside
```
Filter out: payout ratio > 80%, negative EPS, < 3 years dividend history.
Equal-weight the top N stocks. This is simpler, more transparent, and nearly as effective as a full optimizer.

### Phase 2: Backtest Before Optimizing
Pull 3–5 years of historical data and test whether this scoring model actually outperforms a benchmark (S&P 500, SET Index, or a dividend ETF). **If a simple scoring model can't beat the benchmark, adding an optimizer won't save it** — the signal itself is too weak.

### Phase 3: Add Optimization Only If Phase 2 Shows Promise
At this point, introduce `cvxpy` with meaningful constraints:
- Sector caps ($\le 25\%$ per sector)
- Volatility budget (portfolio vol $\le X\%$)
- Turnover limits (max $Y\%$ portfolio change per rebalance)

This makes the optimizer do real work instead of just sorting a list.

---

## 6. Next Steps

- [ ] **Data Pipeline**: Build scripts to pull dividend histories, payout ratios, & analyst targets from `yfinance`.
- [ ] **Scoring Model**: Implement Phase 1 blended scoring with financial health filters.
- [ ] **Backtesting**: Test historical portfolio performance vs benchmark over 3–5 years.
- [ ] **Optimization Layer**: Only if backtesting shows the signal has value, add `cvxpy` with sector/risk constraints.

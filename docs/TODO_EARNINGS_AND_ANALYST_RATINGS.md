# [TODO / TEMPORARY] Earnings & Analyst Ratings Tracking Specification

> [!WARNING]
> **Temporary Design Document**: This document outlines the schema, data extraction, and tracking logic for analyst consensus revisions and earnings forecast changes. 
> Once the feature implementation (database tables, sync pipeline, API endpoints, and UI views) is fully complete and merged, **this document should be deleted**.

---

## 1. Objectives

Track **temporal revisions** (changes over time) of institutional analyst price targets, recommendation ratings, and quarterly corporate earnings estimates to generate actionable buy/sell signals:
1. **Target Price Momentum**: Detect when consensus price targets are being revised upwards (bullish) or cut (bearish).
2. **Rating Migrations**: Track shifts in recommendation breakdown (e.g. upgrades from *Hold* to *Buy*).
3. **Earnings Estimate Revisions**: Track consensus EPS revisions leading up to quarterly reporting dates, and record actual earnings surprises.

---

## 2. Available Data from `yfinance.Ticker`

### A. Analyst Price Targets (`ticker.analyst_price_targets`)
Returns consensus target prices:
```python
{
    'current': 235.50,
    'low': 185.00,
    'high': 300.00,
    'mean': 246.30,
    'median': 248.00
}
```
* **Database mapping**: Matches the existing [`AnalystPriceTarget`](file:///home/tam/github/goose/backend/models.py#L168-L183) table in `backend/models.py` (`high`, `low`, `mean`, `median`, `date`).

---

### B. Recommendations & Ratings (`ticker.recommendations_summary`)
Returns analyst consensus rating distribution across historical months:
```python
# DataFrame columns:
# - period: '0m' (current), '-1m' (last month), '-2m', '-3m'
# - strongBuy: int
# - buy: int
# - hold: int
# - sell: int
# - strongSell: int
```
* **Derived Metrics**:
  * Consensus Score = $(5 \times \text{StrongBuy} + 4 \times \text{Buy} + 3 \times \text{Hold} + 2 \times \text{Sell} + 1 \times \text{StrongSell}) / \text{Total}$
  * Rating Change = Current Consensus Score $-$ Previous Week's Score.

---

### C. Earnings Estimates & Surprises (`ticker.earnings_dates`)
Returns historical and forward reporting dates with consensus EPS estimates and actual reported figures:
```python
# DataFrame columns:
# - Earnings Date: Timestamp
# - EPS Estimate: float | None (analyst consensus expectation)
# - Reported EPS: float | None (actual announced EPS)
# - Surprise(%): float | None (percentage beat or miss)
```

---

## 3. Implemented Database Schema Models

The models are defined in `backend/models.py` (pending migration):

```mermaid
erDiagram
    STOCK ||--o{ ANALYST_PRICE_TARGET : "records weekly targets & ratings"
    STOCK ||--o{ STOCK_EARNING : "records quarterly consensus expectations & results"
    STOCK ||--o{ STOCK_GUIDANCE : "records executive forward guidance ranges"

    ANALYST_PRICE_TARGET {
        int id PK
        int stock_id FK
        date date "Snapshot date"
        decimal target_high "High target"
        decimal target_low "Low target"
        decimal target_mean "Consensus mean"
        decimal target_median "Consensus median"
        int strong_buy "Strong buy count"
        int buy "Buy count"
        int hold "Hold count"
        int sell "Sell count"
        int strong_sell "Strong sell count"
        decimal consensus_score "Weighted 1.0 to 5.0"
    }

    STOCK_EARNING {
        int id PK
        int stock_id FK
        date report_date "Earnings announcement date"
        string fiscal_period "e.g. Q3 2026"
        decimal eps_estimate "Consensus forecasted EPS"
        decimal eps_reported "Actual announced EPS"
        decimal surprise_pct "EPS beat/miss %"
        decimal rev_estimate "Consensus forecasted Revenue"
        decimal rev_reported "Actual announced Revenue"
        decimal rev_surprise_pct "Revenue beat/miss %"
        string data_source "YFINANCE | MANUAL | AGENT"
        boolean is_verified "Lock against automated feed overwrite"
    }

    STOCK_GUIDANCE {
        int id PK
        int stock_id FK
        date issue_date "Guidance release date"
        string target_period "e.g. Q4 2026 or FY 2026"
        string period_type "QUARTER | FULL_YEAR"
        decimal rev_low "Revenue guidance low"
        decimal rev_high "Revenue guidance high"
        decimal rev_mid "Revenue guidance midpoint"
        decimal eps_low "EPS guidance low"
        decimal eps_high "EPS guidance high"
        decimal eps_mid "EPS guidance midpoint"
        string revision_type "INITIAL | RAISED | LOWERED | REAFFIRMED"
        string notes "Commentary & assumptions"
    }
```

---

## 4. Planned API Endpoints

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/stocks/{identifier}/targets` | Historical analyst price targets and latest revision delta |
| `GET` | `/api/v1/stocks/{identifier}/ratings` | Historical analyst recommendation breakdown & upgrades/downgrades |
| `GET` | `/api/v1/stocks/{identifier}/earnings` | Earnings calendar, revenue & EPS estimates, and surprise history |
| `POST` | `/api/v1/stocks/{identifier}/earnings` | Manual / Agent entry/verification of earnings actuals and revenue |
| `GET` | `/api/v1/stocks/{identifier}/guidance` | Retrieve management guidance history and track record |
| `POST` | `/api/v1/stocks/{identifier}/guidance` | Manual / Agent / MCP entry of executive guidance ranges |
| `POST` | `/api/v1/stocks/sync/fundamentals` | Trigger weekly batch refresh of fundamentals & analyst data |

---

## 5. Deletion Checklist

Before deleting this file, ensure:
- [ ] Database migration generated and applied for `StockGuidance` and updated `StockEarning`.
- [ ] Weekly synchronization worker implemented in `backend/app/services/`.
- [ ] API routes implemented under `/api/v1/stocks/...`.
- [ ] Web client displays target momentum, upcoming earnings dates, and guidance tracker.
- [ ] Permanent architecture notes migrated into `DATABASE_DESIGN.md` and `API_DESIGN.md`.
- [ ] Web client displays target momentum and upcoming earnings dates.
- [ ] Permanent architecture notes migrated into `DATABASE_DESIGN.md` and `API_DESIGN.md`.

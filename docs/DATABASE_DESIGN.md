# Database & API Design Specification: Goose

This document details the database schema, relational structure, design rationale, and the preliminary REST API contract for the **Goose** multi-client financial application.

---

## 1. Architectural Strategy: Database vs. API Schemas

In accordance with our multi-client architecture:
* **Database Models (`backend/models.py`)**: Defined via **SQLModel** (`table=True`). Owned strictly by the backend to manage SQLite persistence, indexing, migrations (Alembic), and relational integrity.
* **API Schemas (`shared/schemas/`)**: Defined via **Pydantic** (`BaseModel`). Shared across the backend, Python TUI, and serving as the blueprint for Angular TypeScript interfaces (`.ts`).
* **Clients never connect directly to the database**. All client interaction flows through the FastAPI REST server.

---

## 2. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    STOCK ||--o{ STOCK_PRICE : "has daily historical prices"
    STOCK ||--o{ STOCK_DIVIDEND : "has dividend cash payouts"
    STOCK ||--o{ ANALYST_PRICE_TARGET : "has consensus price targets"

    STOCK {
        int id PK
        string ticker "Local symbol (e.g. AAPL, PTT, A)"
        string yf_ticker UK "Yahoo Finance symbol (e.g. AAPL, PTT.BK, A.BK)"
        string name "Company legal name"
        string country "USA | THAILAND"
        string exchange "NASDAQ | NYSE | SET"
        string currency "USD | THB"
        string sector "GICS Sector (e.g. Technology, Energy)"
        string industry "GICS Industry (e.g. Consumer Electronics)"
        boolean is_active "Tracking status"
        datetime created_at "Registration timestamp"
    }

    STOCK_PRICE {
        int id PK
        int stock_id FK
        date date "Trading date"
        decimal open "Opening price"
        decimal high "Daily high"
        decimal low "Daily low"
        decimal close "Raw unadjusted closing price"
        decimal adj_close "Split & dividend adjusted close"
        int volume "Traded share volume"
    }

    STOCK_DIVIDEND {
        int id PK
        int stock_id FK
        date ex_date "Ex-dividend cutoff date"
        date payment_date "Cash distribution date"
        date record_date "Corporate record date"
        decimal amount "Cash dividend payout per share"
        string currency "Payout currency (e.g. USD, THB)"
    }

    ANALYST_PRICE_TARGET {
        int id PK
        int stock_id FK
        date date "Publish/recorded date"
        decimal high "Analyst target high"
        decimal low "Analyst target low"
        decimal mean "Analyst consensus mean"
        decimal median "Analyst consensus median"
    }
```

---

## 3. Database Schema Definitions

### A. `Stock` Table
The master registry of tracked companies across US and international markets.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing internal identifier. |
| `ticker` | `VARCHAR(10)` | `INDEX` | Local market symbol (e.g., `AAPL`, `PTT`, `A`). |
| `country` | `VARCHAR(20)` | `DEFAULT 'USA'` | Country of primary listing (`USA`, `THAILAND`). |
| `yf_ticker` | `VARCHAR(20)` | `UNIQUE, INDEX` | Globally unique Yahoo Finance symbol (`AAPL`, `PTT.BK`, `A.BK`). |
| `name` | `VARCHAR(255)` | `NOT NULL` | Full corporate name. |
| `exchange` | `VARCHAR(50)` | `NULLABLE` | Listing exchange (`NASDAQ`, `NYSE`, `SET`). |
| `currency` | `VARCHAR(10)` | `DEFAULT 'USD'` | Currency for pricing and cash flows (`USD`, `THB`). |
| `sector` | `VARCHAR(100)` | `NULLABLE` | GICS economic sector (used for portfolio sector caps). |
| `industry` | `VARCHAR(100)` | `NULLABLE` | GICS industry classification. |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Allows pausing price syncs without deleting historical data. |
| `created_at` | `DATETIME` | `DEFAULT UTC` | Audit timestamp. |

* **Table Constraints**:
  * `UNIQUE (ticker, country)`: Prevents duplicate tickers within the same market, while permitting the same symbol across different countries (e.g., `A` in US vs. `A` in Thailand).
  * `UNIQUE (yf_ticker)`: Guarantees external data sync integrity.

---

### B. `StockPrice` Table
Daily time-series records of price action and market liquidity.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-incrementing record ID. |
| `stock_id` | `INTEGER` | `FOREIGN KEY (stock.id)` | Link to parent company. |
| `date` | `DATE` | `INDEX` | Market trading session date. |
| `open` | `NUMERIC(10, 2)` | `NOT NULL` | Daily opening price. |
| `high` | `NUMERIC(10, 2)` | `NOT NULL` | Session high. |
| `low` | `NUMERIC(10, 2)` | `NOT NULL` | Session low. |
| `close` | `NUMERIC(10, 2)` | `NOT NULL` | Raw unadjusted closing price. |
| `adj_close` | `NUMERIC(10, 2)` | `NOT NULL` | Split- and dividend-adjusted closing price. |
| `volume` | `BIGINT` | `DEFAULT 0` | Total traded shares in session. |

* **Table Constraints & Indexes**:
  * `UNIQUE (stock_id, date)`: Enforces idempotency; prevents duplicate rows during re-runs of historical backfills.
  * `INDEX (stock_id, date)`: Optimizes range scans and latest-price lookups.

---

### C. `StockDividend` Table
Discrete corporate cash dividend distributions.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY` | Record ID. |
| `stock_id` | `INTEGER` | `FOREIGN KEY (stock.id)` | Link to parent company. |
| `ex_date` | `DATE` | `INDEX` | Cutoff date for dividend entitlement. |
| `payment_date` | `DATE` | `NULLABLE` | Date cash was distributed to shareholders. |
| `record_date` | `DATE` | `NULLABLE` | Corporate book-close date. |
| `amount` | `NUMERIC(10, 2)` | `NOT NULL` | Cash amount per share. |
| `currency` | `VARCHAR(10)` | `DEFAULT 'USD'` | Dividend currency. |

* **Table Constraints & Indexes**:
  * `UNIQUE (stock_id, ex_date)`: Guarantees each dividend event is recorded only once per stock.
  * `INDEX (stock_id, ex_date)`: Accelerates multi-year dividend growth and payout ratio calculations.

---

## 4. Key Design Decisions & Trade-Offs

1. **Why `(ticker, country)` Compound Uniqueness?**
   * Multi-market tracking introduces symbol collision (e.g., ticker `A` is *Agilent Technologies* in the US, but *Areeya Property* in Thailand).
   * Combining `(ticker, country)` allows human users to read simple symbols (`A`) while guaranteeing database integrity.
   * `yf_ticker` remains globally unique (`A` vs `A.BK`) and is used as the external synchronization key.

2. **Why a Dedicated `StockDividend` Table?**
   * Dividends occur 1 to 4 times a year, whereas prices occur ~252 trading days a year.
   * Merging dividend columns into daily prices wastes space and complicates corporate actions (e.g., special dividends, payment dates vs. ex-dates).
   * A separate table makes calculating consecutive years of dividend growth, dividend safety, and yield history straightforward and performant.

3. **Why `adj_close` alongside `close`?**
   * Raw `close` is necessary for reflecting exact historical trading quotes.
   * `adj_close` adjusts backwards for stock splits (e.g., 2-for-1 or 10-for-1 splits) and dividend distributions. Without `adj_close`, historical return calculations and technical indicators produce false drops.

---

## 5. Preliminary REST API Design

All endpoints are hosted under `/api/v1` and return JSON.

### Endpoints Overview

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/stocks` | List all tracked stocks with current prices & performance metrics. |
| `POST` | `/api/v1/stocks` | Register a new stock to the watchlist. |
| `GET` | `/api/v1/stocks/{yf_ticker}` | Retrieve details for a single stock by `yf_ticker` (e.g. `AAPL`, `PTT.BK`). |
| `GET` | `/api/v1/stocks/{yf_ticker}/prices` | *(Draft)* Retrieve historical daily OHLCV prices with date range filtering. |
| `GET` | `/api/v1/stocks/{yf_ticker}/dividends` | *(Draft)* Retrieve historical dividend distributions for a stock. |

---

### Request / Response Schemas

#### `POST /api/v1/stocks` (Create Stock)
**Request Body**:
```json
{
  "ticker": "PTT",
  "name": "PTT Public Company Limited",
  "yf_ticker": "PTT.BK",
  "country": "THAILAND",
  "exchange": "SET",
  "currency": "THB",
  "sector": "Energy",
  "industry": "Oil & Gas Integrated",
  "is_active": true
}
```

**Response (201 Created)**:
```json
{
  "id": 1,
  "ticker": "PTT",
  "name": "PTT Public Company Limited",
  "yf_ticker": "PTT.BK",
  "country": "THAILAND",
  "exchange": "SET",
  "currency": "THB",
  "sector": "Energy",
  "industry": "Oil & Gas Integrated",
  "is_active": true,
  "created_at": "2026-10-22T14:20:00Z",
  "price": 32.50,
  "change": {
    "week": 1.25,
    "month": -0.80,
    "quarter": 4.50,
    "year": 8.20
  },
  "earning": null
}
```

#### `GET /api/v1/stocks/{yf_ticker}/prices` *(Draft for Next Phase)*
Query parameters: `?start_date=2026-01-01&end_date=2026-10-22`
```json
[
  {
    "date": "2026-10-22",
    "open": "32.00",
    "high": "32.75",
    "low": "31.75",
    "close": "32.50",
    "adj_close": "32.50",
    "volume": 45120300
  }
]
```

#### `GET /api/v1/stocks/{yf_ticker}/dividends` *(Draft for Next Phase)*
```json
[
  {
    "id": 10,
    "stock_id": 1,
    "ex_date": "2026-09-04",
    "payment_date": "2026-09-20",
    "record_date": "2026-09-05",
    "amount": "0.80",
    "currency": "THB"
  }
]
```

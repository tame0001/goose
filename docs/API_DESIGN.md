# REST API Specification: Goose

This document defines the REST API contract for the **Goose** platform. The API serves as the single source of truth for all client applications, including the Textual Terminal UI (`tui/`) and the upcoming Angular Web App (`web/`).

---

## 1. Architectural Principles

1. **API-First Decoupling**: Clients never access the database directly. All read and write operations flow through FastAPI endpoints under `/api/v1`.
2. **Shared Contract (`goose-shared`)**: All request and response structures are defined via Pydantic models in [`shared/shared/schemas/`](file:///home/tam/github/goose/shared/shared/schemas). Python clients (TUI) import these models directly; web clients mirror them as TypeScript interfaces.
3. **Identifier Flexibility**: Stock lookup endpoints accept either the Yahoo Finance ticker (`yf_ticker`, e.g., `PTT.BK`, `AAPL`) or the local market ticker (`ticker`, e.g., `PTT`, `AAPL`) with automatic uppercase normalization.
4. **Automated Onboarding**: Adding a stock immediately triggers a 1-year historical backfill of daily OHLCV prices and cash dividend events before returning.
5. **Settled History vs. Intraday Quotes**: The `stock_price` table strictly stores finalized, settled OHLCV daily bars after the market close. If a sync is executed while a market is actively trading, the partial intraday candle is excluded from `stock_price`; only `Stock.latest_price` and `Stock.latest_price_update_at` are refreshed.

---

## 2. Global Conventions

* **Base URL**: `http://localhost:8000/api/v1`
* **Content-Type**: `application/json`
* **Date Format**: ISO 8601 extended calendar date (`YYYY-MM-DD`).
* **Timestamp Format**: ISO 8601 UTC string (`YYYY-MM-DDTHH:MM:SSZ`).
* **Price / Monetary Values**: Serialized as numbers or exact 2-decimal strings to preserve financial precision.
* **Error Response Format**: Standard FastAPI error structure:
  ```json
  {
    "detail": "Error message describing the issue"
  }
  ```

---

## 3. Endpoints Summary

| Method | Path | Summary | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/stocks` | List all tracked stocks with latest cached price & changes | `list[StockResponse]` |
| `POST` | `/api/v1/stocks` | Register a new stock (triggers 1-yr historical backfill) | `StockResponse` (201) |
| `GET` | `/api/v1/stocks/{identifier}` | Retrieve single stock details by symbol | `StockResponse` |
| `POST` | `/api/v1/stocks/sync` | Incrementally sync daily prices & dividends | `StockSyncSummary` |
| `GET` | `/api/v1/stocks/{identifier}/prices` | Retrieve daily historical OHLCV prices | `list[StockPriceResponse]` |
| `GET` | `/api/v1/stocks/{identifier}/dividends` | Retrieve discrete cash dividend payouts | `list[StockDividendResponse]` |

---

## 4. Endpoint Specifications

### A. List Tracked Stocks
* **Route**: `GET /api/v1/stocks`
* **Description**: Returns all registered stocks in the watchlist, including current market price, performance percentage changes over trailing intervals (week, month, quarter, year), and fundamental tags.
* **Status Codes**:
  * `200 OK`: Success.

**Example Response**:
```json
[
  {
    "id": 1,
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "yf_ticker": "AAPL",
    "country": "USA",
    "exchange": "NASDAQ",
    "currency": "USD",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "is_active": true,
    "created_at": "2026-10-22T14:00:00Z",
    "latest_price": "235.50",
    "latest_price_update_at": "2026-10-22T14:05:00Z",
    "change": {
      "week": 1.25,
      "month": -0.80,
      "quarter": 4.50,
      "year": 18.20
    },
    "earning": null
  }
]
```

---

### B. Add New Stock
* **Route**: `POST /api/v1/stocks`
* **Description**: Adds a new stock to tracking. Validates uniqueness across `yf_ticker` and `(ticker, country)`. Automatically performs a 1-year historical data backfill (daily OHLCV prices + dividend payouts) via Yahoo Finance before returning the populated entity.
* **Status Codes**:
  * `201 Created`: Stock successfully added and history backfilled.
  * `400 Bad Request`: `yf_ticker` or `(ticker, country)` already registered.
  * `422 Unprocessable Entity`: Validation error on request body.

**Request Body** (`StockCreateRequest`):
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

**Example Response** (`StockResponse`, 201 Created):
```json
{
  "id": 2,
  "ticker": "PTT",
  "name": "PTT Public Company Limited",
  "yf_ticker": "PTT.BK",
  "country": "THAILAND",
  "exchange": "SET",
  "currency": "THB",
  "sector": "Energy",
  "industry": "Oil & Gas Integrated",
  "is_active": true,
  "created_at": "2026-10-22T15:30:00Z",
  "latest_price": "32.50",
  "latest_price_update_at": "2026-10-22T15:30:02Z",
  "change": {
    "week": 0.50,
    "month": 2.10,
    "quarter": -1.20,
    "year": 5.40
  },
  "earning": null
}
```

---

### C. Get Stock Details
* **Route**: `GET /api/v1/stocks/{identifier}`
* **Path Parameters**:
  * `identifier` (`str`): The Yahoo Finance ticker (`PTT.BK`) or local symbol (`PTT`).
* **Description**: Fetches the company details, latest cached price, and trailing performance metrics for a single stock.
* **Status Codes**:
  * `200 OK`: Stock found.
  * `404 Not Found`: No stock matches the provided symbol.

---

### D. Sync Daily Prices & Dividends (Incremental)
* **Route**: `POST /api/v1/stocks/sync`
* **Query Parameters**:
  * `yf_ticker` (`str`, optional): Sync only this specific stock. If omitted, syncs all active stocks.
* **Description**: Routine incremental batch synchronization.
  * Checks the latest recorded price date for each active stock against market close.
  * Stocks already up to date are **skipped with 0 API calls**.
  * Out-of-date stocks are grouped by market/date (e.g., Thai batch and US batch) and fetched in a single multi-ticker call using `yf.download(tickers=[...], actions=True)`.
  * Data is extracted via fast vectorized array operations and committed into SQLite.
* **Status Codes**:
  * `200 OK`: Sync completed.
  * `404 Not Found`: Specific `yf_ticker` not found.

**Example Response** (`StockSyncSummary`):
```json
{
  "message": "Incremental sync completed: 2 updated, 1 skipped, 0 errors",
  "total_checked": 3,
  "updated_count": 2,
  "skipped_count": 1,
  "error_count": 0,
  "results": [
    {
      "yf_ticker": "AAPL",
      "status": "updated",
      "records_added": 1,
      "dividends_added": 0,
      "message": "Fetched 1 day(s) from 2026-10-21"
    },
    {
      "yf_ticker": "MSFT",
      "status": "skipped",
      "records_added": 0,
      "dividends_added": 0,
      "message": "Already up to date (latest: 2026-10-22)"
    },
    {
      "yf_ticker": "PTT.BK",
      "status": "updated",
      "records_added": 1,
      "dividends_added": 0,
      "message": "Fetched 1 day(s) from 2026-10-21"
    }
  ]
}
```

---

### E. Get Historical Prices (OHLCV)
* **Route**: `GET /api/v1/stocks/{identifier}/prices`
* **Path Parameters**:
  * `identifier` (`str`): Yahoo Finance symbol (`AAPL`) or local symbol.
* **Query Parameters**:
  * `start_date` (`date`, optional): Filter records on or after this date (`YYYY-MM-DD`).
  * `end_date` (`date`, optional): Filter records on or before this date (`YYYY-MM-DD`).
* **Description**: Returns daily trading session records sorted descending by date.
* **Status Codes**:
  * `200 OK`: Success.
  * `404 Not Found`: Stock not found.

**Example Response** (`list[StockPriceResponse]`):
```json
[
  {
    "date": "2026-10-22",
    "open": "234.10",
    "high": "236.00",
    "low": "233.50",
    "close": "235.50",
    "adj_close": "235.50",
    "volume": 48201500
  },
  {
    "date": "2026-10-21",
    "open": "232.00",
    "high": "234.50",
    "low": "231.80",
    "close": "233.80",
    "adj_close": "233.80",
    "volume": 41205300
  }
]
```

---

### F. Get Dividend Payouts
* **Route**: `GET /api/v1/stocks/{identifier}/dividends`
* **Path Parameters**:
  * `identifier` (`str`): Stock symbol.
* **Description**: Returns all recorded historical cash dividend events sorted descending by `ex_date`.
* **Status Codes**:
  * `200 OK`: Success.
  * `404 Not Found`: Stock not found.

**Example Response** (`list[StockDividendResponse]`):
```json
[
  {
    "id": 15,
    "stock_id": 2,
    "ex_date": "2026-09-04",
    "payment_date": "2026-09-20",
    "record_date": "2026-09-05",
    "amount": "0.80",
    "currency": "THB"
  }
]
```

---

## 5. Schema Reference

All request and response models are maintained in the [`shared/shared/schemas/`](file:///home/tam/github/goose/shared/shared/schemas) package:

```
shared/shared/schemas/
├── stock.py       # StockBaseSchema, StockCreateRequest, StockResponse
├── price.py       # StockPriceResponse, StockChangeResponse, StockEarningResponse
├── dividend.py    # StockDividendResponse, StockDividendCreate
└── sync.py        # StockSyncResult, StockSyncSummary
```

---

## 6. Planned Future Endpoints

The following endpoints are scheduled for subsequent implementation phases:

1. **Portfolio Optimization (`/api/v1/portfolio`)**:
   * `POST /api/v1/portfolio/optimize`: Execute dividend yield and upside potential mathematical weighting models.
2. **Analyst Price Targets (`/api/v1/stocks/{identifier}/targets`)**:
   * `GET /api/v1/stocks/{identifier}/targets`: Retrieve high/mean/low consensus price targets.
3. **Dividend Analytics (`/api/v1/stocks/{identifier}/dividends/summary`)**:
   * Trailing 12-month yield, 5-year compound annual dividend growth rate (CAGR), and payout frequency.

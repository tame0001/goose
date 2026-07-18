# Backend Code Review — Goose

## 🔴 Critical Issues

### 1. No Error Handling on Price Lookups — `ZeroDivisionError`
In [data.py L72–75](file:///home/tam/github/goose/backend/utils/data.py#L72-L75), if any historical price returns `None` (e.g., stock was recently added, no data 365 days ago), `float(None)` raises `TypeError`, or a `0.0` price causes `ZeroDivisionError`:

```python
changes.week = (price_current - price_last_week) / price_last_week * 100  # 💥
```

> [!WARNING]
> **Fix:** Guard against `None` returns and zero-value prices before computing changes.

---

## 🟡 Architectural Issues

### 2. N+1 Query Problem
[read_stock_list](file:///home/tam/github/goose/backend/utils/data.py#L18-L36) iterates over every stock and:
1. Calls `update_stock_price(stock)` → multiple DB queries + possible yfinance API call
2. Calls `calculate_stock_changes(stock)` → 5–6 more DB queries

For 8 stocks, this is **easily 50+ DB queries** plus network calls, all sequentially. Your TODOs on lines 24–27 already acknowledge this.

> [!IMPORTANT]
> **Quick win:** Use a single session for the whole `read_stock_list` flow and batch the price lookups with a window function, as your TODO suggests.

## 🟢 Minor / Quality-of-Life

### 3. FastAPI App Has No Routes Beyond "Hello World"
[main.py](file:///home/tam/github/goose/backend/main.py) only has a root endpoint returning `{"message": "Hello World"}`. The actual functionality is all in the TUI path. If FastAPI is intended to serve data, consider adding stock endpoints; otherwise, you could drop it to simplify.

### 4. `fetch_real_time_price` TODO
[yfinance.py L28](file:///home/tam/github/goose/backend/utils/yfinance.py#L28) notes `fast_info.last_price` should be used instead of `info.currentPrice`. `fast_info` is significantly faster since it avoids the full `info` API call.

---

## Summary — Prioritized Action Items

| Priority | Issue | Effort |
|----------|-------|--------|
| 🔴 P0 | Add null/zero guards for price change calculations | Small |
| 🟡 P1 | Batch price queries (N+1 problem) | Medium |
| 🟢 P2 | Use `fast_info.last_price` | Small |

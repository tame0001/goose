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

### 2. Model Methods Require External Sessions — Awkward API
[Stock.get_latest_price_date](file:///home/tam/github/goose/backend/models.py#L25-L31) and [Stock.get_close_price_on_date](file:///home/tam/github/goose/backend/models.py#L33-L40) require a `Session` argument. Consider making these standalone query functions if the pattern becomes unwieldy.

### 3. N+1 Query Problem
[read_stock_list](file:///home/tam/github/goose/backend/utils/data.py#L18-L36) iterates over every stock and:
1. Calls `update_stock_price(stock)` → multiple DB queries + possible yfinance API call
2. Calls `calculate_stock_changes(stock)` → 5–6 more DB queries

For 8 stocks, this is **easily 50+ DB queries** plus network calls, all sequentially. Your TODOs on lines 24–27 already acknowledge this.

> [!IMPORTANT]
> **Quick win:** Use a single session for the whole `read_stock_list` flow and batch the price lookups with a window function, as your TODO suggests.

### 4. `stock-list.yml` is Unused
[stock-list.yml](file:///home/tam/github/goose/backend/utils/stock-list.yml) exists but is never read by any code. The stocks come from the database now. Either remove it or use it as a seed file.

### 5. `etf.py` is an Empty Placeholder
[etf.py](file:///home/tam/github/goose/backend/utils/etf.py) has only TODO comments. Either implement it or remove it from the repo to reduce clutter.

---

## 🟢 Minor / Quality-of-Life

### 6. Ruff `target-version` Mismatch
[ruff.toml](file:///home/tam/github/goose/backend/ruff.toml#L37) targets `py310`, but [pyproject.toml](file:///home/tam/github/goose/backend/pyproject.toml#L6) requires `>=3.12`. They should match (`py312`).

### 7. FastAPI App Has No Routes Beyond "Hello World"
[main.py](file:///home/tam/github/goose/backend/main.py) only has a root endpoint returning `{"message": "Hello World"}`. The actual functionality is all in the TUI path. If FastAPI is intended to serve data, consider adding stock endpoints; otherwise, you could drop it to simplify.

### 8. `calculate_stock_earnings` References a Non-Existent Attribute
[yfinance.py L39](file:///home/tam/github/goose/backend/utils/yfinance.py#L39) accesses `stock.yf_data.info`, but `StockData` has no `yf_data` attribute. This function would crash if called.

### 9. `fetch_real_time_price` TODO
[yfinance.py L28](file:///home/tam/github/goose/backend/utils/yfinance.py#L28) notes `fast_info.last_price` should be used instead of `info.currentPrice`. `fast_info` is significantly faster since it avoids the full `info` API call.

### 10. Missing `__init__.py` Typing / Imports
Both [backend/\_\_init\_\_.py](file:///home/tam/github/goose/backend/__init__.py) and [utils/\_\_init\_\_.py](file:///home/tam/github/goose/backend/utils/__init__.py) are empty, which is fine, but consider adding `__all__` exports if the package grows.

### 11. Shell Script Uses Hardcoded Path
[goose.sh](file:///home/tam/github/goose/backend/goose.sh#L4) hardcodes `$HOME/github/goose/backend`. Using `"$(dirname "$0")"` would make it portable.

---

## Summary — Prioritized Action Items

| Priority | Issue | Effort |
|----------|-------|--------|
| 🔴 P0 | Add null/zero guards for price change calculations | Small |
| 🟡 P1 | Fix broken `calculate_stock_earnings` (dead `yf_data` attr) | Small |
| 🟡 P1 | Fix ruff `target-version` → `py312` | Trivial |
| 🟡 P1 | Batch price queries (N+1 problem) | Medium |
| 🟢 P2 | Use `fast_info.last_price` | Small |
| 🟢 P2 | Remove dead files (`etf.py`, `stock-list.yml`) or implement them | Trivial |
| 🟢 P2 | Make `goose.sh` portable | Trivial |

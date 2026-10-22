import datetime

from pydantic import BaseModel


class StockSyncResult(BaseModel):
    yf_ticker: str
    status: str  # "updated", "skipped", "error"
    new_price_records: int = 0
    new_dividend_records: int = 0
    latest_date: datetime.date | None = None
    reason: str | None = None


class StockSyncSummary(BaseModel):
    message: str
    total_checked: int
    updated_count: int
    skipped_count: int
    error_count: int = 0
    results: list[StockSyncResult]

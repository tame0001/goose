from pydantic.dataclasses import dataclass


@dataclass
class StockChange:
    week: float | None = None
    month: float | None = None
    quarter: float | None = None
    year: float | None = None


@dataclass
class StockEarning:
    # Trailing Twelve Months Earnings Per Share
    eps_ttm: float | None = None
    # Forecast Earnings Per Share
    eps_forecast: float | None = None


@dataclass
class StockData:
    ticker: str
    yf_ticker: str | None = None
    price: float | None = None
    change: StockChange | None = None
    earning: StockEarning | None = None

import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class StockPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: datetime.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


class StockChangeResponse(BaseModel):
    week: float | None = None
    month: float | None = None
    quarter: float | None = None
    year: float | None = None


class StockEarningResponse(BaseModel):
    eps_ttm: float | None = None
    eps_forecast: float | None = None

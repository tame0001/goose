import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StockDividendBase(BaseModel):
    ex_date: datetime.date
    payment_date: datetime.date | None = None
    record_date: datetime.date | None = None
    amount: Decimal
    currency: str = "USD"


class StockDividendCreate(StockDividendBase):
    pass


class StockDividendResponse(StockDividendBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_id: int

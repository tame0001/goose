import datetime

from pydantic import BaseModel, ConfigDict

from shared.schemas.price import StockChangeResponse, StockEarningResponse


class StockBaseSchema(BaseModel):
    ticker: str
    name: str
    yf_ticker: str
    country: str = "USA"
    exchange: str | None = None
    currency: str = "USD"
    sector: str | None = None
    industry: str | None = None
    is_active: bool = True


class StockCreateRequest(StockBaseSchema):
    pass


class StockResponse(StockBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime | None = None
    price: float | None = None
    change: StockChangeResponse | None = None
    earning: StockEarningResponse | None = None

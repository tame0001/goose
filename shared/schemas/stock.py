from pydantic import BaseModel, ConfigDict
from shared.schemas.price import StockChangeResponse, StockEarningResponse


class StockBaseSchema(BaseModel):
    ticker: str
    name: str
    yf_ticker: str | None = None


class StockCreateRequest(StockBaseSchema):
    pass


class StockResponse(StockBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price: float | None = None
    change: StockChangeResponse | None = None
    earning: StockEarningResponse | None = None

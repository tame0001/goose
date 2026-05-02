from sqlmodel import SQLModel, Field


class StockBase(SQLModel):
    ticker: str
    name: str
    yf_ticker: str | None = None


class Stock(StockBase, table=True):
    id: int = Field(default=None, primary_key=True)

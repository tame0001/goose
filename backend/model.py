from sqlmodel import SQLModel, Field


class Exchange(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    country: str


class StockBase(SQLModel):
    ticker: str
    name: str
    # Foreign key
    exchange_id: int = Field(default=None, foreign_key="exchange.id")


class Stock(StockBase, table=True):
    id: int = Field(default=None, primary_key=True)

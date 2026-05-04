import datetime
from decimal import Decimal
from sqlmodel import Relationship, SQLModel, Field


class StockBase(SQLModel):
    ticker: str
    name: str
    yf_ticker: str | None = None


class Stock(StockBase, table=True):
    id: int = Field(default=None, primary_key=True)
    # Reference to StockPrice
    prices: list["StockPrice"] = Relationship(back_populates="stock")
    # Reference to AnalystPriceTarget
    analyst_targets: list["AnalystPriceTarget"] = Relationship(back_populates="stock")


class StockPriceBase(SQLModel):
    date: datetime.date
    # Foreign key to Stock
    stock_id: int = Field(foreign_key="stock.id")
    open: Decimal = Field(decimal_places=2)
    high: Decimal = Field(decimal_places=2)
    low: Decimal = Field(decimal_places=2)
    close: Decimal = Field(decimal_places=2)


class StockPrice(StockPriceBase, table=True):
    id: int = Field(default=None, primary_key=True)
    # References to Stock
    stock: Stock | None = Relationship(back_populates="prices")


class AnalystPriceTargetBase(SQLModel):
    """Currently use information from yfinance"""

    date: datetime.date
    # Foreign key to Stock
    stock_id: int = Field(foreign_key="stock.id")
    high: Decimal = Field(decimal_places=2)
    low: Decimal = Field(decimal_places=2)
    mean: Decimal = Field(decimal_places=2)
    median: Decimal = Field(decimal_places=2)


class AnalystPriceTarget(AnalystPriceTargetBase, table=True):
    id: int = Field(default=None, primary_key=True)
    # References to Stock
    stock: Stock | None = Relationship(back_populates="analyst_targets")

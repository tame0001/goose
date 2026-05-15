import datetime
from decimal import Decimal
from sqlmodel import Relationship, SQLModel, Field, Session, select


# TODO: Add field to show 1) industry and sector based of yfinance API,
# 2) products and services,
# 3) direct competitors (foreign key to Stock table),
# 4) supply chain companies (foreign key to Stock table)
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

    def get_latest_price_date(self, session: Session) -> datetime.date:
        """Get the latest price date of the stock from the database."""
        return session.exec(
            select(StockPrice.date)
            .where(StockPrice.stock_id == self.id)
            .order_by(StockPrice.date.desc())
        ).first()

    def get_close_price_on_date(self, session: Session, date: datetime.date) -> float:
        """Get the stock's closing price on a specific date from the database."""
        return session.exec(
            select(StockPrice.close)
            .where(StockPrice.stock_id == self.id)
            .where(StockPrice.date <= date)
            .order_by(StockPrice.date.desc())
        ).first()


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


# TODO: Add ESP with option to indicate whether if it is actual or estimated + annual or quarterly.

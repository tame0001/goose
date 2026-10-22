import datetime
from decimal import Decimal
from sqlmodel import Field, Index, Relationship, SQLModel, Session, UniqueConstraint, select


# TODO: Add field to show 
# 1) industry and sector based of yfinance API,
# 2) products and services,
# 3) direct competitors (foreign key to Stock table),
# 4) supply chain companies (foreign key to Stock table)
class StockBase(SQLModel):
    """Base fields for a Stock entity representing a tracked company."""

    ticker: str = Field(
        index=True,
        max_length=10,
        description="Local market ticker symbol (e.g. AAPL, PTT, A)",
    )
    name: str = Field(
        max_length=255,
        description="Full company name",
    )
    yf_ticker: str = Field(
        unique=True,
        index=True,
        max_length=20,
        description="Globally unique Yahoo Finance ticker (e.g. AAPL, PTT.BK, A.BK)",
    )
    country: str = Field(
        default="USA",
        max_length=20,
        description="Country of primary listing (e.g. USA, THAILAND)",
    )
    exchange: str | None = Field(
        default=None,
        max_length=50,
        description="Stock exchange (e.g. NASDAQ, NYSE, SET)",
    )
    currency: str = Field(
        default="USD",
        max_length=10,
        description="Currency for pricing and dividend distributions (e.g. USD, THB)",
    )
    sector: str | None = Field(
        default=None,
        max_length=100,
        description="GICS sector (e.g. Technology, Energy, Financial Services)",
    )
    industry: str | None = Field(
        default=None,
        max_length=100,
        description="GICS industry (e.g. Consumer Electronics, Oil & Gas)",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this stock is actively tracked and updated",
    )


class Stock(StockBase, table=True):
    """Stock database table storing tracked companies."""

    __table_args__ = (
        UniqueConstraint("ticker", "country", name="uq_stock_ticker_country"),
    )

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        description="Timestamp when stock was added to database",
    )

    # Relationships to time-series children
    prices: list["StockPrice"] = Relationship(back_populates="stock")
    dividends: list["StockDividend"] = Relationship(back_populates="stock")
    analyst_targets: list["AnalystPriceTarget"] = Relationship(back_populates="stock")


class StockPriceBase(SQLModel):
    """Daily OHLCV price bar."""

    date: datetime.date = Field(
        index=True,
        description="Market trading date",
    )
    stock_id: int = Field(
        foreign_key="stock.id",
        description="Reference to parent Stock",
    )
    open: Decimal = Field(decimal_places=2, description="Opening price")
    high: Decimal = Field(decimal_places=2, description="Daily high price")
    low: Decimal = Field(decimal_places=2, description="Daily low price")
    close: Decimal = Field(decimal_places=2, description="Raw unadjusted closing price")
    adj_close: Decimal = Field(
        decimal_places=2,
        description="Adjusted closing price accounting for splits and dividend distributions",
    )
    volume: int = Field(
        default=0,
        description="Total traded share volume",
    )


class StockPrice(StockPriceBase, table=True):
    """Daily historical price records table."""

    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_stock_price_stock_date"),
        Index("ix_stock_price_stock_date", "stock_id", "date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="prices")


class StockDividendBase(SQLModel):
    """Cash dividend distribution event."""

    stock_id: int = Field(
        foreign_key="stock.id",
        description="Reference to parent Stock",
    )
    ex_date: datetime.date = Field(
        index=True,
        description="Ex-dividend date (cutoff eligibility date)",
    )
    payment_date: datetime.date | None = Field(
        default=None,
        description="Actual cash payment distribution date",
    )
    record_date: datetime.date | None = Field(
        default=None,
        description="Company record date",
    )
    amount: Decimal = Field(
        decimal_places=2,
        description="Cash dividend payout amount per share",
    )
    currency: str = Field(
        default="USD",
        max_length=10,
        description="Currency of the dividend distribution",
    )


class StockDividend(StockDividendBase, table=True):
    """Dividend payouts table."""

    __table_args__ = (
        UniqueConstraint("stock_id", "ex_date", name="uq_stock_dividend_stock_date"),
        Index("ix_stock_dividend_stock_date", "stock_id", "ex_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="dividends")


class AnalystPriceTargetBase(SQLModel):
    """Analyst consensus price target from data sources."""

    date: datetime.date = Field(description="Date target was published or retrieved")
    stock_id: int = Field(foreign_key="stock.id")
    high: Decimal = Field(decimal_places=2)
    low: Decimal = Field(decimal_places=2)
    mean: Decimal = Field(decimal_places=2)
    median: Decimal = Field(decimal_places=2)


class AnalystPriceTarget(AnalystPriceTargetBase, table=True):
    """Analyst price targets table."""

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="analyst_targets")


# Helper Query Functions
def get_latest_price_date(session: Session, stock_id: int) -> datetime.date | None:
    """Get the latest price date of the stock from the database."""
    return session.exec(
        select(StockPrice.date)
        .where(StockPrice.stock_id == stock_id)
        .order_by(StockPrice.date.desc())
    ).first()


def get_close_price_on_date(session: Session, stock_id: int, date: datetime.date) -> float | None:
    """Get the stock's closing price on a specific date from the database."""
    return session.exec(
        select(StockPrice.close)
        .where(StockPrice.stock_id == stock_id)
        .where(StockPrice.date <= date)
        .order_by(StockPrice.date.desc())
    ).first()

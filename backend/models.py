import datetime
from decimal import Decimal
from sqlmodel import Field, Index, Relationship, SQLModel, UniqueConstraint


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

    __table_args__: tuple[UniqueConstraint] = (
        UniqueConstraint("ticker", "country", name="uq_stock_ticker_country"),
    )

    id: int | None = Field(default=None, primary_key=True)
    latest_price: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=10,
        description="Latest recorded price quote or settled closing price",
    )
    latest_price_update_at: datetime.datetime | None = Field(
        default=None,
        description="Timestamp of the latest price update",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp when stock was added to database",
    )

    # Relationships to time-series children
    prices: list["StockPrice"] = Relationship(back_populates="stock")
    dividends: list["StockDividend"] = Relationship(back_populates="stock")
    analyst_targets: list["AnalystPriceTarget"] = Relationship(back_populates="stock")
    earnings: list["StockEarning"] = Relationship(back_populates="stock")
    guidances: list["StockGuidance"] = Relationship(back_populates="stock")


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


class StockDividend(StockDividendBase, table=True):
    """Dividend payouts table."""

    __table_args__ = (
        UniqueConstraint("stock_id", "ex_date", name="uq_stock_dividend_stock_date"),
        Index("ix_stock_dividend_stock_date", "stock_id", "ex_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="dividends")


class AnalystPriceTargetBase(SQLModel):
    """Analyst consensus price target and recommendation breakdown."""

    date: datetime.date = Field(description="Date target was published or retrieved")
    stock_id: int = Field(foreign_key="stock.id", index=True)

    # 1. Price Targets (from yfinance analyst_price_targets)
    target_high: Decimal | None = Field(default=None, decimal_places=2, max_digits=10)
    target_low: Decimal | None = Field(default=None, decimal_places=2, max_digits=10)
    target_mean: Decimal | None = Field(default=None, decimal_places=2, max_digits=10)
    target_median: Decimal | None = Field(default=None, decimal_places=2, max_digits=10)

    # 2. Recommendation Breakdown (from yfinance recommendations)
    strong_buy: int = Field(default=0, description="Strong Buy recommendation count")
    buy: int = Field(default=0, description="Buy recommendation count")
    hold: int = Field(default=0, description="Hold recommendation count")
    sell: int = Field(default=0, description="Sell recommendation count")
    strong_sell: int = Field(default=0, description="Strong Sell recommendation count")
    total_analysts: int = Field(default=0, description="Total analyst coverage count")

    # 3. Weighted Score (1.0 = Strong Sell, 5.0 = Strong Buy)
    consensus_score: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=3,
        description="Weighted score: (5*SB + 4*B + 3*H + 2*S + 1*SS) / total",
    )


class AnalystPriceTarget(AnalystPriceTargetBase, table=True):
    """Analyst price targets and recommendation snapshots table."""

    __tablename__ = "analyst_price_target"
    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_analyst_target_stock_date"),
        Index("ix_analyst_target_stock_date", "stock_id", "date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="analyst_targets")


class StockEarningBase(SQLModel):
    """Corporate quarterly earnings announcements, Wall Street expectations, and actual results."""

    stock_id: int = Field(foreign_key="stock.id", index=True)
    report_date: datetime.date = Field(
        description="Date of the earnings release (or scheduled date for upcoming)"
    )
    fiscal_period: str | None = Field(
        default=None,
        max_length=20,
        description="Quarter label (e.g. 'Q3 2026' or '2026-09-30')",
    )

    # 1. Bottom-Line EPS (auto-populated by yfinance or enriched manually/agent)
    eps_estimate: Decimal | None = Field(
        default=None,
        decimal_places=4,
        max_digits=10,
        description="Consensus forecasted Earnings Per Share (in parent Stock.currency)",
    )
    eps_reported: Decimal | None = Field(
        default=None,
        decimal_places=4,
        max_digits=10,
        description="Actual announced Earnings Per Share (NULL for upcoming earnings)",
    )
    surprise_pct: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=6,
        description="EPS surprise percentage (e.g. +4.52 or -1.80)",
    )

    # 2. Top-Line Revenue (sourced from Web / 8-K / MCP Agent / UI)
    rev_estimate: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=14,
        description="Consensus forecasted Revenue (in parent Stock.currency)",
    )
    rev_reported: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=14,
        description="Actual announced Revenue (in parent Stock.currency)",
    )
    rev_surprise_pct: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=6,
        description="Revenue surprise percentage (e.g. +1.25 or -0.80)",
    )

    # 3. Provenance & Conflict Prevention
    data_source: str = Field(
        default="YFINANCE",
        max_length=20,
        description="Source of latest write ('YFINANCE', 'MANUAL', 'AGENT')",
    )
    is_verified: bool = Field(
        default=False,
        description="If True, automated yfinance background sync will not overwrite this record",
    )


class StockEarning(StockEarningBase, table=True):
    """Corporate earnings history and upcoming announcements table."""

    __tablename__ = "stock_earning"
    __table_args__ = (
        UniqueConstraint("stock_id", "report_date", name="uq_stock_earning_stock_date"),
        Index("ix_stock_earning_stock_date", "stock_id", "report_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="earnings")


class StockGuidanceBase(SQLModel):
    """Executive forward management guidance ranges issued during corporate disclosures."""

    stock_id: int = Field(foreign_key="stock.id", index=True)
    issue_date: datetime.date = Field(
        index=True,
        description="Date guidance was released (usually matching earnings release date)",
    )
    target_period: str = Field(
        max_length=20,
        description="Target horizon label (e.g. 'Q4 2026' or 'FY 2026')",
    )
    period_type: str = Field(
        default="QUARTER",
        max_length=20,
        description="Horizon type: 'QUARTER' or 'FULL_YEAR'",
    )

    # Revenue Guidance (in parent Stock.currency)
    rev_low: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=14,
        description="Management revenue guidance lower bound",
    )
    rev_high: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=14,
        description="Management revenue guidance upper bound",
    )
    rev_mid: Decimal | None = Field(
        default=None,
        decimal_places=2,
        max_digits=14,
        description="Management revenue guidance midpoint",
    )

    # EPS Guidance (in parent Stock.currency)
    eps_low: Decimal | None = Field(
        default=None,
        decimal_places=4,
        max_digits=10,
        description="Management EPS guidance lower bound",
    )
    eps_high: Decimal | None = Field(
        default=None,
        decimal_places=4,
        max_digits=10,
        description="Management EPS guidance upper bound",
    )
    eps_mid: Decimal | None = Field(
        default=None,
        decimal_places=4,
        max_digits=10,
        description="Management EPS guidance midpoint",
    )

    # Revision Momentum & Notes
    revision_type: str | None = Field(
        default=None,
        max_length=20,
        description="Revision direction: 'INITIAL', 'RAISED', 'LOWERED', or 'REAFFIRMED'",
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Executive commentary or key assumptions (e.g. FX headwind, capex update)",
    )
    data_source: str = Field(
        default="MANUAL",
        max_length=20,
        description="Source of guidance entry ('MANUAL', 'AGENT', '8K_PARSER')",
    )


class StockGuidance(StockGuidanceBase, table=True):
    """Forward management guidance table."""

    __tablename__ = "stock_guidance"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "issue_date",
            "target_period",
            name="uq_stock_guidance_stock_issue_target",
        ),
        Index("ix_stock_guidance_stock_issue", "stock_id", "issue_date"),
    )

    id: int | None = Field(default=None, primary_key=True)
    stock: Stock | None = Relationship(back_populates="guidances")



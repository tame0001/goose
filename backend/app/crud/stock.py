import datetime
from typing import Tuple
from sqlmodel import Session, desc, or_, select

from models import Stock, StockPrice
from shared.schemas.price import StockChangeResponse
from shared.schemas.stock import StockResponse


def get_stock_by_symbol(session: Session, symbol: str) -> Stock | None:
    """Look up a stock by either yf_ticker or local ticker in a single normalized query."""
    target = symbol.strip().upper()
    return session.exec(
        select(Stock).where(
            or_(Stock.yf_ticker == target, Stock.ticker == target)
        )
    ).first()


def get_latest_price_date(session: Session, stock_id: int) -> datetime.date | None:
    """Get the latest price date of the stock from the database."""
    latest = session.exec(
        select(StockPrice)
        .where(StockPrice.stock_id == stock_id)
        .order_by(desc(StockPrice.date))
    ).first()
    return latest.date if latest else None


def get_close_price_on_date(session: Session, stock_id: int, date: datetime.date) -> float | None:
    """Get the stock's closing price on or before a specific date."""
    record = session.exec(
        select(StockPrice)
        .where(StockPrice.stock_id == stock_id)
        .where(StockPrice.date <= date)
        .order_by(desc(StockPrice.date))
    ).first()
    return float(record.close) if record else None


def _pct_change(current: float | None, previous: float | None) -> float | None:
    """Calculate percentage change, returning None if data is missing or zero."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100


def calculate_stock_changes(session: Session, stock: Stock) -> Tuple[float | None, StockChangeResponse]:
    """Calculate the stock price changes over different time periods using local database records."""
    assert stock.id is not None

    # Retrieve latest recorded price from database (fast & offline-safe)
    latest_record = session.exec(
        select(StockPrice)
        .where(StockPrice.stock_id == stock.id)
        .order_by(desc(StockPrice.date))
    ).first()
    price_current = float(latest_record.close) if latest_record else None

    today = datetime.date.today()

    def _get_price(days_ago: int) -> float | None:
        assert stock.id is not None
        return get_close_price_on_date(
            session, stock.id, today - datetime.timedelta(days=days_ago)
        )

    price_last_week = _get_price(7)
    price_last_month = _get_price(30)
    price_last_quarter = _get_price(90)
    price_last_year = _get_price(365)

    changes = StockChangeResponse(
        week=_pct_change(price_current, price_last_week),
        month=_pct_change(price_current, price_last_month),
        quarter=_pct_change(price_current, price_last_quarter),
        year=_pct_change(price_current, price_last_year),
    )

    return price_current, changes


def get_all_stocks(session: Session) -> list[StockResponse]:
    """Retrieve all stocks from DB with latest cached price and performance changes (fast, read-only)."""
    stocks = session.exec(select(Stock)).all()
    results = []

    for stock in stocks:
        assert stock.id is not None
        price_current, changes = calculate_stock_changes(session, stock)

        results.append(
            StockResponse(
                id=stock.id,
                ticker=stock.ticker,
                name=stock.name,
                yf_ticker=stock.yf_ticker,
                country=stock.country,
                exchange=stock.exchange,
                currency=stock.currency,
                sector=stock.sector,
                industry=stock.industry,
                is_active=stock.is_active,
                created_at=stock.created_at,
                price=price_current,
                change=changes,
                earning=None,
            )
        )

    return results

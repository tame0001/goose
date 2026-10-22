import datetime
from typing import Tuple
from sqlmodel import Session, select
from models import Stock, StockPrice
import utils.yfinance as yf
from shared.schemas.price import StockChangeResponse, StockEarningResponse
from shared.schemas.stock import StockResponse
from utils.data_update import update_stock_price


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


def _pct_change(current: float | None, previous: float | None) -> float | None:
    """Calculate percentage change, returning None if data is missing or zero."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100


def calculate_stock_changes(session: Session, stock: Stock) -> Tuple[float | None, StockChangeResponse]:
    """Calculate the stock price changes over different time periods."""
    if get_latest_price_date(session, stock.id) == datetime.date.today():
        raw = get_close_price_on_date(session, stock.id, datetime.date.today())
        price_current = float(raw) if raw is not None else None
    else:
        price_current = yf.fetch_real_time_price(stock.yf_ticker)
    today = datetime.date.today()

    def _get_price(days_ago: int) -> float | None:
        raw = get_close_price_on_date(
            session, stock.id, today - datetime.timedelta(days=days_ago)
        )
        return float(raw) if raw is not None else None

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


def get_all_stocks_with_data(session: Session) -> list[StockResponse]:
    """Retrieve all stocks from DB, update historical prices, and compute changes."""
    stocks = session.exec(select(Stock)).all()
    results = []

    for stock in stocks:
        update_stock_price(session, stock)
        price_current, changes = calculate_stock_changes(session, stock)
        
        # Calculate earnings if available
        earnings_raw = yf.calculate_stock_earnings(stock)
        earnings = StockEarningResponse(
            eps_ttm=getattr(earnings_raw, "eps_ttm", None),
            eps_forecast=getattr(earnings_raw, "eps_forecast", None),
        ) if earnings_raw else None

        results.append(
            StockResponse(
                id=stock.id,
                ticker=stock.ticker,
                name=stock.name,
                yf_ticker=stock.yf_ticker,
                country=getattr(stock, "country", "USA"),
                exchange=getattr(stock, "exchange", None),
                currency=getattr(stock, "currency", "USD"),
                sector=getattr(stock, "sector", None),
                industry=getattr(stock, "industry", None),
                is_active=getattr(stock, "is_active", True),
                created_at=getattr(stock, "created_at", None),
                price=price_current,
                change=changes,
                earning=earnings,
            )
        )

    return results

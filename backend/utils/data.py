import datetime
from typing import Tuple
from sqlmodel import Session, select

import utils.yfinance as yf
from utils.dataclass import StockChange, StockData
from utils.data_update import update_stock_price
from dependencies import engine
from models import Stock, get_latest_price_date, get_close_price_on_date

# TODO: Check price jump
# TODO: Check when current price last seen
# TODO: Current price with EPS with similar prices or EPSs other stocks
# TODO: Check current price with analyst price target and historical price against analyst price target
# TODO: Check price against EPS


def read_stock_list() -> list[StockData]:
    """Read the stock list from the YAML file."""
    with Session(engine) as db:
        stocks = db.exec(select(Stock)).all()

        data = []
        # TODO: yf.Download is a better option to minimize the number of API calls
        # TODO: Create a composite index that combine stock_id and date to speed up the query last price in the database.
        # TODO: Use Window query to get all latest price in one query instead of querying for each stock separately.
        # TODO: Calculate change in batch instead of calculating for each stock separately.
        for stock in stocks:
            ticker = StockData(ticker=stock.ticker)
            ticker.yf_ticker = stock.yf_ticker
            # Update historical price data in the database
            update_stock_price(db, stock)
            ticker.price, ticker.change = calculate_stock_changes(db, stock)
            data.append(ticker)

    return data


def calculate_stock_changes(session: Session, stock: Stock) -> Tuple[float, StockChange]:
    """Calculate the stock price changes over different time periods."""
    # Get real-time price from Yahoo Finance
    # If the latest price in db is up to date, there is no need to fetch new data
    if get_latest_price_date(session, stock.id) == datetime.date.today():
        price_current = float(
            get_close_price_on_date(session, stock.id, datetime.date.today())
        )
    else:
        price_current = yf.fetch_real_time_price(stock.yf_ticker)
    today = datetime.date.today()
    price_last_week = float(
        get_close_price_on_date(
            session, stock.id, today - datetime.timedelta(days=7)
        )
    )
    price_last_month = float(
        get_close_price_on_date(
            session, stock.id, today - datetime.timedelta(days=30)
        )
    )
    price_last_quarter = float(
        get_close_price_on_date(
            session, stock.id, today - datetime.timedelta(days=90)
        )
    )
    price_last_year = float(
        get_close_price_on_date(
            session, stock.id, today - datetime.timedelta(days=365)
        )
    )
    # Format the price data to match the StockChange structure
    changes = StockChange()
    changes.week = (price_current - price_last_week) / price_last_week * 100
    changes.month = (price_current - price_last_month) / price_last_month * 100
    changes.quarter = (price_current - price_last_quarter) / price_last_quarter * 100
    changes.year = (price_current - price_last_year) / price_last_year * 100

    return price_current, changes


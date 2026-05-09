import datetime
from typing import Tuple
from sqlmodel import Session, select

import utils.yfinance as yf
from utils.dataclass import StockChange, StockData
from utils.data_update import update_stock_price
from utils.common import engine
from models import Stock


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
        update_stock_price(stock)
        ticker.price, ticker.change = calculate_stock_changes(stock)
        data.append(ticker)

    return data


def calculate_stock_changes(stock: Stock) -> Tuple[float, StockChange]:
    """Calculate the stock price changes over different time periods."""
    # TODO: If the latest price in db is up to date, there is no need to fetch new data.
    # Get real-time price from Yahoo Finance
    # TODO: Real-time price should be from other APIs
    price_current = yf.fetch_real_time_price(stock.yf_ticker)
    today = datetime.date.today()
    price_last_week = float(
        stock.get_close_price_on_date(
            Session(engine), today - datetime.timedelta(days=7)
        )
    )
    # Format the price data to match the StockChange structure
    changes = StockChange()
    # Calculate week change
    week_change = (price_current - price_last_week) / price_last_week * 100
    changes.week = week_change

    return price_current, changes

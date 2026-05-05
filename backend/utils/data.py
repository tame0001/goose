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
    # Get real-time price from Yahoo Finance
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

import datetime
from sqlmodel import Session, select

import utils.yfinance as yf
from utils.common import engine
from models import Stock, StockPrice


def create_stock(ticker: str, name: str, yf_ticker: str | None) -> Stock:
    """Create a new stock in the database."""
    stock = Stock(ticker=ticker, name=name, yf_ticker=yf_ticker)
    with Session(engine) as db:
        db.add(stock)
        db.commit()
        db.refresh(stock)
    return stock


def fetch_stock_data(yf_ticker: str) -> Stock:
    """Fetch stock data from the database."""
    with Session(engine) as db:
        stock = db.exec(
            select(Stock).where(Stock.yf_ticker == yf_ticker.upper())
        ).first()
    if not stock:
        # If the stock does not exist in the database, fetch it from Yahoo Finance
        # and add it to the database
        stock_info = yf.get_stock_info(yf_ticker)
        # If the stock is not found in Yahoo Finance, raise an exception
        if not stock_info.name:
            raise ValueError(
                f"Stock with ticker {yf_ticker} not found in Yahoo Finance."
            )
        stock = create_stock(
            # Extract the ticker without the exchange suffix
            ticker=yf_ticker.split(".")[0],
            name=stock_info.name,
            yf_ticker=stock_info.yf_ticker,
        )
    return stock


def update_stock_price(stock: Stock, start_date: datetime.date | None = None):
    """Update the stock price. By default, it will update the price for the current date.
    If the date is provided, it will update the price from that date to the current date."""
    # TODO: Update 1 year of historical price should be automatically done when adding a new stock to the database.
    # TODO: There should be separated functions, one for manually update with start_date and another one for automatically update the latest price.
    latest_price_date = stock.get_latest_price_date(Session(engine))
    # so only need to update database up to yesterday.
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    # If yesterday Saturday or Sunday, set it to the latest Friday
    if yesterday.weekday() >= 5:
        yesterday -= datetime.timedelta(days=yesterday.weekday() - 4)
    # If the start date is provided.
    if start_date:
        with Session(engine) as db:
            oldest_price = db.exec(
                select(StockPrice)
                .where(StockPrice.stock == stock)
                .order_by(StockPrice.date.asc())
            ).first()
        # If the oldest price date is after the start date,
        # fetch the historical data from Yahoo Finance
        if oldest_price and oldest_price.date > start_date:
            history = yf.fetch_stock_price(
                stock.yf_ticker,
                start_date,
                oldest_price.date - datetime.timedelta(days=1),
            )
        else:
            # No need to update the price
            return
    # If price history is empty,
    # fetch 1 year of historical data from Yahoo Finance
    elif not latest_price_date:
        history = yf.fetch_stock_price(
            stock.yf_ticker, datetime.date.today() - datetime.timedelta(days=365)
        )
    # If the latest price date is before yesterday,
    # fetch the historical data from Yahoo Finance
    elif latest_price_date and latest_price_date < yesterday:
        history = yf.fetch_stock_price(
            stock.yf_ticker, latest_price_date + datetime.timedelta(days=1), yesterday
        )
    else:
        # No need to update the price
        return
    # Update the stock price in the database
    # If the history is empty due to holiday or other reasons, do nothing
    if not history.empty:
        with Session(engine) as db:
            for date, row in history.iterrows():
                price = StockPrice(
                    date=date.date(),
                    stock_id=stock.id,
                    # Round the price to 2 decimal places
                    open=round(row["Open"], 2),
                    high=round(row["High"], 2),
                    low=round(row["Low"], 2),
                    close=round(row["Close"], 2),
                )
                db.add(price)
            db.commit()

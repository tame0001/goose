import datetime
from sqlmodel import Session, create_engine, select

import utils.yfinance as yf
from utils.dataclass import StockChange, StockData
from models import Stock, StockPrice
from dependencies import SQLALCHEMY_DATABASE_URL


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)


def create_stock(ticker: str, name: str, yf_ticker: str | None):
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


def update_stock_price(
    stock: Stock, start_date: datetime.date | None = None
) -> StockPrice:
    """Update the stock price. By default, it will update the price for the current date.
    If the date is provided, it will update the price from that date to the current date.
    Return latest price in the database."""
    # Find the latest price date in the database
    with Session(engine) as db:
        latest_price = db.exec(
            select(StockPrice)
            .where(StockPrice.stock == stock)
            .order_by(StockPrice.date.desc())
        ).first()
    # Today is the latest weekday
    today = datetime.date.today()
    # If today is Saturday or Sunday, set it to the latest Friday
    if today.weekday() >= 5:
        today -= datetime.timedelta(days=today.weekday() - 4)
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
            return latest_price
    # If price history is empty,
    # fetch 1 year of historical data from Yahoo Finance
    elif not latest_price:
        history = yf.fetch_stock_price(
            stock.yf_ticker, today - datetime.timedelta(days=365)
        )
    # If the latest price date is before today,
    # fetch the historical data from Yahoo Finance
    elif latest_price and latest_price.date < today:
        history = yf.fetch_stock_price(
            stock.yf_ticker, latest_price.date + datetime.timedelta(days=1), today
        )
    else:
        # No need to update the price
        return latest_price
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
            # Refresh the latest price after updating the database
            latest_price = db.exec(
                select(StockPrice)
                .where(StockPrice.stock == stock)
                .order_by(StockPrice.date.desc())
            ).first()
    return latest_price


def read_stock_list() -> list[StockData]:
    """Read the stock list from the YAML file."""
    with Session(engine) as db:
        stocks = db.exec(select(Stock)).all()

    data = []
    for stock in stocks:
        ticker = StockData(ticker=stock.ticker)
        ticker.yf_ticker = stock.yf_ticker
        ticker.price = update_stock_price(stock).close
        ticker.change = calculate_stock_changes(stock)
        data.append(ticker)

    return data


def calculate_stock_changes(stock: Stock) -> StockChange:
    """Calculate the stock price changes over different time periods."""
    # Get real-time price from Yahoo Finance
    price_current = yf.fetch_real_time_price(stock.yf_ticker)
    # Get latest price from the database
    today = datetime.date.today()
    with Session(engine) as db:
        price_last_week = float(
            db.exec(
                select(StockPrice)
                .where(StockPrice.stock == stock)
                .where(StockPrice.date <= today - datetime.timedelta(days=7))
                .order_by(StockPrice.date.desc())
            )
            .first()
            .close  # Use the closing price for the change calculation
        )
    # Format the price data to match the StockChange structure
    changes = StockChange()
    # Calculate week change
    week_change = (price_current - price_last_week) / price_last_week * 100
    changes.week = week_change

    return changes


if __name__ == "__main__":
    with Session(engine) as db:
        stocks = db.exec(select(Stock)).all()
        for stock in stocks:
            update_stock_price(stock, start_date=datetime.date(2025, 1, 1))

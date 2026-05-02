import yaml
import yfinance as yf
from pathlib import Path
from pydantic.dataclasses import dataclass
from sqlmodel import Session, create_engine, select

from models import Stock
from dependencies import SQLALCHEMY_DATABASE_URL
from .yfinance import get_stock_info


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)


@dataclass
class StockChange:
    week: float | None = None
    month: float | None = None
    quarter: float | None = None
    year: float | None = None


@dataclass
class StockEarning:
    # Trailing Twelve Months Earnings Per Share
    eps_ttm: float | None = None
    # Forecast Earnings Per Share
    eps_forecast: float | None = None


@dataclass
class StockData:
    ticker: str
    yf_ticker: str | None = None
    yf_data: dict | None = None
    price: float | None = None
    change: StockChange | None = None
    earning: StockEarning | None = None


path = Path(__file__).parent


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
        stock_info = get_stock_info(yf_ticker)
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


def read_stock_list() -> list[StockData]:
    """Read the stock list from the YAML file."""
    with open(path / "stock-list.yml", "r") as fp:
        stocks = yaml.safe_load(fp)

    data = []
    # Fetch data from Yahoo Finance
    for stock in stocks["thai"]:
        ticker = StockData(ticker=stock)
        # Stock in Thailand are suffixed with .BK
        ticker.yf_ticker = f"{stock.upper()}.BK"
        ticker.yf_data = yf.Ticker(ticker.yf_ticker)
        ticker.price = ticker.yf_data.info["currentPrice"]
        ticker.change = calculate_stock_changes(ticker)
        ticker.earning = calculate_stock_earnings(ticker)
        data.append(ticker)

    return data


def calculate_stock_changes(stock: StockData) -> StockChange:
    """Calculate the stock price changes over different time periods."""
    # Get the historical price data. The return is a DataFrame
    history = stock.yf_data.history(period="5d")
    changes = StockChange()
    # If the history is empty, return an empty StockChange
    if history.empty:
        return changes

    closing_prices = history["Close"].tolist()
    # Calculate week change
    week_change = (stock.price - closing_prices[0]) / closing_prices[0] * 100
    changes.week = week_change

    return changes


def calculate_stock_earnings(stock: StockData) -> StockEarning:
    """Calculate the stock earnings.
    1. eps_ttm: TTM EPS (Trailing Twelve Months Earnings Per Share): This is the EPS calculated based on the company's earnings over the past 12 months.
    2. eps_forecast: Forecast EPS (Earnings Per Share): This is the projected EPS for the
    """
    ticker_info = stock.yf_data.info
    earnings = StockEarning()
    try:
        earnings.eps_ttm = ticker_info["trailingEps"]
        earnings.eps_forecast = ticker_info["forwardEps"]
    except KeyError:
        pass

    return earnings

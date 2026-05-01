import yaml
import yfinance as yf
from pathlib import Path
from pydantic.dataclasses import dataclass


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

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
class StockData:
    ticker: str
    yf_ticker: str | None = None
    price: float | None = None
    change: StockChange | None = None


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
        ticker.price = yf.Ticker(ticker.yf_ticker).info["currentPrice"]
        ticker.change = calculate_stock_changes(ticker)
        data.append(ticker)

    return data


def calculate_stock_changes(stock: StockData) -> StockChange:
    """Calculate the stock price changes over different time periods."""
    ticker = yf.Ticker(f"{stock.ticker.upper()}.BK")
    # Get the historical price data. The return is a DataFrame
    history = ticker.history(period="5d")
    changes = StockChange()
    # If the history is empty, return an empty StockChange
    if history.empty:
        return changes

    closing_prices = history["Close"].tolist()
    # Calculate week change
    week_change = (stock.price - closing_prices[0]) / closing_prices[0] * 100
    changes.week = week_change

    return changes

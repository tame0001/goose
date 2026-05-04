import yfinance as yf
from datetime import date

from utils.dataclass import StockData, StockEarning
from models import StockBase


def get_stock_info(ticker: str) -> StockBase:
    """Fetch stock information using yfinance.
    Returns a Stock object."""
    stock = yf.Ticker(ticker)
    info = stock.info

    return StockBase(
        ticker=ticker, name=info.get("longName", ""), yf_ticker=info.get("symbol", None)
    )


def fetch_stock_price(ticker: str, start_date: date, end_date: date = date.today()):
    """Fetch stock price data from yfinance."""
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date, end=end_date)
    return hist


def fetch_real_time_price(ticker: str) -> float | None:
    """Fetch real-time stock price from yfinance."""
    stock = yf.Ticker(ticker)
    info = stock.info
    return info.get("currentPrice", None)


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


"""
API Reference:
From Ticker
- analyst_price_targets
{'current': 131.6, 'high': 150.0, 'low': 62.0, 'mean': 136.56097, 'median': 138.0}

- balance_sheet
return dataframe with balance sheet data

- calendar 
{'Dividend Date': datetime.date(2027, 1, 3), 'Ex-Dividend Date': datetime.date(2026, 5, 7), 'Earnings Date': [datetime.date(2026, 5, 21)], 'Earnings High': 0.73, 'Earnings Low': 0.63, 'Earnings Average': 0.65885, 'Revenue High': 174273600000, 'Revenue Low': 170523000000, 'Revenue Average': 172235651180}


"""

import yfinance as yf

from models import StockBase


def get_stock_info(ticker: str) -> StockBase:
    """Fetch stock information using yfinance.
    Returns a Stock object."""
    stock = yf.Ticker(ticker)
    info = stock.info

    return StockBase(
        ticker=ticker, name=info.get("longName", ""), yf_ticker=info.get("symbol", None)
    )

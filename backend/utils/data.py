import yaml
import yfinance as yf
from pathlib import Path
from pydantic.dataclasses import dataclass


@dataclass
class StockData:
    ticker: str
    price: float | None = None


path = Path(__file__).parent


def read_stock_list() -> list[StockData]:
    """Read the stock list from the YAML file."""
    with open(path / "stock-list.yml", "r") as fp:
        stocks = yaml.safe_load(fp)

    # Stock in Thailand are suffixed with .BK
    data = yf.Tickers(" ".join([f"{stock.upper()}.BK" for stock in stocks["thai"]]))

    return [
        StockData(
            ticker=stock,
            # The price is the previous close price
            price=data.tickers[f"{stock.upper()}.BK"].info["previousClose"],
        )
        for stock in stocks["thai"]
    ]

from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll
from textual.widgets import Header, Footer, Static

from utils.data import read_stock_list, StockData

# TODO: Follow this https://textual.textualize.io/tutorial/


class StockName(Static):
    DEFAULT_CSS = """
    StockName {
        border: dashed white;
        padding: 1;
    }  

    StockName:hover {
        background: $secondary;
    }
    """


class StockBar(HorizontalGroup):
    """A widget to display stock information."""

    def __init__(self, stock: StockData):
        super().__init__()
        self.stock = stock

    def compose(self) -> ComposeResult:
        """Create child widgets for the stock bar."""
        yield StockName(f"{self.stock.ticker.upper()} {self.stock.price:.2f}")


class GooseApp(App):
    """A Terminal User Interface for the Goose application."""

    def __init__(self):
        super().__init__()
        self.stocks = read_stock_list()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield VerticalScroll(*[StockBar(stock) for stock in self.stocks])


def terminal_ui():
    """Run the Terminal User Interface."""
    app = GooseApp()
    app.run()

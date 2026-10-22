from api_client import GooseAPIClient
from textual.app import App, ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll
from textual.widgets import Footer, Header, Static

from shared.schemas.stock import StockResponse


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

    def __init__(self, stock: StockResponse):
        super().__init__()
        self.stock = stock

    def compose(self) -> ComposeResult:
        """Create child widgets for the stock bar."""
        price = f"{self.stock.price:.2f}" if self.stock.price is not None else "N/A"
        week = (
            f"{self.stock.change.week:.2f}%"
            if self.stock.change and self.stock.change.week is not None
            else "N/A"
        )
        yield StockName(
            f"{self.stock.ticker.upper()} Current Price: {price} Week Change: {week} "
        )


class GooseApp(App):
    """A Terminal User Interface for the Goose application."""

    def __init__(self):
        super().__init__()
        self.client = GooseAPIClient()
        self.stocks = self.client.fetch_stocks()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        # Sort by weekly change (stocks with missing data go to the bottom)
        self.stocks.sort(
            key=lambda x: x.change.week
            if x.change and x.change.week is not None
            else float("-inf"),
            reverse=True,
        )
        yield VerticalScroll(*[StockBar(stock) for stock in self.stocks])


def terminal_ui():
    """Run the Terminal User Interface."""
    app = GooseApp()
    app.run()


if __name__ == "__main__":
    terminal_ui()

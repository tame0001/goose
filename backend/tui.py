from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


# TODO: Follow this https://textual.textualize.io/tutorial/
class GooseApp(App):
    """A Terminal User Interface for the Goose application."""

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()


def terminal_ui():
    """Run the Terminal User Interface."""
    app = GooseApp()
    app.run()

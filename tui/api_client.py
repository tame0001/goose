import os

import httpx

from shared.schemas.stock import StockResponse


class GooseAPIClient:
    """HTTP Client for communicating with the Goose FastAPI backend."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000/api/v1")

    def fetch_stocks(self) -> list[StockResponse]:
        """Fetch stock list from backend REST API."""
        try:
            response = httpx.get(f"{self.base_url}/stocks", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return [StockResponse.model_validate(item) for item in data]
        except httpx.HTTPError as e:
            # Fallback or empty list on connection error
            print(f"[TUI Client] Failed to fetch stocks from backend: {e}")
            return []

.PHONY: backend tui web sync lint

sync:
	uv sync

backend:
	cd backend && uv run uvicorn app.main:app --reload

tui:
	cd tui && uv run python main.py

web:
	cd web && ng serve

lint:
	uv run ruff check

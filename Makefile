.PHONY: backend tui web sync lint backup

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

backup:
	@mkdir -p .db_backup
	@sqlite3 backend/db.sql ".backup '.db_backup/goose_backup.db'"
	@sqlite3 backend/db.sql ".dump" > ".db_backup/goose_backup.sql"
	@echo "✅ Backup updated in .db_backup/ (goose_backup.db & goose_backup.sql)"



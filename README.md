# Goose 🪿

**Goose** is a multi-client portfolio management, dividend investing, and stock analysis platform. It provides an API-first backend to track stock fundamentals, daily OHLCV prices, dividend distributions, and quantitative portfolio optimization models across US and Thai markets.

---

## Architecture Overview

Goose is built as an **API-first monorepo** using a unified **`uv` workspace**:
* **FastAPI Backend (`backend/`)**: The single source of truth for database access, business logic, and third-party data integrations (e.g. Yahoo Finance). Owns the SQLite database (`backend/db.sql`).
* **Shared Contract (`shared/`)**: Shared Pydantic schemas and enums used across backend and clients to ensure end-to-end data integrity.
* **Terminal UI (`tui/`)**: A fast, interactive terminal dashboard built with **Textual** for active development and quick inspection. Communicates with the backend strictly via HTTP REST.
* **Web UI (`web/`, Planned)**: An Angular single-page application for production web consumption.

```mermaid
graph TD
    Shared["shared/ (goose-shared)<br>Pydantic schemas & enums"]
    DB[("SQLite (backend/db.sql)")] <--> Backend["FastAPI Backend Server (goose-backend)"]
    Shared --> Backend
    Shared --> TUI["Textual TUI Client (goose-tui)"]
    Backend <-->|HTTP REST / httpx| TUI
    Backend <..->|HTTP REST / HttpClient (Planned)| Angular["Angular Web Client (Planned)"]
```

---

## Directory Structure

```
goose/
├── docs/                      # Architectural & design specifications
│   ├── DATABASE_DESIGN.md     # Relational schema, ER diagram, constraints, and draft API
│   ├── PROJECT_STRUCTURE.md   # Multi-client workspace layout and system architecture
│   └── CODE_REVIEW.md         # Backend code audit and prioritized backlog
│
├── backend/                   # FastAPI REST API & Database server (goose-backend)
│   ├── app/
│   │   ├── api/               # API endpoints (/api/v1/stocks)
│   │   ├── core/              # Global config and database session management
│   │   └── crud/              # Database query logic
│   ├── migrations/            # Alembic database migration scripts
│   ├── models.py              # SQLModel database tables (Stock, StockPrice, StockDividend)
│   ├── utils/                 # Data fetching and calculations (yfinance)
│   └── pyproject.toml         # Backend package definition
│
├── shared/                    # Shared Pydantic data schemas & contracts (goose-shared)
│   ├── schemas/               # Stock, Price, and Dividend response/request schemas
│   ├── enums.py               # Shared enumerations (Currency, Exchange)
│   └── pyproject.toml         # Shared package definition
│
├── tui/                       # Textual Terminal Client (goose-tui)
│   ├── api_client.py          # Asynchronous HTTP client (httpx) calling backend
│   ├── main.py                # Textual TUI dashboard entry point
│   ├── goose.sh               # Terminal launcher script
│   └── pyproject.toml         # TUI package definition
│
├── experiment/                # Research & Algorithmic Prototyping
│   └── portfolio_optimization_idea.md  # Dividend & upside portfolio optimization proposal
│
├── pyproject.toml             # Root uv workspace configuration
├── Makefile                   # Convenience commands for development
└── README.md                  # Project overview (this file)
```

---

## Key Documentation

* 📐 [**Database & API Design (`docs/DATABASE_DESIGN.md`)**](docs/DATABASE_DESIGN.md): Detailed ER diagrams, table schemas (`Stock`, `StockPrice`, `StockDividend`), multi-market ticker collision handling (`ticker x country`), and REST API specifications.
* 🏗️ [**Project Architecture (`docs/PROJECT_STRUCTURE.md`)**](docs/PROJECT_STRUCTURE.md): Detailed explanation of the multi-client decoupling, workspace structure, and packaging rationale.
* 💡 [**Portfolio Optimization Strategy (`experiment/portfolio_optimization_idea.md`)**](experiment/portfolio_optimization_idea.md): Quantitative framework for dividend yield and analyst target optimization, critical risk assessment, and phased backtesting roadmap.
* 🔍 [**Code Review & Backlog (`docs/CODE_REVIEW.md`)**](docs/CODE_REVIEW.md): Audit of legacy queries, N+1 optimization, and technical debt.

---

## Getting Started

### Prerequisites
* Python `>= 3.12`
* [`uv`](https://github.com/astral-sh/uv) (fast Python package and project manager)

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:tame0001/goose.git
   cd goose
   ```

2. **Sync workspace dependencies**:
   ```bash
   make sync
   # or: uv sync
   ```

---

## Running the Application

### 1. Start the FastAPI Backend
```bash
make backend
# Server runs on http://127.0.0.1:8000
# Interactive Swagger docs: http://127.0.0.1:8000/docs
```

### 2. Launch the Textual TUI Client
In a separate terminal window:
```bash
make tui
# or: cd tui && uv run python main.py
```

### 3. Code Formatting & Linting
```bash
make lint
# Runs ruff check across all workspace packages
```

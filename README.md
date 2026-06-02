# Trading Journal

Local-first trading journal for Munch, inspired by TradeZella and implemented as V1-Lite.

## Phase 1 Scope

Phase 1 builds the foundation only:

- Project scaffold
- SQLite initialization
- Backend structure
- Frontend structure
- README

The following features are intentionally deferred: TradeLocker import, cloud sync, AI features, advanced review workflows, execution-level trade entry UI, daily journal, trade CRUD, reviews, psychology scoring, and analytics calculations.

## Source of Truth

SQLite is the source of truth. All future analytics must derive from canonical rows in the `trades` table and its related tables, while preserving user-entered values.

## Project Structure

```text
trading_journal/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route modules
│   │   ├── db/               # SQLite connection, schema, and initialization
│   │   ├── models/           # Future typed data models
│   │   ├── services/         # Future business logic
│   │   ├── config.py         # Local configuration
│   │   └── main.py           # FastAPI application entrypoint
│   └── pyproject.toml
├── data/                     # Local SQLite database location, ignored by Git
├── frontend/
│   ├── src/
│   │   ├── components/       # Future shared React components
│   │   ├── pages/            # Dashboard, Trades, Trade Detail, Playbooks, Settings
│   │   ├── styles/           # Global styling
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
└── project_bootstrap.json    # Authoritative implementation guide for V1-Lite
```

## SQLite Schema

Phase 1 creates the approved V1-Lite tables:

- `accounts`
- `instruments`
- `playbooks`
- `trades`
- `tags`
- `trade_tags`
- `attachments`
- `trade_attachments`
- `psychology_entries`
- `trade_reviews`

Trade statuses are constrained to `draft`, `closed`, `reviewed`, and `archived`. Trades keep the user-entered `symbol` as the authoritative analytics value while optionally linking to `instruments` for stable instrument metadata, avoiding a later symbol-to-instrument refactor. Attachments are metadata-only and constrained to `before_screenshot` and `after_screenshot`.

## Backend Setup

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app.db.init_db
uvicorn app.main:app --reload
```

The SQLite database initializes at `data/trading_journal.db` by default.

## Frontend Setup

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

The Phase 1 frontend is a React + Vite shell with placeholder pages for Dashboard, Trades, Trade Detail, Playbooks, and Settings.

## Phase 2 Implementation Plan

Phase 2 will add Trade Logging without moving beyond V1-Lite:

1. Add backend CRUD routes for trades, playbooks, tags, and metadata-only screenshots.
2. Keep `trades` as the canonical record for analytics inputs, preserving the submitted symbol even when a trade links to an instrument record.
3. Implement simple React forms for the approved trade entry fields: symbol, direction, entry price, exit price, quantity, P&L, risk, playbook, tags, and notes.
4. Add list/detail UI for trades and simple playbook/tag management.
5. Preserve user-entered values exactly; do not auto-correct or enrich data.
6. Add tests around schema initialization and CRUD behavior before implementing review or analytics phases.

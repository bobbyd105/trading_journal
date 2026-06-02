# Post-Phase 2 Architecture Audit

Branch: `architecture/post-phase2-audit`
Audit date: 2026-06-02
Scope: Current implementation after PR #3, with no new product features added.

## Architecture findings

### 1. Backend route structure

- Phase 2 CRUD routes are currently concentrated in `backend/app/api/crud.py`. This is workable for the V1-Lite surface area, but it mixes request handlers, payload schemas, validation helpers, and direct SQL operations in one module.
- The health route remains separate in `backend/app/api/health.py`, which is a good pattern to preserve as new feature areas are added.
- The audit extracted request-scoped database session resolution into `backend/app/db/session.py`, so route modules no longer own database-path resolution or initialization details.

### 2. Database access patterns

- SQLite connection creation is centralized through `backend/app/db/connection.py`, and schema initialization remains centralized through `backend/app/db/init_db.py`.
- The API still performs SQL directly from route handlers. This keeps Phase 2 simple, but creates a scaling risk once Reviews add more write workflows and richer trade hydration.
- `hydrate_trade` currently performs follow-up queries for tags and attachments per trade. This is acceptable for local-first V1-Lite usage, but the list endpoint has an N+1 query shape that should be watched before adding review summaries to list responses.

### 3. Service/repository boundaries

- `backend/app/services/` and `backend/app/models/` exist but are not yet used.
- Current behavior-oriented helpers (`ensure_playbook_exists`, `ensure_tags_exist`, `sync_trade_tags`, `hydrate_trade`, attachment upsert logic) are route-local. These are the first candidates for repository/service extraction when Phase 3 begins.
- Recommended next extraction order: schemas first, repositories second, services third. This minimizes churn and avoids inventing abstractions before Review behavior is known.

### 4. Frontend state management

- App-level React state is centralized in `App.jsx` for trades, playbooks, tags, selected trade, edit mode, and notification message. This is still acceptable for Phase 2.
- Phase 3 will likely add review form state. If added directly to `App.jsx`, the root component may become the main frontend bottleneck.
- The audit moved trade form defaults and conversion helpers into `frontend/src/domain/trades.js`, keeping state transformations separate from component rendering.

### 5. API request organization

- The frontend had one inline `apiRequest` helper in `App.jsx`.
- The audit moved the request helper to `frontend/src/api/client.js`. This creates a stable home for future endpoint wrappers without changing current fetch behavior.
- Recommended Phase 3 follow-up: add thin feature-specific API functions only as needed, for example a reviews API module, rather than scattering raw `fetch` calls through pages.

### 6. Validation consistency

- Backend payload models consistently forbid extra fields and use constrained literals for trade status, direction, and attachment type.
- The SQLite schema also enforces status, direction, attachment type, booleans, uniqueness, foreign keys, and cascades. This is a strong Phase 2 foundation.
- Frontend validation remains mostly HTML/input driven and does not mirror all backend constraints. This is acceptable for now, but Phase 3 should avoid duplicating validation rules manually across several components.

### 7. Future refactor risks relative to the approved roadmap

- Reviews are already represented in the schema, but no Review API/UI behavior exists in this audit change.
- The biggest Phase 3 risk is adding review logic into the existing `crud.py` route module without first separating schemas and repository functions. That would make later psychology, analytics, imports, cloud sync, or AI work harder to isolate.
- Do not add psychology, analytics, imports, cloud sync, or AI concerns while implementing Reviews. Keep Reviews bounded to review persistence, retrieval, and trade-review relationships.

## Risks discovered

1. **Backend route bloat:** `crud.py` is already carrying routes, schemas, validation, and SQL. Reviews could push it beyond maintainable size.
2. **N+1 trade hydration:** `list_trades` hydrates each trade individually. This is tolerable now, but review summary data could amplify the issue.
3. **Unused boundary directories:** `services` and `models` are placeholders. Adding Phase 3 code without deciding their role may create inconsistent layering.
4. **Root frontend state concentration:** `App.jsx` remains the coordinator for all loaded entities and form actions. Review state should be isolated before it becomes another root-level cluster.
5. **Validation drift:** Backend and database constraints are aligned, but frontend form constraints are not centralized with domain conversion logic.

## Files modified

- `backend/app/api/crud.py` imports database session helpers instead of defining request database resolution inline.
- `backend/app/db/session.py` centralizes request-scoped database path resolution and initialized connection creation.
- `backend/pyproject.toml` declares the HTTP test client dependency in the backend dev extras so route tests have an explicit dependency path.
- `frontend/src/App.jsx` imports API and trade-domain helpers instead of defining them inline.
- `frontend/src/api/client.js` centralizes frontend API request/error handling.
- `frontend/src/domain/trades.js` centralizes empty trade state and trade form/payload conversion.
- `docs/architecture/post-phase2-audit.md` records the audit findings, risks, and Phase 3 recommendation.

## Phase 3 recommendation

Phase 3 Reviews is safe to begin if it starts with a small boundary cleanup:

1. Move Pydantic schemas out of `crud.py` into a schemas module.
2. Move trade/playbook/tag/attachment SQL helpers into repository modules before adding review queries.
3. Keep review API routes in a dedicated route module or clearly separated router section.
4. Keep review frontend state close to the Reviews UI rather than expanding `App.jsx` further.
5. Do not introduce roadmap-later concerns: psychology, analytics, imports, cloud sync, or AI.

If those guardrails are followed, the current Phase 2 implementation is stable enough for Reviews.

# Repository Guidelines

## Project Structure & Module Organization
- `backend/` runs the FastAPI service; `main.py` exposes the app and `api.py` + `scheduler.py` manage routes and jobs.
- Analysis code lives in `backend/data_management/`, `factors/`, and `market_data/`; extend these modules when adding tasks or factors.
- `frontend/app/` is the Vite + React UI (`components/`, `services/api.ts`, `hooks/`, `types.ts`); static assets stay in `frontend/public/` and deployment scripts at the repo root.

## Build, Test, and Development Commands
- `pnpm run install:all` installs Node packages and synchronizes Python deps through `uv sync --quiet`.
- `pnpm run dev` launches both tiers (`uvicorn main:app --reload` + Vite on port 5173) for development.
- `pnpm run dev:backend` or `pnpm run dev:frontend` focus on one tier; API docs: `http://localhost:8000/docs`.
- `pnpm run build` bundles the frontend and invokes the backend placeholder; update `build:backend` when packaging.
- Run `uv run pytest`, `uv run ruff check backend`, and `uv run black backend` before pushing.

## Coding Style & Naming Conventions
- Python code follows PEP 8: 4-space indentation, snake_case modules, and PascalCase classes.
- Use Ruff and Black for linting/formatting; fix warnings instead of suppressing them.
- React files use PascalCase component names, `use`-prefixed hooks, and colocated helper logic in `app/lib/`; style with Tailwind utilities and keep generated assets out of git.

## Testing Guidelines
- Store backend specs in `backend/tests/` and mirror the module name in each filename.
- Mock external services (LLM, market feeds) so `uv run pytest` runs offline; cover scheduler and factor edges.
- Until a frontend harness exists, rely on manual smoke tests via `pnpm run dev`; if you add automation, prefer Vitest + Testing Library in `frontend/app/__tests__/`.

## Commit & Pull Request Guidelines
- Mirror the existing history: short, imperative commit subjects under 72 characters (e.g., `fix polling non stop issue`).
- Keep each commit focused on one concern and note config or migration steps in the body when relevant.
- PRs should describe changes, list verification steps, link issues, include UI screenshots when relevant, and note the gates you ran.

## Security & Configuration Tips
- Replace real secrets in `backend/config.json` with placeholders and load runtime values from environment variables inside `config.py`.
- Keep credentials in untracked `.env.local` files or your deployment secret store; only commit sample values that are safe to share.
- After changing ports, URLs, or scopes, review Docker and deployment scripts so Traefik, TLS, and clients stay aligned.

# Repository Guidelines

## Project Structure & Module Organization

- `app/backend/app/` contains the FastAPI API, PostgreSQL repositories, inventory synchronization, ZPL generation, and printer adapters.
- `app/backend/label_templates/` stores Zebra ZPL templates. Keep template placeholders compatible with the validation in `printer.py`.
- `app/frontend/src/` contains the React/Vite application, organized into `features/` and reusable `shared/` modules.
- `app/windows_agent/` contains the Windows service that polls the backend and writes ZPL to the local spooler.
- `scripts/` contains PostgreSQL schema/seed SQL, external inventory queries, and startup utilities.
- `docker/` and `docker-compose.yml` define the development containers. Documentation and architecture assets live in `docs/`.

## Build, Test, and Development Commands

Run commands from the repository root unless noted otherwise:

- `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1` runs frontend, backend, and PostgreSQL in Docker.
- `scripts\install-print-agent.ps1` installs the Windows print agent as a service; use `run-print-agent.ps1` for foreground diagnostics.
- `docker compose --env-file .\conn\.env config` validates Compose interpolation.
- `python -m compileall app\backend\app` checks backend syntax.
- In `app/frontend`, `npm run build` creates a production build and `npm run lint` runs ESLint/Prettier checks.

## Coding Style & Naming Conventions

Use four spaces and type hints for Python. Follow existing FastAPI/Pydantic patterns and use `snake_case` for functions and variables. React components use PascalCase exports and kebab-case filenames, while variables and hooks use camelCase. Prefer shared UI components and API functions over duplicating request or layout logic. Keep SQL keywords and database identifiers consistent with existing query files.

## Testing Guidelines

No automated test suite is currently committed. For every change, run backend/agent compilation, frontend build, and `git diff --check`. Exercise queue claiming and result reporting without hardware before validating the Zebra under the dedicated service account.

## Commit & Pull Request Guidelines

Recent commits use concise Spanish descriptions beginning with `Se ajusta`, `Se cambia`, or `Se corrige`. Keep each commit focused on one behavior. Pull requests should describe the problem, implementation, validation commands, configuration or schema impact, and rollback considerations. Include screenshots for visible UI changes and link the relevant issue when available.

## Security & Configuration Tips

Never commit `conn/.env`, agent tokens, database passwords, SSH credentials, or production data. Update the example env files whenever adding configuration. Docker uses `clinic_db`; the Windows agent only receives generated ZPL through authenticated API endpoints.

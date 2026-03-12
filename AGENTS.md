# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Wilo Water Pump Automation System — an IoT smart water pump management platform with AI-powered predictive control. Two independent runnable services:

1. **Python backend** — ML-based pump automation engine with terminal dashboard (runs via `python run.py` from repo root)
2. **React dashboard** — Vite + React + TypeScript web monitoring UI (runs via `npm run dev` in `dashboard/`, serves on port 8080)

The two services are **independent** and do not communicate — the React dashboard runs fully client-side simulations.

### Running services

- **Python backend**: `cd /workspace && python3 run.py` (runs an infinite monitoring loop; use `PYTHONUNBUFFERED=1` if capturing output to a file)
- **React dashboard**: `cd /workspace/dashboard && npm run dev` (Vite dev server on port 8080)

### Lint, test, build commands

| Service | Lint | Test | Build |
|---------|------|------|-------|
| Python backend | N/A (no linter configured) | `python3 -m pytest tests/unit/` (note: `test_analysis.py` is a standalone script, not proper pytest tests — 0 tests collected) | N/A |
| React dashboard | `npm run lint` (in `dashboard/`) | N/A (no test framework configured) | `npm run build` (in `dashboard/`) |
| TypeScript check | `npx tsc --noEmit` (in `dashboard/`) | — | — |

### Non-obvious caveats

- The Python backend uses ANSI escape codes for its terminal UI. When redirecting output to a file, set `PYTHONUNBUFFERED=1` to avoid empty captures due to buffering.
- The test file `tests/unit/test_analysis.py` is a standalone script (not pytest-compatible), so `pytest tests/unit/` collects 0 tests. Run it directly with `python tests/unit/test_analysis.py` from the `data/raw/` directory (it expects `synthetic_water_data.csv` in CWD).
- ESLint reports pre-existing errors/warnings in the dashboard (9 errors, 9 warnings); these are in the existing codebase.
- The `dashboard/package-lock.json` is present, so use `npm` (not pnpm/yarn) for the dashboard.
- The embedded/IoT layer (`embedded/`) requires physical ESP32/Raspberry Pi hardware and cannot be tested in a software-only environment.

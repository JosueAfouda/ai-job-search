# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python CLI for France-focused job search, scoring, and application tailoring. `main.py` parses CLI options and starts the run. Core behavior lives in `job_search/`: `pipeline.py` orchestrates fetch, normalization, filtering, scoring, and document generation; `models.py` defines shared dataclasses; `cv_loader.py`, `scoring.py`, `tailoring.py`, and `cover_letter.py` own their domain steps. Keep job-board integrations in `job_search/fetchers/` and normalize their output into shared `Job` records before downstream use. JSON schemas belong in `job_search/schemas/`.

Generated run artifacts include `matched_jobs.json`, `job_search_results.md`, `tailored_cvs/`, and `cover_letters/`. Treat them as outputs unless a change intentionally updates a fixture or example.

## Build, Test, and Development Commands

Create an environment and install the only declared dependency set:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run live sources with `python3 main.py`. During development, prefer deterministic local execution:

```bash
python3 main.py --sample --no-llm
python3 main.py --max-per-source 3 --sources france_travail,hellowork
python3 -m py_compile main.py job_search/*.py job_search/fetchers/*.py
```

The sample run avoids live job-board HTML and Codex subprocess variability. The compile command checks syntax and import health before review.

## Coding Style & Naming Conventions

Use Python 3.12-compatible code, four-space indentation, type hints, and `from __future__ import annotations` in typed modules. Follow existing structured records with `@dataclass(slots=True)`. Use `snake_case` for modules and functions, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Keep source-specific parsing inside fetchers instead of leaking board-specific fields into scoring or writers.

## Testing Guidelines

There is no committed automated test suite yet. Add focused tests under `tests/` with `test_*.py` names when behavior changes. Prefer sample jobs or mocked fetchers so tests do not depend on remote sites or Codex availability. At minimum, run sample mode and the `py_compile` command above.

## Commit & Pull Request Guidelines

Recent commits use brief imperative summaries such as `add other jobboards`; keep new messages concise and behavior-focused. Pull requests should describe changed behavior, list verification commands, call out live-source assumptions, and include representative CLI output when reports or tailored documents change.

## Security & Configuration Tips

Do not commit personal CV PDFs or generated application artifacts accidentally. Handle job-board failures and subprocess responses defensively so `--no-llm` remains usable.

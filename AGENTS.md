# Repository Guidelines

## Project Structure & Module Organization

This is a small Python CLI for France-focused job search and CV tailoring. `main.py` is the command-line entry point. Core behavior lives in `job_search/`: `pipeline.py` orchestrates the run, `models.py` defines dataclasses, `cv_loader.py` reads the candidate PDF, `scoring.py` ranks jobs, `tailoring.py` writes tailored markdown CVs, and `llm.py` wraps Codex subprocess calls. Job-board integrations live in `job_search/fetchers/`; shared schemas live in `job_search/schemas/`. Generated outputs are `matched_jobs.json` and `tailored_cvs/`.

## Build, Test, and Development Commands

Create a local environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the full pipeline with the default CV:

```bash
python3 main.py
```

Use deterministic local behavior while developing:

```bash
python3 main.py --sample --no-llm
python3 main.py --max-per-source 3 --sources france_travail,hellowork
```

Check import and syntax health before committing:

```bash
python3 -m py_compile main.py job_search/*.py job_search/fetchers/*.py
```

## Coding Style & Naming Conventions

Use Python 3.12-compatible syntax, four-space indentation, type hints, and `from __future__ import annotations` in modules that define typed APIs. Follow the existing dataclass style with `slots=True` for structured records. Name modules and functions in `snake_case`, classes in `PascalCase`, and constants in `UPPER_SNAKE_CASE`. Keep fetcher-specific parsing inside `job_search/fetchers/` and normalize external data into the shared `Job` model.

## Testing Guidelines

There is no committed test suite yet. For new behavior, add focused tests under a future `tests/` directory using `test_*.py` filenames. Prefer sample-mode or mocked fetchers so tests do not depend on live job boards or Codex availability. At minimum, run `python3 main.py --sample --no-llm` and the `py_compile` command above before opening a PR.

## Commit & Pull Request Guidelines

Git history currently uses a simple initial commit, so keep messages short and imperative, for example `add apec fetcher tests` or `fix cv output paths`. PRs should explain the behavior change, list manual verification commands, mention any live-source assumptions, and include sample output or screenshots when CLI output or generated CV formatting changes.

## Security & Configuration Tips

Do not commit personal CV PDFs, generated `matched_jobs.json`, or tailored CVs unless they are intentional fixtures. Treat live job-board HTML and Codex responses as unstable external inputs; handle failures gracefully and keep `--no-llm` usable.

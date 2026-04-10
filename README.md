# Agentic Job Search

A small Python tool that searches job offers in France, scores them against a candidate CV, keeps strong matches, and generates a tailored markdown CV for each selected job.

The default candidate CV is:

```text
Consultant_Data_Josue_Afouda.pdf
```

## What It Does

Running `python3 main.py` will:

1. Extract text from the CV PDF.
2. Fetch jobs from France-focused sources.
3. Normalize job data into one schema:
   - title
   - company
   - location
   - description
   - URL
4. Score each job from `1.0` to `5.0` using Codex through a subprocess call.
5. Keep only jobs with score `>= 4.0`.
6. Save matching jobs to `matched_jobs.json`.
7. Generate tailored markdown CVs in `tailored_cvs/`.

The current default sources are:

- France Travail
- HelloWork

Apec and Indeed connectors are included and can be enabled with `--sources all`.

## Install

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

You also need the Codex CLI available in your shell:

```bash
codex --help
```

If Codex is not available, you can still run the local heuristic fallback:

```bash
python3 main.py --no-llm
```

## Run

```bash
python3 main.py
```

Useful options:

```bash
python3 main.py --max-per-source 3
python3 main.py --sources france_travail,hellowork
python3 main.py --sources all
python3 main.py --query "Data Engineer Python Azure"
python3 main.py --no-llm
python3 main.py --sample --no-llm
```

## Required Input

The default run expects this file in the repository root:

```text
Consultant_Data_Josue_Afouda.pdf
```

To use another CV:

```bash
python3 main.py --cv path/to/cv.pdf
```

## Outputs

The tool generates:

```text
matched_jobs.json
tailored_cvs/
```

`matched_jobs.json` contains the selected jobs, scores, reasons, links, and tailored CV paths.

Each tailored CV is saved as:

```text
tailored_cvs/<company>_<job_title>.md
```

## Example Output

```text
Agentic Job Search
CV: Consultant_Data_Josue_Afouda.pdf
Query: Data Python
Location: France
Sources: france_travail, hellowork

Fetched jobs: 2
Matched jobs (score >= 4.0): 1

- Data Scientist, expert python, pyspark, Azure - France Travail
  Score: 4.4 (codex)
  Reason: Strong Python, PySpark, Azure, SQL, ML, and consulting match.
  Link: https://candidat.francetravail.fr/offres/recherche/detail/...
  Tailored CV: tailored_cvs/france_travail_data_scientist_expert_python.md

Saved matches: matched_jobs.json
Tailored CV folder: tailored_cvs
```

## Notes

- The tool never submits job applications.
- Codex is called via subprocess from Python.
- If a live job source blocks or changes its HTML, the fetcher fails gracefully and the other sources continue.

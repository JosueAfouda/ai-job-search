#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from job_search.fetchers import DEFAULT_SOURCE_NAMES, FETCHERS
from job_search.pipeline import DEFAULT_QUERY, PipelineOptions, run_pipeline


def parse_args() -> argparse.Namespace:
    default_sources = ",".join(DEFAULT_SOURCE_NAMES)
    parser = argparse.ArgumentParser(
        description="Agentic Job Search System for a France-focused Data & AI consultant."
    )
    parser.add_argument("--cv", default="Consultant_Data_Josue_Afouda.pdf", help="Path to the candidate CV PDF.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Search query sent to job boards.")
    parser.add_argument("--location", default="France", help="Search location.")
    parser.add_argument(
        "--sources",
        default=default_sources,
        help=f"Comma-separated sources: {', '.join(sorted(FETCHERS))}, or all.",
    )
    parser.add_argument("--max-per-source", type=int, default=5, help="Maximum jobs to fetch per source.")
    parser.add_argument("--min-score", type=float, default=4.0, help="Minimum score to keep a job.")
    parser.add_argument(
        "--threshold",
        dest="min_score",
        type=float,
        help="Deprecated alias for --min-score.",
    )
    parser.add_argument("--output", default="matched_jobs.json", help="JSON output path.")
    parser.add_argument("--tailored-dir", default="tailored_cvs", help="Folder for tailored markdown CVs.")
    parser.add_argument("--no-llm", action="store_true", help="Disable Codex subprocess calls and use local fallbacks.")
    parser.add_argument("--sample", action="store_true", help="Use built-in sample jobs instead of live job boards.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = [source.strip() for source in args.sources.split(",") if source.strip()]
    options = PipelineOptions(
        cv_path=Path(args.cv),
        query=args.query,
        location=args.location,
        sources=sources,
        max_per_source=args.max_per_source,
        threshold=args.min_score,
        output_json=Path(args.output),
        tailored_dir=Path(args.tailored_dir),
        use_llm=not args.no_llm,
        sample=args.sample,
    )

    print("Agentic Job Search")
    print(f"CV: {options.cv_path}")
    print(f"Query: {options.query}")
    print(f"Location: {options.location}")
    print(f"Sources: {', '.join(options.sources or [])}")
    print("")

    run = run_pipeline(options)

    if run.errors:
        print("Fetch warnings:")
        for error in run.errors:
            print(f"- {error}")
        print("")

    print(f"Fetched jobs: {len(run.fetched_jobs)}")
    print(f"Matched jobs (score >= {options.threshold:.1f}): {len(run.matched_jobs)}")
    print("")

    if not run.matched_jobs:
        print(f"No jobs met the threshold. Results saved to {options.output_json}.")
        return 0

    for match in run.matched_jobs:
        job = match.job
        score = match.score
        print(f"- {job.title} - {job.company}")
        print(f"  Score: {score.score:.1f} ({score.method})")
        print(f"  Reason: {score.reason}")
        print(f"  Link: {job.url}")
        if match.tailored_cv_path:
            print(f"  Tailored CV: {match.tailored_cv_path}")
        print("")

    print(f"Saved matches: {options.output_json}")
    print(f"Tailored CV folder: {options.tailored_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

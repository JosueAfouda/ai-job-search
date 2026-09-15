#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from job_search.fetchers import DEFAULT_SOURCE_NAMES, FETCHERS
from job_search.pipeline import PipelineOptions, run_pipeline
from job_search.profile import DEFAULT_PROFILE_PATH, load_search_profile
from job_search.cv_loader import resolve_cv_path


def parse_args() -> argparse.Namespace:
    default_sources = ",".join(DEFAULT_SOURCE_NAMES)
    parser = argparse.ArgumentParser(
        description="Recherche et classement des offres selon votre CV et votre positionnement."
    )
    parser.add_argument("--cv", help="CV PDF ; détecté automatiquement si un seul PDF est présent.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE_PATH, help="Profil de recherche JSON.")
    parser.add_argument("--query", help="Remplace les requêtes du profil par une seule recherche.")
    parser.add_argument("--location", help="Localisation ; utilise celle du profil par défaut.")
    parser.add_argument(
        "--sources",
        default=default_sources,
        help=f"Comma-separated sources: {', '.join(sorted(FETCHERS))}, or all.",
    )
    parser.add_argument("--max-per-source", type=int, default=25, help="Maximum jobs to fetch per source.")
    parser.add_argument("--min-score", type=float, default=4.0, help="Minimum score to keep a job.")
    parser.add_argument(
        "--threshold",
        dest="min_score",
        type=float,
        help="Deprecated alias for --min-score.",
    )
    parser.add_argument("--output", default="matched_jobs.json", help="JSON output path.")
    parser.add_argument("--tailored-dir", default="tailored_cvs", help="Folder for tailored markdown CVs.")
    parser.add_argument("--cover-letter-dir", default="cover_letters", help="Folder for tailored markdown cover letters.")
    parser.add_argument("--report", default="job_search_results.md", help="Markdown report output path.")
    parser.add_argument("--no-llm", action="store_true", help="Disable Codex subprocess calls and use local fallbacks.")
    parser.add_argument("--sample", action="store_true", help="Use built-in sample jobs instead of live job boards.")
    args = parser.parse_args()
    if args.max_per_source < 1:
        parser.error("--max-per-source doit être supérieur à zéro.")
    if not 1 <= args.min_score <= 5:
        parser.error("--min-score doit être compris entre 1 et 5.")
    if args.query is not None and not args.query.strip():
        parser.error("--query ne peut pas être vide.")
    return args


def main() -> int:
    args = parse_args()
    try:
        profile = load_search_profile(args.profile)
        cv_path = resolve_cv_path(Path(args.cv) if args.cv else None)
    except (OSError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    sources = [source.strip() for source in args.sources.split(",") if source.strip()]
    options = PipelineOptions(
        cv_path=cv_path,
        query=args.query,
        location=args.location or profile.location,
        sources=sources,
        max_per_source=args.max_per_source,
        threshold=args.min_score,
        output_json=Path(args.output),
        tailored_dir=Path(args.tailored_dir),
        cover_letter_dir=Path(args.cover_letter_dir),
        report_path=Path(args.report),
        use_llm=not args.no_llm,
        sample=args.sample,
        profile_path=args.profile,
    )

    print("Agentic Job Search")
    print(f"CV: {options.cv_path}")
    print(f"Profile: {profile.headline}")
    print(f"Queries: {options.query or '; '.join(profile.queries)}")
    print(f"Location: {options.location}")
    print(f"Sources: {', '.join(options.sources or [])}")
    print("")

    try:
        run = run_pipeline(options)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2

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
        print(f"Tailored CV folder: {options.tailored_dir}")
        print(f"Cover letter folder: {options.cover_letter_dir}")
        print(f"Markdown report: {options.report_path}")
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
        if match.cover_letter_path:
            print(f"  Cover Letter: {match.cover_letter_path}")
        print("")

    print(f"Saved matches: {options.output_json}")
    print(f"Tailored CV folder: {options.tailored_dir}")
    print(f"Cover letter folder: {options.cover_letter_dir}")
    print(f"Markdown report: {options.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

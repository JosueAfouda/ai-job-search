from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from main import parse_args
from job_search.cover_letter import _fallback_cover_letter
from job_search.cv_loader import CandidateProfile, extract_keywords, resolve_cv_path
from job_search.fetchers.base import FetchError, job_from_json_ld
from job_search.models import Job
from job_search.normalizer import normalize_jobs
from job_search.pipeline import PipelineOptions, fetch_jobs, filter_jobs, run_pipeline, sample_jobs
from job_search.profile import has_term, load_search_profile
from job_search.scoring import heuristic_score, score_job
from job_search.tailoring import _fallback_tailored_cv, tailored_cv_filename
from job_search.utils import infer_work_mode


class MatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_search_profile()
        # Synthetic evidence; tests never require the personal PDF or a live service.
        text = "Candidate Test\nSenior Python Engineer\n" + " ".join(self.profile.vocabulary())
        self.candidate = CandidateProfile(text, "Candidate Test", extract_keywords(text), self.profile)
        self.jobs = normalize_jobs(sample_jobs())

    def test_new_roles_match_and_old_or_junior_roles_do_not(self) -> None:
        scores = [heuristic_score(job, self.candidate).score for job in self.jobs]
        self.assertTrue(all(score >= 4 for score in scores[:3]), scores)
        self.assertTrue(all(score < 4 for score in scores[3:]), scores)

    def test_limits_apply_even_when_llm_returns_five(self) -> None:
        codex = Mock()
        codex.run_json.return_value = {"score": 5, "reason": "Excellent"}
        for job in self.jobs[3:]:
            with self.subTest(title=job.title):
                self.assertLess(score_job(job, self.candidate, codex).score, 4)
        prompt = codex.run_json.call_args.args[0]
        self.assertIn(self.profile.headline, prompt)
        self.assertIn('"remote_policy": "any"', prompt)

    def test_invalid_llm_responses_fall_back(self) -> None:
        codex = Mock()
        for value in (float("nan"), float("inf"), True, 7, "4.8"):
            codex.run_json.return_value = {"score": value, "reason": "test"}
            self.assertEqual(score_job(self.jobs[0], self.candidate, codex).method, "heuristic")
        codex.run_json.return_value = {"score": 5, "reason": ""}
        self.assertEqual(score_job(self.jobs[0], self.candidate, codex).method, "heuristic")

    def test_no_llm_never_calls_codex(self) -> None:
        codex = Mock()
        score_job(self.jobs[0], self.candidate, codex, use_llm=False)
        codex.run_json.assert_not_called()

    def test_missing_candidate_skill_cannot_be_assumed(self) -> None:
        candidate = CandidateProfile("SQL Power BI analyst", "Test", ["SQL"], self.profile)
        self.assertLess(heuristic_score(self.jobs[0], candidate).score, 4)

    def test_short_description_is_not_a_confirmed_match(self) -> None:
        job = replace(self.jobs[0], description="Python LLM FastAPI Docker SQL")
        codex = Mock()
        codex.run_json.return_value = {"score": 5, "reason": "Test"}
        self.assertLess(score_job(job, self.candidate, codex).score, 4)

    def test_mentoring_juniors_does_not_make_role_junior(self) -> None:
        job = replace(self.jobs[0], description=self.jobs[0].description + " Encadrer les développeurs junior.")
        self.assertGreaterEqual(heuristic_score(job, self.candidate).score, 4)

    def test_other_positioning_needs_no_python_code_change(self) -> None:
        profile = replace(self.profile, headline="Data Analyst", queries=["Data Analyst"],
                          target_roles=["Data Analyst"], required_skills=["SQL"],
                          priority_skills={"Analyse": ["Power BI", "DAX", "Tableau"]},
                          supporting_skills=["Excel", "reporting"], excluded_titles=[], seniority="any")
        text = "SQL Power BI DAX Tableau Excel reporting"
        candidate = CandidateProfile(text, "Test", extract_keywords(text, terms=profile.vocabulary()), profile)
        job = Job("Data Analyst", "Test", "France", text + " pour analyser les indicateurs et construire les tableaux de bord de nos équipes métier.", "https://example.com/analyst", "test")
        self.assertGreaterEqual(heuristic_score(job, candidate).score, 4)
        self.assertNotIn("Python", _fallback_tailored_cv(job, candidate))
        self.assertNotIn("Python", _fallback_cover_letter(job, "", candidate))

    def test_term_boundaries_and_accents(self) -> None:
        self.assertTrue(has_term("Développeur  PYTHON confirmé", "developpeur python"))
        self.assertFalse(has_term("Rapid business intelligence", "API"))
        self.assertFalse(has_term("SQLAlchemy", "SQL"))
        self.assertEqual(extract_keywords("SQLAlchemy", terms=["SQL", "SQLAlchemy"]), ["SQLAlchemy"])

    def test_generated_documents_use_candidate_evidence(self) -> None:
        candidate = CandidateProfile("Test\nPython et SQL", "Test", ["Python", "SQL"], self.profile)
        job = replace(self.jobs[0], description="Python Kubernetes LangChain Power BI SQL")
        cv = _fallback_tailored_cv(job, candidate)
        letter = _fallback_cover_letter(job, cv, candidate)
        for content in (cv, letter):
            self.assertNotIn("Kubernetes", content)
            self.assertNotIn("LangChain", content)
            self.assertNotIn("Power BI", content)
            self.assertNotIn("10+", content)
        self.assertLessEqual(len(letter), 1000)

    def test_all_work_modes_are_accepted_by_default(self) -> None:
        for mode in ("remote", "hybrid", "onsite", "unknown"):
            self.assertGreaterEqual(heuristic_score(replace(self.jobs[0], work_mode=mode), self.candidate).score, 4)

    def test_optional_remote_requirement(self) -> None:
        candidate = replace(self.candidate, search_profile=replace(self.profile, remote_policy="required"))
        self.assertLess(heuristic_score(replace(self.jobs[0], work_mode="hybrid"), candidate).score, 4)
        self.assertGreaterEqual(heuristic_score(replace(self.jobs[0], work_mode="remote"), candidate).score, 4)

    def test_json_ld_remote_and_text_hybrid_are_normalized(self) -> None:
        job = job_from_json_ld({"title": "Python", "jobLocationType": "TELECOMMUTE"}, "https://example.com", "test")
        self.assertEqual(job.work_mode, "remote")
        self.assertEqual(self.jobs[1].work_mode, "hybrid")

    def test_documents_for_distinct_offers_do_not_overwrite(self) -> None:
        other = replace(self.jobs[0], url="https://example.com/another-offer")
        self.assertNotEqual(tailored_cv_filename(self.jobs[0]), tailored_cv_filename(other))

    def test_work_mode_variants(self) -> None:
        self.assertEqual(infer_work_mode("Télétravail à 100%"), "remote")
        self.assertEqual(infer_work_mode("Poste sur site à Lyon"), "onsite")
        self.assertEqual(infer_work_mode("No remote. Full remote not available."), "onsite")

    def test_cv_auto_detection_refuses_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                resolve_cv_path(directory=root)
            (root / "new.PDF").touch()
            self.assertEqual(resolve_cv_path(directory=root), root / "new.PDF")
            (root / "old.pdf").touch()
            with self.assertRaises(ValueError):
                resolve_cv_path(directory=root)
            self.assertEqual(resolve_cv_path(root / "new.PDF"), root / "new.PDF")

    def test_profile_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            for key, value in (("queries", []), ("queries", [""]), ("priority_skills", []),
                               ("remote_policy", "sometimes"), ("max_job_age_days", -1)):
                payload = asdict(self.profile)
                payload[key] = value
                path.write_text(json.dumps(payload))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    load_search_profile(path)

    def test_queries_are_balanced_bounded_and_fail_independently(self) -> None:
        fetcher = Mock(source="Test")
        def search(query: str, location: str, limit: int) -> list[Job]:
            if query == "broken":
                raise FetchError("unavailable")
            return [replace(self.jobs[0], url=f"https://example.com/{query}/{index}") for index in range(limit)]
        fetcher.search.side_effect = search
        profile = replace(self.profile, queries=["first", "broken", "last"])
        with patch("job_search.pipeline.build_fetchers", return_value=[fetcher]):
            jobs, errors = fetch_jobs(PipelineOptions(max_per_source=3), profile)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(fetcher.search.call_count, 3)
        self.assertIn("last", jobs[1].url)
        self.assertEqual(len(errors), 1)

    def test_source_budget_and_duplicate_queries(self) -> None:
        fetcher = Mock(source="Test")
        fetcher.search.return_value = self.jobs[:3]
        with patch("job_search.pipeline.build_fetchers", return_value=[fetcher]):
            jobs, _ = fetch_jobs(PipelineOptions(max_per_source=2), self.profile)
        self.assertLessEqual(len(jobs), 2)
        self.assertEqual(len({job.url for job in jobs}), len(jobs))

    def test_query_override_replaces_profile_queries(self) -> None:
        fetcher = Mock(source="Test")
        fetcher.search.return_value = []
        with patch("job_search.pipeline.build_fetchers", return_value=[fetcher]):
            fetch_jobs(PipelineOptions(query="custom", location="Lyon", max_per_source=3), self.profile)
        fetcher.search.assert_called_once_with("custom", "Lyon", 3)

    def test_duplicate_url_with_different_title_is_removed(self) -> None:
        self.assertEqual(len(normalize_jobs([self.jobs[0], replace(self.jobs[0], title="Different title")])), 1)

    def test_salary_age_filters_and_freelance_rate(self) -> None:
        current = date(2026, 9, 15)
        old = replace(self.jobs[0], raw={"date": "2026-08-01"})
        low = replace(self.jobs[0], raw={"salary_text": "35 000 EUR annuel"})
        freelance = replace(self.jobs[0], description=self.jobs[0].description + " TJM 650 EUR/jour en France.")
        self.assertEqual(filter_jobs([old, low, freelance], today=current), [freelance])
        low_with_days = replace(self.jobs[0], description="35 000 EUR annuel, un jour de télétravail par semaine.")
        self.assertEqual(filter_jobs([low_with_days], today=current), [])
        self.assertEqual(filter_jobs([old, low], today=current, max_age_days=90, min_salary=30000), [old, low])

    def test_sample_pipeline_writes_sorted_matches_and_documents_without_llm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = PipelineOptions(cv_path=root / "cv.pdf", sample=True, use_llm=False,
                                      output_json=root / "matches.json", report_path=root / "report.md",
                                      tailored_dir=root / "cvs", cover_letter_dir=root / "letters")
            with patch("job_search.pipeline.load_cv", return_value=self.candidate), \
                 patch("job_search.llm.CodexClient.run_text") as llm:
                run = run_pipeline(options)
            llm.assert_not_called()
            self.assertEqual(len(run.matched_jobs), 3)
            scores = [match.score.score for match in run.matched_jobs]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertEqual(len(json.loads(options.output_json.read_text())), 3)
            self.assertTrue(options.report_path.exists())
            for match in run.matched_jobs:
                self.assertTrue(Path(match.tailored_cv_path).exists())
                self.assertTrue(Path(match.cover_letter_path).exists())

    def test_cli_defaults_and_legacy_threshold(self) -> None:
        with patch("sys.argv", ["main.py"]):
            args = parse_args()
        self.assertIsNone(args.cv)
        self.assertIsNone(args.query)
        self.assertEqual(args.min_score, 4.0)
        with patch("sys.argv", ["main.py", "--threshold", "4.5"]):
            self.assertEqual(parse_args().min_score, 4.5)


if __name__ == "__main__":
    unittest.main()

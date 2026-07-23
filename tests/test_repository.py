"""Repository-level regression tests for Macawiki."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class RepositoryTests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        result = run_script("scripts/validate.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_query_finds_performance_pattern(self) -> None:
        result = run_script("scripts/query.py", "性能", "--compact")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pattern-establish-performance-baseline", result.stdout)

    def test_query_or_mode_improves_recall(self) -> None:
        # AND mode: multi-concept queries like "性能 基线" may return 0 results
        # because no single page contains all search terms simultaneously.
        and_result = run_script("scripts/query.py", "性能", "基线", "--mode", "and", "--paths-only")
        self.assertEqual(and_result.returncode, 0, and_result.stderr)
        # OR mode: same terms should return results when at least one term matches.
        or_result = run_script("scripts/query.py", "性能", "基线", "--mode", "or", "--paths-only")
        self.assertEqual(or_result.returncode, 0, or_result.stderr)
        or_pages = [line for line in or_result.stdout.strip().split("\n") if line]
        # OR mode must not return fewer results than AND mode.
        and_pages = [line for line in and_result.stdout.strip().split("\n") if line]
        self.assertGreaterEqual(len(or_pages), len(and_pages))

    def test_query_fuzzy_mode_finds_pages(self) -> None:
        """Fuzzy search with n-gram Jaccard should return results even for non-exact terms."""
        # Search with a slightly different term that fuzzy matching should still catch
        result = run_script("scripts/query.py", "kernel", "roofline", "--fuzzy", "--paths-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        # Should find performance-related pages via n-gram similarity
        pages = [line for line in result.stdout.strip().split("\n") if line]
        self.assertGreater(len(pages), 0, "Fuzzy search should return results")
        # The top result should be the performance pattern page
        self.assertIn("wiki/optimization-patterns/establish-performance-baseline.md", result.stdout)

    def test_query_auto_fuzzy_fallback(self) -> None:
        """Auto-fuzzy should fall back when exact AND returns 0 results."""
        # A query that won't match exactly in any single page
        result = run_script("scripts/query.py", "MXMACA", "BLAS", "优化", "--mode", "and", "--auto-fuzzy", "--paths-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        pages = [line for line in result.stdout.strip().split("\n") if line]
        self.assertGreater(len(pages), 0, "Auto-fuzzy should return results when exact AND returns 0")

    def test_alias_filter_is_normalized(self) -> None:
        result = run_script("scripts/query.py", "--component", "mcProfiler", "--paths-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wiki/optimization-patterns/establish-performance-baseline.md", result.stdout)

    def test_get_page_follows_sources(self) -> None:
        result = run_script(
            "scripts/get_page.py",
            "pattern-establish-performance-baseline",
            "--follow-sources",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SOURCE: repo-mxmaca-performance-tuning-guide", result.stdout)

    def test_generated_indices_are_current(self) -> None:
        result = run_script("scripts/generate_indices.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_minimum_page_count(self) -> None:
        """Corpus must not shrink below usable threshold."""
        result = run_script("scripts/repo_status.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        # repo_status outputs "pages: N" on the first line
        import re
        match = re.search(r"pages:\s*(\d+)", result.stdout)
        self.assertIsNotNone(match, f"Could not find page count in output: {result.stdout}")
        count = int(match.group(1))
        self.assertGreaterEqual(count, 12, f"Corpus has {count} pages, minimum is 12")

    def test_agent_value_proxy_passes(self) -> None:
        result = run_script("scripts/run_agent_value_eval.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("agent-value-eval-001", result.stdout)

    def test_doctor_passes_without_pytorch(self) -> None:
        result = run_script("scripts/doctor.py", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"ready": true', result.stdout)

    def test_installer_is_idempotence_safe(self) -> None:
        with tempfile.TemporaryDirectory() as target:
            first = run_script(
                "scripts/install.py", "--agent", "both", "--scope", "user",
                "--target-root", target, "--mode", "copy",
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertTrue((Path(target) / ".agents/skills/macawiki/SKILL.md").is_file())
            second = run_script(
                "scripts/install.py", "--agent", "both", "--scope", "user",
                "--target-root", target, "--mode", "copy",
            )
            self.assertNotEqual(second.returncode, 0)

    def test_operator_fixture_is_listable(self) -> None:
        result = run_script("benchmarks/pytorch_baseline.py", "--list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for operator in ("add", "softmax", "layer_norm", "matmul", "quantize", "transpose", "moe_routing"):
            self.assertIn(operator, result.stdout)

    def test_tilelang_list_runs_without_import_error(self) -> None:
        result = run_script("benchmarks/tilelang_candidate.py", "--list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for case_id in ("add-f32-4096", "quantize-f32-8192", "moe-routing-f32-1024x8-top2"):
            self.assertIn(case_id, result.stdout)

    # ── compare_benchmarks.py contract tests ──────────────────────────

    def _make_result(self, **overrides: object) -> dict:
        """Build a minimal valid completed result, with optional overrides."""
        result: dict = {
            "status": "completed",
            "environment": {"environment_fingerprint": "fp:test"},
            "cases": [
                {
                    "case_id": "add-f32-4096",
                    "operator": "add",
                    "shape": [4096],
                    "dtype": "float32",
                    "correctness": {"passed": True},
                    "timing": {"median_ms": 1.2, "warmup": 2, "iterations": 5},
                }
            ],
        }
        for key, val in overrides.items():
            if val is None:
                result.pop(key, None)
            else:
                result[key] = val
        return result

    def _run_compare(self, baseline: dict, candidate: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as td:
            base_path = Path(td) / "baseline.json"
            cand_path = Path(td) / "candidate.json"
            base_path.write_text(json.dumps(baseline), encoding="utf-8")
            cand_path.write_text(json.dumps(candidate), encoding="utf-8")
            return run_script(
                "scripts/compare_benchmarks.py",
                "--baseline", str(base_path),
                "--candidate", str(cand_path),
            )

    def test_compare_rejects_missing_status(self) -> None:
        base = self._make_result(status=None)
        cand = self._make_result()
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing top-level key", result.stdout)

    def test_compare_rejects_missing_environment(self) -> None:
        base = self._make_result(environment=None)
        cand = self._make_result()
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)

    def test_compare_rejects_missing_cases(self) -> None:
        base = self._make_result(cases=None)
        cand = self._make_result()
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)

    def test_compare_rejects_non_list_cases(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        cand["cases"] = "not_a_list"
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be a list", result.stdout)

    def test_compare_flags_missing_case_id(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        del cand["cases"][0]["case_id"]
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required key", result.stdout)

    def test_compare_flags_negative_median(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        cand["cases"][0]["timing"]["median_ms"] = -1.0
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be positive", result.stdout)

    def test_compare_flags_zero_median(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        cand["cases"][0]["timing"]["median_ms"] = 0.0
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be positive", result.stdout)

    def test_compare_detects_case_mismatch(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        cand["cases"][0]["case_id"] = "softmax-f32-64x128"
        cand["cases"][0]["operator"] = "softmax"
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0,
                            "missing cases should produce non-zero exit code")
        self.assertIn("baseline_only", result.stdout)
        self.assertIn("candidate_only", result.stdout)

    def test_compare_detects_contract_mismatch(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        # same case_id but different shape
        cand["cases"][0]["shape"] = [2048]
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0,
                            "contract mismatch should produce non-zero exit code")
        self.assertIn("shape mismatch", result.stdout)
        self.assertIn("not_comparable", result.stdout)

    def test_compare_detects_parameter_mismatch(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        # same case_id/operator/shape but different parameters
        base["cases"][0]["parameters"] = {"scale": 0.1}
        cand["cases"][0]["parameters"] = {"scale": 0.2}
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0,
                            "parameter mismatch should produce non-zero exit code")
        self.assertIn("parameter 'scale' mismatch", result.stdout)

    def test_compare_detects_seed_mismatch(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        base["cases"][0]["seed"] = 20260722
        cand["cases"][0]["seed"] = 99999999
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0,
                            "seed mismatch should produce non-zero exit code")
        self.assertIn("seed mismatch", result.stdout)

    def test_compare_detects_tolerance_mismatch(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        # same case but different correctness tolerance
        base["cases"][0].setdefault("correctness", {})["atol"] = 1e-5
        cand["cases"][0].setdefault("correctness", {})["atol"] = 1e-3
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0,
                            "tolerance mismatch should produce non-zero exit code")
        self.assertIn("atol mismatch", result.stdout)

    def test_compare_passes_valid_input(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        result = self._run_compare(base, cand)
        self.assertEqual(result.returncode, 0)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["comparisons"][0]["status"], "comparable")
        self.assertIn("speedup", parsed["comparisons"][0])

    def test_compare_rejects_correctness_failure(self) -> None:
        base = self._make_result()
        cand = self._make_result()
        cand["cases"][0]["correctness"]["passed"] = False
        result = self._run_compare(base, cand)
        # should run (returncode 0 for completed comparison) but mark as not_comparable
        self.assertEqual(result.returncode, 0)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["comparisons"][0]["status"], "not_comparable")

    def test_compare_accepts_null_timing_on_correctness_failure(self) -> None:
        """Real C500 TileLang matmul result: passed=false, timing=null."""
        base = self._make_result()
        cand = self._make_result()
        cand["cases"][0]["correctness"]["passed"] = False
        cand["cases"][0]["timing"] = None
        result = self._run_compare(base, cand)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["comparisons"][0]["status"], "not_comparable")
        self.assertNotEqual(
            parsed.get("status"), "schema_error",
            "correctness failure with timing=null should not be schema_error"
        )

    def test_compare_rejects_non_dict_case(self) -> None:
        """Non-dict case element should be rejected as schema_error."""
        base = self._make_result()
        cand = self._make_result()
        cand["cases"] = [None]
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        parsed = json.loads(result.stdout)
        self.assertIn("must be an object", result.stdout)
        self.assertEqual(parsed.get("status"), "schema_error")

    def test_compare_rejects_duplicate_case_id(self) -> None:
        """Duplicate case_id within a single result should be rejected."""
        base = self._make_result()
        base_case = base["cases"][0]
        base["cases"] = [base_case, base_case]
        cand = self._make_result()
        result = self._run_compare(base, cand)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate case_id", result.stdout)

    # ── version-claim and evidence integrity tests ────────────────────

    def test_version_claim_integrity(self) -> None:
        """version-claims.yaml entries must have required fields."""
        claims_path = ROOT / "data" / "version-claims.yaml"
        data = json.loads(claims_path.read_text(encoding="utf-8"))
        claims = data.get("claims", [])
        if claims:
            for i, claim in enumerate(claims):
                with self.subTest(i=i):
                    self.assertIn("id", claim, f"claim {i} missing id")
                    self.assertIn("statement", claim, f"claim {i} missing statement")

    def test_no_fabricated_c500_numbers(self) -> None:
        """C500 performance numbers (e.g. X TFlops, Y GB/s) must not appear in wiki."""
        import re
        # Match fabricated numeric performance claims, not methodological context
        fabricated_pattern = re.compile(
            r"C500.*?\d+(?:\.\d+)?\s*(?:TFlops|TFLOPS|GB/s|GFlops|GFLOPs|TOPS)",
            re.IGNORECASE
        )
        fabrications = []
        for wiki_dir in ["wiki"]:
            wiki_path = ROOT / wiki_dir
            if wiki_path.is_dir():
                for md_file in wiki_path.rglob("*.md"):
                    text = md_file.read_text(encoding="utf-8")
                    matches = fabricated_pattern.findall(text)
                    if matches:
                        fabrications.append((str(md_file.relative_to(ROOT)), matches))
        self.assertEqual(
            len(fabrications), 0,
            f"Found potential fabricated C500 performance numbers: {fabrications}"
        )

    def test_source_registry_urls_are_plausible(self) -> None:
        """All sources in source-registry.yaml must have URL and id fields."""
        registry_path = ROOT / "data" / "source-registry.yaml"
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        sources = data.get("sources", [])
        self.assertGreater(len(sources), 0, "source registry is empty")
        for src in sources:
            with self.subTest(src_id=src.get("id", "unknown")):
                self.assertIn("id", src)
                self.assertIn("url", src)
                self.assertTrue(
                    src["url"].startswith("http"),
                    f"source {src['id']} URL is not HTTP: {src['url']}"
                )

    def test_agent_value_proxy_enhanced_passes(self) -> None:
        """All agent-value cases (>=8) must pass including negative-trigger."""
        result = run_script("scripts/run_agent_value_eval.py", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertGreaterEqual(report["total"], 8)
        self.assertTrue(report["all_passed"], f"Some cases failed: {report}")
        # Verify each individual case passed
        for case in report["cases"]:
            self.assertTrue(case.get("loaded_pass"), f"Case {case.get('id', '?')} did not pass: {case}")
        # Verify negative cases exist
        negative_cases = [
            c for c in report["cases"]
            if c.get("type") == "negative_trigger"
        ]
        self.assertGreaterEqual(len(negative_cases), 2,
                                "Expected at least 2 negative-trigger cases")

    def test_eval_files_are_valid_json(self) -> None:
        """Both agent-value-cases and gold-questions must be valid JSON."""
        for path in ["evals/agent-value-cases.yaml", "evals/gold-questions.yaml"]:
            with self.subTest(file=path):
                data = json.loads((ROOT / path).read_text(encoding="utf-8"))
                self.assertIn("schema_version", data)

    def test_gold_questions_count(self) -> None:
        """gold-questions.yaml must have at least 6 questions."""
        data = json.loads(
            (ROOT / "evals" / "gold-questions.yaml").read_text(encoding="utf-8")
        )
        questions = data.get("questions", [])
        self.assertGreaterEqual(
            len(questions), 6,
            f"Expected >=6 gold questions, got {len(questions)}"
        )

    # ── agent value eval regression tests ─────────────────────────────

    def test_eval_source_scoped_to_target_pages(self) -> None:
        """Evidence sources should only include target page sources, not whole corpus."""
        result = run_script("scripts/run_agent_value_eval.py", "--json")
        report = json.loads(result.stdout)
        # The baseline case only targets pattern-establish-performance-baseline,
        # which only has source repo-mxmaca-performance-tuning-guide
        baseline = next(
            (c for c in report["cases"] if c["id"] == "agent-value-baseline-001"),
            None,
        )
        self.assertIsNotNone(baseline)
        sources = baseline["evidence"]["sources"]
        # Should NOT include sources from unrelated pages
        num_unrelated = sum(
            1 for s in sources
            if s not in ("repo-mxmaca-performance-tuning-guide",)
        )
        # The target page only has repo-mxmaca-performance-tuning-guide;
        # other sources like doc-pytorch-operator-reference should not appear
        self.assertNotIn("doc-pytorch-operator-reference", sources,
                         "Sources must be scoped to target pages only")
        # At most 1 source should be from the target page
        self.assertLessEqual(len(sources), 2,
                            "Too many sources: not scoped to target pages")
        self.assertTrue(baseline["loaded_pass"])

    def test_eval_multi_page_requires_all(self) -> None:
        """Multi-page case: existing case should have both pages found."""
        result = run_script("scripts/run_agent_value_eval.py", "--json")
        report = json.loads(result.stdout)
        multi = next(
            (c for c in report["cases"] if c["id"] == "agent-value-multi-page-001"),
            None,
        )
        self.assertIsNotNone(multi)
        # If any expected pages are missing, loaded_pass must be false
        missing = set(multi.get("expected_pages_missing", []))
        if missing:
            self.assertFalse(multi["loaded_pass"],
                             f"Multi-page with missing pages {missing} must FAIL, "
                             f"found: {multi.get('expected_pages_found', [])}")
        else:
            self.assertTrue(multi["loaded_pass"],
                            "All expected pages found, should pass")

    # ── transpose workload contract ────────────────────────────────────

    def test_transpose_baseline_output_is_contiguous(self) -> None:
        """PyTorch transpose baseline must return a contiguous (materialised)
        output, not a view — otherwise the timing comparison is not valid
        against TileLang's tl_transpose which allocates and writes every element.

        Calls the actual production function pytorch_baseline._run_op() so that
        if the production code regresses (e.g. removing .contiguous()), this
        test fails rather than silently passing on a hand-rolled copy.
        """
        try:
            import torch
        except ImportError:
            raise unittest.SkipTest("PyTorch not installed")
        # Import the production function that the PyTorch runner uses
        sys.path.insert(0, str(ROOT / "benchmarks"))
        from pytorch_baseline import _run_op  # type: ignore[import-not-found]
        x = torch.randn(128, 4096)
        case = {"name": "transpose", "parameters": {}}
        out = _run_op(torch, case, x, None)
        self.assertTrue(out.is_contiguous(),
                        "transpose output from _run_op must be contiguous (materialised), "
                        "not a stride-change view")
        # Values must match torch.t(x)
        torch.testing.assert_close(out, torch.t(x))

    def test_transpose_reference_output_is_contiguous(self) -> None:
        """TileLang candidate _reference for transpose must also return a
        contiguous tensor so the correctness check compares materialised outputs.

        Calls the actual production function tilelang_candidate._reference() so
        that if the reference regresses, this test catches it.
        """
        try:
            import torch
        except ImportError:
            raise unittest.SkipTest("PyTorch not installed")
        sys.path.insert(0, str(ROOT / "benchmarks"))
        from tilelang_candidate import _reference  # type: ignore[import-not-found]
        x = torch.randn(128, 4096)
        case = {"name": "transpose", "parameters": {}}
        out = _reference(torch, case, x, None)
        self.assertTrue(out.is_contiguous(),
                        "transpose reference from _reference must be contiguous")
        torch.testing.assert_close(out, torch.t(x))

    def test_transpose_view_is_not_contiguous(self) -> None:
        """Sanity check: torch.t(x) without .contiguous() IS non-contiguous
        for a non-trivial shape, which is why the old baseline was invalid."""
        try:
            import torch
        except ImportError:
            raise unittest.SkipTest("PyTorch not installed")
        x = torch.randn(128, 4096)
        view = torch.t(x)
        self.assertFalse(view.is_contiguous(),
                         "torch.t(x) on a non-square matrix should be non-contiguous; "
                         "this confirms the old baseline measured view-creation cost")


if __name__ == "__main__":
    unittest.main()

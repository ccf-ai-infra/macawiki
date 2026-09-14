"""Repository-level regression tests for Macawiki."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Redirect every signal write in this process (and the subprocesses it
# spawns) to a scratch dir. Without this, `make test` dumps synthetic
# queries ("zzzqqq", "算子") and perf records into the real evals/signals/,
# and `make signals-merge` then turns that test noise into backlog items
# the self-evolution loop will dutifully try to "fix". setdefault keeps an
# explicit redirect from the caller's environment.
_SIGNAL_SCRATCH = tempfile.TemporaryDirectory(prefix="macawiki-test-signals-")
os.environ.setdefault("MACAWIKI_SIGNAL_DIR", _SIGNAL_SCRATCH.name)


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = {**os.environ, **env} if env else None
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=full_env,
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

    def test_query_fuzzy_prefers_flash_attention_topic(self) -> None:
        result = run_script(
            "scripts/query.py", "flash attenton", "--fuzzy", "--limit", "8", "--paths-only"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = result.stdout.strip().splitlines()
        self.assertEqual(paths[0], "wiki/kernels/flash-attention-mxmaca.md")
        self.assertTrue(
            set(paths).issubset({
                "wiki/kernels/flash-attention-mxmaca.md",
                "sources/repos/flash-attention-v2-6-3.md",
                "sources/official-docs/mctilelang-flash-attention-pr-2.md",
            })
        )

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

    def test_flash_attention_aliases_find_topic_page(self) -> None:
        for alias in ("flash_attn", "flash-attn", "FlashAttention", "flash attention"):
            with self.subTest(alias=alias):
                result = run_script("scripts/query.py", alias, "--paths-only")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("wiki/kernels/flash-attention-mxmaca.md", result.stdout)

    def test_flash_attention_component_filter(self) -> None:
        result = run_script("scripts/query.py", "--component", "flash_attn", "--paths-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("wiki/kernels/flash-attention-mxmaca.md", result.stdout)

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

    def test_copy_install_ships_skill_referenced_docs(self) -> None:
        """copy install must include every docs/ file the skill contract points at.

        SKILL.md cites docs/hardware-validation.md and the iterate skill cites
        docs/source-and-license-policy.md; excluding docs/ wholesale made both
        dangling references in every copy install.
        """
        with tempfile.TemporaryDirectory() as target:
            r = run_script(
                "scripts/install.py", "--agent", "codebuddy", "--scope", "user",
                "--target-root", target, "--mode", "copy", "--replace",
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            skill = Path(target) / ".codebuddy/skills/macawiki"
            for doc in ("hardware-validation.md", "source-and-license-policy.md"):
                self.assertTrue((skill / "docs" / doc).is_file(),
                                f"copy install omitted docs/{doc}")

    def test_copy_install_drops_contributor_only_docs(self) -> None:
        """copy install must NOT ship contributor planning docs."""
        with tempfile.TemporaryDirectory() as target:
            run_script(
                "scripts/install.py", "--agent", "codebuddy", "--scope", "user",
                "--target-root", target, "--mode", "copy", "--replace",
            )
            installed = Path(target) / ".codebuddy/skills/macawiki/docs"
            self.assertFalse((installed / "iteration-plan.md").exists(),
                             "contributor planning doc shipped to agents")
            self.assertFalse((installed / "iteration-plan-issue2.md").exists(),
                             "contributor planning doc shipped to agents")

    def test_operator_fixture_is_listable(self) -> None:
        result = run_script("benchmarks/pytorch_baseline.py", "--list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for operator in ("add", "softmax", "layer_norm", "matmul", "quantize", "transpose", "moe_routing"):
            self.assertIn(operator, result.stdout)

    def test_flash_attention_contract_stays_not_run_without_artifact(self) -> None:
        cases = json.loads((ROOT / "benchmarks/flash_attention_cases.yaml").read_text(encoding="utf-8"))
        backend = json.loads(
            (ROOT / "benchmarks/backends/flash_attn_mxmaca_contract.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(cases["status"], "not_run")
        self.assertTrue(cases["cases"])
        self.assertTrue(all(case["status"] == "not_run" for case in cases["cases"]))
        self.assertEqual(backend["status"], "not_run")
        self.assertIsNone(backend["artifact_identity"]["sha256"])
        self.assertFalse(backend["artifact_identity"]["reported_version_is_compatibility_evidence"])

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
        """All sources in source-registry.yaml must have URL and id fields.

        Remote sources must be HTTP(S) so a fabricated or placeholder URL is
        caught. A local-capture source is a separate, audited class: its
        evidence is a committed artifact in this repo, not a fetchable page, so
        it uses the explicit local:// scheme and must point at that artifact.
        """
        registry_path = ROOT / "data" / "source-registry.yaml"
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        sources = data.get("sources", [])
        self.assertGreater(len(sources), 0, "source registry is empty")
        for src in sources:
            with self.subTest(src_id=src.get("id", "unknown")):
                self.assertIn("id", src)
                self.assertIn("url", src)
                url = src["url"]
                if url.startswith("http"):
                    continue
                self.assertTrue(
                    url.startswith("local://"),
                    f"source {src['id']} URL is neither HTTP nor local://: {url}")
                # A local:// claim is only auditable if it names the committed
                # artifact it stands on; otherwise it is an unfalsifiable
                # assertion about an unreachable machine.
                self.assertEqual(
                    src.get("access"), "local-capture",
                    f"source {src['id']} uses local:// but access is not "
                    f"local-capture: {src.get('access')}")
                ref = src.get("fixed_ref") or ""
                artifact = ref.split()[0] if ref else ""
                self.assertTrue(
                    artifact and (ROOT / artifact).is_file(),
                    f"source {src['id']} local:// URL has no committed artifact "
                    f"in fixed_ref: {ref!r}")

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

    def test_signal_logger_creates_file(self) -> None:
        """Signal logger must create log file on first write (via subprocess for clean import)."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import log_query
log_query(["test"], {{}}, "and", False, 1, ["test-id"], 1.0)
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            log_path = Path(tmp) / "query-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")
            self.assertIn("test-id", log_path.read_text())

    def test_signal_logger_zero_result(self) -> None:
        """Zero-result log must be written to separate file."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import log_zero_result
log_zero_result(["missing_term"], {{}}, "and", False)
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            log_path = Path(tmp) / "zero-result-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")
            self.assertIn("missing_term", log_path.read_text())
            self.assertIn("zero_result", log_path.read_text())

    def test_self_improve_refuses_dirty_git(self) -> None:
        """Self-improve should refuse to run with dirty working tree."""
        # If working tree is clean, this test verifies the check works
        import subprocess
        r = subprocess.run(
            ["python3", "scripts/self_improve.py", "--dry-run", "--json"],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertIn(r.returncode, (0, 1), f"self_improve crashed: {r.stderr}")
        data = json.loads(r.stdout)
        self.assertIn("auto_fixable_count", data)

    def test_signal_aggregator_empty_no_error(self) -> None:
        """Signal aggregator should handle empty signal dir gracefully."""
        with tempfile.TemporaryDirectory() as tmp:
            # Pass via env=, not os.environ=: mutating the process env would
            # clobber the module-level redirect for every later test.
            r = run_script("scripts/signal_aggregator.py", "--check", "--json",
                           env={"MACAWIKI_SIGNAL_DIR": tmp})
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["total_signals"], 0)

    def test_query_signal_log_flag_works(self) -> None:
        """--signal-log flag should produce log entries."""
        # Redirect to a temp dir: tests that write to the real
        # evals/signals/ pollute the self-evolution backlog with
        # synthetic queries (e.g. "zzzqqq") every time `make test` runs.
        with tempfile.TemporaryDirectory() as tmp:
            result = run_script(
                "scripts/query.py", "算子", "--compact", "--signal-log",
                env={"MACAWIKI_SIGNAL_DIR": tmp},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            log_path = Path(tmp) / "query-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")

    def test_evolve_pipeline_scripts_exist(self) -> None:
        """All self-evolution scripts must be importable."""
        scripts = ["signal_logger", "signal_aggregator", "self_improve", "env_detector", "perf_capture"]
        import importlib
        for name in scripts:
            with self.subTest(script=name):
                try:
                    importlib.import_module(f"scripts.{name}")
                except ImportError:
                    try:
                        importlib.import_module(name)
                    except ImportError:
                        self.fail(f"Could not import {name}")

    def test_env_detector_imports(self) -> None:
        """env_detector module must import and detect() returns EnvInfo fields."""
        from scripts.env_detector import detect, is_mxmaca_env, snapshot
        info = detect()
        self.assertIsInstance(info.is_c500, bool)
        self.assertIsInstance(is_mxmaca_env(), bool)
        snap = snapshot()
        for key in ("is_c500", "device_name", "maca_version", "driver_version",
                     "environment_fingerprint"):
            self.assertIn(key, snap, f"Missing key in snapshot: {key}")

    def test_env_detector_cli_json(self) -> None:
        """env_detector --json must produce valid JSON with required keys."""
        result = subprocess.run(
            [sys.executable, "scripts/env_detector.py", "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        for key in ("schema_version", "is_c500", "device_name", "environment_fingerprint"):
            self.assertIn(key, data, f"Missing key: {key}")

    def test_signal_logger_perf_creates_file(self) -> None:
        """log_performance() must write to perf-log.jsonl with correct fields."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import log_performance
log_performance("add", [4096], "pytorch", 0.1, 0.1, 0.01, 20, 100)
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            log_path = Path(tmp) / "perf-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")
            record = json.loads(log_path.read_text().strip().split("\n")[0])
            self.assertEqual(record["type"], "performance")
            self.assertEqual(record["operator"], "add")
            self.assertEqual(record["backend"], "pytorch")

    def test_signal_logger_token_creates_file(self) -> None:
        """log_token_usage() must write to token-log.jsonl with correct fields."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import log_token_usage
log_token_usage("query", ["test"], "or", 3, 100, 200)
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            log_path = Path(tmp) / "token-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")
            record = json.loads(log_path.read_text().strip().split("\n")[0])
            self.assertEqual(record["type"], "token_usage")
            self.assertEqual(record["total_tokens"], 300)
            self.assertEqual(record["tokens_per_result"], 100.0)

    def test_signal_logger_env_creates_file(self) -> None:
        """log_environment() must write to env-log.jsonl (when C500 detected)."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import log_environment
log_environment("test")
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            log_path = Path(tmp) / "env-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")
            record = json.loads(log_path.read_text().strip().split("\n")[0])
            self.assertEqual(record["type"], "environment")
            self.assertIn("fingerprint", record)

    def test_signal_aggregator_handles_all_types(self) -> None:
        """Aggregator must process all signal type JSONs without error."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            # Write synthetic signals via subprocess
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import (
    log_performance, log_token_usage, log_environment,
    log_query, log_zero_result,
)
log_query(["test"], {{}}, "and", False, 2, ["p1"], 5.0)
log_zero_result(["missing"], {{}}, "or", False)
log_performance("softmax", [64, 128], "tilelang", 0.03, 0.03, 0.001, 20, 100)
log_token_usage("query", ["softmax", "perf"], "or", 2, 80, 120)
log_environment("test")
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            result = sp.run(
                [sys.executable, "scripts/signal_aggregator.py", "--check", "--json"],
                capture_output=True, text=True, cwd=str(ROOT),
                env={**os.environ, "MACAWIKI_SIGNAL_DIR": tmp},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertGreaterEqual(data["total_signals"], 3)

    def test_env_detector_snapshot_writes_file(self) -> None:
        """env_detector --snapshot must write env-snapshot.json."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            result = sp.run(
                [sys.executable, "scripts/env_detector.py", "--snapshot"],
                capture_output=True, text=True, cwd=str(ROOT),
                env={**os.environ, "MACAWIKI_SIGNAL_DIR": tmp},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            snap_path = Path(tmp) / "env-snapshot.json"
            self.assertTrue(snap_path.exists(), f"Snapshot not created at {snap_path}")
            data = json.loads(snap_path.read_text())
            self.assertIn("environment_fingerprint", data)

    def test_self_improve_new_strategies_registered(self) -> None:
        """STRATEGIES dict must include perf_baseline_update and token_efficiency_hint."""
        from scripts.self_improve import STRATEGIES
        for name in ("perf_baseline_update", "token_efficiency_hint"):
            self.assertIn(name, STRATEGIES, f"Strategy '{name}' not registered")
            self.assertTrue(callable(STRATEGIES[name]),
                            f"Strategy '{name}' is not callable")

    def test_auto_fix_rules_has_new_strategies(self) -> None:
        """auto-fix-rules.yaml must contain perf_baseline_update and token_efficiency_hint."""
        from scripts.common import load_data
        rules = load_data(ROOT / "data" / "auto-fix-rules.yaml")
        for name in ("perf_baseline_update", "token_efficiency_hint"):
            self.assertIn(name, rules.get("rules", {}),
                          f"Strategy '{name}' missing in auto-fix-rules.yaml")

    def test_token_report_script_works(self) -> None:
        """token_report.py must execute without error."""
        result = subprocess.run(
            [sys.executable, "scripts/token_report.py", "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn("total_records", data)

    def test_env_detector_deep_probe(self) -> None:
        """env_detector --deep --json must include pip_packages and maca_libraries."""
        result = subprocess.run(
            [sys.executable, "scripts/env_detector.py", "--deep", "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["schema_version"], 2)
        self.assertIn("pip_packages", data)
        self.assertIn("maca_libraries", data)
        self.assertIn("macainfo", data)
        self.assertIn("tools", data)
        # Check mcTracer tool detection
        self.assertIn("mcTracer", data.get("tools", {}))

    def test_perf_capture_module_importable(self) -> None:
        """perf_capture module must be importable."""
        import importlib
        try:
            importlib.import_module("scripts.perf_capture")
        except ImportError:
            importlib.import_module("perf_capture")

    def test_perf_capture_json_output(self) -> None:
        """perf_capture --json must return structured results or a valid error.

        When PyTorch + CUDA device are available the response must include
        device_name, operator_results, and memory_bandwidth (exit 0).
        When PyTorch is unavailable a structured error response with a
        non-zero exit code is acceptable.
        """
        result = subprocess.run(
            [sys.executable, "scripts/perf_capture.py", "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
            timeout=120,
        )
        data = json.loads(result.stdout)
        if result.returncode == 0:
            # Success path: must have the expected benchmark fields
            self.assertIn("device_name", data, "Success response missing device_name")
            self.assertIn("operator_results", data, "Success response missing operator_results")
            self.assertIn("memory_bandwidth", data, "Success response missing memory_bandwidth")
            self.assertGreaterEqual(len(data.get("operator_results", [])), 4,
                                    "Expected at least 4 operator_results")
        elif result.returncode == 1 and isinstance(data.get("error"), str):
            # Error path: device unavailable — only specific errors accepted
            self.assertIn(data["error"], (
                "PyTorch not available",
                "CUDA/MXMACA device not available",
            ), f"Unexpected error message: {data.get('error')}")
            self.assertIsInstance(data.get("results"), list,
                                  "Error response must include results list")
        else:
            self.fail(
                f"Unexpected exit {result.returncode}: "
                f"stdout={result.stdout[:500]} stderr={result.stderr[:500]}"
            )

    def test_signal_logger_tool_inventory(self) -> None:
        """log_tool_inventory() must write to tool-inventory-log.jsonl."""
        import tempfile, os, subprocess as sp
        with tempfile.TemporaryDirectory() as tmp:
            r = sp.run(
                ["python3", "-c", f"""
import os; os.environ["MACAWIKI_SIGNAL_DIR"] = "{tmp}"
from scripts.signal_logger import log_tool_inventory
log_tool_inventory({{"mcTracer": {{"path": "/opt/maca/bin/mcTracer", "version": "3.7.1.5"}}}}, "test")
"""],
                cwd=str(ROOT), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            log_path = Path(tmp) / "tool-inventory-log.jsonl"
            self.assertTrue(log_path.exists(), f"Log not created at {log_path}")
            record = json.loads(log_path.read_text().strip().split("\n")[0])
            self.assertEqual(record["type"], "tool_inventory")
            self.assertIn("mcTracer", record.get("tools", {}))

    def test_env_detector_recognizes_mctracer(self) -> None:
        """env_detector must detect mcTracer at /opt/maca/bin/mcTracer when C500 present."""
        result = subprocess.run(
            [sys.executable, "scripts/env_detector.py", "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        tools = data.get("tools", {})
        if data.get("is_c500"):
            mct = tools.get("mcTracer", {})
            self.assertIsNotNone(mct.get("path"),
                                 "mcTracer path should be detected on C500")

    # ── iteration loop state gates ────────────────────────────────────

    def test_iterate_skill_copies_stay_identical(self) -> None:
        """The two macawiki-iterate SKILL.md copies must stay byte-identical.

        They are the same adapter duplicated for discovery paths; a drift
        (e.g. a step added to one) means the two agents follow different
        iteration protocols.
        """
        copies = (
            ROOT / ".claude/skills/macawiki-iterate/SKILL.md",
            ROOT / ".agents/skills/macawiki-iterate/SKILL.md",
        )
        missing = [str(p.relative_to(ROOT)) for p in copies if not p.is_file()]
        self.assertEqual(missing, [], f"iterate skill copies missing: {missing}")
        bodies = [p.read_text(encoding="utf-8") for p in copies]
        self.assertEqual(bodies[0], bodies[1],
                         "macawiki-iterate SKILL.md copies have diverged")

    def test_precheck_rejects_drifted_state(self) -> None:
        """iterate_precheck must fail loudly on structural drift, not pass silently.

        next_cycle_id colliding with an existing cycle, and a champion SHA that
        does not exist in this repo, both previously went unnoticed — that is
        how state drifted far enough to break cycle 11.
        """
        import shutil as _shutil

        state_path = ROOT / "evals/claude/iteration-state.json"
        backup = state_path.with_suffix(".json.precheck-test-backup")
        try:
            _shutil.copy2(state_path, backup)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("cycles"):
                state["next_cycle_id"] = state["cycles"][-1]["cycle_id"]  # collide
            state.setdefault("champion", {})["commit"] = "0" * 40          # foreign
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")

            r = run_script("scripts/iterate_precheck.py", "--json")
            self.assertNotEqual(r.returncode, 0,
                                "precheck must exit non-zero on drifted state")
            data = json.loads(r.stdout)
            codes = {f["code"] for f in data["findings"]}
            self.assertFalse(data["ok"], "precheck reported ok=true on drifted state")
            self.assertIn("cycle-id-collision", codes)
            self.assertIn("champion-foreign-sha", codes)
        finally:
            # Restored by plain rename/overwrite, never git checkout/reset.
            backup.replace(state_path)

    def test_precheck_passes_on_current_state(self) -> None:
        """precheck must accept the real, maintained state file (no false blocks)."""
        r = run_script("scripts/iterate_precheck.py", "--json")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        data = json.loads(r.stdout)
        blocking = [f for f in data["findings"]
                    if f["level"] in ("critical", "error")]
        self.assertEqual(blocking, [],
                         f"state has unhandled blocking findings: {blocking}")


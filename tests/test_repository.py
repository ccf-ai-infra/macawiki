"""Repository-level regression tests for Macawiki v0.1."""

from __future__ import annotations

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
        for operator in ("add", "softmax", "layer_norm", "matmul"):
            self.assertIn(operator, result.stdout)


if __name__ == "__main__":
    unittest.main()

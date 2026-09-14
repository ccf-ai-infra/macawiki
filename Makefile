.PHONY: validate test indices status eval doctor quality freshness coverage recall signals signals-merge self-improve-check self-improve evolve report check check-advisory iterate-precheck iterate-cycle trend all env-probe perf-signals token-report perf-capture perf-capture-full

validate:
	python3 scripts/validate.py

test:
	python3 -m unittest discover -s tests -v

indices:
	python3 scripts/generate_indices.py

status:
	python3 scripts/repo_status.py

eval:
	python3 scripts/run_agent_value_eval.py

doctor:
	python3 scripts/doctor.py

quality:
	python3 scripts/quality_gates.py

freshness:
	python3 scripts/freshness_check.py

coverage:
	python3 scripts/coverage_report.py --markdown evals/coverage/report.md

recall:
	python3 scripts/recall_check.py --mode or

# Combined advisory quality check — runs all non-blocking gates.
# Use `make check-advisory` to see a full picture of corpus health.
# These gates are advisory (non-blocking) while the corpus matures.
check-advisory:
	-@echo "=== Quality Gates ==="
	-@python3 scripts/quality_gates.py; _rc=$$?; echo "  (exit: $$_rc)"
	-@echo ""
	-@echo "=== Coverage Report ==="
	-@python3 scripts/coverage_report.py --markdown evals/coverage/report.md; _rc=$$?; echo "  (exit: $$_rc)"
	-@echo ""
	-@echo "=== Recall Check ==="
	-@python3 scripts/recall_check.py --mode or 2>&1; _rc=$$?; echo "  (exit: $$_rc)"
	-@echo ""
	-@echo "=== Freshness Check ==="
	-@python3 scripts/freshness_check.py --skip-url-check 2>&1; _rc=$$?; echo "  (exit: $$_rc)"
	-@echo ""
	@echo "=== Advisory check complete ==="
	@echo "See: make quality | make coverage | make recall | make freshness"

# Full health report: all gates + status summary.
report: check-advisory status
	@echo ""
	@echo "=== Full health report written to evals/ ==="

# Signal aggregation — analyze query logs, print report (no state changes).
signals:
	python3 scripts/signal_aggregator.py --check

# Signal aggregation + merge — process signals into backlog items.
signals-merge:
	python3 scripts/signal_aggregator.py --merge

# Iteration precheck — refuse to start a cycle while loop state has drifted
# (cycle-id collision, foreign/absent champion SHA, unaggregated signals).
# Non-zero exit means: fix the findings before opening a new cycle.
iterate-precheck:
	python3 scripts/iterate_precheck.py

# Self-improvement dry-run — preview auto-fixable items.
self-improve-check:
	python3 scripts/self_improve.py --dry-run

# Self-improvement apply — process auto-fixable backlog items with safety gates.
self-improve:
	python3 scripts/self_improve.py --apply

# Iteration cycle orchestration — the mechanical spine of the 13-step loop.
# The hypothesis and the accept/reject judgement stay with the agent; this
# only enforces that a cycle records its hypothesis, its measured before/after
# metrics, and a report even when rejected.
iterate-cycle:
	python3 scripts/iterate_cycle.py --status

# Iteration trend — per-cycle metrics and decisions from loop history.
trend:
	python3 scripts/trend_report.py --markdown evals/claude/trend.md

# Environment detection — probe C500/MXMACA hardware and software versions,
# write a JSONL record for the aggregator so env changes are detected over time.
env-probe:
	python3 scripts/env_detector.py --snapshot
	@python3 -c "from scripts.signal_logger import log_environment; log_environment('periodic')"

# Performance signals — analyze operator performance logs and detect regressions.
perf-signals:
	python3 scripts/signal_aggregator.py --check

# Token consumption report — identify expensive query patterns.
token-report:
	python3 scripts/token_report.py

# Performance capture — run quick microbenchmarks and log results.
perf-capture:
	python3 scripts/perf_capture.py

# Full performance capture — extended benchmark suite.
perf-capture-full:
	python3 scripts/perf_capture.py --full --json

# Evolve: aggregate signals + preview auto-fixes (combined advisory gate).
evolve: env-probe signals self-improve-check
	@echo ""
	@echo "=== Self-evolution: env probed, signals analyzed, auto-fixes previewed ==="

# Fast pre-commit check (validate + test only, no index regeneration).
check: validate test
	@echo ""
	@echo "=== Pre-commit check passed ==="

# trend is in `all` because the artifact is regenerated, not hand-edited: if it
# is not refreshed on every gate run it silently drifts from the state file, and
# a trend that disagrees with the loop it describes is worse than none.
all: validate indices test eval doctor status trend

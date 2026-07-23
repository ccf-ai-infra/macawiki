.PHONY: validate test indices status eval doctor quality freshness coverage recall report check check-advisory all

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

# Fast pre-commit check (validate + test only, no index regeneration).
check: validate test
	@echo ""
	@echo "=== Pre-commit check passed ==="

all: validate indices test eval doctor status

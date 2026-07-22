.PHONY: validate test indices status eval doctor all

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

all: validate indices test eval doctor status

# Multi-firm operations — convenience targets.
# Wrappers around scripts that the pre-commit hook also calls.

.PHONY: validate validate-params validate-data test

validate: validate-params validate-data

validate-params:
	@python scripts/validate_params.py

validate-data:
	@python scripts/check_data_manifests.py --check

test:
	@python -m pytest tests/ -x

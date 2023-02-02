tests:
	KEEP_FILES_FOR_ARTIFACTS=1 coverage run -m pytest tests.py -vvv
	coverage report -m
	coverage-badge -f -o docs/coverage.svg

.PHONY: tests

tests:
	coverage run -m pytest tests.py -vvv
	coverage report -m
	coverage html
	coverage-badge -f -o docs/coverage.svg

.PHONY: tests

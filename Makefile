tests:
	pytest --cov-report term --cov-report html:html-cov --cov=tests --cov=click-up-timereport tests.py -vvv
	coverage-badge -f -o docs/coverage.svg

.PHONY: tests

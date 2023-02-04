tests:
	# Runs only non-fuzzy test cases
	pytest -m 'not fuzzy' --cov-report term --cov-report html:html-cov --cov=click_up_timesheeting tests.py -vvv
	coverage-badge -f -o docs/coverage.svg

tests-fuzzy:
	# Runs both fuzzy and non-fuzzy test cases, checking also coverage for the tests.py file
	pytest --cov-report term --cov-report html:html-cov --cov=tests --cov=click_up_timesheeting tests.py -vvv
	coverage-badge -f -o docs/coverage.svg

.PHONY: tests

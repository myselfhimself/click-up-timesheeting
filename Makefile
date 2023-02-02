tests:
	KEEP_FILES_FOR_ARTIFACTS=1 coverage run -m pytest tests.py -k test_main_output_from_mocked_api -vvv
	coverage report -m
	coverage-badge -f -o docs/coverage.svg

.PHONY: tests

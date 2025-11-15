.PHONY: fmt
fmt:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: check
check:
	uv run ruff format --check .
	uv run ruff check .
	uv run basedpyright ./src

.PHONY: tests
tests:
	uv run pytest -s -vvv \
		--cov=carthorse \
		--cov-branch \
		--cov-report=term-missing:skip-covered \
		--cov-fail-under=90 \
		--cov-report html:cov_html \
		--cov-report=xml:coverage.xml


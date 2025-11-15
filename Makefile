.PHONY: fmt
fmt:
	uv run --locked ruff format .
	uv run --locked ruff check --fix .

.PHONY: check
check:
	uv run --locked ruff format --check .
	uv run --locked ruff check .
	uv run --locked basedpyright ./src

.PHONY: tests
tests:
	uv run pytest -s -vvv \
		--cov=carthorse \
		--cov-branch \
		--cov-report=term-missing:skip-covered \
		--cov-fail-under=90 \
		--cov-report html:cov_html \
		--cov-report=xml:coverage.xml


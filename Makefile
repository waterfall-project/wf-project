# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# Waterfall — repository commands.
#
# The specification lives in docs/spec, the interface contract in docs/api.
# Requirements: python3, pandoc (document projection), node with npx (contract
# linting and bundling), uv (repository tools), and mmdc to validate the diagrams.

SPEC    := docs/spec
API     := docs/api
BUNDLE  := $(API)/waterfall.bundle.yaml
MOCK_SPEC := $(API)/waterfall.mock.json
COMPOSE_DEV := docker compose -f deploy/compose/compose.dev.yaml
TOOLS   := tools
BACK    := backend
FRONT   := frontend
PNPM    := cd $(FRONT) && COREPACK_ENABLE_DOWNLOAD_PROMPT=0 NEXT_TELEMETRY_DISABLED=1 pnpm
# Pinned so that a check passes or fails on what this repository contains, never on
# what a tool released overnight. Raise a version here and nowhere else.
REDOCLY_VERSION := 2.54.3
PRISM_VERSION   := 5.16.0
REDOCLY := npx --yes @redocly/cli@$(REDOCLY_VERSION)
PRISM   := npx --yes @stoplight/prism-cli@$(PRISM_VERSION)

.DEFAULT_GOAL := help
.PHONY: help build-doc build-doc-strict build-openapi lint-openapi inventory allocate-pbs mock \
	mock-spec dev dev-down lint-compose \
	test-tools lint-tools typecheck-tools sources fixtures check-fixtures requirements \
	requirements-release reuse lint-workflows \
	lint-shell check \
	check-all check-repo check-spec \
	check-contract check-back lint-back typecheck-back imports-back test-back check-front \
	install-front lint-front typecheck-front test-front generate-client client-up-to-date \
	lint-docker changes gate \
	check-tools clean

# The branch a change is compared with, for `make check` and `make changes`.
BASE ?= origin/main
WFTOOLS := uv run --frozen --project $(TOOLS) python -m wftools

help: ## List the commands
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

build-doc: ## Regenerate the Markdown projection from Word and draw.io
	@$(SPEC)/build.sh

build-doc-strict: ## Same, but fail on any warning (for CI)
	@$(SPEC)/build.sh --strict

lint-openapi: ## Check the interface contract
	@cd $(API) && $(REDOCLY) lint openapi.yaml

build-openapi: lint-openapi ## Check, then bundle the contract into a single file
	@cd $(API) && $(REDOCLY) bundle openapi.yaml -o $(notdir $(BUNDLE))
	@echo "  -> $(BUNDLE)"

inventory: ## Regenerate the endpoint inventory and the requirement coverage
	@python3 $(API)/tools/inventory.py

allocate-pbs: ## Write the PBS field of every requirement into the Word document
	@python3 $(SPEC)/tools/allocate_pbs.py

mock-spec: lint-openapi ## Derive from the contract the variant the fake back serves
	@cd $(API) && $(REDOCLY) bundle openapi.yaml --ext json -o $(notdir $(MOCK_SPEC)) >/dev/null
	@$(WFTOOLS).mock $(MOCK_SPEC)

mock: mock-spec ## Serve the fake back on http://localhost:4010, from the contract's examples
	@$(PRISM) mock $(MOCK_SPEC) --host 0.0.0.0 --port 4010

dev: mock-spec ## Start the front against the fake back (http://localhost:3000)
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) up --build

dev-down: ## Stop the development platform
	@$(COMPOSE_DEV) down

test-tools: ## Run the tests of the repository tools
	@cd $(TOOLS) && uv run --frozen pytest

lint-tools: ## Lint and format check of the repository tools
	@cd $(TOOLS) && uv run --frozen ruff check . && uv run --frozen ruff format --check .

typecheck-tools: ## Strict type check of the repository tools
	@cd $(TOOLS) && uv run --frozen pyright

sources: ## No suppression comment, no source file over 1,000 lines (US-0050)
	@$(WFTOOLS).sources

fixtures: ## Regenerate the listing of the numeric examples of the document
	@$(WFTOOLS).examples --write

check-fixtures: ## The listing is up to date, and every fixture cites an existing example
	@$(WFTOOLS).examples

requirements: ## Report which F0 requirements the tests cover (WF-QUA-0010)
	@$(WFTOOLS).coverage

requirements-release: ## Same, and fail on an F0 requirement no test covers
	@$(WFTOOLS).coverage --release

reuse: ## Check that every file declares its copyright and licence
	@uv run --frozen --project $(TOOLS) reuse lint

lint-workflows: ## Lint the GitHub Actions workflows
	@uv run --frozen --project $(TOOLS) actionlint

lint-shell: ## Lint the shell scripts
	@git ls-files '*.sh' | xargs uv run --frozen --project $(TOOLS) shellcheck

lint-docker: ## Lint the Dockerfiles
	@git ls-files '*Dockerfile' | xargs -r uv run --frozen --project $(TOOLS) hadolint

lint-compose: ## Validate the Compose files
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) config --quiet

# --- The chain: one target per family of checks (tools/paths.toml) -----------------

check: ## Run the checks of what the change touches (BASE=origin/main by default)
	@for target in $$($(WFTOOLS).changes $(BASE) --targets); do \
		echo "== $$target"; $(MAKE) --no-print-directory $$target || exit 1; \
	done

check-all: check-repo check-spec check-contract check-back check-front ## Run every family of checks

check-repo: reuse lint-workflows lint-shell lint-docker lint-compose sources check-fixtures \
	requirements lint-tools typecheck-tools test-tools ## Checks that run on any change

check-spec: build-doc-strict ## The projection builds without warning and is up to date
	@git diff --exit-code --stat -- $(SPEC)/waterfall-spec.md \
		|| { echo "  the projection is not the one the Word document produces: run make build-doc"; exit 1; }

check-contract: lint-openapi inventory ## The contract lints and its inventory is up to date
	@git diff --exit-code --stat -- $(API)/INVENTORY.md \
		|| { echo "  INVENTORY.md is not the one the contract produces: run make inventory"; exit 1; }

check-back: lint-back typecheck-back imports-back test-back ## The back: lint, types, boundaries, tests

lint-back: ## Lint and format check of the back
	@cd $(BACK) && uv run --frozen ruff check . && uv run --frozen ruff format --check .

typecheck-back: ## Strict type check of the back
	@cd $(BACK) && uv run --frozen pyright

imports-back: ## The boundaries of the core (WF-ARC-0010)
	@cd $(BACK) && uv run --frozen lint-imports --no-cache

test-back: ## Tests of the back
	@cd $(BACK) && uv run --frozen pytest

check-front: client-up-to-date lint-front typecheck-front test-front ## The front: client, lint and format, types, tests

install-front: ## Install the dependencies of the front, as the lock file says
	@$(PNPM) install --frozen-lockfile --silent

generate-client: build-openapi install-front ## Regenerate the API client of the front from the contract
	@$(PNPM) exec openapi-typescript ../$(BUNDLE) -o src/api/generated/schema.d.ts --silent
	@echo "  -> $(FRONT)/src/api/generated/schema.d.ts"

client-up-to-date: generate-client ## The versioned client is the one the contract produces
	@git diff --exit-code --stat -- $(FRONT)/src/api/generated \
		|| { echo "  the client is not the one the contract produces: run make generate-client"; exit 1; }

lint-front: install-front ## Lint and format check of the front
	@$(PNPM) lint
	@$(PNPM) format:check

typecheck-front: install-front ## Strict type check of the front
	@$(PNPM) typecheck

test-front: install-front ## Unit tests of the front
	@$(PNPM) test

changes: ## Print which families of checks the change touches (BASE; HEAD, or the working tree)
	@$(WFTOOLS).changes $(BASE) $(HEAD)

gate: ## Decide the outcome of the chain from its jobs (NEEDS, from GitHub Actions)
	@$(WFTOOLS).gate

check-tools: ## Report which prerequisites are missing
	@for t in python3 pandoc npx uv; do \
		command -v $$t >/dev/null && echo "  ok       $$t" || echo "  missing  $$t"; \
	done
	@command -v mmdc >/dev/null && echo "  ok       mmdc" || echo "  absent   mmdc (diagrams will not be validated)"

clean: ## Remove everything the commands generate
	@rm -rf $(SPEC)/.build $(SPEC)/images $(BUNDLE) $(MOCK_SPEC)
	@echo "  cleaned"

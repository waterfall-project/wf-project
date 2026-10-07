# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# Waterfall — repository commands.
#
# The specification lives in docs/spec, the interface contract in docs/api.
# Requirements: python3 3.11+ (the projection), uv (Python 3.13 for the back and the tools),
# node with npx and corepack (the front, the contract), pandoc 3.1.11.1 (the projection),
# docker (make dev), and mmdc to validate the diagrams.

SPEC    := docs/spec
API     := docs/api
BUNDLE  := $(API)/waterfall.bundle.yaml
# Where the variant the fake back serves is written, and the port `make mock` serves it on. The
# end-to-end paths give both their own (`frontend/playwright.config.ts`): rewriting the file
# that `make dev` mounts would bring its fake back down. `make dev` heeds neither: Compose mounts
# docs/api/waterfall.mock.json and publishes 4010 (deploy/compose/compose.dev.yaml).
MOCK_SPEC := $(API)/waterfall.mock.json
MOCK_PORT := 4010
# The same bundle in JSON, which the repository tools read without a YAML parser.
JSON_BUNDLE := $(API)/waterfall.bundle.json
COMPOSE_DEV := docker compose -f deploy/compose/compose.dev.yaml
TOOLS   := tools
# The tools of the specification and of the contract, held to the same rules as the others.
DOC_TOOLS := ../docs/api/tools ../docs/spec/tools
BACK    := backend
FRONT   := frontend
# An address where no API answers: the front builds without reaching one (#131).
NOWHERE := http://127.0.0.1:9
PNPM    := cd $(FRONT) && COREPACK_ENABLE_DOWNLOAD_PROMPT=0 NEXT_TELEMETRY_DISABLED=1 pnpm
# Pinned so that a check passes or fails on what this repository contains, never on
# what a tool released overnight. Raise a version here and nowhere else.
REDOCLY_VERSION := 2.54.3
PRISM_VERSION   := 5.16.0
REDOCLY := npx --yes @redocly/cli@$(REDOCLY_VERSION)
PRISM   := npx --yes @stoplight/prism-cli@$(PRISM_VERSION)

.DEFAULT_GOAL := help
.PHONY: help build-doc build-doc-strict build-openapi lint-openapi inventory allocate-pbs mock \
	mock-spec mock-data mock-data-up-to-date dev dev-down lint-compose \
	test-tools lint-tools typecheck-tools sources fixtures check-fixtures requirements \
	requirements-release reuse lint-workflows \
	lint-shell check \
	check-all check-repo check-spec \
	check-contract check-back lint-back typecheck-back imports-back test-back check-front \
	install-front lint-front typecheck-front test-front build-front generate-client client-up-to-date catalogs \
	coverage-back coverage-front roadmap check-roadmap e2e e2e-browsers lot-size \
	lint-docker changes gate \
	check-tools clean

# The branch a change is compared with, for `make check` and `make changes`.
BASE ?= origin/main
# The tier of the chain: `fast` on every push, `full` when a pull request is merged
# (US-0310). The full tier adds what is slow: code coverage, end-to-end tests.
TIER ?= fast
# Extra flags to install Playwright's browsers: the chain adds --with-deps.
PLAYWRIGHT_INSTALL ?=
full-only = $(if $(filter full,$(TIER)),$(1))
# The coverage run executes the same tests: in the full tier it replaces the plain run.
full-else = $(if $(filter full,$(TIER)),$(1),$(2))
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
	@uv run --frozen --project $(TOOLS) python $(API)/tools/inventory.py

allocate-pbs: ## Write the PBS field of every requirement into the Word document
	@python3 $(SPEC)/tools/allocate_pbs.py

mock-spec: lint-openapi ## Derive from the contract the variant the fake back serves
	@mkdir -p $(dir $(MOCK_SPEC))
	@cd $(API) && $(REDOCLY) bundle openapi.yaml --ext json -o $(abspath $(MOCK_SPEC)) >/dev/null
	@$(WFTOOLS).mock $(MOCK_SPEC)

mock-data: ## Regenerate the volumes of §4.6.2 and the readings and writes of the witness the fake back serves (fixtures/api)
	@$(WFTOOLS).mockdata

mock-data-up-to-date: ## The versioned volumes and witness readings and writes are the ones the generator writes
	@$(WFTOOLS).mockdata --check

mock: mock-spec ## Serve the fake back on http://localhost:4010 (MOCK_PORT), from the contract's examples
	@$(PRISM) mock $(MOCK_SPEC) --host 0.0.0.0 --port $(MOCK_PORT)

dev: mock-spec ## Start the front against the fake back (http://localhost:3000)
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) up --build

dev-down: ## Stop the development platform
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) down

test-tools: ## Run the tests of the repository tools
	@cd $(TOOLS) && uv run --frozen pytest

lint-tools: ## Lint and format check of the repository tools
	@cd $(TOOLS) && uv run --frozen ruff check . $(DOC_TOOLS) \
		&& uv run --frozen ruff format --check . $(DOC_TOOLS)

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
	@git ls-files '*.sh' | xargs -r uv run --frozen --project $(TOOLS) shellcheck

lint-docker: ## Lint the Dockerfiles
	@git ls-files '*Dockerfile' | xargs -r uv run --frozen --project $(TOOLS) hadolint

lint-compose: ## Validate the Compose files
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) config --quiet

# --- The chain: one target per family of checks (tools/paths.toml) -----------------

check: ## Run the checks of what the change touches (BASE=origin/main by default)
	@targets=$$($(WFTOOLS).changes "$(BASE)" --targets) \
		|| { echo "  the family selection failed: no check ran" >&2; exit 1; }; \
	for target in $$targets; do \
		echo "== $$target"; $(MAKE) --no-print-directory $$target || exit 1; \
	done

check-all: check-repo check-spec check-contract check-back check-front check-roadmap ## Run every family of checks

check-repo: reuse lint-workflows lint-shell lint-docker lint-compose sources check-fixtures \
	requirements lint-tools typecheck-tools test-tools ## Checks that run on any change

check-spec: build-doc-strict ## The projection builds without warning and is up to date
	@git diff --exit-code --stat -- $(SPEC)/waterfall-spec.md \
		|| { echo "  the projection is not the one the Word document produces: run make build-doc"; exit 1; }

check-contract: lint-openapi inventory mock-data-up-to-date ## The contract lints, its inventory and its volumes are up to date
	@git diff --exit-code --stat -- $(API)/INVENTORY.md \
		|| { echo "  INVENTORY.md is not the one the contract produces: run make inventory"; exit 1; }

check-back: lint-back typecheck-back imports-back $(call full-else,coverage-back,test-back) ## The back: lint, types, boundaries, tests; coverage replaces the plain tests in the full tier

lint-back: ## Lint and format check of the back
	@cd $(BACK) && uv run --frozen ruff check . && uv run --frozen ruff format --check .

typecheck-back: ## Strict type check of the back
	@cd $(BACK) && uv run --frozen pyright

imports-back: ## The boundaries of the core (WF-ARC-0010)
	@cd $(BACK) && uv run --frozen lint-imports --no-cache

test-back: ## Tests of the back
	@cd $(BACK) && uv run --frozen pytest

coverage-back: ## Code coverage of the back: 90 % of lines, 85 % of branches (US-0060)
	@cd $(BACK) && uv run --frozen pytest --quiet --cov --cov-report=json:coverage.json
	@$(WFTOOLS).codecoverage coverage.py $(BACK)/coverage.json

check-front: client-up-to-date lint-front typecheck-front catalogs $(call full-else,coverage-front e2e-browsers e2e,build-front test-front) ## The front: client, lint, types, catalogues, production build, tests; coverage and end-to-end, which build the front, replace the build and the plain tests in the full tier

install-front: ## Install the dependencies of the front, as the lock file says
	@$(PNPM) install --frozen-lockfile --silent

generate-client: build-openapi install-front ## Regenerate the API client of the front from the contract
	@$(PNPM) exec openapi-typescript ../$(BUNDLE) -o src/api/generated/schema.d.ts --silent
	@echo "  -> $(FRONT)/src/api/generated/schema.d.ts"
	@cd $(API) && $(REDOCLY) bundle openapi.yaml --ext json -o $(notdir $(JSON_BUNDLE)) >/dev/null
	@$(WFTOOLS).exampleroutes $(JSON_BUNDLE) $(FRONT)/src/api/generated/examples.d.ts

client-up-to-date: generate-client ## The versioned client is the one the contract produces
	@git diff --exit-code --stat -- $(FRONT)/src/api/generated \
		|| { echo "  the client is not the one the contract produces: run make generate-client"; exit 1; }

lint-front: install-front ## Lint and format check of the front
	@$(PNPM) lint
	@$(PNPM) format:check

typecheck-front: install-front ## Strict type check of the front
	@$(PNPM) typecheck

# The contract is bundled here, never read from a bundle left on the disk by an older run.
catalogs: ## The catalogues of the front are twins, with a key for each value the contract codes (WF-QUA-0070)
	@cd $(API) && $(REDOCLY) bundle openapi.yaml --ext json -o $(notdir $(JSON_BUNDLE)) >/dev/null
	@$(WFTOOLS).catalogs $(JSON_BUNDLE) $(FRONT)/messages/fr.json $(FRONT)/messages/en.json

test-front: install-front ## Unit tests of the front
	@$(PNPM) test

build-front: export WATERFALL_API_ADDRESS = $(NOWHERE)
build-front: install-front ## Build the front for production with no API to reach, no page reading it while built (#131); in the fast tier, the full one builds it for the end-to-end paths
	@$(PNPM) build

coverage-front: install-front ## Code coverage of the front: 90 % of lines, 85 % of branches (US-0060)
	@$(PNPM) exec vitest run --coverage --silent
	@$(WFTOOLS).codecoverage istanbul $(FRONT)/coverage/coverage-summary.json

check-roadmap: roadmap ## The roadmap and the requirements agree (US-0070)

roadmap: ## Confront the stories of docs/roadmap with the requirements of the document
	@$(WFTOOLS).roadmap

e2e-browsers: install-front ## Install the browser the end-to-end tests run in
	@$(PNPM) exec playwright install $(PLAYWRIGHT_INSTALL) chromium

e2e: install-front ## End-to-end paths, against the fake back that Playwright starts (US-0080)
	@$(PNPM) exec playwright test

lot-size: ## The real size of a lot, against its epic (BASE=origin/epic/EP-nn); never fails
	@$(WFTOOLS).lotsize "$(BASE)" $(HEAD)

changes: ## Print which families of checks the change touches (BASE; HEAD, or the working tree)
	@$(WFTOOLS).changes "$(BASE)" $(HEAD)

gate: ## Decide the outcome of the chain from its jobs (NEEDS, from GitHub Actions)
	@$(WFTOOLS).gate

check-tools: ## Report which prerequisites are missing
	@for t in python3 pandoc node npx corepack uv docker; do \
		command -v $$t >/dev/null && echo "  ok       $$t" || echo "  missing  $$t"; \
	done
	@command -v pandoc >/dev/null && pandoc --version | head -1 | grep -q " 3.1.11.1$$" \
		|| echo "  warning  pandoc is not 3.1.11.1: the projection would differ from the chain's"
	@command -v mmdc >/dev/null && echo "  ok       mmdc" || echo "  absent   mmdc (diagrams will not be validated)"

clean: ## Remove everything the commands generate
	@rm -rf $(SPEC)/.build $(SPEC)/images $(BUNDLE) $(JSON_BUNDLE) $(MOCK_SPEC) $(FRONT)/.e2e
	@echo "  cleaned"

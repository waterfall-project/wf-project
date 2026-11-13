# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# Waterfall — repository commands.
#
# The specification lives in docs/spec, the interface contract in docs/api.
# Requirements: python3 3.14+ (the projection), uv (Python 3.14 for the back and the tools),
# node with npx and pnpm (the front, the contract), pandoc 3.13 (the projection),
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
# The variant Prism serves as a proxy in front of the real service (make e2e-service): the fake
# back's, in a file of its own, which a running fake back does not read.
PROXY_SPEC := $(API)/waterfall.proxy.json
# The same bundle in JSON, which the repository tools read without a YAML parser.
JSON_BUNDLE := $(API)/waterfall.bundle.json
COMPOSE_DEV := docker compose -f deploy/compose/compose.dev.yaml
# Prism is named at the version pinned below: the proxy of `make e2e-service` runs it too. The
# platform runs under the project of the slot of the worktree (WATERFALL_SERVICE_PROJECT, below).
COMPOSE_SERVICE_FILE = PRISM_VERSION=$(PRISM_VERSION) docker compose -f deploy/compose/compose.service.yaml
COMPOSE_SERVICE = $(COMPOSE_SERVICE_FILE) -p $(WATERFALL_SERVICE_PROJECT)
# The services of the tests (US-1110), under the project of the slot of the worktree.
COMPOSE_TEST = docker compose -f deploy/compose/compose.test.yaml -p $(WATERFALL_TEST_PROJECT)
# The production platform (US-0430), under a local name: Caddy's own authority makes its certificate.
COMPOSE_PRODUCTION := docker compose -f deploy/compose/compose.prod.yaml -f deploy/compose/compose.prod.local.yaml
# The root of the authority of Keycloak's front end on the service platform (#680), copied out of
# Caddy at each start: what the front (NODE_EXTRA_CA_CERTS, added to the authorities it trusts)
# and the tests of the platform (SSL_CERT_FILE, the only one they trust) trust. Ignored by git.
KEYCLOAK_AUTHORITY := $(abspath deploy/compose/.authority/root.crt)
# Where the browser reaches Keycloak on the service platform, as compose.service.yaml says it: its
# port alone moves, its front end serving localhost and 127.0.0.1 only (#735).
KEYCLOAK_ADDRESS = https://localhost:$${WATERFALL_KEYCLOAK_PORT:-8443}/auth
TOOLS   := tools
# The tools of the specification and of the contract, held to the same rules as the others.
DOC_TOOLS := ../docs/api/tools ../docs/spec/tools
BACK    := backend
FRONT   := frontend
# An address where no API answers: the front builds without reaching one (#131).
NOWHERE := http://127.0.0.1:9
PNPM_ENV := NEXT_TELEMETRY_DISABLED=1
PNPM    := cd $(FRONT) && $(PNPM_ENV) pnpm
# pnpm for a heavy run, which waits for its turn (tools/src/wftools/slots.py).
# The front takes the same share as the back (WATERFALL_PROCESSORS), a run of one file (TESTS) too.
PNPM_HEAVY = cd $(FRONT) && $(heavy) $(PNPM_ENV) WATERFALL_PROCESSORS=$(WATERFALL_PROCESSORS) pnpm
# pnpm for the unit tests of the front, which have the Redis of the slot of the worktree (TESTING_FRONT).
PNPM_TESTING = cd $(FRONT) && $(TESTING_FRONT) $(PNPM_ENV) WATERFALL_PROCESSORS=$(WATERFALL_PROCESSORS) pnpm
# Pinned so that a check passes or fails on what this repository contains, never on
# what a tool released overnight. Raise a version here and nowhere else.
REDOCLY_VERSION := 2.73.0
PRISM_VERSION   := 5.16.0
REDOCLY := npx --yes @redocly/cli@$(REDOCLY_VERSION)
PRISM   := npx --yes @stoplight/prism-cli@$(PRISM_VERSION)

.DEFAULT_GOAL := help
.PHONY: help build-doc build-doc-strict build-openapi lint-openapi inventory allocate-pbs mock \
	mock-tools mock-spec mock-data mock-data-up-to-date dev dev-down lint-compose service-up service-install service-witness service-purge service-logs service-down migrate \
	build-keycloak build-cache test-keycloak check-keycloak keycloak-authority e2e-service check-service images \
	production-trial check-production \
	test-tools test-openldap lint-tools typecheck-tools sources fixtures check-fixtures requirements \
	requirements-release screens readmes reuse lint-workflows \
	lint-shell check slot slot-release e2e-down slots test-services test-services-down \
	check-all check-repo check-repo-tools check-spec \
	check-contract check-back check-back-static check-back-tests coverage-back-merge lint-back typecheck-back imports-back test-back check-front \
	check-front-code check-front-e2e check-front-image \
	install-front lint-front typecheck-front test-front build-front prerendered-front generate-client client-up-to-date generate-server-models server-models-up-to-date catalogs \
	coverage-back coverage-front roadmap check-roadmap e2e e2e-durations e2e-measure e2e-browsers e2e-image mirror lot-size tracking merge-queue merge-queue-check queue-report \
	lint-docker changes gate \
	check-tools clean

# The branch a change is compared with, for `make check` and `make changes`.
BASE ?= origin/main
# The tier of the chain: `fast` on every push, `full` when a pull request is merged
# (US-0310). The full tier adds what is slow: code coverage, end-to-end tests.
TIER ?= fast
# Extra flags to install Playwright's browsers, such as --with-deps for their system packages.
PLAYWRIGHT_INSTALL ?=
# Test files to run alone, during development: `make test-back TESTS=tests/test_x.py`,
# `make test-front TESTS=src/x.test.tsx`, `make e2e TESTS=e2e/x.spec.ts`. Empty runs them all,
# as the chain does.
TESTS ?=
# The part of the end-to-end paths `make e2e` plays, as i/N: the chain spreads them over N
# runners by the seconds the paths took (tools/e2e-durations.json), and plays the measure of
# §4.6.2 on one more (e2e.yml). Empty, it plays them all.
SHARD ?=
# How many workers `make e2e` plays the paths on (E2E_WORKERS, frontend/playwright.config.ts), each
# against a front of its own: fewer than Playwright takes by itself on a loaded workstation, where
# paths fail by a timeout (#736). From 1 to 40: a front per worker, forty ports per slot. Empty, its
# own: half the processors, at most 40.
WORKERS ?=
# N heavy runs at a time on the workstation (WATERFALL_SLOTS, 1 by default): the whole tests of a
# side, their coverage, the production build of the front, the end-to-end paths. Several agents
# running them side by side ran out of memory (2026-10). tools/src/wftools/slots.py admits them
# (a free slot among N lock files of XDG_RUNTIME_DIR, the first the one of before N existed),
# keeps the slot until the run ends and sets WATERFALL_PROCESSORS, the share of the processors of
# one run. A run of one file (TESTS) does not wait; on a runner of the chain, alone, a slot is
# always free. `env` keeps the variables set before the command a command of their own.
SLOTS = python3 $(CURDIR)/tools/src/wftools/slots.py
heavy = $(if $(TESTS),,$(SLOTS) run --heavy -- env)
# A ceiling of memory on the tests of the tools (2026-11-12: a test whose fake never ended its pages
# filled the 122 GB of the workstation twice, and the kernel killed the whole session of the pilot
# with its four deliverers). Under systemd the run is a scope of its own: past TOOLS_MEMORY the
# kernel kills the run, not the session. The probe asks for the same properties as the run: a host
# whose user systemd does not delegate the memory controller gets no scope, so no ceiling it ignores.
# Without a user systemd (a runner of the chain), no ceiling.
TOOLS_MEMORY ?= 24G
capped = $(if $(shell systemd-run --user --scope --quiet -p MemoryMax=$(TOOLS_MEMORY) -p MemorySwapMax=0 -- true 2>/dev/null && echo yes),systemd-run --user --scope --quiet -p MemoryMax=$(TOOLS_MEMORY) -p MemorySwapMax=0 --,)
# The same for tests that need services (US-1110: db, redis, storage, as `slots.py run --services`
# names them): once the slot is taken, if any, it starts those whose WATERFALL_TEST_*_URL the
# environment does not give (make test-services), sets the variables on them, and runs the command.
# They start with TESTS too, which does not wait for a slot but needs its services as much.
testing = $(SLOTS) run $(if $(TESTS),,--heavy )--services
TESTING_BACK = $(testing) db,redis,storage -- env
TESTING_FRONT = $(testing) redis -- env
# The workers of pytest: the share a heavy run was given, or the one it would be given, for a run
# of one file that does not wait.
# An invalid WATERFALL_SLOTS stops make here, saying so, only where the share is used. It is handed
# to the shell by hand: GNU make 4.3 does not export a variable of the command line to $(shell).
WATERFALL_PROCESSORS ?= $(or $(shell $(if $(filter-out undefined,$(origin WATERFALL_SLOTS)),WATERFALL_SLOTS='$(subst ','\'',$(WATERFALL_SLOTS))') $(SLOTS) processors 2>/dev/null),$(error WATERFALL_SLOTS must be an integer from 1 to 9, not '$(WATERFALL_SLOTS)'))

# The slot of the worktree (US-1100): its ports, its projects of Compose and the tags of its images,
# so that two worktrees play the paths, try Keycloak or run the service platform side by side. The
# main repository — a runner of the chain too — is at slot 0, on the ports and under the names of
# before; a worktree of a lot takes a slot of 1 to N (make slot), the block of ports 20000 + 100·i.
# A target that needs them is given each of its variables by slot-export, unless the environment
# gives it; they are asked once, of the register (slots.py which --variables). In a linked worktree
# without a slot, such a target stops, saying make slot; the others never ask.
slot-variables = $(eval slot-variables := $(or $(shell $(SLOTS) which --variables),$(error no slot for this worktree: run make slot)))$(slot-variables)
slot-value = $(patsubst $(1)=%,%,$(filter $(1)=%,$(slot-variables)))
slot-export = $(foreach name,$(2),$(eval $(1): export $(name) ?= $$(call slot-value,$(name))))
SLOT_SERVICE := WATERFALL_SERVICE_PROJECT WATERFALL_KEYCLOAK_IMAGE WATERFALL_OPENLDAP_IMAGE \
	WATERFALL_POSTGRES_PORT WATERFALL_REDIS_PORT WATERFALL_API_PORT WATERFALL_KEYCLOAK_PORT \
	WATERFALL_MAILPIT_PORT WATERFALL_PROXY_PORT
SLOT_PATHS := E2E_API_PORT E2E_FRONT_PORT
$(call slot-export,service-up service-install service-witness service-purge keycloak-authority service-logs service-down \
	test-keycloak e2e-service,$(SLOT_SERVICE))
$(call slot-export,build-keycloak,WATERFALL_KEYCLOAK_IMAGE)
$(call slot-export,test-services test-services-down,WATERFALL_TEST_PROJECT \
	WATERFALL_TEST_POSTGRES_PORT WATERFALL_TEST_REDIS_PORT WATERFALL_TEST_STORAGE_PORT)
$(call slot-export,e2e e2e-measure e2e-service,$(SLOT_PATHS))
$(call slot-export,check-front-image,WATERFALL_FRONT_CHECK_IMAGE)

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

# The pinned tools of the fake back, fetched once before the harness starts it: left to `npx` at
# the first `make mock`, their installation counted in the 120 s Playwright gives the fake back
# (`webServer`), which a slow network used up in the chain (#1901).
mock-tools: ## Fetch the pinned Redocly and Prism into the cache of npx, so that the fake back starts at once
	@$(REDOCLY) --version >/dev/null
	@$(PRISM) --version >/dev/null

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

# The tests of the tools compute more than they wait: one process per core (pytest-xdist). Work
# stealing, as a few tests of the witness take minutes each and would otherwise wait behind a
# worker's queue: on four cores, eleven minutes become under five. A heavy run, which takes its
# share of the processors, unless it selects a single file (TESTS).
test-tools: ## Run the tests of the repository tools (TESTS=<file> runs one file)
	@cd $(TOOLS) && $(capped) $(heavy) uv run --frozen pytest -n $(WATERFALL_PROCESSORS) --dist worksteal $(TESTS)

# The entrypoint of the directory, tried in Docker on throwaway volumes: a minute of starts that the
# tools leave out (the marker openldap), run by the keycloak family, which deploy/openldap wakes.
test-openldap: ## Try the entrypoint of the directory of test on throwaway volumes (needs Docker)
	@cd $(TOOLS) && uv run --frozen pytest -m openldap -n $(WATERFALL_PROCESSORS) --dist worksteal

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

screens: ## Each leaf of the FBS has its route in the table of the front, answered by a page (EP-02/L3)
	@$(WFTOOLS).screens

readmes: ## Each README-fr.md of docs/ has its English README.md, their headings one for one (#1711)
	@$(WFTOOLS).readmes

reuse: ## Check that every file declares its copyright and licence
	@uv run --frozen --project $(TOOLS) reuse lint

# actionlint is the one tool of the group `workflows`, not of the default one: its package downloads
# a binary from GitHub Releases when it is built, which no other install of the tools should wait for.
lint-workflows: ## Lint the GitHub Actions workflows
	@uv run --frozen --project $(TOOLS) --group workflows actionlint

lint-shell: ## Lint the shell scripts
	@git ls-files '*.sh' | xargs -r uv run --frozen --project $(TOOLS) shellcheck

lint-docker: ## Lint the Dockerfiles
	@git ls-files '*Dockerfile' | xargs -r uv run --frozen --project $(TOOLS) hadolint

# Keycloak answers before its realm is applied: the application starts once it does, anew at each
# start, and stays, to apply it again after a restoration (#955). The root of the authority of its
# front end is copied out first: a new volume makes a new one. The service of the restoration waits
# for the application, which it would start with the platform: it starts last, so that the realm is
# applied once, and Keycloak, which the application waits for, is never started again (--no-deps).
# A start that fails prints the log of the control of the volume of PostgreSQL, which says nothing
# unless it refuses the data of another major version (US-1130): `up --detach` shows no log.
service-up: ## Start the service platform: PostgreSQL, Redis, the migrations, the API, the worker and its schedule, the service of the restoration, Keycloak in HTTPS and its realm, OpenLDAP, Mailpit (needs the secrets of the guide, "Commandes")
	@$(COMPOSE_SERVICE) up --build --detach --wait postgres redis api worker scheduler keycloak keycloak-front-end openldap mailpit \
		|| { rc=$$?; $(COMPOSE_SERVICE) logs --no-color --no-log-prefix postgres-volume >&2; exit $$rc; }
	@$(MAKE) --no-print-directory keycloak-authority
	@$(COMPOSE_SERVICE) up --detach --wait --force-recreate --no-deps keycloak-realm
	@$(COMPOSE_SERVICE) up --build --detach --wait restore

# The bootstrap of the platform (US-0420), once its realm is applied: the link of the first
# administrator on the standard output, alone — its image built quietly first, and no terminal,
# which would mix the logs in —, and nothing on an installation whose administrator has set a
# password.
service-install: ## Bootstrap the installation of the service platform, started, and print the link of its first administrator (WATERFALL_ADMIN_EMAIL, WATERFALL_DEFAULT_LANGUAGE, WATERFALL_CURRENCY, WATERFALL_COMPANY_NAME)
	@$(COMPOSE_SERVICE) build --quiet install
	@$(COMPOSE_SERVICE) run --rm --no-TTY install

# The witness (EP-05), once the platform is bootstrapped: the examples of the contract written on it
# by `waterfall-api load-witness`, as the role of the service; run again, it writes nothing.
service-witness: ## Load the witness, the examples of the contract (fixtures/api), on the service platform, started and bootstrapped
	@$(COMPOSE_SERVICE) build --quiet witness
	@$(COMPOSE_SERVICE) run --rm --no-TTY witness

# The purge of what expired (EP-06, "La purge"), by hand: the verb the scheduler calls at each
# interval of WATERFALL_PURGE_INTERVAL, run in the container of the scheduler, which holds its
# settings. Two purges never run together: the verb takes a lock of its own.
service-purge: ## Purge what expired on the service platform, started: imports, deposits, exports, history (`waterfall-worker purge`)
	@$(COMPOSE_SERVICE) exec --no-TTY scheduler waterfall-worker purge

keycloak-authority: ## Copy out of the service platform the root of the authority of Keycloak's front end (KEYCLOAK_AUTHORITY)
	@mkdir -p $(dir $(KEYCLOAK_AUTHORITY))
	@$(COMPOSE_SERVICE) cp keycloak-front-end:/data/caddy/pki/authorities/local/root.crt $(KEYCLOAK_AUTHORITY)
	@echo "  -> $(KEYCLOAK_AUTHORITY)"

service-logs: ## Print the logs of the services of the platform (SERVICES, all of them by default)
	@$(COMPOSE_SERVICE) logs --no-color $(SERVICES)

service-down: ## Stop the service platform, the proxy of e2e-service included; WATERFALL_RESET_DATA=yes also drops its databases, its directory and its authority
	@$(COMPOSE_SERVICE) --profile e2e --profile install --profile witness down $(if $(filter yes,$(WATERFALL_RESET_DATA)),--volumes)

migrate: ## Apply the migrations to the database WATERFALL_DATABASE_URL designates (the guide, "Migrations")
	@cd $(BACK) && uv run --frozen waterfall-migrate

# The Compose files refuse to start without their secrets: validated with stand-ins that never run.
lint-compose: ## Validate the Compose files
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) config --quiet
	@WATERFALL_POSTGRES_PASSWORD=stand-in WATERFALL_SERVICE_DATABASE_PASSWORD=stand-in \
		WATERFALL_BACKUP_DATABASE_PASSWORD=stand-in \
		WATERFALL_REDIS_PASSWORD=stand-in WATERFALL_KEYCLOAK_DATABASE_PASSWORD=stand-in WATERFALL_KEYCLOAK_ADMIN_PASSWORD=stand-in \
		WATERFALL_FRONT_CLIENT_SECRET=stand-in WATERFALL_SERVICE_CLIENT_SECRET=stand-in \
		WATERFALL_INSTALLATION_CLIENT_SECRET=stand-in \
		WATERFALL_STORAGE_SECRET=stand-in WATERFALL_STORAGE_RPC_SECRET=stand-in \
		$(COMPOSE_SERVICE_FILE) --profile e2e --profile install --profile witness config --quiet
	@WATERFALL_DOMAIN=waterfall.localhost WATERFALL_ACME_EMAIL=stand-in WATERFALL_IMAGE_TAG=stand-in \
		WATERFALL_ADMIN_EMAIL=stand-in WATERFALL_SERVER_ACTIONS_KEY=stand-in \
		WATERFALL_CURRENCY=EUR WATERFALL_COMPANY_NAME=stand-in \
		WATERFALL_POSTGRES_ADMIN_PASSWORD=stand-in WATERFALL_POSTGRES_PASSWORD=stand-in WATERFALL_SERVICE_DATABASE_PASSWORD=stand-in \
		WATERFALL_BACKUP_DATABASE_PASSWORD=stand-in \
		WATERFALL_REDIS_PASSWORD=stand-in WATERFALL_KEYCLOAK_DATABASE_PASSWORD=stand-in WATERFALL_KEYCLOAK_ADMIN_PASSWORD=stand-in \
		WATERFALL_FRONT_CLIENT_SECRET=stand-in WATERFALL_SERVICE_CLIENT_SECRET=stand-in \
		WATERFALL_INSTALLATION_CLIENT_SECRET=stand-in \
		WATERFALL_STORAGE_SECRET=stand-in WATERFALL_STORAGE_RPC_SECRET=stand-in \
		$(COMPOSE_PRODUCTION) --profile install config --quiet
	@WATERFALL_DOMAIN=demo.localhost WATERFALL_ACME_EMAIL=stand-in WATERFALL_IMAGE_TAG=stand-in \
		WATERFALL_DEMO_USER=stand-in WATERFALL_DEMO_PASSWORD_HASH=stand-in \
		WATERFALL_SERVER_ACTIONS_KEY=stand-in PRISM_VERSION=$(PRISM_VERSION) \
		docker compose -f deploy/compose/compose.demo.yaml config --quiet
	@docker compose -f deploy/compose/compose.test.yaml config --quiet

build-keycloak: ## Build the image of Keycloak: the extension compiled and tested, the themes, the realm (deploy/keycloak)
	@docker build --build-arg WATERFALL_MIRROR $(call build-cache-from,keycloak) --tag $(WATERFALL_KEYCLOAK_IMAGE) deploy/keycloak

# The cache of the builds of the images on GitHub Actions (type=gha, .github/actions/build-cache):
# every build of an image reads it, under the name of the image (wftools.images); after a merge,
# images.yml writes it, each image built into it alone, neither loaded nor published. Docker leaves
# a cache of type gha out where the runtime of GitHub Actions is not given to it: on a workstation,
# both are without effect.
build-cache-from = --cache-from type=gha,scope=$(1)
build-cache-to = --output type=cacheonly --cache-to type=gha,mode=max,scope=$(1) $(call build-cache-from,$(1))

build-cache: ## Write the builds of the images front, waterfall and keycloak into the cache of GitHub Actions (images.yml)
	@docker build --build-arg WATERFALL_MIRROR --target production $(call build-cache-to,front) frontend
	@docker build --build-arg WATERFALL_MIRROR --target production $(call build-cache-to,waterfall) backend
	@docker build --build-arg WATERFALL_MIRROR --target production $(call build-cache-to,keycloak) deploy/keycloak

# The images the chain publishes (US-0430): front, waterfall and keycloak, under
# ghcr.io/waterfall-project, tagged by the commit and the branch they are built from, and by the
# version of the back's distribution on main, unless the registry holds it already: the tag of a
# version is immutable (wftools.images). The branch and the commit are the checkout's unless
# IMAGE_BRANCH and IMAGE_COMMIT name them, read by the tool from its environment. PUSH=yes publishes
# them, from main or an epic branch alone, from a clean checkout at the commit named, once the three
# are built and none holds a value of the development (.github/workflows/images.yml).
images: ## Build the images front, waterfall and keycloak, tagged by commit, by branch, and by version on main once; PUSH=yes publishes them
	@$(WFTOOLS).images $(if $(filter yes,$(PUSH)),--push)

# The production platform (compose.prod.yaml, US-0430) on the images tagged WATERFALL_IMAGE_TAG — the
# commit of the checkout by default —, built here or published, under a local name
# (WATERFALL_DOMAIN, waterfall.localhost by default) on ports 80 and 443 (WATERFALL_HTTP_PORT,
# WATERFALL_HTTPS_PORT): started, bootstrapped, its API's liveness and the sign-in of its first
# administrator held, then removed with its volumes (wftools.production). Its secrets come from the
# environment, as production.env.example names them; the project of Compose is
# WATERFALL_PRODUCTION_PROJECT (waterfall-production-trial). Outside the slots, at slot 0 alone: from
# the worktree of a lot, it would take the ports 80 and 443 of the workstation (US-1100).
production-trial: ## Start the production platform on the images of WATERFALL_IMAGE_TAG (the commit by default) under a local name, bootstrap it, hold its liveness and the sign-in of its first administrator, back it up and restore it by the API with WATERFALL_TRIAL_RESTORATION=1, then remove it (needs its secrets); at slot 0 alone, the main repository
	@[ "$$($(SLOTS) which 2>/dev/null)" = 0 ] || { echo "make production-trial runs at slot 0 alone, from the main repository, never from the worktree of a lot" >&2; exit 1; }
	@$(WFTOOLS).production

# The tests marked keycloak, which the other tests of the back deselect, against the Keycloak of the
# service platform, its realm applied, through its front end in HTTPS, whose authority alone they
# trust: at the address the browser knows it by, and at another one, 127.0.0.1, as a service
# reaches it. Those that serve the API in their process create their database on the PostgreSQL
# of the platform, unless WATERFALL_TEST_DATABASE_URL names another server. They measure the
# administration API of Keycloak and the bootstrap that creates the first administrator in it,
# which the measure of the back leaves out, to the thresholds of the back (coverage-keycloak.toml). Their environment is synchronised first, outside of
# SSL_CERT_FILE: uv reads it too, and would trust no other authority to download Python or the
# packages (#737). One of them restarts Keycloak, whose container is named to it (#852).
test-keycloak: ## Start Keycloak on the service platform, apply its realm, and try it, the API that validates its tokens and the bootstrap included, measuring its administration client and the bootstrap (needs the secrets of service-up)
	@$(COMPOSE_SERVICE) up --build --detach --wait keycloak keycloak-front-end openldap
	@$(MAKE) --no-print-directory keycloak-authority
	@$(COMPOSE_SERVICE) up --detach --wait --force-recreate --no-deps keycloak-realm
	@cd $(BACK) && uv sync --frozen
	@WATERFALL_TEST_KEYCLOAK_CONTAINER=$$($(COMPOSE_SERVICE) ps --quiet keycloak) && export WATERFALL_TEST_KEYCLOAK_CONTAINER && \
		cd $(BACK) && WATERFALL_TEST_KEYCLOAK_ADDRESS=$(KEYCLOAK_ADDRESS) \
		WATERFALL_TEST_KEYCLOAK_BACKCHANNEL=https://127.0.0.1:$${WATERFALL_KEYCLOAK_PORT:-8443}/auth \
		SSL_CERT_FILE=$(KEYCLOAK_AUTHORITY) \
		WATERFALL_TEST_FRONT_ADDRESS=$${WATERFALL_FRONT_ADDRESS:-http://localhost:3000} \
		WATERFALL_TEST_DATABASE_URL=$${WATERFALL_TEST_DATABASE_URL:-postgresql://waterfall:$${WATERFALL_POSTGRES_PASSWORD}@127.0.0.1:$${WATERFALL_POSTGRES_PORT:-5432}/postgres} \
		uv run --frozen --no-sync pytest -m keycloak --cov --cov-config=coverage-keycloak.toml --cov-report=json:coverage-keycloak.json
	@$(WFTOOLS).codecoverage coverage.py $(BACK)/coverage-keycloak.json

# --- The chain: one target per family of checks (tools/paths.toml) -----------------

check: ## Run the checks of what the change touches (BASE=origin/main by default)
	@targets=$$($(WFTOOLS).changes "$(BASE)" --targets) \
		|| { echo "  the family selection failed: no check ran" >&2; exit 1; }; \
	for target in $$targets; do \
		echo "== $$target"; $(MAKE) --no-print-directory $$target || exit 1; \
	done

check-all: check-repo check-repo-tools check-spec check-contract check-back check-front check-front-image check-roadmap check-keycloak check-service check-production ## Run every family of checks

check-repo: reuse lint-workflows lint-shell lint-docker lint-compose sources check-fixtures \
	requirements screens readmes ## Checks that run on any change

check-repo-tools: lint-tools typecheck-tools test-tools ## The tools of the repository: lint, types, tests

check-spec: build-doc-strict ## The projection builds without warning and is up to date
	@git diff --exit-code --stat -- $(SPEC)/waterfall-spec.md \
		|| { echo "  the projection is not the one the Word document produces: run make build-doc"; exit 1; }

check-contract: lint-openapi inventory mock-data-up-to-date server-models-up-to-date ## The contract lints, its inventory, its volumes and the models of the service are up to date
	@git diff --exit-code --stat -- $(API)/INVENTORY.md \
		|| { echo "  INVENTORY.md is not the one the contract produces: run make inventory"; exit 1; }

check-back: check-back-static check-back-tests ## The back: lint, types, boundaries, tests; coverage replaces the plain tests in the full tier

# The chain runs the back apart, as the front (back.yml): check-back-static on one runner,
# check-back-tests SHARD=i/N on each of the others, and in the full tier the measures of their parts
# gathered (coverage-back-merge). A part is the i-th of N of the tests, one in N in the order of their
# collection (four in the chain, SHARD=1/4 to 4/4): the files that load the witness, the longest,
# are spread over all the parts.
check-back-static: lint-back typecheck-back imports-back ## The back but its tests: lint, types, boundaries

check-back-tests: $(call full-else,coverage-back,test-back) ## The tests of the back, SHARD=i/N one part of them; in the full tier, measured

lint-back: ## Lint and format check of the back
	@cd $(BACK) && uv run --frozen ruff check . && uv run --frozen ruff format --check .

typecheck-back: ## Strict type check of the back
	@cd $(BACK) && uv run --frozen pyright

imports-back: ## The boundaries of the core (WF-ARC-0010)
	@cd $(BACK) && uv run --frozen lint-imports --no-cache

# The tests of the back wait on PostgreSQL, Redis and the storage more than they compute: they run on
# one process per core (pytest-xdist), eight at most — each takes a database of Redis of its own,
# which has sixteen. The tests of Keycloak (test-keycloak) stay on one: one of them restarts it.
PYTEST_WORKERS = -n $(WATERFALL_PROCESSORS) --maxprocesses 8
BACK_PART = $(if $(SHARD),--shard=$(SHARD))

test-back: ## Tests of the back (TESTS=<file> runs one file; SHARD=i/N one part of them, as the chain spreads them)
	@cd $(BACK) && $(TESTING_BACK) uv run --frozen pytest -q $(PYTEST_WORKERS) $(BACK_PART) $(TESTS)

# With SHARD, one part of the tests measured alone, its data kept apart for coverage-back-merge
# (backend/.coverage-parts/), out of the reach of the next measure, which erases the data files beside
# its own; the thresholds are held on the parts gathered alone.
coverage-back: ## Code coverage of the back: 90 % of lines, 85 % of branches (US-0060); SHARD=i/N measures one part of the tests, for coverage-back-merge
ifdef SHARD
	@cd $(BACK) && $(TESTING_BACK) uv run --frozen pytest $(PYTEST_WORKERS) --quiet --cov --cov-report= $(BACK_PART)
	@mkdir -p $(BACK)/.coverage-parts && mv $(BACK)/.coverage $(BACK)/.coverage-parts/.coverage.part-$(subst /,-of-,$(SHARD))
else
	@cd $(BACK) && $(TESTING_BACK) uv run --frozen pytest $(PYTEST_WORKERS) --quiet --cov --cov-report=json:coverage.json
	@$(WFTOOLS).codecoverage coverage.py $(BACK)/coverage.json
endif

coverage-back-merge: ## The code coverage of the back from the parts of coverage-back SHARD=i/N (backend/.coverage-parts/), held to the same thresholds
	@cd $(BACK) && uv run --frozen coverage combine --quiet --keep .coverage-parts \
		&& uv run --frozen coverage json --quiet -o coverage.json
	@$(WFTOOLS).codecoverage coverage.py $(BACK)/coverage.json

# The front in two halves, which the chain runs side by side (front.yml, e2e.yml); on a
# workstation, check-front runs both.
check-front: check-front-code check-front-e2e ## The front: check-front-code, then check-front-e2e

check-front-code: check-front-static $(call full-else,coverage-front,test-front) ## The front but its end-to-end paths: check-front-static, then the tests; coverage replaces the plain tests in the full tier

# The chain runs the tests of the front apart, over several runners (front.yml): check-front-static
# on one, check-front-tests SHARD=<part> on each of the others, and in the full tier the measure of
# their parts gathered (coverage-front-merge). A part is `lint`, the guards that run ESLint, a minute
# each (the project lint of frontend/vitest.config.ts), or i/N, the i-th of N parts of the others.
FRONT_PART = $(if $(filter lint,$(SHARD)),--project lint,$(if $(SHARD),--project node --project dom --shard=$(SHARD)))
check-front-static: client-up-to-date lint-front typecheck-front catalogs $(call full-else,,build-front prerendered-front) ## The front but its tests and its end-to-end paths: client, lint, types, catalogues, and in the fast tier its production build and what it prerendered

check-front-tests: $(call full-else,coverage-front,test-front) ## The tests of the front, SHARD=lint or i/N one part of them; in the full tier, measured

# The paths build the front for production, whose manifest prerendered-front then reads.
check-front-e2e: $(call full-only,e2e-browsers e2e prerendered-front) ## The end-to-end paths of the front, which build it for production, and what that build prerendered, in the full tier only

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

# The models of the service, engendered from the bundled contract (WF-ARC-0060). Ruff formats
# them with the rules of the repository, which they only find under the repository: the check
# writes its copy beside the versioned one. An address is a plain text in them: the service gives
# it back as it is held, which pydantic's EmailStr would refuse for a special-use domain and
# rewrite in lower case; what an address in input must be is decided apart (#665).
SERVER_MODELS := $(BACK)/src/waterfall/api/contract/models.py
CODEGEN := cd $(BACK) && uv run --frozen datamodel-codegen --input ../$(BUNDLE) --input-file-type openapi \
	--output-model-type pydantic_v2.BaseModel --target-python-version 3.14 --use-annotated \
	--disable-timestamp --type-mappings email=string --formatters ruff-format ruff-check --output

generate-server-models: build-openapi ## Regenerate the Pydantic models of the service from the contract
	@( $(CODEGEN) "$(abspath $(SERVER_MODELS))" )
	@echo "  -> $(SERVER_MODELS)"

server-models-up-to-date: build-openapi ## The versioned models of the service are the ones the contract produces
	@tmp=$$(mktemp -d -p $(abspath $(BACK))); \
		( $(CODEGEN) "$$tmp/models.py" ) && diff -q "$$tmp/models.py" $(SERVER_MODELS) >/dev/null; \
		status=$$?; rm -rf "$$tmp"; \
		[ $$status -eq 0 ] || { echo "  the models are not the ones the contract produces: run make generate-server-models"; exit 1; }

lint-front: install-front ## Lint and format check of the front
	@$(PNPM) lint
	@$(PNPM) format:check

typecheck-front: install-front ## Strict type check of the front
	@$(PNPM) typecheck

# The contract is bundled here, never read from a bundle left on the disk by an older run.
catalogs: ## The catalogues of the front are twins, with a key for each value the contract codes (WF-QUA-0070)
	@cd $(API) && $(REDOCLY) bundle openapi.yaml --ext json -o $(notdir $(JSON_BUNDLE)) >/dev/null
	@$(WFTOOLS).catalogs $(JSON_BUNDLE) $(FRONT)/messages/fr.json $(FRONT)/messages/en.json

test-front: install-front ## Unit tests of the front (TESTS=<file> runs one file; SHARD=lint or i/N one part of them, as the chain spreads them)
	@$(PNPM_TESTING) test $(FRONT_PART) $(TESTS)

build-front: export WATERFALL_API_ADDRESS = $(NOWHERE)
build-front: install-front ## Build the front for production with no API to reach, no page reading it while built (#131); in the fast tier, the full one builds it for the end-to-end paths
	@$(PNPM_HEAVY) build

# What the last production build of the front prerendered, read from the manifest it wrote, without
# Docker: build-front's, in the fast tier as for the end-to-end paths in the full one, which
# prerenders as the image does (wftools.frontimage, US-0430).
prerendered-front: ## The production build of the front prerendered no page that reads the environment, as its image would not (US-0430)
	@$(WFTOOLS).frontimage --manifest $(FRONT)/.next/prerender-manifest.json

# With SHARD, one part of the tests measured alone, its report written for coverage-front-merge
# (frontend/.vitest/blob/), the thresholds held on the parts gathered alone. Beside the blob, which
# says nothing of a test that fails, the dot reporter names it and its error in the log of the part:
# a part of the chain that failed silent cost a run to diagnose (US-0590b). The part lint, the
# guards that run ESLint, is played and not measured: they cover nothing of src/, and measured they
# took three times as long, the first test of a guard starving on its minute while three of them
# built the program of the project at once (#2015); no report of theirs is written or gathered.
FRONT_MEASURE = $(if $(filter lint,$(SHARD)),,--coverage --reporter=blob)
coverage-front: install-front ## Code coverage of the front: 90 % of lines, 85 % of branches (US-0060); SHARD=i/N measures one part of the tests, for coverage-front-merge; SHARD=lint plays the guards, which cover nothing, unmeasured
ifdef SHARD
	@$(PNPM_TESTING) exec vitest run --silent $(FRONT_PART) $(FRONT_MEASURE) --reporter=dot
else
	@$(PNPM_TESTING) exec vitest run --coverage --silent
	@$(WFTOOLS).codecoverage istanbul $(FRONT)/coverage/coverage-summary.json
endif

coverage-front-merge: install-front ## The code coverage of the front from the parts of coverage-front SHARD=i/N (frontend/.vitest/blob/), held to the same thresholds
	@$(PNPM) exec vitest run --merge-reports --coverage --silent
	@$(WFTOOLS).codecoverage istanbul $(FRONT)/coverage/coverage-summary.json

check-roadmap: roadmap ## The roadmap and the requirements agree (US-0070)

check-keycloak: build-keycloak test-keycloak test-openldap ## The image of Keycloak builds, its realm applies and its extension answers (US-0350); the entrypoint of the directory seeds its volumes

# The production image of the front, which the chain publishes after a merge alone (images.yml),
# built and started at a pull request that changes what makes it (wftools.frontimage, US-0430).
check-front-image: ## The production image of the front builds, starts and answers /, refuses the fake back, and prerenders no page that reads the environment (US-0430)
	@$(WFTOOLS).frontimage

check-service: $(call full-only,e2e-service) ## The paths against the real service, in the full tier only (US-0340)

# The three images built as the chain publishes them, never pushed, then the production platform on
# them (production-trial): in the full tier only, as images.yml does again on the images it published.
check-production: $(call full-only,images production-trial) ## The production platform starts on the images built here, bootstraps and lets its first administrator in, in the full tier only (US-0430)

roadmap: ## Confront the stories of docs/roadmap with the requirements of the document
	@$(WFTOOLS).roadmap

e2e-browsers: install-front ## Install the browser the end-to-end tests run in
	@$(PNPM) exec playwright install $(PLAYWRIGHT_INSTALL) chromium

# The work image of the end-to-end paths (deploy/e2e, US-1900): Playwright's, with make, the Python
# of the tools, pnpm and Docker's client, so that no job of the paths downloads a package of Ubuntu
# (#2913). Tagged by the hash of its directory, it is found in the registry, or built here, and
# published with PUSH=yes, which the full tier of the chain runs before the paths, the fast one
# building without it (ci.yml); the line it prints, image=<reference>, is the output of that step
# (wftools.e2eimage).
e2e-image: ## Find the work image of the end-to-end paths in the registry by the hash of deploy/e2e, or build it — PUSH=yes publishes it —; prints image=<reference>
	@$(WFTOOLS).e2eimage publish $(if $(filter yes,$(PUSH)),--push)

mirror: ## Check that ghcr.io holds the images of Docker Hub the files name under mirror/, by their digest — PUSH=yes copies those it does not hold (wftools.mirror, US-1900)
	@$(WFTOOLS).mirror $(if $(filter yes,$(PUSH)),--push)

# E2E_IMAGE, the reference of that image, plays the browser of the paths against the service in it
# (service.yml): Playwright's server (run-server) runs in the image, on the network of the host, and
# `playwright test` connects to it from the runner (PW_TEST_CONNECT_WS_ENDPOINT), where Node, the front
# and the harness stay. The browser and its system packages are the image's, where the runner would
# install them from the mirrors of Ubuntu. The paths played whole in the image took 17.3 minutes of
# `playwright test` in the median of four runs, against 14.2 in three so (US-1900). The server is
# stopped with the shell, after the paths. Empty, on a workstation, the paths play on it.
E2E_IMAGE ?=
E2E_BROWSER_PORT ?= 3990
e2e-in-image = uv run --frozen --project $(CURDIR)/$(TOOLS) python -m wftools.e2eimage run --image $(E2E_IMAGE) --
e2e-browser = $(if $(E2E_IMAGE),$(e2e-in-image) node node_modules/@playwright/test/cli.js run-server --host 127.0.0.1 --port $(E2E_BROWSER_PORT) & browser=$$! && trap 'kill $$browser' EXIT && timeout 120 sh -c 'until curl --silent --output /dev/null http://127.0.0.1:$(E2E_BROWSER_PORT)/; do sleep 1; done' && export PW_TEST_CONNECT_WS_ENDPOINT=ws://127.0.0.1:$(E2E_BROWSER_PORT)/ &&)

# The paths play against the front built for production (US-0590): built first by build-front, which
# Next's cache (.next/cache) shortens after the first time, then started by the harness, told it is
# built (E2E_BUILT). E2E_BUILT=1 set already says the front is built — the chain builds it once for
# all its parts (front-build, ci.yml) —, and E2E_DEV_SERVER=1, on a workstation, plays the paths against next
# dev, which needs no build; the measure never follows it (frontend/playwright.config.ts).
E2E_BUILT ?=
E2E_DEV_SERVER ?=
e2e-build = $(if $(filter 1,$(E2E_BUILT) $(1)),,build-front)

# With SHARD, the paths alone (E2E_PART, frontend/playwright.config.ts): the measure, which
# waits for all of them, would bring every path into each part; e2e-measure plays it apart.
e2e: export E2E_PART = $(if $(SHARD),paths)
e2e: export E2E_BUILT = 1
e2e: export E2E_WORKERS = $(WORKERS)
e2e: install-front mock-tools $(call e2e-build,$(E2E_DEV_SERVER)) ## End-to-end paths, against the fake back that Playwright starts (US-0080), on the front built for production; SHARD=i/N plays the i-th of N parts of them, without the measure; WORKERS=n (1 to 40, by default half the processors, at most 40) plays them on n workers; TESTS=<file> plays one file (not with SHARD); E2E_DEV_SERVER=1 plays them against next dev, on a workstation
	@$(if $(and $(SHARD),$(TESTS)),$(error SHARD and TESTS do not combine: the file may be in another part))$(if $(SHARD),dir=$$(mktemp -d) && trap 'rm -rf "$$dir"' EXIT && ( $(PNPM) exec playwright test --list > "$$dir/listing" ) && $(WFTOOLS).e2eparts plan $(SHARD) < "$$dir/listing" > "$$dir/part" && )$(PNPM_HEAVY) exec playwright test $(if $(SHARD),--test-list="$$dir/part") $(TESTS)

# Rewrite tools/e2e-durations.json, the seconds each unit of the paths took, from the log of a run
# (LOG=<file>, the list reporter's output of a make e2e, or of the job of a part in the chain; the
# standard input without it), for the parts of make e2e SHARD=i/N (wftools.e2eparts, US-1910).
e2e-durations: ## Refresh the durations the parts of the end-to-end paths are spread by, from the log of a run of make e2e (LOG=<file>, standard input without it)
	@$(WFTOOLS).e2eparts refresh $(if $(filter command line,$(origin LOG)),$(LOG))

e2e-measure: export E2E_PART = measure
e2e-measure: export E2E_BUILT = 1
e2e-measure: install-front mock-tools $(call e2e-build) ## The measure of the second of §4.6.2 alone, against the front built for production (US-0110)
	@$(PNPM_HEAVY) exec playwright test

# The paths of the Playwright project `service` (frontend/e2e/service/), against the real service:
# the platform started — its realm applied with the address of the front of the harness, and the
# address Keycloak reaches it at from its container (#681) —, and Prism between the front and the
# API (`--errors`): an answer outside its schema, or an operation outside the contract, fails the
# path (WF-ARC-0060). The front is the harness's, on the workstation, with the real authentication:
# it trusts the authority of Keycloak's front end and keeps its sessions in the Redis of the
# platform. The platform stays up afterwards: make service-down stops it. The addresses of the front
# are the harness's, whatever the environment exports; the variables of the front go through the
# environment, never the command line, which would show the password of Redis to anyone. The paths
# are given the containers of the proxy, whose log they read, and of PostgreSQL, where they give the
# person of the directory and the one of the external provider a role, as an administrator would.
# The platform is bootstrapped (US-0420, #730): the paths read the address of its first
# administrator in E2E_ADMIN_EMAIL, and in E2E_INSTALLATION_LINK the link that sets its password —
# empty once a path has set it, the administrator then signing in with the constant password of the
# paths. Through it, each path signs in as an account of its own, on several workers. The address
# must be the one the platform was first bootstrapped with: a bootstrap run again ignores another
# one (the guide, « Un parcours de bout en bout »). The witness is loaded once it is bootstrapped
# (EP-05), as make service-witness does: the paths of the reference read what the examples say.
E2E_ADMIN_EMAIL ?= administrateur@waterfall.test
# The workers of the paths against the service (#2890): three quarters of the processors of the slot
# (WATERFALL_PROCESSORS), at least 1, at most 40 (the fronts of a slot), instead of the half of the
# processors of the workstation that playwright.config.ts takes, 16 of 32, where 18 to 23 paths
# failed to navigate. Measured on 8 processors (US-1930): 8 workers and more failed to navigate in
# two passes, no failure to navigate at 6. An E2E_WORKERS given, in the environment or on the command
# line, wins (an empty one does not count); a WATERFALL_PROCESSORS that is not a positive integer is
# refused, where the default is read only.
E2E_WORKERS_GIVEN := $(E2E_WORKERS)
E2E_SERVICE_PROCESSORS = $(if $(shell printf '%s' '$(WATERFALL_PROCESSORS)' | grep -Eq '^[1-9][0-9]*$$' && echo ok),$(WATERFALL_PROCESSORS),$(error WATERFALL_PROCESSORS must be a positive integer, got '$(WATERFALL_PROCESSORS)'))
E2E_SERVICE_WORKERS = $(shell workers=$$(($(E2E_SERVICE_PROCESSORS) * 3 / 4)); echo $$((workers < 1 ? 1 : (workers > 40 ? 40 : workers))))
e2e-service: export E2E_WORKERS = $(or $(E2E_WORKERS_GIVEN),$(E2E_SERVICE_WORKERS))
e2e-service: export WATERFALL_FRONT_ADDRESS = http://127.0.0.1:$(E2E_FRONT_PORT)
e2e-service: export WATERFALL_FRONT_BACKCHANNEL = http://host.docker.internal:$(E2E_FRONT_PORT)
e2e-service: export E2E_PART = service
e2e-service: export WATERFALL_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
e2e-service: export E2E_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
e2e-service: export E2E_BUILT = 1
e2e-service: install-front mock-tools $(call e2e-build,$(E2E_DEV_SERVER)) ## End-to-end paths of the project `service` against the real service, through Prism as a proxy, on the front built for production (needs the secrets of service-up and a browser, make e2e-browsers); TESTS=<arguments of playwright test>: a file alone also plays installation and, with a @realm-wide or @platform-wide path, the projects its own depends on; TESTS="--no-deps --project=shared --project=realm <files>" plays only the files, on an installation already played
	@$(MAKE) --no-print-directory mock-spec MOCK_SPEC=$(PROXY_SPEC)
	@$(MAKE) --no-print-directory service-up
	@$(COMPOSE_SERVICE) up --detach --wait contract-proxy
	@$(COMPOSE_SERVICE) build --quiet install witness
	@E2E_INSTALLATION_LINK=$$($(COMPOSE_SERVICE) run --rm --no-TTY install) && \
		$(COMPOSE_SERVICE) run --rm --no-TTY witness && \
		E2E_CONTRACT_PROXY=$$($(COMPOSE_SERVICE) ps --quiet contract-proxy) && \
		E2E_SERVICE_DATABASE=$$($(COMPOSE_SERVICE) ps --quiet postgres) && \
		WATERFALL_API_ADDRESS=http://127.0.0.1:$(WATERFALL_PROXY_PORT) && \
		WATERFALL_KEYCLOAK_ADDRESS=$(KEYCLOAK_ADDRESS) && \
		WATERFALL_REDIS_URL=redis://:$${WATERFALL_REDIS_PASSWORD}@127.0.0.1:$${WATERFALL_REDIS_PORT:-6379}/0 && \
		NODE_EXTRA_CA_CERTS=$(KEYCLOAK_AUTHORITY) && \
		export E2E_INSTALLATION_LINK E2E_CONTRACT_PROXY E2E_SERVICE_DATABASE WATERFALL_API_ADDRESS WATERFALL_KEYCLOAK_ADDRESS WATERFALL_REDIS_URL NODE_EXTRA_CA_CERTS && \
		cd $(FRONT) && { $(e2e-browser) $(PNPM_ENV) pnpm exec playwright test $(TESTS); }

# The slot of the worktree, among the N of WATERFALL_SLOTS, in the register of the workstation
# ($XDG_RUNTIME_DIR/waterfall-slots, /tmp/waterfall-slots without it), whatever the repository.
slot: ## Take a slot of 1 to N for this worktree of a lot — its ports and its names —, or say the one it holds; fails, naming the holders, when all are taken
	@$(SLOTS) claim

slot-release: ## Stop the servers of the e2e paths, remove the containers and volumes of the slot of this worktree — the service platform, the services of the tests —, then free it
	@$(SLOTS) release

e2e-down: ## Stop the servers of the end-to-end paths of the slot of this worktree — the fake back, the fronts —, found by their ports and stopped by PID; after an interrupted e2e, e2e-service or check-front (US-1300)
	@$(SLOTS) stop-servers

slots: ## Print N, then the slots taken on the workstation and their worktrees
	@$(SLOTS) list

# PostgreSQL 18, Redis and Garage of the platform, in memory, on the ports of the slot of the worktree
# (WATERFALL_TEST_POSTGRES_PORT, _REDIS_PORT, _STORAGE_PORT): what the tests of the back and of the
# front are given by make test-back and the others, unless their WATERFALL_TEST_*_URL says otherwise.
test-services: ## Start, for the slot of this worktree, the services the tests run against — PostgreSQL, Redis, Garage — and wait for them; running, they stay as they are (SERVICES=<some of them>)
	@$(COMPOSE_TEST) up --detach --wait $(SERVICES)

test-services-down: ## Remove the services of the tests of the slot of this worktree, their volumes included
	@$(COMPOSE_TEST) down --volumes

lot-size: ## The real size of a lot, against its epic (BASE=origin/epic/EP-nn); never fails
	@$(WFTOOLS).lotsize "$(BASE)" $(HEAD)

# A variable of the table is taken only when it comes from the command line of make: one exported
# on the workstation (PR, STATE, MODEL…) must not overwrite a cell of the shared table. Make
# exports the command-line variables to the recipe; an empty value is ignored.
tracking_option = $(if $(filter command line,$(origin $(1))),$${$(1):+$(2) "$$$(1)"})

tracking: ## Change a line of the tracking table of an epic's issue, under a lock: ISSUE=<n> with LOT=<id> [STATE PR MODEL DEPENDS], US=<id> STATUS=…, FINDING=<n> ATTACHED=… DECISION=…, ADD_LOT=<id> AFTER=<lot> [DEPENDS MODEL LOT_ISSUE], or REPLACE_DEPENDENCY='<old>=<new>'
	@$(WFTOOLS).tracking $(call tracking_option,ISSUE,--issue) $(call tracking_option,LOT,--lot) \
		$(call tracking_option,US,--us) $(call tracking_option,FINDING,--finding) \
		$(call tracking_option,STATE,--state) $(call tracking_option,PR,--pr) \
		$(call tracking_option,MODEL,--model) $(call tracking_option,STATUS,--status) \
		$(call tracking_option,ATTACHED,--attached) $(call tracking_option,DECISION,--decision) \
		$(call tracking_option,ADD_LOT,--add-lot) $(call tracking_option,AFTER,--after) \
		$(call tracking_option,DEPENDS,--depends) $(call tracking_option,LOT_ISSUE,--issue-number) \
		$(call tracking_option,REPLACE_DEPENDENCY,--replace-dependency)

merge-queue: ## Create the merge queue ruleset of an epic's branch from .github/rulesets/merge-queue.json (EPIC=EP-nn); for a person, never a deliverer
	@$(WFTOOLS).mergequeue create "$(EPIC)"

merge-queue-check: ## Check that an active ruleset with a merge queue targets an epic's branch (EPIC=EP-nn)
	@$(WFTOOLS).mergequeue check "$(EPIC)"

# The runs of the merge queue of a branch, read by gh from a workstation, never in the chain: their
# failures by job and step, the tests and paths that failed, classified against
# tools/queue-known.toml, the wall time and the runner minutes (wftools.queue, US-1880).
queue-report: ## Report the merge queue runs of the chain on a branch and classify their failures (BRANCH=epic/EP-nn or main, all if empty; LAST=<n>, 50 by default; SINCE=YYYY-MM-DD)
	@$(WFTOOLS).queue --branch "$(BRANCH)" --last "$(LAST)" --since "$(SINCE)"

changes: ## Print which families of checks the change touches (BASE; HEAD, or the working tree)
	@$(WFTOOLS).changes "$(BASE)" $(HEAD)

gate: ## Decide the outcome of the chain from its jobs (NEEDS, from GitHub Actions)
	@$(WFTOOLS).gate

check-tools: ## Report which prerequisites are missing
	@for t in python3 pandoc node npx pnpm uv docker; do \
		command -v $$t >/dev/null && echo "  ok       $$t" || echo "  missing  $$t"; \
	done
	@if [ ! -f $(TOOLS)/.python-version ]; then echo "  missing  $(TOOLS)/.python-version"; else \
		v=$$(cut -d. -f1,2 $(TOOLS)/.python-version); \
		python3 --version 2>/dev/null | grep -q "^Python $$(echo "$$v" | sed 's/\./\\./g')\." \
		|| echo "  warning  python3 is not $$v, the version of $(TOOLS)/.python-version: the guard and the slots would run by another"; \
	fi
	@command -v pandoc >/dev/null && pandoc --version | head -1 | grep -q " 3.13$$" \
		|| echo "  warning  pandoc is not 3.13: the projection would differ from the chain's"
	@/usr/bin/pg_restore --version 2>/dev/null | grep -q " 18\." \
		|| echo "  warning  /usr/bin/pg_restore is not PostgreSQL 18, the server's: the tests of the backups and restorations would fail (#982)"
	@command -v mmdc >/dev/null && echo "  ok       mmdc" || echo "  absent   mmdc (diagrams will not be validated)"

clean: ## Remove everything the commands generate
	@rm -rf $(SPEC)/.build $(SPEC)/images $(BUNDLE) $(JSON_BUNDLE) $(MOCK_SPEC) $(PROXY_SPEC) $(FRONT)/.e2e
	@echo "  cleaned"

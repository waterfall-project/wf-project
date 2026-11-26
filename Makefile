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
# WATERFALL_KEYCLOAK_LOADED=1 says the image of Keycloak was loaded (load-keycloak): the platform then
# starts it as it is and never builds it again (ci.yml builds it, service.yml loads it, #4790).
COMPOSE_SERVICE_FILE = PRISM_VERSION=$(PRISM_VERSION) docker compose -f deploy/compose/compose.service.yaml \
	$(if $(WATERFALL_KEYCLOAK_LOADED),-f deploy/compose/compose.keycloak-loaded.yaml)
COMPOSE_SERVICE = $(COMPOSE_SERVICE_FILE) -p $(WATERFALL_SERVICE_PROJECT)
# The profiles of the services of that file the platform starts: service-down stops them, and the
# logs are read under them, Compose leaving out of its commands the services of a profile not given.
SERVICE_PROFILES = e2e install witness load
COMPOSE_SERVICE_ALL = $(COMPOSE_SERVICE) $(addprefix --profile ,$(SERVICE_PROFILES))
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
FRONT_LOG = $(FRONT)/.e2e/front.log
# An address where no API answers: the front builds without reaching one (#131).
NOWHERE := http://127.0.0.1:9
PNPM_ENV := NEXT_TELEMETRY_DISABLED=1
PNPM    := cd $(FRONT) && $(PNPM_ENV) pnpm
# pnpm for a heavy run, which waits for its turn (tools/src/wftools/slots.py).
# The front takes the same share as the back (WATERFALL_PROCESSORS), a run of one file (TESTS) too.
PNPM_HEAVY = cd $(FRONT) && $(heavy) $(PNPM_ENV) WATERFALL_PROCESSORS=$(WATERFALL_PROCESSORS) pnpm
# pnpm for the unit tests of the front, which have the Redis of the slot of the worktree (TESTING_FRONT).
PNPM_TESTING = cd $(FRONT) && $(TESTING_FRONT) $(PNPM_ENV) WATERFALL_PROCESSORS=$(WATERFALL_PROCESSORS) pnpm
# Pinned so that a check passes or fails on what this repository contains, never on what a tool
# released overnight: Redocly and Prism are exact development dependencies of the front, locked
# by frontend/pnpm-lock.yaml and read from the store of pnpm that `make install-front` fills, never
# downloaded by `npx` from the registry of npm at each run (#2913). Raise a version in
# frontend/package.json and nowhere else; the Makefile reads it from there (Compose names Prism's).
PRISM_VERSION := $(shell sed -n 's/^ *"@stoplight\/prism-cli": *"\([^"]*\)".*/\1/p' $(FRONT)/package.json)
REDOCLY := $(abspath $(FRONT))/node_modules/.bin/redocly
PRISM   := $(abspath $(FRONT))/node_modules/.bin/prism
# What the recipes that run them need first: the installation of the front, unless it is newer than
# the lock file and package.json (the witness is the file pnpm keeps in node_modules, which
# `make install-front` touches too). A raised version installs again; the fake back, started by
# several processes of the harness, does not install at once when `make e2e` has installed before.
FRONT_WITNESS := $(FRONT)/node_modules/.modules.yaml
FRONT_TOOLS = $(FRONT_WITNESS)

.DEFAULT_GOAL := help
.PHONY: help build-doc build-doc-strict build-openapi lint-openapi inventory allocate-pbs mock \
	mock-spec mock-data mock-data-up-to-date dev dev-down lint-compose service-up service-install service-witness service-purge service-logs service-logs-search service-logs-fields service-down measure-core migrate \
	build-keycloak save-keycloak load-keycloak build-cache test-keycloak check-keycloak keycloak-authority e2e-service check-service images \
	production-trial check-production kube-tools lint-chart test-chart chart-trial check-chart \
	test-tools test-openldap lint-tools typecheck-tools sources fixtures check-fixtures requirements \
	requirements-release screens implementations readmes reuse lint-workflows \
	lint-shell check slot slot-release e2e-down slots test-services test-services-down \
	check-all check-repo check-repo-tools check-spec \
	check-contract check-back check-back-static check-back-tests coverage-back-merge lint-back typecheck-back imports-back test-back check-front \
	check-front-code check-front-e2e check-front-image \
	install-front lint-front typecheck-front test-front build-front prerendered-front generate-client client-up-to-date generate-server-models server-models-up-to-date catalogs \
	coverage-back coverage-front roadmap check-roadmap check-measures e2e e2e-durations e2e-measure e2e-browsers e2e-image mirror mirror-sync lot-size measure-reference tracking merge-queue merge-queue-check queue-report \
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
# §4.6.2 on one more (e2e.yml). Empty, it plays them all. `make e2e-service SHARD=i/N` plays a
# part of the paths against the service, each on a platform of its own (service.yml).
SHARD ?=
# SHARD=lint is the part of check-front-tests and test-front alone: the guard below refuses it on the
# other goals.
# A part of the paths does not combine with a file of them: the file may be in another part.
# Refused as the Makefile is read, before the installation and the build of the front, which the
# recipe would otherwise wait for to say so (#3026). Every goal that reaches the paths is named,
# the families that run them included.
E2E_PATH_GOALS := e2e e2e-service check-service check-front-e2e check-front check-all check
ifneq ($(and $(SHARD),$(TESTS),$(filter $(E2E_PATH_GOALS),$(MAKECMDGOALS))),)
$(error SHARD and TESTS do not combine for the end-to-end paths: the file may be in another part)
endif
# How many workers `make e2e` plays the paths on (E2E_WORKERS, frontend/playwright.config.ts), each
# against a front of its own: fewer than Playwright takes by itself on a loaded workstation, where
# paths fail by a timeout (#736). From 1 to 40: a front per worker, forty ports per slot. Empty, its
# own: half the processors, at most 40.
WORKERS ?=
# N heavy runs at a time on the workstation (WATERFALL_SLOTS, 1 by default): the whole tests of a
# side, their coverage, the production build of the front, the end-to-end paths. Several agents
# running them side by side ran out of memory (2026-10). tools/src/wftools/slots.py admits them
# (a free slot among N lock files of the directory of the locks of the workstation, the first the
# one of before N existed), keeps the slot until the run ends and sets WATERFALL_PROCESSORS, the
# share of the processors of one run. A run of one file (TESTS) does not wait; on a runner of the
# chain, alone, a slot is always free. `env` keeps the variables set before the command a command
# of their own. It runs by tools/src/wftools/launch.py, which says the version it expects under a
# python3 older than the one of the tools, instead of their SyntaxError (US-2450).
SLOTS = python3 $(CURDIR)/tools/src/wftools/launch.py slots
heavy = $(if $(TESTS),,$(SLOTS) run --heavy -- env)
# A measure takes the workstation for itself alone (US-2210): every slot of the heavy runs, in a
# fixed order, once those in progress have ended; the heavy runs started meanwhile wait for it. The
# light work of the other deliverers goes on. TESTS changes nothing: a measure is never a light run.
exclusive = $(SLOTS) run --exclusive -- env
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
# GNU make 4.4 exports the exported variables to each $(shell), so it expands E2E_WORKERS (which
# reads this share) to prepare the very $(shell) that computes it, and reads the share empty
# (#3029): WATERFALL_PROCESSORS_READING tells E2E_SERVICE_PROCESSORS not to read it meanwhile. The
# rule from now on: an exported variable that reads the share goes through E2E_SERVICE_PROCESSORS
# (or tests the flag), and tools/tests/test_e2eworkers.py keeps it under 4.4.
# The share is the one word of digits the tool prints on its standard output, when it ends by 0: a
# warning on its error output does not spoil it. Without a share, make relays what the tool said on
# its error output instead: the setting it refuses, or why it did not run (US-2450). The tool runs
# once: its standard output goes to s, its error output to e by the descriptor 3, and the share to
# make by the descriptor 5. What the tool said on its standard output instead of a share is relayed
# after its error output, and the final point of the reason is dropped: make's own closes it. The
# words of the tool are not read again as make: the $(shell) is escaped ($$) in the eval, which
# assigns its output as it is, so that a `$` or a `#` it says (in the path of python3, say) stays a
# letter.
SLOTS_PROCESSORS = $(if $(filter-out undefined,$(origin WATERFALL_SLOTS)),WATERFALL_SLOTS='$(subst ','\'',$(WATERFALL_SLOTS))') $(SLOTS) processors
SHARE_OR_REASON = { e=$$( { s=$$($(SLOTS_PROCESSORS) 2>&3 3>&-); if [ $$? -eq 0 ] && [ -n "$$s" ] && [ -z "$$(printf %s "$$s" | tr -d 0-9)" ]; then printf '%s\n' "$$s" >&5; else [ -z "$$s" ] || printf '%s\n' "$$s"; false; fi; } 3>&1 ) || printf '%s\n' "$${e%.}"; } 5>&1
nondigits = $(subst 0,,$(subst 1,,$(subst 2,,$(subst 3,,$(subst 4,,$(subst 5,,$(subst 6,,$(subst 7,,$(subst 8,,$(subst 9,,$(1)))))))))))
WATERFALL_PROCESSORS ?= $(eval WATERFALL_PROCESSORS_READING = 1)$(eval WATERFALL_PROCESSORS_SHARE := $$(shell $$(SHARE_OR_REASON)))$(eval WATERFALL_PROCESSORS_READING =)$(if $(and $(filter 1,$(words $(WATERFALL_PROCESSORS_SHARE))),$(if $(call nondigits,$(WATERFALL_PROCESSORS_SHARE)),,share)),$(WATERFALL_PROCESSORS_SHARE),$(error no share of the processors from the tool of the slots: $(or $(WATERFALL_PROCESSORS_SHARE),it said nothing)))

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
SLOT_PATHS := E2E_API_PORT E2E_FRONT_PORT E2E_METRICS_FRONT_PORT E2E_METRICS_PORT
$(call slot-export,service-up service-install service-witness service-purge keycloak-authority service-logs service-logs-search service-logs-fields service-down service-api-processes \
	test-keycloak e2e-service,$(SLOT_SERVICE))
# e2e-down is not tolerant of a worktree without a slot, on purpose: its first command, stop-servers,
# already stops on "run make slot" (US-1300), because without a slot there are no ports to look at and
# no load container (named after the slot's project) to stop — nothing was started by this worktree.
# Being tolerant for the container alone would hide the same refusal one command later (#3429).
$(call slot-export,e2e-down,WATERFALL_SERVICE_PROJECT)
$(call slot-export,build-keycloak save-keycloak load-keycloak,WATERFALL_KEYCLOAK_IMAGE)
$(call slot-export,test-services test-services-down,WATERFALL_TEST_PROJECT \
	WATERFALL_TEST_POSTGRES_PORT WATERFALL_TEST_REDIS_PORT WATERFALL_TEST_STORAGE_PORT)
$(call slot-export,e2e e2e-measure e2e-service,$(SLOT_PATHS))
$(call slot-export,check-front-image,WATERFALL_FRONT_CHECK_IMAGE)

full-only = $(if $(filter full,$(TIER)),$(1))
# The coverage run executes the same tests: in the full tier it replaces the plain run.
full-else = $(if $(filter full,$(TIER)),$(1),$(2))
WFTOOLS := uv run --frozen --project $(TOOLS) python -m wftools
# A command of Docker that resolves the images of the mirror, tried again when ghcr.io does not answer
# (#4894); `env` lets it be given variables first, as COMPOSE_SERVICE is. Never read the standard
# output of a wrapped command (`$(shell …)`, a pipe): retried returns it on the standard error.
RETRIED := $(WFTOOLS).retried -- env
# A part of the paths of a shape the plan refuses (i/N, N >= 2) is refused as the Makefile is read
# too, before the installation and the build of the front, whichever goal of the paths asks for it
# (#3108): one guard for all of E2E_PATH_GOALS. Two things keep the value from a shell. SHARD_BAD
# judges the characters first: a value that is not digits and one slash never gets further (an
# apostrophe closed the quotes the value was between). What passes reaches the tool by the
# shell variable the command sets itself, not in the quotes of its text: WATERFALL_SHARD_ASKED is set
# and exported inside the $(shell) command, so nothing depends on make handing its exported
# variables to $(shell) (GNU make 4.4 does, the 4.3 of the e2e image does not). Interpolating
# $(SHARD) there is safe: $(or) does not expand its later arguments once one is non-empty, so a
# value that reaches the $(shell) passed SHARD_BAD, and is digits and one slash alone.
# `nondigits` is the one above. SHARD=lint is the part of check-front-tests and test-front alone:
# check, check-front, check-all and e2e refuse it here.
SHARD_BAD = $(or $(word 2,$(SHARD)),$(call nondigits,$(subst /,,$(SHARD))))
ifneq ($(and $(SHARD),$(filter $(E2E_PATH_GOALS),$(MAKECMDGOALS))),)
ifneq ($(or $(SHARD_BAD),$(shell WATERFALL_SHARD_ASKED=$(SHARD); export WATERFALL_SHARD_ASKED; $(WFTOOLS).e2eparts service-part "$$WATERFALL_SHARD_ASKED" >/dev/null 2>&1 || echo refused)),)
$(error SHARD must be i/N with 1 <= i <= N and N >= 2 for the paths: $(SHARD))
endif
endif

help: ## List the commands
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

build-doc: ## Regenerate the Markdown projection from Word and draw.io
	@$(SPEC)/build.sh

build-doc-strict: ## Same, but fail on any warning (for CI)
	@$(SPEC)/build.sh --strict

lint-openapi: $(FRONT_TOOLS) ## Check the interface contract
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

mock-data: ## Regenerate the volumes of §4.6.2 and the readings and writes of the witness the fake back serves (fixtures/api, fixtures/witness)
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
test-tools: install-front ## Run the tests of the repository tools (TESTS=<file> runs one file); one of them bundles the contract with the Redocly of the front
	@cd $(TOOLS) && $(capped) $(heavy) uv run --frozen pytest -n $(WATERFALL_PROCESSORS) --dist worksteal $(TESTS)

# The entrypoint of the directory, tried in Docker on throwaway volumes: a minute of starts that the
# tools leave out (the marker openldap), run by the keycloak family, which deploy/openldap wakes.
test-openldap: ## Try the entrypoint of the directory of test on throwaway volumes (needs Docker)
	@cd $(TOOLS) && uv run --frozen pytest -m openldap -n $(WATERFALL_PROCESSORS) --dist worksteal

# The tests of the chart (deploy/helm/waterfall, US-2800), which render it by Helm: the tools leave
# them out (the marker chart), the chart family runs them.
test-chart: kube-tools ## Render the chart and hold what its objects say (US-2800)
	@cd $(TOOLS) && uv run --frozen pytest -m chart -n $(WATERFALL_PROCESSORS) --dist worksteal

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

implementations: ## Each calculation of WF-ARC-0010 has one implementation, in its module of the core (US-2780/L3)
	@$(WFTOOLS).implementations

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

# Helm, kind and kubectl, which PyPI does not hold as it holds the linters above: downloaded at the
# versions and digests wftools.kubetools pins, kept under the cache of the user, shared by worktrees.
kube-tools: ## Install Helm, kind, kubectl, promtool, amtool and alertmanager at their pinned versions, under ~/.cache/waterfall/bin
	@$(WFTOOLS).kubetools

lint-chart: kube-tools ## Lint the chart strictly, with the values of the chain (US-2800)
	@$(WFTOOLS).chart

# The chart installed on a cluster of kind made for it, from the images of WATERFALL_IMAGE_TAG (the
# commit by default) built here, bootstrapped, its liveness and the sign-in of its first
# administrator held, the test of a restoration played as the platform plans it, then deleted
# (wftools.charttrial). A heavy run: a cluster, Keycloak three times — the test starts its own — and
# PostgreSQL. The cluster is named after the slot, so that two worktrees never share one.
chart-trial: export WATERFALL_CHART_CLUSTER ?= waterfall-chart-s$(call slot-value,WATERFALL_SLOT)
chart-trial: kube-tools ## Install the chart on a throwaway cluster of kind from the images of WATERFALL_IMAGE_TAG (the commit by default, make images first), bootstrap it, hold its liveness, the sign-in of its first administrator and its services without state (one token answered the same by each instance, a worker killed in a marking) and the test of a restoration the platform plans (closed while it runs, gone after), then delete the cluster
	@$(heavy) $(WFTOOLS).charttrial

# Keycloak answers before its realm is applied: the application starts once it does, anew at each
# start, and stays, to apply it again after a restoration (#955). The root of the authority of its
# front end is copied out first: a new volume makes a new one. The service of the restoration waits
# for the application, which it would start with the platform: it starts last, so that the realm is
# applied once, and Keycloak, which the application waits for, is never started again (--no-deps).
# A start that fails prints the log of the control of the volume of PostgreSQL, which says nothing
# unless it refuses the data of another major version (US-1130): `up --detach` shows no log.
service-up: ## Start the service platform: PostgreSQL, Redis, the migrations, the API, the worker and its schedule, the service of the restoration, Keycloak in HTTPS and its realm, OpenLDAP, Mailpit (needs the secrets of the guide, "Commandes")
	@$(RETRIED) $(COMPOSE_SERVICE) up --build --detach --wait postgres redis api worker scheduler keycloak keycloak-front-end openldap mailpit \
		|| { rc=$$?; $(COMPOSE_SERVICE) logs --no-color --no-log-prefix postgres-volume >&2; exit $$rc; }
	@$(MAKE) --no-print-directory keycloak-authority
	@$(COMPOSE_SERVICE) up --detach --wait --force-recreate --no-deps keycloak-realm
	@$(RETRIED) $(COMPOSE_SERVICE) up --build --detach --wait restore

# The bootstrap of the platform (US-0420), once its realm is applied: the link of the first
# administrator on the standard output, alone — its image built quietly first, and no terminal,
# which would mix the logs in —, and nothing on an installation whose administrator has set a
# password.
service-install: ## Bootstrap the installation of the service platform, started, and print the link of its first administrator (WATERFALL_ADMIN_EMAIL, WATERFALL_DEFAULT_LANGUAGE, WATERFALL_CURRENCY, WATERFALL_COMPANY_NAME, WATERFALL_TIME_ZONE)
	@$(RETRIED) $(COMPOSE_SERVICE) build --quiet install
	@$(COMPOSE_SERVICE) run --rm --no-TTY install

# The witness (EP-05), once the platform is bootstrapped: the examples of the contract written on it
# by `waterfall-api load-witness`, as the role of the service; run again, it writes nothing.
service-witness: ## Load the witness, the examples of the contract (fixtures/api and fixtures/witness), on the service platform, started and bootstrapped
	@$(RETRIED) $(COMPOSE_SERVICE) build --quiet witness
	@$(COMPOSE_SERVICE) run --rm --no-TTY witness

# The purge of what expired (EP-06, "La purge"), by hand: the schedule the scheduler calls every five
# minutes, run in its container with a purge interval of one second, so that the purge is due now;
# the worker runs the task. No purge is deposited while one is queued or running. The interval of one
# second is that of the purge alone: a reading of the accounts whose last is older than a day is
# deposited as well, the schedule depositing whatever is due.
service-purge: ## Deposit the purge of what expired on the service platform, started: the worker runs it (`waterfall-worker schedule`)
	@$(COMPOSE_SERVICE) exec --no-TTY --env WATERFALL_PURGE_INTERVAL=1 scheduler waterfall-worker schedule

# The measure of the core in process (US-2210, EP-26, "La mesure"): backend/measure/, which calls the
# core as the API does, on the database of the service platform of the slot, without HTTP or Keycloak;
# every write it makes is rolled back. It takes the workstation for itself alone (the exclusive turn,
# US-2210/L2) and starts from a witness freshly loaded: the platform is stopped and its data dropped,
# started again, bootstrapped and the witness loaded (measure-fresh-witness), so that a measure
# changes nothing of the next. It never fails on a duration and the chain does not run it. RUNS
# identical runs of the whole read, the cell entered and the revision opened (5; the profile and the
# waves of reads make one pass), ONLY=<part> one of read, profile, parallel, write, revision, kept,
# current, indicators, merge, occurrence (several by repeating: ONLY="read write"), JSON=<file> the
# report also written as JSON. A lot that corrects the back measures before and after it in one pass: ONLY and RUNS the
# same, two commands in one.
.PHONY: measure-core measure-core-run measure-fresh-witness measure-secrets
# The secrets of service-up, asked before the workstation is taken: the Compose file refuses to
# render without them and names the one missing (the same check as lint-compose).
$(call slot-export,measure-secrets,$(SLOT_SERVICE))
measure-secrets:
	@$(COMPOSE_SERVICE) --profile install --profile witness config --quiet

measure-core: measure-secrets ## Measure the core in process, the workstation for itself alone, on a witness freshly loaded of the service platform (needs the secrets of service-up): whole reads of PRJ-001, profile, threads and processes, a cell entered, a revision opened, a marked revision read as kept, the marking, the comparison of two marked ones and the filtered readings against the document (US-2270), the comparison of the current revision in its parts and its nodes differing (US-2390), the entry of the cache of the indicators of the day (US-2420), the merge of a differential and the occurrence of a risk, read without an objective (US-2650/L2); RUNS, ONLY="read profile parallel write revision kept current indicators merge occurrence", JSON=<file>
	@$(exclusive) $(MAKE) --no-print-directory measure-core-run

$(call slot-export,measure-core-run,$(SLOT_SERVICE))
measure-core-run: measure-fresh-witness
	@cd $(BACK) && PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -m measure $(if $(RUNS),--runs $(RUNS)) \
		$(foreach part,$(ONLY),--only $(part)) $(if $(JSON),--json $(abspath $(JSON)))

# The measure of the workbooks (US-3190/L2b, EP-33, "Les bornes des classeurs"): backend/measure/workbooks.py,
# on workbooks it engenders alone (tests/workbook_bombs.py, the writers of the exports, the support of the
# tests, the prototypes of the specification), each point of a sweep read in a fresh process. No database.
# Without VECTOR, the vectors of the workbooks engendered, the time the judgment of the archive adds,
# the members of each parsed into a tree and where the nodes of its tabs lie, and the peak of reading each
# (US-3190/L3); VECTOR=<vector> COUNTS="<count>..." the peak of the reading along one vector. It takes
# the workstation for itself alone, as measure-core does, and never fails on a figure.
.PHONY: measure-workbooks
measure-workbooks: ## Measure what a workbook engendered costs its reader (US-3190/L2b, L3), the workstation for itself alone: the vectors of the workbooks engendered, the time of the judgment of the archive, the members parsed into a tree, the peak of each; VECTOR=<vector> COUNTS="<count>..." the peak resident size along one vector, READER=openpyxl by openpyxl alone, behind the bounds
	@cd $(BACK) && $(exclusive) PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -m measure.workbooks \
		$(if $(VECTOR),sweep $(VECTOR) $(COUNTS) $(if $(READER),--reader $(READER)),books)
	@$(if $(VECTOR),,cd $(BACK) && $(exclusive) PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -m measure.workbooks preread)
	@$(if $(VECTOR),,cd $(BACK) && $(exclusive) PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -m measure.workbooks members)
	@$(if $(VECTOR),,cd $(BACK) && $(exclusive) PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -m measure.workbooks peaks)

# The witness freshly loaded, for a measure: the platform of the slot stopped and its data dropped,
# started again, bootstrapped (its link discarded) and the witness loaded.
$(call slot-export,measure-fresh-witness,$(SLOT_SERVICE))
measure-fresh-witness:
	@echo 'The data of the service platform of this slot are dropped (service-down WATERFALL_RESET_DATA=yes).'
	@$(MAKE) --no-print-directory service-down WATERFALL_RESET_DATA=yes
	@$(MAKE) --no-print-directory service-up
	@$(RETRIED) $(COMPOSE_SERVICE) build --quiet install witness
	@$(COMPOSE_SERVICE) run --rm --no-TTY install > /dev/null
	@$(COMPOSE_SERVICE) run --rm --no-TTY witness

keycloak-authority: ## Copy out of the service platform the root of the authority of Keycloak's front end (KEYCLOAK_AUTHORITY)
	@mkdir -p $(dir $(KEYCLOAK_AUTHORITY))
	@$(COMPOSE_SERVICE) cp keycloak-front-end:/data/caddy/pki/authorities/local/root.crt $(KEYCLOAK_AUTHORITY)
	@echo "  -> $(KEYCLOAK_AUTHORITY)"

service-logs: ## Print the logs of the services of the platform (SERVICES, all of them by default)
	@$(COMPOSE_SERVICE_ALL) logs --no-color $(SERVICES)

# The logs the search reads (WF-OBS-0020, US-2900), put in a file — a pipe would pass whatever the
# reading did, the shell having no pipefail: those of every service of Compose, under all its
# profiles, the log of the front end of the paths (FRONT_LOG, which Compose does not hold: the
# server of Next is a web server of Playwright), and those of the bootstrap and of the witness, which
# e2e-service runs by `run --rm` and whose containers go with their logs (RUN_LOGS, #4395): of the
# bootstrap, its log alone, its standard output being the link of the first administrator, a token
# of one use it prints on purpose. A reading that fails fails the search; so does an empty text
# (logsearch).
SERVICE_LOGS = $(FRONT)/.e2e/service-logs.txt
SERVICE_LOGS_OF_WATERFALL = $(FRONT)/.e2e/service-logs-waterfall.txt
INSTALL_LOG = $(FRONT)/.e2e/install.log
WITNESS_LOG = $(FRONT)/.e2e/witness.log
RUN_LOGS = $(INSTALL_LOG) $(WITNESS_LOG)
service-logs-text = mkdir -p $(FRONT)/.e2e && { $(COMPOSE_SERVICE_ALL) logs --no-color $(SERVICES) && { test ! -f $(FRONT_LOG) || cat $(FRONT_LOG); } && for each in $(RUN_LOGS); do test ! -f $$each || cat $$each; done; } > $(SERVICE_LOGS)
# A service run once, what it writes kept in a file, then shown: (call run-logged,<service>,<file>,
# <redirection to the file>) — `2>` for its log alone, `>` then `2>&1` for both its outputs.
run-logged = { $(COMPOSE_SERVICE) run --rm --no-TTY $(1) $(3); ran=$$?; cat $(2) >&2; [ $$ran -eq 0 ]; }
service-logs-secrets = $(service-logs-text) && $(WFTOOLS).logsearch secrets $(SERVICE_LOGS)
# The secrets of the platform of service, by their values, in every file git tracks (WF-SEC-0010,
# US-2840): e2e-service, which the chain plays with them, searches them there too. Those values
# alone: neither the shapes of the tokens, nor the password of the paths, a constant of the
# repository (FIXED_SECRETS), nor the values a workflow sets in clear, those of a workstation, public
# (wftools.logsearch, chain_values): under the chain, it searches nothing and says so.
repository-secrets = $(WFTOOLS).logsearch repository
service-logs-check = mkdir -p $(FRONT)/.e2e && $(COMPOSE_SERVICE_ALL) logs --no-color api worker scheduler restore > $(SERVICE_LOGS_OF_WATERFALL) && $(WFTOOLS).logsearch fields $(SERVICE_LOGS_OF_WATERFALL)
service-logs-search: ## Search the logs of the platform and the log of the front of the last e2e-service for the secrets and tokens known; CORRELATION=<identifier>: the story of an identifier instead (its lines, and those of the deposit, the import and the task they name). The front log is the last run's, kept until e2e-service empties it
	@$(if $(CORRELATION),$(service-logs-text) && $(WFTOOLS).logsearch follow $(CORRELATION) $(SERVICE_LOGS),$(service-logs-secrets))

service-logs-fields: ## Check that every record of the logs of the API, the worker, its schedule and the service of the restoration carries its correlation identifier, its author and its severity (WF-OBS-0020, US-2900)
	@$(service-logs-check)

service-down: ## Stop the service platform, the proxy of e2e-service and the load of make measure-version included; WATERFALL_RESET_DATA=yes also drops its databases, its directory and its authority
	@$(COMPOSE_SERVICE_ALL) down $(if $(filter yes,$(WATERFALL_RESET_DATA)),--volumes)

migrate: ## Apply the migrations to the database WATERFALL_DATABASE_URL designates (the guide, "Migrations")
	@cd $(BACK) && uv run --frozen waterfall-migrate

# The Compose files refuse to start without their secrets: validated with stand-ins that never run.
# The images of production by their digests (#3726): stand-ins of no image.
STAND_IN_DIGESTS := WATERFALL_DIGEST_FRONT=sha256:0000000000000000000000000000000000000000000000000000000000000000 \
	WATERFALL_DIGEST_WATERFALL=sha256:0000000000000000000000000000000000000000000000000000000000000000 \
	WATERFALL_DIGEST_KEYCLOAK=sha256:0000000000000000000000000000000000000000000000000000000000000000
lint-compose: ## Validate the Compose files
	@PRISM_VERSION=$(PRISM_VERSION) $(COMPOSE_DEV) config --quiet
	@WATERFALL_POSTGRES_PASSWORD=stand-in WATERFALL_SERVICE_DATABASE_PASSWORD=stand-in \
		WATERFALL_BACKUP_DATABASE_PASSWORD=stand-in \
		WATERFALL_REDIS_PASSWORD=stand-in WATERFALL_KEYCLOAK_DATABASE_PASSWORD=stand-in WATERFALL_KEYCLOAK_ADMIN_PASSWORD=stand-in \
		WATERFALL_FRONT_CLIENT_SECRET=stand-in WATERFALL_SERVICE_CLIENT_SECRET=stand-in \
		WATERFALL_INSTALLATION_CLIENT_SECRET=stand-in \
		WATERFALL_STORAGE_SECRET=stand-in WATERFALL_STORAGE_RPC_SECRET=stand-in \
		$(COMPOSE_SERVICE_FILE) --profile e2e --profile install --profile witness config --quiet
	@WATERFALL_DOMAIN=waterfall.localhost WATERFALL_ACME_EMAIL=stand-in $(STAND_IN_DIGESTS) \
		WATERFALL_ADMIN_EMAIL=stand-in WATERFALL_SERVER_ACTIONS_KEY=stand-in \
		WATERFALL_CURRENCY=EUR WATERFALL_COMPANY_NAME=stand-in \
		WATERFALL_DATABASE_CAPACITY_BYTES=1 WATERFALL_STORAGE_CAPACITY_BYTES=1 \
		WATERFALL_POSTGRES_ADMIN_PASSWORD=stand-in WATERFALL_POSTGRES_PASSWORD=stand-in WATERFALL_SERVICE_DATABASE_PASSWORD=stand-in \
		WATERFALL_BACKUP_DATABASE_PASSWORD=stand-in \
		WATERFALL_REDIS_PASSWORD=stand-in WATERFALL_KEYCLOAK_DATABASE_PASSWORD=stand-in WATERFALL_KEYCLOAK_ADMIN_PASSWORD=stand-in \
		WATERFALL_FRONT_CLIENT_SECRET=stand-in WATERFALL_SERVICE_CLIENT_SECRET=stand-in \
		WATERFALL_INSTALLATION_CLIENT_SECRET=stand-in \
		WATERFALL_STORAGE_SECRET=stand-in WATERFALL_STORAGE_RPC_SECRET=stand-in \
		WATERFALL_GRAFANA_ADMIN_PASSWORD=stand-in \
		$(COMPOSE_PRODUCTION) --profile install config --quiet
	@WATERFALL_DOMAIN=waterfall.localhost $(STAND_IN_DIGESTS) WATERFALL_SERVICE_DATABASE_PASSWORD=stand-in \
		WATERFALL_STORAGE_SECRET=stand-in WATERFALL_RESTORE_TEST_PASSWORD=stand-in \
		docker compose -f deploy/compose/compose.restore-test.yaml --profile restore-test config --quiet
	@WATERFALL_DOMAIN=demo.localhost WATERFALL_ACME_EMAIL=stand-in WATERFALL_IMAGE_TAG=stand-in \
		WATERFALL_DEMO_USER=stand-in WATERFALL_DEMO_PASSWORD_HASH=stand-in \
		WATERFALL_SERVER_ACTIONS_KEY=stand-in PRISM_VERSION=$(PRISM_VERSION) \
		docker compose -f deploy/compose/compose.demo.yaml config --quiet
	@docker compose -f deploy/compose/compose.test.yaml config --quiet

build-keycloak: ## Build the image of Keycloak: the extension compiled and tested, the themes, the realm (deploy/keycloak)
	@$(RETRIED) docker build --build-arg WATERFALL_MIRROR $(call build-cache-from,keycloak) --tag $(WATERFALL_KEYCLOAK_IMAGE) deploy/keycloak

# The image of Keycloak built once in the run of the chain, by one job (keycloak-image, in ci.yml, #4790): the
# Maven downloads of its build are made there and nowhere else. save-keycloak writes it to
# KEYCLOAK_ARCHIVE, which the job uploads; load-keycloak reads it in each part of the paths
# (service.yml), which then start the
# platform with WATERFALL_KEYCLOAK_LOADED=1, so that Compose does not build it again.
KEYCLOAK_ARCHIVE ?= $(or $(RUNNER_TEMP),/tmp)/keycloak-image.tar

save-keycloak: ## Write the image of Keycloak, built by build-keycloak, to KEYCLOAK_ARCHIVE
	@docker save --output $(KEYCLOAK_ARCHIVE) $(WATERFALL_KEYCLOAK_IMAGE)

load-keycloak: ## Load the image of Keycloak from KEYCLOAK_ARCHIVE, without building it
	@docker load --quiet --input $(KEYCLOAK_ARCHIVE)

# The cache of the builds of the images on GitHub Actions (type=gha, .github/actions/build-cache):
# every build of an image reads it, under the name of the image (wftools.images); after a merge,
# images.yml writes it, each image built into it alone, neither loaded nor published. Docker leaves
# a cache of type gha out where the runtime of GitHub Actions is not given to it: on a workstation,
# both are without effect.
build-cache-from = --cache-from type=gha,scope=$(1)
build-cache-to = --output type=cacheonly --cache-to type=gha,mode=max,scope=$(1) $(call build-cache-from,$(1))

build-cache: ## Write the builds of the images front, waterfall and keycloak into the cache of GitHub Actions (images.yml)
	@$(RETRIED) docker build --build-arg WATERFALL_MIRROR --target production $(call build-cache-to,front) frontend
	@$(RETRIED) docker build --build-arg WATERFALL_MIRROR --target production $(call build-cache-to,waterfall) backend
	@$(RETRIED) docker build --build-arg WATERFALL_MIRROR --target production $(call build-cache-to,keycloak) deploy/keycloak

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
# commit of the checkout by default —, built here, pushed to a registry that lives for the run and
# run by the digests its pushes say (wftools.trialregistry, #3726), or published and run by the
# WATERFALL_DIGEST_* the environment gives, under a local name
# (WATERFALL_DOMAIN, waterfall.localhost by default) on ports 80 and 443 (WATERFALL_HTTP_PORT,
# WATERFALL_HTTPS_PORT): started, bootstrapped, its API's liveness and the sign-in of its first
# administrator held, then removed with its volumes (wftools.production). Its secrets come from the
# environment, as production.env.example names them; the project of Compose is
# WATERFALL_PRODUCTION_PROJECT (waterfall-production-trial). Outside the slots, at slot 0 alone: from
# the worktree of a lot, it would take the ports 80 and 443 of the workstation (US-1100).
production-trial: ## Start the production platform on the images of WATERFALL_IMAGE_TAG (the commit by default) under a local name, bootstrap it, hold its liveness and the sign-in of its first administrator, back it up and restore it by the API, then play the test of a restoration (deploy/compose/restore-test.sh) on a scheduled backup, with WATERFALL_TRIAL_RESTORATION=1, then remove it (needs its secrets); at slot 0 alone, the main repository
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
	@$(RETRIED) $(COMPOSE_SERVICE) up --build --detach --wait keycloak keycloak-front-end openldap
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

check-all: check-repo check-repo-tools check-spec check-contract check-back check-front check-front-image check-roadmap check-measures check-keycloak check-service check-production check-chart ## Run every family of checks

check-repo: reuse lint-workflows lint-shell lint-docker lint-compose sources check-fixtures \
	requirements screens implementations readmes ## Checks that run on any change

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
# collection (six in the chain, SHARD=1/6 to 6/6): the files that load the witness, the longest,
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
	@test ! -d $(FRONT)/node_modules || touch $(FRONT_WITNESS)

$(FRONT_WITNESS): $(FRONT)/pnpm-lock.yaml $(FRONT)/package.json
	@$(PNPM) install --frozen-lockfile --silent
	@touch $@

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
catalogs: $(FRONT_TOOLS) ## The catalogues of the front are twins, with a key for each value the contract codes (WF-QUA-0070)
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

check-measures: ## The measure reports of the versions held to the objectives and to the previous version (US-2300)
	@$(WFTOOLS).measures

check-keycloak: build-keycloak test-keycloak test-openldap ## The image of Keycloak builds, its realm applies and its extension answers (US-0350); the entrypoint of the directory seeds its volumes

# The production image of the front, which the chain publishes after a merge alone (images.yml),
# built and started at a pull request that changes what makes it (wftools.frontimage, US-0430).
check-front-image: ## The production image of the front builds, starts and answers /, refuses the fake back, and prerenders no page that reads the environment (US-0430)
	@$(WFTOOLS).frontimage

check-service: $(call full-only,e2e-service) ## The paths against the real service, in the full tier only (US-0340)

# The three images built as the chain publishes them, never pushed, then the production platform on
# them (production-trial): in the full tier only, as images.yml does again on the images it published.
check-production: $(call full-only,images production-trial) ## The production platform starts on the images built here, bootstraps and lets its first administrator in, in the full tier only (US-0430)

# The chart linted and rendered in every tier; installed on a cluster of kind from the three images
# built here, in the full tier only, as check-production starts the Compose (US-2800).
check-chart: lint-chart test-chart $(call full-only,images chart-trial) ## The chart lints and says what it must; in the full tier, it installs on a throwaway cluster, bootstraps and lets its first administrator in (US-2800)

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

# Dependabot follows the images of Docker Hub in their manifest, deploy/images/Dockerfile, which it
# reads where it does not read the references behind the prefix of the mirror (US-2490).
mirror-sync: ## Copy the manifest of the images of Docker Hub (deploy/images/Dockerfile) into the Dockerfiles, the Compose files and the workflows, their prefix kept (wftools.mirror, US-2490)
	@$(WFTOOLS).mirror sync

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
# Before it starts, the port must be free: a server already there would be waited for, and played
# against, as ours. The server answers on a path drawn at each run, which only the paths know
# (PW_TEST_CONNECT_WS_ENDPOINT): any process of the host reaching the port could otherwise start a
# browser, in a container that mounts the socket of Docker. The shell stops the server on exit, and
# on SIGINT and SIGTERM, which dash would not run the trap of EXIT for. The wait is a loop of the
# shell itself, bounded at 120 tries of 2 seconds at most (a server that accepts and never answers
# would hold a bare `curl`), so that an interruption is heard at once (a `timeout` would put it in
# a group of its own, and the trap would wait for its end); it gives up when the server dies. Any
# answer ends it, an error too: `run-server` serves only the path drawn, so that something listens
# on the port is all a request to `/` can tell, and a probe of the path itself would be
# Playwright's to answer.
e2e-port-free = python3 -c 'import socket, sys; sys.exit(socket.socket().connect_ex(("127.0.0.1", $(E2E_BROWSER_PORT))) == 0)'
e2e-browser = $(if $(E2E_IMAGE),$(e2e-port-free) || { echo 'port $(E2E_BROWSER_PORT) is taken (stop the server there or set E2E_BROWSER_PORT)' >&2; exit 1; }; secret=$$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n'); $(e2e-in-image) node node_modules/@playwright/test/cli.js run-server --host 127.0.0.1 --port $(E2E_BROWSER_PORT) --path /$$secret & browser=$$!; trap 'kill $$browser' EXIT; trap 'exit 130' INT TERM; waited=0; until curl --silent --max-time 2 --output /dev/null http://127.0.0.1:$(E2E_BROWSER_PORT)/; do kill -0 $$browser || exit 1; waited=$$((waited + 1)); [ $$waited -lt 120 ] || exit 1; sleep 1; done && export PW_TEST_CONNECT_WS_ENDPOINT=ws://127.0.0.1:$(E2E_BROWSER_PORT)/$$secret &&)

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
e2e: install-front $(call e2e-build,$(E2E_DEV_SERVER)) ## End-to-end paths, against the fake back that Playwright starts (US-0080), on the front built for production; SHARD=i/N plays the i-th of N parts of them, without the measure; WORKERS=n (1 to 40, by default half the processors, at most 40) plays them on n workers; TESTS=<file> plays one file (not with SHARD); E2E_DEV_SERVER=1 plays them against next dev, on a workstation
	@$(if $(SHARD),dir=$$(mktemp -d) && trap 'rm -rf "$$dir"' EXIT && ( $(PNPM) exec playwright test --list > "$$dir/listing" ) && $(WFTOOLS).e2eparts plan $(SHARD) < "$$dir/listing" > "$$dir/part" && )$(PNPM_HEAVY) exec playwright test $(if $(SHARD),--test-list="$$dir/part") $(TESTS)

# Rewrite tools/e2e-durations.json, the seconds each unit of the paths took, from the log of a run
# (LOG=<file>, the list reporter's output of a make e2e, or of the job of a part in the chain; the
# standard input without it), for the parts of make e2e SHARD=i/N (wftools.e2eparts, US-1910); and
# tools/e2e-service-durations.json, those of the projects `service` and `shared`, from the log of
# a make e2e-service, for its parts.
e2e-durations: ## Refresh the durations the parts of the end-to-end paths are spread by, from the log of a run of make e2e or make e2e-service (LOG=<file>, standard input without it)
	@$(WFTOOLS).e2eparts refresh $(if $(filter command line,$(origin LOG)),$(LOG))

e2e-measure: export E2E_PART = measure
e2e-measure: export E2E_BUILT = 1
e2e-measure: install-front $(call e2e-build) ## The measure of the second of §4.6.2 alone, against the front built for production (US-0110)
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
# refused as the Makefile is read, below, whichever goal reads the share.
E2E_WORKERS_GIVEN := $(E2E_WORKERS)
# With SHARD=i/N, the i-th of N parts of the paths, each on a platform of its own, as the chain plays
# them on N runners (service.yml, US-1910): the parts 1 to N-1 share the projects `service` and
# `shared`, spread by the seconds their units took (tools/e2e-service-durations.json,
# wftools.e2eparts), each playing the test list of its share, written under frontend/.e2e/, which
# git ignores; the last part plays `shared-serial`, `realm` and `restoration`, which play one at a
# time after the others, alone on its platform (E2E_SERVICE_SERIAL, frontend/playwright.config.ts).
# The part is checked before the platform starts; the paths are listed once it has, the
# configuration of Playwright reading the log of its proxy.
e2e-service-part = $(if $(SHARD),if [ "$$($(WFTOOLS).e2eparts service-part $(SHARD))" = serial ]; then export E2E_SERVICE_SERIAL=1; else mkdir -p $(FRONT)/.e2e && ( cd $(FRONT) && $(PNPM_ENV) pnpm exec playwright test --list ) > $(FRONT)/.e2e/service-listing && $(WFTOOLS).e2eparts plan --service $(SHARD) < $(FRONT)/.e2e/service-listing > $(FRONT)/.e2e/service-part && part=--test-list=.e2e/service-part; fi &&)
E2E_SERVICE_PROCESSORS = $(if $(WATERFALL_PROCESSORS_READING),1,$(if $(shell printf '%s' '$(WATERFALL_PROCESSORS)' | grep -Eq '^[1-9][0-9]*$$' && echo ok),$(WATERFALL_PROCESSORS),$(error WATERFALL_PROCESSORS must be a positive integer, got '$(WATERFALL_PROCESSORS)')))
E2E_SERVICE_WORKERS = $(shell workers=$$(($(E2E_SERVICE_PROCESSORS) * 3 / 4)); echo $$((workers < 1 ? 1 : (workers > 40 ? 40 : workers))))
# Refused where the Makefile is read, before any prerequisite builds anything (#3011): expanding the
# share stops on one that is no integer. The goals covered are those that surely play e2e-service,
# as a prerequisite of this very make: e2e-service itself, and check-service and check-all, which
# do so in the full tier only (TIER=full, full-only above). check, which plays each family in a
# make of its own and only if the change touches it, is not covered: it would pay a $(shell) in
# the fast tier, which does not play the paths. The target-specific override below keeps an empty
# E2E_WORKERS= of the command line, which would win with its empty value, from reaching Playwright.
$(if $(or $(filter e2e-service,$(MAKECMDGOALS)),$(and $(filter full,$(TIER)),$(filter check-service check-all,$(MAKECMDGOALS)))),$(if $(E2E_SERVICE_PROCESSORS),))
# The workers the paths against the service take here, written in the log of the chain beside the
# processors of its runner (service.yml, US-2290): four processors give three workers, beside the
# four processes of the API.
.PHONY: e2e-service-workers service-api-processes
service-api-processes: ## Print the number of processes of the API the service platform is given (WATERFALL_API_PROCESSES, four by default in compose.service.yaml; needs the secrets of service-up)
	@$(COMPOSE_SERVICE) config --format json | jq -r '.services.api.environment.WATERFALL_API_PROCESSES'
e2e-service-workers: ## Print the number of workers make e2e-service gives Playwright here (E2E_SERVICE_WORKERS, or E2E_WORKERS given)
	@echo $(or $(E2E_WORKERS_GIVEN),$(E2E_SERVICE_WORKERS))
e2e-service: override export E2E_WORKERS = $(or $(E2E_WORKERS_GIVEN),$(E2E_SERVICE_WORKERS))
e2e-service: export WATERFALL_FRONT_ADDRESS = http://127.0.0.1:$(E2E_FRONT_PORT)
e2e-service: export WATERFALL_FRONT_BACKCHANNEL = http://host.docker.internal:$(E2E_FRONT_PORT)
e2e-service: export E2E_PART = service
e2e-service: export E2E_SERVICE_SERIAL =
e2e-service: export WATERFALL_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
e2e-service: export E2E_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
e2e-service: export E2E_BUILT = 1
e2e-service: install-front $(call e2e-build,$(E2E_DEV_SERVER)) ## End-to-end paths of the project `service` against the real service, through Prism as a proxy, on the front built for production (needs the secrets of service-up and a browser, make e2e-browsers); TESTS=<arguments of playwright test>: a file alone also plays installation and, with a @realm-wide or @platform-wide path, the projects its own depends on; TESTS="--no-deps --project=shared --project=realm <files>" plays only the files, on an installation already played; SHARD=i/N (N >= 2, not with TESTS) plays the i-th of N parts on a platform of its own, the last one the paths that play one at a time
	@$(if $(SHARD),$(WFTOOLS).e2eparts service-part $(SHARD) > /dev/null)
	@$(MAKE) --no-print-directory mock-spec MOCK_SPEC=$(PROXY_SPEC)
	@$(MAKE) --no-print-directory service-up
	@$(COMPOSE_SERVICE) up --detach --wait contract-proxy
	@$(RETRIED) $(COMPOSE_SERVICE) build --quiet install witness
	@mkdir -p $(FRONT)/.e2e && \
		E2E_INSTALLATION_LINK=$$($(call run-logged,install,$(INSTALL_LOG),2> $(INSTALL_LOG))) && \
		$(call run-logged,witness,$(WITNESS_LOG),> $(WITNESS_LOG) 2>&1) && \
		E2E_CONTRACT_PROXY=$$($(COMPOSE_SERVICE) ps --quiet contract-proxy) && \
		E2E_SERVICE_DATABASE=$$($(COMPOSE_SERVICE) ps --quiet postgres) && \
		E2E_SERVICE_CACHE=$$($(COMPOSE_SERVICE) ps -a --quiet redis) && \
		E2E_SERVICE_DIRECTORY=$$($(COMPOSE_SERVICE) ps -a --quiet openldap) && \
		E2E_SERVICE_WORKER=$$($(COMPOSE_SERVICE) ps -a --quiet worker) && \
		WATERFALL_API_ADDRESS=http://127.0.0.1:$(WATERFALL_PROXY_PORT) && \
		WATERFALL_KEYCLOAK_ADDRESS=$(KEYCLOAK_ADDRESS) && \
		WATERFALL_REDIS_URL=redis://:$${WATERFALL_REDIS_PASSWORD}@127.0.0.1:$${WATERFALL_REDIS_PORT:-6379}/0 && \
		NODE_EXTRA_CA_CERTS=$(KEYCLOAK_AUTHORITY) && \
		export E2E_INSTALLATION_LINK E2E_CONTRACT_PROXY E2E_SERVICE_DATABASE E2E_SERVICE_CACHE E2E_SERVICE_DIRECTORY E2E_SERVICE_WORKER WATERFALL_API_ADDRESS WATERFALL_KEYCLOAK_ADDRESS WATERFALL_REDIS_URL NODE_EXTRA_CA_CERTS && \
		part= && $(e2e-service-part) \
		mkdir -p $(FRONT)/.e2e && : > $(FRONT_LOG) && \
		{ ( cd $(FRONT) && { $(e2e-browser) $(PNPM_ENV) pnpm exec playwright test $$part $(TESTS); } ); played=$$?; \
		echo 'Searching the logs of the platform and of the front for the secrets and tokens known (WF-OBS-0020, US-2900).'; \
		$(service-logs-secrets); found=$$?; \
		echo 'Checking the records of the services of Waterfall for their fields (WF-OBS-0020, US-2900).'; \
		$(service-logs-check); fields=$$?; \
		echo 'Searching the files of the repository for the secrets of the platform of service (WF-SEC-0010, US-2840).'; \
		$(repository-secrets); written=$$?; \
		if [ $$played -ne 0 ]; then exit $$played; fi; if [ $$found -ne 0 ]; then exit $$found; fi; \
		if [ $$written -ne 0 ]; then exit $$written; fi; exit $$fields; }

# The measure of the journey of the grids against the service (US-2210, frontend/e2e/measure/): the
# platform started as e2e-service starts it — its realm told the address of the front of the
# harness —, bootstrapped and its witness loaded, but no proxy of the contract: the front, built for
# production, reaches the API directly (WATERFALL_API_ADDRESS), and the measure reads the log of the
# API (E2E_SERVICE_API) for its part of each step. One, four and eight users (MEASURE_USERS), five
# passes (MEASURE_PASSES); the report, a JSON, where MEASURE_REPORT says. It takes the workstation for
# itself alone (the exclusive turn, US-2210/L2), once the front is built, and starts from a witness
# freshly loaded: the platform stopped and its data dropped, then started again. It fails on no
# duration, and no goal of the chain plays it (E2E_PART).
MEASURE_USERS ?= 1 4 8
MEASURE_PASSES ?= 5
MEASURE_REPORT ?= $(FRONT)/.e2e/measure.json
.PHONY: measure measure-run
$(call slot-export,measure measure-run,$(SLOT_SERVICE) $(SLOT_PATHS))
measure: export WATERFALL_FRONT_ADDRESS = http://127.0.0.1:$(E2E_FRONT_PORT)
measure: export WATERFALL_FRONT_BACKCHANNEL = http://host.docker.internal:$(E2E_FRONT_PORT)
measure: export E2E_PART = measure-service
measure: export E2E_BUILT = 1
measure: export WATERFALL_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
measure: export E2E_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
measure: export E2E_MEASURE_USERS = $(MEASURE_USERS)
measure: export E2E_MEASURE_PASSES = $(MEASURE_PASSES)
measure: export E2E_MEASURE_REPORT = $(abspath $(MEASURE_REPORT))
measure: measure-secrets install-front $(call e2e-build) ## Measure the journey of the grids against the service, the front built for production and no proxy of the contract, at one, four and eight users, five passes, in three parts: the API, Next, the browser (US-2210); MEASURE_USERS="1 4 8", MEASURE_PASSES=5, MEASURE_REPORT=<file of the JSON> (frontend/.e2e/measure.json); the workstation for itself alone, on a witness freshly loaded; needs the secrets of service-up and a browser
	@$(exclusive) $(MAKE) --no-print-directory measure-run

measure-run:
	@echo 'The data of the service platform of this slot are dropped (service-down WATERFALL_RESET_DATA=yes).'
	@$(MAKE) --no-print-directory service-down WATERFALL_RESET_DATA=yes
	@$(MAKE) --no-print-directory service-up
	@$(RETRIED) $(COMPOSE_SERVICE) build --quiet install witness
	@E2E_INSTALLATION_LINK=$$($(COMPOSE_SERVICE) run --rm --no-TTY install) && \
		$(COMPOSE_SERVICE) run --rm --no-TTY witness && \
		E2E_SERVICE_API=$$($(COMPOSE_SERVICE) ps --quiet api) && \
		WATERFALL_API_ADDRESS=http://127.0.0.1:$${WATERFALL_API_PORT:-8000} && \
		WATERFALL_KEYCLOAK_ADDRESS=$(KEYCLOAK_ADDRESS) && \
		WATERFALL_REDIS_URL=redis://:$${WATERFALL_REDIS_PASSWORD}@127.0.0.1:$${WATERFALL_REDIS_PORT:-6379}/0 && \
		NODE_EXTRA_CA_CERTS=$(KEYCLOAK_AUTHORITY) && \
		export E2E_INSTALLATION_LINK E2E_SERVICE_API WATERFALL_API_ADDRESS WATERFALL_KEYCLOAK_ADDRESS WATERFALL_REDIS_URL NODE_EXTRA_CA_CERTS && \
		$(PNPM) exec playwright test

# The report of the measures of a version (US-2300, frontend/e2e/measure/version.measure.ts): on a
# platform whose data are dropped and whose witness is loaded afresh, started as for make measure,
# the browser measures each operation of table 15 the service serves under the load of fifty users
# that k6 plays in its service of the platform (frontend/bench/load.ts), then the background tasks:
# the export of the planning, the import of eighteen thousand lines of actual costs, the marking.
# The measure takes the workstation for itself alone ($(exclusive)), and the report, in the form
# make check-measures confronts, is written where MEASURE_VERSION_REPORT says — never under
# docs/measures/ by itself. The container of the load (LOAD_CONTAINER) is stopped at the end of the
# measure, successful or not; after an interruption, make e2e-down or make service-down stops it.
LOAD_CONTAINER = $(WATERFALL_SERVICE_PROJECT)-load
MEASURE_VERSION ?= $(shell sed -n 's/^  "version": "\([^"]*\)".*/\1/p' $(FRONT)/package.json)
MEASURE_VERSION_REPORT ?= $(FRONT)/.e2e/measures/$(MEASURE_VERSION).json
MEASURE_TASK_PASSES ?= 3
# The cost of the entry of the cache of the indicators (US-2420) is not measured here: make measure-core
# ONLY=indicators JSON=<file> measures it, on a witness of its own, and the report of the version takes
# it from MEASURE_CACHE. The two both start from a witness freshly loaded and take the workstation alone:
# they follow each other, they never nest.
MEASURE_CACHE ?= $(FRONT)/.e2e/measure-core-indicators.json
# The file of the cost of the cache is checked first, before the install and the build: its absence costs
# no minute. (Prerequisites run in order; the measure is never played with -j.)
.PHONY: measure-cache-present
measure-cache-present:
	@test -f $(MEASURE_CACHE) || { echo 'The cost of the cache of the indicators is missing: run make measure-core ONLY=indicators JSON=$(MEASURE_CACHE) first.' >&2; exit 1; }
.PHONY: measure-version
$(call slot-export,measure-version,$(SLOT_SERVICE) $(SLOT_PATHS))
measure-version: export WATERFALL_FRONT_ADDRESS = http://127.0.0.1:$(E2E_FRONT_PORT)
measure-version: export WATERFALL_FRONT_BACKCHANNEL = http://host.docker.internal:$(E2E_FRONT_PORT)
measure-version: export WATERFALL_LOAD_CONTAINER = $(LOAD_CONTAINER)
measure-version: export WATERFALL_UID = $(shell id -u)
measure-version: export WATERFALL_GID = $(shell id -g)
measure-version: export E2E_PART = measure-version
measure-version: export E2E_BUILT = 1
measure-version: export WATERFALL_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
measure-version: export E2E_ADMIN_EMAIL := $(E2E_ADMIN_EMAIL)
measure-version: export E2E_MEASURE_PASSES = $(MEASURE_PASSES)
measure-version: export E2E_MEASURE_TASK_PASSES = $(MEASURE_TASK_PASSES)
measure-version: export E2E_MEASURE_VERSION = $(MEASURE_VERSION)
measure-version: export E2E_MEASURE_VERSION_REPORT = $(abspath $(MEASURE_VERSION_REPORT))
measure-version: export E2E_MEASURE_CACHE = $(abspath $(MEASURE_CACHE))
measure-version: export PRISM_VERSION := $(PRISM_VERSION)
measure-version: measure-cache-present measure-secrets install-front $(call e2e-build) ## The report of the measures of a version (US-2300): on the witness loaded afresh, each operation of table 15 the service serves, measured by a browser under the load of fifty users played by k6, then the export, the import of 18,000 lines of actual costs and the marking, read at their tasks; takes the workstation alone; MEASURE_VERSION (that of frontend/package.json), MEASURE_PASSES=5, MEASURE_TASK_PASSES=3, MEASURE_VERSION_REPORT=<file> (frontend/.e2e/measures/<version>.json); the cost of the entry of the cache of the indicators is read in MEASURE_CACHE (frontend/.e2e/measure-core-indicators.json), which make measure-core ONLY=indicators JSON=<that file> writes first; needs the secrets of service-up and a browser
	@$(MAKE) --no-print-directory service-down WATERFALL_RESET_DATA=yes
	@$(MAKE) --no-print-directory service-up
	@$(RETRIED) $(COMPOSE_SERVICE) build --quiet install witness
	@$(COMPOSE_SERVICE) --profile load pull --quiet load
	@E2E_INSTALLATION_LINK=$$($(COMPOSE_SERVICE) run --rm --no-TTY install) && \
		$(COMPOSE_SERVICE) run --rm --no-TTY witness && \
		WATERFALL_API_ADDRESS=http://127.0.0.1:$${WATERFALL_API_PORT:-8000} && \
		WATERFALL_KEYCLOAK_ADDRESS=$(KEYCLOAK_ADDRESS) && \
		WATERFALL_REDIS_URL=redis://:$${WATERFALL_REDIS_PASSWORD}@127.0.0.1:$${WATERFALL_REDIS_PORT:-6379}/0 && \
		NODE_EXTRA_CA_CERTS=$(KEYCLOAK_AUTHORITY) && \
		export E2E_INSTALLATION_LINK WATERFALL_API_ADDRESS WATERFALL_KEYCLOAK_ADDRESS WATERFALL_REDIS_URL NODE_EXTRA_CA_CERTS && \
		{ ( cd $(FRONT) && $(exclusive) $(PNPM_ENV) pnpm exec playwright test ); status=$$?; \
		docker stop --time 60 $(LOAD_CONTAINER) > /dev/null 2>&1; exit $$status; }

# The slot of the worktree, among the N of WATERFALL_SLOTS, in the register of the workstation
# (waterfall-slots of /run/user/<uid>, of /tmp without it), whatever the repository and the session.
# LOT=<identifier> writes the lot in the slot: a deliverer stopped without make slot-release holds
# back no other, the next one of its lot taking its slot over when all are taken (US-2460).
slot: ## Take a slot of 1 to N for this worktree of a lot — its ports and its names —, or say the one it holds; all taken, takes over the one another worktree holds for the same LOT=<identifier>, else fails, naming the holders
	@$(SLOTS) claim$(if $(LOT), --lot '$(subst ','\'',$(LOT))')

slot-release: ## Stop the servers of the e2e paths, remove the containers and volumes of the slot of this worktree — the service platform, the services of the tests —, then free it
	@$(SLOTS) release

e2e-down: ## Stop the servers of the end-to-end paths of the slot of this worktree — the fake back, the fronts —, found by their ports and stopped by PID, and the load of make measure-version; after an interrupted e2e, e2e-service or check-front (US-1300)
	@$(SLOTS) stop-servers
	@docker stop --time 60 $(LOAD_CONTAINER) > /dev/null 2>&1 || true

slots: ## Print N, then the slots taken on the workstation, their worktrees and their lots
	@$(SLOTS) list

# PostgreSQL 18, Redis and Garage of the platform, in memory, on the ports of the slot of the worktree
# (WATERFALL_TEST_POSTGRES_PORT, _REDIS_PORT, _STORAGE_PORT): what the tests of the back and of the
# front are given by make test-back and the others, unless their WATERFALL_TEST_*_URL says otherwise.
test-services: ## Start, for the slot of this worktree, the services the tests run against — PostgreSQL, Redis, Garage — and wait for them; running, they stay as they are (SERVICES=<some of them>)
	@$(COMPOSE_TEST) up --detach --wait $(SERVICES)

test-services-down: ## Remove the services of the tests of the slot of this worktree, their volumes included
	@$(COMPOSE_TEST) down --volumes

# The reference of the measures of the grids, before any correction (US-2210/L4): the reports of
# make measure-core (CORE) and make measure (JOURNEY), as written, and the target of the API for
# opening a grid, in docs/measures/reference.json. Not the report of a version.
measure-reference: ## Assemble docs/measures/reference.json from the JSON of measure-core (CORE=<file>) and of measure (JOURNEY=<file>)
	$(if $(and $(CORE),$(JOURNEY)),,$(error measure-reference needs CORE=<JSON of make measure-core> and JOURNEY=<JSON of make measure>))
	@$(WFTOOLS).measurereference "$(CORE)" "$(JOURNEY)" docs/measures/reference.json \
		--commit "$(or $(MEASURED_COMMIT),$$(git merge-base origin/epic/EP-26 HEAD))"

lot-size: ## The real size of a lot, against its epic (BASE=origin/epic/EP-nn); never fails
	@$(WFTOOLS).lotsize "$(BASE)" $(HEAD)

# A variable of the table is taken only when it comes from the command line of make: one exported
# on the workstation (PR, STATE, MODEL…) must not overwrite a cell of the shared table. Make
# exports the command-line variables to the recipe; an empty value is ignored.
tracking_option = $(if $(filter command line,$(origin $(1))),$${$(1):+$(2) "$$$(1)"})

tracking: ## Change a line of the tracking table of an epic's issue, under a lock: ISSUE=<n> with LOT=<id> [STATE PR MODEL DEPENDS NOT_WITH], US=<id> STATUS=…, FINDING=<n> ATTACHED=… DECISION=…, ADD_LOT=<id> AFTER=<lot> [DEPENDS NOT_WITH MODEL LOT_ISSUE], ADD_US=<US-nnnn> AFTER=<US-mmmm> [US_ISSUE FIRST_LOT=<Ln> LOT_ISSUE (with FIRST_LOT only) DEPENDS NOT_WITH MODEL], or REPLACE_DEPENDENCY='<old>=<new>'
	@$(WFTOOLS).tracking $(call tracking_option,ISSUE,--issue) $(call tracking_option,LOT,--lot) \
		$(call tracking_option,US,--us) $(call tracking_option,FINDING,--finding) \
		$(call tracking_option,STATE,--state) $(call tracking_option,PR,--pr) \
		$(call tracking_option,MODEL,--model) $(call tracking_option,STATUS,--status) \
		$(call tracking_option,ATTACHED,--attached) $(call tracking_option,DECISION,--decision) \
		$(call tracking_option,ADD_LOT,--add-lot) $(call tracking_option,AFTER,--after) \
		$(call tracking_option,DEPENDS,--depends) $(call tracking_option,NOT_WITH,--not-with) $(call tracking_option,LOT_ISSUE,--issue-number) \
		$(call tracking_option,ADD_US,--add-us) $(call tracking_option,US_ISSUE,--us-issue) \
		$(call tracking_option,FIRST_LOT,--first-lot) \
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
		|| echo "  warning  python3 is not $$v, the version of $(TOOLS)/.python-version: the guard would refuse every command and the slots would not run"; \
	fi
	@command -v pandoc >/dev/null && pandoc --version | head -1 | grep -q " 3.13$$" \
		|| echo "  warning  pandoc is not 3.13: the projection would differ from the chain's"
	@/usr/bin/pg_restore --version 2>/dev/null | grep -q " 18\." \
		|| echo "  warning  /usr/bin/pg_restore is not PostgreSQL 18, the server's: the tests of the backups and restorations would fail (#982)"
	@command -v mmdc >/dev/null && echo "  ok       mmdc" || echo "  absent   mmdc (diagrams will not be validated)"

clean: ## Remove everything the commands generate
	@rm -rf $(SPEC)/.build $(SPEC)/images $(BUNDLE) $(JSON_BUNDLE) $(MOCK_SPEC) $(PROXY_SPEC) $(FRONT)/.e2e
	@echo "  cleaned"

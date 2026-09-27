# Waterfall — repository commands.
#
# The specification lives in docs/spec, the interface contract in docs/api.
# Requirements: python3, pandoc (document projection), node with npx (contract
# linting and bundling), and mmdc to validate the diagrams.

SPEC    := docs/spec
API     := docs/api
BUNDLE  := $(API)/waterfall.bundle.yaml
# Pinned so that a check passes or fails on what this repository contains, never on
# what a tool released overnight. Raise a version here and nowhere else.
REDOCLY_VERSION := 2.54.3
PRISM_VERSION   := 5.16.0
REDOCLY := npx --yes @redocly/cli@$(REDOCLY_VERSION)
PRISM   := npx --yes @stoplight/prism-cli@$(PRISM_VERSION)

.DEFAULT_GOAL := help
.PHONY: help build-doc build-doc-strict build-openapi lint-openapi inventory allocate-pbs mock check-tools clean

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

mock: build-openapi ## Serve a fake backend from the contract, for the mockup
	@$(PRISM) mock $(BUNDLE)

check-tools: ## Report which prerequisites are missing
	@for t in python3 pandoc npx; do \
		command -v $$t >/dev/null && echo "  ok       $$t" || echo "  missing  $$t"; \
	done
	@command -v mmdc >/dev/null && echo "  ok       mmdc" || echo "  absent   mmdc (diagrams will not be validated)"

clean: ## Remove everything the commands generate
	@rm -rf $(SPEC)/.build $(SPEC)/images $(BUNDLE)
	@echo "  cleaned"

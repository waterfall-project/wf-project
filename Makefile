# Waterfall — commandes du dépôt.
#
# La spécification est dans docs/spec, le contrat d'interface dans docs/api.
# Prérequis : python3, pandoc (projection du document), node avec npx
# (contrôle et assemblage du contrat), mmdc pour valider les diagrammes.

SPEC    := docs/spec
API     := docs/api
BUNDLE  := $(API)/waterfall.bundle.yaml
REDOCLY := npx --yes @redocly/cli@latest
PRISM   := npx --yes @stoplight/prism-cli@latest

.DEFAULT_GOAL := help
.PHONY: help build-doc build-doc-strict build-openapi lint-openapi inventaire pbs mock outils clean

help: ## Liste les commandes
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

build-doc: ## Régénère la projection Markdown depuis Word et draw.io
	@$(SPEC)/build.sh

build-doc-strict: ## Comme build-doc, mais échoue au moindre avertissement (CI)
	@$(SPEC)/build.sh --strict

lint-openapi: ## Contrôle le contrat d'interface
	@cd $(API) && $(REDOCLY) lint openapi.yaml

build-openapi: lint-openapi ## Contrôle puis assemble le contrat en un fichier
	@cd $(API) && $(REDOCLY) bundle openapi.yaml -o $(notdir $(BUNDLE))
	@echo "  → $(BUNDLE)"

inventaire: ## Régénère l'inventaire des endpoints et la couverture des exigences
	@python3 $(API)/tools/inventaire.py

pbs: ## Écrit les champs PBS des exigences dans le document Word
	@python3 $(SPEC)/tools/appliquer_pbs.py

mock: build-openapi ## Sert un faux back depuis le contrat, pour la maquette
	@$(PRISM) mock $(BUNDLE)

outils: ## Vérifie les prérequis
	@for o in python3 pandoc npx; do \
		command -v $$o >/dev/null && echo "  ok      $$o" || echo "  manque  $$o"; \
	done
	@command -v mmdc >/dev/null && echo "  ok      mmdc" || echo "  absent  mmdc (les diagrammes ne seront pas validés)"

clean: ## Supprime ce que les commandes engendrent
	@rm -rf $(SPEC)/.build $(SPEC)/images $(BUNDLE)
	@echo "  nettoyé"

# Guide de développement

Ce guide fixe ce qui doit se ressembler d'un lot à l'autre, qu'une personne ou un agent
l'ait écrit : où chaque chose vit, comment elle se nomme, et la forme des pièces qui se
répètent. Il ne recopie ni la spécification (`docs/spec`), ni le contrat (`docs/api`), ni
[CONTRIBUTING](../../CONTRIBUTING.md), ni la [roadmap](../roadmap/README.md) : il y renvoie.

Chaque règle qu'un outil peut contrôler l'est, et la règle nomme son contrôle ; une règle
que rien ne contrôle le dit. Le guide s'écrit en même temps que le socle (EP-01) : chaque US
y ajoute la section qu'elle établit, et une section encore vide nomme celle qui l'écrira.

## Arborescence

| Chemin | Contenu | PBS |
|---|---|---|
| `backend/` | un seul projet Python, un seul paquet `waterfall` : le noyau (`core/`, un sous-paquet par module, calqué sur un bloc FBS), le service d'API (`api/`), le worker (`worker/`) ; les tests dans `backend/tests/` | PBS-2 |
| `frontend/` | l'application Next.js ; le client engendré dans `frontend/src/api/` ; les parcours de bout en bout dans `frontend/e2e/` | PBS-1 |
| `fixtures/` | le relevé engendré des exemples chiffrés des Vérif, et les fixtures qui s'y rattachent | — |
| `tools/` | les outils du dépôt, un seul paquet Python, `wftools`, et leurs tests | PBS-5.2 |
| `deploy/compose/`, `deploy/helm/` | l'empaquetage : Compose, puis le chart Helm en EP-13 | PBS-5.1 |
| `.github/workflows/` | la chaîne | PBS-5.2 |
| `docs/spec/`, `docs/api/`, `docs/roadmap/` | la spécification, le contrat, la roadmap | — |
| `docs/dev/` | ce guide, et les règles de codage par langage | — |
| `LICENSES/`, `REUSE.toml` | les textes des licences, et la licence des fichiers qui ne portent pas d'en-tête | — |

Un répertoire naît avec le lot qui y met le premier fichier : `backend/`, `frontend/`,
`fixtures/` et `deploy/` n'existent pas encore tous. La conception d'EP-01 dit pourquoi
chaque chose est là (`docs/roadmap/EP-01-socle-de-developpement.md`, « Conception »).

## Le back et les frontières du noyau

Le back est un seul paquet, `waterfall`, et deux processus : `waterfall-api` et
`waterfall-worker`, deux points d'entrée d'une même distribution. Ils portent donc la même
version par construction, celle de `backend/pyproject.toml` (WF-ARC-0010).

Le noyau, `waterfall.core`, a un sous-paquet par module, nommé d'après son bloc FBS de
second niveau, en anglais. Un module expose ce que les autres peuvent utiliser dans son
module `interface`, et rien d'autre : ses tables et son accès aux données lui sont privés.
Un module en importe un autre par `waterfall.core.<module>.interface`, jamais par ses
tables. Le noyau n'importe ni l'API ni le worker, qui ne s'importent pas l'un l'autre.

*Contrôle* : `make imports-back` (import-linter, contrats dans `backend/pyproject.toml`) ;
un test les éprouve sur un paquet d'essai (`backend/tests/test_boundaries.py`). Une requête
SQL écrite en texte, qui nommerait la table d'un autre module, échappe à l'analyse des
imports : elle relève des règles SQL d'EP-03 et de la revue.

## Commandes

Tout se lance par le Makefile, sur un poste comme dans la chaîne : `make help` les liste.
Une commande que la chaîne exécute existe dans le Makefile, et un workflow n'écrit aucune
logique de contrôle de son côté ; un échec de la chaîne se reproduit donc par la même
commande.

| Commande | Ce qu'elle fait |
|---|---|
| `make check BASE=origin/epic/EP-nn` | les contrôles de ce que la modification touche, fichiers non commités compris : à lancer avant de pousser |
| `make check-all` | toutes les familles de contrôles |
| `make check-<famille>` | une famille : `repo`, `spec`, `contract`, `back` — puis `front` et `roadmap` avec les lots qui les créent |
| `make changes BASE=…` | les familles qu'une modification touche |

`BASE` vaut `origin/main` par défaut ; un lot se compare à la branche de son EPIC.

## Chaîne

La chaîne est faite de workflows GitHub Actions (`.github/workflows/`) :

- `ci.yml` décide des familles qu'une pull request touche (`make changes`), appelle le
  workflow de chacune, et termine par la **porte** (`gate`), qui juge le tout
  (`make gate`) : elle échoue si un travail a échoué ou a été annulé, et un travail sauté
  parce que sa famille n'est pas touchée n'est pas un échec. La porte est le seul contrôle
  que la protection des branches exige : un contrôle exigé qui ne s'exécute pas faute de
  fichier touché resterait « en attente » et bloquerait la fusion.
- un workflow par famille — `repo.yml`, `spec.yml`, `contract.yml`… —, qui installe ses
  outils et appelle `make check-<famille>`. `repo` s'exécute sur toute modification.

Les familles, les chemins qui les réveillent, les chemins engendrés et ceux des tests sont
déclarés dans `tools/paths.toml`, et nulle part ailleurs. Un chemin de `shared` — le
Makefile, les workflows, la déclaration elle-même — réveille toutes les familles.

Deux paliers : le rapide à chaque poussée sur une pull request (`pull_request`), le complet
dans la file de fusion (`merge_group`), sur le résultat de la fusion, avant qu'elle soit
acceptée.

Règles des workflows :

- une action tierce est épinglée par l'empreinte de son commit, la version en commentaire ;
  Dependabot propose chaque mois leur mise à jour (`.github/dependabot.yml`) ;
- chaque workflow déclare `permissions: contents: read`, et n'en demande pas plus sans
  raison écrite ;
- `actions/checkout` ne garde pas le jeton (`persist-credentials: false`) ;
- un outil téléchargé hors d'une action est épinglé par sa version et vérifié par son
  empreinte, comme pandoc dans `spec.yml`.

*Contrôle* : `make lint-workflows` (actionlint) ; l'épinglage et les permissions, la revue.

La protection des branches est un réglage de GitHub, fait par le propriétaire du dépôt :
sur `epic/*`, pas de poussée directe, la porte exigée, la file de fusion ; sur `main`, la
porte n'est exigée qu'à partir de la livraison d'EP-01 — GitHub lit les workflows dans la
branche d'une pull request, et une pull request vers `main` tirée d'avant la chaîne ne la
déclencherait pas.

## Nommage

Le code, les tables, les colonnes, les variables, les chemins et les messages de console
sont en anglais ; la documentation est en français, comme la spécification. Les noms des
objets du domaine sont ceux du tableau de correspondance du §4.4.1 de la spécification
(`estimate_line`, `cost_line`, `revision`…), et les conventions du contrat — `snake_case`,
`operationId` en `camelCase`, identifiants UUID — sont dans `docs/api/README.md`.

*Contrôle* : aucun outil ne vérifie la langue d'un nom ; la revue le fait.

## En-têtes et licences

Chaque fichier de code commence par deux lignes, après la ligne `#!` s'il en a une :

<!-- REUSE-IgnoreStart -->
```text
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only
```
<!-- REUSE-IgnoreEnd -->

dans la syntaxe de commentaire du langage. Le nom du fichier n'y figure pas : il deviendrait
faux au premier renommage ; la première ligne de la docstring du module dit à quoi il sert.
Ce qui ne peut pas porter de commentaire, ou n'y gagnerait rien — documentation, figures,
contrat, gabarits, images, fichiers engendrés — est déclaré dans `REUSE.toml`. Le code de
conduite garde sa propre licence, CC BY 4.0.

Un document qui cite ces deux lignes, comme celui-ci, les encadre de
`REUSE-IgnoreStart` et `REUSE-IgnoreEnd`, faute de quoi l'outil les lirait comme la licence
du document.

*Contrôle* : `make reuse` échoue sur un fichier couvert ni par un en-tête ni par
`REUSE.toml`.

## Outils du dépôt

Les outils vivent dans `tools/`, en Python, avec leurs tests (`make test-tools`). Tout outil
qui a besoin des exigences les lit par `wftools.projection`, qui lit la projection
`docs/spec/waterfall-spec.md` : un seul lecteur, pour que deux outils ne puissent pas
diverger sur ce qu'une exigence dit. Il compare les textes après normalisation — apostrophes
et espaces typographiques rendus simples —, et découpe un Vérif en phrases. L'exemple du
§1.3.1, `WF-EXAMP-0010-A`, n'est pas une exigence du produit : les outils l'excluent.

*Contrôle* : `make test-tools`.

## Commentaires

Un commentaire dit pourquoi, pas ce que fait le code : la raison d'un choix, un invariant,
un cas limite. Il est en anglais, comme le code.

*Contrôle* : aucun outil ne juge ce qu'un commentaire dit ; la revue le fait. La forme des
docstrings, le code commenté et les `TODO` sont contrôlés : voir « Lint, typage et format ».

## Lint, typage et format

*À écrire* — [US-0050](https://github.com/waterfall-project/wf-project/issues/10), lots
[US-0050/L1](https://github.com/waterfall-project/wf-project/issues/18) et
[US-0050/L2](https://github.com/waterfall-project/wf-project/issues/20).

## Règles de codage

*À écrire* — `python.md` et `typescript.md`, par l'[US-0300](https://github.com/waterfall-project/wf-project/issues/4).

## Tests

- **Un test qui cite son exigence** — *à écrire*, [US-0060](https://github.com/waterfall-project/wf-project/issues/11).
- **Un test qui reprend un exemple chiffré** — *à écrire*, [US-0040](https://github.com/waterfall-project/wf-project/issues/9).
- **Un parcours de bout en bout** — *à écrire*, [US-0080](https://github.com/waterfall-project/wf-project/issues/13).

## Enveloppe d'erreur et codes d'erreur

L'enveloppe est fixée par le contrat (`docs/api/README.md`, WF-ARC-0110) : un code machine et
ses paramètres, jamais une phrase.

- **Ajouter un code côté front** — *à écrire*, US-0190 (EP-02), qui crée le catalogue des
  codes.
- **Ajouter un code côté service** — *à écrire*, EP-03, qui crée le service.

## Clés de traduction

*À écrire* — US-0190 (EP-02), qui choisit la bibliothèque et crée les catalogues.

## Migrations

*À écrire* — EP-03, avec la première table et les règles de codage du SQL.

## Branches, lots et pull requests

Les règles sont dans le [README de la roadmap](../roadmap/README.md), sections « Lots » et
« Branches », et dans [CONTRIBUTING](../../CONTRIBUTING.md) : un lot, une issue, une branche
`lot/<identifiant>` tirée de `epic/EP-nn`, une pull request qui y revient.

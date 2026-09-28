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

## Le front

Le front est une application Next.js en TypeScript strict (`frontend/tsconfig.json`, avec
`noUncheckedIndexedAccess` et `exactOptionalPropertyTypes`). pnpm en gère les dépendances,
à la version que nomme `packageManager` dans `package.json`, lancée par corepack
(`corepack enable pnpm`) ; le verrou, `pnpm-lock.yaml`, fait foi et la chaîne installe
avec `--frozen-lockfile`. Les tests unitaires sont des fichiers `*.test.ts` ou `*.test.tsx`
à côté du code qu'ils éprouvent, lancés par Vitest.

L'image de développement (`frontend/Dockerfile`) part d'une image épinglée par son
empreinte, et tourne sous un utilisateur non privilégié, désigné par son numéro.

Le client de l'API est engendré du contrat (PBS-1.2, WF-ARC-0060) : `make generate-client`
écrit ses types dans `frontend/src/api/generated/schema.d.ts`, que personne ne retouche, et
`frontend/src/api/client.ts` en fait des appels typés par openapi-fetch. Une opération qui
manque au client est une modification du contrat, suivie d'un `make generate-client` ; le
fichier engendré se versionne avec elle. Aucun appel réseau ne s'écrit hors de
`frontend/src/api/`.

*Contrôles* : `make client-up-to-date` échoue si le client versionné n'est pas celui que le
contrat produit ; une modification du contrat réveille donc la famille front. ESLint refuse
`fetch` hors de `src/api/`. `make typecheck-front`, `make test-front` ; `make lint-docker`
(hadolint).

## Le faux back

Le faux back sert le contrat par prism, sans une ligne de réponse écrite à la main : ce qu'il
répond, ce sont les **exemples du contrat**. Une réponse qui manque est un exemple ajouté au
contrat, jamais un fichier dans le front ; un exemple invalide au regard de son schéma fait
échouer `make lint-openapi`.

Un exemple long se range sous `fixtures/api/`, en objet Example d'OpenAPI (`summary`,
`value`), et le contrat le cite par `$ref` ; le bundle l'embarque. Ses nombres reprennent
ceux des Vérif là où ils ont un sens — probabilité de gain, inflation, montants.

`make mock-spec` dérive du contrat la variante que prism sert : chemins sous le préfixe du
serveur, `/api/v1`, que prism ignorerait, et aucune session exigée — le faux back accorde
celle dont part la maquette (EP-02). Rien d'autre ne change.

- `make mock` : le faux back seul, sur `http://localhost:4010`.
- `make dev` : le front (`http://localhost:3000`) contre le faux back, par
  `deploy/compose/compose.dev.yaml`. Le front ne connaît que l'adresse de l'API,
  `WATERFALL_API_ADDRESS` : à partir d'EP-03, la même variable désigne le vrai service.

Le faux back sert des lectures. Il ne garde aucun état : un projet créé n'apparaît pas dans
la liste suivante. Il sert aux lots de front qui précèdent leur lot de back et aux tests du
front qui ne font que lire, jamais à éprouver une écriture.

*Contrôles* : `make lint-openapi` (exemples conformes aux schémas), `make lint-compose`.

## Commandes

Tout se lance par le Makefile, sur un poste comme dans la chaîne : `make help` les liste.
Une commande que la chaîne exécute existe dans le Makefile, et un workflow n'écrit aucune
logique de contrôle de son côté ; un échec de la chaîne se reproduit donc par la même
commande.

| Commande | Ce qu'elle fait |
|---|---|
| `make check BASE=origin/epic/EP-nn` | les contrôles de ce que la modification touche, fichiers non commités compris : à lancer avant de pousser |
| `make check-all` | toutes les familles de contrôles |
| `make check-<famille>` | une famille : `repo`, `spec`, `contract`, `back`, `front`, `roadmap` |
| `make changes BASE=…` | les familles qu'une modification touche |

`BASE` vaut `origin/main` par défaut ; un lot se compare à la branche de son EPIC.

`make lot-size BASE=origin/epic/EP-nn` mesure un lot : les lignes de son diff, séparées en
code de production, tests et le reste (documentation, configuration, contrat), les fichiers
engendrés mis à part. La pull request met ce nombre à côté de l'estimation de son issue ; un
dépassement ne fait rien échouer (README de la roadmap, section « Lots »).

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
acceptée. Le palier complet ajoute ce qui est lent — la couverture du code, puis les tests de
bout en bout ; sur un poste, `make check-back TIER=full`. Une pull request entre dans la file par
le bouton « Merge when ready », ou par la mutation `enqueuePullRequest` de l'API GraphQL :
`gh pr merge` ne sait pas le faire tant que la fusion automatique est désactivée sur le
dépôt. Une branche sans file de fusion fait tourner le palier complet à la main sur la
branche d'un lot, avant de le fusionner : `gh workflow run chain --ref <branche>`.

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

## La roadmap et les exigences

Les US de `docs/roadmap` citent les exigences qu'elles réalisent, et leurs critères
d'acceptation reprennent le Vérif de chacune **mot pour mot**, en critère ou en écart : ce
sont les cas de test à venir. `make roadmap` confronte la roadmap au document, et échoue :

- sur un identifiant inconnu, ou d'un indice de révision que le document a dépassé, dans un
  tableau d'EPIC comme dans une US ;
- sur une phrase du Vérif d'une exigence citée, absente de l'US ou tronquée — une phrase se
  cite entière, point final compris ; les apostrophes et les espaces typographiques ne
  comptent pas ;
- sur une exigence du tableau d'un EPIC qu'aucune de ses US ne cite, sauf si l'EPIC est
  `à planifier` ;
- sur une exigence qu'aucun EPIC ne close, ou que plusieurs closent.

Il liste, sans échouer, les exigences F0 qu'aucune US ne cite encore : leur nombre décroît à
mesure que les US des EPIC suivants s'écrivent. L'outil ne lit que le dépôt : l'état des
issues n'est pas son affaire.

Il échoue aussi sur une commande `make` que cite un agent (`.claude/agents/`,
`docs/dev/agents.md`) et que le Makefile n'a pas : une cible renommée ne laisse pas un agent
appeler une commande disparue.

*Contrôle* : `make roadmap`, famille `roadmap` de la chaîne, réveillée aussi par un
changement de la projection ou des agents.

## Commentaires

Un commentaire dit pourquoi, pas ce que fait le code : la raison d'un choix, un invariant,
un cas limite. Il est en anglais, comme le code.

*Contrôle* : aucun outil ne juge ce qu'un commentaire dit ; la revue le fait. La forme des
docstrings, le code commenté et les `TODO` — toujours `TODO(#12): …`, avec le numéro de
l'issue — sont contrôlés : voir « Lint, typage et format ».

## Lint, typage et format

Ce que la spécification appelle analyse statique (WF-QUA-0030) : tout est bloquant, et aucun
avertissement n'est toléré ; ce qui ne mérite pas de bloquer se retire du jeu de règles.

**Python** — le back et les outils du dépôt partagent un seul jeu de règles,
`ruff.toml`, à la racine :

- toutes les règles de Ruff sont actives ; celles qui sont retirées sont listées, chacune
  avec sa raison, et l'historique du fichier montre chaque retrait ;
- complexité cyclomatique inférieure à 15 par fonction (`C901`, maximum 14) ;
- l'en-tête SPDX (`CPY001`), une docstring d'une ligne pour ce qui est public (`D1`,
  convention PEP 257 ; ni les tests ni les méthodes spéciales n'en demandent), pas de code
  commenté (`ERA001`), un `TODO` qui cite son issue (`TD003`) ;
- Pyright en mode strict (`[tool.pyright]` de chaque projet), `# type: ignore` non honoré.

**Aucune règle ne s'écarte par un commentaire dans le code.** Une exception, s'il en faut
une, s'écrit dans la configuration de l'outil — `per-file-ignores` de `ruff.toml` —, avec sa
raison. Aucun fichier source ne dépasse 1 000 lignes, lignes vides et commentaires compris ;
les fichiers engendrés en sont exclus.

*Contrôles* : `make lint-back`, `make typecheck-back`, `make lint-tools`,
`make typecheck-tools` ; `make sources` pour les commentaires d'exemption et la taille des
fichiers, sur tout le dépôt. Les outils de `docs/spec/tools` et `docs/api/tools` suivent
les mêmes règles que ceux de `tools/` ; une exception, s'il en faut une, se déclare dans
`tools/paths.toml`, avec sa raison et ce qui la lèvera.

**TypeScript** — le front a son jeu de règles dans `frontend/eslint.config.mjs` :

- les configurations recommandées d'ESLint, de Next.js (`core-web-vitals`) et de
  typescript-eslint en mode strict, avec les informations de type ; ce qui leur est ajouté
  ou retiré est écrit dans le fichier, avec sa raison ;
- complexité cyclomatique inférieure à 15 (`complexity`, maximum 14) ; 1 000 lignes au plus
  par fichier (`max-lines`) ;
- une docstring JSDoc pour ce qui est exporté, sans type — TypeScript les porte
  (`jsdoc/no-types`) — et sans section par paramètre, qui répéterait la signature ;
- aucun `fetch` hors de `src/api/` : l'API ne s'appelle que par le client engendré
  (WF-ARC-0020) ;
- Prettier pour le format (`frontend/.prettierrc.json`) ; ESLint s'exécute avec
  `--max-warnings 0`.

Les commentaires de configuration dans le code ne sont pas honorés (`noInlineConfig`) et
`make sources` les refuse. Un `TODO` cite son issue, sous la même forme qu'en Python :
`TODO(#12): …` ; les autres étiquettes d'attente sont refusées — c'est `make sources` qui le
vérifie, ESLint n'ayant pas d'équivalent aux règles `TD` et `FIX` de Ruff.

*Contrôles* : `make lint-front` (ESLint, Prettier), `make typecheck-front`, `make sources`.

**Contrat** — `docs/api/redocly.yaml` étend `recommended-strict` : toute règle de Redocly
bloque. Une opération à laquelle une règle ne s'applique pas — une sonde sans réponse 4xx,
une redirection OIDC sans réponse 2xx — est déclarée dans `docs/api/.redocly.lint-ignore.yaml`,
avec sa raison.

*Contrôle* : `make lint-openapi`.

## Règles de codage

Comment s'écrit chaque langage : [Python](python.md), pour le back et les outils, et
[TypeScript](typescript.md), pour le front. Chacun nomme d'abord les jeux de règles des
outils, par renvoi, puis les règles de conception qu'aucun outil ne contrôle, chacune avec
sa raison, et finit par les défauts déjà rencontrés, que la revue cherche nommément. Les
règles d'écriture du SQL et des migrations viennent avec EP-03, en troisième fichier.

## Tests

- **Un test qui cite son exigence** — voir ci-dessous.
- **Un test qui reprend un exemple chiffré** — voir ci-dessous.
- **Un parcours de bout en bout** — voir ci-dessous.

### Un test qui cite son exigence

Chaque exigence F0 est couverte par au moins un test qui la cite par son identifiant complet,
indice de révision compris (WF-QUA-0010).

- **Python** : le marqueur `@pytest.mark.requirement("WF-ARC-0010-A")`, sur le test, sur sa
  classe, ou sur le module (`pytestmark = pytest.mark.requirement(...)`) quand tout le
  fichier porte la même exigence. Le marqueur est déclaré : une faute de frappe dans son nom
  fait échouer Pytest.
- **TypeScript** — Vitest ou Playwright : l'identifiant entre crochets dans le titre,
  `it("lit une grille [WF-QUA-0050-A]", …)`.

Un test cite l'exigence dont il éprouve le Vérif, pas celle dont il parle. Un test qui ne
couvre aucune exigence — un outil, un détail de réalisation — n'en cite aucune.

*Contrôles* : `make requirements` lit les citations dans les fichiers de test, sans les
lancer, et publie le relevé — chaque exigence F0 avec les tests qui la couvrent — dans le
résumé du travail de la chaîne ; une citation d'un identifiant inconnu, ou d'un indice de
révision que le document a dépassé, le fait échouer. `make requirements-release` échoue en
plus sur toute exigence F0 non couverte, en la nommant : c'est la commande de la
publication d'une version.

### Un parcours de bout en bout

Un parcours s'écrit sous `frontend/e2e/`, en Playwright, et cite dans son titre l'exigence
qu'il couvre : `test("… [WF-QUA-0050-A]", …)`. Il trouve les éléments par leur rôle et leur
nom accessible (`getByRole`), comme un utilisateur les voit, jamais par une classe CSS.

`make e2e` : Playwright démarre le faux back (`make mock`) et le front, joue les parcours
dans Chromium, puis arrête les deux — il signale leur groupe de processus entier, sans quoi
les serveurs que `make` et `pnpm` lancent survivraient. `make e2e-browsers` installe le
navigateur. À partir d'EP-03, les mêmes parcours se jouent contre le vrai service en
changeant `WATERFALL_API_ADDRESS`.

Le parcours témoin — liste des projets, projet, grille — traverse trois pages minimales,
sans texte propre, qu'EP-02 remplace en gardant le parcours. Elles lisent l'API côté
serveur (`frontend/src/api/server.ts`) ; leurs tests unitaires reçoivent les exemples du
contrat par `frontend/src/test/fixtures.ts`, les mêmes données que sert le faux back.

*Contrôle* : `make e2e`, au palier complet de la chaîne ; l'échec d'un parcours la fait
échouer.

### Couverture du code

La spécification ne demande que la couverture des exigences ; la couverture du code est une
règle du dépôt, qui trouve ce que la première ne voit pas — un chemin d'erreur jamais
exécuté, du code mort. Le back et le front doivent chacun couvrir **90 % des lignes et 85 %
des branches** : les branches comptent, parce qu'un `if` sans son `else` couvre toutes ses
lignes et la moitié des cas. Le code engendré en est exclu. Aucune ligne ne s'exclut de la
mesure par un commentaire ; une exclusion s'écrit dans la configuration, avec sa raison
(`[tool.coverage.report]` de `backend/pyproject.toml`, `coverage` de
`frontend/vitest.config.ts`). Un test qui passe sur des lignes sans rien vérifier est un
défaut, que la revue relève.

*Contrôles* : `make coverage-back`, `make coverage-front`, au palier complet : ils nomment
les fichiers les moins couverts quand un seuil n'est pas atteint.

### Un test qui reprend un exemple chiffré

Chaque phrase chiffrée d'un champ Vérif est un cas de test du noyau, avec les mêmes entrées
et la même valeur attendue (WF-QUA-0020). `make fixtures` les relève dans
`fixtures/examples.json` — fichier engendré, qu'on ne retouche pas —, chacune sous une clé
faite de l'exigence et de l'empreinte de son texte : `WF-PTF-0020-A#ab12cd34ef56`.

Pour éprouver un exemple :

1. écrire une fixture sous `fixtures/`, un fichier JSON qui cite dans `examples` la clé de
   la phrase, et porte ses données, recopiées de la phrase ;
2. écrire le test sous `backend/tests/examples/` : la fixture `example` le charge par la
   clé, le test appelle le noyau et compare à la valeur de la phrase.

Les sockets y sont fermées : un exemple qui passe ne demande ni base, ni service, ni
navigateur. Une phrase modifiée dans le document change de clé ; la fixture de l'ancienne
fait alors échouer la chaîne, et on la réécrit d'après la nouvelle phrase.

*Contrôles* : `make check-fixtures` — le relevé est à jour, chaque clé citée existe, et les
exemples qu'aucune fixture ne cite encore sont listés, sans échec : leur nombre décroît avec
les EPIC de calcul (EP-06 à EP-11).

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

## Agents

Les agents de `.claude/agents/` — cadrage, livraison, développement et revue par langage —
suivent ce guide comme une personne, et leurs règles propres sont dans
[agents.md](agents.md) : ce qui fait foi, comment un lot se fait, où un agent s'arrête.

## Branches, lots et pull requests

Les règles sont dans le [README de la roadmap](../roadmap/README.md), sections « Lots » et
« Branches », et dans [CONTRIBUTING](../../CONTRIBUTING.md) : un lot, une issue, une branche
`lot/<identifiant>` tirée de `epic/EP-nn`, une pull request qui y revient.

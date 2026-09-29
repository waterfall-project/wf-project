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
à côté du code qu'ils éprouvent, lancés par Vitest en deux projets (`vitest.config.ts`),
que le nom du fichier départage : `node` pour les `*.test.ts` et `*.test.tsx` — la logique,
et les composants serveur de `src/app/`, qui se rendent sans document comme en production —,
`dom` pour les `*.dom.test.ts` et `*.dom.test.tsx` — les composants client, que Testing
Library rend dans le document de happy-dom.

La coquille (`frontend/src/components/shell/`) tire sa navigation de
`frontend/src/navigation/functions.json` : pour chaque fonction de second niveau de la FBS,
son code, la clé de son libellé, sa route, sa portée et la permission qui la laisse
consulter ; une fonction dont la session n'a pas la permission `<fonction>.read` n'y figure
pas. La table ne porte encore que le second niveau : les feuilles adressables y entrent avec
le contrôle de complétude des écrans, que le lot EP-02/L3 (#125) ajoute. Trois portées : hors projet ; `project`, les fonctions du
projet lui-même — révisions, paramètres, cycle de vie —, sous `/projects/[projectId]/…`,
qu'un projet sans révision offre ; `revision`, les autres, sous
`/projects/[projectId]/revisions/[revisionId]/…`. Le contexte de lecture est dans l'adresse :
le projet dans le chemin, la révision dans le chemin ou, sur une fonction du projet, en
paramètre `revision_id` ; sous-projet filtré et date de calcul en paramètres, `subproject_id`
et `as_of`, comme le contrat les nomme. Les liens entre fonctions d'un projet les reportent,
et un témoin du front, `wf_last_project`, garde le dernier, dont la coquille tire le « retour
au projet » (WF-IHM-0010) ; il ne ramène qu'à un écran de projet de la table. Chaque route
existe dès la coquille, servie par la page d'attente `frontend/src/app/[...path]/page.tsx`,
qui répond « introuvable » quand l'API ne trouve pas le projet ou la révision ; le lot d'un
écran écrit sa page à la même route, qui l'emporte sur elle.

Les pages système sont des pièces de la coquille (`frontend/src/app/`,
`frontend/src/components/system/`). Une lecture dont un écran ne peut se passer passe par
`readOrFail` de `frontend/src/api/problem.ts`, qui rend ses données ou lève : un 404 mène à
l'écran « introuvable » unique (`not-found.tsx`), qu'une adresse inexistante et une lecture
refusée atteignent sans distinction (WF-ADM-0110) ; l'API injoignable lève `Unreachable`, et
toute autre réponse `UnexpectedAnswer`. L'écran de panne (`error.tsx` dans la coquille,
`global-error.tsx` quand le layout racine échoue) ne reçoit en production que le `digest` de
l'erreur levée côté serveur : `Unreachable` porte `UNREACHABLE_DIGEST`, qu'il annonce comme
tel, `SignedOut` (un 401) `SESSION_REQUIRED_DIGEST`, qui mène à la connexion
(`loginHref`), `UnexpectedAnswer` l'identifiant de corrélation de l'enveloppe, préfixé de
`WATERFALL_CORRELATION;` pour qu'aucune valeur de l'API ne prenne un sens pour Next
(`NEXT_REDIRECT;…`), et qu'il affiche en référence sans le préfixe (`failure.ts`). Sans
enveloppe, ou sans `correlation_id`, la référence affichée est le digest que Next calcule,
celui de ses propres journaux. Un écran ne dit jamais « vide » sur une réponse qu'il n'a pas
lue. Quand la session est illisible, la navigation garde l'écran d'état (WF-ADM-0130).
Chaque segment qui lit l'API a son `loading.tsx`, le squelette `ScreenSkeleton`, qui
porte un `role="status"` nommé — un lecteur d'écran ne l'annonce pas toujours ; la réponse est alors diffusée, et « introuvable » répond
200 et non 404 — un 404 doux, que Next marque `noindex` : le statut part avec le squelette,
avant que la page sache l'objet introuvable. Il est le même pour toute adresse introuvable,
ce qui compte ici. Chaque état vide — aucun projet, projet sans révision, référentiel
incomplet — se montre sur un exemple nommé du contrat (`empty`, `incomplete`).

Un écran de données de projet lit son contexte par `readAddress` de
`frontend/src/components/context/reading.ts` — projet, révision, filtres actifs, lus une
fois par requête — et le montre par `ContextBanner`, au-dessus de son `<main>`
(WF-IHM-0020). La lecture porte `edits`, les commandes `edit_*` de la révision que
l'appelant peut exercer (`read-only.ts`), qu'un écran reçoit plutôt que de les déduire : une
grille lit sa propre commande — `edits.has("edit_planning")` pour le planning —, car un
chiffreur peut saisir le devis sans toucher au planning. `readOnly` — révision marquée, ou
aucune commande `edit_*` disponible — ne sert qu'à l'avis du bandeau. Une valeur sous
enveloppe `Computable` s'affiche par `ComputedIndicator`, jamais sans la date de son
`CalculationContext` (`indicator.tsx`).

Une commande s'affiche par `Command` de `frontend/src/components/commands/` (WF-IHM-0090) :
absente quand l'objet ne la liste pas dans `available_commands` — le serveur n'y met que
celles que l'appelant a la permission d'exercer, et le front ne sait pas quelle permission
garde quelle commande —, présente et disponible, ou présente et indisponible, marquée
`aria-disabled` et décrite par le texte visible des conditions qui lui manquent
(`enums.CommandCondition.*`). `ProjectCommands` et `RevisionCommands` rendent, dans l'ordre
du serveur, toutes celles d'un projet et d'une révision, chacune selon son `is_available` et
ses conditions — une révision marquée les liste indisponibles, faute d'être en cours
d'élaboration — ; `findOffer` en tire une seule. Hors projet — comptes, rôles, référentiel,
sauvegarde —, `platformOffer` suit la permission de modification d'une fonction de portée
`platform` (`PlatformFunction`) dans `Session.permissions`, ou `platform_restore` pour la
restauration. Griser n'est qu'une
commodité : une commande disponible lance son action serveur, et le refus du serveur est dit
par `OutcomeNotice`.

Une action longue rend la main à la réception de sa tâche de fond (WF-ARC-0090) : son action
serveur passe par `decodeTask` de `frontend/src/api/problem.ts`, qui tient le motif d'un échec
à la règle du catalogue, et l'écran remet la référence au suivi de la coquille par
`useTrackTask()` (`frontend/src/components/tasks/`), avec la commande qui l'a lancée et, s'il
y en a un, le nom que l'utilisateur lui a donné (WF-IHM-0080). Le suivi est commun aux neuf
genres de tâche : il relit la tâche toutes les deux secondes tant qu'elle court, par l'action
serveur `readBackgroundTask`, en montre l'avancement, annonce sa fin dans une région
`aria-live` quel que soit l'écran, et rejoue la commande d'une tâche échouée. Aucun écran ne
suit ses tâches lui-même. Une réponse ne s'applique qu'à la tâche pour laquelle elle a été
demandée, jamais à celle qu'une relance a mise à sa place. Le stockage de session de l'onglet
garde les tâches qui courent pour un rechargement complet, sans leur commande : le contrat n'a
pas de liste des tâches d'un utilisateur (#146). La commande `mark` d'une révision
(`MarkCommand`) en est le premier emploi : elle ouvre, dans la page, la saisie du nom de
version.

L'image de développement (`frontend/Dockerfile`) part d'une image épinglée par son
empreinte, et tourne sous un utilisateur non privilégié, désigné par son numéro.

Le client de l'API est engendré du contrat (PBS-1.2, WF-ARC-0060) : `make generate-client`
écrit ses types dans `frontend/src/api/generated/schema.d.ts`, que personne ne retouche, et
`frontend/src/api/client.ts` en fait des appels typés par openapi-fetch. Une opération qui
manque au client est une modification du contrat, suivie d'un `make generate-client` ; le
fichier engendré se versionne avec elle. Aucun appel réseau ne s'écrit hors de
`frontend/src/api/client.ts`, et seul le serveur Next appelle l'API : un composant client
n'importe de `src/api/` que ses actions serveur (`src/api/actions/`) et des types.

*Contrôles* : `make client-up-to-date` échoue si le client versionné n'est pas celui que le
contrat produit ; une modification du contrat réveille donc la famille front. ESLint refuse
hors de `src/api/client.ts` les moyens connus d'atteindre le réseau — `fetch`,
`XMLHttpRequest`, `WebSocket`, `EventSource`, un client http importé —, et, dans un fichier
`"use client"`, l'import direct de `src/api/` hors des actions serveur, qui s'ouvrent sur
`"use server"` ; `src/api/network-guard.test.ts` l'éprouve sur des extraits piégés, et fige
la liste des dépendances de `package.json`, pour qu'une nouvelle soit examinée pour la
garde avant d'entrer. Le cas transitif — un module sans directive qui importe
`@/api/server`, et qu'un composant client importe — échappe à ESLint : `client.ts` et
`server.ts` importent `server-only`, le filet de `next build`, qu'aucun contrôle ne lance
encore (#131), pas un contrôle de la chaîne. `make typecheck-front`, `make test-front` ;
`make lint-docker` (hadolint).

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
- aucun des moyens connus d'appeler le réseau hors de `src/api/client.ts` — `fetch`,
  `XMLHttpRequest`, `WebSocket`, `EventSource`, ni un client http importé —, et aucun
  import de `src/api/` dans un composant client hors des actions serveur : l'API ne
  s'appelle que par le client engendré, depuis le serveur
  (WF-ARC-0020) ;
- aucun texte destiné à l'utilisateur écrit dans le code (WF-QUA-0070) : voir « Clés de
  traduction » ;
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

- **Ajouter un code côté front** — un code nouveau est d'abord une modification du contrat
  (`ErrorCode`, `docs/api/components/common.yaml`), suivie de `make generate-client`. Le
  front lui donne sa phrase, `errors.<CODE>`, dans les deux catalogues : ce qui est refusé,
  sans rien de ce que les paramètres nomment. Un paramètre nouveau qu'un lecteur doit
  connaître reçoit la sienne, `problemDetails.<param>`, et sa lecture dans `DETAILS` de
  `frontend/src/i18n/problem.ts`, qui nomme une valeur codée — une permission, une
  condition — par son libellé du catalogue ; un paramètre qui ne dit rien à un lecteur —
  un identifiant, un compteur d'écriture — n'en reçoit pas. Un composant rend un refus par
  `problemMessage(problem, { locale, messages })`, jamais en écrivant la phrase.

  *Contrôles* : `make typecheck-front` échoue sur un code d'`ErrorCode` sans clé dans le
  catalogue français, que `problem.ts` lit par `errors.${code}` ; `make catalogs`, sur un
  code sans clé dans l'un des deux, ou sur une clé `errors.` que le contrat n'a plus.
- **Réagir à un refus côté front** — une action serveur ne rend jamais la réponse brute de
  l'API : elle appelle le client par `decode` de `frontend/src/api/problem.ts`, le seul
  décodeur, et rend son `Outcome` — `done` ; `refused`, un `Problem` à dire tel quel ;
  `stale` (412) ; `conflict` (409) ; `signed_out` (401) ; `unreachable`, l'API qui n'a pas
  répondu du tout, distinct de tout `Problem` — le rejet de `fetch` lui-même, que
  `client.ts` marque `Unreachable` (une autre `TypeError` est un défaut et remonte), ou un
  502, 503 ou 504 sans enveloppe `Problem`, qu'une passerelle rend quand le service est
  tombé. Une réponse d'erreur sans enveloppe, ou dont le `code` manque au catalogue — un
  service plus récent que le front —, vaut `INTERNAL_ERROR`, « erreur inattendue », au
  statut reçu : l'écran n'affiche jamais une clé brute. Le composant le dit par
  `OutcomeNotice` (`frontend/src/components/commands/`), en alerte : la phrase de
  `problemMessage` ; sur 412, l'offre de recharger l'écran ; l'objet en conflit
  (`params.conflicting_object_id`) nommé quand l'écran le connaît, par `names` ; sur 401, le
  lien vers la connexion ; l'API injoignable annoncée, jamais un écran blanc. La connexion
  est `/login?next=<chemin et requête de l'écran visé>` (`loginHref`,
  `frontend/src/navigation/login.ts`) : la page de connexion (US-0320), la session rouverte,
  mène à `returnTarget(next)`, qui ne suit qu'un chemin du front — ni `//hôte`, ni une
  adresse d'un autre site — et ramène sinon à l'accueil.

  *Contrôles* : `make test-front` (`problem.test.ts`, `login.test.ts`) ; qu'une action
  serveur passe par `decode`, la revue.
- **Ajouter un code côté service** — *à écrire*, EP-03, qui crée le service.

## Clés de traduction

Les textes de l'interface vivent dans deux catalogues jumeaux, que lit next-intl :
`frontend/messages/fr.json`, la référence, et `frontend/messages/en.json`. La langue
n'apparaît pas dans l'adresse — un lien partagé s'ouvre chez chacun dans la sienne
(WF-INTF-0170) — : le serveur la résout à chaque requête (`frontend/src/i18n/request.ts`),
d'après la préférence du compte si elle vaut `fr` ou `en`, sinon la première langue offerte
que demande `Accept-Language`, sinon la langue par défaut de l'installation
(`getInstallation`). Un `*` placé devant toute langue offerte dans `Accept-Language` laisse
décider l'installation ; une installation illisible ou injoignable donne `fr`, la langue du
catalogue de référence. Sans compte — pas de session, ou une API injoignable — il n'y a pas
de préférence : le navigateur décide, et la coquille n'offre pas le sélecteur de langue.

- **Une clé est hiérarchique, en anglais.** Un texte propre à l'interface se range sous le
  composant ou l'écran qui l'emploie, en camelCase (`languageSelector.label`). Ce que le
  contrat énumère garde ses noms, et chaque valeur a sa clé :
  - `enums.<Schéma>.<valeur>` pour une énumération nommée (`enums.ProjectState.in_progress`),
    `enums.<Schéma>.<propriété>.<valeur>` pour une énumération déclarée dans une propriété
    (`enums.BackgroundTaskRef.status.running`), les `items` d'un tableau ne comptant pas
    (`enums.ReferenceReadiness.missing.active_cost_category`) : toutes les énumérations de
    `components.schemas`, sauf les deux suivantes ;
  - `errors.<CODE>` pour chaque code d'`ErrorCode`, `permissions.<code>` pour chaque
    `PermissionCode` ;
  - `enums.<Paramètre>.<valeur>` pour une énumération d'un paramètre partagé de
    `components.parameters` (`enums.Scope.unassigned`) : son nom partage le niveau des
    schémas, et un paramètre qui énumère des valeurs ne porte pas le nom d'un schéma ;
  - aucune énumération ne s'écrit en ligne, faute d'un nom pour ranger ses clés : celle d'un
    paramètre d'opération devient un paramètre partagé de
    `docs/api/components/parameters.yaml` ; celle d'un corps de requête ou de réponse, ou
    d'un en-tête — sous `paths` comme sous `components.responses`, `requestBodies` et
    `headers` —, un schéma nommé de `components.schemas`. Deux exceptions, sans clé :
    `sort_by`, dont les valeurs sont des colonnes que l'en-tête de la grille libelle déjà, et
    les corps des sondes, `/health` et les chemins qui en partent, qu'aucun écran n'affiche ;
  - un `const` n'a pas de clé : le contrat ne s'en sert que pour l'accord qu'une requête
    donne (`confirmed: true`), qui ne s'affiche pas ;
  - une valeur qui porte un point se lit comme un niveau, next-intl réservant le point au
    chemin : `permissions.users.write`, `enums.ComputedField.task.start_date`.
- **Une valeur est un message ICU** — `{max_columns, plural, one {…} other {…}}` —, avec les
  mêmes arguments dans les deux catalogues, ce que `make catalogs` vérifie ; le libellé d'une valeur d'énumération ou d'une
  permission est du texte sans argument. Le français suit sa typographie : espace insécable
  avant les deux-points, fine insécable avant le point-virgule et les points d'exclamation et
  d'interrogation, apostrophe typographique ; l'anglais suit l'orthographe britannique.
- **Ajouter une clé**, c'est l'écrire dans les deux catalogues, au même endroit, et la lire par
  `useTranslations` — composant client, ou serveur sans `await` — ou par `createTranslator`
  et `requestLanguage()` dans un composant serveur asynchrone. Une valeur ajoutée à une
  énumération du contrat ajoute sa clé dans la même modification.
- **Ce que l'utilisateur a saisi ne se traduit pas** : un libellé de tâche, un nom de projet
  s'affichent tels quels (WF-INTF-0170).
- **Les formats** sont ceux de `frontend/src/i18n/format.ts`, par la langue : un montant, un
  décimal, des heures depuis la chaîne exacte du contrat (`formatMoney`, `formatDecimal`),
  jamais par un flottant ; une date de planning telle quelle, sans fuseau
  (`formatPlanningDate`) ; un horodatage en heure locale du poste, écrit dans le navigateur
  (`LocalTime`) ; un rapport — un avancement — en pourcentage, depuis sa chaîne exacte
  (`formatPercent`). En français, `Intl` sépare les milliers par une fine insécable
  (U+202F) : « 1 234,56 » ne se coupe pas en fin de ligne. L'anglais se formate en anglais
  britannique (`en-GB`), comme ses catalogues s'écrivent : « 31 May 2026, 16:30 », les
  nombres restant « 1,234.56 ».

*Contrôles* : `make typecheck-front` — next-intl est typé par le catalogue français, et une
clé que le code emploie sans qu'il l'ait casse le typage, comme une clé qui manque au
catalogue anglais (`frontend/src/i18n/catalogues.ts`) ; `make lint-front` —
`react/jsx-no-literals` refuse le texte écrit dans le JSX, et `no-restricted-syntax` un
littéral dans un attribut lu — `aria-label`, `aria-description`, `aria-roledescription`,
`aria-valuetext`, `aria-placeholder`, `title`, `alt`, `placeholder` (sauf `blur`, `empty` et
une adresse `data:image/`, les formes de next/image), `label`, la `value` d'un `input`
bouton —, ou dans une branche ou une concaténation d'un enfant ou d'un de ces attributs ;
restent à la revue les autres props de nos propres composants, et une chaîne bâtie par une
fonction ou une méthode (`.join`, `.concat`), dans le JSX ou hors de lui ;
`frontend/src/i18n/text-guard.test.ts` l'éprouve sur des extraits piégés, à côté de la garde
réseau qui partage la règle ; `make catalogs`, dans `check-front`, qui lit le
contrat qu'il vient d'assembler (`wftools.catalogs`) — les deux catalogues ont les mêmes
clés, chaque valeur est un texte non vide, chaque valeur d'énumération, chaque code d'erreur
et chaque permission du contrat a la sienne, et aucune clé sous `enums`, `errors` ou
`permissions` ne survit à la valeur que le contrat a retirée ; un texte emploie les mêmes
arguments ICU que celui du catalogue français, une clé ne s'écrit qu'une fois par fichier, et
aucune énumération ne s'écrit en ligne, hors `sort_by` et les sondes. Il demande au moins
deux catalogues, et nomme chaque clé qui manque et le catalogue qui la porte.

## Charte graphique

La charte vit dans `frontend/src/theme/globals.css`, et nulle part ailleurs : les couleurs,
la typographie, les espacements et les rayons y sont des jetons — des variables CSS que
Tailwind et les composants de shadcn/ui lisent par le thème (`bg-primary`,
`text-muted-foreground`, `rounded-md`). Les bleus viennent des logos de `docs/assets`
(`#027dc6`, `#1195e1`), qui n'atteignent un composant que par des jetons mesurés, les
neutres de shadcn/ui ; la police est Geist, celle du logo.

- **Clair et sombre par les mêmes jetons.** Chaque jeton de couleur porte ses deux valeurs,
  `light-dark(claire, sombre)`. Le document suit le poste (`color-scheme: light dark`) ; quand
  le compte force un mode (`DisplayPreferences.theme`), le layout racine pose
  `data-theme="light"` ou `data-theme="dark"` sur `<html>`, résolu côté serveur comme la
  langue. Aucun composant ne se demande quel mode s'affiche : la variante `dark:` de
  Tailwind, qui ne suivrait que le poste et ignorerait le mode forcé, est refusée. Un état
  qui change de couleur — survol, page courante — a son propre jeton (`--primary-hover`),
  mesuré comme les autres.
- **Ajouter une couleur, c'est ajouter un jeton** : sa valeur claire et sa valeur sombre dans
  `:root`, son nom dans `@theme inline` (`--color-<nom>: var(--<nom>)`), et chaque paire
  texte et fond qu'il forme dans `frontend/src/theme/contrast.test.ts` ; un composant emploie
  ensuite sa classe (`bg-<nom>`). Jamais une couleur dans un composant : ni une classe de la
  palette de Tailwind, retirée du thème — `bg-blue-500` ne produit rien —, ni une valeur
  arbitraire d'un utilitaire de couleur (`bg-[#027dc6]`, `bg-[red]`) — une longueur ou un
  nombre passent, `ring-[3px]` —, ni une variable entre parenthèses (`bg-(--x)`,
  `font-(family-name:--x)`), que personne n'a mesurée, ni une propriété arbitraire qui peint ou une variable
  (`[color:…]`, `[--primary:…]`), ni `color-mix(`, ni une couleur écrite dans une chaîne,
  dans un `style` ou dans l'attribut d'un SVG. Une police s'ajoute de même, par un jeton
  `--font-<nom>`.
- **Le contraste** d'un texte sur son fond atteint 4,5:1, celui de ce qui montre un contrôle —
  bord d'un champ, anneau du focus — 3:1, dans les deux modes (WCAG AA, §3.6).
- **Un signalement passe par `Signal`** (`frontend/src/components/signal/`), et seulement
  par lui (WF-IHM-0070) : il reçoit une `AlertZone` du contrat et la rend par une forme
  Lucide, son libellé du catalogue (`enums.AlertZone.<zone>`) et son jeton,
  `--signal-<zone>`, dans une seule table typée sur `AlertZone`. **Une zone vient du
  serveur**, qui classe selon les seuils du référentiel : le front n'en déduit jamais une
  d'une valeur (WF-ARC-0020). Une zone nulle ou absente ne rend aucun `Signal` ; la valeur
  dit qu'elle manque (`ComputedIndicator`) ; jamais `?? "nominal"`. Un signalement que le
  contrat ne classe pas encore attend sa zone (#139). Les jetons de signalement sont mesurés
  comme les autres, et de plus en niveaux de gris et vus d'un protanope et d'un deutéranope
  (`contrast.test.ts`). Hors de `src/components/signal/`, un utilitaire de couleur qui nomme
  un jeton de zone (`bg-signal-alert`, `text-signal-watch`) est refusé : `SIGNAL_SYNTAX` de
  `frontend/eslint.config.mjs`, `make lint-front`, éprouvé par `colour-guard.test.ts`.
  Qu'aucun écran ne distingue deux états par la seule couleur — une pastille, une ligne
  teintée sans forme ni texte —, c'est pour le reste la revue qui le tient ; les tests de
  `Signal` le prouvent pour le composant.
- **shadcn/ui** : un composant s'ajoute en copiant son source dans
  `frontend/src/components/ui/` (`frontend/components.json` en donne les chemins), et seulement
  quand un écran l'emploie. Copié, il est du code du dépôt, soumis à toutes ses règles :
  en-tête, lint, JSDoc, couverture, textes par le catalogue. Les icônes sont celles de Lucide
  (`lucide-react`) ; une icône seule porte un nom, une icône à côté de son texte est
  `aria-hidden`.
- **Le logo et le favicon** sont les fichiers de `docs/assets`, copiés à l'octet près dans
  `frontend/public/` et `frontend/src/app/icon.svg` ; le logo prend sa variante sombre là où
  le mode sombre s'applique.

*Contrôles* : `make lint-front` — `no-restricted-syntax` (`COLOUR_SYNTAX` de
`frontend/eslint.config.mjs`) refuse, dans toute chaîne du code, une classe de couleur de la
palette, une valeur arbitraire d'un utilitaire de couleur qui n'est ni une longueur ni un
nombre, une variable passée à un utilitaire de couleur ou de police, une police arbitraire, une propriété arbitraire qui peint, pose une police ou une
variable, `color-mix(`, une couleur écrite en chaîne entière et la variante `dark:` ; dans un
`style`, quelle que soit sa valeur, une propriété qui peint, borde, ombre ou pose une police,
et une variable, que la clé soit un nom ou une chaîne ; et, pour `fill`, `stroke`, `color` et
les couleurs d'un SVG, tout littéral ou gabarit sans expression autre que `currentColor`,
`none` ou `url(…)`, où qu'il soit dans la valeur, une branche comprise.
`frontend/src/theme/colour-guard.test.ts` l'éprouve sur des extraits piégés, et vérifie
qu'aucune feuille de style ne vit hors de `src/theme/`. `make test-front` —
`contrast.test.ts` mesure chaque paire de jetons dans les deux modes, `brand.test.ts`
compare les logos et l'icône à ceux de `docs/assets`. Le contraste des écrans rendus se
contrôle dans le navigateur (US-0200) ; le reste de l'accessibilité d'un composant, dans ses
tests, par `expectAccessible` (`frontend/src/test/axe.ts`, axe-core sous happy-dom, qui ne
calcule pas les couleurs). Reste à la revue : une couleur bâtie par un gabarit à expressions
ou par une fonction, et un `style` ou un attribut de SVG qui reçoit une variable plutôt qu'un
objet ou un littéral écrit sur place.

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

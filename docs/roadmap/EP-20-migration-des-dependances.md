---
id: EP-20
titre: Porter la plateforme, ses environnements d'exécution et ses dépendances à leurs dernières versions stables, et en tenir la veille
statut: en cours
depend_de: EP-19
famille: plateforme
issue: 1925
---

# EP-20 — Migration des dépendances

## Objet

Le bilan des versions du 2026-11-03 trouve la plateforme en retard d'une ou deux majeures sur
presque tout : PostgreSQL 16 (18.6 est stable), Redis 7.4 (8.10), Python 3.13 (3.15), Node 24
(26 LTS), pnpm 11 (12), ESLint 9 (10), l'outil de construction de l'extension de Keycloak sur un
JDK 21, et une vingtaine de bibliothèques du back et du front. L'annuaire de test que Keycloak
fédère, `osixia/openldap` 1.5.0, n'est plus maintenu depuis 2021. Le poste de l'auteur a déjà le
client PostgreSQL 18 : les tests des restaurations y échouent contre le serveur 16 de la plateforme
(#982). Et rien ne dit qu'une version a bougé, sauf pour les Actions. EP-20 rattrape ce retard d'un
bloc, avant que les EPIC de domaine n'empilent du code sur ces versions, puis en rend la veille
régulière. Redis 8 est aussi un choix de licence : il se distribue sous l'AGPLv3, la licence du
projet, là où Redis 7.4 n'offre que la RSAL et la SSPL.

Il vient après EP-19, qui réécrit le Makefile et ajoute le Compose des services de test, tous deux
épinglés sur les versions qu'EP-20 monte. Il vient avant EP-05, qui en dépend : le référentiel est
le premier EPIC de domaine, et il se construit sur les versions cibles (décision de l'auteur du
2026-11-03). Les US n'ont pas d'acteur du §3.1.3. Leur bénéficiaire est celui qui développe ou qui
exploite.

## Ce qui en fait partie

- PostgreSQL 18 sur toutes les plateformes, de production, de service, des services de test et de
  la chaîne, avec le client `pg_dump`/`pg_restore` de l'image `waterfall` à la même majeure ; la
  sauvegarde et la restauration au vert sur cette version ;
- la rupture de cette montée, écrite et tenue : une plateforme ne reprend pas un volume
  PostgreSQL 16, elle refuse de démarrer en le disant (décision de l'auteur du 2026-11-03) ;
- Redis 8, Garage v2.5, Mailpit v1.33 ;
- un annuaire de test maintenu, OpenLDAP construit par le dépôt sur Debian, à la place
  d'`osixia/openldap` ;
- Python 3.14, celui d'Ubuntu 26.04, uv 0.13 et la borne d'`uv_build`, les bibliothèques du back
  et des outils ;
- les runners de la chaîne sur Ubuntu 26.04, et pandoc à sa dernière version, la projection de la
  spécification régénérée ;
- Node 26, pnpm 12, ESLint 10 et les bibliothèques du front, Redocly CLI ;
- l'image de construction de l'extension de Keycloak sur Maven 3.10 et un JDK 25, et ses
  bibliothèques de test et greffons ;
- les quatre épinglages des Actions en retard d'un patch ;
- la veille : Dependabot étendu à tous les écosystèmes du dépôt ;
- le faux back qui cherche comme le service : sa table d'`unaccent` est celle de PostgreSQL 18.6, que
  la montée a changée sous lui (#1960, option 1 retenue par l'auteur le 2026-11-05) ;
- la documentation d'installation d'un poste neuf : `INSTALL.md`, `README-fr.md`, `README.md` et
  `CONTRIBUTING.md` relus en entier, et les six points que la mise au point du poste de l'auteur a
  relevés (constat du 2026-11-05 sur #1925).

## Ce qui n'en fait pas partie

- la reprise des données d'une plateforme PostgreSQL 16 : on repart de zéro (décision de l'auteur
  du 2026-11-03). Ni `pg_upgrade` outillé, ni garantie qu'une sauvegarde prise sur la 16 se
  restaure sur la 18 ;
- TypeScript 7 : `typescript-eslint`, dans sa dernière version (8.72.1), déclare
  `typescript >=4.8.4 <6.1.0`, et le lint typé du front ne tiendrait plus. Le front reste en 6.0,
  au dernier patch, et la veille dira quand la paire le permettra (décision de l'auteur du
  2026-11-03) ;
- Java 25 comme cible de l'extension : Keycloak 26.8.1 s'exécute sur OpenJDK 21, et une classe
  compilée pour 25 ne s'y chargerait pas. L'extension se compile avec un JDK 25, en
  `release 21`, et suivra Keycloak (décision de l'auteur du 2026-11-03). `jakarta.ws.rs-api`,
  fourni par Keycloak, le suit aussi ;
- PostgreSQL 19, encore en version candidate ;
- Python 3.15 : le `python3` d'Ubuntu 26.04, du poste comme des runners, est en 3.14, et le garde
  des commandes et `slots.py` d'EP-19 tournent par lui, sans uv. Le dépôt cible la même version
  que lui (décision de l'auteur du 2026-11-03, qui revient sur celle de 3.15 prise le même jour) ;
- les minima de WF-CMP-0020 (PostgreSQL ≥ 15, Redis ≥ 7), qu'EP-20 ne change pas : un constat de
  spécification les propose à PostgreSQL 18 et Redis 8, à trancher par l'auteur, et EP-13 clôt
  l'exigence ;
- #1291 (`braces` tiré par `eslint-config-next`) et #1512 (Next 16.5) : ils restent à EP-13. La
  dernière `eslint-config-next` tire encore `braces` 3.0.3, et le bilan ne monte pas Next en 16.5 ;
- l'essai de la documentation d'installation sur un poste neuf : la preuve d'US-1260 est la
  relecture, contre le Makefile, les workflows et les Dockerfiles qui font foi (décision de l'auteur
  du 2026-11-05) ;
- les composants déjà à jour : Keycloak 26.8.1, keycloak-config-cli 6.5.1-26.5.5, Caddy 2.11.7,
  curl 8.23.0, Prism 5.16.0, l'image de Playwright v1.64.1.

## Exigences réalisées

Aucune : EP-20 monte les versions de ce qui porte les exigences, sans en réaliser une, comme EP-19
pour l'outillage du dépôt. Ses US portent « aucune — plateforme » ou « aucune — outil du dépôt »,
et leurs critères sont propres à l'US. Les exigences déjà closes restent prouvées : c'est ce que
disent la définition de fini et les critères de non-régression de chaque US.

## Opérations du contrat

Aucune.

## Préalables

EP-19 livré : `epic/EP-20` se tire de `main` après sa fusion, pour monter les épinglages du
Compose des services de test et du Makefile qu'EP-19 écrit.

## Définition de fini

- `make check BASE=origin/main` passe sur `epic/EP-20`, ainsi que `make roadmap` et
  `make readmes`, et la chaîne est au vert sur sa pull request vers `main`, `production`,
  `keycloak`, `service` et `e2e` compris ;
- `make production-trial`, avec `WATERFALL_TRIAL_RESTORATION=1`, sauvegarde et restaure une
  plateforme PostgreSQL 18 ;
- sur le poste de l'auteur, client PostgreSQL 18, les tests des restaurations passent ;
- `make service-up` sur un volume PostgreSQL 16 refuse de démarrer, en disant
  `make service-down WATERFALL_RESET_DATA=yes` ;
- aucun fichier du dépôt n'épingle plus une version que le bilan dit en retard, hors celles que
  « Ce qui n'en fait pas partie » nomme ;
- `.github/dependabot.yml` couvre les écosystèmes du dépôt ;
- la chaîne tourne sur Ubuntu 26.04, et `make check-spec` passe sur le poste avec le pandoc que
  la chaîne épingle ;
- le faux back cherche comme le service : sa table d'`unaccent` est comparée à celle d'un
  PostgreSQL 18 sur chaque point de code Unicode, sans différence (US-1250) ;
- `INSTALL.md`, les README de la racine et `CONTRIBUTING.md` ne disent plus une étape, un ordre ou
  une version que le Makefile, les workflows et les Dockerfiles démentent (US-1260).

## Constats reçus

Aucun.

## Conception

### Ce qui change, et ce qui ne change pas

Aucune table, aucune migration, aucun module du noyau, aucune opération du contrat. Ce qui
change, ce sont des épinglages : images des Compose, des Dockerfiles et des workflows, verrous
`uv.lock` et `pnpm-lock.yaml`, `pom.xml`, `.python-version`, `pyproject.toml`, `ruff.toml`,
`package.json`, le Makefile. Le code ne change que là où une nouvelle version l'exige : une API
retirée, une règle de lint renommée, un avertissement devenu erreur. Deux pièces sont neuves :
le contrôle du volume de PostgreSQL (US-1130) et l'image de l'annuaire de test (US-1150).

**La règle des versions** : celles du bilan du 2026-11-03 sont des planchers. Un lot prend la
dernière version corrective de la série que vise son US, au jour où il se livre, et la pull request
dit laquelle. Toute image est épinglée par l'empreinte de son index multi-architecture, comme
aujourd'hui. Les épinglages qui se répètent — PostgreSQL dans `compose.prod.yaml`,
`compose.service.yaml`, `compose.test.yaml` et `back.yml` ; Redis et Garage de même ; Node — sont
changés ensemble, et le lot vérifie, par une recherche dans le dépôt, qu'aucune ancienne empreinte
ne subsiste.

### PostgreSQL 18 (US-1130)

- **L'image** : `postgres:18-trixie`, Debian 13 comme l'image `waterfall`, à la place de
  `postgres:16-bookworm`.
- **Le montage** : l'image 18 range ses données dans `/var/lib/postgresql/18/docker` et attend
  son volume sur `/var/lib/postgresql`. Elle refuse d'elle-même un volume de la 16, à l'ancien
  chemin comme au nouveau (code 1, éprouvé le 2026-11-03 sur un volume 16 qui portait une table) :
  son message renvoie à `pg_upgrade`, qu'EP-20 n'outille pas. Le volume `postgres-data` garde son nom et se monte
  sur `/var/lib/postgresql` dans `compose.prod.yaml` et `compose.service.yaml`. Le `tmpfs` de
  `compose.test.yaml` se monte au même chemin. Les services de `back.yml` gardent le chemin par
  défaut de l'image.
- **Le contrôle du volume** : un script `deploy/compose/postgres-volume.sh`, en POSIX `sh`,
  qu'exécute un service ponctuel `postgres-volume`. Ce service prend l'image de PostgreSQL de la
  plateforme et monte `postgres-data` en lecture seule sur `/var/lib/postgresql`. `postgres`
  en dépend (`service_completed_successfully`), dans `compose.prod.yaml` comme dans
  `compose.service.yaml`. Il a deux raisons, puisque l'image refuse déjà un volume 16 : son
  message dit notre remède, et non `pg_upgrade` ; et il couvre la montée suivante, où une image 19
  trouverait `18/docker` et créerait en silence un `19/docker` vide à côté. Le script refuse
  (code 1) dans deux cas :
  - un `PG_VERSION` à la racine du volume, la disposition des images 17 et antérieures ;
  - un `<n>/docker/PG_VERSION` dont `n` n'est pas 18.

  Son message nomme la version trouvée, lue dans `PG_VERSION`, la version attendue, 18, et le
  remède, qu'il reçoit en argument du Compose. En production, le remède renvoie à « Mettre à jour »
  de `deploy/compose/README.md` ; en service, c'est `make service-down WATERFALL_RESET_DATA=yes`.
  Un volume vide ou en 18 passe sans rien dire. Les tests des outils exécutent le script sur un
  répertoire temporaire, dans ces quatre cas. `make service-up`, en échec, affiche le journal de
  `postgres-volume`.
- **Le contrôle de santé** : `pg_isready` passe par `--host 127.0.0.1` partout où il figure
  (`compose.prod.yaml`, `compose.service.yaml`, `compose.test.yaml`, `back.yml`). Sans hôte, il
  interroge le socket Unix, sur lequel le serveur provisoire de la première initialisation répond
  avant de s'arrêter pour redémarrer : la base était dite prête pendant son initialisation, et un
  service ponctuel qui la joignait trouvait le serveur fermé (constaté le 2026-11-03 sur le nouveau
  poste, au premier `make test-keycloak`). Ce défaut ne se voit qu'au premier démarrage d'un volume
  neuf, que la rupture impose à toutes les plateformes. Le serveur provisoire n'écoute pas sur TCP :
  l'hôte suffit.
- **Le client** : `postgresql-client-18=18.*`, du dépôt PGDG, dans `backend/Dockerfile`, dont le
  commentaire garde la raison (#982) avec la nouvelle majeure.
- **Les vidages** : `worker/backup.py` et `worker/restore.py` ne changent pas, sauf si
  `pg_dump` 18 change ce que contient un vidage au format `custom` ; le lot le vérifie par les
  tests des sauvegardes et des restaurations, et par `make production-trial` avec
  `WATERFALL_TRIAL_RESTORATION=1`.
- **La rupture** : `deploy/compose/README.md`, « Mettre à jour », reçoit un paragraphe qui nomme la
  version de Waterfall qui passe à PostgreSQL 18 et Redis 8. Cette version ne reprend pas les
  données d'avant : on retire la plateforme avec ses volumes (`down --volumes`), puis on la
  réinstalle et on l'amorce. Si on l'oublie, PostgreSQL refuse de démarrer. Le guide
  (« Un test contre PostgreSQL », « Un test contre le stockage objet ») et `INSTALL.md` disent le
  client 18 du poste, et la phrase d'EP-19 sur les restaurations qui échouent est retirée.

### Redis 8, Garage v2.5, Mailpit v1.33 (US-1140)

- `redis:8-alpine` à la place de `redis:7-alpine`, avec la même commande (`--requirepass`,
  `--save ''`). Rien ne se reprend : Redis tourne sans persistance (#956, EP-13).
- `dxflrs/garage:v2.5.x` : `garage.toml` et `storage-buckets.sh` ne changent que si les notes de
  version de Garage l'exigent.
- `axllent/mailpit:v1.33.x` dans `compose.service.yaml`.
- La licence : `deploy/compose/README.md`, où l'exploitant lit ce qu'il fait tourner, dit que
  Redis 8 est employé sous l'AGPLv3. Le dépôt ne redistribue pas Redis, et `REUSE.toml` ne porte
  que la licence des fichiers du dépôt.

### L'annuaire de test (US-1150)

- **L'image** : construite par le dépôt, `deploy/openldap/Dockerfile`, sur `debian:trixie-slim`
  épinglée par empreinte, avec `slapd` et `ldap-utils` de Debian, épinglés à leur série
  (`=2.6.*`) comme le client PostgreSQL de l'image `waterfall`. Les images officielles de 389
  Directory Server sont arrêtées depuis juin 2025, et celle d'`osixia` depuis 2021 : la base
  Debian est rafraîchie chaque mois, Dependabot la suit (US-1190), et Debian suit la sécurité de
  `slapd`. L'image s'appelle `waterfall-openldap`, et suit la règle des créneaux d'EP-19, comme
  celle de Keycloak (`-s<i>` au créneau i ≥ 1).
- **Le premier démarrage** : un script d'entrée, `deploy/openldap/entrypoint.sh`, en POSIX `sh`.
  Si la configuration est vide, il la crée par `slapadd -n0` : le schéma `core`, `cosine` et
  `inetorgperson`, une base `mdb` de suffixe `dc=waterfall,dc=test`, l'administrateur
  `cn=admin,dc=waterfall,dc=test`, dont le mot de passe, une valeur de développement visible
  comme aujourd'hui, vient de l'environnement. Il charge ensuite
  `deploy/keycloak/development/directory.ldif` par `slapadd -n1`, qui reçoit l'entrée du suffixe,
  que l'image d'`osixia` créait d'elle-même. Enfin il lance `slapd` au premier plan, sur
  `ldap:///` sans TLS, sous l'utilisateur `openldap`. Les démarrages suivants trouvent la
  configuration et ne chargent rien.
- **Le service** : il garde son nom, `openldap`, son port, 389, et ses volumes, `openldap-data` et
  `openldap-config`. Ses données survivent au conteneur pour la même raison qu'aujourd'hui :
  réamorcé, l'annuaire donnerait à la personne un autre `entryUUID`, et Keycloak un autre compte.
  Il gagne un contrôle de santé, une recherche anonyme sur la racine.
- **Le royaume** : rien ne change. `ldap://openldap:389`, `cn=admin,dc=waterfall,dc=test`, le
  fournisseur `other`, l'identifiant `entryUUID`, que `slapd` fournit nativement, et les
  correspondances de #667.
- **Ce qui le nomme** : `compose.service.yaml` (`build:` au lieu de l'image d'`osixia`), le guide
  et `INSTALL.md`. Le Makefile, `keycloak.yml` et les tests des outils qui disent que la
  production n'a pas d'annuaire de test (`test_production.py`, `test_images.py`) ne changent pas.
  `make lint-docker` et `make lint-shell` éprouvent les deux nouveaux fichiers.

### Python 3.14 (US-1160)

- **L'interpréteur** : `backend/.python-version` et `tools/.python-version` disent 3.14. Dans les
  deux `pyproject.toml`, `requires-python` devient `>=3.14` et `pythonVersion` de pyright `3.14`.
  `ruff.toml` cible `py314`. L'image `waterfall` part de `python:3.14-slim-trixie`. Dans la
  chaîne, `setup-uv` prend la version de `.python-version`.
- **Le `python3` du système** : le garde des commandes et `slots.py` (EP-19) tournent par lui,
  sans uv. Après US-1200, c'est 3.14 sur le poste comme sur les runners, la version que cible
  ruff : aucune cible à part. Un test des outils vérifie que ces deux scripts se compilent avec
  l'interpréteur du système qui les lance.
- **uv** : `uv==0.13.x` dans `backend/Dockerfile` ; `uv_build>=0.13.<x>,<0.14.0` dans les deux
  `pyproject.toml`, la même série que l'uv de l'image.
- **Les bibliothèques** : `uv lock --upgrade` dans le back et dans les outils, puis les planchers
  du bilan relevés dans `pyproject.toml` là où une borne les retient. Le lot lit les notes de
  version des dix-neuf mineures de fastapi et de starlette 1.10 : c'est là qu'est le risque de
  comportement, et la pull request dit ce qu'il en a retenu. Le relevé du 2026-11-03 en nomme
  quatre, à éprouver en premier :
  - la 0.151, qui distingue un `null` JSON d'un champ omis dans un corps : le back s'y appuie
    (`model_fields_set`, `exclude_unset`, dans neuf modules de `api/`), et le contrat aussi (une
    écriture n'exige que `lock_version`, DECISIONS.md) ;
  - la 0.148 et la 0.160, qui changent les valeurs par défaut des paramètres et la configuration
    `extra` des modèles de paramètres ;
  - la 0.155, qui retire les `**extra` de `Query`, `Path`, `Body` et des autres, et lève désormais
    `TypeError` ;
  - la 0.145 et la 0.146, qui retirent `openapi_prefix` et rendent `root_path` obsolète ; le back
    n'emploie ni l'un ni l'autre.

  Les formulaires (0.147, 0.149, 0.150, 0.162) ne le touchent pas : il n'en reçoit aucun.
  Trois dépendances indirectes restent sous leur dernière version, retenues par celles qui les
  tirent : `python-dateutil` 2.9 par botocore (`<3.0.0`), `isort` 8 par
  datamodel-code-generator, `openapi-schema-validator` 0.8 par openapi-core. Le lot ne les force
  pas.
- **Le code engendré** : `make generate-client`, puis la régénération des modèles par
  datamodel-code-generator 0.88. Un écart de pure forme passe : ordre, mise en page, commentaires.
  Un écart qui change la forme d'un modèle — son type Python, sa structure, le moteur qui valide
  ses motifs — est un constat que l'auteur tranche, même s'il ne vient que du générateur. L'essai
  du 2026-11-03 en a trouvé un : la 0.88 met à plat l'`allOf` de `Money` et d'`IndexThreshold`.
  Ces deux modèles passent d'une enveloppe de la classe engendrée `Decimal` à une chaîne qui
  cumule les deux motifs, validée par le moteur de Python (`regex_engine="python-re"`) et non
  plus par celui de pydantic. Rien ne change sur le fil, et aucun code du back ne les emploie
  encore, mais EP-05 les emploiera (taux, seuils), et des lectures en masse paieraient le moteur
  plus lent. Le lot ouvre le constat avec une mesure sur le volume des 6 000 nœuds, et ne
  régénère pas les modèles avant la décision.
- **Les roues** : toutes les bibliothèques compilées du back et des outils, pyyaml compris, en ont
  une pour 3.14.

### Node 26 et le front (US-1170)

- **Node** : `node:26-alpine`, épinglé, dans `frontend/Dockerfile`, `deploy/compose/mock.Dockerfile`
  et `compose.dev.yaml` ; `node-version: 26` dans les sept appels de `setup-node` ;
  `engines.node` `>=26` ; `@types/node` `^26`.
- **corepack se retire** : Node 26 ne le livre plus. pnpm n'en a plus besoin : lancé dans un
  projet, il prend lui-même la version de `packageManager`. Constaté le 2026-11-03 : un pnpm
  12.16.1 lancé dans un projet épinglé en 11.27.1 répond 11.27.1. `packageManager` reste la seule
  version qui compte. Un pnpm de départ suffit, et sa version importe peu (décision de l'auteur
  du 2026-11-03) :
  - dans l'étape `development` de `frontend/Dockerfile`, `package.json` est copié d'abord, puis
    `npm install --global pnpm@<version>`, la version lue dans `package.json` par `node` : aucune
    copie de la version ;
  - dans la chaîne, les sept `corepack enable pnpm` deviennent `pnpm/action-setup`, épinglé par
    empreinte de commit, sans `version`, avec `package_json_file: frontend/package.json` : il lit
    `packageManager`. Il passe avant `setup-node`, dont le cache de pnpm a besoin ;
  - sur le poste, `npm install --global pnpm`, une fois, comme le disent `INSTALL.md` et
    `CONTRIBUTING.md` ;
  - le Makefile perd `COREPACK_ENABLE_DOWNLOAD_PROMPT` (`PNPM_ENV`), et `make check-tools`
    cherche `pnpm` au lieu de `corepack`. `mock.Dockerfile` et `compose.dev.yaml` n'emploient pas
    corepack.
- **pnpm** : `packageManager: pnpm@12.x`. Un changement du format de `pnpm-lock.yaml` est du code
  engendré.
- **Le lint** : ESLint 10 et `@eslint/js` 10 ; `eslint-plugin-jsdoc` 65 ; `typescript-eslint`, à sa
  dernière version, tient ESLint 10. La configuration plate reste la même ; une règle retirée ou
  renommée prend sa remplaçante, et la pull request la nomme. Ce que la configuration refuse ne
  diminue pas.
- **Les bibliothèques** : `pnpm update` dans les bornes, puis les planchers du bilan relevés dans
  `package.json`. `axe-core` reste épinglé exactement. L'essai du 2026-11-03 a monté tout le front
  dans un worktree jetable : pnpm 12 réécrit le verrou de pnpm 11 sans erreur ; ESLint 10 ne relève
  que deux constats, de sa règle `no-useless-assignment`, chacun d'une ligne ; types, catalogues et
  construction passent ; et les 4 495 tests passent tant que `@tanstack/virtual-core` reste en
  3.17.11. Un paquet trop récent peut ne pas être proposé par pnpm le jour même : le lot le prend
  à la version que pnpm retient, et la pull request le dit.
- **`@tanstack/virtual-core` (US-1170/L3)** : il porte la fenêtre des lignes de toutes les grilles
  (`row-window.ts`). En 3.19.10, 664 tests du front échouent : les lignes ne sont plus rendues
  sous jsdom. La piste est la 3.19.6, qui mesure la fenêtre de défilement par ses dimensions client
  (`clientHeight`, `clientWidth`), que jsdom laisse à 0, là où le banc de test simule
  `offsetHeight` et `offsetWidth` (`src/test/choice-menu.tsx`, et des fichiers qui simulent les
  tailles à leur façon). Simuler aussi les dimensions client dans le banc commun ne ramène les
  échecs qu'à 626. Le lot établit la cause, adapte le banc de test au même endroit pour tous, sans
  affaiblir un attendu, et prouve par les parcours de bout en bout, joués dans un navigateur, que
  les grilles se comportent comme avant : défilement, lignes rendues, saisie, collage. S'il ne
  peut pas le prouver, la version reste en 3.17.11 : le lot ouvre le constat, et l'US se ferme
  sur ce critère. TypeScript
  reste `~6.0`, au dernier patch.
- **Redocly** : `REDOCLY_VERSION := 2.72.x` dans le Makefile ; le contrat ne change pas.

### L'extension de Keycloak (US-1180)

- `deploy/keycloak/Dockerfile` : l'étape `extension` part de `maven:3.10.0-eclipse-temurin-25`,
  épinglé.
- `pom.xml` : `maven.compiler.release` reste 21, avec un commentaire qui le lie au Java de l'image
  de Keycloak, 21 pour 26.8.1. junit-jupiter passe en 6.x, maven-compiler-plugin en 3.16,
  surefire en 3.6.1 et jar en 3.5.1, au moins. Les versions des dépendances de Keycloak et de
  `jakarta.ws.rs-api` ne changent pas.
- La preuve que Keycloak charge l'extension : `make test-keycloak`.

### La veille (US-1190)

- Les quatre épinglages des Actions passent à leur dernier patch, par empreinte de commit, le
  commentaire de version à côté.
- `.github/dependabot.yml` : chaque mois, avec le même préfixe de message `Chaîne :`, six écosystèmes :
  - `github-actions` (`/`, celle d'aujourd'hui) ;
  - `uv` (`/backend`, `/tools`) ;
  - `npm` (`/frontend`) ;
  - `maven` (`/deploy/keycloak/extension`) ;
  - `docker` (`/backend`, `/frontend`, `/deploy/keycloak`, `/deploy/openldap`, `/deploy/compose`) ;
  - `docker-compose` (`/deploy/compose`).

  Dans chaque entrée, un groupe réunit les mineures et les correctifs ; une majeure vient seule.
  Pour Maven, les dépendances `org.keycloak` et `jakarta.ws.rs-api` sont ignorées : elles suivent
  l'image de Keycloak, qui vient par l'entrée `docker`. TypeScript n'a pas de règle d'ignorance : la
  pull request de la majeure 7 arrive, et l'auteur la ferme tant que `typescript-eslint` ne la
  tient pas.
- Le guide, « La chaîne », dit ce que Dependabot ne suit pas — `REDOCLY_VERSION` et `PRISM_VERSION`
  du Makefile, `packageManager`, l'uv et le client PostgreSQL de l'image
  `waterfall`, les runners et le pandoc de la chaîne —, et que leur relève se fait à la main, à
  la pull request mensuelle de Dependabot.

### Les runners et pandoc (US-1200)

- **Les runners** : les vingt `runs-on: ubuntu-24.04` passent à `ubuntu-26.04`. Le runner apporte
  `python3` 3.14 (le garde, `slots.py`) et `pg_dump`/`pg_restore` 18 du système, avec lesquels les
  tests du back sauvegardent et restaurent. Ce client 18 ne restaure pas sur un serveur 16 (#982) :
  US-1200 vient donc après US-1130, et avant US-1160, dont la cible `py314` demande un `python3`
  3.14 dans la chaîne.
- **pandoc** : `PANDOC_VERSION` et `PANDOC_SHA256` de `spec.yml`, la version qu'attend
  `make check-tools`, `INSTALL.md`, `README-fr.md`, `README.md` et `CONTRIBUTING.md` passent à la
  dernière version publiée, celle d'Ubuntu 26.04 au moins. Le lot régénère la projection
  (`make build-doc`) sans toucher au document source : c'est du code engendré. La revue vérifie
  que l'écart est de forme seulement — aucune exigence, aucun champ Vérif, aucun identifiant ne
  change —, et `make roadmap` comme `make inventory` le confirment. C'est la seule écriture d'EP-20
  dans `docs/spec`, et elle se fait sur l'accord de l'auteur (2026-11-03).
- **Ce qui ne change pas** : les images des travaux (Playwright) et les services gardent leurs
  épinglages ; un travail qui suppose un outil du runner 24.04 absent du 26.04 l'installe, et la
  pull request le nomme.

### Le faux back et la table d'`unaccent` de la 18 (US-1250)

Aucune table, aucune migration, aucune opération du contrat. Trois pièces changent dans `tools/` :
`wftools/unaccent.rules`, le lecteur `Unaccent.read` de `wftools/mocktext.py`, et
`tests/test_mocktext.py` ; une seule du contrat : le texte de `docs/api/DECISIONS.md`. Le tableau de
`docs/api/README-fr.md` et son pendant anglais disent « sa table livrée » sans version : ils ne
changent pas.

- **La table.** Le fichier `/usr/share/postgresql/18/tsearch_data/unaccent.rules` de l'image
  `postgres` que la plateforme épingle au jour du lot (`compose.service.yaml`), tiré par
  `docker run --rm --entrypoint cat <image> <chemin>`. Toutes les lignes après l'en-tête sont celles
  de l'image, inchangées. L'en-tête garde les deux lignes SPDX, la licence PostgreSQL et le paragraphe
  de permission de la copie 16 ; il dit la version (18.6 au cadrage), le chemin, et l'image par son
  empreinte. La licence est déjà dans `LICENSES/PostgreSQL.txt`.
- **Le lecteur.** Il lit le format de la 18 : champs séparés par des blancs, un champ pouvant être
  entre guillemets doubles, qui gardent ses blancs, `""` y valant un guillemet (relevé sur l'image :
  `" 1/4"` se lit ` 1/4`, `""""` se lit `"`). Une source seule reste une suppression, et une ligne qui
  garde plus de deux champs une fois les guillemets lus reste refusée. Le lot lit la règle exacte dans
  les sources de la 18 (`contrib/unaccent`) et la fait confirmer par la comparaison ci-dessous, non
  par cette conception.
- **La comparaison.** Une seule fois, par le lot : un PostgreSQL 18 des services de test
  (`make test-services`), l'extension créée, `unaccent` demandé pour chaque point de code Unicode hors
  substituts, puis `lower(unaccent(…))` pour chaque texte des exemples ; le faux back doit rendre les
  mêmes chaînes. La pull request donne les nombres et `DECISIONS.md` le fait, comme pour la 16. Aucun
  test permanent : les tests des outils n'ont pas de PostgreSQL, et en ajouter un pour une table
  figée coûterait plus qu'il ne protège.
- **Le contrat.** `DECISIONS.md`, « Une recherche translittère comme `unaccent`, puis met en
  minuscules » : la copie est celle de la 18, la comparaison a été faite contre la 18, et la phrase
  sur « ¼ » dit ` 1/4`. Elle prend la forme « Reformulé par EP-20/US-1250 » que le fichier emploie
  déjà. Cette modification est faite sur la branche de l'EPIC, avec le code qui la fait vivre.

### La documentation d'un poste neuf (US-1260)

Aucune table, aucun code, aucune opération du contrat. Cinq fichiers : `INSTALL.md`, `README-fr.md`,
`README.md` et `CONTRIBUTING.md`, plus `docs/dev/agents.md` ; le guide ne change pas. `make roadmap`
lit `docs/dev/*.md` : toute commande `make` que le lot y cite existe au Makefile.

- **L'ordre d'`INSTALL.md`.** Le poste se monte dans l'ordre où il le demande : les prérequis (avec
  `openssl`, et la source de pandoc), puis un temps « Le shell », puis « Une seule fois ». Le temps
  « Le shell » dit le `~/.bashrc` tel qu'il doit être, de haut en bas : le bloc du `PATH` (pnpm, Node
  de nvm), la ligne qui charge le fichier des secrets, `WATERFALL_SLOTS`, puis la garde `case $- in`
  d'Ubuntu. Tout ce qui doit se lire dans un shell non interactif précède la garde, et c'est la seule
  règle que ce temps énonce, avec la panne qu'elle évite (`pnpm: not found`). Les étapes de la
  plateforme de service gardent leur ordre.
- **Les secrets.** Le fichier est `~/.config/waterfall/service.env`, en mode 600, de lignes
  `export NOM=valeur`. `INSTALL.md` donne une commande qui l'engendre depuis le bloc `env` de
  `.github/workflows/keycloak.yml` : les valeurs ne sont écrites que là. Le lot éprouve la commande
  dans un répertoire temporaire et vérifie qu'elle rend les onze variables que lit le tableau de
  « Commandes » du guide. L'auteur a éprouvé la disposition sur son poste : `make service-up`
  démarre, `make check-keycloak` passe (133 tests).
- **`mmdc` et AppArmor.** Installation par npm
  (`npm install -g --allow-scripts=puppeteer @mermaid-js/mermaid-cli`). Sur Ubuntu 23.10 et plus, si
  `kernel.apparmor_restrict_unprivileged_userns` vaut 1, le profil ci-dessous va dans
  `/etc/apparmor.d/puppeteer-chrome`, puis `sudo apparmor_parser -r /etc/apparmor.d/puppeteer-chrome`.
  Texte éprouvé par l'auteur (`mmdc` rend alors un diagramme), que `INSTALL.md` reprend tel quel :

  ```
  abi <abi/5.0>,
  include <tunables/global>
  profile puppeteer-chrome /home/*/.cache/puppeteer/chrome/*/chrome-linux64/chrome flags=(unconfined) {
    userns,
    @{exec_path} mr,
  }
  profile puppeteer-chrome-headless-shell /home/*/.cache/puppeteer/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell flags=(unconfined) {
    userns,
    @{exec_path} mr,
  }
  ```
- **La permission de la file de fusion.** Dans `docs/dev/agents.md`, une section « La mise en file »
  après « Le pilote » : l'entrée de `permissions.allow` que l'auteur a posée dans
  `~/.claude/settings.json`, qui n'autorise que cette mutation exacte pour n'importe quel
  identifiant de pull request, éprouvée le 2026-11-05 (un livreur a mis #1978 en file avec elle) :

  ```
  "permissions": { "allow": [ "Bash(gh api graphql -f query='mutation($id:ID!){enqueuePullRequest(input:{pullRequestId:$id}){mergeQueueEntry{state}}}' -f id=*)" ] }
  ```

  Elle se pose dans `~/.claude/settings.json` pour tous les dépôts, ou dans `.claude/settings.json`
  du clone pour un seul. La section dit aussi ce qu'elle n'autorise pas : aucune autre requête
  GraphQL, et ni `gh pr merge` ni une fusion hors de la file. `CONTRIBUTING.md` y renvoie.
- **La relecture.** Chaque fichier est lu en entier, une affirmation après l'autre, contre sa source :
  une version contre son fichier de versions (`.python-version`, `package.json`, les Dockerfiles, le
  Makefile, `spec.yml`), une commande contre le Makefile, un chiffre contre la commande qui l'établit
  (`docs/api/INVENTORY.md`, `make requirements`). Un chiffre que rien n'engendre est remplacé par un
  renvoi plutôt que recopié. `README-fr.md` fait foi, `README.md` le suit, `INSTALL.md` reste en
  français, `CONTRIBUTING.md` en anglais.

### Ordre de construction

1. US-1130, PostgreSQL 18 : la montée qui casse, d'abord, sur une branche où rien d'autre n'a bougé ;
2. US-1140, Redis, Garage, Mailpit : les mêmes fichiers de Compose ;
3. US-1150, l'annuaire : `compose.service.yaml` et `deploy/openldap/` ;
4. US-1200, les runners et pandoc : après US-1130, dont le serveur 18 accepte le client 18 des
   runners ;
5. US-1160, Python : `backend/Dockerfile`, après le client PostgreSQL d'US-1130, et après
   US-1200, qui donne à la chaîne le `python3` 3.14 ;
6. US-1170, Node et le front : indépendante des précédentes, sauf `compose.dev.yaml` et les
   workflows ; `@tanstack/virtual-core` en dernier (L3), une fois le reste du front monté ;
7. US-1180, l'extension : `deploy/keycloak/Dockerfile`, après US-1150, qui éprouve la fédération ;
8. US-1250, le faux back : indépendante des autres, elle ne demande qu'US-1130, livrée, et ne touche
   que `tools/` et `DECISIONS.md` ; elle se livre à tout moment ;
9. US-1260, la documentation : après US-1200, US-1150, US-1160/L1 et US-1170/L1 et L2, pour relire
   l'état final de ces quatre fichiers ;
10. US-1190, la veille : en dernier, sur les épinglages de leur forme finale.

Les fichiers qui reviennent : `compose.service.yaml` (US-1130, 1140, 1150),
`compose.prod.yaml` (US-1130, 1140), `backend/Dockerfile` (US-1130, 1160), les workflows (US-1130,
1140, 1170, 1190, 1200), le Makefile (US-1130, 1150, 1170, 1200), `INSTALL.md` et les README de la
racine (US-1130, 1150, 1170, 1200). US-1250 ne partage aucun fichier avec les autres US ; US-1260 ne partage les siens qu'avec des US dont
elle dépend. Le plan de lots en tire ses « Pas avec ».

### Décisions

| Décision | Option écartée, et pourquoi |
|---|---|
| Repartir de zéro à la montée de PostgreSQL, sans garantie sur les sauvegardes prises sur la 16 (auteur, 2026-11-03) | `pg_upgrade` outillé : un composant de plus pour des plateformes qui n'ont pas de données à garder ; la reprise par une sauvegarde prouvée par un test : écartée par l'auteur. C'est une entorse à « Mettre à jour » de `deploy/compose/README.md`, qui gardait les données, et elle s'écrit dans ce même texte ; WF-EXP-0030, que clôt EP-13, n'est pas encore tenue |
| Refuser de démarrer sur un volume d'une autre majeure, en production et en service, par un service ponctuel (auteur, 2026-11-03) | laisser l'image le dire seule : elle refuse bien un volume 16, mais renvoie à `pg_upgrade`, que l'on n'outille pas, et elle ne verra rien à la montée suivante, où un `19/docker` vide naîtrait à côté de `18/docker` ; un nouveau nom de volume : la plateforme démarrerait en silence sur une base vide. La conception validée disait à tort que l'image 18 démarrait sur une base vide ; l'essai du 2026-11-03 l'a démenti, et l'auteur garde le contrôle pour les deux raisons ci-dessus |
| Le contrôle de santé de PostgreSQL par `--host 127.0.0.1`, réécrit dans US-1130 (auteur, 2026-11-03) | un constat à part, ou reporté vers EP-13 : US-1130 touche déjà ces lignes, et la rupture fait passer toutes les plateformes par le premier démarrage où le défaut se montre |
| `postgres:18-trixie` | `18-bookworm` : l'image `waterfall` est déjà en trixie, et le client PGDG suit la même distribution |
| Redis 8 sous l'AGPLv3, dit dans `deploy/compose/README.md` | `REUSE.toml` : il ne déclare que la licence des fichiers du dépôt, et le dépôt ne redistribue pas Redis |
| OpenLDAP construit par le dépôt sur `debian:trixie-slim`, le service, le royaume et les correspondances inchangés (auteur, 2026-11-03, qui revient sur 389 Directory Server décidé le même jour) | 389 Directory Server : ses images officielles, sur Docker Hub comme sur quay.io, sont arrêtées depuis le 24 juin 2025, alors que le logiciel vit (3.3.1, septembre 2026) ; 389 DS construit sur Fedora : `dscreate` et l'amorce plus lourds que `slapd` ; lldap : son schéma est fixe, il ne s'amorce pas par LDIF, et il éprouve la fédération sur un annuaire moins représentatif ; le catalogue Bitnami : il n'est plus libre depuis 2025 |
| Python 3.14, la version du `python3` d'Ubuntu 26.04, du poste et des runners (auteur, 2026-11-03, qui revient sur 3.15 décidé le même jour) | 3.15 : le garde et `slots.py` d'EP-19, lancés par le `python3` du système, auraient demandé une cible de ruff à part, et la cible du dépôt serait restée en avance sur le système |
| Les runners en Ubuntu 26.04, après PostgreSQL 18 (auteur, 2026-11-03) | les garder en 24.04 : la chaîne n'aurait ni le `python3` ni le client PostgreSQL du poste ; avant US-1130 : leur client 18 ne restaurerait pas sur le serveur 16 (#982) |
| pandoc à sa dernière version, la projection régénérée par le lot, sur l'accord de l'auteur (2026-11-03) | installer pandoc 3.1.11.1 sur le poste : Ubuntu 26.04 ne l'a plus, et la projection du poste différerait de celle de la chaîne. C'est une exception à la règle qui interdit à un agent d'écrire dans `docs/spec` (`docs/dev/agents.md`), limitée à la régénération : le document source ne change pas |
| `@tanstack/virtual-core` 3.19 par un lot à lui, prouvé par les parcours, sinon gardé en 3.17.11 (auteur, 2026-11-04) | le garder en 3.17.11 hors d'EP-20, avec un constat : la dette resterait, et Dependabot la reproposerait chaque mois ; le monter avec les autres bibliothèques : 664 tests du front échouent, et la cause n'est pas établie |
| TypeScript reste en 6.0 (auteur, 2026-11-03) | TS 7 : `typescript-eslint` déclare `<6.1.0`, et le contournement d'une dépendance paire est un contournement d'outil |
| corepack retiré ; un pnpm de départ, qui prend lui-même la version de `packageManager` (auteur, 2026-11-03, qui revient sur « corepack épinglé » décidé le même jour) | corepack épinglé, installé par npm : un outil de plus, que Node ne livre plus et que Dependabot ne suit pas, une version en trois copies à accorder par un test, et des pannes à lui (ses clés de signature de npm, en 2025) ; il ne servait qu'à ce que pnpm fait désormais seul |
| JDK 25 pour construire, `release 21` (auteur, 2026-11-03) | `release 25` : Keycloak 26.8.1 tourne sur OpenJDK 21 et ne chargerait pas l'extension ; tout garder en 21 : l'outil de construction prendrait du retard sans raison |
| Les versions du bilan sont des planchers, le lot prend le dernier correctif de la série | les versions exactes du bilan : un lot livré une semaine plus tard reprendrait un retard, que Dependabot signalerait aussitôt |
| Dependabot étendu, mensuel, mineures groupées et majeures seules (auteur, 2026-11-03) | Renovate : une application GitHub de plus ; une cible `make outdated` : elle n'ouvre aucune pull request, et le bilan resterait manuel |
| Recopier la table d'`unaccent` de la 18.6 et adapter le lecteur, dans EP-20 (auteur, 2026-11-05, option 1 de #1960) | la reporter vers un EPIC suivant : EP-20 crée l'écart, et EP-05 s'appuie sur la recherche du faux back ; la laisser : l'écart est mesuré (« ¼ » donne ` 1/4` au service, `1/4` au faux back) |
| La copie reste celle de l'image, le lecteur apprend les guillemets | réécrire la table pour qu'elle reste lisible par `split()` : une copie retouchée ne se compare plus au fichier de l'image, et c'est ce qui la prouve |
| La comparaison à la 18 est faite une fois par le lot et consignée dans `DECISIONS.md` | un test permanent contre un PostgreSQL : les tests des outils n'en ont pas, et la table est figée jusqu'à la prochaine montée |
| Les valeurs des secrets de poste ne s'écrivent que dans `keycloak.yml`, `INSTALL.md` donne la commande qui en tire le fichier (auteur, 2026-11-05) | copier les valeurs dans `INSTALL.md` : elles divergent déjà (`devpostgres`, `chainonlypostgres`) |
| La permission d'`enqueuePullRequest` se documente dans `docs/dev/agents.md` et ne se versionne pas dans `.claude/settings.json` (auteur, 2026-11-05, pour l'endroit ; le choix de ne pas la versionner est du cadrage) | la poser dans le `.claude/settings.json` du dépôt : elle s'appliquerait à tous ceux qui clonent, et la porte d'une mutation de plus ne se donne pas par un fichier versionné |
| La documentation d'installation se prouve par relecture contre ce qui fait foi (auteur, 2026-11-05) | un essai sur un poste neuf : il n'y en a pas de disponible |
| Les minima de WF-CMP-0020 inchangés ; un constat de spécification les propose à 18 et 8 (auteur, 2026-11-03) | les changer dans EP-20 : aucun agent ne modifie la spécification |

---

## US-1130 — La plateforme sur PostgreSQL 18

- **statut** : fini
- **exigences** : aucune — plateforme
- **opérations** : aucune
- **issue** : #1926

**En tant qu'**exploitant, **je veux** que la plateforme tourne sur PostgreSQL 18, sauvegarde et
restauration comprises, et refuse de démarrer sur les données d'une version antérieure, **afin
de** suivre une version maintenue, et de savoir quoi faire quand mes anciennes données ne sont
pas reprises.

**Critères d'acceptation.**

- propre à l'US : PostgreSQL 18, à l'image épinglée par empreinte, sert la plateforme de
  production, la plateforme de service, les services de test et la chaîne ; aucun fichier du
  dépôt n'épingle plus PostgreSQL 16 ;
- propre à l'US : sur un volume neuf, la plateforme de production et la plateforme de service
  démarrent du premier coup : leur contrôle de santé ne dit PostgreSQL prêt qu'une fois son
  initialisation finie, et aucun service qui en dépend ne trouve le serveur fermé ;
- propre à l'US : l'image `waterfall` porte `pg_dump` et `pg_restore` de la majeure 18, et son
  commentaire dit pourquoi le client suit le serveur (#982) ;
- propre à l'US : une sauvegarde déclenchée sur la plateforme de service est vérifiée, et sa
  restauration aboutit ; `make production-trial`, avec `WATERFALL_TRIAL_RESTORATION=1`, passe ;
- propre à l'US : sur un poste dont le client est PostgreSQL 18, les tests des restaurations
  passent, et le guide ne dit plus qu'ils échouent ;
- propre à l'US : la plateforme de production et la plateforme de service refusent de démarrer sur
  un volume PostgreSQL d'une autre majeure ; le refus nomme la version trouvée et celle attendue,
  et dit quoi faire : la note de rupture en production, `make service-down
  WATERFALL_RESET_DATA=yes` en service ; un test le prouve sur un volume 16 ;
- propre à l'US : `deploy/compose/README.md`, « Mettre à jour », dit la
  rupture : la version qui passe à PostgreSQL 18 ne reprend pas les données d'une plateforme 16,
  qu'on retire (`down --volumes`) avant de réinstaller ;
- propre à l'US : le guide et `INSTALL.md` disent le client PostgreSQL 18 du poste.

**Hors périmètre.**

La reprise des données d'une plateforme 16, et la restauration d'une sauvegarde prise sur elle
(« Ce qui n'en fait pas partie »).

---

## US-1140 — Redis 8, Garage v2.5, Mailpit v1.33

- **statut** : fini
- **exigences** : aucune — plateforme
- **opérations** : aucune
- **issue** : #1927

**En tant qu'**exploitant, **je veux** que la plateforme tourne sur Redis 8, Garage v2.5 et
Mailpit v1.33, **afin de** suivre des versions maintenues, et un Redis sous la licence du projet.

**Critères d'acceptation.**

- propre à l'US : Redis 8, Garage v2.5 et Mailpit v1.33, chacun à son image épinglée par
  empreinte, servent toutes les plateformes et la chaîne ; aucun fichier n'épingle plus Redis 7,
  Garage v2.4 ni Mailpit v1.31 ;
- propre à l'US : les tests du back et du front contre Redis et le stockage objet passent, ainsi
  que les parcours contre le service, la session du front, la file des tâches et le cache comme
  avant ;
- propre à l'US : la note de rupture d'US-1130 dit que les données de Redis et de Garage ne se
  reprennent pas non plus ;
- propre à l'US : `deploy/compose/README.md` dit la licence sous laquelle le projet emploie
  Redis : l'AGPLv3.

---

## US-1150 — Un annuaire de test maintenu

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1929

**En tant que** développeur, **je veux** que l'annuaire que Keycloak fédère en développement et
dans la chaîne soit une image maintenue, **afin que** les essais de la fédération (WF-ADM-0180)
ne reposent plus sur une image figée depuis 2021.

**Critères d'acceptation.**

- propre à l'US : l'annuaire de test est une image que le dépôt construit sur une base Debian
  épinglée par empreinte, avec le `slapd` de Debian ; elle remplace `osixia/openldap` dans
  `compose.service.yaml` ; amorcé au premier démarrage, il porte la même personne que
  `deploy/keycloak/development/directory.ldif`, et ne la recharge pas aux démarrages suivants ;
- propre à l'US : le royaume de développement fédère cet annuaire sans changement, et les tests de
  Keycloak (`make test-keycloak`, `keycloak.yml`) qui éprouvent la fédération passent sans changer
  ce qu'ils affirment ;
- propre à l'US : plus aucun fichier ne cite `osixia/openldap`, et le guide et `INSTALL.md` disent
  l'image construite ; `make lint-docker` et `make lint-shell` passent sur ses fichiers.

---

## US-1160 — Le back et les outils sur Python 3.14

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1930

**En tant que** développeur, **je veux** que le back et les outils du dépôt tournent sur
Python 3.14, construits par uv 0.13, avec des bibliothèques à leur dernière version, **afin de**
ne pas écrire le référentiel sur un interpréteur et des bibliothèques en retard.

**Critères d'acceptation.**

- propre à l'US : l'image `waterfall` part de `python:3.14-slim-trixie`, épinglée par empreinte ;
  `requires-python`, `pythonVersion` de pyright et la cible de ruff disent 3.14, dans le back
  comme dans les outils ;
- propre à l'US : le garde des commandes et `slots.py` se compilent avec le `python3` du système
  qui les lance, sur le poste comme dans la chaîne, et un test des outils le vérifie ;
- propre à l'US : l'uv de l'image est de la série 0.13, et la borne `uv_build` des deux
  `pyproject.toml` admet l'uv épinglé ;
- propre à l'US : `backend/uv.lock` et `tools/uv.lock` portent au moins les versions du bilan du
  2026-11-03 — fastapi 0.162, starlette 1.10, httpx2 2.16, uuid-utils 1.2, pytest 9.2,
  datamodel-code-generator 0.88, grimp 3.18, reuse 6.3, et les patchs de sqlalchemy, alembic,
  psycopg, pydantic, pydantic-settings, boto3 et boto3-stubs-lite, ruff, coverage, hadolint-py et
  tzdata ;
- propre à l'US : le client engendré du back depuis le contrat est inchangé, ou sa différence est
  celle de la nouvelle version du générateur, et elle seule ;
- propre à l'US : les tests, le lint, le contrôle de types et l'architecture du back et des outils
  passent ; aucune règle d'un outil n'est relâchée pour y parvenir.

---

## US-1170 — Le front sur Node 26, pnpm 12 et ESLint 10

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1933

**En tant que** développeur, **je veux** que le front se construise et se teste sur Node 26 et
pnpm 12, avec ESLint 10 et des bibliothèques à leur dernière version, **afin de** ne pas écrire
les écrans du référentiel sur une chaîne en retard.

**Critères d'acceptation.**

- propre à l'US : les images du front, du faux back et de développement partent de Node 26,
  épinglé par empreinte ; la chaîne installe Node 26 ; `engines.node` dit `>=26`, et
  `@types/node` est de la série 26 ;
- propre à l'US : `INSTALL.md`, `README-fr.md`, `README.md` et `CONTRIBUTING.md` disent Node 26 et
  pnpm installé par npm, et non plus « Node 24, dont corepack apporte pnpm » ;
- propre à l'US : `packageManager` dit pnpm 12, et reste la seule source de sa version ; plus aucun
  fichier n'emploie corepack, que Node 26 ne livre plus : les images et le poste installent un pnpm
  de départ par npm, la chaîne par `pnpm/action-setup`, et pnpm prend de lui-même la version de
  `packageManager` ;
- propre à l'US : ESLint et `@eslint/js` sont de la série 10, et `eslint-plugin-jsdoc` de la
  série 65 ; le jeu de règles du front garde ce qu'il refuse : une règle retirée ou renommée par
  ces versions a sa remplaçante, ou son retrait est dit dans la pull request ;
- propre à l'US : `pnpm-lock.yaml` porte au moins les versions du bilan du 2026-11-03 — next et
  eslint-config-next 16.4.4, vitest 5.1.0, vite 8.3.5, tailwind 4.3.4, typescript-eslint 8.72.1,
  @redis/client 6.3.1, react et react-dom 19.3.1, echarts 6.1.0, @tanstack/react-table 9.3.1,
  et les dernières de lucide-react, geist, jose et openid-client ; `axe-core`, épinglé exactement,
  à 4.14.0 ;
- propre à l'US : `@tanstack/virtual-core`, épinglé exactement, passe de 3.17.11 à la dernière
  3.19 seulement si les tests du front et les parcours de bout en bout qui éprouvent les grilles
  passent, sans qu'un attendu soit affaibli ; sinon il reste en 3.17.11, et un constat dit
  pourquoi ;
- propre à l'US : TypeScript reste en 6.0, à son dernier patch (« Ce qui n'en fait pas partie ») ;
- propre à l'US : Redocly CLI est à la version 2.72.1 au moins, et `make lint-openapi` passe sur
  le contrat sans le changer ;
- propre à l'US : les tests du front, son lint, son contrôle de types, sa construction pour la
  production et les parcours de bout en bout passent.

---

## US-1180 — L'extension de Keycloak construite sur un JDK 25

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1937

**En tant que** développeur, **je veux** que l'extension de Keycloak se construise sur Maven 3.10
et un JDK 25, avec des bibliothèques de test et des greffons à leur dernière version, sans
dépasser la version de Java que Keycloak exécute, **afin que** sa construction suive, et que
l'image de Keycloak la charge toujours.

**Critères d'acceptation.**

- propre à l'US : l'étape de construction de l'image de Keycloak part de Maven 3.10.0 sur un
  JDK 25, épinglé par empreinte ;
- propre à l'US : `maven.compiler.release` reste 21, celle de Java dans l'image de Keycloak, et le
  `pom.xml` dit pourquoi ;
- propre à l'US : junit-jupiter est de la série 6, et maven-compiler-plugin, surefire et jar sont
  aux versions du bilan au moins (3.16, 3.6.1, 3.5.1) ; `jakarta.ws.rs-api` ne change pas ;
- propre à l'US : `make build-keycloak` et `make test-keycloak` passent, et l'extension se charge
  dans Keycloak 26.8.1.

---

## US-1190 — La veille des versions

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1938

**En tant que** développeur, **je veux** qu'une pull request me propose chaque mois les nouvelles
versions de ce que le dépôt épingle, **afin de** ne plus découvrir un retard de deux majeures
par un bilan fait à la main.

**Critères d'acceptation.**

- propre à l'US : les quatre épinglages des Actions en retard d'un patch sont à jour
  (`ci.yml`, `setup-node` et `upload-artifact` ; `service.yml` et `e2e.yml`,
  `download-artifact`) ;
- propre à l'US : `.github/dependabot.yml` suit, chaque mois, en plus des Actions : uv (back et
  outils), npm (front), Maven (extension de Keycloak), les images des Dockerfiles et celles des
  Compose ;
- propre à l'US : les mises à jour mineures et correctives d'un écosystème arrivent groupées dans
  une pull request, et chaque majeure dans la sienne ; leurs messages de commit suivent la forme
  du dépôt ;
- propre à l'US : le guide dit ce que Dependabot ne suit pas — `REDOCLY_VERSION` et
  `PRISM_VERSION` du Makefile, `packageManager`, l'uv et le client
  PostgreSQL de l'image `waterfall`, les runners et le pandoc de la chaîne —, et qui les relève.

---

## US-1200 — La chaîne sur Ubuntu 26.04, et pandoc à jour

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1928

**En tant que** développeur, **je veux** que la chaîne tourne sur le système de mon poste,
Ubuntu 26.04, et que la projection de la spécification s'y produise avec le même pandoc, **afin
qu'**un essai sur le poste dise ce que dira la chaîne.

**Critères d'acceptation.**

- propre à l'US : chaque travail des workflows tourne sur `ubuntu-26.04` ; aucun ne nomme plus
  `ubuntu-24.04` ;
- propre à l'US : la chaîne est au vert, les tests des sauvegardes et des restaurations du back
  compris, avec le client PostgreSQL 18 du runner contre le serveur 18 d'US-1130 ;
- propre à l'US : `spec.yml` installe la dernière version publiée de pandoc, vérifiée par son
  empreinte, et `make check-tools` attend cette version ;
- propre à l'US : la projection est régénérée par `make build-doc`, le document source inchangé ;
  aucune exigence, aucun champ Vérif et aucun identifiant ne change, et `make roadmap`,
  `make inventory` et `make check-spec` passent ;
- propre à l'US : `INSTALL.md`, `README-fr.md`, `README.md` et `CONTRIBUTING.md` disent la version
  de pandoc.

**Hors périmètre.**

Toute modification du texte de la spécification.

---

## US-1250 — Le faux back cherche comme PostgreSQL 18

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1981

**En tant que** développeur, **je veux** que le faux back translittère un texte cherché avec la table
d'`unaccent` de PostgreSQL 18, celle de la version que sert la plateforme, **afin que** le faux back
cherche comme le service, et que les parcours joués contre l'un se rejouent contre l'autre sans
qu'une fraction ou un guillemet les départage.

**Critères d'acceptation.**

- propre à l'US : `tools/src/wftools/unaccent.rules` est la table que livre PostgreSQL 18.6, celui
  de l'image que la plateforme épingle, telle que l'image la livre ; son en-tête dit la version, le
  fichier d'où elle est copiée et l'image, par son empreinte, et garde la licence PostgreSQL ; la
  pull request donne la commande qui compare la copie au fichier de l'image, et son résultat : aucune
  différence hors l'en-tête ;
- propre à l'US : `wftools.mocktext` lit la table de la 18 comme `unaccent` de la 18 la lit, ses
  traductions entre guillemets comprises (`" 1/4"`, `""""`), et refuse toujours une ligne qu'il ne
  sait pas lire : « ¼ » se lit ` 1/4`, l'espace en tête comprise, comme le service ;
- propre à l'US : la table du faux back est comparée au `unaccent` que livre un PostgreSQL 18, sur
  chaque point de code Unicode, et `folded` à `lower(unaccent(…))` sur chaque texte des exemples :
  aucune différence ; la pull request donne les nombres comparés ;
- propre à l'US : `tools/tests/test_mocktext.py` éprouve ce que la 18 change par rapport à la 16 —
  les traductions entre guillemets, « ¼ » et les guillemets droits — ; un attendu des cas existants
  ne change que là où la 18 diffère de la 16, et la pull request nomme chacun ;
- propre à l'US : aucun exemple engendré ne change (`make mock-data` et `make check-fixtures`
  donnent le même résultat) ; si un exemple change, le lot ouvre un constat que l'auteur tranche ;
- propre à l'US : `docs/api/DECISIONS.md`, « Une recherche translittère comme `unaccent`, puis met
  en minuscules », dit que la table est celle de PostgreSQL 18 et que la comparaison a été faite
  contre un PostgreSQL 18, sous la mention « Reformulé par EP-20/US-1250 » avec ce que la 18
  change ; aucun fichier du dépôt ne dit plus que la table vient de PostgreSQL 16 ; aucune autre
  ligne du contrat ne change.

**Notes de réalisation.**

- **D'où vient le travail.** Constat #1960, relevé par US-1130 : depuis la montée, le service
  tourne sur PostgreSQL 18.6, dont la table diffère de la copie 16.14 que lit le faux back. L'auteur
  retient l'option 1 (2026-11-05) : recopier la table de la 18.6 et rejouer la comparaison de
  `DECISIONS.md` contre un PostgreSQL 18, dans EP-20.
- **L'écart est réel, il se voit sur « ¼ ».** Relevé au cadrage sur l'image `postgres:18-trixie`
  (18.6) : `unaccent('¼')` y donne ` 1/4`, l'espace en tête comprise, là où la copie 16 donne `1/4`.
  La table de la 18 compte 2 661 règles contre 1 650, soit 1 011 sources nouvelles et aucune retirée,
  et 29 lignes dont la traduction change. Le fichier change de forme : 28 traductions y sont entre
  guillemets, ce que la lecture actuelle (`split()`) refuserait comme « plus de deux chaînes ».
- **Comment `make lot-size` compte la table.** `unaccent.rules` n'est ni engendré
  (`tools/paths.toml`), ni un test, ni un fichier source : il tombe dans « autre », en entier. Le
  diff de la table pèse environ 1 075 lignes (1 040 ajoutées, 29 retirées, l'en-tête), et le lot
  environ 1 170 avec le lecteur, les tests et la décision, dont une trentaine de lignes de code de
  production. Il reste sous la barre de 1 500 lignes et de 800 lignes de production ; la revue ne
  lit pas la table ligne à ligne, mais la commande qui la compare au fichier de l'image, et le
  lecteur. L'auteur accepte qu'une copie de données ne se découpe pas (2026-11-05) : si la mesure
  dépassait, le lot ne se couperait pas pour autant.
- **Rien de commun avec US-1160/L1.** Le changement de cible de ruff (`py314`) ne réécrit ni
  `mocktext.py` ni `test_mocktext.py` (essai du 2026-11-05 : 58 constats dans les outils, aucun dans
  ces fichiers).

---

## US-1260 — La documentation d'installation d'un poste neuf

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1982

**En tant que** développeur, **je veux** que `INSTALL.md` et les README disent tout ce qu'un poste
neuf demande, dans l'ordre où il le demande et aux versions que le dépôt épingle, **afin de** monter
un poste en lisant ces seuls documents, sans retomber sur les pannes qu'a relevées la mise au point
du poste de l'auteur.

**Critères d'acceptation.**

- propre à l'US : `INSTALL.md` dit que le bloc qui met `pnpm` et Node (celui de nvm) dans le `PATH`
  — `PNPM_HOME` compris — précède la garde `case $- in` de `~/.bashrc`, et pourquoi : sans cela, un
  shell non interactif, celui des agents ou de `bash -c`, répond `pnpm: not found` ;
- propre à l'US : `INSTALL.md` dit d'installer `mmdc` par npm
  (`npm install -g --allow-scripts=puppeteer @mermaid-js/mermaid-cli`) et non par le snap, dont le
  `/tmp` propre fait échouer `make build-doc` et `make check-spec` ; et, sur Ubuntu 23.10 et plus,
  où `kernel.apparmor_restrict_unprivileged_userns` vaut 1, le profil AppArmor qui accorde `userns`
  au Chrome de puppeteer, avec le texte du profil (« Conception ») ;
- propre à l'US : `INSTALL.md` nomme les onze variables `WATERFALL_*` de `make service-up` et renvoie,
  pour leurs valeurs de poste, au bloc `env` de `.github/workflows/keycloak.yml`, sans les copier ;
  il les range dans `~/.config/waterfall/service.env`, de mode 600, que le `~/.bashrc` charge avant la
  garde `case $- in`,
  et ne donne plus de valeurs qui diffèrent de celles du workflow alors qu'il dit s'y référer ;
- propre à l'US : `INSTALL.md` dit la version de pandoc qu'attend `make check-tools` et comment
  l'obtenir sur Ubuntu 26.04, et qu'une autre version fait échouer `make check-spec` ;
- propre à l'US : `INSTALL.md` dit `WATERFALL_SLOTS`, le nombre de créneaux du poste, où le poser
  — avant la garde, pour que les shells non interactifs le lisent — et renvoie au guide
  (« Commandes ») pour ce qu'il borne ;
- propre à l'US : `docs/dev/agents.md` dit la règle de permission qui laisse un livreur mettre sa
  pull request en file de fusion par la mutation `enqueuePullRequest` (l'entrée de
  `permissions.allow` de « Conception »), où elle se pose et ce qu'elle n'autorise pas ; `CONTRIBUTING.md` y renvoie ;
- propre à l'US : `INSTALL.md`, `README-fr.md`, `README.md` et `CONTRIBUTING.md` sont relus en
  entier, comme le ferait quelqu'un qui installe un poste neuf, et chaque étape manquante, chaque
  ordre faux et chaque version périmée est corrigé contre ce qui fait foi (le Makefile, les
  workflows, les Dockerfiles, les fichiers de versions) ; la pull request liste, fichier par
  fichier, ce qu'elle a corrigé et ce qu'elle a vérifié sans rien changer ;
- propre à l'US : ces quatre fichiers disent Python 3.14, uv et le `python3` du système tels que
  l'EPIC les épingle, Node 26 et pnpm tel qu'US-1170 les installe, l'annuaire que le dépôt
  construit, et la pandoc d'US-1200 — aucune version d'avant la migration ne subsiste ;
- propre à l'US : `README-fr.md` et `README.md` restent la traduction l'un de l'autre, et
  `INSTALL.md` comme `CONTRIBUTING.md` ne se contredisent pas sur un prérequis ;
- propre à l'US : la pull request dit que la documentation n'a pas été rejouée sur un poste neuf, et
  donne, pour chaque commande ou version qu'elle affirme, le fichier qui la fonde.

**Notes de réalisation.**

- **D'où vient le travail.** Constat du 2026-11-05 sur #1925, relevé en mettant le poste de l'auteur
  au point pendant le pilotage d'EP-20 :
  https://github.com/waterfall-project/wf-project/issues/1925#issuecomment-6650689459. Décisions
  de l'auteur du même jour : la preuve est la relecture, sans essai sur un poste neuf ; la revue
  porte sur les quatre fichiers en entier ; les valeurs des secrets renvoient au workflow ; la
  règle de `enqueuePullRequest` va dans `docs/dev/agents.md`, avec un renvoi de `CONTRIBUTING.md` ;
  le travail reste dans EP-20.
- **Se livre après** US-1200 (pandoc, toutes les occurrences de ces fichiers), US-1150 (l'annuaire
  que `INSTALL.md` nomme), US-1160/L1 (Python, que ces fichiers citent) et US-1170/L1 et L2 (Node,
  pnpm sans corepack) : le lot relit l'état final de ces quatre fichiers, pas celui d'avant.
- **Inexactitudes relevées au cadrage**, dans l'état de `epic/EP-20` et de la branche d'US-1200,
  que la relecture confirmera ou complétera : Python 3.13 et « Python 3.11 ou plus » (les trois
  fichiers) ; Node 24 et `corepack enable pnpm` (que l'US-1170 réécrit) ; `openssl`, qu'emploie
  `INSTALL.md` pour `WATERFALL_STORAGE_RPC_SECRET` sans le dire parmi les prérequis ; la source de
  pandoc, que le tableau des prérequis ne dit pas ; des valeurs de secrets que le texte attribue à
  `keycloak.yml` et qui n'y sont pas (`devpostgres` contre `chainonlypostgres`) ; et, dans
  `README-fr.md` et `README.md`, des chiffres et un état que le dépôt a dépassés — « 203 exigences »,
  « 150 opérations sur 116 chemins et 147 schémas » (`docs/api/INVENTORY.md` dit 169 sur 131),
  « quatorze EPIC » (vingt-deux fichiers), « le back vient ensuite, en commençant par EP-03 »
  (livré), « le Compose de développement aujourd'hui ».
- **Les valeurs des secrets ne se copient pas.** Le workflow `keycloak.yml` est la seule source des
  valeurs de poste ; `INSTALL.md` en donne les noms, et la commande qui les range dans le fichier.
- **Taille.** Documentation seulement, aucune ligne de code : environ 450 lignes, de 350 à 700 selon
  ce que la relecture trouve. Si elle dépassait la barre, le lot se couperait en deux : les six
  points du constat, puis la relecture des quatre fichiers.

**Hors périmètre.**

Un essai de la documentation sur un poste neuf. Le guide de développement, qui dit déjà où poser
`WATERFALL_SLOTS`. Les messages de `make check-tools`. L'installation de Claude Code et ses autres
réglages que la permission d'`enqueuePullRequest`.

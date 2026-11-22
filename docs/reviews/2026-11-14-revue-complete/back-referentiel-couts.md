# Revue — back : référentiel de l'entreprise (EP-05) et coûts réels (EP-09)

Commit `29785cc`. Lecture seule ; aucun test, lint ni typage lancé (réservés au coordinateur).
Chemins relatifs à `backend/src/waterfall/` sauf mention.

## Synthèse

Le périmètre est dans un bon état général : les verrous sont pensés règle par règle (référence,
natures, arbre, désignation, projet) et pris dans un ordre unique que j'ai suivi sans trouver de
cycle ; chaque écriture versionnée teste son compteur dans l'écriture ou sous le verrou de la
ligne ; l'unicité est tenue en base partout (codes, libellé, taux par année, triplet de la ligne
de coût `NULLS NOT DISTINCT`, intitulés repliés) ; aucune suppression, clés en `RESTRICT` ; aucun
commentaire d'exemption, aucun SQL en texte. L'import des coûts réels suit sa conception de bout en
bout (lecture gardée avec le compte rendu, application sous le verrou du projet, idempotence par le
triplet, exclusion intacte), et ses tests affirment réellement le résultat. Les huit constats
d'EP-05 repris par EP-23 sont corrigés dans le code lu.

Ce qui inquiète : (1) depuis EP-07 une tâche suit les calendriers des rôles de ses lignes, mais
seule la modification du calendrier **par défaut** redate les révisions en cours — changer les
heures d'un calendrier de rôle, ou le calendrier d'un rôle, laisse des dates (et des montants
projetés) périmés jusqu'à la prochaine écriture sans rapport ; (2) aucun garde-fou contre un
classeur à forte décompression, ouvert par openpyxl dans le processus de l'API dès `openImport`.
Le reste est mineur. Aucun bloquant.

## Constats bloquants

Aucun.

## Constats majeurs

### BRC-01 — Un calendrier de rôle modifié, ou un rôle changé de calendrier, ne redate aucune révision en cours

- **Issue** : #4411 (EP-32), ouverte le 2026-11-21, avec BCH-07.
- **Où** : `core/resource_settings/interface/calendars.py:446-450` (`redating = calendar.is_default and …`),
  `core/resource_settings/interface/resource_roles.py:590-633` (`update_role` : garde `_role_left_idle`
  puis `_write`, aucun `recalculate`, aucun `lock_reference`) ; test qui épingle l'ancien
  comportement : `backend/tests/test_registries.py:605` (« A calendar that is not the default
  redates nothing, whatever its hours »).
- **Quoi** : le recalcul des structures des révisions en cours n'est déclenché que pour le
  calendrier par défaut, alors que depuis EP-07 le calendrier applicable d'une tâche est
  l'intersection des calendriers des rôles de ses lignes de main-d'œuvre (WF-PLA-0010 ;
  `core/planning/interface/facets.py:243-265`, `core/estimate/interface/facet.py:130-153`). La
  docstring le dit encore dans les termes d'EP-06 : « the hours of another calendar, which no task
  of EP-06 is on, redate nothing ». La garde `TASK_WITHOUT_WORKING_HOURS`, elle, a bien été étendue
  aux rôles par EP-07 (`core/estimate/interface/calendars.py:108`) ; le déclencheur du recalcul non.
  C'est le défaut n° 7 de `python.md` (valeur dérivée recalculée sur un chemin, pas sur les autres).
- **Scénario** : calendrier « 35 h » (non par défaut, 7 h du lundi au vendredi) porté par le rôle R ;
  une tâche T d'une révision en cours porte une ligne de main-d'œuvre de R, ses dates sont calculées
  sur 7 h/j. Le manager passe « 35 h » à 8,75 h du lundi au jeudi, 0 le vendredi
  (`updateCalendar`) — ou donne à R un autre calendrier (`updateResourceRole`). La garde passe, rien
  n'est redaté : `start`/`finish` stockés de T restent ceux de l'ancien calendrier, alors que
  `listNodes` rend déjà le nouveau `calendar_hours` (lu en direct, `core/planning/reading.py:66`).
  À la prochaine écriture quelconque de la structure (le moteur rejoue toute la structure,
  `core/planning/interface/structures.py:60-74`), T et ses successeurs sautent, dans `rescheduled`
  d'une saisie sans rapport, sous le nom d'un autre auteur ; les montants projetés qui suivent les
  dates (`reinflate`) aussi. Une révision marquée entre-temps fige des dates fausses.
- **Vérifié** : aucun autre appel de `recalculate` (`grep` : `calendars.py:426,450,475`,
  `duration_units.py:167`) ; les routes `api/calendars.py` et `api/resource_roles.py` n'ajoutent
  rien ; le sujet n'est dans aucun fichier de la roadmap (EP-06 « Le recalcul au changement des
  unités de durée ou du calendrier par défaut », EP-07 « Les déclencheurs du recalcul » ne citent
  pas ce cas). Non exécuté.
- **Proposition** : `update_calendar` redate dès que les heures changent et qu'un rôle employé par
  une ligne d'une révision en cours porte le calendrier (ou, plus simple, dès que les heures
  changent) ; `update_role` prend `lock_reference` avant le verrou du rôle et appelle `recalculate`
  quand `recalendared`. Coût : une vingtaine de lignes, l'ordre des verrous existant (référence →
  ligne → structures) est déjà le bon. Tests : dans `test_reference_recalculation.py`, une tâche
  portant une ligne d'un rôle sur un calendrier non par défaut, ses dates comparées avant/après
  `updateCalendar` puis `updateResourceRole`, et la révision marquée intacte ; corriger
  `test_registries.py:605`.
- **Confiance** : confirmé (chemin lu de bout en bout ; non rejoué).

### BRC-02 — Un classeur à forte décompression est ouvert sans borne, dans l'API dès `openImport`

- **Issue** : #4419 (EP-33), ouverte le 2026-11-21, avec BEX-03, BCH-06, BRC-03, BEX-05.
- **Où** : `core/costs/extraction.py:93-109` (`sheet_rows` : `load_workbook(BytesIO(content),
  read_only=True, …)` puis `list(iter_rows(...))`), appelé par
  `core/costs/interface/actual_costs.py:79` (`read_header`, dans la requête `openImport`),
  `core/costs/analysing.py:180` et `actual_costs.py:102-108` (`prepare`, worker).
- **Quoi** : la seule borne est celle du dépôt, 10 Mio compressés
  (`core/exchanges/interface/imports.py:118,328`). openpyxl, même en `read_only`, charge toute la
  table des chaînes partagées en mémoire (`openpyxl/reader/strings.py:22`, `strings.append(text)`) et
  lit `styles.xml` d'un bloc ; aucun contrôle de la taille décompressée des membres du zip
  (`grep ZipFile|file_size` : rien dans `src/`). Le commentaire « openpyxl, in read-only mode,
  inflates only the first row of the first tab » (`actual_costs.py:43-46`) n'est vrai que de
  l'onglet. `DAMAGES` ne couvre pas `MemoryError`.
- **Scénario** : un contributeur portant `actual_costs.write` sur un projet En cours dépose un
  `.xlsx` de 10 Mio dont `sharedStrings.xml` (ou `styles.xml`) se décompresse en plusieurs Go, puis
  appelle `openImport` : la lecture de l'en-tête, synchrone, épuise la mémoire du processus de
  l'API — indisponibilité pour tous. La même lecture se rejoue dans le worker à l'analyse et à
  l'application (trois tentatives). `sheet_rows` matérialise aussi toutes les lignes du premier
  onglet en une liste, sans plafond de lignes.
- **Proposition** : avant `load_workbook`, ouvrir le zip et refuser (`FILE_FORMAT_UNREADABLE`) si la
  somme des `ZipInfo.file_size` dépasse un plafond (par exemple 200 Mio) ou si un membre dépasse un
  ratio ; plafonner le nombre de lignes lues. À écrire une fois dans `core/exchanges` (le lecteur de
  devis, `core/estimate/interface/excel.py:53`, partage le défaut — à rapprocher des relecteurs
  d'`exchanges` et d'`estimate`). Test : un zip engendré en mémoire dont un membre annonce 1 Go,
  refusé 422 sans allocation.
- **Confiance** : plausible — comportement d'openpyxl lu dans la bibliothèque installée, non
  exécuté ; non vérifié : une éventuelle limite de mémoire du conteneur qui bornerait l'effet à un
  redémarrage.

## Constats mineurs

### BRC-03 — L'en-tête du classeur est lu verrou du projet tenu, à l'ouverture d'un import

- **Issue** : #4419 (EP-33), ouverte le 2026-11-21, avec BEX-03, BRC-02, BCH-06, BEX-05.
- **Où** : `core/exchanges/interface/imports.py:437` (`lock_project`) puis `:452`
  (`form.read_header(session, head)`) ; pour les coûts réels, `core/costs/interface/actual_costs.py:64-80`.
- **Quoi** : `read_header` ouvre le classeur entier par openpyxl (zip, chaînes partagées) et
  interroge la base (`fold_labels`) sous le `FOR UPDATE` du projet — défaut n° 4 de `python.md`. Les
  décisions #2582/#2739 ont sorti la lecture du verrou à l'application, pas à l'ouverture.
- **Scénario** : extraction de 10 Mio, quelques secondes d'analyse des chaînes ; pendant ce temps
  toute écriture du projet attend.
- **Proposition** : lire l'en-tête avant `lock_project` (un `Format.read_header` sans session, ou
  la correspondance lue avant), rejuger sous le verrou. Relève de la mécanique d'`exchanges`
  (autre relecteur) ; le format des coûts réels en est le cas le plus lourd (`HEADER_LENGTH =
  LARGEST_FILE`).
- **Confiance** : confirmé (lecture).

### BRC-04 — Une ligne du projet est rejetée « doublée » à cause d'une ligne d'un autre projet du même fichier

- **Issue** : #3966 (EP-33), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où** : `core/costs/analysing.py:67-90` (`doubled_lines` compare toute ligne dont la pièce est
  lisible, rejetées comprises) ; `core/costs/extraction.py:352-359` (`_key` sans le code projet).
- **Quoi** : WF-DAT-0110 identifie une ligne par **le projet**, la pièce et le poste ; le
  rapprochement interne au fichier ignore le projet. Décidé (#2724 et « the contract's letter »),
  mais la décision ne traite que le motif de confirmation, pas ce cas.
- **Scénario** : extraction « trop large » (cas que le motif de WF-CRE-0020 prévoit), sans colonne
  de poste déclarée (elle est facultative) ; la pièce 5100001 porte une ligne sur `A.ABC.26001` et
  une sur `A.ABC.26002`. À l'import dans 26001, la ligne de 26002 est `WBS_ELEMENT_OUTSIDE_PROJECT`
  **et** fait rejeter la ligne légitime de 26001 par `DUPLICATE_COST_LINE` : elle n'entre jamais
  dans le coût réel (le compte rendu le dit, rien n'est silencieux).
- **Proposition** : ne comparer entre elles que les lignes du projet importé (clé = pièce, poste
  parmi les lignes dont le code projet est le bon) ; garder #2724 pour deux lignes d'un autre
  projet. À trancher par l'auteur : c'est une décision consignée. Test : le scénario ci-dessus dans
  `test_actual_costs_analysis.py`.
- **Confiance** : confirmé (lecture) ; qualification « défaut » à trancher (décision #2724).

### BRC-05 — Les bornes de la matrice de risques ne sont jugées ni en signe ni en étendue

- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `core/risk_settings/matrix.py:29-49` (`matrix_faults` : précision et ordre seuls),
  `api/reference_settings_write.py:86-87` ; la base ne contraint que l'ordre
  (`core/cost_settings/tables.py:84-92`).
- **Quoi** : `probability_bounds: ["-0.5","0","1234567890"]` est accepté et écrit (le motif
  `Decimal` du contrat admet le signe ; `test_reference_settings.py:614` écrit dix chiffres avant le
  point). Une borne de probabilité hors de ]0, 1[ rend des niveaux inatteignables ; une borne
  négative n'a de sens sur aucun axe. Les seuils, eux, sont bornés (`thresholds.py:45-55`).
- **Proposition** : refuser une borne ≤ 0 sur les deux axes et > 1 en probabilité (422 au rang,
  `VALUE_OUT_OF_RANGE`), contrainte de vérification à l'appui dans une migration ; le contrat
  (`Percent`) ne le dit pas — issue de contrat. Sans effet tant qu'EP-08 n'est pas livré.
- **Confiance** : confirmé (lecture).

### BRC-06 — La capacité d'un rôle n'a pas de borne de précision : 500 au lieu de 422 — déjà connu (#2875, EP-10)

- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `api/resource_roles.py:133-135` (`capacity_of`), `core/resource_settings/interface/resource_roles.py:382-392`
  (`_capacity_faults` : le signe seul), colonnes `numeric` sans précision (`tables.py:140-141`).
- **Quoi** : un `headcount` de plus de 16 383 décimales (ou 131 072 chiffres) passe la validation et
  fait échouer PostgreSQL ; aucune limite de taille de corps dans l'API. EP-24 (US-1980) a borné les
  autres décimaux et renvoyé celui-ci à EP-10 (`docs/roadmap/EP-24-…md:232`).
- **Confiance** : plausible (non exécuté).

### BRC-07 — Les unités de durée répondent 500 sur une installation dont l'amorçage n'a pas écrit la ligne

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — le scénario demande une
  installation amorcée avant EP-05 puis migrée sans rejouer l'amorçage, ce qui n'existera pas en
  production ; le gain est un 503 au lieu d'un 500 sur une installation de toute façon inutilisable.
- **Où** : `core/resource_settings/interface/duration_units.py:100-107` et `:141-148` (`.one()`).
- **Quoi** : `getDurationUnits`/`setDurationUnits` lèvent `NoResultFound` là où les paramètres
  communs et la correspondance répondent 503 (`core/cost_settings/refusals.py`, #2235 corrigé par
  EP-23 pour la seule correspondance). Les trois lignes sont écrites ensemble par l'amorçage
  (`bootstrap.py:335-339`) : même cas d'installation migrée sans amorçage rejoué.
- **Proposition** : `one_or_none()` et le même refus 503 ; un test à côté de
  `test_settings_the_bootstrap_has_not_written_are_unavailable`.
- **Confiance** : confirmé (lecture).

### BRC-08 — Le poste d'une ligne de coût et le motif d'exclusion n'ont aucune borne

- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `core/costs/extraction.py:339` (`document_item = text_of(...)`, sans longueur, quand la
  pièce est bornée à 200), `core/costs/tables.py:140,144` (ni `bounded` ni `CHECK`),
  `core/costs/scoping.py:87-90` (motif écrit tel quel, chaîne vide comprise) ; le contrat ne borne
  ni `document_item` ni `ScopeExclusion.reason`.
- **Quoi** : le poste entre dans l'index unique (`tables.py:124-126`) et dans le libellé indexé du
  journal d'audit (`scoping.py:101`) : un poste de plusieurs kilo-octets peu compressible fait
  échouer l'application de tout le fichier (ligne d'index trop grande) au lieu de rejeter la ligne
  (`VALUE_TOO_LONG`). Le motif, sans borne et sans limite de corps, est stocké et rendu à chaque
  page de `listActualCosts`.
- **Proposition** : borner le poste comme la pièce à la lecture (rejet de la ligne) et en base ;
  borner le motif (issue de contrat). Tests : une ligne au poste trop long rejetée, les autres
  appliquées.
- **Confiance** : plausible (limite de l'index non éprouvée).

### BRC-09 — `api/cost_types.py` importe un fichier privé du module

- **Issue** : #4454 (EP-36), ouverte le 2026-11-21.
- **Où** : `api/cost_types.py:39` (`from waterfall.core.cost_settings.commands import CommandAvailability`).
- **Quoi** : le nom n'est pas réexporté par `core/cost_settings/interface/__init__.py` ; la règle
  « toujours depuis `…interface`, jamais depuis le fichier d'un objet » n'est tenue par
  import-linter qu'entre modules du noyau, pas depuis `api/` (même cas hors périmètre :
  `api/subprojects.py:42` → `core.projects.tables`).
- **Proposition** : réexporter `CommandAvailability` dans l'interface ; étendre le contrat
  `independence` aux imports d'`api`, `worker`, `witness` vers `core.*` hors `interface`.
- **Confiance** : confirmé.

### BRC-10 — `tests/test_cost_imports.py` est un fichier vide qui annonce des tests écrits ailleurs

- **Issue** : #4451 (EP-36), ouverte le 2026-11-21, avec BAC-10, FCO-13, FAR-05.
- **Où** : `backend/tests/test_cost_imports.py` (7 lignes, une docstring : « US-1610/L2 writes its
  tests here ») ; les tests du journal sont dans `test_actual_costs_apply.py:365-510`.
- **Proposition** : supprimer le fichier ou y déplacer les quatre tests du journal.
- **Confiance** : confirmé.

## Points forts

- **Verrous** : un verrou consultatif par règle d'ensemble, pris avant toute lecture et dans un
  ordre unique (référence → natures/arbre/désignation → lignes → structures) ; partage (`share_*`)
  pour les écritures qui s'appuient sur un état sans le changer ; documenté dans chaque fichier et
  éprouvé (`test_reference_lock.py`, `test_resource_settings_role_locks.py`). Aucun cycle trouvé.
- **Compteurs** : `UPDATE … WHERE lock_version = :lu` ou comparaison sous `FOR UPDATE` de la ligne
  relue (`populate_existing`) partout ; réponse construite avant la validation.
- **Idempotence des coûts** : triplet unique `NULLS NOT DISTINCT`, une seule fonction d'écriture
  pour l'application et le témoin (`writing.write_line`), exclusion jamais touchée, lecture des
  lignes tenues après le verrou du projet, imputation à la création d'un sous-projet sous ce même
  verrou (`test_an_application_waits_for_the_creation_of_a_subproject_and_imputes_to_it`).
- **Montants** : `Decimal` de bout en bout, arrondi `ROUND_HALF_UP` sur `repr(float)`, bornes de la
  colonne jugées avant le `quantize`, avoirs acceptés, totaux par agrégat SQL.
- **Périmètre** : toutes les lectures et écritures de coûts filtrent par `project_id` du chemin ; un
  sous-projet ou une ligne d'un autre projet répond 422/404 ; tri `passthrough.<colonne>` par
  paramètre lié, sans injection.
- **Habilitations du référentiel** : conformes à #2084 (désactivés sous la permission d'écriture,
  jugée sur la requête, avec la même lecture des booléens que la route).
- **Tests** : 361 tests des fichiers du périmètre parcourus par script — 345 citent une exigence
  (les 16 autres éprouvent des critères « propres à l'US »), tous affirment quelque chose ; les tests
  de concurrence existent pour chaque règle d'ensemble.

## Couverture

- **Lu en entier** : `core/costs/` (tous les fichiers, `interface/` compris) ; `core/cost_settings/`
  (`tables`, `records`, `commands`, `employment`, `refusals`, `interface/hourly_rates`,
  `cost_categories`, `cost_types`, `actual_cost_mapping`, `reference_settings`, `readiness`) ;
  `core/resource_settings/` (`tables`, `org_tree`, `interface/org_nodes`, `resource_roles`,
  `calendars`, `duration_units`, `extensions`, `readiness`) ; `core/indicator_settings/`,
  `core/risk_settings/` ; `api/` : `org_nodes`, `contributors`, `resource_roles`, `calendars`,
  `cost_types`, `hourly_rates`, `reference`, `reference_settings`, `reference_settings_write`,
  `actual_costs`, `actual_cost_mapping`, `cost_imports`, `resource_role_admission`, `evaluation`.
- **Lu pour suivre un chemin** (hors périmètre) : `core/exchanges/running.py`, `judgments.py`,
  `interface/imports.py` (`open_import`), `interface/damages.py` ; `core/projects/interface/subprojects.py`
  et `contributors.py` (parties) ; `core/estimate/interface/calendars.py` ;
  `core/planning/interface/reference.py`, `facets.py` (parties) ; `platform/decimals.py`,
  `platform/database.py` (aides) ; `bootstrap.py` (référentiel).
- **Échantillonné** : `test_actual_costs_apply.py`, `test_actual_costs_analysis.py` (noms et
  extraits), `test_registries.py`, `test_reference_recalculation.py`, `test_reference_settings.py`,
  `test_estimate_hooks.py` (extraits), `asked_*.py` du périmètre ; marqueurs et assertions de tous
  les `test_*` du périmètre par un script d'AST. Spécification : §3.2.2, FBS-3 (corps et Vérif),
  WF-CRE-0010 à 0050, WF-INTF-0140, WF-DAT-0110, WF-PLA-0010. Conception d'EP-05 et d'EP-09 (les
  sections demandées), US-1610 et US-0860 en entier. Contrat : schémas `reference.yaml`,
  `costs.yaml`, `common.yaml` et opérations par extraits.
- **Non lu** : `witness/` (chargeurs du référentiel et des coûts), les migrations `0018`, `0019`,
  `0027` (seulement par `grep`), `interface/__init__.py` des modules au-delà des ré-exports, le
  corps de la plupart des tests, `test_database_constraints_costs.py`, `test_witness_costs.py`,
  les critères d'US-0810 à 0850, 0870 à 0900 et d'US-1620 un par un, le front.
- **Non exécuté** : rien n'a été lancé ; BRC-01 et BRC-02 sont à rejouer par le coordinateur.

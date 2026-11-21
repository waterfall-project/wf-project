# Revue — modèles de données : schéma, migrations, requêtes

Commit relu : `29785cc` (`main`). Préfixe des constats : `DON`. Rien n'a été exécuté : tout est
établi par lecture (migrations, `tables.py`, requêtes, scripts de rôles, tests). Les coûts donnés
pour les constats de performance sont des ordres de grandeur tirés des volumétries du §4.6.2, non
des mesures.

## Synthèse

Le schéma est d'une tenue rare : chaîne Alembic linéaire (0001 → 0028, une tête), migrations
écrites à la main et relues contre `tables.py` par un test de catalogue, types exacts partout
(`numeric`, `timestamptz`, `date`, `uuid` v7 sans défaut de base, aucune énumération PostgreSQL,
aucun `float`), clés étrangères en refus sauf les cascades décidées, unicités du §4.4.1 toutes
déclarées, immuabilité des révisions marquées tenue par déclencheurs sur les neuf tables
révisionnées (propriétaire compris, `search_path` propre, troncature refusée partition par
partition), journal d'audit protégé par droits et par déclencheur, rôle de service sans DDL.
Aucun constat bloquant.

Ce qui inquiète est du côté des **requêtes**, pas du schéma : trois familles de lectures ne
tiennent pas les volumétries que le partitionnement devait garantir — des `EXISTS` sur `node`
filtrés par la seule révision, donc sans élagage de partition, joués 2 à 3 fois par révision
listée (DON-01) ; la garde des calendriers d'EP-07, qui lit les lignes de devis de **toutes** les
révisions de **tous** les projets, marquées comprises (DON-02) ; et la question « cette catégorie
est-elle employée ? », un `DISTINCT` sur toutes les lignes de la plateforme à chaque liste des
natures ou des catégories (DON-03). Les trois grandissent avec l'histoire (130 à 180 révisions par
projet) et non avec le projet ouvert.

Le reste est mineur : quelques invariants simples laissés au service, des colonnes `*_id` sans clé,
un index de lignée absent, un compte rendu d'import que la spécification dit supprimé et que le
code garde, un droit perdu à la restauration, un test de « descente miroir » qui prouve moins qu'il
n'annonce.

## Constats bloquants

Aucun.

## Constats majeurs

### DON-01 — Des lectures de `node` filtrées par la seule révision parcourent toutes les partitions, 2 à 3 fois par révision lue

- **Issue** : #4484 (EP-40), ouverte le 2026-11-21, avec DON-04, BPR-05, BPR-06.
- **Où** : `backend/src/waterfall/core/planning/interface/nodes.py:209-213` (`revision_has_tasks` :
  `exists().where(Node.revision_id == revision_id, Node.kind == TASK)`) ;
  `backend/src/waterfall/core/planning/interface/lines.py:233-237` (`revision_bears`, même forme) ;
  `backend/src/waterfall/core/planning/interface/skeleton.py:150-155` (`_has_tasks` :
  `Node.structure_id == …` sans `project_id`, alors que `place.project_id` est sous la main).
  Appelants : `core/revisions/states.py:48-70` (`state_of`, qui tient pourtant `project_id` dans son
  couple `revision`), lui-même appelé **par ligne** dans `core/revisions/interface/revisions.py:271-320`
  (`_views` : `listRevisions`, `getRevision`) et par `core/revisions/interface/structures.py:195`
  (`revision_state`, à chaque lecture des structures) ; `core/revisions/interface/reference.py:165`.
- **Quoi** : `node` est partitionnée par `project_id` ; un filtre sur `revision_id` seul ne permet
  aucun élagage, PostgreSQL planifie et sonde l'index `ix_node_revision_id` de **chaque** partition.
  WF-DAT-0050 : « Toute requête portant sur un projet ne lit que sa partition ». Le test du dépôt
  le sait pour `cost_structure` (`backend/tests/test_partitions.py:89-112` : « A reading by the
  revision alone would read every partition ») mais aucune des requêtes ci-dessus n'est éprouvée.
- **Scénario** : plateforme à 600 projets conservés (§4.6.2). Un chef de projet ouvre l'historique
  des révisions : pour chaque révision de la page, `revision_has_tasks_and_lines` (question
  « tâches », puis « lignes ») et `revision_has_tasks` émettent 2 à 3 `EXISTS`, chacun planifié sur
  600 partitions et leurs 6 index, verrous `AccessShare` compris (≈ 4 000 par requête, tenus jusqu'à
  la fin de la transaction — c'est la raison de `max_locks_per_transaction=1024` du Compose, qu'un
  PostgreSQL externe n'aura pas). Une page de 50 révisions fait 100 à 150 de ces requêtes ; une
  révision vide (aucune tâche) sonde les 600 index. Le temps de lecture d'une révision dépend donc
  du nombre de projets, ce que le Vérif de WF-DAT-0050 exclut (« la même sur une plateforme d'un
  projet et sur une plateforme de six cents »).
- **Proposition** : donner `project_id` aux trois fonctions (les questions du registre
  `register_tasks_and_lines` prennent `(session, project_id, revision_id)`, `state_of` l'a déjà) et
  l'ajouter au `WHERE` ; au passage, lire les faits d'une page de révisions en une requête groupée
  plutôt qu'en N+1. Test : étendre `test_partitions.py` — `EXPLAIN (FORMAT JSON)` des trois requêtes
  compilées, trois projets, l'ensemble des relations lues doit être la seule partition du projet.
- **Confiance** : confirmé (requêtes et appelants lus ; coût non mesuré). WF-DAT-0050 se clôt en
  EP-13 (non livré), mais le défaut est dans du code livré (EP-04/EP-06/EP-07) et contredit le corps
  de l'exigence ; non trouvé dans `docs/roadmap/`.

### DON-02 — La garde des calendriers d'EP-07 lit les lignes de devis de toutes les révisions de tous les projets

- **Issue** : #4485 (EP-40), ouverte le 2026-11-21, avec BCH-12.
- **Où** : `backend/src/waterfall/core/estimate/interface/calendars.py:41-51` (`_roles_changed` :
  `select(EstimateLine.resource_role_id).where(resource_role_id IS NOT NULL).distinct()`, sans
  projet ni révision) et `:54-72` (`_lines_of_roles` :
  `select(project_id, node_id).where(resource_role_id.in_(roles))`, puis filtre **en Python** sur
  les révisions en cours par `node_revisions`) ; appelées par `idle_tasks_for_role_calendar`
  (`:108-128`), enregistrée par `core/estimate/interface/__init__.py:428`, donc jouée à chaque
  `updateCalendar`, `setDefaultCalendar`, création d'un calendrier par défaut et `updateResourceRole`
  (`core/resource_settings/interface/calendars.py:408,445,472`, `resource_roles.py:620`).
- **Quoi** : la docstring ne vise que « a task of a current revision », mais le SQL ne borne rien :
  `estimate_line` n'a pas de `revision_id` (la facette passe par son nœud), et aucune jointure à
  `node` ne restreint aux révisions en cours. La garde sœur du planning, elle, filtre par les
  structures en cours (`core/planning/interface/reference.py:74-80`).
- **Scénario** : un administrateur modifie les heures du calendrier que portent la plupart des
  rôles. (1) `_roles_changed` parcourt l'index `resource_role_id` de chaque partition, soit toutes
  les lignes de main-d'œuvre jamais marquées — de l'ordre de 10⁸ à l'échelle du §4.6.2 (600 projets
  × 130 révisions × quelques milliers de lignes). (2) `_lines_of_roles` ramène en mémoire du
  processus un couple `(project_id, node_id)` par ligne de ces rôles dans **chaque** révision
  marquée, puis passe par projet un tableau de tous ces identifiants à `node_revisions`. Dès une
  année d'usage (300 projets × 12 révisions × ~4 000 lignes ≈ 14 M de couples) la route met des
  dizaines de secondes et des gigaoctets ; à terme elle ne répond plus, et c'est une écriture du
  référentiel qui tient déjà ses verrous (`REFERENCE_LOCK`).
- **Proposition** : (a) lire les rôles du calendrier changé dans le référentiel (par l'interface de
  `resource_settings`, `resource_role.calendar_id`), pas dans les lignes ; (b) pour chaque structure
  en cours (`current_structures`, qui donne `project_id` et `revision_id`), joindre `estimate_line`
  à `node` sur `(project_id, node_id)` avec `node.project_id = :p AND node.revision_id = :r` — une
  partition, une révision. Test : un projet portant une révision marquée et une en cours employant
  le même rôle ; espionner les instructions (événement `before_cursor_execute`) et vérifier que
  chaque lecture d'`estimate_line` porte le projet et qu'aucune ligne de la révision marquée n'est
  ramenée ; plus un `EXPLAIN` d'élagage comme DON-01.
- **Confiance** : confirmé (chemin lu de la route au SQL) ; volumes estimés. Non trouvé dans
  `docs/roadmap/`.

### DON-03 — « Cette catégorie est-elle employée ? » : un `DISTINCT` sur toutes les lignes de devis de la plateforme, à chaque liste des natures et des catégories

- **Issue** : #4486 (EP-40), ouverte le 2026-11-21.
- **Où** : `backend/src/waterfall/core/estimate/interface/employment.py:34-43`
  (`select(EstimateLine.cost_category_id).where(cost_category_id.in_(ids)).distinct()`), enregistrée
  par `core/estimate/interface/__init__.py:414` ; appelée par
  `core/cost_settings/interface/cost_categories.py:145-147` (`category_holdings`), lui-même dans
  les vues de liste : `cost_categories.py:173` et `cost_types.py:114-123,144` (pour un lecteur qui
  peut modifier, `may_change`).
- **Quoi** : la réponse attendue est un booléen par catégorie ; la requête lit **toutes** les
  entrées d'index correspondantes de toutes les partitions (PostgreSQL ne s'arrête pas au premier
  rang d'un `DISTINCT … IN`). Pour `listCostTypes`, l'ensemble demandé est celui de toutes les
  catégories des natures listées, c'est-à-dire, en pratique, toutes les lignes de devis de toutes
  les révisions de tous les projets.
- **Scénario** : le responsable du référentiel ouvre l'écran des natures de coût : une lecture
  d'index de l'ordre de 10⁶ entrées après quelques mois, 10⁸ à 10⁹ à l'échelle du §4.6.2, pour
  afficher une liste de quelques natures. Même requête à chaque `updateCostType`/`updateCostCategory`
  (`cost_types.py:300`, `cost_categories.py:491`).
- **Proposition** : un `EXISTS` par catégorie, qui s'arrête au premier rang —
  `SELECT c.id FROM unnest(:ids) AS c(id) WHERE EXISTS (SELECT 1 FROM estimate_line WHERE
  cost_category_id = c.id)` : au pire une sonde d'index par partition et par catégorie non
  employée. Test fonctionnel inchangé, plus un test de forme (`EXPLAIN` : un `Semi Join`/`Limit`, pas
  d'`Index Only Scan` sans borne), et une mesure sur le jeu de référence de WF-QUA-0040 quand il
  existera.
- **Confiance** : confirmé (requête et appelants lus) ; volumes estimés. Non trouvé dans
  `docs/roadmap/`.

## Constats mineurs

### DON-04 — Aucun index sur `node.lineage_id` : chaque suppression de tâche balaie la partition du projet

- **Issue** : #4484 (EP-40), ouverte le 2026-11-21, avec DON-01, BPR-05, BPR-06.
- **Où** : `backend/src/waterfall/core/planning/shaping.py:182-188`
  (`select(Node.lineage_id).where(Node.project_id == project_id, Node.lineage_id.in_(lineages))`) ;
  index de `node` : `core/planning/tables.py:132-149`, migration `0022_planning.py:319-339` —
  aucun ne commence par `lineage_id`.
- **Quoi** : pour savoir si une lignée survit dans une autre révision (inscriptions aux suivis,
  WF-PLA-0060), `deleted()` cherche par lignée dans toute la partition du projet — toutes ses
  révisions, jusqu'à 1,8 million de nœuds (180 × 10 000) — sans index.
- **Scénario** : en dixième année d'un projet, `deleteNode` d'une tâche de la révision en cours fait
  un parcours séquentiel de la partition, sous le verrou de la structure, dans une opération dont
  l'objectif est la seconde (§4.6.2).
- **Proposition** : `Index(None, "lineage_id")` sur `node` (créé sur le parent, hérité par chaque
  partition ; migration `CONCURRENTLY` par partition si des données existent). Il servira aussi la
  comparaison de révisions et le suivi temps/temps (WF-DAT-0030, EP-10). Test : `EXPLAIN` de la
  requête, `Index Scan` attendu.
- **Confiance** : confirmé (requête et index lus), coût estimé.

### DON-05 — Un compte rendu d'import n'est jamais supprimé, contre le §4.4.1, la Conception d'EP-06 et ses propres docstrings ; le droit `DELETE` accordé ne sert pas

- **Issue** : #4425 (EP-33), ouverte le 2026-11-21, avec BEX-07, BEX-10, BEX-11, FCO-06.
- **Où** : spécification §4.4.1 (« un compte rendu d'import [se supprime] à son expiration ou à
  l'abandon de l'import », `docs/spec/waterfall-spec.md`, « Suppression », et WF-DAT-0080) ;
  `docs/roadmap/EP-06-planification.md:386-389` ; docstrings de
  `backend/src/waterfall/core/exchanges/tables.py:9-10` (« It is deleted at its expiry or its
  abandonment ») et de `migrations/versions/0022_planning.py` (en-tête) ; commentaire de
  `tests/test_migrations.py:408-411`. Code : `core/exchanges/interface/purge.py:132-153` ne fait que
  passer la ligne à `expired`/`failed` ; `core/exchanges/interface/imports.py:614` la passe à
  `abandoned` ; aucun `delete(ImportReport)` dans `backend/src` (recherché).
- **Quoi** : la ligne et son `report` (jsonb, un rejet par ligne refusée) restent pour toujours ;
  le contrat, lui, liste les imports `abandoned` et `expired`, et `cost_import.import_report_id`
  est une clé en refus (`0027_costs_and_remaining.py`) qui interdirait de supprimer un compte rendu
  appliqué. Trois textes disent une règle, le code et le contrat une autre. Le rôle du service
  tient `DELETE` sur `import_report` (`0022_planning.py:56-62`) sans l'employer.
- **Scénario** : aucune panne ; une table technique qui grossit sans règle de rétention, et un
  lecteur de la spec ou de la docstring qui croit la ligne purgée.
- **Proposition** : trancher et aligner — soit la spec et les docstrings disent que le compte rendu
  est gardé (et `DELETE` est retiré au rôle du service, `SERVICE_RIGHTS` avec), soit la purge
  supprime les comptes rendus `abandoned`/`expired`/`failed`/`refused` échus et garde les `applied`
  que `cost_import` cite. Test : celui de la purge, qui compte les lignes après l'échéance.
- **Confiance** : confirmé.

### DON-06 — Après une restauration, `create_project_partitions` est exécutable par `PUBLIC`

- **Issue** : #4475 (EP-39), ouverte le 2026-11-21, avec BSO-05, BSO-03.
- **Où** : `backend/src/waterfall/worker/restore.py:134-144` (`pg_restore --no-owner
  --no-privileges`) ; `backend/src/waterfall/platform/restoration.py:49-65` (`SERVICE_GRANTS` ne
  garde que les droits des **tables** et des **colonnes** : `pg_class.relacl`, `pg_attribute.attacl`)
  et `:181-185` (`end_keeping`) ; `migrations/versions/0020_projects_and_revisions.py:49-52,85`
  (`REVOKE ALL … FROM PUBLIC`, `GRANT EXECUTE … TO <base>_service`).
- **Quoi** : la fonction `SECURITY DEFINER` est recréée par `pg_restore` sans ses droits, donc avec
  le défaut de PostgreSQL — `EXECUTE` à `PUBLIC` —, et rien ne rejoue le `REVOKE` de `0020` (les
  migrations ≥ 0022 la remplacent par `CREATE OR REPLACE`, qui garde les droits en place). Le
  service continue de l'exécuter (par `PUBLIC`), si bien que rien ne casse ; mais l'invariant que
  `tests/test_migrations.py:455-481` épingle (« the service alone may execute ») ne tient plus : le
  rôle de sauvegarde, que `deploy/compose/backup-database-role.sql` veut incapable d'écrire, peut
  faire créer des partitions par le propriétaire (`pg_read_all_data` lui donne `USAGE` sur le
  schéma).
- **Scénario** : restauration d'une sauvegarde prise en ≥ 0020 (toutes, depuis la v0.3.0) ; ensuite
  `SELECT has_function_privilege('waterfall_backup', 'create_project_partitions(uuid)', 'EXECUTE')`
  rend vrai.
- **Proposition** : faire garder par `SERVICE_GRANTS` les droits des fonctions (`pg_proc.proacl`) et
  rejouer `REVOKE ALL ON FUNCTION … FROM PUBLIC` dans `end_keeping`, ou le poser dans la migration
  de tête par un bloc idempotent que la restauration rejoue. Test : dans `test_restore_service.py`,
  la requête de `test_migrations.py:462-470` après une restauration.
- **Confiance** : confirmé par lecture (comportement de `--no-privileges` et droits par défaut d'une
  fonction) ; non exécuté.

### DON-07 — Invariants simples que la base laisse au service (défaut n° 1 de `sql.md`)

- **Issue** : #4469 (EP-38), ouverte le 2026-11-21, avec DON-08, DON-09, DON-14, BPR-11.

Chacun est une contrainte de vérification d'une ligne, sans coût, que la base ne porte pas :

- `node` (`core/planning/tables.py:114-163`, `0022_planning.py:303-336`) : une ligne de devis sans
  parent est admise (`kind = 'task' OR parent_id IS NOT NULL` manque — « une ligne de devis est
  toujours portée par une tâche », §3.2.5) ; un nœud est admis comme son propre parent
  (`parent_id <> id` manque, alors qu'`org_node` l'a : `ck_org_node_not_its_own_parent`) — la clé
  `(project_id, parent_id, structure_id) → node` est satisfaite par la ligne elle-même.
- `revision` (`core/revisions/tables.py:80-152`) : `is_reference` est admis sur une révision
  `draft` (WF-REV-0040 : « parmi les révisions marquées ») ; `inflation_rate` et `win_probability`
  ajoutés par `0025_estimate.py:245-246` n'ont pas la borne 0–1 que `project` porte
  (`ck_project_inflation_rate_between_zero_and_one`).
- `cost_line` (`core/costs/tables.py:91-154`) : `document_item` vide (`''`) et nul sont deux
  valeurs pour l'unicité `NULLS NOT DISTINCT` ; seul `text_of` (`core/costs/extraction.py:112-123`)
  ramène le vide au nul. WF-DAT-0110 veut que l'idempotence tienne « même quand le code a oublié » :
  `CHECK (document_item <> '')` (ou non blanc) la ferme.
- `import_report` (`core/exchanges/tables.py:46-91`) : `period_from <= period_to` manque, alors que
  `cost_import` l'a (`ck_cost_import_period_ordered`).
- **Scénario** : une écriture qui contourne le service — un chargeur, une migration de données, un
  futur chemin d'import — pose la ligne sans être refusée.
- **Proposition** : une migration de contraintes (posées `NOT VALID` puis validées), un test par
  contrainte dans `test_database_constraints_*.py`.
- **Confiance** : confirmé (absence lue dans les tables et les migrations ; le service tient chacune
  aujourd'hui, vérifié pour `is_reference` — `designate_reference` — et `document_item`).

### DON-08 — Des clés qui ne nomment pas le projet laissent passer un rattachement entre deux projets, et leurs contrôles ne s'élaguent pas

- **Issue** : #4469 (EP-38), ouverte le 2026-11-21, avec DON-07, DON-09, DON-14, BPR-11.
- **Où** : `task.order_item_id → order_item(id)` et `task.work_package_id → work_package(id)`
  (`0022_planning.py:370-371`) ; `project.reference_revision_id` et `current_revision_id →
  revision(id)` (`0020_projects_and_revisions.py:369-370`, alors que `uq_revision_project_id`
  `(project_id, id)` existe) ; `order_item.project_id` et `deliverable.project_id`, recopiés du
  parent sans clé composite (`0020…:296-330`) ; `cost_line.last_import_id → cost_import(id)`
  (`0027…`) ; `tracking_entry.project_id` à côté de `timeline_id`.
- **Quoi** : la conception a pris soin de clés composites partout dans le révisionné (structure avec
  sa révision, nœud avec sa structure, sous-projet avec son projet) ; ces relations-ci ne le sont
  pas, et la base admet une tâche du projet A rattachée à un poste du projet B, ou un projet dont
  la « révision en cours » est celle d'un autre. S'y ajoute un coût : la suppression physique d'un
  lot ou d'un poste fait vérifier `task` sans clé de partition, donc dans chaque partition.
- **Proposition** : `UNIQUE (id, project_id)` sur `work_package`, `order_item`, `cost_import` (comme
  `uq_subproject_id`), puis clés `(project_id, …_id)` ; pour `project`, clés
  `(id, reference_revision_id)` et `(id, current_revision_id)` vers `revision(project_id, id)`.
  Tests : l'insertion croisée, refusée par le nom de la clé.
- **Confiance** : confirmé (schéma lu) ; aucun chemin du service ne produit aujourd'hui la ligne
  croisée (non recherché exhaustivement).

### DON-09 — Colonnes `*_id` sans clé étrangère que la Conception ne justifie pas

- **Issue** : #4469 (EP-38), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec DON-07, DON-08, DON-14, BPR-11.
- **Où** : `revision_rate.cost_category_id` (`0025_estimate.py:255`, `core/estimate/tables.py:172-192`) ;
  `import_report.task_id`, `upload_id`, `revision_id`, `structure_id` (`0022_planning.py:566-574`) ;
  `paste_plan.structure_id`, `target_node_id` (`0022…:540-542`) ; les identifiants recopiés des
  images (`revision_role.resource_role_id`, `org_node_id`, `cost_category_id`, `calendar_id`, etc.).
- **Quoi** : `sql.md` (« une relation sans clé étrangère n'existe pas », WF-DAT-0090) ne fait
  exception que pour le journal d'audit. Pour les images, la raison donnée (« an image outlives
  what it names ») ne tient pas : un objet du référentiel n'est jamais supprimé (WF-DAT-0080), une
  clé en refus ne coûterait rien et garantirait la jointure ; `revision_rate.cost_category_id`,
  ligne vivante d'une révision en cours, n'a aucune raison donnée (la ligne de devis voisine a sa
  clé). `import_report.upload_id`/`revision_id`/`structure_id` sont défendables (le dépôt est purgé,
  la révision peut être abandonnée) mais la Conception ne le dit pas ; `task_id` pourrait être une
  clé.
- **Proposition** : clé en refus pour `revision_rate.cost_category_id` et `import_report.task_id` ;
  une phrase dans les Conceptions pour les autres. `node.origin_risk_id` attend EP-08, ce n'est pas
  un constat.
- **Confiance** : confirmé.

### DON-10 — Écarts schéma ↔ spécification décidés par les Conceptions, jamais reportés dans la spécification

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — déjà tranché par l'auteur au tri
  du 2026-11-18 : #3385 (SPT-07) clos « non retenu », #3386 (SPT-08) retenu sans le Tableau 10.
- `display_preference` : le Tableau 10 (§4.4.1) nomme une table, et le régime de suppression « une
  préférence d'affichage à la demande de son porteur » ; le schéma porte
  `user_account.display_preferences` (jsonb, `0001…`, Conception d'EP-03 l. 417).
- WF-DAT-0090 : « La suppression physique d'un lot ou d'un poste met à nul, **en base**, le
  rattachement des tâches de la révision en cours » ; le schéma refuse (`RESTRICT`,
  `0022_planning.py:370-371`) et c'est le service qui détache (`detach_work_breakdown_item`,
  Conception d'EP-06 l. 460). Le résultat est le même, la phrase de l'exigence — close en EP-07 —
  est fausse.
- WF-DAT-0090 : cascade autorisée « qu'à l'intérieur d'une révision en cours, d'une tâche vers ses
  lignes et ses liaisons » ; `tracking_entry.timeline_id` est en `CASCADE` hors de toute révision
  (`0022…:453`, décidé par EP-06), et `node → cost_structure`, `node → parent` cascadent au-delà de
  « ses lignes et ses liaisons ».
- **Proposition** : une correction de la spécification (comme celles relevées pendant EP-16/EP-24),
  pas du schéma. **Confiance** : confirmé.

### DON-11 — Le test de la « descente miroir » ne prouve que la descente de la chaîne entière, sur une base vide

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue dit elle-même « portée
  faible » : la descente ne sert qu'aux tests et au poste, jamais à une installation (§4.5.3 ;
  US-2850 met le retour arrière du schéma hors périmètre).
- **Où** : `backend/tests/test_migrations.py:196-212`
  (`test_each_migration_is_undone_by_its_mirror_and_applied_again`) ; `docs/dev/sql.md` (tableau des
  contrôles) et le guide (« la descente est le miroir de la montée ») s'y réfèrent.
- **Quoi** : le test monte tout, descend à `base`, constate qu'il ne reste ni table ni fonction, et
  remonte. Une descente qui ne remet pas l'état de la révision précédente passe dès qu'une descente
  plus ancienne supprime l'objet : celles de `0011`, `0014`, `0021` (contraintes et index du
  journal), de `0022`/`0025`/`0026` (la fonction précédente remise), de `0012`/`0024` (droits) ne
  sont pas comparées à l'état qu'elles doivent rendre ; et aucune ne tourne sur des lignes. Seules
  `0016` et `0023` ont un test propre (`:709`, `:769`), `0002`/`0003` aussi (`:330`).
- **Proposition** : un test pas à pas — pour chaque révision N, `describe_schema` (déjà écrit,
  `:215-239`, à étendre aux fonctions, déclencheurs et droits) après montée à N-1, puis après montée
  à N et descente à N-1 : égalité. Coût : une cinquantaine de montées/descentes sur base vide.
- **Confiance** : confirmé (test lu). La descente ne sert qu'aux tests et au poste (§4.5.3) : portée
  faible.

### DON-12 — Deux migrations importent du code applicatif

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — préférence de style : une
  migration appliquée ne se modifie pas, et `new_id` est la fonction la plus stable du service.
- **Où** : `migrations/versions/0005_permission_catalogue.py:18` et
  `0006_read_only_functions.py:16` (`from waterfall.platform.identifiers import new_id`).
- **Quoi** : les migrations `0014` et `0021` écrivent en toutes lettres ce qu'elles emploient
  « as a migration does not read the code that follows it » ; ces deux-là dépendent d'une fonction
  du service (et de `uuid_utils`) qui devra rester importable à jamais sous ce nom.
- **Proposition** : `uuid_utils.uuid7()` en ligne dans les deux fichiers (une migration appliquée ne
  se modifie pas : seulement si l'on juge l'import figé inacceptable), ou la règle écrite dans
  `sql.md` avec `new_id` comme seule exception. **Confiance** : confirmé.

### DON-13 — La purge relit et verrouille tous les exports réussis de l'histoire, toutes les dix minutes

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — une fois la rétention d'EP-13
  fusionnée, le lot est borné à un mois d'exports : gain non mesurable.
- **Où** : `backend/src/waterfall/core/exchanges/interface/purge.py:156-175` (`_exports_old`).
- **Quoi** : la requête prend `FOR UPDATE` toutes les tâches `export` réussies de plus de 24 h, déjà
  consommées comprises (le tri se fait en Python par `has_file`), et `background_task` n'a aucune
  rétention avant EP-13 : le lot grandit sans borne.
- **Proposition** : ajouter au `WHERE` la condition que `_named_exports` écrit déjà
  (`result['consumed'].astext IS DISTINCT FROM 'true'`, `:272-282`). **Confiance** : confirmé.

### DON-14 — Droits du rôle du service au-delà de ce que le code emploie

- **Issue** : #4469 (EP-38), ouverte le 2026-11-21, avec DON-07, DON-08, DON-09, BPR-11.
- **Où** : `installation` : `UPDATE` (`0002_service_role.py`, gardé par `0012`) — aucun code ne
  modifie la ligne (`platform/installation.py` ne fait que lire ; recherché) ; `import_report` :
  `DELETE` (DON-05).
- **Proposition** : retirer `UPDATE` sur `installation` tant qu'aucune route ne la modifie, et
  `DELETE` sur `import_report` selon l'issue de DON-05 ; `SERVICE_RIGHTS` avec leurs raisons.
- **Confiance** : confirmé pour ces deux droits ; les autres tables n'ont pas été passées au crible
  droit par droit.

### DON-15 — `backup.task_id` bloquera la purge des tâches comme `identity_sync_report.task_id`

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-13 (US-2830), la purge des
  tâches épargne celles que nomme une sauvegarde encore listée (`backup_task_ids`, passé en `spared`
  à `purge_ended`) : la clé reste en refus mais n'est plus heurtée. `identity_sync_report.task_id`
  est passée en cascade (`0035`, #921). Aucune autre table ne désigne `background_task` par une clé.
- **Où** : `0010_backup.py` (`ForeignKeyConstraint(["task_id"], ["background_task.id"],
  ondelete="RESTRICT")`), `core/backups/tables.py:50-53`.
- **Quoi** : même motif que le constat reporté pour `identity_sync_report` ; la purge de rétention
  des tâches (§4.4.1, trente jours) butera aussi sur les sauvegardes gardées plus longtemps que
  leurs tâches.
- **Déjà connu en partie** (#921, EP-13, `docs/roadmap/EP-13-exploitation.md:321-325`) : l'issue ne
  nomme que `identity_sync_report`. **Confiance** : confirmé.

## Points forts

- Chaîne linéaire 0001 → 0028, chaque `down_revision` vérifié à la lecture ; un verrou consultatif
  de session sérialise les instances (`migrations/env.py`) ; `waterfall-migrate` ne sait que monter.
- Schéma et `tables.py` comparés dans le catalogue de PostgreSQL (contraintes, index, colonnes,
  défauts) par `test_migrations.py:241` : je n'ai trouvé aucune divergence de colonne, de type, de
  nullité ou de défaut entre les 28 migrations et les 12 `tables.py`.
- Types : aucun `float`, aucun `timestamp` sans fuseau, aucun identifiant engendré par la base,
  aucune énumération PostgreSQL ; montants `numeric(14,2)`/`numeric(12,2)`, précisions jugées avant
  l'écriture (`platform/decimals.py`).
- Immuabilité (WF-DAT-0020) : déclencheur `BEFORE INSERT OR UPDATE OR DELETE` sur chacune des neuf
  tables révisionnées, révision verrouillée `FOR KEY SHARE` avant d'être lue, `search_path` propre,
  table nommée dans `public` ; `revision` ne change, marquée, que dans quatre colonnes ; troncature
  refusée sur le parent et sur chaque partition ; clés composites qui empêchent de lier une révision
  en cours à la structure, au parent ou au nœud d'une révision marquée.
- Journal d'audit : `INSERT`/`SELECT` seuls, `UPDATE` sur deux colonnes, déclencheurs qui refusent
  au propriétaire même ; références sans clé, comme la spec le veut.
- Rôles : service sans DDL ni possession, nommé par la base ; propriétaire non superutilisateur en
  production ; rôle de sauvegarde en lecture seule ; mots de passe lus de l'environnement par
  `psql`, jamais sur une ligne de commande.
- Unicités du §4.4.1 toutes déclarées (adresse sans casse, codes, libellé de calendrier, nom de
  version partiel, triplet de la ligne de coût en `NULLS NOT DISTINCT`).
- Aucun SQL construit par concaténation d'une valeur reçue : les `text()` du service sont des
  constantes, le tri sur une colonne conservée des coûts passe le nom en paramètre lié
  (`core/costs/reading.py:180-183`).
- Listes paginées en SQL (`limit`/`offset`) ; création des partitions sans attente sous verrou
  (`0026`), éprouvée par `test_partitions.py`.

## Couverture

- **Lu en entier** : `backend/src/waterfall/migrations/env.py`, `runner.py`, les 28 fichiers de
  `versions/` dans l'ordre de la chaîne ; `backend/alembic.ini` ; `backend/src/waterfall/schema.py` ;
  les 12 `tables.py` de `core/` ; `platform/database.py`, `audit_columns.py`, `identifiers.py`,
  `decimals.py` ; `deploy/compose/*.sql` (quatre scripts) ; `docs/dev/sql.md`, `docs/dev/python.md`,
  les sections « Migrations » et « Le back et les frontières du noyau » du guide ; spécification
  §3.2, §4.4 et §4.6.2 ; « Tables et migrations » des Conceptions d'EP-03 à EP-07 (EP-06 avec « La
  purge »).
- **Échantillonné** : `tests/test_migrations.py` (tests de chaîne, de descente, des droits, de la
  fonction des partitions), `tests/test_partitions.py` (plan et noms des tests),
  `tests/test_audit_columns.py` (noms des tests seulement) ; `platform/installation.py`, `tasks.py`,
  `restoration.py`, `worker/restore.py`, `restore/task.py` (pour DON-06) ; les requêtes de
  `core/planning`, `core/estimate`, `core/revisions`, `core/exchanges`, `core/history`,
  `core/cost_settings` cherchées par motif (`revision_id ==`, `lineage_id`, `text(`, `delete(`), non
  lues fichier par fichier ; la « Tables et migrations » d'EP-09 (ligne `cost_line` seulement) ;
  `compose.prod.yaml` et `compose.service.yaml` (services PostgreSQL et rôles).
- **Non lu** : `migrations/script.py.mako` ; `tests/test_database_constraints*.py` (cinq fichiers) et
  `test_revision_immutability.py` ; `platform/audit.py`, `uploads.py` au-delà de leurs index ; le
  détail de la requête SQL de `0016` (migration de données d'avant toute installation) ; les
  modules `reading.py` ligne à ligne. `test_schema*` n'existe pas.

---

## Annexe — le schéma final (après `0028`), reconstitué des migrations

Conventions : `PK` clé primaire ; `NN` non nul ; `→` clé étrangère, **en `RESTRICT` sauf mention** ;
`C` collation `"C"` ; « audit » = `created_at`, `updated_at` (`timestamptz NN`), `created_by`,
`updated_by` (`uuid` nul → `user_account`) ; « lv » = `lock_version integer NN DEFAULT 0, CHECK ≥ 0` ;
« borné n » = `char_length BETWEEN 1 AND n` et non blanc (`~ '\S'`). Tous les identifiants sont des
`uuid` sans défaut. Droits = ceux du rôle `<base>_service` (S, I, U, D).

### Plateforme

| Table | Colonnes et contraintes | Index, déclencheurs, droits |
|---|---|---|
| `installation` | `id smallint PK` (`= 1`) ; `default_language text NN` (`fr`,`en`) ; `avatar_max_bytes integer NN` (1..8 388 608) ; `external_backup_max_bytes bigint NN` (1..2⁵³−1) ; `installed_at timestamptz NN`. Ni audit ni lv. | S, U |
| `user_account` | `id PK` ; `last_name`, `first_name`, `email` `text C` nuls ssi anonymisé (noms 1..100, adresse non vide) ; `anonymized_at timestamptz` ; `idp_subject text NN UNIQUE` non vide ; `origin text NN` (`local`,`directory`,`identity_provider`) ; `state text NN DEFAULT 'active'` (`active`,`deactivated`) ; `display_preferences jsonb NN DEFAULT '{}'` ; `avatar bytea` (1..8 Mio) et `avatar_media_type text` (`image/png`,`image/jpeg`), ensemble ; `sessions_closed_at timestamptz` ; `org_node_id → org_node` nul ; lv ; audit. `CHECK anonymized_deactivated`. | `uq_user_account_email_lower` UNIQUE `(lower(email COLLATE "und-x-icu"))` ; `ix (org_node_id)`. S, I, U |
| `audit_entry` | `id PK` ; `occurred_at timestamptz NN` ; `actor_user_id uuid` (sans clé) ; `actor_display_name text C` (nul si pas d'auteur) ; `action text NN` (22 valeurs) ; `object_kind text NN` (10 valeurs) ; `object_id uuid NN` (sans clé) ; `object_label text C` (nul admis pour `backup`, `user`, `revision_abandon`) ; `object_revision_id uuid`, `object_revision_label text` ; `project_id uuid` (sans clé), `project_code text C`, `project_label text` (libellé ssi projet ; code seulement avec projet) ; `params jsonb NN` (objet) ; `correlation_id text C NN` (`^[A-Za-z0-9._-]{1,64}$`). | `ix` sur `occurred_at`, `actor_user_id`, `action`, `object_kind`, `object_id`, `object_label`, `project_id`, `project_code`, `correlation_id` ; `ix_audit_entry_action_rank`, `ix_audit_entry_object_kind_rank` (`array_position`), `ix_audit_entry_actor_order` `((actor_user_id IS NULL), actor_display_name)`. Déclencheurs `audit_entry_refuse_row_change` (UPDATE/DELETE, sauf mise à nul des deux libellés), `audit_entry_refuse_truncate`, `user_account_forget_anonymized`. S, I, `UPDATE (actor_display_name, object_label)` |
| `permission` | `id PK` ; `code text NN UNIQUE` ; `kind text NN` (4) ; `fbs_code text` (forme `FBS-n.n`, nul ssi `irreversible`/`structuring`) ; `position smallint NN UNIQUE ≥ 0`. Écrite par `0005`, `0006`. | S |
| `access_role` | `id PK` ; `label text C NN` (1..100, non unique) ; `is_predefined boolean NN` ; `deleted_at timestamptz` ; lv ; audit. | S, I, U |
| `access_role_permission` | `PK (access_role_id, permission_id)`, → `access_role`, → `permission`. | S, I, D |
| `user_access_role` | `PK (user_account_id, access_role_id)`, → `user_account`, → `access_role`. | `ix (access_role_id)`. S, I, D |
| `background_task` | `id PK` ; `kind text NN` (9) ; `status text NN` (`queued`,`running`,`succeeded`,`failed`) ; `progress smallint NN` 0..100 ; `payload jsonb NN` (objet) ; `result jsonb` ; `problem jsonb` (ssi `failed`) ; `requested_by → user_account` nul ; `correlation_id text NN` (forme) ; `attempts smallint NN ≥ 0` ; `submitted_at NN`, `started_at`, `finished_at` (ssi terminé) `timestamptz`. | `ix (status)`, `ix (requested_by)`. S, I, U |
| `backup` | `id PK` ; `taken_at timestamptz NN` ; `size_bytes bigint NN ≥ 0` ; `verification text NN` (3) ; `origin text NN` (2) ; `is_retained boolean NN` ; `object_key text NN UNIQUE` ; `application_version`, `schema_revision text NN` ; `task_id NN UNIQUE → background_task`. | `ix (taken_at)`. S, I |
| `identity_sync_report` | `task_id PK → background_task` ; `finished_at timestamptz NN` ; `created`, `updated`, `deactivated integer NN ≥ 0` ; `restored integer NN DEFAULT 0 ≥ 0` ; `skipped`, `removed jsonb NN` (tableaux). | `ix (finished_at)`. S, I |
| `file_upload` | `id PK` ; `purpose text NN` (`import`,`external_backup`) ; `filename text NN` 1..255 ; `size_bytes bigint NN ≥ 1` ; `part_size_bytes integer NN` (5..10 Mio) ; `part_count integer NN` 1..10 000 ; `object_key text NN UNIQUE` ; `deposit text` (nul ssi complété) ; `backup_taken_at timestamptz` ; `uploaded_by → user_account` nul ; `created_at`, `expires_at NN`, `completed_at`. | `ix (uploaded_by)`. S, I, U, D (`0024`) |

### Référentiel (toutes : lv + audit, sauf mention ; aucune suppression)

| Table | Colonnes et contraintes | Index, droits |
|---|---|---|
| `reference_setting` | `id smallint PK` (`= 1`) ; `currency_code text NN` (`^[A-Z]{3}$`) ; `company_name text NN` borné 200 ; `probability_bound_1..3`, `severity_bound_1..3 numeric NN` (strictement croissantes par axe, sans borne 0–1) ; `risk_zones text[] NN` (16 valeurs parmi `nominal`,`watch`,`alert`) ; `cost_watch`, `cost_alert`, `schedule_watch`, `schedule_alert numeric NN` (dans ]0,1[, alerte < vigilance) ; `max_weeks_between_reviews smallint NN` 1..104. | S, U |
| `duration_unit` | `id smallint PK` (`= 1`) ; `hours_per_day`, `hours_per_week`, `days_per_month numeric NN > 0`. | S, I, U |
| `cost_type` | `id PK` ; `code text C NN UNIQUE` borné 20 ; `label text C NN` borné 200 ; `kind text NN` (`labor`,`non_labor`,`provision`) ; `is_active boolean NN`. | S, I, U |
| `cost_category` | `id PK` ; `code C UNIQUE` borné 20 ; `label C` borné 200 ; `accounting_code C UNIQUE` borné 20 ; `cost_type_id NN → cost_type` ; `is_active`. | `ix (cost_type_id)`. S, I, U |
| `hourly_rate` | `id PK` ; `cost_category_id NN → cost_category` ; `year smallint NN` 2000..2100 ; `amount numeric(12,2) NN ≥ 0.01` ; `UNIQUE (cost_category_id, year)`. | S, I, U |
| `org_node` | `id PK` ; `code C UNIQUE` borné 20 ; `label C` borné 200 ; `parent_id → org_node` nul, `CHECK parent_id <> id` ; `is_active`. | `ix (parent_id)`. S, I, U |
| `calendar` | `id PK` ; `label C NN UNIQUE` borné 200 ; `monday`…`sunday numeric(4,2) NN` 0..24 ; `is_default`, `is_active boolean NN`, `CHECK is_active OR NOT is_default`. | `uq_calendar_default` UNIQUE `(is_default) WHERE is_default`. S, I, U |
| `resource_role` | `id PK` ; `code C UNIQUE` borné 20 ; `label C` borné 200 ; `org_node_id NN → org_node` ; `cost_category_id NN → cost_category` ; `calendar_id NN → calendar` ; `monthly_hours`, `headcount numeric NN ≥ 0` ; `is_active`. | `ix` sur chacune des trois clés. S, I, U |
| `actual_cost_mapping` | `id smallint PK` (`= 1`) ; lv ; audit. | S, I, U |
| `actual_cost_mapping_label` | `id PK` ; `kind text NN` (`read`,`kept`) ; `"column" text` (5 valeurs, non nul ssi `read`) ; `position smallint NN` ; `label text NN` borné 200 ; `folded text NN UNIQUE`. Ni audit, ni lv, ni clé vers `actual_cost_mapping`. | S, I, U, D |

### Projet

| Table | Colonnes et contraintes | Index, déclencheurs, droits |
|---|---|---|
| `project` | `id PK` ; `label C NN` borné 300 ; `code C UNIQUE` nul, borné 50, sans `/` ; `description text` ; `client C` nul, borné 300 ; `state text NN` (6 états) ; `inflation_rate`, `win_probability numeric(5,4) NN` 0..1 ; `order_received_on date` ; `reference_revision_id`, `current_revision_id → revision(id)` nuls ; `contributors_lock_version`, `work_breakdown_lock_version integer NN DEFAULT 0 ≥ 0` ; lv ; audit. | `ix (reference_revision_id)`, `ix (current_revision_id)`. S, I, U |
| `project_state_transition` | `id PK` ; `project_id NN → project` ; `from_state text` nul, `to_state text NN` (6 états) ; `occurred_at timestamptz NN` ; `actor_user_id → user_account` nul ; `reason text`. | `ix (project_id, occurred_at)`. S, I |
| `contributor` | `PK (project_id, user_account_id)`, → `project`, → `user_account` ; `kind text NN` (`project_manager`,`contributor`). Ni audit ni lv (compteur sur `project`). | `ix (user_account_id)`. S, I, U, D |
| `subproject` | `id PK` ; `project_id NN → project` ; `code C NN` borné 31, sans `: \ / ? * [ ]` ; `label C NN` borné 300 ; `UNIQUE (project_id, code)` ; `UNIQUE (id, project_id)` (`0025`) ; lv ; audit. | S, I, U, D |
| `work_package` | `id PK` ; `project_id NN → project` ; `label C NN` borné 300 ; `position integer NN ≥ 0` ; `deleted_at timestamptz` ; audit (sans lv). | `uq_work_package_position` UNIQUE `(project_id, position) WHERE deleted_at IS NULL`. S, I, U, D |
| `order_item` | `id PK` ; `project_id NN → project` ; `work_package_id NN → work_package` ; `label`, `position`, `deleted_at`, audit. | `uq_order_item_position` UNIQUE `(work_package_id, position) WHERE deleted_at IS NULL` ; `ix (project_id)`. S, I, U, D |
| `deliverable` | `id PK` ; `project_id NN → project` ; `order_item_id NN → order_item` ; `label`, `position`, audit. | `uq_deliverable_position` UNIQUE `(order_item_id, position)` ; `ix (project_id)`. S, I, U, D |
| `revision` | `id PK` ; `project_id NN → project` ; `status text NN` (`draft`,`marked`) ; `version_name C` nul, borné 100, non nul si marquée ; `description text` ; `marked_at timestamptz` (ssi marquée) ; `reference_year smallint NN` 2000..2100 ; `is_reference boolean NN` ; `lineage_id uuid NN` ; `source_revision_id` nul, clé `(project_id, source_revision_id) → revision(project_id, id)`, `<> id` ; `inflation_rate`, `win_probability numeric(5,4)` nuls, sans borne (`0025`) ; `UNIQUE (project_id, id)` ; lv ; audit. | `uq_revision_draft` UNIQUE `(project_id) WHERE status = 'draft'` ; `uq_revision_version_name` UNIQUE `(project_id, version_name) WHERE status = 'marked'` ; `uq_revision_reference` UNIQUE `(project_id) WHERE is_reference`. Déclencheurs `revision_refuse_marked_change` (marquée : seuls `is_reference`, `lock_version`, `updated_at`, `updated_by` changent ; pas de suppression), `revision_refuse_truncate`. S, I, U, D |
| `timeline` | `id PK` ; `project_id NN → project` ; `label C NN` borné 200 (non unique) ; audit. | `ix (project_id)`. S, I, U, D |
| `tracking_entry` | `id PK` ; `project_id NN → project` ; `lineage_id uuid NN` ; `kind text NN` (`timeline`,`milestone_tracking`) ; `timeline_id → timeline` **`CASCADE`**, non nul ssi `kind = 'timeline'` ; `UNIQUE NULLS NOT DISTINCT (lineage_id, kind, timeline_id)` ; audit. | `ix (project_id)`, `ix (timeline_id)`. S, I, U, D |
| `import_report` | `id PK` ; `project_id NN → project` ; `kind text NN` (4) ; `filename text NN` 1..255 ; `upload_id uuid NN UNIQUE` (sans clé) ; `object_key text NN` ; `structure_id`, `revision_id uuid` nuls (sans clé) ; `period_from`, `period_to date` ; `status text NN` (8) ; `report jsonb` (objet ou nul) ; `task_id uuid` (sans clé) ; `requested_by → user_account` nul ; `created_at NN`, `analysed_at`, `expires_at` (ssi `analysed`,`applying`,`applied`,`abandoned`,`expired`), `applied_at` ; `duration_rule text` (`keep_durations`,`keep_dates` ; seulement pour `ms_project_schedule`) (`0028`). | `ix (project_id)`. S, I, U, D |
| `undo_entry` | `id PK` ; `(project_id, revision_id) → revision(project_id, id)` ; `user_account_id NN → user_account` ; `session_id text NN` ; `rank integer NN` ; `kind text NN` (14) ; `node_ids uuid[] NN` ; `before`, `after jsonb NN` ; `undone boolean NN` ; `created_at NN` ; `UNIQUE (revision_id, user_account_id, session_id, rank)`. | S, I, U, D |
| `paste_plan` | `id PK` ; `(project_id, revision_id) → revision(project_id, id)` ; `structure_id uuid NN` (sans clé) ; `user_account_id NN → user_account` ; `target_node_id uuid NN` (sans clé) ; `target_column text NN` (28) ; `rows jsonb NN` ; `structure_lock_version integer NN ≥ 0` ; `created_at`, `expires_at NN`. Aucun index hors la clé. | S, I, U, D |
| `cost_import` | `id PK` ; `project_id NN → project` ; `import_report_id NN UNIQUE → import_report` ; `imported_at timestamptz NN` ; `requested_by NN → user_account` ; `period_from`, `period_to date` (`from <= to`) ; `created_count`, `updated_count`, `unchanged_count`, `rejected_count integer NN ≥ 0` ; `passthrough_columns jsonb NN` (tableau de textes). | `ix (project_id, imported_at)`. S, I |
| `cost_line` | `id PK` ; `project_id NN → project` ; `subproject_id` nul, clé `(project_id, subproject_id) → subproject(project_id, id)` ; `subproject_code C` nul ≤ 50 (non nul si imputée) ; `document_number C NN` borné 200 ; `document_item C` nul ; `document_date date NN` ; `amount numeric(14,2) NN` (signé) ; `is_in_tracked_scope boolean NN` ; `excluded_reason C` (nul si suivie) ; `passthrough jsonb NN` (objet de textes) ; `last_import_id NN → cost_import` ; audit (sans lv) ; `UNIQUE NULLS NOT DISTINCT (project_id, document_number, document_item)`. | `ix (project_id, document_date)`, `ix (subproject_id, project_id)`, `ix (subproject_code, project_id)`. S, I, U |

### Révisionné — `PARTITION BY LIST (project_id)`, une partition `<table>_p_<uuid sans tirets>` par projet

Chaque table porte `<table>_refuse_marked_change` (`BEFORE INSERT OR UPDATE OR DELETE`, ligne : la
révision est lue sous `FOR KEY SHARE`, refus si `marked`) et `<table>_refuse_truncate` (parent et
chaque partition).

| Table | Colonnes et contraintes | Index, droits |
|---|---|---|
| `cost_structure` | `PK (project_id, id)` ; `revision_id NN`, clé `(project_id, revision_id) → revision(project_id, id)` ; `kind text NN` (`main`) ; `label C NN` borné 300 ; `is_merged boolean NN` ; `lineage_id uuid NN` ; `planning_start_on date`, `scheduled_at timestamptz` nuls (`0022`, remplis par `0023`) ; `UNIQUE (project_id, id, revision_id)` ; lv ; audit. | `ix (project_id, revision_id)` ; `uq_cost_structure_main` UNIQUE `(project_id, revision_id) WHERE kind = 'main'`. S, I, U, D |
| `node` | `PK (project_id, id)` ; `revision_id`, `structure_id NN`, clé `(project_id, structure_id, revision_id) → cost_structure(project_id, id, revision_id)` **`CASCADE`** ; `lineage_id uuid NN` (ni unique ni indexé) ; `kind text NN` (`task`,`estimate_line`) ; `parent_id` nul, clé `(project_id, parent_id, structure_id) → node(project_id, id, structure_id)` **`CASCADE`** ; `rank integer NN ≥ 1` ; `origin_risk_id uuid` (sans clé, EP-08) ; lv ; audit ; `UNIQUE (project_id, id, kind)` ; `UNIQUE (id, project_id, structure_id)` ; `UNIQUE NULLS NOT DISTINCT (structure_id, parent_id, kind, rank, project_id) DEFERRABLE INITIALLY IMMEDIATE`. | `ix (revision_id)`, `ix (parent_id)`. S, I, U, D |
| `task` | `PK (project_id, node_id)` ; `structure_id NN` ; `kind text NN` (`= 'task'`) ; clés `(project_id, node_id, kind) → node(project_id, id, kind)` et `(node_id, project_id, structure_id) → node(id, project_id, structure_id)`, toutes deux **`CASCADE`** ; `label C NN` borné 300 ; `description text` ; `scheduling_mode text NN` (2) ; `duration_value numeric NN ≥ 0`, `duration_unit text NN` (10) ; `start_date`, `finish_date date NN` ; `start_hours`, `finish_hours numeric NN` 0..24 ; `progress text NN` (3) ; `started_on` (non nul si démarrée), `completed_on` (ssi terminée) `date` ; `external_id text ≤ 200` ; `order_item_id → order_item(id)`, `work_package_id → work_package(id)` nuls, jamais tous deux ; `total_float_days numeric` nul ; `is_critical boolean NN`. Sans audit ni lv (ceux du nœud). | `uq_task_order_item` UNIQUE `(project_id, structure_id, order_item_id) WHERE … IS NOT NULL` ; `uq_task_work_package` de même ; `ix (order_item_id)`, `ix (work_package_id)`. S, I, U, D |
| `task_link` | `PK (project_id, id)` ; `revision_id`, `structure_id NN`, clé vers `cost_structure` **`CASCADE`** ; `predecessor_id`, `successor_id NN`, clés `(x, project_id, structure_id) → node(id, project_id, structure_id)` **`CASCADE`**, `predecessor_id <> successor_id` ; `link_type text NN` (4) ; `lag_value numeric NN` ; `lag_unit text NN` (11) ; `in_conflict boolean NN` ; `UNIQUE (structure_id, predecessor_id, successor_id, project_id)`. Sans audit. | `ix (predecessor_id)`, `ix (successor_id)`. S, I, U, D |
| `estimate_line` | `PK (project_id, node_id)` ; `kind text NN` (`= 'estimate_line'`), clé `(project_id, node_id, kind) → node` **`CASCADE`** ; `label C NN` borné 300 ; `cost_category_id NN → cost_category` ; `resource_role_id → resource_role` nul ; `quantity numeric(14,4) NN ≥ 0` ; `hours numeric(12,2) ≥ 0` (ssi rôle) ; `unit_disbursement numeric(14,2) ≥ 0` (ssi sans rôle) ; `payment_delay_days integer NN ≥ 0` ; `subproject_id` nul, clé `(project_id, subproject_id) → subproject(project_id, id)` ; `reference_quantity (14,4)`, `reference_hours (12,2)`, `reference_unit_disbursement (14,2)` nuls ; `base_amount`, `reestimated_amount numeric(14,2) NN` ; `budgeted_amount numeric(14,2)` nul ; `consumption_year smallint NN` 2000..2100 ; `previous_quantity (14,4)`, `previous_hours (12,2)`, `previous_unit_disbursement (14,2)`, `previous_reestimated_amount (14,2)` nuls ≥ 0, `reestimated_at timestamptz`, `remaining_reason text` (`0027`) ; lv ; audit. | `ix (cost_category_id)`, `ix (resource_role_id)`, `ix (subproject_id)`. S, I, U, D |
| `revision_rate` | `PK (project_id, id)` ; `revision_id NN`, clé `(project_id, revision_id) → revision` ; `cost_category_id uuid NN` (sans clé) ; `amount numeric(12,2) NN ≥ 0.01` ; `origin text NN` (`reference`,`projected`) ; `UNIQUE (revision_id, cost_category_id, project_id)`. Sans audit ni lv. | S, I, U, D |
| `revision_role` | `PK (project_id, id)` ; `revision_id` → `revision` (composite) ; `resource_role_id uuid NN` ; `code`, `label C NN` ; `org_node_id uuid NN`, `org_node_label C` ; `cost_category_id uuid NN`, `cost_category_label C` ; `calendar_id uuid NN`, `calendar_label C` ; `monthly_hours`, `headcount numeric NN` ; `is_active` ; audit recopié (sans clé) ; `lock_version integer NN ≥ 0` (sans défaut) ; `UNIQUE (revision_id, resource_role_id, project_id)`. | S, I |
| `revision_calendar` | de même ; `calendar_id uuid NN` ; `label C` ; `monday`…`sunday numeric(4,2) NN` ; `is_default` ; `UNIQUE (revision_id, calendar_id, project_id)`. | S, I |
| `revision_category` | de même ; `cost_category_id uuid NN` ; `code`, `label C` ; `cost_type_id uuid NN`, `cost_type_label C`, `cost_type_kind text NN` (3), `cost_type_is_active boolean NN` ; `accounting_code C` ; `UNIQUE (revision_id, cost_category_id, project_id)`. | S, I |

### Fonctions, extension, rôles

- `create_project_partitions(uuid)` : `SECURITY DEFINER`, `search_path = pg_catalog, pg_temp`,
  `EXECUTE` au seul rôle du service (`0020`), dernière version en `0026` (verrou consultatif
  `4100010`, verrous `NOWAIT` pris d'un coup, `CREATE TABLE … (LIKE …)` puis `ATTACH PARTITION`,
  tables lues dans le catalogue).
- Fonctions de déclencheur : `audit_entry_refuse_change`, `user_account_forget_anonymized`,
  `revision_refuse_marked_change`, `revision_refuse_truncate`, et pour chacune des neuf tables
  révisionnées `<table>_refuse_marked_change` et `<table>_refuse_truncate`.
- Extension `unaccent` (`0004`).
- Rôles : le propriétaire (`waterfall`, non superutilisateur en production ; superutilisateur du
  serveur sur les Compose de service et de démonstration) ; `<base>_service` (créé `NOLOGIN` par
  `0002` ou par `waterfall-database.sql`, mot de passe par `service-database-role.sql`) ;
  `waterfall_backup` (`pg_read_all_data`) ; `keycloak` (sa base).
- Chaîne : `0001 ← 0002 ← … ← 0028`, sans branche ; migrations de données : `0005`, `0006`
  (catalogue), `0016` (comptes rendus), `0023` (structures, garde coupée pour l'instruction) ;
  migrations de droits seuls : `0002`, `0012`, `0024`.

# Revue — socle du back : plateforme, coquille de l'API, worker, témoin, restauration

Commit `29785cc` (`main`). Chemins relatifs à `backend/` sauf mention.

## Synthèse

Le socle est solide, et nettement plus soigné que la moyenne : je n'ai trouvé **aucun constat
bloquant**. L'authentification (signature, `iss`, `aud`, `exp`, RS256 imposé, cache et rotation des
clés, Keycloak injoignable, compte désactivé lu à chaque requête, sessions révoquées) tient de bout
en bout et ses tests prouvent ce qu'ils annoncent. La file est « au moins une fois » côté Redis et
« exactement une fois » côté base (travail et fin de tâche dans une transaction, verrou consultatif,
trois tentatives, redépôt depuis la table) ; les clés du stockage sont toutes engendrées par le
serveur, aucune URL présignée, aucun argument de sous-processus ne vient d'une entrée utilisateur.
Les frontières tiennent (aucun import de `core`/`api`/`worker` dans `platform`, aucun commentaire
d'exemption dans le périmètre). Seules `/health` et `/installation` sont sans authentification
(132 routes relues par script), comme le contrat le déclare (`security: []`).

Ce qui inquiète est concentré sur la **restauration** : deux engagements de la décision de contrat
#679 n'ont pas de réalisation dans le service (le dépôt désigné n'est pas gardé de la purge ; le
motif d'échec n'est pas celui du contrat), une restauration s'abandonne en maintenance pour une
panne brève de Keycloak alors qu'aucune base n'a été touchée, et les droits d'exécution de la
fonction des partitions ne sont pas rendus après restauration. Le reste est mineur ou latent.

Déjà connus, lus et **non repris** ci-dessous (tous dans `docs/roadmap/EP-13-exploitation.md`, sauf
mention) : #1035 (409 nommés de `startBackup`/`downloadBackup`/`startRestore`, sauvegarde non
vérifiée ou en cours non refusées), #896 (coûts de la tâche `backup`, archive orpheline), #897
(flux de `downloadBackup`), #1016 (maintenance laissée par l'abandon — voir BSO-05 pour une
précision), #956 (Redis sans persistance), #1014/#2229 (écriture en vol), #934, #928, #809, #924,
#908, #989, #993, #998, #2231, #2241, #3172 (EP-26). L'API n'est pas exposée (Caddy ne sert que le
front et Keycloak, `deploy/compose/Caddyfile.prod`) : l'absence de CORS, d'en-têtes de sécurité et de
borne de corps dans l'API n'est donc pas un constat ; à noter seulement que FastAPI lit le corps
JSON avant d'évaluer `Requires` (voulu, `api/evaluation.py:5-9`).

## Constats bloquants

Aucun.

## Constats majeurs

### BSO-01 — Le dépôt qu'une restauration acceptée désigne n'est pas gardé de la purge

- **Issue** : #4471 (EP-39), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec BEX-06.
- **Où** : `src/waterfall/core/exchanges/interface/purge.py:177-203` (`_deposits_expired`) et
  `:249-269` (`_named_uploads`), lancés par `src/waterfall/worker/main.py:203-232` (`_purge`) ;
  `src/waterfall/api/restores.py:90-102` (la charge de la tâche ne fait que nommer `object_key`) ;
  `src/waterfall/restore/task.py:102-105`, `src/waterfall/restore/runner.py:182-187` et `:164-171`.
- **Quoi** : la purge supprime la ligne `file_upload` et l'objet `uploads/<id>` dès
  `expires_at <= now`, sans regarder si une tâche `restore` en file ou en cours le désigne, alors
  que le contrat promet : « The upload that an accepted restore designates is kept until the end of
  its task, even beyond its day (WF-DAT-0120) » (`docs/api/paths/platform.yaml:505-507`,
  `docs/api/DECISIONS.md:5030-5032`, décision #679). Aucun code ni test ne porte cette garde
  (`grep` de « restore » dans `core/exchanges` : rien ; `_purge` ne lit pas non plus la maintenance).
- **Scénario** : dépôt achevé lundi 10 h 00 (expire mardi 10 h 00). Mardi 9 h 30, `startRestore`
  l'accepte (`completed_upload` le trouve non expiré). La première tentative télécharge l'archive,
  pose la maintenance, puis est interrompue (Keycloak qui ne répond pas à `close_sessions`, ou
  `apply_realm` qui dépasse ses 600 s). À 10 h 00 la purge (toutes les dix minutes) supprime l'objet.
  La reprise retélécharge l'archive : `MissingObjectError` → `NotFoundError`, la maintenance étant
  tenue par cette tâche l'erreur est relancée (`runner.py:185-187`), trois fois, puis la
  restauration est abandonnée, plateforme en maintenance. Variante sans maintenance : le service
  `restore` arrêté ou occupé au-delà de l'échéance, la tâche échoue `NOT_FOUND` alors que la requête
  avait été acceptée. (Entre le remplacement et la réinscription, la purge échoue faute de droits
  du rôle du service et ne supprime rien ; avant le remplacement et après la réinscription, elle
  supprime.)
- **Proposition** : dans `_deposits_expired` et `_named_uploads`, épargner un dépôt qu'une tâche
  `restore` `queued`/`running` nomme (`payload->>'upload_id'`), et faire sauter `_purge` tant que la
  maintenance est posée (la tâche peut ne plus avoir de ligne). Test : un dépôt expiré désigné par
  une restauration en file survit à `purge`, puis est purgé une fois la tâche finie ; un second
  test rejoue une restauration interrompue après l'échéance du dépôt et la voit aboutir.
- **Confiance** : confirmé (chemin lu de la requête à la purge et à la reprise ; non exécuté).

### BSO-02 — Une archive déposée qui ne passe pas la vérification échoue par un autre code que celui du contrat

- **Issue** : #4470 (EP-39), ouverte le 2026-11-21.
- **Où** : `src/waterfall/worker/restore.py:91`, `:98`, `:105`, `:108` (`extracted`) ;
  `tests/test_uploads.py:507` l'affirme.
- **Quoi** : la tâche `restore` échoue avec `FILE_FORMAT_UNREADABLE` (422, sans paramètre) quand
  l'archive déposée ne se relit pas (empreinte, `pg_restore --list`, base manquante, date du
  manifeste entier différente). Le contrat dit `problem` à `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` à `backup_verified` (`docs/api/paths/platform.yaml:499-505`), et la
  décision #679 écarte nommément `FILE_FORMAT_UNREADABLE` parce qu'il « n'aurait pas dit la vraie
  cause » (`docs/api/DECISIONS.md:5040-5042`) — c'est le défaut n° 10 de `python.md`. La conception
  d'EP-03 dit encore l'ancien code (`docs/roadmap/EP-03-comptes-et-habilitations.md:777-778`) : elle
  contredit le contrat, qui fait foi.
- **Scénario** : un administrateur dépose une archive altérée pendant sa copie, confirme la date,
  lance la restauration ; la tâche échoue avant la maintenance et l'écran lit sur
  `getBackgroundTask` « format illisible » au lieu de la condition `backup_verified` que le
  catalogue sait dire.
- **Proposition** : faire lever par `extracted`, pour ces quatre cas, un `ConflictError(
  STATE_FORBIDS_OPERATION, {"missing_condition": "backup_verified"})` (en gardant
  `BACKUP_FROM_NEWER_VERSION` à part), corriger la phrase de la conception d'EP-03, et retourner
  l'assertion de `test_uploads.py:507` et de `test_restoration.py:477-502`. Portée faible (un
  message), mais c'est un écart au contrat que #1035 ne nomme pas (il ne parle que des 409 des
  requêtes).
- **Confiance** : confirmé.

## Constats mineurs

### BSO-03 — Après une restauration, `create_project_partitions` redevient exécutable par `PUBLIC`

- **Issue** : #4475 (EP-39), ouverte le 2026-11-21, avec BSO-05, DON-06.
- **Où** : `src/waterfall/worker/restore.py:141-142` (`--no-owner --no-privileges`) ;
  `src/waterfall/platform/restoration.py:49-64` (`SERVICE_GRANTS` ne lit que `pg_class.relacl` et
  `pg_attribute.attacl`) et `:181-185` ; `src/waterfall/migrations/versions/0020_projects_and_revisions.py:51-53`
  et `:85`.
- **Quoi** : la migration retire `EXECUTE` à `PUBLIC` et le donne au seul rôle du service ; la
  restauration recrée la fonction sans ses droits et ne rend que ceux des tables et des colonnes.
  La fonction `SECURITY DEFINER` retrouve donc le droit par défaut de PostgreSQL (`EXECUTE` à
  `PUBLIC`) : le service continue de fonctionner — par `PUBLIC` —, mais l'invariant que
  `tests/test_migrations.py:455-480` affirme (« nothing else may: not PUBLIC », WF-DAT-0050-A, #701)
  ne tient plus après la première restauration. Le rôle de la sauvegarde (`pg_read_all_data`, donc
  `USAGE` sur le schéma) peut alors faire créer des partitions par le propriétaire.
- **Scénario** : restauration d'une sauvegarde de révision ≥ 0020 ; aucune migration ne rejoue le
  `REVOKE` (0025 et 0026 font `CREATE OR REPLACE`, « its grants kept »).
- **Proposition** : garder aussi les droits des fonctions (`pg_proc.proacl`, `REVOKE … FROM PUBLIC`
  compris) dans `keep_grants`/`end_keeping`. Test : la requête de `test_migrations.py:463-470`
  rejouée après `test_restoration.py:319` ; aujourd'hui seul `has_table_privilege` y est vérifié
  (`tests/test_restoration.py:343`).
- **Confiance** : plausible — déduit du code et de la sémantique de `pg_restore -x` ; je n'ai pas
  exécuté de restauration.

### BSO-04 — Le dépôt d'une tâche part à la libération d'un point de sauvegarde, pas à la validation

- **Issue** : #4476 (EP-39), ouverte le 2026-11-21, avec BEX-04.
- **Où** : `src/waterfall/platform/tasks.py:175-181` (`event.listen(session, "after_commit", deposit, once=True)`).
- **Quoi** : SQLAlchemy émet `after_commit` aussi quand une transaction imbriquée se valide
  (`.venv/…/sqlalchemy/orm/session.py:1414-1422`). `worker/identity_sync.py:273-300` le sait et
  s'en garde (`get_nested_transaction() is not None`) ; `submit` non. Un `begin_nested()` qui se
  ferme entre `submit` et la validation de la requête déposerait l'identifiant avant que la ligne
  existe : un worker la lirait absente (`worker/runner.py:245-246`), acquitterait et supprimerait
  l'entrée, et la tâche attendrait le redépôt (60 s). Latent : j'ai relu les neuf appelants de
  `submit`, aucun ne ferme de point de sauvegarde après lui (`open_import` le fait avant,
  `_inserted` puis `submit`, `core/exchanges/interface/imports.py:453` et `:458`).
- **Proposition** : employer dans `submit` la garde de `identity_sync.after_commit` (à remonter
  dans `platform`). Test : `submit`, puis un `begin_nested()` vide, `queue.waiting()` reste vide
  jusqu'à la validation.
- **Confiance** : confirmé pour le mécanisme, sans chemin qui le déclenche aujourd'hui.

### BSO-05 — Une panne brève de Keycloak à la pose de la maintenance abandonne la restauration, bases intactes

- **Issue** : #4475 (EP-39), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec BSO-03, DON-06.
- **Où** : `src/waterfall/restore/task.py:111-114` (`hold` puis `close_sessions`),
  `src/waterfall/restore/runner.py:150-173` et `:182-187`, `src/waterfall/worker/runner.py:135`
  (`claim_after = 30.0`, repris tel quel par `restore/main.py`).
- **Quoi** : la maintenance est posée avant le premier appel à Keycloak ; s'il échoue (503), la
  tentative est « interrompue », reprise dès que l'entrée a trente secondes, et abandonnée à la
  troisième : environ 90 s d'indisponibilité de Keycloak laissent la plateforme en maintenance
  jusqu'à une levée à la main, alors que rien n'a été gardé ni remplacé.
- **Proposition** : tant que rien n'est gardé (`kept_for` nul et première pose), lever la
  maintenance et faire échouer la tâche par `COMPONENT_UNAVAILABLE`, comme avant la maintenance ;
  sinon espacer les reprises. Test : `close_sessions` qui lève à la première tentative → tâche
  `failed`, maintenance absente, bases inchangées.
- **Confiance** : confirmé. **Déjà connu en partie (#1016, EP-13)** : l'issue traite la maintenance
  laissée par un abandon ; elle ne dit pas qu'un échec précoce et réversible y mène en 90 s.

### BSO-06 — Aucune borne de durée ni de verrou sur les sessions du service, pool laissé à ses défauts

- **Issue** : #4477 (EP-39), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `src/waterfall/platform/database.py:151-155`.
- **Quoi** : ni `statement_timeout`, ni `lock_timeout`, ni `idle_in_transaction_session_timeout`,
  et un pool de 5 + 10 connexions (défauts de SQLAlchemy) pour 40 fils d'exécution et trois
  transactions courtes par requête (`identify`, `acting`, la route). Une requête qui attend un
  verrou (le cas #924, ou une ligne tenue par une tâche longue du worker) tient un fil et une
  connexion sans limite ; au-delà de quinze, chaque requête attend trente secondes puis rend 500,
  `/health` continuant de dire `ok`. L'objectif du §4.6.2 se mesure à cinquante utilisateurs
  simultanés.
- **Proposition** : poser `lock_timeout` et `statement_timeout` dans les `options` de connexion de
  l'API (pas du worker ni de la restauration), dimensionner le pool par réglage, et rendre
  l'épuisement en 503 `COMPONENT_UNAVAILABLE`. Coût faible ; à mesurer avec la charge d'EP-26.
- **Confiance** : plausible — pas de mesure sous charge.

### BSO-07 — La purge planifiée ignore la maintenance, et sa lecture préalable sort par une trace nue

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-13 (commit `0258a2d94`,
  US-2830/L2, #3963), la commande `waterfall-worker purge` n'existe plus : la purge est la tâche
  `purge` du worker. `Worker.handle` ne lance aucune tâche tant que la maintenance est tenue, et une
  exception de la tâche — lecture préalable comprise, faite dans `PurgeTask.__call__` — est attrapée
  par `Worker.execute` et journalisée par structlog (`task.failed`).
- **Où** : `src/waterfall/worker/main.py:213-227` (`_stored` appelé hors du `try`, ligne 215 ;
  seul `UnavailableError` y est attrapé, ligne 198).
- **Quoi** : pendant une restauration, `waterfall-worker purge` s'exécute contre la base en cours
  de remplacement (schéma vide, ou tables sans droits du service) : l'erreur de `_stored` traverse
  `_purge` et `main` en trace Python sur la sortie d'erreur, hors de structlog et de son masquage
  (WF-OBS-0020), au lieu de `purge.failed`. Même défaut si PostgreSQL est injoignable à ce moment.
- **Proposition** : englober `_stored` dans le `try` de `_purge`, et ne rien purger tant que
  `Maintenance.current()` n'est pas nul (lié à BSO-01). Test : `_purge` sur une base sans la table
  `file_upload` rend 1 et journalise `purge.failed`.
- **Confiance** : confirmé (lecture) ; non exécuté.

### BSO-08 — Le jeton du compte de service se demande verrou tenu, sans mémoire de l'échec

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — dit « plausible » par la revue :
  il faut un Keycloak qui accepte les connexions sans répondre et plusieurs appels d'administration
  simultanés ; le gain n'est pas mesurable.
- **Où** : `src/waterfall/platform/keycloak_admin.py:525-543` (`_service_token`).
- **Quoi** : l'appel HTTP (dix secondes de délai) se fait sous `_token_lock` ; quand Keycloak
  accepte les connexions sans répondre, les requêtes qui ont besoin du jeton (première requête
  d'une personne de l'annuaire, `closeMySessions`, routes des comptes) s'enfilent et tentent chacune
  à leur tour, la dernière attendant N × 10 s en tenant son fil. Le client des clés du royaume, lui,
  borne l'attente à une seconde et redonne le dernier échec (`platform/keycloak.py:215-231` et `:248-252`, #674).
- **Proposition** : même traitement que les clés (attente bornée du verrou, échec redonné pendant
  `KEYS_REREAD_SECONDS`). Test à l'image de
  `test_a_request_whose_key_is_not_held_waits_a_while_for_the_keys_being_read`.
- **Confiance** : plausible — demande plusieurs appels d'administration simultanés pendant la panne.

## Points forts

- **Jeton** : `algorithms=("RS256",)`, `require` de `exp/iat/iss/aud/sub`, clés d'usage `enc`
  écartées, signature jugée avant l'expiration, clés relues au plus toutes les 10 s et vieillies à
  300 s, clés tenues servies pendant une panne, 503 et non 401 quand la clé manque
  (`platform/keycloak.py`) ; chaque cas a son test (`tests/test_api_authentication.py`, 37 tests).
- **Compte** : lu par `idp_subject` à chaque requête, désactivé → 401, connexion antérieure à la
  fermeture des sessions → `SESSION_REVOKED`, aucun appel à Keycloak sous transaction (#669).
- **Worker** : travail et fin de tâche validés ensemble, tentative comptée à part, `UndoneError`,
  verrou consultatif relu par la restauration (`await_runs`), balayage `XAUTOCLAIM` qui avance ;
  `tests/test_worker.py` éprouve l'arrêt en cours de tâche, les trois tentatives, la perte du flux,
  le Redis muet (j'ai vérifié que `redis.from_url` n'hérite d'aucune reprise : la borne d'une seconde tient).
- **Sous-processus** : `pg_dump`/`pg_restore` par chemin absolu, arguments constants, adresse par
  fichier de service et `PGPASSWORD`, rien sur la ligne de commande (`worker/backup.py:84-136`) ;
  archives lues par `extractfile` sous des noms choisis par le serveur, `mode="r:"`, manifeste borné
  en profondeur.
- **Téléversement** : morceau borné à 10 Mio avant et pendant la lecture, après l'habilitation ;
  clés `uploads/<uuid>` ; achèvement relu sous verrou.
- **Erreurs et journaux** : une seule enveloppe, 500 sans détail, corrélation reçue filtrée par
  `[A-Za-z0-9._-]{1,64}` et contrainte en base, secrets retirés par nom et masqués par valeur,
  aucun jeton ni adresse électronique journalisé dans le périmètre.
- **Audit** : inscription dans la transaction de l'acte, secret refusé par nom à toute profondeur.
- **Réglages** : aucun secret n'a de valeur par défaut ; l'erreur nomme la variable, jamais la valeur.
- Tous les codes levés par `…Error("CODE")` résolubles statiquement existent dans `ErrorCode`
  (script) ; aucun test du périmètre sans assertion (script, 26 fichiers).

## Couverture

- **Lu en entier** : `src/waterfall/platform/` (21 fichiers) ; `api/app.py`, `main.py`,
  `middleware.py`, `authentication.py`, `problems.py`, `queries.py`, `actors.py`, `uploads.py`,
  `tasks.py`, `maintenance.py`, `system.py`, `restores.py`, `backups.py` ; `worker/` (8 fichiers) ;
  `restore/` (5 fichiers) ; `bootstrap.py` ; `schema.py` ; `pyproject.toml` ; `alembic.ini`.
  En appui, hors périmètre : `core/backups/interface.py`, `api/evaluation.py` (tête),
  la purge de `core/exchanges/interface/purge.py` (lignes 92-270), les migrations 0020 et 0026
  (droits et fonction), `deploy/compose/Caddyfile.prod`, `deploy/compose/README.md` (restauration).
- **Échantillonné** : `witness/` — lus `main.py`, `loader.py`, `description.py`, `filling.py`,
  `chronology.py` ; les 19 autres fichiers (tranches par objet) non lus. Tests : `test_worker.py`
  en entier, `test_api_authentication.py` (tête et cas des clés), listes des tests de
  `test_restore_service.py`, `test_restoration.py`, `test_uploads.py`, `test_backups.py`,
  `test_boundaries.py` ; contrôle par script de la présence d'assertions sur 26 fichiers.
- **Non lu** : `test_witness*.py`, `test_database_constraints*.py`, `test_registries.py`,
  `test_api_problems.py`, `test_platform_*.py`, `test_audit_*.py` au-delà de leurs noms ; les tests
  `test_keycloak_*.py` ; `keycloak_admin.py` n'a été jugé que par lecture (aucun Keycloak lancé).
  Rien n'a été exécuté : ni tests, ni restauration, ni charge.

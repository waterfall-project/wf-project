# Revue — projets, révisions et cycle de vie (EP-04, back)

Commit relu : `29785cc` (`main`). Lecture seule ; aucun test lancé (règle du cahier) : « confirmé »
veut dire ici « chemin lu de bout en bout dans le code, la migration et le contrat », non « rejoué ».
Les chemins sont relatifs à `backend/src/waterfall/` sauf mention.

## Synthèse

Le domaine est solide, et nettement au-dessus de ce qu'on attend d'un premier EPIC révisionné.
L'immuabilité d'une révision marquée est tenue **par la base**, table par table (un déclencheur
`BEFORE INSERT OR UPDATE OR DELETE` par table révisionnée, propriétaire compris, plus le refus du
`TRUNCATE` sur le parent et chaque partition), doublée par une garde de service unique
(`revision_draft`, appelée par `judge_revision` du planning) ; je n'ai trouvé aucun chemin
d'écriture qui modifie une révision marquée. La machine à états suit le §3.3.2 transition pour
transition, chaque décision est prise sous `FOR UPDATE` du projet et relue sous le verrou, les
unicités (code de projet, code de sous-projet, révision en cours, nom de version, référence) sont
garanties par des index et non par une lecture préalable, et les tests de concurrence annoncés par
la conception existent.

Ce qui inquiète : (1) **un chemin a échappé au protocole de verrouillage** « la révision, puis le
projet » — `setWorkBreakdown` verrouille le projet puis écrit des tâches de la révision en cours ;
contre un marquage ou un abandon simultané, c'est un interblocage, donc une 500 (BPR-01) ; (2) **la
borne « coût réel reçu » de la correction de la référence n'existe pas**, alors que le contrat la
promet et qu'EP-09, à qui EP-04 l'avait renvoyée, est livré (BPR-02). Le reste est mineur :
compteurs nés à 0 contre la règle « un objet naît à 1 », questions posées « par révision seule » qui
traversent toutes les partitions et se répètent par ligne de liste, année de référence prise en
UTC, quelques incohérences locales.

Aucun constat bloquant.

## Constats bloquants

Aucun.

## Constats majeurs

### BPR-01 — `setWorkBreakdown` prend les verrous dans l'ordre inverse du marquage et de l'abandon : interblocage, 500

- **Issue** : #4442 (EP-35), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec BPR-08, BPR-12.
- **Où** : `core/projects/interface/work_breakdown.py:552` (verrou du projet, `_locked`), puis
  `:515-518` (`_remove` → `detach_item`) ; `core/planning/interface/work_breakdown.py:82-94`
  (`UPDATE task … SET work_package_id = NULL` sur les tâches de la révision en cours) ; le
  déclencheur de `task` prend alors `FOR KEY SHARE OF revision`
  (`migrations/versions/0022_planning.py:163-170`, `:174-197`). En face :
  `core/revisions/interface/marking.py:185-186` (`submit_marking` : révision `FOR UPDATE`, puis
  projet), `core/revisions/interface/revisions.py:600-603` (`abandon_revision`, même ordre).
- **Quoi** : toute écriture qui tient le projet puis écrit dans la révision en cours inverse
  l'ordre « la révision, puis son projet — jamais le projet avant la révision »
  (`core/revisions/interface/shared.py:9-17`). `designate_reference` et `update_project` ont reçu
  la parade (`hold_current_revision`, `hold_estimate` : partage de la révision **avant** le verrou
  du projet) ; `set_work_breakdown` ne l'a pas. C'est le défaut n° 2 de `python.md` (« protocole
  appliqué à une route, pas à ses sœurs »).
- **Scénario** : un projet dont le squelette a été engendré (chaque lot et chaque poste est porté
  par une tâche de la révision en cours). Le chef A enregistre un lotissement qui retire un lot :
  T2 verrouille le projet, lit « aucune tâche de fond » (`:556`), verrouille les lignes du lot.
  Au même instant le chef B demande `markRevision` (ou `abandonRevision`, ou `exitProject` avec
  abandon) : T1 tient la révision `FOR UPDATE` et attend le projet. T2 lance l'`UPDATE task`, son
  déclencheur attend la révision : T1 attend T2, T2 attend T1. PostgreSQL abat l'une des deux
  après `deadlock_timeout` ; aucune reprise n'existe (`grep -rn "Deadlock\|40P01" src` : rien),
  donc 500 `INTERNAL_ERROR` pour l'un des deux chefs. Le worker, lui, n'y tombe pas (sa tâche est
  déjà visible, T2 répond 409). Le test `test_the_marking_locks_the_revision_then_the_project…`
  (`tests/test_revision_mark.py:569`) éprouve l'ordre pour le marquage et l'abandon, aucun pour
  `set_work_breakdown`.
- **Proposition** : partager la révision en cours avant le verrou du projet dans
  `set_work_breakdown` — par le registre des rattachements (`Attachments` gagne un `hold(session,
  project_id)`, que le planning remplit par `hold_current_revision`), comme `EstimateFacts.hold_revision`
  le fait pour l'inflation. Test : le jumeau de `test_revision_mark.py:569` — une transaction tient
  la révision `FOR UPDATE`, `setWorkBreakdown` qui retire un lot porté doit attendre **sans** tenir
  le projet (`SELECT … FROM project … FOR UPDATE NOWAIT` passe pendant l'attente).
- **Confiance** : confirmé (lecture de bout en bout ; non rejoué). Fenêtre étroite — deux
  gestes de chefs de projet dans la même seconde — mais sans garde ni reprise.
- **Variante mineure, même famille** : `abandon_revision` et `submit_marking` verrouillent
  `FOR UPDATE` la révision nommée **avant** de savoir qu'elle est en cours
  (`revisions.py:600`, `marking.py:185`), alors que `designate_reference` verrouille le projet puis
  des révisions marquées (`reference.py:174-188`) en s'appuyant sur « le marquage et l'abandon ne
  verrouillent jamais une révision marquée » (`reference.py:15-19`). Un `DELETE` ou un `mark`
  adressé à une révision marquée (l'écran ne le propose pas, l'API l'admet avant de répondre 409)
  pendant une désignation de cette même révision s'interbloque de même. Parade : lire le statut
  sans verrou d'abord, ou `FOR SHARE` puis promotion.

### BPR-02 — La correction de la référence reste ouverte après réception de coûts réels (contrat et WF-REV-0040)

- **Issue** : #4440 (EP-35), ouverte le 2026-11-21, avec SPB-01.
- **Où** : `core/revisions/interface/reference.py:77-102` (`reference_correctable`), docstring
  `:83` « The actual costs, which also close it, are EP-09's » ; contrat
  `docs/api/components/schemas/projects.yaml:387-389` et `docs/api/paths/revisions.yaml:358-360`
  (« the project having received an actual cost or a revision having been marked since the last
  designation ») ; `docs/roadmap/EP-04-projets-et-revisions.md:54-55` et `:1330` (« les coûts réels
  sont d'EP-09 »).
- **Quoi** : la condition `reference_correctable` ne regarde que les marquages postérieurs à la
  dernière désignation ; un coût réel reçu ne la ferme pas. EP-09 est livré et n'a rien branché
  (`grep -rn correctable src` hors `core/revisions` : rien ; `grep "correctable\|désignation"
  docs/roadmap/EP-09*.md` : rien) ; EP-08, qui clôt WF-REV-0040, n'a pas encore d'US et ne nomme
  pas ce poste. Le morceau est tombé entre trois EPIC.
- **Scénario** : offres v2 puis v3 marquées, v2 désignée, code saisi : le projet passe En cours.
  L'extraction de l'ERP est importée (EP-09). Le chef de projet désigne v3 : aucune révision
  marquée depuis la désignation, donc 200 — la référence, `project.reference_revision_id`, et les
  montants budgétés de la révision en cours (`refresh_budgeted`) se déplacent alors que des coûts
  sont imputés. WF-REV-0040 : « Cette désignation peut être corrigée tant que le projet n'a reçu
  aucun coût réel » ; la commande `designate_reference` est de même listée disponible à tort.
- **Proposition** : un registre de plus dans `core/revisions` (`register_reference_bound`, ou la
  question ajoutée à ce que `core/costs` enregistre déjà chez les projets, `CostFacts`) : « le projet
  a-t-il une ligne de coût ? », lue dans `reference_correctable` — la couche des coûts est
  au-dessus de celle des révisions, d'où le registre. Tests : désignation refusée 409
  `reference_correctable` après un import de coûts, acceptée avant ; la commande de la révision
  nomme la condition. À défaut, une issue rattachée à EP-08 qui porte explicitement le poste, et la
  docstring corrigée.
- **Confiance** : confirmé pour l'écart au contrat et à l'exigence. Cherché dans `docs/roadmap/`
  (`correctable`, `coût réel`, `WF-REV-0040`) : aucun constat reporté ne le porte ; l'exigence
  elle-même n'est pas déclarée close (EP-08), d'où « majeur » et non « bloquant ».

## Constats mineurs

### BPR-03 — L'année de référence d'une révision est celle du temps universel, et échappera au fuseau d'EP-25

- **Issue** : #3983 (EP-35), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où** : `core/revisions/interface/revisions.py:501` (`reference_year=act.at.year`) ;
  `core/projects/interface/days.py:8-9`, `:18`.
- **Quoi** : WF-REV-0060 veut « l'année courante ». Le jour courant passe par `current_day`, la
  seule fonction qu'US-2200 (EP-25, #2527) branchera sur le fuseau de l'installation, « ses
  appelants inchangés » ; l'année de référence ne passe pas par elle.
- **Scénario** : installation au fuseau de Paris, révision créée le 1ᵉʳ janvier 2027 à 0 h 30
  (31 décembre 23 h 30 UTC) : année de référence 2026, donc taux de 2026 et aucune proposition de
  mise à jour ; l'erreur est figée au marquage.
- **Proposition** : `reference_year=current_day(act.at).year` ; un test à l'instant
  `2026-12-31T23:30Z` une fois le fuseau branché. Coût : une ligne.
- **Confiance** : confirmé. Le fuseau est déjà connu (#2527, EP-25) ; cet appelant-là n'y est pas.

### BPR-04 — Révision, sous-projet et liste des contributeurs naissent à `lock_version` 0, contre le contrat

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — l'auteur a tranché le même écart
  pour les rôles et les comptes le 2026-11-11 (#2779 et #2843 closes, « rien avant la v1, aucune
  migration ») ; aucun dommage fonctionnel.
- **Où** : `core/revisions/interface/revisions.py:496-509` (aucun `lock_version` à l'insertion,
  donc le défaut 0 de `core/revisions/tables.py:69`, dont le commentaire `:66-68` affirme le
  contraire) ; `core/projects/interface/subprojects.py:456` (`lock_version=0`) ;
  `core/projects/interface/projects.py:573-585` (`contributors_lock_version` laissé à 0 alors que
  le créateur est inscrit) ; contrat `docs/api/components/common.yaml:120-124` (« An object is
  created at 1 … the marking of a revision created and then marked carries it to 2 »).
- **Quoi** : #2542 a aligné la structure principale, #2762 le projet et son lotissement ; ces
  trois compteurs sont restés à 0. Les exemples `revision_created` et `subproject_created` portent
  1, le service rend 0 ; une révision créée puis marquée est à 1, non 2. Les tests affirment le 0
  (`tests/test_subprojects.py:84`, `tests/test_contributors.py:153`).
- **Scénario** : aucun dommage fonctionnel ; l'écart se voit dès qu'un parcours compare un
  compteur à l'exemple en absolu (ce que `test_skeleton.py` fait déjà pour la structure).
- **Proposition** : `lock_version=1` aux trois insertions, tests ajustés, commentaire de
  `tables.py` corrigé — ou une ligne ajoutée à la dette #2779, qui ne nomme que rôles, comptes et
  nœuds.
- **Confiance** : confirmé.

### BPR-05 — Les questions « la révision porte-t-elle… » ignorent la partition et se répètent par ligne de liste

- **Issue** : #4484 (EP-40), ouverte le 2026-11-21, avec DON-01, DON-04, BPR-06.
- **Où** : `core/revisions/interface/reference.py:70` (signature du registre :
  `Callable[[Session, UUID], bool]`, la révision seule), `:219-239` ;
  `core/revisions/states.py:65-67` ; `core/revisions/interface/revisions.py:309-322` (`_views`,
  une `state_of` par ligne) ; réponses : `core/planning/interface/nodes.py:209-213`,
  `core/planning/interface/lines.py:233-237` (`EXISTS … WHERE node.revision_id = :r`, sans
  `project_id`).
- **Quoi** : deux défauts qui se multiplient. (a) La question ne reçoit pas le projet : la
  requête lit toutes les partitions de `node` — ce que `tests/test_partitions.py:109-112` montre
  lui-même pour une lecture « par la révision seule », contre WF-DAT-0050. (b) `_views` la pose
  deux à trois fois par révision (`revision_has_tasks_and_lines`, puis `revision_has_tasks`, qui
  repose la question des tâches), sans lot : N+1.
- **Scénario** : `listRevisions` par défaut (50 lignes) = 100 à 150 requêtes non élaguées ;
  à `limit=500`, jusqu'à 1 500. Sur l'installation cible (600 projets, 180 révisions par projet),
  chaque requête planifie et sonde 600 partitions. `getRevision` et `listCostStructures` paient la
  même chose à l'unité.
- **Proposition** : donner `(session, project_id, revision_ids)` aux questions, qui répondent pour
  un lot en une requête filtrée sur `project_id` (le modèle existe : `opening_with_tasks`,
  `subprojects_cited`). Coût : trois signatures et leurs deux réponses. Test : le compteur de
  requêtes de `test_projects_list.py` (`test_the_list_sends_as_many_statements…`) porté à
  `listRevisions`, et le plan lu comme `test_partitions.py:89`.
- **Confiance** : confirmé pour le N+1 et l'absence du prédicat ; le coût chiffré est une
  estimation, non mesurée. WF-DAT-0050 (F1) se clôt en EP-13.

### BPR-06 — `item_cited` cherche les tâches d'un lot dans toutes les partitions

- **Issue** : #4484 (EP-40), ouverte le 2026-11-21, avec DON-01, DON-04, BPR-05.
- **Où** : `core/projects/interface/attachments.py:35`, `:48` (`cited(session, item_id)`, sans
  projet) ; appel `core/projects/interface/work_breakdown.py:520`, `:526` ;
  `core/planning/interface/work_breakdown.py:69-79` (jointure `node`/`task` sans `project_id`,
  puis une `current_revision` par ligne trouvée).
- **Quoi** : même cause que BPR-05, sur le chemin d'écriture du lotissement, projet verrouillé.
- **Proposition** : `cited(session, project_id, item_id)` ; le planning filtre `Task.project_id`.
- **Confiance** : confirmé.

### BPR-07 — Un projet En cours peut perdre son code

- **Issue** : #3989 (EP-35), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où** : `api/projects.py:297`, `:309` (un `code: null` envoyé est porté) ;
  `core/projects/interface/projects.py:728-739` (écrit `None`, `advance` non appelé, rien ne refuse).
- **Quoi** : WF-PRJ-0010 exige le code pour passer En cours ; rien ne l'exige ensuite. Le contrat
  admet `null` sans dire l'état. Un projet En cours sans code n'a plus de prochain état nommé, et
  ses imports de coûts réels rejettent toute ligne (`WBS_ELEMENT_OUTSIDE_PROJECT`,
  `core/costs/extraction.py:265-281`) ; le code libéré peut être pris par un autre projet.
- **Scénario** : un chef de projet vide le champ par erreur sur un projet lancé ; l'import mensuel
  suivant échoue ligne à ligne sans que l'écran du projet ne signale rien.
- **Proposition** : refuser l'effacement dès En cours (409 `STATE_FORBIDS_OPERATION`, condition
  à nommer au contrat — donc une « Interface contract issue »), ou l'assumer et le dire dans le
  contrat. Test des deux côtés de l'état.
- **Confiance** : confirmé pour le comportement ; l'intention est à trancher par l'auteur.

### BPR-08 — `updateProject` rechiffre la révision en cours pendant qu'un marquage est en file

- **Issue** : #4442 (EP-35), ouverte le 2026-11-21, avec BPR-12, BPR-01.
- **Où** : `core/projects/interface/projects.py:708-741` (aucune lecture des tâches de fond ;
  `core/projects/commands.py:101-106` ne suspend pas `update`).
- **Quoi** : la conception (« Le worker ») veut que les commandes « qui écriraient dans la
  révision » nomment `no_background_task_running` pendant la tâche. Le taux d'inflation, branché par
  EP-07, écrit les lignes de la révision en cours (`reinflate_estimate`) sans cette condition.
- **Scénario** : A demande le marquage « Offre v2 » (202) ; avant que le worker ne le prenne, B
  change le taux d'inflation : la révision est rechiffrée, puis marquée avec des montants que A n'a
  pas vus. Les données restent cohérentes (le taux conservé est celui du projet au marquage).
- **Proposition** : refuser `inflation_rate` par 409 `no_background_task_running` quand une tâche
  vise le projet, lue sous le verrou ; test jumeau de
  `test_while_the_marking_is_pending_the_writes_of_the_revision_name_the_task`.
- **Confiance** : confirmé (lecture). Fenêtre de quelques secondes.

### BPR-09 — `api/subprojects.py` importe la table privée du module des projets

- **Issue** : #3966 (EP-33), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où** : `api/subprojects.py:42` (`from waterfall.core.projects.tables import SUBPROJECT_CODE_LENGTH`).
- **Quoi** : seule entrée de l'API dans un `tables.py` du noyau (`grep` sur `api/`, `worker/`,
  `witness/`) ; le contrat `independence` d'import-linter ne couvre que les modules du noyau entre
  eux, donc rien ne le voit. `api/projects.py:71` redéclare la borne voisine au lieu de l'importer.
- **Proposition** : exporter la constante par `core/projects/interface`, ou la redéclarer comme
  `CODE_LENGTH` ; étendre le contrat d'imports à `api → core.*.tables`.
- **Confiance** : confirmé.

### BPR-10 — « Marquée depuis la désignation » compare deux horloges

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue le dit « plausible »,
  sans scénario constaté : il faut un écart d'horloge entre deux hôtes supérieur au délai entre une
  désignation et un marquage, et l'effet est une référence restée corrigeable.
- **Où** : `core/revisions/interface/reference.py:98` (`marked_at > designated_at`), `:153`
  (instant de la désignation : horloge de l'API) ; `core/revisions/interface/marking.py:232`
  (instant du marquage : horloge du worker).
- **Quoi** : #2274 a pris les deux instants sous verrou pour les ordonner, mais chacun sur
  l'horloge de son processus. Un worker en retard de Δ sur l'API date un marquage fait dans les Δ
  qui suivent la désignation **avant** elle : la référence reste corrigeable.
- **Proposition** : prendre les deux instants à la base (`clock_timestamp()`), seule horloge
  commune ; ou comparer par un compteur. Coût faible ; risque nul sur un seul hôte.
- **Confiance** : plausible — non vérifié : la synchronisation d'horloge des hôtes en production.

### BPR-11 — `project.current_revision_id` et `reference_revision_id` : deux vérités que la base ne lie pas

- **Issue** : #4469 (EP-38), ouverte le 2026-11-21, avec DON-07, DON-08, DON-09, DON-14.
- **Où** : `core/projects/tables.py:133-139` (clés simples vers `revision.id`) ;
  `migrations/versions/0020_projects_and_revisions.py:369-370`.
- **Quoi** : la révision en cours se lit tantôt dans `project.current_revision_id`
  (`project_facts`), tantôt par `revision.status = 'draft'` (`current_revision`,
  `revisions.py:235-239`) ; la référence de même (`is_reference`). Le service les écrit ensemble,
  mais la base admettrait la révision d'un autre projet — ce que #2105 a justement refusé pour
  `source_revision_id` par une clé composite.
- **Proposition** : clés composites `(id, current_revision_id)` et `(id, reference_revision_id)`
  vers `revision(project_id, id)` (l'unicité existe), dans une migration ultérieure ; un test par
  contrainte dans `test_database_constraints_projects.py`.
- **Confiance** : confirmé (défaut de durcissement, aucun chemin du service ne l'exploite).

### BPR-12 — Fenêtre d'interblocage documentée et laissée ouverte

- **Issue** : #4442 (EP-35), ouverte le 2026-11-21, avec BPR-08, BPR-01.
- **Où** : `core/revisions/interface/shared.py:19-27` ; `core/revisions/interface/reference.py:194`.
- **Quoi** : une révision ouverte entre les deux lectures de `hold_current_revision` est partagée
  sous le verrou du projet ; un `markRevision` simultané s'interbloque (500). Le code le dit et
  renvoie à un code d'erreur que le contrat n'a pas. Aucune issue ne le porte dans `docs/roadmap/`.
- **Proposition** : l'inscrire aux constats reçus d'un EPIC (avec BPR-01, qui a la même issue :
  une 500 sur interblocage), et trancher une reprise transparente de la transaction sur `40P01`
  dans `Database.transaction`, qui fermerait les deux sans code nouveau.
- **Confiance** : confirmé (documenté par le code lui-même).

## Points forts

- **Immuabilité par la base**, complète : `revision_refuse_marked_change` (retour à `draft`,
  toute colonne hors `is_reference`/compteur/audit, suppression), un garde par table révisionnée
  (`cost_structure`, `node`, `task`, `task_link`, `estimate_line`, `revision_rate`, les trois
  images), qui juge `OLD` **et** `NEW` (une ligne ne se déplace pas dans une révision marquée),
  `FOR KEY SHARE` contre le `FOR UPDATE` du marquage (#2104), clés qui nomment la structure *avec*
  sa révision. Éprouvé par le propriétaire autour du service (`tests/test_revision_immutability.py`).
- **Copie d'une révision** atomique (transaction de la requête, sous le verrou du projet et le
  partage du référentiel), source nécessairement marquée donc immuable, identifiants remappés par
  `RevisionCopy.identifiers`, lignée conservée, structures fusionnées écartées, insertions en lot.
- **Cycle de vie** : `next_state` pure, `advance` idempotent, sorties jugées sous verrou avec
  relecture des tâches (#2220), sortie-qui-marque en une transaction du worker avec contrôle du
  compteur lu par le chef. Conforme au §3.3.2 ; aucune transition en trop ni en moins.
- **Unicités en base** avec point de sauvegarde et refus nommé (`uq_project_code`,
  `uq_subproject_project_id`, `uq_revision_draft`, `uq_revision_version_name`,
  `uq_revision_reference`), compteurs testés sous verrou, qualité de chef de projet rejugée sous le
  verrou du projet (#2207).
- **Périmètre** : filtre des projets appliqué en SQL (`projects.py:278-295`), tri par colonnes
  typées (`Literal`), recherche par `strpos` ; aucune concaténation SQL, aucun commentaire
  d'exemption, aucune table d'un autre module lue.
- **Tests** : nombreux, précis, chacun citant son exigence ou disant pourquoi il n'en cite pas ;
  concurrence couverte (deux ouvertures, deux sorties, deux désignations, dernier chef de projet,
  deux créations d'un même code).

## Couverture

- **Lu en entier** : `core/revisions/` (les 13 fichiers), `core/projects/` (les 13 fichiers) ;
  `api/projects.py`, `api/revisions.py`, `api/lifecycle.py`, `api/comparison.py`, `api/history.py`,
  `api/subprojects.py` ; `migrations/versions/0020_projects_and_revisions.py` ;
  `core/estimate/comparing.py`, `core/estimate/uniting.py`, `core/estimate/repricing.py` ;
  `worker/marking.py` ; spec §3.3.2, §4.4.2, FBS-4.1 et FBS-4.2 ; la Conception d'EP-04 et US-0980.
- **Échantillonné** : `api/contributors.py`, `api/evaluation.py`, `core/access_roles/evaluation.py` ;
  `migrations/versions/0022`, `0025`, `0027` (gardes, clés, index) ; `core/planning` pour ce que
  le domaine y appelle (`writing.judge_revision`, `interface/nodes.copy_nodes`,
  `interface/work_breakdown.py`, `interface/closing.py`, `attachments.py`) ; `core/history`
  (clôture) ; `platform/tasks.py`, `platform/audit.py` ; tests : `test_revision_mark.py`,
  `test_revision_immutability.py`, `test_projects_lifecycle.py`, `test_revisions.py`,
  `test_partitions.py` (extraits), noms de tests et marqueurs des 18 fichiers du domaine,
  `asked_revisions.py`, `asked_lifecycle.py`.
- **Non lu** : `api/work_breakdown.py` ; `migrations/versions/0026` (fonction des partitions,
  décrite par `sql.md`) ; `witness/` ; `test_comparison.py`, `test_subprojects.py`,
  `test_contributors.py`, `test_work_breakdown*.py` au-delà de leurs noms ; `paths/projects.yaml` et
  `paths/revisions.yaml` hors des passages cités ; le front.
- **Sans objet** : suppression d'un projet (il n'en existe pas : le rôle du service n'a pas
  `DELETE` sur `project`, un projet sort par un état terminal) ; hiérarchie de sous-projets (ils
  sont à plat : ni cycle, ni profondeur) ; comparaison avec la révision en cours (EP-27, non livré).

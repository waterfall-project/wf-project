# Revue — contrat d'API, familles de projet (projects, revisions, costs, exchanges, analysis ; risks et portfolio survolés)

Chemins relatifs à `/home/user/wf-project`. « Servie » = une route du back porte l'`operationId`
(`grep -rn` dans `backend/src/waterfall/api`). Non servies dans mon périmètre : `createCostStructure`,
`getStructureMergeReport`, `mergeCostStructure` (EP-08), les cinq opérations `indicators` (EP-10),
toute la famille `risks` (EP-08) et `portfolio` (EP-11).

## Synthèse

Le contrat de ces familles est tenu de très près : aucun `$ref` cassé, aucun `required` qui nomme
une propriété absente, catalogue des codes d'erreur et des conditions sans orphelin, 401/500/503
partout, 412 et `lock_version` sur chaque écriture hors exceptions décidées, exemples chiffrés
justes là où je les ai refaits (coûts réels, reste à engager, couverture des risques). Ce qui reste
n'est donc pas de la forme mais du fond, là où le contrat se tait.

Trois points inquiètent. (1) L'application d'un import n'a aucune garde de péremption : le contrat
pose le principe « le compte rendu confirmé est ce qui s'applique » sans rien qui le garantisse
quand la structure a bougé depuis l'analyse — et le service, de fait, diverge d'un format à l'autre :
le devis s'y tient, le planning MS Project replanifie et supprime une tâche saisie entre-temps.
(2) `uploadFile` est la seule écriture sans permission ni 403 : tout compte authentifié écrit
10 Mio par requête sur le stockage objet, sans quota. (3) La disposition en couloirs d'une
chronologie est rangée par `node_id`, que chaque nouvelle révision renouvelle : elle se perd à
chaque revue. Le reste est mineur : bornes d'entrée manquantes (textes libres, listes, un entier),
refus et durées de vie non dits, champs nullables tantôt absents tantôt nuls, conventions du README
tenues inégalement sur quelques listes.

## Constats bloquants

Aucun.

## Constats majeurs

### CTB-01 — L'application d'un import n'est pas liée au compte rendu confirmé ; le planning MS Project supprime ce qui a été saisi depuis l'analyse

- **Issue** : #4420 (EP-33), ouverte le 2026-11-21, avec BEX-02.
- **Où** : `docs/api/components/schemas/exchanges.yaml:1009-1019` (`ImportApply` : `confirmed` seul,
  aucun compteur) ; `docs/api/paths/exchanges.yaml:470-547` (`applyImport` : ni 412, ni règle sur
  une structure modifiée depuis l'analyse ; le principe n'est dit que pour la correspondance,
  `:481-483`, « the confirmed report is what applies ») ; `:529-532` ne rejuge que les *refus*.
  Opération servie. Côté service : `backend/src/waterfall/core/planning/interface/msproject.py:100-117`
  (`del report`, puis `plan_import(..., lock=True)`), `backend/src/waterfall/core/planning/importing.py:596-602`
  (`removed` = toute tâche non commencée de la structure que le fichier ne porte pas, calculé sur
  la structure telle qu'elle est à l'application) ; à l'inverse `backend/src/waterfall/core/estimate/importing.py:262-271`
  (`Confirmed.removed` : seules les lignes annoncées retirées le sont, « one entered since the
  analysis » laissée) et son test `backend/tests/test_estimate_import_application.py:454`.
- **Quoi** : entre l'analyse et la confirmation (jusqu'à vingt-quatre heures, pendant lesquelles
  l'analyse « suspends nothing », `schemas/projects.yaml:195-197`), le contrat ne dit pas ce
  qu'applique un import dont la structure a changé, et ne donne aucun moyen de le refuser ; le
  collage (`PasteApply`, `schemas/revisions.yaml:2595-2614`) et la fusion (`StructureMerge`,
  `:566-605`) ont, eux, leur 412.
- **Scénario** : A ouvre l'import d'un planning MS Project exporté la veille ; le compte rendu
  annonce trois tâches modifiées, aucune retirée. B, contributeur, crée dans la grille une tâche T
  et ses lignes de devis. A confirme : le worker rebâtit le plan sous le verrou, T est « absente du
  fichier », non commencée, donc supprimée avec ses lignes — rien de tel ne figurait au compte
  rendu que A a confirmé (WF-INTF-0080 : « L'import n'est appliqué qu'après confirmation », WF-ARC-0100).
  Le même scénario sur un devis laisse la ligne de B en place : deux comportements pour un même contrat.
- **Proposition** : trancher au contrat, une fois pour les quatre natures — soit le compte rendu
  retient les compteurs des structures lues et `applyImport` refuse par 412 (comme `PasteApply`),
  l'import restant `analysed` et réanalysable ; soit la règle du devis est écrite pour tous (« ce
  que le compte rendu n'a pas annoncé retiré ne l'est pas ») et le format MS Project s'y range.
  Test : analyse d'un planning, création d'une tâche par `createNode`, `applyImport`, la tâche
  existe toujours (ou 412).
- **Confiance** : confirmé à la lecture, de `applyImport` jusqu'à `plan_import` ; non rejoué sur une base.
  La partie service relève aussi du relecteur du back.

### CTB-02 — `uploadFile` : une écriture sans permission, sans 403 et sans quota

- **Issue** : #4423 (EP-33), ouverte le 2026-11-21, avec BAC-09.
- **Où** : `docs/api/paths/exchanges.yaml:4-45` (réponses 201/400/401/413/422/500/503, aucune
  permission nommée) ; servie par `backend/src/waterfall/api/imports.py:148-151` (dépendance
  `Caller` seule). Aucune décision ne le motive (`grep uploadFile docs/api/DECISIONS.md` : usage et
  borne de taille seulement, `:1014-1026`).
- **Quoi** : c'est la seule écriture de mes familles qui ne déclare pas de 403 ; tout compte
  authentifié, sans aucune permission d'import ni qualité de contributeur, écrit un objet de 10 Mio
  et une ligne `file_upload`, gardés vingt-quatre heures, autant de fois qu'il veut.
- **Scénario** : un compte en lecture seule boucle sur `POST /file-uploads` : le stockage objet, qui
  porte aussi les sauvegardes, se remplit de 10 Mio par requête jusqu'à la purge du lendemain.
- **Proposition** : exiger l'une des permissions d'import (`planning.write`, `estimate.write`,
  `remaining.write`, celle des coûts réels) — 403 `PERMISSION_MISSING` déclaré — et borner les
  dépôts en attente par compte ; ou, à défaut, écrire l'exception au contrat comme le sont celles
  du README. Test : un compte sans permission d'écriture reçoit 403 et rien n'est écrit au stockage.
- **Confiance** : confirmé (contrat et route lus). La gravité est un jugement : déni de service
  par un compte interne, pas une fuite.

### CTB-03 — Les couloirs d'une chronologie sont rangés par `node_id`, qui change à chaque révision

- **Issue** : #4463 (EP-38), ouverte le 2026-11-21.
- **Où** : `docs/api/components/schemas/access.yaml:416-433` (`TimelinePreferences.lanes`, « by its
  `node_id` ») et la décision `docs/api/DECISIONS.md:7716-7729` — famille `me`, hors de mon
  périmètre strict, relevé parce qu'il découle du modèle des nœuds ; `docs/api/components/schemas/revisions.yaml:687-690`
  (`lineage_id`, « stable from one revision to the next », porte les inscriptions) ;
  `backend/src/waterfall/core/planning/interface/nodes.py:236-262` (la copie d'une révision donne
  à chaque nœud un identifiant neuf, « The inscriptions follow the lineage ») ;
  `frontend/src/components/gantt/timeline-chart.tsx:132` (clé `node.node_id`).
- **Quoi** : l'inscription d'une tâche à une chronologie suit la lignée, sa place en couloir suit
  l'identifiant du nœud ; la décision n'a pas pesé la copie des révisions.
- **Scénario** : un chef de projet range sa frise ; la révision est marquée à la revue mensuelle,
  la suivante ouverte ; les tâches sont toujours inscrites, mais toutes retombent en empilement
  automatique — à chaque revue (WF-PLA-0140 : « cette disposition, qui lui est propre, se retrouve
  d'une session à l'autre », close par EP-06/US-1400 sur un rechargement dans la même révision).
- **Proposition** : ranger les couloirs par `lineage_id` (contrat, décision, front) ; test : marquer,
  ouvrir la révision suivante, la disposition est retrouvée.
- **Confiance** : confirmé à la lecture (contrat, copie, front) ; non rejoué.

## Constats mineurs

### CTB-04 — `payment_delay_days` sans borne haute
- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `schemas/revisions.yaml:2122-2123` (`EstimateLineWrite`), `:2167-2168` (`EstimateLineUpdate`),
  `:1736-1737` (lecture) : `integer, minimum: 0`, sans `maximum`. Servie (`createNode`,
  `updateEstimateLine`). Colonne `Integer` (`backend/src/waterfall/migrations/versions/0025_estimate.py:286`),
  le cœur ne juge que `>= 0` (`core/estimate/entries.py:335`).
- **Scénario** : `{"payment_delay_days": 3000000000, "lock_version": n}` : aucun refus prévu, la base
  déborde — 500 plausible ; et, sous la borne, un délai de plusieurs millénaires décale la courbe.
- **Proposition** : `maximum` (36 500 par exemple), 422 `VALUE_OUT_OF_RANGE` ; test au pointeur.
- **Confiance** : confirmé pour l'absence de borne ; plausible pour le 500 (non rejoué). US-1980
  (#2875) a borné les décimaux au service en laissant le contrat tel quel (décision du 2026-11-12) :
  les bornes des décimaux (`numeric(12,2)`, `numeric(14,2)`) restent de même absentes du contrat.

### CTB-05 — Textes libres sans `maxLength`
- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `schemas/projects.yaml:631-633`, `:649-651` (`description` du projet), `:750-754`
  (`ProjectExit.reason`), `:802-806` ; `schemas/revisions.yaml:299-305`, `:327-331`, `:590-595`
  (descriptions de révision), `:1997-1999`, `:2063-2065` (description de tâche), `:2296-2301`
  (`RemainingUpdate.reason`) ; `schemas/costs.yaml:121-125` (`ScopeExclusion.reason`) ; de même
  `RiskWrite.description`, `mitigation_notes` (non encore réalisé). Opérations servies, modèles du
  service sans borne (`api/contract/models.py:2641-2643`).
- **Scénario** : une description de 10 Mio par tâche ou par projet, rendue à chaque lecture —
  `listProjects` rend `Project` entier, 500 par page ; seul le plafond du corps côté front borne.
- **Proposition** : une borne par champ (4 000 caractères par exemple), `VALUE_TOO_LONG` et son
  `max_length`, comme les libellés. Coût : contrat, modèles engendrés, un test par champ.
- **Confiance** : confirmé.

### CTB-06 — Listes d'écriture sans `maxItems`
- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `schemas/projects.yaml:839-842`, `:880-882`, `:891-893` (`setWorkBreakdown`, d'où naît le
  squelette) ; `schemas/revisions.yaml:400-409` (`RateUpdateApply.cost_category_ids`), `:1891-1900`
  (`predecessors`), `:2235-2238` (`NodeMove.node_ids`) ; `paths/revisions.yaml:2151-2157`
  (`setNodeTracking.entries`). Servies. `ContributorsWrite` a la sienne, motivée (`projects.yaml:1157-1164`).
  Le collage est borné par la taille de la requête, décidé (`schemas/revisions.yaml:2441`).
- **Proposition** : une borne tirée du §4.6.2 par liste ; `VALUE_TOO_LONG` au pointeur.
- **Confiance** : confirmé.

### CTB-07 — Le plan d'un collage : durée de vie et refus non dits
- **Issue** : #4398 (EP-31), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où** : `schemas/revisions.yaml:2471-2502` (`PastePlan` sans `expires_at`), `paths/revisions.yaml:2441-2531`
  (`applyPaste` : 404 commun seul). Servie : le plan vit une heure et n'appartient qu'à son auteur
  (`backend/src/waterfall/core/history/tables.py:118-148`), sinon 404 (`core/planning/interface/paste.py:896`) ;
  l'heure n'est écrite que dans la Conception d'EP-06 (`docs/roadmap/EP-06-planification.md:379`).
- **Scénario** : aperçu, pause, confirmation : 404 `NOT_FOUND` sur un projet et une structure bien
  visibles, que le front ne sait pas dire.
- **Proposition** : `PastePlan.expires_at`, et le 404 d'un plan expiré, inconnu ou d'un autre
  auteur décrit sous `applyPaste`, avec son exemple.
- **Confiance** : confirmé.

### CTB-08 — `revision_id` des indicateurs de devis et de reste à engager : ni défaut, ni refus décrits
- **Issue** : #4466 (EP-38), ouverte le 2026-11-21, avec CTA-08, CTA-09, CTC-02.
- **Où** : `paths/analysis.yaml:23-25` (`getEstimateIndicators`), `:65-67` (`getMissingRates`),
  `:163-165` (`getRemainingIndicators`) : paramètre sans description ; réponses `:40-45`, `:80-81`, `:176-177`.
  Servies : « the revision named, else the current one, else the last one marked », sinon 404
  (`backend/src/waterfall/core/revisions/interface/revisions.py:365-375`).
- **Quoi** : la révision lue par défaut n'est pas dite ; un projet à l'état Créé, sans révision,
  répond 404 alors qu'il existe et se consulte ; une révision inconnue en requête est un 404 ici,
  un 422 sur `/query/revision_id` pour `getProjectWorkload` (`:139-143`), deux formes pour un même refus.
- **Proposition** : décrire le paramètre comme `IndicatorsRevision` (`parameters.yaml:889-905`), et
  choisir une forme pour le projet sans révision et la révision inconnue.
- **Confiance** : confirmé.

### CTB-09 — Champs nullables tantôt absents, tantôt nuls
- **Issue** : #4467 (EP-38), ouverte le 2026-11-21, avec CTA-07, CTB-10, CTB-13, CTB-14.
- **Où** : `schemas/costs.yaml:5-17` contre `:43-48` (`ActualCostLine.subproject_id` hors `required`,
  son code et son libellé exigés) ; `schemas/revisions.yaml:425-433` contre `:449-453`
  (`CostStructure.risk_id`, « Null for the main structure », absent de l'exemple `structures.json`) ;
  `:1671-1683` contre `:1718-1750` (`EstimateLineFacet` : identifiants de rôle et de sous-projet
  facultatifs, « absent otherwise », leurs libellés exigés et nuls) ; `:360` contre `:367`
  (`RateUpdateProposal.target_year`, absent de `rate_update_none.json`, toujours rendu par
  `api/rate_update.py:46`) ; `schemas/indicators.yaml:65` contre `:72` (`MissingRate.label`) ;
  `:284` contre `:292` (`SubprojectBalance.label`, absent pour `unassigned`, quand `AmountByKey.label`,
  `:320-327`, est exigé et nul dans la même réponse).
- **Quoi** : le client engendré reçoit `x?: T | null` et doit traiter deux absences ; le contrat dit
  ailleurs « Always returned: the screen guesses nothing from an absent value ».
- **Proposition** : exiger ces champs, nuls quand ils n'ont pas de valeur ; régénérer les exemples.
- **Confiance** : confirmé.

### CTB-10 — Listes sans pagination qui ne disent pas pourquoi (README, `:64`)
- **Issue** : #4467 (EP-38), ouverte le 2026-11-21, avec CTA-07, CTB-09, CTB-13, CTB-14.
- **Où** : `paths/analysis.yaml:181-222` (`listStartableTasks` : toutes les tâches de la structure
  principale, chacune un `Node` entier, sans `fields`, sans filtre — 960 tâches et 1,6 Mo dans
  l'exemple de volume `fixtures/api/startable_tasks.json`, la colonne des terminées croissant toute
  l'exécution) ; `paths/projects.yaml:1085-1099` (`listTimelines`), `:1055-1075`, `:270-289` ;
  `paths/revisions.yaml:661-681` (`listCostStructures`) ; `paths/analysis.yaml:54-75`. Servies.
- **Proposition** : la phrase du §4.6.2 sous chacune ; pour le Kanban, `fields` comme `listNodes`,
  ou une page par colonne.
- **Confiance** : confirmé. Le temps de réponse du Kanban sur mille tâches est déjà connu et mesuré
  (#646, EP-09/US-1590) ; reste le silence du contrat.

### CTB-11 — Tables plates sans filtre ou sans tri par colonne
- **Issue** : #4468 (EP-38), ouverte le 2026-11-21.
- **Où** : `paths/costs.yaml:13-60` (`listActualCosts` : chaque colonne se trie, trois seulement se
  filtrent — ni pièce, ni poste, ni montant, ni motif, ni colonnes conservées) ; `:159-170`
  (`listCostImports`) et `paths/exchanges.yaml:202-214` (`listImports`) : ni tri, ni filtre.
  Servies. Le journal d'audit, les sous-projets, les sauvegardes et le registre des risques ont
  reçu les leurs au nom de WF-IHM-0130 et WF-IHM-0060 (`DECISIONS.md:3403`, `:3535`, `:4385`, `:10799`).
- **Proposition** : `amount_min`/`amount_max` et les filtres de texte selon la convention du README ;
  `sort_by` sur les deux journaux, ou la raison écrite.
- **Confiance** : plausible — WF-IHM-0130 est close par EP-11, non livré : à tenir pour dû par lui
  si le coordinateur lit ainsi la portée ; le contrat, lui, est dit figé sur tout l'horizon.

### CTB-12 — Deux vocabulaires pour une même notion
- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — préférence de vocabulaire ; la
  fenêtre que la revue visait (« avant qu'EP-08 ne serve la fusion ») est passée, et renommer
  toucherait le contrat figé, le service, le client et le catalogue du front pour un gain nul.
- **Où** : `schemas/revisions.yaml:799-801` (`NodeDifference` : `modified`) contre
  `schemas/exchanges.yaml:897-899` (`ImportDifference.change` : `updated`), repris par
  `StructureMergeReport.differences` (`revisions.yaml:647-659`) : le même différentiel dit
  `modified` à la lecture de ses nœuds et `updated` dans son compte rendu de fusion.
  `paths/revisions.yaml:17-23` : le filtre `status`, une liste, au singulier, quand `listProjects`
  et `listRisks` disent `states`.
- **Proposition** : aligner avant qu'EP-08 ne serve la fusion ; coût : contrat, client, catalogue du front.
- **Confiance** : confirmé.

### CTB-13 — `WorkloadPlan.roles` décrit moins que ce qui est servi
- **Issue** : #4467 (EP-38), ouverte le 2026-11-21, avec CTA-07, CTB-09, CTB-10, CTB-14.
- **Où** : `schemas/indicators.yaml:509-514` (« Every active role ») ; servie :
  `backend/src/waterfall/api/workload.py:14`, `:283` (les rôles actifs *et* ceux que la révision
  emploie, désactivés compris). À la lettre du contrat, la charge d'un rôle désactivé manquerait,
  et `monthly_totals` ne serait plus la somme des rôles rendus.
- **Proposition** : écrire au contrat la règle du service. **Confiance** : confirmé.

### CTB-14 — `ProjectSummary` défini, jamais employé
- **Issue** : #4467 (EP-38), ouverte le 2026-11-21, avec CTA-07, CTB-09, CTB-10, CTB-13.
- **Où** : `schemas/projects.yaml:572-581`, cité par `ProjectCode` (`:592`) ; aucun `$ref` dans
  `docs/api` (recherche par script sur tous les fichiers). **Proposition** : le retirer. **Confiance** : confirmé.

### CTB-15 — `compareRevisions` refuse la révision en cours, que la spécification 1.0.6 admet
- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — le contrat dit maintenant que la
  révision lue (`to_revision_id`) est « the current revision or a marked one », seule la base devant
  être marquée (409 `revision_marked` sur `from_revision_id`, « The current revision read is not
  refused »), avec l'exemple `comparison_current.json` ; le service suit (US-2320/L3, 46fce83b2).
  #3176 est fermée depuis le 2026-11-14.
- **Où** : `paths/revisions.yaml:629-633` (409 `revision_marked`) contre WF-REV-0080
  (`docs/spec/waterfall-spec.md:2008-2010`). **Déjà connu (#3176, EP-27)**
  (`docs/roadmap/EP-07-chiffrage-et-devis.md:1556-1566`).

## Points forts

- Intégrité mécanique : tous les `$ref` de `docs/api` résolus, `required` ⊆ propriétés dans les sept
  fichiers de schémas, chaque code et chaque condition cités existent dans `ErrorCode` et
  `CommandCondition`, les énumérations en ligne sont des sous-ensembles des énumérations nommées.
- Verrouillage optimiste complet : compteur dans le corps ou en paramètre sur chaque écriture, 412
  déclaré ; les trois exceptions sont décidées et écrites (`setActualCostTrackedScope`,
  `deleteTimeline`, les états d'un import).
- Révision figée et projet terminal : un seul refus, 409 `STATE_FORBIDS_OPERATION` et sa condition,
  annoncé d'avance par `available_commands`.
- Écritures par lots : collage en deux temps, lignes refusées nommées, 412 sur la structure jugée ;
  fusion avec les deux compteurs du compte rendu.
- Opérations longues : `BackgroundTaskRef` partout, échec porté par `problem`, états d'import nommés.
- Chiffres des exemples refaits et justes : `actual_costs*` (suivi + exclu = général, totaux de toute
  la sélection et non de la page), `remaining_indicators*` (marges par sous-projet, somme des marges
  = marge du projet, parts sommant à 1), couverture des risques.

## Couverture

- **Lu en entier** : `paths/costs.yaml`, `paths/exchanges.yaml`, `paths/analysis.yaml:1-290`,
  `components/schemas/costs.yaml`, `components/schemas/exchanges.yaml` (descriptions longues
  abrégées au-delà de quelques lignes pour `ImportRejection`, `ImportSignal`), `components/common.yaml`,
  `components/responses.yaml`, `README-fr.md`, `openapi.yaml`, `components/schemas/projects.yaml:1-620`.
- **Lu en structure complète, descriptions abrégées** (chaque schéma, chaque propriété, chaque
  réponse ; les descriptions de plus de trois à sept lignes tronquées, relues en entier là où un
  constat en dépendait) : `paths/projects.yaml`, `paths/revisions.yaml`,
  `components/schemas/projects.yaml:614-1215`, `components/schemas/revisions.yaml`,
  `components/schemas/indicators.yaml:1-545`, `components/parameters.yaml:1-140` et `:889-945`.
- **Par script seulement** (références, `required`, schémas inemployés, bornes des corps, table des
  opérations, énumérations) : `paths/risks.yaml`, `paths/portfolio.yaml`,
  `components/schemas/risks.yaml` (structure affichée), `components/schemas/portfolio.yaml`,
  `components/schemas/indicators.yaml:545-745`, le reste de `parameters.yaml`.
- **Non fait** : la validation de chaque exemple contre son schéma (mon script n'a pas abouti en
  temps raisonnable, arrêté ; `make lint-openapi` le fait) ; les exemples de `listNodes`, du plan de
  charge et des indicateurs de devis non recalculés ; `DECISIONS.md` consulté par recherche, jamais
  lu ; la conformité de chaque opération à chaque exigence citée n'a été vérifiée que sur
  WF-CRE-0010 à 0050, WF-ARC-0100, WF-INTF-0080, WF-RAE-0020/0030, WF-IND-0020, WF-REV-0060/0080/0090,
  WF-PLA-0140, WF-DEV-0070, WF-PRJ-0080, WF-IHM-0060/0130.

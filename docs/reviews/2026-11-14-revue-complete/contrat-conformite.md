# Revue — conformité au contrat (routes du back, modèles engendrés, client du front, faux back)

Commit relu : `29785cc` (`main`). Méthode : scripts `python3` d'analyse (YAML du contrat résolu
par `$ref`, AST des modules `backend/src/waterfall/api/*.py` et du noyau, validation
`jsonschema` des exemples), puis lecture des chemins signalés. Aucune commande lourde, aucun test
lancé : ce qui est dit « confirmé » l'est par lecture de bout en bout, pas par exécution.

## Synthèse

La conformité mécanique est très bonne. Les 132 routes du service répondent toutes à une
opération du contrat, même méthode, même chemin, même `operationId`, même statut de succès ;
aucune route hors contrat. Les paramètres de requête, d'en-tête et de chemin coïncident (un seul
écart, déjà connu : `listBackups`). Les 73 codes d'erreur que le back émet sont tous dans
`ErrorCode` (93 valeurs), toute erreur passe par l'enveloppe (`problems.py`, 422 natif, 404/405,
500 par `CorrelationMiddleware`, 401, 503 de maintenance). Le client du front et les modèles du
serveur portent les 170 opérations et les 93 codes du contrat ; le front n'a qu'un `fetch(`
(`client.ts:189`) et aucun code d'erreur hors contrat. Les 1 587 exemples que le contrat cite
(856 fixtures) valident tous leur schéma, sans propriété non déclarée.

Ce qui inquiète est étroit : deux opérations du contrat (`getIdentitySyncSchedule`,
`setIdentitySyncSchedule`) qu'aucun EPIC ne doit et que le front tolère en 404, alors que
l'exigence qu'elles portent est déclarée close ; trois réponses que le service peut rendre et que
le contrat ne déclare pas ou ne peut pas recevoir (422 d'`undo`/`redo`, 413 de `previewPaste`,
500 de `getProjectWorkload` sur une capacité écrite en notation scientifique). Le reste est déjà
connu et planifié en EP-13.

## Inventaire chiffré (périmètre implémenté)

**170 opérations au contrat, 132 servies, 38 non servies.** Routes du back : 132, toutes au
contrat (0 route hors contrat, 0 `operationId` divergent, 0 statut de succès divergent).

| Famille (`paths/*.yaml`) | Contrat | Servies | Non servies | Qui doit les non servies |
|---|---|---|---|---|
| system | 8 | 5 | 3 | EP-13 : `getReadiness`, `getMetrics`, `getSystemStatus` (`EP-13-exploitation.md:106`) |
| me | 5 | 5 | 0 | — |
| access | 20 | 18 | 2 | **aucun EPIC** : `getIdentitySyncSchedule`, `setIdentitySyncSchedule` (CTC-01) |
| platform | 10 | 5 | 5 | EP-13 : `retainBackup`, `getBackupSchedule`, `setBackupSchedule`, `listExternalBackupLocations`, `testExternalBackupLocation` (`EP-13:107`) |
| audit | 2 | 2 | 0 | — |
| reference | 31 | 31 | 0 | — |
| projects | 19 | 19 | 0 | — |
| revisions | 31 | 28 | 3 | EP-08 : `createCostStructure`, `getStructureMergeReport`, `mergeCostStructure` |
| analysis | 10 | 5 | 5 | EP-10 : `getProjectIndicators`, `getMilestoneTracking`, `getCostCurve`, `getEarnedValueCurves`, `getIndexHistory` |
| risks | 12 | 0 | 12 | EP-08 (toute la famille) |
| costs | 3 | 3 | 0 | — |
| exchanges | 11 | 11 | 0 | — |
| portfolio | 8 | 0 | 8 | EP-11 (toute la famille) |
| **Total** | **170** | **132** | **38** | 36 dues par un EPIC non livré, 2 sans propriétaire |

Familles entièrement servies : me, audit, reference, projects, costs, exchanges. Servies en
partie : system, access, platform, revisions, analysis. Non servies : risks, portfolio.

Codes d'erreur : 93 au contrat ; 73 levés par le back, tous énumérés ; 9 sites à code dynamique
(code relu d'un refus déjà typé ou d'un compte rendu gardé). Codes du contrat que rien n'émet
dans le back : `PATH_INVALID`, `UNKNOWN_EXTERNAL_BACKUP_LOCATION` (planification des sauvegardes,
EP-13), `PROVISION_CATEGORY_REQUIRED`, `PROVISION_LINE_MOVED_BY_RISK`, `UNKNOWN_RISK`,
`PASTE_TARGET_REMOVED` (risques et différentiels, EP-08) — aucun d'une famille livrée.

## Constats bloquants

Aucun.

## Constats majeurs

### CTC-01 — `getIdentitySyncSchedule` et `setIdentitySyncSchedule` : au contrat, servies par personne, dues par aucun EPIC, exigence close

- **Suite** : sans issue propre, vérifié le 2026-11-21 — tombera avec US-3040, issue #4065 (EP-13).
- **Où** : `docs/api/paths/access.yaml:708` (`/identity-sync-schedule`, GET et PUT) ;
  `backend/src/waterfall/api/identity_syncs.py` (deux routes seulement : `startIdentitySync`
  l. 43, `getLatestIdentitySync` l. 56) ; `frontend/src/app/admin/users/page.tsx:172-176` ;
  `deploy/compose/compose.prod.yaml:298` ; `docs/roadmap/EP-16-maquette-durcissement.md:939-941`,
  `EP-03-comptes-et-habilitations.md:1469`, `EP-04-projets-et-revisions.md:94` et `:900-901`.
- **Quoi** : le contrat déclare la lecture et le réglage de la périodicité de la lecture des
  comptes ; le service ne les sert pas (404), aucun EPIC, livré ou non, ne les liste dans ses
  « Opérations du contrat » (seul EP-16, EPIC de maquette, les a ajoutées), et le front masque
  l'absence par une tolérance du 404.
- **Scénario** : la décision A-02 du recadrage du 2026-10-28 ajoute les deux opérations en
  écartant expressément l'alternative « un paramètre d'exploitation, contraire à "choisie par un
  utilisateur habilité" » (`EP-16:939-941`, WF-ADM-0070, corps : « selon une périodicité choisie
  par un utilisateur habilité », `waterfall-spec.md:1225`). Or la périodicité du service est
  exactement ce paramètre d'exploitation : `while sleep "$WATERFALL_IDENTITY_SYNC_INTERVAL"; do
  waterfall-worker enqueue identity_sync` (`compose.prod.yaml:298`). EP-03 a constaté le critère
  « au terme de la périodicité choisie » par « la périodicité est celle de la tâche planifiée »
  (`EP-03:1469`), EP-04 clôt WF-ADM-0070-A (« fin », `EP-04:94`). Contre le service, un
  administrateur ouvre « Gestion des utilisateurs » : `readUnlessRefused("getIdentitySyncSchedule",
  [{ status: 404 }], …)` rend `undefined`, la section de la périodicité disparaît sans rien dire
  (commentaire : « the service not yet (EP-04) » — EP-04 est livré). Le 404 est un statut que le
  contrat déclare pour cette lecture (permission manquante) : ni Prism en proxy ni le typage du
  client ne voient l'écart. L'écran complet ne se joue qu'au faux back.
- **Proposition** : rattacher les deux opérations à un EPIC (EP-13 porte déjà leur jumelle
  `getBackupSchedule`/`setBackupSchedule`), ou rouvrir WF-ADM-0070-A le temps qu'elles soient
  servies ; retirer alors la tolérance du 404 de `users/page.tsx`. Preuve : un test du back avec
  `ContractClient` sur `GET` puis `PUT /identity-sync-schedule`, et un parcours `@shared
  @administration` qui règle la fréquence et la relit.
- **Confiance** : confirmé (recherche des deux identifiants dans tout `docs/roadmap/`, routes du
  back inventoriées, page du front lue). Non vérifié : l'existence d'une issue GitHub hors du
  dépôt (#1676 ne concerne que la régression du parcours `installation.setup`,
  `tools/queue-known.toml:520-527`).
- **Gravité** : rendue majeure, pas bloquante : la phrase du Vérif (« au terme de la périodicité
  choisie, sans intervention ») tient avec un intervalle d'exploitation ; c'est le corps de
  l'exigence et la décision A-02 qui ne tiennent pas. Au coordinateur de trancher.

## Constats mineurs

### CTC-02 — `undoLastChange` et `redoLastUndo` peuvent répondre 422, que le contrat ne déclare pas

- **Issue** : #4466 (EP-38), ouverte le 2026-11-21, avec CTA-08, CTA-09, CTB-08.
- **Où** : `backend/src/waterfall/core/planning/restoring.py:475` et `:524`
  (`redated_structure`) → `core/planning/rescheduling.py:113-119` (`horizon_exceeded`) et
  `core/planning/dating.py:102`, `:156`, `:158` ; routes `backend/src/waterfall/api/history.py:119`
  et `:133` ; contrat `docs/api/paths/revisions.yaml:2535-2637` (`undoLastChange` : 200, 401, 403,
  404, 409, 500, 503) et `:2642` (`redoLastUndo`, mêmes statuts).
- **Quoi** : une annulation réécrit ses objets puis rejoue le moteur de dates ; le moteur refuse
  par 422 (`PROJECT_HORIZON_EXCEEDED`, `LINK_CYCLE`, `LINK_FORBIDDEN`), statut absent des deux
  opérations.
- **Scénario** : T précède U (fin-début). A raccourcit T de 10 j à 5 j (entrée de sa pile). B
  allonge U jusqu'à quelques jours sous l'horizon de quinze ans (WF-PLA-0150) : U change de
  compteur, pas T (« what the server recalculates … does not advance the counter of any node »,
  `common.yaml:124-129`). A annule : `_judge` (`core/history/interface/undo.py:214-224`) ne compare
  que les objets de l'entrée, T est à sa version, la restauration passe ; `replayed` recalcule,
  U dépasse l'horizon, `raise horizon_exceeded(…)` → 422. Le conflit n'est pas un
  `UNDO_CONFLICT` : l'objet écrit depuis n'est pas celui de l'entrée.
- **Ce qui a été vérifié** : aucun `except` entre `bring_back` et la route ; aucun test de
  `test_history.py` ni de `test_undo_routes.py` n'attend un 422 ; Prism en proxy laisse passer un
  statut non déclaré avec un simple avertissement (`frontend/e2e/service/contract.ts`, en-tête),
  seul `ContractClient` le refuserait, s'il jouait ce cas. Le front décode tout statut portant une
  enveloppe (`api/problem.ts:375-389`) : l'utilisateur lit le refus, le défaut est d'abord celui
  du contrat.
- **Proposition** : déclarer le 422 sur les deux opérations, comme pour toute écriture de l'arbre
  (« an undo is subject to the rules of entry »), avec un exemple, puis `make generate-client` ;
  test du back : le scénario ci-dessus par `ContractClient`, qui échoue aujourd'hui sur le statut.
- **Confiance** : confirmé par lecture ; scénario non exécuté.

### CTC-03 — le 413 de `previewPaste` ne peut pas être rendu : le service ne borne aucun corps JSON

- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `docs/api/paths/revisions.yaml:2427` (`'413': PayloadTooLarge`) ;
  `docs/api/components/schemas/revisions.yaml:2441` (« The block has no limit of height but the
  size of the request (413) ») ; `docs/roadmap/EP-06-planification.md:767-768` (« Aucune borne
  nouvelle : `PASTE_TOO_WIDE` et la taille de la requête (413) suffisent ») ;
  `backend/src/waterfall/api/history.py:77-93` ;
  `backend/src/waterfall/api/contract/models.py:4913` (`rows: list[list[str]]`, `min_length=1`,
  sans maximum) ; `backend/src/waterfall/api/main.py:61-67` (uvicorn sans borne).
- **Quoi** : la conception d'EP-06 fait de la taille de la requête la seule borne de hauteur d'un
  bloc collé ; rien, dans le service ni dans `deploy/compose/Caddyfile.prod`, ne borne un corps
  JSON. Les seuls 413 du back sont ceux des dépôts (`avatars.py`, `imports.py`, `uploads.py`).
- **Scénario** : un contributeur colle un bloc de plusieurs centaines de milliers de lignes. Sous
  12 Mo, l'action serveur de Next le transmet (`frontend/next.config.ts:42`) et le service juge
  chaque ligne dans la transaction de la requête, sous le verrou de la structure ; au-delà, c'est
  Next qui échoue avant l'API (écran d'échec, pas le refus 413 du contrat). Le 413 déclaré n'est
  jamais émis.
- **Proposition** : une borne du corps des écritures JSON dans le service (un intergiciel qui lit
  `Content-Length` et compte les octets reçus, comme `_bounded` d'`imports.py:106-122`), ou un
  `maxItems` sur `PastePreview.rows` au contrat avec son refus nommé ; test : un bloc au-delà de
  la borne reçoit 413 `FILE_TOO_LARGE` par `ContractClient`, rien n'est gardé.
- **Confiance** : confirmé pour l'absence de borne (recherche dans `backend/src/waterfall` et
  `deploy/`) ; le coût d'un très grand bloc n'a pas été mesuré.

### CTC-04 — `getProjectWorkload` répond 500 dès qu'un rôle actif a une capacité inférieure à 0,000001 h

- **Suite** : sans objet depuis la revue, vérifié le 2026-11-21 — depuis US-2410 (EP-10, sur
  `main`), la capacité mensuelle d'un rôle ne s'écrit plus : la colonne
  `resource_role.monthly_hours` est supprimée, seul l'effectif est saisi, et les heures sont
  calculées en SQL puis arrondies au centième (`func.round(…, 2)`). Le `str()` de `workload.py:57`
  demeure, mais ne reçoit plus qu'un décimal à deux chiffres, que `str()` n'écrit jamais en notation
  scientifique.
- **Où** : `backend/src/waterfall/api/workload.py:41` (`"capacity_monthly_hours":
  str(role.capacity_monthly_hours)`) ; `core/estimate/workloading.py:297-302` ;
  `core/resource_settings/tables.py:140` (`monthly_hours: Numeric`, sans précision) ;
  `core/resource_settings/interface/resource_roles.py:77` et `:382-392` (seule règle : `>= 0`) ;
  `api/contract/models.py:350-357` (`Decimal`, motif `^-?\d+(\.\d+)?$`).
- **Quoi** : `str()` d'un `Decimal` passe en notation scientifique sous 10⁻⁶ ; le modèle engendré
  `WorkloadPlan` refuse alors la valeur, et l'erreur de validation de la réponse sort en 500.
  Partout ailleurs le service écrit `format(valeur, "f")` (`resource_roles.py:128-130`,
  `calendars.py:101-103`, `nodes.py:333-340`).
- **Scénario** : un gestionnaire du référentiel crée ou modifie un rôle de ressource avec
  `capacity.monthly_hours` à `"0.0000001"` : accepté (201/200, le motif `Hours` l'admet, la règle
  ne refuse que le négatif), et relu correctement par `listResourceRoles`. Tout
  `GET /projects/{id}/workload` liste ensuite ce rôle (tous les rôles actifs le sont,
  `workloading.py:283`) : `str(Decimal("0.0000001"))` vaut `'1E-7'` (vérifié sous Python 3.13),
  `WorkloadPlan.model_validate` lève, `CorrelationMiddleware` répond 500 `INTERNAL_ERROR`, pour
  tous les projets, jusqu'à correction du rôle.
- **Proposition** : `format(role.capacity_monthly_hours, "f")` (et de même aux deux autres `str()`
  du module, l. 45 et 68, sans effet aujourd'hui car arrondis au centième) ; test : un rôle de
  capacité `0.0000001`, le plan de charge lu par `ContractClient` rend `"0.0000001"`. À voir par
  les relecteurs du back : la capacité échappe aussi à `exceeds_precision`
  (`platform/decimals.py`), que #2875 applique aux autres décimaux écrits.
- **Confiance** : confirmé par lecture et par la conversion rejouée ; route non exécutée.

### CTC-05 — les corps redéclarés à la main ne sont tenus au contrat par aucun test

- **Issue** : #4452 (EP-36), ouverte le 2026-11-21.
- **Où** : `backend/src/waterfall/api/projects.py:103-121` (`ProjectCreateBody`,
  `ProjectUpdateBody`), `subprojects.py:72-90` (`SubprojectWriteBody`, `SubprojectUpdateBody`),
  `reference_settings_write.py:35-63` (`ThresholdsWrite`, `SettingsWrite`), et les corps que le
  contrat écrit en ligne : `calendars.py:88-98`, `cost_types.py:73-77`, `org_nodes.py:54-65`,
  `resource_roles.py:89-93`, `timelines.py:42-46`.
- **Quoi** : ces modèles doublent `ProjectCreate`, `ProjectUpdate`, `SubprojectWrite`,
  `SubprojectUpdate` et `ReferenceSettingsWrite`, que `contract/models.py` engendre
  (l. 2639, 2658, 2920, 2925, 1909), avec leurs bornes recopiées (`max_length=300`, `pattern=r"\S"`).
  Le doublement est voulu et dit (rendre les trois codes du contrat là où le modèle engendré n'en
  rend qu'un). Mais `test_contract_declarations.py:583` ne tient au contrat que les bornes des
  **paramètres** (#1873) : une borne de corps qui change au contrat ne casse rien.
- **Scénario** : le contrat porte `ProjectCreate.label` à 200 caractères ; `make
  generate-server-models` régénère `ProjectCreate`, que la route n'emploie pas ; le service
  accepte toujours 300. Aujourd'hui les bornes coïncident (comparées une à une pour les cinq
  schémas nommés).
- **Proposition** : étendre le test des bornes aux corps des opérations dont la route déclare un
  modèle local (coût : une trentaine de lignes, le lecteur de bornes existe déjà) ; risque de ne
  rien faire : une dérive silencieuse à la prochaine révision du contrat.
- **Confiance** : confirmé.

### Déjà connus et planifiés (rappel, non recomptés)

- **CTC-06** — `backend/src/waterfall/api/backups.py:107-119` : `listBackups` n'accepte que
  `limit` et `offset` ; les neuf filtres et tris du contrat (`from`, `to`, `is_retained`,
  `origins`, `size_bytes_min/max`, `verifications`, `sort_by`, `sort_order`) sont ignorés sans
  refus. Majeur, **déjà connu (#2231, EP-13)**.
  **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-13, `BackupsQuery` porte
  `from`, `to`, `origins`, `verifications`, `is_retained`, `size_bytes_min/max`, `sort_by`,
  `sort_order`, jugés par `backup_filters` (422 sur une borne inversée) et passés à `list_backups`
  (US-2910/L2, 1686e66ae). Pas encore sur `main`.
- **CTC-07** — `backups.py:129` et `:142-160` : les 409 déclarés de `startBackup` et de
  `downloadBackup` (sauvegarde non vérifiée, sauvegarde en cours) ne sont jamais levés ; une
  archive non vérifiée se télécharge. Majeur, **déjà connu (#1035, EP-13)**.
  **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-13, `startBackup` prend les
  deux verrous puis `refuse_if_lacking(backup_start_lacks(…))`, et `downloadBackup` appelle
  `refuse_if_lacking(download_lacks(view.verification))` avant de lire l'archive : une archive non
  vérifiée n'est plus copiée (US-2910/L2, 1686e66ae).
- **CTC-08** — `backups.py:66-88` : les commandes `retain`/`release` sont annoncées disponibles
  alors que `retainBackup` n'est pas servi. Mineur, **déjà connu (#2241, EP-13)**.
  **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-13, `retainBackup` est servie
  (`PATCH /backups/{backup_id}`), et la commande de marquage n'est listée que sous la permission de
  modifier, avec `marking_lacks(platform)` pour condition manquante (US-2910/L2, 1686e66ae).
- **CTC-09** — huit paramètres de requête bornés au contrat et lus en texte par le service
  (`rate_*`, `headcount_*`, `monthly_hours_*`, `correlation_id`, `actions`). Mineur, **déjà connu
  (#2303, EP-13)**.
  **Suite** : sans issue propre, vérifié le 2026-11-21 — tombera avec issue #2303 (EP-13, ouverte),
  US-3020/L3 (#4109).
- **CTC-10** — parcours joués contre le seul faux back sous quarantaine nommée :
  `frontend/e2e/revisions.spec.ts:132` (#3192, EP-27), `structure.spec.ts:344` (#3087, EP-26),
  `reference-costs.spec.ts:382` et `:486` (#3190, #3191, EP-25). Mineur, **déjà connu**.
  **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — les constantes `QUARANTINED_3192`,
  `_3087`, `_3190` et `_3191` et leurs `test.skip(inService, …)` ont disparu : « quarantin » ne se
  trouve plus dans `frontend/e2e` sur aucune des quatre branches, et `structure.spec.ts:337` dit le
  parcours « Played against the service again (US-2290, #3087) ». Les quatre issues sont fermées (du
  2026-11-14 au 2026-11-18).

## Points forts

- Inventaire croisé sans reste : 132/132 routes au contrat ; statuts de garde cohérents (404 pour
  une permission de consultation, 403 pour une écriture, 401, 400 avec corps, 422 avec requête)
  sur toutes les routes, vérifié contre `Requires`/`RequiresProject` et `CONSULTATION`.
- Les réponses écrites en `dict` à la main (`nodes.py:451-534`, `comparison.py`, `history.py`,
  `estimate_indicators.py`, `remaining_indicators.py`, `rate_update.py`, `startable_tasks.py`)
  ont été confrontées clé par clé aux schémas : aucune clé hors schéma, aucun champ requis omis,
  aucun `None` sur un champ non nullable. Le contournement de `nodes.py` est motivé (#3048).
- `ContractClient` (`backend/tests/support.py:444-476`) valide chaque réponse des tests contre le
  contrat, propriétés non déclarées comprises.
- `problem_response` refuse un code hors `ErrorCode` (`problems.py:65`) ; aucun modèle rendu sans
  `exclude_unset` ne porte de propriété facultative non nullable.
- Front : client typé par opération, faux client des tests typé par les exemples que le contrat
  cite (`frontend/src/test/fixtures.ts`), `fakeClient` refusant un statut non déclaré.
- Faux back : aucune réponse écrite à la main ; chaque 2xx JSON du contrat a un exemple.

## Couverture

- **Lu en entier** : `docs/api/openapi.yaml`, `INVENTORY.md`, `components/responses.yaml` ;
  `backend/src/waterfall/api/{app,main,problems,middleware,maintenance,authentication,evaluation,
  queries,actual_costs,backups,avatars,uploads,comparison,history,workload,system}.py`,
  `contract/base.py`, `platform/errors.py`, `platform/decimals.py` ;
  `frontend/src/api/{client,server,relay}.ts`, `frontend/e2e/mode.ts` ; guide, sections « Le
  client de l'API » et « Le faux back ».
- **Analysé par script, exhaustivement** : les 170 opérations du contrat et les 132 routes
  (méthode, chemin, identifiant, statuts, paramètres, corps, gardes) ; les statuts d'erreur
  atteignables par graphe d'appels approché sur `backend/src/waterfall` (résolution par nom : un
  appel par registre ou par méthode d'un objet passé en paramètre peut lui échapper) ; les codes
  d'erreur ; les 1 587 exemples contre leur schéma ; les littéraux de code du front.
- **Échantillonné** : `nodes.py`, `imports.py`, `exports.py`, `projects.py`, `users.py`,
  `calendars.py`, `resource_roles.py`, `reference_settings_write.py`, `subprojects.py`,
  `lifecycle.py` (parties signalées par les scripts) ; `frontend/src/api/problem.ts` ;
  `frontend/e2e/*.spec.ts` (les 182 emplois de `inService` listés, les `test.skip` lus) ;
  `frontend/e2e/service/contract.ts` (140 premières lignes).
- **Non lu / non vérifié** : `make server-models-up-to-date` et `make client-up-to-date` non
  lancés (sondes seulement : opérations, codes, noms de schémas ; le dernier commit du contrat,
  `862c3ab`, ne fait que recouper des paragraphes) ; `contract/models.py` et `schema.d.ts` non
  relus ; le noyau au-delà des chemins cités ; les routes qui passent par `model_validate` ne
  sont pas prouvées exemptes d'un `None` sur un champ requis (ce serait un 500, que seuls les
  tests voient) ; les formats des feuilles (dates, montants) n'ont été vérifiés que sur les
  conversions `str()`/`format()` de la couche d'API ; les tests du front et leurs réponses
  bâties à la main ; `frontend/src/api/actions/*.ts` (seulement cherchés par motif).

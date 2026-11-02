---
revue_du: 2026-10-28
sur: >-
  le contrat d'interface docs/api sur epic/EP-16 (a735115c, info.version 1.0.0-draft : 163
  opérations, 127 chemins, 13 familles), ses fixtures (fixtures/api, 598 fichiers, dont 18 de
  volume) et la spécification waterfall-spec.md en révision 1.0.0
revue_par: Claude Code (Fable 5.1) — dix relectures par famille, trois vérifications du delta de la spécification, une consolidation
perimetre: >-
  le contrat entier avant le gel (US-0640/L5, #1333), hors ce que portent les quatre lots de
  contrat restants (US-0640/L6 #1457, US-0680/L1 #1453, US-0700/L1 #1455, US-0640/L5 #1333)
---

# Revue du 2026-10-28 — le contrat avant le gel

## Pourquoi cette revue, et comment elle a été faite

EP-16 fige le contrat à l'issue de quatre lots encore ouverts ; après le gel, toute modification
passe par une issue tranchée par l'auteur. Cette revue cherche ce qu'il faut corriger **avant**, par
ordre d'importance : ce qu'il serait coûteux de changer après (un champ, un statut, une énumération,
une opération que la spécification exige et que le contrat ne porte pas), ce qui ferait mal
implémenter le service ou le front (une description ambiguë ou contraire à la spécification, une
fixture qui contredit sa description), et la qualité (exemples et descriptions manquants).

La revue part d'un contrat formellement sain : `make check-contract` passe sur la branche (lint,
inventaire, fixtures et modèles du service à jour), le front appelle 156 des 163 opérations (les sept
autres sont justifiées : sondes, annuler/rétablir câblés par EP-06, trois lectures unitaires), toutes
les exigences citées existent, et une seule fixture n'est référencée par aucun fichier du contrat.

Treize relectures ont été menées en parallèle, chacune sur ses fichiers du contrat, les fixtures
qu'ils référencent, les sections de la spécification correspondantes et `DECISIONS.md` :

- dix par famille — A système et comptes, B plateforme et audit, C référentiel, D projets,
  E révisions et structures, F arbre commun, G indicateurs et portefeuille, H risques, I coûts réels
  et échanges, J transversal (composants partagés, conventions, relevé par script des 163
  opérations, 87 codes, 54 conditions, 1 291 propriétés et 618 références de fixtures) ;
- trois sur le **delta de la spécification** (K, L, M) : entre le 2026-10-07 et le 2026-10-22, les
  passes de cohérence des 9 et 10 octobre (commits 7dc06e9d et b18a8883, constats C-104 à C-350) et la
  reprise du 2026-10-22 (C-366 à C-375) ont changé le corps ou la Vérif de **137 exigences**. Ces trois
  relectures ont confronté chaque changement au contrat, exigence par exigence (leur « Relevé » dit le
  verdict pour chacune des 137).

Chaque constat est vérifié à la ligne du fichier, cite la spécification et dit si une décision de
`DECISIONS.md` l'explique. Les constats que plusieurs relectures ont trouvés sont fusionnés (le
tableau général nomme les doublons) : **210 constats bruts, 174 après fusion — 4 bloquants,
83 majeurs, 87 mineurs.** Une précision de datation : plusieurs relecteurs ont d'abord attribué les
phrases nouvelles de la spécification au commit de la révision 1.0.0 (51305dd, 2026-10-24) ; ce commit
n'a changé que le numéro de révision, et les phrases datent des 9 et 10 octobre. Les annexes sont
corrigées en ce sens.

Les gravités sont celles du brief : **bloquant**, le contrat contredit frontalement la spécification
ou ne peut pas être servi tel quel sur ce point ; **majeur**, un changement incompatible à prévoir
après le gel si on ne le fait pas maintenant, ou un implémenteur se tromperait ; **mineur**, clarté,
exemple ou description, corrigible sans rompre le contrat.

## Ce que la revue exclut

Rien n'est signalé de ce que les quatre lots restants font déjà : `apply_rate_update`, la pagination
de `listRisks`, `NON_WORKING_DAY` sur `createNode`, le collage ancré sur un nœud retiré, les exemples
#1379 et #1384, la préférence d'états de l'accueil, `display_name` nullable des contributeurs,
`project_create` et `revision_abandon` dans `AuditAction`, `NodeChange.payment_delay_days`, les exemples
#1531 (US-0640/L6) ; `getRiskOccurrenceReport` et les compteurs de `RiskOccurrence` (US-0680/L1) ; le
filtre `difference` et le décompte de `RiskMatrix.cells` (US-0700/L1) ; la version 1.0.0 et la règle
d'après (US-0640/L5). Ne sont pas signalés non plus les choix que `DECISIONS.md` assume quand ils ne
contredisent pas la spécification actuelle.

## Ce qui ressort

### 1. Le contrat n'a pas suivi la spécification des 9 et 10 octobre

C'est le constat qui domine. Les lots d'EP-14 (L42h à L42s) et d'EP-15 ont rattrapé une partie des
137 exigences changées, mais pas toutes, et `DECISIONS.md` garde des décisions antérieures que la
spécification contredit désormais. Ce que les trois vérifications du delta relèvent comme **non
porté**, par ordre de poids :

- **les montants budgété et réestimé** : « inflation comprise, à l'année de consommation » dans la
  spécification (WF-DEV-0020, WF-DEV-0050, glossaire) ; « à l'année de référence » à douze endroits du
  contrat, sur les décisions #235 et #352 d'EP-02 (L-01, bloquant) ;
- **le coût à la survenance** d'un risque, attribut figé que la couverture compare à la réserve
  (WF-RIS-0010, WF-RIS-0050) : le contrat compare le montant réestimé, vivant, et le risque n'a pas
  l'attribut (H-01 bloquant, H-02) ; la **réserve pour risques** n'est plus celle de la seule révision
  de référence mais un cumul à travers les références (M-01) ;
- **la date de début de planning d'une structure**, saisie, dont dépend toute tâche automatique sans
  prédécesseur et que l'import et l'export MS Project lisent et écrivent (WF-PLA-0020, WF-REV-0100) :
  ni champ ni opération (E-01 bloquant, I-03) ;
- **la sortie du cycle de vie** d'un projet qui porte une révision en cours doit la marquer ou
  l'abandonner « dans la même opération » (WF-CYC-0090) : `ProjectExit` ne porte pas le choix (D-01
  bloquant) ; « Déclarer perdu » ne doit plus figurer sur un projet En cours (D-02) ; le dernier chef de
  projet désactivé ouvre l'inscription à un non-contributeur (D-06) ;
- **les courbes d'un projet** au pas du mois, conservées avec la révision marquée, sur le coût réel
  connu au marquage (WF-IND-0100, WF-IND-0110, WF-IND-0010, WF-DAT-0040) : le contrat les recalcule au
  jour sur le coût réel connu aujourd'hui (G-01, M-02) ; les indicateurs au jour courant d'un projet
  sans révision en cours (M-03) ; le diagramme temps/temps (M-10) ; les décaissements (M-06) ;
- **l'arbre commun** : marge et criticité d'une récapitulative (F-01), conflit d'une tâche manuelle
  nommant la liaison (F-02), une seule liaison entre deux tâches (F-03), récapitulative qui redevient
  feuille ou jalon (F-14), lignes de provision d'une tâche supprimée (F-04), colonnes de démarrage et de
  terminaison dans `NodeColumn` (F-07), jalon terminé et sa date de démarrage (F-13), la fusion qui donne
  aussi les grandeurs courantes (L-14), les deux écarts de la comparaison (E-02), le plan de charge sur
  une révision marquée et après la date de calcul (L-16), le reste à engager d'une ligne jamais
  réestimée (M-08, M-09) ;
- **les échanges** : lignes « inchangées et rejetées » du journal des imports (I-01), code de rejet
  d'une ligne de coût sur son élément d'OTP (I-02), récapitulative manuelle importée et date de début
  de planning au compte rendu (I-03, I-04), lignes de provision ignorées ou conservées (I-05), exports
  stockés jusqu'au premier téléchargement complet (I-07), la date de la revue que porte le fichier
  (I-09, où la spécification se contredit elle-même) ;
- **la plateforme** : périodicité de la lecture des comptes (A-02), paramètres d'exploitation sur
  l'écran d'état (A-03), renvoi du courriel de fixation du mot de passe (A-04), `can_open` du journal
  (B-03), `amendment_merge` devenu « fusion d'un différentiel » (K-04) ;
- **le portefeuille** : contribution d'une offre hors provisions au budget et provisions comprises au
  reste, risques non pondérés (M-07), couverture « en cours et terminés » (G-06), projets terminés sans
  période sur quatre vues (G-05).

La révision 1.0.0 de la spécification est publiée ; c'est le contrat qui est en retard. Chaque annexe
K, L, M nomme la décision antérieure que la spécification contredit, à réécrire dans `DECISIONS.md`.

### 2. Deux formes pour un même refus, et un catalogue qui porte des codes morts

- Un projet terminal est refusé par **403 `PROJECT_TERMINAL`** sur `deleteTimeline` et le squelette, par
  **409 `STATE_FORBIDS_OPERATION`/`project_not_terminal`** sur six autres écritures ; `createTimeline` ne
  dit rien ; deux décisions (L42k et L42i/L42l) se contredisent (D-05, J-01). De même **`REVISION_MARKED`**
  (403) n'est rendu par personne quand les écritures d'une révision marquée sont 409 `revision_draft`
  (J-02).
- **Onze codes d'`ErrorCode`** ne sont cités par aucune opération ni aucun schéma hors `common.yaml`
  (`NOT_PROJECT_MANAGER`, `REVISION_MARKED`, `UNDO_CONFLICT`, `TASK_ALREADY_STARTED`, `TASK_COMPLETED`,
  `SUMMARY_TASK_DERIVED`, `RESOURCE_ROLE_REQUIRED`, `HOURLY_RATE_MISSING`, `PROJECT_CODE_REQUIRED`,
  `UNKNOWN_RESOURCE_ROLE`, `INTERNAL_ERROR`), et vingt n'ont aucun exemple (J-03, J-17). Trois d'entre
  eux portent un refus que la spécification exige et que l'opération décrit sans code : les subordonnées
  d'une récapitulative (J-04, F-05), l'objet en conflit d'une annulation (E-07, J-05), le taux manquant
  (J-06). `CommandCondition` porte trois valeurs mortes et deux employées sans définition (J-11).
- **Aucune opération ne déclare le 500** `INTERNAL_ERROR` ni de `default`, alors que `Problem` promet un
  `correlation_id` (J-07) ; `fields` est le seul paramètre de requête refusé par 400 (J-10).
- Des refus déclarés sans code, condition ni exemple : `exitProject` (D-03), `deleteNode` (F-04),
  `markRevision`/`abandonRevision`/`createCostStructure` (E-12 à E-14), `declareRiskOccurrence` (H-08),
  `requestExport` (I-17), `getBackgroundTaskResult` (A-05), `setActualCostTrackedScope` sans 409 (I-06),
  `setNodeTracking` sans 409 (F-11), trois listes du référentiel sans le 403 d'`include_inactive` (C-01).

### 3. Des attributs et des opérations que la spécification exige

Au-delà du delta : la devise lisible par qui voit un montant (C-02) ; `AuditProject.code` nullable (B-01)
et `AuditParams` fermé sur des paramètres remis « à l'EPIC qui les réalise » (B-02) ; `BackupSchedule` aux
champs facultatifs (B-04) et sa rétention ambiguë (B-05) ; `Revision` sans taux d'inflation ni
probabilité de gain conservés (E-03) ni révision source (L-05) ; `StructureMerge` sans description (E-04)
ni refus du nom pris (E-05) ; `UndoResult` sans `NodesWritten` (E-08) et l'historique annulable tenu par
le serveur quand la spécification le place dans le front (E-06, question à trancher) ; `createCostStructure`
qui doublonne `createRisk` (E-09) ; `Import` sans structure, révision ni période (I-08) ;
`EstimateLineWrite` exigeant le libellé que le serveur compose et la catégorie que le rôle détermine
(F-08, F-09) ; une ligne de provision qui accepte la réestimation (F-10) ; `listNodes` sans les filtres
de colonnes que WF-IHM-0060 impose à toute grille (F-06).

### 4. Du facultatif là où tout est toujours rendu

Des champs que toutes les fixtures portent et que la spécification exige sont facultatifs dans le
schéma : les avancements, écarts et projections de `ProjectIndicators`, `is_stored`, la capacité des rôles,
la zone des mois, les parts (G-02) ; `is_critical` et `total_float` (F-01) ; `BackgroundTaskRef` (A-09) ;
`UserAccount.org_node_id` (A-08) ; `SystemStatus.last_*` (B-08) ; `Risk` (H-07) ; `ImportReport`,
`ActualCostLine` (I-13) ; `ActorRef.user_id` pour un compte (A-07). Les exiger est compatible pour tout
lecteur aujourd'hui, incompatible pour les producteurs après le gel.

### 5. Les fixtures

Le témoin est arithmétiquement juste presque partout (formules des indicateurs, parts à quatre
décimales, totaux, versions, journal) ; les écarts relevés : le rôle « Manager » sans
`risk_settings.write` ni `indicator_settings.write` (A-01) ; les récapitulatives sans marge ni
criticité (F-01) ; les compteurs faux de `structure_merge_report_without_current_revision` (E-10) ;
`revision_offer` sans ses exports et le compteur initial sans règle (E-15, E-16) ; une chronologie des
sauvegardes qui se contredit (B-07) ; `format_version: "1"` sur une extraction ERP (I-12) ; les indices
du portefeuille à deux décimales (G-08) et dix pour cent de « Provision » dans le budget agrégé (G-15) ;
un point à l'offre dans le diagramme temps/temps (M-10) ; des tâches fusionnées en mode automatique
(M-05) ; `lose` listée sur un projet En cours (D-02) ; `risk_matrix_no_basis` orpheline (J-21).

## Ce qu'il faut trancher avant le gel

Les points que la revue ne peut pas décider seule, par ordre de conséquence sur la forme du contrat :

1. **L'inflation dans le budgété et le réestimé** (L-01) : suivre la spécification (le sens de deux
   champs de la ligne, de la tâche, des totaux, des indicateurs et de la comparaison change ;
   `inflated_amount` disparaît ou devient le réestimé) ou faire corriger la spécification.
2. **Où vit l'historique annulable** (E-06, L-18) : serveur par session, comme le contrat, et corriger
   WF-IHM-0110 ; ou front par page, et `undo`/`redo` reçoivent un corps qui désigne l'entrée à défaire.
3. **La sortie du cycle de vie** (D-01) : le corps porte le sort de la révision en cours ; la réponse
   reste 200 ou devient 202 quand elle marque (le marquage est une tâche de fond).
4. **La date de terminaison d'une tâche terminée par l'import** (I-09) : WF-PLA-0130 dit le jour
   d'application, WF-INTF-0120/0130 la date de la revue que porte le fichier ; le contrat a suivi la
   première.
5. **Le sens de la marge du reste à engager** (G-07) : décision de l'auteur #466, contraire au Vérif de
   WF-RAE-0020 ; c'est la spécification qui est à aligner.
6. **Projet terminal et révision marquée : 403 ou 409** (D-05, J-01, J-02) ; et le sort de chaque code
   mort (J-03) : employé par une opération ou retiré.
7. **Les noms que la table du §4.4.1 fixe** : `audit_event` ou `audit_entry` (B-06) ; `labor` et
   `LABOUR_` (C-08) ; `amendment_merge` ou `structure_merge` (K-04, à faire avec #1577 dans US-0640/L6).
8. **Les opérations manquantes** : planification de la lecture des comptes (A-02), renvoi de
   l'invitation (A-04), écriture d'une structure (E-01), inscription d'un chef de projet par un
   non-contributeur (D-06) ; la liste des paramètres d'exploitation de l'écran d'état (A-03).
9. **La devise** : `Installation.currency_code`, ou `getReferenceSettings` ouvert à toute session (C-02).
10. **Les risques** : `updateRisk` et la probabilité produisent-ils un réexamen (H-04) ; `provision_amount`
    d'un survenu ou d'un écarté (H-03) ; `StructureCreate.kind: risk` (E-09) ; le placement des tâches
    fusionnées par la survenance, à écrire avec US-0680 (M-05).
11. **Le contrôle du format d'un import** : synchrone à l'ouverture ou dans l'analyse (I-10).
12. **La ligne de devis** : libellé composé par le serveur (F-08), catégorie d'une ligne de main-d'œuvre
    tenue du rôle (F-09), un indicateur « réestimée depuis la grille » et l'année des montants du reste à
    engager (M-08).
13. **`lock_version` sur les suppressions et les écritures sans compteur** : `abandonRevision`,
    `exitProject`, `designateReferenceRevision`, `deleteRisk`, `deleteSubproject`, `tracked-scope`
    (E-13, E-24, J et I, « Doutes »).
14. **Les paramètres du journal** pour `project_exit`, `restore`, `import_apply` (B-02) ; le sens
    d'`horizon_months` et les projets terminés sans période sur quatre vues du portefeuille (G-04,
    G-05) ; `BackupSchedule.retained_count` et les manuelles (B-05).

## Recommandation

Le contrat tel qu'il est, une fois les quatre lots restants livrés, **ne peut pas être figé sans
rompre avec la spécification 1.0.0** sur les quatre points bloquants et sur une partie des majeurs :
chacun changerait, après le gel, le sens d'un champ existant, un statut HTTP, une énumération ou un
corps d'écriture. La revue propose :

- **un lot de contrat avant US-0640/L5**, consacré au delta de la spécification des 9 et 10 octobre
  (annexes K, L, M, et les constats des familles qui en relèvent), qui réécrit aussi les décisions
  contredites de `DECISIONS.md` ; au vu de l'estimation de L6 (≈ 900), il se coupe en deux : le modèle
  (L-01, E-01, D-01, H-01/H-02, E-03, L-05, E-02, F-07, I-01 à I-05, I-08, A-02 à A-04, B-01 à B-04) et
  les règles de calcul et de description (M-*, L-14, L-16, F-*) ;
- **un lot des refus** : les deux formes du projet terminal et de la révision marquée, les codes et
  conditions morts, le 500, le 422 de `fields`, les refus sans code ni exemple (annexe J, D-03, D-05,
  E-12 à E-14, F-04, F-05, F-11, H-08, I-06, I-17, C-01) ;
- **les champs à exiger et les descriptions**, qui peuvent se répartir sur ces lots ou sur US-0640/L6
  quand elles touchent un fichier qu'il modifie déjà (K-04 avec #1577 ; J-21 et H-08 avec US-0700/L1 et
  US-0680/L1) ;
- **les questions ci-dessus**, à poser à l'auteur en une fois, parce que plusieurs changent la forme du
  lot (L-01, E-06, D-01, I-09) ; et, côté spécification, trois points à ouvrir (G-07, I-09 et la
  contradiction WF-PLA-0130/WF-INTF-0120, #1589 déjà ouvert).

Le gel (US-0640/L5) vient alors après ces lots, comme la décision du 2026-10-28 le prévoit déjà pour
les derniers lots de l'EPIC.

## Tableau général des constats

Un constat par ligne, fusionné quand plusieurs relectures l'ont trouvé (« aussi » nomme les doublons,
dont le détail figure dans leur annexe). L'emplacement est abrégé ; l'annexe donne la ligne exacte, la
citation de la spécification, ce que dit le contrat, la proposition et la décision de `DECISIONS.md`.

### Bloquants (4)

| # | Famille | Emplacement | Constat | Exigence |
|---|---|---|---|---|
| D-01 (aussi L-02) | D | `schemas/projects.yaml:557-574` (`ProjectExit`), `paths/projects.yaml… | La sortie d'un projet qui porte une révision en cours ne reçoit pas le choix « la marquer (nom de version) ou l'abandonner », exigé « dans la même opération » ; `project_completed` montre la révision 102 disparue sans que rien ne dise comment | WF-CYC-0090 |
| E-01 (aussi L-06) | E | `schemas/revisions.yaml:277-308` (`CostStructure`), aucune opération | La date de début de planning d'une structure, « saisie », n'est portée par aucun schéma ni aucune opération du contrat | WF-REV-0100, WF-PLA-0020 |
| H-01 | H | `schemas/risks.yaml:489-507` (`RiskCoverageTotals.occurred_cost`), `p… | Le coût des risques survenus de la couverture est défini comme le **montant réestimé** des lignes fusionnées ; la spec (révision 1.0.0) le définit comme le **coût à la survenance**, figé, que ni réestimation ni terminaison ne changent | WF-RIS-0050, WF-RIS-0010, glossaire « Coût à la survenance » |
| L-01 | L | `schemas/revisions.yaml:1300-1308, 1354-1367` (`EstimateLineFacet`),… | Les montants budgété et réestimé sont « à l'année de référence » dans tout le contrat ; la spec les veut « inflation comprise, à l'année de consommation », le montant avant inflation n'étant qu'une valeur de lecture | WF-DEV-0020, WF-DEV-0050, WF-DEV-0030, WF-PRJ-0040 |

### Majeurs (83)

| # | Famille | Emplacement | Constat | Exigence |
|---|---|---|---|---|
| A-01 (aussi K-09) | A | `fixtures/api/access_roles.json:212-236` (rôle prédéfini « Manager »)… | Le rôle prédéfini « manager » du témoin n'a ni `risk_settings.write` ni `indicator_settings.write`, alors que la spec lui donne le paramétrage de FBS-3.1 à FBS-3.4 entier | WF-INTF-0020, WF-ADM-0010 |
| A-02 (aussi K-01) | A | `paths/access.yaml:535-594` (`startIdentitySync`, `getLatestIdentityS… | La périodicité de la lecture des comptes, « choisie par un utilisateur habilité, quotidienne par défaut, comme celle des sauvegardes », n'a aucune surface : pas d'équivalent de `getBackupSchedule`/`setBackupSchedule` | WF-ADM-0070 |
| A-03 (aussi K-02, K-10) | A | `schemas/platform.yaml:3-36` (`SystemStatus`), servi par `paths/syste… | L'écran d'état ne porte ni « les valeurs en vigueur des paramètres d'exploitation (§4.5.1) » ni « la durée de validité du cache en vigueur », que l'exigence et sa Vérif demandent | WF-ADM-0130 |
| A-04 | A | `paths/access.yaml:468-512` (`createPasswordSetupLink`) | Le « renvoi » du courriel de fixation du mot de passe par un utilisateur habilité n'a aucune opération : le contrat ne porte que l'obtention du lien | WF-ADM-0140 |
| B-01 | B | `schemas/audit.yaml:125` (`AuditProject.code`) | Le code du projet est une chaîne non nulle, quand un projet peut n'en avoir aucun avant En cours : un marquage, une désignation ou une création sur un projet sans code ne peut pas être inscrit | WF-SEC-0030, WF-PRJ-0010, WF-CYC-0030 |
| B-02 | B | `schemas/audit.yaml:173-183` (`AuditParams`) | Objet fermé (`additionalProperties: false`) dont les paramètres des actions d'un projet, de la sauvegarde et de la restauration sont « jusqu'à l'EPIC qui les réalise » vides, et « un paramètre nouveau est une modification du contrat » : à trancher avant le gel (`project_exit` sans état d'arrivée, `restore` sans la date de la sauvegarde restaurée, `import_apply` sans nature) | WF-SEC-0030, WF-CYC-0060, WF-ADM-0160 |
| B-03 (aussi K-03) | B | `schemas/audit.yaml:115-126` (`AuditProject`), `paths/audit.yaml:26-3… | L'inscription doit « mener au projet lorsque l'utilisateur peut le consulter » et ne pas y mener s'il n'existe plus, mais rien ne le dit : le portefeuille et la matrice portent `can_open`, le journal non, et l'écran relit toute la liste des projets pour le savoir | WF-ADM-0190, WF-ADM-0110 |
| B-04 | B | `schemas/platform.yaml:230,234-251` (`BackupSchedule`) | `frequency` et `at_time` facultatifs, `weekday` nullable mais facultatif, pour une planification « à une fréquence et une heure choisies » ; le 422 ne dit ni le jour manquant d'une hebdomadaire ni le jour en trop d'une quotidienne | WF-ADM-0170 |
| B-05 | B | `schemas/platform.yaml:256-259` (`BackupSchedule.retained_count`) | « Le nombre de sauvegardes **planifiées** gardées » contredit la spec (« le nombre de sauvegardes conservées », marquées exceptées) et le contrat lui-même (`is_retained` : « celles que la rotation supprimera à leur tour » ; `backup_released`) : une manuelle non marquée est-elle comptée, et supprimée ? | WF-ADM-0170 |
| B-06 | B | `paths/audit.yaml:3`, `schemas/audit.yaml:128,143` (`/audit-events`,… | La table 10 du §4.4.1 nomme l'objet `audit_entry` ; le contrat dit `audit_event`, sans décision : un renommage est impossible après le gel | §4.4.1, README « Conventions » |
| C-01 (aussi J-08) | C | `paths/reference.yaml:205-206` (`listOrgNodes`), `:874-875` (`listCal… | Trois listes prennent `include_inactive` et `is_active` mais ne déclarent pas le 403 que le paramètre partagé `IsActive` et les trois autres listes du référentiel promettent sans la permission de modification | WF-REF-0150, WF-ADM-0100 |
| C-02 | C | `paths/reference.yaml:31-50` (`getReferenceSettings`), `schemas/refer… | La devise n'est lisible que par `getReferenceSettings`, gardé par une permission de consultation (404) que l'opération ne nomme pas ; aucune lecture ouverte à qui consulte un projet ne la porte, quand elle doit « apparaître partout où un montant est affiché » | WF-REF-0140 |
| C-03 | C | `schemas/reference.yaml:620` (`CostCategoryWrite.accounting_code`), e… | Le code comptable reçu n'a pas `pattern: '\S'` : un code fait de blancs passe le modèle engendré, contre la convention « Aucun libellé fait seulement de blancs » ; les codes lus des nœuds, natures et catégories ne l'ont pas non plus, celui des rôles et de la grille oui | WF-REF-0040, WF-ARC-0110 |
| D-02 (aussi L-03) | D | `schemas/projects.yaml:347-431` (`ProjectCommand`), fixtures `project… | `lose` est listée indisponible (`project_in_pricing`) sur un projet En cours et sur un projet clos, alors qu'une sortie « qui ne le deviendra jamais … n'y figure pas » ; les conditions des trois sorties ne sont décrites nulle part | WF-CYC-0060 |
| D-03 | D | `paths/projects.yaml:325-330` (`exitProject` 409, 422) | Le 409 ne nomme ni code ni `missing_condition` ni ordre, sans exemple ; le 422 est générique : le refus de `confirmed` absent/faux n'a pas de code (422 `VALIDATION_FAILED` ou 400 `CONFIRMATION_REQUIRED` ?) | WF-CYC-0060, WF-CYC-0080, WF-CYC-0090 |
| D-05 (aussi J-01) | D | `paths/projects.yaml:960-971` (`deleteTimeline` 403), `:897-939` (`cr… | Un projet terminal est refusé par 403 `PROJECT_TERMINAL` sur une chronologie et par 409 `STATE_FORBIDS_OPERATION`/`project_not_terminal` sur toute autre écriture du projet ; `createTimeline` ne dit rien | WF-CYC-0100, WF-IHM-0090 |
| D-06 (aussi L-17) | D | `paths/projects.yaml:785-845` (`setContributors`), `schemas/projects.… | « La seule saisie ouverte à un non-contributeur » — inscrire un chef de projet quand le compte du dernier est désactivé — n'est ni décrite ni permise par le contrat, qui réserve l'écriture aux chefs de projet | WF-PRJ-0060 |
| D-07 | D | `schemas/projects.yaml:32-36`, `:477-478`, `:492-493`, `:450-451` (`P… | Le code projet admet `""`, les blancs et la barre oblique : pas de `pattern: '\S'` (convention des codes), et rien n'interdit `/`, seul séparateur de l'élément d'OTP qui le porte | WF-PRJ-0010, WF-CRE-0020, WF-CYC-0030 |
| D-10 (aussi J-09) | D | `paths/projects.yaml:564-594` (`createSubproject`) | Seule opération sous `/projects/{project_id}` sans `404` | WF-ADM-0110 (convention 404) |
| E-02 (aussi L-15) | E | `schemas/revisions.yaml:1979-2014` (`RevisionComparison.amount_deltas… | Un seul `delta` par nature/sous-projet, calculé sur le montant à l'année de référence ; la spec exige l'écart des montants budgétés **et** celui des montants réestimés | WF-REV-0080 |
| E-03 (aussi L-04) | E | `schemas/revisions.yaml:13-63` (`Revision`), `paths/revisions.yaml:3-… | Le taux d'inflation et la probabilité de gain conservés ne sont lisibles que dans `snapshot`, nul dans les 13 exemples et sans règle de nullité ; l'historique ne peut pas les afficher | WF-REV-0070, WF-REV-0090 |
| E-04 | E | `schemas/revisions.yaml:369-398` (`StructureMerge`) | La fusion marque la révision mais n'admet pas de `description`, que tout marquage permet | WF-REV-0050, WF-REV-0020 |
| E-05 | E | `paths/revisions.yaml:588-610` (`mergeCostStructure`, 409) | Le refus d'un nom de version déjà employé n'est déclaré ni au 409 de la fusion ni comme échec de sa tâche de fond | WF-REV-0050, WF-REV-0020 |
| E-06 (aussi L-18) | E | `paths/revisions.yaml:1646-1700` (`undoLastChange`), `1702-1745` (`re… | L'historique annulable est tenu par le serveur (« historique de la session », `remaining_depth`) quand la spec le fait tenir par le front, par page ouverte | WF-IHM-0110 |
| E-07 (aussi J-05) | E | `paths/revisions.yaml:1672-1676`, `common.yaml:409` (`UNDO_CONFLICT`) | Le refus d'une annulation pour modification postérieure ne nomme ni son code ni l'objet en conflit, que la spec exige ; `UNDO_CONFLICT` n'est cité par aucune opération ; aucun exemple | WF-IHM-0110 |
| E-08 | E | `schemas/revisions.yaml:1757-1790` (`UndoResult`) | Une annulation est une écriture de grille mais ne rend ni totaux, ni tâches redatées, ni compteur de structure (`NodesWritten`) ; `undone.kind` est une chaîne libre | WF-IHM-0110, WF-IHM-0040 |
| E-09 | E | `paths/revisions.yaml:441-471` (`createCostStructure`), `schemas/revi… | `kind: risk` fait créer un devis propre que `createRisk` crée déjà avec le risque ; aucune règle pour `risk_id`, aucun refus du doublon | WF-REV-0100, WF-RIS-0030 |
| E-10 | E | `fixtures/api/structure_merge_report_without_current_revision.json:4-… | Compteurs 1 et 2 alors que la description dit « ceux des structures de la révision marquée » : `structures_amendments.json` donne 3 (principale) et 1 (avenant 2) | WF-REV-0050 |
| E-11 | E | `schemas/revisions.yaml:175-193` (`EmployedReference.hourly_rates`) | Les taux conservés sont des `HourlyRate` vivants (`audit`, `lock_version` du référentiel) quand les trois autres valeurs sont des `*Image` | WF-REV-0030, WF-DAT-0010 |
| F-01 (aussi L-10) | F | `schemas/revisions.yaml:1139-1153`, `1208-1221` (`TaskFacet`) ; `fixt… | `is_critical` et `total_float` ne sont pas exigés, et **toutes** les récapitulatives des fixtures les omettent : la spec leur donne la plus petite marge de leurs subordonnées et la criticité dès qu'une l'est | WF-PLA-0100 |
| F-02 (aussi L-07) | F | `schemas/revisions.yaml:1208-1216` (`TaskFacet.total_float`), `1442-1… | Le conflit entre une tâche manuelle et son prédécesseur doit être signalé sur les deux tâches « en nommant la liaison en cause » ; aucun attribut ne nomme la liaison ni ne marque la tâche manuelle | WF-PLA-0020, WF-PLA-0100 |
| F-03 (aussi L-08) | F | `schemas/revisions.yaml:1457-1464` (`PredecessorsReplace`) ; `paths/r… | « Une seconde liaison entre les mêmes tâches est refusée » : ni unicité de `predecessor_node_id` dans `predecessors`, ni code, ni exemple | WF-PLA-0030 |
| F-04 (aussi L-11, H-05) | F | `paths/revisions.yaml:918-919`, `954` (`deleteNode`) ; `common.yaml:4… | « Refusée sur une tâche portant un coût réel ou déjà démarrée » : citation fautive (une ligne de coût ne se rattache à aucune tâche ; la spec dit « démarrée ou terminée ») ; le 409 est la réponse générique, sans code ni condition ni exemple ; `TASK_ALREADY_STARTED`/`TASK_COMPLETED` ne sont cités par aucune opération ; le sort des lignes de provision n'est pas dit | WF-PLA-0070, §3.2.5 |
| F-05 (aussi J-04) | F | `paths/revisions.yaml:1260-1261`, `1295-1307` (`setTaskProgress`) ; `… | « Refusé sur une récapitulative » sans code ni condition déclarés ; `SUMMARY_TASK_DERIVED` (et `params.subordinate_node_ids`) n'est porté par aucune opération du contrat | WF-PLA-0040, WF-IHM-0030 |
| F-06 | F | `paths/revisions.yaml:712-732` (`listNodes`) ; `parameters.yaml:106-2… | Aucun filtre sur les colonnes de nombres (`_min`/`_max` : heures, quantité, débours, montants, délai de paiement, durée), de dates (`from`/`to` : début, fin, démarrage, terminaison), ni sur le mode, le jalon, la fin dépassée, l'objet désactivé, l'année de consommation : « toute grille se filtre sur chacune de ses colonnes » | WF-IHM-0060, WF-IHM-0130 |
| F-07 (aussi L-12) | F | `schemas/revisions.yaml:729-775` (`NodeColumn`) | Les colonnes de la grille de planning omettent `started_on` et `completed_on`, que WF-PLA-0080 nomme, et comptent `progress`, que WF-PLA-0080 dit « signalé par une marque visuelle et non par une colonne » ; l'ordre de `NodeColumn` règle le collage | WF-PLA-0080, WF-IHM-0050 |
| F-08 | F | `schemas/revisions.yaml:1592-1601` (`EstimateLineWrite.label` exigé,… | La spec fait composer le libellé d'une ligne créée par Waterfall (tâche + rôle) ; le contrat oblige le client à l'envoyer | WF-DEV-0020, WF-ARC-0020 |
| F-09 | F | `schemas/revisions.yaml:1594` (`EstimateLineWrite`), `1316`, `1632` ;… | « La catégorie d'une ligne de main-d'œuvre n'est pas saisissable : c'est celle de son rôle » ; le contrat l'exige à la création et les lignes de main-d'œuvre la nomment dans `editable_fields` | WF-DEV-0020 |
| F-10 | F | `schemas/revisions.yaml:1414-1419` (`remaining_entry`) ; `fixtures/ap… | Une ligne de provision rend `remaining_entry.is_available: true` alors que ses grandeurs sont calculées depuis le risque ; aucune condition ne dit qu'elle ne se réestime pas | WF-RAE-0010, WF-RIS-0010, WF-IHM-0030 |
| F-11 | F | `paths/revisions.yaml:1368-1422` (`setNodeTracking`) ; `schemas/revis… | Pas de 409 (seule écriture de grille sans lui) ; `TrackingEntry` sans description, `timeline_id` ni exigé pour `timeline` ni interdit pour `milestone_tracking` ; une chronologie qui n'est pas du projet n'a aucun refus déclaré (aucun `UNKNOWN_TIMELINE`) | WF-PLA-0060, WF-PLA-0140 |
| F-13 (aussi L-13) | F | `schemas/revisions.yaml:1744-1754` (`RemainingUpdate.completed_on`) ;… | Un jalon terminé garde `started_on` nul, alors que la spec dit sans exception qu'une tâche terminée sans avoir été démarrée prend pour date de démarrage celle de sa terminaison — à trancher | WF-PLA-0130 |
| F-14 (aussi L-09, F-15) | F | `schemas/revisions.yaml:1537-1547` (`TaskFacetUpdate`), `512-543` ; `… | Le mode d'une récapitulative n'est ni dans `computed_fields` ni dans `editable_fields`, et aucune description ne dit par quel motif sa saisie est refusée (seule « la durée d'un jalon » est nommée) | WF-PLA-0040, WF-IHM-0030 |
| G-01 | G | `schemas/indicators.yaml:459` (`CurveSeries`), `paths/analysis.yaml:2… | La spec 1.0.0 impose le pas du mois aux courbes d'un projet ; le contrat ne dit aucun pas et les exemples portent un point par jour d'événement (756 points) | WF-IND-0100, WF-IND-0110, WF-DAT-0040 |
| G-02 | G | `indicators.yaml:270` (`ProjectIndicators.required`), `:333` (`Projec… | Des indicateurs que la spec exige sont facultatifs dans le schéma : avancements, écarts, écarts des projections, budget agrégé, capacité des rôles, zone des mois, parts ; le client engendré les voit `?` | WF-IND-0040 à 0080, WF-PTF-0060, WF-PTF-0070, WF-DEV-0060, WF-DEV-0070 |
| G-03 | G | `portfolio.yaml:190–198` (`PortfolioPerformance.quarterly`), `paths/p… | L'évolution trimestrielle n'a ni bornes ni date de lecture définies ; la fixture rend quatre trimestres avec `scope.from/to` nuls, contre la description de `PortfolioFrom` | WF-PTF-0070, WF-PTF-0010 |
| G-04 | G | `paths/portfolio.yaml:117–119` et `:238–240` (`horizon_months`) | Paramètre sans description ni défaut ; le faux back lui donne deux sens (6 mois à partir du mois courant ; 12 mois centrés sur la date de calcul) | WF-PTF-0060, WF-PTF-0100 |
| G-05 | G | `paths/portfolio.yaml:168–180` (`getPortfolioCostStructure`), `:222–2… | Ces vues acceptent `states=completed` sans `from`/`to` : la « période qu'il fixe » des projets terminés n'est pas exprimable, le périmètre est indéfini | WF-PTF-0010 |
| G-06 (aussi H-10) | G | `portfolio.yaml:222–225` et `:249–253` (`PortfolioRisks`, `coverage`) | La couverture agrégée est dite sommée « sur les projets en cours » ; la spec la somme sur les projets en cours **et terminés** du périmètre | WF-PTF-0090 |
| H-02 | H | `schemas/risks.yaml:10-140` (`Risk`) | Le risque n'a aucun attribut pour le **coût à la survenance** que la spec lui fait conserver, donnée révisionnée du §4.4.1 | WF-RIS-0010, WF-RIS-0020, §4.4.1 |
| H-03 | H | `schemas/risks.yaml:46-51` (`Risk.provision_amount`), `parameters.yam… | Le sens de `provision_amount` pour un risque survenu ou écarté n'est pas dit : le paramètre dit « celle de la révision de référence », le générateur rend gravité × probabilité ; les totaux somment la provision de référence ; les fixtures coïncident par hasard | WF-RIS-0040, WF-RIS-0050 |
| H-04 | H | `schemas/risks.yaml:264-275` (`RiskUpdate`), `paths/risks.yaml:169-23… | `updateRisk` reçoit `probability` (exigée) sans dire si sa modification produit un réexamen daté ; pour la spec, modifier la probabilité **est** un réexamen, et l'historique doit en montrer l'évolution | WF-RIS-0010, WF-RIS-0040 |
| I-01 | I | `schemas/costs.yaml:119-133` (`CostImport`), `paths/costs.yaml:136-13… | Le journal compte `created/updated/ignored` ; la spec veut créées, mises à jour, **inchangées et rejetées** | WF-CRE-0050, WF-INTF-0140 |
| I-02 | I | `common.yaml:420-620` (`ErrorCode`), `schemas/exchanges.yaml:386-389`… | Aucun code pour une ligne de coût rejetée pour son élément d'OTP (mal formé, autre projet) ; le journal en compte 12 345 | WF-CRE-0020 |
| I-03 (aussi K-05) | I | `schemas/exchanges.yaml:439-441` (`ImportDifference.target`) | L'écart de date de début de planning de la structure, que l'import MS Project présente, n'a pas de cible | WF-INTF-0040, WF-PLA-0020 |
| I-04 | I | `schemas/exchanges.yaml:352-357` (`ImportSignal.code`) | `code` est `const: NON_WORKING_DAY` ; la spec demande déjà un second signalement : la récapitulative en mode manuel | WF-INTF-0040 |
| I-05 (aussi K-06) | I | `schemas/exchanges.yaml:213-223, 263-272, 429-438` (`ImportReport.ign… | Les lignes de provision ignorées ou conservées par un import Excel ne se signalent nulle part ; `ignored` est dit vide pour Excel | WF-INTF-0100, WF-INTF-0120 |
| I-06 | I | `paths/costs.yaml:115-129` (`setActualCostTrackedScope`) | Aucun 409 alors que `exclude_cost_lines` nomme `project_not_terminal` et `project_in_progress` | WF-CYC-0100, WF-CRE-0030 |
| I-07 (aussi K-07, L-19) | I | `paths/exchanges.yaml:455-456` (`requestExport`), `schemas/exchanges.… | « n'est pas stocké (WF-DAT-0120) » : l'exigence citée dit l'inverse (stocké 24 h ou jusqu'au premier téléchargement complet) | WF-DAT-0120 |
| I-08 | I | `schemas/exchanges.yaml:140-160` (`Import`) | La lecture d'un import ne rend ni la structure visée, ni la révision, ni la période données à l'ouverture | WF-INTF-0090, WF-CRE-0050 |
| I-09 | I | `schemas/exchanges.yaml:302-308` (`ImportCompletedTask.completed_on`)… | Date de terminaison = jour d'application (WF-PLA-0130) contre « date de la revue que porte le fichier » (WF-INTF-0120/0130) ; l'export ne dit pas cette date | WF-INTF-0120, WF-INTF-0130, WF-PLA-0130 |
| I-10 | I | `paths/exchanges.yaml:235-237, 304-325` (`openImport`) | Le format est contrôlé « par l'analyse, confiée au worker » et pourtant refusé par un 422 synchrone de l'ouverture | WF-ARC-0100, WF-INTF-0070 |
| I-11 | I | `common.yaml:420-620` (`ErrorCode`), `fixtures/api/import_analysed.js… | Aucun code pour le libellé de tâche ambigu de l'annexe B ; `UNKNOWN_TASK`/`UNKNOWN_RESOURCE_ROLE` rejettent sans nommer ce que la ligne citait | annexe B, WF-INTF-0100 |
| J-02 | J | `common.yaml:397` (`REVISION_MARKED`), `responses.yaml:33-35`, `paths… | `REVISION_MARKED` (403) n'est rendu par aucune opération ; les écritures d'une révision marquée sont 409 `revision_draft`, sauf le squelette qui dit 403 et `createNode` qui ne dit rien | WF-DAT-0020, WF-ARC-0110 |
| J-03 (aussi D-13) | J | `common.yaml:395,409,420-421,433,447,453` | Sept codes du catalogue qu'aucune opération ne nomme et qu'aucun exemple ne porte (`NOT_PROJECT_MANAGER`, `UNDO_CONFLICT`, `TASK_ALREADY_STARTED`, `TASK_COMPLETED`, `SUMMARY_TASK_DERIVED`, `RESOURCE_ROLE_REQUIRED`, `PROJECT_CODE_REQUIRED`) : doublons de `STATE_FORBIDS_OPERATION` ou orphelins | WF-ARC-0110, WF-ARC-0060 |
| J-06 | J | `paths/revisions.yaml:1169-1170` (`updateEstimateLine`), `paths/revis… | « Taux horaire manquant… ou rôle absent » sans code nommé ; `HOURLY_RATE_MISSING` n'apparaît que dans l'échec d'une tâche `revision_mark` qu'aucune description n'annonce ; `RESOURCE_ROLE_REQUIRED` nulle part | WF-DEV-0010, WF-DEV-0020, WF-IHM-0080 |
| J-07 | J | `common.yaml:616-619`, toutes les opérations | `INTERNAL_ERROR` (5xx) est au catalogue et `correlation_id` décrit pour « une erreur inattendue », mais aucune opération ne déclare de `500` ni de `default` | WF-ARC-0060, WF-OBS-0020 |
| J-10 | J | `parameters.yaml:89-101` (`NodeFields`), `paths/revisions.yaml:766` (… | Une propriété inconnue de `fields` « est refusée (400) », seul paramètre de requête refusé par 400 `MALFORMED_REQUEST` au lieu de 422 `/query/fields` | WF-ARC-0110, WF-IHM-0130 |
| J-11 | J | `schemas/projects.yaml:296,297,300,301,312` (`CommandCondition`) | Trois conditions sans description, sans opération ni exemple (`project_code_set`, `at_least_one_estimate_line`, `hourly_rates_set`) ; deux employées par les exemples mais jamais décrites (`project_in_pricing`, `no_current_revision`) | WF-IHM-0090, WF-CYC-0050 |
| K-04 | K | `schemas/audit.yaml:3-36` (`AuditAction.amendment_merge`) | La spec dit « la fusion d'un différentiel (WF-REV-0050) », la permission et la tâche de fond s'appellent `structure_merge` ; l'action d'audit garde « la contractualisation d'un avenant », `amendment_merge` | WF-SEC-0030 |
| L-05 | L | `schemas/revisions.yaml:13-63` (`Revision`) | La révision en cours doit dire la révision marquée dont elle est issue (nom de version) ; aucun champ ne la porte | WF-IHM-0020 |
| L-14 | L | `paths/revisions.yaml:533-535` (`mergeCostStructure`), `schemas/revis… | La fusion « ne touche que les montants budgétés … réestimés conservés » : règle ancienne ; la spec donne les grandeurs de référence, et aussi les grandeurs courantes d'une ligne désignée d'une tâche non démarrée jamais réestimée | WF-REV-0050 |
| L-16 | L | `paths/analysis.yaml:84-92, 118-126` (`getProjectWorkload`), `paramet… | Sans révision de référence, seule la révision en cours est admise ; la spec n'écarte que la base de la référence et garde une révision marquée ; la répartition du reste après la date de calcul n'est pas décrite | WF-DEV-0070 |
| M-01 | M | `schemas/risks.yaml:473-507` (`ProvisionTotals.reserve`, `RiskCoverag… | La réserve pour risques est partout « la réserve de la révision de référence », somme de ses lignes de provision ; la spec en fait désormais un cumul à travers les références (les survenus et écartés d'avant la nouvelle référence y restent), et l'avenant qui intègre les lignes d'un survenu ne touche pas la couverture | WF-RIS-0050 |
| M-02 | M | `parameters.yaml:341-358` (`IndicatorsRevision`), `paths/analysis.yam… | Les courbes d'une révision marquée sont dites « recalculées … sur les lignes de coût réel connues aujourd'hui », `is_stored` faux ; la spec dit l'inverse : coût réel = lignes connues au marquage telles qu'elles étaient, courbes conservées avec les indicateurs ; décisions #247 et #365 antérieures et contredites | WF-IND-0010 (WF-DAT-0040) |
| M-03 | M | `parameters.yaml:341-366` (`IndicatorsRevision`, `AsOf`), `paths/anal… | Sur un projet sans révision en cours, les indicateurs au jour courant « se calculent sur sa dernière révision marquée, avec le coût réel au jour courant », le dernier point de l'évolution et la contribution au portefeuille aussi ; le contrat ne dit que « la révision en cours » (`RiskRevision` l. 275-283 porte la règle pour les risques, pas les indicateurs) | WF-IND-0010, WF-IND-0130, WF-PTF-0010 |
| M-04 | M | `paths/revisions.yaml:127-148` (`abandonRevision`), `paths/risks.yaml… | L'abandon de la révision en cours ramène les risques à l'évaluation de la dernière révision marquée (créé → disparaît, survenu → identifié avec sa provision) et « seul l'abandon défait » la survenance ; le contrat dit « Définitif » sans exception et l'abandon ne parle que des lignes | WF-RIS-0020, WF-RIS-0060 |
| M-05 | M | `paths/risks.yaml:388-399` (`declareRiskOccurrence`), `schemas/risks.… | La place et l'état des tâches fusionnées (sous la tâche porteuse en dernière position, liaisons/durées/modes conservés, mode manuel sans prédécesseur, cas du jalon porteur, grandeurs conservées et réestimé recalculé) ne sont pas décrits ; la fixture rend les tâches fusionnées en mode `automatic` | WF-RIS-0060 |
| M-06 | M | `schemas/indicators.yaml:522-531` (`CurveSeries.cash_out_by_month`),… | « Le passé par mois de date de pièce décalée » : la spec dit « le coût réel n'est pas décalé » (la fixture ne le décale pas) ; l'étalement du reste à engager est encore « sur les dates de la révision courante », sans la part postérieure à la date de calcul ni le report entier d'une tâche dont la fin est dépassée | WF-IND-0100 |
| M-07 | M | `paths/portfolio.yaml:224-233` (`getPortfolioCostCurve`), `schemas/po… | La contribution d'un projet en chiffrage — devis pondéré **hors provisions** pour le budget, **provisions comprises** pour le reste à engager et la projection, risques **non pondérés** — n'est portée nulle part ; le « choix déclaré » d'EP-02/L26 (budget = projection = devis pondéré) dit l'inverse de la spec | WF-PTF-0020, WF-PTF-0080, WF-PTF-0090, WF-PTF-0100 |
| M-08 | M | `schemas/revisions.yaml:1365-1367` (`EstimateLineFacet.reestimated_am… | Le reste à engager d'une tâche non démarrée non réestimée se calcule « depuis les grandeurs de la référence, aux taux conservés par la révision courante », sur l'année de consommation courante (150 h après l'avenant) ; le contrat ne dit rien du réestimé d'une ligne non réestimée, et les décisions disent « le budgété projeté » | WF-RAE-0010, WF-RAE-0040 |
| M-09 | M | `schemas/indicators.yaml:223-230` (`RemainingIndicators.delta_to_prev… | « Nul sans revue précédente » : la spec ne compte que la révision marquée précédente **marquée à l'état En cours** ; une offre marquée en chiffrage ne fait pas une revue précédente | WF-RAE-0020 |
| M-10 | M | `fixtures/api/milestone_tracking.json:7`, `schemas/indicators.yaml:43… | La fixture donne un point à la révision marquée le 15 décembre 2025, en chiffrage, quand « les révisions marquées avant l'état En cours ne donnent aucun point » ; la description ne dit ni le dernier point au jour courant (révision en cours ou dernière marquée) ni l'arrêt à la terminaison | WF-IND-0090 |
| M-11 | M | `schemas/revisions.yaml:1222-1229` (`TaskFacet.physical_progress`), `… | L'avancement physique d'une récapitulative garde l'ancienne formule (« montants budgétés portés par les tâches terminées … au total budgété du sous-arbre »), qui compte les lignes de provision que la spec exclut désormais au numérateur et au dénominateur, lignes propres comprises ; la valeur acquise et le budget d'un sous-projet ne disent pas « hors lignes de provision » | WF-IND-0060, WF-IND-0030, WF-IND-0020 |

### Mineurs (87)

| # | Famille | Emplacement | Constat | Exigence |
|---|---|---|---|---|
| A-05 | A | `paths/system.yaml:251` (`getBackgroundTaskResult`, `'409'`) | Un 409 déclaré sans que la description dise quand ni avec quel code (tâche non aboutie ? tâche sans résultat ?) | WF-ARC-0090, WF-DAT-0120 |
| A-06 (aussi K-13) | A | `schemas/access.yaml:296` (`DisplayPreferences.highlight_tasks_added_… | Seule propriété des préférences sans description ; la spec fait de « la » préférence le marqueur des tâches ajoutées après la référence **et** des lignes à budget nul — le nom ne dit que la première moitié | WF-ADM-0040, WF-RAE-0040 |
| A-07 | A | `common.yaml:115-128` (`ActorRef`) | `user_id` facultatif quelle que soit la nature : pour `kind: user` le client généré doit tester un identifiant qui ne manque jamais ; `AuditActorFacet` l'exige, lui | WF-DAT-0070, WF-ADM-0060 |
| A-08 | A | `schemas/access.yaml:121-133, 165, 184` (`UserAccount.required`) | `org_node_label` est exigé mais pas `org_node_id` ; `has_avatar` n'est pas exigé — toutes les fixtures les portent | WF-ADM-0050, WF-ADM-0030, WF-ADM-0080 |
| A-09 | A | `common.yaml:812, 839-860` (`BackgroundTaskRef`) | `submitted_at`, `progress`, `finished_at`, `problem`, `result_url` facultatifs alors que toutes les fixtures les portent et que la liste se trie sur `submitted_at` ; `result_url` sans `format` | WF-ARC-0090, WF-IHM-0080 |
| A-10 | A | `paths/access.yaml:833-839` (`deleteAccessRole` 409), `:768-772` (`ge… | Refus déclaré sans exemple (`ACCESS_ROLE_IN_USE`), et trois réponses sans exemple | WF-ADM-0090, WF-EXP-0040 |
| A-11 | A | `schemas/access.yaml:538-541` (`AccessRoleUpdate`) ; `common.yaml:505… | « rôle d'accès » pour un rôle d'habilitation ; `TASK_INTERRUPTED_BY_RESTORE` rangé sous le commentaire « 422 » alors que son exemple est un 409 | — |
| B-07 | B | `fixtures/api/task_restore_queued.json`, `backup_pending.json`, `rest… | La chronologie des exemples se contredit : une restauration acceptée à 14 h 04 min 30 s pendant que la sauvegarde de 14 h 04 s'exécute (prise à 14 h 04 min 50 s), alors que la restauration de 14 h 04 min 20 s est refusée pour cette raison | WF-ADM-0150, WF-ADM-0160 |
| B-08 | B | `schemas/platform.yaml:5` (`SystemStatus.required`) | `last_backup`, `last_identity_sync`, `last_restore_test` ne sont pas exigés quand `last_backup_copy` l'est, tous quatre nullables et tous quatre demandés par l'écran d'état | WF-ADM-0130 |
| B-09 | B | `schemas/platform.yaml:399-431`, `paths/platform.yaml:509-519` (`Rest… | `confirmed` faux ou absent : 422 par le schéma (`const: true`) ou 400 `CONFIRMATION_REQUIRED` ? Les deux désignations à la fois, ou aucune (`oneOf`) : refus non décrit | WF-ADM-0160 |
| B-10 | B | `schemas/audit.yaml:83-84,164` (`AuditObject.label`, `AuditEvent.proj… | « nul pour une sauvegarde … sa date est celle de l'inscription » est faux pour `restore` ; le dépôt manque à la liste des objets sans projet | WF-SEC-0030 |
| B-11 | B | `paths/platform.yaml:173-175,302-305` (`getBackup`, `getBackupSchedul… | Seules opérations de la famille qui ne nomment pas leur permission (`backups.read`) | WF-ADM-0100 |
| C-04 (aussi H-06) | C | `schemas/reference.yaml:816-823` (`RiskMatrixSettings`) | « Les bornes de gravité sont exprimées en pourcentage du budget de référence » : la spécification révisée dit l'assiette — budget de référence ou, avant lui, total hors provisions du devis courant | WF-REF-0160 |
| C-05 | C | `paths/reference.yaml:1708` (`listHourlyRates`) | « Le taux de l'année en cours est exigé au chiffrage (WF-REF-0060) » : c'est le taux de l'année de référence, et l'exigence qui le dit est WF-DEV-0010 ; WF-REF-0060 porte l'ajout d'une colonne | WF-REF-0060, WF-DEV-0010 |
| C-06 | C | `schemas/reference.yaml:742` (`ReferenceSettings`), `:882` (`Duration… | Deux objets uniques modifiables de la même famille sans `audit`, le troisième avec : « Modifié le / par » ne se lit pas pour les paramètres communs ni les unités de durée | WF-DAT-0070, §4.4.1 |
| C-07 | C | `paths/reference.yaml:206`, `:1061`, `:1271-1304`, `:1350`, `:1602`,… | Six refus déclarés sans exemple, dont un 409 de modification qui ne cite pas l'exemple de code pris que la règle des exemples exige | WF-REF-0030, WF-REF-0070, WF-REF-0120, WF-REF-0190 |
| C-08 | C | `schemas/reference.yaml:384-386` (`CostTypeKind`) vs `common.yaml` (`… | Deux graphies du même mot dans les identifiants figés : `labor`/`non_labor` et `LABOUR_…` ; le seul moment pour unifier est avant le gel | WF-REF-0030 |
| C-09 | C | `schemas/reference.yaml:243-268` (`ResourceRoleUpdate`), `paths/refer… | Le Vérif veut la modification du nœud d'un rôle « refusée » ; le contrat ne porte pas le champ et ne dit pas ce qu'il advient d'un `org_node_id` envoyé (ignoré ou refusé, et par quel code) | WF-REF-0090 |
| D-04 | D | `paths/projects.yaml:181-183` (`updateProject`) | La description dit la probabilité de gain « refusée par champ (422) » dès En cours, quand le 409 de la même opération, `Project.win_probability`, la fixture et L42i disent 409 `STATE_FORBIDS_OPERATION` | WF-PRJ-0090 |
| D-08 | D | `paths/projects.yaml:492` (`listSubprojects`) | « Les sous-projets, qui regroupent des tâches sans dupliquer l'arbre » : ils regroupent des lignes de devis, « jamais » des tâches | WF-PRJ-0050, §3.2.3 |
| D-09 | D | `paths/projects.yaml:392` (`setWorkBreakdown`) | « Croise le découpage fonctionnel et le découpage produit du projet » : le lotissement reproduit le bon de commande, rien d'autre | WF-PRJ-0020 |
| D-11 | D | `schemas/projects.yaml:592-594` (`WorkBreakdown.work_packages`), `pat… | Rien ne dit ce que fait une saisie sans aucun lot (`minItems` absent) ni si le lotissement par défaut, persistant (ids 714/715), suit le libellé du projet | WF-PRJ-0020 |
| D-12 (aussi J-13) | D | `paths/projects.yaml:917` (`createTimeline` corps) | `label` sans `pattern: '\S'`, quand `Timeline.label` (`revisions.yaml:1482`) le porte ; schéma anonyme | WF-PLA-0140, convention `\S` |
| E-12 | E | `paths/revisions.yaml:150-193` (`markRevision`, 409), `schemas/revisi… | « Révision déjà marquée » sans code ni condition ; `no_background_task_running` absent ; aucun exemple des deux 409 ; conditions de `mark`, `abandon`, `designate_reference` non décrites dans `RevisionCommand` | WF-REV-0020, WF-IHM-0090 |
| E-13 | E | `paths/revisions.yaml:127-148` (`abandonRevision`), `49-97` (`createR… | 409 générique sans code ni condition ni exemple ; l'abandon ne porte pas de `lock_version` ni de 412, contrairement à `deleteNode` | WF-REV-0010, WF-IHM-0110 |
| E-14 | E | `paths/revisions.yaml:441-471` (`createCostStructure`) | 409 générique sans condition ni exemple ; la description ne dit pas qu'un différentiel naît copie de la structure principale, ce que `amendment_created` affirme | WF-REV-0100 |
| E-15 | E | `fixtures/api/revision_offer.json` (bloc `available_commands`, `lock_… | L'offre v1.0 n'y liste aucun export, quand l'item 100 de `revisions.json` à la même version les liste tous (#421) | WF-INTF-0050, WF-CYC-0110 |
| E-16 | E | `fixtures/api/revisions.json:330`, `revision_offer.json:91`, `structu… | Compteur initial incohérent : révision créée à 1, structure principale neuve à 0, différentiel neuf à 1 ; l'offre marquée reste à 1 quand le marquage « porte une version de plus » (#1352) | WF-IHM-0110 |
| E-17 | E | `fixtures/api/merge_revision_marked_refused.json:2,7` | Le résumé nomme `revision_marked`, la valeur `revision_draft` | WF-REV-0050 |
| E-18 | E | `schemas/revisions.yaml:236-268` (`RateUpdateProposal`), `fixtures/ap… | `target_year` facultatif et absent de l'exemple ; rien ne dit ce que la proposition rend des catégories déjà acceptées depuis la création (C-362) | WF-REV-0060 |
| E-19 | E | `paths/revisions.yaml:256` (`getRateUpdateProposal`) | « lorsque le référentiel a changé » : la spec présente l'écart quand l'année de référence diffère, que le référentiel ait changé ou non | WF-REV-0060 |
| E-20 | E | `schemas/revisions.yaml:218,388` (`RevisionMark.version_name`, `Struc… | Pas de `pattern: '\S'` sur le nom de version, contrairement à la convention et à `StructureCreate.label` | WF-ARC-0110, WF-DAT-0090 |
| E-21 | E | `paths/revisions.yaml:287-298` (`applyRateUpdate`) | Corps de requête anonyme, seul de la famille sans schéma nommé | — |
| E-22 | E | `schemas/revisions.yaml:288-290` (`CostStructure.is_merged`), `fixtur… | Décrit pour le seul différentiel, mais vrai sur un devis propre fusionné par survenance | WF-RIS-0060 |
| E-23 | E | `paths/revisions.yaml:331-410` (`compareRevisions`) | Rien ne dit ce que reçoit une révision en cours donnée en `from`/`to` (refus ou lecture) | WF-REV-0080 |
| E-24 | E | `paths/revisions.yaml:195-250` (`designateReferenceRevision`), `schem… | Écriture du projet sans `lock_version` ni 412, le projet en portant un (`reference_designated.json`, version 5) | WF-IHM-0110 |
| E-25 | E | `common.yaml:642-700` (`ProblemParams`) | `cycle`, `link`, `task`, `work_package_task`, `order_item_tasks`, partagés par la fusion, son compte rendu, les saisies et l'import, restent non typés malgré la règle de `ProblemParams` | WF-ARC-0110 |
| F-12 | F | `schemas/revisions.yaml:985-1010` (`NodesWritten.rescheduled`/`reinfl… | `reinflated` exclut ce que `ancestors` rend entier, `rescheduled` ne le dit pas, et l'exemple rend « Montage des armoires sur site » dans les deux | WF-PLA-0020 |
| F-16 | F | `schemas/revisions.yaml:1119-1135` (`LagUnit`, `Lag`) | L'échelle d'un décalage en `percent` n'est pas dite (`50` ou `0.5`), aucun exemple n'en porte, et la convention des rapports du README dit l'inverse de WF-PLA-0160 | WF-PLA-0030, WF-PLA-0160 |
| F-17 | F | `paths/revisions.yaml` : `createNode` 835-855, `updateEstimateLine` 1… | Refus déclarés sans exemple : `TASK_WITHOUT_WORKING_HOURS` (3 opérations), `FIELD_NOT_ACCEPTED` (3), `HOURLY_RATE_MISSING`, `RESOURCE_ROLE_REQUIRED`, `PROVISION_CATEGORY_RESERVED` et `COMPUTED_VALUE` sur `updateEstimateLine`, le 409 `task_not_completed` de `setLineRemaining`, le 409 d'`applyPaste` ; aucune fixture du dépôt ne porte `FIELD_NOT_ACCEPTED` ni `RESOURCE_ROLE_REQUIRED` | WF-PLA-0010, WF-DEV-0020, WF-RAE-0040 |
| F-18 | F | `parameters.yaml:106-113` (`NodeKinds`) ; `schemas/revisions.yaml:119… | `kinds` décrit comme « restreint », quand `listNodes` dit qu'il n'est pas un filtre ; `calendar_id` nul pour une intersection sans que la description le dise (l'exemple `estimate_line_redated` le rend nul) | WF-PLA-0010 |
| F-19 | F | `paths/revisions.yaml:973-1022` (`getComputedValueDependencies`), `85… | Pas de 400 déclaré alors que `listNodes`, lecture à paramètres de requête comme elles, le déclare (une valeur de `field` hors énumération) | — |
| G-07 | G | `indicators.yaml:216–222` (`RemainingIndicators.delta_to_reference`),… | Sens opposé au Vérif de WF-RAE-0020 (« + 50 » ; le contrat donne −50) ; décision de l'auteur #466 assumée, mais la spec 1.0.0 dit toujours l'inverse : à aligner côté spec avant le gel | WF-RAE-0020 |
| G-08 | G | `indicators.yaml:322–330` (`IndexValue`), `fixtures/api/volume/portfo… | La précision des indices n'est pas fixée ; la fixture du portefeuille les arrondit à deux décimales (0,94 pour 0,9410 exact, 0,91 pour 0,9088) | WF-PTF-0020, README « Une part… » |
| G-09 | G | `indicators.yaml:296` (`ProjectIndicators.actual_cost`) | « antérieure à la date de calcul » : la spec dit « antérieure **ou égale** » (et `getCostCurve` le dit bien) | WF-IND-0010 |
| G-10 | G | `indicators.yaml:288–290` (`planned_value`), `:361–363` (`WorkloadPla… | « étalées linéairement » / « interpolation linéaire » : la spec dit « au prorata des heures travaillées du calendrier de son rôle » ; la règle du reste à engager après la date de calcul n'est pas dite | WF-DEV-0080, WF-DEV-0070 |
| G-11 | G | `parameters.yaml:393–400` (`PortfolioStates`), `:359–366` (`AsOf`) | `states` admet `created`, `lost`, `abandoned` sans dire ce qu'en fait le portefeuille ; l'état « à cette date » du calcul passé n'est pas dit | WF-PTF-0010, WF-CYC-0130 |
| G-12 | G | `indicators.yaml:203`, `:345`, `:350`, `:355` | Renvoi à un schéma qui n'existe pas : `PortfolioProject.delta_to_reference` (le schéma est `PortfolioProjectRow`) | — |
| G-13 | G | `portfolio.yaml:154` (`roles[].months[].zone`), `paths/portfolio.yaml… | La zone d'un mois du plan agrégé n'est pas décrite (alerte au-delà de 100 %, vigilance sous le seuil) ; le 422 ne dit pas ce qu'il refuse | WF-PTF-0060 |
| G-14 | G | `paths/portfolio.yaml:140–148`, `portfolio.yaml:156–159` (`PortfolioP… | La vue ne dit pas qu'elle se calcule sur les seuls projets en cours du périmètre ; `scope.states` rend `[in_progress]` pour une requête qui ajoutait le chiffrage | WF-PTF-0070 |
| G-15 | G | `fixtures/api/volume/portfolio_cost_structure.json`, `mockportfolio.p… | Le budget de référence agrégé reçoit 10 % de nature « Provision » (« the provision the rest »), alors que le budget de référence est hors lignes de provision et que celui du témoin n'en porte aucune | WF-PTF-0080, WF-IND-0020 |
| H-07 | H | `schemas/risks.yaml:12-29` (`Risk.required`) | `description`, `mitigation_notes`, `provision_node_id`, `matrix_cell`, `last_review_on` ne sont pas `required` alors que toutes les fixtures les rendent, que `listRisks` les promet, et que la décision #786 dit `provision_node_id` « exigé » comme `provision_task` | WF-RIS-0040 |
| H-08 | H | `paths/risks.yaml:422` (`declareRiskOccurrence`, 409) | 409 générique `Conflict` : aucune condition nommée (`risk_identified`, `project_not_terminal`, `no_background_task_running`, `may_create_revision`), aucun exemple, alors que les quatre autres saisies du risque nomment les leurs | WF-RIS-0020, WF-RIS-0060 |
| H-09 | H | `paths/risks.yaml:14-19` (`states`), `:206-215`, `:349-362`, `:265-27… | `states` sans description ; les 409 des trois saisies ne mentionnent pas les conditions d'état d'`edit_risks` que `createRisk` liste (`project_not_terminal`, `no_background_task_running`) | WF-RIS-0040, WF-IHM-0090 |
| I-12 | I | `fixtures/api/import_actual_costs_analysed.json`, `_column_ignored.js… | `format_version: "1"` pour une extraction ERP qui « n'en porte pas » ; `format_version` sans description | WF-INTF-0070 |
| I-13 | I | `schemas/exchanges.yaml:164-165, 253`, `schemas/costs.yaml:5-15, 68-7… | `requires_confirmation_reasons`, `format_version`, `passthrough`, `excluded_reason`, `ImportDifference.label` non exigés alors que « toujours rendus » | WF-INTF-0080 |
| I-14 | I | `schemas/exchanges.yaml:151-157` (`Import.status`, `expires_at`) | `status` sans description (quel état après un refus à l'application, une analyse échouée ?) ; `expires_at` exigé pendant `analysing` | WF-ARC-0100 |
| I-15 | I | `schemas/exchanges.yaml:132-138` (`ImportRequest`), `paths/exchanges.… | `structure_id`, `period_from`, `period_to` sans description ; période inversée, structure ou dépôt inconnus : refus non décrits | WF-INTF-0090, WF-CRE-0050 |
| I-16 | I | `schemas/exchanges.yaml:548-554, 561-565` (`ExportRequest`) | `kind` est une énumération anonyme (pas d'`ExportKind` nommé) ; `structure_id` sans description | WF-INTF-0050/0110/0130 |
| I-17 | I | `paths/exchanges.yaml:485` (`requestExport`) | Un 409 déclaré sans cause possible ni exemple : un export « ne manque d'aucune condition » | WF-CYC-0110 |
| I-18 | I | `paths/exchanges.yaml:370-385` (`abandonImport`) | Rien ne dit ce que fait l'abandon d'un import appliqué, en cours d'application ou expiré | WF-ARC-0100 |
| I-19 (aussi J-15) | I | `paths/costs.yaml:19-27` (`listActualCosts`) | `from`, `to`, `in_tracked_scope` sans description : quelle colonne, quelle borne | WF-CRE-0040, WF-IHM-0130 |
| I-20 | I | `paths/exchanges.yaml:354-366, 441-442, 478-484` | Exemples manquants : premier import de coûts réels (`added`, `lines_outside_project`), `completed_tasks` non vide, 409 de l'application pour droits/état, 404 d'export | WF-INTF-0080, WF-CRE-0020 |
| J-12 | J | `paths/access.yaml:620-636` (`listAccessRoles`), `paths/risks.yaml:28… | Tables plates triées/filtrées sans `limit`/`offset`/`meta`, sans la justification de volume que `listSubprojects` et `listContributors` donnent | WF-IHM-0060 |
| J-14 | J | `common.yaml:625-634` (`FieldProblem.pointer`), `paths/exchanges.yaml… | Le pointeur `/body` d'un morceau déposé (décidé, DECISIONS 3847) n'est pas une forme que la description de `pointer` admet | WF-ARC-0110 |
| J-16 | J | `paths/system.yaml:83-98` (`getMetrics`) | Opération publique qui déclare un seul refus, `404` partagé « objet inexistant ou invisible », sans dire quand ; ni `503` comme les autres sondes, ni exception dans `.redocly.lint-ignore.yaml` | WF-OBS-0010, WF-ARC-0060 |
| J-17 | J | `responses.yaml:3-7,66-70`, `common.yaml:377,429,464-465,473,477-487,… | Treize codes déclarés sans aucun exemple, dont `MALFORMED_REQUEST`, `FILE_TOO_LARGE`, `NUMBER_INVALID`, `DATE_INVALID`, `FIELD_NOT_ACCEPTED`, `UNKNOWN_CALENDAR`, `ACCESS_ROLE_IN_USE`, `SESSION_REQUIRED`, `ACCOUNT_*` | WF-QUA-0020 |
| J-18 | J | `schemas/projects.yaml:292-293,317` | `is_contributor`, `is_project_manager`, `task_not_milestone` : conditions décrites sans aucun exemple de `missing_conditions` ni de `missing_condition` | WF-IHM-0090 |
| J-19 | J | `schemas/revisions.yaml:363-364` (`StructureCreate.kind`) | Seule énumération du contrat écrite `allOf` + `enum` sans `type` ; les 323 autres schémas typent leurs énumérations | — |
| J-20 | J | `parameters.yaml:3-11` (`Limit`, `Offset`), `common.yaml:87-90` (`Yea… | Trois types/paramètres partagés sans description ; `Limit.maximum: 500` ne cite pas la règle des pages (10/25/50/100) | WF-IHM-0060 |
| J-21 | J | `fixtures/api/risk_matrix_no_basis.json`, `paths/risks.yaml:474` | Fixture engendrée et nommée « exemple » par DECISIONS 7525, qu'aucun fichier du contrat ne référence | WF-RIS-0040 |
| K-08 | K | `schemas/exchanges.yaml:360-401` (`ImportRejection`) | « Une ligne nouvelle sous une tâche terminée est rejetée au compte rendu » : aucun motif nommé ; `TASK_COMPLETED` existe au catalogue pour la réestimation | WF-INTF-0100, WF-INTF-0120 |
| K-11 | K | `paths/system.yaml:83-98` (`getMetrics`) | Le point de métriques est « servi en HTTP » et « joignable du seul réseau interne au cluster » (TFX-09) ; le contrat le place sous `/api/v1` avec un 404 sans explication | WF-SEC-0010 |
| K-12 | K | `schemas/platform.yaml:228-267` (`BackupSchedule`), `paths/platform.y… | « La planification livrée est quotidienne (WF-EXP-0050) » : rien ne dit la planification livrée ni ce que `is_enabled` vaut sur une installation neuve | WF-ADM-0170 |
| K-14 | K | `paths/exchanges.yaml:10-11` (`uploadFile`), `schemas/exchanges.yaml:… | Le fichier est supprimé aussi quand l'import est « refusé à l'application » ; `applyImport` le dit, le dépôt et son schéma ne le disent pas | WF-ARC-0100 |
| L-20 | L | `paths/revisions.yaml:130-135` (`abandonRevision`) | L'abandon de l'unique révision laisse le projet sans révision, à Chiffrage ; il supprime les risques que plus aucune révision n'évalue ; non dit | WF-REV-0010, WF-DAT-0080, WF-DAT-0130 |
| L-21 | L | `paths/revisions.yaml:255-258` (`getRateUpdateProposal`), `schemas/re… | La présentation des taux n'a lieu à la création que si l'utilisateur la demande ; une révision créée par un import, une saisie de risque ou une survenance applique les taux projetés ; seule la fusion le dit | WF-REV-0060 |
| L-22 | L | `paths/revisions.yaml:199-201` (`designateReferenceRevision`), `schem… | « ni révision marquée postérieure » (ancienne règle) alors que le 409 dit « depuis la dernière désignation » | WF-REV-0040 |
| L-23 | L | `paths/revisions.yaml:1751-1754` (`generatePlanningSkeleton`) | La feuille par livrable est automatique et d'un jour ; non dit, et aucun exemple ne porte de livrable | WF-PRJ-0030 |
| L-24 | L | `schemas/indicators.yaml:161-166` (`EstimateIndicators.delta_to_refer… | L'écart est celui du devis de la révision affichée, lignes de provision comprises de part et d'autre ; le contrat dit « devis en cours » sans parler des provisions | WF-DEV-0060 |
| L-25 | L | `schemas/projects.yaml:61-72` (`Project.available_commands`), `:93-99… | Une commande que la qualité sur le projet ne permet pas est présentée indisponible en nommant cette qualité ; `is_contributor` n'est décrite nulle part et la liste dit n'omettre que les commandes sans permission | WF-IHM-0090 |
| L-26 | L | `schemas/revisions.yaml:474-477` (`Node`) | La lignée fonde aussi le rapprochement des imports ; la description de `lineage_id` ne le cite pas | WF-DAT-0030 |
| M-12 | M | `schemas/reference.yaml:590-597` (`CostCategoryImage.accounting_code`) | « N'intervient dans aucun calcul ni dans aucun import » : la spec dit « ni dans l'import des coûts réels … ; les fichiers de devis et de reste à engager désignent la catégorie d'une ligne hors main-d'œuvre par ce code (annexe B) » | WF-REF-0040 |
| M-13 | M | `schemas/reference.yaml:852-860` (`IndexThresholds`), `:1040-1045` (`… | Les bornes des zones sont désormais fermées/ouvertes (« supérieur ou égal au seuil de vigilance → nominal ; … ≥ alerte → vigilance ») ; le contrat ne le dit pas, alors qu'il le dit pour les niveaux de la matrice (`RiskMatrixLevel`) | WF-REF-0170 |
| M-14 | M | `schemas/indicators.yaml:322-330` (`IndexValue.zone`), `:581-594` (`I… | « Une révision marquée est toujours lue avec [les seuils et bornes] courants … seule la zone qui [qualifie ses indicateurs] peut changer » : rien ne dit que `zone` d'un indice conservé est recalculée à la lecture et non conservée | WF-REF-0130 |
| M-15 | M | `schemas/portfolio.yaml:87-89` (`PortfolioValue.conversion_rate`), `s… | Le taux de transformation compte les offres « sorties de Chiffrage vers En cours ou vers Perdu » ; une offre abandonnée ne compte pas — le motif « aucune offre n'est sortie de l'état Chiffrage » et le champ ne le disent pas | WF-PTF-0050 |
| M-16 | M | `schemas/portfolio.yaml:156-199` (`PortfolioPerformance.projections`)… | La projection au rythme constaté agrégée vaut « le budget de référence agrégé divisé par l'indice de coût agrégé », non calculable avec lui, les deux autres étant des sommes ; le générateur le fait (`mockportfolio.py:422-438`), le contrat ne le dit pas | WF-PTF-0070 |

## Annexes — le détail par relecture

Chaque annexe reprend la relecture telle qu'elle a été rendue (ce qui a été lu, le tableau de la famille, chaque constat avec sa citation, sa proposition et la décision de `DECISIONS.md`, ce qui a été vérifié conforme, les doutes), à la seule correction de la datation des phrases de la spécification (voir « Pourquoi cette revue »). Les relectures K, L et M terminent par le relevé des exigences changées de leur groupe, avec le verdict de chacune.

## Annexe A — Système, compte courant, comptes et habilitations


Lu : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/system.yaml` (252 l.), `paths/me.yaml`
(166 l.), `paths/access.yaml` (840 l.), `components/schemas/access.yaml` (548 l.), `components/common.yaml`
(860 l., dont `ActorRef`, `Audit`, `Problem`, `ErrorCode`, `BackgroundTaskStatus`, `BackgroundTaskRef`) ;
`schemas/platform.yaml` pour `SystemStatus`, `ComponentHealth`, `Alert`, `BackupSchedule`, `IdentitySyncReport` ;
`schemas/reference.yaml#/Installation` ; `schemas/audit.yaml` (`AuditAction`, `AuditActorKind`, `AuditActorFacet`) ;
`schemas/projects.yaml#/CommandCondition` ; `parameters.yaml` et `responses.yaml` (les références de la famille).
Spécification : §3.1.3–3.1.5 (l. 377–597), §3.4.2 à §3.4.2.3 (l. 1182–1384), §3.6 (l. 3174–3352), §4.1.3
(3392–3420), §4.4.1 (table, l. 3857–3881), §4.5.2 (4149–4167), §4.5.4 (4185–4215), §4.6.1 (4217–4259),
§4.6.2 (volumes), §4.6.3 (4329–4369), WF-ARC-0090 (l. 3825). `DECISIONS.md` (grep par constat),
`INVENTORY.md`, section « Constats reçus » du fichier EP-16. Fixtures ouvertes : 97 (toutes celles que
les trois paths référencent, plus `import_analysing`, `task_backup_queued`, et un balayage programmé de
toutes les fixtures qui portent une tâche de fond et de tous les `permissions`).

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| A-01 | majeur | `fixtures/api/access_roles.json:212-236` (rôle prédéfini « Manager »), repris par `me_manager.json:49`, `me_directory.json:49` | Le rôle prédéfini « manager » du témoin n'a ni `risk_settings.write` ni `indicator_settings.write`, alors que la spec lui donne le paramétrage de FBS-3.1 à FBS-3.4 entier | WF-INTF-0020, WF-ADM-0010 |
| A-02 | majeur | `docs/api/paths/access.yaml:535-594` (`startIdentitySync`, `getLatestIdentitySync`) ; aucune opération de planification | La périodicité de la lecture des comptes, « choisie par un utilisateur habilité, quotidienne par défaut, comme celle des sauvegardes », n'a aucune surface : pas d'équivalent de `getBackupSchedule`/`setBackupSchedule` | WF-ADM-0070 |
| A-03 | majeur | `docs/api/components/schemas/platform.yaml:3-36` (`SystemStatus`), servi par `paths/system.yaml:100-123` (`getSystemStatus`) | L'écran d'état ne porte ni « les valeurs en vigueur des paramètres d'exploitation (§4.5.1) » ni « la durée de validité du cache en vigueur », que l'exigence et sa Vérif demandent | WF-ADM-0130 |
| A-04 | majeur | `docs/api/paths/access.yaml:468-512` (`createPasswordSetupLink`) | Le « renvoi » du courriel de fixation du mot de passe par un utilisateur habilité n'a aucune opération : le contrat ne porte que l'obtention du lien | WF-ADM-0140 |
| A-05 | mineur | `docs/api/paths/system.yaml:251` (`getBackgroundTaskResult`, `'409'`) | Un 409 déclaré sans que la description dise quand ni avec quel code (tâche non aboutie ? tâche sans résultat ?) | WF-ARC-0090, WF-DAT-0120 |
| A-06 | mineur | `docs/api/components/schemas/access.yaml:296` (`DisplayPreferences.highlight_tasks_added_after_reference`) | Seule propriété des préférences sans description ; la spec fait de « la » préférence le marqueur des tâches ajoutées après la référence **et** des lignes à budget nul — le nom ne dit que la première moitié | WF-ADM-0040, WF-RAE-0040 |
| A-07 | mineur | `docs/api/components/common.yaml:115-128` (`ActorRef`) | `user_id` facultatif quelle que soit la nature : pour `kind: user` le client généré doit tester un identifiant qui ne manque jamais ; `AuditActorFacet` l'exige, lui | WF-DAT-0070, WF-ADM-0060 |
| A-08 | mineur | `docs/api/components/schemas/access.yaml:121-133, 165, 184` (`UserAccount.required`) | `org_node_label` est exigé mais pas `org_node_id` ; `has_avatar` n'est pas exigé — toutes les fixtures les portent | WF-ADM-0050, WF-ADM-0030, WF-ADM-0080 |
| A-09 | mineur | `docs/api/components/common.yaml:812, 839-860` (`BackgroundTaskRef`) | `submitted_at`, `progress`, `finished_at`, `problem`, `result_url` facultatifs alors que toutes les fixtures les portent et que la liste se trie sur `submitted_at` ; `result_url` sans `format` | WF-ARC-0090, WF-IHM-0080 |
| A-10 | mineur | `docs/api/paths/access.yaml:833-839` (`deleteAccessRole` 409), `:768-772` (`getAccessRole` 200), `paths/system.yaml:69-80` (`getReadiness` 200), `:171` (`listBackgroundTasks` 422) | Refus déclaré sans exemple (`ACCESS_ROLE_IN_USE`), et trois réponses sans exemple | WF-ADM-0090, WF-EXP-0040 |
| A-11 | mineur | `docs/api/components/schemas/access.yaml:538-541` (`AccessRoleUpdate`) ; `common.yaml:505-513` (commentaire d'`ErrorCode`) | « rôle d'accès » pour un rôle d'habilitation ; `TASK_INTERRUPTED_BY_RESTORE` rangé sous le commentaire « 422 » alors que son exemple est un 409 | — |

#### A-01 — Le rôle prédéfini « Manager » du témoin ne paramètre ni les risques ni les indicateurs
- **gravité** : majeur ; **emplacement** : `fixtures/api/access_roles.json:212-236` (objet `Manager`,
  `is_predefined: true`), même liste dans `me_manager.json:33-57` et `me_directory.json:33-57`
  (`permissions` du compte de Dominique Bernard) ; **exigence** : WF-INTF-0020 (l. 401) : « paramétrer le
  référentiel commun — l'organisation de l'entreprise, les rôles de ressources, les calendriers, les
  natures et catégories de coût, les taux horaires, la correspondance de l'extraction des coûts réels,
  **les bornes de la matrice de risques, les seuils d'alerte des indices et le délai maximal entre deux
  revues** (FBS-3) » ; Vérif : « mène à leur terme le paramétrage de chacune des fonctions FBS-3.1 à
  FBS-3.4 » ; WF-ADM-0010 (l. 1304) : « trois rôles d'habilitation prédéfinis … dont les permissions
  couvrent respectivement les usages décrits par WF-INTF-0010, WF-INTF-0020 et WF-INTF-0030 » ;
  **ce que dit le contrat** : la fixture donne au « Manager » `cost_settings.write`,
  `resource_settings.write`, mais seulement `risk_settings.read` et `indicator_settings.read`
  (l. 225-226). Le résumé de `access_roles.json` dit « les trois prédéfinis tels que livrés ».
- **Constat.** Le témoin est ce que le faux back sert et ce que le service copiera pour amorcer les trois
  rôles (WF-EXP-0020). Tel quel, un porteur du rôle livré « manager » ne peut pas régler les bornes de la
  matrice (FBS-3.3) ni les seuils et le délai (FBS-3.4) : le témoin contredit frontalement la Vérif de
  WF-INTF-0020. Les deux autres rôles prédéfinis sont justes (voir « Ce qui est juste »). Le générateur
  `tools/src/wftools/mockaudit.py:478` tient d'ailleurs pour acquis que le Manager ne porte que ces deux
  écritures (`WITHDRAWN = ("cost_settings.write", "resource_settings.write")`, « which it holds »), ce qui
  propage l'erreur dans les exemples d'audit.
- **Proposition.** Ajouter `risk_settings.write` et `indicator_settings.write` au « Manager » de
  `access_roles.json`, `me_manager.json`, `me_directory.json`, `access_roles_by_updated_by.json`,
  `access_role_updated.json`, `access_role_renamed.json` (mêmes permissions, dans l'ordre du catalogue),
  et reprendre `WITHDRAWN` du générateur d'audit puis `make mock-data`. Ou, si l'auteur veut un manager
  réduit, le dire dans DECISIONS.md en citant WF-INTF-0020 — mais la Vérif ne laisse pas de marge.
- **DECISIONS.md** : aucune décision (grep `Manager`, `risk_settings.write`, `WF-INTF-0020`,
  `WF-ADM-0010` : la l. 4023 ne parle que du découpage des écritures de `ReferenceSettings`).

#### A-02 — La périodicité de la lecture des comptes n'a pas de surface
- **gravité** : majeur ; **emplacement** : `docs/api/paths/access.yaml:535-566` (`startIdentitySync`,
  « à la demande ») et `:568-594` (`getLatestIdentitySync`, « demandée ou planifiée ») ; rien dans
  `platform.yaml` (grep `identity_sync|sync` : aucun chemin) ; **exigence** : WF-ADM-0070 (l. 1225) :
  « Waterfall lit les comptes du fournisseur d'identité … à la demande et **selon une périodicité choisie
  par un utilisateur habilité, quotidienne par défaut, comme celle des sauvegardes (WF-ADM-0170)** » ;
  Vérif : « Une personne ajoutée à l'annuaire a un compte dans Waterfall **au terme de la périodicité
  choisie**, sans intervention » ; PBS-5.3 (l. 3541) : « déclenchées par la plateforme à l'heure
  convenue » ; **ce que dit le contrat** : la sauvegarde a `getBackupSchedule`/`setBackupSchedule`
  (`BackupSchedule`, `platform.yaml:228`) ; la lecture des comptes n'a que son déclenchement manuel
  et son compte rendu, et `IdentitySyncReport` dit « la lecture que la plateforme planifie » sans que
  rien ne la règle.
- **Constat.** Une exigence demande un réglage par un utilisateur habilité ; le contrat ne le porte pas,
  et l'écran d'administration ne pourra ni le montrer ni le changer. Un implémenteur du service fixerait
  la période en paramètre d'exploitation, ce que la spec réserve explicitement à l'utilisateur. Un ajout
  après le gel est additif mais c'est une opération que la spec exige : à trancher maintenant.
- **Proposition.** Soit deux opérations symétriques des sauvegardes :
  ```yaml
  /identity-syncs/schedule:
    get:  { operationId: getIdentitySyncSchedule }   # users.read ; 200 IdentitySyncSchedule
    put:  { operationId: setIdentitySyncSchedule }   # users.write ; 200, 400, 401, 403, 412, 422, 503
  IdentitySyncSchedule:   # schemas/access.yaml
    type: object
    required: [is_enabled, frequency, at_time, lock_version]
    properties:
      is_enabled: { type: boolean }
      frequency: { type: string, enum: [daily, weekly] }
      at_time: { type: string, pattern: '^([01]\d|2[0-3]):[0-5]\d$' }   # UTC, comme BackupSchedule
      weekday: { anyOf: [{ type: integer, minimum: 1, maximum: 7 }, { type: 'null' }] }
      lock_version: { $ref: ../common.yaml#/LockVersion }
  ```
  avec une fixture « quotidienne à 02:00 » cohérente avec `identity_sync_report.json` (lecture « de
  cette nuit, achevée à 2 h »). Soit une décision écrite qui range la périodicité parmi les paramètres
  d'exploitation — mais elle contredirait « choisie par un utilisateur habilité ».
- **DECISIONS.md** : aucune décision (grep `périodicité`, `quotidienne`, `schedule` + `sync`,
  `heure convenue` : rien ; la section 6 de la l. 3784 ne traite que du renommage `directory` →
  `identity`).

#### A-03 — L'écran d'état ne porte pas les paramètres d'exploitation ni la durée de validité du cache
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/platform.yaml:3-36`
  (`SystemStatus`, `required: [version, components, storage, last_backup_copy, alerts]`), servi par
  `paths/system.yaml:100-123` (`getSystemStatus`) ; **exigence** : WF-ADM-0130 (l. 1379) : « Un écran
  d'état présente … la version de chaque composant employé (WF-CMP-0020) ; **les valeurs en vigueur des
  paramètres d'exploitation (§4.5.1)** ; la date et le résultat de la dernière lecture des comptes … » ;
  Vérif : « **L'écran présente la durée de validité du cache en vigueur.** » ; §4.5.1 (l. 4124) : « les
  paramètres d'exploitation : des valeurs fixées par l'exploitant au déploiement … chacune livrée avec
  une valeur par défaut que le document donne là où il la cite » (les trois seuils d'alerte de
  WF-OBS-0030, la durée de validité du cache, la taille d'avatar, la rétention des tâches de fond…) ;
  **ce que dit le contrat** : `SystemStatus` porte version, composants, stockage, trois derniers
  résultats et alertes ; rien des paramètres d'exploitation, et sa description dit « Il ne présente que
  des valeurs issues des métriques », ce que l'exigence ne dit pas (les dates sont lues en base,
  WF-OBS-0010).
- **Constat.** Un attribut que l'exigence et sa Vérif nomment manque au schéma ; le front ne peut pas
  présenter la durée de validité du cache, et le contrôle de recette de WF-ADM-0130 échoue. Additif après
  le gel, mais le schéma de l'écran d'état est la seule lecture de ces valeurs : mieux vaut fixer leur
  forme avant.
- **Proposition.** Ajouter à `SystemStatus` un objet exigé, aux noms du document :
  ```yaml
  operating_parameters:
    type: object
    required: [cache_validity_seconds, task_queue_stall_threshold_minutes,
               storage_alert_ratio, error_rate_alert_ratio, background_task_retention_days]
    properties:
      cache_validity_seconds: { type: integer, minimum: 1 }           # Vérif WF-ADM-0130
      task_queue_stall_threshold_minutes: { type: integer, minimum: 1 }  # WF-OBS-0030, livré 15
      storage_alert_ratio: { $ref: ../common.yaml#/Decimal }        # livré 0.85
      error_rate_alert_ratio: { $ref: ../common.yaml#/Decimal }     # livré 0.05 sur cinq minutes
      background_task_retention_days: { type: integer, minimum: 1 } # §4.4.1
  ```
  (la liste exacte est à arrêter d'après §4.5.1 : tous les paramètres que le document « cite avec leur
  valeur par défaut »), et compléter les quatre fixtures `system_status*.json`. Corriger la description
  « Il ne présente que des valeurs issues des métriques ».
- **DECISIONS.md** : aucune décision (grep `paramètres d'exploitation`, `durée de validité`, `cache`,
  `SystemStatus`, `WF-ADM-0130` : seules les l. 2666 et 3790 touchent `SystemStatus`, pour la copie
  externe et le renommage).

#### A-04 — Le renvoi du courriel de fixation du mot de passe n'a pas d'opération
- **gravité** : majeur (à trancher) ; **emplacement** : `docs/api/paths/access.yaml:468-512`
  (`createPasswordSetupLink`), `schemas/access.yaml:62-78` (`UserCreated.invitation_sent`) ;
  **exigence** : WF-ADM-0140 (l. 1237) : « fixe et réinitialise le mot de passe par un lien envoyé à
  l'adresse du compte … Un compte local nouvellement créé n'a pas de mot de passe et ne peut pas se
  connecter avant que son porteur n'en ait fixé un par ce lien, **qu'un utilisateur habilité peut
  renvoyer**. Un utilisateur habilité peut **aussi** obtenir ce lien depuis Waterfall, pour le remettre
  au porteur par un autre canal » ; Vérif : « par le lien reçu ou remis » ; **ce que dit le contrat** :
  `createPasswordSetupLink` « engendre … le lien … et le rend à l'appelant pour qu'il le remette par un
  autre canal » ; `createUser` dit si l'invitation est partie (`invitation_sent`) et, sinon, renvoie
  à `createPasswordSetupLink`. Aucune opération ne fait repartir le courriel.
- **Constat.** La spec décrit deux gestes distincts — renvoyer le courriel, obtenir le lien — et le
  contrat n'en porte qu'un. Sur une installation avec messagerie, l'administrateur dont l'invité a
  perdu son courriel n'a que la remise manuelle ; la Vérif de WF-ADM-0140 (« lien reçu ou remis »)
  attend les deux. Additif après le gel, mais c'est une opération que la spec exige.
- **Proposition.** Soit `POST /users/{user_id}/invitation` (`resendInvitation`, 202 ou 204 ;
  mêmes 401/403/404/409 `is_local_account`/`is_active_account`/503 que le lien ; inscrit au journal
  comme `password_link_create`, ou action propre), soit une décision écrite disant que « renvoyer » se
  fait par la console du fournisseur d'identité ou se confond avec la remise manuelle — en citant la
  phrase de WF-ADM-0140 qu'elle écarte.
- **DECISIONS.md** : la l. 1304 (« Un administrateur obtient le lien ») et la l. 5818 (`invitation_sent`)
  traitent l'obtention et l'envoi initial ; aucune ne parle du renvoi (grep `renvoy`, `resend`,
  `invitation`).

#### A-05 — Le 409 de `getBackgroundTaskResult` ne dit ni quand ni quel code
- **gravité** : mineur ; **emplacement** : `docs/api/paths/system.yaml:251` (`'409': { $ref:
  ../components/responses.yaml#/Conflict }`) ; **exigence** : WF-ARC-0090 (l. 3831) : « La requête rend
  la main en désignant la tâche créée, dont l'utilisateur suit l'avancement et le résultat » ;
  **ce que dit le contrat** : la description (l. 217-220) parle du téléchargement du fichier et de
  WF-DAT-0120 ; rien sur le 409. `responses.yaml#/Conflict` dit « `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` nommant la condition manquante », mais aucune `CommandCondition` ne
  correspond (une tâche qui court, une tâche sans résultat, un fichier expiré ?).
- **Constat.** Le serveur ne sait pas quoi rendre, ni le front quoi afficher : un refus déclaré sans
  cause est une ambiguïté à lever (catégorie 2 du brief), et le code qu'il porterait doit être choisi
  avant le gel s'il demande une `CommandCondition` nouvelle.
- **Proposition.** Soit décrire : « 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à
  `task_succeeded` (valeur nouvelle de `CommandCondition`) tant que la tâche n'a pas abouti, ou pour une
  tâche qui ne produit pas de fichier (`result_url` nul) ; un fichier dont la rétention est passée est
  un 404 (WF-DAT-0120) », avec un exemple ; soit retirer le 409 et ne garder que le 404.
- **DECISIONS.md** : l. 896 (« Le résultat d'une tâche se télécharge nommé et typé », #323) ne parle que
  de `Content-Disposition` et des types ; aucune décision sur le 409.

#### A-06 — `highlight_tasks_added_after_reference` : sans description, et la spec couvre aussi les lignes à budget nul
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/access.yaml:296`
  (`highlight_tasks_added_after_reference: { type: boolean }`) ; **exigence** : WF-ADM-0040 (l. 1273) :
  « **Une** préférence d'affichage permet de distinguer visuellement les tâches ajoutées après la révision
  de référence **et les lignes dont le montant budgété est nul** (WF-RAE-0040) » ; WF-RAE-0040 (l. 2681) :
  « Une préférence d'affichage permet de distinguer visuellement les lignes dont le montant budgété est
  nul (WF-ADM-0040) » ; **ce que dit le contrat** : un booléen nommé par les seules tâches, sans
  description — la seule propriété de `DisplayPreferences` qui n'en a pas.
- **Constat.** Le front ne sait pas si ce réglage gouverne aussi les lignes à budget nul (lecture
  littérale de WF-ADM-0040 : une préférence pour les deux) ou s'il en manque un. Si c'est la même
  préférence, le nom gelé ne le dira jamais ; si c'en est une autre, elle manque. Corrigible par une
  description seule, d'où la gravité, mais le choix du nom se fait maintenant.
- **Proposition.** Décrire : « Vrai, la grille distingue les tâches ajoutées après la révision de
  référence et, dans le reste à engager, les lignes dont le montant budgété est nul (WF-ADM-0040,
  WF-RAE-0040) ; absent, faux. » Ou, si l'auteur préfère deux réglages, ajouter
  `highlight_zero_budget_lines` avant le gel.
- **DECISIONS.md** : aucune décision (grep `highlight`, `ajoutées après la révision de référence`,
  `montant budgété est nul`).

#### A-07 — `ActorRef` n'exige pas `user_id` pour un compte
- **gravité** : mineur ; **emplacement** : `docs/api/components/common.yaml:115-128` (`ActorRef`,
  `required: [kind]`) ; le client engendré le dit : `frontend/src/api/generated/schema.d.ts:2917`
  (`user_id?: …`) ; **exigence** : WF-DAT-0070 (colonnes d'audit, l. 3934) et WF-ADM-0060 : « ses actes
  lui restent attribués, par son identifiant » ; **ce que dit le contrat** : `kind: user|platform`,
  `user_id` et `display_name` facultatifs ; la description de `display_name` dit « Absent pour la
  plateforme » mais rien n'oblige `user_id` quand `kind` vaut `user`. `AuditActorFacet`
  (`audit.yaml:258`) exige, lui, `user_id` et `display_name`.
- **Constat.** Toutes les fixtures portent `user_id` et `display_name` pour un compte, jamais pour la
  plateforme : la forme est en fait une union discriminée que le schéma ne dit pas. Le front teste un
  identifiant qui ne manque jamais ; le service peut en omettre un sans violer le contrat. Même concept
  typé différemment selon la famille (`AuditActorFacet`). Resserrer est compatible pour les lecteurs.
- **Proposition.**
  ```yaml
  ActorRef:
    oneOf:
      - type: object
        required: [kind, user_id, display_name]
        properties:
          kind: { const: user }
          user_id: { $ref: '#/Uuid' }
          display_name: { anyOf: [{ type: string }, { type: 'null' }] }
      - type: object
        required: [kind]
        properties: { kind: { const: platform } }
    discriminator: { propertyName: kind }
  ```
  ou, à défaut, `if: { properties: { kind: { const: user } } } then: { required: [user_id, display_name] }`.
- **DECISIONS.md** : l. 2691, 5829, 6072 décrivent `ActorRef` (identifiant et nom d'un compte, ou
  `platform`) sans décider de la contrainte ; aucune décision contraire.

#### A-08 — `UserAccount.required` : `org_node_label` exigé mais pas `org_node_id`, ni `has_avatar`
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/access.yaml:121-133` (liste
  `required`), `:165-167` (`org_node_id`, nullable), `:184` (`has_avatar: { type: boolean }`) ; client
  engendré `schema.d.ts:2945` (`org_node_id?`), `:2952` (`has_avatar?`) ; **exigence** : WF-ADM-0050
  (l. 1197) : « un rattachement facultatif à un nœud d'organisation (WF-ADM-0030), un avatar facultatif »
  ; **ce que dit le contrat** : le libellé du nœud est exigé (nul sans rattachement), l'identifiant du
  même nœud ne l'est pas ; l'avatar se dit par `has_avatar`, facultatif. Toutes les fixtures `me*`,
  `user*`, `users*` portent les deux.
- **Constat.** « Facultatif » dans la spec veut dire nullable, ce que `anyOf … null` fait déjà ; laisser
  le champ absent en plus crée deux façons de dire « sans rattachement » et oblige le front à tester
  `undefined` et `null`. Incohérence interne entre `org_node_id` et `org_node_label`.
- **Proposition.** Ajouter `org_node_id` et `has_avatar` à `required` de `UserAccount` (compatible
  pour tout lecteur ; les fixtures sont déjà conformes).
- **DECISIONS.md** : aucune décision (grep `has_avatar`, `org_node_id` + `required`).

#### A-09 — `BackgroundTaskRef` : cinq champs facultatifs que toute fixture porte
- **gravité** : mineur ; **emplacement** : `docs/api/components/common.yaml:812`
  (`required: [task_id, kind, status]`) et `:839-860` ; client `schema.d.ts:2896-2902` ; **exigence** :
  WF-ARC-0090 (l. 3831) : « dont l'utilisateur suit l'avancement et le résultat » ; WF-IHM-0080
  (l. 3275) : « l'échec nomme ce qui a échoué » ; `listBackgroundTasks` (system.yaml:131) : « les plus
  récentes d'abord » ; **ce que dit le contrat** : `progress`, `submitted_at`, `finished_at`, `problem`,
  `result_url` facultatifs ; `result_url` est une `string` sans `format: uri-reference`. Le balayage des
  31 fixtures de tâches (toutes nature × statut) : aucune n'omet un de ces champs, `finished_at` non nul
  pour toute tâche finie, `problem` présent pour tout échec.
- **Constat.** Le tri de la liste suppose `submitted_at` ; le suivi de WF-IHM-0080 suppose `progress`
  et `problem`. Les laisser facultatifs force des gardes inutiles dans le front et laisse le service
  libre de ne pas les rendre. Resserrer est compatible.
- **Proposition.** `required: [task_id, kind, status, progress, submitted_at, finished_at, problem,
  result_url]`, les trois derniers nullables comme aujourd'hui ; `result_url: { type: string,
  format: uri-reference }` avec sa description (« chemin sous `/api/v1`, comme les exemples »).
- **DECISIONS.md** : aucune décision (grep `submitted_at`, `result_url`).

#### A-10 — Exemples manquants
- **gravité** : mineur ; **emplacements** : `docs/api/paths/access.yaml:833-839` (`deleteAccessRole`,
  409 `ACCESS_ROLE_IN_USE` : seul refus par code propre de la famille sans fixture — aucun
  `access_role_*in_use*.json`) ; `:768-772` (`getAccessRole` 200, sans `examples`) ;
  `docs/api/paths/system.yaml:69-80` (`getReadiness` 200, sans exemple ni fixture) ; `:171`
  (`listBackgroundTasks` 422 générique, sans exemple : un `status` hors de `BackgroundTaskStatus` ou
  un `finished_since` mal formé, `/query/finished_since` par `DATE_INVALID`) ; **exigences** :
  WF-ADM-0090 (« Un rôle ne peut être supprimé tant qu'un compte le porte »), WF-EXP-0040.
- **Constat.** Le faux back ne sert donc ni le refus de suppression du rôle « Chef de projet » (porté
  par Alix Moreau, désactivée — bon cas : « compte tous les comptes qui portent le rôle, désactivés
  compris »), ni la sonde de préparation ; le front ne peut pas éprouver ces écrans.
- **Proposition.** `access_role_delete_refused.json` (`ACCESS_ROLE_IN_USE`, 409, sur
  `…0703`), `access_role.json` (le « Manager » tel que `access_roles.json` le liste), `readiness.json`
  (sept composants `is_available: true` cohérents avec `system_status.json`), `tasks_status_invalid.json`.
- **DECISIONS.md** : aucune décision.

#### A-11 — Deux mineurs de vocabulaire
- **gravité** : mineur ; **emplacements** : `docs/api/components/schemas/access.yaml:538-541`
  (`AccessRoleUpdate` : « Modification d'un rôle d'**accès** », partout ailleurs « rôle d'habilitation »,
  glossaire) ; `docs/api/components/common.yaml:505-513` : `TASK_INTERRUPTED_BY_RESTORE` est rangé après
  le commentaire « # 422 — règle métier » alors que son seul exemple (`task_interrupted_by_restore.json`)
  porte `status: 409` — comme `BACKUP_FROM_NEWER_VERSION` juste avant, à 422, le lecteur ne sait pas
  lequel est voulu.
- **Proposition.** « Modification d'un rôle d'habilitation » ; un commentaire « # 409 dans `problem` d'une
  tâche échouée » devant `TASK_INTERRUPTED_BY_RESTORE`, ou le mettre à 422 dans la fixture.
- **DECISIONS.md** : aucune décision.

### Ce qui est juste

- **Tâches de fond.** Les neuf opérations à `'202'` du contrat (`startIdentitySync`, `openImport`,
  `applyImport`, `requestExport`, `startBackup`, `startRestore`, `markRevision`, `mergeCostStructure`,
  `declareRiskOccurrence`) ont chacune leur valeur dans `BackgroundTaskRef.kind` (`identity_sync`,
  `import_analysis`, `import_apply`, `export`, `backup`, `restore`, `revision_mark`, `structure_merge`,
  `risk_occurrence`) : énumération complète, sans valeur orpheline ; les 31 fixtures qui portent une tâche
  n'emploient que ces natures et les quatre statuts, et toutes sont cohérentes (`finished_at`, `problem`).
  `listBackgroundTasks` est paginé, filtré par statut et date, 401/422/503 déclarés ; `getBackgroundTaskResult`
  déclare ses trois types de média et `Content-Disposition` conformément à DECISIONS l. 896.
- **Catalogue et rôles.** `PermissionCode` (51 valeurs) = `permissions.json` (51, même ordre) ; deux
  permissions par fonction de second niveau FBS-1.1 à FBS-4.9, lecture seule pour FBS-1.3, FBS-1.5,
  FBS-2.1 à 2.7, huit irréversibles et deux structurantes : conforme à WF-ADM-0100. Dans les douze
  fixtures `me*`, `permissions` est exactement l'union, dans l'ordre du catalogue, des permissions des
  rôles de `access_roles.json`, et `access_role_labels` correspond aux `access_role_ids`. Les rôles
  prédéfinis « Chef de projet » (toutes les permissions propres hors `platform_restore` et
  `all_projects_read`, écritures FBS-4, `project_create`) et « Administrateur » (FBS-1 entier,
  `platform_restore`) sont conformes à WF-INTF-0010 et WF-INTF-0030.
- **Comptes.** `User`/`UserSelf`/`UserCreated`, `available_commands` dans l'ordre d'`UserCommand`,
  conditions `last_administrator`, `is_not_anonymized`, `is_deactivated_account`, `is_local_account`,
  `is_active_account` toutes dans `CommandCondition` ; refus 409/412/422 déclarés avec exemples sur
  `createUser`, `updateUser`, `setUserActivation`, `anonymizeUser`, `setUserAccessRoles`,
  `createPasswordSetupLink` ; `is_active` booléen assumé (DECISIONS l. 1173) ; filtres d'audit et tri
  de `listUsers`/`listAccessRoles` conformes aux conventions `_from`/`_to`, `_min`/`_max`, départage par
  identifiant ; 401 et 503 sur toute opération gardée, `security: []` sur les quatre sondes publiques.
- **Préférences.** `DisplayPreferences`/`GridPreferences` portent colonnes, largeurs, tri, filtres et
  `page_size` ∈ {10, 25, 50, 100} par grille (WF-IHM-0060), la langue (WF-INTF-0160), le thème, les
  chronologies et les graphiques ; bornes (#874, #1235) identiques entre description du 422, schéma et
  les trois fixtures de refus ; `me_grid_settings.json` cohérent (`sort.column: budgeted_amount` est une
  valeur de `NodeSort`, les filtres sont des paramètres de `listAccessRoles`/`listUsers`).

### Doutes

- **`listAccessRoles` sans pagination** (`access.yaml:618-730`, « Une table plate ») : DECISIONS l. 3807
  l'assume (« tableau nu … la liste n'étant pas paginée »). WF-IHM-0060 (l. 3251) dit « Une table plate
  se lit par pages », et `GridPreferences.page_size` cite « le défaut de `limit` » ; une pagination côté
  front tient la phrase pour quelques dizaines de rôles. Je ne le compte pas comme constat, mais le
  consolidateur peut le rapprocher de la pagination que US-0640/L6 ajoute à `listRisks`.
- **`BackgroundTaskRef` ne nomme ni objet ni projet** : DECISIONS l. 103 l'a écarté « attendre EP-04 »,
  et §4.4.1 (l. 3857) dit pourtant qu'« une tâche de fond porte [une référence] vers le sien ». Un
  `project_id`/`object` facultatif s'ajoute après le gel sans rompre ; s'il devait être exigé, c'est
  maintenant. WF-IHM-0080 (« l'échec nomme ce qui a échoué ») est tenu par `problem.params`.
- **`startIdentitySync` sans 409 de concurrence** : `startBackup` refuse une seconde sauvegarde
  (`no_backup_running`) ; deux lectures des comptes simultanées écriraient les mêmes comptes. Rien dans
  la spec ne l'exige ; aucune décision. À trancher par l'auteur.
- **`installation.json` borne l'avatar à 2 Mio** quand §4.4.1 (l. 3863) dit « livré à 512 Ko » : un
  réglage (DECISIONS l. 515), le témoin peut en avoir changé ; je ne tranche pas.
- **`getMetrics` déclare un 404** (`system.yaml:98`) sans dire pourquoi (point servi seulement du réseau
  interne, WF-SEC-0010 ?) ; aucune décision trouvée.
- **`listPermissions` sans 404** : lisible par toute session, sans permission de consultation nommée ;
  cohérent avec l'écran des rôles, mais non écrit (DECISIONS l. 2742 ne parle que d'`audit_log.read`).

## Annexe B — Sauvegarde, restauration et journal d'audit


**Lu** : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/platform.yaml` (562 l.),
`docs/api/paths/audit.yaml` (186 l.), `docs/api/components/schemas/platform.yaml` (548 l.),
`docs/api/components/schemas/audit.yaml` (291 l.) en entier ; `components/common.yaml` (`ActorRef`,
`Problem`, `ErrorCode`, `BackgroundTaskRef`), `components/parameters.yaml`, `components/responses.yaml`,
`schemas/projects.yaml#/CommandCondition`, `schemas/access.yaml#/PermissionCode`, `UserUpdate`,
`schemas/exchanges.yaml#/FileUpload`, `paths/exchanges.yaml#completeChunkedUpload`, `paths/system.yaml`
(sonde), `paths/projects.yaml#exitProject`, `paths/costs.yaml#setActualCostTrackedScope`,
`paths/revisions.yaml#markRevision/designateReferenceRevision`, `paths/access.yaml#createPasswordSetupLink`.
Spécification : §3.4.2.4–3.4.2.5 (l. 1384–1440), §4.4.1 (table 10, l. 3860–3905), §4.4.4 (4072–4088),
§4.5.4 (4185–4215), §4.6.1 (4217–4259), §4.6.4 (4369–4397), et WF-ADM-0060, -0090, -0100, -0110,
-0130, -0140, WF-PRJ-0010, WF-CYC-0030/-0090/-0130, WF-REV-0020/-0050, WF-RIS-0060, WF-CRE-0030,
WF-IHM-0090, WF-ARC-0090, WF-OBS-0020/-0030, WF-DAT-0130. `DECISIONS.md` : sections EP-02/L42 (journal,
copie externe), L42d (tri, facettes), L43c, EP-14/L42h, L42m, L42o (extraits), EP-03/US-0350/L1,
US-0360/L2b, US-0410/L2, US-0440/L1 et L2, « Reprise de `main` après EP-03 », « Le contrat figé
(EP-16) » (grep). Roadmap EP-16 : « Constats reçus », « Les modifications du contrat ».
Générateurs : `tools/src/wftools/mockaudit.py` (en entier), `mocklists.py` (partie sauvegardes),
`tools/paths.toml`. **69 fixtures ouvertes** : les 16 du journal (13 `audit_events*`, 2 `audit_facets*`,
`audit_events_period_inverted`), les 53 des sauvegardes (`backup*`, `backups*`, `backup_schedule*`,
`external_backup_location*`, `restore_*`, `task_backup_queued`, `task_restore_*`,
`task_interrupted_by_restore`, `file_upload_external_backup`, `system_status_backup_failed`,
`me_auditor`, `users`, `project_created`, `revisions`). Le front a été consulté pour un seul point
(`frontend/src/components/audit/audit-columns.tsx`, `frontend/src/app/admin/audit-log/page.tsx`).

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| B-01 | majeur | `docs/api/components/schemas/audit.yaml:125` (`AuditProject.code`) | Le code du projet est une chaîne non nulle, quand un projet peut n'en avoir aucun avant En cours : un marquage, une désignation ou une création sur un projet sans code ne peut pas être inscrit | WF-SEC-0030, WF-PRJ-0010, WF-CYC-0030 |
| B-02 | majeur | `docs/api/components/schemas/audit.yaml:173-183` (`AuditParams`) | Objet fermé (`additionalProperties: false`) dont les paramètres des actions d'un projet, de la sauvegarde et de la restauration sont « jusqu'à l'EPIC qui les réalise » vides, et « un paramètre nouveau est une modification du contrat » : à trancher avant le gel (`project_exit` sans état d'arrivée, `restore` sans la date de la sauvegarde restaurée, `import_apply` sans nature) | WF-SEC-0030, WF-CYC-0060, WF-ADM-0160 |
| B-03 | majeur | `docs/api/components/schemas/audit.yaml:115-126` (`AuditProject`), `docs/api/paths/audit.yaml:26-31` | L'inscription doit « mener au projet lorsque l'utilisateur peut le consulter » et ne pas y mener s'il n'existe plus, mais rien ne le dit : le portefeuille et la matrice portent `can_open`, le journal non, et l'écran relit toute la liste des projets pour le savoir | WF-ADM-0190, WF-ADM-0110 |
| B-04 | majeur | `docs/api/components/schemas/platform.yaml:230,234-251` (`BackupSchedule`) | `frequency` et `at_time` facultatifs, `weekday` nullable mais facultatif, pour une planification « à une fréquence et une heure choisies » ; le 422 ne dit ni le jour manquant d'une hebdomadaire ni le jour en trop d'une quotidienne | WF-ADM-0170 |
| B-05 | majeur | `docs/api/components/schemas/platform.yaml:256-259` (`BackupSchedule.retained_count`) | « Le nombre de sauvegardes **planifiées** gardées » contredit la spec (« le nombre de sauvegardes conservées », marquées exceptées) et le contrat lui-même (`is_retained` : « celles que la rotation supprimera à leur tour » ; `backup_released`) : une manuelle non marquée est-elle comptée, et supprimée ? | WF-ADM-0170 |
| B-06 | majeur | `docs/api/paths/audit.yaml:3`, `schemas/audit.yaml:128,143` (`/audit-events`, `AuditEvent`, `audit_event_id`) | La table 10 du §4.4.1 nomme l'objet `audit_entry` ; le contrat dit `audit_event`, sans décision : un renommage est impossible après le gel | §4.4.1, README « Conventions » |
| B-07 | mineur | `fixtures/api/task_restore_queued.json`, `backup_pending.json`, `restore_during_backup_refused.json`, `backup_start_during_restore_refused.json` | La chronologie des exemples se contredit : une restauration acceptée à 14 h 04 min 30 s pendant que la sauvegarde de 14 h 04 s'exécute (prise à 14 h 04 min 50 s), alors que la restauration de 14 h 04 min 20 s est refusée pour cette raison | WF-ADM-0150, WF-ADM-0160 |
| B-08 | mineur | `docs/api/components/schemas/platform.yaml:5` (`SystemStatus.required`) | `last_backup`, `last_identity_sync`, `last_restore_test` ne sont pas exigés quand `last_backup_copy` l'est, tous quatre nullables et tous quatre demandés par l'écran d'état | WF-ADM-0130 |
| B-09 | mineur | `docs/api/components/schemas/platform.yaml:399-431`, `docs/api/paths/platform.yaml:509-519` (`RestoreRequest`, `startRestore` 400) | `confirmed` faux ou absent : 422 par le schéma (`const: true`) ou 400 `CONFIRMATION_REQUIRED` ? Les deux désignations à la fois, ou aucune (`oneOf`) : refus non décrit | WF-ADM-0160 |
| B-10 | mineur | `docs/api/components/schemas/audit.yaml:83-84,164` (`AuditObject.label`, `AuditEvent.project`) | « nul pour une sauvegarde … sa date est celle de l'inscription » est faux pour `restore` ; le dépôt manque à la liste des objets sans projet | WF-SEC-0030 |
| B-11 | mineur | `docs/api/paths/platform.yaml:173-175,302-305` (`getBackup`, `getBackupSchedule`) | Seules opérations de la famille qui ne nomment pas leur permission (`backups.read`) | WF-ADM-0100 |

#### B-01 — Le code d'un projet du journal ne peut pas être nul

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/audit.yaml:115-126`, `AuditProject`
  (`code: { type: string }`, exigé), employé par `AuditEvent.project` (l. 162) et `AuditFacets.projects`
  (l. 284) ; **exigence** WF-SEC-0030 : « L'auteur, l'objet et le projet y sont désignés par leur
  identifiant et par leur libellé — et leur code pour un projet … — tels qu'ils étaient au moment de
  l'action » ; WF-PRJ-0010 : le code « peut être renseigné à tout moment, et il est exigé pour le
  passage du projet à l'état En cours » ; WF-CYC-0030 : le passage à En cours se produit dès que le
  projet porte référence et code « quel que soit l'ordre de ces deux saisies » ; **ce que dit le
  contrat** : `Project.code` est `anyOf: [string, null]` (`schemas/projects.yaml:32-36`), et
  `project_created.json` est « sans code » ; `AuditProject.code` est `{ type: string }` non nullable.
- **Constat.** Un projet se crée, se chiffre, marque son offre et la désigne référence avant d'avoir
  un code (l'offre peut être désignée avant le code, WF-CYC-0030). `revision_mark`,
  `reference_designate`, `import_apply` d'un devis, et `project_create` qu'US-0640/L6 ajoute (ses
  `params` disent « le code et le libellé du projet ») ont alors un projet sans code, que le schéma ne
  peut pas porter : le serveur devra inventer une chaîne (vide ?) ou refuser d'inscrire. Le témoin ne
  le montre pas parce que PRJ-001 a son code depuis sa création. La nullabilité d'un champ exigé ne se
  change pas sans rompre le client engendré : c'est avant le gel.
- **Proposition.**
  ```yaml
  AuditProject:
    properties:
      code:
        anyOf: [{ type: string }, { type: 'null' }]
        description: Le code du projet au moment de l'action ; nul pour un projet qui n'en avait pas encore (WF-PRJ-0010).
  ```
  Et dire dans `listAuditEvents.sort_by` où se range un projet sans code (après les autres dans l'ordre
  croissant, comme une inscription sans projet). Hors du périmètre d'US-0640/L6, qui n'écrit que les
  actions et leurs `params`, non `AuditProject`.
- **DECISIONS.md** : aucune décision sur `AuditProject.code`. Précédent dans le même sens : « Les
  paramètres des refus reçoivent un schéma » (l. 8057-8061) — `ProblemProject.project_code` « nul pour
  un projet sans code ».

#### B-02 — Les paramètres des actions d'un projet, de la sauvegarde et de la restauration, remis à plus tard dans un objet fermé

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/audit.yaml:173-183`
  (`AuditParams`, `additionalProperties: false`) ; **exigence** WF-SEC-0030 : « Chaque inscription
  porte l'action, la date, l'auteur, l'objet concerné et le projet s'il y en a un » ; WF-CYC-0060 (les
  trois sorties : Terminé, Perdu, Abandonné) ; WF-ADM-0160 : « la restauration elle-même s'inscrit au
  journal une fois faite » ; **ce que dit le contrat** : « Un objet vide pour une action qui n'a rien à
  dire de plus que son objet … et, **jusqu'à l'EPIC qui les réalise, pour les actions d'un projet, de
  la sauvegarde et de la restauration**. Un paramètre nouveau est une modification du contrat. »
- **Constat.** Le contrat annonce lui-même une modification à venir sur un objet fermé, dans un
  contrat que le gel va figer. Ce qui manque de façon vérifiable : (a) `project_exit` — l'inscription
  « sortie du cycle de vie » ne dit pas vers quel état terminal (`ProjectExit.to_state` : `completed`,
  `lost`, `abandoned`), ni le motif que la transition conserve (WF-CYC-0130) : un auditeur ne distingue
  pas un projet terminé d'un projet perdu sans ouvrir le projet, qu'il ne peut peut-être pas ouvrir
  (WF-ADM-0190) ; (b) `restore` — l'objet est la sauvegarde (`label` nul) ou le dépôt (expiré le
  lendemain, WF-DAT-0120), `occurred_at` est la fin de la restauration : la date de l'état remis en
  place, celle que la confirmation a dû énoncer (`acknowledged_backup_taken_at`), n'est nulle part dans
  l'inscription ; (c) `import_apply` — l'objet est nommé par son fichier ; la nature de l'import
  (`ExchangeKind`) ne se lit que dans `object.revision` (nul pour les coûts réels), indirectement ;
  (d) `backup` — rien à ajouter (`origin` se lit de l'auteur). Si l'auteur décide que ces inscriptions
  restent sans paramètre, il faut l'écrire dans DECISIONS.md et retirer « jusqu'à l'EPIC qui les
  réalise » : la phrase actuelle promet un changement incompatible.
- **Proposition.** Au minimum :
  ```yaml
  AuditParams:
    properties:
      to_state:
        allOf: [{ $ref: projects.yaml#/ProjectState }]
        description: '`project_exit` : l''état terminal atteint, `completed`, `lost` ou `abandoned` (WF-CYC-0060).'
      reason:
        anyOf: [{ type: string }, { type: 'null' }]
        description: '`project_exit` : le motif donné à la confirmation, nul s''il n''en a pas été donné (WF-CYC-0130).'
      backup_taken_at:
        allOf: [{ $ref: ../common.yaml#/Timestamp }]
        description: '`restore` : la date de la sauvegarde remise en place, celle que la confirmation a énoncée (WF-ADM-0160).'
      import_kind:
        allOf: [{ $ref: exchanges.yaml#/ExchangeKind }]
        description: '`import_apply` : la nature de l''import appliqué (WF-INTF-0090).'
  ```
  et retirer « jusqu'à l'EPIC qui les réalise ». `project_create` et `revision_abandon` sont à
  US-0640/L6 et ne sont pas visés ici.
- **DECISIONS.md** : « Le journal d'audit rend les paramètres de l'action (EP-03/US-0410/L2, #706) »
  (l. 5866) ne décide que des comptes et des rôles ; rien sur les actions d'un projet, de la sauvegarde
  ni de la restauration.

#### B-03 — Le journal ne dit pas si l'inscription mène au projet

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/audit.yaml:115-126`
  (`AuditProject`), `docs/api/paths/audit.yaml:26-31` ; **exigence** WF-ADM-0190 : « Chaque inscription
  mène au projet concerné lorsque l'utilisateur peut le consulter (WF-ADM-0110), et le nomme par son
  libellé et son code sinon » ; Vérif : « Après une restauration, une inscription qui cite un projet
  créé après la sauvegarde s'affiche avec le libellé et le code de ce projet, sans mener à lui » ;
  **ce que dit le contrat** : « l'inscription ne mène qu'à un projet qu'il peut ouvrir (WF-ADM-0110) …
  un projet qui n'existe plus … se nomme de même, sans mener à lui » — sans aucun champ qui le porte.
- **Constat.** Le même concept est porté ailleurs par un booléen évalué par le serveur :
  `PortfolioProjectRow.can_open`, les risques les plus lourds, `PilotHealth`, la matrice des risques
  (DECISIONS l. 1318-1329, #389 : « Écarté : laisser le front le déduire des permissions de la
  session, qui ne connaît pas les contributeurs » ; l. 7332). Le journal, lu par un auditeur qui n'est
  contributeur d'aucun projet et ne lit pas tous les projets, est le cas le plus net ; or l'écran
  d'aujourd'hui relit **toutes les pages** de `listProjects` à chaque consultation pour construire la
  liste des projets ouvrables (`frontend/src/app/admin/audit-log/page.tsx:126`,
  `audit-columns.tsx:98`), ce qui ne dit rien non plus d'un projet disparu après restauration (il n'est
  pas dans la liste : « sans mener à lui » est alors juste par accident). Incohérence entre familles
  sur un même concept, et un attribut que la spec demande que le contrat ne porte pas : à ajouter avant
  le gel, un champ exigé ne s'ajoutant pas après.
- **Proposition.**
  ```yaml
  AuditProject:
    required: [project_id, code, label, can_open]
    properties:
      can_open:
        type: boolean
        description: >-
          Vrai si l'appelant peut consulter le projet aujourd'hui (WF-ADM-0110) : la permission de
          consulter et la qualité de contributeur, ou « consulter tous les projets » ; faux sinon, et
          pour un projet qui n'existe plus (WF-ADM-0190). Dans les facettes, évalué de même.
  ```
  Même question pour l'objet (`AuditObject`), dont « le lien vers l'objet ne vaut que pour qui peut le
  consulter » : le front le déduit aujourd'hui des permissions de la session, ce qui est juste tant
  que l'objet existe.
- **DECISIONS.md** : EP-02/L42 (l. 2741-2742) : « le lien vers l'objet ne vaut que pour qui peut le
  consulter (WF-ADM-0110) » — la règle, pas le moyen ; #389 (l. 1318) pour le portefeuille.

#### B-04 — La planification : fréquence et heure facultatives, jour facultatif et nullable

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/platform.yaml:228-267`
  (`BackupSchedule`, `required: [is_enabled, retained_count, lock_version]`, l. 230 ; `frequency`
  l. 234, `at_time` l. 237, `weekday` l. 244-251) ; `docs/api/paths/platform.yaml:347-358` (422 de
  `setBackupSchedule`) ; **exigence** WF-ADM-0170 : « Les sauvegardes sont planifiées à une fréquence et
  une heure choisies par un utilisateur habilité » ; **ce que dit le contrat** : `frequency` et
  `at_time` ne sont pas exigés ; `weekday` est `anyOf [integer 1..7, null]` mais pas exigé, « nul pour
  une sauvegarde quotidienne ».
- **Constat.** Les trois exemples de lecture (`backup_schedule`, `_weekly`, `_disabled`) et l'exemple
  d'écriture (`_set`) portent tous `frequency`, `at_time` et `weekday` (nul pour les quotidiennes) ;
  le schéma admet pourtant un `PUT` sans heure ni fréquence, qu'un service devra refuser par un 422
  que l'opération ne déclare pas (`VALUE_REQUIRED` sur `/frequency`, `/at_time`), et un client engendré
  (TypeScript, Pydantic) les tient pour optionnels à la lecture. La convention du contrat pour un
  champ qui ne s'applique pas toujours est « exigé, nul quand il ne s'applique pas » (DECISIONS
  l. 3077, `AuditObject.revision`, `AuditEvent.project`) : `weekday` devrait l'être. Le 422 ne dit pas
  non plus le refus d'une hebdomadaire sans jour ni d'une quotidienne avec un jour. Rendre un champ
  exigé après le gel rompt les écritures des clients : c'est maintenant.
- **Proposition.**
  ```yaml
  BackupSchedule:
    required: [is_enabled, frequency, at_time, weekday, retained_count, lock_version]
  ```
  et dans le 422 de `setBackupSchedule` : « un jour absent d'une planification hebdomadaire
  (`/weekday`, `VALUE_REQUIRED`), un jour donné à une quotidienne (`/weekday`, `VALIDATION_FAILED`
  … ) », avec un exemple.
- **DECISIONS.md** : l. 817-826 (heure en UTC, jour ISO 8601) et l. 4423-4433 (bornes de la rétention
  et du jour, « relevé, non traité ici ») : rien sur le caractère exigé.

#### B-05 — Ce que la rétention compte : les planifiées, ou toutes les sauvegardes non marquées ?

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/platform.yaml:256-259`
  (`BackupSchedule.retained_count` : « Le nombre de sauvegardes planifiées gardées sur la
  plateforme ») ; contre `docs/api/paths/platform.yaml:49-54` (`is_retained` : « celles que la rotation
  supprimera à leur tour (faux) »), `schemas/platform.yaml:135` (`BackupCommand` : « Aucune ne la
  supprime : seule la rotation le fait »), `fixtures/api/backup_released.json` (« La sauvegarde manuelle
  du 30 janvier, qui n'est plus marquée à conserver : la rotation la supprimera à son tour ») ;
  **exigence** WF-ADM-0170 : « Le nombre de sauvegardes conservées sur la plateforme est paramétrable ;
  au-delà, les plus anciennes sont supprimées, à l'exception de celles que l'utilisateur a marquées à
  conserver » ; Vérif : « Avec une rétention de sept, la huitième supprime la plus ancienne non marquée. »
- **Constat.** La spécification ne distingue pas l'origine : toute sauvegarde non marquée est soumise à
  la rotation et comptée. Le contrat dit « planifiées » dans `retained_count` et « la rotation la
  supprimera à son tour » d'une manuelle : si la manuelle n'est pas comptée, quand est-elle supprimée ?
  Si elle l'est, le témoin (sept planifiées + une manuelle démarquée par `backup_released`, rétention
  sept) perd aussitôt la manuelle du 30 janvier, ce que l'exemple ne dit pas. Un implémenteur du
  service choisira l'une des deux lectures ; le front dit déjà à l'utilisateur l'autre. Ambiguïté sur
  une règle de suppression : à lever avant le gel, le mot « planifiées » d'une description étant sans
  coût à changer maintenant, et le comportement du service très coûteux ensuite.
- **Proposition.** Suivre la spec : « Le nombre de sauvegardes non marquées, manuelles ou planifiées,
  gardées sur la plateforme ; au-delà, la plus ancienne non marquée est supprimée (WF-ADM-0170) » ; ou,
  si l'auteur veut que la rotation ne touche que les planifiées, le décider dans DECISIONS.md et dire
  d'une manuelle démarquée ce qui l'attend (jamais supprimée ? supprimée par quoi ?).
- **DECISIONS.md** : aucune décision (grep `rotation`, `retained_count`, « planifiées gardées ») ;
  EP-02/L42 (l. 2640-2649) ne parle que de la rétention de la copie externe.

#### B-06 — `audit_event` quand la table 10 dit `audit_entry`

- **gravité** majeur (catégorie 1 du brief : un nom qui s'écarte de la table du §4.4.1 ; voir la
  nuance) ; **emplacement** `docs/api/paths/audit.yaml:1-3` (`/audit-events`, `listAuditEvents`),
  `:155-157` (`/audit-events/facets`, `listAuditFacets`), `docs/api/components/schemas/audit.yaml:128,143`
  (`AuditEvent`, `audit_event_id`) ; **exigence** §4.4.1, table 10 : « Inscription au journal d'audit
  (WF-SEC-0030) | audit_entry | plateforme », « le tableau ci-dessous est … la traduction de référence
  de chaque objet » ; README : « Les noms du tableau de correspondance du §4.4.1 » ; **ce que dit le
  contrat** : `AuditEvent`, `audit_event_id`, `/audit-events`, `AuditAction`, `AuditObject`…
- **Constat.** Le contrat parle partout d'« inscription » en français et d'`event` en anglais ; la
  table de référence dit `audit_entry`. Un chemin et un identifiant ne se renomment plus après le gel.
  Nuance honnête : la même table dit `user_account` là où le contrat dit `User`/`user_id`, sans que
  personne ne l'ait relevé — la table n'est donc pas appliquée à la lettre pour les objets de la
  plateforme, et une entrée de DECISIONS.md qui l'assume (« `event`, le mot des journaux structurés,
  WF-OBS-0020 ») clôt le constat sans toucher au contrat. Ce qui ne peut pas rester, c'est l'absence
  de décision sur un nom que la table fixe.
- **Proposition.** Soit renommer (`/audit-entries`, `listAuditEntries`, `AuditEntry`, `audit_entry_id`,
  et le client engendré), soit écrire la décision. À trancher par l'auteur.
- **DECISIONS.md** : aucune (grep `audit_entry`, `audit_event`) ; EP-02/L42 (l. 2686-2700) nomme
  `AuditEvent` sans dire pourquoi pas `audit_entry`.

#### B-07 — Une restauration acceptée pendant la sauvegarde qu'une autre requête dit en cours

- **gravité** mineur ; **emplacement** `fixtures/api/task_restore_queued.json` (« confirmée aujourd'hui
  à 14 h 04 min 30 s et mise en file »), `fixtures/api/backup_pending.json` et
  `backups_during_backup.json` (sauvegarde « mise en file à 14 h 04 … prise à 14 h 04 min 50 s »),
  `fixtures/api/restore_during_backup_refused.json` (« confirmée à 14 h 04 min 20 s, pendant que la
  sauvegarde manuelle mise en file à 14 h 04 s'exécute … refusée, `no_backup_running` manquante »),
  `fixtures/api/backup_start_during_restore_refused.json` et `backup_retain_refused.json` (14 h 04 min
  40 s, pendant la restauration de 14 h 04 min 30 s) ; **exigence** WF-ADM-0150, WF-ADM-0160 ; **ce que
  dit le contrat** : `no_backup_running` « manque, pendant qu'une sauvegarde s'exécute — de sa mise en
  file à la production du fichier » (`schemas/projects.yaml:223-225`, `BackupCommand` l. 144) ;
  `startBackup` : « une sauvegarde prise pendant une restauration ne serait d'aucun état cohérent »
  (`paths/platform.yaml:158-160`).
- **Constat.** Lus comme la chronologie unique que DECISIONS.md revendique (« que l'univers témoin
  enchaîne (14 h 04 et 14 h 04 min 30 s) », l. 6145), les exemples se contredisent : à 14 h 04 min 20 s
  la restauration est refusée parce que la sauvegarde de 14 h 04 s'exécute ; à 14 h 04 min 30 s une
  restauration est acceptée alors que cette sauvegarde n'est prise qu'à 14 h 04 min 50 s ; et cette
  sauvegarde est prise pendant que la restauration s'exécute, ce que `startBackup` interdit. Chaque
  exemple est juste pour sa réponse (règle de L43c), mais un lecteur qui les enchaîne — le harnais, un
  implémenteur qui rejoue le témoin — y lit deux règles différentes.
- **Proposition.** Décaler la restauration et ses refus liés après la production du fichier
  (14 h 05 min 30 s, 14 h 05 min 40 s…), ou avancer `backup_pending.taken_at` avant 14 h 04 min 20 s ;
  mettre les résumés d'accord.
- **DECISIONS.md** : EP-02/L43c (l. 3871-3879 : « Chacun ne vaut que pour la réponse de son
  écriture ») et « Reprise de `main` après EP-03 » (l. 6145) — la seconde affirme l'enchaînement que
  les horodatages ne tiennent pas.

#### B-08 — `SystemStatus` : quatre « dernières opérations », une seule exigée

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/platform.yaml:5`
  (`required: [version, components, storage, last_backup_copy, alerts]`) et l. 15-33 ; **exigence**
  WF-ADM-0130 : l'écran d'état présente « la date et le résultat de la dernière lecture des comptes … ;
  la date et le résultat de la dernière sauvegarde ; la date et le résultat du dernier test de
  restauration » ; **ce que dit le contrat** : `last_identity_sync`, `last_backup`, `last_restore_test`
  sont `anyOf [OperationOutcome, null]` mais non exigés ; `last_backup_copy`, même forme, exigé.
- **Constat.** Les quatre champs sont du même régime (« nulle tant qu'aucune n'a eu lieu ») ; les quatre
  exemples `system_status*` les portent tous. Un client engendré tient trois d'entre eux pour
  optionnels, le quatrième pour exigé : incohérence sans raison, corrigible sans rompre (un champ
  toujours présent qui devient exigé).
- **Proposition.** `required: [version, components, storage, last_identity_sync, last_backup,
  last_backup_copy, last_restore_test, alerts]`.
- **DECISIONS.md** : EP-02/L42 (l. 2663-2667) ajoute `last_backup_copy` ; rien sur le caractère exigé
  des trois autres.

#### B-09 — Deux refus de `RestoreRequest` que l'opération ne décrit pas

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/platform.yaml:399-431`
  (`RestoreRequest` : `oneOf` sur `backup_id` / `external_backup_upload_id` ; `confirmed: { const:
  true }`), `docs/api/paths/platform.yaml:509-519` (400) et 550-561 (422) ; **exigence** WF-ADM-0160 :
  « n'est appliquée qu'après une confirmation qui énonce la date de la sauvegarde et le caractère
  irréversible de l'opération » ; **ce que dit le contrat** : le 400 `CONFIRMATION_REQUIRED` n'est
  décrit que pour « une confirmation qui ne nomme pas la date » ; `confirmed` faux ou absent relève du
  schéma, donc d'un 422 `VALIDATION_FAILED` sur `/confirmed` que le texte ne dit pas ; une requête qui
  désigne les deux sauvegardes, ou aucune, viole le `oneOf` sans refus décrit.
- **Constat.** Pour la même garde, `ProjectExit.confirmed` dit « Faux ou absent, la sortie est
  refusée » ; ici le front, qui envoie `confirmed: true` par construction, ne se trompera pas, mais un
  service l'implémentera en 400 ou en 422 selon le lecteur. Clarté, sans rupture.
- **Proposition.** Dans le 400 : « `confirmed` absent ou faux, ou une date qui n'est pas celle de la
  sauvegarde désignée : `CONFIRMATION_REQUIRED` » (la confirmation est une seule chose) ; dans le 422 :
  « deux sauvegardes désignées, ou aucune : `VALIDATION_FAILED`, `fields` désignant `/backup_id` et
  `/external_backup_upload_id` par `VALUE_REQUIRED` ou `FIELD_CONFLICT`… ».
- **DECISIONS.md** : EP-03/US-0440/L2 (l. 5929-5934) : le 400 pour la date, « Écarté : un 422 par
  champ sur `acknowledged_backup_taken_at` » ; rien sur `confirmed` ni sur le `oneOf`.

#### B-10 — Deux phrases d'`AuditObject` et d'`AuditEvent` à ajuster

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/audit.yaml:83-84`
  (`AuditObject.label` : « nul pour une sauvegarde, qui n'en a pas : sa date est celle de
  l'inscription ») et l. 164 (`AuditEvent.project` : « nul pour un objet de la plateforme — compte,
  rôle, sauvegarde ») ; **exigence** WF-SEC-0030, WF-ADM-0160 ; **ce que dit le contrat** :
  `AuditEvent.occurred_at` (l. 147-150) : « pour une action confiée au worker — … restauration —, celui
  où la tâche a abouti ; pour une sauvegarde, sa date ».
- **Constat.** Pour une inscription `restore` dont l'objet est une sauvegarde (`backup`), le libellé est
  nul et la date de l'inscription est celle de la restauration, non celle de la sauvegarde : la phrase
  « sa date est celle de l'inscription » n'est vraie que pour l'action `backup` (voir B-02 (b)). Et le
  dépôt (`external_backup_upload`) manque à la liste des objets sans projet.
- **Proposition.** « nul pour une sauvegarde, qui n'en a pas : pour l'action `backup`, sa date est celle
  de l'inscription ; pour `restore`, … [`params.backup_taken_at`, B-02] » ; « compte, rôle, sauvegarde,
  dépôt ».
- **DECISIONS.md** : EP-02/L42 (l. 2708-2717) sur l'objet d'une restauration ; rien sur ces phrases.

#### B-11 — `getBackup` et `getBackupSchedule` ne nomment pas leur permission

- **gravité** mineur ; **emplacement** `docs/api/paths/platform.yaml:173-175` (`getBackup`) et
  `:302-305` (`getBackupSchedule`) ; **exigence** WF-ADM-0100 ; **ce que dit le contrat** : `listBackups`
  (l. 14-15), `listExternalBackupLocations` (l. 381), `startBackup`, `retainBackup`, `downloadBackup`,
  `setBackupSchedule`, `testExternalBackupLocation`, `startRestore` nomment chacun leur permission ;
  ces deux lectures non.
- **Constat.** Les deux déclarent le 404 (lecture refusée), donc `backups.read` est implicite ; une
  description, pour la cohérence de la famille et du client.
- **Proposition.** Ajouter « Lisible sous la permission de consulter les sauvegardes (`backups.read`,
  WF-ADM-0100) » aux deux.
- **DECISIONS.md** : aucune.

### Ce qui est juste

- **Énumérations.** `AuditAction` couvre chaque action de WF-SEC-0030 (avec `project_create` et
  `revision_abandon` qu'US-0640/L6 ajoute), dans son ordre, et chaque opération du contrat qui se dit
  inscrite (`markRevision`, `designateReferenceRevision`, `mergeCostStructure`, `declareRiskOccurrence`,
  `exitProject`, `setActualCostTrackedScope`, `applyImport`, `createUser`/`updateUser`/
  `setUserActivation`/`anonymizeUser`/`setUserAccessRoles`/`createPasswordSetupLink`, les trois des
  rôles, `startBackup`, `startRestore`) a son action ; `user_reactivate` et `password_link_create`,
  au-delà de la liste de la spec, sont tranchés en EP-02/L42 (l. 2726-2729) et ne la contredisent pas.
  `AuditObjectKind` nomme l'objet de chacune ; `deleteSubproject`, `deleteRisk`, `deleteAccessRole`
  hors `access_role_delete`, les activations du référentiel ne sont pas dans la liste de WF-SEC-0030 et
  n'ont pas à y être. `CommandCondition` porte `backup_verified`, `no_backup_running`,
  `no_restore_running` ; `ErrorCode` porte tous les codes cités (`CONFIRMATION_REQUIRED`,
  `BACKUP_FROM_NEWER_VERSION`, `TASK_INTERRUPTED_BY_RESTORE`, `UNKNOWN_EXTERNAL_BACKUP_LOCATION`,
  `PATH_INVALID`, `UPLOAD_PURPOSE_MISMATCH`, `COMPONENT_UNAVAILABLE`) ; `BackgroundTaskRef.kind` porte
  `backup` et `restore` ; `PermissionCode` porte `backups.read`, `backups.write`, `audit_log.read`,
  `platform_restore`.
- **Conventions.** `from`/`to` (fin exclue, 422 `/query/to` par `VALUE_OUT_OF_RANGE`, `params.minimum`)
  sur les deux listes ; `size_bytes_min`/`_max` ; listes `explode: false` (`origins`, `verifications`,
  `actions`) ; tri sur chaque colonne avec départage par l'ordre sans tri puis l'identifiant ; 401 et
  503 sur toute opération ; 400 et 422 sur toute opération à corps ; 412 sur `setBackupSchedule`
  (`lock_version`) ; 409 `STATE_FORBIDS_OPERATION` + `params.missing_condition` partout, cohérent avec
  `BackupCommand` et `CommandCondition` ; 404 pour la lecture refusée ; tâche de fond pour la sauvegarde
  et la restauration ; aucune phrase localisée (libellés gardés, codes).
- **Exemples.** Chaque refus déclaré a son exemple (listBackups 422 ×2 ; startBackup 409 ×2 ;
  retainBackup 409 ; downloadBackup 409 ; setBackupSchedule 422 ×5 ; testExternalBackupLocation 422 ;
  startRestore 400 ×2, 404, 409 ×3, 422 ; listAuditEvents 422), chacun conforme à sa description
  (codes, pointeurs, `params`). Horodatages cohérents : sauvegardes à `01:00Z` ⇔ `at_time` `01:00` ;
  sept planifiées (28 mai–3 juin) ⇔ `retained_count` 7 ; copie de Lyon du 20 mai parmi 30 copies ;
  dépôt expirant à 24 h ; `system_status_backup_failed` (stockage tombé à 0 h 52, sauvegarde d'1 h
  échouée, dernière copie la veille à 1 h 14) ; `backups_unverified` et `backup_pending` cohérents avec
  `BackupCommand`. Journal : les 36 inscriptions du témoin datées de leurs sources (`marked_at`,
  `taken_at`, audits des comptes et rôles), `occurred_at` des sauvegardes = `taken_at`, les trois
  inscriptions de la fusion sous une corrélation, `params` des comptes et rôles conformes
  (`administration`), anonymisation cohérente entre `audit_events_anonymized_*`, `audit_facets_anonymized`
  et `users` (compte …303), tris par points de code conformes (`by_actor`, `by_object_label`),
  recherche insensible à la casse et aux accents (`search`), facettes sans la plateforme.
- **Spec → contrat.** WF-ADM-0150 (liste datée, taille, vérification, copie hors plateforme),
  WF-ADM-0160 (deux bases, confirmation par la date, journal conservé et réinscrit, tâches en échec,
  inscription de la restauration, 503 maintenance et sonde), WF-ADM-0170 (fréquence, rétention,
  marquage, copie externe, alertes), WF-ADM-0190 (cinq filtres, tri récent d'abord, permission seule,
  lecture seule), WF-SEC-0030 (action, date, auteur, objet, projet ; libellés gardés ; anonymisation
  seule modification), WF-EXP-0050 (rétention externe ≥ plateforme, `last_backup_copy`), WF-EXP-0060
  (`last_restore_test`), WF-DAT-0120 (dépôt d'un jour, gardé jusqu'à la fin de la tâche) : portés.

### Doutes

- **La chronologie d'une sortie du cycle de vie.** WF-CYC-0090 : la confirmation d'une sortie, quand le
  projet porte une révision en cours, « demande de la marquer, avec un nom de version, ou de
  l'abandonner ; la sortie n'est appliquée qu'avec ce choix, dans la même opération ». `ProjectExit`
  (`schemas/projects.yaml:557-574`) n'a ni `version_name` ni choix d'abandon — famille projets, pas la
  mienne —, mais pour le journal cela signifie que `project_exit` produit `revision_mark` ou
  `revision_abandon` sous la même corrélation, ce que la description d'`AuditEvent` (« Une action qui
  en produit d'autres les inscrit toutes ») couvre sans le nommer. À signaler au relecteur des projets.
- **Les tâches que la restauration garde.** `startRestore` (l. 487-491) : les tâches de la
  restauration et des sauvegardes « reprennent l'état gardé (#987) » quand la spec dit que « les
  traitements en attente ou en cours dans les bases restaurées sont terminés en échec ». DECISIONS
  l. 5938-5945 l'assume (un succès présenté comme un échec contredirait WF-EXP-0040) et la liste des
  sauvegardes survit par la spec même ; je ne tranche pas si c'est un écart à la lettre de WF-ADM-0160.
- **Le dépôt d'une sauvegarde et sa vérification.** L42m (l. 4386-4388) : « Que la vérification d'une
  sauvegarde déposée soit énoncée, comme celle d'une sauvegarde de la liste, n'est pas tranché ici » ;
  L42o puis EP-14 la font faire par la restauration même, avant la maintenance (`startRestore`,
  l. 463-469). Le dépôt n'a donc pas de `verification` lisible avant qu'on tente la restauration :
  cohérent, mais l'écran ne peut dire d'avance qu'un dépôt est restaurable.
- **`Backup.scope` à une seule valeur** (`enum: [database]`, l. 215) : existait avant #705 et n'est
  jamais filtré ; sans conséquence, non signalé.
- **Compte d'installation.** Dans le journal du témoin, Camille Martin (créée par la plateforme à
  l'installation, 2025-09-01 09:00) ne reçoit aucun `user_access_roles_set` pour son rôle
  « Administrateur » créé au même instant (`mockaudit._given` n'inscrit que les rôles créés *après* le
  compte) ; la règle « À la création d'un compte, ses premiers rôles » (`AuditParams.access_roles_granted`)
  voudrait une inscription jointe à son `user_create`. Fixture engendrée, mineur, non compté.

## Annexe C — Référentiel


**Lu** : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/reference.yaml` (1 894 lignes, en entier) ; `docs/api/components/schemas/reference.yaml` (1 074 lignes, en entier) ; `common.yaml` (types, `Problem`, `ProblemParams`, `ErrorCode`), `parameters.yaml` (`Limit`, `Offset`, `Search`, `IncludeInactive`, `IsActive`, identifiants de chemin, `RateYear`), `responses.yaml`, `CommandCondition` (`projects.yaml`), `PermissionCode` (`access.yaml`), `EmployedReference` (`revisions.yaml`) ; spécification §3.2.2 (642–682), §3.4.4 en entier (1608–1900), WF-CYC-0120 (892), WF-EXP-0020 (4157), WF-ADM-0100 (1334), §4.4.1 (3847–3980), §4.6.2 (4259–4328) ; `DECISIONS.md` : sections US-0250/L1, EP-02/L42a, L43a, L43b, L42g, #577, #578, EP-14/L42h, L42m, L42j, L42p, L42r, L42s, EP-03 #837, EP-15/US-0570, EP-16 (US-0600, US-0620) et les greps ciblés ; `INVENTORY.md` (lignes du référentiel) ; `docs/roadmap/EP-16-maquette-durcissement.md` (« Constats reçus », « Les modifications du contrat ») ; **101 fixtures ouvertes** (toutes celles que `reference.yaml` référence, dont les trois `volume/cost_categories*`, les quatre `volume/hourly_rate*`, les sept `actual_cost_mapping*`, les quatre `duration_units*`), avec un contrôle programmé de cohérence (niveaux et libellés de parents de l'arbre, rattachements des rôles, unicité du calendrier par défaut, 150 lignes de grille = 150 catégories de main-d'œuvre, `years` croissantes et `cells` alignées, codes comptables uniques, bornes de `hourly_rate_grid_bounded`) ; docstrings de `wftools.mockreference`, `mockcategories`, `mockcalendar`.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| C-01 | majeur | `docs/api/paths/reference.yaml:205-206` (`listOrgNodes`), `:874-875` (`listCalendars`), `:1187-1188` (`listCostTypes`) | Trois listes prennent `include_inactive` et `is_active` mais ne déclarent pas le 403 que le paramètre partagé `IsActive` et les trois autres listes du référentiel promettent sans la permission de modification | WF-REF-0150, WF-ADM-0100 |
| C-02 | majeur | `docs/api/paths/reference.yaml:31-50` (`getReferenceSettings`), `components/schemas/reference.yaml:742-765` (`ReferenceSettings.currency_code`), `:705` (`Installation`) | La devise n'est lisible que par `getReferenceSettings`, gardé par une permission de consultation (404) que l'opération ne nomme pas ; aucune lecture ouverte à qui consulte un projet ne la porte, quand elle doit « apparaître partout où un montant est affiché » | WF-REF-0140 |
| C-03 | majeur | `docs/api/components/schemas/reference.yaml:620` (`CostCategoryWrite.accounting_code`), et en lecture `:86`, `:445`, `:563`, `:590` | Le code comptable reçu n'a pas `pattern: '\S'` : un code fait de blancs passe le modèle engendré, contre la convention « Aucun libellé fait seulement de blancs » ; les codes lus des nœuds, natures et catégories ne l'ont pas non plus, celui des rôles et de la grille oui | WF-REF-0040, WF-ARC-0110 |
| C-04 | mineur | `docs/api/components/schemas/reference.yaml:816-823` (`RiskMatrixSettings`) | « Les bornes de gravité sont exprimées en pourcentage du budget de référence » : la spécification révisée dit l'assiette — budget de référence ou, avant lui, total hors provisions du devis courant | WF-REF-0160 |
| C-05 | mineur | `docs/api/paths/reference.yaml:1708` (`listHourlyRates`) | « Le taux de l'année en cours est exigé au chiffrage (WF-REF-0060) » : c'est le taux de l'année de référence, et l'exigence qui le dit est WF-DEV-0010 ; WF-REF-0060 porte l'ajout d'une colonne | WF-REF-0060, WF-DEV-0010 |
| C-06 | mineur | `docs/api/components/schemas/reference.yaml:742` (`ReferenceSettings`), `:882` (`DurationUnits`) vs `:1006` (`ActualCostMapping.audit`) | Deux objets uniques modifiables de la même famille sans `audit`, le troisième avec : « Modifié le / par » ne se lit pas pour les paramètres communs ni les unités de durée | WF-DAT-0070, §4.4.1 |
| C-07 | mineur | `docs/api/paths/reference.yaml:206`, `:1061`, `:1271-1304`, `:1350`, `:1602`, `:1853` | Six refus déclarés sans exemple, dont un 409 de modification qui ne cite pas l'exemple de code pris que la règle des exemples exige | WF-REF-0030, WF-REF-0070, WF-REF-0120, WF-REF-0190 |
| C-08 | mineur | `docs/api/components/schemas/reference.yaml:384-386` (`CostTypeKind`) vs `common.yaml` (`LABOUR_CATEGORY_REQUIRED`) | Deux graphies du même mot dans les identifiants figés : `labor`/`non_labor` et `LABOUR_…` ; le seul moment pour unifier est avant le gel | WF-REF-0030 |
| C-09 | mineur | `docs/api/components/schemas/reference.yaml:243-268` (`ResourceRoleUpdate`), `paths/reference.yaml:600-676` (`updateResourceRole`) | Le Vérif veut la modification du nœud d'un rôle « refusée » ; le contrat ne porte pas le champ et ne dit pas ce qu'il advient d'un `org_node_id` envoyé (ignoré ou refusé, et par quel code) | WF-REF-0090 |

### C-01 — Le 403 d'`include_inactive` manque à trois listes

- **gravité** majeur ; **emplacement** `docs/api/paths/reference.yaml:205-206` (`listOrgNodes` : `'404'`, `'422'`, pas de `'403'`), `:874-875` (`listCalendars`), `:1187-1188` (`listCostTypes`) ; à comparer à `:521` (`listResourceRoles`), `:1421` (`listCostCategories`), `:1686` (`getHourlyRateGrid`), qui déclarent le `403` ; **exigence** WF-REF-0150 (« Les listes du référentiel ne présentent que les objets actifs, et permettent d'afficher également les objets désactivés ») lue avec WF-ADM-0100 ; **ce que dit le contrat** : `parameters.yaml:44-55`, `IsActive` : « faux, les seuls désactivés, lus sous la permission qu'`include_inactive` exige […] `include_inactive` reste refusé sans sa permission, même quand `is_active` le rend sans effet » ; `listResourceRoles` : « sans elle, l'un et l'autre sont refusés par 403 » ; `listCostCategories` : « `include_inactive` et `is_active` faux sont refusés par 403 ».
- **Constat.** La règle est une : lire les désactivés exige la permission de modification de la fonction, et sans elle la requête est refusée par 403. Les trois listes de ce constat prennent `IncludeInactive` et `IsActive` (lignes 161, 174 ; 836-840 ; 1148-1152), leurs exemples `*_reader` sont décrits comme la lecture d'« une session qui ne peut pas modifier sa fonction : les objets actifs seuls, puisqu'elle ne peut pas demander `include_inactive` » (DECISIONS 2915), mais aucune ne déclare le 403, et leurs descriptions ne disent pas le refus. Le lint `rule/session-operation-declares-401` ne le voit pas ; le client engendré ne connaît pas ce statut pour ces trois opérations, et le service engendré n'a pas de réponse à produire : un implémenteur hésitera entre 403, 404 et une liste vide, et les trois listes divergeraient des trois autres pour le même concept. Après le gel, ajouter une réponse d'erreur est une modification du contrat.
- **Proposition.** Sur les trois opérations, à la place qu'occupe le `403` ailleurs :
  ```yaml
      '403': { $ref: ../components/responses.yaml#/Forbidden }
  ```
  et une phrase dans chaque description, sur le modèle de `listResourceRoles` : « Les nœuds/calendriers/natures désactivés (`include_inactive`, `is_active` faux) restent sous la permission des paramètres de ressources/de coûts (WF-ADM-0100) : sans elle, l'un et l'autre sont refusés par 403. » À trancher au passage : qui lit l'arbre, les calendriers et les natures actifs — toute session, comme les rôles et les catégories (le libellé d'un nœud sert à l'écran du plan de charge, celui d'un calendrier au rôle) — ou la seule permission de consultation de la fonction, ce que le 404 déclaré suggère sans le dire.
- **DECISIONS.md** : EP-02/L42a (« Chaque colonne des tables du référentiel se filtre », 2810-2821 : « `include_inactive` reste refusé sans sa permission ») et « Une lecture sans droit d'écriture […] ont leurs exemples » (2913-2918) posent la règle pour les cinq listes ; aucune décision n'exempte ces trois opérations du 403.

### C-02 — La devise ne se lit que sous une permission du référentiel

- **gravité** majeur ; **emplacement** `docs/api/paths/reference.yaml:31-50` (`getReferenceSettings`, `'404'` à la ligne 49), `docs/api/components/schemas/reference.yaml:742-765` (`ReferenceSettings.currency_code`, « Devise unique, choisie à l'installation et non modifiable ») et `:705-735` (`Installation`, lisible sans session, sans devise) ; **exigence** WF-REF-0140 : « Tous les montants de l'installation sont exprimés dans une devise unique […] Vérif : La devise apparaît partout où un montant est affiché ou exporté » ; **ce que dit le contrat** : `getReferenceSettings` « Les réglages que tout projet hérite de l'installation », avec un `404` « Objet inexistant, ou invisible faute de la permission de consultation », sans nommer la permission ; `grep currency_code docs/api` ne trouve que `reference.yaml`.
- **Constat.** Un chiffreur ou un lecteur de projet qui n'a aucune des permissions du référentiel (`cost_settings.read`, `risk_settings.read`, `indicator_settings.read`, `PermissionCode`) voit des montants sur toutes les grilles et les indicateurs, mais aucune opération qu'il peut appeler ne lui donne la devise : le front, aujourd'hui, appelle `formatMoney(amount, locale)` sans devise hors de l'écran des coûts du référentiel (`frontend/src/components/indicators/project-indicators.tsx:59`, `costs/cost-line-scope.tsx:90`), et ne la lit que dans `app/reference/costs/page.tsx:297`. Le Vérif de WF-REF-0140 n'est donc pas atteignable par le contrat tel qu'il est. Deuxième ambiguïté, du même endroit : trois permissions de consultation couvrent un seul objet lu, et `getReferenceSettings` ne dit pas laquelle ouvre la lecture (l'une, toutes, n'importe laquelle), alors que `getActualCostMapping` nomme la sienne (`cost_settings.read`, ligne 1807) et que l'écriture nomme les trois fonctions champ par champ. Un implémenteur du service choisira seul ; un client ne saura pas quand attendre le 404.
- **Proposition.** Soit porter la devise là où toute session lit : `Installation.currency_code` (le lot US-0600 a écarté le nom de l'entreprise dans `Installation` « quand le nom ne sert qu'aux fichiers exportés » — la raison ne vaut pas pour la devise, qui sert à chaque montant) ; soit déclarer `getReferenceSettings` lisible par toute session (retirer le `404`, le dire dans la description : « Lisible par toute session : la devise, la matrice et les seuils qualifient ce que tout lecteur de projet voit »). Dans les deux cas, nommer la permission de la lecture quand elle existe :
  ```yaml
  description: >-
    […] Lu par toute session ouverte : la devise (WF-REF-0140) et la langue par défaut servent
    à tout écran ; les bornes, les seuils et le délai qualifient ce que tout lecteur de projet
    voit (WF-REF-0160 à WF-REF-0180). Seule l'écriture relève des permissions de ses fonctions.
  ```
- **DECISIONS.md** : EP-14/L42h (4021-4035) règle la permission de l'écriture par champ, rien de la lecture ; EP-16/US-0600 (7641-7676) : « Écarté : un réglage dans `Installation`, que `getInstallation` rend sans session, quand le nom ne sert qu'aux fichiers exportés » — l'argument porte sur le nom, pas sur la devise. Aucune décision sur la permission qui ouvre `getReferenceSettings` ni sur la lecture de la devise hors du référentiel.

### C-03 — Le code comptable reçu accepte un texte fait de blancs

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/reference.yaml:620` : `accounting_code: { type: string, minLength: 1, maxLength: 20 }` (`CostCategoryWrite`, repris par `CostCategoryUpdate`) ; en lecture, `:86-93` (`OrgNode.code`), `:445-451` (`CostType.code`), `:563-569` (`CostCategoryImage.code`), `:590-598` (`CostCategoryImage.accounting_code`) sans motif, alors que `:188-196` (`ResourceRoleImage.code`) et `:683` (`HourlyRateRow.code`) le portent ; **exigence** WF-REF-0040 (« porte un code comptable unique et un libellé ») et la convention du README : « Un libellé, un nom ou un code reçu porte au moins un caractère qui n'est pas un blanc (`pattern: '\S'`) : fait seulement de blancs, il est refusé par 422 `VALIDATION_FAILED` sur son champ » (WF-ARC-0110) ; **ce que dit le contrat** : le 422 de `createCostCategory` (ligne 1461) ne dit pour `/accounting_code` que vide (`VALUE_REQUIRED`) ou trop long (`VALUE_TOO_LONG`).
- **Constat.** Le service et le client sont engendrés du contrat ; la décision #837 compte sur le motif pour que le service refuse « ␣␣␣ » : « le service, dont les modèles sont engendrés du contrat, le refuse par 422 ». Le code comptable est le seul champ reçu de la famille qui y échappe : une catégorie peut naître avec un code comptable « ␣ », unique en base et illisible en comptabilité, « ce par quoi la comptabilité nomme la dépense ». Côté lecture, l'absence du motif sur quatre codes et sa présence sur deux ne dit rien de faux, mais le même concept est typé différemment d'un schéma à l'autre.
- **Proposition.** Ligne 620 :
  ```yaml
      accounting_code: { type: string, minLength: 1, pattern: '\S', maxLength: 20 }
  ```
  et le même `pattern: '\S'` sur les quatre codes lus (86, 445, 563, 590), comme `ResourceRoleImage.code`. Ajouter au 422 de `createCostCategory`/`updateCostCategory` « fait seulement de blancs, par `VALIDATION_FAILED` au même pointeur », comme `ReferenceSettingsWrite.company_name` le dit.
- **DECISIONS.md** : EP-03 #837 (5766-5773) : « Les quarante-quatre libellés, noms et codes du contrat qui exigeaient un caractère exigent désormais un caractère qui n'est pas un blanc » ; EP-02/L42g (3459-3464) a fait du code comptable « une chaîne d'un à vingt caractères, comme le code » — avant #837, qui ne l'a pas rattrapé. Aucune décision ne l'exempte.

### C-04 — L'assiette des bornes de gravité est dite trop court

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/reference.yaml:816-823` (`RiskMatrixSettings`, description) ; **exigence** WF-REF-0160 : « trois bornes de gravité, exprimées en pourcentage de l'assiette du projet — son budget de référence ou, tant qu'il n'en a pas, le total hors provisions du devis de sa révision courante » ; **ce que dit le contrat** : « Les bornes de gravité sont exprimées en pourcentage du budget de référence. »
- **Constat.** La spécification a été révisée pour qu'un projet en chiffrage classe ses risques sur son devis courant (Vérif : « Sur un projet en chiffrage, un risque est classé d'après le total hors provisions de son devis courant »). La description du schéma, et les résumés de `reference_settings`, `reference_settings_matrix_updated` et `reference_settings_bounds_refused` (« du budget de référence »), gardent la rédaction antérieure. Un implémenteur du classement qui lirait le schéma plutôt que la spécification diviserait par zéro, ou ne classerait rien, avant la référence.
- **Proposition.** « Les bornes de gravité sont exprimées en pourcentage de l'assiette du projet : son budget de référence ou, tant qu'il n'en a pas, le total hors provisions du devis de sa révision courante (WF-REF-0160). » Les trois résumés de fixtures suivent.
- **DECISIONS.md** : aucune décision ; EP-14/L42h (4036-4049) nomme les bornes sans dire leur assiette.

### C-05 — `listHourlyRates` cite WF-REF-0060 pour une règle de WF-DEV-0010, et la dit faux

- **gravité** mineur ; **emplacement** `docs/api/paths/reference.yaml:1708` (`listHourlyRates`, description) ; **exigence** §3.4.4.1.2 : « le chiffrage n'emploie que celui de l'année de référence, et le taux d'inflation du projet se charge des années suivantes » ; WF-DEV-0010 (cité par `getMissingRates`, INVENTORY ligne 197) ; WF-REF-0060 : « ajouter à la grille des taux une colonne pour une année qui n'en a pas encore » ; **ce que dit le contrat** : « Au plus un taux par année (WF-REF-0050). Le taux de l'année en cours est exigé au chiffrage (WF-REF-0060). »
- **Constat.** Deux erreurs dans une phrase : « l'année en cours » là où la spécification dit l'année de référence du projet — la seule qui compte, un chiffrage créé en 2026 sur une référence 2025 n'exige pas le taux 2026 —, et une citation d'exigence qui ne porte pas ce qu'elle cite. C'est la seule description de la famille réduite à une ligne ; `INVENTORY.md` en déduit que l'opération réalise WF-REF-0060.
- **Proposition.** « Les taux d'une catégorie, au plus un par année (WF-REF-0050) : la liste creuse que `getHourlyRateGrid` présente en grille. Le chiffrage n'emploie que le taux de l'année de référence du projet (WF-DEV-0010, `getMissingRates`) ; une année s'ajoute par son premier taux (`setHourlyRate`, WF-REF-0060). »
- **DECISIONS.md** : aucune décision ; US-0250/L1 et EP-02/L29 (444-452) décrivent la grille et gardent `listHourlyRates` « pour une catégorie seule » sans en dire plus.

### C-06 — Deux objets uniques sans colonnes d'audit

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/reference.yaml:742-765` (`ReferenceSettings`, `required` sans `audit`), `:882-897` (`DurationUnits`), à comparer à `:964-1006` (`ActualCostMapping`, `audit` requis) ; **exigence** WF-DAT-0070 : « Toute table dont les lignes peuvent être modifiées porte la date de création et son auteur, la date de dernière modification et son auteur » ; §4.4.1, table 10 : `reference_setting`, régime référentiel, « ses paramètres se modifient » ; **ce que dit le contrat** : `ActualCostMapping` « lu et remplacé entier avec son compteur […] `lock_version` et `audit` » ; `ReferenceSettings` et `DurationUnits` portent `lock_version` seul.
- **Constat.** Trois objets uniques de l'installation, trois écritures versionnées, deux formes : la correspondance dit qui l'a réglée et quand (fixture : Camille Martin, le 3 avril 2026), les paramètres communs et les unités de durée ne le disent pas, quand une correction de borne ou de seuil change la zone de tous les projets (WF-REF-0130). Ajouter un champ requis à une réponse est compatible pour un client, mais c'est une modification du contrat après le gel, et la décision #936 a montré que les écrans finissent par demander « Modifié le / par ».
- **Proposition.** Ajouter `audit: { $ref: ../common.yaml#/Audit }` aux `required` et `properties` de `ReferenceSettings` et `DurationUnits`, les fixtures portant la plateforme à l'amorçage et Camille Martin aux écritures du jour, comme `actual_cost_mapping*`.
- **DECISIONS.md** : aucune décision pour ces deux objets ; EP-16/US-0620 (7738-7742) a donné l'audit à la correspondance « comme les unités de durée » pour la version 1 à l'amorçage — les unités n'ont pourtant pas d'`audit`.

### C-07 — Six refus déclarés sans exemple

- **gravité** mineur ; **emplacement** `docs/api/paths/reference.yaml:206-214` (`listOrgNodes` 422, bornes de profondeur), `:1061-1074` (`setDefaultCalendar` 422, `TASK_WITHOUT_WORKING_HOURS` à `resource_role_ids` vide), `:1271-1304` (`updateCostType` 409 : seul `kind_frozen`, pas de `code_taken`), `:1350-1357` (`setCostTypeActivation` 412), `:1602-1609` (`setCostCategoryActivation` 412), `:1853-1860` (`setActualCostMapping` 403) ; **exigences** WF-REF-0070, WF-REF-0120, WF-REF-0030, WF-REF-0010, WF-REF-0190 ; **ce que dit le contrat** : chaque réponse a sa description et son schéma, aucune `examples`.
- **Constat.** Le faux back sert les exemples du contrat ; un refus sans exemple ne se joue pas dans la maquette, et le front ne peut pas éprouver sa phrase. Le cas de `updateCostType` est en plus contraire à la règle que `test_mockcostsettings.py` tient (DECISIONS 5033-5035 : « tout exemple d'une valeur prise cité sous une création et une modification dit l'une et l'autre ») : `cost_type_code_taken` est cité sous `createCostType` seulement, alors que sa description du 409 dit le code pris à la modification. Les autres familles de la même règle (`org_node_code_taken`, `resource_role_code_taken`, `calendar_label_taken`) sont citées sous les deux.
- **Proposition.** Citer `cost_type_code_taken` sous le 409 d'`updateCostType` (et compléter son résumé, « à sa création comme à sa modification »). Écrire, aux corrélations de la seconde suite : `org_nodes_bounds_inverted` (`level_max` 2 sous `level_min` 3), `calendar_default_without_hours` (une variante contrefactuelle : un calendrier sans heure désigné par défaut, le projet témoin nommé, `resource_role_ids: []`), `cost_type_activation_stale`, `cost_category_activation_stale`, `actual_cost_mapping_permission_missing` (`cost_settings.write`).
- **DECISIONS.md** : EP-03 #799/#827 (5789) : « Le 412 et le 422 de chaque opération qui peut les rendre » — déclarés, non exemplifiés pour les deux activations ; US-0600 (7669-7671) a jugé qu'un 403 existant « montre déjà la forme du refus » pour `updateReferenceSettings` — l'argument peut valoir pour `setActualCostMapping`, à dire alors dans la description. Aucune décision pour les quatre autres.

### C-08 — `labor` et `LABOUR` dans les identifiants figés

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/reference.yaml:384-386` (`CostTypeKind: enum: [labor, non_labor, provision]`), `common.yaml` (`LABOUR_CATEGORY_REQUIRED`), `paths/reference.yaml:1794` (exemple `not_labour`, fixture `hourly_rate_non_labour_refused`), `portfolio.yaml:215` (`labor_by_org_node`) ; **exigence** WF-REF-0030 (« main-d'œuvre ») ; **ce que dit le contrat** : la valeur d'énumération écrite à l'américaine, le code d'erreur et les noms d'exemples à l'anglaise.
- **Constat.** Les deux graphies sont figées avec le contrat : `enums.CostTypeKind.labor` dans les catalogues du front, `errors.LABOUR_CATEGORY_REQUIRED` à côté. Sans conséquence fonctionnelle ; mais une fois gelé, unifier coûterait un changement incompatible de l'un ou de l'autre. À trancher maintenant ou à assumer dans DECISIONS (« Vocabulaire »).
- **Proposition.** Soit renommer le code `LABOR_CATEGORY_REQUIRED` (un code d'erreur se renomme à moindre coût qu'une valeur d'énumération portée en base), soit une ligne dans « Vocabulaire » de DECISIONS.md assumant les deux graphies.
- **DECISIONS.md** : « Vocabulaire » (8277) ne tranche pas la graphie ; EP-14/L42p (4850) a écarté de renommer `provision`, « un changement du client et du back sans gain de sens » — le même raisonnement peut s'appliquer, à condition de l'écrire.

### C-09 — Le nœud d'un rôle envoyé à la modification : ignoré ou refusé ?

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/reference.yaml:243-268` (`ResourceRoleUpdate`, sans `org_node_id`), `docs/api/paths/reference.yaml:600-676` (`updateResourceRole`) ; **exigence** WF-REF-0090 : « Le nœud d'un rôle ne se modifie pas après sa création […] Vérif : La modification du nœud d'un rôle existant est refusée » ; **ce que dit le contrat** : « Le nœud du rôle ne se modifie pas : un rôle ne se déplace pas d'un nœud à l'autre, une réorganisation le recrée sous le nouveau » ; le schéma ne porte pas le champ et n'a pas `additionalProperties: false`.
- **Constat.** Le Vérif décrit un refus ; le contrat décrit une absence. Un client qui envoie `org_node_id` (un formulaire qui renvoie l'objet lu entier, comme la correspondance le fait) ne sait pas s'il sera ignoré en silence ou refusé, ni par quel code — le contrat a `FIELD_READ_ONLY` (`UserUpdate`, « une valeur différente de celle du compte est refusée ») et `FIELD_NOT_ACCEPTED` (un champ qu'un nœud n'accepte pas) pour deux situations voisines. Les modèles Pydantic engendrés peuvent ignorer ou rejeter les champs inconnus selon leur configuration : le service et le faux back peuvent diverger.
- **Proposition.** Une phrase dans `ResourceRoleUpdate` et le 422 d'`updateResourceRole`, sur le modèle d'`UserUpdate` : « Un `org_node_id` envoyé différent du nœud du rôle est refusé par 422, `fields` désignant `/org_node_id` par `FIELD_READ_ONLY` ; renvoyé inchangé, il ne l'est pas (WF-REF-0090). » Ou dire qu'il est ignoré — mais le Vérif dit « refusée ».
- **DECISIONS.md** : EP-14/L42j (4542-4556) décrit les refus par champ d'un rôle sans celui-ci ; aucune décision sur un nœud envoyé à la modification.

### Ce qui est juste

- **Attributs et énumérations** : chaque attribut des WF-REF-0030 à 0120 et 0160 à 0190 est porté par son schéma (code, libellé, type et ses trois valeurs ; code comptable ; nœud, catégorie, calendrier et capacité `monthly_hours`/`headcount` ; libellé et sept jours ; six bornes, quatre seuils, délai ; cinq colonnes lues dans l'ordre fixe, intitulés, colonnes conservées, `is_complete`/`missing_columns`) ; `ReferenceReadiness.missing` suit l'ordre de WF-CYC-0120 ; les treize `CommandCondition` et tous les `ErrorCode` cités par la famille existent au catalogue ; les noms suivent la table du §4.4.1 (`org_node`, `resource_role`, `calendar`, `cost_type`, `cost_category`, `hourly_rate`, `reference_setting` → `/reference/settings`).
- **Règles et refus** : désactivation en cascade d'un nœud et d'une nature (réponse ou « relit » dits), réactivation conditionnée (`org_node_parent_active`, `org_node_active`, `cost_type_active`) avec 409 et exemples ; type d'une nature et rattachement d'une catégorie figés par emploi, taux et rôle, les 409 nommant catégories ou rôles ; unicité par 409 `ALREADY_EXISTS` avec `conflicting_object_id` (et `_label` pour nœuds et rôles) sur code, code comptable, libellé de calendrier ; second taux par 409 sans `fields` ; calendrier par défaut unique, désactivation et désignation gardées ; bornes de la matrice et seuils (ordre, ]0,1[, 1–104 semaines) refusés par champ ; doublons d'intitulés de la correspondance ; 412 sur chaque écriture versionnée ; bornes `minimum`/`maximum` cohérentes entre lecture et écriture (`max_weeks_between_reviews`, `IndexThreshold`, `Year`, `maxLength` 20/200).
- **Listes et volumes** : quatre tables plates et la grille paginées (`Limit` ≤ 500) avec `meta.total`, filtres par colonne et bornes `_min`/`_max` (sauf les heures des calendriers, C-352), tri à égalité départagé ; 200 catégories, 150 lignes de grille sur 15 ans, 40 nœuds possibles sans pagination (décision L42a). **Fixtures** : cohérentes (niveaux et libellés de parent de l'arbre, rattachements des rôles vers des objets lus, un seul calendrier par défaut, `years` croissantes et `cells` alignées, `hourly_rates` = ligne MO-001 de la grille, codes comptables uniques, borne 99,12 incluse et 39 lignes, zones 16 rangées p puis g, chaque refus conforme à sa description).

### Doutes

- **WF-REF-0060, Vérif** : « L'ajout d'une colonne pour une année déjà présente est refusé. Une colonne ajoutée est vide. » Le contrat ne connaît pas de colonne vide : une année existe par son premier taux (`HourlyRateGrid.years`, `setHourlyRate`), et l'ajout d'une colonne est un geste du front. C'est cohérent et DECISIONS (448, 2937) l'assume implicitement, mais le refus du Vérif n'a pas de surface d'API — à confirmer comme choix assumé, ou à écrire dans `INVENTORY.md` parmi « Ce que le contrat ne porte pas ».
- **`RoleCapacity.headcount` en `Decimal`** : la spécification dit « l'effectif auquel ces heures correspondent », les fixtures écrivent des entiers (`"3"`, `"2800"`). Un effectif fractionnaire (2,5 ETP) est-il voulu ? Le type ne gêne pas ; un `integer` ne serait plus possible après le gel.
- **`setHourlyRate` sur une catégorie désactivée** : ni la spécification ni le contrat ne disent si un taux se saisit sur une catégorie désactivée (lisible dans la grille avec `include_inactive`). Un 422 `INACTIVE_REFERENCE_OBJECT` sans `fields` serait la forme voisine ; aucune exigence ne l'impose.
- **Lecture des taux d'une catégorie désactivée** : `listHourlyRates` n'a ni `include_inactive` ni 403 ; `getHourlyRateGrid` refuse les désactivées sans permission. Les deux lectures du même concept n'ont pas la même garde ; je n'ai pas trouvé de décision, et je ne sais pas si c'est voulu.

## Annexe D — Projets, cycle de vie, lotissement, sous-projets, contributeurs


Lu : `docs/api/README.md` (Conventions) ; `docs/api/paths/projects.yaml` (973 lignes, entier) ;
`docs/api/components/schemas/projects.yaml` (939 lignes, entier) ; `common.yaml` (`ErrorCode`,
`ProblemParams`, `Percent`, `ActorRef`, `Audit`, `LockVersion`) ; `responses.yaml` (`Forbidden`,
`NotFound`, `Conflict`, `PreconditionFailed`) ; `revisions.yaml` (`Timeline`, `TrackingEntry`,
`RevisionMark`, `abandonRevision`, `setNodeTracking`) ; spec §3.2.3 (682–752), §3.3.2 (902–1069),
§3.4.5.2 (2032–2197), §3.4.5.3.1 (2350–2378), §4.4.1 (3847–3980), §4.6.2 (volumes), glossaire
« Contributeur » ; `INVENTORY.md` (lignes 127–149) ; `DECISIONS.md` : L44a, L42i, L42l, L42o, L42k,
EP-15/US-0450, US-0490, US-0490/L4, US-0530, US-0610, US-0640/L1, et la section « Révision de la
spécification du 2026-10-03 » (permissions, `StateTransition.reason`) ; `EP-16-maquette-durcissement.md`
(« Constats reçus », US-0610) ; générateurs `mockcycle.py`, `mocklists.py`, `mockdata.py`,
`mockcore.py` (chronologies). **70 fixtures ouvertes** : toutes celles que `paths/projects.yaml`
référence (témoins, variantes et chaque exemple de refus), de `project*.json` à `timeline*.json`.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| D-01 | bloquant | `schemas/projects.yaml:557-574` (`ProjectExit`), `paths/projects.yaml:294-331` (`exitProject`) | La sortie d'un projet qui porte une révision en cours ne reçoit pas le choix « la marquer (nom de version) ou l'abandonner », exigé « dans la même opération » ; `project_completed` montre la révision 102 disparue sans que rien ne dise comment | WF-CYC-0090 |
| D-02 | majeur | `schemas/projects.yaml:347-431` (`ProjectCommand`), fixtures `project.json`, `project_updated.json`, `project_completed.json` | `lose` est listée indisponible (`project_in_pricing`) sur un projet En cours et sur un projet clos, alors qu'une sortie « qui ne le deviendra jamais … n'y figure pas » ; les conditions des trois sorties ne sont décrites nulle part | WF-CYC-0060 |
| D-03 | majeur | `paths/projects.yaml:325-330` (`exitProject` 409, 422) | Le 409 ne nomme ni code ni `missing_condition` ni ordre, sans exemple ; le 422 est générique : le refus de `confirmed` absent/faux n'a pas de code (422 `VALIDATION_FAILED` ou 400 `CONFIRMATION_REQUIRED` ?) | WF-CYC-0060, WF-CYC-0080, WF-CYC-0090 |
| D-04 | mineur | `paths/projects.yaml:181-183` (`updateProject`) | La description dit la probabilité de gain « refusée par champ (422) » dès En cours, quand le 409 de la même opération, `Project.win_probability`, la fixture et L42i disent 409 `STATE_FORBIDS_OPERATION` | WF-PRJ-0090 |
| D-05 | majeur | `paths/projects.yaml:960-971` (`deleteTimeline` 403), `:897-939` (`createTimeline`), contre `:205-214`, `:438-447`, `:567-573`, `:625-631`, `:685-708`, `:822-826` | Un projet terminal est refusé par 403 `PROJECT_TERMINAL` sur une chronologie et par 409 `STATE_FORBIDS_OPERATION`/`project_not_terminal` sur toute autre écriture du projet ; `createTimeline` ne dit rien | WF-CYC-0100, WF-IHM-0090 |
| D-06 | majeur | `paths/projects.yaml:785-845` (`setContributors`), `schemas/projects.yaml:93-99` (`CommandCondition.is_project_manager`) | « La seule saisie ouverte à un non-contributeur » — inscrire un chef de projet quand le compte du dernier est désactivé — n'est ni décrite ni permise par le contrat, qui réserve l'écriture aux chefs de projet | WF-PRJ-0060 |
| D-07 | majeur | `schemas/projects.yaml:32-36`, `:477-478`, `:492-493`, `:450-451` (`Project.code`, `ProjectCreate.code`, `ProjectUpdate.code`, `ProjectSummary.code`) | Le code projet admet `""`, les blancs et la barre oblique : pas de `pattern: '\S'` (convention des codes), et rien n'interdit `/`, seul séparateur de l'élément d'OTP qui le porte | WF-PRJ-0010, WF-CRE-0020, WF-CYC-0030 |
| D-08 | mineur | `paths/projects.yaml:492` (`listSubprojects`) | « Les sous-projets, qui regroupent des tâches sans dupliquer l'arbre » : ils regroupent des lignes de devis, « jamais » des tâches | WF-PRJ-0050, §3.2.3 |
| D-09 | mineur | `paths/projects.yaml:392` (`setWorkBreakdown`) | « Croise le découpage fonctionnel et le découpage produit du projet » : le lotissement reproduit le bon de commande, rien d'autre | WF-PRJ-0020 |
| D-10 | mineur | `paths/projects.yaml:564-594` (`createSubproject`) | Seule opération sous `/projects/{project_id}` sans `404` | WF-ADM-0110 (convention 404) |
| D-11 | mineur | `schemas/projects.yaml:592-594` (`WorkBreakdown.work_packages`), `paths/projects.yaml:387-413` | Rien ne dit ce que fait une saisie sans aucun lot (`minItems` absent) ni si le lotissement par défaut, persistant (ids 714/715), suit le libellé du projet | WF-PRJ-0020 |
| D-12 | mineur | `paths/projects.yaml:917` (`createTimeline` corps) | `label` sans `pattern: '\S'`, quand `Timeline.label` (`revisions.yaml:1482`) le porte ; schéma anonyme | WF-PLA-0140, convention `\S` |
| D-13 | mineur | `common.yaml:453` (`ErrorCode.PROJECT_CODE_REQUIRED`) | Code du catalogue qu'aucune opération ne déclare, comme `WIN_PROBABILITY_FROZEN` retiré par L42i | WF-PRJ-0010 |

### Constats

#### D-01 — La sortie du cycle de vie ne porte pas le sort de la révision en cours
- **gravité** : bloquant ; **emplacement** : `docs/api/components/schemas/projects.yaml:557-574`
  (`ProjectExit` : `to_state`, `confirmed`, `reason`, et rien d'autre),
  `docs/api/paths/projects.yaml:294-331` (`exitProject`, réponse 200 `Project`) ; fixture
  `fixtures/api/project_completed.json` (`current_revision_id: null`, le témoin ayant la révision 102
  en cours dans `project.json`) ; **exigence** WF-CYC-0090 : « Lorsque le projet porte une révision
  en cours, la confirmation demande de la marquer, avec un nom de version (WF-REV-0020), ou de
  l'abandonner (WF-REV-0010) ; la sortie n'est appliquée qu'avec ce choix, dans la même opération.
  Un projet terminal ne porte donc aucune révision en cours. » ; **ce que dit le contrat** :
  `ProjectExit` « Sortie manuelle … appliquée après confirmation explicite (WF-CYC-0090) » ; la
  description d'`exitProject` ne nomme la révision en cours nulle part.
- **Constat.** Le choix est une donnée obligatoire de l'opération quand une révision est en cours,
  et il emporte un nom de version (unique parmi les révisions marquées, WF-REV-0020) : sans lui le
  serveur ne peut pas appliquer la sortie conforme, et le front ne peut pas poser la question que la
  confirmation doit poser. La fixture `project_completed` contredit silencieusement `project.json`
  (la 102 a disparu : marquée ? abandonnée ?). Le marquage étant confié au worker (202,
  `RevisionMark`), une sortie qui marque devient une opération longue (WF-ARC-0090) : la forme de la
  réponse (200 `Project` aujourd'hui) est à trancher aussi. Tout cela est une modification
  incompatible du corps après le gel.
- **Proposition.** Ajouter à `ProjectExit` le sort de la révision en cours, exigé quand
  `Project.current_revision_id` n'est pas nul, et le dire :
  ```yaml
  current_revision:
    anyOf:
      - type: object
        required: [action]
        properties:
          action: { type: string, enum: [mark, abandon] }
          version_name: { type: string, minLength: 1, pattern: '\S', maxLength: 100 }  # exigé si mark (WF-REV-0020)
          description: { anyOf: [{ type: string }, { type: 'null' }] }
      - { type: 'null' }
  ```
  422 `VALIDATION_FAILED` sur `/current_revision` (`VALUE_REQUIRED`) quand le projet en porte une et
  que le choix manque ; 409 `ALREADY_EXISTS` sur `/current_revision/version_name` pris. Trancher si la
  sortie qui marque rend 202 `BackgroundTaskRef` (le marquage calcule les indicateurs dans le worker)
  ou 200 avec le marquage synchrone. Dire dans `project_completed` ce qu'est devenue la 102, et
  ajouter un exemple d'`exitProject` avec révision en cours.
- **DECISIONS.md** : aucune décision (grep `exit`, `sortie`, `WF-CYC-0090` : seules la relecture du
  motif, « Le motif d'une sortie se relit », l. 326, et « Le projet terminal n'a pas de révision en
  cours » (#795 point 3), l. 7987, qui constate l'absence sans dire comment elle s'obtient).

#### D-02 — `lose` listée là où la spécification veut qu'elle ne figure pas ; conditions des sorties non décrites
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/projects.yaml:347-431`
  (`ProjectCommand`, l. 384 : « ouvrir une révision, les trois sorties du cycle de vie
  (WF-CYC-0060) » — aucune condition nommée pour `complete`, `lose`, `abandon`) ; fixtures
  `project.json`, `project_updated.json`, `project_without_current_revision.json`,
  `project_actual_cost_mapping_incomplete.json` (En cours : `lose` `is_available: false`,
  `missing_conditions: ["project_in_pricing"]`), `project_completed.json` (clos : `complete`
  `project_in_progress`, `lose` `project_in_pricing`, `abandon` `project_not_terminal`) ;
  **exigence** WF-CYC-0060, Vérif : « Une sortie qui le deviendra dans un état ultérieur — Terminer
  depuis Chiffrage — y est présentée indisponible, avec sa condition (WF-IHM-0090) ; une sortie qui
  ne le deviendra jamais — Déclarer perdu depuis En cours — n'y figure pas. » ; **ce que dit le
  contrat** : `Project.available_commands` (l. 63-66) « chacune disponible ou non, avec les conditions
  qui lui manquent (WF-IHM-0090). Une commande absente de la liste n'est pas présentée. »
- **Constat.** Par la règle même du contrat, une commande listée indisponible est présentée avec sa
  condition : le front qui suit les fixtures présente « Déclarer perdu » indisponible sur un projet En
  cours, ce que la spécification interdit. Le projet en cours ne redescend jamais à Chiffrage
  (WF-CYC-0080, aucun retour en arrière) : `project_in_pricing` n'est pas une condition qui peut se
  satisfaire, et la nommer trompe (WF-IHM-0090 : « ce qu'il faut faire pour la satisfaire »). Les
  conditions des trois sorties (`complete` → `project_in_progress`, `lose` → `project_in_pricing`,
  `abandon` → `project_not_terminal`) ne sont dites que par les exemples. Changer la liste après le
  gel change ce que le front présente.
- **Proposition.** Dans la description de `ProjectCommand`, dire les conditions des sorties et la
  règle de présence : `complete` listée dès Créé, `project_in_progress` manquante avant En cours ;
  `lose` listée aux états Créé (`project_in_pricing` manquante) et Chiffrage, **absente** dès En
  cours ; `abandon` listée sur tout état non terminal. Trancher ce qu'un projet clos liste : par
  WF-CYC-0060 aucune sortie n'y figure (aucune ne « le deviendra ») ; par la règle du contrat tout est
  listé avec `project_not_terminal`. Régénérer les fixtures en conséquence (`project*.json`,
  `projects*.json`).
- **DECISIONS.md** : aucune décision sur la présence de `lose` (grep `project_in_pricing` : seule la
  mention de L42i, l. 4114, qui l'écarte pour la probabilité de gain) ; l'exception du 2026-10-05
  (`Project.available_commands`, l. 66-71) ne couvre que les imports et `generate_skeleton`.

#### D-03 — Les refus d'`exitProject` ne sont pas décrits
- **gravité** : majeur ; **emplacement** : `docs/api/paths/projects.yaml:325-329` (`'409':
  description: Sortie non permise depuis l'état courant (WF-CYC-0060, WF-CYC-0080).` — sans code,
  sans `params`, sans exemple), `:330` (`'422': { $ref: …/UnprocessableEntity }`),
  `docs/api/components/schemas/projects.yaml:568-571` (`confirmed: const: true`, « Faux ou absent, la
  sortie est refusée ») ; **exigence** WF-CYC-0060 et WF-CYC-0080 (« Toute tentative de transition
  depuis Terminé, Perdu ou Abandonné est refusée »), WF-IHM-0090 (« Tout refus nomme la condition
  manquante ») ; **ce que dit le contrat** : rien de plus que « non permise ».
- **Constat.** Toute autre commande du projet refusée par son état l'est par 409
  `STATE_FORBIDS_OPERATION`, `params.missing_condition` nommant la première condition dans l'ordre de
  la commande (`updateProject`, `setWorkBreakdown`, `deleteSubproject`…) ; `exitProject` est la seule
  qui ne le dit pas, et la seule des opérations à corps sans aucun exemple de refus (409 ni 422). Le
  refus de `confirmed` absent ou faux n'a pas de code : `CONFIRMATION_REQUIRED` (400) existe au
  catalogue et sert à `startRestore` pour une confirmation qui ne nomme pas sa cible
  (`paths/platform.yaml:481`) ; `const: true` tombe sinon dans le 422 `VALIDATION_FAILED` sur
  `/confirmed`. Un implémenteur choisira ; le front ne saura pas quoi rendre.
- **Proposition.**
  ```yaml
  '409':
    description: >-
      La sortie demandée est indisponible : `STATE_FORBIDS_OPERATION`, `params.missing_condition`
      la nommant — `project_in_progress` pour `completed`, `project_in_pricing` pour `lost`,
      `project_not_terminal` pour `abandoned` et pour toute sortie d'un état terminal (WF-CYC-0060,
      WF-CYC-0080) ; une révision en cours sans sort choisi (D-01) ; rien n'est écrit.
    examples: { lost_from_in_progress: …, terminal: … }
  '422':
    description: >-
      `VALIDATION_FAILED`, `fields` désignant `/confirmed` absent ou faux par `VALUE_REQUIRED`
      (WF-CYC-0090), ou `/reason` trop long — ou 400 `CONFIRMATION_REQUIRED`, à trancher.
  ```
  Ajouter les exemples (`project_exit_refused`, `project_exit_unconfirmed`).
- **DECISIONS.md** : aucune décision (grep `exitProject`, `/exit`, `sorties du cycle` : L42i l. 4101
  dit seulement que les sorties « sont des commandes du projet (WF-CYC-0060), pas un prochain état »).

#### D-04 — `updateProject` dit « 422 » pour la probabilité figée, le reste du contrat dit 409
- **gravité** : mineur ; **emplacement** : `docs/api/paths/projects.yaml:181-183` : « La probabilité
  de gain n'est plus modifiable à partir de En cours (WF-PRJ-0090) : la commande
  `update_win_probability` le dit d'avance, et la valeur envoyée malgré elle est refusée par champ
  (422) » ; contre `:210-213` (409 `STATE_FORBIDS_OPERATION`, `project_before_in_progress`),
  `schemas/projects.yaml:49-52` et `:500-501`, fixture `project_win_probability_frozen.json`
  (`status: 409`) ; **exigence** WF-PRJ-0090 (« La modification de la probabilité est refusée à
  partir de l'état En cours »).
- **Constat.** La description de l'opération contredit son propre 409, le schéma, la fixture et la
  décision ; c'est la rédaction que L42i dit avoir écartée. Un implémenteur du service qui lit la
  description écrit un 422.
- **Proposition.** Remplacer « refusée par champ (422) » par « refusée par 409
  `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_before_in_progress` » ; garder le
  422 pour la seule borne (`VALUE_OUT_OF_RANGE`).
- **DECISIONS.md** : L42i, « La probabilité de gain est dite figée d'avance » (l. 4104-4127) :
  « Écartés, à la relecture : un 422 `VALIDATION_FAILED`, `fields` désignant `/win_probability` par
  `WIN_PROBABILITY_FROZEN`, que la première rédaction du lot avait retenu ». La phrase de la
  description est un reste de cette première rédaction.

#### D-05 — Deux enveloppes pour le même fait : le projet terminal
- **gravité** : majeur ; **emplacement** : `docs/api/paths/projects.yaml:960-971` (`deleteTimeline`
  403 : « comme pour toute écriture du projet … sur un projet terminal `PROJECT_TERMINAL`,
  `params.missing_condition` à `project_not_terminal` », fixture `timeline_delete_terminal.json`,
  `status: 403`) ; `:897-939` (`createTimeline` : ni 409 ni 403 décrit, bien que `manage_timelines`
  nomme `project_not_terminal`, `schemas/projects.yaml:380-383`) ; contre `updateProject` `:210-214`,
  `setWorkBreakdown` `:438-447`, `createSubproject` `:567-573`, `updateSubproject` `:625-631`,
  `deleteSubproject` `:685-708`, `setContributors` `:822-826` : 409 `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` à `project_not_terminal` ; **exigence** WF-CYC-0100 (« Toute modification
  d'un projet terminal est refusée »), WF-IHM-0090 ; **ce que dit le contrat** : `deleteTimeline`
  prétend suivre « toute écriture du projet » alors que toutes les autres écritures du projet font
  l'inverse.
- **Constat.** Une même condition d'une même commande du projet (`project_not_terminal`, listée par
  `update`, `update_work_breakdown`, `manage_contributors` et `manage_timelines` de la même manière,
  `project_completed.json`) se refuse par 409 ici et par 403 là. Le front (`problemMessage`, la lecture
  commune des `missing_condition`) et le service engendré doivent porter deux chemins ; un
  implémenteur de `createTimeline`, à qui le contrat ne dit rien, choisira l'un ou l'autre. Un statut
  qui change après le gel est une rupture pour le client.
- **Proposition.** Une seule règle au contrat pour les écritures du projet (hors grille) : 409
  `STATE_FORBIDS_OPERATION` `project_not_terminal`, celle de L42a (« le refus d'une commande qu'un état
  rend indisponible est `STATE_FORBIDS_OPERATION` ») ; `deleteTimeline` et `createTimeline` déclarent
  ce 409, `timeline_delete_terminal` passe à 409, et le 403 `PROJECT_TERMINAL` reste à la saisie de
  grille (famille révisions), ou l'inverse — mais une seule, écrite dans le README. À tout le moins,
  `createTimeline` doit dire son refus sur un projet clos.
- **DECISIONS.md** : deux décisions qui se contredisent sur le même fait : L42k, « `deleteTimeline`
  reste un 204 sans 409 … Un projet terminal reste un 403, comme toute écriture » (l. 5436-5449) et
  US-0640/L1 #803 (l. 7969-7973 : « c'est le premier exemple de ce refus ») d'un côté ; L42i (l. 4123,
  « tout refus de ce lot qui nomme une `missing_condition` est un 409 `STATE_FORBIDS_OPERATION` »),
  L42l (« Sur un projet clos, `project_not_terminal` vient en dernier » dans le 409) de l'autre.
  Aucune ne tranche l'écart entre elles.

#### D-06 — L'inscription d'un chef de projet par un non-contributeur n'existe pas au contrat
- **gravité** : majeur ; **emplacement** : `docs/api/paths/projects.yaml:789-799` (`setContributors` :
  « réservée aux chefs de projet (WF-PRJ-0060, WF-ADM-0110) »), `:820` (403 générique),
  `docs/api/components/schemas/projects.yaml:98-99` (`CommandCondition` : « `is_project_manager`
  manque à qui n'est que contributeur pour une action structurante ou le paramétrage du projet,
  réservés aux chefs de projet ») ; **exigence** WF-PRJ-0060 : « Lorsque le compte du dernier chef de
  projet est désactivé (WF-ADM-0060), un utilisateur portant la permission de modifier FBS-4.2 et
  celle de consulter tous les projets peut y inscrire un chef de projet ; c'est la seule saisie
  ouverte à un non-contributeur. » (repris par WF-ADM-0110 : « hors l'inscription d'un chef de projet
  que WF-PRJ-0060 ouvre à un non-contributeur lorsque le compte du dernier chef de projet est
  désactivé ») ; **ce que dit le contrat** : rien — la liste des contributeurs est inscriptible par
  ses chefs de projet, et par eux seuls.
- **Constat.** Un projet dont le dernier chef de projet est désactivé n'a plus personne pour écrire
  sa liste : la spécification prévoit la seule issue, le contrat la ferme. Un service écrit sur le
  contrat refuse par 403 `NOT_CONTRIBUTOR`/`NOT_PROJECT_MANAGER` ; un front ne présente pas la
  commande, `manage_contributors` n'étant listée qu'aux chefs de projet (`project_reader.json` :
  aucune commande pour le manager qui lit tout). La fixture `contributors.json` ne porte pas le cas
  (Camille Martin reste active).
- **Proposition.** Décrire dans `setContributors` et dans `ProjectCommand.manage_contributors` la
  condition d'ouverture : « ouverte aussi, quand aucun chef de projet du projet n'a de compte actif, à
  l'appelant qui porte `project_settings.write` et `all_projects_read` ; la liste envoyée doit alors
  inscrire un chef de projet actif, sinon 409 `LAST_PROJECT_MANAGER` » ; lister `manage_contributors`
  à cet appelant dans ce seul cas ; un exemple (`contributors_set_by_rescuer`, le témoin après la
  désactivation de Camille Martin, variante contrefactuelle). Trancher si la liste lue
  (`listContributors`) lui est ouverte : il lui faut son `lock_version`.
- **DECISIONS.md** : aucune décision (grep `dernier chef de projet`, `non-contributeur`, `seule
  saisie ouverte` : rien).

#### D-07 — Le code projet n'est ni borné par en bas ni protégé de la barre oblique
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/projects.yaml:32-36`
  (`Project.code: anyOf: [{ type: string, maxLength: 50 }, { type: 'null' }]`), `:477-478`
  (`ProjectCreate.code`), `:492-493` (`ProjectUpdate.code`), `:450-451` (`ProjectSummary.code`) ;
  `paths/projects.yaml:131-136` et `:222-228` (422 : seul `VALUE_TOO_LONG` pour `/code`) ;
  **exigences** WF-PRJ-0010 (« Un projet porte un code projet, unique dans l'installation … exigé pour
  le passage du projet à l'état En cours »), WF-CRE-0020 (« Le projet et le sous-projet d'une ligne de
  coût sont déduits de son élément d'OTP, qui porte le code projet (WF-PRJ-0010), suivi
  facultativement d'une barre oblique et du code sous-projet : seule la barre oblique sépare les deux
  codes, et le code projet peut contenir des points »), convention README (« Un libellé, un nom ou un
  code reçu porte au moins un caractère qui n'est pas un blanc (`pattern: '\S'`) ») ; **ce que dit le
  contrat** : `maxLength: 50` seulement — les codes du référentiel portent tous `minLength: 1,
  pattern: '\S'` (`reference.yaml:121, 235, 268, 463`), et `DeclaredSubprojectCode` exclut `/`.
- **Constat.** (1) Un code `""` ou `"   "` est accepté par le schéma, compte comme « renseigné »
  pour `project_code_set` (WF-CYC-0030 : le projet passerait En cours) et entre dans l'unicité
  (`ALREADY_EXISTS` sur un code vide). (2) Un code projet qui contient `/` rend l'élément d'OTP
  ambigu : « PRJ/001/SP-CMD » ne se découpe plus — la spécification désigne `/` comme le seul
  séparateur, et le contrat s'y fonde (`reference.yaml:926-927`, `ActualCostLine.subproject_code`).
  Interdire le caractère après le gel invaliderait des codes déjà saisis : c'est maintenant.
- **Proposition.**
  ```yaml
  ProjectCode:
    type: string
    minLength: 1
    maxLength: 50
    pattern: '^[^/\s]([^/]*[^/\s])?$'   # ou au moins '^[^/]*\S[^/]*$'
    description: >-
      Code sous lequel l'ERP connaît le projet (WF-PRJ-0010) : jamais blanc, sans barre oblique,
      seul séparateur de l'élément d'OTP qui le porte (WF-CRE-0020). Refusé par 422 `VALIDATION_FAILED`,
      `fields` désignant `/code` : vide, `VALUE_REQUIRED` ; `/`, `PROJECT_CODE_INVALID` (ou un motif
      commun) ; trop long, `VALUE_TOO_LONG`.
  ```
  partagé par `Project`, `ProjectCreate`, `ProjectUpdate` ; dire dans `updateProject` ce que fait
  `code: null` sur un projet En cours (voir Doutes).
- **DECISIONS.md** : aucune décision sur la forme du code projet (US-0610, l. 7677-7723, ne borne que
  le code d'un sous-projet et écarte explicitement d'appliquer son motif « au code lu d'une ligne de
  coût réel », pas au code projet ; L42i, l. 4140-4153, ne traite que le porteur d'un code pris).

#### D-08 — « Les sous-projets, qui regroupent des tâches »
- **gravité** : mineur ; **emplacement** : `docs/api/paths/projects.yaml:492` (`listSubprojects` :
  « Les sous-projets, qui regroupent des tâches sans dupliquer l'arbre (WF-PRJ-0050) ») ;
  **exigence** §3.2.3 : « Les sous-projets … regroupent des lignes de devis, et c'est à cette maille
  que les coûts réels sont rapprochés du budget : les dépenses se font sur un code de sous-projet,
  jamais sur une tâche. » ; WF-PRJ-0050 (lignes de devis portées par un sous-projet).
- **Constat.** La description dit l'inverse du modèle : une ligne de devis porte un sous-projet
  (`EstimateLine.subproject_id`), une tâche n'en porte pas ; un implémenteur du front ou du service
  chercherait un rattachement de tâche qui n'existe pas.
- **Proposition.** « Les sous-projets, codes de l'ERP sous lesquels les lignes de devis se
  ventilent et les coûts réels s'imputent (WF-PRJ-0050), chacun avec ses commandes … ».
- **DECISIONS.md** : aucune décision ; L42i (« `update` couvre le paramétrage du projet, sous-projets
  compris ») ne touche pas cette phrase.

#### D-09 — « Croise le découpage fonctionnel et le découpage produit »
- **gravité** : mineur ; **emplacement** : `docs/api/paths/projects.yaml:392` (`setWorkBreakdown`) ;
  **exigence** WF-PRJ-0020 : « Le lotissement découpe la commande en lots, chaque lot contenant des
  postes, chaque poste contenant des livrables » ; §3.2.3 : « Le lotissement reflète le bon de
  commande ».
- **Constat.** Ni « découpage fonctionnel » ni « découpage produit » n'existent dans la spécification
  pour le lotissement ; la phrase vient d'une lecture antérieure et égare.
- **Proposition.** « Saisit le lotissement entier — les lots de la commande, leurs postes, leurs
  livrables (WF-PRJ-0020). Un lot ou un poste que la saisie omet est supprimé … ».
- **DECISIONS.md** : aucune décision ; EP-15/US-0450 (l. 6165-6231) réécrit l'imbrication sans toucher
  cette phrase.

#### D-10 — `createSubproject` sans `404`
- **gravité** : mineur ; **emplacement** : `docs/api/paths/projects.yaml:564-594` (réponses : 400,
  401, 403, 409, 422, 503) ; **exigence** convention README « 404 lorsque la permission de consultation
  manque » (WF-ADM-0110), appliquée par `createTimeline` (`:929`), `setContributors` (`:821`),
  `setWorkBreakdown` (`:437`), `updateSubproject` (`:624`).
- **Constat.** Le chemin porte `project_id` ; un projet inexistant ou invisible répond 404 comme
  partout, et le client engendré (`openapi-fetch`) ne le typera pas.
- **Proposition.** `'404': { $ref: ../components/responses.yaml#/NotFound }` après le 403.
- **DECISIONS.md** : aucune décision.

#### D-11 — La saisie sans lot et le lotissement par défaut
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/projects.yaml:592-594`
  (`WorkBreakdown.work_packages: type: array, items: WorkPackage` — sans `minItems`),
  `paths/projects.yaml:387-413` ; fixture `work_breakdown_default.json` (lot 714 et poste 715,
  `lock_version: 0`, libellé « Rénovation du poste de livraison ») ; **exigence** WF-PRJ-0020 : « en son
  absence, le lotissement vaut un lot et un poste qui portent le libellé du projet, sans livrable ».
- **Constat.** Le défaut est un objet persistant (il a des identifiants et un compteur), et le
  contrat ne dit ni ce que produit `work_packages: []` (retour au défaut ? refus ? lotissement vide,
  que WF-PRJ-0020 interdit ?), ni si le lot et le poste par défaut suivent le renommage du projet
  (`updateProject.label`) tant que personne ne les a écrits. Deux implémentations divergeraient.
- **Proposition.** Soit `minItems: 1` et 422 `VALUE_REQUIRED` sur `/work_packages`, soit : « vide, la
  saisie supprime tout lot saisi et le lotissement redevient celui par défaut, rendu avec de nouveaux
  identifiants » ; dire que le défaut porte le libellé du projet « tant qu'aucune saisie ne l'a
  écrit, et le suit ».
- **DECISIONS.md** : L42k, « Le lotissement par défaut porte le libellé du projet » (l. 5302-5308),
  dit le libellé, pas la saisie vide ni le suivi du renommage.

#### D-12 — Le nom d'une chronologie créée, sans `\S` et sans schéma nommé
- **gravité** : mineur ; **emplacement** : `docs/api/paths/projects.yaml:913-917` (corps inline :
  `label: { type: string, minLength: 1, maxLength: 200 }`) contre
  `docs/api/components/schemas/revisions.yaml:1482` (`Timeline.label: … pattern: '\S' …`) ;
  **exigence** convention README (`pattern: '\S'`, « fait seulement de blancs, il est refusé par 422
  `VALIDATION_FAILED` sur son champ ») ; WF-PLA-0140.
- **Constat.** Un nom fait de blancs passe le schéma de l'écriture et contredit celui de la lecture ;
  le modèle engendré du corps n'a pas de nom (`TimelineCreate`), seul corps anonyme de la famille.
- **Proposition.** `TimelineCreate: { required: [label], properties: { label: { type: string,
  minLength: 1, pattern: '\S', maxLength: 200 } } }` dans `revisions.yaml`, référencé par
  `createTimeline`, et le 422 (`:930-933`) nommant le nom blanc.
- **DECISIONS.md** : EP-03 #837 (« Aucun libellé fait seulement de blancs », l. 5766) pose la règle ;
  aucune exception pour la chronologie.

#### D-13 — `PROJECT_CODE_REQUIRED` au catalogue, déclaré par personne
- **gravité** : mineur ; **emplacement** : `docs/api/components/common.yaml:453` (`ErrorCode`) ;
  aucune occurrence dans `paths/*.yaml` ni `schemas/*.yaml` (grep) ; **exigence** WF-PRJ-0010,
  WF-CYC-0020 : le passage à En cours est automatique, et le code manquant se dit par la condition
  `project_code_set` de `NextState.missing_conditions`.
- **Constat.** Un code que le front doit savoir rendre et qu'aucune réponse n'emploie ; L42i a
  retiré `WIN_PROBABILITY_FROZEN` et `HAS_ACTUAL_COSTS` pour cette raison exacte.
- **Proposition.** Le retirer, ou nommer l'opération qui le rend (aucune n'exige le code : la
  désignation de la référence sans code laisse le projet en Chiffrage, WF-CYC-0030).
- **DECISIONS.md** : L42i, l. 4120-4122 (« `WIN_PROBABILITY_FROZEN`, qui figurait au catalogue sans
  qu'aucune réponse le déclare, en est retiré, comme `HAS_ACTUAL_COSTS` ») ; rien sur
  `PROJECT_CODE_REQUIRED`.

### Ce qui est juste

- `ProjectState` porte les six codes du tableau 6 et aucun autre ; `LifecycleTrigger` les deux faits
  de la figure 8 ; `NextState` et ses quatre exemples (créé → `first_revision_created` sans
  condition ; chiffrage avec code → `reference_revision_designated` seule ; en cours et clos → nuls) ;
  `StateTransition` (`from_state` nul à la création, `reason` nul hors sortie manuelle,
  `occurred_at`/`actor`) et ses deux fixtures datent le témoin comme `project.json` et l'offre
  perdue au 15 mars (WF-CYC-0130).
- `Project` porte chaque attribut de WF-PRJ-0080 (libellé, description, `client` nullable borné,
  code, état, `inflation_rate` et `win_probability` en rapports 0–1 avec leurs refus `minimum`/
  `maximum`, `order_received_on`), les deux révisions, `audit`, `lock_version` ; les fixtures sont
  cohérentes entre elles (versions 7 → 8 après écriture, `update_win_probability` toujours à la
  suite d'`update`, états et révisions du témoin identiques d'un exemple à l'autre).
- Lotissement : imbrication lot → poste → livrable et `WorkBreakdownKind` dans l'ordre du §4.4.1 ;
  `is_match`, `attached_task`, compteur nul des lectures filtrées, `UNKNOWN_`/`DUPLICATE_WORK_BREAKDOWN_ITEM`
  aux bons pointeurs, 409 `no_background_task_running`, 412 avec le compteur de `work_breakdown_saved`.
- Sous-projets : `DeclaredSubprojectCode` (31, caractères interdits, « Synthèse »/« Hors
  sous-projet » sans égard à la casse — fixtures `SP/01` et `synthèse`), `ALREADY_EXISTS` avec
  `conflicting_object_label`, les trois conditions de `delete` dans l'ordre décidé puis
  `project_not_terminal`, `params.estimate_lines` nommant les lignes.
- Contributeurs : `LAST_PROJECT_MANAGER` 409 sans paramètre, `UNKNOWN_USER`/`USER_INACTIVE` à la
  ligne, compteur propre à la liste et nul en lecture filtrée, suggestions nommant nœud et rôles ;
  chronologies : liste, création, suppression physique sans 409, inscriptions par `setNodeTracking`
  (famille révisions). `listProjects` : pagination, `meta.states`, `search` code+libellé, période
  sur `audit.updated_at` avec son 422.

### Doutes

- **`exitProject` sans `lock_version`.** `ProjectExit` ne porte aucun compteur et l'opération n'a
  pas de 412, comme `abandonRevision` (DELETE sans corps), alors que `markRevision` en exige un et que
  `deleteNode` en a reçu un (#1210). Une sortie irréversible (WF-CYC-0080) engagée depuis un écran
  périmé n'est refusée par rien ; WF-IHM-0110 exclut la sortie de l'annulation mais ne dit rien de la
  concurrence. À trancher avec D-01.
- **`code: null` sur un projet En cours.** `ProjectUpdate.code` est nullable ; WF-PRJ-0010 exige le
  code pour le passage à En cours et WF-DAT-0060 dit qu'« un code se corrige ». Effacer le code d'un
  projet en cours est-il refusé (par quoi ?) ou admis ? Le contrat ne le dit pas.
- **`ContributorKind.contributor` pour « participant ».** La spécification nomme la qualité
  « chef de projet ou participant » (WF-PRJ-0060, glossaire « Contributeur », WF-IHM-0090) ; le
  contrat `project_manager`/`contributor`, décidé le 2026-10-03 (DECISIONS l. 287-289). Un même mot
  pour l'inscrit et pour la qualité de l'inscrit non chef ; pas un constat, une décision à confirmer
  avant le gel.
- **Propositions de contributeurs.** Le corps de WF-PRJ-0070 propose « les utilisateurs rattachés aux
  nœuds d'organisation des rôles … employés », la Vérif ne les propose que pour « un service dont
  aucun utilisateur n'est contributeur ». Le contrat suit le corps (tout compte du nœud non encore
  inscrit) ; L42i a tranché la révision lue, pas ce point.
- **Export PNG d'une chronologie** (WF-PLA-0140) : aucune opération ni décision ; vraisemblablement
  un rendu du front, mais rien ne l'écrit.
- **`:` dans `DeclaredSubprojectCode`.** La spécification écrit « sans aucun des caractères : \\ / ? *
  [ ] », où le deux-points peut se lire comme ponctuation ; D-7 (US-0610) l'inclut dans les caractères
  interdits, ce qu'Excel justifie. Noté pour que l'auteur le confirme.

## Annexe E — Révisions et structures de coûts


Lu : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/revisions.yaml` lignes 1–636 et
1646–1799 (toutes les opérations hors nœuds) ; `docs/api/components/schemas/revisions.yaml` lignes
1–470, 562–590, 900–928, 1757–1790, 1949–2054 ; `exchanges.yaml` (`ImportCompletedTask`,
`ReportRefusal`, `ImportDifference`, `ImportDifferenceField`) ; `projects.yaml` (`CommandCondition`,
`ProjectCommand`) ; `common.yaml` (`ErrorCode`, `Problem`, `ProblemParams`, `LockVersion`) ;
`reference.yaml#/HourlyRate` ; `parameters.yaml`. Spécification : §3.2.3 (682–752), §3.4.5.1
(1906–2032), WF-RIS-0030/0050/0060 (2753–2807), §3.5.2 (3118–3174), WF-IHM-0110 (3306–3316),
WF-PLA-0020 (2244–2251), §4.4.1 (3849–3979), §4.4.2 (3980–4054), §4.6.2 (volumes). 56 fixtures
ouvertes (toutes celles que les opérations de la famille référencent, `volume/comparison_volume`
exclue), les générateurs `mockcomparisons.py`, `mockhistory.py` et les tests `test_mockversions.py`.
`DECISIONS.md` grep pour chaque constat ; les sections « Constats reçus » et « Les modifications du
contrat » d'EP-16 lues.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| E-01 | bloquant | `schemas/revisions.yaml:277-308` (`CostStructure`), aucune opération | La date de début de planning d'une structure, « saisie », n'est portée par aucun schéma ni aucune opération du contrat | WF-REV-0100, WF-PLA-0020 |
| E-02 | majeur | `schemas/revisions.yaml:1979-2014` (`RevisionComparison.amount_deltas`) | Un seul `delta` par nature/sous-projet, calculé sur le montant à l'année de référence ; la spec exige l'écart des montants budgétés **et** celui des montants réestimés | WF-REV-0080 |
| E-03 | majeur | `schemas/revisions.yaml:13-63` (`Revision`), `paths/revisions.yaml:3-9` (`listRevisions`) | Le taux d'inflation et la probabilité de gain conservés ne sont lisibles que dans `snapshot`, nul dans les 13 exemples et sans règle de nullité ; l'historique ne peut pas les afficher | WF-REV-0070, WF-REV-0090 |
| E-04 | majeur | `schemas/revisions.yaml:369-398` (`StructureMerge`) | La fusion marque la révision mais n'admet pas de `description`, que tout marquage permet | WF-REV-0050, WF-REV-0020 |
| E-05 | majeur | `paths/revisions.yaml:588-610` (`mergeCostStructure`, 409) | Le refus d'un nom de version déjà employé n'est déclaré ni au 409 de la fusion ni comme échec de sa tâche de fond | WF-REV-0050, WF-REV-0020 |
| E-06 | majeur | `paths/revisions.yaml:1646-1700` (`undoLastChange`), `1702-1745` (`redoLastUndo`) | L'historique annulable est tenu par le serveur (« historique de la session », `remaining_depth`) quand la spec le fait tenir par le front, par page ouverte | WF-IHM-0110 |
| E-07 | majeur | `paths/revisions.yaml:1672-1676`, `common.yaml:409` (`UNDO_CONFLICT`) | Le refus d'une annulation pour modification postérieure ne nomme ni son code ni l'objet en conflit, que la spec exige ; `UNDO_CONFLICT` n'est cité par aucune opération ; aucun exemple | WF-IHM-0110 |
| E-08 | majeur | `schemas/revisions.yaml:1757-1790` (`UndoResult`) | Une annulation est une écriture de grille mais ne rend ni totaux, ni tâches redatées, ni compteur de structure (`NodesWritten`) ; `undone.kind` est une chaîne libre | WF-IHM-0110, WF-IHM-0040 |
| E-09 | majeur | `paths/revisions.yaml:441-471` (`createCostStructure`), `schemas/revisions.yaml:355-367` (`StructureCreate`) | `kind: risk` fait créer un devis propre que `createRisk` crée déjà avec le risque ; aucune règle pour `risk_id`, aucun refus du doublon | WF-REV-0100, WF-RIS-0030 |
| E-10 | majeur | `fixtures/api/structure_merge_report_without_current_revision.json:4-5` | Compteurs 1 et 2 alors que la description dit « ceux des structures de la révision marquée » : `structures_amendments.json` donne 3 (principale) et 1 (avenant 2) | WF-REV-0050 |
| E-11 | majeur | `schemas/revisions.yaml:175-193` (`EmployedReference.hourly_rates`) | Les taux conservés sont des `HourlyRate` vivants (`audit`, `lock_version` du référentiel) quand les trois autres valeurs sont des `*Image` | WF-REV-0030, WF-DAT-0010 |
| E-12 | mineur | `paths/revisions.yaml:150-193` (`markRevision`, 409), `schemas/revisions.yaml:65-150` | « Révision déjà marquée » sans code ni condition ; `no_background_task_running` absent ; aucun exemple des deux 409 ; conditions de `mark`, `abandon`, `designate_reference` non décrites dans `RevisionCommand` | WF-REV-0020, WF-IHM-0090 |
| E-13 | mineur | `paths/revisions.yaml:127-148` (`abandonRevision`), `49-97` (`createRevision`) | 409 générique sans code ni condition ni exemple ; l'abandon ne porte pas de `lock_version` ni de 412, contrairement à `deleteNode` | WF-REV-0010, WF-IHM-0110 |
| E-14 | mineur | `paths/revisions.yaml:441-471` (`createCostStructure`) | 409 générique sans condition ni exemple ; la description ne dit pas qu'un différentiel naît copie de la structure principale, ce que `amendment_created` affirme | WF-REV-0100 |
| E-15 | mineur | `fixtures/api/revision_offer.json` (bloc `available_commands`, `lock_version` l. 91) | L'offre v1.0 n'y liste aucun export, quand l'item 100 de `revisions.json` à la même version les liste tous (#421) | WF-INTF-0050, WF-CYC-0110 |
| E-16 | mineur | `fixtures/api/revisions.json:330`, `revision_offer.json:91`, `structures_without_tasks.json`, `amendment_created.json` | Compteur initial incohérent : révision créée à 1, structure principale neuve à 0, différentiel neuf à 1 ; l'offre marquée reste à 1 quand le marquage « porte une version de plus » (#1352) | WF-IHM-0110 |
| E-17 | mineur | `fixtures/api/merge_revision_marked_refused.json:2,7` | Le résumé nomme `revision_marked`, la valeur `revision_draft` | WF-REV-0050 |
| E-18 | mineur | `schemas/revisions.yaml:236-268` (`RateUpdateProposal`), `fixtures/api/rate_update_none.json` | `target_year` facultatif et absent de l'exemple ; rien ne dit ce que la proposition rend des catégories déjà acceptées depuis la création (C-362) | WF-REV-0060 |
| E-19 | mineur | `paths/revisions.yaml:256` (`getRateUpdateProposal`) | « lorsque le référentiel a changé » : la spec présente l'écart quand l'année de référence diffère, que le référentiel ait changé ou non | WF-REV-0060 |
| E-20 | mineur | `schemas/revisions.yaml:218,388` (`RevisionMark.version_name`, `StructureMerge.version_name`) | Pas de `pattern: '\S'` sur le nom de version, contrairement à la convention et à `StructureCreate.label` | WF-ARC-0110, WF-DAT-0090 |
| E-21 | mineur | `paths/revisions.yaml:287-298` (`applyRateUpdate`) | Corps de requête anonyme, seul de la famille sans schéma nommé | — |
| E-22 | mineur | `schemas/revisions.yaml:288-290` (`CostStructure.is_merged`), `fixtures/api/structures.json:78` | Décrit pour le seul différentiel, mais vrai sur un devis propre fusionné par survenance | WF-RIS-0060 |
| E-23 | mineur | `paths/revisions.yaml:331-410` (`compareRevisions`) | Rien ne dit ce que reçoit une révision en cours donnée en `from`/`to` (refus ou lecture) | WF-REV-0080 |
| E-24 | mineur | `paths/revisions.yaml:195-250` (`designateReferenceRevision`), `schemas/revisions.yaml:223-234` | Écriture du projet sans `lock_version` ni 412, le projet en portant un (`reference_designated.json`, version 5) | WF-IHM-0110 |
| E-25 | mineur | `common.yaml:642-700` (`ProblemParams`) | `cycle`, `link`, `task`, `work_package_task`, `order_item_tasks`, partagés par la fusion, son compte rendu, les saisies et l'import, restent non typés malgré la règle de `ProblemParams` | WF-ARC-0110 |

### Constats

#### E-01 — La date de début de planning d'une structure n'existe pas dans le contrat
- **bloquant** ; `docs/api/components/schemas/revisions.yaml:277-308` (`CostStructure`), aucune
  opération de `docs/api/paths/revisions.yaml` ni d'`exchanges.yaml` ; **WF-REV-0100** : « Chaque
  structure porte une nature — principale, différentielle, ou devis de risque —, un libellé, une
  date de début de planning (WF-PLA-0020), et l'arbre de tâches » ; **WF-PLA-0020** : « Chaque
  structure de coûts porte une date de début de planning, saisie, qui vaut par défaut le jour de sa
  première création ; une structure reprise d'une révision marquée (WF-REV-0010) conserve la
  sienne. Une tâche en mode automatique sans prédécesseur commence à cette date […] L'import
  MS Project la lit dans la date de début du projet du fichier, et l'export l'y écrit » ; Vérif :
  « avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs automatiques ».
  **Contrat** : `CostStructure` porte `structure_id`, `revision_id`, `kind`, `label`, `risk_id`,
  `is_merged`, `available_commands`, `lock_version` — rien d'autre ; la seule mention est dans
  `NodeListMeta.scheduled_at` (`revisions.yaml:911-912` : « sa date de début de planning, sa création
  comprise ») ; aucune opération n'écrit une structure (`createCostStructure` crée, `mergeCostStructure`
  fusionne ; pas de `PATCH …/structures/{structure_id}`) ; `grep -i "début de planning|planning_start|
  start_on"` sur `docs/api/` ne rend que cette ligne.
- **Constat.** Un attribut que deux exigences F0 nomment, saisi par l'utilisateur, dont dépendent les
  dates de toute tâche automatique sans prédécesseur, le Vérif de WF-PLA-0020, l'import et l'export
  MS Project (WF-INTF-0040/0050), n'a ni champ ni écriture. Le front ne peut ni l'afficher ni la
  saisir ; le service ne peut pas la recevoir. Après le gel, il faudra un champ **et** une opération
  nouvelle, la plus coûteuse des modifications.
- **Proposition.** Un champ exigé sur `CostStructure` et une écriture, qui rend `NodesWritten`
  puisqu'elle redate la structure :
  ```yaml
  CostStructure:
    required: [..., planning_start_on]
    properties:
      planning_start_on:
        allOf: [{ $ref: ../common.yaml#/PlanningDate }]
        description: >-
          Date de début de planning de la structure, saisie, le jour de sa première création par
          défaut ; une structure reprise d'une révision marquée conserve la sienne (WF-PLA-0020,
          WF-REV-0100). Une tâche automatique sans prédécesseur y commence.
  StructureUpdate:
    type: object
    required: [planning_start_on, lock_version]
    properties:
      planning_start_on: { $ref: ../common.yaml#/PlanningDate }
      label: { type: string, minLength: 1, pattern: '\S', maxLength: 300 }
      lock_version: { $ref: ../common.yaml#/LockVersion }
  ```
  `PATCH /projects/{p}/revisions/{r}/structures/{s}` (`updateCostStructure`), sous `edit_planning`
  de la structure, 200 `NodesWritten` (les tâches redatées), 403/404/409/412/422, refus d'un jour
  sans heure travaillée par 422 `NON_WORKING_DAY` comme une date manuelle. À trancher : si
  l'auteur préfère porter la date sur `TaskFacet` de la première tâche, qu'il le dise ; la spec la
  met sur la structure.
- **DECISIONS.md** : aucune décision (`DECISIONS.md:6317` ne fait que la citer).

#### E-02 — Un seul écart de montant là où la spec en demande deux
- **majeur** ; `docs/api/components/schemas/revisions.yaml:1979-2014` (`RevisionComparison.amount_deltas[].delta`),
  `paths/revisions.yaml:331-410` (`compareRevisions`) ; **WF-REV-0080** : « ainsi que les écarts de
  montants budgétés et de montants réestimés, par nature de coût et par sous-projet » ; Vérif : « Les
  montants réestimés n'y diffèrent que par les lignes que le différentiel ajoute ou retire […] une
  ligne existante dont le différentiel ne modifie que le montant budgété ne présente aucun écart de
  montant réestimé ». **Contrat** : `required: [dimension, key, label, delta]`, `delta` décrit
  « L'écart de montant de la nature ou du sous-projet, à l'année de référence de chaque révision » ;
  `tools/src/wftools/mockcomparisons.py:51-82` (`_deltas`) le calcule sur `row.amounts.base`, le
  montant à l'année de référence, ni le budgété ni le réestimé ; `fixtures/api/comparison.json`
  rend 3 300,00 pour « Main-d'œuvre », somme des écarts de `reestimated_amount` (180 + 120 + 3 000)
  quand l'écart budgété serait 3 000.
- **Constat.** Le Vérif distingue explicitement les deux écarts ; le contrat n'en porte qu'un, d'une
  troisième grandeur. Un front ne peut pas présenter « l'écart budgété » d'un avenant, premier usage
  nommé par le motif (« instruire un avenant »). Renommer ou dédoubler `delta` après le gel change le
  schéma et la sémantique de la valeur.
- **Proposition.** `required: [dimension, key, label, budgeted_delta, reestimated_delta]`, chacun un
  `Money`, « révision comparée moins révision de base » (sens de `DECISIONS.md:1546`) ; retirer `delta`
  ou le garder comme écart du montant à l'année de référence s'il sert à la grille, en le nommant
  `base_delta`. Régénérer `comparison*.json` et `volume/comparison_volume.json`.
- **DECISIONS.md** : `DECISIONS.md:1546-1550` (« la spécification ne donne aucun sens ») ne tranche
  que le signe, non la grandeur ; `6664-6680` la fenêtre. Aucune décision sur l'unicité du delta.

#### E-03 — Le taux d'inflation et la probabilité de gain conservés ne sont pas des attributs lisibles de la révision
- **majeur** ; `docs/api/components/schemas/revisions.yaml:13-63` (`Revision`), `52` (`snapshot`,
  nullable, non exigé), `163-173` (`RevisionSnapshot`) ; `paths/revisions.yaml:3-9` (`listRevisions`),
  `99-104` et `109` (`getRevision` : « Révision, avec les valeurs de référentiel et les paramètres
  conservés ») ; **WF-REV-0090** : « Une révision porte un nom de version, une description facultative,
  son état […], la date de son marquage, son année de référence, le taux d'inflation et la probabilité
  de gain qu'elle conserve » ; **WF-REV-0070** : « L'historique des révisions marquées […] : nom de
  version, description, date de marquage, année de référence, taux d'inflation et probabilité de gain
  conservés (WF-REV-0090) », Vérif : « L'année de référence, le taux d'inflation et la probabilité de
  gain affichés pour une révision marquée sont ceux conservés à son marquage ». **Contrat** :
  `inflation_rate` et `win_probability` ne vivent que dans `RevisionSnapshot` ; `snapshot` est `null`
  dans les 13 exemples qui rendent une révision (`revisions.json`, `revision_marked.json`,
  `revision_offer.json`, `revision.json`, …), y compris le témoin de `getRevision` dont la description
  promet l'instantané ; aucune description ne dit quand `snapshot` est nul (liste ? brouillon ?) ;
  `listRevisions` cite WF-REV-0090 mais énumère les attributs sans ces deux-là.
- **Constat.** L'historique (WF-REV-0070) doit afficher ces deux valeurs par révision ; avec le
  contrat, il faudrait un `getRevision` par ligne, ou `snapshot` dans la liste, ce que rien ne dit. La
  décision `DECISIONS.md:1187-1194` a sorti `reference_year` de l'instantané pour exactement cette
  raison (« Écarté : un champ dans `RevisionSnapshot`, où il n'aurait été lu qu'avec l'instantané
  entier, quand l'historique des révisions le présente ») ; le même raisonnement vaut pour les deux
  autres paramètres que WF-REV-0090 liste au même rang. Par ailleurs, un schéma jamais exemplifié ne
  valide rien (README : les mocks « ne valident plus rien »).
- **Proposition.** Sur `Revision`, `inflation_rate` et `win_probability` exigés, `Percent`, en lecture
  seule, « conservés par la révision (WF-REV-0030, WF-REV-0090) » ; `RevisionSnapshot` réduit à
  `employed_reference` (ou les garde en double, en le disant) ; une phrase sur `snapshot` : « nul dans
  `listRevisions` ; rendu par `getRevision` » ; un exemple de `getRevision` avec l'instantané
  (`revision_marked`, les rôles, calendriers, catégories et taux du témoin).
- **DECISIONS.md** : `DECISIONS.md:5024` constate que « `Revision.snapshot` [est] nul partout » sans
  le décider ; `1187-1194` pour `reference_year`.

#### E-04 — La fusion marque sans permettre la description
- **majeur** ; `docs/api/components/schemas/revisions.yaml:369-398` (`StructureMerge`, propriétés
  `confirmed`, `version_name`, `main_structure_lock_version`, `amendment_lock_version`) ;
  **WF-REV-0050** : « La fusion s'applique à la révision en cours et la marque dans la même
  opération ; elle exige à ce titre un nom de version, comme tout marquage (WF-REV-0020) » ;
  **WF-REV-0020** : « Le marquage d'une révision exige un nom de version, et permet d'y joindre une
  description » ; **WF-REV-0090** Vérif : « Le nom de version et la description sont ceux saisis au
  marquage ». **Contrat** : `RevisionMark` porte `description` (`revisions.yaml:219-220`),
  `StructureMerge` non.
- **Constat.** La révision produite par un avenant est précisément celle dont les hypothèses
  méritent une description (motif de WF-REV-0020). Sans champ, l'utilisateur ne peut jamais la
  renseigner : une révision marquée ne se modifie plus (WF-DAT-0020). Ajouter un champ facultatif
  après le gel est compatible, mais l'écran de confirmation de la fusion est à construire maintenant.
- **Proposition.** `StructureMerge.description: anyOf [string, null]`, « jointe à la révision marquée,
  comme au marquage (`RevisionMark.description`) ».
- **DECISIONS.md** : aucune décision (`5614-5650`, `8170-8215` ne parlent que du nom de version).

#### E-05 — Le nom de version déjà employé n'a pas de refus déclaré sur la fusion
- **majeur** ; `docs/api/paths/revisions.yaml:588-610` (409 de `mergeCostStructure`), `529-586`
  (description, aucun mot sur l'unicité) ; **WF-REV-0020** Vérif : « Le marquage d'une révision sous
  un nom de version déjà employé dans le projet est refusé » ; **WF-REV-0050** : « exige à ce titre un
  nom de version, comme tout marquage ». **Contrat** : le 409 de `markRevision` (`150-193`) déclare
  `ALREADY_EXISTS`, `fields` sur `/version_name`, `conflicting_object_id` ; celui de la fusion ne
  déclare que `STATE_FORBIDS_OPERATION` ; la tâche de fond ne liste pas ce motif d'échec non plus.
- **Constat.** Un implémenteur du service ne sait pas s'il refuse en synchrone (409 au dépôt) ou en
  échec de la tâche (`problem.code`), ni ce que le front doit afficher sur le champ. L'unicité étant
  déclarée en base (WF-DAT-0090), le contrôle synchrone est le seul qui évite une fusion qui aurait
  créé la révision en cours (#790) pour échouer au marquage.
- **Proposition.** Au 409 de `mergeCostStructure` : « Ou nom de version déjà employé par une révision
  marquée du projet : `ALREADY_EXISTS`, `fields` désignant `/version_name`,
  `fields[].params.conflicting_object_id` la révision qui le porte, comme `markRevision`
  (WF-REV-0020) ; jugé au dépôt, rien n'est mis en file » ; un exemple (`merge_version_name_taken`,
  « Référence » repris).
- **DECISIONS.md** : aucune décision.

#### E-06 — Où vit l'historique annulable
- **majeur** ; `docs/api/paths/revisions.yaml:1646-1700` (`undoLastChange` : « Annule les
  modifications de la session », 409 « l'historique de la session est vide »), `1702-1745`
  (`redoLastUndo`), `schemas/revisions.yaml:1789` (`remaining_depth`) ; **WF-IHM-0110** : « L'historique
  annulable couvre au moins les cinquante dernières modifications faites par l'utilisateur dans la
  page ouverte ; il est tenu par le front, et ne survit ni à la fermeture ni au rechargement de la
  page. » Motif : « Une annulation est une modification comme une autre : elle passe par l'API, subit
  les mêmes règles et s'inscrit dans les colonnes d'audit ».
- **Constat.** Un `POST /undo` sans corps suppose un historique tenu par le serveur, par session,
  avec sa profondeur (`remaining_depth`) et ses refus (« historique vide »). La spec dit l'inverse :
  l'historique est au front, par page, et c'est le front qui rejoue l'inverse de chaque saisie par
  l'API ordinaire — ce qui rend naturels « ne survit ni à la fermeture ni au rechargement » et « dans
  la page ouverte » (deux grilles ouvertes de la même révision ont chacune leur pile). Les deux
  conceptions tiennent, mais pas ensemble : avec le contrat, le serveur doit garder une pile par
  session et par révision, décider ce qu'est une « session » (jeton ? onglet ?), et sa durée de vie ;
  avec la spec, `/undo` et `/redo` sont inutiles et un front qui rejoue a besoin, pour chaque écriture,
  de l'état antérieur que `NodesWritten` ne rend pas. Avant le gel, il faut trancher : garder les
  opérations et faire corriger la spec (« tenu par le serveur, par session de travail ») ; ou les
  retirer.
- **Proposition.** Question à l'auteur. Si les opérations restent : décrire ce qu'est la session
  (le jeton `bearer`), que la pile est par révision et par utilisateur, qu'elle ne survit pas au
  marquage ni à l'abandon, et sa profondeur (« au moins cinquante ») ; et faire corriger WF-IHM-0110.
- **DECISIONS.md** : aucune décision sur l'emplacement de l'historique (grep « historique », « session »,
  « tenu par » ; `1430-1436` et `8008-8026` ne parlent que des risques et des refus #732/#795).

#### E-07 — Le refus d'une annulation ne nomme ni son code ni l'objet en conflit
- **majeur** ; `docs/api/paths/revisions.yaml:1672-1676` (409 d'`undoLastChange` : « Une modification
  postérieure porte sur le même objet, ou l'historique de la session est vide (WF-IHM-0110) »),
  `1719-1722` (`redoLastUndo`) ; `common.yaml:409` (`UNDO_CONFLICT`, sous « 409 ») ; **WF-IHM-0110** :
  « Elle est refusée, en nommant l'objet en conflit, lorsqu'une modification postérieure porte sur le
  même objet » ; Vérif : « L'annulation d'une modification qu'un autre contributeur a depuis reprise
  est refusée en nommant l'objet en conflit ».
- **Constat.** Les deux premiers cas du 409 n'ont ni code (`UNDO_CONFLICT` existe dans `ErrorCode`
  mais aucune opération ne le cite, aucun `params` ne le décrit dans `Problem.params`) ni paramètre
  nommant l'objet (nœud ? risque ?), ni exemple ; seuls les cas #732/#795 sont décrits. Le front ne
  peut pas rendre la phrase que la spec exige, et le service ne sait pas quel code émettre pour un
  historique vide (409 ? 404 ?).
- **Proposition.** Au 409 : « `UNDO_CONFLICT`, `params.conflicting_node_id` ou
  `params.conflicting_risk_id` et `params.conflicting_label`, l'objet qu'une modification postérieure
  a repris (WF-IHM-0110) ; un historique vide, `STATE_FORBIDS_OPERATION`, `params.missing_condition` à
  une condition nouvelle `undo_history_not_empty` » (ou retirer `UNDO_CONFLICT` si la décision E-06
  retire les opérations) ; deux exemples (`undo_conflict`, `undo_history_empty`) ; déclarer les
  paramètres dans `Problem.params`.
- **DECISIONS.md** : aucune décision (`3575` ne concerne que le 412).

#### E-08 — Une annulation est une écriture de grille qui ne rend pas ce qu'une écriture rend
- **majeur** ; `docs/api/components/schemas/revisions.yaml:1757-1790` (`UndoResult` : `undone.kind`
  chaîne libre, `node_ids`, `risk_ids`, `remaining_depth`) ; README « Conventions » : « Toute écriture
  de grille — cellule, collage, déplacement, création, liaison, avancement, réestimation, inscription,
  suppression — rend `NodesWritten` : nœuds écrits, ancêtres recalculés, tâches redatées, totaux de la
  structure, compteur de la structure » ; **WF-IHM-0110** : « Une annulation est une modification
  comme une autre ». **Contrat** : `CostStructure.lock_version` « avance à chaque écriture dans son
  arbre » (`revisions.yaml:299-307`), `NodesWritten.structure_lock_version` « pour que la grille le
  garde à jour ».
- **Constat.** Après une annulation, le compteur de la structure a avancé et la grille ne le connaît
  pas : sa saisie suivante est refusée par 412 ; les totaux, les ancêtres et les dates recalculés ne
  sont pas rendus, la grille doit relire la structure entière (dix mille nœuds, §4.6.2) pour un
  Ctrl+Z. `undone.kind` en chaîne libre contredit « jamais une phrase » (WF-ARC-0110) : le front ne
  peut pas le rendre par son catalogue.
- **Proposition.** `UndoResult` : `written: { $ref: '#/NodesWritten' }` (nul pour une saisie de risque),
  `undone.kind` en énumération (`cell`, `node_create`, `node_delete`, `node_move`, `paste`, `link`,
  `progress`, `remaining`, `tracking`, `risk_create`, `risk_update`, `risk_review`, `risk_delete`),
  `remaining_depth` gardé. Même forme pour le rétablissement.
- **DECISIONS.md** : aucune décision (`1435`, `4903` n'ajoutent que `risk_ids`).

#### E-09 — `createCostStructure` crée un devis propre que `createRisk` crée déjà
- **majeur** ; `docs/api/paths/revisions.yaml:441-471` (`createCostStructure`, « Créer un différentiel
  ou un devis de risque »), `schemas/revisions.yaml:355-367` (`StructureCreate.kind` enum
  `[amendment, risk]`, `risk_id` nullable sans règle) ; `paths/risks.yaml:60-61` (`createRisk` : « La
  création ouvre la structure de coûts propre du risque et sa ligne de provision ») ; **WF-REV-0100** :
  « Une structure différentielle est créée par un utilisateur habilité pour préparer un avenant […]
  Une structure propre de risque existe tant que le risque existe » ; **WF-RIS-0030** : « dans une
  structure de coûts qui lui est réservée ».
- **Constat.** Deux chemins créent le même objet ; pour `kind: risk`, rien ne dit si `risk_id` est
  exigé, ce qu'un risque qui a déjà sa structure reçoit (409 `ALREADY_EXISTS` ?), ni ce qu'est une
  structure `risk` sans `risk_id`. Un implémenteur du service doit inventer la règle ; un front ne
  sait pas quel chemin emprunter. Restreindre l'énumération après le gel est incompatible.
- **Proposition.** `StructureCreate.kind: { const: amendment }` (ou `enum: [amendment]`), retirer
  `risk_id` de `StructureCreate`, résumé « Ouvrir un différentiel » ; description : « Le devis propre
  d'un risque naît avec lui (`createRisk`, WF-RIS-0030) et disparaît avec lui ; la structure
  principale existe dès la révision ». Sinon, écrire la règle (`risk_id` exigé pour `risk`, 409
  `ALREADY_EXISTS` sur `/risk_id`).
- **DECISIONS.md** : aucune décision (`StructureCreate` absent ; `39` cite seulement les trois
  natures).

#### E-10 — Les compteurs du compte rendu sans révision en cours ne sont pas ceux de la révision marquée
- **majeur** ; `fixtures/api/structure_merge_report_without_current_revision.json:4-5`
  (`main_structure_lock_version: 1`, `amendment_lock_version: 2`) ; `schemas/revisions.yaml:412-419`
  (`creates_current_revision` : « ses compteurs sont ceux de ses structures, que le marquage a
  figés ») ; `fixtures/api/structures_amendments.json:34` (principale 211 de la révision 101,
  `lock_version: 3`) et `:82` (avenant 2, structure 213, `lock_version: 1`). **WF-REV-0050**.
- **Constat.** Le compte rendu d'une fusion demandée sur la référence 101 doit porter 3 et 1 ; il
  porte 1 et 2, qui sont les compteurs des structures 201 et 203 de la révision courante 102
  (`structures.json`, `structure_merge_report.json`). Un test du faux back ou du front construit sur
  cet exemple confirmerait avec des compteurs que la révision marquée ne porte pas, et un service qui
  le sert recevrait un 412 de son propre exemple. Exemple écrit à la main (pas de `description`
  « engendré »), d'où la dérive.
- **Proposition.** `main_structure_lock_version: 3`, `amendment_lock_version: 1` ; un test de
  `test_mockversions.py` tenant les compteurs d'un compte rendu à ceux de `structures*` de la
  révision du chemin.
- **DECISIONS.md** : `8170-8180` dit la règle (« ses compteurs sont ceux de ses structures, que le
  marquage a figés ») ; l'exemple la contredit.

#### E-11 — Les taux conservés sont des objets vivants, non des images
- **majeur** (bas) ; `docs/api/components/schemas/revisions.yaml:175-193` (`EmployedReference` :
  `resource_roles` → `ResourceRoleImage`, `calendars` → `CalendarImage`, `cost_categories` →
  `CostCategoryImage`, `hourly_rates` → `reference.yaml#/HourlyRate`) ; `reference.yaml:633-644`
  (`HourlyRate` exige `audit`, `lock_version`) ; **WF-REV-0030** : « Une révision conserve les valeurs
  du référentiel employées […] et taux horaires » ; §4.4.1 : « quatre tables images des tables du
  référentiel — rôle, calendrier, catégorie, taux » (`revision_rate`).
- **Constat.** La description même d'`EmployedReference` dit « Images des objets du référentiel
  employés, figées au marquage : sans les commandes qu'un objet lu aujourd'hui porte » ; un `HourlyRate`
  conservé porterait pourtant l'`audit` et le `lock_version` du taux du référentiel, qui bougent
  après le marquage, ou ceux de la ligne `revision_rate`, que personne n'écrit. Le même concept est
  typé différemment des trois autres valeurs ; aucun exemple ne le montre (E-03).
- **Proposition.** `HourlyRateImage { required: [cost_category_id, year, amount] }` dans
  `reference.yaml`, aux côtés des trois autres images.
- **DECISIONS.md** : aucune décision (`HourlyRateImage` absent).

#### E-12 — Les 409 de `markRevision` et les conditions de `mark`, `abandon`, `designate_reference`
- **mineur** ; `docs/api/paths/revisions.yaml:180-190` (409 : « Ou révision déjà marquée
  (WF-REV-0020). Rien n'est écrit. ») ; `schemas/revisions.yaml:65-150` (`RevisionCommand`) ;
  **WF-REV-0020**, **WF-IHM-0090**. **Contrat** : le second cas du 409 n'a ni code ni condition (le
  régime des écritures de la révision, `DECISIONS.md:8192-8196`, est `STATE_FORBIDS_OPERATION`,
  `revision_draft`) ; `no_background_task_running` pendant un marquage qui court
  (`revision_marking.json` : `mark!no_background_task_running`) n'est pas déclaré ; aucun exemple ni
  du nom pris ni de la révision marquée ; la description de `RevisionCommand` détaille les conditions
  de `merge_structure`, `declare_risk`, `generate_skeleton`, `edit_risks`, pas celles de `mark`,
  `abandon` ni `designate_reference` (que les exemples montrent : `revision_marked`,
  `revision_has_tasks_and_lines`, `reference_correctable`, `no_background_task_running`).
- **Proposition.** Au 409 : « Ou révision déjà marquée, ou marquage qui court : `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` à `revision_draft` ou `no_background_task_running`, dans l'ordre de la
  commande `mark` » ; deux exemples (`mark_version_name_taken`, `mark_revision_marked`) ; un alinéa
  de `RevisionCommand` pour `mark` (`revision_draft`, `no_background_task_running`,
  `project_not_terminal`), `abandon` (idem) et `designate_reference` (`revision_marked`,
  `revision_has_tasks_and_lines`, `reference_correctable`, `no_background_task_running`).
- **DECISIONS.md** : `6814-6820` (ordre du 409 de la désignation), rien sur `mark`.

#### E-13 — `abandonRevision` et `createRevision` : refus d'état non nommés, abandon sans compteur
- **mineur** ; `docs/api/paths/revisions.yaml:127-148` (`abandonRevision`, 409 générique
  `Conflict`, aucun exemple, pas de `lock_version`, pas de 412), `49-97` (`createRevision`, 409
  `CURRENT_REVISION_EXISTS` seul) ; **WF-REV-0010**, **WF-IHM-0110** ; README « `lock_version` sur
  les écritures concurrentes ». **Contrat** : `deleteNode` (`912-935`) exige `lock_version` en
  paramètre et déclare le 412 ; l'abandon, qui supprime dix mille lignes, non ; la description dit
  « Refusé sur une révision marquée (WF-DAT-0020) » sans code (403 `REVISION_MARKED` ou 409
  `revision_draft` ?) ; `abandon!no_background_task_running` dans `revision_marking.json` n'est pas
  déclaré ; `createRevision` pendant un import qui crée la révision (`no_background_task_running` du
  projet) n'a pas de refus décrit.
- **Proposition.** `abandonRevision` : paramètre `lock_version` (query, exigé) et 412, comme
  `deleteNode` ; 409 : « `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `revision_draft` ou
  `no_background_task_running`, dans l'ordre de la commande `abandon` » ; un exemple.
  `createRevision` 409 : « ou un traitement de fond qui crée la révision en cours,
  `STATE_FORBIDS_OPERATION`, `no_background_task_running` (`ProjectCommand.create_revision`) ».
- **DECISIONS.md** : `6808-6811` (C-363, irréversibilité) ; rien sur le compteur ni les codes.

#### E-14 — `createCostStructure` : refus et naissance d'un différentiel non décrits
- **mineur** ; `docs/api/paths/revisions.yaml:441-471` (409 générique, aucun exemple) ;
  `fixtures/api/amendment_created.json` (résumé : « copie de la structure principale à sa création ») ;
  **WF-REV-0100**. **Contrat** : rien ne dit qu'un différentiel naît copie de la structure
  principale de la même révision (ce que `nodes_amendment` et le compte rendu de fusion supposent :
  `NodeDifference` « absent de la structure de base — la principale pour un différentiel »), ni les
  conditions du 409 (`revision_draft`, `no_background_task_running`, `project_not_terminal`, dans
  l'ordre de `create_structure`), ni si le libellé est unique.
- **Proposition.** Description : « Un différentiel naît copie de la structure principale de sa
  révision, à son compteur 1, chaque nœud marqué `unchanged` (WF-REV-0100, C-361) » ; 409 nommé comme
  ailleurs, un exemple (`structure_create_revision_marked`).
- **DECISIONS.md** : `6855-6875` (#1211, coexistence) ; rien sur la copie.

#### E-15 — L'offre v1.0 sans ses exports dans `revision_offer.json`
- **mineur** ; `fixtures/api/revision_offer.json` (bloc `available_commands`, 9 commandes ; `grep -c
  export_` = 0 ; `lock_version: 1` l. 91) contre `fixtures/api/revisions.json:223-330` (même révision
  100, même version 1, 13 commandes dont les quatre exports) ; `schemas/revisions.yaml:85-91`
  (`RevisionCommand` : « sur une révision marquée […] il reste disponible ») ; **WF-INTF-0050**,
  **WF-CYC-0110**.
- **Constat.** Deux lectures de la même révision à la même version ne rendent pas le même contenu
  (#421, `DECISIONS.md:6852`) ; `test_mockversions.py:117` ne compare que `status` et `marked_at`, et
  laisse passer. Le résumé ne dit pas un appelant sans permission de consulter. Exemple écrit à la
  main.
- **Proposition.** Ajouter les quatre exports à `revision_offer.json` (ou dire l'appelant) ; étendre
  la clé du test aux commandes.
- **DECISIONS.md** : `6852` (#421 pour les révisions).

#### E-16 — Le compteur initial n'a pas une seule règle dans les exemples
- **mineur** ; `fixtures/api/revisions.json:330` et `revision_offer.json:91` (offre 100 marquée,
  `lock_version: 1`), `revision_created.json` (103 créée « à sa première version », 1),
  `rate_update_applied.json` / `revisions.json:220` (101 : créée 1, taux 2, marquée 3),
  `structures_without_tasks.json` (principale neuve 207 : 0, « son compteur à 0 »),
  `amendment_created.json` (différentiel neuf 213 : 1, « à sa première version ») ; **WF-IHM-0110** ;
  `DECISIONS.md:6852-6854` (#1352 : « son marquage porte une version de plus »).
- **Constat.** Si une révision naît à 1 et que le marquage ajoute 1, l'offre marquée sans autre
  écriture devrait être à 2 ; si une structure neuve naît à 0, un différentiel neuf devrait l'être
  aussi. Un implémenteur ne peut pas lire dans les exemples la valeur initiale de `LockVersion`
  (`common.yaml:92-103` ne la dit pas).
- **Proposition.** Une phrase dans `LockVersion` (« une création rend 1 » ou « 0 ») ; aligner
  `revision_offer`/`revisions` (offre à 2) ou `structures_without_tasks` (0 → 1) ; un test
  d'incrément du marquage dans `test_mockversions.py`.
- **DECISIONS.md** : `6852-6854` (#1352), `5257` (« son compteur à 0 ») : les deux constats, pas la
  règle.

#### E-17 — Résumé et valeur en désaccord dans `merge_revision_marked_refused.json`
- **mineur** ; `fixtures/api/merge_revision_marked_refused.json:2` (« la condition que la commande
  `merge_structure` de la référence dit manquer (revision_marked) ») et `:7`
  (`"missing_condition": "revision_draft"`) ; **WF-REV-0050**. La valeur est la bonne
  (`revisions.json:113-220` : `merge_structure!revision_draft`) ; le résumé nomme la condition
  inverse.
- **Proposition.** `revision_marked` → `revision_draft` dans le résumé.
- **DECISIONS.md** : `8192-8196` (le 409 nomme `revision_draft`).

#### E-18 — `RateUpdateProposal` : `target_year` facultatif, catégories acceptées non dites
- **mineur** ; `docs/api/components/schemas/revisions.yaml:236-268` (`required: [categories]`,
  `target_year` décrit comme « l'année de référence de la révision créée ») ;
  `fixtures/api/rate_update_none.json:4` (sans `target_year`) ; `paths/revisions.yaml:275-281`
  (« Une mise à jour refusée à la création de la révision s'accepte ensuite », C-362) ;
  **WF-REV-0060** : « la présentation reste proposée depuis la révision en cours tant qu'elle n'est
  pas marquée, et une mise à jour refusée peut y être acceptée ensuite ».
- **Constat.** L'année visée existe toujours (celle de la révision) ; la rendre facultative force le
  front à la relire sur la révision. Après `applyRateUpdate` sur deux catégories, rien ne dit si la
  proposition les liste encore (à taux égaux ?), les omet, ou les marque acceptées : l'écran de la
  révision en cours ne sait pas ce qu'il propose encore.
- **Proposition.** `required: [target_year, categories]` ; `rate_update_none.json` avec
  `target_year: 2026` ; une phrase : « Une catégorie dont le taux de la révision est déjà celui de
  l'année visée n'est plus proposée » (ou un `accepted: boolean` par catégorie).
- **DECISIONS.md** : `6788-6791`, `6810-6811` (C-362) ne disent pas le contenu de la proposition
  après acceptation.

#### E-19 — « lorsque le référentiel a changé »
- **mineur** ; `docs/api/paths/revisions.yaml:256` (`getRateUpdateProposal` : « Présenté à la création
  d'une révision lorsque le référentiel a changé ») ; **WF-REV-0060** : « Lorsqu'elle diffère de celle
  de la révision précédente, Waterfall présente, catégorie par catégorie, le taux conservé et le taux
  du référentiel pour la nouvelle année ». Le schéma (`revisions.yaml:239-242`) dit juste. Un
  référentiel inchangé à année différente présente quand même l'écart (taux de 2027 saisi avant).
- **Proposition.** « Présenté quand l'année de référence de la révision diffère de celle de la
  révision copiée (WF-REV-0060) ».
- **DECISIONS.md** : aucune.

#### E-20 — Nom de version sans `pattern: '\S'`
- **mineur** ; `docs/api/components/schemas/revisions.yaml:218` (`RevisionMark.version_name:
  { type: string, minLength: 1, maxLength: 100 }`), `:388` (`StructureMerge.version_name`, idem) ;
  README : « Un libellé, un nom ou un code reçu porte au moins un caractère qui n'est pas un blanc
  (`pattern: '\S'`) » ; `StructureCreate.label` (`:365`) le porte. Un nom de version fait de blancs
  serait accepté et unique en base (WF-DAT-0090).
- **Proposition.** `pattern: '\S'` sur les deux.
- **DECISIONS.md** : aucune.

#### E-21 — Corps anonyme d'`applyRateUpdate`
- **mineur** ; `docs/api/paths/revisions.yaml:287-298` (schéma en ligne `{ cost_category_ids,
  lock_version }`) ; toutes les autres écritures de la famille ont un schéma nommé (`RevisionCreate`,
  `RevisionMark`, `ReferenceDesignation`, `StructureCreate`, `StructureMerge`). Le client engendré et
  les modèles Pydantic reçoivent un type sans nom.
- **Proposition.** `RateUpdateApply` dans `schemas/revisions.yaml`, après `RateUpdateProposal`.
- **DECISIONS.md** : aucune.

#### E-22 — `is_merged` vrai sur un devis propre
- **mineur** ; `docs/api/components/schemas/revisions.yaml:288-290` (« Vrai lorsque le différentiel a
  été fusionné dans la principale (WF-REV-0050) ») ; `fixtures/api/structures.json:73-92` (structure
  205, `kind: risk`, `is_merged: true`, l. 78 ; résumé : « dont la survenance a fusionné le devis
  propre ») ; **WF-RIS-0060**.
- **Proposition.** « …ou lorsque le devis propre d'un risque a été fusionné par sa survenance
  (WF-RIS-0060) ; faux pour la structure principale ».
- **DECISIONS.md** : aucune.

#### E-23 — Comparer une révision en cours
- **mineur** ; `docs/api/paths/revisions.yaml:331-410` (résumé « Comparer deux révisions marquées »,
  404/422 seuls refus déclarés) ; **WF-REV-0080** (F1) : « Deux révisions marquées d'un même projet
  peuvent être comparées ». Rien ne dit ce que reçoit `to_revision_id` = révision en cours : 409
  `STATE_FORBIDS_OPERATION` `revision_marked`, ou une lecture (utile à « l'écart à la référence » du
  brouillon, mais hors spec). Un implémenteur choisira seul.
- **Proposition.** Déclarer le 409 (`revision_marked`) ou admettre la révision en cours et le dire.
- **DECISIONS.md** : aucune.

#### E-24 — La désignation écrit le projet sans son compteur
- **mineur** ; `docs/api/paths/revisions.yaml:195-250` (`designateReferenceRevision`, pas de 412),
  `schemas/revisions.yaml:223-234` (`ReferenceDesignation` : `revision_id`, `confirmed`) ;
  `fixtures/api/reference_designated.json` (`Project.lock_version: 5`, « Sa version est la
  cinquième ») ; README : « `lock_version` sur les écritures concurrentes, refus par 412 ».
- **Constat.** Toute autre écriture du projet porte son compteur ; deux chefs de projet qui désignent
  v2 et v3 en même temps ne sont départagés que par le 409 `reference_correctable`, qui ne joue que si
  une révision a été marquée entre-temps. Compatible à ajouter après le gel (champ facultatif), mais
  la convention dit « et rien d'autre ».
- **Proposition.** `ReferenceDesignation.lock_version` exigé (celui du projet) et 412
  `PreconditionFailed` ; ou une décision qui écarte le compteur ici, en disant pourquoi.
- **DECISIONS.md** : `10` (le `PUT`), rien sur le compteur.

#### E-25 — Paramètres partagés des refus de fusion non typés
- **mineur** ; `docs/api/components/common.yaml:642-700` (`ProblemParams` : « Ceux que plusieurs refus
  partagent sont déclarés ici, facultatifs et typés » ; déclarés : `state_enum`, `resource_roles`,
  `projects`, `tasks`, `estimate_lines`, `subproject`, `columns`, `missing_columns`) ; `Problem.params`
  (`common.yaml:238-284`) décrit en prose `work_package_task`, `order_item_tasks`, `task`, `cycle`,
  `link`, chacun `{ node_id, label }`, partagés par `mergeCostStructure`,
  `StructureMergeReport.refusals`, `ImportReport.refusals`, `setPredecessors`, `moveNodes`,
  `updateTaskFacet` ; **WF-ARC-0110**.
- **Constat.** Le client engendré reçoit `unknown` pour les paramètres que la fusion, son compte
  rendu et les saisies rendent tous de la même forme ; la règle que `ProblemParams` s'est donnée
  n'est pas suivie pour eux. Additif, mais autant le faire avant le gel.
- **Proposition.** `ProblemNamedTask { node_id: Uuid|null, label }` ; `task`, `work_package_task`
  (objet), `order_item_tasks`, `cycle`, `link` (tableaux) dans `ProblemParams`.
- **DECISIONS.md** : `768` point 3 (le principe des paramètres typés) ; rien sur ceux-ci.

### Ce qui est juste

- **WF-REV-0050 et la fusion** (#790, EP-14/L42s, #788, #789, #1582) : compte rendu préalable lu
  seul, confirmation portant les deux compteurs et refusée par 412 sur le compteur du différentiel
  (#296), tâche de fond une seule opération, création de la révision en cours par copie quand il n'y en
  a pas (`creates_current_revision`, `merge_structure` sur la dernière marquée seulement,
  `may_create_revision` en 409), taux conservés projetés (WF-REV-0060 mot pour mot), horizon et
  boucle (`LINK_CYCLE` sans jugement d'horizon), `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`,
  `TASK_WITHOUT_WORKING_HOURS`, tâche démarrée conservée et terminée (`kept` + `completed_tasks`,
  `completed_on` nul avant application), provision déplacée (`updated`/`parent`) : contrat, fixtures
  (`structure_merge_report*`, `task_merge_*`, `merge_*`) et décisions concordent — hors E-10.
- **WF-REV-0010/0020/0040/0090/0100** : unicité de la révision en cours (`CURRENT_REVISION_EXISTS`),
  `RevisionStatus` `draft`/`marked`, `version_name` nul en brouillon et unique au marquage
  (`ALREADY_EXISTS` sur `/version_name` de `markRevision`), `marked_at`, `is_reference`,
  `reference_year` (#381), désignation parmi les marquées avec `revision_marked` →
  `revision_has_tasks_and_lines` → `REFERENCE_NOT_CORRECTABLE` dans l'ordre de la commande, passage à
  En cours (WF-CYC-0030), `StructureKind` `main`/`amendment`/`risk` conforme au glossaire et au
  §4.4.1 (`cost_structure`), plusieurs différentiels non fusionnés (#1211), les commandes des
  structures par phase (`project_before_in_progress`, `project_in_progress`). `revisions.json` : ordre
  décroissant, états et versions cohérents entre `revisions`, `revisions_marked`,
  `revisions_designation_open`, `revision_marked`, `rate_update_applied` (#1352) ; le régime 403
  (saisie de grille) / 409 `revision_draft` (écriture de la révision) est décidé (`DECISIONS.md:8192`).
- **WF-IHM-0110** : ce qui est annulable (grilles et risques) et ce qui ne l'est pas (import,
  marquage, fusion, désignation, survenance, abandon — C-363, exclusion), les refus #732/#795 dans
  l'ordre de l'énumération, les exemples `undo_risk_without_task`, `redo_risk_category_deactivated`.
  **WF-REV-0060** : `getRateUpdateProposal`/`applyRateUpdate`, `source` `reference_rate`/
  `inflated_previous`, `rate_update`, `rate_update_applied`, 409 `revision_draft`
  (`RevisionCommand.apply_rate_update` est à L6). **Squelette** : conditions, 409
  `main_structure_without_tasks`, `NodesWritten`. `ImportDifference`/`ReportRefusal`/
  `ImportCompletedTask` partagés : `lineage_id` nul pour un ajout, `link` par le successeur avec
  `predecessor_label`, `fields` en `NodeColumn` + `parent`, `kept` sans `fields`, `work_breakdown_label`
  pour le retrait d'une tâche rattachée — prêts pour la survenance (US-0680).

### Doutes

- **Modification du devis propre d'un risque survenu** : `structures.json` (205, `is_merged: true`)
  garde `edit_planning`/`edit_estimate` disponibles ; WF-RIS-0030 dit « modifiable tout au long du
  projet », WF-RIS-0060 qu'aucune transition ne part de survenu. Famille risques ; non tranché ici.
- **`listCostStructures` en tableau nu** sans `items`/`meta` : une structure par risque, quelques
  différentiels — les volumes du §4.6.2 ne nomment pas les risques par projet ; je ne le signale pas,
  mais c'est la seule liste de la famille hors enveloppe.
- **`/revisions/comparison` sous `/revisions/{revision_id}`** : `comparison` n'est pas un UUID, les
  routeurs départagent ; aucune décision ne le dit, aucun problème constaté.
- **Le `delta` par `subproject` pour l'offre sans sous-projet** (`unassigned` 584 350,00) : cohérent
  avec le résumé ; je n'ai pas recalculé les écarts par sous-projet ligne à ligne.
- **WF-REV-0070** parle de l'historique des révisions **marquées** ; `listRevisions` liste aussi la
  révision en cours, avec le filtre `status`. Conforme à WF-IHM-0130 ; pas un constat.

## Annexe F — Arbre commun : nœuds et écritures de grille


**Lu** : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/revisions.yaml` lignes 634–1644 (`listNodes`, `createNode`, `resolveRowNumber`, `deleteNode`, `getComputedValueDependencies`, `updateTaskFacet`, `updateEstimateLine`, `setPredecessors`, `setTaskProgress`, `setLineRemaining`, `setNodeTracking`, `moveNodes`, `previewPaste`, `applyPaste`) ; `docs/api/components/schemas/revisions.yaml` lignes 464–2054 (`NodeKind` → `ComparedEstimateLineFacet`) ; `docs/api/components/parameters.yaml` (paramètres `Node*`, `Search`, `SortOrder`, `SubprojectFilter`, `RowNumber`) ; `docs/api/components/common.yaml` (types élémentaires, `WorkInstant*`, `LockVersion`, `Problem`, `ErrorCode`, `ProblemParams`) ; `docs/api/components/responses.yaml` ; `CommandCondition` de `schemas/projects.yaml` ; spécification §3.2.4–3.2.5 (752–840), §3.4.5.3 (2197–2456), §3.4.5.4 (2456–2597), §3.4.5.5 (2597–2698), §3.5.1 (3100–3118), §3.6 (3174–3352), §4.4.1 (3847–3980) ; `DECISIONS.md` : sections « Arbre commun », « Calculé contre saisi », « Listes et grilles », « Les tâches qu'une écriture redate », « Le tri des grilles arborescentes », « La structure lue, sa phase et son diff », « Les gestes de structure et la saisie des tâches », « La place d'un nœud créé ou déplacé », « La saisie et le collage sur l'avenant », « Les heures d'une date saisie », « Les gestes du Kanban », « La lecture du planning dit sa date de calcul », « La résolution d'un numéro de ligne », « Les exemples manquants… (US-0640/L1) », « Collage et annulation », plus grep ciblés ; `docs/roadmap/EP-16-maquette-durcissement.md` (« Constats reçus », « Les modifications du contrat ») ; générateurs `mockstructure.py`, `mockgestures.py`, `mocklinks.py`, `mockdating.py`, `mocknonworking.py`, `mocksort.py` (en-têtes et points cités). **Fixtures ouvertes : 93** (les 17 lectures `nodes*.json` + `volume/nodes_thousand.json`, les 33 `NodesWritten`/`PasteApplied`, les 34 refus, les 7 `dependencies_*`, les 3 `row_number_*`, les 5 `paste_plan*`, `task_dates_sent`, `nodes_move_mixed`), avec un script de cohérence (numéros de ligne, parents, totaux, sommes des tâches, présence des champs).

Rien de ce qui suit ne recoupe les quatre lots restants (#1457, #1453, #1455, #1333) : le paramètre `difference`, `createNode`/`NON_WORKING_DAY`, le collage ancré sur un nœud retiré, `apply_rate_update` et les exemples qu'ils portent ne sont pas signalés.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| F-01 | majeur | `docs/api/components/schemas/revisions.yaml:1139-1153`, `1208-1221` (`TaskFacet`) ; `fixtures/api/nodes.json` (« Études ») | `is_critical` et `total_float` ne sont pas exigés, et **toutes** les récapitulatives des fixtures les omettent : la spec leur donne la plus petite marge de leurs subordonnées et la criticité dès qu'une l'est | WF-PLA-0100 |
| F-02 | majeur | `schemas/revisions.yaml:1208-1216` (`TaskFacet.total_float`), `1442-1456` (`Predecessor`) | Le conflit entre une tâche manuelle et son prédécesseur doit être signalé sur les deux tâches « en nommant la liaison en cause » ; aucun attribut ne nomme la liaison ni ne marque la tâche manuelle | WF-PLA-0020, WF-PLA-0100 |
| F-03 | majeur | `schemas/revisions.yaml:1457-1464` (`PredecessorsReplace`) ; `paths/revisions.yaml:1232-1249` (`setPredecessors` 422) | « Une seconde liaison entre les mêmes tâches est refusée » : ni unicité de `predecessor_node_id` dans `predecessors`, ni code, ni exemple | WF-PLA-0030 |
| F-04 | majeur | `paths/revisions.yaml:918-919`, `954` (`deleteNode`) ; `common.yaml:420-421` | « Refusée sur une tâche portant un coût réel ou déjà démarrée » : citation fautive (une ligne de coût ne se rattache à aucune tâche ; la spec dit « démarrée ou terminée ») ; le 409 est la réponse générique, sans code ni condition ni exemple ; `TASK_ALREADY_STARTED`/`TASK_COMPLETED` ne sont cités par aucune opération ; le sort des lignes de provision n'est pas dit | WF-PLA-0070, §3.2.5 |
| F-05 | majeur | `paths/revisions.yaml:1260-1261`, `1295-1307` (`setTaskProgress`) ; `common.yaml:433` | « Refusé sur une récapitulative » sans code ni condition déclarés ; `SUMMARY_TASK_DERIVED` (et `params.subordinate_node_ids`) n'est porté par aucune opération du contrat | WF-PLA-0040, WF-IHM-0030 |
| F-06 | majeur | `paths/revisions.yaml:712-732` (`listNodes`) ; `parameters.yaml:106-220` | Aucun filtre sur les colonnes de nombres (`_min`/`_max` : heures, quantité, débours, montants, délai de paiement, durée), de dates (`from`/`to` : début, fin, démarrage, terminaison), ni sur le mode, le jalon, la fin dépassée, l'objet désactivé, l'année de consommation : « toute grille se filtre sur chacune de ses colonnes » | WF-IHM-0060, WF-IHM-0130 |
| F-07 | majeur | `schemas/revisions.yaml:729-775` (`NodeColumn`) | Les colonnes de la grille de planning omettent `started_on` et `completed_on`, que WF-PLA-0080 nomme, et comptent `progress`, que WF-PLA-0080 dit « signalé par une marque visuelle et non par une colonne » ; l'ordre de `NodeColumn` règle le collage | WF-PLA-0080, WF-IHM-0050 |
| F-08 | majeur | `schemas/revisions.yaml:1592-1601` (`EstimateLineWrite.label` exigé, `minLength: 1`) | La spec fait composer le libellé d'une ligne créée par Waterfall (tâche + rôle) ; le contrat oblige le client à l'envoyer | WF-DEV-0020, WF-ARC-0020 |
| F-09 | majeur | `schemas/revisions.yaml:1594` (`EstimateLineWrite`), `1316`, `1632` ; `fixtures/api/nodes_estimate.json` (ligne 10), `estimate_line_entered.json` | « La catégorie d'une ligne de main-d'œuvre n'est pas saisissable : c'est celle de son rôle » ; le contrat l'exige à la création et les lignes de main-d'œuvre la nomment dans `editable_fields` | WF-DEV-0020 |
| F-10 | majeur | `schemas/revisions.yaml:1414-1419` (`remaining_entry`) ; `fixtures/api/nodes_estimate.json` (ligne 12) | Une ligne de provision rend `remaining_entry.is_available: true` alors que ses grandeurs sont calculées depuis le risque ; aucune condition ne dit qu'elle ne se réestime pas | WF-RAE-0010, WF-RIS-0010, WF-IHM-0030 |
| F-11 | majeur | `paths/revisions.yaml:1368-1422` (`setNodeTracking`) ; `schemas/revisions.yaml:1466-1474` (`TrackingEntry`) | Pas de 409 (seule écriture de grille sans lui) ; `TrackingEntry` sans description, `timeline_id` ni exigé pour `timeline` ni interdit pour `milestone_tracking` ; une chronologie qui n'est pas du projet n'a aucun refus déclaré (aucun `UNKNOWN_TIMELINE`) | WF-PLA-0060, WF-PLA-0140 |
| F-12 | mineur | `schemas/revisions.yaml:985-1010` (`NodesWritten.rescheduled`/`reinflated`) ; `fixtures/api/estimate_line_redated.json` | `reinflated` exclut ce que `ancestors` rend entier, `rescheduled` ne le dit pas, et l'exemple rend « Montage des armoires sur site » dans les deux | WF-PLA-0020 |
| F-13 | mineur | `schemas/revisions.yaml:1744-1754` (`RemainingUpdate.completed_on`) ; `fixtures/api/milestone_completed.json` | Un jalon terminé garde `started_on` nul, alors que la spec dit sans exception qu'une tâche terminée sans avoir été démarrée prend pour date de démarrage celle de sa terminaison — à trancher | WF-PLA-0130 |
| F-14 | mineur | `schemas/revisions.yaml:1537-1547` (`TaskFacetUpdate`), `512-543` ; `fixtures/api/nodes.json` (« Études ») | Le mode d'une récapitulative n'est ni dans `computed_fields` ni dans `editable_fields`, et aucune description ne dit par quel motif sa saisie est refusée (seule « la durée d'un jalon » est nommée) | WF-PLA-0040, WF-IHM-0030 |
| F-15 | mineur | `paths/revisions.yaml:919-920`, `1435-1436` (`deleteNode`, `moveNodes`) | La récapitulative qui perd sa dernière subordonnée : seul le rattachement gardé est décrit, pas la durée reprise, le jalon ou le jour de la tâche démarrée | WF-PLA-0040 |
| F-16 | mineur | `schemas/revisions.yaml:1119-1135` (`LagUnit`, `Lag`) | L'échelle d'un décalage en `percent` n'est pas dite (`50` ou `0.5`), aucun exemple n'en porte, et la convention des rapports du README dit l'inverse de WF-PLA-0160 | WF-PLA-0030, WF-PLA-0160 |
| F-17 | mineur | `paths/revisions.yaml` : `createNode` 835-855, `updateEstimateLine` 1167-1189, `updateTaskFacet` 1080-1115, `setLineRemaining` 1354, `applyPaste` 1632 | Refus déclarés sans exemple : `TASK_WITHOUT_WORKING_HOURS` (3 opérations), `FIELD_NOT_ACCEPTED` (3), `HOURLY_RATE_MISSING`, `RESOURCE_ROLE_REQUIRED`, `PROVISION_CATEGORY_RESERVED` et `COMPUTED_VALUE` sur `updateEstimateLine`, le 409 `task_not_completed` de `setLineRemaining`, le 409 d'`applyPaste` ; aucune fixture du dépôt ne porte `FIELD_NOT_ACCEPTED` ni `RESOURCE_ROLE_REQUIRED` | WF-PLA-0010, WF-DEV-0020, WF-RAE-0040 |
| F-18 | mineur | `parameters.yaml:106-113` (`NodeKinds`) ; `schemas/revisions.yaml:1190-1194` (`calendar_id`) | `kinds` décrit comme « restreint », quand `listNodes` dit qu'il n'est pas un filtre ; `calendar_id` nul pour une intersection sans que la description le dise (l'exemple `estimate_line_redated` le rend nul) | WF-PLA-0010 |
| F-19 | mineur | `paths/revisions.yaml:973-1022` (`getComputedValueDependencies`), `858-908` (`resolveRowNumber`) | Pas de 400 déclaré alors que `listNodes`, lecture à paramètres de requête comme elles, le déclare (une valeur de `field` hors énumération) | — |

### F-01 — Les récapitulatives n'ont ni marge ni criticité

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1139-1153` (`TaskFacet.required`), `1208-1221` (`total_float`, `is_critical`) ; `fixtures/api/nodes.json` nœud `…0521` « Études » et toutes les récapitulatives de `nodes_core`, `nodes_planning`, `nodes_estimate`, `nodes_nested`, `nodes_summaries`, `volume/nodes_thousand.json` (40 récapitulatives sans `is_critical`) ; **exigence** WF-PLA-0100 : « Une tâche récapitulative porte la plus petite marge totale de celles de ses subordonnées qui en portent une, et appartient au chemin critique dès que l'une d'elles y appartient ; une récapitulative dont aucune subordonnée ne porte de marge n'en porte pas » ; Vérif : « Une récapitulative dont une subordonnée est critique est critique et affiche la marge de cette subordonnée » ; **ce que dit le contrat** : `is_critical` « Appartenance au chemin critique, calculée » (ligne 1217), ni lui ni `total_float` ne sont dans `required` ; `TaskFacet.description` : « Les valeurs calculées — … marge, criticité … — ne sont pas saisissables ».
- **Constat.** Dans `nodes.json`, « Études » a trois subordonnées à marge `0` critiques (« Études de détail », « Revue de conception », « Réception des études ») : la spec lui donne `total_float: 0` et `is_critical: true` ; la fixture n'a ni l'un ni l'autre, et le schéma le tolère parce qu'aucun des deux n'est exigé. Le générateur le dit en toutes lettres (`tools/src/wftools/mockdating.py:57-61` : « A summary … has no latest finish: the first is not scheduled »). Un `is_critical` facultatif se traduit en `is_critical?: boolean` dans le client engendré : le Gantt (WF-PLA-0090 : « le chemin critique » visible) ne peut pas distinguer une récapitulative non critique d'une récapitulative dont la valeur manque. C'est un témoin qui contredit la spec, et un `required` qui change après le gel.
- **Proposition.** Ajouter `is_critical` et `total_float` à `TaskFacet.required` (`total_float` reste nullable : mode manuel, et récapitulative dont aucune subordonnée n'en porte) ; dire dans leurs descriptions la règle de WF-PLA-0100 pour une récapitulative ; faire porter par `mockdating` la marge et la criticité des récapitulatives et régénérer les lectures et les `ancestors` des écritures.
- **DECISIONS.md** : aucune décision sur les récapitulatives ; « Les tâches qu'une écriture redate (EP-02/L10) » fixe la marge en `Duration`, « nulle pour une tâche en mode manuel », sans parler des récapitulatives ; la ligne 1212 (« la facette n'exige que ce que toute tâche porte ») porte sur `started_on`, `calendar_id` et le rattachement, pas sur la criticité, que toute tâche porte.

### F-02 — Le conflit d'une tâche manuelle n'est pas nommé

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1208-1216` (`TaskFacet.total_float`), `1037-1050` (`NodeSchedule`), `1442-1456` (`Predecessor`) ; **exigence** WF-PLA-0020 : « la tâche manuelle et ce prédécesseur sont signalés dans la grille de planning et dans le diagramme de Gantt, selon l'échelle commune de WF-IHM-0070 ; le signalement nomme la liaison en cause et disparaît dès que les dates le permettent » ; WF-IHM-0070 compte « le conflit entre une tâche manuelle et ses prédécesseurs (WF-PLA-0020) » parmi les signalements ; **ce que dit le contrat** : « un prédécesseur qui ne peut pas finir à temps pour elle porte une marge négative, il est critique, et le conflit est signalé (WF-PLA-0020). Nulle pour une tâche en mode manuel ».
- **Constat.** Le contrat ne porte le conflit que par la marge négative du prédécesseur. Rien ne marque la tâche manuelle (sa marge est nulle, par règle), et rien ne dit *quelle* liaison est en cause : un prédécesseur à plusieurs successeurs manuels porte une seule marge, et le front devrait recalculer les dates pour retrouver la liaison — ce que WF-ARC-0020 lui interdit. La grille ne peut donc pas « nommer la liaison en cause », et le Gantt ne peut signaler que l'une des deux tâches. Après le gel, l'attribut qui manque est une propriété nouvelle de `Predecessor` ou de `TaskFacet`.
- **Proposition.** Sur `Predecessor` (lecture), un booléen calculé `is_conflicting` (lecture seule) : vrai quand le prédécesseur, en mode automatique, ne peut pas satisfaire la liaison avec cette tâche en mode manuel ; la tâche manuelle est signalée dès qu'une de ses liaisons l'est, le prédécesseur par sa marge négative, et la liaison est nommée. Le rendre aussi dans `NodeSchedule` (un tableau `conflicting_predecessor_node_ids`) pour qu'une écriture qui lève ou crée le conflit le montre sans relecture.
- **DECISIONS.md** : aucune décision (grep « conflit » : seules les sections sur le 412 et l'annulation).

### F-03 — La seconde liaison entre les mêmes tâches n'a pas de refus

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1457-1464` (`PredecessorsReplace`, `predecessors` sans `uniqueItems` ni règle), `1431-1440` (`PredecessorWrite`) ; `docs/api/paths/revisions.yaml:1232-1249` (422 de `setPredecessors`) ; **exigence** WF-PLA-0030 : « Deux tâches ne sont reliées que par une liaison au plus, comme dans MS Project ; une seconde liaison entre les mêmes tâches est refusée » ; **ce que dit le contrat** : le 422 nomme `LINK_CYCLE`, `LINK_FORBIDDEN`, `PROJECT_HORIZON_EXCEEDED` et « une valeur hors règle, `fields` la localisant ».
- **Constat.** `setPredecessors` remplace les prédécesseurs d'une tâche : deux entrées de `predecessors` qui nomment le même `predecessor_node_id` sont deux liaisons entre les mêmes tâches (la liaison inverse, elle, est déjà un cycle). Le refus que la spec décrit n'est déclaré nulle part, et le catalogue n'a pas de code pour le dire : `ALREADY_EXISTS` est le 409 d'une unicité d'objet, `DUPLICATE_WORK_BREAKDOWN_ITEM` est propre au lotissement. Un code nouveau après le gel est une modification du contrat.
- **Proposition.** Dans `PredecessorsReplace.predecessors`, dire que `predecessor_node_id` est unique dans la liste, refusé par 422 `VALIDATION_FAILED`, `fields[].pointer` à `/predecessors/<n>/predecessor_node_id` de chaque occurrence après la première, motif nouveau `DUPLICATE_PREDECESSOR` (sur le modèle de `DUPLICATE_WORK_BREAKDOWN_ITEM`, `common.yaml:571`), sans paramètre ; l'ajouter au 422 de `setPredecessors` avec un exemple engendré par `wftools.mockgestures`.
- **DECISIONS.md** : aucune décision (grep « seconde liaison », « liaison au plus », « mêmes tâches » : rien).

### F-04 — `deleteNode` : citation fautive, refus d'état sans code ni exemple

- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:918-919` (« Refusée sur une tâche portant un coût réel ou déjà démarrée, selon WF-PLA-0070 »), `954` (`'409': { $ref: …#/Conflict }`) ; `docs/api/components/common.yaml:420-421` (`TASK_ALREADY_STARTED`, `TASK_COMPLETED`) ; **exigence** WF-PLA-0070 : « Une tâche démarrée ou terminée ne peut pas être supprimée. Les lignes de provision qu'elles portent ne sont pas supprimées : elles passent sur une autre tâche selon WF-RIS-0010 » ; Vérif : « La suppression d'une tâche démarrée est refusée, et l'utilisateur est renvoyé vers la mise à zéro de son reste à engager » ; §3.2.5 : une ligne de coût « ne se rattache à aucune tâche et à aucune révision ».
- **Constat.** (1) « portant un coût réel » n'est dans aucune exigence et contredit le modèle : aucune tâche ne porte de coût réel ; « terminée » manque. (2) Le 409 renvoie à la réponse commune sans dire le code ni la condition : le front ne sait pas quoi afficher (« renvoyé vers la mise à zéro de son reste à engager »), alors que les autres écritures nomment `params.missing_condition` ; `TASK_ALREADY_STARTED` et `TASK_COMPLETED` figurent au catalogue sous le 409 et aucune opération ne les emploie (grep sur `paths/` et `schemas/` : aucun). (3) Le sort des lignes de provision de la tâche supprimée (déplacées, non supprimées) n'est pas décrit, et `NodesWritten` ne dit pas si la ligne déplacée est rendue dans `nodes`.
- **Proposition.** Réécrire : « Refusée sur une tâche démarrée ou terminée, ou dont une subordonnée l'est (WF-PLA-0070) : 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `task_not_started` [condition à ajouter à `CommandCondition`] — l'utilisateur est renvoyé vers la mise à zéro de son reste à engager » ; ou employer `TASK_ALREADY_STARTED`/`TASK_COMPLETED`, et sinon les retirer du catalogue. Dire que les lignes de provision portées passent sur la tâche que WF-RIS-0010 désigne et sont rendues dans `nodes` (écrites) ou dans `ancestors`. Ajouter l'exemple du refus.
- **DECISIONS.md** : « `deleteNode` porte le compteur du nœud supprimé » (#1210, ligne 7176) ne traite que le 412 ; « Les gestes de structure… » cite WF-PLA-0070 pour `node_summary_deleted` ; aucune décision sur le refus d'une tâche démarrée ni sur « coût réel ».

### F-05 — Le refus de `setTaskProgress` sur une récapitulative n'a pas de code

- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:1260-1261` (« Refusé sur une récapitulative, dont l'état est dérivé (WF-PLA-0040) »), `1295-1307` (409 : `task_is_milestone`, `task_without_lines`, `task_not_milestone`, `completed_milestone`, puis `project_in_progress`, `no_background_task_running`), `1315` (422 commun) ; `docs/api/components/common.yaml:433` (`SUMMARY_TASK_DERIVED`) et `Problem.params` (`subordinate_node_ids`) ; **exigence** WF-PLA-0040 : « son état n'est pas saisissable » ; WF-IHM-0030 : « Une tentative de saisie sur une valeur calculée est refusée en nommant ce dont elle dépend » ; **ce que dit le contrat** : le refus en prose, aucun code sous le 409 ni le 422, et `SUMMARY_TASK_DERIVED` n'apparaît dans aucun `paths/*.yaml` ni `schemas/*.yaml`.
- **Constat.** Le code existe depuis EP-02 avec son paramètre (`subordinate_node_ids`, « les subordonnées directes »), mais aucune opération ne le déclare : le service ne sait pas quoi rendre, le front ne sait pas quoi attendre, et le Kanban, qui ne liste pas les récapitulatives, n'est pas la seule voie (la grille de planning porte la colonne d'état). Un code mort au catalogue est aussi un constat de gel.
- **Proposition.** Sous le 422 de `setTaskProgress` : « sur une récapitulative, `SUMMARY_TASK_DERIVED`, `params.subordinate_node_ids` ses subordonnées directes (WF-PLA-0040, WF-IHM-0030) », avec un exemple ; ou, si le motif retenu est l'état, une condition `task_not_summary` sous le 409, et retirer `SUMMARY_TASK_DERIVED` et `subordinate_node_ids` du catalogue.
- **DECISIONS.md** : « Calculé contre saisi », ligne 90 : « Les subordonnées que nomme `subordinate_node_ids` (`SUMMARY_TASK_DERIVED`) sont les subordonnées directes » — la décision fixe le paramètre, aucune opération ne le porte.

### F-06 — `listNodes` ne filtre pas chaque colonne des grilles

- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:712-732` (paramètres de `listNodes`), `660-668` (description des filtres) ; `docs/api/components/parameters.yaml:106-220` ; **exigence** WF-IHM-0060 : « Toute grille se filtre sur chacune de ses colonnes (WF-IHM-0130) ; dans une grille arborescente, le filtre laisse visibles les parents des lignes retenues » ; WF-IHM-0130 : « Toute table se filtre sur chacune de ses colonnes, et le filtre s'applique aux totaux qu'elle présente » ; README : « Une colonne de nombres se filtre par deux bornes `<colonne>_min` et `<colonne>_max` » ; « Une période se filtre par `from` et `to` » ; **ce que dit le contrat** : les filtres sont `search` (libellés), `subtree_of`, `subproject_id`, `cost_type_id`, `order_item_id`, `work_package_id`, `cost_category_id`, `resource_role_id`, `progress`, `is_critical`, `summaries_only`, `max_level`, `timeline_id`.
- **Constat.** Les colonnes des trois grilles (WF-PLA-0080, WF-DEV-0050, WF-RAE-0040) qu'aucun paramètre ne filtre : mode de planification, durée, début, fin, dates de démarrage et de terminaison, marge totale, description ; quantité, charge, débours, délai de paiement, année de consommation, les quatre montants et les grandeurs précédentes ; jalon, fin dépassée, objet désactivé. Les autres listes du contrat appliquent la convention (`DECISIONS.md:2826-2844`, `3141`, `5450` : « toute table se filtre sur chacune de ses colonnes »), et `listNodes` fait dire aux descriptions que « les totaux sont ceux des lignes retenues » — un filtre de montant ne peut pas se faire côté front sans fausser les totaux (WF-IHM-0130, WF-ARC-0020). Six mille nœuds (§4.6.2) ne se filtrent pas dans le navigateur.
- **Proposition.** Ajouter à `listNodes`, sur le modèle des autres listes : `scheduling_mode` (liste), `is_milestone`, `finish_overdue`, `uses_inactive_object` (booléens), `start_from`/`start_to`, `finish_from`/`finish_to`, `started_on_from`/`…_to`, `completed_on_from`/`…_to` (dates de planning, fin incluse), `hours_min/_max`, `quantity_min/_max`, `unit_disbursement_min/_max`, `payment_delay_days_min/_max`, `base_amount_min/_max`, `inflated_amount_min/_max`, `reestimated_amount_min/_max`, `budgeted_amount_min/_max`, `total_float_min/_max` (jours), `consumption_year_min/_max` ; un filtre de tâche retient la tâche avec ses lignes, un filtre de ligne les lignes ; `search` étendu à `description` ou un `description` propre. Les refus sont ceux du README (`NUMBER_INVALID`, `DATE_INVALID`, `VALUE_OUT_OF_RANGE` sur la borne haute).
- **DECISIONS.md** : « Listes et grilles » (ligne 212 : « Chaque grille demande … ses filtres par des paramètres nommés ») ; aucune décision n'écarte les filtres de colonne de `listNodes` (grep `listNodes` × `borne`/`_min`/`from` : rien).

### F-07 — `NodeColumn` ne reflète pas les colonnes de la grille de planning

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:729-775` (`NodeColumn`), `1800-1805` (`PastePreview` : « chacune des suivantes remplit la colonne suivante de la facette … dans l'ordre de `NodeColumn` ») ; **exigence** WF-PLA-0080 : « avec pour chacune : son libellé, sa description, sa durée, ses dates, son mode de planification, son état, signalé par une marque visuelle et non par une colonne, pour une récapitulative, son avancement physique, sa marge totale, son appartenance au chemin critique, ses dates de démarrage et de terminaison, son rattachement à un lot ou à un poste, ses prédécesseurs » ; **ce que dit le contrat** : « les colonnes de la grille de planning (WF-PLA-0080) … de `label` à `work_breakdown` », soit `label, description, scheduling_mode, duration, start, finish, progress, physical_progress, total_float, is_critical, predecessors, work_breakdown`.
- **Constat.** Les colonnes de démarrage et de terminaison (`started_on`, `completed_on`), exigées, n'y sont pas ; `progress` y est alors que la spec en fait une marque et non une colonne. Or l'énumération est ce qui aligne un bloc collé sur les colonnes affichées : « C'est dans cet ordre qu'un collage remplit les colonnes qui suivent la colonne visée » (ligne 743), et la décision du rattachement place `work_breakdown` en dernier « pour ne déplacer aucune colonne de ligne dans l'ordre d'un collage » (`DECISIONS.md:1202`). Dès que la grille présentera les deux dates que WF-PLA-0080 exige, un bloc collé à partir de `finish` tombera sur `started_on` à l'écran et sur `progress` au serveur : l'énumération devra changer, et elle est figée. Les deux colonnes manquent aussi au tri (sans conséquence : le planning ne trie pas) et à toute `PasteRejection.column`.
- **Proposition.** Insérer `started_on` et `completed_on` dans `NodeColumn`, à la place que WF-PLA-0080 leur donne (après `is_critical`, avant `predecessors`) ; décider du sort de `progress` (le garder comme colonne non saisissable que le collage refuse par `FIELD_NOT_ACCEPTED`, en le disant, ou le retirer) ; régénérer `paste_too_wide` si le compte des colonnes de tâche change.
- **DECISIONS.md** : ligne 1202 (le rang de `work_breakdown`) ; aucune décision sur `started_on`/`completed_on` ni sur `progress` comme colonne.

### F-08 — Le libellé d'une ligne créée est exigé du client

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1592-1601` (`EstimateLineWrite`, `required: [label, cost_category_id, quantity]`, `label: { minLength: 1, pattern: '\S' }`) ; **exigence** WF-DEV-0020 : « À la création d'une ligne, Waterfall compose son libellé à partir de celui de la tâche qui la porte et, s'il existe, de celui de son rôle de ressource ; ce libellé reste modifiable » ; Motif : « La composition du libellé évite de recopier à la main, du planning vers le devis, des centaines de libellés » ; **ce que dit le contrat** : le libellé est exigé, jamais vide.
- **Constat.** La composition est une règle du serveur ; le contrat ne lui laisse aucun chemin pour l'exercer : le client doit envoyer un libellé non vide, donc le composer lui-même en recopiant la règle (WF-ARC-0020). Le collage d'une ligne depuis un tableur sans colonne de libellé et l'import suivent la même règle. Rendre `label` facultatif après le gel est compatible ; l'inverse ne l'est pas, mais une création sans libellé servie par le faux back aujourd'hui serait refusée par Prism : autant le dire avant.
- **Proposition.** `EstimateLineWrite.label` facultatif (ou nullable) : « absent ou nul, le serveur le compose du libellé de la tâche porteuse et, s'il existe, de celui du rôle (WF-DEV-0020) ; envoyé, il est pris tel quel, non vide » ; `createNode` le dit, et un exemple `estimate_line_created_labelled` montre le libellé composé.
- **DECISIONS.md** : aucune décision (grep « compose », « libellé composé » : seule la ligne 7828, sur les lignes de coût).

### F-09 — La catégorie d'une ligne de main-d'œuvre est saisissable

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1594` (`EstimateLineWrite.required` : `cost_category_id`), `1631-1632` (`EstimateLineUpdate.cost_category_id`), `1316` (`EstimateLineFacet.cost_category_id`), `523-543` (`editable_fields`) ; `fixtures/api/nodes_estimate.json` ligne 10 « Raccordement des borniers » (`editable_fields` : `estimate_line.cost_category_id`, `estimate_line.resource_role_id`, …), de même `estimate_line_entered.json`, `estimate_line_updated.json`, `paste_applied.json` ; **exigence** WF-DEV-0020 : « Lorsque sa catégorie relève d'une nature de main-d'œuvre, elle porte en outre un rôle de ressource, dont elle tient cette catégorie » ; Vérif : « La catégorie d'une ligne de main-d'œuvre n'est pas saisissable : c'est celle de son rôle » ; §3.2.5 : « l'utilisateur traverse l'organigramme et choisit un rôle de ressource, qui détermine la catégorie ».
- **Constat.** Le contrat exige la catégorie à la création de toute ligne et la laisse saisissable sur une ligne de main-d'œuvre ; le témoin la nomme parmi les champs acceptés. Rien ne dit ce qui se passe quand le rôle et la catégorie envoyés ne concordent pas, ni que changer le rôle change la catégorie. C'est l'inverse du Vérif. Après le gel, retirer un champ de `required` et le sortir d'`editable_fields` change ce que le client engendré exige.
- **Proposition.** `EstimateLineWrite` : `cost_category_id` exigé sauf si `resource_role_id` est envoyé — dire : « pour une ligne de main-d'œuvre, le rôle suffit et la catégorie est la sienne ; une catégorie envoyée différente de celle du rôle est refusée par 422, `fields` sur `/estimate_line/cost_category_id`, motif `FIELD_NOT_ACCEPTED` » ; les lignes de main-d'œuvre ne nomment pas `estimate_line.cost_category_id` dans `editable_fields` et le portent dans `computed_fields` (dépendance `resource_role` à ajouter à `ComputedDependency`) ; régénérer les fixtures (`mockcore`).
- **DECISIONS.md** : « Constats du contrat, second passage (EP-02/L8) », lignes 374-380, liste les champs acceptés (« une ligne de main-d'œuvre porte le rôle et la charge… ») sans mentionner la catégorie ; aucune décision n'assume sa saisie sur une ligne de main-d'œuvre.

### F-10 — Une ligne de provision accepte la réestimation

- **gravité** majeur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1414-1419` (`EstimateLineFacet.remaining_entry` : « les lignes d'une tâche terminée ne se modifient pas ») ; `fixtures/api/nodes_estimate.json`, ligne 12 « Provision — risque de reprise du câblage » : `is_computed: true`, `computed_fields: [estimate_line.quantity, estimate_line.unit_disbursement, estimate_line.subproject_id]`, `remaining_entry: {is_available: true, missing_conditions: []}` ; `paths/revisions.yaml:1320-1329` (`setLineRemaining` : « La ligne dit elle-même si elle accepte la réestimation ») ; **exigence** WF-RAE-0010 : le reste à engager compte « des lignes de provision des risques identifiés à la date de calcul, pour leur montant » ; WF-DEV-0020 : une ligne de provision « porte un montant calculé, qui n'est pas saisi » ; WF-RIS-0010 (cité par le contrat) : son montant suit le risque.
- **Constat.** La ligne dit à la grille de reste à engager qu'elle accepte une réestimation, alors que ses grandeurs sont calculées (`computed_fields`) et que `RemainingUpdate.reestimated_amount_basis` ne porte que ces grandeurs : la grille offrirait la cellule, et le serveur devrait refuser par `COMPUTED_VALUE` une saisie que le nœud a annoncée possible — la contradiction même que `remaining_entry` a été créé pour éviter (`DECISIONS.md:73-77`). Aucune `CommandCondition` ne dit « ligne de provision ».
- **Proposition.** Pour une ligne de provision, `remaining_entry.is_available: false`, `missing_conditions: [line_not_provision]` (condition à ajouter, nommée par la ligne comme `task_not_completed`) ; le dire dans `remaining_entry` et dans le 409 de `setLineRemaining` ; régénérer `nodes_estimate`, `nodes_core`, le volume.
- **DECISIONS.md** : « Calculé contre saisi », lignes 73-77 (la ligne dit si elle accepte une réestimation ; « sous une tâche terminée, elle ne l'accepte plus ») ; rien sur les lignes de provision.

### F-11 — `setNodeTracking` : 409 absent, `TrackingEntry` sans règle

- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:1368-1422` (réponses : 200, 400, 401, 403, 404, 412, 422, 503 — pas de 409), `1390-1397` (corps en ligne) ; `docs/api/components/schemas/revisions.yaml:1466-1474` (`TrackingEntry` : `kind` seul exigé, `timeline_id` nullable, aucune description) ; **exigence** WF-PLA-0060 : « Une tâche peut être inscrite à une chronologie, ou en être retirée. Un jalon peut de la même façon être inscrit au suivi temps/temps » ; WF-PLA-0140 : « Un projet peut porter plusieurs chronologies » ; **ce que dit le contrat** : `EditableField.task.tracking` « sous la commande de saisie du planning » (`edit_planning`), comme les autres champs de la tâche.
- **Constat.** (1) Toute autre écriture de grille déclare le 409 des conditions de sa commande (`no_background_task_running`, révision pendant un marquage…) ; `setNodeTracking`, écrite sous `edit_planning`, ne le déclare pas : pendant un marquage, elle n'a pas de réponse déclarée. (2) `TrackingEntry` ne dit ni que `timeline_id` est exigé pour `kind: timeline`, ni qu'il est nul pour `milestone_tracking`, ni ce qui refuse une `timeline_id` qui n'est pas une chronologie du projet (ou qui n'existe pas) : aucun code du catalogue (`UNKNOWN_TASK`, `UNKNOWN_SUBPROJECT` existent, pas `UNKNOWN_TIMELINE`), aucun exemple ; une entrée envoyée deux fois n'a pas de règle non plus. Un code nouveau après le gel est une modification du contrat.
- **Proposition.** Ajouter `'409': { $ref: …#/Conflict }` ; décrire `TrackingEntry` : « `timeline` exige `timeline_id`, une chronologie du projet, sinon 422 `VALIDATION_FAILED` sur `/entries/<n>/timeline_id`, motif `VALUE_REQUIRED` (absent) ou `UNKNOWN_TIMELINE` (code à ajouter) ; `milestone_tracking` le porte nul ; une entrée répétée est refusée ou ignorée (à dire) » ; un exemple de chaque refus.
- **DECISIONS.md** : « Le suivi temps/temps d'une tâche qui n'est pas un jalon est refusé » (#1159, ligne 6619) ne traite que `MILESTONE_REQUIRED` ; #827 (ligne 5794) a ajouté le 412 ; #803 (« exemples manquants des refus des chronologies ») porte sur `createTimeline` et le 412 du lotissement.

### F-12 — `rescheduled` et `ancestors` rendent la même tâche

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/revisions.yaml:985-997` (`rescheduled` : « Les tâches non récapitulatives dont le début, la fin … ont changé … sans être écrites »), `998-1010` (`reinflated` : « hors celles que `ancestors` rend entières »), `976-984` (`ancestors`) ; `fixtures/api/estimate_line_redated.json` : `ancestors` = `…0561`, `…0562` (« Montage des armoires sur site », tâche porteuse, entière) ; `rescheduled` = `…0562`, `…0565` ; **exigence** WF-PLA-0020 ; **ce que dit le contrat** : `reinflated` exclut explicitement ce qu'`ancestors` rend entier, `rescheduled` ne le dit pas.
- **Constat.** La tâche porteuse d'une ligne écrite est un ancêtre (rendu entier, avec ses dates) et, redatée par le changement de rôle, est aussi dans `rescheduled` : la même valeur arrive deux fois, et le front doit choisir. Les deux listes devraient suivre la même règle ; l'exemple montre qu'elles ne la suivent pas.
- **Proposition.** Soit `rescheduled` « hors les tâches que `ancestors` rend entières », comme `reinflated`, et régénérer `estimate_line_redated` ; soit dire qu'une tâche peut paraître dans les deux et que la projection prime.
- **DECISIONS.md** : « Les tâches qu'une écriture redate (EP-02/L10) » (ligne 526) : « `ancestors` devient les ancêtres des nœuds écrits et des tâches redatées … entier » ; EP-02/L16 (ligne 986) pour `reinflated` ; le recoupement des deux n'est pas tranché.

### F-13 — La date de démarrage d'un jalon terminé

- **gravité** mineur (à trancher) ; **emplacement** `docs/api/components/schemas/revisions.yaml:1744-1754` (`RemainingUpdate.completed_on` : « Pour une tâche non démarrée qui n'est pas un jalon, la même date est aussi celle de son démarrage »), `1703-1717` (`ProgressUpdate`) ; `fixtures/api/milestone_completed.json` (« Réception usine » : `completed_on: 2026-06-03`, pas de `started_on`) ; **exigence** WF-PLA-0130 : « une tâche terminée sans avoir été démarrée prend pour date de démarrage celle de sa terminaison » ; WF-PLA-0050 : « Son état passe directement de non démarré à terminé ».
- **Constat.** La phrase de WF-PLA-0130 ne fait pas d'exception pour le jalon, et la valeur acquise d'un jalon se situe par ces dates (WF-IND-0030) ; le contrat lui laisse `started_on` nul. Les deux lectures se défendent (un jalon ne démarre jamais) : la question est à poser à l'auteur, et la réponse à écrire dans `TaskFacet.started_on`, qui n'a pas de description.
- **Proposition.** Décrire `started_on` : « nul pour un jalon, qui ne démarre pas (WF-PLA-0050) » si c'est la lecture retenue, ou l'aligner sur `completed_on` pour un jalon terminé, et régénérer `milestone_completed`, `nodes.json` (« Réception des études »).
- **DECISIONS.md** : « Une tâche non démarrée réestimée à zéro passe par l'état démarré » (#486, ligne 1619) ne parle que des tâches qui ne sont pas des jalons.

### F-14 — Le mode d'une récapitulative n'est ni calculé ni accepté

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1544-1547` (`TaskFacetUpdate` : « un champ que le nœud n'accepte pas, ni saisi ni calculé pour lui — la durée d'un jalon … — par `FIELD_NOT_ACCEPTED` »), `512-543` (`computed_fields`, `editable_fields`), `675-686` (`ComputedField`) ; `fixtures/api/nodes.json` « Études » : `computed_fields: [task.duration, task.start, task.finish, task.progress]`, `editable_fields` sans `task.scheduling_mode` ; **exigence** WF-PLA-0040 : « Une tâche récapitulative est toujours en mode automatique ; son mode n'est pas saisissable » ; WF-IHM-0030 : une valeur calculée « se distingue visuellement d'une valeur saisie ».
- **Constat.** Le mode d'une récapitulative n'est ni dans `computed_fields` (la grille ne le présente donc pas comme calculé) ni dans `editable_fields` ; le seul cas nommé par la description de `FIELD_NOT_ACCEPTED` est la durée d'un jalon. L'implémenteur du service doit choisir entre `COMPUTED_VALUE` et `FIELD_NOT_ACCEPTED` sans que le contrat le dise.
- **Proposition.** Nommer le mode d'une récapitulative à côté de la durée d'un jalon dans `TaskFacetUpdate`, `ErrorCode.FIELD_NOT_ACCEPTED` (`common.yaml`) et `PastePreview`, ou le ranger dans `computed_fields` (`ComputedField` gagne `task.scheduling_mode`, dépendance `subordinates`).
- **DECISIONS.md** : EP-14/L42s (`FIELD_NOT_ACCEPTED`, « la durée d'un jalon ») ; rien sur le mode d'une récapitulative.

### F-15 — La récapitulative qui perd sa dernière subordonnée

- **gravité** mineur ; **emplacement** `docs/api/paths/revisions.yaml:919-920` (`deleteNode` : « Une récapitulative qui perd sa dernière subordonnée garde son rattachement au lotissement »), `1435-1436` (`moveNodes`, même phrase) ; **exigence** WF-PLA-0040 : « Une récapitulative qui perd sa dernière subordonnée devient une tâche feuille en mode automatique : elle prend pour durée celle qu'elle calculait, conserve son état, ses lignes propres et son rattachement, et ses dates sont recalculées. Si cette durée est nulle, elle devient un jalon … ; démarrée, elle prend une durée d'un jour ».
- **Constat.** Les deux opérations ne retiennent de la règle que le rattachement ; la durée reprise, le jalon et le jour de la tâche démarrée ne sont dits nulle part, et `NodesWritten.ancestors` rendra cette tâche « recalculée » sans que le contrat dise en quoi. Le service et le faux back peuvent diverger.
- **Proposition.** Compléter les deux descriptions d'une phrase citant WF-PLA-0040, et dire que l'ancienne récapitulative est rendue dans `ancestors` (pour `deleteNode`, l'ancêtre du nœud supprimé ; pour `moveNodes`, l'ancien ancêtre), feuille ou jalon désormais, ses `computed_fields` et `editable_fields` changés.
- **DECISIONS.md** : lignes 1347-1348 (le rattachement gardé « par `deleteNode`, `moveNodes`, un import ou une annulation ») ; rien sur la durée ni le jalon.

### F-16 — L'échelle d'un décalage en pourcentage

- **gravité** mineur ; **emplacement** `docs/api/components/schemas/revisions.yaml:1119-1125` (`LagUnit`, `percent` : « un décalage de 50 % sur un prédécesseur de dix jours vaut cinq jours de travail »), `1127-1135` (`Lag.value`, `Decimal`) ; **exigence** WF-PLA-0030 : « en pourcentage de la durée du prédécesseur » ; README : « Une part, un avancement ou un taux calculé … est un décimal exact … » (les taux du contrat, `inflation_rate`, `win_probability`, vont « de 0 à 1 »).
- **Constat.** Rien ne dit si `{value: "50", unit: "percent"}` ou `{value: "0.5", unit: "percent"}` est le décalage de 50 % ; la convention des rapports du contrat (0 à 1) et l'exemple de la description (« 50 % ») tirent chacun de leur côté, et aucune fixture ne porte `percent` (grep : aucune). MS Project écrit `50%`.
- **Proposition.** Dire dans `Lag.value` : « en `percent`, le nombre de pour cent, `50` pour la moitié de la durée du prédécesseur (WF-PLA-0160, MS Project) », et porter un prédécesseur en `percent` dans `predecessors_entered` ou le témoin.
- **DECISIONS.md** : « Listes et grilles » (`lag`, `lag_unit` « garde son unité ») ; rien sur l'échelle du pourcentage.

### F-17 — Refus déclarés sans exemple

- **gravité** mineur ; **emplacement** `docs/api/paths/revisions.yaml` : `createNode` 835-855 (`TASK_WITHOUT_WORKING_HOURS`, `FIELD_NOT_ACCEPTED`, les refus du rattachement « (`TaskFacetWrite`, WF-PLA-0170) » : exemples `provision_refused`, `out_of_range`, `horizon_exceeded`, `after_not_sibling` seulement) ; `updateEstimateLine` 1167-1189 (`HOURLY_RATE_MISSING`, `RESOURCE_ROLE_REQUIRED`, `TASK_WITHOUT_WORKING_HOURS`, `PROVISION_CATEGORY_RESERVED`, `FIELD_NOT_ACCEPTED` : exemples `payment_delay_out_of_range`, `subproject_has_actual_costs` seulement ; `COMPUTED_VALUE`, que `EstimateLineUpdate.subproject_id` (1646-1647) déclare pour une ligne de provision, n'est pas même nommé dans ce 422) ; `updateTaskFacet` 1080-1115 (`FIELD_NOT_ACCEPTED`, la durée d'un jalon, nommé par `TaskFacetUpdate` : aucun exemple) ; `setLineRemaining` 1354 (409 commun, la condition `task_not_completed` que `CommandCondition` lui attribue, `projects.yaml:257`, sans exemple) ; `applyPaste` 1632 (409 commun, sans description : une ligne du bloc sous une tâche terminée ? un traitement de fond ?) ; **exigence** WF-PLA-0010, WF-DEV-0020, WF-RAE-0040 ; **ce que dit le contrat** : grep des fixtures : aucune ne porte `FIELD_NOT_ACCEPTED` ni `RESOURCE_ROLE_REQUIRED` ; `TASK_WITHOUT_WORKING_HOURS` n'existe que pour `updateCalendar` et un import ; `HOURLY_RATE_MISSING` que dans `task_failed`.
- **Constat.** Chaque refus déclaré sans exemple est servi par le faux back sous la forme du premier exemple du statut, et le front ne l'éprouve jamais ; `FIELD_NOT_ACCEPTED` est le motif de trois opérations et du collage sans qu'aucune réponse le montre.
- **Proposition.** Un exemple engendré par `wftools.mockgestures`/`mockwrites` pour chacun : une ligne du monteur câbleur ajoutée à une tâche d'un rôle du week-end (`TASK_WITHOUT_WORKING_HOURS`, `createNode` et `updateEstimateLine`), un débours envoyé sur « Raccordement des borniers » (`FIELD_NOT_ACCEPTED`), une durée envoyée sur « Réception usine », un rôle retiré d'une ligne de main-d'œuvre (`RESOURCE_ROLE_REQUIRED`), une réestimation de « Ingénierie de détail » sous les études terminées (409 `task_not_completed`) ; nommer `COMPUTED_VALUE` dans le 422 d'`updateEstimateLine` ; décrire le 409 d'`applyPaste`.
- **DECISIONS.md** : « Les exemples manquants et les descriptions du contrat (US-0640/L1, #1329) » a soldé les mineurs d'EP-14 (#764, #803, #817, #747, #752, #795) ; aucun de ces refus n'y figure ; « L'horizon refuse les saisies… » (ligne 6395) écarte seulement l'exemple de `PROJECT_HORIZON_EXCEEDED` sur `moveNodes`, non signalé ici.

### F-18 — Deux descriptions qui disent moins que la règle

- **gravité** mineur ; **emplacement** `docs/api/components/parameters.yaml:106-113` (`NodeKinds` : « Restreint aux tâches ou aux lignes, selon la grille affichée ») ; `docs/api/components/schemas/revisions.yaml:1190-1194` (`TaskFacet.calendar_id` : « Calendrier applicable, résolu à la lecture : intersection des calendriers des rôles … ou calendrier par défaut ») ; **exigence** WF-PLA-0010 ; **ce que dit le contrat** : `listNodes` (ligne 671) : « `kinds` n'est pas un filtre : il choisit ce que la grille rend … et les totaux ne changent pas avec lui » ; `DECISIONS.md:7601` : « une intersection n'a pas d'identifiant ».
- **Constat.** Le paramètre dit « restreint » quand l'opération dit « n'est pas un filtre » : un implémenteur qui lit le paramètre seul en fera un filtre des totaux. `calendar_id` est nullable sans que la description dise quand (l'exemple `estimate_line_redated` rend « Montage des armoires sur site » avec `calendar_id: null` et des heures d'intersection) ; `calendar_hours` dit la règle, `calendar_id` non.
- **Proposition.** `NodeKinds` : « Choisit ce que la lecture rend, tâches ou lignes ; ce n'est pas un filtre, les totaux ne changent pas (`listNodes`) ». `calendar_id` : « nul quand le calendrier applicable est l'intersection de plusieurs calendriers, qui n'a pas d'identifiant ; `calendar_hours` porte alors les heures ».
- **DECISIONS.md** : #487 (ligne 1570, les totaux ne changent pas avec `kinds`) ; #1410 (lignes 7597-7601) pour `calendar_hours`.

### F-19 — Le 400 des deux lectures à paramètres

- **gravité** mineur ; **emplacement** `docs/api/paths/revisions.yaml:973-1022` (`getComputedValueDependencies` : 200, 401, 404, 422, 503 ; `field` est une énumération de requête), `858-908` (`resolveRowNumber`) ; **exigence** — ; **ce que dit le contrat** : `listNodes` (766) déclare le 400 ; `NodeFields` : « une propriété inconnue est refusée (400) » ; le README n'exige le 400 que des opérations à corps.
- **Constat.** Une valeur de `field` hors de `ComputedValueField` est-elle un 400 (comme `fields` de `listNodes`) ou un 422 `VALIDATION_FAILED` sur `/query/field` (comme `row_number` sur `/path/row_number`) ? Les deux conventions coexistent dans la même famille sans que l'opération le dise.
- **Proposition.** Dire dans le 422 de `getComputedValueDependencies` : « ou une valeur de `field` hors de l'énumération, `fields` sur `/query/field` », ou déclarer le 400 comme `listNodes`.
- **DECISIONS.md** : « Toute opération à corps déclare 400 et 422 (#748) » ; rien sur les lectures à paramètres énumérés.

### Ce qui est juste

Vérifié conforme : chaque attribut de WF-PLA-0130 est sur `TaskFacet` avec le type de WF-DAT-0100 (`Duration` dans son unité, `WorkInstant` date + heures, `PlanningDate` pour `started_on`/`completed_on`, marge en `Duration` signée, `physical_progress` en `Computable`, rattachement exclusif lot/poste avec libellé résolu) ; chaque attribut de WF-DEV-0020 sur `EstimateLineFacet` (quantité, charge, débours, délai de paiement entier ≥ 0 et nul pour la provision, quatre montants `Money`, sous-projet, rôle, `is_computed`, grandeurs précédentes de WF-RAE-0040) ; les quatre `LinkType`, les dix `DurationUnit` et `LagUnit` + `percent`, le décalage négatif ; `LINK_CYCLE` (`params.cycle` ordonné), `LINK_FORBIDDEN`, `PROJECT_HORIZON_EXCEEDED` (`params.task`), `NON_WORKING_DAY`, `VALUE_OUT_OF_RANGE` des heures, les six motifs du rattachement : chacun avec un exemple dont le code, le statut, le pointeur et les paramètres correspondent à la description (34 refus relus) ; `NodesWritten` rendu par les douze écritures, `PasteApplied` l'étend ; `computed_fields`/`editable_fields` cohérents avec le mode, la nature et l'état sur toutes les lectures (hors F-09, F-10, F-14) ; `nodes.json` : numéros de ligne 1–7 continus, parents présents, `position` à partir de 1, durée de 40 j = jours ouvrés du 2 mars au 24 avril, dates des successeurs exactes (FD −2 j, DD +1 sem), totaux = la ligne de 100 000, `physical_progress` 1, `finish_overdue` juste à la date du 3 juin ; les 33 `NodesWritten` : versions avancées des seuls nœuds écrits, ancêtres recalculés, `structure_lock_version` cohérent avec les suites (`following`), totaux qui bougent du montant écrit ; le tri (`estimate_sorted`, `estimate_hours`) garde `row_number` ; `resolveRowNumber` et ses trois exemples ; le collage (plan, partiel, rejugé, 412, trop large à 17 colonnes) ; les refus de `moveNodes` ; `getComputedValueDependencies` et ses huit exemples ; les filtres de `listNodes` qui existent ont une description et une exigence justes.

### Doutes

- **La création d'une tâche datée** (`TaskFacetWrite.start`/`finish` en `WorkInstant`, heures exigées, contre `WorkInstantWrite` en modification) : tranché par #1244 (« La création n'est pas touchée… suivra la même règle, par une modification du contrat »), que le gel rend coûteuse ; #1345 (US-0640/L6) touche `createNode` sur le jour chômé et pourrait la reprendre — hors de mon périmètre, mais à signaler au consolidateur.
- **`is_critical` d'une tâche en mode manuel** : `TaskFacet.is_critical` ne dit pas « fausse en mode manuel » (seul `NodeSchedule.is_critical` le dit) ; les fixtures le font. Mineur de description, non compté.
- **La grille de planning du front** (`frontend/src/components/grid/planning.tsx`) n'a pas non plus de colonnes `started_on`/`completed_on` : F-07 vaut pour le contrat ; la part front relève d'un autre lot.
- **`Duration.value` « jamais négative pour la durée d'une tâche »** : le schéma (`Decimal`) ne l'interdit pas et aucun refus n'est déclaré pour une durée négative (`VALUE_OUT_OF_RANGE` sur `/duration/value`, `minimum: 0` serait la forme du README) ; probablement couvert par « une valeur hors règle, `fields` la localisant », non compté.
- **`EstimateLineWrite.quantity` exigée pour une ligne de main-d'œuvre** : la spec dit « la charge, la quantité et le débours sont saisis » ; une valeur par défaut de 1 n'est pas dite — rien à signaler, mais le front doit l'envoyer.
- **`KanbanCommand`/`listStartableTasks`** et `undo`/`redo` ne sont pas de ma famille ; je n'en ai lu que ce que `setTaskProgress` et `NodesWritten` citent.

## Annexe G — Indicateurs et portefeuille


**Lu** : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/analysis.yaml` (453 l.) et
`docs/api/paths/portfolio.yaml` (286 l.) en entier ; `docs/api/components/schemas/indicators.yaml`
(594 l.) et `docs/api/components/schemas/portfolio.yaml` (348 l.) en entier ; dans `common.yaml`
`Decimal`, `Money`, `Hours`, `Percent`, `PaginationMeta`, `SortOrder` ; dans `parameters.yaml`
`Limit`, `Offset`, `Search`, `SortOrder`, `IndicatorsRevision`, `AsOf`, `Scope`, `WorkloadBasis`,
`PortfolioStates`, `PortfolioFrom`, `PortfolioTo`, `PortfolioOrgNode` ; `responses.yaml`
`PortfolioPeriodRefused` ; `reference.yaml` `AlertZone`, `IndexThresholds` ; `risks.yaml`
`RiskCoverageTotals` ; `projects.yaml` `ProjectState`, `Project.win_probability` ; `revisions.yaml`
`KanbanTask`, `NotStartedTask`. Spécification : §3.4.3 (l. 1440–1608), §3.4.4.4 (1872–1900),
§3.4.5.4.1 (2509–2525), §3.4.5.4.4 (2581–2597), §3.4.5.5.1 (2636–2652), §3.4.5.8 (2875–3096),
§4.6.2 (4259–4329), plus WF-DEV-0080 (l. 2571), WF-DAT-0040 (l. 4032), WF-PRJ-0090 (l. 2187),
WF-RAE-0030 (l. 2658). **46 fixtures ouvertes** (tous les témoins et refus référencés par les deux
fichiers de chemins, dont les sept de `fixtures/api/volume/`), les générateurs `mockportfolio.py`,
`mockportfoliotime.py`, `mockindicators.py` (en-tête), `mockcurves.py` (grep), et les sections de
`DECISIONS.md` citées plus bas. Les formules des indicateurs (avancement financier, consommation,
avancement physique, CPI, SPI, écarts, trois projections et leurs écarts) et les parts (devis, reste à
engager, structure des coûts) ont été recalculées en `Decimal` sur les fixtures du témoin et sur
`portfolio_performance.json`.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| G-01 | majeur | `docs/api/components/schemas/indicators.yaml:459` (`CurveSeries`), `paths/analysis.yaml:290` (`getCostCurve`), `:364` (`getEarnedValueCurves`), fixtures `cost_curve*.json`, `earned_value_curves.json` | La spec 1.0.0 impose le pas du mois aux courbes d'un projet ; le contrat ne dit aucun pas et les exemples portent un point par jour d'événement (756 points) | WF-IND-0100, WF-IND-0110, WF-DAT-0040 |
| G-02 | majeur | `indicators.yaml:270` (`ProjectIndicators.required`), `:333` (`Projections`), `:105` (`CalculationContext`), `:405` (`WorkloadPlan.roles[]`), `:175`/`:256` (`share`) ; `portfolio.yaml:158` (`PortfolioPerformance`), `:135`/`:146` (`PortfolioWorkload.roles[]`) | Des indicateurs que la spec exige sont facultatifs dans le schéma : avancements, écarts, écarts des projections, budget agrégé, capacité des rôles, zone des mois, parts ; le client engendré les voit `?` | WF-IND-0040 à 0080, WF-PTF-0060, WF-PTF-0070, WF-DEV-0060, WF-DEV-0070 |
| G-03 | majeur | `portfolio.yaml:190–198` (`PortfolioPerformance.quarterly`), `paths/portfolio.yaml:140–166` (`getPortfolioPerformance`), `parameters.yaml:402–412` (`PortfolioFrom`) | L'évolution trimestrielle n'a ni bornes ni date de lecture définies ; la fixture rend quatre trimestres avec `scope.from/to` nuls, contre la description de `PortfolioFrom` | WF-PTF-0070, WF-PTF-0010 |
| G-04 | majeur | `paths/portfolio.yaml:117–119` et `:238–240` (`horizon_months`) | Paramètre sans description ni défaut ; le faux back lui donne deux sens (6 mois à partir du mois courant ; 12 mois centrés sur la date de calcul) | WF-PTF-0060, WF-PTF-0100 |
| G-05 | majeur | `paths/portfolio.yaml:168–180` (`getPortfolioCostStructure`), `:222–247` (`getPortfolioCostCurve`), `:104–123` (`getPortfolioWorkload`), `:263–274` (`getPortfolioPilotHealth`) | Ces vues acceptent `states=completed` sans `from`/`to` : la « période qu'il fixe » des projets terminés n'est pas exprimable, le périmètre est indéfini | WF-PTF-0010 |
| G-06 | majeur | `portfolio.yaml:222–225` et `:249–253` (`PortfolioRisks`, `coverage`) | La couverture agrégée est dite sommée « sur les projets en cours » ; la spec la somme sur les projets en cours **et terminés** du périmètre | WF-PTF-0090 |
| G-07 | mineur | `indicators.yaml:216–222` (`RemainingIndicators.delta_to_reference`), `:245–250` (`SubprojectBalance.variance`) | Sens opposé au Vérif de WF-RAE-0020 (« + 50 » ; le contrat donne −50) ; décision de l'auteur #466 assumée, mais la spec 1.0.0 dit toujours l'inverse : à aligner côté spec avant le gel | WF-RAE-0020 |
| G-08 | mineur | `indicators.yaml:322–330` (`IndexValue`), `fixtures/api/volume/portfolio_performance.json`, `mockportfolio.py:412–419`, `mockportfoliotime.py:613` | La précision des indices n'est pas fixée ; la fixture du portefeuille les arrondit à deux décimales (0,94 pour 0,9410 exact, 0,91 pour 0,9088) | WF-PTF-0020, README « Une part… » |
| G-09 | mineur | `indicators.yaml:296` (`ProjectIndicators.actual_cost`) | « antérieure à la date de calcul » : la spec dit « antérieure **ou égale** » (et `getCostCurve` le dit bien) | WF-IND-0010 |
| G-10 | mineur | `indicators.yaml:288–290` (`planned_value`), `:361–363` (`WorkloadPlan`) | « étalées linéairement » / « interpolation linéaire » : la spec dit « au prorata des heures travaillées du calendrier de son rôle » ; la règle du reste à engager après la date de calcul n'est pas dite | WF-DEV-0080, WF-DEV-0070 |
| G-11 | mineur | `parameters.yaml:393–400` (`PortfolioStates`), `:359–366` (`AsOf`) | `states` admet `created`, `lost`, `abandoned` sans dire ce qu'en fait le portefeuille ; l'état « à cette date » du calcul passé n'est pas dit | WF-PTF-0010, WF-CYC-0130 |
| G-12 | mineur | `indicators.yaml:203`, `:345`, `:350`, `:355` | Renvoi à un schéma qui n'existe pas : `PortfolioProject.delta_to_reference` (le schéma est `PortfolioProjectRow`) | — |
| G-13 | mineur | `portfolio.yaml:154` (`roles[].months[].zone`), `paths/portfolio.yaml:137` (422 de `getPortfolioWorkload`) | La zone d'un mois du plan agrégé n'est pas décrite (alerte au-delà de 100 %, vigilance sous le seuil) ; le 422 ne dit pas ce qu'il refuse | WF-PTF-0060 |
| G-14 | mineur | `paths/portfolio.yaml:140–148`, `portfolio.yaml:156–159` (`PortfolioPerformance`) | La vue ne dit pas qu'elle se calcule sur les seuls projets en cours du périmètre ; `scope.states` rend `[in_progress]` pour une requête qui ajoutait le chiffrage | WF-PTF-0070 |
| G-15 | mineur | `fixtures/api/volume/portfolio_cost_structure.json`, `mockportfolio.py:505–511` | Le budget de référence agrégé reçoit 10 % de nature « Provision » (« the provision the rest »), alors que le budget de référence est hors lignes de provision et que celui du témoin n'en porte aucune | WF-PTF-0080, WF-IND-0020 |

### Constats

#### G-01 — Les courbes d'un projet au pas du mois
- **gravité** : majeur (frontal avec la spec ; le schéma peut porter la correction sans changer de forme, d'où « majeur » plutôt que « bloquant ») ; **emplacement** : `docs/api/components/schemas/indicators.yaml:459–531` (`CurveSeries`, description et `series[].points`), `docs/api/paths/analysis.yaml:290–313` (`getCostCurve`), `:364–375` (`getEarnedValueCurves`) ; fixtures `fixtures/api/cost_curve.json` (série `reference_budget` : 756 points datés 2026-02-01, 2026-03-31, 2026-04-10, 2026-04-26, 2026-04-30, 2026-05-01…), `cost_curve_payment_delays.json` (1 043 points), `cost_curve_amendment.json`, `earned_value_curves.json` (754 points) ; **exigence** : WF-IND-0100 (spec l. 3070) « Les courbes se calculent et se présentent au pas du mois, chaque point portant le cumul à la fin du mois ; la révision en cours et les révisions marquées sont présentées au même pas (WF-DAT-0040) » ; WF-IND-0110 (l. 3086), même phrase ; WF-DAT-0040 (l. 4032) « Les séries des courbes […] sont conservées avec eux, au pas du mois » ; **ce que dit le contrat** : `CurveSeries` « Séries temporelles cumulées. Les changements du budget de référence y apparaissent comme des marches datées » — aucun pas ; `getCostCurve` « deux points à cette date, avant et après » (résumé de `cost_curve.json`).
- **Constat.** La phrase « au pas du mois » a été ajoutée dans les trois exigences par les passes de cohérence des 9 et 10 octobre 2026 (commits 7dc06e9d et b18a8883 ; la révision 1.0.0 du 2026-10-24 n'a changé que le numéro de révision). Le contrat et ses exemples suivent encore la règle d'EP-02/L24 — « un point par jour où un montant commence ou finit, gardée » (`DECISIONS.md:2434`) — qui lui est antérieure. Un serveur écrit d'après le contrat rend des séries journalières que WF-DAT-0040 ne conserve pas à ce pas, et le front trace aujourd'hui des courbes qui ne seront pas celles de la cible ; la courbe du portefeuille (`PortfolioCostCurve`, un point par fin de mois, fixture `portfolio_cost_curve.json`) est déjà au pas du mois : les deux familles ne racontent pas la même histoire, ce que WF-PTF-0100 interdit (« rien recalculer ici, seulement sommer »). Après le gel, changer la nature des points (jour → fin de mois) change ce que tout client reçoit.
- **Proposition.** Dire le pas dans `CurveSeries` et le réaliser dans `mockcurves` :
  ```yaml
  CurveSeries:
    description: >-
      Séries cumulées au pas du mois, chaque point portant le cumul à la fin du mois
      (WF-IND-0100, WF-IND-0110) ; la date de calcul est un point de plus sur les séries
      qui s'y arrêtent ou en partent (`actual_cost`, `project_manager_projection`), une
      marche d'avenant deux points à sa date (`steps`). Les révisions marquées sont
      conservées et présentées au même pas (WF-DAT-0040).
  ```
  Ou, si l'auteur veut garder le point par jour pour la maquette, le dire dans DECISIONS et ouvrir un point d'annexe D sur les trois exigences — mais trancher avant le gel.
- **DECISIONS.md** : `:2008–2016` (« La série suit, à chaque jour, la référence en vigueur ce jour-là ») et `:2434–2435` (règle d'EP-02/L24 « gardée ») — toutes deux antérieures à la spec 1.0.0 et ne la citent pas.

#### G-02 — Indicateurs exigés par la spec, facultatifs dans le schéma
- **gravité** : majeur ; **emplacement** : `indicators.yaml:270–279` (`ProjectIndicators.required` sans `financial_progress`, `budget_consumption`, `physical_progress`, `cost_variance`, `schedule_variance`) ; `:333` (`Projections.required: [at_budget, project_manager, at_observed_rate]`, sans `variance_at_budget`, `variance_project_manager`, `variance_at_observed_rate`) ; `:105` (`CalculationContext.required: [revision_id, computed_at, scope]`, sans `is_stored` ni `revision_status`, dont toutes les descriptions font pourtant le pivot) ; `:405–410` (`WorkloadPlan.roles[].required: [resource_role_id, label, months]`, `capacity_monthly_hours` facultative) ; `:175`, `:256` (`share` facultative dans `ComputableAmountByKey` et `AmountByKey`) ; `portfolio.yaml:158` (`PortfolioPerformance.required` sans `reference_budget`, `cost_variance`, `schedule_variance`) ; `:135–139` (`PortfolioWorkload.roles[]`, `capacity_monthly_hours` facultative) ; `:146–154` (`months[].zone` facultative). Le client engendré le reflète : `frontend/src/api/generated/schema.d.ts:4934–4942` (`financial_progress?`, `cost_variance?`…), `:4916` (`variance_at_budget?`), `:4766–4771` (`revision_status?`, `is_stored?`), `:4832`, `:5431` (`capacity_monthly_hours?`), `:5449–5451`. **Exigences** : WF-IND-0040 « Tous deux sont exprimés en pourcentage et calculés par sous-projet et pour le projet » ; WF-IND-0050 « Les trois sont présentées ensemble, avec leur écart au budget de référence » ; WF-IND-0060 ; WF-IND-0070/0080 « Il est présenté avec l'écart de coût/de délai » ; WF-PTF-0070 « les écarts de coût et de délai cumulés ; les trois projections à terminaison agrégées face au budget de référence agrégé » ; WF-PTF-0060 « Il présente en regard la capacité de chaque rôle et le taux de charge […] en signalant les mois » ; WF-DEV-0070 « La capacité de chaque rôle y est présentée en regard de sa charge » ; WF-DEV-0060 et WF-PTF-0080 « en montant et en pourcentage ».
- **Constat.** Une réponse conforme au contrat peut omettre l'avancement financier, les écarts, les écarts des projections, le budget agrégé, la capacité d'un rôle ou la zone d'un mois : le front doit garder chaque champ contre `undefined`, et les modèles Pydantic du service les engendrent `Optional`. Rendre ces champs exigés après le gel resserre le contrat du côté du producteur — c'est le changement incompatible à faire maintenant. Le précédent existe : `under_load_threshold` a été rendu exigé pour cette raison exacte (« Facultatif, une réponse conforme pouvait l'omettre », `DECISIONS.md:799–804`).
- **Proposition.** Ajouter aux `required` : `ProjectIndicators` → `financial_progress, budget_consumption, physical_progress, cost_variance, schedule_variance` ; `Projections` → `variance_at_budget, variance_project_manager, variance_at_observed_rate` (nullable, déjà) ; `CalculationContext` → `is_stored` (et `revision_status`) ; `PortfolioPerformance` → `reference_budget, cost_variance, schedule_variance` ; `WorkloadPlan.roles[]` et `PortfolioWorkload.roles[]` → `capacity_monthly_hours` ; `PortfolioWorkload.roles[].months[]` → `zone` ; `AmountByKey`/`ComputableAmountByKey` → `share` (la part d'une répartition est toujours rendue ; pour un lot sans tâche elle est un `Computable` non calculable, déjà prévu). Toutes les fixtures les portent déjà : aucun exemple à toucher.
- **DECISIONS.md** : aucune décision sur le caractère facultatif de ces champs ; `:799–804` (US-0240/L5) pour le précédent.

#### G-03 — L'évolution trimestrielle : quels trimestres, lus à quelle date
- **gravité** : majeur ; **emplacement** : `portfolio.yaml:190–198` (`quarterly`, sans description) ; `paths/portfolio.yaml:145–148` (« L'évolution trimestrielle se calcule aux dates passées selon WF-PTF-0010 ») ; `parameters.yaml:402–412` (`PortfolioFrom` : « Sans l'une ni l'autre, les statistiques retiennent les douze mois qui finissent à la date de calcul, et la liste des projets aucune période ; `scope.from` et `scope.to` disent la période retenue ») ; fixture `fixtures/api/volume/portfolio_performance.json` (`scope.from: null, to: null`, quatre trimestres 2025-Q3 → 2026-Q2) ; générateur `mockportfolio.py:365–366` (`QUARTERS` constants), `:328` (`_scope(..., period=False)`), `mockportfoliotime.py:558–563` (`_quarter_end` : dernier jour du trimestre, aujourd'hui pour le dernier). **Exigence** : WF-PTF-0070 « l'évolution des deux indices agrégés par trimestre, calculée aux dates passées selon WF-PTF-0010 ».
- **Constat.** Le contrat ne dit ni combien de trimestres la vue rend (la période `from`/`to` ? un nombre fixe ? depuis le premier projet en cours ?), ni à quelle date de chaque trimestre l'indice est lu (fin du trimestre, comme le fait le générateur), ni si le trimestre courant est lu à la date de calcul. `getPortfolioPerformance` prend `from`/`to`, et `PortfolioFrom` dit que toute statistique de période rend la période retenue dans `scope` — mais la fixture rend `from`/`to` nuls avec quatre trimestres qui sont exactement la période par défaut. Un implémenteur du service ne peut que deviner ; le front (`portfolio-charts.tsx:43`, `QuarterlyChart`) trace ce qu'il reçoit.
- **Proposition.** Décrire `quarterly` et remplir `scope.from`/`to` :
  ```yaml
  quarterly:
    type: array
    description: >-
      Un point par trimestre civil que la période touche (`from`, `to` ; par défaut les
      douze mois qui finissent à la date de calcul, `scope.from` et `scope.to`), du plus
      ancien au plus récent : chaque indice est le rapport des sommes des projets en cours
      à cette date (WF-PTF-0020), lu au dernier jour du trimestre selon WF-PTF-0010, et à
      la date de calcul pour le trimestre qui la contient.
  ```
  et `_scope(rows, ["in_progress"], period=True)` dans `portfolio_performance`.
- **DECISIONS.md** : `:771–772` et `:2167–2170` disent ce que fait le générateur (« de 2025-T3 à 2026-T2 », « chaque trimestre à sa fin — aujourd'hui pour le dernier ») ; rien ne le porte au contrat. `:794–800` (« La période des statistiques, par défaut ») ne nomme pas l'évolution parmi les statistiques de période.

#### G-04 — `horizon_months` sans description, et deux sens dans le faux back
- **gravité** : majeur ; **emplacement** : `paths/portfolio.yaml:117–119` (`getPortfolioWorkload`) et `:238–240` (`getPortfolioCostCurve`) : `- name: horizon_months / in: query / schema: { type: integer, minimum: 1, maximum: 240 }`, sans `description` ni `default` ; réponses : `PortfolioWorkload.months` « Les mois de l'horizon » (`portfolio.yaml:113–118`), `PortfolioCostCurve` sans écho de l'horizon. **Exigences** : WF-PTF-0060 « s'étend sur un horizon choisi » ; WF-PTF-0100 « mois par mois et sur l'horizon choisi ».
- **Constat.** Le générateur donne au même paramètre deux lectures : pour le plan de charge, `HORIZON = 6`, « the month of today the first » (`mockportfoliotime.py:80–81` ; fixture `portfolio_workload.json` : 2026-06 → 2026-11) ; pour la courbe en S, `CURVE_MONTHS = 12` centrés sur la date de calcul, six mois avant et six après (`mockportfoliotime.py:83`, `:443` ; fixture `portfolio_cost_curve.json` : 2025-12-31 → 2026-11-30). Rien dans le contrat ne dit si l'horizon part du mois de la date de calcul, s'il compte des mois passés, ni ce que vaut un appel sans horizon. Le front conserve la valeur en préférence (`frontend/src/components/portfolio/address.ts:46`, tests à 12, 24, 36, 240) sans savoir ce qu'elle désigne.
- **Proposition.** Une description par opération, et un défaut :
  ```yaml
  - name: horizon_months
    in: query
    description: >-
      Nombre de mois du plan, le mois de la date de calcul le premier (WF-PTF-0060) ;
      absent, six.
    schema: { type: integer, minimum: 1, maximum: 240, default: 6 }
  ```
  et pour la courbe, dire si et combien de mois passés précèdent la date de calcul (la fixture en montre six) : par exemple « les `horizon_months` mois qui suivent la date de calcul, précédés des douze mois qui la précèdent », ou un second paramètre. À trancher par l'auteur.
- **DECISIONS.md** : `:1118–1121` (#326, les mois en tête de la réponse) et `:2176–2203` (C7, le générateur) ; aucune sur le sens du paramètre.

#### G-05 — Quatre vues admettent les projets terminés sans période
- **gravité** : majeur ; **emplacement** : `paths/portfolio.yaml:168–180` (`getPortfolioCostStructure` : `PortfolioStates`, `AsOf`, `PortfolioOrgNode`), `:222–247` (`getPortfolioCostCurve` : `PortfolioStates`, `AsOf`, `horizon_months`, `payment_delays`), `:104–123` (`getPortfolioWorkload`), `:263–274` (`getPortfolioPilotHealth`) ; `parameters.yaml:393–400` (`PortfolioStates`, tout `ProjectState`) ; `parameters.yaml:402–412` (`PortfolioFrom` : « pour les projets terminés et les statistiques de période […] la liste des projets aucune période »). **Exigence** : WF-PTF-0010 « Toute vue du portefeuille se calcule sur un périmètre choisi par l'utilisateur : les projets en cours, auxquels il peut ajouter les projets en chiffrage, et les projets terminés d'une période qu'il fixe ».
- **Constat.** Ces quatre vues reçoivent `states=completed` (le front le fait : `kept-workload-address.test.ts:58`, `kept-workload.dom.test.tsx:49`) mais n'ont ni `from` ni `to` : quels projets terminés entrent — tous (600 sur vingt ans, §4.6.2, tableau 14), ceux des douze derniers mois par défaut, aucun ? Pour la structure des coûts et la courbe en S, un projet terminé a un budget de référence et des courbes, et la question est réelle ; pour le plan de charge (reste à engager des projets en cours, WF-PTF-0060) et la santé du pilotage (projets en cours, WF-PTF-0110), le contrat devrait au moins dire que `completed` n'y change rien. `PortfolioScope` porte déjà `from`/`to` pour le rendre.
- **Proposition.** Ajouter `PortfolioFrom`, `PortfolioTo` et le 422 `PortfolioPeriodRefused` à `getPortfolioCostStructure` et `getPortfolioCostCurve`, avec la même règle de période par défaut ; dire dans `getPortfolioWorkload` et `getPortfolioPilotHealth` que seuls les projets en cours (et en chiffrage pour la charge) contribuent, les autres états nommés étant sans effet.
- **DECISIONS.md** : `:3404–3411` (le 422 des quatre vues qui prennent `from`/`to`) ; `:794–800` ; aucune sur les quatre autres vues face aux projets terminés.

#### G-06 — La couverture agrégée oublie les projets terminés
- **gravité** : majeur ; **emplacement** : `portfolio.yaml:222–225` (« chaque montant est la somme de celui des projets en cours du périmètre ») et `:249–253` (« la somme des réserves de référence des projets en cours, face aux sommes de leurs provisions restantes et du coût de leurs risques survenus ») ; `paths/portfolio.yaml:199–203`. **Exigence** : WF-PTF-0090 (spec l. 1566) « la réserve et la couverture ne portent que sur les projets en cours **et terminés** du périmètre, un projet en chiffrage n'ayant pas de référence » ; Vérif : « Un projet terminé inclus dans le périmètre compte dans la réserve agrégée et dans l'écart de couverture agrégé ».
- **Constat.** La description exclut les projets terminés que la spec inclut explicitement ; un service écrit d'après elle les laisserait hors de la réserve agrégée, et le Vérif échouerait. La décision citée décrit le faux back, où aucun projet du périmètre n'est terminé, pas une règle contraire à la spec.
- **Proposition.** `portfolio.yaml:223–225` et `:250–253` : « la somme de celui des projets en cours et terminés du périmètre ; un projet en chiffrage n'y entre pas, n'ayant pas de référence (WF-PTF-0090) ». Idem pour `identified_total`/`heaviest`/`matrix`, qui comptent aussi les risques d'un projet en chiffrage inclus, « sans pondération » — à dire.
- **DECISIONS.md** : `:2242–2246` (« La couverture agrégée est la somme de celles des projets en cours ») et `:1156` : les deux parlent de l'exemple ; ni l'une ni l'autre ne tranche contre la spec.

#### G-07 — Le sens de la marge du reste à engager contre le Vérif de WF-RAE-0020
- **gravité** : mineur (décision de l'auteur ; la correction est côté spécification) ; **emplacement** : `indicators.yaml:216–222` (`RemainingIndicators.delta_to_reference` : « budget 1 000, coût réel 500, reste à engager 550, marge -50 »), `:245–250` (`SubprojectBalance.variance`), fixture `remaining_indicators.json` (`delta_to_reference: "-3275301.28"`, `variance: "-1037316.10"`). **Exigence** : WF-RAE-0020 (spec l. 2642) « deux écarts, signés dans le sens de la dérive — positifs lorsque le projet coûte plus que prévu : la projection du chef de projet […] moins le budget de référence » ; Vérif « l'écart au budget vaut + 50 ».
- **Constat.** Le contrat rend l'opposé du nombre que la spec donne en Vérif. `DECISIONS.md:1521–1552` (#466, « décision de l'auteur du 2026-10-07 ») l'assume : « le reste à engager parle de marge […] le portefeuille et les projections parlent d'écart ». La décision est claire et les descriptions la disent ; mais la spec publiée en 1.0.0 le 2026-10-24, après la décision, garde le texte et le Vérif opposés. Au gel, la traçabilité `make inventory` citera une exigence que l'opération contredit ; le point est à aligner (texte ou annexe D), pas le contrat.
- **Proposition.** Ouvrir le point sur WF-RAE-0020 (corps : « la marge sur le budget de référence : le budget de référence moins la projection du chef de projet, positive quand il en reste » ; Vérif : « − 50 »), ou à défaut le consigner en annexe D ; le contrat ne change pas.
- **DECISIONS.md** : `:1521–1552` (section « La marge du reste à engager a un seul sens », #466).

#### G-08 — Précision des indices : non fixée, et deux décimales dans la fixture du portefeuille
- **gravité** : mineur ; **emplacement** : `indicators.yaml:322–330` (`IndexValue`, `value: Computable`, sans précision) ; `fixtures/api/volume/portfolio_performance.json` : `cost_index.value "0.94"`, `schedule_index.value "0.91"`, `quarterly[].cost_index "0.94"` ; générateur `mockportfolio.py:412–419` (`_ratio_index` : `(numerator / denominator).quantize(CENT)`), `mockportfoliotime.py:613` (idem pour les trimestres). **Exigence** : WF-PTF-0020 Vérif « un indice de coût de portefeuille de 0,917 » ; README « Une part, un avancement ou un taux calculé — le rapport de deux grandeurs […] est un décimal exact donné à quatre décimales ».
- **Constat.** Recalculé depuis la fixture elle-même (`at_observed_rate` = BR·AC/EV et `cost_variance` = EV−AC donnent EV = 1 209 292 319,32 et AC = 1 285 133 439,69) : l'indice de coût exact vaut 0,9410 et l'indice de délai 0,9088 ; la fixture les rend `0.94` et `0.91`, un arrondi au centième que le README n'admet pour aucun rapport calculé, et que `DECISIONS.md:4702` contredit (« Les indices (`IndexValue`), que le faux back donne aussi à quatre décimales, ne sont pas traités : #694 ne les nomme pas »). Les indices du témoin sont bien à quatre décimales (`1.0261`, `0.8674`). Le contrat, lui, ne dit la précision d'aucun indice : un client ne sait pas combien de décimales attendre.
- **Proposition.** `IndexValue.value` : « L'indice, à quatre décimales (README, « Une part… »), le rapport de deux grandeurs » ; `_ratio_index` et `quarterly` : `share(...)` de `mockstructure` au lieu de `quantize(CENT)` ; régénérer.
- **DECISIONS.md** : `:4664–4706` (#694) — les indices explicitement « non traités ».

#### G-09 — « antérieure » pour « antérieure ou égale »
- **gravité** : mineur ; **emplacement** : `indicators.yaml:296` : `actual_cost` « Lignes du périmètre suivi dont la date de pièce est antérieure à la date de calcul (WF-IND-0010) ». **Exigence** : WF-IND-0010 « dont la date de pièce est antérieure ou égale à cette date » ; `getCostCurve` (`analysis.yaml:305–306`) et `IndicatorsRevision` (`parameters.yaml:350`) le disent correctement.
- **Constat.** Une pièce datée du jour du calcul entre dans le coût réel ; la description l'exclut. Un implémenteur qui lit le schéma plutôt que la spec se trompe d'un jour, et les deux lectures du même contrat divergent.
- **Proposition.** « dont la date de pièce est antérieure ou égale à la date de calcul (WF-IND-0010) ».
- **DECISIONS.md** : aucune décision.

#### G-10 — « linéaire » pour « au prorata des heures travaillées »
- **gravité** : mineur ; **emplacement** : `indicators.yaml:288–290` (`planned_value` : « étalées linéairement sur la durée de leur tâche dans la révision de référence (WF-DEV-0080) ») ; `:361–363` (`WorkloadPlan` : « la charge d'une ligne étant répartie sur la durée de sa tâche par interpolation linéaire (WF-DEV-0070) »). **Exigences** : WF-DEV-0080 « étalé sur la durée de leur tâche au prorata des heures travaillées — sur le calendrier de son rôle pour une ligne de main-d'œuvre, sur le calendrier applicable de la tâche sinon » ; WF-DEV-0070 « répartie sur la durée de la tâche qui la porte au prorata des heures travaillées du calendrier de son rôle […] la charge restante […] est répartie sur la seule part de la durée de la tâche postérieure à la date de calcul, et portée au mois de la date de calcul lorsque la fin de la tâche est dépassée ».
- **Constat.** « Linéaire » (en jours civils) et « au prorata des heures travaillées » ne donnent pas les mêmes points dès qu'un calendrier a des jours chômés : les deux descriptions contredisent la spec, et le générateur lui-même fait le prorata (`DECISIONS.md:1972–1974`). `WorkloadPlan` ne dit pas non plus la règle de la base « reste à engager » (rien avant la date de calcul, report au mois de la date de calcul), que la fixture `workload.json` applique (« aucun mois passé »).
- **Proposition.** `planned_value` : « au prorata des heures travaillées du calendrier de son rôle, telle que la révision de référence la date (WF-DEV-0080) » ; `WorkloadPlan` : « au prorata des heures travaillées du calendrier de son rôle ; sur une base de reste à engager, la charge restante d'une tâche non terminée sur la seule part de sa durée postérieure à la date de calcul, portée au mois de la date de calcul quand sa fin est dépassée (WF-DEV-0070) ».
- **DECISIONS.md** : `:1969–1975` (les formules du générateur : prorata) ; aucune n'assume « linéaire ».

#### G-11 — Les états hors périmètre, et l'état « à cette date »
- **gravité** : mineur ; **emplacement** : `parameters.yaml:393–400` (`PortfolioStates` : `items: ProjectState`, « Par défaut, les projets en cours ») ; `:359–366` (`AsOf`) ; `portfolio.yaml:6–28` (`PortfolioScope`). **Exigence** : WF-PTF-0010 « les projets en cours, auxquels il peut ajouter les projets en chiffrage, et les projets terminés d'une période qu'il fixe […] À une date passée, [un projet] est retenu dans le périmètre selon l'état qu'il avait à cette date (WF-CYC-0130) ».
- **Constat.** `states=created`, `lost` ou `abandoned` sont acceptés par le schéma ; aucune vue ne déclare de refus et aucune description ne dit si ces états sont ignorés ou comptés (une offre perdue a un devis : entre-t-elle au pipeline ?). L'énumération complète tient à `listProjects`, qui partage le paramètre (`DECISIONS.md:3124–3133`) — raison du type, pas du comportement. Par ailleurs, la règle de l'état à la date de calcul n'est écrite ni dans `AsOf` ni dans `PortfolioStates`, alors que le faux back l'applique (`portfolio_cost_curve_credit.json` : « les 198 projets alors en cours — le projet témoin, encore en chiffrage, n'en est pas »).
- **Proposition.** Dans `PortfolioStates` : « Pour le portefeuille, seuls `in_progress`, `pricing` et `completed` sont retenus (WF-PTF-0010) ; un autre état est refusé par 422 `VALIDATION_FAILED`, `fields[]` désignant `/query/states` par `VALUE_OUT_OF_RANGE` » (ou « est sans effet », à trancher) ; « À une date passée (`as_of`), un projet est retenu selon l'état qu'il avait à cette date (WF-CYC-0130) ».
- **DECISIONS.md** : `:3124–3133` (#536, paramètre partagé) ; aucune sur les trois états ni sur l'état à la date.

#### G-12 — `PortfolioProject` n'existe pas
- **gravité** : mineur ; **emplacement** : `indicators.yaml:203` (`RemainingIndicators` : « `PortfolioProject.delta_to_reference` »), `:345`, `:350`, `:355` (`Projections.variance_*` : « au sens de `PortfolioProject.delta_to_reference` ») ; le schéma de la ligne est `PortfolioProjectRow` (`portfolio.yaml:30`). **Exigence** : — (cohérence interne).
- **Constat.** Quatre descriptions renvoient à un nom de schéma absent du contrat ; un lecteur cherche en vain.
- **Proposition.** Remplacer par `PortfolioProjectRow.delta_to_reference`.
- **DECISIONS.md** : `:1538` emploie le même nom fautif.

#### G-13 — La zone d'un mois du plan agrégé, et le 422 du plan agrégé
- **gravité** : mineur ; **emplacement** : `portfolio.yaml:154` (`zone: { $ref: reference.yaml#/AlertZone }`, sans description) ; `paths/portfolio.yaml:137` (`'422': UnprocessableEntity`, générique). **Exigence** : WF-PTF-0060 « en signalant les mois où il dépasse 100 % et ceux où il est inférieur à un seuil que l'utilisateur choisit ».
- **Constat.** Le plan du projet décrit sa zone (`WorkloadZone`, `indicators.yaml:421–430`) ; le plan agrégé, qui porte la vraie règle (alerte au-delà de 100 %, vigilance sous le seuil, un rôle sans charge en vigilance — fixture `portfolio_workload.json`, monteur câbleur `load_ratio "0"`, `zone "watch"`), ne la dit nulle part ; le front ne doit rien en déduire (WF-IHM-0070), mais le serveur doit la connaître. Le 422 ne dit pas ce qu'il refuse (`under_load_threshold` hors de [0, 1] ? `horizon_months` hors bornes ? un `org_node_id` inconnu, comme `getProjectWorkload` le déclare par `/query/org_node_id`).
- **Proposition.** `zone` : « La zone du mois, classée par le serveur : `alert` quand la charge dépasse la capacité, `watch` quand le taux de charge est sous `under_load_threshold`, un rôle sans charge compris, `nominal` sinon (WF-PTF-0060, WF-IHM-0070) » ; 422 : nommer `/query/org_node_id` (inconnu) et `/query/under_load_threshold` (`VALUE_OUT_OF_RANGE`).
- **DECISIONS.md** : `:2215–2230` (le taux de charge propre au plan agrégé) ; rien sur la zone ni sur le 422.

#### G-14 — La performance se calcule sur les projets en cours, sans le dire
- **gravité** : mineur ; **emplacement** : `paths/portfolio.yaml:140–148`, `portfolio.yaml:156–159` ; fixture `fixtures/api/volume/portfolio_performance.json` (`scope.states: ["in_progress"]`, `project_count: 269`) à côté de `portfolio_value.json` (`["in_progress","pricing"]`, 300) pour la même requête d'exemple. **Exigence** : WF-PTF-0070 « présente, sur les projets en cours du périmètre : … ».
- **Constat.** Ni l'opération ni le schéma ne disent que les projets en chiffrage, même ajoutés au périmètre, ne contribuent pas aux indices ni aux projections ; et `PortfolioScope.states` rend tantôt les états demandés (valeur), tantôt les états effectivement sommés (performance) : « Périmètre effectivement retenu » (`portfolio.yaml:9`) laisse les deux lectures.
- **Proposition.** Description de `getPortfolioPerformance` : « sur les seuls projets en cours du périmètre (WF-PTF-0070) ; `scope.states` nomme les états demandés » (ou « retenus », mais la même règle pour toutes les vues).
- **DECISIONS.md** : `:767–772` (le générateur) ; aucune sur le sens de `scope.states`.

#### G-15 — Un dixième de « Provision » dans le budget de référence agrégé
- **gravité** : mineur (exemple) ; **emplacement** : `fixtures/api/volume/portfolio_cost_structure.json` (`budget_by_cost_type` : Main-d'œuvre 0,55, Débours 0,35, **Provision 0,1** — 266 262 019,77 sur 2 662 620 197,64) ; générateur `mockportfolio.py:451–452`, `:505–511` (`_parts` : « the provision the rest »). **Exigence** : WF-PTF-0080 Vérif « Une offre incluse […] dont le devis porte une ligne de provision pour risques de 50 n'ajoute rien à la nature de cette ligne dans le budget agrégé » ; WF-IND-0020 « le budget de référence […] hors lignes de provision » ; le témoin : `project_indicators.json` « budget de référence de 65 430 697,64, hors provisions », et sa seule nature « Provision » est la provision du risque identifié (`estimate_indicators.json`, 500 000,00 = `provisions_identified`).
- **Constat.** Le budget de référence agrégé — qui égale le carnet, 2 662 620 197,64 — porte dix pour cent de nature « Provision », nature que les lignes de provision pour risques, exclues du budget de référence, sont seules à porter dans l'univers témoin. Pour le témoin au moins, la part est inventée ; la fixture suggère au front qu'un budget de référence porte des provisions pour risques. Des lignes d'aléas de nature « Provision » rendraient la fixture possible, mais rien ne le dit.
- **Proposition.** Soit retirer la nature « Provision » du budget de référence agrégé dans le générateur (la garder dans le reste à engager, où elle est due), soit le dire dans le résumé de la fixture (« provisions pour aléas, hors provisions pour risques »).
- **DECISIONS.md** : `:772–775` (« le budget et le reste à engager par nature, dont les parts somment à un ») ; rien sur la nature des provisions du budget.

### Ce qui est juste

- **Formules et fixtures du témoin.** Sur `project_indicators.json` : avancement financier 0,0206 = AC/(AC+RAE), consommation 0,0216 = AC/BR, avancement physique 0,0222 = EV/BR, CPI 1,0261 = EV/AC, SPI 0,8674 = EV/PV (zone `watch` aux seuils 0,9/0,8), écarts 36 888,13 et −221 599,80, projection au budget 65 393 809,51 = AC + (BR − EV), chef de projet 68 705 998,92 = AC + RAE, rythme constaté 63 765 972,18 = BR·AC/EV, les trois écarts aux budgets — tous exacts à la décimale, dans le sens des descriptions. `project_indicators_marked.json` : indices non calculables (`no_actual_cost`, `no_planned_value`), zone nulle, `variance_at_observed_rate` nul, conformes à WF-IND-0010. Parts du devis (`estimate_indicators*.json`) et du reste à engager : quatre décimales, somme exactement 1 par nature et par sous-projet, plancher `0.00003` pour 0,0000309 (README) ; `by_subproject` du reste à engager : budgets, coûts réels et restes somment au projet, marges et couverture (850 060 − 500 000 − 200 = 349 860) exactes. `portfolio_value` : taux de transformation 0,4 (Vérif WF-PTF-0050) ; `portfolio_performance` : répartition par zone 169+47+53 = 152+58+59 = 269, projections agrégées cohérentes (écart au budget = −écart de coût), rythme constaté = BR/CPI exact (Vérif WF-PTF-0070, 2 222 et non 2 250).
- **Contrat.** Chaque indicateur de §3.4.5.8 a son champ, `Computable` partout où un dénominateur peut être nul (`cost_index`, `schedule_index`, `financial_progress`, `budget_consumption`, `physical_progress`, `at_observed_rate`, `load_ratio`, `conversion_rate`, parts), et `NotComputableReason` couvre chaque cas de la spec ; les noms `cost_index`, `schedule_index`, `IndexValue`, `Projections`, `cost_variance`, `schedule_variance`, `AlertZone` sont les mêmes dans `indicators.yaml` et `portfolio.yaml` ; les signes des écarts du portefeuille et des projections suivent le Vérif de WF-PTF-0040 (1 050 pour 1 000 → 50). `getPortfolioProjects` porte chaque colonne de WF-PTF-0040, un `sort_by` par colonne, les filtres état/période/recherche (plus `zones`), la pagination (`Limit` ≤ 500 pour 300 projets, fixtures de 300 et de la page 51–100), `can_open` pour WF-PTF-0030 ; `PortfolioStates` par défaut `in_progress` (WF-PTF-0010). Les refus déclarés ont leur exemple (409 état, 409 offre, 422 `scope`, 422 `revision_id`+`as_of`, 409/422 du plan de charge, 422 des périodes, borne ouverte comprise) ; `getMilestoneTracking`, `getIndexHistory`, `PilotHealth` (quatre codes) et `getPortfolioValue` suivent leur exigence ; la courbe du portefeuille est au pas du mois avec `cash_out_by_month`, un mois net négatif admis (avoirs).

### Doutes

- `getPortfolioProjects` prend `PortfolioOrgNode` (`paths/portfolio.yaml:22`) : sur une liste de projets, le filtre « ne restreint que les lignes de main-d'œuvre » — restreint-il le budget, la projection et les indices de chaque ligne à la main-d'œuvre du nœud, ou n'a-t-il aucun effet et ne fait-il que remplir `scope.org_node_id` ? Non dit, non tranché ici.
- `getEstimateIndicators` prend `Scope` (`analysis.yaml:22`) : restreint à un sous-projet, que deviennent `by_subproject` (une seule clé ?) et `by_work_package` (le sous-arbre croisé au sous-projet ?) ; aucun exemple ne le montre.
- `PilotHealth.signals` n'est ni paginé ni filtrable par `code` : jusqu'à quatre signaux par projet, 212 dans la fixture, de l'ordre du millier possible à 300 projets ; la spec ne demande pas de pagination, le §4.6.2 vise 2 s pour la vue — probablement acceptable, non vérifié.
- `getIndexHistory` : « le dernier point au jour courant pour la révision en cours » — sur un projet sans révision en cours, WF-IND-0010/WF-IND-0130 veulent un dernier point au jour courant calculé sur la dernière révision marquée avec le coût réel du jour ; `IndexHistoryPoint.version_name` « nul pour la révision en cours » ne couvre pas ce cas. Non tranché.
- `PortfolioRisks.period_outcome` (provisions survenues et écartées de la période) n'est dans aucune exigence du §3.4.3.5 ; ajout utile, à citer dans DECISIONS s'il ne l'est pas (`:778` ne le nomme pas).
- `MilestoneTracking.points[].marked_at` sert aussi au point de terminaison (`2026-04-24T00:00:00Z`, qui n'est le marquage d'aucune révision) : conforme à WF-IND-0090 (« la courbe d'un jalon s'arrête par un point à sa date de terminaison ») mais le nom du champ et la description (« date de marquage ») ne le disent pas.
- `PortfolioProjectRow.current_estimate` nul pour l'offre témoin (PRJ-002) : le générateur dit « the offer, without revision, has neither budget nor index » (`mockportfolio.py:153–154`) — cohérent si l'offre n'a aucune révision ; non vérifié contre les fixtures de l'offre.

## Annexe H — Risques et provisions


**Lu** : `docs/api/README.md` (Conventions, en entier) ; `docs/api/paths/risks.yaml` (478 l., en entier) ; `docs/api/components/schemas/risks.yaml` (518 l., en entier) ; `parameters.yaml` (`RiskId`, `RiskRevision`), `responses.yaml` (`Conflict`, `UnprocessableEntity`, `PreconditionFailed`), `common.yaml` (`Decimal`, `Percent`, `Money`, `PlanningDate`, `Audit`, `LockVersion`, `ErrorCode`, `BackgroundTaskRef.kind`), `reference.yaml` (`RiskMatrixSettings`, `AlertZone`), `projects.yaml` (`CommandCondition`, `ProjectCommand`), `revisions.yaml` (`RevisionCommand`, `ComputedDependency`, `Node.budgeted_amount`, `NodesWritten`, `deleteNode` dans `paths/revisions.yaml`), `portfolio.yaml` (`getPortfolioRisks`, `PortfolioRisks`), `indicators.yaml` (`CalculationContext`, `Computable`, `RemainingIndicators.coverage`). Spécification : §3.2.6 (840–878), WF-REV-0100 (2022–2030), §3.4.4.3 (1856–1872), §3.4.5.6 en entier (2698–2807), §4.4.1 (3847–3905), glossaire (4780–4848), §4.6.2 (volumes). **26 fixtures ouvertes** (`risks`, `risks_empty`, `risk`, `risk_created`, `risk_updated`, `risk_occurred_detail`, `risk_reviewed`, `risk_dismissed`, `risk_reidentified`, `risk_reviews`, `risk_reviews_reviewed`, `risk_coverage`, `risk_matrix_no_basis`, `task_occurrence_queued`, `reference_settings` (bornes), et les onze refus `risk_*`). Générateurs : `mockhistory.py` (`risk_item`, `matrix_cell`, `matrix_point`, `totals`), `mockwitnessrisks.py` (`reference_provision`), `mockriskwrites.py` (en-tête, `RISK_SCALE`, `REFERENCE_PROVISION_751`). `DECISIONS.md` : grep de chaque constat (sections citées), `INVENTORY.md` (lignes 209–222, 262), `EP-16-maquette-durcissement.md` (opérations modifiées, constats reportés, US-0680). Exclu : ce que portent US-0640/L6, US-0680/L1, US-0700/L1, US-0640/L5.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| H-01 | bloquant | `docs/api/components/schemas/risks.yaml:489-507` (`RiskCoverageTotals.occurred_cost`), `docs/api/paths/risks.yaml:431-435` (`getProjectRiskCoverage`) | Le coût des risques survenus de la couverture est défini comme le **montant réestimé** des lignes fusionnées ; la spec (révision 1.0.0) le définit comme le **coût à la survenance**, figé, que ni réestimation ni terminaison ne changent | WF-RIS-0050, WF-RIS-0010, glossaire « Coût à la survenance » |
| H-02 | majeur | `docs/api/components/schemas/risks.yaml:10-140` (`Risk`) | Le risque n'a aucun attribut pour le **coût à la survenance** que la spec lui fait conserver, donnée révisionnée du §4.4.1 | WF-RIS-0010, WF-RIS-0020, §4.4.1 |
| H-03 | majeur | `docs/api/components/schemas/risks.yaml:46-51` (`Risk.provision_amount`), `docs/api/components/parameters.yaml:281-282` (`RiskRevision`) | Le sens de `provision_amount` pour un risque survenu ou écarté n'est pas dit : le paramètre dit « celle de la révision de référence », le générateur rend gravité × probabilité ; les totaux somment la provision de référence ; les fixtures coïncident par hasard | WF-RIS-0040, WF-RIS-0050 |
| H-04 | majeur | `docs/api/components/schemas/risks.yaml:264-275` (`RiskUpdate`), `docs/api/paths/risks.yaml:169-236` (`updateRisk`) | `updateRisk` reçoit `probability` (exigée) sans dire si sa modification produit un réexamen daté ; pour la spec, modifier la probabilité **est** un réexamen, et l'historique doit en montrer l'évolution | WF-RIS-0010, WF-RIS-0040 |
| H-05 | majeur | `docs/api/paths/revisions.yaml:912-970` (`deleteNode`), `docs/api/components/schemas/revisions.yaml` (`NodesWritten`) — hors `paths/risks.yaml`, règle de WF-RIS-0010 | La suppression par saisie de la tâche qui porte une ligne de provision n'est pas décrite (report sur la parente, signalé par la confirmation) et le refus de supprimer la dernière tâche d'une structure principale portant une provision, « en nommant le risque », n'est pas déclaré | WF-RIS-0010 |
| H-06 | mineur | `docs/api/components/schemas/risks.yaml:362-364, 451-452`, `docs/api/paths/risks.yaml:460-461`, `docs/api/components/schemas/reference.yaml:822-823` | Les bornes et niveaux de gravité sont dits « en pourcentage du **budget de référence** » ; la spec dit « de l'**assiette** du projet » (budget de référence ou, avant lui, total hors provisions du devis courant), ce que `severity_ratio` et `RiskMatrixCell` disent déjà | WF-REF-0160 |
| H-07 | mineur | `docs/api/components/schemas/risks.yaml:12-29` (`Risk.required`) | `description`, `mitigation_notes`, `provision_node_id`, `matrix_cell`, `last_review_on` ne sont pas `required` alors que toutes les fixtures les rendent, que `listRisks` les promet, et que la décision #786 dit `provision_node_id` « exigé » comme `provision_task` | WF-RIS-0040 |
| H-08 | mineur | `docs/api/paths/risks.yaml:422` (`declareRiskOccurrence`, 409) | 409 générique `Conflict` : aucune condition nommée (`risk_identified`, `project_not_terminal`, `no_background_task_running`, `may_create_revision`), aucun exemple, alors que les quatre autres saisies du risque nomment les leurs | WF-RIS-0020, WF-RIS-0060 |
| H-09 | mineur | `docs/api/paths/risks.yaml:14-19` (`states`), `:206-215`, `:349-362`, `:265-270` (409 d'`updateRisk`, `reviewRisk`, `deleteRisk`) | `states` sans description ; les 409 des trois saisies ne mentionnent pas les conditions d'état d'`edit_risks` que `createRisk` liste (`project_not_terminal`, `no_background_task_running`) | WF-RIS-0040, WF-IHM-0090 |
| H-10 | mineur | `docs/api/components/schemas/portfolio.yaml:247-253` (`PortfolioRisks.coverage`), `:219-228` (`identified_total`) | La couverture agrégée est dite sommée sur « les projets en cours » quand WF-PTF-0090 dit « en cours et terminés » ; `identified_total` nomme autrement `ProvisionTotals.identified` | WF-PTF-0090, WF-RIS-0050 |

### Constats

#### H-01 — Le coût des risques survenus de la couverture : réestimé au lieu du coût à la survenance
- **gravité** : bloquant (contredit frontalement la spec, et le schéma est réemployé trois fois).
- **emplacement** : `docs/api/components/schemas/risks.yaml:489-507` (`RiskCoverageTotals`, description et `occurred_cost`) ; `docs/api/paths/risks.yaml:431-435` (`getProjectRiskCoverage`) ; réemploi par `indicators.yaml:207-209` (`RemainingIndicators.coverage`) et `portfolio.yaml:247-253` (`PortfolioRisks.coverage`) ; fixture `fixtures/api/risk_coverage.json` (résumé).
- **exigence** : WF-RIS-0050 — « la réserve de référence, face à la somme des provisions des risques identifiés dans la révision courante et du **coût à la survenance** des risques survenus (WF-RIS-0010) » ; Vérif : « La terminaison des tâches issues d'un risque survenu ne change ni le coût des survenus ni l'écart de couverture ». Glossaire (l. 4780) : « Coût à la survenance : … le total de son devis propre au moment où il a été déclaré survenu. **Il ne change plus, quelles que soient les réestimations et la terminaison des tâches fusionnées** ; c'est lui que la couverture des risques compare à la réserve. » §3.2.6 (l. 872) : « Ce qui est figé, ce n'est pas le devis propre, mais la réserve … et, pour un risque survenu, son coût à la survenance. »
- **ce que dit le contrat** : `RiskCoverageTotals` : « le **montant réestimé des lignes issues des risques survenus** » ; `getProjectRiskCoverage` : « au **coût réestimé** des risques survenus » ; `risk_coverage.json` : « aux 200,00 **réestimés** des lignes fusionnées du risque survenu ».
- **Constat.** Les deux grandeurs divergent dès qu'une ligne fusionnée est réestimée, redatée (WF-RIS-0060 : « le montant que ces grandeurs et ses dates donnent ») ou terminée : la spec veut un écart de couverture **stable**, le contrat en fait une grandeur vivante. Un serveur qui suit le contrat échouera la Vérif de WF-RIS-0050 ; un front qui affiche « coût à la survenance » mentira. La valeur de l'exemple (200,00) est la même dans les deux lectures tant que rien n'a bougé, ce qui cache le désaccord. À corriger avant le gel : c'est une définition de champ, pas une description.
- **Proposition.** Dans `RiskCoverageTotals` : `occurred_cost` → « la somme des coûts à la survenance des risques survenus (`Risk.occurrence_cost`, WF-RIS-0010) : le total de leur devis propre au moment de la survenance, que ni les réestimations ni la terminaison des tâches fusionnées ne changent (WF-RIS-0050) » ; même phrase dans `getProjectRiskCoverage` et le résumé de `risk_coverage.json` (« 200,00 de coût à la survenance »). Le nom `occurred_cost` peut rester (compatible), ou devenir `occurrence_cost` pour s'aligner sur H-02.
- **DECISIONS.md** : « Révision de la spécification du 2026-10-04 » (l. 1144–1156) : « la couverture des risques — la réserve face aux provisions des risques identifiés et au **coût réestimé des lignes issues des risques survenus** » (décision de l'auteur du 2026-10-06). Cette décision précède la passe de cohérence du 2026-10-09 (commit 7dc06e9d), qui introduit le terme « coût à la survenance » dans WF-RIS-0010, WF-RIS-0020, WF-RIS-0050, §4.4.1 et le glossaire : la décision contredit désormais la spec.

#### H-02 — Le risque ne porte pas son coût à la survenance
- **gravité** : majeur (attribut exigé par la spec, absent du contrat ; ajout compatible maintenant, rupture après le gel si le front doit le lire).
- **emplacement** : `docs/api/components/schemas/risks.yaml:10-140` (`Risk`, `properties`).
- **exigence** : WF-RIS-0010 — « Un risque survenu conserve son coût à la survenance : le total de son devis propre au moment où il est déclaré survenu (WF-RIS-0060) » ; §4.4.1 (l. 3861) — le révisionné porte « l'évaluation des risques — réexamens, état, **coût à la survenance** (WF-RIS-0020) » ; Vérif de WF-RIS-0020 — après abandon « le troisième est identifié, avec sa provision et **sans coût à la survenance** ».
- **ce que dit le contrat** : `Risk` porte `severity` (« total de la structure propre », vivant), `provision_amount`, `state`… et rien pour le coût figé. `risk_occurred_detail.json` ne rend que `severity: "200.00"`, qui suivra les réestimations du devis fusionné.
- **Constat.** Sans cet attribut, ni la fiche du risque survenu, ni la couverture (H-01), ni la Vérif de l'abandon ne peuvent se servir du contrat ; le front n'a que `severity`, qui n'est pas la bonne grandeur. L'historique (`RiskReview.severity` de la revue à la survenance) ne le remplace pas : la spec en fait un attribut du risque, et un `GET` du risque doit le rendre.
- **Proposition.**
  ```yaml
  occurrence_cost:
    anyOf: [{ $ref: ../common.yaml#/Money }, { type: 'null' }]
    description: >-
      Le coût à la survenance d'un risque survenu : le total de son devis propre au moment où
      il a été déclaré survenu, que ni les réestimations ni la terminaison des tâches fusionnées
      ne changent, et que la couverture compare à la réserve (WF-RIS-0010, WF-RIS-0050,
      WF-RIS-0060). Nul pour un risque identifié ou écarté.
  ```
  ajouté à `required` ; `risk_occurred_detail.json` et `risks.json` (752) à `"200.00"`, les autres à `null` ; `RiskCoverageTotals.occurred_cost` le cite (H-01). Le compte rendu préalable d'US-0680 peut en annoncer la valeur, mais l'attribut du risque n'est pas dans son périmètre tel que l'EPIC le décrit.
- **DECISIONS.md** : aucune décision (aucune occurrence de « coût à la survenance », `occurrence_cost` ni `cost_at_occurrence`).

#### H-03 — `provision_amount` d'un risque survenu ou écarté : courante ou de référence ?
- **gravité** : majeur (un implémenteur se tromperait ; le tri `provision_amount` et la cohérence lignes/totaux en dépendent).
- **emplacement** : `docs/api/components/schemas/risks.yaml:46-51` (`Risk.provision_amount`) ; `docs/api/components/parameters.yaml:281-282` (`RiskRevision`) ; `docs/api/components/schemas/risks.yaml:473-487` (`ProvisionTotals`) ; générateur `tools/src/wftools/mockhistory.py:312, 400` (`"provision_amount": money(provision(risk))`) contre `:437` (`provision(risk) if state == IDENTIFIED else reference_provision(risk)`).
- **exigence** : WF-RIS-0040 — « pour chaque risque … le montant de sa provision » et « les risques survenus, et les risques écartés, chacun pour la provision qu'ils portaient dans la révision de référence » ; glossaire « Provision » (l. 4837) : « un risque survenu ou écarté n'en porte plus ».
- **ce que dit le contrat** : `Risk.provision_amount` : « Calculée, gravité pondérée par la probabilité ; celle que portait la révision de référence compte à la réserve pour risques » — rien sur ce qu'elle vaut hors état identifié ; `RiskRevision` : « La provision d'un risque survenu est celle qu'il avait dans la révision de référence (WF-RIS-0050) » ; le générateur rend gravité × probabilité quel que soit l'état (752 : 200 × 0,3 = 60 = provision de référence ; 753 : 12 000 000 × 0,05 = 600 000 = provision de référence : coïncidences qui rendent les fixtures muettes).
- **Constat.** Pour un risque écarté dont la probabilité ou la gravité a changé depuis la référence, ou identifié après elle (provision de référence nulle), la ligne du registre et le total `dismissed` ne diront pas la même chose ; le tri par provision (WF-RIS-0040) classera des grandeurs hétérogènes. Le paramètre et le schéma se contredisent déjà en lecture.
- **Proposition.** Trancher dans `Risk.provision_amount` : « Pour un risque identifié, sa provision courante, gravité pondérée par la probabilité ; pour un risque survenu ou écarté, qui ne porte plus de ligne, la provision qu'il portait dans la révision de référence, `0.00` s'il n'y était pas identifié (WF-RIS-0040, WF-RIS-0050) : la ligne du registre somme aux totaux. » — et aligner `mockhistory.risk_item` sur `reference_provision`. Variante si l'on veut garder la valeur « ce qu'il pèserait » : ajouter `reference_provision_amount` (nullable) et dire que les totaux `occurred`/`dismissed` somment celui-là.
- **DECISIONS.md** : « Le total général des provisions est rendu, et la réserve en regard » (l. 590–595) ne parle que des totaux ; rien sur la valeur par ligne.

#### H-04 — `updateRisk` modifie la probabilité sans dire si c'est un réexamen
- **gravité** : majeur (question de modèle à trancher avant le gel : retirer un champ après coup est incompatible).
- **emplacement** : `docs/api/components/schemas/risks.yaml:264-275` (`RiskUpdate`, `allOf: RiskWrite` qui exige `label` et `probability`, l. 207 et 224–226) ; `docs/api/paths/risks.yaml:173-185` (description d'`updateRisk`), `:222-229` (422 `/probability`).
- **exigence** : WF-RIS-0010 — « Un réexamen est l'acte par lequel un utilisateur confirme ou modifie la probabilité et l'état d'un risque ; il est daté du jour où il est fait » ; WF-RIS-0040 — l'historique « montre l'évolution de sa probabilité et de sa gravité » ; WF-RIS-0020 — « La probabilité et l'état de chaque risque sont réexaminés à chaque revue périodique ».
- **ce que dit le contrat** : `updateRisk` accepte `probability` (exigée par `RiskWrite`), la borne en est dite (« `/probability` hors de 0 à 1 … comme à la déclaration (`RiskUpdate.probability`) »), mais ni la description ni `RiskUpdate` ne disent qu'une probabilité changée s'inscrit à l'historique ni que `last_review_on` avance ; `reviewRisk` est seul à produire « un réexamen daté ».
- **Constat.** Deux chemins écrivent la même grandeur ; si `updateRisk` l'écrit sans réexamen, l'historique de WF-RIS-0040 ment (une probabilité peut passer de 25 à 40 % sans trace datée), et la revue périodique ne verra pas le risque comme réexaminé. Si au contraire il en produit un, le contrat doit le dire et l'exemple le montrer.
- **Proposition.** Au choix de l'auteur : (a) retirer `probability` de la modification — `RiskUpdate` défini en propre (`label`, `description`, `mitigation_notes`, `provision_*`, `lock_version`), la probabilité ne se changeant que par `reviewRisk` ; ou (b) écrire dans `updateRisk` et `RiskUpdate` : « une probabilité différente de celle du risque produit un réexamen daté du jour, à l'état inchangé (`last_review_on`, `listRiskReviews`) ; égale, rien ne s'ajoute à l'historique », avec un exemple `risk_updated_probability` le montrant.
- **DECISIONS.md** : « La modification dit la même borne de la probabilité » (l. 7124–7133, US-0520/L2b, #1371) ne tranche que la borne ; « La saisie des risques est une saisie de la révision en cours » (l. 1431–1456) range `updateRisk` dans la révision en cours sans parler de l'historique.

#### H-05 — La tâche porteuse d'une provision supprimée par saisie : report et refus non déclarés
- **gravité** : majeur (un refus que la spec décrit et que l'opération ne déclare pas ; comportement de report non décrit). Hors `paths/risks.yaml` — à recouper avec la famille des nœuds —, mais c'est une règle de WF-RIS-0010.
- **emplacement** : `docs/api/paths/revisions.yaml:912-970` (`deleteNode` : description l. 915–927, `'409': Conflict` générique l. 954, 422 l. 964–969) ; `docs/api/components/schemas/revisions.yaml` (`NodesWritten`, aucune mention d'une ligne de provision reportée).
- **exigence** : WF-RIS-0010 — « Lorsque la tâche qui la porte est supprimée — **par saisie (WF-PLA-0070)**, par l'import d'un planning … ou par la fusion d'un différentiel … —, la ligne de provision passe sur la tâche parente de celle-ci ou, pour une tâche de premier niveau, sur la première tâche de premier niveau restante, et **la confirmation** ou le compte rendu le signale ; **la suppression de la dernière tâche d'une structure principale qui porte une ligne de provision est refusée en nommant le risque**. » Vérif : « La suppression de la tâche qui porte une provision de 40 laisse le devis inchangé, la provision étant passée sur la tâche parente. »
- **ce que dit le contrat** : `deleteNode` : « La suppression d'une tâche emporte ses lignes et ses liaisons … celle d'une récapitulative emporte aussi ses subordonnées, leurs lignes » — ce qui, lu à la lettre, emporte la ligne de provision ; `409` : `Conflict` générique sans condition ; rien ne nomme le risque. L'import et la fusion, eux, sont couverts (`StructureMergeReport.differences`, l. 444–446 ; #789).
- **Constat.** Le serveur ne sait pas s'il doit refuser, reporter ou supprimer la ligne ; le front ne sait pas où la retrouver après la confirmation (`NodesWritten.nodes` ?) ni quel refus afficher. Le total du devis doit rester inchangé (Vérif), ce qu'une suppression de la ligne violerait.
- **Proposition.** Dans `deleteNode` : « Une ligne de provision portée par la tâche supprimée, ou par une de ses subordonnées, n'est pas emportée : elle passe sur la tâche parente ou, pour une tâche de premier niveau, sur la première tâche de premier niveau restante, et `nodes` la rend écrite sous sa nouvelle tâche, le total du devis inchangé (WF-RIS-0010). La suppression qui laisserait la structure principale sans tâche alors qu'elle porte une ligne de provision est refusée par 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `<condition nouvelle, p. ex. provision_task_remaining>`, `params.risks[]` nommant les risques par `risk_id` et `label` » ; condition à ajouter à `CommandCondition` et au catalogue de `Problem.params` ; exemple `node_delete_last_provision_task_refused`. Le risque, lui, voit `provision_task` changer (à dire dans `Risk.provision_task`).
- **DECISIONS.md** : « La ligne de provision déplacée, au compte rendu » (l. 8097–8110, #789) ne traite que l'import et la fusion ; aucune décision sur `deleteNode`.

#### H-06 — « Budget de référence » pour « assiette » sur l'axe des gravités
- **gravité** : mineur (description ; `severity_ratio` et `RiskMatrixCell` disent déjà juste).
- **emplacement** : `docs/api/components/schemas/risks.yaml:362-364` (`RiskMatrixLevel` : « du budget de référence sur l'axe des gravités »), `:451-452` (`RiskMatrix.severity_levels` : « en pourcentage du budget de référence »), `docs/api/paths/risks.yaml:460-461` (`getProjectRiskMatrix` : « celles de gravité en pourcentage du budget de référence »), `docs/api/components/schemas/reference.yaml:822-823` (`RiskMatrixSettings`).
- **exigence** : WF-REF-0160 — « trois bornes de gravité, exprimées en pourcentage de **l'assiette du projet** — son budget de référence ou, tant qu'il n'en a pas, le total hors provisions du devis de sa révision courante » ; Vérif : « Sur un projet en chiffrage, un risque est classé d'après le total hors provisions de son devis courant ».
- **ce que dit le contrat** : quatre descriptions disent « budget de référence » seul ; `RiskMatrixPoint.severity_ratio` (l. 400–402) et `RiskMatrixCell` (l. 347–350) disent l'assiette.
- **Constat.** Un implémenteur qui lit les niveaux ou le paramètre du référentiel sans lire le point classera tout risque d'un projet en chiffrage au niveau 1 (pas de budget de référence) : la Vérif de WF-REF-0160 échouerait. Les fixtures (`risk_matrix_no_basis`) ne couvrent que l'assiette nulle.
- **Proposition.** Remplacer par « en pourcentage de l'assiette du projet — son budget de référence ou, avant lui, le total hors provisions du devis de sa révision courante (WF-REF-0160) » aux quatre endroits.
- **DECISIONS.md** : « La part de gravité d'un risque sur une assiette nulle » (l. 7516–7525, #1240) emploie « assiette » et décrit la règle ; aucune décision ne retient « budget de référence » seul.

#### H-07 — Champs toujours rendus mais non exigés dans `Risk`
- **gravité** : mineur (ajout à `required` compatible pour tout client ; types générés plus justes).
- **emplacement** : `docs/api/components/schemas/risks.yaml:12-29` (`Risk.required`) ; propriétés l. 38–41 (`description`, `mitigation_notes`), 58–60 (`provision_node_id`), 114 (`matrix_cell`), 115–116 (`last_review_on`).
- **exigence** : WF-RIS-0040 — la grille présente « la date de son dernier réexamen » et « Chaque ligne porte une couleur donnée par une matrice » ; `listRisks` (l. 7–8) promet « la case de matrice ».
- **ce que dit le contrat** : `provision_task` et `provision_subproject_id`, nullables, sont exigés ; `provision_node_id`, `matrix_cell`, `last_review_on`, `description`, `mitigation_notes` ne le sont pas, alors que les quatorze fixtures `Risk` les rendent tous (nuls le cas échéant).
- **Constat.** Le client généré (`schema.d.ts`) les typera optionnels : le front gardera des `?.` sur des champs que le serveur rend toujours, et un serveur pourrait les omettre sans faute. La décision #786 dit `provision_task` « exigé … nulle quand le risque n'est pas identifié …, **comme `provision_node_id`** » : le schéma ne suit pas sur ce dernier.
- **Proposition.** Ajouter à `required` : `description`, `mitigation_notes`, `provision_node_id`, `matrix_cell`, `last_review_on` (les trois premiers et le dernier nullables).
- **DECISIONS.md** : « La déclaration d'un risque désigne la tâche de sa provision » (l. 7064–7082, #786) pour `provision_task`/`provision_node_id` ; rien sur les autres.

#### H-08 — Le 409 de `declareRiskOccurrence` ne nomme rien et n'a pas d'exemple
- **gravité** : mineur (qualité ; les conditions existent dans `CommandCondition` et `RiskCommand.declare_occurrence` les décrit).
- **emplacement** : `docs/api/paths/risks.yaml:422` (`'409': { $ref: ../components/responses.yaml#/Conflict }`).
- **exigence** : WF-RIS-0020 — « Toute transition depuis l'état survenu est refusée » ; WF-RIS-0060 — « Lorsque le projet ne comporte pas de révision en cours, elle en crée une au préalable » ; `RiskCommand` (schemas l. 173–177) : « indisponible pour un risque qui n'est pas identifié, `risk_identified` manquante, et … `may_create_revision` manquante ».
- **ce que dit le contrat** : réponse partagée `Conflict` (« `STATE_FORBIDS_OPERATION` … ou `ALREADY_EXISTS` »), sans condition ni exemple, alors que `createRisk`, `updateRisk`, `reviewRisk`, `deleteRisk` nomment les leurs et ont chacun un exemple (`risk_without_task`, `risk_provision_frozen`, `risk_review_occurred`, `risk_delete_cited`).
- **Constat.** Le front d'US-0680 devra afficher ce refus (« elle est refusée pour un risque qui n'est pas identifié ») sans exemple du contrat à lire ; l'ordre des conditions n'est dit nulle part pour cette opération. Hors périmètre US-0680 tel que listé (compte rendu, compteurs, 412).
- **Proposition.** Description : « `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_not_terminal`, `no_background_task_running`, `may_create_revision` (sans révision en cours, pour qui n'a pas `revisions.write`), puis `risk_identified` pour un risque écarté ou déjà survenu, dans cet ordre, comme `ProjectCommand.declare_risk_occurrence` et `RiskCommand.declare_occurrence` les listent. Rien n'est écrit. » ; exemple `risk_occurrence_not_identified` (753, écarté, `risk_identified`).
- **DECISIONS.md** : l. 7160–7166 ne cite pour `declareRiskOccurrence` que la mise en file, la structure obtenue et le risque survenu ; aucune décision sur son 409.

#### H-09 — Descriptions : `states` muet, conditions d'état absentes des 409 de trois saisies
- **gravité** : mineur.
- **emplacement** : `docs/api/paths/risks.yaml:14-19` (`states`, sans `description`) ; `:206-215` (409 d'`updateRisk`), `:265-270` (409 de `deleteRisk`), `:349-362` (409 de `reviewRisk`).
- **exigence** : WF-RIS-0040 — « se filtre par état » ; WF-IHM-0090 ; `RevisionCommand.edit_risks` (`revisions.yaml:103-136`) qui porte `project_not_terminal`, `no_background_task_running`, `may_create_revision` pour les quatre saisies.
- **ce que dit le contrat** : `createRisk` (l. 97–113) : « Le projet est terminal, `project_not_terminal` …, ou un traitement de fond court sur la révision en cours, `no_background_task_running` : les conditions d'état de la saisie des risques » ; les trois autres 409 ne citent que les conditions propres au risque.
- **Constat.** Un implémenteur du back lirait que `updateRisk` sur un projet terminal ou pendant une survenance n'a pas de 409 à rendre ; `states` n'explique pas qu'il s'agit d'une liste séparée par des virgules d'états du risque.
- **Proposition.** `states` : « Restreint aux risques dans l'un de ces états (WF-RIS-0040). » ; dans les trois 409 : « … ou les conditions d'état de la saisie des risques, `project_not_terminal` et `no_background_task_running`, puis `may_create_revision` sans révision en cours, comme à la déclaration (`createRisk`), jugées avant celles du risque. »
- **DECISIONS.md** : « Le projet terminal n'a pas de révision en cours » (l. 7987–7990, #795) fixe l'ordre (`project_not_terminal` avant `may_create_revision`) pour `edit_risks` ; aucune décision n'exempte les trois opérations.

#### H-10 — Cohérence avec le portefeuille : périmètre de la couverture agrégée et nom du total identifié
- **gravité** : mineur (famille portefeuille ; signalé pour la cohérence des concepts de risques).
- **emplacement** : `docs/api/components/schemas/portfolio.yaml:247-253` (`PortfolioRisks.coverage`) ; `:219-228` (`identified_total`) ; `docs/api/paths/portfolio.yaml:199-203`.
- **exigence** : WF-PTF-0090 — « la réserve et la couverture ne portent que sur les projets **en cours et terminés** du périmètre, un projet en chiffrage n'ayant pas de référence ».
- **ce que dit le contrat** : « la somme des réserves de référence des projets **en cours** du périmètre » (`PortfolioRisks`, l. 223–224 et 250) ; le total des provisions identifiées s'appelle `identified_total` ici, `ProvisionTotals.identified` dans la famille des risques (et `PortfolioRisks.matrix.totals.identified` dans la même réponse).
- **Constat.** Un projet terminé qui a consommé sa réserve sort de la couverture agrégée au moment où il devrait y peser ; deux noms pour le même concept dans une même réponse.
- **Proposition.** « des projets en cours et terminés du périmètre (WF-PTF-0090) » ; garder `identified_total` (renommer serait une rupture gratuite) mais le décrire comme « la somme des provisions des risques identifiés, `ProvisionTotals.identified` de chaque projet, un projet en chiffrage inclus sans pondération ».
- **DECISIONS.md** : « La couverture agrégée est la somme de celles des projets en cours » (l. 2242–2246) : décision écrite « en cours » ; à confronter à la lettre de WF-PTF-0090 (« en cours et terminés »), que le texte de la décision ne cite pas.

### Ce qui est juste

- Les attributs de WF-RIS-0010 sont portés et bien typés : `label` (`\S`, 300), `description`, `mitigation_notes`, `probability` (`Percent`, rapport 0–1 : décidé, DECISIONS l. 4135–4137), `severity`/`provision_amount` calculés et nommés dans `computed_fields` (`own_estimate`, `severity_and_probability`), `state` (`identified`/`occurred`/`dismissed` complet), `structure_id` (WF-REV-0100), catégorie/sous-projet/tâche de la provision avec leurs libellés résolus (EP-14/L42p, #786, #1227). Les noms suivent le §4.4.1 (`risk`, `risk_review` → `RiskReview`, `estimate_line`).
- Le cycle des états : `RiskReviewWrite.state` ∈ {identified, dismissed}, la survenance par `/occurrence` seule et définitive, `risk_not_occurred`/`risk_identified`/`risk_not_cited`/`at_least_one_task`/`active_provision_category`/`restored_subproject_exists`/`may_create_revision` tous dans `CommandCondition` ; tous les codes de champ cités (`UNKNOWN_COST_CATEGORY`, `INACTIVE_REFERENCE_OBJECT`, `PROVISION_CATEGORY_REQUIRED`, `UNKNOWN_SUBPROJECT`, `UNKNOWN_TASK`, `VALUE_OUT_OF_RANGE`, `VALUE_TOO_LONG`) sont dans `ErrorCode` ; la préséance 409 avant 422 et l'ordre des conditions sont décidés (#747, #732, #787, #795) ; chaque refus déclaré de `createRisk`, `updateRisk`, `reviewRisk`, `deleteRisk` a un exemple cohérent (code, statut, `params`/`fields`).
- Les fixtures sont arithmétiquement justes : cases de matrice recalculées sur `reference_settings.risk_matrix` (bornes 0,1/0,3/0,6 et 1 %/5 %/10 %, zones au rang 4(p−1)+(g−1), « égale à une borne relève du niveau supérieur » pour 752 à 30 %) ; totaux 500 000 + 60 + 600 000 = 1 100 060 ; réserve 850 060 = 250 000 + 60 + 600 000 (provisions au marquage du 1er février, `risk_reviews` à l'appui) ; couverture 850 060 − 500 000 − 200 = 349 860 ; `lock_version` et `audit.updated_at` progressent d'une version à chaque saisie ; `risk_created` à la version 1 comme tous les `*_created`. `BackgroundTaskRef.kind` connaît `risk_occurrence` ; 401/503 partout, 400/422 sur toute opération à corps, 412 sur les modifications à `lock_version` ; `INVENTORY.md` cite les bonnes exigences.
- Le total général et la réserve « sur les risques retenus » (`risks_empty` à zéro sous filtre) sont une décision de l'auteur (DECISIONS l. 590–595) ; `moveNodes` refusant une ligne de provision (`PROVISION_LINE_MOVED_BY_RISK`) et le report de la provision à l'import et à la fusion (#789) couvrent les autres alinéas de WF-RIS-0010.

### Doutes

- `RiskMatrix.totals` et `RiskMatrix.points` « sur les risques retenus » : une fois `cells` restreint aux risques identifiés (US-0700/L1), les totaux `occurred`/`dismissed` de la matrice et les points des survenus/écartés restent-ils ? `risk_matrix_no_basis.json` (absent de la liste d'US-0700) compte aujourd'hui les trois risques, survenu et écarté compris, dans `cells` et `points` : à régénérer ou à préciser avec ce lot.
- `getProjectRiskCoverage` sur un projet sans révision de référence : `reserve` à `0.00` ou couverture non calculable ? La spec ne le dit pas ; `RiskCoverageTotals` exige quatre `Money`.
- La survenance ajoute-t-elle un réexamen à l'historique (état `occurred`) ? `last_review_on` de 752 vaut la date de survenance et `RiskReview.state` admet `occurred`, mais ni `listRiskReviews` ni `declareRiskOccurrence` ne le disent ; aucun exemple d'historique d'un risque survenu.
- WF-RIS-0020 : « La revue périodique présente les risques dont la probabilité n'a pas été réexaminée » — `listRisks` n'a pas de filtre sur `last_review_on` (`last_review_on_from`/`_to`, convention des périodes). Aux volumes du §4.6.2 (30 risques par projet) le front peut filtrer lui-même ; si l'écran de revue doit l'obtenir du serveur, le filtre manquera après le gel. À trancher par le lot des revues.
- `RiskOccurrence` dit « leur montant du devis propre en réestimé » ; WF-RIS-0060 : « le montant que ces grandeurs et ses dates donnent — celui du devis propre tant que ses dates n'ont pas changé ». Nuance de description ; non compté comme constat, la fusion étant celle de `nodes_risk_occurred`.

## Annexe I — Coûts réels et échanges par fichier


Lu : `docs/api/README.md` (Conventions) ; `docs/api/paths/costs.yaml` (163 l.), `docs/api/paths/exchanges.yaml` (496 l.), `docs/api/components/schemas/costs.yaml` (133 l.), `docs/api/components/schemas/exchanges.yaml` (565 l.) en entier ; les parties citées de `common.yaml` (`ErrorCode`, `ProblemParams`, `BackgroundTaskRef`), `parameters.yaml`, `responses.yaml`, `reference.yaml` (`ActualCostMapping*`), `projects.yaml` (`ProjectCommand`), `revisions.yaml` (`RevisionCommand`), `system.yaml` (`getBackgroundTaskResult`), `audit.yaml` ; la spécification §3.1.2 (322–377), §3.1.4 (417–555), §3.1.5 WF-INTF-0180, §3.4.4.1.3, §3.4.5.3.4, §3.4.5.7 (2807–2875), §4.3.4 WF-ARC-0090/0100, §4.4.1 (3849–3920), §4.4.3, §4.4.4, §4.6.2, annexe B (4870–4918), plus WF-PLA-0020, WF-PLA-0130, WF-RAE-0040, WF-CYC-0100, WF-SEC-0030 ; `DECISIONS.md` par grep (186 lignes touchant la famille ; sections EP-02/L17, L18, L25, L30, L35, EP-03/US-0350 décision 10, EP-14/L42s, US-0500, US-0620, US-0630 lues) ; `INVENTORY.md` (l. 230–249) ; l'EPIC (« Constats reçus », « Les modifications du contrat ») ; les générateurs `mockcosts.py`, `mockwitnesscosts.py`, `mockexchanges.py` ; **48 fixtures ouvertes** (toutes celles référencées par les deux fichiers de chemins, plus `task_import_*`, `task_export_*`, `task_result_disposition`, `project*` pour `exclude_cost_lines`). Les 28 lignes d'`actual_costs.json` ont été resommées : les trois totaux sont exacts.

Les phrases de la spécification citées ci-dessous comme nouvelles sont entrées par les passes de cohérence des 9 et 10 octobre 2026 (commits 7dc06e9d et b18a8883 ; la révision 1.0.0 du 2026-10-24 n'a changé que le numéro de révision) ; les décisions qui les contredisent lui sont antérieures.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| I-01 | majeur | `schemas/costs.yaml:119-133` (`CostImport`), `paths/costs.yaml:136-138` (`listCostImports`) | Le journal compte `created/updated/ignored` ; la spec veut créées, mises à jour, **inchangées et rejetées** | WF-CRE-0050, WF-INTF-0140 |
| I-02 | majeur | `common.yaml:420-620` (`ErrorCode`), `schemas/exchanges.yaml:386-389` (`ImportRejection`) | Aucun code pour une ligne de coût rejetée pour son élément d'OTP (mal formé, autre projet) ; le journal en compte 12 345 | WF-CRE-0020 |
| I-03 | majeur | `schemas/exchanges.yaml:439-441` (`ImportDifference.target`) | L'écart de date de début de planning de la structure, que l'import MS Project présente, n'a pas de cible | WF-INTF-0040, WF-PLA-0020 |
| I-04 | majeur | `schemas/exchanges.yaml:352-357` (`ImportSignal.code`) | `code` est `const: NON_WORKING_DAY` ; la spec demande déjà un second signalement : la récapitulative en mode manuel | WF-INTF-0040 |
| I-05 | majeur | `schemas/exchanges.yaml:213-223, 263-272, 429-438` (`ImportReport.ignored`, `ImportIgnoredKind`, `change: kept`) | Les lignes de provision ignorées ou conservées par un import Excel ne se signalent nulle part ; `ignored` est dit vide pour Excel | WF-INTF-0100, WF-INTF-0120 |
| I-06 | majeur | `paths/costs.yaml:115-129` (`setActualCostTrackedScope`) | Aucun 409 alors que `exclude_cost_lines` nomme `project_not_terminal` et `project_in_progress` | WF-CYC-0100, WF-CRE-0030 |
| I-07 | majeur | `paths/exchanges.yaml:455-456` (`requestExport`), `schemas/exchanges.yaml:544-545` (`ExportRequest`) | « n'est pas stocké (WF-DAT-0120) » : l'exigence citée dit l'inverse (stocké 24 h ou jusqu'au premier téléchargement complet) | WF-DAT-0120 |
| I-08 | majeur | `schemas/exchanges.yaml:140-160` (`Import`) | La lecture d'un import ne rend ni la structure visée, ni la révision, ni la période données à l'ouverture | WF-INTF-0090, WF-CRE-0050 |
| I-09 | majeur (à trancher) | `schemas/exchanges.yaml:302-308` (`ImportCompletedTask.completed_on`), `540-565` (`ExportRequest`) | Date de terminaison = jour d'application (WF-PLA-0130) contre « date de la revue que porte le fichier » (WF-INTF-0120/0130) ; l'export ne dit pas cette date | WF-INTF-0120, WF-INTF-0130, WF-PLA-0130 |
| I-10 | majeur | `paths/exchanges.yaml:235-237, 304-325` (`openImport`) | Le format est contrôlé « par l'analyse, confiée au worker » et pourtant refusé par un 422 synchrone de l'ouverture | WF-ARC-0100, WF-INTF-0070 |
| I-11 | majeur | `common.yaml:420-620` (`ErrorCode`), `fixtures/api/import_analysed.json` | Aucun code pour le libellé de tâche ambigu de l'annexe B ; `UNKNOWN_TASK`/`UNKNOWN_RESOURCE_ROLE` rejettent sans nommer ce que la ligne citait | annexe B, WF-INTF-0100 |
| I-12 | mineur | `fixtures/api/import_actual_costs_analysed.json`, `_column_ignored.json`, `_duplicate_line.json` ; `schemas/exchanges.yaml:183-184` | `format_version: "1"` pour une extraction ERP qui « n'en porte pas » ; `format_version` sans description | WF-INTF-0070 |
| I-13 | mineur | `schemas/exchanges.yaml:164-165, 253`, `schemas/costs.yaml:5-15, 68-73` | `requires_confirmation_reasons`, `format_version`, `passthrough`, `excluded_reason`, `ImportDifference.label` non exigés alors que « toujours rendus » | WF-INTF-0080 |
| I-14 | mineur | `schemas/exchanges.yaml:151-157` (`Import.status`, `expires_at`) | `status` sans description (quel état après un refus à l'application, une analyse échouée ?) ; `expires_at` exigé pendant `analysing` | WF-ARC-0100 |
| I-15 | mineur | `schemas/exchanges.yaml:132-138` (`ImportRequest`), `paths/exchanges.yaml:304-317` | `structure_id`, `period_from`, `period_to` sans description ; période inversée, structure ou dépôt inconnus : refus non décrits | WF-INTF-0090, WF-CRE-0050 |
| I-16 | mineur | `schemas/exchanges.yaml:548-554, 561-565` (`ExportRequest`) | `kind` est une énumération anonyme (pas d'`ExportKind` nommé) ; `structure_id` sans description | WF-INTF-0050/0110/0130 |
| I-17 | mineur | `paths/exchanges.yaml:485` (`requestExport`) | Un 409 déclaré sans cause possible ni exemple : un export « ne manque d'aucune condition » | WF-CYC-0110 |
| I-18 | mineur | `paths/exchanges.yaml:370-385` (`abandonImport`) | Rien ne dit ce que fait l'abandon d'un import appliqué, en cours d'application ou expiré | WF-ARC-0100 |
| I-19 | mineur | `paths/costs.yaml:19-27` (`listActualCosts`) | `from`, `to`, `in_tracked_scope` sans description : quelle colonne, quelle borne | WF-CRE-0040, WF-IHM-0130 |
| I-20 | mineur | `paths/exchanges.yaml:354-366, 441-442, 478-484` | Exemples manquants : premier import de coûts réels (`added`, `lines_outside_project`), `completed_tasks` non vide, 409 de l'application pour droits/état, 404 d'export | WF-INTF-0080, WF-CRE-0020 |

### Constats

#### I-01 — Le journal des imports ne compte ni les lignes inchangées ni les rejetées
- **majeur** ; `docs/api/components/schemas/costs.yaml:119` (`required: [cost_import_id, imported_at, actor, created_count, updated_count, ignored_count]`) et `:131-133`, `docs/api/paths/costs.yaml:136-138` (`listCostImports`) ; **WF-CRE-0050** : « journalisé avec sa date, son auteur, la période extraite et le nombre de lignes créées, mises à jour, inchangées et rejetées (WF-CRE-0020) » ; Vérif de **WF-INTF-0140** : « Le compte rendu (WF-INTF-0080) présente les lignes ajoutées, mises à jour, inchangées et rejetées avant confirmation » ; **le contrat** : « nombre de lignes créées, mises à jour et ignorées » ; `CostImport` porte `created_count`, `updated_count`, `ignored_count`.
- **Constat.** Deux des quatre compteurs exigés manquent : « inchangées » n'existe pas, et « rejetées » est confondu avec « ignorées » (le résumé de `cost_imports.json` le dit : « Le journal compte parmi les lignes ignorées celles qu'un import rejette »). Or une ligne inchangée (rejouée à l'identique) et une ligne rejetée (OTP d'un autre projet) sont deux choses que le contrôleur de gestion lit différemment : la première dit que l'extraction recouvre la précédente, la seconde qu'elle est mal filtrée. Côté compte rendu, `ImportReport` ne dit pas non plus « inchangées » (ni `change: unchanged`, ni compteur) : le front ne peut l'obtenir que par `read_count − rejected − added − updated`. Renommer ou ajouter un champ exigé d'un schéma de lecture est incompatible après le gel.
- **Proposition.**
  ```yaml
  CostImport:
    required: [cost_import_id, imported_at, actor, period_from, period_to, created_count, updated_count, unchanged_count, rejected_count]
    properties:
      unchanged_count: { type: integer, minimum: 0, description: Lignes lues déjà importées à l'identique (WF-CRE-0050). }
      rejected_count: { type: integer, minimum: 0, description: Lignes rejetées au compte rendu — OTP mal formé ou d'un autre projet, doublons (WF-CRE-0020, WF-INTF-0140). }
  ```
  (`ignored_count` retiré ; `period_from`/`period_to` exigés et nullables, comme la lecture les rend déjà.) Et sur `ImportReport`, un `unchanged_count` exigé, ou la mention explicite que l'inchangé se déduit de `read_count`.
- **DECISIONS.md** : section « Coûts, échanges, tâches, comptes (EP-02/L25) », l. 2072-2073 : « le journal la compte parmi les lignes ignorées, seul compte que WF-CRE-0050 lui donne » — vrai avant la passe de cohérence des 9 et 10 octobre 2026 (commits 7dc06e9d, b18a8883), qui nomme désormais les quatre comptes. La décision contredit la spécification en vigueur.

#### I-02 — Aucun code pour une ligne de coût rejetée sur son élément d'OTP
- **majeur** ; `docs/api/components/common.yaml:420-620` (`ErrorCode`, aucun code `*WBS*`, `*OTP*`, « autre projet ») ; `docs/api/components/schemas/exchanges.yaml:386-389` (`ImportRejection`, seul motif d'une extraction : `DUPLICATE_COST_LINE`) ; `:253-261` (`requires_confirmation_reasons: lines_outside_project`) ; **WF-CRE-0020** : « Une ligne dont l'élément d'OTP n'a pas cette forme est rejetée et signalée au compte rendu, comme une ligne d'un autre projet. Une ligne dont le code projet ne correspond pas au projet importé est rejetée et signalée au compte rendu » ; **le contrat** : `ImportRejection.code` est un `ErrorCode`, et `cost_imports.json` compte « 12 345 lignes d'autres projets rejetées et signalées ».
- **Constat.** Le compte rendu doit porter chaque ligne rejetée « avec son motif » (WF-INTF-0080), et le témoin lui-même suppose des milliers de ces rejets, mais le catalogue fermé des codes n'en a aucun : l'implémenteur devra en inventer un après le gel (modification du contrat). `lines_outside_project` est un motif global de confirmation, pas le motif d'une ligne ; il ne couvre pas l'OTP mal formé (« vide, ou sans rien avant la barre oblique », Vérif). Aucune fixture ne montre un tel rejet.
- **Proposition.** Deux codes dans `ErrorCode`, motifs d'`ImportRejection`, avec `params.wbs_element` (la valeur lue) : `WBS_ELEMENT_INVALID` (forme non reconnue) et `WBS_ELEMENT_OUTSIDE_PROJECT` (code projet différent, `params.project_code` le code lu). Un exemple de compte rendu d'un premier import (voir I-20).
- **DECISIONS.md** : EP-02/L25, l. 2072 (« Une ligne d'un autre projet est « rejetée et signalée au compte rendu » (WF-CRE-0020 révisée) ») constate la règle sans lui donner de code ; aucune décision sur le code.

#### I-03 — L'écart de date de début de planning n'a pas de place au compte rendu
- **majeur** ; `docs/api/components/schemas/exchanges.yaml:439-441` : `target: enum: [task, estimate_line, link, actual_cost_line]` ; **WF-INTF-0040** : « la date de début du projet du fichier devient la date de début de planning de la structure (WF-PLA-0020), et le compte rendu la présente lorsqu'elle diffère de celle en place » ; **WF-PLA-0020** : « Chaque structure de coûts porte une date de début de planning … L'import MS Project la lit dans la date de début du projet du fichier, et l'export l'y écrit ».
- **Constat.** `ImportDifference` ne peut viser qu'une tâche, une ligne, une liaison ou une ligne de coût ; la structure elle-même n'a pas de cible, et aucun champ de `NodeColumn`/`ImportDifferenceField` ne nomme la date de début de planning. Un écart que la spécification demande de présenter ne peut pas être transporté, et une valeur d'énumération ajoutée après le gel est une modification du contrat. (La phrase est entrée le 2026-10-09, commit 7dc06e9d.)
- **Proposition.** `target` gagne `cost_structure` ; `ImportDifferenceField` gagne `planning_start` ; l'écart : `{ change: updated, target: cost_structure, lineage_id: <lignée de la structure>, label: <libellé de la structure>, fields: [planning_start] }`. À faire d'accord avec la famille des révisions : `CostStructure` (revisions.yaml) ne porte aujourd'hui aucun champ de date de début de planning (voir Doutes).
- **DECISIONS.md** : aucune décision (grep « début de planning », `planning_start`).

#### I-04 — `ImportSignal.code` est figé sur un seul code alors que la spec en demande un second
- **majeur** ; `docs/api/components/schemas/exchanges.yaml:352-357` : « `code: allOf: [ErrorCode, { const: NON_WORKING_DAY }]` … `NON_WORKING_DAY` seul, tant qu'aucun autre signalement n'existe ; un signalement nouveau élargit cette liste, par une modification du contrat » ; **WF-INTF-0040** : « Une récapitulative en mode manuel dans le fichier est importée en mode automatique, et le compte rendu la signale avec l'écart de dates ».
- **Constat.** Le second signalement existe déjà dans la spécification : une récapitulative que le fichier date à la main et que Waterfall recalcule. Ce n'est ni un rejet (`rejected`), ni un écart avec l'existant (`differences`, la tâche peut être créée), ni un `date_mismatches` seul (qui ne dit pas pourquoi le mode a changé) ; c'est exactement un `ImportSignal` — « ce que l'import garde ou corrige, et signale ». Le `const` interdit de le porter sans rompre le contrat.
- **Proposition.** Lever le `const` en une énumération de deux codes, en réemployant le code existant du refus de la saisie : `code: { $ref: ErrorCode, enum: [NON_WORKING_DAY, SUMMARY_TASK_DERIVED] }`, `column: scheduling_mode`, `params.start`/`params.finish` les dates du fichier, l'écart de dates recalculé restant dans `date_mismatches`. Un exemple.
- **DECISIONS.md** : aucune (grep « mode manuel », « récapitulative » hors saisie) ; la phrase du schéma est le seul texte qui en parle.

#### I-05 — Les lignes de provision ignorées ou conservées par un import Excel ne se signalent pas
- **majeur** ; `docs/api/components/schemas/exchanges.yaml:221-222` (`ImportReport.ignored` : « Vide pour un devis ou un reste à engager, qui ne lisent que leurs colonnes »), `:263-272` (`ImportIgnoredKind`, sans nature pour une ligne), `:432-438` (`change: kept` : « une tâche démarrée ou terminée que le fichier ne porte plus, ou une ligne de devis d'une telle tâche ») ; **WF-INTF-0100** : « une ligne du fichier qui porte la lignée d'une ligne de provision est ignorée, une ligne sans identifiant dont la catégorie relève d'une nature de type provision pour risques est rejetée (WF-DEV-0020), et une ligne de provision absente du fichier est conservée ; le compte rendu signale les unes et les autres » ; **WF-INTF-0120** : « Les lignes de provision des risques ne sont ni mises à jour ni créées par l'import, selon la même règle que WF-INTF-0100 ».
- **Constat.** Des trois cas, seul le rejet a son code (`PROVISION_CATEGORY_RESERVED`). La ligne du fichier qui porte une lignée de provision (ignorée) et la ligne de provision absente du fichier (conservée) doivent être signalées, et le contrat n'offre ni nature d'`ignored` ni `kept` pour elles — il dit même le contraire pour `ignored`. La fixture `import_remaining_analysed.json` porte la provision « inchangée à 500 000 » dans le fichier et ne la signale pas. Une valeur d'énumération manque ; la description de `kept` exclut le cas.
- **Proposition.** `ImportIgnoredKind` gagne `provision_lines` (les lignes du fichier portant la lignée d'une provision, `labels` leurs libellés) ; `change: kept` s'étend à « une ligne de provision que le fichier ne porte plus, conservée » ; `ImportReport.ignored` ne dit plus « vide pour Excel ». Fixture `import_remaining_analysed` complétée d'un `ignored: [{ kind: provision_lines, count: 1, labels: ["Provision — risque de reprise du câblage"] }]`.
- **DECISIONS.md** : « La ligne de provision déplacée, au compte rendu » (#789, l. 8097-8115) ne traite que la provision dont la tâche porteuse est retirée ; rien sur la ligne ignorée ou conservée. La phrase de WF-INTF-0100 est entrée le 2026-10-09, commit 7dc06e9d.

#### I-06 — L'exclusion d'une ligne ne déclare pas le 409 que sa commande annonce
- **majeur** ; `docs/api/paths/costs.yaml:115-129` (`setActualCostTrackedScope` : 200, 400, 401, 403, 404, 422, 503) ; **WF-CYC-0100** : « Dans un état terminal, le projet et toutes ses données (plannings, devis, restes à engager, coûts réels) sont en lecture seule » ; **le contrat** : `fixtures/api/project_completed.json` liste `exclude_cost_lines` indisponible, `missing_conditions: [project_not_terminal]`, et `project_pricing.json` `[project_in_progress]`.
- **Constat.** La commande dit d'avance deux conditions ; l'opération qui les juge ne déclare pas le refus qui les nomme. Un implémenteur du service rendra un 409 que le contrat n'a pas, le client généré ne le typera pas (« défaut n° 2 du guide », cité dans DECISIONS pour `setWorkBreakdown`).
- **Proposition.**
  ```yaml
  '409':
    description: >-
      `STATE_FORBIDS_OPERATION`, `params.missing_condition` la première condition manquante dans
      l'ordre de la commande `exclude_cost_lines` : `project_not_terminal` sur un projet terminal
      (WF-CYC-0100), `project_in_progress` avant En cours.
    content: { application/problem+json: { schema: Problem, examples: { project_terminal: … } } }
  ```
- **DECISIONS.md** : aucune (grep `exclude_cost_lines` : une seule mention, l. 2537, sur l'écran).

#### I-07 — L'export est dit « non stocké » en citant l'exigence qui le fait stocker
- **majeur** ; `docs/api/paths/exchanges.yaml:455-456` : « Le fichier est engendré à la demande et n'est pas stocké (WF-DAT-0120) » ; `docs/api/components/schemas/exchanges.yaml:544-545` : « transmis sans être stocké (WF-DAT-0120) » ; même phrase dans `paths/system.yaml:219-221` (`getBackgroundTaskResult`, autre famille) et dans le résumé de `task_export_succeeded.json` ; **WF-DAT-0120** : « Le stockage objet porte trois compartiments : les fichiers en cours d'import, les fichiers exportés en attente de téléchargement, et les sauvegardes. … Un fichier exporté est supprimé à l'issue de son premier téléchargement complet, ou au terme de vingt-quatre heures s'il n'a pas été téléchargé ; un téléchargement interrompu le laisse en place » ; §4.6.2 : « Conservation des fichiers exportés : vingt-quatre heures au plus, ou jusqu'au téléchargement ».
- **Constat.** La citation est fautive et contredit frontalement le texte cité : l'export est produit par le worker (WF-ARC-0090), déposé sur le stockage objet, et téléchargé ensuite par `result_url` — il est donc stocké, et sa règle de disparition est une exigence F0 que le service doit implémenter (suppression au premier téléchargement complet). Un implémenteur qui suit la description engendrerait le fichier à la requête de téléchargement, et le second téléchargement ne serait jamais refusé.
- **Proposition.** Réécrire les trois descriptions : « Le fichier est engendré par le worker et écrit sur le stockage objet ; il est supprimé à l'issue de son premier téléchargement complet, ou au terme de vingt-quatre heures ; un téléchargement interrompu le laisse en place (WF-DAT-0120) ». Et, pour la famille des tâches, dire ce que `getBackgroundTaskResult` répond après la suppression (404 ou 410) et que `result_url` reste lisible.
- **DECISIONS.md** : aucune (grep « stocké », « téléchargement » dans les entrées d'export).

#### I-08 — La lecture d'un import ne rend pas ce que son ouverture a reçu
- **majeur** ; `docs/api/components/schemas/exchanges.yaml:140-160` (`Import` : `import_id, kind, filename, status, created_at, expires_at, report, task`) contre `:119-138` (`ImportRequest` : `kind, upload_id, structure_id, period_from, period_to`) ; **WF-INTF-0090** : « Un import porte sur une seule structure de coûts de cette révision, désignée par l'utilisateur au lancement de l'import … Lorsque le projet n'en comporte pas, l'import en crée une » ; **WF-CRE-0050** : « la période extraite ».
- **Constat.** Ni la liste des imports ni le compte rendu ne disent sur quelle structure (différentiel, devis propre d'un risque, principale) ni dans quelle révision l'import écrit, ni quelle période une extraction couvre : les résumés des fixtures le disent en prose (`import_analysing.json` : « différentiel de la révision courante (structure_id …203) ») parce que la valeur n'y est pas. L'écran du compte rendu ne peut pas nommer la structure sans relire la requête d'ouverture, qu'il n'a plus après un rechargement, et `applyImport` revérifie « l'état du projet » pour une structure que le lecteur ne connaît pas. Ajouter des champs exigés après le gel est incompatible.
- **Proposition.** Sur `Import` : `structure_id` (Uuid, exigé : la principale résolue quand la requête n'en nommait pas), `revision_id` (Uuid nullable : nul tant que la révision en cours n'est pas créée, à l'application), `period_from`/`period_to` (PlanningDate nullables, exigés, nuls hors coûts réels). Fixtures régénérées/complétées.
- **DECISIONS.md** : aucune (grep « Structure visée », `structure_id` + import).

#### I-09 — La date de terminaison d'une tâche terminée par l'import : jour d'application ou date de la revue ?
- **majeur, question à trancher** ; `docs/api/components/schemas/exchanges.yaml:302-308` : « `completed_on` : Le jour de l'application de l'import ou de la fusion … nul tant que l'import ou la fusion n'est pas appliqué » ; `:540-565` (`ExportRequest`, aucune date de revue) ; **WF-PLA-0130** : « lorsqu'il résulte d'un import ou d'une fusion, la date est le jour de l'application de l'import ou de la fusion » ; **WF-INTF-0120** : « Une tâche dont toutes les lignes du fichier portent un reste nul est terminée à la date de la revue que porte le fichier, et le compte rendu la nomme (WF-RAE-0040) » ; **WF-INTF-0130** : « Le fichier porte la date de la revue, que l'import retient pour terminer une tâche (WF-INTF-0120) » ; annexe B « Synthèse » : « la date de la revue ».
- **Constat.** La spécification 1.0.0 se contredit : WF-PLA-0130 dit le jour d'application, WF-INTF-0120 et WF-INTF-0130 (phrases entrées les 9 et 10 octobre 2026) disent la date de la revue écrite dans le fichier exporté. Le contrat a suivi WF-PLA-0130 (décision EP-02/L35). Si la date de la revue l'emporte : `completed_on` est connu dès l'analyse (non nul), et l'export du reste à engager doit savoir quelle date écrire dans « Synthèse » — l'instant de l'export ? une date demandée (`ExportRequest.review_date`) ? — : deux formes du contrat à changer après le gel. Il faut trancher avant.
- **Proposition.** Question à l'auteur : laquelle des deux phrases fait foi ? Si WF-INTF-0120/0130 : `completed_on` devient « la date de la revue lue dans le fichier, connue à l'analyse », exigée non nulle ; `ExportRequest` gagne `review_date` (PlanningDate, nullable, « la date du jour par défaut ») pour `remaining` ; la fusion garde le jour d'application. Si WF-PLA-0130 : corriger la spécification, et le contrat ne bouge pas.
- **DECISIONS.md** : EP-02/L35, l. 1626-1630 : « `completed_tasks` … leur date nulle tant que l'import n'est pas appliqué — c'est le jour de l'application (WF-PLA-0130) » — prise avant que WF-INTF-0120 ne dise la date de la revue.

#### I-10 — Le contrôle du format : à l'ouverture (422 synchrone) ou à l'analyse (worker) ?
- **majeur** ; `docs/api/paths/exchanges.yaml:235-237` : « L'analyse lit le fichier, contrôle son format et sa version, compare aux données existantes et produit le compte rendu … Confiée au worker (WF-ARC-0090) » et `:304-325` : le 422 `FILE_FORMAT_UNREADABLE` (format, version, `missing_columns`) est une réponse d'`openImport`, qui rend sinon un 202 ; **WF-ARC-0100** : « L'analyse lit le fichier, contrôle son format et sa version (WF-INTF-0070), compare son contenu aux données existantes et produit le compte rendu » ; **WF-ARC-0090** : « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir exécuté ».
- **Constat.** Le contrat place le contrôle de format dans l'analyse (asynchrone) et le refuse pourtant synchroniquement à l'ouverture : l'implémenteur ne sait pas s'il doit ouvrir le classeur (jusqu'à 10 Mio) dans la requête pour lire A1/B1 et la ligne 1 des intitulés, ou si l'analyse échoue (`Import.status: failed`, `task.problem` à `FILE_FORMAT_UNREADABLE`) — les deux lectures sont possibles et le front doit traiter l'une ou l'autre. Le lot US-0640/L6 ajoute un exemple `task_import_analysis_failed` (hors de cette revue) : il rendra la question plus visible encore.
- **Proposition.** Choisir et l'écrire : soit « l'ouverture lit l'en-tête du fichier — format, version, intitulés des colonnes — avant de mettre l'analyse en file, et refuse par 422 ce qu'elle ne reconnaît pas ; l'analyse ne refuse plus un format », soit retirer le 422 de format d'`openImport` et le porter en échec de la tâche d'analyse, `Import.status` à `failed`, `task.problem` le motif. La première forme garde les exemples ; elle demande de préciser WF-ARC-0100 dans la description.
- **DECISIONS.md** : EP-02/L18, l. 905-908 (« `FILE_FORMAT_UNREADABLE` nomme le format et la version attendus ») ne dit pas où le refus tombe ; aucune décision sur le synchrone (grep « synchron » : fusion et restauration seulement).

#### I-11 — Les motifs de rejet d'un devis ne nomment pas ce que la ligne citait, et le libellé ambigu n'a pas de code
- **majeur** ; `docs/api/components/common.yaml:420-620` (`ErrorCode` : aucun code d'ambiguïté) ; `fixtures/api/import_analysed.json` (`rejected: [{ sheet: "Hors lot", row: 3, code: UNKNOWN_TASK, params: {} }, { …, code: UNKNOWN_RESOURCE_ROLE, params: {} }]`) ; `docs/api/components/schemas/exchanges.yaml:360-389` (`ImportRejection`) ; **annexe B** : « Une tâche s'y désigne par son libellé lorsque l'onglet « Tâches » ne la connaît pas ; un libellé que portent plusieurs tâches est signalé au compte rendu (WF-INTF-0080) » ; **WF-INTF-0100** (Vérif) : « Une ligne qui cite une tâche, un rôle ou un sous-projet inconnu … est rejetée et figure au compte rendu ».
- **Constat.** (1) Le libellé de tâche porté par plusieurs tâches est un motif de rejet que la spécification nomme et que le catalogue n'a pas : code à inventer après le gel. (2) `UNKNOWN_TASK`, `UNKNOWN_RESOURCE_ROLE`, `UNKNOWN_SUBPROJECT` rejettent une ligne sans dire quelle valeur du fichier n'a pas été reconnue (`params: {}` dans le seul exemple) : l'utilisateur relit son fichier à l'aveugle, quand le compte rendu « se lit sans relire » ailleurs (`TASK_WITHOUT_WORKING_HOURS` nomme rôles et tâche).
- **Proposition.** `ErrorCode` gagne `AMBIGUOUS_TASK_LABEL`, `params.label` et `params.tasks` (les tâches candidates, `lineage_id`, `label`) ; les trois `UNKNOWN_*` portent, dans `ImportRejection.params`, la valeur lue (`params.value`, texte tel que le fichier le porte). Fixture `import_analysed` complétée.
- **DECISIONS.md** : aucune (grep « ambigu », « plusieurs tâches »).

#### I-12 — Une extraction ERP avec un numéro de version
- **mineur** ; `fixtures/api/import_actual_costs_analysed.json`, `import_actual_costs_column_ignored.json`, `import_actual_costs_duplicate_line.json` : `"format_version": "1"` pour `kind: actual_costs` ; `docs/api/components/schemas/exchanges.yaml:183-184` (`format_version`, sans description) ; **WF-INTF-0070** : « le format « Coûts réels », extrait de l'ERP, n'en porte pas » ; **le contrat lui-même** : `import_actual_costs_column_missing.json` « sans version — une extraction de l'ERP n'en porte pas ».
- **Constat.** Trois exemples servis par le faux back contredisent la spécification et un quatrième exemple de la même famille ; le front afficherait « version 1 » d'un fichier qui n'en a pas. `format_version` n'a pas de description qui dise quand il est nul (MS Project, coûts réels).
- **Proposition.** `null` dans les trois fixtures ; description : « La version du format lue en B2 d'un devis ou d'un reste à engager (annexe B) ; nulle pour un planning MS Project et une extraction de coûts réels, qui n'en portent pas (WF-INTF-0070) ».
- **DECISIONS.md** : US-0620 (l. 7772-7775) dit « sans `expected_version`, une extraction de l'ERP n'en ayant pas (D-2) » — la fixture lui est contraire.

#### I-13 — Des champs « toujours rendus » qui ne sont pas exigés
- **mineur** ; `docs/api/components/schemas/exchanges.yaml:164-165` (`ImportReport.required` sans `format_version` ni `requires_confirmation_reasons`, alors que `:177-179` dit « Les tableaux sont toujours rendus, vides quand il n'y a rien à dire ») ; `:424` (`ImportDifference.required: [change, target]`, `label` facultatif alors que tout écart en porte un) ; `docs/api/components/schemas/costs.yaml:5-15` (`ActualCostLine.required` sans `excluded_reason` ni `passthrough`, que la grille présente à toutes les lignes, `paths/costs.yaml:9-11`) ; **WF-INTF-0080**, **WF-CRE-0010**.
- **Constat.** Toutes les fixtures les portent ; le client généré les type pourtant facultatifs, et l'écran doit distinguer absent de vide — ce que la description de `ImportReport` dit vouloir éviter. Ajouter à `required` après le gel est une rupture pour les émetteurs ; maintenant c'est sans coût.
- **Proposition.** Exiger `format_version` (nullable), `requires_confirmation_reasons`, `ImportDifference.label` (nullable), `ActualCostLine.excluded_reason` (nullable) et `passthrough`.
- **DECISIONS.md** : EP-02/L35, l. 1232 (« trois tableaux exigés ») ne couvre pas `requires_confirmation_reasons`, antérieur ; aucune décision sur `passthrough`/`excluded_reason`.

#### I-14 — `Import.status` sans description, `expires_at` exigé avant l'analyse
- **mineur** ; `docs/api/components/schemas/exchanges.yaml:151-153` (`status: enum: [analysing, analysed, applying, applied, abandoned, expired, failed]`, aucune description) ; `:155-157` (`expires_at` exigé, « Vingt-quatre heures après l'analyse ») ; `fixtures/api/import_analysing.json` (`status: analysing`, `expires_at: 2026-06-04T08:41:00Z` alors que l'analyse n'est pas finie) ; **WF-ARC-0100**.
- **Constat.** Rien ne dit quel état prend un import dont l'application est refusée à l'exécution (droits, état, `import_file_accepted` : « seul l'abandon reste offert » → reste `analysed` ?), ni si `failed` couvre l'analyse échouée et l'application échouée ; l'écran de la liste des imports ne peut pas distinguer. `expires_at`, défini par l'analyse, est exigé d'un import encore en analyse : la fixture invente une valeur.
- **Proposition.** Décrire chaque état et ses transitions ; `expires_at` nullable tant que `analysing` (ou défini comme « vingt-quatre heures après l'ouverture »).
- **DECISIONS.md** : aucune (grep `Import.status`, « expired »).

#### I-15 — Les champs facultatifs de l'ouverture et leurs refus
- **mineur** ; `docs/api/components/schemas/exchanges.yaml:132-138` (`structure_id` : « Structure visée ; la structure principale par défaut » ; `period_from`, `period_to` : aucune description) ; `docs/api/paths/exchanges.yaml:304-317` (422 : format, colonnes, usage du dépôt seulement) ; **WF-CRE-0050** (« la période extraite »), **WF-INTF-0090**, convention README « Une période … Une fin qui précède le début est refusée par 422 … `VALUE_OUT_OF_RANGE` ».
- **Constat.** La période n'est dite ni propre aux coûts réels, ni facultative à chaque borne (le journal en montre trois formes), ni refusée inversée ; une `structure_id` inconnue ou d'une autre révision, un `upload_id` inconnu ou déjà consommé (le 409 dit « fichier déjà consommé », pas l'inconnu) n'ont pas de refus décrit (404 ? 422 `/upload_id` ?).
- **Proposition.** Descriptions : « `period_from`/`period_to` : la période extraite de l'ERP, pour `actual_costs` seul, chaque borne facultative, journalisée (WF-CRE-0050) ; une fin avant le début est refusée par 422, `/period_to`, `VALUE_OUT_OF_RANGE`, `params.minimum` le début » ; « `structure_id` : une structure de la révision en cours — ou de la dernière marquée, dont la révision en cours se créera — ; inconnue, 404 » ; « `upload_id` inconnu ou expiré : 404 ».
- **DECISIONS.md** : aucune.

#### I-16 — La nature d'un export est une énumération anonyme
- **mineur** ; `docs/api/components/schemas/exchanges.yaml:548-554` (`ExportRequest.kind: enum: [ms_project_schedule, estimate, remaining, task_tree_image]`, en ligne) contre `:108-117` (`ExchangeKind`, nommé) ; `:561-562` (`structure_id` sans description) ; **WF-INTF-0050/0110/0130** : « la structure principale par défaut » ; **WF-PLA-0120**.
- **Constat.** `RevisionCommand.export_*` et `getBackgroundTaskResult` renvoient à « la nature de l'export (`ExportRequest.kind`) » qui n'a pas de nom de schéma : le client généré y voit une union littérale anonyme, et le catalogue du front ne peut pas la nommer comme il nomme `ExchangeKind`. `structure_id` ne dit pas le défaut ni ce qu'il vaut pour l'image d'arborescence.
- **Proposition.** Un schéma `ExportKind` (les quatre valeurs, avec la description FLX-02/04/06 + image hors flux, WF-INTF-0150) référencé par `ExportRequest.kind` ; description de `structure_id` : « la structure exportée ; la principale par défaut (WF-INTF-0050, 0110, 0130, WF-PLA-0120) ».
- **DECISIONS.md** : EP-02/L17 (l. 1027-1029) nomme les commandes par nature d'export sans nommer l'énumération.

#### I-17 — Un 409 d'export sans cause
- **mineur** ; `docs/api/paths/exchanges.yaml:485` (`'409': { $ref: Conflict }`, générique, sans exemple) ; **WF-CYC-0110** (exports d'un projet terminal aboutissent).
- **Constat.** DECISIONS (EP-02/L17, l. 1046-1052) : « un export ne manque d'aucune condition, ni sur une révision marquée, ni pendant un marquage, ni sur un projet terminal. Il est présent ou absent ». Le 409 déclaré n'a donc aucune cause décrite ; un implémenteur ne sait pas quoi y mettre, et le refus n'a pas d'exemple.
- **Proposition.** Retirer le 409, ou dire sa seule cause si elle existe (par exemple une révision en cours d'abandon).
- **DECISIONS.md** : EP-02/L17, citée ; elle plaide pour le retrait.

#### I-18 — L'abandon d'un import déjà appliqué
- **mineur** ; `docs/api/paths/exchanges.yaml:370-385` (`abandonImport` : 204, 401, 403, 404, 503) ; **WF-ARC-0100**, **WF-INTF-0080**.
- **Constat.** `DELETE` sur un import `applied`, `applying`, `expired` ou `abandoned` : 204 silencieux (et la liste le dit toujours appliqué ?), 404, ou 409 ? Rien ne le dit ; le front qui offre « Abandonner » sur le compte rendu doit savoir.
- **Proposition.** « Un import appliqué, en cours d'application, expiré ou déjà abandonné est refusé par 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `import_analysed` », avec exemple ; ou déclarer l'abandon idempotent et le dire.
- **DECISIONS.md** : aucune.

#### I-19 — Les filtres de la consultation sans description
- **mineur** ; `docs/api/paths/costs.yaml:19-27` (`from`, `to`, `in_tracked_scope` : schéma seul) ; **WF-CRE-0040** : « filtrable par sous-projet, par période et selon l'exclusion » ; convention README (« une date de planning sa fin incluse »).
- **Constat.** Quelle colonne la période filtre (`document_date`, et non la date d'import), que la fin est incluse, que `in_tracked_scope=false` rend les exclues seules : le 422 le laisse deviner, pas le paramètre.
- **Proposition.** `from`/`to` : « bornes de la date de pièce (`document_date`), incluses » ; `in_tracked_scope` : « vrai, les lignes suivies seules ; faux, les exclues seules ; absent, toutes ».
- **DECISIONS.md** : EP-02/L18, l. 866-870 (le 422) ; rien sur la description.

#### I-20 — Exemples manquants
- **mineur** ; `docs/api/paths/exchanges.yaml:354-366` (`getImport`), `:441-442` (`applyImport` 409 : un seul exemple, `import_file_accepted`), `:478-484` (`requestExport` 404 : sans exemple) ; **WF-INTF-0080**, **WF-CRE-0020**, **WF-INTF-0120**, **WF-ARC-0100**.
- **Constat.** Aucun compte rendu de premier import de coûts réels (`added` d'`actual_cost_line`, `lines_outside_project`, lignes rejetées sur l'OTP — I-02) alors que le journal en suppose cinq ; aucun `completed_tasks` non vide (DECISIONS l. 1633 : « la liste non vide n'a pas d'exemple ») ; aucun 409 d'application pour une condition de droits ou d'état cessée (`project_before_in_progress` à l'application, décrit l. 434-437) ; aucun 404 d'export pour une révision d'un autre projet.
- **Proposition.** Quatre fixtures écrites à la main ou engendrées (le témoin a les données : l'extraction de mars, c11, crée trois lignes).
- **DECISIONS.md** : l. 1633 reconnaît l'absence d'exemple de `completed_tasks`.

### Ce qui est juste

- L'idempotence des coûts réels : `document_number` + `document_item` nullable (« un poste nul est une valeur comme une autre »), `DUPLICATE_COST_LINE` avec `params.rows` et `sheet: null`, l'exclusion préservée au réimport, l'imputation recalculée (`subproject` en `fields`) — schémas, descriptions, `common.yaml` et fixtures d'accord (WF-INTF-0140, WF-DAT-0110, WF-CRE-0020/0030, D-4). La correspondance : 409 `actual_cost_mapping_complete` + `params.columns` (quatre colonnes, ordre de l'énumération) et 422 `FILE_FORMAT_UNREADABLE` + `missing_columns` sans `expected_version` cohérents entre `openImport`, `ProblemParams`, `ProjectCommand`, `ActualCostMapping` et les fixtures ; `ImportIgnoredKind.columns` et `import_actual_costs_column_ignored` conformes à WF-REF-0190.
- La consultation : les 28 lignes d'`actual_costs.json` somment aux trois totaux (1 412 970,20 + 650,00 = 1 413 620,20), `actual_costs_page`/`_subproject`/`_after_exclusion` cohérents (totaux et `passthrough_columns` sur toutes les lignes retenues, `last_import_at` = `cost_imports[0].imported_at`), les codes inconnus SP-AUT/SP-CAB/SP-REC imputés au seul projet avec leur code, l'avoir négatif ; `sort_by` (chaque colonne, `passthrough.<colonne>`, nuls en queue), 422 période inversée (`/query/to`, `minimum`) et `UNKNOWN_SUBPROJECT` suivent les conventions ; `imports.json` ↔ `cost_imports.json` concordent (cinq imports `actual_costs` appliqués, identifiants, instants). Les noms suivent le §4.4.1 (`cost_line`, `cost_import`, `estimate_line`, `subproject`, `lineage_id`).
- Les échanges : l'import en deux temps (202 → `Import` → `applyImport` 202 `BackgroundTaskRef`, 409 `import_file_accepted`, expiration 24 h, revérification des droits et de l'état, `project_before_in_progress` à l'ouverture et à l'application, `SUBPROJECT_HAS_ACTUAL_COSTS` avec `sheet`) ; `ImportRejection.sheet` et les onglets fixes (WF-INTF-0180) ; `refusals` (`ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, `PROJECT_HORIZON_EXCEEDED`), `kept`, `date_mismatches` vides sur l'aller-retour (WF-INTF-0060), `signals` `NON_WORKING_DAY`, `work_breakdown_label`, `predecessor_label`, `parent` ; `ExchangeKind` couvre FLX-01 à FLX-07 et les commandes `import_*`/`export_*` correspondent ; `uploadFile` 10 Mio ≥ « 10 Mo » du §4.6.2, `UPLOAD_PURPOSE_MISMATCH` des deux côtés ; le dépôt par morceaux (5–10 Mio, 10 000 morceaux, 413, 422 `/body` et `/size_bytes`, 409 `missing_parts`, 422 manifeste) avec un exemple par refus ; 401/503 partout, 400/422 sur toute opération à corps.

### Doutes

- **`setActualCostTrackedScope` sans `lock_version`** (`paths/costs.yaml:110-114`, `ScopeExclusion`) : la convention veut le `lock_version` « sur les écritures concurrentes » ; DECISIONS (l. 8-12) fait du `PUT …/tracked-scope` un état idempotent « rejouable ». Deux utilisateurs qui excluent et réintègrent la même ligne au même instant : dernier écrit gagne, sans 412. Non tranché ici.
- **`uploadFile` sans 403** (`paths/exchanges.yaml:39-43`) : tout compte authentifié peut déposer 10 Mio sur le stockage objet, la permission n'étant jugée qu'à `openImport`. La spécification ne dit rien du dépôt lui-même.
- **`requires_confirmation_reasons: unknown_subproject`** est global : WF-CRE-0020 dit la ligne « signalée », la Vérif renvoie à la consultation « avec son code ». Le compte rendu ne nomme pas les codes inconnus par ligne (l'`ImportDifference` d'un `added` n'a pas de `subproject_code`). Suffisant ou non, question de lecture de « signalée ».
- **La date de début de planning d'une structure** n'apparaît dans aucun schéma de `revisions.yaml` (grep « début de planning » : une seule mention descriptive, `NodeListMeta.scheduled_at`) alors que WF-PLA-0020 la dit « saisie » : hors famille, mais I-03 en dépend.
- **La langue des exports** : l'image d'arborescence (`task_tree_image`) est un document engendré « dans la langue du compte destinataire » (WF-ARC-0110) tandis que la description de `requestExport` ne parle que des en-têtes fixes des formats Excel (WF-INTF-0180) ; l'API ne porte aucune langue, le serveur lit celle du compte. Rien à changer au contrat, une phrase de description le dirait. Le nom de l'entreprise et le client (annexe B, « Présentation ») sont des contenus du fichier, lus de `ReferenceSettings.company_name` et `Project.client` : aucun champ d'API n'est attendu.

## Annexe J — Transversal : composants partagés et conventions


Lu : `docs/api/openapi.yaml`, `components/common.yaml` (860 l.), `components/parameters.yaml` (507 l.),
`components/responses.yaml`, `redocly.yaml`, `.redocly.lint-ignore.yaml`, `README.md` (Conventions en
entier), `INVENTORY.md` ; spec §1.3 (92–158), §3.6 entier (3174–3352), §4.1 (3354–3420), §4.4.1
(3847–3980), §4.6.2 (4259–4329), WF-ARC-0020/0060/0090/0110, WF-DAT-0060/0100, WF-ADM-0110,
WF-IHM-0110/0130 ; DECISIONS.md par grep sur chaque constat. Un script (`scratchpad/audit_j.py`, sortie
`audit_j.out`) a parcouru les 13 fichiers `paths/`, les 11 `schemas/`, `common.yaml` et les 598 fixtures
(580 dans `fixtures/api/`, 18 dans `fixtures/api/volume/`) : 163 opérations, 127 chemins, 324 schémas,
87 codes d'erreur, 54 conditions, 1 291 propriétés, 618 références de fixtures.

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| J-01 | majeur | `paths/projects.yaml:960-966` (`deleteTimeline`), `paths/revisions.yaml:1764` (`generatePlanningSkeleton`) vs `projects.yaml:214,442,572,630,825`, `exchanges.yaml:286` | Un projet terminal est refusé par 403 `PROJECT_TERMINAL` ici, par 409 `STATE_FORBIDS_OPERATION`/`project_not_terminal` là : deux formes pour un même refus | WF-CYC-0100, WF-ARC-0110 |
| J-02 | majeur | `components/common.yaml:397` (`REVISION_MARKED`), `responses.yaml:33-35`, `paths/revisions.yaml:776,1764` | `REVISION_MARKED` (403) n'est rendu par aucune opération ; les écritures d'une révision marquée sont 409 `revision_draft`, sauf le squelette qui dit 403 et `createNode` qui ne dit rien | WF-DAT-0020, WF-ARC-0110 |
| J-03 | majeur | `components/common.yaml:395,409,420-421,433,447,453` | Sept codes du catalogue qu'aucune opération ne nomme et qu'aucun exemple ne porte (`NOT_PROJECT_MANAGER`, `UNDO_CONFLICT`, `TASK_ALREADY_STARTED`, `TASK_COMPLETED`, `SUMMARY_TASK_DERIVED`, `RESOURCE_ROLE_REQUIRED`, `PROJECT_CODE_REQUIRED`) : doublons de `STATE_FORBIDS_OPERATION` ou orphelins | WF-ARC-0110, WF-ARC-0060 |
| J-04 | majeur | `paths/revisions.yaml:1082-1084` (`updateTaskFacet`), `common.yaml:151-152,433` | La date d'une récapitulative est refusée « `COMPUTED_VALUE`, sans paramètre » ; la spec veut qu'on nomme ses subordonnées, et `params.subordinate_node_ids`/`SUMMARY_TASK_DERIVED` existent sans être rendus | WF-IHM-0030 |
| J-05 | majeur | `paths/revisions.yaml:1673-1690` (`undoLastChange`), `redoLastUndo`, `schemas/revisions.yaml:1761-1763`, `common.yaml:409` | Le 409 d'une annulation « qu'une modification postérieure porte sur le même objet » ne nomme ni code ni l'objet en conflit ; `UNDO_CONFLICT` reste inemployé | WF-IHM-0110 |
| J-06 | majeur | `paths/revisions.yaml:1169-1170` (`updateEstimateLine`), `paths/revisions.yaml:150-158` (`markRevision`), `fixtures/api/task_failed.json` | « Taux horaire manquant… ou rôle absent » sans code nommé ; `HOURLY_RATE_MISSING` n'apparaît que dans l'échec d'une tâche `revision_mark` qu'aucune description n'annonce ; `RESOURCE_ROLE_REQUIRED` nulle part | WF-DEV-0010, WF-DEV-0020, WF-IHM-0080 |
| J-07 | majeur | `components/common.yaml:616-619`, toutes les opérations | `INTERNAL_ERROR` (5xx) est au catalogue et `correlation_id` décrit pour « une erreur inattendue », mais aucune opération ne déclare de `500` ni de `default` | WF-ARC-0060, WF-OBS-0020 |
| J-08 | majeur | `paths/reference.yaml:164,830,1148` vs `:425/521, 1372/1421, 1625/1686` ; `parameters.yaml:50-53` | `include_inactive` sans permission est « refusé par 403 » pour les rôles, les catégories et la grille des taux ; `listOrgNodes`, `listCalendars`, `listCostTypes` prennent le même paramètre sans déclarer ni décrire le 403 | WF-REF-0150, WF-ADM-0100 |
| J-09 | majeur | `paths/projects.yaml:542-600` (`createSubproject`) | Seule écriture sous `/projects/{project_id}` sans `404` : un projet inexistant ou invisible n'a pas de réponse déclarée | WF-ADM-0110 |
| J-10 | majeur | `parameters.yaml:89-101` (`NodeFields`), `paths/revisions.yaml:766` (`listNodes`), `:404` (`compareRevisions`) | Une propriété inconnue de `fields` « est refusée (400) », seul paramètre de requête refusé par 400 `MALFORMED_REQUEST` au lieu de 422 `/query/fields` | WF-ARC-0110, WF-IHM-0130 |
| J-11 | majeur | `schemas/projects.yaml:296,297,300,301,312` (`CommandCondition`) | Trois conditions sans description, sans opération ni exemple (`project_code_set`, `at_least_one_estimate_line`, `hourly_rates_set`) ; deux employées par les exemples mais jamais décrites (`project_in_pricing`, `no_current_revision`) | WF-IHM-0090, WF-CYC-0050 |
| J-12 | mineur | `paths/access.yaml:620-636` (`listAccessRoles`), `paths/risks.yaml:280-291` (`listRiskReviews`) | Tables plates triées/filtrées sans `limit`/`offset`/`meta`, sans la justification de volume que `listSubprojects` et `listContributors` donnent | WF-IHM-0060 |
| J-13 | mineur | `paths/projects.yaml:917` (`createTimeline`) | `label` reçu sans `pattern: '\S'` : seul libellé d'écriture du contrat qui admet un nom fait de blancs | WF-ARC-0110 (README « Un libellé… ») |
| J-14 | mineur | `components/common.yaml:625-634` (`FieldProblem.pointer`), `paths/exchanges.yaml:104,135` | Le pointeur `/body` d'un morceau déposé (décidé, DECISIONS 3847) n'est pas une forme que la description de `pointer` admet | WF-ARC-0110 |
| J-15 | mineur | `paths/costs.yaml:19-26` (`listActualCosts`) | `from`, `to`, `in_tracked_scope` sans description : la seule période du contrat qui ne dit pas ses bornes | WF-IHM-0130 |
| J-16 | mineur | `paths/system.yaml:83-98` (`getMetrics`) | Opération publique qui déclare un seul refus, `404` partagé « objet inexistant ou invisible », sans dire quand ; ni `503` comme les autres sondes, ni exception dans `.redocly.lint-ignore.yaml` | WF-OBS-0010, WF-ARC-0060 |
| J-17 | mineur | `responses.yaml:3-7,66-70`, `common.yaml:377,429,464-465,473,477-487,586` | Treize codes déclarés sans aucun exemple, dont `MALFORMED_REQUEST`, `FILE_TOO_LARGE`, `NUMBER_INVALID`, `DATE_INVALID`, `FIELD_NOT_ACCEPTED`, `UNKNOWN_CALENDAR`, `ACCESS_ROLE_IN_USE`, `SESSION_REQUIRED`, `ACCOUNT_*` | WF-QUA-0020 |
| J-18 | mineur | `schemas/projects.yaml:292-293,317` | `is_contributor`, `is_project_manager`, `task_not_milestone` : conditions décrites sans aucun exemple de `missing_conditions` ni de `missing_condition` | WF-IHM-0090 |
| J-19 | mineur | `schemas/revisions.yaml:363-364` (`StructureCreate.kind`) | Seule énumération du contrat écrite `allOf` + `enum` sans `type` ; les 323 autres schémas typent leurs énumérations | — |
| J-20 | mineur | `parameters.yaml:3-11` (`Limit`, `Offset`), `common.yaml:87-90` (`Year`) | Trois types/paramètres partagés sans description ; `Limit.maximum: 500` ne cite pas la règle des pages (10/25/50/100) | WF-IHM-0060 |
| J-21 | mineur | `fixtures/api/risk_matrix_no_basis.json`, `paths/risks.yaml:474` | Fixture engendrée et nommée « exemple » par DECISIONS 7525, qu'aucun fichier du contrat ne référence | WF-RIS-0040 |

### Constats

#### J-01 — Un projet terminal, refusé par 403 ici et par 409 là
- **gravité** majeur ; **emplacement** `docs/api/paths/projects.yaml:960-966` (`deleteTimeline`, 403), `docs/api/paths/revisions.yaml:1764` (`generatePlanningSkeleton` : « refusée sur une révision marquée ou un projet terminal, par 403, comme toute saisie »), `docs/api/components/common.yaml:389-397` (le bloc 403 d'`ErrorCode` range `PROJECT_TERMINAL`), `docs/api/components/responses.yaml:33-35` (`Forbidden` : « qualité de contributeur, état du projet, révision marquée ») — contre `docs/api/paths/projects.yaml:214` (`updateProject`), `:442` (`setWorkBreakdown`), `:572` (`createSubproject`), `:630` (`updateSubproject`), `:825` (`setContributors`) et `docs/api/paths/exchanges.yaml:286` (`openImport`), tous « projet terminal (WF-CYC-0100), `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_not_terminal` » en 409 ; **exigence** WF-CYC-0100 (« qu'elle soit tentée par la saisie, par un import Excel ou MS Project, ou par un traitement automatique »), WF-ARC-0110 (un code, pas une phrase).
- **ce que dit le contrat** : `deleteTimeline` → « sur un projet terminal `PROJECT_TERMINAL`, `params.missing_condition` à `project_not_terminal` » (403) ; `createSubproject` → « ou un projet terminal (WF-CYC-0100), `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_not_terminal` » (409). Le seul exemple de `project_not_terminal` dans une enveloppe est `timeline_delete_terminal.json` (403 `PROJECT_TERMINAL`) ; les 20 autres fixtures qui nomment la condition sont des `available_commands`.
- **Constat.** Le même cas — une écriture sur un projet clos — a deux statuts et deux codes selon l'opération. Le front doit rendre une même phrase sur deux chemins (catalogue d'erreurs et catalogue de conditions), l'implémenteur du service choisit au hasard, et après le gel, aligner les uns sur les autres est un changement de statut HTTP, incompatible. Le modèle général du contrat (commandes et conditions, DECISIONS « Le projet et la révision portent leurs commandes disponibles ») est le 409 `STATE_FORBIDS_OPERATION` ; `PROJECT_TERMINAL` est un reste de l'écriture d'origine.
- **Proposition.** Retirer `PROJECT_TERMINAL` d'`ErrorCode` ; `deleteTimeline` déclare un `409` partagé (`Conflict`) et sa description dit `STATE_FORBIDS_OPERATION`/`project_not_terminal` comme `createSubproject` ; l'exemple `timeline_delete_terminal` passe à 409 ; `generatePlanningSkeleton` et `createNode` (`revisions.yaml:776`) nomment le 409 ; `Forbidden` ne parle plus d'« état du projet ». Ou, si l'auteur veut garder le 403 pour l'état terminal, le dire dans toutes les opérations et dans le README — mais la convention écrite (« 403 lorsque c'est l'écriture ou la qualité de contributeur ») ne le prévoit pas.
- **DECISIONS.md** : « Sur un projet clos, `project_not_terminal` vient en dernier » (l. 4292, EP-14/L42l) ne connaît que la forme 409 ; aucune décision ne mentionne `PROJECT_TERMINAL`.

#### J-02 — `REVISION_MARKED` n'est rendu par personne, et la révision marquée est 403 ou 409 selon le paragraphe
- **gravité** majeur ; **emplacement** `docs/api/components/common.yaml:397`, `docs/api/components/responses.yaml:33-35`, `docs/api/paths/revisions.yaml:776` (`createNode` : « Refusé sur une révision marquée (WF-DAT-0020) et sur un projet terminal (WF-CYC-0100) », sans code), `:1764` (`generatePlanningSkeleton`, « par 403 ») ; **exigence** WF-DAT-0020, WF-ARC-0110.
- **ce que dit le contrat** : partout ailleurs (`revisions.yaml:315`, `:598`, 78 exemples) une écriture sur une révision marquée est 409 `STATE_FORBIDS_OPERATION`, `missing_condition` à `revision_draft`. `REVISION_MARKED` n'a ni emploi (une seule mention : sa ligne du catalogue) ni exemple.
- **Constat.** Même défaut que J-01 pour la révision marquée : un code mort au catalogue, une réponse partagée qui l'annonce, deux opérations qui disent 403 et une qui ne dit rien. Le front qui lit `Forbidden` attend un 403 qui ne viendra pas.
- **Proposition.** Retirer `REVISION_MARKED` ; `Forbidden` ne garde que « permission présente, qualité de contributeur ou de chef de projet manquante » ; `generatePlanningSkeleton` et `createNode` disent le 409 `revision_draft`.
- **DECISIONS.md** : aucune décision ne nomme `REVISION_MARKED`.

#### J-03 — Sept codes d'erreur que rien ne rend
- **gravité** majeur ; **emplacement** `docs/api/components/common.yaml:395` (`NOT_PROJECT_MANAGER`), `:409` (`UNDO_CONFLICT`), `:420-421` (`TASK_ALREADY_STARTED`, `TASK_COMPLETED`), `:433` (`SUMMARY_TASK_DERIVED`), `:447` (`RESOURCE_ROLE_REQUIRED`), `:453` (`PROJECT_CODE_REQUIRED`) ; **exigence** WF-ARC-0110 (« le front n'en rencontre aucun qu'il ne sache rendre »), WF-ARC-0060.
- **ce que dit le contrat** : `ErrorCode` (l. 369-374) : « chaque refus que l'API peut opposer… y a son code ». Relevé : pour chacun de ces sept codes, zéro mention dans `paths/*.yaml`, `schemas/*.yaml`, `parameters.yaml`, `responses.yaml`, et zéro exemple (fixtures et inline). `TASK_ALREADY_STARTED`/`TASK_COMPLETED` sont couverts par `setTaskProgress` 409 `STATE_FORBIDS_OPERATION` `task_not_completed`… (`revisions.yaml:1295-1301`) ; `NOT_PROJECT_MANAGER` par la condition `is_project_manager` (elle-même sans opération, J-11/J-18) ; `PROJECT_CODE_REQUIRED` par le déclencheur `reference_designated_and_code_set` de `NextState` sans condition correspondante.
- **Constat.** Un catalogue figé qui porte des codes morts oblige le front à écrire des textes qu'il ne verra jamais, et laisse l'implémenteur libre de les rendre, ce qui ferait deux formes pour un cas (J-01, J-02). Retirer un code après le gel est une modification du contrat ; le faire maintenant ne rompt rien.
- **Proposition.** Pour chacun : soit l'opération qui le rend le nomme et a son exemple (J-04, J-05, J-06 disent où), soit il sort du catalogue. Un test d'outil (« tout code d'`ErrorCode` est nommé par une opération ou un schéma hors `common.yaml` ») tiendrait la règle.
- **DECISIONS.md** : l. 289-291 (EP-02/L7) nomme `NOT_PROJECT_MANAGER` et `is_project_manager` comme le modèle du refus d'une action structurante — jamais rattaché à une opération depuis ; l. 90 cite `SUMMARY_TASK_DERIVED` (voir J-04) ; aucune décision pour les cinq autres.

#### J-04 — La date d'une récapitulative : refusée « sans paramètre » quand la spec veut nommer les subordonnées
- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:1082-1084` (`updateTaskFacet`, 422) ; `docs/api/components/common.yaml:151-152` (`Problem.params` : « `subordinate_node_ids` (les subordonnées directes d'une récapitulative, WF-IHM-0030, WF-PLA-0040) »), `:433` (`SUMMARY_TASK_DERIVED`) ; **exigence** WF-IHM-0030, Vérif : « La tentative de modifier la date de fin d'une tâche récapitulative est refusée en nommant ses subordonnées. »
- **ce que dit le contrat** : « une valeur calculée — une date d'une tâche en mode automatique, sans paramètre, la grille lisant ce dont elle dépend (`getComputedValueDependencies`) — (`COMPUTED_VALUE`…) ». Aucune opération ne rend `subordinate_node_ids` (grep : zéro occurrence hors `common.yaml`), et le cas de la récapitulative n'est pas distingué de celui d'une tâche automatique.
- **Constat.** Le contrat porte le paramètre et un code dédiés, les décrit dans `Problem.params`, et l'opération qui devrait les rendre dit explicitement « sans paramètre » : contradiction interne, et avec le Vérif de WF-IHM-0030. Renvoyer à une seconde lecture (`getComputedValueDependencies`) n'est pas « refusée en nommant ».
- **Proposition.** Dans `updateTaskFacet` 422 : « sur une récapitulative, `fields[].params.subordinate_node_ids` nomme ses subordonnées directes » (en gardant `COMPUTED_VALUE`, et en retirant `SUMMARY_TASK_DERIVED` du catalogue ; ou l'inverse, mais un seul code), avec un exemple ; typer `subordinate_node_ids` dans `ProblemParams` (tableau d'`Uuid`).
- **DECISIONS.md** : l. 90 (« Calculé contre saisi ») : « `subordinate_node_ids` (`SUMMARY_TASK_DERIVED`) sont les subordonnées directes » — la décision existe, le contrat des opérations ne l'a jamais reçue.

#### J-05 — L'annulation refusée pour conflit n'a ni code ni objet nommé
- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:1673-1690` (`undoLastChange`, 409), même forme pour `redoLastUndo` ; `docs/api/components/schemas/revisions.yaml:1761-1763` (`UndoResult`) ; `docs/api/components/common.yaml:409` (`UNDO_CONFLICT`) ; **exigence** WF-IHM-0110 : « Elle est refusée, en nommant l'objet en conflit, lorsqu'une modification postérieure porte sur le même objet » ; Vérif : « L'annulation d'une modification qu'un autre contributeur a depuis reprise est refusée en nommant l'objet en conflit. »
- **ce que dit le contrat** : « Une modification postérieure porte sur le même objet, ou l'historique de la session est vide (WF-IHM-0110). Ou l'annulation rendrait un sous-projet supprimé… : `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `restored_subproject_exists`… ». Les deux premiers cas n'ont ni code ni `params` ; le seul exemple (`undo_risk_without_task`) est le troisième cas.
- **Constat.** Le refus que la spec exige le plus précisément (nommer l'objet) est celui que le contrat décrit le moins : l'implémenteur ne sait pas s'il rend `UNDO_CONFLICT` (au catalogue, jamais nommé) ou `STATE_FORBIDS_OPERATION`, ni sous quel paramètre nommer l'objet (`node_id` ? `risk_id` ?). Un historique vide n'est pas un conflit : il mérite sa forme.
- **Proposition.** « `UNDO_CONFLICT`, `params.conflicting_object_id` (et `conflicting_object_kind`, `task`/`estimate_line`/`risk`) l'objet repris depuis ; `STATE_FORBIDS_OPERATION`, `missing_condition` à `undo_history_not_empty` (condition nouvelle) pour un historique vide » ; deux exemples ; typer ces paramètres dans `ProblemParams`.
- **DECISIONS.md** : aucune décision ne nomme `UNDO_CONFLICT` ; la section « Collage et annulation » (l. 8243) ne traite pas du conflit.

#### J-06 — Taux manquant et rôle absent : un refus décrit sans code, un code rendu sans description
- **gravité** majeur ; **emplacement** `docs/api/paths/revisions.yaml:1169-1170` (`updateEstimateLine`, 422 : « Taux horaire manquant pour l'année de référence, ou rôle absent sur une ligne de main-d'œuvre (WF-DEV-0010, WF-DEV-0020) ; ou… »), `docs/api/paths/revisions.yaml:150-158` (`markRevision`), `docs/api/components/common.yaml:818-837` (`BackgroundTaskRef.kind`), `:447,452` ; `fixtures/api/task_failed.json` (`kind: revision_mark`, `problem.code: HOURLY_RATE_MISSING`, 422), référencée par `paths/system.yaml:194` seulement ; **exigence** WF-DEV-0010 (Vérif : « Le refus énumère les catégories de coût sans taux horaire pour l'année de référence »), WF-IHM-0080 (« l'échec nomme ce qui a échoué »).
- **ce que dit le contrat** : la phrase d'`updateEstimateLine` ne nomme aucun code pour ces deux cas, alors que tous les autres cas du même paragraphe en nomment un ; `HOURLY_RATE_MISSING` n'apparaît dans aucune description (une seule mention : sa ligne du catalogue), mais une tâche de marquage échoue dessus dans un exemple ; `RESOURCE_ROLE_REQUIRED` n'apparaît nulle part.
- **Constat.** L'implémenteur du service ne sait pas quel code rendre sur la ligne (`VALIDATION_FAILED` + motif par champ ? `HOURLY_RATE_MISSING` seul ?), ni quels paramètres (la spec veut l'énumération des catégories : `params.missing_rates`, que `getEstimateIndicators` connaît déjà sous `Computable.params`, DECISIONS l. 464-472). Le marquage, lui, échoue sur un code que ni sa description ni celle de la tâche n'annoncent.
- **Proposition.** `updateEstimateLine` 422 : « `fields` sur `/cost_category_id` par `HOURLY_RATE_MISSING`, `fields[].params.missing_rates` (des `MissingRate`) ; `/resource_role_id` par `RESOURCE_ROLE_REQUIRED` » ; `markRevision` et `BackgroundTaskRef.kind` : « un marquage échoue par `HOURLY_RATE_MISSING`, `params.missing_rates`, quand une ligne de main-d'œuvre n'a pas de taux à l'année de référence » ; typer `missing_rates` dans `ProblemParams`.
- **DECISIONS.md** : l. 464-472 (EP-02/L8) oppose le motif `hourly_rate_missing` de `Computable` au « code d'erreur `HOURLY_RATE_MISSING` qui dit le même refus sur une écriture » — l'écriture qui le rend n'a jamais été nommée.

#### J-07 — Aucune opération ne déclare le 500 `INTERNAL_ERROR`
- **gravité** majeur ; **emplacement** `docs/api/components/common.yaml:616-619` (« 5xx — composant indisponible… ou erreur inattendue, suivie par son `correlation_id` »), `:349-357` (`correlation_id` : « Le front l'affiche comme référence d'une erreur inattendue ») ; `grep "'500'" paths/*.yaml` : aucune ; aucun `default:` ; **exigence** WF-ARC-0060 (« toute erreur qu'un client peut rencontrer y figurent »), WF-OBS-0020.
- **Constat.** Le client engendré (openapi-fetch) ne type que les statuts déclarés : un 500 arrive en `unknown`, et le front ne peut pas lire `correlation_id` de façon typée pour l'afficher, ce que `Problem` promet. DECISIONS l. 8077 fait pourtant du 500 `INTERNAL_ERROR` une réponse définie du service. Après le gel, ajouter un statut à 163 opérations est une modification du contrat.
- **Proposition.** Une réponse partagée `InternalError` (`responses.yaml`) et une règle `redocly` « toute opération déclare `500` », ou un `default: { $ref: …#/InternalError }` par opération ; un exemple avec `correlation_id`.
- **DECISIONS.md** : l. 8077 (US-0640/L2) nomme le 500 `INTERNAL_ERROR` comme comportement du service ; aucune décision ne l'écarte du contrat.

#### J-08 — `include_inactive` : 403 déclaré sur trois listes du référentiel, tu sur les trois autres
- **gravité** majeur ; **emplacement** `docs/api/paths/reference.yaml:164` (`listOrgNodes`), `:830` (`listCalendars`), `:1148` (`listCostTypes`) — paramètre `IncludeInactive`, aucun `403`, descriptions muettes — contre `:425` et `:521` (`listResourceRoles` : « `include_inactive` et `is_active` faux… l'un et l'autre sont refusés par 403 »), `:1372`/`:1421` (`listCostCategories`), `:1625`/`:1686` (`getHourlyRateGrid`) ; `docs/api/components/parameters.yaml:44-54` (`IsActive` : « lus sous la permission qu'`include_inactive` exige… `include_inactive` reste refusé sans sa permission ») ; **exigence** WF-REF-0150, WF-ADM-0100.
- **Constat.** Le paramètre partagé dit la règle pour toutes les listes ; trois opérations ne déclarent pas le refus qu'elle implique. Soit la permission des nœuds, des calendriers et des natures n'existe pas (alors la description du paramètre partagé est fausse pour elles), soit le 403 manque. Un GET qui rend un 403 non déclaré fait échouer la vérification des réponses (WF-ARC-0060).
- **Proposition.** Déclarer `'403': Forbidden` sur `listOrgNodes`, `listCalendars`, `listCostTypes`, et dire dans leur description la permission qu'`include_inactive` exige (`resource_settings.read` ? `cost_settings.read` ?), comme `listResourceRoles` le fait.
- **DECISIONS.md** : l. 437-438 (US-0250/L1) : « `include_inactive` sans elle est refusé par 403 », règle générale ; l. 2819-2821 (EP-02/L42a) la répète pour « les cinq listes et la grille ». La décision couvre les six ; le contrat n'en tient que trois.

#### J-09 — `createSubproject` sans 404
- **gravité** majeur ; **emplacement** `docs/api/paths/projects.yaml:542-600` (`POST /projects/{project_id}/subprojects` : `201, 400, 401, 403, 409, 422, 503`) ; **exigence** WF-ADM-0110 (« L'interface présente le même écran pour un objet inexistant et pour un objet dont la consultation n'est pas permise »).
- **Constat.** Les 123 autres opérations sur un chemin paramétré déclarent `404` ; `createTimeline`, `createRevision`, `createRisk`, `openImport` le déclarent pour le même `{project_id}`. Un projet invisible ne peut recevoir qu'un 404, non déclaré ici.
- **Proposition.** `'404': { $ref: ../components/responses.yaml#/NotFound }`.
- **DECISIONS.md** : aucune décision.

#### J-10 — `fields` : le seul paramètre de requête refusé par 400
- **gravité** majeur ; **emplacement** `docs/api/components/parameters.yaml:89-101` (`NodeFields` : « une propriété inconnue est refusée (400) »), `docs/api/paths/revisions.yaml:766` (`listNodes`, `'400': BadRequest`), `:404` (`compareRevisions`) ; **exigence** WF-ARC-0110, WF-IHM-0130 ; README l. 49-50 et 56 (bornes, périodes : 422 sur `/query/<nom>` ; 400 réservé au corps illisible).
- **ce que dit le contrat** : `Scope` (`parameters.yaml:368-376`) refuse un sous-projet inconnu par « 422 `VALIDATION_FAILED`, `fields[]` désignant `/query/scope` » ; `FieldProblem.pointer` (`common.yaml:628-630`) prévoit « un paramètre de requête, sous `/query` suivi de son nom » ; `BadRequest` est « Requête mal formée » (`MALFORMED_REQUEST`), un code sans `fields`.
- **Constat.** Deux lectures (`listNodes`, `compareRevisions`) sont les seules GET sans corps à déclarer un 400, pour un paramètre que l'utilisateur ne saisit pas mais que le front compose : une faute du front est un 422 `/query/fields` par `VALUE_REQUIRED`/`FIELD_NOT_ACCEPTED` comme partout ailleurs. Changer le statut après le gel est incompatible.
- **Proposition.** `NodeFields` : « une propriété inconnue est refusée par 422 `VALIDATION_FAILED`, `fields[]` désignant `/query/fields` par `FIELD_NOT_ACCEPTED` » ; retirer le `400` des deux GET.
- **DECISIONS.md** : l. 5789-5794 (EP-03, #799) : « Le service refuse un paramètre de requête hors de son schéma par 422 `VALIDATION_FAILED`, sur toute opération qui en a » ; l. 866-872 : un refus par champ « plutôt que `MALFORMED_REQUEST` (400) : … l'écran doit dire lequel corriger, ce que `fields` porte et que le 400 du catalogue ne porte pas ». Le 400 de `fields` (EP-02/L4, l. 231-240) est antérieur à ces deux décisions et les contredit.

#### J-11 — `CommandCondition` : cinq valeurs que la description ne dit pas, trois que rien n'emploie
- **gravité** majeur ; **emplacement** `docs/api/components/schemas/projects.yaml:296` (`project_in_pricing`), `:297` (`project_code_set`), `:300` (`at_least_one_estimate_line`), `:301` (`no_current_revision`), `:312` (`hourly_rates_set`) ; **exigence** WF-IHM-0090 (« Tout refus nomme la condition manquante et… ce qu'il faut faire pour la satisfaire »), WF-CYC-0050.
- **ce que dit le contrat** : la description de `CommandCondition` (l. 95-290) explique chaque condition… sauf ces cinq. `project_in_pricing` et `no_current_revision` sont pourtant rendues par les exemples (`project.json` : `lose` → `[project_in_pricing]`, `create_revision` → `[no_current_revision]`, 9 et 7 fixtures). `project_code_set`, `at_least_one_estimate_line`, `hourly_rates_set` : zéro mention hors de l'énumération, zéro exemple ; `NextState.missing_conditions` (`next_state_pricing.json`) ne nomme que `reference_revision_designated` pour un déclencheur `reference_designated_and_code_set`.
- **Constat.** Le front rend chaque condition « dans la langue du lecteur » : une condition sans définition n'a pas de phrase sûre ; une condition morte est un texte à écrire pour rien, et une énumération figée. `project_code_set` a pourtant un emploi évident (le passage En cours exige le code, WF-CYC-0050) que `getProjectNextState` ne rend pas — s'il le rend, il faut le dire ; sinon, retirer les trois.
- **Proposition.** Compléter la description pour `project_in_pricing` (« manque à `lose` hors de l'état Chiffrage ») et `no_current_revision` (« manque à `create_revision` tant qu'une révision en cours existe ») ; pour `project_code_set` : `getProjectNextState` la nomme quand le projet en chiffrage n'a pas de code (exemple) ; retirer `at_least_one_estimate_line` et `hourly_rates_set` ou dire quelle commande les nomme.
- **DECISIONS.md** : l. 4114 (EP-14/L42i) : « `project_in_pricing`, qui existe mais exclut Créé » — mention en passant, pas de définition ; aucune décision pour les quatre autres.

#### J-12 — Tables plates sans pages : `listAccessRoles`, `listRiskReviews`
- **gravité** mineur ; **emplacement** `docs/api/paths/access.yaml:620-636` (`listAccessRoles` : « Une table plate : chaque colonne se trie… et se filtre », `search`, bornes, colonnes d'audit, `sort_by`/`sort_order`, mais ni `Limit`, ni `Offset`, ni `meta`) ; `docs/api/paths/risks.yaml:280-291` (`listRiskReviews` : ni pages, ni tri) ; **exigence** WF-IHM-0060 (« Une table plate se lit par pages, dont l'utilisateur choisit le nombre de lignes… »), §4.6.2 (revues mensuelles sur 15 ans : jusqu'à 180 réexamens par risque).
- **Constat.** `listSubprojects` (`projects.yaml:496`) et `listContributors` (`:730`) justifient leur absence de pages par le §4.6.2 ; `listAccessRoles` a tous les attributs d'une table plate paginée (`listUsers` l'est) sans pages ni justification ; `listRiskReviews` peut atteindre 180 lignes. Les volumes restent petits : mineur, mais la forme de la réponse (`items` nus contre `items`+`meta`) est ce qu'on ne change pas après le gel.
- **Proposition.** Soit `Limit`/`Offset`/`meta` sur `listAccessRoles` (tables uniformes, DECISIONS l. 2796-2801), soit une phrase « Sans pagination : … » comme les deux listes du projet ; même choix pour `listRiskReviews`.
- **DECISIONS.md** : l. 2789-2805 (EP-02/L42a) : « l'auteur veut des tables uniformes » ; l. 3259 (EP-02/L42f, filtres des rôles d'habilitation) ne parle pas de pagination.

#### J-13 — `createTimeline.label` sans `pattern: '\S'`
- **gravité** mineur ; **emplacement** `docs/api/paths/projects.yaml:917` (`label: { type: string, minLength: 1, maxLength: 200 }`) ; **exigence** WF-ARC-0110, README l. 57 : « Un libellé, un nom ou un code reçu porte au moins un caractère qui n'est pas un blanc (`pattern: '\S'`) ».
- **Constat.** Relevé sur les 1 291 propriétés : tout autre libellé, nom ou code d'écriture porte le motif (`ProjectCreate.label`, `StructureCreate.label`, `ProjectClient`…), ou un motif plus fort (`SubprojectWrite.code`) ; `createTimeline` est le seul contre-exemple, et le 422 déclaré ne prévoit que « vide ou trop long ».
- **Proposition.** `label: { type: string, minLength: 1, pattern: '\S', maxLength: 200 }`, et le 422 dit « fait seulement de blancs, `VALIDATION_FAILED` ».
- **DECISIONS.md** : l. 5766 (« Aucun libellé fait seulement de blancs », EP-03, #837) pose la règle ; `createTimeline` lui a échappé.

#### J-14 — Le pointeur `/body` n'est pas une forme de `FieldProblem.pointer`
- **gravité** mineur ; **emplacement** `docs/api/components/common.yaml:625-634` ; `docs/api/paths/exchanges.yaml:104,135` (`uploadChunk`), `fixtures/api/chunked_upload_part_size_mismatch.json` ; **exigence** WF-ARC-0110.
- **Constat.** La description de `pointer` énumère trois formes (corps RFC 6901, `/query/<nom>`, `/path/<nom>`) et affirme qu'« un pointeur ne désigne ainsi qu'un seul champ ». `/body` (un corps binaire entier) est une quatrième forme, décidée mais non décrite : le seul écart que le contrôle des pointeurs des 91 exemples de refus relève.
- **Proposition.** Ajouter à `pointer` : « un corps qui n'est pas un objet — un fichier déposé —, `/body` ».
- **DECISIONS.md** : l. 3847 (EP-14/L42h) décide `/body` ; la description générale n'a pas suivi.

#### J-15 — `listActualCosts` : `from`, `to`, `in_tracked_scope` sans description
- **gravité** mineur ; **emplacement** `docs/api/paths/costs.yaml:19-26` ; **exigence** WF-IHM-0130, README l. 50 (« Une période se filtre par `from` et `to`, le début inclus ; … une date de planning sa fin incluse »).
- **Constat.** Les sept autres périodes du contrat (`listProjects`, `listBackups`, `listAuditEvents`, `PortfolioFrom/To`, `CreatedAt*`, `UpdatedAt*`) disent la colonne filtrée et la borne exclue ou incluse ; ici rien ne dit que la colonne est `document_date` ni que `to` est inclus.
- **Proposition.** Une description par paramètre, sur le modèle de `PortfolioFrom`/`PortfolioTo`.
- **DECISIONS.md** : l. 864-868 (US-0230/L3) décrit le refus de la période, pas la colonne ni l'inclusion.

#### J-16 — `getMetrics` : un `404` partagé sans cause, pas de `503`, pas d'exception déclarée
- **gravité** mineur ; **emplacement** `docs/api/paths/system.yaml:83-98` ; `docs/api/.redocly.lint-ignore.yaml` (n'excepte que `/health`, `/health/ready`, `/installation`) ; **exigence** WF-OBS-0010, WF-ARC-0060 ; spec l. 3710 (TFX-09 : « HTTP, point /metrics … Réseau interne au cluster »).
- **Constat.** Le seul refus déclaré renvoie à `NotFound` (« Objet inexistant, ou invisible faute de la permission de consultation »), qui n'a pas de sens pour une exposition sans objet ni session ; rien ne dit s'il signifie « exposition désactivée » ou « hors du réseau interne ». Les trois autres opérations publiques déclarent `503`.
- **Proposition.** Dire la cause du 404 dans la description (ou le retirer et déclarer l'exception dans `.redocly.lint-ignore.yaml` avec sa raison, comme les sondes) ; `503` si la collecte peut attendre un composant.
- **DECISIONS.md** : aucune décision (`grep getMetrics|/metrics` : rien).

#### J-17 — Treize codes déclarés sans aucun exemple
- **gravité** mineur ; **emplacement** `docs/api/components/responses.yaml:3-7` (`BadRequest`, `MALFORMED_REQUEST`), `:66-70` (`PayloadTooLarge`, `FILE_TOO_LARGE`, 7 opérations), `:9-29` (`Unauthorized` : exemples de `SESSION_EXPIRED` et `SESSION_REVOKED` seuls ; `SESSION_REQUIRED`, `ACCOUNT_DEACTIVATED`, `ACCOUNT_NOT_ADMITTED` sans) ; `common.yaml:464-465` (`NUMBER_INVALID`, `DATE_INVALID` : la convention de toute borne et de toute période, 8 mentions chacun, 0 exemple), `:473` (`UNKNOWN_CALENDAR`), `:586` (`FIELD_NOT_ACCEPTED`, 7 mentions), `:419` (`ACCESS_ROLE_IN_USE`, `deleteAccessRole` 409), `:394` (`NOT_CONTRIBUTOR`), `:474` (`UNKNOWN_RESOURCE_ROLE`, une occurrence dans `import_analysed.json`, aucune description au catalogue) ; **exigence** WF-QUA-0020 (les exemples du contrat sont les jeux du faux back).
- **Constat.** Le faux back ne sert que ce que les exemples portent : treize phrases du front n'ont rien à rejouer. `NUMBER_INVALID`/`DATE_INVALID` sont de plus la forme que le README impose à toutes les listes bornées.
- **Proposition.** Un exemple par code sur une opération témoin (les réponses partagées peuvent porter les exemples de `MALFORMED_REQUEST`, `FILE_TOO_LARGE`, `SESSION_REQUIRED`, `ACCOUNT_*`).
- **DECISIONS.md** : l. 2841 (EP-02/L42a) annonce `NUMBER_INVALID` avec les exemples `resource_roles_bounds_inverted`, `calendars_bounds_inverted` — ces fixtures portent `VALUE_OUT_OF_RANGE` ; l. 7924 (US-0640/L1, « Les exemples manquants ») ne couvre pas ces codes.

#### J-18 — Trois conditions sans exemple
- **gravité** mineur ; **emplacement** `docs/api/components/schemas/projects.yaml:292` (`is_contributor`), `:293` (`is_project_manager`), `:317` (`task_not_milestone`) ; **exigence** WF-IHM-0090.
- **Constat.** Décrites, mais aucune fixture ne les porte, ni dans `available_commands`, ni dans un `missing_condition` : le front n'a pas de projet témoin où un simple contributeur voit `update` indisponible, ni de carte Kanban qui refuse `started` à un jalon.
- **Proposition.** Une variante de `project.json` lue par un contributeur non chef de projet ; un 409 de `setTaskProgress` pour un jalon envoyé à `started`.
- **DECISIONS.md** : l. 7471-7485 (EP-15/US-0540) ajoute `task_not_milestone` sans exemple ; rien pour les deux qualités.

#### J-19 — `StructureCreate.kind` : la seule énumération sans `type`
- **gravité** mineur ; **emplacement** `docs/api/components/schemas/revisions.yaml:363-364` (`kind: allOf: [{ $ref: '#/StructureKind' }], enum: [amendment, risk]`).
- **Constat.** Relevé sur 324 schémas : c'est l'unique `enum` posé à côté d'un `allOf` sans `type`. Valide en JSON Schema 2020-12, mais openapi-typescript et datamodel-codegen ne rendent pas tous deux un sous-ensemble d'une énumération référencée de la même façon (union littérale d'un côté, `StructureKind` entier de l'autre) — la restriction peut se perdre côté Pydantic.
- **Proposition.** Un type nommé `StructureCreateKind: { type: string, enum: [amendment, risk] }`, référencé par `kind`.
- **DECISIONS.md** : aucune.

#### J-20 — `Limit`, `Offset`, `Year` sans description
- **gravité** mineur ; **emplacement** `docs/api/components/parameters.yaml:3-11`, `docs/api/components/common.yaml:87-90` ; **exigence** WF-IHM-0060 (« 10, 25, 50 et 100 — 50 par défaut »).
- **Constat.** Les seuls paramètres et type partagés muets ; `Limit` (`maximum: 500`, `default: 50`) ne cite pas la règle des pages ni pourquoi 500 (les listes de choix lues « par la plus grande page », DECISIONS l. 2802-2803).
- **Proposition.** Trois phrases.
- **DECISIONS.md** : l. 2802-2803 donne la raison du 500 ; elle n'est pas au contrat.

#### J-21 — `risk_matrix_no_basis.json`, exemple orphelin
- **gravité** mineur ; **emplacement** `fixtures/api/risk_matrix_no_basis.json` (engendrée par `tools/src/wftools/mockhistory.py:737`), `docs/api/paths/risks.yaml:474` (`getProjectRiskMatrix` : un seul exemple, `witness`) ; **exigence** WF-RIS-0040.
- **Constat.** La seule fixture de `fixtures/api/` qu'aucun fichier du contrat ne référence ; DECISIONS l. 7525 la présente comme « Exemple : `risk_matrix_no_basis`, variante contrefactuelle ». Le faux back ne la sert donc pas.
- **Proposition.** `no_basis: { $ref: ../../../fixtures/api/risk_matrix_no_basis.json }` sous `getProjectRiskMatrix` (hors de la part US-0700 sur `RiskMatrix.cells`).
- **DECISIONS.md** : l. 7518-7525 (EP-15/US-0550) la décide comme exemple.

### Ce qui est juste

- Types élémentaires : aucun `nullable` (OAS 3.0) ; 234 nuls tous écrits `anyOf: [{…}, { type: 'null' }]`, aucun `type: [x, 'null']` ; les seuls `format` sont `uuid`, `date`, `date-time` (une fois chacun, dans `Uuid`/`PlanningDate`/`Timestamp`), `email` ×3, `uri` ×1, `binary` ×10 — toute date, tout horodatage, tout identifiant passe par `$ref` ; `Decimal` et ses dérivés (`Money` à deux décimales par `allOf`+`pattern`) sont les seules chaînes numériques hors `month`/`quarter`/`at_time` à motif propre ; 1 291 propriétés et tous les paramètres en `snake_case` ; `operationId` uniques et `camelCase`.
- Réponses : les règles `redocly` tiennent sur les 163 opérations (401+503 sur toute opération gardée, 400+422 sur toute opération à corps) ; toute écriture PATCH/PUT dont le corps porte `lock_version` déclare `412`, et `deleteNode` le porte en requête ; toute création à clé unique (`createUser`, nœuds, rôles, calendriers, natures, catégories, projets, sous-projets, structures, `markRevision`) déclare `409` et nomme `ALREADY_EXISTS` ; les quatre opérations publiques disent `security: []`.
- Listes : `search` partout `minLength 1`/`maxLength 200` et comparé comme le README le dit ; `sort_by` toujours accompagné de `sort_order` (14 listes), ses colonnes énumérées (ou `rate.<année>`/`passthrough.<colonne>` motivés) ; `_min`/`_max` sur chaque colonne de nombres filtrée (level, monthly_hours, headcount, rate, size_bytes, holder_count) ; `from`/`to` typés par la colonne (Timestamp exclu, PlanningDate inclus) ; tout paramètre de tableau déclare `explode: false` ; les 15 listes paginées rendent `meta` ; `listNodes`, `compareRevisions`, `listOrgNodes`, `listAuditFacets` sans pages par décision écrite.
- `openapi.yaml` : 18 étiquettes toutes déclarées et toutes employées, une par opération ; les 127 chemins des `paths/*.yaml` tous renvoyés et groupés par fichier ; `servers` `/api/v1` ; `bearer` JWT ; la description de la racine reste vraie (WF-ARC-0020 cité à propos) ; `info.version` relève d'US-0640/L5.
- Fixtures : 618 références, 597 fichiers distincts, tous présents (18 dans `fixtures/api/volume/`) ; aucun exemple inline de plus de 300 caractères ; 91 exemples de refus dont tous les `fields[].pointer` désignent une propriété du schéma d'entrée ou un paramètre de l'opération, à la seule exception de `/body` (J-14) ; chaque `status` d'exemple est celui de sa réponse ; `ProblemParams` typé conforme à DECISIONS US-0640/L2 et aux paramètres que les exemples portent.

### Doutes

- **Suppressions sans `lock_version`.** `deleteNode` exige le compteur (`?lock_version`, 412, décision #1210) ; `deleteRisk`, `deleteSubproject`, `abandonRevision`, `deleteAccessRole`, `deleteTimeline`, `abandonImport` n'en portent pas. Un risque se supprime dans la révision en cours et s'annule (WF-IHM-0110, `risks.yaml:252`) : le même argument que pour le nœud s'applique ; mais la spec ne l'exige pas mot pour mot, et aucune décision ne tranche. De même `designateReferenceRevision` et `exitProject` (`confirmed: true`, sans compteur du projet) et `retainBackup`/`setActualCostTrackedScope` (leurs objets n'ont pas de `lock_version` : cohérent).
- **`listStartableTasks`** rend jusqu'à mille tâches sans pages ni filtre : un tableau Kanban se lit entier, mais le §4.6.2 ne le mesure pas (la seconde ne vaut que pour les grilles) — à mesurer plutôt qu'à trancher ici.
- **`Forbidden` et `NOT_PROJECT_MANAGER`.** Les opérations réservées aux chefs de projet (`updateProject`, `setContributors`, `exitProject`, `markRevision`, `designateReferenceRevision`, sous-projets) déclarent le `Forbidden` partagé, qui ne nomme pas le code : si la qualité manque, est-ce `PERMISSION_MISSING` avec `missing_condition` à `is_project_manager`, ou `NOT_PROJECT_MANAGER` ? Le README (« 403 lorsque c'est l'écriture ou la qualité de contributeur ») ne dit pas lequel ; rangé sous J-03/J-18, à trancher par l'auteur.
- **Le `PaginationMeta.limit` à 500** contre les pages de WF-IHM-0060 (10 à 100) : la décision l. 2802 (listes de choix lues par la plus grande page) l'explique ; reste à savoir si le front borne lui-même à 100 l'offre de l'utilisateur — hors contrat.

## Annexe K — Delta de la spécification — administration, interfaces, sécurité, exploitation


Lu : `spec-diff-group1.md` (42 exigences), `docs/api/README.md` (Conventions), en entier
`docs/api/paths/system.yaml`, `me.yaml`, `audit.yaml`, `access.yaml`, `platform.yaml`, `costs.yaml`,
`exchanges.yaml`, et les schémas `access.yaml`, `platform.yaml`, `audit.yaml`, `exchanges.yaml`,
`costs.yaml`, plus `common.yaml` (`ErrorCode`, `BackgroundTaskRef`), `reference.yaml`
(`Installation`, `ReferenceSettings`, `NodeColumn`, `CostStructure`) ; les passages concernés de
`docs/spec/waterfall-spec.md` (WF-ADM-0190, WF-ADM-0070, WF-REF-0190, WF-PLA-0160, WF-PLA-0020,
WF-DAT-0120, §4.4.4, §4.4.5, §4.5.1) ; `docs/api/DECISIONS.md` (grep par exigence et par mot-clé,
sections EP-02/L29, L42, L42d, L42s, EP-03, EP-16) ; `docs/api/INVENTORY.md` ; la section
« Constats reçus » et la conception d'`EP-16-maquette-durcissement.md` ; 9 fixtures ouvertes
(`access_roles`, `permissions`, `me_manager`, `reference_settings`, `backup_schedule`,
`backup_schedule_disabled`, `system_status`, `audit_events`, `file_upload` via le schéma) ;
`tools/src/wftools/mockaudit.py` et `mocklists.py` pour l'origine des fixtures des rôles.

Les changements datent des commits `4fc7546f`, `7dc06e9d` (2026-10-09), `b18a8883` (2026-10-10) et
`55dba1d0`/`149470aa` (2026-10-18/22) ; les décisions citées comme antérieures sont celles d'EP-02
(avant le 2026-10-07).

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| K-01 | majeur | `docs/api/paths/access.yaml:535-594` (`startIdentitySync`, `getLatestIdentitySync`) | La périodicité de la lecture des comptes, « choisie par un utilisateur habilité, quotidienne par défaut, comme celle des sauvegardes », n'a aucune opération ni aucun schéma | WF-ADM-0070 |
| K-02 | majeur | `docs/api/components/schemas/platform.yaml:3-36` (`SystemStatus`) | L'écran d'état doit présenter « les valeurs en vigueur des paramètres d'exploitation (§4.5.1) », dont la durée de validité du cache ; le schéma ne les porte pas | WF-ADM-0130, WF-OBS-0030 |
| K-03 | majeur | `docs/api/components/schemas/audit.yaml:115-126` (`AuditProject`), `paths/audit.yaml:26-31` | « Chaque inscription mène au projet concerné lorsque l'utilisateur peut le consulter » : rien ne dit au front si le lien s'ouvre, quand le portefeuille porte `can_open` pour la même règle | WF-ADM-0190 |
| K-04 | majeur | `docs/api/components/schemas/audit.yaml:3-36` (`AuditAction.amendment_merge`) | La spec dit « la fusion d'un différentiel (WF-REV-0050) », la permission et la tâche de fond s'appellent `structure_merge` ; l'action d'audit garde « la contractualisation d'un avenant », `amendment_merge` | WF-SEC-0030 |
| K-05 | majeur | `docs/api/components/schemas/exchanges.yaml:162-258, 330-358, 422-441` (`ImportReport`, `ImportSignal`, `ImportDifference`) | Le compte rendu d'un import MS Project ne peut présenter ni la date de début de planning qui change, ni la récapitulative manuelle importée en automatique « avec l'écart de dates » | WF-INTF-0040 |
| K-06 | majeur | `docs/api/components/schemas/exchanges.yaml:213-223, 263-272, 429-438` (`ImportReport.ignored`, `ImportIgnoredKind`, `ImportDifference.change`) | Les lignes de provision à l'import du devis et du reste à engager — ligne du fichier ignorée, ligne absente conservée, « le compte rendu signale les unes et les autres » — n'ont aucune place : `ignored` est dit vide pour un devis, `kept` ne vaut que pour une tâche démarrée ou terminée | WF-INTF-0100, WF-INTF-0120 |
| K-07 | majeur | `docs/api/paths/system.yaml:212-252` (`getBackgroundTaskResult`), `paths/exchanges.yaml:455-456`, `schemas/exchanges.yaml:543-546` | « Le fichier est engendré à la demande et n'est pas stocké » quand la spec range désormais « les fichiers exportés en attente de téléchargement » sur le stockage objet, supprimés au premier téléchargement complet ou après vingt-quatre heures ; le 409 déclaré n'est pas décrit | WF-ARC-0040 (WF-DAT-0120) |
| K-08 | mineur | `docs/api/components/schemas/exchanges.yaml:360-401` (`ImportRejection`) | « Une ligne nouvelle sous une tâche terminée est rejetée au compte rendu » : aucun motif nommé ; `TASK_COMPLETED` existe au catalogue pour la réestimation | WF-INTF-0100, WF-INTF-0120 |
| K-09 | mineur | `fixtures/api/access_roles.json` (rôle « Manager »), `fixtures/api/me_manager.json` | Le rôle prédéfini « manager » paramètre « les bornes de la matrice de risques, les seuils d'alerte des indices et le délai maximal entre deux revues » ; la fixture ne lui donne ni `risk_settings.write` ni `indicator_settings.write` | WF-INTF-0020 |
| K-10 | mineur | `docs/api/components/schemas/platform.yaml:7-8` (`SystemStatus`), `paths/system.yaml:89-91` (`getMetrics`) | « Il ne présente que des valeurs issues des métriques » : la spec révisée dit que les dates et résultats de la dernière lecture, de la dernière sauvegarde et du dernier test de restauration sont lus dans la base | WF-OBS-0010, WF-ADM-0130 |
| K-11 | mineur | `docs/api/paths/system.yaml:83-98` (`getMetrics`) | Le point de métriques est « servi en HTTP » et « joignable du seul réseau interne au cluster » (TFX-09) ; le contrat le place sous `/api/v1` avec un 404 sans explication | WF-SEC-0010 |
| K-12 | mineur | `docs/api/components/schemas/platform.yaml:228-267` (`BackupSchedule`), `paths/platform.yaml:297-318` | « La planification livrée est quotidienne (WF-EXP-0050) » : rien ne dit la planification livrée ni ce que `is_enabled` vaut sur une installation neuve | WF-ADM-0170 |
| K-13 | mineur | `docs/api/components/schemas/access.yaml:296` (`DisplayPreferences.highlight_tasks_added_after_reference`) | La préférence distingue désormais aussi « les lignes dont le montant budgété est nul (WF-RAE-0040) » ; le champ, sans description, ne nomme que les tâches | WF-ADM-0040 |
| K-14 | mineur | `docs/api/paths/exchanges.yaml:10-11` (`uploadFile`), `schemas/exchanges.yaml:9-13` (`FileUpload`) | Le fichier est supprimé aussi quand l'import est « refusé à l'application » ; `applyImport` le dit, le dépôt et son schéma ne le disent pas | WF-ARC-0100 |

#### K-01 — La périodicité de la lecture des comptes n'a pas d'opération
- **gravité** : majeur ; **emplacement** : `docs/api/paths/access.yaml:535-594` (`startIdentitySync`, `getLatestIdentitySync`), `docs/api/components/schemas/platform.yaml:433-489` (`IdentitySyncReport`) ; **exigence** : WF-ADM-0070, corps `{+selon une périodicité choisie par un utilisateur habilité, quotidienne par défaut, comme celle des sauvegardes (WF-ADM-0170)+}`, Vérif `{+Une personne ajoutée à l'annuaire a un compte dans Waterfall au terme de la périodicité choisie, sans intervention.+}` ; **ce que dit le contrat** : `startIdentitySync` lance une lecture « à la demande » ; `getLatestIdentitySync` parle d'une lecture « demandée ou planifiée » (`access.yaml:575`) et `IdentitySyncReport` de « la lecture que la plateforme planifie » (`platform.yaml:438`), sans qu'aucune opération ne lise ni n'écrive cette planification.
- **Constat.** La spec fait de la périodicité un réglage de l'utilisateur habilité, sur le modèle de la planification des sauvegardes, qui a `getBackupSchedule`/`setBackupSchedule`. Le contrat ne porte que la lecture manuelle : l'écran ne peut ni afficher ni régler la périodicité, et la Vérif (« au terme de la périodicité choisie ») n'est pas vérifiable sur le contrat. Une opération nouvelle après le gel est un changement de contrat.
- **Proposition.** Sur le modèle de `BackupSchedule`, sous `users.write` (lecture sous `users.read`) :
  ```yaml
  /identity-sync-schedule:
    get: { operationId: getIdentitySyncSchedule }
    put: { operationId: setIdentitySyncSchedule }
  IdentitySyncSchedule:
    type: object
    required: [is_enabled, frequency, at_time, lock_version]
    properties:
      is_enabled: { type: boolean }
      frequency: { type: string, enum: [daily, weekly] }
      at_time: { type: string, pattern: '^([01]\d|2[0-3]):[0-5]\d$' }   # UTC, comme BackupSchedule
      weekday: { anyOf: [{ type: integer, minimum: 1, maximum: 7 }, { type: 'null' }] }
      lock_version: { $ref: ../common.yaml#/LockVersion }
  ```
  avec, en description, la valeur livrée (activée, quotidienne) et l'exemple `identity_sync_schedule`. Ou, si l'auteur préfère un réglage d'exploitation, une décision qui le dise et une mention sur `startIdentitySync`.
- **DECISIONS.md** : aucune décision ; l'EPIC EP-16 (« Les modifications du contrat ») n'en parle pas non plus.

#### K-02 — L'écran d'état ne porte pas les paramètres d'exploitation
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/platform.yaml:3-36` (`SystemStatus`), `paths/system.yaml:100-123` (`getSystemStatus`) ; **exigence** : WF-ADM-0130, corps `{+; la version de chaque composant employé (WF-CMP-0020) ; les valeurs en vigueur des paramètres d'exploitation (§4.5.1)+}`, Vérif `{+L'écran présente la durée de validité du cache en vigueur.+}` ; §4.5.1 : « l'écran d'état en présente les valeurs en vigueur (WF-ADM-0130) » ; WF-OBS-0030 : « Les trois seuils sont des paramètres d'exploitation, livrés à quinze minutes, 85 % et 5 % sur cinq minutes » ; **ce que dit le contrat** : `SystemStatus` porte `version`, `components` (avec `version` par composant : porté), `storage`, `last_identity_sync`, `last_backup`, `last_backup_copy`, `last_restore_test`, `alerts` ; aucun paramètre d'exploitation.
- **Constat.** La spec nomme au moins quatre paramètres d'exploitation (durée de validité du cache, livrée à dix minutes, §4.4.5 ; rétention des tâches de fond, trente jours, §4.4.4 ; les trois seuils d'alerte de WF-OBS-0030 ; la taille que §4.4.1 livre à 512 Ko) et veut leurs valeurs en vigueur sur l'écran d'état. Rien dans le contrat ne les transporte ; le front ne peut pas les présenter sans un attribut nouveau, donc un changement de contrat après le gel.
- **Proposition.** Un attribut exigé de `SystemStatus`, en codes et valeurs typées, jamais en phrase (WF-ARC-0110) :
  ```yaml
  operating_parameters:
    type: array
    description: Les valeurs en vigueur des paramètres d'exploitation (§4.5.1), dans l'ordre de l'énumération.
    items:
      type: object
      required: [code, value, unit]
      properties:
        code: { type: string, enum: [cache_ttl, task_result_retention, task_queue_age_threshold, storage_usage_threshold, error_rate_threshold, error_rate_window] }
        value: { type: string }     # décimal en chaîne, convention WF-DAT-0100
        unit: { type: string, enum: [seconds, days, ratio] }
  ```
  avec un exemple dans `system_status.json` (10 minutes, 30 jours, 15 minutes, 0.85, 0.05, 5 minutes). La liste exacte des codes est à trancher avec l'auteur (§4.5.1 dit « que le document donne là où il la cite »).
- **DECISIONS.md** : aucune décision sur WF-ADM-0130 (aucune occurrence) ; les seuils d'alerte ne sont cités qu'à propos des alertes elles-mêmes (EP-02/L42, #488).

#### K-03 — Le journal ne dit pas si l'inscription mène au projet
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/audit.yaml:115-126` (`AuditProject`), `audit.yaml:162-164` (`AuditEvent.project`), `docs/api/paths/audit.yaml:26-31` ; **exigence** : WF-ADM-0190 (nouvelle) : « Chaque inscription mène au projet concerné lorsque l'utilisateur peut le consulter (WF-ADM-0110), et le nomme par son libellé et son code sinon » ; Vérif : « Une inscription sur un projet que le lecteur ne peut pas consulter nomme ce projet sans l'ouvrir » ; **ce que dit le contrat** : `listAuditEvents` : « l'inscription ne mène qu'à un projet qu'il peut ouvrir (WF-ADM-0110), et qu'à un objet qu'il peut consulter » ; `AuditProject` : `project_id`, `code`, `label`, rien de plus.
- **Constat.** La règle est énoncée dans la description, mais aucune donnée ne la porte : le front devrait déduire l'ouvrabilité des permissions de la session et de la liste des contributeurs, ce que la décision #389 (`can_open` du portefeuille) a écarté explicitement : « pour que le front retire le lien sans recopier la règle. Écarté : laisser le front le déduire des permissions de la session, qui ne connaît pas les contributeurs ». Le même concept est donc porté par `PortfolioProjectRow.can_open`, `PortfolioRisks.heaviest[].can_open`, `RiskMatrix` (points du portefeuille), et absent du journal, qui est pourtant la vue où le lecteur (un auditeur sans `all_projects_read`) a le plus souvent des projets qu'il ne peut pas ouvrir. C'est une incohérence entre familles sur un attribut, à régler avant le gel.
- **Proposition.** Sur `AuditEvent.project` (et non sur les facettes, où le projet n'est qu'un choix de filtre) :
  ```yaml
  AuditProject:
    required: [project_id, code, label]
    properties:
      can_open:
        type: boolean
        description: >-
          Vrai quand l'appelant peut ouvrir le projet aujourd'hui (WF-ADM-0110) ; faux sinon, et
          faux pour un projet qui n'existe plus (WF-ADM-0190). Exigé dans `AuditEvent.project`,
          absent dans `AuditFacets.projects`.
  ```
  (ou un schéma `AuditEventProject` dérivé, `can_open` exigé). Même question pour l'objet (« qu'à un objet qu'il peut consulter ») : `AuditObject.can_open`, ou dire que l'objet suit le projet. Exemples : `audit_events` (le témoin, ouvrable), `audit_events_project`, et le projet disparu de la Vérif de WF-ADM-0190.
- **DECISIONS.md** : #389 (EP-02/L29, « Les lignes du portefeuille disent si le projet s'ouvre ») ; EP-02/L42 et L42d (journal, facettes) ne parlent pas du lien ; aucune décision sur WF-ADM-0190.

#### K-04 — `amendment_merge` nomme encore la contractualisation d'un avenant
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/audit.yaml:3-36` (`AuditAction`), `audit.yaml:45-64` (`AuditObjectKind`, « le différentiel d'un avenant »), `audit.yaml:139-141` (`AuditEvent`) ; **exigence** : WF-SEC-0030, corps `la [-contractualisation-]{+fusion+} d'un [-avenant,-]{+différentiel (WF-REV-0050),+}` ; **ce que dit le contrat** : `amendment_merge` — « la contractualisation d'un avenant, qui fusionne son différentiel (`amendment_merge`, WF-REV-0050) » ; ailleurs, la permission (`PermissionCode.structure_merge`), la tâche de fond (`BackgroundTaskRef.kind: structure_merge`) et la commande (`RevisionCommand.merge_structure`) nomment la même action.
- **Constat.** La décision d'EP-02/L42 (antérieure au 2026-10-07) a choisi les actions « dans les mots du catalogue des permissions et des tâches de fond » et a pourtant nommé `amendment_merge` ; la décision d'EP-02/L29 (#384) a nommé la permission `structure_merge` « le nom que `BackgroundTaskRef.kind` donne déjà à la fusion ». La spec a depuis retiré le mot « avenant » de WF-SEC-0030 : le journal enregistre « la fusion d'un différentiel ». Le même concept porte deux noms dans le contrat (`structure_merge` / `amendment_merge`), et la description d'`AuditAction` cite une phrase que la spec n'a plus. Renommer une valeur d'énumération après le gel est un changement incompatible.
- **Proposition.** `AuditAction`: `amendment_merge` → `structure_merge` (même rang), description : « la fusion d'un différentiel (WF-REV-0050) » ; `AuditObjectKind` : « la structure différentielle fusionnée » ; `AuditEvent` : « la fusion d'un différentiel inscrit `structure_merge` sur sa structure, puis… ». Fixtures `audit_events*.json` et `tools/src/wftools/mockaudit.py` à régénérer (8 occurrences dans le bundle). À faire dans le même geste que l'ajout de `project_create` et `revision_abandon` (US-0640/L6, #1457), qui touche la même énumération.
- **DECISIONS.md** : EP-02/L42 « Les actions (`AuditAction`) suivent l'énumération de WF-SEC-0030 … `amendment_merge` — la contractualisation d'un avenant » (antérieure, contredite par la spec du 2026-10-09) ; EP-02/L29 #384 pour `structure_merge`.

#### K-05 — Le compte rendu MS Project : la date de début de planning et la récapitulative manuelle
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/exchanges.yaml:162-258` (`ImportReport`), `330-358` (`ImportSignal.code`, `const: NON_WORKING_DAY`), `422-441` (`ImportDifference.target`, `[task, estimate_line, link, actual_cost_line]`) ; `paths/exchanges.yaml:328-369` (`getImport`) ; **exigence** : WF-INTF-0040, corps `{+la date de début du projet du fichier devient la date de début de planning de la structure (WF-PLA-0020), et le compte rendu la présente lorsqu'elle diffère de celle en place+}` et `{+Une récapitulative en mode manuel dans le fichier est importée en mode automatique, et le compte rendu la signale avec l'écart de dates.+}` ; **ce que dit le contrat** : `ImportSignal.code` n'admet que `NON_WORKING_DAY` (« tant qu'aucun autre signalement n'existe ; un signalement nouveau élargit cette liste, par une modification du contrat ») ; `ImportDifference` ne vise que des nœuds et des liaisons ; `ImportDateMismatch.fields` ne nomme que `duration`, `start`, `finish`.
- **Constat.** Deux informations nouvelles du compte rendu n'ont pas de forme : (a) la date de début de planning que le fichier porte et qui remplace celle de la structure — elle n'est ni une tâche ni une liaison, donc hors de `differences`, `signals` et `date_mismatches` ; (b) la récapitulative manuelle importée en automatique, à signaler « avec l'écart de dates » — `signals` ne porte qu'un code, par construction du schéma (`const`). Les autres nouveautés de la même exigence sont portées (liaisons remplacées : `target: link` ; description lue dans les notes : colonne `description` ; rattachement conservé : `work_breakdown_label` ; rejet entier : `refusals`).
- **Proposition.** (a) Un champ exigé, nul quand rien ne change :
  ```yaml
  planning_start_change:
    anyOf:
      - type: object
        required: [current, imported]
        properties:
          current: { $ref: ../common.yaml#/PlanningDate }   # celle en place
          imported: { $ref: ../common.yaml#/PlanningDate }  # celle du fichier, appliquée
      - type: 'null'
  ```
  (b) élargir `ImportSignal.code` à `SUMMARY_TASK_DERIVED`, code déjà au catalogue pour une récapitulative dont les dates dérivent, avec `column: scheduling_mode` et, dans `params`, les dates du fichier et les dates recalculées (`start`, `finish`, `recalculated_start`, `recalculated_finish`) — ou l'inscrire aussi dans `date_mismatches`. Exemples : `import_planning_mismatch` à compléter.
- **DECISIONS.md** : #383 (EP-02/L29, « Le compte rendu d'import dit l'aller-retour »), US-0640/L2 (#1330, comptes rendus), #1271 (`signals`) : aucune ne traite ces deux points.

#### K-06 — Les lignes de provision à l'import du devis et du reste à engager
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/exchanges.yaml:213-223` (`ImportReport.ignored` : « Vide pour un devis ou un reste à engager, qui ne lisent que leurs colonnes »), `263-272` (`ImportIgnoredKind`), `429-438` (`ImportDifference.change`, `kept`) ; **exigence** : WF-INTF-0100, corps `{+Les lignes de provision des risques (WF-RIS-0010) figurent à l'export pour information et ne sont jamais modifiées par l'import : une ligne du fichier qui porte la lignée d'une ligne de provision est ignorée, une ligne sans identifiant dont la catégorie relève d'une nature de type provision pour risques est rejetée (WF-DEV-0020), et une ligne de provision absente du fichier est conservée ; le compte rendu signale les unes et les autres.+}` ; Vérif `{+Un fichier d'où une ligne de provision a été retirée laisse cette ligne en place+}` ; WF-INTF-0120 : `{+Les lignes de provision des risques ne sont ni mises à jour ni créées par l'import, selon la même règle que WF-INTF-0100.+}` ; **ce que dit le contrat** : le rejet d'une ligne nouvelle de catégorie provision est porté (`PROVISION_CATEGORY_RESERVED`, `ImportRejection`) ; rien pour la ligne du fichier qui porte la lignée d'une provision (ignorée), ni pour la provision absente du fichier (conservée) — `kept` est défini pour « une tâche démarrée ou terminée que le fichier ne porte plus, ou une ligne de devis d'une telle tâche » seulement.
- **Constat.** Deux des trois cas que la spec demande de signaler n'ont aucune forme ; la description d'`ignored` dit même l'inverse (vide pour un devis). Un implémenteur du service ne saurait pas où écrire, et le front n'aurait rien à montrer. L'énumération `ImportIgnoredKind` est fermée : l'élargir après le gel est un changement de contrat.
- **Proposition.** `ImportIgnoredKind` gagne `provision_lines` (« d'un devis ou d'un reste à engager, les lignes du fichier qui portent la lignée d'une ligne de provision, laissées telles quelles, nommées par leur désignation ») ; `ImportDifference.change: kept` s'étend à « une ligne de provision absente du fichier, conservée (WF-INTF-0100) » ; la phrase « Vide pour un devis ou un reste à engager » est retirée. Exemples : un devis avec une provision dans `import_analysed` (ou une variante `import_estimate_provision_kept`).
- **DECISIONS.md** : EP-14/L42p (provision d'un risque) et L42s (`PROVISION_CATEGORY_RESERVED`) ne traitent que la ligne nouvelle ; #789 (ouvert, « Constats reçus ») porte sur la provision déplacée par un planning, pas sur ces deux cas.

#### K-07 — Les exports sont désormais stockés en attente de téléchargement
- **gravité** : majeur ; **emplacement** : `docs/api/paths/system.yaml:218-220` (`getBackgroundTaskResult` : « Le fichier est engendré à la demande et n'est pas stocké (WF-DAT-0120) »), `system.yaml:251` (`'409'` sans description), `paths/exchanges.yaml:455-456` (`requestExport`), `schemas/exchanges.yaml:543-546` (`ExportRequest`) ; **exigence** : WF-ARC-0040, corps `{+import, les fichiers exportés en attente de téléchargement+} et les sauvegardes` ; WF-DAT-0120 (révisée) : « les fichiers exportés en attente de téléchargement … Un fichier exporté est supprimé à l'issue de son premier téléchargement complet, ou au terme de vingt-quatre heures s'il n'a pas été téléchargé ; un téléchargement interrompu le laisse en place » ; §4.4.4 (FLX-02) : « engendrement du fichier par le worker …, dépôt sur le stockage objet (TFX-05), téléchargement par l'utilisateur, suppression du fichier » ; **ce que dit le contrat** : trois descriptions affirment le contraire en citant WF-DAT-0120 ; `BackgroundTaskRef.result_url` « où lire le résultat » ; un `409` générique (`Conflict`) sans texte, que seule la décision EP-02/L38 explique (« le 409 d'un résultat expiré ou pas encore prêt »).
- **Constat.** Le mécanisme du contrat (tâche de fond, puis `getBackgroundTaskResult`) convient à la spec révisée, mais ses descriptions disent un fichier jamais stocké, donc relisible à volonté : un implémenteur ne supprimerait rien, et un client relirait un résultat que la spec supprime après le premier téléchargement complet. Le refus d'un résultat expiré ou déjà consommé n'a ni code ni condition nommés.
- **Proposition.** Réécrire les trois descriptions : « engendré par le worker, déposé sur le stockage objet, supprimé à l'issue du premier téléchargement complet ou au terme de vingt-quatre heures (WF-DAT-0120, WF-ARC-0040) ». Décrire le `409` : `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `result_available` (à ajouter à `CommandCondition`) pour un résultat pas encore prêt ; `404` pour un résultat supprimé (téléchargé ou expiré), `result_url` passant à `null`. Exemple `task_result_expired`. Vérifier que `INVENTORY.md` cite WF-DAT-0120 et WF-ARC-0040 sur ces opérations.
- **DECISIONS.md** : EP-02/L38 (#416, « se télécharge en flux ») et EP-02/L29 (#323, « nommé et typé ») — antérieures ; elles décrivent le flux sans trancher le stockage ; aucune décision depuis la révision de WF-DAT-0120.

#### K-08 — La ligne nouvelle sous une tâche terminée : quel motif de rejet ?
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/exchanges.yaml:360-401` (`ImportRejection`), `docs/api/components/common.yaml:421` (`TASK_COMPLETED`) ; **exigence** : WF-INTF-0100 `{+— une ligne nouvelle sous une tâche terminée est rejetée au compte rendu (WF-INTF-0080) —+}`, WF-INTF-0120 `{+sauf si cette tâche est terminée : la ligne est alors rejetée au compte rendu (WF-INTF-0080)+}` ; **ce que dit le contrat** : `ImportRejection` nomme `TASK_WITHOUT_WORKING_HOURS`, `PROVISION_CATEGORY_RESERVED`, `SUBPROJECT_HAS_ACTUAL_COSTS`, `DUPLICATE_COST_LINE` ; rien pour la tâche terminée. `TASK_COMPLETED` existe pour la réestimation (`remaining_entry`).
- **Constat.** Le code est ouvert (`ErrorCode`), donc le contrat peut le porter sans changement de schéma, mais rien ne dit lequel : le service et le front choisiraient chacun. Corrigible par la description.
- **Proposition.** Ajouter à la description d'`ImportRejection` : « une ligne nouvelle d'un devis ou d'un reste à engager que le fichier place sous une tâche terminée : `TASK_COMPLETED`, `params.tasks` nommant la tâche (`lineage_id`, `label`) comme `TASK_WITHOUT_WORKING_HOURS` (WF-INTF-0100, WF-INTF-0120) » ; un exemple de ligne rejetée dans `import_remaining_analysed`.
- **DECISIONS.md** : aucune (aucune occurrence de `TASK_COMPLETED` dans DECISIONS.md).

#### K-09 — Le rôle « Manager » de la fixture ne paramètre pas la matrice ni les seuils
- **gravité** : mineur ; **emplacement** : `fixtures/api/access_roles.json` (écrite à la main ; `mockaudit.py` la relit), `fixtures/api/me_manager.json` ; **exigence** : WF-INTF-0020, corps `{+le référentiel commun — +}… {+les natures+} et {+catégories de coût,+} les taux horaires, {+la correspondance de l'extraction des coûts réels, les bornes de la matrice de risques, les seuils d'alerte des indices et le délai maximal entre deux revues (FBS-3) —+}`, Vérif `{+mène à leur terme le paramétrage de chacune des fonctions FBS-3.1 à FBS-3.4+}` ; **ce que dit la fixture** : « Manager » porte `cost_settings.read/write`, `resource_settings.read/write`, `risk_settings.read`, `indicator_settings.read`, les sept `portfolio_*.read`, `all_projects_read` — sans `risk_settings.write` ni `indicator_settings.write`.
- **Constat.** La matrice (WF-REF-0160) et les seuils et le délai (WF-REF-0170/0180) s'écrivent par `updateReferenceSettings` sous `risk_settings.write` et `indicator_settings.write` (`paths/reference.yaml:96`). Le rôle prédéfini de l'exemple ne les porte pas : la maquette refuse au manager ce que la Vérif lui fait faire. La correspondance des coûts réels, elle, est sous `cost_settings.write` (US-0620) : portée.
- **Proposition.** Ajouter `risk_settings.write` et `indicator_settings.write` au rôle « Manager » dans `access_roles.json` et aux `permissions` de `me_manager.json` ; vérifier `access_role_updated`/`mockaudit.WITHDRAWN` (qui retire au Manager `cost_settings.write` et `resource_settings.write`) et `test_mockaudit.py`.
- **DECISIONS.md** : aucune décision sur les permissions du manager (EP-02/L29 #384 ne règle que le chef de projet).

#### K-10 — « Il ne présente que des valeurs issues des métriques »
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/platform.yaml:7-8` (`SystemStatus`), `paths/system.yaml:89-91` (`getMetrics`) ; **exigence** : WF-OBS-0010, corps `{+Les disponibilités, espaces, taux et âges que présente l'écran+} d'état du système {+sont issus+} de ces métriques ; {+les dates et résultats de la dernière lecture des comptes, de la dernière sauvegarde et du dernier test de restauration sont lus dans la base.+}` et `{+L'API expose en outre, pour chaque composant de données et pour le fournisseur d'identité, sa disponibilité, vérifiée par une sonde à chaque collecte+}` ; **ce que dit le contrat** : « Il ne présente que des valeurs issues des métriques (WF-ADM-0130, WF-OBS-0010) » — l'ancienne phrase de la spec.
- **Constat.** Description contredite par la spec révisée ; sans conséquence sur les schémas (`last_*` sont des `OperationOutcome`), mais un implémenteur chercherait ces dates dans Prometheus.
- **Proposition.** `SystemStatus` : « Les disponibilités, espaces, taux et âges viennent des métriques (`getMetrics`) ; les dates et résultats des dernières lecture des comptes, sauvegarde et test de restauration sont lus dans la base (WF-OBS-0010). » `getMetrics` : ajouter que la disponibilité des composants de données et du fournisseur d'identité est sondée à chaque collecte.
- **DECISIONS.md** : aucune.

#### K-11 — Le point de métriques, servi en HTTP et interne au cluster
- **gravité** : mineur ; **emplacement** : `docs/api/paths/system.yaml:83-98` (`getMetrics`, `security: []`, `'404'`) ; **exigence** : WF-SEC-0010, corps `{+Seul le point de métriques (TFX-09), qui n'expose ni donnée de projet, ni identité, ni secret, est servi en HTTP, et il n'est joignable que du réseau interne au cluster.+}`, Vérif `{+hors le point de métriques, qui n'est pas joignable hors du cluster+}` ; **ce que dit le contrat** : une opération sous `/api/v1`, publique, dont le 404 déclaré n'est pas expliqué.
- **Constat.** Le contrat ne dit ni que le point est servi sans TLS, ni qu'il n'est pas routé par l'entrée publique — ce que le 404 traduit sans le dire. Un consommateur du contrat (ou le faux back) pourrait croire le point exposé.
- **Proposition.** Décrire : « Servi en HTTP, sur le réseau interne au cluster seulement (TFX-09, WF-SEC-0010) : l'entrée publique répond 404 ; `security: []` parce que Prometheus ne porte pas de jeton. » Ou sortir l'opération du contrat public (serveur distinct), à trancher.
- **DECISIONS.md** : aucune (aucune occurrence de `getMetrics` ni de `/metrics`).

#### K-12 — La planification livrée des sauvegardes
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/platform.yaml:228-267` (`BackupSchedule`), `paths/platform.yaml:297-318` (`getBackupSchedule`) ; **exigence** : WF-ADM-0170, corps `Les sauvegardes {+sont+} planifiées … {+; la planification livrée est quotidienne (WF-EXP-0050).+}`, Vérif `{+Sur une installation neuve, une sauvegarde est produite chaque jour sans qu'aucune planification ait été saisie.+}` ; **ce que dit le contrat** : `is_enabled`, `frequency`, `at_time`, `retained_count` sans valeur livrée ; `backup_schedule_disabled.json` montre une planification désactivée.
- **Constat.** La valeur livrée est une règle du service que l'écran présente avant toute saisie ; la description ne la donne pas, et l'exemple `disabled` pourrait laisser croire qu'une installation neuve n'a rien.
- **Proposition.** Dans `BackupSchedule` : « Livrée activée, quotidienne, à `01:00` UTC, sept sauvegardes conservées, sans copie externe (WF-ADM-0170, WF-EXP-0050) ; `getBackupSchedule` ne répond jamais 404 pour cette raison. »
- **DECISIONS.md** : EP-02/L42 (#488) et EP-14/L42h ne parlent pas de la valeur livrée.

#### K-13 — La préférence qui distingue aussi les lignes à budget nul
- **gravité** : mineur ; **emplacement** : `docs/api/components/schemas/access.yaml:296` (`DisplayPreferences.highlight_tasks_added_after_reference: { type: boolean }`, sans description) ; **exigence** : WF-ADM-0040, corps `Une préférence d'affichage permet de distinguer visuellement les tâches ajoutées après la révision de référence {+et les lignes dont le montant budgété est nul (WF-RAE-0040). +}` ; **ce que dit le contrat** : un booléen nommé pour les seules tâches, sans description.
- **Constat.** La spec parle d'une seule préférence pour les deux distinctions ; le nom du champ ne couvre que la première et aucune description ne dit la seconde. Le front rendrait les lignes à budget nul sous une autre préférence ou pas du tout. Si le nom doit changer, c'est avant le gel.
- **Proposition.** Au minimum une description : « Distingue visuellement les tâches ajoutées après la révision de référence et les lignes dont le montant budgété est nul (WF-ADM-0040, WF-RAE-0040) » ; ou renommer `highlight_added_after_reference` maintenant, le client engendré et `preferences*.json` suivant.
- **DECISIONS.md** : aucune (WF-ADM-0040 n'est cité que pour le thème et les chronologies).

#### K-14 — Le fichier supprimé quand l'import est refusé à l'application
- **gravité** : mineur ; **emplacement** : `docs/api/paths/exchanges.yaml:10-11` (`uploadFile`), `docs/api/components/schemas/exchanges.yaml:9-13` (`FileUpload`) ; **exigence** : WF-ARC-0100, corps `le fichier est supprimé dès que l'import est appliqué, {+refusé à l'application, +}abandonné ou expiré` ; **ce que dit le contrat** : `applyImport` (409) : « Refusé, le fichier est supprimé, comme celui de tout import refusé à l'application (WF-ARC-0100) » — porté ; `uploadFile` et `FileUpload` : « supprimé dès que l'import est appliqué, abandonné ou expiré ».
- **Constat.** La règle est portée là où elle s'exerce ; les deux descriptions amont énumèrent les cas sans le nouveau, et un lecteur du dépôt ne le trouverait pas.
- **Proposition.** Ajouter « refusé à l'application » aux deux énumérations.
- **DECISIONS.md** : aucune.

### Ce qui est juste

Vérifié conforme à la spec révisée : l'anonymisation d'un compte (WF-ADM-0050/0060 : `anonymizeUser`, `UserAccount.anonymized_at`, refus `is_not_anonymized`, `user_anonymize`, libellés nuls dans le journal et les facettes) ; la lecture des comptes face à un compte anonymisé et le retrait d'un compte local (WF-ADM-0070/0180, `IdentitySyncReport`) ; la restauration qui garde le journal et la liste des sauvegardes et fait échouer les tâches restaurées (WF-ADM-0160, `TASK_INTERRUPTED_BY_RESTORE`) ; le dernier administrateur sur la modification d'un rôle (WF-ADM-0120, `updateAccessRole` 409 `LAST_ADMINISTRATOR`) ; la suppression d'un rôle prédéfini et le rôle supprimé cité par le journal (WF-ADM-0010/0090, `AuditAccessRole`) ; le catalogue à 51 permissions avec la seule lecture pour FBS-1.3, FBS-1.5 et FBS-2 (WF-ADM-0100, `PermissionCode`, `permissions.json`) ; les rôles « Chef de projet » (toutes les permissions distinctes hors `platform_restore` et `all_projects_read`) et « Administrateur » (`audit_log.read`) de `access_roles.json` (WF-INTF-0010/0030) ; le journal et ses cinq filtres, le projet nommé par code et libellé, le projet disparu (WF-ADM-0190, hors K-03) ; le nom de l'entreprise (WF-EXP-0020, `ReferenceSettings.company_name`, décision du 2026-10-22) ; l'écran d'état non servi quand PostgreSQL ou Redis manquent (WF-EXP-0040, 503) ; les codes d'alerte de WF-OBS-0030 ; le format sans version des coûts réels et la colonne manquante (WF-INTF-0070, `openImport` 422) ; l'import sur une structure désignée (WF-INTF-0090, `ImportRequest.structure_id`) et l'export d'une structure (WF-INTF-0110/0130, `ExportRequest.structure_id`) ; le devis refusé sur la structure principale d'un projet En cours, les lignes qui quitteraient un sous-projet à coûts réels (WF-INTF-0100/0120, `project_before_in_progress`, `SUBPROJECT_HAS_ACTUAL_COSTS`) ; le poste de la pièce et les doublons (WF-INTF-0140, `document_item`, `DUPLICATE_COST_LINE`) ; les noms d'onglets fixes (WF-INTF-0180, `ImportRejection.sheet`) ; les liaisons remplacées et le rattachement conservé (WF-INTF-0040, `target: link`, `work_breakdown_label`) ; les constantes d'heures par jour (WF-INTF-0120, `DurationUnits.hours_per_day`).

### Doutes

- **La date de début de planning d'une structure** (WF-PLA-0020, « saisie ») n'apparaît dans aucun schéma (`CostStructure` : `structure_id`, `revision_id`, `kind`, `label`, `risk_id`, `is_merged`, `available_commands`, `lock_version`) : K-05 (a) suppose qu'elle existe. Hors de mon groupe (PLA) ; à vérifier par le relecteur de la planification.
- **WF-ARC-0090** : « conservés pendant la rétention des tâches de fond (§4.4.1) » (trente jours) — `listBackgroundTasks` et `BackgroundTaskRef` ne disent rien de la rétention ; une description suffirait, je ne l'ai pas compté comme constat (lié à K-02 si la rétention devient un paramètre d'exploitation présenté).
- **WF-ADM-0140** : « hors le lien produit à l'installation, qui vaut jusqu'à son emploi » — `PasswordSetupLink.expires_at` est exigé et dit « une heure » ; le lien d'installation n'est pas servi par l'API (sans surface), mais si `createPasswordSetupLink` devait un jour le rendre, `expires_at` devrait être nullable.
- **WF-ARC-0110** : la langue transmise au fournisseur d'identité pour les courriels (choisie, ou par défaut avant la première connexion) — comportement du service sans champ dans `UserCreate` ; je l'ai classé sans surface.
- **WF-EXP-0020** : les valeurs livrées (bornes 25/50/75 % et 1/5/10 %, seuils 0,9/0,8, six semaines, calendrier 8 h du lundi au vendredi) ne sont dites nulle part dans le contrat ; `reference_settings.json` montre d'autres valeurs (0,1/0,3/0,6 ; huit semaines), ce que « modifiables ensuite » admet. Affaire de l'installateur ; une phrase dans `ReferenceSettings` serait un confort.
- **WF-SEC-0030** : « leur code pour un projet ou un rôle de ressource » — aucune action du journal n'a un rôle de ressource pour objet ; rien à porter tant que c'est vrai.

### Relevé

| Exigence | Verdict |
|---|---|
| WF-INTF-0010 | porté (fixture `access_roles.json`, chef de projet) |
| WF-INTF-0020 | non porté (K-09, fixture du manager) |
| WF-INTF-0030 | porté |
| WF-INTF-0040 | non porté (K-05) ; le reste porté |
| WF-INTF-0050 | sans surface (contenu du fichier) ; `structure_id` porté |
| WF-INTF-0060 | porté / sans surface |
| WF-INTF-0070 | porté |
| WF-INTF-0090 | porté |
| WF-INTF-0100 | non porté (K-06, K-08) ; le reste porté |
| WF-INTF-0110 | porté |
| WF-INTF-0120 | non porté (K-06, K-08) ; « date de la revue » déjà relevée en première passe |
| WF-INTF-0130 | sans surface (contenu du fichier) |
| WF-INTF-0140 | porté ; « inchangées et rejetées » déjà relevé en première passe |
| WF-INTF-0180 | porté |
| WF-ADM-0050 | porté |
| WF-ADM-0060 | porté |
| WF-ADM-0070 | non porté (K-01) ; anonymisé porté |
| WF-ADM-0140 | sans surface (lien d'installation) |
| WF-ADM-0180 | porté |
| WF-ADM-0040 | non porté (K-13) |
| WF-ADM-0010 | porté |
| WF-ADM-0090 | porté |
| WF-ADM-0100 | porté |
| WF-ADM-0110 | sans surface (exception de WF-PRJ-0060 : `setContributors` la laisse au service) |
| WF-ADM-0120 | porté |
| WF-ADM-0130 | non porté (K-02) ; versions des composants portées |
| WF-ADM-0160 | porté |
| WF-ADM-0170 | non porté (K-12, mineur) |
| WF-ADM-0190 | non porté (K-03) ; filtres et facettes portés |
| WF-ARC-0110 | sans surface |
| WF-ARC-0040 | non porté (K-07) |
| WF-ARC-0050 | sans surface |
| WF-ARC-0090 | porté (doute sur la rétention) |
| WF-ARC-0100 | porté (K-14, mineur) |
| WF-EXP-0010 | sans surface |
| WF-EXP-0020 | porté (`company_name`, décision 2026-10-22) ; valeurs livrées sans surface |
| WF-EXP-0040 | porté |
| WF-SEC-0010 | non porté (K-11, mineur) |
| WF-SEC-0030 | non porté (K-04) ; `project_create`/`revision_abandon` exclus (L6) |
| WF-OBS-0010 | non porté (K-10, mineur) |
| WF-OBS-0030 | porté (codes) ; seuils → K-02 ; tableau de bord sans surface |
| WF-QUA-0010 | sans surface |

## Annexe L — Delta de la spécification — projets, révisions, planning, devis, données, interface


Lu : `docs/api/README.md` (Conventions) ; `docs/api/paths/projects.yaml` (973 l.) et `paths/revisions.yaml`
(1 799 l.) en entier ; `components/schemas/projects.yaml` (939 l.), `components/schemas/revisions.yaml`
(2 054 l.), `components/common.yaml` (860 l.), `components/parameters.yaml` (507 l.) en entier ; les
opérations et schémas des autres familles que les 57 exigences touchent (`paths/analysis.yaml`
estimate-indicators, missing-rates, workload ; `paths/exchanges.yaml` requestExport ; `paths/system.yaml`
getBackgroundTaskResult ; `paths/reference.yaml` duration-units, ReferenceReadiness ; `paths/portfolio.yaml`
workload, cost-structure, risks ; `schemas/indicators.yaml` EstimateIndicators, MissingRate, WorkloadPlan,
CalculationContext ; `schemas/access.yaml` GridPreferences ; `schemas/exchanges.yaml` ExportRequest) ;
`docs/api/DECISIONS.md` par grep ciblé sur chaque exigence et chaque mot-clé nouveau ; `docs/api/INVENTORY.md` ;
le diff `spec-diff-group2.md` (57 exigences) et le texte entier de 8 exigences dans `docs/spec/waterfall-spec.md` ;
14 fixtures ouvertes (`revisions`, `revision`, `revision_marked`, `revision_offer`, `revision_created`,
`project`, `project_pricing`, `project_created`, `skeleton_generated`, `milestone_completed`, `nodes`,
`nodes_planning`, `dependencies_provision`, `duration_units`). Chaque changement de la spec est daté par
`git log -S` sur `docs/spec/waterfall-spec.md` (4fc7546f et 7dc06e9d du 2026-10-09, b18a8883 du 2026-10-10,
149470aa du 2026-10-22).

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| L-01 | bloquant | `components/schemas/revisions.yaml:1300-1308, 1354-1367` (`EstimateLineFacet`), `:1237-1247` (`TaskFacet`), `:938-955` (`NodeTotals`) ; `schemas/indicators.yaml:131-136` ; `schemas/revisions.yaml:2010-2014` | Les montants budgété et réestimé sont « à l'année de référence » dans tout le contrat ; la spec les veut « inflation comprise, à l'année de consommation », le montant avant inflation n'étant qu'une valeur de lecture | WF-DEV-0020, WF-DEV-0050, WF-DEV-0030, WF-PRJ-0040 |
| L-02 | majeur | `components/schemas/projects.yaml:557-574` (`ProjectExit`), `paths/projects.yaml:294-331` (`exitProject`) | La sortie d'un projet qui porte une révision en cours doit la marquer (nom de version) ou l'abandonner dans la même opération ; `ProjectExit` ne porte ni le choix ni le nom de version | WF-CYC-0090 |
| L-03 | majeur | `fixtures/api/project.json` (`available_commands`), `components/schemas/projects.yaml:384` (`ProjectCommand`) | `lose` est listée indisponible (`project_in_pricing`) sur un projet En cours ; la spec dit qu'une sortie qui ne deviendra jamais possible « n'y figure pas » | WF-CYC-0060 |
| L-04 | majeur | `components/schemas/revisions.yaml:13-63` (`Revision`), `:163-173` (`RevisionSnapshot`), `paths/revisions.yaml:6-9` (`listRevisions`) | Le taux d'inflation et la probabilité de gain conservés sont des attributs de la révision que l'historique présente ; ils ne vivent que dans `snapshot`, nullable et nul dans toutes les fixtures | WF-REV-0090, WF-REV-0070 |
| L-05 | majeur | `components/schemas/revisions.yaml:13-63` (`Revision`) | La révision en cours doit dire la révision marquée dont elle est issue (nom de version) ; aucun champ ne la porte | WF-IHM-0020 |
| L-06 | majeur | `components/schemas/revisions.yaml:277-308` (`CostStructure`), `:355-367` (`StructureCreate`), `paths/revisions.yaml:410-469` | Chaque structure porte une date de début de planning, saisie, défaut au jour de sa création ; le contrat ne la lit ni ne l'écrit nulle part | WF-PLA-0020, WF-REV-0100 |
| L-07 | majeur | `components/schemas/revisions.yaml:1208-1221` (`TaskFacet.total_float`, `is_critical`), `:1037-1050` (`NodeSchedule`) | Le conflit tâche manuelle / prédécesseur doit signaler les deux tâches et nommer la liaison ; le contrat ne signale que le prédécesseur par sa marge négative | WF-PLA-0020 |
| L-08 | majeur | `components/schemas/revisions.yaml:1457-1464` (`PredecessorsReplace`), `paths/revisions.yaml:1197-1203, 1232-1242` (`setPredecessors`) | Deux tâches ne sont reliées que par une liaison au plus ; aucune unicité ni refus déclaré | WF-PLA-0030 |
| L-09 | majeur | `components/schemas/revisions.yaml:675-685` (`ComputedField`), `:523-543` (`editable_fields`), `paths/revisions.yaml:919-920` (`deleteNode`), `:1435-1436` (`moveNodes`) | Une récapitulative est toujours automatique (mode non saisissable, non déclarable calculé) et devient feuille ou jalon en perdant sa dernière subordonnée ; le contrat ne dit que « garde son rattachement » | WF-PLA-0040 |
| L-10 | majeur | `components/schemas/revisions.yaml:1208-1221` (`TaskFacet`), `fixtures/api/nodes.json`, `nodes_planning.json` (tâche « Études ») | Une récapitulative porte la plus petite marge de ses subordonnées et est critique dès que l'une l'est ; descriptions muettes, et les fixtures omettent `total_float` et `is_critical` sur les récapitulatives | WF-PLA-0100 |
| L-11 | majeur | `paths/revisions.yaml:916-919` (`deleteNode`) | Les lignes de provision d'une tâche supprimée ne sont pas supprimées mais passent sur une autre tâche ; non dit, et la description invente un refus « tâche portant un coût réel » | WF-PLA-0070 |
| L-12 | majeur | `components/schemas/revisions.yaml:729-775` (`NodeColumn`) | La grille de planning présente les dates de démarrage et de terminaison ; `NodeColumn`, qui ordonne les colonnes pour le collage, ne les a pas | WF-PLA-0080 |
| L-13 | majeur | `fixtures/api/milestone_completed.json`, `components/schemas/revisions.yaml:1179-1183` (`started_on`), `:1703-1717` (`ProgressUpdate`) | Une tâche terminée sans avoir été démarrée prend pour date de démarrage celle de sa terminaison ; le jalon terminé de la fixture garde `started_on` nul | WF-PLA-0130 |
| L-14 | majeur | `paths/revisions.yaml:533-535` (`mergeCostStructure`), `components/schemas/revisions.yaml:373-374` (`StructureMerge`) | La fusion « ne touche que les montants budgétés … réestimés conservés » : règle ancienne ; la spec donne les grandeurs de référence, et aussi les grandeurs courantes d'une ligne désignée d'une tâche non démarrée jamais réestimée | WF-REV-0050 |
| L-15 | majeur | `components/schemas/revisions.yaml:1979-2014` (`RevisionComparison.amount_deltas`) | Un seul `delta` par nature et sous-projet ; la spec veut les écarts de montants budgétés et de montants réestimés | WF-REV-0080 |
| L-16 | majeur | `paths/analysis.yaml:84-92, 118-126` (`getProjectWorkload`), `components/parameters.yaml:383-391` (`WorkloadBasis`), `schemas/indicators.yaml:358-372` (`WorkloadPlan`) | Sans révision de référence, seule la révision en cours est admise ; la spec n'écarte que la base de la référence et garde une révision marquée ; la répartition du reste après la date de calcul n'est pas décrite | WF-DEV-0070 |
| L-17 | majeur | `paths/projects.yaml:789-799` (`setContributors`), `README.md` (403 `NOT_CONTRIBUTOR`) | Un non-contributeur porteur de deux permissions peut inscrire un chef de projet quand le dernier est désactivé ; le contrat réserve l'écriture aux chefs de projet contributeurs | WF-PRJ-0060 |
| L-18 | majeur | `paths/revisions.yaml:1646-1700` (`undoLastChange`), `components/schemas/revisions.yaml:1757-1789` (`UndoResult`) | L'historique annulable est « tenu par le front » et ne survit pas au rechargement ; le contrat le tient côté serveur, par session, sur 50 niveaux (décision EP-02 antérieure) | WF-IHM-0110 |
| L-19 | majeur | `paths/exchanges.yaml` (`requestExport`), `components/schemas/exchanges.yaml:543-546` (`ExportRequest`), `paths/system.yaml` (`getBackgroundTaskResult`) | « Le fichier est engendré à la demande et n'est pas stocké » ; la spec stocke l'export jusqu'au premier téléchargement complet ou vingt-quatre heures | WF-DAT-0120 |
| L-20 | mineur | `paths/revisions.yaml:130-135` (`abandonRevision`) | L'abandon de l'unique révision laisse le projet sans révision, à Chiffrage ; il supprime les risques que plus aucune révision n'évalue ; non dit | WF-REV-0010, WF-DAT-0080, WF-DAT-0130 |
| L-21 | mineur | `paths/revisions.yaml:255-258` (`getRateUpdateProposal`), `components/schemas/revisions.yaml:236-243` ; `paths/exchanges.yaml` (`applyImport`), `paths/risks.yaml` (`createRisk`) | La présentation des taux n'a lieu à la création que si l'utilisateur la demande ; une révision créée par un import, une saisie de risque ou une survenance applique les taux projetés ; seule la fusion le dit | WF-REV-0060 |
| L-22 | mineur | `paths/revisions.yaml:199-201` (`designateReferenceRevision`), `components/schemas/revisions.yaml:227-229` (`ReferenceDesignation`) | « ni révision marquée postérieure » (ancienne règle) alors que le 409 dit « depuis la dernière désignation » | WF-REV-0040 |
| L-23 | mineur | `paths/revisions.yaml:1751-1754` (`generatePlanningSkeleton`) | La feuille par livrable est automatique et d'un jour ; non dit, et aucun exemple ne porte de livrable | WF-PRJ-0030 |
| L-24 | mineur | `components/schemas/indicators.yaml:161-166` (`EstimateIndicators.delta_to_reference`) | L'écart est celui du devis de la révision affichée, lignes de provision comprises de part et d'autre ; le contrat dit « devis en cours » sans parler des provisions | WF-DEV-0060 |
| L-25 | mineur | `components/schemas/projects.yaml:61-72` (`Project.available_commands`), `:93-99` (`CommandCondition`) | Une commande que la qualité sur le projet ne permet pas est présentée indisponible en nommant cette qualité ; `is_contributor` n'est décrite nulle part et la liste dit n'omettre que les commandes sans permission | WF-IHM-0090 |
| L-26 | mineur | `components/schemas/revisions.yaml:474-477` (`Node`) | La lignée fonde aussi le rapprochement des imports ; la description de `lineage_id` ne le cite pas | WF-DAT-0030 |

### Constats

#### L-01 — Les montants budgété et réestimé sont « inflation comprise » dans la spec, « à l'année de référence » dans le contrat
- **bloquant** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:1300-1308` (`EstimateLineFacet`, description), `:1354-1367` (`budgeted_amount`, `reestimated_amount` « à l'année de référence »), `:1237-1247` (`TaskFacet.budgeted_amount`, `reestimated_amount`), `:938-955` (`NodeTotals` : « Chaque montant … à l'année de référence, sauf le montant corrigé de l'inflation »), `:739-742` (`NodeColumn`), `docs/api/components/schemas/indicators.yaml:131-136` (`EstimateIndicators` : « Tous sont à l'année de référence … seul le montant corrigé de l'inflation de la grille porte l'inflation »), `docs/api/components/schemas/revisions.yaml:2010-2014` (`amount_deltas[].delta` « à l'année de référence de chaque révision ») ; **exigence** : WF-DEV-0020 (2026-10-10, 2026-10-22) : « {+Les deux montants sont exprimés inflation comprise, à l'année de consommation de la ligne (WF-DEV-0030, WF-DEV-0040) : c'est à ce titre qu'ils entrent au budget de référence, au reste à engager, à la valeur planifiée et à la valeur acquise. Le montant aux taux de l'année de référence, avant inflation, est une valeur de lecture (WF-DEV-0050).+} » ; WF-DEV-0050 : « son montant {+aux taux de l'année de référence, avant inflation, et, dans une colonne distincte, son montant réestimé, inflation comprise+} » ; glossaire (spec l. 4768, 4820) : « budget de référence … inflation comprise, à l'année de consommation des lignes », « budgété … inflation comprise » ; **ce que dit le contrat** : quatre montants par ligne — `base_amount` (année de référence), `budgeted_amount` et `reestimated_amount` « à l'année de référence », `inflated_amount` « seul à porter l'inflation ».
- **Constat.** La spec a tranché, les 9-10 et 22 octobre, que le budgété et le réestimé portent l'inflation à l'année de consommation, et que le montant avant inflation n'est qu'une colonne de lecture. Le contrat dit l'inverse à chaque endroit où ces montants sont définis, sommés ou comparés ; il a été écrit sur deux décisions antérieures au changement : EP-02/L7 (DECISIONS l. 329-332, #235 : « `budgeted_amount` et `reestimated_amount` restent des attributs de la ligne », seul `inflated_amount` porte l'inflation) et EP-02/L29 (l. 1482-1485, #352 : « Les indicateurs de devis sont à l'année de référence … Écarté : un second total corrigé »). Le sens de deux champs de la ligne, de la tâche, des totaux, des indicateurs de devis et de reste à engager (`RemainingIndicators` parle du même budget de référence), des écarts de comparaison et des exemples engendrés en dépend. Figer le contrat sur ce sens, c'est figer un budget de référence qui n'est pas celui de la spec ; le changer après le gel, c'est changer la valeur de champs existants sans changer leur nom — la pire des incompatibilités.
- **Proposition.** Trancher avec l'auteur, avant le gel, l'une des deux voies : (a) suivre la spec — `budgeted_amount` et `reestimated_amount` deviennent « inflation comprise, à l'année de consommation » (`EstimateLineFacet`, `TaskFacet`, `NodeTotals`, `EstimateIndicators.total` et ses ventilations, `amount_deltas`), `inflated_amount` disparaît ou devient le synonyme du réestimé, `base_amount` reste « aux taux de l'année de référence, avant inflation » ; la grille de devis lit `base_amount` et `reestimated_amount` (deux colonnes), la grille de reste à engager `budgeted_amount` et `reestimated_amount` ; régénérer les fixtures (`wftools.mockstructure.inflated`) ; (b) faire modifier la spec pour revenir à la lettre des décisions #235/#352, qui ont un motif (« la somme des parts ne valant cent que sur une même base »). La voie (a) est celle du glossaire et de WF-RIS-0050 ; dans les deux cas, dire la décision dans DECISIONS.md en citant la date du changement de la spec.
- **DECISIONS.md** : EP-02/L7 (l. 329-332, #235) et EP-02/L29 (l. 1482-1485, #352), toutes deux antérieures au 2026-10-09 et contredites par la spec actuelle ; aucune décision postérieure sur « inflation comprise ».

#### L-02 — La sortie d'un projet qui porte une révision en cours doit la marquer ou l'abandonner dans la même opération
- **majeur** ; **emplacement** : `docs/api/components/schemas/projects.yaml:557-574` (`ProjectExit` : `to_state`, `confirmed`, `reason`), `docs/api/paths/projects.yaml:294-331` (`exitProject`, 409 « Sortie non permise depuis l'état courant ») ; **exigence** : WF-CYC-0090 (2026-10-10) : « {+Lorsque le projet porte une révision en cours, la confirmation demande de la marquer, avec un nom de version (WF-REV-0020), ou de l'abandonner (WF-REV-0010) ; la sortie n'est appliquée qu'avec ce choix, dans la même opération. Un projet terminal ne porte donc aucune révision en cours.+} » ; Vérif : « après la sortie, le projet n'a plus de révision en cours, et ses indicateurs se lisent dans sa dernière révision marquée » ; **ce que dit le contrat** : `ProjectExit` ne porte que l'état visé, la confirmation et le motif ; `exitProject` ne nomme aucune condition tenant à la révision en cours ; `project_completed` (exemple du 200) a `current_revision_id` nul sans que rien dise comment.
- **Constat.** Un projet En cours porte presque toujours une révision en cours (celle du reste à engager) ; sans le choix dans le corps, le service ne peut ni marquer (il lui manque le nom de version, unique) ni abandonner sans décision de l'utilisateur, et un projet terminal garderait une révision en cours, ce que la spec interdit. Le marquage étant une tâche de fond (`markRevision`, 202), la sortie « dans la même opération » change aussi la forme de la réponse quand la révision est marquée. C'est un ajout de champs au corps d'écriture et une règle de refus : à faire avant le gel.
- **Proposition.** Ajouter à `ProjectExit` un objet `current_revision` exigé dès que le projet porte une révision en cours : `{ action: mark | abandon, version_name?: string, description?: string, lock_version: LockVersion }` ; 422 `VALIDATION_FAILED` sur `/current_revision` par `VALUE_REQUIRED` quand le projet en porte une et que rien n'est envoyé, sur `/current_revision/version_name` par `VALUE_REQUIRED` avec `mark` ; 409 `ALREADY_EXISTS` sur `/current_revision/version_name` comme `markRevision` ; dire si la sortie avec marquage rend 202 `BackgroundTaskRef` (`kind: revision_mark`, la transition appliquée à la fin de la tâche) ou reste synchrone ; `ProjectCommand.complete|lose|abandon` nomment `no_background_task_running` pendant un marquage. Exemple de refus et exemple de sortie avec marquage.
- **DECISIONS.md** : aucune décision (seule l. 326-328, EP-02/L7, sur le motif de la sortie ; aucune occurrence d'`exitProject` ni de `ProjectExit`).

#### L-03 — « Déclarer perdu » ne doit pas figurer sur un projet En cours
- **majeur** ; **emplacement** : `fixtures/api/project.json` (`available_commands` : `('lose', False, ['project_in_pricing'])` sur un projet `in_progress`), `docs/api/components/schemas/projects.yaml:384` (`ProjectCommand` : « ouvrir une révision, les trois sorties du cycle de vie (WF-CYC-0060) », sans règle de présence) ; **exigence** : WF-CYC-0060 Vérif (2026-10-10) : « {+Une sortie qui le deviendra dans un état ultérieur — Terminer depuis Chiffrage — y est présentée indisponible, avec sa condition (WF-IHM-0090) ; une sortie qui ne le deviendra jamais — Déclarer perdu depuis En cours — n'y figure pas.+} » ; **ce que dit le contrat** : `project_created` liste `complete` indisponible (`project_in_progress`) et `lose` indisponible (`project_in_pricing`) — juste pour Créé, d'où les deux deviendront possibles ; `project.json` (En cours) liste `lose` indisponible, `project_in_pricing`, alors qu'un projet En cours ne reviendra jamais à Chiffrage.
- **Constat.** La spec distingue depuis le 10 octobre « indisponible » (possible plus tard) et « absent » (jamais possible) ; le témoin principal montre une commande que le menu ne doit pas montrer, et aucune description ne dit la règle : le front, qui « ne déduit rien de l'état », affichera « Déclarer perdu » grisé sur tous les projets En cours. C'est un exemple et une description, mais ils servent de spécification au front et au faux back.
- **Proposition.** Dans `ProjectCommand`, après « les trois sorties du cycle de vie » : « `complete` est listée dès Créé, indisponible avant En cours (`project_in_progress`) ; `lose` est listée aux états Créé et Chiffrage, indisponible à Créé (`project_in_pricing`), et n'est plus listée dès En cours — une sortie qui ne redeviendra jamais possible n'y figure pas (Vérif de WF-CYC-0060) ; `abandon` est listée sur tout projet non terminal ». Retirer `lose` de `project.json`, `project_revision_opened.json`, `project_without_current_revision.json` et des autres témoins En cours ; vérifier `mockwitness`.
- **DECISIONS.md** : aucune décision (l. 4114 cite `project_in_pricing` pour une autre raison ; EP-02/L44a, l. 3889-3908, parle du prochain état, pas des sorties listées).

#### L-04 — Le taux d'inflation et la probabilité de gain conservés sont des attributs de la révision
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:13-63` (`Revision`, `required` sans eux ; `snapshot` nullable), `:163-173` (`RevisionSnapshot.inflation_rate`, `win_probability`), `docs/api/paths/revisions.yaml:6-9` (`listRevisions` : « Nom de version, description, état, date de marquage, année de référence et caractère de référence — les attributs d'une révision (WF-REV-0090) ») ; fixtures `revisions.json`, `revision.json`, `revision_marked.json`, `revision_offer.json`, `revision_created.json` : aucune ne porte `snapshot` ; **exigence** : WF-REV-0090 (2026-10-09) : « son année de référence, {+le taux d'inflation et la probabilité de gain qu'elle conserve (WF-REV-0030, WF-REV-0060),+} » ; WF-REV-0070 : « nom de version, description, date de marquage, {+année de référence, taux d'inflation et probabilité de gain conservés (WF-REV-0090),+} » et Vérif « {+L'année de référence, le taux d'inflation et la probabilité de gain affichés pour une révision marquée sont ceux conservés à son marquage, même après modification de ceux du projet.+} ».
- **Constat.** L'historique des révisions (`listRevisions`) doit afficher ces deux valeurs par ligne ; le contrat ne les offre que dans `snapshot`, que la liste ne rend pas (toutes les fixtures l'omettent, DECISIONS l. 5024 : « `Revision.snapshot` étant nul partout ») et que `getRevision` lui-même ne rend pas dans ses exemples. Le raisonnement qui a sorti `reference_year` de l'instantané vaut mot pour mot (DECISIONS l. 1187-1194 : « champ dans `RevisionSnapshot`, où il n'aurait été lu qu'avec l'instantané entier, quand l'historique des révisions le présente (WF-REV-0090) »). Ajouter deux champs exigés après le gel est une rupture pour les clients générés.
- **Proposition.** Dans `Revision`, `inflation_rate` et `win_probability` (`Percent`, exigés, `readOnly`) : « Le taux d'inflation et la probabilité de gain que la révision conserve (WF-REV-0090, WF-REV-0030) : ceux du projet à sa création pour une révision en cours — où ils suivent le projet jusqu'au marquage (WF-PRJ-0040) —, figés au marquage pour une révision marquée ». Les retirer de `RevisionSnapshot` ou les y laisser en double déclaré. Les ajouter aux fixtures (`mockhistory`) : l'offre v1.0 de 2025 garde la probabilité de gain d'alors. Compléter la description de `listRevisions`.
- **DECISIONS.md** : aucune décision postérieure ; l. 1187-1194 (EP-02/L29, `reference_year`) donne le modèle à suivre.

#### L-05 — La révision en cours doit nommer la révision marquée dont elle est issue
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:13-63` (`Revision` : aucun champ d'origine) ; `docs/api/components/schemas/indicators.yaml:103-119` (`CalculationContext`, « que tout écran doit pouvoir afficher (WF-IHM-0020) », sans lui non plus) ; **exigence** : WF-IHM-0020 (2026-10-10) : « la révision dans laquelle il lit — {+pour une révision marquée, +}son nom de version ; {+pour la révision en cours, cette mention et le nom de version de la révision marquée dont elle est issue+} » ; **ce que dit le contrat** : `Revision.version_name` est nul pour une révision en cours ; rien ne dit de quelle révision marquée elle est la copie (WF-REV-0010).
- **Constat.** Chaque écran de projet doit afficher « révision en cours, issue de v2.1 » ; le front ne peut pas le déduire avec certitude — la copie peut dater d'avant un abandon et une recréation, et le contrat ne garantit nulle part que la source est la dernière révision marquée au moment de la lecture. C'est un attribut lu partout, à ajouter au schéma avant le gel.
- **Proposition.** `Revision.source_revision_id` (`Uuid`, nullable : nul pour la première révision d'un projet) et `source_version_name` (chaîne, nullable, résolu à la lecture, WF-ARC-0020) : « la révision marquée dont la révision en cours est la copie (WF-REV-0010), que tout écran nomme avec elle (WF-IHM-0020) » ; dire s'ils restent portés une fois la révision marquée. Les porter aussi dans `CalculationContext` si les indicateurs se lisent sans relire la révision. Fixtures : la révision 102 du témoin est issue de 101 (« Référence »).
- **DECISIONS.md** : aucune décision (une seule occurrence de WF-IHM-0020, l. 795, sans rapport).

#### L-06 — La date de début de planning d'une structure n'est ni lue ni écrite
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:277-308` (`CostStructure` : `structure_id`, `revision_id`, `kind`, `label`, `risk_id`, `is_merged`, `available_commands`, `lock_version`), `:355-367` (`StructureCreate`), `docs/api/paths/revisions.yaml:410-469` (`listCostStructures`, `createCostStructure`, aucune modification d'une structure) ; seule trace : `NodeListMeta.scheduled_at` (`:907-916`, « la dernière écriture qui l'a redatée — … sa date de début de planning ») ; **exigence** : WF-PLA-0020 (2026-10-09) : « {+Chaque structure de coûts porte une date de début de planning, saisie, qui vaut par défaut le jour de sa première création ; une structure reprise d'une révision marquée (WF-REV-0010) conserve la sienne. Une tâche en mode automatique sans prédécesseur commence à cette date, à la première heure travaillée de son calendrier applicable. L'import MS Project la lit dans la date de début du projet du fichier, et l'export l'y écrit+} » ; Vérif : « {+avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs automatiques+} » ; WF-REV-0100 : « Chaque structure porte une nature …, un libellé,{+ une date de début de planning (WF-PLA-0020),+} » ; glossaire l. 4784.
- **Constat.** Un attribut saisi, qui redate tout le planning, sans champ de lecture ni opération d'écriture : le front ne peut ni l'afficher ni la changer, et le faux back ne peut pas la servir. Le contrat connaît la règle (DECISIONS l. 6317 : une tâche créée naît « à la date de début de planning ») sans la porter. Ajouter un champ exigé et une écriture après le gel est une modification incompatible.
- **Proposition.** `CostStructure.planning_start_date` (`PlanningDate`, exigé) : « Date de début de planning de la structure (WF-PLA-0020, WF-REV-0100) : le jour de sa première création par défaut, conservée par la copie d'une révision (WF-REV-0010), lue dans la date de début du projet d'un fichier MS Project importé et écrite dans celui exporté (WF-INTF-0040, WF-INTF-0050) ; une tâche automatique sans prédécesseur y commence ». Une écriture `PATCH …/structures/{structure_id}` (`CostStructureUpdate` : `planning_start_date`, `label`, `lock_version`) sous `edit_planning`, rendant `NodesWritten` (les tâches redatées dans `rescheduled`, les montants dans `reinflated`), 412 et 422 (la spec dit « à la première heure travaillée » : une date chômée est donc admise, à confirmer). `StructureCreate.planning_start_date` facultative.
- **DECISIONS.md** : aucune décision ; l. 6317 (EP-15/US-0460) et `NodeListMeta.scheduled_at` supposent la date sans la nommer dans un schéma.

#### L-07 — Le conflit entre une tâche manuelle et son prédécesseur signale les deux tâches et nomme la liaison
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:1208-1221` (`TaskFacet.total_float` : « un prédécesseur qui ne peut pas finir à temps pour elle porte une marge négative, il est critique, et le conflit est signalé (WF-PLA-0020). Nulle pour une tâche en mode manuel » ; `is_critical`), `:1037-1050` (`NodeSchedule`, idem) ; **exigence** : WF-PLA-0020 (2026-10-10) : « {+Lorsqu'un prédécesseur en mode automatique ne peut pas satisfaire la liaison qui le relie à une tâche en mode manuel — finir ou commencer avant la date que cette liaison impose, selon son type (WF-PLA-0030) —, la tâche manuelle et ce prédécesseur sont signalés dans la grille de planning et dans le diagramme de Gantt, selon l'échelle commune de WF-IHM-0070 ; le signalement nomme la liaison en cause et disparaît dès que les dates le permettent.+} » ; WF-IHM-0070 ajoute « le conflit entre une tâche manuelle et ses prédécesseurs (WF-PLA-0020) » à l'échelle commune ; WF-PLA-0100 Vérif : « {+Un prédécesseur lié début à début à une tâche manuelle, et qui ne peut pas commencer avant elle, porte une marge négative et est signalé.+} ».
- **Constat.** Le contrat ne signale que le prédécesseur, par une marge négative que la grille doit interpréter ; la tâche manuelle, qui porte `total_float` nul et `is_critical` faux, n'est pas signalée, et aucune liaison n'est nommée. Le front devrait croiser marges négatives et prédécesseurs pour retrouver la tâche manuelle et la liaison, ce que WF-ARC-0020 et la convention des valeurs calculées lui interdisent. Le type de liaison (début à début, fin à fin) change ce qui est jugé.
- **Proposition.** Sur `TaskFacet` (et `NodeSchedule`) : `link_conflicts`, tableau, toujours rendu (vide sans conflit), chaque entrée `{ predecessor_node_id, successor_node_id, link_type }` — sur la tâche manuelle, les liaisons que ses prédécesseurs ne peuvent pas satisfaire ; sur le prédécesseur, celles qu'il ne satisfait pas — « calculé, jamais saisi, disparaît dès que les dates le permettent (WF-PLA-0020) » ; `rescheduled` le porte pour que le signalement suive une écriture. Nommer `task.link_conflicts` dans `NodeFields`.
- **DECISIONS.md** : l. 1385-1390 (EP-02/L29, #402, « La marge totale est signée ») et l. 2304 (EP-02/L27), antérieures ; aucune décision sur le signalement des deux tâches ni sur la liaison nommée.

#### L-08 — Une seule liaison entre deux tâches
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:1457-1464` (`PredecessorsReplace.predecessors`, sans `uniqueItems` ni règle), `docs/api/paths/revisions.yaml:1197-1203` et `:1232-1242` (`setPredecessors`, 422 : boucle, récapitulative, horizon, « valeur hors règle ») ; **exigence** : WF-PLA-0030 (2026-10-10) : « Deux tâches [-peuvent être reliées par plusieurs liaisons-]{+ne sont reliées que par une liaison au plus, comme dans MS Project ; une seconde liaison entre les mêmes tâches est refusée+} » ; **ce que dit le contrat** : rien ; la règle inverse (plusieurs liaisons) était celle de la spec quand le contrat a été écrit.
- **Constat.** Un refus nouveau, par champ, que ni le schéma ni le 422 ne déclarent : une saisie qui envoie deux liaisons vers le même prédécesseur passerait (A→B et B→A sont déjà une boucle, refusée). L'import MS Project (`ImportDifference` sur les liaisons) et la fusion sont concernés de même.
- **Proposition.** `PredecessorsReplace` : « Deux tâches ne sont reliées que par une liaison au plus (WF-PLA-0030) : deux entrées pour le même `predecessor_node_id` sont refusées par 422 `VALIDATION_FAILED`, `fields` sur `/predecessors/<n>/predecessor_node_id` de chaque occurrence après la première, motif `DUPLICATE_LINK` » (code nouveau au catalogue, ou `ALREADY_EXISTS` par champ, à trancher) ; l'ajouter au 422 de `setPredecessors`, au motif de rejet d'une liaison importée (`ImportRejection`) et au compte rendu de fusion (`StructureMergeReport.refusals`). Exemple.
- **DECISIONS.md** : aucune décision (l. 6347-6368 traitent les boucles et `LINK_FORBIDDEN`).

#### L-09 — Une récapitulative est toujours automatique, et redevient feuille ou jalon en perdant sa dernière subordonnée
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:675-685` (`ComputedField` : pas de `task.scheduling_mode`), `:523-543` (`editable_fields` : « une récapitulative ni durée, ni dates, ni avancement (WF-PLA-0130) »), `:1533-1547` (`TaskFacetUpdate`), `docs/api/paths/revisions.yaml:919-920` (`deleteNode` : « Une récapitulative qui perd sa dernière subordonnée garde son rattachement au lotissement ») et `:1435-1436` (`moveNodes`, idem) ; **exigence** : WF-PLA-0040 (2026-10-09) : « {+Une tâche récapitulative est toujours en mode automatique ; son mode n'est pas saisissable. … Une récapitulative qui perd sa dernière subordonnée devient une tâche feuille en mode automatique : elle prend pour durée celle qu'elle calculait, conserve son état, ses lignes propres et son rattachement, et ses dates sont recalculées (WF-PLA-0020). Si cette durée est nulle, elle devient un jalon, à l'état non démarré ou terminé qu'elle avait ; démarrée, elle prend une durée d'un jour (WF-PLA-0160).+} » ; Vérif : « {+La suppression de la seule subordonnée d'une récapitulative de dix jours laisse une tâche feuille de dix jours … Une récapitulative dont la seule subordonnée est un jalon terminé … privée de ce jalon, est une feuille démarrée d'un jour, non un jalon. Une récapitulative terminée dont la seule subordonnée, un jalon, est déplacée devient un jalon terminé.+} ».
- **Constat.** Deux manques : (1) le mode d'une récapitulative n'est ni saisissable ni déclarable calculé — `ComputedField` ne connaît pas `task.scheduling_mode`, si bien que la fixture `nodes.json` (« Études ») ne le liste ni dans `editable_fields` ni dans `computed_fields`, et que `TaskFacetUpdate` ne dit pas le refus (`COMPUTED_VALUE` ou `FIELD_NOT_ACCEPTED` ?) ; une feuille manuelle qui reçoit une sous-tâche doit repasser automatique, ce que `moveNodes`/`createNode` ne disent pas. (2) La transformation feuille/jalon d'une récapitulative qui perd sa dernière subordonnée fixe la durée, le mode, le jalon et l'état de la tâche rendue dans `ancestors` ; le contrat ne dit que le rattachement, et un implémenteur laisserait une « récapitulative » sans subordonnée ou une durée nulle.
- **Proposition.** Ajouter `task.scheduling_mode` à `ComputedField` : « le mode d'une récapitulative, toujours automatique (WF-PLA-0040) » ; dans `editable_fields` : « une récapitulative ni mode, ni durée, ni dates, ni avancement » ; dans `TaskFacetUpdate`, le refus `COMPUTED_VALUE` sur `/scheduling_mode` d'une récapitulative. Dans `deleteNode`, `moveNodes` et `NodesWritten.ancestors` : « une récapitulative qui perd sa dernière subordonnée est rendue dans `ancestors` telle qu'elle devient : une feuille automatique de la durée qu'elle calculait, à son état, avec ses lignes et son rattachement ; un jalon si cette durée est nulle et qu'elle n'est pas démarrée ; une feuille d'un jour si elle est démarrée (WF-PLA-0040) ; une feuille manuelle qui reçoit une subordonnée repasse automatique ». Exemple `node_summary_emptied`.
- **DECISIONS.md** : l. 1344-1348 (EP-02/L30, #411, antérieure) ne traite que le rattachement conservé ; aucune décision sur le mode ni sur la transformation.

#### L-10 — La marge et la criticité d'une récapitulative
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:1208-1221` (`TaskFacet.total_float`, `is_critical` : rien sur les récapitulatives ; tous deux facultatifs dans `TaskFacet.required`, l. 1139-1153), `fixtures/api/nodes.json` et `nodes_planning.json` : la récapitulative « Études » ne porte ni `total_float` ni `is_critical` ; **exigence** : WF-PLA-0100 (2026-10-09) : « {+Une tâche récapitulative porte la plus petite marge totale de celles de ses subordonnées qui en portent une, et appartient au chemin critique dès que l'une d'elles y appartient ; une récapitulative dont aucune subordonnée ne porte de marge n'en porte pas.+} » ; Vérif : « {+Une récapitulative dont une subordonnée est critique est critique et affiche la marge de cette subordonnée, nulle ou négative.+} » ; WF-PLA-0080 ajoute la colonne « son appartenance au chemin critique ».
- **Constat.** La grille de planning et le Gantt doivent montrer la marge et la criticité d'une récapitulative ; les descriptions ne disent pas comment elles se calculent pour elle, et les témoins les omettent — ce que le front lira comme « pas de marge », faux dès qu'une subordonnée est critique. Le générateur (`mockstructure`) ne les calcule pas pour les récapitulatives. `ComputedDependency.float_dates` ne couvre pas « la plus petite marge des subordonnées ».
- **Proposition.** `total_float` : « … Une récapitulative porte la plus petite marge de ses subordonnées qui en portent une, nulle quand aucune n'en porte (WF-PLA-0100) » ; `is_critical` : « … vraie pour une récapitulative dont une subordonnée est critique ». Un `ComputedDependency` (`subordinates`) pour `task.total_float` d'une récapitulative. Régénérer les témoins avec ces valeurs sur chaque récapitulative, et rendre `is_critical` toujours présent (l'exiger dans `TaskFacet`, comme `NodeSchedule` l'exige).
- **DECISIONS.md** : l. 531, 557 (EP-02/L10), 1385 (EP-02/L29), 2304 (EP-02/L27), antérieures ; aucune sur la récapitulative.

#### L-11 — La suppression d'une tâche ne supprime pas ses lignes de provision
- **majeur** ; **emplacement** : `docs/api/paths/revisions.yaml:916-919` (`deleteNode` : « La suppression d'une tâche emporte ses lignes et ses liaisons … Refusée sur une tâche portant un coût réel ou déjà démarrée, selon WF-PLA-0070 ») ; **exigence** : WF-PLA-0070 (2026-10-10) : « Une tâche démarrée ou terminée ne peut pas être supprimée.{+ Les lignes de provision qu'elles portent ne sont pas supprimées : elles passent sur une autre tâche selon WF-RIS-0010.+} » ; Vérif : « La suppression d'une tâche démarrée est refusée, et l'utilisateur est renvoyé vers la mise à zéro de son reste à engager. » ; **ce que dit le contrat** : la suppression « emporte ses lignes » sans exception ; le refus cité (« portant un coût réel ») n'est pas dans la spec, qui refuse « démarrée ou terminée » — une tâche terminée n'est pas nommée.
- **Constat.** Une tâche non démarrée qui porte la ligne de provision d'un risque se supprime ; la ligne doit survivre et passer sur la tâche que WF-RIS-0010 désigne, et le risque change de tâche — ce que la réponse doit rendre (la ligne déplacée, son nouveau parent, le risque dont `lock_version` avance), comme le compte rendu de fusion le dit déjà (`StructureMergeReport.differences`, #789). Sans cela, un implémenteur supprime la ligne et laisse un risque identifié sans provision. Le refus « coût réel » est une règle inventée (un coût réel s'impute à un sous-projet, pas à une tâche) et « terminée » manque ; le 409 reste générique.
- **Proposition.** `deleteNode` : « Refusée sur une tâche démarrée ou terminée (409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` nommant la condition — ou `TASK_ALREADY_STARTED`/`TASK_COMPLETED` du catalogue, à trancher), le refus renvoyant à la mise à zéro de son reste à engager (Vérif). Les lignes de provision que la tâche ou ses subordonnées portent ne sont pas supprimées : chacune passe sur la tâche que WF-RIS-0010 désigne, et est rendue dans `nodes` à sa nouvelle place, son risque voyant son `lock_version` avancer (`Risk.provision_task_id`) ». Exemple `node_deleted_provision_moved`.
- **DECISIONS.md** : aucune décision (#789, schémas l. 444-446, ne traite que la fusion).

#### L-12 — Les dates de démarrage et de terminaison sont des colonnes de la grille de planning
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:729-775` (`NodeColumn` : `label` … `progress`, `physical_progress`, `total_float`, `is_critical`, `predecessors`, `work_breakdown` ; ni `started_on` ni `completed_on`) ; **exigence** : WF-PLA-0080 (2026-10-09) : « son état, …, pour une récapitulative, son avancement physique, sa marge totale, {+son appartenance au chemin critique, ses dates de démarrage et de terminaison, son rattachement à un lot ou à un poste (WF-PLA-0170), +}ses prédécesseurs » ; Vérif : « Chacune des colonnes citées est présente » ; **ce que dit le contrat** : `NodeColumn` est « les colonnes de la grille de planning … chacune dans l'ordre où sa grille les présente », et c'est « dans cet ordre qu'un collage remplit les colonnes qui suivent la colonne visée ».
- **Constat.** `is_critical` et `work_breakdown` ont été ajoutés pour les mêmes raisons ; `started_on` et `completed_on`, colonnes de lecture que la grille doit présenter entre la marge et les prédécesseurs, manquent. Un collage dont le bloc traverse ces deux colonnes à l'écran sera décalé par le serveur, qui ne les connaît pas, ou l'écran devra les placer hors de l'ordre de `NodeColumn` — la description l'interdit. Une énumération partagée par trois écritures : à compléter avant le gel.
- **Proposition.** Ajouter `started_on` et `completed_on` à `NodeColumn` après `is_critical` (ou là où la grille les place, à fixer dans la description) : « les dates de démarrage et de terminaison (WF-PLA-0130), colonnes de lecture — une cellule non vide collée y est refusée par `FIELD_NOT_ACCEPTED` ». Vérifier `known_columns` des fixtures `me_grid_settings`.
- **DECISIONS.md** : EP-16/US-0650 (l. 7858-7922) ne traite que `known_columns` ; aucune décision sur ces colonnes.

#### L-13 — Un jalon terminé depuis le Kanban prend pour date de démarrage sa date de terminaison
- **majeur** ; **emplacement** : `fixtures/api/milestone_completed.json` (« Réception usine », `completed`, `started_on` nul, `completed_on` 2026-06-03), `docs/api/components/schemas/revisions.yaml:1179-1183` (`started_on` sans description), `:1703-1717` (`ProgressUpdate`), `docs/api/paths/revisions.yaml:1257-1261` (`setTaskProgress`) ; **exigence** : WF-PLA-0130 (2026-10-10) : « avec la date du jour par défaut{+ ; une tâche terminée sans avoir été démarrée prend pour date de démarrage celle de sa terminaison+} » ; **ce que dit le contrat** : la règle est dite pour la réestimation (`RemainingUpdate.completed_on`, l. 1752-1754 : « la même date est aussi celle de son démarrage ») et pour l'import (DECISIONS l. 1622-1625), pas pour le jalon terminé par `setTaskProgress`, seule tâche qui passe directement de non démarrée à terminée ; l'exemple montre l'inverse.
- **Constat.** Le diagramme temps/temps et la valeur acquise lisent `started_on` ; un jalon terminé avec `started_on` nul est l'« état impossible » que la spec exclut désormais. L'exemple engendré (`mockgestures`) contredit la spec, et la réouverture d'un jalon (« sa date de terminaison effacée ») doit aussi effacer ce démarrage.
- **Proposition.** `TaskFacet.started_on` : « Date du démarrage (WF-PLA-0130) ; une tâche terminée sans avoir été démarrée — un jalon terminé depuis le Kanban — porte celle de sa terminaison ; une récapitulative, celle de la première de ses subordonnées démarrées ». `ProgressUpdate` : « `completed` sur un jalon non démarré écrit `completed_on` et `started_on` à `occurred_on` ; `not_started` les efface tous deux ». Corriger `milestone_completed.json` et `milestone_reopened.json`.
- **DECISIONS.md** : l. 1593-1625 (EP-02/L35) couvre `setLineRemaining` et l'import ; rien sur le Kanban.

#### L-14 — La fusion donne aux lignes désignées leurs grandeurs de référence, et aussi leurs grandeurs courantes quand la tâche n'est pas démarrée et que personne n'a réestimé
- **majeur** ; **emplacement** : `docs/api/paths/revisions.yaml:533-535` (`mergeCostStructure` : « La fusion ne touche que les montants budgétés des lignes que le différentiel désigne ; les montants réestimés sont conservés »), `docs/api/components/schemas/revisions.yaml:373-374` (`StructureMerge`, même phrase) ; à l'inverse `:1358-1360` (`EstimateLineFacet.budgeted_amount` : « la fusion lui donne les grandeurs de référence qu'il porte, d'où son montant budgété est tiré ») ; **exigence** : WF-REV-0050 (2026-10-10) : « La fusion [-ne modifie que les montants budgétés des-]{+donne aux+} lignes que le différentiel désigne{+ les grandeurs de référence qu'il porte, d'où leur montant budgété est tiré (WF-DEV-0020). Une ligne désignée d'une tâche non démarrée, que personne n'a réestimée, prend aussi ces grandeurs pour grandeurs courantes+} ; les {+grandeurs courantes et le montant réestimé+} de toutes les{+ autres+} lignes sont conservés. »
- **Constat.** Deux descriptions de la même opération se contredisent, et la règle nouvelle — un avenant qui rechiffre une ligne non encore démarrée et jamais réestimée change aussi son réestimé — n'est dite nulle part : un service qui suit `mergeCostStructure` conservera 100 réestimés là où la spec veut 140, et la comparaison de révisions (WF-REV-0080 : « une ligne existante dont le différentiel ne modifie que le montant budgété ne présente aucun écart de montant réestimé ») en dépend. La décision qui fonde la phrase ancienne (#467) date d'EP-02/L27, avant le changement.
- **Proposition.** Réécrire les deux phrases selon la spec : « La fusion donne aux lignes que le différentiel désigne les grandeurs de référence qu'il porte, d'où leur montant budgété est tiré ; une ligne désignée d'une tâche non démarrée, que personne n'a réestimée depuis la référence, prend aussi ces grandeurs pour grandeurs courantes ; les grandeurs courantes et le montant réestimé de toutes les autres lignes sont conservés (WF-REV-0050) ». Dire dans `StructureMergeReport.differences` comment un écart `updated` d'une ligne distingue « budgété seul » de « budgété et courant ». Vérifier les fixtures `structure_merge_report*` et le témoin (`mockwitness.OFFER_BUDGETS`, DECISIONS l. 2344-2352).
- **DECISIONS.md** : l. 2344-2352 (EP-02/L27, « décision de l'auteur sur #467 ») — antérieure au 2026-10-10 et contredite ; l. 6748 et 7200 (EP-15) portent déjà la règle nouvelle pour les lignes créées sur un différentiel.

#### L-15 — La comparaison rend les écarts de montants budgétés et de montants réestimés
- **majeur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:1979-2014` (`RevisionComparison.amount_deltas[]` : `dimension`, `key`, `label`, `delta` — un seul montant, « à l'année de référence de chaque révision ») ; **exigence** : WF-REV-0080 (2026-10-09) : « ainsi que les écarts de montants {+budgétés et de montants réestimés, +}par nature de coût et par sous-projet » ; Vérif (2026-10-10) : « {+Les montants réestimés n'y diffèrent que par les lignes que le différentiel ajoute ou retire, par celles des tâches démarrées qu'il termine et par celles dont il change l'année de consommation ; une ligne existante dont le différentiel ne modifie que le montant budgété ne présente aucun écart de montant réestimé.+} ».
- **Constat.** La décision qui a fixé `delta` (l. 1546-1549 : « la spécification ne donne aucun sens (WF-REV-0080, “les écarts de montants”) ») date d'EP-02/L35, avant que la spec nomme les deux montants. Un champ unique ne porte pas deux écarts ; l'ajouter après le gel ajoute un champ exigé. `NodeChange` distingue déjà `budgeted_amount` et `reestimated_amount` par nœud : les totaux doivent suivre.
- **Proposition.** `amount_deltas[]` : remplacer `delta` par `budgeted_delta` et `reestimated_delta` (`Money`, exigés, même sens : comparée moins base), ou garder `delta` pour le budgété et ajouter `reestimated_delta` ; description : « l'écart des montants budgétés et celui des montants réestimés (WF-REV-0080) ». Régénérer `comparison*.json`.
- **DECISIONS.md** : l. 1546-1549 (EP-02/L35), antérieure et contredite ; l. 6664-6669 (EP-15/US-0500/L5) ne change pas la forme.

#### L-16 — Le plan de charge : une révision marquée est une base sans révision de référence, et le reste se répartit après la date de calcul
- **majeur** ; **emplacement** : `docs/api/paths/analysis.yaml:84-92` (`getProjectWorkload` : « Sur un projet sans révision de référence, seule la révision en cours est une base : les deux autres sont refusées (409 …) ») et `:118-126` (409), `docs/api/components/parameters.yaml:383-391` (`WorkloadBasis` : « les montants budgétés de la révision de référence, les montants réestimés d'une révision marquée »), `docs/api/components/schemas/indicators.yaml:358-372` (`WorkloadPlan` : « répartie sur la durée de sa tâche par interpolation linéaire » ; `basis`) ; **exigence** : WF-DEV-0070 (2026-10-10) : « la charge des lignes de main-d'œuvre, {+prise,+} au choix, {+dans+} la révision de référence, {+dans une révision marquée pour sa charge réestimée+}, ou {+dans+} la révision en cours … {+Sur la base d'une révision marquée pour sa charge réestimée ou de la révision en cours — la base du reste à engager —, la charge restante de chaque ligne d'une tâche non terminée est répartie sur la seule part de la durée de la tâche postérieure à la date de calcul (WF-IND-0010), et portée au mois de la date de calcul lorsque la fin de la tâche est dépassée.+} » ; Vérif : « sur un projet sans révision de référence, {+la base de la référence est absente, et sur un projet sans aucune révision marquée, +}seule la révision en cours {+est proposée+} … {+sur une révision marquée, la date de calcul est sa date de marquage. Une tâche non démarrée dont la date de début est antérieure à la date de calcul ne présente aucune charge sur les mois écoulés+} ».
- **Constat.** (1) Le 409 du contrat refuse `marked_remaining` sur un projet en chiffrage qui a marqué des offres ; la spec l'admet dès qu'une révision marquée existe, et ne refuse que `reference_budget`. La décision (l. 334-336, EP-02/L7) est antérieure et contredite. (2) La répartition du reste à engager après la date de calcul — rien sur les mois écoulés, report au mois de la date de calcul quand la fin est dépassée, date de marquage pour une révision marquée — est une règle de calcul que l'écran ne peut pas vérifier ; le générateur la fait (DECISIONS l. 2022-2024) mais le contrat dit « interpolation linéaire » sur « la durée de sa tâche », ce qui est faux pour la base du reste à engager. (3) Le plan est en heures (« charge »), pas en montants : `WorkloadBasis` et `WorkloadPlan.basis` parlent de montants.
- **Proposition.** `getProjectWorkload`/409 : « `reference_budget` est refusé sur un projet sans révision de référence ; `marked_remaining` sur un projet sans révision marquée ; `current_remaining` sans révision en cours » ; `WorkloadPlan` : « la charge d'une ligne est répartie sur la durée de sa tâche au prorata des heures travaillées du calendrier de son rôle ; sur `marked_remaining` et `current_remaining`, la charge restante d'une tâche non terminée se répartit sur la seule part de la durée postérieure à la date de calcul (`context.computed_at`, la date de marquage pour une révision marquée), portée au mois de la date de calcul quand la fin est dépassée (WF-DEV-0070) » ; `WorkloadBasis` : « la charge de la révision de référence, la charge réestimée d'une révision marquée, celle de la révision en cours ». Un exemple `workload_marked_remaining` sur un projet en chiffrage.
- **DECISIONS.md** : l. 334-336 (EP-02/L7), antérieure et contredite ; l. 2022-2024 (EP-02/L24) décrit le générateur, pas le contrat.

#### L-17 — Un non-contributeur peut inscrire un chef de projet quand le compte du dernier est désactivé
- **majeur** ; **emplacement** : `docs/api/paths/projects.yaml:789-799` (`setContributors` : « réservée aux chefs de projet (WF-PRJ-0060, WF-ADM-0110) »), `docs/api/README.md` (Conventions : « 403 lorsque c'est l'écriture ou la qualité de contributeur »), `docs/api/components/common.yaml:393-396` (`NOT_CONTRIBUTOR`, `NOT_PROJECT_MANAGER`), `docs/api/components/schemas/projects.yaml:353` (`ProjectCommand.manage_contributors`) ; **exigence** : WF-PRJ-0060 (2026-10-09) : « {+Un projet non terminal compte toujours au moins un chef de projet : le retrait du dernier, ou son passage en participant, est refusé. Lorsque le compte du dernier chef de projet est désactivé (WF-ADM-0060), un utilisateur portant la permission de modifier FBS-4.2 et celle de consulter tous les projets peut y inscrire un chef de projet ; c'est la seule saisie ouverte à un non-contributeur.+} » ; **ce que dit le contrat** : `LAST_PROJECT_MANAGER` porte la première phrase ; rien ne porte la seconde — un non-contributeur reçoit 403 `NOT_CONTRIBUTOR` sur toute écriture, et `manage_contributors` n'est pas listée pour lui.
- **Constat.** Sans cette exception, un projet dont le seul chef de projet est désactivé n'a plus personne pour inscrire un chef de projet : il est orphelin pour toujours — c'est le cas que la spec a voulu fermer le 9 octobre. C'est une règle d'habilitation (403 ou non) et une commande à lister : à fixer avant le gel.
- **Proposition.** `setContributors` : « Réservée aux chefs de projet ; toutefois, lorsque aucun chef de projet du projet n'a de compte actif, un appelant qui porte la permission du paramétrage du projet (FBS-4.2) et « consulter tous les projets » l'exerce sans être contributeur, pour y inscrire un chef de projet — la seule écriture ouverte à un non-contributeur (WF-PRJ-0060) ; la liste envoyée doit alors porter au moins un chef de projet au compte actif ». `ProjectCommand.manage_contributors` listée à cet appelant dans ce seul cas, avec une condition qui dit pourquoi elle apparaît (`project_manager_active`, nouvelle) ; `Project.available_commands` : dire que les autres commandes ne lui sont pas listées. Exemple `contributors_set_orphan`.
- **DECISIONS.md** : l. 283-291 (EP-02/L7), l. 4189-4225 (EP-14/L42i) : aucune ne traite le dernier chef de projet désactivé.

#### L-18 — L'historique annulable est tenu par le front, dit la spec ; le contrat le tient côté serveur
- **majeur** ; **emplacement** : `docs/api/paths/revisions.yaml:1646-1700` (`undoLastChange` : « Annule les modifications de la session, une par une et dans l'ordre inverse, sur au moins cinquante niveaux » ; 409 « l'historique de la session est vide »), `:1700-1743` (`redoLastUndo`), `docs/api/components/schemas/revisions.yaml:1757-1789` (`UndoResult.remaining_depth`) ; **exigence** : WF-IHM-0110 (2026-10-10) : « L'historique annulable couvre au moins les cinquante dernières modifications {+faites par l'utilisateur dans la page ouverte ; il est tenu par le front, et ne survit ni à la fermeture ni au rechargement +}de la [-session-]{+page+}. » ; aussi : « ni sur les actions {+qui ont leur propre commande inverse ou sont définitives+} — marquage d'une révision,{+ abandon d'une révision en cours,+} fusion …, déclaration d'un risque survenu {+—, ni sur l'exclusion et la réintégration+} d'une ligne de coût, {+qui se défont par le geste inverse (WF-CRE-0030)+} ».
- **Constat.** La décision d'EP-02 (DECISIONS l. 8259-8261 : « L'annulation est une opération de la révision, `POST …/undo` et `POST …/redo`, pas un état du client ») est antérieure au 2026-10-10 et la spec dit désormais l'inverse : l'historique vit dans la page. Les deux ne sont pas incompatibles si l'API garde l'annulation comme écriture (« une annulation est une modification comme une autre ») mais que le front désigne ce qu'il annule ; or `undoLastChange` ne prend aucun corps : c'est le serveur qui sait quelle est « la dernière modification de la session », et `remaining_depth` compte un historique serveur. Avec la spec actuelle, un utilisateur qui recharge la page ne doit plus pouvoir annuler ce qu'il a fait avant ; avec le contrat, il le peut. Il faut trancher avant le gel : la forme de l'opération en dépend (corps ou non).
- **Proposition.** Question à l'auteur : la phrase « tenu par le front » est-elle une contrainte d'architecture (alors `undo`/`redo` prennent un corps qui désigne l'entrée à défaire — `{ change_id, lock_version }`, chaque écriture rendant un `change_id` — et `remaining_depth` disparaît) ou une description de l'expérience (alors le contrat garde la forme actuelle, et DECISIONS.md dit que la spec décrit l'écran, l'historique serveur étant borné à la session de la page) ? Dans les deux cas : ajouter « l'abandon d'une révision en cours » et « la réintégration d'une ligne de coût » à la liste des actions hors annulation de `undoLastChange` (l. 1657-1660), et citer C-363.
- **DECISIONS.md** : l. 8259-8261 (section « Collage et annulation », EP-02), antérieure et contredite dans sa lettre ; l. 6808-6811 (C-363) sur l'abandon.

#### L-19 — Les exports sont stockés jusqu'à leur premier téléchargement complet ou vingt-quatre heures
- **majeur** ; **emplacement** : `docs/api/paths/exchanges.yaml` (`requestExport` : « Le fichier est engendré à la demande et n'est pas stocké (WF-DAT-0120) »), `docs/api/components/schemas/exchanges.yaml:543-546` (`ExportRequest` : « engendré à la demande et transmis sans être stocké (WF-DAT-0120) »), `docs/api/paths/system.yaml` (`getBackgroundTaskResult` : « Le fichier est engendré à la demande et n'est pas stocké (WF-DAT-0120) » ; 409 générique) ; **exigence** : WF-DAT-0120 (2026-10-09) : « Le stockage objet porte [-deux-]{+trois+} compartiments : les fichiers en cours d'import, {+les fichiers exportés en attente de téléchargement,+} et les sauvegardes. … {+Un fichier exporté est supprimé à l'issue de son premier téléchargement complet, ou au terme de vingt-quatre heures s'il n'a pas été téléchargé ; un téléchargement interrompu le laisse en place.+} Aucun autre fichier n'y est [-conservé, et les exports sont engendrés à la demande sans y être stockés-]{+conservé+}. » ; Vérif : « {+Un export téléchargé jusqu'au bout n'est plus sur le stockage objet ; un téléchargement interrompu le laisse disponible ; un export jamais téléchargé en disparaît au terme de vingt-quatre heures.+} ».
- **Constat.** Trois descriptions disent, en citant WF-DAT-0120, la règle que WF-DAT-0120 a retirée le 9 octobre. L'opération ne change pas de forme, mais son cycle de vie si : un second `GET /tasks/{id}/result` après un téléchargement complet, ou après vingt-quatre heures, doit être refusé (404 ou 409, à nommer), et un téléchargement interrompu doit pouvoir reprendre ; l'écran du suivi des tâches de fond (`result_url`) doit savoir quand le lien meurt. La décision EP-02/L38 (l. 2558-2576, « se télécharge en flux ») est antérieure et portait sur le front.
- **Proposition.** Les trois descriptions : « Le fichier est produit par la tâche et conservé sur le stockage objet jusqu'à son premier téléchargement complet, ou vingt-quatre heures s'il n'est pas téléchargé ; un téléchargement interrompu le laisse disponible (WF-DAT-0120) ». `getBackgroundTaskResult` : déclarer le refus d'un résultat déjà téléchargé ou expiré — 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `result_available` (condition nouvelle), ou 404 — et `BackgroundTaskRef.result_url` : « nul une fois le résultat téléchargé ou expiré ». Exemple `task_result_expired`.
- **DECISIONS.md** : l. 2558-2576 (EP-02/L38), antérieure ; l. 747, 2119, 4365, 4654 ne traitent que les dépôts d'import ; aucune décision sur la rétention des exports.

#### L-20 — L'abandon de l'unique révision laisse le projet sans révision, et supprime les risques que plus rien n'évalue
- **mineur** ; **emplacement** : `docs/api/paths/revisions.yaml:130-135` (`abandonRevision` : « Le projet revient à son état à la dernière révision marquée, et les lignes de la révision abandonnée sont supprimées ») ; **exigence** : WF-REV-0010 (2026-10-09) : « {+Lorsqu'il n'existe aucune révision marquée, l'abandon laisse le projet sans révision ; il reste à l'état Chiffrage (WF-CYC-0020), et une nouvelle révision peut être créée.+} » ; WF-DAT-0080 (2026-10-09) : « {+Un risque qu'aucune révision, marquée ou en cours, n'évalue plus est supprimé avec l'abandon de la révision qui l'avait créé.+} » ; WF-DAT-0130 : « {+l'abandon de la révision en cours présente à la lecture suivante les indicateurs de la dernière révision marquée au jour courant+} ».
- **Constat.** La description suppose une révision marquée ; sur un projet en chiffrage sans aucune, « revient à son état à la dernière révision marquée » ne veut rien dire, et l'écran doit savoir que le projet reste à Chiffrage avec `create_revision` disponible. La suppression physique des risques créés dans la révision abandonnée (et de leurs structures propres) n'est dite nulle part : `listRisks` après abandon ne doit plus les rendre.
- **Proposition.** `abandonRevision` : « … Lorsque le projet n'a aucune révision marquée, l'abandon le laisse sans révision, à l'état Chiffrage, et `create_revision` redevient disponible (WF-REV-0010). Les risques que la révision abandonnée avait créés et qu'aucune révision marquée n'évalue sont supprimés avec elle, avec leur devis propre (WF-DAT-0080) ; les indicateurs au jour courant se lisent ensuite dans la dernière révision marquée (WF-DAT-0130) ». Exemple `project` relu après abandon sans révision.
- **DECISIONS.md** : l. 6808-6811 (C-363) sur l'irréversibilité seulement ; aucune sur ces deux règles.

#### L-21 — La mise à jour des taux : présentée à la demande, appliquée projetée par les créations indirectes
- **mineur** ; **emplacement** : `docs/api/paths/revisions.yaml:255-258` (`getRateUpdateProposal` : « Présenté à la création d'une révision lorsque le référentiel a changé »), `docs/api/components/schemas/revisions.yaml:236-243` (`RateUpdateProposal`, idem), `:203-208` (`RevisionCreate.apply_rate_update`) ; `paths/exchanges.yaml` (`applyImport`) et `paths/risks.yaml` (`createRisk`, `declareRiskOccurrence`) ne disent rien des taux de la révision qu'ils créent ; **exigence** : WF-REV-0060 (2026-10-10) : « {+Cette présentation est faite à la création lorsque l'utilisateur la demande lui-même ; lorsque la révision est créée par un import (WF-INTF-0090), une saisie de risque (WF-RIS-0020) ou une survenance (WF-RIS-0060), les taux conservés, projetés jusqu'à la nouvelle année de référence, sont appliqués. Dans tous les cas, la présentation reste proposée depuis la révision en cours tant qu'elle n'est pas marquée+} … Une catégorie{+ non encore présentée,+} refusée, ou sans taux … conserve son taux précédent, projeté ».
- **Constat.** `applyRateUpdate` dit déjà l'acceptation ultérieure (C-362) et `mergeCostStructure` dit les taux projetés pour la fusion sans révision en cours (#790) ; mais la proposition se décrit encore comme un moment de la création, et les trois autres créations indirectes ne disent pas qu'elles chiffrent aux taux projetés — un implémenteur de l'import pourrait appliquer les taux du référentiel. Descriptions seulement ; `RevisionCommand.apply_rate_update` est pris par US-0640/L6.
- **Proposition.** `getRateUpdateProposal`/`RateUpdateProposal` : « Lisible sur toute révision en cours dont l'année de référence diffère de celle de la révision copiée, à sa création comme ensuite, tant qu'elle n'est pas marquée ; `source` dit, catégorie par catégorie, ce que la révision porte aujourd'hui (`inflated_previous` tant que la mise à jour n'est pas acceptée) ». `applyImport`, `createRisk`, `declareRiskOccurrence` : « La révision en cours qu'ils créent est chiffrée aux taux conservés, projetés jusqu'à l'année courante (WF-REV-0060) ; la mise à jour reste proposée depuis elle ».
- **DECISIONS.md** : l. 6790 (C-362) et l. 8206-8208 (#790) : portent l'acceptation ultérieure et la fusion ; rien sur l'import, le risque et la survenance.

#### L-22 — « ni révision marquée postérieure » : la règle ancienne reste dans deux descriptions
- **mineur** ; **emplacement** : `docs/api/paths/revisions.yaml:199-201` (`designateReferenceRevision` : « tant que le projet n'a ni coût réel ni révision marquée postérieure »), `docs/api/components/schemas/revisions.yaml:227-229` (`ReferenceDesignation`, idem) ; le 409 (l. 235-238) et `CommandCondition.reference_correctable` disent « depuis la dernière désignation » ; **exigence** : WF-REV-0040 Vérif : « ni révision marquée [-postérieure à-]{+depuis+} la [-référence-]{+dernière désignation+} … {+Un projet dont les offres v2 puis v3 sont marquées, et dont v2 a été désignée par erreur, accepte la désignation de v3 tant qu'il n'a reçu aucun coût réel.+} ».
- **Constat.** Les deux règles diffèrent sur l'exemple de la spec (v3 marquée après v2, v2 désignée ensuite par erreur : correctible selon la spec, pas selon « postérieure ») ; le contrat se contredit lui-même entre description et 409.
- **Proposition.** Aligner les deux phrases sur le 409 : « tant que le projet n'a reçu aucun coût réel et qu'aucune révision n'a été marquée depuis la dernière désignation ».
- **DECISIONS.md** : EP-15/US-0490 (l. 6813-6830) a écrit le 409 ; les descriptions n'ont pas suivi.

#### L-23 — Le squelette : une feuille automatique d'un jour par livrable
- **mineur** ; **emplacement** : `docs/api/paths/revisions.yaml:1751-1754` (`generatePlanningSkeleton` : « une feuille par livrable, un jalon de fin par poste et par lot, avec leurs liaisons »), `fixtures/api/skeleton_generated.json` (lotissement par défaut, sans livrable) ; **exigence** : WF-PRJ-0030 (2026-10-09/10) : « une tâche feuille par livrable,{+ en mode automatique et d'une durée d'un jour (WF-PLA-0160), sous la récapitulative de son poste ; un jalon de fin par poste, sous la récapitulative du poste,+} … {+Le jalon de fin de poste a pour prédécesseurs les livrables de son poste,+} et le jalon de fin de lot … les jalons de fin de ses postes ».
- **Constat.** La durée et le mode de la feuille, et le sens des liaisons, ne sont dits que dans la spec ; le seul exemple n'a pas de livrable. Un implémenteur devinerait la durée.
- **Proposition.** Compléter la description (feuille automatique d'un jour, sous la récapitulative du poste ; jalon de poste prédécédé des livrables ; jalon de lot prédécédé des jalons de poste) et ajouter un exemple sur le lotissement saisi du témoin (`work_breakdown_entered`).
- **DECISIONS.md** : EP-14/L42k (l. 5214-5290) décrit le squelette avant la réécriture de WF-PRJ-0030 ; rien sur la durée d'un jour.

#### L-24 — L'écart au devis de référence : révision affichée, provisions comprises de part et d'autre
- **mineur** ; **emplacement** : `docs/api/components/schemas/indicators.yaml:161-166` (`EstimateIndicators.delta_to_reference` : « L'écart entre le devis en cours et celui de la révision de référence … le devis en cours moins celui de la référence ») ; **exigence** : WF-DEV-0060 (2026-10-10) : « l'écart entre le {+total du +}devis [-en cours-]{+de la révision affichée+} et celui de la [-référence-]{+révision de référence, lignes de provision comprises de part et d'autre+} ».
- **Constat.** `getEstimateIndicators` prend `revision_id` : sur une révision marquée, l'écart est celui de cette révision, pas « du devis en cours » ; et la description ne dit pas si les lignes de provision entrent dans les deux termes (elles entrent dans `total`, somme de `base_amount`). Clarté.
- **Proposition.** « L'écart entre le total du devis de la révision lue (`context.revision_id`) et celui de la révision de référence, lignes de provision comprises de part et d'autre (WF-DEV-0060) ».
- **DECISIONS.md** : l. 481 (EP-02/L8), l. 1546 (EP-02/L35) : le sens de l'écart seulement.

#### L-25 — Une commande que la qualité ne permet pas est présentée indisponible en nommant cette qualité
- **mineur** ; **emplacement** : `docs/api/components/schemas/projects.yaml:61-72` (`Project.available_commands` : « Commandes du projet que l'appelant a la permission d'exercer … Une commande absente de la liste n'est pas présentée »), `:93-99` (`CommandCondition` : `is_project_manager` décrite, `is_contributor` dans l'énumération sans description) ; **exigence** : WF-IHM-0090 (2026-10-10) : « {+Une commande que la qualité de l'utilisateur sur le projet ne permet pas — non-contributeur, ou participant pour une action réservée aux chefs de projet (WF-PRJ-0060) — est présentée indisponible, en nommant cette qualité.+} ».
- **Constat.** Le contrat porte les deux conditions mais ne dit pas quand `is_contributor` manque : un lecteur qui ouvre un projet par « consulter tous les projets » doit voir les commandes de saisie qu'il a la permission d'exercer, indisponibles, `is_contributor` manquante. Rien ne le dit ; l'exemple `project_reader.json` existe sans que la règle soit écrite.
- **Proposition.** Dans `CommandCondition` : « `is_contributor` manque à qui ouvre le projet par « consulter tous les projets » sans en être contributeur, pour toute commande que sa permission lui donnerait : elle est listée indisponible, la qualité nommée (WF-IHM-0090) ». Vérifier `project_reader.json`.
- **DECISIONS.md** : l. 1321 (EP-02/L29) et l. 137 : le principe, sans `is_contributor`.

#### L-26 — La lignée fonde aussi le rapprochement des imports
- **mineur** ; **emplacement** : `docs/api/components/schemas/revisions.yaml:474-477` (`Node` : « `lineage_id` est stable d'une révision à l'autre et fonde la comparaison, le diagramme temps/temps et les inscriptions aux suivis (WF-DAT-0030) ») ; **exigence** : WF-DAT-0030 : « {+et le rapprochement des imports (WF-INTF-0040, WF-INTF-0100, WF-INTF-0120) +}s'appuient sur l'identifiant de lignée ».
- **Constat.** `ImportDifference` et `ImportRejection` nomment déjà les objets par leur lignée ; la description du nœud n'en dit rien. Clarté.
- **Proposition.** Ajouter « et le rapprochement des imports (WF-INTF-0040, WF-INTF-0100, WF-INTF-0120) ».
- **DECISIONS.md** : aucune.

### Ce qui est juste

Vérifié et conforme à la spec actuelle : WF-CYC-0120 (`ReferenceReadiness.missing` : `active_cost_category` de main-d'œuvre et `active_provision_category`, Vérif de l'installation neuve) ; WF-CYC-0030 (`LifecycleTrigger`, `revision_has_tasks_and_lines`, ordre indifférent) ; WF-REV-0040 dans son 409 (`reference_correctable`) ; WF-PRJ-0010, WF-PRJ-0080 (`client`, US-0610), WF-PRJ-0020 (lots/postes/livrables), WF-PRJ-0050 (`DeclaredSubprojectCode`, 31 caractères, noms réservés, `SUBPROJECT_HAS_ACTUAL_COSTS`, `subproject_without_estimate_lines` avec `params.estimate_lines`) ; WF-PLA-0010 (`params.projects` par libellé et code, rejet de la ligne importée) ; WF-PLA-0050 (`task_without_lines` hors provision, `enter_remaining`) ; WF-PLA-0150 (horizon à la fusion, #788) ; WF-PLA-0160 (`setDurationUnits`, C-360 ; les suffixes et le nombre sans suffixe relèvent du front) ; WF-PLA-0170 (rattachement, `setWorkBreakdown`, poste déplacé) ; WF-DEV-0010 (`MissingRate` : catégories de main-d'œuvre employées) ; WF-DEV-0050 (`project_before_in_progress` sur `edit_estimate`, C-358 ; tâche créée depuis le devis : feuille automatique d'un jour ; filtres par lot et poste ; `task_not_completed`) ; WF-IHM-0050 (collage partiel, L42q) ; WF-IHM-0060 (`GridPreferences.page_size`, C-351) ; WF-IHM-0130 (calendriers sans bornes d'heures, US-0530) ; WF-DAT-0090 (unicités `ALREADY_EXISTS` des codes, du libellé de calendrier, du code comptable) ; WF-DAT-0110 (triplet pièce/poste, US-0630) ; WF-REV-0100 pour les structures copiées et les commandes de phase ; WF-REV-0050 pour le compte rendu préalable, la fusion sans révision en cours et les motifs de refus (hors L-14).

### Doutes

- **WF-DAT-0040 et `IndicatorsRevision`** (`components/parameters.yaml:341-357`) : la description dit que « les courbes, que rien ne conserve, sont recalculées à cette date, `is_stored` faux », alors que WF-DAT-0040 conserve désormais les séries des courbes « au pas du mois », la charge par rôle et par mois, les totaux par nature et par nœud, et les risques, « ce que lisent, à une date passée, le plan de charge agrégé, la structure des coûts et les risques du portefeuille ». La première passe a relevé « au pas du mois » (WF-IND-0100/0110) ; je ne le recopie pas, mais `IndicatorsRevision`, `AsOf` et l'en-tête de `schemas/portfolio.yaml` (« lisent les indicateurs conservés ») devraient être relus avec ce constat : `PortfolioWorkload`, `PortfolioCostStructure` et `PortfolioRisks` ne disent pas qu'à `as_of` passé ils lisent des valeurs conservées plutôt que des tâches et des lignes (Vérif : « ne lit de ligne de tâche ni de ligne de devis »).
- **WF-DEV-0030 / WF-PRJ-0040** : « une ligne de provision n'est pas projetée » ; `EstimateLineFacet.inflated_amount` n'excepte pas la provision, et le témoin ne porte pas de ligne de provision avec une année de consommation postérieure à la référence pour le vérifier. Si L-01 est tranché dans le sens de la spec, cette règle doit être dite avec lui.
- **WF-IHM-0070** : « lignes propres hors provision d'une récapitulative dont toutes les subordonnées sont terminées » doivent être signalées dans la grille de reste à engager ; aucun champ ne le dit (`EstimateLineFacet.remaining_entry` dit seulement si la saisie est ouverte). La phrase existait avant la période ; seul l'endroit du signalement a changé. À confirmer par la famille RAE.
- **WF-DAT-0130** : la liste des écritures qui invalident le cache et la non-disponibilité de la session du front pendant une indisponibilité du cache n'ont pas de surface d'API (`COMPONENT_UNAVAILABLE`, `component: cache` existe) ; je les tiens pour sans surface.
- **WF-REV-0060** « une catégorie non encore présentée » : `RateUpdateProposal.source` (`reference_rate`, `inflated_previous`) suffit-il à distinguer « refusée » de « jamais présentée » ? La spec les traite de même ; aucun constat.

### Relevé

| Exigence | Verdict |
|---|---|
| WF-CYC-0120 | porté |
| WF-CYC-0030 | porté |
| WF-CYC-0060 | non porté (L-03) |
| WF-CYC-0090 | non porté (L-02) |
| WF-REV-0010 | non porté (L-20, mineur) ; copie des structures et taux projetés portés |
| WF-REV-0040 | porté (409) ; description ancienne (L-22, mineur) |
| WF-REV-0050 | non porté (L-14) ; compte rendu, fusion sans révision en cours, refus : portés |
| WF-REV-0060 | décision (C-362, #790) pour l'acceptation ultérieure et la fusion ; non porté pour l'import, le risque, la survenance (L-21, mineur) |
| WF-REV-0070 | non porté (L-04) |
| WF-REV-0080 | non porté (L-15) ; marques par nœud et parent : portées |
| WF-REV-0090 | non porté (L-04) |
| WF-REV-0100 | non porté pour la date de début de planning (L-06) ; structures copiées : porté |
| WF-PRJ-0010 | porté |
| WF-PRJ-0080 | porté (US-0610) |
| WF-PRJ-0020 | porté (EP-15/US-0450) |
| WF-PRJ-0030 | porté ; description incomplète (L-23, mineur) |
| WF-PRJ-0040 | porté ; provision non projetée : voir L-01 et Doutes |
| WF-PRJ-0050 | porté (US-0610, L42q, C-359) |
| WF-PRJ-0060 | non porté pour le non-contributeur (L-17) ; `LAST_PROJECT_MANAGER` porté |
| WF-PLA-0010 | porté (L42r, L42s) |
| WF-PLA-0020 | non porté (L-06, L-07) ; `NON_WORKING_DAY` porté (#1271) |
| WF-PLA-0030 | non porté (L-08) |
| WF-PLA-0160 | porté (C-360) ; suffixes et nombre sans suffixe : sans surface |
| WF-PLA-0040 | non porté (L-09) ; lignes de provision hors reste : porté (`task_without_lines`) |
| WF-PLA-0050 | porté |
| WF-PLA-0070 | non porté (L-11) |
| WF-PLA-0130 | non porté (L-13) ; rattachement déplacé vers WF-PLA-0170 : porté |
| WF-PLA-0150 | porté (#788) |
| WF-PLA-0080 | non porté (L-12) ; filtres par lot et poste, `is_critical` : portés |
| WF-PLA-0100 | non porté (L-10) |
| WF-PLA-0120 | sans surface (mise en page de l'image) ; `depth` porté |
| WF-DEV-0010 | porté |
| WF-DEV-0020 | non porté (L-01) ; délai de paiement, catégorie du rôle, provision réservée : portés |
| WF-DEV-0060 | porté (lots) ; écart : description (L-24, mineur) |
| WF-DEV-0050 | non porté pour les montants (L-01) ; phase, tâche créée, filtres, tâche terminée : portés |
| WF-DEV-0030 | non porté (L-01) ; provision non projetée : Doutes |
| WF-DEV-0080 | forme |
| WF-DEV-0070 | non porté (L-16) |
| WF-IHM-0010 | forme |
| WF-IHM-0020 | non porté (L-05) ; structure lue : porté (`CostStructure.kind`) |
| WF-IHM-0050 | porté (L42q) |
| WF-IHM-0060 | porté (C-351) |
| WF-IHM-0070 | porté pour les signalements que le contrat connaît ; conflit manuel : L-07 ; lignes ouvertes d'une récapitulative : Doutes |
| WF-IHM-0090 | non porté pour la qualité nommée (L-25, mineur) |
| WF-IHM-0110 | décision antérieure contredite (L-18) |
| WF-IHM-0130 | porté (calendriers) ; export des images : sans surface |
| WF-IHM-0140 | forme |
| WF-DAT-0080 | porté (sous-projets, lots, postes, chronologies) ; risque supprimé à l'abandon : L-20 |
| WF-DAT-0090 | porté (unicités) ; cascade et clés : sans surface |
| WF-DAT-0010 | sans surface (copie des évaluations de risque, implicite dans `createRevision`) |
| WF-DAT-0030 | porté ; description (L-26, mineur) |
| WF-DAT-0040 | déjà relevé en première passe (« au pas du mois ») ; portefeuille à date passée : Doutes |
| WF-DAT-0110 | porté (US-0630) |
| WF-DAT-0120 | non porté (L-19) ; dépôts d'import : porté |
| WF-DAT-0130 | sans surface |
| WF-DAT-0140 | sans surface |
| WF-PLA-0170 | porté (L42k, L42s, EP-15) |

## Annexe M — Delta de la spécification — risques, reste à engager, coûts réels, indicateurs, portefeuille, référentiel


Lu : `BRIEF.md`, `BRIEF-DELTA.md`, `spec-diff-group3.md` (43 exigences, dont WF-REF-0190 nouvelle) ; dans la
spécification, les corps de WF-DEV-0030 et WF-DAT-0040 (groupe 2, pour recouper WF-IND-0010) ; le contrat :
`paths/risks.yaml` (478 l.), `paths/costs.yaml` (163), `paths/portfolio.yaml` (286), `paths/analysis.yaml` (453),
`paths/reference.yaml` (1894) en entier ; `paths/revisions.yaml` l. 99–195 (`getRevision`, `abandonRevision`,
`markRevision`), 912–975 (`deleteNode`), 1252–1370 (`setTaskProgress`, `setLineRemaining`) ; les schémas
`risks.yaml`, `costs.yaml`, `portfolio.yaml`, `indicators.yaml`, `reference.yaml` en entier, `revisions.yaml`
(`Revision`, `RevisionSnapshot`, `StructureCommand`, `KanbanTask`/`KanbanCommand`, `TaskFacet.physical_progress`,
`EstimateLineFacet`, `ProgressUpdate`, `RemainingUpdate`) ; `parameters.yaml` (`RiskRevision`, `IndicatorsRevision`,
`AsOf`, `Scope`, `PortfolioStates`, `PortfolioFrom`) ; `exchanges.yaml` (l. 200–215, 480–530, `ImportIgnoredKind`,
`ActualCostColumn`) ; `INVENTORY.md` ; `DECISIONS.md` par grep ciblé (une soixantaine de passages lus) ;
`docs/roadmap/EP-16-maquette-durcissement.md` l. 30–160 ; les générateurs `mockportfolio.py` (l. 365–450),
`mockindicators.py` (l. 447–456). Fixtures ouvertes : 17 (`portfolio_performance`, `portfolio_risks`,
`portfolio_value`, `portfolio_cost_curve`, `portfolio_cost_structure`, `milestone_tracking`, `cost_curve`,
`cost_curve_payment_delays`, `actual_costs`, `index_history`, `project_indicators_marked`, `remaining_indicators`,
`nodes_risk_occurred`, `nodes_estimate`, `nodes_core`, `risks`, `structures`). Les constats de la première passe
(`findings-A` à `-J`) ont été relus sur les mêmes thèmes pour ne rien recopier : sont écartés ici ce que portent
déjà H-01/H-02 (coût à la survenance), H-05 (`deleteNode` et la tâche porteuse), G-06/H-10 (couverture « en cours et
terminés »), G-07 (sens de la marge, #466), G-09 (« antérieure ou égale »), G-15 (budget agrégé avec provisions),
I-02 et D-07 (élément d'OTP, barre oblique), C-04/H-06 (assiette des bornes), E-13 (409 de l'abandon).

### Synthèse

| # | Gravité | Emplacement | Constat (une ligne) | Exigence |
|---|---|---|---|---|
| M-01 | majeur | `schemas/risks.yaml:473-507` (`ProvisionTotals.reserve`, `RiskCoverageTotals.reserve`), `schemas/revisions.yaml:1356-1364` (`EstimateLineFacet.budgeted_amount`), `paths/risks.yaml:428-436` | La réserve pour risques est partout « la réserve de la révision de référence », somme de ses lignes de provision ; la spec en fait désormais un cumul à travers les références (les survenus et écartés d'avant la nouvelle référence y restent), et l'avenant qui intègre les lignes d'un survenu ne touche pas la couverture | WF-RIS-0050 |
| M-02 | majeur | `parameters.yaml:341-358` (`IndicatorsRevision`), `paths/analysis.yaml:303-308` (`getCostCurve`), `:371-375` (`getEarnedValueCurves`), `schemas/indicators.yaml:115-119` (`CalculationContext.is_stored`) | Les courbes d'une révision marquée sont dites « recalculées … sur les lignes de coût réel connues aujourd'hui », `is_stored` faux ; la spec dit l'inverse : coût réel = lignes connues au marquage telles qu'elles étaient, courbes conservées avec les indicateurs ; décisions #247 et #365 antérieures et contredites | WF-IND-0010 (WF-DAT-0040) |
| M-03 | majeur | `parameters.yaml:341-366` (`IndicatorsRevision`, `AsOf`), `paths/analysis.yaml:215-226`, `:416-426` (`getIndexHistory`), `schemas/indicators.yaml:581-594` (`IndexHistoryPoint`), `schemas/portfolio.yaml:1-4` | Sur un projet sans révision en cours, les indicateurs au jour courant « se calculent sur sa dernière révision marquée, avec le coût réel au jour courant », le dernier point de l'évolution et la contribution au portefeuille aussi ; le contrat ne dit que « la révision en cours » (`RiskRevision` l. 275-283 porte la règle pour les risques, pas les indicateurs) | WF-IND-0010, WF-IND-0130, WF-PTF-0010 |
| M-04 | majeur | `paths/revisions.yaml:127-148` (`abandonRevision`), `paths/risks.yaml:388-399` (`declareRiskOccurrence`), `schemas/risks.yaml:3-8` (`RiskState`), `:328-336` (`RiskOccurrence`) | L'abandon de la révision en cours ramène les risques à l'évaluation de la dernière révision marquée (créé → disparaît, survenu → identifié avec sa provision) et « seul l'abandon défait » la survenance ; le contrat dit « Définitif » sans exception et l'abandon ne parle que des lignes | WF-RIS-0020, WF-RIS-0060 |
| M-05 | majeur | `paths/risks.yaml:388-399` (`declareRiskOccurrence`), `schemas/risks.yaml:328-340` (`RiskOccurrence`), `fixtures/api/nodes_risk_occurred.json:6-10` | La place et l'état des tâches fusionnées (sous la tâche porteuse en dernière position, liaisons/durées/modes conservés, mode manuel sans prédécesseur, cas du jalon porteur, grandeurs conservées et réestimé recalculé) ne sont pas décrits ; la fixture rend les tâches fusionnées en mode `automatic` | WF-RIS-0060 |
| M-06 | majeur | `schemas/indicators.yaml:522-531` (`CurveSeries.cash_out_by_month`), `:533-544` (`CashOutMonth`), `paths/analysis.yaml:295-301` (`getCostCurve`) | « Le passé par mois de date de pièce décalée » : la spec dit « le coût réel n'est pas décalé » (la fixture ne le décale pas) ; l'étalement du reste à engager est encore « sur les dates de la révision courante », sans la part postérieure à la date de calcul ni le report entier d'une tâche dont la fin est dépassée | WF-IND-0100 |
| M-07 | majeur | `paths/portfolio.yaml:224-233` (`getPortfolioCostCurve`), `schemas/portfolio.yaml:200-215` (`PortfolioCostStructure`), `:219-253` (`PortfolioRisks`), `:261-275` (`PortfolioCostCurve`) ; `DECISIONS.md:2196-2201` | La contribution d'un projet en chiffrage — devis pondéré **hors provisions** pour le budget, **provisions comprises** pour le reste à engager et la projection, risques **non pondérés** — n'est portée nulle part ; le « choix déclaré » d'EP-02/L26 (budget = projection = devis pondéré) dit l'inverse de la spec | WF-PTF-0020, WF-PTF-0080, WF-PTF-0090, WF-PTF-0100 |
| M-08 | majeur | `schemas/revisions.yaml:1365-1367` (`EstimateLineFacet.reestimated_amount`), `schemas/indicators.yaml:191-203` (`RemainingIndicators`) ; `DECISIONS.md:1974-1977`, `:2355-2356` | Le reste à engager d'une tâche non démarrée non réestimée se calcule « depuis les grandeurs de la référence, aux taux conservés par la révision courante », sur l'année de consommation courante (150 h après l'avenant) ; le contrat ne dit rien du réestimé d'une ligne non réestimée, et les décisions disent « le budgété projeté » | WF-RAE-0010, WF-RAE-0040 |
| M-09 | majeur | `schemas/indicators.yaml:223-230` (`RemainingIndicators.delta_to_previous_revision`) ; `DECISIONS.md:1530-1533` | « Nul sans revue précédente » : la spec ne compte que la révision marquée précédente **marquée à l'état En cours** ; une offre marquée en chiffrage ne fait pas une revue précédente | WF-RAE-0020 |
| M-10 | majeur | `fixtures/api/milestone_tracking.json:7`, `schemas/indicators.yaml:432-452` (`MilestoneTracking`), `paths/analysis.yaml:267-273` | La fixture donne un point à la révision marquée le 15 décembre 2025, en chiffrage, quand « les révisions marquées avant l'état En cours ne donnent aucun point » ; la description ne dit ni le dernier point au jour courant (révision en cours ou dernière marquée) ni l'arrêt à la terminaison | WF-IND-0090 |
| M-11 | majeur | `schemas/revisions.yaml:1222-1229` (`TaskFacet.physical_progress`), `schemas/indicators.yaml:291-293` (`ProjectIndicators.earned_value`), `:231-243` (`SubprojectBalance.budget`) | L'avancement physique d'une récapitulative garde l'ancienne formule (« montants budgétés portés par les tâches terminées … au total budgété du sous-arbre »), qui compte les lignes de provision que la spec exclut désormais au numérateur et au dénominateur, lignes propres comprises ; la valeur acquise et le budget d'un sous-projet ne disent pas « hors lignes de provision » | WF-IND-0060, WF-IND-0030, WF-IND-0020 |
| M-12 | mineur | `schemas/reference.yaml:590-597` (`CostCategoryImage.accounting_code`) | « N'intervient dans aucun calcul ni dans aucun import » : la spec dit « ni dans l'import des coûts réels … ; les fichiers de devis et de reste à engager désignent la catégorie d'une ligne hors main-d'œuvre par ce code (annexe B) » | WF-REF-0040 |
| M-13 | mineur | `schemas/reference.yaml:852-860` (`IndexThresholds`), `:1040-1045` (`AlertZone`), `schemas/indicators.yaml:322-330` (`IndexValue`) | Les bornes des zones sont désormais fermées/ouvertes (« supérieur ou égal au seuil de vigilance → nominal ; … ≥ alerte → vigilance ») ; le contrat ne le dit pas, alors qu'il le dit pour les niveaux de la matrice (`RiskMatrixLevel`) | WF-REF-0170 |
| M-14 | mineur | `schemas/indicators.yaml:322-330` (`IndexValue.zone`), `:581-594` (`IndexHistoryPoint`), `:103-120` (`CalculationContext.is_stored`) | « Une révision marquée est toujours lue avec [les seuils et bornes] courants … seule la zone qui [qualifie ses indicateurs] peut changer » : rien ne dit que `zone` d'un indice conservé est recalculée à la lecture et non conservée | WF-REF-0130 |
| M-15 | mineur | `schemas/portfolio.yaml:87-89` (`PortfolioValue.conversion_rate`), `schemas/indicators.yaml:83-85`, `:99` (`no_offer_out_of_pricing`) | Le taux de transformation compte les offres « sorties de Chiffrage vers En cours ou vers Perdu » ; une offre abandonnée ne compte pas — le motif « aucune offre n'est sortie de l'état Chiffrage » et le champ ne le disent pas | WF-PTF-0050 |
| M-16 | mineur | `schemas/portfolio.yaml:156-199` (`PortfolioPerformance.projections`), `paths/portfolio.yaml:142-150` | La projection au rythme constaté agrégée vaut « le budget de référence agrégé divisé par l'indice de coût agrégé », non calculable avec lui, les deux autres étant des sommes ; le générateur le fait (`mockportfolio.py:422-438`), le contrat ne le dit pas | WF-PTF-0070 |

#### M-01 — La réserve pour risques n'est plus la somme des provisions de la référence
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/risks.yaml:473-487` (`ProvisionTotals`, « la
  réserve pour risques de la révision de référence »), `:489-507` (`RiskCoverageTotals.reserve`, « la réserve pour
  risques de la révision de référence »), `:46-51` (`Risk.provision_amount`, « celle que portait la révision de
  référence compte à la réserve ») ; `docs/api/components/schemas/revisions.yaml:1356-1364`
  (`EstimateLineFacet.budgeted_amount` : « Une ligne de provision porte la provision qu'elle avait dans la révision de
  référence : ce montant compte à la réserve pour risques ») ; `docs/api/paths/risks.yaml:428-436`
  (`getProjectRiskCoverage`) ; **exigence** : WF-RIS-0050 `{+À chaque nouvelle référence, la réserve conserve la
  provision que portaient, dans la référence précédente, les risques survenus ou écartés avant elle, et s'augmente de
  celle des risques identifiés que la nouvelle référence porte. Un avenant qui intègre au budget de référence les
  lignes d'un risque survenu rétablit l'indice de coût, sans toucher la couverture : la provision de ce risque a été
  consommée à sa survenance, et son coût y reste compté.+}` ; Vérif : `{+un avenant qui ne touche pas aux risques
  laisse la réserve à 60 … un avenant qui intègre au budget de référence les lignes de ce risque porte le budget à
  1 250 et laisse la réserve à 60 et l'écart à −190 ; un avenant qui déclare un nouveau risque de provision 50 porte
  la réserve à 110+}`.
- **Ce que dit le contrat.** La réserve est définie par la seule révision de référence courante : « La révision de
  référence conserve, comme réserve pour risques, la somme de ses lignes de provision » (phrase que la spec garde),
  et chaque description la rattache à « la révision de référence ». DECISIONS l. 1928 : « la réserve de la référence,
  910, somme de ses lignes de provision ».
- **Constat.** Après la survenance de 752 (provision 60 dans la référence 101), un avenant 2 qui ne touche pas aux
  risques fait une nouvelle référence sans ligne de provision pour 752 : par le contrat, la réserve retombe de 60 à 0
  et l'écart de couverture de −190 à −250 ; par la spec, la réserve reste 60 et l'écart −190. Même chose pour un
  risque écarté avant la nouvelle référence. La règle est un calcul du service, mais toutes les descriptions qui
  servent de spécification au service disent l'ancienne, et l'écran lira « la réserve de la révision de référence »
  faux. Avant le gel parce que la réserve n'a pas de champ propre : la corriger ensuite ne rompt rien, mais la
  description fait foi pour l'implémenteur.
- **Proposition.** Dire la règle une fois sur `RiskCoverageTotals.reserve` et y renvoyer depuis `ProvisionTotals.reserve`
  et `EstimateLineFacet.budgeted_amount` :
  ```yaml
  reserve:
    allOf: [{ $ref: ../common.yaml#/Money }]
    description: >-
      La réserve pour risques de la révision de référence (WF-RIS-0050) : la somme des provisions
      des risques identifiés qu'elle porte, augmentée de la provision que portaient, dans la
      référence précédente, les risques survenus ou écartés avant elle — un avenant ne la diminue
      jamais, même quand il intègre au budget les lignes d'un risque survenu.
  ```
  Revoir l'exemple de la Vérif (réserve 60 → 110 au second avenant) dans `risk_coverage` si l'univers témoin gagne un
  avenant 2 fusionné (il en a un non fusionné : `structures.json`, « Avenant 2 — reprise des essais »).
- **DECISIONS.md** : « Révision de la spécification du 2026-10-04 » (l. 1149-1156) et « Le total général des
  provisions est rendu, et la réserve en regard » (l. 590-595), toutes deux antérieures (décisions du 2026-10-06),
  disent la réserve de la seule révision de référence. Aucune entrée après le 2026-10-09 sur la réserve.

#### M-02 — Les courbes d'une révision marquée sont conservées, et son coût réel est celui connu au marquage
- **gravité** : majeur ; **emplacement** : `docs/api/components/parameters.yaml:341-358` (`IndicatorsRevision` :
  « les courbes, que rien ne conserve, sont recalculées à cette date, `is_stored` faux, sur les lignes de coût réel
  connues aujourd'hui dont la date de pièce lui est antérieure ou égale (WF-IND-0010) : une pièce datée d'avant le
  marquage mais importée après compte dans la courbe et non dans les indicateurs conservés ») ;
  `docs/api/paths/analysis.yaml:303-308` (`getCostCurve`, même phrase), `:371-375` (`getEarnedValueCurves`) ;
  `docs/api/components/schemas/indicators.yaml:115-119` (`CalculationContext.is_stored`) ; **exigence** :
  WF-IND-0010 `{+Pour une révision marquée, ce sont les lignes connues à son marquage, telles qu'elles étaient
  alors : une ligne importée ensuite n'y entre pas, quelle que soit sa date de pièce, et une ligne mise à jour ou
  exclue ensuite y reste avec le montant et le périmètre qu'elle avait au marquage. Les courbes d'une révision
  marquée (WF-IND-0100, WF-IND-0110) sont conservées avec ses indicateurs (WF-DAT-0040).+}` ; Vérif :
  `{+l'import d'une ligne de coût datée avant le marquage, qui n'entre ni dans son coût réel ni dans ses courbes+}`.
- **Constat.** Le contrat décrit exactement le cas que la spec interdit (la pièce antidatée importée après compte
  dans la courbe) et un comportement divergent entre indicateurs et courbes que la spec supprime. `is_stored` n'a
  plus de raison d'être faux pour une révision marquée : la valeur et la sémantique du champ changent, et le front
  qui « montre les divergences » n'a plus rien à montrer. C'est une règle de calcul et de persistance (WF-DAT-0040
  conserve désormais les séries au pas du mois — relevé par la première passe pour le pas, non pour la
  conservation). Le groupe 2 (WF-DAT-0040) peut l'avoir vu du côté de la conservation ; côté WF-IND-0010 le contrat
  dit l'ancienne règle à trois endroits.
- **Proposition.** `IndicatorsRevision` : « une révision marquée, les indicateurs et les courbes que son marquage a
  conservés (WF-DAT-0040), `is_stored` vrai, sur les lignes de coût réel connues à son marquage telles qu'elles
  étaient alors (WF-IND-0010) ». Retirer les deux phrases « connues aujourd'hui » de `getCostCurve` et
  `getEarnedValueCurves` ; `is_stored` : « vrai pour une révision marquée, indicateurs et courbes ; faux pour la
  révision en cours et pour le calcul au jour courant d'un projet sans révision en cours ». Mettre à jour les fixtures
  des courbes lues pour 101 si elles existent (aucune n'est référencée avec `revision_id`).
- **DECISIONS.md** : « Les indicateurs et les courbes se lisent pour une révision » (#247, l. 1097-1105) et « Les
  courbes d'une révision marquée et les colonnes conservées » (#365, l. 1502-1507, EP-02/L35 : « WF-DAT-0040 ne
  change pas ») : deux décisions antérieures au 2026-10-09 qui disent l'inverse de la spec actuelle.

#### M-03 — Un projet sans révision en cours a des indicateurs au jour courant
- **gravité** : majeur ; **emplacement** : `docs/api/components/parameters.yaml:341-358` (`IndicatorsRevision` :
  « absente, ou la révision en cours, le calcul au jour courant »), `:359-366` (`AsOf` : « Absente, les indicateurs
  sont ceux de la révision en cours au jour courant ») ; `docs/api/paths/analysis.yaml:215-226`
  (`getProjectIndicators`), `:416-426` (`getIndexHistory` : « le dernier point au jour courant pour la révision en
  cours ») ; `docs/api/components/schemas/indicators.yaml:546-558` (`IndexHistory`), `:581-594`
  (`IndexHistoryPoint` : « au jour courant pour la révision en cours, dont `version_name` est nul ») ;
  `docs/api/components/schemas/portfolio.yaml:1-4` (en-tête : « lisent les indicateurs conservés ») ; **exigence** :
  WF-IND-0010 `{+Lorsque le projet ne comporte pas de révision en cours, ses indicateurs au jour courant se
  calculent sur sa dernière révision marquée, avec le coût réel au jour courant ; les indicateurs conservés de cette
  révision à sa date de marquage restent inchangés (WF-DAT-0040).+}` ; Vérif `{+Sur un projet sans révision en
  cours, un import de coûts réels change les indicateurs au jour courant et laisse inchangés ceux conservés de la
  dernière révision marquée.+}` ; WF-IND-0130 `[-pour la révision en cours,-]{+(WF-IND-0010),+}` ; WF-PTF-0010
  `{+Un projet dont la revue vient d'être marquée et qui n'a pas de révision en cours contribue par cette revue.+}`.
- **Ce que dit le contrat.** Pour les risques, `RiskRevision` (l. 275-283) porte la règle : « absente, la révision en
  cours, ou la dernière révision marquée quand aucune n'est en cours ». Pour les indicateurs, les courbes, l'évolution
  des indices et le portefeuille, rien : « la révision en cours » partout, et `getProjectIndicators` ne déclare qu'un
  409 pour l'état du projet. Aucune fixture d'indicateurs pour `project_without_current_revision`.
- **Constat.** Le cas est courant (toute revue venant d'être marquée, « la révision suivante n'est créée qu'à la
  demande », `markRevision`) : sans la règle, un implémenteur rend 409 ou les indicateurs conservés (coût réel du
  marquage, `is_stored` vrai), et l'accueil ou le portefeuille montrent un projet sans indice du jour le temps que la
  révision suivante soit créée. La première passe (G, « Doutes ») a posé la question sans la trancher ; la spec l'a
  tranchée.
- **Proposition.** `IndicatorsRevision` et `AsOf` : « absente, le calcul au jour courant : sur la révision en cours,
  ou, quand le projet n'en a pas, sur sa dernière révision marquée avec le coût réel du jour (WF-IND-0010),
  `is_stored` faux et `context.revision_id` nommant cette révision marquée » ; `getIndexHistory`/`IndexHistoryPoint` :
  « le dernier point au jour courant (WF-IND-0010), `version_name` nul, `revision_id` celui de la révision en cours
  ou de la dernière marquée » ; en-tête de `portfolio.yaml`/`PortfolioScope` : « au jour courant, chaque projet
  contribue par sa révision courante — la révision en cours, ou la dernière marquée (WF-PTF-0010) ». Un exemple
  `project_indicators_without_current_revision` (`is_stored` faux, `revision_status` `marked`).
- **DECISIONS.md** : aucune décision pour les indicateurs ; l. 4228-4234 (EP-14/L42i) prend « la révision en cours,
  ou la dernière révision marquée quand il n'en a pas » pour les contributeurs suggérés et renvoie la question à
  EP-04 ; `RiskRevision` l'a tranchée pour les risques (US-0230/L2).

#### M-04 — L'abandon de la révision en cours défait les saisies des risques, survenance comprise
- **gravité** : majeur ; **emplacement** : `docs/api/paths/revisions.yaml:127-148` (`abandonRevision` : « Le projet
  revient à son état à la dernière révision marquée, et les lignes de la révision abandonnée sont supprimées ») ;
  `docs/api/paths/risks.yaml:388-399` (`declareRiskOccurrence` : « Définitif, hors de l'historique d'annulation ») ;
  `docs/api/components/schemas/risks.yaml:3-8` (`RiskState` : « la survenance est définitive »), `:328-336`
  (`RiskOccurrence` : « Définitif. ») ; **exigence** : WF-RIS-0020 `{+Un risque appartient au projet : son libellé,
  sa description et sa note de mitigation sont des données du projet. Son évaluation — probabilité, état, structure
  propre et ligne de provision — est portée par chaque révision … L'abandon de la révision en cours (WF-REV-0010)
  ramène les risques à l'évaluation de la dernière révision marquée : un risque créé dans la révision abandonnée
  disparaît, et un risque qui y a été déclaré survenu redevient identifié, avec sa provision.+}` ; WF-RIS-0060
  `{+Elle est définitive : aucune transition ne part de l'état survenu, et aucune commande ne l'annule (WF-IHM-0110)
  ; seul l'abandon de la révision en cours la défait, avec tout ce que cette révision contient.+}` ; Vérif
  RIS-0020 : `{+le troisième est identifié, avec sa provision et sans coût à la survenance+}`.
- **Constat.** Le contrat ne dit nulle part que l'abandon touche les risques ; il dit trois fois la survenance
  « définitive » sans l'exception, et `RiskState` la fait lire comme irréversible au client généré. Un service qui
  suit le contrat garde un risque créé après abandon (orphelin, sans révision qui porte son évaluation) et un
  survenu dont les tâches fusionnées ont disparu avec la révision — état incohérent. Avant le gel : la sémantique de
  `abandonRevision` et de `RiskState` est ce que le front explique à l'utilisateur dans sa confirmation.
- **Proposition.** `abandonRevision` : « … et les saisies des risques qu'elle portait avec elles : un risque créé dans
  la révision disparaît, un réexamen est défait, un risque déclaré survenu redevient identifié avec sa ligne de
  provision — l'évaluation est celle de la dernière révision marquée (WF-RIS-0020) ». `declareRiskOccurrence`,
  `RiskOccurrence`, `RiskState` : « Définitif : aucune transition ne part de l'état survenu et aucune commande ne
  l'annule ; seul l'abandon de la révision en cours la défait (WF-RIS-0060) ». Un exemple `risks_after_abandon`
  (la Vérif : créé, réexaminé, survenu).
- **DECISIONS.md** : aucune décision (grep `abandon` : l. 1260-1270 permission `revision_abandon`, l. 1445-1449
  `project_without_current_revision`, l. 7044-7050 le témoin abandonné sans risque ni survenance « qui court ») ;
  E-13 (première passe) ne porte que sur le 409 et le compteur.

#### M-05 — La survenance ne dit pas où ni comment elle range les tâches fusionnées
- **gravité** : majeur ; **emplacement** : `docs/api/paths/risks.yaml:388-399` (`declareRiskOccurrence` :
  « Fusionne les tâches et les lignes du devis propre dans la structure principale … l'exemple `nodes_risk_occurred`
  de `listNodes` montre la structure obtenue ») ; `docs/api/components/schemas/risks.yaml:328-340`
  (`RiskOccurrence` : « les lignes fusionnées portant un montant budgété nul et leur montant du devis propre en
  réestimé ») ; `fixtures/api/nodes_risk_occurred.json:6-10` (541 « Risque survenu — Retard de livraison des
  armoires », 542, 544 : `scheduling_mode` `automatic`) ; **exigence** : WF-RIS-0060 `{+Les tâches de premier
  niveau du devis propre sont placées, dans leur ordre, en dernière position sous la tâche qui portait la ligne de
  provision ; leurs subordonnées, leurs liaisons internes, leurs durées et leurs modes sont conservés, et une tâche
  sans prédécesseur dans le devis propre passe en mode manuel aux dates qu'elle y avait … Lorsque la tâche qui
  portait la ligne de provision est un jalon, ces tâches sont placées, dans leur ordre, immédiatement après lui,
  sous sa tâche parente ou au premier niveau. Chaque ligne fusionnée conserve ses grandeurs ; elle porte … pour
  montant réestimé, le montant que ces grandeurs et ses dates donnent (WF-DEV-0020) — celui du devis propre tant que
  ses dates n'ont pas changé+}` ; Vérif : `{+une tâche fusionnée qui n'avait pas de prédécesseur est en mode
  manuel. La survenance d'un risque dont la provision était portée par un jalon place ses tâches après ce jalon, qui
  reste un jalon sans sous-tâche.+}`.
- **Constat.** La seule « spécification » du résultat est l'exemple, qui ne dit ni sous quelle tâche (551, « Poste de
  commande », est-elle la porteuse de la provision de 752 ? rien ne le dit, la ligne retirée n'étant visible nulle
  part), ni le mode (les tâches fusionnées sont `automatic`, quand au moins la tête 541 sans prédécesseur devrait
  être `manual` aux dates du devis propre), ni le cas du jalon porteur. Le réestimé « montant du devis propre » devient
  « celui que ses grandeurs et ses dates donnent », donc change avec les dates — c'est ce que la grille de reste à
  engager doit savoir. US-0680/L1 (#1453) ajoute le compte rendu préalable, pas la règle de placement de l'opération
  elle-même, qui reste à écrire sur `declareRiskOccurrence`.
- **Proposition.** Sur `declareRiskOccurrence` : la règle de placement (porteuse, dernière position ; jalon porteur :
  après lui sous son parent), la conservation (subordonnées, liaisons internes, durées, modes), le passage en mode
  manuel des tâches sans prédécesseur à leurs dates, et le réestimé « recalculé des grandeurs et des dates ». Faire
  rendre `manual` par `mockgestures`/`mockcore` pour 541 (ou 542/544 si elles n'ont pas de prédécesseur) ; ajouter
  l'exemple du jalon porteur si le témoin en a un.
- **DECISIONS.md** : « La survenance d'un risque ne budgète rien » (l. 344-350, 2026-10-04) décrit l'ancien texte ;
  l. 1764-1770 nomme `nodes_risk_occurred` « le sous-arbre 541 seul » sans dire la porteuse. Aucune décision sur le
  placement ni le mode (grep `mode manuel`, `dernière position`, `immédiatement après`).

#### M-06 — Les décaissements : le coût réel n'est pas décalé, et le reste à engager s'étale après la date de calcul
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/indicators.yaml:522-531`
  (`CurveSeries.cash_out_by_month` : « le passé par mois de date de pièce décalée, l'avenir en étalant le reste à
  engager et les provisions des risques identifiés, chaque part décalée de son délai de paiement »), `:533-544`
  (`CashOutMonth`) ; `docs/api/paths/analysis.yaml:295-301` (`getCostCurve` : « le reste à engager étalé sur les
  dates de la révision courante … chaque montant est décalé du délai de paiement de sa ligne ») ;
  **exigence** : WF-IND-0100 Vérif `{+la projection l'est aussi, hormis les lignes de provision, qui restent à leur
  date ; le coût réel n'est pas décalé.+}` ; corps `{+le reste à engager de chaque ligne est étalé … sur la part de
  la durée de sa tâche postérieure à la date de calcul, et porté entier à la date de calcul lorsque la fin de la
  tâche est dépassée (WF-RAE-0040)+}`.
- **Ce que disent les fixtures.** `cost_curve_payment_delays.json` rend la série `actual_cost` identique à celle de
  `cost_curve.json` (1 400 au 27 mars, 1 200 au 8 avril…) : le générateur ne décale pas le coût réel (DECISIONS
  l. 2201-2203 : « son coût réel à la date de ses pièces »). La description dit l'inverse de la fixture et de la spec.
- **Constat.** Un implémenteur qui suit `cash_out_by_month` décale les pièces ; l'écran qui lit « date de pièce
  décalée » explique faux. Le second point (étalement sur la part postérieure à la date de calcul, report entier
  d'une tâche dont la fin est dépassée) est ce qui fait partir la projection « de ce point » (Vérif) : « sur les
  dates de la révision courante » laisse étaler avant la date de calcul une tâche démarrée en retard. Le prorata des
  heures est relevé ailleurs (WF-DEV-0070/0080) et n'est pas repris ici.
- **Proposition.** `cash_out_by_month` : « le passé par mois de date de pièce — le coût réel n'est pas décalé —,
  l'avenir en étalant le reste à engager de chaque ligne sur la part de la durée de sa tâche postérieure à la date de
  calcul, porté entier à la date de calcul quand la fin est dépassée, chaque part décalée de son délai de paiement,
  les provisions à la date de leur tâche (WF-IND-0100) ». `getCostCurve` : remplacer « étalé sur les dates de la
  révision courante » par la même règle ; « chaque montant à venir est décalé ».
- **DECISIONS.md** : l. 310-316 (révision du 2026-10-04 : « décale chaque montant du délai de paiement de sa ligne »)
  antérieure ; l. 2196-2203 (EP-02/L26) fait déjà le coût réel « à la date de ses pièces » — le générateur a devancé
  le contrat.

#### M-07 — Ce qu'un projet en chiffrage apporte au portefeuille : hors provisions au budget, provisions comprises au reste, risques non pondérés
- **gravité** : majeur ; **emplacement** : `docs/api/paths/portfolio.yaml:224-233` (`getPortfolioCostCurve` : « un
  projet en chiffrage inclus contribue pondéré par sa probabilité de gain ») ; `docs/api/components/schemas/portfolio.yaml:261-275`
  (`PortfolioCostCurve`), `:200-215` (`PortfolioCostStructure`, rien sur le chiffrage), `:219-253` (`PortfolioRisks`,
  rien sur le chiffrage ni sur la non-pondération) ; `paths/portfolio.yaml:196-204` (`getPortfolioRisks`) ;
  **exigence** : WF-PTF-0020 `{+deux exceptions près : le pipeline brut … et la vue des risques (WF-PTF-0090), qui
  compte des risques et leurs provisions telles qu'elles sont+}` ; WF-PTF-0080 `{+Pour un projet en chiffrage,
  lorsqu'il est inclus, son devis courant pondéré par sa probabilité de gain tient lieu de budget de référence — hors
  lignes de provision, comme lui (WF-RIS-0050) — et, provisions comprises, de reste à engager+}` (Vérif : 50 de
  provision pour risques → 0 au budget, 20 au reste ; 50 de provision pour aléas → 20 et 20) ; WF-PTF-0090 `{+Un
  projet en chiffrage, lorsqu'il est inclus, apporte ses risques identifiés et leurs provisions sans pondération+}` ;
  WF-PTF-0100 `{+hors lignes de provision pour la courbe du budget, comme pour la structure des coûts, et provisions
  comprises pour la projection+}` (Vérif : 100 hors provisions + 50 de provision à 40 % → 40 au budget cumulé final,
  60 à la projection) ; WF-PTF-0010 Vérif `{+pondérée par leur probabilité de gain, hors le pipeline brut et la vue
  des risques, où elle ne l'est pas+}`.
- **Ce que dit le contrat.** « Contribue pondéré par sa probabilité de gain » sans distinguer budget et projection ;
  rien pour la structure des coûts ni pour les risques (hors « projets en cours », relevé par G-06/H-10). La fixture
  `portfolio_cost_curve` inclut 31 offres (`scope.states` `[in_progress, pricing]`).
- **Constat.** La décision d'EP-02/L26, « **Choix déclaré** : dans la courbe en S, le devis pondéré d'une offre tient
  lieu de budget de référence et de projection, rien n'étant dépensé — WF-PTF-0100 dit “les courbes de son devis
  courant” sans dire lesquelles » (l. 2199-2201), a été tranchée par l'auteur dans l'autre sens : budget et projection
  d'une offre diffèrent de ses provisions pondérées. La non-pondération des risques est une troisième règle, propre à
  la vue des risques, qui change `identified_total`, `heaviest[].provision_amount` et la matrice dès qu'une offre est
  incluse. Trois vues, trois descriptions à écrire ; le générateur (`mockportfolio.py:505-511`, « the provision the
  rest ») n'en tient aucune, ce que G-15 relève pour le budget des projets en cours.
- **Proposition.** `getPortfolioCostCurve`/`PortfolioCostCurve` : « un projet en chiffrage inclus contribue par les
  courbes de son devis courant, pondérées par sa probabilité de gain : hors lignes de provision pour le budget de
  référence, provisions comprises pour la projection du chef de projet (WF-PTF-0100) » ; `PortfolioCostStructure` :
  même règle pour `budget_by_cost_type` (hors provisions) et `remaining_by_cost_type` (provisions comprises) ;
  `PortfolioRisks` : « un projet en chiffrage inclus apporte ses risques identifiés et leurs provisions sans
  pondération (WF-PTF-0020, WF-PTF-0090) ; la réserve et la couverture ne portent que sur les projets en cours et
  terminés ». Amender la décision l. 2199 et faire suivre `mockportfoliotime`.
- **DECISIONS.md** : l. 2196-2203 (EP-02/L26, « Le portefeuille à l'échelle »), décision antérieure au 2026-10-09
  contredite par la spec actuelle ; l. 756-800 (US-0240/L3) ne parle pas des offres dans les risques.

#### M-08 — Le reste à engager d'une ligne non réestimée d'une tâche non démarrée
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/revisions.yaml:1365-1367`
  (`EstimateLineFacet.reestimated_amount` : « Montant réestimé, à l'année de référence. ») ;
  `docs/api/components/schemas/indicators.yaml:191-203` (`RemainingIndicators`, cite WF-RAE-0010 sans règle) ;
  **exigence** : WF-RAE-0010 `{+du montant réestimé de ses lignes si elle est démarrée, ou si elle ne l'est pas et
  que ses lignes ont été réestimées depuis la grille (WF-RAE-0040) ; et sinon du montant réestimé de ses lignes,
  qui, faute de réestimation, se calcule depuis les grandeurs de la référence, aux taux conservés par la révision
  courante (WF-REV-0060) et sur son année de consommation courante (WF-DEV-0030, WF-DEV-0040) — à taux horaires
  inchangés, c'est le montant budgété de la ligne reporté de l'année de consommation que lui donnait la référence
  sur son année de consommation courante+}` ; Vérif : `{+Dans une révision créée en 2027 où le taux de 2027 d'une
  catégorie a été accepté, une tâche non démarrée … compte pour sa charge au taux de 2027, et non au taux de 2026
  corrigé d'une année d'inflation. Après un avenant qui porte de 100 à 150 heures une ligne non réestimée d'une
  tâche non démarrée, le reste à engager compte 150 heures ; une ligne réestimée à 140 avant l'avenant garde
  140.+}` ; WF-RAE-0040 Vérif `{+80 fois le taux, projeté sur l'année de consommation de la ligne (WF-DEV-0030)+}`.
- **Ce que dit le contrat.** Rien sur la valeur de `reestimated_amount` d'une ligne jamais réestimée (celle d'une
  tâche non démarrée après la référence ou après un avenant), ni sur la distinction « réestimée depuis la grille /
  non réestimée » que la spec introduit (une ligne réestimée garde sa valeur à l'avenant, une ligne non réestimée
  suit les grandeurs de l'avenant). La ligne ne dit pas si elle a été réestimée.
- **Constat.** Les deux décisions qui décrivent les formules du générateur disent l'ancienne règle : « le budgété
  projeté d'une tâche non démarrée » (l. 1974-1977, EP-02/L24) et « ces deux tâches non démarrées y comptant leur
  budget projeté (WF-RAE-0010) » (l. 2355-2356, EP-02/L27). Avec la nouvelle règle, après la mise à jour des taux de
  la révision courante, une tâche non démarrée compte aux taux conservés par la révision courante, pas au budget
  (taux de la référence) projeté d'une inflation : les exemples `remaining_indicators` et les réestimés des lignes non
  démarrées du témoin peuvent différer. Avant le gel : il manque sans doute un indicateur de ligne « réestimée depuis
  la grille » (`previous_reestimated_amount` ne le dit pas) pour que la grille distingue les deux et que l'avenant
  sache quelles lignes recalculer.
- **Proposition.** `reestimated_amount` : « Montant réestimé, à l'année de référence : celui de la dernière
  réestimation (WF-RAE-0040) ; pour une ligne jamais réestimée, calculé depuis ses grandeurs courantes — celles de la
  référence, ou de l'avenant qui les a changées — aux taux conservés par la révision (WF-RAE-0010, WF-REV-0060) ». Un
  booléen calculé `is_reestimated` sur `EstimateLineFacet` (question à trancher). Trancher aussi l'année des montants
  de `RemainingIndicators` (voir « Doutes »). Mettre à jour les deux passages de DECISIONS.
- **DECISIONS.md** : l. 1974-1977 et 2355-2356, antérieures, disent « budgété projeté » ; aucune entrée sur WF-RAE-0010
  après le 2026-10-09.

#### M-09 — La revue précédente est une révision marquée à l'état En cours
- **gravité** : majeur ; **emplacement** : `docs/api/components/schemas/indicators.yaml:223-230`
  (`RemainingIndicators.delta_to_previous_revision` : « L'écart avec le reste à engager de la révision marquée
  précédente, à son marquage … nul (`null`) sans revue précédente ») ; **exigence** : WF-RAE-0020 `{+le reste à
  engager moins celui de la révision marquée précédente, lorsque celle-ci a été marquée à l'état En cours+}` ;
  Vérif `{+Sur un projet dont aucune révision n'a été marquée à l'état En cours avant celle qui est lue, l'écart
  correspondant est absent plutôt que nul+}`.
- **Constat.** Pour la première revue d'un projet dont la référence est l'offre marquée en chiffrage (le cas de
  tout projet dont la référence est désignée au passage En cours sans nouveau marquage), le contrat fait calculer
  un écart avec une révision qui n'a pas de reste à engager au sens du suivi ; la spec le veut absent. Le témoin
  n'a pas ce cas (101 marquée En cours, l. 1653, 2259), les fixtures ne le montrent donc pas.
- **Proposition.** « … de la révision marquée précédente qui l'a été à l'état En cours, à son marquage ; `null`
  quand aucune révision n'a été marquée En cours avant celle qui est lue — une offre marquée en chiffrage n'est pas
  une revue (WF-RAE-0020) ». Même précision pour `EstimateLineFacet.previous_*` (« nulles avant la première revue »)
  si la revue précédente y est la même.
- **DECISIONS.md** : l. 1530-1533 (EP-02/L35, #466) : « nul (`null`) sans revue précédente » — antérieure, sans la
  condition ; rien ensuite.

#### M-10 — Le diagramme temps/temps : aucun point avant l'état En cours, et le dernier au jour courant
- **gravité** : majeur ; **emplacement** : `fixtures/api/milestone_tracking.json:7` (« Réception des études » : point
  `marked_at` 2025-12-15, l'offre marquée en chiffrage, `forecast_date` 2026-04-24) ;
  `docs/api/components/schemas/indicators.yaml:432-452` (`MilestoneTracking` : « la date que chaque révision marquée
  prévoyait, en fonction de sa date de marquage ») ; `docs/api/paths/analysis.yaml:267-273` (`getMilestoneTracking`) ;
  **exigence** : WF-IND-0090 `{+Les révisions marquées avant l'état En cours ne donnent aucun point.+}` ; `{+la
  courbe d'un jalon s'arrête par un point à sa date de terminaison, en abscisse comme en ordonnée, et aucune révision
  marquée après cette date n'y ajoute de point. Le dernier point est celui du jour courant (WF-IND-0010) : il est
  fourni par la révision en cours ou, à défaut, par la dernière révision marquée.+}`.
- **Constat.** La fixture contredit la spec (un point de l'offre, marquée le 15 décembre 2025 en chiffrage, le projet
  passant En cours en janvier 2026 — DECISIONS l. 2088-2090) ; et la description ne dit ni le point du jour courant
  (que la fixture rend bien, `marked_at` = `computed_at` pour « Réception usine »), ni d'où il vient sans révision en
  cours, ni l'arrêt à la terminaison. La première passe (G, « Doutes ») a noté que `marked_at` sert aussi au point de
  terminaison sans que le nom le dise ; le point de l'offre n'a pas été vu.
- **Proposition.** Retirer le point du 2025-12-15 de `milestone_tracking.json` (générateur `mocktoday`) ;
  `MilestoneTracking.milestones[].points` : « un point par révision marquée à l'état En cours, à sa date de marquage,
  jusqu'à la terminaison du jalon — le dernier point d'un jalon terminé est à sa date de terminaison en abscisse comme
  en ordonnée, aucune révision marquée ensuite n'en ajoute — ; puis le point du jour courant, par la révision en cours
  ou, à défaut, la dernière révision marquée (WF-IND-0090, WF-IND-0010) ». Renommer ou décrire `marked_at` comme
  « l'abscisse : la date de marquage, la terminaison ou le jour courant ».
- **DECISIONS.md** : l. 1949-1953 (EP-02/L23) notait déjà que `milestone_tracking` « contredit l'histoire engendrée :
  la réception usine y a un point à l'offre » et renvoyait à L24 ; la fixture régénérée garde un point à l'offre pour
  l'autre jalon. Aucune décision sur les révisions marquées avant En cours.

#### M-11 — Les lignes de provision sortent de la valeur acquise, de l'avancement physique et du budget d'un sous-projet
- **gravité** : majeur (pour `physical_progress`, dont la formule est écrite) ; **emplacement** :
  `docs/api/components/schemas/revisions.yaml:1222-1229` (`TaskFacet.physical_progress` : « le rapport des montants
  budgétés portés par les tâches terminées de son sous-arbre au total budgété de ce sous-arbre ») ;
  `docs/api/components/schemas/indicators.yaml:291-293` (`ProjectIndicators.earned_value` : « Montants budgétés des
  tâches terminées »), `:231-243` (`SubprojectBalance.budget`, sans description), `parameters.yaml:368-380` (`Scope`) ;
  **exigence** : WF-IND-0060 `[-portés par les tâches terminées de-]{+acquis dans+} son sous-arbre {+— ses lignes
  propres comprises, hors lignes de provision (WF-IND-0030) — +}au total [-budgété-]{+des montants budgétés+} de ce
  [-sous-arbre-]{+sous-arbre, hors lignes de provision+}` ; WF-IND-0030 `{+hors lignes de provision
  (WF-DEV-0080), +}` ; WF-IND-0020 `{+le budget de référence d'un sous-projet est la somme des montants budgétés de
  ses lignes dans la révision de référence, hors lignes de provision+}` ; `{+Une ligne passée du sous-projet A au
  sous-projet B après la référence acquiert sa valeur dans A, et compte son reste à engager dans B.+}`.
- **Constat.** `NodeTotals.budgeted_amount` et le montant budgété d'une tâche « comptent les lignes de provision »
  (DECISIONS l. 912-916) ; la formule écrite de `physical_progress` prend donc au dénominateur la provision de 555
  (250 000 dans la référence) sous « Câblage des armoires » et son parent : avancement faux de plusieurs points, et
  faux aussi au numérateur si la tâche porteuse est terminée. `earned_value` et `SubprojectBalance.budget` sont
  silencieux, et la règle du sous-projet d'appartenance (référence pour EV/PV/budget, révision courante pour le
  reste) n'est dite nulle part.
- **Proposition.** `physical_progress` : « le rapport des montants budgétés acquis dans son sous-arbre — ses lignes
  propres comprises, hors lignes de provision — au total des montants budgétés du sous-arbre hors lignes de provision
  (WF-IND-0060) ; non calculable quand ce total est nul » ; `earned_value` : « hors lignes de provision
  (WF-IND-0030) » ; `SubprojectBalance.budget` : « la somme des montants budgétés hors provision des lignes qui
  appartiennent au sous-projet dans la révision de référence ; `remaining`, sur celles qui lui appartiennent dans la
  révision courante (WF-IND-0020) ». Vérifier `physical_progress` de 552 et 551 dans `nodes*.json` après correction du
  générateur.
- **DECISIONS.md** : l. 60-70 (`physical_progress` devenu `Computable`) et l. 912-916 ; rien depuis le 2026-10-09 sur
  les provisions dans l'avancement physique (grep `WF-IND-0060`, `WF-IND-0020` : l. 319, 3168-3206 seulement).

#### M-12 — Le code comptable sert aux fichiers de devis et de reste à engager
- **mineur** ; `docs/api/components/schemas/reference.yaml:590-597` (`CostCategoryImage.accounting_code` : « Il est
  documentaire : il n'intervient dans aucun calcul ni dans aucun import (WF-REF-0040). ») ; WF-REF-0040
  `{+il n'intervient dans aucun calcul ni dans l'import des coûts réels (WF-INTF-0140), qui ne ventile pas par
  nature ; les fichiers de devis et de reste à engager désignent la catégorie d'une ligne hors main-d'œuvre par ce
  code (annexe B)+}`.
- **Constat.** La description dit l'ancienne règle ; l'implémenteur de l'import Excel (EP-07/EP-09) lira « aucun
  import » là où l'annexe B le fait désigner la catégorie. Pas de surface d'API au-delà de la description.
- **Proposition.** « Documentaire : il n'intervient dans aucun calcul ni dans l'import des coûts réels, qui ne
  ventile pas par nature ; les fichiers de devis et de reste à engager désignent par lui la catégorie d'une ligne
  hors main-d'œuvre (WF-REF-0040, annexe B). »
- **DECISIONS.md** : l. 3459-3463 (#562, 2026-10-09 : exigé et unique) ne parle pas de l'emploi par l'import ;
  C-03 (première passe) porte sur le motif `\S`.

#### M-13 — Les bornes des zones d'un indice
- **mineur** ; `docs/api/components/schemas/reference.yaml:852-860` (`IndexThresholds`), `:1040-1045` (`AlertZone`),
  `docs/api/components/schemas/indicators.yaml:322-330` (`IndexValue`) ; WF-REF-0170 `{+Un indice supérieur ou égal au
  seuil de vigilance est nominal ; inférieur au seuil de vigilance et supérieur ou égal au seuil d'alerte, il est en
  vigilance ; inférieur au seuil d'alerte, il est en alerte.+}` ; Vérif `{+un indice de 0,9 est nominal et un indice
  de 0,8 en vigilance+}`.
- **Constat.** Le contrat dit l'inclusion des bornes pour la matrice (`RiskMatrixLevel` : « borne basse comprise,
  borne haute exclue ») et rien pour les seuils ; les deux générateurs classent déjà comme la spec
  (`mockindicators.py:447-456`, `mockportfolio.py:82-87`). Le serveur classe (WF-IHM-0070), mais c'est le contrat qui
  le spécifie.
- **Proposition.** `IndexThresholds` : « Un indice supérieur ou égal au seuil de vigilance est nominal ; inférieur à
  lui et supérieur ou égal au seuil d'alerte, en vigilance ; inférieur au seuil d'alerte, en alerte (WF-REF-0170) :
  à 0,9 et 0,8, un indice de 0,9 est nominal, 0,8 en vigilance. »
- **DECISIONS.md** : aucune (grep `égal au seuil`, `supérieur ou égal`).

#### M-14 — La zone d'un indice conservé est lue avec les seuils courants
- **mineur** ; `docs/api/components/schemas/indicators.yaml:322-330` (`IndexValue.zone`), `:581-594`
  (`IndexHistoryPoint` : « tels que le marquage les a conservés »), `:103-120` (`CalculationContext.is_stored` :
  « indicateurs conservés … invariables ») ; WF-REF-0130 `{+Les bornes de la matrice de risques, les seuils d'alerte
  et le délai maximal entre deux revues ne sont pas conservés par les révisions : une révision marquée est toujours
  lue avec leurs valeurs courantes … ses indicateurs conservés (WF-DAT-0040) ne changent pas, seule la zone qui les
  qualifie peut changer.+}` ; Vérif `{+Après abaissement du seuil d'alerte, la zone de l'indice de coût d'une
  révision marquée peut changer, sa valeur non.+}`.
- **Constat.** `IndexValue` porte `value` et `zone` ensemble ; pour une révision marquée, « conservés » et
  « invariables » laissent croire que la zone est conservée aussi. La matrice le dit bien (« d'après le
  référentiel »), les indices non.
- **Proposition.** `IndexValue.zone` : « classée à la lecture d'après les seuils courants du référentiel, pour un
  indice conservé comme pour un indice du jour : la valeur conservée ne change pas, sa zone peut changer avec les
  seuils (WF-REF-0130, WF-REF-0170) » ; `IndexHistory.thresholds` : « les seuils courants, ceux qui classent chaque
  point ».
- **DECISIONS.md** : aucune (grep `zone` + `conserv`, `seuils courants`).

#### M-15 — Le dénominateur du taux de transformation
- **mineur** ; `docs/api/components/schemas/portfolio.yaml:87-89` (`PortfolioValue.conversion_rate` : « À quatre
  décimales ») ; `docs/api/components/schemas/indicators.yaml:83-85`, `:99` (`no_offer_out_of_pricing` : « une
  période où aucune offre n'est sortie de l'état Chiffrage ») ; WF-PTF-0050 Vérif `{+Sur dix offres sorties de
  l'état Chiffrage dans la période vers En cours ou vers Perdu, dont quatre passées à En cours, le taux de
  transformation vaut 40 % ; une onzième, abandonnée dans la période, ne le change pas.+}`.
- **Constat.** Une offre abandonnée « sort de l'état Chiffrage » aussi : le motif et l'absence de description font
  compter onze au dénominateur. Le générateur compte « quatre gagnées sur dix sorties du chiffrage » (l. 766) sans
  dire ce qu'il fait des abandons.
- **Proposition.** `conversion_rate` : « les offres passées de Chiffrage à En cours sur celles passées de Chiffrage à
  En cours ou à Perdu dans la période ; une offre abandonnée ne compte pas (WF-PTF-0050) ; non calculable sans
  aucune, `no_offer_out_of_pricing` » ; le motif : « aucune offre n'est passée de Chiffrage à En cours ou à Perdu
  sur la période ».
- **DECISIONS.md** : l. 766, 791, 2179 (US-0240/L3, EP-02/L26) : « sorties du chiffrage », sans l'exclusion des
  abandons ; antérieures.

#### M-16 — La projection au rythme constaté agrégée
- **mineur** ; `docs/api/components/schemas/portfolio.yaml:156-199` (`PortfolioPerformance.projections`, un
  `Projections` sans description propre) ; `paths/portfolio.yaml:142-150` ; WF-PTF-0070 `{+la projection au budget et
  celle du chef de projet comme sommes des projections des projets, la projection au rythme constaté comme le budget
  de référence agrégé divisé par l'indice de coût agrégé, non calculable tant que celui-ci ne l'est pas
  (WF-PTF-0020)+}` ; Vérif `{+… vaut 2 222 et non 2 250+}`.
- **Constat.** Le générateur fait la bonne chose (`mockportfolio.py:422-438` : AC × BR / EV, soit BR / CPI ;
  `portfolio_performance.json` : 2 829 607 199,61 pour un budget de 2 662 620 197,64 et un indice de 0,941…) ; le
  contrat laisse l'implémenteur sommer les projections des projets, ce que WF-PTF-0020 interdit pour un rapport.
- **Proposition.** Sur `PortfolioPerformance.projections` : « `at_budget` et `project_manager` sont les sommes des
  projections des projets en cours ; `at_observed_rate` est le budget de référence agrégé divisé par l'indice de coût
  agrégé, non calculable tant qu'il ne l'est pas (WF-PTF-0070, WF-PTF-0020) : deux projets de budget 1 000, de valeur
  acquise 400 et 500 et de coût réel 500 et 500 donnent 2 222, non 2 250. »
- **DECISIONS.md** : l. 766-770 (« chaque indice en rapport des sommes ») ne parle pas des projections.

### Ce qui est juste

Vérifié conforme à la spec révisée : WF-REF-0010 (cascade de la nature sur ses catégories, `cost_type_active`,
`setCostTypeActivation`, `setCostCategoryActivation`, C-291) ; WF-REF-0030 (type figé par l'emploi, un taux ou un
rôle : `cost_type_unused`/`unrated`/`without_role` ; catégorie désignée par le risque ; désactivation de la dernière
catégorie de provision acceptée et ses refus `active_provision_category` sur `createProject`, `createRisk`,
`reviewRisk`, `getReferenceReadiness`) ; WF-REF-0040 hors M-12 (libellé exigé, rattachements : `cost_category_unused`,
`cost_category_unrated`, `cost_category_without_role`, « vers une nature du même type toujours permis ») ;
WF-REF-0070 (déplacement par `parent_id`, `ORG_NODE_CYCLE`, refus sous un nœud désactivé) ; WF-REF-0090 (code unique,
nœud non modifiable — `ResourceRoleUpdate` sans `org_node_id` —, catégorie et calendrier vers des objets actifs) ;
WF-REF-0110 (libellé unique, `ALREADY_EXISTS` sur `/label`) ; WF-REF-0160 (« borne basse comprise, borne haute
exclue » = « une valeur égale à une borne relève du niveau supérieur ») ; WF-REF-0190 (correspondance, `is_complete`,
`missing_columns`, colonne exigée absente et colonnes ignorées au compte rendu, `DUPLICATE_COLUMN_LABEL`) ;
WF-RIS-0010 pour la tâche désignée (`provision_task_id`, première tâche de premier niveau, `at_least_one_task`,
`UNKNOWN_TASK`, report sur la parente par import et fusion signalé `parent`, « n'entre pas dans l'état de sa tâche »,
catégorie changeable tant qu'identifié, retour d'un écarté avec sa catégorie ou une autre, sous-projet) ;
WF-RIS-0040 (trois totaux distincts et la réserve en regard) ; WF-RAE-0030 (Kanban : `task_is_milestone`,
`task_without_lines`, provision ne comptant pas, jalon rouvert → non démarré et date effacée, `completed_milestone`) ;
WF-RAE-0040 (réestimation d'une tâche non démarrée, zéro partout → terminée à `completed_on` qui est aussi
`started_on`, création/suppression de nœuds par `edit_remaining` sur un projet En cours) ; WF-RAE-0050 (budgété nul,
« comme issue d'un risque survenu ») ; WF-CRE-0010 (poste, colonnes conservées selon la correspondance) ;
WF-CRE-0040 (totaux de toutes les lignes retenues ; `overall` = `tracked` + `excluded` dans `actual_costs.json`) ;
WF-PTF-0010/0020 pour le périmètre et le rapport des sommes ; WF-PTF-0070 pour l'indice (`portfolio_performance`
cohérent) ; WF-RAE-0020 pour la somme des écarts des sous-projets (`remaining_indicators.json` : −3 275 301,28 des deux
côtés). Les fixtures de couverture et de totaux de provisions sont arithmétiquement justes sur l'univers témoin.

### Doutes

- **Année des montants du reste à engager.** WF-RAE-0010 et la Vérif de WF-RAE-0040 (« 80 fois le taux, projeté sur
  l'année de consommation ») font du reste à engager un montant « sur l'année de consommation courante » (donc
  inflation comprise, WF-DEV-0030) ; `EstimateLineFacet.reestimated_amount` est « à l'année de référence » et
  `RemainingIndicators.total` ne dit pas son année. Soit le contrat choisit de rendre les réestimés hors inflation
  et le total inflaté, soit la spec veut l'inflation partout : à trancher (lié à M-08).
- **Nouvelle référence et réserve (M-01)** : la spec ne dit pas explicitement le sort d'un risque écarté *après* la
  nouvelle référence ; lecture retenue : la réserve ne diminue jamais (règle générale de WF-RIS-0050 inchangée).
- **Tâche porteuse de la provision de 752 (M-05)** : aucune fixture ne montre la ligne de provision retirée ni le
  devis propre de 752 ; « Risque survenu — Retard de livraison des armoires » (541) peut être la tâche de premier
  niveau du devis propre lui-même, auquel cas seul le mode est en cause.
- **WF-CRE-0020** : la suppression de « ou à un sous-projet marqué supprimé (WF-DAT-0080) » dans le corps laisse
  ouvert ce que devient une ligne dont le code est celui d'un sous-projet marqué supprimé — toujours imputée au seul
  projet ? Le contrat (`ActualCostLine.subproject_code`) ne traite pas le cas ; non tranché, non compté.
- **WF-PTF-0090 et le filtre par nœud** : `getPortfolioRisks` n'a pas `PortfolioOrgNode`, ce qui est cohérent avec
  « ne restreint que les lignes de main-d'œuvre » ; mais `scope.org_node_id` est alors toujours nul dans cette vue —
  acceptable, non compté.
- **Recouvrement avec le groupe 2** : M-02 touche WF-DAT-0040 (conservation des courbes), que le groupe 2 relit ;
  le consolidateur fusionnera si le même constat y figure.

### Relevé (43 exigences du groupe)

| Exigence | Verdict | Renvoi |
|---|---|---|
| WF-PTF-0010 | non porté (contribution sans révision en cours ; pondération des risques) | M-03, M-07 |
| WF-PTF-0020 | non porté (exception de la vue des risques) | M-07 |
| WF-PTF-0040 | forme (Motif) | — |
| WF-PTF-0050 | non porté (dénominateur du taux) | M-15 |
| WF-PTF-0070 | non porté (projection au rythme constaté agrégée, description) | M-16 |
| WF-PTF-0080 | non porté (offre : hors provisions au budget, comprises au reste) | M-07 (G-15 adjacent) |
| WF-PTF-0090 | non porté (risques d'une offre non pondérés) ; « en cours et terminés » déjà relevé | M-07 (G-06/H-10 exclus) |
| WF-PTF-0100 | non porté ; décision l. 2199 contredite | M-07 |
| WF-PTF-0110 | forme (Motif) | — |
| WF-REF-0010 | porté | — |
| WF-REF-0130 | non porté (zone recalculée) | M-14 |
| WF-REF-0030 | porté | — |
| WF-REF-0040 | porté, sauf le code comptable et les fichiers | M-12 |
| WF-REF-0070 | porté | — |
| WF-REF-0090 | porté | — |
| WF-REF-0110 | porté | — |
| WF-REF-0160 | porté (assiette déjà relevée : C-04/H-06) | — |
| WF-REF-0170 | non porté (bornes des zones, description) | M-13 |
| WF-RAE-0010 | non porté ; décisions l. 1974, 2356 contredites | M-08 |
| WF-RAE-0020 | non porté (revue précédente En cours) ; sens de la marge déjà relevé (#466, G-07) ; somme des écarts vérifiée juste | M-09 |
| WF-RAE-0030 | porté | — |
| WF-RAE-0040 | porté (saisie), sans surface (grille) ; année du réestimé en doute | Doutes, M-08 |
| WF-RAE-0050 | porté / sans surface | — |
| WF-RIS-0010 | porté ; suppression par saisie de la porteuse déjà relevée (H-05) ; coût à la survenance exclu (H-01/H-02) | — |
| WF-RIS-0020 | non porté (abandon ; données du projet vs évaluation) | M-04 |
| WF-RIS-0030 | forme / sans surface | — |
| WF-RIS-0040 | porté | — |
| WF-RIS-0050 | non porté (réserve cumulée, avenant) ; coût à la survenance exclu | M-01 |
| WF-RIS-0060 | non porté (placement, modes, réestimé recalculé, abandon) | M-05, M-04 |
| WF-CRE-0010 | porté | — |
| WF-CRE-0020 | déjà relevé (I-02 code de rejet, D-07 code projet) ; sous-projet supprimé en doute | Doutes |
| WF-CRE-0040 | porté | — |
| WF-CRE-0050 | exclu (première passe : inchangées/rejetées) | — |
| WF-IND-0010 | non porté (coût réel au marquage, courbes conservées ; sans révision en cours) ; décisions #247/#365 contredites ; « ou égale » déjà relevé (G-09) | M-02, M-03 |
| WF-IND-0020 | non porté (budget d'un sous-projet hors provision, appartenance par révision) | M-11 |
| WF-IND-0030 | non porté (description) | M-11 |
| WF-IND-0060 | non porté (formule de l'avancement physique) | M-11 |
| WF-IND-0080 | forme / sans surface (`no_planned_value` suffit) | — |
| WF-IND-0130 | non porté (dernier point sans révision en cours) | M-03 |
| WF-IND-0090 | non porté (fixture : point de l'offre ; description) | M-10 |
| WF-IND-0100 | non porté (coût réel non décalé, étalement après la date de calcul) ; pas du mois et prorata exclus | M-06 |
| WF-IND-0110 | forme (pas du mois exclu) | — |
| WF-REF-0190 | porté (nouvelle) | — |
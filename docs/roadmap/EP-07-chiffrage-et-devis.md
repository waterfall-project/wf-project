---
id: EP-07
titre: Chiffrer un projet sur ses tâches, et le faire passer En cours
statut: en cours
depend_de: EP-06
famille: front, back
issue: 2360
---

# EP-07 — Chiffrage et devis

## Objet

Les lignes de devis portées par les tâches, leur montant calculé des taux horaires et de
l'année de consommation, l'inflation du projet, les indicateurs de devis, la grille de devis, le
plan de charge calculé sur le devis, la mise à jour des taux à la création d'une révision, la
comparaison de deux révisions et la proposition des contributeurs ; l'import et l'export du devis
au format Excel de l'annexe B (FLX-03, FLX-04), dont l'aller-retour se valide ici (revue de la
ventilation, 2026-10-09 : EP-12 abandonné).

Avec des tâches et des lignes, une référence complète peut être désignée : le passage à En cours
(WF-CYC-0030) devient constatable, et avec lui les exigences du référentiel qui ne se vérifient
que sur des montants — conservation des valeurs dans une révision, désactivation et
modification sans effet rétroactif.

## Ce qui en fait partie

- les attributs d'une ligne, le calcul de son montant, son année de consommation, et le refus de
  calculer sans taux pour l'année de référence ;
- la facette ligne de la table des nœuds d'EP-06, ses règles de placement, sa copie, sa
  suppression, son entrée dans l'historique annulable et dans le collage, et les calendriers des
  rôles qu'elle donne à sa tâche ;
- les tables images du référentiel que la révision conserve — rôles, calendriers, catégories, taux
  — et les paramètres du projet qu'elle fige à son marquage ;
- le taux d'inflation du projet et ses effets sur la révision en cours ;
- les indicateurs de devis et la grille de devis ;
- le plan de charge du projet, calculé sur le devis d'une révision ;
- la mise à jour des taux proposée à la création d'une révision ;
- la comparaison de deux révisions, sur l'identité de lignée ;
- la proposition des contributeurs d'après les rôles employés ;
- le passage à En cours et l'exigence du code projet ;
- la valeur planifiée, calculée sur la révision de référence, une fonction du noyau sans écran
  avant EP-10 ;
- l'import et l'export du devis (FLX-03, FLX-04), leur format versionné et indépendant de la
  langue, leur idempotence, sur la mécanique d'import d'EP-06 ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — les lignes des trois révisions de
  PRJ-001, la mise à jour des taux de la révision 101, la désignation de l'offre et le passage
  En cours —, chargée par le chargeur après celle des tâches ;
- les écrans du devis de la maquette, branchés sur le service, et les parcours écrits sur le faux
  back rejoués contre lui.

## Ce qui n'en fait pas partie

- la réestimation et le reste à engager, et le plan de charge calculé sur lui — EP-09 ;
- les provisions des risques, qui entrent au devis sans entrer au budget de référence — EP-08 ;
- les structures différentielles et les devis propres des risques : leur saisie, leur import,
  leur fusion — EP-08 ;
- la valeur planifiée recalculée sur la référence produite par un avenant — EP-08 ;
- l'import et l'export du reste à engager et des coûts réels — EP-09 ;
- la révision 101 du témoin désignée référence : elle ne le devient que par la fusion de
  l'avenant 1 — EP-08 ; ici, la référence de PRJ-001 est l'offre 100 (décision de l'auteur du
  2026-11-07, au cadrage).

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
WF-PLA-0010, WF-INTF-0040, WF-INTF-0050, WF-INTF-0060 et WF-INTF-0080 sont commencées par EP-06
et closes ici : leur Vérif demande des lignes de devis, l'import d'un devis ou des rôles aux
calendriers différents (cadrage d'EP-06, décision de l'auteur du 2026-11-07). Dix exigences que le
fichier disait entières ou closes ici ont une phrase de Vérif qui demande une ligne de provision,
un différentiel ou une fusion, les coûts réels, le reste à engager ou sa grille, ou l'indice de
coût : elles se commencent ici et se closent en EP-08, EP-09 ou EP-10 (décision de l'auteur du
2026-11-07, au cadrage d'EP-07) ; les tableaux de ces EPIC les reçoivent. Trois exigences
qu'EP-07 réalise en partie entrent au tableau en portée « début » (même décision) : WF-IHM-0110,
WF-INTF-0010 et WF-QUA-0040. Chaque US cite les exigences dont une phrase de Vérif tient avec des
lignes, des tâches, des révisions et le référentiel ; les phrases qui demandent plus sont des
écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-DEV-0020-A` | Attributs d’une ligne de devis | entière | US-1490 |
| `WF-DEV-0030-A` | Calcul du montant d’une ligne | début — close en EP-08 | US-1490 |
| `WF-DEV-0040-A` | Année de consommation d’une ligne | entière | US-1490 |
| `WF-DEV-0010-A` | Taux horaires requis pour le calcul à la création d’un chiffrage | début — close en EP-08 | US-1490, US-1510 |
| `WF-PLA-0010-A` | Calendrier applicable à une tâche | fin — amorcée en EP-06 | US-1490 |
| `WF-DAT-0090-A` | Intégrité déclarée en base | fin — amorcée en EP-03, EP-04, EP-06 | US-1490 |
| `WF-DAT-0100-A` | Types des grandeurs | fin — amorcée en EP-03, EP-06 | US-1490 |
| `WF-DAT-0010-A` | Copie complète des révisions | fin — amorcée en EP-04 | US-1490 |
| `WF-DAT-0020-A` | Immuabilité garantie par la base | fin — amorcée en EP-04 | US-1490 |
| `WF-DAT-0080-A` | Régimes de suppression | fin — amorcée en EP-03, EP-04 | US-1490 |
| `WF-REF-0040-A` | Catégories de coût | fin — amorcée en EP-05 | US-1490 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | début — close en EP-08, amorcée aussi en EP-02, EP-06 | US-1490, US-1560 |
| `WF-REV-0030-A` | Contenu de l’instantané | fin — amorcée en EP-04 | US-1500 |
| `WF-REV-0060-A` | Année de référence et mise à jour des taux à la création d’une révision | début — close en EP-09, amorcée aussi en EP-15 | US-1500 |
| `WF-REV-0010-A` | Unicité de la révision en cours | fin — amorcée en EP-15, EP-04 | US-1500 |
| `WF-REV-0020-A` | Marquage d’une révision | fin — amorcée en EP-04 | US-1500 |
| `WF-REV-0070-A` | Historique des révisions | fin — amorcée en EP-04 | US-1500 |
| `WF-REF-0020-A` | Désactivation sans effet sur les projets | fin — amorcée en EP-05 | US-1500 |
| `WF-REF-0130-A` | Modification sans effet rétroactif | début — close en EP-10, amorcée aussi en EP-05 | US-1500 |
| `WF-REF-0030-A` | Natures de coût | début — close en EP-08, amorcée aussi en EP-05 | US-1500 |
| `WF-REF-0010-A` | Désactivation des objets du référentiel | début — close en EP-09, amorcée aussi en EP-05 | US-1500 |
| `WF-PRJ-0040-A` | Taux d’inflation du projet | début — close en EP-08 | US-1500 |
| `WF-DEV-0060-A` | Indicateurs de devis | entière | US-1510 |
| `WF-DEV-0070-A` | Plan de charge du projet | début — close en EP-09, amorcée aussi en EP-15 | US-1520 |
| `WF-DEV-0080-A` | Valeur planifiée | début — close en EP-08 | US-1520 |
| `WF-REV-0080-A` | Comparaison de deux révisions | début — close en EP-08, amorcée aussi en EP-15 | US-1530 |
| `WF-CYC-0020-A` | Progression automatique | fin — amorcée en EP-04 | US-1540 |
| `WF-CYC-0030-A` | Conditions du passage à En cours | fin — amorcée en EP-04, EP-15 | US-1540 |
| `WF-CYC-0050-A` | Conditions de progression consultables | fin — amorcée en EP-04 | US-1540 |
| `WF-PRJ-0010-A` | Code projet | fin — amorcée en EP-04 | US-1540 |
| `WF-PRJ-0060-A` | Liste des contributeurs | fin — amorcée en EP-04 | US-1540 |
| `WF-PRJ-0070-A` | Proposition des contributeurs | entière | US-1540 |
| `WF-INTF-0070-A` | Formats d’échange Excel | début — close en EP-09 | US-1550 |
| `WF-INTF-0100-A` | Import du devis (FLX-03) | début — close en EP-08 | US-1550 |
| `WF-INTF-0110-A` | Export du devis (FLX-04) | entière | US-1550 |
| `WF-INTF-0180-A` | Formats indépendants de la langue | fin — amorcée en EP-02 | US-1550 |
| `WF-INTF-0080-A` | Contrôle et confirmation des imports Excel | fin — amorcée en EP-06 | US-1550 |
| `WF-INTF-0090-A` | Imports et révisions marquées | début — close en EP-08, amorcée aussi en EP-06 | US-1550 |
| `WF-INTF-0040-A` | Imports MS Project | fin — amorcée en EP-06 | US-1550 |
| `WF-INTF-0050-A` | Exports MS Project | fin — amorcée en EP-06 | US-1550 |
| `WF-INTF-0060-A` | Réversibilité de l’échange MS Project | fin — amorcée en EP-06 | US-1550 |
| `WF-DAT-0110-A` | Idempotence garantie par la base | début — close en EP-09 | US-1550 |
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | fin — amorcée en EP-03, EP-05, EP-16, EP-04 | US-1550 |
| `WF-PRJ-0080-A` | Attributs d’un projet | fin — amorcée en EP-16, EP-04 | US-1550 |
| `WF-REF-0140-A` | Devise de l’installation | fin — amorcée en EP-05 | US-1550 |
| `WF-DEV-0050-A` | Grille de devis | début — close en EP-08, amorcée aussi en EP-15 | US-1560 |
| `WF-IHM-0060-A` | Lecture d'une grille | fin — amorcée en EP-02, EP-03, EP-15 | US-1560 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06 | US-1570 |
| `WF-INTF-0010-A` | Usages du chef de projet | début — close en EP-08, amorcée aussi en EP-06 | US-1570 |

## Opérations du contrat

Servies ici pour la première fois (8) :

- `projects` : `listContributorSuggestions` (US-1540) ;
- `revisions` : `updateEstimateLine` (US-1490), `getRateUpdateProposal`, `applyRateUpdate`
  (US-1500), `compareRevisions` (US-1530) ;
- `analysis` : `getEstimateIndicators`, `getMissingRates` (US-1510), `getProjectWorkload`
  (US-1520).

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute :

- `revisions` : `listNodes` (la facette ligne, ses filtres et son tri), `createNode`,
  `deleteNode`, `moveNodes`, `resolveRowNumber`, `getComputedValueDependencies` — les lignes, les
  montants et ce dont ils dépendent (US-1490) ; `previewPaste`, `applyPaste`, `undoLastChange`,
  `redoLastUndo` — les colonnes de la ligne (US-1560) ; `createRevision`, `getRevision`,
  `listRevisions` — les taux projetés, l'instantané (US-1500) ; `designateReferenceRevision` —
  les lignes exigées (US-1540) ; `listCostStructures` — rien ne change ;
- `projects` : `getProject`, `updateProject`, `getProjectNextState` — le code et le passage
  En cours (US-1540) ; `updateProject` — le taux d'inflation (US-1500) ; `deleteSubproject` — les
  lignes qui le portent (US-1490) ;
- `reference` : `updateResourceRole`, `setResourceRoleActivation`, `updateCalendar`,
  `setDefaultCalendar`, `setCostTypeActivation`, `updateCostType`, `updateCostCategory`,
  `setCostCategoryActivation`, `setHourlyRate` — leurs effets sur les révisions, et les gardes que
  les lignes alimentent (US-1500) ;
- `exchanges` : `uploadFile`, `openImport`, `getImport`, `abandonImport`, `applyImport`,
  `requestExport`, `getBackgroundTaskResult` — le devis (US-1550).

Aucune opération ne manque au contrat, figé en 1.0.0 : un écart devient une « Interface contract
issue » que l'auteur tranche.

## Préalables

`epic/EP-07` se tire d'`epic/EP-06` dès la fusion de son lot pivot, **US-1380/L1 #2328** — le
socle d'EP-06 —, et non de `main` à la livraison d'EP-06 (décision de l'auteur du 2026-11-07, pour
toute la série EP-06 → EP-07 → EP-09 → EP-10 → EP-08 ; l'exception du README, « Branches ») : elle
reprend `epic/EP-06` à chaque lot que celui-ci fusionne et se fusionne dans `main` après elle. Ce
que le socle garantit : la table `node` (`kind` à deux valeurs, l'unique `(project_id, id, kind)`
que la facette ligne cite), la facette `task`, `task_link`, les registres `register_copy`,
`register_tasks_and_lines`, `register_closing`, `register_facet`, `register_format`,
`register_exporter`, `register_idle_task_guard`, `register_revision_filler`, l'interface de
`core/history`, et la chaîne des migrations arrêtée à `0024`. Les lots d'EP-07 qui créent des
lignes attendent aussi **US-1380/L2 #2335** (la lecture, la création, la modification des tâches)
et **US-1380/L3 #2338** (la suppression et le déplacement des nœuds) ; chaque lot nomme les lots
d'EP-06 qu'il attend par leur numéro.

EP-16 livré, le contrat figé en 1.0.0 : un écart devient une « Interface contract issue » que
l'auteur tranche.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.4, de WF-PRJ-0040 et de WF-REV-0060 qui ne citent ni
  ligne de provision, ni différentiel, ni reste à engager sont des tests qui passent
  (WF-QUA-0020) ;
- un projet passe à En cours dès que sa référence porte une tâche, une ligne et un code projet,
  et la condition manquante est nommée tant qu'il n'y passe pas ; PRJ-001, chargé, est En cours ;
- la correction d'un taux et la désactivation d'une catégorie laissent inchangés les montants
  d'une révision marquée ;
- la somme des montants d'une révision ne dépend pas de l'ordre de sommation ;
- un devis s'exporte en Excel, se réimporte sans écart, et deux imports du même fichier donnent
  le même devis ;
- le parcours de bout en bout chiffre un projet et le fait passer En cours, contre le service
  réel ;
- `make check` passe sur la branche de l'EPIC, les tests du back citent leurs exigences, et aucun
  fichier de `docs/api` ne change hors d'une « Interface contract issue » tranchée.

## Constats reçus

Relevés par la revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`)
et tranchés par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), que le service
suit une fois figé.

- #1752 — la comparaison compte une ligne sous la clé de chaque révision ; `subproject` et
  `cost_category` dans `changes` ; le réestimé entre années de référence (E-01, E-02 ; contrat
  #1751, #1754). US-1530.
- #1756 — `applyRateUpdate` exige le compteur et des catégories de la proposition (E-03 ; contrat
  #1755). US-1500.
- #1767 — les saisies du devis refusées sur la structure principale en réalisation et sous une
  tâche terminée, permises dans un différentiel (F-01 ; contrat #1766 ; spécification #1765).
  US-1490 (la saisie), US-1560 (le collage) ; le différentiel est d'EP-08.

#624 et #729, la comparaison de révisions en table simple et son e2e, reportés ici le
2026-10-18, sont ramenés en EP-15 le même jour (décision de l'auteur) : la comparaison passe dans la
grille dense, marquée comme un diff (#1060, US-0500).

Reportés d'EP-17 à sa livraison (rangement du 2026-11-05) :

- #1973 — front : `NODES` désigne un suffixe de chemin dans le test de la page du devis
  (`estimate/page.test.tsx`), une route complète dans celui du planning ; à nommer d'après ce que
  la constante est, quand les tests du devis se rejouent contre le service. Relevé par la revue
  d'US-0800 (EP-17). Corrigé par le premier lot d'EP-07 qui touche ce fichier, US-1560 (décision
  de l'auteur du 2026-11-07).

- #1628 [EP-16] — outil : l'offre du témoin projetée depuis 2026, et non depuis son année de référence
  2025 ; fermée le 2026-10-29 par l'option 4 (raccourci déclaré, #1641 sans code). Rouverte par le
  cadrage d'EP-07 : le service calculera l'offre à ses taux de 2025, et la fixture se corrige
  (décision de l'auteur du 2026-11-07). US-1570, lot d'outil.

- #2190 [EP-04] — le code d'un sous-projet sert de nom d'onglet Excel, qu'Excel unifie sans égard
  à la casse et mesure en unités UTF-16 ; le modèle garde ses codes tels quels, et c'est la
  génération des onglets qui désambiguïse (suffixe, troncature en unités UTF-16). Décision de
  l'auteur du 2026-11-07, option B ; reporté d'EP-04. US-1550 écrit la fonction qui nomme un
  onglet, commune aux formats Excel, et l'éprouve sur les onglets des postes et des lots du devis ;
  EP-09 l'applique aux codes des sous-projets du reste à engager.

Relevés par les revues locales d'EP-06 et reportés ici par l'auteur le 2026-11-08 :

- #2510, point 3 [EP-06] — `redate_copy` (`core/planning/interface/reference.py`) s'enregistre
  après `copy_nodes` : une facette qu'EP-07 copie à l'ouverture d'une révision s'enregistre
  avant lui, ou se redate elle-même.
- #2527 [EP-06] — le fuseau horaire de l'installation, dans lequel s'entend le jour courant
  (WF-EXP-0020-A, WF-PLA-0130-A, spécification 1.0.3), n'existe pas dans le back : le jour d'un
  changement d'état est pris en UTC. US-1550, qui clôt WF-EXP-0020-A, l'ajoute — une colonne
  d'`installation` dans la migration du socle, la valeur fixée par `waterfall-api install` avec un
  défaut livré — et branche dessus la fonction du jour courant qu'US-1380/L4 (#2519) a regroupée,
  avec un test de borne près de minuit.

## Conception

EP-07 est le quatrième EPIC de domaine du back, et le premier qui calcule des montants : il
ajoute la seconde facette de la table des nœuds d'EP-06, les tables images que la révision
conserve, un module du noyau, les routes de ses huit opérations nouvelles, le second format
d'échange sur la mécanique d'EP-06, la tranche des lignes du témoin, et il branche sur le service
les écrans du devis. Il **ne modifie pas le contrat**, figé en 1.0.0 : un manque devient une
« Interface contract issue » que l'auteur tranche. Ce qui suit fixe ce que chaque lot devrait sinon
décider seul. Il se livre pendant les lots d'EP-06, sur une branche tirée de la sienne : la section
« Ce qu'EP-06 écrit encore » dit ce que les lots d'EP-07 n'écrivent pas avant le lot d'EP-06 qui le
possède.

### Ce que le cadrage décide

Décisions de l'auteur du 2026-11-07, sur les questions du cadrage, chacune avec l'option écartée :

- **Neuf US, le socle en lot technique de la première**, lot pivot d'EP-09 ; quatre lectures
  indépendantes (les indicateurs, le plan de charge, la comparaison, les contributeurs) dans une
  même vague. Écartés : les indicateurs et le plan de charge en une US ; le passage En cours fondu
  dans la ligne.
- **Dix portées recalées** (voir « Exigences réalisées »), comme EP-06 l'a fait : une phrase de
  Vérif qui demande une ligne de provision, un différentiel, une fusion ou la déclaration d'un
  risque se clôt en EP-08, le reste à engager ou sa grille en EP-09, l'indice de coût en EP-10.
  Écarté : clore ici avec des écarts, contre la règle du README.
- **WF-IHM-0110, WF-INTF-0010 et WF-QUA-0040 entrent au tableau** en portée « début », pour que les
  US les citent et que les tests les nomment. Écarté : les laisser en « propre à l'US ».
- **La valeur planifiée est une fonction du noyau, sans écran** : `planned_value` de l'interface
  de `core/estimate`, le même module d'étalement que le plan de charge, éprouvée par les exemples
  chiffrés ; EP-10 branche les courbes (G-01, G-02 : aucun indicateur projet avant En cours), EP-08
  clôt. Écarté : la reporter à EP-10, qui réécrirait l'étalement.
- **Le plan de charge sert les trois bases** et toutes les phrases du Vérif sauf celle du reste de
  80 heures : sans réestimation, la charge restante d'une ligne est sa charge courante, et les
  tâches terminent déjà par `setTaskProgress` (EP-06). Écarté : la seule base de la référence.
- **La référence du témoin reste l'offre 100** jusqu'à la fusion de l'avenant 1 par EP-08 : la
  révision 101 est marquée sans être référence, WF-REV-0040 interdisant de la désigner après coup,
  et le chargeur ne contourne aucune règle (#1402). Les lectures du témoin se comparent aux
  exemples à la référence, aux provisions et aux montants qui en dépendent près, listés. Écartés :
  écrire `is_reference` autour des règles ; ne pas rejouer la désignation.
- **Les exemples du témoin projettent l'offre 100 depuis son année de référence, 2025** : le
  raccourci de #1628 (option 4 du 2026-10-29) se retire par un lot d'outil d'US-1570, avant la
  tranche des lignes, et le témoin chargé se compare aux exemples montants compris (README, « le
  calculé devient l'attendu, la spécification arbitre »). Écarté : garder le raccourci et une liste
  d'écarts connus que chaque EPIC suivant hériterait.
- **Les trois montants et l'année de consommation sont conservés** sur `estimate_line`, comme les
  dates des tâches d'EP-06, et recalculés dans la transaction de ce qui les change (« Le calcul des
  montants ») ; le tri et les bornes de `listNodes`, `compareRevisions` et WF-REV-0070 lisent des
  colonnes, et l'immuabilité d'une révision marquée protège les montants eux-mêmes. Écarté : le
  calcul à la lecture, qui chiffrerait cinq mille lignes à chaque lecture et laisserait le tri par
  montant à la mémoire.
- **Le montant budgété est conservé et fixé par la lignée** : à la création ou à la copie d'une
  ligne, celui de la ligne de même lignée dans la révision de référence, nul sans elle, confondu
  avec le réestimé sur un projet sans référence ; rafraîchi dans la révision en cours quand une
  référence est désignée, par un registre nouveau de `core/revisions` ; une révision marquée garde
  le sien pour toujours (WF-REV-0070). Les grandeurs de référence qu'EP-08 écrira à la fusion
  (`reference_quantity`, `reference_hours`, `reference_unit_disbursement`) naissent nulles dès la
  migration d'EP-07. Écartés : le budgété lu par la lignée à chaque lecture, qui changerait sur une
  révision marquée quand la référence se déplace ; laisser à EP-08 une migration sur
  `estimate_line`.
- **XlsxWriter écrit, openpyxl lit** : le prototype de la spécification
  (`docs/spec/exemples/prototype_devis.py`) est écrit avec XlsxWriter et ses leçons sur Excel et
  LibreOffice — totaux déclarés, formules qui nomment leur tableau, fonctions communes — sont
  acquises ; openpyxl lit les cellules saisies, et `check_xlsx.py` s'en sert déjà. Les deux entrent
  dans `backend/pyproject.toml` par le socle. Écarté : openpyxl seul, qui retraduirait le prototype.
- **Le logo est copié dans le paquet**, `core/estimate/excel/assets/waterfall_logo.png`, sa
  licence dans le fichier voisin `waterfall_logo.png.license` que REUSE admet : aucun lot d'EP-07
  n'écrit `REUSE.toml`, qu'US-1440/L1 #2337 possède encore. Écartés : la ligne dans `REUSE.toml`,
  qui attendait #2337 ; aucun logo, contre l'annexe B.
- **Les registres de `core/projects` sont déclarés par US-1490/L3, après US-1380/L3 #2338** —
  un seul, `register_estimate_facts` —, et celui de `core/cost_settings` par le socle : le socle
  (pivot d'EP-09) n'attend que #2328 et n'écrit ni `core/projects` ni `core/planning`. Écarté : un
  socle qui déclare tout et attend #2338, deux vagues d'EP-06 plus tard.
- **EP-07 complète `FacetHooks` et ses appels dans `core/planning`**, après le lot d'EP-06 qui
  possède chaque fichier, nommé par son numéro ; `planning` ne connaît toujours pas `estimate`, il
  appelle le registre. Écarté : `api/nodes.py` qui routerait par `kind` vers `estimate`, deux
  chemins d'écriture pour un même nœud.
- **La chronologie du témoin reçoit l'écriture `rate_update_applied`**, par le lot d'outil
  d'US-1570, et la désignation de l'offre cesse d'être attendue refusée par le chargeur. Écarté :
  une date lue dans un fichier du chargeur, deux sources pour un instant du témoin.
- **Le module est `core/estimate`** (FBS-4.4, « Chiffrage et devis »), et la fonction qui nomme un
  onglet Excel (#2190) vit dans son interface, qu'EP-09 importera : `core/exchanges` reste aux
  seuls lots d'EP-06. Écarté : la fonction dans `core/exchanges`, dont l'interface est écrite par
  trois lots d'EP-06.
- **Une seule migration, `0025`, dans le socle**, au prochain numéro libre à la création
  d'`epic/EP-07` — `epic/EP-06` s'arrête à `0024` —, aucune donnée à reprendre : les colonnes
  nouvelles de `revision` restent nulles et se lisent comme les valeurs du projet. Aucune migration
  d'EP-07 après le socle ; EP-09 chaîne la sienne sur `0025`. Écarté : une migration par US.

Décision de l'utilisateur du 2026-11-08, sur la question d'US-1490/L1 (#2370) :

- **Le socle enregistre « à vide » de façon neutre, et diffère `register_facet` à US-1490/L3.**
  `app.py` importe les interfaces qui remplissent les registres et `tests/conftest.py` importe
  `create_app` : tout enregistrement du socle vaut dans chaque processus de test, et trois d'entre
  eux heurtaient des tests d'EP-04 et d'EP-06 qui simulent eux-mêmes la part d'EP-07. Le socle
  enregistre donc `revision_has_lines` répondant oui tant que la ligne n'existe pas (rendue réelle
  par US-1490/L3, qui adapte alors `test_reference_designation.py`), le format `estimate` refusant
  toute en-tête par 422 `FILE_FORMAT_UNREADABLE` (rendu réel par US-1550), et les autres registres
  sans effet ; il n'enregistre pas la facette `estimate_line`, que `test_nodes_state.py` enregistre
  lui-même par un espion et que `register_facet` refuse en double : US-1490/L3 la crée et adapte
  ces deux tests. Le socle n'écrit aucun fichier de test d'EP-06 ; le test des points d'entrée
  (#2180) ne couvre la facette qu'à partir d'US-1490/L3. Écartés : le socle qui enregistre tout
  réellement et réécrit quatre fichiers de tests d'EP-04 et d'EP-06, dont deux que des lots d'EP-06
  en cours possèdent ; différer aussi `lines` et le format, qui laissait le test des points d'entrée
  sans trois registres de plus pour rien ; attendre la fusion des lots d'EP-06 concernés, qui
  retardait le pivot d'EP-09.

### Tables et migrations

Régime « révisionné » (§4.4.1), partitionnées par projet comme `node`, pour `estimate_line` et les
quatre tables images ; UUID v7 engendrés par le service, ou imposés par le chargeur ; colonnes
d'audit et `lock_version` sur `estimate_line` ; textes en collation `C` ; règles SQL du guide. Chaque
clé refuse (`RESTRICT`), sauf la clé composite de la facette vers son nœud, en cascade : la ligne
suit sa tâche (WF-DAT-0090), et les images suivent leur révision abandonnée par `register_closing`
avant toute cascade ; une révision marquée ne supprime rien, ses déclencheurs le refusant.

| Table | Contenu | Contraintes |
|---|---|---|
| `estimate_line` | `project_id`, `node_id` (clé primaire avec lui), `kind` (`CHECK (kind = 'estimate_line')`, clé composite (`project_id`, `node_id`, `kind`) vers `node` en cascade, sur le modèle de `task`), `label`, `cost_category_id`, `resource_role_id` (nul hors main-d'œuvre), `quantity` (`numeric(14,4)`), `hours` (`numeric(12,2)`, nul hors main-d'œuvre), `unit_disbursement` (`numeric(14,2)`, nul en main-d'œuvre), `payment_delay_days`, `subproject_id` (nul hors sous-projet), `reference_quantity`, `reference_hours`, `reference_unit_disbursement` (nuls : écrits par la fusion d'un avenant, EP-08), `base_amount`, `budgeted_amount`, `reestimated_amount` (`numeric(14,2)`), `consumption_year`, audit, `lock_version` | `label` de 1 à 300 non blanc ; `quantity ≥ 0`, `hours ≥ 0`, `unit_disbursement ≥ 0`, `payment_delay_days ≥ 0` ; `(resource_role_id IS NULL) = (hours IS NULL)` et `(resource_role_id IS NULL) = (unit_disbursement IS NOT NULL)` — EP-08 les assouplit pour la ligne de provision — ; clés vers `cost_category`, `resource_role` et `(project_id, subproject_id)` vers `subproject` en refus ; index sur (`project_id`, `cost_category_id`), (`project_id`, `resource_role_id`), (`project_id`, `subproject_id`) pour les questions du référentiel ; déclencheur d'immuabilité comme `task` |
| `revision_rate` | `project_id`, `id`, `revision_id`, `cost_category_id`, `amount` (`numeric(12,2)`), `origin` (`reference`, `projected`) | unique (`revision_id`, `cost_category_id`) ; clé composite vers `revision` en refus ; `amount ≥ 0.01` ; déclencheur d'immuabilité |
| `revision_role` | `project_id`, `id`, `revision_id`, `resource_role_id`, et les colonnes de `ResourceRoleImage` : `code`, `label`, `org_node_id`, `org_node_label`, `cost_category_id`, `cost_category_label`, `calendar_id`, `calendar_label`, la capacité, `is_active`, l'audit et le compteur de l'objet au marquage | unique (`revision_id`, `resource_role_id`) ; clé composite vers `revision` en refus ; déclencheur d'immuabilité |
| `revision_calendar` | `project_id`, `id`, `revision_id`, `calendar_id`, `label`, les sept heures de `WeeklyHours`, `is_default`, `is_active`, l'audit et le compteur au marquage (`CalendarImage`) | unique (`revision_id`, `calendar_id`) ; idem |
| `revision_category` | `project_id`, `id`, `revision_id`, `cost_category_id`, `code`, `label`, `cost_type_id`, `cost_type_label`, `cost_type_kind`, `cost_type_is_active`, `accounting_code`, `is_active`, l'audit et le compteur au marquage (`CostCategoryImage`) | unique (`revision_id`, `cost_category_id`) ; idem |
| `revision` | reçoit `inflation_rate` et `win_probability` (`numeric(5,4)`, nuls : les valeurs du projet, que le code lit encore ; écrits au marquage) | aucune autre contrainte ; `copy_revision` ne les reprend pas (la révision en cours suit le projet) |

- **Une migration, `0025`, dans le socle** (US-1490/L1) : les cinq tables, les deux colonnes de
  `revision`, `create_project_partitions` remplacée pour qu'elle crée leurs partitions
  (`estimate_line_p_<uuid>`, `revision_rate_p_<uuid>`…) et celles des projets existants, les
  déclencheurs d'immuabilité sur le modèle d'EP-06, les droits du rôle du service — `SELECT`,
  `INSERT`, `UPDATE`, `DELETE` : une ligne et un taux conservé d'une révision en cours se modifient
  et se suppriment, une image s'écrit une fois — déclarés dans `SERVICE_RIGHTS`. Aucune migration de
  données : rien n'existe à reprendre.
- **L'immuabilité** : une fonction de déclencheur par table, dans le module `estimate`, qui lit
  l'état de la révision par `revision_id` sous `FOR KEY SHARE`, comme `cost_structure` et `task`.
  Elle protège les montants conservés (WF-REF-0130, WF-REV-0070) autant que les grandeurs.
- Les tests : `test_migrations.py` (schéma, droits, partitions d'un projet créé),
  `test_database_constraints.py` (une contrainte, un test), `test_revision_immutability.py`
  étendu aux cinq tables.

### Modules

| Module | Tables | Interface offerte |
|---|---|---|
| `waterfall.core.estimate` (FBS-4.4) | `estimate_line`, `revision_rate`, `revision_role`, `revision_calendar`, `revision_category` | les crochets de la facette pour `planning` (`FacetHooks` : lire, créer, instantané, restituer, juger une cellule, rechiffrer, `calendar_of`) ; une ligne modifiée (`update_line`) ; les filtres, le tri et les totaux des lignes pour `listNodes` ; `pricing` (pur : le montant d'une ligne, sa projection) et `spreading` (pur : l'étalement au prorata des heures d'un calendrier, par année ou par mois) ; `estimate_indicators`, `missing_rates` ; `workload`, `planned_value` ; `compare_revisions` ; les taux d'une révision — `rate_update_proposal`, `apply_rate_update`, la copie des taux, l'instantané au marquage, le budgété rafraîchi à la désignation — ; `category_is_employed`, `subproject_is_cited`, `subproject_is_estimated`, `roles_employed` et `reinflate_project` pour les registres de `cost_settings` et de `projects` ; `revision_has_lines` ; `idle_tasks_for_role_calendar` pour `resource_settings` ; le format et l'exporteur `estimate`, `sheet_name` ; `load_*` avec identifiants et instants imposés |

- **La couche** : `estimate` importe les interfaces de `planning`, `revisions`, `projects`,
  `cost_settings`, `resource_settings`, `users` (les comptes des propositions) et `exchanges` ; aucun
  d'eux ne l'importe — ils appellent des registres. Le contrat d'import-linter de
  `backend/pyproject.toml` le déclare (socle).
- **Le calendrier applicable** d'une tâche devient l'intersection des calendriers des rôles de
  ses lignes de main-d'œuvre, le calendrier par défaut sans elles : `calendar_of(task)` d'EP-06
  reçoit les calendriers par le crochet de la facette ; une ligne dont le rôle ne recouperait
  aucune heure est refusée (`TASK_WITHOUT_WORKING_HOURS`), et la garde
  `register_idle_task_guard` juge aussi les calendriers des rôles (`updateCalendar`,
  `updateResourceRole`).
- **Les commandes** : `apply_rate_update` et `export_estimate` entrent dans `REVISION_RULES` de
  `core/revisions/commands.py` — `revisions.write` et `rate_update_available` ; `estimate.read`,
  présente ou absente —, `import_estimate` dans celles de `core/projects/commands.py`
  (`estimate.write`, `project_before_in_progress` dès En cours, puis `no_background_task_running`,
  `may_create_revision`) ; les deux fichiers sont encore écrits par EP-06 (« Ce qu'EP-06 écrit
  encore »).

### Les points d'extension

Chaque registre est un `Registry` de `core/revisions/registry.py`, rempli à l'import de
`core/estimate/interface`, et le test des points d'entrée d'EP-06 (#2180) — l'API, le worker, le
chargeur — s'étend à chacun.

| Module | Registre | Qui le déclare | Qui le remplit | Ce qu'il fait |
|---|---|---|---|---|
| `core/planning` | `register_facet` (EP-06) | EP-06 | `estimate` (`estimate_line`), dès US-1490/L3 — non le socle (2026-11-08) | `listNodes` lit la facette, la copie et la suppression l'emportent, `calendar_of` lit ses rôles ; **complété par EP-07** : `create` (la facette d'un nœud créé, sa charge utile opaque pour `planning`), `snapshot`/`restore` (ses lignes de `estimate_line` pour l'historique), `judge_cell` (une cellule collée, dans l'ordre de `NodeColumn`), `reinflate` (les montants des lignes des nœuds redatés ou déplacés, rendus dans `reinflated`), `filters`/`sort`/`totals` (les colonnes de la ligne) |
| `core/revisions` | `register_copy` (EP-04) | EP-04 | `estimate`, après `planning` | la copie des lignes (par les identifiants des nœuds copiés) et des taux conservés, projetés si l'année change |
| `core/revisions` | `register_tasks_and_lines` (EP-04) | EP-04 | `estimate` (`revision_has_lines`) | la désignation exige une ligne |
| `core/revisions` | `register_closing` (EP-06) | EP-06 | `estimate` | à l'abandon, les taux conservés supprimés (les lignes suivent les nœuds) |
| `core/revisions` | `revisions.rate_update` (`register_rate_update`) | US-1500/L1 | `estimate` (`rate_update_offered`) | la condition `rate_update_available` de `apply_rate_update` : la proposition des taux d'une révision en cours présente une catégorie |
| `core/revisions` | `register_marking` (nouveau) | socle d'EP-07 | `estimate` | dans la transaction du marquage, avant `compute_indicators` : les images des rôles, calendriers et catégories employés et des taux retenus, `revision.inflation_rate` et `win_probability` |
| `core/revisions` | `register_designation` (nouveau) | socle d'EP-07 | `estimate` | après la désignation d'une référence : le budgété des lignes de la révision en cours rafraîchi par la lignée |
| `core/cost_settings` | `register_employment` (nouveau) | socle d'EP-07 | `estimate` | `category_is_employed` d'EP-05 rempli ; la modification du type d'une nature et le rattachement d'une catégorie employée refusés |
| `core/projects` | `register_estimate_facts` (nouveau) | US-1490/L3, après #2338 | `estimate` | `subproject_is_cited` et `subproject_is_estimated` (la suppression d'un sous-projet), `roles_employed` (`listContributorSuggestions`), `reinflate_project` (`updateProject` rechiffre la révision en cours quand l'inflation change) |
| `core/resource_settings` | `register_idle_task_guard` (EP-06) | EP-06 | `estimate` | les calendriers des rôles des lignes, projets nommés par `params.projects` |
| `core/exchanges` | `register_format`, `register_exporter` (EP-06) | EP-06 | `estimate` (`estimate`) | l'en-tête, l'analyse, l'application et l'export du devis |
| `witness/revisions` | `register_revision_filler` (EP-06) | EP-06 | `witness/estimate_lines` | les lignes de chaque révision écrites après ses tâches et avant son marquage |

### Le calcul des montants

- **Le montant de base** d'une ligne (`base_amount`) : quantité × charge × taux horaire de sa
  catégorie pour l'année de référence de la révision — le taux conservé (`revision_rate`) s'il
  existe, celui du référentiel (`hourly_rate`) sinon — pour une ligne de main-d'œuvre ; quantité ×
  débours sinon ; en `Decimal`, arrondi au centime (`ROUND_HALF_EVEN`) une fois par ligne, pour que
  la somme ne dépende pas de l'ordre (WF-DAT-0100). Sans taux ni conservé ni du référentiel, la
  ligne n'a pas de montant : la saisie est refusée (`HOURLY_RATE_MISSING`) ; une ligne existante
  dont le taux manque après une correction du référentiel garde ses montants et `getMissingRates`
  la nomme — ce cas ne se produit que si un taux est retiré, ce que le référentiel ne fait pas.
- **L'année de consommation et la projection** : `spreading` répartit les heures travaillées de
  la tâche porteuse entre les années, sur le calendrier du rôle de la ligne (celui de la tâche
  hors main-d'œuvre), par arithmétique sur les semaines pleines et les jours restants, sans boucle
  sur les jours ; chaque part est projetée d'une fois le taux d'inflation par année écoulée depuis
  l'année de référence, et le réestimé est la somme des parts projetées, arrondie une fois au
  centime — jamais une somme de parts arrondies, pour que WF-DAT-0100 tienne sur une ligne à cheval
  sur deux années — ; `consumption_year` est l'année de la part la plus lourde, la première à
  égalité. Le taux d'inflation est celui du
  projet pour la révision en cours, celui conservé pour une révision marquée.
- **Le budgété** suit « Ce que le cadrage décide » : fixé par la lignée à la création et à la copie,
  rafraîchi à la désignation ; la projection du budgété est celle de la référence, conservée avec
  lui — il ne suit pas les dates de la révision courante (`NodeInflation`).
- **Les déclencheurs du recalcul**, chacun dans sa transaction, sous le verrou de la structure :
  l'écriture de la ligne (création, modification, collage, import, annulation) ; le redatage de sa
  tâche par toute écriture de `planning` et par `reschedule_current_structures` (unités de durée,
  calendriers), par le crochet `reinflate` que `planning` appelle avec les tâches redatées ; le
  déplacement d'une ligne ou de sa tâche ; la mise à jour des taux (`applyRateUpdate`) ; le taux
  d'inflation du projet (`updateProject`, par `register_estimate_facts.reinflate_project`) ; un taux
  du référentiel écrit pour une catégorie sans taux conservé (`setHourlyRate`, par
  `register_employment` qui rend les révisions en cours à rechiffrer) ; la désignation (le budgété).
  Chaque recalcul rend les lignes et tâches dont un montant change (`reinflated`) et les totaux.
- **Les totaux d'une tâche** (`TaskFacet.base_amount`, `budgeted_amount`, `reestimated_amount`) sont
  la somme de ses lignes et de ses subordonnées, calculée à la lecture par `listNodes` et aux
  `ancestors` des écritures — ils ne sont pas conservés, une somme se refaisant sans perte.
- **Les indicateurs** sont des sommes des montants conservés : `total` et ses ventilations sur le
  réestimé, le budget de référence sur le budgété hors provision ; un montant non calculable
  (`hourly_rate_missing`) ne se présente que pour une ligne sans montant, cas qu'une saisie refuse
  — l'enveloppe `Computable` est servie telle que le contrat la lit.

### L'instantané et les taux

- **La révision en cours suit le référentiel** pour ses rôles, calendriers et catégories, et ne
  conserve que ses taux (`RevisionSnapshot` du contrat) : `revision_rate` porte, pour les
  catégories qu'une révision copiée employait, le taux copié (`reference`) à année égale, projeté
  (`projected`) sinon, remplacé par celui du référentiel pour les catégories que `apply_rate_update`
  de `createRevision` retient ; la première révision d'un projet n'en a aucun.
- **La proposition** (`getRateUpdateProposal`) liste chaque catégorie de main-d'œuvre employée
  dont le taux conservé est `projected` : `previous_amount` le taux projeté, `proposed_amount` et
  `source` le taux du référentiel pour `target_year` (`reference_rate`) ou, sans lui, le taux
  projeté (`inflated_previous`) ; `applyRateUpdate` écrit `reference` sur les catégories retenues
  et rechiffre.
- **Au marquage**, `register_marking` écrit les images des rôles, calendriers et catégories que les
  lignes emploient — un calendrier par rôle employé, le calendrier par défaut compris —, un
  `revision_rate` pour chaque catégorie de main-d'œuvre employée sans taux conservé (celui du
  référentiel, `reference`), `inflation_rate` et `win_probability` du projet ; `getRevision` rend
  `snapshot` d'une révision marquée seule.
- **Une révision marquée se lit sur ses images** : les libellés de `EstimateLineFacet`, les
  calendriers de l'export MS Project, la comparaison ; une révision en cours sur le référentiel.

### Le format Excel du devis

- **L'écriture** (XlsxWriter) suit le prototype de la spécification et l'annexe B : « Présentation »
  (format et version en A1-B2, l'entreprise de `getReferenceSettings`, le client, le projet, la
  révision, la structure, l'année de référence, la devise, la date, la ventilation par nature) ;
  « Devis » (une ligne par lot, par poste, par lot hors postes, « Hors lot », avec `SOMME.SI.ENS`
  sur les onglets de lignes, la case « Inclus ») ; un onglet par poste (« 1.1 Libellé »), par lot et
  « Hors lot », chacun un tableau Excel à ligne de total déclarée, listes de validation sur
  « Tâches » et « Paramètres », colonnes calculées par formule qui nomme son tableau, lignée dans une
  colonne masquée ; « Tâches » (lignée, numéro, libellé, onglet, dates, description) et
  « Paramètres » (rôles, catégories hors main-d'œuvre, taux retenus, sous-projets), protégés ; le
  logo et le pied de page sur chaque onglet ; aucun texte saisi écrit comme formule
  (`strings_to_formulas` faux). `sheet_name` ramène un nom aux règles d'Excel : caractères refusés
  remplacés, 31 unités UTF-16, unicité sans égard à la casse par un suffixe ` (2)` ; EP-09
  l'importe pour les codes des sous-projets (#2190).
- **La lecture** (openpyxl, `read_only`, valeurs) : l'en-tête d'abord — format « Devis », version
  connue (`FILE_FORMAT_UNREADABLE`, `expected_format`, `expected_version`) —, puis chaque onglet de
  lignes par ses en-têtes ; les colonnes lues sont la tâche, le rôle ou la catégorie, la
  désignation, la quantité, les heures, le débours unitaire, le délai de paiement, le sous-projet et
  la lignée ; une ligne vide ou de total ignorée, une colonne inconnue ignorée, un nombre en texte
  rejeté (`NUMBER_INVALID`), chaque rejet par son onglet et son numéro de ligne Excel.
- **L'analyse** rapproche par la lignée, puis désigne la tâche par « Tâches » ou par son libellé
  (`AMBIGUOUS_TASK_LABEL`, `UNKNOWN_TASK`), crée les lignes sans lignée, met à jour les autres sans
  toucher leur budgété, supprime les absentes sauf sous une tâche démarrée ou terminée (`kept`),
  rejette une ligne nouvelle sous une tâche terminée de la structure principale
  (`task_not_completed`), un rôle ou un sous-projet inconnu, une catégorie de provision
  (`PROVISION_CATEGORY_RESERVED`), une ligne qui laisserait sa tâche sans heure
  (`TASK_WITHOUT_WORKING_HOURS`), et présente les écarts (`differences`) ; **l'application** écrit
  par les mêmes fonctions que la saisie, sous le verrou de la structure, dans la transaction de la
  tâche d'EP-06, sans entrée d'historique ; `ProjectCommand.import_estimate` dit la phase.
- **L'export** s'enregistre par `register_exporter` : la révision et la structure nommées, le
  fichier `.xlsx`, `media_type`
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, le nom
  `<code ou libellé du projet>-<version>-devis.xlsx` ; le stockage, le téléchargement et la purge
  sont ceux d'EP-06.

### Le service d'API

- Un routeur par US — `api/estimate_lines.py` (US-1490 : `updateEstimateLine`),
  `api/rate_update.py` (US-1500 : `getRateUpdateProposal`, `applyRateUpdate`),
  `api/estimate_indicators.py` (US-1510 : `getEstimateIndicators`, `getMissingRates`),
  `api/workload.py` (US-1520), `api/comparison.py` (US-1530) —, créés vides et enregistrés dans
  `app.py` par le socle, chacun avec son `asked_*.py` ; `listContributorSuggestions`
  (`api/contributors.py`, EP-04) et `getRevision` (`api/revisions.py`, le `snapshot`) sont des
  routes existantes qu'US-1540 et US-1500 complètent ; `createNode`, `deleteNode`, `moveNodes`,
  `listNodes`, `previewPaste`, `applyPaste`, `openImport`, `requestExport` restent aux routeurs
  d'EP-06, qui appellent les registres.
- Chaque route déclare `RequiresProject(...)` : `estimate.read` pour les lectures, la qualité de
  contributeur et `estimate.write` pour `updateEstimateLine`, `revisions.write` pour
  `applyRateUpdate`, la proposition `getRateUpdateProposal` se lisant sous `revisions.read`, comme
  le contrat la range sous `revisions` à côté de `getRevision`, qui sert déjà l'instantané des
  taux ; les refus sont ceux du contrat, dans l'ordre que chaque opération écrit ;
  chaque réponse d'un test passe par `ContractClient` ; `test_access_evaluation.py` reçoit chaque
  opération avec ses deux termes.

### Le worker

Aucun gestionnaire nouveau : l'import, l'export et le marquage sont ceux d'EP-06 et d'EP-04, qui
appellent les registres. Le worker doit importer l'interface d'`estimate` pour les remplir
(#2180) ; `worker/main.py` est encore écrit par US-1420/L2 #2341 : l'import est du lot d'US-1500
qui écrit le marquage, après #2341. Jusque-là, un marquage dans le worker n'écrit pas d'image, et
le test des points d'entrée (#2180), que le socle étend, dit explicitement que les extensions
d'`estimate` ne sont attendues du worker qu'à partir de ce lot — l'API et le chargeur les
attendent dès le socle —, pour qu'il ne soit pas rouge entre les deux.

### Le chargeur du témoin

- **Un lot d'outil**, dans `wftools` : `mockdating` projette l'offre depuis 2025, les exemples se
  régénèrent, `DECISIONS.md` retire le raccourci de L-01 ; la chronologie exportée reçoit
  l'écriture `rate_update_applied` (révision 101, 12 janvier 2026, 10 h 15, les deux catégories) ;
  `make mock-data` écrit `fixtures/api/witness_lines.json` : pour chaque révision de PRJ-001 (100,
  101, 102), ses lignes par lignée — la tâche porteuse par sa lignée, le rang parmi les lignes, la
  facette saisie — ; le back le lit par un modèle propre, strict, sans importer `wftools`.
- **La tranche** : `witness/estimate_lines.py` s'enregistre par `register_revision_filler`, après
  `witness/tasks.py` (l'ordre de l'enregistrement, par l'import dans `chronology.py`), et réconcilie
  par lignée les lignes que la copie a données avec celles du fichier — création, modification,
  suppression — par l'interface d'`estimate`, identifiants et instant imposés ;
  `witness/revisions.py` applique `rate_update_applied` par `apply_rate_update` et attend que la
  désignation de l'offre aboutisse (`designation_attempted` devient une désignation réussie, un
  refus arrêtant la commande), le passage En cours constaté par les transitions. Entre la tranche
  des tâches d'EP-06 (US-1480/L2 #2347) et celle des lignes, la désignation attendue refusée l'est
  faute de lignes, non plus faute de tâches : le chargeur d'EP-06 ne doit pas tester le motif du
  refus, seulement la condition `revision_has_tasks_and_lines` — une ligne pour le pilote d'EP-06.
  Les montants sont ceux que le service calcule : le calculé devient l'attendu.

### Le front

- Les écrans sont ceux d'EP-02, d'EP-14 et d'EP-15 ; chaque US branche le sien et retire
  `MockupNotice` de la page qu'elle sert en dernier : le plan de charge par US-1520, le devis par
  US-1560 ; les révisions et les paramètres du projet l'ont perdu par EP-04. Les aides
  `frontend/help/fr/FBS-4.4*.md` disent ce que le service fait, par US-1560 ; `FBS-4.2.4.md`
  (contributeurs) par US-1540.
- Le front ne calcule rien : les montants, les parts, les écarts et les propositions viennent du
  service. Un manque que le branchement révèle devient une issue ; un manque du contrat, une
  « Interface contract issue ».

### Le harnais

Chaque US étiquette `@shared` les tests dont l'écran est servi : US-1520 `workload.spec.ts` ;
US-1530 `revisions.spec.ts` (`BEFORE_EP07` levé, la proposition des taux comprise, après US-1500) ;
US-1540 le jumeau des contributeurs et le cycle (`revision-cycle.spec.ts`) ; US-1550 l'import en
deux temps d'`exchanges.spec.ts` ; US-1560 `entry.spec.ts`, `computed.spec.ts`, `keyboard.spec.ts`,
`paste.spec.ts`, `undo.spec.ts`, la part du devis de `grid.spec.ts`, `structure.spec.ts` et
`context.spec.ts` (`BEFORE_THE_DATA` levé pour le devis). Les parcours qui écrivent le font sur un
projet que la course crée (#2193) ; ceux qui lisent le devis propre d'un risque restent gardés par
`inService` jusqu'à EP-08, et le guide le dit. La liste des entrées non rejouées n'est écrite que
par US-1570/L3.

### Les tests du back

Un fichier par objet et par règle — `test_estimate_lines.py`, `test_estimate_lines_move.py`,
`test_pricing.py` (pur), `test_spreading.py` (pur), `test_estimate_hooks.py` (la facette dans
`planning` : création, historique, collage, redatage), `test_revision_snapshot.py`,
`test_rate_update.py`, `test_estimate_indicators.py`, `test_workload.py`, `test_planned_value.py`,
`test_comparison.py`, `test_contributor_suggestions.py`, `test_in_progress.py`,
`test_estimate_excel_write.py`, `test_estimate_excel_read.py`, `test_estimate_import.py`,
`test_estimate_export.py`, `test_witness_lines.py` —, chaque test citant son exigence, chaque réponse
validée contre le contrat ; les exemples chiffrés des Vérif sont des tests sans base quand ils le
peuvent (`tests/examples`). Les fixtures communes — une structure avec ses tâches et ses lignes par
l'interface, une référence désignée, l'horloge posée — vivent dans `tests/estimate_support.py`,
écrit par le socle. Un test de concurrence par règle d'ensemble : deux écritures d'une même ligne,
deux mises à jour des taux, un marquage pendant une saisie.

### Ce qu'EP-06 écrit encore

Les lots d'EP-07 se livrent pendant ceux d'EP-06, et `epic/EP-07` reprend `epic/EP-06` à chaque
fusion. Un fichier qu'un lot d'EP-06 non fusionné possède, les lots d'EP-07 ne l'écrivent pas avant
ce lot, ou en dépendent par son numéro :

| Fichier | Lot d'EP-06 qui le possède | Lots d'EP-07 qui l'attendent |
|---|---|---|
| `core/planning/interface/{nodes,facets}.py` (lecture, création, `snapshot`) | US-1380/L2 #2335 | tout lot qui crée ou lit une ligne (US-1490/L2 et suivants) |
| `core/planning` : suppression, déplacement ; `core/projects` (`register_attachments`) | US-1380/L3 #2338 | US-1490/L3, US-1500, US-1540 |
| `core/planning` : `setPredecessors`, les registres de `resource_settings` (`reschedule_current_structures`) | US-1390/L2 #2339 | US-1500 (la garde des calendriers des rôles) |
| `core/planning` : le collage (`previewPaste`, `applyPaste`), `api/history.py` | US-1450/L2 #2344, puis US-1450/L5 (le collage qui crée, #2559) | US-1560 (le jugement des cellules de la ligne) |
| `core/revisions/commands.py` (`export_*`), `api/tasks.py` | US-1430/L2 #2336 | US-1500 (`apply_rate_update`), US-1550 (`export_estimate`) |
| `core/projects/commands.py` (`manage_timelines`, `generate_skeleton`) | US-1400/L1 #2331, US-1460 #2325 | US-1550 (`import_estimate`), après les deux |
| `core/exchanges` (la mécanique d'import, les formats) | US-1420/L1 #2332 | US-1550 (la lecture, l'analyse et l'application du classeur ; son écriture, pure, n'en a pas besoin) |
| `worker/main.py`, les Compose, `production.env.example`, le Makefile | US-1420/L2 #2341 | US-1500 (l'import de l'interface dans le worker) |
| `REUSE.toml`, `LICENSES/` | US-1440/L1 #2337 | aucun : le logo porte son fichier `.license` |
| `wftools`, `make mock-data` | US-1480/L1 #2330, US-1450/L4 (le collage qui crée, #2559) | US-1570/L1 |
| `witness/tasks.py` | US-1480/L2 #2347 | US-1570 (la tranche des lignes, après les tâches) |
| le guide, la liste des entrées non rejouées | US-1480/L3 #2348 | US-1570/L3 |
| `app.py`, `pyproject`, `tests/planning_support.py`, `witness/revisions.py`, `chronology.py` | US-1380/L1 #2328, fusionné avant la branche | aucun |

`conftest.py`, `support.py`, `api/queries.py`, `loader.py` et `mode.ts` ne s'écrivent dans aucun
des deux EPIC : une fixture qui manque devient une issue. Les catalogues `messages/*.json` ne
s'écrivent que par le lot qui ajoute un code d'erreur au contrat, pour sa seule clé
`errors.<CODE>` et son test (décision du 2026-11-08, EP-06, « Les catalogues du front et le
collage », #2537), et par le lot qui porte un écran, pour les clés non-erreur de ce seul écran
(amendement du 2026-11-08, #2559, #2563) ; toute autre clé manquante devient une issue.

### L'ordre de construction

Le socle d'abord, puis ce qui ne dépend que de lui, la ligne dès que l'arbre d'EP-06 est là, les
quatre lectures en une vague large, les écrans par l'US qui sert leur objet, la vérification
d'ensemble en dernier ; le plan de lots (étape 3) le détaille en vagues.

1. **US-1490/L1**, le socle — dès la fusion d'US-1380/L1 #2328 et d'US-1420/L2 #2341, dont la
   migration `0024` porte celle du socle (#2341) : la migration `0025`, le module
   `core/estimate` à vide avec son interface en paquet (un fichier par objet) — hors les
   sous-paquets `pricing/` et `spreading/`, que leurs lots possèdent entiers, comme le socle
   d'EP-06 ne créait pas `scheduling/` : l'interface d'`estimate` ne les importe qu'une fois leurs
   lots fusionnés —, les trois registres nouveaux de `core/revisions`
   (`register_marking`, `register_designation`) et de `core/cost_settings` (`register_employment`),
   l'enregistrement à vide, neutre, dans ceux d'EP-04 et d'EP-06 (`register_copy`,
   `register_tasks_and_lines`, `register_closing`, `register_format`, `register_exporter`,
   `register_idle_task_guard`, `register_revision_filler` — hors `register_facet`, différé à
   US-1490/L3 ; décision du 2026-11-08), les cinq routeurs vides dans `app.py` et
   leurs `asked_*`, XlsxWriter et openpyxl dans `pyproject`, le contrat de couches,
   `tests/estimate_support.py` et les fichiers de tests, `witness/estimate_lines.py` à vide enchaîné
   dans `chronology.py`, le test des points d'entrée étendu. **Lot pivot d'EP-09** : `epic/EP-09` se
   tire d'`epic/EP-07` dès sa fusion. Il lui garantit `estimate_line` avec ses grandeurs courantes
   et de référence, ses trois montants, son délai de paiement et son sous-projet, les tables
   images, l'interface d'`estimate` déclarée — dont `update_line`, que `setLineRemaining` étendra,
   et `revision_has_lines` —, et la chaîne des migrations arrêtée à `0025`. En parallèle, dès la
   branche : **les modules purs** `pricing` et `spreading` (US-1490, US-1520) et **le lot d'outil**
   d'US-1570 (les exemples depuis 2025, la chronologie, `witness_lines.json`, après #2330).
2. **La ligne** (US-1490 : la facette lue et créée, `updateEstimateLine`, le calcul, après #2335 ;
   puis la suppression, le déplacement, les questions de `core/projects` et de `cost_settings`,
   après #2338), **l'instantané et les taux** (US-1500 : la copie des taux, la proposition, la mise à
   jour, le marquage, la désignation, les gardes, après #2336, #2339 et #2341 pour ce qui les
   touche ; l'inflation du projet après US-1490/L3, qui déclare `register_estimate_facts`),
   **l'écriture du classeur** (US-1550, pure : XlsxWriter n'a besoin de rien d'EP-06, seul
   l'enregistrement par `register_exporter`, déclaré par le socle d'EP-06, le relie à
   `core/exchanges`).
3. **Les quatre lectures** (US-1510, US-1520, US-1530, US-1540) et **la lecture et l'analyse du
   classeur** (US-1550), après la ligne.
4. **La grille de devis** (US-1560, le collage après #2344), **l'export et l'import branchés**
   (US-1550, après #2336 et #2325), **la tranche des lignes** (US-1570, après #2347), après tout ce
   qui écrit ; puis **la vérification d'ensemble** (US-1570, après #2348), seule.

---

## US-1490 — La ligne de devis : sa facette, ses grandeurs, son montant et son année de consommation

- **statut** : fini
- **exigences** : `WF-DEV-0020-A`, `WF-DEV-0030-A`, `WF-DEV-0040-A`, `WF-DEV-0010-A`,
  `WF-PLA-0010-A`, `WF-DAT-0090-A`, `WF-DAT-0100-A`, `WF-DAT-0010-A`, `WF-DAT-0020-A`,
  `WF-DAT-0080-A`, `WF-REF-0040-A`, `WF-IHM-0110-A`
- **opérations** : `createNode`, `updateEstimateLine`, `deleteNode`, `moveNodes`, `listNodes`,
  `getComputedValueDependencies`, `resolveRowNumber` ; `deleteSubproject`, `updateCostCategory`
  pour ce que les lignes leur refusent
- **issue** : 2361

**En tant que** chef de projet, **je veux** accrocher des lignes de devis aux tâches de ma
structure principale — une ligne de main-d'œuvre avec son rôle et sa charge, une ligne hors
main-d'œuvre avec son débours —, les modifier, les déplacer et les supprimer, et lire pour chacune
son montant aux taux de l'année de référence, son montant réestimé et son montant budgété, calculés
par le serveur sur l'année où sa tâche la consomme, **afin de** chiffrer mon projet sur son planning
sans construire un second arbre.

**Critères d'acceptation.**

- `WF-DEV-0020-A` — « Une ligne de main-d’œuvre refuse la saisie d’un débours ; une ligne hors
  main-d’œuvre refuse celle d’une charge et d’un rôle. » : 422 `VALIDATION_FAILED`,
  `FIELD_NOT_ACCEPTED` sur le champ, à la création (`EstimateLineWrite`) comme à la modification
  (`EstimateLineUpdate`) ; un rôle envoyé fait de la ligne une ligne de main-d'œuvre ;
- `WF-DEV-0020-A` — « Pour une ligne consommée dans l’année de référence, le montant d’une ligne de
  main-d’œuvre est le produit de sa quantité, de sa charge et du taux horaire de sa catégorie pour
  cette année ; pour une ligne consommée deux ans plus tard, avec un taux d’inflation de 3 %, il
  vaut ce produit fois 1,0609 (WF-DEV-0030). » : un test sans base du module de calcul, et le même
  sur le service, la tâche porteuse datée deux ans après l'année de référence ;
- `WF-DEV-0020-A` — « Aucun des deux montants n’est saisissable. » : ni `EstimateLineWrite` ni
  `EstimateLineUpdate` n'ont de champ pour eux, un champ inconnu est refusé (422), et
  `getComputedValueDependencies` nomme ce dont chacun dépend — `hourly_rate` ou
  `unit_disbursement`, `reference_revision`, `remaining_reviews`, `inflation` ;
- `WF-DEV-0020-A` — « La saisie d’une charge de 80 heures sur une ligne de quantité 1 budgétée à
  100 heures, consommée dans l’année de référence, donne un montant réestimé de 80 fois le taux et
  laisse le montant budgété inchangé. » : sur la révision en cours d'un projet dont la référence
  porte la ligne à 100 heures, `updateEstimateLine` écrit la charge, `reestimated_amount` suit et
  `budgeted_amount` reste celui de la référence ;
- `WF-DEV-0020-A` — « La création à la main d’une ligne dont la catégorie relève d’une nature de
  type provision pour risques est refusée. » : 422 `VALIDATION_FAILED`,
  `PROVISION_CATEGORY_RESERVED` sur `/estimate_line/cost_category_id`, à la création comme à la
  modification ;
- `WF-DEV-0020-A` — « Une ligne créée dans la révision de référence porte des montants budgété et
  réestimé égaux ; une ligne créée après porte un montant budgété nul. » : la ligne d'une révision
  marquée puis désignée référence porte les deux montants égaux ; une ligne de la révision en cours
  sans lignée dans la référence porte un budgété nul ; sur un projet sans référence, les deux sont
  confondus (WF-DEV-0050) ;
- `WF-DEV-0020-A` — « La catégorie d’une ligne de main-d’œuvre n’est pas saisissable : c’est celle
  de son rôle. » : `estimate_line.cost_category_id` dans `computed_fields`, une autre catégorie
  refusée par `COMPUTED_VALUE`, la sienne acceptée, un rôle changé lui donnant sa catégorie ;
- `WF-DEV-0030-A` — « Une même ligne consommée deux ans après l’année de référence, avec un taux
  d’inflation de 3 %, vaut 1,03 x 1,03 fois son montant de base. »
- `WF-DEV-0030-A` — « Une ligne consommée dans l’année de référence vaut son montant de base. » :
  les deux, des tests sans base du module de calcul ;
- écart : `WF-DEV-0030-A` — « Une ligne de provision portée par une tâche consommée deux ans après
  l’année de référence vaut sa gravité pondérée par sa probabilité, sans autre projection. » : les
  lignes de provision sont d'EP-08, qui clôt ; la règle « une ligne de provision n'est pas
  projetée » est écrite dans le module de calcul, sur une ligne marquée provision, sans risque ;
- `WF-DEV-0040-A` — « Une ligne portée par une tâche à cheval sur deux années est chiffrée en deux
  parts, dont le rapport est celui des heures travaillées dans chacune. »
- `WF-DEV-0040-A` — « Deux lignes d’une même tâche, portées par des rôles aux calendriers
  différents, sont réparties entre les années selon leur propre calendrier. »
- `WF-DEV-0040-A` — « La somme des parts égale le montant total de la ligne avant inflation. » :
  les trois, des tests sans base du module d'étalement, sur les dates de la tâche et les heures des
  calendriers donnés ; `consumption_year` est l'année de la part la plus lourde ;
- `WF-DEV-0010-A` — « Le refus énumère les catégories de coût sans taux horaire pour l’année de
  référence. » : `createNode` et `updateEstimateLine` refusent par 422 `HOURLY_RATE_MISSING`,
  `params.missing_rates` nommant chaque catégorie et son année, une ligne dont la catégorie n'a ni
  taux pour l'année de référence ni taux conservé ; `getMissingRates`, par US-1510 ;
- `WF-DEV-0010-A` — « Le calcul aboutit dès que ces taux sont renseignés. » : la même écriture
  aboutit après `setHourlyRate` ;
- écart : `WF-DEV-0010-A` — « Un devis qui ne porte que des lignes hors main-d’œuvre et une ligne
  de provision se calcule sans aucun taux horaire. » : les lignes hors main-d'œuvre, ici ; la ligne
  de provision est d'EP-08, qui clôt ;
- `WF-PLA-0010-A` — « Une tâche de seize heures en mode automatique, commencée un lundi matin sur
  un calendrier de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre
  heures, elle finit le jeudi. » : constaté par EP-06 (US-1390) ;
- `WF-PLA-0010-A` — « Une tâche dont les deux rôles travaillent huit et six heures le lundi est
  planifiée sur six heures ce jour-là. » : l'intersection d'EP-06 reçoit les calendriers des rôles
  des lignes par `calendar_of(task)`, que la facette ligne alimente ; la tâche est redatée à la
  création de la seconde ligne, `rescheduled` et `reinflated` la rendent ;
- `WF-PLA-0010-A` — « Une tâche sans ligne de main-d’œuvre est planifiée sur le calendrier par
  défaut. » : constaté par EP-06 ; ici, une tâche dont la dernière ligne de main-d'œuvre est
  supprimée y revient ;
- `WF-PLA-0010-A` — « L’ajout, à une tâche dont un rôle travaille du lundi au vendredi, d’une
  ligne d’un rôle qui ne travaille que le week-end est refusé en nommant les deux rôles, et la
  tâche reste inchangée. » : 422 `TASK_WITHOUT_WORKING_HOURS`, `params.resource_roles` et
  `params.tasks`, à la création et au changement de rôle ;
- `WF-PLA-0010-A` — « La répartition mensuelle de la charge d’une ligne suit les heures du
  calendrier de son rôle. » : par US-1520 ;
- `WF-PLA-0010-A` — « L’import d’un fichier de devis dont une ligne donnerait ce résultat rejette
  cette ligne au compte rendu et applique les autres. » : par US-1550 ;
- `WF-PLA-0010-A` — « La modification d’un calendrier qui laisserait une tâche sans heure dans un
  projet que le manager ne peut pas consulter est refusée en nommant ce projet par son libellé et
  son code ; un projet en chiffrage sans code est nommé par son seul libellé. » : la garde d'EP-06
  (`register_idle_task_guard`) juge aussi les calendriers des rôles des lignes, par US-1500 ;
- `WF-DAT-0090-A` — « L’insertion d’une ligne de devis référençant une catégorie inexistante est
  rejetée par la base. » : la clé vers `cost_category`, éprouvée par le propriétaire ;
- `WF-DAT-0090-A` — « L’insertion de deux sous-projets de même code dans un projet est rejetée par
  la base, avant toute règle des services. » : constaté par EP-04 ;
- `WF-DAT-0090-A` — « La suppression d’une tâche de la révision en cours entraîne ses lignes et ses
  liaisons, et rien d’autre. » : la clé composite de `estimate_line` vers `node` en cascade ;
  `deleteNode` d'une tâche rend les totaux diminués de ses lignes ;
- `WF-DAT-0090-A` — « La suppression d’un poste cité par une révision marquée le marque supprimé,
  retire le rattachement de la tâche de la révision en cours et laisse celui de la révision
  marquée. » : constaté par EP-06 ;
- `WF-DAT-0100-A` — « La somme des montants budgétés d’une révision est identique quel que soit
  l’ordre de sommation. » : des `Decimal` à deux décimales, sommés dans deux ordres ;
- `WF-DAT-0100-A` — « Une tâche planifiée au 30 juin s’affiche au 30 juin sur tout poste client,
  quel que soit son fuseau. » : constaté par EP-02 et EP-06 ;
- `WF-DAT-0100-A` — « Un montant de 0,10 additionné dix fois donne exactement 1,00. » : un test
  sans base ;
- `WF-DAT-0100-A` — « Deux tâches de quatre heures liées fin à début, sur un calendrier de huit
  heures, commencent et finissent le même jour. » : constaté par EP-06 ;
- `WF-DAT-0010-A` — « Après marquage d’une révision puis création de la suivante, le nombre de
  lignes de chaque table portant l’identifiant de la nouvelle révision égale celui de la révision
  marquée, hors les lignes des structures différentielles fusionnées et des structures propres des
  risques survenus. » : `estimate_line` et les tables images comprises, par `register_copy` ; les
  structures qu'une révision ne reprend pas sont d'EP-08 ;
- `WF-DAT-0010-A` — « Une modification dans la révision en cours ne change aucune ligne portant
  l’identifiant d’une révision marquée. »
- `WF-DAT-0010-A` — « L’abandon d’une révision en cours ne laisse aucune ligne portant son
  identifiant. » : les lignes et les images, par la cascade et `register_closing` ;
- `WF-DAT-0020-A` — « Une mise à jour ou une suppression exécutée directement en base sur une
  tâche, une ligne de devis ou une valeur de référentiel d’une révision marquée est rejetée par la
  base. » : les déclencheurs d'immuabilité de `estimate_line` et des quatre tables images, sur le
  modèle d'EP-06, propriétaire compris ;
- `WF-DAT-0020-A` — « La désignation d’une révision marquée comme référence aboutit. » : constaté
  par EP-04 ;
- `WF-DAT-0020-A` — « La suppression physique d’un sous-projet référencé par une révision marquée
  est rejetée. » : constaté par EP-04 ; ici, « référencé » devient vrai par une ligne
  (`subproject_is_cited`) ;
- `WF-DAT-0080-A` — « La suppression d’un sous-projet non référencé le retire de la base. » :
  constaté par EP-04 ;
- `WF-DAT-0080-A` — « Celle d’un sous-projet que portent des lignes de devis de la révision en
  cours est refusée et nomme ces lignes ; elle aboutit une fois ces lignes passées hors
  sous-projet ou à un autre sous-projet. » : `subproject_is_estimated` d'EP-04 rempli ; 409
  `STATE_FORBIDS_OPERATION`, `subproject_without_estimate_lines`, `params.estimate_lines` nommant
  les lignes ;
- `WF-DAT-0080-A` — « Celle d’un sous-projet référencé par une révision marquée est refusée, et le
  sous-projet reste proposé à la saisie. » : constaté par EP-04 ; ici, par une ligne d'une
  révision marquée ;
- `WF-DAT-0080-A` — « Celle d’un poste référencé par une révision marquée le marque supprimé : la
  révision l’affiche toujours, la saisie ne le propose plus. » : constaté par EP-06 ;
- `WF-DAT-0080-A` — « Aucune commande ne supprime physiquement un rôle de ressource, un rôle
  d’habilitation ou un compte. » : constaté par EP-03 et EP-05 ;
- `WF-REF-0040-A` — « La création d’une catégorie sans nature est refusée. »
- `WF-REF-0040-A` — « La création d’une catégorie dont le code comptable existe déjà est refusée. »
- `WF-REF-0040-A` — « La création d’une catégorie sans libellé est refusée. » : les trois,
  constatées par EP-05 ;
- `WF-REF-0040-A` — « Le rattachement d’une catégorie employée à une nature d’un autre type est
  refusé, de même que celui d’une catégorie qui porte un taux, ou à laquelle un rôle de ressource
  est rattaché, à une nature hors main-d’œuvre ; le rattachement d’une catégorie inemployée, sans
  taux ni rôle, à une nature d’un autre type est accepté. » : `category_is_employed` d'EP-05
  rempli — une catégorie qu'une ligne d'une révision, en cours ou marquée, porte —, le refus
  d'EP-05 constaté sur une catégorie employée ;
- `WF-IHM-0110-A` — « La suppression d’une tâche puis son annulation restituent la tâche, ses
  lignes et ses liaisons. » : l'instantané de `planning` (`snapshot`) reçoit les lignes de
  `estimate_line` des nœuds touchés par les crochets de la facette, et `undoLastChange` les
  restitue ;
- écart : `WF-IHM-0110-A` — « Le réexamen d’un risque puis son annulation lui rendent sa
  probabilité et son état précédents. » : les risques sont d'EP-08, qui clôt ;
- `WF-IHM-0110-A` — « Cinquante modifications successives s’annulent une par une, puis se
  rétablissent dans l’ordre. » : constaté par EP-06 par l'API ; sur des lignes, par US-1560 ;
- `WF-IHM-0110-A` — « L’annulation d’une modification qu’un autre contributeur a depuis reprise
  est refusée en nommant l’objet en conflit. » : constaté par EP-06 ; ici, l'objet repris est une
  ligne, nommée par son libellé ;
- `WF-IHM-0110-A` — « Aucune commande n’annule un marquage, un import appliqué, une déclaration de
  survenance ou une exclusion de ligne de coût. » : constaté par EP-06 pour le marquage et l'import
  d'un planning ; un import de devis appliqué n'entre pas dans l'historique (US-1550) ; la
  survenance et l'exclusion sont d'EP-08 et d'EP-09, EP-08 clôt ;
- propre à l'US : `createNode` d'une ligne (`kind: estimate_line`, `EstimateLineWrite`) la place
  sous sa tâche porteuse, après ses autres lignes et avant ses sous-tâches, ou après `after_node_id`
  parmi elles ; sous un jalon, elle est permise ; son libellé absent est composé de celui de la
  tâche et de celui du rôle, séparés par un tiret cadratin (« Mise en service — Technicien de mise
  en service »), tronqué à 300 ; sa catégorie absente sans rôle est refusée par `VALUE_REQUIRED` ;
  un délai de paiement négatif par `VALUE_OUT_OF_RANGE` ; une ligne ajoutée après la référence porte
  un budgété nul ; la réponse est `NodesWritten`, la tâche porteuse et ses ancêtres recalculés dans
  `ancestors`, `reinflated` les lignes et tâches dont un montant change d'année ;
- propre à l'US : `updateEstimateLine` écrit le libellé, la catégorie, le rôle, la quantité, la
  charge, le débours, le délai de paiement et le sous-projet, seul ce qui est envoyé, au compteur
  lu (412) ; le retrait du rôle d'une ligne de main-d'œuvre est refusé (`RESOURCE_ROLE_REQUIRED`) ;
  un rôle changé change le calendrier de la tâche, redate ses successeurs (`rescheduled`) et rend
  dans `reinflated` les lignes et tâches dont un montant change d'année ; `remaining_entry` dit la
  ligne réestimable sous une tâche non terminée (`task_not_completed` sinon), `previous_*` nuls
  jusqu'à EP-09, `is_computed` faux ;
- propre à l'US : sur la structure principale, une ligne d'une tâche terminée ne se crée, ne se
  modifie, ne se supprime ni ne se déplace — 409 `STATE_FORBIDS_OPERATION`, `task_not_completed`,
  après `project_not_terminal`, `revision_draft` et `no_background_task_running` —, et ne nomme
  aucun champ dans `editable_fields` (#1767) ; la phase du projet ne refuse rien (C-358) ; une ligne
  d'une tâche démarrée ou terminée ne quitte pas un sous-projet qui a reçu des coûts réels
  (`SUBPROJECT_HAS_ACTUAL_COSTS`) — la règle est écrite, et ne manque jamais avant EP-09, qui
  apporte les coûts réels ;
- propre à l'US : `deleteNode` d'une ligne la supprime physiquement et rend ses ancêtres et les
  totaux ; `moveNodes` déplace une ligne ou une sélection de lignes sous une autre tâche, un jalon
  compris, et refuse `after_node_id` d'un autre genre que la ligne (`NODE_NOT_SIBLING`) ; `listNodes`
  rend la facette ligne entière — libellés de la catégorie, du rôle et du sous-projet résolus,
  `uses_inactive_object`, les trois montants, `consumption_year` —, les totaux (`hours`,
  `base_amount`, `budgeted_amount`, `reestimated_amount`) des lignes retenues, les filtres de la
  ligne (`subproject_id`, `cost_type_id`, `cost_category_id`, `resource_role_id`, les bornes des
  grandeurs et des montants, `uses_inactive_object`, `description`) et le tri des lignes sous
  chaque tâche (`sort_by`, `sort_direction`) ; `resolveRowNumber` rend une ligne par son numéro ;
  `getComputedValueDependencies` nomme, pour le montant d'une tâche, `lines_and_subordinates` et ses
  lignes ;
- propre à l'US : chaque écriture d'une ligne se fait sous le verrou de la structure, dans
  l'encadrement `history.recording` d'EP-06, est refusée sur une révision marquée (`revision_draft`),
  sur un projet terminal, pendant un traitement de fond, par un non-contributeur (403
  `NOT_CONTRIBUTOR`) et sans `estimate.write` (403) ; chaque réponse est validée contre le contrat
  dans les tests du service, et la route de chaque opération déclare ses permissions ;
- propre à l'US (lot technique) : la table `estimate_line` — clé primaire `(project_id, node_id)`,
  `kind` avec `CHECK (kind = 'estimate_line')` et clé composite `(project_id, node_id, kind)` vers
  `node` en cascade, ses grandeurs courantes et de référence, son délai de paiement, son
  sous-projet —, les tables images `revision_role`, `revision_calendar`, `revision_category`,
  `revision_rate`, les colonnes `inflation_rate` et `win_probability` de `revision`, les partitions,
  les déclencheurs d'immuabilité et les droits du rôle du service, en une seule chaîne de
  migrations sur `0024` ; le module `core/estimate` avec son interface en paquet, enregistré dans
  les registres d'EP-04 et d'EP-06 — la facette (`register_facet`), la copie des lignes et des
  images (`register_copy`), « a des lignes » (`register_tasks_and_lines`), le format et l'exporteur
  `estimate` (`register_format`, `register_exporter`), la garde des calendriers des rôles
  (`register_idle_task_guard`), la tranche des lignes (`register_revision_filler`) — ; un routeur
  vide par US enregistré dans `app.py`, la déclaration des opérations et des permissions par
  routeur, les fichiers de tests et de tranche du témoin ; le test des points d'entrée d'EP-06
  (#2180) étendu aux registres qu'EP-07 remplit ; `make check` passe sur ce socle, tiré
  d'`epic/EP-06`.

**Notes de réalisation.** La ligne est la seconde facette de la table `node` d'EP-06 (décision de
l'auteur du 2026-11-07, au cadrage d'EP-06) : l'ordre, la lignée, `row_number` et `position` sont
ceux de `node`, et `core/planning` tient les règles de placement d'une ligne, que ce module appelle
sans les réécrire. Les trois montants sont calculés, jamais saisis : la conception dit s'ils sont
conservés ou calculés à la lecture, et comment le montant budgété se tire de la révision de
référence par la lignée. Le socle de l'EPIC est le premier lot de cette US, et le lot pivot
d'EP-09 : il pose `estimate_line` avec ses grandeurs courantes et de référence, et l'interface
qu'EP-09 étendra (`setLineRemaining`, le reste d'une ligne, les tâches démarrées).

**Hors périmètre.** Les lignes de provision (EP-08) ; la réestimation et `previous_*` (EP-09) ;
le collage et l'annulation depuis la grille (US-1560) ; les indicateurs (US-1510) ; l'instantané et
la mise à jour des taux (US-1500).

---

## US-1500 — L'instantané du référentiel conservé par la révision, et la mise à jour des taux

- **statut** : en cours
- **exigences** : `WF-REV-0030-A`, `WF-REV-0060-A`, `WF-REV-0010-A`, `WF-REV-0020-A`,
  `WF-REV-0070-A`, `WF-REF-0020-A`, `WF-REF-0130-A`, `WF-REF-0030-A`, `WF-REF-0010-A`,
  `WF-PRJ-0040-A`
- **opérations** : `getRateUpdateProposal`, `applyRateUpdate`, `getRevision`, `listRevisions`,
  `createRevision`, `markRevision`, `updateProject` ; `setHourlyRate`, `updateCostCategory`,
  `setCostCategoryActivation`, `setCostTypeActivation`, `updateCostType`, `updateResourceRole`,
  `setResourceRoleActivation`, `updateCalendar`, `setDefaultCalendar` pour leurs effets
- **issue** : 2362

**En tant que** chef de projet, **je veux** qu'une révision marquée garde les rôles, les
calendriers, les catégories et les taux qu'elle employait, ainsi que le taux d'inflation et la
probabilité de gain de son marquage, que la révision en cours chiffre ses lignes aux taux de son
année de référence ou aux taux conservés projetés, et qu'on me propose, catégorie par catégorie,
de passer aux taux de la nouvelle année, **afin que** rien de ce que le référentiel change ensuite
ne réécrive une offre remise.

**Critères d'acceptation.**

- `WF-REV-0030-A` — « Après désactivation d’un rôle et correction de son taux horaire, une révision
  marquée qui les employait affiche toujours le rôle et les montants d’origine. » : les images
  `revision_role` et `revision_rate` écrites au marquage, lues par `getRevision` (`snapshot`) et par
  `listNodes` de la révision marquée ;
- `WF-REV-0030-A` — « La modification du taux d’inflation ou de la probabilité de gain du projet
  laisse inchangées les valeurs conservées par une révision marquée. » : `revision.inflation_rate`
  et `win_probability` écrits au marquage, lus par `getRevision` et `listRevisions`, nuls jusque-là
  et lus comme ceux du projet ;
- `WF-REV-0060-A` — « Une révision créée en 2027 porte l’année de référence 2027. » : l'horloge
  du service posée en 2027 par les tests ;
- `WF-REV-0060-A` — « À sa création, lorsque la précédente portait 2026, l’écart est présenté
  catégorie par catégorie et la mise à jour peut être refusée. » : `getRateUpdateProposal` rend,
  pour chaque catégorie de main-d'œuvre employée, le taux conservé projeté et le taux du
  référentiel de l'année (`reference_rate`), ou le taux projeté seul sans taux de l'année
  (`inflated_previous`) ; `createRevision` avec `apply_rate_update` faux les laisse projetés ;
- `WF-REV-0060-A` — « Une catégorie refusée ou sans taux pour 2027 est chiffrée au taux de 2026
  corrigé d’une année d’inflation. » : `revision_rate` porte le taux projeté, et les montants des
  lignes le suivent ;
- écart : `WF-REV-0060-A` — « Une révision créée en 2027 par un import de reste à engager porte
  les taux de 2026 projetés d’une année ; la mise à jour catégorie par catégorie reste proposée
  jusqu’à son marquage, et l’accepter pour une catégorie la rechiffre au taux de 2027. » :
  l'import de reste à engager est d'EP-09, qui clôt ; ici, une révision créée par un import de
  devis (US-1550) porte les taux projetés et la proposition reste offerte ;
- `WF-REV-0060-A` — « Une mise à jour refusée à la création d’une révision est acceptée ensuite
  depuis la révision en cours, qui est alors rechiffrée au taux de 2027 pour cette catégorie. » :
  `applyRateUpdate` écrit le taux de l'année sur les catégories retenues, au compteur lu de la
  révision (412), une liste vide ou une catégorie que la proposition ne présente pas refusées par
  422 (#1756), une révision marquée par 409 `revision_draft`, aucune catégorie proposée par
  `rate_update_available` ; la révision avance d'une version et ses montants suivent ;
- `WF-REV-0010-A` — « La création d’une seconde révision en cours est refusée tant que la première
  n’est pas marquée. » : constaté par EP-04 ;
- `WF-REV-0010-A` — « Une révision créée à partir d’une révision marquée porte les mêmes tâches et
  les mêmes lignes, hors celles des structures qu’elle ne reprend pas (WF-REV-0100) ; à année de
  référence égale, elle porte aussi les mêmes valeurs de référentiel ; sinon, elle porte les mêmes
  rôles, calendriers et catégories, et, pour chaque catégorie dont la mise à jour de WF-REV-0060
  n’a pas été acceptée, le taux précédent projeté par le taux d’inflation du projet jusqu’à la
  nouvelle année de référence. » : la copie des lignes (US-1490) et des taux par `register_copy`,
  les taux projetés quand l'année change ; les structures qu'une révision ne reprend pas sont
  d'EP-08 ;
- `WF-REV-0010-A` — « Après abandon d’une révision en cours, le projet présente les données de la
  dernière révision marquée, et une nouvelle révision peut être créée. »
- `WF-REV-0010-A` — « L’abandon de l’unique révision d’un projet en chiffrage le laisse sans
  révision, à l’état Chiffrage, et la création d’une révision y est de nouveau proposée. » : les
  deux, constatées par EP-04 ; ici, les lignes de la révision abandonnée disparaissent avec elle ;
- `WF-REV-0020-A` — « Le marquage est refusé tant que le nom de version n’est pas renseigné. » :
  constaté par EP-04 ;
- `WF-REV-0020-A` — « Toute tentative de modification d’une révision marquée est refusée, quel que
  soit le point d’entrée. » : une ligne (US-1490), la mise à jour des taux, l'import d'un devis
  (US-1550), par 409 `revision_draft` ;
- `WF-REV-0020-A` — « Le marquage d'une révision sous un nom de version déjà employé dans le projet
  est refusé. » : constaté par EP-04 ;
- `WF-REV-0070-A` — « La liste des révisions marquées est accessible depuis le projet, et
  l’ouverture de l’une d’elles affiche son planning, son devis et ses montants tels qu’ils étaient
  au marquage. » : `listNodes` d'une révision marquée chiffre ses lignes sur ses images et son
  taux d'inflation conservé, identiques après toute modification du référentiel et du projet ;
- `WF-REV-0070-A` — « L’année de référence, le taux d’inflation et la probabilité de gain affichés
  pour une révision marquée sont ceux conservés à son marquage, même après modification de ceux du
  projet. » : `listRevisions` et `getRevision` ;
- `WF-REF-0020-A` — « On désactive un rôle de ressource et une catégorie de coût employés par une
  révision en cours. »
- `WF-REF-0020-A` — « La révision reste calculable et peut être marquée sans que ses lignes soient
  modifiées. » : `listNodes` rend les lignes, `uses_inactive_object` vrai, les montants inchangés ;
  `markRevision` aboutit ;
- `WF-REF-0130-A` — « Après correction d’un taux horaire et changement de la catégorie d’un rôle,
  les montants d’une révision marquée qui les employait sont identiques à ceux relevés avant la
  modification. »
- écart : `WF-REF-0130-A` — « Après abaissement du seuil d’alerte, la zone de l’indice de coût
  d’une révision marquée peut changer, sa valeur non. » : l'indice de coût est d'EP-10, qui clôt ;
- `WF-REF-0030-A` — « Une nature de chacun des trois types peut être créée. »
- `WF-REF-0030-A` — « La création d’une nature dont le code existe déjà est refusée. » : les deux,
  constatées par EP-05 ;
- `WF-REF-0030-A` — « La modification du type est refusée pour une nature dont une catégorie est
  employée, porte un taux ou est rattachée à un rôle de ressource. » : « employée » devient vrai
  par une ligne (`category_is_employed`, US-1490) ; le refus d'EP-05 constaté ;
- `WF-REF-0030-A` — « Sur une installation neuve, la nature de type provision pour risques et sa
  catégorie existent. » : constaté par EP-05 ;
- écart : `WF-REF-0030-A` — « Une fois saisis la catégorie de main-d’œuvre et le rôle de ressource
  qu’exige WF-CYC-0120, un projet se crée, et la déclaration d’un risque y aboutit sans qu’aucune
  catégorie de provision ait été saisie. » : la création, constatée par EP-04 ; la déclaration d'un
  risque est d'EP-08, qui clôt ;
- écart : `WF-REF-0030-A` — « La désactivation de la dernière catégorie active de type provision
  pour risques est acceptée ; la création d’un projet (WF-CYC-0120), la déclaration d’un risque et
  le retour d’un risque écarté à l’état identifié (WF-RIS-0010) sont alors refusés. » : la
  désactivation et la création, constatées par EP-05 et EP-04 ; les risques sont d'EP-08, qui clôt ;
- `WF-REF-0010-A` — « Aucun écran ne propose de supprimer un objet du référentiel. »
- `WF-REF-0010-A` — « Un objet désactivé n’apparaît plus dans les listes de choix, mais reste
  affiché sur les éléments qui l’emploient. »
- `WF-REF-0010-A` — « Une fois réactivé, il est de nouveau proposé. » : les trois, constatées par
  EP-05 ; ici, les libellés d'un rôle ou d'une catégorie désactivés sont résolus sur la ligne qui
  les emploie ;
- écart : `WF-REF-0010-A` — « Après désactivation d’un rôle de ressource, les lignes qui le portent
  sont signalées dans la grille de devis et dans celle du reste à engager, et restent lisibles. » :
  `uses_inactive_object` servi ici et lu par la grille de devis (US-1560) ; la grille de reste à
  engager est branchée par EP-09, qui clôt ;
- `WF-REF-0010-A` — « La désactivation d’une nature désactive ses catégories. »
- `WF-REF-0010-A` — « La réactivation d’une catégorie dont la nature est désactivée est refusée. » :
  les deux, constatées par EP-05 ;
- `WF-PRJ-0040-A` — « La modification du taux d’inflation laisse inchangés les montants des
  révisions marquées. » : `updateProject` écrit le taux, les révisions marquées gardent le leur ;
- écart : `WF-PRJ-0040-A` — « Dans la révision en cours, les lignes de main-d’œuvre et hors
  main-d’œuvre dont l’année de consommation suit l’année de référence sont rechiffrées, les autres
  non ; une ligne de provision ne change que par son devis propre. » : les lignes de main-d'œuvre
  et hors main-d'œuvre, ici ; la ligne de provision est d'EP-08, qui clôt ;
- propre à l'US : au marquage, le crochet que `core/estimate` enregistre dans `core/revisions`
  écrit les images des rôles, des calendriers, des catégories et des taux que les lignes de la
  révision emploient, et le taux d'inflation et la probabilité de gain du projet, dans la
  transaction de la tâche ; à la création d'une révision, `register_copy` écrit les taux conservés —
  copiés à année égale, projetés sinon, remplacés par ceux du référentiel pour les catégories que
  `apply_rate_update` retient — ; une catégorie sans taux conservé lit celui du référentiel pour
  l'année de référence ; `getRevision` rend `snapshot` pour une révision marquée seule ;
- propre à l'US : la garde d'EP-06 `register_idle_task_guard` juge aussi les calendriers des rôles
  des lignes : `updateCalendar` et `updateResourceRole` refusent par `TASK_WITHOUT_WORKING_HOURS`
  la modification qui laisserait une tâche d'une révision en cours sans heure, `params.projects`
  nommant chaque projet par son libellé et son code, nul sans code ;
- propre à l'US : la commande `apply_rate_update` de la révision est listée sous `revisions.write`,
  disponible quand la proposition présente une catégorie, `rate_update_available` sinon ; la mise à
  jour des taux de l'écran des révisions (`rate-update-command.tsx`) travaille contre le service, et
  le parcours `revisions.spec.ts` perd `BEFORE_EP07` pour la proposition des taux, par US-1530 qui
  lève le reste ; chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Les images sont celles de la décision de l'auteur du 2026-10-28 (EP-04,
« Ce qui n'en fait pas partie ») : `revision_role`, `revision_calendar`, `revision_category`,
`revision_rate`, du régime révisionné, partitionnées par projet. La révision en cours suit le
référentiel pour ses rôles, calendriers et catégories, et ne conserve que ses taux (`RevisionSnapshot`
du contrat) ; la conception dit ce que chaque image porte et quand elle s'écrit. `source` de
`RateUpdateProposal` vaut `reference_rate` quand le référentiel porte un taux pour l'année,
`inflated_previous` sinon.

**Hors périmètre.** La fusion d'un différentiel sur un projet sans révision en cours (EP-08) ;
l'import de reste à engager (EP-09) ; l'indice de coût (EP-10).

---

## US-1510 — Les indicateurs de devis et les taux manquants

- **statut** : fini
- **exigences** : `WF-DEV-0060-A`, `WF-DEV-0010-A`
- **opérations** : `getEstimateIndicators`, `getMissingRates`
- **issue** : 2363

**En tant que** chef de projet, **je veux** lire le total de mon devis, ses ventilations par
nature de coût, par sous-projet et par lot du lotissement, ses écarts avec la référence et la
révision marquée précédente, et les catégories dont il manque le taux horaire, **afin d'**arbitrer
mon chiffrage sans le lire ligne à ligne.

**Critères d'acceptation.**

- `WF-DEV-0060-A` — « La somme des totaux par nature égale le total général, et la somme de leurs
  pourcentages vaut cent. » : `by_cost_type`, les parts à quatre décimales, la plus grande portant
  le reste des arrondis (README, « Une part… ») ;
- `WF-DEV-0060-A` — « Sur un planning importé dont aucune tâche n’est rattachée à un lot, les
  totaux par lot sont absents plutôt que nuls ; après rattachement d’une récapitulative au lot 1,
  son total apparaît, et il vaut celui de son sous-arbre ; après rattachement d’une feuille à un
  lot, le total de ce lot est le montant des lignes de cette feuille. » : `by_work_package`, un lot
  par ligne du lotissement, `work_package_without_task` sans tâche rattachée, le total du
  sous-arbre de la tâche rattachée sinon, sur un planning importé par EP-06 ;
- `WF-DEV-0010-A` — « Le refus énumère les catégories de coût sans taux horaire pour l’année de
  référence. » : `getMissingRates` nomme chaque catégorie employée sans taux pour l'année de
  référence de la révision, et les montants de `getEstimateIndicators` qui en dépendent ne se
  calculent pas (`hourly_rate_missing`, `params.missing_rates`) ; la saisie, par US-1490 ;
- `WF-DEV-0010-A` — « Le calcul aboutit dès que ces taux sont renseignés. » : après
  `setHourlyRate`, la liste est vide et les montants se calculent ;
- écart : `WF-DEV-0010-A` — « Un devis qui ne porte que des lignes hors main-d’œuvre et une ligne
  de provision se calcule sans aucun taux horaire. » : les lignes hors main-d'œuvre, ici ; la ligne
  de provision est d'EP-08, qui clôt ;
- propre à l'US : `getEstimateIndicators` lit la révision nommée ou la révision en cours, ou la
  dernière marquée sans elle, pour le projet, un sous-projet ou « hors sous-projet » (`scope`,
  `UNKNOWN_SUBPROJECT`) ; `total` vaut le réestimé des totaux de la structure principale,
  `by_subproject` et `by_cost_type` somment à `total`, `provisions_identified` est nul avant EP-08,
  `delta_to_reference` est le devis lu moins celui de la référence, nul sans référence,
  `delta_to_previous_revision` le devis lu moins celui de la révision marquée précédente, nul sans
  elle ; `context` dit la révision, `computed_at` et `is_stored` faux ; sous `estimate.read` ; chaque
  réponse est validée contre le contrat dans les tests du service ;
- propre à l'US : l'encart des indicateurs de l'écran du devis (`EstimateSummary`) lit le service ;
  son parcours est étiqueté `@shared` par US-1560, qui branche l'écran.

**Notes de réalisation.** Les indicateurs d'une révision marquée se calculent ici à la lecture, sur
ses images ; leur conservation au marquage (WF-DAT-0040, `is_stored`) est d'EP-10. Le même module
de totaux sert `NodeTotals` de `listNodes` (US-1490) et les ventilations.

**Hors périmètre.** Les indicateurs de projet et leur conservation (EP-10) ; la provision (EP-08).

---

## US-1520 — Le plan de charge sur le devis, et la valeur planifiée

- **statut** : fini
- **exigences** : `WF-DEV-0070-A`, `WF-DEV-0080-A`
- **opérations** : `getProjectWorkload` ; `listRevisions`, `listOrgNodes` que l'écran lit
- **issue** : 2364

**En tant que** chef de projet, **je veux** lire, par rôle et par mois, la charge que mon devis
représente — sur la révision de référence, sur une révision marquée ou sur la révision en cours —,
la capacité de chaque rôle en regard, filtrée par nœud d'organisation, **afin de** voir ce que le
projet demande à chaque métier et quand ; et, pour les indicateurs à venir, que la valeur planifiée
s'étale sur la référence au prorata des heures travaillées.

**Critères d'acceptation.**

- `WF-DEV-0070-A` — « La charge d’une ligne portée par une tâche qui couvre exactement deux mois
  civils apparaît sur ces deux mois, au prorata des heures travaillées de la tâche dans chacun. » :
  un test sans base du module d'étalement, et le même sur le service ;
- `WF-DEV-0070-A` — « La capacité de chaque rôle est affichée. » : `roles[].capacity_monthly_hours`
  du référentiel, pour chaque rôle employé ou retenu par le filtre ;
- `WF-DEV-0070-A` — « Le filtre par nœud d’organisation ne laisse voir que les rôles qui en
  relèvent. » : `org_node_id`, les rôles rattachés au nœud ou à l'un de ses descendants,
  `org_node_label` résolu, `UNKNOWN_ORG_NODE` sinon ;
- `WF-DEV-0070-A` — « Le plan de charge calculé sur le reste à engager ignore les lignes des tâches
  terminées. » : sur `current_remaining` et `marked_remaining`, les lignes d'une tâche terminée par
  `setTaskProgress` (EP-06) n'y comptent rien ;
- `WF-DEV-0070-A` — « Les trois bases sont proposées ; sur un projet sans révision de référence, la
  base de la référence est absente, et sur un projet sans aucune révision marquée, seule la
  révision en cours est proposée. » : `reference_budget` refusée par 409 sans référence,
  `marked_remaining` par 422 sans révision marquée nommée, `current_remaining` par 409 sans
  révision en cours ; l'écran n'offre que les bases que le projet admet ;
- écart : `WF-DEV-0070-A` — « Une tâche démarrée qui couvre exactement quatre mois civils, à
  mi-parcours à la date de calcul — le premier jour du troisième mois —, dont une ligne porte un
  reste de 80 heures, présente ces 80 heures sur les deux mois restants au prorata de leurs heures
  travaillées — 40 et 40 s’ils en comptent autant — et rien sur les mois écoulés ; sur une révision
  marquée, la date de calcul est sa date de marquage. » : la charge restante étalée sur la part de
  la tâche postérieure à la date de calcul, et la date de marquage comme date de calcul, ici, sur
  la charge courante de la ligne ; le reste de 80 heures est une réestimation, d'EP-09, qui clôt ;
- `WF-DEV-0070-A` — « Une tâche non démarrée dont la date de début est antérieure à la date de
  calcul ne présente aucune charge sur les mois écoulés ; sa charge est la même avant et après son
  démarrage. » : la charge portée aux mois restants, et au mois de la date de calcul quand la fin
  est dépassée ;
- `WF-DEV-0080-A` — « Sur un projet dont le budget de référence est de 1 000, la valeur planifiée
  vaut 1 000 à la date de fin de la dernière tâche de la référence, et 0 avant le début de la
  première. »
- `WF-DEV-0080-A` — « Une ligne portée par une tâche de deux mois comptant autant d’heures
  travaillées contribue pour moitié à la fin du premier mois. »
- `WF-DEV-0080-A` — « Retarder une tâche dans la révision courante ne change pas la valeur
  planifiée. » : les trois, des tests du noyau — `planned_value(reference, at)` de l'interface de
  `core/estimate`, calculée sur les lignes de la révision de référence hors provision, à leur
  montant budgété, étalé sur les dates de la tâche telle que la référence la date, une ligne d'un
  jalon comptée entière à sa date — ; aucune opération du contrat ne la sert avant EP-10 (décision
  de l'auteur du 2026-11-07) ;
- écart : `WF-DEV-0080-A` — « Après contractualisation d’un avenant, la valeur planifiée totalise
  le nouveau budget de référence. » : l'avenant est d'EP-08, qui clôt ;
- propre à l'US : `getProjectWorkload` rend `monthly_totals` du premier au dernier mois chargé, sans
  trou, `zone` d'un mois en alerte au-delà de la capacité, `context.computed_at` au jour courant ou
  à la date de marquage ; sous `estimate.read` ; l'écran du plan de charge (`…/workload`) travaille
  contre le service, `MockupNotice` en est retiré, et `workload.spec.ts` porte `@shared` ; chaque
  réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** L'étalement d'une charge ou d'un montant sur les mois ou les années, au
prorata des heures travaillées d'un calendrier entre deux instants, est un module pur de
`core/estimate`, le même pour l'année de consommation (US-1490), le plan de charge et la valeur
planifiée ; la conception le nomme. L'écran est celui d'EP-02 (US-0240) et d'EP-15 (US-0550).

**Hors périmètre.** La réestimation et le reste à engager (EP-09) ; les courbes de valeur acquise
et de valeur planifiée (EP-10) ; le plan de charge agrégé du portefeuille (EP-11).

---

## US-1530 — La comparaison de deux révisions

- **statut** : en cours
- **exigences** : `WF-REV-0080-A`
- **opérations** : `compareRevisions`
- **issue** : 2365

**En tant que** chef de projet, **je veux** comparer deux révisions marquées de mon projet dans la
grille, chaque tâche et chaque ligne marquée ajoutée, retirée, modifiée ou inchangée, avec les
écarts de montants budgétés et réestimés par nature et par sous-projet, **afin de** lire ce qui a
changé d'une offre à la suivante.

**Critères d'acceptation.**

- écart : `WF-REV-0080-A` — « La comparaison d’une révision obtenue par fusion d’un différentiel
  avec la révision marquée qui la précède, de même année de référence, lorsqu’aucune autre
  modification n’a été faite entre les deux, restitue exactement les tâches et les montants
  budgétés de ce différentiel. » : la fusion est d'EP-08, qui clôt ; ici, deux révisions marquées
  dont la seconde ajoute, retire, déplace et modifie des tâches et des lignes se comparent par la
  lignée, et `budgeted_delta` restitue ce qui change ;
- écart : `WF-REV-0080-A` — « Les montants réestimés n’y diffèrent que par les lignes que le
  différentiel ajoute ou retire, par celles des tâches démarrées qu’il termine et par celles dont
  il change l’année de consommation ; une ligne existante dont le différentiel ne modifie que le
  montant budgété ne présente aucun écart de montant réestimé. » : EP-08, qui clôt ; ici,
  `reestimated_delta` ne vient que des lignes dont le réestimé change ;
- écart : `WF-REV-0080-A` — « Entre deux révisions d’années de référence différentes, les montants
  réestimés diffèrent en outre sur chaque ligne dont le taux a été mis à jour ou projeté jusqu’à la
  nouvelle année de référence (WF-REV-0060) ; les tâches et les montants budgétés restent ceux du
  différentiel. » : les taux mis à jour ou projetés, ici, sur deux révisions marquées d'années
  différentes sans différentiel ; le différentiel est d'EP-08, qui clôt ;
- `WF-REV-0080-A` — « Une tâche déplacée sous une autre récapitulative est présentée modifiée. » :
  `difference` à `modified`, `parent` dans `changes`, l'ancienne et la nouvelle récapitulative
  modifiées par leur contenu ;
- propre à l'US : `compareRevisions` rend l'arbre de la révision comparée dans l'ordre du plan, les
  nœuds retirés à leur place en lecture seule, chaque nœud avec `difference` et `changes` — une
  tâche par ses dates, sa durée, son état ou son parent, une ligne par ses montants, son délai de
  paiement, son sous-projet, sa catégorie ou son parent (#1752) —, les mêmes paramètres que
  `listNodes` (`kinds`, `search`, `subtree_of`, les filtres de colonne, `difference`, `fields`,
  le tri), `totals` de la révision comparée, `meta`, et `amount_deltas` par nature et par
  sous-projet, chaque ligne comptant sous la clé qu'elle porte dans chaque révision, les clés aux
  deux écarts nuls omises, la somme par sous-projet égale à la somme par nature (#1752) ; une paire
  identique rend chaque nœud inchangé ; une révision en cours ou d'un autre projet refusée par 422
  et 404 ;
- propre à l'US : la comparaison de l'écran des révisions travaille contre le service,
  `revisions.spec.ts` perd `BEFORE_EP07` et ses parcours de la comparaison portent `@shared`, la
  volumétrie des 5 999 nœuds du témoin tenue sous la borne d'un écran de grille ; chaque réponse est
  validée contre le contrat dans les tests du service.

**Notes de réalisation.** La comparaison lit deux révisions marquées sur leurs images et leurs taux
conservés (US-1500) : rien n'est recalculé sur le référentiel du jour. L'écran est celui d'EP-15
(US-0500) ; le témoin compare l'offre 100 à la révision 101.

**Hors périmètre.** La fusion d'un différentiel et la marque d'un différentiel lue par `listNodes`
(EP-08).

---

## US-1540 — Le passage à En cours, le code projet et la proposition des contributeurs

- **statut** : à faire
- **exigences** : `WF-CYC-0020-A`, `WF-CYC-0030-A`, `WF-CYC-0050-A`, `WF-PRJ-0010-A`,
  `WF-PRJ-0060-A`, `WF-PRJ-0070-A`
- **opérations** : `listContributorSuggestions`, `designateReferenceRevision`,
  `getProjectNextState`, `updateProject`, `getProject`, `setContributors`
- **issue** : 2366

**En tant que** chef de projet, **je veux** que mon projet passe En cours de lui-même dès que sa
référence porte des tâches et des lignes et que son code est saisi, et qu'on me propose comme
contributeurs les utilisateurs des services dont mon devis emploie les rôles, **afin de** démarrer
l'exécution avec l'équipe que le chiffrage appelle.

**Critères d'acceptation.**

- `WF-CYC-0020-A` — « Aucun écran ne propose de commande menant à Chiffrage ou En cours. » :
  constaté par EP-04 et EP-15 ;
- `WF-CYC-0020-A` — « Chacun de ces états est atteint dès que son fait déclencheur est réalisé, sans
  autre action. » : la désignation d'une référence qui porte des tâches et des lignes, le code
  saisi, mène En cours par `advance` d'EP-04 ;
- `WF-CYC-0030-A` — « La désignation d’une révision marquée sans tâche, ou sans ligne de devis, est
  refusée et la condition manquante est nommée ; le projet n’a pas de référence. » :
  `revision_has_tasks_and_lines` d'EP-04 reçoit la question des lignes
  (`register_tasks_and_lines`) ; une révision marquée avec des tâches sans ligne est refusée par
  409 `revision_has_tasks_and_lines` ;
- `WF-CYC-0030-A` — « Un projet dont la référence est désignée avant le code projet passe à En
  cours à la saisie du code ; un projet dont le code est saisi avant la désignation y passe à la
  désignation. » : les deux ordres, contre le service, avec une référence qui porte des lignes ;
- `WF-CYC-0050-A` — « Pour un projet dans chacun des états Créé et Chiffrage, l’utilisateur
  consulte le prochain état, son déclencheur et les conditions restantes, sans avoir tenté
  d’action. » : `getProjectNextState` d'EP-04 nomme `revision_has_tasks_and_lines` parmi les
  conditions restantes tant qu'aucune révision marquée ne porte de ligne ;
- `WF-PRJ-0010-A` — « Un projet se crée et se chiffre sans code projet. » : des lignes se créent
  sur un projet sans code ;
- `WF-PRJ-0010-A` — « Le projet ne passe pas à En cours tant qu’il n’est pas renseigné, et la
  condition manquante est nommée (WF-CYC-0050). » : la référence désignée sans code, le projet reste
  en Chiffrage et `getProjectNextState` nomme le code ;
- `WF-PRJ-0010-A` — « La saisie d’un code déjà porté par un autre projet est refusée. » : constaté
  par EP-04 ;
- `WF-PRJ-0060-A` — « La liste d’un projet nouvellement créé comporte son créateur, chef de projet,
  qui peut y inscrire d’autres utilisateurs. »
- `WF-PRJ-0060-A` — « Un utilisateur habilité à consulter les projets, non contributeur d’un projet
  et sans la permission « consulter tous les projets », ne l’ouvre pas et ne le trouve pas par son
  adresse ; le carnet du portefeuille le compte pourtant. » : les deux, constatées par EP-04 ; le
  carnet est d'EP-11 ;
- `WF-PRJ-0060-A` — « Inscrit comme participant, il l’ouvre et saisit le devis, mais ne marque pas
  de révision même s’il en porte la permission ; inscrit comme chef de projet, il la marque. » : un
  participant crée une ligne, 403 `NOT_PROJECT_MANAGER` au marquage ; chef de projet, il marque ;
- `WF-PRJ-0060-A` — « Le retrait du seul chef de projet d’un projet est refusé, de même que son
  passage en participant ; il est accepté dès qu’un second chef de projet est inscrit. » : constaté
  par EP-04 ;
- `WF-PRJ-0070-A` — « Après création d’une ligne de main-d’œuvre portant un rôle relevant d’un
  service dont aucun utilisateur n’est contributeur, Waterfall propose les utilisateurs de ce
  service. » : `listContributorSuggestions` rend les comptes actifs rattachés aux nœuds
  d'organisation des rôles employés par les lignes de la révision en cours, ou de la dernière
  marquée sans elle, que la liste ne compte pas, chacun avec son nœud et ses rôles ;
- `WF-PRJ-0070-A` — « Tant que la proposition n’est pas confirmée, la liste est inchangée. » :
  `listContributors` ne change pas ; `setContributors` l'écrit ;
- propre à l'US : les paramètres du projet proposent les contributeurs que le service rend, et le
  parcours jumeau des contributeurs (`own-project.ts`) crée une ligne d'un rôle d'un service, lit la
  proposition et la confirme ; le parcours du cycle (`revision-cycle.spec.ts`) désigne une
  référence qui porte une tâche et une ligne et constate le passage En cours ; `load-witness`
  rejoue la désignation de l'offre 100 de PRJ-001, acceptée, par US-1570 ; chaque réponse est
  validée contre le contrat dans les tests du service.

**Notes de réalisation.** EP-04 a servi `listContributorSuggestions` vide et déclaré
`revision_has_tasks_and_lines` ; cette US les remplit par l'interface de `core/estimate`, sans que
`core/projects` ni `core/revisions` l'importent. Le passage En cours est le fait d'EP-04 ; rien
n'y change.

**Hors périmètre.** La correction de la référence et l'avenant (EP-08) ; le carnet du portefeuille
(EP-11).

---

## US-1550 — Le format Excel du devis : export, import et aller-retour

- **statut** : en cours
- **exigences** : `WF-INTF-0070-A`, `WF-INTF-0100-A`, `WF-INTF-0110-A`, `WF-INTF-0180-A`,
  `WF-INTF-0080-A`, `WF-INTF-0090-A`, `WF-INTF-0040-A`, `WF-INTF-0050-A`, `WF-INTF-0060-A`,
  `WF-DAT-0110-A`, `WF-EXP-0020-A`, `WF-PRJ-0080-A`, `WF-REF-0140-A`
- **opérations** : `requestExport` (`estimate`), `getBackgroundTaskResult` ; `uploadFile`,
  `openImport`, `getImport`, `abandonImport`, `applyImport` pour `estimate`
- **issue** : 2367

**En tant que** chef de projet, **je veux** exporter le devis d'une révision au format Excel
« Devis » de l'annexe B, le travailler dans Excel et le réimporter dans ma révision en cours sans
perdre une ligne ni une lignée, **afin de** chiffrer avec l'outil que mes interlocuteurs
connaissent et de revenir sans écart.

**Critères d'acceptation.**

- écart : `WF-INTF-0070-A` — « Un fichier conforme à chacun des formats de ANNEXE B: Formats
  d’échanges Excel est accepté. » : le format « Devis », ici ; « Reste à engager » et « Coûts
  réels » sont d'EP-09, qui clôt ;
- écart : `WF-INTF-0070-A` — « Un fichier de devis ou de reste à engager sans version, ou d’une
  version non reconnue, est refusé avec un message qui nomme le format et la version attendus ; un
  fichier de coûts réels auquel manque une colonne exigée par la correspondance est refusé avec un
  message qui la nomme. » : `openImport` refuse un devis sans version ou d'une version inconnue par
  422 `FILE_FORMAT_UNREADABLE`, `expected_format` et `expected_version` ; le reste à engager et les
  coûts réels sont d'EP-09, qui clôt ;
- `WF-INTF-0070-A` — « Le projet est inchangé. »
- `WF-INTF-0100-A` — « On importe un fichier qui comporte des lignes de main-d’œuvre et des lignes
  hors main-d’œuvre. »
- `WF-INTF-0100-A` — « Chaque ligne se retrouve sous la tâche désignée, avec sa quantité, ses
  heures ou son débours, son rôle et, le cas échéant, son sous-projet. »
- `WF-INTF-0100-A` — « Un second import du même fichier donne un devis identique. »
- `WF-INTF-0100-A` — « Un fichier exporté, dont une charge a été modifiée, réimporté sur un projet
  qui porte une révision de référence sans être encore En cours met à jour cette ligne sans changer
  son montant budgété ni sa lignée. » : la référence désignée, le code non saisi ;
- `WF-INTF-0100-A` — « Une ligne qui cite une tâche, un rôle ou un sous-projet inconnu, ou qui
  laisserait une tâche sans aucune heure travaillée dans la semaine (WF-PLA-0010), est rejetée et
  figure au compte rendu (WF-INTF-0080). » : `rejected` par `UNKNOWN_TASK`,
  `UNKNOWN_RESOURCE_ROLE`, `UNKNOWN_SUBPROJECT` avec `params.value`, `TASK_WITHOUT_WORKING_HOURS`
  avec les rôles et la tâche, `AMBIGUOUS_TASK_LABEL` pour un libellé que plusieurs tâches portent ;
  les autres lignes s'appliquent ;
- écart : `WF-INTF-0100-A` — « Une ligne d’une tâche démarrée dont le sous-projet a reçu des coûts
  réels, que le fichier place sous un autre sous-projet ou laisse sans sous-projet, est rejetée, et
  le compte rendu nomme ce sous-projet. » : la règle est écrite (`SUBPROJECT_HAS_ACTUAL_COSTS`) et
  ne rejette jamais avant les coûts réels d'EP-09 ; EP-08 clôt ;
- `WF-INTF-0100-A` — « Un devis exporté d’une révision marquée puis réimporté dans la révision en
  cours met à jour les lignes de même lignée sans en créer aucune. »
- écart : `WF-INTF-0100-A` — « Un fichier d’où une ligne de provision a été retirée laisse cette
  ligne en place ; une ligne de catégorie de provision sans identifiant est rejetée au compte
  rendu. » : le rejet par `PROVISION_CATEGORY_RESERVED`, ici ; la ligne de provision conservée
  (`kept`, `provision_lines`) est d'EP-08, qui clôt ;
- écart : `WF-INTF-0100-A` — « Sur un projet En cours, l’import d’un devis sur la structure
  principale est refusé et nomme la condition ; sur une structure différentielle, il aboutit. » :
  le refus, ici — `ProjectCommand.import_estimate` indisponible dès En cours,
  `project_before_in_progress`, et `openImport` refusé par 409 — ; la structure différentielle est
  d'EP-08, qui clôt ;
- `WF-INTF-0110-A` — « On exporte un devis, puis on le réimporte sans modification dans la révision
  en cours. »
- `WF-INTF-0110-A` — « Le compte rendu (WF-INTF-0080) ne signale aucun écart, et les lignes
  obtenues sont identiques. » : `differences` et `rejected` vides, `unchanged_count` égal à
  `read_count`, les lignes relues identiques ;
- `WF-INTF-0180-A` — « Un devis exporté par un utilisateur en français et réimporté par un
  utilisateur en anglais donne un devis identique, sans avertissement de format. »
- `WF-INTF-0180-A` — « Le même montant s'affiche « 1 234,56 » en français et « 1,234.56 » en
  anglais, et le total du projet est le même. » : constaté par EP-02 ;
- `WF-INTF-0180-A` — « Le fichier Excel exporté porte les mêmes en-têtes quelle que soit la langue
  de celui qui l'exporte. » : les en-têtes de l'annexe B, en français, fixes ;
- `WF-INTF-0080-A` — « Pour un fichier qui contient des lignes invalides, le compte rendu les
  liste avec leur motif avant la confirmation. » : `rejected`, chaque ligne par son onglet et son
  numéro de ligne Excel ;
- `WF-INTF-0080-A` — « Si l’utilisateur abandonne à cette étape, le projet reste inchangé. »
- `WF-INTF-0080-A` — « Si l’import est interrompu pendant son application, le projet revient à son
  état antérieur. » : les deux, constatées par EP-06 ; ici, sur un devis ;
- `WF-INTF-0090-A` — « On importe un planning MS Project, puis un devis, dans un projet qui comporte
  une révision marquée. »
- `WF-INTF-0090-A` — « Seule la révision en cours est modifiée : les tâches, les dates et les
  montants de la révision marquée sont identiques avant et après chaque import. » : les montants,
  ici ; les tâches et les dates, constatées par EP-06 ;
- `WF-INTF-0090-A` — « Un import sur un projet dont toutes les révisions sont marquées crée une
  révision en cours d’élaboration et s’y applique ; les révisions marquées sont inchangées. » :
  constaté par EP-06 ; ici, pour un devis, la révision créée porte les taux projetés (US-1500) ;
- écart : `WF-INTF-0090-A` — « L’import d’un planning sur la structure principale d’une révision qui
  porte un devis propre de risque laisse ce devis propre inchangé, tâches comprises ; l’import du
  même fichier sur ce devis propre laisse la structure principale inchangée. » : les devis propres
  sont d'EP-08, qui clôt (une seconde structure ne se pose pas : `cost_structure.kind` n'admet que
  `main`) ;
- `WF-INTF-0040-A` — « Un fichier XML produit par MS Project 2013 est importé sans erreur. »
- `WF-INTF-0040-A` — « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD, FF
  ou DF, et décalage — sont identiques à celles du fichier source ; une tâche en mode manuel du
  fichier est en mode manuel aux mêmes dates ; une tâche portant une contrainte « Pas avant le » est
  en mode manuel et signalée ; une tâche à 50 % d’avancement est importée non démarrée ; aucune
  ressource et aucun calendrier présents dans le fichier n’a été créé dans Waterfall, et
  l’utilisateur est informé que ces éléments ont été ignorés. » : les deux, constatées par EP-06 ;
- `WF-INTF-0040-A` — « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les
  lignes de devis et les lignées de ses tâches, et ses tâches démarrées. » : les lignes d'une tâche
  rapprochée par sa lignée restent sous elle ; les lignées et les tâches démarrées, constatées par
  EP-06 ;
- `WF-INTF-0040-A` — « Un fichier qui place la tâche d’un poste hors du sous-arbre de la tâche de
  son lot est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée
  a disparu est appliqué et le compte rendu nomme le poste qu’elle portait ; une tâche rattachée
  réimportée conserve son rattachement. » : constaté par EP-06 ;
- `WF-INTF-0050-A` — « Vérifiée en recette pour l’ouverture dans MS Project ; l’égalité des dates
  est couverte par le corpus de WF-QUA-0080. »
- `WF-INTF-0050-A` — « Un planning Waterfall exporté au format XML s’ouvre sans erreur dans les
  versions de MS Project visées par WF-INTF-0040. » : les deux, constatées par EP-06 et en recette ;
- `WF-INTF-0050-A` — « Les calendriers Waterfall y figurent et sont affectés aux tâches, et chaque
  tâche porte son identifiant Waterfall et, dans ses notes, sa description. » : l'exporteur
  d'EP-06 écrit un calendrier par calendrier applicable distinct, que `calendar_of(task)` tire des
  rôles des lignes : deux tâches aux rôles différents portent deux calendriers ; l'identifiant et
  la description, constatés par EP-06 ;
- `WF-INTF-0050-A` — « En mode automatique, MS Project recalcule pour chaque tâche des dates de
  début et de fin identiques à celles affichées par Waterfall. » : constaté par EP-06 ;
- `WF-INTF-0060-A` — « Vérifiée en recette pour l’ouverture dans MS Project ; l’absence d’écart de
  dates est couverte par le corpus de WF-QUA-0080. » : constaté par EP-06 et en recette ;
- `WF-INTF-0060-A` — « Un planning comportant au moins une tâche récapitulative, un jalon, les
  quatre types de liaison, et des tâches portant des rôles de ressources aux calendriers
  différents, est exporté, ouvert dans MS Project sans y être modifié, puis réimporté. » :
  l'aller-retour d'EP-06 rejoué sur un planning dont des tâches portent des lignes de rôles aux
  calendriers différents, sans ouverture dans MS Project ;
- `WF-INTF-0060-A` — « Le compte rendu ne présente aucun écart de dates ni de durées, et le planning
  obtenu est identique à celui relevé avant l’export. » : sur ce planning, lignes comprises ;
- `WF-INTF-0060-A` — « La date de début de planning est identique avant et après l’aller-retour. »
- `WF-INTF-0060-A` — « La description de chaque tâche est identique avant et après
  l’aller-retour. » : les deux, constatées par EP-06 ;
- écart : `WF-DAT-0110-A` — « Deux imports du même fichier de coûts réels laissent le même nombre
  de lignes et les mêmes montants, et une ligne exclue le reste. »
- écart : `WF-DAT-0110-A` — « L’insertion directe en base de deux lignes de coût de même projet, de
  même numéro de pièce et de même poste est rejetée ; de postes différents, elle aboutit. » : les
  deux, les coûts réels d'EP-09, qui clôt ;
- `WF-DAT-0110-A` — « Deux imports successifs du même fichier de devis donnent une révision en
  cours au contenu identique. » : les lignes rapprochées par leur lignée, écrite dans la colonne
  masquée du fichier ;
- `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le lien
  produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles prédéfinis et le
  catalogue des permissions. »
- `WF-EXP-0020-A` — « La création d’un projet est refusée et nomme les prérequis manquants, jusqu’à
  ce qu’une catégorie de coût de main-d’œuvre et un rôle de ressource aient été saisis. »
- `WF-EXP-0020-A` — « Une seconde exécution de l’installation ne crée ni compte, ni calendrier, ni
  nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent, tant que
  l’administrateur n’a pas fixé son mot de passe, et aucun lien ensuite. »
- `WF-EXP-0020-A` — « Le lien produit à l’installation est accepté plus d’une heure après sa
  production. »
- `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %, 50 % et
  75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines, et le
  calendrier par défaut compte huit heures du lundi au vendredi et aucune le week-end. » : les cinq,
  constatées par EP-03, EP-04 et EP-05 ;
- `WF-EXP-0020-A` — « Le nom de l’entreprise saisi à l’installation figure sur un devis exporté ;
  modifié, il figure sur le suivant. » : l'onglet « Présentation » et le pied de page ;
- `WF-PRJ-0080-A` — « La création d’un projet sans libellé est refusée. »
- `WF-PRJ-0080-A` — « La date de réception de la commande est saisissable à tout moment et n’est
  exigée par aucune transition. » : les deux, constatées par EP-04 ;
- `WF-PRJ-0080-A` — « Le nom du client est saisissable à tout moment, n’est exigé par aucune
  transition, et figure sur la présentation d’un devis exporté. » : l'onglet « Présentation » ;
- `WF-REF-0140-A` — « La devise apparaît partout où un montant est affiché ou exporté, et aucun
  écran ne propose d’en changer ni d’en saisir une seconde. » : l'onglet « Présentation » nomme la
  devise de l'installation ; l'affichage et l'absence d'écran, constatés par EP-02 et EP-05 ;
- propre à l'US : l'exporteur `estimate` écrit le classeur de l'annexe B — « Présentation »,
  « Devis » (une ligne par lot, par poste, par lot hors de ses postes, « Hors lot », les montants
  par nature, les heures par code comptable, la case « Inclus »), un onglet par poste, par lot et
  « Hors lot » dont les lignes forment un tableau Excel aux listes, formules et mise en forme
  étendues à la saisie, « Tâches » et « Paramètres » protégés, le logo et le pied de page, la lignée
  dans une colonne masquée — avec les seules fonctions que toutes les versions d'Excel et de
  LibreOffice connaissent, et un texte saisi écrit comme texte ; le nom d'un onglet suit les règles
  d'Excel — caractères refusés, 31 unités UTF-16, unicité sans égard à la casse par suffixe —, par
  une fonction commune aux formats Excel (#2190) ; l'export d'une structure sans ligne donne le
  modèle vierge ; `requestExport` sous `export_estimate`, gardée par `estimate.read` ;
- propre à l'US : le format `estimate` enregistré lit l'en-tête (A1, B1, A2, B2), analyse chaque
  onglet de lignes par ses en-têtes quel que soit leur rang, ignore les colonnes inconnues, les
  lignes vides et la ligne de total, lit les nombres dans des cellules numériques et rejette un
  nombre en texte, rapproche une ligne par sa lignée, désigne une tâche par l'onglet « Tâches » ou
  par son libellé, crée les lignes sans lignée (budgété nul si le projet porte une référence),
  supprime les lignes absentes du fichier sauf sous une tâche démarrée ou terminée (`kept`),
  rejette une ligne nouvelle sous une tâche terminée de la structure principale
  (`task_not_completed`, #1767) et présente ses écarts (`differences`) ; `ProjectCommand.import_estimate`
  sous `estimate.write`, indisponible dès En cours ; l'import appliqué n'entre pas dans l'historique
  annulable ;
- propre à l'US : l'écran des échanges, branché par EP-06, importe et exporte un devis contre le
  service, et le parcours de l'import en deux temps d'`exchanges.spec.ts` porte `@shared`, joué sur
  un projet que la course crée ; chaque réponse est validée contre le contrat dans les tests du
  service.

**Notes de réalisation.** Le format reprend la mécanique d'EP-06 (`register_format`,
`register_exporter`) sans rien écrire de la purge ni du téléchargement, qui sont de
`core/exchanges`. La bibliothèque Excel et la place du logo dans le dépôt se fixent à la conception.
Le témoin importe le devis de l'avenant 2 (`import_analysed`), un différentiel : l'import du devis
de PRJ-001 ne se rejoue pas avant EP-08 ; les parcours de la course importent sur un projet à eux.

**Hors périmètre.** Les formats « Reste à engager » et « Coûts réels » (EP-09) ; l'import sur un
différentiel ou un devis propre, les lignes de provision (EP-08) ; l'écran des échanges lui-même
(EP-06).

---

## US-1560 — La grille de devis branchée sur le service

- **statut** : à faire
- **exigences** : `WF-DEV-0050-A`, `WF-IHM-0060-A`, `WF-IHM-0110-A`
- **opérations** : `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo` ; toutes celles
  de l'EPIC que la grille de devis lit et écrit
- **issue** : 2368

**En tant que** chef de projet, **je veux** que la grille de devis travaille contre le service —
saisie des lignes, création et déplacement des tâches et des lignes, collage depuis un tableur,
annulation, tri, filtres, indicateurs —, **afin de** chiffrer mon projet sans faux back.

**Critères d'acceptation.**

- `WF-DEV-0050-A` — « La création d’une tâche depuis la grille de devis la fait apparaître dans la
  grille de planning, en mode automatique, d’une durée d’un jour et sans prédécesseur, et le
  déplacement d’un sous-arbre depuis l’une se répercute dans l’autre. » : le parcours du report
  d'EP-06 (#1057) rejoué avec une ligne sous la tâche créée ;
- `WF-DEV-0050-A` — « Le montant d’une récapitulative suit celui de ses subordonnées et n’est pas
  modifiable. » : `ancestors` recalculés à chaque écriture de ligne, la cellule calculée refusée
  en nommant `lines_and_subordinates` ;
- `WF-DEV-0050-A` — « La grille de devis ne présente pas le montant budgété ; une ligne dont la
  tâche se place deux ans après l’année de référence, avec une inflation de 2 %, affiche un montant
  réestimé supérieur de 4,04 % à son montant aux taux de l’année de référence. » : `base_amount` et
  `reestimated_amount` du service, sur une tâche datée deux ans après l'année de référence d'un
  projet à 2 % ;
- `WF-DEV-0050-A` — « Dans la structure principale, la création d’une ligne sous une tâche terminée,
  ou le déplacement d’une ligne vers elle, est refusé. » : le refus du service (#1767) dit à la
  ligne en cause ;
- écart : `WF-DEV-0050-A` — « Dans un différentiel, la modification de la quantité d’une ligne d’une
  tâche terminée aboutit, et la fusion lui donne ce montant budgété ; dans la structure principale,
  elle est refusée. » : le refus sur la structure principale, ici ; le différentiel et la fusion
  sont d'EP-08, qui clôt ;
- `WF-DEV-0050-A` — « La grille de devis ne propose la saisie ni de la durée ni des prédécesseurs
  d’une tâche. » : constaté par EP-15, rejoué contre le service ;
- écart : `WF-DEV-0050-A` — « Sur un projet En cours, la grille de devis de la structure principale
  ne propose aucune saisie ni aucune commande d’écriture ; celle d’une structure différentielle les
  propose. » : la lecture seule suit `edit_estimate` de la structure principale, que le service
  rend indisponible dès En cours (`project_before_in_progress`), sur PRJ-001 ; la structure
  différentielle est d'EP-08, qui clôt ;
- `WF-IHM-0060-A` — « Chaque colonne d’une table plate se trie dans les deux sens. » : constaté par
  EP-02 et EP-05 ;
- `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose de tri ; dans
  la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans déplacer les
  tâches. » : `sort_by` sur une colonne de la ligne, tenu par le serveur (US-1490), lu dans la
  grille ;
- `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours visibles,
  de même que la colonne de libellé après défilement horizontal. » : constaté par EP-02, rejoué
  contre le service sur les six mille nœuds de PRJ-001 ;
- `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la
  réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. » :
  constaté par EP-03 ;
- `WF-IHM-0060-A` — « Le nombre de lignes par page choisi pour une table est retrouvé à sa
  réouverture, sans changer celui des autres tables ; une grille arborescente n’offre pas ce
  choix. » : constaté par EP-15 ;
- `WF-IHM-0110-A` — « La suppression d’une tâche puis son annulation restituent la tâche, ses lignes
  et ses liaisons. » : par US-1490 ; ici, depuis la grille ;
- écart : `WF-IHM-0110-A` — « Le réexamen d’un risque puis son annulation lui rendent sa
  probabilité et son état précédents. » : les risques sont d'EP-08, qui clôt ;
- `WF-IHM-0110-A` — « Cinquante modifications successives s’annulent une par une, puis se
  rétablissent dans l’ordre. » : cinquante saisies de lignes, depuis la grille de devis, contre le
  service ;
- `WF-IHM-0110-A` — « L’annulation d’une modification qu’un autre contributeur a depuis reprise est
  refusée en nommant l’objet en conflit. » : constaté par EP-06 ;
- `WF-IHM-0110-A` — « Aucune commande n’annule un marquage, un import appliqué, une déclaration de
  survenance ou une exclusion de ligne de coût. » : constaté par EP-06 et US-1550 ; la survenance et
  l'exclusion sont d'EP-08 et d'EP-09, EP-08 clôt ;
- propre à l'US : `previewPaste` et `applyPaste` d'EP-06 jugent les colonnes de la ligne —
  `cost_category`, `resource_role`, `quantity`, `hours`, `unit_disbursement`, `subproject`,
  `payment_delay_days` — dans l'ordre de `NodeColumn`, par les mêmes fonctions que la saisie d'une
  cellule, que les crochets de la facette fournissent : `COMPUTED_VALUE` pour la catégorie d'une
  ligne de main-d'œuvre et pour un montant, `FIELD_NOT_ACCEPTED`, `UNKNOWN_COST_CATEGORY`,
  `UNKNOWN_RESOURCE_ROLE`, `UNKNOWN_SUBPROJECT`, `PROVISION_CATEGORY_RESERVED`,
  `TASK_WITHOUT_WORKING_HOURS`, et `task_not_completed` sur une cellule non vide d'une ligne d'une
  tâche terminée de la structure principale (#1767) ; un bloc collé sous une tâche crée ses lignes ;
- propre à l'US : la grille de devis lit `listNodes` servi — colonnes, tri, filtres, recherche,
  totaux —, écrit chaque cellule par `updateEstimateLine`, crée, déplace et supprime tâches et
  lignes, colle, annule et rétablit, porte une ligne à un sous-projet, et lit les indicateurs
  (US-1510) et les taux manquants ; `MockupNotice` est retiré de l'écran du devis, les aides
  `frontend/help/fr/FBS-4.4*.md` disent ce que le service fait ; les parcours `entry.spec.ts`,
  `computed.spec.ts`, `keyboard.spec.ts`, la part du devis de `grid.spec.ts`, `structure.spec.ts`,
  `paste.spec.ts`, `undo.spec.ts` et `context.spec.ts` (`BEFORE_THE_DATA` levé pour le devis) portent
  `@shared` pour ce qu'ils jouent contre le service, les écritures sur un projet que la course crée ;
  la constante `NODES` de `estimate/page.test.tsx` est nommée d'après ce qu'elle est (#1973).

**Notes de réalisation.** Les écrans sont ceux d'EP-02 (US-0120, US-0150, US-0220), d'EP-14 et
d'EP-15 (US-0460, US-0480, US-0500) ; cette US ne les réécrit pas. Un manque que le branchement
révèle devient une issue ; un manque du contrat, une « Interface contract issue ». Les parcours
qui lisent le devis propre d'un risque (`paste.spec.ts`, `entry.spec.ts`) restent gardés par
`inService` jusqu'à EP-08, et leur entrée du guide le dit.

**Hors périmètre.** La grille du reste à engager (EP-09) ; les différentiels et le devis propre
(EP-08).

---

## US-1570 — Le témoin : la tranche des lignes, PRJ-001 En cours, et les parcours rejoués

- **statut** : en cours
- **exigences** : `WF-QUA-0040-A`, `WF-INTF-0010-A`
- **opérations** : aucune en propre ; le chargement passe par les interfaces du noyau
- **issue** : 2369

**En tant que** développeur, **je veux** charger, sur une plateforme qui porte les tâches du
témoin, les lignes des trois révisions de PRJ-001, la mise à jour des taux de la révision 101 et la
désignation de l'offre qui mène le projet En cours, et rejouer contre le service tous les parcours
du devis écrits sur le faux back, **afin que** les tests déjà écrits prouvent le service sur le
plus gros devis.

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour la tranche des lignes — les cinq mille lignes de la structure principale de la
  révision en cours de PRJ-001 et celles des révisions marquées 100 et 101, leurs rôles,
  catégories, grandeurs, délais de paiement et sous-projets, la mise à jour des taux acceptée sur la
  révision 101 le 12 janvier 2026, la désignation de l'offre 100 le 15 janvier 2026 et le passage
  En cours qu'elle produit —, chargée par `waterfall-api load-witness` par les interfaces, avec les
  identifiants et les instants du témoin, les lignes des révisions marquées chargées avant leur
  marquage ; la référence reste l'offre 100 jusqu'à la fusion de l'avenant 1 (EP-08), les
  provisions sont d'EP-08, les coûts d'EP-09, les volumes entiers d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes
  identiques. » : deux plateformes chargées portent les mêmes identifiants, lignées et montants ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les libellés sont ceux du témoin, fictifs ;
- écart : `WF-INTF-0010-A` — « Un utilisateur porteur du rôle prédéfini « chef de projet » crée un
  projet et atteint, sur un projet où il est habilité, les fonctions de gestion des révisions
  (FBS-4.1), de paramétrage du projet, contributeurs compris (FBS-4.2), de planification (FBS-4.3),
  de chiffrage (FBS-4.4), de gestion des risques (FBS-4.6), d’estimation du reste à engager
  (FBS-4.5), de gestion des coûts réels (FBS-4.7), de lecture des indicateurs (FBS-4.8), de sortie
  du cycle de vie (FBS-4.9) et d’échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les
  mène jusqu’à leur terme, marquage d’une révision, exclusion d’une ligne de coût et déclaration
  d’une sortie compris. » : le chiffrage (FBS-4.4) et les flux FLX-03 et FLX-04, ici, par le compte
  « chef de projet » de la course, jusqu'au passage En cours ; les révisions, le paramétrage, la
  sortie et la planification sont constatés par EP-04 et EP-06 ; les risques, le reste à engager,
  les coûts réels, les indicateurs et les autres flux sont d'EP-08 à EP-10, EP-08 clôt ;
- propre à l'US : `make mock-data` écrit, à côté des exemples, le fichier de la tranche des lignes
  que la commande lit, sans que le back importe `wftools` ; `witness/estimate_lines.py` s'enregistre
  par `register_revision_filler` d'EP-06 et, après la tranche des tâches de chaque révision,
  réconcilie par lignée les lignes que la copie lui a données avec celles que le fichier décrit ;
  `witness/revisions.py` rejoue la mise à jour des taux et attend que la désignation de l'offre
  aboutisse, le passage En cours constaté par les transitions du témoin ; les lectures du témoin
  chargé — `nodes_estimate`, `nodes_estimate_sorted`, `nodes_estimate_filtered`,
  `nodes_estimate_hours`, `volume/nodes_thousand`, `estimate_indicators`, `workload`,
  `contributor_suggestions`, `revisions`, `project`, `comparison` — sont comparées aux exemples,
  montants compris, aux colonnes d'audit, à la référence, aux provisions et aux montants qui en
  dépendent près, listés dans le test ;
- propre à l'US (lot d'outil) : les exemples projettent l'offre 100 depuis son année de référence,
  2025, et non plus depuis 2026 — `mockdating` corrigé, les exemples régénérés, le raccourci de
  `DECISIONS.md` (section L-01 du « Contrat figé ») retiré, le budget de référence des lignes que
  l'avenant 1 ne touche pas recalculé (#467) —, avant que la tranche des lignes ne se compare aux
  exemples (#1628, décision de l'auteur du 2026-11-07, qui remplace l'option 4 du 2026-10-29) ;
- propre à l'US : tous les parcours du devis, du plan de charge, de la comparaison, des
  contributeurs proposés et de l'import du devis étiquetés `@shared` passent contre le service, le
  témoin chargé ; la définition de fini est constatée — un projet chiffré et passé En cours, un
  devis exporté et réimporté sans écart, cinquante saisies annulées puis rétablies — ; les entrées
  du guide que `BEFORE_EP07` et `BEFORE_THE_DATA` (le devis) gardaient, et celles qu'EP-04 a
  marquées « levées par EP-07 » (PRJ-001 En cours, sa référence, ses lignes) et qu'EP-06 laisse
  (« les lignes, les montants, le devis »), sont levées, le guide disant ce que la tranche charge et
  ce qu'EP-08 et EP-09 y ajoutent ; le statut de cette US est passé `fini` dans le fichier — chaque
  autre US l'est par le lot qui la termine.

**Notes de réalisation.** La tranche suit la chronologie d'EP-04 (`Act.at`) et le registre d'EP-06
(`register_revision_filler`) : les lignes de chaque révision s'écrivent après ses tâches et avant
son marquage. Le calculé devient l'attendu, et la spécification arbitre : les exemples projetaient
l'offre 100 depuis 2026 quand elle porte l'année de référence 2025 (raccourci déclaré, #1628) ; EP-07,
premier EPIC dont le service calcule des montants, corrige les exemples plutôt que de lister l'écart
(README, « Le jeu de données de référence »). Le récit de la mise à jour des taux (2025 → 2026)
ne dépendait pas du raccourci. Les deux fichiers d'outil — les exemples corrigés, puis la tranche des
lignes — sont des lots d'outil, lançables tôt, après celui d'EP-06 (US-1480/L1 #2330), seul autre
lot à écrire `wftools`.

**Hors périmètre.** Les provisions, l'avenant 1 et la référence 101 (EP-08) ; les coûts réels
(EP-09) ; les trois cents projets (EP-13).

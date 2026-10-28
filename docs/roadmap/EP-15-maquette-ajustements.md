---
id: EP-15
titre: La maquette ajustée après la validation de l'auteur, chaque geste du contrat montré
statut: livré
depend_de: EP-14
famille: front
issue: 1087
---

# EP-15 — Maquette : ajustements issus de la validation

## Objet

L'auteur a validé la spécification 1.0, la maquette et le contrat écran par écran, après la fusion
d'EP-03 puis d'EP-14 dans `main` (décision du 2026-10-11, validation du 2026-10-18). EP-15 réalise
les ajustements qu'il a décidés — les trente-trois issues du label `EP-15` — de sorte qu'à la fin de
l'EPIC la spécification, la maquette et le contrat soient entièrement validés : chaque opération
d'écriture du contrat a un geste dans la maquette, et chaque geste de la maquette une opération du
contrat. La spécification a été reprise avant ce cadrage (C-350 à C-365, PR #1076) : les noms du
lotissement — des lots, qui contiennent des postes, qui contiennent des livrables —, le partage du
devis et du reste à engager selon la phase du projet, le refus du changement de sous-projet d'une
ligne démarrée, le nombre de lignes par page, l'exception des calendriers, le recalcul des durées,
la structure lue, la mise à jour des taux, l'abandon hors de l'annulation.

Il vient après EP-14 et avant les EPIC de domaine parce qu'il fixe ce qu'ils serviront : polir un
contrat et des écrans encore appelés à changer ferait payer deux fois chaque ajustement, au front
comme au back. Le durcissement — mineurs du contrat et du front, accessibilité des dialogues et des
menus, navigateurs, reliquats de tests — passe à EP-16, qui le suit.

## Ce qui en fait partie

Les issues du label `EP-15`, groupées par parcours de l'utilisateur :

- le lotissement en lots, postes et livrables, au contrat, dans le témoin et dans les écrans
  (#1054) — US-0450, menée en premier ;
- les gestes de structure des trois grilles — ajouter, indenter et désindenter, déplacer,
  supprimer —, le devis en chiffrage, le reste à engager en réalisation (#1056) — US-0460 ;
- la saisie des tâches et de leurs prédécesseurs dans la grille de planning (#1073) — US-0470 ;
- l'inscription d'une tâche à une chronologie et le sous-projet d'une ligne, par le menu
  contextuel (#1065, #1066) — US-0480 ;
- du projet créé au projet En cours : l'encart de démarrage du planning, l'ouverture et l'abandon
  d'une révision, la désignation de la référence, la mise à jour des taux (#1058, #1074,
  #1072) — US-0490 ;
- la structure lue par les grilles, l'affichage d'un différentiel comme un diff, la comparaison de
  deux révisions dans la grille dense (#1060, #624, #729) — US-0500 ;
- les avenants : préparer, chiffrer, contractualiser (#1061) — US-0510 ;
- les risques : identifier, chiffrer le devis propre, modifier, réexaminer, supprimer, déclarer
  survenu (#1062, #763) — US-0520 ;
- le Gantt épinglé et zoomé, la chronologie en frise à couloirs (#1063, #1064, #1068) — US-0530 ;
- les gestes du Kanban (#1070) — US-0540 ;
- les graphiques et les cartes : plans de charge empilés, chiffres clés en cartes, matrice à bulles,
  le plan de charge depuis le reste à engager (#1051, #1052, #1053, #1069) — US-0550 ;
- le cadre de l'application : le plancher et la barre des grilles, l'historique des messages, le
  menu latéral (#1033, #1041, #1042, #1043, #1050) — US-0560 ;
- le référentiel et les grilles paginées : les paramètres de coûts empilés, le nombre de lignes par
  page, les calendriers sans filtre d'heures, les unités de durée (#1044, #1045, #1047,
  #1049) — US-0570 ;
- l'aide en ligne et les infobulles (#1071, #1075) — US-0580 : les infobulles, la mécanique de
  l'aide, cinq écrans clés et les notions EVM ; les autres aides, la recherche et la section « Ses
  colonnes » du panneau passent à EP-16, US-0670 (décision de l'auteur du 2026-10-25, #1445).

Chaque modification du contrat que ces issues appellent, avec ses exemples, son entrée dans
`docs/api/DECISIONS.md`, le faux back et le témoin régénérés (`make mock-data`), faite avant le
code qui la consomme (« Conception », « Modifications du contrat »).

## Ce qui n'en fait pas partie

- la validation elle-même : l'auteur l'a faite, et ses décisions sont dans les issues ; une
  « Décision de l'auteur (2026-10-18) » ne se rediscute pas ;
- le comportement réel des écrans : il arrive avec l'EPIC de leur domaine — EP-04 pour le projet et
  les révisions, EP-05 pour le référentiel, EP-06 pour le planning, EP-07 pour le devis, EP-08 pour
  les avenants et les risques, EP-09 pour le reste à engager et le Kanban, EP-10 et EP-11 pour les
  indicateurs et le portefeuille ; le report d'un geste de structure d'une grille à l'autre se
  constate contre le service, en EP-06 (#1057) ;
- Annuler et Rétablir, posés par EP-02 et branchés sur le service par EP-06 (#1056, point 4 ;
  #1057 ; décision de l'auteur au cadrage, 2026-10-18) — l'écart est écrit au croisement
  contrat-maquette ;
- le durcissement : les mineurs du contrat et du front, l'extension du harnais d'accessibilité aux
  dialogues et aux menus (#782), les navigateurs (US-0290, #92) et les reliquats de tests (#776,
  #781, #784) — EP-16 ;
- les 409 nommés que le service des sauvegardes ne rend pas (#1035) — EP-13 ;
- les aides des écrans hors des cinq écrans clés, la recherche de l'aide et la section « Ses
  colonnes » du panneau : EP-16, US-0670 (décision de l'auteur du 2026-10-25, #1445 — les lots
  US-0580/L3b, L4 et L5 en sont devenus US-0670/L1 à L5) ;
- la version anglaise de l'aide en ligne : décidée en EP-16 après la relecture de toutes les aides
  par l'auteur (#1075, #1441), elle se constate avec WF-IHM-0140, qu'EP-11 clôt ;
- les formats Excel de l'annexe B, dont le reste attend les fichiers d'exemple de l'auteur
  (`docs/spec/TODO.md`, entrée 1) — EP-07 et EP-09.

## Exigences réalisées

EP-15 ne clôt aucune exigence : il montre dans la maquette, contre le faux back, les gestes que
l'EPIC de chaque domaine servira et vérifiera en entier. Chaque US cite les exigences dont une
phrase de Vérif tient côté front, et ses tests citent ces exigences ; les phrases qui demandent le
service sont des écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-PRJ-0020-A` | Lotissement | début — close en EP-04 | US-0450 |
| `WF-PLA-0080-A` | Grille de planning | début — close en EP-06 | US-0460 |
| `WF-DEV-0050-A` | Grille de devis | début — close en EP-07 | US-0460 |
| `WF-RAE-0040-A` | Grille de reste à engager | début — close en EP-09 | US-0460 |
| `WF-PLA-0020-A` | Mode de planification | début — close en EP-06 | US-0470 |
| `WF-PLA-0030-A` | Liaisons entre tâches | début — close en EP-06 | US-0470 |
| `WF-PLA-0160-A` | Unités de durée | début — close en EP-06 | US-0470 |
| `WF-PLA-0060-A` | Inscription aux suivis | début — close en EP-10 | US-0480 |
| `WF-PRJ-0050-A` | Sous-projets | début — close en EP-09 | US-0480 |
| `WF-PRJ-0030-A` | Squelette de planning | début — close en EP-06 | US-0490 |
| `WF-REV-0010-A` | Unicité de la révision en cours | début — close en EP-07 | US-0490 |
| `WF-REV-0040-A` | Désignation de la révision de référence | début — close en EP-08 | US-0490 |
| `WF-CYC-0030-A` | Conditions du passage à En cours | début — close en EP-07 | US-0490 |
| `WF-REV-0060-A` | Année de référence et mise à jour des taux à la création d’une révision | début — close en EP-07 | US-0490 |
| `WF-IHM-0020-A` | Contexte de lecture affiché | début — close en EP-08 | US-0500 |
| `WF-REV-0080-A` | Comparaison de deux révisions | début — close en EP-07 | US-0500 |
| `WF-REV-0100-A` | Structures de coûts d'une révision | début — close en EP-08 | US-0500 |
| `WF-REV-0050-A` | Fusion d’un différentiel | début — close en EP-08 | US-0510 |
| `WF-RIS-0010-A` | Attributs d’un risque | début — close en EP-08 | US-0520 |
| `WF-RIS-0020-A` | États d’un risque | début — close en EP-08 | US-0520 |
| `WF-RIS-0030-A` | Devis propre d’un risque | début — close en EP-08 | US-0520 |
| `WF-PLA-0090-A` | Diagramme de Gantt | début — close en EP-06 | US-0530 |
| `WF-PLA-0140-A` | Chronologies nommées | début — close en EP-06 | US-0530 |
| `WF-RAE-0030-A` | Démarrage d’une tâche | début — close en EP-09 | US-0540 |
| `WF-DEV-0070-A` | Plan de charge du projet | début — close en EP-09 | US-0550 |
| `WF-PTF-0060-A` | Plan de charge agrégé | début — close en EP-11 | US-0550 |
| `WF-RIS-0040-A` | Grille de suivi des risques | début — close en EP-08 | US-0550 |
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | début — close en EP-11 | US-0550, US-0570 |
| `WF-IHM-0080-A` | Traitements longs | début — close en EP-09 | US-0560 |
| `WF-OBS-0020-A` | Journaux structurés et corrélation | début — close en EP-13 | US-0560 |
| `WF-IHM-0060-A` | Lecture d'une grille | début — close en EP-07 | US-0570 |
| `WF-IHM-0140-A` | Aide en ligne | début — close en EP-11 | US-0580 |

Les exigences déjà closes par un EPIC livré que ces travaux touchent — WF-IHM-0030, WF-IHM-0040,
WF-IHM-0070, WF-IHM-0090, WF-IHM-0100, WF-IHM-0110, WF-INTF-0170 (EP-02, EP-14) — restent closes :
leurs tests existants continuent de les citer, et les écrans ajustés ne les contredisent pas.

## Opérations du contrat

Celles d'EP-02, d'EP-03 et d'EP-14, et les écritures que les écrans branchent pour la première
fois, chacune avec les lectures qui la préparent :

- la structure : `createNode`, `moveNodes`, `deleteNode`, `setPredecessors`, `setNodeTracking`,
  `updateTaskFacet` (libellé, description, mode, durée, dates), `updateEstimateLine`
  (`subproject_id`) ; `listTimelines`, `listSubprojects`, `listCostStructures`, `listNodes` (par
  structure) ;
- les révisions : `createRevision`, `abandonRevision`, `designateReferenceRevision`,
  `applyRateUpdate`, `compareRevisions` (dans sa forme nouvelle) ; `getProject`, `getRevision`,
  `getRateUpdateProposal` ;
- les avenants : `createCostStructure`, `getStructureMergeReport`, `mergeCostStructure` ;
- les risques : `createRisk`, `updateRisk`, `reviewRisk`, `deleteRisk`, `declareRiskOccurrence` ;
  `getProjectRiskMatrix`, `getPortfolioRisks` (dans leur forme nouvelle) ;
- le Kanban : `setTaskProgress`, `listStartableTasks` (dans sa forme nouvelle) ;
- le projet : `generatePlanningSkeleton`, `uploadFile`, `openImport`, `getWorkBreakdown`,
  `setWorkBreakdown` (dans leur forme nouvelle) ;
- le référentiel et les préférences : `setDurationUnits`, `listCalendars` (sans ses bornes
  d'heures), `updateMyPreferences` (`page_size`, `timelines`), `getPortfolioWorkload` (dans sa
  forme nouvelle).

Les modifications du contrat sont listées opération par opération dans « Conception » ; chacune
précède le code qui la consomme. Le croisement contrat-maquette, à la fin de la conception, met
chaque opération d'écriture en regard de l'écran et du geste qui l'appellent.

## Préalables

EP-14 livré ; la spécification reprise après la validation (PR #1076) fusionnée dans `main`, aucune
issue `specification` ouverte hors #1045 ; `make check-spec` au vert sur `main`.

## Définition de fini

- chaque issue du label `EP-15` est soldée : réalisée par un lot, ou écartée dans l'issue avec la
  décision de l'auteur ;
- la table du croisement contrat-maquette (« Conception ») est sans manque : chaque opération
  d'écriture du contrat a l'écran et le geste qui l'appellent, ou l'écart écrit que l'auteur a
  tranché ;
- chaque modification du contrat a son entrée dans `docs/api/DECISIONS.md`, ses exemples, et le
  faux back et le témoin sont régénérés par l'outillage, jamais à la main (`make mock-data`) ;
- `make check` passe sur la branche de l'EPIC : contrat, front, faux back, parcours de bout en bout,
  harnais d'accessibilité aux deux largeurs, roadmap ;
- l'auteur a constaté, écran par écran, les ajustements livrés ;
- aucune entrée nouvelle de `docs/spec/TODO.md` n'est restée sans reprise ;
- l'aide en ligne en français est rédigée pour les cinq écrans clés et les notions EVM, et relue
  par l'auteur ; les autres aides et la recherche sont reportées à EP-16 (US-0670, décision de
  l'auteur du 2026-10-25, #1445) ; la version anglaise se décide en EP-16, après la relecture de
  toutes les aides, et son écart est écrit sous WF-IHM-0140 (US-0580, puis US-0670).

## Constats reçus

Ramenés en EP-15 par la décision de l'auteur du 2026-10-18, à rattacher à l'issue de l'EPIC à son
ouverture, chacun sous l'US qui le règle :

- #624 — front : la comparaison de révisions rend ses 2 770 modifications en une table simple —
  reporté d'EP-14 vers EP-07 (2026-10-18), puis ramené ici : la comparaison passe dans la grille
  dense, marquée comme un diff (#1060) — US-0500 ;
- #729 — e2e : la comparaison de `revisions.spec` n'écrit pas toujours son adresse en 15 s dans la
  file — suit #624, seul l'écran réglant la marge — US-0500 ;
- #763 — front : les formulaires du risque (provision de L42p, exemples de succès de `createRisk`,
  `updateRisk`, `reviewRisk`) — reporté d'EP-14 vers EP-08, puis ramené ici : repris par #1062 —
  US-0520 ;
- #1033 — front : sur un écran rempli, le plancher de la grille ne remonte pas la chaîne des
  `min-h-0` — relevé par la reprise de `main` d'EP-14 (#1032) — US-0560.

Ramenés d'EP-16 par la décision de l'auteur au cadrage (2026-10-18, réponses aux questions 5 à 7),
parce que les parcours d'EP-15 en ont besoin :

- #786 — contrat : la tâche qui porte la provision d'un risque ne se désigne pas à sa déclaration
  (WF-RIS-0010) — le formulaire d'US-0520 la désigne ; part contrat d'US-0520 ;
- #788 — contrat : l'horizon et le cycle de liaisons n'ont pas de refus décrit pour les saisies —
  la part « saisies » seule (`setPredecessors`, `updateTaskFacet`, `createNode`, `moveNodes`), que
  la colonne des prédécesseurs d'US-0470 dit à la cellule ; la part « fusion » reste à EP-16 ;
- #791 — outil : la révision courante du témoin ne reprend pas l'avenant 2 (WF-REV-0100) — le
  différentiel du témoin fait voir la marque du diff sans variante (US-0500), et donne au compte
  rendu de fusion son premier exemple réel (US-0510) ;
- #802 — contrat : la lecture du lotissement ne dit pas si une tâche porte un poste ou un lot —
  `attached_task` sur chaque lot et chaque poste lus, part contrat K1 d'US-0450 (validation de la
  conception, réponse 8).

Les autres constats qu'EP-14 avait reportés vers EP-15 pour le durcissement — les mineurs du
contrat (#774 et ses sous-issues, #785, #789, #790, #792, #795, #803), les mineurs du front
(#806, #817, #819, #779, #846 à #1024), l'accessibilité des dialogues (#782), les reliquats de tests
(#776, #781, #784) et US-0290 (#92) — portent le label `EP-16` et sont les « Constats reçus »
d'EP-16. #1035 est reçu par EP-13. Cinq d'entre eux, que les ajustements rendent caducs, se ferment
à l'ouverture des issues d'EP-15 avec la décision qui les rend caducs (décision de l'auteur,
2026-10-18) : #872 et #937 par l'historique des messages (#1043, US-0560), #959 et #960 par la
barre et l'historique (#1042, #1043, US-0560), #821 par la frise des chronologies (#1068,
US-0530). #817 et #819 restent en EP-16, réduits aux points qu'aucune US d'EP-15 ne couvre
(« Conception », « Ce que le cadrage décide »).

## Conception

Celle d'EP-02 et d'EP-14 fait foi : arborescence du front, faux back et exemples, univers témoin,
composants partagés, refus par champ, défauts nommés du guide. EP-15 n'a ni table, ni migration, ni
module du noyau : il écrit du front, des parties du contrat avec leurs exemples, et des générateurs
du témoin (`wftools`), un outil écrit en passant qui ne change pas sa famille. Ce qui suit est ce
qu'il ajoute, validé par l'auteur le 2026-10-18 (les huit questions de la conception, toutes
tranchées dans le sens proposé).

### Ce que le cadrage décide

- **Les US citent les exigences de domaine** (décision de l'auteur, réponse 2 du 2026-10-18), avec
  chaque phrase de Vérif en critère ou en écart ; EP-15 n'en clôt aucune, et les tableaux d'EP-04,
  EP-06 à EP-11 et EP-13 disent « amorcée en EP-15 ». C'est le contraire de ce qu'EP-02 (US-0220) et
  EP-14 (« Ce que le cadrage décide ») avaient choisi — aucune US pour les commandes, les tableaux
  de domaine gardés « entière » — : les tests d'EP-15 citent ainsi l'exigence dont ils éprouvent la
  phrase, et `make roadmap` tient chaque phrase. Écarté : la forme d'EP-02, qui laissait aux
  critères propres des phrases que la roadmap ne vérifie pas.
- **L'échange des noms du lotissement garde le sens des identifiants** (#1054, décision 2) :
  `WorkPackage` est un lot, `OrderItem` un poste, `WorkPackage` passe au niveau 1. Ce qui s'attache
  au niveau suit : le total par lot de WF-DEV-0060 devient `EstimateIndicators.by_work_package`,
  motif `work_package_without_task` ; la règle « la tâche d'un poste se trouve dans le sous-arbre de
  la tâche de son lot » prend le code `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, `params.work_package_task`
  et `params.order_item_tasks`. Écarté : garder les codes et les noms d'ancienne lecture avec une
  description inversée, qui ferait lire « poste » là où le code dit `work_package` (défaut n° 10 du
  guide : un nom qui dit autre chose que la cause).
- **`createRisk` crée la structure propre du risque** avec sa ligne de provision, comme le contrat
  le dit déjà (« La création ouvre la structure de coûts propre du risque ») : le parcours d'US-0520
  n'appelle pas `createCostStructure` de nature `risk`, qui reste au contrat pour un risque dont la
  structure manquerait — EP-08 en décide. Écarté : deux appels depuis le formulaire, qui pourraient
  laisser un risque sans devis propre.
- **Annuler et Rétablir restent à EP-06** (#1056, point 4 ; #1057 ; décision de l'auteur, réponse
  4) : `undoLastChange` et `redoLastUndo` sont l'écart écrit du croisement contrat-maquette, les
  commandes posées par EP-02 (US-0140) restant visibles et non branchées. Écarté : les brancher
  contre le faux back, qui ne garde rien et ne saurait rendre l'état d'avant.
- **L'historique des messages est une décision de conception**, sans exigence WF-IHM nouvelle
  (#1043 ; réponse 9) : il vit dans le front, propre à la session, et aucun test ne cite d'exigence
  pour lui-même — ceux qui le traversent citent WF-IHM-0080 et WF-OBS-0020 pour ce qu'ils y lisent.
- **Trois constats d'EP-16 sont ramenés** (réponses 5 à 7) : #786, part contrat d'US-0520 ; #788,
  la part « saisies », part contrat d'US-0470, la part « fusion » restant à EP-16 ; #791, part
  outillage d'US-0500.
- **#817, #819 et #802, point par point** (réponse 10 ; table acceptée par l'auteur à la
  validation de la conception, 2026-10-18) :

  | Issue, point | Couvert par | Proposition |
  |---|---|---|
  | #817.1 — `byField` généralisé à toute écriture de cellule | US-0470 (le refus dit à la cellule, `cell-writes.ts`) ; US-0460 (dit à la ligne) | ramener : part front d'US-0470/L1 |
  | #817.2a — exemple de succès d'un rattachement (`updateTaskFacet`) | US-0450 (fixtures du rattachement réécrites) | ramener : part contrat d'US-0450 (`task_attached`) |
  | #817.2b — exemple d'un refus à deux motifs | aucune US | garder en EP-16 |
  | #819.1 — focus d'une cellule refusée distingué par la seule couleur | aucune US (harnais #782) | garder en EP-16 |
  | #819.2 — `aria-invalid` posé pour tout échec | US-0470 (généralisation de `byField`, qui distingue un refus de la valeur d'un échec de transport) | ramener : avec #817.1 |
  | #819.3 — commande du squelette sans `key` par structure | US-0500 (la grille se monte par structure lue) | ramener : US-0500/L1 |
  | #819.4 — recherche sans résultat : squelette « indisponible » | US-0490 (le squelette s'offre dans l'encart et au lotissement) | partiel : la grille vide garde l'offre ; le reste EP-16 |
  | #819.5 — après un 409 du squelette, rien ne relit | US-0490 (l'encart relit sa condition au serveur) | ramener : US-0490 |
  | #819.6 — après la génération, l'en-tête dit « aucune tâche » | US-0490 (la réponse remplit la grille et l'en-tête) | ramener : US-0490 |
  | #819.7 — `structureVersion` facultatif | US-0500 (`grid-screen` lit la structure choisie, version exigée) | ramener : US-0500/L1 |
  | #819.8 — écriture en attente qui produit `{lock_version}` seul | US-0470 (écritures de `updateTaskFacet` généralisées) | ramener : US-0470/L1 |
  | #819.9 — exemple sur `/work_package_id` (lot déjà porté) | US-0450 (fixtures du rattachement) | ramener : part contrat d'US-0450 |
  | #819.10 — exemple de `WORK_BREAKDOWN_ITEMS_EXCLUSIVE` | US-0450 | ramener : part contrat d'US-0450 |
  | #819.11 — test « never both » incomplet | US-0450 (tests du rattachement réécrits) | ramener : US-0450 |
  | #819.12 — `bearing` modifie une réponse à la main | US-0450 (`skeleton_generated` réécrit) | ramener : US-0450 |
  | #819.13 — lotissement lu en série | aucune US | garder en EP-16 |
  | #819.14 — `waitForRequest(POST)` trop large | aucune US | garder en EP-16 |
  | #819.15 — largeur d'un commentaire | aucune US | garder en EP-16 |
  | #802 — la lecture du lotissement ne dit pas si un lot ou un poste est porté | US-0450 (le schéma `WorkBreakdownReading` est réécrit) ; US-0490 (l'encart et le squelette) | ramener : part contrat d'US-0450 (`attached_task`) |

  Décision : #817 et #819 restent en EP-16, réduites aux points gardés, les points ramenés nommés
  dans un commentaire à l'ouverture des issues ; #802 est ramenée en EP-15 entière, part contrat K1
  d'US-0450.
- **Les choix de l'échelle du Gantt** (US-0530/L2, #1393 ; décision de l'auteur du 2026-10-24 :
  tous acceptés, sauf les jours non travaillés) : les graduations sont de 0,5, 1,5, 6 et 24 pixels
  par jour, puis 20 par heure ; la semaine commence le lundi (ISO), quelle que soit la langue, et la
  rangée basse des semaines montre le jour du lundi, sans numéro de semaine ; un label trop serré
  est sauté (22 points en bas, 72 en haut) ; « Ajusté au projet » donne au dessin la largeur de la
  colonne, au plus fin niveau qui tient, un dézoom pouvant donner un dessin plus étroit ; la date
  gardée au zoom est celle du centre du cadre, pour la molette comme pour les boutons, non celle
  sous le pointeur ; le niveau est gardé dans `sessionStorage`, sous la clé `planning:<revision_id>` ;
  le fichier s'appelle `gantt/scale.ts`, `timeline` entrant en conflit avec `gantt/timeline.tsx` ;
  le bouton de pliage d'une récapitulative sortie du cadre par le défilement du temps est rogné
  mais reste dans l'ordre du clavier ; les trois boutons de zoom sont dans le coin épinglé de
  l'en-tête du Gantt, en `tabIndex=-1` (la treegrid n'a qu'un arrêt de tabulation, WF-IHM-0100),
  et le zoom passe au clavier par Ctrl et `+`/`-` et par le menu d'une cellule. `hours_per_day`, un
  `Decimal`, devient le nombre de graduations horaires par un calcul entier sur la chaîne décimale,
  jamais par un flottant : arrondi à l'heure entière la plus proche, la demi-heure vers le haut,
  minimum 1, maximum 24, sans demi-heures. **Contre le choix de L2**, qui ne dessinait pas les jours
  non travaillés faute de calendrier dans la lecture du planning, ils sont dessinés dans une couleur
  distincte (#1410) : K10 porte le calendrier de chaque tâche, US-0530/L5 la teinte et sa légende ;
  la frise n'est pas teintée (décision du 2026-10-24 : elle range des tâches de calendriers
  différents sur un axe commun, sans ligne par tâche). La conception d'origine disait « rien d'autre
  n'y change » au contrat pour US-0530, et rangeait #1064 parmi ce qui ne change pas : K10 la corrige.
- **Taille des lots** : comme EP-14, les lots sont coupés à 1 200 lignes estimées, et un lot
  d'écran qui approche le plafond se découpe plutôt que de grossir.
- **La branche du cadrage** est `roadmap/EP-15-cadrage`, vers `main` (autorisation de l'auteur du
  2026-10-18) : contrairement à EP-14, le statut `en cours`, les numéros d'issues et le ménage
  atteignent `main` à la fusion de la pull request de cadrage.

### La grille qui se modifie selon la phase

Le front ne déduit pas la phase (#1056, commentaire 2 ; WF-IHM-0090). Les gestes de structure et
la saisie des lignes ne sont pas refusés par le serveur selon la grille qui les envoie — une ligne
créée sur la structure principale d'un projet En cours est la même écriture depuis le devis et
depuis le reste à engager —, si bien que la lecture seule du devis est une règle de présentation
que le serveur doit dire. **Chaque structure liste ses commandes** : `CostStructure.available_commands`,
une liste de `StructureCommandAvailability` sur une énumération nouvelle `StructureCommand` —
`edit_planning`, `edit_estimate`, `edit_remaining` —, chacune gardée par la permission de la
révision correspondante (`planning.write`, `estimate.write`, `remaining.write`) et présente ou
absente comme elle. Sur la structure principale : `edit_estimate` est indisponible dès que le
projet est En cours, `project_before_in_progress` manquante — la condition existe déjà pour la
probabilité de gain — ; `edit_remaining` est indisponible tant qu'il ne l'est pas, condition
nouvelle `project_in_progress`. Sur un différentiel et sur le devis propre d'un risque :
`edit_estimate` et `edit_planning` sont disponibles quel que soit l'état du projet (WF-DEV-0050),
`edit_remaining` n'est jamais listée (WF-RAE-0040 : la seule principale). Les conditions d'état de
la révision — `revision_draft`, `no_background_task_running`, `project_not_terminal` — s'y
nomment comme sur la révision. Les grilles lisent la commande de la structure lue — `grid-screen.ts`
lit déjà `listCostStructures` — pour offrir ou non la saisie des cellules, les gestes de structure,
le collage et les sous-menus ; les commandes de la révision (`RevisionCommand`) restent ce qu'elles
sont et gardent ce qui ne lit pas une structure : le squelette, le marquage, les exports, les
risques. Écartés : la condition sur `RevisionCommand.edit_estimate`, qui aurait fermé le devis
propre d'un risque et le différentiel avec la principale ; des `editable_fields` vides, qui ne
disent rien de la création ni de la suppression ; lire `Project.state`, que le front ne déduit pas.

### Modifications du contrat, opération par opération

Dix parties, chacune avec ses exemples, son entrée dans `docs/api/DECISIONS.md` nommée ci-dessous,
`make lint-openapi`, `make inventory`, `make generate-client`, `make mock-data` et `make catalogs`,
faites **avant** le lot d'écran qui les consomme. Un exemple engendré se régénère ; un exemple écrit à
la main se réécrit et reste confronté par `test_mockuniverse.py`. Les noms des champs, des codes et
des conditions sont ceux que le cadrage propose ; chaque partie les arrête dans `DECISIONS.md`.

| Partie | Opérations | Changement | Faux back et `make mock-data` | Entrée de `DECISIONS.md` |
|---|---|---|---|---|
| K1 — le lotissement (#1054, #802, #817.2a, #819.9-10) | `getWorkBreakdown`, `setWorkBreakdown`, `generatePlanningSkeleton`, `listNodes`, `updateTaskFacet`, `createNode`, `moveNodes`, `getEstimateIndicators`, `openImport`, `previewPaste` | `WorkBreakdown` et `WorkBreakdownReading` portent `work_packages` au niveau 1, chaque `WorkPackage` ses `order_items`, chaque `OrderItem` ses `deliverables` ; `kinds` vaut `[work_package, order_item, deliverable]` ; les descriptions des opérations, des filtres `work_package_id` et `order_item_id`, de `EditableField` et de `NodeColumn.work_breakdown` suivent ; `WORK_PACKAGE_OUTSIDE_ORDER_ITEM` devient `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, `params.work_package_task` et `order_item_tasks` (refus de `updateTaskFacet`, `createNode`, `moveNodes`, `PasteRejection`, `ImportReport`) ; `EstimateIndicators.by_order_item` devient `by_work_package`, `order_item_without_task` → `work_package_without_task` ; `OrderItemReading` et `WorkPackageReading` gagnent `attached_task` — `{node_id, label}` ou nul —, la tâche de la révision en cours qui porte l'élément (#802) ; exemples ajoutés : `task_attached` (succès d'un rattachement), un refus sur `/work_package_id` (lot déjà porté), `WORK_BREAKDOWN_ITEMS_EXCLUSIVE` | les fixtures écrites à la main `work_breakdown*`, `skeleton_generated`, `task_attach_*`, `task_merge_outside_order_item`, `nodes_move_outside_order_item` sont réécrites ; `mockwitness` nomme « Lot 1 », « Poste 1.1 » ; `mockstructure`, `mocklists` (lotissement filtré, refus), `mockindicators.by_order_item` → `by_work_package`, `mocktoday` suivent ; `test_mockbreakdown.py`, `test_mocklists.py`, `test_mocktoday.py` réécrits ; les catalogues échangent chaque clé qui nomme un niveau (`enums.*`, `errors.*`, écrans) | « Le lotissement en lots, postes et livrables (EP-15/US-0450) », citant C-350 et le tableau du §4.4.1 |
| K2 — la structure lue, la phase et le diff (#1060, #624, #1056, #1066, #1065, #791) | `listCostStructures`, `listNodes`, `compareRevisions`, `updateEstimateLine`, `setNodeTracking`, `getStructureMergeReport` | `CostStructure.available_commands` (ci-dessus) ; `Node.difference` — `added`, `removed`, `modified`, `unchanged`, nul sur la principale — et `Node.changes` (l'énumération de `ComparedNode.changes`, `parent` compris) sur une lecture d'un différentiel, qui rend aussi les nœuds retirés à leur place, en lecture seule ; `RevisionComparison` rend `nodes`, l'arbre de la révision comparée dans l'ordre du plan avec `difference` et `changes` et les champs que `fields` nomme — comme `listNodes`, sans pagination —, à la place de `added`, `removed` et `changed` ; `amount_deltas` reste ; `EditableField` gagne `task.tracking`, que nomme toute tâche de la structure principale, récapitulative, feuille ou jalon, quel que soit l'appelant — `StructureCommand.edit_planning` porte la permission d'écrire (#1065) ; `updateEstimateLine` refuse par 422 `VALIDATION_FAILED`, `fields[].pointer` `/subproject_id` (le corps de `EstimateLineUpdate` est plat), code nouveau `SUBPROJECT_HAS_ACTUAL_COSTS`, `params.subproject` `{subproject_id, label}`, et une telle ligne ne nomme plus `estimate_line.subproject_id` dans `editable_fields` (#1066) ; réalisé par US-0500/L1 (part K2b) : `NodeDifference` et `NodeChange`, qui remplace `ComparedNode`, un nœud retiré occupant sa ligne et une tâche marquée modifiée par son seul contenu, `changes` vide, et `compareRevisions` prend `fields` (`NodeFields`, partagé avec `listNodes`) ; repris sur décision de l'auteur du 2026-10-20 (#1193), réalisé par US-0500/L5 : `compareRevisions` se lit comme `listNodes` — ses filtres, sa recherche et son tri, devenus des paramètres partagés, la structure rendue entière sans pagination ou par la fenêtre que ses filtres retiennent, et sa réponse, `items`, `totals` et `meta`, `items` à la place de `nodes` —, `amount_deltas` rendu dans chaque réponse, sur les lignes retenues comme `totals` ; tranché par l'auteur le 2026-10-20 (#1205), réalisé par US-0490/L1 : un filtre et un tri jugent un nœud retiré sur ses valeurs de base, comme tout autre nœud, et sans tri il reste à sa place, pour `listNodes` comme pour `compareRevisions` ; tranché par l'auteur le 2026-10-20 (#1208), réalisé par US-0500/L6 : `RevisionComparison.items` décrit ses nœuds par `ComparedNodeRead`, qui n'exige que `node_id`, `row_number`, `level`, `lock_version`, `difference` et `changes`, ses facettes `ComparedTaskFacet` et `ComparedEstimateLineFacet` n'exigeant rien, `Node` inchangé ; ajouté sur décision de l'auteur du 2026-10-19 (#1159) : `setNodeTracking` refuse le suivi temps/temps d'une tâche qui n'est pas un jalon par 422 `VALIDATION_FAILED`, `fields` sur `/entries/<n>/kind`, code nouveau `MILESTONE_REQUIRED` ; et (#1170) la description d'`ImportReport.rejected` | `mockwitness` et `mockhistory` décrivent l'avenant 2 « reprise des essais » comme différentiel non fusionné de la révision courante 102 (#791) : `structures` le porte, `structure_merge_report` devient une lecture du témoin, `nodes_amendment` (nouveau, `listNodes` sur le différentiel, marqué) et `comparison` (réécrit en arbre, 2 770 nœuds) sont engendrés — réalisé par US-0500/L1 : `wftools.mockamendment` et `wftools.mockdiff`, `comparison` rendant l'arbre entier, 5 999 nœuds dont 2 770 modifiés par leurs valeurs, `comparison_identical` engendré sur le cœur de l'offre — puis, par US-0500/L5 (#1193), `comparison` devenu la fenêtre de l'installation sur site (`subtree_of`, 9 nœuds) et `comparison_identical` dans la forme de `listNodes` —, et, par US-0500/L6 (#1201, point 2), `volume/comparison_volume` engendré, la comparaison de toute la structure lue avec `fields` (`kind`, `task.label`, `estimate_line.label`), 5 999 nœuds, 1,3 Mo, cité en deuxième —, l'ancien premier exemple de `getStructureMergeReport` gardé en variante déclarée, `structure_merge_report_started_task` ; `node_tracking_milestone_refused` engendré (#1159) ; l'import du devis du témoin (`import_analysed`, `imports` et les exemples qui le suivent) réécrit sur l'avenant 2, son résumé nommant le `structure_id`, ses lignes rejetées leur onglet (#1161, #1168), `test_mockuniverse.py` tenant qu'aucun ne vise la principale d'un projet En cours ; le résumé d'`import_remaining_subproject_held` (#1170) ; `structures` et `structures_*` disent leurs commandes ; `estimate_line_subproject_changed` et `estimate_line_subproject_has_actual_costs` écrits ; `nodes*` nomment `task.tracking` | « La structure lue, sa phase et son diff (EP-15/US-0460, US-0480, US-0500) », citant C-358, C-359, C-361 et #1067 ; « Le diff d'un différentiel, la comparaison en arbre, l'avenant 2 du témoin (EP-15/US-0500/L1) », citant C-361, #791, #1159, #1161, #1168 et #1170 ; « La comparaison de révisions se lit comme `listNodes` (EP-15/US-0500/L5) », citant #1193 ; « L'exemple de volume de la comparaison, et ses nœuds partiels (EP-15/US-0500/L6) », renvoyant à #166 et citant #1201 et #1208 ; #1205 dans « Du projet créé au projet En cours, et l'avenant (EP-15/US-0490, US-0510) » |
| K3 — les saisies de la structure (#1056, #1073, #1065, #788 saisies, #1152, #1153, #1162, #1164) | `createNode`, `moveNodes`, `deleteNode`, `updateTaskFacet`, `setPredecessors`, `setNodeTracking`, `previewPaste`, `openImport`, `getImport`, `applyImport` | exemples de succès qui manquent : `node_created` (tâche sœur), `node_created_child`, `estimate_line_created`, `nodes_moved` (une sélection), `nodes_indented`, et la suppression d'une récapitulative ; `updateTaskFacet` : `task_mode_changed`, `task_duration_entered`, `task_dates_entered` (manuelle), `task_description_entered`, et le 422 `COMPUTED_VALUE` d'une date automatique ; `setPredecessors` : le 422 `LINK_CYCLE` reçoit `params.cycle` (les tâches du cycle, `node_id` et `label`), `LINK_FORBIDDEN` celui d'une récapitulative et sa subordonnée, et `PROJECT_HORIZON_EXCEEDED` (`params.task`) s'étend aux saisies qui déplacent une date — `updateTaskFacet`, `setPredecessors`, `createNode`, `moveNodes` — (#788) ; exemples `predecessors_cycle_refused`, `predecessors_entered` ; `setNodeTracking` : `node_tracked`, `node_tracking_milestone_refused` (422, le suivi temps/temps d'une tâche qui n'est pas un jalon) ; `moveNodes` : 422 `LINK_FORBIDDEN` et `LINK_CYCLE` (`params.cycle`), pour un déplacement ou une mise en retrait qui relierait une récapitulative à l'une de ses subordonnées ou fermerait une boucle à travers elle (#1164 ; une création ne porte aucune liaison, `createNode` ne les déclare pas, #1167), exemples `nodes_indent_forbidden` (mise en retrait) et `nodes_move_cycle_refused` (déplacement) ; ajouté sur décision de l'auteur du 2026-10-19 (#1152, #1153) : le collage et l'import d'une cellule de sous-projet sur une ligne déjà portée — sa tâche démarrée ou terminée, son sous-projet chargé de coûts réels — sont rejetés par `SUBPROJECT_HAS_ACTUAL_COSTS`, `params.subproject`, comme `updateEstimateLine` (`PasteRejection`, `ImportRejection`), exemples `paste_plan_subproject_held` et `import_remaining_subproject_held` ; l'import du devis sur la structure principale d'un projet En cours est refusé par 409 `STATE_FORBIDS_OPERATION`, `project_before_in_progress` (C-358), exemple `import_estimate_main_in_progress` ; une ligne placée dans l'onglet d'un autre sous-projet est rejetée au compte rendu, qui nomme ce sous-projet (C-359, WF-INTF-0120), dans `import_remaining_subproject_held` ; `ImportRejection` gagne `sheet`, le nom de l'onglet tel que le fichier le porte, nul pour un fichier à un seul onglet (MS Project, extraction de coûts réels), que les exemples d'import Excel engendrés renseignent (#1162) ; les descriptions de ces opérations citent WF-INTF-0100 et WF-INTF-0120 ; ajouté sur décision de l'auteur du 2026-10-20 (#1183), par US-0460/L3b : `NodeCreate` et `NodeMove` désignent leur place par `after_node_id`, le nœud après lequel se placer parmi les frères sous le parent — nul en tête, absent en fin —, et n'écrivent plus `position` ; un `after_node_id` qui n'est pas un frère sous le parent visé est refusé par 422 `VALIDATION_FAILED`, `/after_node_id`, code nouveau `NODE_NOT_SIBLING`, exemples `node_create_after_not_sibling` et `nodes_move_after_not_sibling`, qui remplace `nodes_move_position_out_of_range` ; `Node.position`, en lecture seule, est le rang parmi les frères, à partir de 1 | `mockgestures` engendre les réponses comme les écritures existantes de `mockwrites` (différence de deux lectures du cœur), et les refus avec elles, leurs libellés pris aux lectures ; `mockdating.schedule` refuse la structure qu'un déplacement refusé laisserait ; `mockexchanges` juge le collage, l'import et le refus du devis sur les lectures du témoin et la structure principale listée ; `mockcore` compte `position` à partir de 1, les lignes d'une tâche puis ses subordonnées (#1183) | « Les gestes de structure et la saisie des tâches (EP-15/US-0460, US-0470, US-0480) », citant C-358, C-359, #1152 et #1153 ; « La place d'un nœud créé ou déplacé (EP-15/US-0460/L3b, #1183) » |
| K4 — le cycle des révisions et les avenants (#1074, #1072, #1061) | `createRevision`, `abandonRevision`, `designateReferenceRevision`, `applyRateUpdate`, `createCostStructure`, `mergeCostStructure` | exemples de succès qui manquent : `revision_created` (201), `reference_designated` (200), `rate_update_applied` (200), `amendment_created` (201), `task_merge_queued` (202) ; refus nommés : `designateReferenceRevision` 409 `reference_without_tasks` (`STATE_FORBIDS_OPERATION`, condition nouvelle `revision_has_tasks_and_lines`, WF-CYC-0030) et `reference_not_correctable` (`REFERENCE_NOT_CORRECTABLE`, WF-REV-0040) ; `createCostStructure` 409 `amendment_unmerged_exists` (`unmerged_amendment_exists`), retiré sur décision de l'auteur du 2026-10-20 (#1211) ; `mergeCostStructure` 412 `merge_report_stale` ; `applyRateUpdate` 409 `rate_update_revision_marked` (`revision_draft`) ; `abandonRevision` garde son 204 et son 409 ; réalisé par US-0490/L1 : la règle de #1195 levée sur décision de l'auteur du 2026-10-20 (#1211) — plusieurs avenants non fusionnés coexistent (WF-REV-0100), `create_structure` reste disponible sur la révision 102, la condition `no_unmerged_amendment`, le 409 `amendment_unmerged_exists` de `createCostStructure` et son exemple retirés, `unmerged_amendment_exists` restant la condition de `merge_structure` —, `REFERENCE_NOT_CORRECTABLE` sans paramètre, l'abandon hors de l'annulation (C-363) et la mise à jour refusée acceptée ensuite (C-362) dits aux descriptions ; ajouté sur décision de l'auteur du 2026-10-20 : `ImportDifference.fields` gagne `parent` (#1194) ; et les constats des gestes : la boucle d'un déplacement traverse la hiérarchie et une sélection nomme le premier nœud en cause (#1169), la règle du rang « hors nœuds déplacés » et l'exemple de requête d'une sélection mêlée (#1188), le 409 de `createNode` sur une tâche terminée (#1184) | écrits à la main dans la chronologie du témoin : la révision créée aujourd'hui sur le projet créé (103), la référence désignée sur l'offre en chiffrage, l'avenant 2 (#791) comme différentiel fusionnable ; `test_mockhistory.py` les date — réalisé par US-0490/L1 : la mise à jour des taux acceptée sur la 101 le 12 janvier à 10 h 15 (`mockwitness.RATES_UPDATED`), la 101 marquée à sa version 2, `amendment_created` l'avenant 2, ouvert pendant que l'avenant 1 l'est (#1211), `task_merge_queued` à 14 h 09, datés par `test_mockcycle.py`, `test_mockhistory.py` passant sinon les mille lignes ; `structure_merge_report` dit le déplacement de la mise en service (#1194) ; `wftools.mocktree` porte la règle du rang et les boucles ; `nodes_move_mixed` et `estimate_line_completed_refused` engendrés, le 412 de `deleteNode` sans exemple, inatteignable (#1184, #1210) ; `ELSEWHERE` réduit à `comparison` (#1196) | « Du projet créé au projet En cours, et l'avenant (EP-15/US-0490, US-0510) », citant C-362 et C-363, et #1169, #1184, #1188, #1194, #1195, #1196, #1205, #1210 et #1211 |
| K5 — les risques (#1062, #763, #786) | `createRisk`, `updateRisk`, `reviewRisk`, `deleteRisk`, `declareRiskOccurrence`, `getRisk`, `listRisks` | `RiskWrite.provision_task_id`, facultatif — nul, la première tâche de premier niveau —, changeable tant que le risque est identifié (`update_provision`), refusé par 422 `UNKNOWN_TASK` si la tâche n'est pas de la structure principale de la révision en cours ; `Risk` rend `provision_task` `{node_id, label}` (#786) ; exemples de succès : `risk_created` (201, avec sa structure propre et sa ligne de provision), `risk_updated` (200), `risk_reviewed` (201), `task_occurrence_queued` (202), et `risk_provision_task_refused` (422) ; réalisé par US-0520/L1 : `provision_task` nul pour un risque qui n'est pas identifié, sous un schéma nommé `ProvisionTask`, `provision_task_id` nul à la modification rendant la ligne à la première tâche de premier niveau ; ajouté sur décision de l'auteur du 2026-10-20 : `deleteNode` reçoit `lock_version` en paramètre de requête, le compteur du nœud supprimé, et son 412 a son exemple (#1210), une écriture qui déclare un 412 envoyant un compteur ; `estimate_line_created`, `estimate_line_created_after_subtask` et `nodes_moved` portent sur l'avenant 2, et `moveNodes` décrit son 409 vers une tâche terminée, `task_not_completed` (#1214) ; ajouté sur décision de l'auteur du 2026-10-21 (#1227), réalisé par US-0570/L1 : `moveNodes` refuse une ligne de provision par 422 `VALIDATION_FAILED`, `/node_ids/<n>`, motif nouveau `PROVISION_LINE_MOVED_BY_RISK`, `params.risk` renvoyant au formulaire du risque, et la description de `reviewRisk` dit la tâche de la ligne d'un risque écarté redevenu identifié | `risk_reviewed` engendré depuis le registre (`mockwitness.REGISTER`) comme les réexamens, sur 751 confirmé aujourd'hui ; `risk_created` et `risk_updated` engendrés d'un risque déclaré aujourd'hui, hors registre, 754, sa structure propre vide ; `risks`, `risk`, `risk_occurred_detail` nomment `provision_task` — réalisé par US-0520/L1 : les cinq exemples engendrés par `wftools.mockriskwrites`, `mockhistory` passant sinon les mille lignes, `task_occurrence_queued` sur la survenance de 752 ; les gestes du devis sur l'avenant 2, `nodes_move_completed_refused` et `node_delete_stale` (#1210), sur une ligne que `nodes_moved` a portée à sa version 2, par `wftools.mockamendmentwrites`, `mockgestures` passant sinon les mille lignes (#1214) ; le test du tri d'un nœud retiré lit le différentiel marqué par le tri du faux back, `mockcore.subtree(…, sort=…)` (#1216) ; par US-0570/L1 : `nodes_move_provision_refused` engendré par `wftools.mockriskwrites`, la ligne de 751 envoyée sous le « Montage des armoires sur site », et le résumé de `risk_created` ouvert par « Variante contrefactuelle » (#1228) | « La déclaration d'un risque désigne la tâche de sa provision, et les saisies du risque ont leurs exemples (EP-15/US-0520) », citant #763, #786, #1210, #1214 et #1216, puis #1227 et #1228 |
| K6 — le Kanban (#1070) | `listStartableTasks`, `setTaskProgress` | chaque tâche des trois colonnes est un `KanbanTask` — `Node` et `available_commands` sur une énumération `KanbanCommand` : `start`, `complete`, `reopen`, `enter_remaining`, chacune avec ses conditions manquantes (`task_without_lines`, `task_is_milestone`…) et, au-delà de cette conception, l'état qu'elle envoie (`KanbanCommandAvailability.progress`, justifié dans `DECISIONS.md`) — ; `NotStartedTask` garde `predecessors_completed` ; `ProgressUpdate.progress` accepte `not_started`, pour un jalon terminé seulement, refusé par 409 `STATE_FORBIDS_OPERATION`, `missing_condition` `completed_milestone`, pour toute autre tâche ; sa description (« aucun geste ne la ramène à “non démarrée” ») est réécrite ; exemples `task_started`, `milestone_completed`, `task_reopened`, `milestone_reopened`, `task_reopen_not_started_refused` | `startable_tasks*` engendrés par `mockkanban` disent les commandes et l'état que chacune envoie ; les réponses des gestes aussi, par `mockkanban`, sur les écritures du noyau de `mockwrites` | « Les gestes du Kanban (EP-15/US-0540) » |
| K7 — les graphiques (#1051, #1053) | `getPortfolioWorkload`, `getProjectRiskMatrix`, `getPortfolioRisks` | `PortfolioWorkload` gagne `capacity_monthly_hours` à la racine (la somme des rôles retenus, filtrés ou non) et `monthly_totals` — un total d'heures par mois de `months`, dans le même ordre — ; `RiskMatrix` gagne `points`, un par risque retenu : `risk_id`, `label`, `probability`, `severity_amount`, `severity_ratio`, `provision_amount`, `state`, `zone`, et pour le portefeuille `project_id`, `project_label`, `can_open` ; `cells` reste | `mockportfoliotime` somme la capacité et les totaux ; `mockhistory` (`risk_matrix`) et `mockportfolio` (`portfolio_risks`) placent les points depuis le registre ; `portfolio_workload*`, `risk_matrix`, `portfolio_risks` régénérés, la matrice du volume un point par ligne (`mockdata.render`) | « Le plan de charge agrégé porte sa capacité, la matrice ses points (EP-15/US-0550) », citant #375, #1051, #1053 et #1236 |
| K8 — les préférences et le référentiel (#1045, #1068, #1047, #1049) | `updateMyPreferences`, `getMe`, `listCalendars`, `setDurationUnits` | `GridPreferences.page_size`, entier parmi 10, 25, 50, 100, refusé hors de ces valeurs par 422 `VALUE_OUT_OF_RANGE` sur `/grids/<grille>/page_size` ; `DisplayPreferences.timelines`, une table par `timeline_id` (100 au plus) de `{lanes: {node_id: entier ≥ 0}}` (64 au plus), bornée comme `grids` ; les quatorze paramètres `monday_min` à `sunday_max` de `listCalendars` retirés avec `calendars_bounds_inverted` ; `setDurationUnits` : `duration_units_updated` (200), `duration_units_zero` (422, `fields` sur la constante), `duration_units_stale` (412) ; réalisé par US-0570/L1 : `page_size` refusé sans paramètre, quatre valeurs et non des bornes, le service disant `VALUE_OUT_OF_RANGE` pour tout entier hors d'une énumération d'entiers ; `TimelinePreferences`, `lanes` exigé, une chronologie à `null` retrouvant sa disposition automatique, un couloir négatif refusé par `VALUE_OUT_OF_RANGE`, `params.minimum` à `0` ; la constante nulle refusée par un motif nouveau, `DURATION_UNIT_NOT_POSITIVE`, sans paramètre, la borne étant exclue | fixtures écrites à la main : `preferences*` (dont `preferences_page_size_out_of_range`), `duration_units_*`, `calendars*` ; `test_mockbounds.py` tient les bornes — réalisé par US-0570/L1 : `preferences_page_size`, `preferences_timeline_lanes`, `preferences_page_size_out_of_range`, `preferences_lane_out_of_range`, `me_grid_settings` (25 lignes, le « Comité de pilotage » disposé : ses jalons, qu'une frise ne range pas, et, sur décision de l'auteur du 2026-10-24 (#1406), le couloir 2 d'une tâche, « Mise en service » `01926f3a-7c00-7000-8000-000000000565`, qui diffère de l'empilement automatique), `duration_units_updated`, `duration_units_zero`, `duration_units_stale`, `calendars_bounds_inverted` retiré ; les corrélations écrites à la main dans une plage nouvelle, 1300-1599 (#1228) ; le front n'envoie plus les bornes d'heures, la barre restant à US-0570/L3 | « Le nombre de lignes par page, la disposition d'une chronologie, les calendriers sans bornes d'heures, les unités de durée (EP-15/US-0530, US-0570) », citant C-351, C-352, C-360 |
| K9 — les refus des gestes selon la phase | `createNode`, `deleteNode`, `moveNodes` | aucun refus nouveau : la phase est une commande de la structure (K2), et le serveur accepte les mêmes écritures depuis les trois grilles ; la description de `createNode` dit qu'une tâche créée depuis le devis ou le reste à engager est une feuille automatique d'un jour sans prédécesseur (WF-DEV-0050), et qu'une ligne ajoutée après la référence a un montant budgété nul (WF-RAE-0050) | — | dans l'entrée de K2 |
| K10 — la date de calcul et le calendrier de la lecture du planning (#1404, #1406, #1410) | `listNodes`, `getMe` | `NodeListMeta.scheduled_at` (`Timestamp`, exigé) : l'instant du dernier calcul des dates de la structure lue — la dernière écriture qui l'a redatée, ou son import —, quels que soient les filtres, comme `summary_depth` (décision de l'auteur du 2026-10-24, #1404) ; écartée : la variante `CostStructure.scheduled_at`, la date étant un fait de la lecture du planning, et `NodeListMeta` disant déjà ce que la lecture dit de la structure lue ; le calendrier de chaque tâche (#1410, option A, décision du 2026-10-24) : un champ de `NodeFields` rend les `WeeklyHours` du calendrier applicable à la tâche (WF-PLA-0020 : le plus petit nombre d'heures, jour par jour, des calendriers des rôles de ses lignes de main-d'œuvre, le calendrier par défaut sans ligne) ; un jour chômé est un jour à 0 heure, le contrat ne connaissant pas de jours fériés (WF-REF-0110) ; écartée : les seules `WeeklyHours` du calendrier par défaut dans `NodeListMeta`, qui montreraient travaillé un jour que le rôle de la tâche ne travaille pas ; le nom du champ et le sort des récapitulatives sont arrêtés par le lot | `mockwitness` donne `scheduled_at` à toute lecture de nœuds (la date du témoin) et le générateur calcule le calendrier applicable depuis les lignes ; `nodes*` régénérés ; `me_grid_settings` reçoit le couloir de la tâche `…0565` (voir K8) ; `test_mocklists.py` confronte le calendrier | « La lecture du planning dit sa date de calcul et ses jours chômés (EP-15/US-0530) », citant #1404, #1406 et #1410 |

Ce qui ne change pas au contrat : #1058 (l'encart lit `generate_skeleton` et `import_planning`),
#1063 (le Gantt, la largeur dans `column_widths`), #1069 (le lien et sa base), #1052
(les cartes), #1043 (l'historique), #1050 (le menu), #1041, #1042, #1033, #1044, #1071 et #1075
(l'aide : la seule lecture nouvelle est celle des infobulles des valeurs calculées, par
`getComputedValueDependencies`, déjà servie).

### Le front

- **La sélection et les gestes de structure (US-0460)** : `DenseGrid` reçoit un modèle de sélection
  de lignes contiguës — colonne de poignée en tête, `aria-selected`, Maj+clic et Maj+flèches —, un
  glisser-déposer dont la cible est entre deux lignes ou sous une ligne, et des commandes de
  structure dans `CellMenu` et `screenCommands`, aux raccourcis de `grid-keyboard.ts` (Alt+Maj et
  les flèches). Les actions serveur `createNode`, `moveNodes`, `deleteNode` vont dans
  `src/api/actions/nodes.ts`, et leurs réponses passent par `answers.ts` (`NodesWritten` : les
  nœuds écrits, les ancêtres, `rescheduled`, `reinflated`, les totaux). La saisie des cellules de la
  tâche (US-0470) étend `planning-cells.tsx` avec les éditeurs du mode (choix), de la durée avec son
  suffixe (analyse dans `cell-values.ts`, deux langues) et des dates ; la colonne des prédécesseurs
  a son analyseur « 3FD+2 j ; 5DD » et son éditeur, et `setPredecessors` son action. `byField`
  (`planning-attachment.ts`) est généralisé dans `cell-writes.ts` pour que chaque refus nomme son
  champ et son motif (#817.1, #819.2). Les sous-menus « Chronologies » et « Sous-projet » (US-0480)
  sont deux instances d'un même sous-menu de `CellMenu` — cases à cocher ou boutons radio — qui
  s'applique à la sélection, un appel par ligne.
- **La structure lue (US-0500)** : `grid-screen.ts` lit la structure que l'adresse nomme
  (`structure=<id>`, la principale par défaut) parmi `listCostStructures`, sa version et ses
  commandes ; le bandeau (`context-banner.tsx`) la nomme et offre d'en changer ; une colonne
  `DiffMark` en tête de la grille dense rend `difference` par un caractère et une classe de couleur
  de ligne, avec ses variantes sombres ; l'écran de la comparaison (`revision-comparison.tsx`) passe
  à la grille dense sur `RevisionComparison.items`, lue comme `listNodes` (#1193).
- **Les révisions et les avenants (US-0490, US-0510)** : les commandes de la révision vont à côté
  de `mark-command.tsx` (`revision-commands.tsx`), chacune offerte comme la révision ou le projet la
  liste, avec sa confirmation ; le compte rendu de la fusion est un dialogue qui réemploie la lecture
  du compte rendu d'import (`ImportDifference`) et les marques de `DiffMark` ; la fusion confiée au
  worker est remise à `TaskTracker`. L'encart « Démarrer le projet » (`projects/project-start.tsx`)
  et la zone de dépôt (`exchanges/file-drop.tsx`) réemploient l'import de FBS-4.3.4.
- **Les risques (US-0520)** : un formulaire `risk-form.tsx` (créer, modifier), le réexamen et la
  suppression dans `risk-detail.tsx`, la survenance avec son compte rendu ; les règles de la
  provision sont celles de L42p (catégorie, sous-projet, `update_provision`), plus la tâche
  porteuse (#786).
- **Le Gantt et la frise (US-0530)** : `DenseGrid` reçoit l'épinglage à droite d'une colonne
  (`columnPinning.right`, `scrollPaddingInlineEnd`) et une poignée de séparation ; `gantt/scale.ts`
  (et non `gantt/timeline.ts`, que `gantt/timeline.tsx` rend ambigu) reçoit le modèle d'échelle à cinq niveaux et l'axe à deux rangées ; `gantt/timeline-chart.tsx`
  dessine la frise en SVG et écrit la disposition par `updateMyPreferences`.
- **Le Kanban (US-0540)** : `kanban/` reçoit la sélection des cartes, le glisser entre colonnes, le
  menu de la carte et l'action `setTaskProgress`.
- **Les graphiques et les cartes (US-0550)** : `components/figures-card.tsx` (tiré
  d'`IndicatorCard`), `workload-chart.tsx` empilé, `portfolio/workload-chart` avec la droite de
  capacité, `risks/risk-bubble-chart.tsx` partagé par le projet et le portefeuille ; l'export PNG
  passe par `components/chart/chart.tsx`.
- **Le cadre (US-0560)** : `dense-grid.tsx` (plancher, largeur de la barre), `shell/navigation.tsx`
  (les `leaves` en retrait), `tasks/task-tracker.tsx` étendu en panneau `Sheet` qui porte aussi
  l'historique des messages (`notices/message-history.ts` : un magasin de session, alimenté par
  `OutcomeNotice` et les avis de la grille, sans doubler l'annonce `role="alert"`).
- **Le référentiel et la pagination (US-0570)** : `grid/list-pages.tsx` reçoit « Lignes par
  page », `kept-address.ts` porte `limit` ; `reference/duration-units-form.tsx` et l'action
  `setDurationUnits` ; `resource-lists.tsx` perd la barre des bornes ; `reference/costs/page.tsx`
  empile.

### L'aide en ligne et les infobulles (US-0580)

- **Où vit le texte.** Les aides des écrans sont des fichiers Markdown, un par code de la FBS qui a
  un écran — fonction, feuille (`leaves`) ou section (`sections`) — et par langue :
  `frontend/help/fr/FBS-4.3.md`, `frontend/help/fr/FBS-4.3.1.md`… ; les notions de la méthode sous
  `frontend/help/fr/notions/<notion>.md` (révisions, budget de référence et valeurs EVM, reste à
  engager et devis actualisé, provision et réserve, avenant et différentiel, lotissement, chemin
  critique), reprises du glossaire de l'annexe A. La version anglaise, quand elle est décidée, vit
  sous `frontend/help/en/`. Écarté : les textes dans les catalogues `messages/*.json`, faits pour des
  libellés et non pour des pages ; MDX, qui compile du code dans un texte que l'auteur relit.
- **Comment il se relie aux écrans.** `functions.json` est la clé : le panneau d'aide
  (`shell/help-panel.tsx`, un `Sheet` ouvert par le bouton « Aide » de `page-header.tsx` ou par F1)
  lit le fichier du code de l'écran courant, côté serveur (`server-only`, lecture du répertoire au
  rendu), et le rend par `react-markdown` sans HTML brut (`skipHtml`) — une dépendance nouvelle,
  avec `remark-gfm` pour les tables, déclarée comme Vitest l'a été en EP-01. Les liens entre aides
  sont des liens relatifs vers un code ou une notion, que le panneau résout sans quitter l'écran ;
  la recherche porte sur les titres et les notions, côté client, sur un index des titres rendu avec
  le panneau. Un test (`help.test.ts`) parcourt `functions.json` et exige un fichier français par
  code ; il exigera l'anglais quand il sera décidé.
- **Comment il se relie aux infobulles.** Une seule source pour ce qui se lit aux deux endroits :
  les définitions des colonnes et l'aide d'une commande vivent dans les catalogues
  (`columns.<grille>.<colonne>.help`, `commands.<commande>.help`, dans les deux langues, tenus par
  `make catalogs`) ; l'en-tête d'une colonne les porte en infobulle (`CommandTooltip` sur
  `header-cell.tsx`), et la section « Ses colonnes » du panneau les rend depuis les mêmes clés, pas
  depuis le Markdown. Une valeur calculée dit de quoi elle dépend par
  `getComputedValueDependencies`, déjà lue par `computed-cell.tsx`. L'infobulle du montant corrigé
  de l'inflation nomme l'année de référence (`Revision.reference_year`) et le taux d'inflation du
  projet (`Project.inflation_rate`), que l'écran lit déjà. Écarté : des textes de colonnes dans le
  Markdown, qui auraient divergé des en-têtes.
- **Qui écrit, qui relit.** Le premier jet français est rédigé par l'agent du lot, à partir de la
  spécification, du code des écrans et des catalogues, dans la structure fixe de #1075 ; l'auteur le
  relit sur la pull request du lot — la mécanique et cinq écrans clés d'abord, puis les familles
  d'écrans, en EP-16 (US-0670, décision de l'auteur du 2026-10-25, #1445) —, et décide ensuite de
  la traduction. Le lot qui relit est celui qui livre le texte : sa pull request ne se fusionne
  qu'après la relecture de l'auteur, dite dans l'issue.

### Le croisement contrat-maquette

Les quatre-vingt-trois opérations d'écriture du contrat, chacune avec l'écran et le geste qui
l'appellent dans la maquette, ou l'US d'EP-15 qui l'ajoute. La table est la preuve de la définition
de fini : à la livraison, chaque ligne « US-nnnn » est devenue un geste, et seule la ligne de
l'écart reste.

| Opération | Écran et geste | Depuis |
|---|---|---|
| `createUser`, `updateUser`, `setUserActivation`, `anonymizeUser`, `setUserAccessRoles`, `createPasswordSetupLink`, `startIdentitySync` | Comptes (FBS-1.1) : créer, modifier, désactiver, anonymiser, attribuer les rôles, lien de mot de passe, lire les comptes du fournisseur | EP-03 |
| `createAccessRole`, `updateAccessRole`, `deleteAccessRole` | Rôles d'habilitation (FBS-1.2) : composer, modifier, supprimer | EP-03 |
| `startBackup`, `retainBackup`, `setBackupSchedule`, `testExternalBackupLocation`, `startRestore`, `openChunkedUpload`, `uploadChunk`, `completeChunkedUpload` | Sauvegardes (FBS-1.4) : sauvegarder, conserver, planifier, éprouver l'emplacement, restaurer, déposer une sauvegarde | EP-14, EP-03 |
| `closeMySessions`, `updateMyPreferences`, `putMyAvatar`, `deleteMyAvatar` | Compte personnel et préférences : se déconnecter, langue, thème, réglages de grille, avatar — `page_size` et `timelines` ajoutés par US-0570 et US-0530 | EP-02, EP-03 |
| `updateReferenceSettings` | Paramètres des risques et des indicateurs (FBS-3.3, FBS-3.4) | EP-14 |
| `createOrgNode`, `updateOrgNode`, `setOrgNodeActivation`, `createResourceRole`, `updateResourceRole`, `setResourceRoleActivation`, `createCalendar`, `updateCalendar`, `setDefaultCalendar`, `setCalendarActivation` | Paramètres de ressources (FBS-3.2) : créer, modifier, désactiver, calendrier par défaut | EP-02, EP-14 |
| `setDurationUnits` | Paramètres de ressources : « Modifier les unités de durée » | **US-0570** |
| `createCostType`, `updateCostType`, `setCostTypeActivation`, `createCostCategory`, `updateCostCategory`, `setCostCategoryActivation`, `setHourlyRate` | Paramètres de coûts (FBS-3.1) : natures, catégories, taux | EP-02, EP-14 |
| `createProject`, `updateProject`, `exitProject`, `setWorkBreakdown`, `createSubproject`, `updateSubproject`, `deleteSubproject`, `setContributors`, `createTimeline`, `deleteTimeline` | Projet (FBS-4.2, FBS-4.9, FBS-4.3.1) : créer, paramétrer, sortir du cycle, lotissement, sous-projets, contributeurs, chronologies | EP-14 |
| `uploadFile`, `openImport`, `abandonImport`, `applyImport`, `requestExport` | Imports et exports (FBS-4.3.4, FBS-4.4.3, FBS-4.5.1, FBS-4.7) ; l'encart de démarrage y mène aussi (US-0490) | EP-02 |
| `setActualCostTrackedScope` | Coûts réels (FBS-4.7) : exclure, réintégrer | EP-02 |
| `markRevision` | Révisions (FBS-4.1) : « Marquer » | EP-02 |
| `createRevision` | Révisions : « Ouvrir une révision en cours » | **US-0490** |
| `abandonRevision` | Révisions : « Abandonner la révision en cours » | **US-0490** |
| `designateReferenceRevision` | Révisions : « Désigner comme référence » | **US-0490** |
| `applyRateUpdate` | Révisions : « Appliquer la mise à jour des taux » | **US-0490** |
| `createCostStructure` | Révisions : « Préparer un avenant » | **US-0510** |
| `mergeCostStructure` | Révisions, grille d'un différentiel : « Contractualiser l'avenant » | **US-0510** |
| `createNode` | Planning, devis, reste à engager : « Insérer au-dessous », « Insérer une sous-tâche », « Insérer une ligne » | **US-0460** |
| `moveNodes` | Les trois grilles : indenter, désindenter, monter, descendre, glisser la sélection | **US-0460** |
| `deleteNode` | Les trois grilles : « Supprimer » | **US-0460** |
| `updateTaskFacet` | Planning : rattachement (EP-14) ; libellé, description, mode, durée, dates | EP-14, **US-0470** |
| `setPredecessors` | Planning : la colonne des prédécesseurs | **US-0470** |
| `setNodeTracking` | Planning : sous-menu « Chronologies » | **US-0480** |
| `updateEstimateLine` | Devis : les cellules de la ligne (EP-02) ; sous-menu « Sous-projet » au devis et au reste à engager | EP-02, **US-0480** |
| `setLineRemaining` | Reste à engager : les grandeurs réestimées | EP-02 |
| `setTaskProgress` | Kanban (FBS-4.5.3) : démarrer, terminer, rouvrir | **US-0540** |
| `previewPaste`, `applyPaste` | Les trois grilles : coller depuis un tableur | EP-02 |
| `generatePlanningSkeleton` | Planning vide (EP-14) ; encart de démarrage et lotissement : « Engendrer le planning » | EP-14, **US-0490** |
| `createRisk` | Risques (FBS-4.6) : « Identifier un risque » | **US-0520** |
| `updateRisk` | Détail d'un risque : « Modifier » | **US-0520** |
| `reviewRisk` | Détail d'un risque : « Réexaminer » | **US-0520** |
| `deleteRisk` | Détail d'un risque : « Supprimer le risque » | **US-0520** |
| `declareRiskOccurrence` | Détail d'un risque : « Déclarer survenu » | **US-0520** |
| `undoLastChange`, `redoLastUndo` | **Écart** : les commandes Annuler et Rétablir sont posées par EP-02 (US-0140) et visibles dans les trois grilles, mais ne sont pas branchées ; EP-06 les branche sur le service, qui seul rend l'état d'avant (#1056, point 4 ; #1057 ; décision de l'auteur du 2026-10-18) | EP-06 |

### Ordre de construction

1. Le cadrage : ce fichier, EP-16, le README, le ménage des EPIC voisins, les issues.
2. **US-0450**, le lotissement, part contrat K1 puis front, en premier : tout ce qui nomme un lot ou
   un poste en dépend.
3. Les parties de contrat **K2** et **K3** (la structure lue, la phase, le diff, les saisies), puis
   **US-0460** (trois lots), **US-0470** (deux lots), **US-0480**, **US-0500** (trois lots) — les
   gestes de structure et la structure lue, que les avenants et les risques réemploient.
4. **K4** puis **US-0490** et **US-0510** ; **K5** puis **US-0520** : le cycle des révisions, les
   avenants, les risques, dans cet ordre (#1074, #1061, #1062 reposent sur #1060 et #1056).
5. En parallèle du point 3, sans dépendance avec lui : **K8** puis **US-0570** ; **K7** puis
   **US-0550** ; **K6** puis **US-0540** ; **US-0560** ; **US-0530** (l'épinglage et le zoom
   d'abord, la frise après US-0480 pour les inscriptions), puis **K10** et les jours chômés
   (US-0530/L4, L5), puis les exports (L3b, L2b), qui reprennent la date de calcul et la teinte.
6. **US-0580**, l'aide et les infobulles, en dernier : elle décrit les écrans tels que les US
   précédentes les laissent. Ses lots de rédaction des autres écrans et la recherche sont passés à
   EP-16 (US-0670), qui les mène après les lots d'écran qu'ils décrivent (#1445).
7. La clôture : le croisement sans manque, la définition de fini constatée par l'auteur écran par
   écran, les issues soldées.
---

## US-0450 — Le lotissement en lots, postes et livrables

- **statut** : fini
- **exigences** : `WF-PRJ-0020-A`
- **opérations** : `getWorkBreakdown`, `setWorkBreakdown`, `generatePlanningSkeleton`,
  `updateTaskFacet`, `listNodes`, `getEstimateIndicators`
- **issue** : #1088

**En tant que** chef de projet, **je veux** que le lotissement nomme ses niveaux comme le bon de
commande — des lots, qui contiennent des postes, qui contiennent des livrables — dans le contrat,
dans les exemples et dans chaque écran, **afin de** saisir, rattacher et filtrer sans traduire dans
ma tête ce que l'application appelle poste et ce qu'elle appelle lot.

**Critères d'acceptation.**

- `WF-PRJ-0020-A` — « Un projet sans lotissement saisi présente un lot, un poste et aucun
  livrable. » : constaté contre le faux back, sur l'exemple du lotissement par défaut ; EP-04 le
  constate sur le service.
- `WF-PRJ-0020-A` — « Un poste peut être créé sans livrable. » : constaté dans la grille du
  lotissement (EP-14/L44c), avec les noms corrigés ; EP-04 le constate sur le service.
- propre à l'US : `WorkBreakdown` porte `work_packages` au niveau 1, chaque `WorkPackage` ses
  `order_items`, chaque `OrderItem` ses `deliverables` ; `kinds` vaut `[work_package, order_item,
  deliverable]` dans l'ordre des niveaux ; `WorkPackage` désigne toujours un lot et `OrderItem` un
  poste (#1054, décision 2) ; les refus qui nomment les niveaux, les filtres de `listNodes` par lot
  et par poste, les totaux par lot de WF-DEV-0060 et les descriptions des opérations suivent ;
- propre à l'US : les fixtures du lotissement, du squelette et du rattachement, les libellés du
  témoin (« Lot 1 », « Poste 1.1 »…) et les volumes sont régénérés par `make mock-data`, jamais à la
  main ; le client est régénéré (`make generate-client`) ;
- propre à l'US : chaque clé des deux catalogues qui nomme un niveau du lotissement s'échange ;
  « poste » au sens du poste de travail ou du poste qu'un rôle de ressource représente ne bouge pas ;
- propre à l'US : les écrans du lotissement (FBS-4.2.1), du squelette, du rattachement et les
  filtres du planning et du devis par lot et par poste disent les noms corrigés, et leurs tests DOM
  et e2e les affirment.

**Notes de réalisation.** La spécification corrigée (C-350) fait foi : « il découpe l'affaire en
lots, qui contiennent des postes, qui contiennent des livrables », et chaque règle reste attachée à
son niveau — « la suppression d'un lot emporte ses postes », « la tâche d'un poste se trouve dans le
sous-arbre de la tâche de son lot ». Le tableau du §4.4.1 dit « Lot, Poste, Livrable — work_package,
order_item, deliverable » : les identifiants gardent leur sens, leur imbrication s'inverse. Le total
par niveau de WF-DEV-0060 est celui des lots (niveau 1) : `EstimateIndicators.by_order_item` et le
motif `order_item_without_task` suivent le lot, et le code `WORK_PACKAGE_OUTSIDE_ORDER_ITEM` dit la
règle à l'endroit — la conception arrête les noms. Cette US passe la première : les autres lots de
structure en dépendent (#1054, « Ordre »). Le dernier critère est maintenu tel quel (décision de
l'auteur du 2026-10-19, #1148) : le front n'offrait aucun filtre par lot ni par poste, et
US-0450/L3 le réalise au-dessus des grilles du planning et du devis.

**Hors périmètre.** Toute règle nouvelle du lotissement, hors `attached_task` (#802), qui dit si un
lot ou un poste est porté par une tâche de la révision en cours.

## US-0460 — Construire la structure depuis les trois grilles

- **statut** : fini
- **exigences** : `WF-PLA-0080-A`, `WF-DEV-0050-A`, `WF-RAE-0040-A`
- **opérations** : `createNode`, `moveNodes`, `deleteNode`, `listNodes`, `getRevision`,
  `getProject`
- **issue** : #1091

**En tant que** chef de projet, **je veux** ajouter, indenter et désindenter, déplacer et supprimer
des tâches et des lignes depuis la grille de planning, depuis celle du devis tant que le projet
n'est pas En cours, et depuis celle du reste à engager ensuite, au clavier comme à la souris,
**afin de** construire et faire vivre la structure de la révision en cours dans la grille où je
travaille, sans changer d'écran.

**Critères d'acceptation.**

- `WF-PLA-0080-A` — « L’indentation d’un groupe de tâches déplace le groupe entier sous la tâche
  précédente. » : le geste envoie `moveNodes` avec la sélection et le parent de la précédente, et les
  lignes rendues prennent la place des lignes lues ; constaté contre le faux back, le report réel
  en EP-06.
- écart : `WF-PLA-0080-A` — « Chacune des colonnes citées est présente. » : constaté par EP-02
  (US-0220) et EP-14 (le rattachement) ; la colonne des prédécesseurs se saisit avec US-0470 ;
  EP-06 clôt.
- écart : `WF-PLA-0080-A` — « La recherche sur un libellé ne laisse voir que les tâches
  correspondantes et leurs parents. » : constaté par EP-02 ; EP-06 clôt.
- écart : `WF-PLA-0080-A` — « Les trois sortes de tâches se distinguent sans lire leur durée. » :
  constaté par EP-02 ; EP-06 clôt.
- écart : `WF-PLA-0080-A` — « Une tâche terminée se distingue d’une tâche démarrée sans lire de
  colonne ; une feuille ne porte pas d’avancement physique. » : constaté par EP-02 ; EP-06 clôt.
- écart : `WF-PLA-0080-A` — « Le filtre sur un poste ne laisse voir que la tâche qui le porte, son
  sous-arbre et ses parents. » : le filtre se choisit au-dessus de la grille parmi les lots et les
  postes du lotissement lu entier, et la grille relit `listNodes` avec `order_item_id` — avec
  `work_package_id` pour un lot —, que le contrat dit retenir le sous-arbre de la tâche rattachée et
  ses ancêtres (US-0450/L3) ; le contrat n'a aucun exemple de lecture filtrée par lot ou par poste,
  le faux back rend la structure entière, et ce que le serveur retient se constate contre le
  service ; EP-06 clôt.
- `WF-DEV-0050-A` — « La création d’une ligne sous une tâche terminée, ou le déplacement d’une
  ligne vers elle, est refusé. » : le refus est dit à la ligne en cause, sur l'exemple du faux back ;
  EP-07 le juge sur le service.
- `WF-DEV-0050-A` — « La grille de devis ne propose la saisie ni de la durée ni des prédécesseurs
  d’une tâche. »
- `WF-DEV-0050-A` — « Sur un projet En cours, la grille de devis de la structure principale ne
  propose aucune saisie ni aucune commande d’écriture ; celle d’une structure différentielle les
  propose. » : la lecture seule suit ce que le serveur dit de la grille lue (« Conception »), jamais
  une phase déduite par le front ; la structure différentielle se lit avec US-0500.
- écart : `WF-DEV-0050-A` — « La création d’une tâche depuis la grille de devis la fait apparaître
  dans la grille de planning, en mode automatique, d’une durée d’un jour et sans prédécesseur, et le
  déplacement d’un sous-arbre depuis l’une se répercute dans l’autre. » : le faux back ne garde
  rien ; le report d'une grille à l'autre se vérifie contre le service, en EP-06 (#1057).
- écart : `WF-DEV-0050-A` — « Le montant d’une récapitulative suit celui de ses subordonnées et
  n’est pas modifiable. » : constaté par EP-02 (US-0150) ; EP-07 clôt.
- écart : `WF-DEV-0050-A` — « La grille de devis ne présente pas le montant budgété ; une ligne
  dont la tâche se place deux ans après l’année de référence, avec une inflation de 2 %, affiche un
  montant réestimé supérieur de 4,04 % à son montant aux taux de l’année de référence. » : le calcul
  est du service — EP-07.
- `WF-RAE-0040-A` — « Sur un projet qui n’est pas En cours, la grille ne propose ni création ni
  suppression de tâche ou de ligne. »
- `WF-RAE-0040-A` — « Une ligne ajoutée après la référence peut y être portée à un sous-projet. » :
  par le menu contextuel d'US-0480, sur une ligne que le serveur dit saisissable.
- écart : `WF-RAE-0040-A` — « Une tâche ajoutée depuis la grille de reste à engager apparaît dans la
  grille de planning de la révision en cours, et une tâche ajoutée au planning d’un projet En cours
  apparaît dans la grille de reste à engager parmi les tâches non démarrées ; la révision de
  référence est inchangée, et le budget de référence comme la valeur planifiée ne bougent pas. » :
  le geste est branché ici et le parcours e2e ajoute une tâche depuis le reste à engager ; le report
  et l'invariance de la référence se constatent contre le service — EP-09.
- écart : `WF-RAE-0040-A` — « Les montants et les grandeurs sont présents pour chaque ligne, au
  reste à engager précédent et courant. » : constaté par EP-02 ; EP-09 clôt.
- écart : `WF-RAE-0040-A` — « La saisie d’une charge de 80 heures sur une ligne de quantité 1
  budgétée à 100 heures donne un montant réestimé de 80 fois le taux, projeté sur l’année de
  consommation de la ligne (WF-DEV-0030) ; le montant n’est pas saisissable. » : le calcul est du
  service — EP-09.
- écart : `WF-RAE-0040-A` — « Les tâches non démarrées n’apparaissent qu’à la demande, et sont alors
  modifiables. » : constaté par EP-02 ; EP-09 clôt.
- écart : `WF-RAE-0040-A` — « La modification d’une ligne portée par une tâche terminée est
  refusée. » : le refus est du service — EP-09.
- écart : `WF-RAE-0040-A` — « Une tâche démarrée dont la fin est dépassée est signalée ; sa date
  n’est pas modifiable depuis cette grille. » : constaté par EP-02 ; EP-09 clôt.
- écart : `WF-RAE-0040-A` — « La saisie d’un reste à engager nul sur toutes les lignes d’une tâche
  non démarrée la termine, avec une date de démarrage égale à sa date de terminaison. » : EP-09.
- propre à l'US : les commandes — « Insérer au-dessous », « Insérer une sous-tâche », « Insérer une
  ligne », « Indenter », « Désindenter », « Monter », « Descendre », « Supprimer » — sont au menu
  contextuel des cellules et ont un raccourci : Alt+Maj+→, Alt+Maj+←, Alt+Maj+↑, Alt+Maj+↓, comme
  MS Project ; une poignée en tête de ligne sélectionne une ou plusieurs lignes contiguës (clic,
  Maj+clic, Maj+flèches) et les glisse à une nouvelle place, avec un indicateur de dépôt ;
- propre à l'US : la suppression d'une récapitulative qui emporte ses subordonnées est confirmée ;
  chaque refus — tâche terminée, poste hors du sous-arbre de son lot, version périmée — est dit à la
  ligne en cause et inscrit dans l'historique des messages (US-0560) ;
- propre à l'US : les lignes rendues par la réponse prennent la place des lignes lues, avec leurs
  ancêtres recalculés, les tâches redatées et regonflées (`NodesWritten`) ;
- propre à l'US : la poignée a un nom accessible, se traverse au clavier, et le glisser a son
  équivalent au clavier (WF-IHM-0100).

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1056 et ses deux commentaires) :
les trois grilles partagent les mêmes commandes ; le planning les porte toujours ; le devis tant
que le projet n'est pas En cours (WF-CYC-0030), puis passe en lecture seule ; le reste à engager dès
que le projet est En cours. Le front ne déduit pas la phase : la conception dit comment le serveur
nomme la grille qui se modifie. Une tâche créée depuis le devis ou le reste à engager est une
feuille en mode automatique, d'un jour, sans prédécesseur (WF-DEV-0050). Annuler et Rétablir restent
posés sans être branchés (#1056, point 4 ; EP-06). L'US se découpe en trois lots : ajout et
suppression ; indentation ; sélection et déplacement.

## US-0470 — Saisir les tâches et leurs prédécesseurs dans la grille de planning

- **statut** : fini
- **exigences** : `WF-PLA-0020-A`, `WF-PLA-0030-A`, `WF-PLA-0160-A`
- **opérations** : `updateTaskFacet`, `setPredecessors`, `listNodes`
- **issue** : #1097

**En tant que** chef de projet, **je veux** saisir dans la grille de planning le libellé, la
description, le mode, la durée avec son unité, les dates d'une tâche manuelle et la liste des
prédécesseurs d'une tâche, comme dans MS Project, **afin de** construire un planning sans quitter
la grille ni la souris.

**Critères d'acceptation.**

- `WF-PLA-0020-A` — « Les dates d’une tâche en mode automatique ne sont pas saisissables. » : les
  cellules que le serveur dit calculées (`computed_fields`) sont traversées sans entrer en saisie.
- écart : `WF-PLA-0020-A` — « Le déplacement d’une tâche prédécesseur déplace ses successeurs en
  mode automatique et laisse inchangés ceux en mode manuel. » : les tâches redatées que la réponse
  rend (`rescheduled`) prennent la place des lignes lues, sur l'exemple du faux back ; le calcul est
  du service — EP-06.
- écart : `WF-PLA-0020-A` — « Une tâche en mode automatique sans prédécesseur commence à la date de
  début de planning ; avancer cette date d’une semaine l’avance d’autant, ainsi que ses successeurs
  automatiques. » : EP-06.
- écart : `WF-PLA-0020-A` — « Une tâche manuelle datée avant la fin calculée de son prédécesseur est
  signalée dans la grille et dans le Gantt, avec ce prédécesseur ; la retarder au-delà de cette fin,
  ou raccourcir le prédécesseur, fait disparaître le signalement. » : le signalement se lit (EP-02) ;
  son apparition et sa disparition sont du service — EP-06.
- `WF-PLA-0020-A` — « Sur un calendrier du lundi au vendredi, la date de début d’une tâche manuelle
  saisie un samedi est refusée, et le refus nomme le lundi suivant ; la même date importée d’un
  fichier MS Project est gardée et signalée au compte rendu. » : saisie — le refus est dit à la
  cellule et nomme le jour travaillé suivant, sur l'exemple du faux back (US-0470/L3, #1285, #1289)
  ; importée — EP-06.
- `WF-PLA-0030-A` — « Les quatre types et un décalage négatif sont importés, saisis et exportés
  sans perte. » : saisis — la colonne des prédécesseurs accepte « 3FD+2 j ; 5DD », les quatre types
  et un décalage négatif ou en pourcentage, analysés dans la langue de l'interface ; importés et
  exportés — EP-06.
- `WF-PLA-0030-A` — « La création d’une liaison fermant un cycle, ou reliant une récapitulative à
  l’une de ses subordonnées, est refusée, et la raison en est nommée à l’utilisateur. » : le refus
  est dit à la cellule, sur l'exemple du faux back, que la part « saisies » de #788, ramenée en
  EP-15, ajoute au contrat ; EP-06 le juge.
- écart : `WF-PLA-0030-A` — « Un décalage saisi en semaines ou en mois est conservé dans son
  unité, importé et exporté sans conversion. » : EP-06.
- écart : `WF-PLA-0030-A` — « Un décalage de 50 % sur un prédécesseur de dix jours vaut cinq jours
  de travail. » : le calcul est du service — EP-06.
- `WF-PLA-0160-A` — « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des
  langues de l’interface. » : l'analyse des suffixes au front, dans les deux langues.
- écart : `WF-PLA-0160-A` — « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize
  heures, « 1 sem » quarante heures et « 1 m » cent soixante heures. » : la durée s'envoie avec son
  unité ; la conversion est du service — EP-06.
- écart : `WF-PLA-0160-A` — « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer
  d’unité. » : EP-06.
- écart : `WF-PLA-0160-A` — « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur
  finit à la dernière heure travaillée d’un vendredi s’achève le dimanche ; le successeur, sur un
  calendrier du lundi au vendredi, commence le lundi à la première heure travaillée, de même qu’avec
  un décalage de 2 eh. » : EP-06.
- écart : `WF-PLA-0160-A` — « Un décalage de 2 j sur la même liaison le fait commencer le
  mercredi. » : EP-06.
- écart : `WF-PLA-0160-A` — « Un fichier MS Project dont les constantes diffèrent de celles de
  l’installation est importé avec les mêmes durées en heures, et le compte rendu signale la
  différence. » : EP-06.
- écart : `WF-PLA-0160-A` — « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j »
  dans une révision en cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision
  marquée, elle vaut toujours seize heures. » : le formulaire des unités (US-0570) le dit ; le
  recalcul est du service — EP-06.
- `WF-PLA-0160-A` — « En anglais, « 1 j » et « 1 d » valent chacun un jour ; « 3 », saisi sans
  suffixe, vaut trois jours. » : l'analyse des suffixes au front, ceux du catalogue de la langue
  courante compris (US-0470/L1, #1243).
- propre à l'US : les cellules saisissables — libellé, description, mode, durée avec son unité,
  début et fin d'une tâche manuelle — sont gardées par `editable_fields` et `edit_planning`, écrites
  par `updateTaskFacet`, au clavier seul (WF-IHM-0040) ; la validation de la dernière cellule place
  le curseur sur la ligne suivante ;
- propre à l'US : la colonne des prédécesseurs s'écrit par `setPredecessors` ; une ligne inconnue
  est refusée à la cellule ;
- propre à l'US : le Gantt suit les lignes écrites et redatées.

**Notes de réalisation.** Les codes des types de liaison dans la langue de l'interface — FD, DD,
FF, DF en français — sont ceux de l'énumération du contrat, traduits par les catalogues
(WF-INTF-0170). L'US se découpe en deux lots : les champs de la tâche, puis les prédécesseurs
(#1073).

## US-0480 — Inscrire une tâche à une chronologie, porter une ligne à un sous-projet

- **statut** : fini
- **exigences** : `WF-PLA-0060-A`, `WF-PRJ-0050-A`
- **opérations** : `setNodeTracking`, `listTimelines`, `createTimeline`, `updateEstimateLine`,
  `listSubprojects`, `listNodes`
- **issue** : #1100

**En tant que** chef de projet, **je veux** inscrire une tâche à une chronologie ou l'en retirer, et
porter une ligne de devis ou de reste à engager à un sous-projet ou l'en retirer, depuis le menu
contextuel de la ligne, pour une ligne ou pour la sélection, **afin de** composer mes chronologies
et ma ventilation par sous-projet sans quitter la grille.

**Critères d'acceptation.**

- `WF-PLA-0060-A` — « Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu’elle est
  retirée. » : le sous-menu « Chronologies » coche et décoche chaque chronologie du projet, envoie la
  liste complète des inscriptions (`setNodeTracking`), et la ligne rendue prend la place de la ligne
  lue ; l'apparition dans la chronologie se constate sur l'exemple du faux back, et contre le
  service en EP-06.
- écart : `WF-PLA-0060-A` — « Le diagramme temps/temps ne suit que les jalons inscrits. » : « Suivi
  temps/temps » se coche sur un jalon ; le diagramme est d'EP-10.
- `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d’une ligne d’une tâche démarrée, dont le
  sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d’une ligne d’une
  tâche non démarrée aboutit, comme celui de la ligne de provision d’un risque identifié. » : le
  refus (422, `SUBPROJECT_HAS_ACTUAL_COSTS`, qui nomme le sous-projet) et le succès ont leurs exemples
  au faux back ; la ligne de provision passe par le détail du risque (US-0520) ; EP-04 et EP-09
  jugent sur le service.
- écart : `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. » : constaté par EP-02 ;
  EP-04 clôt.
- écart : `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est
  refusée. » : constaté par EP-14/L44b ; EP-04 clôt.
- écart : `WF-PRJ-0050-A` — « La suppression d’un sous-projet portant des coûts réels est
  refusée. » : constaté par EP-14/L44b ; EP-04 clôt.
- écart : `WF-PRJ-0050-A` — « La suppression d’un sous-projet cité par une révision marquée est
  refusée. » : constaté par EP-14/L42l ; EP-04 clôt.
- écart : `WF-PRJ-0050-A` — « La suppression d’un sous-projet que porte une ligne de devis de la
  révision en cours est refusée ; elle aboutit une fois cette ligne passée à un autre
  sous-projet. » : la seconde moitié demande le service — EP-04.
- écart : `WF-PRJ-0050-A` — « La création d’un sous-projet de code « SP/01 », « Synthèse » ou de
  plus de trente et un caractères est refusée. » : la borne du code est au contrat et au service —
  #1304.
- propre à l'US : le sous-menu « Sous-projet » est exclusif (boutons radio) : « Aucun sous-projet »
  et chaque sous-projet du projet, celui de la ligne coché ; il n'est offert que si la ligne nomme
  `estimate_line.subproject_id` dans `editable_fields` — une ligne de provision ne l'offre pas ;
- propre à l'US : le choix s'applique à chaque ligne sélectionnée (US-0460), un appel par ligne avec
  sa version ; un refus est dit pour sa ligne ;
- propre à l'US : sans chronologie dans le projet, le sous-menu propose « Créer une chronologie… »
  (`createTimeline`) et y inscrit la tâche ;
- propre à l'US : une colonne « Chronologies » dans le planning et une colonne « Sous-projet » dans
  le devis et le reste à engager, masquées par défaut, en lecture, listent les inscriptions et le
  sous-projet par leur nom ; dans le devis, cela change le défaut actuel.

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1065, #1066 et leurs
commentaires) : le choix du sous-projet suit le partage d'US-0460 — le devis tant que le projet
n'est pas En cours, le reste à engager ensuite. La garde du sous-menu « Chronologies » doit venir du
serveur et non d'une déduction du front : la conception dit si `task.tracking` entre dans
`editable_fields` ou si une commande de la tâche le dit. Le refus `SUBPROJECT_HAS_ACTUAL_COSTS` et
la façon de ne pas l'offrir d'avance (champ calculé ou non saisissable sur une telle ligne) se
décident à la conception ; le service n'est pas concerné avant EP-04 et EP-09.

## US-0490 — Du projet créé au projet En cours

- **statut** : fini
- **exigences** : `WF-PRJ-0030-A`, `WF-REV-0010-A`, `WF-REV-0040-A`, `WF-CYC-0030-A`,
  `WF-REV-0060-A`
- **opérations** : `getProject`, `getRevision`, `listRevisions`, `createRevision`,
  `abandonRevision`, `designateReferenceRevision`, `getRateUpdateProposal`, `applyRateUpdate`,
  `generatePlanningSkeleton`, `getWorkBreakdown`, `uploadFile`, `openImport`, `getImport`,
  `applyImport`
- **issue** : #1106

**En tant que** chef de projet, **je veux** qu'après la création d'un projet un encart me propose
de démarrer son planning — le lotissement puis le squelette, ou un fichier MS Project déposé —, puis
ouvrir et abandonner une révision en cours, désigner la référence parmi les révisions marquées,
appliquer la mise à jour des taux, et voir le projet passer En cours, **afin que** la maquette
montre tout le cycle, de la création à la réalisation.

**Critères d'acceptation.**

- `WF-PRJ-0030-A` — « Elle n’est plus proposée dès que la structure principale comporte une tâche,
  et ne l’est jamais sur un différentiel ni sur le devis propre d’un risque. » : l'encart et le
  bouton « Engendrer le planning » suivent `generate_skeleton` comme la révision la liste, et
  ne s'offrent pas sur une structure différentielle lue (US-0500).
- `WF-PRJ-0030-A` — « Sur le lotissement par défaut, la génération produit une récapitulative de
  lot, une récapitulative de poste sans feuille, et leurs deux jalons de fin. » : l'exemple
  `skeleton_generated` du faux back, atteint depuis l'encart.
- écart : `WF-PRJ-0030-A` — « La génération sur un lotissement de deux lots et trois postes produit
  les récapitulatives, rattachées à leur lot ou à leur poste, les feuilles et les jalons attendus,
  avec leurs liaisons. » : EP-06.
- écart : `WF-PRJ-0030-A` — « Renommer un poste ensuite ne change aucune tâche ; le supprimer ne
  déplace ni ne supprime aucune tâche, et retire le seul rattachement de celle qui le portait
  (WF-PLA-0170). » : EP-06.
- `WF-REV-0010-A` — « La création d’une seconde révision en cours est refusée tant que la première
  n’est pas marquée. » : « Ouvrir une révision en cours » est offerte comme le projet la liste
  (`create_revision`), indisponible avec sa condition quand une révision est en cours.
- écart : `WF-REV-0010-A` — « Une révision créée à partir d’une révision marquée porte les mêmes
  tâches et les mêmes lignes ; à année de référence égale, elle porte aussi les mêmes valeurs de
  référentiel ; sinon, elle porte les mêmes rôles, calendriers et catégories, et, pour chaque
  catégorie dont la mise à jour de WF-REV-0060 n’a pas été acceptée, le taux précédent projeté par
  le taux d’inflation du projet jusqu’à la nouvelle année de référence. » : EP-04.
- écart : `WF-REV-0010-A` — « Après abandon d’une révision en cours, le projet présente les données
  de la dernière révision marquée, et une nouvelle révision peut être créée. » : la commande et sa
  confirmation sont branchées ; le retour à la dernière révision marquée est du service — EP-04.
- écart : `WF-REV-0010-A` — « L’abandon de l’unique révision d’un projet en chiffrage le laisse sans
  révision, à l’état Chiffrage, et la création d’une révision y est de nouveau proposée. » : EP-04.
- `WF-REV-0040-A` — « La désignation manuelle est proposée tant que le projet n’a ni coût réel ni
  révision marquée depuis la dernière désignation, et refusée au-delà. » : « Désigner comme
  référence » est offerte comme la révision marquée la liste (`designate_reference`), et le refus
  nomme la condition, sur les exemples du faux back.
- écart : `WF-REV-0040-A` — « Un projet dont les offres v2 puis v3 sont marquées, et dont v2 a été
  désignée par erreur, accepte la désignation de v3 tant qu’il n’a reçu aucun coût réel. » : EP-04.
- écart : `WF-REV-0040-A` — « Après contractualisation d’un avenant, la révision produite est la
  référence sans intervention de l’utilisateur, et l’ancienne reste consultable. » : le parcours de
  l'avenant est US-0510 ; la désignation automatique est du service — EP-08.
- `WF-CYC-0030-A` — « La désignation d’une révision marquée sans tâche, ou sans ligne de devis, est
  refusée et la condition manquante est nommée ; le projet n’a pas de référence. » : sur l'exemple
  de refus du faux back.
- écart : `WF-CYC-0030-A` — « Un projet dont la référence est désignée avant le code projet passe
  à En cours à la saisie du code ; un projet dont le code est saisi avant la désignation y passe à
  la désignation. » : l'en-tête, le bandeau et la lecture seule du devis suivent l'état que rend le
  serveur ; le passage lui-même est du service — EP-04 et EP-07.
- `WF-REV-0060-A` — « À sa création, lorsque la précédente portait 2026, l’écart est présenté
  catégorie par catégorie et la mise à jour peut être refusée. » : la proposition se lit (EP-02) et
  « Appliquer la mise à jour des taux » présente ce qui change puis l'applique (`applyRateUpdate`),
  offerte comme la révision la liste.
- écart : `WF-REV-0060-A` — « Une révision créée en 2027 porte l’année de référence 2027. » : EP-04.
- écart : `WF-REV-0060-A` — « Une catégorie refusée ou sans taux pour 2027 est chiffrée au taux de
  2026 corrigé d’une année d’inflation. » : EP-07.
- écart : `WF-REV-0060-A` — « Une révision créée en 2027 par un import de reste à engager porte les
  taux de 2026 projetés d’une année ; la mise à jour catégorie par catégorie reste proposée jusqu’à
  son marquage, et l’accepter pour une catégorie la rechiffre au taux de 2027. » : EP-07 et EP-09.
- écart : `WF-REV-0060-A` — « Une mise à jour refusée à la création d’une révision est acceptée
  ensuite depuis la révision en cours, qui est alors rechiffrée au taux de 2027 pour cette
  catégorie. » : la commande est offerte depuis la révision en cours ; le rechiffrage est du
  service — EP-07.
- propre à l'US : la page du projet porte l'encart « Démarrer le projet » tant que la structure
  principale de la révision en cours n'a aucune tâche, pour qui peut modifier le planning — et
  aussi dès la création du projet, sur un projet sans révision, où « Engendrer le planning » ouvre
  la révision puis engendre le squelette (décision de l'auteur du 2026-10-23, #1358, lot
  US-0490/L4) —, avec trois choix : « Planning automatique depuis le lotissement », qui mène à
  la saisie du lotissement et à « Engendrer le planning » ; « Importer un fichier MS Project »,
  une zone de dépôt accessible qui réemploie l'import de FBS-4.3.4 ; « Plus tard », qui replie
  l'encart pour la session ;
- propre à l'US : « Abandonner la révision en cours » demande une confirmation qui dit que le projet
  revient à sa dernière révision marquée, et qu'elle est irréversible (WF-IHM-0110) ; « Désigner
  comme référence » demande une confirmation qui dit ce que la désignation fixe — le budget de
  référence et la valeur planifiée — et qu'avec un code projet le projet passe En cours ;
- propre à l'US : un parcours e2e enchaîne, contre le faux back : marquer, désigner, saisir le code,
  voir l'état En cours, ouvrir une révision en cours, trouver le reste à engager saisissable.

**Notes de réalisation.** La spécification corrigée dit l'abandon hors de l'annulation (C-363,
WF-IHM-0110) et la mise à jour refusée acceptable ensuite (C-362, WF-REV-0060). L'encart lit sa
condition au serveur — la structure vide, et la révision qui liste `generate_skeleton` ou l'import
du planning, ou, sans révision, le projet qui liste `generate_skeleton` — et ne déduit rien (#1058,
#1358). Les libellés du lotissement sont ceux d'US-0450.

## US-0500 — Lire la structure choisie, voir un différentiel comme un diff

- **statut** : fini
- **exigences** : `WF-IHM-0020-A`, `WF-REV-0080-A`, `WF-REV-0100-A`
- **opérations** : `listCostStructures`, `listNodes`, `compareRevisions`, `listRevisions`
- **issue** : #1101

**En tant que** chef de projet, **je veux** ouvrir mes grilles de planning et de devis sur la
structure que je choisis — la principale, un différentiel d'avenant, le devis propre d'un risque —,
voir un différentiel marqué `+`, `-` et `M` par rapport à la principale, et comparer deux révisions
marquées dans la même grille avec les mêmes marques, **afin de** lire ce qui change là où je
travaille, sans table à plat.

**Critères d'acceptation.**

- `WF-IHM-0020-A` — « Chaque écran de données de projet nomme le projet et la révision affichée ;
  une grille ouverte sur une structure différentielle nomme cette structure. » : le bandeau du
  contexte de lecture dit la structure lue et offre d'en changer ; le projet et la révision sont
  constatés depuis EP-02 (US-0100).
- écart : `WF-IHM-0020-A` — « L'ouverture d'une révision marquée présente cet état et ne propose
  aucune commande de modification. » : constaté par EP-02 ; EP-08 clôt.
- écart : `WF-IHM-0020-A` — « Un indicateur affiché porte sa date de calcul. » : constaté par
  EP-02 ; EP-08 clôt.
- écart : `WF-IHM-0020-A` — « Un filtre actif est visible sans avoir à ouvrir le panneau de
  filtres. » : constaté par EP-02 ; EP-08 clôt.
- `WF-REV-0080-A` — « Une tâche déplacée sous une autre récapitulative est présentée modifiée. » :
  la marque `M`, que le serveur rend (`difference`, `changes` dont `parent`), sur l'exemple du faux
  back.
- écart : `WF-REV-0080-A` — « La comparaison d’une révision obtenue par fusion d’un différentiel
  avec la révision marquée qui la précède, lorsqu’aucune autre modification n’a été faite entre les
  deux, restitue exactement les tâches et les montants budgétés de ce différentiel. » : EP-07.
- écart : `WF-REV-0080-A` — « Les montants réestimés n’y diffèrent que par les lignes que le
  différentiel ajoute ou retire, par celles des tâches démarrées qu’il termine et par celles dont il
  change l’année de consommation ; une ligne existante dont le différentiel ne modifie que le
  montant budgété ne présente aucun écart de montant réestimé. » : EP-07.
- `WF-REV-0100-A` — « Deux structures différentielles coexistent dans une même révision, et la
  fusion de l'une laisse l'autre intacte. » : le choix de la structure liste chaque différentiel de
  la révision (`structures_amendments`) ; l'indépendance des fusions est du service — EP-08.
- écart : `WF-REV-0100-A` — « La première révision d'un projet comporte, à sa création, une
  structure principale et aucune autre ; une révision créée à partir d'une révision marquée en
  reprend toutes les structures, différentielles et propres des risques comprises (WF-REV-0010). » :
  EP-04.
- écart : `WF-REV-0100-A` — « Un risque déclaré ajoute une structure propre, présente dans chaque
  révision marquée postérieure. » : le devis propre s'ouvre depuis le risque (US-0520) ; la
  persistance dans chaque révision est du service — EP-08.
- propre à l'US : l'adresse des grilles de planning et de devis nomme la structure lue
  (`structure`), la principale par défaut ; les gestes d'US-0460 s'y appliquent comme à la
  principale ; le reste à engager ne lit que la principale (WF-RAE-0040) ;
- propre à l'US : sur un différentiel, chaque nœud porte la marque que le serveur rend — `+` vert
  pour un ajout, `-` rouge pour un retrait montré à sa place dans l'arbre, `M` jaune pour une
  récapitulative dont le contenu change et pour une tâche ou une ligne dont les valeurs changent
  (durée, dates, grandeurs, montants, parent) — dans une colonne de tête, doublée de la couleur,
  avec sa variante en mode sombre ; la marque ne repose jamais sur la seule couleur (WF-IHM-0100) ;
- propre à l'US : la comparaison de deux révisions (`/revisions?from_revision_id=…&to_revision_id=…`)
  emploie la grille dense et les mêmes marques, et tient les 2 770 nœuds du témoin sous la borne de
  15 s de `revisions.spec` (#624, #729) ;
- propre à l'US : le harnais d'accessibilité vérifie le contraste des trois couleurs, en clair et en
  sombre.

**Notes de réalisation.** Décision de l'auteur du 2026-10-18 (#1060 et son commentaire). Le front ne
calcule rien : `listNodes` sur un différentiel rend l'écart de chaque nœud avec la principale et les
nœuds retirés à leur place ; `compareRevisions` rend l'arbre comparé avec la même marque, paginé ou
fenêtré comme `listNodes` — la conception arrête la forme et l'entrée de `DECISIONS.md`. La
spécification corrigée (C-361) dit le contexte qui nomme la structure et la comparaison qui porte
les lignes et le parent. L'US se découpe en trois lots : le choix de la structure ; la marque du
diff ; la comparaison. Le témoin doit porter un différentiel dans sa révision courante pour que la
marque se voie sans variante (#791, ramené en EP-15).

## US-0510 — Préparer un avenant et le contractualiser

- **statut** : fini
- **exigences** : `WF-REV-0050-A`
- **opérations** : `createCostStructure`, `getStructureMergeReport`, `mergeCostStructure`,
  `listCostStructures`, `getRevision`, `listBackgroundTasks`, `getBackgroundTask`
- **issue** : #1110

**En tant que** chef de projet, **je veux** préparer un avenant depuis la révision en cours, y
ajouter et modifier des tâches et des lignes dans la grille, lire le compte rendu de sa fusion, lui
donner un nom de version et le contractualiser, **afin que** la maquette montre comment la
référence se déplace, et qu'EP-08 serve ce parcours tel qu'il est validé.

**Critères d'acceptation.**

- `WF-REV-0050-A` — « La fusion demande un nom de version, et la révision produite le porte. » :
  « Contractualiser l'avenant » demande le nom de version avant de confirmer ; la révision produite
  se constate sur le service — EP-08.
- `WF-REV-0050-A` — « Le compte rendu d’une fusion dont le différentiel retire une tâche démarrée
  nomme cette tâche comme terminée ; l’abandon à cette étape laisse la révision en cours et la
  référence inchangées. » : l'exemple `structure_merge_report` du faux back nomme les tâches
  démarrées qui seront terminées ; abandonner n'envoie rien.
- écart : `WF-REV-0050-A` — « Après fusion, la structure principale comporte les tâches ajoutées,
  les valeurs modifiées et plus aucune des tâches retirées. » : EP-08.
- écart : `WF-REV-0050-A` — « Les tâches inchangées conservent leur identité et leur état. » :
  EP-08.
- écart : `WF-REV-0050-A` — « Une tâche démarrée désignée comme retirée par un différentiel est
  conservée, son reste à engager est nul, et sa valeur acquise est inchangée après la fusion. » :
  EP-08.
- écart : `WF-REV-0050-A` — « Une ligne réestimée à 140 pour un montant budgété de 100, non désignée
  par le différentiel, porte toujours 100 et 140 après la fusion. » : EP-08.
- écart : `WF-REV-0050-A` — « Une ligne ajoutée en revue périodique, non désignée par le
  différentiel, garde un montant budgété nul. » : EP-08.
- écart : `WF-REV-0050-A` — « Après fusion, le projet ne comporte plus de révision en cours. » :
  EP-08.
- propre à l'US : « Préparer un avenant » est une commande de la révision en cours, offerte comme
  elle la liste (`create_structure`) ; elle demande un libellé, crée le différentiel et l'ouvre
  dans la grille de planning (US-0500), où les gestes d'US-0460 s'appliquent ;
- propre à l'US : « Contractualiser l'avenant » présente le compte rendu — les tâches et les lignes
  ajoutées, modifiées et retirées dans les marques `+`, `-`, `M` ; les tâches démarrées qui seront
  terminées ; les motifs de refus — puis demande le nom de version et confirme avec les deux
  compteurs lus ; une version périmée (412) propose de relire le compte rendu (WF-IHM-0110) ;
- propre à l'US : après la confirmation, la fusion est suivie dans « Tâches de fond » comme une
  sauvegarde (WF-IHM-0080), puis mène à la nouvelle référence.

**Notes de réalisation.** Décision de l'auteur du 2026-10-18 (#1061) : le parcours est montré pour
validation, le comportement réel reste à EP-08. Le compte rendu, ses compteurs et le 412 sont ceux
qu'EP-14/L42s a écrits au contrat (`DECISIONS.md`, « Le compte rendu préalable de la fusion »).

## US-0520 — Identifier un risque, chiffrer son devis propre, le réexaminer, le déclarer survenu

- **statut** : fini
- **exigences** : `WF-RIS-0010-A`, `WF-RIS-0020-A`, `WF-RIS-0030-A`
- **opérations** : `createRisk`, `updateRisk`, `reviewRisk`, `deleteRisk`,
  `declareRiskOccurrence`, `getRisk`, `listRisks`, `listRiskReviews`, `listCostStructures`,
  `listNodes`, `listCostCategories`, `listSubprojects`
- **issue** : #1111

**En tant que** chef de projet, **je veux** identifier un risque avec sa provision, chiffrer son
devis propre dans la grille de devis, le modifier, le réexaminer, le supprimer et le déclarer
survenu après avoir lu le compte rendu de la fusion, **afin que** la maquette montre tout le cycle
d'un risque, et qu'EP-08 le serve tel qu'il est validé.

**Critères d'acceptation.**

- `WF-RIS-0010-A` — « La confirmation d’un risque sans modification produit un réexamen daté. » :
  « Réexaminer » envoie la probabilité et l'état retenus (`reviewRisk`), et l'historique rendu
  porte le réexamen daté, sur l'exemple du faux back.
- `WF-RIS-0010-A` — « Avec deux catégories actives de type provision pour risques, la déclaration
  d’un risque demande laquelle porte sa provision, et la ventilation du devis présente la provision
  sous la nature de la catégorie choisie ; avec une seule, elle ne la demande pas. » : le formulaire
  demande la catégorie parmi les catégories actives de ce type, et ne la demande pas s'il n'y en a
  qu'une (EP-14/L42p) ; la ventilation est du service — EP-08.
- `WF-RIS-0010-A` — « Sans aucune catégorie active de ce type, la déclaration d’un risque est
  refusée et nomme la condition manquante. » : « Identifier un risque » est indisponible comme
  `declare_risk` le dit (`active_provision_category`), et le 409 est dit au formulaire.
- `WF-RIS-0010-A` — « Sur une révision sans tâche, la déclaration d’un risque est refusée, de même
  que le retour d’un risque écarté à l’état identifié ; l’une et l’autre aboutissent dès qu’une
  tâche existe. » : `at_least_one_task` rend la commande indisponible et le 409 est dit au
  formulaire (`risk_without_task`) ; le retour d'un risque écarté suit la même règle (C-354).
- écart : `WF-RIS-0010-A` — « Un risque déclaré sans désignation de tâche porte sa provision sur la
  première tâche de premier niveau ; la ligne peut être déplacée sur une autre tâche de la structure
  principale, et le total du devis est inchangé. » : la tâche porteuse se désigne au formulaire,
  facultative (#786, ramené en EP-15) ; le déplacement de la ligne et le total sont du service —
  EP-08.
- écart : `WF-RIS-0010-A` — « La gravité et le montant de la provision ne sont pas saisissables, et
  suivent toute modification de la structure propre ou de la probabilité. » : non saisissables,
  constaté par EP-02 (US-0230) ; le calcul est du service — EP-08.
- écart : `WF-RIS-0010-A` — « Les trois états sont atteignables, et un risque écarté ne pèse plus sur
  le devis. » : les trois états s'atteignent par le réexamen et la survenance ; le poids est du
  service — EP-08.
- écart : `WF-RIS-0010-A` — « La suppression de la tâche qui porte une provision de 40 laisse le
  devis inchangé, la provision étant passée sur la tâche parente. » : EP-08.
- écart : `WF-RIS-0010-A` — « Un risque écarté dont la catégorie a été désactivée redevient
  identifié avec la catégorie active choisie. » : le formulaire redemande la catégorie quand
  `provision_cost_category_is_active` est faux (C-261) ; EP-08 clôt.
- écart : `WF-RIS-0010-A` — « Sans catégorie active de ce type, son retour à l’état identifié est
  refusé et nomme la condition manquante. » : EP-08.
- écart : `WF-RIS-0010-A` — « Un risque déclaré sur le sous-projet S2 porte sa provision au reste à
  engager de S2 ; sans sous-projet désigné, elle compte hors sous-projet. » : le sous-projet se
  choisit au formulaire, facultatif ; le reste à engager est du service — EP-08 et EP-09.
- écart : `WF-RIS-0010-A` — « Un risque écarté qui redevient identifié porte sa provision sur la
  tâche qu’il désignait ; si cette tâche a été supprimée entre-temps, sur la première tâche de
  premier niveau. » : le contrat le dit de `reviewRisk` (US-0570/L1, #1237) ; le choix de la tâche
  est du service — EP-08.
- `WF-RIS-0020-A` — « Les transitions entre identifié et écarté sont possibles dans les deux
  sens. » : par « Réexaminer », l'état retenu parmi ceux que le risque liste.
- `WF-RIS-0020-A` — « Toute transition depuis l’état survenu est refusée. » : un risque survenu n'a
  plus de commande de saisie, comme il les liste (`risk_not_occurred`).
- `WF-RIS-0020-A` — « La suppression d’un risque cité par une révision marquée est refusée. » :
  « Supprimer le risque » est indisponible comme le risque le liste (`risk_not_cited`), et le refus
  a son exemple (`risk_delete_cited`).
- écart : `WF-RIS-0020-A` — « La revue périodique présente les risques dont la probabilité n’a pas
  été réexaminée. » : EP-08.
- écart : `WF-RIS-0020-A` — « Après abandon d’une révision en cours où un risque a été créé, un autre
  réexaminé et un troisième déclaré survenu, le premier n’existe plus, le second présente la
  probabilité et l’état de la dernière révision marquée, et le troisième est identifié, avec sa
  provision et sans coût à la survenance. » : EP-08.
- `WF-RIS-0030-A` — « La grille de devis d’un risque offre les mêmes opérations que celle du
  projet. » : le devis propre s'ouvre dans la grille de devis (US-0500) et y reçoit les gestes
  d'US-0460, quel que soit l'état du projet (WF-DEV-0050).
- écart : `WF-RIS-0030-A` — « La modification du devis propre d’un risque identifié ne change ni le
  budget de référence, ni la valeur planifiée, ni la valeur acquise, ni les indices de coût et de
  délai ; elle change la provision, donc le reste à engager, l’avancement financier et la projection
  du chef de projet (WF-RAE-0010). » : EP-08 et EP-10.
- propre à l'US : « Identifier un risque » est un formulaire — libellé, description, actions de
  mitigation, probabilité, catégorie et sous-projet de la provision — qui crée le risque
  (`createRisk`) puis ouvre son devis propre dans la grille de devis ; « Modifier » et
  « Réexaminer » se font depuis le détail du risque ; « Supprimer le risque » demande une
  confirmation ;
- écart : « Déclarer survenu » présente le compte rendu de la fusion du devis propre dans la
  principale, dans les marques `+`, `-`, `M` d'US-0500. : la lecture `getRiskOccurrenceReport` et le
  front de ce compte rendu sont d'EP-16 (#1383, US-0680), par décision de l'auteur du 2026-10-23 ;
  dans EP-15, la déclaration se fait par simple confirmation ;
- propre à l'US : « Déclarer survenu » dit le retrait de la provision du reste à engager, puis
  confirme ou abandonne ; un risque survenu n'est plus modifiable ;
- propre à l'US : les exemples de succès de `createRisk`, `updateRisk` et `reviewRisk` manquent au
  contrat (#763) et sont ajoutés avant les formulaires ; un parcours e2e enchaîne identifier,
  chiffrer, réexaminer, déclarer.

**Notes de réalisation.** Décision de l'auteur du 2026-10-18 (#1062, #763 et le complément de
l'analyse) : le parcours est montré pour validation ; la provision, la réserve et la fusion à la
survenance restent à EP-08. Les règles de la provision sont celles d'EP-14/L42p et L42s : la
catégorie parmi les catégories actives de type provision pour risques, le sous-projet facultatif,
`update_provision` tant que le risque est identifié, les refus `PROVISION_CATEGORY_REQUIRED`,
`INACTIVE_REFERENCE_OBJECT` et `active_provision_category`. `createRisk` crée la structure propre
avec le risque (« La création ouvre la structure de coûts propre du risque ») : `createCostStructure`
de nature `risk` ne sert pas à ce parcours — la conception le confirme. L'US se découpe en deux ou
trois lots : les formulaires et le devis propre ; le réexamen, la suppression et la survenance.

## US-0530 — Le Gantt épinglé et zoomé, la chronologie en frise

- **statut** : fini
- **exigences** : `WF-PLA-0090-A`, `WF-PLA-0140-A`
- **opérations** : `listNodes`, `listTimelines`, `getMe`, `updateMyPreferences`,
  `getDurationUnits`
- **issue** : #1131

**En tant que** chef de projet, **je veux** élargir le Gantt par-dessus les colonnes de la table
comme dans MS Project, le zoomer et le dézoomer sur une échelle de temps à deux rangées, et lire
chaque chronologie comme une frise à couloirs que je dispose moi-même, **afin de** lire un planning
de plusieurs années comme une tâche de quelques jours, et présenter une chronologie lisible.

**Critères d'acceptation.**

- `WF-PLA-0090-A` — « Aucune action de la souris ou du clavier ne modifie une tâche depuis le
  Gantt. » : la poignée de séparation, le zoom et le défilement du temps ne modifient aucune tâche.
- écart : `WF-PLA-0090-A` — « Les liaisons et la hiérarchie sont visibles, ainsi que le chemin
  critique. » : constaté par EP-02 (US-0220) ; le chemin critique est du service — EP-06.
- écart : `WF-PLA-0090-A` — « Une récapitulative pliée dans la grille l’est dans le Gantt, et
  réciproquement. » : constaté par EP-02/L40 ; EP-06 clôt.
- `WF-PLA-0140-A` — « L’export produit un fichier PNG de la chronologie affichée. » : l'export
  reprend la frise telle que l'utilisateur l'a disposée, avec le nom de la chronologie, le projet,
  la révision et la date de calcul (WF-IHM-0130).
- écart : `WF-PLA-0140-A` — « Deux chronologies d’un même projet portent des sélections distinctes
  et se retrouvent d’une session à l’autre. » : les sélections sont du service — EP-06 ; la
  disposition des couloirs, elle, se retrouve d'une session à l'autre par les préférences
  (`DisplayPreferences.timelines`), contre le service d'EP-03.
- propre à l'US : la colonne du Gantt est épinglée à droite, une poignée de séparation sur son bord
  gauche règle sa largeur — à la souris et au clavier, Maj et les flèches — entre un minimum et la
  largeur du cadre moins les colonnes épinglées en tête et la plus large colonne affichée entre
  les deux, pour qu'une cellule active recouverte puisse toujours se montrer (WCAG 2.4.11, #1389) ;
  les colonnes recouvertes restent
  atteignables par le défilement, les colonnes d'identification restent visibles (WF-IHM-0060), et
  la cellule active recouverte fait défiler la table pour se montrer ; la largeur est celle de la
  colonne `gantt` dans `GridPreferences.column_widths` ;
- propre à l'US : cinq niveaux d'échelle — années/trimestres, trimestres/mois, mois/semaines,
  semaines/jours, jours/heures travaillées —, les commandes « Zoom avant », « Zoom arrière »,
  « Ajuster au projet », Ctrl et `+`/`-` dans la grille, Ctrl et la molette sur le Gantt ; zoomé, le
  Gantt défile dans sa propre zone, l'axe avec les barres, la date du centre gardée ; le niveau est
  gardé pour la session, par grille et par révision, et le Gantt s'ouvre « Ajusté au projet » ;
  l'export PNG reprend toute l'étendue au niveau choisi ;
- propre à l'US : `TimelineChart` dessine, sur un axe qui suit l'échelle et le zoom, une tâche en
  rectangle qui contient son nom (tronqué, entier dans l'infobulle et le nom accessible) et un jalon
  en ligne verticale avec son nom et sa date ; les rectangles s'empilent en couloirs, par défaut
  automatiquement, et se déplacent d'un couloir à l'autre à la souris et au clavier (Alt+↑, Alt+↓) ;
  la disposition est une préférence d'affichage par chronologie (WF-ADM-0040) ;
- propre à l'US : le graphique et chaque rectangle ou jalon ont un nom accessible, et une lecture en
  table est donnée (WF-IHM-0100) ;
- propre à l'US : le Gantt teinte les jours chômés de chaque tâche — les jours à 0 heure du
  calendrier que la lecture du planning rend pour elle — d'une couleur distincte, que l'information
  ne porte pas par la seule couleur, avec une légende ; l'export PNG du Gantt (L2b) reprend la
  teinte et la légende ; la frise n'est pas teintée (décision de l'auteur du 2026-10-24, #1410).

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1063, #1064 et son commentaire,
#1068). Le contrat reçoit `DisplayPreferences.timelines` — une table par `timeline_id`, chaque
entrée portant le couloir de chaque tâche (`lanes`), bornée comme `grids` — avec ses exemples et son
entrée de `DECISIONS.md` ; rien d'autre n'y change. Le refus ou l'ouverture d'un couloir quand un
rectangle en chevaucherait un autre se tranche au lot (#1068). Trois lots : l'épinglage et la
poignée ; l'échelle et le zoom ; la frise. Ajoutés le 2026-10-24 (#1393, #1404, #1406, #1410) : un lot de contrat, `NodeListMeta.scheduled_at`, le couloir d'une tâche de `me_grid_settings` et le calendrier de chaque tâche (K10, L4), puis la teinte des jours chômés (L5), avant les exports (L3b, L2b), qui nomment la date de calcul de `scheduled_at`. Tranché par US-0530/L3 : le déplacement vers un couloir
où le rectangle en chevaucherait un autre est refusé, dit, et rien ne bouge ; aucun couloir ne
s'ouvre au-dessus d'un autre, un couloir vide s'offrant toujours sous le dernier, et le clavier vise
le plus proche couloir où le rectangle tient. Un jalon, ligne sur toute la hauteur, n'a pas de
couloir. L'export PNG de la frise est livré par US-0530/L3b, celui du Gantt par L2b. Réalisé par
L2b : l'image du Gantt a une ligne par tâche que la grille montre, une ligne sans tâche n'y
dessinant rien ; elle est deux fois plus dense que l'écran tant qu'un canevas le tient, aussi dense
sinon, et l'export est indisponible, son motif dit, au-delà des bornes des navigateurs ; une heure
travaillée se lit sur l'axe par son numéro dans le jour, le front ne connaissant pas l'heure où le
calendrier la place ; la date gardée au zoom est celle du centre du cadre qui défile dans l'en-tête,
non celui de la colonne.

## US-0540 — Les gestes du Kanban

- **statut** : fini
- **exigences** : `WF-RAE-0030-A`, `WF-IHM-0090-A`
- **opérations** : `listStartableTasks`, `setTaskProgress`
- **issue** : #1128

**En tant que** chef de projet, **je veux** sélectionner une carte du Kanban et la démarrer, la
terminer, la rouvrir ou la renvoyer à la saisie de son reste à engager, à la date que je saisis,
par glisser-déposer, par son menu ou au clavier, **afin de** tenir l'avancement de mes tâches depuis
la vue qui les répartit par état.

**Critères d'acceptation.**

- `WF-RAE-0030-A` — « Le passage direct de non démarrée à terminée n’est possible que pour un
  jalon, ou par la saisie d’un reste à engager nul sur toutes les lignes d’une tâche non démarrée
  (WF-RAE-0040) ; un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. » :
  « Terminer » n'est offerte que comme le serveur liste les commandes de la carte
  (`available_commands`), et demande la date de l'événement, celle du jour par défaut.
- `WF-RAE-0030-A` — « Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non
  démarré tant que personne ne le termine. » : la marque « prêt à terminer », par un texte et une
  icône (WF-IHM-0070), suit `predecessors_completed`.
- `WF-RAE-0030-A` — « Aucune commande ne fait passer une tâche démarrée à l’état non démarré. » :
  seul un jalon terminé liste « Rouvrir » vers non démarré, et le contrat refuse `not_started` à
  toute autre tâche.
- `WF-RAE-0030-A` — « Une tâche feuille démarrée sans ligne de devis est terminée depuis le
  Kanban. » : « Terminer » offerte comme le serveur la liste pour une telle tâche.
- écart : `WF-RAE-0030-A` — « Une tâche passée à l’état démarré voit ses lignes apparaître dans la
  grille de reste à engager. » : le report est du service — EP-09.
- écart : `WF-RAE-0030-A` — « Une tâche non démarrée n’y apparaît qu’à la demande. » : constaté par
  EP-02 ; EP-09 clôt.
- écart : `WF-RAE-0030-A` — « Un jalon terminé que l’on rouvre est non démarré et ne contribue plus à
  la valeur acquise. » : l'état est rendu par le serveur ; la valeur acquise est d'EP-09 et EP-10.
- `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée
  indisponible en nommant la condition manquante. » : sur la carte du Kanban, un geste que l'état
  de la tâche rend momentanément impossible est présenté indisponible avec la condition qui lui
  manque, comme le serveur la liste (`available_commands`), et un refus de l'API se dit sur la
  carte.
- écart : `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas
  cette commande. » : les permissions sont d'EP-02 et d'EP-14.
- écart : `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas
  contributeur nomme cette condition. » : les contributeurs sont d'EP-02 et d'EP-14.
- propre à l'US : une carte se sélectionne au clic ou au clavier, de carte en carte et de colonne en
  colonne ; les gestes se font par glisser-déposer entre colonnes, par un menu de la carte ou au
  clavier ; la réponse remplace la carte dans sa colonne ; un refus est dit sur la carte ; le focus
  suit la carte déplacée, et le glisser a son équivalent au clavier (WF-IHM-0100) ;
- propre à l'US : « Saisir le reste à engager » renvoie à la grille de reste à engager, sur ce jalon.

**Notes de réalisation.** Décision de l'auteur du 2026-10-18 (#1070). Le contrat change en deux
points : chaque tâche de `listStartableTasks` liste ses commandes disponibles (`start`, `complete`,
`reopen`, `enter_remaining`) avec la condition de celles qui manquent — le front ne les déduit pas
(WF-IHM-0090) —, et `ProgressUpdate.progress` accepte `not_started` pour un jalon terminé, refusé
pour toute autre tâche ; la décision va dans `DECISIONS.md`, et sa description actuelle (« aucun
geste ne la ramène à “non démarrée” ») est réécrite. Un parcours e2e reprend la Vérif : un jalon
sans ligne se termine à une date saisie.

## US-0550 — Les graphiques et les cartes de chiffres clés

- **statut** : fini
- **exigences** : `WF-DEV-0070-A`, `WF-PTF-0060-A`, `WF-RIS-0040-A`, `WF-IHM-0130-A`
- **opérations** : `getProjectWorkload`, `getPortfolioWorkload`, `getProjectRiskMatrix`,
  `getPortfolioRisks`, `getRiskCoverage`, `getEstimateIndicators`, `getRemainingIndicators`,
  `listActualCosts`, `getPortfolioProjects`, `getPortfolioValue`
- **issue** : #1123

**En tant que** chef de projet ou manager, **je veux** lire les plans de charge en histogramme
empilé par rôle — le plan agrégé avec sa capacité en pointillés et son filtre par nœud bien
visible —, les chiffres clés de chaque écran en cartes, la matrice des risques en graphique à bulles
pour un projet et pour le portefeuille, et atteindre le plan de charge depuis le reste à engager,
**afin de** lire d'un coup d'œil ce qui pèse, sans table pour le deviner.

**Critères d'acceptation.**

- `WF-DEV-0070-A` — « La capacité de chaque rôle est affichée. » : dans la table des valeurs sous
  l'histogramme du projet, qui reste sans droite de capacité (#375, option b).
- `WF-DEV-0070-A` — « Les trois bases sont proposées ; sur un projet sans révision de référence, la
  base de la référence est absente, et sur un projet sans aucune révision marquée, seule la
  révision en cours est proposée. » : constaté par EP-02 ; le lien « Plan de charge » du reste à
  engager ouvre `current_remaining`, celui du devis ouvre `reference_budget` en réalisation et
  `current_remaining` en chiffrage (#1069).
- écart : `WF-DEV-0070-A` — « La charge d’une ligne portée par une tâche qui couvre exactement deux
  mois civils apparaît sur ces deux mois, au prorata des heures travaillées de la tâche dans
  chacun. » : EP-07.
- écart : `WF-DEV-0070-A` — « Le filtre par nœud d’organisation ne laisse voir que les rôles qui en
  relèvent. » : l'exemple `workload_org_node` ; le filtre réel est du service — EP-07.
- écart : `WF-DEV-0070-A` — « Le plan de charge calculé sur le reste à engager ignore les lignes des
  tâches terminées. » : EP-09.
- écart : `WF-DEV-0070-A` — « Une tâche démarrée qui couvre exactement quatre mois civils, à
  mi-parcours à la date de calcul — le premier jour du troisième mois —, dont une ligne porte un
  reste de 80 heures, présente ces 80 heures sur les deux mois restants au prorata de leurs heures
  travaillées — 40 et 40 s’ils en comptent autant — et rien sur les mois écoulés ; sur une révision
  marquée, la date de calcul est sa date de marquage. » : EP-09.
- écart : `WF-DEV-0070-A` — « Une tâche non démarrée dont la date de début est antérieure à la date
  de calcul ne présente aucune charge sur les mois écoulés ; sa charge est la même avant et après
  son démarrage. » : EP-09.
- `WF-PTF-0060-A` — « Un mois à 120 % de la capacité est signalé. » : dans la table sous
  l'histogramme agrégé, qui garde la capacité, le taux de charge et les signaux par rôle ; la droite
  en pointillés porte la capacité du périmètre que le serveur rend.
- écart : `WF-PTF-0060-A` — « Sur deux projets en cours dont les restes à engager portent 100 et
  150 heures d’un même rôle le même mois, le plan agrégé porte 250 heures. » : EP-11.
- écart : `WF-PTF-0060-A` — « Une offre à 50 % avec 100 heures ajoute 50 heures quand le chiffrage
  est inclus, rien sinon. » : EP-11.
- `WF-RIS-0040-A` — « Les trois totaux — identifiés, survenus, écartés — sont distincts, et la
  réserve pour risques de la référence est affichée en regard. » : en cartes de chiffres clés —
  « Provisions », « Couverture des risques ».
- écart : `WF-RIS-0040-A` — « Les six colonnes sont présentes, ainsi que l’accès aux deux notes et à
  l’historique. » : constaté par EP-02 ; EP-08 clôt.
- écart : `WF-RIS-0040-A` — « Le tri par provision classe les risques du plus lourd au plus
  léger. » : EP-08.
- écart : `WF-RIS-0040-A` — « Un risque dont la probabilité augmente change de couleur conformément
  à la matrice. » : la bulle se place aux valeurs que le serveur rend ; le changement est du
  service — EP-08.
- `WF-IHM-0130-A` — « Le plan de charge d’un projet exporté est une image PNG qui porte le nom du
  projet, la révision et la date de calcul ; le plan de charge agrégé exporté porte le périmètre et
  la date de calcul. » : les deux histogrammes et les deux matrices s'exportent avec leur
  provenance — périmètre, nœud, horizon, date de calcul.
- écart : `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les projets de
  cet état dans ses totaux. » : EP-11.
- écart : `WF-IHM-0130-A` — « La table des calendriers ne propose aucun filtre sur les heures de ses
  jours ; elle se filtre sur ses autres colonnes. » : US-0570.
- propre à l'US : chaque série du plan de charge est empilée (une barre par mois, divisée par rôle,
  les motifs gardés pour distinguer sans la couleur, WF-IHM-0100), l'infobulle d'un mois liste les
  rôles et leurs heures, le total de chaque mois étiquette le sommet de la barre ;
- propre à l'US : un composant commun de cartes — titre, date de calcul, liste de libellés et de
  valeurs qui garde son sens pour les lecteurs d'écran — remplace les chiffres en ligne des six
  écrans (risques, devis, reste à engager, coûts réels, portefeuille vues et valeur) ;
  `IndicatorCard` le réemploie, et la règle est écrite dans le guide ;
- propre à l'US : la matrice est un nuage de bulles — probabilité en abscisse, gravité en pourcentage
  de l'assiette en ordonnée, chaque bulle à ses valeurs exactes, sa taille suivant la gravité en
  montant, sur le fond des seize cases colorées par zone —, intitulée « Matrice des risques », sur
  toute la largeur entre les cartes et la grille du projet, et à la place du tableau du
  portefeuille ; les bulles sont les risques du filtre d'état de l'écran ; une infobulle par bulle,
  un clic qui mène au détail ; le décompte par case reste lisible dans une table sous le graphique ;
  les zones se distinguent sans leur couleur (WF-IHM-0100) ;
- propre à l'US : la matrice des risques d'un projet retrouve son état replié ou déplié d'une session
  à l'autre, une seule préférence (`charts.risk_matrix`) pour tous les projets ; elle démarre repliée
  sans préférence, un clic l'écrit sans attendre la réponse, et un refus du service se dit.

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1051, #1052, #1053, #1069 et leurs
commentaires). Le contrat change : `PortfolioWorkload` reçoit la capacité du périmètre et le total
de chaque mois ; `RiskMatrix` reçoit un point par risque retenu (`risk_id`, `label`, `probability`,
la gravité en montant et en pourcentage, `provision`, `state`, `zone`, et pour le portefeuille
`project_id`, `project_label`), `cells` restant ; le front ne calcule rien. Chaque changement a ses
exemples, le faux back régénéré et son entrée de `DECISIONS.md`. Sur les écrans remplis, la hauteur
des cartes au-dessus de la grille se vérifie avec US-0560.

## US-0560 — Le cadre de l'application : grilles, historique des messages, menu

- **statut** : fini
- **exigences** : `WF-IHM-0080-A`, `WF-OBS-0020-A`
- **opérations** : `listBackgroundTasks`, `getBackgroundTask`
- **issue** : #1119

**En tant que** chef de projet, **je veux** que la barre et le bouton « Colonnes » d'une grille se
placent au bord de la table, qu'une grille courte n'ait pas de bande vide ni ne déborde sur un écran
rempli, que le menu latéral montre les sous-fonctions qui ont un écran, et relire dans un historique
central les refus et les succès de mes commandes, **afin de** retrouver un message fermé ou laissé
derrière moi, et de ne plus chercher le plan de charge.

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « Un utilisateur qui change d’écran pendant un import est informé de son
  aboutissement. » : l'historique des messages, qui étend « Tâches de fond », garde l'issue de
  chaque commande — succès comme refus — avec l'heure, l'écran, l'objet, la phrase de l'avis et un
  lien qui ramène à l'écran ; constaté contre le faux back, l'import réel en EP-04.
- écart : `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran
  utilisable et présente son avancement. » : EP-04.
- écart : `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même
  traitement peut être relancé. » : constaté par EP-02 (US-0180) ; EP-04 clôt.
- `WF-OBS-0020-A` — « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par
  un seul identifiant, que le message présenté à l'utilisateur contient. » : une erreur inattendue
  garde sa référence de corrélation dans l'historique ; la chaîne complète est d'EP-13.
- écart : `WF-OBS-0020-A` — « Une recherche des secrets et des jetons connus dans les journaux ne
  les trouve pas. » : EP-13.
- propre à l'US : le plancher du cadre d'une grille dense ne dépasse jamais la hauteur de son
  contenu (`min(10rem, 2 × EDGE_REM + max(lignes, 1) × ROW_REM)`), et, sur un écran rempli, remonte
  la chaîne des `min-h-0` ou la règle du guide dit qu'un écran qui a du contenu sous sa grille ne
  remplit pas la fenêtre (#1033, #1041) ; les autres écrans remplis sont vérifiés ;
- propre à l'US : la barre et le bouton « Colonnes » suivent la largeur de la table ; les avis
  (`OutcomeNotice`, `PasteAppliedNotice`, `UnshownNotice`, le problème de saisie) restent sur place et
  sur toute la largeur ; le harnais passe aux deux largeurs ;
- propre à l'US : sur place, rien ne change — le refus reste à la cellule, au champ ou sous le
  formulaire, annoncé aussitôt ; l'historique est un panneau latéral (`Sheet`) propre à la session
  de navigation, effacé à la déconnexion, sans opération du contrat ; un badge dit le nombre de
  refus non lus ; les succès qui ne se voient pas à l'écran reçoivent une courte confirmation sur
  place, gardée aussi dans l'historique ; le panneau est accessible — focus, Échap, titre ;
- propre à l'US : le menu latéral montre chaque sous-fonction qui a un écran, en retrait sous sa
  fonction parente, avec la garde de la sous-fonction ; le lien courant est marqué sur la
  sous-fonction et sa parente se montre comme le chemin ; repliée en icônes, la barre ne montre que
  la parente, marquée courante quand la page est l'une de ses sous-fonctions ; chaque `leaf` est
  atteignable depuis le menu, et le harnais `tab-walk` passe.

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1041, #1042 et son commentaire,
#1043, #1050 et son commentaire). L'historique n'est pas le journal d'audit (WF-SEC-0030) : aide à
l'utilisateur, éphémère, pour lui seul. Si les filtres de la liste (`ListBody`) suivent la largeur de
la table se décide au lot (#1042). L'historique des messages est une décision de conception, sans
exigence WF-IHM nouvelle (décision de l'auteur au cadrage, 2026-10-18, réponse 9).

## US-0570 — Le référentiel et les grilles paginées

- **statut** : fini
- **exigences** : `WF-IHM-0060-A`, `WF-IHM-0130-A`
- **opérations** : `listCalendars`, `getDurationUnits`, `setDurationUnits`, `getMe`,
  `updateMyPreferences`, `listUsers`, `listAccessRoles`, `listBackups`, `listAuditEvents`,
  `listOrgNodes`, `listResourceRoles`, `listCostTypes`, `listCostCategories`, `listHourlyRates`,
  `listProjects`, `listSubprojects`, `listRisks`, `listActualCosts`, `listCostImports`,
  `listImports`
- **issue** : #1115

**En tant qu'** administrateur ou chef de projet, **je veux** choisir le nombre de lignes par page
de chaque table et le retrouver, lire les paramètres de coûts en grilles empilées, une table des
calendriers sans filtre sur les heures de ses jours, et modifier les unités de durée depuis les
paramètres de ressources, **afin d'**ajuster chaque table à mon écran et de régler l'installation
sans quitter l'écran qui la montre.

**Critères d'acceptation.**

- `WF-IHM-0060-A` — « Le nombre de lignes par page choisi pour une table est retrouvé à sa
  réouverture, sans changer celui des autres tables ; une grille arborescente n’offre pas ce
  choix. » : « Lignes par page » — 10, 25, 50 ou 100, 50 par défaut — à côté de la pagination de
  chaque table plate, porté par l'adresse, qui revient à la première page, envoyé en `limit` à
  chaque lecture et écrit dans `GridPreferences.page_size` de la grille ; une grille arborescente ne
  l'offre pas ; la réouverture le retrouve contre le service des préférences d'EP-03, et EP-07
  clôt.
- écart : `WF-IHM-0060-A` — « Chaque colonne d’une table plate se trie dans les deux sens. » :
  constaté par EP-02 et EP-03 ; EP-07 clôt.
- écart : `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose de
  tri ; dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans
  déplacer les tâches. » : constaté par EP-02 pour le planning ; le devis trié est d'EP-07.
- écart : `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours
  visibles, de même que la colonne de libellé après défilement horizontal. » : constaté par EP-02 ;
  EP-07 clôt.
- écart : `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la
  réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. » :
  constaté par EP-03 (US-0400) ; EP-07 clôt.
- `WF-IHM-0130-A` — « La table des calendriers ne propose aucun filtre sur les heures de ses
  jours ; elle se filtre sur ses autres colonnes. » : la barre de bornes des sept jours est retirée
  de la liste et les quatorze paramètres de `listCalendars` du contrat ; la recherche et le filtre
  d'état restent.
- écart : `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les projets de
  cet état dans ses totaux. » : EP-11.
- écart : `WF-IHM-0130-A` — « Le plan de charge d’un projet exporté est une image PNG qui porte le
  nom du projet, la révision et la date de calcul ; le plan de charge agrégé exporté porte le
  périmètre et la date de calcul. » : US-0550.
- propre à l'US : `/reference/costs` empile ses grilles comme `/reference/resources` — natures,
  catégories, puis paramètres de coûts avec leurs filtres —, dans une page qui défile, chaque grille
  plafonnée à la fenêtre ; l'ordre des sections est tenu par le test de la page et l'e2e
  d'accessibilité aux deux largeurs ;
- propre à l'US : « Modifier les unités de durée », offerte à qui porte la permission des
  paramètres de ressources (WF-IHM-0090), ouvre un formulaire des trois constantes en décimaux de la
  langue ; le refus est dit au champ (422), la version périmée propose de relire (412), la réponse
  prend la place des valeurs lues ; sous les champs : « Le changement vaut pour tous les projets :
  les plannings des révisions en cours sont recalculés ; une révision marquée garde les heures
  qu'elle a calculées. » (WF-PLA-0160, WF-REF-0130).

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1044, #1045 et ses commentaires,
#1047, #1049 et son commentaire). Le contrat change : `GridPreferences.page_size` parmi 10, 25, 50
et 100, une autre valeur refusée par 422 `VALUE_OUT_OF_RANGE` ; les quatorze paramètres `*_min` et
`*_max` de `listCalendars` retirés avec leurs exemples et `calendars_bounds_inverted` ; les
exemples manquants de `setDurationUnits` — succès, constante nulle (422), version périmée (412).
US-0110, US-0400 (préférences), US-0240 et US-0360 (calendriers) portent déjà ces phrases en écart
vers #1045 et #1047.
Les deux journaux d'imports (décision #1267) offrent aussi « Lignes par page » : le journal des
coûts réels sous la clé de grille `cost_imports` et l'adresse `imports_limit`, les imports du projet
sous la clé `imports` et l'adresse `limit` ; la taille est gardée par grille, l'une sans changer
l'autre, et leur taille par défaut passe à 50.

## US-0580 — L'aide en ligne et les infobulles

- **statut** : fini
- **exigences** : `WF-IHM-0140-A`
- **opérations** : `getComputedValueDependencies`, `getRevision`, `getProject`
- **issue** : #1135

**En tant que** chef de projet, **je veux** ouvrir sur chaque écran une aide qui dit ce qu'il
montre, ses commandes et leurs conditions, ses colonnes et ses valeurs calculées, les gestes au
clavier et les notions de la méthode, et lire sur chaque bouton une infobulle qui dit son raccourci
et ce qu'il fait, **afin de** me servir de Waterfall sans manuel ni formation.

**Critères d'acceptation.**

- `WF-IHM-0140-A` — « Chaque écran ouvre une aide qui le concerne. » : un bouton « Aide » dans
  l'en-tête de chaque écran, ou F1, ouvre un panneau latéral (`Sheet`) qui rend le fichier Markdown
  du code FBS de l'écran ; un test vérifie que chaque code de la FBS qui a un écran a son aide en
  français, ou la nomme dans la liste des pages à venir avec le lot d'EP-16 qui l'écrit (US-0670) :
  EP-15 livre la mécanique, cinq écrans clés — planning, devis, reste à engager, risques,
  révisions — et les notions EVM (décision de l'auteur du 2026-10-25, #1445).
- `WF-IHM-0140-A` — « Dans la grille de devis, l’intitulé de la colonne du montant corrigé de
  l’inflation porte une infobulle qui nomme l’année de référence et le taux d’inflation. » :
  l'année de référence de la révision (`reference_year`) et le taux d'inflation du projet, que le
  serveur rend.
- écart : `WF-IHM-0140-A` — « L’aide s’affiche dans la langue de l’utilisateur. » : le premier jet
  est rédigé en français par un agent et relu par l'auteur ; la version anglaise est décidée après
  cette relecture (décision de l'auteur, #1075) ; le test de complétude vérifie le français, puis
  l'anglais quand il est décidé ; EP-11 clôt.
- propre à l'US : l'aide d'un écran suit toujours la même structure — ce que montre l'écran et son
  rôle dans la méthode ; ses commandes, leur raccourci et leurs conditions ; ses colonnes et ses
  valeurs calculées ; les gestes au clavier ; voir aussi — et relie les notions de la méthode
  (révisions, budget de référence et valeurs EVM, reste à engager et devis actualisé, provision et
  réserve, avenant et différentiel, lotissement, chemin critique), reprises du glossaire de
  l'annexe A sans le réécrire ; une recherche porte sur les titres et les notions (la recherche, la
  section « Ses colonnes » du panneau et les cinq notions restantes : EP-16, US-0670) ;
- propre à l'US : le rendu Markdown n'accepte aucun HTML brut ; le panneau est accessible — focus,
  Échap, titre ;
- propre à l'US : un composant commun `CommandTooltip`, sur `Tooltip` de shadcn, porte le libellé,
  une phrase d'aide des catalogues (clé `help` par commande, dans les deux langues, `make catalogs`)
  et le raccourci en `<kbd>` selon le poste, à une seule source avec `aria-keyshortcuts` ; une
  commande indisponible dit dans son infobulle la condition qui manque et reste atteignable au
  survol et au focus (`aria-disabled`) ; l'infobulle s'ouvre au survol comme au focus, se ferme par
  Échap sans déplacer le focus, est liée par `aria-describedby`, et ne porte jamais seule une
  information nécessaire ;
- propre à l'US : la règle du guide dit qu'un bouton porte `CommandTooltip`, les `title=` sont
  retirés, et un test refuse un nouveau `title=` sur un bouton ;
- propre à l'US : l'en-tête d'une colonne dit ce qu'elle désigne — la définition de l'aide, à la
  même source — et une valeur calculée dit de quoi elle dépend comme le serveur le rend
  (`getComputedValueDependencies`, WF-IHM-0030).

**Notes de réalisation.** Décisions de l'auteur du 2026-10-18 (#1071, #1075). La conception dit où
vivent les fichiers (`frontend/help/fr/<code FBS>.md`, proposé), comment la table des fonctions
(`functions.json`) en est la clé, comment les infobulles des colonnes lisent la même source, et le
lot qui relit le texte. Lots proposés : la mécanique avec les aides de cinq écrans clés et les
notions EVM ; les infobulles des colonnes et des valeurs calculées avec `CommandTooltip` ; les aides
des autres écrans par familles. Réalisé par L1, L1b, L2 et L3 (#1136, #1409, #1137, #1138) ; L3b, L4
et L5 transférés à EP-16 comme US-0670/L1 à L5 (décision de l'auteur du 2026-10-25, #1445), et l'US
passée `fini` par le recadrage. Hors périmètre : un tutoriel guidé et une documentation hors de
l'application.

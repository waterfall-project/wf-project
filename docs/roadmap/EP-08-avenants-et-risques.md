---
id: EP-08
titre: Gérer les risques, leurs provisions et la réserve, et déplacer la référence par avenant
statut: en cours
depend_de: EP-10, EP-27
famille: front, back
issue: 3809
---

# EP-08 — Avenants, risques et provisions

## Objet

Les risques — attributs, états, réexamens datés, devis propre —, leur grille de suivi, et
leurs provisions, qui n'entrent jamais au budget de référence, et la réserve pour risques de la
révision de référence ; les structures différentielles qui préparent un avenant ; la fusion
d'un différentiel, qui marque la révision et en fait la référence ; la survenance d'un risque,
qui fusionne son devis propre dans la révision en cours, à montant budgété nul, sans toucher
à la référence (#257).

Un avenant est la seule façon de déplacer la référence une fois désignée ; la survenance d'un
risque partage avec lui la mécanique de fusion, et donc cet EPIC. Il vient après le reste à
engager, dont la fusion conserve les montants réestimés et qui porte les provisions des risques
identifiés et la couverture des risques, et après les indicateurs (revue de la ventilation,
2026-10-09) : il clôt donc les Vérif qui citent la valeur acquise ou la dérive devant un risque
survenu, une fusion ou un avenant (WF-RIS-0050, WF-RIS-0060, WF-REV-0050, WF-IND-0030,
WF-IND-0100), et les usages du chef de projet, dont la gestion des risques est la dernière
fonction (WF-INTF-0010).

## Ce qui en fait partie

- les attributs, les états et les réexamens d'un risque, et sa grille de suivi ;
- le devis propre d'un risque, dans une structure qui lui est réservée ;
- les provisions, leur place dans le devis et le reste à engager, la réserve et la couverture des risques ;
- les structures différentielles, leur coexistence, leur fusion ou leur abandon — l'abandon par une
  opération nouvelle du contrat, `deleteCostStructure` (décision de l'auteur du 2026-11-17) ;
- la base d'un différentiel, l'état de la structure principale auquel il se rapporte, et sa mise à
  jour depuis la structure principale, qui précède sa fusion — par deux opérations nouvelles du
  contrat (décision de l'auteur du 2026-11-19, #4034) ;
- la contractualisation d'un avenant, qui produit la nouvelle référence, et la survenance
  d'un risque, qui fusionne son devis propre dans la révision en cours ;
- les bornes de la correction manuelle d'une référence ;
- la valeur planifiée recalculée sur la nouvelle référence ;
- les écrans des risques et des avenants de la maquette, branchés sur le service ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — les risques de PRJ-001, leurs devis
  propres, leurs réexamens et leurs provisions, l'avenant 1 fusionné, qui fait de la révision 101 la
  référence, la survenance de 752 et l'avenant 2 — chargée par `waterfall-api load-witness` ;
- les constats reçus, soldés.

## Ce qui n'en fait pas partie

- le calcul des indicateurs — EP-10 ; ici, leurs exemples chiffrés devant un risque survenu,
  une fusion ou un avenant, qui se closent dans cet EPIC ;
- les risques du portefeuille — EP-11 ;
- une mesure propre : le tableau des objectifs du §4.6.2 ne cite ni la fusion, ni la survenance, ni
  le registre ; les mesures existantes sont rejouées à la livraison (« Définition de fini »).

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
WF-QUA-0040 entre au tableau en portée « début », comme en EP-10 : cet EPIC charge sa tranche du
jeu de données de référence, qu'EP-13 clôt. WF-IHM-0110 est construite par EP-06 et close
ici : son Vérif demande le réexamen d'un risque et la déclaration d'une survenance (cadrage
d'EP-06, décision de l'auteur du 2026-11-07). WF-DEV-0010, WF-DEV-0030, WF-PRJ-0040, WF-DEV-0050,
WF-REV-0080, WF-INTF-0100, WF-INTF-0090 et WF-REF-0030 sont commencées par EP-07 et closes ici :
leur Vérif demande une ligne de provision, un différentiel, une fusion ou la déclaration d'un
risque (cadrage d'EP-07, décision de l'auteur du 2026-11-07). WF-RAE-0010, WF-RAE-0020, WF-PLA-0040,
WF-PLA-0050, WF-PRJ-0050 et WF-INTF-0120 sont commencées par EP-09 ou avant lui et closes ici : leur
Vérif demande une ligne de provision, un risque identifié, écarté ou survenu, ou un avenant (cadrage
d'EP-09, décision de l'auteur du 2026-11-07).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-REV-0040-A` | Désignation de la révision de référence | fin — amorcée en EP-04, EP-15 | US-2560 |
| `WF-REV-0050-A` | Fusion d’un différentiel | fin — amorcée en EP-15 | US-2560 |
| `WF-PLA-0170-A` | Rattachement au lotissement | fin — amorcée en EP-06 | US-2560 |
| `WF-REV-0100-A` | Structures de coûts d'une révision | fin — amorcée en EP-04, EP-15 | US-2550, US-3050 |
| `WF-IHM-0020-A` | Contexte de lecture affiché | fin — amorcée en EP-02, EP-15, EP-27 | US-2640 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | fin — amorcée en EP-02, EP-06, EP-07 | US-2590 |
| `WF-DEV-0080-A` | Valeur planifiée | fin — amorcée en EP-07 | US-2630 |
| `WF-RIS-0010-A` | Attributs d’un risque | fin — amorcée en EP-15 | US-2580 |
| `WF-RIS-0020-A` | États d’un risque | fin — amorcée en EP-15 | US-2590 |
| `WF-RIS-0030-A` | Devis propre d’un risque | fin — amorcée en EP-15 | US-2570 |
| `WF-RIS-0040-A` | Grille de suivi des risques | fin — amorcée en EP-15 | US-2600 |
| `WF-RIS-0050-A` | Réserve pour risques et couverture | entière | US-2610 |
| `WF-RIS-0060-A` | Survenance d’un risque | entière | US-2620 |
| `WF-ADM-0100-A` | Catalogue des permissions | fin — amorcée en EP-03 | US-2560 |
| `WF-IND-0030-A` | Valeur acquise | fin — amorcée en EP-10 | US-2630 |
| `WF-IND-0100-A` | Courbe de coûts cumulés | fin — amorcée en EP-10 | US-2630 |
| `WF-INTF-0010-A` | Usages du chef de projet | fin — amorcée en EP-06, EP-07, EP-09, EP-10 | US-2650 |
| `WF-RAE-0010-A` | Composition du reste à engager | fin — amorcée en EP-09 | US-2610 |
| `WF-RAE-0020-A` | Indicateurs de reste à engager | fin — amorcée en EP-09 | US-2610 |
| `WF-PLA-0040-A` | Hiérarchie des tâches | fin — amorcée en EP-06, EP-22, EP-09 | US-2580 |
| `WF-PLA-0050-A` | Jalons | fin — amorcée en EP-06, EP-09 | US-2580 |
| `WF-PRJ-0050-A` | Sous-projets | fin — amorcée en EP-15, EP-16, EP-04, EP-09 | US-2580 |
| `WF-INTF-0120-A` | Import du reste à engager (FLX-05) | fin — amorcée en EP-09 | US-2580 |
| `WF-REF-0160-A` | Matrice de risques | fin — amorcée en EP-05 | US-2600 |
| `WF-DEV-0010-A` | Taux horaires requis pour le calcul à la création d’un chiffrage | fin — amorcée en EP-07 | US-2580 |
| `WF-DEV-0030-A` | Calcul du montant d’une ligne | fin — amorcée en EP-07 | US-2580 |
| `WF-PRJ-0040-A` | Taux d’inflation du projet | fin — amorcée en EP-07 | US-2580 |
| `WF-DEV-0050-A` | Grille de devis | fin — amorcée en EP-15, EP-07 | US-2550 |
| `WF-REV-0080-A` | Comparaison de deux révisions | fin — amorcée en EP-15, EP-07, EP-27 | US-2560 |
| `WF-INTF-0100-A` | Import du devis (FLX-03) | fin — amorcée en EP-07 | US-2550 |
| `WF-INTF-0090-A` | Imports et révisions marquées | fin — amorcée en EP-06, EP-07 | US-2570 |
| `WF-REF-0030-A` | Natures de coût | fin — amorcée en EP-05, EP-07 | US-2570 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06, EP-07, EP-09, EP-10 | US-2650 |

## Opérations du contrat

Une opération manque au contrat, et sa conception l'y écrit avant le code qui la consomme :
`deleteCostStructure`, l'abandon d'un différentiel non fusionné (WF-REV-0100 : « chacune est
fusionnée ou abandonnée indépendamment » ; décision de l'auteur du 2026-11-17, contre le gel du
contrat par EP-16). Le contrat reçoit aussi le refus de `setNodeTracking` hors de la structure
principale (#2497) et une variante déclarée de `getProjectRiskCoverage` (#2002). Deux autres
opérations lui manquent depuis la reprise du 2026-11-19 (#4034), et la conception les y écrit de
même : `getStructureRebaseReport` et `rebaseCostStructure`, le compte rendu et l'application de la
mise à jour d'un différentiel depuis la structure principale.

Servies ici pour la première fois (18) :

- `revisions` : `createCostStructure`, `deleteCostStructure`, `getStructureRebaseReport`,
  `rebaseCostStructure`, `getStructureMergeReport`, `mergeCostStructure` ;
- `risks` : `listRisks`, `createRisk`, `getRisk`, `updateRisk`, `deleteRisk`, `updateRiskProvision`,
  `listRiskReviews`, `reviewRisk`, `getRiskOccurrenceReport`, `declareRiskOccurrence`,
  `getProjectRiskCoverage`, `getProjectRiskMatrix`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute :

- `revisions` : `createRevision` et `abandonRevision` (les structures et les risques qu'elles
  reprennent ou défont), `designateReferenceRevision`, `listCostStructures`, `compareRevisions`,
  `listNodes` et les écritures de l'arbre sur un différentiel et sur un devis propre,
  `updateEstimateLine`, `setNodeTracking`, `undoLastChange`, `redoLastUndo`,
  `generatePlanningSkeleton` ;
- `exchanges` : `openImport`, `listImports`, `getImport`, `applyImport` — sur une structure autre
  que la principale, et pour leur garde (#2473) ;
- `analysis` : `getRemainingIndicators`, `getProjectIndicators`, `getCostCurve`,
  `getEarnedValueCurves` — devant une provision, un risque survenu, une fusion ou un avenant ;
- `reference` : `getReferenceSettings`.

## Préalables

EP-10 et EP-27 livrés : `epic/EP-08` se tire de `main`, au premier lot, une fois les deux fusionnés
(décision de l'auteur du 2026-11-17). C'est la règle du README, et non plus l'exception du lot pivot
US-1660/L1 #2437 (décisions du 2026-11-07 et du 2026-11-15), écrite avant qu'EP-08 ne dépende aussi
d'EP-27, dont la branche est distincte : à ce cadrage, il reste deux lots à chacun. EP-08 trouve
alors dans `main` ce qu'il attendait lot par lot — le calcul du jour, la conservation et la lecture
conservée, les courbes, le cache d'EP-10, et la comparaison dans les grilles d'EP-27 —, et chaîne sa
migration sur la dernière d'EP-10. EP-09 avant eux : la fusion conserve les montants réestimés et
épargne les tâches démarrées.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.6, et ceux de WF-REV-0050, WF-IND-0030 et
  WF-IND-0100 qui citent un risque survenu, une fusion ou un avenant, sont des tests qui
  passent (WF-QUA-0020) ;
- deux structures différentielles coexistent, et la fusion de l'une laisse l'autre intacte ;
- un différentiel ouvert avant que la structure principale ne reçoive une tâche, une réestimation,
  la survenance d'un risque et la fusion d'un autre différentiel, puis mis à jour et fusionné,
  laisse dans la structure principale tout ce qu'elle a reçu entre-temps (#4034) ;
- après fusion, la révision produite porte le nom de version demandé et devient la référence ;
- la modification du devis propre d'un risque identifié ne change pas le budget de référence ;
- le parcours de bout en bout déclare un risque, le fait survenir et contractualise un avenant,
  contre le service réel ;
- le témoin chargé a pour référence la révision 101, produite par la fusion de l'avenant 1, et ses
  lectures sont comparées aux exemples du contrat sans la réserve « à la référence près » ;
- `make requirements` ne laisse sans test du back aucune des exigences que cet EPIC clôt ;
- les mesures existantes, `make measure-core` et `make measure`, rejouées sur le témoin chargé avec
  ses risques et ses avenants, tiennent leurs objectifs et ne se dégradent pas de plus d'un quart
  (WF-QUA-0060) ; la durée de la fusion et de la survenance y est relevée, sans objectif (décision de
  l'auteur du 2026-11-17).

## Constats reçus

Relevés par la revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`)
et tranchés par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), que le service
suit une fois figé.

- #1762 — la trace des nœuds issus d'un risque survenu (`origin_risk_id`), ses filtres, et leur
  réestimé face au coût à la survenance (E-04 ; contrat #1761 ; spécification #1760).
- #1783 — l'identité d'un risque, donnée du projet (`updateRisk`) ; sa provision, saisie de la
  révision (`updateRiskProvision`) (H-02 ; contrat #1782).
- #1786 — le registre des risques se filtre sur chacune de ses colonnes (H-01 ; contrat #1785).

- #1363 — faux back : l'avenant que crée « Préparer un avenant » (structure 213) ne s'ouvre pas ;
  #1369 — faux back : la structure du risque créé (208) n'est pas listée. Relevés par EP-15, la
  limite d'un faux back sans état que le service des structures différentielles et des devis
  propres lève ici ; reportés d'EP-04 au cadrage du 2026-10-28 (décision de l'auteur).

- #1830 — contrat : aucun exemple de `getBackgroundTask` ne montre une survenance aboutie
  (`task_occurrence_succeeded`), si bien que le succès de « Déclarer survenu » — son message et le
  `router.refresh` qui relit le risque survenu — n'est éprouvé par aucun test du front (point 3 de
  #1384). Reporté d'EP-17 le 2026-11-02 (décision déléguée par l'auteur) : le succès s'éprouve ici,
  contre le service réel, sans exemple ajouté au contrat figé, comme #1714 l'a fait pour EP-04.

#763, les formulaires du risque, reporté ici par EP-14/L53, est ramené en EP-15 le
2026-10-18 (décision de l'auteur) : le parcours du risque est montré dans la maquette pour
validation (#1062, US-0520) ; le comportement réel — provision, réserve, fusion à la survenance —
reste ici.

Reportés d'EP-17 à sa livraison (rangement du 2026-11-05) :

- #1972 — front : dans `readGridScreen`, la promesse qui retient l'origine d'un filtre sur un
  risque nommé peut rester sans gestionnaire quand la lecture des risques survenus rejette avant
  qu'elle soit attendue ; la lecture des risques et de leur filtre d'origine est servie ici.
  Relevé par la revue d'US-0800 (EP-17).

- #2002 — contrat : aucun exemple ne porte un réestimé des survenus (`occurred_reestimated`)
  différent de leur coût (`occurred_cost`) — `portfolio_risks`, `risk_coverage` servent le même
  montant des deux côtés —, et le test de la vue des risques du portefeuille ne les sépare pas ;
  l'exemple se décide avec le service de la survenance. Relevé par la revue d'US-1210 (EP-17).

- #1626 — contrat : après une saisie du devis propre d'un risque, qui fait avancer
  `Risk.lock_version` (décision Q1 (b) du 2026-10-28, #1453), `NodesWritten` ne rend que
  `structure_lock_version` : un écran du risque ouvert en parallèle est refusé par 412 sans
  moyen de reprendre le compteur. Relevé par la revue d'US-0680/L1 (EP-16), rangé ici le
  2026-11-05.

Relevés par la revue locale d'US-1400/L2 (EP-06, #2340) et reportés ici, le cas n'existant
qu'avec les différentiels :

- #2497 — contrat : `setNodeTracking` ne vérifie pas que le nœud est de la structure principale
  (`task.tracking` n'est dans `editable_fields` que pour elle) ; une inscription demandée sur un
  nœud d'un différentiel écrirait la lignée de la principale. Un refus s'ajoute au contrat puis au
  code. Décision de l'auteur du 2026-11-08.
- #2499 — back : deux écritures d'inscriptions d'une même lignée sous deux structures ne sont
  sérialisées que par le verrou de chaque structure ; la violation d'unicité de `tracking_entry`
  remonterait en 500.

Relevé par la revue locale d'US-1460 (EP-06, #2325), reporté ici, et noté au cadrage du 2026-11-17 :

- #2541 — back : `main_structure_without_tasks` juge toute la révision, pas la seule structure
  principale ; l'écart naît avec le premier différentiel ou devis propre qui porte une tâche.

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Reçus à ce titre :

- #1767 — back : les saisies du devis refusées sur la structure principale en réalisation et sous
une tâche terminée, permises dans un différentiel (F-01) ;
- #2473 — conception : les routes des imports sont gardées par planning.read, que l'import d'un
devis ou de coûts réels ne demande pas ;
- #2538 — back : l'annulation suppose une entrée de planning, risk_ids rendu vide en dur ;
- #2883 — back : le refus d'un cycle de parenté du chargeur des tâches nomme la tâche de départ, et
son test n'éprouve ni le type ni l'auto-parenté ;
- #2884 — back : un parent_lineage_id absent de la description donne un KeyError brut au chargeur
des tâches ;
- #2905 — back : annuler un collage de l'avancement d'une tâche demande planning.write, le collage
remaining.write ;
- #3095 — back : une ligne d'import dont le montant déborde fait échouer l'application sans dire
laquelle ;
- #3154 — corpus : 10-other-constants.xml, un « Standard » de 6 heures sous des constantes de 7, en
écart de calendrier ;
- #3156 — tests : le test « constantes différentes ⇒ écart » sur tout le corpus peut passer à vide,
et l'en-tête du README du corpus mal recoupé ;
- #3165 — tests : trois mineurs du parcours e2e de l'écart de calendrier.

Décisions de l'auteur au cadrage du 2026-11-17, sur les constats restés sans décision : #1626, le
front relit le risque et le contrat ne change pas (US-2640) ; #2002, une variante déclarée de
`getProjectRiskCoverage` (US-2610) ; #2473, les routes des imports gardées par la seule visibilité du
projet, le genre jugé dans le noyau (US-2660).

## Conception

Écrite au cadrage du 2026-11-17, sur le code de `main` et d'`epic/EP-10` à cette date. Elle dit ce
qu'un lot devrait sinon décider seul ; ce qui relève d'un lot reste au lot. Reprise le 2026-11-19,
sur le code d'`epic/EP-08` à cette date, pour la base d'un différentiel et sa mise à jour (#4034) :
« Ce que la reprise du 2026-11-19 décide » et « La base d'un différentiel et sa mise à jour » sont
d'elle, et les autres sections disent ce qu'elle y change.

### Ce que le cadrage décide

- **Douze US, le socle en lot technique de la première** : la migration, les natures de structure,
  le module `core/risks` à vide avec son interface déclarée, les points d'extension nouveaux et les
  routeurs vides. Tout lot du back en dépend.
- **`epic/EP-08` se tire de `main`**, EP-10 et EP-27 livrés (« Préalables »). Écartée : l'exception
  du lot pivot (décisions du 2026-11-07 et du 2026-11-15), écrite avant la dépendance à EP-27, dont
  la branche est distincte.
- **L'abandon d'un différentiel entre au contrat**, `deleteCostStructure`, contre le gel d'EP-16
  (décision du 2026-10-22). Écartés : ne rien servir, un différentiel jamais fusionné étant recopié
  dans chaque révision suivante ; un constat laissé « à trancher ».
- **Cet abandon est irréversible**, hors de l'historique annulable, comme celui d'une révision.
  Écarté : un genre nouveau d'`UndoneKind` qui restituerait un arbre entier, un instantané de toute
  la structure dans la pile.
- **Une tâche démarrée que le différentiel retire garde le budgété de ses lignes** ; seul leur reste
  à engager passe à zéro, comme `mergeCostStructure` le dit. « Sa valeur acquise est inchangée » se
  lit du montant que la tâche porte : terminée par la fusion, elle l'acquiert (WF-IND-0030). Un
  constat de spécification (#3850) demande de préciser le Vérif et le motif de WF-REV-0050 (« ramène son
  budget à ce qui a été fait ») ; il ne bloque aucun lot. Écarté : mettre à zéro ses grandeurs de
  référence, que ni le contrat ni le corps de l'exigence ne disent.
- **Le témoin rejoue la fusion de l'avenant 1** (« Le chargeur du témoin »). Écarté : charger la
  révision 101 telle que marquée et la marquer par la fusion d'un avenant vide, qui n'éprouverait
  rien et ne chargerait pas le saisi comme il a été saisi.
- **Pas d'US de mesure** : la non-régression des mesures existantes est en définition de fini.
  Écartée : une US propre, le tableau du §4.6.2 ne citant aucune opération de cet EPIC.
- **Trois constats tranchés** : #1626, le front relit le risque ; #2002, une variante déclarée de
  `getProjectRiskCoverage` ; #2473, les routes des imports gardées par la visibilité du projet.

### Ce que la reprise du 2026-11-19 décide

Un avenant se négocie pendant que le projet avance et passe plusieurs revues : la structure
principale reçoit, entre l'ouverture d'un différentiel et sa fusion, des tâches, des réestimations,
la survenance d'un risque, la fusion d'un autre différentiel. La reprise dit ce que la fusion en
fait (#4034, décisions de l'auteur du 2026-11-19).

- **La fusion est en trois voies, sur une base conservée.** Un différentiel se rapporte à l'état de
  la structure principale qu'il a copié, sa base ; ce qu'il désigne est son écart à cette base, et
  la fusion n'applique que cela. Écartées : les deux voies, où le différentiel est l'état cible —
  elles défont ce que la principale a reçu depuis, et de deux différentiels ouverts sur le même
  état, la fusion du second retire ce que la fusion du premier a apporté ; la marque du compteur
  d'un nœud ou de sa date de création — la copie d'une révision remet le premier à 1 et réécrit la
  seconde, pour la principale comme pour le différentiel qu'elle reprend, et un compteur ne dit pas
  quelle valeur a changé.
- **La base est une structure**, d'une nature que rien ne liste ni ne sert, copie de la structure
  principale. Écartés : une image sérialisée, dont le format devrait rester lisible tant que le
  différentiel vit, des mois, quand une structure suit les migrations du schéma sans code à elle ;
  un journal de ce que le différentiel écrit, que chaque écriture de l'arbre, l'annulation et les
  imports auraient à tenir.
- **Un différentiel se lit contre sa base**, non plus contre la structure principale : ce qu'il
  présente ajouté, modifié ou retiré est ce qu'il désigne, que la principale ait bougé ou non.
  Écartée : la lecture contre la principale, qui présente retiré, sur un différentiel en retard, ce
  que la principale a reçu depuis ; elle est celle d'US-2550/L3, et ne change que de base.
- **La mise à jour reporte dans le différentiel ce que la principale a reçu depuis sa base**, sans
  rien changer de ce qu'il désigne, puis fait de la principale sa nouvelle base. Un différentiel à
  jour a pour base la principale telle qu'elle est : son écart à la principale est alors ce qu'il
  désigne, et **le calcul en deux voies d'US-2560/L1 se garde tel quel**.
- **La fusion exige un différentiel à jour ; elle ne le met pas à jour elle-même.** Son compte rendu
  est une lecture, qui ne peut écrire la mise à jour, et ce que celle-ci signale se résout par une
  saisie avant de fusionner. Écartée, contre ce que la décision de #4034 disait d'abord : la mise à
  jour d'office en tête de la fusion, qui demanderait de calculer le compte rendu sur un
  différentiel mis à jour sans l'écrire — `merge_plan` et `merge_lines` réécrits sur des arbres en
  mémoire — et ferait confirmer d'un seul geste des conflits que personne n'a regardés.
- **La mise à jour a son compte rendu préalable et sa confirmation**, comme l'import, la fusion et
  la survenance, calculés par la même fonction. Elle est synchrone : elle écrit ce que la principale
  a reçu et recopie la base, ce que l'ouverture d'un différentiel fait déjà sans tâche de fond. Elle
  n'entre ni à l'historique annulable ni au journal d'audit, que la spécification ne lui ouvre pas.
  Écartée : une tâche de fond de plus et son genre au contrat.
- **Pas d'écran de résolution de conflits.** Ce que la spécification règle reste une règle, lue au
  compte rendu de la fusion : la tâche démarrée que le différentiel retire est gardée et terminée,
  la provision dont la tâche disparaît passe à sa parente. Ce que la mise à jour ne peut reporter
  est gardé au différentiel, signalé à son compte rendu, et se corrige par une saisie : les quatre
  règles sont dans « La base d'un différentiel et sa mise à jour ».
- **Deux opérations nouvelles au contrat**, contre son gel, comme `deleteCostStructure` :
  `getStructureRebaseReport` et `rebaseCostStructure`. Écarté : une seule opération qui écrit sans
  compte rendu préalable, contre l'usage de toute écriture en masse du contrat.
- **Ce que la structure désigne et son report sont deux fonctions**, qui ne nomment pas la nature
  « avenant » : EP-30 les reprendra pour le devis propre d'un risque. Dans cet EPIC, un devis propre
  n'a ni base ni mise à jour : il ne copie rien de la structure principale.
- **Le montant budgété garde ce qui a été notifié.** Vérifié sur le code : il est calculé à la
  fusion, des grandeurs que le différentiel donne, puis repris par la lignée dans la révision de
  référence à chaque copie (`copy_lines`). Un avenant chiffré une année et fusionné la suivante se
  relit avant sa fusion, dans sa grille, aux taux de la révision en cours (WF-REV-0060).
- **Deux constats de la survenance tranchés au plus léger**, EP-30 rendant leur règle provisoire :
  #4133, le compte rendu signale un devis propre qui commence avant le jour de la déclaration, sans
  refuser ni redater ; #4134, chaque tâche de la structure principale que la greffe redate est une
  différence de plus au compte rendu, sans champ nouveau.

### Tables et migrations

Une migration, dans le socle, chaînée sur la dernière de `main` à la création de la branche (`0034`
à ce jour), sans donnée à reprendre : aucune révision n'a d'autre structure que la principale, ni de
risque. Les tables révisées sont partitionnées par projet, comme celles d'EP-04 à EP-07, et la
fonction qui crée les partitions d'un projet les connaît.

- **`cost_structure`** : `kind_known` admet `main`, `amendment` et `risk` ; une colonne `risk_id`,
  non nulle si et seulement si la nature est `risk`, clé étrangère vers `risk` ; un devis propre au
  plus par risque et par révision (index unique partiel). L'unicité de la principale est inchangée.
- **`risk`**, non révisée : l'identité du risque, donnée du projet — libellé, description, actions
  de mitigation —, son compteur et son audit. `Risk.lock_version` est ce compteur : il avance à
  toute écriture du risque, de son évaluation ou de son devis propre, et ne revient jamais en
  arrière, abandon et annulation compris.
- **`risk_evaluation`**, révisée, une ligne par risque et par révision qui le porte : la
  probabilité, l'état, la structure propre, la ligne de provision (nulle hors de l'état identifié),
  la catégorie, le sous-projet et la lignée de la tâche que le risque désigne — gardés quand il est
  écarté, pour son retour —, le coût à la survenance (nul hors de l'état survenu). La copie d'une
  révision la reprend, l'abandon la supprime avec la révision : c'est ce qui ramène l'évaluation à
  celle de la dernière révision marquée. Un risque dont aucune révision ne garde d'évaluation après
  un abandon est supprimé avec lui.
- **`risk_review`**, une ligne par réexamen, rattachée à la révision où il a été fait : sa date, la
  probabilité, la gravité et l'état retenus. Elle n'est pas copiée : l'historique d'un risque lu
  dans une révision est celui des révisions marquées qui la précèdent et le sien. L'abandon et
  l'annulation retirent les réexamens de la révision en cours.
- **`risk_reference_share`**, une ligne par risque et par révision de référence : la provision que
  le risque porte dans cette référence. Écrite quand une révision devient la référence — par
  désignation ou par fusion —, supprimée quand une désignation est corrigée : pour un risque que la
  nouvelle référence porte identifié, le montant de sa ligne de provision ; pour un risque survenu
  ou écarté avant elle, la part qu'il avait dans la référence précédente. La réserve est leur somme
  (M-01), la provision lue d'un survenu ou d'un écarté est sa part (H-03), et le budgété d'une
  ligne de provision est celle de son risque.
- **`node.origin_risk_id`** existe (EP-06) : il reçoit sa clé étrangère vers `risk`, et ne désigne
  plus que le risque dont la survenance a fusionné le nœud, comme le contrat le dit.

Écartés : la réserve dans une colonne de `revision`, qui ne donnerait pas la part de chaque risque
et ferait écrire `core/revisions` pour les risques ; un réexamen recopié dans chaque révision, cent
quatre-vingts copies d'un historique qui ne change pas ; l'identité versionnée, contre H-02.

Une seconde migration, par le socle de la mise à jour (US-3050), chaînée sur la dernière
d'`epic/EP-08`, sans donnée à reprendre : aucun différentiel n'existe hors des bases de
développement, qui se recréent.

- **`cost_structure`** : `kind_known` admet `base` ; une colonne qui nomme le différentiel dont la
  structure est la base, non nulle si et seulement si la nature est `base`, clé étrangère vers ce
  différentiel dans la même révision, une base au plus par différentiel (unicité) ; et, sur un
  différentiel, le compteur que la structure principale portait quand la base a été prise, non nul
  si et seulement si la nature est `amendment` : le différentiel est à jour tant que la principale
  porte ce compteur.
- **Les nœuds, les tâches, les liaisons, les lignes et leurs images d'une base** sont dans les
  tables de toute structure : aucune table nouvelle. Une base ne porte ni rattachement au
  lotissement, ni ligne de provision, comme le différentiel qu'elle accompagne (WF-PLA-0170,
  #4008).

Écartés : des tables propres à la base, doubles de celles des nœuds et des lignes ; la base sur
la ligne du différentiel sans structure à elle, que ni la copie ni la lecture d'un arbre ne
sauraient lire.

### Ce qui reconnaît une ligne de provision

Une ligne de provision est une ligne dont la catégorie relève d'une nature de type provision pour
risques (WF-DEV-0020), lue sur l'image des catégories de sa révision. `core/estimate` le dit, et lui
seul : `core/planning` cesse de la juger par `origin_risk_id` non nul — ce qui tiendrait pour des
provisions les lignes fusionnées par une survenance, qui sont du travail et retiennent leur tâche —
et pose la question aux lignes par le registre qu'EP-09 a déclaré (`register_open_lines`). Le socle
fait ce changement, avec un test qui pose une ligne issue d'un risque sous une tâche : elle la
retient ouverte. Écarté : un booléen sur `estimate_line`, une seconde source de la même règle.

### Modules

| Module | Ce qu'il reçoit | Ce qu'il expose |
|---|---|---|
| `core/risks` (nouveau, FBS-4.6) | les tables des risques ; la déclaration, l'identité, la provision, le réexamen, la suppression ; le registre, la matrice, la couverture, la réserve ; le compte rendu et l'application d'une survenance | son interface, une fonction par opération ; il s'inscrit à `register_copy`, à la clôture d'une révision, à `register_designation`, à `register_coverage`, à l'historique annulable et aux registres ci-dessous |
| `core/revisions` | les structures d'autres natures : ouvrir, lister, abandonner un différentiel ; sa base, créée, reprise et supprimée avec lui, jamais listée, et l'état « à jour » ; la mise à jour — son compte rendu, sa commande, la base reprise — et `register_rebase`, par lequel `core/planning` et `core/estimate` donnent chacun leur part ; la copie qui ne reprend pas une structure consommée ; la fusion — son compte rendu, sa commande, sa tâche de fond, le marquage et la référence qu'elle produit | `merge_report`, `submit_merge`, `run_merge`, `load_merge` pour le témoin ; `register_merge`, par lequel `core/planning` et `core/estimate` donnent chacun leur part des écarts et de l'application ; la question « structure principale » de `main_structure_without_tasks` (#2541) |
| `core/planning` | la copie d'une structure dans une autre (un différentiel naît copie de la principale) ; les écarts d'un différentiel à la principale par la lignée, et leur application ; ce qu'une structure désigne par rapport à sa base, et le report dans le différentiel de ce que la principale a reçu, tâches et liaisons ; la greffe d'un sous-arbre sous une tâche ou après un jalon ; le report d'une ligne de provision dont la tâche disparaît ; le refus de `setNodeTracking` hors de la principale et le verrou de la lignée (#2497, #2499) | `graft`, que la survenance appelle ; sa part de `register_merge` |
| `core/estimate` | la ligne de provision — créée, déplacée, rechiffrée, retirée par `core/risks` seul — ; les grandeurs de référence que la fusion donne aux lignes désignées ; la lecture d'un différentiel contre sa base ; la part des lignes dans la mise à jour ; les lignes greffées à budgété nul ; les imports sur une structure autre que la principale | la question « provision » ; l'écriture de la provision, réservée à `core/risks` ; sa part de `register_merge` |
| `core/indicators` | les marches d'avenant, les provisions dans la projection et les décaissements, la couverture dans le document `remaining`, les compteurs des risques dans l'empreinte du cache | inchangé |
| `core/history` | les quatre genres de saisie d'un risque (`risk_create`, `risk_update`, `risk_review`, `risk_delete`) ; `risk_ids` de la réponse (#2538) | `register_undoable`, par lequel `core/risks` dit comment défaire et refaire les siens |
| `core/exchanges` | la consultation du genre d'un import, jugée dans le noyau (#2473) | inchangé |

Les modules ne se lisent que par leur interface. `core/risks` dépend de `core/revisions`,
`core/planning`, `core/estimate` et `core/risk_settings` ; aucun d'eux ne dépend de lui : ce qu'ils
doivent savoir des risques passe par leurs registres.

### La base d'un différentiel et sa mise à jour

Écrite à la reprise du 2026-11-19 (#4034). Trois structures y jouent : la structure principale, le
différentiel, et la base du différentiel — la principale telle qu'elle était quand le différentiel
l'a copiée, ou à sa dernière mise à jour.

- **La base naît avec le différentiel.** `createCostStructure` copie la structure principale deux
  fois sous son verrou, par la copie d'une structure dans une autre : le différentiel, que
  l'utilisateur écrit, et sa base, que personne n'écrit. Les nœuds de l'une et de l'autre gardent
  la lignée de ceux de la principale.
- **La base n'est servie par aucune opération.** `listCostStructures` ne la rend pas, et une route
  qui la nomme répond 404, comme pour une structure inconnue ; ce qui parcourt les structures d'une
  révision — la grille, les imports, les indicateurs et leur empreinte, `generate_skeleton` — ne la
  compte pas. Seules l'écrivent l'ouverture d'une révision, qui la copie et la redate avec les
  autres, et la mise à jour.
- **Elle suit son différentiel.** L'abandon du différentiel la supprime ; la copie d'une révision la
  reprend avec un différentiel non fusionné, sous la lignée de sa structure, et garde l'état du
  différentiel : à jour dans la révision marquée, il l'est dans la révision ouverte ; en retard, il
  le reste. Un différentiel fusionné garde sa base dans la révision que sa fusion marque — c'est
  contre elle que se relit ce qu'il contenait (WF-REV-0100) —, et la révision suivante ne reprend
  ni l'un ni l'autre.
- **Un différentiel se lit contre sa base.** `listNodes` d'un différentiel compare, par la lignée,
  le différentiel à sa base, et non plus à la structure principale : la lecture est celle
  d'US-2550/L3, dont seule la base change. Une ligne de provision de la principale n'y est plus
  présentée retirée, la base n'en portant pas (#4035).
- **« À jour » se lit sur la structure.** Un différentiel est à jour tant que la structure
  principale porte le compteur qu'elle avait quand sa base a été prise ; toute écriture qui avance
  ce compteur le met en retard, qu'elle touche ou non ce qu'il désigne. L'état est rendu avec la
  structure (`CostStructure`), et la commande de mise à jour n'est disponible que sur un
  différentiel en retard.
- **Ce qu'une structure désigne** est son écart à sa base, par la lignée : les tâches, les
  liaisons et les lignes qu'elle ajoute, celles qu'elle retire, et, pour celles des deux, les
  valeurs qui diffèrent — celles que le compte rendu d'une fusion nomme (US-2560/L1). Il est
  calculé à la demande, jamais conservé.
- **La mise à jour** lit ce que la structure principale a reçu depuis la base — son écart à la
  base, par le même calcul — et l'écrit dans le différentiel, hors ce qu'il désigne : un nœud que
  la principale a ajouté y entre sous sa lignée, à sa place ; une valeur qu'elle a changée y est
  changée ; un nœud qu'elle a retiré en sort. Les nœuds du différentiel gardent leur identifiant.
  Puis la base est remplacée par une copie de la principale, et le différentiel est à jour. Le
  moteur de dates est rejoué une fois sur le différentiel.
- **Ce que la mise à jour ne reporte pas**, quatre règles, chacune signalée au compte rendu par une
  différence `kept` — « gardé et signalé », comme un import le dit d'une tâche démarrée :
  1. une valeur que le différentiel désigne et que la principale a changée aussi garde la valeur du
     différentiel. Pour les grandeurs d'une ligne, ce n'est pas un conflit mais la règle de
     WF-REV-0050 : la fusion donnera à la ligne les grandeurs du différentiel pour référence, et la
     principale gardera ses grandeurs courantes, réestimées ;
  2. une tâche ou une ligne que le différentiel modifie et que la principale n'a plus reste au
     différentiel, qui la désigne désormais comme un ajout ;
  3. une tâche ou une ligne que le différentiel ajoute sous une tâche que la principale n'a plus, et
     qu'il ne modifie pas, passe sous l'ancêtre le plus proche qui reste, ou au premier niveau ;
  4. une liaison que le différentiel ajoute et dont la principale n'a plus l'une des tâches est
     retirée du différentiel.
  Un nœud que le différentiel retire et que la principale n'a plus ne se signale pas.
- **Ce qui refuse la mise à jour** est ce qui refuse une fusion, jugé de même sur le différentiel
  que la mise à jour laisserait : une boucle, une liaison interdite, l'horizon, une tâche sans
  heure travaillée (`ReportRefusal`). Il naît de la rencontre de ce que le différentiel désigne et
  de ce que la principale a reçu ; l'utilisateur le lève par une saisie dans le différentiel, puis
  relance.
- **Le compte rendu** est calculé par la même fonction que l'application, qui écrit sous le verrou
  du projet puis des trois structures. La confirmation porte
  les compteurs lus de la principale et du différentiel : l'un changé depuis, 412, rien n'est
  écrit.
- **L'historique annulable** ne reçoit pas la mise à jour. Une saisie du différentiel faite avant
  elle reste annulable, sauf sur un nœud qu'elle a écrit : l'annulation est alors refusée en
  nommant l'objet, par la règle de conflit qui existe (WF-IHM-0110).
- **La mise à jour n'est offerte que sur la révision en cours**, comme l'ouverture d'un
  différentiel : sur la dernière révision marquée d'un projet sans révision en cours, un
  différentiel en retard attend que la révision soit créée.

Écartés : appliquer ce que le différentiel désigne à une copie fraîche de la principale, qui
changerait l'identifiant de chaque nœud du différentiel sous les grilles ouvertes et l'historique ;
un état « à jour » calculé par l'écart de la base à la principale à chaque lecture d'une structure,
le prix d'une comparaison entière pour un booléen.

### La fusion et la survenance

Elles partagent trois choses, écrites une fois : le calcul d'écarts présentés avant d'être
appliqués (`ImportDifference`, `ReportRefusal`, ceux de l'import), une tâche de fond qui est une
seule opération, et la création préalable de la révision en cours.

- **Le compte rendu** est calculé par la même fonction que l'application, sous le verrou des
  structures pour celle-ci : ce que le compte rendu présente est ce qui est écrit. La confirmation
  porte les compteurs lus et `creates_current_revision` ; le contrôle et le dépôt de la tâche se
  font dans une transaction, sous le verrou du projet puis des deux structures.
- **La fusion n'est offerte que sur un différentiel à jour** (reprise du 2026-11-19) : sur un
  différentiel en retard, son compte rendu et sa commande répondent 409, la condition manquante
  nommée, la dernière dans l'ordre du contrat. Sur un différentiel à jour, l'écart à la principale
  est ce qu'il désigne, et le contrôle des compteurs lus tient l'état jusqu'à l'application : une
  écriture de la principale entre le compte rendu et la confirmation est déjà un 412.
- **La fusion** applique les écarts du différentiel par la lignée : ajouts sous des lignées
  nouvelles, modifications, retraits ; une tâche démarrée retirée est gardée, le reste de ses
  lignes mis à zéro par la fonction de `setLineRemaining` (EP-09) ; une ligne désignée reçoit ses
  grandeurs de référence, et ses grandeurs courantes si sa tâche n'est pas démarrée et qu'elle ne
  porte pas la marque d'une réestimation (EP-09) ; le moteur de dates rejoué une fois juge la
  boucle, le lien interdit, l'horizon, la tâche sans heure et le poste hors de son lot. Elle
  appelle ensuite le marquage tel qu'il est (`run_marking` : images, indicateurs conservés,
  journal), fait de la révision marquée la référence par la voie de la désignation
  (`register_designation`), et marque le différentiel `is_merged`.
- **Sans révision en cours**, la même tâche ouvre la révision par copie, y fusionne la copie du
  différentiel — retrouvée par sa lignée — et la marque ; en échec, la transaction ne laisse rien.
- **La survenance** greffe le devis propre par `graft`, pose `origin_risk_id` sur chaque nœud
  greffé, retire la ligne de provision, fige le coût à la survenance, écrit le réexamen de
  survenance et marque le devis propre `is_merged`. Elle ne marque rien.
- **La copie d'une révision** ne reprend ni un différentiel fusionné ni un devis propre fusionné,
  ni leurs nœuds : la règle est dans la copie des structures, que les copies des nœuds, des lignes
  et des images suivent.
- **Les tâches de fond** portent les genres que le contrat nomme pour la fusion et la survenance ;
  pendant qu'elles courent, les écritures du projet nomment `no_background_task_running`.

Écarté : un module `core/amendments` à côté de `core/revisions`, qui aurait dû lire ses tables ;
une fusion qui appliquerait des écritures une à une par les fonctions de saisie, des états
intermédiaires que le moteur refuserait (c'est la leçon de l'application d'un import, EP-07).

### Le contrat

Modifié par un lot, avant le code qui le consomme, et le client réengendré :

- **`deleteCostStructure`**, `DELETE …/structures/{structure_id}`, avec le compteur lu de la
  structure : 204 ; 409 `STATE_FORBIDS_OPERATION`, la première condition qui manque dans l'ordre de
  la commande — `project_not_terminal`, `revision_draft`, `no_background_task_running`,
  `unmerged_amendment_exists` pour une structure qui n'est pas un différentiel non fusionné — ;
  412 au compteur périmé. Une commande `delete` s'ajoute aux commandes d'une structure
  (`StructureCommand`), disponible sur un différentiel non fusionné de la révision en cours, sous
  la permission de `create_structure`. `structure_abandon` s'ajoute aux actions du journal. La
  description de `createCostStructure` y renvoie ; `docs/api/DECISIONS.md` reçoit la décision.
- **`setNodeTracking`** déclare son refus sur une structure autre que la principale (#2497) : 409
  `STATE_FORBIDS_OPERATION`, par une condition que le lot choisit parmi celles de
  `CommandCondition` ou y ajoute, et le dit dans `DECISIONS.md`.
- **`getProjectRiskCoverage`** reçoit une variante contrefactuelle déclarée, engendrée par
  `make mock-data` : les lignes issues de 752 réestimées, `occurred_reestimated` différent
  d'`occurred_cost`, l'écart de couverture inchangé (#2002).

La reprise du 2026-11-19 y ajoute, par un lot du contrat qui précède le code (US-3050) ; ce lot
arrête les noms, et les dit dans `docs/api/DECISIONS.md` :

- **`getStructureRebaseReport`**, `GET …/structures/{structure_id}/rebase` : une lecture qui
  n'écrit rien, `StructureRebaseReport` — les compteurs lus de la structure principale et du
  différentiel, les différences (`ImportDifference`) et les motifs de refus (`ReportRefusal`). Une
  différence `added`, `updated` ou `removed` est ce que la mise à jour reporte de la principale
  dans le différentiel ; une différence `kept`, ce que le différentiel garde contre elle, `fields`
  nommant les valeurs gardées quand il y en a. Aucun schéma nouveau pour une différence : la
  description d'`ImportDifference` le dit.
- **`rebaseCostStructure`**, `POST …/structures/{structure_id}/rebase`, avec la confirmation et les
  deux compteurs lus (`StructureRebase`) : 200 et la structure mise à jour ; 409
  `STATE_FORBIDS_OPERATION`, la première condition qui manque — celles de `deleteCostStructure`,
  dans son ordre, pour une structure qui n'est pas un différentiel non fusionné, puis celle d'un
  différentiel déjà à jour — ; 412 à un compteur périmé ; et, quand un motif la refuse, le refus
  que le lot du contrat arrête, rien n'étant écrit.
- **`CostStructure`** dit si un différentiel est à jour, par un champ nul pour toute autre
  structure ; `StructureCommand` reçoit la commande de la mise à jour, listée sur un différentiel
  non fusionné, sous la permission de `create_structure`, indisponible sur un différentiel à jour.
- **`getStructureMergeReport` et `mergeCostStructure`** déclarent leur refus sur un différentiel en
  retard : 409 `STATE_FORBIDS_OPERATION`, par une condition nouvelle de `CommandCondition`, nommée
  après celles que le contrat ordonne déjà.
- **`NodeDifference`** dit que la base d'un différentiel est sa base conservée, et non la structure
  principale ; `createCostStructure` et `deleteCostStructure` disent que la base naît et disparaît
  avec le différentiel.
- **`RiskOccurrenceReport`** : la description de `differences` reçoit les tâches de la structure
  principale que la greffe redate (#4134), et le compte rendu le signalement d'un devis propre qui
  commence avant le jour de la déclaration (#4133), par US-2620/L2.
- **Exemples**, engendrés par `make mock-data` : le compte rendu d'une mise à jour de l'avenant 2,
  avec une différence de chaque sorte, sa variante refusée, et l'avenant 2 en retard dans
  `structures_amendments`.

Aucun schéma servi par un EPIC livré ne change, hors le champ que `CostStructure` reçoit, que les
écrans livrés ne lisent pas, et les commandes ajoutées à `StructureCommand`. Le succès d'une
survenance n'a pas d'exemple ajouté (#1830), et `NodesWritten` ne rend pas le compteur du risque
(#1626).

### Le service d'API et le worker

Un routeur par US, créés vides par le socle, comme en EP-10, pour que deux lots sans dépendance
n'écrivent pas le même fichier : les différentiels (US-2550), la fusion (US-2560), la déclaration
(US-2570), la provision (US-2580), les réexamens (US-2590), le registre et la matrice (US-2600), la
couverture (US-2610), la survenance (US-2620). De même, l'interface de `core/risks` a un fichier
par sujet, réexportés par le module. La mise à jour d'un différentiel (US-3050) a le sien, que son
premier lot du back crée.
Les lectures sont sous `risks.read`, les saisies sous `risks.write`, la fusion sous
`structure_merge`, la mise à jour d'un différentiel sous la permission de `create_structure` ; la
création préalable d'une révision est refusée par 409
`may_create_revision`, jamais par 403. Chaque réponse est validée contre le contrat dans les tests.
Le worker reçoit deux tâches, la fusion et la survenance, sur le modèle du marquage.

Les routes des imports ne gardent plus que la visibilité du projet ; le genre est jugé par
`core/exchanges`, et le test de l'évaluation des accès admet ces routes comme il admet
`PATH_OBJECTS` (#2473).

### Les indicateurs et le cache

Dans `core/indicators`, sur ce qu'EP-10 a prévu (« Ce que le cadrage laisse à EP-08 ») : `steps`
se calcule des références successives du projet, chacune en vigueur de son marquage à celui de la
suivante ; la projection et les décaissements comptent les lignes de provision à leur date, sans
délai de paiement ; l'exclusion des tâches de survenance de la valeur acquise est déjà dans la
sélection des lignes, et reçoit son test ; la couverture entre dans le document `remaining`
conservé au marquage. L'empreinte du cache lit le compteur de toutes les structures de la révision,
le nombre des risques du projet et la somme de leurs compteurs.

### Le chargeur du témoin

La tranche des risques et des avenants s'insère dans la marche des événements (`witness`), aux
instants de la chronologie : le 12 janvier 2026, la déclaration des trois risques ouvre la révision
101, copie de l'offre 100 ; leurs devis propres et l'avenant 1 sont remplis ; le 1er février, la
fusion de l'avenant 1 (`load_merge`) marque 101 et en fait la référence ; le 2 février, un réexamen
ouvre 102 ; le 20 février, la survenance de 752 ; l'avenant 2 est ouvert et rempli dans 102.

Le remplissage direct des tâches et des lignes de 101 (EP-06, EP-07) devient celui de l'avenant 1 :
ce qui sépare l'offre de la référence, que `wftools.mockhistory` décrit déjà pour engendrer
`comparison`. Ce que la fusion produit est comparé aux exemples de 101 ; un désaccord est arbitré
par la spécification, et la fixture se corrige. La désignation de l'offre 100 le 15 janvier reste.
`load_merge` met l'avenant à jour avant de le fusionner quand la marche des événements a écrit la
structure principale depuis son ouverture, par la fonction de la mise à jour, sans compte rendu.
Les lots d'EP-07, EP-09 et EP-10 qui listent des écarts « à la référence près » voient ces listes
retirées par le lot du témoin.

### Le front

Les écrans existent (EP-15, EP-17, EP-25) et suivent les commandes que le service rend. Quatre
changements de code : le geste « Abandonner l'avenant » et son action de serveur ; la relecture du
risque après une écriture dans son devis propre (#1626) ; le gestionnaire de la promesse du filtre
d'origine (#1972) ; l'avenant en retard — l'écran le dit, offre « Mettre à jour l'avenant », en
présente le compte rendu avant de confirmer, et n'offre « Contractualiser l'avenant » que sur un
avenant à jour (reprise du 2026-11-19). Le reste est la levée des gardes `inService` des parcours et la mise à jour du
guide.

### Les tests du back

Les exemples chiffrés du §3.4.5.6 et ceux de WF-REV-0050, WF-IND-0030 et WF-IND-0100 qui citent un
risque survenu, une fusion ou un avenant entrent au harnais d'exemples (`fixtures/examples.json`),
chacun citant son exigence. Un jeu de fabriques commun aux lots — un projet chiffré à 1 000, un
risque de gravité 200 à 30 %, un différentiel — est écrit par le socle, pour que chaque lot ne
bâtisse pas le sien. Le socle de la mise à jour (US-3050) y ajoute un différentiel en retard : la
structure principale a reçu depuis son ouverture une tâche, un libellé changé, une ligne réestimée
et une tâche retirée, et le différentiel désigne de son côté un ajout, une modification et un
retrait.

### L'ordre de construction

1. **Le socle, et ce qui ne l'attend pas**, en parallèle : le socle (US-2550) ; le contrat
   (`deleteCostStructure`, le refus de `setNodeTracking`, la variante de la couverture) ; les
   constats sans lien avec les risques (US-2660).
2. **Les structures et le risque** : les différentiels (US-2550) ; la déclaration, le devis propre
   et la ligne de provision (US-2570, US-2580).
3. **Ce qui lit ou écrit un risque déclaré** : les réexamens et l'annulation (US-2590), le registre
   et la matrice (US-2600), la réserve et la couverture (US-2610) ; à côté, le compte rendu de la
   fusion (US-2560), puis la base d'un différentiel et sa mise à jour (US-3050) — le contrat, la
   base et la lecture contre elle, la mise à jour —, puis l'application de la fusion (US-2560).
4. **La survenance** (US-2620), sur la greffe et la couverture ; **les indicateurs** (US-2630), sur
   la fusion, la survenance et la couverture.
5. **Les écrans** (US-2640), puis **le témoin** (US-2650), qui attend tout le back, et **la
   vérification d'ensemble**, seule : le parcours du chef de projet, la définition de fini, les
   mesures rejouées.

---

## US-2550 — Les structures différentielles : ouvrir, saisir, importer, abandonner

- **statut** : fini
- **exigences** : `WF-REV-0100-A`, `WF-DEV-0050-A`, `WF-INTF-0100-A`
- **opérations** : `createCostStructure`, `listCostStructures`, `updateCostStructure`,
  `deleteCostStructure` (nouvelle, écrite par la conception), `createRevision` ; sur un
  différentiel, les lectures et les écritures de l'arbre (`listNodes`, `createNode`,
  `updateTaskFacet`, `updateEstimateLine`, `setPredecessors`, `moveNodes`, `deleteNode`,
  `previewPaste`, `applyPaste`, `undoLastChange`), `openImport`, `applyImport` ; `setNodeTracking`,
  `generatePlanningSkeleton` (les refus)
- **issue** : #3810
**En tant que** chef de projet, **je veux** ouvrir une structure différentielle, copie de la
structure principale de la révision en cours, y saisir et y importer ce qu'un avenant change sans
toucher à la principale, en préparer plusieurs à la fois, et abandonner celle qui ne se signera pas,
**afin de** négocier un écart sans déplacer ni le planning suivi ni la référence.

**Critères d'acceptation.**

- `WF-REV-0100-A` — « La première révision d'un projet comporte, à sa création, une structure
  principale et aucune autre ; une révision créée à partir d'une révision marquée en reprend toutes
  les structures, différentielles et propres des risques comprises, hors les structures
  différentielles déjà fusionnées et les structures propres des risques survenus (WF-REV-0010,
  WF-REV-0050, WF-RIS-0060). » : la principale seule à la première révision, tenu par EP-04 ; la
  copie d'une révision marquée reprend, par `register_copy`, ses différentiels non fusionnés et les
  devis propres de ses risques identifiés ou écartés, avec leurs tâches, leurs lignes et leurs
  images, leurs lignées conservées, et ne reprend ni un différentiel fusionné ni le devis propre
  d'un risque survenu (E-04, #1758) ; le nombre de lignes de chaque table qui porte la révision
  nouvelle est celui de la révision marquée hors ces structures (WF-DAT-0010) ; la non-reprise après
  une fusion et après une survenance s'éprouve avec US-2560 et US-2620 ;
- `WF-REV-0100-A` — « Deux structures différentielles coexistent dans une même révision, et la
  fusion de l'une laisse l'autre intacte. » : deux différentiels ouverts dans la même révision ont
  chacun leur compteur et leur libellé, qui n'est pas unique ; une saisie dans l'un ne change ni
  l'autre ni la principale ; l'abandon de l'un laisse l'autre intact ; la fusion de l'un, qui laisse
  l'autre intact et repris par la révision suivante, est éprouvée par US-2560 ;
- `WF-REV-0100-A` — « Un risque déclaré ajoute une structure propre, présente dans chaque révision
  marquée postérieure tant qu'il n'est pas survenu. » : tenu par US-2570, qui crée le devis propre
  avec le risque ;
- `WF-DEV-0050-A` — « La création d'une tâche depuis la grille de devis la fait apparaître dans la
  grille de planning, en mode automatique, d'une durée d'un jour et sans prédécesseur, et le
  déplacement d'un sous-arbre depuis l'une se répercute dans l'autre. » : tenu par EP-07, non touché
  ici ; les mêmes opérations écrivent un différentiel ;
- `WF-DEV-0050-A` — « Le montant d'une récapitulative suit celui de ses subordonnées et n'est pas
  modifiable. » : tenu par EP-07, non touché ici ;
- `WF-DEV-0050-A` — « La grille de devis ne présente pas le montant budgété ; une ligne dont la
  tâche se place deux ans après l'année de référence, avec une inflation de 2 %, affiche un montant
  réestimé supérieur de 4,04 % à son montant aux taux de l'année de référence. » : tenu par EP-07,
  et par le test du harnais d'EP-10 pour le 4,04 % (#2893), non touché ici ;
- `WF-DEV-0050-A` — « Dans la structure principale, la création d'une ligne sous une tâche terminée,
  ou le déplacement d'une ligne vers elle, est refusé. » : tenu par EP-07 (`task_not_completed`),
  non touché ici ; la phrase passe à WF-RAE-0040 par la spécification 1.0.7 (#3372) ;
- écart : `WF-DEV-0050-A` — « Dans un différentiel, la modification de la quantité d’une ligne d’une
  tâche terminée aboutit, et la fusion lui donne ce montant budgété. » : réécrit par la
  spécification 1.0.7 (#3372) : le refus dans la structure principale se lit dans WF-RAE-0040 ;
- `WF-DEV-0050-A` — « La grille de devis ne propose la saisie ni de la durée ni des prédécesseurs
  d'une tâche. » : tenu par EP-07, non touché ici ;
- `WF-DEV-0050-A` — « Sur un projet En cours, la grille de devis de la structure principale ne
  propose aucune saisie ni aucune commande d'écriture ; celle d'une structure différentielle les
  propose. » : sur un projet En cours, `edit_estimate` de la structure principale est indisponible
  (`project_before_in_progress`, tenu par EP-07) et celui d'un différentiel est disponible : ses
  écritures aboutissent ; l'écran est d'US-2640 ;
- `WF-INTF-0100-A` — « On importe un fichier qui comporte des lignes de main-d'œuvre et des lignes
  hors main-d'œuvre. » : tenu par EP-07, non touché ici ;
- `WF-INTF-0100-A` — « Chaque ligne se retrouve sous la tâche désignée, avec sa quantité, ses heures
  ou son débours, son rôle et, le cas échéant, son sous-projet. » : tenu par EP-07, non touché ici ;
- `WF-INTF-0100-A` — « Un second import du même fichier donne un devis identique. » : tenu par
  EP-07, non touché ici ;
- `WF-INTF-0100-A` — « Un fichier exporté, dont une charge a été modifiée, réimporté sur un projet
  qui porte une révision de référence sans être encore En cours met à jour cette ligne sans changer
  son montant budgété ni sa lignée. » : tenu par EP-07, non touché ici ;
- `WF-INTF-0100-A` — « Une ligne qui cite une tâche, un rôle ou un sous-projet inconnu, ou qui
  laisserait une tâche sans aucune heure travaillée dans la semaine (WF-PLA-0010), est rejetée et
  figure au compte rendu (WF-INTF-0080). » : tenu par EP-07, non touché ici ;
- `WF-INTF-0100-A` — « Une ligne d'une tâche démarrée dont le sous-projet a reçu des coûts réels,
  que le fichier place sous un autre sous-projet ou laisse sans sous-projet, est rejetée, et le
  compte rendu nomme ce sous-projet. » : tenu par EP-07 pour la règle et par EP-09 pour son premier
  rejet (`SUBPROJECT_HAS_ACTUAL_COSTS`), non touché ici ;
- `WF-INTF-0100-A` — « Un devis exporté d'une révision marquée puis réimporté dans la révision en
  cours met à jour les lignes de même lignée sans en créer aucune. » : tenu par EP-07, non touché
  ici ;
- `WF-INTF-0100-A` — « Un fichier d'où une ligne de provision a été retirée laisse cette ligne en
  place ; une ligne de catégorie de provision sans identifiant est rejetée au compte rendu. » : le
  rejet par `PROVISION_CATEGORY_RESERVED` est tenu par EP-07 ; la ligne de provision laissée en
  place (`kept`, `provision_lines`) est tenue par US-2580 ;
- `WF-INTF-0100-A` — « Sur un projet En cours, l'import d'un devis sur la structure principale est
  refusé et nomme la condition ; sur une structure différentielle, il aboutit. » : le refus sur la
  principale est tenu par EP-07 (`project_before_in_progress`) ; sur un différentiel du même projet,
  `openImport` puis `applyImport` d'un devis aboutissent, et seule la structure visée
  (`structure_id`) est écrite ;
- `WF-INTF-0100-A` — « Un fichier qui recopie une ligne avec sa lignée voit les deux lignes
  rejetées, et la ligne existante inchangée. » : tenu par EP-07, non touché ici ;
- propre à l'US : `createCostStructure`, sous la commande `create_structure` de la révision, ouvre
  un différentiel, copie de la structure principale, date de début de planning comprise : à sa
  création chacun de ses nœuds est celui de la principale, par sa lignée, et se lit `unchanged`
  (`NodeDifference`) ; il est refusé par 409 sur une révision marquée (`revision_draft`) et pendant
  un traitement de fond (`no_background_task_running`) ; `listCostStructures` rend la principale,
  les différentiels et les devis propres de la révision lue, chacun avec sa nature, `is_merged` et
  ses commandes (#1369) ;
- propre à l'US : les grilles de planning et de devis lisent et écrivent un différentiel par les
  opérations de la principale, ses saisies entrant à l'historique annulable (WF-IHM-0110) ; un
  différentiel n'a ni reste à engager ni avancement (`edit_remaining` est de la principale seule),
  et la comparaison n'y est pas offerte (WF-IHM-0150, tenu par EP-27) ;
- propre à l'US : `deleteCostStructure` abandonne un différentiel non fusionné de la révision en
  cours, avec le compteur lu (412 sinon) : ses tâches, ses lignes et ses images disparaissent, les
  autres structures sont inchangées, et la révision suivante ne le connaît plus ; il est refusé par
  409 sur la structure principale, sur le devis propre d'un risque, sur un différentiel fusionné,
  sur une révision marquée et pendant un traitement de fond ; sa forme, sa commande et ses exemples
  sont ceux que la conception écrit au contrat (décision de l'auteur du 2026-11-17) ;
- propre à l'US : `setNodeTracking` sur un nœud d'une structure autre que la principale est refusé,
  par le refus que la conception ajoute au contrat (#2497, décision de l'auteur du 2026-11-08), et
  deux écritures d'inscriptions d'une même lignée sous deux structures sont sérialisées : aucune ne
  finit en 500 (#2499) ;
- propre à l'US : `main_structure_without_tasks` juge la seule structure principale : une révision
  dont seul un différentiel porte une tâche liste `generate_skeleton` disponible (#2541) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Le différentiel est une copie de la principale (`createCostStructure`), et
la fusion n'y lit que ce qui a changé depuis (US-2560). `docs/api/DECISIONS.md` : « Le devis
principal en réalisation et sous une tâche terminée ; le différentiel rebudgète » (F-01), « La
révision suivante ne reprend pas une structure fusionnée » (E-04), « Les révisions et les structures
» (E-01, E-09). La nature d'une structure n'admet aujourd'hui que `main`
(`core/revisions/tables.py`) : la migration qui l'élargit est du socle de l'EPIC.

**Hors périmètre.** La fusion et son compte rendu (US-2560) ; le devis propre d'un risque (US-2570)
; les écrans (US-2640).

---

## US-2560 — La fusion d'un différentiel : compte rendu, confirmation, révision marquée et nouvelle référence

- **statut** : en cours
- **exigences** : `WF-REV-0050-A`, `WF-REV-0040-A`, `WF-PLA-0170-A`, `WF-ADM-0100-A`,
  `WF-REV-0080-A`
- **opérations** : `getStructureMergeReport`, `mergeCostStructure`, `getBackgroundTask`,
  `getRevision`, `listRevisions`, `designateReferenceRevision`, `compareRevisions`
- **issue** : #3817
**En tant que** chef de projet, **je veux** lire ce que la fusion d'un différentiel ferait de la
structure principale, puis la confirmer sous un nom de version, **afin que** l'avenant
contractualisé devienne la référence en une seule opération, sans perdre ni l'identité des tâches,
ni ce qui a été réestimé, ni ce qui a été fait.

**Critères d'acceptation.**

- `WF-REV-0050-A` — « Après fusion, la structure principale comporte les tâches ajoutées, les
  valeurs modifiées et plus aucune des tâches retirées. » : après la fusion, la structure principale
  porte les tâches et les lignes que le différentiel ajoute, sous des lignées nouvelles, les valeurs
  qu'il modifie, et plus aucune des tâches non démarrées qu'il retire ; ce que la fusion écrit est
  ce que le compte rendu a présenté ;
- `WF-REV-0050-A` — « Les tâches inchangées conservent leur identité et leur état. » : une tâche que
  le différentiel ne touche pas garde sa lignée, son état, son avancement et ses inscriptions ;
- `WF-REV-0050-A` — « Une tâche démarrée désignée comme retirée par un différentiel est conservée,
  son reste à engager est nul, et le montant budgété de ses lignes est inchangé après la fusion :
  terminée, elle l’acquiert. » : la tâche est conservée, le reste à engager de ses lignes est nul,
  elle est terminée à la date de la fusion, et ses lignes gardent leur budgété : la valeur que la
  tâche porte est inchangée, et elle l'acquiert en se terminant (décision de l'auteur du 2026-11-17
  ; un constat de spécification demande de préciser la phrase) ;
- `WF-REV-0050-A` — « Une ligne réestimée à 140 pour un montant budgété de 100, non désignée par le
  différentiel, porte toujours 100 et 140 après la fusion. » : la ligne porte 100 de budgété et 140
  de réestimé après la fusion ;
- `WF-REV-0050-A` — « Une ligne ajoutée en revue périodique, non désignée par le différentiel, garde
  un montant budgété nul. » : une ligne ajoutée en revue périodique, à budgété nul, que le
  différentiel ne désigne pas, garde un budgété nul ;
- `WF-REV-0050-A` — « La fusion demande un nom de version, et la révision produite le porte. » :
  `StructureMerge.version_name` est exigé, unique parmi les révisions marquées du projet
  (WF-REV-0020), la description facultative ; la révision que la fusion marque les porte ;
- `WF-REV-0050-A` — « Après fusion, le projet ne comporte plus de révision en cours. » : la fusion
  marque la révision en cours dans la même opération ; sur un projet sans révision en cours, elle en
  crée une par copie de la dernière révision marquée, aux taux conservés, projetés (WF-REV-0060), y
  fusionne la copie du différentiel et la marque (`creates_current_revision`) ;
- `WF-REV-0050-A` — « Le compte rendu d'une fusion dont le différentiel retire une tâche démarrée
  nomme cette tâche comme terminée ; l'abandon à cette étape laisse la révision en cours et la
  référence inchangées. » : `getStructureMergeReport` nomme la tâche parmi celles que la fusion
  termine (`ImportCompletedTask`) ; ne pas confirmer n'écrit rien : la révision en cours, ses
  compteurs et la référence sont inchangés ;
- `WF-REV-0040-A` — « La désignation manuelle est proposée tant que le projet n'a ni coût réel ni
  révision marquée depuis la dernière désignation, et refusée au-delà. » : tenu par EP-04
  (`reference_correctable`) et par EP-09 pour le coût réel reçu ; après une fusion, une révision a
  été marquée depuis la dernière désignation, et la désignation manuelle est refusée par 409 ;
- `WF-REV-0040-A` — « Un projet dont les offres v2 puis v3 sont marquées, et dont v2 a été désignée
  par erreur, accepte la désignation de v3 tant qu'il n'a reçu aucun coût réel. » : tenu par EP-04
  et EP-09, non touché ici ;
- `WF-REV-0040-A` — « Après contractualisation d'un avenant, la révision produite est la référence
  sans intervention de l'utilisateur, et l'ancienne reste consultable. » : la révision que la fusion
  marque est la référence dans la même opération, sans appel à `designateReferenceRevision` ;
  l'ancienne référence reste dans l'historique, lisible en entier, sans caractère de référence ; ce
  qui suit une désignation (`register_designation`) est prévenu de la nouvelle ;
- `WF-PLA-0170-A` — « Une feuille peut être rattachée à un poste ; une récapitulative rattachée dont
  on supprime la dernière subordonnée garde son rattachement. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0170-A` — « Le rattachement d'une tâche à un poste déjà porté par une autre est refusé,
  comme celui d'une même tâche à un lot et à un poste. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0170-A` — « Le déplacement de la tâche d'un poste hors du sous-arbre de la tâche de son
  lot est refusé. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0170-A` — « La suppression d'un poste porté par une tâche de la révision en cours aboutit
  ; la tâche reste et ne porte plus de rattachement ; une révision marquée qui la citait l'affiche
  toujours rattachée. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0170-A` — « Après suppression d'un poste sur un projet sans révision en cours, la révision
  créée ensuite ne porte plus ce rattachement ; la révision marquée l'affiche toujours. » : tenu par
  EP-06, non touché ici ;
- `WF-PLA-0170-A` — « La génération du squelette n'est pas proposée sur le devis propre d'un risque.
  » : la commande est de la révision et n'engendre que sur la structure principale (tenu par EP-06)
  ; éprouvé ici sur une révision qui porte un devis propre et un différentiel : ni l'un ni l'autre
  n'est écrit par `generatePlanningSkeleton`, et aucune commande de ces structures ne le propose ;
- `WF-PLA-0170-A` — « La fusion d'un différentiel qui déplacerait la tâche d'un poste hors du
  sous-arbre de la tâche de son lot est refusée en nommant la tâche. » : le compte rendu porte le
  motif `ORDER_ITEM_OUTSIDE_WORK_PACKAGE` en nommant la tâche (`ReportRefusal`), et la tâche de fond
  d'une fusion confirmée malgré lui finit en échec sans rien fusionner ;
- `WF-PLA-0170-A` — « Une tâche rattachée au poste 2 dont un différentiel allonge la durée porte
  toujours ce rattachement après la fusion. » : la tâche garde son rattachement au poste 2 après la
  fusion ;
- écart : `WF-ADM-0100-A` — « Chaque fonction de second niveau de l’arborescence est représentée par
  ses deux permissions, ou par la seule permission de consulter pour FBS-1.3, FBS-1.5, FBS-2.1 à
  FBS-2.7, FBS-4.8 et FBS-4.9. » : réécrit par la spécification 1.0.7 (#3354) : FBS-4.8 et FBS-4.9
  n'ont que la permission de consulter, quand le livré leur donne encore celle de modifier ; #3975
  l'éprouve ;
- `WF-ADM-0100-A` — « Un rôle disposant de la modification du chiffrage mais non du marquage permet
  de modifier un devis et refuse de marquer la révision ; un rôle disposant du marquage mais non de
  la fusion refuse de fusionner un différentiel. » : la première moitié est tenue par EP-04 et EP-07
  ; un rôle qui a le marquage sans `structure_merge` ne liste pas `merge_structure` disponible et
  reçoit 403 de `mergeCostStructure` ;
- `WF-ADM-0100-A` — « Un utilisateur sans la permission de créer un projet n'en crée pas. » : tenu
  par EP-04, non touché ici ;
- `WF-ADM-0100-A` — « Aucun écran ne permet de créer une permission. » : tenu par EP-03, non touché
  ici ;
- `WF-REV-0080-A` — « La comparaison d'une révision obtenue par fusion d'un différentiel avec la
  révision marquée qui la précède, de même année de référence, lorsqu'aucune autre modification n'a
  été faite entre les deux, restitue exactement les tâches et les montants budgétés de ce
  différentiel. » : `compareRevisions` de la révision marquée par une fusion à la révision marquée
  qui la précède rend les tâches et les lignes ajoutées, retirées et modifiées du différentiel, et
  `budgeted_delta` ses montants budgétés, tels que le compte rendu les a présentés ;
- `WF-REV-0080-A` — « Les montants réestimés n'y diffèrent que par les lignes que le différentiel
  ajoute ou retire, par celles des tâches démarrées qu'il termine et par celles dont il change
  l'année de consommation ; une ligne existante dont le différentiel ne modifie que le montant
  budgété ne présente aucun écart de montant réestimé. » : `reestimated_delta` ne vient que des
  lignes ajoutées ou retirées, de celles des tâches démarrées que la fusion termine et de celles
  dont l'année de consommation change ; une ligne dont seul le budgété change n'a aucun écart de
  réestimé ;
- écart : `WF-REV-0080-A` — « Entre deux révisions d’années de référence différentes, les montants
  réestimés diffèrent en outre sur chaque ligne dont le taux a été mis à jour ou projeté jusqu’à la
  nouvelle année de référence (WF-REV-0060) ; une ligne de débours, dont le débours unitaire est
  projeté de même, n’y présente aucun écart de montant réestimé ; les tâches et les montants
  budgétés restent ceux du différentiel. » : réécrit par la spécification 1.0.7 (#3366) ; une ligne
  de débours ne présente plus d'écart, son débours étant projeté ; #3983 l'éprouve ;
- `WF-REV-0080-A` — « Une tâche déplacée sous une autre récapitulative est présentée modifiée. » :
  tenu par EP-07 et EP-27, non touché ici ;
- `WF-REV-0080-A` — « La révision en cours se compare à la révision marquée dont elle est issue :
  une tâche dont la fin y est repoussée de cinq jours est présentée modifiée, avec la date de fin de
  la base ; la date ramenée à celle de la base, la tâche n'est plus présentée modifiée. » : tenu par
  EP-27, non touché ici ;
- `WF-REV-0080-A` — « La comparaison d'une révision marquée à une révision marquée postérieure
  présente retirées les tâches que la seconde ajoute. » : tenu par EP-27, non touché ici ;
- `WF-REV-0080-A` — « Une révision en cours prise pour base est refusée. » : tenu par EP-27, non
  touché ici ;
- `WF-REV-0080-A` — « Un utilisateur qui consulte le planning sans consulter les révisions y active
  une comparaison. » : tenu par EP-27, non touché ici ;
- propre à l'US : `getStructureMergeReport` est une lecture qui n'écrit rien : les écarts du
  différentiel à la principale (`ImportDifference`), les tâches démarrées que la fusion termine, les
  motifs qui la refusent — `LINK_CYCLE`, `PROJECT_HORIZON_EXCEEDED`, `LINK_FORBIDDEN`,
  `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, chacun avec les paramètres que le contrat dit —, les compteurs
  lus de la principale et du différentiel, et `creates_current_revision` ; une structure qui n'est
  pas un différentiel fusionnable reçoit le 409 de sa fusion ;
- propre à l'US : `mergeCostStructure` exige les compteurs lus et `creates_current_revision` tel que
  lu : l'un ou l'autre changé depuis, 412 `STALE_LOCK_VERSION`, rien n'est fusionné ; les conditions
  de la commande `merge_structure` sont nommées dans l'ordre du contrat (`project_not_terminal`,
  `no_background_task_running`, `unmerged_amendment_exists`, `may_create_revision`,
  `revision_draft`), et sur la dernière révision marquée d'un projet sans révision en cours la
  fusion est offerte ;
- propre à l'US : la fusion est une tâche de fond et une seule opération : pendant qu'elle court,
  les écritures de la révision nomment `no_background_task_running` ; en échec, sur un motif de
  refus ou tout autre, elle ne laisse ni fusion, ni révision marquée, ni révision créée ;
- propre à l'US : la fusion fait tout ce que fait un marquage — les images du référentiel, la
  conservation des indicateurs et des courbes (`register_marking`, `register_indicators`, EP-10),
  l'historique annulable de la révision fini — et s'inscrit au journal ; aucune commande ne l'annule
  (WF-IHM-0110, US-2590) ;
- propre à l'US : une ligne de provision dont la fusion retire la tâche passe sur la tâche parente,
  et le compte rendu le signale (WF-RIS-0010, US-2580) ; la trace d'un risque survenu
  (`origin_risk_id`) traverse la fusion (US-2620) ;
- propre à l'US : le différentiel fusionné se lit `is_merged` dans la révision marquée et n'est pas
  repris par la suivante ; un autre différentiel de la même révision est intact, repris par la
  révision suivante, et reste fusionnable (WF-REV-0100, US-2550) ;
- propre à l'US : la fusion n'applique que ce que le différentiel désigne (#4034, reprise du
  2026-11-19) : une tâche ajoutée à la structure principale après l'ouverture du différentiel, que
  celui-ci ne désigne pas, figure toujours dans la structure principale après la fusion ; une ligne
  réestimée à 140 après l'ouverture, pour un montant budgété de 100, non désignée, porte toujours
  100 et 140 ; une ligne que le différentiel porte à 120 et que la principale a réestimée à 140
  depuis porte 120 de budgété et 140 de réestimé ; de deux différentiels ouverts le même jour, la
  fusion du second, mis à jour dans la révision suivante, laisse dans la structure principale tout
  ce que la fusion du premier y a apporté ;
- propre à l'US : `getStructureMergeReport` et `mergeCostStructure` d'un différentiel en retard
  sont refusés par 409 `STATE_FORBIDS_OPERATION`, la condition nouvelle que le contrat ajoute,
  nommée après les autres ; sur un différentiel à jour, le compte rendu est celui d'US-2560/L1,
  inchangé ; une écriture de la structure principale entre le compte rendu et la confirmation est
  un 412, et rien n'est fusionné (US-3050) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** La fusion compare un différentiel à jour à la structure principale, en
deux voies : c'est sa base, que la mise à jour vient de reprendre (US-3050), qui fait de cet écart
ce que le différentiel désigne. La spécification le dira par #4132 ; d'ici là, les deux critères
ci-dessus sont propres à l'US. `docs/api/DECISIONS.md` : « La fusion : cycle, horizon, et fusion sans
révision en cours » (#1331), « Les révisions et les structures » (E-04, E-10 : la description à la
fusion, les grandeurs qu'elle donne), « Le réestimé après une fusion, selon l'année de référence »
(E-02). La marque d'une ligne réestimée, que la fusion épargne, est écrite par EP-09 (US-1580). Les
exemples du témoin sont ceux de l'avenant 2 (`structure_merge_report` et ses variantes).

**Hors périmètre.** Les indicateurs lus devant un avenant — la marche de la courbe, la valeur
planifiée (US-2630) ; la réserve à une nouvelle référence (US-2610) ; les écrans (US-2640) ; la base
d'un différentiel et sa mise à jour (US-3050).

---

## US-3050 — La base d'un différentiel et sa mise à jour depuis la structure principale

- **statut** : à faire
- **exigences** : `WF-REV-0100-A`
- **opérations** : `getStructureRebaseReport`, `rebaseCostStructure` (nouvelles, écrites par la
  conception), `createCostStructure`, `listCostStructures`, `deleteCostStructure`, `createRevision`,
  `listNodes` sur un différentiel, `getStructureMergeReport`, `mergeCostStructure` (leur refus)
- **issue** : #4143
**En tant que** chef de projet, **je veux** qu'un avenant préparé pendant que le projet avance ne
désigne que ce que j'y ai changé, et le remettre au niveau de la structure principale quand elle a
bougé, **afin de** le négocier sur plusieurs revues et de le contractualiser sans défaire ce que le
projet a reçu entre-temps.

**Critères d'acceptation.**

- `WF-REV-0100-A` — « La première révision d'un projet comporte, à sa création, une structure
  principale et aucune autre ; une révision créée à partir d'une révision marquée en reprend toutes
  les structures, différentielles et propres des risques comprises, hors les structures
  différentielles déjà fusionnées et les structures propres des risques survenus (WF-REV-0010,
  WF-REV-0050, WF-RIS-0060). » : tenu par EP-04 et US-2550 ; ici, la copie d'une révision marquée
  reprend avec chaque différentiel non fusionné sa base, sous la lignée de sa structure, et son
  état, à jour ou en retard ; elle ne reprend pas la base d'un différentiel fusionné ; le nombre de
  lignes de chaque table qui porte la révision nouvelle est celui de la révision marquée hors les
  différentiels fusionnés et leurs bases (WF-DAT-0010) ;
- `WF-REV-0100-A` — « Deux structures différentielles coexistent dans une même révision, et la
  fusion de l'une laisse l'autre intacte. » : tenu par US-2550 et US-2560 ; ici, après la fusion de
  l'une, l'autre, reprise par la révision suivante, est en retard ; mise à jour, elle porte ce que
  la première a apporté à la structure principale, sans le désigner, et ce qu'elle désignait est
  inchangé — éprouvé avec US-2560, qui fusionne ;
- `WF-REV-0100-A` — « Un risque déclaré ajoute une structure propre, présente dans chaque révision
  marquée postérieure tant qu'il n'est pas survenu. » : tenu par US-2570, non touché ici ; un devis
  propre n'a ni base ni mise à jour (EP-30) ;
- propre à l'US : `createCostStructure` crée avec le différentiel sa base, copie de la structure
  principale au même instant ; `listCostStructures` ne la rend pas, et toute opération qui la nomme
  par son identifiant répond 404 ; `deleteCostStructure` la supprime avec son différentiel ; une
  révision qui porte une base liste `generate_skeleton` et ses autres commandes comme sans elle, et
  ses indicateurs sont les mêmes ;
- propre à l'US : `listNodes` d'un différentiel le compare à sa base : après une tâche ajoutée, un
  libellé changé, une ligne réestimée et une tâche retirée dans la structure principale, le
  différentiel présente `added`, `modified` et `removed` les seuls nœuds qu'il a écrits, et
  `unchanged` tous les autres ; la ligne de provision d'un risque de la structure principale n'y est
  pas présentée retirée (#4035) ; un différentiel fusionné se relit, dans la révision que sa fusion
  a marquée, contre la base qu'il avait à sa fusion ;
- propre à l'US : `CostStructure` dit un différentiel à jour à son ouverture et après sa mise à
  jour, en retard dès qu'une écriture avance le compteur de la structure principale, et rend nul
  cet état pour la structure principale et pour un devis propre ; la commande de mise à jour est
  listée sur un différentiel non fusionné, disponible s'il est en retard ;
- propre à l'US : `getStructureRebaseReport` est une lecture qui n'écrit rien : ce que la mise à
  jour reporterait de la structure principale dans le différentiel — tâches, liaisons et lignes
  ajoutées, modifiées avec leurs champs, retirées —, ce que le différentiel garde contre elle
  (`kept`), les motifs qui la refusent et les compteurs lus des deux structures ; une structure qui
  n'est pas un différentiel en retard de la révision en cours reçoit le 409 de sa mise à jour ;
- propre à l'US : `rebaseCostStructure`, avec les compteurs lus, écrit ce que le compte rendu a
  présenté : la tâche ajoutée à la structure principale est dans le différentiel sous sa lignée, à
  sa place, le libellé et la réestimation qu'il ne désignait pas y sont, la tâche retirée n'y est
  plus, et tous se lisent `unchanged` ; les nœuds qu'il désignait se lisent comme avant, sous leur
  identifiant ; le différentiel est à jour, et la structure principale n'est pas écrite ; un
  compteur changé depuis la lecture, 412 `STALE_LOCK_VERSION`, rien n'est écrit ;
- propre à l'US : une valeur que le différentiel désigne et que la structure principale a changée
  depuis garde la valeur du différentiel, et le compte rendu la nomme (`kept`, ses champs) ; une
  tâche que le différentiel modifie et que la structure principale n'a plus reste au différentiel,
  qui la présente ensuite `added`, signalée de même ; une tâche qu'il ajoute sous une tâche que la
  structure principale n'a plus passe sous l'ancêtre le plus proche qui reste, signalée ; une
  liaison qu'il ajoute vers une tâche que la structure principale n'a plus est retirée, signalée ;
- propre à l'US : une mise à jour qui laisserait dans le différentiel une boucle de liaisons, une
  liaison interdite, une date au-delà de l'horizon ou une tâche sans heure travaillée est refusée,
  le motif et la tâche nommés au compte rendu (`ReportRefusal`), et rien n'est écrit ; le lien
  fautif retiré du différentiel, elle aboutit ;
- propre à l'US : `rebaseCostStructure` est refusé par 409 sur la structure principale, sur un devis
  propre, sur un différentiel fusionné, sur une révision marquée, pendant un traitement de fond et
  sur un différentiel à jour, la première condition qui manque nommée dans l'ordre du contrat ; il
  est gardé par la permission de `create_structure` ;
- propre à l'US : la mise à jour n'entre pas à l'historique annulable ; une saisie du différentiel
  faite avant elle s'annule encore, sauf sur un nœud qu'elle a écrit, où l'annulation est refusée
  en nommant l'objet (WF-IHM-0110) ; un autre différentiel de la révision et son état sont
  inchangés ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Écrite à la reprise du 2026-11-19 (#4034) : la conception, « La base d'un
différentiel et sa mise à jour », dit la forme de la base, ce qu'une structure désigne et les
quatre règles de ce qu'une mise à jour ne reporte pas. La spécification 1.0.7 ne dit ni la base ni
la mise à jour : #4132 en propose le texte, et les critères ci-dessus sont propres à l'US jusqu'à
sa révision. La lecture d'un différentiel (`compare_differential`, US-2550/L3) et le compte rendu
d'une fusion (`merge_plan`, `merge_lines`, US-2560/L1) comparent deux structures par la lignée : ce
qu'une structure désigne est le même calcul, la base à la place de la structure principale. La copie
d'une structure dans une autre (`copy_structure_nodes`) pose la base comme elle pose le
différentiel. Ce que la structure désigne et son report ne nomment pas la nature « avenant » : EP-30
les reprend pour le devis propre d'un risque.

**Hors périmètre.** La fusion et son compte rendu (US-2560) ; les écrans (US-2640) ; la base et la
mise à jour du devis propre d'un risque (EP-30).

---

## US-2570 — Déclarer un risque et chiffrer son devis propre

- **statut** : fini
- **exigences** : `WF-RIS-0030-A`, `WF-REF-0030-A`, `WF-INTF-0090-A`
- **opérations** : `createRisk`, `getRisk`, `updateRisk`, `listCostStructures` ; sur le devis
  propre, les lectures et les écritures de l'arbre (`listNodes`, `createNode`, `updateTaskFacet`,
  `updateEstimateLine`, `setPredecessors`, `moveNodes`, `deleteNode`, `previewPaste`, `applyPaste`),
  `openImport`, `applyImport`
- **issue** : #3812
**En tant que** chef de projet, **je veux** déclarer un risque — son libellé, sa description, ses
actions de mitigation, sa probabilité — et décrire dans un devis à part ce qu'il coûterait s'il
survenait, **afin que** sa gravité soit un chiffrage et non une affirmation.

**Critères d'acceptation.**

- `WF-RIS-0030-A` — « La grille de devis d'un risque offre les mêmes opérations que celle du projet.
  » : le devis propre se lit et s'écrit par les opérations de la structure principale, sous
  `edit_planning` et `edit_estimate` de sa structure, de nature `risk`, à tout état non terminal du
  projet, En cours compris ; il n'a ni avancement ni reste à engager ;
- `WF-RIS-0030-A` — « La modification du devis propre d'un risque identifié ne change ni le budget
  de référence, ni la valeur planifiée, ni la valeur acquise, ni les indices de coût et de délai ;
  elle change la provision, donc le reste à engager, l'avancement financier et la projection du chef
  de projet (WF-RAE-0010). » : la provision suit dans la même écriture (US-2580) ; les grandeurs
  lues avant et après — budget de référence, valeur planifiée, valeur acquise, indices, reste à
  engager, avancement financier, projection du chef de projet — sont éprouvées par US-2630 ;
- `WF-REF-0030-A` — « Une nature de chacun des trois types peut être créée. » : tenu par EP-05, non
  touché ici ;
- `WF-REF-0030-A` — « La création d'une nature dont le code existe déjà est refusée. » : tenu par
  EP-05, non touché ici ;
- `WF-REF-0030-A` — « La modification du type est refusée pour une nature dont une catégorie est
  employée, porte un taux ou est rattachée à un rôle de ressource. » : tenu par EP-05, non touché
  ici ;
- `WF-REF-0030-A` — « Sur une installation neuve, la nature de type provision pour risques et sa
  catégorie existent. » : tenu par EP-05, non touché ici ;
- `WF-REF-0030-A` — « Une fois saisis la catégorie de main-d'œuvre et le rôle de ressource qu'exige
  WF-CYC-0120, un projet se crée, et la déclaration d'un risque y aboutit sans qu'aucune catégorie
  de provision ait été saisie. » : sur une installation neuve où seuls la catégorie de main-d'œuvre
  et le rôle ont été saisis, le projet se crée (EP-04) et `createRisk` aboutit, sa provision sous la
  catégorie d'origine, retenue sans être demandée ;
- `WF-REF-0030-A` — « La désactivation de la dernière catégorie active de type provision pour
  risques est acceptée ; la création d'un projet (WF-CYC-0120), la déclaration d'un risque et le
  retour d'un risque écarté à l'état identifié (WF-RIS-0010) sont alors refusés. » : la
  désactivation et le refus de la création d'un projet sont tenus par EP-05 et EP-04 ; `createRisk`
  est alors refusé par 409, `active_provision_category` manquante, comme le retour d'un risque
  écarté à l'état identifié (US-2590) ;
- `WF-INTF-0090-A` — « On importe un planning MS Project, puis un devis, dans un projet qui comporte
  une révision marquée. » : tenu par EP-06 et EP-07, non touché ici ;
- `WF-INTF-0090-A` — « Seule la révision en cours est modifiée : les tâches, les dates et les
  montants de la révision marquée sont identiques avant et après chaque import. » : tenu par EP-06
  et EP-07, non touché ici ;
- `WF-INTF-0090-A` — « Un import sur un projet dont toutes les révisions sont marquées crée une
  révision en cours d'élaboration et s'y applique ; les révisions marquées sont inchangées. » : tenu
  par EP-06 et EP-07, non touché ici ;
- `WF-INTF-0090-A` — « L'import d'un planning sur la structure principale d'une révision qui porte
  un devis propre de risque laisse ce devis propre inchangé, tâches comprises ; l'import du même
  fichier sur ce devis propre laisse la structure principale inchangée. » : l'import appliqué sur la
  structure principale laisse identiques les tâches, les lignes et le compteur du devis propre ; le
  même fichier appliqué sur le devis propre (`structure_id`) laisse identiques ceux de la principale
  ;
- propre à l'US : `createRisk` est une saisie de la révision en cours, sous `edit_risks`, que la
  commande `declare_risk` annonce : sans révision en cours, il en crée une au préalable
  (`may_create_revision`), aux taux conservés, projetés (WF-REV-0060) ; il crée le risque, son
  évaluation dans la révision — sa probabilité, l'état identifié, un premier réexamen daté du jour
  —, son devis propre et sa ligne de provision (US-2580), et rend `structure_id`,
  `provision_node_id` et `provision_task` ; il est refusé par 409 sans tâche dans la structure
  principale (`at_least_one_task`) ou sans catégorie active de provision ;
- propre à l'US : la gravité est le total du devis propre, calculée, jamais saisie ; toute saisie
  dans le devis propre fait avancer `Risk.lock_version` avec le compteur de sa structure (#1453) ;
- propre à l'US : `updateRisk` écrit l'identité — libellé, description, actions de mitigation —,
  donnée du projet : il ne crée pas de révision, n'entre pas à l'historique annulable, et
  l'abandon de la révision ne le défait pas ; un nouveau libellé renomme aussi le devis propre et la
  ligne de provision de la révision en cours, hors historique, et l'ouverture d'une révision les
  nomme d'après le libellé du risque, non d'après la dernière révision marquée, qui garde les siens
  (#3980, DECISIONS) ; `getRisk` lit l'évaluation de la révision en cours ou,
  avec `revision_id`, celle qu'une révision marquée a figée (H-02, #1783) ;
- propre à l'US : un risque déclaré ajoute une structure propre que `listCostStructures` rend
  (#1369), présente dans chaque révision marquée postérieure tant qu'il n'est pas survenu
  (WF-REV-0100, US-2550) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « L'identité d'un risque, donnée du projet ; sa
provision, saisie de la révision » (H-02), « Les risques : coût à la survenance, provision de
référence, probabilité par le réexamen » (H-04 : la probabilité ne s'écrit que par le réexamen), «
Les révisions et les structures » (E-09 : le devis propre naît et disparaît avec le risque).

**Hors périmètre.** La ligne de provision (US-2580) ; les réexamens, la suppression et l'abandon
(US-2590) ; le registre (US-2600) ; la survenance (US-2620).

---

## US-2580 — La ligne de provision d'un risque identifié

- **statut** : en cours
- **exigences** : `WF-RIS-0010-A`, `WF-DEV-0010-A`, `WF-DEV-0030-A`, `WF-PRJ-0040-A`,
  `WF-PRJ-0050-A`, `WF-PLA-0040-A`, `WF-PLA-0050-A`, `WF-INTF-0120-A`
- **opérations** : `createRisk`, `updateRiskProvision`, `reviewRisk`, `listNodes`, `deleteNode`,
  `applyImport`, `setTaskProgress`, `getEstimateIndicators`, `getRemainingIndicators`
- **issue** : #3813
**En tant que** chef de projet, **je veux** que chaque risque identifié pèse sur le devis et sur le
reste à engager par une ligne de provision calculée — sa gravité pondérée par sa probabilité —,
portée par la tâche, la catégorie et le sous-projet que je désigne, **afin que** ce que les risques
font peser sur le projet se lise là où il se lirait s'ils survenaient.

**Critères d'acceptation.**

- `WF-RIS-0010-A` — « La gravité et le montant de la provision ne sont pas saisissables, et suivent
  toute modification de la structure propre ou de la probabilité. » : aucune écriture ne porte la
  gravité ni la provision, et la ligne de provision ne nomme aucun champ saisissable ; toute
  écriture du devis propre et tout réexamen de la probabilité recalculent, dans la même écriture, le
  montant de la ligne ;
- `WF-RIS-0010-A` — « Les trois états sont atteignables, et un risque écarté ne pèse plus sur le
  devis. » : les transitions sont d'US-2590 ; ici, un risque écarté n'a plus de ligne de provision,
  et le total du devis baisse de son montant ;
- `WF-RIS-0010-A` — « La confirmation d'un risque sans modification produit un réexamen daté. » :
  tenu par US-2590 ;
- `WF-RIS-0010-A` — « Un risque déclaré sans désignation de tâche porte sa provision sur la première
  tâche de premier niveau ; la ligne peut être déplacée sur une autre tâche de la structure
  principale, et le total du devis est inchangé. » : sans `provision_task_id`, la ligne est sous la
  première tâche de premier niveau ; `updateRiskProvision` la déplace sous une autre tâche de la
  structure principale, et le total du devis est le même ;
- `WF-RIS-0010-A` — « Sur une révision sans tâche, la déclaration d'un risque est refusée, de même
  que le retour d'un risque écarté à l'état identifié ; l'une et l'autre aboutissent dès qu'une
  tâche existe. » : `createRisk` est refusé par 409, `at_least_one_task` manquante, comme le
  réexamen qui ramène un risque écarté à l'état identifié ; l'un et l'autre aboutissent après la
  création d'une tâche ;
- `WF-RIS-0010-A` — « Avec deux catégories actives de type provision pour risques, la déclaration
  d'un risque demande laquelle porte sa provision, et la ventilation du devis présente la provision
  sous la nature de la catégorie choisie ; avec une seule, elle ne la demande pas. » : avec deux
  catégories actives, la catégorie est exigée de `createRisk`, et la ventilation du devis par nature
  compte la provision sous la nature de la catégorie choisie ; avec une seule, elle est retenue ;
- `WF-RIS-0010-A` — « Sans aucune catégorie active de ce type, la déclaration d'un risque est
  refusée et nomme la condition manquante. » : 409, `active_provision_category` manquante ;
- `WF-RIS-0010-A` — « La suppression de la tâche qui porte une provision de 40 laisse le devis
  inchangé, la provision étant passée sur la tâche parente. » : la suppression de la tâche porteuse
  passe la ligne sur sa tâche parente — pour une tâche de premier niveau, sur la première tâche de
  premier niveau restante —, la réponse le dit et le total est inchangé ; il en va de même, au
  compte rendu, pour l'import d'un planning et pour la fusion d'un différentiel ; la suppression de
  la dernière tâche d'une structure principale qui porte une provision est refusée en nommant le
  risque ;
- `WF-RIS-0010-A` — « Un risque écarté dont la catégorie a été désactivée redevient identifié avec
  la catégorie active choisie. » : tenu par US-2590 ; la ligne recréée porte la catégorie choisie ;
- `WF-RIS-0010-A` — « Un risque écarté qui redevient identifié porte sa provision sur la tâche qu'il
  désignait ; si cette tâche a été supprimée entre-temps, sur la première tâche de premier niveau. »
  : tenu par US-2590 ; la ligne recréée est sous la tâche désignée ou, à défaut, sous la première
  tâche de premier niveau ;
- `WF-RIS-0010-A` — « Sans catégorie active de ce type, son retour à l'état identifié est refusé et
  nomme la condition manquante. » : tenu par US-2590 ;
- `WF-RIS-0010-A` — « Un risque déclaré sur le sous-projet S2 porte sa provision au reste à engager
  de S2 ; sans sous-projet désigné, elle compte hors sous-projet. » : la provision compte au reste à
  engager de S2 (`getRemainingIndicators` par sous-projet) et, sans sous-projet, dans l'ensemble «
  hors sous-projet » ;
- `WF-DEV-0010-A` — « Le refus énumère les catégories de coût sans taux horaire pour l'année de
  référence. » : tenu par EP-07, non touché ici ;
- `WF-DEV-0010-A` — « Le calcul aboutit dès que ces taux sont renseignés. » : tenu par EP-07, non
  touché ici ;
- `WF-DEV-0010-A` — « Un devis qui ne porte que des lignes hors main-d'œuvre et une ligne de
  provision se calcule sans aucun taux horaire. » : une révision dont le devis ne porte que des
  lignes hors main-d'œuvre et une ligne de provision se calcule alors qu'aucun taux horaire n'existe
  ;
- `WF-DEV-0030-A` — « Une même ligne consommée deux ans après l'année de référence, avec un taux
  d'inflation de 3 %, vaut 1,03 x 1,03 fois son montant de base. » : tenu par EP-07, non touché ici
  ;
- `WF-DEV-0030-A` — « Une ligne consommée dans l'année de référence vaut son montant de base. » :
  tenu par EP-07, non touché ici ;
- `WF-DEV-0030-A` — « Une part consommée l'année qui précède l'année de référence vaut son montant
  de base, quel que soit le taux d'inflation. » : tenu par EP-07, non touché ici ;
- `WF-DEV-0030-A` — « Une ligne de provision portée par une tâche consommée deux ans après l'année
  de référence vaut sa gravité pondérée par sa probabilité, sans autre projection. » : la règle «
  une ligne de provision n'est pas projetée », écrite par EP-07 dans le module de calcul, est
  éprouvée sur la ligne d'un risque ;
- `WF-PRJ-0040-A` — « La modification du taux d'inflation laisse inchangés les montants des
  révisions marquées. » : tenu par EP-07, non touché ici ;
- `WF-PRJ-0040-A` — « Dans la révision en cours, les lignes de main-d'œuvre et hors main-d'œuvre
  dont l'année de consommation suit l'année de référence sont rechiffrées, les autres non ; une
  ligne de provision ne change que par son devis propre. » : le rechiffrage des lignes de
  main-d'œuvre et hors main-d'œuvre est tenu par EP-07 ; une ligne de provision ne change à la
  modification du taux que de ce que son devis propre, rechiffré, change à la gravité ;
- `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. » : tenu par EP-04, non touché
  ici ;
- `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est refusée.
  » : tenu par EP-04, non touché ici ;
- écart : `WF-PRJ-0050-A` — « Un sous-projet de code « A.ABC.26001/10001 », « Synthèse » ou de
  quarante caractères se crée, et le fichier de reste à engager lui donne un onglet qui porte son
  code en tête. » : remplace, par la spécification 1.0.7 (#3370), le refus de « SP/01 », de «
  Synthèse » et de plus de trente et un caractères, que le livré tient encore ; #3966 l'éprouve ;
- écart : `WF-PRJ-0050-A` — « La création d’un sous-projet dont le code est celui du projet est
  refusée. » : ajouté par la spécification 1.0.7 (#3370) ; #3966 l'éprouve ;
- `WF-PRJ-0050-A` — « La suppression d'un sous-projet portant des coûts réels est refusée. » : tenu
  par EP-09, non touché ici ;
- `WF-PRJ-0050-A` — « La suppression d'un sous-projet cité par une révision marquée est refusée. » :
  tenu par EP-04, non touché ici ;
- `WF-PRJ-0050-A` — « La suppression d'un sous-projet que porte une ligne de devis de la révision en
  cours est refusée ; elle aboutit une fois cette ligne passée à un autre sous-projet. » : tenu par
  EP-07, non touché ici ;
- `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d'une ligne d'une tâche démarrée, dont le
  sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d'une ligne d'une
  tâche non démarrée aboutit, comme celui de la ligne de provision d'un risque identifié. » : les
  deux premiers cas sont tenus par EP-09 ; la ligne de provision d'un risque identifié passe à un
  autre sous-projet par `updateRiskProvision`, même portée par une tâche démarrée dont le
  sous-projet a reçu des coûts réels ;
- `WF-PLA-0040-A` — « Après déplacement d'une récapitulative portant deux niveaux de subordonnées,
  les tâches et les lignes déplacées sont inchangées, et le devis totalise le même montant. » : tenu
  par EP-06, non touché ici ;
- `WF-PLA-0040-A` — « Les dates et l'état d'une récapitulative ne sont pas saisissables. » : tenu
  par EP-06, non touché ici ;
- `WF-PLA-0040-A` — « Une récapitulative dont une subordonnée est démarrée est démarrée ; elle n'est
  terminée qu'après la dernière. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont une
  ligne propre porte un reste à engager de 500 est démarrée et signalée ; la saisie d'un reste nul
  sur cette ligne la termine. » : tenu par EP-09 et EP-22, non touché ici ;
- `WF-PLA-0040-A` — « La suppression de la seule subordonnée d'une récapitulative de dix jours
  laisse une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être ajoutée. » :
  tenu par EP-06, non touché ici ;
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont la
  seule ligne propre est une provision de 40 est terminée et n'est pas signalée. » : la règle « hors
  lignes de provision », écrite par EP-09 dans la question que `core/planning` pose aux lignes, est
  éprouvée sur la provision d'un risque : la récapitulative est terminée, et le Kanban ne la signale
  pas ;
- `WF-PLA-0040-A` — « Une récapitulative dont la seule subordonnée est un jalon terminé et dont une
  ligne propre garde un reste à engager, privée de ce jalon, est une feuille démarrée d'un jour, non
  un jalon. » : tenu par EP-09, non touché ici ;
- `WF-PLA-0040-A` — « Une récapitulative terminée dont la seule subordonnée, un jalon, est déplacée
  devient un jalon terminé. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0040-A` — « Le déplacement d'une sélection qui contient une récapitulative et l'une de ses
  subordonnées laisse la subordonnée sous la récapitulative : le groupe est déplacé entier, sans
  être aplati. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0040-A` — « Un déplacement qui placerait un nœud sous lui-même ou sous l'un de ses
  subordonnés est refusé. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0050-A` — « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. » : tenu par
  EP-06, non touché ici ;
- `WF-PLA-0050-A` — « Une récapitulative dont la seule subordonnée est un jalon a une durée nulle et
  reste une récapitulative. » : tenu par EP-06, non touché ici ;
- `WF-PLA-0050-A` — « Un jalon portant une ligne de devis passe de non démarré à terminé par la
  saisie d'un reste à engager nul ; un jalon sans ligne est terminé depuis le Kanban. » : tenu par
  EP-09, non touché ici ;
- `WF-PLA-0050-A` — « La terminaison depuis le Kanban d'un jalon portant une ligne est refusée en
  renvoyant à la saisie de son reste à engager. » : tenu par EP-09, non touché ici ;
- `WF-PLA-0050-A` — « Un jalon qui ne porte qu'une ligne de provision est terminé depuis le Kanban.
  » : `setTaskProgress` termine depuis le Kanban le jalon dont la seule ligne est la provision d'un
  risque ;
- `WF-INTF-0120-A` — « Même critère que WF-INTF-0100, appliqué aux grandeurs réestimées ; les
  montants budgétés et les lignées de toutes les lignes sont inchangés après l'import, et une ligne
  absente du fichier conserve son reste à engager. » : tenu par EP-09 ; les lignes de provision du
  fichier sont ignorées et signalées (`provision_lines`), et celles de la révision sont inchangées
  après l'import ;
- `WF-INTF-0120-A` — « Un reste à engager exporté d'une révision marquée puis réimporté dans la
  révision en cours met à jour les lignes de même lignée sans en créer aucune. » : tenu par EP-09,
  non touché ici ;
- `WF-INTF-0120-A` — « Avec huit heures par jour, une ligne de main-d'œuvre dont le fichier porte
  trois jours a un reste de vingt-quatre heures. » : tenu par EP-09, non touché ici ;
- écart : `WF-INTF-0120-A` — « Une tâche démarrée dont toutes les lignes, celles absentes du fichier
  comprises, sont à zéro après l’import, et dont le fichier en met au moins une à zéro, est terminée
  à la date de la revue ; une tâche non démarrée dont les lignes sont laissées telles quelles reste
  non réestimée. » : réécrit par la spécification 1.0.7 (#3362) ; #3978 le confronte au livré ;
- `WF-INTF-0120-A` — « Un fichier qui recopie une ligne avec sa lignée voit les deux lignes
  rejetées, et la ligne existante inchangée. » : tenu par EP-09, non touché ici ;
- `WF-INTF-0120-A` — « Un fichier sans date de revue applique les lignes qui ne terminent aucune
  tâche et rejette celles qui en termineraient une. » : tenu par EP-09, non touché ici ;
- `WF-INTF-0120-A` — « Une cellule de reste effacée sur une ligne connue la met à zéro. » : tenu par
  EP-09, non touché ici ;
- écart : `WF-INTF-0120-A` — « Un onglet renommé dans Excel garde son sous-projet. » : ajouté par la
  spécification 1.0.7 (#3370) ; #3966 l'éprouve ;
- propre à l'US : la ligne de provision est une ligne de la structure principale, de la catégorie que le
  risque désigne, dont le budgété est la provision qu'elle portait dans la référence et le montant est la gravité pondérée par la probabilité,
  au centime ; elle ne s'écrit que par le risque — sa déclaration, `updateRiskProvision`, ses
  réexamens, les écritures de son devis propre — et les écritures de grille, le collage et les
  imports la refusent ou l'ignorent comme le contrat le dit ;
- propre à l'US : `updateRiskProvision` écrit la catégorie, le sous-projet et la tâche de la
  provision d'un risque identifié (`update_provision`) : une saisie de la révision en cours, créée
  au besoin, annulable, que l'abandon défait ; ses conditions sont nommées dans l'ordre du contrat
  (`project_not_terminal`, `no_background_task_running`, `risk_identified`, `may_create_revision`) ;
- propre à l'US : un devis importé d'où la ligne de provision a été retirée la laisse en place
  (`kept`, `provision_lines` ; WF-INTF-0100, US-2550) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Ce qui reconnaît une ligne de provision est dit une fois par la conception
: aujourd'hui `core/planning` la juge par `origin_risk_id`, que le contrat réserve aux nœuds issus
d'une survenance, et la dépendance du sous-arbre d'EP-10 par sa catégorie. `docs/api/DECISIONS.md` :
« La catégorie et le sous-projet de la provision d'un risque » (EP-14/L42p), « La déclaration d'un
risque désigne la tâche de sa provision » (US-0520), « Une écriture engendrée ne change l'avancement
d'aucune tâche » (F-02).

**Hors périmètre.** La réserve et la couverture (US-2610) ; les provisions dans les courbes
(US-2630).

---

## US-2590 — Les états d'un risque, ses réexamens et sa suppression ; ce que l'abandon et l'annulation en défont

- **statut** : en cours
- **exigences** : `WF-RIS-0020-A`, `WF-IHM-0110-A`
- **opérations** : `reviewRisk`, `listRiskReviews`, `deleteRisk`, `listRisks` (`last_review_on_to`),
  `abandonRevision`, `undoLastChange`, `redoLastUndo`
- **issue** : #3814
**En tant que** chef de projet, **je veux** réexaminer à chaque revue la probabilité et l'état de
chaque risque, écarter celui qui ne peut plus se produire, le reprendre s'il revient, supprimer
celui qu'aucune révision marquée ne cite, et annuler une saisie malheureuse, **afin que** le
registre dise ce qu'on pense des risques aujourd'hui et garde ce qu'on en pensait à chaque révision.

**Critères d'acceptation.**

- `WF-RIS-0020-A` — « Les transitions entre identifié et écarté sont possibles dans les deux sens. »
  : `reviewRisk` écarte un risque identifié, dont la ligne de provision est retirée, et ramène un
  risque écarté à l'état identifié, dont la ligne est recréée : sous la catégorie qu'il désignait si
  elle est encore active, demandée sinon, et refusée par 409 (`active_provision_category`) s'il n'en
  reste aucune ; sous la tâche qu'il désignait si elle est encore une tâche de la structure
  principale, sinon sous la première tâche de premier niveau (WF-RIS-0010) ;
- `WF-RIS-0020-A` — « Toute transition depuis l'état survenu est refusée. » : 409
  `STATE_FORBIDS_OPERATION`, `risk_not_occurred` manquante, pour `reviewRisk`, `updateRiskProvision`
  et `deleteRisk` ; l'état survenu ne s'atteint que par la survenance (US-2620) ;
- `WF-RIS-0020-A` — « La suppression d'un risque cité par une révision marquée est refusée. » : 409,
  `risk_not_cited` manquante ; un risque qu'aucune révision marquée ne cite est supprimé avec son
  devis propre et sa ligne de provision ;
- `WF-RIS-0020-A` — « La revue périodique présente les risques dont la probabilité n'a pas été
  réexaminée. » : `listRisks` filtré par `last_review_on_to` rend les risques dont le dernier
  réexamen précède la date donnée (H-01) ; l'écran de la revue, qui pose la date, est d'US-2640 ;
- `WF-RIS-0020-A` — « Après abandon d'une révision en cours où un risque a été créé, un autre
  réexaminé et un troisième déclaré survenu, le premier n'existe plus, le second présente la
  probabilité et l'état de la dernière révision marquée, et le troisième est identifié, avec sa
  provision et sans coût à la survenance. » : après `abandonRevision`, le premier risque n'existe
  plus, ni son identité ; le second a la probabilité et l'état de la dernière révision marquée, et
  son historique ne garde aucun réexamen de la révision abandonnée ; le troisième est identifié,
  avec sa ligne de provision, son devis propre, et `occurrence_cost` nul ;
- `WF-IHM-0110-A` — « La suppression d'une tâche puis son annulation restituent la tâche, ses lignes
  et ses liaisons. » : tenu par EP-06 pour la tâche et ses liaisons, par EP-07 pour ses lignes, non
  touché ici ;
- `WF-IHM-0110-A` — « Le réexamen d'un risque puis son annulation lui rendent sa probabilité et son
  état précédents. » : `undoLastChange` après un `reviewRisk` rend au risque sa probabilité, son
  état et sa ligne de provision d'avant, et retire le réexamen de l'historique ; `redoLastUndo` le
  rétablit ;
- `WF-IHM-0110-A` — « Cinquante modifications successives s'annulent une par une, puis se
  rétablissent dans l'ordre. » : tenu par EP-06, non touché ici ;
- `WF-IHM-0110-A` — « L'annulation d'une modification qu'un autre contributeur a depuis reprise est
  refusée en nommant l'objet en conflit. » : tenu par EP-06, non touché ici ;
- `WF-IHM-0110-A` — « Aucune commande n'annule un marquage, un import appliqué, une déclaration de
  survenance ou une exclusion de ligne de coût. » : le marquage et les imports sont tenus par EP-06
  et EP-07, l'exclusion par EP-09 ; ni la survenance ni la fusion n'entrent à l'historique : après
  elles, `undoLastChange` ne les défait pas ;
- propre à l'US : `reviewRisk` est une saisie de la révision en cours, créée au besoin : il écrit la
  probabilité et l'état, daté du jour ; la confirmation d'un risque sans modification produit un
  réexamen daté (WF-RIS-0010) ; la probabilité ne s'écrit que par lui ; `listRiskReviews` rend
  chaque réexamen, sa date, la probabilité, la gravité et l'état retenus, l'identification le
  premier ;
- propre à l'US : la déclaration, la modification de la provision, le réexamen et la suppression
  d'un risque entrent à l'historique annulable de la révision, et la réponse de l'annulation nomme
  les risques qu'elle touche (`risk_ids`, #2538) sans supposer une entrée de planning ; la
  modification de l'identité n'y entre pas ;
- propre à l'US : l'annulation d'un collage de l'avancement demande la permission du collage,
  `remaining.write`, et non `planning.write` (#2905) ;
- propre à l'US : les conditions d'état de la saisie des risques sont jugées avant celles du risque,
  dans l'ordre du contrat (H-09) ; chaque réponse est validée contre le contrat dans les tests du
  service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Les risques : coût à la survenance… » (M-04 :
l'abandon ramène l'évaluation ; H-09), « Les révisions et les structures » (E-06, E-08 :
l'historique tenu par le serveur, `UndoneKind`), « Le registre des risques se filtre sur chacune de
ses colonnes ». L'évaluation d'un risque est portée par la révision : c'est la copie et l'abandon de
la révision qui la font suivre, par les points d'extension d'EP-04.

**Hors périmètre.** La survenance (US-2620) ; le registre et ses filtres (US-2600) ; l'écran de la
revue (US-2640).

---

## US-2600 — Le registre des risques et la matrice

- **statut** : fini
- **exigences** : `WF-RIS-0040-A`, `WF-REF-0160-A`
- **opérations** : `listRisks`, `getRisk`, `listRiskReviews`, `getProjectRiskMatrix`,
  `getReferenceSettings`
- **issue** : #3815
**En tant que** chef de projet, **je veux** lire le registre des risques du projet, trié par ce que
chacun fait peser, filtré sur chacune de ses colonnes, coloré par la matrice de l'entreprise, avec
ses totaux, **afin de** mener la revue des risques par ordre d'importance.

**Critères d'acceptation.**

- `WF-RIS-0040-A` — « Les six colonnes sont présentes, ainsi que l'accès aux deux notes et à
  l'historique. » : `listRisks` rend pour chaque risque son libellé, sa probabilité, sa gravité, sa
  provision, son état et la date de son dernier réexamen, et pour un survenu son coût à la
  survenance et le réestimé courant des lignes qui en sont issues ; `getRisk` et `listRiskReviews`
  donnent la description, les actions de mitigation et l'historique ;
- `WF-RIS-0040-A` — « Le tri par provision classe les risques du plus lourd au plus léger. » :
  `sort_by` sur la provision, décroissant ; la provision d'un survenu ou d'un écarté est celle qu'il
  portait dans la référence (H-03) ;
- `WF-RIS-0040-A` — « Un risque dont la probabilité augmente change de couleur conformément à la
  matrice. » : `matrix_cell` et la zone du risque suivent ses niveaux de probabilité et de gravité :
  un réexamen qui fait franchir une borne à la probabilité change la case ;
- `WF-RIS-0040-A` — « Les trois totaux — identifiés, survenus, écartés — sont distincts, et la
  réserve pour risques de la référence est affichée en regard. » : `ProvisionTotals` rend trois
  totaux — les identifiés pour leur provision courante, les survenus et les écartés pour celle de la
  référence — et la réserve de la référence ;
- `WF-REF-0160-A` — « Les six bornes sont saisissables et ordonnées. » : tenu par EP-05, non touché
  ici ;
- `WF-REF-0160-A` — « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité 60 est au
  troisième niveau sur un projet de budget 1 000 (6 %) et au deuxième sur un projet de budget 2 000
  (3 %). » : le niveau de gravité se lit de la gravité rapportée à l'assiette du projet : troisième
  niveau à 6 %, deuxième à 3 % ;
- `WF-REF-0160-A` — « Sur un projet en chiffrage, un risque est classé d'après le total hors
  provisions de son devis courant ; la désignation de la révision de référence ne change pas son
  niveau si ce total égale le budget de référence. » : en chiffrage, l'assiette est le total hors
  provisions du devis courant ; après la désignation, le budget de référence : à total égal, le
  niveau est le même ;
- `WF-REF-0160-A` — « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité 50 sur un
  projet de budget 1 000 est au troisième niveau. » : une gravité égale à une borne est du niveau
  que la borne ouvre : 5 % est au troisième niveau ;
- propre à l'US : le registre se filtre sur chacune de ses colonnes — état, zone, recherche, bornes
  de la probabilité, de la gravité, de la provision, du coût à la survenance et du réestimé des
  survenus, période du dernier réexamen, fin incluse — et se trie sur chacune, les valeurs nulles à
  la place que dit le contrat ; les totaux sont ceux des risques retenus (H-01, #1786) ;
- propre à l'US : avec `revision_id`, le registre, le détail et la matrice lisent l'évaluation
  qu'une révision marquée a figée ; sans lui, celle de la révision en cours ou, à défaut, de la
  dernière révision marquée ;
- propre à l'US : `getProjectRiskMatrix` rend les niveaux de la matrice du référentiel, les points
  des risques et le décompte de chaque case (#1395), et dit quand aucune assiette ne permet de
  classer ;
- propre à l'US : les lectures sont sous `risks.read` ; chaque réponse est validée contre le contrat
  dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Les risques : coût à la survenance, provision
de référence… » (H-03, H-06, H-07), « Le registre des risques se filtre sur chacune de ses colonnes
» (H-01), « Le filtre des écarts et le décompte de la matrice des risques » (#1395). La zone d'un
couple (probabilité, gravité) est exposée par `core/risk_settings` (EP-05).

**Hors périmètre.** La couverture (US-2610) ; les risques du portefeuille (EP-11) ; les écrans
(US-2640).

---

## US-2610 — La réserve pour risques et la couverture

- **statut** : à faire
- **exigences** : `WF-RIS-0050-A`, `WF-RAE-0020-A`, `WF-RAE-0010-A`
- **opérations** : `getProjectRiskCoverage`, `getRemainingIndicators`, `listNodes` (`totals`),
  `listRisks` (`ProvisionTotals`)
- **issue** : #3816
**En tant que** chef de projet, **je veux** voir, à chaque revue, la réserve pour risques de la
référence face à ce que les risques pèsent encore et à ce que les survenus ont coûté, **afin de**
savoir si le projet consomme ses provisions sans que cela se voie dans son budget.

**Critères d'acceptation.**

- `WF-RIS-0050-A` — « Sur un projet chiffré à 1 000 portant un risque de gravité 200 à 30 %, le
  devis totalise 1 060, le budget de référence 1 000 et la réserve 60. » : le devis de la révision
  totalise 1 060, provision comprise ; le budget de référence, hors lignes de provision, 1 000 ; la
  réserve que la référence conserve, 60 ;
- `WF-RIS-0050-A` — « Après survenance de ce risque, réévalué à 250, le budget de référence vaut
  toujours 1 000, les provisions restantes 0, le coût des survenus 250, et l'écart de couverture
  −190. » : après la survenance (US-2620) : budget de référence 1 000, `remaining_provisions` 0,
  `occurred_cost` 250, écart de couverture −190 ;
- `WF-RIS-0050-A` — « Sur le même projet, un second risque de provision 40 présent dans la référence
  porte la réserve à 100 ; l'écarter fait passer les provisions restantes de 40 à 0 sans toucher le
  budget de référence, et l'écart de couverture de −190 à −150. » : la réserve vaut 100 ; l'écart du
  second risque porte `remaining_provisions` de 40 à 0 et l'écart de −190 à −150, le budget de
  référence inchangé ;
- `WF-RIS-0050-A` — « Sur un projet dont la réserve est nulle et sans risque survenu, un risque
  identifié après la référence, de provision 30, porte les provisions restantes à 30 et l'écart de
  couverture à −30. » : `remaining_provisions` 30, écart −30 ;
- `WF-RIS-0050-A` — « La terminaison des tâches issues d'un risque survenu ne change ni le coût des
  survenus ni l'écart de couverture. » : `occurred_cost` et l'écart sont les mêmes avant et après la
  terminaison des tâches ;
- `WF-RIS-0050-A` — « Sur le projet dont le risque est survenu à 250 : un avenant qui ne touche pas
  aux risques laisse la réserve à 60 et l'écart de couverture à −190 ; un avenant qui intègre au
  budget de référence les lignes de ce risque porte le budget de référence à 1 250 et laisse la
  réserve à 60 et l'écart à −190 ; un avenant qui déclare un nouveau risque de provision 50 porte la
  réserve à 110 et les provisions restantes à 50, et laisse l'écart à −190. » : éprouvé par trois
  fusions (US-2560) : la réserve de la nouvelle référence conserve la provision que portaient dans
  la précédente les risques survenus ou écartés avant elle, et s'augmente de celle des risques
  identifiés qu'elle porte — 60 et −190 ; 1 250, 60 et −190 ; 110, 50 et −190 ;
- `WF-RIS-0050-A` — « Sur le projet dont le risque est survenu à 250, la réestimation à 300 des
  lignes qui en sont issues présente 300 en regard de 250, et laisse l'écart de couverture à −190. »
  : `occurred_reestimated` 300 en regard de `occurred_cost` 250, hors de l'écart, −190 ;
- `WF-RAE-0020-A` — « Sur un projet de budget 1 000, de coût réel 500 et de reste à engager 550, la
  marge sur le budget vaut − 50 ; un reste à engager passé de 600 à 550 depuis la revue précédente
  donne un écart de − 50. » : tenu par EP-09, non touché ici ;
- `WF-RAE-0020-A` — « Un sous-projet dont le coût réel augmenté du reste à engager dépasse son
  budget est signalé par la couleur, les autres non. » : tenu par EP-09, non touché ici ;
- écart : `WF-RAE-0020-A` — « Sur un projet dont aucune révision n’a été marquée avant celle qui est
  lue, l’écart correspondant est absent plutôt que nul, et sur la première révision qui suit
  l’offre, il se mesure à l’offre ; sur un projet sans révision de référence, la marge sur le budget
  l’est aussi. » : réécrit par la spécification 1.0.7 (#3929) : l'écart se mesure à l'offre sur la
  première révision qui la suit ; tenu par EP-10 (#3930) ;
- `WF-RAE-0020-A` — « La marge sur le budget du projet égale la somme des marges de ses
  sous-projets, ensemble hors sous-projet compris. » : tenu par EP-09 ; les provisions comptent dans
  la marge de la maille de leur sous-projet ;
- `WF-RAE-0020-A` — « La couverture des risques présente la réserve de référence, les provisions
  restantes, le coût des risques survenus et l'écart de couverture. » : `coverage` de
  `getRemainingIndicators`, servie à zéro par EP-09, est remplie par `register_coverage` : la
  réserve, les provisions restantes, le coût des survenus et l'écart, égaux à ceux de
  `getProjectRiskCoverage` ;
- `WF-RAE-0010-A` — « Sur un projet dont une tâche est terminée, une démarrée et une non démarrée,
  le reste à engager vaut la somme des deux dernières, la démarrée pour son montant réestimé et
  l'autre pour son montant de référence projeté, plus les provisions des risques identifiés. » :
  tenu par EP-09 pour les tâches ; les provisions des risques identifiés s'y ajoutent ;
- `WF-RAE-0010-A` — « Le décalage d'une tâche non démarrée d'une année modifie son montant du taux
  d'inflation. » : tenu par EP-09, non touché ici ;
- `WF-RAE-0010-A` — « Écarter un risque de provision 40 diminue le reste à engager de 40 ; en
  identifier un nouveau l'augmente de sa provision. » : le reste à engager baisse de 40 à l'écart du
  risque, et monte de la provision d'un risque nouveau ;
- `WF-RAE-0010-A` — « La réestimation à 120 d'une ligne budgétée à 100 sur une tâche non démarrée,
  saisie depuis la grille, porte le reste à engager de 100 à 120. » : tenu par EP-09, non touché ici
  ;
- `WF-RAE-0010-A` — « Un projet portant un risque de provision 40 compte cette provision une fois. »
  : la provision compte par sa ligne, une seule fois ;
- `WF-RAE-0010-A` — « Le reste à engager égale la somme des montants réestimés courants des lignes
  des tâches non terminées, hors lignes de provision, plus les provisions des risques identifiés,
  quel que soit l’état de la tâche qui les porte. » : la somme des `reestimated_amount` des lignes
  des tâches non terminées, lignes de provision comprises, égale le reste à engager ;
- `WF-RAE-0010-A` — « Dans une révision créée en 2027 où le taux de 2027 d'une catégorie a été
  accepté, une tâche non démarrée dont une ligne relève de cette catégorie compte pour sa charge au
  taux de 2027, et non au taux de 2026 corrigé d'une année d'inflation. » : tenu par EP-09, non
  touché ici ;
- `WF-RAE-0010-A` — « Après un avenant qui porte de 100 à 150 heures une ligne non réestimée d'une
  tâche non démarrée, le reste à engager compte 150 heures ; une ligne réestimée à 140 avant
  l'avenant garde 140. » : après la fusion (US-2560), la ligne non réestimée compte 150 heures, et
  la ligne réestimée à 140 garde 140, par la marque d'EP-09 ;
- propre à l'US : la réserve est conservée par la révision de référence au moment où elle le devient
  — une désignation, une fusion — et ne change plus : ni un réexamen, ni un écart, ni une
  survenance, ni une saisie dans un devis propre ne la déplacent (M-01) ;
- propre à l'US : `getProjectRiskCoverage` rend la réserve, les provisions restantes des risques
  identifiés de la révision lue, le coût à la survenance des survenus, l'écart de couverture, signé,
  `reserve − (remaining_provisions + occurred_cost)`, et, en regard, le réestimé courant des lignes
  issues des survenus ; sans révision de référence, la réserve et l'écart sont ce que le contrat dit
  ;
- propre à l'US : la couverture d'une révision marquée est conservée à son marquage dans le document
  `remaining` d'EP-10 et rendue telle quelle : aucune lecture d'une révision marquée ne recalcule
  ses risques (WF-DAT-0040) ;
- propre à l'US : une variante contrefactuelle déclarée de `getProjectRiskCoverage`, engendrée par
  `make mock-data`, porte un réestimé des survenus différent de leur coût, l'écart de couverture
  inchangé (#2002, décision de l'auteur du 2026-11-17) ; le test du portefeuille est d'EP-11 ;
- propre à l'US : les lectures sont sous `risks.read` ; chaque réponse est validée contre le contrat
  dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Les risques : coût à la survenance, provision
de référence… » (H-01, H-02, M-01), « Les lignes issues d'un risque survenu gardent sa trace »
(#1761). Le registre `register_coverage` est déclaré par `core/estimate` (EP-09).

**Hors périmètre.** Les indicateurs de valeur acquise et les courbes (US-2630) ; la couverture du
portefeuille (EP-11).

---

## US-2620 — La survenance d'un risque

- **statut** : en cours
- **exigences** : `WF-RIS-0060-A`
- **opérations** : `getRiskOccurrenceReport`, `declareRiskOccurrence`, `getBackgroundTask`,
  `listNodes` et `compareRevisions` (`is_from_risk`, `origin_risk_ids`), `getRisk`
- **issue** : #3818
**En tant que** chef de projet, **je veux** déclarer qu'un risque est survenu, après avoir lu ce que
cela fera de la structure principale, **afin que** son devis propre devienne du travail comme un
autre — planifié, réestimé, terminé —, sans budget, et que ce qu'il coûte se suive jusqu'au bout.

**Critères d'acceptation.**

- `WF-RIS-0060-A` — « Après déclaration de survenance d'un risque dont le devis propre porte deux
  lignes de 120 et 80, ces lignes figurent dans la structure principale de la révision en cours avec
  des montants budgétés nuls et des montants réestimés de 120 et 80 ; la ligne de provision a
  disparu ; le budget de référence et la révision de référence sont inchangés ; le reste à engager a
  augmenté de 200 moins la provision retirée ; la terminaison de ces tâches n'acquiert aucune
  valeur. » : les deux lignes sont dans la structure principale de la révision en cours, budgété
  nul, réestimé 120 et 80 ; la ligne de provision n'y est plus ; la révision de référence et son
  budget sont les mêmes ; le reste à engager a monté de 200 moins la provision ; que leur
  terminaison n'acquière rien est éprouvé par US-2630 ;
- `WF-RIS-0060-A` — « Les tâches fusionnées se trouvent sous la tâche qui portait la provision, aux
  dates qu’elles avaient dans le devis propre ; le total du lot dont cette tâche relève augmente de
  leur montant, moins la provision retirée ; une tâche feuille fusionnée qui n’avait pas de
  prédécesseur est en mode manuel. » : les tâches de premier niveau du devis propre sont, dans leur
  ordre, les dernières sous la tâche qui portait la provision, avec leurs subordonnées, leurs
  liaisons internes, leurs durées et leurs modes ; une tâche sans prédécesseur dans le devis propre
  est en mode manuel aux dates qu'elle y avait ; le total du lot de la tâche porteuse monte de leur
  montant moins la provision ;
- `WF-RIS-0060-A` — « La survenance d'un risque dont la provision était portée par un jalon place
  ses tâches après ce jalon, qui reste un jalon sans sous-tâche. » : les tâches sont placées, dans
  leur ordre, immédiatement après le jalon, sous sa tâche parente ou au premier niveau ; le jalon
  reste un jalon ;
- `WF-RIS-0060-A` — « Une ligne fusionnée par la survenance d'un risque est encore désignée comme
  issue de ce risque dans la révision suivante, et après son déplacement sous une autre tâche ; une
  ligne ajoutée ensuite sous une tâche issue du risque ne l'est pas. » : `origin_risk_id` est posé
  sur chaque tâche et chaque ligne fusionnée, conservé par la copie d'une révision, les
  déplacements, les imports rapprochés par la lignée et la fusion d'un avenant ; une création le
  laisse nul, même sous une tâche issue du risque (#1762) ;
- `WF-RIS-0060-A` — « Les grilles de planning et de devis se filtrent sur les tâches et les lignes
  issues d'un risque, ou d'un risque donné (WF-IHM-0130). » : `is_from_risk` et `origin_risk_ids`
  filtrent `listNodes` et `compareRevisions` ; un identifiant qui n'est pas celui d'un risque
  survenu du projet est refusé par 422, `UNKNOWN_RISK` ;
- propre à l'US : `getRiskOccurrenceReport` est une lecture qui n'écrit rien : les tâches et les
  lignes du devis propre ajoutées dans l'ordre de son plan, la tâche porteuse modifiée par ses dates
  et sa durée, la ligne de provision retirée et son montant, les motifs de refus
  (`TASK_WITHOUT_WORKING_HOURS`), les compteurs lus de la structure principale et du risque, et
  `creates_current_revision` ; un risque qui n'est pas identifié reçoit 409, `risk_identified`
  manquante ;
- propre à l'US : `declareRiskOccurrence` exige les deux compteurs et `creates_current_revision`
  tels que lus : l'un changé depuis — une saisie dans le devis propre comprise —, 412
  `STALE_LOCK_VERSION` ; la survenance est une tâche de fond et une seule opération, qui en échec ne
  laisse rien ; sans révision en cours, elle en crée une au préalable, aux taux conservés, projetés
  ;
- propre à l'US : le risque survenu garde son coût à la survenance (`occurrence_cost`), le total de
  son devis propre à cet instant, qui ne change plus ; son dernier réexamen est la survenance ; son
  devis propre se lit `is_merged` dans la révision où il est survenu et n'est pas repris par la
  suivante ; `occurred_reestimated_amount` est le réestimé courant des lignes qui en sont issues ;
- propre à l'US : la survenance ne marque aucune révision, ne déplace pas la référence, n'entre pas
  à l'historique annulable, et aucune transition ne part de l'état survenu ; seul l'abandon de la
  révision en cours la défait (US-2590) ;
- propre à l'US : la tâche de fond aboutie porte `task_occurrence_succeeded`, que le parcours de
  l'écran éprouve contre le service, sans exemple ajouté au contrat (#1830) ;
- propre à l'US : le compte rendu nomme, après la tâche porteuse, chaque tâche de la structure
  principale dont les dates calculées changent par la greffe, par une différence `updated` sur ses
  dates : une tâche liée à la récapitulative porteuse, que la greffe allonge de dix jours, y figure
  avec ses dates, et une tâche que rien ne lie à elle n'y figure pas (#4134, décision de l'auteur
  du 2026-11-19) ;
- propre à l'US : le compte rendu signale un devis propre dont la date de début de planning précède
  le jour de la déclaration, et nomme cette date ; il ne refuse pas, et la survenance ne redate
  rien : le début du devis propre déplacé par `updateCostStructure`, le compte rendu lu est périmé,
  et celui qui suit ne signale plus rien (#4133, décision de l'auteur du 2026-11-19) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** `docs/api/DECISIONS.md` : « Le compte rendu préalable de la survenance
d'un risque » (#1453), « Les risques… » (M-05 : la place des tâches fusionnées), « Les lignes issues
d'un risque survenu gardent sa trace » (#1761), « La racine du devis propre d'un risque survenu,
dans le témoin » (H-03). La survenance partage avec la fusion d'un avenant la mécanique qui greffe
un sous-arbre dans la structure principale : la conception dit ce qui est commun.

**Hors périmètre.** La couverture après la survenance (US-2610) ; la valeur acquise et la projection
devant elle (US-2630) ; l'écran (US-2640).

---

## US-2630 — Les indicateurs devant une provision, une survenance et un avenant

- **statut** : à faire
- **exigences** : `WF-IND-0030-A`, `WF-IND-0100-A`, `WF-DEV-0080-A`
- **opérations** : `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves`,
  `getRemainingIndicators`, `markRevision`, `mergeCostStructure` (la conservation)
- **issue** : #3819
**En tant que** chef de projet, **je veux** que les indicateurs, les courbes et la valeur planifiée
disent juste devant un risque provisionné, un risque survenu et un avenant contractualisé, **afin
que** la dérive d'un risque se lise comme une dérive, et un avenant comme un déplacement de la
référence.

**Critères d'acceptation.**

- `WF-IND-0030-A` — « Une tâche terminée le 12 du mois contribue à la valeur acquise dès cette date,
  non à la revue suivante. » : tenu par EP-10, non touché ici ;
- `WF-IND-0030-A` — « Une tâche dont le coût réel dépasse le montant budgété contribue pour le
  montant budgété. » : tenu par EP-10, non touché ici ;
- `WF-IND-0030-A` — « La valeur acquise d'un projet dont toutes les tâches sont terminées égale son
  budget de référence ; les tâches issues d'un risque survenu n'y contribuent pas. » : la première
  moitié est tenue par EP-10 ; les tâches issues d'un risque survenu (`origin_risk_id`), terminées,
  n'ajoutent rien à la valeur acquise, pas plus que les lignes de provision : la valeur acquise du
  projet tout terminé reste le budget de référence ;
- `WF-IND-0100-A` — « La courbe du budget de référence atteint le budget de référence à la date de
  fin de la référence. » : tenu par EP-10, non touché ici ;
- `WF-IND-0100-A` — « Celle du coût réel s'arrête à la date de calcul, et la projection part de ce
  point pour atteindre la projection du chef de projet. » : tenu par EP-10, non touché ici ;
- `WF-IND-0100-A` — « Après contractualisation d'un avenant qui porte le budget de 1 000 à 1 200, la
  courbe du budget présente, au point du mois de l'avenant, une marche égale à l'écart des deux
  cumulés à cette date, et atteint 1 200 à la date de fin de la nouvelle référence. » : `steps`
  porte la marche au point du mois de la fusion, égale à l'écart des deux budgets cumulés à cette
  date ; la série du budget lit, à chaque date, la référence alors en vigueur, et atteint 1 200 à la
  fin de la nouvelle ;
- écart : `WF-IND-0100-A` — « Avec un délai de paiement de 60 jours saisi sur toutes les lignes,
  main-d’œuvre comprise, chaque montant de la courbe du budget de référence est compté au mois de sa
  date décalée de 60 jours ; ceux de la projection le sont aussi, hormis les lignes de provision,
  qui restent à leur date ; le coût réel n’est pas décalé. » : réécrit par la spécification 1.0.7
  (#3378) : la courbe est au pas du mois ; tenu par EP-10 (#3564) ;
- `WF-IND-0100-A` — « La somme des décaissements à venir égale le reste à engager, provisions des
  risques identifiés comprises. » : la somme des `forecast` de `cash_out_by_month` égale
  `remaining`, provisions des risques identifiés comprises, au centime ;
- `WF-DEV-0080-A` — « Sur un projet dont le budget de référence est de 1 000, la valeur planifiée
  vaut 1 000 à la date de fin de la dernière tâche de la référence, et 0 avant le début de la
  première. » : tenu par EP-07 et EP-10, non touché ici ;
- `WF-DEV-0080-A` — « Une ligne portée par une tâche de deux mois comptant autant d'heures
  travaillées contribue pour moitié à la fin du premier mois. » : tenu par EP-07, non touché ici ;
- `WF-DEV-0080-A` — « Retarder une tâche dans la révision courante ne change pas la valeur
  planifiée. » : tenu par EP-07, non touché ici ;
- `WF-DEV-0080-A` — « Après contractualisation d'un avenant, la valeur planifiée totalise le nouveau
  budget de référence. » : après une fusion, la valeur planifiée se calcule sur la référence
  nouvelle et totalise son budget à la fin de sa dernière tâche ;
- propre à l'US : la modification du devis propre d'un risque identifié laisse identiques le budget
  de référence, la valeur planifiée, la valeur acquise et les indices de coût et de délai, et change
  la provision, le reste à engager, l'avancement financier et la projection du chef de projet
  (WF-RIS-0030, US-2570) ;
- propre à l'US : après une survenance, la projection du chef de projet porte le coût du risque et
  l'indice de coût le compte comme une dérive ; un avenant qui intègre au budget de référence les
  lignes d'un risque survenu rétablit l'indice de coût sans toucher la couverture (WF-RIS-0050,
  US-2610) ; une tâche démarrée qu'un avenant
  termine acquiert le budgété que ses lignes gardent (WF-REV-0050, US-2560) ;
- propre à l'US : l'empreinte du cache des indicateurs lit les compteurs de toutes les structures de
  la révision et ceux des risques (#3629) : après une saisie dans un devis propre, un réexamen, une
  survenance, une fusion ou un abandon de différentiel, aucune entrée périmée n'est servie ;
- propre à l'US : les documents conservés au marquage et à la fusion (EP-10) comptent les
  provisions, excluent les tâches de survenance de la valeur acquise et portent la couverture ; une
  lecture `as_of` antérieure à un avenant lit la référence d'alors ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Ce qu'EP-10 laisse à EP-08 (« Ce que le cadrage laisse à EP-08 ») : les
marches d'avenant, les lignes de provision dans la projection et les décaissements, l'exclusion des
tâches de survenance (déjà écrite dans la sélection des lignes), la couverture dans le document
`remaining`, les compteurs de l'empreinte. Cette US attend, dans `main`, le calcul du jour, la
conservation, la lecture conservée, les courbes et le cache d'EP-10.

**Hors périmètre.** Le calcul des indicateurs lui-même (EP-10) ; le portefeuille (EP-11) ; l'écran
des indicateurs, inchangé.

---

## US-2640 — Les écrans des risques et des avenants, branchés sur le service

- **statut** : à faire
- **exigences** : `WF-IHM-0020-A`
- **opérations** : celles des US-2550 à US-2630 et d'US-3050, par le client engendré ;
  `deleteCostStructure` et `rebaseCostStructure` (les gestes nouveaux)
- **issue** : #3820
**En tant que** chef de projet, **je veux** que le registre des risques, le détail d'un risque, son
devis propre, sa revue, sa survenance, et la préparation, la contractualisation et l'abandon d'un
avenant fassent contre le service ce que la maquette montrait, **afin de** mener une revue des
risques et un avenant de bout en bout.

**Critères d'acceptation.**

- `WF-IHM-0020-A` — « Chaque écran de données de projet nomme le projet et la révision affichée ;
  une grille ouverte sur une structure différentielle nomme cette structure. » : le projet et la
  révision, tenus par EP-02 ; une grille ouverte sur un différentiel ou sur le devis propre d'un
  risque nomme cette structure, constaté contre le service ;
- `WF-IHM-0020-A` — « L'ouverture d'une révision marquée présente cet état et ne propose aucune
  commande de modification. » : tenu par EP-02, non touché ici ;
- `WF-IHM-0020-A` — « Un indicateur affiché porte sa date de calcul. » : tenu par EP-02 et EP-10,
  non touché ici ;
- `WF-IHM-0020-A` — « Un filtre actif est visible sans avoir à ouvrir le panneau de filtres. » :
  tenu par EP-02 et EP-25, non touché ici ;
- `WF-IHM-0020-A` — « Depuis la grille de devis de la révision en cours, l'utilisateur choisit une
  révision marquée pour base sans quitter l'écran ; l'écran la nomme, et la comparaison se lève sans
  ouvrir aucun panneau. » : tenu par EP-27, non touché ici ;
- `WF-IHM-0020-A` — « Depuis la même grille, il ouvre une autre révision du projet sans passer par
  l'historique. » : tenu par EP-27, non touché ici ;
- propre à l'US : contre le service, les écrans des risques — registre, filtres, totaux, matrice,
  couverture, détail, formulaires de déclaration, d'identité et de provision, réexamen, revue
  périodique, devis propre, compte rendu de survenance — et ceux des avenants — « Préparer un
  avenant », le choix de la structure, le compte rendu et « Contractualiser l'avenant » —
  aboutissent, chacun suivant les commandes que le service rend ; l'avenant créé s'ouvre (#1363), la
  structure du risque créé est listée (#1369) ;
- propre à l'US : « Abandonner l'avenant », geste nouveau, demande confirmation, appelle
  `deleteCostStructure` et ramène à la structure principale ; il n'est offert que sur un
  différentiel non fusionné de la révision en cours, et l'aide en ligne de l'écran le dit ;
- propre à l'US : sur un avenant en retard, l'écran le dit et offre « Mettre à jour l'avenant », qui
  présente le compte rendu de `getStructureRebaseReport` — ce qui est reporté, ce que l'avenant
  garde, ce qui refuse — avant de confirmer par `rebaseCostStructure`, puis relit la grille ;
  « Contractualiser l'avenant » n'est offert que sur un avenant à jour, et l'aide en ligne le dit
  (reprise du 2026-11-19, US-3050) ; le compte rendu d'une survenance présente les tâches que la
  greffe redate et le signalement d'un devis propre qui commence avant le jour (#4133, #4134) ;
- propre à l'US : après une écriture dans le devis propre d'un risque, l'écran relit le risque avant
  sa prochaine écriture, et un 412 se résout par une relecture (#1626, décision de l'auteur du
  2026-11-17 : le contrat ne change pas) ;
- propre à l'US : le succès de « Déclarer survenu » — son message et la relecture du risque survenu
  — est éprouvé contre le service (#1830) ; la promesse qui retient l'origine d'un filtre sur un
  risque nommé a son gestionnaire quand la lecture des risques rejette (#1972) ;
- propre à l'US : les parcours de bout en bout que `inService` gardait jusqu'à EP-08 pour un risque,
  une provision ou un différentiel sont rejoués contre le service ou réécrits, et le guide ne les
  liste plus comme non rejoués ; les écrans passent l'audit d'accessibilité.

**Notes de réalisation.** Aucune réponse écrite à la main : le faux back sert les exemples du
contrat, le client est engendré. Les écrans existent depuis EP-15 et EP-17 dans la présentation
d'EP-25 ; cette US ne les redessine pas.

**Hors périmètre.** Les risques du portefeuille (EP-11) ; la refonte d'un écran.

---

## US-2650 — Le témoin : les risques, les provisions et les avenants de PRJ-001, et le parcours du chef de projet

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`, `WF-INTF-0010-A`
- **opérations** : celles des US-2550 à US-2630, lues sur le témoin chargé
- **issue** : #3821
**En tant que** développeur, **je veux** que le témoin chargé dans le service porte les risques, les
provisions et les avenants de PRJ-001, et que la référence y soit celle que la fusion de l'avenant 1
a produite, **afin que** les exemples du contrat soient l'attendu du service sur toute la
chronologie, et que le chef de projet mène sa dernière fonction jusqu'au bout.

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour la tranche des risques et des avenants — les trois risques de PRJ-001, leur
  identité, leurs devis propres, leurs réexamens datés, leurs lignes de provision ; la révision 101
  ouverte le 12 janvier 2026 par leur identification et marquée le 1er février par la fusion de
  l'avenant 1, qui en fait la référence ; la révision 102 ouverte le 2 février par un réexamen ; la
  survenance de 752 le 20 février ; l'avenant 2, non fusionné —, chargée par `waterfall-api
  load-witness` par les interfaces, avec les identifiants et les instants du témoin ; les volumes
  entiers sont d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes identiques. »
  : deux chargements successifs donnent les mêmes risques, structures, réexamens et lignes,
  identifiants compris ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les libellés des risques et des avenants sont ceux du témoin ;
- `WF-INTF-0010-A` — « Un utilisateur porteur du rôle prédéfini « chef de projet » crée un projet et
  atteint, sur un projet où il est habilité, les fonctions de gestion des révisions (FBS-4.1), de
  paramétrage du projet, contributeurs compris (FBS-4.2), de planification (FBS-4.3), de chiffrage
  (FBS-4.4), de gestion des risques (FBS-4.6), d'estimation du reste à engager (FBS-4.5), de gestion
  des coûts réels (FBS-4.7), de lecture des indicateurs (FBS-4.8), de sortie du cycle de vie
  (FBS-4.9) et d'échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les mène jusqu'à
  leur terme, marquage d'une révision, exclusion d'une ligne de coût et déclaration d'une sortie
  compris. » : la gestion des risques (FBS-4.6), ici, par le compte « chef de projet » de la course,
  sur un projet qu'il crée : il déclare un risque, chiffre son devis propre, le réexamine, le
  déclare survenu, prépare un avenant et le contractualise ; les autres fonctions sont constatées
  par EP-04, EP-06, EP-07, EP-09 et EP-10, et cette US, qui clôt, les rejoue toutes dans une même
  course ;
- propre à l'US : sur le témoin chargé, les lectures du service sont comparées aux exemples du
  contrat — le registre, le détail, les réexamens, la matrice, la couverture, les structures, le
  devis propre, les comptes rendus de fusion et de survenance, la comparaison — ; la spécification
  arbitre un désaccord, et la fixture se corrige ;
- propre à l'US : la référence du témoin chargé est la révision 101 : les écarts « à la référence
  près » que listent EP-07, EP-09 et EP-10 sont levés, et leurs lectures — devis, reste à engager,
  indicateurs, courbes — sont comparées aux exemples sans cette réserve ;
- propre à l'US : le parcours de bout en bout de la définition de fini déclare un risque, le fait
  survenir et contractualise un avenant, contre le service ; la liste des parcours non rejoués du
  guide est mise à jour.

**Notes de réalisation.** Les quatre règles du jeu de données de référence (README de la roadmap) :
le saisi se charge par les interfaces, le calculé devient l'attendu. La révision 101 est aujourd'hui
chargée telle que marquée, ses lignes écrites avant son marquage (EP-07), et l'offre 100 reste la
référence (EP-10 : « Écarté : désigner la 101 après coup ») : la conception dit comment la tranche
rejoue la fusion. `docs/api/DECISIONS.md`, « L'univers témoin », « Révisions et risques ».

**Hors périmètre.** Les trois cents projets et les volumes du §4.6.2 (EP-13) ; le portefeuille
(EP-11).

---

## US-2660 — Les constats reçus sont soldés

- **statut** : fini
- **exigences** : aucune en propre — les exigences de ces fonctions sont closes par EP-06, EP-07 et
  EP-09
- **opérations** : `openImport`, `listImports`, `getImport`, `applyImport`
- **issue** : #3811
**En tant que** développeur, **je veux** que les constats rattachés à cet EPIC par la ventilation du
2026-11-14 soient corrigés, **afin qu'** il ne laisse pas derrière lui la dette qu'il a reçue.

**Critères d'acceptation.**

- propre à l'US : les routes des imports ne demandent que la visibilité du projet, et la
  consultation du genre d'import est jugée dans `core/exchanges` : `listImports` ne rend que les
  genres que l'appelant lit, `getImport` répond 404 pour un genre qu'il ne lit pas, et un chiffreur
  qui ne lit pas le planning ouvre, lit et applique l'import de son devis ; le test de l'évaluation
  des accès admet ces routes (#2473, décision de l'auteur du 2026-11-17) ;
- propre à l'US : le refus d'un cycle de parenté par le chargeur des tâches nomme la tâche en cause,
  et son test éprouve le type et l'auto-parenté (#2883) ; un `parent_lineage_id` absent de la
  description est refusé par un message qui le nomme, non par un `KeyError` (#2884) ;
- propre à l'US : une ligne d'import dont le montant déborde est rejetée au compte rendu en étant
  nommée, et l'application n'échoue plus en entier (#3095) ;
- propre à l'US : le corpus MS Project : `10-other-constants.xml` porte un calendrier cohérent avec
  ses constantes ou est déclaré en écart de calendrier (#3154) ; le test « constantes différentes ⇒
  écart » ne peut plus passer à vide, et l'en-tête du README du corpus est recoupé (#3156) ; les
  trois mineurs du parcours de l'écart de calendrier sont corrigés (#3165).

**Notes de réalisation.** Chaque constat garde son issue, rattachée au lot qui le corrige. Les
constats reçus qui touchent le code des risques et des avenants sont portés par l'US de ce code :
#1767, #2497, #2499 et #2541 par US-2550 ; #1783 par US-2570 ; #2538 et #2905 par US-2590 ; #1786
par US-2600 ; #2002 par US-2610 ; #1762 par US-2620 ; #1363, #1369, #1626, #1830 et #1972 par
US-2640.

**Hors périmètre.** Tout constat relevé pendant la livraison, rattaché selon « Suivi sur GitHub ».

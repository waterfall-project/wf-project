---
id: EP-09
titre: Suivre ce qui a été dépensé, et réestimer ce qui reste à engager
statut: en cours
depend_de: EP-07
famille: front, back
issue: 2389
---

# EP-09 — Coûts réels, reste à engager et import des coûts

## Objet

Le Kanban de démarrage des tâches, la grille de reste à engager, sa composition et ses
indicateurs ; les coûts réels importés de l'ERP (FLX-07), leur imputation par élément d'OTP,
l'exclusion du périmètre suivi, la consultation et le journal des imports ; l'import et l'export
du reste à engager au format Excel de l'annexe B (FLX-05, FLX-06), dont l'aller-retour se valide
ici. Ces imports reprennent la mécanique en deux temps qu'EP-06 a construite pour MS Project
(revue de la ventilation, 2026-10-09 : EP-12 abandonné).

L'import des coûts est ici parce qu'une ligne de coût n'existe que par import
(WF-CRE-0010) : sans lui, cet EPIC n'aurait aucun coût réel et EP-10 aucun indice de coût. Il
vient avant les risques parce que la survenance d'un risque se chiffre par le reste à engager,
et que la fusion d'un différentiel conserve les montants réestimés et épargne les tâches
démarrées.

## Ce qui en fait partie

- la réestimation d'une ligne depuis la grille (`setLineRemaining`), ce qu'elle garde du reste à
  engager précédent, et la mise à zéro qui termine une tâche ;
- le Kanban : démarrer une tâche, rouvrir une tâche terminée, servi contre le service et mesuré
  sur les mille tâches de PRJ-001 ; la récapitulative qui n'attend plus que ses lignes propres,
  signalée et terminée par leur reste ;
- la grille de reste à engager, la composition du reste et ses indicateurs, l'ensemble « hors
  sous-projet » compris, et la couverture des risques servie à zéro, par une question qu'EP-08
  remplit ;
- l'ajout de tâches et de lignes en cours d'exécution, à montant budgété nul ;
- le plan de charge calculé sur le reste à engager ;
- la suppression d'une tâche démarrée, refusée et renvoyée vers la mise à zéro de son reste ;
- l'import des coûts réels (FLX-07) : l'extraction de l'ERP, lue selon la correspondance du
  référentiel (WF-REF-0190, que cet EPIC clôt), idempotente sur le triplet projet, numéro de
  pièce et numéro de poste (WF-DAT-0110, D-4) ;
- l'imputation par élément d'OTP, l'exclusion et la réintégration d'une ligne, la consultation,
  le journal des imports ;
- l'import et l'export du reste à engager (FLX-05, FLX-06), sur la mécanique d'import d'EP-06,
  et tous les formats de l'annexe B, avec leur version ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — les cinq imports de coûts réels de
  PRJ-001, leurs vingt-huit lignes, l'exclusion de la réception du client, l'extraction d'avril
  rejouée et expirée —, chargée par le chargeur par les interfaces, aux instants de la
  chronologie ; le reste à engager précédent des lignes de la révision 102 vient de la référence
  101, par la copie ;
- les écrans du reste à engager, du Kanban et des coûts réels de la maquette, branchés sur le
  service, et les parcours écrits sur le faux back rejoués contre lui.

## Ce qui n'en fait pas partie

- l'échange MS Project — EP-06 ; celui du devis — EP-07 ;
- les indicateurs de projet, dont l'indice de coût que dégradent les tâches ajoutées, et la
  valeur acquise — EP-10 ;
- les risques, leurs lignes de provision et la couverture des risques — EP-08 : ce que le reste à
  engager, le Kanban, l'import du reste à engager et le passage d'une ligne à un autre sous-projet
  en disent se clôt là ;
- les extractions complémentaires de l'ERP — commandes engagées, heures consommées — que le point
  ouvert PO-01 de la spécification nomme : relu au cadrage (décision de l'auteur du 2026-11-07),
  EP-09 importe les coûts payés tels que l'annexe B et la correspondance les décrivent, et PO-01
  reste ouvert ; ce qu'il changerait — une seconde correspondance, un second format, des colonnes
  d'engagement et d'heures sur la ligne de coût — passe par la spécification, puis par une issue
  « contrat » ;
- les sauvegardes, second compartiment du stockage objet — EP-03 et EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
WF-PLA-0070 est commencée par EP-06 et close ici : son Vérif demande le renvoi vers la mise à zéro
du reste à engager (cadrage d'EP-06, décision de l'auteur du 2026-11-07). WF-REV-0060 et
WF-REF-0010 sont commencées par EP-07 et closes ici : leur Vérif demande un import de reste à
engager et la grille de reste à engager (cadrage d'EP-07, décision de l'auteur du 2026-11-07).
Sept exigences que le fichier disait entières ou closes ici ont une phrase de Vérif qui demande
une ligne de provision, un risque ou la valeur acquise : WF-RAE-0010, WF-RAE-0020, WF-PLA-0040,
WF-PLA-0050, WF-PRJ-0050 et WF-INTF-0120 se commencent ici et se closent en EP-08, WF-RAE-0030 en
EP-10 (décision de l'auteur du 2026-11-07, au cadrage d'EP-09) ; les tableaux de ces EPIC les
reçoivent. Deux exigences qu'EP-09 réalise en partie entrent au tableau en portée « début », pour
que les US du témoin les citent et que les tests les nomment (même décision) : WF-QUA-0040 et
WF-INTF-0010. Chaque US cite les exigences dont une phrase de Vérif tient avec des tâches, des
lignes, des coûts réels, le référentiel et les révisions ; les phrases qui demandent plus sont des
écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-RAE-0010-A` | Composition du reste à engager | début — close en EP-08 | US-1580 |
| `WF-RAE-0040-A` | Grille de reste à engager | fin — amorcée en EP-15 | US-1580, US-1640 |
| `WF-RAE-0050-A` | Tâches ajoutées en cours d’exécution | début — close en EP-10 | US-1580 |
| `WF-DEV-0070-A` | Plan de charge du projet | fin — amorcée en EP-15, EP-07 | US-1580 |
| `WF-RAE-0030-A` | Démarrage d’une tâche | début — close en EP-10, amorcée aussi en EP-15 | US-1590, US-1640 |
| `WF-PLA-0040-A` | Hiérarchie des tâches | début — close en EP-08, amorcée aussi en EP-06, EP-22 | US-1590 |
| `WF-PLA-0050-A` | Jalons | début — close en EP-08, amorcée aussi en EP-06 | US-1590 |
| `WF-PLA-0070-A` | Suppression d’une tâche | fin — amorcée en EP-06 | US-1590 |
| `WF-RAE-0020-A` | Indicateurs de reste à engager | début — close en EP-08 | US-1600 |
| `WF-INTF-0140-A` | Import des coûts réels (FLX-07) | entière | US-1610 |
| `WF-REF-0190-A` | Correspondance de l’extraction des coûts réels | fin — amorcée en EP-05, EP-16 | US-1610 |
| `WF-CRE-0010-A` | Attributs d’une ligne de coût | entière | US-1610 |
| `WF-CRE-0020-A` | Imputation d’une ligne de coût | entière | US-1610 |
| `WF-CRE-0050-A` | Journal des imports | entière | US-1610 |
| `WF-DAT-0110-A` | Idempotence garantie par la base | fin — amorcée en EP-07 | US-1610 |
| `WF-DAT-0070-A` | Colonnes d’audit | fin — amorcée en EP-03 | US-1610 |
| `WF-INTF-0070-A` | Formats d’échange Excel | fin — amorcée en EP-07 | US-1610, US-1630 |
| `WF-CRE-0030-A` | Exclusion du périmètre suivi | entière | US-1620 |
| `WF-CRE-0040-A` | Consultation des coûts réels | entière | US-1620 |
| `WF-PRJ-0050-A` | Sous-projets | début — close en EP-08, amorcée aussi en EP-15, EP-16, EP-04 | US-1620 |
| `WF-CYC-0100-A` | Lecture seule des projets terminaux | fin — amorcée en EP-04 | US-1620 |
| `WF-CYC-0110-A` | Consultation des projets terminaux | fin — amorcée en EP-04 | US-1620 |
| `WF-INTF-0120-A` | Import du reste à engager (FLX-05) | début — close en EP-08 | US-1630 |
| `WF-INTF-0130-A` | Export du reste à engager (FLX-06) | entière | US-1630 |
| `WF-REV-0060-A` | Année de référence et mise à jour des taux à la création d’une révision | fin — amorcée en EP-15, EP-07 | US-1630 |
| `WF-IHM-0080-A` | Traitements longs | fin — amorcée en EP-02, EP-15, EP-04 | US-1630 |
| `WF-REF-0010-A` | Désactivation des objets du référentiel | fin — amorcée en EP-05, EP-07 | US-1640 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06, EP-07 | US-1650 |
| `WF-INTF-0010-A` | Usages du chef de projet | début — close en EP-08, amorcée aussi en EP-06, EP-07 | US-1650 |

## Opérations du contrat

Servies ici pour la première fois (6) :

- `revisions` : `setLineRemaining` (US-1580) ;
- `analysis` : `listStartableTasks` (US-1590), `getRemainingIndicators` (US-1600) ;
- `costs` : `listCostImports` (US-1610), `listActualCosts`, `setActualCostTrackedScope`
  (US-1620).

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute :

- `revisions` : `listNodes` (`remaining_entry`, `previous_*`, le filtre `progress`,
  `awaiting_own_lines`), `createRevision` (le reste à engager précédent copié), `setTaskProgress`
  (le Kanban qui la branche, la récapitulative terminée par son reste), `deleteNode` (le renvoi
  vers la mise à zéro), `updateEstimateLine`, `createNode`, `moveNodes` (`SUBPROJECT_HAS_ACTUAL_COSTS`
  qui manque désormais, la grille de reste à engager qui les saisit) ;
- `analysis` : `getProjectWorkload` (`current_remaining`, `marked_remaining` sur le reste réestimé) ;
- `projects` : `getProject` (`import_actual_costs`, `exclude_cost_lines`), `listSubprojects`
  (`has_actual_costs`), `createSubproject` (les lignes qui attendaient son code), `deleteSubproject`
  (`subproject_without_actual_costs`) ;
- `exchanges` : `uploadFile`, `listImports`, `openImport`, `getImport`, `abandonImport`,
  `applyImport` — le reste à engager et les coûts réels —, `requestExport`,
  `getBackgroundTaskResult` — le reste à engager.

Aucune opération ne manque au contrat, figé en 1.0.0 : un écart devient une « Interface contract
issue » que l'auteur tranche.

## Préalables

`epic/EP-09` se tire d'`epic/EP-07` dès la fusion de son lot pivot, **US-1490/L1 #2370** — le socle
d'EP-07, qui pose `estimate_line` avec ses grandeurs courantes et de référence, ses trois montants,
son délai de paiement et son sous-projet, les tables images, et l'interface de `core/estimate` déclarée
(`update_line`, que `setLineRemaining` étendra ; `revision_has_lines`) —, et non de `main` à la livraison
d'EP-07 (décision de l'auteur du 2026-11-07, pour toute la série EP-06 → EP-07 → EP-09 → EP-10 → EP-08 ;
l'exception du README, « Branches ») : elle reprend `epic/EP-07` à chaque lot que celui-ci fusionne et se
fusionne dans `main` après elle. Le premier lot d'EP-09, son socle, étend `core/estimate` et en réexporte
ses fonctions : il attend **US-1490/L4 #2373**, dernier lot d'EP-07 à écrire `core/estimate/interface/__init__.py`
et les questions du référentiel de ce module (décision de l'auteur du 2026-11-07, au cadrage d'EP-09) ; c'est
donc à la fusion de #2373 que la branche se tire, en pratique. Les lots d'EP-09 qui réestiment des lignes
attendent aussi US-1490/L3 #2372 (la ligne lue, créée, modifiée, chiffrée), ceux du Kanban US-1410 #2324
d'EP-06, US-1380/L2 #2335, L3 #2338 et US-1390/L2 #2339 ; chaque lot nomme ceux qu'il attend par leur numéro.
Le reste à engager part des montants budgétés.

Le point ouvert PO-01 (extraction des engagements et des heures par l'ERP) a été relu au cadrage :
EP-09 réalise FLX-07 tel que l'annexe B le décrit, et PO-01 reste ouvert (« Ce qui n'en fait pas
partie »).

EP-16 livré, le contrat figé en 1.0.0 : un écart devient une « Interface contract issue » que
l'auteur tranche.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.5 et du §3.4.5.7 qui ne citent ni risque, ni ligne de
  provision, ni valeur acquise sont des tests qui passent (WF-QUA-0020) ;
- un fichier de coûts réels conforme à l'annexe B s'importe en deux temps, et un abandon laisse
  le projet inchangé ;
- deux imports du même fichier laissent les mêmes lignes, et une ligne exclue le reste ;
- l'interruption de l'application laisse le projet dans son état antérieur ; un compte rendu
  expiré ne s'applique plus, et son fichier n'est plus sur le stockage objet ;
- une tâche démarrée au Kanban voit ses lignes réestimables, et la mise à zéro de son reste la
  termine ;
- un reste à engager s'exporte en Excel, se réimporte sans écart, et une tâche dont le fichier met
  toutes les lignes à zéro est terminée à la date de la revue ;
- le parcours de bout en bout importe des coûts réels et réestime un reste, contre le service
  réel ; PRJ-001, chargé, porte ses coûts réels et son journal des imports ;
- `make check` passe sur la branche de l'EPIC, les tests du back citent leurs exigences, et aucun
  fichier de `docs/api` ne change hors d'une « Interface contract issue » tranchée.

## Constats reçus

Relevés par la revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`)
et tranchés par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), que le service
suit une fois figé.

- #1775 — `awaiting_own_lines`, la récapitulative qui n'attend plus que ses lignes propres (F-05 ;
  contrat #1774). US-1590.
- #1851, reporté à EP-22 (US-1240) — `listStartableTasks` liste aussi la récapitulative démarrée qui
  n'attend plus que ses lignes propres, avec ses gestes (décision de l'auteur du 2026-11-04) : le
  service le sert tel que le contrat le dit. US-1590.
- #1794 — l'import du reste à engager rejette la ligne nouvelle sous une tâche terminée (I-05 ;
  contrat #1793). US-1630.

- #1340, pour #1304, points 3, 4 et 5 — le service de la reprise de la spécification du 2026-10-22 (#1306, C-371 à C-375 ; #1304), dont EP-16 écrit le contrat, le faux back et les écrans (décision de l'auteur du 2026-10-22, au cadrage d'EP-16) :
  - la lecture de l'extraction selon la correspondance qu'EP-05 stocke : le refus tant
    qu'elle est incomplète, la colonne exigée absente nommée, les colonnes ignorées nommées au
    compte rendu, les colonnes conservées restituées (WF-REF-0190, WF-CRE-0010,
    WF-INTF-0070) ;
  - le poste d'une ligne de coût : la contrainte d'unicité sur le projet, la pièce et le poste,
    sa migration, et deux lignes du fichier de même pièce et de même poste rejetées au compte
    rendu (WF-INTF-0140, WF-DAT-0110) ;
  - l'élément d'OTP : le code projet, préfixe compris, puis la barre oblique et le code
    sous-projet ; seule la barre oblique sépare les deux codes (WF-CRE-0020, C-373).
  US-1610.

- #1525 — front : le test de la colonne « Poste » cite WF-CRE-0040-A, dont le Vérif ne nomme pas
  les colonnes de la grille (relevé par US-0630/L2, EP-16 ; reporté ici avec #1340, le service du
  poste, par la décision de l'auteur du 2026-10-27, confirmée au cadrage d'EP-17 le 2026-10-28) :
  la citation se corrige quand EP-09 réalise le poste. US-1620, qui branche l'écran : le test cite
  WF-CRE-0010-A, dont le corps nomme le poste parmi les attributs d'une ligne.
- #2093 — front : l'aide FBS-3.1.3 (fr, en) et les messages `reference.actualCostMapping.complete`
  et `.missing` de `/reference/costs/actual-cost-mapping` à reprendre quand l'import lit la
  correspondance (relevé par US-0870, EP-05) : l'aide dit l'import « pas encore offert », les
  messages disent le refus que l'import tiendra. US-1620.

- #646 [EP-09] front : le Kanban rend ses 960 cartes en listes simples, sans fenêtre — relevé par
  EP-14/L45b : EP-09, qui construit le Kanban contre le service, mesure sur mille tâches réelles
  avant toute optimisation ; EP-14 garde les listes simples sous le délai `WORKING`. Reporté
  d'EP-14 (2026-10-10), puis d'EP-06 à EP-09 au cadrage d'EP-06 (décision de l'auteur du
  2026-11-07) ; l'issue est retitrée et relabellisée à l'ouverture des issues d'EP-06. US-1590 : la
  mesure sur les mille tâches de PRJ-001 contre le service, et la raison corrigée dans le guide ;
  une optimisation, si la mesure la demande, devient une issue.

Le rattachement de WF-REF-0190 est réécrit au cadrage d'EP-16 (décision de l'auteur du
2026-10-22). C-374 la rattachait entière ici ; EP-05 la commence en stockant la correspondance,
EP-16 en écrit le contrat et la page, et EP-09 la clôt.

## Conception

EP-09 est le cinquième EPIC de domaine du back, et le premier qui lit une dépense : il étend le
module du devis d'EP-07 au reste à engager — six colonnes de plus sur `estimate_line`, la
réestimation, le Kanban, les indicateurs et le format Excel du reste à engager —, ajoute un module
du noyau pour les coûts réels et ses deux tables, les routes de ses six opérations nouvelles, deux
formats d'échange sur la mécanique d'EP-06, la tranche des coûts du témoin, et il branche sur le
service les écrans du reste à engager, du Kanban et des coûts réels. Il **ne modifie le contrat**,
figé en 1.0.0, que par les « Interface contract issue » que l'auteur a tranchées, chacune inscrite
dans `docs/api/DECISIONS.md` par le lot qui l'écrit (« Les décisions du 2026-11-10 ») : un manque
devient une issue de contrat. Ce qui suit fixe ce que chaque lot devrait sinon décider seul. Il se livre pendant les
lots d'EP-07 et les derniers d'EP-06, sur une branche tirée de celle d'EP-07 : les sections « Ce
qu'EP-07 écrit encore » et « Ce qu'EP-06 écrit encore » disent ce que les lots d'EP-09 n'écrivent
pas avant le lot qui le possède.

### Ce que le cadrage décide

Décisions de l'auteur du 2026-11-07, sur les questions du cadrage, chacune avec l'option écartée :

- **Huit US, le socle en lot technique de la première**, lot pivot d'EP-10 ; les indicateurs à
  part parce qu'ils lisent les coûts et le reste à engager. Écartés : les indicateurs fondus dans
  la réestimation ; l'export et l'import du reste à engager en deux US, pour un seul Vérif.
- **Sept portées recalées** (voir « Exigences réalisées »), comme EP-06 et EP-07 l'ont fait : une
  phrase de Vérif qui demande une ligne de provision, un risque ou un avenant se clôt en EP-08, la
  valeur acquise en EP-10. Écarté : clore ici avec des écarts, contre la règle du README.
- **WF-QUA-0040 et WF-INTF-0010 entrent au tableau** en portée « début ». Écarté : les laisser en
  « propre à l'US ».
- **PO-01 reste ouvert** : FLX-07 tel que l'annexe B le décrit, les coûts payés ; rien n'est
  préparé pour les engagements ni les heures. Écartés : des colonnes spéculatives sur `cost_line` ;
  une issue de spécification qui aurait suspendu le cadrage.
- **Le reste à engager est une extension de `core/estimate`** (FBS-4.5 : « il n'introduit aucun
  objet : ce sont les lignes de devis vues sous un autre angle »), dans un sous-paquet `remaining/`
  et des fichiers d'interface qu'EP-09 possède, et six colonnes de plus sur `estimate_line`. Le
  socle réexporte ses fonctions dans `core/estimate/interface/__init__.py` et attend donc
  **US-1490/L4 #2373**, dernier lot d'EP-07 à écrire ce fichier et les questions du référentiel de
  ce module ; EP-07 est en vague 3 quand EP-09 démarre, le délai est court. Écarté : un module
  `core/remaining` avec une table 1:1 (`line_remaining`) qui n'écrit rien dans `core/estimate`, au
  prix d'un registre de lecture pour que `listNodes` rende `previous_*`, et d'une facette
  reconstituée à partir de deux tables pour quatre colonnes.
- **Les coûts réels sont un module propre, `core/costs`** (FBS-4.7), qui possède `cost_line` et
  `cost_import`, deux tables du régime « projet » (Tableau 10) ; `estimate` l'importe pour les
  indicateurs, lui n'importe ni `estimate` ni `planning`. Écarté : les coûts dans `core/estimate`,
  qui aurait mêlé une dépense sans révision aux lignes d'une révision.
- **« Le reste à engager précédent » est celui de la dernière révision marquée à l'état En cours**,
  copié à l'ouverture d'une révision par un second enregistrement de `register_copy`, après la
  copie des lignes d'EP-07 : `previous_*` reçoivent les grandeurs et le réestimé courants de la
  ligne source si celle-ci appartient à une révision marquée après le passage En cours du projet
  (l'instant de la transition, lu par l'interface des projets, comparé à `marked_at`) ; nuls sinon
  — une offre marquée en chiffrage n'est pas une revue (`delta_to_previous_revision`) — et pour
  une ligne créée depuis. Écartés : la copie depuis toute révision marquée, qui montrerait un
  « reste précédent » sans revue ; la jointure à la lecture avec la révision marquée précédente,
  cinq mille lignes jointes à chaque lecture ; une colonne `marked_in_progress` sur `revision`.
- **Une ligne réestimée porte une marque**, `reestimated_at`, posée par `setLineRemaining` et par
  l'import du reste à engager, jamais par la saisie du devis ni par la copie ; c'est ce que la
  fusion d'un avenant (EP-08) lira pour épargner une ligne réestimée (WF-RAE-0010, « une ligne
  réestimée à 140 avant l'avenant garde 140 »). Écarté : comparer les grandeurs courantes aux
  grandeurs de référence, qui ne distinguerait pas une ligne réestimée à sa valeur de référence.
- **`RemainingUpdate.reason` est conservé sur la ligne** (`remaining_reason`), écrasé à chaque
  réestimation (F-09 de la revue du 2026-10-31) ; le constat « contrat » #2420, ouvert avec les
  issues de l'EPIC, est tranché le 2026-11-10 : la lecture le rend par
  `EstimateLineFacet.remaining_reason` (« Les décisions du 2026-11-10 »). Écartés : ne pas le
  conserver ; trancher au cadrage une modification du contrat figé.
- **La question des lignes propres ouvertes est un registre de `core/planning`**,
  `register_open_lines`, déclaré par EP-09 dans un fichier nouveau de l'interface de `planning`
  (`open_lines.py`), réexporté par `core/planning/interface/__init__.py` — qu'EP-06 écrit encore
  jusqu'à US-1390/L2 #2339, qui y importe le moteur — et rempli par `estimate` : « parmi ces tâches, lesquelles portent une ligne
  propre hors provision dont le reste n'est pas nul ». `planning` l'appelle pour terminer une
  récapitulative dont la dernière subordonnée se termine, pour `awaiting_own_lines`, et pour la
  feuille qu'une récapitulative devient ; il n'écrit pas `FacetHooks` (`facets.py`), que #2335,
  #2372, #2373 et #2382 écrivent encore. Écarté : un crochet de plus dans `FacetHooks`, qui aurait
  attendu le collage d'EP-07 (#2382), en vague 4.
- **Les commandes nouvelles s'écrivent après le dernier lot d'EP-07 qui tient leur fichier** :
  `import_actual_costs`, `exclude_cost_lines` et `import_remaining` dans `RULES` de
  `core/projects/commands.py` par un seul lot d'EP-09, après US-1550/L3 #2380 ; `export_remaining`
  dans `REVISION_RULES` de `core/revisions/commands.py` par un seul lot, après US-1550/L4 #2381 ;
  les autres lots en dépendent par leur numéro. Écarté : un registre de commandes dans
  `core/projects`, qui changeait la mécanique d'EP-04 pour trois lignes.
- **La couverture des risques est servie à zéro par un registre**, `register_coverage`, déclaré
  par le socle dans `core/estimate` et vide jusqu'à EP-08 : réserve, provisions restantes, coût des
  survenus et écart nuls, ce qui est vrai d'un projet sans risque ; la nature provision compte zéro
  dans `by_cost_type`. Écarté : lire des tables qui n'existent pas.
- **Le témoin charge ses imports par les interfaces, sans fichier ni worker** : une fonction
  `load_import` de `core/exchanges` écrit une ligne d'`import_report` à son instant, dans son état,
  sans dépôt — écrite par EP-09 dans un fichier nouveau de l'interface d'`exchanges` après
  US-1420/L2 #2341, dernier lot d'EP-06 à écrire ce module — ; `load_cost_import` et
  `load_cost_lines` de `core/costs` écrivent le journal et les lignes aux identifiants imposés ;
  l'exclusion passe par la fonction de `setActualCostTrackedScope` à son instant. Écarté : rejouer
  cinq classeurs engendrés par le moteur d'import, qui exige le stockage objet et le worker dans
  une commande d'une seule transaction, et des fixtures binaires.
- **Une seule migration, `0027`, dans le socle**, au prochain numéro libre à la création
  d'`epic/EP-09` — `epic/EP-07` s'arrête à `0026`, la création des partitions sans verrou mortel
  d'US-1560/L3 (décision du 2026-11-09, #2603 et #2667) —, aucune donnée à reprendre : les colonnes
  nouvelles d'`estimate_line` naissent nulles. Aucune migration d'EP-09 après le socle ; EP-10
  chaîne la sienne sur `0027`. Écarté : une migration par US.
- **XlsxWriter écrit, openpyxl lit**, comme EP-07 l'a décidé : le prototype
  `docs/spec/exemples/prototype_rae.py` vaut pour le reste à engager ce que `prototype_devis.py` a
  valu pour le devis ; `sheet_name` d'EP-07 nomme les onglets des sous-projets (#2190, option B).
  Rien n'entre dans `pyproject` : les deux bibliothèques y sont depuis le socle d'EP-07.
- **Le reste d'une ligne se saisit, dans le fichier, en jours ou en montant, et se range dans les
  grandeurs** : pour une ligne de main-d'œuvre, « Jours restants » vaut quantité × charge ÷ heures
  par jour à l'export, et l'import écrit la charge, jours × heures par jour ÷ quantité, la quantité
  conservée (portée à 1 si elle est nulle) ; pour une ligne hors main-d'œuvre, « Débours restant »
  est le réestimé inflation comprise, et l'import écrit le débours unitaire, montant ÷ (quantité ×
  coefficient d'inflation de la tâche), arrondi au centime, la quantité conservée de même. Une
  division suivie d'un arrondi ne redonne pas la grandeur de départ : pour chaque ligne connue,
  l'analyse recalcule la valeur que l'export aurait écrite et ne touche la ligne que si la cellule en
  diffère — un classeur réimporté sans modification ne produit aucun écart, par construction
  (WF-INTF-0130), sans colonne de plus que l'annexe B. Écartés : une quantité ramenée à 1 à chaque
  import, qui perdrait une grandeur saisie ; un montant écrit tel quel dans le débours unitaire, qui
  ferait réestimer quantité fois trop ; les grandeurs brutes masquées dans le classeur à côté de la
  lignée, relues quand la cellule visible n'a pas changé, qui changeait le format.
- **Le recodage d'un sous-projet ne change l'imputation d'aucune ligne** (D-10 de la revue) : les
  lignes imputées le restent par leur identifiant (WF-DAT-0060), celles qui attendaient l'ancien ou
  le nouveau code ne bougent qu'à leur réimport ; la création d'un sous-projet impute aussitôt les
  lignes de son code (WF-CRE-0020). Le constat « contrat » #2421 est tranché le 2026-11-10 : la
  règle est acceptée, `DECISIONS.md` l'inscrit, et la phrase entre dans la description
  d'`updateSubproject`, sans changement de forme, par le lot de la préparation des imports (« La
  préparation des imports hors verrou et la lecture figée »). Écarté : réimputer par le code au
  recodage, qui capterait des lignes sans réimport et contredirait le Vérif de WF-DAT-0060.
- **Le Kanban se mesure avant de se fenêtrer** (#646) : `listStartableTasks` et l'écran sur les
  mille tâches de PRJ-001, contre le service, relevés sur la pull request ; sous la borne `WORKING`,
  rien ne change hors la raison donnée dans le guide ; au-delà, une issue. Écarté : fenêtrer
  d'avance.

### Les décisions du 2026-11-10

Décisions de l'auteur du 2026-11-10, sur une question et les constats de la livraison, chacune avec
l'option écartée :

- **La terminaison d'une tâche par la mise à zéro est écrite par la réestimation** (question de
  #2399, option C) : US-1580/L2 l'écrit dans l'état des tâches de `core/planning`
  (`interface/progress.py`) et la réexporte par `core/planning/interface/__init__.py`, 422
  `COMPLETION_DATE_REQUIRED` compris, comme le dit « Ce qu'EP-06 écrit encore » ; US-1590/L1 en
  dépend et l'appelle pour la récapitulative, sans la réécrire. `set_task_progress` d'US-1410, qui
  refuse de terminer une tâche portant une ligne hors provision (`task_without_lines`), n'y sert pas.
  Écartées : US-1580/L2 après US-1590/L1, qui aurait écrit la terminaison (A) ; la terminaison passée
  entière à US-1590/L1, qui coupait la règle de WF-RAE-0040-A entre deux lots (B).
- **Les fonctions qu'EP-10 lit sont servies par les lots que la conception nomme** (#2708) :
  `remaining_of_revision` par US-1580/L2 — US-1600 la lit, ne l'écrit pas —, `actual_costs_until` par
  US-1610/L2 ; les lots d'EP-10 qui lisent un reste dépendent d'US-1580/L2, ceux qui lisent des coûts
  d'US-1610/L2. `CalculationContext`, le contexte de calcul du contrat, est défini dans l'interface
  d'`estimate` (`remaining_indicators.py`), d'où EP-10 l'importe. Écartée : la portée de l'issue
  d'US-1600, que le socle avait suivie.
- **`EstimateLineFacet.remaining_reason`** (#2420) : nullable, le motif de la dernière réestimation,
  rendu par la lecture de la facette à côté du reste précédent ; la colonne
  `estimate_line.remaining_reason` reste. US-1580/L2 l'écrit au contrat
  (`docs/api/components/schemas/revisions.yaml`) et à la lecture ; l'entrée de
  `docs/api/DECISIONS.md` (« La règle d'après le gel ») est écrite avec cette décision. Écarté : le
  retrait de `RemainingUpdate.reason`.
- **Une ligne d'un autre projet demande la confirmation même doublée** (#2724, option 1) : une ligne
  dont la faute lue est `WBS_ELEMENT_OUTSIDE_PROJECT` garde `lines_outside_project` dans
  `requires_confirmation_reasons` quand elle est rejetée `DUPLICATE_COST_LINE` — la confirmation
  protège d'un fichier du mauvais projet, qu'un doublon n'excuse pas ; US-1610/L2 le réalise et
  précise la description de `requires_confirmation_reasons`. Écartée : l'option 2, le comportement
  d'US-1610/L1 écrit au contrat.
- **Le montant d'un coût réel s'arrondit au centime ; un élément d'OTP sans rien après la barre
  oblique est invalide** (#2721) : les choix d'US-1610/L1 sont gardés — un montant à plus de deux
  décimales arrondi au centime, `ROUND_HALF_UP` (au plus loin de zéro : −0,005 donne −0,01) ;
  `A.ABC.26001/` rejeté `WBS_ELEMENT_INVALID`. La spécification les reçoit (WF-CRE-0010,
  WF-CRE-0020) par l'issue de spécification #2735, que l'auteur intègre au Word ; US-1610/L2 les
  écrit dans la description d'`ImportRejection`. Écartés : rejeter la ligne d'un montant à plus de
  deux décimales ; imputer `A.ABC.26001/` au seul projet.
- **Les paramètres des rejets par cellule d'une ligne de coût réel se décrivent par `column`**
  (#2722), l'identifiant de la colonne dans la correspondance : US-1610/L2 les décrit au contrat
  (`ProblemParams` ou la description d'`ImportRejection`), avec les autres paramètres que chaque
  code porte, et le service les suit. Écarté : `header`, l'intitulé du fichier, comme les lignes
  d'un devis.
- **La date de la revue est en B9 de « Synthèse »** (#2702), comme le prototype
  (`docs/spec/exemples/prototype_rae.py`) et l'ordre de l'annexe B : le projet en A4, puis, de la
  ligne 6 à la ligne 11, l'entreprise, le client, la révision, la date de la revue, la structure et
  la devise. US-1630/L3 corrige l'écriture d'US-1630/L1 — la constante `REVIEW_DATE_CELL` de
  `layout.py` et l'ordre des faits — avant d'y lire la date. Écarté : garder B6, et aligner le
  prototype et `rae-prototype.xlsx`.
- **Les index de `cost_line` et de `cost_import` sont ceux de la migration `0027`** (#2707) :
  « Tables et migrations » le dit.
- **La liste des exceptions d'un classeur abîmé reste recopiée du lecteur de devis** (#2723) : la
  refonte, facultative, revient à un lot qui touche `core/exchanges`.
- **`_doubled` ne trie ses lignes qu'une fois** (#2725), par US-1610/L2.

### Les décisions du 2026-11-10 (soir)

- **`open_lines` garde la signature réalisée par US-1590/L1** (#2766) :
  `open_lines(session, project_id, lines_by_task)`, que la conception écrit désormais (« Les modules »,
  « Les points d'extension », « Le Kanban et les lignes propres ») ; la date d'une mise à zéro d'une
  récapitulative n'est gardée que si la saisie la termine. Écartée : `open_lines(task_ids)`, qui
  aurait relu dans `estimate` les lignes que `planning` connaît déjà, risques compris.
- **La date de clôture d'une récapitulative s'efface dès qu'elle n'est plus terminée** (#2769) :
  US-1590/L2 vérifie la création et le déplacement d'une tâche sous une récapitulative et la
  suppression d'une subordonnée, et y efface la date comme US-1590/L1 le fait à la réouverture
  (WF-PLA-0040, WF-PLA-0130). Écartée : garder la date et ne la lire que si la récapitulative est
  encore terminée, qui laisse en base une date périmée.
- **La date d'une récapitulative refermée se relit sur la mise à zéro de ses lignes** (#2803,
  `register_zeroed_at`) : deux limites connues. La date relue est l'instant de la saisie de la mise à
  zéro, `reestimated_at`, non le jour déclaré à la validation, que la réouverture efface (#2769) ; la
  même relecture vaut au déplacement d'une subordonnée hors de la récapitulative.
- **Le libellé de l'aperçu du collage se lit dans la configuration de la grille** (#2753, EP-07) :
  un champ déclaratif `GridConfig.creates: "tasks" | "lines"`, posé par US-1640/L1, la grille de
  reste à engager étant la deuxième à créer des lignes. Écarté : `config.name === "estimate"`.

### Tables et migrations

Régime « projet » (§4.4.1) pour `cost_line` et `cost_import`, non partitionnées — seul le
révisionné l'est —, UUID v7 engendrés par le service ou imposés par le chargeur, textes en
collation `C`, règles SQL du guide ; chaque clé refuse (`RESTRICT`) : une ligne de coût ne se
supprime jamais, un journal non plus. Les colonnes nouvelles d'`estimate_line` suivent son régime
révisionné et son déclencheur d'immuabilité d'EP-07, qui les protège sans rien changer.

| Table | Contenu | Contraintes |
|---|---|---|
| `estimate_line` | reçoit `previous_quantity` (`numeric(14,4)`), `previous_hours` (`numeric(12,2)`), `previous_unit_disbursement` (`numeric(14,2)`), `previous_reestimated_amount` (`numeric(14,2)`), `reestimated_at` (`timestamptz`, la marque de réestimation), `remaining_reason` (`text`), tous nuls | `previous_* ≥ 0` ; aucune autre : la cohérence main-d'œuvre/hors main-d'œuvre des `previous_*` est celle de la ligne source, copiée telle quelle |
| `cost_line` | `id`, `project_id`, `subproject_id` (nul hors sous-projet et pour un code inconnu), `subproject_code` (le code lu dans l'OTP, nul sans partie sous-projet), `document_number`, `document_item` (nul sans poste), `document_date` (`date`), `amount` (`numeric(14,2)`, signé), `is_in_tracked_scope`, `excluded_reason`, `passthrough` (`jsonb`, un objet texte → texte), `last_import_id` (le dernier import qui l'a écrite), audit | unique (`project_id`, `document_number`, `document_item`) `NULLS NOT DISTINCT` (WF-DAT-0110) ; `document_number` de 1 à 200 non blanc, `subproject_code` de 50 au plus ; `excluded_reason IS NULL OR NOT is_in_tracked_scope` ; `subproject_id IS NULL OR subproject_code IS NOT NULL` ; clé vers `project` et clé composite (`project_id`, `subproject_id`) vers `subproject` en refus — la suppression d'un sous-projet imputé est refusée par le service avant la base (WF-PRJ-0050) — ; clé vers `cost_import` en refus ; index sur (`project_id`, `document_date`), (`subproject_id`, `project_id`), (`subproject_code`, `project_id`) pour l'imputation à la création d'un sous-projet — l'ordre inverse sert les mêmes égalités, et la convention de nommage aurait donné trois fois `ix_cost_line_project_id` ; `actual_cost_by_subproject(project_id)` s'appuie sur l'index unique, qui commence par `project_id` (#2707) |
| `cost_import` | `id`, `project_id`, `import_report_id`, `imported_at`, `requested_by` (le compte qui a confirmé), `period_from`, `period_to`, `created_count`, `updated_count`, `unchanged_count`, `rejected_count`, `passthrough_columns` (`jsonb`, la liste des colonnes conservées du fichier, dans son ordre) | `import_report_id` unique, clé vers `import_report` en refus ; `requested_by` vers `user_account` en refus ; `period_from <= period_to` quand les deux sont donnés ; comptes `≥ 0` ; jamais modifiée : pas de `lock_version`, l'instant et l'auteur tiennent lieu d'audit, comme une transition d'état ; index sur (`project_id`, `imported_at`), pour `listCostImports` (#2707) |

- **Une migration, `0027`, dans le socle** (US-1580/L1) : les six colonnes d'`estimate_line` — par
  `ALTER TABLE` sur la table partitionnée, qui les porte à chaque partition —, les deux tables, les
  droits du rôle du service — `SELECT`, `INSERT`, `UPDATE` sur `cost_line` (une ligne se met à jour
  et s'exclut, jamais ne se supprime), `SELECT`, `INSERT` sur `cost_import` — déclarés dans
  `SERVICE_RIGHTS`. Aucune migration de données.
- **L'idempotence par la base** : l'application d'un import insère ou met à jour sur le triplet,
  et la contrainte unique refuse ce qu'un chemin oublierait ; `test_database_constraints.py`
  l'éprouve en propriétaire (deux lignes de même pièce et de même poste, nul compris, refusées ;
  de postes différents, acceptées).
- Les tests : `test_migrations.py` (schéma, droits), `test_database_constraints.py` (une
  contrainte, un test), `test_revision_immutability.py` étendu aux colonnes nouvelles d'une ligne
  marquée.

### Modules

| Module | Tables | Interface offerte |
|---|---|---|
| `waterfall.core.estimate`, sous-paquet `remaining/` (FBS-4.5) | les six colonnes nouvelles d'`estimate_line` | `set_line_remaining` (la réestimation, la mise à zéro qui termine) ; `copy_previous` (le second enregistrement de `register_copy`) ; `open_lines(session, project_id, lines_by_task)` pour le registre de `planning` ; `startable_tasks(project_id)` (le Kanban) ; `remaining_indicators(project_id, revision_id, at)` et `register_coverage` ; `remaining_of_revision(session, project_id, revision_id)` — le total et le reste par ligne des tâches non terminées, à l'état des tâches de la révision — pour les indicateurs et EP-10 ; le format et l'exporteur `remaining` ; `remaining_entry` et `previous_*` rendus par la lecture de la facette d'EP-07, que le lot de la réestimation complète après #2372 |
| `waterfall.core.costs` (FBS-4.7) | `cost_line`, `cost_import` | le format `actual_costs` (l'en-tête selon la correspondance, l'analyse, l'application) ; `list_actual_costs` (filtres, tri, totaux, colonnes conservées, dernier import), `set_tracked_scope`, `list_cost_imports` ; `actual_cost_by_subproject(project_id)` et `actual_costs_until(project_id, date, scope)` — les lignes suivies, pour les indicateurs du reste à engager et pour EP-10 — ; `subproject_has_actual_costs` et `impute_waiting_lines(project_id, subproject_id, code)` pour le registre de `projects` ; `load_cost_import`, `load_cost_lines` et `load_exclusion` avec identifiants et instants imposés |

- **La couche** : `estimate` importe l'interface de `costs` (le coût réel par sous-projet des
  indicateurs), outre celles qu'EP-07 lui donne ; `costs` importe `projects`, `cost_settings` (la
  correspondance, l'unicité des intitulés), `exchanges` (le format), `users` (l'auteur du journal)
  et `platform` ; ni `planning`, ni `projects`, ni `exchanges` n'importent l'un ou l'autre — ils
  appellent des registres. Le socle ajoute `costs` au contrat de couches d'import-linter que le socle
  d'EP-07 a déclaré, sous `estimate`.
- **La réestimation** passe par `update_line` d'EP-07, la même fonction que la saisie du devis :
  les grandeurs écrites, le réestimé recalculé par `pricing` et `spreading`, le budgété et la lignée
  intacts, `reinflated` et `ancestors` rendus ; elle y ajoute `reestimated_at` et
  `remaining_reason`, et juge d'abord `remaining_entry`. « Un reste nul » est un `reestimated_amount`
  à zéro ; quand toutes les lignes propres hors provision d'une tâche sont à zéro, et pour une
  récapitulative quand toutes ses subordonnées sont terminées, `set_line_remaining` appelle la
  terminaison par mise à zéro de `planning` à `completed_on`, dans la même transaction, par
  l'interface — écrite par US-1580/L2 dans l'état des tâches d'US-1410 #2324, que
  `set_task_progress` ne sert pas (« Les décisions du 2026-11-10 ») — : une tâche non démarrée qui n'est pas un jalon passe par l'état démarré, un jalon
  non, les deux avec `started_on` égal à `completed_on` ; sans `completed_on`, 422
  `COMPLETION_DATE_REQUIRED` et rien n'est écrit.
- **Les commandes** : `import_actual_costs` (`actual_costs.write` ; `project_in_progress`,
  `no_background_task_running`, `actual_cost_mapping_complete`), `exclude_cost_lines`
  (`cost_line_exclude` ; `project_in_progress`) et `import_remaining` (`remaining.write` ;
  `project_in_progress`, `no_background_task_running`, `may_create_revision`) entrent dans `RULES`
  de `core/projects/commands.py`, dans l'ordre de `ProjectCommand` ; `export_remaining`
  (`remaining.read`, sans condition, sur un projet terminal aussi) dans `REVISION_RULES` de
  `core/revisions/commands.py` ; chaque fichier par un seul lot, après #2380 et #2381.

### Les points d'extension

Chaque registre est un `Registry` de `core/revisions/registry.py`, rempli à l'import de
l'interface du module qui enregistre, et le test des points d'entrée d'EP-06 (#2180) — l'API, le
worker, le chargeur — s'étend à chacun.

| Module | Registre | Qui le déclare | Qui le remplit | Ce qu'il fait |
|---|---|---|---|---|
| `core/planning` | `register_open_lines` (nouveau) | US-1590, après #2324, #2338 et #2339 | `estimate` (`open_lines(session, project_id, lines_by_task)`) | la dernière subordonnée terminée ne termine la récapitulative que si aucune ligne propre hors provision ne garde un reste ; `awaiting_own_lines` est vrai pour une récapitulative démarrée dont toutes les subordonnées sont terminées et qu'une ligne propre retient ; la feuille qu'une récapitulative devient reste démarrée si une ligne propre retient (WF-PLA-0040) |
| `core/planning` | `register_zeroed_at` (nouveau) | US-1650/L2 (#2803) | `estimate` (`zeroed_lines(session, project_id, lines_by_task)`) | l'instant de la mise à zéro des lignes propres, hors provisions (`reestimated_at`), qu'une récapitulative refermée relit à la suppression ou au déplacement d'une subordonnée (WF-PLA-0130) |
| `core/planning` | `progress_commands(task, bears_lines)` (fonction nouvelle, pas un registre) | US-1590, après #2324 | — | les gestes d'une carte du Kanban et l'état que chacun envoie, par la fonction qui juge le 409 de `setTaskProgress` (US-1410), pour que la carte et le refus nomment la même condition |
| `core/revisions` | `register_copy` (EP-04) | EP-04 | `estimate`, second enregistrement (`copy_previous`), après la copie des lignes | `previous_*` des lignes copiées depuis une révision marquée En cours |
| `core/projects` | `register_cost_facts` (nouveau) | US-1610, après #2373 | `costs` | `subproject_has_actual_costs` (la suppression refusée, `has_actual_costs` de la liste et son filtre), `impute_waiting_lines` dans la transaction de `createSubproject` ; `updateSubproject` ne l'appelle pas |
| `core/estimate` | `register_coverage` (nouveau) | socle | EP-08 | la couverture des risques de `getRemainingIndicators`, à zéro sans entrée |
| `core/estimate` | `register_estimate_facts` (EP-07) | US-1490/L4 #2373 | `estimate` | `subproject_is_cited` : une ligne d'une révision marquée ; les coûts réels ont leur registre propre, ci-dessus |
| `core/exchanges` | `register_format`, `register_exporter` (EP-06) | EP-06 | `estimate` (`remaining`), `costs` (`actual_costs`) | l'en-tête, l'analyse, l'application et l'export des deux natures |
| `core/exchanges` | `load_import` (fonction nouvelle) | US-1650, après #2341 | — | une ligne d'`import_report` à son instant, dans son état, son compte rendu et sa période, sans dépôt ni tâche, pour le témoin |
| `witness/revisions` | la marche des événements (EP-04, EP-07) | US-1650, après #2385 | `witness/costs` | les écritures `cost_import_applied`, `cost_line_excluded` et `import_expired` de la chronologie, à leur instant |

### Le Kanban et les lignes propres

- `startable_tasks` lit la structure principale de la révision courante — la révision en cours,
  ou la dernière marquée sans elle — par l'interface de `planning` (les tâches, leur état, leurs
  dates, leurs liaisons pour `predecessors_completed`), et par `estimate` les tâches qui portent une
  ligne hors provision ; trois colonnes dans l'ordre du plan, jamais une récapitulative, sauf celle
  dont `awaiting_own_lines` est vrai, dans `started` (#1851) ; chaque carte reçoit
  `progress_commands` de `planning`, puis les conditions de `edit_remaining` de la structure
  principale, vides sans `remaining.write`, et le nœud entier (`KanbanTask`, `NotStartedTask`). Une
  requête par table, jamais une par tâche : la liste se tient en deux lectures (nœuds et liaisons,
  lignes porteuses).
- `open_lines(session, project_id, lines_by_task)` répond par une requête sur `estimate_line` :
  parmi les tâches nommées, chacune avec les lignes qu'elle porte — `planning` les connaît déjà et
  en écarte les lignes d'un risque (EP-08 : `origin_risk_id` du nœud) —, celles qui portent une
  ligne propre hors provision (la catégorie de type provision, jamais vrai ici) dont
  `reestimated_amount` n'est pas nul ; `project_id` borne la lecture à la partition du projet.
  `planning` la pose à la terminaison d'une subordonnée, à chaque lecture de `TaskFacet` pour les
  récapitulatives démarrées rendues, et à la transformation d'une récapitulative en feuille
  (décision du 2026-11-10, #2766 : la signature réalisée par US-1590/L1, non `open_lines(task_ids)`).
- La date d'une mise à zéro d'une récapitulative n'est gardée que si la saisie la termine ;
  `completed_on` reste la plus tardive de ses subordonnées et de la mise à zéro qui l'a terminée.
  Dès que la récapitulative n'est plus terminée, sa date de clôture s'efface : à la réouverture
  d'une subordonnée (US-1590/L1), et sur les chemins qu'US-1590/L2 vérifie — une tâche créée ou
  déplacée sous la récapitulative, la suppression d'une subordonnée (WF-PLA-0040, WF-PLA-0130 ;
  #2769).
- La mesure (#646) : `listStartableTasks` sur PRJ-001 chargé, et l'ouverture de l'écran du Kanban
  par son adresse et par un clic, relevées sur la pull request d'US-1590 ; la raison donnée dans
  `docs/dev/README-fr.md` et `README.md` pour la présence du Kanban parmi les écrans à `WORKING`
  est corrigée — il lit `listStartableTasks`, non `listNodes`.

### Les coûts réels

- **L'en-tête** (`openImport`) : le premier onglet, ses intitulés en ligne 1, lus par openpyxl en
  valeurs et comparés aux intitulés de la correspondance par la fonction d'EP-05 (sans égard à la
  casse, aux accents ni aux espaces en bout) ; une colonne exigée sans intitulé déclaré, 409
  `actual_cost_mapping_complete` (`params.columns`), que la commande dit d'avance ; une colonne
  exigée absente du fichier, 422 `FILE_FORMAT_UNREADABLE`, `expected_format` à `actual_costs`,
  `missing_columns` avec leurs intitulés ; la correspondance lue est gardée avec le compte rendu
  (les rangs des colonnes lues et conservées), pour que l'application s'exécute telle que l'analyse
  l'a lue même si la correspondance change.
- **L'analyse** (worker) lit chaque ligne : l'élément d'OTP, un texte — vide, commençant ou
  finissant par `/`, `WBS_ELEMENT_INVALID` (#2721) ; la part avant la première barre oblique est le code projet, qui peut
  contenir des points, celle après le code de sous-projet (C-373) ; un code projet qui n'est pas
  celui du projet, `WBS_ELEMENT_OUTSIDE_PROJECT` et `lines_outside_project` ; un code de sous-projet
  qu'aucun sous-projet ne porte, la ligne acceptée, imputée au seul projet, `unknown_subproject` — ;
  le numéro de pièce, texte ou entier lu comme texte ; le poste, texte ou nul ; la date, cellule de
  date ou texte AAAA-MM-JJ ; le montant, cellule numérique, un texte rejeté (`NUMBER_INVALID`),
  arrondi au centime `ROUND_HALF_UP` s'il porte plus de deux décimales (#2721) ; chaque rejet par
  cellule nomme sa colonne par `params.column`, l'identifiant de la colonne dans la correspondance
  (#2722) ; les colonnes conservées en texte ; une ligne vide ignorée ; les colonnes ni lues ni conservées
  comptées dans `ignored` (`columns`) ; deux lignes de même pièce et de même poste, nul compris,
  rejetées chacune (`DUPLICATE_COST_LINE`, `params.rows`), une ligne d'un autre projet ainsi
  doublée gardant `lines_outside_project` (#2724). Puis le rapprochement avec les lignes du
  projet sur le triplet : `added`, `updated` (les champs qui changent : `document_date`, `amount`,
  `subproject`, `passthrough.<colonne>`), `unchanged_count` ; `format_version` nul ;
  `requires_confirmation_reasons`.
- **L'application** (worker, dans la transaction de la tâche d'EP-06, sous le verrou du projet) :
  revérifie ce qu'EP-06 revérifie, écrit l'entrée de `cost_import` (l'auteur `requested_by`, la
  période de l'ouverture, les colonnes conservées du fichier), puis insère ou met à jour chaque
  ligne acceptée sur le triplet — l'imputation recalculée depuis l'OTP, `passthrough` remplacé,
  `is_in_tracked_scope` et `excluded_reason` intacts, `last_import_id`, `updated_by` l'auteur —,
  compte les quatre nombres, et laisse à `exchanges` l'inscription `import_apply` au journal d'audit
  et l'absence d'entrée d'historique annulable ; une tâche `applying` qui échoue ne laisse rien.
- **L'imputation à la création d'un sous-projet** : `createSubproject` d'EP-04 appelle
  `register_cost_facts.impute_waiting_lines` dans sa transaction, qui pose `subproject_id` sur les
  lignes du projet dont `subproject_code` est le code créé et `subproject_id` nul, l'auteur de
  `updated_by` étant celui de la création ; le recodage n'appelle rien.
- **L'exclusion** (`set_tracked_scope`) : une mise à jour de la ligne seule, idempotente, sans
  compteur — l'état visé et le motif, nul en réintégration —, après `project_not_terminal` et
  `project_in_progress` (`exclude_cost_lines`), sous `cost_line_exclude` et la qualité de
  contributeur, inscrite au journal d'audit par la fonction d'EP-03 (`cost_line_exclude`,
  `cost_line_reinstate`, l'objet `cost_line` nommé par sa pièce et son poste, le projet) ; hors de
  l'historique annulable.
- **La consultation** (`list_actual_costs`) : une requête filtrée (sous-projet — `unassigned` par
  `subproject_id` nul n'est pas un filtre du contrat —, période sur `document_date`, périmètre),
  triée par la colonne demandée — `passthrough.<colonne>` par `passthrough ->> colonne` en texte,
  les nuls après dans l'ordre croissant —, paginée ; les trois totaux et `last_import_at` par des
  agrégats sur l'ensemble retenu ; `meta.passthrough_columns` l'union, dans l'ordre, des
  `passthrough_columns` des imports (`cost_import`, par `imported_at`) que `last_import_id` des
  lignes retenues désigne, chaque colonne à sa première déclaration ; `subproject_label` résolu.

### Les indicateurs du reste à engager

- `remaining_of_revision(session, project_id, revision_id)` : la somme des `reestimated_amount` des
  lignes hors provision des tâches non terminées de la structure principale, et la même par ligne —
  l'état des tâches de cette révision, en cours ou marquée ; le projet est passé avec la révision,
  la lecture des lignes placées l'exigeant (signature réalisée par US-1580/L2, #2743) ; c'est la
  fonction qu'EP-10 lira pour la projection du chef de projet et l'indice de coût, et le marquage
  (EP-10) pour conserver.
- `remaining_indicators` : `total` et `by_cost_type` (le même module de parts qu'EP-07, la nature
  provision à zéro) sur la révision lue ; `by_subproject` par sous-projet et `unassigned` — `budget`
  la somme des budgétés hors provision des lignes de la révision de référence par sous-projet (nul
  sans référence), `actual_cost` par `actual_cost_by_subproject` de `costs` (les lignes suivies,
  `subproject_id` nul vers `unassigned`), `remaining` par `remaining_of_revision`, `variance` =
  budget − coût réel − reste, `is_over_budget` quand elle est négative, `zone` `alert` ou `nominal`
  — ; « nul sans référence » dit un montant zéro (`0.00`) et non un budget absent, puisque le contrat
  exige un `Money` pour `budget` et `variance` : sans référence, la marge d'un sous-projet est
  l'opposé de ce qu'il a engagé (#2715) ; `delta_to_reference` = budget de référence − (coût réel
  + reste), nul sans référence ;
  `delta_to_previous_revision` = reste courant − `remaining_of_revision` de la dernière révision
  marquée après le passage En cours, nul sans elle ; `coverage` par `register_coverage` ;
  `context` avec `is_stored` faux. Tout se calcule à la lecture ; la conservation au marquage et le
  cache sont d'EP-10.
- Le plan de charge sur le reste (`current_remaining`, `marked_remaining`) est celui d'EP-07
  (US-1520) : la charge restante d'une ligne est sa charge courante, que la réestimation écrit ; EP-09
  n'y ajoute que des tests (le reste de 80 heures, la tâche terminée par mise à zéro).

### Le format Excel du reste à engager

- **L'écriture** (XlsxWriter) suit le prototype et l'annexe B : « Synthèse » (format « Reste à
  engager » et version en A1-B2, le projet en A4, puis de la ligne 6 à la ligne 11 l'entreprise, le
  client, la révision, la date de la revue en B9 — `review_date`, le jour de la demande par défaut
  (#2702) —, la structure, la devise ; par sous-projet et pour le
  projet : budget, coûts réels, reste à engager, projection, écart signé dans le sens de la dérive,
  avancement financier, ventilation du reste par nature et en jours par code comptable, par des
  formules qui lisent les onglets) ; un onglet par sous-projet, nommé par son code ramené aux
  règles d'Excel par `sheet_name`, et « Hors sous-projet », chacun avec son en-tête puis ses lignes
  des tâches non terminées en tableau Excel à ligne de total déclarée — tâche, description, état,
  rôle ou catégorie, désignation, budget, reste précédent (`previous_reestimated_amount`), jours
  restants ou débours restant, puis les colonnes calculées (nature, code comptable, service, taux,
  main-d'œuvre, débours, reste à engager, type, coefficient), la lignée masquée —, listes de
  validation sur « Tâches » et « Paramètres », dix lignes vides pour les lignes nouvelles ;
  « Tâches » (les tâches non terminées par sous-projet, leur lignée, leur état, le coefficient
  d'inflation de leur année de consommation, leur description) et « Paramètres » (le référentiel
  que la révision retient, les heures par jour), protégés ; le logo et le pied de page d'EP-07 ;
  `strings_to_formulas` faux. Les montants des en-têtes sont ceux que `remaining_indicators` et
  `costs` calculent pour la révision exportée. Le nom : `<code ou libellé du projet>-<version>-reste-a-engager.xlsx`.
- **La lecture** (openpyxl, valeurs) : l'en-tête (A1, B1, A2, B2 — format « Reste à engager »,
  version connue, sinon `FILE_FORMAT_UNREADABLE` avec `expected_format` à `remaining` et
  `expected_version`), la date de la revue en B9 de « Synthèse », puis chaque onglet de sous-projet et
  « Hors sous-projet » — reconnus par leur nom, les onglets « Synthèse », « Tâches » et
  « Paramètres » exclus — par ses en-têtes ; les colonnes lues : la tâche, le rôle ou la catégorie,
  la désignation, les jours restants, le débours restant, la lignée ; une ligne vide ou de total
  ignorée, une colonne inconnue ignorée, un nombre en texte rejeté, chaque rejet par son onglet et
  son rang.
- **L'analyse** rapproche par la lignée : pour une ligne connue, elle recalcule la valeur que
  l'export aurait écrite — les jours restants, le débours restant — et ne la juge changée que si la
  cellule en diffère ; changée, la ligne reçoit ses grandeurs (« Ce que le cadrage décide »), un
  écart `updated` sur la colonne changée, le budgété et la lignée intacts ; inchangée, elle compte
  dans `unchanged_count`, sans écriture ni marque de réestimation ;
  une ligne d'une tâche terminée, inchangée, est rejetée (`task_not_completed`) ; une ligne sans
  lignée crée une ligne à budgété nul sous la tâche désignée par « Tâches » ou par son libellé
  (`AMBIGUOUS_TASK_LABEL`, `UNKNOWN_TASK`), rejetée sous une tâche terminée (I-05, #1794) ; le
  sous-projet est celui de l'onglet — une ligne existante placée ailleurs en change (écart
  `subproject`), sauf si sa tâche est démarrée ou terminée et que son sous-projet a reçu des coûts
  réels (`SUBPROJECT_HAS_ACTUAL_COSTS`) — ; un rôle ou un sous-projet inconnu, une catégorie de
  provision, une ligne qui laisserait sa tâche sans heure, rejetés comme au devis ; les lignes
  absentes du fichier, inchangées et non signalées ; les tâches dont toutes les lignes du fichier
  portent zéro, dans `completed_tasks` à la date de la revue ; les lignes de provision ignorées
  (`provision_lines`) sont d'EP-08. **L'application** écrit par `set_line_remaining`, sous le verrou
  de la structure, dans la transaction de la tâche d'EP-06, la marque de réestimation posée, les
  tâches de `completed_tasks` terminées à la date de la revue, sans entrée d'historique ; sur un
  projet dont toutes les révisions sont marquées, la révision en cours est créée d'abord (EP-06), aux
  taux projetés (EP-07), et `previous_*` copiés ; `ProjectCommand.import_remaining` dit la phase.
- **L'export** s'enregistre par `register_exporter` : la révision et la structure nommées, le
  fichier `.xlsx`, `media_type`
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` ; le stockage, le
  téléchargement et la purge sont ceux d'EP-06 ; disponible sur un projet terminal (WF-CYC-0110).

### Le service d'API

- Un routeur par US — `api/remaining_lines.py` (US-1580 : `setLineRemaining`),
  `api/startable_tasks.py` (US-1590 : `listStartableTasks`), `api/remaining_indicators.py` (US-1600 :
  `getRemainingIndicators`), `api/cost_imports.py` (US-1610 : `listCostImports`),
  `api/actual_costs.py` (US-1620 : `listActualCosts`, `setActualCostTrackedScope`) —, créés vides et
  enregistrés dans `app.py` par le socle, chacun avec son `asked_*.py` ; `setTaskProgress`,
  `deleteNode`, `listNodes`, `createNode`, `moveNodes`, `updateEstimateLine`, `openImport`,
  `applyImport`, `requestExport`, `createSubproject`, `listSubprojects` restent aux routeurs
  d'EP-04, d'EP-06 et d'EP-07, qui appellent les registres.
- Chaque route déclare `RequiresProject(...)` : `remaining.read` pour `listStartableTasks` et
  `getRemainingIndicators`, la qualité de contributeur et `remaining.write` pour `setLineRemaining`,
  `actual_costs.read` pour `listActualCosts` et `listCostImports`, la qualité de contributeur et
  `cost_line_exclude` pour `setActualCostTrackedScope` ; les refus sont ceux du contrat, dans
  l'ordre que chaque opération écrit ; chaque réponse d'un test passe par `ContractClient` ;
  `test_access_evaluation.py` reçoit chaque opération avec ses deux termes.

### Le worker

Aucun gestionnaire nouveau : l'analyse, l'application et l'export sont ceux d'EP-06, qui
appellent les registres. Le worker doit importer l'interface de `costs` pour que le format
`actual_costs` soit enregistré (#2180) — `remaining` l'est par l'interface d'`estimate`, qu'EP-07
y importe depuis US-1500/L2 #2375 — ; `worker/main.py` est écrit par #2341 (EP-06) puis #2375
(EP-07) : l'import est du lot d'US-1610 qui applique une extraction, après #2375. Le test des
points d'entrée (#2180), que le socle étend, dit que les extensions de `costs` ne sont attendues du
worker qu'à partir de ce lot — l'API et le chargeur les attendent dès le socle.

### Le chargeur du témoin

- **Un lot d'outil**, dans `wftools` : la chronologie exportée reçoit, sur les cinq événements
  « Import de coûts réels », l'écriture `cost_import_applied` (le numéro de l'import) ; un
  événement nouveau, « Exclusion de la réception du client », le 6 avril 2026 à 9 h 15, avec
  l'écriture `cost_line_excluded` (la pièce, le poste, le motif) ; et sur « Extraction d'avril
  rejouée et analysée », l'écriture `import_expired` ; `make mock-data` écrit
  `fixtures/api/witness_costs.json` : chaque import de coûts — son numéro, son import des échanges,
  son fichier, sa période, ses colonnes conservées, son compte rendu tel que l'analyse l'a
  présenté, ses comptes —, chaque ligne de coût — pièce, poste, date, montant, code de
  sous-projet, colonnes conservées, les imports qui l'ont apportée et mise à jour, son exclusion —,
  depuis `wftools.mockwitnesscosts` et `mockexchanges` ; le back le lit par un modèle propre,
  strict, sans importer `wftools`.
- **La tranche** : `witness/costs.py`, appelé par la marche des événements de `witness/revisions.py`
  (étendue après #2385) pour chaque écriture nouvelle — `load_import` d'`exchanges` pour la ligne du
  journal des imports (appliquée, ou analysée puis expirée, avec son compte rendu), `load_cost_import`
  et `load_cost_lines` de `costs` pour l'entrée du journal et les lignes créées ou mises à jour, aux
  identifiants du témoin, à l'instant de l'événement, l'auteur du témoin pour compte —, et
  `load_exclusion` à l'instant de l'exclusion. `witness/timeline.py` (EP-04, écrit par #2384 et
  #2385) reçoit les trois modèles d'écriture après #2385. Rien n'est chargé pour le reste à engager :
  les états viennent d'EP-06, les lignes d'EP-07, `previous_*` de la copie de la révision 102 depuis
  la référence 101, marquée En cours — le registre est rempli dès le chargement, qui tourne entier
  sur une plateforme neuve. Les imports du planning (a10) et du devis (a11) restent à EP-06, EP-07 et
  EP-08. Les montants et imputations sont ceux que le service calcule : le calculé devient l'attendu.

### Le front

- Les écrans sont ceux d'EP-02, d'EP-14, d'EP-15, d'EP-16, d'EP-17 et d'EP-22 ; chaque US branche
  le sien et retire `MockupNotice` de la page qu'elle sert en dernier : les coûts réels par
  US-1620, le reste à engager par US-1640 ; le Kanban n'en a pas, les échanges l'ont perdu par EP-06.
  Les aides `frontend/help/fr/FBS-4.5*.md`, celle du Kanban comprise, par US-1640, `FBS-4.7.md` et
  `FBS-3.1.3.md` (#2093) par US-1620 ; le renvoi d'une suppression refusée vers la mise à zéro du
  reste, dans les grilles de planning et de devis qu'EP-06 (#2326) et EP-07 (#2383) possèdent, par
  US-1640.
- Le front ne calcule rien : les restes, les totaux, les écarts, les gestes des cartes et les
  conditions viennent du service. Un manque que le branchement révèle devient une issue ; un manque
  du contrat, une « Interface contract issue ».

### Le harnais

Chaque US étiquette `@shared` les tests dont l'écran est servi : US-1620 `actual-costs.spec.ts` ;
US-1640 `remaining.spec.ts`, que la grille et le Kanban partagent ; US-1630 ajoute à
`exchanges.spec.ts`, après US-1550/L4 #2381, le parcours de l'import d'un reste à engager quitté
pendant son application et informé de son aboutissement (WF-IHM-0080). Les parcours qui écrivent le
font sur un projet que la course crée (#2193) ; ceux qui lisent une provision ou un risque restent
gardés par `inService` jusqu'à EP-08, et le guide le dit. La liste des entrées non rejouées n'est
écrite que par US-1650/L3.

### Les tests du back

Un fichier par objet et par règle — `test_line_remaining.py` (la réestimation, la mise à zéro, la
marque), `test_previous_remaining.py` (la copie), `test_remaining_entry.py`,
`test_remaining_workload.py`, `test_open_lines.py` (la récapitulative, la feuille, dans
`planning`), `test_startable_tasks.py`, `test_remaining_indicators.py`, `test_actual_costs_header.py`,
`test_actual_costs_analysis.py`, `test_actual_costs_apply.py`, `test_actual_costs_imputation.py`,
`test_actual_costs_list.py`, `test_actual_costs_scope.py`, `test_cost_imports.py`,
`test_subproject_costs.py` (la suppression, la liste, la ligne retenue), `test_remaining_excel_write.py`,
`test_remaining_excel_read.py`, `test_remaining_import.py`, `test_remaining_export.py`,
`test_terminal_project_costs.py`, `test_witness_costs.py` —, chaque test citant son exigence, chaque
réponse validée contre le contrat ; les exemples chiffrés des Vérif sont des tests sans base quand
ils le peuvent (`tests/examples`). Les fixtures communes — un projet En cours avec sa référence, ses
tâches et ses lignes par l'interface, des lignes de coût chargées, l'horloge posée — vivent dans
`tests/remaining_support.py` et `tests/costs_support.py`, écrits par le socle. Un test de concurrence
par règle d'ensemble : deux réestimations d'une même ligne, deux exclusions d'une même ligne, une
application d'extraction pendant une saisie.

### La préparation des imports hors verrou et la lecture figée (décisions du 2026-11-10)

Trois constats sur la mécanique des échanges d'EP-06 (#2582, #2679, relevés par US-1430/L3 et L4 ;
#2739, relevé par US-1610/L2), tranchés par l'auteur le 2026-11-10 et réalisés par un lot d'EP-09
(US-1610/L4 #2749), après l'application des coûts réels (US-1610/L2 #2404), pour tous les formats :

- **Un fichier importé se prépare hors du verrou, puis s'applique sous lui** (#2582, #2739). Le
  protocole des formats d'US-1420 gagne une étape : `Format.prepare(content)`, appelée par la tâche
  d'application avant tout verrou, lit le fichier et rend son modèle en mémoire ; `Format.apply`
  reçoit ce modèle, sous les verrous du projet et de la structure, et ne fait que rejuger et
  écrire. Les formats existants — `ms_project_schedule`, `estimate`, `actual_costs`, et `remaining`
  s'il est déjà écrit — suivent ; un format écrit après le lot naît sous ce protocole : US-1630/L3
  #2410 en dépend. Écartés :
  garder la lecture sous verrou, le défaut « travail long sous verrou » de `docs/dev/python.md` ;
  ne préparer que les formats volumineux, deux protocoles pour une mécanique.
- **Les tâches d'export et d'analyse lisent dans une transaction figée** (#2679) : `REPEATABLE
  READ`, pour qu'une liaison créée entre la lecture de l'arbre et celle des liaisons ne fasse pas
  échouer l'export ; écarté : un export qui ignore les liaisons dont une tâche manque, qui
  rendrait un fichier incohérent sans le dire.
- **La description d'`updateSubproject` dit le recodage** (#2421) : ce lot l'écrit au contrat,
  sans changement de forme (« Ce que le cadrage décide »).

### Ce qu'EP-07 écrit encore

Les lots d'EP-09 se livrent pendant ceux d'EP-07, et `epic/EP-09` reprend `epic/EP-07` à chaque
fusion. Un fichier qu'un lot d'EP-07 non fusionné possède, les lots d'EP-09 ne l'écrivent pas avant
ce lot, ou en dépendent par son numéro :

| Fichier | Lot d'EP-07 qui le possède | Lots d'EP-09 qui l'attendent |
|---|---|---|
| `core/estimate/interface/__init__.py`, les questions du référentiel, `register_estimate_facts`, la suppression et le déplacement d'une ligne | US-1490/L3 #2372, US-1490/L4 #2373 | le socle (US-1580/L1), et tout lot d'EP-09 |
| `core/estimate` : la lecture de la facette (`remaining_entry`, que `previous_*` complètent), `update_line`, `pricing/` | US-1490/L2 #2371, US-1490/L3 #2372 | US-1580 (la réestimation) |
| `core/estimate` : `spreading/`, `workload`, `planned_value` | US-1520/L1 #2376, US-1520/L2 #2377 | US-1580 (le plan de charge sur le reste) |
| `core/estimate` : les taux, le marquage, la désignation, `reinflate_project` | US-1500/L1 #2374, US-1500/L2 #2375 | US-1630 (la révision créée par l'import, aux taux projetés) |
| `core/estimate` : les crochets de la facette dans `core/planning` (`FacetHooks`, `judge_cell`) | US-1490/L3 #2372, US-1490/L4 #2373, US-1560/L1 #2382 | aucun : `register_open_lines` est un fichier propre |
| `core/estimate/excel/` (l'écriture, `sheet_name`), la lecture, l'analyse, le format `estimate` | US-1550/L1 #2378, L2 #2379, L3 #2380, L4 #2381 | US-1630 (`sheet_name`, le logo et le pied de page, après #2378 ; les fonctions de lecture communes, après #2379) |
| `core/projects/commands.py` (`import_estimate`) | US-1550/L3 #2380 | le lot qui écrit `import_actual_costs`, `exclude_cost_lines`, `import_remaining` |
| `core/revisions/commands.py` (`apply_rate_update`, `export_estimate`) | US-1500/L1 #2374, US-1550/L4 #2381 | le lot qui écrit `export_remaining` |
| `core/projects` (`register_estimate_facts`, `subproject_is_cited`, `subproject_is_estimated`) | US-1490/L4 #2373 | US-1610 (`register_cost_facts`) |
| `worker/main.py` (l'import de l'interface d'`estimate`) | US-1500/L2 #2375 | US-1610 (l'import de l'interface de `costs`) |
| `wftools`, `make mock-data`, `DECISIONS.md` (L-01) | US-1570/L1 #2384 | US-1650/L1 |
| `witness/revisions.py`, `witness/timeline.py`, `witness/estimate_lines.py` | US-1570/L2 #2385 | US-1650/L2 |
| `frontend/e2e/exchanges.spec.ts`, `revisions.spec.ts`, les pages du devis, le guide (la liste des entrées non rejouées) | US-1550/L4 #2381, US-1530, US-1560/L2 #2383, US-1570/L3 #2386 | US-1630 (`exchanges.spec.ts`), US-1650/L3 (le guide) |
| `app.py`, `pyproject`, `tests/estimate_support.py`, `chronology.py`, le test des points d'entrée | US-1490/L1 #2370, fusionné avant la branche | aucun |

### Ce qu'EP-06 écrit encore

| Fichier | Lot d'EP-06 qui le possède | Lots d'EP-09 qui l'attendent |
|---|---|---|
| `core/planning` : la lecture et la création des nœuds (`interface/nodes.py`, `facets.py`) | US-1380/L2 #2335 | US-1590 (`register_open_lines`, `progress_commands`) |
| `core/planning/interface/__init__.py` (le moteur `scheduling/` importé, les noms des liaisons) | US-1390/L1 #2329, US-1390/L2 #2339 | US-1580/L2 (le réexport de la terminaison par mise à zéro), puis US-1590/L1, qui en dépend (le réexport de `register_open_lines` et de `progress_commands`) |
| `core/planning` : la suppression et le déplacement, `core/projects` (`register_attachments`) | US-1380/L3 #2338 | US-1590 (la feuille qu'une récapitulative devient, `deleteNode`) |
| `core/planning` : l'état des tâches (`setTaskProgress`, `started_on`, `completed_on`, `finish_overdue`, les récapitulatives) | US-1410 #2324 | US-1580/L2 (la terminaison par mise à zéro), puis US-1590/L1, qui en dépend (`register_open_lines`, `progress_commands`) |
| `core/planning` : `setPredecessors`, les registres de `resource_settings` | US-1390/L2 #2339 | US-1590, par le réexport ci-dessus |
| `core/planning` : le collage, `api/history.py` | US-1450/L2 #2344 | aucun |
| `core/exchanges` : la mécanique d'import, les formats | US-1420/L1 #2332 | US-1610 (le format `actual_costs`), US-1630 (le format `remaining`) |
| `core/exchanges` : la purge ; `worker/main.py`, les Compose, `production.env.example`, le Makefile | US-1420/L2 #2341 | US-1650 (`load_import`), US-1610 (l'import dans le worker, après #2375 aussi) |
| `core/revisions/commands.py` (`export_*`), `api/tasks.py`, `api/exports.py` | US-1430/L2 #2336, US-1440/L2 #2343 | aucun : `export_remaining` attend #2381 d'EP-07, qui vient après |
| `core/projects/commands.py` (`manage_timelines`, `generate_skeleton`) | US-1400/L1 #2331, US-1460 #2325 | aucun : le lot des commandes attend #2380 d'EP-07, qui vient après |
| `REUSE.toml`, `LICENSES/` | US-1440/L1 #2337 | aucun |
| `wftools`, `make mock-data` | US-1480/L1 #2330 | aucun : US-1650/L1 attend #2384 d'EP-07, qui vient après |
| `witness/tasks.py` | US-1480/L2 #2347 | aucun : US-1650/L2 attend #2385 d'EP-07, qui vient après |
| le guide, la liste des entrées non rejouées | US-1480/L3 #2348 | aucun : US-1650/L3 attend #2386 d'EP-07, qui vient après |

Les catalogues `messages/*.json` (hors les deux clés de #2093, qu'US-1620 corrige), `conftest.py`,
`support.py`, `api/queries.py`, `loader.py` et `mode.ts` ne s'écrivent dans aucun des trois EPIC —
sauf `support.py` par le lot d'outillage des tests d'EP-07, qui le possède (décision de l'auteur du
2026-11-10) — : une clé ou une fixture qui manque devient une issue.

### Ce que le cadrage laisse à EP-10

Le socle (US-1580/L1 #2398) est le **lot pivot d'EP-10** : `epic/EP-10` se tire d'`epic/EP-09` dès
sa fusion. Il lui garantit `cost_line` et `cost_import`, les colonnes `previous_*` et
`reestimated_at` d'`estimate_line`, la chaîne des migrations arrêtée à `0027`, et l'interface
déclarée que les indicateurs liront : `actual_costs_until(project_id, date, scope)` et
`actual_cost_by_subproject` de `costs`, `remaining_of_revision(session, project_id, revision_id)` et
`startable_tasks` d'`estimate`, à côté de `planned_value` d'EP-07 et des états et dates des tâches
d'EP-06 ; les lots d'EP-10 qui lisent des coûts attendent US-1610/L2 #2404, qui sert
`actual_costs_until`, ceux qui lisent un reste US-1580/L2 #2399, qui sert `remaining_of_revision`
(#2708, « Les décisions du 2026-11-10 ») ; `CalculationContext` s'importe de l'interface
d'`estimate`. EP-10 remplit `register_indicators` de `core/revisions` (EP-04) pour conserver au
marquage ce que ces fonctions calculent, et pose le cache (WF-DAT-0130).

### L'ordre de construction

Le socle d'abord, dès #2373 ; puis ce qui ne dépend que de lui et des lots d'EP-07 déjà fusionnés,
en largeur quatre ; les lectures et les formats après les écritures ; les écrans par l'US qui sert
leur objet ; la vérification d'ensemble en dernier ; le plan de lots (étape 3) le détaille en vagues.

1. **US-1580/L1**, le socle — dès la fusion d'US-1490/L4 #2373 et d'US-1560/L3 d'EP-07, dont
   elle chaîne la migration : la migration `0027`, le sous-paquet `remaining/` de `core/estimate`
   à vide — hors le sous-paquet `remaining/excel/`, qu'US-1630/L1 possède entier et dont les lots suivants d'US-1630 complètent les fichiers — et ses fichiers
   d'interface réexportés, le module
   `core/costs` à vide avec son interface en paquet, `register_coverage` déclaré, l'enregistrement à
   vide dans `register_format`, `register_exporter` et `register_copy`, le contrat de couches, les
   cinq routeurs vides et leurs `asked_*`, `tests/remaining_support.py`, `tests/costs_support.py`, les
   fichiers de tests, `witness/costs.py` à vide, le test des points d'entrée étendu. **Lot pivot
   d'EP-10.** Ni `core/planning`, ni `core/projects`, ni `core/exchanges`, ni le worker. En parallèle,
   dès la branche : **le lot d'outil** d'US-1650 (la chronologie, `witness_costs.json`, après #2384)
   et **l'écriture du classeur** du reste à engager (US-1630, pure, après #2378 et sans attendre le
   socle : le lot crée `core/estimate/remaining/__init__.py` vide s'il n'existe pas, identique à
   celui du socle, comme `pricing/` et `spreading/` en EP-07).
2. **La réestimation** (US-1580 : `setLineRemaining`, `remaining_entry` et `previous_*` lus, la copie,
   la mise à zéro qui termine, après #2372 et #2324), **les lignes propres et le Kanban** (US-1590 :
   `register_open_lines`, `progress_commands`, `listStartableTasks`, après #2324, #2338, #2339 ; la
   mesure),
   **l'en-tête et l'analyse d'une extraction** (US-1610, après #2332), **la lecture du classeur**
   (US-1630, après #2379).
3. **L'application d'une extraction et le journal** (US-1610, après #2375 pour le worker, #2380
   pour les commandes), **la consultation et l'exclusion** (US-1620, `register_cost_facts` après
   #2373), **les indicateurs** (US-1600, après la réestimation et l'application), **le plan de charge
   sur le reste** (US-1580, après #2377), **l'analyse et l'application du reste à engager** (US-1630,
   après la réestimation et #2380).
4. **L'écran des coûts réels** (US-1620), **l'export branché et l'aller-retour** (US-1630, après
   #2381), **la grille de reste à engager et le Kanban branchés** (US-1640, après #2383 et US-1600),
   **la tranche des coûts** (US-1650, après #2385 et #2341), après tout ce qui écrit ; puis **la
   vérification d'ensemble** (US-1650, après #2386), seule.

---

## US-1580 — La réestimation d'une ligne, le reste à engager précédent et le plan de charge sur le reste

- **statut** : fini
- **exigences** : `WF-RAE-0010-A`, `WF-RAE-0040-A`, `WF-RAE-0050-A`, `WF-DEV-0070-A`
- **opérations** : `setLineRemaining`, `listNodes`, `createRevision`, `getProjectWorkload` ;
  `createNode`, `updateEstimateLine` pour la ligne ajoutée après la référence
- **issue** : 2390

**En tant que** chef de projet, **je veux** réestimer une ligne d'une tâche non terminée en saisissant
ses grandeurs — sa charge, ou sa quantité et son débours —, lire à côté ce qu'elle valait au reste à
engager précédent, voir une tâche se terminer quand toutes ses lignes sont mises à zéro, et lire la
charge restante de mon projet par rôle et par mois, **afin de** tenir ma revue périodique sur les
tâches démarrées sans attendre un fichier.

**Critères d'acceptation.**

- `WF-RAE-0010-A` — « Sur un projet dont une tâche est terminée, une démarrée et une non démarrée,
  le reste à engager vaut la somme des deux dernières, la démarrée pour son montant réestimé et
  l’autre pour son montant de référence projeté, plus les provisions des risques identifiés. » : la
  somme des `reestimated_amount` des lignes des tâches non terminées, lue par `listNodes`
  (`totals`) et par US-1600 ; les provisions sont d'EP-08, qui clôt, et comptent zéro ici ;
- `WF-RAE-0010-A` — « Le décalage d’une tâche non démarrée d’une année modifie son montant du taux
  d’inflation. » : constaté par EP-07 (`reinflated`) ; ici, le reste à engager de la révision le
  suit ;
- écart : `WF-RAE-0010-A` — « Écarter un risque de provision 40 diminue le reste à engager de 40 ;
  en identifier un nouveau l’augmente de sa provision. » : les risques sont d'EP-08, qui clôt ;
- `WF-RAE-0010-A` — « La réestimation à 120 d’une ligne budgétée à 100 sur une tâche non démarrée,
  saisie depuis la grille, porte le reste à engager de 100 à 120. » : `setLineRemaining` sur une
  ligne d'une tâche non démarrée, `budgeted_amount` inchangé, `reestimated_amount` à 120 et les
  totaux de la structure portés de 100 à 120 ;
- écart : `WF-RAE-0010-A` — « Un projet portant un risque de provision 40 compte cette provision
  une fois. » : EP-08, qui clôt ;
- `WF-RAE-0010-A` — « Le reste à engager égale la somme des montants réestimés courants des lignes
  des tâches non terminées, lignes de provision des risques identifiés comprises. » : la somme sur
  les lignes des tâches non terminées, démarrées ou non, réestimées ou non ; les lignes de
  provision sont d'EP-08, qui clôt, et il n'en existe aucune ici ;
- `WF-RAE-0010-A` — « Dans une révision créée en 2027 où le taux de 2027 d’une catégorie a été
  accepté, une tâche non démarrée dont une ligne relève de cette catégorie compte pour sa charge au
  taux de 2027, et non au taux de 2026 corrigé d’une année d’inflation. » : constaté par EP-07
  (`applyRateUpdate`, le réestimé rechiffré) ; ici, la ligne non réestimée compte ce réestimé ;
- écart : `WF-RAE-0010-A` — « Après un avenant qui porte de 100 à 150 heures une ligne non
  réestimée d’une tâche non démarrée, le reste à engager compte 150 heures ; une ligne réestimée à
  140 avant l’avenant garde 140. » : l'avenant est d'EP-08, qui clôt ; la règle « une réestimation
  marque la ligne, et la fusion épargne une ligne marquée » demande un fait que cette US écrit :
  la ligne réestimée se distingue d'une ligne qui ne l'a jamais été (« Notes de réalisation ») ;
- `WF-RAE-0040-A` — « Les montants et les grandeurs sont présents pour chaque ligne, au reste à
  engager précédent et courant. » : `listNodes` rend `previous_quantity`, `previous_hours`,
  `previous_unit_disbursement` et `previous_reestimated_amount` à côté des grandeurs et du réestimé
  courants ; nuls avant la première revue ;
- `WF-RAE-0040-A` — « La saisie d’une charge de 80 heures sur une ligne de quantité 1 budgétée à 100
  heures donne un montant réestimé de 80 fois le taux, projeté sur l’année de consommation de la
  ligne (WF-DEV-0030) ; le montant n’est pas saisissable. » : `setLineRemaining` écrit `hours` à 80,
  le réestimé est recalculé par le module de calcul d'EP-07 sur l'année de consommation courante ;
  `RemainingUpdate` n'a pas de champ pour un montant, un champ inconnu est refusé (422) ;
- `WF-RAE-0040-A` — « Les tâches non démarrées n’apparaissent qu’à la demande, et sont alors
  modifiables. » : `listNodes` avec `progress=started` ne rend que les lignes des tâches démarrées,
  avec `progress=started,not_started` celles des deux, et `remaining_entry` est disponible sur une
  ligne d'une tâche non démarrée ; la grille, par US-1640 ;
- `WF-RAE-0040-A` — « La modification d’une ligne portée par une tâche terminée est refusée. » :
  409 `STATE_FORBIDS_OPERATION`, `task_not_completed`, et `remaining_entry.missing_conditions` le dit
  d'avance ;
- `WF-RAE-0040-A` — « Une tâche démarrée dont la fin est dépassée est signalée ; sa date n’est pas
  modifiable depuis cette grille. » : `finish_overdue` d'EP-06 ; la grille, par US-1640 ;
- `WF-RAE-0040-A` — « La saisie d’un reste à engager nul sur toutes les lignes d’une tâche non
  démarrée la termine, avec une date de démarrage égale à sa date de terminaison. » : la dernière
  ligne ouverte mise à zéro avec `completed_on` termine la tâche par l'interface de `core/planning`,
  `started_on` égal à `completed_on`, une tâche qui n'est pas un jalon passant par l'état démarré ;
  sans `completed_on`, 422 `COMPLETION_DATE_REQUIRED` sur `/completed_on`,
  `fields[].params.task_node_id`, et rien n'est écrit ; une saisie qui ne termine pas la tâche
  l'ignore ;
- `WF-RAE-0040-A` — « Une tâche ajoutée depuis la grille de reste à engager apparaît dans la grille
  de planning de la révision en cours, et une tâche ajoutée au planning d’un projet En cours apparaît
  dans la grille de reste à engager parmi les tâches non démarrées ; la révision de référence est
  inchangée, et le budget de référence comme la valeur planifiée ne bougent pas. » : `createNode`
  d'EP-06 et d'EP-07 sur un projet En cours, la tâche et ses lignes à budgété nul, lues par
  `listNodes` avec `progress=not_started` ; le budget de référence de `getEstimateIndicators` et
  `planned_value` d'EP-07 inchangés ; les grilles, par US-1640 ;
- `WF-RAE-0040-A` — « Une ligne ajoutée après la référence peut y être portée à un sous-projet. » :
  `updateEstimateLine` écrit `subproject_id` sur une ligne à budgété nul ; la grille, par US-1640 ;
- `WF-RAE-0040-A` — « Sur un projet qui n’est pas En cours, la grille ne propose ni création ni
  suppression de tâche ou de ligne. » : `edit_remaining` manque `project_in_progress` hors de
  l'état En cours (EP-04), et `setLineRemaining` le refuse par 409 ; la grille, par US-1640 ;
- `WF-RAE-0050-A` — « Après ajout d’une tâche chiffrée en revue périodique, le reste à engager et la
  projection du chef de projet augmentent de son montant ; le budget de référence, la projection au
  budget, la projection au rythme constaté et l’indice de coût sont inchangés. » : le reste à engager
  (`listNodes`, `totals`, et US-1600) et le budget de référence, ici, sur une tâche créée avec une
  ligne sur la structure principale d'un projet En cours ; la projection, les projections et
  l'indice sont d'EP-10, qui clôt ;
- écart : `WF-RAE-0050-A` — « Lorsque la dépense de cette tâche est importée au coût réel, la
  valeur acquise ne change pas et l’indice de coût baisse. » : la valeur acquise et l'indice de coût
  sont d'EP-10, qui clôt ; l'import de la dépense, par US-1610 ;
- `WF-DEV-0070-A` — « La charge d’une ligne portée par une tâche qui couvre exactement deux mois
  civils apparaît sur ces deux mois, au prorata des heures travaillées de la tâche dans chacun. »
- `WF-DEV-0070-A` — « La capacité de chaque rôle est affichée. »
- `WF-DEV-0070-A` — « Le filtre par nœud d’organisation ne laisse voir que les rôles qui en
  relèvent. » : les trois, constatées par EP-07 (US-1520) ;
- `WF-DEV-0070-A` — « Le plan de charge calculé sur le reste à engager ignore les lignes des tâches
  terminées. » : sur `current_remaining`, une tâche terminée par la mise à zéro de son reste n'y
  compte rien ; EP-07 l'a constaté pour une tâche terminée par `setTaskProgress` ;
- `WF-DEV-0070-A` — « Les trois bases sont proposées ; sur un projet sans révision de référence, la
  base de la référence est absente, et sur un projet sans aucune révision marquée, seule la
  révision en cours est proposée. » : constaté par EP-07 et EP-15 ;
- `WF-DEV-0070-A` — « Une tâche démarrée qui couvre exactement quatre mois civils, à mi-parcours à
  la date de calcul — le premier jour du troisième mois —, dont une ligne porte un reste de 80
  heures, présente ces 80 heures sur les deux mois restants au prorata de leurs heures travaillées
  — 40 et 40 s’ils en comptent autant — et rien sur les mois écoulés ; sur une révision marquée, la
  date de calcul est sa date de marquage. » : la ligne réestimée à 80 heures par `setLineRemaining`,
  puis `getProjectWorkload` sur `current_remaining` à la date de calcul, et sur `marked_remaining`
  après le marquage de la révision, la date de marquage pour date de calcul ; le module d'étalement
  d'EP-07 fait le reste ;
- `WF-DEV-0070-A` — « Une tâche non démarrée dont la date de début est antérieure à la date de
  calcul ne présente aucune charge sur les mois écoulés ; sa charge est la même avant et après son
  démarrage. » : constaté par EP-07 ; ici, la même tâche démarrée par `setTaskProgress` présente la
  même charge ;
- propre à l'US : `setLineRemaining` écrit les grandeurs de `reestimated_amount_basis` sur la ligne,
  seul ce qui est envoyé, au compteur lu (412), par la même fonction que la saisie d'EP-07, sous le
  verrou de la structure et dans l'encadrement `history.recording` d'EP-06 ; le réestimé est
  recalculé, le budgété et la lignée inchangés, `previous_*` inchangés ; un débours envoyé pour une
  ligne de main-d'œuvre, une charge pour une ligne hors main-d'œuvre, sont refusés par
  `FIELD_NOT_ACCEPTED`, une grandeur négative par `VALUE_OUT_OF_RANGE`, une catégorie sans taux par
  `HOURLY_RATE_MISSING` (F-09) ; `reason` est conservé avec la ligne et rendu par la lecture de
  la facette, `remaining_reason`, nul avant toute réestimation (#2420) ; la réponse est `NodesWritten`, la tâche porteuse et ses ancêtres recalculés dans
  `ancestors` ;
- propre à l'US : la ligne refuse la réestimation par 409 `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` nommant la première condition qui manque — `task_not_completed` sur
  une tâche terminée, `line_not_provision` sur une ligne de provision (EP-08, jamais manquante ici)
  —, puis `project_in_progress` et `no_background_task_running` de `edit_remaining` ;
  `remaining_entry` dit d'avance les mêmes conditions, et la ligne d'une révision marquée ou d'un
  projet terminal est refusée (`revision_draft`, `project_not_terminal`) ; chaque réponse est
  validée contre le contrat dans les tests du service, et la route déclare la qualité de
  contributeur et `remaining.write` ;
- propre à l'US : à la création d'une révision depuis une révision marquée à l'état En cours, la
  copie écrit sur chaque ligne copiée `previous_quantity`, `previous_hours`,
  `previous_unit_disbursement` et `previous_reestimated_amount` : les grandeurs et le réestimé
  courants de la ligne source ; depuis une révision marquée en chiffrage, et sur une ligne créée
  après, ils sont nuls ; une révision marquée les garde ;
- propre à l'US (lot technique) : la migration d'EP-09, `0027`, chaînée sur `0026` et seule de
  l'EPIC — les quatre colonnes `previous_*` et la marque de réestimation de `estimate_line`, les tables
  `cost_line` et `cost_import` du régime « projet » avec l'unicité sur le projet, la pièce et le
  poste, les droits du rôle du service — ; le module `core/costs` à vide avec son interface en
  paquet, et les fichiers du reste à engager de `core/estimate` à vide ; les registres nouveaux
  déclarés ; un routeur vide par US enregistré dans `app.py`, la déclaration des opérations et des
  permissions par routeur, les fichiers de tests et de tranche du témoin ; le test des points
  d'entrée (#2180) étendu aux registres qu'EP-09 remplit ; `make check` passe sur ce socle, tiré
  d'`epic/EP-07`.

**Notes de réalisation.** La réestimation est une écriture des grandeurs courantes de la ligne
d'EP-07 (`update_line`), par le même module de calcul : rien n'est saisi d'un montant. « Le reste à
engager précédent » est celui de la dernière révision marquée à l'état En cours, copié à l'ouverture
de la révision (décision de l'auteur du 2026-11-07, au cadrage) : nul depuis une offre marquée en
chiffrage, qui n'est pas une revue (`delta_to_previous_revision`). Une ligne réestimée porte une
marque (la date de sa dernière réestimation), que la fusion d'un différentiel (EP-08) lira pour
épargner les lignes réestimées (WF-RAE-0010) ; le socle de l'EPIC est le premier lot de cette US,
et le lot pivot d'EP-10. Les lots qui écrivent une ligne attendent US-1490/L3 #2372 et L4 #2373
d'EP-07.

**Hors périmètre.** Le Kanban et la récapitulative terminée par son reste (US-1590) ; les
indicateurs (US-1600) ; l'import du reste à engager (US-1630) ; la grille (US-1640) ; les lignes de
provision et la fusion (EP-08) ; les projections et l'indice de coût (EP-10).

---

## US-1590 — Les tâches en exécution : le Kanban servi, la récapitulative qui n'attend que ses lignes, la suppression renvoyée

- **statut** : fini
- **exigences** : `WF-RAE-0030-A`, `WF-PLA-0040-A`, `WF-PLA-0050-A`, `WF-PLA-0070-A`
- **opérations** : `listStartableTasks`, `setTaskProgress`, `setLineRemaining`, `deleteNode`,
  `listNodes`
- **issue** : 2391

**En tant que** chef de projet, **je veux** lire mes tâches réparties par état et faire depuis le
Kanban les gestes que chaque carte liste, voir la récapitulative dont toutes les subordonnées sont
terminées rester démarrée et signalée tant qu'une de ses lignes propres garde un reste, et être
renvoyé vers la mise à zéro du reste quand je tente de supprimer une tâche démarrée, **afin de**
déclarer ce qui a commencé et clore mes phases depuis la vue qui les répartit.

**Critères d'acceptation.**

- `WF-RAE-0030-A` — « Une tâche passée à l’état démarré voit ses lignes apparaître dans la grille
  de reste à engager. » : après `setTaskProgress` à `started`, `listNodes` avec `progress=started`
  rend ses lignes, `remaining_entry` disponible ; la grille, par US-1640 ;
- `WF-RAE-0030-A` — « Une tâche non démarrée n’y apparaît qu’à la demande. » : `progress=started`
  ne la rend pas, `progress=started,not_started` la rend ; la grille, par US-1640 ;
- `WF-RAE-0030-A` — « Le passage direct de non démarrée à terminée n’est possible que pour un
  jalon, ou par la saisie d’un reste à engager nul sur toutes les lignes d’une tâche non démarrée
  (WF-RAE-0040) ; un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. » :
  `setTaskProgress` à `completed` sur une tâche non démarrée qui n'est pas un jalon refusée par 409
  `task_is_milestone` (EP-06) ; `setLineRemaining` à zéro sur toutes les lignes d'une tâche non
  démarrée la termine (US-1580) ; un jalon sans ligne terminé par `setTaskProgress` à
  `occurred_on` ;
- `WF-RAE-0030-A` — « Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non
  démarré tant que personne ne le termine. » : `listStartableTasks` rend
  `predecessors_completed` vrai dans `not_started`, et rien ne le termine ;
- `WF-RAE-0030-A` — « Aucune commande ne fait passer une tâche démarrée à l’état non démarré. » :
  constaté par EP-06 (`completed_milestone`) ; ici, aucune carte d'une tâche démarrée ne liste un
  geste vers `not_started` ;
- écart : `WF-RAE-0030-A` — « Un jalon terminé que l’on rouvre est non démarré et ne contribue plus
  à la valeur acquise. » : non démarré, constaté par EP-06 et lu ici dans `not_started` ; la
  valeur acquise est d'EP-10, qui clôt ;
- `WF-RAE-0030-A` — « Une tâche feuille démarrée sans ligne de devis est terminée depuis le
  Kanban. » : sa carte liste `complete` disponible, et `setTaskProgress` l'applique ;
- `WF-PLA-0040-A` — « Après déplacement d’une récapitulative portant deux niveaux de subordonnées,
  les tâches et les lignes déplacées sont inchangées, et le devis totalise le même montant. »
- `WF-PLA-0040-A` — « Les dates et l’état d’une récapitulative ne sont pas saisissables. »
- `WF-PLA-0040-A` — « Une récapitulative dont une subordonnée est démarrée est démarrée ; elle
  n’est terminée qu’après la dernière. » : les trois, constatées par EP-06 et EP-07 ; ici, la
  dernière subordonnée terminée ne termine la récapitulative que si le reste de ses lignes propres
  est nul ;
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont une
  ligne propre porte un reste à engager de 500 est démarrée et signalée ; la saisie d’un reste nul
  sur cette ligne la termine. » : `progress` reste `started`, `awaiting_own_lines` vrai dans
  `listNodes` et dans la colonne `started` de `listStartableTasks`, sa carte offrant
  `enter_remaining` disponible et `complete` indisponible faute de `task_without_lines`, ni `start`
  ni `reopen` (#1851) ; `setLineRemaining` à zéro sur cette ligne la termine, `completed_on` la
  plus tardive des dates de ses subordonnées et de cette saisie, et éteint le drapeau (#1775) ;
- `WF-PLA-0040-A` — « La suppression de la seule subordonnée d’une récapitulative de dix jours
  laisse une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être ajoutée. » :
  constaté par EP-06 ;
- écart : `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et
  dont la seule ligne propre est une provision de 40 est terminée et n’est pas signalée. » : la
  règle « hors lignes de provision » est écrite dans la question que `core/planning` pose aux
  lignes ; la ligne de provision est d'EP-08, qui clôt ;
- `WF-PLA-0040-A` — « Une récapitulative dont la seule subordonnée est un jalon terminé et dont une
  ligne propre garde un reste à engager, privée de ce jalon, est une feuille démarrée d’un jour, non
  un jalon. » : EP-06 fait la feuille d'un jour ; ici, elle reste démarrée parce que sa ligne garde
  un reste, et sa carte passe dans `started` sans le signal, qui ne vaut qu'aux récapitulatives ;
- `WF-PLA-0040-A` — « Une récapitulative terminée dont la seule subordonnée, un jalon, est
  déplacée devient un jalon terminé. » : constaté par EP-06 ;
- écart : `WF-PLA-0040-A` — « Le déplacement d’une sélection qui contient une récapitulative et
  l’une de ses subordonnées laisse la subordonnée sous la récapitulative : le groupe est déplacé
  entier, sans être aplati. » : le déplacement est d’EP-06 (US-1380/L4) ;
- `WF-PLA-0050-A` — « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. »
- `WF-PLA-0050-A` — « Une récapitulative dont la seule subordonnée est un jalon a une durée nulle
  et reste une récapitulative. » : les deux, constatées par EP-06 ;
- `WF-PLA-0050-A` — « Un jalon portant une ligne de devis passe de non démarré à terminé par la
  saisie d’un reste à engager nul ; un jalon sans ligne est terminé depuis le Kanban. » :
  `setLineRemaining` à zéro sur la ligne du jalon le termine, `started_on` égal à `completed_on`,
  sans passer par l'état démarré ; le jalon sans ligne, par `setTaskProgress` ;
- `WF-PLA-0050-A` — « La terminaison depuis le Kanban d’un jalon portant une ligne est refusée en
  renvoyant à la saisie de son reste à engager. » : sa carte liste `complete` indisponible,
  `task_without_lines`, et `enter_remaining` disponible ; `setTaskProgress` refuse par 409
  `task_without_lines` (EP-06) ;
- écart : `WF-PLA-0050-A` — « Un jalon qui ne porte qu’une ligne de provision est terminé depuis le
  Kanban. » : la ligne de provision est d'EP-08, qui clôt ; « porte une ligne » s'écrit « hors
  provision » dans la question posée aux lignes ;
- `WF-PLA-0070-A` — « La suppression d’une récapitulative supprime ses subordonnées et leurs
  lignes, et le devis diminue d’autant. » : constaté par EP-06 et EP-07 ;
- `WF-PLA-0070-A` — « La suppression d’une tâche démarrée est refusée, et l’utilisateur est
  renvoyé vers la mise à zéro de son reste à engager. » : le refus `task_not_started` d'EP-06 ;
  les grilles de planning, de devis et de reste à engager le disent à la tâche et mènent à sa ligne
  dans la grille de reste à engager, sur la révision en cours — par US-1640, qui branche les
  grilles ;
- propre à l'US : `listStartableTasks` rend les tâches de la structure principale de la révision
  courante — la révision en cours, ou la dernière marquée sans elle — en trois colonnes dans
  l'ordre du plan, jamais une récapitulative hors celle qui n'attend plus que ses lignes propres,
  chaque tâche avec ses `available_commands` dans l'ordre de `KanbanCommand`, les conditions dans
  l'ordre du contrat (le geste, puis `project_in_progress`, `no_background_task_running`), vides
  sans `remaining.write`, et `progress` l'état que chaque geste envoie ; sous `remaining.read` ;
  chaque réponse est validée contre le contrat dans les tests du service ;
- propre à l'US : le temps de réponse de `listStartableTasks` sur les mille tâches de PRJ-001 est
  mesuré contre le service, le témoin chargé, et relevé sur la pull request avec celui de l'écran
  du Kanban (#646) : sous la borne `WORKING` d'un écran de grille, les listes simples restent et la
  raison de la présence du Kanban parmi ces écrans est corrigée dans le guide — il lit
  `listStartableTasks`, non `listNodes` — ; au-delà, l'optimisation devient une issue, rien n'est
  fenêtré sans mesure ;
- propre à l'US : la page du Kanban (`…/kanban`) travaille contre le service, `setTaskProgress`
  répond à chaque geste et la carte prend la réponse ; l'aide FBS-4.5.3 et le parcours du Kanban,
  étiqueté `@shared`, sont d'US-1640, qui branche la grille, les aides FBS-4.5* et le fichier de
  parcours qu'ils partagent.

**Notes de réalisation.** `setTaskProgress` et l'état des récapitulatives sont servis par EP-06
(US-1410 #2324) ; `listStartableTasks` les lit, et cette US ne fait que brancher le Kanban d'EP-15
(US-0540) et d'EP-22 (US-1240). Ce qu'elle ajoute à `core/planning` tient en une question posée aux
lignes — le reste des lignes propres hors provision d'une tâche —, que la conception place dans le
crochet de la facette d'EP-07, et qui change deux choses : la récapitulative ne se termine qu'à ce
reste nul, et `awaiting_own_lines` (#1775) est calculé. Les lots attendent US-1410 #2324,
US-1380/L2 #2335, L3 #2338 et US-1390/L2 #2339 d'EP-06 — le dernier à écrire
`core/planning/interface/__init__.py`, qui réexporte le registre —, et US-1490/L4 #2373 d'EP-07,
qui écrit encore les crochets.

**Hors périmètre.** La réestimation elle-même (US-1580) ; la grille (US-1640) ; les lignes de
provision (EP-08) ; la valeur acquise (EP-10).

---

## US-1600 — Les indicateurs de reste à engager

- **statut** : fini
- **exigences** : `WF-RAE-0020-A`
- **opérations** : `getRemainingIndicators`
- **issue** : 2392

**En tant que** chef de projet, **je veux** lire le total de mon reste à engager, ses ventilations
par nature de coût et par sous-projet, la marge sur le budget de référence, l'écart à la revue
précédente, et pour chaque sous-projet la marge entre son budget et la somme de son coût réel et de
son reste, signalée quand elle est dépassée, **afin de** voir où mon projet dérive avant que cela
ne remonte au total.

**Critères d'acceptation.**

- `WF-RAE-0020-A` — « Sur un projet de budget 1 000, de coût réel 500 et de reste à engager 550, la
  marge sur le budget vaut − 50 ; un reste à engager passé de 600 à 550 depuis la revue précédente
  donne un écart de − 50. » : `delta_to_reference` et `delta_to_previous_revision`, un test sans
  base du module et le même sur le service, avec une révision marquée En cours à 600 ;
- `WF-RAE-0020-A` — « Un sous-projet dont le coût réel augmenté du reste à engager dépasse son
  budget est signalé par la couleur, les autres non. » : `by_subproject[].is_over_budget` et
  `zone` à `alert`, `nominal` pour les autres ; le serveur classe, le front ne déduit rien ;
- `WF-RAE-0020-A` — « Sur un projet dont aucune révision n’a été marquée à l’état En cours avant
  celle qui est lue, l’écart correspondant est absent plutôt que nul ; sur un projet sans révision
  de référence, la marge sur le budget l’est aussi. » : `null`, et non zéro, dans les deux cas ;
  une offre marquée en chiffrage n'est pas une revue ;
- `WF-RAE-0020-A` — « La marge sur le budget du projet égale la somme des marges de ses
  sous-projets, ensemble hors sous-projet compris. » : `unassigned` compte les lignes sans
  sous-projet et les lignes de coût imputées au seul projet ; la somme des `variance` égale
  `delta_to_reference` ;
- écart : `WF-RAE-0020-A` — « La couverture des risques présente la réserve de référence, les
  provisions restantes, le coût des risques survenus et l’écart de couverture. » : `coverage` est
  servie à zéro, par une question qu'EP-08 remplit (décision de l'auteur du 2026-11-07, au
  cadrage) ; EP-08 clôt ;
- propre à l'US : `getRemainingIndicators` lit la révision nommée, ou la révision en cours, ou la
  dernière marquée sans elle ; `total` est la somme des réestimés des lignes des tâches non
  terminées (US-1580), `by_cost_type` le ventile par nature, la nature provision à zéro, les parts
  à quatre décimales, la plus grande portant le reste des arrondis ; `by_subproject[].budget` est
  la somme des budgétés des lignes du sous-projet dans la révision de référence, `actual_cost` la
  somme des lignes de coût suivies qui lui sont imputées (US-1610), `remaining` celle des lignes de
  la révision lue ; `delta_to_previous_revision` est le reste à engager courant moins celui de la
  révision marquée précédente qui l'a été à l'état En cours, calculé sur ses lignes et l'état de
  ses tâches à son marquage ; `context` dit la révision, `computed_at`, `is_stored` faux ; sous
  `remaining.read` ; chaque réponse est validée contre le contrat dans les tests du service ;
- propre à l'US : l'encart des indicateurs de l'écran du reste à engager (`RemainingSummary`) lit
  le service ; son parcours est étiqueté `@shared` par US-1640, qui branche l'écran.

**Notes de réalisation.** Le même module de totaux qu'EP-07 (US-1510) sert les ventilations ; le
coût réel par sous-projet vient de l'interface de `core/costs`. La conservation des indicateurs au
marquage (WF-DAT-0040) est d'EP-10 : ici, tout se calcule à la lecture.

**Hors périmètre.** Les indicateurs de projet (EP-10) ; la couverture des risques (EP-08) ; le
portefeuille (EP-11).

---

## US-1610 — L'import des coûts réels (FLX-07) : la correspondance, l'imputation, l'idempotence et le journal

- **statut** : fini
- **exigences** : `WF-INTF-0140-A`, `WF-REF-0190-A`, `WF-CRE-0010-A`, `WF-CRE-0020-A`,
  `WF-CRE-0050-A`, `WF-DAT-0110-A`, `WF-DAT-0070-A`, `WF-INTF-0070-A`
- **opérations** : `uploadFile`, `openImport`, `getImport`, `abandonImport`, `applyImport`,
  `listImports` pour `actual_costs` ; `listCostImports` ; `getProject`, `createSubproject`,
  `getActualCostMapping` pour ce que l'import en lit
- **issue** : 2393

**En tant que** chef de projet, **je veux** importer l'extraction de l'ERP en deux temps — ses
colonnes lues selon la correspondance de l'installation, chaque ligne imputée par son élément
d'OTP, une ligne déjà connue mise à jour et jamais doublée —, et retrouver chaque import dans un
journal qui compte ce qu'il a créé, mis à jour, laissé et rejeté, **afin de** rapprocher ma dépense
de mon budget sans compter deux fois la même pièce.

**Critères d'acceptation.**

- `WF-INTF-0140-A` — « Deux imports successifs du même fichier donnent le même total de coûts
  réels. » : le second compte toutes ses lignes inchangées (`unchanged_count`), aucune créée ;
- `WF-INTF-0140-A` — « Si deux fichiers ont des périodes qui se recouvrent, une ligne présente dans
  les deux n’est comptée qu’une fois. » : la ligne est mise à jour, ou inchangée, par le second ;
- `WF-INTF-0140-A` — « Une ligne déjà importée dont le montant a changé dans l’ERP est mise à jour,
  et son exclusion est préservée. » : l'écart `updated` sur `amount`, `is_in_tracked_scope` et
  `excluded_reason` inchangés ;
- `WF-INTF-0140-A` — « Une facture ventilée sur deux éléments d’OTP, en deux postes de la même
  pièce, donne deux lignes de coût ; deux lignes de la même pièce sans poste sont rejetées au compte
  rendu. » : deux postes, deux lignes ; deux lignes de même pièce et de même poste, nul compris,
  rejetées chacune par `DUPLICATE_COST_LINE`, `params.rows` nommant les rangs des autres (#1340) ;
- `WF-INTF-0140-A` — « Le compte rendu (WF-INTF-0080) présente les lignes ajoutées, mises à jour,
  inchangées et rejetées avant confirmation. » : `differences` (`added`, `updated`, cible
  `actual_cost_line`, `label` la pièce, `document_item` le poste, `fields` les colonnes changées,
  `subproject` et `passthrough.<colonne>` comprises), `unchanged_count`, `rejected`, et
  `requires_confirmation_reasons` (`lines_outside_project`, `unknown_subproject`) ;
- `WF-REF-0190-A` — « Sur une installation neuve, l’import d’un fichier de coûts réels est refusé
  et nomme la correspondance à régler. » : `openImport` refuse par 409 `STATE_FORBIDS_OPERATION`,
  `actual_cost_mapping_complete`, `params.columns` les colonnes exigées sans intitulé, après les
  conditions de l'état du projet ; la commande `import_actual_costs` du projet le dit d'avance ;
- `WF-REF-0190-A` — « Après déclaration de « Elément d’OTP », « Nº pièce référence », « Date de la
  pièce » et « Val./Devise objet », une extraction dont l’en-tête est « Élément d’OTP »
  s’importe. » : les intitulés comparés sans égard à la casse, aux accents ni aux espaces en bout,
  par la fonction d'EP-05 ;
- `WF-REF-0190-A` — « Une colonne « Nom Matricule » non déclarée n’est pas conservée, et le compte
  rendu la nomme ; déclarée conservée, elle est restituée à la consultation des lignes importées
  ensuite. » : `ignored` (`columns`, `labels` tels que le fichier les porte) ; déclarée, elle entre
  dans `passthrough` des lignes du prochain import, celles des imports antérieurs ne changeant pas ;
- `WF-REF-0190-A` — « Une extraction à laquelle manque une colonne exigée est refusée, et le
  message nomme la colonne attendue. » : `openImport`, 422 `FILE_FORMAT_UNREADABLE`,
  `params.expected_format` à `actual_costs`, sans `expected_version`, `params.missing_columns`
  chaque colonne et ses intitulés déclarés, dans l'ordre de la correspondance ;
- `WF-CRE-0010-A` — « Les quatre attributs significatifs sont renseignés pour chaque ligne
  importée. » : la pièce, la date, le montant et l'imputation ; le poste quand l'extraction le
  donne ;
- `WF-CRE-0010-A` — « Les colonnes conservées sont restituées à la consultation. » : `passthrough`,
  par `listActualCosts` (US-1620) ;
- `WF-CRE-0010-A` — « Une colonne que la correspondance ne déclare pas conservée ne l’est pas. » :
  absente de `passthrough` et de `meta.passthrough_columns` ;
- `WF-CRE-0010-A` — « Une ligne de montant négatif est acceptée et diminue le coût réel. » : un
  avoir, `amount` négatif, et les totaux le comptent ;
- `WF-CRE-0020-A` — « Une ligne dont l’élément d’OTP ne respecte pas la forme attendue — vide, ou
  sans rien avant la barre oblique — est signalée au compte rendu et n’est pas importée ; une ligne
  qui ne porte que le code projet, sans sous-projet, est importée et imputée au seul projet. » :
  `WBS_ELEMENT_INVALID`, `params.wbs_element`, de même pour un élément sans rien après la barre
  oblique (`A.ABC.26001/`, #2721) ; `subproject_id` et `subproject_code` nuls ;
- `WF-CRE-0020-A` — « Une ligne d’un autre projet est rejetée et signalée. » :
  `WBS_ELEMENT_OUTSIDE_PROJECT`, `params.project_code` le code lu, `lines_outside_project` parmi les
  motifs de confirmation, même quand la ligne est doublée et rejetée `DUPLICATE_COST_LINE` (#2724),
  et le journal la compte rejetée ;
- `WF-CRE-0020-A` — « Sur le projet de code A.ABC.26001, une ligne d’élément A.ABC.26001/10001 est
  imputée au sous-projet 10001, et une ligne d’élément A.ABC.26002/10001 est rejetée comme d’un
  autre projet. » : le code projet peut contenir des points, seule la barre oblique sépare les deux
  codes (C-373, #1340) ;
- `WF-CRE-0020-A` — « Une ligne dont le sous-projet est inconnu est importée, imputée au projet, et
  apparaît comme telle à la consultation avec son code. » : `subproject_id` nul, `subproject_code`
  conservé, `unknown_subproject` parmi les motifs de confirmation ;
- `WF-CRE-0020-A` — « Après création du sous-projet dont dix lignes portaient le code, ces dix
  lignes lui sont imputées sans réimport, et l’ensemble hors sous-projet diminue d’autant. » :
  `createSubproject` d'EP-04 appelle, dans sa transaction, la question que `core/costs` enregistre
  dans `core/projects`, qui impute les lignes de ce code ; un recodage (`updateSubproject`) ne
  change l'imputation d'aucune ligne (D-10) ;
- `WF-CRE-0020-A` — « Une ligne réimportée avec un autre élément d’OTP change d’imputation. » :
  l'écart `updated` sur `subproject`, `subproject_id` recalculé ;
- `WF-CRE-0050-A` — « Après un import, le journal présente une entrée datée du jour avec ses
  comptes de lignes, et la consultation des coûts réels affiche cette date comme celle du dernier
  import. » : `listCostImports` rend l'entrée écrite à l'application — `imported_at`, `actor` le
  compte qui a confirmé, `period_from`, `period_to`, les quatre comptes —, du plus récent au plus
  ancien, paginé ; `last_import_at` de `listActualCosts`, par US-1620 ;
- `WF-DAT-0110-A` — « Deux imports du même fichier de coûts réels laissent le même nombre de lignes
  et les mêmes montants, et une ligne exclue le reste. » : l'application insère ou met à jour sur le
  triplet, sans toucher `is_in_tracked_scope` ;
- `WF-DAT-0110-A` — « L’insertion directe en base de deux lignes de coût de même projet, de même
  numéro de pièce et de même poste est rejetée ; de postes différents, elle aboutit. » : l'unicité
  (`project_id`, `document_number`, `document_item`) déclarée `NULLS NOT DISTINCT`, éprouvée par le
  propriétaire ;
- `WF-DAT-0110-A` — « Deux imports successifs du même fichier de devis donnent une révision en
  cours au contenu identique. » : constaté par EP-07 ;
- `WF-DAT-0070-A` — « Après modification d’une tâche par un utilisateur, la ligne porte son compte
  et l’horodatage de la modification. » : constaté par EP-06 ;
- `WF-DAT-0070-A` — « Une ligne créée par un import porte le compte qui l’a confirmé. » : la ligne
  de coût créée par la tâche d'application porte `requested_by` dans `created_by`, et mise à jour
  par un réimport dans `updated_by` ;
- `WF-DAT-0070-A` — « Une ligne mise à jour par un traitement automatique porte la plateforme
  comme auteur. » : constaté par EP-03 et EP-05 (la synchronisation des comptes) et par EP-06 (la
  purge) ; aucune ligne de coût n'est écrite par un traitement automatique ;
- `WF-INTF-0070-A` — « Un fichier conforme à chacun des formats de ANNEXE B: Formats d’échanges
  Excel est accepté. » : le format « Coûts réels », ici ; le devis, constaté par EP-07 ; le reste à
  engager, par US-1630 ;
- `WF-INTF-0070-A` — « Un fichier de devis ou de reste à engager sans version, ou d’une version non
  reconnue, est refusé avec un message qui nomme le format et la version attendus ; un fichier de
  coûts réels auquel manque une colonne exigée par la correspondance est refusé avec un message qui
  la nomme. » : les coûts réels, ici ; le devis, constaté par EP-07 ; le reste à engager, par
  US-1630 ;
- `WF-INTF-0070-A` — « Le projet est inchangé. » : après chaque refus ;
- propre à l'US : le format `actual_costs` enregistré par `register_format` lit le premier onglet
  seul, ses intitulés en ligne 1, par openpyxl en valeurs — une colonne calculée par la valeur
  enregistrée — ; un numéro de pièce en texte ou en nombre entier, lu comme texte ; une date dans
  une cellule de date ou un texte AAAA-MM-JJ ; un montant signé dans une cellule numérique, arrondi
  au centime `ROUND_HALF_UP` s'il porte plus de deux décimales (#2721), un nombre en texte rejeté
  (`NUMBER_INVALID`) ; un rejet par cellule nommant sa colonne par `params.column` (#2722) ; une
  ligne vide ignorée ; `read_count` les lignes
  lues, `format_version` nul ; `ImportRequest.period_from` et `period_to` portés par l'import et
  journalisés, une fin qui précède le début refusée par 422 (`/period_to`, `VALUE_OUT_OF_RANGE`) ;
  l'import n'écrit sur aucune structure ni révision (`structure_id`, `revision_id` nuls), et
  `ProjectCommand.import_actual_costs` est listée sous `actual_costs.write`, indisponible hors de
  l'état En cours (`project_in_progress` ; D-04 de la revue du 2026-10-31, `docs/api/2026-10-31-contrat-spec-et-fixtures.md`), puis `no_background_task_running`, puis
  `actual_cost_mapping_complete` ; un compte rendu analysé s'applique tel qu'il a été analysé, même
  si la correspondance change entre-temps ; l'application écrit dans la transaction de la tâche
  d'EP-06, les lignes puis l'entrée du journal, inscrit `import_apply` au journal d'audit avec sa
  nature, et n'entre pas dans l'historique annulable ; chaque réponse est validée contre le contrat
  dans les tests du service.

**Notes de réalisation.** La mécanique est celle d'EP-06 (`register_format`), le format est propre
à cet EPIC ; la correspondance se lit par l'interface de `core/cost_settings` (EP-05). Les lignes
de coût et le journal vivent dans deux tables du régime « projet » (Tableau 10 : `cost_line`,
`cost_import`), posées par le socle (US-1580/L1). Le témoin importe par les interfaces, non par
ce format (US-1650).

**Hors périmètre.** La consultation, l'exclusion et l'écran (US-1620) ; les extractions
d'engagements et d'heures (PO-01) ; les indicateurs (EP-10).

---

## US-1620 — La consultation des coûts réels, l'exclusion du périmètre suivi et l'écran branché

- **statut** : fini
- **exigences** : `WF-CRE-0030-A`, `WF-CRE-0040-A`, `WF-PRJ-0050-A`, `WF-CYC-0100-A`,
  `WF-CYC-0110-A`
- **opérations** : `listActualCosts`, `setActualCostTrackedScope`, `listCostImports`,
  `listSubprojects`, `deleteSubproject`, `updateEstimateLine`, `moveNodes`, `getProject`
- **issue** : 2394

**En tant que** chef de projet, **je veux** lire les coûts réels de mon projet en liste, filtrée par
sous-projet, par période et selon l'exclusion, avec le total suivi, le total exclu et le total
général, exclure une ligne que la comptabilité impute mais que je n'ai pas budgétée et la
réintégrer, **afin de** trier le périmètre que mes indicateurs comptent sans rien perdre du
rapprochement avec l'ERP.

**Critères d'acceptation.**

- `WF-CRE-0030-A` — « Une ligne exclue n’apparaît dans aucun total d’indicateur, et reste visible
  dans la consultation des coûts réels. » : `totals.tracked` et le coût réel de
  `getRemainingIndicators` (US-1600) ne la comptent pas, `listActualCosts` la rend,
  `is_in_tracked_scope` faux, `in_tracked_scope=false` la retient seule ;
- `WF-CRE-0030-A` — « Après un second import couvrant la même période, elle est toujours exclue. » :
  l'import d'US-1610 ne touche pas l'exclusion, constaté ici après `setActualCostTrackedScope` ;
- `WF-CRE-0040-A` — « Les trois totaux sont présents, et le total général égale la somme du total
  du périmètre suivi et du total exclu. » : `totals`, sur toutes les lignes retenues, pas la page ;
- `WF-CRE-0040-A` — « Un filtre par sous-projet ou par période s’applique aux trois
  (WF-IHM-0130). » : `subproject_id`, `from`, `to` sur la date de pièce, les totaux et
  `meta.passthrough_columns` recalculés ; une fin qui précède le début refusée par 422 ; un
  sous-projet inconnu par `UNKNOWN_SUBPROJECT` ;
- `WF-CRE-0040-A` — « L’exclusion d’une ligne depuis la liste modifie immédiatement les deux
  premiers totaux. » : `setActualCostTrackedScope` écrit l'état visé et le motif, sans compteur
  (idempotent), et la lecture suivante déplace le montant du total suivi au total exclu ;
- `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. »
- `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est
  refusée. »
- `WF-PRJ-0050-A` — « La création d’un sous-projet de code « SP/01 », « Synthèse » ou de plus de
  trente et un caractères est refusée. » : les trois, constatées par EP-04 ;
- `WF-PRJ-0050-A` — « La suppression d’un sous-projet portant des coûts réels est refusée. » :
  `subproject_has_actual_costs` d'EP-04 rempli par la question de `core/costs` — une ligne de coût
  imputée, suivie ou exclue — ; 409 `subproject_without_actual_costs`, et `listSubprojects` le dit
  d'avance (`has_actual_costs`, le filtre du même nom) ;
- `WF-PRJ-0050-A` — « La suppression d’un sous-projet cité par une révision marquée est refusée. » :
  constaté par EP-04 et EP-07 ;
- `WF-PRJ-0050-A` — « La suppression d’un sous-projet que porte une ligne de devis de la révision en
  cours est refusée ; elle aboutit une fois cette ligne passée à un autre sous-projet. » : constaté
  par EP-07 ;
- `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d’une ligne d’une tâche démarrée, dont le
  sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d’une ligne d’une
  tâche non démarrée aboutit, comme celui de la ligne de provision d’un risque identifié. » : la
  règle `SUBPROJECT_HAS_ACTUAL_COSTS` d'EP-07 manque pour la première fois — `updateEstimateLine`,
  le collage et l'import la refusent, la ligne ne nomme plus `estimate_line.subproject_id` dans
  `editable_fields` — ; la ligne d'une tâche non démarrée aboutit ; la ligne de provision est
  d'EP-08, qui clôt ;
- `WF-CYC-0100-A` — « Toute modification d’un projet terminal est refusée, qu’elle soit tentée par
  la saisie, par un import Excel ou MS Project, ou par un traitement automatique. » : ici, la
  réestimation, le geste du Kanban, l'exclusion et l'ouverture d'un import de coûts réels ou de
  reste à engager sur un projet terminal, par 409 `project_not_terminal` ; la saisie et MS Project,
  constatés par EP-04 et EP-06 ; le traitement automatique, par la tâche d'application d'un import
  confirmé avant la sortie, qui revérifie et refuse (EP-06) ;
- `WF-CYC-0110-A` — « Toutes les vues de consultation d’un projet clos s’affichent normalement, et
  ses exports aboutissent. Seules les modifications sont refusées. » : `listActualCosts`,
  `listCostImports`, `getRemainingIndicators` et `listStartableTasks` répondent sur un projet
  terminal, les cartes sans geste ; l'export du reste à engager aboutit, par US-1630 ; les
  commandes `import_actual_costs` et `exclude_cost_lines` ne sont pas listées ;
- propre à l'US : `listActualCosts` pagine, trie par chaque colonne (`document_item`,
  `excluded_reason`, `passthrough.<colonne>` comparés en texte, les valeurs absentes après dans
  l'ordre croissant), les pièces les plus récentes d'abord par défaut, rend `subproject_code` et
  `subproject_label` résolus, `passthrough` et l'union `meta.passthrough_columns` dans l'ordre des
  imports puis du fichier, `last_import_at` nul sans import ; sous `actual_costs.read` ;
- propre à l'US : `setActualCostTrackedScope` est gardée par `cost_line_exclude`, refusée par 409
  `project_not_terminal` puis `project_in_progress` (`exclude_cost_lines` ; D-04 de la revue du 2026-10-31), inscrite au
  journal d'audit (`cost_line_exclude`, `cost_line_reinstate`, WF-SEC-0030), et n'entre pas dans
  l'historique annulable (WF-IHM-0110, constaté par EP-08 qui clôt) ; chaque réponse est validée
  contre le contrat dans les tests du service ;
- propre à l'US : l'écran des coûts réels (`…/actual-costs`) et le journal des imports travaillent
  contre le service, `MockupNotice` en est retiré, `actual-costs.spec.ts` porte `@shared`, le test
  de la colonne « Poste » cite WF-CRE-0010-A (#1525), l'aide FBS-3.1.3 (fr, en) dit ce que l'import
  fait de la correspondance et les messages `reference.actualCostMapping.complete` et `.missing`
  disent le refus qu'il tient (#2093) ; l'aide FBS-4.7 dit ce que le service fait.

**Notes de réalisation.** L'écran est celui d'EP-02 (US-0230/L3), d'EP-16 (US-0620, US-0630) et
d'EP-17 ; cette US ne le réécrit pas. `has_actual_costs` d'un sous-projet et la suppression refusée
sont des questions d'EP-04 que `core/costs` remplit par un registre de `core/projects`, déclaré
après US-1490/L4 #2373 d'EP-07, qui écrit encore ce module.

**Hors périmètre.** L'import lui-même (US-1610) ; les indicateurs de projet et le cache (EP-10) ;
la ligne de provision (EP-08).

---

## US-1630 — Le format Excel du reste à engager : export (FLX-06), import (FLX-05) et aller-retour

- **statut** : en cours
- **exigences** : `WF-INTF-0120-A`, `WF-INTF-0130-A`, `WF-INTF-0070-A`, `WF-REV-0060-A`,
  `WF-IHM-0080-A`
- **opérations** : `requestExport` (`remaining`), `getBackgroundTaskResult` ; `uploadFile`,
  `openImport`, `getImport`, `abandonImport`, `applyImport`, `listImports` pour `remaining` ;
  `createRevision`, `getRateUpdateProposal`, `applyRateUpdate` pour la révision que l'import crée
- **issue** : 2395

**En tant que** chef de projet, **je veux** exporter le reste à engager d'une révision au format
« Reste à engager » de l'annexe B, un onglet par sous-projet, le faire remplir par les responsables
de lots et le réimporter dans ma révision en cours — chaque ligne retrouvant la sienne, une tâche
dont tout le reste est à zéro terminée à la date de la revue —, **afin de** mener ma revue
périodique avec l'outil que mes interlocuteurs connaissent.

**Critères d'acceptation.**

- `WF-INTF-0120-A` — « Même critère que WF-INTF-0100, appliqué aux grandeurs réestimées ; les
  montants budgétés et les lignées de toutes les lignes sont inchangés après l’import, et une ligne
  absente du fichier conserve son reste à engager. » : les lignes du fichier rapprochées par leur
  lignée, leurs grandeurs écrites par la même fonction que `setLineRemaining` (US-1580) — en jours
  pour une ligne de main-d'œuvre, en montant pour une ligne hors main-d'œuvre —, `budgeted_amount`
  et `lineage_id` relus identiques ; une ligne absente du fichier inchangée, sans écart ; une ligne
  sans identifiant créée à budgété nul sous la tâche qu'elle désigne, dans le sous-projet de son
  onglet ; une ligne nouvelle sous une tâche terminée rejetée (`task_not_completed`, `params.tasks`,
  #1794) ; une ligne d'une tâche démarrée dont le sous-projet a reçu des coûts réels, placée dans
  un autre onglet, rejetée en nommant ce sous-projet (`SUBPROJECT_HAS_ACTUAL_COSTS`) ; une ligne
  d'une tâche non démarrée placée dans un autre onglet en change, un écart `subproject` ; une tâche,
  un rôle ou un sous-projet inconnus, un libellé ambigu, une ligne qui laisserait sa tâche sans
  heure, rejetés comme au devis ; les lignes de provision, ignorées et signalées
  (`provision_lines`), sont d'EP-08, qui clôt ; le compte rendu désigne chaque ligne par son onglet
  et son rang ;
- `WF-INTF-0120-A` — « Un reste à engager exporté d’une révision marquée puis réimporté dans la
  révision en cours met à jour les lignes de même lignée sans en créer aucune. » : `differences`
  sans `added` ;
- `WF-INTF-0120-A` — « Avec huit heures par jour, une ligne de main-d’œuvre dont le fichier porte
  trois jours a un reste de vingt-quatre heures. » : la constante d'heures par jour de
  l'installation (`getDurationUnits`, EP-05) ;
- `WF-INTF-0120-A` — « Une tâche démarrée dont toutes les lignes du fichier portent zéro est
  terminée à la date de la revue ; une tâche non démarrée dont les lignes sont laissées telles
  quelles reste non réestimée. » : `completed_tasks` nomme la tâche dès l'analyse, `completed_on` la
  date de la revue lue en « Synthèse » (B9, #2702) et jamais nulle, l'application la termine à cette
  date — une tâche non démarrée qui n'est pas un jalon passe par l'état démarré, un jalon non, les
  deux avec `started_on` égal à `completed_on` — ; une ligne laissée telle quelle n'est pas un écart ;
- `WF-INTF-0130-A` — « Même critère d’aller-retour que WF-INTF-0110. » : un reste à engager
  exporté puis réimporté sans modification dans la révision en cours ne présente ni écart ni rejet,
  `unchanged_count` égal à `read_count`, les lignes relues identiques ; un export de la révision en
  cours ou d'une révision marquée, de la structure principale par défaut, sur un projet terminal
  aussi ;
- `WF-INTF-0070-A` — « Un fichier conforme à chacun des formats de ANNEXE B: Formats d’échanges
  Excel est accepté. » : le format « Reste à engager », ici ; le devis, constaté par EP-07 ; les
  coûts réels, par US-1610 ;
- `WF-INTF-0070-A` — « Un fichier de devis ou de reste à engager sans version, ou d’une version non
  reconnue, est refusé avec un message qui nomme le format et la version attendus ; un fichier de
  coûts réels auquel manque une colonne exigée par la correspondance est refusé avec un message qui
  la nomme. » : `openImport` refuse un reste à engager sans version ou d'une version inconnue par
  422 `FILE_FORMAT_UNREADABLE`, `expected_format` à `remaining` et `expected_version` ; le devis,
  constaté par EP-07 ; les coûts réels, par US-1610 ;
- `WF-INTF-0070-A` — « Le projet est inchangé. » : après chaque refus ;
- `WF-REV-0060-A` — « Une révision créée en 2027 porte l’année de référence 2027. »
- `WF-REV-0060-A` — « À sa création, lorsque la précédente portait 2026, l’écart est présenté
  catégorie par catégorie et la mise à jour peut être refusée. »
- `WF-REV-0060-A` — « Une catégorie refusée ou sans taux pour 2027 est chiffrée au taux de 2026
  corrigé d’une année d’inflation. » : les trois, constatées par EP-07 ;
- `WF-REV-0060-A` — « Une révision créée en 2027 par un import de reste à engager porte les taux de
  2026 projetés d’une année ; la mise à jour catégorie par catégorie reste proposée jusqu’à son
  marquage, et l’accepter pour une catégorie la rechiffre au taux de 2027. » : l'application d'un
  reste à engager sur un projet dont toutes les révisions sont marquées crée la révision en cours
  (EP-06), dont les taux sont copiés projetés (EP-07) ; `getRateUpdateProposal` la propose,
  `applyRateUpdate` rechiffre la catégorie retenue, l'horloge posée en 2027 ;
- `WF-REV-0060-A` — « Une mise à jour refusée à la création d’une révision est acceptée ensuite
  depuis la révision en cours, qui est alors rechiffrée au taux de 2027 pour cette catégorie. » :
  constaté par EP-07 ;
- `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable et
  présente son avancement. » : constaté par EP-04 ;
- `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de son
  aboutissement. » : le parcours de l'import d'un reste à engager quitte l'écran des échanges
  pendant l'application et lit l'aboutissement dans la coquille, contre le service ;
- `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même
  traitement peut être relancé. » : constaté par EP-04 ;
- propre à l'US : l'exporteur `remaining` écrit le classeur de l'annexe B avec XlsxWriter, sur le
  modèle du prototype de la spécification — « Synthèse » (format et version en A1-B2, le projet,
  l'entreprise, le client, la révision, la date de la revue en B9 (#2702), la structure, la
  devise ; par sous-projet et pour le projet, le budget, les coûts réels, le reste à engager, la
  projection, l'écart signé dans le sens de la dérive, l'avancement financier, la ventilation du
  reste par nature et en jours par code comptable de main-d'œuvre) ; un onglet par sous-projet nommé par son code, ramené aux règles
  d'Excel par `sheet_name` d'EP-07 (#2190), et « Hors sous-projet », chacun avec son en-tête
  (budget, coûts réels, reste à engager, projection, écart, avancement) puis ses lignes des tâches
  non terminées en tableau Excel — tâche, description, état, rôle ou catégorie, désignation, budget,
  reste précédent, jours restants ou débours restant, colonnes calculées, lignée masquée — aux
  listes et formules étendues à la saisie ; « Tâches » (les tâches non terminées par sous-projet,
  leur état, leur coefficient) et « Paramètres » (le référentiel de la révision et les heures par
  jour), protégés ; le logo et le pied de page ; `review_date` de la demande, le jour par défaut ;
  le fichier `.xlsx`, `<code ou libellé du projet>-<version>-reste-a-engager.xlsx` ; `requestExport`
  sous `export_remaining`, gardée par `remaining.read`, disponible sur un projet terminal ;
- propre à l'US : le format `remaining` enregistré lit l'en-tête (A1, B1, A2, B2) et la date de la
  revue de « Synthèse », analyse chaque onglet de sous-projet et « Hors sous-projet » par ses
  en-têtes, ignore les colonnes inconnues, les lignes vides et la ligne de total, lit les nombres
  dans des cellules numériques et rejette un nombre en texte, rapproche par la lignée, désigne la
  tâche par « Tâches » ou par son libellé ; `ProjectCommand.import_remaining` sous
  `remaining.write`, indisponible hors de l'état En cours (`project_in_progress`), puis
  `no_background_task_running` et `may_create_revision` ; l'application écrit sous le verrou de la
  structure dans la transaction de la tâche d'EP-06, sans entrée d'historique, et termine les
  tâches de `completed_tasks` ; l'écran des échanges, branché par EP-06, importe et exporte un reste
  à engager contre le service ; chaque réponse est validée contre le contrat dans les tests du
  service.

**Notes de réalisation.** Le format reprend la mécanique d'EP-06 et les leçons du prototype
`docs/spec/exemples/prototype_rae.py` (XlsxWriter écrit, openpyxl lit, comme EP-07 l'a décidé) ;
`sheet_name` vient de l'interface de `core/estimate` (US-1550/L1 #2378). Le témoin n'importe aucun
reste à engager (`import_remaining_analysed` est une variante) : l'aller-retour se joue sur un projet
que la course crée.

**Hors périmètre.** Le format « Devis » (EP-07) et « Coûts réels » (US-1610) ; les lignes de
provision et l'import sur un différentiel (EP-08) ; l'écran des échanges lui-même (EP-06).

---

## US-1640 — La grille de reste à engager et le Kanban branchés sur le service

- **statut** : en cours
- **exigences** : `WF-RAE-0040-A`, `WF-RAE-0030-A`, `WF-REF-0010-A`
- **opérations** : `listNodes`, `setLineRemaining`, `createNode`, `deleteNode`, `moveNodes`,
  `updateEstimateLine`, `listStartableTasks`, `setTaskProgress`, `getRemainingIndicators`,
  `getProjectWorkload` ; toutes celles de l'EPIC que la grille et le Kanban lisent et écrivent
- **issue** : 2396

**En tant que** chef de projet, **je veux** que la grille de reste à engager et le Kanban
travaillent contre le service — les lignes des tâches démarrées par défaut, les non démarrées à la
demande, la réestimation sur les grandeurs, la mise à zéro qui demande une date, la création et le
déplacement des tâches et des lignes d'un projet En cours, le sous-projet d'une ligne, les cartes et
leurs gestes —, **afin de** mener ma revue sans faux back.

**Critères d'acceptation.**

- `WF-RAE-0040-A` — « Les montants et les grandeurs sont présents pour chaque ligne, au reste à
  engager précédent et courant. » : les colonnes du reste précédent lisent `previous_*` du service
  (US-1580) ;
- `WF-RAE-0040-A` — « La saisie d’une charge de 80 heures sur une ligne de quantité 1 budgétée à 100
  heures donne un montant réestimé de 80 fois le taux, projeté sur l’année de consommation de la
  ligne (WF-DEV-0030) ; le montant n’est pas saisissable. » : depuis la cellule, contre le service ;
  la cellule du montant est calculée ;
- `WF-RAE-0040-A` — « Les tâches non démarrées n’apparaissent qu’à la demande, et sont alors
  modifiables. » : la grille lit `progress=started` par défaut, le bouton ajoute `not_started`, et
  les lignes rendues se saisissent comme `remaining_entry` le dit ;
- `WF-RAE-0040-A` — « La modification d’une ligne portée par une tâche terminée est refusée. » : la
  grille ne l'offre pas (`remaining_entry`), et un refus du service se dit à la ligne ;
- `WF-RAE-0040-A` — « Une tâche démarrée dont la fin est dépassée est signalée ; sa date n’est pas
  modifiable depuis cette grille. » : `finish_overdue` du service, la date en lecture ;
- `WF-RAE-0040-A` — « La saisie d’un reste à engager nul sur toutes les lignes d’une tâche non
  démarrée la termine, avec une date de démarrage égale à sa date de terminaison. » : la grille
  demande la date au `COMPLETION_DATE_REQUIRED` du service et rejoue la saisie ; la tâche relue est
  terminée ;
- `WF-RAE-0040-A` — « Une tâche ajoutée depuis la grille de reste à engager apparaît dans la grille
  de planning de la révision en cours, et une tâche ajoutée au planning d’un projet En cours apparaît
  dans la grille de reste à engager parmi les tâches non démarrées ; la révision de référence est
  inchangée, et le budget de référence comme la valeur planifiée ne bougent pas. » : le parcours du
  report d'EP-06 (#1057) rejoué entre la grille de reste à engager et celle du planning sur un
  projet En cours que la course crée ; la révision de référence et le budget de référence relus
  identiques ; la valeur planifiée, par US-1580 ;
- `WF-RAE-0040-A` — « Une ligne ajoutée après la référence peut y être portée à un sous-projet. » :
  le sous-menu « Sous-projet » d'EP-15 (US-0480), contre le service ;
- `WF-RAE-0040-A` — « Sur un projet qui n’est pas En cours, la grille ne propose ni création ni
  suppression de tâche ou de ligne. » : la grille suit `edit_remaining` de la structure principale,
  que le service rend indisponible hors de l'état En cours ;
- `WF-RAE-0030-A` — « Une tâche passée à l’état démarré voit ses lignes apparaître dans la grille
  de reste à engager. » : démarrée au Kanban, la tâche a ses lignes dans la grille relue, contre le
  service ;
- `WF-RAE-0030-A` — « Une tâche non démarrée n’y apparaît qu’à la demande. » : la grille par
  défaut ne la montre pas, le bouton la montre ;
- `WF-RAE-0030-A` — « Le passage direct de non démarrée à terminée n’est possible que pour un
  jalon, ou par la saisie d’un reste à engager nul sur toutes les lignes d’une tâche non démarrée
  (WF-RAE-0040) ; un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. » :
  le parcours du jalon terminé à une date saisie d'EP-15 (US-0540), contre le service ; la saisie
  d'un reste nul, depuis la grille ;
- `WF-RAE-0030-A` — « Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non
  démarré tant que personne ne le termine. » : la marque « prêt à terminer » sur
  `predecessors_completed` du service ;
- `WF-RAE-0030-A` — « Aucune commande ne fait passer une tâche démarrée à l’état non démarré. » :
  aucune carte d'une tâche démarrée n'offre ce geste, le service ne le listant pas ;
- écart : `WF-RAE-0030-A` — « Un jalon terminé que l’on rouvre est non démarré et ne contribue plus
  à la valeur acquise. » : rouvert au Kanban, il est dans la colonne non démarrée ; la valeur
  acquise est d'EP-10, qui clôt ;
- `WF-RAE-0030-A` — « Une tâche feuille démarrée sans ligne de devis est terminée depuis le
  Kanban. » : par le menu de la carte, contre le service ;
- `WF-REF-0010-A` — « Aucun écran ne propose de supprimer un objet du référentiel. »
- `WF-REF-0010-A` — « Un objet désactivé n’apparaît plus dans les listes de choix, mais reste
  affiché sur les éléments qui l’emploient. »
- `WF-REF-0010-A` — « Une fois réactivé, il est de nouveau proposé. » : les trois, constatées par
  EP-05 ;
- `WF-REF-0010-A` — « Après désactivation d’un rôle de ressource, les lignes qui le portent sont
  signalées dans la grille de devis et dans celle du reste à engager, et restent lisibles. » : la
  grille de reste à engager signale `uses_inactive_object` d'EP-07, les libellés résolus ; la grille
  de devis, constatée par EP-07 ;
- `WF-REF-0010-A` — « La désactivation d’une nature désactive ses catégories. »
- `WF-REF-0010-A` — « La réactivation d’une catégorie dont la nature est désactivée est refusée. » :
  les deux, constatées par EP-05 ;
- propre à l'US : la grille de reste à engager lit `listNodes` servi — le filtre `progress`, les
  colonnes du reste précédent et courant, `remaining_entry`, `finish_overdue`, `awaiting_own_lines`
  et la marque des lignes propres ouvertes, les totaux relus après chaque écriture —, écrit chaque
  grandeur par `setLineRemaining`, crée, déplace et supprime tâches et lignes sur un projet En
  cours, porte une ligne à un sous-projet, et lit les indicateurs (US-1600) et le lien vers le plan
  de charge sur `current_remaining` ; le renvoi d'une suppression refusée vers la mise à zéro
  (WF-PLA-0070, US-1590) s'écrit ici, dans les grilles de planning, de devis et de reste à engager ; `MockupNotice` est retiré de l'écran du reste à engager ; les aides
  `frontend/help/fr/FBS-4.5*.md` disent ce que le service fait ; `remaining.spec.ts` porte
  `@shared`, les écritures sur un projet que la course crée ; chaque réponse lue est celle du
  service.

**Notes de réalisation.** Les écrans sont ceux d'EP-02 (US-0230), d'EP-14, d'EP-15 (US-0460,
US-0480, US-0540), d'EP-17 (US-0730b) et d'EP-22 (US-1240) ; cette US ne les réécrit pas. Un manque
que le branchement révèle devient une issue ; un manque du contrat, une « Interface contract
issue ». Le fichier `remaining.spec.ts` porte les parcours de la grille et du Kanban : une seule US
l'étiquette.

**Hors périmètre.** Les lignes de provision et la fusion (EP-08) ; l'avancement physique et la
valeur acquise (EP-10) ; les écrans des coûts réels (US-1620).

---

## US-1650 — Le témoin : la tranche des coûts réels et du reste à engager, et les parcours rejoués

- **statut** : en cours
- **exigences** : `WF-QUA-0040-A`, `WF-INTF-0010-A`
- **opérations** : aucune en propre ; le chargement passe par les interfaces du noyau
- **issue** : 2397

**En tant que** développeur, **je veux** charger, sur une plateforme qui porte les lignes du témoin,
les imports de coûts réels de PRJ-001 et leurs lignes, l'exclusion de la réception du client,
l'extraction rejouée et expirée, et rejouer contre le service tous les parcours du reste à engager,
du Kanban, des coûts réels et de leurs échanges écrits sur le faux back, **afin que** les tests déjà
écrits prouvent le service sur le plus gros projet, coûts compris.

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour la tranche des coûts — les cinq imports de coûts réels de PRJ-001 (3 avril,
  4, 6 et 11 mai, 3 juin), leur ligne du journal des imports et leur entrée du journal des coûts
  avec leurs périodes et leurs comptes, les vingt-huit lignes de coût qu'ils ont apportées ou mises à
  jour, chacune avec son poste, son imputation, ses colonnes conservées et l'audit de ses imports,
  l'exclusion de la réception du client le 6 avril à 9 h 15 avec son motif, l'extraction d'avril
  rejouée, analysée le 2 juin et expirée —, chargée par `waterfall-api load-witness` par les
  interfaces, avec les identifiants et les instants du témoin ; le reste à engager précédent des
  lignes de la révision 102 vient de la référence 101 par la copie, sans tranche ; les provisions et
  les risques sont d'EP-08, les volumes entiers d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes
  identiques. » : deux plateformes chargées portent les mêmes identifiants, imputations et totaux ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les fournisseurs et les pièces sont ceux du témoin, fictifs ;
- écart : `WF-INTF-0010-A` — « Un utilisateur porteur du rôle prédéfini « chef de projet » crée un
  projet et atteint, sur un projet où il est habilité, les fonctions de gestion des révisions
  (FBS-4.1), de paramétrage du projet, contributeurs compris (FBS-4.2), de planification (FBS-4.3),
  de chiffrage (FBS-4.4), de gestion des risques (FBS-4.6), d’estimation du reste à engager
  (FBS-4.5), de gestion des coûts réels (FBS-4.7), de lecture des indicateurs (FBS-4.8), de sortie
  du cycle de vie (FBS-4.9) et d’échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les
  mène jusqu’à leur terme, marquage d’une révision, exclusion d’une ligne de coût et déclaration
  d’une sortie compris. » : le reste à engager (FBS-4.5), les coûts réels (FBS-4.7), l'exclusion
  d'une ligne de coût et les flux FLX-05 à FLX-07, ici, par le compte « chef de projet » de la
  course ; les révisions, le paramétrage, la sortie, la planification, le chiffrage et les autres
  flux sont constatés par EP-04, EP-06 et EP-07 ; les risques et les indicateurs sont d'EP-08 et
  d'EP-10, EP-08 clôt ;
- propre à l'US (lot d'outil) : `make mock-data` écrit, à côté des exemples, le fichier de la
  tranche des coûts que la commande lit — les imports par leur numéro, leur instant, leur import
  des échanges, leur période, leurs lignes rejetées et inchangées ; chaque ligne par sa pièce, son
  poste, sa date, son montant, son code de sous-projet, ses colonnes conservées, les imports qui
  l'ont apportée et son exclusion — depuis `wftools.mockwitnesscosts`, sans que le back importe
  `wftools` ;
- propre à l'US : `witness/costs.py` charge, après la tranche des lignes, chaque import à son
  instant de la chronologie par les interfaces de `core/exchanges` et de `core/costs` —
  identifiants et instants imposés, l'auteur du témoin pour compte —, ses lignes créées ou mises à
  jour, puis l'exclusion par la fonction de `setActualCostTrackedScope` à son instant, et
  l'extraction expirée ; les lectures du témoin chargé — `actual_costs`, `actual_costs_page`,
  `actual_costs_subproject`, `cost_imports`, `imports`, `subprojects_with_actual_costs`,
  `remaining_indicators`, `startable_tasks`, `workload_marked_remaining`, `project` — sont comparées
  aux exemples, aux colonnes d'audit, aux imports du planning et du devis, aux provisions, à la
  couverture des risques et aux montants qui en dépendent près, listés dans le test ;
- propre à l'US : tous les parcours du reste à engager, du Kanban, des coûts réels et de l'import
  d'un reste à engager ou d'une extraction étiquetés `@shared` passent contre le service, le témoin
  chargé ; la définition de fini est constatée — une extraction importée deux fois sans doublon, une
  ligne exclue qui le reste, un reste exporté et réimporté sans écart, une tâche terminée par la mise
  à zéro de son reste — ; les entrées du guide qu'EP-07 a marquées « levées par EP-09 » (les coûts,
  le reste à engager, le Kanban) sont levées, le guide disant ce que la tranche charge et ce
  qu'EP-08 et EP-13 y ajoutent ; le statut de cette US est passé `fini` dans le fichier — chaque
  autre US l'est par le lot qui la termine.

**Notes de réalisation.** La tranche suit la chronologie d'EP-04 (`Act.at`) et vient après celle
des lignes (EP-07, US-1570/L2 #2385) : les imports de coûts sont des événements de la chronologie
sans écriture jusqu'ici (« Import de coûts réels », douze à dix-huit), que cette tranche écrit, par
les interfaces et non par le moteur d'import — pas de fichier Excel ni de worker dans le chargeur
(décision de l'auteur du 2026-11-07, au cadrage). Le fichier de la tranche est un lot d'outil,
lançable tôt, après celui d'EP-07 (US-1570/L1 #2384), seul autre lot à écrire `wftools`. Le
calculé devient l'attendu : les totaux, imputations et indicateurs du témoin sont ceux que le
service calcule, et un désaccord avec une fixture se tranche par la spécification.

**Hors périmètre.** Les risques et les provisions (EP-08) ; les indicateurs de projet (EP-10) ;
les trois cents projets et les dix-huit mille lignes de coût du §4.6.2 (EP-13).

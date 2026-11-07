---
id: EP-09
titre: Suivre ce qui a été dépensé, et réestimer ce qui reste à engager
statut: à planifier
depend_de: EP-07
famille: front, back
issue:
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

- le Kanban : démarrer une tâche, rouvrir une tâche terminée ;
- la grille de reste à engager, la composition du reste et ses indicateurs, l'ensemble « hors
  sous-projet » compris ;
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
- les écrans du reste à engager et des coûts réels de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- l'échange MS Project — EP-06 ; celui du devis — EP-07 ;
- les indicateurs de projet, dont l'indice de coût que dégradent les tâches ajoutées — EP-10 ;
- les sauvegardes, second compartiment du stockage objet — EP-03 et EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`. WF-PLA-0040 et WF-PLA-0050 sont commencées
par EP-06 et closes ici : leur Vérif demande le reste à engager d'une ligne et le Kanban (cadrage
d'EP-06, décision de l'auteur du 2026-11-07). WF-REV-0060 et WF-REF-0010 sont commencées par EP-07
et closes ici : leur Vérif demande un import de reste à engager et la grille de reste à engager
(cadrage d'EP-07, décision de l'auteur du 2026-11-07).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0070-A` | Formats d’échange Excel | fin — amorcée en EP-07 | — |
| `WF-INTF-0140-A` | Import des coûts réels (FLX-07) | entière | — |
| `WF-REF-0190-A` | Correspondance de l’extraction des coûts réels | fin — amorcée en EP-05, EP-16 | — |
| `WF-PLA-0040-A` | Hiérarchie des tâches | fin — amorcée en EP-06 | — |
| `WF-PLA-0050-A` | Jalons | fin — amorcée en EP-06 | — |
| `WF-PLA-0070-A` | Suppression d’une tâche | fin — amorcée en EP-06 | — |
| `WF-DEV-0070-A` | Plan de charge du projet | fin — amorcée en EP-07, EP-15 | — |
| `WF-RAE-0010-A` | Composition du reste à engager | entière | — |
| `WF-RAE-0020-A` | Indicateurs de reste à engager | entière | — |
| `WF-RAE-0030-A` | Démarrage d’une tâche | fin — amorcée en EP-15 | — |
| `WF-RAE-0040-A` | Grille de reste à engager | fin — amorcée en EP-15 | — |
| `WF-RAE-0050-A` | Tâches ajoutées en cours d’exécution | début — close en EP-10 | — |
| `WF-CRE-0010-A` | Attributs d’une ligne de coût | entière | — |
| `WF-CRE-0020-A` | Imputation d’une ligne de coût | entière | — |
| `WF-CRE-0030-A` | Exclusion du périmètre suivi | entière | — |
| `WF-CRE-0040-A` | Consultation des coûts réels | entière | — |
| `WF-CRE-0050-A` | Journal des imports | entière | — |
| `WF-DAT-0070-A` | Colonnes d’audit | fin — amorcée en EP-03 | — |
| `WF-DAT-0110-A` | Idempotence garantie par la base | fin — amorcée en EP-07 | — |
| `WF-INTF-0120-A` | Import du reste à engager (FLX-05) | entière | — |
| `WF-INTF-0130-A` | Export du reste à engager (FLX-06) | entière | — |
| `WF-PRJ-0050-A` | Sous-projets | fin — amorcée en EP-15, EP-16, EP-04 | — |
| `WF-CYC-0100-A` | Lecture seule des projets terminaux | fin — amorcée en EP-04 | — |
| `WF-CYC-0110-A` | Consultation des projets terminaux | fin — amorcée en EP-04 | — |
| `WF-IHM-0080-A` | Traitements longs | fin — amorcée en EP-02, EP-15, EP-04 | — |
| `WF-REV-0060-A` | Année de référence et mise à jour des taux à la création d’une révision | fin — amorcée en EP-15, EP-07 | — |
| `WF-REF-0010-A` | Désactivation des objets du référentiel | fin — amorcée en EP-05, EP-07 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (6) :

- `revisions` : `setLineRemaining` ;
- `analysis` : `getRemainingIndicators`, `listStartableTasks` ;
- `costs` : `listActualCosts`, `setActualCostTrackedScope`, `listCostImports`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (10) :

- `revisions` : `deleteNode`, `setTaskProgress` ;
- `analysis` : `getProjectWorkload` ;
- `exchanges` : `uploadFile`, `listImports`, `openImport`, `getImport`, `abandonImport`, `applyImport`, `requestExport` — le reste à engager et les coûts réels.

## Constats reçus

Relevés par la revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`)
et tranchés par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), que le service
suit une fois figé.

- #1775 — `awaiting_own_lines`, la récapitulative qui n'attend plus que ses lignes propres (F-05 ;
  contrat #1774).
- #1851, reporté à EP-22 (US-1240) — `listStartableTasks` liste aussi la récapitulative démarrée qui
  n'attend plus que ses lignes propres, avec ses gestes (décision de l'auteur du 2026-11-04) : le
  service le sert tel que le contrat le dit.
- #1794 — l'import du reste à engager rejette la ligne nouvelle sous une tâche terminée (I-05 ;
  contrat #1793).

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

- #1525 — front : le test de la colonne « Poste » cite WF-CRE-0040-A, dont le Vérif ne nomme pas
  les colonnes de la grille (relevé par US-0630/L2, EP-16 ; reporté ici avec #1340, le service du
  poste, par la décision de l'auteur du 2026-10-27, confirmée au cadrage d'EP-17 le 2026-10-28) :
  la citation se corrige quand EP-09 réalise le poste.
- #2093 — front : l'aide FBS-3.1.3 (fr, en) et les messages `reference.actualCostMapping.complete`
  et `.missing` de `/reference/costs/actual-cost-mapping` à reprendre quand l'import lit la
  correspondance (relevé par US-0870, EP-05) : l'aide dit l'import « pas encore offert », les
  messages disent le refus que l'import tiendra.

- #646 [EP-09] front : le Kanban rend ses 960 cartes en listes simples, sans fenêtre — relevé par
  EP-14/L45b : EP-09, qui construit le Kanban contre le service, mesure sur mille tâches réelles
  avant toute optimisation ; EP-14 garde les listes simples sous le délai `WORKING`. Reporté
  d'EP-14 (2026-10-10), puis d'EP-06 à EP-09 au cadrage d'EP-06 (décision de l'auteur du
  2026-11-07) ; l'issue est retitrée et relabellisée à l'ouverture des issues d'EP-06.

Le rattachement de WF-REF-0190 est réécrit au cadrage d'EP-16 (décision de l'auteur du
2026-10-22). C-374 la rattachait entière ici ; EP-05 la commence en stockant la correspondance,
EP-16 en écrit le contrat et la page, et EP-09 la clôt.

## Préalables

`epic/EP-09` se tire d'`epic/EP-07` dès la fusion de son lot pivot, **US-1490/L1 #2370** — le socle
d'EP-07, qui pose `estimate_line` avec ses grandeurs courantes et de référence, ses trois montants,
son délai de paiement et son sous-projet, les tables images, et l'interface de `core/estimate` déclarée
(`update_line`, que `setLineRemaining` étendra ; `revision_has_lines`) —, et non de `main` à la livraison
d'EP-07 (décision de l'auteur du 2026-11-07, pour toute la série EP-06 → EP-07 → EP-09 → EP-10 → EP-08 ;
l'exception du README, « Branches ») : elle reprend `epic/EP-07` à chaque lot que celui-ci fusionne et se
fusionne dans `main` après elle. Les lots d'EP-09 qui réestiment des lignes attendent aussi US-1490/L3
#2372 et L4 #2373 (la ligne lue, créée, modifiée, supprimée et déplacée), ceux du Kanban
US-1410 #2324 d'EP-06 ; chaque lot nomme ceux qu'il attend par leur numéro. Le reste à engager part des
montants budgétés. Le point ouvert PO-01
(extraction des engagements et des heures par l'ERP) est à relire avant de détailler les US de
l'import.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.5 et du §3.4.5.7 sont des tests qui passent
  (WF-QUA-0020) ;
- un fichier de coûts réels conforme à l'annexe B s'importe en deux temps, et un abandon laisse
  le projet inchangé ;
- deux imports du même fichier laissent les mêmes lignes, et une ligne exclue le reste ;
- l'interruption de l'application laisse le projet dans son état antérieur ; un compte rendu
  expiré ne s'applique plus, et son fichier n'est plus sur le stockage objet ;
- une tâche démarrée au Kanban voit ses lignes réestimables, et la mise à zéro de son reste la
  termine ;
- le parcours de bout en bout importe des coûts réels et réestime un reste, contre le service
  réel.

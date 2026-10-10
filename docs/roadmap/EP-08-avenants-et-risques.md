---
id: EP-08
titre: Gérer les risques, leurs provisions et la réserve, et déplacer la référence par avenant
statut: à planifier
depend_de: EP-10
famille: front, back
issue:
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
- les structures différentielles, leur coexistence, leur fusion ou leur abandon ;
- la contractualisation d'un avenant, qui produit la nouvelle référence, et la survenance
  d'un risque, qui fusionne son devis propre dans la révision en cours ;
- les bornes de la correction manuelle d'une référence ;
- la valeur planifiée recalculée sur la nouvelle référence ;
- les écrans des risques de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- le calcul des indicateurs — EP-10 ; ici, leurs exemples chiffrés devant un risque survenu,
  une fusion ou un avenant, qui se closent dans cet EPIC ;
- les risques du portefeuille — EP-11.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-REV-0040-A` | Désignation de la révision de référence | fin — amorcée en EP-04 | — |
| `WF-REV-0050-A` | Fusion d’un différentiel | entière | — |
| `WF-PLA-0170-A` | Rattachement au lotissement | fin — amorcée en EP-06 | — |
| `WF-REV-0100-A` | Structures de coûts d'une révision | fin — amorcée en EP-04 | — |
| `WF-DEV-0080-A` | Valeur planifiée | fin — amorcée en EP-07 | — |
| `WF-RIS-0010-A` | Attributs d’un risque | entière | — |
| `WF-RIS-0020-A` | États d’un risque | entière | — |
| `WF-RIS-0030-A` | Devis propre d’un risque | entière | — |
| `WF-RIS-0040-A` | Grille de suivi des risques | entière | — |
| `WF-RIS-0050-A` | Réserve pour risques et couverture | entière | — |
| `WF-RIS-0060-A` | Survenance d’un risque | entière | — |
| `WF-ADM-0100-A` | Catalogue des permissions | fin — amorcée en EP-03 | — |
| `WF-IND-0030-A` | Valeur acquise | fin — amorcée en EP-10 | — |
| `WF-IND-0100-A` | Courbe de coûts cumulés | fin — amorcée en EP-10 | — |
| `WF-INTF-0010-A` | Usages du chef de projet | fin — amorcée en EP-06 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (11) :

- `revisions` : `createCostStructure`, `mergeCostStructure` ;
- `risks` : `listRisks`, `createRisk`, `getRisk`, `updateRisk`, `listRiskReviews`, `reviewRisk`, `declareRiskOccurrence`, `getProjectRiskMatrix`, `deleteRisk`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (9) :

- `revisions` : `designateReferenceRevision`, `listCostStructures`, `updateEstimateLine` ;
- `analysis` : `getRemainingIndicators`, `getProjectRiskCoverage`, `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves` — devant un risque survenu, une fusion ou un avenant ;
- `reference` : `getReferenceSettings`.

## Préalables

EP-10 livré, et EP-09 avant lui : la fusion conserve les montants réestimés et épargne les
tâches démarrées, et les indicateurs se lisent devant un risque survenu, une fusion ou un
avenant.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.6, et ceux de WF-REV-0050, WF-IND-0030 et
  WF-IND-0100 qui citent un risque survenu, une fusion ou un avenant, sont des tests qui
  passent (WF-QUA-0020) ;
- deux structures différentielles coexistent, et la fusion de l'une laisse l'autre intacte ;
- après fusion, la révision produite porte le nom de version demandé et devient la référence ;
- la modification du devis propre d'un risque identifié ne change pas le budget de référence ;
- le parcours de bout en bout déclare un risque, le fait survenir et contractualise un avenant,
  contre le service réel.

## Constats reçus

- #763 [EP-14] front : les formulaires du risque (provision de L42p, exemples de succès de
  `createRisk`, `updateRisk`, `reviewRisk`) — reporté d'EP-14/L53 (#760) : l'écran des risques de
  la maquette est en lecture seule. Les formulaires de déclaration, de modification et de réexamen
  suivront les règles de la provision qu'EP-14/L42p a écrites au contrat — la catégorie choisie
  parmi les catégories actives de type provision pour risques dont la nature est active, non
  demandée s'il n'y en a qu'une ; le sous-projet facultatif ; leur changement selon
  `update_provision` ; la catégorie redemandée au retour à l'état identifié quand
  `provision_cost_category_is_active` est faux ; les refus `PROVISION_CATEGORY_REQUIRED`,
  `INACTIVE_REFERENCE_OBJECT` et `active_provision_category` —, après que le contrat aura reçu les
  exemples de succès de ces trois opérations.

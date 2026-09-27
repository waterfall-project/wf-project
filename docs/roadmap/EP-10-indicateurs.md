---
id: EP-10
titre: Lire où en est un projet : avancement, indices, projections et courbes
statut: à planifier
depend_de: EP-08
issue:
---

# EP-10 — Indicateurs de projet

## Objet

La date et le périmètre de calcul, la granularité par sous-projet, la valeur acquise,
l'avancement financier et physique, les projections à terminaison, les indices de coût et de
délai et leurs seuils, le diagramme temps/temps, la courbe des coûts cumulés, les courbes de
valeur acquise et les projections de décaissement. Les indicateurs d'une révision marquée sont
calculés dans la transaction qui la marque et conservés ; ceux de la révision en cours sont
calculés à la demande et mis en cache.

Il rassemble tout ce qui précède, et c'est ici que se closent les Vérif des EPIC antérieurs qui
citaient un indicateur : les tâches ajoutées en cours d'exécution, la fusion d'un différentiel,
la survenance d'un risque, l'avancement physique de la grille de planning.

## Ce qui en fait partie

- chacun des indicateurs du §3.4.5.8, pour le projet et pour chaque sous-projet, l'ensemble
  « hors sous-projet » compris ;
- la présentation « non calculable » d'un indicateur au dénominateur nul ;
- les seuils de vigilance et d'alerte appliqués aux indices, sur l'échelle de signalement
  commune ;
- le calcul au marquage, dans la même transaction, et la conservation des indicateurs ;
- le cache des indicateurs de la révision en cours et son invalidation ;
- le diagramme temps/temps sur l'identité de lignée des jalons inscrits ;
- les courbes, rendues par Apache ECharts ;
- les écrans des indicateurs de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- l'agrégation sur plusieurs projets — EP-11 ;
- la mesure des temps de réponse aux volumes du §4.6.2 — EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-REF-0170-A` | Seuils d’alerte des indices | fin — amorcée en EP-05 | — |
| `WF-REV-0050-A` | Fusion d’un différentiel | fin — amorcée en EP-08 | — |
| `WF-PLA-0130-A` | Attributs d’une tâche | fin — amorcée en EP-06 | — |
| `WF-PLA-0060-A` | Inscription aux suivis | fin — amorcée en EP-06 | — |
| `WF-RAE-0050-A` | Tâches ajoutées en cours d’exécution | fin — amorcée en EP-09 | — |
| `WF-RIS-0050-A` | Provisions et budget de référence | fin — amorcée en EP-08 | — |
| `WF-RIS-0060-A` | Survenance d’un risque | fin — amorcée en EP-08 | — |
| `WF-IND-0010-A` | Date et périmètre de calcul | entière | — |
| `WF-IND-0020-A` | Granularité des indicateurs | entière | — |
| `WF-IND-0030-A` | Valeur acquise | entière | — |
| `WF-IND-0040-A` | Avancement financier et consommation du budget | entière | — |
| `WF-IND-0050-A` | Projections à terminaison | entière | — |
| `WF-IND-0060-A` | Avancement physique | entière | — |
| `WF-IND-0070-A` | Indice de coût | entière | — |
| `WF-IND-0080-A` | Indice de délai | entière | — |
| `WF-IND-0090-A` | Diagramme temps/temps | entière | — |
| `WF-IND-0100-A` | Courbe de coûts cumulés | entière | — |
| `WF-IND-0110-A` | Courbes de valeur acquise | entière | — |
| `WF-IND-0120-A` | Projections de décaissement | entière | — |
| `WF-ARC-0070-A` | Autorité du serveur | fin — amorcée en EP-04 | — |
| `WF-DAT-0030-A` | Identité de lignée des objets d’une révision | fin — amorcée en EP-04 | — |
| `WF-DAT-0040-A` | Conservation des indicateurs des révisions marquées | fin — amorcée en EP-04 | — |
| `WF-DAT-0130-A` | Contenu et invalidation du cache | entière | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (5) :

- `analysis` : `getProjectIndicators`, `getMilestoneTracking`, `getCostCurve`, `getEarnedValueCurves`, `getProjectCashOut`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (12) :

- `platform` : `startRestore` ;
- `reference` : `getReferenceSettings`, `updateReferenceSettings` ;
- `revisions` : `mergeCostStructure`, `createNode`, `setTaskProgress`, `setNodeTracking` ;
- `analysis` : `getEstimateIndicators`, `getRemainingIndicators` ;
- `risks` : `createRisk`, `reviewRisk`, `declareRiskOccurrence`.

## Préalables

EP-08 livré : le budget de référence dépend des provisions et des avenants.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.8, et ceux de WF-RIS-0050, WF-RIS-0060,
  WF-REV-0050 et WF-RAE-0050, sont des tests qui passent (WF-QUA-0020) ;
- le marquage échoue entièrement si le calcul de ses indicateurs échoue, et les indicateurs
  conservés sont inchangés après un import de coûts postérieur ;
- après vidage du cache, les valeurs recalculées sont identiques, et l'indisponibilité du cache
  n'empêche ni lecture ni saisie ;
- un indicateur affiché est identique à celui que l'API renvoie pour la même date et le même
  périmètre ;
- le parcours de bout en bout lit les indicateurs et les courbes d'un projet, contre le service
  réel.

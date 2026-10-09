---
id: EP-10
titre: Lire où en est un projet : avancement, indices, projections et courbes
statut: à planifier
depend_de: EP-09
famille: front, back
issue:
---

# EP-10 — Indicateurs de projet

## Objet

La date et le périmètre de calcul, la granularité par sous-projet, la valeur acquise,
l'avancement financier et physique, les projections à terminaison, les indices de coût et de
délai et leurs seuils, le diagramme temps/temps, la courbe des coûts cumulés avec sa lecture
en décaissements, et les courbes de valeur acquise. Les indicateurs d'une révision marquée sont
calculés dans la transaction qui la marque et conservés ; ceux de la révision en cours sont
calculés à la demande et mis en cache.

Il vient dès qu'un projet a une référence, des coûts réels et un reste à engager, avant les
risques et les avenants (revue de la ventilation, 2026-10-09) : le pilotage d'un projet en
cours sert avant ces événements plus rares, qui le modifient ensuite. C'est ici que se closent
les Vérif des EPIC antérieurs qui citaient un indicateur — les tâches ajoutées en cours
d'exécution, l'avancement physique de la grille de planning — ; celles qui citent un risque
survenu, une fusion ou un avenant se closent en EP-08, qui dispose alors des indicateurs.

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

- les indicateurs devant un risque survenu, une fusion ou un avenant — EP-08, qui clôt
  WF-IND-0030 et WF-IND-0100 sur ces cas ;
- l'agrégation sur plusieurs projets — EP-11 ;
- la mesure des temps de réponse aux volumes du §4.6.2 — EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-REF-0170-A` | Seuils d’alerte des indices | fin — amorcée en EP-05 | — |
| `WF-PLA-0130-A` | Attributs d’une tâche | fin — amorcée en EP-06 | — |
| `WF-PLA-0060-A` | Inscription aux suivis | fin — amorcée en EP-06 | — |
| `WF-RAE-0050-A` | Tâches ajoutées en cours d’exécution | fin — amorcée en EP-09 | — |
| `WF-IND-0010-A` | Date et périmètre de calcul | entière | — |
| `WF-IND-0020-A` | Granularité des indicateurs | entière | — |
| `WF-IND-0030-A` | Valeur acquise | début — close en EP-08 | — |
| `WF-IND-0040-A` | Avancement financier et consommation du budget | entière | — |
| `WF-IND-0050-A` | Projections à terminaison | entière | — |
| `WF-IND-0060-A` | Avancement physique | entière | — |
| `WF-IND-0070-A` | Indice de coût | entière | — |
| `WF-IND-0080-A` | Indice de délai | entière | — |
| `WF-IND-0090-A` | Diagramme temps/temps | entière | — |
| `WF-IND-0100-A` | Courbe de coûts cumulés | début — close en EP-08 | — |
| `WF-IND-0110-A` | Courbes de valeur acquise | entière | — |
| `WF-IND-0130-A` | Évolution des indices | entière | — |
| `WF-ARC-0070-A` | Autorité du serveur | fin — amorcée en EP-04 | — |
| `WF-DAT-0030-A` | Identité de lignée des objets d’une révision | fin — amorcée en EP-04 | — |
| `WF-DAT-0040-A` | Conservation des indicateurs des révisions marquées | fin — amorcée en EP-04 | — |
| `WF-DAT-0130-A` | Contenu et invalidation du cache | entière | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (5) :

- `analysis` : `getProjectIndicators`, `getMilestoneTracking`, `getCostCurve`, `getEarnedValueCurves`, `getIndexHistory`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (6) :

- `reference` : `getReferenceSettings`, `updateReferenceSettings` ;
- `revisions` : `createNode`, `setTaskProgress`, `setNodeTracking` ;
- `analysis` : `getEstimateIndicators`.

## Préalables

EP-09 livré : la valeur acquise, les indices et les projections se calculent sur la référence, les coûts réels et le reste à engager.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.8 qui ne citent ni risque survenu ni avenant, et
  ceux de WF-RAE-0050, sont des tests qui passent (WF-QUA-0020) ;
- le marquage échoue entièrement si le calcul de ses indicateurs échoue, et les indicateurs
  conservés sont inchangés après un import de coûts postérieur ;
- après vidage du cache, les valeurs recalculées sont identiques, et l'indisponibilité du cache
  n'empêche ni lecture ni saisie ;
- un indicateur affiché est identique à celui que l'API renvoie pour la même date et le même
  périmètre ;
- le parcours de bout en bout lit les indicateurs et les courbes d'un projet, contre le service
  réel.

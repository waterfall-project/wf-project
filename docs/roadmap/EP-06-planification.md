---
id: EP-06
titre: Construire le planning d'un projet, et le lire en grille, en Gantt et en arborescence
statut: à planifier
depend_de: EP-04
famille: front, back
issue:
---

# EP-06 — Planification

## Objet

Les tâches et leur hiérarchie, les jalons, les liaisons, le calendrier applicable, les modes de
planification et l'horizon d'un projet ; la grille de planning ; le diagramme de Gantt et le
chemin critique ; l'arborescence de tâches et son export ; les chronologies nommées ; le
squelette de planning engendré du lotissement.

Les lignes de devis sont portées par les tâches — l'arbre est commun —, si bien que le planning
précède le chiffrage. C'est aussi la première grille dont les saisies sont conservées :
l'annulation multi-niveaux (WF-IHM-0110) s'y clôt, conflits entre contributeurs compris.

## Ce qui en fait partie

- l'arbre des tâches de la structure principale : création, modification, déplacement,
  indentation, suppression ;
- les attributs d'une tâche, son état et sa date, les jalons, les liaisons, le calendrier
  applicable, le mode de planification et l'horizon de quinze ans ;
- le calcul des dates, des marges et du chemin critique ;
- la grille de planning, avec la saisie au clavier, le collage depuis un tableur et l'annulation
  servis par le serveur, le menu contextuel de ses cellules et le branchement de ses commandes —
  l'arbre pliable et le pliage commun avec le Gantt sont déjà faits par EP-02/L40, qu'EP-06
  reprend sur le service ;
- le diagramme de Gantt et l'arborescence de tâches, en lecture seule, et l'export de
  l'arborescence ;
- les chronologies nommées, l'inscription des tâches et des jalons, et l'export PNG ;
- le squelette de planning engendré du lotissement ;
- les écrans du planning de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- les lignes de devis — EP-07 ; l'avancement physique que la grille affiche, calculé sur
  elles — EP-10 ;
- la suppression d'une tâche démarrée, renvoyée vers la mise à zéro de son reste à engager, et
  le démarrage par le Kanban — EP-09 ;
- le diagramme temps/temps, qui lit l'inscription des jalons faite ici — EP-10 ;
- l'import et l'export MS Project — EP-12.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0010-A` | Usages du chef de projet | début — close en EP-12 | — |
| `WF-PRJ-0030-A` | Squelette de planning | entière | — |
| `WF-PLA-0010-A` | Calendrier applicable à une tâche | entière | — |
| `WF-PLA-0020-A` | Mode de planification | entière | — |
| `WF-PLA-0030-A` | Liaisons entre tâches | entière | — |
| `WF-PLA-0040-A` | Hiérarchie des tâches | entière | — |
| `WF-PLA-0050-A` | Jalons | entière | — |
| `WF-PLA-0070-A` | Suppression d’une tâche | début — close en EP-09 | — |
| `WF-PLA-0130-A` | Attributs d’une tâche | début — close en EP-10 | — |
| `WF-PLA-0150-A` | Horizon d’un projet | entière | — |
| `WF-PLA-0060-A` | Inscription aux suivis | début — close en EP-10 | — |
| `WF-PLA-0140-A` | Chronologies nommées | entière | — |
| `WF-PLA-0080-A` | Grille de planning | entière | — |
| `WF-PLA-0090-A` | Diagramme de Gantt | entière | — |
| `WF-PLA-0100-A` | Chemin critique | entière | — |
| `WF-PLA-0110-A` | Vue en arborescence de tâches | entière | — |
| `WF-PLA-0120-A` | Export de l’arborescence de tâches | entière | — |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | fin — amorcée en EP-02 | — |
| `WF-PLA-0160-A` | Unités de durée | entière | — |
| `WF-QUA-0080-A` | Corpus de plannings de référence et schéma d’échange | entière | — |

WF-PLA-0080 et WF-PLA-0090 sont partiels avant cet EPIC : l'arbre pliable des grilles et le pliage
commun de la grille et du Gantt sont faits par EP-02/L40, dans la maquette, sans qu'aucune US
d'EP-02 les cite. Ils restent « entière » ici : EP-06 les vérifie en entier, sur le service, et
garde la saisie, le menu contextuel des cellules et le branchement des commandes.

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (19) :

- `system` : `getBackgroundTaskResult` ;
- `projects` : `listTimelines`, `createTimeline`, `deleteTimeline` ;
- `revisions` : `listNodes`, `createNode`, `deleteNode`, `updateTaskFacet`, `setPredecessors`, `setTaskProgress`, `setNodeTracking`, `moveNodes`, `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo`, `generatePlanningSkeleton`, `getComputedValueDependencies` ;
- `exchanges` : `requestExport`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (0) :

aucune.

## Préalables

EP-04 livré : les tâches vivent dans la structure principale d'une révision en cours.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.3 sont des tests qui passent (WF-QUA-0020) ;
- le planning du plus gros projet du jeu de données de référence s'affiche en grille, en Gantt
  et en arborescence ;
- cinquante saisies de la grille s'annulent puis se rétablissent, et l'annulation d'une
  modification qu'un autre contributeur a reprise est refusée en nommant l'objet ;
- un collage depuis un tableur est prévisualisé, puis crée les tâches collées ;
- l'export de l'arborescence et celui d'une chronologie produisent leurs fichiers ;
- le parcours de bout en bout construit un planning contre le service réel.

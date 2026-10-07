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
l'exclusion du périmètre suivi, la consultation et le journal des imports. Ce premier import
construit la mécanique en deux temps — analyse, compte rendu, confirmation, application en une
transaction, expiration, fichier en transit sur le stockage objet — qu'EP-12 reprend pour les
six autres flux.

L'import des coûts est ici, et non en EP-12, parce qu'une ligne de coût n'existe que par import
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
- l'import des coûts réels (FLX-07), au format de l'annexe B, idempotent sur le couple projet
  et numéro de pièce ;
- l'imputation par élément d'OTP, l'exclusion et la réintégration d'une ligne, la consultation,
  le journal des imports ;
- la mécanique d'import en deux temps, et la purge des fichiers d'import sur le stockage
  objet ;
- les écrans du reste à engager et des coûts réels de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- les imports et exports FLX-01 à FLX-06 — EP-12, qui reprend la mécanique d'ici ;
- les indicateurs de projet, dont l'indice de coût que dégradent les tâches ajoutées — EP-10 ;
- les sauvegardes, second compartiment du stockage objet — EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0070-A` | Formats d’échange Excel | début — close en EP-12 | — |
| `WF-INTF-0080-A` | Contrôle et confirmation des imports Excel | début — close en EP-12 | — |
| `WF-INTF-0140-A` | Import des coûts réels (FLX-07) | entière | — |
| `WF-PLA-0070-A` | Suppression d’une tâche | fin — amorcée en EP-06 | — |
| `WF-DEV-0070-A` | Plan de charge du projet | fin — amorcée en EP-07 | — |
| `WF-RAE-0010-A` | Composition du reste à engager | entière | — |
| `WF-RAE-0020-A` | Indicateurs de reste à engager | entière | — |
| `WF-RAE-0030-A` | Démarrage d’une tâche | entière | — |
| `WF-RAE-0040-A` | Grille de reste à engager | entière | — |
| `WF-RAE-0050-A` | Tâches ajoutées en cours d’exécution | début — close en EP-10 | — |
| `WF-CRE-0010-A` | Attributs d’une ligne de coût | entière | — |
| `WF-CRE-0020-A` | Imputation d’une ligne de coût | entière | — |
| `WF-CRE-0030-A` | Exclusion du périmètre suivi | entière | — |
| `WF-CRE-0040-A` | Consultation des coûts réels | entière | — |
| `WF-CRE-0050-A` | Journal des imports | entière | — |
| `WF-ARC-0100-A` | Import en deux temps | entière | — |
| `WF-DAT-0070-A` | Colonnes d’audit | fin — amorcée en EP-03 | — |
| `WF-DAT-0110-A` | Idempotence garantie par la base | début — close en EP-12 | — |
| `WF-DAT-0120-A` | Contenu et purge du stockage objet | début — close en EP-13 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (12) :

- `revisions` : `setLineRemaining` ;
- `analysis` : `getRemainingIndicators`, `listStartableTasks` ;
- `costs` : `listActualCosts`, `setActualCostTrackedScope`, `listCostImports` ;
- `exchanges` : `uploadFile`, `listImports`, `openImport`, `getImport`, `abandonImport`, `applyImport`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (3) :

- `revisions` : `deleteNode`, `setTaskProgress` ;
- `analysis` : `getProjectWorkload`.

## Préalables

EP-07 livré : le reste à engager part des montants budgétés. Le point ouvert PO-01
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

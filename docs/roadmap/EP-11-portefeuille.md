---
id: EP-11
titre: Voir l'ensemble des projets : valeur, charge, performance, risques, décaissements, santé
statut: à planifier
depend_de: EP-10
issue:
---

# EP-11 — Portefeuille

## Objet

Les vues du portefeuille (FBS-2), en consultation seule, calculées sur un périmètre et à une
date : la liste des projets, la valeur et le pipeline pondéré, le plan de charge agrégé, les
indices et projections, la structure des coûts, les risques, les décaissements et la santé du
pilotage. Une grandeur de portefeuille est une somme, un indice un rapport de sommes — jamais
une moyenne d'indices —, et un projet en chiffrage compte au prorata de sa probabilité de gain.

C'est le dernier calcul. Deux exigences d'EP-01 s'y closent donc : chaque exemple chiffré du
document a son test (WF-QUA-0020), et la « seule implémentation » de chaque calcul se constate
sur un dépôt qui les porte tous (WF-ARC-0010).

## Ce qui en fait partie

- le périmètre choisi — projets en cours, en chiffrage, terminés d'une période — et la date de
  calcul ;
- à une date passée, la lecture des indicateurs conservés, sans rien recalculer ;
- la règle d'agrégation et la pondération par la probabilité de gain ;
- les vues de FBS-2.1 à FBS-2.7, et le filtre par nœud d'organisation ;
- la santé du pilotage, avec le délai maximal entre deux revues ;
- les usages du manager sur le portefeuille (WF-INTF-0020) ;
- les écrans du portefeuille de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- tout export du portefeuille : aucun flux du tableau ne le prévoit (WF-INTF-0150) ;
- la mesure des temps de réponse sur trois cents projets — EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0020-A` | Usages du manager | fin — amorcée en EP-05 | — |
| `WF-PTF-0010-A` | Périmètre et date de calcul du portefeuille | entière | — |
| `WF-PTF-0020-A` | Règle d’agrégation | entière | — |
| `WF-PTF-0030-A` | Vues en consultation seule | entière | — |
| `WF-PTF-0040-A` | Liste des projets | entière | — |
| `WF-PTF-0050-A` | Valeur du portefeuille | entière | — |
| `WF-PTF-0060-A` | Plan de charge agrégé | entière | — |
| `WF-PTF-0070-A` | Indices et projections du portefeuille | entière | — |
| `WF-PTF-0080-A` | Structure des coûts du portefeuille | entière | — |
| `WF-PTF-0090-A` | Risques du portefeuille | entière | — |
| `WF-PTF-0100-A` | Décaissements du portefeuille | entière | — |
| `WF-PTF-0110-A` | Santé du pilotage | entière | — |
| `WF-REF-0180-A` | Délai maximal entre deux revues | fin — amorcée en EP-05 | — |
| `WF-PRJ-0090-A` | Probabilité de gain | fin — amorcée en EP-04 | — |
| `WF-ARC-0010-A` | Un noyau, un service, un worker | fin — amorcée en EP-01 | — |
| `WF-QUA-0020-A` | Les exemples chiffrés du document sont des cas de test | fin — amorcée en EP-01 | — |
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | entière | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (8) :

- `portfolio` : `getPortfolioProjects`, `getPortfolioValue`, `getPortfolioWorkload`, `getPortfolioPerformance`, `getPortfolioCostStructure`, `getPortfolioRisks`, `getPortfolioCashOut`, `getPortfolioPilotHealth`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (4) :

- `reference` : `getReferenceSettings` ;
- `projects` : `listProjects`, `updateProject`, `listProjectStateTransitions`.

## Préalables

EP-10 livré : le portefeuille agrège les indicateurs, conservés ou calculés.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.3 et de WF-PRJ-0090 sont des tests qui passent ;
- le rapport de couverture des exigences ne laisse aucun exemple chiffré du document sans son
  test (WF-QUA-0020) ;
- un portefeuille calculé à une date passée ne change pas quand une révision est marquée
  après cette date ;
- le parcours de bout en bout ouvre chacune des vues du portefeuille, contre le service réel.

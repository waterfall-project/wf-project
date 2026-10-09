---
id: EP-07
titre: Chiffrer un projet sur ses tâches, et le faire passer En cours
statut: à planifier
depend_de: EP-06
famille: front, back
issue:
---

# EP-07 — Chiffrage et devis

## Objet

Les lignes de devis portées par les tâches, leur montant calculé des taux horaires et de
l'année de consommation, l'inflation du projet, les indicateurs de devis, la grille de devis, le
plan de charge calculé sur le devis, la mise à jour des taux à la création d'une révision, la
comparaison de deux révisions et la proposition des contributeurs ; l'import et l'export du devis
au format Excel de l'annexe B (FLX-03, FLX-04), dont l'aller-retour se valide ici (revue de la
ventilation, 2026-10-09 : EP-12 abandonné).

Avec des tâches et des lignes, une référence complète peut être désignée : le passage à En cours
(WF-CYC-0030) devient constatable, et avec lui les exigences du référentiel qui ne se vérifient
que sur des montants — conservation des valeurs dans une révision, désactivation et
modification sans effet rétroactif.

## Ce qui en fait partie

- les attributs d'une ligne, le calcul de son montant, son année de consommation, et le refus de
  calculer sans taux pour l'année de référence ;
- le taux d'inflation du projet et ses effets sur la révision en cours ;
- les indicateurs de devis et la grille de devis ;
- le plan de charge du projet, calculé sur le devis d'une révision ;
- la mise à jour des taux proposée à la création d'une révision ;
- la comparaison de deux révisions, sur l'identité de lignée ;
- la proposition des contributeurs d'après les rôles employés ;
- le passage à En cours et l'exigence du code projet ;
- la valeur planifiée, calculée sur la révision de référence ;
- l'import et l'export du devis (FLX-03, FLX-04), leur format versionné et indépendant de la
  langue, leur idempotence, sur la mécanique d'import d'EP-06 ;
- les écrans du devis de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- la réestimation et le reste à engager, et le plan de charge calculé sur lui — EP-09 ;
- les provisions des risques, qui entrent au devis sans entrer au budget de référence — EP-08 ;
- la valeur planifiée recalculée sur la référence produite par un avenant — EP-08 ;
- l'import et l'export du reste à engager et des coûts réels — EP-09.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-CYC-0020-A` | Progression automatique | fin — amorcée en EP-04 | — |
| `WF-CYC-0030-A` | Conditions du passage à En cours | fin — amorcée en EP-04 | — |
| `WF-CYC-0050-A` | Conditions de progression consultables | fin — amorcée en EP-04 | — |
| `WF-REF-0020-A` | Désactivation sans effet sur les projets | fin — amorcée en EP-05 | — |
| `WF-REF-0130-A` | Modification sans effet rétroactif | fin — amorcée en EP-05 | — |
| `WF-REF-0140-A` | Devise de l’installation | fin — amorcée en EP-05 | — |
| `WF-REV-0030-A` | Contenu de l’instantané | fin — amorcée en EP-04 | — |
| `WF-REV-0060-A` | Mise à jour des taux à la création d’une révision | entière | — |
| `WF-REV-0080-A` | Comparaison de deux révisions | entière | — |
| `WF-PRJ-0010-A` | Code projet | fin — amorcée en EP-04 | — |
| `WF-PRJ-0040-A` | Taux d’inflation du projet | entière | — |
| `WF-PRJ-0070-A` | Proposition des contributeurs | entière | — |
| `WF-DEV-0010-A` | Taux horaires requis pour le calcul à la création d’un chiffrage | entière | — |
| `WF-DEV-0020-A` | Attributs d’une ligne de devis | entière | — |
| `WF-DEV-0060-A` | Indicateurs de devis | entière | — |
| `WF-DEV-0050-A` | Grille de devis | entière | — |
| `WF-DEV-0030-A` | Calcul du montant d’une ligne | entière | — |
| `WF-DEV-0040-A` | Année de consommation d’une ligne | entière | — |
| `WF-DEV-0080-A` | Valeur planifiée | début — close en EP-08 | — |
| `WF-DEV-0070-A` | Plan de charge du projet | début — close en EP-09 | — |
| `WF-DAT-0090-A` | Intégrité déclarée en base | fin — amorcée en EP-03 | — |
| `WF-DAT-0100-A` | Types des grandeurs | fin — amorcée en EP-03 | — |
| `WF-IHM-0060-A` | Lecture d'une grille | fin — amorcée en EP-02, EP-03 | — |
| `WF-INTF-0070-A` | Formats d’échange Excel | début — close en EP-09 | — |
| `WF-INTF-0080-A` | Contrôle et confirmation des imports Excel | fin — amorcée en EP-06 | — |
| `WF-INTF-0090-A` | Imports et révisions marquées | fin — amorcée en EP-06 | — |
| `WF-INTF-0100-A` | Import du devis (FLX-03) | entière | — |
| `WF-INTF-0110-A` | Export du devis (FLX-04) | entière | — |
| `WF-INTF-0180-A` | Formats indépendants de la langue | fin — amorcée en EP-02 | — |
| `WF-DAT-0110-A` | Idempotence garantie par la base | début — close en EP-09 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (8) :

- `projects` : `listContributorSuggestions` ;
- `revisions` : `getRateUpdateProposal`, `applyRateUpdate`, `compareRevisions`, `updateEstimateLine` ;
- `analysis` : `getEstimateIndicators`, `getMissingRates`, `getProjectWorkload`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (24) :

- `reference` : `getReferenceSettings`, `updateReferenceSettings`, `updateOrgNode`, `updateResourceRole`, `setResourceRoleActivation`, `updateCalendar`, `setCostTypeActivation`, `updateCostCategory`, `setCostCategoryActivation`, `setHourlyRate` ;
- `projects` : `getProject`, `updateProject`, `getProjectNextState` ;
- `revisions` : `createRevision`, `getRevision`, `designateReferenceRevision`, `listNodes`, `getComputedValueDependencies` — les montants et ce dont ils dépendent ;
- `exchanges` : `uploadFile`, `openImport`, `getImport`, `abandonImport`, `applyImport`, `requestExport` — le devis.

## Préalables

EP-06 livré : une ligne de devis est portée par une tâche.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.4, de WF-PRJ-0040 et de WF-REV-0060 sont des tests
  qui passent (WF-QUA-0020) ;
- un projet passe à En cours dès que sa référence porte une tâche, une ligne et un code projet,
  et la condition manquante est nommée tant qu'il n'y passe pas ;
- la correction d'un taux et la désactivation d'une catégorie laissent inchangés les montants
  d'une révision marquée ;
- la somme des montants d'une révision ne dépend pas de l'ordre de sommation ;
- le parcours de bout en bout chiffre un projet et le fait passer En cours, contre le service
  réel.

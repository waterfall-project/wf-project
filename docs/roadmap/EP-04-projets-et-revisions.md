---
id: EP-04
titre: Créer un projet, en figer des versions, et le mener d'un état à l'autre
statut: à planifier
depend_de: EP-05
famille: front, back
issue:
---

# EP-04 — Projets, révisions et cycle de vie

## Objet

Les projets et leurs attributs, le lotissement, les sous-projets et les contributeurs ; les
révisions — la révision en cours, le marquage, l'historique — avec la copie complète,
l'immuabilité garantie par la base et le partitionnement par projet ; le cycle de vie, ses six
états, ses sorties et leur datation. Le marquage est le premier traitement lourd confié au
worker.

Toute donnée d'un projet vit dans une révision : planning, devis, risques, reste à engager. La
mécanique des révisions se pose donc avant qu'il y ait quoi que ce soit à y mettre, et c'est ici
que se fixe le schéma dont le §4.4.2 a fait le choix le plus coûteux du modèle. Des deux
passages automatiques du cycle de vie, le premier — vers Chiffrage — se constate ici ; le second
demande une référence qui porte des tâches et des lignes, et se clôt en EP-07.

## Ce qui en fait partie

- la création d'un projet, refusée tant que le référentiel est incomplet ; ses attributs, son
  code, son lotissement, ses sous-projets ;
- la liste des contributeurs, et l'évaluation complète d'une action : permission et qualité de
  contributeur ;
- la révision en cours et son abandon, le marquage confié au worker, l'historique et les
  attributs des révisions ;
- la copie complète, l'immuabilité par la base, l'identité de lignée, le partitionnement ;
- la structure de coûts principale de chaque révision, encore vide ;
- la désignation de la révision de référence parmi les révisions marquées ;
- le cycle de vie : les six états, le passage à Chiffrage, les sorties, leur confirmation et
  leur datation, la lecture seule et la consultation des projets terminaux ;
- l'autorité du serveur sur les révisions marquées, les projets terminaux et les
  non-contributeurs ;
- le premier état du jeu de données de référence (WF-QUA-0040), qui grossit ensuite avec chaque
  EPIC ;
- les écrans du projet, des révisions et des contributeurs de la maquette, branchés sur le
  service.

## Ce qui n'en fait pas partie

- les tâches — EP-06 — et les lignes de devis — EP-07 ; les conditions du passage à En cours
  se closent donc en EP-07 ;
- les structures différentielles, les devis propres des risques, et les bornes de la correction
  d'une référence (coût réel reçu, avenant) — EP-08 et EP-09 ;
- la comparaison de deux révisions — EP-07, quand il y a de quoi comparer ;
- les indicateurs conservés au marquage — EP-10 : ici, le marquage prévoit leur place et la
  transaction qui les écrira ;
- la probabilité de gain : saisie ici, employée par le portefeuille — EP-11.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-CYC-0120-A` | Référentiel minimal requis pour créer un projet | entière | — |
| `WF-CYC-0010-A` | États du cycle de vie | entière | — |
| `WF-CYC-0020-A` | Progression automatique | début — close en EP-07 | — |
| `WF-CYC-0030-A` | Conditions du passage à En cours | début — close en EP-07 | — |
| `WF-CYC-0050-A` | Conditions de progression consultables | début — close en EP-07 | — |
| `WF-CYC-0060-A` | Sorties manuelles | entière | — |
| `WF-CYC-0080-A` | Irréversibilité des états terminaux | entière | — |
| `WF-CYC-0090-A` | Confirmation des sorties | entière | — |
| `WF-CYC-0100-A` | Lecture seule des projets terminaux | entière | — |
| `WF-CYC-0110-A` | Consultation des projets terminaux | entière | — |
| `WF-CYC-0130-A` | Datation des transitions | entière | — |
| `WF-ADM-0110-A` | Évaluation d’une action | fin — amorcée en EP-03 | — |
| `WF-REV-0010-A` | Unicité de la révision en cours | entière | — |
| `WF-REV-0020-A` | Marquage d’une révision | entière | — |
| `WF-REV-0030-A` | Contenu de l’instantané | début — close en EP-07 | — |
| `WF-REV-0040-A` | Désignation de la révision de référence | début — close en EP-08 | — |
| `WF-REV-0070-A` | Historique des révisions | entière | — |
| `WF-REV-0090-A` | Attributs d’une révision | entière | — |
| `WF-REV-0100-A` | Structures de coûts d'une révision | début — close en EP-08 | — |
| `WF-PRJ-0010-A` | Code projet | début — close en EP-07 | — |
| `WF-PRJ-0080-A` | Attributs d’un projet | entière | — |
| `WF-PRJ-0020-A` | Lotissement | entière | — |
| `WF-PRJ-0050-A` | Sous-projets | entière | — |
| `WF-PRJ-0060-A` | Liste des contributeurs | entière | — |
| `WF-PRJ-0090-A` | Probabilité de gain | début — close en EP-11 | — |
| `WF-ARC-0070-A` | Autorité du serveur | début — close en EP-10 | — |
| `WF-DAT-0060-A` | Identifiants | fin — amorcée en EP-03 | — |
| `WF-DAT-0080-A` | Régimes de suppression | fin — amorcée en EP-03 | — |
| `WF-DAT-0010-A` | Copie complète des révisions | entière | — |
| `WF-DAT-0020-A` | Immuabilité garantie par la base | entière | — |
| `WF-DAT-0030-A` | Identité de lignée des objets d’une révision | début — close en EP-10 | — |
| `WF-DAT-0040-A` | Conservation des indicateurs des révisions marquées | début — close en EP-10 | — |
| `WF-DAT-0050-A` | Partitionnement par projet | entière | — |
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | fin — amorcée en EP-03, EP-05 | — |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13 | — |
| `WF-IHM-0080-A` | Traitements longs | fin — amorcée en EP-02 | — |
| `WF-ADM-0040-A` | Préférences d’affichage | fin — amorcée en EP-02, EP-03 | — |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | fin — amorcée en EP-03 | — |
| `WF-ADM-0070-A` | Lecture des comptes du fournisseur d’identité | fin — amorcée en EP-03 | — |
| `WF-IHM-0120-A` | Écran d’accueil | entière | — |
| `WF-ADM-0160-A` | Restauration | fin — amorcée en EP-03 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (23) :

- `reference` : `getReferenceReadiness` ;
- `projects` : `listProjects`, `createProject`, `getProject`, `updateProject`, `listProjectStateTransitions`, `getProjectNextState`, `exitProject`, `getWorkBreakdown`, `setWorkBreakdown`, `listSubprojects`, `createSubproject`, `updateSubproject`, `deleteSubproject`, `listContributors`, `setContributors` ;
- `revisions` : `listRevisions`, `createRevision`, `getRevision`, `abandonRevision`, `markRevision`, `designateReferenceRevision`, `listCostStructures`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (0) :

aucune.

## Préalables

EP-05 livré : la création d'un projet exige un référentiel complet.

## Définition de fini

- un projet se crée sur une plateforme au référentiel complet, et le refus nomme chaque
  prérequis manquant sur une plateforme neuve ;
- une révision marquée résiste à une modification par l'API comme par une requête directe en
  base ;
- le marquage s'exécute dans le worker, et l'arrêt du worker pendant la tâche laisse la base
  inchangée ;
- un utilisateur habilité mais non contributeur consulte un projet sans pouvoir le modifier ;
- un projet sort vers chacun des états terminaux permis et n'y est plus modifiable ;
- un jeu de données engendré, sans aucune donnée réelle, charge des projets et des révisions
  marquées sur la plateforme de développement ;
- le parcours de bout en bout crée un projet, marque une révision et le fait sortir, contre le
  service réel.

## Constats reçus

- #754 [EP-03] la consultation d'un projet ne se décidera pas par `require(permission)` seule —
  relevé par la revue d'US-0390 : `require` rend 404 pour une permission de consultation
  absente et 403 pour toute autre, la consultation se reconnaissant au suffixe `.read`
  (`backend/src/waterfall/core/access_roles/evaluation.py`). Exact pour le catalogue d'EP-03,
  mais `all_projects_read` donnerait 403 en nommant la permission, alors que WF-ADM-0110 veut
  qu'un projet non consultable n'existe pas pour l'appelant, et consulter un projet demande
  la permission et la qualité de contributeur, ou `all_projects_read`. EP-04, qui ajoute la
  qualité de contributeur à l'évaluation, décide la consultation d'un projet par une règle
  propre, et la règle 404/403 par une propriété déclarée de la permission plutôt que par son
  suffixe. Reporté d'EP-03 le 2026-10-11.
- #870 [EP-03] le nom d'un contributeur anonymisé — relevé par la revue d'US-0360/L2b :
  `Contributor.display_name` et `ContributorSuggestion.display_name` sont des chaînes non nulles
  au contrat, et un compte désactivé reste listé comme contributeur ; anonymisé, le contrat
  obligerait le service à rendre son nom (contre WF-ADM-0060-A) ou une phrase (contre
  WF-ARC-0110). EP-04, qui sert les contributeurs, rend ces deux champs nullables comme
  `ActorRef.display_name`, et le front les nomme par `useAccountNaming`, avec un exemple de
  contributeur anonymisé et le test de la branche nulle d'`Actor` (`project-tables.tsx`).
  Reporté d'EP-03 le 2026-10-11.

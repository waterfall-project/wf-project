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
- sa tranche du jeu de données de référence (WF-QUA-0040) — projets, révisions, contributeurs,
  sous-projets —, chargée après celle du référentiel (EP-05, #1402), et qui grossit ensuite avec
  chaque EPIC ;
- les écrans du projet, des révisions et des contributeurs de la maquette, branchés sur le
  service ;
- les parcours du projet écrits sur le faux back, rejoués contre le service, le témoin chargé aux
  instants de sa chronologie, pour ce qu'un projet en chiffrage et des révisions vides laissent
  lire (#1350).

## Ce qui n'en fait pas partie

- les tâches — EP-06 — et les lignes de devis — EP-07 ; les conditions du passage à En cours
  se closent donc en EP-07 ;
- les structures différentielles, les devis propres des risques, et les bornes de la correction
  d'une référence (coût réel reçu, avenant) — EP-08 et EP-09 ;
- la comparaison de deux révisions — EP-07, quand il y a de quoi comparer ;
- les indicateurs conservés au marquage — EP-10 : ici, le marquage prévoit leur place et la
  transaction qui les écrira ;
- la probabilité de gain : saisie ici, employée par le portefeuille — EP-11.
- les tables images d'une révision (`revision_role`, `revision_calendar`, `revision_category`,
  `revision_rate`), que seules des lignes remplissent — EP-07, avec la copie qu'elles demandent
  (décision de l'auteur du 2026-10-28) ;
- le passage En cours du projet témoin : la désignation de la référence exige des tâches et des
  lignes (WF-CYC-0030), et le chargeur ne contourne aucune règle — EP-07 ;
- #870, le nom d'un contributeur anonymisé, une modification du contrat — rendu à EP-16, avant le
  gel (décision de l'auteur du 2026-10-28) ; #1363 et #1369, les structures que crée un avenant ou
  un risque — EP-08.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
Dix-sept exigences que le fichier disait entières ou closes ici ont une phrase de Vérif qui
demande des tâches, des lignes de devis, un devis exporté, un import, des indicateurs, le
portefeuille ou les volumes du §4.6.2 : elles se commencent ici et se closent en EP-06, EP-07,
EP-09, EP-10, EP-11 ou EP-13 (décision de l'auteur du 2026-10-28, au cadrage). Chaque US cite
les exigences dont une phrase de Vérif tient avec un projet, ses révisions vides et son cycle ;
les phrases qui demandent plus sont des écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-ADM-0110-A` | Évaluation d’une action | début — close en EP-06, amorcée aussi en EP-03 | US-0910 |
| `WF-DAT-0060-A` | Identifiants | fin — amorcée en EP-03 | US-0910 |
| `WF-DAT-0050-A` | Partitionnement par projet | début — close en EP-13 | US-0910 |
| `WF-ARC-0070-A` | Autorité du serveur | début — close en EP-10 | US-0910 |
| `WF-CYC-0120-A` | Référentiel minimal requis pour créer un projet | fin — amorcée en EP-05 | US-0920 |
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-07, amorcée aussi en EP-03, EP-05, EP-16 | US-0920 |
| `WF-PRJ-0080-A` | Attributs d’un projet | début — close en EP-07, amorcée aussi en EP-16 | US-0920 |
| `WF-PRJ-0010-A` | Code projet | début — close en EP-07 | US-0920 |
| `WF-PRJ-0090-A` | Probabilité de gain | début — close en EP-11 | US-0920 |
| `WF-IHM-0120-A` | Écran d’accueil | entière | US-0920 |
| `WF-CYC-0010-A` | États du cycle de vie | entière | US-0920 |
| `WF-PRJ-0060-A` | Liste des contributeurs | début — close en EP-07 | US-0930 |
| `WF-ADM-0070-A` | Lecture des comptes du fournisseur d’identité | fin — amorcée en EP-03 | US-0930 |
| `WF-PRJ-0050-A` | Sous-projets | début — close en EP-09, amorcée aussi en EP-15, EP-16 | US-0940 |
| `WF-DAT-0080-A` | Régimes de suppression | début — close en EP-07, amorcée aussi en EP-03 | US-0940 |
| `WF-PRJ-0020-A` | Lotissement | fin — amorcée en EP-15 | US-0950 |
| `WF-REV-0010-A` | Unicité de la révision en cours | début — close en EP-07, amorcée aussi en EP-15 | US-0960 |
| `WF-REV-0070-A` | Historique des révisions | début — close en EP-07 | US-0960 |
| `WF-REV-0090-A` | Attributs d’une révision | entière | US-0960 |
| `WF-REV-0100-A` | Structures de coûts d'une révision | début — close en EP-08, amorcée aussi en EP-15 | US-0960 |
| `WF-DAT-0010-A` | Copie complète des révisions | début — close en EP-07 | US-0960 |
| `WF-REV-0030-A` | Contenu de l’instantané | début — close en EP-07 | US-0960 |
| `WF-REV-0020-A` | Marquage d’une révision | début — close en EP-07 | US-0970 |
| `WF-DAT-0020-A` | Immuabilité garantie par la base | début — close en EP-07 | US-0970 |
| `WF-DAT-0040-A` | Conservation des indicateurs des révisions marquées | début — close en EP-10 | US-0970 |
| `WF-DAT-0030-A` | Identité de lignée des objets d’une révision | début — close en EP-10 | US-0970 |
| `WF-IHM-0080-A` | Traitements longs | début — close en EP-09, amorcée aussi en EP-02, EP-15 | US-0970 |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | fin — amorcée en EP-03 | US-0970 |
| `WF-ADM-0160-A` | Restauration | fin — amorcée en EP-03 | US-0970 |
| `WF-CYC-0020-A` | Progression automatique | début — close en EP-07 | US-0980 |
| `WF-CYC-0030-A` | Conditions du passage à En cours | début — close en EP-07, amorcée aussi en EP-15 | US-0980 |
| `WF-CYC-0050-A` | Conditions de progression consultables | début — close en EP-07 | US-0980 |
| `WF-CYC-0060-A` | Sorties manuelles | entière | US-0980 |
| `WF-CYC-0080-A` | Irréversibilité des états terminaux | entière | US-0980 |
| `WF-CYC-0090-A` | Confirmation des sorties | début — close en EP-10 | US-0980 |
| `WF-CYC-0100-A` | Lecture seule des projets terminaux | début — close en EP-09 | US-0980 |
| `WF-CYC-0110-A` | Consultation des projets terminaux | début — close en EP-09 | US-0980 |
| `WF-CYC-0130-A` | Datation des transitions | début — close en EP-11 | US-0980 |
| `WF-REV-0040-A` | Désignation de la révision de référence | début — close en EP-08, amorcée aussi en EP-15 | US-0980 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05 | US-0990 |
| `WF-ADM-0040-A` | Préférences d’affichage | fin — amorcée en EP-02, EP-03 | US-1000 |

## Opérations du contrat

Servies ici pour la première fois, les vingt-trois du fichier — dans l'état du contrat
d'`epic/EP-16` au 2026-10-28, aucune ajoutée ni modifiée ; la liste se relit au gel
(« Préalables ») — et une de plus, `listContributorSuggestions`, que l'écran des contributeurs
lit et que le service rend vide tant qu'aucune ligne de devis n'emploie un rôle (WF-PRJ-0070,
EP-07) :

- `projects` : `listProjects`, `createProject`, `getProject`, `updateProject` (US-0920) ;
  `listContributors`, `setContributors`, `listContributorSuggestions` (US-0930) ;
  `listSubprojects`, `createSubproject`, `updateSubproject`, `deleteSubproject` (US-0940) ;
  `getWorkBreakdown`, `setWorkBreakdown` (US-0950) ; `getProjectNextState`, `exitProject`,
  `listProjectStateTransitions` (US-0980) ;
- `revisions` : `listRevisions`, `createRevision`, `getRevision`, `abandonRevision`,
  `listCostStructures` (US-0960) ; `markRevision` (US-0970) ; `designateReferenceRevision`
  (US-0980) ;
- `reference` : `getReferenceReadiness`, servie par EP-05, dont la création d'un projet lit les
  quatre questions (US-0920).

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute : `listAuditFacets` (le code et le
libellé du jour d'un projet, #927, US-0920) ; `getBackgroundTask` et `listBackgroundTasks` (la
tâche de marquage, US-0970).

## Préalables

EP-05 livré : la création d'un projet exige un référentiel complet, le chargeur du témoin et la
fixture des parcours à deux modes existent. EP-16 livré, le contrat figé en 1.0.0 ; le cadrage
du 2026-10-28 s'est fait sur le contrat d'`epic/EP-16` avant le gel, et #870, une modification
du contrat, y est rendu (« Constats reçus ») : la liste des opérations et des refus se relit au
gel, et un écart devient une « Interface contract issue » que l'auteur tranche.

## Définition de fini

- un projet se crée sur une plateforme au référentiel complet, et le refus nomme chaque
  prérequis manquant sur une plateforme neuve ;
- une révision marquée résiste à une modification par l'API comme par une requête directe en
  base, sur les tables que cet EPIC crée ;
- le marquage s'exécute dans le worker, et l'arrêt du worker pendant la tâche laisse la base
  inchangée ;
- un utilisateur habilité mais non contributeur consulte un projet sans pouvoir le modifier, et
  un projet qu'il ne peut pas consulter n'existe pas pour lui ;
- un projet sort vers chacun des états terminaux permis et n'y est plus modifiable ;
- chaque table révisionnée est partitionnée par projet, et le plan d'exécution d'une lecture de
  révision ne parcourt que la partition du projet ;
- la tranche des projets de l'univers témoin se charge sur une plateforme qui porte celle du
  référentiel, aux instants de sa chronologie, aussi loin que les règles le permettent sans
  tâche ni ligne, et deux chargements donnent les mêmes identifiants ;
- les parcours du projet, des révisions, des contributeurs, des sous-projets et du lotissement
  passent contre le service, le témoin chargé, pour ce qu'un projet en chiffrage et des
  révisions vides laissent lire ; ce qui attend EP-07 est listé dans le guide ;
- les écrans du projet ne portent plus l'avis de la maquette, et l'accueil se rend connecté
  contre le service ;
- `make check` passe sur la branche de l'EPIC, les tests du back citent leurs exigences, et aucun
  fichier de `docs/api` ne change hors d'une « Interface contract issue » tranchée.

## Constats reçus

- #1337, pour #1304, points 2 et 6 — le service de la reprise de la spécification du 2026-10-22 (#1306, C-371 à C-375 ; #1304), dont EP-16 écrit le contrat, le faux back et les écrans (décision de l'auteur du 2026-10-22, au cadrage d'EP-16) :
  - le client d'un projet, facultatif, saisissable à tout moment, exigé par aucune transition
    (WF-PRJ-0080) : la colonne et sa migration ;
  - le code d'un sous-projet borné aux règles d'un nom d'onglet : 31 caractères au plus, sans
    `: \ / ? * [ ]`, ni « Synthèse » ni « Hors sous-projet » (WF-PRJ-0050, D-7). Il faut sa
    validation, et vérifier les données existantes avant la migration.
- #513, #524 — les commandes d'écriture du projet dans la maquette, sur décision de l'auteur du
  2026-10-08 (EP-02/L44), une entorse assumée au cadrage qui laissait les formulaires du projet à
  cet EPIC. EP-02/L44a (#583) fait le projet lui-même : « Créer un projet » sur l'accueil, à la
  session qui porte la permission de le créer et tant que le référentiel minimal est complet
  (`createProject`) ; l'identité et les faits du projet modifiés sur ses paramètres comme il liste
  sa commande `update` (`updateProject`), la probabilité de gain figée à partir de En cours ; le
  prochain état, son déclencheur et ses conditions restantes au cycle de vie
  (`getProjectNextState`), dont la sortie était déjà confirmée. Un succès remplace ce qui est
  affiché par ce que le serveur rend, un refus se dit au champ ou sous le formulaire, et l'écran dit
  que le faux back ne garde rien. EP-02/L44b (#584) fera les sous-projets et les contributeurs,
  EP-02/L44c (#585) le lotissement et le jalonnement. Restent à EP-04 : le back de ces écritures —
  le créateur inscrit chef de projet et contributeur (WF-PRJ-0060), le refus d'un code déjà porté
  (WF-PRJ-0010), de la probabilité de gain à partir de En cours (WF-PRJ-0090), de toute
  modification d'un projet terminal (WF-CYC-0100), d'une création sur un référentiel incomplet
  (WF-CYC-0120) — et la conformité de leurs réponses au contrat, refus compris, que les « Interface
  contract issue » relevées par EP-02/L44a précisent ; le parcours les éprouvera contre le service
  réel.
- #513, #584 — les commandes des sous-projets et des contributeurs dans la maquette, sur décision de
  l'auteur du 2026-10-08 (EP-02/L44b), une entorse assumée au cadrage qui laissait ces formulaires à
  cet EPIC : la création, la modification et la suppression confirmée d'un sous-projet comme le projet
  liste `update` (`createSubproject`, `updateSubproject`, `deleteSubproject`), la suppression
  présentée indisponible pour un sous-projet qui porte des coûts réels ; la liste des contributeurs
  écrite entière comme il liste `manage_contributors` (`setContributors`), depuis une lecture
  entière, les propositions de `listContributorSuggestions` inscrites sur confirmation. Restent à cet
  EPIC : le back de ces écritures — l'unicité du code d'un sous-projet dans le projet et le refus de
  supprimer un sous-projet qui porte des coûts réels ou qu'une révision marquée cite (WF-PRJ-0050,
  WF-DAT-0080), le refus d'une liste sans chef de projet et le compteur de la liste (WF-PRJ-0060,
  WF-IHM-0110), les propositions tirées des nœuds des rôles du devis (WF-PRJ-0070) — et la conformité
  de leurs réponses au contrat, refus compris, que les « Interface contract issue » relevées par
  EP-02/L44b précisent ; le parcours les éprouvera contre le service réel.
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
- #927 [EP-03] les facettes du journal nomment un projet par sa dernière inscription, non par
  son libellé du jour — relevé par la revue d'US-0410/L2, tour 1 : le contrat veut, pour
  `AuditFacets.projects`, le code et le libellé du jour de chaque projet, et ceux de la dernière
  inscription pour un projet qui n'existe plus ; `journal_projects`
  (`backend/src/waterfall/platform/audit_consultation.py`) rend toujours ceux de la dernière
  inscription, faute de projets. EP-04, avec le module des projets, lit le code et le libellé du
  jour, et teste qu'un projet renommé est nommé sous son libellé du jour. Reporté d'EP-03 le
  2026-10-12.
- #962 [EP-03] l'écran du journal tolère le 404 de `listProjects` — relevé par la revue
  d'US-0410/L2b, tour 1 : `frontend/src/app/admin/audit-log/page.tsx` tolère le 404 de la
  première page de `GET /projects`, que le service ne sert pas encore, et le journal nomme ses
  projets sans lien ; une fois `listProjects` servi, un 404 fautif effacerait en silence tous
  les liens vers les projets. EP-04, qui sert `listProjects`, retire cette tolérance. Reporté
  d'EP-03 le 2026-10-12.
- #1004 [EP-03] avec une session, l'accueil rend « Introuvable » — relevé par EP-03/L1
  (#1001) : l'accueil lit `listProjects` et `getReferenceReadiness`, que le service d'EP-03 ne
  sert pas, et le 404 de ces lectures rend « Introuvable » dans la coquille. EP-04, qui sert
  `listProjects`, rend l'accueil, et un parcours contre le service l'affirme connecté. Reporté
  d'EP-03 le 2026-10-14.

- #1350 — e2e : le cycle complet des révisions ne se joue pas contre un faux back sans état
  (relevé par US-0490/L2, EP-15 ; titre `[EP-15]`, label EP-04) : repris ici, par le parcours du
  cycle contre le service, le témoin chargé, aussi loin que des révisions sans tâche le
  permettent — marquer, abandonner, ouvrir —, le passage En cours attendant EP-07 (décision de
  l'auteur du 2026-10-28, au cadrage ; US-0990).
- #1502 — back : les noms réservés d'un code de sous-projet, comparés après normalisation (espaces,
  Unicode) — relevé par la revue d'US-0610/L1 (EP-16), reporté ici avec #1337 (US-0940).

Rendus ou renvoyés au cadrage du 2026-10-28 (décisions de l'auteur) :

- #870 — contrat : le nom d'un contributeur anonymisé. Rendre `Contributor.display_name` et
  `ContributorSuggestion.display_name` nullables est une modification du contrat, qu'EP-16 fige :
  rendu à EP-16, titre et label `EP-16`, à trancher avant le gel (US-0640/L5) ; EP-04 sert le
  champ tel que le contrat figé le dit, et le front le nomme par `useAccountNaming` (US-0930) ;
- #1363 et #1369 — faux back : l'avenant créé qui ne s'ouvre pas, la structure du risque créé non
  listée (titres `[EP-15]`, label EP-04) : le service des structures différentielles et des devis
  propres est d'EP-08, qui les reçoit — titre `[EP-08]`, label EP-08, listés dans son fichier.

## Conception

À écrire au cadrage.

---

## US-0910 — Le socle du projet : tables, partition, modules et consultation d'un projet

- **statut** : à faire
- **exigences** : `WF-ADM-0110-A`, `WF-DAT-0060-A`, `WF-DAT-0050-A`, `WF-ARC-0070-A`
- **opérations** : aucune en propre ; l'évaluation que toutes les opérations du projet
  partagent
- **issue** :

**En tant que** développeur, **je veux** que les tables du projet et du révisionné existent,
partitionnées par projet, dans deux modules du noyau, et que la consultation d'un projet se
décide par une règle propre — la permission et la qualité de contributeur, ou « consulter tous
les projets » —, **afin que** chaque US suivante n'ait que ses opérations à écrire, et qu'un
projet qu'on ne peut pas consulter n'existe pas pour l'appelant (#754).

**Critères d'acceptation.**

- `WF-ADM-0110-A` — « Un utilisateur sans la permission de consultation ne voit pas le projet,
  même contributeur ; un contributeur sans « consulter tous les projets » ne voit que ses
  projets. » : `getProject` répond 404 à qui ne porte pas `projects.read`, contributeur ou non,
  et à qui la porte sans être contributeur ni porter `all_projects_read` ; `listProjects` ne rend
  que les projets ouvrables ;
- `WF-ADM-0110-A` — « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent
  au même écran. » : le même 404, `NOT_FOUND`, sans paramètre qui distingue ;
- écart : `WF-ADM-0110-A` — « Un utilisateur habilité à modifier le planning et porteur de
  « consulter tous les projets », mais non contributeur d'un projet, voit ce planning et ne peut
  pas le modifier, ni par la grille ni par import. » : le planning est d'EP-06, qui clôt ; ici,
  le même utilisateur voit le projet et se voit refuser ses paramètres, ses sous-projets, son
  lotissement et ses contributeurs par 403, `NOT_CONTRIBUTOR` ;
- écart : `WF-ADM-0110-A` — « Inscrit comme contributeur, il le modifie. » : EP-06 ; ici, inscrit
  chef de projet, il modifie les paramètres ;
- écart : `WF-ADM-0110-A` — « Un utilisateur connaît la liste de ses permissions effectives, et
  elle change immédiatement lorsqu'un de ses rôles est modifié. » : constaté par EP-03 (US-0390) ;
- `WF-DAT-0060-A` — « La modification du code d'un projet ou de l'adresse d'un compte n'affecte
  aucune ligne qui les référence. » : le code d'un projet est une contrainte d'unicité, jamais
  une clé — ses révisions, ses contributeurs et ses sous-projets le référencent par
  identifiant — ; l'adresse d'un compte, constatée par EP-03 ;
- `WF-DAT-0060-A` — « Deux instances des services insérant simultanément ne produisent jamais le
  même identifiant. » : UUID v7 engendrés par le service, constaté par EP-03 ; le chargeur du
  témoin est la seule voie qui en impose un ;
- `WF-DAT-0060-A` — « Un identifiant n'apparaît dans aucune URL sous une forme séquentielle. » :
  les adresses des écrans du projet portent des UUID ;
- `WF-DAT-0050-A` — « Le plan d'exécution d'une lecture de révision ne parcourt que la partition
  du projet. » : `cost_structure`, et chaque table révisionnée que les EPIC suivants créent, est
  partitionnée par liste sur `project_id`, une partition par projet créée avec lui, et un test
  lit le plan (`EXPLAIN`) d'une lecture de révision ;
- écart : `WF-DAT-0050-A` — « La durée de lecture d'une révision est la même sur une plateforme
  d'un projet et sur une plateforme de six cents projets. » : les volumes sont d'EP-13, qui clôt ;
- `WF-ARC-0070-A` — « Un appel direct à l'API qui tente de modifier une révision marquée, un
  projet terminal, ou un projet dont l'utilisateur n'est pas contributeur est refusé, alors même
  que le front n'en propose pas l'action. » : par le service, sur chaque écriture du projet et de
  ses révisions que cet EPIC sert — 403 `NOT_CONTRIBUTOR`, 403 `PROJECT_TERMINAL`, 409
  `STATE_FORBIDS_OPERATION` sur une révision marquée — ; les grilles sont d'EP-06 et d'EP-07 ;
- écart : `WF-ARC-0070-A` — « Un indicateur affiché est identique à celui que l'API renvoie pour
  la même date et le même périmètre. » : les indicateurs sont d'EP-10, qui clôt ;
- propre à l'US : les tables `project`, `project_state_transition`, `contributor`, `subproject`,
  `work_package`, `order_item`, `deliverable`, `revision` et `cost_structure` existent par des
  migrations écrites à la main, leurs contraintes déclarées et éprouvées, les droits du rôle du
  service accordés ; les deux modules `projects` (FBS-4.2 et le cycle de vie, §3.3.2) et
  `revisions` (FBS-4.1) existent avec leur interface, et `make imports-back` les tient ;
- propre à l'US : l'évaluation d'une action (`waterfall.core.access_roles`) reçoit la qualité de
  contributeur, lue par le module des projets, et la règle 404/403 se décide par une propriété
  déclarée de chaque permission, non par son suffixe (#754) ; `all_projects_read` ouvre la
  consultation sans qualité de contributeur ; `test_access_evaluation.py` l'éprouve.

**Notes de réalisation.** La consultation d'un projet est une règle à deux termes (WF-PRJ-0060,
WF-ADM-0110) : la permission de la fonction et la qualité de contributeur, ou `all_projects_read`.
Elle s'écrit une fois, dans une dépendance que chaque route d'un projet déclare, avant la
validation des paramètres, comme `Requires` ; une écriture structurante demande en plus la
qualité de chef de projet. La partition par liste est celle de la conception (« Tables et
migrations »).

**Hors périmètre.** Les grilles et les imports (EP-06, EP-07, EP-09) ; les volumes (EP-13).

---

## US-0920 — Le projet : sa création, ses attributs, la liste des projets et l'accueil

- **statut** : à faire
- **exigences** : `WF-CYC-0120-A`, `WF-EXP-0020-A`, `WF-PRJ-0080-A`, `WF-PRJ-0010-A`,
  `WF-PRJ-0090-A`, `WF-IHM-0120-A`, `WF-CYC-0010-A`
- **opérations** : `listProjects`, `createProject`, `getProject`, `updateProject`,
  `getReferenceReadiness` ; `listAuditFacets` (#927)
- **issue** :

**En tant que** chef de projet, **je veux** créer un projet dès que le référentiel le permet, le
nommer, lui donner son client, son code, sa commande, sa probabilité de gain et son taux
d'inflation, et retrouver mes projets à l'accueil, **afin de** commencer un chiffrage sans
attendre l'administrateur.

**Critères d'acceptation.**

- `WF-CYC-0120-A` — « Sur une plateforme dont le référentiel est incomplet, la création d'un
  projet est refusée, et le refus nomme chaque prérequis manquant. » : 409,
  `REFERENCE_INCOMPLETE`, `params.missing_prerequisites` chaque valeur de
  `ReferenceReadiness.missing`, dans son ordre, lue par l'interface d'EP-05 ; rien n'est écrit ;
- `WF-CYC-0120-A` — « La création aboutit dès que tous les prérequis sont satisfaits. »
- `WF-CYC-0120-A` — « L'énoncé des prérequis manquants à l'accueil relève de WF-IHM-0120. » :
  l'accueil lit `getReferenceReadiness` contre le service et les nomme (ci-dessous) ;
- `WF-CYC-0120-A` — « Sur une installation neuve, dont la seule catégorie est celle des provisions
  pour risques, la création est refusée en nommant la catégorie de main-d'œuvre et le rôle
  manquants. » : contre une plateforme amorcée, `active_cost_category` puis
  `active_resource_role` ;
- `WF-CYC-0120-A` — « Sur un référentiel dont aucune catégorie de type provision pour risques n'est
  active, la création est refusée en nommant ce prérequis. » : `active_provision_category` ;
- `WF-EXP-0020-A` — « La création d'un projet est refusée et nomme les prérequis manquants,
  jusqu'à ce qu'une catégorie de coût de main-d'œuvre et un rôle de ressource aient été saisis. » :
  le même refus, levé par la saisie des deux objets contre le service ;
- écart : `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le
  lien produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles
  prédéfinis et le catalogue des permissions. » : constaté par EP-03 ;
- écart : `WF-EXP-0020-A` — « Une seconde exécution de l'installation ne crée ni compte, ni
  calendrier, ni nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent,
  tant que l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » : constaté
  par EP-03 et EP-05 ;
- écart : `WF-EXP-0020-A` — « Le lien produit à l'installation est accepté plus d'une heure après
  sa production. » : constaté par EP-03 ;
- écart : `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %,
  50 % et 75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines,
  et le calendrier par défaut compte huit heures du lundi au vendredi et aucune le week-end. » :
  constaté par EP-05 ;
- écart : `WF-EXP-0020-A` — « Le nom de l'entreprise saisi à l'installation figure sur un devis
  exporté ; modifié, il figure sur le suivant. » : le devis exporté est d'EP-07, qui clôt ;
- `WF-PRJ-0080-A` — « La création d'un projet sans libellé est refusée. » : 422, `VALUE_REQUIRED`
  sur `/label` ;
- `WF-PRJ-0080-A` — « La date de réception de la commande est saisissable à tout moment et n'est
  exigée par aucune transition. » : `order_received_on`, par `updateProject`, à tout état non
  terminal ; aucune transition ne la lit ;
- `WF-PRJ-0080-A` — « Le nom du client est saisissable à tout moment, n'est exigé par aucune
  transition, et figure sur la présentation d'un devis exporté. » : `client`, saisi et effacé à
  tout état non terminal, exigé par aucune transition (#1337) ; le devis exporté est d'EP-07, qui
  clôt ;
- `WF-PRJ-0010-A` — « Un projet se crée et se chiffre sans code projet. » : la création sans code
  aboutit, `code` nul ; le chiffrage est d'EP-07, qui clôt ;
- `WF-PRJ-0010-A` — « Le projet ne passe pas à En cours tant qu'il n'est pas renseigné, et la
  condition manquante est nommée (WF-CYC-0050). » : `getProjectNextState` nomme `project_code_set`
  parmi les conditions restantes tant que le code est nul (US-0980) ;
- `WF-PRJ-0010-A` — « La saisie d'un code déjà porté par un autre projet est refusée. » : 409,
  `ALREADY_EXISTS` sur `/code`, `conflicting_object_id` et `conflicting_object_label`, à la
  création comme à la modification ; l'unicité est une contrainte de la base ;
- `WF-PRJ-0090-A` — « La modification de la probabilité est refusée à partir de l'état En
  cours. » : 409, `STATE_FORBIDS_OPERATION`, `project_before_in_progress`, que la commande
  `update_win_probability` dit d'avance ; l'état En cours se pose autour du service dans les tests
  tant qu'aucune référence ne porte de tâche (EP-07) ;
- écart : `WF-PRJ-0090-A` — « Une offre à 40 % de probabilité et 100 000 € de devis pèse 40 000 €
  dans le pipeline pondéré et 40 % de sa charge dans le plan de charge agrégé pondéré. » : le
  portefeuille est d'EP-11, qui clôt ;
- écart : `WF-PRJ-0090-A` — « Le devis et les indicateurs du projet lui-même sont identiques à 0 %
  et à 100 %. » : EP-07 et EP-10 ; EP-11 clôt ;
- `WF-IHM-0120-A` — « Un contributeur de deux projets les voit à sa connexion ; la levée du filtre
  montre aussi les projets qu'il peut ouvrir sans en être contributeur, et aucun autre. » :
  `listProjects` avec `is_contributor` vrai, puis levé par une session qui porte
  `all_projects_read`, contre le service ;
- `WF-IHM-0120-A` — « Sur une installation au référentiel incomplet, l'accueil nomme les
  prérequis manquants et mène au référentiel. » : contre le service, l'accueil connecté se rend
  (#1004) et lit `getReferenceReadiness` ;
- `WF-CYC-0010-A` — « Les listes, filtres et en-têtes de projet ne proposent que ces six statuts,
  avec les codes et libellés du tableau des états d'un projet. »
- `WF-CYC-0010-A` — « L'API ne renvoie que ces six codes. » : `state` est une contrainte de
  vérification sur les six valeurs de `ProjectState`, et le projet naît `created` ;
- propre à l'US : `listProjects` cherche sur le libellé et le code, se filtre par `states`
  (sans lui, les projets en cours seuls, `meta.states` disant les états retenus), `is_contributor`,
  `from` et `to` sur `audit.updated_at`, se trie et se pagine comme l'opération le dit ;
  `updateProject` réserve ses champs aux chefs de projet, refuse un projet terminal
  (`project_not_terminal`), un taux d'inflation ou une probabilité hors de 0 à 1 (422), un
  compteur périmé (412) ; le créateur est inscrit chef de projet (US-0930) ;
- propre à l'US : `listAuditFacets` nomme chaque projet qui existe par son code et son libellé du
  jour, et un projet renommé est nommé sous son libellé du jour (#927) ; l'écran du journal ne
  tolère plus le 404 de `listProjects` (#962) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et la
  route de chaque opération déclare ses permissions.

**Notes de réalisation.** Les écrans sont ceux d'EP-02/L44a (#583) et d'EP-16/US-0610 (le
client) ; cette US sert ce que #513 et #524 laissaient à EP-04. La liste des projets filtrée par
défaut (#1401) est d'EP-16. Le refus `REFERENCE_INCOMPLETE` lit les quatre questions de l'interface
d'EP-05 dans la transaction de la création, sous le verrou du référentiel minimal, pour qu'une
désactivation concurrente ne laisse pas naître un projet sans rôle.

**Hors périmètre.** Les transitions (US-0980) ; les contributeurs (US-0930) ; le devis exporté
(EP-07).

---

## US-0930 — Les contributeurs et les chefs de projet

- **statut** : à faire
- **exigences** : `WF-PRJ-0060-A`, `WF-ADM-0070-A`
- **opérations** : `listContributors`, `setContributors`, `listContributorSuggestions`
- **issue** :

**En tant que** chef de projet, **je veux** inscrire les contributeurs de mon projet, en faire
des chefs de projet ou de simples participants, et les retirer, **afin que** chacun consulte et
saisisse ce qu'il doit, et qu'un projet garde toujours un chef.

**Critères d'acceptation.**

- `WF-PRJ-0060-A` — « La liste d'un projet nouvellement créé comporte son créateur, chef de projet,
  qui peut y inscrire d'autres utilisateurs. » : `createProject` inscrit le créateur
  `project_manager`, dans la même transaction ; `setContributors` lui est ouvert ;
- `WF-PRJ-0060-A` — « Un utilisateur habilité à consulter les projets, non contributeur d'un projet
  et sans la permission « consulter tous les projets », ne l'ouvre pas et ne le trouve pas par son
  adresse ; le carnet du portefeuille le compte pourtant. » : 404 par la règle d'US-0910, et
  absent de `listProjects` ; le carnet du portefeuille est d'EP-11, EP-07 constate la clôture ;
- `WF-PRJ-0060-A` — « Inscrit comme participant, il l'ouvre et saisit le devis, mais ne marque pas
  de révision même s'il en porte la permission ; inscrit comme chef de projet, il la marque. » :
  inscrit `contributor`, il ouvre le projet (200) et se voit refuser le marquage par 403,
  `NOT_PROJECT_MANAGER` (US-0970) ; inscrit `project_manager`, il marque ; le devis est d'EP-07,
  qui clôt ;
- `WF-PRJ-0060-A` — « Le retrait du seul chef de projet d'un projet est refusé, de même que son
  passage en participant ; il est accepté dès qu'un second chef de projet est inscrit. » : 409,
  `LAST_PROJECT_MANAGER`, sans paramètre, sous un verrou de la liste ;
- `WF-ADM-0070-A` — « Une personne retirée de l'annuaire voit son compte désactivé à la
  synchronisation suivante, et ses actes restent consultables. » : un contributeur dont le compte
  est désactivé depuis son inscription reste listé, `is_active` faux, et les lignes qu'il a
  écrites gardent son nom ; la synchronisation est constatée par EP-03 ;
- écart : `WF-ADM-0070-A` — « Après lecture, chaque personne de l'annuaire retenue a un compte
  actif dans Waterfall, sans rôle si elle n'en avait pas, avant toute connexion. » : constaté par
  EP-03 (US-0370) ;
- écart : `WF-ADM-0070-A` — « Le dernier compte administrateur, retiré de l'annuaire, reste actif
  et la synchronisation le signale. » : constaté par EP-03 ;
- écart : `WF-ADM-0070-A` — « Un compte local créé depuis Waterfall existe dans le fournisseur
  d'identité. » : constaté par EP-03 ;
- écart : `WF-ADM-0070-A` — « Une personne ajoutée à l'annuaire a un compte dans Waterfall au terme
  de la périodicité choisie, sans intervention. » : constaté par EP-03 ;
- écart : `WF-ADM-0070-A` — « Un compte anonymisé dont la personne figure encore dans l'annuaire
  reste anonymisé après synchronisation, et aucun compte n'est créé à son nom. » : constaté par
  EP-03 ;
- propre à l'US : `setContributors` écrit la liste entière avec son compteur propre
  (`ContributorList.lock_version`, 412 s'il est périmé, 422 s'il est nul) ; un compte que
  l'installation n'a pas est refusé par `UNKNOWN_USER`, un compte désactivé inscrit ou changé de
  qualité par `USER_INACTIVE`, à sa ligne ; réservée aux chefs de projet (403, `NOT_CONTRIBUTOR`
  ou `NOT_PROJECT_MANAGER`), refusée sur un projet terminal ;
- propre à l'US : `listContributors` cherche sur le nom, se filtre par `kinds` et `is_active`,
  se trie comme l'opération le dit, et rend un compteur nul à une lecture filtrée ; un
  contributeur anonymisé est rendu comme le contrat figé le dit, et le front le nomme par
  `useAccountNaming` (#870, rendu à EP-16) ;
- propre à l'US : `listContributorSuggestions` rend les comptes actifs rattachés aux nœuds des
  rôles qu'emploient les lignes du projet, que la liste ne compte pas encore — vide tant
  qu'aucune ligne n'existe (WF-PRJ-0070, EP-07) —, et l'écran les inscrit sur confirmation ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** La qualité de contributeur est lue par l'évaluation d'US-0910 à chaque
requête : une liste réécrite vaut à la requête suivante, sans reconnexion (WF-ADM-0090). Un
compte désactivé reste contributeur et son compte est refusé à chaque requête (WF-ADM-0060) :
la liste ne le retire pas, elle le signale. L'écran est celui d'EP-02/L44b (#584).

**Hors périmètre.** Le portefeuille (EP-11) ; les propositions nourries par des lignes (EP-07).

---

## US-0940 — Les sous-projets

- **statut** : à faire
- **exigences** : `WF-PRJ-0050-A`, `WF-DAT-0080-A`
- **opérations** : `listSubprojects`, `createSubproject`, `updateSubproject`, `deleteSubproject`
- **issue** :

**En tant que** chef de projet, **je veux** déclarer les sous-projets de mon projet sous le code
que l'ERP leur donne, et supprimer ceux que rien ne retient, **afin que** les coûts réels et le
devis se rejoignent à la maille du sous-projet (#1337).

**Critères d'acceptation.**

- `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est
  refusée. » : 409, `ALREADY_EXISTS` sur `/code`, `conflicting_object_id` et
  `conflicting_object_label` ; l'unicité par projet est une contrainte de la base ;
- `WF-PRJ-0050-A` — « La création d'un sous-projet de code « SP/01 », « Synthèse » ou de plus de
  trente et un caractères est refusée. » : 422, `SUBPROJECT_CODE_INVALID` avec
  `forbidden_characters` ou `reserved_name`, `VALUE_TOO_LONG` avec `max_length` à 31, à la
  création comme à la modification ; les noms réservés se comparent sans égard à la casse, après
  normalisation des espaces et de l'Unicode (#1502) ;
- écart : `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. » : le chiffrage est
  d'EP-07 ; ici, un projet se crée et vit sans sous-projet ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet portant des coûts réels est
  refusée. » : les coûts réels sont d'EP-09, qui clôt ; ici, `subproject_without_actual_costs` ne
  manque jamais, et `has_actual_costs` est faux ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet cité par une révision marquée est
  refusée. » : une révision marquée le cite par ses lignes, d'EP-07 ; ici, `subproject_not_cited`
  ne manque jamais ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet que porte une ligne de devis de la
  révision en cours est refusée ; elle aboutit une fois cette ligne passée à un autre
  sous-projet. » : EP-07 ;
- écart : `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d'une ligne d'une tâche démarrée,
  dont le sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d'une
  ligne d'une tâche non démarrée aboutit, comme celui de la ligne de provision d'un risque
  identifié. » : EP-09 ;
- `WF-DAT-0080-A` — « La suppression d'un sous-projet non référencé le retire de la base. » :
  `deleteSubproject`, 204, la ligne disparue ;
- `WF-DAT-0080-A` — « Aucune commande ne supprime physiquement un rôle de ressource, un rôle
  d'habilitation ou un compte. » : constaté par EP-05 et EP-03 ;
- écart : `WF-DAT-0080-A` — « Celle d'un sous-projet que portent des lignes de devis de la révision
  en cours est refusée et nomme ces lignes ; elle aboutit une fois ces lignes passées hors
  sous-projet ou à un autre sous-projet. » : EP-07, qui clôt ; la place de `params.estimate_lines`
  est prévue ;
- écart : `WF-DAT-0080-A` — « Celle d'un sous-projet référencé par une révision marquée est refusée,
  et le sous-projet reste proposé à la saisie. » : EP-07 ;
- écart : `WF-DAT-0080-A` — « Celle d'un poste référencé par une révision marquée le marque
  supprimé : la révision l'affiche toujours, la saisie ne le propose plus. » : le rattachement
  d'une tâche est d'EP-06 ; EP-07 constate (US-0950 prévoit la colonne) ;
- propre à l'US : les trois conditions de `delete` et `project_not_terminal` sont dites d'avance
  par `Subproject.available_commands`, dans l'ordre du contrat, et un refus nomme la première qui
  manque ; la création et la modification suivent la commande `update` du projet (chefs de
  projet, projet non terminal) ; `listSubprojects` cherche, filtre `has_actual_costs` et trie
  comme l'opération le dit, sans page ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et le
  parcours des sous-projets joue contre le service.

**Notes de réalisation.** `subproject` porte `project_id`, `code`, `label`, audit et compteur,
l'unicité sur (`project_id`, `code`) ; `has_actual_costs` et les trois conditions sont des
questions de l'interface qu'EP-07 et EP-09 rempliront, toujours vraies ici. La suppression passe
à nul la désignation d'un risque non identifié (EP-08) : la place est prévue, rien n'est fait.

**Hors périmètre.** Les lignes (EP-07), les coûts réels (EP-09), les risques (EP-08).

---

## US-0950 — Le lotissement

- **statut** : à faire
- **exigences** : `WF-PRJ-0020-A`
- **opérations** : `getWorkBreakdown`, `setWorkBreakdown`
- **issue** :

**En tant que** chef de projet, **je veux** décrire le lotissement de mon projet — lots, postes,
livrables — et le corriger, **afin que** le planning s'y rattache et que le devis se lise par
lot.

**Critères d'acceptation.**

- `WF-PRJ-0020-A` — « Un projet sans lotissement saisi présente un lot, un poste et aucun
  livrable. » : `getWorkBreakdown` d'un projet qui n'a rien saisi rend un lot et un poste qui
  portent le libellé du projet, sans livrable, créés avec le projet ;
- `WF-PRJ-0020-A` — « Un poste peut être créé sans livrable. »
- propre à l'US : `setWorkBreakdown` écrit le lotissement entier avec son compteur (412 périmé,
  422 nul), engendre l'identifiant des éléments nouveaux, refuse un identifiant inconnu
  (`UNKNOWN_WORK_BREAKDOWN_ITEM`) ou envoyé deux fois (`DUPLICATE_WORK_BREAKDOWN_ITEM`), un
  libellé vide ou trop long ; un élément omis est supprimé — un livrable physiquement, un lot ou un
  poste physiquement tant qu'aucune tâche d'une révision marquée ne le porte (EP-06), la colonne
  du marquage supprimé prévue — ; réservé aux chefs de projet, refusé sur un projet terminal et
  pendant un traitement de fond qui écrit dans la révision en cours (`no_background_task_running`,
  US-0970) ;
- propre à l'US : `getWorkBreakdown` cherche sur le libellé et filtre par `kinds`, rend les
  conteneurs des éléments retenus avec `is_match`, et un compteur nul à une lecture filtrée ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et le
  parcours du lotissement (`project-start.spec.ts`, ses étapes sans squelette) joue contre le
  service.

**Notes de réalisation.** Trois tables, `work_package`, `order_item`, `deliverable`, en refus,
chacune avec `position` et `deleted_at` (le marquage supprimé, nul ici) ; `attached_task` est
d'EP-06, rendu nul. L'écran est celui d'EP-02/L44c (#585) et d'EP-14/L44c.

**Hors périmètre.** Le rattachement des tâches et le squelette (EP-06) ; le jalonnement (EP-06).

---

## US-0960 — La révision en cours, son abandon, l'historique et les structures

- **statut** : à faire
- **exigences** : `WF-REV-0010-A`, `WF-REV-0070-A`, `WF-REV-0090-A`, `WF-REV-0100-A`,
  `WF-DAT-0010-A`, `WF-REV-0030-A`
- **opérations** : `listRevisions`, `createRevision`, `getRevision`, `abandonRevision`,
  `listCostStructures`
- **issue** :

**En tant que** chef de projet, **je veux** ouvrir la révision en cours de mon projet, l'abandonner
si elle ne vaut rien, et relire l'historique de ses révisions marquées, **afin que** chaque
version du projet soit une révision, et une seule à la fois.

**Critères d'acceptation.**

- `WF-REV-0010-A` — « La création d'une seconde révision en cours est refusée tant que la première
  n'est pas marquée. » : 409, `CURRENT_REVISION_EXISTS`, sous un verrou du projet ; l'unicité est
  aussi une contrainte de la base (un index unique partiel sur `status = draft`) ;
- `WF-REV-0010-A` — « Après abandon d'une révision en cours, le projet présente les données de la
  dernière révision marquée, et une nouvelle révision peut être créée. » : `current_revision_id`
  nul, la dernière marquée lisible, `createRevision` de nouveau disponible ;
- `WF-REV-0010-A` — « L'abandon de l'unique révision d'un projet en chiffrage le laisse sans
  révision, à l'état Chiffrage, et la création d'une révision y est de nouveau proposée. »
- écart : `WF-REV-0010-A` — « Une révision créée à partir d'une révision marquée porte les mêmes
  tâches et les mêmes lignes ; à année de référence égale, elle porte aussi les mêmes valeurs de
  référentiel ; sinon, elle porte les mêmes rôles, calendriers et catégories, et, pour chaque
  catégorie dont la mise à jour de WF-REV-0060 n'a pas été acceptée, le taux précédent projeté par
  le taux d'inflation du projet jusqu'à la nouvelle année de référence. » : les tâches sont
  d'EP-06, les lignes et les valeurs d'EP-07, qui clôt ; ici, la copie reprend les structures ;
- `WF-REV-0070-A` — « La liste des révisions marquées est accessible depuis le projet, et
  l'ouverture de l'une d'elles affiche son planning, son devis et ses montants tels qu'ils étaient
  au marquage. » : la liste, par `listRevisions`, filtrée par `status` et cherchée ; le planning
  et le devis sont d'EP-06 et d'EP-07, qui clôt ;
- écart : `WF-REV-0070-A` — « L'année de référence, le taux d'inflation et la probabilité de gain
  affichés pour une révision marquée sont ceux conservés à son marquage, même après modification
  de ceux du projet. » : `reference_year` est conservé ici ; le taux et la probabilité conservés
  sont d'EP-07, qui clôt ;
- `WF-REV-0090-A` — « Chacun de ces attributs est présent dans l'historique des révisions. » :
  nom de version, description, état, date de marquage, année de référence, caractère de
  référence ;
- `WF-REV-0090-A` — « Le nom de version et la description sont ceux saisis au marquage, et l'état
  d'une révision marquée ne redevient jamais « en cours ». » : aucune opération ne l'écrit, et une
  contrainte de la base refuse le retour (US-0970) ;
- `WF-REV-0100-A` — « La première révision d'un projet comporte, à sa création, une structure
  principale et aucune autre ; une révision créée à partir d'une révision marquée en reprend
  toutes les structures, différentielles et propres des risques comprises (WF-REV-0010). » : la
  principale, `kind` `main`, créée avec la révision ; les différentiels et les devis propres sont
  d'EP-08, qui clôt ;
- écart : `WF-REV-0100-A` — « Deux structures différentielles coexistent dans une même révision,
  et la fusion de l'une laisse l'autre intacte. » : EP-08 ;
- écart : `WF-REV-0100-A` — « Un risque déclaré ajoute une structure propre, présente dans chaque
  révision marquée postérieure. » : EP-08 ;
- `WF-DAT-0010-A` — « Après marquage d'une révision puis création de la suivante, le nombre de
  lignes de chaque table portant l'identifiant de la nouvelle révision égale celui de la révision
  marquée. » : pour `cost_structure` ici, par la copie ; chaque EPIC suivant ajoute ses tables à
  la même copie, et EP-07 clôt ;
- `WF-DAT-0010-A` — « Une modification dans la révision en cours ne change aucune ligne portant
  l'identifiant d'une révision marquée. »
- `WF-DAT-0010-A` — « L'abandon d'une révision en cours ne laisse aucune ligne portant son
  identifiant. » : la révision et sa structure principale, supprimées physiquement ;
- écart : `WF-REV-0030-A` — « Après désactivation d'un rôle et correction de son taux horaire, une
  révision marquée qui les employait affiche toujours le rôle et les montants d'origine. » : les
  valeurs employées sont d'EP-07, qui clôt ;
- écart : `WF-REV-0030-A` — « La modification du taux d'inflation ou de la probabilité de gain du
  projet laisse inchangées les valeurs conservées par une révision marquée. » : EP-07 ;
- propre à l'US : `createRevision` copie la dernière révision marquée par une fonction de
  l'interface des révisions que chaque EPIC étend table par table, fixe `reference_year` à
  l'année courante, et mène le projet de Créé à Chiffrage (US-0980) ; l'écran lit la mise à jour
  des taux (EP-07) ; `abandonRevision` refuse une révision marquée (409, `revision_draft`) ;
  `listCostStructures` rend la principale avec ses commandes ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et les
  parcours de l'historique et de l'abandon (`revisions.spec.ts`, `revision-cycle.spec.ts` pour sa
  part) jouent contre le service.

**Notes de réalisation.** `revision` porte `project_id` (clé de partition), `status`,
`version_name`, `description`, `marked_at`, `reference_year`, `is_reference`, `lineage_id`,
audit et compteur ; `cost_structure` est la première table révisionnée partitionnée. La copie
est une fonction `copy_revision(session, source, target)` de l'interface, appelée dans la
transaction de la création, qu'EP-06 (tâches, liaisons), EP-07 (lignes, images) et EP-08
(structures) étendent.

**Hors périmètre.** La mise à jour des taux (EP-07) ; les différentiels et les devis propres
(EP-08).

---

## US-0970 — Le marquage par le worker, et l'immuabilité par la base

- **statut** : à faire
- **exigences** : `WF-REV-0020-A`, `WF-DAT-0020-A`, `WF-DAT-0040-A`, `WF-DAT-0030-A`,
  `WF-IHM-0080-A`, `WF-ADM-0060-A`, `WF-ADM-0160-A`
- **opérations** : `markRevision` ; `getBackgroundTask`, `listBackgroundTasks`
- **issue** :

**En tant que** chef de projet, **je veux** marquer la révision en cours sous un nom de version,
dans une tâche de fond qui me laisse l'écran, et savoir qu'une révision marquée ne changera plus,
quel que soit le chemin, **afin que** l'histoire du projet soit sûre.

**Critères d'acceptation.**

- `WF-REV-0020-A` — « Le marquage est refusé tant que le nom de version n'est pas renseigné. » :
  422, `VALUE_REQUIRED` sur `/version_name` ;
- `WF-REV-0020-A` — « Toute tentative de modification d'une révision marquée est refusée, quel que
  soit le point d'entrée. » : par l'API, chaque écriture de la révision et de sa structure que cet
  EPIC sert (409, `revision_draft`) ; par la base, ci-dessous ; les grilles et les imports sont
  d'EP-06, EP-07 et EP-09, EP-07 clôt ;
- `WF-REV-0020-A` — « Le marquage d'une révision sous un nom de version déjà employé dans le projet
  est refusé. » : 409, `ALREADY_EXISTS` sur `/version_name`, `conflicting_object_id` ; l'unicité
  par projet est une contrainte de la base sur les révisions marquées ;
- `WF-DAT-0020-A` — « Une mise à jour ou une suppression exécutée directement en base sur une
  tâche, une ligne de devis ou une valeur de référentiel d'une révision marquée est rejetée par la
  base. » : un déclencheur sur chaque table révisionnée — `cost_structure` ici, chaque EPIC
  suivant y plaçant les siennes — refuse toute mise à jour et toute suppression d'une ligne dont
  la révision est marquée, propriétaire compris, et un déclencheur sur `revision` refuse le retour
  de `marked` à `draft` ; un test écrit la ligne en passant autour du service ; les tâches, les
  lignes et les valeurs sont d'EP-06 et d'EP-07, qui clôt ;
- `WF-DAT-0020-A` — « La désignation d'une révision marquée comme référence aboutit. » : la
  désignation n'écrit que `is_reference` et le projet, ce que le déclencheur admet (US-0980) ;
- écart : `WF-DAT-0020-A` — « La suppression physique d'un sous-projet référencé par une révision
  marquée est rejetée. » : la référence passe par les lignes, d'EP-07 ;
- `WF-DAT-0040-A` — « Le marquage d'une révision échoue entièrement si le calcul de ses indicateurs
  échoue. » : la tâche marque et calcule dans une seule transaction, le calcul étant une fonction
  de l'interface qu'EP-10 remplit — ici, elle ne conserve rien et ne peut pas échouer ; un calcul
  qui lève fait échouer la tâche sans rien écrire, et la révision reste en cours ;
- écart : `WF-DAT-0040-A` — « Aucune vue de portefeuille à une date passée, sur trois cents projets
  — plan de charge agrégé, structure des coûts et risques compris —, ne lit de ligne de tâche ni
  de ligne de devis. » : EP-11, EP-10 clôt ;
- écart : `WF-DAT-0040-A` — « Les indicateurs conservés d'une révision marquée sont identiques
  avant et après un import de coûts réels postérieur. » : EP-10 ;
- écart : `WF-DAT-0040-A` — « Le marquage d'une offre, sur un projet en chiffrage, aboutit et
  conserve le total du devis sans aucun indicateur projet. » : le marquage d'une offre aboutit
  ici ; le total du devis est d'EP-07, EP-10 clôt ;
- écart : `WF-DAT-0040-A` — « La courbe de coût réel d'une révision marquée est identique avant et
  après l'exclusion d'une ligne de coût connue à son marquage. » : EP-10 ;
- écart : `WF-DAT-0030-A` — « Une tâche renommée et déplacée dans la révision en cours est
  rapprochée de la tâche d'origine par la comparaison avec la révision marquée précédente. » :
  les tâches sont d'EP-06, EP-10 clôt ; ici, `cost_structure` porte `lineage_id`, que la copie
  conserve ;
- écart : `WF-DAT-0030-A` — « Un jalon renommé conserve sa courbe sur le diagramme temps/temps. » :
  EP-10 ;
- écart : `WF-DAT-0030-A` — « Deux tâches créées séparément n'ont jamais le même identifiant de
  lignée. » : EP-06 ; ici, la lignée d'une structure créée est son propre identifiant ;
- `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même
  traitement peut être relancé. » : la tâche de marquage échouée porte son motif
  (`BackgroundTask.problem`), et un nouveau `markRevision` la relance ;
- écart : `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran
  utilisable et présente son avancement. » : les objets sont d'EP-06 et d'EP-07 ; ici, le marquage
  répond 202 avec sa tâche, que l'écran suit ; EP-09 clôt ;
- écart : `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de
  son aboutissement. » : les imports sont d'EP-06 à EP-09, qui clôt ;
- `WF-ADM-0060-A` — « Une révision marquée par un compte depuis désactivé affiche toujours son
  auteur. » : `audit.updated_by` de la révision marquée nomme le compte désactivé ;
- `WF-ADM-0060-A` — « Après anonymisation d'un compte désactivé, aucun écran — journal d'audit
  compris — ne présente plus son nom ni son adresse ; les révisions qu'il a marquées affichent le
  libellé neutre comme auteur ; sa réactivation est refusée. » : la révision marquée par un
  compte anonymisé rend un auteur sans nom, que le front montre par le libellé neutre ; le reste,
  constaté par EP-03 ;
- écart : `WF-ADM-0060-A` — « Aucun écran ne propose de supprimer un compte. » : constaté par
  EP-03 ;
- écart : `WF-ADM-0060-A` — « La connexion d'un compte désactivé est refusée. » : constaté par
  EP-03 ;
- écart : `WF-ADM-0060-A` — « Un compte réactivé se connecte de nouveau avec ses rôles d'avant. » :
  constaté par EP-03 ;
- `WF-ADM-0160-A` — « Après restauration d'une sauvegarde, la plateforme présente exactement les
  projets, révisions et comptes qu'elle contenait à la date de la sauvegarde, et rien de
  postérieur, hors le journal d'audit et la liste des sauvegardes, qui gardent leurs inscriptions
  et leurs sauvegardes ; le journal nomme la restauration. » : le parcours de restauration d'EP-03
  crée un projet et marque une révision après la sauvegarde, et ne les retrouve plus ;
- écart : `WF-ADM-0160-A` — « Une tâche de fond en file ou en cours dans la sauvegarde est en échec
  après la restauration. » : constaté par EP-03 ;
- écart : `WF-ADM-0160-A` — « La confirmation nomme la date de la sauvegarde. » : constaté par
  EP-03 ;
- écart : `WF-ADM-0160-A` — « Aucune restauration partielle n'est proposée. » : constaté par EP-03 ;
- écart : `WF-ADM-0160-A` — « Une inscription faite après la sauvegarde est encore présente après
  la restauration, et la dernière inscription est la restauration elle-même. » : constaté par
  EP-03 ;
- propre à l'US : `markRevision` dépose une tâche `revision_mark` (202), réservée aux chefs de
  projet qui portent `revision_mark` ; le worker marque sous un verrou de la révision, inscrit
  `revision_mark` au journal d'audit avec le nom de version, et un worker arrêté pendant la tâche
  laisse la base inchangée ; les commandes qui écriraient dans la révision nomment
  `no_background_task_running` pendant le marquage ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et le
  parcours du marquage (`revision-cycle.spec.ts`, sa part) joue contre le service.

**Notes de réalisation.** Le marquage est le premier traitement du métier confié au worker
(EP-03, « Worker, file et planification ») : un gestionnaire `revision_mark` enregistré dans
`handlers`, qui appelle l'interface des révisions. Les déclencheurs d'immuabilité suivent le
modèle du journal d'audit (`0003_audit_entry`) : une fonction par table, qui lit l'état de la
révision par sa clé, dans le même module.

**Hors périmètre.** Les indicateurs conservés (EP-10) ; les tâches et les lignes (EP-06, EP-07).

---

## US-0980 — La référence et le cycle de vie

- **statut** : à faire
- **exigences** : `WF-CYC-0020-A`, `WF-CYC-0030-A`, `WF-CYC-0050-A`, `WF-CYC-0060-A`,
  `WF-CYC-0080-A`, `WF-CYC-0090-A`, `WF-CYC-0100-A`, `WF-CYC-0110-A`, `WF-CYC-0130-A`,
  `WF-REV-0040-A`
- **opérations** : `designateReferenceRevision`, `getProjectNextState`, `exitProject`,
  `listProjectStateTransitions`
- **issue** :

**En tant que** chef de projet, **je veux** que mon projet avance de lui-même de Créé à Chiffrage
puis à En cours quand ses faits sont là, savoir ce qui lui manque, le sortir du cycle en le
disant, et relire ses transitions datées, **afin que** l'état du projet soit un fait et non une
case à cocher.

**Critères d'acceptation.**

- `WF-CYC-0020-A` — « Aucun écran ne propose de commande menant à Chiffrage ou En cours. » :
  aucune opération ne les écrit ; `exitProject` n'admet que `completed`, `lost`, `abandoned` ;
- `WF-CYC-0020-A` — « Chacun de ces états est atteint dès que son fait déclencheur est réalisé,
  sans autre action. » : Chiffrage à la création de la première révision (`createRevision`,
  `first_revision_created`), dans sa transaction ; En cours à la désignation de la référence et à
  la saisie du code, dans n'importe quel ordre, par la transaction qui réalise le second fait —
  constaté ici par les tests du service, la référence posée autour du service tant qu'aucune
  révision ne porte de tâche ni de ligne (EP-07, qui clôt) ;
- écart : `WF-CYC-0030-A` — « Un projet dont la référence est désignée avant le code projet passe
  à En cours à la saisie du code ; un projet dont le code est saisi avant la désignation y passe à
  la désignation. » : la désignation exige des tâches et des lignes, d'EP-06 et d'EP-07, qui
  clôt ; la mécanique des deux ordres est écrite et éprouvée autour du service ;
- `WF-CYC-0030-A` — « La désignation d'une révision marquée sans tâche, ou sans ligne de devis, est
  refusée et la condition manquante est nommée ; le projet n'a pas de référence. » : 409,
  `STATE_FORBIDS_OPERATION`, `revision_has_tasks_and_lines` — ici toujours manquante, la question
  posée à l'interface qu'EP-06 et EP-07 remplissent —, le projet sans référence ;
- `WF-CYC-0050-A` — « Pour un projet dans chacun des états Créé et Chiffrage, l'utilisateur
  consulte le prochain état, son déclencheur et les conditions restantes, sans avoir tenté
  d'action. » : `getProjectNextState` — `pricing` et `first_revision_created` depuis Créé ;
  `in_progress`, `reference_designated_and_code_set` et les conditions restantes
  (`reference_designated`, `project_code_set`) depuis Chiffrage ; nuls depuis En cours et les
  états terminaux ;
- `WF-CYC-0060-A` — « Pour chaque état non terminal, le menu des sorties ne permet que les sorties
  permises depuis cet état. » : les commandes `complete`, `lose`, `abandon` du projet, listées et
  disponibles selon l'état — Terminé depuis En cours, Perdu depuis Chiffrage, Abandonné depuis
  tout état non terminal —, et `exitProject` refuse une sortie non permise par 409 ;
- `WF-CYC-0060-A` — « Une sortie qui le deviendra dans un état ultérieur — Terminer depuis
  Chiffrage — y est présentée indisponible, avec sa condition (WF-IHM-0090) ; une sortie qui ne le
  deviendra jamais — Déclarer perdu depuis En cours — n'y figure pas. » : `complete` listée
  indisponible en Chiffrage avec `project_in_progress` ; `lose` absente en En cours — l'état posé
  autour du service ;
- `WF-CYC-0080-A` — « Toute tentative de transition depuis Terminé, Perdu ou Abandonné est
  refusée. » : `exitProject` et `createRevision` répondent 403, `PROJECT_TERMINAL`, et aucune
  commande n'est listée disponible ;
- `WF-CYC-0090-A` — « La confirmation nomme l'état visé et le passage en lecture seule du projet et
  de toutes ses données, et propose la saisie d'un motif ; une sortie confirmée sans motif est
  appliquée. » : `ProjectExit` porte `to_state`, `confirmed` et `reason` facultatif ; une sortie
  non confirmée est refusée par 422 ; l'écran d'EP-02/L44a confirme ainsi ;
- `WF-CYC-0090-A` — « La sortie d'un projet qui porte une révision en cours demande de la marquer
  ou de l'abandonner ; après la sortie, le projet n'a plus de révision en cours, et ses
  indicateurs se lisent dans sa dernière révision marquée (WF-IND-0010). » : la sortie d'un
  projet qui porte une révision en cours est refusée par 409, `no_current_revision` manquante,
  que la commande dit d'avance ; après la sortie, `current_revision_id` est nul ; les indicateurs
  sont d'EP-10, qui clôt ;
- `WF-CYC-0100-A` — « Toute modification d'un projet terminal est refusée, qu'elle soit tentée par
  la saisie, par un import Excel ou MS Project, ou par un traitement automatique. » : par la
  saisie, chaque écriture de cet EPIC répond 403, `PROJECT_TERMINAL` ; les imports sont d'EP-06
  à EP-09, qui clôt ;
- `WF-CYC-0110-A` — « Toutes les vues de consultation d'un projet clos s'affichent normalement, et
  ses exports aboutissent. » : les lectures de cet EPIC répondent 200 sur un projet clos ; les
  exports sont d'EP-06 à EP-09, qui clôt ;
- `WF-CYC-0110-A` — « Seules les modifications sont refusées. »
- `WF-CYC-0130-A` — « Après passage d'un projet à En cours puis à Terminé, l'historique présente
  les deux transitions avec leur date. » : `listProjectStateTransitions`, chaque transition
  datée de l'instant de la transaction qui l'a faite, avec son auteur — la plateforme pour une
  transition automatique — ; En cours posé autour du service ;
- `WF-CYC-0130-A` — « Une sortie à Perdu confirmée avec un motif présente ce motif dans
  l'historique ; une transition automatique n'en porte aucun. »
- écart : `WF-CYC-0130-A` — « Un projet passé à Perdu le 15 mars compte parmi les offres closes de
  mars et d'aucun autre mois. » : les statistiques du portefeuille sont d'EP-11, qui clôt ;
- `WF-REV-0040-A` — « La désignation manuelle est proposée tant que le projet n'a ni coût réel ni
  révision marquée depuis la dernière désignation, et refusée au-delà. » : la commande
  `designate_reference` d'une révision marquée, `reference_correctable` manquante dès qu'une
  révision a été marquée depuis la dernière désignation, et `REFERENCE_NOT_CORRECTABLE` au
  refus ; les coûts réels sont d'EP-09 ; la désignation elle-même se constate autour du service
  (EP-08 clôt) ;
- écart : `WF-REV-0040-A` — « Un projet dont les offres v2 puis v3 sont marquées, et dont v2 a été
  désignée par erreur, accepte la désignation de v3 tant qu'il n'a reçu aucun coût réel. » :
  EP-09 et EP-08 ;
- écart : `WF-REV-0040-A` — « Après contractualisation d'un avenant, la révision produite est la
  référence sans intervention de l'utilisateur, et l'ancienne reste consultable. » : EP-08 ;
- propre à l'US : `exitProject` est réservée aux chefs de projet, inscrite au journal d'audit
  (`project_exit`, avec l'état et le motif), et écrit la transition, l'état et la date dans la
  même transaction, sous un verrou du projet ; `designateReferenceRevision` l'est de même
  (`reference_designate`) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et le
  parcours du cycle (`projects.spec.ts`, sa sortie ; `revision-cycle.spec.ts`) joue contre le
  service pour ce qu'un projet en chiffrage permet.

**Notes de réalisation.** L'état est une colonne de `project` sous contrainte ; chaque transition
est une ligne de `project_state_transition` (`from_state`, `to_state`, `occurred_at`, `actor`,
`reason`), jamais modifiée. Les conditions des commandes et du prochain état viennent des mêmes
fonctions : `project_code_set`, `reference_designated`, `revision_has_tasks_and_lines` (une
question à l'interface des révisions, fausse jusqu'à EP-07), `no_current_revision`,
`reference_correctable`. Les écrans sont ceux d'EP-02/L44a (le cycle de vie, #583) et d'EP-15
(US-0490, la désignation et l'encart).

**Hors périmètre.** Le passage En cours sur le témoin (EP-07) ; les avenants (EP-08) ; les coûts
réels (EP-09).

---

## US-0990 — Le témoin : la tranche des projets, et les parcours rejoués

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`
- **opérations** : aucune en propre ; le chargement passe par les interfaces du noyau
- **issue** :

**En tant que** développeur, **je veux** charger sur une plateforme qui porte le référentiel du
témoin ses projets, leurs révisions, leurs contributeurs, leurs sous-projets et leur lotissement,
aux instants de sa chronologie, et rejouer contre le service les parcours écrits sur le faux
back, **afin que** les tests déjà écrits prouvent le service (#1402, #1350).

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour la tranche des projets — PRJ-001 et PRJ-002, leurs attributs et leur client,
  les contributeurs du témoin par des comptes locaux de la tranche, leurs sous-projets, le
  lotissement, les révisions 100, 101 et 102 avec leur structure principale et leurs transitions —,
  chargée par `waterfall-api load-witness` après celle du référentiel, par les interfaces, avec les
  identifiants du témoin et l'instant de chaque événement de sa chronologie (décision de l'auteur
  du 2026-10-28) ; aussi loin que les règles le permettent sans tâche ni ligne : l'offre et la
  référence marquées, la désignation refusée faute de tâches, PRJ-001 en Chiffrage, son code
  saisi — le passage En cours et le reste du témoin arrivent avec EP-07 ; les volumes entiers sont
  d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes
  identiques. » : deux plateformes chargées portent les mêmes identifiants, codes, libellés et
  dates ; une seconde exécution sur une plateforme chargée ne crée rien et le dit ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les comptes de la tranche portent des adresses en `waterfall.test`, et les libellés sont ceux du
  témoin, fictifs ;
- propre à l'US : la commande lit `projects.json`, `project.json` (le client), `revisions.json`,
  `project_state_transitions` (la chronologie, par `mockwitness`, exportée par `make mock-data`
  dans un fichier de la tranche), `contributors.json`, `subprojects.json` et `work_breakdown.json`,
  validés par les modèles du contrat ; les comptes des contributeurs — Camille Martin, Dominique
  Bernard, Alix Moreau désactivée, et le quatrième — sont créés dans Waterfall seul, sans
  fournisseur d'identité, par l'interface des comptes, et ne se connectent pas ;
- propre à l'US : les dates du référentiel restent celles du chargement (EP-05) ; celles des
  projets, des révisions et des transitions sont celles de la chronologie, et le README le dit ;
- propre à l'US : les parcours du projet rejoués dans le projet `shared` de Playwright, sans
  réécriture de leurs attendus de lecture pour ce qu'un projet en chiffrage et des révisions vides
  laissent lire — `project-start.spec.ts` (la création, le lotissement), `projects.spec.ts` (la
  liste, les paramètres, les contributeurs, les sous-projets, l'historique des états, la sortie),
  `revisions.spec.ts` et `revision-cycle.spec.ts` (l'historique, l'abandon, le marquage),
  `context.spec.ts` et `navigation.spec.ts` pour leurs lectures du projet — ; ce qui lit PRJ-001 En
  cours, sa référence, ses tâches ou ses lignes se note comme non rejoué jusqu'à EP-07, et la
  liste est dans le guide ; les assertions d'écriture affirment ce qui a été écrit, par
  `inService` ;
- propre à l'US : le parcours du cycle contre le service (#1350) : créer, ouvrir, marquer,
  abandonner, rouvrir, saisir le code, sortir — et constater que la désignation est refusée faute
  de tâches, ce que EP-07 renversera.

**Notes de réalisation.** La chronologie du témoin vit dans `wftools.mockwitness` (`CHRONOLOGY`) :
`make mock-data` l'écrit dans un fichier de la tranche que la commande lit, sans que le back
importe `wftools`. Le chargeur écrit chaque événement à son instant par `Act.at` ; l'auteur est
la plateforme. La révision 101 du témoin naît d'une saisie de risque (EP-08) : ici, elle s'ouvre
par `createRevision` à son instant. Ce que la tranche ne peut pas faire sans EP-06, EP-07 et
EP-08 est écrit dans le guide, et chaque EPIC le reprend.

**Hors périmètre.** Les tâches, les lignes, les risques et les coûts du témoin (EP-06 à EP-09) ;
les trois cents projets (EP-13).

---

## US-1000 — Les écrans du projet branchés sur le service

- **statut** : à faire
- **exigences** : `WF-ADM-0040-A`
- **opérations** : toutes celles de l'EPIC, lues par les écrans du projet
- **issue** :

**En tant que** chef de projet, **je veux** que l'accueil, l'écran du projet, ses paramètres, son
cycle de vie, ses révisions, ses contributeurs et ses sous-projets travaillent contre le service,
chacun avec mes réglages, **afin de** mener un projet sans faux back.

**Critères d'acceptation.**

- `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes données présentées
  selon leurs réglages respectifs. » : contre le service, deux comptes contributeurs du même
  projet, l'un en français, l'autre en anglais avec d'autres colonnes gardées, lisent le même
  projet et ses révisions ;
- écart : `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier celles
  d'un autre. » : constaté par EP-03 (US-0400) ;
- propre à l'US : l'accueil, les paramètres du projet et l'écran du projet ne portent plus
  `MockupNotice`, et leurs commentaires le disent ; un succès est ce que le service a gardé, relu ;
- propre à l'US : l'accueil connecté se rend contre le service (#1004), l'écran du journal ne
  tolère plus le 404 de `listProjects` et mène aux projets (#962) ;
- propre à l'US : les aides des écrans du projet (`frontend/help/fr/FBS-4*.md`, le projet et les
  révisions) disent ce que le service fait, là où elles disaient ce que le faux back
  n'appliquait pas.

**Notes de réalisation.** Les écrans sont ceux d'EP-02/L44, d'EP-14, d'EP-15 et d'EP-16 ; cette US
ne les réécrit pas. Un manque que le branchement révèle devient une issue, tranchée selon le
README ; un manque du contrat, une « Interface contract issue ». L'écran du projet qui mène à sa
révision (#1400) est d'EP-17, et les deux EPIC peuvent se croiser : le dernier fusionné reprend
l'autre.

**Hors périmètre.** Les écrans des grilles, du Gantt, des risques et des coûts (EP-06 à EP-10).

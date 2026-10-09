---
id: EP-14
titre: Les écrans de la maquette achevés, commandes branchées et constats du contrat soldés
statut: à planifier
depend_de: EP-02
famille: front
issue: 599
---

# EP-14 — Maquette du front : finitions

## Objet

Achever ce qu'EP-02 n'a pas fini quand il a été fusionné dans `main`, le 2026-10-09, pour
qu'EP-03 démarre sans attendre (décision de l'auteur) : les commandes d'écriture que la maquette
montre depuis la décision du 2026-10-08, branchées au contrat et répondues par le faux back sans
rien conserver ; les parties du contrat que ces commandes ont révélées ; l'univers témoin à
l'échelle de toute la structure ; l'accessibilité minimale et les quatre navigateurs.

Cet EPIC avance en parallèle d'EP-03 : il ne touche ni le contrat des comptes, des rôles et de la
session, ni le journal d'audit, qu'EP-03 réalise. Il reprend les règles, la conception et le faux
back d'EP-02, qui font foi pour lui.

## Ce qui en fait partie

- l'écran des sauvegardes, sa grille et ses commandes — sauvegarder, conserver, télécharger,
  restaurer —, puis le formulaire de planification et de la copie externe (#519) ;
- les paramètres des risques et des indicateurs (#512) ;
- les paramètres du projet — créer un projet, son identité et son cycle de vie (#583, #524), les
  sous-projets et les contributeurs (#584), le lotissement et le jalonnement (#585) ;
- les parties du contrat restantes : les nœuds retenus d'un lotissement filtré (#574), les
  écritures des ressources et des réglages (#575), la catégorie provision par défaut (#579), le
  rattachement au lotissement (#586), les sauvegardes (#588), le projet (#590), les sous-projets
  et les contributeurs (#592) — chacune suivie de son adoption par l'écran ;
- l'univers témoin : les lectures sur toute la structure, et les risques à l'échelle (#528, qui
  ferme #287) ; les relectures lentes sous charge (#500) ;
- l'accessibilité minimale (US-0200) et les navigateurs (US-0290), reprises d'EP-02 telles
  quelles.

## Ce qui n'en fait pas partie

- le comportement réel des écrans : il arrive avec l'EPIC de leur domaine — EP-04 pour le projet,
  EP-05 pour le référentiel, EP-13 pour les sauvegardes ;
- les comptes, les rôles, la session et le journal d'audit : EP-03 ;
- la restauration depuis un fichier déposé (#350) : EP-03, US-0440.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0100-A` | Accessibilité minimale | entière | US-0200 |
| `WF-CMP-0010-A` | Navigateurs et affichage | début — close en EP-13 | US-0290 |

Les commandes des écrans ne réalisent aucune exigence en propre : comme en EP-02, leurs tests
citent les exigences du domaine dont le Vérif tient côté front, et l'EPIC du domaine les clôt.

## Opérations du contrat

Celles d'EP-02, et les écritures que les écrans branchent : les sauvegardes (`startBackup`,
`retainBackup`, `downloadBackup`, `startRestore`, `setBackupSchedule`,
`testExternalBackupLocation`), les réglages (`updateReferenceSettings`), le projet
(`createProject`, `updateProject`, `getProjectNextState`), les sous-projets et les contributeurs
(`createSubproject`, `updateSubproject`, `deleteSubproject`, `setContributors`,
`listContributorSuggestions`), le lotissement (`setWorkBreakdown`, `generatePlanningSkeleton`).

## Préalables

EP-02 fusionné dans `main` ; la branche `epic/EP-14` tirée de `main` après cette fusion.

## Définition de fini

- chaque commande d'écriture qu'un écran de la maquette montre est branchée sur l'opération du
  contrat, gardée par la permission et les commandes disponibles, et dit son succès et son refus ;
- un contrôle automatisé de contraste ne relève aucun écart au niveau AA, en clair comme en sombre ;
- les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne sur les quatre
  navigateurs de la spécification ;
- les constats du contrat que ces écrans ont faits sont soldés — appliqués dans `docs/api`, ou
  écartés dans `DECISIONS.md` avec leur raison — et aucun n'est resté dans une tête.

## Constats reçus

Repris d'EP-02 à la coupure du 2026-10-09, renommés `[EP-14/Ln]` en gardant leur numéro de lot,
et rattachés à #599 :

- #512 [EP-14/L43] — les commandes du référentiel et des sauvegardes, dont #519 ;
- #513 [EP-14/L44] — les commandes des paramètres du projet : #583, #584, #585, et #524 ;
- #528 [EP-14/L45] — l'univers témoin à l'échelle, et #287 ;
- #507 [EP-14/L42] — ses parties de contrat ouvertes : #574, #575, #579, #586, #588, #590, #592 ;
- #84 [US-0200] et #126 ; #92 [US-0290] et #127 ;
- #500 — relectures lentes sous charge, à trancher ;
- #591 — le critère d'US-0210 à réécrire en écart quand les commandes du projet entrent.

Trois lots étaient commencés à la coupure, sur leur branche, et repartent d'`epic/EP-14` :
EP-14/L43c (l'écran des sauvegardes, revue 1 faite), EP-14/L44a (créer un projet, revue 1 faite)
et EP-14/L44b (sous-projets et contributeurs, à relire). Relevé par EP-02/L46, sans issue :
`DenseGrid` ne mémorise ni ses lignes ni ses cellules, si bien que chaque déplacement de la cellule
active les rend toutes ; aucun défaut n'est démontré en production.

## Conception

Celle d'EP-02, qui fait foi : arborescence du front, faux back et exemples, composants partagés,
commandes du référentiel (`CommandedList`, `ReferenceForm`, `CellCommand`), refus par champ,
défauts nommés du guide. Ce qu'EP-14 ajoute s'écrit au cadrage, avant son plan de lots.

## Notes de réalisation

L'écran des sauvegardes (#519), commencé en EP-02/L43c et repris ici (#599), reçoit sa grille et
ses commandes, la même entorse assumée au cadrage d'US-0250, qui le laissait en lecture : la liste
passe sur la grille dense, paginée par le serveur, ses colonnes choisies et élargies — le contrat ne
trie, ne cherche ni ne filtre les sauvegardes, et la grille n'en simule rien (WF-IHM-0090) —, et
chaque commande suit la permission du catalogue qui la garde (WF-ADM-0100) : à une session qui peut
modifier les sauvegardes, en déclencher une, une tâche de fond suivie comme les autres
(`startBackup`), en marquer une à conserver ou ne plus la conserver (`retainBackup`) ; à une session
qui peut restaurer la plateforme, la télécharger par une route du front qui relaie `downloadBackup`
en flux, jamais par une action serveur — le téléchargement est gardé par la permission de la
restauration (décision de l'auteur du 2026-10-09, #588) —, et la restaurer depuis une sauvegarde de
la liste (`startRestore`), après une confirmation qui énonce la date de la sauvegarde, sa
vérification et le caractère irréversible de l'opération, et exige la saisie de son identifiant
(WF-ADM-0160) ; aucune commande ne supprime une sauvegarde. Le refus d'un téléchargement ramène à
l'écran, qui le dit au-dessus de la liste et y porte le focus ; l'écran dit que le faux back ne
garde rien (`MockupNotice`). Les exemples de succès de ces écritures entrent au contrat
(`task_backup_queued`, `backup_retained`, `backup_released`, `task_restore_queued`). Ce que le
contrat ne porte pas est signalé pour #507 : les filtres et le tri de `listBackups`, le nom et la
longueur du fichier de `downloadBackup`, les commandes qu'une sauvegarde offre, et ce que refusent
`startBackup` et `startRestore` pendant qu'une sauvegarde ou une restauration court, comme une date
confirmée qui n'est pas celle de la sauvegarde. Le formulaire de la planification, de la rétention
et de la copie externe vient avec la partie suivante, L43d.

EP-02/L44, sur la décision de l'auteur du 2026-10-08 qui fait montrer à la maquette ses commandes
d'écriture (#513) — une entorse assumée au critère qui laissait les formulaires du projet à EP-04 —,
est découpé en trois parties menées en parallèle (décision de l'auteur du 2026-10-09), reprises ici
sous EP-14 : L44a (#583) le projet lui-même, L44b (#584) ses sous-projets et ses contributeurs,
L44c (#585) son lotissement et son jalonnement. L44a offre « Créer un projet » sur l'accueil (#524),
à la seule session qui porte la permission de le créer (WF-ADM-0100), indisponible tant que le
référentiel minimal est incomplet (WF-CYC-0120) : un formulaire validé côté front appelle
`createProject` — le libellé exigé (WF-PRJ-0080), le code facultatif (WF-PRJ-0010), la description —
et mène à l'écran du projet créé, que le faux back sert sous les traits du témoin. Les paramètres du
projet présentent son identité et ses faits, et leur modification (`updateProject`) comme le projet
liste sa commande `update` : le libellé, le code, la date de réception de la commande, la
description, le taux d'inflation et la probabilité de gain, saisis en pourcentages et envoyés en
rapports, celle-ci figée à partir de En cours (WF-PRJ-0090). La réponse prend la place des faits lus
tant qu'elle est plus récente, la page relue ; un refus par champ est dit au champ — le code déjà
porté par un autre projet (409) compris, depuis EP-02/L42g, qui le décrit au contrat et l'apprend au
formulaire —, la version périmée avec l'offre de relire ; l'écran dit que le faux back ne garde rien
(`MockupNotice`). Le cycle de vie, dont la sortie, irréversible, était déjà confirmée, dit le prochain
état du projet, son déclencheur et ses conditions restantes (`getProjectNextState`, WF-CYC-0050),
sans commande vers Chiffrage ni En cours (WF-CYC-0020). Les exemples de succès de ces écritures et
du prochain état entrent au contrat. Écarts au contrat relevés par L44a, pour #507 : le déclencheur
du prochain état n'est pas énuméré ; rien ne dit d'avance que la probabilité de gain est figée, ni
sous quel statut et quel pointeur `WIN_PROBABILITY_FROZEN` la refuse ; le prochain état d'un projet
en cours ou terminal n'est pas décrit ; le refus d'un code de projet déjà porté nomme le projet par
son seul identifiant, que l'écran ne connaît pas ; les bornes des deux taux ne sont pas dites.

---

## US-0200 — Accessibilité minimale

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** : #84

**En tant que** chef de projet, manager ou administrateur, **je veux** atteindre toute action
au clavier, lire les textes sans effort et agrandir l'affichage sans rien perdre, **afin
d'**utiliser Waterfall toute la journée sans que l'outil me coûte plus que le travail.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste
  visible. »
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau
  AA. »
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. »
- propre à l'US : chaque champ de saisie porte un libellé associé, et chaque image porteuse
  d'information une description — le quatrième point du corps de WF-IHM-0100, que son Vérif
  ne reprend pas ; un contrôle automatisé d'accessibilité le vérifie dans la chaîne ;
- propre à l'US : le contrôle de contraste joue en mode clair et en mode sombre — la charte
  existe dans les deux (US-0090), et un mode qui n'est pas contrôlé dérive.

**Notes de réalisation.** Le contrôle de contraste est exécuté par la chaîne, sinon il n'est
fait qu'une fois. Aucune conformité complète à un référentiel n'est visée ni déclarée
(§2.2) : ces quatre points, et rien de plus.

**Hors périmètre.** L'aide en ligne, qui n'est pas dans cet EPIC.

---

## US-0290 — Navigateurs et largeurs d'affichage

- **statut** : à faire
- **exigences** : `WF-CMP-0010-A`
- **opérations** : aucune en propre
- **issue** : #92

**En tant que** chef de projet, **je veux** que les grilles, le Gantt et les courbes
fonctionnent sur le navigateur de mon poste, et consulter les indicateurs depuis mon
téléphone, **afin de** ne rien installer et de répondre à une question sur un projet loin de
mon bureau.

**Critères d'acceptation.**

- `WF-CMP-0010-A` — « Les vues d'indicateurs se lisent sur un écran de 360 points de large et
  n'y proposent aucune saisie. »
- `WF-CMP-0010-A` — « Aucune fonction n'exige une installation sur le poste. »
- propre à l'US : les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne
  sur les quatre navigateurs de la spécification — Chrome et Edge par leurs canaux
  Playwright, Firefox, et WebKit tenant lieu de Safari —, en version courante, à 1366 points
  de large ;
- écart : `WF-CMP-0010-A` — « Les grilles, le diagramme de Gantt et les courbes s'affichent et
  s'utilisent sur chacun des quatre navigateurs, dans leurs deux dernières versions majeures,
  à 1366 points de large. » : la version majeure précédente et le Safari réel ne se rejouent
  pas par l'outillage ; ils se constatent en recette, sur la plateforme déployée — EP-13.
- écart : `WF-CMP-0010-A` — « Vérifiée en recette pour Safari et les terminaux mobiles. » : la
  recette se tient sur la plateforme déployée, avec son procès-verbal — EP-13.

**Notes de réalisation.** Le harnais d'EP-01 ne joue que Chromium : c'est cette US qui lui
ajoute les quatre navigateurs — Chrome et Edge sont des canaux de Chromium dans Playwright,
Firefox et WebKit ses deux autres moteurs, et le Safari réel reste à la recette (EP-13) —
et les deux largeurs, 1366 points partout, 360 pour les vues d'indicateurs.

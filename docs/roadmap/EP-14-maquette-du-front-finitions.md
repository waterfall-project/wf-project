---
id: EP-14
titre: Les écrans de la maquette achevés, commandes branchées et constats du contrat soldés
statut: à planifier
depend_de: EP-02
famille: front
issue: à ouvrir
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

Repris d'EP-02 à la coupure du 2026-10-09, à rattacher à l'issue de cet EPIC à son ouverture :

- #512 [EP-02/L43] — les commandes du référentiel et des sauvegardes, dont #519 ;
- #513 [EP-02/L44] — les commandes des paramètres du projet : #583, #584, #585, et #524 ;
- #528 [EP-02/L45] — l'univers témoin à l'échelle, et #287 ;
- #507 [EP-02/L42] — ses parties de contrat ouvertes : #574, #575, #579, #586, #588, #590, #592 ;
- #84 [US-0200] et #126 ; #92 [US-0290] et #127 ;
- #500 — relectures lentes sous charge, à trancher ;
- #591 — le critère d'US-0210 à réécrire en écart quand les commandes du projet entrent.

Trois lots étaient commencés à la coupure, sur leur branche, et repartent d'`epic/EP-14` :
EP-02/L43c (l'écran des sauvegardes, revue 1 faite), EP-02/L44a (créer un projet, revue 1 faite)
et EP-02/L44b (sous-projets et contributeurs, à relire). Relevé par EP-02/L46, sans issue :
`DenseGrid` ne mémorise ni ses lignes ni ses cellules, si bien que chaque déplacement de la cellule
active les rend toutes ; aucun défaut n'est démontré en production.

Reportés d'EP-03 le 2026-10-11 :

- #846 [EP-03] le guide dit encore à venir la confirmation de #836 — relevé par la revue
  d'US-0380/L2 : `docs/dev/README.md`, à la règle des préférences d'une grille, écrit
  « (#836, confirmation de l'auteur à venir) », alors que #836 est tranchée : les filtres d'une
  grille qui les déclare sont gardés en préférence. EP-14 écrit « (#836, confirmée par l'auteur
  le 2026-10-11) ». Reporté d'EP-03 le 2026-10-11.
- #847 [EP-03] la source commune des rôles répondus n'est éprouvée que dans un sens, et le test
  d'axe de la matrice en fait deux — relevé par la revue d'US-0380/L2 : seul « renommage puis case
  cochée » est éprouvé sous `RoleAnswers` ; l'inverse, que `role-answers.tsx` et le guide
  annoncent, n'a pas de test, et retirer `answers?.latest(shown)` de `renaming` ne casse rien ;
  le contrôle d'axe de la matrice fait la lecture et l'écriture dans un seul `it`. EP-14 ajoute
  le test du second sens — une case cochée, puis un renommage dont le corps porte la
  `lock_version` et les `permissions` de la réponse — et coupe le contrôle d'axe en deux `it`.
  Reporté d'EP-03 le 2026-10-11.
- #872 [EP-03] un import refusé après la fermeture de son formulaire n'est dit nulle part —
  relevé par la revue d'US-0350/L5b : `FileForm` (`import-commands.tsx`), fermé pendant
  l'envoi, ne dit son refus ni dans le formulaire démonté, ni sur l'écran qui l'a ouvert. EP-14
  rapporte le refus à l'écran porteur, comme `reference-form` le fait vers la liste, avec un
  test « fermer pendant l'envoi, refus dit ». Reporté d'EP-03 le 2026-10-11.
- #888 [EP-03] trois mineurs du front — relevés par la revue d'US-0350/L5b, tour 3 : le test
  « nothing armed » de `session.test.ts` n'affirme que l'adresse rendue, et non qu'aucune clé
  `wf:sign-out:*` n'a été écrite dans Redis ; `own` est créé sans condition dans
  `reference-form.tsx` et `commands.tsx`, sans le commentaire qui dirait pourquoi ; la directive
  `"use client"` de l'utilitaire de test `held-link.ts` n'a d'effet que sur les gardes d'import,
  ce que le guide (`typescript.md`, « Où s'exécute un composant ») ne dit pas. EP-14 reprend les
  trois. Reporté d'EP-03 le 2026-10-11.
- #889 [EP-03] les écritures des rôles et de la matrice ne retiennent pas la navigation —
  relevé par la revue d'US-0350/L5b, tour 4 : `permission-matrix.tsx` et `role-commands.tsx`
  appellent leurs actions sans `list.held` ni `useHeldCommand` ; refusée pendant qu'on quitte
  l'écran, une telle écriture n'est dite nulle part, contre l'invariant que #688 pose pour les
  autres. EP-14 fait passer ces trois appels par la retenue, avec un test « refus pendant la
  navigation » par écran, à l'image de `cost-commands.dom.test.tsx`. Le constat couvre aussi
  les écritures de la table des comptes (`user-commands.tsx`), relevées à la reprise d'epic
  d'US-0350/L5b après US-0360/L2b : EP-14 les fait passer par la même retenue. Reporté d'EP-03
  le 2026-10-11.
- #901 [EP-03] la liste garde les refus des lectures passées — relevé par la revue
  d'US-0350/L5b, tour 5 : depuis que les refus sont datés par une génération de lecture,
  `reported` (`reactivation.tsx`) garde ceux des générations passées, qui ne s'affichent plus
  jamais mais restent en mémoire tant que la liste vit. EP-14 n'y garde que les refus de la
  génération courante, avec un test qui le constate. Reporté d'EP-03 le 2026-10-11.
- #902 [EP-03] un test importe `RouterContext` d'un module privé de Next — relevé par la revue
  d'US-0350/L5b, tour 5 : `outcome-notice.dom.test.tsx` l'importe de `next/dist/shared/lib/…`,
  qu'une montée de version de Next peut casser sans avertissement. EP-14 fournit le routeur au
  test par une voie publique, une simulation de `next/navigation` comme les tests voisins.
  Reporté d'EP-03 le 2026-10-11.
- #905 [EP-03] des tests du front écrivent des espaces insécables littéraux, qu'ESLint ne relève
  pas — relevé pendant la correction du tour 5 d'US-0350/L5b : `page.test.tsx` des coûts,
  `reference-filters.dom.test.tsx`, `exchanges.dom.test.tsx`, `command.dom.test.tsx` et
  `resource-commands.dom.test.tsx` en écrivent encore, invisibles à la lecture, et
  `no-irregular-whitespace` ignore les chaînes par défaut. EP-14 les écrit par leur
  échappement, comme les tests voisins, et active la règle avec `skipStrings: false` sur les
  fichiers de tests. Reporté d'EP-03 le 2026-10-11.

Reportés d'EP-03 le 2026-10-12 :

- #937 [EP-03] le refus d'une écriture lancée avant un changement de lecture n'est dit nulle
  part — relevé par la revue d'US-0350/L5b, tour 5 : une écriture lancée sur une liste du
  référentiel, puis la lecture changée — recherche, filtre — avant sa réponse ; refusée, elle
  n'est plus dite, même au retour sur la lecture d'origine (`useHeldCommand(generation)`,
  #688), contre le « ne rien perdre en silence » d'US-0350. Rien n'est écrit par le service
  dans ce cas ; seul le message manque. EP-14, au retour sur la lecture d'origine, y rattache
  les écritures encore en cours et dit leur refus (décision de l'auteur). Reporté d'EP-03 le
  2026-10-12.
- #941 [EP-03] une confirmation d'anonymisation n'écrit rien sans le dire quand la ligne est
  occupée — relevé par le développement d'US-0360/L3b : un renommage de la même ligne commencé
  pendant que la confirmation est ouverte, celle-ci n'écrit rien, et rien ne le dit
  (`UserWrites.run` refuse en silence une écriture sur une ligne occupée, comme pour
  l'interrupteur d'état). EP-14 dit le refus, ou tient la confirmation indisponible tant que la
  ligne est occupée. Reporté d'EP-03 le 2026-10-12.
- #942 [EP-03] la confirmation d'anonymisation n'énumère pas tout ce que l'anonymisation fait —
  relevé par la revue d'US-0360/L3b, tour 1 : `admin.users.anonymizationFinal` dit
  l'irréversibilité (#856), mais ni le retrait de l'avatar ni celui du fournisseur d'identité
  d'un compte local (corps de WF-ADM-0060). EP-14 complète la phrase, en français et en
  anglais. Reporté d'EP-03 le 2026-10-12.
- #949 [EP-03] la désactivation reste offerte pendant que le lien de la même ligne est en
  route — relevé par la revue d'US-0360/L3b, tour 2 : `StateSwitch` (`user-cells.tsx`) ne lit
  pas `writes.linking`, si bien qu'un lien demandé avant une désactivation peut s'afficher pour
  un compte désactivé ; la connexion d'un tel compte reste refusée (WF-ADM-0060). EP-14 tient
  l'interrupteur tant que le lien de sa ligne est en route, avec un test. Reporté d'EP-03 le
  2026-10-12.
- #951 [EP-03] aucun test ne dit où tombe le focus quand le dialogue d'un lien se ferme
  par-dessus la création — relevé par la revue d'US-0360/L3b, tour 3 : `focusBack` vise la
  cellule du compte, derrière le dialogue modal de création ; le piège de focus de Radix le
  ramène probablement dans la création, sans test qui le constate. EP-14 ajoute l'assertion du
  focus après la fermeture du lien. Reporté d'EP-03 le 2026-10-12.
- #959 [EP-03] le focus tombe sur la page quand on ferme l'avis des écritures refusées de la
  barre — relevé par le développement d'US-0400/L2 : le bouton de l'avis
  (`left-refusals.tsx`, #863) disparaît à sa fermeture, et le focus tombe sur `<body>`. EP-14
  le rend à un élément stable de la barre. Reporté d'EP-03 le 2026-10-12.
- #963 [EP-03] deux finitions de l'écran et du parcours du journal d'audit — relevé par la
  revue d'US-0410/L2b, tour 1 : le parcours du journal crée un rôle « Audit … » à chaque passage
  sans le supprimer (`frontend/e2e/service/realm.ts`) ; une attribution sans effet dit « Aucun
  rôle donné ni retiré », mais un `access_role_update` sans libellé ni permission changés
  n'affiche rien (`audit-cells.tsx`). EP-14 supprime le rôle dans le `finally` du parcours, et
  décide si la seconde appelle une phrase. Reporté d'EP-03 le 2026-10-12.
- #967 [EP-03] deux finitions du parcours et de la cellule de l'action du journal — relevé par
  la revue d'US-0410/L2b, tour 2 : `audit.spec.ts` recopie en dur les langues de format et prend
  « aujourd'hui » à l'heure de l'assertion, non à celle de l'inscription, ce qui peut échouer à
  minuit ; le `title` de la seconde ligne de la cellule de l'action (`audit-cells.tsx`) répète
  son texte, lu deux fois par certaines aides techniques. EP-14 lit les langues de
  `FORMAT_LOCALE` et date l'attente de l'inscription, et ne pose le `title` que sur un texte
  tronqué. Reporté d'EP-03 le 2026-10-12.
- #984 [EP-03] le test de l'aboutissement de la lecture des comptes montre le compte rendu d'une
  autre tâche — relevé par la revue d'US-0370/L2b, tour 1 : dans `identity-sync.dom.test.tsx`,
  le commentaire présente le compte rendu de la lecture qui vient d'aboutir (tâche …0941), mais
  le test montre `identity_sync_report_flagged` (tâche …0942, variante contrefactuelle) ;
  l'aboutissement est prouvé avant, par le suivi. EP-14 ajoute l'exemple du compte rendu de la
  tâche …0941, ou retire ces lignes. Reporté d'EP-03 le 2026-10-12.
- #990 [EP-03] « Adresse portée par le compte Compte anonymisé » — relevé par la revue
  d'US-0370/L2b, tour 2 : la clé `admin.identitySync.carrier` (fr, en) met « compte » devant le
  nom du porteur, qui, anonymisé, est déjà « Compte anonymisé ». EP-14 prend une tournure qui ne
  l'ajoute pas, « Adresse portée par : » suivi du nom. Reporté d'EP-03 le 2026-10-12.

Reportés d'EP-03 le 2026-10-13 :

- #960 [EP-03] l'avis de la barre dit le nombre des écritures refusées, sans dire laquelle,
  pourquoi ni ce qui reste possible — relevé par la revue d'US-0400/L2, tour 1 : l'avis de la
  coquille (`left-refusals.tsx`, décision (b) de #863) compte les écritures refusées lancées
  depuis un écran quitté ; un refus parce que le service est injoignable ou la session perdue
  s'y dit comme un 412, alors que WF-EXP-0040 veut nommer le composant indisponible et ce qui
  reste possible. L'avis existe et prévient : EP-14 garde, par écriture libérée, l'écran et la
  nature du refus, et dit le dernier. Reporté d'EP-03 le 2026-10-13, sur décision de l'auteur.

## Conception

Celle d'EP-02, qui fait foi : arborescence du front, faux back et exemples, composants partagés,
commandes du référentiel (`CommandedList`, `ReferenceForm`, `CellCommand`), refus par champ,
défauts nommés du guide. Ce qu'EP-14 ajoute s'écrit au cadrage, avant son plan de lots.

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

---
id: EP-17
titre: La maquette finie hors contrat — accessibilité des dialogues, mineurs des écrans, lenteur du navigateur, cosmétique
statut: à planifier
depend_de: EP-16
famille: front
issue:
---

# EP-17 — Maquette : finitions et accessibilité

## Objet

EP-16 fige le contrat : il garde tout ce qui touche le contrat ou peut le toucher, et reporte le
reste ici (décision de l'auteur du 2026-10-22, au cadrage d'EP-16). EP-17 reçoit donc les
finitions de la maquette qui ne demandent que le front et son harnais :
- l'extension du harnais d'accessibilité aux dialogues, aux menus et aux éditeurs ouverts ;
- les ajustements de la validation de la maquette du 2026-10-23 qui ne touchent pas le contrat, et
  les défauts visibles du front ;
- les mineurs des composants partagés et des écrans ;
- la lenteur du navigateur à quitter une grille de mille tâches ;
- le cosmétique, marqué comme tel.

Il vient après EP-16 parce qu'il ne change pas le contrat, que les EPIC de domaine servent dès
qu'EP-16 est livré. Il peut avancer en parallèle d'eux.

## Ce qui en fait partie

Cadré le 2026-10-28, par objet : une US par écran ou par famille de composants, qui cite les
exigences de domaine dont une phrase de Vérif tient côté front (décision de l'auteur du 2026-10-28).

- le harnais d'accessibilité étendu aux dialogues, aux menus et aux éditeurs de cellule (#782,
  option A ; #784 ; #819, point 1), et les totaux gardés en vue à 911 points (#1209) — US-0710 ;
- l'écran d'un projet qui mène à sa révision (#1400) — US-0720 ;
- le Kanban filtré par libellé et par tâches prêtes, et l'accessibilité de sa carte (#1396,
  #1356) — US-0730 ;
- la matrice des risques sur fond blanc, la couleur sur les bulles, les seuls risques identifiés,
  pour sa part front (#1395), et les mineurs de la matrice repliable (#1386) — US-0740 ;
- les grilles du projet, le Gantt et les chronologies : la projection sur `kinds` (#1397), l'export
  PNG du Gantt avec les noms des tâches (#1428), et leurs mineurs (#1421, #1144, #1424, #806, #819
  points 4, 13, 14 et 15) — US-0750 ;
- ce que le faux back n'applique pas, dit dans le guide et à l'écran (#1399) — US-0760 ;
- les commandes et les écritures retenues des composants partagés (#1364, #1377, #889, #1476,
  #1430, #1432, #901, #781, et le point 2 de #1384) — US-0770 ;
- l'administration, la session et le journal d'audit (#941, #942, #949, #951, #984, #990, #1005,
  #1010, #1012, #1021, #1023, #1024, #1180, #847, #963, #967) — US-0780 ;
- l'écran des révisions, le panneau de l'aide et l'outillage des tests (#1438, #1481, #902, #905,
  #846, #888) — US-0790 ;
- la lenteur du navigateur à quitter une grille de mille tâches (#1230), une lenteur du
  produit — US-0800 ;
- le cosmétique, chaque constat marqué comme tel dans « Constats reçus », corrigé par le lot de
  son écran (décision de l'auteur du 2026-10-28).

## Ce qui n'en fait pas partie

- tout ce qui touche le contrat : EP-16. Au cadrage du 2026-10-28, deux constats y retournent ou
  y restent par cette règle (décisions de l'auteur du 2026-10-28) :
  - #1401 — la liste des projets filtrée par défaut sur Chiffrage et En cours : son point « à
    trancher au lot » — un choix d'états gardé en préférence — demande le contrat (`GridPreferences`
    n'a pas d'entrée pour la liste de l'accueil) ; il rend à EP-16 l'issue entière, titre et label
    `EP-16`, comme issue « contrat » que l'auteur tranche avant le gel ; EP-17 ne le reprend pas ;
  - #1533 — un refus à deux motifs sur le même champ ne dit que le premier (`byField`) : l'adoption
    par l'écran d'un exemple que le contrat d'EP-16 écrit (#817, point 2b), corrigé par US-0660/L3
    #1458 ; de même #1518 et #1524, corrigés par US-0660/L3 (décisions de l'auteur du 2026-10-27,
    confirmées le 2026-10-28), et #1525, reporté → EP-09 #1340 ;
- la stabilité des tests, qui relève d'EP-16 et jamais d'EP-17 (décisions de l'auteur des
  2026-10-25, 26 et 27, US-0590b à US-0590g) : la stabilité restante des parcours (#1263, #1145,
  #776, #1264) y est revenue le 2026-10-25 ; #1354 (`restore-dialog.dom.test.tsx` et
  `backup-deposit.dom.test.tsx` instables sous charge), d'abord dit « en EP-17 avec #1145 » le
  2026-10-23, y retourne au cadrage du 2026-10-28, titre et label `EP-16`, avec US-0590g
  (décision de l'auteur du 2026-10-28) ;
- les navigateurs et les largeurs d'affichage de WF-CMP-0010 (US-0290, 1366 et 360 points) : EP-13.
  Les 911 points de #1209 ne sont pas une largeur d'US-0290 mais l'agrandissement de 150 % de
  WF-IHM-0100, et le constat reste ici (décision de l'auteur du 2026-10-28) ;
- les points 1 et 3 de #1384 (les exemples du contrat) : EP-16, US-0640/L6 ; l'issue s'y ferme ;
- le comportement réel des écrans : l'EPIC de leur domaine.

## Exigences réalisées

EP-17 ne clôt aucune exigence : il finit, contre le faux back, des écrans que l'EPIC de chaque
domaine servira et vérifiera en entier. Comme en EP-14 et en EP-15, chaque US cite les exigences
dont une phrase de Vérif tient côté front, et ses tests citent ces exigences ; les phrases qui
demandent le service sont des écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-RAE-0030-A` | Démarrage d’une tâche | début — close en EP-09 | US-0730 |
| `WF-RIS-0040-A` | Grille de suivi des risques | début — close en EP-08 | US-0740 |
| `WF-PLA-0080-A` | Grille de planning | début — close en EP-06 | US-0750 |
| `WF-PLA-0090-A` | Diagramme de Gantt | début — close en EP-06 | US-0750 |
| `WF-PRJ-0020-A` | Lotissement | début — close en EP-04 | US-0750 |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | début — close en EP-04 | US-0780 |
| `WF-IHM-0140-A` | Aide en ligne | début — close en EP-11 | US-0790 |

Les exigences déjà closes par un EPIC livré que ces travaux touchent restent closes, et leurs tests
existants continuent de les citer ; trois d'entre elles sont citées par une US, avec tout leur
Vérif, parce que l'US porte un test qui en relève (décision de l'auteur du 2026-10-28) :
- `WF-IHM-0100-A`, Accessibilité minimale, close par EP-14 (US-0200) : US-0710 lève l'écart qu'EP-14
  a écrit sous sa première phrase — les dialogues, les menus et les éditeurs ouverts hors du
  harnais (#782, option A) — et le fichier d'EP-14 le note sous US-0200 ;
- `WF-IHM-0010-A`, Navigation et contexte du projet, close par EP-02 : US-0720 ;
- `WF-IHM-0070-A`, Une échelle de signalement commune, lisible sans couleur, close par EP-02 :
  US-0730 et US-0740.

## Opérations du contrat

Aucune en propre : celles que les écrans touchés lisent déjà, sans en ajouter ni en modifier —
`listNodes` et `compareRevisions` (la projection sur `kinds`, US-0750), `getProject` et
`listRevisions` (US-0720), `listStartableTasks` (US-0730), `getProjectRiskMatrix` et
`getPortfolioRisks` (US-0740), `getUser` (US-0780), `deleteAccessRole` (le nettoyage d'un parcours
du service, US-0780). Le diff de la branche de l'EPIC ne touche aucun fichier de `docs/api`.

## Préalables

EP-16 livré, le contrat en 1.0.0.

## Définition de fini

- chaque constat reçu est soldé : corrigé dans le front ou son harnais, ou écarté dans l'issue,
  avec sa raison ;
- le harnais d'accessibilité parcourt les dialogues, les menus et les éditeurs de cellule (#782,
  option A), en clair et en sombre, et l'écart qu'EP-14 a écrit sous US-0200 est levé, dans le
  fichier d'EP-14 comme dans la note du guide « Ce que les tests ne prouvent pas » ;
- `make check` passe sur la branche de l'EPIC, et la file de fusion est verte ; aucun test n'a
  gagné d'attente allongée, de `retries`, de `fixme` ni de seuil baissé ;
- chaque écran que l'EPIC change a son aide (`frontend/help/fr/<code>.md`) retouchée par le lot
  qui le change, et la liste des pages à venir reste vide ;
- `grid-frame.spec.ts` mesure à 911 points les deux écrans qu'il excluait (#1209) ;
- le diff de la branche de l'EPIC ne touche aucun fichier de `docs/api` ; `make roadmap` passe.

## Constats reçus

Reportés d'EP-16 à son cadrage (décision de l'auteur du 2026-10-22) et à son recadrage (2026-10-25,
#1445), label et titre `EP-17`, à rattacher à l'issue de l'EPIC à son ouverture, chacun sous l'US
qui le règle. Deux issues portent le label `EP-17` sous un titre `[EP-15]` : #1356 reste ici, son
titre s'accorde à l'ouverture ; #1354 retourne à EP-16 (« Ce qui n'en fait pas partie »).

**US-0710 — le harnais d'accessibilité.**

- #782 — front : les dialogues, les menus et les éditeurs hors du harnais d'accessibilité (option A,
  décision de l'auteur du 2026-10-11 ; périmètre fixé le 2026-10-28 : les dialogues, les menus et
  les éditeurs de cellule) ;
- #784 — front : les mineurs du harnais d'accessibilité ; son point 2, le parcours au clavier en
  sombre, se joue et se mesure (décision de l'auteur du 2026-10-28) ; ses points 1, 4, 6, 7, 12 et
  13 sont **cosmétiques** (rédaction du guide, de la note et d'un titre de test) ;
- #819, point 1 — front : le focus d'une cellule refusée distingué par la seule couleur ;
- #1209 — front : à 911 de large, replier les cartes ou plafonner la grille empilée pour garder les
  totaux en vue (reçu d'EP-15 le 2026-10-20 ; gardé ici le 2026-10-28).

**US-0720 — l'écran d'un projet.**

- #1400 — front : l'écran d'un projet mène directement à sa révision en cours (validation du
  2026-10-23) ; sans révision lisible, à la liste des révisions (décision de l'auteur du
  2026-10-28).

**US-0730 — le Kanban.**

- #1396 — front : le Kanban filtré par libellé et par tâches prêtes, la marque « prête à
  démarrer », le compteur de la colonne (validation du 2026-10-23) ; les filtres vivent dans
  l'adresse seule (décision de l'auteur du 2026-10-28) ;
- #1356 — front : l'annonce et le tiret de la carte du Kanban en attente de relecture (reçu d'EP-15,
  décision de l'auteur du 2026-10-23 ; titre `[EP-15]` à accorder).

**US-0740 — la matrice des risques.**

- #1395 — front : la matrice des risques sur fond blanc, la couleur sur les bulles, les seuls
  risques identifiés ; sa part contrat (le décompte de `cells`) est écrite par EP-16 (US-0700) ;
- #1386 — front : trois mineurs de la matrice repliable gardée ; son point 2 est **cosmétique**.

**US-0750 — les grilles du projet, le Gantt et les chronologies.**

- #1397 — front : la projection sur `kinds`, pour que la grille de planning, le planning d'un
  différentiel et la comparaison ne montrent pas les lignes de devis que le faux back rend ;
- #1428 — front : l'export PNG du Gantt porte une colonne des noms des tâches (option B de
  l'auteur, #1426) ;
- #1421 — front : la tenue de la légende des jours chômés dure un tick ;
- #1144 — front : la largeur mesurée de la barre des grilles denses n'est pas éprouvée au
  redimensionnement (décision de l'auteur du 2026-10-25 : EP-17, non repris par EP-15) ;
- #1424 — front : deux mineurs du test de provenance de l'écran des chronologies ;
- #806 — front : les mineurs de la relecture 1 de L44c, le lotissement dans sa grille ; son point 14
  relève de #803, corrigé en EP-16 ; ses points 11 et 15 sont **cosmétiques** ;
- #819, points 4, 13, 14 et 15 — front : la grille sous une recherche sans résultat, la lecture du
  lotissement en série, l'attente d'une action serveur trop large ; le point 15 est **cosmétique**.

**US-0760 — ce que le faux back n'applique pas.**

- #1399 — doc, front : le guide et `MockupNotice` disent que le faux back n'applique ni filtres, ni
  pagination, ni `kinds` (validation du 2026-10-23 ; le point 2 de #1397 y est tranché).

**US-0770 — les commandes et les écritures retenues.**

- #1364 — front : `ConfirmedCommand` laisse rouvrir la commande pendant l'écriture (défaut n° 24) ;
- #1377 — front : le refus tardif de « Modifier » un risque n'est pas redit au retour ;
- #889 — front : les écritures des rôles, de la matrice et de la table des comptes ne retiennent
  pas la navigation ;
- #1476 — front : trois mineurs des écritures retenues après « Précédent » (relevé par US-0590c ;
  reporté vers EP-17 sur décision de l'auteur du 2026-10-25) ;
- #1430 — front : des inscriptions de l'historique sans objet hors des trois de #1181 ;
- #1432 — front : `clear` de `cell-writes` hors de la référence synchrone ;
- #901 — front : la liste garde les refus des lectures passées ;
- #781 — test : `held()` n'a pas remplacé toutes les retenues faites à la main ;
- #1384, point 2 — front : le libellé et l'icône de `ReferenceForm` pour « Réexaminer » (l'issue
  reste en EP-16 pour ses points 1 et 3, et se ferme avec eux ; une issue `[EP-17]` reprend le point
  à l'ouverture).

**US-0780 — l'administration, la session et le journal d'audit.**

- #941 — front : une confirmation d'anonymisation n'écrit rien sans le dire quand la ligne est
  occupée ;
- #942 — front : la confirmation d'anonymisation n'énumère pas tout ce que l'anonymisation fait ;
- #949 — front : la désactivation reste offerte pendant que le lien de la même ligne est en route ;
- #951 — test : où tombe le focus quand le dialogue d'un lien se ferme par-dessus la création ;
- #984 — test : le test de l'aboutissement de la lecture des comptes montre un compte rendu d'une
  autre tâche ;
- #1005 — front : la liste des refus de compte recopiée dans `refusedState` ;
- #1010 — front : un auteur choisi que le journal d'audit ne retient plus s'affiche par son
  identifiant ;
- #1021 — test : citations manquantes et test de flux trop rigide ;
- #1024 — écran : « Session terminée » renvoie à une reconnexion qui ne dit pas l'issue de la
  restauration ; le message mène au journal d'audit (décision de l'auteur du 2026-10-28) ;
- #1180 — front : l'historique des messages et le suivi des tâches survivent à une session
  expirée ;
- #847 — front : la source commune des rôles répondus n'est éprouvée que dans un sens ;
- **cosmétiques** : #963 — deux finitions de l'écran et du parcours du journal d'audit (son point 2
  reçoit une phrase, décision de l'auteur du 2026-10-28) ; #967 — deux finitions du parcours et de
  la cellule de l'action du journal ; #990 — « Adresse portée par le compte Compte anonymisé » ;
  #1012 — la documentation de la page des comptes ; #1023 — « en attente » affiché un rendu avant
  la page du refus.

**US-0790 — l'écran des révisions, le panneau de l'aide et l'outillage des tests.**

- #1438 — front : la commande « Déclarer un risque » de l'écran des révisions ne fait rien ; elle
  devient un lien vers l'écran des risques (décision de l'auteur du 2026-10-28) ;
- #1481 — front : Échap dans le champ de recherche de l'aide ferme le panneau au lieu de vider le
  champ (relevé par US-0670/L1 ; reporté vers EP-17 sur décision de l'auteur du 2026-10-25) ;
- #902 — test : un test importe `RouterContext` d'un module privé de Next ;
- **cosmétiques** : #905 — des espaces insécables littéraux dans les tests du front ; #846 — le
  guide dit encore à venir la confirmation de #836 ; #888 — trois mineurs du tour 3 d'US-0350/L5b.

**US-0800 — la lenteur du produit.**

- #1230 — front : quitter un écran de grille de mille tâches coûte plusieurs secondes au navigateur
  (#1218) ; borné : la cause d'abord, un budget, un correctif à la cause (décision de l'auteur du
  2026-10-28).

## Conception

À écrire au cadrage.

---

## US-0710 — Le harnais d'accessibilité parcourt les dialogues, les menus et les éditeurs

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** :

**En tant que** chef de projet, manager ou administrateur, **je veux** que ce qu'un geste ouvre —
un dialogue, un menu, l'éditeur d'une cellule — se parcoure au clavier comme l'écran qui le porte,
sans piège, le focus visible, et que les totaux d'une grille restent en vue à 150 %
d'agrandissement, **afin d'**utiliser Waterfall toute la journée au clavier seul, sans qu'une
commande se dérobe.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » :
  sur chaque écran du harnais, chaque déclencheur `aria-haspopup="dialog"` ou `aria-haspopup="menu"`
  est ouvert par Entrée, et l'éditeur d'une cellule saisissable de chaque grille par F2 ; ce qui
  s'ouvre est parcouru au Tab — aucun piège hors de celui que veut un dialogue modal, chaque élément
  atteint visible et marqué —, audité par axe, fermé par Échap, et le focus revient au déclencheur
  ou à la cellule ; l'écart qu'EP-14 a écrit sous cette phrase (US-0200, #782) est levé, et la note
  du guide le dit ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » : il
  porte aussi sur ce que le geste a ouvert, en clair et en sombre ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » : à
  911 points, la ligne des totaux du reste à engager et des coûts réels reste dans une fenêtre de
  768 de haut — les cartes repliées, ou la grille empilée plafonnée —, et `grid-frame.spec.ts`
  mesure ces deux écrans à 911 (#1209) ;
- propre à l'US : le parcours au clavier joue en sombre comme en clair, et la pull request donne la
  durée du fichier avant et après (#784, point 2) ; les autres points de #784 sont corrigés, ou
  écrits dans « Ce que les tests ne prouvent pas » avec leur raison ;
- propre à l'US : le focus d'une cellule refusée se distingue autrement que par la couleur (#819,
  point 1).

**Notes de réalisation.** Le harnais est celui d'EP-14 (`accessibility.spec.ts`, `axe.ts`,
`tab-walk.ts`, `focus-probe.ts`), que l'US étend sans le réécrire ; US-0590g (EP-16) y lit les
mesures par lots avant que cette US ne commence. Les popovers de refus, les `<details>` fermés et
les états atteints par un geste (`?import=`) restent aux tests de composants et s'écrivent dans la
note du guide (décision de l'auteur du 2026-10-28). Le coût de chaîne se mesure contre la règle
d'US-0590d : une étape qui dépasserait 10 % du chemin critique se dit dans la pull request.

**Hors périmètre.** Les navigateurs et 360 points (US-0290, EP-13) ; une conformité déclarée (§2.2).

---

## US-0720 — L'écran d'un projet mène à sa révision

- **statut** : à faire
- **exigences** : `WF-IHM-0010-A`
- **opérations** : `getProject`, `listRevisions`
- **issue** :

**En tant que** chef de projet, **je veux** qu'ouvrir un projet m'amène à la révision sur laquelle
je travaille, **afin de** ne pas m'arrêter à une fiche qui ne me sert pas (#1400).

**Critères d'acceptation.**

- `WF-IHM-0010-A` — « Un utilisateur qui n'a ouvert aucun projet atteint le portefeuille, le
  référentiel, l'administration et l'écran d'état. »
- `WF-IHM-0010-A` — « Dans un projet, le passage du reste à engager aux risques puis aux indicateurs
  conserve la révision affichée et le sous-projet filtré. »
- `WF-IHM-0010-A` — « Le retour au projet précédent depuis une fonction hors projet retrouve le même
  contexte. » : `/projects/P` mène à `/projects/P/revisions/R`, où `R` est la révision en cours,
  sinon la révision de référence, sinon la dernière révision marquée, le contexte de lecture de
  l'adresse et ses filtres gardés ; quand la révision choisie n'est pas lisible par la session,
  l'écran mène à `/projects/P/revisions` (décision de l'auteur du 2026-10-28) ;
- propre à l'US : un projet sans révision garde l'écran du projet — l'encart de démarrage du
  planning et les imports qui créent la révision —, sans liste de révisions ;
- propre à l'US : le compte rendu d'un import nommé par l'adresse (`?import=`) s'ouvre sur l'écran
  des échanges de la révision choisie quand le projet en a une, et sur l'écran du projet quand
  l'import est celui qui crée la première ; tous les liens qui mènent à `/projects/P` passent par le
  renvoi, et le chemin témoin d'US-0080 et ses parcours suivent ;
- propre à l'US : l'aide de l'écran du projet et celle de la liste des révisions disent ce renvoi.

**Notes de réalisation.** La fiche du projet n'a plus d'écran à elle : le bandeau de contexte nomme
le projet et son état, et ses paramètres (`/projects/P/settings`) la portent. WF-IHM-0010 et
WF-IHM-0020 restent inchangés et se vérifient au lot. #1401 (la liste des projets filtrée par
défaut) n'est pas ici : rendu à EP-16, parce que son point à trancher demande le contrat.

**Hors périmètre.** La liste des projets de l'accueil (#1401, EP-16).

---

## US-0730 — Le Kanban filtré, et sa carte annoncée

- **statut** : à faire
- **exigences** : `WF-RAE-0030-A`, `WF-IHM-0070-A`
- **opérations** : `listStartableTasks`
- **issue** :

**En tant que** chef de projet, **je veux** retrouver une tâche du Kanban par son libellé, ne voir
que les tâches prêtes à démarrer quand je le demande, et reconnaître une tâche prête sans lire ses
prédécesseurs, **afin de** démarrer le travail du jour sans parcourir trois colonnes (#1396).

**Critères d'acceptation.**

- `WF-RAE-0030-A` — « Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non
  démarré tant que personne ne le termine. » : la marque « prête à démarrer » s'ajoute, sur la carte
  de toute tâche non démarrée dont `predecessors_completed` est vrai, par une icône et un texte,
  filtre actif ou non ; la marque « prêt à terminer » du jalon ne change pas ;
- écart : `WF-RAE-0030-A` — « Une tâche passée à l’état démarré voit ses lignes apparaître dans la
  grille de reste à engager. » : constaté par EP-15 (US-0540), inchangé ici ; EP-09 clôt.
- écart : `WF-RAE-0030-A` — « Une tâche non démarrée n’y apparaît qu’à la demande. » : idem ; EP-09
  clôt.
- écart : `WF-RAE-0030-A` — « Le passage direct de non démarrée à terminée n’est possible que pour
  un jalon, ou par la saisie d’un reste à engager nul sur toutes les lignes d’une tâche non démarrée
  (WF-RAE-0040) ; un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. » :
  idem ; EP-09 clôt.
- écart : `WF-RAE-0030-A` — « Aucune commande ne fait passer une tâche démarrée à l’état non
  démarré. » : idem ; EP-09 clôt.
- écart : `WF-RAE-0030-A` — « Un jalon terminé que l’on rouvre est non démarré et ne contribue plus
  à la valeur acquise. » : idem ; EP-09 clôt.
- écart : `WF-RAE-0030-A` — « Une tâche feuille démarrée sans ligne de devis est terminée depuis le
  Kanban. » : idem ; EP-09 clôt.
- `WF-IHM-0070-A` — « Aucun écran ne distingue deux états par la seule couleur. » : la marque
  « prête à démarrer » se lit sans couleur, et le tiret décoratif de la carte n'est pas lu par les
  lecteurs d'écran (#1356, point 1) ;
- `WF-IHM-0070-A` — « Une copie d'écran en niveaux de gris laisse identifier chaque signalement. »
- `WF-IHM-0070-A` — « La même zone d'indice porte la même couleur dans la liste des projets, dans
  les indicateurs du projet et dans la performance du portefeuille. »
- propre à l'US : un champ au-dessus du tableau filtre les trois colonnes par libellé ; un filtre
  « Tâches prêtes » ne garde, dans la colonne Non démarrée, que les tâches prêtes, les deux autres
  colonnes inchangées ; le front filtre sur ce que le serveur rend et ne calcule rien
  (WF-ARC-0020) ; les deux filtres vivent dans l'adresse seule, sans préférence (décision de
  l'auteur du 2026-10-28) ;
- propre à l'US : sous un filtre, l'en-tête de chaque colonne dont des cartes sont masquées dit son
  compte, « 4 sur 12 », lu par les lecteurs d'écran ; une carte sélectionnée qu'un filtre masque
  perd la sélection, et le clavier reprend sur la première carte visible de sa colonne ;
- propre à l'US : la région d'état de la lecture d'une carte est permanente, le bouton « Réessayer »
  hors d'elle (#1356, point 2), et le commentaire du test du chemin nominal est réécrit (point 3) ;
- propre à l'US : l'aide du Kanban décrit les filtres et la marque.

**Notes de réalisation.** Trois colonnes, les états d'une tâche : une quatrième colonne « Prêtes »
est écartée par l'auteur (#1396). `predecessors_completed` est déjà rendu (`NotStartedTask`) ; le
contrat ne change pas.

**Hors périmètre.** Un filtre gardé en préférence ou en session ; le glisser-déposer, inchangé.

---

## US-0740 — La matrice des risques sur fond blanc

- **statut** : à faire
- **exigences** : `WF-RIS-0040-A`, `WF-IHM-0070-A`
- **opérations** : `getProjectRiskMatrix`, `getPortfolioRisks`
- **issue** :

**En tant que** chef de projet ou manager, **je veux** lire la matrice des risques d'une révision et
du portefeuille sans qu'un fond rouge sur neuf dixièmes de la surface la noie, chaque bulle portant
la zone que le serveur lui rend, **afin de** voir d'un coup d'œil où sont les risques identifiés
(#1395).

**Critères d'acceptation.**

- `WF-RIS-0040-A` — « Un risque dont la probabilité augmente change de couleur conformément à la
  matrice. » : la couleur est celle de la bulle, prise de `RiskMatrixPoint.zone`, que le front ne
  classe pas (WF-ARC-0020) ; les seize cases sont sur fond blanc, avec leur trait, leurs graduations
  et le nom de leur zone, et les axes restent linéaires (#1253) ;
- `WF-RIS-0040-A` — « Les trois totaux — identifiés, survenus, écartés — sont distincts, et la
  réserve pour risques de la référence est affichée en regard. » : les totaux de provisions restent
  sur les trois états, quand le graphique ne montre plus que les risques identifiés, pour un projet
  comme pour le portefeuille, quel que soit le filtre d'état de la grille ; la légende des états
  disparaît ; le décompte par case (`cells`), compté par le serveur (US-0700, EP-16), est affiché
  tel quel ;
- écart : `WF-RIS-0040-A` — « Les six colonnes sont présentes, ainsi que l’accès aux deux notes et à
  l’historique. » : constaté par EP-15 (US-0550), inchangé ici ; EP-08 clôt.
- écart : `WF-RIS-0040-A` — « Le tri par provision classe les risques du plus lourd au plus
  léger. » : idem ; EP-08 clôt.
- `WF-IHM-0070-A` — « Aucun écran ne distingue deux états par la seule couleur. » : la zone d'une
  bulle se distingue aussi sans sa couleur, par sa forme, qui ne sert plus à l'état ;
- `WF-IHM-0070-A` — « Une copie d'écran en niveaux de gris laisse identifier chaque signalement. »
- `WF-IHM-0070-A` — « La même zone d'indice porte la même couleur dans la liste des projets, dans
  les indicateurs du projet et dans la performance du portefeuille. »
- propre à l'US : la taille d'une bulle selon la gravité, l'infobulle, le clic vers le risque ou
  vers son projet, l'export PNG avec sa provenance, le pliage (#1252) et la table accessible sont
  gardés ;
- propre à l'US : les trois mineurs de #1386 sont corrigés — le nom exact du bouton de fermeture
  dans le test du refus, l'ordre des imports, une fonction « écrire maintenant » de `useKeptWriter`
  à la place de `record` suivi de `flush` ;
- propre à l'US : l'aide de l'écran des risques et celle de la vue des risques du portefeuille
  décrivent la matrice ainsi.

**Notes de réalisation.** La décision de l'auteur du 2026-10-23 dans #1395 fait foi ; le graphique
est partagé (`risk-bubble-chart.tsx`) entre les deux écrans. Cette US ne commence qu'US-0700/L2
(EP-16) fusionné : le décompte de `cells` lui vient du contrat.

**Hors périmètre.** Les axes (#1253 tient) ; le décompte lui-même (EP-16).

---

## US-0750 — Les grilles du projet, le Gantt et les chronologies

- **statut** : à faire
- **exigences** : `WF-PLA-0080-A`, `WF-PLA-0090-A`, `WF-PRJ-0020-A`
- **opérations** : `listNodes`, `compareRevisions`
- **issue** :

**En tant que** chef de projet, **je veux** que la grille de planning ne montre que ses tâches,
même contre un faux back qui rend plus que demandé, que l'image exportée du Gantt nomme ses tâches,
et que les grilles du projet tiennent ce que leurs revues ont relevé, **afin de** juger la maquette
sur ce qu'elle montre et lire un Gantt exporté sans l'écran à côté (#1397, #1428).

**Critères d'acceptation.**

- `WF-PLA-0080-A` — « Chacune des colonnes citées est présente. » : la projection de la page garde
  les seuls nœuds dont le type est demandé par `kinds`, sur la grille de planning, le planning d'un
  différentiel et la comparaison de révisions ; une réponse qui mêle tâches et lignes ne fait
  atteindre à la grille aucune ligne, et la révision 102 de `make dev` ne montre aucune ligne de
  devis ; les grilles de devis et de reste à engager montrent toujours leurs lignes ;
- écart : `WF-PLA-0080-A` — « L’indentation d’un groupe de tâches déplace le groupe entier sous la
  tâche précédente. » : constaté par EP-15 (US-0460), inchangé ici ; EP-06 clôt.
- `WF-PLA-0080-A` — « La recherche sur un libellé ne laisse voir que les tâches correspondantes et
  leurs parents. » : une recherche sans résultat sur une structure qui a des tâches montre une
  grille vide qui le dit, non le squelette « indisponible » (#819, point 4) ;
- écart : `WF-PLA-0080-A` — « Les trois sortes de tâches se distinguent sans lire leur durée. » :
  constaté par EP-15, inchangé ici ; EP-06 clôt.
- écart : `WF-PLA-0080-A` — « Une tâche terminée se distingue d’une tâche démarrée sans lire de
  colonne ; une feuille ne porte pas d’avancement physique. » : idem ; EP-06 clôt.
- écart : `WF-PLA-0080-A` — « Le filtre sur un poste ne laisse voir que la tâche qui le porte, son
  sous-arbre et ses parents. » : idem ; EP-06 clôt.
- `WF-PLA-0090-A` — « Les liaisons et la hiérarchie sont visibles, ainsi que le chemin critique. » :
  l'export PNG du Gantt porte, à gauche des barres, une colonne des noms des tâches indentés selon
  leur niveau, qui compte dans la borne de largeur du canevas (#1428, option B) ;
- écart : `WF-PLA-0090-A` — « Aucune action de la souris ou du clavier ne modifie une tâche depuis
  le Gantt. » : constaté par EP-15 (US-0530), inchangé ici ; EP-06 clôt.
- écart : `WF-PLA-0090-A` — « Une récapitulative pliée dans la grille l’est dans le Gantt, et
  réciproquement. » : idem ; EP-06 clôt.
- `WF-PRJ-0020-A` — « Un poste peut être créé sans livrable. » : le test qui le cite affirme un
  poste sans livrable (#806, point 4) ;
- écart : `WF-PRJ-0020-A` — « Un projet sans lotissement saisi présente un lot, un poste et aucun
  livrable. » : constaté par EP-15 (US-0450), inchangé ici ; EP-04 clôt.
- propre à l'US : la légende des jours chômés du Gantt est tenue jusqu'à la mesure de l'axe, et non
  un tick (#1421 ; #1539, s'il est tranché vers ce lot) ; la largeur mesurée de la barre des grilles
  denses est éprouvée au redimensionnement, et la largeur minimale de la recherche comparée aux
  minimales mesurées (#1144) ;
- propre à l'US : les mineurs du lotissement dans sa grille (#806, points 1 à 3, 5 à 10, 12, 13, 16)
  sont corrigés — une écriture dont l'élément visé manque à la lecture de départ n'est pas envoyée
  et le dit ; un refus pointé sur l'élément lui-même lui est attribué ; une suppression refusée est
  éprouvée ; un lotissement vide dit « Aucun poste » — et les mineurs des tests du planning et des
  chronologies (#819, points 13 et 14 ; #1424) ;
- propre à l'US : l'aide de la grille de planning et celle du Gantt décrivent l'export et la grille
  vide.

**Notes de réalisation.** La projection sur `kinds` suit celle sur `fields` (EP-02/L4 : « le faux
back ignore `fields` ») ; le faux back ne change pas, et #1399 (US-0760) dit sa limite. Le point 2
de #1397 est tranché par l'auteur le 2026-10-23 : aucune couche devant Prism. Le point 11 de #806
(`dense-grid.tsx` à cinq lignes de la limite de `make sources`) se règle par une coupe si le lot le
franchit.

**Hors périmètre.** Les lignes de devis et de reste à engager ; le lotissement lui-même (EP-04).

---

## US-0760 — Ce que le faux back n'applique pas, dit

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** :

**En tant que** chef de projet qui valide la maquette, **je veux** savoir, sur un écran de liste ou
de grille de `make dev`, que les filtres, la recherche, le tri, la pagination et `kinds` n'y sont
pas appliqués, **afin de** ne pas juger comme un défaut ce que le faux back ne fait pas (#1399).

**Critères d'acceptation.**

- propre à l'US : `docs/dev/README.md` a une section « Ce que le faux back ne fait pas », près de
  `make dev` : Prism rend le premier exemple de l'opération quelle que soit la requête — ni filtre,
  ni recherche, ni tri, ni pagination (`limit`, `offset`, la barre se calculant sur le `meta` de
  l'exemple), ni `kinds`, ni `fields`, ni `include_inactive` — et ne garde rien ; les mentions
  éparses du guide y renvoient ;
- propre à l'US : `MockupNotice` dit, sur les écrans de listes et de grilles, que les filtres et la
  pagination n'y sont pas appliqués, en une phrase, dans les deux catalogues, éprouvée par un test ;
  où et comment la dire sans charger chaque écran se fixe à la conception.

**Notes de réalisation.** Décision de l'auteur du 2026-10-23 : on l'accepte et on le dit ; le faux
back ne change pas ; une couche devant Prism est écartée.

**Hors périmètre.** Le faux back ; la projection sur `kinds` (US-0750).

---

## US-0770 — Les commandes et les écritures retenues

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : aucune en propre
- **issue** :

**En tant que** chef de projet ou administrateur, **je veux** qu'une commande en cours d'écriture
ne se rouvre pas, qu'un refus tardif me soit redit, et qu'une écriture retienne la navigation
partout, **afin qu'**une réponse tardive n'efface pas ce que je saisis ni ne se perde (#1364, #1377,
#889).

**Critères d'acceptation.**

- propre à l'US : `ConfirmedCommand` tient indisponible la commande qui ouvre le formulaire pendant
  l'écriture (défaut n° 24), pour toutes ses instances, éprouvé par un test (#1364) ;
- propre à l'US : un refus de « Modifier » un risque reçu pendant que le détail montre un autre
  risque est redit quand on revient sur ce risque ; un succès ne l'est pas (#1377) ;
- propre à l'US : les écritures des rôles, de la matrice des permissions et de la table des comptes
  retiennent la navigation (`useHeldCommand`, ou `list.held`), avec un test « refus pendant la
  navigation » par écran (#889) ;
- propre à l'US : un refus d'une écriture retenue après « Précédent » puis « Suivant » n'est dit
  qu'une fois, ou le double dire est écrit comme accepté ; le guide dit qu'une écriture d'un écran
  quitté par « Précédent » retient encore ses clics jusqu'à sa réponse ; `shell.spec.ts` commente ce
  que `toHaveText("Mon compte")` prouve (#1476) ;
- propre à l'US : chaque appel de `say(...)` sans objet est instruit : l'objet nommé là où la
  commande en a un, un commentaire là où elle n'en a pas (#1430) ;
- propre à l'US : `clear` de `cell-writes` passe par la référence synchrone, un test faisant partir
  `clear()` et un refus de `retotal` dans le même `act` avec une seule entrée ; le test du refus
  voisin affirme l'issue `stale` (#1432) ;
- propre à l'US : la liste de réactivation purge les refus des générations passées (#901) ;
- propre à l'US : `held()` remplace les cinq retenues faites à la main, et aucune autre ne reste
  dans `frontend/src` (#781) ;
- propre à l'US : `ReferenceForm` dit « Réexaminer » par son libellé et une icône qui n'est pas
  `Save`, sans quatrième branche au ternaire (#1384, point 2).

**Notes de réalisation.** US-0590d (EP-16) a posé la forme des commandes en ligne — un état
« occupé » local, levé dans la même mise à jour que la réponse (option B de #1491, défaut n° 25) —
et celle des dialogues modaux — la transition imbriquée ; cette US s'y tient, et le défaut n° 24
du guide se relit à sa lumière.

**Hors périmètre.** `byField` et ses deux motifs (#1533, EP-16).

---

## US-0780 — L'administration, la session et le journal d'audit

- **statut** : à faire
- **exigences** : `WF-ADM-0060-A`
- **opérations** : `getUser`, `deleteAccessRole`
- **issue** :

**En tant qu'**administrateur, **je veux** que la confirmation d'anonymisation dise tout ce qu'elle
fait et ne se taise jamais, que la désactivation et le lien d'un compte ne se contredisent pas, que
le journal nomme un auteur même sans ligne, et qu'une session finie n'en laisse rien au suivant,
**afin de** tenir les comptes sans surprise.

**Critères d'acceptation.**

- `WF-ADM-0060-A` — « Après anonymisation d’un compte désactivé, aucun écran — journal d’audit
  compris — ne présente plus son nom ni son adresse ; les révisions qu’il a marquées affichent le
  libellé neutre comme auteur ; sa réactivation est refusée. » : la confirmation d'anonymisation
  énumère ce que l'anonymisation fait — l'irréversibilité, le retrait de l'avatar, le retrait du
  fournisseur d'identité d'un compte local (#942) —, et le porteur anonymisé d'une adresse se dit
  sans « compte » devant le libellé neutre (#990) ;
- `WF-ADM-0060-A` — « Aucun écran ne propose de supprimer un compte. »
- `WF-ADM-0060-A` — « La connexion d’un compte désactivé est refusée. » : la désactivation est tenue
  tant que le lien de la même ligne est en route, l'invariant tenant dans les deux sens (#949) ;
- écart : `WF-ADM-0060-A` — « Une révision marquée par un compte depuis désactivé affiche toujours
  son auteur. » : constaté par EP-03 (US-0360), inchangé ici ; EP-04 clôt.
- écart : `WF-ADM-0060-A` — « Un compte réactivé se connecte de nouveau avec ses rôles d’avant. » :
  idem ; EP-04 clôt.
- propre à l'US : une confirmation d'anonymisation ouverte pendant qu'un renommage occupe la ligne
  n'écrit rien et le dit, ou se tient indisponible tant que la ligne est occupée (#941) ; un test
  dit où tombe le focus quand le dialogue d'un lien se ferme par-dessus la création (#951) ;
- propre à l'US : un auteur choisi dans le filtre du journal d'audit qu'aucune ligne lue ne nomme
  est lu par `getUser`, au plus une fois, et nommé, jamais par son identifiant (#1010) ;
- propre à l'US : l'historique des messages et le suivi des tâches s'effacent à toute fin de session
  constatée — expiration, connexion d'un autre compte —, éprouvé (#1180) ;
- propre à l'US : `refusedState` passe par `ACCOUNT_REFUSALS`, un `it.each` parcourant la liste
  (#1005) ;
- propre à l'US : le message `maintenance.signedOut` mène au journal d'audit, où l'issue de la
  restauration se lit (#1024) ; « en attente » n'est plus rendu avant la page du refus (#1023) ;
- propre à l'US : les tests disent ce qu'ils montrent — le compte rendu de la tâche qui vient
  d'aboutir (#984), les deux sens de la source commune des rôles répondus et un contrôle d'axe par
  `it` (#847), les citations manquantes et le flux lu jusqu'à la fin (#1021) ;
- propre à l'US : le parcours du journal supprime le rôle qu'il crée, l'inscription
  `access_role_update` sans changement reçoit une phrase (#963), le parcours ne recopie pas les
  locales en dur et prend « aujourd'hui » à l'heure de l'inscription, le `title` d'une cellule n'est
  posé que si le texte est tronqué (#967) ; la documentation de la page des comptes dit tout refus
  422 (#1012) ;
- propre à l'US : les aides de l'administration touchées (les comptes, le journal, les sauvegardes)
  sont retouchées.

**Notes de réalisation.** Les écritures de la table des comptes retenues à la navigation sont dans
US-0770 (#889). Les constats viennent d'EP-03, reportés trois fois ; chaque point se relit d'abord
sur `epic/EP-16` livré, et un point que la livraison a rendu sans objet se ferme avec sa raison.

**Hors périmètre.** Le service d'anonymisation (EP-04) ; le suivi de la tâche `restore` par le
suivi des tâches.

---

## US-0790 — L'écran des révisions, le panneau de l'aide et l'outillage des tests

- **statut** : à faire
- **exigences** : `WF-IHM-0140-A`
- **opérations** : aucune en propre
- **issue** :

**En tant que** chef de projet, **je veux** qu'une commande offerte fasse ce qu'elle promet, et
qu'Échap dans la recherche de l'aide vide d'abord le champ, **afin de** ne pas rencontrer une
commande muette ni perdre le panneau d'un geste (#1438, #1481).

**Critères d'acceptation.**

- `WF-IHM-0140-A` — « Chaque écran ouvre une aide qui le concerne. » : un premier Échap dans le
  champ de recherche du panneau vide le champ quand il porte une requête, le second ferme le
  panneau, éprouvé au clavier (#1481) ; l'aide de l'écran des révisions ne dit plus que
  « Déclarer un risque » n'ouvre rien ;
- écart : `WF-IHM-0140-A` — « Dans la grille de devis, l’intitulé de la colonne du montant corrigé
  de l’inflation porte une infobulle qui nomme l’année de référence et le taux d’inflation. » :
  constaté par EP-15 (US-0580), inchangé ici ; EP-11 clôt.
- écart : `WF-IHM-0140-A` — « L’aide s’affiche dans la langue de l’utilisateur. » : la décision de
  la langue est d'US-0670 (EP-16), inchangée ici ; EP-11 clôt.
- propre à l'US : sur l'écran des révisions, « Déclarer un risque », quand elle est disponible, mène
  à l'écran des risques de la révision, où « Identifier un risque » s'offre ; son infobulle le dit
  (#1438, décision de l'auteur du 2026-10-28) ;
- propre à l'US : `outcome-notice.dom.test.tsx` reçoit le routeur par une voie publique (#902) ; les
  espaces insécables des tests s'écrivent par leur échappement, et `no-irregular-whitespace` les
  relève dans les fichiers de tests (#905) ; le guide dit #836 confirmée (#846) ; les trois mineurs
  de #888 sont corrigés.

**Notes de réalisation.** Le panneau de l'aide est celui d'US-0670/L1 (`help-panel.tsx`, Radix) :
Échap y est pris par le dialogue, et le champ doit le prendre avant.

**Hors périmètre.** La rédaction des aides (US-0670, EP-16).

---

## US-0800 — Quitter une grille de mille tâches

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** :

**En tant que** chef de projet, **je veux** quitter une grille de mille tâches sans que le
navigateur se fige plusieurs secondes, **afin de** passer d'un écran à l'autre au rythme de mon
travail (#1230).

**Critères d'acceptation.**

- propre à l'US : la cause est écrite dans la pull request, après une mesure reproductible qui la
  montre — le démontage de la grille, les styles, le payload RSC gardé, ou autre —, avant tout
  correctif ;
- propre à l'US : le correctif tombe où la cause est, et un test ou une mesure échoue sans lui et
  passe avec ; quitter la grille de mille tâches coûte au navigateur moins d'une seconde de travail
  natif, ou la pull request dit pourquoi la borne n'est pas atteinte ;
- propre à l'US : les attentes de `workload.spec.ts` et de `screens.spec.ts` alignées sur `WORKING`
  pour ce départ reviennent à la borne courte si la mesure le permet ; aucune attente allongée,
  aucun `retries`, aucun `fixme`, aucun seuil baissé.

**Notes de réalisation.** Borné comme US-0590f (EP-16) : 90 minutes de diagnostic au total ; passé
ce délai sans cause, le lot passe `question` dans son issue, avec ce qui a été essayé, et ne livre
aucun correctif au hasard (décision de l'auteur du 2026-10-28).

**Hors périmètre.** Le serveur, qui n'est pas la cause ; la stabilité des tests (EP-16).

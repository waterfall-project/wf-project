---
id: EP-17
titre: La maquette finie hors contrat — accessibilité des dialogues, mineurs des écrans, lenteur du navigateur, cosmétique
statut: en cours
depend_de: EP-16
famille: front
issue: 1547
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
  option A ; #784 ; #819, point 1 ; #1808), et les totaux gardés en vue à 911 points (#1209) —
  US-0710 ;
- l'écran d'un projet qui mène à sa révision (#1400) — US-0720 ;
- le Kanban filtré par libellé et par tâches prêtes, et l'accessibilité de sa carte (#1396,
  #1356), et la récapitulative qui n'attend plus que ses lignes propres, signalée au Kanban et au
  reste à engager (#1776) — US-0730 ;
- la matrice des risques sur fond blanc, la couleur sur les bulles, les seuls risques identifiés,
  pour sa part front (#1395), les mineurs de la matrice repliable (#1386), les libellés de la
  gravité (#1781) et le composant `Amount` de la vue du portefeuille (#1729) — US-0740 ;
- les grilles du projet, le Gantt et les chronologies : la projection sur `kinds` (#1397), l'export
  PNG du Gantt avec les noms des tâches (#1428), et leurs mineurs (#1421, #1539, #1144, #1424, #806,
  #819 points 4, 13, 14 et 15, #1699), et les gestes indisponibles sous un jalon (#1773) —
  US-0750 ;
- ce que le faux back n'applique pas, dit dans le guide et à l'écran (#1399) — US-0760 ;
- les commandes et les écritures retenues des composants partagés (#1364, #1377, #889, #1476,
  #1430, #1432, #901, #781, #1701, #1500, et le point 2 de #1384, #1568) — US-0770 ;
- l'administration, la session et le journal d'audit (#941, #942, #949, #951, #984, #990, #1005,
  #1010, #1012, #1021, #1023, #1024, #1180, #847, #963, #967, #1673, #1744) — US-0780 ;
- l'écran des révisions, le panneau de l'aide et l'outillage des tests (#1438, #1481, #902, #905,
  #846, #888, #1821, #1822, #1819, et la part de l'aide de #1804) — US-0790 ;
- les écrans du référentiel : les désactivés demandés sous la seule permission de modification
  (#1810), le plafond des colonnes conservées de la correspondance et son refus (#1567) — US-1010 ;
- le registre des risques filtré sur chacune de ses colonnes (#1787), et les lignes issues d'un
  risque survenu, filtrées, marquées et suivies jusqu'à la couverture (#1763) — US-1020 ;
- l'accueil qui retient aussi les projets créés (#1748) — US-1030 ;
- le compte rendu d'import qui lit ses commandes et présente l'état refusé (#1791) — US-1040 ;
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
    `EP-16`, rattachée à #1312 comme issue « contrat » que l'auteur tranche avant le gel ; EP-17 ne
    le reprend pas ;
  - #1533 — un refus à deux motifs sur le même champ ne dit que le premier (`byField`) : l'adoption
    par l'écran d'un exemple que le contrat d'EP-16 écrit (#817, point 2b), corrigé par US-0660/L3
    #1458 ; de même #1518 et #1524, corrigés par US-0660/L3 (décisions de l'auteur du 2026-10-27,
    confirmées le 2026-10-28), et #1525, reporté → EP-09 #1340 ;
- la stabilité des tests, qui relève d'EP-16 et jamais d'EP-17 (décisions de l'auteur des
  2026-10-25, 26 et 27, US-0590b à US-0590g) : la stabilité restante des parcours (#1263, #1145,
  #776, #1264) y est revenue le 2026-10-25 ; #1354 (`restore-dialog.dom.test.tsx` et
  `backup-deposit.dom.test.tsx` instables sous charge), d'abord dit « en EP-17 avec #1145 » le
  2026-10-23, y retourne au cadrage du 2026-10-28, titre et label `EP-16`, sous US-0590g #1543
  (décision de l'auteur du 2026-10-28) ;
- les navigateurs et les largeurs d'affichage de WF-CMP-0010 (US-0290, 1366 et 360 points) : EP-13.
  Les 911 points de #1209 ne sont pas une largeur d'US-0290 mais l'agrandissement de 150 % de
  WF-IHM-0100, et le constat reste ici (décision de l'auteur du 2026-10-28) ;
- le point 1 de #1384 (les exemples du contrat) : EP-16, US-0640/L6 et US-0660/L3 ; son point 2
  vient ici (« Constats reçus », US-0770), et son point 3, suivi par #1830, part à EP-08 ;
- toute écriture dans `docs/api`, même une remise en forme qui laisse le document lu identique : la
  définition de fini l'interdit à la branche de l'EPIC. Deux constats reçus en demandaient une
  (décisions du 2026-11-02, déléguées par l'auteur) : l'exemple `task_occurrence_succeeded` du point
  3 de #1384, suivi par #1830, est reporté → EP-08, où le succès de « Déclarer survenu » s'éprouve
  contre le service réel, comme #1714 ; le reflux des lignes longues du contrat (#1820) est écarté,
  aucune règle outillée ne fixant la largeur de `docs/api` ;
- ce que US-0704 (EP-16) a déjà fait des écrans de la revue du contrat : #1753 (les libellés de
  `NodeChange.subproject` et `cost_category`, et le test de la comparaison) et #1784 (le détail du
  risque écrit son identité et sa provision par `updateRisk` et `updateRiskProvision`,
  `update_provision` gouvernant la seule provision) sont sans objet, fermés avec leur raison ;
- le comportement réel des écrans : l'EPIC de leur domaine.

## Exigences réalisées

EP-17 ne clôt aucune exigence : il finit, contre le faux back, des écrans que l'EPIC de chaque
domaine servira et vérifiera en entier. Comme en EP-14 et en EP-15, chaque US cite les exigences
dont une phrase de Vérif tient côté front, et ses tests citent ces exigences ; les phrases qui
demandent le service sont des écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-RAE-0030-A` | Démarrage d’une tâche | début — close en EP-09 | US-0730 |
| `WF-PLA-0040-A` | Hiérarchie des tâches | début — close en EP-06 | US-0730 |
| `WF-RIS-0040-A` | Grille de suivi des risques | début — close en EP-08 | US-0740 |
| `WF-PLA-0080-A` | Grille de planning | début — close en EP-06 | US-0750 |
| `WF-PLA-0090-A` | Diagramme de Gantt | début — close en EP-06 | US-0750 |
| `WF-PLA-0050-A` | Jalons | début — close en EP-06 | US-0750 |
| `WF-PRJ-0020-A` | Lotissement | début — close en EP-04 | US-0750 |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | début — close en EP-04 | US-0780 |
| `WF-IHM-0140-A` | Aide en ligne | début — close en EP-11 | US-0790 |
| `WF-REF-0150-A` | Affichage des objets désactivés | début — close en EP-05 | US-1010 |
| `WF-RIS-0020-A` | États d’un risque | début — close en EP-08 | US-1020 |
| `WF-RIS-0050-A` | Réserve pour risques et couverture | début — close en EP-08 | US-1020 |
| `WF-RIS-0060-A` | Survenance d’un risque | début — close en EP-08 | US-1020 |

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
du service, US-0780) ; et, pour les écrans de ce que la revue du contrat du 2026-10-31 a changé, que
US-0704 (EP-16) a écrit au contrat : `listNodes` (`awaiting_own_lines`, US-0730 ; `is_from_risk`,
`origin_risk_ids`, US-1020), `listResourceRoles`, `listCostCategories` et `setActualCostMapping`
(US-1010), `listRisks` et `getProjectRiskCoverage` (US-1020), `listProjects` (US-1030), `getImport`,
`listImports`, `applyImport` et `abandonImport` (US-1040). Le diff de la branche de l'EPIC ne touche
aucun fichier de `docs/api`.

## Préalables

EP-16 livré, le contrat en 1.0.0. Les issues sont ouvertes depuis le 2026-10-28 (#1547) ; l'EPIC
reste `prêt` jusqu'à ce que l'auteur tire `epic/EP-17`, et passe alors `en cours` (décision de
l'auteur du 2026-10-28, « Conception »).

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
  totaux en vue (reçu d'EP-15 le 2026-10-20 ; gardé ici le 2026-10-28) ;
- #1808 — e2e : `tab-walk.ts` (le `finally` de `walkByTab`) et `indicators.spec.ts` avalent toute
  erreur par un `catch` global (relevé hors lot en EP-16 ; reporté ici par décision de l'auteur du
  2026-11-01 : aucune instabilité ne leur est attribuée, ce n'est pas un constat de stabilité).

**US-0720 — l'écran d'un projet.**

- #1400 — front : l'écran d'un projet mène directement à sa révision en cours (validation du
  2026-10-23) ; sans révision lisible, à la liste des révisions (décision de l'auteur du
  2026-10-28).

**US-0730 — le Kanban.**

- #1396 — front : le Kanban filtré par libellé et par tâches prêtes, la marque « prête à
  démarrer », le compteur de la colonne (validation du 2026-10-23) ; les filtres vivent dans
  l'adresse seule (décision de l'auteur du 2026-10-28) ;
- #1356 — front : l'annonce et le tiret de la carte du Kanban en attente de relecture (reçu d'EP-15,
  décision de l'auteur du 2026-10-23 ; titre `[EP-15]` à accorder) ;
- #1776 — front : signaler, au Kanban et dans la grille de reste à engager, la récapitulative qui
  n'attend plus que ses lignes propres (`TaskFacet.awaiting_own_lines`, WF-PLA-0040 ; revue du
  contrat du 2026-10-31, F-05, contrat #1774) ; la grille de reste à engager n'a pas d'US à elle, et
  le Kanban porte la carte.

**US-0740 — la matrice des risques.**

- #1395 — front : la matrice des risques sur fond blanc, la couleur sur les bulles, les seuls
  risques identifiés ; sa part contrat (le décompte de `cells`) est écrite par EP-16 (US-0700) ;
- #1386 — front : trois mineurs de la matrice repliable gardée ; son point 2 est **cosmétique** ;
- #1781 — front : les libellés de la gravité d'un risque, dans les réglages de la matrice et sur le
  graphique, disent « budget de référence » au lieu de l'assiette du projet (WF-REF-0160 ; relevé
  par US-0670/L3) ;
- #1729 — front : deux composants « Amount » aux propriétés différentes (`portfolio-views.tsx`, qui
  porte la vue des risques du portefeuille, et `components/amount.tsx`) ; reporté d'EP-16 à sa
  livraison (décision de l'auteur du 2026-11-01).

**US-0750 — les grilles du projet, le Gantt et les chronologies.**

- #1397 — front : la projection sur `kinds`, pour que la grille de planning, le planning d'un
  différentiel et la comparaison ne montrent pas les lignes de devis que le faux back rend ;
- #1428 — front : l'export PNG du Gantt porte une colonne des noms des tâches (option B de
  l'auteur, #1426) ;
- #1421 — front : la tenue de la légende des jours chômés dure un tick ;
- #1539 — front : la légende du Gantt rendue par le serveur, tenue jusqu'à l'hydratation et non
  « for a tick at most » ; aucun lot d'EP-16 n'a touché le Gantt, il revient donc à US-0750/L1 #1560
  (décision de l'auteur du 2026-10-28), avec #1421, qui touche le même code ;
- #1144 — front : la largeur mesurée de la barre des grilles denses n'est pas éprouvée au
  redimensionnement (décision de l'auteur du 2026-10-25 : EP-17, non repris par EP-15) ;
- #1424 — front : deux mineurs du test de provenance de l'écran des chronologies ;
- #806 — front : les mineurs de la relecture 1 de L44c, le lotissement dans sa grille ; son point 14
  relève de #803, corrigé en EP-16 ; ses points 11 et 15 sont **cosmétiques** ;
- #819, points 4, 13, 14 et 15 — front : la grille sous une recherche sans résultat, la lecture du
  lotissement en série, l'attente d'une action serveur trop large ; le point 15 est **cosmétique** ;
- #1699 — front : la garde locale du collage (`paste.ts`, `localRefusal`) refuserait en « colonne
  absente » un bloc qui traverse `is_critical`, que la grille de planning ne montre pas ; piste A
  retenue par l'auteur le 2026-10-31 — la garde ne refuse que si une cellule non vide du bloc tombe
  sur la colonne absente ;
- #1773 — front : « Indenter » sous un jalon et « Ajouter une sous-tâche » sur un jalon, présentés
  indisponibles d'avance avec leur condition (WF-PLA-0050, WF-IHM-0090 ; revue du contrat, F-04,
  contrat #1771). La grille ne les tente déjà plus (`structure-rules.ts`) : reste à les dire.

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
- #1384, points 2 et 3 — front : le libellé et l'icône de `ReferenceForm` pour « Réexaminer »
  (#1568 reprend le point 2) ; le succès de « Déclarer survenu », son message et `router.refresh`,
  non testé faute d'un exemple `task_occurrence_succeeded` de `GET /tasks/{id}` (point 3, reporté
  ici par décision de l'auteur du 2026-10-28). L'exemple modifierait le contrat figé : le point 3
  est suivi par l'issue « contrat » #1830, reportée → EP-08 le 2026-11-02 (voir « Ce qui n'en fait
  pas partie »), et EP-17 n'en garde rien. Le point 1 est corrigé en EP-16 ; l'issue porte le label
  `EP-17` depuis le 2026-11-01, et se ferme avec #1568 ;
- #1701 — front : l'historique des messages nomme une ligne de devis créée sans libellé d'après la
  ligne active (`structure-gestures.tsx`), comme le sujet de son refus — le même objet de `say(...)`
  que #1430 ;
- #1500 — doc : l'entrée n° 25 de `docs/dev/typescript.md`, la parenthèse sur `held(…)` et le
  renvoi à l'audit de #1491 ; **cosmétique**. Sa correction par une pull request de documentation
  vers `epic/EP-16` (décision de l'auteur du 2026-10-31) n'a pas été faite : `main` porte encore les
  deux phrases.

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
- #1673 — front : l'infobulle d'une inscription du journal perd l'instant de la sauvegarde
  restaurée (`audit-cells.tsx`) ; la même cellule que le `title` de #967, à corriger avec lui ;
- #1744 — front : la lecture de la session répétée dans le layout, et le titre d'axe en devise des
  graphiques des indicateurs et du portefeuille sans test ; son point 2 n'est pas de l'objet de
  l'US, mais un test de deux options ECharts, pris avec le point 1 pour ne pas couper l'issue ;
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
- #1821 — doc, front : `FBS-4.4.md` et `FBS-4.4.3.md`, dans les deux langues, nomment une colonne
  « Montant corrigé de l'inflation » que la grille de devis intitule « Montant réestimé », et
  `FBS-4.4.3.md` dit que le devis ne montre pas le montant réestimé (relevé par US-0670b #1811) ;
  c'est l'aide qui suit la grille, dont l'intitulé est le terme de la spécification (§3.2.5) ;
- #1822 — front : les incohérences du catalogue `en` — « Reste à engager », « Nouvelle nature »,
  « Cash-out by month », « Modify the schedule » (relevé par US-0670b #1811) ;
- #1819 — outil : trois copies de l'analyseur d'instants des exemples (`mockaudit.py`,
  `test_mockuniverse.py`, `test_mockhistory.py`) subsistent après #1708 (relevé par US-0640/L5
  #1333, transféré d'EP-16 le 2026-11-02) ; de l'outillage des tests et des exemples, sans effet sur
  le contrat : les exemples engendrés ne changent pas ;
- #1804 — spec : WF-IND-0040, l'avancement financier n'est pas le seul indicateur indépendant de la
  valeur acquise (reporté d'EP-16 à sa livraison, 2026-11-01). La modification de la spécification
  est à l'auteur, que nul lot n'écrit ; l'US ne prend que sa suite, la formulation reportée dans
  l'aide `FBS-4.8.1.md`, en français et en anglais, si l'auteur l'a intégrée avant le lot ;
- **cosmétiques** : #905 — des espaces insécables littéraux dans les tests du front ; #846 — le
  guide dit encore à venir la confirmation de #836 ; #888 — trois mineurs du tour 3 d'US-0350/L5b.

**US-0800 — la lenteur du produit.**

- #1230 — front : quitter un écran de grille de mille tâches coûte plusieurs secondes au navigateur
  (#1218) ; borné : la cause d'abord, un budget, un correctif à la cause (décision de l'auteur du
  2026-10-28).

**Reportés d'EP-16 à sa livraison (2026-11-01)**, label et titre `EP-17`, décision de l'auteur
du 2026-11-01 : #1729 est rangé sous US-0740, #1804 sous US-0790, #1810 sous US-1010.

**Décidés le 2026-11-02** (décisions déléguées par l'auteur) : #1830, le point 3 de #1384, reporté →
EP-08 et noté dans son fichier ; #1820, le reflux des lignes longues de `docs/api`, écarté et fermé
— aucune règle outillée ne fixe la largeur de ces fichiers, et le reflux toucherait `docs/api`, que
la définition de fini ferme à la branche de l'EPIC.

**US-1010 — les écrans du référentiel.**

- #1810 — front : les désactivés du référentiel demandés sous la seule permission de consultation,
  quand le contrat les réserve à `*.write` (WF-REF-0150 ; relevé par US-0704 #1735, comme C-01
  #1745) — les écrans des ressources et des coûts du référentiel, et le devis ;
- #1567 — front : la correspondance des coûts réels (`/reference/costs/actual-cost-mapping`) ne
  plafonne pas les colonnes conservées aux 50 du contrat et ne dit pas leur refus `VALUE_TOO_LONG`
  (relevé par US-0640/L2 ; reporté ici par décision de l'auteur du 2026-10-28).

**La revue du contrat du 2026-10-31.** Les écrans de ce que la revue du contrat a changé, tranché
par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), et les écrans viennent à
EP-17 (décision de l'auteur du 2026-11-01). Rangés le 2026-11-02 : chacun sous l'US qui porte déjà
son écran, sinon sous une US nouvelle ; deux sont sans objet.

- #1748 — le défaut de l'accueil retient aussi les projets créés : Créé, Chiffrage et En cours
  (D-01 ; contrat #1747) — US-1030 ;
- #1763 — les lignes issues d'un risque survenu : filtre, marque, et réestimé face au coût à la
  survenance (E-04 ; contrat #1761) — US-1020 ;
- #1773 — indenter ou créer une sous-tâche sous un jalon, indisponible d'avance (F-04 ; contrat
  #1771) — US-0750 ;
- #1776 — signaler les lignes propres ouvertes d'une récapitulative, au reste à engager et au Kanban
  (F-05 ; contrat #1774) — US-0730 ;
- #1787 — le registre des risques filtre chacune de ses colonnes depuis son adresse (H-01 ; contrat
  #1785) — US-1020 ;
- #1791 — le compte rendu d'import lit ses commandes et présente l'état `refused` (I-01, I-02 ;
  contrat #1789) — US-1040 ;
- #1753 — les libellés de `NodeChange.subproject` et `cost_category` dans la comparaison (E-01 ;
  contrat #1751) — **sans objet** : US-0704 a écrit les deux libellés, en français et en anglais, et
  `comparison-grid.dom.test.tsx` lit la ligne « Câblage sur site » qui change de sous-projet ;
- #1784 — le détail du risque écrit son identité et sa provision par deux opérations (H-02 ; contrat
  #1782) — **sans objet** : `writeRisk` (`api/actions/risks.ts`) écrit l'identité par `updateRisk`
  et la provision par `updateRiskProvision`, et `update_provision` gouverne la seule partie
  provision du formulaire (`risk-form.tsx`), depuis US-0704.

## Conception

EP-17 est un EPIC du front et de son harnais : il ne crée **aucune table ni migration**, ne touche
aucun module du noyau et **ne modifie pas le contrat** — ni opération, ni schéma, ni exemple ; le
faux back et le témoin restent ceux qu'EP-16 a figés en 1.0.0. Ce qui suit fixe ce que chaque lot
devrait sinon décider seul : les modules du front touchés, la forme du harnais étendu, l'ordre de
construction, et les décisions prises avec leur option écartée. Validée par l'auteur le 2026-10-28.

### Ce que le cadrage décide

- **Le découpage par objet** (décision de l'auteur du 2026-10-28) : une US par écran ou famille de
  composants, qui cite les exigences de domaine dont une phrase de Vérif tient côté front. Écarté :
  quatre US par nature — harnais, ajustements, mineurs, cosmétique —, dont chacune aurait cité
  toutes les exigences de tous les écrans, et dont les lots auraient touché les mêmes fichiers en
  même temps.
- **Aucune exigence close** : treize lignes « début — close en EP-nn » au tableau (sept au cadrage
  du 2026-10-28, six aux écrans de la revue du contrat le 2026-11-02), et trois exigences
  déjà closes (WF-IHM-0100-A, WF-IHM-0010-A, WF-IHM-0070-A) citées par une US avec tout leur Vérif,
  sans ligne au tableau, parce que `make roadmap` ferme toute portée qui ne commence pas par
  « début » et refuse une exigence close par deux EPIC. L'écart d'EP-14 sous WF-IHM-0100-A est noté
  levé dans le fichier d'EP-14, sous US-0200, par la pull request du cadrage — la seule retouche
  d'un EPIC livré. Écarté : ne rien écrire dans EP-14, où qui relit US-0200 ne saurait pas que
  l'écart est levé.
- **Ce qui sort** (décisions de l'auteur du 2026-10-28) : #1401 rendu à EP-16, parce que son point
  à trancher — un choix d'états gardé en préférence — demande le contrat, et qu'EP-17 ne tranche
  rien du contrat ; #1354 rendu à EP-16, avec US-0590g, par la règle « la stabilité des tests relève
  d'EP-16, jamais d'EP-17 » ; #1518, #1524 et #1533 corrigés par US-0660/L3 ; #1525 reporté → EP-09.
  Écarté pour #1401 : le garder ici en le bornant à l'adresse seule — ce qui aurait tranché, par
  omission, une question de contrat que l'auteur se réserve avant le gel.
- **#1209 reste ici** : 911 points est l'agrandissement de 150 % de WF-IHM-0100, pas une largeur de
  WF-CMP-0010 (US-0290, EP-13 : 1366 et 360). Écarté : EP-13.
- **Le harnais, option A, bornée** aux dialogues, aux menus et aux éditeurs de cellule, générique
  sur chaque écran (décision de l'auteur du 2026-10-28). Écartés : les dialogues et les menus seuls
  — les éditeurs de cellule sont ce que le clavier ouvre le plus souvent dans une grille — ; tout ce
  que #782 liste, les popovers de refus, les `<details>` fermés et les états atteints par un geste
  (`?import=`), qui demandent des parcours écrits un à un, et restent aux tests de composants, dits
  dans la note du guide.
- **Le parcours au clavier joue en sombre**, mesuré (#784, point 2) : la pull request donne la durée
  du fichier avant et après ; une étape qui dépasserait 10 % du chemin critique de la chaîne se dit,
  et l'auteur tranche (règle d'US-0590d). Écarté : écrire le manque, qui laisserait l'indicateur du
  focus jamais vu en sombre, le mode que la charte peint autant que le clair.
- **#1230 borné** comme US-0590f : la cause d'abord, 90 minutes de diagnostic, un correctif à la
  cause ; passé le budget, `question`. Écartés : la mesure seule, qui ferait deux lots ; l'écart,
  alors que `WORKING` à 15 s couvre une lenteur du produit que les parcours paient à chaque départ.
- **Le cosmétique se corrige dans le lot de son écran**, et le fichier garde la marque. Écartés : un
  lot à part, qui aurait touché dix fichiers de dix écrans en fin d'EPIC ; l'écart en bloc,
  contraire à la définition de fini.
- **Chaque lot qui change un écran retouche son aide** (`frontend/help/fr/<code>.md`), dans le même
  lot, sans relecture bloquante de l'auteur : des retouches, non un premier jet. Écartés : la
  relecture par l'auteur, le goulot d'US-0670, pour quelques phrases ; un lot d'aides en fin d'EPIC,
  qui laisserait des aides fausses entre deux.
- **#1400, sans révision lisible** : `/projects/P` mène à `/projects/P/revisions`. Écarté : garder
  l'écran du projet sous sa forme d'aujourd'hui pour ce seul cas, deux formes à maintenir.
- **#1396, l'adresse seule** : les filtres du Kanban vivent dans l'adresse, sans préférence.
  Écarté : `GridPreferences.filters` sous une clé `kanban` — le contrat ne changerait pas de forme,
  mais une lecture nouvelle du contrat s'y glisserait pendant qu'il est figé.
- **#1438, un lien** : « Déclarer un risque », disponible, mène à l'écran des risques. Écarté :
  `OfferedElsewhere`, qui retirerait de l'écran une commande que la révision liste.
- **#1024, le message mène au journal d'audit**. Écarté : relire la tâche au retour, une lecture de
  plus pour un cas rare.
- **#963, point 2** : une inscription `access_role_update` sans changement reçoit une phrase, comme
  l'attribution. Écarté : la cellule vide.
- **L'EPIC reste `prêt` après l'ouverture de ses issues** (décision de l'auteur du 2026-10-28) :
  le README lie `en cours` aux issues ouvertes, mais ses lots ne peuvent se livrer qu'EP-16 livré ;
  l'auteur le passe `en cours` quand il tire `epic/EP-17`. Écarté : `en cours` dès le cadrage, qui
  ferait lire un EPIC en travail alors qu'aucun lot ne peut partir.

**Les constats reçus après le cadrage** (reportés d'EP-16 du 2026-10-28 au 2026-11-02, rangés le
2026-11-02, à valider par l'auteur avec la pull request qui les range) :

- **Chacun sous l'US de son fichier**, dans un lot existant, sans lot nouveau : aucun ne fait passer
  son lot au-delà de la taille visée. Écarté : un lot de mineurs à part, qui toucherait en fin
  d'EPIC les fichiers des lots d'écran.
- **#1539, le commentaire dit vrai** : la légende est rendue par le serveur et tenue jusqu'à la
  mesure de l'axe, ce que #1421 fait tenir ; le commentaire de `GanttRows` le dit. Écarté : ne plus
  rendre la légende au serveur, qui déplacerait la grille dans l'autre sens sur les projets qui la
  gardent.
- **#1699, la piste A dès maintenant**, sur la garde de `paste.ts`, éprouvée par un test de la
  garde sur les colonnes de la grille de planning, sans câbler le collage sur cette grille. Écarté :
  attendre le lot qui câblera ce collage, qui laisserait le constat ouvert à la livraison, contre
  la définition de fini.
- **#1821, l'aide suit la grille** : « Montant réestimé » est le terme de la spécification (§3.2.5).
  Écarté : renommer la colonne d'après l'aide.
- **#1822, un terme, une traduction** : pour chaque terme, le lot retient celui que le catalogue
  emploie déjà le plus, et donne à deux commandes distinctes deux libellés distincts ; la pull
  request dit chaque choix. Écarté : un glossaire anglais à part, qui n'existe pas et que rien ne
  demande.
- **#1744 entier sous US-0780** : son point 2, un test du titre d'axe de deux graphiques, est pris
  avec le point 1. Écarté : couper l'issue entre deux US pour quelques lignes de test.
- **#1830, reporté → EP-08** (décision du 2026-11-02, déléguée par l'auteur) : le succès de
  « Déclarer survenu » s'éprouve contre le service réel, sans exemple ajouté au contrat figé, comme
  #1714 l'a fait pour `completed`. Écartés : l'exemple ajouté sur `main` par une pull request de
  contrat — une modification du contrat figé pour un seul test du front — ; une dérogation à la
  définition de fini d'EP-17, qui ferme `docs/api` à sa branche pour qu'il avance en parallèle des
  EPIC de domaine.
- **#1820, écarté** (même décision) : aucune règle outillée ne fixe la largeur de `docs/api`, et un
  reflux sans règle se défait au premier ajout. Écartés : un reflux sur `main` avec un contrôle de
  largeur, une règle nouvelle que rien ne demande ; une dérogation à la définition de fini.

**Les écrans de la revue du contrat du 2026-10-31** (rangés le 2026-11-02, décisions déléguées par
l'auteur) :

- **Sous l'US qui porte déjà l'écran, sinon une US nouvelle par écran** : #1773 sous US-0750 (la
  grille de planning), #1776 sous US-0730 (le Kanban, qui porte la carte ; la grille de reste à
  engager n'a pas d'US à elle) ; quatre US nouvelles — US-1010 le référentiel (#1810, #1567),
  US-1020 le registre des risques et les lignes issues d'un risque survenu (#1787, #1763), US-1030
  l'accueil (#1748), US-1040 le compte rendu d'import (#1791). Écartés : une US « de la revue du
  contrat », qui grouperait par origine contre le découpage par objet ; #1810 et #1567 sous US-0790,
  qui ne sont pas des mineurs sans écran ; les rendre à EP-05, contre le report décidé par l'auteur
  ; #1748 sous US-0720, dont l'écran n'est pas l'accueil.
- **#1753 et #1784, sans objet** : US-0704 les a faits en écrivant le contrat (le client régénéré
  ne compilait pas sans eux) ; ils se ferment avec leur raison. Écarté : les garder ouverts jusqu'à
  un lot qui n'aurait rien à y faire.
- **#1776, une part détachée d'US-0730** (`[US-0730b]`) : le lot unique d'US-0730 vise déjà 1 000
  lignes. Écarté : l'y ajouter, à 1 350 lignes, ou une US nouvelle pour une carte que le Kanban
  porte déjà.
- **#1763 et #1787, une US, deux lots** : le registre d'abord (ses filtres, dont les deux colonnes
  des survenus), puis les grilles filtrées sur un risque, leur marque, le lien du registre vers
  elles et la couverture. Écartés : un lot (environ 2 000 lignes) ; #1763 sous US-0750, dont les
  deux lots sont pleins, et qui couperait le constat entre deux US.
- **Le front trie ce que le contrat trie** : le registre trie par `severity`, `provision_amount` et
  `occurrence_cost` (`sort_by`), et filtre toutes ses colonnes de nombres, réestimé des survenus
  compris ; le réestimé n'est pas triable. Écarté : un tri du réestimé côté front sur la page lue,
  faux dès la deuxième page (WF-ARC-0020).
- **Les exigences citées** : WF-PLA-0040-A (US-0730), WF-PLA-0050-A (US-0750), WF-REF-0150-A
  (US-1010), WF-RIS-0020-A, WF-RIS-0050-A et WF-RIS-0060-A (US-1020), chacune « début — close » par
  l'EPIC de son domaine, la phrase qui tient côté front en critère, les autres en écart ;
  WF-IHM-0090 et WF-IHM-0130, dont aucune phrase de Vérif ne porte sur ces écrans, sont nommées dans
  les critères sans être citées. Écarté : citer WF-IHM-0090 (close par EP-02) pour US-1040, qui
  demanderait d'y vérifier des phrases sans rapport avec le compte rendu.

### Le harnais (US-0710)

Le harnais est celui d'EP-14 — `accessibility.spec.ts`, `axe.ts`, `tab-walk.ts`,
`focus-probe.ts`, `hydration.ts` —, étendu après qu'US-0590g (EP-16) a fait lire à `focus-probe.ts`
ses mesures par lots ; rien n'y est réécrit.

- **Ce qu'un geste ouvre.** Un module nouveau, `frontend/e2e/opened.ts`, trouve sur une page ce que
  le harnais doit ouvrir, et l'ouvre au clavier :
  - les déclencheurs de dialogue et de menu — `[aria-haspopup="dialog"]`, `[aria-haspopup="menu"]`,
    ce que Radix pose sur chaque `DialogTrigger` et `DropdownMenuTrigger` —, affichés et actifs,
    chacun ouvert par Entrée depuis le focus ; ce qui s'ouvre est le `[role="dialog"]` ou le
    `[role="menu"]` qui apparaît, attendu visible ;
  - les éditeurs de cellule : dans chaque `[role="grid"]` ou `[role="treegrid"]`, la première
    cellule saisissable — `[aria-readonly="false"]` ou ce que `DenseGrid` marque d'une cellule qui
    s'édite (`data-editable`, posé par le lot si rien ne la distingue encore) — reçoit le focus et
    F2 ; ce qui s'ouvre est l'éditeur qui prend le focus dans la cellule.
  - Chaque ouverture est un test à elle, nommé par l'écran et le déclencheur, en clair et en sombre,
    aux deux largeurs : un parcours au Tab borné à ce qui s'est ouvert (`walkByTab`, dont le piège
    voulu du modal est le retour au premier élément du dialogue, non de la page), un audit d'axe de
    ce qui s'est ouvert — la cellule, pour un éditeur —, auquel s'ajoute, sur le reste de la page,
    la seule règle dont l'ouverture change le verdict (`aria-hidden-focus` : un menu ou un dialogue
    modal cache la page au lecteur d'écran) — l'écran, que son propre audit juge, n'est pas audité
    de nouveau à chaque ouverture : la page entière coûtait huit secondes l'audit et dépassait le
    délai d'un test —, puis Échap, et le focus attendu sur le déclencheur ou sur la cellule. Un menu
    se parcourt aux flèches, pas au Tab : le test y vérifie l'entrée du focus, l'audit, et le
    retour.
  - Les déclencheurs se découvrent à l'ouverture de l'écran, et le test les joue l'un après l'autre
    dans un seul test par écran — un test par déclencheur ferait découvrir la page autant de fois
    qu'elle a de déclencheurs —, chaque échec dit à part (`expect.soft`, nommé par le déclencheur).
- **Ce qui reste hors du harnais**, écrit dans la note de l'US-0200 (EP-14, « Ce que les tests ne
  prouvent pas »), que le lot réécrit, et dans le guide (« L'accessibilité minimale de chaque
  écran ») : les popovers de refus, le contenu d'un `details` fermé, les états qu'un geste atteint, les
  dialogues qu'un geste ouvre sans bouton (`TimelineForm` et `GestureDialog` de
  `structure-gestures.tsx`, le collage de `paste-dialog.tsx` par Ctrl+V) — un garde-fou
  (`dialog-command-guard.test.ts`) fait échouer toute commande d'un dialogue qui ne dit pas
  `aria-haspopup="dialog"` hors de cette liste —, et la liste ou le popover qu'un éditeur rendrait
  dans un portail hors de la cellule (aucun éditeur d'aujourd'hui n'en rend un : l'audit d'un
  éditeur porte sur la cellule).
- **Le mode sombre** : le test du parcours au Tab reçoit `test.use({ colorScheme })` comme celui
  d'axe, un `describe` par mode ; la durée se relève par `--reporter=json` sur le fichier, avant et
  après, et s'écrit dans la pull request.
- **Les mineurs de #784** : un seul sélecteur des éléments atteignables, partagé par `hydration.ts`
  et `focus-probe.ts` (point 3) ; `untabbable` étendu aux rôles `button`, `link`, `checkbox` (point
  10) ; les résultats « incomplete » des autres règles d'axe annotés (point 8) ; l'écran de panne
  (`error.tsx`, `global-error.tsx`) ajouté à la note (point 11) ; les points 5, 9 et 14 écrits
  dans la note ; les points 1, 4, 6, 7, 12 et 13, cosmétiques, corrigés en passant.
- **#1808** : le `finally` de `walkByTab` ne rattrape que l'erreur de fermeture de la page, sous la
  forme qu'a établie le correctif de #1720 (« Test ended. », « Test timeout of …ms exceeded. »), et
  relance toute autre ; dans `indicators.spec.ts`, le `catch` qui évite un rejet non géré est gardé
  si `opened` est attendu sur tous les chemins, et un commentaire le dit, ou il se retire.
- **#819, point 1** : `dense-grid.tsx` distingue le focus d'une cellule refusée par un second
  trait — un anneau double, ou un contour en pointillé —, non par la seule couleur de l'anneau ; le
  parcours au Tab (`unmarked`) ne le juge pas, un test DOM le tient.
- **#1209** : sur le reste à engager, `remaining-summary.tsx` replie ses cartes en un résumé qui se
  déplie (`details`/`summary`, replié sous 1024 points, ouvert au-dessus) ; sur les coûts réels, la
  grille empilée reçoit un plafond de hauteur quand `max-h-svh` de `DenseGrid` ne suffit pas — la
  hauteur de la fenêtre moins ce qui la précède, mesurée par `frame-width.ts` ou son pendant — ;
  `grid-frame.spec.ts` remet 911 aux deux écrans (`CARD_SCREENS`), et son commentaire change.
  Écarté : réduire la hauteur des cartes, qui ne rendrait pas les 476 points du reste à engager.

### Le front

- **US-0720, l'écran du projet** : `app/projects/[projectId]/page.tsx` devient un renvoi
  (`redirect` de `next/navigation`, côté serveur) dès que `listRevisions` rend une révision :
  `R` = `Project.current_revision_id`, sinon `reference_revision_id`, sinon la plus récente des
  révisions marquées (`revisions.json` est trié du plus récent au plus ancien, US-0640/L4) ; une
  lecture de `R` refusée (403, 404) mène à `/projects/P/revisions`. L'adresse gardée passe par
  `contextAddress` (`navigation/context`). La page garde sa forme — `ProjectFacts`, `ProjectStart`,
  `ImportPart` — pour un projet sans révision, la section `Revisions` retirée. `?import=` : la page
  lit `readShownImport` avant de renvoyer ; un compte rendu d'un projet à révisions est renvoyé à
  `revisions/R/exchanges?import=…`, qui le montre déjà ; `screens.test.ts` ne range pas la page
  dans `REDIRECTS`, puisqu'elle ne fait pas que rediriger. Le chemin témoin (US-0080) et les
  parcours qui ouvrent `/projects/P` (`projects.spec.ts`, `navigation.spec.ts`, `opening.spec.ts`)
  attendent la révision. Les aides FBS-4 (le projet) et FBS-4.1 (les révisions) disent le renvoi.
- **US-0730, le Kanban** : `remaining/address.ts` lit deux paramètres de plus, `q` (le libellé) et
  `ready` (`1`) ; la page les passe à `Kanban`, qui filtre `columns` par `label` (insensible à la
  casse et aux accents, comme la recherche des grilles) et, pour la colonne `not_started`, par
  `predecessors_completed` ; un champ de recherche et une case « Tâches prêtes » au-dessus du
  tableau écrivent l'adresse (`router.replace`), comme la recherche des grilles. L'en-tête d'une
  colonne dont des cartes sont masquées dit « n sur N » dans son nom accessible. `CardTitle` porte
  la marque « prête à démarrer » (icône `CircleCheck` et texte) pour toute tâche `not_started` à
  `predecessors_completed`, à côté de celle du jalon. La sélection masquée est levée, `tabStop`
  revenant à la première carte visible. #1356 : le tiret de `CardReading` devient un espacement ;
  la région `status` est permanente, le bouton hors d'elle. L'aide FBS-4.5.3 décrit les filtres.
  **US-0730b** (#1776) : `CardTitle` porte, pour une tâche dont la lecture dit
  `awaiting_own_lines`, la marque « lignes propres ouvertes » de l'échelle commune (icône et texte,
  WF-IHM-0070) ; la grille de reste à engager (`remaining/`) marque la tâche et ses lignes propres
  hors provision de la même façon, une ligne de provision jamais ; le front ne déduit rien des
  subordonnées (WF-ARC-0020) ; tests de la grille et du Kanban sur `nodes_awaiting_own_lines`, aides
  FBS-4.5.2 et FBS-4.5.3.
- **US-0740, la matrice** : `risk-bubble-chart.tsx` ne colore plus les seize `markArea` (fond de la
  charte), garde `ZONE_STROKE` et les noms ; `STATE_STYLE` disparaît au profit d'une forme par zone
  (`palette.zones[point.zone]` pour la couleur, un symbole par zone) ; `shownPoints` ne garde que
  `identified`, quels que soient `states` ; la légende des états disparaît. Les deux écrans
  (`risks/page.tsx`, `portfolio/risks/page.tsx`) passent la matrice telle quelle. #1386 : le test
  du refus nomme le bouton par le catalogue, l'import est rangé, `useKeptWriter` reçoit `writeNow`.
  Cette US attend US-0700/L2 (EP-16) fusionné, qui met `cells` au compte des seuls identifiés. Les
  aides FBS-4.6 et celle de la vue des risques du portefeuille suivent. #1781 : les libellés de la
  gravité (`reference.riskMatrix.severity`, `reference.riskForm.severity`, ceux du graphique), en
  français et en anglais, disent l'assiette du projet (WF-REF-0160), un test les tenant ; le front
  ne calcule pas la gravité (WF-ARC-0020), il la lit. #1729 : le `Amount` local de
  `portfolio-views.tsx` cède la place à `components/amount.tsx`, ou prend un autre nom si leurs
  rendus diffèrent.
- **US-0750, les grilles du projet** : `projectNodes` (`grid/nodes.tsx`) reçoit `kinds` et écarte
  les nœuds d'un autre type avant `projectNode`, appelé par `grid-screen.ts` pour toute lecture qui
  passe `kinds` — le planning, le planning d'un différentiel ; la comparaison
  (`comparison-rows.ts`), qui ne demande aucun `kinds`, montre ses deux natures —, un test de page
  donnant une réponse mêlée. `gantt-image.ts` dessine une colonne des noms à gauche (`ROW` par
  ligne, l'indentation par niveau, la largeur de la colonne mesurée au texte le plus long, bornée),
  comptée dans `sizeOf` et donc dans `ganttOverflow`. `gantt.tsx` tient la légende jusqu'au signal
  de mesure de l'axe (#1421), et le commentaire de `GanttRows` dit qu'elle est rendue par le
  serveur et tenue jusque-là, hydratation comprise (#1539). `frame-width.ts` est éprouvé par un
  `setViewportSize` dans `grid-frame.spec.ts` (#1144). Le lotissement (#806) : `breakdown-edits.ts`
  n'envoie rien quand l'élément visé manque et le dit, attribue un refus pointé sur l'élément même
  ; `settings-grid.tsx` dit « Aucun poste » ; les tests manquants s'écrivent. #819 : la grille sous
  une recherche sans résultat (point 4), la lecture du lotissement dans le `Promise.all` (13), le
  filtre de `waitForRequest` sur `next-action` (14). #1699 : `localRefusal` (`paste.ts`) ne refuse
  « colonne absente » que si une cellule non vide du bloc tombe sur une colonne que la grille ne
  configure pas, un test de la garde sur les colonnes de la grille de planning (`is_critical` entre
  `total_float` et `started_on`). #1773 : `structure-rules.ts`, qui ne place déjà rien sous un
  jalon (`byLevel`, `createdOn`), rend « Indenter » et « Ajouter une sous-tâche » indisponibles
  avec leur condition au lieu de les taire, par la forme des gestes indisponibles de la grille
  (WF-IHM-0090) ; le refus `MILESTONE_HAS_NO_SUBTASK`, déjà au catalogue, est éprouvé sur un
  collage et dans un compte rendu d'import. Les aides touchées, FBS-4.3.2 (gestes) et FBS-4.3.3
  (export), le disent.
- **US-0760, le faux back dit** : `docs/dev/README.md` reçoit « Ce que le faux back ne fait pas »
  sous « Le faux back », et les mentions des lignes 984 et 1228 y renvoient. `MockupNotice` reçoit
  une prop `lists?: boolean` : posée par les pages de listes et de grilles, elle ajoute la phrase
  `mockup.notFiltered` à la note existante — une seule note par écran, sous l'en-tête. Écarté : une
  seconde note par écran.
- **US-0770, les commandes** : `confirmed-command.tsx` passe `offer` indisponible pendant l'écriture
  (`busy`, l'état local d'US-0590d/L3) ; `risk-detail.tsx` garde le dernier refus de « Modifier »
  par identifiant de risque, dans un état du détail et non de l'instance affichée ;
  `role-commands.tsx`, `permission-matrix.tsx`, `user-commands.tsx` passent par `useHeldCommand` ou
  `list.held` ; `held-writes.ts` et `commands/held.ts` : un refus dit par la barre est marqué dit,
  et l'écran revenu par « Suivant » ne le redit pas (#1476, point 1), le guide gagne sa phrase
  (point 2), `shell.spec.ts` son commentaire (point 3) ; `say(...)` sans objet instruit un à un
  (#1430) ; `cell-writes.ts` fait passer `clear` par `current` (#1432) ; `reactivation.tsx` purge
  `reported` à chaque génération (#901) ; `held()` partout (#781), et l'entrée n° 25 de
  `docs/dev/typescript.md` dit « avec `held(…)` quand la commande l'emploie » et la propriété qui
  rend un fichier sans objet, à la place du renvoi à #1491 (#1500, décision de l'auteur du
  2026-10-31) ; `reference-form.tsx` reçoit une prop `icon` et un libellé par cas, sans ternaire
  (#1384, point 2) ; `structure-gestures.tsx` passe à `send` un libellé indéfini pour une ligne
  créée sans nom, l'historique et le sujet d'un refus ne nommant plus la ligne active (#1701).
- **US-0780, l'administration** : `user-dialogs.tsx` et les catalogues
  (`admin.users.anonymizationFinal`) pour #942 ; `user-cells.tsx` (`StateSwitch`) lit
  `writes.linking` pour #949 ; `UserWrites.run` dit le refus d'une ligne occupée (#941) ;
  `audit-filters.tsx` lit par `getUser` l'auteur choisi absent (#1010) ; `session/request.ts` passe
  par `accountRefusalOf` de `problem-kind.ts` (#1005) ; l'effacement de `wf_messages` et
  `wf_background_tasks` se fait dans un seul endroit, appelé à la déconnexion comme à toute fin de
  session constatée — `signed_out` reçu, ou un compte différent de celui qui a écrit (l'identifiant
  du compte gardé avec les magasins) — (#1180) ; `maintenance.tsx` mène au journal (#1024) ;
  `restoration.tsx` ne rend pas « en attente » en phase `failed` (#1023) ; les tests et le parcours
  du service (#984, #847, #1021, #963, #967) ; `admin/users/page.tsx` renomme `PERIOD_REFUSED`
  (#1012). `audit-cells.tsx` compose le `title` de la cellule de l'action instant de la sauvegarde
  restaurée compris, posé seulement quand le texte est tronqué (#967), et passe `taken` après un
  garde de type, sans repli `""` (#1673). `app/layout.tsx` lit la session une fois, dans une
  variable réemployée, et le titre d'axe en devise de `curve-series-chart.tsx` et
  `portfolio-charts.tsx` est éprouvé avec et sans devise (#1744). Les aides de l'administration
  touchées suivent.
- **US-0790** : `commands/object-commands.tsx` rend `declare_risk` par un `Link` vers
  `functionHref(functionOf("risks"), context)` quand il est disponible, indisponible sinon avec sa
  condition (#1438), et l'aide FBS-4.1 retire sa phrase ; `help-panel.tsx` prend Échap par
  `onEscapeKeyDown` du `SheetContent`, filtré sur le champ de recherche et sur une requête
  `query` non vide (`event.preventDefault()`), Radix écoutant Échap sur le document, en capture
  (#1481) ; `outcome-notice.dom.test.tsx` simule `next/navigation` (#902) ; la règle
  `no-irregular-whitespace` avec `skipStrings: false` sur `**/*.test.ts?(x)` et `**/*.spec.ts` (#905) ; #846 et #888.
  Les aides du devis, `FBS-4.4.md` et `FBS-4.4.3.md`, dans les deux langues, nomment la colonne
  « Montant réestimé » et ne disent plus que le devis ne le montre pas (#1821) ; `messages/en.json`
  rend chaque terme d'une seule façon et deux commandes distinctes par deux libellés, les pages de
  `frontend/help/en/` qui les citent suivant (#1822, le test des libellés en gras de `help.test.ts`
  les relève) ; `mockaudit.py`, `test_mockuniverse.py` et `test_mockhistory.py` lisent leurs
  instants par `wftools.mockproject.moment` — la forme datée seule de `test_mockhistory.py` gardée
  par un appel à part —, les exemples engendrés inchangés, `make mock-data-up-to-date` au vert
  (#1819) ; `FBS-4.8.1.md`, dans les deux langues, reprend la formulation de WF-IND-0040 si l'auteur
  l'a intégrée avant le lot, sinon #1804 reste ouvert à sa seule part de la spécification.
- **US-1010, le référentiel** : `inactiveQuery` (`reference/resources/page.tsx`,
  `reference/costs/page.tsx`) et `referenceQuery` (le devis) demandent les désactivés sous
  `resource_settings.write` et `cost_settings.write`, comme le contrat (C-01, #1745), et la case
  « Afficher les désactivés » n'est pas présentée sans eux ; un test par écran avec un compte de
  consultation seule. `actual-cost-mapping.tsx` lit le plafond des colonnes conservées de la
  validation du contrat (`maxItems`, par le client engendré ou une constante qui cite le schéma,
  éprouvée contre lui) et tient « Déclarer une colonne conservée » indisponible au-delà, avec sa
  condition ; le refus `VALUE_TOO_LONG` sur `/kept_columns` se dit sous la liste, son test réécrit.
  Aides FBS-3.1, FBS-3.1.3 et FBS-3.2.
- **US-1020, le registre et les survenus.** L1 : `risks/address.ts` lit `zones`, les bornes
  `<colonne>_min` et `<colonne>_max` de chaque colonne de nombres (probabilité, gravité, provision,
  coût à la survenance, réestimé des survenus) et la période `last_review_on_from` /
  `last_review_on_to`, par `boundNames` et `period-filter.tsx` comme les autres grilles ; le
  registre (`risk-grid.tsx`) gagne la colonne du réestimé des survenus
  (`occurred_reestimated_amount`) et ses filtres de colonne ; un raccourci « Non réexaminés depuis
  le dernier marquage » pose `last_review_on_to` à la date du dernier marquage (WF-RIS-0020) ; aide
  FBS-4.6.1. L2 : `grid-screen.ts` passe `is_from_risk` et `origin_risk_ids` de l'adresse à
  `listNodes` pour le planning et le devis, un filtre « Issues d'un risque » et le choix d'un risque
  survenu dans la barre de la grille ; une marque discrète sur une tâche ou une ligne dont la
  lecture porte `origin_risk_id`, qui nomme le risque ; le registre mène d'un survenu à la grille
  filtrée sur lui ; `risk-coverage.tsx` présente `occurred_reestimated` en regard de
  `occurred_cost`, comme une information, hors de l'écart ; aides FBS-4.3, FBS-4.4, FBS-4.6.1 et
  FBS-4.6.2.
- **US-1030, l'accueil** : `DEFAULT_STATES` (`navigation/home.ts`) devient `["created", "pricing",
  "in_progress"]`, dans l'ordre du contrat, sa docstring le dit ; un choix gardé (`filters.states`)
  prime toujours ; les tests de l'accueil et le parcours qui l'ouvre attendent les trois états, et
  le projet créé se lit par `projects_with_created`. Aide FBS-4 (l'accueil).
- **US-1040, le compte rendu d'import** : `import-report.tsx` lit « Appliquer » et « Abandonner »
  dans `Import.available_commands` (`findOffer`), indisponibles avec leur condition
  (`import_awaiting_decision`, `import_not_applied`, déjà au catalogue) ; `IMPORT_STEPS` et
  `stepsOf` (`offers.ts`) disparaissent, et leur commentaire avec ; l'état `refused` a son
  explication (« refusé à l'application, le fichier est supprimé ; relancez l'import ») sur le
  compte rendu et dans le journal des imports ; tests du compte rendu et du journal. Aide FBS-4.3.4
  (imports et exports).
- **US-0800** : la mesure se prend au Performance panel ou par `page.evaluate(performance.now)`
  autour de la navigation, sur le planning de mille tâches ; les pistes — le démontage de
  `DenseGrid` (mille lignes de cellules, chacune avec ses gestionnaires), le recalcul des styles au
  retrait de la feuille de la grille, le payload RSC gardé par le routeur — se départagent par la
  mesure, aucune n'est posée comme cause ; `workload.spec.ts` et `screens.spec.ts` ne changent
  qu'après.

### L'ordre de construction

1. **US-0710 en tête** : le harnais étendu garde ensuite chaque lot d'écran, comme en EP-14 ; son
   premier lot est le harnais, son second #1209 et #819.1.
2. **Les ajustements de la validation** : US-0720, US-0730, US-0740 (après US-0700/L2 d'EP-16, ce
   qui est acquis à la livraison d'EP-16), US-0750, US-0760, dans cet ordre, chacun sous le harnais.
3. **Les mineurs** : US-0770 puis US-0780, qui touchent des composants partagés et des écrans que
   les lots précédents ne touchent pas ; US-0790 en parallèle.
4. **Les écrans de la revue du contrat** : US-0730b après US-0730 ; US-1010, US-1030 dès le
   harnais ; US-1020/L1 après US-0740 (le même écran des risques), US-1020/L2 après US-1020/L1
   et US-0750/L1 (`grid-screen.ts`) ; US-1040 après US-0720 (le renvoi de `?import=`).
5. **US-0800 en dernier**, quand les grilles ne bougent plus, pour mesurer sur ce qui sera livré.

---

## US-0710 — Le harnais d'accessibilité parcourt les dialogues, les menus et les éditeurs

- **statut** : fini
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** : #1548

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
  point 1) ;
- propre à l'US : `walkByTab` et `indicators.spec.ts` ne rattrapent que l'erreur de fermeture de la
  page, ou disent dans le code pourquoi leur `catch` est sûr (#1808).

**Notes de réalisation.** Le harnais est celui d'EP-14 (`accessibility.spec.ts`, `axe.ts`,
`tab-walk.ts`, `focus-probe.ts`), que l'US étend sans le réécrire ; US-0590g (EP-16) y lit les
mesures par lots avant que cette US ne commence. Les popovers de refus, les `<details>` fermés et
les états atteints par un geste (`?import=`) restent aux tests de composants et s'écrivent dans la
note du guide (décision de l'auteur du 2026-10-28). Le coût de chaîne se mesure contre la règle
d'US-0590d : une étape qui dépasserait 10 % du chemin critique se dit dans la pull request.
- L1 (#1558) : les dialogues du front s'ouvrent par un état, non par un `DialogTrigger` ; chaque
  commande qui en ouvre un pose donc elle-même `aria-haspopup="dialog"`, que le harnais lit. Ce
  qu'un geste ouvre est audité par axe en lui-même, et le reste de la page par `aria-hidden-focus`
  seule : la page entière auditée à chaque ouverture dépassait le délai d'un test sur le Kanban et
  le référentiel (huit secondes l'audit). Les écarts relevés et corrigés : les menus déroulants
  modaux (`aria-hidden-focus`, rendus non modaux), le dialogue d'alerte qui ne se disait pas modal
  (`aria-modal`), le premier champ d'un dialogue long atteint hors de la vue (WCAG 2.4.11, le
  dialogue défile au focus), la cellule en saisie restée cible autour de son champ (`target-size`).

**Hors périmètre.** Les navigateurs et 360 points (US-0290, EP-13) ; une conformité déclarée (§2.2).

---

## US-0720 — L'écran d'un projet mène à sa révision

- **statut** : fini
- **exigences** : `WF-IHM-0010-A`
- **opérations** : `getProject`, `listRevisions`
- **issue** : #1549

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

- **statut** : fini
- **exigences** : `WF-RAE-0030-A`, `WF-IHM-0070-A`, `WF-PLA-0040-A`
- **opérations** : `listStartableTasks`, `listNodes` (la grille de reste à engager, US-0730b)
- **issue** : #1550

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
- propre à l'US : l'aide du Kanban décrit les filtres et la marque ;
- écart : `WF-PLA-0040-A` — « Après déplacement d’une récapitulative portant deux niveaux de
  subordonnées, les tâches et les lignes déplacées sont inchangées, et le devis totalise le même
  montant. » : du service ; EP-06 clôt.
- écart : `WF-PLA-0040-A` — « Les dates et l’état d’une récapitulative ne sont pas saisissables. » :
  le refus est du service, et la grille de planning ne change pas ici ; EP-06 clôt.
- écart : `WF-PLA-0040-A` — « Une récapitulative dont une subordonnée est démarrée est démarrée ;
  elle n’est terminée qu’après la dernière. » : l'état est calculé par le service ; EP-06 clôt.
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont une
  ligne propre porte un reste à engager de 500 est démarrée et signalée ; la saisie d’un reste nul
  sur cette ligne la termine. » : la carte du Kanban d'une tâche dont la lecture dit
  `awaiting_own_lines`, et dans la grille de reste à engager la tâche et ses lignes propres hors
  provision, portent la marque « lignes propres ouvertes » de l'échelle commune, lisible sans
  couleur, sur l'exemple `nodes_awaiting_own_lines` ; le front ne la déduit pas des subordonnées
  (WF-ARC-0020), et la terminaison par la saisie d'un reste nul est du service, EP-06 clôt (#1776) ;
- écart : `WF-PLA-0040-A` — « La suppression de la seule subordonnée d’une récapitulative de dix
  jours laisse une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être
  ajoutée. » : du service ; EP-06 clôt.
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont la
  seule ligne propre est une provision de 40 est terminée et n’est pas signalée. » : une ligne de
  provision n'est jamais marquée, et une tâche que la lecture ne dit pas `awaiting_own_lines` ne
  l'est pas ; l'état est du service, EP-06 clôt (#1776) ;
- écart : `WF-PLA-0040-A` — « Une récapitulative dont la seule subordonnée est un jalon terminé et
  dont une ligne propre garde un reste à engager, privée de ce jalon, est une feuille démarrée d’un
  jour, non un jalon. » : du service ; EP-06 clôt.
- écart : `WF-PLA-0040-A` — « Une récapitulative terminée dont la seule subordonnée, un jalon, est
  déplacée devient un jalon terminé. » : du service ; EP-06 clôt.
- propre à l'US : les aides du reste à engager et du Kanban disent la marque (#1776).

**Notes de réalisation.** Trois colonnes, les états d'une tâche : une quatrième colonne « Prêtes »
est écartée par l'auteur (#1396). `predecessors_completed` est déjà rendu (`NotStartedTask`) ; le
contrat ne change pas. #1776, venu de la revue du contrat du 2026-10-31, se livre dans une part
détachée, `[US-0730b]`, après le lot unique : celui-ci vise déjà 1 000 lignes.

**Hors périmètre.** Un filtre gardé en préférence ou en session ; le glisser-déposer, inchangé.

---

## US-0740 — La matrice des risques sur fond blanc

- **statut** : fini
- **exigences** : `WF-RIS-0040-A`, `WF-IHM-0070-A`
- **opérations** : `getProjectRiskMatrix`, `getPortfolioRisks`
- **issue** : #1551

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
- propre à l'US : les libellés de la gravité, dans les réglages de la matrice et sur le graphique,
  disent l'assiette du projet, en français et en anglais (#1781) ; la vue du portefeuille n'a plus
  deux composants nommés `Amount` (#1729) ;
- propre à l'US : l'aide de l'écran des risques et celle de la vue des risques du portefeuille
  décrivent la matrice ainsi.

**Notes de réalisation.** La décision de l'auteur du 2026-10-23 dans #1395 fait foi ; le graphique
est partagé (`risk-bubble-chart.tsx`) entre les deux écrans. Cette US ne commence qu'US-0700/L2
(EP-16) fusionné : le décompte de `cells` lui vient du contrat.

**Hors périmètre.** Les axes (#1253 tient) ; le décompte lui-même (EP-16).

---

## US-0750 — Les grilles du projet, le Gantt et les chronologies

- **statut** : fini
- **exigences** : `WF-PLA-0080-A`, `WF-PLA-0090-A`, `WF-PRJ-0020-A`, `WF-PLA-0050-A`
- **opérations** : `listNodes`, `compareRevisions`
- **issue** : #1552

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
  un tick, et le code dit qu'elle est rendue par le serveur (#1421, #1539) ; la largeur mesurée de
  la barre des grilles denses est éprouvée au redimensionnement, et la largeur minimale de la
  recherche comparée aux minimales mesurées (#1144) ;
- propre à l'US : les mineurs du lotissement dans sa grille (#806, points 1 à 3, 5 à 10, 12, 13, 16)
  sont corrigés — une écriture dont l'élément visé manque à la lecture de départ n'est pas envoyée
  et le dit ; un refus pointé sur l'élément lui-même lui est attribué ; une suppression refusée est
  éprouvée ; un lotissement vide dit « Aucun poste » — et les mineurs des tests du planning et des
  chronologies (#819, points 13 et 14 ; #1424) ;
- propre à l'US : la garde locale du collage ne refuse une colonne absente que si une cellule non
  vide du bloc y tombe, éprouvé sur les colonnes de la grille de planning, `is_critical` comprise
  (#1699, piste A) ;
- `WF-PLA-0050-A` — « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. » : la grille
  de planning présente indisponibles, avec leur condition (WF-IHM-0090), « Indenter » quand la tâche
  qui précède est un jalon et « Ajouter une sous-tâche » sur un jalon, d'après `is_milestone` que la
  lecture rend ; le refus `MILESTONE_HAS_NO_SUBTASK` d'un collage ou d'un import dit son message
  (#1773) ;
- écart : `WF-PLA-0050-A` — « Une récapitulative dont la seule subordonnée est un jalon a une durée
  nulle et reste une récapitulative. » : du service ; EP-06 clôt.
- écart : `WF-PLA-0050-A` — « Un jalon portant une ligne de devis passe de non démarré à terminé par
  la saisie d’un reste à engager nul ; un jalon sans ligne est terminé depuis le Kanban. » : la
  transition est du service, et le Kanban ne change pas ici ; EP-06 clôt.
- écart : `WF-PLA-0050-A` — « La terminaison depuis le Kanban d’un jalon portant une ligne est
  refusée en renvoyant à la saisie de son reste à engager. » : le refus est du service ; EP-06 clôt.
- écart : `WF-PLA-0050-A` — « Un jalon qui ne porte qu’une ligne de provision est terminé depuis le
  Kanban. » : la transition est du service ; EP-06 clôt.
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

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1553

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

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune en propre
- **issue** : #1554

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
  `Save`, sans quatrième branche au ternaire (#1384, point 2) ;
- propre à l'US : une ligne de devis créée sans libellé est inscrite à l'historique des messages, et
  nommée dans le sujet de son refus, sans le libellé de la ligne active (#1701) ;
- propre à l'US : l'entrée n° 25 de `docs/dev/typescript.md` ne dit `held(…)` que là où la commande
  l'emploie et nomme la propriété qui rend un fichier sans objet (#1500).

**Notes de réalisation.** US-0590d (EP-16) a posé la forme des commandes en ligne — un état
« occupé » local, levé dans la même mise à jour que la réponse (option B de #1491, défaut n° 25) —
et celle des dialogues modaux — la transition imbriquée ; cette US s'y tient, et le défaut n° 24
du guide se relit à sa lumière.

**Hors périmètre.** `byField` et ses deux motifs (#1533, EP-16).

---

## US-0780 — L'administration, la session et le journal d'audit

- **statut** : fini
- **exigences** : `WF-ADM-0060-A`
- **opérations** : `getUser`, `deleteAccessRole`
- **issue** : #1555

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
  posé que si le texte est tronqué (#967), et il porte alors l'instant de la sauvegarde restaurée
  (#1673) ; la documentation de la page des comptes dit tout refus 422 (#1012) ;
- propre à l'US : le layout lit la session une fois (#1744, point 1), et le titre d'axe en devise
  des graphiques des indicateurs et du portefeuille est éprouvé, avec et sans devise (point 2) ;
- propre à l'US : les aides de l'administration touchées (les comptes, le journal, les sauvegardes)
  sont retouchées.

**Notes de réalisation.** Les écritures de la table des comptes retenues à la navigation sont dans
US-0770 (#889). Les constats viennent d'EP-03, reportés trois fois ; chaque point se relit d'abord
sur `epic/EP-16` livré, et un point que la livraison a rendu sans objet se ferme avec sa raison.

**Hors périmètre.** Le service d'anonymisation (EP-04) ; le suivi de la tâche `restore` par le
suivi des tâches.

---

## US-0790 — L'écran des révisions, le panneau de l'aide et l'outillage des tests

- **statut** : fini
- **exigences** : `WF-IHM-0140-A`
- **opérations** : aucune en propre
- **issue** : #1556

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
  de #888 sont corrigés ;
- propre à l'US : l'aide du devis, en français et en anglais, nomme la colonne comme la grille,
  « Montant réestimé », et ne dit plus que le devis ne le montre pas (#1821) ; le catalogue anglais
  traduit chaque terme d'une seule façon et deux commandes distinctes par deux libellés distincts,
  les aides anglaises qui les citent suivant (#1822) ;
- propre à l'US : aucune copie de l'analyseur d'instants des exemples ne reste dans `tools/` hors de
  `wftools.mockproject.moment`, et les exemples engendrés ne changent pas (#1819) ;
- propre à l'US : si l'auteur a intégré la reformulation de WF-IND-0040 avant le lot, l'aide de
  l'avancement financier la reprend, dans les deux langues (#1804).

**Notes de réalisation.** Le panneau de l'aide est celui d'US-0670/L1 (`help-panel.tsx`, Radix) :
Échap y est pris par le dialogue, et le champ doit le prendre avant.

**Hors périmètre.** La rédaction des aides (US-0670, EP-16).

---

## US-1010 — Les écrans du référentiel demandent ce que le contrat leur accorde

- **statut** : fini
- **exigences** : `WF-REF-0150-A`
- **opérations** : `listResourceRoles`, `listCostCategories`, `getActualCostMapping`,
  `setActualCostMapping`
- **issue** : #1833

**En tant qu'**administrateur du référentiel ou lecteur de ses listes, **je veux** que les écrans
du référentiel ne demandent les objets désactivés que si j'ai le droit de les voir, et que la
correspondance des coûts réels me dise d'avance combien de colonnes elle conserve, **afin de** ne
pas tomber sur un refus que l'écran aurait pu éviter (#1810, #1567).

**Critères d'acceptation.**

- `WF-REF-0150-A` — « Un objet désactivé n’apparaît pas dans la liste par défaut, apparaît lorsque
  l’affichage des objets désactivés est demandé, et peut y être réactivé. » : l'affichage des
  désactivés n'est présenté et demandé qu'à un compte qui porte la permission de modification de la
  fonction (`resource_settings.write`, `cost_settings.write`), comme le contrat le réserve (C-01,
  #1745) ; un compte de consultation seule ne le demande ni sur l'écran des ressources, ni sur celui
  des coûts, ni dans le devis, éprouvé par un test par écran (#1810) ; le service, qui filtre et
  réactive, est d'EP-05, qui clôt ;
- propre à l'US : la correspondance des coûts réels tient « Déclarer une colonne conservée »
  indisponible, avec sa condition, au plafond que le contrat fixe (50, `maxItems`, lu du contrat et
  non écrit en dur), et dit sous la liste le refus `VALUE_TOO_LONG` de `/kept_columns` ; le test qui
  figeait la phrase de l'enveloppe est réécrit (#1567) ;
- propre à l'US : les aides des paramètres de coûts, de la correspondance et des paramètres de
  ressources sont retouchées.

**Notes de réalisation.** Le défaut de #1810 est antérieur à US-0704, qui a écrit la règle au
contrat ; le front ne fait que s'y tenir. Le faux back rend les désactivés quelle que soit la
permission (US-0760) : les tests portent sur la requête que la page fait, non sur la réponse.

**Hors périmètre.** Le filtrage et la réactivation par le service (EP-05).

---

## US-1020 — Le registre des risques filtré, et les lignes issues d'un risque survenu

- **statut** : à faire
- **exigences** : `WF-RIS-0020-A`, `WF-RIS-0050-A`, `WF-RIS-0060-A`
- **opérations** : `listRisks`, `getProjectRiskCoverage`, `listNodes`
- **issue** : #1834

**En tant que** chef de projet, **je veux** filtrer le registre des risques sur chacune de ses
colonnes, retrouver à la revue les risques que je n'ai pas réexaminés, et suivre un risque survenu
jusqu'aux tâches et aux lignes qu'il a fait naître, **afin de** mesurer sa dérive sans recompter à
la main (#1787, #1763).

**Critères d'acceptation.**

- écart : `WF-RIS-0020-A` — « Les transitions entre identifié et écarté sont possibles dans les deux
  sens. » : constaté par EP-15 (US-0520), inchangé ici ; EP-08 clôt.
- écart : `WF-RIS-0020-A` — « Toute transition depuis l’état survenu est refusée. » : idem ; EP-08
  clôt.
- écart : `WF-RIS-0020-A` — « La suppression d’un risque cité par une révision marquée est
  refusée. » : idem ; EP-08 clôt.
- `WF-RIS-0020-A` — « La revue périodique présente les risques dont la probabilité n’a pas été
  réexaminée. » : un raccourci « Non réexaminés depuis le dernier marquage » du registre pose
  `last_review_on_to` à la date du dernier marquage, dans l'adresse ; le serveur filtre (#1787) ;
- écart : `WF-RIS-0020-A` — « Après abandon d’une révision en cours où un risque a été créé, un
  autre réexaminé et un troisième déclaré survenu, le premier n’existe plus, le second présente la
  probabilité et l’état de la dernière révision marquée, et le troisième est identifié, avec sa
  provision et sans coût à la survenance. » : du service ; EP-08 clôt.
- écart : `WF-RIS-0050-A` — « Sur un projet chiffré à 1 000 portant un risque de gravité 200 à 30 %,
  le devis totalise 1 060, le budget de référence 1 000 et la réserve 60. » : du service ; EP-08
  clôt.
- écart : `WF-RIS-0050-A` — « Après survenance de ce risque, réévalué à 250, le budget de référence
  vaut toujours 1 000, les provisions restantes 0, le coût des survenus 250, et l’écart de
  couverture −190. » : idem ; EP-08 clôt.
- écart : `WF-RIS-0050-A` — « Sur le même projet, un second risque de provision 40 présent dans la
  référence porte la réserve à 100 ; l’écarter fait passer les provisions restantes de 40 à 0 sans
  toucher le budget de référence, et l’écart de couverture de −190 à −150. » : idem ; EP-08 clôt.
- écart : `WF-RIS-0050-A` — « Sur un projet dont la réserve est nulle et sans risque survenu, un
  risque identifié après la référence, de provision 30, porte les provisions restantes à 30 et
  l’écart de couverture à −30. » : idem ; EP-08 clôt.
- écart : `WF-RIS-0050-A` — « La terminaison des tâches issues d’un risque survenu ne change ni le
  coût des survenus ni l’écart de couverture. » : idem ; EP-08 clôt.
- écart : `WF-RIS-0050-A` — « Sur le projet dont le risque est survenu à 250 : un avenant qui ne
  touche pas aux risques laisse la réserve à 60 et l’écart de couverture à −190 ; un avenant qui
  intègre au budget de référence les lignes de ce risque porte le budget de référence à 1 250 et
  laisse la réserve à 60 et l’écart à −190 ; un avenant qui déclare un nouveau risque de provision
  50 porte la réserve à 110 et les provisions restantes à 50, et laisse l’écart à −190. » : idem ;
  EP-08 clôt.
- `WF-RIS-0050-A` — « Sur le projet dont le risque est survenu à 250, la réestimation à 300 des
  lignes qui en sont issues présente 300 en regard de 250, et laisse l’écart de couverture à
  −190. » : le panneau de la couverture présente le réestimé des survenus (`occurred_reestimated`)
  en regard de leur coût (`occurred_cost`), comme une information, hors de l'écart de couverture, et
  le registre, pour chaque survenu, son réestimé (`occurred_reestimated_amount`) en regard de son
  coût à la survenance ; les montants sont ceux que le serveur rend, que le front ne calcule pas
  (WF-ARC-0020), et le calcul est d'EP-08, qui clôt (#1763) ;
- écart : `WF-RIS-0060-A` — « Après déclaration de survenance d’un risque dont le devis propre porte
  deux lignes de 120 et 80, ces lignes figurent dans la structure principale de la révision en cours
  avec des montants budgétés nuls et des montants réestimés de 120 et 80 ; la ligne de provision a
  disparu ; le budget de référence et la révision de référence sont inchangés ; le reste à engager a
  augmenté de 200 moins la provision retirée ; la terminaison de ces tâches n’acquiert aucune
  valeur. » : du service ; EP-08 clôt.
- écart : `WF-RIS-0060-A` — « Les tâches fusionnées se trouvent sous la tâche qui portait la
  provision, aux dates qu’elles avaient dans le devis propre ; le total du lot dont cette tâche
  relève augmente de leur montant, moins la provision retirée ; une tâche fusionnée qui n’avait pas
  de prédécesseur est en mode manuel. » : idem ; EP-08 clôt.
- écart : `WF-RIS-0060-A` — « La survenance d’un risque dont la provision était portée par un jalon
  place ses tâches après ce jalon, qui reste un jalon sans sous-tâche. » : idem ; EP-08 clôt.
- `WF-RIS-0060-A` — « Une ligne fusionnée par la survenance d’un risque est encore désignée comme
  issue de ce risque dans la révision suivante, et après son déplacement sous une autre tâche ; une
  ligne ajoutée ensuite sous une tâche issue du risque ne l’est pas. » : les grilles de planning et
  de devis marquent, discrètement et en nommant le risque, toute tâche et toute ligne dont la
  lecture porte `origin_risk_id`, et aucune autre ; que la trace survive aux révisions et aux
  déplacements est du service, EP-08 clôt (#1763) ;
- `WF-RIS-0060-A` — « Les grilles de planning et de devis se filtrent sur les tâches et les lignes
  issues d’un risque, ou d’un risque donné (WF-IHM-0130). » : un filtre « Issues d'un risque » et le
  choix d'un risque survenu passent `is_from_risk` et `origin_risk_ids` par l'adresse, comme les
  autres filtres des grilles, et le registre mène d'un risque survenu à la grille filtrée sur lui ;
  le serveur filtre (#1763) ;
- propre à l'US : le registre se filtre sur chacune de ses colonnes depuis son adresse, comme le
  contrat le permet (WF-IHM-0130) — la zone par une liste, chaque colonne de nombres (probabilité,
  gravité, provision, coût à la survenance, réestimé des survenus) par ses deux bornes, la date du
  dernier réexamen par sa période — et se trie sur ce que le contrat trie (`severity`,
  `provision_amount`, `occurrence_cost`) ; tests du registre (#1787) ;
- propre à l'US : les aides de la planification, du devis, du registre et des provisions des risques
  sont retouchées.

**Notes de réalisation.** Le contrat est d'US-0704 (EP-16 : H-01 #1785, E-04 #1761). Les bornes
des colonnes de nombres suivent `boundNames` et la période `period-filter.tsx`, comme les autres
grilles. L1 fait le registre ; L2 les grilles, le lien du registre vers elles et la couverture.

**Hors périmètre.** Le calcul des montants, la trace à travers les révisions, le filtrage par le
service (EP-08) ; un tri du réestimé des survenus, que le contrat ne propose pas.

---

## US-1030 — L'accueil retient aussi les projets créés

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : `listProjects`
- **issue** : #1835

**En tant que** chef de projet, **je veux** retrouver sur l'accueil, sans lever de filtre, le projet
que je viens de créer, **afin de** reprendre ce que je viens de faire (#1748).

**Critères d'acceptation.**

- propre à l'US : l'accueil retient par défaut les projets Créés, en Chiffrage et En cours, dans
  l'ordre du contrat (`DEFAULT_STATES`, décision de l'auteur du 2026-11-01, D-01) ; un compte qui a
  gardé un choix d'états (`filters.states`) le garde ; le projet créé aujourd'hui se lit sur
  l'accueil par défaut (`projects_with_created`) ; les tests de l'accueil, de sa grille et le
  parcours qui l'ouvre attendent les trois états ;
- propre à l'US : l'aide de l'accueil dit le défaut.

**Notes de réalisation.** Le choix gardé en préférence est celui de #1401 (EP-16, US-0660/L4) ; le
contrat de #1747 est d'US-0704.

**Hors périmètre.** Le filtrage par le service (EP-04).

---

## US-1040 — Le compte rendu d'import lit ses commandes

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : `getImport`, `listImports`, `applyImport`, `abandonImport`
- **issue** : #1836

**En tant que** chef de projet, **je veux** que le compte rendu d'un import m'offre « Appliquer » et
« Abandonner » comme le serveur les liste, et me dise pourquoi un import a été refusé, **afin de**
savoir quoi faire d'un import sans deviner (#1791).

**Critères d'acceptation.**

- propre à l'US : le compte rendu présente « Appliquer » et « Abandonner » selon
  `Import.available_commands`, indisponibles avec leur condition (WF-IHM-0090 ;
  `import_awaiting_decision`, `import_not_applied`), et ne les déduit plus de l'état de l'import ;
- propre à l'US : l'état `refused` a son libellé et son explication — refusé à l'application, le
  fichier supprimé, l'import à relancer — sur le compte rendu et dans le journal des imports, en
  français et en anglais ;
- propre à l'US : tests du compte rendu et du journal ; l'aide des imports et exports est retouchée.

**Notes de réalisation.** Le contrat est d'US-0704 (I-01, I-02, #1789). `IMPORT_STEPS` et `stepsOf`
(`exchanges/offers.ts`, `import-report.tsx`), qui suppléaient l'absence de commandes, disparaissent.

**Hors périmètre.** L'application et l'abandon par le service (EP-06 pour MS Project, EP-07 pour le
devis, EP-09 pour le reste à engager).

---

## US-0800 — Quitter une grille de mille tâches

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1557

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

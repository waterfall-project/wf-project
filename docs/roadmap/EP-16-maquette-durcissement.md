---
id: EP-16
titre: Le contrat figé — ses mineurs soldés, la reprise de la spécification du 2026-10-22 au contrat, au faux back et aux écrans, des parcours joués contre le front construit, et les aides des autres écrans
statut: en cours
depend_de: EP-15
famille: front
issue: 1312
---

# EP-16 — Maquette et contrat : durcissement

## Objet

EP-15 réalise les ajustements que la validation de l'auteur a décidés. EP-16 **fige le contrat**
avant les EPIC de domaine, qui le serviront tel quel : tout ce qui touche le contrat, ou peut le
toucher, y est soldé, et le reste sort (décision de l'auteur du 2026-10-22, au cadrage). Il y a
cinq parts :
- les mineurs du contrat et du faux back reportés d'EP-14 et d'EP-15, et les constats de contrat que
  les lots d'EP-15 ont relevés en livrant (#1345 à #1398) ;
- ce que la reprise de la spécification du 2026-10-22 (#1306, constats C-366 à C-375, #1304)
  ajoute au modèle, pour le contrat, le faux back et les écrans : le nom de l'entreprise, le client
  d'un projet, le code borné d'un sous-projet, la correspondance de l'extraction des coûts réels, le
  poste d'une ligne de coût ;
- en exception au principe, des parcours de bout en bout joués contre le front construit pour la
  production, parce qu'il faut une file de fusion stable pour livrer (#1262) ;
- les aides en ligne des écrans que les cinq écrans clés d'EP-15 ne couvrent pas, et la recherche
  de l'aide, reprises d'EP-15 par la décision de l'auteur du 2026-10-25 (#1445) : elles décrivent
  les écrans tels que les lots d'EP-16 les laissent, et leur relecture par l'auteur ne doit pas
  tenir `epic/EP-15` ouverte ;
- le contrat aligné sur la spécification 1.0.0 avant le gel, sur la revue du 2026-10-28
  (`docs/api/2026-10-28-contrat-avant-gel.md`) : ses bloquants et ses majeurs, au contrat, au faux
  back et aux écrans (recadrage du 2026-10-28).

Recadré d'un bloc le 2026-10-25 (#1445), avec une règle qui prime : **ne reste dans EP-16 que ce qui
concerne le durcissement ou le contrat ; tout le reste part à EP-17.**

Il vient après EP-15, parce qu'on ne fige pas un contrat que les ajustements changent encore, et
avant EP-05, le premier EPIC de domaine, qui doit servir un contrat qui ne bouge plus. Le service de
chaque point de #1304 va à son EPIC de domaine, qui le reçoit dans ses « Constats reçus » :
- EP-05, la correspondance stockée et ses règles, et le nom de l'entreprise demandé par l'amorçage ;
- EP-04, le client d'un projet et le code borné d'un sous-projet ;
- EP-06, la description d'une tâche dans les notes MS Project ;
- EP-09, la lecture de l'extraction selon la correspondance, et le poste d'une ligne de coût.

## Ce qui en fait partie

- les parcours de bout en bout, faux back et service, joués contre `next build` puis `next start`,
  en local comme dans la chaîne, sur un seul build partagé entre les parts (#1262, #1265) —
  US-0590 ;
- le nom de l'entreprise utilisatrice, réglage du référentiel commun sous `cost_settings.write`, à
  côté de la devise (C-371, #1304 point 1) — US-0600 ;
- le client d'un projet et le code borné d'un sous-projet (C-372, D-7 ; #1304 points 2 et 6) —
  US-0610 ;
- la correspondance de l'extraction des coûts réels, page propre du référentiel, et le refus de
  l'import tant qu'elle est incomplète (C-374, C-373 ; #1304 points 3 et 5) — US-0620 ;
- le poste d'une ligne de coût (D-4, #1304 point 4) — US-0630 ;
- les mineurs du contrat et du faux back reportés d'EP-14 et d'EP-15, et les constats de contrat
  relevés par les lots d'EP-15 (« Constats reçus ») — US-0640 ;
- la résolution d'un numéro de ligne en nœud pour les prédécesseurs, et la préférence des colonnes
  connues (#1288, #1260) — US-0650 ;
- l'adoption par les écrans de ce que le contrat décrit — ce qu'EP-14/L42s y a écrit (#1142, #779),
  puis ce qu'US-0640 y ajoute —, qui peut encore y faire apparaître un manque — US-0660 ;
- les aides des autres écrans et la recherche de l'aide, reprises d'EP-15 (#1445) — US-0670 ;
- le compte rendu préalable de la survenance d'un risque, une lecture nouvelle du contrat
  (#1383) — US-0680 ;
- l'adresse de retour de la connexion durcie, une redirection ouverte (#1429) — US-0690 ;
- le filtre des écarts d'un différentiel et de la comparaison, et le décompte de la matrice des
  risques, au contrat puis aux écrans (#1398, part contrat de #1395) — US-0700 ;
- les bloquants et les majeurs de la revue du 2026-10-28 qui touchent le modèle, les règles de
  calcul et les gestes du contrat, au contrat et au faux back — US-0701 ;
- ceux qui touchent la forme des refus — une seule forme par refus, les codes et les conditions
  morts, le 500, les refus sans code ni exemple, le compteur des écritures concurrentes — US-0702 ;
- l'adoption par les écrans de ce qu'US-0701 et US-0702 écrivent au contrat — US-0703.

## Ce qui n'en fait pas partie

- le service de chaque point de #1304 : EP-04, EP-05, EP-06, EP-09 (« Objet ») ;
- la description d'une tâche dans les notes MS Project (C-375, #1304 point 7) : le contrat la porte
  déjà (`description` de la facette de la tâche), seul le service change — EP-06 ;
- les fichiers Excel eux-mêmes et leur présentation, qui nomment l'entreprise et le client : EP-07
  et EP-09 ;
- les finitions hors contrat, reportées le 2026-10-22 vers EP-17 (« Maquette : finitions et
  accessibilité ») :
  - le harnais d'accessibilité aux dialogues, aux menus et aux éditeurs (#782, #784, #819 point 1) ;
  - les mineurs des composants partagés et des écrans ;
  - la lenteur du navigateur à quitter une grille de mille tâches (#1230), une lenteur du produit et
    non de la file — la stabilité restante des e2e (#1263, #1145, #776, #1264), d'abord reportée
    avec elle, revient ici le 2026-10-25 : elle relève du durcissement (US-0590b) ;
  - le cosmétique ;
- par la règle du recadrage du 2026-10-25 — ne reste dans EP-16 que ce qui concerne le durcissement
  ou le contrat ; tout le reste part à EP-17 —, les constats du front ajoutés au label depuis le
  cadrage et les ajustements de la validation du 2026-10-23 qui ne touchent pas le contrat :
  - les mineurs du front relevés par les derniers lots d'EP-15 : #1421, #1424, #1430, #1432, #1386,
    #1364, #1377, et le point 2 de #1384 (le libellé de `ReferenceForm`), repris par #1568 ;
  - deux défauts visibles du front : #1438 (« Déclarer un risque » sur l'écran des révisions ne fait
    rien) et #1428 (l'export PNG du Gantt sans les noms des tâches) ;
  - les ajustements de la validation du 2026-10-23 qui ne demandent que le front ou le guide :
    #1396 (le Kanban filtré), #1397 (la projection sur `kinds`), #1399 (ce que le faux back
    n'applique pas), #1400 (l'écran du projet mène à sa révision), et la part front de #1395 (la
    matrice sur fond blanc, la couleur sur les bulles, les seuls risques identifiés) — sa part
    contrat, le décompte de `cells`, reste ici (US-0700) ;
- la version anglaise de l'aide en ligne : décidée par l'auteur au dernier lot d'US-0670, après la
  relecture de toutes les aides, elle se constate avec WF-IHM-0140, qu'EP-11 clôt ;
- les navigateurs et les largeurs d'affichage (US-0290, #92), et les dépendances sans version
  corrigée (#1291) : EP-13, reportés le 2026-10-22 ;
- de la revue du 2026-10-28 (recadrage du 2026-10-28) :
  - ses 87 mineurs, corrigibles sans rompre le contrat : après le gel, chacun en issue « contrat »
    que l'auteur tranche — sauf ceux qui touchent un fichier qu'un lot d'US-0701 ou d'US-0702
    modifie déjà, que ce lot corrige ;
  - les filtres de colonnes de `listNodes` présentés dans les trois grilles (F-06) : EP-17 ; leurs
    paramètres, eux, entrent au contrat avant le gel (US-0701) ;
  - le service de ce que les trois US écrivent au contrat : l'EPIC de domaine de chaque opération.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-07 | US-0600 |
| `WF-PRJ-0080-A` | Attributs d’un projet | début — close en EP-07 | US-0610 |
| `WF-PRJ-0050-A` | Sous-projets | début — close en EP-09 | US-0610 |
| `WF-REF-0190-A` | Correspondance de l’extraction des coûts réels | début — close en EP-09 | US-0620 |
| `WF-IHM-0140-A` | Aide en ligne | début — close en EP-11 | US-0670 |

Les autres travaux ne réalisent aucune exigence en propre. Comme en EP-14 et en EP-15, leurs tests
citent les exigences du domaine dont le Vérif tient côté front, et l'EPIC du domaine les clôt.

## Opérations du contrat

Ajoutées au contrat :
- la lecture et la modification de la correspondance de l'extraction des coûts réels (US-0620) ;
- la lecture de résolution d'un numéro de ligne en nœud (US-0650) ;
- la lecture du compte rendu préalable de la survenance d'un risque, `getRiskOccurrenceReport`
  (US-0680, #1383).

Leurs noms se fixent à la conception.

Ajoutées par le recadrage du 2026-10-28 (US-0701) : `getIdentitySyncSchedule`,
`setIdentitySyncSchedule` (A-02), `resendInvitation` (A-04), `updateCostStructure` (E-01).

Modifiées :
- `risks` : `declareRiskOccurrence` — les deux compteurs lus (US-0680) ; `listRisks` — la
  pagination (US-0640, #1367) ; `getProjectRiskMatrix`, `getPortfolioRisks` — le décompte de
  `cells` (US-0700, #1395) ;
- `revisions` : `RevisionCommand` — `apply_rate_update` (US-0640, #1351) ; `listNodes`,
  `compareRevisions` — le filtre `difference` (US-0700, #1398) ;
- `nodes` : `createNode` — le refus d'une date manuelle un jour chômé (US-0640, #1345) ;
  `previewPaste`, `applyPaste` — l'ancre sur un nœud retiré (US-0640, #1361) ;
- `projects` : `ProjectCommand.declare_risk` — sa condition dite (US-0640, #1368) ;
- `reference` : `getReferenceSettings`, `updateReferenceSettings` — le nom de l'entreprise
  (US-0600) ;
- `projects` : `createProject`, `getProject`, `updateProject`, `listProjects` — le client ;
  `createSubproject`, `updateSubproject`, `listSubprojects` — le code borné (US-0610) ;
- `exchanges` : `openImport`, `getImport` — le refus tant que la correspondance est incomplète, la
  colonne exigée absente, les colonnes ignorées, le poste (US-0620, US-0630) ;
- `costs` : `listActualCosts` — le poste (US-0630) ;
- `me` : `updateMyPreferences`, `GridPreferences` — les colonnes connues (US-0650), et le choix
  d'états de la liste des projets de l'accueil (US-0640/L6, #1401) ;
- les opérations que touchent les constats d'US-0640, sans en ajouter : la liste se fixe à la
  conception ;
- celles que touchent les bloquants et les majeurs de la revue du 2026-10-28 (US-0701, US-0702) :
  la liste, par famille, est dans la conception.

## Préalables

EP-15 livré.

## Définition de fini

- chaque constat reçu est soldé : appliqué dans `docs/api`, le faux back ou le front, ou écarté dans
  `DECISIONS.md` ou dans l'issue, avec sa raison ;
- chaque modification du contrat a son entrée dans `docs/api/DECISIONS.md` et ses exemples, et le
  faux back et le témoin sont régénérés par l'outillage (`make mock-data`) ;
- les EPIC de domaine nomment, dans leurs « Constats reçus », le service de chaque point de #1304 ;
- `make check` passe sur la branche de l'EPIC ; les parcours de bout en bout s'y jouent contre le
  front construit, en local comme dans la chaîne ;
- chaque code de la table des fonctions qui a un écran a son aide en français, relue par l'auteur ;
  les listes des pages à venir (`SCREENS_TO_COME`, `NOTIONS_TO_COME`) sont vides ; la version
  anglaise est décidée, et son écart écrit sous WF-IHM-0140 (US-0670) ;
- chaque constat ajouté au label `EP-16` depuis le cadrage du 2026-10-22 est placé : corrigé par un
  lot, reporté vers EP-17 et listé dans son fichier, ou fermé avec sa décision.

## Constats reçus

Les issues rattachées à l'issue de l'EPIC (#1312), chacune sous l'US qui la règle.

Repris d'EP-15 par la décision de l'auteur du 2026-10-25 (#1445), au recadrage — US-0670 :

- #1437 [ex-US-0580/L3b], #1139 [ex-US-0580/L4], #1140 [ex-US-0580/L5] — les lots de l'aide, devenus
  US-0670/L1, L2 et L4 ; L3 (#1451) et L5 (#1452) coupés au recadrage ;
- #1075 — front : l'aide en ligne, une aide par écran, les notions et les infobulles des colonnes
  (WF-IHM-0140) : sa part restante, suivie par US-0670 ;
- #1434 — front : les définitions des colonnes des tables de listes — US-0670/L2, L3 et L5 ;
- #1435 — front : les articles du menu de la carte du reste à engager sans infobulle — US-0670/L5 ;
- #1439 — front : les écrans hors de la table des fonctions n'ouvrent pas d'aide — US-0670/L4 ;
- #1440 — front : les identifiants d'exigence dans les citations du glossaire — US-0670/L1 ;
- #1442 — front : les messages d'interface du corps de l'aide sous `lang="fr"` — US-0670/L1 ;
- #1446 — front : le guide et le commentaire du bouton d'aide — US-0670/L1 ;
- #1441 — front : les exemples de saisie de l'aide française dans l'interface anglaise — fermé au
  recadrage, l'écart écrit sous WF-IHM-0140 (US-0670).

Relevés par les lots d'EP-15 et reportés ici parce qu'ils touchent le contrat, le faux back ou le
harnais (décisions des 2026-10-22 au 2026-10-25) :

- #1383 — contrat : la survenance d'un risque n'a pas de compte rendu préalable — US-0680 ;
- #1345 — contrat : `createNode` accepte une date manuelle un jour chômé — US-0640/L6, US-0660/L3 ;
- #1351 — contrat : « Appliquer la mise à jour des taux » n'est listée par aucune commande —
  US-0640/L6, US-0660/L3 ;
- #1367 — contrat : `listRisks` sans `limit`, `offset` ni `meta` — US-0640/L6, US-0660/L3 ;
- #1361 — question : un collage dont la cellule visée est sur un nœud retiré — US-0640/L6 ;
- #1368 — question : « Identifier un risque » sans révision en cours — écarté, par US-0640/L6 ;
- #1379 — contrat : les exemples de l'encart et de l'analyse échouée — US-0640/L6 ;
- #1384 — front, contrat : deux risques dérivés d'exemples dans les tests (point 1) — US-0640/L6 ;
  son point 2, le libellé de `ReferenceForm`, repris par #1568 (EP-17, US-0770/L2) ;
- #870 — contrat : `Contributor.display_name` et `ContributorSuggestion.display_name` nullables,
  pour le nom d'un contributeur anonymisé. Reporté à EP-04 le 2026-10-11, rendu à EP-16 au cadrage
  d'EP-04 (décision de l'auteur du 2026-10-28) : une modification du contrat, qu'EP-16 fige —
  US-0640/L6. EP-04 sert le champ tel que le contrat figé le dit, et le front le nomme par
  `useAccountNaming` (US-0930 d'EP-04) ;
- #1577 — contrat : `AuditAction` sans `project_create` ni `revision_abandon` (WF-SEC-0030), relevé
  au cadrage d'EP-04. Décision de l'auteur du 2026-10-28 : corrigé par US-0640/L6b #1594, avant
  le gel (US-0640/L5 #1333) ;
- #1352 — contrat : la révision 101 à la version 2 sous deux états, l'ordre de `revisions.json` —
  US-0640/L4 ;
- #1398 — contrat, front : un filtre « Écarts seulement » (décision de l'auteur du 2026-10-23) —
  US-0700 ;
- #1309 — e2e : `next dev` à 9,4 Go après le préchauffage — US-0590, qui le fait disparaître ;
- #1342 — e2e : deux expressions de test trop larges, un en-tête à resserrer — US-0590, avec #1309
  (décision de l'auteur du 2026-10-25) ;
- #1444 — outillage : les agents suppriment la branche locale et le worktree d'un lot — US-0590 ;
- #1401 — contrat, front : la liste des projets filtrée par défaut sur Chiffrage et En cours. Rendu
  à EP-16 au cadrage d'EP-17 (décision de l'auteur du 2026-10-28, #1312) : le choix d'états
  différent du défaut, gardé en préférence comme « Lignes par page », demande le contrat, et EP-17
  ne touche pas le contrat. Décisions de l'auteur du 2026-10-28 : **le choix d'états est une
  préférence** — une clé de `grids` pour la liste de l'accueil, écrite au contrat par US-0640/L6
  #1457, avant le gel (US-0640/L5 #1333) — et **la part front** (le filtre par défaut, « Tous les
  états » dans l'adresse, les totaux) **est US-0660/L4 #1571** ;
- #1539 — front : la légende du Gantt rendue par le serveur, tenue jusqu'à l'hydratation (relevé
  par US-0590f). Décision de l'auteur du 2026-10-28 : corrigé par le prochain lot qui touche le
  Gantt du planning. Aucun lot restant d'EP-16 ne le touche (US-0700/L2 touche la grille d'un
  différentiel, non le Gantt) : il est donc reporté → EP-17, US-0750/L1 #1560, au plus tard à la
  livraison d'EP-16 (titre et label changés alors) ; un lot d'EP-16 qui toucherait le Gantt d'ici
  là le corrige ;
- #1512 — front : retirer `prefetch={false}` du menu du compte à la montée vers Next 16.5
  (relevé par US-0590e). Décision de l'auteur du 2026-10-28 : reporté à EP-13 (dépendances), listé
  dans son fichier ;
- #1354 — tests : `restore-dialog.dom.test.tsx` et `backup-deposit.dom.test.tsx`, instables sous
  charge dans la suite front. Rendu à EP-16 au cadrage d'EP-17 (décision de l'auteur du 2026-10-28 :
  la stabilité des tests relève d'EP-16) — repris par le rejeu sous charge d'US-0590g/L2 #1545 ;
- la stabilité restante des parcours, revenue d'EP-17 le 2026-10-25 (le durcissement) — US-0590b :
  #1263 (le rendu serveur du Kanban à 3,2 s, le parcours d'accessibilité d'`/admin/access-roles` à
  1 420 actions), #1145 (les cinq parcours qui échouaient au palier complet local), #776 (l'e2e « on
  a narrow window » de `grid.spec` sous concurrence), #1264 (trois choix d'une ligne sans ordre
  déterminé, dans des tests du back et `latest_report`), et, par la décision de l'auteur du
  2026-10-25, #1473 et #1479 (le Gantt sur le front construit), #1474 (des tests unitaires hors
  délai sous la couverture) et #1477 (`context.spec.ts:24` sous charge) ;
- le durcissement restant des tests, relevé par les revues d'US-0590b (décision de l'auteur du
  2026-10-26) — US-0590d : #1483 (le gestionnaire de molette du Gantt, L1), #1485 (le commentaire
  du test de `latest_report`, L1), #1486 (le `make --dry-run` de `test_frontimage.py`, L1), #1487
  (`MFLAGS` de `harness.test.ts`, L1) et #1484 (les mises à jour après un `await` dans une
  transition, 26 fichiers, L2) ;
- #1429 — front : l'adresse de retour de la connexion ne refuse ni tabulation ni saut de ligne
  (sécurité) — US-0690.

Venus de la reprise de la spécification du 2026-10-22 :

- #1304 — contrat, back, front : ce que la reprise ajoute au modèle — sa part contrat, faux back et
  écrans (US-0600 à US-0630) ; son service va à EP-04 (#1337), EP-05 (#1338), EP-06
  (#1339) et EP-09 (#1340), une issue de service par EPIC ouverte au cadrage.
- #1311 — spec : FBS-3.1.3, une feuille pour la correspondance de l'extraction des coûts réels
  (WF-REF-0190), ouverte au cadrage (validation de la conception, 2026-10-22) ; intégrée par l'auteur
  le même jour (PR #1344), elle ne bloque plus la page de la correspondance d'US-0620.

Reportés d'EP-15 le 2026-10-22, en exception au principe (#1262), ou parce qu'ils touchent le
contrat :

- #1262 — e2e : le serveur de développement sert les quatre workers en série — US-0590 ;
- #1265 — e2e : le guide du préchauffage, un avertissement en mode service, une citation, « corrigé
  avec #1262 » — US-0590 ;
- #1288 — contrat : une lecture de résolution d'un numéro de ligne en nœud (#1257, point 1) —
  US-0650 ;
- #1260 — contrat : une préférence des colonnes connues — US-0650.

Reportés d'EP-14 par la décision de l'auteur du 2026-10-11, puis d'EP-15 au cadrage du 2026-10-18
— US-0640 :

- #774 [ex-EP-14/L42t] — contrat : les exemples manquants et les mineurs des relectures de L42p,
  L42q et L42r ; ses sous-issues #747, #752, #764, #768, #777 ;
- #785 — contrat : le délai de paiement d'une ligne de main-d'œuvre n'est pas saisissable
  (WF-DEV-0020) ;
- #788 — contrat : l'horizon et le cycle de liaisons n'ont pas de refus décrit pour la fusion ; la
  part « saisies » a été faite en EP-15 (US-0460/L2) ;
- #789 — contrat : les comptes rendus d'import et de fusion ne signalent ni la ligne de provision
  déplacée ni la tâche rangée ailleurs ;
- #790 — contrat : une fusion sans révision en cours n'en crée pas une au préalable (WF-REV-0050) ;
- #792 — outil : `is_active_provision` et le point fixe de `make mock-data` ;
- #795 — contrat : les mineurs de la relecture 2 de L42s ;
- #803 — contrat : les exemples manquants des refus des chronologies et du 412 du lotissement ;
- #817 — front : réduit au point 2b, un exemple de refus à deux motifs, qui est du contrat.

Relevés au cadrage d'EP-15 (2026-10-18) et reportés d'EP-14 — US-0660 :

- #1142 — front : l'adoption par les écrans de ce qu'EP-14/L42s a écrit au contrat ;
- #779 — front : le refus d'une saisie qui laisserait une tâche sans heure ne nomme ni les rôles ni
  la tâche.

Relevés par les revues des lots d'EP-16 et corrigés par US-0660/L3 #1458 (décisions de l'auteur des
2026-10-27 et 2026-10-28, cadrage d'EP-17) :

- #1518 — front : la liste des statuts d'une lecture facultative est écrite deux fois (relevé par
  US-0620/L3) ;
- #1524 — front : le détail d'une ligne de coût la nomme par sa pièce seule, sans son poste (relevé
  par US-0630/L2) ;
- #1533 — front : un refus à deux motifs sur le même champ ne dit que le premier (`byField`).

#1525 (le test de la colonne « Poste » cite WF-CRE-0040-A, dont le Vérif ne nomme pas les colonnes)
est reporté à EP-09 #1340 (titre et label `EP-09`).

Relevés par la revue du contrat avant le gel (2026-10-28,
`docs/api/2026-10-28-contrat-avant-gel.md`, 174 constats : 4 bloquants, 83 majeurs, 87 mineurs), au
recadrage du 2026-10-28 — US-0701, US-0702 et US-0703 :

- les 4 bloquants (D-01, E-01, H-01, L-01) et les 83 majeurs, chacun sous l'US qui le règle (tableau
  de la conception) ; ils ne sont pas des issues : la revue les numérote, et la pull request du lot
  nomme ceux qu'elle solde ;
- les 87 mineurs : après le gel, en issues « contrat » (« Ce qui n'en fait pas partie ») ;
- trois points de la spécification que le recadrage laisse à l'auteur, en issues « Specification
  finding » rattachées à l'EPIC : #1595, WF-IHM-0110, l'historique annulable tenu par le serveur
  (E-06) ; #1596, WF-PLA-0130, la date de terminaison d'une tâche terminée par un import, qui est la
  date de la revue que porte le fichier, comme WF-INTF-0120 et WF-INTF-0130 le disent (I-09) ;
  #1597, WF-RAE-0020, le sens de la marge du reste à engager, que la décision #466 fixe (G-07).

Les autres constats du label `EP-16` passent à EP-17 ou à EP-13 (« Ce qui n'en fait pas partie ») :
leur label et leur titre changent au cadrage, et le fichier de leur EPIC les liste. Le recadrage du
2026-10-25 a fait de même pour les constats du front ajoutés au label depuis le 2026-10-22 et pour les
ajustements de la validation du 2026-10-23 qui ne touchent pas le contrat : titre `[EP-17]`, label
`EP-17`, listés dans le fichier d'EP-17 — à l'exception de #1401, rendu ici le 2026-10-28 (voir
ci-dessus).

## Conception

EP-16 est un EPIC du front et du contrat : il ne crée **aucune table ni migration** et ne touche
aucun module du noyau. Le service de chaque point de #1304 va à son EPIC de domaine (« Objet »),
qui reçoit un contrat déjà écrit. Ce qui suit fixe ce que chaque lot devrait sinon décider seul :
- les modifications du contrat ;
- ce que le faux back et le témoin en engendrent ;
- les modules du front touchés ;
- le harnais des parcours ;
- l'ordre de construction.

### Ce que le cadrage décide

La conception est validée par l'auteur le 2026-10-22. Il a suivi chaque recommandation sauf une :
une variable locale rejoue les parcours contre `next dev`.

- **Le contrat figé** : `info.version` passe à `1.0.0` à la livraison d'EP-16. Ensuite, toute
  modification du contrat par un EPIC de domaine passe par une issue « contrat » que l'auteur
  tranche, inscrite dans `DECISIONS.md`. Écartées : la version seule sans règle, et rien.
- **Le principe** (décision de l'auteur du 2026-10-22) : EP-16 garde tout ce qui touche le contrat
  ou peut le toucher, et fige le contrat ; le reste va à EP-17 (finitions) ou à EP-13 (navigateurs,
  dépendances). Exception : #1262, parce qu'il faut une file de fusion stable pour livrer.
- **Les parcours se jouent contre le front construit, et le préchauffage disparaît** (US-0590).
  - Par défaut, le harnais ne démarre plus `next dev`. Un seul serveur `next start` sert les
    parcours, la mesure de la seconde et les parcours du service, sur le port `E2E_FRONT_PORT`,
    celui que Keycloak connaît pour son canal de retour. `E2E_PRODUCTION_PORT` disparaît.
  - Une variable locale, `E2E_DEV_SERVER=1`, rejoue les parcours contre `next dev` (décision de
    l'auteur du 2026-10-22, à la validation de la conception) :
    - elle évite au développeur de reconstruire le front à chaque rejeu ;
    - la mesure de la seconde ne la suit jamais, et se joue toujours contre le front construit ;
    - le harnais refuse de démarrer quand elle est posée dans la chaîne (`CI` défini), en le
      disant ;
    - le guide la documente (`docs/dev/README.md`, « Un parcours de bout en bout ») ;
    - le préchauffage ne revient pas pour elle : un rejeu local se joue sur peu de fichiers, et la
      première compilation d'une route s'y attend.
  - Le build est celui de `make build-front`, qui ne joint aucune API pendant la construction
    (#131). Un même build sert donc le faux back et le vrai service.
  - Le préchauffage des routes (`e2e/warm-up.ts`, #1145) compilait chaque route au premier appel du
    serveur de développement. Le front construit n'a plus rien à compiler : le préchauffage est
    retiré avec ses tests, ce qui solde les points 1 et 3 de #1265.
  - Écartée : le garder pour sa détection d'une panne en 5xx avant le premier parcours. Le premier
    parcours la dit tout aussi bien, et le garder ferait vivre un code sans objet.
  - Point 2 de #1265 : les parcours du service posent `WATERFALL_E2E`. L'avertissement du mode
    `closed` ne s'écrit donc plus pour eux, et `WATERFALL_AUTH` n'y vaut pas `mock`, si bien que
    rien d'autre ne change.
- **Le nom de l'entreprise se range dans `ReferenceSettings`** sous `cost_settings.write`, à côté de
  la devise (décision de l'auteur du 2026-10-22).
  - Il prend le compteur commun des paramètres, comme la matrice et les seuils.
  - Écartée : un réglage dans `Installation`. `getInstallation` se lit sans session, et le nom ne
    sert qu'aux fichiers exportés.
- **La correspondance est un objet unique de l'installation**, lu et remplacé entier, avec son
  compteur, comme les unités de durée (`getDurationUnits`, `setDurationUnits`).
  - Écartée : une opération par colonne. La règle des doublons porte sur toute la correspondance,
    et une écriture partielle devrait la rejuger contre le reste.
  - Une correspondance incomplète s'enregistre : elle est vide à l'installation, et se règle en
    plusieurs fois. C'est l'import qui la refuse.
- **Un import de coûts réels analysé s'applique tel qu'il a été analysé**, même si la
  correspondance change entre-temps. Le compte rendu confirmé est ce qui s'applique (WF-INTF-0080),
  et une modification de la correspondance ne change aucune ligne déjà importée (WF-REF-0190).
  Écartée : refuser l'application par un 409, qui ajouterait un refus pour un cas rare.
- **Le poste se nomme `document_item`**, à côté de `document_number` et de `document_date` :
  l'ERP parle du poste d'une pièce. Comme le numéro de pièce, il identifie la ligne et n'est jamais
  un champ d'un écart `updated` (WF-INTF-0140, D-4).
- **L'élément d'OTP n'est pas exposé à la consultation.**
  - Une ligne importée est de ce projet, si bien que son élément se reconstruit à partir du code
    projet et de `subproject_code`.
  - L'élément d'OTP est une colonne lue : il ne peut pas être aussi une colonne conservée (règle des
    doublons). Le témoin le retire de ses colonnes conservées.
  - Écartée : un champ `ActualCostLine.wbs_element`, qui ne dirait rien de plus.
- **Le code d'un sous-projet lu dans l'élément d'OTP** (`ActualCostLine.subproject_code`) garde sa
  borne de 50. Une ligne au code inconnu se conserve telle quelle (WF-CRE-0020), et la borne du
  code d'un sous-projet déclaré ne s'applique qu'à la création.
- **Les colonnes connues d'une grille** (#1260) : `GridPreferences.known_columns` liste les clés des
  colonnes que la grille offrait à la dernière écriture de ses préférences.
  - Une colonne masquée par défaut et absente de cette liste est masquée. Une colonne absente de la
    liste et non masquée par défaut est montrée.
  - Écartée : une liste des colonnes affichées, qui masquerait aussi une colonne nouvelle montrée
    par défaut.
- **La résolution d'un numéro de ligne** (#1288) est une lecture à part, qui rend le nœud d'un
  numéro dans la numérotation de toute la structure, quels que soient la recherche et les filtres.
  - Écartée : un filtre `row_number` de `listNodes`, qui rendrait aussi les ancêtres et les totaux.
  - L'écriture reste en `predecessor_node_id`.
- **Une fusion sans révision en cours** (#790, WF-REV-0050) se demande sur le différentiel de la
  dernière révision marquée.
  - La commande `merge_structure` y est offerte quand le projet n'a pas de révision en cours.
  - `mergeCostStructure` crée alors la révision en cours par copie (WF-REV-0010), y fusionne la
    copie du différentiel et la marque, dans la même tâche de fond.
  - Le compte rendu (`getStructureMergeReport`) le dit.
  - Écartée : exiger d'ouvrir d'abord une révision, contraire à WF-REV-0050.
- **Les paramètres des refus reçoivent un schéma** (#768, point 3). `Problem.params` déclare, comme
  propriétés facultatives typées, ceux que plusieurs refus partagent : `resource_roles`, `projects`,
  `tasks`, `estimate_lines`, `subproject`, `columns`, `missing_columns`. Il reste ouvert aux autres,
  et le client ne les reçoit plus en `unknown`. Écartée : un schéma par code d'erreur
  (`oneOf`), qui doublerait le catalogue.
- **Un constat d'US-0640 que les ajustements d'EP-15 ont rendu sans objet se ferme**, avec la
  décision qui le rend caduc. Par exemple, la tâche rangée ailleurs de #789 que dit déjà
  `ImportDifference.fields` à `parent` (#1194).

Décisions du recadrage du 2026-10-25 (#1445), toutes prises par l'auteur sur le rendu à blanc de
l'agent de cadrage, avec deux règles qui priment :

- **La règle du périmètre** : ne reste dans EP-16 que ce qui concerne le durcissement ou le
  contrat ; tout le reste part à EP-17. Elle s'applique à chaque issue, et une issue à cheval dit
  dans son corps ce qui va où (#1384, #1395). Écarté : un lot de mineurs du front dans EP-16, qui
  contredirait le principe du 2026-10-22 et retarderait le gel.
- **La règle du titre** : toute issue qui change d'EPIC est retitrée pour que son titre porte l'EPIC
  de destination (`[EP-16] …`, `[EP-17] …`), en plus du label ; un lot transféré porte son nouvel
  identifiant (`[US-0670/L1] …`), le fichier et le label disant son EPIC.
- **US-0670 porte les lots de l'aide repris d'EP-15** (US-0580/L3b, L4, L5 → US-0670/L1, L2, L4 ;
  L3 et L5 coupés). Écarté : déplacer US-0580 vers EP-16 — elle est `fini` dans EP-15 par quatre
  lots fusionnés, une US n'a qu'un fichier, et retirer WF-IHM-0140 du tableau d'EP-15 contredirait
  les tests qui la citent ; écarté aussi : rattacher ces lots à une US existante, aucune ne parlant
  de l'aide. `make roadmap` accepte la forme : EP-15 et EP-16 disent tous deux « début — close en
  EP-11 », chaque US reprenant les trois phrases de Vérif.
- **Les lots de rédaction sont coupés et estimés avec le facteur observé** : les quatre lots
  fusionnés d'US-0580 ont dépassé leur estimation d'un facteur ≈ 1,7 (L3 : 2 466 lignes pour
  1 400). Les ex-L4 et L5 deviennent quatre lots (L2 à L5), chacun estimé nominalement puis avec ce
  facteur, pour rester sous 1 500. Écarté : garder deux lots de ≈ 1 350 et 1 300 nominales, qui
  approcheraient 2 300 au réel.
- **Les lots de rédaction se développent en opus** — conception qui laisse une part à interpréter,
  la rédaction du premier jet, comme US-0580/L3 — : un premier jet faible se paye en relecture de
  l'auteur, le goulot de ces lots. Écarté : sonnet, comme les issues d'origine le disaient.
- **#1383, option (a)** : `getRiskOccurrenceReport`, l'écart calculé par le serveur comme pour
  l'avenant (C-361), US-0680. Écartée : (b), le front compose, qui ne montre ni `M` ni le cas du
  jalon.
- **#1367 : `listRisks` se pagine** (`Limit`, `Offset`, `meta` ; `totals` sur tous les risques
  retenus) — WF-IHM-0060 vaut pour chaque table plate, et le back d'EP-08 n'est pas écrit. Écarté :
  renoncer à « Lignes par page » sur le registre.
- **#1345 : `createNode` refuse aussi** une date manuelle un jour chômé, `NON_WORKING_DAY`, comme
  `updateTaskFacet` — WF-PLA-0020 dit « une date saisie ». Écarté : garder l'asymétrie.
- **#1361 : le collage entier est refusé** quand la cellule visée est sur un nœud retiré, dit par
  `PasteRejection` sur l'ancre. Écarté : reporter l'ancre au nœud suivant, qui écrirait ailleurs que
  là où l'utilisateur a cliqué.
- **#1368 : écarté** — `declare_risk` exige `revision_in_progress`, sur le projet comme sur la
  révision (le devis propre vit dans une révision, WF-RIS-0030) ; la commande indisponible dit la
  condition. Écarté : une lecture nouvelle pour un cas rare.
- **#1352 : le marquage porte une version de plus** dans le témoin, et le test de #421 s'étend aux
  révisions ; `revisions.json` est trié du plus récent au plus ancien (US-0640/L4).
- **#1395 : le décompte de `cells` compte les seuls risques identifiés**, comme les bulles, le
  serveur comptant et le front jamais (US-0700/L1) ; le reste de l'issue — le fond blanc, la couleur
  sur les bulles — est du front, EP-17.
- **#1444 : la règle de fin de lot des agents** est écrite par US-0590, premier lot, qui réécrit
  déjà le guide des parcours. Écarté : une pull request de documentation à part.
- **La discipline des pages à venir** : un lot d'EP-16 qui ajoute un code à `functions.json`
  l'inscrit dans `SCREENS_TO_COME` avec le lot d'US-0670 qui l'écrit (US-0620/L2, FBS-3.1.3 →
  US-0670/L3), et une colonne nouvelle reçoit sa clé `columns.<grille>.<colonne>.help`
  (US-0650/L2) : sans quoi `help.test.ts` ou la section « Ses colonnes » manquent.
- **Les écrans hors de la table des fonctions** — le compte, l'avatar, les pages d'erreur et de
  session — n'ouvrent pas d'aide (#1439, option 1) ; la page du projet ouvre celle de sa fonction.
- **Le bouton « Aide » garde l'icône seule**, avec son libellé accessible, comme US-0580/L3 l'a
  livré ; US-0670/L1 retouche son guide et son commentaire (#1446).
- **La branche du recadrage** vise `epic/EP-15`, non `main` (décision de l'utilisateur du
  2026-10-25) : les fichiers de la roadmap qui font foi y vivent depuis le cadrage (#1341), et une
  pull request vers `main` entrerait en conflit avec la fusion d'EP-15 — contraire à la règle
  habituelle de l'agent de cadrage (`roadmap/EP-nn-cadrage` → `main`), ce qui s'écrit ici.

### Les modifications du contrat

Chacune a son entrée dans `docs/api/DECISIONS.md`, sous une section « Le contrat figé (EP-16) »,
et ses exemples.

- **Les paramètres communs** (US-0600) :
  - `ReferenceSettings.company_name` est requis, de 1 à 200 caractères, et ne peut pas être blanc ;
  - `ReferenceSettingsWrite.company_name` est facultatif, sous `cost_settings.write` ;
  - un refus 422 `VALUE_REQUIRED` ou `VALUE_TOO_LONG` sur `/company_name`, et un 403
    `PERMISSION_MISSING` nommant `cost_settings.write` ;
  - les exemples `reference_settings_company_updated` et `reference_settings_company_refused`.
- **Le projet et ses sous-projets** (US-0610) :
  - `Project.client`, `ProjectCreate.client` et `ProjectUpdate.client` : nullable, de 1 à 300
    caractères comme le libellé, écrits par `createProject` et `updateProject` ;
  - `Subproject.code` et ses écritures : `maxLength` passe de 50 à 31, avec le motif des
    caractères interdits et les deux noms réservés, comparés sans égard à la casse ;
  - un code trop long est refusé par `VALUE_TOO_LONG`, `params.max_length` à 31 ;
  - un caractère interdit ou un nom réservé est refusé par un code nouveau,
    `SUBPROJECT_CODE_INVALID`, `params.forbidden_characters` ou `params.reserved_name` ;
  - l'exemple `import_remaining_subproject_held` nomme l'onglet par le code.
- **La correspondance** (US-0620) :
  - deux opérations : `getActualCostMapping` (`GET /reference/actual-cost-mapping`, sous
    `cost_settings.read`) et `setActualCostMapping` (`PUT`, sous `cost_settings.write`, la
    correspondance entière et son compteur, 412 s'il est périmé) ;
  - le schéma `ActualCostMapping` :
    - `columns`, les cinq colonnes lues dans un ordre fixe, chacune avec son identifiant
      (`ActualCostSourceColumn` : `wbs_element`, `document_number`, `document_item`,
      `document_date`, `amount`), son caractère exigé, rendu par le serveur, et ses intitulés
      (`labels`, au plus 20, chacun de 1 à 200 caractères) ;
    - `kept_columns`, les intitulés des colonnes conservées, au plus 50 ;
    - `is_complete` et `missing_columns`, calculés ;
    - `lock_version` et `audit` ;
  - le refus 422 d'un doublon : `DUPLICATE_COLUMN_LABEL`, sur le pointeur de l'intitulé en
    double, `params.duplicate_of` donnant le pointeur de l'autre ;
  - la condition `actual_cost_mapping_complete` dans `CommandCondition`, nommée par la commande
    `import_actual_costs` ;
  - le 409 `STATE_FORBIDS_OPERATION` d'`openImport` (`params.missing_condition`,
    `params.columns`) ;
  - le 422 `FILE_FORMAT_UNREADABLE` d'un fichier de coûts réels :
    - il porte `params.missing_columns`, chaque colonne exigée absente avec ses intitulés déclarés ;
    - il ne porte aucune `expected_version` : une extraction de l'ERP n'a pas de version (D-2) ;
  - `ImportIgnoredKind` gagne `columns` : les colonnes du fichier ni lues ni conservées, nommées
    par leur intitulé tel que le fichier le porte ;
  - les exemples : `actual_cost_mapping_empty`, la correspondance du témoin, celle d'une écriture
    et celle d'un doublon, le projet dont la commande attend la correspondance, les deux refus
    d'`openImport` et un compte rendu à colonne ignorée.
- **Le poste** (US-0630) :
  - `ActualCostLine.document_item`, nullable ;
  - `ActualCostColumn` gagne `document_item`, qui sert au tri, jamais un champ d'écart ;
  - `ImportDifference.document_item`, pour une ligne de coût ;
  - un code nouveau, `DUPLICATE_COST_LINE`, pour une ligne du fichier dont une autre porte la même
    pièce et le même poste : chacune est rejetée, et `params.rows` nomme les rangs des autres ;
  - les exemples du compte rendu et de la consultation.
- **La résolution d'un numéro de ligne** (US-0650) : `resolveRowNumber`
  (`GET …/structures/{structure_id}/rows/{row_number}`) rend `node_id`, `row_number`, `label` et
  `kind`, ou un 404 si aucun nœud ne porte ce numéro.
- **Les colonnes connues** (US-0650) : `GridPreferences.known_columns`, au plus 64 clés, écrit par
  `updateMyPreferences`.
- **Le choix d'états de la liste de l'accueil** (#1401, décision de l'auteur du 2026-10-28 : une
  préférence ; écrit par US-0640/L6) : sans changer le schéma, une clé de `grids` nommée pour la
  liste des projets de l'accueil, dont `filters.states` garde les états choisis sous le nom que
  l'adresse leur donne ; le défaut — Chiffrage et En cours — reste celui de l'écran (US-0660/L4),
  et un compte qui n'a rien écrit le prend. Le nom de la clé se fixe au lot, avec son exemple et son
  entrée dans `DECISIONS.md` ; le serveur garde le filtre tel qu'il est écrit, comme pour toute
  grille. `getPortfolioProjects` et `PortfolioStates` ne changent pas.
- **Les actions du journal d'audit** (#1577, décision de l'auteur du 2026-10-28 ; écrit par
  US-0640/L6b #1594) : `AuditAction` gagne `project_create` (avant `revision_mark`) et
  `revision_abandon` (après `revision_mark`), dans l'ordre de WF-SEC-0030, avec leurs `params` (le
  code et le libellé du projet ; la révision abandonnée par son projet). `AuditObjectKind` ne change pas.
- **Les mineurs** (US-0640) : chaque constat, point par point, selon sa proposition, sauf ce que
  « Ce que le cadrage décide » tranche autrement ; aucune opération nouvelle. Les constats des lots
  d'EP-15 (US-0640/L6) : `RevisionCommand.apply_rate_update` avec ses conditions et un exemple
  (#1351) ; `listRisks` avec `Limit`, `Offset` et `meta`, `totals` sur tous les risques retenus,
  `risks` et `risks_empty` régénérés (#1367) ; `createNode` refuse par 422 `NON_WORKING_DAY` une date
  manuelle un jour chômé, avec son exemple (#1345) ; la description de `previewPaste` et `applyPaste`
  dit le refus entier d'un collage ancré sur un nœud retiré (#1361) ; celle de
  `ProjectCommand.declare_risk` dit `revision_in_progress` (#1368) ; les exemples `revisions` portant
  0103 et `task_import_analysis_failed` (#1379), `risk_dismissed_category_deactivated` et
  `risk_uncited` (#1384) ; avec la préférence d'états de la liste de l'accueil (#1401).
- **Le nom d'un contributeur anonymisé** (#870, décision de l'auteur du 2026-10-28 ; écrit par
  US-0640/L6) : `Contributor.display_name` et `ContributorSuggestion.display_name` deviennent
  nullables, comme `ActorRef.display_name`, avec un exemple de contributeur anonymisé. Le nom nul
  dit un compte anonymisé : le service, qui ne rend ni le nom (WF-ADM-0060) ni une phrase
  (WF-ARC-0110), et le front qui le nomme (`useAccountNaming`) sont d'EP-04.
- **La survenance d'un risque** (US-0680, #1383) : `getRiskOccurrenceReport`
  (`GET /projects/{project_id}/risks/{risk_id}/occurrence`), une lecture qui n'écrit rien et rend
  `RiskOccurrenceReport` — `main_structure_lock_version`, `risk_lock_version`, `differences`
  (`ImportDifference[]` : les tâches et les lignes du devis propre ajoutées sous la tâche porteuse,
  ou après elle quand c'est un jalon ; la ligne de provision retirée ; la tâche porteuse modifiée),
  `provision_amount` retiré du reste à engager, `refusals` (`ReportRefusal[]`) —, refusée par 409
  pour un risque qui n'est pas identifié ; `RiskOccurrence` reçoit les deux compteurs lus, refusée
  par 412 s'ils ont avancé, comme `StructureMerge` (WF-IHM-0110).
- **Le filtre des écarts et le décompte de la matrice** (US-0700) : un paramètre `difference`,
  partagé par `listNodes` et `compareRevisions`, aux valeurs `added`, `removed`, `modified`,
  combinables ; il retient les nœuds dont l'écart est l'une des valeurs, leurs ancêtres étant
  `modified` par leur contenu ; sans effet sur la structure principale et le devis propre d'un
  risque — refus ou lecture inchangée, tranché au lot et écrit dans `DECISIONS.md` ; `totals` sur la
  structure entière, `amount_deltas` restant « sur les lignes retenues » (#1398). La description de
  `RiskMatrix.cells` dit que le décompte par case ne compte que les risques identifiés, comme les
  bulles ; `totals` reste sur les trois états (WF-RIS-0040 ; #1395, part contrat).
- **La version du contrat** : `info.version` passe de `1.0.0-draft` à `1.0.0` par le dernier lot
  de contrat d'EP-16 (US-0640/L5), qui vient en dernier, à la fin de l'EPIC, après tous les autres
  lots — les lots de rédaction de l'aide (US-0670/L3 à L5) et US-0690 compris — (décision de l'auteur
  du 2026-10-28).

### Le faux back et le témoin

- Les exemples écrits à la main vont dans `fixtures/api` : les paramètres communs, la
  correspondance, la résolution d'un numéro. Ceux que l'outillage engendre se régénèrent par
  `make mock-data`, jamais à la main.
- Le témoin des coûts réels change trois choses :
  - il donne le poste à ses lignes, deux d'entre elles sur la même pièce ;
  - ses éléments d'OTP deviennent le code projet suivi de `/code sous-projet`, et perdent le
    préfixe `WF.` (`mockcosts.py`, C-373) ;
  - « Élément d'OTP » quitte ses colonnes conservées.
- La correspondance du témoin déclare ses intitulés, et ses colonnes conservées sont celles du
  témoin (« Fournisseur », « Texte de commande ») : un test des outils tient les deux d'accord.
- Les codes de sous-projet du témoin respectent déjà la borne. Le test des outils le vérifie.
- Le devis propre du risque 751 (structure 204, 1 250 000,00) est décrit dans `mockwitness`, et
  `mockriskwrites` engendre `risk_occurrence_report` et `nodes_risk_estimate` (US-0680).
- Le marquage de la révision 101 porte une version de plus, le test de #421 s'étend aux révisions,
  `revisions.json` est trié du plus récent au plus ancien (#1352, US-0640/L4) ; les exemples de
  #1379 et #1384 sont écrits (US-0640/L6) ; `risks` et `risks_empty` portent `meta` (#1367) ; un
  contributeur anonymisé porte un `display_name` nul (#870, US-0640/L6) ; le journal du témoin
  (`mockaudit`) reçoit les inscriptions `project_create` (création de PRJ-001, le 6 octobre 2025) et
  `revision_abandon` (#1577, US-0640/L6b #1594).

### Le front

- **Le nom de l'entreprise** : `reference/settings-forms.tsx` reçoit un formulaire à un champ,
  rangé avec la devise sur `/reference/costs`, offert selon `cost_settings.write`.
- **Le client** : `projects/project-form.tsx`, à la création et sur l'écran des paramètres du
  projet ; aucun autre écran.
- **Le code d'un sous-projet** : le formulaire du sous-projet dit le motif du 422 par son
  catalogue, et borne la saisie à 31 caractères.
- **La correspondance** : une page `/reference/costs/actual-cost-mapping`, sous
  `components/reference/`.
  - Les cinq colonnes lues y sont une liste d'intitulés éditable chacune ; les colonnes
    conservées, une autre.
  - Une barre dit les colonnes exigées sans intitulé.
  - L'enregistrement est entier, et un refus se dit au champ par son pointeur.
  - La page est l'écran de la feuille FBS-3.1.3, que #1311 demande à la spécification :
    - `functions.json` la range dans les `leaves` de FBS-3.1 ;
    - l'écran des paramètres de coûts y mène par `leafOf("FBS-3.1.3")`, et le menu l'offre ;
    - **ce lot attend l'intégration de #1311 par l'auteur**, sans quoi `wftools.screens` refuse un
      code que la FBS n'a pas.
- **L'import des coûts réels** :
  - l'écran des échanges dit la condition `actual_cost_mapping_complete` et les colonnes sans
    intitulé, avec un lien vers la page de la correspondance quand le lecteur peut la consulter ;
  - il dit aussi les colonnes exigées absentes d'un fichier ;
  - le compte rendu nomme les colonnes ignorées et les lignes en double.
- **Le poste** : une colonne « Poste » de la grille des coûts réels, après le numéro de pièce,
  triable.
- **US-0650** :
  - la colonne des prédécesseurs (`planning-grid`) résout un numéro hors des lignes lues par
    `resolveRowNumber` avant d'écrire ;
  - `grid/settings.ts` lit et écrit `known_columns`.
- **US-0660** : les écrans des paramètres de coûts (#1142, points 1 et 2), des échanges (point 3),
  du lotissement (points 4 à 6) et `i18n/problem.ts` (#779) ; chaque point sur un exemple du
  contrat. Puis (L3) ce qu'US-0640/L6 écrit : `revision-commands.tsx` offre « Appliquer la mise à
  jour des taux » comme la révision la liste (#1351) ; le registre des risques reçoit `ListPages` et
  `PageSizeChoice` (#1367) ; le refus `NON_WORKING_DAY` d'une tâche créée se dit à la cellule par
  `byField` (#1345) ; les tests du risque lisent les exemples nouveaux (#1384). Puis (L4 #1571)
  la liste des projets de l'accueil : le filtre d'état par défaut, son adresse
  (`navigation/home.ts`), ses totaux, et la préférence qu'US-0640/L6 écrit pour elle (#1401).
- **US-0670, l'aide** : la conception d'EP-15 (« L'aide en ligne et les infobulles ») fait foi —
  `frontend/help/fr/<code>.md`, la structure fixe de #1075, `functions.json` pour clé, les
  définitions des colonnes dans les catalogues, `SCREENS_TO_COME` et `NOTIONS_TO_COME`
  (`frontend/src/help/to-come.ts`) pour les pages promises. L1 reprend le code de
  `lot/US-0580/L3b` (df6a9903) : la recherche (`searched`, `SearchResults`), `HelpColumns` depuis
  les clés `columns.*.help`, les sept colonnes du registre des risques ; puis #1442 (`lang` sur la
  seule page rendue), #1446, #1440 (les notions sans identifiants, `help.test.ts` les ignorant). L2
  à L5 écrivent les pages par famille d'écrans et les définitions des colonnes des tables qui
  passent par `HeaderCell` (#1434) ; L4 rattache la page du projet à sa fonction dans `helpCodeAt`
  (#1439) ; L5 passe les articles du menu de la carte du Kanban à `MenuCommand` (#1435).
- **US-0680** : `risk-detail.tsx` ouvre, pour « Déclarer survenu », le dialogue du compte rendu de
  fusion d'US-0510b (`ImportDifference`, `DiffMark`) sur `getRiskOccurrenceReport`, dit le retrait de
  la provision et les refus, confirme avec les deux compteurs ou abandonne, remet la survenance à
  `TaskTracker`.
- **US-0690** : `navigation/login.ts` refuse tout caractère de contrôle dans l'adresse de retour,
  par la garde partagée `navigation/application-path.ts` (`isApplicationPath`), qu'emploient
  `returnTarget` et `isScreen` (`components/notices/message-history.ts`).
- **US-0700** : le filtre « Écarts seulement » dans l'adresse des grilles de planning et de devis
  d'un différentiel et de l'écran de comparaison, dit dans le bandeau des filtres actifs, absent sur
  la principale et le devis propre d'un risque.

### Le harnais (US-0590)

- `playwright.config.ts` remplace `developmentServer()` et `productionServer()` par un seul
  serveur `next start`, sur `E2E_FRONT_PORT` ; US-0590b en démarre un par worker des parcours, sur
  les ports qui suivent (#1477), et garde un seul front pour la mesure, le service et `next dev`.
  - Le build se fait avant, comme `build-front`, sauf si `E2E_BUILT` dit qu'il est déjà fait.
  - `E2E_DEV_SERVER=1`, en local seulement, remplace ce serveur par `next dev` pour les parcours.
    Posée avec `CI`, elle fait échouer le lancement, avec un message qui le dit.
  - En mode service, le serveur écoute sur toutes les interfaces.
- `make e2e`, `make e2e-measure` et `make e2e-service` construisent le front, puis jouent. En
  local, le cache de Next (`.next/cache`) abrège les builds suivants.
- `e2e.yml` gagne un travail `build`, qui lance `make build-front` et téléverse `.next` sans son
  cache.
  - Les trois parts des parcours et la mesure le téléchargent et jouent avec `E2E_BUILT`.
  - `service.yml` construit une fois pour ses parcours.
- Le guide (« Un parcours de bout en bout ») dit contre quel serveur les parcours se jouent, retire
  le préchauffage, et réécrit la règle de #1145. Les échecs de #1263 restent tolérés au rejeu
  isolé jusqu'à US-0590b. #1309 (la mémoire de `next dev` après le préchauffage) disparaît avec lui,
  et les expressions de test de #1342 se resserrent sur le front construit.
- **US-0590b, la stabilité restante** (décision de l'auteur du 2026-10-25 : la stabilité des e2e est
  du durcissement, donc d'EP-16 et non d'EP-17) : le lot porte ce qui échoue encore une fois US-0590
  fusionné — #1263, #1145, #776, #1264 —, et son contenu définitif s'arrête quand US-0590 a joué
  trois paliers complets sur le front construit : ce qui ne tombe plus sort du lot et se ferme
  « corrigé par US-0590 » ; ce qui tombe encore se corrige à sa cause — le rendu serveur, la
  concurrence des parcours, l'ordre non déterminé —, jamais par une attente plus longue ; la règle
  provisoire de #1145 disparaît du guide avec lui. #1230, une lenteur du produit, reste à EP-17.
  Écarté : une US nouvelle, alors que le README nomme `[US-nnnnb]` la part détachée d'une US à un
  seul lot. **Décision de l'auteur du 2026-10-25** (#1460, #1466) : le lot se livre avant US-0590c,
  et sa condition des trois paliers complets joués avant d'arrêter son contenu est levée — son
  travail est de les obtenir ; son périmètre s'élargit à toute la stabilité des tests, jamais
  reportée à EP-17, et à leur durée — la file de fusion, visée en 8 à 12 minutes, et le palier local
  du front ; il reprend le correctif du Gantt (#1473, #1479), décidé pour US-0590c, et #1474. Ce
  qui en est fait : un front construit par worker des parcours (#1477), l'axe du Gantt qui dit sa
  largeur dans le commit qui le dessine, le parcours au clavier qui ne restyle plus la page entière
  à chaque Tab (#1263), Vitest sur quatre workers au plus (#1474).
- **US-0590c, la montée de Next en 16.4** (#1466 ; décision de l'auteur du 2026-10-25) : les trois
  avis de sécurité du 2026-10-25 ne sont corrigés qu'à partir de 16.4.1, une version mineure qui
  remanie la navigation côté client (vercel/next.js#96252, #97397, #95439) ; au premier passage de
  file avec elle (PR Dependabot #1465), `context.spec.ts:24` et `shell.spec.ts:140`, jamais tombés
  jusque-là, tombent ensemble. v0.1.0 part avec 16.3.8 — Waterfall n'est exposé qu'au déni de
  service par Server Actions, écrit aux notes de version —, et le lot monte Next et `happy-dom`,
  diagnostique les deux parcours à leur cause — un comportement du routeur à adopter, ou un test
  qui présumait l'ancien —, jamais par une attente plus longue, et relit `node_modules/next/dist/docs/`
  à la version montée. Il suit US-0590, sur le front construit, ou le précède sur décision de
  l'auteur. Écarté : fusionner #1465 en l'état, deux parcours rouges.
- **US-0590d, le durcissement restant des tests** (#1489 ; décision de l'auteur du 2026-10-26 : la
  stabilité des tests relève d'EP-16, jamais d'EP-17, et leur durée s'optimise au mieux). Deux lots,
  après US-0590c et US-0670/L1, avant les lots de contrat.
  - L1 (#1490) : `useLayoutEffect` pour le gestionnaire de molette du Gantt et un test du geste pris
    juste après le rendu (#1483, même classe que #1473) ; SHARD, MAKEFLAGS et MAKELEVEL retirés du
    `make --dry-run` de `test_frontimage.py`, avec un test sous `SHARD=2/2` (#1486) ; la ligne
    `MFLAGS` de `harness.test.ts` retirée (#1487) ; le commentaire du test de `latest_report` réécrit
    (#1485) ; et la durée par étape de la chaîne relevée.
  - L2 (#1491) : l'audit des 26 fichiers à `startTransition(async` (#1484), puis leurs correctifs.
    Une mise à jour d'état faite après un `await` n'appartient pas à la transition : la forme de
    correction est la transition imbriquée de `restore-dialog.tsx` (e7688292), pas une abstraction
    écrite d'avance ; le défaut s'écrit dans `docs/dev/typescript.md`. Décision de l'auteur du
    2026-10-26 (#1491, option B), qui précise cette forme après l'audit : la transition imbriquée
    vaut pour les dialogues modaux ; une commande en ligne qui peut tourner en même temps qu'une
    autre tient son geste par un état « occupé » local, levé dans la même mise à jour que la
    réponse, parce que React 19 fait attendre une transition imbriquée jusqu'à la fin de toutes les
    actions asynchrones de la page ; un refus dit à un champ qui prend le focus déplace ce focus dans
    un effet, après le commit du refus ; une réponse portée par un magasin externe est sans objet.
    La taille de L2 dépend de
    l'audit : au-delà de 1 500 lignes ou de 800 de production, le livreur la coupe en L2 (dialogues)
    et L3 (le reste). Coupé à la mesure (1 085 lignes, 516 de production) : L2 (#1491) les dialogues
    et le focus d'un champ refusé, L3 (#1496) les commandes en ligne à l'état local.
  - La durée : en chaîne, le chemin critique mesuré (run 40261263854) est `front-build` (62 s) puis
    la plus longue des parts, `service / paths` (316 s) ou `e2e / paths` (288 / 271 / 222 s). L1
    relève la durée par étape de ces travaux et n'agit que si une étape dépasse 10 % du chemin
    critique, sans qu'un test perde une assertion ; aucun gain n'est promis.
  - Décisions écartées : une abstraction partagée pour la transition (avant l'audit) ;
    `useEffect` ou une écriture pendant le rendu pour la molette ; fermer #1485 et #1487 sans suite.
- **US-0590e, la stabilité d'un parcours sous charge** (#1499 ; décision de l'auteur du 2026-10-26 :
  la stabilité des tests relève d'EP-16, jamais d'EP-17). `shell.spec.ts:120` (« the menu of the
  account leads to the pages of the account ») reçoit parfois `""` à `toHaveTitle("Changer l’avatar —
  Waterfall")` (l. 137), alors que le `h1` de la même page a déjà passé son assertion. Il passe seul
  et n'a jamais été reproduit en file ; relevé par le palier complet local d'US-0590d/L3. Un lot,
  après US-0610/L2 et avant US-0620. Il commence par reproduire (charge, nombre de workers), avant
  tout correctif, et dit sa cause dans la pull request. Le correctif tombe où la cause est — le
  test, l'environnement ou le code de production —, sans attente allongée, `retries`, `fixme` ni
  seuil baissé : il attend la condition que le titre suit, pas plus de temps. Pistes à départager par
  la reproduction, aucune n'est posée comme cause : (a) la métadonnée que Next diffuse en flux après
  une navigation côté client (`generateMetadata` de la page de l'avatar passe par `screenMetadata`),
  qui arrive après le `h1` sous charge ; (b) un titre réellement perdu, défaut du produit ; (c) la
  saturation d'un `next start` partagé, de la classe de `context.spec.ts:24`. À relire à la version
  montée : `node_modules/next/dist/docs/` (`generate-metadata`, `streaming`, `htmlLimitedBots`).
  Part détachée d'US-0590, comme US-0590b, c et d : US-0590 reste `fini`, le lot ne la rouvre que
  par sa lettre. Écarté : le report vers EP-17, que la décision du 2026-10-26 interdit.
- **US-0590f, la stabilité de `planning.spec.ts:23` sous charge** (#1522 ; décision de l'auteur du
  2026-10-27 : la récidive, deux occurrences au palier complet local du front dans des lots qui ne
  touchent pas le planning — US-0630/L1 #1323, puis US-0650/L1 #1326 —, ouvre le lot de stabilité ;
  la stabilité relève d'EP-16, jamais d'EP-17). L'assertion de la ligne 43, `withinBox(grid, « Total
  — 1 000 tâches »)`, reçoit `false`. Elle est prise d'un seul coup, juste après les `columnheader`
  visibles, et le parcours passe seul (15 sur 15). Un lot, après US-0640/L1 et avant US-0640/L2,
  sans dépendance de code.
  - **La cause d'abord.** Reproduire avant tout correctif, à six workers, la charge du palier
    complet local, puis dire la cause dans la pull request.
  - **Une sonde déterministe.** Un test qui échoue sans le correctif et passe avec. Il ne dépend pas
    de la charge : il force l'ordre des événements que la charge fait arriver par hasard (la
    disposition de la grille retardée, la mesure prise avant). La pull request dit lequel des trois
    porte la cause : test, environnement ou production.
  - **Pistes à départager par la reproduction, aucune posée comme cause** :
    - (a) la grille n'a pas fini de se disposer à la mesure, comme #1473 et #1479 (largeur apprise
      par un effet après le montage) ;
    - (b) un défaut du produit : une mise en page qui change après le premier rendu ;
    - (c) la boîte de défilement ou la fenêtre encore en mouvement sous charge.
  - **Le correctif tombe où la cause est.** Il ne passe ni par une attente allongée, ni par
    `retries`, `fixme` ou un seuil baissé. Un `expect.poll` sur `withinBox` n'est admis que si la
    pull request montre que l'état attendu est atteint puis tenu, et non une valeur qui passe un
    instant.
  - **L'audit borné.** Une fois la cause connue, le lot lit les sept autres fichiers qui mesurent
    `withinBox` d'un seul coup, sans `expect.poll` : `grid.spec.ts`, `remaining.spec.ts:93`,
    `portfolio.spec.ts:69`, `projects.spec.ts:70`, `reference.spec.ts:133`, `risks.spec.ts:50`,
    `keyboard.spec.ts:145`. Il corrige ceux qui ont la même cause. Tout autre constat devient une
    issue `[EP-16] e2e : …`, rattachée au lot, avec sa décision.
  - **Le budget.** 90 minutes de reproduction au total, quelles que soient les hypothèses
    essayées. Passé ce délai sans cause trouvée, le lot passe `question` dans son issue, avec ce
    qui a été essayé, comme US-0590e avec #1505. Il ne livre aucun correctif au hasard et ne
    reporte rien vers EP-17.
  - **Décisions écartées.**
    - Le report vers EP-17, que les décisions des 2026-10-25 et 2026-10-26 interdisent.
    - Corriger sur l'hypothèse de #1473 et #1479, qui n'a pas été observée pour `:23`.
    - Allonger une attente, `retries`, `fixme`, baisser un seuil : ils masquent la cause.
    - `expect.poll` partout, d'office : sur une géométrie il peut passer à un instant où la boîte
      n'est pas à sa place finale, et déplacer le défaut.
    - Ne toucher que la ligne 43, ou réécrire tous les `withinBox` d'office : le premier laisse la
      même cause ailleurs, le second grossit le lot au-delà de sa cause.
    - Un plafond en nombre de passes : la charge se mesure en temps de poste.
    - Quatre workers, comme US-0590e : les deux occurrences viennent du palier à six.
    - Y rattacher #1529 et #1528 (tests unitaires du front, d'une autre nature, en sonnet) : ils
      vont à US-0660/L3 #1458.
- **US-0590g, la stabilité du harnais sous charge** (#1540, #1541 ; décision de l'auteur du
  2026-10-28 : la stabilité des tests relève d'EP-16, jamais d'EP-17). Deux lots, après les lots
  qui touchent le contrat ou y reviennent et avant US-0640/L5. Aucune table, aucune opération, aucun
  fichier du contrat : seuls `frontend/e2e/` et le guide changent.
  - **L1, le parcours au Tab (#1540).** La durée de `walkByTab` est proportionnelle au nombre de
    contrôles d'un écran et à la latence d'un aller-retour, que la charge multiplie. Il en fait deux
    par élément : la touche, puis `focusNow`. La mesure passe dans la page.
    - La sonde (`focus-probe.ts`) écoute la touche Tab au `keyup`, quand le focus a déjà bougé, et
      range dans la page le relevé que `focus()` donnait, par le même code. Le parcours presse un lot
      de touches, puis lit les relevés d'un seul `evaluate`. Il reste un aller-retour par élément,
      celui de la touche, que le clavier réel impose.
    - La page cesse d'enregistrer quand le focus revient au premier élément. Les touches de la fin
      d'un lot ne changent rien à `Walk`, et le décompte (`take`, `Tally`) reste côté test.
    - Ce que le parcours dit ne change pas, ni `Walk`, ni `faults`, ni `lost`, ni l'ordre des
      relevés. Le lot le prouve de deux façons : les cas de `tab-walk.spec.ts` rendent les mêmes
      résultats, et un cas nouveau compte les appels à `evaluate` d'une page de fixture.
    - Le lot choisit la taille du lot de touches et la dit dans la pull request avec sa mesure, sans
      charge puis sous charge.
    - Écartée : `focusin`, qui ne se déclenche ni quand le focus reste sur l'élément — le piège que
      le parcours doit voir —, ni quand il quitte le document. Écartée aussi : relever le délai du
      test, que l'issue interdit, et réduire les écrans parcourus, qui retire de la vérification.
  - **L2, le rejeu de #1541.** Il commence par rejouer `projects.spec.ts:103`, `planning.spec.ts:400`
    et `undo.spec.ts:20` sous la charge de #1540 sur `epic/EP-16`, L1 fusionné : le parcours au Tab
    est le test le plus long du palier, et sa durée fait une part de la charge que subissent les
    autres. Ce qui suit dépend du rejeu.
    - Un test qui tombe encore : reproduire, dire la cause, sonde déterministe, correction à la cause
      — la méthode d'US-0590f, avec son budget de 90 minutes.
    - Un test qui ne tombe plus : #1541 le dit « non reproduit », avec les passages rejoués.
    - La charge n'est pas outillée dans le dépôt : elle tient au poste (nombre de cœurs), et un
      outil de plus à entretenir pour un lot ne vaut pas sa reproductibilité. La pull request dit la
      charge réelle. Écartée : une cible `make`.
    - Le `compile(...)` de `projects.spec.ts` et ses semblables, vestiges du serveur de
      développement, ne sont retirés que si la cause les désigne.
- Les instructions des agents reçoivent la règle de fin de lot (#1444) : branche locale et branches
  de travail supprimées, worktree retiré, aucun processus du lot encore vivant.

### Le recadrage du 2026-10-28 : le contrat aligné sur la spécification 1.0.0

La revue du 2026-10-28 (`docs/api/2026-10-28-contrat-avant-gel.md`) conclut que le contrat, une fois
les quatre lots de contrat restants livrés, « ne peut pas être figé sans rompre avec la
spécification 1.0.0 ». Le recadrage du même jour la reprend dans EP-16, avant le gel, par trois US :
US-0701 (le modèle et les règles de calcul), US-0702 (la forme des refus), US-0703 (les écrans).
Rien n'y touche une table ni un module du noyau : EP-16 n'écrit que le contrat, ses exemples, leurs
générateurs (`tools/src/wftools/mock*.py`) et le front ; le service va aux EPIC de domaine.

**Les décisions de l'auteur (2026-10-28).** Chacune réécrit dans `DECISIONS.md` la décision
antérieure qu'elle contredit, en citant la date du changement de la spécification.

- **Le tri** : les 4 bloquants et les 83 majeurs avant le gel ; les 87 mineurs après, en issues
  « contrat », sauf ceux d'un fichier qu'un lot d'US-0701 ou d'US-0702 modifie déjà, que ce lot
  corrige. Écartés : tout avant le gel (deux ou trois lots de plus, sans changement incompatible à
  la clé) ; les seuls bloquants (les majeurs sont des changements incompatibles, qui reviendraient
  un par un après le gel).
- **La règle des autres majeurs** : quand la spécification est claire, la proposition de la revue
  s'applique et la décision antérieure contredite est réécrite ; un lot ne pose une question que
  s'il doit inventer une forme que ni la spécification ni la revue ne donnent. Écarté : une question
  par majeur, une quinzaine de plus, sans choix réel.
- **L'inflation (L-01)** : les montants budgété et réestimé sont « inflation comprise, à l'année de
  consommation » (WF-DEV-0020, WF-DEV-0050, glossaire) ; `base_amount` reste le montant aux taux de
  l'année de référence, avant inflation ; `inflated_amount` disparaît. Réécrit : EP-02/L7 (#235) et
  EP-02/L29 (#352). Écarté : garder #235 et #352 et faire corriger la spécification — elle a tranché
  les 10 et 22 octobre, et le glossaire, WF-RIS-0050 et le budget de référence en dépendent.
- **La sortie (D-01, L-02)** : `ProjectExit` reçoit le sort de la révision en cours, exigé quand le
  projet en porte une — marquer, avec nom de version et description, ou abandonner ; marquer rend
  202 `BackgroundTaskRef`, la sortie s'appliquant quand la tâche réussit ; abandonner, ou sortir
  sans révision en cours, rend 200 `Project`. Écartés : toujours 200, le marquage fait dans la
  requête (contraire à WF-ARC-0090) ; toujours 202, quand rien n'est à calculer.
- **Projet terminal et révision marquée (D-05, J-01, J-02)** : 409 `STATE_FORBIDS_OPERATION` et leur
  `missing_condition` partout ; `PROJECT_TERMINAL` et `REVISION_MARKED` sortent d'`ErrorCode`.
  Réécrits : L42k et US-0640/L1 #803. Écartés : 409 hors grille et 403 sur la grille (deux règles
  pour un même fait) ; 403 partout (contraire à L42a, L42i, L42l et à la lecture commune des
  conditions par le front).
- **L'historique annulable (E-06, L-18)** : tenu par le serveur ; le contrat dit la session (le
  jeton), une pile par révision et par utilisateur, sa fin au marquage et à l'abandon, et au moins
  cinquante niveaux ; une issue de spécification demande de corriger WF-IHM-0110. Écarté : le front
  qui rejoue l'inverse de chaque saisie — `undo` et `redo` retirés, et chaque écriture devant rendre
  l'état antérieur.
- **La date de terminaison par import (I-09)** : la date de la revue que porte le fichier
  (WF-INTF-0120, WF-INTF-0130), connue dès l'analyse ; `ExportRequest` reçoit cette date, le jour
  par défaut, pour l'export du reste à engager ; la fusion garde le jour de son application. Réécrit
  : EP-02/L35. Issue de spécification sur WF-PLA-0130. Écarté : le jour de l'application.
- **La marge du reste à engager (G-07)** : la décision #466 reste ; issue de spécification sur
  WF-RAE-0020. Le contrat ne change pas. Écarté : suivre le Vérif et changer le signe.
- **La date de début de planning (E-01)** : `CostStructure.planning_start_on`, exigé ;
  `updateCostStructure` (`PATCH …/structures/{structure_id}`) l'écrit avec le libellé et le
  `lock_version`, sous la commande de planification de la structure, rend 200 `NodesWritten` et
  refuse un jour sans heure travaillée par 422 `NON_WORKING_DAY`. Écarté : la date seule sans le
  libellé (un second PATCH viendrait pour le libellé).
- **Les risques** : la probabilité ne s'écrit que par `reviewRisk` — `RiskUpdate` défini en propre,
  sans `probability` (H-04 ; écarté : un réexamen implicite produit par `updateRisk`, deux chemins
  pour la même grandeur) ; `Risk.provision_amount` d'un survenu ou d'un écarté est la provision de
  la révision de référence, `0.00` s'il n'y était pas identifié, et `mockhistory` s'aligne (H-03 ;
  écarté : un second champ) ; `Risk.occurrence_cost`, et la couverture le compare à la réserve
  (H-01, H-02 ; réécrit : la décision du 2026-10-06 sur « le coût réestimé des lignes issues des
  risques survenus ») ; `StructureCreate.kind` réduit à `amendment` (E-09 ; écarté : une règle pour
  `risk_id`, deux chemins pour le même objet).
- **La plateforme** : `getIdentitySyncSchedule` et `setIdentitySyncSchedule`, symétriques de
  `BackupSchedule` (A-02 ; écarté : un paramètre d'exploitation, contraire à « choisie par un
  utilisateur habilité ») ; `resendInvitation`, `POST /users/{user_id}/invitation` (A-04 ; écarté :
  le renvoi par la console du fournisseur d'identité) ; `SystemStatus.operating_parameters`, chaque
  paramètre que le §4.5.1 cite avec sa valeur par défaut, la liste relevée par le lot (A-03 ;
  écarté : les cinq de la revue seulement) ; `AuditParams` reçoit `to_state` et `reason`
  (`project_exit`), `backup_taken_at` (`restore`), `import_kind` (`import_apply`), et « jusqu'à
  l'EPIC qui les réalise » disparaît (B-02 ; écarté : aucun paramètre) ; `AuditEvent` garde son nom,
  et une décision assume `event` et `User` face à la table 10 (B-06 ; écarté : le renommage en
  `audit_entry`, un chemin et un client changés sans gain de sens).
- **La devise (C-02)** : `getReferenceSettings` lisible par toute session ouverte, sans 404 ;
  l'écriture garde ses permissions par champ. Écarté : `Installation.currency_code`, lisible sans
  session, quand la devise ne sert qu'à qui voit un montant.
- **Le format d'un import (I-10)** : `openImport` lit l'en-tête — format, version, intitulés — avant
  de mettre l'analyse en file, et refuse par 422 ; l'analyse ne refuse plus de format. Écarté : le
  refus porté par l'échec de la tâche d'analyse, qui change les exemples et le front.
- **Le compteur (E-13, E-24, « Doutes »)** : `lock_version` exigé et 412 sur `abandonRevision`,
  `exitProject`, `designateReferenceRevision`, `deleteRisk`, `deleteSubproject` ; le `PUT` du
  périmètre suivi reste idempotent, sans compteur, et l'exception s'écrit. Écartés : exigé partout
  (l'idempotence de `tracked-scope` est déjà décidée) ; inchangé (contraire à la convention).
- **Le portefeuille** : `horizon_months`, les mois à partir de celui de la date de calcul, 6 par
  défaut ; la courbe en S les fait précéder des douze mois passés (G-04 ; écartés : le futur seul
  partout, un paramètre de plus) ; `from` et `to` sur la structure des coûts et la courbe en S, avec
  la règle de période et le 422 existants, et les projets terminés sans effet, dit, sur le plan de
  charge et la santé du pilotage (G-05 ; écarté : la période sur les quatre vues).
- **Les filtres de colonnes (F-06)** : leurs paramètres entrent au contrat et au faux back avant le
  gel ; leur présentation dans les trois grilles va à EP-17, en constat reporté. Écartés : contrat
  et grilles avant le gel (un lot de front de plus) ; tout après le gel.
- **Les écrans** : US-0703 fait adopter par les écrans tout ce qu'US-0701 et US-0702 changent,
  administration comprise ; les aides d'US-0670/L4 et L5 en dépendent. L'aide des écrans
  d'administration, rédigée par US-0670/L2 déjà fusionné, est mise à jour par le lot d'US-0703 qui
  change ces écrans. Écartés : les seuls écrans existants, les gestes nouveaux de l'administration
  allant à EP-17 ; le front tenu au vert seulement (les aides décriraient des écrans qui changent).

**Les constats, par US.** Les identifiants sont ceux de la revue ; un doublon (« aussi ») suit le
constat qu'il double.

| US | Bloquants et majeurs |
|---|---|
| US-0701 — plateforme | A-01, A-02, A-03, A-04, B-01, B-02, B-03, B-04, B-05, B-06, C-02, C-03, K-04 |
| US-0701 — projets et révisions | D-01, D-02, D-06, D-07, E-01, E-02, E-03, E-04, E-06, E-08, E-09, E-10, E-11, L-01, L-05, L-14, L-16 |
| US-0701 — arbre commun | F-01, F-02, F-06 (paramètres), F-07, F-08, F-09, F-10, F-13, F-14 |
| US-0701 — risques | H-01, H-02, H-03, H-04, M-01, M-04, M-05 |
| US-0701 — indicateurs et portefeuille | G-01, G-02, G-03, G-04, G-05, G-06, M-02, M-03, M-06, M-07, M-08, M-09, M-10, M-11 |
| US-0701 — échanges | I-01, I-02, I-03, I-04, I-05, I-07, I-08, I-09, I-10, I-11 |
| US-0702 | C-01, D-03, D-05, D-10, E-05, E-07, F-03, F-04, F-05, F-11, I-06, J-02, J-03, J-06, J-07, J-10, J-11 ; et, décidés avec eux, les mineurs E-12, E-13, E-14, E-24, H-08, I-17, A-05 |
| US-0703 | la part écran de chacun des constats ci-dessus qui change ce qu'un écran montre ou demande |

**Les modifications du contrat, par famille.**

- `access`, `platform`, `system`, `audit` : les opérations de la périodicité et du renvoi ;
  `SystemStatus.operating_parameters` ; `BackupSchedule` aux champs exigés et sa rétention sur
  toutes les sauvegardes non marquées (B-04, B-05) ; `AuditProject.code` nullable (B-01) ;
  `AuditParams` (B-02) ; ce qui fait mener une inscription au projet (B-03) ; `structure_merge` dans
  `AuditAction` (K-04) ; le rôle prédéfini « Manager » du témoin (A-01).
- `reference` : `getReferenceSettings` lisible par toute session (C-02) ; le code comptable non
  blanc (C-03).
- `projects` : `ProjectExit` et la réponse d'`exitProject` ; `lose` absente d'un projet En cours
  (D-02) ; l'inscription d'un chef de projet par un non-contributeur (D-06) ; le code projet borné
  (D-07).
- `revisions` : les montants (L-01) ; `planning_start_on` et `updateCostStructure` (E-01) ; les deux
  écarts de la comparaison (E-02) ; le taux d'inflation, la probabilité de gain et la révision
  source lisibles sur la révision (E-03, L-05) ; la description de la fusion et ses grandeurs (E-04,
  L-14) ; l'historique annulable dit et `UndoResult` qui rend `NodesWritten` (E-06, E-08) ;
  `StructureCreate` (E-09) ; les images des taux conservés (E-11) ; le plan de charge sur une
  révision marquée (L-16) ; les récapitulatives, la liaison en conflit, les colonnes, le libellé
  composé, la catégorie tenue du rôle, la ligne de provision, le jalon terminé, le mode d'une
  récapitulative (F-01 à F-14) ; les paramètres de filtre de `listNodes` (F-06).
- `risks` : `occurrence_cost`, la couverture, `provision_amount`, `RiskUpdate`, la réserve cumulée,
  l'abandon qui ramène l'évaluation, le placement des tâches fusionnées (H-01 à H-04, M-01, M-04,
  M-05).
- `analysis`, `indicators`, `portfolio` : les courbes au pas du mois, conservées au marquage ; les
  indicateurs exigés ; l'évolution trimestrielle ; `horizon_months` ; la période des projets
  terminés ; la couverture agrégée ; les décaissements ; la contribution d'une offre ; le reste à
  engager d'une ligne non réestimée ; la revue précédente ; le diagramme temps/temps ; l'avancement
  d'une récapitulative (G-01 à G-06, M-02, M-03, M-06 à M-11).
- `exchanges` : le journal des imports, le rejet pour élément d'OTP, la date de début de planning et
  la récapitulative manuelle au compte rendu, les lignes de provision, l'export stocké, la lecture
  d'un import, la date de la revue, le format à l'ouverture, le libellé ambigu (I-01 à I-11).
- Transversal (US-0702) : le README du contrat dit la règle unique des refus d'état ; `ErrorCode` et
  `CommandCondition` sans valeur morte ; le 500 ; `fields` en 422 ; le compteur des cinq écritures.

**Le faux back et le témoin.** Les exemples restent engendrés : L-01 change le calcul des montants
au plus bas des générateurs (`mockstructure`), et tous les exemples qui portent un montant se
régénèrent par `make mock-data` ; les courbes et indicateurs (`mockcurves`, `mockindicators`,
`mockportfolio`, `mockportfoliotime`), les risques (`mockhistory`, `mockwitnessrisks`,
`mockriskwrites`), l'audit (`mockaudit`) et les échanges (`mockexchanges`) suivent leurs constats.
Aucun exemple n'est écrit à la main.

**Le front.** Un lot de contrat ne casse pas la chaîne : il adapte le front que le client régénéré
casse, sans rien présenter de nouveau. US-0703 présente ensuite le nouveau : la confirmation de
sortie, la date de début de planning dans la grille de planning, les colonnes du devis
(`components/grid/estimate.tsx`, `nodes.tsx`, `computed-nodes.ts`), le coût à la survenance et la
modification du risque sans probabilité, la devise avec chaque montant (`formatMoney`, quatorze
appels), l'administration (périodicité, renvoi, paramètres d'exploitation) et les messages des refus
qui changent de forme.

**L'ordre.** US-0701 se construit après US-0640/L6 #1457 et L6b #1594, qui touchent `risks`,
`audit` et `revisions`, et après US-0680/L1 #1453, qui touche la survenance ; L-01 en premier, parce
que tous les montants et tous les calculs en dépendent. US-0702 vient après US-0701, pour donner sa
forme aux refus des opérations qu'US-0701 ajoute. Chaque lot d'US-0703 suit le lot de contrat qu'il
adopte. US-0670/L3 à L5 suivent US-0703 ; le gel vient toujours en dernier.

### L'ordre de construction

1. **US-0590 en tête**, seule : la file de fusion stable sert tous les lots qui suivent ;
   **US-0590b** aussitôt après, la stabilité et la durée des tests, que la file attendait — le
   Gantt la rejetait trois fois de suite —, sans attendre trois paliers complets ; **US-0590c**
   ensuite, la montée de Next en 16.4 sur le front construit (décision de l'auteur du 2026-10-25,
   qui inverse l'ordre de US-0590b et US-0590c) ; **US-0590d** après US-0590c et US-0670/L1, avant
   les lots de contrat (le durcissement restant des tests, décision de l'auteur du 2026-10-26) ;
   **US-0590e** après US-0610/L2 et avant US-0620 (la stabilité d'un parcours sous charge, #1499,
   décision de l'auteur du 2026-10-26) ; **US-0590f** après US-0640/L1 et avant US-0640/L2 (la
   stabilité d'un second parcours sous charge, #1522, décision de l'auteur du 2026-10-27).
2. **US-0670/L1** aussitôt après : du code déjà écrit, qui profite de la file stable ; puis
   **US-0670/L2** (les aides de l'administration et du portefeuille, dont aucun écran ne change en
   EP-16), qui se fusionne comme les autres lots : l'auteur relit après coup (décision du
   2026-10-26, #1139).
3. **Les contrats ensuite**, avant le front qui les consomme : US-0600 et US-0610 (petits, en un lot
   de contrat), US-0620 et US-0630 (la correspondance et le poste, qui touchent les mêmes schémas
   des échanges), US-0650, US-0680/L1, US-0700/L1.
4. **US-0640**, les mineurs du contrat (L1 à L4, L6 ; L7, le front de la fusion, après L3), en
   parallèle des écrans : ils ne touchent pas les mêmes schémas. Chaque point se relit d'abord sur
   EP-15 livré.
5. **Le front de chaque US** après son contrat ; US-0690 à tout moment ; US-0660 (L1 à L4) en
   dernier des fronts, parce qu'elle peut faire revenir au contrat ; **US-0670/L6** (#1583, le plan
   de charge agrégé, correction de #1580) avant le gel, au cas où il touche le contrat des
   préférences.
6. **US-0590g**, la stabilité du harnais sous charge (décision de l'auteur du 2026-10-28) : L1 (le
   parcours au Tab), puis L2 (le rejeu de #1541, sur `epic/EP-16` avec L1). Elle ne touche pas le
   contrat ; elle se place après les lots d'écran et de contrat (US-0660/L3 #1458, US-0640/L6
   #1457).
7. **US-0701, US-0702 puis US-0703**, le contrat aligné sur la spécification 1.0.0 (recadrage du
   2026-10-28) : US-0701 après US-0640/L6 et L6b et US-0680/L1, L-01 en tête ; US-0702 après
   US-0701 ; chaque lot d'US-0703 après le lot de contrat qu'il adopte.
8. **US-0670/L3, L4 puis L5**, les aides du référentiel et du projet : elles suivent US-0703,
   décrivent les écrans tels que tous les lots les laissent, et ne touchent pas le contrat ; L5
   porte la décision de la langue et passe l'US `fini`. Leurs pull requests se fusionnent comme
   celles des autres lots : l'auteur relit après coup, à 18 h 30, et ouvre des issues (décision du
   2026-10-26, #1139).
9. **Le gel** (US-0640/L5 #1333), **en dernier, à la fin de l'EPIC**, dépendant de tous les autres
   lots — US-0670/L3 à L5, US-0690 et US-0701 à US-0703 compris (décision de l'auteur du
   2026-10-28) : le contrat est figé, `info.version` passe à `1.0.0`. La règle d'après s'écrit en
   tête de `docs/api/DECISIONS.md` : une modification du contrat par un EPIC de domaine passe par
   une issue « contrat » que l'auteur tranche, et s'inscrit dans `DECISIONS.md`.

---

## US-0590 — Les parcours de bout en bout joués contre le front construit

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1313

**En tant que** développeur, **je veux** que tous les parcours de bout en bout se jouent contre le
front construit pour la production, en local comme dans la chaîne, **afin que** la file de fusion
ne rejette plus un lot parce que le serveur de développement sert quatre workers en série (#1262).

**Critères d'acceptation.**

- propre à l'US : par défaut, `make e2e` et `make e2e-service` jouent tous leurs parcours contre le
  front construit (`next build` puis `next start`) ;
- propre à l'US : `E2E_DEV_SERVER=1` rejoue en local les parcours contre `next dev`, et le guide le
  dit ; posée dans la chaîne, elle fait échouer le lancement (décision de l'auteur du 2026-10-22) ;
- propre à l'US : dans la chaîne, le front est construit une seule fois par exécution, et chaque part
  des parcours, la mesure de la seconde et la part du service jouent ce même build ;
- propre à l'US : trois passages successifs du palier complet local, à quatre workers, ne montrent
  aucun des échecs que #1262 attribue au débit du serveur de développement : `remaining`,
  `planning`, `admin`, `context`, `navigation`, `review`. Le parcours d'accessibilité
  d'`/admin/access-roles` et le rendu serveur du Kanban relèvent de #1263, part du lot US-0590b ;
- propre à l'US : le guide dit contre quel serveur les parcours se jouent, et ce que deviennent le
  préchauffage des routes et la règle provisoire de #1145 ; les trois points de #1265 sont corrigés ;
  les expressions de test et l'en-tête de #1342 sont resserrés ;
- propre à l'US (US-0590b) : les échecs qui restent après trois paliers complets sur le front
  construit — #1263, #1145, #776, #1264, pour ce qui tombe encore — sont corrigés à leur cause, et
  ceux qui ne tombent plus sont fermés « corrigé par US-0590 » ; la règle provisoire de #1145
  disparaît du guide ;
- propre à l'US (US-0590c) : `next` ≥ 16.4.1 et `happy-dom` ≥ 21.0.4, aucune alerte Dependabot
  ouverte sur ces paquets ; `context.spec.ts:24` et `shell.spec.ts:140` verts sur trois paliers
  complets, sans `fixme` ni attente allongée, leur cause écrite dans la pull request ;
- propre à l'US (US-0590d) : la molette Ctrl du Gantt, donnée juste après un rendu, zoome avec les
  valeurs de ce rendu (test du geste pris juste après le rendu, qui échoue sans `useLayoutEffect`) ;
  le `make --dry-run` de `test_frontimage.py` donne les mêmes commandes avec `SHARD=2/2` dans
  l'environnement ; `harness.test.ts` ne retire plus `MFLAGS` ; le commentaire du test de
  `latest_report` dit que seul le cas croissant tombe sûrement ;
- propre à l'US (US-0590d) : les 26 fichiers de `frontend/src` à `startTransition(async` sont audités,
  chacun « corrigé » ou « sans objet » avec sa raison ; une mise à jour d'après un `await` est posée
  dans la transition imbriquée quand le geste est un dialogue modal, ou, pour une commande en ligne
  qui peut tourner en même temps qu'une autre, tenue par un état « occupé » local levé dans la même
  mise à jour que la réponse (écart : décision de l'auteur du 2026-10-26, option B de #1491 — React 19
  fait attendre une transition imbriquée jusqu'à la fin de toutes les actions asynchrones de la
  page ; reformulation de #1498) ; un test relève l'état au commit qui la montre, et
  `docs/dev/typescript.md` dit le défaut ;
- propre à l'US (US-0590d) : la durée par étape de `service / paths` et des parts de `e2e / paths`
  est relevée dans la pull request ; une étape qui dépasse 10 % du chemin critique est abrégée sans
  qu'un test perde une assertion, sinon la pull request le dit.

**Notes de réalisation.**
- Le harnais construit déjà le front pour la mesure de la seconde (US-0110/L2, port 3101) : l'US
  étend ce build à tous les parcours ; elle ne le crée pas.
- Le front construit refuse l'authentification simulée hors du harnais (`WATERFALL_E2E`).
- Les parcours du service passent par le canal de retour de Keycloak, qui exige d'écouter sur toutes
  les interfaces.
- Décision de l'auteur du 2026-10-22, sur #1262 : EP-16, en tête, tout le harnais, parcours du
  service compris, un seul build partagé entre les parts de la chaîne.
- Décision de l'auteur du 2026-10-25 : la stabilité restante des e2e est du durcissement ; elle
  revient d'EP-17 dans un second lot, US-0590b (#1460), part détachée de cette US, dont le contenu
  s'arrête après trois paliers complets. #1342 et #1309 sont corrigés par le premier lot.
- Décision de l'auteur du 2026-10-25 : la montée de Next de 16.3.8 à 16.4.x (avis GHSA-673q-mjm6-r5xr,
  GHSA-2464-fhr4-w9xw, GHSA-p3m5-59mp-jv5r, corrigés en 16.4.1 seulement) est un troisième lot,
  US-0590c (#1466), parce qu'elle fait tomber deux parcours de navigation : v0.1.0 reste en 16.3.8,
  seul le déni de service par Server Actions concernant Waterfall (aucun `use cache`, aucun
  `next/image`).
- Décision de l'auteur du 2026-10-25 (#1460, #1466) : US-0590b se livre avant US-0590c, sa
  condition des trois paliers complets levée ; son périmètre s'élargit à toute la stabilité des
  tests et à leur durée, et il reprend le correctif du Gantt (#1473, #1479) et #1474. Tout s'y
  corrige à sa cause : ni délai allongé, ni `retries`, ni `fixme`, ni seuil baissé.
- US-0590b : `planning.spec.ts:530` et `:562` tombaient parce que l'axe du Gantt n'apprenait la
  largeur de sa colonne que dans un effet, une tâche après le montage — un défaut du produit, qu'un
  test du geste pris juste après le montage tient (`gantt.dom.test.tsx`) ; `context.spec.ts:24`
  parce qu'un seul `next start` rendait en série les pages des workers (3 échecs sur 60 sous six
  workers, aucun avec un front par worker) ; le parcours au clavier d'`/admin/access-roles`, à 84
  de ses 90 s, parce qu'une feuille posée et retirée à chaque Tab restylait toute la page (66 s) ;
  les tests unitaires de #1474 parce que Vitest prenait douze workers sur un poste dont le débit
  plafonne à quatre (300 s au lieu de 325, le test le plus lent 1,9 s au lieu de 5,4). Le rendu
  serveur du Kanban (#1263), 0,1 s sur le front construit, et les parcours de #1145 et de #776 ne
  tombent plus. US-0590 est `fini` (US-0590d/L3 : finie).
- Décision de l'auteur du 2026-10-26 : US-0590d (#1489) reprend les constats restants des revues
  d'US-0590b (#1483 à #1487), en deux lots, et mesure la durée de la chaîne ; elle se livre après
  US-0590c et US-0670/L1, avant les lots de contrat.
- US-0590d/L2 : l'audit des fichiers à `startTransition(async` est dans #1491, avec la raison de
  chaque classement. Transition imbriquée, dans les dialogues modaux : `restore-dialog.tsx`,
  `reference-form.tsx`, `user-dialogs.tsx`, `breakdown-commands.tsx`, `contributor-commands.tsx`.
  Focus dans un effet, après le commit du refus : `reference-form.tsx`, `role-commands.tsx`,
  `user-dialogs.tsx`, `breakdown-commands.tsx`. Sans objet : `backup-schedule.tsx`, `held.ts`,
  `timeline-commands.tsx`, `subproject-commands.tsx`, `kanban.tsx`, `account-menu.tsx`,
  `task-entry.tsx` et la tâche remise au suivi (un magasin externe). Le défaut est le n° 25
  de `docs/dev/typescript.md`.
- US-0590d/L3 (#1496) : état « occupé » local, dans les commandes en ligne qui peuvent tourner en
  même temps qu'une autre : `reference/commands.tsx`, `backup-commands.tsx` (lancement, marquage
  et dépôt), `command.tsx`, `confirmed-command.tsx`, `exit-command.tsx`, `mark-command.tsx`,
  `export-form.tsx`, `file-drop.tsx`, `import-commands.tsx`, `report-commands.tsx`,
  `author-filter.tsx`, `identity-sync.tsx`, la création en ligne de `role-commands.tsx`,
  `avatar-form.tsx`, `preferences-form.tsx`. US-0590c, US-0590d/L1 et L2 fusionnés, l'US est finie.

**Hors périmètre.** #1230, la lenteur du navigateur à quitter une grille de mille tâches : EP-17.

---

## US-0590e — La stabilité d'un parcours sous charge

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1505

**En tant que** développeur, **je veux** que `shell.spec.ts:120` ne reçoive plus un titre vide sous
charge, **afin que** la file de fusion ne rejette plus un lot sur un échec qui disparaît au rejeu
(#1499).

**Critères d'acceptation.**

- propre à l'US : la cause du titre vide est écrite dans la pull request, après une reproduction qui
  la montre — la charge, le nombre de workers, le test qui échoue —, avant tout correctif ;
- propre à l'US : un test échoue sans le correctif et passe avec ; le test ou le code de production
  est corrigé à sa cause, et la pull request dit lequel des trois (test, environnement, production)
  la porte ;
- propre à l'US : trois passages successifs du palier complet local (`make check-front TIER=full`),
  à quatre workers, voient `shell.spec.ts:120` vert, et la file de fusion verte du premier coup ;
- propre à l'US : aucune attente allongée, aucun `retries`, aucun `fixme`, aucun seuil baissé.

**Notes de réalisation.**
- Part détachée d'US-0590 (un lot, comme US-0590b, c et d) ; US-0590 reste `fini`.
- Voir la conception, « Le harnais (US-0590) ».

**Hors périmètre.** #1500 (deux mineurs de rédaction de `docs/dev/typescript.md`), qui se corrige
avec le prochain lot qui touche ce fichier ; #1230 : EP-17.

---

## US-0590f — La stabilité de `planning.spec.ts:23` sous charge

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1534

**En tant que** développeur, **je veux** que la cellule « Total — 1 000 tâches » du parcours
d'ouverture de la grille de planning soit mesurée dans la fenêtre sous charge, **afin que** le
palier complet local du front et la file de fusion ne rejettent plus un lot sur un échec qui
disparaît au rejeu (#1522).

**Critères d'acceptation.**

- propre à l'US : la cause est écrite dans la pull request, après une reproduction qui la montre
  — la charge, le nombre de workers, le test qui échoue —, avant tout correctif ;
- propre à l'US : un test échoue sans le correctif et passe avec, sans dépendre de la charge ; le
  test ou le code de production est corrigé à sa cause, et la pull request dit lequel des trois
  (test, environnement, production) la porte ;
- propre à l'US : trois passages successifs du palier complet local (`make check-front
  TIER=full`), à six workers, voient `planning.spec.ts:23` vert, et la file de fusion verte du
  premier coup ;
- propre à l'US : aucune attente allongée, aucun `retries`, aucun `fixme`, aucun seuil baissé ; un
  `expect.poll` sur `withinBox` n'est admis que si la pull request montre que l'état attendu est
  atteint puis tenu ;
- propre à l'US : les sept autres fichiers qui mesurent `withinBox` d'un seul coup sont audités
  une fois la cause connue ; ceux qui ont la même cause sont corrigés, les autres constats
  deviennent des issues rattachées au lot.

**Notes de réalisation.**
- Part détachée d'US-0590 (un lot, comme US-0590b à e) ; US-0590 reste `fini`.
- Budget : 90 minutes de reproduction au total ; passé ce délai sans cause, le lot passe
  `question` dans son issue, avec ce qui a été essayé.
- Voir la conception, « Le harnais (US-0590) ».

**Hors périmètre.** #1528 et #1529 : US-0660/L3 #1458 ; #1230 : EP-17.

---

## US-0590g — La stabilité du harnais sous charge : le parcours au Tab et trois parcours non examinés

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1543

**En tant que** développeur, **je veux** que le parcours au Tab d'`accessibility.spec.ts` tienne ses
90 s sous la charge du palier complet local, et que `projects.spec.ts:103`, `planning.spec.ts:400`
et `undo.spec.ts:20` ne tombent plus sous charge, **afin que** le palier complet local du front et
la file de fusion ne rejettent plus un lot sur la saturation du poste (#1540, #1541).

**Critères d'acceptation.**

- propre à l'US (#1540, la mesure) : le parcours au Tab ne fait plus qu'un aller-retour vers le
  navigateur par élément atteint, celui de la touche : la mesure de l'élément n'a plus le sien, la
  page la garde et le parcours la lit par lots. Un test de `tab-walk.spec.ts` le vérifie sans
  dépendre de la charge. Ce que le parcours vérifie ne change pas : `faults(walk)`, `lost` et les
  rubriques de `Walk` ;
- propre à l'US (#1540, la tenue) : sous la charge artificielle qu'a relevée #1540 (six workers,
  `make e2e WORKERS=6 E2E_BUILT=1`, douze à dix-huit boucles actives), trois passages successifs
  voient le parcours au Tab de FBS-1.2, de FBS-2.7 et de FBS-4.8 sous les 90 s du test ;
- propre à l'US (#1541, le rejeu) : avant tout correctif, `projects.spec.ts:103`,
  `planning.spec.ts:400` et `undo.spec.ts:20` sont rejoués sous cette charge sur `epic/EP-16`, et
  l'issue du lot dit lesquels échouent encore.
  - Pour chacun qui échoue : la reproduction (la charge, le nombre de workers, le test), la cause,
    un test qui échoue sans le correctif et passe avec sans dépendre de la charge, et le lieu de la
    cause — test, environnement ou production.
  - Pour chacun qui ne tombe plus : #1541 le ferme « non reproduit », sans correctif, avec les
    passages rejoués consignés dans l'issue ;
- propre à l'US (#1354, le rejeu) : `restore-dialog.dom.test.tsx` et `backup-deposit.dom.test.tsx`,
  instables sous charge dans la suite front, sont rejoués de la même façon, avant tout correctif,
  par L2 #1545 : un test qui tombe encore est corrigé à sa cause (l'attente qui dépend du temps
  rendue déterministe), sans attente allongée ; un test qui ne tombe plus fait fermer #1354 « non
  reproduit », avec les passages rejoués consignés dans l'issue ;
- propre à l'US : aucune attente allongée, aucun `retries`, aucun `fixme`, aucun seuil baissé, aucun
  délai de test relevé ;
- propre à l'US : trois passages successifs du palier complet local (`make check-front TIER=full`),
  à six workers, voient ces quatre parcours verts, et la file de fusion verte du premier coup.

**Notes de réalisation.**
- Part détachée d'US-0590 (deux lots, comme US-0590b et d) ; US-0590 reste `fini`.
- Décision de l'auteur du 2026-10-28 (#1312) : #1540 et #1541 forment un lot de stabilité du
  harnais d'EP-16, placé avant le gel du contrat (US-0640/L5 #1333), qui vient en dernier, sans
  dépendance de code.
- Budget de reproduction de #1541 : 90 minutes au total, comme US-0590f. Passé ce délai sans cause,
  le lot passe `question` dans son issue, avec ce qui a été essayé, sans correctif au hasard ni
  report vers EP-17.
- Pistes pour #1541, aucune tenue pour cause :
  - `planning.spec.ts:400` et `undo.spec.ts:20` s'ouvrent déjà par `openHydrated` : si la cause est
    un écran hydraté après le shell, ils passent peut-être déjà ;
  - `projects.spec.ts:103` s'ouvre par `page.goto` et un clic de menu, sans `openHydrated`, après un
    `compile(...)` hérité du serveur de développement.
- #1354 (`restore-dialog.dom.test.tsx`, `backup-deposit.dom.test.tsx`) est rendu à EP-16 au cadrage
  d'EP-17 (décision de l'auteur du 2026-10-28) et rattaché à cette US : il est repris par le rejeu
  sous charge de L2 #1545, avec le même budget de 90 minutes.
- Le rejeu sous charge est une exécution lourde : elle attend son tour derrière `HEAVY_LOCK`.
- Voir la conception, « Le harnais (US-0590) ».

**Hors périmètre.** #1539 (le Gantt : EP-17, US-0750/L1 #1560, faute de lot d'EP-16 qui le
touche) ; #1230 : EP-17 ; ajouter ou retirer un écran du parcours d'accessibilité.

---

## US-0600 — Le nom de l'entreprise utilisatrice

- **statut** : fini
- **exigences** : `WF-EXP-0020-A`
- **opérations** : `getReferenceSettings`, `updateReferenceSettings`
- **issue** : #1314

**En tant que** manager, **je veux** lire et corriger le nom de l'entreprise que l'installation
connaît, **afin que** les fichiers exportés disent de quelle entreprise ils viennent.

**Critères d'acceptation.**

- écart : `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le
  lien produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles prédéfinis
  et le catalogue des permissions. » : constaté par EP-03 (US-0420), livré ;
- écart : `WF-EXP-0020-A` — « La création d'un projet est refusée et nomme les prérequis manquants,
  jusqu'à ce qu'une catégorie de coût de main-d'œuvre et un rôle de ressource aient été saisis. » :
  le service du projet — EP-04 ; EP-07 clôt l'exigence ;
- écart : `WF-EXP-0020-A` — « Une seconde exécution de l'installation ne crée ni compte, ni
  calendrier, ni nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent,
  tant que l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » : constaté par
  EP-03 (US-0420) ;
- écart : `WF-EXP-0020-A` — « Le lien produit à l'installation est accepté plus d'une heure après
  sa production. » : constaté par EP-03 (US-0420) ;
- écart : `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %,
  50 % et 75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines,
  et le calendrier par défaut compte huit heures du lundi au vendredi et aucune le week-end. » :
  l'amorçage du référentiel — EP-05 ;
- écart : `WF-EXP-0020-A` — « Le nom de l'entreprise saisi à l'installation figure sur un devis
  exporté ; modifié, il figure sur le suivant. » :
  - l'amorçage qui demande le nom et la base qui le garde : EP-05 ;
  - le devis exporté qui le porte : EP-07 ;
  - EP-16 en donne le réglage, au contrat et à l'écran (ci-dessous) ;
- propre à l'US : les paramètres communs (`ReferenceSettings`) portent le nom de l'entreprise, que
  l'écran des paramètres de coûts montre à côté de la devise ;
- propre à l'US : qui porte `cost_settings.write` modifie le nom de l'entreprise à cet écran ; qui
  ne la porte pas le lit sans commande de modification, et une modification qu'il enverrait malgré
  tout est refusée par 403, `PERMISSION_MISSING` nommant `cost_settings.write` ;
- propre à l'US : le nom de l'entreprise est obligatoire ; un nom vide est refusé par champ (422),
  et rien n'est écrit (décision de l'auteur du 2026-10-22).

**Notes de réalisation.**
- Décision de l'auteur du 2026-10-22 : le nom se range sous `cost_settings.write`, dans
  `ReferenceSettings`, à côté de la devise (WF-REF-0140, FBS-3.1).
- `updateReferenceSettings` a déjà le modèle d'une permission par champ : la matrice relève de
  `risk_settings.write`, les seuils d'`indicator_settings.write`.
- Le nom ne va pas dans `Installation` : `getInstallation` se lit sans session, et le nom n'est
  utile qu'aux fichiers exportés.

---

## US-0610 — Le client d'un projet et le code d'un sous-projet

- **statut** : fini
- **exigences** : `WF-PRJ-0080-A`, `WF-PRJ-0050-A`
- **opérations** : `createProject`, `getProject`, `updateProject`, `listProjects`,
  `createSubproject`, `updateSubproject`, `listSubprojects`, `openImport`, `getImport`
- **issue** : #1315

**En tant que** chef de projet, **je veux** nommer le client de mon projet, et que le code d'un
sous-projet puisse nommer un onglet Excel, **afin que** le devis remis au client le nomme, et que
le fichier de reste à engager range chaque sous-projet dans son onglet.

**Critères d'acceptation.**

- écart : `WF-PRJ-0080-A` — « La création d'un projet sans libellé est refusée. » : constaté par
  EP-14 contre le faux back ; le service — EP-04 ;
- écart : `WF-PRJ-0080-A` — « La date de réception de la commande est saisissable à tout moment et
  n'est exigée par aucune transition. » : non touchée ici — EP-04 ;
- écart : `WF-PRJ-0080-A` — « Le nom du client est saisissable à tout moment, n'est exigé par aucune
  transition, et figure sur la présentation d'un devis exporté. » :
  - EP-16 rend le client saisissable au contrat et à l'écran (ci-dessous) ;
  - les transitions qui ne l'exigent pas : le service, EP-04 ;
  - la présentation du devis exporté : EP-07 ;
- écart : `WF-PRJ-0050-A` — « Un projet se chiffre sans aucun sous-projet. » : constaté par EP-02 ;
  EP-09 clôt ;
- écart : `WF-PRJ-0050-A` — « La création de deux sous-projets de même code dans un même projet est
  refusée. » : le service — EP-04 ;
- écart : `WF-PRJ-0050-A` — « La création d'un sous-projet de code « SP/01 », « Synthèse » ou de
  plus de trente et un caractères est refusée. » :
  - EP-16 en écrit au contrat la borne, le motif et le refus, et le formulaire le dit
    (ci-dessous) ;
  - le refus par le service : EP-04 ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet portant des coûts réels est refusée. » :
  constaté par EP-14 contre le faux back ; EP-09 clôt ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet cité par une révision marquée est
  refusée. » : constaté par EP-14/L42l ; EP-09 clôt ;
- écart : `WF-PRJ-0050-A` — « La suppression d'un sous-projet que porte une ligne de devis de la
  révision en cours est refusée ; elle aboutit une fois cette ligne passée à un autre
  sous-projet. » : la seconde moitié demande le service — EP-04 ;
- écart : `WF-PRJ-0050-A` — « Le passage à un autre sous-projet d'une ligne d'une tâche démarrée,
  dont le sous-projet a reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d'une ligne
  d'une tâche non démarrée aboutit, comme celui de la ligne de provision d'un risque identifié. » :
  constaté par EP-15 (US-0480) ; EP-09 clôt ;
- propre à l'US : un projet porte le nom de son client, facultatif.
  - `createProject` et `updateProject` l'écrivent, `getProject` le lit.
  - Le formulaire de création et l'écran des paramètres du projet le saisissent et l'effacent, quel
    que soit l'état du projet, tant que le projet n'est pas terminal.
  - Aucun autre écran ne le montre : ni la liste des projets, ni le portefeuille (décision de
    l'auteur du 2026-10-22).
- propre à l'US : au contrat, le code d'un sous-projet compte au plus 31 caractères, sans `:`, `\`,
  `/`, `?`, `*`, `[` ni `]`, et ne vaut ni « Synthèse » ni « Hors sous-projet ».
  - Un code qui ne l'est pas est refusé par champ (422), avec son motif.
  - Le formulaire du sous-projet dit ce motif.
- propre à l'US : l'exemple `import_remaining_subproject_held` nomme l'onglet du sous-projet par son
  code, et non plus par son libellé, et chaque code de sous-projet du témoin respecte la borne.

**Notes de réalisation.**
- La spécification veut le client « facultatif » (introduction du §3.4.5.2) : nul par défaut,
  exigé par aucune transition.
- La borne du code suit la décision D-7 de la reprise du 2026-10-22. Le contrat passe de 50 à 31.
- Le code d'un sous-projet lu dans un élément d'OTP (`ActualCostLine.subproject_code`) garde sa
  propre borne : un code inconnu y est conservé tel quel (WF-CRE-0020). Que la borne suive ou non se
  tranche à la conception.

---

## US-0620 — La correspondance de l'extraction des coûts réels

- **statut** : fini
- **exigences** : `WF-REF-0190-A`
- **opérations** : `getActualCostMapping`, `setActualCostMapping`, ajoutées au contrat ;
  `getProject`, `openImport`, `getImport`
- **issue** : #1318

**En tant que** manager, **je veux** déclarer les intitulés sous lesquels l'extraction de notre ERP
nomme les colonnes que Waterfall lit, et les colonnes qu'il conserve, **afin d'** importer les coûts
réels quels que soient l'ERP, son paramétrage et la langue de qui l'extrait, sans faire entrer dans
Waterfall une colonne que nous n'avons pas choisie.

**Critères d'acceptation.**

- écart : `WF-REF-0190-A` — « Sur une installation neuve, l'import d'un fichier de coûts réels est
  refusé et nomme la correspondance à régler. » :
  - le refus par le service : EP-09, qui clôt ;
  - la correspondance vide à l'installation : EP-05 ;
  - EP-16 écrit le refus au contrat, et l'écran le dit (ci-dessous) ;
- écart : `WF-REF-0190-A` — « Après déclaration de « Elément d'OTP », « Nº pièce référence »,
  « Date de la pièce » et « Val./Devise objet », une extraction dont l'en-tête est « Élément
  d'OTP » s'importe. » :
  - la lecture de l'extraction selon la correspondance : EP-09 ;
  - la comparaison sans égard à la casse, aux accents et aux espaces en bout : EP-05 ;
- écart : `WF-REF-0190-A` — « Une colonne « Nom Matricule » non déclarée n'est pas conservée, et le
  compte rendu la nomme ; déclarée conservée, elle est restituée à la consultation des lignes
  importées ensuite. » :
  - le service : EP-09 ;
  - EP-16 donne au compte rendu la liste des colonnes ignorées (ci-dessous) ;
- écart : `WF-REF-0190-A` — « Une extraction à laquelle manque une colonne exigée est refusée, et le
  message nomme la colonne attendue. » :
  - le refus par le service : EP-09 ;
  - EP-16 écrit au contrat le paramètre qui nomme la colonne, et l'écran le dit (ci-dessous) ;
- propre à l'US : une page propre du référentiel, avec son entrée de menu sous les paramètres de
  coûts (FBS-3.1), montre la correspondance.
  - Pour chaque colonne lue (élément d'OTP, numéro de pièce, poste, date de pièce, montant), elle
    montre ses intitulés admis.
  - Elle montre aussi la liste des colonnes conservées, déclarées une à une par leur intitulé.
  - Une correspondance vide dit les quatre colonnes exigées qui n'ont aucun intitulé : toutes sauf
    le poste.
- propre à l'US : qui porte `cost_settings.write` ajoute, modifie et retire un intitulé, déclare et
  retire une colonne conservée ; qui porte seulement `cost_settings.read` lit la page sans commande
  de modification ;
- propre à l'US : un intitulé qui, une fois normalisé (sans égard à la casse, aux accents ni aux
  espaces en bout), en double un autre est refusé par champ (422), et rien n'est écrit. Le doublon
  peut être entre deux colonnes lues, ou entre une colonne lue et une colonne conservée. Une colonne
  conservée se déclare par son intitulé et se compare de la même façon (décisions de l'auteur du
  2026-10-22) ;
- propre à l'US : tant que l'une des quatre colonnes exigées n'a aucun intitulé, la commande
  `import_actual_costs` d'un projet est indisponible et nomme la condition
  `actual_cost_mapping_complete`.
  - Un `openImport` de coûts réels envoyé malgré tout est refusé par 409 `STATE_FORBIDS_OPERATION`,
    `params.missing_condition` à `actual_cost_mapping_complete`.
  - `params.columns` y nomme les colonnes sans intitulé, et l'écran des échanges le dit.
- propre à l'US : un fichier de coûts réels auquel manque une colonne exigée est refusé par 422
  `FILE_FORMAT_UNREADABLE`, un paramètre nommant la colonne attendue, et l'écran le dit ;
- propre à l'US : le compte rendu d'un import de coûts réels nomme chaque colonne du fichier ni lue
  ni déclarée conservée, que l'import ignore ;
- propre à l'US : les éléments d'OTP des exemples de coûts réels portent le code projet, préfixe
  compris, suivi facultativement d'une barre oblique et du code sous-projet (WF-CRE-0020, C-373).

**Notes de réalisation.**
- Décisions de l'auteur du 2026-10-22 :
  - une page propre, par exemple `/reference/costs/actual-cost-mapping`, avec son entrée de menu ;
  - le refus de l'import par 409 `STATE_FORBIDS_OPERATION`, `actual_cost_mapping_complete` et
    `params.columns`, la commande `import_actual_costs` nommant la condition d'avance ;
  - le service : EP-05 stocke la correspondance et applique ses règles, EP-09 lit l'extraction selon
    elle et clôt WF-REF-0190.
- La permission découle de la spécification : WF-REF-0190 relève de FBS-3.1, dont la permission de
  modifier est `cost_settings.write` (WF-ADM-0100).
- Une modification de la correspondance ne change aucune ligne déjà importée (WF-REF-0190) : le
  contrat le dit, le service le tient (EP-09).
- L'exemple de l'auteur (« Elément d'OTP », « Nº pièce référence », « Date de la pièce »,
  « Val./Devise objet ») est celui du Vérif. Les exemples du contrat le reprennent.

---

## US-0630 — Le poste d'une ligne de coût

- **statut** : fini
- **exigences** : aucune en propre ; le service clôt WF-INTF-0140, WF-CRE-0010 et WF-DAT-0110 en
  EP-09
- **opérations** : `listActualCosts`, `getImport`
- **issue** : #1322

**En tant que** chef de projet, **je veux** voir le poste de chaque ligne de coût, **afin de**
distinguer les postes d'une même pièce de l'ERP, qu'une facture ventilée sur deux éléments d'OTP
donne en deux lignes.

**Critères d'acceptation.**

- propre à l'US : une ligne de coût porte son numéro de poste, nul quand l'extraction n'en donne
  pas ; la consultation des coûts réels le montre à côté du numéro de pièce ;
- propre à l'US : le compte rendu d'un import de coûts réels désigne une ligne par sa pièce et son
  poste. Deux lignes du fichier de même pièce et de même poste y sont rejetées, avec un motif que
  l'écran dit, sur un exemple du contrat.

**Notes de réalisation.**
- Décision D-4 de la reprise du 2026-10-22 : une ligne de coût est identifiée par le projet, le
  numéro de pièce et le numéro de poste.
- La contrainte d'unicité, sa migration et l'idempotence de WF-DAT-0110 sur ce triplet sont le
  service : EP-09.

---

## US-0640 — Les mineurs du contrat et du faux back

- **statut** : en cours
- **exigences** : aucune en propre
- **opérations** : celles que les constats touchent, sans en ajouter — dont `updateMyPreferences`
  (#1401), `applyPaste`,
  `createRisk`, `updateRisk`, `updateEstimateLine`, `updateCalendar`, `undoLastChange`,
  `redoLastUndo`, `createTimeline`, `deleteTimeline`, `setWorkBreakdown`, `getImport`,
  `getStructureMergeReport`, `mergeCostStructure`
- **issue** : #1328

**En tant que** développeur, **je veux** solder les mineurs du contrat et du faux back que les
relectures d'EP-14 ont relevés, et les constats de contrat que les lots d'EP-15 ont relevés en
livrant, **afin que** les EPIC de domaine servent un contrat figé, aux exemples complets et aux
refus décrits.

**Critères d'acceptation.**

- propre à l'US : chaque constat de contrat reçu (« Constats reçus », US-0640) est soldé, point par
  point.
  - Appliqué : dans `docs/api`, avec son entrée dans `DECISIONS.md` et ses exemples.
  - Ou caduc : un ajustement d'EP-15 l'a rendu sans objet, et l'issue le dit.
  - Ou écarté : avec sa raison, dans `DECISIONS.md` ou dans l'issue.
- propre à l'US : chaque refus que le contrat décrit a un exemple, et les tests du front qui
  l'éprouvent passent par cet exemple, non par une enveloppe écrite dans le test (#803, #764,
  #817 point 2b) ;
- propre à l'US : deux exécutions de suite de `make mock-data` donnent les mêmes exemples (#792), et
  les indices d'un portefeuille sans projet en cours sont non calculables, avec leur motif, jamais
  une erreur (#777).

**Notes de réalisation.**
- Plusieurs points datent d'avant EP-15, qui a découpé `mockcore.py` et `mockwitness.py` (#1281) et
  réécrit les refus de la structure : chaque point se relit sur `epic/EP-15` livré avant d'être
  appliqué.
- #785 rend le délai de paiement saisissable sur une ligne de main-d'œuvre (WF-DEV-0020). La cellule
  du devis suit `editable_fields`, sans code propre.
- Les constats des lots d'EP-15 — #1345, #1351, #1352, #1361, #1367, #1368, #1379, #1384 (point 1) —
  sont tranchés dans « Ce que le cadrage décide » (recadrage du 2026-10-25) ; leur part front est
  d'US-0660.
- L6 #1457 écrit aussi le nom nul d'un contributeur anonymisé (#870, décision de l'auteur du
  2026-10-28) : `Contributor.display_name` et `ContributorSuggestion.display_name` nullables,
  avec un exemple et son entrée dans `DECISIONS.md` ; le lot que le pilote retient par défaut, l'auteur n'en
  ayant nommé aucun autre.
- L6b #1594, qui dépend de L6 #1457, écrit `project_create` et `revision_abandon` dans
  `AuditAction` (#1577, décision de l'auteur du 2026-10-28) : leurs `params`, les deux
  inscriptions de `mockaudit` et l'entrée de `DECISIONS.md`. US-0640/L5 #1333, qui fige le
  contrat, dépend de L6b.
- L6 #1457 écrit aussi la préférence d'états de la liste de l'accueil (#1401, décision de l'auteur
  du 2026-10-28), parmi ses constats de contrat : une clé de `grids`, son exemple et son entrée
  dans `DECISIONS.md` (« Les modifications du contrat »). Si le lot devient trop gros à la
  lecture, le livreur le dit dans l'issue plutôt que de le découper.
- L3 #1331 écrit la fusion sans révision en cours (#790) au contrat et dans le témoin ; sa part front
  est **L7 #1584** (décision de l'auteur du 2026-10-28, dépend de L3) : la commande `merge_structure`
  offerte sur le différentiel de la dernière révision marquée, le compte rendu qui dit
  `creates_current_revision`, et les échecs `LINK_CYCLE`, `PROJECT_HORIZON_EXCEEDED` et
  `LINK_FORBIDDEN` avec leurs paramètres.
- L5 #1333, qui fige le contrat (`info.version` à `1.0.0`), vient **en dernier**, à la fin de
  l'EPIC (décision de l'auteur du 2026-10-28) : il dépend de tous les autres lots, US-0670/L3 à L5,
  US-0690, US-0590g, US-0660 et L6 et L7 compris, et, depuis le recadrage du 2026-10-28, ceux
  d'US-0701, US-0702 et US-0703.

---

## US-0650 — La résolution d'un numéro de ligne, et les colonnes connues d'une grille

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : `resolveRowNumber`, ajoutée au contrat ; `setPredecessors`, `getMe`,
  `updateMyPreferences`
- **issue** : #1325

**En tant que** chef de projet, **je veux** saisir comme prédécesseur le numéro d'une tâche que ma
recherche a écartée, et ne voir apparaître une colonne nouvelle, masquée par défaut, que si je la
demande, **afin que** filtrer une grille ne m'empêche pas de la saisir, et qu'une colonne ajoutée
par une version ne bouscule pas la grille que j'ai réglée.

**Critères d'acceptation.**

- propre à l'US : un numéro de ligne absent des lignes lues, mais porté par une tâche de la structure
  lue, se saisit dans la colonne des prédécesseurs.
  - Le front le résout en nœud par la lecture du contrat, et la liaison s'écrit en
    `predecessor_node_id`.
  - Un numéro qu'aucune tâche de la structure ne porte est refusé comme inconnu.
- propre à l'US : une colonne masquée par défaut, que la grille ne connaissait pas, l'est aussi pour
  un compte qui a déjà réglé cette grille ; une colonne que le compte a choisi d'afficher reste
  affichée.

**Notes de réalisation.** Décisions de l'auteur :
- #1288 : une lecture de résolution au contrat ; l'écriture reste en `predecessor_node_id`
  (2026-10-22, #1257 point 1) ;
- #1260 : une préférence des « colonnes connues » au contrat des préférences (2026-10-21, #1232).

---

## US-0660 — Ce que le contrat décrit, adopté par les écrans

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : celles des six points de #1142, celles des saisies que refuse
  `TASK_WITHOUT_WORKING_HOURS`, et celles qu'US-0640/L6 modifie — `listRisks`, `createNode`, les
  commandes de la révision
- **issue** : #1334

**En tant que** chef de projet, **je veux** que les écrans disent les règles que le contrat décrit
déjà, **afin que** chaque refus et chaque indisponibilité me nomment ce qui les cause.

**Critères d'acceptation.**

- propre à l'US : les six points de #1142 sont montrés par les écrans, chacun sur un exemple du
  contrat :
  - la réactivation d'une catégorie sous une nature désactivée, et la désactivation d'une nature en
    cascade sur ses catégories ;
  - les catégories nommées par le refus d'un changement de type ;
  - l'import rejeté entier ;
  - le lot sans tâche rattachée, présenté sans total ;
  - la saisie du lotissement indisponible pendant un traitement de fond ;
  - les tâches nommées par le refus d'un poste hors du sous-arbre de son lot.
- propre à l'US : le refus d'une saisie qui laisserait une tâche sans heure travaillée
  (`TASK_WITHOUT_WORKING_HOURS`) nomme la tâche par son libellé et les rôles par leur libellé (#779).
- propre à l'US : les écrans adoptent ce qu'US-0640/L6 écrit au contrat : « Appliquer la mise à jour
  des taux » s'offre comme la révision la liste, l'exception de US-0490/L2 levée (#1351) ; le
  registre des risques reçoit « Lignes par page » et sa pagination, ses totaux restant ceux de tous
  les risques retenus (#1367) ; le refus d'une tâche créée avec une date manuelle un jour chômé se dit
  à la cellule (#1345) ; les tests du risque lisent les exemples nouveaux du contrat (#1384) ;
- propre à l'US (L4 #1571, #1401 ; décision de l'auteur du 2026-10-23, complétée le 2026-10-28) :
  la liste des projets s'ouvre filtrée sur **Chiffrage et En cours** :
  - le filtre par défaut se dit comme le filtre « contributeur », visible tant qu'il s'applique ; il
    se lève par « Tous les états » et se change comme aujourd'hui ;
  - une adresse sans `states` vaut le défaut ; « Tous les états » a son expression dans l'adresse
    et se lit au serveur sans filtre ; les liens du filtre gardent le reste de l'adresse ;
  - un choix d'états différent du défaut se garde en préférence, comme « Lignes par page », par ce
    qu'US-0640/L6 écrit au contrat avant le gel ;
  - les totaux suivent les états retenus (WF-IHM-0130) ; « Voir tous les projets » ne change pas ;
- propre à l'US : un manque du contrat que cette adoption révèle est corrigé au contrat, dans l'US.

**Notes de réalisation.** Ces constats ne demandent que le front, mais ils peuvent révéler un
manque du contrat, comme EP-15 l'a souvent constaté : c'est ce qui les garde en EP-16 (principe de
l'auteur du 2026-10-22). Le titre et le troisième lot viennent du recadrage du 2026-10-25.
- L4 #1571 (décision de l'auteur du 2026-10-28) porte la part front de #1401 : la liste des
  projets de l'accueil s'ouvre filtrée sur Chiffrage et En cours. Son contrat — le choix d'états en
  préférence de la liste de l'accueil — est écrit par US-0640/L6 #1457, avant le gel (US-0640/L5
  #1333) ; L4 en dépend.
- L3 #1458 corrige aussi trois constats des revues de lots : #1518 (la liste des statuts d'une
  lecture facultative, écrite deux fois), #1524 (le détail d'une ligne de coût sans son poste) et
  #1533 (un refus à deux motifs sur le même champ, que `byField` ne dit qu'à moitié). #1525 est
  reporté à EP-09 #1340.

---

## US-0670 — Les aides des autres écrans et la recherche de l'aide

- **statut** : en cours
- **exigences** : `WF-IHM-0140-A`
- **opérations** : aucune en propre ; `getComputedValueDependencies`, déjà lue par les infobulles
- **issue** : #1447

**En tant que** chef de projet, manager ou administrateur, **je veux** ouvrir sur chacun des écrans
que l'aide ne décrit pas encore — l'administration, le portefeuille, le référentiel, le projet hors
des cinq écrans clés — une aide qui dit ce qu'il montre, ses commandes et leurs conditions, ses
colonnes, les gestes au clavier et les notions de la méthode, et retrouver une page de l'aide par
son titre, **afin de** me servir de Waterfall sans manuel ni formation, quel que soit l'écran où je
suis.

**Critères d'acceptation.**

- `WF-IHM-0140-A` — « Chaque écran ouvre une aide qui le concerne. » : chaque code de la table des
  fonctions qui a un écran et n'a pas encore sa page — les vingt et un codes de FBS-1, FBS-2 et
  FBS-3, les vingt-trois codes de FBS-4 que les cinq écrans clés d'EP-15 ne couvrent pas, et
  FBS-3.1.3 qu'US-0620 ajoute — reçoit son fichier français, dans la structure fixe ; les listes des
  pages à venir (`SCREENS_TO_COME`, `NOTIONS_TO_COME`) sont vides à la fin de l'US, et le test de
  complétude exige un fichier par code ; la page du projet (`/projects/P`) ouvre l'aide de sa
  fonction (#1439) ; les écrans hors de la table des fonctions — le compte, l'avatar, les pages
  d'erreur et de session — n'ouvrent pas d'aide, et cette exclusion est écrite ici.
- écart : `WF-IHM-0140-A` — « Dans la grille de devis, l’intitulé de la colonne du montant corrigé de
  l’inflation porte une infobulle qui nomme l’année de référence et le taux d’inflation. » :
  constaté par EP-15 (US-0580/L2), inchangé ici ; EP-11 clôt.
- écart : `WF-IHM-0140-A` — « L’aide s’affiche dans la langue de l’utilisateur. » : l'aide n'existe
  qu'en français, et une interface en anglais la montre telle quelle ; ses exemples de saisie
  (« 2 j », « 1 sem », FD/DD) ne valent pas dans l'interface anglaise, qui attend `d`, `w`, FS/SS
  (#1441) ; la version anglaise se décide après la relecture par l'auteur de toutes les aides, au
  dernier lot de cette US, et le test de complétude l'exigera alors ; EP-11 clôt.
- propre à l'US : la recherche de l'aide porte sur les titres des pages et des notions, côté client,
  sur l'index rendu avec le panneau ; elle a son libellé dans les deux catalogues ;
- propre à l'US : la section « Ses colonnes » du panneau se rend depuis les clés
  `columns.<grille>.<colonne>.help` des catalogues, jamais depuis le Markdown, pour les grilles du
  projet comme pour les sept colonnes du registre des risques ; les tables de listes qui passent par
  `HeaderCell` (référentiel, administration, portefeuille, échanges, coûts réels) reçoivent leurs
  définitions, chacune avec le lot qui décrit son écran (#1434) ; les colonnes qu'US-0650 ajoute en
  ont une ;
- propre à l'US : les articles du menu des gestes d'une carte du reste à engager passent par
  `MenuCommand`, avec une clé `commands.<geste>.help` par geste (#1435) ;
- propre à l'US : les notions citent le glossaire sans ses identifiants d'exigence, et le test de
  complétude les ignore dans sa comparaison (#1440, décision de l'auteur du 2026-10-25) ; la région
  du corps du panneau ne porte `lang="fr"` que sur la page rendue, jamais sur les messages de
  l'interface (#1442) ; le guide et le commentaire du bouton d'aide disent ce qu'il fait (#1446) ;
- propre à l'US : les cinq aides d'EP-15 et les notions EVM reçoivent les retouches que la relecture
  de l'auteur demande, et chaque aide décrit l'écran tel que les lots d'EP-16 le laissent — la
  correspondance (US-0620), le client (US-0610), le poste (US-0630), le nom de l'entreprise
  (US-0600), les colonnes nouvelles (US-0650), le compte rendu de survenance (US-0680), le filtre des
  écarts (US-0700) ;
- propre à l'US : les lots de rédaction (L2 à L5) se fusionnent comme les autres ; l'auteur relit
  après coup, à 18 h 30, et ouvre des issues (décision de l'auteur du 2026-10-26, #1139).

**Notes de réalisation.** Reprise d'EP-15 par la décision de l'auteur du 2026-10-25 (#1445) : les
lots US-0580/L3b, L4 et L5 deviennent US-0670/L1, L2 et L4, et deux lots s'y ajoutent par la coupe
du recadrage (L3, le référentiel et les notions ; L5, les indicateurs et la langue) — les quatre lots
fusionnés d'US-0580 ayant dépassé leur estimation d'un facteur ≈ 1,7. L1 (la recherche et « Ses
colonnes », code déjà écrit sur `lot/US-0580/L3b`, à rebaser sur `epic/EP-16`) vient juste après
US-0590 ; L2 (l'administration et le portefeuille, écrans qu'EP-16 ne change pas) peut le suivre ;
L3, L4 et L5 viennent en fin d'EPIC, après les lots d'écran qu'ils décrivent — ceux d'US-0703
compris, depuis le recadrage du 2026-10-28 — et avant le gel du contrat (US-0640/L5), qui vient en
dernier. L6 #1583 (décision de l'auteur du 2026-10-28) corrige
#1580 : l'écran du plan de charge agrégé (`portfolio/workload/page.tsx`) conserve l'horizon, le
seuil de sous-charge et le filtre en préférences d'affichage au lieu de paramètres de l'adresse
(WF-PTF-0060-A, WF-ADM-0040, WF-IHM-0060), puis la phrase de `FBS-2.2.md` qui le décrit ; elle se
place avant le gel, au cas où `DisplayPreferences` n'aurait pas où ranger ces préférences, et
dépend d'US-0670/L2. La conception d'EP-15
(« L'aide en ligne et les infobulles ») fait foi pour la mécanique. Un lot d'EP-16 qui ajoute un
code à la table des fonctions l'inscrit dans `SCREENS_TO_COME` avec le lot de cette US qui l'écrit
(US-0620/L2 pour FBS-3.1.3), sans quoi le test de complétude échoue.

**Hors périmètre.** La version anglaise elle-même (EP-11, après la décision de l'auteur) ; un
tutoriel guidé ; une documentation hors de l'application ; les défauts d'écran que les aides
révèlent, qui deviennent des constats (#1438 → EP-17).

---

## US-0680 — Déclarer survenu un risque avec son compte rendu préalable

- **statut** : en cours
- **exigences** : aucune en propre ; le service clôt WF-RIS-0060 en EP-08
- **opérations** : `getRiskOccurrenceReport`, ajoutée au contrat ; `declareRiskOccurrence`,
  `getRisk`, `listNodes`
- **issue** : #1448

**En tant que** chef de projet, **je veux** lire, avant de confirmer la survenance d'un risque, ce
qu'elle ferait de la structure principale — les tâches et les lignes du devis propre ajoutées, la
ligne de provision retirée, la tâche porteuse modifiée — et du reste à engager, **afin de** déclarer
un risque survenu en sachant ce que la révision en cours deviendra.

**Critères d'acceptation.**

- propre à l'US : une lecture du contrat rend, sans rien écrire, ce que la survenance ferait : les
  tâches et les lignes du devis propre en `+` sous la tâche qui porte la provision — ou après elle
  quand c'est un jalon —, la ligne de provision en `-`, la tâche porteuse en `M`, le montant de la
  provision retiré du reste à engager, et les refus qui s'opposeraient à la fusion ; elle est refusée
  pour un risque qui n'est pas identifié ; son exemple est engendré sur le risque 751 du témoin, dont
  le devis propre est décrit ;
- propre à l'US : « Déclarer survenu » montre ce compte rendu dans les marques `+`, `-`, `M`
  d'US-0500, dit le retrait de la provision, puis confirme ou abandonne ; la confirmation porte les
  compteurs lus, et une version périmée (412) propose de relire ; la survenance confiée au worker
  est suivie comme une fusion ;
- propre à l'US : l'écart écrit sous US-0520 (EP-15) pour ce compte rendu est levé.

**Notes de réalisation.** #1383, décision de l'auteur du 2026-10-23 (« d'EP-16 ») et option (a)
retenue au recadrage du 2026-10-25 : l'écart est calculé par le serveur, comme pour l'avenant
(C-361). Le dialogue réemploie celui du compte rendu de fusion d'US-0510b. Deux lots : le contrat et
le témoin, puis le front.

**Hors périmètre.** La fusion elle-même et ses effets sur les montants (WF-RIS-0060) : le service,
EP-08.

---

## US-0690 — L'adresse de retour de la connexion durcie

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #1449

**En tant qu'** administrateur, **je veux** qu'une adresse de retour forgée après la connexion ne
mène jamais hors de Waterfall, **afin qu'** un lien reçu ne serve pas à détourner une session vers un
autre site.

**Critères d'acceptation.**

- propre à l'US : l'adresse de retour après la connexion refuse tout caractère de contrôle —
  tabulation, saut de ligne et les autres —, par la même garde qu'`isScreen` emploie pour les
  écritures retenues (#1181, point 5), que les deux partagent ; `/\t/elsewhere` et `/\n/elsewhere`
  sont refusés par un test, et les adresses déjà refusées (`//`, `/\`) le restent (#1429).

**Notes de réalisation.** Un seul lot, dont l'issue est celle de l'US. Gardé en EP-16 par la règle
du recadrage du 2026-10-25 : une redirection ouverte est du durcissement (sécurité) ; les deux
défauts du front proposés avec lui (#1438, #1428) sont partis à EP-17.

---

## US-0700 — Le filtre des écarts d'un différentiel, et le décompte de la matrice des risques

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : `listNodes`, `compareRevisions` (filtre `difference`, ajouté) ;
  `getProjectRiskMatrix`, `getPortfolioRisks` (`cells` précisé)
- **issue** : #1450

**En tant que** chef de projet, **je veux** ne voir que les écarts d'un différentiel ou d'une
comparaison de révisions quand je le demande, et que le décompte par case de la matrice des risques
compte les mêmes risques que ses bulles, **afin de** relire un avenant de mille tâches sans chercher
ses lignes à la main, et de lire une matrice qui ne se contredit pas.

**Critères d'acceptation.**

- propre à l'US : un filtre `difference`, aux valeurs `added`, `removed` et `modified` combinables,
  partagé par la lecture des nœuds et la comparaison des révisions, retient les nœuds dont l'écart
  est l'une des valeurs, leurs ancêtres compris ; l'arbre filtré reste un arbre ; sur la structure
  principale et le devis propre d'un risque, où `difference` est nul, le contrat dit ce qu'il fait
  (#1398, décision de l'auteur du 2026-10-23) ;
- propre à l'US : « Écarts seulement » s'offre sur la grille de planning et la grille de devis d'un
  différentiel et sur l'écran de comparaison, s'écrit dans l'adresse, se dit dans le bandeau des
  filtres actifs, et la grille relit ;
- propre à l'US : le décompte par case de la matrice des risques (`cells`) compte les seuls risques
  identifiés, comme les bulles, et le contrat le dit ; le front ne compte rien ; les totaux de
  provisions restent sur les trois états (#1395, part contrat ; WF-RIS-0040).

**Notes de réalisation.** Les décisions de l'auteur du 2026-10-23 dans #1398 et #1395 font foi ; les
« à trancher au lot » qu'elles nomment — les totaux sous le filtre, la structure sans écart — se
tranchent au lot de contrat et s'écrivent dans `DECISIONS.md`. La part front de #1395 et quatre
des cinq autres ajustements de la validation du 2026-10-23 (#1396, #1397, #1399, #1400) sont d'EP-17
(règle du recadrage du 2026-10-25) ; le cinquième, #1401, est rendu à EP-16 (« Constats reçus »).

**Hors périmètre.** La pagination d'un différentiel, écartée par #1193 et #1201 ; tout filtre qui
calculerait côté front.

---

## US-0701 — Le contrat rattrape la spécification 1.0.0

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : `getIdentitySyncSchedule`, `setIdentitySyncSchedule`, `resendInvitation`,
  `updateCostStructure`, ajoutées au contrat ; celles que touchent les bloquants et les majeurs de
  modèle et de calcul de la revue du 2026-10-28 — dont `exitProject`, `getSystemStatus`,
  `getReferenceSettings`, `listAuditEvents`, `getBackupSchedule`, `setBackupSchedule`,
  `setContributors`, `listRevisions`, `mergeCostStructure`, `createCostStructure`,
  `compareRevisions`, `listNodes`, `createNode`, `updateEstimateLine`, `setPredecessors`,
  `deleteNode`, `undoLastChange`, `redoLastUndo`, `updateRisk`, `declareRiskOccurrence`,
  `getProjectRiskCoverage`, `getProjectIndicators`, `getProjectWorkload`, `openImport`,
  `getImport`, `requestExport`, les vues du portefeuille ; la liste par famille est dans la
  conception
- **issue** : #1598

**En tant que** développeur, **je veux** que le contrat dise, avant d'être figé, ce que la
spécification 1.0.0 exige depuis ses passes des 9, 10 et 22 octobre, **afin que** les EPIC de
domaine servent un contrat qui ne contredit pas la spécification, et qu'aucun changement de sens
d'un champ existant ne vienne après le gel.

**Critères d'acceptation.**

- propre à l'US : chaque bloquant et chaque majeur de la revue du 2026-10-28 rangé sous US-0701
  dans la conception est soldé.
  - Appliqué : dans `docs/api`, avec ses exemples, le faux back et le témoin régénérés.
  - Ou écarté : avec sa raison, dans `DECISIONS.md`.
  - Une décision de `DECISIONS.md` que la spécification contredit est réécrite, en citant la date
    du changement de la spécification et la décision du recadrage.
- propre à l'US (L-01, décision de l'auteur du 2026-10-28) : les montants budgété et réestimé
  d'une ligne, d'une tâche, des totaux, des indicateurs et de la comparaison sont « inflation
  comprise, à l'année de consommation » ; le montant aux taux de l'année de référence, avant
  inflation, est le seul autre montant de la ligne, et `inflated_amount` disparaît. Les décisions
  #235 et #352 sont réécrites. Sur le témoin, une ligne dont la tâche se place deux ans après
  l'année de référence, avec une inflation de 2 %, a un montant réestimé supérieur de 4,04 % à son
  montant aux taux de l'année de référence (WF-DEV-0050).
- propre à l'US (D-01) : la sortie d'un projet qui porte une révision en cours reçoit le sort de
  cette révision — la marquer, avec un nom de version, ou l'abandonner — et la refuse sans lui ;
  marquer rend 202 et une tâche de fond, abandonner rend 200. L'exemple de la sortie montre que
  « après la sortie, le projet n'a plus de révision en cours, et ses indicateurs se lisent dans sa
  dernière révision marquée » (WF-CYC-0090).
- propre à l'US (E-01) : chaque structure porte sa date de début de planning, que
  `updateCostStructure` écrit et qui redate les tâches automatiques sans prédécesseur ; un exemple
  montre qu'« avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs
  automatiques » (WF-PLA-0020). L'import MS Project la lit et le compte rendu présente son
  changement (I-03, K-05).
- propre à l'US (H-01, H-02, M-01, H-03) : le risque survenu porte son coût à la survenance, et la
  couverture le compare à la réserve ; sur le témoin, « la terminaison des tâches issues d'un risque
  survenu ne change ni le coût des survenus ni l'écart de couverture » (WF-RIS-0050). La provision
  d'un risque survenu ou écarté est celle qu'il portait dans la révision de référence, nulle s'il
  n'y était pas identifié.
- propre à l'US (H-04) : la probabilité d'un risque ne s'écrit que par le réexamen ; la
  modification d'un risque ne la reçoit plus.
- propre à l'US (A-02, A-03, A-04, C-02) : la périodicité de la lecture des comptes se lit et se
  règle, quotidienne par défaut ; l'écran d'état reçoit les paramètres d'exploitation du §4.5.1,
  dont la durée de validité du cache ; le courriel de fixation du mot de passe se renvoie ; la
  devise se lit par toute session ouverte.
- propre à l'US (E-06) : l'historique annulable reste tenu par le serveur ; le contrat dit sa
  session (le jeton), sa pile par révision et par utilisateur, sa fin au marquage et à l'abandon, et
  au moins cinquante niveaux.
- propre à l'US (I-09) : la date de terminaison d'une tâche terminée par un import est la date de la
  revue que porte le fichier, connue dès l'analyse ; l'export du reste à engager reçoit cette date,
  le jour par défaut ; la fusion garde le jour de son application.
- propre à l'US (F-06) : `listNodes` se filtre sur chaque colonne des trois grilles, par les bornes
  et les périodes de la convention du README du contrat.

**Notes de réalisation.**
- Les décisions du recadrage du 2026-10-28 sont écrites dans la conception, « Le recadrage du
  2026-10-28 » ; pour tout majeur où la spécification est claire, la règle est de la suivre et de
  réécrire la décision antérieure contredite.
- K-04 (`amendment_merge` devient `structure_merge`) touche l'énumération qu'US-0640/L6b #1594
  modifie : il se fait dans ce lot, ou après lui, selon le plan de lots.
- Les mineurs ne sont pas de l'US, sauf ceux d'un fichier qu'un lot modifie déjà.

**Hors périmètre.** Les écrans (US-0703) ; la forme des refus (US-0702) ; le service.

---

## US-0702 — Une seule forme pour chaque refus

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : toutes celles qui déclarent un refus d'état, un code d'`ErrorCode` ou un compteur
  — dont `createTimeline`, `deleteTimeline`, `generatePlanningSkeleton`, `exitProject`,
  `markRevision`, `abandonRevision`, `createRevision`, `designateReferenceRevision`,
  `createCostStructure`, `deleteNode`, `setTaskProgress`, `setNodeTracking`,
  `declareRiskOccurrence`, `deleteRisk`, `deleteSubproject`, `requestExport`,
  `getBackgroundTaskResult`, `setActualCostTrackedScope`, `undoLastChange`, et les trois listes du
  référentiel sans le 403 d'`include_inactive`
- **issue** : #1599

**En tant que** développeur, **je veux** qu'un même refus ait partout le même statut, le même code
et ses paramètres, avec un exemple, **afin que** le service et le front n'aient qu'un chemin par
refus, et que le gel ne fige pas un catalogue qui porte des codes que rien ne rend.

**Critères d'acceptation.**

- propre à l'US : chaque bloquant et chaque majeur de la revue rangé sous US-0702 dans la
  conception est soldé, comme pour US-0701.
- propre à l'US (D-05, J-01, J-02, décision de l'auteur du 2026-10-28) : un projet terminal et une
  révision marquée se refusent partout par 409 `STATE_FORBIDS_OPERATION` et leur
  `missing_condition` ; `PROJECT_TERMINAL` et `REVISION_MARKED` sortent du catalogue ; les décisions
  L42k et US-0640/L1 #803 sont réécrites.
- propre à l'US (J-03, J-11) : chaque code d'`ErrorCode` et chaque `CommandCondition` est rendu par
  au moins une opération, avec un exemple, ou retiré.
- propre à l'US (E-07) : l'annulation d'une modification reprise depuis est refusée par un code qui
  nomme l'objet en conflit ; un exemple montre que « l'annulation d'une modification qu'un autre
  contributeur a depuis reprise est refusée en nommant l'objet en conflit » (WF-IHM-0110).
- propre à l'US (J-07, J-10) : le 500 est déclaré, avec son `correlation_id` ; une propriété
  inconnue de `fields` se refuse comme les autres paramètres de requête, par 422.
- propre à l'US : les refus que la revue relève sans code, condition ni exemple ont les trois (D-03,
  E-05, E-12 à E-14, F-03 à F-05, F-11, H-08, I-06, I-17, A-05, C-01).
- propre à l'US (décision de l'auteur du 2026-10-28) : `abandonRevision`, `exitProject`,
  `designateReferenceRevision`, `deleteRisk` et `deleteSubproject` exigent le `lock_version` et
  déclarent le 412 ; le `PUT` du périmètre suivi des coûts réels reste idempotent, sans compteur,
  et cette exception est écrite.

**Notes de réalisation.** La règle de L42a — « le refus d'une commande qu'un état rend indisponible
est `STATE_FORBIDS_OPERATION` » — devient celle de tout le contrat ; le README du contrat la dit.

**Hors périmètre.** Les messages des refus aux écrans (US-0703).

---

## US-0703 — Les écrans adoptent le contrat aligné

- **statut** : à faire
- **exigences** : aucune en propre
- **opérations** : celles qu'US-0701 et US-0702 ajoutent ou modifient, côté front
- **issue** : #1600

**En tant que** chef de projet, manager ou administrateur, **je veux** que les écrans montrent et
demandent ce que le contrat aligné décrit, **afin que** la maquette figée avec le contrat soit celle
que les EPIC de domaine serviront, et que les aides des derniers lots d'US-0670 décrivent des écrans
qui ne changeront plus.

**Critères d'acceptation.**

- propre à l'US : la confirmation de la sortie d'un projet qui porte une révision en cours demande
  de la marquer, avec un nom de version, ou de l'abandonner ; une sortie qui marque suit sa tâche de
  fond comme un marquage.
- propre à l'US : la grille de planning présente et fait saisir la date de début de planning de la
  structure ; le compte rendu d'un import MS Project dit son changement.
- propre à l'US : la grille de devis présente le montant aux taux de l'année de référence et le
  montant réestimé inflation comprise, et ne présente pas le montant budgété ; les totaux, les
  indicateurs et la comparaison suivent le sens nouveau des montants.
- propre à l'US : la fiche et le registre des risques disent le coût à la survenance d'un survenu ;
  la modification d'un risque ne fait plus saisir sa probabilité, que seul le réexamen change.
- propre à l'US : la devise s'affiche avec chaque montant, pour toute session.
- propre à l'US : l'administration fait régler la périodicité de la lecture des comptes et renvoyer
  le courriel de fixation du mot de passe ; l'écran d'état présente les paramètres d'exploitation,
  dont la durée de validité du cache.
- propre à l'US : chaque refus qu'US-0702 change de forme se dit à l'écran par son code et ses
  paramètres, sur un exemple du contrat, et aucun test ne garde une enveloppe disparue.
- propre à l'US : un manque du contrat que cette adoption révèle est corrigé au contrat, dans l'US.

**Notes de réalisation.** Les aides d'US-0670/L4 et L5 décrivent les écrans qu'US-0703 laisse :
elles en dépendent. Les filtres de colonnes des grilles (F-06) ne sont pas de l'US : EP-17.

**Hors périmètre.** Les filtres de colonnes des trois grilles (EP-17) ; les mineurs de la revue.

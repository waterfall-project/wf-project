---
id: EP-36
titre: Durcir les tests et la preuve des exigences — attentes des parcours, gardes du harnais, tests instables, citations, renvois de la roadmap
statut: prêt
depend_de: EP-08, EP-11
famille: front, back
issue:
---

# EP-36 — Tests et preuve des exigences

## Objet

« Close » n'est pas « prouvée » : la revue du 2026-11-14 relève des parcours dont les attentes sont
trop faibles, des gardes absentes du harnais, des exigences citées de travers, et des renvois de la
roadmap qu'aucun EPIC ne porte. S'y ajoutent les constats mineurs sur des tests que les revues des
lots ont laissés ouverts. Les lots de cet EPIC touchent des fichiers distincts : c'est le seul qui
se parallélise sur tous les créneaux du poste, et il se glisse là où des créneaux sont libres.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Ses US et sa conception datent du cadrage du
2026-11-21, validées par l'auteur le même jour.

## Ce qui en fait partie

- trois phrases de Vérif que la roadmap dit constatées sans qu'un test du back les cite (US-3360) ;
- les parcours joués contre le service dont l'attente ne prouve pas ce que leur titre cite :
  l'arborescence de tâches et son export, le filtre du plan de charge, le journal des imports et le
  réimport après une exclusion (US-3370) ;
- les parcours qui laissent le référentiel modifié, passent à vide ou échouent tard, et le compte
  des bulles du portefeuille par un détail d'ECharts (US-3380) ;
- la flèche d'une liaison du Gantt, nommée, pour qu'un parcours ne la trouve plus par une classe
  de la charte (US-3390) ;
- les tests instables : le Kanban sous charge, deux parcours vus en échec une fois ou deux
  (US-3400, US-3410) ;
- les tests de composants qui promettent plus qu'ils n'éprouvent (US-3400, US-3420), et le test
  d'en-tête du reste à engager (US-3410) ;
- le harnais des tests du front : le texte rendu lu sans expression régulière, la sortie d'erreur
  refusée au projet `node` (US-3430) ;
- les gardes des sources du front : la typographie des catalogues, les sauts de parcours ; et trois
  commentaires périmés (US-3440) ;
- les citations d'exigences : ce que `make requirements` ne lit pas le fait échouer, et les
  citations fautives sont corrigées (US-3450) ;
- les tests du back : marqueurs, aides partagées, fichier vide (US-3460), et les bornes des corps
  que le service redéclare, tenues au contrat (US-3470) ;
- la règle d'import-linter étendue aux imports hors de l'interface d'un module, depuis l'API, le
  worker et le témoin (US-3480) ;
- la roadmap : les renvois de portée et les titres des tableaux contrôlés par `make roadmap`, les
  fichiers livrés corrigés, et chaque phrase de Vérif renvoyée à un EPIC qui ne la porte pas
  rendue à son porteur (US-3490).

## Ce qui n'en fait pas partie

- la preuve de WF-PLA-0090-A par un test du service — EP-32 (US-3290), avant la porte de
  publication ;
- la porte de publication elle-même — EP-13 (US-3000) ;
- les mesures de performance — EP-40 ;
- le parcours au volume qui citera WF-IHM-0080-A sur le marquage d'une révision de dix mille
  objets (#4446) — EP-40, après EP-13 ; les citations de WF-ADM-0160-A par les tests de la
  restauration d'EP-13 (#4447) — EP-39. EP-36 ne garde de ces deux constats que la correction des
  renvois de la roadmap (US-3490), et reste sans préalable sur EP-13 (décision de l'auteur du
  2026-11-21) ;
- l'alignement des compteurs `lock_version`, nés à 0 ou à 1 selon la table (#4456) — EP-38 ;
- le renvoi de WF-RAE-0020 à WF-IND-0010 (#4457) — la spécification 1.0.9, qui l'écrit ;
- les bulles de l'écran des risques d'un projet, que `risks.spec.ts` trouve par un détail d'ECharts
  (FTE-09) — EP-30 (US-3160), qui redessine ce graphique et réécrit ce parcours ;
- faire lire à `make requirements` l'étiquette `@shared` d'un parcours, ou déplacer
  `planning-service.spec.ts` sous `e2e/service/` — écartés au cadrage : une exigence close par un
  EPIC du back se prouve par un test du back ou de `e2e/service/`, et un parcours `@shared` dont
  l'attente contre le service est faible (FTE-03, FTE-04) compterait à tort ;
- l'audit et le parcours au Tab des écrans rejoués en anglais, la page de fixation du mot de passe
  et le parcours au Tab du thème de connexion (FTE-08, a et b) — écartés au cadrage : aucun écart
  n'est connu, et ce sont des parcours lents ;
- une garde des clés de catalogue inemployées (FTE-07) — écartée au cadrage : une heuristique à
  entretenir à chaque clé composée à l'exécution ;
- la réécriture des US livrées d'EP-06 et d'EP-07 pour qu'elles citent WF-IHM-0030, 0040 et 0050
  (RMP-09) — écartée au cadrage : leurs tests citent déjà ces exigences ;
- la marge de 3,5 points sous la grille du reste à engager à 1280 × 720 (#3997) et les branches
  dupliquées de `_spread_after` (#3916) — sans suite : aucune n'est un défaut aujourd'hui.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Comme EP-17,
EP-18 et EP-23 (décision de l'auteur du 2026-10-28), une US dont les tests éprouvent une phrase de
Vérif cite son exigence, avec tout son Vérif ; les phrases qu'elle ne touche pas sont des écarts qui
disent qui les constate. Une US qui ne porte qu'un outil, une garde ou le ménage de tests n'en cite
aucune, comme celles d'EP-28. La portée des exigences citées reste celle des EPIC qui les ouvrent et
les closent : `WF-DAT-0100-A` (close par EP-07), `WF-DAT-0070-A`, `WF-DEV-0070-A`, `WF-CRE-0030-A`
et `WF-CRE-0050-A` (EP-09), `WF-IHM-0030-A` (EP-02), `WF-PLA-0090-A`, `WF-PLA-0110-A` et
`WF-PLA-0120-A` (EP-06), `WF-IHM-0100-A` (EP-14), `WF-IHM-0170-A` (EP-27).

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Aucune modification du contrat : aucune opération ne manque, aucune ne change de forme.

Consommées par les tests que l'EPIC écrit ou corrige, sans changement : `createNode`,
`setPredecessors`, `updateTaskFacet`, `listNodes`, `createRisk`, `updateRisk`,
`updateRiskProvision` (US-3360) ; `listNodes`, `requestExport`, `getBackgroundTask`,
`getBackgroundTaskResult`, `getProjectWorkload`, `listOrgNodes`, `uploadFile`, `openImport`,
`applyImport`, `listCostImports`, `listActualCosts`, `setActualCostTrackedScope` (US-3370) ;
`getReferenceSettings`, `updateReferenceSettings`, `getPortfolioRisks` (US-3380) ; `listNodes`
(US-3390) ; `createAccessRole` (US-3420) ; les écritures dont le service redéclare le corps —
`createProject`, `updateProject`, `createSubproject`, `updateSubproject`,
`updateReferenceSettings`, et celles des calendriers, des types de coût, des nœuds d'organisation,
des rôles et des chronologies (US-3470).

## Préalables

EP-08 et EP-11 fusionnés, dont les tests suivent le code : EP-08 livre les risques qu'US-3360
éprouve et les imports qu'US-3480 fait passer par l'interface, EP-11 le portefeuille d'US-3380 et
le contrôle de `wftools.coverage` (#4374) sur lequel US-3450 s'appuie.

Deux US attendent un autre EPIC dans `main`, puis sa reprise par `epic/EP-36` ; les autres ne
l'attendent pas (décision de l'auteur du 2026-11-21 : EP-36 reste de la vague 1, quelques lots
attendent) :

- US-3390 attend EP-32, dont US-3350 réécrit le placement des liaisons du Gantt ;
- US-3480 attend EP-32, qui touche l'interface de `core/planning`, et EP-33, dont US-3270 réexporte
  la borne du code de sous-projet qu'`api/subprojects.py` importe aujourd'hui d'un fichier privé.

Décisions de l'auteur du 2026-11-21, au cadrage, que les US portent : les preuves de #4446 et de
#4447 reportées après EP-13, à EP-40 et à EP-39 ; les compteurs `lock_version` (#4456) à EP-38 ;
les bulles des risques (FTE-09) à EP-30, la flèche du Gantt gardée ici après EP-32 ; `make
requirements` ne lit pas `@shared` ; de l'accessibilité (FTE-08), le seul compte des déclencheurs ;
la garde de la sortie d'erreur posée sur le projet `node`, tous ses échecs corrigés (FTE-06) ; des
catalogues (FTE-07), les six textes et une garde typographique, sans garde des clés inemployées ;
la garde des sauts de parcours (FTE-12) ; de RMP-09, le seul test du back sur la gravité et la
provision d'un risque ; les trois lignes de `role-creation.tsx` corrigées avec leur test (#3461),
la marge de #3997 et `_spread_after` de #3916 sans suite. Celle du 2026-11-17, sur #3789 : `make
requirements` refuse une citation qui n'est pas écrite en toutes lettres.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs :
jusqu’à 6.

## Définition de fini

- trois tests du back citent `WF-DAT-0100-A` sur deux tâches de quatre heures liées fin à début,
  `WF-DAT-0070-A` sur une tâche modifiée par un utilisateur, `WF-IHM-0030-A` sur la gravité et la
  provision d'un risque, et `make requirements` les compte ;
- contre le service, le parcours de l'arborescence échoue quand la lecture ne rend aucune
  récapitulative sur le témoin ou que l'export échoue ; celui du plan de charge, quand le filtre
  par nœud laisse un rôle qui n'en relève pas ; celui des coûts réels, quand le journal n'a pas
  l'entrée du jour avec ses comptes ou qu'un second import rend la ligne exclue au périmètre ;
- deux passages de suite de `make e2e-service` sur une même plateforme laissent la matrice des
  risques et les seuils des indices du témoin ; un test « ce qu'un geste ouvre » échoue quand il ne
  trouve pas les déclencheurs que son écran doit offrir ;
- aucun parcours ne trouve un élément du Gantt par une classe de la charte, ni une bulle du
  portefeuille par `path[fill-opacity='0.85']` ;
- `kanban.dom.test.tsx` passe cinquante fois de suite sur un poste chargé, sans écriture de React
  sur la sortie d'erreur ; les deux parcours vus en échec (#4140, #4141) ont leur cause établie et
  corrigée, ou sont classés avec leur raison ;
- un test `node` du front qui écrit sur la sortie d'erreur échoue, et aucun test du front ne
  filtre du HTML par expression régulière ;
- une apostrophe droite dans le catalogue français, des guillemets français dans le catalogue
  anglais, un `test.skip` sans condition, un `fixme` ou un `.only` dans un parcours font chacun
  échouer `make check-front` ;
- `make requirements` échoue sur une citation par une constante et sur une citation sans indice de
  révision, et il n'en reste aucune ;
- une borne changée dans le schéma d'un corps que le service redéclare fait échouer un test du
  back, qui nomme l'opération et le champ ;
- `make imports-back` échoue sur un import, depuis l'API, le worker ou le témoin, d'un fichier d'un
  module du noyau hors de son interface, et il n'en reste aucun ;
- `make roadmap` échoue sur une portée dont l'autre bout ne répond pas et sur un titre d'exigence
  périmé, et passe sur les fichiers corrigés ; les renvois « constaté par EP-06 » et le renvoi
  circulaire de WF-IHM-0080-A nomment leur porteur ;
- `make check` passe sur la branche de l'EPIC, la file de fusion est verte ; `make roadmap`,
  `make requirements` et `make readmes` passent ;
- les constats reçus sont fermés par la fusion de leur lot, ou reportés à l'EPIC que leur ligne
  nomme.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3916 — back : trois reprises mineures des tests du lot #3802 (citation de WF-DEV-0090-A, somme
  reconnue par GROUP BY, branches dupliquées de _spread_after) → US-3460 ; `_spread_after` sans
  suite ;
- #3921 — back : le module de tests de clôture d'US-1670 importe ses aides de test_indicators_stored
  et copie ses fixtures → US-3460 ;
- #3997 — test : le test d'en-tête du reste à engager ne prouve pas la largeur naturelle des
  commandes, et la grille ne garde que 3,5 points à 1280 × 720 → US-3410 ; la marge sans suite ;
- #3521 — front : une assertion arbitraire et un double serve() dans le test de l'export retrouvé
  (revue 2 d'US-2310/L1) → US-3420 ;
- #3461 — test : la création d'un rôle attend la relecture d'une écriture perdue sans test qui
  l'éprouve → US-3420, les trois lignes de `role-creation.tsx` comprises ;
- #3595 — test : le test des relectures du Kanban promet un refus qu'il n'éprouve pas → US-3400 ;
- #3788 — front : le test du collage sous repli affirme ses sommaires par construction → US-3420 ;
- #3907 — front : le test du signal de fin de mesure n'éprouve ni la cellule non marquée ni
  l'adresse attendue → US-3420 ;
- #3908 — front : le test de la relecture comparée ne joue ni l'écriture en cours échouée ni celle
  sans changement → US-3420 ;
- #3909 — e2e : reachByKeyboard n'échoue tôt que sur la dernière cellule de la rangée → US-3380 ;
- #3937 — qualité : les tests du front qui filtrent encore du HTML par expression régulière
  → US-3430 ;
- #4000 — front : kanban.dom.test.tsx instable sous charge (act non attendu) → US-3400 ;
- #4140 — front : admin.spec.ts:572 attend « Service des achats » et reçoit « Aucun » (une fois, en
  local ; revu dans la file d'EP-13 le 2026-11-20) → US-3410 ;
- #4141 — front : remaining.spec.ts:441, page.waitForRequest sur une page fermée dans seedPlanning
  (une fois, en local) → US-3410 ;
- #3789 — outil : make requirements ignore une exigence citée par une constante → US-3450.

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4444 — deux phrases de Vérif closes par un renvoi « constaté par EP-06 » qu'EP-06 ne porte pas
  (RMP-06) → US-3360 pour les tests, US-3490 pour les renvois ;
- #4445 — un parcours laisse la matrice de risques et les seuils modifiés (FTE-02) — reste d'un
  majeur → US-3380 ;
- #4446 — WF-IHM-0080-A close par un renvoi circulaire, sans test au volume qui la cite (RMP-03) —
  reste d'un majeur → reporté → EP-40 pour le parcours au volume ; US-3490 corrige le renvoi ;
- #4447 — WF-ADM-0160-A reste close par EP-04, sans citation dans les tests d'EP-13 qui la tiennent
  (RMP-04) — reste d'un majeur → reporté → EP-39 pour les citations ; US-3490 corrige le critère
  d'EP-04 ;
- #4448 — les parcours du front : attentes trop faibles ou fragiles (FTE-03, FTE-04, FTE-05, FTE-08,
  FTE-09) → US-3370 (FTE-03, FTE-04, FTE-05), US-3380 (FTE-08 pour le compte des déclencheurs,
  FTE-09 pour le portefeuille), US-3390 (FTE-09 pour le Gantt) ; les bulles des risques de FTE-09
  reportées → EP-30 ; le reste de FTE-08 écarté ;
- #4449 — les tests du front : gardes manquantes du harnais et des sources (FTE-06, FTE-07, FTE-12)
  → US-3430 (FTE-06), US-3440 (FTE-07, FTE-12) ; la garde des clés inemployées écartée ;
- #4450 — les tests du front : commentaires périmés (FTE-10, FTE-14) → US-3440 ;
- #4451 — les tests : citations d'exigences, et ménage (BAC-10, BRC-10, FCO-13, FAR-05) → US-3450
  (FCO-13, FAR-05), US-3460 (BAC-10, BRC-10) ;
- #4452 — les corps redéclarés à la main ne sont tenus au contrat par aucun test (CTC-05)
  → US-3470 ;
- #4454 — les imports hors de l'interface d'un module, et la règle d'import-linter (BRC-09)
  → US-3480 ;
- #4455 — la roadmap : renvois de portée, titres, fichiers livrés (RMP-08, RMP-09, RMP-13) — un
  contrôle de `wftools.roadmap` → US-3490 (RMP-08, RMP-13), US-3360 (RMP-09, pour le seul test des
  risques) ;
- #4456 — les compteurs `lock_version` : la dette remise à la v1, sans porteur (RMP-10) → reporté
  → EP-38 ;
- #4457 — la spécification : WF-RAE-0020 renvoie à WF-IND-0010 pour une révision marquée (SPB-12)
  → corrigé par la spécification 1.0.9.

Reçu du cadrage d'EP-32 (« ce que `make requirements` ne lit pas d'un parcours joué contre le
service — EP-36 ») : écarté, voir « Ce qui n'en fait pas partie ».

## Conception

Écrite le 2026-11-21, après la validation des US par l'auteur le même jour, contre `main`
(985bbc198) et les branches `epic/EP-08` (5568efc89) et `epic/EP-11`, dont EP-36 part une fois
fusionnées. Courte, comme celles d'EP-18, d'EP-23 et d'EP-33 : chaque issue porte sa proposition,
ses lieux et ses tests, et fait foi pour le détail ; ce qui suit ne dit que ce qu'elles laissent
ouvert, ce qui s'en écarte, et ce que les décisions de l'auteur du 2026-11-21 y changent.

**Tables et migrations.** Aucune.

**Modifications du contrat.** Aucune : `docs/api/DECISIONS.md` ne reçoit aucune entrée, et ni le
client ni les modèles ne sont régénérés.

**Modules du noyau touchés.** Aucun ne change de comportement. US-3480 ajoute des réexports à trois
interfaces — `CommandAvailability` à celle de `core/cost_settings`, `Duration`, `DurationUnit` et
`LagUnit` à celle de `core/planning`, `Written` à celle de `core/estimate` — sans déplacer aucun
objet. Hors du noyau, le code de production ne change qu'en deux endroits du front : trois lignes
de `admin/role-creation.tsx` (US-3420), et le tracé d'une liaison dans `gantt/gantt.tsx`, avec une
clé des catalogues (US-3390).

**Les outils du dépôt.**

- `wftools.coverage` (US-3450). Une marque `requirement` ou `story` dont un argument n'est pas une
  chaîne écrite en toutes lettres est une erreur de lecture, comme l'est déjà une forme d'appel
  inconnue dans un titre TypeScript : le relevé échoue en nommant le fichier et la ligne. Un titre
  qui porte entre crochets un identifiant d'exigence sans indice échoue de même. Rien n'est résolu
  ni deviné. La marque `unexecuted`, dont l'argument est une raison et non une citation, garde ses
  constantes.
- `wftools.roadmap` (US-3490). La portée d'une ligne se lit selon trois formes, et toute autre
  échoue : `entière` ; `début — close en EP-x`, suivie ou non de `, amorcée aussi en EP-…` ; `fin —
  amorcée en EP-…`. Quatre contrôles : l'EPIC que nomme un « début » clôt l'exigence ; la liste
  d'un « fin » est celle des EPIC qui portent un « début » pour elle ; une exigence « entière »
  n'a de « début » nulle part ; un EPIC nommé par « amorcée aussi en » porte un « début » — sans
  exiger que cette liste soit complète, elle n'est qu'une aide. Le titre d'une ligne se compare à
  celui de la spécification, normalisé comme un Vérif l'est déjà. Le nombre d'exigences que le
  README énonce se compare à celui de la projection, hors l'exemple du §1.3.1. Relevé au cadrage
  sur `main` : dix-neuf portées sans répondant, dont une de forme inconnue (« fin — amorcée en
  EP-15, poursuivie en EP-16 », EP-11), et six titres périmés ; le lot corrige l'état que `main`
  porte à sa date, les lignes d'EP-08 et d'EP-11 comprises. `Row` gagne des champs et n'en change
  aucun : `wftools.coverage`, qui lit `roadmap`, n'est pas touché.
- import-linter (US-3480). Un contrat de plus dans `backend/pyproject.toml`, à côté de celui qui
  tient les modules du noyau entre eux : depuis `waterfall.api`, `waterfall.worker` et
  `waterfall.witness`, un module du noyau ne s'importe que par son `interface`. Les imports sous
  `TYPE_CHECKING` comptent, comme aujourd'hui. Quatre imports sont à faire passer par l'interface
  sur les branches d'EP-08 et d'EP-11 — `api/cost_types.py`, `api/numbering.py`,
  `witness/filling.py`, `witness/tasks.py` — ; un cinquième, celui d'`api/subprojects.py`, est
  corrigé par EP-33.

**Le harnais et les gardes du front.**

- La sortie d'erreur (US-3430). `refuseStderr` quitte `setup-dom.ts` pour `src/test/stderr.ts`, et
  le projet `node` reçoit sa mise en place, qui la pose comme celle du projet `dom`. `text`, dans
  `src/test/markup.ts`, s'appuie sur `textOfMarkup` : les aides du harnais sont le seul lieu où un
  rendu se lit.
- Les deux gardes d'US-3440 sont des tests `node`, chacun dans un fichier à lui : la typographie
  lit les deux catalogues ; les sauts lisent les sources de `e2e/**` par l'analyseur de TypeScript,
  non par expression régulière, et jugent le premier argument de chaque `test.skip`. Aucune ne
  touche `catalogue-terms.test.ts`, qu'US-3450 corrige.
- Les déclencheurs (US-3380) : une table dans `e2e/opened.ts` donne, par écran, le nombre de
  déclencheurs que le test doit au moins jouer, par largeur de fenêtre quand elles diffèrent ; le
  lot la remplit de ce que le parcours joue aujourd'hui, qu'il annote déjà.
- La flèche d'une liaison (US-3390) prend la forme du nom que la liaison en conflit porte déjà —
  le prédécesseur, le type, la ligne visée —, sans « en conflit » ; la liaison en conflit garde le
  sien.
- Le portefeuille (US-3380) : le parcours garde l'assertion que le dessin est visible, et compte
  les risques par la table des valeurs.

**La règle des mille lignes.** `make sources` refuse un fichier de plus de 1 000 lignes, tests
compris. `kanban.dom.test.tsx` en compte 998 : US-3400 en détache les tests de la relecture dans un
fichier à eux avant d'y ajouter l'étape du refus. `test_scheduling_examples.py` (877),
`test_nodes.py` (873), `gantt.tsx` (870), `test_access_evaluation.py` (854), `remaining.spec.ts`
(844) et `test_contract_declarations.py` (768) sont proches : un lot qui en ferait passer un
au-delà le scinde, il ne resserre pas ses lignes.

**Les EPIC voisins.**

- **EP-32** écrit `gantt.tsx` et `layout.ts` (US-3350) et l'interface de `core/planning` : US-3390
  et US-3480 l'attendent dans `main`. Il touche aussi `folded-runs.tsx`, pour le tracé d'un lien :
  US-3420 corrige un autre test du même fichier de tests, et ne l'attend pas. US-3360 ajoute un
  test à `test_scheduling_examples.py`, dont EP-32 ne change pas les dates.
- **EP-33** corrige l'import d'`api/subprojects.py` (US-3270) : US-3480 l'attend. Il change les
  bornes du code d'un sous-projet au contrat et dans le modèle local à la fois : US-3470 ne
  l'attend pas.
- **EP-30** réécrit les risques et leur parcours : le test des risques d'US-3360 a son fichier, et
  `risks.spec.ts` n'est pas touché.
- **EP-29**, **EP-34** et **EP-37**, pas encore cadrés, reprendront des fichiers où EP-36 ne
  change que des tests : `test_users_activation.py`, `test_access_evaluation.py`,
  `user-bulk.dom.test.tsx` et `role-creation.tsx` (EP-29), les tests de la grille (EP-34),
  `remaining.spec.ts` (EP-37). Leur cadrage lit cette liste.
- **EP-13** a modifié `test_contract_declarations.py` sur sa branche : US-3470 y ajoute des
  fonctions, et la reprise de `main` par `epic/EP-13` règle ce qui se chevauche.
- **La spécification 1.0.9** porte le nombre d'exigences à 224 : US-3490 écrit au README le nombre
  que `main` porte à sa date.
- Les catalogues (`messages/*.json`) et le guide (`docs/dev/README-fr.md`, `README.md`) reçoivent
  des lignes de plusieurs lots, à des endroits distincts, comme dans tout EPIC.

**Ordre de construction.**

1. Dès la branche tirée, EP-08 et EP-11 fusionnés : toutes les US, hors US-3390 et US-3480. Aucune
   ne dépend d'une autre.
2. Dans US-3430, la lecture du rendu par les aides du harnais précède la garde de la sortie
   d'erreur : les deux touchent les mêmes fichiers de tests de pages.
3. US-3450 corrige des citations dans deux fichiers que d'autres US corrigent aussi —
   `tasks/remount.dom.test.tsx` (US-3420) et `app/(home)/page.test.tsx` (US-3430) : ces lots ne se
   livrent pas en même temps.
4. US-3390 après EP-32 dans `main` ; US-3480 après EP-32 et EP-33 dans `main` ; `epic/EP-36`
   reprend `main` à chaque fois.

**Décisions prises.**

- **Deux preuves attendent EP-13 ailleurs** (#4446, #4447) : le parcours au volume va à EP-40, les
  citations des tests de la restauration à EP-39, et EP-36 ne corrige que les renvois. Écarté : une
  US d'EP-36 qui attendrait EP-13, et ferait de l'EPIC le dernier livré ; demander la citation aux
  lots d'EP-13, que l'auteur n'élargit pas.
- **Le relevé ne lit pas `@shared`.** Une exigence close par un EPIC du back se prouve par un test
  du back ou de `e2e/service/`. Écarté : compter un parcours `@shared` comme joué contre le service
  — cent quarante-six parcours deviendraient des preuves, dont ceux qu'US-3370 corrige parce que
  leur attente contre le service était faible ; déplacer `planning-service.spec.ts`, qu'EP-32
  touche.
- **Une citation illisible est refusée, non résolue** (décision de l'auteur du 2026-11-17, #3789).
  Écarté : résoudre une constante du même module — une lecture de plus à tenir juste ; une règle
  écrite au guide seule, que rien ne tiendrait.
- **Une citation sans indice se juge une à une** : l'indice si le test éprouve une phrase du Vérif,
  le retrait sinon. Écarté : ajouter l'indice partout — FAR-05 montre des tests qui parlent d'une
  exigence sans l'éprouver, et le relevé les compterait.
- **Les marqueurs de BAC-10 suivent le Vérif d'aujourd'hui.** La revue nommait WF-ADM-0090 et
  WF-ADM-0110 ; aucune phrase de leur Vérif en 1.0.8 n'est celle des deux tests. Ils citent l'US
  dont ils portent un critère, à moins que le lot ne trouve la phrase. Écarté : poser les marqueurs
  de la revue, qui gonfleraient le relevé.
- **Les fichiers des EPIC livrés se corrigent dans le lot du contrôle**, sur `epic/EP-36`. Écarté :
  les corriger dans la pull request du cadrage — le contrôle qui les vérifie n'existe pas encore.
  Qui clôt ne change nulle part.
- **Le README garde un nombre, que l'outil tient.** Écarté : retirer le nombre — la phrase dit que
  les exigences sont fixées, et le nombre la rend vérifiable.
- **Le compte des déclencheurs est un plancher.** Écarté : une égalité, qui ferait échouer le lot
  qui ajoute un dialogue ; la revue demande d'« échouer sur une baisse ».
- **Les bulles du portefeuille se comptent par la table des valeurs.** Écarté : un nom accessible
  par bulle, quatre cent vingt-neuf noms dans un dessin que la table dit déjà ; un attribut posé
  sur le tracé, que le rendu d'ECharts ne porte pas.
- **La flèche d'une liaison est nommée.** Écarté : un attribut `data-slot`, comme EP-25 l'a fait
  pour la puce d'un risque survenu — il trouve la flèche sans la dire à qui ne la voit pas.
- **La garde typographique est un test du front**, à côté de la garde des textes. Écarté :
  `wftools.catalogs`, qui tient les catalogues au contrat, non leur rédaction.
- **Aucune exemption à la garde de la sortie d'erreur** : la règle commune interdit de contourner
  une règle dans le code, et la liste nommée de la garde des sauts naît vide.
- **Une instabilité se ferme par sa cause**, ou se classe avec une hypothèse dans
  `tools/queue-known.toml`, l'issue restant ouverte. Écarté : fermer sur des passages verts seuls
  un parcours déjà vu en échec dans la file (#4140).
- **Trois paquets pour import-linter**, ceux que le constat nomme. `waterfall.restore`,
  `waterfall.bootstrap` et les migrations n'importent aucun fichier privé aujourd'hui, et ne sont
  pas inscrits. Les objets ne bougent pas : l'interface les réexporte.

---

## US-3360 — Trois phrases de Vérif closes sans preuve reçoivent le test du back qui les cite

- **statut** : à faire
- **exigences** : `WF-DAT-0100-A`, `WF-DAT-0070-A`, `WF-IHM-0030-A`
- **opérations** : `createNode`, `setPredecessors`, `updateTaskFacet`, `listNodes`, `createRisk`,
  `updateRisk`, `updateRiskProvision`
- **issue** :

**En tant que** développeur, **je veux** que trois phrases de Vérif que la roadmap dit constatées —
deux par un renvoi à EP-06, qui ne porte pas leurs exigences, une par EP-02 sur le seul faux back —
aient chacune un test du back qui la cite, **afin qu'** une régression du moteur de dates, des
colonnes d'audit ou de l'écriture d'un risque fasse échouer un test qui nomme l'exigence (#4444 ;
RMP-09 de #4455).

**Critères d'acceptation.**

- `WF-DAT-0100-A` — « Deux tâches de quatre heures liées fin à début, sur un calendrier de huit heures, commencent et finissent le même jour. » : un
  test du back, rangé avec les exemples de planification, fait dater par le moteur deux tâches de
  « 4 h » liées fin à début sur un calendrier de huit heures par jour, et affirme que les deux
  commencent et finissent le même jour — mêmes dates de début et de fin ; il cite l'exigence.
- `WF-DAT-0070-A` — « Après modification d’une tâche par un utilisateur, la ligne porte son compte et l’horodatage de la modification. » : un
  test du back modifie une tâche par l'API, sous le compte d'un utilisateur qui n'est pas celui qui
  l'a créée, puis relit `updated_by` et `updated_at` de sa ligne : le compte est celui de la
  modification, l'horodatage n'est pas antérieur à la requête ; il cite l'exigence.
- `WF-IHM-0030-A` — « La gravité et la provision d'un risque ne sont pas saisissables. » : la part
  que le service en doit : ni la déclaration d'un risque ni sa modification n'acceptent une gravité
  ou un montant de provision — un corps qui en porte un est refusé, et rien n'est écrit — ; un test
  du back le tient et cite l'exigence.
- propre à l'US : `make requirements` compte les trois tests sous leur exigence, dans la famille
  du back.
- écart : `WF-DAT-0100-A` — « La somme des montants budgétés d’une révision est identique quel que soit l’ordre de sommation. » : constaté par EP-07, inchangé.
- écart : `WF-DAT-0100-A` — « Une tâche planifiée au 30 juin s’affiche au 30 juin sur tout poste client, quel que soit son fuseau. » : constaté par EP-02 et EP-07, inchangé.
- écart : `WF-DAT-0100-A` — « Un montant de 0,10 additionné dix fois donne exactement 1,00. » : constaté par EP-03 et EP-07, inchangé.
- écart : `WF-DAT-0100-A` — « Un montant calculé de 75,705 est présenté 75,71. » : constaté par EP-07, inchangé.
- écart : `WF-DAT-0100-A` — « Sur une installation au fuseau de Paris, une saisie datée faite à 0 h 30, heure de Paris, propose le jour de Paris. » : constaté par EP-07, inchangé.
- écart : `WF-DAT-0100-A` — « Un nombre ou un montant calculé qui dépasse ce que sa colonne tient est refusé, au champ qui le provoque, sans rien écrire. » : constaté par EP-07, inchangé.
- écart : `WF-DAT-0070-A` — « Une ligne créée par un import porte le compte qui l’a confirmé. » : constaté par EP-09, inchangé.
- écart : `WF-DAT-0070-A` — « Une ligne mise à jour par un traitement automatique porte la plateforme comme auteur. » : constaté par EP-03 et EP-09, inchangé.
- écart : `WF-IHM-0030-A` — « Dans une grille de devis, le montant d'une ligne de main-d'œuvre n'est pas saisissable, et son apparence diffère de celle de la charge en heures. » : constaté par EP-02, et par les tests du back d'EP-07 qui citent l'exigence ; inchangé.
- écart : `WF-IHM-0030-A` — « La tentative de modifier la date de fin d'une tâche récapitulative est refusée en nommant ses subordonnées. » : constaté par EP-02, et par les tests du back d'EP-06 qui citent l'exigence ; inchangé.

**Notes de réalisation.** La proposition de RMP-06 fait foi pour les deux premiers tests. La phrase
des deux tâches n'a pas de chiffre : elle n'est pas dans `fixtures/examples.json`, et son test se
range avec les exemples de planification sans entrer dans la liste des exemples chiffrés. Le test
des risques vient après la fusion d'EP-08, dans un fichier à lui : EP-30 réécrit les risques, et
garde la règle (WF-RIS-0010). Les deux renvois « constaté par EP-06 » des fichiers d'EP-07 et
d'EP-09 sont corrigés par US-3490, qui nomme cette US.

**Hors périmètre.** Réécrire les US livrées d'EP-06 et d'EP-07 pour qu'elles citent WF-IHM-0030,
0040 et 0050 (RMP-09) : écarté par l'auteur le 2026-11-21. WF-IHM-0050 sera rouverte par EP-31
(#4398).

---

## US-3370 — Trois parcours joués contre le service affirment ce que leur titre cite : l'arborescence et son export, le filtre du plan de charge, le journal des imports

- **statut** : à faire
- **exigences** : `WF-PLA-0110-A`, `WF-PLA-0120-A`, `WF-DEV-0070-A`, `WF-CRE-0050-A`,
  `WF-CRE-0030-A`
- **opérations** : `listNodes`, `requestExport`, `getBackgroundTask`, `getBackgroundTaskResult`,
  `getProjectWorkload`, `listOrgNodes`, `uploadFile`, `openImport`, `applyImport`,
  `listCostImports`, `listActualCosts`, `setActualCostTrackedScope`
- **issue** :

**En tant que** développeur, **je veux** que les parcours de l'arborescence de tâches, du plan de
charge et des coûts réels affirment, quand ils se jouent contre le service, ce que l'exigence de
leur titre demande, **afin qu'** un service qui ne rend aucune récapitulative, ignore un filtre,
n'inscrit rien au journal ou réintègre une ligne exclue fasse échouer le parcours qui le cite
(FTE-03, FTE-04 et FTE-05, de #4448).

**Critères d'acceptation.**

- `WF-PLA-0110-A` — « Sur un planning de quatre niveaux, l’affichage demandé au niveau 2 ne représente que les récapitulatives des deux premiers niveaux, sous le nœud du projet. » : sa
  forme sur le témoin, contre le service : le parcours affirme la profondeur du témoin, écrite dans
  le parcours — celle qu'il affirme déjà contre le faux back —, et le libellé d'une récapitulative,
  au lieu de relire l'attendu par l'API ; une lecture qui rend une profondeur nulle sur PRJ-001 le
  fait échouer, et la branche qui affirmait « Ce planning n'a aucune tâche récapitulative » sur le
  témoin disparaît.
- `WF-PLA-0120-A` — « L’export d’un planning de trois niveaux produit un fichier PNG dont le premier niveau est disposé horizontalement et les suivants verticalement. » : la
  part que le parcours en doit : contre le service, il attend que la tâche d'export soit
  « Réussie », télécharge l'image et la passe à `pngSize` — un fichier PNG, aux dimensions non
  nulles ; un export en échec le fait échouer. La disposition des niveaux reste prouvée par les
  tests du back, inchangés.
- `WF-DEV-0070-A` — « Le filtre par nœud d’organisation ne laisse voir que les rôles qui en relèvent. » : contre
  le service, après le choix du nœud, le parcours ouvre « Valeurs du graphique » et affirme qu'un
  rôle hors du nœud a disparu et qu'un rôle du nœud reste ; l'adresse et la valeur de la liste ne
  suffisent plus.
- `WF-DEV-0070-A` — « La capacité de chaque rôle est affichée. » : le même parcours lit la capacité
  du rôle resté dans la table des valeurs, et non le seul en-tête de colonne.
- `WF-CRE-0050-A` — « Après un import, le journal présente une entrée datée du jour avec ses comptes de lignes, et la consultation des coûts réels affiche cette date comme celle du dernier import. » : contre
  le service, après l'import, le parcours affirme dans la table « Journal des imports » une ligne
  datée du jour qui porte ses comptes — quatre lignes créées —, en plus de la date du dernier
  import, qu'il affirme déjà.
- `WF-CRE-0030-A` — « Après un second import couvrant la même période, elle est toujours exclue. » : contre
  le service, après l'exclusion de la ligne, le parcours réimporte les quatre lignes de la même
  période, puis affirme que la ligne est toujours « Exclue » et que les totaux n'ont pas changé.
- propre à l'US : contre le faux back, les attendus des trois parcours ne changent pas — Prism
  ignore les paramètres, et le filtre n'y est affirmé que par l'adresse.
- écart : `WF-PLA-0110-A` — « Aucun jalon ni aucune tâche feuille n’apparaît, quel que soit le niveau demandé. » : constaté par EP-06, inchangé.
- écart : `WF-PLA-0110-A` — « Un planning composé uniquement de tâches feuilles produit une arborescence réduite au nœud du projet. » : constaté par EP-06, inchangé.
- écart : `WF-PLA-0120-A` — « Le contenu ne dépend que du niveau demandé. » : constaté par EP-06, inchangé.
- écart : `WF-PLA-0120-A` — « L’export d’une arborescence trop large pour une page produit une image plus large que la page, sans réduction. » : constaté par EP-06, inchangé.
- écart : `WF-PLA-0120-A` — « L’export d’une arborescence dont l’image dépasserait cent millions de pixels échoue, et l’échec le dit. » : constaté par EP-06, inchangé.
- écart : `WF-DEV-0070-A` — « La charge d’une ligne portée par une tâche qui couvre exactement deux mois civils apparaît sur ces deux mois, au prorata des heures travaillées de la tâche dans chacun. » : constaté par EP-07 et EP-09, inchangé.
- écart : `WF-DEV-0070-A` — « Le plan de charge calculé sur le reste à engager ignore les lignes des tâches terminées. » : constaté par EP-09, inchangé.
- écart : `WF-DEV-0070-A` — « Les trois bases sont proposées ; sur un projet sans révision de référence, la base de la référence est absente, et sur un projet sans aucune révision marquée, seule la révision en cours est proposée. » : constaté par EP-15 et EP-09, inchangé.
- écart : `WF-DEV-0070-A` — « Une tâche démarrée qui couvre exactement quatre mois civils, à mi-parcours à la date de calcul — le premier jour du troisième mois —, dont une ligne porte un reste de 80 heures, présente ces 80 heures sur les deux mois restants au prorata de leurs heures travaillées — 40 et 40 s’ils en comptent autant — et rien sur les mois écoulés ; sur une révision marquée, la date de calcul est sa date de marquage. » : constaté par EP-09, inchangé.
- écart : `WF-DEV-0070-A` — « Une tâche non démarrée dont la date de début est antérieure à la date de calcul ne présente aucune charge sur les mois écoulés ; sa charge est la même avant et après son démarrage. » : constaté par EP-09, inchangé.
- écart : `WF-CRE-0030-A` — « Une ligne exclue n’apparaît dans aucun total d’indicateur, et reste visible dans la consultation des coûts réels. » : constaté par EP-09, que le parcours d'aujourd'hui tient déjà ; inchangé.

**Notes de réalisation.** FTE-03, FTE-04 et FTE-05 font foi pour les lieux
(`e2e/task-tree.spec.ts`, `e2e/workload.spec.ts`, `e2e/actual-costs.spec.ts`). Le parcours des
coûts réels cite aussi WF-CRE-0040-A et WF-CRE-0020-A, qu'il prouve déjà : rien n'y change. La
règle du jeu de données de référence vaut : un parcours se rejoue contre le service sans réécriture
de ses attendus de lecture, et c'est elle que le parcours de l'arborescence retrouve.

**Hors périmètre.** Un parcours de `e2e/service/` qui filtre le plan de charge. Le parcours
« importe des coûts réels » d'US-2990 (EP-13), sur la plateforme de la version.

---

## US-3380 — Des parcours qui remettent ce qu'ils écrivent, échouent tôt et ne passent pas à vide

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`
- **opérations** : `getReferenceSettings`, `updateReferenceSettings`, `getPortfolioRisks`
- **issue** :

**En tant que** développeur, **je veux** qu'un parcours laisse l'installation comme il l'a trouvée,
qu'il échoue dès que son attente est perdue et qu'il n'affirme jamais rien sur un écran où il n'a
rien trouvé, **afin qu'** un second passage sur la même plateforme lise le témoin, et qu'un vert
dise qu'une chose a été éprouvée (#4445, #3909 ; FTE-08 et FTE-09 de #4448).

**Critères d'acceptation.**

- propre à l'US (#4445, reste de FTE-02) : le parcours des paramètres communs remet, dans un
  `finally`, la matrice des risques et les seuils des indices qu'il a lus avant d'écrire, même
  après un échec ; son assertion « relu après rechargement » reste. Deux passages de suite de
  `make e2e-service` sur une même plateforme laissent les paramètres du témoin.
- `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé associé ni aucune image porteuse d'information sans description. » : sa
  forme pour ce qu'un geste ouvre (FTE-08, c) : un test « ce qu'un geste ouvre » compare le nombre
  de déclencheurs qu'il a joués à celui que son écran doit offrir, épinglé par écran, et échoue
  quand il en trouve moins — zéro compris ; un écran qui n'en a aucun le déclare.
- propre à l'US (#3909) : `reachByKeyboard`, dans `e2e/revisions.spec.ts`, compare la position du
  focus — rangée et colonne — à celle de la cible, et échoue dès qu'elle est dépassée ou que le
  focus sort d'une cellule, au lieu d'attendre la borne de `toPass`.
- propre à l'US (FTE-09, le portefeuille) : le parcours de la matrice des risques du portefeuille
  ne lit plus `path[fill-opacity='0.85']`, un détail du rendu d'ECharts : il compte les risques par
  ce que l'écran nomme, la table « Valeurs du graphique », dont la somme des cases est le nombre de
  risques identifiés que le service rend.
- écart : `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » : constaté par EP-14, inchangé ; le parcours au Tab rejoué en anglais est écarté (FTE-08, b).
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » : constaté par EP-14, et par EP-25 (US-2190) pour le thème de connexion ; inchangé.
- écart : `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » : constaté par EP-14, en français ; l'audit rejoué en anglais est écarté (FTE-08, b).

**Notes de réalisation.** La première occurrence de FTE-02, les heures par jour laissées à 7, est
corrigée par EP-28 (#3967), dont le `finally` de `reference-resources.spec.ts` est le modèle. Le
nombre de bulles dessinées n'est plus affirmé pour lui-même : la conception dit ce que le parcours
garde du dessin.

**Hors périmètre.** L'audit et le parcours au Tab en anglais, la page de fixation du mot de passe
et le parcours au Tab du thème de connexion (FTE-08, a et b) : écartés par l'auteur le 2026-11-21.
Les bulles de l'écran des risques d'un projet : EP-30 (US-3160). La flèche des liaisons du Gantt :
US-3390.

---

## US-3390 — Le Gantt nomme la flèche de chaque liaison, et le parcours la trouve par son nom

- **statut** : à faire
- **exigences** : `WF-PLA-0090-A`
- **opérations** : `listNodes`
- **issue** :

**En tant que** développeur, **je veux** que le parcours qui prouve « les liaisons sont visibles »
trouve les flèches du Gantt par un nom que l'écran leur donne, **afin qu'** un changement de la
charte ne casse pas une preuve de WF-PLA-0090 sans défaut derrière, et qu'une liaison se lise aussi
sans la voir (FTE-09, de #4448).

**Critères d'acceptation.**

- `WF-PLA-0090-A` — « Les liaisons et la hiérarchie sont visibles, ainsi que le chemin critique. » : la
  flèche d'une liaison porte dans le Gantt un rôle d'image et un nom qui dit ses deux tâches, comme
  la liaison en conflit en porte déjà un ; le parcours joué contre le service trouve les liaisons
  par ce nom, et non par `g.stroke-muted-foreground polygon` ; un test de composant tient le nom.
- propre à l'US : aucun parcours ne trouve plus un élément du Gantt par une classe de la charte.
- écart : `WF-PLA-0090-A` — « Aucune action de la souris ou du clavier ne modifie une tâche depuis le Gantt. » : constaté par EP-06 (US-1470) et EP-15 (US-0530), inchangé.
- écart : `WF-PLA-0090-A` — « Une récapitulative pliée dans la grille l’est dans le Gantt, et réciproquement. » : constaté par EP-06 (US-1470) et EP-15 (US-0530), inchangé.

**Notes de réalisation.** Après la fusion d'EP-32 dans `main` : US-3350 y réécrit le placement des
liaisons, et le nom s'ajoute au tracé qu'elle livre. Le nom est un texte du catalogue, dans les
deux langues.

**Hors périmètre.** Le chemin critique prouvé par un test du service : EP-32 (US-3290). Déplacer
`planning-service.spec.ts` sous `e2e/service/` : écarté par l'auteur le 2026-11-21.

---

## US-3400 — Le test des relectures du Kanban ne dépend plus de la charge du poste, et éprouve le refus que son titre promet

- **statut** : à faire
- **exigences** : aucune — tests du front
- **opérations** : aucune en propre
- **issue** :

**En tant que** développeur, **je veux** que `kanban.dom.test.tsx` passe quelle que soit la charge
du poste et que ses titres disent ce que ses tests éprouvent, **afin de** ne plus relancer la
chaîne d'un lot qui ne touche pas le Kanban (#4000, trois occurrences du 2026-11-19 au
2026-11-21 ; #3595).

**Critères d'acceptation.**

- propre à l'US (#4000) : le test « mounts the reading anew of a write lost once sent once for the
  board… » n'écrit plus « A component suspended inside an `act` scope, but the `act` call was not
  awaited » : la cause est établie, dite dans l'issue, et la suspension est attendue. Le fichier
  passe cinquante fois de suite sur un poste chargé par une exécution lourde, sans relance.
- propre à l'US (#3595, 1) : le test « keeps the card of a write lost waiting… when another write
  is lost or refused meanwhile » joue aussi l'étape où la seconde carte est refusée (`conflict` ou
  `stale`), et vérifie que la première reste `draggable="false"` jusqu'au relâchement.
- propre à l'US (#3595, 2) : le titre du premier test du montage de la relecture perd sa virgule
  orpheline, et l'assertion `expect(readAnew.mounts).toBe(0)`, vraie avec l'ancien code comme avec
  le nouveau, n'est plus présentée comme une preuve.

**Notes de réalisation.** Même forme que #859 (`cost-commands.dom.test.tsx`, EP-24), dont la
correction est le modèle. Les deux constats touchent le même fichier : un seul lot.

---

## US-3410 — L'en-tête du reste à engager est prouvé par ses largeurs, et deux parcours instables ont leur cause

- **statut** : à faire
- **exigences** : aucune — parcours du front
- **opérations** : aucune en propre
- **issue** :

**En tant que** développeur, **je veux** que le test d'en-tête du reste à engager exige ce que son
titre annonce, et que deux parcours vus en échec sans lien avec leur lot aient une cause connue,
**afin qu'** un échec de ces parcours dise un défaut (#3997, #4140, #4141).

**Critères d'acceptation.**

- propre à l'US (#3997) : le test des commandes de l'en-tête, à 360, 900, 1000, 1100 et 1280 px,
  compare la largeur de chaque bouton à sa largeur naturelle, mesurée sans contrainte ; quand les
  commandes passent sous le titre, il vérifie leur nombre de rangées, et que le bloc du titre garde
  au moins 384 px.
- propre à l'US (#4141) : `seedPlanning`, dans `e2e/remaining.spec.ts`, n'attend plus une requête
  sur une page qui peut être fermée : la cause de la course est établie et dite dans l'issue, et
  l'attente est résolue avant la fermeture.
- propre à l'US (#4140) : l'échec d'`e2e/admin.spec.ts` — « Service des achats » attendu, « Aucun »
  reçu, vu en local le 2026-11-19 et dans la file d'EP-13 le 2026-11-20 — a sa cause établie et
  corrigée dans le parcours : un état laissé par un parcours précédent, ou une lecture faite avant
  la fin d'une écriture.
- propre à l'US : pour chacun des deux parcours, l'historique de la file est relu (`make
  queue-report`). Une cause que ni cette relecture ni des passages répétés n'établissent laisse une
  entrée dans `tools/queue-known.toml`, sa cause ouverte par « hypothèse : », et l'issue ouverte ;
  la pull request le dit.

**Notes de réalisation.** `remaining.spec.ts` porte #3997 et #4141 : un seul lot.

**Hors périmètre.** La marge de 3,5 points sous la grille à 1280 × 720 (#3997) : sans suite, par
décision de l'auteur du 2026-11-21 — aucun écran ne la demande aujourd'hui.

---

## US-3420 — Cinq tests de composants éprouvent ce que leur titre promet

- **statut** : à faire
- **exigences** : `WF-IHM-0170-A`
- **opérations** : `createAccessRole`
- **issue** :

**En tant que** développeur, **je veux** que cinq tests du front, relevés par les revues de leurs
lots, éprouvent les branches et les états que leur titre annonce, **afin qu'** une régression de
l'attente d'une relecture, du repli, de la relecture comparée ou du signal de fin de mesure fasse
échouer un test (#3461, #3521, #3788, #3907, #3908).

**Critères d'acceptation.**

- propre à l'US (#3461) : un test monte la création d'un rôle sous une relecture retenue, perd la
  connexion à l'envoi, et vérifie que le bouton d'envoi est `aria-disabled` et `aria-busy`, qu'un
  second clic n'envoie rien, puis que la relecture libérée rend la main — sur le modèle des tests
  d'abandon de `revision-commands.dom.test.tsx`. Le dialogue porte `aria-busy` pendant la relecture
  aussi, et le bouton emploie `waitingAttributes` et `WaitingIcon`, comme les autres commandes en
  attente.
- propre à l'US (#3521) : le test « an export found again that succeeds does not download »
  n'affirme plus un nombre arbitraire de lectures : il affirme qu'aucune lecture du résultat n'est
  faite ; le second `serve()` est retiré ou expliqué.
- `WF-IHM-0170-A` — « Les branches sans écart repliées, la grille n’affiche que les lignes marquées et leurs récapitulatives, signale chaque suite de lignes repliées, la déplie à la demande, au clavier comme au pointeur, et porte les mêmes totaux qu’avant le repli. » : la
  part que le test du collage sous repli en doit (#3788) : les sommaires affichés sont affirmés
  contre les ancêtres attendus des lignes collées, lus dans la structure de l'exemple, et non relus
  de la sortie qu'ils servent à vérifier ; une ligne non marquée restée visible avant le collage
  fait échouer le test. Le reste de la phrase est constaté par EP-27, inchangé.
- propre à l'US (#3908) : le `it.each` de la relecture comparée joue aussi l'écriture en cours
  échouée — le rejet de l'écriture — et l'écriture sans changement, que `cell-writes.ts` traite
  comme les deux autres.
- propre à l'US (#3907) : `e2e/measure/armed.test.ts` éprouve le signal donné sans cellule marquée
  attendue, et l'adresse attendue ; le commentaire d'en-tête de `grids.measure.ts` retrouve son
  remplissage.

**Notes de réalisation.** Les trois lignes de `role-creation.tsx` sont le seul code de production
de l'US (décision de l'auteur du 2026-11-21). `folded-runs.dom.test.tsx` est aussi le fichier de
tests d'un composant qu'EP-32 (US-3350) touche pour le tracé d'un lien : des tests distincts.

---

## US-3430 — Les tests de pages lisent le texte rendu par les aides du harnais, et le projet `node` refuse la sortie d'erreur

- **statut** : à faire
- **exigences** : aucune — harnais des tests du front
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** qu'un test `node` qui écrit sur la sortie d'erreur échoue
comme un test `dom`, et que les tests de pages lisent le texte rendu par les aides du harnais,
**afin qu'** un avertissement de React sur une page serveur — une clé manquante, une imbrication
invalide — ne passe plus sans être lu (#3937 ; FTE-06 de #4449).

**Critères d'acceptation.**

- propre à l'US (#3937) : aucun test du front ne retire plus les balises ou les commentaires d'un
  rendu par une expression régulière : les fichiers qui le font — vingt-sept dans `main` au
  cadrage — passent par `plain` et `textOfMarkup` de `src/test/page-stream.tsx`, sans qu'une
  assertion soit affaiblie.
- propre à l'US (FTE-06) : le projet Vitest `node` charge une mise en place qui pose `watchStderr`
  et `refuseStderr` : un test `node` qui écrit sur la sortie d'erreur échoue ; un test de la garde
  le tient, sur le modèle de `setup-dom.dom.test.tsx`.
- propre à l'US : chaque test `node` que la garde fait échouer est corrigé, ou attend l'écriture
  par un espion qui l'affirme ; aucun n'est exempté. Le lot compte d'abord ces tests, et dit leur
  nombre dans son issue.
- propre à l'US : `make test-front` et `make coverage-front` passent, la garde posée ; le guide dit
  que la garde vaut pour les deux projets.

**Notes de réalisation.** Les deux gestes touchent les mêmes fichiers, les tests de pages rendues
par `renderToStaticMarkup` : le premier précède le second. Le coût de la garde n'est pas mesuré —
personne ne sait combien de tests `node` écrivent aujourd'hui ; l'auteur a retenu de la poser et de
tout corriger (2026-11-21).

**Hors périmètre.** Le projet `lint` de Vitest, qui ne rend rien.

---

## US-3440 — Les catalogues et les parcours tenus par deux gardes, et trois commentaires remis au jour

- **statut** : à faire
- **exigences** : aucune — gardes des sources du front
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que la typographie des catalogues et la règle « ni `skip`
ni `fixme` » soient tenues par un test, **afin qu'** une apostrophe droite ou un parcours sauté
sans raison n'attendent pas une revue pour être vus (FTE-07 et FTE-12, de #4449 ; #4450).

**Critères d'acceptation.**

- propre à l'US (FTE-07) : `admin.audit.find` et `admin.audit.findButton`, que plus rien ne lit,
  quittent les deux catalogues ; `grid.structure.taskHint` et
  `enums.CommandCondition.task_not_milestone` portent l'apostrophe typographique ; les deux textes
  anglais relevés portent des guillemets anglais.
- propre à l'US : un test `node`, à côté de `text-guard.test.ts`, échoue sur une apostrophe droite
  dans un texte du catalogue français, et sur des guillemets français dans un texte du catalogue
  anglais.
- propre à l'US (FTE-12) : un test `node` lit `e2e/**` et n'admet de `test.skip` que sur
  `inService` ou `!inService`, ou sur une constante d'une liste nommée qui donne son issue ; il
  refuse un `test.skip` sans condition, un `fixme` et un `.only`. Les sauts d'aujourd'hui —
  soixante-seize dans `main` au cadrage, tous sur `inService` ou `!inService` — passent, et la
  liste est vide.
- propre à l'US (#4450) : `e2e/opening.spec.ts` et le guide ne disent plus que la mesure « se
  tient, bloquante, en EP-13 » — EP-26 a clos WF-QUA-0060-A, et rien n'échoue sur un objectif ; le
  commentaire de `src/test/axe.ts` dit qu'`e2e/accessibility.spec.ts` audite chaque écran.

**Notes de réalisation.** L'apostrophe droite est aussi l'échappement des messages ICU : la garde
ne juge que le texte qu'un utilisateur lit. Le relevé de `make requirements` range déjà un test
sauté « non exécuté » (US-2440) : la garde des sauts vaut pour tout parcours, cité ou non.

**Hors périmètre.** Une garde des clés inemployées : écartée par l'auteur le 2026-11-21.

---

## US-3450 — `make requirements` refuse une citation qu'il ne lit pas, et les citations fautives sont corrigées

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** qu'une citation d'exigence que le relevé ne sait pas lire
le fasse échouer, **afin qu'** un test ne soit plus tenu pour une preuve par son auteur et ignoré
par l'outil, sans que personne le sache (#3789 ; FCO-13 et FAR-05, de #4451).

**Critères d'acceptation.**

- propre à l'US (#3789, décision de l'auteur du 2026-11-17) : `make requirements` échoue, en
  nommant le fichier et la ligne, sur une citation du back dont l'argument n'est pas écrit en
  toutes lettres ; les quatre fichiers qui citent WF-REV-0080-A par une constante
  (`test_comparison.py`, `test_comparison_current.py`, `test_uniting.py`,
  `test_witness_lines_reads.py`) passent au littéral, et le relevé compte leurs citations.
- propre à l'US (FCO-13) : `make requirements` échoue de même sur le titre d'un test TypeScript qui
  porte entre crochets un identifiant d'exigence sans son indice de révision ; les citations sans
  indice — vingt-sept, dans neuf fichiers du front et des parcours, dans `main` au cadrage — sont
  corrigées une à une : l'indice quand le test éprouve une phrase du Vérif, que la pull request met
  en regard, la citation retirée sinon.
- propre à l'US (FAR-05) : les six titres de `user-bulk.dom.test.tsx` qui citent WF-ADM-0120-A,
  WF-ADM-0180-A et WF-IHM-0110-A sans en éprouver le Vérif perdent leur citation, et gardent leur
  numéro d'issue.
- propre à l'US : `make requirements` passe, et aucune exigence F0 ne quitte le relevé par ces
  retraits : la pull request donne le compte des exigences couvertes avant et après. Le guide (« Un
  test qui cite son exigence ») dit les deux refus.

**Notes de réalisation.** Après la fusion d'EP-11, dont US-2770/L3 modifie `wftools.coverage`
(#4374). Le guide dit déjà la règle : « Un test cite l'exigence dont il éprouve le Vérif, pas celle
dont il parle ».

**Hors périmètre.** Faire lire au relevé l'étiquette `@shared` : écarté par l'auteur le
2026-11-21. La porte de publication : EP-13 (US-3000).

---

## US-3460 — Les tests du back : des marqueurs justes, des aides partagées, un fichier vide retiré

- **statut** : à faire
- **exigences** : aucune — tests du back
- **opérations** : aucune en propre
- **issue** :

**En tant que** développeur, **je veux** que les tests du back relevés par les revues citent ce
qu'ils éprouvent et partagent leurs aides par le module de support, **afin que** le relevé de
couverture ne soit ni gonflé ni troué, et que deux copies d'une fixture ne dérivent pas (#3916,
#3921 ; BAC-10 et BRC-10, de #4451).

**Critères d'acceptation.**

- propre à l'US (#3916, 1) : le test de `test_parting.py` qui compte les appels à `month_weights`
  ne cite plus WF-DEV-0090-A, dont il n'éprouve pas le Vérif ; l'exigence reste couverte.
- propre à l'US (#3916, 2) : le test de `test_indicators_statements.py` reconnaît la somme du coût
  réel par sa requête groupée, et ne dépend plus du nombre de dates de document du jeu.
- propre à l'US (#3921) : `kept`, `document`, `marked_now`, `ONE_DAY` et les fixtures partagées
  vivent dans `indicators_support.py` ; `test_indicators_stored`, `test_indicators_marked_read` et
  `test_indicators_kept_closure` les y lisent, et aucun module de test n'en importe un autre. Le
  test du 409 affirme d'abord que la lecture répondait, indicateurs conservés, avant la suppression
  des documents.
- propre à l'US (BAC-10) : `test_who_may_change_the_accounts_but_not_the_roles_does_not_give_himself_the_administration`
  et `test_an_operation_asked_without_its_permission_is_refused_naming_it` citent ce qu'ils
  éprouvent : l'exigence, si une phrase de son Vérif est celle du test, sinon l'US dont ils portent
  un critère propre — US-0390 pour le second, que son commentaire nomme déjà.
- propre à l'US (BRC-10) : `backend/tests/test_cost_imports.py`, qui n'a aucun test, est supprimé.
- propre à l'US : `make requirements` passe.

**Hors périmètre.** Le test du lien de mot de passe (`test_users_password_link.py`) et le test sans
assertion de WF-REF-0150-A, que #3342 et #3960 (EP-29) réécrivent. Les branches dupliquées de
`_spread_after` (#3916, 3) : sans suite.

---

## US-3470 — Les bornes des corps que le service redéclare sont tenues au contrat par un test

- **statut** : à faire
- **exigences** : aucune — test de conformité au contrat
- **opérations** : `createProject`, `updateProject`, `createSubproject`, `updateSubproject`,
  `updateReferenceSettings`, et les écritures des calendriers, des types de coût, des nœuds
  d'organisation, des rôles et des chronologies
- **issue** :

**En tant que** développeur, **je veux** qu'une borne changée au contrat sur un corps que le
service déclare par un modèle à lui fasse échouer un test, **afin que** le service ne continue pas
d'accepter en silence ce que le contrat refuse désormais (CTC-05, #4452).

**Critères d'acceptation.**

- propre à l'US : le test des bornes de `test_contract_declarations.py`, qui ne tient aujourd'hui
  que les paramètres, s'étend aux corps : pour chaque opération dont la route déclare un modèle
  local au lieu du modèle engendré — les projets, les sous-projets, les paramètres communs, et les
  corps que le contrat écrit en ligne —, chaque borne du modèle local, longueur, motif, minimum ou
  maximum, est celle du schéma du contrat.
- propre à l'US : le test trouve ces routes lui-même, sans liste à tenir : un corps redéclaré
  demain est tenu sans y être inscrit.
- propre à l'US : une borne changée dans le schéma du contrat, le modèle local laissé tel quel,
  fait échouer le test, qui nomme l'opération et le champ.

**Hors périmètre.** Remplacer les modèles locaux par les modèles engendrés : le doublement est
voulu, pour rendre les trois codes du contrat là où le modèle engendré n'en rend qu'un.

---

## US-3480 — L'API, le worker et le témoin n'importent un module du noyau que par son interface, et import-linter le tient

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que la règle « toujours depuis l'interface, jamais depuis
le fichier d'un objet » soit tenue par l'outil au-dessus du noyau comme elle l'est dedans, **afin
qu'** un module du noyau puisse changer ses fichiers sans casser une route (BRC-09, #4454).

**Critères d'acceptation.**

- propre à l'US : `make imports-back` échoue sur un import, depuis `waterfall.api`,
  `waterfall.worker` ou `waterfall.witness`, d'un fichier d'un module du noyau qui n'est pas son
  `interface` ; la règle est un contrat d'import-linter, à côté de celui qui tient déjà les modules
  du noyau entre eux.
- propre à l'US : les imports d'aujourd'hui passent par l'interface, qui réexporte ce qui manque :
  `CommandAvailability` (`core/cost_settings`), `Duration`, `DurationUnit` et `LagUnit`
  (`core/planning`), `Written` (`core/estimate`, qu'EP-08 importe dans `api/numbering.py`) ; la
  borne du code de sous-projet (`core/projects`) est réexportée par EP-33 (US-3270).
- propre à l'US : le guide dit que la règle vaut pour l'API, le worker et le témoin, et nomme la
  commande qui la tient.

**Notes de réalisation.** Après la fusion d'EP-32 et d'EP-33 dans `main` : EP-32 touche l'interface
de `core/planning`, EP-33 corrige l'import d'`api/subprojects.py` (BPR-09). `waterfall.restore`,
`waterfall.bootstrap` et les migrations n'importent aujourd'hui aucun fichier privé du noyau.

**Hors périmètre.** Les imports entre modules du noyau, déjà tenus.

---

## US-3490 — La roadmap : les renvois de portée et les titres sont contrôlés, et une phrase de Vérif renvoyée nomme son porteur

- **statut** : à faire
- **exigences** : aucune — outil du dépôt et fichiers de la roadmap
- **opérations** : aucune
- **issue** :

**En tant que** développeur, **je veux** que `make roadmap` confronte les deux bouts d'une portée
et le titre d'une exigence à la spécification, et que les renvois que la revue a trouvés sans
répondant soient corrigés, **afin que** la colonne « Portée » redevienne fiable pour qui cherche
quel EPIC doit quoi, et qu'aucune phrase de Vérif ne soit dite constatée par un EPIC qui ne la porte
pas (RMP-08 et RMP-13, de #4455 ; les renvois de #4444, #4446 et #4447).

**Critères d'acceptation.**

- propre à l'US (RMP-08) : `make roadmap` échoue sur une portée « début — close en EP-x » quand
  EP-x ne clôt pas l'exigence ; sur une portée « fin — amorcée en … » dont la liste n'est pas celle
  des EPIC qui portent un « début » pour elle ; sur une portée « entière » qu'un autre EPIC amorce.
  Les lignes que la revue relève sont corrigées, sans changer qui clôt : WF-IHM-0110-A dans EP-02
  et EP-18, WF-DAT-0090-A et WF-DAT-0100-A dans EP-07, WF-REF-0150-A dans EP-05, les « fin »
  incomplètes d'EP-04 et d'EP-06, WF-CMP-0010-A dans EP-02, WF-QUA-0060 dans EP-01.
- propre à l'US (RMP-13) : `make roadmap` échoue sur un titre d'exigence d'un tableau qui n'est pas
  celui de la spécification ; les six titres périmés d'EP-02, EP-04, EP-05, EP-06 et EP-07 sont
  corrigés.
- propre à l'US (RMP-13) : le README de la roadmap ne dit plus « les 212 exigences » : il donne le
  nombre de la spécification, que `make roadmap` tient ; EP-21 y est listé après EP-05, dont il
  dépend ; la ligne de WF-PLA-0150-A d'EP-06 nomme l'US qui la cite ; EP-04 ne garde plus
  l'alternative qu'il a tranchée. `README.md` suit, et `make readmes` passe.
- propre à l'US (#4444) : les deux renvois « constaté par EP-06 » — WF-DAT-0100-A dans EP-07,
  WF-DAT-0070-A dans EP-09 — nomment US-3360, qui porte les tests.
- propre à l'US (#4446) : la phrase « Le marquage d'une révision de dix mille objets laisse l'écran
  utilisable et présente son avancement » n'est plus renvoyée d'EP-09 à EP-04 et d'EP-04 à EP-09 :
  EP-09, qui clôt, la porte en écart, lequel dit que le fond est éprouvé par US-2830 d'EP-13 sous
  WF-ARC-0090-A, et que le parcours au volume qui citera WF-IHM-0080-A est reporté à EP-40 (#4446).
- propre à l'US (#4447) : le critère d'EP-04 sur la première phrase du Vérif de WF-ADM-0160-A dit
  en écart ce qu'EP-13 en tient — la planification des sauvegardes (US-2910), l'inscription d'une
  écriture admise avant la maintenance (US-2940), la périodicité de la lecture des comptes
  (US-3040) —, et que la citation de l'exigence par ces tests est reportée à EP-39 (#4447) ; qui
  clôt ne change pas.
- propre à l'US : `make roadmap` passe sur la roadmap corrigée, et ses tests tiennent chaque
  contrôle nouveau.

**Notes de réalisation.** RMP-08 et RMP-13 font foi pour les lignes. La colonne « Portée » s'écrit
aujourd'hui de plusieurs façons (« début — close en EP-09, amorcée aussi en EP-15 ») : la conception
dit la grammaire que le contrôle lit.

**Hors périmètre.** RMP-09, hors le test des risques d'US-3360. Les preuves de #4446 et de #4447 :
EP-40 et EP-39.

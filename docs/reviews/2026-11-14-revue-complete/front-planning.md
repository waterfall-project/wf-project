# Revue — écrans de projet et de planning du front

Périmètre : `frontend/src/components/{gantt,tasks,tree,chart,workload,projects,revisions}`,
`frontend/src/app/projects`, `frontend/src/app/tasks` (commit `29785cc`). Lecture seule ; rien n'a
été exécuté (ni lint, ni typage, ni test) : tout ce qui suit vient de la lecture du code, du
contrat, de la spécification et de la documentation embarquée de Next 16.4.

## Synthèse

Le code de ce périmètre est d'une tenue rare : les commandes sont lues du serveur
(`available_commands`), jamais déduites ; les dates de planning sont placées en UTC de bout en bout
(aucun décalage de fuseau ni d'heure d'été possible dans le Gantt) ; le chemin critique, les marges
et les conflits sont ceux du serveur ; les écritures « liste entière » (lotissement, contributeurs)
partent toujours d'une lecture entière avec son compteur ; les réponses tardives sont gardées par
ouverture, par projet, par structure. Aucun commentaire d'exemption, aucun `any`, les 851 tests des
66 fichiers de test du périmètre affirment tous quelque chose.

Ce qui inquiète tient en trois points. (1) Le suivi des tâches de fond s'arrête de lui-même dès
qu'une lecture trouve la tâche inchangée — c'est la cause, restée « à établir », du symptôme connu
#3103 : toute tâche qui dure plus de deux lectures (≈ 4 s) n'est plus jamais lue. (2) L'écran des
contributeurs ne permet d'inscrire que les comptes que le serveur propose d'après le devis : sur un
projet neuf, un chef de projet ne peut inscrire personne depuis l'interface. (3) Les écritures de
cellule des grilles ne relisent pas la page, et Next réemploie la page au retour arrière : le
planning revenu par « Précédent » montre les données d'avant la saisie (plausible, non exécuté).
Le reste est mineur : le Gantt place ses barres au jour même au niveau « heures », dessine tout
l'axe dans chaque ligne une fois zoomé, et ne défile pas dans le temps au clavier.

## Constats bloquants

### FPL-01 — Le suivi d'une tâche de fond s'arrête à la première lecture « inchangée »

- **Issue** : #3103, fermée le 2026-11-14 — corrigé sur `epic/EP-25` par US-2170/L2 (#3331) ; reste dans
  `main` jusqu'à la fusion d'EP-25.
- **Où** : `frontend/src/components/tasks/tracking.ts:290-292` (`answer` rend `state` tel quel quand
  `unchanged`), `frontend/src/components/tasks/task-tracker.tsx:136-139` (`hold` n'avertit personne
  si rien ne change), `frontend/src/components/tasks/task-entry.tsx:291-314` (`usePolling` : un
  `setTimeout` unique, réarmé seulement quand l'objet `entry` change, dépendances `[entry, dispatch]`).
- **Quoi** : la lecture suivante n'est planifiée que par le re-rendu que provoque un changement de
  l'entrée ; une lecture qui trouve la tâche au même état rend le même objet, rien n'est rendu, le
  minuteur n'est pas réarmé, et la tâche n'est plus jamais lue.
- **Scénario** : un chef de projet marque une révision (ou demande un export, applique un import,
  fusionne un avenant). Le service rend `queued`, `progress: 0`. Lecture 1 (+2 s) : `running`,
  `progress: 0` → l'entrée change, la lecture 2 est planifiée. Lecture 2 (+4 s) : `running`,
  `progress: 0` encore — le worker n'écrit `progress` qu'à la fin (`backend/src/waterfall/worker/runner.py:109`,
  0 puis 100) → `unchanged` → plus aucune lecture. (Si la tâche est encore `queued` à +2 s, l'arrêt
  vient dès la première lecture.) Le panneau reste sur « En cours » ; la fin n'est jamais annoncée ;
  « Télécharger » n'est jamais offert pour un export ; `Following`/`useWhenTaskSucceeds`
  (`merge-amendment-command.tsx:331`, `risk-lifecycle.tsx:148`, `report-commands.tsx:128`,
  `duration-rule.tsx:57`) ne relisent jamais l'écran. Revenir sur l'onglet n'y change rien (`found`
  n'ajoute que les tâches inconnues) ; un rechargement complet relance deux lectures au plus
  (`progressUnknown`), puis s'arrête de même. WF-IHM-0080-A (« est informé de son aboutissement »,
  « présente son avancement ») n'est donc pas tenu au-delà de ≈ 4 s.
- **Vérifié** : aucun autre chemin ne relit (seuls `usePolling`, la lecture avant téléchargement et
  `listRunningTasks` au retour de l'onglet appellent l'API) ; `clear`, `found`, `restore` et la
  réponse d'une autre tâche gardent l'identité de l'entrée. Aucun test ne sert deux lectures
  identiques de suite : `task-tracker.dom.test.tsx:258-276` sert `running` puis `succeeded` depuis
  `queued` (chaque lecture change la tâche), et `tracking.test.ts:45-62` fige au contraire
  l'optimisation au niveau du réducteur (défaut n° 8 de `typescript.md` : la logique pure testée,
  pas le composant).
- **Proposition** : dissocier la relance de l'identité de l'entrée — une boucle par tâche suivie
  (clé + `task_id`) qui réarme son minuteur à chaque réponse, quelle qu'elle soit, tant que
  `isPolled`, l'optimisation « rien n'est rendu » restant dans le magasin. Test : tâche remise
  `queued`, `serve({ [TASK]: ["task_running", "task_running", "task_succeeded"] })`, trois
  `tick()`, la fin annoncée et trois lectures comptées ; un second avec deux `queued` de suite.
- **Confiance** : confirmé (chemin lu de bout en bout, front et worker).
- **Déjà connu (#3103, EP-25 US-2170)** pour le symptôme — « une tâche lue deux fois, aboutie,
  plus jamais lue », dont l'US dit la cause à établir ; elle est ici établie. Classé bloquant par
  la définition du cahier (exigence close non tenue) ; à reclasser si le coordinateur tient le
  « déjà planifié » pour atténuant.

## Constats majeurs

### FPL-02 — Un chef de projet ne peut inscrire que les comptes que le serveur propose

- **Issue** : #4487 (EP-29), ouverte le 2026-11-21.
- **Où** : `frontend/src/components/projects/contributor-commands.tsx:332-595` (`ContributorEditor` :
  lignes du brouillon, changement de qualité, retrait, et la seule section « propositions »,
  lignes 362 et 526-570) ; `frontend/src/app/projects/[projectId]/settings/page.tsx:135-155`.
- **Quoi** : le dialogue n'offre aucun moyen d'ajouter un compte hors de
  `listContributorSuggestions` — les comptes des services dont le devis emploie un rôle —, et le
  contrat n'a aucune opération qui liste les comptes à un chef de projet (`listUsers` est de
  l'administration).
- **Scénario** : un chef de projet crée un projet ; aucune ligne de devis n'existe, la liste des
  propositions est vide (EP-04 : « vide tant qu'aucune ligne n'existe »). Il ouvre « Modifier la
  liste » : il peut se retirer ou changer sa qualité, rien d'autre. Il ne peut inscrire ni le
  planificateur ni le chiffreur, qui reçoivent `NOT_CONTRIBUTOR` à chaque écriture — et c'est
  justement leur saisie qui ferait naître des propositions. Même projet avancé, un second chef de
  projet d'un service qu'aucun rôle du devis n'emploie ne s'inscrit pas. WF-PRJ-0060-A, Vérif :
  « son créateur, chef de projet, qui peut y inscrire d'autres utilisateurs » ; WF-PRJ-0070-A :
  « la liste reste modifiable à la main ». Le critère est clos par EP-04 sur la seule API
  (« `setContributors` lui est ouvert »), et les parcours inscrivent leurs comptes « par l'API »
  (EP-04, Conception).
- **Vérifié** : la Conception d'EP-14 décrit bien ce dialogue (« l'inscription des comptes que le
  serveur propose ») : c'est la décision elle-même qui contredit le Vérif ; aucune issue ni US
  d'EP-25 à EP-28 ne le reprend (`grep` « inscri » sur `docs/roadmap/`).
- **Proposition** : une recherche de comptes actifs dans le dialogue. Elle demande une opération au
  contrat (recherche bornée, ouverte à qui porte `manage_contributors`, rendant identifiant, nom,
  `is_active`) — donc une issue « contrat » d'abord. Test : projet sans ligne de devis, le dialogue
  inscrit un compte cherché par son nom, `setContributors` reçoit les deux lignes.
- **Confiance** : confirmé (dialogue lu en entier ; contrat et critères d'EP-04 lus).

### FPL-03 — Revenue par « Précédent », une grille montre les données d'avant la saisie

- **Issue** : #4436 (EP-34), ouverte le 2026-11-21.
- **Où** : `frontend/src/api/actions/nodes.ts:100-320` (`updateTaskFacet`, `updateEstimateLine`,
  `setLineRemaining`, `setPredecessors`, `createNode`, `deleteNode`, `moveNodes` ne relisent pas la
  page ; seul `updateStructure`, ligne 370, appelle `refresh()`) ;
  `frontend/src/app/projects/[projectId]/revisions/[revisionId]/planning/page.tsx:257-291`,
  `estimate/page.tsx`, `remaining/page.tsx` (les lignes et `structureVersion` descendent en props
  de la page) ; `frontend/src/components/grid/structure-version.ts:46-48` (les versions atteintes
  vivent dans un état React).
- **Quoi** : les réponses des écritures de cellule ne vivent que dans l'état des composants ; la
  page gardée par le routeur reste celle de la première lecture, et Next la réemploie au retour
  arrière (« Pages are not cached by default but are reused during browser back/forward
  navigation », `node_modules/next/dist/docs/01-app/04-glossary.md:49` ; `staleTimes.md` : « This
  doesn't change back/forward caching behavior »).
- **Scénario** : un planificateur saisit dix durées dans le planning, clique « Devis » dans la
  barre latérale, puis « Précédent » du navigateur. La grille est remontée avec les lignes et le
  compteur de la lecture initiale : ses dix saisies semblent perdues (elles sont au serveur), le
  Gantt montre les anciennes dates, et sa prochaine saisie sur une de ces lignes part d'un
  `lock_version` périmé (412), jusqu'à un rechargement.
- **Vérifié** : aucun `router.refresh()` au montage d'une grille ni sur `popstate` (seul
  `commands/held.ts:79` écoute `popstate`, pour autre chose) ; les grilles ne relisent qu'après un
  collage qui crée, un déplacement refusé ou un squelette. Les écritures des paramètres, des
  révisions, du Kanban et des préférences relisent, elles, la page (`refresh()`), et ne sont pas
  touchées.
- **Proposition** : relire la page quand un écran de grille est remonté depuis l'historique
  (traversée détectée, ou version de structure gardée par onglet et comparée au montage), ou faire
  marquer la page périmée par les actions d'écriture sans la relire sur place. Preuve : un parcours
  e2e — saisir une cellule, suivre un lien, `page.goBack()`, la cellule montre la valeur saisie.
- **Confiance** : plausible — la pièce non vérifiée est le comportement réel de Next 16.4.5 à la
  traversée (lu dans sa documentation embarquée, non exécuté). Le défaut naît dans `components/grid`
  et `api/actions` (autres relecteurs) ; il est rendu ici parce qu'il se voit sur les pages
  d'`app/projects`.

## Constats mineurs

### FPL-04 — Le Gantt place les barres au jour, même au niveau « jours/heures travaillées »

- **Issue** : #4418 (EP-32), ouverte le 2026-11-21, avec FPL-05, FPL-06.
- **Où** : `frontend/src/components/gantt/layout.ts:66-78` (`startTime`, `finishTime` : minuit du
  jour, + 1 jour si `hours` ≠ 0), `layout.ts:124-131`, `gantt.tsx:663` (`rightward`),
  `scale.ts:36` (niveau heures).
- **Quoi** : `WorkInstant.hours` n'est lu que pour savoir s'il vaut zéro ; au niveau heures, l'axe
  gradue les heures 1 à 8 mais une tâche de deux heures couvre la journée entière, et deux tâches
  enchaînées le même jour sont deux barres identiques reliées par une flèche qui repart en arrière.
- **Scénario** : A de 4 h (`{D, 0}` → `{D, 4}`), B de 4 h liée fin-à-début (`{D, 4}` → `{D, 8}`,
  l'exemple même du contrat). A et B vont de D 00:00 à D+1 00:00 ; la liaison sort à D+1 et arrive
  à D : flèche vers la gauche, à tous les niveaux, sur 160 points au niveau heures.
- **Proposition** : au niveau heures (et pour l'ancrage des liaisons), placer l'instant à
  `jour + hours / heures du jour du calendrier de la tâche` (`calendar_hours` est déjà lu) ; à
  défaut, ne pas offrir le niveau heures. Test de `layout.test.ts` sur l'exemple du contrat : la
  liaison arrive à droite de son départ. Le guide dit la règle « au jour » (« Rien n'y est
  planifié… ») : décision antérieure au niveau heures d'US-0530, à revoir avec lui.
- **Confiance** : confirmé (calcul déroulé à la main sur l'exemple du contrat).

### FPL-05 — Zoomé, chaque ligne du Gantt dessine toutes les graduations de l'axe entier

- **Issue** : #4418 (EP-32), ouverte le 2026-11-21, avec FPL-04, FPL-06.
- **Où** : `frontend/src/components/gantt/gantt.tsx:556-573` et `786` (`Months` : une `<line>` par
  graduation basse de tout l'axe, dans chaque cellule), `595-622` et `783` (`DaysOff` : toutes les
  bandes de l'axe), `382-405` (`view` recréé à chaque rendu : chaque cellule abonnée au contexte se
  rend à nouveau), `844-846` (`setOffset` à chaque événement de défilement),
  `timeline-chart.tsx:560-569`.
- **Quoi** : les lignes sont fenêtrées (la grille), l'axe du temps ne l'est pas. Au niveau
  semaines/jours un projet de trois ans donne ≈ 1 100 `<line>` par ligne visible ; au niveau heures
  ≈ 8 800 — soit plusieurs centaines de milliers de nœuds SVG pour une trentaine de lignes —,
  tous reconciliés à chaque événement de défilement horizontal et à chaque rendu de la grille
  (déplacement de la cellule active).
- **Scénario** : sur le témoin de mille tâches, zoomer deux fois puis faire défiler le temps à la
  molette ou déplacer la cellule active.
- **Proposition** : ne dessiner que les graduations et les bandes de la fenêtre
  `[offset, offset + frame]` (la vue les connaît), ou les peindre en un motif de fond ; mémoïser
  `view`. Preuve : la mesure du déplacement de la cellule active (#620) rejouée au niveau le plus
  fin.
- **Confiance** : plausible — le nombre d'éléments est lu dans le code, la lenteur n'est pas mesurée.

### FPL-06 — Zoomé, le Gantt du planning ne défile pas dans le temps au clavier

- **Issue** : #4418 (EP-32), ouverte le 2026-11-21, avec FPL-04, FPL-05.
- **Où** : `frontend/src/components/gantt/gantt.tsx:838-847` (le cadre qui défile : ni `tabIndex`,
  ni rôle, ni nom), `343-365` (molette seule), `320-327` (`reveal`, appelé par la seule frise,
  `timeline-chart.tsx:361`).
- **Quoi** : Ctrl et +/− zooment, mais aucune touche ne fait défiler l'axe, et la barre de la ligne
  active n'est pas ramenée dans le cadre ; `typescript.md` (« Accessibilité ») rappelle que Safari
  ne rend pas focalisable un conteneur qui défile.
- **Scénario** : au clavier, Ctrl + + deux fois sur un planning de deux ans : la date du centre est
  gardée, le reste de l'axe est hors d'atteinte sans souris, sauf à dézoomer (WF-IHM-0100-A).
- **Proposition** : ramener la barre de la ligne active (`reveal`) quand la cellule active change,
  ou une touche de la grille qui fait défiler le temps ; test `gantt.dom.test.tsx` : zoomé, la
  flèche bas amène la barre d'une tâche tardive dans le cadre.
- **Confiance** : confirmé pour l'absence de geste clavier ; l'atteinte par Tab du cadre dans
  Chromium et Firefox (conteneurs défilants focalisables) n'a pas été éprouvée.

### FPL-07 — Une révision abandonnée rend « introuvables » les écrans du projet qui la portent encore

- **Issue** : #4458 (EP-37), ouverte le 2026-11-21, avec FPL-08.
- **Où** : `frontend/src/components/context/reading.ts:195-197` (404 de la révision → `not_found`),
  `frontend/src/navigation/context.ts:155-161` (`revision_id` porté par les écrans de projet),
  `frontend/src/app/projects/[projectId]/screen.ts:68-74`.
- **Quoi** : « Révisions », « Paramètres », « Cycle de vie » et la page du projet répondent
  introuvable quand leur adresse porte `revision_id` d'une révision supprimée, alors que le projet
  existe et que l'écran n'a pas besoin d'elle.
- **Scénario** : A abandonne la révision en cours (son écran, lui, quitte l'adresse :
  `revision-commands.tsx:109-113`). B, qui travaillait dans cette révision (autre onglet, autre
  poste, favori, ou l'adresse gardée par le cookie `wf_last_project`), clique « Révisions » : page
  introuvable ; il doit repasser par l'accueil.
- **Proposition** : sur un écran de portée projet, une révision de `revision_id` introuvable se
  lève (redirection vers la même adresse sans le paramètre) au lieu de `notFound()` ; test de page :
  `getRevision` 404, `getProject` 200 → redirection.
- **Confiance** : confirmé pour le chemin de code ; le 404 de `getRevision` après abandon est celui
  que dit l'action (`api/actions/revisions.ts:77-80`).

### FPL-08 — Les listes du plan de charge et de la comparaison ne suivent pas l'adresse au retour arrière

- **Issue** : #4458 (EP-37), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec FPL-07.
- **Où** : `frontend/src/components/workload/workload-section.tsx:166`,
  `frontend/src/components/revisions/revision-comparison.tsx:121` (`<NativeSelect defaultValue=…>`
  dans un `next/form` qui n'est pas remonté).
- **Quoi** : React n'applique pas un `defaultValue` changé à un `<select>` déjà monté ; après
  « Précédent », la page lit l'ancienne base (ou l'ancienne paire de révisions) et la liste montre
  encore le dernier choix. Parent des défauts n° 20 et 21 de `typescript.md`.
- **Scénario** : plan de charge, choisir « Reste d'une révision marquée », « Afficher », puis
  « Précédent » : le graphique et la phrase « calculé sur… » redisent la révision en cours, la liste
  dit encore la révision marquée ; « Afficher » relance alors ce qu'on vient de quitter.
- **Proposition** : `ChoiceFilter` (déjà écrit pour ce cas) ou une liste contrôlée par l'adresse ;
  test : rendre la section sous l'adresse B puis sous l'adresse A, la liste montre A.
- **Confiance** : plausible (sémantique de React connue, non exécutée ici).

### FPL-09 — Divers, de faible portée

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — ce qui reste est une adresse
  écrite à la main (1), une règle que la revue dit de ne pas corriger au front (2), un coût non
  mesuré (4) et un point du back hors périmètre (5).
- **Comparaison, paramètres d'adresse** (`app/projects/[projectId]/revisions/page.tsx:134-147`,
  `revision-comparison.tsx:57-63`) : `from_revision_id`/`to_revision_id` partent tels quels ; un
  identifiant mal formé (422) ou la révision en cours (409) font tomber tout l'écran « Révisions »
  sur l'écran de panne, une révision d'un autre projet (404) le rend introuvable. Atteignable
  seulement par une adresse écrite à la main. Proposition : `isUuid` avant de demander, et
  `readOrRefused` (409, 422) dit dans la section. Confirmé à la lecture.
- **Règle locale plus stricte que le serveur** (`contributor-commands.tsx:415-424`) : le dialogue
  refuse, « comme l'API », une liste sans chef de projet *actif* ; le service n'exige un chef actif
  que d'un sauveteur (`backend/.../projects/interface/contributors.py:438-441`) et accepte d'un chef
  de projet une liste dont le seul chef restant est désactivé. Le front protège ici ce que le back
  laisse passer : à signaler au relecteur du back plutôt qu'à corriger au front. Confirmé.
- **Date proposée au Kanban** (`components/remaining/address.ts:150-154`, hors de mon périmètre
  strict) : le jour du poste, non celui de l'installation (WF-PLA-0130, spécification 1.0.3). Déjà connu (#2527, EP-25
  US-2200).
- **Kanban à mille cartes** (`components/remaining/kanban.tsx:303-357, 430-443`) : `actions` et
  `state` sont recréés à chaque rendu, toutes les cartes des trois colonnes se rendent à nouveau à
  chaque choix de carte ; la colonne « terminées » ne fait que croître. Plausible, non mesuré.
- **Hors périmètre, relevé en passant** : le worker n'écrit `progress` qu'à 0 puis 100
  (`backend/src/waterfall/worker/runner.py:109`) ; la barre du suivi ne peut donc « présenter
  l'avancement » (WF-IHM-0080-A) d'aucune tâche réelle.

## Points forts

- Gantt : tout en UTC (`layout.ts:66`, `scale.ts:95-123`, `days-off.ts:76`, `axis-labels.ts:55`),
  semaine ISO au lundi, bornes de mois par `Date.UTC` ; ni fuseau ni heure d'été ne décalent une
  barre. Lecture seule stricte (WF-PLA-0090) : aucun geste n'écrit une tâche ; critique, marge et
  conflits lus du serveur ; rien à la seule couleur ; plis partagés avec la grille.
- Commandes : partout `available_commands` / `missing_conditions` ; les états du contrat sont
  classés par des `Record` exhaustifs (`read-only.ts:27`, `tracking.ts:40-88`,
  `project-state-badge.tsx:42`), ce qui ferme le défaut n° 4.
- Écritures « liste entière » : lotissement et contributeurs partent d'une lecture entière et de son
  compteur, jamais d'une lecture filtrée (`breakdown-commands.tsx:222-227`, `settings/page.tsx:135-179`).
- Bascule de structure et de révision : grilles, Kanban, frise et commandes sont remontés par `key`
  (structure, chronologie, révision) ; les réponses tardives ne ferment que leur ouverture.
- Chargement : lectures parallèles, 404 uniforme, refus attendus dits à l'écran (plan de charge,
  indicateurs, lotissement), `cache()` sur projet, révision et sous-projets.
- Tests : exemples du contrat, exigences citées là où un Vérif est porté, aucune assertion vide
  (balayage automatique des 851 tests).

## Couverture

- **Lu en entier (production)** : `components/gantt/*` ; `components/tasks/*` ; `components/tree/*` ;
  `components/chart/*` ; `components/workload/*` ; `components/revisions/*` ; `components/projects/*`
  sauf `subproject-commands.tsx` ; `app/projects` : `screen.ts`, `grid-screen.ts`, page du projet,
  `lifecycle`, `settings`, `revisions`, page d'une révision, `planning`, `timelines`, `task-tree`,
  `kanban`, `workload`, `exchanges`, `estimate`, les `loading.tsx` ; `app/tasks/[taskId]/result/route.ts`.
- **Lu en partie** : `components/projects/subproject-commands.tsx` (en-tête, lignes, suppression :
  ≈ 250 lignes sur 605) ; pages `remaining`, `indicators`, `actual-costs`, `risks` d'`app/projects`
  (corps de la page seulement — écrans tenus par d'autres relecteurs).
- **Lu hors périmètre, pour suivre les chemins** : `components/remaining/{kanban.tsx,kanban-cards.ts,
  kanban-answers.ts,kanban-filter.ts,address.ts}` en entier, `kanban-card.tsx` pour moitié ;
  `components/commands/{object-commands,revision-commands}.tsx`, `mark-command.tsx` en partie ;
  `components/context/{reading,read-only}.ts` ; `navigation/context.ts` ; `api/actions/revisions.ts` ;
  parties d'`api/problem.ts`, `api/actions/nodes.ts`, `components/grid/structure-version.ts` ; côté
  back, `worker/runner.py` (fin d'une tâche) et `core/projects/interface/contributors.py`
  (`set_contributors`).
- **Tests** : titres et citations de douze fichiers (≈ un cinquième), corps lus de
  `task-tracker.dom.test.tsx` et `tracking.test.ts` autour du suivi ; balayage automatique des 66
  fichiers pour l'absence d'assertion. Le tiers demandé n'est pas atteint en lecture de corps.
- **Non lu** : `frontend/e2e/` ; les corps de la plupart des tests ; `components/grid` et le socle
  (autres relecteurs) au-delà des extraits cités.
- **Non vérifié par exécution** : FPL-03, FPL-05, FPL-08 (dits « plausibles »).

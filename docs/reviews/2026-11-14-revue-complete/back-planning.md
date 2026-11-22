# Revue — back, planification (EP-06) : `core/planning`, routes du planning

Commit relu : `29785cc` (`main`). Lecture seule. Le moteur étant pur, ses résultats ont été
**rejoués** par de petits scripts `python` (interpréteur du `.venv` du back, sans base ni réseau) ;
le script de reproduction des constats du moteur est en annexe, à lancer depuis la racine du dépôt.

## Synthèse

Le module est d'une tenue élevée : un seul cadre d'écriture (`writing`) pour tous les chemins,
verrou de la structure pris avant la lecture de l'arbre, version jugée sous le verrou, réponse
construite avant la validation, calcul en fractions exactes, lecture du « fin de journée / début du
lendemain » correcte, cycles et liaisons récapitulative–subordonnée refusés. Les exemples chiffrés
de six exigences WF-PLA rejoués contre le code **sortent tous** (tableau plus bas).

Ce qui inquiète est concentré dans **la passe arrière du moteur** et dans **l'état d'une feuille qui
devient récapitulative** :

- une liaison début-à-début (ou début-à-fin) **qui part d'une récapitulative** donne des marges
  négatives et un chemin critique faux sur un planning entièrement automatique (BPL-01) ;
- une feuille **démarrée ou terminée** qui reçoit une sous-tâche non démarrée (indentation) perd son
  état et sa date de démarrage, et devient supprimable (BPL-02) ;
- une durée écoulée de moins d'un jour (`eh`, `emin`) donne encore une marge négative sans conflit,
  ce qu'US-1820 (EP-23) déclarait réglé (BPL-03) ;
- la passe arrière est quadratique dès qu'une liaison relie deux récapitulatives : 3,3 s pour dix
  phases de cent tâches enchaînées, à chaque écriture d'une cellule, verrou tenu (BPL-04) ;
- le refus « tâche sans heure travaillée » du moteur n'est traduit nulle part : 500 à l'ouverture
  d'une révision après un changement de calendrier (BPL-05).

2 bloquants, 3 majeurs, 7 mineurs.

### Exemples du Vérif rejoués contre le moteur

| Exigence | Exemple | Résultat du code |
|---|---|---|
| WF-PLA-0010 | 16 h, lundi matin, calendrier 8 h → finit mardi ; calendrier 4 h → jeudi | mardi 8 h ; jeudi 4 h — **sort** |
| WF-PLA-0160 | décalage 2 ej après un vendredi fin de journée → lundi 1re heure ; 2 eh idem ; 2 j → mercredi | lundi 0 h ; lundi 0 h ; mercredi 0 h — **sort** |
| WF-PLA-0030 | 50 % d'un prédécesseur de 10 j = 5 j de travail | successeur 5 jours ouvrés après la fin — **sort** |
| WF-PLA-0100 | deux branches 5 j / 3 j : la longue critique, l'autre marge = écart ; allongée à 6 j elle devient critique | marges 0 / 2 ; puis 1 / 0 — **sort** |
| WF-PLA-0100 | prédécesseur automatique qui ne peut finir avant une manuelle : marge négative, critique, signalé ; variante début-à-début | marge −3 j, critique, 1 conflit ; −1 j, 1 conflit — **sort** |
| WF-PLA-0150 | fin à quinze ans et un jour du début refusée, tâche nommée | début 2026-11-16 : fin 2041-11-18 refusée (tâche nommée), 2041-11-15 acceptée — **sort** |
| WF-PLA-0050 | récapitulative dont la seule subordonnée est un jalon : durée nulle | durée 0, reste récapitulative — **sort** |
| WF-PLA-0040 | récapitulative démarrée de durée nulle privée de son jalon → feuille d'un jour | `emptied` : 1 j — **sort** (lecture) |

Campagne aléatoire (3 000 structures par famille, tout automatique, propriété « aucune marge
négative, une tâche au moins à marge nulle ») : **aucun écart** pour les quatre types de liaison,
décalages positifs et négatifs, calendriers mêlés, décalages écoulés et en pourcentage entre
feuilles, et liaisons FD vers/depuis une récapitulative. Écarts : DD/DF depuis une récapitulative
(BPL-01) et durées écoulées (BPL-03).

## Constats bloquants

### BPL-01 — Une liaison DD ou DF qui part d'une récapitulative fausse les marges et le chemin critique

- **Issue** : #3335.
- **Où** : `backend/src/waterfall/core/planning/scheduling/engine.py:275-288` (`backward`) et
  `:301-331` (`bound`, dernière ligne).
- **Quoi** : en passe avant, une liaison qui part du *début* d'une récapitulative compte depuis son
  début agrégé (le plus tôt de ses subordonnées, `anchor`, l.210-213) ; en passe arrière, la même
  liaison borne **le début de chaque feuille** de la récapitulative (« a link from a summary binding
  each of its subordinates »). Juste pour une liaison qui part de la fin (toutes les feuilles
  doivent finir avant), faux pour le début : seule la première feuille porte le début.
- **Scénario** (rejoué, annexe) : calendrier 8 h lun–ven, tout automatique, aucune tâche manuelle.
  Récapitulative S = {A 1 j ; B 1 j, A→B fin-début} ; T 5 j, prédécesseur S en début-à-début.
  Dates : A lundi, B mardi, T lundi→vendredi — correctes. Marges rendues : **A −1 j, B −1 j,
  S −1 j, toutes « critiques »**, T 0, aucun `link_conflicts`. Attendu : A 0 (elle porte le début
  de S), B 3 j. La grille et le Gantt affichent donc un chemin critique faux et des marges
  négatives que WF-PLA-0100 réserve au conflit avec une tâche manuelle ; `total_float_days` et
  `is_critical` sont conservés en base et figés au marquage. L'import MS Project admet ces
  liaisons (une récapitulative prédécesseur en DD est permise par MS Project).
- **Vérifié** : le test `test_a_link_to_or_from_a_summary_binds_each_of_its_subordinates`
  (`tests/examples/test_scheduling_examples.py:424`) n'éprouve qu'une liaison FD ; le test du
  corpus ne compare aucune marge (`grep total_float tests/test_msproject_corpus.py` : rien) ; le
  témoin ne porte aucune liaison sur une récapitulative (1 013 liaisons, toutes entre feuilles).
- **Proposition** : en passe arrière, pour une liaison portée par un ancêtre et qui compte depuis
  le début (`link_type not in FROM_FINISH`), ne borner que les feuilles dont le début au plus tôt
  est celui de la récapitulative (celles qui le portent) ; les autres ne reçoivent de cette liaison
  aucune borne. Test : l'exemple ci-dessus (A 0, B 3, S 0), plus un test de propriété « une
  structure sans tâche manuelle ne rend aucune marge négative » sur des structures tirées au sort
  avec liaisons de récapitulatives des quatre types.
- **Confiance** : confirmé (exécuté).

### BPL-02 — Une feuille démarrée ou terminée qui reçoit une sous-tâche perd son état, et devient supprimable

- **Issue** : #3336.
- **Où** : `core/planning/interface/nodes.py:368-380` (`_judge_parent` : aucun jugement de l'état
  du parent), `core/planning/views.py:162-179` et `:195-204` (`_derived`, `state_of` : l'état d'une
  récapitulative ne lit que ses subordonnées), `core/planning/shaping.py:60-74` (`emptied` écrit
  cet état dérivé sur la facette), `interface/nodes.py:827` (garde de `deleteNode`),
  `shaping.py:77-91` (`closed_above` ne traite que `completed`), `interface/nodes.py:954-999`
  (`_moved`, même absence).
- **Quoi** : `createNode` et `moveNodes` acceptent comme parent une feuille démarrée (ou terminée).
  Elle devient récapitulative ; son état lu devient celui de sa seule subordonnée, **non
  démarrée** ; `started_on` disparaît de toute lecture ; la garde de WF-PLA-0070 (« une tâche
  démarrée ou terminée ne peut pas être supprimée ») ne la retient plus ; et dès que la
  sous-tâche repart, `emptied` écrit `not_started` et `started_on = NULL` sur la facette : l'état
  constaté est perdu pour de bon.
- **Scénario** : P, feuille démarrée le 2026-03-01 (Kanban), porte des lignes réestimées. Dans la
  grille, un contributeur indente la tâche suivante C (non démarrée) sous P — geste ordinaire
  (`moveNodes`, `parent_id = P`) ; ou crée une sous-tâche (`createNode`). 1) P se lit
  `not_started`, quitte la colonne « démarrées » du Kanban, n'est plus `finish_overdue`. 2)
  `deleteNode(P)` aboutit : P, C et les lignes de P sont supprimées, alors que le Vérif de
  WF-PLA-0070 veut le refus et le renvoi vers la mise à zéro du reste. 3) Sinon, C désindentée,
  P redevient feuille **non démarrée**, date de démarrage effacée (WF-PLA-0040 : « conserve son
  état »). Pour une feuille terminée, `closed_above` la repasse d'abord à `started`, puis le même
  chemin s'applique.
- **Vérifié** : rejoué au niveau du noyau sur un `Tree` construit à la main (sans base) :
  `state_of(P)` passe de `started, 2026-03-01` à `not_started, None` dès que C est sous P, et
  `emptied` écrit `not_started / None` sur la facette. Aucun test n'éprouve ce cas
  (`grep "def test_.*started.*\(subtask\|under\)" tests/test_nodes*.py tests/test_progress.py`).
  La spécification ne dit rien de cette transition ; ni la Conception d'EP-06, ni celle d'EP-09,
  ni `DECISIONS.md` ne la tranchent. Non rejoué par HTTP.
- **Proposition** : trancher la règle (une « Specification finding »), puis l'écrire en un seul
  endroit : soit refuser une sous-tâche sous une feuille démarrée ou terminée (422/409, comme
  `MILESTONE_HAS_NO_SUBTASK`), dans `_judge_parent` et `_judge_move` ; soit faire entrer l'état
  propre de la feuille dans l'état dérivé (une récapitulative née d'une feuille démarrée reste
  démarrée, son `started_on` gardé comme borne basse). Tests : création et indentation sous une
  feuille démarrée, puis `deleteNode` refusé (`task_not_started`), puis désindentation qui rend une
  feuille démarrée à sa date.
- **Confiance** : confirmé (chemin lu de la route au noyau, fonctions d'état exécutées).

## Constats majeurs

### BPL-03 — Une durée écoulée de moins d'un jour donne encore une marge négative sans conflit

- **Issue** : #4412 (EP-32), ouverte le 2026-11-21, avec BPL-08.
- **Où** : `core/planning/scheduling/engine.py:150-171` (`latest_start`, repli des l.168-171).
- **Quoi** : quand le départ au plus tard d'une durée écoulée tombe hors des heures travaillées, le
  repli le ramène « à la première heure du dernier jour ouvré d'avant », soit un jour entier trop
  tôt pour une durée de quelques heures écoulées : le prédécesseur reçoit une fin au plus tard
  antérieure à sa fin au plus tôt.
- **Scénario** (rejoué) : calendrier 8 h, A 13 h → B 0,5 eh → C 1 j, et D 2 j → C. A finit mardi
  5 h, B mardi 5–5,5 h, C mercredi. Rendu : **A marge −0,625 j, critique, aucun conflit**, alors
  que B porte +0,3125 j. Avec B = 0,5 h de travail, A porte +0,3125 j.
- **Déjà connu, mais déclaré clos** : #2816/#2832, portés par US-1820 d'EP-23 (livré), dont le
  critère n'éprouve que 1, 2, 3 et 5 ej (`docs/roadmap/EP-23-…md:870-874`) et dont la phrase est
  « qu'aucune tâche ne se dise critique, ou en marge négative, sans conflit qui l'explique ». Les
  unités `eh` et `emin` — que MS Project exporte — ne sont pas couvertes.
- **Proposition** : dans `latest_start`, chercher le dernier départ du jour dont la fin placée
  tient encore le compte (départ = fin du travail du jour − ce que la durée écoulée en consomme),
  au lieu de la première heure du jour ; étendre le test paramétré de #2832 à 0,5 eh, 2 eh, 30 emin,
  et le test de propriété de BPL-01 aux durées écoulées.
- **Confiance** : confirmé (exécuté ; 185 structures fautives sur 3 000 tirées avec des durées
  écoulées).

### BPL-04 — La passe arrière est quadratique sur une liaison entre récapitulatives, à chaque écriture

- **Issue** : #4414 (EP-32), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `core/planning/scheduling/engine.py:278-288` (trois boucles : feuille × liaisons de ses
  ancêtres × feuilles du successeur) et `scheduling/links.py:57-66` (`below`/`leaves` recalculés,
  récursifs, à chaque tour) ; appelé par toute écriture : `core/planning/rescheduling.py:90-131` (`replayed`).
- **Quoi** : une liaison d'une récapitulative de *n* feuilles vers une de *m* feuilles coûte
  *n × m* appels de `bound` (fractions, `late_span`, `moment`), et autant de parcours du
  sous-arbre.
- **Mesure** (annexe ; machine chargée par les autres relecteurs, le rapport des temps vaut plus
  que leur valeur) : chaîne plate de 1 000 tâches : 0,11 s ; **dix phases de 100 feuilles
  enchaînées phase→phase : 3,3 s** ; deux récapitulatives de 500 feuilles et une liaison : 8,9 s.
  Enchaîner des phases par leurs récapitulatives est la forme la plus courante d'un planning
  importé de MS Project.
- **Scénario** : sur un tel planning de 1 000 tâches (la taille du §4.6.2), chaque validation de
  cellule — un libellé, un état (`setTaskProgress`), une inscription (`setNodeTracking`), qui ne
  changent aucune date mais rejouent tout le moteur (`write.redate`) — tient le verrou de la
  structure (`FOR UPDATE`) plusieurs secondes ; les autres contributeurs attendent ; la seconde du
  §4.6.2 que #196 confie à EP-06 n'est pas tenue ; le changement d'une constante d'unités, qui
  redate toutes les structures en cours dans sa transaction (`interface/reference.py:91-111`),
  se compte en minutes. Le témoin ne le montre pas : il ne porte aucune liaison de récapitulative.
- **Proposition** : calculer une fois par liaison la borne que ses successeurs laissent (le
  minimum sur les feuilles du successeur, par calendrier du prédécesseur — et par durée pour une
  liaison depuis un début), mémoriser `leaves()` par tâche ; coût : une trentaine de lignes dans
  `backward`, risque nul sur les dates (passe avant intacte). Test : borne de temps relative
  (dix phases de 100 ≤ quelques fois la chaîne plate de 1 000), ou compteur d'appels de `bound`.
  Second levier, indépendant : ne pas rejouer le moteur pour une écriture qui ne touche ni durée,
  ni mode, ni date, ni liaison, ni arbre.
- **Confiance** : confirmé (mesuré sur le moteur seul ; le temps sous verrou d'une requête réelle
  n'a pas été mesuré).

### BPL-05 — « Tâche sans heure travaillée » levé par le moteur n'est traduit nulle part : 500

- **Issue** : #4413 (EP-32), ouverte le 2026-11-21.
- **Où** : `core/planning/scheduling/engine.py:80-82` (`TaskWithoutWorkingHoursError`, une
  `Exception` hors `ServiceError`), `core/planning/dating.py:152-158` (`dated` ne traduit que
  `LinkCycleError` et `LinkForbiddenError`), `core/planning/interface/reference.py:120-136`
  (`redate_copy`), `:66-88` (`tasks_left_idle`).
- **Quoi** : les gardes du référentiel (`tasks_left_idle`, et celle du devis,
  `core/estimate/interface/calendars.py:118`) ne regardent que les **révisions en cours**. Un
  calendrier peut donc laisser sans heure une tâche qui n'existe que dans une révision marquée ;
  à l'ouverture de la révision suivante, `copy_nodes` puis `redate_copy` rejouent le moteur, qui
  lève une exception que rien ne traduit dans l'enveloppe.
- **Scénario** : le projet P est entre deux revues — dernière révision marquée, aucune en cours,
  l'état de repos normal. Une tâche porte des lignes de deux rôles. Le gestionnaire du référentiel
  change le calendrier d'un rôle (ou donne au rôle un autre calendrier) : les deux calendriers
  n'ont plus de jour commun. La garde passe, P n'ayant pas de révision en cours. Le chef de projet
  ouvre une révision : 500, sans code ni projet nommé, à chaque essai, jusqu'à ce que le
  référentiel soit corrigé — par quelqu'un à qui rien ne dit quoi corriger. Variante plus simple :
  calendrier par défaut passé à zéro heure alors qu'aucune révision en cours n'a de tâche (état
  que `test_planning_start.py:174` tient pour possible), puis premier `createNode` automatique
  d'un projet : 500.
- **Vérifié** : aucune occurrence de `TaskWithoutWorkingHoursError` ni de
  `SchedulingRefusalError` hors de `scheduling/` (`grep -rn` sur `src/`) ; aucun garde à
  l'ouverture (`grep idle core/revisions`) ; le crochet de copie du devis ne juge pas les
  calendriers (`core/estimate/interface/facet.py:82`). Non rejoué en base : le statut 500 est
  déduit du type de l'exception.
- **Proposition** : traduire dans `dated` le refus du moteur en 422
  `TASK_WITHOUT_WORKING_HOURS`, la tâche nommée (code déjà au contrat, `ProblemParams.tasks`) ;
  et à l'ouverture, soit étendre les gardes à la dernière révision marquée de chaque projet sans
  révision en cours, soit rendre ce 422 par `create_revision`. Tests : l'ouverture après le
  changement de calendrier ; le `createNode` sur calendrier par défaut vide.
- **Confiance** : plausible — la pièce non vérifiée est l'exécution contre PostgreSQL (statut
  réellement rendu).

## Constats mineurs

### BPL-06 — Marge négative sans signalement quand la liaison vise la récapitulative d'une tâche manuelle

- **Issue** : #3335 (ouverte).
- **Où** : `core/planning/scheduling/engine.py:335-356` (`conflicts`, l.343 : le successeur doit
  être lui-même une feuille manuelle).
- **Quoi / scénario** (rejoué) : P 5 j → S (récapitulative) dont la subordonnée M est manuelle,
  datée mercredi. La passe arrière borne P par M (liaison vers une récapitulative = vers chacune
  de ses subordonnées) : P marge −3 j, critique ; mais `link_conflicts` est vide, puisque le
  successeur de la liaison est S. Le chef de projet voit un retard de trois jours que rien ne
  nomme (WF-PLA-0100 : « porte une marge négative, et le conflit est signalé »).
- **Proposition** : dans `conflicts`, juger chaque feuille manuelle sous le successeur d'une
  liaison, comme `place` et `backward` le font ; test sur l'exemple.
- **Confiance** : confirmé (exécuté).

### BPL-07 — Une liaison FF ou DF vers une récapitulative retarde chaque subordonnée, pas la seule fin

- **Issue** : #3335 (ouverte).
- **Où** : `core/planning/scheduling/engine.py:228-250` (`place`, l.237-242).
- **Quoi / scénario** (rejoué) : P 5 j (finit vendredi), fin-à-fin vers S = {A 1 j → B 1 j}.
  Chaque feuille doit finir après P : A est placée vendredi, B lundi, S finit **lundi**, un jour
  ouvré après ce que la liaison demande (A jeudi, B vendredi la satisfont). MS Project refuse
  FF et DF vers une récapitulative ; Waterfall les accepte avec cette lecture, écrite dans la
  docstring du moteur mais pas dans la spécification.
- **Proposition** : à trancher par l'auteur — refuser FF/DF vers une récapitulative
  (`LINK_FORBIDDEN`), ou ne borner que la fin de la récapitulative. Coût faible, mais change des
  dates : à décider avant qu'un planning réel en porte.
- **Confiance** : confirmé (exécuté) ; la gravité dépend de la règle voulue.

### BPL-08 — La fin d'une tâche manuelle à durée écoulée n'est pas bornée aux heures du jour

- **Issue** : #4412 (EP-32), ouverte le 2026-11-21, avec BPL-03.
- **Où** : `core/planning/entries.py:122-135` (`finish_after`, l.134).
- **Quoi / scénario** (rejoué) : tâche manuelle commençant lundi 0 h sur un calendrier de 8 h,
  durée saisie « 10 eh » : fin écrite `lundi, hours = 10`, plus que les heures travaillées du
  jour, alors que le moteur borne la même durée en automatique (`calendar.bounded`, lundi 8 h) et
  que `_instant` refuse à la saisie des heures au-delà de celles du jour (l.90-92).
  `WorkInstant.hours` du contrat (« heures de travail écoulées ce jour ») n'est plus tenu ; la
  contrainte de base (0–24) ne le voit pas.
- **Proposition** : `calendar.bounded(origin.elapsed(hours)).instant()` ; test sur 10 eh et sur
  1 ej depuis un vendredi.
- **Confiance** : confirmé (exécuté).

### BPL-09 — Récursions non bornées sur la profondeur de l'arbre, qu'aucune règle ne borne

- **Issue** : #4464 (EP-38), ouverte le 2026-11-21, avec 7 autres constats.
- **Où** : `scheduling/engine.py:360-373` (`total_float`), `scheduling/links.py:57-62` (`below`),
  `views.py:195-204` (`state_of`), `interface/nodes.py:226-229` (`_depth_first.level`, copie d'une
  révision), `restoring.py:343-345` (`_depth`).
- **Quoi** : aucune borne de niveau à la création, au déplacement ni à l'import (`OutlineLevel`).
  Mesuré sur le moteur seul : 990 niveaux passent, 1 100 lèvent `RecursionError` (moins sous la
  pile d'une requête). Un fichier MSPDI fabriqué de 1 000 niveaux fait échouer l'analyse par une
  exception non typée ; une structure aussi profonde bloque toute écriture (500) jusqu'à la
  suppression du sous-arbre.
- **Proposition** : borner le niveau (une centaine suffit à tout planning réel) dans
  `_judge_parent`, `_judge_move` et le plan d'import, ou dérouler ces cinq récursions (elles ont
  toutes une forme itérative de quelques lignes, comme `Tree.subtree`). Faible risque, cas
  fabriqué.
- **Confiance** : confirmé pour le moteur (exécuté) ; plausible pour les routes.

### BPL-10 — L'abandon d'une révision laisse les inscriptions des lignées qu'elle a créées

- **Issue** : #4417 (EP-32), ouverte le 2026-11-21.
- **Où** : `core/planning/interface/closing.py:27-37` (`delete_nodes`), à comparer à
  `core/planning/shaping.py:172-195` (`deleted`, qui supprime les inscriptions des lignées
  qu'aucun nœud ne porte plus).
- **Quoi / scénario** : une tâche créée dans la révision en cours est inscrite à une chronologie ;
  la révision est abandonnée. Ses nœuds partent, sa `tracking_entry` reste, lignée sans nœud,
  invisible, jusqu'à la suppression de la chronologie. WF-DAT-0010 / Conception (« l'abandon d'une
  révision pleine ne laisse aucune ligne »).
- **Proposition** : dans `delete_nodes`, supprimer les inscriptions des lignées que plus aucun
  nœud du projet ne porte après la suppression (la requête de `deleted`, mise en commun) ; test
  d'abandon qui compte `tracking_entry`.
- **Confiance** : confirmé (lecture ; seule suppression d'inscriptions par lignée :
  `shaping.py:192`).

### BPL-11 — Les modules privés importent le paquet `interface`, qui les importe : ordre d'import fragile

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — fragilité de développeur sans
  chemin d'exécution du service : l'erreur se dit d'elle-même à l'import, et le correctif déplace
  deux modules importés par dix-sept modules privés qu'EP-08 est en train d'écrire.
- **Où** : `core/planning/tree.py:23`, `shaping.py:19-20`, `rescheduling.py:24`, `carrying.py:18`,
  `views.py:22`, `writing.py:34`, `reading.py:18`, `restoring.py:39-40`.
- **Quoi** : `import waterfall.core.planning.entries` (ou `dating`, `tree`) **en premier** échoue :
  `ImportError: cannot import name 'ENTRIES' from partially initialized module` (exécuté). Tout
  tient parce que chaque point d'entrée importe d'abord `…planning.interface`. Un test du noyau
  qui importe un module privé seul, ou un outil, casse sans rapport apparent.
- **Proposition** : sortir `facets` et `open_lines` (registres purs, sans import du reste) du
  paquet `interface` vers des modules privés que `interface` réexporte ; ou un test qui importe
  chaque module du paquet dans un interpréteur neuf. Coût : deux déplacements de fichiers.
- **Confiance** : confirmé (exécuté).

### BPL-12 — Lectures de toute la structure pour une ligne, et lectures par ligne dans le collage

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue le dit « plausible, coût
  non mesuré, à mesurer avant d'optimiser », et le poste principal (calendrier et constantes par
  ligne) est corrigé.
- **Où** : `interface/nodes.py:772-783` (`resolve_row_number`) et `:723-756`
  (`computed_value_dependencies`) lisent tout l'arbre (jointure `node`/`task`, puis `held_open`)
  pour rendre une ligne ; `interface/nodes.py:456`, `:462`, `:586`, `:592` (`judge_creation`,
  `judge_cell`) lisent le calendrier applicable et les constantes d'unités **à chaque ligne** d'un
  collage, à l'aperçu puis à la confirmation (`interface/paste.py:531-594`) ;
  `traced_creation` (`nodes.py:636-655`) reconstruit et retrie l'arbre entier à chaque ligne
  créée ; `carrying.py:85-102` lit un calendrier par ligne déplacée.
- **Quoi** : un collage de 500 lignes fait de l'ordre de 2 × 500 × (calendrier par défaut,
  calendriers des rôles, unités) requêtes, dont une part sous le verrou de la structure.
- **Proposition** : passer au `Ground` les calendriers (`calendars_of`, déjà groupé) et les
  constantes lus une fois ; `resolve_row_number` peut lire `id, parent_id, kind, rank` seuls.
  Aucune mesure faite : à mesurer avant d'optimiser.
- **Confiance** : plausible (lecture ; coût non mesuré).

## Points forts

- **Un seul cadre d'écriture** (`core/planning/writing.py:331-346`, `writing`) : révision jugée sous
  `FOR SHARE`, pile d'historique, puis `cost_structure FOR UPDATE`, arbre relu sous le verrou
  (`populate_existing`), une transaction pour l'écriture, le recalcul et l'entrée d'historique ;
  création, modification, prédécesseurs, état, inscriptions, collage, squelette, lignes, annulation
  y passent tous. Versions comparées sous le verrou. Tests de concurrence présents
  (`test_nodes_state.py:306`, `test_progress.py:583`, `test_tracking.py:428,475`,
  `test_history.py:393,425`).
- **Moteur pur et exact** : fractions, rendu à dix décimales, instant « jour + heures de travail »,
  lecture fin/début d'un même compte ; jalon placé à la fin de son prédécesseur ; date de début de
  planning sur un jour chômé du calendrier de la tâche correctement reportée.
- **Refus** : cycles nommés par la plus courte chaîne depuis la tâche saisie, liaison
  récapitulative–subordonnée refusée d'abord, déplacement sous soi-même (`NODE_CYCLE`), tâche sous
  un jalon, horizon de quinze ans par la tâche écrite ; durée et décalage bornés à dix chiffres.
- **Frontières** : aucun SQL en texte, les lignes du devis lues, copiées et supprimées par les
  crochets `register_facet` ; suppression en cascade des liaisons et inscriptions soignée.
- **Annulation** : conflits jugés sur le parent, la place et le rattachement ; rattachement à un
  élément disparu abandonné plutôt que refusé.
- **Plan de charge** (`core/estimate/spreading/spread.py`, `workloading.py`) : parts exactes, la
  dernière prend le reste (somme = total), un seul arrondi au centième par rôle et par mois, les
  totaux additionnent l'arrondi.

## Couverture

- **Lu en entier** : `core/planning/scheduling/` (6 fichiers), `dating.py`, `rescheduling.py`,
  `calendars.py`, `tree.py`, `reading.py`, `tables.py`, `writing.py`, `entries.py`, `shaping.py`,
  `applying.py`, `carrying.py`, `views.py`, `restoring.py`, `snapshotting.py` ;
  `interface/nodes.py`, `predecessors.py`, `structures.py`, `reference.py`, `closing.py`,
  `facets.py`, `progress.py`, `tracking.py`, `timelines.py`, `skeleton.py`, `work_breakdown.py` ;
  `msproject/translation.py` ; `api/nodes.py`, `scheduling.py`, `timelines.py`, `workload.py`,
  `startable_tasks.py`, `progress.py`, `skeleton.py` ; `core/estimate/spreading/spread.py` et
  `workloading.py` (pour l'angle plan de charge) ; `docs/dev/agents.md` (sections demandées),
  `python.md`, `sql.md`, la Conception d'EP-06, les exigences WF-PLA-0010 à 0170 et WF-PRJ-0030,
  WF-DEV-0070, US-1820 d'EP-23.
- **Échantillonné** : `interface/paste.py` (jugement, aperçu, confirmation ; pas le codage du
  plan ni les lignes), `importing.py` (facette, dates manuelles, rejeu du moteur), `filters.py`,
  `interface/lines.py` et `loading.py` (plan et verrous seulement), `interface/__init__.py`
  (enregistrements), `api/work_breakdown.py` (en-tête et routes) ; les tests par leurs noms, un
  balayage AST (assertions, marqueurs) et quelques corps (`test_scheduling_examples.py`,
  `test_nodes_move.py`) ; le contrat pour `finish_overdue` et `NodeSchedule` seulement.
- **Non lu** : `attachments.py`, `calendar_gap.py`, `exporting.py`, `task_tree_image.py`,
  `interface/task_tree.py`, `open_lines.py`, `snapshots.py`, `interface/msproject.py`,
  `msproject/reader.py`, `writer.py`, `model.py`, `tree.py`, `header.py` ; le noyau du Kanban
  (`core/estimate` : `startable_tasks`) ; les parts d'EP-24 ; `docs/api/paths/revisions.yaml`
  dans son détail (codes et statuts non confrontés route par route) ; aucun test n'a été lancé.
- **Non constats** : le jour courant et la date de calcul pris en UTC (plan de charge,
  `current_day`) — déjà connu (#2527, EP-13/EP-25) ; `finish_overdue` jugé à la date du dernier
  calcul — c'est le contrat ; une avance qui place un successeur avant la date de début de
  planning — non tranché par la spécification, éprouvé par un test.

## Annexe — reproduction des constats du moteur

À lancer depuis la racine du dépôt : `backend/.venv/bin/python <fichier>` (ni base ni réseau).

```python
import time
from datetime import date, timedelta
from decimal import Decimal as D
from uuid import UUID
from waterfall.core.planning.scheduling import (Calendar, Duration, Lag, Link, Structure, Task,
    UnitConstants, WorkInstant, schedule)
C8 = Calendar((D(8),) * 5 + (D(0), D(0))); K = UnitConstants(D(8), D(40), D(20)); MON = date(2026, 11, 16)
N = {}
def T(name, parent=None, d=1, u="d", mode="automatic", start=None, finish=None):
    t = Task(UUID(int=len(N) + 1), parent, mode, Duration(D(str(d)), u), C8, start, finish); N[t.task_id] = name; return t
def L(p, s, t="finish_to_start", lag=0): return Link(p.task_id, s.task_id, t, Lag(D(lag), "d"))
def run(title, tasks, links):
    r = schedule(Structure(tuple(tasks), tuple(links), MON, K)); print(title)
    for k, v in r.tasks.items(): print(f"   {N[k]:3} {v.start.day:%a %d} {v.start.hours} -> {v.finish.day:%a %d} {v.finish.hours}  float={v.total_float} critical={v.is_critical} conflicts={len(v.link_conflicts)}")
s = T("S"); a = T("A", s.task_id); b = T("B", s.task_id); t = T("T", d=5)
run("BPL-01 SS from a summary", [s, a, b, t], [L(a, b), L(s, t, "start_to_start")])
a = T("A", d=13, u="h"); b = T("B", d="0.5", u="eh"); c = T("C"); d = T("D", d=2)
run("BPL-03 elapsed half hour", [a, b, c, d], [L(a, b), L(b, c), L(d, c)])
p = T("P", d=5); s = T("S"); m = T("M", s.task_id, mode="manual", start=WorkInstant(MON + timedelta(2)), finish=WorkInstant(MON + timedelta(2), D(8)))
run("BPL-06 link to the summary of a manual task", [p, s, m], [L(p, s)])
p = T("P", d=5); s = T("S"); a = T("A", s.task_id); b = T("B", s.task_id)
run("BPL-07 FF to a summary", [p, s, a, b], [L(a, b), L(p, s, "finish_to_finish")])
tasks, links, prev = [], [], None
for i in range(10):
    s = T(f"P{i}"); tasks += [s, *(T("x", s.task_id) for _ in range(100))]; links += [L(prev, s)] if prev else []; prev = s
t0 = time.perf_counter(); schedule(Structure(tuple(tasks), tuple(links), MON, K)); print("BPL-04 10 phases x 100, phase->phase:", round(time.perf_counter() - t0, 2), "s")
chain = [T("c") for _ in range(1000)]
t0 = time.perf_counter(); schedule(Structure(tuple(chain), tuple(L(chain[i], chain[i + 1]) for i in range(999)), MON, K)); print("       flat chain of 1000:", round(time.perf_counter() - t0, 2), "s")
```

Sortie obtenue :

```
BPL-01 SS from a summary
   S   Mon 16 0 -> Tue 17 8  float=-1 critical=True conflicts=0
   A   Mon 16 0 -> Mon 16 8  float=-1 critical=True conflicts=0
   B   Tue 17 0 -> Tue 17 8  float=-1 critical=True conflicts=0
   T   Mon 16 0 -> Fri 20 8  float=0 critical=True conflicts=0
BPL-03 elapsed half hour
   A   Mon 16 0 -> Tue 17 5  float=-0.625 critical=True conflicts=0
   B   Tue 17 5 -> Tue 17 5.5  float=0.3125 critical=False conflicts=0
   C   Wed 18 0 -> Wed 18 8  float=0 critical=True conflicts=0
   D   Mon 16 0 -> Tue 17 8  float=0 critical=True conflicts=0
BPL-06 link to the summary of a manual task
   P   Mon 16 0 -> Fri 20 8  float=-3 critical=True conflicts=0
   S   Wed 18 0 -> Wed 18 8  float=None critical=False conflicts=0
   M   Wed 18 0 -> Wed 18 8  float=None critical=False conflicts=0
BPL-07 FF to a summary
   P   Mon 16 0 -> Fri 20 8  float=0 critical=True conflicts=0
   S   Fri 20 0 -> Mon 23 8  float=0 critical=True conflicts=0
   A   Fri 20 0 -> Fri 20 8  float=0 critical=True conflicts=0
   B   Mon 23 0 -> Mon 23 8  float=0 critical=True conflicts=0
BPL-04 10 phases x 100, phase->phase: 3.34 s
       flat chain of 1000: 0.11 s
```

# Revue — roadmap et conception des EPIC livrés, vue transverse

Périmètre : `docs/roadmap/README-fr.md`, `MODELE.md`, et les fichiers des EPIC livrés (EP-01 à
EP-07, EP-09, EP-14 à EP-24), confrontés à `docs/spec/waterfall-spec.md`, aux tests
(`backend/tests`, `frontend/src`, `frontend/e2e`), aux migrations et aux interfaces du noyau.
Commit `29785cc`. Lecture seule ; aucun outil du dépôt lancé (`wftools` exige Python 3.14, le poste
a 3.13 : les contrôles de `wftools.roadmap` et `wftools.coverage` ont été rejoués par des scripts
d'analyse à moi, d'après leur code).

## Synthèse

La roadmap est, mécaniquement, très tenue : les 218 exigences du produit sont closes chacune par un
seul EPIC, les 1 628 phrases de Vérif citées par les US y figurent mot pour mot, toutes les US des
EPIC livrés sont `fini`, la liste du README et les front matter concordent, et les conceptions des
EPIC du back (tables, migrations 0018 à 0028, registres d'extension, frontières des modules) sont
celles que le code porte. Les tests sont nommés d'après les phrases de Vérif, et sur 112 exigences
closes par du livré, 111 sont citées par la famille de tests qui doit les prouver.

Ce qui inquiète tient à **ce que « close » veut dire** : la clôture est jugée sur la présence de la
phrase dans une US, pas sur sa preuve. Trois mécanismes laissent une exigence close alors qu'une
part n'est ni réalisée ni prouvée : (1) la spécification ajoute des phrases à des exigences déjà
closes, et l'EPIC qui les réalisera ne les porte pas à son tableau (WF-IHM-0010, WF-IHM-0070) ;
(2) des renvois « constaté par EP-nn » qui ne répondent pas, ou qui tournent en rond
(WF-IHM-0080 et ses dix mille objets, WF-DAT-0100, WF-DAT-0070) ; (3) des constats connus sur une
phrase de Vérif d'une exigence close, reportés vers un EPIC dont le tableau ne la reprend pas
(WF-ADM-0160, WF-EXP-0020). S'y ajoute un report sans porteur : la capacité d'un rôle
(WF-REF-0100, spécification 1.0.4), dite « à EP-10 » par trois fichiers, absente du fichier d'EP-10.

Aucune contradiction de conception entre EPIC livrés n'a été trouvée sur le verrouillage optimiste
(404, puis 412, puis 409 partout où je l'ai lu), l'arrondi (`ROUND_HALF_UP`, une fois par ligne) ni
la propriété des tables. La seule divergence relevée est une dette reconnue : des compteurs qui
naissent à 0 ou à 1 selon la table, remise « à la v1 » sans EPIC qui la porte.

## Constats bloquants

### RMP-01 — WF-EXP-0020-A est close par EP-07 alors que le fuseau de l'installation, que son corps exige, n'existe pas — déjà connu (#2527, EP-25 US-2200)

- **Issue** : #3382 (fermée) — le fuseau de l'installation, traité au tri des constats de
  spécification du 2026-11-18.
- **Où** : `docs/roadmap/EP-07-chiffrage-et-devis.md:124` (portée « fin », US-1550) et `:242-247`
  (« US-1550, qui clôt WF-EXP-0020-A, l'ajoute ») ; `docs/roadmap/EP-13-exploitation.md:618-623`
  (« US-1550 devait le porter et ne l'a pas fait ») ; `docs/roadmap/EP-25-refonte-ergonomique.md:173`
  et `:221` ; `docs/spec/waterfall-spec.md:4242` (corps : « … et son fuseau horaire, dans lequel
  s'entend le jour courant ») ; `backend/src/waterfall/core/projects/interface/days.py:7-9` et `:18-25`.
- **Quoi** : l'exigence est déclarée close par un EPIC livré, son US `fini`, alors qu'une part de
  son corps n'est pas réalisée : `current_day` rend le jour en UTC. Le Vérif ne cite pas le fuseau,
  ce qui a laissé passer la clôture. Le fichier d'EP-07 dit toujours que US-1550 l'ajoute, et la
  docstring de `days.py` « until EP-07 gives the installation its own ».
- **Scénario** : installation à Paris ; un chef de projet termine une tâche au Kanban à 0 h 30
  locale. `completed_on` proposé par défaut est la veille (22 h 30 ou 23 h 30 UTC) ; de même la date
  de revue par défaut d'un export de reste à engager et le début de planning d'une structure créée
  (les trois appelants que la docstring nomme). Une date d'état fausse entre dans la valeur acquise.
- **Proposition** : c'est le travail d'US-2200 (EP-25, migration `0029`). Côté roadmap : passer la
  portée d'EP-07 à « début — close en EP-25 », porter WF-EXP-0020-A au tableau d'EP-25 (qui ne
  porte que WF-IHM-0130-A, `EP-25:85`), corriger `EP-07:242-247` et la docstring. Test qui le
  prouve : celui que `EP-25:131` annonce (tâche terminée à 0 h 30, fuseau de Paris, datée du jour).
  Faire entrer le fuseau dans le Vérif (constat de spécification) éviterait la récidive.
- **Confiance** : confirmé (corps de l'exigence, tableau, code et absence de toute colonne ou
  lecture de fuseau dans `backend/src/waterfall` lus). Gravité prise de la grille (« exigence
  déclarée close et non tenue », « date fausse ») ; le défaut est connu et planifié.

## Constats majeurs

### RMP-02 — Deux exigences restent « entières, closes par EP-02 » alors qu'une phrase de leur Vérif attend un EPIC non livré, qui ne les porte pas à son tableau

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — EP-27 et EP-25 sont livrés et
  fusionnés ; US-2330 cite WF-IHM-0010-A avec tout son Vérif et porte en critère (non en écart) la
  phrase « Une comparaison active sur le planning l'est encore sur le devis puis sur le reste à
  engager, avec la même base », et US-2160 porte de même la phrase de la préférence des motifs de
  WF-IHM-0070-A (et les deux phrases de WF-ADM-0040-A).
- **Où** : `docs/roadmap/EP-02-maquette-du-front.md:80` et `:731-733` (WF-IHM-0010-A, « EP-27 le
  réalise ») ; `:86` et `:1009-1012` (WF-IHM-0070-A, « EP-25 le réalise ») ;
  `docs/roadmap/EP-27-comparaison-dans-les-grilles.md:49-58` ; `docs/roadmap/EP-25-refonte-ergonomique.md:70-85` ;
  règle : `docs/roadmap/README-fr.md:58-62`.
- **Quoi** : la spécification 1.0.6 ajoute une phrase au Vérif de WF-IHM-0010-A (« Une comparaison
  active sur le planning l'est encore sur le devis puis sur le reste à engager, avec la même base. »)
  et de WF-IHM-0070-A (la préférence des motifs). Les US d'EP-02 et d'EP-17 les notent en écart,
  mais la portée reste `entière` chez EP-02, et ni EP-27 ni EP-25 n'ont la ligne. C'est une décision
  écrite (`EP-25:70-72`, `EP-27:51-52`), et elle contredit le README : « Une exigence n'est close que
  par un seul EPIC : c'est lui qui la vérifie en entier. »
- **Scénario** : `make roadmap` passe (la phrase figure, en écart) ; `make requirements` compte les
  deux exigences couvertes par les tests du front d'EP-02, alors qu'aucun test ne peut prouver la
  phrase ajoutée ; `make requirements-release` publierait. Pour EP-27, encore `à planifier`, rien
  de mécanique n'oblige ses US à citer WF-IHM-0010-A : la règle « au tableau mais aucune US ne la
  cite » ne joue que pour une exigence au tableau. WF-ADM-0040-A (close par EP-04) est dans le même
  cas pour son corps (préférence des motifs, `spec:1278`), sans phrase de Vérif.
- **Proposition** : rouvrir la portée — EP-02 « début — close en EP-27 » pour WF-IHM-0010-A et
  « début — close en EP-25 » pour WF-IHM-0070-A —, avec la ligne « fin — amorcée en EP-02 » aux
  tableaux d'EP-27 et d'EP-25. Coût : quatre lignes de tableau et la famille de preuve qui change
  (EP-25 et EP-27 sont `front, back`, le front seul ne suffira plus : à trancher). Preuve : `make
  requirements` les montre non couvertes jusqu'au test de la phrase.
- **Confiance** : confirmé.

### RMP-03 — WF-IHM-0080-A est close par EP-09 sans que le marquage « d'une révision de dix mille objets » ait jamais été constaté : trois fichiers se renvoient la phrase

- **Issue** : #4446 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `docs/roadmap/EP-02-maquette-du-front.md:1063-1066` (« le volume … se constate sur le
  marquage réel, en EP-04 ») ; `docs/roadmap/EP-04-projets-et-revisions.md:1191-1193` (« écart … les
  objets sont d'EP-06 et d'EP-07 … EP-09 clôt ») ; `docs/roadmap/EP-09-couts-reels-et-reste-a-engager.md:116`
  et `:1654-1655` (« constaté par EP-04 ») ; `docs/roadmap/EP-23-dette-constats-ep02-ep03.md:560`.
- **Quoi** : l'EPIC qui clôt renvoie la phrase à EP-04, qui l'avait notée en écart faute d'objets
  et renvoyée à EP-09. Aucun test ne marque une révision de dix mille objets : le seul test du back
  qui cite l'exigence est l'échec et la relance (`backend/tests/test_revision_mark.py:461-463`), les
  parcours (`frontend/e2e/tasks.spec.ts:71`, `revision-cycle.spec.ts:92`) marquent une révision vide
  ou le faux back. Aucun fichier d'EP-13, d'EP-25 ni d'EP-26 ne reprend le volume (US-2170,
  `EP-25:909-911`, ne traite que le bouton inerte).
- **Scénario** : une régression qui rendrait le marquage d'une révision de 1 000 tâches et 5 000
  lignes lent ou bloquant (les images d'EP-07 et le calcul d'EP-10 s'ajoutent dans la transaction
  du marquage) ne ferait échouer aucun test, l'exigence restant close. Le constat voisin #3102
  (ouvrir une révision d'un projet de mille tâches prend dix secondes, EP-26) montre que ce volume
  n'est pas anodin.
- **Proposition** : soit un test contre le service sur le projet de volume (dix mille objets,
  marquage par le worker, écran utilisable, avancement lu), porté par EP-26 qui mesure déjà ces
  volumes, et la portée d'EP-09 passée à « début — close en EP-26 » ; soit, au minimum, corriger
  `EP-09:1654-1655` en écart qui nomme son porteur.
- **Confiance** : confirmé pour le renvoi circulaire et l'absence de test citant l'exigence à ce
  volume (recherche de « dix mille », `10000`, `10_000`, « thousand », « volume » dans
  `backend/tests` et `frontend/e2e`) ; je n'ai pas cherché un test de volume qui ne citerait pas
  l'exigence au-delà de ces motifs.

### RMP-04 — WF-ADM-0160-A est close par EP-04 alors que deux de ses phrases ont un défaut ou un manque reporté à EP-13, qui ne la porte pas — déjà connu (#1743, #2229, EP-13)

- **Issue** : #4447 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `docs/roadmap/EP-04-projets-et-revisions.md:110` (« fin — amorcée en EP-03 ») et
  `:1209-1214` ; `docs/roadmap/EP-03-comptes-et-habilitations.md:1768-1771` (« la planification
  conservée est … du service en EP-13 (#1743) ») ; `docs/roadmap/EP-13-exploitation.md:144-145`
  et `:610-612` ; `docs/roadmap/EP-23-dette-constats-ep02-ep03.md:572` et `:805`.
- **Quoi** : la phrase « … hors le journal d'audit, la liste des sauvegardes et leur planification,
  qui gardent leurs inscriptions, leurs sauvegardes et leurs réglages » attend la planification
  d'EP-13 (#1743), et la phrase « Une inscription faite après la sauvegarde est encore présente
  après la restauration » a un défaut connu (#2229 : une écriture admise avant la maintenance perd
  son inscription d'audit). Le critère d'EP-04 reprend la première phrase sans écart et ne dit
  rien de la planification ; le tableau d'EP-13 n'a pas WF-ADM-0160-A.
- **Scénario** : EP-13 corrige #2229 et sert #1743 sans qu'aucune US n'ait à citer WF-ADM-0160-A ni
  son Vérif : les tests de ces corrections peuvent ne pas citer l'exigence, qui reste « prouvée »
  par les tests d'EP-03 et d'EP-04.
- **Proposition** : portée d'EP-04 « début — close en EP-13 », ligne « fin — amorcée en EP-03,
  EP-04 » au tableau d'EP-13, écart explicite dans US-0970. Preuve : le test de #2229 (une écriture
  admise juste avant la maintenance, son inscription relue après restauration) cite WF-ADM-0160-A.
- **Confiance** : confirmé pour la traçabilité ; le défaut #2229 lui-même n'a pas été relu dans le
  code (il revient au relecteur des sauvegardes).

### RMP-05 — WF-PLA-0090-A, close par EP-06 (`front, back`), n'est citée que par les familles du front : « front seul » pour `make requirements-release`

- **Issue** : #4415 (EP-32), ouverte le 2026-11-21, avec FTE-01.
- **Où** : `docs/roadmap/EP-06-planification.md:116` ; `tools/src/wftools/coverage.py:249-255`
  (`front_only`) et `:48` (`FRONT_FAMILIES`) ; `tools/paths.toml:778` (`end-to-end-service =
  ["frontend/e2e/service/**"]`) ; `frontend/e2e/planning-service.spec.ts:70` et `:327` ;
  `frontend/e2e/planning.spec.ts:459`, `:510`, `:526`.
- **Quoi** : aucune citation dans `backend/tests` ni dans `frontend/e2e/service/` ; 21 dans
  `frontend/src` et `frontend/e2e`. Par la règle du README (`README-fr.md:114-116`), elle n'est
  donc pas prouvée. Les deux parcours de `planning-service.spec.ts` ne jouent pourtant que contre
  le service (`test.skip(!inService, …)`, lignes 76 et 333) : ils traversent le back, mais leur fichier
  est rangé hors de `e2e/service/` et compte pour le front.
- **Scénario** : `make requirements-release` échoue sur « not covered: WF-PLA-0090-A (front
  alone) » à la première publication qui l'exige ; ou bien on retire la liaison ou le chemin
  critique de la réponse de `listNodes` et aucun test du back qui cite l'exigence n'échoue.
- **Proposition** : citer WF-PLA-0090-A dans un test du back qui lit ce que le Gantt dessine
  (liaisons, hiérarchie, `is_critical` de `listNodes`) ; ou déclarer dans `tools/paths.toml` que
  les fichiers `*-service.spec.ts` sont de la famille `end-to-end-service`. Le second corrige aussi
  la sous-estimation générale des parcours `@shared` joués contre le service. Preuve : la sortie de
  `make requirements` ne porte plus « (front alone) ».
- **Confiance** : confirmé par la lecture de l'outil et le relevé des citations ; l'outil lui-même
  n'a pas été lancé.

### RMP-06 — Deux phrases de Vérif closes par un renvoi « constaté par EP-06 » qu'EP-06 ne porte pas, et qu'aucun test citant l'exigence ne prouve

- **Issue** : #4444 (EP-36), ouverte le 2026-11-21.
- **Où** : `docs/roadmap/EP-07-chiffrage-et-devis.md:88` et `:1113-1114` (WF-DAT-0100-A, « Deux
  tâches de quatre heures liées fin à début, sur un calendrier de huit heures, commencent et
  finissent le même jour. » : constaté par EP-06) ; `docs/roadmap/EP-09-couts-reels-et-reste-a-engager.md:1436-1437`
  (WF-DAT-0070-A, « Après modification d'une tâche par un utilisateur, la ligne porte son compte
  et l'horodatage de la modification. » : constaté par EP-06) ; EP-06 n'a ni l'une ni l'autre
  exigence à son tableau (`EP-06:82-124`) ni dans une US.
- **Quoi** : pour WF-DAT-0100-A, aucun des vingt tests du back qui la citent ne date deux tâches de
  quatre heures (ils portent sur l'arrondi, la précision des décimaux, les fuseaux des horodatages),
  et `fixtures/examples.json:449-458` ne retient pas la phrase parmi les exemples chiffrés. Pour
  WF-DAT-0070-A, aucun des neuf tests qui la citent ne modifie une tâche ; le seul test qui lit
  `Node.updated_by` après une écriture est celui de l'annulation, sous WF-IHM-0110-A
  (`backend/tests/test_undo_routes.py:189-203`).
- **Scénario** : le moteur arrondit une fin au jour suivant quand deux tâches remplissent
  exactement une journée de huit heures (borne fin/début à 8 h de travail) : aucun test qui cite
  WF-DAT-0100-A n'échoue. Ou `update_node` cesse d'écrire `updated_by` : seul un test de
  l'annulation le voit, par chance.
- **Proposition** : un test d'exemple dans `backend/tests/examples/test_scheduling_examples.py`
  (deux tâches « 4 h » liées fin à début, calendrier de huit heures, mêmes `start_date` et
  `finish_date`), citant WF-DAT-0100-A ; un test dans `backend/tests/test_nodes.py` qui modifie une
  tâche et relit `updated_by` et `updated_at`, citant WF-DAT-0070-A. Corriger les deux renvois, ou
  porter les deux exigences au tableau d'EP-06.
- **Confiance** : confirmé pour l'absence de citation (relevé exhaustif des tests citant les deux
  identifiants) ; plausible pour l'absence de tout test équivalent sous un autre identifiant
  (cherché par « 4 h », « four », « same day », « quatre heures », « liées fin à début »).

### RMP-07 — La reprise de la capacité d'un rôle (WF-REF-0100-A, spécification 1.0.4) est dite reportée à EP-10 par trois fichiers ; le fichier d'EP-10 n'en dit rien

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — le fichier d'EP-10 (livré, fusionné
  dans `main`) porte maintenant la ligne « `WF-REF-0100-A` — début — close en EP-11, amorcée aussi
  en EP-05 — US-2410 », #2978 dans ses « Constats reçus » et l'US-2410 (`fini`) qui cite l'exigence
  et réalise la capacité déduite. Le code suit : les tests citant WF-REF-0100-A éprouvent l'exemple
  chiffré (303,33 et 75,83 heures) et la migration des rôles ; #2978 est close (2026-11-17).
- **Où** : `docs/roadmap/EP-24-consolidation-apres-v0-3-0.md:64-67`, `:245-246` (« → EP-10, par
  #2978, ouverte sous #2427 »), `:482`, `:495-497`, `:1184`, `:1191` ;
  `docs/roadmap/EP-05-referentiel.md:968-973` ; `docs/roadmap/EP-10-indicateurs.md` (aucune
  occurrence de `REF-0100`, de `2978`, de `2836`, de « capacité » ni d'« effectif ») ;
  `docs/roadmap/EP-11-portefeuille.md:77` (« fin — amorcée en EP-05 », sans EP-10).
- **Quoi** : depuis la 1.0.4, un rôle porte un effectif et ses heures se déduisent du calendrier
  (`spec:1828-1830`, « 2 × 35 × 52 / 12, soit environ 303,33 heures par mois ») ; le code livré
  garde des heures saisies (`resource_role.monthly_hours`, `headcount`,
  `backend/src/waterfall/migrations/versions/0018_reference.py:258-259`). La reprise — contrat,
  saisie, migration des rôles, et la borne de #2875 — n'est dans aucune US d'EP-10 (onze US, dont
  aucune ne cite WF-REF-0100-A), ni dans ses « Constats reçus », ni dans son tableau.
- **Scénario** : EP-10, `en cours`, se livre par ses US ; le pilote et les livreurs ne lisent que
  le fichier et le tableau de suivi. La reprise ne tient qu'à une issue GitHub (#2978) ; EP-11, qui
  clôt l'exigence sur le plan de charge agrégé, comparera la charge à des heures saisies que la
  spécification ne connaît plus.
- **Proposition** : une US dans EP-10 (ou EP-11) citant WF-REF-0100-A avec son Vérif, la ligne
  « début — close en EP-11, amorcée aussi en EP-05 » au tableau d'EP-10, #2978 dans ses « Constats
  reçus », et la portée d'EP-11 complétée. Preuve : `make roadmap` exige alors les trois phrases
  dans l'US ; le test est l'exemple chiffré (303,33 et 75,83).
- **Confiance** : confirmé pour le fichier (README, « Lire ce répertoire doit suffire ») ; l'état de
  #2978 sur GitHub n'a pas été lu (interdit par le cahier).

## Constats mineurs

### RMP-08 — Des « Portée » dont l'autre bout ne répond pas

- **Issue** : #4455 (EP-36), ouverte le 2026-11-21, avec RMP-09, RMP-13.
- **Où et quoi** (aucune ne change qui clôt, toutes passent `make roadmap`, qui ne confronte pas les
  renvois) :
  - `EP-02:89` et `EP-18:71` : WF-IHM-0110-A « début — close en EP-06 », alors qu'EP-06 la dit
    « début — close en EP-08 » (`EP-06:113`) et qu'EP-08 la clôt (`EP-08:69`, qui n'énumère pas
    EP-18 parmi ses amorces) ;
  - `EP-07:88` : WF-DAT-0100-A « fin — amorcée en EP-03, EP-06 » — EP-06 n'a pas la ligne, EP-02 qui
    l'amorce (`EP-02:95`) n'est pas nommé ; `EP-07:87` : WF-DAT-0090-A « amorcée en EP-03, EP-04,
    EP-06 » — ni EP-04 ni EP-06 n'ont la ligne ;
  - `EP-05:97` : WF-REF-0150-A « entière », alors qu'EP-17 l'amorce (`EP-17:129`) ;
  - des « fin » qui n'énumèrent pas tous leurs débuts : `EP-04:109` (WF-ADM-0060-A, sans EP-17 ni
    EP-18), `EP-04:94`, `EP-04:97`, `EP-06:104`, `EP-06:115-116` ;
  - `EP-02:164-165` : WF-CMP-0010-A « qu'EP-16 commence et qu'EP-13 clôt » — EP-16 n'a pas la
    ligne, EP-13 la dit « entière » (`EP-13:88`) ; `EP-01:61` : WF-QUA-0060 « — EP-13 », passée à
    EP-26.
- **Proposition** : un contrôle de plus dans `wftools.roadmap` — pour chaque « début — close en
  EP-x », EP-x clôt ; pour chaque « fin — amorcée en … », la liste égale celle des EPIC qui portent
  un « début » — et la correction des lignes ci-dessus. Coût : une vingtaine de lignes d'outil ;
  gain : la colonne redevient fiable pour qui cherche « qui doit quoi ».
- **Confiance** : confirmé (relevé exhaustif des 410 lignes de tableau).

### RMP-09 — Trois exigences closes « entières » par EP-02, de la seule famille `front`, dont le travail du back est fait par EP-06 et EP-07 sans qu'aucune de leurs US ne les cite

- **Issue** : #4455 (EP-36), ouverte le 2026-11-21, avec RMP-08, RMP-13.
- **Où** : `EP-02:82-84` (WF-IHM-0030-A, 0040-A, 0050-A, `entière`) ; `EP-06:1710-1715` (US-1450,
  « Le collage et l'annulation servis par le serveur », `previewPaste`, `applyPaste`, ne cite que
  WF-IHM-0110-A) ; `backend/tests/test_paste.py:155` et suivantes, `test_estimate_paste.py:133` et
  suivantes (41 citations de WF-IHM-0050-A), `backend/tests/test_progress.py:297`,
  `test_nodes.py:781`.
- **Quoi** : le Vérif de ces exigences nomme des refus et des comptes rendus que seul le service
  rend (« est refusée en nommant ses subordonnées », « un bloc dont une cellule porte une catégorie
  inconnue signale cette ligne »). EP-02 les a closes sur le faux back ; EP-06 et EP-07 les ont
  réalisées et testées côté service, mais leurs US ne les citent pas : leurs critères ne reprennent
  donc pas ce Vérif. C'est la forme du constat #3186 (EP-10), ici sur du livré. La deuxième phrase
  de WF-IHM-0030-A (« La gravité et la provision d'un risque ne sont pas saisissables ») concerne
  un service qu'EP-08 n'a pas encore écrit, et aucune ligne n'obligera EP-08 à la prouver.
- **Proposition** : ajouter WF-IHM-0050-A à US-1450 et à l'US du collage du devis d'EP-07,
  WF-IHM-0030-A à l'US de l'état des tâches, sans changer qui clôt ; noter à EP-08 la phrase des
  risques. Sans cela, le risque est faible : les tests existent.
- **Confiance** : confirmé.

### RMP-10 — Les compteurs `lock_version` naissent à 0 ou à 1 selon la table ; la dette est reconnue et remise « à la v1 », sans EPIC qui la porte

- **Issue** : #4456 (EP-36), ouverte le 2026-11-21.
- **Où** : `EP-23:81-83`, `:509-510`, `:514` (#2779, #2240) ; `EP-06:885-889` et `:904-907` (#2843,
  « le projet et son lotissement nés à 1, "jamais écrit" lu à `lock_version` 1 ») ; code :
  `server_default="0"` dans `migrations/versions/0001…:61`, `0004…:80`, `0018…:68`, `0020…:176`,
  `:222-223`, `0022…:316`, `0025…:295`, et `lock_version=1` à l'insertion dans
  `core/estimate/writing.py:207` et `core/planning/applying.py:101`.
- **Quoi** : deux EPIC ont décidé différemment de la première valeur d'un compteur, et la remise
  d'aplomb demande une migration de données qu'on ne veut pas faire après la première installation
  réelle. Aucun des fichiers d'EP-13, d'EP-25 à EP-28, d'EP-10 ni d'EP-08 ne cite #2779, #2240 ni
  #2843 : « la v1 » n'est pas un EPIC.
- **Proposition** : noter les trois issues dans les « Constats reçus » d'EP-13 (mise en
  production), avec la condition « avant la première installation qui garde ses données ». Coût
  nul ; risque de ne pas le faire : la fenêtre « aucune installation ne porte de données » se ferme
  sans que personne ne l'ait vu.
- **Confiance** : confirmé.

### RMP-11 — EP-10 est `en cours` avec une conception antérieure à EP-24 : sa migration `0028` est prise, et deux de ses US n'ont ni issue ni opération

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — EP-10 a été recadré le 2026-11-15
  puis livré : sa conception dit « Les migrations ne portent plus de numéro dans ce fichier … `0028`
  est prise », US-2040 et US-2050 ont leur issue (#3506, #3507) et leurs opérations, et ses
  migrations sont `0031` à `0034` dans `main`.
- **Où** : `EP-10:314-316`, `:333`, `:684`, `:702`, `:869` (« une seule migration, `0028`, chaînée
  sur `0027` ») ; `EP-08:116-117` (« la chaîne des migrations arrêtée à `0028` ») ;
  `backend/src/waterfall/migrations/versions/0028_import_duration_rule.py` (EP-24, livré) ;
  `EP-25:221` (`0029`) ; `EP-10:1457-1462` et `:1486-1491` (US-2040, US-2050 : « opérations : à
  écrire au contrat », issue vide) ; `README-fr.md:167` (statut) et `:179-180` (« se relit contre la
  base livrée »).
- **Quoi** : le README définit `en cours` par un plan de lots validé et des issues ouvertes, et
  `prêt` par une conception validée. Celle d'EP-10 nomme six fois une migration qu'un EPIC livré a
  prise, s'appuie sur une série de branches (`epic/EP-10` tirée d'`epic/EP-09`) qui n'a plus
  d'objet, et ne porte pas la capacité d'un rôle (RMP-07).
- **Scénario** : un livreur qui suit la conception à la lettre écrit `0028_…` sur `0027` : deux
  têtes Alembic, que `test_migrations.py` refuserait — le défaut est donc rattrapé, mais au prix
  d'un tour.
- **Proposition** : repasser EP-10 `prêt` (ou `à planifier`) jusqu'à la relecture annoncée, et y
  écrire « les prochains numéros libres », comme `EP-04:442-443` et `EP-05:367-368` l'ont fait.
- **Confiance** : confirmé. EP-10 n'est pas livré : seul l'accord entre sa conception et celles du
  livré est relevé ici.

### RMP-12 — EP-07 est `livré` alors qu'un point de sa définition de fini n'est pas entièrement tenu — déjà connu (#2893, EP-10)

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — #2893 est fermée le 2026-11-16,
  soldée par US-2430 d'EP-10 (« chaque clé de `fixtures/examples.json` du §3.4.5.4 et de WF-REV-0060
  qui n'a pas de test du harnais d'exemples en reçoit un, dont le 4,04 % »), et le 4,04 % est dans
  les tests du harnais.
- **Où** : `EP-07:183-185` (« les exemples chiffrés des Vérif du §3.4.5.4, de WF-PRJ-0040 et de
  WF-REV-0060 … sont des tests qui passent (WF-QUA-0020) ») ; `EP-10:160-161` (#2893 : « des
  exemples chiffrés du §3.4.5.4 et de WF-REV-0060 n'ont pas de test du harnais d'exemples, dont le
  4,04 % de WF-DEV-0050-A »).
- **Quoi** : le statut `livré` dit « sa définition de fini est vérifiée » (`README-fr.md:78`).
- **Proposition** : le correctif est celui de #2893 ; côté roadmap, une phrase à la définition de
  fini d'EP-07 qui nomme l'issue.
- **Confiance** : plausible — je n'ai pas recompté les exemples du harnais contre le §3.4.5.4, je
  m'appuie sur l'énoncé de #2893 dans le fichier d'EP-10.

### RMP-13 — Incohérences documentaires du README et des fichiers livrés

- **Issue** : #4455 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec RMP-08, RMP-09.
- `README-fr.md:27` (et `README.md:27`) : « les 212 exigences » ; la spécification 1.0.6 en compte
  218 hors l'exemple du §1.3.1 (210 F0, 8 F1).
- `README-fr.md:155` et `:157` : EP-21 est listé avant EP-05, dont il dépend (`depend_de: EP-19,
  EP-05`), dans une liste « dans l'ordre où ils se démarrent ».
- `README-fr.md:386-392` : l'exception des branches décrit encore `epic/EP-08` tirée d'`epic/EP-10`
  dès US-1660/L1, alors qu'EP-08 dépend désormais aussi d'EP-27 (`README-fr.md:168`) et vient
  après EP-25, EP-26 et EP-27.
- Titres d'exigence périmés dans les tableaux : `EP-02:92` (WF-INTF-0170-A), `EP-04:86` et
  `EP-05:78` (WF-CYC-0120-A), `EP-05:96` (WF-REF-0010-A), `EP-06:102` et `EP-07:118`
  (WF-INTF-0080-A).
- `EP-06:92` : la ligne de WF-PLA-0150-A nomme US-1430, qui ne cite pas l'exigence (US-1380 porte
  les deux phrases ; le test de l'import existe, `backend/tests/test_msproject_import.py:671`).
- `EP-04:512-514` garde l'alternative « une colonne de `permission` écrite par migration, ou une
  propriété de `predefined.py` », tranchée plus haut (`EP-04:436-437`).
- **Proposition** : une passe de relecture ; le contrôle des titres tient en cinq lignes dans
  `wftools.roadmap`.
- **Confiance** : confirmé.

### RMP-14 — EP-26 annonce clore WF-QUA-0060-A « entière » alors que son Vérif exige des mesures aux volumes d'un jeu qu'EP-13 charge après lui

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la clôture par EP-26 est une
  décision de l'auteur (2026-11-14), redite au cadrage d'EP-13 (2026-11-18), avec l'écart écrit et
  la mesure rejouée par US-2970.
- **Où** : `EP-26:42-43` (« le jeu de données aux trois cents projets (WF-QUA-0040) — EP-13 ») et
  `:49-55` ; `docs/spec/waterfall-spec.md:4608` (« Les mesures sont faites aux volumes du §4.6.2. ») ;
  `README-fr.md:177`.
- **Quoi** : c'est le mécanisme de RMP-02 et de RMP-03, inscrit d'avance dans un EPIC `à planifier` :
  une clôture avec des écarts annoncés (« l'US le dira en écart »).
- **Proposition** : au cadrage d'EP-26, « début — close en EP-13 » (ou EP-11), plutôt qu'`entière`.
- **Confiance** : plausible (EPIC non cadré, la décision peut encore changer).

## Points forts

- **Clôture unique** : chacune des 218 exigences du produit est close par un EPIC et un seul ;
  aucune ligne de tableau ne cite un identifiant inconnu ou une révision dépassée.
- **Mot pour mot** : les 1 628 couples (US, phrase de Vérif) rejoués contre la spécification 1.0.6
  sont tous présents — les deux seuls manques apparents tiennent à US-0670b, sous-US que l'outil du
  dépôt rattache à US-0670. Les écarts des EPIC qui closent sont peu nombreux (26) et tous motivés.
- **Statuts** : aucune US `à faire` ou `en cours` dans un EPIC livré ; les deux US reportées d'EP-02
  (US-0200, US-0290) sont bien reprises par EP-14 et EP-13 ; la liste du README et les 28 front
  matter concordent en statut et en dépendances (hors EP-12, abandonné), et aucun EPIC livré ne
  dépend d'un EPIC non livré.
- **Conception et code** : les tables et migrations des conceptions d'EP-04 à EP-09 sont celles de
  `migrations/versions/0018` à `0028` (partition par projet, `create_project_partitions` remplacée
  par 0022, 0025 et 0026, déclencheurs d'immuabilité sur les neuf tables révisionnées) ; les vingt
  et un registres d'extension annoncés existent (`grep "Registry("`) ; aucun module du noyau
  n'importe les tables d'un autre ; la purge planifiée d'EP-06 est dans les deux Compose.
- **Décisions** : chaque décision lue porte son option écartée et sa raison, et celles qui en
  défont une autre le disent avec leur source (EP-03 « Décisions », EP-05 #2084, EP-24).
- **Tests** : les tests du back portent le nom de la phrase qu'ils éprouvent ; sur une quarantaine
  d'exigences closes relues test par test, seules celles de RMP-03, RMP-05 et RMP-06 manquent de
  preuve. Aucun test `skip`, `fixme` ou `todo` statique ne cite une exigence ; `MISSING` du corpus
  MS Project est vide.
- **Reports** : les issues reportées que j'ai suivies (#763, #1830, #1714, #2229, #2231, #2241,
  #2258, #2527, #2867, #1014, #1035, #859, #2696, #1363, #1369) figurent bien au fichier de l'EPIC
  qui les reçoit.

## Couverture

- **Lu en entier** : `docs/roadmap/README-fr.md`, `MODELE.md` ; front matter et tableaux des 28
  EPIC ; `tools/src/wftools/roadmap.py`, `coverage.py` (pour savoir ce que la chaîne garantit).
- **Lu en entier, sections « Conception »** : EP-04 (`:307-651`), EP-05 (`:240-469`), EP-18,
  EP-24 (`:248-536`). **Lu en partie** : EP-03 (tables, modules, service d'API, décisions ; pas
  l'authentification, le worker, la sauvegarde ni l'amorçage en détail), EP-06 (cadrage, tables,
  modules, points d'extension ; pas les formats, l'historique, la purge ni les « constats des lots
  livrés »), EP-07 (tables, modules, points d'extension, calcul des montants, instantané ; pas le
  cadrage `:267-497`, ni le format Excel), EP-09 (tables, modules, points d'extension, Kanban,
  coûts réels, indicateurs ; pas les décisions des 10 et 11 novembre).
- **Traité par script sur tout le périmètre, pas lu ligne à ligne** : les US (statuts, exigences,
  critères contre le Vérif, écarts, renvois « constaté par », colonne US), les citations d'exigence
  dans `backend/tests`, `frontend/src`, `frontend/e2e`, `tools/tests`, les numéros d'issue des
  « Constats reçus » d'EP-08, EP-10, EP-11, EP-13, EP-25 à EP-28.
- **Échantillonné** : une quarantaine d'exigences closes relues contre la liste de leurs tests ;
  le corps de cinq tests lu.
- **Non lu** : les conceptions des EPIC du front (EP-02, EP-14 à EP-17, EP-22) et de l'outillage
  (EP-01, EP-19, EP-20, EP-21), EP-23 hors ses décisions de report ; le détail des « Constats
  reçus » des EPIC livrés ; l'état des issues sur GitHub (interdit) — un report dit « sans
  porteur » l'est au sens du fichier, non du tableau de suivi. Les défauts de code que des constats
  connus décrivent (#2229, #2875, #3102) n'ont pas été reproduits : ils reviennent aux relecteurs
  des domaines.

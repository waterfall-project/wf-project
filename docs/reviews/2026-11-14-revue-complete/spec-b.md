# Revue — Spécification, FBS-4 Projets, §3.5 et §3.6 (`docs/spec/waterfall-spec.md`, lignes 1905-3416)

## Synthèse

Le texte est mûr : 376 constats ont déjà été rendus et intégrés, et presque tous les exemples
chiffrés tombent juste. J'ai refait chaque calcul des Vérif du périmètre (calendriers, décalages,
chemin critique, inflation, marges, projections, indices, couverture des risques, avancement d'une
récapitulative) : aucun n'est faux. Les Vérif qui portent une règle de calcul du planning et du
chiffrage sont tenus par le code livré — je les ai rejoués sur le moteur de planification et les
fonctions de prix, sans rien écrire dans le dépôt.

Ce qui inquiète tient à quatre trous que le modèle rend possibles et qu'aucune exigence ne règle :
la correction de la référence après un coût réel (exigée par le texte, renvoyée par EP-04 à EP-09,
portée par personne) ; le débours d'une ligne hors main-d'œuvre quand l'année de référence change
(le montant perd une année d'inflation, sans saisie) ; la suppression, en revue, d'une tâche ou
d'une ligne budgétée (la valeur acquise ne peut plus atteindre le budget) ; la liaison portée par
une récapitulative (aucune règle, et une marge négative sans conflit signalé). Le reste est fait
de règles que le contrat a tranchées sans que la spécification les porte (arrondi, code projet,
onglets, phase du reste à engager).

Aucun constat bloquant. 4 majeurs, 12 mineurs.

## Constats bloquants

Aucun.

## Constats majeurs

### SPB-01 — La référence se corrige encore après la réception d'un coût réel

- **Issue** : #4440 (EP-35), ouverte le 2026-11-21, avec BPR-02.
- **Où** : `docs/spec/waterfall-spec.md:1960-1962` (WF-REV-0040) ;
  `backend/src/waterfall/core/revisions/interface/reference.py:77-99` (`reference_correctable`) et
  `:162-170` ; `docs/roadmap/EP-04-projets-et-revisions.md:1326-1334` ;
  `docs/roadmap/EP-08-avenants-et-risques.md:4` et `:64`.
- **Quoi** : le corps exige que la désignation ne se corrige que « tant que le projet n'a reçu
  aucun coût réel et qu'aucune révision n'a été marquée depuis » ; le livré ne juge que la seconde
  condition.
- **Scénario** : offres v2 et v3 marquées ; le chef de projet désigne v2 ; le code projet saisi,
  le projet passe En cours ; un import de coûts réels est appliqué (aucune révision marquée
  entre-temps) ; il désigne v3 : accepté. Le budget de référence, les montants budgétés recopiés
  dans la révision en cours (`estimate/repricing.py:88-114`) et la valeur planifiée se déplacent
  alors que des coûts sont imputés — ce que le Motif veut empêcher.
- **Ce que j'ai vérifié** : `reference_correctable` ne lit que le journal et `Revision.marked_at` ;
  son en-tête dit « The actual costs, which also close it, are EP-09's » ; aucun module de
  `core/costs` ne s'enregistre auprès de la désignation (`grep designat|correctable` vide) ;
  `revision_conditions` (`core/revisions/commands.py:120-130`) n'a pas d'autre condition ; les tests
  (`backend/tests/test_reference_designation.py:388-420`) n'éprouvent que la révision marquée
  depuis. EP-04 renvoie « les coûts réels » à EP-09 ; le fichier d'EP-09 ne cite pas WF-REV-0040 ;
  EP-08, qui la clôt, est « à planifier », sans US en face.
- **Proposition** : que `core/costs` réponde à la désignation (« le projet porte une ligne de
  coût ») par un registre, comme `register_tasks_and_lines` ; test : import appliqué, puis
  `designateReferenceRevision` refusé 409 `reference_correctable`. Dans le texte, dire si une ligne
  exclue du périmètre suivi compte (« reçu aucun coût réel » : toute ligne importée, à mon sens).
  À défaut de le faire maintenant, inscrire la part « coût réel » nommément dans EP-08.
- **Confiance** : confirmé. L'exigence n'est pas déclarée close (EP-08 clôt), mais la part que le
  roadmap attribue à un EPIC livré manque.

### SPB-02 — Au changement d'année de référence, une ligne hors main-d'œuvre perd une année d'inflation

- **Issue** : #3366 (fermée), #3983 (ouverte).
- **Où** : `docs/spec/waterfall-spec.md:1984-1986` (WF-REV-0060), `:2557-2559` (WF-DEV-0030),
  `:2010` (Vérif de WF-REV-0080 : « sur chaque ligne de débours, dont le montant est projeté de
  même ») ; `backend/src/waterfall/core/estimate/keeping.py:191-232` (`copy_rates`),
  `core/estimate/costing.py:176-190` (`priced`) ; `docs/roadmap/EP-24-consolidation-apres-v0-3-0.md:483`.
- **Quoi** : WF-REV-0060 projette le taux horaire conservé jusqu'à la nouvelle année de référence ;
  rien ne dit ce que devient le débours unitaire. Lu avec WF-DEV-0030, il reste tel quel et son
  montant n'est plus projeté que depuis la nouvelle année.
- **Scénario** (inflation 3 %, ligne consommée en 2028) : main-d'œuvre 100 h à 80,00 — révision
  de 2026 : 8 487,20 ; révision créée en 2027, taux projeté 82,40 : 8 487,20, inchangé. Débours
  de 8 000 — révision de 2026 : 8 487,20 ; révision de 2027 : 8 240,00. Rejoué sur
  `pricing.projected_amount`. À la première revue de janvier, le reste à engager de tous les achats
  à venir baisse de 2,9 % sans qu'aucune grandeur ait été saisie, et la marge sur le budget
  (WF-RAE-0020) s'améliore d'autant ; chaque année suivante de même.
- **Ce que j'ai vérifié** : `copy_rates` ne touche pas `unit_disbursement` (aucune écriture du
  champ hors saisie, import et collage) et rappelle `reprice_revision` sur la nouvelle année ;
  EP-24 tient ce comportement pour le Vérif de WF-REV-0080 (« réalisée par le calcul »). Le livré
  suit donc une lecture du texte ; l'autre lecture de « projeté de même » (le débours porté à la
  nouvelle année, comme le taux) laisserait le montant inchangé.
- **Proposition** : trancher dans WF-REV-0060 — « le débours unitaire d'une ligne hors
  main-d'œuvre est, comme un taux conservé, projeté par le taux d'inflation du projet jusqu'à la
  nouvelle année de référence » — et réécrire le Vérif de WF-REV-0080 en conséquence ; ou, si la
  baisse est voulue, l'écrire et la chiffrer dans un Vérif. Test : la ligne de 8 000 ci-dessus
  vaut 8 487,20 dans les deux révisions.
- **Confiance** : confirmé pour le comportement et le calcul ; que ce soit un défaut d'intention
  est un jugement à rendre par l'auteur.

### SPB-03 — Une tâche ou une ligne budgétée se supprime en revue : la valeur acquise ne peut plus atteindre le budget

- **Issue** : #3367 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2710` (WF-RAE-0040 : « créer, déplacer et supprimer des
  tâches … des lignes »), `:2314` (WF-PLA-0070 : seule une tâche démarrée ou terminée résiste),
  `:2984-2986` (WF-IND-0030), `:2581` (WF-DEV-0080) ;
  `backend/src/waterfall/core/planning/interface/nodes.py:803-816` (`delete_node`).
- **Quoi** : aucune exigence ne dit ce que devient le montant budgété d'une ligne supprimée de la
  révision en cours d'un projet En cours ; la référence, marquée, la garde.
- **Scénario** : projet En cours, budget 1 000 ; en revue, le chef de projet supprime depuis la
  grille de reste à engager une tâche non démarrée de 200 (travail abandonné sans avenant). Le
  budget de référence et la valeur planifiée comptent toujours 1 000 ; la tâche n'existe plus, donc
  ne sera jamais terminée : toutes les tâches terminées, la valeur acquise vaut 800, l'avancement
  physique 80 %, l'indice de délai 0,8 pour toujours. Le Vérif « La valeur acquise d'un projet dont
  toutes les tâches sont terminées égale son budget de référence » est faux. Même trou pour une
  ligne budgétée déplacée d'une tâche à une autre : WF-IND-0030 dit « les lignes portées par les
  tâches terminées » sans dire dans quelle révision on lit la tâche (EP-10, ligne 785, lit celle de
  la référence par sa lignée).
- **Ce que j'ai vérifié** : `delete_node` ne refuse que l'état de la tâche et la ligne d'une tâche
  terminée ; aucune garde sur `budgeted_amount` dans `planning/interface/{nodes,lines}.py` ni
  `estimate/writing.py`. Recherché dans les constats passés et dans EP-09, EP-10 : non traité.
- **Proposition** : au choix de l'auteur — refuser hors avenant la suppression d'une tâche ou
  d'une ligne dont le montant budgété n'est pas nul, en renvoyant à la mise à zéro du reste (comme
  WF-PLA-0070 pour une tâche démarrée) ; ou dire que la tâche supprimée cesse de compter à la
  valeur planifiée et au budget « restant à acquérir ». Vérif à ajouter : « la suppression d'une
  tâche non démarrée dont une ligne est budgétée à 200 est refusée et renvoie à … ».
- **Confiance** : confirmé (texte et code). L'effet sur les indices est d'EP-10, non livré ; la
  suppression, elle, est livrée (EP-09).

### SPB-04 — Aucune règle pour une liaison portée par une récapitulative ; une subordonnée manuelle donne une marge négative sans conflit signalé

- **Issue** : #3335 (ouverte), #3368 (fermée), #3984 (ouverte).
- **Où** : `docs/spec/waterfall-spec.md:788-792` (§3.2.4), `:2266` (WF-PLA-0030), `:2254`
  (WF-PLA-0020), `:2422-2424` (WF-PLA-0100) ;
  `backend/src/waterfall/core/planning/scheduling/engine.py:237`, `:281-287`, `:343`.
- **Quoi** : WF-PLA-0030 n'interdit qu'une liaison entre une récapitulative et l'une de ses
  subordonnées ; ce qu'une liaison vers ou depuis une récapitulative impose n'est écrit nulle part.
  Le moteur a tranché seul (« a link to a summary binds each of its subordinates »), y compris
  pour le pourcentage de la durée d'une récapitulative.
- **Scénario** rejoué sur le moteur : A (10 j, automatique) précède fin à début la récapitulative
  S, dont la seule subordonnée M est manuelle et datée avant la fin de A. A porte une marge de
  −8 jours et est critique ; aucun conflit n'est rendu (`conflicts()` ne retient qu'un successeur
  feuille manuel, ligne 343, alors que `backward` borne A par chaque feuille de S, ligne 286). La
  même liaison posée directement sur M rend le conflit. Le lecteur voit une marge négative que
  rien n'explique, contre « porte une marge négative, et le conflit est signalé ».
- **Proposition** : écrire dans WF-PLA-0030 « une liaison dont le successeur est une récapitulative
  s'impose à chacune de ses subordonnées, et une liaison dont elle est le prédécesseur part de ses
  dates calculées » ; dans WF-PLA-0020, étendre le conflit à la subordonnée manuelle d'une
  récapitulative liée ; Vérif : le scénario ci-dessus signale A et M. Dire aussi de quoi se prend
  un décalage en pourcentage quand le prédécesseur est une récapitulative ou porte une durée
  écoulée (`scheduling/units.py:147-156` note que la spécification ne le dit pas).
- **Confiance** : confirmé (exécution du moteur, lecture seule).

## Constats mineurs

### SPB-05 — L'arrondi d'un montant calculé n'est écrit que dans le contrat

- **Issue** : #3369 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:4043` (WF-DAT-0100), `:2557`, `:2569-2571` ;
  `docs/api/DECISIONS.md:11325` ; `core/estimate/pricing/amounts.py:47-55`,
  `core/estimate/keeping.py:104-112`.
- **Quoi** : la spécification veut des montants à deux décimales et ne dit ni le mode d'arrondi, ni
  où il se fait (une fois par ligne, après projection), ni si le taux projeté de WF-REV-0060
  s'arrondit ; seul WF-CRE-0010 le dit, pour l'import. Le générateur du témoin et le back ont
  divergé là-dessus (#2618, #2773, #2806). « La somme de leurs pourcentages vaut cent »
  (`:2527`) dépend de même d'un report du reste que seul le contrat porte.
- **Proposition** : une phrase dans WF-DAT-0100 — « un montant calculé s'arrondit au centime une
  fois, au plus proche, la moitié s'éloignant de zéro ; une somme de parts s'arrondit après la
  somme » — et un exemple (75,705 donne 75,71). **Confiance** : confirmé.

### SPB-06 — Le code projet : ni la barre oblique interdite ni sa longueur ne sont dans WF-PRJ-0010

- **Issue** : #3370 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2075-2077`, `:2863` ; `docs/api/DECISIONS.md:9864-9871` ;
  `core/costs/extraction.py:275`.
- **Quoi** : WF-CRE-0020 fait de la barre oblique le seul séparateur ; un code projet qui en
  porterait une rejetterait toutes ses lignes (`partition` coupe à la première). Le contrat
  l'interdit (`PROJECT_CODE_INVALID`, 1 à 50 caractères), l'exigence non.
- **Proposition** : ajouter au corps « de un à cinquante caractères, sans barre oblique » et au
  Vérif « la saisie du code A/B est refusée ». **Confiance** : confirmé.

### SPB-07 — Le code d'un sous-projet : liste de caractères ambiguë, et des noms d'onglet que la règle ne réserve pas

- **Issue** : #3371 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2151-2153`, `:5002` ;
  `core/projects/interface/subprojects.py:85-87` ; `core/estimate/remaining/excel/layout.py:36-39` ;
  `core/estimate/excel/names.py:21-23`.
- **Quoi** : « sans aucun des caractères : \ / ? * [ ] » ne dit pas si le deux-points est de la
  liste (le livré l'interdit, Excel aussi). Seuls « Synthèse » et « Hors sous-projet » sont
  réservés, alors que le classeur porte aussi « Tâches » et « Paramètres », qu'Excel réserve
  « History » et compare les noms sans égard à la casse.
- **Scénario** vérifié : les codes « Tâches », « Paramètres », « History » sont acceptés
  (`code_faults` vide) et leurs onglets s'appellent « Tâches (2) », « Paramètres (2) »,
  « History (2) » ; « SP1 » et « sp1 » coexistent, le second en « sp1 (2) ». L'import s'y retrouve
  (`tab_subprojects`), mais « nommé par son code » n'est plus vrai.
- **Proposition** : écrire la liste sans ponctuation ambiguë (« aucun des sept caractères
  `: \ / ? * [ ]` »), ajouter « Tâches », « Paramètres » et « History » aux noms refusés, et
  l'unicité sans égard à la casse. **Confiance** : confirmé.

### SPB-08 — La phase du reste à engager et du Kanban n'est pas dite ; l'exception de WF-DEV-0050 est hors d'atteinte

- **Issue** : #3372 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2541-2543`, `:2692`, `:2710` ;
  `docs/api/DECISIONS.md:6700-6704`, `:7944-7946` ; `core/planning/interface/progress.py:12-15`.
- **Quoi** : WF-RAE-0040 ne retire avant En cours que « création et suppression » ; le contrat
  ferme toute saisie du reste et tout geste du Kanban hors En cours. Une tâche de la structure
  principale ne se termine donc qu'En cours, quand la grille de devis est en lecture seule :
  « sauf, dans la structure principale, sous une tâche terminée » et son Vérif ne peuvent pas se
  constater depuis cette grille. La règle utile — pas de ligne créée ni déplacée sous une tâche
  terminée — manque à WF-RAE-0040, où le serveur l'applique (`planning/carrying.py:68`).
- **Proposition** : dire dans WF-RAE-0030 et WF-RAE-0040 que le Kanban et la réestimation ne
  s'ouvrent qu'En cours ; déplacer l'exception et son Vérif de WF-DEV-0050 vers WF-RAE-0040.
  **Confiance** : confirmé.

### SPB-09 — « L'année de consommation » d'une ligne est un scalaire ici, une répartition là

- **Issue** : #3373 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2569` (répartie entre les années) contre `:2133`, `:2509`,
  `:2660`, `:2010` (« son année de consommation ») ; `core/estimate/costing.py:186`.
- **Quoi** : pour une tâche à cheval sur deux années, le texte ne dit pas quelle année est
  « l'année de consommation » qu'il affiche, compare et filtre ; le livré retient l'année de la
  plus grande part, la première à égalité. **Proposition** : l'écrire dans WF-DEV-0040.
  **Confiance** : confirmé.

### SPB-10 — Une tâche sans aucune heure travaillée entre ses dates, qui n'est pas un jalon

- **Issue** : #3374 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2254` (une date importée sur un jour non travaillé est
  gardée), `:2569`, `:2581` ; `core/estimate/spreading/spread.py:116-118`, `planned.py:60-63`.
- **Quoi** : une tâche manuelle importée de MS Project sur un samedi et un dimanche ne compte
  aucune heure : le prorata de WF-DEV-0040 et de WF-DEV-0080 divise par zéro. Le texte ne règle
  que le jalon ; le livré porte la ligne entière à la fin de la tâche.
  **Proposition** : l'ajouter aux deux exigences. **Confiance** : confirmé.

### SPB-11 — Une avance peut placer une tâche avant la date de début de planning

- **Issue** : #3375 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2254`, `:2266`, `:2350` ; `scheduling/engine.py:228-252`.
- **Quoi** : un décalage négatif plus long que ce qui précède fait commencer le successeur avant la
  date de début de planning (rejoué : prédécesseur d'un jour, avance de cinq jours, successeur six
  jours avant). Le texte ne dit ni si c'est admis ni d'où se compte alors l'horizon de quinze ans.
  **Proposition** : une phrase dans WF-PLA-0020 (MS Project l'admet). **Confiance** : confirmé.

### SPB-12 — La marge d'une révision marquée mêle son reste à engager et le coût réel du jour

- **Issue** : #4457 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `docs/spec/waterfall-spec.md:2676-2678` (WF-RAE-0020), `:2960` (WF-IND-0010) ;
  `core/estimate/interface/remaining_indicators.py:219-221` ; `core/costs/interface/tracked_costs.py:43-54`.
- **Quoi** : WF-RAE-0020 ne dit pas à quelle date se lit le coût réel d'une révision marquée
  (WF-IND-0010 ne vaut que pour FBS-4.8). Le livré additionne tous les coûts suivis à ce jour au
  reste de la révision marquée : relue six mois plus tard, sa marge compte deux fois la dépense
  faite depuis. **Proposition** : renvoyer WF-RAE-0020 à WF-IND-0010. **Confiance** : confirmé —
  déjà prévu : EP-10 (US-1670, `docs/roadmap/EP-10-indicateurs.md:466`) fera lire le document
  conservé.

### SPB-13 — Lignes de provision : trois phrases en retard (non encore réalisé, EP-08)

- **Issue** : #3376 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2692` (« un jalon qui ne porte aucune ligne ») contre
  `:2302` (« aucune ligne hors lignes de provision ») ; `:2710` (« toutes les lignes d'une tâche »)
  contre `:2290` ; `:2662` (« lignes des tâches non terminées, lignes de provision … comprises »)
  contre le corps, qui compte la provision quel que soit l'état de sa tâche.
- **Quoi** : résidu de C-302. **Proposition** : écrire partout « hors lignes de provision », et
  dans le Vérif de WF-RAE-0010 « plus les provisions des risques identifiés, quel que soit l'état
  de la tâche qui les porte ». **Confiance** : confirmé (texte).

### SPB-14 — Survenance : une récapitulative sans prédécesseur « passe en mode manuel » (non encore réalisé, EP-08)

- **Issue** : #3377 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:2831` contre `:2290` (« Une tâche récapitulative est
  toujours en mode automatique »). **Proposition** : « une tâche feuille sans prédécesseur ».
  **Confiance** : confirmé (texte).

### SPB-15 — « Translatée de 60 jours » sur une courbe au pas du mois (non encore réalisé, EP-10)

- **Issue** : #3378 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:3104-3106`. **Quoi** : les courbes portent un point par fin
  de mois ; soixante jours ne font pas un nombre entier de mois (un montant du 31 janvier glisse
  de trois points, un du 1er janvier de deux) : le Vérif ne peut pas être constaté tel quel.
  **Proposition** : « chaque montant est compté au mois de sa date décalée de 60 jours ».
  **Confiance** : confirmé (calcul) ; voisin de C-279 et du point 5 de C-287, non identique.

### SPB-16 — Le Vérif de WF-IHM-0100 ne constate que trois des « quatre points exigés »

- **Issue** : #3379 (fermée).
- **Où** : `docs/spec/waterfall-spec.md:3364-3366`. **Quoi** : le libellé associé à chaque champ et
  la description de chaque image porteuse d'information ne sont pas vérifiés.
  **Proposition** : ajouter « un contrôle automatisé ne relève aucun champ sans libellé ni image
  informative sans description ». **Confiance** : confirmé (texte).

## Points forts

- Tous les exemples chiffrés du périmètre sont justes : 1,0609 et 4,04 % ; −50 et −50 du reste à
  engager ; 50 % et 70 % ; 1 100, 1 050 et 1 250 ; 0,8 et −100 ; 50 % puis 75 % d'une
  récapitulative ; les neuf valeurs de la couverture des risques (60, −190, −150, −30, 110…) ;
  180 révisions ; pente 1 du temps/temps.
- Le moteur livré tient les Vérif du planning à l'exécution : 16 h finissent le mardi (8 h/jour)
  et le jeudi (4 h/jour) ; 2 ej et 2 eh depuis un vendredi soir donnent le lundi, 2 j le
  mercredi ; deux branches de 10 j et 4 j donnent une marge de 6 ; l'horizon refuse au-delà de
  quinze ans jour pour jour.
- Le chiffrage tient les siens : part d'une année antérieure non projetée
  (`pricing/amounts.py:92-103`), somme des parts égale au total (`spreading/spread.py`), jalon
  compté entier à sa date (`spreading/planned.py:55-65`), parts qui somment à un (`shares.py`),
  arrondi d'un coût réel au plus loin de zéro et élément d'OTP (`costs/extraction.py:265-331`).
- Les exigences disent presque toujours le cas limite (récapitulative qui perd sa dernière
  subordonnée, jalon rouvert, risque écarté qui revient), et le Motif explique la règle.

## Couverture

- **Lu en entier** : `docs/spec/waterfall-spec.md` lignes 1905-3416 ; `docs/spec/revue/PROMPT.md` ;
  les titres des constats C-091 à C-376 (`docs/spec/revue/constats/`), sans relire leur corps ni
  refaire le suivi de leurs statuts.
- **Cherché hors périmètre** (par `grep`, sans relecture) : §3.2.4, WF-CYC-0020/0030, WF-DAT-0100,
  annexe B.
- **Code lu** : `core/planning/scheduling/` (units, calendar, links, engine, structure) en entier ;
  `core/estimate/pricing/amounts.py`, `spreading/`, `shares.py`, `costing.py`, `valuing.py`,
  `repricing.py`, `remaining/{summing,balancing,comparing}.py` en entier ;
  `core/revisions/interface/reference.py` en entier. **Échantillonné** : `estimate/keeping.py`
  (taux), `workloading.py`, `interface/remaining_indicators.py`, `remaining/excel/layout.py`,
  `excel/names.py`, `costs/extraction.py` et `applying.py`, `projects/interface/subprojects.py`,
  `planning/interface/{progress,nodes}.py` (en-têtes), `planning/shaping.py` (en-tête).
- **Exigences sondées contre le livré** (23) : tiennent leur Vérif — WF-PLA-0010, 0020 (liaison
  directe), 0030, 0070, 0100 (hors SPB-04), 0150, 0160, WF-DEV-0010, 0030, 0040, 0060, 0070 (jour
  pris en UTC : déjà connu, #2527, EP-13), 0080, WF-RAE-0010 (hors provisions, EP-08), 0020
  (révision en cours), WF-CRE-0010, 0020, 0030, WF-REV-0060 (taux), WF-PRJ-0050 ; lues sur leur
  seul en-tête de module — WF-PLA-0040, WF-RAE-0030/0040 ; ne tient pas — WF-REV-0040 (SPB-01).
- **Non lu** : `core/exchanges`, les imports et exports MS Project et Excel dans le détail, les
  tests (hors deux `grep`), le contrat `docs/api/*.yaml` (lu seulement par `DECISIONS.md`), le
  front. Les exigences des avenants, des risques, des indicateurs et de la comparaison dans les
  grilles (EP-08, EP-10, EP-27) n'ont été relues que comme texte.

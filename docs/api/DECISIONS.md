# Décisions prises en écrivant le contrat

Ce que la spécification ne dictait pas et qu'il a fallu trancher pour écrire un contrat
cohérent. Chaque décision est réversible, mais aucune ne se change sans toucher plusieurs
dizaines d'opérations : c'est pourquoi elles sont écrites ici plutôt que découvertes.

## Forme des chemins

**Un état est une ressource, pas un verbe.** `PUT /users/{id}/activation`,
`PUT /projects/{id}/reference-revision`, `PUT .../actual-costs/{id}/tracked-scope` plutôt
que `/deactivate`, `/designate`, `/exclude`. Un `PUT` idempotent porte la valeur visée, ce
qui rend l'opération rejouable sans effet de bord — utile pour un client qui réessaie.
Trois exceptions assumées, où l'action n'est pas un état : `POST .../mark`,
`POST .../merge`, `POST .../occurrence`. Elles sont irréversibles et méritent un verbe.

**Les chemins sont profonds et imbriqués par projet.** `/projects/{p}/revisions/{r}/`
`structures/{s}/nodes/{n}/estimate-line` n'est pas court, mais un nœud n'a aucun sens hors
de sa structure, ni une structure hors de sa révision. L'imbrication rend aussi la
partition par projet évidente à la lecture (WF-DAT-0050), et interdit par construction
qu'une requête traverse deux projets.

**Le préfixe de version est dans le serveur, pas dans les chemins.** `/api/v1` est déclaré
une fois ; les chemins n'en portent pas la trace, de sorte qu'un changement de préfixe ne
réécrive pas cent seize chemins. L'ancien contrat versionnait une seule famille,
`/imports/v1`, ce qui promettait une indépendance qui n'existait pas.

## Arbre commun

**Une seule collection de nœuds, deux facettes.** Le nœud porte `kind: task |
estimate_line` et l'une des deux facettes. C'est l'idée la plus juste de l'ancien contrat,
et elle réalise directement l'arbre commun du §3.5.1 : deux collections auraient dupliqué
l'arbre, et il aurait fallu les tenir d'accord.

**La tâche porteuse est résolue à la lecture**, comme dans l'ancien contrat. Déplacer une
ligne, ou la tâche au-dessus d'elle, change sa tâche porteuse sans rien d'autre à mettre à
jour.

**Les structures de coûts apparaissent dans le chemin.** Une révision porte une structure
principale et, le cas échéant, des différentiels et des devis de risque : les nœuds vivent
donc sous une structure. Cette règle n'était que dans le glossaire quand le contrat a été
écrit ; elle est depuis portée par WF-REV-0100 (constat C-083, intégré).

## Calculé contre saisi

**Deux schémas par facette : un de lecture, un d'écriture.** `TaskFacet` porte les dates
calculées, la marge, la criticité, l'avancement physique ; `TaskFacetWrite` ne porte que ce
qui se saisit. Même chose pour la ligne de devis, dont les deux montants sont en lecture
seule. C'est la traduction de WF-IHM-0030 dans le contrat : le front ne peut pas envoyer
une valeur calculée, il n'a pas de champ pour le faire.

**Pas d'endpoint de chemin critique.** `is_critical` et `total_float_days` sont des
attributs calculés de la tâche. Un endpoint séparé aurait imposé une seconde lecture pour
afficher une grille.

**Une enveloppe `Computable` pour ce qui peut ne pas se calculer.** WF-IND-0010 interdit de
présenter zéro ou l'infini : le contrat rend `{ is_computable, value, reason }` partout où
un dénominateur peut être nul. C'est verbeux et c'est le prix de l'exigence.

**Le motif d'une valeur non calculable est un code** (`NotComputableReason`, EP-02/L4, #137).
`reason` était une phrase libre, écrite dans une langue quelle que soit celle du lecteur : la
dernière phrase d'une réponse, quand le contrat avait partout ailleurs remplacé la phrase par un
code (`ErrorCode`, `CommandCondition`, WF-ARC-0110). Un code par grandeur nulle au dénominateur,
relevé sur les indicateurs du §3.4.5.8 et sur les autres `Computable` du contrat : coût réel
(indice de coût, et projection au rythme constaté tant qu'il ne se calcule pas), valeur acquise
(la même projection quand l'indice de coût est nul), valeur planifiée, budget de référence,
montant budgété du sous-arbre d'une récapitulative, coût réel et reste à engager, capacité d'un
rôle, offre sortie de l'état Chiffrage sur la période. L'avancement physique d'une
récapitulative, qui n'était qu'un pourcentage nullable, devient pour cela un `Computable` : il
peut dire qu'il n'est pas calculable, et pourquoi (WF-IND-0060, WF-IND-0010).

**Chaque nœud dit lesquels de ses champs sont calculés** (`computed_fields`, EP-02). Le
schéma d'écriture ne suffit pas à la ligne : une date de tâche se saisit en mode manuel et
se calcule en mode automatique, la durée d'une récapitulative dérive de ses subordonnées,
les grandeurs d'une ligne de provision viennent du risque. Le serveur le sait ; le front,
s'il devait le déduire du mode ou de la nature du nœud, recopierait une règle du noyau.
Pour la même raison, une ligne de devis dit si elle accepte une réestimation au reste à
engager (`remaining_entry`) : sous une tâche terminée, elle ne l'accepte plus.

**Ce dont dépend une valeur calculée se lit à la demande** (`getComputedValueDependencies`,
EP-02/L4, #168). WF-IHM-0030 veut qu'une tentative de saisie sur une valeur calculée soit
refusée en nommant ce dont elle dépend. L'opération prend le nœud et le champ tenté, et rend
les règles qui calculent la valeur (`ComputedDependency`, dans l'ordre où les dire) et les
lignes dont elle est tirée, nommées par leur numéro et leur libellé — toutes, que la recherche
ou les filtres de la grille les retiennent ou non. Elle n'est appelée qu'au refus, qui est
rare : `listNodes` ne s'alourdit pas. Un champ que le serveur ne calcule pas pour ce nœud est
refusé par `VALIDATION_FAILED`, `params.field` le nommant. Écartés : une table champ → dépendance dans
`computed_fields`, qui pèserait sur chaque nœud et laisserait sans nom les subordonnées hors
filtre ; un paramètre `depends_on` sur le seul refus d'une écriture, qui laisserait la grille
recopier les règles pour refuser avant d'écrire. Les subordonnées que nomme
`subordinate_node_ids` (`SUMMARY_TASK_DERIVED`) sont les subordonnées directes.

## Traitements longs

**Neuf opérations renvoient une tâche de fond, jamais un résultat** : marquage, fusion d'un
différentiel, survenance d'un risque, analyse et application d'un import, export,
sauvegarde, restauration, synchronisation de l'annuaire. Chacune a son genre dans
`BackgroundTaskRef.kind` — la fusion et la survenance n'y figuraient pas, et leur suivi
n'aurait pas su dire ce qu'il suivait (EP-02). Toutes répondent `202` avec une
référence de tâche, et le front suit l'avancement par `GET /tasks/{id}` (WF-ARC-0090,
WF-IHM-0080). Conséquence à assumer dans la maquette : aucun de ces gestes n'a de réponse
immédiate.

**Les tâches de l'appelant se listent** (`listBackgroundTasks`, `GET /tasks`, EP-02/L4, #146).
Une tâche ne se relisait que par son `task_id`, que seul l'onglet qui l'avait lancée
connaissait : un autre onglet, un autre poste ne savaient rien d'un marquage en cours. La liste
rend les tâches de l'appelant, celles qui courent et celles finies depuis une date, les plus
récentes d'abord, paginées ; `BackgroundTaskStatus` est nommé pour la filtrer. Elle ne dit pas
quelle commande a lancé une tâche : une tâche qu'elle fait trouver se relance depuis l'écran de
son objet. Écartés : une liste par objet, qui élargirait le contrat et poserait la question des
habilitations ; attendre EP-04. Une tâche qu'un collègue a lancée sur le même objet se dit par
les commandes qu'elle rend caduques, ci-dessous.

**Une commande qu'un traitement de fond rendrait caduque le dit** (`no_background_task_running`,
EP-02/L4, #147). Pendant un marquage, la révision relue listait `mark` disponible : un second
marquage partait, et n'apprenait qu'au refus 409 que le premier courait. Le serveur nomme la
condition dans `missing_conditions` des commandes concernées, quel que soit l'utilisateur qui
a lancé le traitement.

## Session et erreurs

**Témoin de session `httpOnly`, pas de jeton Bearer.** La session est conservée en base et
révocable immédiatement (WF-SEC-0020, constat C-074 de la revue du §4) : un témoin
correspond à ce modèle, et il évite de faire circuler un jeton dans des en-têtes que du
code client pourrait stocker.

**Les permissions effectives sont renvoyées avec la session.** Sans elles, le front ne peut
pas tenir WF-IHM-0090, qui distingue une commande indisponible d'une commande absente.
Aucune exigence ne l'impose — voir C-087. Elles règlent la navigation : une fonction dont
l'utilisateur n'a pas la consultation ne s'y présente pas.

**Le catalogue des permissions est une énumération** (EP-02). WF-ADM-0100 le dit livré et
non modifiable : deux permissions par fonction de second niveau — vingt-quatre fonctions —,
et six pour les actions irréversibles ou structurantes. Un motif de chaîne laissait le front
ignorer quels codes existent ; l'énumération fait d'une permission nouvelle une
modification du contrat, ce qu'elle est.

**Le projet et la révision portent leurs commandes disponibles** (`available_commands`,
EP-02). Chacune dit si elle est disponible et, sinon, les conditions qui lui manquent,
nommées par un catalogue (`CommandCondition`) que le front rend en phrase. Le serveur ne
liste que les commandes que l'appelant a la permission d'exercer : une commande absente de
la liste n'est pas présentée, et le front n'a pas à savoir quelle permission garde quelle
commande — ce serait une règle recopiée. Les autres fonctions — comptes, rôles,
référentiel, sauvegarde — n'ont pas de conditions à nommer : leurs commandes suivent la
permission de modification de la fonction, que la session porte, et la restauration sa
permission propre ; c'est la règle même du catalogue. La saisie d'une révision est trois commandes —
planning, devis, reste à engager —, parce que trois permissions la gardent : un chiffreur
peut saisir le devis sans pouvoir toucher au planning. Les risques et les coûts réels ont
leurs commandes sur le projet ; une commande que refuse l'état d'un objet particulier — un
risque déjà survenu — l'est par son code d'erreur. `getProjectNextState` ne couvrait que les
transitions d'avant En cours ; la terminaison d'un projet en chiffrage, par exemple, n'avait
pas de condition à nommer. La consultation « prochain état » garde sa forme, et ses
conditions viennent du même catalogue.

**Les codes d'erreur sont un catalogue énuméré** (`ErrorCode`, EP-02). `Problem.code`
promettait un catalogue qui n'existait pas. Il couvre les refus de l'API, les motifs par
champ, et les motifs de rejet d'une ligne collée ou importée : ce sont les mêmes phrases à
rendre, et un seul catalogue de textes les rend. Le front n'en rencontre aucun qu'il ne
sache dire ; un code nouveau est une modification du contrat.

**Une seule enveloppe d'erreur, sans phrase.** `code`, `status`, `params`, `fields`,
`correlation_id`. Pas de champ de message : WF-ARC-0110 veut que le texte soit rendu par le
front. `params` porte la condition manquante, ce que WF-ADM-0110 exige, et
`correlation_id` est celui des journaux (WF-OBS-0020).

**404 contre 403, et la règle est dans les réponses partagées.** Pas de permission de
consultation, l'objet n'existe pas pour l'appelant ; permission de lecture mais pas
d'écriture, ou pas contributeur, c'est 403 avec la condition nommée.

**`412` pour un `lock_version` périmé**, distinct du `409` d'un conflit d'état. Le front
peut ainsi proposer de recharger dans un cas et d'expliquer dans l'autre.

**Chaque signalement porte sa zone** (`AlertZone`, EP-02/L4, #139). WF-IHM-0070 veut une
échelle commune, et une zone que le serveur classe : le dépassement du budget d'un sous-projet
(`SubprojectBalance.zone`) et les signaux de santé du pilotage (`PilotHealth.signals[].zone`)
n'en avaient pas, et un écran aurait dû choisir entre vigilance et alerte — deux écrans
auraient pu choisir différemment.

## Langue et thème

**Le compte n'a qu'un champ de langue, sa préférence à trois états** — `default`, `fr`,
`en` (EP-02). `default` suit le navigateur, puis la langue par défaut de l'installation ;
un choix explicite prime (WF-INTF-0160). Le front la résout à chaque requête — la langue
par défaut lui vient de `getInstallation`, lisible sans session pour la page de
connexion —, et l'API ne localise rien (WF-ARC-0110) : `Session.language` et `User.language`, qui la répétaient sans
dire laquelle faisait foi, sont retirés. Le thème suit la même forme — `default`, `light`,
`dark`, où `default` suit le poste —, préférence de présentation (WF-ADM-0040).

## Listes et grilles

**Le serveur trie, filtre et totalise ; le front n'ordonne ni ne somme rien** (EP-02). Chaque
grille demande son tri par `sort_by` et `sort_order`, ses filtres par des paramètres nommés,
et la réponse porte les totaux du périmètre retenu. Trier dans le front aurait exigé
l'exception à la règle « le front ne réordonne pas ce que le back ordonne », et laissé les
totaux mentir sous un filtre. Dans l'arbre, le tri ordonne les frères sans défaire l'arbre,
et un filtre rend aussi les ancêtres des nœuds retenus. Le montant d'une récapitulative —
la somme de ce qu'elle porte et de ses subordonnées (WF-DEV-0050) — est de même rendu par
la facette tâche. La préférence de tri d'une grille garde la forme de la requête, une
colonne et un sens, pour être renvoyée telle quelle.

**`listNodes` rend la structure entière, sans pagination** (EP-02). Une révision porte au
plus dix mille objets (§4.6.2), et un arbre ne se lit pas par pages : une page coupe une
tâche de ses lignes. La grille virtualise l'affichage, pas la lecture.

**Une lecture de `listNodes` choisit les champs qu'elle rend** (`fields`, EP-02/L4, #166). Six
mille nœuds entiers pèsent quatre mégaoctets, dont la moitié en noms de clés et en identifiants
qu'aucune grille n'affiche ; la seconde du §4.6.2 ne tenait qu'à la marge. `fields` nomme les
propriétés de `Node` à rendre, et celles d'une facette sous son nom (`task.label`) ; `node_id`,
`row_number`, `level` et `lock_version` sont toujours rendus. Les schémas décrivent le nœud
entier, que rend une lecture sans `fields` : leurs propriétés exigées ne le sont pas d'une
lecture qui en nomme — c'est la seule réponse du contrat dont le schéma ne dit pas tout, et la
vérification des réponses du service (WF-ARC-0060) devra le savoir. Un nom est une propriété
et non une énumération : il n'a pas de phrase à rendre, et une propriété nouvelle de `Node` le
devient sans toucher au paramètre. Écartés : des vues nommées, qui feraient épouser les écrans
au contrat ; ne rien changer, qui laisserait le back lourd.

**`row_number` numérote toute la structure** (EP-02/L4, #158) : ses tâches et ses lignes, dans
l'ordre du plan, quels que soient `kinds`, les filtres, la recherche et le tri. Une liaison
nomme ainsi son prédécesseur par son numéro (`predecessor_row_number`), même quand la lecture
ne le rend pas, ce que la grille de planning ne pouvait plus faire sous une recherche ; son
décalage garde son unité (`lag`, `lag_unit` : jours, semaines ou mois, WF-PLA-0030), où
`lag_days` convertissait une semaine importée en cinq jours. L'écriture des liaisons
(`PredecessorWrite`) ne porte pas le numéro, que le serveur calcule.

**L'accueil filtre sur la qualité de contributeur** (`is_contributor` de `listProjects`,
EP-02). C'est un filtre que l'utilisateur voit et lève, jamais une restriction de lecture :
la consultation ne dépend que des habilitations (WF-PRJ-0060).

## Révision de la spécification du 2026-10-03 (EP-02/L7)

Ce que la spécification revue impose, et la forme retenue pour chaque chose (#213).

**Une durée est un objet, dans l'unité de sa saisie** (`Duration { value, unit }`,
`DurationUnit`, WF-PLA-0160). `duration_days` convertissait en jours ce que l'utilisateur
avait saisi en semaines ou en mois, et ne savait pas dire un temps écoulé. `value` est un
`Decimal` du contrat, comme `Hours` : MS Project accepte « 2,5 j », et un flottant est
interdit (WF-DAT-0100). `unit` est un code court, celui du suffixe de MS Project en anglais
(`d`, `w`, `mo`, `ed`…), que le front rend par le suffixe de la langue du lecteur
(`j`, `sem`, `m`, `ej`…). Le décalage d'une liaison a la même forme (`Lag`, `LagUnit`), avec
une unité de plus, `percent`, que seule une liaison accepte (WF-PLA-0030) : deux énumérations
nommées plutôt qu'une seule restreinte par facette, pour que chacune ait ses clés de
catalogue et que le typage refuse un pourcentage sur une tâche. `lag` et `lag_unit` sont
remplacés par `lag`. Les constantes de conversion sont une ressource du référentiel,
`GET`/`PUT /reference/duration-units` (`DurationUnits`, 8, 40, 20 par défaut), sous la
permission des paramètres de ressources comme les calendriers, et lisibles par quiconque
consulte un projet : un paramètre de l'installation, pas du projet.

**Le début et la fin d'une tâche sont un instant de travail** (`WorkInstant { date, hours }`,
WF-DAT-0100) : la date sans heure et les heures de travail écoulées ce jour-là, sans fuseau
— deux tâches de quatre heures liées fin à début finissent le même jour. `start_date` et
`finish_date` deviennent `start` et `finish`, sur la facette, dans `computed_fields`, dans
`ComputedValueField` et dans le tri de `listNodes`. Les dates des gestes (`started_on`,
`completed_on`), des pièces et des courbes restent des dates. `hours` est un `Hours`, décimal
exact : un calendrier de sept heures et demie existe.

**Les permissions distinguent le chef de projet** (WF-PRJ-0060, WF-ADM-0100, WF-ADM-0110).
`all_projects_read` entre au catalogue, de nature `structuring` — une quatrième nature de
`Permission.kind`, car consulter n'est pas irréversible — et ouvre à la consultation les projets
dont l'utilisateur n'est pas contributeur. `Contributor.kind` dit la qualité, `project_manager`
ou `contributor` (`ContributorKind`), en lecture comme en écriture : `ContributorsWrite` porte
désormais des `{ user_id, kind }`, et non des identifiants nus. La condition
`is_project_manager` et le code `NOT_PROJECT_MANAGER` nomment le refus d'une action structurante
ou du paramétrage à qui n'est que contributeur, comme `is_contributor` et `NOT_CONTRIBUTOR` le
font pour la saisie. `listProjects`, filtre levé, ne rend que les projets que l'appelant peut
ouvrir ; le refus d'une consultation reste un 404.

**Toute liste se filtre sur ce que son écran présente** (WF-IHM-0130). Les listes qui n'avaient
que la recherche gagnent les filtres que la spécification nomme pour leur grille : l'état des
révisions, la qualité des contributeurs, l'origine et le rattachement des comptes, le type
des natures de coût, la nature des catégories, la zone des risques et des projets du
portefeuille, la recherche sur les objets du référentiel, les rôles d'habilitation et les
sous-projets ; la liste du portefeuille gagne son tri. Les totaux suivent les filtres, et
`meta.total` compte ce qui est retenu. Le filtre de `listNodes` sur l'état des tâches reste
`progress` — nommé comme la propriété qu'il filtre et la colonne qu'il trie —, ce que
WF-PLA-0080 et WF-RAE-0040 demandent sous le nom d'état. Les journaux (imports, imports de
coûts, sauvegardes, réexamens) restent sans filtre : la spécification n'en nomme aucun pour
eux, et un filtre viendra avec l'écran qui le demande.

**Les décaissements sont la courbe de coûts cumulés, décalée** (WF-IND-0100 ; WF-IND-0120
retirée). `getProjectCashOut` et `CashOut` disparaissent : `getCostCurve` prend
`payment_delays`, qui décale chaque montant du délai de paiement de sa ligne et ajoute les
provisions des risques identifiés, et la réponse le dit (`payment_delays`) et détaille alors les
mois (`cash_out_by_month`, nul sinon). Le mois de décaissement est un schéma partagé
(`CashOutMonth`), que le décaissement du portefeuille réemploie (WF-PTF-0100) : le portefeuille
somme ce que les projets rendent.

**L'évolution des indices est une lecture** (`getIndexHistory`, WF-IND-0130). Par maille — le
projet, chaque sous-projet, « hors sous-projet » (WF-IND-0020) —, un point par révision
marquée, à sa date de marquage (`at`, un horodatage comme `marked_at`), avec les deux indices
que le marquage a conservés (WF-DAT-0040), et le dernier point au jour courant pour la
révision en cours, dont `version_name` est nul ; les seuils du référentiel sont rendus avec
(`IndexThresholds`), pour être tracés. Un indice non calculable à un marquage est un point non
calculable, jamais omis : chaque courbe garde un point par révision.

**Le motif d'une sortie se relit** (`StateTransition.reason`, WF-CYC-0090, WF-CYC-0130, #185) :
nul pour une transition automatique ou une sortie confirmée sans motif ; l'exemple `exited`
montre une offre perdue avec le sien.

**La grille de devis lit le montant corrigé de l'inflation** (`inflated_amount`, WF-DEV-0050,
WF-DEV-0040) : calculé, il entre dans `ComputedValueField`, et `inflation` dans
`ComputedDependency` dit d'où il vient. `budgeted_amount` et `reestimated_amount` restent des
attributs de la ligne, que la grille de reste à engager lit (WF-RAE-0040).

**Le plan de charge nomme sa base** (`basis` : `reference_budget`, `marked_remaining` avec
`revision_id`, `current_remaining`, WF-DEV-0070). Sur un projet sans révision de référence,
seule la révision en cours est une base : les deux autres sont refusées par 409.

**La tâche dit si sa fin est dépassée** (`finish_overdue`, WF-RAE-0040, WF-PLA-0080), et **la
ligne si elle emploie un objet désactivé** (`uses_inactive_object`, WF-REF-0010) : deux
booléens calculés, que les grilles signalent sans recopier la règle — la date de calcul, le
référentiel.

**La survenance d'un risque répartit la provision** (WF-RIS-0060) : les descriptions de
`declareRiskOccurrence` et de `RiskOccurrence` disent la part de chaque ligne fusionnée, et
l'exemple `risk_occurred` de `listNodes` montre la structure obtenue — 36 et 24 pour 120 et 80 à
30 %, la ligne de provision retirée.

**La liste des projets du portefeuille porte l'écart à la référence** (`delta_to_reference`,
WF-PTF-0040), nul hors d'un projet en cours. La projection du chef de projet que la même
exigence nomme est `project_manager_projection`, qui existait : un second champ l'aurait
répétée.

**Sans surface** : WF-IHM-0120, l'accueil, est le filtre `is_contributor` existant ; WF-CMP-0030
et WF-QUA-0080 relèvent du déploiement et de la chaîne.

## Collage et annulation

**Le collage depuis un tableur suit exactement la forme d'un import** : `paste-preview`
rend un plan avec les lignes acceptées et rejetées, `paste` l'applique sur confirmation.
WF-IHM-0050 demande le même contrôle avant écriture que WF-INTF-0080 ; autant la même
forme.

**Un bloc plus large que la grille est refusé à l'aperçu**, par un 422 `PASTE_TOO_WIDE` dont
`params.max_columns` dit combien de colonnes la grille offre à partir de la colonne visée
(EP-02, US-0130). Le code et son paramètre existaient sans qu'aucune réponse de `previewPaste`
ne les déclare : WF-IHM-0050 veut que ce refus se dise, avant que rien ne soit écrit. Tant que
l'aperçu ne transmet pas les colonnes que remplit le bloc (#200), le serveur ne connaît ni les
colonnes affichées ni leur ordre : `max_columns` ne peut valoir que pour les colonnes du contrat
à partir de la colonne visée, et le front garde une garde locale sur ce qu'il montre.

**L'annulation est une opération de la révision**, `POST .../undo` et `POST .../redo`, pas
un état du client. C'est ce qui rend vraie la phrase de WF-IHM-0110 : une annulation est
une modification comme une autre, qui passe par l'API et s'inscrit dans l'audit.

## Organisation des fichiers

**Les schémas sont groupés par famille**, douze fichiers, et non un fichier par schéma —
l'ancien contrat en avait cent quatre-vingt-un. Cent quarante-sept fichiers d'une douzaine
de lignes se relisent moins bien qu'une douzaine de fichiers cohérents, et les schémas
d'une même famille se citent entre eux.

**Le lotissement s'écrit d'un coup**, `PUT /projects/{id}/work-breakdown` sur l'arbre
entier, plutôt que trois familles de CRUD pour les postes, les lots et les livrables. C'est
un petit arbre saisi en une fois, jamais modifié ligne à ligne.

## Vocabulaire

Les noms du tableau de correspondance du §4.4.1 font loi, et deux d'entre eux corrigent
l'ancien contrat : `estimate_line` est une ligne de devis, `cost_line` une ligne de coût
réel. L'ancien contrat appelait `cost-lines` les lignes de devis, ce qui aurait donné deux
sens au même mot le jour où les coûts réels arrivent. De même, `org_node` pour
l'organisation, réservé face aux nœuds de l'arbre commun.

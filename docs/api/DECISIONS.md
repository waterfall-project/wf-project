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

**Pas d'endpoint de chemin critique.** `is_critical` et `total_float` sont des
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
commande — ce serait une règle recopiée. Une exception, décidée par l'utilisateur le
2026-10-05 : sans révision en cours, un import que l'appelant a la permission d'exercer mais
qui créerait une révision qu'il n'a pas la permission de créer est listé indisponible, la
condition `may_create_revision` manquante (EP-02/L17). Les autres fonctions — comptes, rôles,
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
font pour la saisie ; `LAST_PROJECT_MANAGER` (409) refuse une liste de contributeurs qui ne
garderait aucun chef de projet, sur le modèle de `LAST_ADMINISTRATOR`, et un compte inconnu ou
désactivé est refusé par 422. `listProjects`, filtre levé, ne rend que les projets que
l'appelant peut ouvrir ; le refus d'une consultation reste un 404.

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
l'exemple `nodes_risk_occurred` de `listNodes` montre la structure obtenue — 36 et 24 pour 120
et 80 à 30 %, la ligne de provision retirée.

**La liste des projets du portefeuille porte l'écart à la référence** (`delta_to_reference`,
WF-PTF-0040), nul hors d'un projet en cours. La projection du chef de projet que la même
exigence nomme est `project_manager_projection`, qui existait : un second champ l'aurait
répétée.

**Sans surface** : WF-IHM-0120, l'accueil, est le filtre `is_contributor` existant ; WF-CMP-0030
et WF-QUA-0080 relèvent du déploiement et de la chaîne.

## Constats du contrat, second passage (EP-02/L8)

Les constats que les écrans d'EP-02 ont relevés après EP-02/L4, corrigés avec les décisions prises
avec l'utilisateur le 2026-10-03 (#214), et la forme retenue pour chacun.

**Un `PATCH` de cellule ne porte que ce qui change** (`TaskFacetUpdate`, `EstimateLineUpdate`,
#178). WF-IHM-0040 veut que chaque cellule se valide seule ; les schémas d'écriture exigeaient le
libellé, la catégorie et la quantité d'une ligne à chaque saisie, et la grille renvoyait ce qu'elle
avait lu en dernier. Seul `lock_version` est exigé, tout autre champ est facultatif, un champ absent
reste ce qu'il était, et `minProperties: 2` refuse un corps qui ne changerait rien. La création
garde ses champs exigés, sans compteur (`TaskFacetWrite`, `EstimateLineWrite`, `NodeCreate`) :
deux schémas par facette, comme `SubprojectWrite` et `SubprojectUpdate`, parce qu'une modification
partielle ne se décrit pas par `allOf` d'un schéma qui exige.

**Le nœud dit quels champs il accepte** (`editable_fields`, `EditableField`, #194), symétrique de
`computed_fields` : une ligne de main-d'œuvre porte le rôle et la charge, une autre le débours
unitaire et le délai de paiement — nul pour la main-d'œuvre, dit le §3.2.5, et le motif de
WF-DEV-0020 : une ligne de main-d'œuvre n'en saisit pas — (WF-DEV-0020), une provision ni l'un
ni l'autre, ni sa catégorie ni sa quantité ; une
tâche en mode manuel porte ses dates, un jalon n'a pas de durée, une récapitulative ni durée, ni
dates, ni avancement (WF-PLA-0130). La grille n'offre une cellule que si son champ y figure, sans
déduire la règle de la nature de la catégorie. La liste dit ce que la ligne accepte, pas ce que
l'appelant a le droit d'écrire, qui reste aux commandes de la révision. Écarté : laisser le serveur
refuser après coup, qui offre des commandes que l'API refusera (WF-IHM-0090).

**Toute écriture de grille rend la même enveloppe** (`NodesWritten`, #188, #201) : les nœuds écrits,
leurs ancêtres recalculés — montants, dates, durée, avancement d'une récapitulative, et les anciens
ancêtres d'un déplacement —, les totaux de la structure entière et le compteur de la structure. La
réponse ne portait que le nœud écrit, et la grille montrait des totaux et des montants de
récapitulatives faux jusqu'à une relecture (WF-DEV-0050, WF-ARC-0020). Une seule enveloppe pour
les dix écritures — cellule, collage, déplacement, création, suppression, liaison, avancement,
réestimation, inscription —, un tableau `nodes` même pour une cellule, vide après une suppression,
plutôt qu'une enveloppe par opération ; une suppression qui répondrait 204 laisserait la grille
sans le compteur que la structure a pris, et le collage suivant en 412.
Les totaux sont ceux de la structure sans filtre : une grille filtrée relit les siens par
`listNodes`. Écartés : relire la structure après chaque saisie, six mille nœuds pour une cellule
(§4.6.2) ; une relecture ciblée des ancêtres, un appel de plus par saisie.

**Le compteur du collage est celui de la structure** (`PasteApply.lock_version`,
`CostStructure.lock_version`, #201), et il avance à chaque écriture dans son arbre, pas seulement
à la modification de la structure elle-même : sans cela, un collage confirmé après la saisie d'un
collègue sur l'une de ses lignes l'écraserait sans refus (WF-IHM-0110). `applyPaste` déclare 412,
et l'enveloppe rend le compteur suivant (`structure_lock_version`) à chaque écriture, pour que la
grille porte toujours le dernier. Écarté : le plan lui-même (`paste_id`) comme objet du compteur,
qui aurait obligé le serveur à garder un plan tant que la structure ne change pas.

**La colonne visée d'un collage est une colonne de `listNodes`** (`NodeColumn`,
`PastePreview.target_column`, #200) : une énumération nommée, celle du tri, que les deux emploient.
Son ordre est celui des grilles — planning (WF-PLA-0080), puis devis et reste à engager
(WF-DEV-0050, WF-RAE-0040) —, et c'est dans cet ordre que le bloc remplit les colonnes qui suivent
la colonne visée, parmi celles de la facette du nœud visé : le serveur ne connaît ni les colonnes
que la grille montre ni leur ordre (WF-IHM-0060), et le contrat fixe donc l'ordre de référence.
Aucune cellule n'est décalée : une cellule non vide qui tombe sur une colonne que sa ligne n'accepte
pas — calculée pour ce nœud, refusée par sa nature, ou qu'aucune écriture ne porte — est refusée,
nommée par sa ligne et sa colonne (`PastePlan.rejected[].column`) ; une cellule vide n'écrit rien,
pour qu'un bloc de lignes de main-d'œuvre et hors main-d'œuvre se colle tel qu'un tableur le copie.
`max_columns` compte les colonnes de la facette à partir de la colonne visée. Écartés : un tableau
`columns` envoyé par la grille, qui ferait du contrat l'image des colonnes affichées ; sauter une
colonne non saisissable, qui déplacerait une valeur dans la colonne voisine — ce que le motif de
WF-IHM-0050 veut éviter. La garde locale du front — un bloc trop large ou qui enjambe une colonne
masquée, refusé avant de rien demander — reste à aligner sur cet ordre : elle mesure encore la
portée d'un bloc sur les colonnes de la configuration de la grille, non sur celles de la facette
dans l'ordre de `NodeColumn` (#223).

**La liste des contributeurs a son compteur** (`ContributorList`, #186). `setContributors` exigeait
un `lock_version` sans dire de quel objet, et `listContributors` rendait un tableau nu : le
formulaire n'aurait rien eu à renvoyer. Le compteur est celui de la liste, rendu par la lecture
dans une enveloppe `{ items, lock_version }` et par l'écriture avec le suivant, exigé par
`ContributorsWrite`, périmé par 412. Écarté : le compteur du projet, qui aurait fait de chaque
changement du libellé ou du taux d'inflation un conflit pour une liste ouverte avant lui, et
l'inverse. `Contributor.is_active` est exigé : une valeur absente ne disait ni actif ni désactivé,
et l'écran ne devine rien (WF-ADM-0060).

**Les rôles et les catégories actifs se lisent avec le projet** (`listResourceRoles`,
`listCostCategories`, #195). La grille du devis nomme et offre au choix le rôle et la catégorie de
chaque ligne (WF-DEV-0020) ; un chiffreur sans `resource_settings.read` lisait un devis dont il ne
pouvait ni nommer ni choisir les rôles. Les objets actifs sont lisibles par quiconque consulte un
projet ; les objets désactivés (`include_inactive`) et toute écriture restent sous la permission du
référentiel (WF-ADM-0100), et `include_inactive` sans elle est refusé par 403. Écarté : rendre avec
`listNodes` les rôles et catégories que la structure emploie, qui alourdirait chaque lecture de
six mille nœuds de ce qui change une fois par an.

**La grille des taux horaires se lit en une fois** (`GET /reference/hourly-rates`,
`getHourlyRateGrid`, `HourlyRateGrid`, #162). Le §3.4.4.1.2 présente les taux « comme une grille :
une ligne par catégorie de main-d'œuvre, une colonne par année », et le contrat ne les servait
qu'une catégorie à la fois : cent cinquante appels pour ouvrir l'écran (§4.6.2). La réponse porte
les années en colonnes (`years`) et les catégories en lignes (`rows`), chaque ligne nommée — code,
libellé, activité — pour que la grille ne joigne rien, avec une cellule par année à la même place,
nulle pour une année sans taux (WF-REF-0060) : des tableaux alignés plutôt qu'une liste creuse de
taux portant leur année, que la grille aurait dû placer. `listHourlyRates` reste, pour une
catégorie seule. Le volume `hourly_rate_grid.json` — cent cinquante catégories, quinze ans — est
engendré avec les autres (`make mock-data`), et la ligne de l'ingénierie électrique y est celle de
`hourly_rates.json`.

**Un écart, une catégorie proposée portent leur libellé** (`RevisionComparison.amount_deltas[].label`,
`RateUpdateProposal.categories[].label`, #204). Un écart n'était nommé que par sa `key`, une
catégorie que par son identifiant, et l'écran disait « Sans nom », WF-ARC-0020 lui interdisant de
joindre le référentiel. Le serveur résout le libellé à la lecture, comme `AmountByKey.label` et la
réponse de `getMissingRates` ; exigé, il est nul pour la seule clé `unassigned`, que le front sait
nommer.

**Un taux horaire manquant rend un montant non calculable** (`EstimateIndicators`,
`ComputableAmountByKey`, `hourly_rate_missing`, #159). WF-DEV-0010 refuse le calcul d'un devis
tant qu'une catégorie employée n'a pas de taux pour l'année de référence, parce qu'un taux à zéro
« produit un budget faux sans rien signaler » ; le contrat ne disait pas ce que rend
`getEstimateIndicators` dans ce cas, et l'écran montrait l'avis des taux manquants au-dessus d'un
total chiffré. Chaque montant du devis est un `Computable`, et les montants qui dépendent des
lignes sans taux — le total, la nature, le sous-projet et le poste qui les portent, les écarts, et
toute part du total — ne se calculent pas, motif `hourly_rate_missing`, les catégories et les
années nommées par `params.missing_rates` (`MissingRate`, le schéma que `getMissingRates` rend
aussi) ; les montants que ces lignes ne touchent pas se calculent. Le motif suit la casse de son
énumération (`no_actual_cost`), non celle du code d'erreur `HOURLY_RATE_MISSING` qui dit le même
refus sur une écriture : les deux catalogues ont chacun leur convention. `Computable` gagne
`params`, parce qu'un motif peut nommer quelque chose — jusqu'ici, une grandeur nulle ne nommait
rien. Un montant calculable est un `ComputableMoney`, la même enveloppe dont la valeur garde la
contrainte de `Money` — deux décimales au plus — qu'un `Decimal` perdrait : le total, les écarts,
les montants par clé, et la projection au rythme constaté ; les ratios, les indices et les parts
restent des `Computable`. Écarté : refuser la lecture par 409 ou 422, qui aurait privé l'écran des montants que les
taux manquants ne touchent pas, et des provisions.

**Le devis dit son écart à la référence et ses totaux par poste** (`delta_to_reference`,
`by_order_item`, #160). WF-DEV-0060 demande « l'écart entre le devis en cours et celui de la
référence » et « les totaux par poste » ; le contrat ne rendait que l'écart à la révision marquée
précédente, qui n'est l'écart à la référence que par hasard. `delta_to_reference` est nul sans
révision de référence, `by_order_item` nul quand le planning n'est pas structuré en postes —
absents plutôt que nuls, comme le Vérif le veut —, et chaque poste est nommé par son libellé
(WF-PRJ-0020).
`delta_to_previous_revision` reste : la revue périodique le lit.

**Toute opération gardée par la session déclare le 401, et une règle du contrat l'exige**
(`rule/session-operation-declares-401` de `redocly.yaml`, #141). Le contrat ne le déclarait que sur
une minorité d'opérations, quand toute opération gardée par la session peut répondre 401 — session
absente, expirée ou révoquée (WF-SEC-0020) — et que le contrat déclare toute erreur qu'un client
peut rencontrer (WF-ARC-0060) ; le client factice des tests du front, typé sur les statuts
déclarés, ne pouvait pas simuler une session perdue sur ces lectures. Cent dix opérations
gagnent leur 401 — trente-huit le déclaraient, cent quarante-huit le déclarent —, et une règle
d'assertion de Redocly — une règle maison n'a pas été nécessaire — exige `401` dans les réponses
de toute opération dont `security` est absent, la session héritée de la racine : une opération
nouvelle ne peut plus l'oublier. La règle ne voit pas une opération qui écrirait
`security: [{ session: [] }]` : la convention est qu'aucune ne l'écrit, et qu'une opération
publique le dit par `security: []`.

**`correlation_id` a un motif** (`^[A-Za-z0-9._-]{1,64}$`, #144). Une chaîne libre, qui pouvait
être vide, et qu'un identifiant repris d'un en-tête d'entrée sans contrôle aurait pu remplir de
n'importe quoi ; le front l'affiche comme référence d'une erreur inattendue et le met dans un
digest. Le back n'émet que des identifiants conformes, et remplace ce qu'un en-tête lui apporte
d'autre.

**La borne de taille d'un avatar est un réglage de l'installation** (`Installation.avatar_max_bytes`,
#153). Le contrat déclarait le 413 sans la borne, et le front ne pouvait ni la dire avant l'envoi
ni régler sur elle le corps qu'il laisse passer. Elle est lisible sans session avec les autres
paramètres publics, et `putMyAvatar` la cite : un réglage, pas une constante du contrat, parce que
la taille admise relève de l'installation (§4.4.1, WF-CMP-0020). Écarté : un `maxLength` sur le
corps binaire, qui aurait figé la borne dans le contrat.

**Mineur** : `setDurationUnits` renvoie `responses.yaml#/UnprocessableEntity`, comme
`createCalendar`, au lieu d'une 422 écrite en ligne ; ce que `fields` nomme est dit par
`DurationUnitsWrite`.

## Les tâches qu'une écriture redate (EP-02/L10)

**L'enveloppe porte les tâches redatées, en projection légère** (`NodesWritten.rescheduled`,
`NodeSchedule`, #222, décision de l'utilisateur du 2026-10-04). Une liaison écrite, ou la durée
d'une tâche en mode automatique, redate ses successeurs (WF-PLA-0020) et peut déplacer le chemin
critique (WF-PLA-0100) : des tâches qui ne sont ni écrites ni ancêtres, et que la grille de
planning aurait montrées à leurs dates d'avant jusqu'à une relecture — le cas que #188 corrigeait
pour les montants. `rescheduled` rend les tâches non récapitulatives, chacune une fois, dans
l'ordre du plan, vide quand rien d'autre n'a bougé ; `ancestors` devient les ancêtres des nœuds
écrits et des tâches redatées, recalculés, chacun une fois, entier — deux phases en chaîne :
allonger une tâche de la première repousse la récapitulative de la seconde, qui n'est ni écrite
ni ancêtre d'un nœud écrit, et dont la durée n'est pas dans la projection ; `rescheduled` est
exigé sur toute écriture, pour que la grille n'ait pas à distinguer une enveloppe qui n'en parle
pas d'une enveloppe où rien n'a bougé. Chacune est un `NodeSchedule` — le nœud, son début, sa
fin, sa marge totale, nulle en mode manuel, sa criticité et sa fin dépassée —, pas un `Node` :
une chaîne de mille tâches reste légère, et le recalcul tient dans la seconde du §4.6.2. Les
montants qui dépendent des dates — le montant corrigé de l'inflation, l'année de consommation —
n'y sont pas : ils se lisent dans la grille de devis, écran distinct qui relit la structure à son
ouverture — EP-02/L16 les rend à part, pour les lignes et les tâches non récapitulatives
(`reinflated`). L'exemple `predecessor_set` lie la revue de conception du planning témoin au dossier
de conception : la revue, écrite, et la réception des études qui la suit glissent au 29 avril, et
le dossier, dont les dates ne bougent pas, passe sur le chemin critique. Écartés : des `Node`
entiers, qui pourraient porter la moitié du plan, facettes de devis comprises ; une relecture de
`listNodes` après chaque saisie de durée.

**La marge totale est une durée, sur la facette comme dans la projection** (`TaskFacet.total_float`,
`NodeSchedule.total_float`, `Duration`). La décision de #222 la donne en durée ; la facette la
portait en entier de jours (`total_float_days`), forme antérieure au planning en heures
(`WorkInstant`, EP-02/L7) : la même valeur serait arrivée à la grille sous deux formes selon
qu'elle est lue ou rendue par une écriture, et une marge de quatre heures ne s'y écrivait pas. La
marge est du temps de travail en jours ouvrés (`unit: d`), décimale, jamais négative — les tâches
en mode manuel, traitées comme des dates imposées, l'évitent (WF-PLA-0100) —, et nulle pour une
tâche en mode manuel. La colonne et le champ calculé suivent (`NodeColumn.total_float`,
`ComputedValueField` `task.total_float`), et la grille de planning l'écrit comme une durée, par
sa valeur et son unité.

## Les risques d'une révision (US-0230/L2)

Ajouts de lecture que l'écran des risques exige, faits par son lot sur l'autorisation de
l'utilisateur du 2026-10-04 (« ajouts de lecture inclus ») : un lot d'écran ajoute au contrat
les exemples nommés des opérations qu'il consomme et les petits ajouts de lecture que son écran
exige.

**Les risques se lisent dans une révision** (`revision_id`, paramètre `RiskRevision` de
`listRisks`, `getRisk`, `listRiskReviews` et `getProjectRiskMatrix`). Chaque révision fige une
version du devis propre d'un risque (WF-RIS-0030), donc de sa gravité, de sa provision et de sa
case de matrice ; l'écran est sous `…/revisions/[r]/risks`, et sans le paramètre il montrerait,
pour une révision marquée, les chiffres de la révision en cours. Absent, la révision en cours,
ou la dernière marquée quand aucune n'est en cours ; c'est le nom que les indicateurs de devis
donnent déjà au même paramètre (`getEstimateIndicators`). L'historique des réexamens lu pour une
révision marquée s'arrête à son marquage. Un paramètre de requête et non un chemin sous la
révision : le risque est un objet du projet, que les révisions versionnent, et les chemins
d'écriture restent ceux du projet. Écarté : lire la révision de l'adresse dans le front pour
filtrer — le front ne saurait rien en tirer.

**La matrice dit les bornes de ses niveaux** (`RiskMatrix.probability_levels`,
`severity_levels`, `RiskMatrixLevel`). L'écran nomme les axes de la matrice par leurs bornes,
que le référentiel fixe (WF-REF-0160) : sans elles, il lirait le référentiel des risques, sous
une permission que le chef de projet n'a pas forcément, et rapprocherait deux réponses. Chaque
niveau porte sa borne basse, comprise, et sa borne haute, exclue, nulle au dernier niveau ; la
gravité en pourcentage du budget de référence, qui est celui de chaque projet — la matrice du
portefeuille, qui reprend `RiskMatrix`, porte les mêmes bornes. Écarté : les montants des bornes
de gravité, propres à un projet et faux pour le portefeuille.

**Le total général des provisions est rendu** (`ProvisionTotals.total`). WF-RIS-0040 veut les
trois totaux distincts et leur somme égale au total général : le front ne somme rien
(WF-ARC-0020), le serveur rend donc le quatrième, sur les mêmes risques retenus que les trois
autres.

**Exemples** : `risks` (trois risques, un par état — le survenu est celui de
`nodes_risk_occurred`, gravité 200 à 30 %, sa ligne de provision retirée — et les quatre
totaux), `risks_empty`, `risk`, `risk_occurred_detail` (le risque survenu, sa ligne de provision
retirée), `risk_reviews` (la probabilité passée de 25 à 40 %, la gravité de 1 000 à 1 250) et
`risk_matrix` (les seize cases, les bornes, les trois risques placés), dans l'univers des autres
exemples.

## Les exemples des courbes (US-0240/L2)

**Les lectures des courbes ont leurs exemples** (#246, autorisation de l'utilisateur du
2026-10-04 : un lot d'écran ajoute les exemples des opérations qu'il consomme). Sans eux, le faux
back tirait de leurs schémas des valeurs sans rapport avec l'univers témoin, et les tests du front
n'avaient rien du contrat à lire. Tous sont au 16 mars 2026, sur la révision courante du projet
témoin, et suivent les montants de `project_indicators` et de `remaining_indicators` — budget de
référence et reste à engager de 100 000, portés par les études de détail du 2 mars au 10 avril,
valeur planifiée de 33 333,33 à la date de calcul, aucun coût réel ni valeur acquise. Ils ne
suivent pas le devis de `nodes_estimate`, d'un autre univers : la scission des univers témoins est
#287. `milestone_tracking` (`getMilestoneTracking`) suit deux jalons, la réception des études et
la réception usine, par l'offre v1.0, la référence et la révision en cours ;
`milestone_tracking_none`, un projet sans jalon inscrit. `cost_curve` (`getCostCurve`) est la
courbe sans délais de paiement, sans marche ; `cost_curve_payment_delays`, les décaissements — le
budget de référence et la projection translatés de trente jours, le coût réel, nul, laissé à ses
dates, les mois à venir égaux au reste à engager ; `cost_curve_amendment`, la marche d'un avenant
de 15 000 contractualisé le 10 mars — `steps[].amount` y est le montant de la marche. **Une marche
est verticale** (WF-IND-0100 : « la courbe du budget présente une marche à sa date ») : la série
du budget de référence porte deux points à la date de la marche, la valeur d'avant puis celle
d'après, dans cet ordre, et non la seule valeur d'après, que le tracé relierait au point précédent
par une pente (relevé par la revue de la PR #289) ; le front trace les points tels quels.
`earned_value_curves` (`getEarnedValueCurves`) prolonge la valeur planifiée jusqu'à la fin de la
référence. Les exemples du plan de charge sont venus avec son écran (US-0240/L4, ci-dessous).

## Les exemples du plan de charge (US-0240/L4)

**Le plan de charge et ce que son écran offre au choix ont leurs exemples** (#286, même
autorisation de l'utilisateur du 2026-10-04). `getProjectWorkload` a un exemple par base, tous au
16 mars 2026 comme les courbes : `workload`, sur le reste à engager de la révision en cours, le
premier, que le faux back sert ; `workload_reference_budget`, sur les montants budgétés de la
révision de référence ; `workload_marked_remaining`, sur les montants réestimés de la révision
marquée « Référence », nommée par `revision_id`. Chacun répartit les 12,5 heures de main-d'œuvre
du raccordement des borniers, portées par le câblage des armoires du 4 mai au 30 juin, sur ces deux
mois au prorata de leurs heures travaillées — 5,95 en mai, 6,55 en juin —, pour l'ingénieur
électricien, sa capacité en regard ; le technicien de mise en service, du même nœud
d'organisation, n'a pas de charge, et sa capacité seule. Ces exemples suivent le devis de
`nodes_estimate`, non les montants de `project_indicators` : ils sont de l'univers du devis, que la
scission des univers témoins (#287) nomme déjà. Les deux rôles sont ceux de `resource_roles`,
relevant du bureau d'études électricité d'`org_nodes` — l'exemple du référentiel (US-0250/L1), que
l'écran offre au filtre, chaque nœud avec le libellé de son parent. `revisions_marked`
(`listRevisions`, filtre `status=marked`), les deux révisions marquées du projet, la référence et
l'offre v1.0, que l'écran offre comme base. Aucune forme du contrat ne change : rien que des exemples.

## Les coûts réels d'un projet (US-0230/L3)

Ajouts de lecture que l'écran des coûts réels exige, faits par son lot sur la même autorisation
de l'utilisateur du 2026-10-04 (« ajouts de lecture inclus »).

**Une ligne de coût nomme son sous-projet** (`ActualCostLine.subproject_code`,
`subproject_label`). La consultation présente l'imputation de chaque ligne (WF-CRE-0010,
WF-CRE-0020) ; la ligne ne la portait que par `subproject_id`, que l'écran ne pouvait nommer
qu'en rapprochant `listSubprojects` de chaque page, dans le front (WF-ARC-0020). Le code ERP et
le libellé, résolus à la lecture, exigés, nuls pour une ligne imputée au seul projet — « hors
sous-projet » —, comme le libellé d'un écart l'est pour la clé `unassigned` de
`RevisionComparison`. Écarté : un objet `subproject` imbriqué, qui redirait l'identifiant.

**La date du dernier import est toujours rendue** (`last_import_at`, exigé, nul tant que rien
n'a été importé). Facultative, son absence se confondait avec « aucun import » : l'écran aurait
dit qu'aucun import n'a eu lieu d'une réponse conforme qui l'omettait (relevé par Copilot sur la
PR #295). Exigée et nullable, `null` dit seul qu'il n'y a pas d'import.

**Exemples** : `actual_costs` (au 4 mai 2026, quatre lignes hors sous-projet — les codes de
sous-projet de l'ERP ne sont pas ceux du projet —, dont un avoir de -200 et la réception du
client exclue du périmètre suivi ; 3 000 suivis, le coût réel de `remaining_indicators_over_budget`,
650 exclus, 3 650 en tout ; le dernier import du 4 mai), `actual_costs_page` (la même
consultation lue une ligne par page, la deuxième ; les totaux de toutes les lignes retenues),
`actual_costs_subproject` (filtrée sur le Poste de commande, après l'import du 3 juin : une
facture imputée au sous-projet, nommé), `actual_costs_empty` (aucun import) ; `cost_imports`
(les imports de mars et d'avril, une ligne d'un autre projet ignorée), `cost_imports_periods`
(le journal au 3 juin : trois extractions à la période incomplète, dont une réextraction qui
ignore 12 345 lignes d'autres projets, puis les imports de mars et d'avril de `cost_imports`), `cost_imports_beyond` (une page demandée au-delà de la fin) et
`cost_imports_empty`.
Ils restent dans l'univers des indicateurs, sans coût réel au 16 mars (`project_indicators`).

## Le référentiel (US-0250/L1)

Ajouts que les écrans du référentiel exigent, faits par leur lot sur l'autorisation de
l'utilisateur du 2026-10-04 (« ajouts de lecture inclus »).

**La grille des taux horaires se cherche** (`search` sur `getHourlyRateGrid`). L'écran la
présente sur la grille dense, dont la recherche est celle de toute grille, et WF-IHM-0130 veut
toute table filtrable : la recherche retient les catégories dont le code ou le libellé contient
le texte cherché, et les années restent celles de toute la grille, pour qu'une colonne ne
disparaisse pas d'une recherche à l'autre. Écarté : une grille sans recherche, seule de son
espèce ; filtrer les cent cinquante lignes dans le front.

**Un objet du référentiel nomme ceux auxquels il est rattaché** (`ResourceRole.org_node_label`,
`cost_category_label`, `calendar_label`, `CostCategory.cost_type_label`, `OrgNode.parent_label`).
Les écrans présentent un rôle avec son nœud, sa catégorie et son calendrier, une catégorie avec sa
nature, un nœud avec son parent ; sans les libellés, le front rapprochait les listes qu'il lit
(WF-ARC-0020), comme `RevisionComparison` avant #204, et disait inconnu un objet désactivé mais
employé, que ces listes ne rendent pas sans `include_inactive` — lui-même refusé sans la
permission du référentiel —, quand il doit rester lisible (WF-REF-0150). Libellés résolus à la
lecture, actifs ou désactivés, exigés ; nul pour le parent d'une racine seul. Écarté : lire les
listes avec `include_inactive`, refusé à qui n'a que la lecture des projets.

**La recherche partagée** (`Search`) cherche sur le libellé ; une opération qui cherche aussi sur
un autre champ le dit dans sa description, comme la grille des taux sur le code.

**Exemples**, dans l'univers des autres : `reference_settings` (l'euro, le français, les bornes
de la matrice et les zones de `risk_matrix`, les seuils 0,9 et 0,8 d'`index_history`, huit
semaines entre deux revues, que dépasse le projet témoin de `pilot_health`), `cost_types` (les
trois natures que ventilent les indicateurs de devis), `org_nodes` (trois niveaux, les nœuds des
rôles de `resource_roles` au deuxième et au troisième, un service sans rôle), `calendars` (le
calendrier par défaut, et la semaine de quatre jours du monteur câbleur, EP-02/L20 ; l'automaticien désactivé de `resource_roles` est rattaché à un
troisième, désactivé, que la liste ne rend pas et que son libellé nomme), et, pour `setHourlyRate`, `hourly_rate_entered` — le premier taux 2015 d'une catégorie
qui n'en avait pas dans la grille des volumes — et `hourly_rate_corrected` — le taux 2016 de la
même catégorie corrigé, sa version avancée. La catégorie n'est employée par aucun devis des
exemples : ni l'une ni l'autre écriture ne contredit un montant chiffré ailleurs.

## L'administration (US-0250/L2)

Ajouts que les écrans de l'administration exigent, faits par leur lot sur l'autorisation de
l'utilisateur du 2026-10-04 (« ajouts de lecture inclus »).

**Un compte nomme ses rôles et son nœud** (`User.access_role_labels`, `User.org_node_label`).
L'écran des comptes présente chacun avec ses rôles d'habilitation et son rattachement
(WF-ADM-0050) ; sans les libellés, le front rapprochait `listAccessRoles` et `listOrgNodes` des
comptes (WF-ARC-0020), et disait inconnu un nœud désactivé auquel un compte reste rattaché
(WF-REF-0150). Libellés résolus à la lecture, exigés : les rôles dans l'ordre de
`access_role_ids`, le nœud nul sans rattachement. Ils valent pour `UserSelf`, que la session
rend. Écarté : des objets `{access_role_id, label}` à la place des identifiants, qui auraient
changé la forme que `setUserAccessRoles` écrit.

**Exemples**, dans l'univers des autres, au 16 mars 2026 : `users` et `users_page` (les comptes
de l'installation, par nom — Dominique Bernard de `me_directory`, Camille Martin de la session,
Alix Moreau, désactivée, de `contributors`, et un compte venu du fournisseur d'identité, sans
rôle —, puis leur seconde page lue deux par deux) ; `permissions` (le catalogue, dans l'ordre de
`PermissionCode`) ; `access_roles` (les trois rôles prédéfinis tels que livrés, et celui, composé
de tout le catalogue, que porte la session) ; `system_status` et `system_status_backup_failed`
(l'installation saine, puis la même au stockage des fichiers indisponible, la sauvegarde planifiée
échouée et signalée) ; `backups` et `backups_empty` (les sept sauvegardes de la rétention et une
manuelle marquée à conserver ; aucune ; une page demandée au-delà de leur fin, `backups_beyond`) ;
`backup_schedule`, `backup_schedule_weekly` et `backup_schedule_disabled` (suspendue). Les sessions
d'un chiffreur et sans administration, qui n'ont pas tout le catalogue, portent chacune un rôle
propre (`Chiffreur`, `Pilotage de projet`), que `access_roles` ne liste pas : ce sont d'autres
installations que celle de l'exemple.

## L'import en deux temps (US-0260/L1)

Ajouts que l'écran d'import exige, faits par son lot sur l'autorisation de l'utilisateur du
2026-10-04 (« ajouts de lecture inclus »).

**Un import nomme son fichier** (`Import.filename`, exigé). L'écran présente les imports du projet
et le compte rendu de chacun (WF-INTF-0080) : sans le nom du fichier, deux imports de même nature
ouverts le même jour ne se distinguent pas, et le fichier lui-même est supprimé dès l'import
appliqué, abandonné ou expiré (WF-DAT-0120) — `FileUpload.filename` ne se relit plus. Le nom est
celui que l'utilisateur a envoyé, gardé tel quel. Écarté : renvoyer au dépôt par `upload_id`, qui ne
se lit pas.

**Exemples**, dans l'univers des autres : `file_upload` (le devis du Poste de commande déposé le
1er juin 2026 à 8 h 40), `import_analysing` (son import ouvert, l'analyse en cours),
`import_analysed` (le même analysé à 8 h 41 : cinq lignes lues — deux rejetées, une tâche et un
rôle inconnus, « Essais de continuité » ajoutée, « Raccordement des borniers » modifiée, la
provision inchangée —, et « Borniers », que le fichier ne porte plus, retirée ; il est de l'univers
du devis de `nodes_estimate`, de la scission des univers témoins, #287), `import_planning_mismatch`
(un planning MS Project tel qu'il se lisait le 20 mai à 10 h 16, analysé et pas encore abandonné,
dont la durée des « Études de détail » diffère de celle que Waterfall recalcule, qui demande une
confirmation explicite ; il est de l'univers des indicateurs et du planning, sa tâche étant
0602 de `nodes.json`, #287), `imports` (au 1er juin : le devis qui attend sa
confirmation, le planning abandonné, et les quatre extractions de coûts réels de
`cost_imports_periods` antérieures au 1er juin, appliquées), `imports_page` (la même liste lue
deux par deux, sa deuxième page) et `imports_empty` ;
`task_export_queued` et `task_export_succeeded` (l'export du devis demandé à 9 h 10, abouti, son
résultat à lire par la tâche). L'application de l'import du devis est `task_import_queued`, à
9 h.

## Les exemples du portefeuille (US-0240/L3)

**Les vues du portefeuille ont leurs exemples**, faits par le lot de leurs écrans sur
l'autorisation de l'utilisateur du 2026-10-04 (un lot d'écran ajoute les exemples des
opérations qu'il consomme). Sans eux, le faux back tirait de leurs schémas des valeurs sans
rapport avec les trois cents projets de `getPortfolioProjects`. **Ce qui se somme des lignes de
la liste est engendré avec elle** (`make mock-data`, `fixtures/api/volume/`), au 16 mars 2026 :
la valeur (`portfolio_value`, `getPortfolioValue` : le carnet des projets en cours, le pipeline
brut et pondéré des offres, rien de réalisé — aucun projet du périmètre n'est terminé —, et le
taux de transformation du Vérif de WF-PTF-0050, quatre offres gagnées sur dix sorties du
chiffrage dans l'année) ; la performance (`portfolio_performance`, `getPortfolioPerformance` :
chaque indice en rapport des sommes, la valeur acquise, le coût réel et la valeur planifiée de
chaque projet tirés de son budget et de ses indices — ceux du projet témoin, de
`project_indicators` —, la répartition par zone comptant chaque projet une fois par indice, le
projet témoin sans zone de coût, et quatre trimestres d'évolution, le premier non calculable, faute de coût réel et de valeur planifiée) ; la structure des coûts
(`portfolio_cost_structure`, `getPortfolioCostStructure` : le budget et le reste à engager par
nature, dont les parts somment à un, et la main-d'œuvre du bureau d'études électricité, le nœud
dont relèvent tous les rôles de l'univers) ; les risques (`portfolio_risks`,
`getPortfolioRisks` : le registre du projet témoin et jusqu'à trois risques identifiés par autre
projet en cours, chacun tiré d'abord dans une case de la matrice, puis sa probabilité et sa gravité
dans les bornes des niveaux de cette case (`risk_matrix`), sa provision la gravité pondérée par la
probabilité (WF-RIS-0010) ; les dix plus lourds avec leur projet) ; et la deuxième page de cinquante
projets de la liste (`portfolio_projects_page`).
**Ce que la liste ne porte pas s'écrit à la main**, au même instant et sur le même périmètre :
`portfolio_workload` (`getPortfolioWorkload` : deux rôles de `resource_roles` sur six mois, au
seuil de 50 %, chaque mois avec sa zone) et `portfolio_cash_out` (`getPortfolioCashOut` :
d'octobre 2025 à septembre 2026, mars portant le passé et l'avenir). `portfolio_projects_empty`
est la liste filtrée qui ne retient aucun projet. `pilot_health` reste au 1er juin, l'exemple de
l'US-0160. Les montants des exemples écrits à la main ne sont pas tirés des trois cents projets :
leur échelle se suit dans #287.

**La période des statistiques, par défaut, est l'année qui précède la date de calcul.** Les
statistiques d'une période — le réalisé et le taux de transformation de la valeur (WF-PTF-0050),
les provisions survenues et écartées des risques (WF-PTF-0090) — se calculent sur `from` et
`to` ; quand la requête ne les nomme pas, le serveur retient les douze mois qui finissent à la date
de calcul, et les rend dans `scope.from` et `scope.to`, que l'écran affiche avec la vue
(WF-IHM-0020). La liste des projets, qui ne retient de projet terminé que sur une période demandée,
rend alors une période nulle.

## Le seuil de sous-charge retenu (US-0240/L5)

**Le plan de charge agrégé rend toujours son seuil de sous-charge**
(`PortfolioWorkload.under_load_threshold`, exigé), resserrement de lecture que l'écran exige, sur
l'autorisation de l'utilisateur du 2026-10-04 (« ajouts de lecture inclus »). Facultatif, une réponse conforme pouvait l'omettre, et
l'écran, qui montre le seuil retenu par le serveur quand l'adresse n'en nomme aucun, aurait dit
« Par défaut » sans dire lequel (relevé par Copilot sur la PR #338), comme `last_import_at` des
coûts réels l'a été. L'exemple `portfolio_workload` le porte. `portfolio_cash_out_credit`, calculé au
31 décembre 2025, montre un mois de décaissements net négatif — les avoirs de décembre importés
avant ses factures, que l'import de janvier apporte au 16 mars — : un décaissement est un `Money`
signé, comme le coût réel dont il vient.

## Les précisions du contrat (EP-02/L15)

Ce que le contrat taisait, sur la décision de l'utilisateur du 2026-10-05 de regrouper les issues
du contrat par nature. Chaque précision suit la spécification, une convention déjà prise ou ce
que les exemples disaient déjà ; trois suivent une décision de l'utilisateur du même jour, dite à
leur place (#324, #292, #236).

**L'heure d'une sauvegarde planifiée est en temps universel** (`BackupSchedule.at_time`, #316),
comme tout instant de la plateforme (`Timestamp`, WF-DAT-0100) et comme le disaient les
exemples : la planification de `backup_schedule` à 01:00 et les sauvegardes de `backups` prises à
`01:00Z`. Le jour d'une planification hebdomadaire s'entend de même, numéroté comme ISO 8601, 1
le lundi (`weekday`, #314), ce que l'exemple `backup_schedule_weekly` faisait déjà du dimanche,
7. Écarté : le fuseau de l'installation, qu'aucun paramètre ne porte. Une sauvegarde à heure fixe
en UTC se décale donc d'une heure en heure locale aux changements d'heure — 02:00 l'hiver, 03:00
l'été à Paris pour 01:00 UTC — : c'est assumé. L'écran dit l'heure en UTC, sans la convertir :
une heure du jour n'a pas de date d'où tirer le décalage d'un fuseau à heure d'été. Le sens du
403 de `listBackups`, relevé avec #316, est suivi en #348.

**Les imports se lisent du plus récent au plus ancien** (`listImports`, #320), par leur ouverture,
comme le journal des imports de coûts réels, les révisions et les tâches de l'appelant ; l'exemple
`imports` les rangeait déjà ainsi.

**Les zones de la matrice se rangent par probabilité puis par gravité** (`RiskMatrixSettings.zones`,
#298), chaque axe du plus bas au plus haut, l'ordre où `reference_settings` les donnait déjà,
celui des cases de `risk_matrix`.

**La borne d'un avatar ne dépasse pas 8 Mio** (`Installation.avatar_max_bytes`, `maximum`, #233).
La spécification dit seulement que « la taille d'un avatar est bornée par l'application »
(§4.4.1) ; 8 Mio est le
plafond technique proposé par la revue d'EP-02/L13 : le front règle d'avance, par un réglage
statique de Next, la taille de corps de ses actions serveur (`bodySizeLimit`), et ne peut la
régler qu'au-dessus d'un maximum déclaré, l'enveloppe du formulaire comprise. Huit mébioctets
restent sous cette borne, et la taille admise reste un réglage de l'installation sous ce maximum.

**Un dépôt dit son usage, qui le borne** (`uploadFile`, `purpose`, `FileUploadPurpose`, #324 ;
décision de l'utilisateur du 2026-10-05, « une borne par usage »). `uploadFile` reçoit le fichier
d'un import et la sauvegarde copiée hors de la plateforme qu'une restauration désigne
(WF-ADM-0160) : un seul maximum aurait refusé l'une ou laissé passer l'autre. Le fichier d'un
import (`import`) ne dépasse pas 10 Mio, un fichier MS Project, le plus lourd des imports du
§4.6.2 ; une sauvegarde à restaurer (`external_backup`) ne dépasse pas
`Installation.external_backup_max_bytes`, un réglage de l'installation, sur le modèle
d'`avatar_max_bytes`, la spécification ne fixant pas la taille d'une sauvegarde. Au-delà, 413,
`FILE_TOO_LARGE`. `FileUpload.purpose` redit l'usage ; un import ne s'ouvre que sur un dépôt
d'import, une restauration que sur un dépôt de sauvegarde. Le front règle sa borne sur celle des
imports (`IMPORT_MAX_BYTES`, `bodySizeLimit`). Exemples : `file_upload` (un import),
`installation` (vingt gigaoctets).

**Un paramètre de requête refusé se désigne par `/query/<nom>`** (`FieldProblem.pointer`, #307).
Le pointeur JSON ne désigne que le corps ; un paramètre de requête a désormais sa forme, préfixée,
qu'aucun champ du corps ne peut prendre, et que le front compare entière. Écarté : `/revision_id`,
qu'une opération à corps et à paramètres aurait rendu ambigu. L'exemple
`workload_revision_refused` (`getProjectWorkload`) la montre.

**`listActualCosts` refuse un filtre qu'il ne peut appliquer** (422, `VALIDATION_FAILED`, #293),
comme `getProjectWorkload` refuse une révision ou un nœud d'organisation : une période dont la fin
précède le début (`/query/to`, `VALUE_OUT_OF_RANGE`), une date mal formée (`DATE_INVALID`), un
sous-projet que le projet n'a pas ou un identifiant mal formé (`/query/subproject_id`,
`UNKNOWN_SUBPROJECT`) ; exemples `actual_costs_period_inverted` et
`actual_costs_subproject_unknown`. Un refus par champ plutôt que `MALFORMED_REQUEST` (400) : la
valeur vient d'un filtre que l'utilisateur a saisi, et l'écran doit dire lequel corriger, ce que
`fields` porte et que le 400 du catalogue ne porte pas ; une date mal formée est de même un motif
par champ du catalogue (`DATE_INVALID`). Écarté aussi : une liste vide, qui dirait « aucune
ligne » d'une demande que le serveur n'a pas comprise.

**Chaque colonne des coûts réels se trie** (`sort_by` de `listActualCosts`, #292), comme toute
colonne de grille (WF-IHM-0060) : le périmètre suivi (`in_tracked_scope`, les lignes exclues
avant les suivies dans l'ordre croissant), le motif (`excluded_reason`) et, sur la décision de
l'utilisateur du 2026-10-05, chaque colonne conservée du fichier, `passthrough.<colonne>`, nommée
comme `passthrough` la nomme. Le motif et les colonnes conservées se comparent en texte, caractère
par caractère dans l'ordre des points de code Unicode — une valeur importée n'a pas de type que
le serveur pourrait lire —, une ligne sans valeur après les autres dans l'ordre croissant. La
grille présente chaque colonne conservée comme une colonne, sous le nom que le fichier lui donne.

**Le 412 de `setHourlyRate` est déclaré** (#296), comme celui de toute écriture qui porte une
version : `STALE_LOCK_VERSION`, `params.expected_lock_version` la version courante ; un taux n'a
pas d'identifiant propre, la catégorie et l'année du chemin le nomment. Exemple
`hourly_rate_stale`, la correction de `hourly_rate_corrected` envoyée avec la version d'avant.

**Le 409 d'une lecture que l'état du projet interdit est `STATE_FORBIDS_OPERATION`** (#248), par
la convention du catalogue (`ErrorCode` : « 409 — l'état courant interdit l'opération ; `params`
nomme l'objet ou l'état ») : celui de `getProjectIndicators`, avant l'état En cours, et celui de
`getProjectWorkload`, sans révision de référence, que l'écran attendait de même. `params.state`
nomme l'état du projet. Exemples `project_indicators_not_in_progress` et `workload_no_reference`,
le projet en chiffrage de `project_pricing`.

**Le résultat d'une tâche se télécharge nommé et typé** (`getBackgroundTaskResult`, #323) :
`Content-Disposition` exigé, `attachment` et le nom que le serveur donne au fichier — un nom qui
n'est pas en ASCII aussi en `filename*` (RFC 6266) —, et le type de média de la nature de
l'export — classeur Excel pour un devis ou un reste à engager (WF-INTF-0110, WF-INTF-0130 ;
`.xlsx`, comme les fichiers des exemples), XML pour un planning MS Project (WF-INTF-0050), PNG
pour l'arborescence (WF-PLA-0120) — au lieu de `application/octet-stream`. Le classeur vient en
premier, celui que le faux back sert, comme l'exemple de l'en-tête (`task_result_disposition`),
le devis de `task_export_succeeded`.

**`FILE_FORMAT_UNREADABLE` nomme le format et la version attendus** (`params.expected_format`, un
`ExchangeKind`, et `params.expected_version`, #321), ce que WF-INTF-0070 et la description
d'`openImport` promettaient ; exemple `import_format_unreadable`. Le format est nommé par la
nature de l'import, que le front rend par son catalogue.

**Le montant budgété d'une ligne est celui que la révision de référence a fixé** (#245) : une
ligne de provision présente dans la révision de référence porte la provision qu'elle y avait, et
le budget de référence est, comme le dit le glossaire, « la somme des montants budgétés des lignes
de la révision de référence, diminuée des provisions selon les règles de WF-RIS-0050 ». Il se lit
dans les indicateurs, jamais en sommant les montants des lignes : le montant budgété d'une tâche
et `NodeTotals.budgeted_amount` comptent les lignes de provision. Ce que porte la ligne de
provision d'un risque écarté, ou identifié après la référence, est l'issue de spécification #347.

**Une marche de la courbe porte son montant** (`CurveSeries.steps[].amount`, #285), signé, ce dont
le budget de référence change à sa date, et non le budget après elle, que la série
`reference_budget` porte ; c'est ce que `cost_curve_amendment` montrait. Le nom reste.

**Les structures des risques témoins ont leurs exemples** (#252) : `structures_amendments` porte
les devis propres du retard de livraison des armoires et de l'indisponibilité de l'automaticien,
nommés par `risks`. La chronologie des risques témoins et des révisions — quand le retard est
survenu, quelle révision sa survenance a produite — n'est pas tenue par les exemples : elle est
suivie dans #287.

**Un recalcul ne fait avancer le compteur d'aucun nœud** (`LockVersion`, `NodeSchedule`,
`NodesWritten.rescheduled`, #236 ; décision de l'utilisateur du 2026-10-05). Le compteur suit les
écritures de l'utilisateur : les dates que le serveur recalcule — les successeurs d'une liaison ou
d'une durée, ce que le chemin critique déplace — et ce qu'il recalcule d'une récapitulative ne le
font pas avancer. Sans cela, la saisie suivante d'une tâche redatée partirait de la version lue
et recevrait un 412 que personne n'a provoqué. `NodeSchedule` ne porte donc pas `lock_version`,
et les ancêtres rendus entiers gardent le leur, ce que les exemples (`predecessor_set`,
`estimate_line_updated`) montraient déjà ; le compteur de la structure, lui, avance à chaque
écriture dans son arbre (`structure_lock_version`). Le front garde la version lue d'une tâche
redatée et n'en prend que le calendrier (`rescheduled()` de
`frontend/src/components/grid/nodes.tsx`).

## Les montants et les libellés de la structure (EP-02/L16)

**La grille de devis lit un montant nommé à l'année de référence** (`base_amount`, #235, décision
de l'utilisateur du 2026-10-05). WF-DEV-0050 veut, pour chaque ligne, son montant à l'année de
référence et son montant corrigé de l'inflation, et jamais le montant budgété ni le montant
réestimé ; le contrat ne nommait pas le premier, et la grille lisait `reestimated_amount` à sa
place (#216). `base_amount` est le montant de la ligne telle qu'elle est chiffrée — quantité ×
charge × taux de l'année de référence, ou quantité × débours (WF-DEV-0030) —, sur la ligne, sur la
tâche (somme de son sous-arbre, récapitulative comprise) et dans `NodeTotals` ; la colonne et le
champ calculé suivent (`NodeColumn.base_amount`, rangé avant les montants budgété et réestimé de
la grille de reste à engager ; `ComputedValueField` `task.base_amount`, `estimate_line.base_amount`).
Les montants budgété et réestimé sont, eux aussi, à l'année de référence (sous-décision du même
jour) : seul `inflated_amount` porte l'inflation, et les descriptions le disent. La colonne de la grille
change de clé avec son champ (`reestimated_amount` → `base_amount`) : une largeur, un masquage ou un
tri gardés sous l'ancienne clé dans les préférences d'affichage ne s'appliquent plus, et la colonne
revient à son réglage par défaut.

**Le montant corrigé de l'inflation remonte à la tâche et aux totaux** (`TaskFacet.inflated_amount`,
`NodeTotals.inflated_amount`, `ComputedValueField` `task.inflated_amount`). Une récapitulative et le
total n'avaient pas de montant corrigé, et la grille montrait une cellule vide ; ils portent la
somme des montants corrigés de leurs lignes, que le front ne calcule pas.

**Après une écriture qui déplace des nœuds dans le temps, leurs montants corrigés en projection
légère** (`NodesWritten.reinflated`, `NodeInflation`, exigé ; décisions de l'utilisateur du
2026-10-05). Un rôle changé dans la grille de devis change le calendrier de la tâche
(WF-PLA-0010), donc ses dates et l'année de consommation de ses autres lignes (WF-DEV-0040) ; une
durée ou une liaison écrite au planning déplace de même les lignes des tâches qu'elle redate. Leur
montant corrigé, et celui des tâches non récapitulatives qui les portent — redatées
(`rescheduled`) ou non —, serait resté périmé dans la grille même. `reinflated` rend chaque nœud
dont le montant corrigé a changé sans être écrit, lignes et tâches non récapitulatives, hors ceux
que `ancestors` rend entiers, où restent les récapitulatives ; chacun une fois, dans l'ordre du
plan, vide quand aucun n'a bougé, sur le modèle de `rescheduled` : le nœud, son montant corrigé et
l'année de consommation d'une ligne, nulle pour une tâche, dont la facette n'en porte pas — une
chaîne de mille tâches et de leurs cinq mille lignes reste légère. Une tâche peut ainsi être dans
`rescheduled` et dans `reinflated` : chaque projection pose ses seuls champs, et la grille les
compose. Comme `NodeSchedule`, `NodeInflation` ne porte pas `lock_version` : un recalcul ne
fait pas avancer le compteur du nœud (EP-02/L15, `LockVersion`). Le montant à l'année de
référence ne dépend pas des dates : il n'y est pas. Écarté : le
montant corrigé d'une tâche dans `NodeSchedule`, qui aurait mêlé les montants au calendrier et
laissé sans projection une tâche dont les lignes bougent sans qu'elle soit redatée. L'exemple
`task_lengthened` (`updateTaskFacet`), engendré dans le volume par `make mock-data`, le montre :
la durée de « Revue 3.1.27 » allongée de deux jours ouvrés, dans sa marge, pousse « Reprise
3.1.30 » au premier jour ouvré de 2027 ; elle est dans `rescheduled` avec les tâches de sa chaîne
dont la marge diminue, ses lignes et elle-même dans `reinflated`, les deux récapitulatives au-dessus
dans `ancestors`, et les totaux suivent. Les autres exemples rendent une liste vide. L'univers
n'offrait aucune écriture du devis qui redate : ses deux rôles actifs étaient sur le même
calendrier, le calendrier par défaut, et le seul rôle sur un autre était désactivé — un changement de
rôle ne changeait donc le calendrier d'aucune tâche (WF-PLA-0010). Le monteur câbleur, actif sur la
semaine de quatre jours, le permet depuis EP-02/L20 ; la projection est éprouvée sur l'exemple du
planning appliqué aux lignes du devis, et le chemin de la grille de devis le sera avec l'écriture
qui redate (EP-02/L22, #287).

**Les exemples de dépendance d'un montant suivent** : `dependencies_labour` et
`dependencies_task_amount` disent désormais ce dont dépend le montant à l'année de référence d'une
ligne et d'une tâche — le taux horaire ; les lignes portées —, celui dont la grille de devis
demande la raison au refus d'une saisie.

**`paste_too_wide` dit la largeur de la ligne de devis** : `base_amount` porte à quatorze les
colonnes de sa facette à partir du libellé (`NodeColumn`) ; l'exemple disait huit, largeur
antérieure à EP-02/L8, et dit désormais quatorze pour un bloc de quinze.

**La ligne de devis nomme sa catégorie, son rôle et son sous-projet** (`cost_category_label`,
`resource_role_label`, `subproject_label`, #305, décision de l'utilisateur du 2026-10-05). La
grille les nommait en rapprochant `listCostCategories` et `listResourceRoles` dans le front, ce que
WF-ARC-0020 exclut, et disait inconnu un objet désactivé mais employé, que ces listes ne rendent
pas sans `include_inactive` (WF-REF-0150). Les trois libellés sont exigés, résolus par le serveur à
la lecture, l'objet actif ou désactivé, nuls sans objet — le rôle d'une ligne hors main-d'œuvre, le
sous-projet d'une ligne hors sous-projet —, comme ceux d'un rôle de ressource (US-0250/L1). Ils
pèsent sur six mille nœuds : `fields` ne les rend qu'à la grille qui les lit, celle du devis, qui ne
présente pas encore de sous-projet et ne demande donc pas `subproject_label`. Les listes du
référentiel restent lues par l'écran, pour offrir le choix d'une saisie.

## Ce que l'écran offre : échanges et dépendances d'un risque (EP-02/L17)

Décisions de l'utilisateur du 2026-10-05, consignées sur #318 et #250.

**Les imports sont des commandes du projet, les exports des commandes de la révision** (#318).
Seul l'import des coûts réels avait sa commande (`import_actual_costs`) : rien ne disait quand un
planning, un devis ou un reste à engager s'importe, ni s'il s'importe sans révision en cours, ni
quand un export est disponible, et l'écran déduisait les uns de la saisie de la révision en cours
(`edit_*`) et offrait l'autre à qui le lisait. `ProjectCommand` gagne `import_planning`,
`import_estimate` et `import_remaining`, à côté de `import_actual_costs` : l'import écrit dans la
révision en cours et la crée quand il n'y en a pas (WF-INTF-0090), il se dit donc du projet, avec
ou sans révision en cours. Chacune est gardée par sa permission, comme la saisie : un chiffreur
importe un devis sans pouvoir importer un planning. `RevisionCommand` gagne une commande par
nature d'export (`ExportRequest.kind`) : `export_planning`, `export_estimate`,
`export_remaining`, `export_task_tree_image`. Écartés : une commande `request_export` unique, qui
ne dirait pas qu'un chiffreur exporte le devis et pas le planning ; les imports sur la révision,
qui ne se diraient pas sans révision en cours.

**Sans révision en cours, l'import exige aussi la permission de créer une révision**
(`revisions.write`), et le dit par une condition : la commande est listée indisponible,
`may_create_revision` manquante, plutôt qu'absente (exemple `project_pricing_estimator`). C'est
la réponse de l'utilisateur du 2026-10-05 à la sous-question de #318, et la seule exception à la
règle qui ne liste que les commandes que l'appelant a la permission d'exercer (« Le projet et la
révision portent leurs commandes disponibles », plus haut) : elle tend contre WF-IHM-0090, qui
veut qu'une commande que les habilitations ne permettent pas ne soit pas présentée — une
habilitation manquante ne se lève pas par l'utilisateur. Elle est soumise à l'utilisateur à son
retour ; d'ici là, elle tient comme décidée.

**Un export relève de la consultation** : il est gardé par la permission de consulter la
fonction de sa nature — le planning et l'image de l'arborescence par celle du planning (FBS-4.3),
le devis par celle du devis (FBS-4.4), le reste à engager par celle du reste à engager (FBS-4.5) —,
deux niveaux par fonction (WF-ADM-0100). WF-CYC-0110 range les exports dans ce qui reste
consultable d'un projet terminal (« ses exports aboutissent ; seules les modifications sont
refusées ») : un export ne manque d'aucune condition, ni sur une révision marquée, ni pendant un
marquage, ni sur un projet terminal. Il est présent ou absent. Les exemples le suivent : tous les
exports sur les révisions lues avec toutes les permissions et sur `revision_reader`, qui lit tout
sans rien modifier ; le devis et le reste à engager pour le chiffreur (`revision_estimator`), qui
les lit sans lire le planning. Les imports sont disponibles sur le projet témoin et sur le projet
en chiffrage sans révision, indisponibles sur le projet terminé (`project_not_terminal`).

**Le risque porte ses dépendances** (`Risk.computed_fields`, #250). WF-IHM-0030 veut que le refus
d'une saisie sur la gravité ou la provision d'un risque nomme ce dont elles dépendent, et
`getComputedValueDependencies` ne connaît que les champs d'un nœud. Chaque risque rend, pour sa
gravité et sa provision, dans cet ordre, les règles qui les calculent : `own_estimate`, la
gravité, total de son devis propre, et `severity_and_probability`, la provision, cette gravité
pondérée par la probabilité (WF-RIS-0010), deux codes ajoutés à `ComputedDependency`. Ce sont des
constantes, légères : aucun appel au refus, et aucune ligne nommée — le devis propre est une
structure à part, que la grille des risques ne montre pas. Écarté : étendre
`getComputedValueDependencies` aux risques, un appel de plus pour dire deux phrases fixes.

**Ce qui reste ouvert.** `ExportRequest.revision_id` reste facultatif, la révision prise par le
serveur quand il est nul : la commande qui dit l'export disponible est celle de la révision lue,
et le contrat ne dit pas laquelle juge un export demandé sans révision — suivi en #359. Les
commandes d'un risque (`Risk.available_commands`, #244) sont décidées et réalisées avec EP-08.

## Ce que les lectures nomment (EP-02/L18)

Décisions de l'utilisateur du 2026-10-05, consignées sur #311, #297, #247, #326, #319 et #327.

**Les paramètres d'un signal et d'une alerte sont typés** (#311). `PilotHealth.signals[].params`
et `Alert.params` étaient des objets libres : l'écran ne pouvait dire ni « 11 semaines sans revue »,
ni le jalon dépassé, ni le composant indisponible. Ils portent, comme `Computable.params`, des
propriétés facultatives typées, et leur description dit lesquelles chaque code porte :
`weeks_since_last_mark` pour `review_overdue` ; `lineage_id`, `milestone_label` et
`reference_date` pour `contractual_milestone_overdue` — le libellé du jalon le nomme, l'écran n'a
pas à le chercher ; `component` pour `component_unavailable`, `used_bytes` et `available_bytes`
pour `storage_nearly_full`. Les autres codes ne portent rien. Exemple : `system_status_storage_full`, le stockage presque
plein, en vigilance, l'alerte disant l'espace employé et l'espace libre. Le composant est nommé
(`PlatformComponent`), que `ComponentHealth.component` emploie aussi : un seul jeu de libellés.
Écarté : une union discriminée par code, plus lourde à engendrer pour le même contrôle.

**Un nœud d'organisation a un code et une profondeur, et l'arbre se lit dans son ordre** (#297).
`OrgNode.code`, exigé, est le code unique de WF-REF-0070 : écrit à la création et à la
modification (`OrgNodeWrite`), un code déjà porté, désactivés compris, est refusé par 409,
`ALREADY_EXISTS`. `OrgNode.level` est résolu à la lecture, 1 pour une racine. `listOrgNodes` rend
l'arbre en ordre de profondeur — chaque nœud suivi de ses descendants —, les frères triés par
libellé, comparé dans l'ordre des points de code Unicode — le plus simple, et le même pour
tout lecteur ; une recherche rend aussi les ancêtres des nœuds retenus, pour que l'arbre se lise sans
trou. **Relever d'un nœud, c'est relever de lui ou de l'un de ses descendants**, pour les quatre
filtres `org_node_id` : `getProjectWorkload`, `listResourceRoles`, `listUsers` et le portefeuille
(`PortfolioOrgNode`), comme WF-DEV-0070 l'entend (« les rôles qui en relèvent »). L'exemple
`org_nodes` porte les codes et les niveaux, dans l'ordre de l'arbre.

**Les indicateurs et les courbes se lisent pour une révision** (#247). `getProjectIndicators`,
`getCostCurve` et `getEarnedValueCurves` prennent `revision_id`, comme les indicateurs de devis :
absent, ou la révision en cours, le calcul du jour ; une révision marquée, le calcul à la date
de son marquage — les indicateurs conservés à son marquage (WF-DAT-0040), `is_stored` vrai, les
courbes, que rien ne conserve, recalculées à cette date, `is_stored` faux. Une révision marquée
avant l'état En cours n'a conservé que le total de son devis, « sans aucun indicateur projet »
(Vérif de WF-DAT-0040) : les trois lectures la refusent par 409, `STATE_FORBIDS_OPERATION`, comme
un projet qui n'est pas en cours (exemple `project_indicators_offer`), mais sans `params.state` :
celui-ci dit l'état du projet qui interdit l'opération (EP-02/L15), et le projet est ici en cours,
c'est la révision qui est antérieure (décision de l'utilisateur, 2026-10-05). `as_of` choisit déjà la
révision par sa date : les deux ensemble sont refusés par 422, `VALIDATION_FAILED`, `fields` sur
`/query/revision_id`. **Point ouvert, à décider par l'utilisateur** : recalculées, les courbes
d'une révision marquée peuvent s'écarter de ses indicateurs conservés — une pièce importée après
le marquage, datée d'avant lui, compte dans le coût réel de la courbe et non dans les indicateurs.
Le contrat le dit tel quel, sans trancher entre des courbes conservées au marquage et des courbes
recalculées. Exemple : `project_indicators_marked`, la référence marquée le 1er février
2026, avant que rien ne soit planifié ni dépensé — ni indice de coût ni indice de délai — : sur
l'écran de cette révision, les indicateurs sont les siens, et l'évolution des indices, toujours
calculée au jour sur la révision en cours, l'est sur une autre.

**Les mois du plan de charge agrégé sont en tête de la réponse** (#326). `PortfolioWorkload.months`,
exigé, porte les mois de l'horizon, croissants et sans trou ; chaque rôle porte un mois par mois de
cette liste, dans le même ordre, un mois sans charge compris — comme les années de la grille des
taux (`HourlyRateGrid.years`). L'écran tire ses colonnes de `months`, non du premier rôle.

**Les champs d'un écart d'import sont des colonnes** (#319). `ImportDifference.fields` nomme les
champs d'un écart `updated` comme les colonnes de leur grille, que le front rend par son catalogue
(WF-ARC-0110) : `NodeColumn` pour une tâche, une ligne de devis ou une liaison — une liaison changée
de type ou de décalage par `predecessors`, la colonne qui la présente —, et `ActualCostColumn`,
nommée comme le tri de `listActualCosts`, pour une ligne de coût réel : sa date et son numéro de
pièce, son montant, son sous-projet, les quatre attributs que porte le fichier (WF-CRE-0010). Le
catalogue d'un champ se choisit par l'objet de l'écart (`target`). Exemple :
`import_actual_costs_analysed`, une extraction d'avril rejouée le 2 juin, dont la facture
FA-2026-0412 passe de 1 800 à 1 850 — mise à jour sur son montant, son exclusion préservée
(WF-INTF-0140).

**Le périmètre d'une vue du portefeuille nomme son nœud** (#327). `PortfolioScope.org_node_label`,
exigé, nul sans nœud, résolu à la lecture, désactivé compris (WF-REF-0150) : l'en-tête d'une vue
dit le nœud retenu sans joindre `listOrgNodes` (WF-ARC-0020). Exemple :
`portfolio_workload_org_node`, le plan de charge agrégé restreint à la direction technique, dont les
deux rôles, du bureau d'études électricité, son descendant, restent retenus. Les résumés des exemples qui retiennent
aussi les projets en chiffrage disent que la requête les a ajoutés au périmètre par défaut, les
projets en cours (WF-PTF-0010), qui reste celui du contrat. `CashOutMonth` dit enfin ce que montrait
`portfolio_cash_out` : un mois qui précède celui de la date de calcul ne porte que le passé, un mois
qui le suit que l'avenir, et le mois de la date de calcul les deux.

## L'univers témoin : le socle (EP-02/L20)

**Le témoin se décrit une fois** (#287, décisions de l'utilisateur du 2026-10-05). Les premiers
exemples décrivent un seul projet, PRJ-001, à un seul instant, aujourd'hui : le 3 juin 2026 à
14 h 05 UTC. `wftools.mockwitness` en est la source unique : cet instant, la chronologie du projet
(de l'installation au 1er septembre 2025 aux imports de coûts du jour), les rôles qu'emploient ses
lignes et leurs calendriers — lus dans `resource_roles` et `calendars`, écrits à la main, jamais
recopiés —, et son cœur lisible : le groupe « Études », le lot « Poste de commande » et le
sous-arbre fusionné par la survenance de 752, aux identifiants fixes (le nœud 5nn, sa lignée 6nn)
et aux chiffres des Vérif — 12,5 h × 80 = 1 000, 1 234,56, la provision de 500 de 751, des
lignes de 120 et 80 budgétées 36 et 24 (WF-RIS-0060). Un autre exemple nommé est une autre lecture
de cet état, un instant antérieur de la même chronologie, la suite d'une écriture faite
aujourd'hui, ou une variante contrefactuelle déclarée.

**Une famille d'identifiants par nature d'objet, sur des plages disjointes**
(`mockwitness.IDENTIFIERS`, C16) : les identifiants écrits à la main par centaines — projets,
révisions, structures, comptes, référentiel, nœuds et lignées, rôles d'habilitation, postes du
lotissement, risques, sous-projets, sauvegardes, tâches de fond, collages et corrélations —, ceux
qu'ils écrivent en hexadécimal — imports et téléversements (…0a01), lignes de coût réel (…0c01),
imports de coûts réels (…0c11) — et les familles engendrées, dont le générateur tire désormais
ses numéros. Un test confronte chaque identifiant de `fixtures/api` à la famille de sa clé
(`node_id`, `backup_id`…) ; les empiètements d'aujourd'hui y sont déclarés, et leur liste ne
fera que décroître : le poste 701 sur les rôles d'habilitation ; les tâches de fond 901 à 905,
les collages 911 et 912 et la corrélation 913 sur les sauvegardes ; les corrélations 921 à 927
sur les tâches de fond. Ils seront ramenés sur leur plage avec leurs exemples (L24, L25).

**Les dates se calculent en heures de travail sur le calendrier applicable**
(`wftools.mockcalendar`, WF-PLA-0010, WF-PLA-0160) : une durée et un décalage convertis en heures
se placent heure après heure, chaque jour selon le moins généreux des calendriers des rôles d'une
tâche. **Le rôle actif 454 « Monteur câbleur »**, de l'atelier de câblage, catégorie Ingénierie
électrique, est sur la semaine de quatre jours de dix heures (482) : l'univers a désormais deux
calendriers employés, et un changement de rôle peut redater une tâche.

**La structure suit en EP-02/L27** (#376) : la structure de mille tâches datée en heures, le cœur
en tête, ses compteurs du §4.6.2 gardés, puis EP-02/L21 à L26. Deux décisions de l'utilisateur
la cadrent déjà : le cœur lisible est **relié au réseau engendré**, pour que ses marges et le
chemin critique aient un sens ; la **réception usine reste au 30 juin 2026** (C13). Jusque-là,
la structure des volumes reste celle d'EP-02/L16, datée en jours ouvrés au 16 mars.

## Collage et annulation

**Le collage depuis un tableur suit exactement la forme d'un import** : `paste-preview`
rend un plan avec les lignes acceptées et rejetées, `paste` l'applique sur confirmation.
WF-IHM-0050 demande le même contrôle avant écriture que WF-INTF-0080 ; autant la même
forme.

**Un bloc plus large que la grille est refusé à l'aperçu**, par un 422 `PASTE_TOO_WIDE` dont
`params.max_columns` dit combien de colonnes la grille offre à partir de la colonne visée
(EP-02, US-0130). Le code et son paramètre existaient sans qu'aucune réponse de `previewPaste`
ne les déclare : WF-IHM-0050 veut que ce refus se dise, avant que rien ne soit écrit. Le serveur
ne connaît ni les colonnes affichées ni leur ordre : `max_columns` compte les colonnes de la facette
du nœud visé à partir de la colonne visée, dans l'ordre de `NodeColumn` (EP-02/L8, #200), et le
front garde une garde locale sur ce qu'il montre.

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

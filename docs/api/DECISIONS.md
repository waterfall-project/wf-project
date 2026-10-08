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
peut saisir le devis sans pouvoir toucher au planning. Les coûts réels ont leurs commandes sur
le projet ; la saisie des risques est une commande de la révision (`edit_risks`), et chaque
risque porte les siennes, avec les conditions que son état lui fait manquer
(`Risk.available_commands`, EP-02/L30, #244) — l'appel envoyé malgré la liste reste refusé par
son code d'erreur. `getProjectNextState` ne couvrait que les
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
au contrat ; ne rien changer, qui laisserait le back lourd. `editable_fields` pesait 1,03 Mo sur
5,70 Mo du volume de mille tâches, mesuré avant L30 (#238) ; une grille qui ne l'emploie pas l'omet par `fields` ;
une table par nature de nœud n'est décidée que si la seconde du §4.6.2 n'est pas tenue, mesurée
en EP-13 (EP-02/L30).

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
n'a jamais existé, la révision de la spécification du 2026-10-04 l'a dit : la projection de
décaissement est « la lecture en décaissements de la courbe en S »). `getProjectCashOut` et
`CashOut` disparaissent : `getCostCurve` prend `payment_delays`, qui décale chaque montant du
délai de paiement de sa ligne et ajoute les provisions des risques identifiés, et la réponse le
dit (`payment_delays`) et détaille alors les mois (`cash_out_by_month`, nul sinon). Le mois de
décaissement est un schéma partagé (`CashOutMonth`), que la courbe en S du portefeuille
réemploie (WF-PTF-0100, voir « Révision de la spécification du 2026-10-04 ») : le portefeuille
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

**La survenance d'un risque ne budgète rien** (WF-RIS-0060, révisée le 2026-10-04 ; la
répartition de la provision au prorata, décidée ici le 2026-10-03, est abandonnée) : les
descriptions de `declareRiskOccurrence` et de `RiskOccurrence` disent que le devis propre est
fusionné dans la structure principale de la révision en cours, chaque ligne à montant budgété
nul et réestimée à son montant, la ligne de provision retirée, sans marquage ni déplacement de
la référence ; l'exemple `nodes_risk_occurred` de `listNodes` montre la structure obtenue — 0 et
0 pour 120 et 80.

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

**Le total général des provisions est rendu, et la réserve en regard** (`ProvisionTotals.total`,
`ProvisionTotals.reserve`). WF-RIS-0040 voulait les trois totaux distincts et leur somme ; sa
révision du 2026-10-04 les veut « en regard de la réserve pour risques » (WF-RIS-0050) : le
front ne somme rien (WF-ARC-0020), le serveur rend donc le total et la réserve de la révision
de référence, sur les mêmes risques retenus que les trois autres (décision de l'auteur du
2026-10-06 : le total reste).

**Exemples** : `risks` (trois risques, un par état — le survenu est celui de
`nodes_risk_occurred`, gravité 200 à 30 %, son devis propre fusionné à budgété nul et sa ligne
de provision retirée — les quatre totaux et la réserve de la référence, 910), `risks_empty`,
`risk`, `risk_occurred_detail` (le risque survenu, sa ligne de provision retirée),
`risk_reviews` (la probabilité passée de 25 à 40 %, la gravité de 1 000 à 1 250), `risk_matrix`
(les seize cases, les bornes, les trois risques placés) et `risk_coverage` (la couverture du
témoin : réserve 910, provisions restantes 500, coût des survenus 200, écart +210), dans
l'univers des autres exemples.

## Les exemples des courbes (US-0240/L2)

**Les lectures des courbes ont leurs exemples** (#246, autorisation de l'utilisateur du
2026-10-04 : un lot d'écran ajoute les exemples des opérations qu'il consomme). Sans eux, le faux
back tirait de leurs schémas des valeurs sans rapport avec l'univers témoin, et les tests du front
n'avaient rien du contrat à lire. Tous sont au 16 mars 2026, sur la révision courante du projet
témoin, et suivent les montants de `project_indicators` et de `remaining_indicators` — budget de
référence et reste à engager de 100 000, portés par les études de détail du 2 mars au 10 avril,
valeur planifiée de 33 333,33 à la date de calcul, aucun coût réel ni valeur acquise. Ils ne
suivent pas le devis de `nodes_estimate`, d'un autre univers. Ils sont depuis engendrés au 3 juin
2026 sur un seul univers : voir « L'univers témoin ». `milestone_tracking` (`getMilestoneTracking`) suit deux jalons, la réception des études et
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
`nodes_estimate`, non les montants de `project_indicators` : ils sont de l'univers du devis. Ils
sont depuis engendrés sur un seul univers, au 3 juin 2026 : voir « L'univers témoin ». Les deux rôles sont ceux de `resource_roles`,
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

**Exemples** : `actual_costs`, `actual_costs_page`, `actual_costs_subproject` et
`cost_imports` sont engendrés depuis la description du témoin, au 3 juin 2026 — voir « L'univers
témoin : coûts, échanges, tâches, comptes (EP-02/L25) » ; restent écrits à la main
`actual_costs_empty` (aucun import), `cost_imports_beyond` (une page demandée au-delà de la fin) et
`cost_imports_empty`.

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

**Exemples**, dans l'univers des autres : `file_upload`, `import_analysing`, `import_analysed`,
`import_planning_mismatch`, `imports`, `imports_page`, `imports_empty`, `task_export_*` et
`task_import_*`. Leurs instants et ce qu'ils visent sont recalés sur la chronologie du témoin par
EP-02/L25 — voir « L'univers témoin », « Coûts, échanges, tâches, comptes ».

## Les exemples du portefeuille (US-0240/L3)

**Les vues du portefeuille ont leurs exemples**, faits par le lot de leurs écrans sur
l'autorisation de l'utilisateur du 2026-10-04 (un lot d'écran ajoute les exemples des
opérations qu'il consomme). Sans eux, le faux back tirait de leurs schémas des valeurs sans
rapport avec les trois cents projets de `getPortfolioProjects`. **Ce qui se somme des lignes de
la liste est engendré avec elle** (`make mock-data`, `fixtures/api/volume/`), au 3 juin 2026
depuis EP-02/L26 :
la valeur (`portfolio_value`, `getPortfolioValue` : le carnet des projets en cours, le pipeline
brut et pondéré des offres, rien de réalisé — aucun projet du périmètre n'est terminé —, et le
taux de transformation du Vérif de WF-PTF-0050, quatre offres gagnées sur dix sorties du
chiffrage dans l'année) ; la performance (`portfolio_performance`, `getPortfolioPerformance` :
chaque indice en rapport des sommes, la valeur acquise, le coût réel et la valeur planifiée de
chaque projet tirés de son budget et de ses indices — ceux du projet témoin, de
`project_indicators` —, la répartition par zone comptant chaque projet une fois par indice, le
projet témoin compté nominal, et quatre trimestres d'évolution — de 2025-T3 à 2026-T2 depuis
EP-02/L26 —, le premier non calculable, faute de coût réel et de valeur planifiée : aucun projet
n'avait encore commencé, ce que la courbe en S tient aussi) ; la structure des coûts
(`portfolio_cost_structure`, `getPortfolioCostStructure` : le budget et le reste à engager par
nature, dont les parts somment à un, et la main-d'œuvre du bureau d'études électricité, le nœud
des deux rôles qui travaillent sur les projets — le monteur câbleur, de l'atelier de câblage,
n'en a pas) ; les risques (`portfolio_risks`,
`getPortfolioRisks` : le registre du projet témoin et jusqu'à trois risques identifiés par autre
projet en cours, chacun tiré d'abord dans une case de la matrice, puis sa probabilité et sa gravité
dans les bornes des niveaux de cette case (`risk_matrix`), sa provision la gravité pondérée par la
probabilité (WF-RIS-0010) ; les dix plus lourds avec leur projet) ; et la deuxième page de cinquante
projets de la liste (`portfolio_projects_page`).
**Ce que la liste ne porte pas s'écrivait à la main** : `portfolio_workload`
(`getPortfolioWorkload`), `portfolio_cost_curve` (`getPortfolioCostCurve`, qui a remplacé
`portfolio_cash_out` et `getPortfolioCashOut` le 2026-10-06) et `pilot_health`, à une autre
échelle et, pour le dernier, à un autre instant. Ils sont engendrés depuis les trois cents
projets, au 3 juin 2026, par EP-02/L26 : voir « L'univers témoin », « Le portefeuille à
l'échelle ». `portfolio_projects_empty` est la liste filtrée qui ne retient aucun projet.

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
coûts réels l'a été. L'exemple `portfolio_workload` le porte. `portfolio_cost_curve_credit`, calculé au
31 décembre 2025 en décaissements, montre un mois net négatif — les avoirs de décembre importés
avant ses factures, que l'import de janvier apportera — : un décaissement est un `Money`
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
La spécification dit seulement que « la taille d'un avatar est bornée par l'application »,
au §4.4.1. Le plafond technique de 8 Mio est celui que la revue d'EP-02/L13 a proposé : le front
règle d'avance, par un réglage statique de Next, la taille de corps de ses actions serveur
(`bodySizeLimit`), et ne peut la régler qu'au-dessus d'un maximum déclaré, l'enveloppe du
formulaire comprise. Huit mébioctets restent sous cette borne, et la taille admise reste un
réglage de l'installation sous ce maximum.

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
ligne de provision présente dans la révision de référence porte la provision qu'elle y avait,
mais ce montant compte à la réserve pour risques, jamais au budget de référence, qui est « la
somme des montants budgétés hors lignes de provision » (glossaire, WF-RIS-0050 révisée le
2026-10-04). Il se lit dans les indicateurs, jamais en sommant les montants des lignes : le
montant budgété d'une tâche et `NodeTotals.budgeted_amount` comptent les lignes de provision,
les indicateurs les en retirent. Une ligne issue d'un risque survenu ou ajoutée après la
référence est budgétée à zéro. #347 est close par la révision : la provision d'un risque écarté
sort du reste à engager sans toucher la référence, celle d'un risque identifié après la
référence n'a pas de part dans la réserve.

**Une marche de la courbe porte son montant** (`CurveSeries.steps[].amount`, #285), signé, ce dont
le budget de référence change à sa date, et non le budget après elle, que la série
`reference_budget` porte ; c'est ce que `cost_curve_amendment` montrait. Le nom reste.

**Les structures des risques témoins ont leurs exemples** (#252) : `structures_amendments` porte
les devis propres du retard de livraison des armoires et de l'indisponibilité de l'automaticien,
nommés par `risks`. La chronologie des risques témoins et des révisions — quand le retard est
survenu, dans quelle révision en cours son devis propre a été fusionné — n'était pas tenue par
les exemples : EP-02/L23 l'a fixée (« L'univers témoin », « Révisions et risques »).

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
qui redate (EP-02/L22, « L'univers témoin »).

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

**Ce qui restait ouvert** a été tranché par EP-02/L30 : `ExportRequest.revision_id` est exigé
(#359), et les commandes d'un risque sont au contrat (`Risk.available_commands`, #244), leur
réalisation restant en EP-08.

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
projets en cours (WF-PTF-0010), qui reste celui du contrat. `CashOutMonth` dit enfin ce que montre
`portfolio_cost_curve_payment_delays` : un mois qui précède celui de la date de calcul ne porte que
le passé, un mois qui le suit que l'avenir, et le mois de la date de calcul les deux.

## Révision de la spécification du 2026-10-04 (PR #328, fusion du 2026-10-06)

La seconde revue de la spécification (#211, #212, #253 à #283) change le modèle des provisions et
quelques lectures ; le contrat suit, les décisions de l'auteur du 2026-10-06 tranchant ce que le
texte laissait ouvert.

**Les provisions ne font jamais partie du budget de référence** (WF-RIS-0050). La révision de
référence conserve leur somme comme réserve pour risques, et la couverture des risques — la
réserve face aux provisions des risques identifiés et au coût réestimé des lignes issues des
risques survenus, écart signé — est une lecture : `RiskCoverageTotals` porte les quatre montants,
`getProjectRiskCoverage` (`GET /projects/{p}/risks/coverage`, dans la révision nommée par
`revision_id` comme les autres lectures des risques) les rend avec leur contexte (`RiskCoverage`),
`RemainingIndicators.coverage` les répète pour l'écran du reste à engager (WF-RAE-0020), et
`PortfolioRisks.coverage` les somme sur les projets en cours (WF-PTF-0090). `ProvisionTotals`
porte la réserve en plus du total général. `CurveSeries.steps[].cause` ne connaît plus que
`amendment` : seul l'avenant déplace la référence (WF-REV-0040), et `RiskOccurrence` n'a plus que
`confirmed`, la survenance ne marquant aucune révision. `budget_change.cause` à `risk_occurred` et
`last_risk_dismissed`, et `version_name` de la survenance, sont retirés.

**La courbe en S du portefeuille est une seule opération** (WF-PTF-0100 ; FBS-2.6 renommée).
`getPortfolioCostCurve` (`GET /portfolio/cost-curve`) rend `PortfolioCostCurve` : le périmètre,
les trois séries cumulées sommées — `reference_budget`, `actual_cost`, `project_manager_projection`
—, et, demandée avec `payment_delays` comme `getCostCurve` au niveau du projet, les décaissements
que les projets rendent, détaillés par mois (`cash_out_by_month`, nul sinon). `getPortfolioCashOut`
et `PortfolioCashOut` disparaissent ; la permission de FBS-2.6 s'appelle `portfolio_cost_curve`.
Écarté : garder deux opérations, l'une pour les courbes, l'autre pour les décaissements — la vue du
portefeuille a les mêmes modes que celle du projet, et le portefeuille somme sans recalculer.

**Les codes d'états sont ceux de la spécification.** Elle donne désormais les codes des états d'un
projet (WF-CYC-0010, tableau), d'une tâche, d'une révision et d'un compte ; les enums du contrat
les portaient déjà. L'état d'un compte reste `User.is_active`, booléen documenté comme portant
`active` et `deactivated` (décision de l'auteur : changer la forme coûte plus qu'elle n'apporte).
Les risques, les natures, les types de liaison et les zones n'ont pas de code dans la
spécification : ceux du contrat restent.

**Ce que la révision demande et que le contrat ne portait pas encore** a été ouvert en constats —
#381 à #389 — et fermé par EP-02/L29, section suivante.

## Ce que la révision de la spécification demande (EP-02/L29)

Les neuf constats du bilan de la spécification révisée (#381 à #389, #392), chacun avec la forme
retenue, l'option écartée et l'exigence qui le dicte. Une décision que ni la spécification ni le
constat ne tranchaient est dite comme telle.

**La révision porte son année de référence** (`Revision.reference_year`, #381 ; WF-REV-0060,
WF-REV-0090, WF-DEV-0010). Un entier `Year`, exigé, en lecture seule : fixé par le serveur à la
création à l'année courante, conservé par la révision et son instantané (WF-REV-0030), jamais
saisi — `RevisionCreate` n'en porte pas. `getMissingRates`, `RateUpdateProposal.target_year` et le
montant « à l'année de référence » de la grille de devis (`base_amount`) le citent. Les révisions
de 2026 des exemples portent 2026 ; l'offre v1.0, marquée en décembre 2025, porte 2025. Écarté : un
champ dans `RevisionSnapshot`, où il n'aurait été lu qu'avec l'instantané entier, quand
l'historique des révisions le présente (WF-REV-0090).

**Une récapitulative porte son poste ou son lot** (`TaskFacet.order_item_id`, `work_package_id`,
`work_breakdown_label`, #382 ; WF-PLA-0130, WF-PLA-0040, WF-DEV-0060, WF-PRJ-0030). Les noms sont
ceux du tableau de correspondance du §4.4.1 — `order_item`, `work_package` —, non `lot_id` que le
constat écrivait. Deux identifiants nullables et exclusifs sur la facette de lecture, les mêmes sur
`TaskFacetWrite` et `TaskFacetUpdate`, `null` retirant le rattachement ; le libellé du poste ou du
lot porté, résolu à la lecture, pour que la grille ne lise pas le lotissement (WF-ARC-0020) ; une
colonne `work_breakdown` de `NodeColumn`, dernière des colonnes de la tâche — après `predecessors`,
pour ne déplacer aucune colonne de ligne dans l'ordre d'un collage (WF-IHM-0050) ; deux champs
d'`EditableField`, que seules les récapitulatives nomment ; deux filtres de `listNodes`,
`order_item_id` et `work_package_id`, qui retiennent le sous-arbre de la récapitulative rattachée ;
`generatePlanningSkeleton` dit que ses récapitulatives sont rattachées (WF-PRJ-0030). Les refus
sont des motifs par champ de `VALIDATION_FAILED`, dans la convention du catalogue : `SUMMARY_TASK_REQUIRED`
— retiré par EP-02/L30, toute tâche portant désormais le rattachement (#411) —,
`UNKNOWN_WORK_BREAKDOWN_ITEM`, `WORK_BREAKDOWN_ITEMS_EXCLUSIVE` et
`WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED`, celui-ci nommant la récapitulative qui porte déjà le poste
(`fields[].params.attached_node_id`, exemple `task_attach_refused` de `updateTaskFacet`) — le Vérif de WF-PLA-0130. Les trois propriétés de lecture sont
facultatives, comme `started_on` ou `calendar_id` sur la même facette, et non exigées : la facette
n'exige que ce que toute tâche porte, et `fields` les laisse hors des lectures qui ne les
affichent pas. Écartés : un 409 pour l'unicité, qui n'aurait pas désigné le champ ; une seule
propriété `work_breakdown_item_id` sans dire si c'est un poste ou un lot. L'exemple : le lot
« Poste de commande » du cœur (nœud 551) porte le poste unique du lotissement, « Fourniture et
montage des armoires » (`mockwitness.ASSEMBLY`), dans `nodes_estimate`, engendré par `make
mock-data` depuis le cœur (EP-02/L21), et dans les écritures écrites à la main qui le rendent en
ancêtre (`estimate_line_updated`, `node_deleted`, `task_renamed`). Le poste passe sur sa plage
d'identifiants (711, au lieu de 701, que les rôles d'habilitation occupent : l'empiètement C16
disparaît), et les totaux par poste du devis le nomment ainsi ; les récapitulatives de tous les
exemples et du volume nomment les deux champs parmi ceux qu'elles acceptent.

**Le compte rendu d'import dit l'aller-retour** (#383 ; WF-INTF-0040, WF-INTF-0060, WF-INTF-0080,
WF-INTF-0100, WF-INTF-0120, WF-PLA-0130). `ImportDifference.change` gagne `kept` : une tâche
démarrée ou terminée que le fichier ne porte plus, ou une ligne d'une telle tâche, conservée et
signalée, sans `fields`. `ImportReport` gagne trois tableaux exigés, vides quand il n'y a rien à
dire — sur le modèle de `rescheduled`, pour que l'écran n'ait pas à distinguer l'absence du vide :
`ignored`, ce que l'import a lu sans l'importer, par nature (`ImportIgnoredKind` : ressources,
calendriers, avancement, coûts, champs personnalisés, contraintes de date), compté et nommé quand
cela se nomme ; `completed_tasks`, les tâches qu'un import de reste à engager termine, nommées,
leur date nulle tant que l'import n'est pas appliqué — c'est le jour de l'application (WF-PLA-0130)
— ; `date_mismatches`, les tâches dont le fichier date ou dure autrement que Waterfall ne les
recalcule, par leurs colonnes. L'écart de dates n'est plus un motif de confirmation :
`date_or_duration_mismatch` quitte `requires_confirmation_reasons`, qui ne garde que les deux motifs
des coûts réels, et un aller-retour sans modification rend `differences` et `date_mismatches`
vides (WF-INTF-0060). `TaskFacet.external_id`, l'identifiant MS Project d'une tâche créée à
l'import, nullable, jamais saisi. Sur un écart de liaison, `lineage_id` et `label` sont ceux du
successeur, dont la colonne `predecessors` porte la liaison ; `predecessor_label` vient avec
EP-02/L30 (#393), qui ferme #364.
Écartés : une `difference` par tâche ignorée, qui aurait mêlé ce que l'import écrit et ce qu'il
laisse ; un compte seul pour les éléments ignorés, qui n'aurait pas nommé la ressource que
l'utilisateur cherche (Vérif de WF-INTF-0040). Exemples : `import_planning_mismatch`, réécrit en
aller-retour sur les lignées du cœur — la « Revue de conception » (624) rallongée, sa fin
recalculée en écart, les « Études de détail » (622), terminées, conservées, deux ressources, un
calendrier et l'avancement ignorés — ; `import_remaining_analysed`, nouveau, un reste à engager
du « Câblage des armoires » (652) qui réestime ses deux lignes à zéro sans le terminer : sa ligne
de provision, calculée depuis le risque 751 toujours identifié, garde son reste (WF-RIS-0010,
WF-RAE-0040), et `completed_tasks` est vide — aucune tâche démarrée du cœur n'est terminable par
un import, et la liste non vide n'a pas d'exemple ; un test du cœur exige qu'un exemple écrit à
la main nomme un libellé du cœur par l'identifiant et la lignée du cœur ;
`import_actual_costs_analysed`, qui dit son motif de confirmation.

**Les trois permissions de WF-ADM-0100 entrent au catalogue** (`project_create`,
`revision_abandon`, `structure_merge`, #384). Les codes suivent ceux du catalogue — l'objet, puis
l'action, comme `revision_mark` — et `structure_merge` est le nom que `BackgroundTaskRef.kind`
donne déjà à la fusion. Abandonner et fusionner sont des actions irréversibles ; créer un projet
est structurante, comme consulter tous les projets : l'énumération range les huit irréversibles
dans l'ordre où WF-ADM-0100 les nomme, puis les deux structurantes, pour que la matrice des
permissions les groupe par nature sans couper un groupe. `RevisionCommand` dit que `merge_structure`
et `abandon` sont gardées par leur permission propre — « un rôle disposant du marquage mais non de
la fusion refuse de fusionner un différentiel » —, et `ProjectCommand` que la survenance d'un
risque emporte la fusion sans exiger `structure_merge`. Les rôles prédéfinis suivent : le chef de
projet crée un projet, abandonne et fusionne ; les sessions qui portaient tout le catalogue le
portent encore. Écarté : garder `revisions.write` pour l'abandon, ce que la révision de la
spécification a précisément défait.

**Un risque non cité se supprime** (`deleteRisk`, #385 ; WF-RIS-0020, WF-PLA-0140). `DELETE
/projects/{p}/risks/{r}` sous `risks.write` et la commande `edit_risks`, 204 avec le devis propre
et la ligne de provision ; refusé par 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition`
nommant `risk_not_cited`, condition nouvelle de `CommandCondition`, dès qu'une révision marquée cite
le risque — il s'écarte alors par `reviewRisk`. `deleteTimeline` existait déjà (`paths/projects.yaml`,
le constat le cherchait dans `revisions.yaml`) : rien à ajouter pour la chronologie. Le risque
n'a pas d'`available_commands` (#244, EP-08) : la condition se dit par le refus, et
`Risk.available_commands` n'est pas créé ici (EP-02/L30). Exemple : `risk_delete_cited`, le risque
de reprise du câblage, cité par la référence.

**La ligne de coût garde le code de sous-projet de son OTP** (`ActualCostLine.subproject_code`, #386 ;
WF-CRE-0010, WF-CRE-0020). Il était résolu depuis le sous-projet imputé, donc nul dès que le code
ne correspondait à rien — et perdu. Il est désormais le code lu dans l'élément d'OTP, conservé
tel quel, toujours renseigné quand l'OTP en donne un, nul seulement sans partie sous-projet ;
`subproject_id` et `subproject_label` restent nuls pour une ligne au code inconnu, imputée au seul
projet. Le réimport qui change l'OTP recalcule l'imputation, et le compte rendu le dit par un
écart `updated` sur la colonne `subproject` d'`ActualCostColumn` (WF-INTF-0140). Les lignes de
`actual_costs` portent SP-CAB, SP-AUT et SP-REC, hors sous-projet ; `import_actual_costs_analysed`
réimpute l'avoir au Poste de commande. La grille des coûts réels, qui déduisait « hors
sous-projet » du code nul, le déduit du libellé nul et montre le code à côté.

**Les tables plates se trient** (#387 ; WF-IHM-0060). `sort_by` et `sort_order` sur `listUsers`
(nom, prénom, adresse, origine, rôles, nœud, état) et `listAccessRoles` (libellé, nature, porteurs),
sur les colonnes que leurs écrans présentent, à la manière de la liste du portefeuille ; les quatre
listes plates du référentiel qui n'en avaient pas les gagnent de même — `listResourceRoles`,
`listCalendars`, `listCostTypes`, `listCostCategories`. Les textes se comparent dans l'ordre des
points de code Unicode, et une valeur nulle vient après les autres dans l'ordre croissant, comme
pour les coûts réels (EP-02/L15). Laissées sans tri : `listOrgNodes`, un arbre en ordre de
profondeur (EP-02/L18) ; `getHourlyRateGrid`, une grille dense ; les listes d'un projet —
sous-projets, contributeurs, chronologies —, hors du constat, à traiter avec leurs écrans.

**Un administrateur obtient le lien de fixation du mot de passe** (`createPasswordSetupLink`,
`POST /users/{id}/password-link`, `PasswordSetupLink`, #388 ; WF-ADM-0140, WF-EXP-0020,
WF-CMP-0030). Un `POST` sur le compte, qui engendre un lien nouveau — à usage unique, valable une
heure, le précédent cessant de valoir — et le rend une seule fois, avec son expiration ; 409 pour
un compte qui n'est pas local ou désactivé, 503 quand le fournisseur d'identité ne répond pas.
Sous `users.write` : WF-ADM-0100 fixe le catalogue et ne nomme pas cette action parmi celles à
permission propre, et une permission nouvelle serait une modification de la spécification —
écarté. Chaque demande est inscrite au journal d'audit, sans le jeton (WF-SEC-0030). Le lien vise
l'adresse du front que #154 demandait de fixer : `<adresse publique du front>/login/reset?token=<jeton>`,
celle que le front d'EP-02 a posée, l'adresse publique du front étant un paramètre de
l'installation, fixé à son déploiement (WF-EXP-0020), que l'API ne sert pas ; la description de
`requestPasswordReset` dit le même lien pour le courriel. Exemple : `password_setup_link`.

**Les lignes du portefeuille disent si le projet s'ouvre** (`can_open`, #389 ; WF-PTF-0030,
WF-ADM-0110) : un booléen exigé sur `PortfolioProjectRow`, sur les risques les plus lourds de
`PortfolioRisks` et sur les signaux de `PilotHealth`, évalué par le serveur — la permission de
consulter et la qualité de contributeur, ou « consulter tous les projets » — pour que le front
retire le lien sans recopier la règle. Écarté : laisser le front le déduire des permissions de la
session, qui ne connaît pas les contributeurs. Dans le volume (`make mock-data`), le témoin et
l'offre s'ouvrent, et des trois cents projets engendrés chaque septième ne s'ouvre pas
(`mockportfolio.UNOPENABLE_EVERY`), le rang choisi pour que l'un des dix risques les plus lourds
soit d'un projet fermé : la liste est lue par un utilisateur sans « consulter tous les
projets », contributeur des autres — une variante déclarée de la session de la maquette, qui a
tout le catalogue, que le résumé de `portfolio_projects` dit ; les risques les plus lourds en
héritent de leur projet, et `pilot_health`, écrit à la main, s'ouvre.

**Ce qui n'est pas ici.** Les écrans qui consomment ces formes — la colonne et les filtres du
lotissement, les sections nouvelles du compte rendu, le tri des tables, le lien sans `can_open`,
le lien de fixation — sont à leurs lots ; le front n'a changé que là où le client engendré ou les
exemples l'exigeaient : l'ordre des colonnes du contrat (`NODE_COLUMNS`), la cellule de sous-projet
des coûts réels, et les tests qui lisent les exemples.

## Les constats d'EP-02 tranchés (EP-02/L30)

Les constats ouverts pendant EP-02 (#238, #244, #348, #352, #359, #360, #362, #364, #365), chacun
selon la décision de l'auteur du 2026-10-07 portée en commentaire, et les suites dans le contrat de
la spécification modifiée par les PR #410 (#337, #377) et #418 (#411, #402). Une forme que ni la
spécification, ni le constat, ni sa décision ne fixaient est dite comme telle.

**Toute tâche porte son rattachement au lotissement** (#411 ; WF-PLA-0130, WF-DEV-0060). La
restriction aux récapitulatives est levée : `SUMMARY_TASK_REQUIRED` quitte le catalogue, une
feuille accepte `task.order_item_id` et `task.work_package_id` (`editable_fields`, après ses autres
champs, dans l'ordre d'`EditableField`), et une récapitulative qui perd sa dernière subordonnée
garde son rattachement — par `deleteNode`, `moveNodes`, un import ou une annulation. L'exclusivité
et l'unicité restent (`WORK_BREAKDOWN_ITEMS_EXCLUSIVE`, `WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED`) ;
l'échange se fait en une écriture, l'autre champ mis à `null` dans le même corps — un détail du
contrat que la décision lui laissait. Le motif nouveau, `WORK_PACKAGE_OUTSIDE_ORDER_ITEM`, refuse
ce qui sortirait la tâche d'un lot du sous-arbre de la tâche de son poste rattaché : un lot rattaché
hors de ce sous-arbre, un poste rattaché à une tâche qui ne contient pas la tâche de l'un de ses
lots, un déplacement (`moveNodes`, 422 désormais déclaré, `fields` sur le nœud déplacé en cause),
une création (`createNode`, par son parent), une ligne importée (`ImportRejection`), et une saisie
du lotissement qui range un lot sous un autre poste, les deux rattachés (`setWorkBreakdown`, 422
désormais déclaré, `fields` sur le lot, `params.work_package_id` le nommant — décision de l'auteur
à la revue) ; ce dernier refus se juge dans la révision en cours, dont seules les tâches se
déplacent encore.
`fields[].params` nomme la tâche du poste (`order_item_node_id`) et celles des lots
(`work_package_node_ids`, une liste : un poste rattaché peut en laisser plusieurs dehors).
Écarté : nommer les lots par leur identifiant du lotissement, quand c'est la tâche que l'écran
montre. Exemple : `task_attach_outside_order_item`, le groupe « Études » refusé au lot 712 du poste
que porte le « Poste de commande ». Les filtres par poste et par lot de `listNodes` et les totaux par
poste lisent la tâche rattachée, quelle qu'elle soit.

**La marge totale est signée** (#402 ; WF-PLA-0100). Une tâche manuelle borne la fin au plus tard
de ses prédécesseurs : `TaskFacet.total_float` et `NodeSchedule.total_float` peuvent être négatifs,
sans minimum — `Duration.value` n'en posait pas, sa description disait « jamais négative » et dit
maintenant qu'une marge est signée —, et `is_critical` vaut pour une marge nulle ou négative. Le
générateur du témoin applique encore « la tâche manuelle n'impose rien » : son alignement est un
lot du témoin, aucun exemple ne porte de marge négative.

**Une saisie qui laisserait une tâche sans heure travaillée est refusée** (#377 ; WF-PLA-0010) :
422 `TASK_WITHOUT_WORKING_HOURS`, `params.resource_role_ids` nommant les rôles dont les calendriers
ne se recoupent aucun jour, `params.tasks` les tâches en cause, chacune par `project_id`, `node_id`
et `label` — un calendrier ou un rôle du référentiel touche les révisions en cours de plusieurs
projets, et l'écran du référentiel ne lit pas leurs structures. Déclaré sur `createNode` (une
ligne de main-d'œuvre ajoutée), `updateEstimateLine` (un rôle changé), `updateResourceRole` et
`updateCalendar` (un calendrier de rôle modifié), et motif de rejet d'une ligne collée ou importée.
Un code d'erreur et non un motif par champ : la saisie refusée n'est pas toujours un champ de la
tâche. Déclaré aussi, à la revue, sur `moveNodes` (une ligne de main-d'œuvre déplacée change de
tâche porteuse), sur `updateCalendar` et `setDefaultCalendar` pour le calendrier par défaut qui
n'aurait plus d'heure — les tâches sans ligne de main-d'œuvre en relèvent, `resource_role_ids` est
alors vide —, et sur `mergeCostStructure` : un différentiel qui donnerait à une tâche de la
structure principale une telle ligne fait échouer la tâche de fond, `problem.code` à
`TASK_WITHOUT_WORKING_HOURS`, sans rien fusionner. Pas d'exemple : aucune tâche du témoin ne porte
deux rôles, et un calendrier qui ne recouperait celui d'aucun autre n'existe pas au référentiel des
exemples.

**Les risques ont leurs commandes** (#244 ; WF-IHM-0090, WF-RIS-0020, WF-RIS-0060, WF-ADM-0100).
`RiskCommand` — `update`, `review`, `declare_occurrence`, `delete`, une par opération —,
`RiskCommandAvailability` sur le modèle de la révision, `Risk.available_commands` exigé.
`CommandCondition` gagne `risk_not_occurred` (modification, réexamen et suppression d'un risque
survenu) et `risk_identified` (survenance d'un risque qui ne l'est pas), et réemploie
`risk_not_cited` (#385) plutôt que le `risk_not_cited_by_marked_revision` de la proposition, qui
dirait la même chose. Le risque ne nomme que ce qui tient à lui ; la survenance reste gardée par la
seule permission `risk_occurrence` et nomme `may_create_revision` à qui n'a pas `revisions.write`
quand le projet n'a pas de révision en cours, qu'elle créerait ; les conditions du projet restent
sur `ProjectCommand.declare_risk_occurrence`. Exemples : `risk`, `risks`, `risk_occurred_detail`
— tous trois cités par la référence, aucun ne se supprime ; le survenu n'a plus aucune commande
disponible.

**La saisie des risques est une saisie de la révision en cours** (#337, PR #410 ; WF-RIS-0020,
WF-IHM-0110). `edit_risks` passe de `ProjectCommand` à `RevisionCommand`, après les trois autres
saisies, `ProjectCommand` la gardant tant que le projet n'a pas de révision en cours ;
`createRisk`, `updateRisk`, `reviewRisk` et `deleteRisk` écrivent dans la révision en
cours, la créent au besoin, et entrent dans l'historique d'`undoLastChange`, dont le résultat nomme
les risques rendus (`UndoResult.undone.risk_ids`) ; la déclaration de survenance reste hors
annulation. Où vit la commande — décision de l'auteur du 2026-10-07, précisée à la revue : le
projet la porte (`ProjectCommand.edit_risks`) tant qu'il n'a pas de révision en cours, qu'il ait
ou non des révisions marquées, comme les imports ; la saisie crée la révision en cours, et
`may_create_revision` manque à qui ne peut pas la créer. Dès qu'une révision est en cours, la
commande vit sur elle (`RevisionCommand.edit_risks`) et quitte le projet. Une révision marquée ne
la liste jamais, pas même indisponible comme les trois autres saisies : elle est immuable
(WF-DAT-0020), et l'écran montrerait sinon deux commandes de saisie des risques. Écarté : la
porter sur la dernière révision marquée quand aucune n'est en cours, qui aurait fait offrir une
saisie par une révision immuable. Exemples : la révision en cours la porte (`revision`,
`revision_marking`, `revision_importing`, la 102 de `revisions`), les révisions marquées non ; le
projet en chiffrage sans révision (`project_pricing`, sa ligne de `projects`) et le projet en
cours dont la révision courante vient d'être abandonnée (`project_without_current_revision`, de
`getProject`) la portent, le projet qui a une révision en cours non. Le front la compte parmi les
commandes de modification de la révision (`availableEdits`), où elle n'est jamais disponible sur
une révision marquée.

Deux formes du contrat, que la spécification ne dictait pas mot pour mot : la modification d'un
risque (`updateRisk`) est, comme le réexamen et la suppression, une saisie de la révision en cours,
annulable et créatrice de la révision au besoin — chaque révision fige une version des risques,
libellé et devis propre compris (WF-RIS-0030), une modification ne peut donc écrire que dans la
révision en cours ; et la suppression d'un risque survenu est refusée, `risk_not_occurred`, aucune
transition ne partant d'un survenu (WF-RIS-0020). Le 409 de `deleteRisk` ne nomme qu'une condition
(`params.missing_condition`) : `risk_not_occurred` avant `risk_not_cited` quand les deux manquent,
pour ne pas renvoyer vers un réexamen qu'un survenu n'a pas.

**Une ligne de provision ne se crée pas à la main** (amendement de #371 ; WF-DEV-0020,
WF-RIS-0010) : « la création à la main d'une ligne de nature provision est refusée » (Vérif de
WF-DEV-0020). Motif par champ `PROVISION_CATEGORY_RESERVED` de `VALIDATION_FAILED`, sur la
catégorie (`/estimate_line/cost_category_id` à la création, `/cost_category_id` à la
modification), `params.cost_category_id` la nommant ; motif de rejet aussi d'une ligne collée ou
importée. Écarté : un code de premier niveau, qui n'aurait pas désigné le champ. Exemple :
`estimate_line_provision_refused` de `createNode`, une ligne de la catégorie « Provisions pour
risques » (404) créée sous le « Câblage des armoires ».

**Pendant l'application d'un import ou une survenance, la révision en cours est suspendue** (#360 ;
WF-INTF-0080, WF-IHM-0080, WF-IHM-0090, WF-RIS-0060). `no_background_task_running` manque, pendant
l'application (`applying`) d'un import de planning, de devis ou de reste à engager et pendant le
traitement d'une déclaration de survenance, à `edit_planning`, `edit_estimate`, `edit_remaining`,
`edit_risks`, `create_structure`, `merge_structure`, `mark` et `abandon` ; les exports restent
disponibles, l'analyse ne suspend rien, l'import de coûts réels n'écrit pas dans la révision.
Écarté : une condition `no_import_applying`, la même phrase pour l'écran. Exemple :
`revision_importing` de `getRevision`, symétrique de `revision_marking`.

**Les sauvegardes se lisent sans 403** (#348 ; WF-ADM-0110). `listBackups` garde 200, 401 et 404 :
une lecture de plateforme n'a pas de condition à nommer, comme `getBackup` et `getBackupSchedule`.

**Les indicateurs de devis sont à l'année de référence** (#352 ; WF-DEV-0060). `total`, ses
ventilations et les deux écarts, la description d'`EstimateIndicators` le dit ; `total` vaut
`NodeTotals.base_amount`, et seul `inflated_amount` de la grille porte l'inflation (#235). Écarté :
un second total corrigé, à décider le jour où un écran d'indicateurs sans grille le montrerait.

**Un export nomme sa révision** (#359 ; WF-INTF-0110, WF-INTF-0130). `ExportRequest.revision_id`
est exigé et non nul ; `requestExport` refuse une révision inconnue ou d'un autre projet par 404, un
corps sans révision par 422 (`/revision_id`). Écarté : une révision par défaut, qui ferait juger
l'export par une commande que l'écran n'a pas lue.

**Le plan de charge du projet nomme son nœud** (#362 ; WF-ARC-0020, WF-REF-0150).
`WorkloadPlan.org_node_id` et `org_node_label`, exigés et nuls sans filtre, sur le modèle de
`PortfolioScope` ; exemple `workload_org_node`, la direction technique. Le front lit encore le
libellé dans `listOrgNodes` : l'en-tête passe à la réponse avec l'écran du plan de charge.

**Un écart de liaison nomme son prédécesseur** (#364 ; WF-INTF-0080, WF-PLA-0080).
`ImportDifference.predecessor_label`, nul sauf pour une liaison, le successeur portant `lineage_id`
et `label` (EP-02/L29). Exemple : `import_planning_mismatch`, la liaison de la « Réception des
études » à la « Revue de conception ».

**Les courbes d'une révision marquée et les colonnes conservées** (#365 ; WF-DAT-0040, WF-IND-0010,
WF-CRE-0010, WF-INTF-0140, WF-REF-0070). Les courbes d'une révision marquée sont recalculées à la
date de son marquage sur les coûts réels connus aujourd'hui, et peuvent différer des indicateurs
conservés : `IndicatorsRevision`, `getCostCurve` et `getEarnedValueCurves` le disent, et
`is_stored` le signale ; WF-DAT-0040 ne change pas. Une colonne conservée du fichier changée est un
écart `updated` nommé `passthrough.<colonne>`, comme le tri la nomme : `ActualCostColumn` devient
un `anyOf` de ses quatre colonnes et du motif `^passthrough\..+$`, et le front nomme une telle
colonne comme le fichier la nomme ; `document_number`, qui identifie la ligne, est porté par
`label` et jamais par `fields`. Exemple : `import_actual_costs_analysed`, le fournisseur de la
facture. `listOrgNodes` cherche aussi sur le code.

## Les constats de la seconde moitié d'EP-02 (EP-02/L35)

Les constats de contrat ouverts pendant les lots d'écrans et du témoin (#466, #463, #424, #425,
#458, #414, #413, et le quatrième point de #353, joint à #414), chacun selon la proposition de son
issue et la décision du plan de résorption du 2026-10-07. Une forme que ni la spécification, ni le
constat ne fixaient est dite comme telle. Le front n'en adopte que ce qu'il faut pour rester juste
et vert ; l'adoption à l'écran est EP-02/L36 (#475).

**La marge du reste à engager a un seul sens** (#466, décision de l'auteur du 2026-10-07 ;
WF-RAE-0020). `RemainingIndicators.delta_to_reference` vaut désormais le budget de référence moins
la somme du coût réel et du reste à engager, positive quand il en reste, comme
`SubprojectBalance.variance` et l'écart de couverture des risques ; les descriptions le disent, et
la marge du projet est la somme des marges de ses sous-projets, hors sous-projet compris. Le
générateur le calcule ainsi, et non plus « le coût réel plus le reste à engager moins le budget »
qu'EP-02/L24 reprenait de l'exemple écrit à la main : `remaining_indicators` porte 93 900 et non
plus -93 900, `remaining_indicators_over_budget` 94 100, la réestimation du jour en ayant dégagé
200. Le front nomme cette valeur « Marge sur le budget de référence ». `delta_to_previous_revision`,
que la décision ne vise pas, garde son sens et le contrat le dit : le reste à engager courant moins
celui de la révision marquée précédente, à son marquage, négatif quand la revue l'a réduit — ce que
la revue a changé (WF-RAE-0020), qui n'est pas une marge : un reste à engager diminue aussi de ce
qui s'est dépensé ; nul (`null`) sans revue précédente, et non zéro, l'écran l'omettant alors. Deux
mots, deux sens — décision de l'auteur à la revue : le reste à engager parle de **marge**
(`delta_to_reference`, `SubprojectBalance.variance`, que le front nomme « marge », par sous-projet
comme pour le projet), et la couverture des risques garde son « écart de couverture » de la
spécification, dans le même sens ; le portefeuille et les projections parlent d'**écart**, positif
au-delà du budget : l'écart de la liste des projets (`PortfolioProject.delta_to_reference`), que le
Vérif de WF-PTF-0040 fixe ainsi (« un écart de 50 » pour 1 050 face à 1 000), et les écarts des
projections (`Projections.variance_*`, la projection moins le budget de référence, WF-IND-0050),
dont le front garde le libellé « Écart au budget ». Les écarts du devis
(`EstimateIndicators.delta_to_*`) sont le devis courant moins le devis comparé. L'écart de coût et
l'écart de délai (`cost_variance`, `schedule_variance` des indicateurs du projet et du portefeuille)
suivent le glossaire : la valeur acquise moins le coût réel, positif sous le budget, et la valeur
acquise moins la valeur planifiée, positif en avance (WF-IND-0070, WF-IND-0080). Les écarts de
montants d'une comparaison de révisions (`RevisionComparison.amount_deltas[].delta`) : la
spécification ne donne aucun sens (WF-REV-0080, « les écarts de montants ») ; retenu, la révision
comparée (`to_revision_id`) moins la révision de base (`from_revision_id`), le sens où une tâche y
est dite ajoutée et celui du devis en cours moins le devis comparé, et le sens que le générateur
calculait déjà. Chaque propriété `*variance*` ou `delta*` des schémas porte désormais une
description qui dit son sens, `RiskCoverageTotals.coverage_variance` compris ; un test des outils le
tient (`test_contract_gaps.py`). La colonne de la liste des projets se nomme « Écart à la référence
», libellé fixé par l'auteur sur #466 ; les projections gardent « Écart au budget ».

**`listNodes` filtre sur la récapitulative, le niveau et la chronologie** (#463 ; WF-PLA-0110,
WF-PLA-0140). Trois filtres sur une tâche, qui se combinent aux autres : `summaries_only`, les
seules récapitulatives ; `max_level`, au moins 1, les tâches dont le niveau ne dépasse pas celui
demandé, le premier étant celui des tâches sans parent — une ligne suit la tâche qui la porte, quel
que soit son niveau ; `timeline_id`, les tâches et les jalons inscrits sur la chronologie. Deux
formes que le constat ne fixait pas : **une lecture par chronologie ne rend pas les ancêtres** des
tâches retenues, seule exception à la règle de lisibilité de l'arbre — une chronologie n'est pas un
arbre, et le front n'aurait sinon d'autre moyen que `tracking` pour écarter les ancêtres, la
sélection que le constat voulait lui retirer ; et une chronologie sans inscription, ou d'un autre
projet, ne retient rien plutôt que d'être refusée, comme un poste qu'aucune tâche ne porte. Exemples
`nodes_summaries` — la variante à quatre niveaux du témoin (`nodes_nested`) demandée au niveau 2 :
les études, l'installation et le lot rangé sous elle, sans le sous-arbre de la survenance, au
troisième niveau — et `nodes_timeline`, le comité de pilotage : les études, la réception des études,
la réception usine et la mise en service, sans le lot ni l'installation.

**Les totaux d'une lecture ne changent pas avec `kinds`** (#487, option (a), décision de l'auteur).
La description de `listNodes` le promettait déjà : les totaux sont ceux de la structure lue, quel
que soit `kinds`. Le générateur rendait des totaux nuls pour une lecture des tâches seules ; il rend
désormais ceux de la lecture complète, aux mêmes filtres. `nodes_planning` porte la ligne des études
de détail, `nodes_timeline` celle de la mise en service, `nodes_nested` les lignes de son sous-arbre
; `nodes_summaries` reste à zéro, aucune récapitulative ne portant de ligne propre, qu'un filtre sur
une tâche retiendrait avec elle.

**La grille de reste à engager reçoit les grandeurs au reste à engager précédent** (#424 ;
WF-RAE-0040, WF-ARC-0020). `EstimateLineFacet.previous_quantity`, `previous_hours` et
`previous_unit_disbursement`, nuls avant la première revue comme `previous_reestimated_amount`, et
nuls comme leurs grandeurs courantes là où la ligne n'en porte pas ; demandables par `fields` comme
toute propriété de la facette. `NodeColumn` les range avant `previous_reestimated_amount` : une
ligne offre désormais dix-sept colonnes à partir de son libellé, et `paste_too_wide` le dit
(`max_columns` à 17). Ce sont des valeurs conservées et non calculées : elles n'entrent ni dans
`ComputedField` ni dans `ComputedValueField`, et aucun nœud ne les accepte en écriture. Les lignes
du témoin les portaient nulles, comme leur montant réestimé précédent ; elles portent depuis
EP-02/L26 celles de la révision 101 (« L'univers témoin », « Le portefeuille à l'échelle »).

**Le Kanban reçoit toutes les tâches, par état** (#425 ; WF-RAE-0030, WF-PLA-0040).
`listStartableTasks` rend trois colonnes exigées, chacune dans l'ordre du plan et sans
récapitulative : `not_started`, toutes les tâches non démarrées et non plus les seules dont les
prédécesseurs sont terminés ; `started` ; `completed`, les tâches terminées avec leur
`task.completed_on`, que le Kanban rouvre par `setTaskProgress`. Une tâche non démarrée est un
`NotStartedTask`, le nœud et `predecessors_completed`, vrai quand tous ses prédécesseurs sont
terminés ou qu'elle n'en a aucun : c'est par lui que le Kanban signale un jalon à terminer. Le nom
s'écarte de l'`is_startable` du constat : WF-RAE-0030 ne fait pas dépendre le démarrage des
prédécesseurs, et un drapeau « démarrable » à faux sur une tâche que rien n'empêche de démarrer
dirait le contraire de la règle. L'operationId reste `listStartableTasks`, que le client engendré
nomme ; le résumé devient « Tâches du Kanban, par état ». Exemples : `startable_tasks`, trois tâches
non démarrées, aucune signalée — la réception usine attend la fin du câblage —, six terminées ;
`startable_tasks_milestone`, la réception usine signalée, le câblage parmi les terminées. Le front
signale désormais un jalon par ce drapeau, et non plus par sa seule colonne, qui le signalerait à
tort ; il garde ses deux colonnes jusqu'à EP-02/L36.

**Une réestimation qui termine une tâche demande sa date** (#458 ; WF-RAE-0040, WF-PLA-0130).
`RemainingUpdate.completed_on`, facultatif, exigé quand la saisie met à zéro la dernière ligne
encore ouverte de sa tâche, ignoré sinon ; sans lui, `setLineRemaining` répond 422
`VALIDATION_FAILED`, motif `COMPLETION_DATE_REQUIRED` sur `/completed_on`,
`fields[].params.task_node_id` nommant la tâche, et rien n'est écrit : l'écran demande la date,
qu'il propose au jour courant, et rejoue la saisie. Un motif par champ et non un code de premier
niveau, comme le proposait le constat : c'est un champ du corps qui manque. Le nom suit
`TaskFacet.completed_on`, et non l'`occurred_on` de `ProgressUpdate`, qui date un démarrage comme
une terminaison. Exemple engendré `remaining_completion_date_required`, variante contrefactuelle
déclarée : la charge du raccordement des borniers mise à zéro, les deux autres lignes du câblage des
armoires supposées déjà à zéro — la ligne de provision du risque identifié 751 ne l'est pas dans le
témoin.

**Une tâche non démarrée réestimée à zéro passe par l'état démarré** (#486, option (a), décision de
l'auteur ; WF-RAE-0030, WF-RAE-0040). Le contrat permettait de réestimer une tâche non démarrée, et
un reste à engager nul termine la tâche : pour une tâche qui n'est pas un jalon, c'était le passage
direct de non démarrée à terminée que WF-RAE-0030 réserve aux jalons. Une telle saisie la démarre et
la termine à la même date, celle de `completed_on`, qui devient aussi son `started_on` ;
`RemainingUpdate`, `completed_on` et `setLineRemaining` le disent. La règle est celle de
WF-RAE-0030, quel que soit le chemin : un import de reste à engager qui termine une telle tâche la
démarre et la termine le jour de son application, `started_on` égal à `completed_on`, ce que disent
`ImportReport.completed_tasks` et `ImportCompletedTask`. Écartés : une date de démarrage demandée en
plus, détail que le reste à engager ne demande pas, et un refus tant que la tâche n'est pas
démarrée. L'exemple `remaining_completion_date_required` porte sur le câblage des armoires, déjà
démarré : il n'en dépend pas.

**L'union des colonnes conservées des coûts réels est donnée pour toute la lecture** (#414, #353
quatrième point ; WF-CRE-0010). `meta` de `listActualCosts` devient un `ActualCostListMeta`, la
pagination et `passthrough_columns`, l'union des colonnes conservées de toutes les lignes retenues
par les filtres, et non de la page : chaque colonne une fois, nommée comme `passthrough` la nomme,
dans l'ordre où les imports les ont déclarées — les imports dans leur ordre d'application, les
colonnes d'un import dans l'ordre de son fichier, une colonne à sa première déclaration —, ordre que
le constat laissait ouvert pour plusieurs imports. `PaginationMeta` ne change pas pour les autres
listes. Les quatre exemples, écrits à la main, la portent : les trois colonnes du témoin, aucune
pour `actual_costs_empty`.

**Un état refusé nomme son énumération** (#413 ; WF-ARC-0110). `Problem.params.state_enum`, rendu
avec `params.state`, nomme l'énumération du contrat dont l'état est une valeur (`StateEnumeration`)
; seul `ProjectState` en relève aujourd'hui — les indicateurs d'un projet qui n'a pas atteint l'état
En cours, le plan de charge d'un projet sans référence, les deux seuls refus qui portent un état —,
et une énumération de plus sera une modification du contrat. Écarté : `object_kind` et une table
objet → énumération, une indirection de plus pour le même renseignement. Exemples
`project_indicators_not_in_progress` et `workload_no_reference`. Le front le lira avec EP-02/L36
(#475, premier point de #353) ; d'ici là il nomme toujours un état comme un `ProjectState`, ce qui
reste juste.

**Ce que ce lot laisse.** Les lignes du témoin ne portaient aucune valeur au reste à engager
précédent, montant ni grandeurs, alors que la révision 101, marquée le 1er février pendant l'état En
cours, en est la revue précédente — celle dont `remaining_indicators` tire son écart à la révision
précédente : EP-02/L26 (#375) les leur donne. Les totaux de `listNodes` lu avec
`kinds=task` sont ouverts en #487.

## L'univers témoin

**Les exemples du contrat décrivent un seul univers, à un seul instant** (#287, décisions de
l'utilisateur du 2026-10-05, plan de résorption du 2026-10-07). Cette section, unique, dit ce
qu'est l'univers témoin et comment il s'engendre ; les sections des autres lots qui renvoyaient
à #287 renvoient ici. Aujourd'hui est le **3 juin 2026 à 14 h 05 UTC** : le premier exemple de
chaque opération décrit le projet témoin, PRJ-001 « Modernisation du poste de commande », ou le
portefeuille de trois cents projets qui le compte, à cet instant. Un autre exemple nommé est l'une
de quatre choses : une autre lecture du même état (une page, un filtre, `subtree_of`) ; un instant
antérieur de la même chronologie (une révision marquée, un `as_of`) ; la suite immédiate d'une
écriture ou d'une tâche lancée aujourd'hui ; ou une variante contrefactuelle déclarée comme telle
(« si… »).

**Ce qui se déduit s'engendre, depuis une seule description.** `wftools.mockwitness` décrit le
témoin une fois — sa chronologie, les familles d'identifiants sur des plages disjointes, les rôles
et calendriers qu'emploient ses lignes, son cœur lisible, ses risques, ses coûts réels, sa
référence telle qu'elle fut marquée — et `make mock-data` en écrit, en une seule exécution qui
atteint son point fixe (ce que la commande engendre se passe en mémoire, jamais relu du disque) :
les lectures et les écritures de la grille (`mockcore`, `mockwrites`), l'histoire et les risques
(`mockhistory`), les indicateurs, les courbes et le plan de charge d'aujourd'hui (`mockindicators`,
`mockcurves`, `mocktoday`), les coûts réels (`mockcosts`), les volumes du §4.6.2 et le portefeuille
(`mockstructure`, `mockportfolio`, `mockportfoliotime`), et le journal d'audit (`mockaudit`,
EP-02/L42). Les formules sont simples et dites dans chaque générateur, en attendant le noyau
d'EP-06 à EP-11. Reste écrit à la main ce qui ne se
déduit pas — sessions, comptes, permissions, référentiel, le projet, ses révisions et ses
transitions, imports et comptes rendus, tâches de fond, état du système et sauvegardes, erreurs,
variantes contrefactuelles — : les générateurs le lisent, et `tools/tests/test_mockhistory.py` et
`tools/tests/test_mockuniverse.py` le confrontent à ce qui est engendré.

**Les contradictions relevées sur #287 sont fermées** : C1 (un identifiant pour plusieurs nœuds)
par EP-02/L21 et L23 ; C2 (premiers exemples à montants différents) par L24 ; C3 (le sous-projet
porteur d'un coût réel) par L25 ; C4 (deux instants du portefeuille) et C7 (son échelle) par L26 ;
C5 et C6 (tâches de fond au même instant, sessions sur un même compte) par L25 ; C8 tombe avec la
spécification révisée (L23) ; C9 et C10 (écriture qui redate, passage par `reinflated`) par L22 ;
C11 à C13 (chronologie, comparaison, réception usine) par L23 et L24 ; C14 et C17 par L21 ; C15
par L24 ; C16 (identifiants à double emploi) par L20 et L25. La structure de mille tâches est
datée en heures, le cœur incrusté en tête et relié au réseau engendré, depuis EP-02/L27 (#376).
Reste la décision 4 du cadrage — 751 et 753 à l'échelle de cette structure —, décidée par l'auteur
le 2026-10-07 (option (a)), et avec elle les lectures du témoin qui somment encore son seul cœur,
qu'EP-02/L45 (#528) reprend : la sous-section d'EP-02/L27 dit ce qui en reste.

Les sous-sections disent, lot par lot, ce que chacun a fait ; ce qu'une sous-section laisse est
repris par une suivante, ou renvoyé à EP-02/L27 (#376), puis à EP-02/L45 (#528). Ce qu'une sous-section décrit et qu'une
suivante a changé — la capacité des rôles, le cours des projets du portefeuille — se lit dans la
dernière qui en parle.

### Le socle (EP-02/L20)

**Le témoin se décrit une fois** (#287, décisions de l'utilisateur du 2026-10-05). Les premiers
exemples décrivent un seul projet, PRJ-001, à un seul instant, aujourd'hui : le 3 juin 2026 à
14 h 05 UTC. `wftools.mockwitness` en est la source unique : cet instant, la chronologie du projet
(de l'installation au 1er septembre 2025 aux imports de coûts du jour), les rôles qu'emploient ses
lignes et leurs calendriers — lus dans `resource_roles` et `calendars`, écrits à la main, jamais
recopiés —, et son cœur lisible : le groupe « Études », le lot « Poste de commande » et le
sous-arbre fusionné dans la révision en cours par la survenance de 752, aux identifiants fixes
(le nœud 5nn, sa lignée 6nn) et aux chiffres des Vérif — 12,5 h × 80 = 1 000, 1 234,56, la
provision de 500 de 751, des lignes de 120 et 80 budgétées à zéro (WF-RIS-0060 révisée ; la
référence reste 101). Un autre exemple nommé est une autre lecture
de cet état, un instant antérieur de la même chronologie, la suite d'une écriture faite
aujourd'hui, ou une variante contrefactuelle déclarée.

**Une famille d'identifiants par nature d'objet, sur des plages disjointes**
(`mockids.IDENTIFIERS`, C16) : les identifiants écrits à la main par centaines — projets,
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

### Les lectures de la grille (EP-02/L21)

**Les exemples nommés de `listNodes` sont des lectures d'un seul arbre, engendrées** (#287 ; C1,
C14). `wftools.mockcore` date le cœur décrit dans `mockwitness` en heures de travail sur le
calendrier de chaque tâche (`mockcalendar`), à partir du début des études (2 mars 2026) et de ses
liaisons ; une passe arrière donne à chaque tâche en mode automatique la fin la plus tardive que ses
successeurs lui laissent — la fin du cœur sans successeur —, sa marge étant les heures de travail de
sa fin à cet instant, en jours ouvrés ; une tâche en mode manuel n'a ni marge ni criticité et
n'impose rien à ses prédécesseurs. Les lignes sont chiffrées au taux de leur catégorie pour l'année
de référence (12,5 h × 80 = 1 000), consommées l'année du début de leur tâche ; une tâche somme ses
lignes et ses subordonnées ; l'avancement physique d'une récapitulative est le budget des lignes de
ses tâches terminées sur celui de son sous-arbre, non calculable sans budget (`no_budgeted_amount`).
L'avancement se lit aux dates à aujourd'hui, le 3 juin 2026 : les études sont terminées, les pupitres
opérateurs en mode manuel démarrés et en dépassement de fin, le câblage des armoires en cours, la
réception usine au 30 juin (C13). Les nœuds sont numérotés depuis la première ligne de la structure,
où EP-02/L27 placera le cœur en tête (#376) ; jusque-là, marges et chemin critique sont ceux du cœur
seul, et les mille tâches du volume restent datées au 16 mars.

`make mock-data` écrit ces lectures sous `fixtures/api/`, par leur nom, à côté des volumes :
`nodes`, le sous-arbre « Études » avec ses lignes (`subtree_of`) ; `nodes_planning`, le même sans ses
lignes (`kinds=task`) ; `nodes_estimate`, le sous-arbre « Poste de commande », qui porte le sous-arbre
fusionné par la survenance de 752 ; `nodes_milestone`, la recherche « Réception usine », dont la
récapitulative est rendue pour la lisibilité et absente des totaux ; `nodes_risk_occurred`, le
sous-arbre 541 seul ; et `dependencies_summary`, `dependencies_summary_moved`, `dependencies_labour`,
`dependencies_task_amount`, `dependencies_provision`, `dependencies_manual_float`, ce dont dépendent
les valeurs calculées des mêmes nœuds. `make mock-data-up-to-date` les vérifie comme les volumes,
et `tools/paths.toml` les déclare engendrés. `dependencies_entered`, un refus sans nœud, reste écrit
à la main. **Les totaux d'une lecture sont ceux des lignes qu'elle retient** (`NodeTotals`) : une
lecture des tâches seules ne somme rien, là où l'exemple écrit à la main gardait les totaux de la
structure.

**La ligne de provision 555 est budgétée à la provision que la référence connaissait**, 250 — 751 à
1 000 × 25 % le 1er février (`risk_reviews`) —, quand son montant d'aujourd'hui est 500 : ce budget
compte à la réserve pour risques, jamais au budget de référence (WF-RIS-0050, `EstimateLineFacet`).
Le devis du lot totalise donc 2 934,56, dont 2 484,56 budgétés. **C14 et C17 sont fermés, et C1 hors `comparison`, dont L23 (C12) porte les lignées** : les
risques 751 (`risks`, `risk`) nomment leur ligne de provision 555, l'import du devis
(`import_analysed`) les lignées 653 et 654 des mêmes lignes, et un test confronte tout
`fixtures/api` — un nœud ou une lignée des familles 500–599 et 600–699 porte une seule nature et un
seul libellé dans tout l'univers, les fixtures qui s'en écartent déclarées : `task_renamed`, qui
renomme, et `comparison`.

**Ce que ce lot laisse** : `comparison.json` compare deux révisions sur les lignées 622, 623, 625 et
626 d'un autre découpage du témoin — une contradiction avec les lectures, déclarée, que L23 ferme
avec C12 ; les écritures `estimate_line_updated`, `task_renamed` et `node_deleted`, que les tests de
la grille combinent aux lectures, ont été reportées à la main sur les nœuds 553, 552 et 551 et aux
totaux d'aujourd'hui, et `predecessor_set` reste une écriture d'avril (marge du dossier de
conception à 7 jours quand les lectures la portent à 54, études sans dépassement de fin) : L22 les
engendre toutes.

### Les écritures de la grille (EP-02/L22)

**Une réponse d'écriture est la différence de deux lectures de la structure, avant et après
l'écriture, engendrée** (#287 ; C9, C10). `wftools.mockwrites` modifie la description du témoin
(`mockwitness`) — un libellé, une charge, une ligne retirée, une liaison ajoutée, un rôle changé
—, la date et la chiffre à nouveau (`mockcore`), lit la structure entière avant et après, et en
tire `NodesWritten` : les nœuds écrits, une version de plus ; les tâches non récapitulatives dont le
début, la fin, la marge ou la criticité ont changé sans être écrites (`rescheduled`) ; les lignes et
les tâches non récapitulatives dont le montant corrigé ou l'année de consommation a changé, hors
celles que `ancestors` rend entières (`reinflated`) ; les ancêtres des nœuds écrits, du nœud
supprimé — lu avant, puisqu'il n'est plus après — et des tâches redatées, entiers ; les totaux de
la structure entière. Une tâche qui porte la ligne écrite et que l'écriture redate est à la fois
dans `ancestors` et dans `rescheduled`, comme le contrat l'écrit. `make mock-data` écrit ainsi
`task_renamed`, `estimate_line_updated`, `node_deleted`, `predecessor_set` et le nouvel
`estimate_line_redated` sur le cœur, et `estimate_line_entered`, `paste_plan`,
`paste_plan_unknown_category`, `paste_too_wide` et `paste_applied` sur la structure de mille tâches
que le faux back sert en premier et que les parcours lisent, comme `task_lengthened`, désormais
produit par la même différence ; `tools/paths.toml` les déclare engendrés. Le poste du lot « Poste
de commande » (`order_item_id`, `work_breakdown_label`, EP-02/L29), rendu en ancêtre, sort du
générateur. **Une ligne saisie garde son budget** : la référence l'a fixé, seul le montant réestimé
suit les grandeurs (WF-DEV-0020) — 14 h au lieu de 12,5 donnent 1 120,00 réestimés et laissent
1 000,00 budgétés. **Les totaux d'une écriture du cœur sont ceux du cœur entier**, quinze tâches
et neuf lignes, comme le contrat le veut (« les totaux de la structure entière, sans filtre ») — les
exemples écrits à la main gardaient ceux du lot ; L27 (#376) les portera à la structure de mille
tâches où il incruste le cœur. Le bloc collé, ses lignes acceptées ou refusées, sont lus du bloc et
des catégories et rôles de l'univers ; la largeur de `paste_too_wide` est comptée dans `NodeColumn`
du contrat — le libellé, puis de `cost_category` à la dernière colonne —, pour suivre la prochaine
colonne sans retouche (EP-02/L16 avait dû la corriger à la main).

**L'univers offre une écriture du devis qui redate, et le cœur s'étend pour la porter** (C9). Le
cœur finissait à la réception usine, le 30 juin : aucune tâche n'y finissait fin 2026, et le monteur
câbleur, seul rôle actif sur un autre calendrier, n'avait pas de ligne. Le cœur gagne l'installation
sur site, après la réception usine, qui reste au 30 juin (C13) : le montage des armoires sur site
(562), du 1er juillet au 18 décembre 2026, son câblage par l'ingénieur électricien (563) et
l'assistance du technicien de mise en service aux essais (564), et la mise en service qui le suit
(565, sa ligne 566), démarrée le 21 décembre et consommée en 2026. `nodes_installation`, nouvel
exemple nommé de `listNodes`, en est la lecture (`subtree_of`). `estimate_line_redated`
(`updateEstimateLine`) confie le câblage sur site au monteur câbleur : le montage n'a plus que les
jours de ses deux rôles, quatre jours de huit heures (WF-PLA-0010), finit le 1er février 2027, et la
mise en service démarre le 2 février ; elle et le montage sont dans `rescheduled`, avec les tâches
sans successeur dont la marge grandit ; la ligne de la mise en service, consommée en 2027, et la
mise en service elle-même sont dans `reinflated`, 6 180,00 au lieu de 6 000,00. Deux écarts au
cadrage de #287, qui disait « la tâche prend 482 et finit en 2027 ; `reinflated` ses lignes et
elle-même », sont imposés par le modèle : la semaine de quatre jours de dix heures compte autant
d'heures que la semaine standard, et le 31 décembre 2026 est un jeudi, dernier jour qu'elle travaille
— un rôle seul sur 482 ne fait passer l'année à aucune tâche ; il y faut un second rôle sur 481, et
le montage prend le calendrier commun des deux. Et une ligne est consommée l'année où sa tâche
commence (simplification déclarée de `mockstructure.inflated`, WF-DEV-0040 voulant une répartition
au prorata des heures) : le montage, commencé en 2026, garde l'année de ses lignes, et c'est la
mise en service qui le suit, avec sa ligne, que l'écriture déplace dans le temps. Ajouter le
cœur allonge le chemin critique : la marge du dossier de conception passe de 54 à 187 jours
(15 avril 2026 – 1er janvier 2027), celle des tâches de la survenance de 32 à 165.

**`predecessor_set` est une écriture d'aujourd'hui, sur une tâche non démarrée** : les
prédécesseurs du montage sur site saisis à nouveau — la réception usine, en fin à début, avec deux
jours ouvrés de décalage. Le montage va du 3 juillet au 22 décembre, la mise en service du
23 décembre 2026 au 5 janvier 2027, démarrée encore en 2026 : `reinflated` est vide ; les tâches
sans successeur gagnent de la marge. Aucune date passée ne bouge : l'avancement d'une tâche et ses
dates de démarrage et d'achèvement sont des faits (WF-PLA-0130), et la réception usine reste au
30 juin (C13) — le test de `predecessor_set` le vérifie, et un invariant interdit à toute écriture
engendrée de changer l'avancement ou les dates d'une tâche démarrée ou terminée. L'exemple écrit à la main liait la
revue de conception au dossier de conception, ce qui, aujourd'hui, aurait redaté des tâches
terminées. Le cœur se date désormais dans l'ordre de ses liaisons, quel que soit l'ordre du plan ;
une boucle est refusée, en nommant les tâches restées sans date.

**La lecture entière du cœur est un exemple nommé** (`nodes_core`, `listNodes` sans filtre) : ses
totaux sont ceux que rendent les écritures du cœur, et les tests de la grille qui éprouvent les
totaux de la structure entière la lisent, plutôt qu'un sous-arbre lu comme s'il était entier.

**Le chemin de la grille de devis par `reinflated` est éprouvé** (C10) :
`inflation.dom.test.tsx` rend la grille sur `nodes_installation`, écrit le rôle du câblage sur site,
et lit dans les cellules de la mise en service et de sa ligne les montants corrigés que la réponse
porte, leur montant à l'année de référence inchangé, la récapitulative rendue entière.

**Ce que ce lot laisse** : le refus de la création à la main d'une ligne de nature provision
(Vérif de WF-DEV-0020) n'a pas d'exemple — il faut un motif de refus au catalogue
(`ErrorCode`), modification d'un schéma que porte EP-02/L30 (#393) ; `paste_applied` calcule ses
montants par un second chemin, sur les nœuds de la structure de mille tâches, que EP-02/L27 (#376)
ramènera au calcul du cœur en l'y incrustant ; `task_renamed` reste déclaré dans le test des
libellés du cœur, puisqu'il renomme.

### Révisions et risques (EP-02/L23)

**La chronologie du témoin se lit dans ses révisions** (#287, C11 ; WF-RIS-0020, WF-RIS-0060
révisée). `wftools.mockwitness` date désormais chaque événement à l'heure où les exemples
l'écrivent, et le cadrage du 2026-10-05 est recalé sur la spécification révisée, comme le
commentaire du 2026-10-06 sur #372 le demandait : l'installation, son référentiel et ses comptes le
1er septembre 2025 (les audits du référentiel, des comptes et des catégories engendrées, qui
portaient le 5 janvier 2026, y passent) ; PRJ-001 créé le 6 octobre 2025, passé en chiffrage le
3 novembre à l'ouverture de l'offre 100, en cours le 15 janvier 2026 à la désignation de sa
référence — l'exemple écrit à la main le créait le 2 mars, après son offre. Deux ouvertures de
révision, que le cadrage ne datait pas, suivent la spécification : **la révision 101 est ouverte le
12 janvier par l'identification des risques**, saisie de la révision en cours qui la crée faute
d'en avoir une (WF-RIS-0020), puis marquée le 1er février par la fusion de l'avenant 1, qui en fait
la référence (WF-REV-0050) ; **la révision courante 102 est ouverte le 2 février par le réexamen
du risque 751**, et non le 2 mars, pour que la survenance du 20 février fusionne dans une révision
en cours sans en créer une (WF-RIS-0060). La référence reste 101 : la révision 103 du cadrage
n'existe plus, et C8 tombe avec elle. `tools/tests/test_mockhistory.py` confronte à cette
chronologie le projet, ses révisions et ses transitions d'état, écrits à la main, et vérifie
qu'aucun instant de l'univers n'est antérieur à l'installation ni postérieur à aujourd'hui, hors
les expirations à venir ; la sortie du projet (`project_completed`), suite d'une écriture faite
aujourd'hui, passe du 30 septembre au 3 juin à 14 h 05.

**L'offre et la référence sont décrites depuis le cœur, et leur comparaison en est la
différence, engendrée** (C12, C13 ; WF-REV-0080). `wftools.mockhistory` décrit la référence telle
qu'elle fut marquée — rien de démarré, sans le sous-arbre de la survenance, chaque risque portant sa
ligne de provision à la provision qu'il avait alors : 751 à 250 (1 000 à 25 %, `risk_reviews`),
752 à 60 sur la ligne 557, 753 à 600 sur la ligne 567, deux lignes que la révision courante ne
porte plus — et l'offre telle qu'elle fut marquée, avant tout risque et sans l'avenant 1 : le
raccordement des borniers à 10 h, ni assistance aux essais de câblage ni réception usine,
le dossier de conception en trois jours, et des essais préliminaires sur site (568, sa ligne 569),
que l'avenant retire. `comparison` est la différence des deux lectures par lignée : une tâche
change par ses dates, sa durée, son avancement ou son parent, une ligne par ses montants ou son
parent — le montant d'une tâche est celui de ses lignes, que disent les lignes et les écarts ; les
écarts sont ceux du devis à l'année de référence, par nature et par sous-projet. La ligne de
provision ajoutée de 751 porte donc 250, et la réception usine est celle du cœur, 656 : `comparison`
quitte la liste des fixtures dispensées du test des libellés du cœur. Chaque révision se chiffre
aux taux de son année de référence (WF-REV-0030) : la référence à ceux de 2026, ceux du cœur ;
l'offre, de 2025, aux taux de 2025 du volume des taux (`getHourlyRateGrid`, la formule sortie dans
`mockstructure.hourly_rate`) : 78,50 pour l'ingénierie électrique, 73,50 pour la mise en service,
comme #232 le propose. Le câblage sur site et la mise en service sur site changent donc de montants
comme le raccordement des borniers, et l'écart de main-d'œuvre vaut 3 515,00. `rate_update`, écrit
à la main, donne encore 80,00 de taux précédent à la mise en service : EP-02/L24 l'alignera sur le
volume (C15 de #287, #232).

**Les risques, leur matrice, leurs réexamens et leur couverture sont engendrés** (#287). Les trois risques sont décrits une fois (`mockwitness.REGISTER`) : ce que l'utilisateur a
saisi, leurs réexamens datés — l'identification la première, la survenance la dernière —, la
ligne de provision qu'ils portent et celle que portait la référence. `risks`, `risk`,
`risk_occurred_detail`, `risk_matrix`, `risk_reviews` et `risk_coverage` en sont lus : la
probabilité, la gravité et l'état du dernier réexamen, la provision la gravité pondérée, les
commandes selon l'état et la citation par une révision marquée (EP-02/L30), les totaux — les
identifiés à leur provision d'aujourd'hui, les survenus et les écartés à celle que portait la
référence —, la réserve de la référence, 910, somme de ses lignes de provision, la couverture au
3 juin. **La matrice est à l'échelle du témoin** : la gravité se lit en part du budget de
référence que le générateur calcule — les montants budgétés de la référence hors provisions,
120 834,56, que la révision courante porte encore, la survenance ne le déplaçant pas —, et non plus
des 100 000 écrits à la main. Les gravités et les probabilités gardent les chiffres que fixe la
réserve de 910 ; « Indisponibilité de l'automaticien », 12 000, soit 9,93 % du budget, passe ainsi
du niveau de gravité 4 au niveau 3, et sa case de la zone de vigilance à la zone nominale ; un
risque prend une version par réexamen, et ce risque passe à la version 3. Un risque identifié
après le marquage de la référence n'a pas de part à sa réserve : sa provision de référence est
nulle, et la référence ne porte pas sa ligne de provision. Le portefeuille, qui somme le registre, la matrice et la couverture du témoin, les reçoit en
mémoire (`mockhistory.readings`), jamais relus des fichiers que la même commande écrit : une seule
exécution de `make mock-data` atteint son point fixe.

**Ce que ce lot laisse.** Les indicateurs du projet (`project_indicators`, budget de référence de
100 000), `remaining_indicators` et sa couverture, au 16 mars, sont à EP-02/L24, qui les
engendrera depuis le même cœur ; la ligne du témoin au portefeuille et `state_transitions_exited`,
l'offre perdue, à EP-02/L26. `milestone_tracking`, écrit à la main, contredit l'histoire engendrée :
la réception usine y a un point à l'offre, que l'avenant 1 lui a pourtant ajoutée, et la réception
des études y est dite repoussée de deux semaines par la référence, quand la référence ne la
déplace pas — renvoyé à EP-02/L24, qui engendrera le suivi des jalons depuis les révisions
décrites ici. **La décision 4 du cadrage n'est pas appliquée** : 751 et 753 gardent les chiffres
qui fixent la réserve de 910, et ne sont pas portés à l'échelle de la structure de mille tâches.
Quand EP-02/L27 (#376) y incrustera le cœur, le budget de référence changera d'ordre de grandeur,
et avec lui les cases de la matrice ; la question est soumise à l'auteur sur #376, qui la tranchera
avec la réserve.

### Les indicateurs d'aujourd'hui (EP-02/L24)

**Les indicateurs du témoin sont engendrés, au 3 juin 2026 à 14 h 05** (#287 ; C2, C13, C15,
#232). `wftools.mockindicators` lit trois révisions décrites depuis le cœur — l'offre et la
référence à leur marquage (`mockhistory`), la révision courante aujourd'hui (`mockcore`) — et les
coûts réels du périmètre suivi que portent `actual_costs` et `actual_costs_subproject`, écrits à
la main, à leur date de pièce ; `wftools.mockcurves` les étale dans le temps ; `wftools.mocktoday`
en écrit les exemples, que `tools/paths.toml` déclare engendrés : `estimate_indicators*`,
`missing_rates`, `rate_update`, `remaining_indicators*`, `project_indicators`,
`project_indicators_marked`, `index_history`, `milestone_tracking`, `cost_curve*`,
`earned_value_curves` et `workload*`. Le budget de référence vaut désormais partout 120 834,56 —
les montants budgétés de la référence hors provisions (WF-RIS-0050) — et non plus les 100 000
écrits à la main ; les exemples au 16 mars disparaissent de ces opérations. Restent écrits à la
main les refus (`project_indicators_not_in_progress`, `project_indicators_offer`, `workload_*`
refusés), `missing_rates_none`, `rate_update_none` et `milestone_tracking_none`, recalé à
aujourd'hui.

**Les formules, simples et dites dans le générateur**, en attendant le noyau d'EP-07 à EP-11 :
une valeur à un jour compte le travail de ce jour, quelle que soit l'heure du calcul ; un montant
étalé sur une tâche l'est au prorata de ses heures travaillées sur le calendrier de la tâche, celui
de ses rôles (WF-DEV-0080, WF-DEV-0070) ; le reste à engager suit WF-RAE-0010 ligne à ligne — rien
pour une tâche terminée, le réestimé d'une tâche démarrée, le budgété projeté d'une tâche non
démarrée, le réestimé d'une ligne budgétée à zéro quel que soit l'état de sa tâche, la provision
d'un risque identifié pour son montant — ; la valeur acquise exclut les lignes fusionnées par une
survenance (WF-IND-0030) ; l'écart du reste à engager au budget de référence est le coût réel plus
le reste à engager moins le budget, comme l'exemple écrit à la main le faisait. Un sous-projet qui
dépasse son budget est en alerte, les autres nominaux, et un mois de charge au-delà de la capacité
de son rôle aussi : WF-IHM-0070 ne fixe aucun seuil intermédiaire pour l'un ni l'autre.

**Ce que disent les exemples.** `estimate_indicators` : 121 534,56 de devis, dont 500 de
provision du risque identifié, le poste du lotissement que porte le lot « Poste de commande », et
un écart de -210,00 à la référence, qui est aussi la révision marquée précédente — les 500 de
provision et les 200 des lignes fusionnées face à ses 910 de provisions. `estimate_indicators_breakdown`
devient le devis que l'offre v1.0 a conservé à son marquage pendant le chiffrage (WF-DAT-0040),
sans écart faute de référence et de révision marquée précédente — l'exemple écrit à la main
décrivait un lot hors de tout univers. `*_missing_rates` reste la variante contrefactuelle
déclarée du devis d'aujourd'hui sans taux 2026 pour l'ingénierie électrique, engendrée : ce que
touchent ses lignes ne se calcule pas. `remaining_indicators` : 21 534,56, le poste de commande
au-delà de son budget de 2 400 — la facture des écrans, datée du 18 mai et importée le 3 juin, s'ajoute à un reste à engager
égal à son budget —, en alerte ; `remaining_indicators_over_budget` devient la suite immédiate de
la réestimation faite aujourd'hui (`remaining_reestimated`), le poste de commande encore au-delà,
de 2 200. `project_indicators` : valeur planifiée 101 223,69, valeur acquise 100 000 (les études
de détail), coût réel 5 400 ; `project_indicators_marked`, ceux que la référence a conservés le
1er février, rien de planifié ni de dépensé, un reste à engager qui compte ses 910 de provisions.
Le portefeuille reçoit ces indicateurs en mémoire (`mocktoday.project_today`) : la ligne du témoin
et les vues qui la somment changent avec eux, en attendant EP-02/L26. `workload_org_node` filtre
désormais sur l'atelier de câblage, qui ne retient que le monteur câbleur et écarte les deux rôles
du bureau d'études électricité : l'exemple éprouve le filtrage (WF-DEV-0070). L'atelier relève du
bureau d'études (`org_nodes`) : un filtre sur ce dernier retiendrait les trois rôles.

**Le suivi des jalons suit les révisions** (C13, commentaire du 2026-10-07 sur #373) : la
réception usine, que l'avenant 1 ajoute, n'a pas de point à l'offre ; la réception des études,
que ni la référence ni la révision courante ne déplacent, garde le 24 avril, et, terminée ce
jour-là, a son dernier point sur la diagonale, daté de minuit de sa terminaison, et aucun après
(WF-IND-0090).

**La courbe du budget porte la marche de l'avenant 1.** L'offre est la référence désignée à la
commande, le 15 janvier ; l'avenant 1 en produit une nouvelle le 1er février (WF-REV-0040,
WF-REV-0050) : `steps` porte sa marche, 3 165,00, la différence des deux budgets de référence, et
la série deux points à cette date, avant et après, nuls tous deux, rien n'étant encore prévu de
dépenser. La série suit, à chaque jour, la référence en vigueur ce jour-là ; la valeur planifiée,
elle, est recalculée entière sur la référence en vigueur (WF-DEV-0080), sans marche.
`cost_curve_amendment`, variante gardée, devient un avenant 2 de 15 000 sur la ligne des études
de détail au 10 mars : sa marche monte de 23 333,33 à 26 833,33, ce que la nouvelle référence
prévoyait de plus à cette date. **Les délais de paiement sont décrits** : trente jours sur
l'ingénierie de détail et sur les borniers (`mockwitness.PAYMENT_DELAY`), aucun sur la
main-d'œuvre ; la provision du risque identifié est placée à la fin de la tâche qui la porte, ou
au premier jour ouvré après aujourd'hui si elle est passée ; une ligne dont la tâche n'a plus
d'heure à travailler compte au premier jour ouvré qui suit la date de calcul. Le plan de charge
sur le reste à engager étale de même les heures d'une tâche démarrée sur ses heures ouvrées après
la date de calcul : aucun mois passé, les mêmes heures en tout. Les lignes du cœur ne rendent pas
`payment_delay_days`, facultatif : les nœuds restent tels quels, renvoyés à EP-02/L25 (#374).

**L'évolution des indices ne compte que les révisions marquées à partir de l'état En cours.**
Une révision marquée pendant le chiffrage ne conserve que les indicateurs de son devis
(WF-DAT-0040, WF-IND-0010) : l'offre v1.0 n'a pas de point, et chaque courbe du témoin en porte
deux, la référence à son marquage et la révision courante aujourd'hui. Le Vérif de WF-IND-0130
(« un point par révision marquée ») le contredit : la question est ouverte sur #468. Le suivi
des jalons, lui, garde le point de l'offre, une date prévue que l'offre porte (WF-IND-0090).

**`rate_update` suit la grille des taux** (C15, #232). Une proposition se présente à la création
d'une révision dont l'année de référence diffère de celle qu'elle copie (WF-REV-0060) : c'est la
création de la révision 101, le 12 janvier 2026, copie de l'offre de 2025. Chaque catégorie de
main-d'œuvre de l'offre y est proposée au taux de 2026 de la grille, celui de 2025 en regard :
l'ingénierie électrique de 78,50 à 80,00, la mise en service de 73,50 à 75,00, source
`reference_rate` — les taux auxquels la comparaison chiffre l'offre et la référence. L'exemple
écrit à la main les disait sans taux 2026, ce que la grille contredit. La révision courante,
ouverte en 2026 comme la référence qu'elle copie, n'a pas de proposition : `rate_update_none`
devient le premier exemple de `getRateUpdateProposal`, le témoin aujourd'hui, et `rate_update`
l'exemple nommé `reference_created`.

**Ce que ce lot laisse.** Le coût réel du témoin est celui des fixtures des coûts, écrites à la
main, qu'EP-02/L25 recale : les études de détail, terminées le 10 avril pour 100 000 de
sous-traitance, n'y ont aucune pièce, et l'indice de coût du projet vaut 18,5185, celui de
l'ensemble hors sous-projet 33,3333 — juste au regard des formules, invraisemblable ; renvoyé à
L25 par un commentaire sur #374, avec `payment_delay_days` des nœuds et le calendrier 481. Le
signe des écarts, que le contrat ne dit pas, est #466 ; le constat sur WF-REV-0050, à trancher
par l'auteur, #467 ; le point de l'offre dans l'évolution
des indices, #468. La ligne du témoin au portefeuille et la décision 4 du cadrage restent à
EP-02/L26.

### Coûts, échanges, tâches, comptes (EP-02/L25)

**Les coûts réels du témoin sont décrits une fois et engendrés** (#287, C3 ; WF-CRE-0010 à
WF-CRE-0050). `wftools.mockwitness` décrit les six lignes de coût — pièce, date, montant signé,
code de sous-projet lu dans l'OTP s'il en a un, colonnes conservées dans l'ordre que les imports
déclarent (`PASSTHROUGH`), imports qui les ont apportées, exclusion — et les cinq imports du
journal, aux instants de la chronologie (3 avril, 4, 6 et 11 mai, 3 juin) ; `wftools.mockcosts` en
écrit `actual_costs`, `actual_costs_page`, `actual_costs_subproject` et `cost_imports`, que
`tools/paths.toml` déclare engendrés. Ce qui s'en déduit est calculé : l'imputation d'une ligne
(WF-CRE-0020), son audit — créée par le premier import qui l'apporte, mise à jour par la
réextraction du 11 mai ou par son exclusion —, les trois totaux, les colonnes conservées de toutes
les lignes retenues (`meta.passthrough_columns`, #414, ajouté au contrat par `ActualCostListMeta`
comme EP-02/L35 le fait), la date du dernier import du journal, quel que soit le filtre, et les
lignes créées, mises à jour et ignorées de chaque entrée du journal. Les indicateurs lisent les
mêmes lignes en mémoire (`mockcosts.tracked`). **Le premier exemple de chaque lecture est le témoin
aujourd'hui** : `actual_costs` passe du 4 mai au 3 juin, six lignes, 105 400,00 suivis, 650,00
exclus ; `cost_imports` porte les cinq imports, et `cost_imports_periods`, qui les portait déjà,
disparaît. Une ligne d'un autre projet est « rejetée et signalée au compte rendu » (WF-CRE-0020
révisée) ; le journal la compte parmi les lignes ignorées, seul compte que WF-CRE-0050 lui donne.

**La facture des études entre dans l'univers** (décision de l'auteur, revue d'EP-02/L25) :
FA-2026-0409, 100 000 de sous-traitance datés du 10 avril, jour où les études de détail se
terminent, sans partie sous-projet dans son OTP comme leur ligne 527, apportée par l'extraction
d'avril du 4 mai. Son délai de paiement de trente jours décale le décaissement, non la date de la
pièce. Le coût réel du projet vaut 105 400,00, l'indice de coût 0,9488 ; l'ensemble hors
sous-projet dépasse son budget de 3 700,00 et passe en alerte, avec le Poste de commande. La
marge sur le budget de référence, dans le sens qu'EP-02/L35 lui donne, passe de 93 900 à
-6 100,00 pour `remaining_indicators` et de 94 100 à -5 900,00 après la réestimation du jour. Les
résumés du reste à engager se construisent depuis `by_subproject` : chaque maille en alerte y est
nommée avec son dépassement, et seules les autres sont dites nominales ; ils disent déjà « la marge
sur le budget de référence » (le budget moins le coût réel et le reste à engager) et « l'écart à la
revue précédente », le vocabulaire qu'EP-02/L35 adopte pour #466 — « écart » ne désigne plus le
budget moins le prévu.

**Les sous-projets suivent la commande** (WF-PRJ-0050) : leurs codes viennent de l'ERP avec la
commande du 15 janvier 2026, et ils sont déclarés le 20 janvier. L'offre, marquée le 15 décembre
2025, ne porte donc aucun sous-projet sur ses lignes (`mockhistory.offer`) : son devis conservé est
tout entier hors sous-projet, et la comparaison de l'offre à la référence fait passer les lignes du
Poste de commande de l'ensemble hors sous-projet au sien. `subprojects` dit le Poste de commande
porteur d'un coût réel (`has_actual_costs`), écrit à la main — `subprojects` est lu par tous les
générateurs — et confronté aux lignes par le test d'invariants.

**Toute ligne rend son délai de paiement, que la courbe applique** (WF-DEV-0020, WF-IND-0100).
`estimate_line.payment_delay_days` est rendu par `mockcore` sur chaque ligne du cœur : trente jours
sur l'ingénierie de détail et sur les borniers, zéro sur les autres, main-d'œuvre et provision
comprises. La lecture des indicateurs tire ses délais des nœuds qu'elle rend, et la courbe des
décaissements les applique : une seule source, que le test d'invariants vérifie ligne à ligne. Les
nœuds du volume ne le rendent pas encore (EP-02/L27).

**Le calendrier 481 ne connaît pas de jour férié** : WF-REF-0110 dit qu'un calendrier « ne gère ni
les jours fériés ni les temps partiels ». Le 25 décembre et le 1er janvier y sont des jours ouvrés,
et la charge de la mise en service y travaille : rien n'est à corriger.

**Les imports se lisent aujourd'hui** (WF-ARC-0100, WF-INTF-0080). Le devis du Poste de commande
(a11), que le cadrage analysait le 1er juin — il aurait expiré avant aujourd'hui —, est ouvert et
analysé ce matin à 8 h 41, applicable jusqu'à demain 8 h 41 : c'est lui qu'applique le parcours des
échanges. `imports` passe au 3 juin à 14 h 05 : ce devis analysé, l'extraction de mai (a14)
appliquée à 8 h 30, la nouvelle extraction d'avril analysée le 2 juin et expirée ce matin, jamais
appliquée, le planning abandonné et les quatre premières extractions ; huit imports.
`import_actual_costs_analysed` reste l'état que son analyse a laissé, un instant antérieur de la
même chronologie ; `import_remaining_analysed`, la variante que la liste ne reprend pas. Un import
expire vingt-quatre heures après son analyse, quelle que soit la lecture qui le dit. Les comptes
rendus visent l'arbre : chaque lignée nommée est celle du cœur, à son libellé, chaque ligne de coût
nommée une pièce du témoin.

**Les tâches de fond sont les suites d'écritures faites aujourd'hui** (C5, cadrage de #287).
Chaque exemple de tâche de fond est une suite possible, indépendante des autres, et non un
moment d'une seule séquence : le marquage a une variante aboutie et une variante échouée, que rien
n'enchaîne. Ainsi : le
marquage demandé à 14 h 05, qui court à 40 % (`tasks_running`), abouti à 14 h 09 ou échoué à
14 h 07 et relancé à 14 h 10 ; l'application de l'import du devis a11, confirmée à 14 h 06 ;
l'export, demandé à 14 h 06 min 30 s. Chacune a son instant, dans les dix minutes qui suivent
aujourd'hui : `test_mockhistory` admet nommément ces instants, bornés, et toute expiration à venir
dans la journée — une session, un lien, un import —, l'inactivité d'une session dans les deux
heures. **Les identifiants rejoignent leurs familles** (C16) : les tâches de fond 901 à 905, sur la
plage des sauvegardes, deviennent 931 à 935 ; les collages 911 et 912 et la corrélation 913, 971 à
973 ; les corrélations 921 à 927, 975 à 982, chacune dite par un seul exemple — les deux 921
d'origine séparées. La liste des empiètements de `test_mockwitness` est vide ; la plage 960-999,
partagée entre collages et corrélations, est notée pour EP-02/L27.

**L'état du système et les sauvegardes sont au 3 juin** : composants vérifiés à 14 h 04 min 30 s,
annuaire relu à 2 h, sauvegarde de 1 h, test de restauration du 1er juin ; les sept sauvegardes
planifiées vont du 28 mai au 3 juin. La copie externe automatique d'une sauvegarde planifiée
(WF-ADM-0170 révisée) n'a pas de paramètre dans `BackupSchedule` : #488.

**Comptes, sessions et contributeurs distincts** (C6 ; WF-ADM-0050, WF-ADM-0110). La session du
chiffreur est celle de Lucas Petit (305, rôle 705 « Chiffreur »), la session sans administration
celle d'Inès Roux (306, rôle 706 « Pilotage de projet ») : deux comptes locaux listés dans `users`,
deux rôles composés dans `access_roles`, les permissions d'une session étant l'union de celles de
ses rôles. Ni l'un ni l'autre ne lit tous les projets : ils sont contributeurs de PRJ-001, Lucas
Petit inscrit le 3 novembre 2025 au passage en chiffrage, Inès Roux le 15 janvier 2026 au passage
en cours ; `contributors` en est à sa quatrième version. Les comptes, sessions et `me` de Camille
Martin, comme `hourly_rate_entered` et `hourly_rate_corrected`, sont mis à jour le 3 juin à 14 h 05.

**Deux réponses d'écriture ne rendent plus un nœud à une version sous deux contenus** (#421). Le
collage suit la saisie du libellé de la ligne 4 des volumes : il la lit à la version 2 que la
saisie lui a laissée, la rend à la version 3, et la structure passe à 4 ; de même la réestimation à
10 h suit la saisie des 14 h (`estimate_line_updated`), la ligne passant à 3 et la structure à 3.
Les tests du collage dans la grille suivent : la réponse la plus récente est désormais celle du
collage, quel que soit l'ordre des réponses.

**Ce que ce lot laisse.** La copie externe des sauvegardes, #488 ; le délai de paiement des nœuds
du volume et la plage partagée des collages et corrélations, EP-02/L27 ; la ligne du témoin au
portefeuille et les exemples du portefeuille datés du 16 mars, EP-02/L26.

### Le portefeuille à l'échelle (EP-02/L26)

**Le portefeuille est lu aujourd'hui** (C4). Toutes ses vues sont calculées au 3 juin 2026, comme
le témoin qu'elles somment, et non plus au 16 mars ; la période des statistiques par défaut va du
4 juin 2025 au 3 juin 2026, et l'évolution trimestrielle de 2025-T3 à 2026-T2, lue des mêmes cours
que la courbe en S (`mockportfoliotime.quarterly`, et non plus d'écarts tirés) : chaque trimestre à sa
fin — aujourd'hui pour le dernier, qui égale les indices du jour —, le coût réel et la valeur
planifiée de la courbe, la valeur acquise du témoin par sa propre courbe et celle d'un autre projet
par la part de son coût réel dépensée, chaque indice en rapport des sommes. La ligne du témoin
est tirée de la structure : ses indicateurs d'aujourd'hui (`mocktoday.project_today`) et l'instant
de sa dernière révision marquée, la référence du 1er février, lu dans la chronologie
(`mockwitness`) ; un test d'invariants la confronte à `project`, `project_indicators` et
`revisions`, écrits ou engendrés ailleurs. Les projets engendrés en cours ont marqué leur dernière
révision entre le 2 février et cinq jours avant aujourd'hui, pour que la santé du pilotage en
trouve en retard et d'autres non. `portfolio_projects_empty` est recalé au 3 juin ; l'offre perdue
de `state_transitions_exited`, sortie du chiffrage le 15 mars 2026, tombe dans la période : c'est
l'une des six offres perdues du taux de transformation.

**Le plan de charge agrégé, la courbe en S et la santé du pilotage sont engendrés** (C7 ;
WF-PTF-0060, WF-PTF-0100, WF-PTF-0110). `wftools.mockportfoliotime` les somme sur les trois cents
projets : le témoin à ses propres lectures — son plan de charge sur le reste à engager, sa courbe
de coûts et ses décaissements, son suivi des jalons —, chaque autre projet par des formules dites
dans le générateur : un projet en cours travaille d'un début tiré entre le 1er octobre 2025 —
après le premier trimestre de l'évolution des indices, déclaré non calculable faute de coût réel et
de valeur planifiée — et le 31 janvier 2026, à une fin tirée après aujourd'hui ; son budget de
référence est étalé en deux morceaux, sa valeur planifiée (`mockportfolio.earned`, bornée au
budget) sur ses jours jusqu'à aujourd'hui et le reste sur ses jours après, pour que la courbe en S
et la performance disent la même valeur planifiée ; son coût réel est étalé sur ses jours jusqu'à
aujourd'hui — jusqu'à sa dernière révision marquée pour un projet que la santé du pilotage signale
sans coût réel importé depuis —, ce qu'il lui reste à engager — sa projection moins son coût
réel — sur ses jours après aujourd'hui ;
sa main-d'œuvre est la part que la structure des coûts lui donne (la moitié du reste à engager),
partagée entre l'ingénieur électricien et le technicien de mise en service par une part tirée, au
taux de la catégorie de chaque rôle. Le plan de charge et la courbe en S retiennent, comme la liste
et la valeur, les projets en chiffrage que la requête ajoute au périmètre par défaut : une offre
y entre pour son devis pondéré par sa probabilité de gain, étalé sur une période tirée après
aujourd'hui. **Choix déclaré** : dans la courbe en S, le devis pondéré d'une offre tient lieu de
budget de référence et de projection, rien n'étant dépensé — WF-PTF-0100 dit « les courbes de son
devis courant » sans dire lesquelles. En décaissements, le budget et le reste à engager d'un projet
engendré sont payés un délai tiré pour lui, de zéro à soixante jours, après leur travail, son coût
réel à la date de ses pièces, comme le témoin le fait de sa sous-traitance : le mois d'aujourd'hui
porte ainsi le passé et l'avenir. `portfolio_cost_curve_credit` est engendré de même, calculé au
31 décembre 2025 d'octobre à décembre, sur les projets alors en cours — ceux qui avaient commencé,
sans le témoin, encore en chiffrage —, chacun suivant le même cours ; décembre y est net négatif
par une variante déclarée en « si… » : si ses factures n'avaient pas encore été importées, ses
seuls avoirs l'étant déjà. Chaque point est la somme des points des projets, ce que les
tests éprouvent en sommant deux moitiés du portefeuille.

**La capacité d'un rôle est ses heures mensuelles, tout son effectif compris** (WF-REF-0100 ;
décision du 2026-10-08 sur #375, revue à la revue du lot : la spécification fait foi). C'est
`monthly_hours` seul que le plan de charge, du projet comme du portefeuille, compare à la charge ;
l'effectif n'est qu'une information. `monthly_hours` vaut l'effectif par les heures hebdomadaires
du calendrier du rôle × 52 / 12, arrondies au centième, la même convention pour tous :
173,33 h par personne pour l'ingénieur électricien et le technicien de mise en service — tous deux
sur la semaine standard de quarante heures, auparavant à 151,67, une base de trente-cinq heures
appliquée à tort — et pour le monteur câbleur, sur la semaine de quatre jours de dix heures ;
169,00 pour l'automaticien, désactivé, sur la semaine de trente-neuf heures. Un test d'invariants
tient `monthly_hours / headcount` égal à ces heures. **Les effectifs sont à l'échelle** du
portefeuille : 3 800 ingénieurs électriciens (658 654,00 h par mois), 2 800 techniciens de mise en
service (485 324,00 h), 1 250 monteurs câbleurs (216 662,50 h), deux automaticiens (338,00 h) ;
l'ingénieur électricien dépasse sa capacité en juillet et en août, le technicien passe sous le seuil
de 50 % en novembre. La capacité étant celle de l'installation, la charge du seul témoin dans son
propre plan de charge (`workload*`) en est au plus 0,02 % — en décembre, pour le technicien de mise
en service —, et nulle à quatre décimales les autres mois. **Le plan de charge d'un projet ne
présente donc pas de taux de charge** (décision de l'auteur du 2026-10-08 sur #375, option b,
réalisée par EP-02/L41) : la capacité de chaque rôle y figure dans le tableau, en regard de sa
charge (WF-DEV-0070), mais n'est plus dessinée dans le graphique, où sa ligne écrasait les barres ;
le faux back n'émet plus `load_ratio` dans les exemples `workload*`, champ que `WorkloadPlan` laisse
facultatif. Le taux de charge reste propre au plan agrégé du portefeuille (WF-PTF-0060), où
`load_ratio` est exigé. La date d'audit des rôles est celle de
l'installation, le 1er septembre 2025, depuis EP-02/L23 : le test d'invariants le tient.

**Le monteur câbleur figure sans charge** (même décision) : aucun projet ne l'emploie, et
`portfolio_workload` comme `portfolio_workload_org_node` le rendent avec sa capacité, une charge
nulle chaque mois, en sous-charge — le plan de charge sert à voir la disponibilité, et WF-PTF-0060
ne l'exclut pas. `portfolio_workload_org_node` filtre sur la direction technique : les trois rôles
relèvent de ses descendants. La main-d'œuvre de la structure des coûts reste tout entière au
bureau d'études électricité, le nœud des deux rôles qui travaillent.

**La couverture agrégée est la somme de celles des projets en cours** (WF-PTF-0090,
WF-RIS-0050) : la réserve de référence du témoin, 910, et celle de chaque autre projet, tirée de
2,5 à 5,5 % de son budget ; le coût des risques survenus du témoin, 200, et celui d'un projet sur
quatre, de 0,1 à 1,5 % de son budget ; les provisions restantes, celles des risques identifiés.
`matrix.totals.reserve` porte la même réserve. L'écart de couverture est la différence des sommes.

**La santé du pilotage se lit des projets en cours.** Une revue est en retard au-delà des huit
semaines du référentiel depuis la dernière révision marquée de la liste ; pour le témoin, ses
risques, ses imports et ses jalons sont lus de sa description : 751 réexaminé après le marquage de
la référence, des coûts importés depuis, la réception des études terminée le 24 avril et la
réception usine attendue le 30 juin — il n'a que sa revue en retard, de dix-sept semaines, et non
plus le jalon que l'exemple écrit à la main disait dépassé. Pour les autres projets, les risques non
réexaminés, les coûts non importés et les jalons dépassés sont tirés ; un jalon dépassé est nommé
par une lignée de la famille engendrée « jalons du portefeuille » (`mockids.IDENTIFIERS`).
Zones : un jalon dépassé en alerte, les trois autres signaux en vigilance — WF-IHM-0070 ne fixe pas
de niveau.

**Les lignes du cœur portent la revue précédente** (#424, renvoyé ici par EP-02/L35 ;
WF-RAE-0040). La révision 101, marquée le 1er février pendant l'état En cours, est la revue
précédente de la révision courante, celle dont `remaining_indicators` tire son écart à la revue
précédente : chaque ligne de la révision courante porte ses grandeurs à 101 — `previous_quantity`,
`previous_hours`, `previous_unit_disbursement` — et le montant réestimé qu'elles donnaient,
`previous_reestimated_amount`. La provision de 751, à 500 aujourd'hui, y était à 250 ; les lignes
fusionnées par la survenance de 752, absentes de 101, les portent nulles, comme toute lecture d'une
révision marquée. La description de la référence passe de `mockhistory` à `mockwitness`, que
`mockcore` lit (`mockcore.current`). `remaining.dom.test.tsx`, avec les colonnes des grandeurs
précédentes qu'EP-02/L36 a ajoutées à la grille, lit des valeurs affichées et leur format — la
charge précédente de la main-d'œuvre, 12,5, les débours unitaires précédents des borniers,
1 234,56, et de la provision, 250,00, la seule grandeur que la revue a changée depuis, et le montant
réestimé précédent —, et une ligne fusionnée qui n'en porte aucune : WF-RAE-0040-A n'y est plus
prouvé par des colonnes vides.

**Ce que ce lot laisse.** La structure de mille tâches et la décision 4 restent à EP-02/L27
(#376) ; d'ici là, les lignes de `volume/nodes_thousand.json` portent leurs grandeurs précédentes
nulles, la structure engendrée n'ayant pas de revue précédente. Aucun écart au contrat : la liste dit déjà un projet non consultable sous son libellé et
son code, sans lien (`can_open`, WF-PTF-0030).

### La structure en heures (EP-02/L27)

**La structure de mille tâches est celle du témoin, son cœur en tête, datée en heures** (#376 ;
WF-PLA-0010, WF-PLA-0160). `wftools.mockstructure` décrit, comme le cœur l'est dans
`mockwitness`, en tâches et en lignes, neuf phases tirées après lui — les approvisionnements à la
réception, les études étant le cœur —, chacune des trois lots, chaque lot ses tâches de travail en
trois chaînes et un jalon ; `wftools.mockcore` date le tout ensemble, en heures de travail sur le
calendrier des rôles de chaque tâche, le chiffre et l'émet. Les compteurs du §4.6.2 sont gardés :
mille tâches, dont les quinze du cœur, et cinq mille lignes, dont ses neuf — cinq sur chacune des
922 tâches de travail tirées et une sixième sur 381 d'entre elles. **Deux calendriers** : le
câblage est confié au monteur câbleur, toutes ses heures de main-d'œuvre, et ses 103 tâches
travaillent la semaine de quatre jours de dix heures (482) ; les autres, la semaine standard. Les
nœuds tirés ont des identifiants de leur famille, numérotés une fois d'après leur ligne de la
structure décrite (`mockwitness.GENERATED`) : une écriture qui retire ou ajoute une ligne au-dessus
ne les change pas.

**Le cœur est relié au réseau** (décision de l'utilisateur du 2026-10-05) : les lots « Poste de
commande » suivent sa réception usine, les deux autres la réception des études, et sa mise en
service mène au jalon de la mise en service du poste de commande. La structure finit le 30 août
2029. Le chemin critique part du cœur — études de détail, revue de conception, réception des
études, câblage des armoires, réception usine, qui reste au 30 juin (C13) — et suit les lots du
poste de commande ; les marges du cœur sont celles de toute la structure : 880,5 jours pour le
dossier de conception, sans successeur, 858,5 pour les tâches de la survenance, 597,5 pour le
montage sur site et la mise en service. Une marge se compte sur le calendrier de sa tâche : une
tâche qui suit une tâche du câblage en garde des demi-journées. **Une tâche manuelle borne ses
prédécesseurs** (WF-PLA-0100, #402, #464) : sa date posée à la main est leur fin au plus tard, une
marge peut être négative, et le chemin critique compte les marges nulles ou négatives.

**La structure est lue aujourd'hui, le 3 juin 2026.** **Rien ne se termine seul** (WF-RAE-0030) :
le générateur tient chaque fin automatique passée pour un geste fait à sa date, et seuls les jalons
attendent le leur — un jalon dont la date est passée reste non démarré tant qu'un geste ne le
termine pas ; la réception des études du cœur est déclarée terminée par un geste du 24 avril,
avant lequel elle se lit non démarrée, et aucun jalon tiré ne l'est.
Chaque récapitulative porte son avancement physique, comme celles du cœur ; chaque ligne son délai
de paiement — trente jours hors main-d'œuvre, zéro pour la main-d'œuvre, et dans le cœur zéro aussi
pour les lignes fusionnées par la survenance et pour la provision — ; chaque ligne tirée ses
grandeurs à la revue précédente, la référence, qui la portait telle qu'elle est. **La revue
précédente se lit une fois**, sur la structure décrite (`mockcore.REFERENCE`), jamais sur celle
qu'une écriture laisse : ce qu'une écriture saisit change les grandeurs d'aujourd'hui, jamais celles
de la revue (WF-RAE-0040), et une ligne qu'une écriture ajouterait n'en aurait pas.
**Aucune ligne tirée n'est une provision** : une ligne de provision n'est créée que par la
déclaration d'un risque (WF-DEV-0020, WF-RIS-0010), et le témoin en a trois ; la sixième ligne
est un transport, et le budget d'une ligne tirée est son montant. La seule provision de la
structure est celle de 751, budgétée aux 250 que la référence connaissait. Les lectures nommées du
cœur (`nodes`, `nodes_estimate`…) sont des lectures de cette structure, aux marges de toute la
structure ; `nodes_core`, `nodes_nested` et `nodes_summaries` sont désormais des variantes
contrefactuelles déclarées, le cœur lu seul (`mockcore.alone`) — marges jusqu'à la fin du cœur,
totaux du cœur —, ce que dit leur résumé. Les deux Kanban (`startable_tasks`,
`startable_tasks_milestone`) lisent toute la structure et n'en présentent que les tâches du cœur,
faute d'un filtre de `listStartableTasks` qui écarte les 985 autres : une tâche que le geste
n'écrit pas y a la même marge dans l'un et dans l'autre. Les phrases des exemples qui disent une
date, une marge, le chemin critique ou les tâches redatées sont tirées des valeurs, et un test
confronte chacune à ce qu'elle dit.

**Les écritures sont des différences de deux lectures de toute la structure** : leurs totaux sont
ceux des mille tâches, comme le contrat le veut, et les tâches qu'elles redatent celles de toute la
structure. Le montage sur site et la mise en service ayant de la marge jusqu'au jalon qu'ils
précèdent, `predecessor_set` ne redate que la mise en service, `estimate_line_redated` le montage
et la mise en service, et aucune marge de tâche sans successeur ne grandit : la fin de la
structure ne bouge pas. Les écritures que font les parcours portent sur les premières lignes tirées
après le cœur, les lignes 28 à 30 (`estimate_line_entered`, `paste_applied`), et `paste_applied`
passe par le même calcul que les autres, sans second chemin ; `task_lengthened` allonge
« Revue 2.1.27 » de quatre jours ouvrés, qui pousse « Reprise 2.1.30 » en 2027.

**La fusion de l'avenant 1 ne change que les montants budgétés des lignes que son différentiel
désigne** (WF-REV-0050, décision de l'auteur sur #467). Le câblage sur site et la mise en service
sur site, que l'avenant ne désigne pas, gardent le budget que l'offre leur avait fixé
(`mockwitness.OFFER_BUDGETS`), 9 420 et 5 880 : la révision 102 copie ces budgétés de la
référence, non des taux. Une révision n'a qu'un taux par catégorie, celui de son année de
référence (WF-DEV-0020, WF-REV-0060) : leurs montants réestimés, dans 101 comme dans 102, sont
ceux de 2026, 9 600 et 6 000 : la mise à jour des taux, acceptée à la création de 101
(`rate_update`), a changé les taux, donc les réestimés, jamais les budgétés que la fusion ne désigne
pas.
Le budget de référence passe à 120 534,56 et la marche de l'avenant à 2 865 ; la comparaison de
l'offre et de la référence dit ces deux lignes réestimées, non budgétées, et l'écart de
main-d'œuvre à l'année de référence reste 3 515 ; le devis d'aujourd'hui vaut 121 534,56, et le
reste à engager 21 234,56, ces deux tâches non démarrées y comptant leur budget projeté
(WF-RAE-0010). Un test d'invariant tient le budget de l'offre de toute ligne que l'avenant ne
désigne pas, un autre l'unicité du taux d'une catégorie dans chaque révision.

**Le reste des points repris** : les risques lus dans 102 citent les structures de 102, à leurs
identifiants propres, 204 à 206 (`structures`, #461 ; WF-DAT-0030) ; l'évolution des indices
choisit ses révisions d'après l'état du projet au marquage, lu dans `state_transitions`, et non
d'après la date ; les jalons suivis n'ont qu'une source (`mockwitness.TRACKED`), qu'un test
confronte aux inscriptions des nœuds ; les numéros du cœur sont rassemblés dans `mockwitness.N` ;
les corrélations gardent 960 à 989 et les collages prennent 990 à 999, 971 et 972 devenant 991 et
992 ; un jalon de durée nulle ne se lit en fin de journée que pour une liaison fin à début qui
l'entraîne, les minutes qui ne font pas un nombre exact d'heures sont refusées, et le refus des
liaisons FF et SF est éprouvé. Les tests de grille lisent l'adresse des nœuds dans les exemples
(#400).

**Ce que ce lot laisse**, à EP-02/L45 (#528) : **la décision 4 du cadrage n'est pas appliquée**.
Les indicateurs, l'histoire (offre, référence, comparaison), les risques et leur matrice, les
courbes, le plan de charge, les coûts réels et la ligne du témoin au portefeuille lisent encore le
seul cœur : le budget de référence qu'ils disent, 120 534,56, est celui du cœur, quand les lignes
de la structure en budgètent 65,6 millions. Porter 751 et 753 à l'échelle suppose que ces lectures
somment la structure entière — l'offre et la référence décrites sur les mille tâches, et des coûts
réels pour les tâches tirées déjà terminées —, ce qui déplace la réserve, les totaux et la
couverture. Le Kanban de toute la structure reste aussi à faire. Les résumés des indicateurs du
projet, de la courbe des coûts, du registre des risques, du Kanban et de la liste du portefeuille le
disent (« sur le seul cœur, jusqu'à EP-02/L45 »). Les écarts de `estimate_indicators_volume`, qui
rapportent le devis de la structure à la référence du seul cœur, mêlent les deux échelles ; les
dire non calculables demanderait un motif que `NotComputableReason` n'a pas : ils restent ceux du
témoin, en attendant L45.

## Les commandes manquantes et les mineurs des relectures (EP-02/L38)

Trois précisions du contrat, que la maquette demandait et qu'aucune décision nouvelle ne change :
elles suivent la spécification ou une convention déjà prise ; et une règle du front, sur la
décision de la revue du lot, pour le téléchargement d'un fichier que l'API produit.

**L'exclusion et la réintégration d'une ligne répondent par des exemples**
(`setActualCostTrackedScope`, #291 ; WF-CRE-0030, WF-CRE-0040). L'opération existait, sans exemple
de sa réponse : l'écran des coûts réels l'exerce désormais, guidé par `exclude_cost_lines`, et ses
tests ne reçoivent que des réponses du contrat. `actual_cost_excluded`, la facture des câbles du
pupitre exclue le 3 juin à 14 h 05 avec son motif, et `actual_cost_reinstated`, la réception du
client réintégrée le même jour, sont engendrés depuis la description du témoin
(`mockcosts.written`) : la ligne de la consultation, retournée, son audit mis à jour à l'instant de
l'écriture, et rien d'autre. La réponse ne porte pas les totaux : la page les relit, que le serveur
tient (WF-CRE-0040, « modifie immédiatement les deux premiers totaux ») ;
`actual_costs_after_exclusion`, engendré de même, est la consultation relue après l'exclusion, la
ligne passée du total suivi au total exclu.

**Un dépôt désigné pour un autre usage est refusé par champ** (`UPLOAD_PURPOSE_MISMATCH`, #353).
Le contrat disait qu'un import ne s'ouvre que sur un dépôt d'import et une restauration que sur un
dépôt de sauvegarde, sans dire le refus de l'autre. C'est un motif par champ de `VALIDATION_FAILED`
(422), dans la convention du catalogue : `fields` désigne le dépôt en défaut, `/upload_id` pour
`openImport`, `/external_backup_upload_id` pour `startRestore`, qui déclare son 422. Exemples :
`import_upload_purpose_mismatch`, `restore_upload_purpose_mismatch`. Écarté : un 409, qui dirait
l'état d'un objet, quand c'est la valeur d'un champ qui ne convient pas ; un code de premier niveau,
que le pointeur rend inutile.

**La borne d'une sauvegarde externe a un maximum** (`Installation.external_backup_max_bytes`,
`maximum`, #353). Le réglage restait sans plafond, quand celui d'un avatar en a un. La spécification
ne fixe pas la taille d'une sauvegarde, et un plafond métier serait une décision : le maximum est le
plus grand entier qu'un nombre JSON garde exact quand le front le lit, 2^53 − 1 octets, environ
8 Pio. Le dépôt d'un tel fichier ne passe pas par une action serveur de Next (#350, reporté à
EP-13).

**Le fichier qu'une tâche produit se télécharge en flux, par une route du front**
(`getBackgroundTaskResult`, #416 ; décision de la revue d'EP-02/L38, option b). Le serveur de Next
lit le résultat et le transmet tel qu'il vient, à `/tasks/[taskId]/result`, que le navigateur suit
comme un lien. Trois raisons : le contrat ne borne pas la taille d'un résultat, et une action
serveur tiendrait le fichier entier en mémoire, sur le serveur puis dans la page ; les actions
serveur de Next partent une à une, dans une seule file, qu'un long téléchargement retiendrait,
écritures et relectures du suivi comprises ; une route laisse le navigateur enregistrer le fichier
comme il vient. Un refus — non-2xx, dont le 409 d'un résultat expiré ou pas encore prêt, l'API
injoignable, une réponse sans nom de fichier ou sans type — renvoie le navigateur à l'écran d'où il
partait, l'adresse nommant la tâche et le refus, que le suivi dit par `OutcomeNotice` dans l'entrée
de la tâche, ou dans un avis de son panneau quand il ne peut relire la tâche. La route ne rend que
les types que le contrat déclare pour un résultat, et rien de ce qu'elle répond ne se garde en cache
(`Cache-Control: private, no-store`). Écarté : une action serveur qui rend le fichier en `Blob`, le
premier passage du lot. La même règle vaudra pour le téléchargement des sauvegardes (#519).

**Ce que ce lot laisse à l'auteur** (#353, confirmations demandées) : le contrat borne le dépôt d'un
import à 10 Mio, 10 485 760 octets (#324), là où la décision disait « 10 Mo » ; et les textes —
motif d'exclusion, colonnes conservées, libellés des tables plates — se comparent dans l'ordre des
points de code Unicode (#292), où « Z » vient avant « É » et « 100 » avant « 20 ». Le lot ne tranche
ni l'un ni l'autre.

## La profondeur des récapitulatives, la copie externe des sauvegardes, le journal d'audit (EP-02/L42)

Trois constats de contrat encore sans lot, rangés dans EP-02/L42 (#507) sur la décision de l'auteur
du 2026-10-08 ; cette partie, L42b, les ferme. Le front n'en adopte que ce qu'il faut pour rester
juste et vert : l'arborescence de tâches abandonne son heuristique, l'écran des sauvegardes lit la
copie externe, et rien ne lit encore le journal d'audit, dont l'écran est L41e (#517).

**`listNodes` dit la profondeur des récapitulatives de la structure** (#494 ; WF-PLA-0110). La
réponse porte désormais un `meta` exigé, `NodeListMeta`, et sa seule propriété, `summary_depth` :
le niveau de la plus profonde récapitulative de la structure lue, le premier étant celui des tâches
sans parent, quels que soient les filtres — `max_level` compris —, la recherche, `kinds` et
`fields` ; 0 pour une structure sans récapitulative. L'arborescence de tâches, qui lit les seules
récapitulatives jusqu'au niveau demandé, ne pouvait savoir s'il en existait une plus profonde :
elle offrait les niveaux de la réponse, et le suivant quand une récapitulative était au niveau
demandé — on n'allait pas du niveau 2 au niveau 4 d'un geste, et un arbre de N niveaux en offrait
un N+1 qui montrait le même arbre. Elle offre désormais exactement les niveaux de 1 à
`summary_depth`, et montre le niveau demandé, ou le plus profond qui existe quand on lui en demande
un au-delà. Un objet `meta` plutôt qu'un champ de premier niveau : il dit la structure, et non les
nœuds rendus, et accueillera ce qu'une lecture dira d'autre de la structure. Écarté : une opération
à part, une lecture de plus pour un entier que le serveur calcule en rendant l'arbre. Chaque
exemple de `listNodes`, engendré, le porte : 2 pour la structure du témoin et son cœur, 3 pour la
variante à quatre niveaux (`nodes_nested`, `nodes_summaries`, demandée au niveau 2), 0 pour le
planning de feuilles seules (`nodes_summaries_leaves`). Le faux back rendant la même réponse quel
que soit le niveau demandé, la profondeur qu'il dit reste juste, et le filtre que le front applique
encore à la réponse (EP-02/L36) n'y touche pas.

**La copie externe des sauvegardes planifiées nomme un emplacement que l'installation déclare**
(#488, proposition retenue avec l'auteur le 2026-10-08 ; WF-ADM-0170, WF-ADM-0150, WF-OBS-0030).
L'emplacement est atteint par le serveur, jamais par le navigateur : un compartiment S3 d'un autre
site, ou un partage réseau monté sur le serveur ; ses identifiants vivent dans la configuration de
déploiement et ne se saisissent jamais à l'écran. Ainsi :

- `ExternalBackupLocation`, en lecture seule, lu par `listExternalBackupLocations`
  (`GET /external-backup-locations`) : les emplacements que l'installation déclare, dans l'ordre de
  leurs noms, chacun avec son nom, sa nature (`ExternalBackupLocationKind` : `s3`,
  `mounted_share`) et sa description, nulle quand la configuration n'en dit rien ; aucun secret,
  aucun identifiant, aucune adresse qui en porterait. Aucune opération ne les crée ni ne les
  modifie. Le nom est la clé de configuration (`ExternalBackupLocationName`, minuscules, chiffres,
  `_` et `-`) : un objet que le serveur ne crée pas n'a pas d'UUID, comme un code de permission.
  La nature se nomme `kind`, le mot du contrat pour la nature d'un objet, et non `type` ;
- `BackupSchedule.external_copy`, facultatif (`BackupExternalCopy`) : `is_enabled`, `location`,
  `path` et `retained_count`, ces deux noms repris de `BackupSchedule` plutôt que les `enabled` et
  `retention` de la proposition, pour qu'un même mot ait un même nom dans le même objet. Absent,
  aucune copie n'est réglée ; une planification enregistrée sans lui retire la copie, `PUT` portant
  la planification entière. `path` est un chemin relatif (`ExternalBackupPath`) : des segments
  séparés par `/`, sans `/` en tête ni en fin, chacun commençant par une lettre, un chiffre ou `_`,
  ce qui exclut `.`, `..` et le segment vide. Le motif s'applique au texte entier, jusqu'à sa fin :
  `"a\n"` est refusé — un service qui l'éprouve par une expression dont `$` admet un retour à la
  ligne final la compare au texte entier. Un chemin qui ne s'y conforme pas est refusé par champ,
  comme #293 l'a décidé pour une valeur que l'utilisateur saisit : 422 `VALIDATION_FAILED`, `fields`
  désignant `/external_copy/path` (ou `/path` pour un test), motif `PATH_INVALID`, nouveau au
  catalogue, aucun motif existant ne disant un chemin (exemples `backup_schedule_path_invalid` et
  `external_backup_location_test_path_invalid`) ;
  le 400 reste à une requête que le serveur ne sait pas lire. Un nom d'emplacement que
  l'installation ne déclare pas est refusé de même, motif `UNKNOWN_EXTERNAL_BACKUP_LOCATION` sur
  `/external_copy/location`, `params.location` le nommant (exemple
  `backup_schedule_unknown_location`). `retained_count` borne les copies gardées dans ce dossier de
  l'emplacement, au moins autant que la plateforme garde de sauvegardes : WF-EXP-0050 veut les
  sauvegardes « conservées hors de la plateforme selon une rétention au moins égale à celle
  configurée sur la plateforme ». Un nombre moindre est refusé, motif `VALUE_OUT_OF_RANGE` sur
  `/external_copy/retained_count`, `params.minimum` disant la rétention de la plateforme (exemple
  `backup_schedule_retention_too_short`), paramètre que la description de `Problem.params` déclare
  et que le front dit (« Valeur minimale : 7. ») ; `test_mockuniverse.py` tient que chaque exemple garde au
  moins autant de copies. Le marquage à conserver ne vaut que pour les sauvegardes de la
  plateforme. Seule une sauvegarde
  planifiée se copie d'elle-même, comme WF-ADM-0170 le dit ; une manuelle sort de la plateforme par
  son téléchargement (WF-ADM-0150) ;
- `testExternalBackupLocation` (`POST /external-backup-locations/{location_name}/test`) : le
  serveur écrit puis efface un fichier témoin, à la racine de l'emplacement ou dans le dossier
  donné, et rend l'issue (`ExternalBackupLocationTest`) : le motif de l'échec en code, nul pour un
  test réussi (`ExternalBackupFailure` : injoignable, accès refusé, écriture ou effacement refusés,
  espace épuisé, délai dépassé ; WF-ARC-0110) — un drapeau `succeeded` le doublait, et deux champs
  qui disent la même chose peuvent se contredire (revue d'EP-02/L42b). Un verbe dans le chemin,
  comme `mark` et `merge` : un test n'est pas un état, et ne laisse rien. Il répond en 200 et non
  par une tâche de fond : il attend trente secondes au plus un emplacement qui ne répond pas, et dit
  leur dépassement comme un échec (`timed_out`). Un échec de test n'est pas une alerte ;
- l'échec d'une copie planifiée est une alerte de l'état du système, comme celui d'une sauvegarde :
  `Alert.code` gagne `scheduled_backup_copy_failed`, ses `params` nommant la sauvegarde
  (`backup_id`), l'emplacement (`location`) et le motif (`failure`) ; la sauvegarde elle-même a
  réussi, et `last_backup` le dit. Une alerte distincte de `scheduled_backup_failed` : l'exploitant
  n'a pas la même chose à faire d'une base non sauvegardée et d'une copie qui n'est pas partie.
  Elle disparaît à la copie réussie suivante. L'écran d'état dit aussi la dernière copie,
  `SystemStatus.last_backup_copy` (`OperationOutcome`, nulle sans copie réglée ou faite) : la copie
  hors plateforme se vérifie ainsi (WF-EXP-0050, « sa copie hors plateforme est vérifiée »). Le
  motif d'une copie échouée est dans l'alerte, et non dans `problem`, le catalogue des erreurs ne
  nommant pas les refus d'un emplacement. Exemple `system_status_copy_failed`, au même instant que
  les autres, chacun avec sa dernière copie — celle de la veille quand la sauvegarde de la nuit a
  échoué ;
- permissions : celles de l'écran des sauvegardes, `backups.read` pour la liste des emplacements,
  `backups.write` pour le test et la planification (WF-ADM-0100).

Exemples, écrits à la main comme l'état du système et les sauvegardes (« L'univers témoin ») :
`external_backup_locations` (le partage du NAS du siège et le compartiment du site de secours de
Lyon), `external_backup_locations_none`, `external_backup_location_tested` (le compartiment de Lyon
éprouvé aujourd'hui à 14 h 05) et `external_backup_location_test_failed` (variante
contrefactuelle : le partage du siège, accès refusé) ; `backup_schedule` copie chaque sauvegarde
vers Lyon, dossier `waterfall/sauvegardes`, trente copies gardées, `backup_schedule_disabled` garde
ce réglage, `backup_schedule_weekly` n'en a pas. `test_mockuniverse.py` tient que chacun nomme un
emplacement déclaré, et que l'alerte suit la dernière sauvegarde planifiée de la liste. L'écran des
sauvegardes dit la copie en lecture ; le formulaire qui la règle et le test viennent avec L43
(#519). La déclaration des emplacements dans Compose et dans Helm, et la copie elle-même, reviennent
à EP-13.

**Le journal d'audit se lit, et ne s'écrit que par les actions qu'il consigne** (#516 ;
WF-SEC-0030). `listAuditEvents` (`GET /audit-events`), en lecture seule, rend les inscriptions de
tous les projets et de la plateforme : `AuditEvent`, son identifiant, sa date (`occurred_at`,
l'instant où l'action a pris effet — celui où une tâche de fond a abouti, la date d'une
sauvegarde), son auteur (`ActorRef` : un compte, son identifiant et son nom affiché, ou `platform`
pour ce que la plateforme fait d'elle-même — une sauvegarde planifiée, un compte créé par
l'annuaire ou à sa première connexion —, et pour ce que l'installation crée), son action
(`AuditAction`), l'objet (`AuditObject` : sa nature, son identifiant, son libellé au moment de
l'action, nul pour une sauvegarde qui n'en a pas), le projet s'il y en a un (`AuditProject` :
identifiant, code, libellé), et l'identifiant de corrélation de la requête qui l'a produite
(WF-OBS-0020). Le libellé est gardé dans l'inscription, et non relu de l'objet : le journal d'un
projet terminé depuis cinq ans doit se lire tel quel, quand l'objet a changé de nom ou n'est plus
consultable. Aucune opération n'inscrit, ne modifie ni ne supprime une inscription : seule l'action
la produit (EP-03, US-0410).

- **Une action qui en produit d'autres les inscrit toutes**, au même instant et sous la même
  corrélation (décision de la revue d'EP-02/L42b) : la fusion d'un avenant inscrit
  `amendment_merge` sur la structure du différentiel, puis `revision_mark` et `reference_designate`
  sur la révision qui en résulte, que WF-REV-0050 marque et fait référence. Sans elles, le journal
  ne dirait ni le marquage ni la désignation de la référence en vigueur. `test_mockaudit.py` tient
  la complétude : chaque révision marquée a son `revision_mark` à son `marked_at`, et la référence
  son `reference_designate`.
- **La restauration face au journal** (WF-ADM-0160, tranché par l'auteur sur #539) : le
  journal est hors du périmètre qu'une restauration remplace — il est conservé aussi longtemps que
  les projets, et une restauration qui le ramènerait à la date de la sauvegarde effacerait ce
  qu'elle doit inscrire —, et l'inscription `restore` s'écrit une fois la restauration faite. Les
  descriptions d'`AuditEvent` et de `listAuditEvents` le disent. L'objet d'une restauration est la
  sauvegarde de la liste (`backup`, `backup_id`), ou le dépôt d'une sauvegarde copiée hors de la
  plateforme (`external_backup_upload`, l'identifiant du dépôt que `RestoreRequest` nomme,
  `external_backup_upload_id`, son libellé le nom du fichier déposé) : une nature à elle, le
  dépôt n'étant pas une sauvegarde de la liste, et le nom du champ de la requête qui le désigne.
- **Une préférence n'est pas une modification de compte** : le compte de la session a été modifié
  aujourd'hui par sa titulaire, ses préférences d'affichage, et le journal n'en dit rien.
  WF-SEC-0030 nomme les comptes qu'on crée et modifie, ce qu'un administrateur fait d'un compte,
  non ce qu'un utilisateur choisit pour lui-même ; `test_mockaudit.py` le tient.

- **Les actions** (`AuditAction`) suivent l'énumération de WF-SEC-0030, dans son ordre et dans les
  mots du catalogue des permissions et des tâches de fond : `revision_mark`, `reference_designate`,
  `amendment_merge` — la contractualisation d'un avenant, que la fusion de son différentiel réalise
  (WF-REV-0050) —, `risk_occurrence`, `project_exit`, `cost_line_exclude` et `cost_line_reinstate`,
  `import_apply`, `user_create`, `user_update`, `user_deactivate`, `user_reactivate`,
  `password_link_create` — le lien de mot de passe, que `createPasswordSetupLink` disait déjà
  inscrit, sans son jeton —, `access_role_create`, `access_role_update`, `access_role_delete`,
  `user_access_roles_set` — l'attribution des rôles —, `backup` et `restore`. La suppression d'un
  rôle est rangée avec sa modification, une désactivation de compte avec la sienne : WF-SEC-0030 dit
  « la création et la modification ».
- **Les filtres** se combinent : la période (`from` compris, `to` exclu), l'auteur (`user_id`), sa
  nature, un compte ou la plateforme (`actor_kind`, `AuditActorKind`), les actions (`actions`, une liste, au pluriel comme les autres filtres à plusieurs valeurs), le projet
  (`project_id`), la nature et l'identifiant de l'objet (`object_kind`, `object_id`) ; une période
  inversée est refusée par 422 comme celle des coûts réels. Le tri est celui des dates, décroissant
  par défaut (`sort_order`), deux inscriptions d'un même instant dans l'ordre de leur inscription,
  inversé dans l'ordre décroissant ; la pagination est celle des autres listes (`limit`, `offset`,
  `PaginationMeta`).
- **La permission** est une consultation, `audit_log.read`, nommée comme celles des fonctions
  (`<fonction>.read`), de la fonction que #518 ajoute sous l'administration, FBS-1.5
  « Journal d'audit » : `listPermissions` la range après les sauvegardes, `fbs_code` à `FBS-1.5`.
  Elle n'a pas de permission de modifier, le journal ne se modifiant pas — c'est la seule fonction
  du catalogue dans ce cas, et le front ne la compte pas parmi les fonctions de la navigation tant
  qu'elle n'y a pas d'écran (`FunctionPermission`, #517). Elle ouvre le journal entier : un projet
  s'y nomme par son code et son libellé, que l'appelant en soit contributeur ou non, comme les vues
  du portefeuille nomment les projets qu'elles comptent ; le lien vers l'objet ne vaut que pour qui
  peut le consulter (WF-ADM-0110). Les exemples l'accordent au rôle prédéfini d'administrateur et à
  « Direction de projet », qui porte tout le catalogue, donc aux sessions de Camille Martin.
  La spécification révisée par #518, relue et acceptée par l'auteur, porte la fonction FBS-1.5, et
  WF-ADM-0100 admet qu'une fonction en lecture seule n'ait que sa permission de consulter.
  L'attribution de cette permission aux rôles prédéfinis reste celle des exemples. L'écran
  des rôles nomme le groupe de cette permission par le catalogue (« Journal d'audit »), jamais par
  un code de la FBS, qu'aucun écran ne montre (décision de l'auteur).
- **Pas de volume** au §4.6.2 : le tableau des volumes ne compte pas le journal, et la convention ne
  crée un volume que pour une grandeur qu'il nomme.

Exemples engendrés par `make mock-data` (`wftools.mockaudit`), à partir de la chronologie du
témoin et des exemples écrits à la main qui datent chaque compte, chaque rôle et chaque sauvegarde,
sans rien inventer qu'un autre exemple ne dise : `audit_events`, le journal de l'installation le
3 juin 2026, trente-quatre inscriptions, les plus récentes d'abord — les rôles et les comptes de
l'installation, par la plateforme, chaque rôle avant les comptes qui le portent, les rôles composés
par Camille Martin et celui qu'elle s'attribue une fois créé, les comptes créés ensuite, Alix Moreau
désactivée, le marquage de l'offre, sa désignation comme référence, la fusion de l'avenant 1 avec
le marquage et la désignation de la référence qu'elle produit, la survenance de 752, les cinq
imports de coûts réels appliqués, l'exclusion de la réception du client, la sauvegarde manuelle du
30 janvier et les sept planifiées ; `audit_events_page`, sa deuxième page de dix ; `audit_events_project`, le
journal du témoin ; `audit_events_exited`, ce journal juste après la sortie du cycle de vie confirmée
aujourd'hui (`project_completed`), la sortie en tête ; `audit_events_empty`, les restaurations,
aucune. Deux familles d'identifiants engendrés naissent avec eux, les inscriptions et leurs
corrélations, une par requête (`mockids.IDENTIFIERS`, familles 7 et 8 ; les familles d'identifiants
quittent `mockwitness.py` pour `mockids.py`). L'auteur d'une inscription n'est lu dans l'audit de
son objet que là où cet audit a été modifié en dernier par l'action même, à son instant — le
marquage de l'offre, la fusion pour la référence, la survenance de 752 — : un audit dit qui a
modifié l'objet en dernier, pas forcément l'auteur de l'action inscrite. La désignation de l'offre
et l'exclusion de la réception du client, qu'un audit modifié depuis ne date plus, sont les gestes
de l'acteur du témoin, le créateur du projet, comme sa chronologie les a ; un import est de
l'auteur que nomme son journal (revue n° 2 d'EP-02/L42b). Ce que la même commande écrit — le
registre des risques, le journal des imports — est lu en mémoire, jamais sur le disque, pour que
`make mock-data` atteigne son point fixe en une passe ; un test tient que `mockaudit` ne lit par
`fixture` aucun exemple que `tools/paths.toml` déclare engendré. `test_mockaudit.py` tient aussi
chaque inscription à l'exemple qui dit son action, l'instant de l'audit dont son auteur vient, et
son auteur existant et actif à son instant. La page d'une liste est une seule constante,
`mocktext.PAGE`, lue du défaut de `Limit`. Le client est régénéré ; l'écran est L41e (#517).

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

**Les schémas sont groupés par famille**, un fichier par famille, et non un fichier par schéma —
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

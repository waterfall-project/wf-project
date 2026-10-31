# Décisions prises en écrivant le contrat

Ce que la spécification ne dictait pas et qu'il a fallu trancher pour écrire un contrat
cohérent. Chaque décision est réversible, mais aucune ne se change sans toucher plusieurs
dizaines d'opérations : c'est pourquoi elles sont écrites ici plutôt que découvertes.

## Forme des chemins

**Un état est une ressource, pas un verbe.** `PUT /users/{id}/activation`,
`PUT /projects/{id}/reference-revision`, `PUT .../actual-costs/{id}/tracked-scope` plutôt
que `/deactivate`, `/designate`, `/exclude`. Un `PUT` idempotent porte la valeur visée, ce
qui rend l'opération rejouable sans effet de bord — utile pour un client qui réessaie. Réécrit
le 2026-10-28 (décision de l'auteur, US-0702/L2) : la désignation de la référence porte le
compteur du projet, qu'elle écrit, et ne se rejoue plus telle quelle — le compteur a avancé,
refusée par 412, le client relit ; le périmètre suivi reste rejouable, sans compteur.
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

**Un jeton `bearer`, le jeton d'accès du fournisseur d'identité** (EP-03, US-0350/L1 ; défait
« témoin de session `httpOnly`, pas de jeton Bearer », décision d'EP-02). Le front obtient les
jetons du fournisseur d'identité côté serveur, les garde dans Redis sous un identifiant opaque
et ne donne au navigateur que cet identifiant, dans un témoin qui n'est pas celui de l'API : le
navigateur ne détient aucun jeton (WF-ARC-0030). Le front porte le jeton d'accès à l'API, qui le
valide et n'en tire que l'identité du compte ; les rôles et l'état du compte se lisent en base à
chaque requête (WF-SEC-0020). Le schéma de sécurité du contrat est donc `bearer` (`type: http`,
`scheme: bearer`, `bearerFormat: JWT`), non plus un témoin `wf_session` ; le motif de C-074, un
jeton qui circule dans des en-têtes que du code client pourrait stocker, vaut pour le navigateur,
et le navigateur n'en voit aucun. Écarté : garder la session ouverte par Waterfall, un mot de
passe reçu et une session conservée en base — contraire à WF-ARC-0030 (l'authentification est
déléguée), à WF-ADM-0140 (aucun écran de Waterfall ne demande de mot de passe) et au §4.4.1
(la session du front est dans Redis).

**Les permissions effectives sont renvoyées par `getMe`** (EP-02 : avec la session ; EP-03 :
avec le compte). Sans elles, le front ne peut
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
condition `may_create_revision` manquante (EP-02/L17). Les autres fonctions — rôles,
sauvegarde — n'ont pas de conditions à nommer : leurs commandes suivent la
permission de modification de la fonction, que la session porte, et la restauration sa
permission propre ; c'est la règle même du catalogue. Le référentiel en a trois, que chacun de ses
objets nomme sur sa commande (`ReferenceCommand`, EP-02/L42a), et les comptes une, le dernier
administrateur (`UserCommand`, `last_administrator`, EP-02/L42d). La saisie d'une révision est trois commandes —
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

**Un identifiant de chemin mal formé est un 404, un autre paramètre de chemin mal formé un
422** (EP-03/US-0330/L1). Un identifiant qui n'est pas un UUID ne peut nommer aucun objet : il
reçoit la réponse d'un objet inexistant ou invisible, 404 `NOT_FOUND` (README, 404 contre 403).
Tout autre paramètre de chemin refusé (`year`, `part_number`, `location_name`…) est une valeur
que l'opération refuse : 422 `VALIDATION_FAILED`, un champ par faute, au pointeur
`/path/<nom>` — par analogie avec `/query/<nom>` du paramètre de requête.

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
totaux mentir sous un filtre. Dans l'arbre, le tri ne réordonne que les lignes de devis sous
chaque tâche, et les tâches gardent l'ordre de l'arbre (#526, section « Le tri des grilles
arborescentes ») ; un filtre rend aussi les ancêtres des nœuds retenus. Le montant d'une récapitulative —
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
*Depuis US-0702/L1 (#1610, J-10, sur la règle des autres majeurs de l'auteur du 2026-10-28), une
propriété inconnue de `fields` est refusée par 422 `VALIDATION_FAILED`, `/query/fields` par
`FIELD_NOT_ACCEPTED`, comme tout paramètre de requête (EP-03, #799), et non plus par 400.*

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

*Réécrit en partie par US-0701/L3 (#1603, F-06, F-07 ; WF-PLA-0080 du 2026-10-09, recadrage du
2026-10-28) : l'état n'est plus une colonne (`NodeColumn`), la grille de planning le signalant
« par une marque visuelle et non par une colonne » ; le filtre `progress` reste, nommé comme la
propriété qu'il filtre. `listNodes` se filtre sur chaque colonne des trois grilles, par les bornes
et les périodes du README.*

**Les décaissements sont la courbe de coûts cumulés, décalée** (WF-IND-0100 ; WF-IND-0120
n'a jamais existé, la révision de la spécification du 2026-10-04 l'a dit : la projection de
décaissement est « la lecture en décaissements de la courbe en S »). `getProjectCashOut` et
`CashOut` disparaissent : `getCostCurve` prend `payment_delays`, qui décale chaque montant du
délai de paiement de sa ligne et ajoute les provisions des risques identifiés, et la réponse le
dit (`payment_delays`) et détaille alors les mois (`cash_out_by_month`, nul sinon). Le mois de
décaissement est un schéma partagé (`CashOutMonth`), que la courbe en S du portefeuille
réemploie (WF-PTF-0100, voir « Révision de la spécification du 2026-10-04 ») : le portefeuille
somme ce que les projets rendent.

*Remplacé en partie par US-0701/L5 (#1605, M-06 ; WF-IND-0100 des passes de cohérence des 9 et 10
octobre 2026, recadrage du 2026-10-28) : seuls le budget et la projection sont décalés, le coût réel
ne l'est pas, une ligne de provision reste à la date de sa tâche, et le reste à engager s'étale sur
la part de la durée postérieure à la date de calcul (« Les décaissements, la revue précédente, le
diagramme temps/temps et l'avancement d'une récapitulative », dans « Le contrat figé »).*

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

*Remplacé par US-0701/L1 (#1601) : la spécification a tranché les 10 et 22 octobre 2026 que les
montants budgété et réestimé sont « inflation comprise, à l'année de consommation de la ligne »
(WF-DEV-0020, WF-DEV-0050, glossaire), et l'auteur l'a suivie au recadrage du 2026-10-28 (L-01).
`inflated_amount` disparaît ; la grille de devis lit `base_amount` et `reestimated_amount`, et
`inflation` dit la projection du budgété et du réestimé (« Les montants inflation comprise », dans
« Le contrat figé »).*

**Le plan de charge nomme sa base** (`basis` : `reference_budget`, `marked_remaining` avec
`revision_id`, `current_remaining`, WF-DEV-0070). Sur un projet sans révision de référence,
seule la révision en cours est une base : les deux autres sont refusées par 409.

*Remplacé par US-0701/L2 (#1602, L-16) : WF-DEV-0070, réécrite le 2026-10-10, n'écarte sans
référence que la base de la référence et garde une révision marquée, calculée à sa date de
marquage ; décision du recadrage du 2026-10-28, « la règle des autres majeurs » (« Les révisions
et les structures », dans « Le contrat figé »).*

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

*Complété par US-0701/L4 (#1604, M-05) : WF-RIS-0060, réécrite le 2026-10-09, dit la place des
tâches fusionnées, leurs modes et le réestimé « que leurs grandeurs et leurs dates donnent » ;
`declareRiskOccurrence` les dit (« Les risques », dans « Le contrat figé »).*

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

*Remplacé en partie par EP-14/L42s : `by_order_item` n'est jamais nul ; chaque poste du lotissement
y est, celui qu'aucune tâche ne porte sans total (`order_item_without_task`, WF-DEV-0060).*

*Remplacé en partie par US-0450/L1 : le total par niveau est celui des lots, au niveau 1 du
lotissement, `by_work_package`, motif `work_package_without_task`, section « Le lotissement en lots,
postes et livrables ».*

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
2026-10-06 : le total reste). *La réserve est désormais un cumul à travers les références
(WF-RIS-0050 du 2026-10-09 ; US-0701/L4, M-01, « Les risques », dans « Le contrat figé »).*

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
`access_role_ids`, le nœud nul sans rattachement. Ils valent pour `UserSelf`, que `getMe`
rend. Écarté : des objets `{access_role_id, label}` à la place des identifiants, qui auraient
changé la forme que `setUserAccessRoles` écrit.

**Exemples**, dans l'univers des autres, au 16 mars 2026 : `users` et `users_page` (les comptes
de l'installation, par nom — Dominique Bernard de `me_directory`, Camille Martin de `me`,
Alix Moreau, désactivée, de `contributors`, et un compte venu du fournisseur d'identité, sans
rôle —, puis leur seconde page lue deux par deux) ; `permissions` (le catalogue, dans l'ordre de
`PermissionCode`) ; `access_roles` (les trois rôles prédéfinis tels que livrés, et celui, composé
de tout le catalogue, que porte `getMe`) ; `system_status` et `system_status_backup_failed`
(l'installation saine, puis la même au stockage des fichiers indisponible, la sauvegarde planifiée
échouée et signalée) ; `backups` et `backups_empty` (les sept sauvegardes de la rétention et une
manuelle marquée à conserver ; aucune ; une page demandée au-delà de leur fin, `backups_beyond` ;
une manuelle en vérification, une planifiée à la vérification échouée et une vérifiée,
`backups_unverified`) ;
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
EP-02/L26, cinq de 2025-T2 à 2026-T2 depuis US-0701/L6 (G-03) —, le premier non calculable,
faute de coût réel et de valeur planifiée : aucun projet n'avait encore commencé, ce que la courbe
en S tient aussi) ; la structure des coûts (`portfolio_cost_structure`,
`getPortfolioCostStructure` : le budget et le reste à engager par nature, dont les parts somment à
un — le budget hors lignes de provision depuis US-0701/L6 (G-15) —, et la main-d'œuvre du bureau
d'études électricité, le nœud des deux rôles qui travaillent sur les projets — le monteur câbleur,
de l'atelier de câblage, n'en a pas) ; les risques (`portfolio_risks`,
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

*Complété par US-0701/L6 (#1606, G-03 et G-05 ; WF-PTF-0010, WF-PTF-0070, recadrage du
2026-10-28) : l'évolution trimestrielle de la performance est une statistique de période, et la
structure des coûts et la courbe en S prennent `from` et `to` pour leurs projets terminés, avec la
même période par défaut et le même refus ; le plan de charge et la santé du pilotage ne prennent
pas de période, un projet terminé y étant sans effet (« Le portefeuille : horizon, projets
terminés, couverture, offres », dans « Le contrat figé »).*

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
`installation` (vingt gigaoctets). *`uploadFile` ne reçoit plus la sauvegarde : défait par
EP-03/US-0350/L1, décision 10.*

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

*Complétée par US-0701/L5 (#1605, M-11 ; WF-IND-0020, WF-IND-0030 et WF-IND-0060 des passes de
cohérence des 9 et 10 octobre 2026, recadrage du 2026-10-28) : la valeur acquise, le budget d'un
sous-projet et l'avancement physique d'une récapitulative sont hors lignes de provision ; ils ne se
lisent donc pas sur le montant budgété d'une tâche (« Les décaissements, la revue précédente, le
diagramme temps/temps et l'avancement d'une récapitulative », dans « Le contrat figé »).*

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

*Remplacé en partie par US-0701/L1 (#1601, spécification des 10 et 22 octobre 2026, recadrage du
2026-10-28) : `base_amount` reste le montant aux taux de l'année de référence, avant inflation,
une valeur de lecture ; les montants budgété et réestimé sont inflation comprise, à l'année de
consommation, et la grille de devis présente `base_amount` et `reestimated_amount`.*

**Le montant corrigé de l'inflation remonte à la tâche et aux totaux** (`TaskFacet.inflated_amount`,
`NodeTotals.inflated_amount`, `ComputedValueField` `task.inflated_amount`). Une récapitulative et le
total n'avaient pas de montant corrigé, et la grille montrait une cellule vide ; ils portent la
somme des montants corrigés de leurs lignes, que le front ne calcule pas.

*Remplacé par US-0701/L1 (#1601, spécification des 10 et 22 octobre 2026, recadrage du
2026-10-28, L-01) : `inflated_amount` disparaît de la tâche, des totaux et de `ComputedValueField` ;
leurs `budgeted_amount` et `reestimated_amount`, inflation comprise, le remplacent.*

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

*Remplacé en partie par US-0701/L1 (#1601, spécification des 10 et 22 octobre 2026, recadrage du
2026-10-28, L-01) : `NodeInflation` porte `budgeted_amount` et `reestimated_amount`, inflation
comprise, au lieu d'`inflated_amount` ; le budgété, projeté sur
l'année où la référence consommait la ligne, ne suit les dates que sur un projet sans révision de
référence, où il est confondu avec le réestimé (WF-DEV-0050).*

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
**Réécrit par US-0702/L3** (#1657) : le projet terminé ne liste aucun import, et le 409 de l'appel
direct nomme seul `project_not_terminal`.

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

*Remplacé en partie par US-0701/L5 (#1605, M-02 et M-03 ; WF-IND-0010 et WF-DAT-0040 des passes de
cohérence des 9 et 10 octobre 2026, recadrage du 2026-10-28) : les courbes d'une révision marquée
sont conservées avec ses indicateurs, `is_stored` vrai, sur les lignes de coût réel connues à son
marquage telles qu'elles étaient — le point ouvert est clos par la spécification ; et, sans
révision en cours, le calcul au jour courant se fait sur la dernière révision marquée avec le coût
réel du jour (« Les courbes au pas du mois, conservées au marquage », dans « Le contrat figé »).*

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
porte la réserve en plus du total général.

*Réécrit par US-0701/L4 (#1604, H-01, M-01) : la passe de cohérence de la spécification du
2026-10-09 compare à la réserve le **coût à la survenance** des risques survenus, le total de leur
devis propre au moment de la survenance, que ni réestimation ni terminaison ne changent
(WF-RIS-0010, WF-RIS-0050, glossaire), et non le coût réestimé des lignes issues des risques
survenus ; elle fait de la réserve un cumul à travers les références. Décision du recadrage du
2026-10-28, « Les risques » (« Les risques », dans « Le contrat figé »).* `CurveSeries.steps[].cause` ne connaît plus que
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

*Le paramètre `attached_node_id` est remplacé par EP-14/L42k : le refus nomme la tâche qui porte
déjà le poste ou le lot par `conflicting_object_id` et `conflicting_object_label`, son nœud et son
libellé — section « Le squelette, le rattachement, les chronologies et les nœuds retenus d'un
lotissement filtré (EP-14/L42k) ». Le texte ci-dessus est gardé pour l'histoire.*

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

*Réécrit par US-0701/L7 (#1607, I-09) : la date de terminaison d'une tâche qu'un import de
reste à engager termine est la date de la revue que porte le fichier, en « Synthèse », lue dès
l'analyse — `ImportCompletedTask.completed_on` n'est jamais nul pour un import —, et non plus le
jour de l'application : WF-INTF-0120 et WF-INTF-0130, réécrites les 9 et 10 octobre 2026, le
disent, contre WF-PLA-0130. Décision de l'auteur au recadrage du 2026-10-28, « La date de
terminaison par import » ; l'issue de spécification #1596 demande d'aligner WF-PLA-0130. La
fusion garde le jour de son application. Section « Les échanges », plus bas.*

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
`requestPasswordReset` dit le même lien pour le courriel (défait par EP-03/US-0350/L1, décision 5 :
le lien mène au fournisseur d'identité, `requestPasswordReset` disparaît). Exemple : `password_setup_link`.

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

*Deux points sont remplacés par EP-14/L42k, d'après la spécification acceptée par l'auteur le
2026-10-09 (WF-PLA-0170). Le refus de `setWorkBreakdown` : « Le déplacement d'un lot sous un autre
poste retire de même le rattachement de sa tâche lorsqu'elle n'est pas dans le sous-arbre de la
tâche de ce poste » ; la saisie aboutit et retire le rattachement, et `params.work_package_id`
disparaît avec le refus. Et « toute tâche » : « Le rattachement n'existe que dans la structure
principale » ; une tâche d'un différentiel ou du devis propre d'un risque n'en porte pas, et
l'écriture qui lui en pose un est refusée par `WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY`. Le texte
ci-dessus est gardé pour l'histoire.*

*Remplacé en partie par EP-14/L42s : la tâche du poste et celles des lots sont nommées par leur nœud
et leur libellé (`order_item_task`, `work_package_tasks`), et une ligne importée hors du sous-arbre
rejette le fichier entier (`ImportReport.refusals`).*

*Remplacé en partie par US-0450/L1 : l'imbrication s'inverse, des lots qui contiennent des postes ;
le refus devient `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, la tâche d'un poste hors du sous-arbre de celle
de son lot, nommées par `params.work_package_task` et `params.order_item_tasks`, et l'exemple
`task_attach_outside_work_package`, section « Le lotissement en lots, postes et livrables ».*

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

*Remplacé en partie par EP-14/L42r : `updateResourceRole`, `updateCalendar` et `setDefaultCalendar`
nomment les projets (`params.projects`, sans identifiant ni tâche, #762 option (a)) ; exemple
`calendar_update_without_hours`.*

*Remplacé en partie par EP-14/L42s : la tâche dont un rôle est le seul, que le calendrier de ce rôle
laisserait sans heure, est refusée de même — `createNode`, `updateEstimateLine`,
`updateResourceRole` —, `params.resource_role_ids` nommant ce rôle seul (#766).*

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

*Remplacé par US-0701/L1 (#1601) : depuis la spécification des 10 et 22 octobre 2026
(WF-DEV-0020 : les deux montants entrent « à ce titre » au budget de référence et au reste à
engager) et le recadrage du 2026-10-28 (L-01), les indicateurs de devis et de reste à engager sont
inflation comprise, à l'année de consommation : `total` vaut `NodeTotals.reestimated_amount`. Le
motif de #352 tient sur la nouvelle base — les parts somment à cent sur le seul réestimé —, et le
montant avant inflation n'est plus qu'une valeur de lecture de la grille.*

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

*Remplacé en partie par US-0701/L5 (#1605, M-02 ; WF-IND-0010 et WF-DAT-0040 des passes de
cohérence des 9 et 10 octobre 2026, recadrage du 2026-10-28) : WF-DAT-0040 conserve désormais les
séries des courbes avec les indicateurs, au pas du mois, et le coût réel d'une révision marquée est
celui connu à son marquage ; les courbes d'une révision marquée ne sont plus recalculées
(« Les courbes au pas du mois, conservées au marquage », dans « Le contrat figé »).*

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

*Remplacé en partie par US-0701/L5 (#1605, M-09 ; WF-RAE-0020 des passes de cohérence des 9 et 10
octobre 2026, recadrage du 2026-10-28) : la revue précédente de `delta_to_previous_revision` est la
révision marquée précédente qui l'a été à l'état En cours ; l'écart est nul quand aucune ne l'a été
avant celle qui est lue (« Les décaissements, la revue précédente, le diagramme temps/temps et
l'avancement d'une récapitulative », dans « Le contrat figé »).*

*Remplacé en partie par US-0701/L1 (#1601, E-02, recadrage du 2026-10-28) : `amount_deltas[].delta`
devient `budgeted_delta` et `reestimated_delta`, dans le même sens.*

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

*Réécrit en partie par US-0701/L7 (#1607, I-09 ; WF-INTF-0120 du 2026-10-09, recadrage du
2026-10-28) : un import de reste à engager démarre et termine une telle tâche à la date de la revue
que porte le fichier, non le jour de son application ; la règle de WF-RAE-0030 est inchangée.*

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
datée en heures, le cœur incrusté en tête et relié au réseau engendré, depuis EP-02/L27 (#376), et
les lectures du témoin somment toute cette structure depuis EP-14/L45a (#618) : la sous-section
« Les lectures sur toute la structure » dit lesquelles, et ce qu'elles valent. La décision 4 du
cadrage — 751 et 753 à l'échelle de cette structure —, décidée par l'auteur le 2026-10-07
(option (a)), est appliquée depuis EP-14/L45b (#619, fin de #528), et avec elle le registre des
risques, sa matrice, leur couverture et le Kanban lisent toute la structure : la sous-section
« Les risques à l'échelle et le Kanban de toute la structure » le dit. #287 est soldé.

Les sous-sections disent, lot par lot, ce que chacun a fait ; ce qu'une sous-section laisse est
repris par une suivante, ou renvoyé à EP-02/L27 (#376), puis à EP-14/L45a (#618) et L45b (#619).
Ce qu'une sous-section décrit et qu'une suivante a changé — la capacité des rôles, le cours des
projets du portefeuille, le budget de référence du témoin, la réserve pour risques et les gravités
de 751 et 753 — se lit dans la dernière qui en parle.

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
C14). `wftools.mockdating` date le cœur décrit dans `mockwitness` en heures de travail sur le
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
`reference-amount.dom.test.tsx` rend la grille sur `nodes_installation`, écrit le rôle du câblage sur site,
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

**Les risques, leur matrice, leurs réexamens et leur couverture sont engendrés** (#287). Les trois risques sont décrits une fois (`mockwitnessrisks.REGISTER`) : ce que l'utilisateur a
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

*Complétée par US-0701/L5 (#1605, M-10 ; WF-IND-0090 des passes de cohérence des 9 et 10 octobre
2026, recadrage du 2026-10-28) : les révisions marquées avant l'état En cours ne donnent aucun point
au diagramme temps/temps ; le point de l'offre que `milestone_tracking` gardait pour la réception
des études disparaît (« Les décaissements, la revue précédente, le diagramme temps/temps et
l'avancement d'une récapitulative », dans « Le contrat figé »). Il en va de même plus bas, à «
L'évolution des indices ne compte que les révisions marquées à partir de l'état En cours »
(EP-02/L24) : les révisions marquées avant l'état En cours ne donnent aucun point, et le suivi des
jalons ne garde plus celui de l'offre.*

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

*Remplacé en partie par US-0701/L1 (#1601, M-08) : depuis la spécification du 2026-10-22
(WF-RAE-0010) et le recadrage du 2026-10-28, une tâche non démarrée ne compte plus son budgété
projeté, mais le montant réestimé de ses lignes, calculé, faute de réestimation, depuis les
grandeurs de la référence aux taux conservés par la révision courante, sur son année de
consommation courante (« Le réestimé d'une ligne non réestimée », dans « Le contrat figé »).*

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
*Remplacé en partie par US-0701/L5 (#1605, G-01 ; WF-IND-0100 et WF-IND-0110 des passes de cohérence
des 9 et 10 octobre 2026, recadrage du 2026-10-28) : les séries se lisent au pas du mois, chaque
point le cumul à la fin du mois, et non plus à chaque jour (« Les courbes au pas du mois, conservées
au marquage », dans « Le contrat figé »). Il en va de même à la reprise du cœur (EP-02/L27) : la
règle d'EP-02/L24, un point par jour où un montant commence ou finit, n'est plus gardée, et le
budget de référence du témoin compte 46 points.*
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

*Remplacé en partie par US-0701/L5 (#1605, M-06 ; WF-IND-0100 des passes de cohérence des 9 et 10
octobre 2026, recadrage du 2026-10-28) : le reste à engager d'une tâche dont la fin est dépassée, et
la provision d'une tâche passée, sont portés entiers à la date de calcul, et non plus au premier
jour ouvré qui la suit (« Les décaissements, la revue précédente, le diagramme temps/temps et
l'avancement d'une récapitulative », dans « Le contrat figé »).*

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
WF-CRE-0050). `wftools.mockwitnesscosts` décrit les six lignes de coût — pièce, date, montant signé,
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

*Réécrit par US-0701/L7 (#1607, I-01 ; WF-CRE-0050 de la passe de cohérence des 9 et 10 octobre
2026, recadrage du 2026-10-28, « la règle des autres majeurs ») : le journal compte les lignes
créées, mises à jour, inchangées et rejetées (`CostImport.unchanged_count`, `rejected_count`) ;
`ignored_count` disparaît, et une ligne d'un autre projet compte parmi les rejetées.*

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

*Remplacé en partie par EP-14/L42s : une ligne de provision ne porte pas de délai de paiement
(WF-DEV-0020) ; elle le rend nul, et la courbe la laisse à la date de sa tâche (WF-IND-0100).*

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

*Remplacé en partie par US-0701/L6 (#1606, G-03 ; WF-PTF-0070, recadrage du 2026-10-28) :
l'évolution trimestrielle porte un point par trimestre civil que la période touche, de 2025-T2 à
2026-T2 pour la période par défaut, que `scope.from` et `scope.to` rendent ; les deux premiers sont
non calculables, et le dernier, lu à la date de calcul, égale les deux indices du jour, à quatre
décimales (G-08) — le témoin y compte sa valeur planifiée du jour, que sa courbe, au pas du mois, ne
porte pas (« Le portefeuille : horizon, projets terminés, couverture, offres », dans « Le contrat
figé »).*

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

*Remplacé en partie par US-0701/L6 (#1606, M-07 et G-04 ; WF-PTF-0080, WF-PTF-0090 et WF-PTF-0100 de
la spécification du 9 octobre 2026, constats C-122 et C-199, recadrage du 2026-10-28) : le choix
déclaré ne tient plus. Une offre incluse apporte à la courbe en S les courbes de son devis courant
pondérées par sa probabilité de gain, hors lignes de provision pour le budget de référence et
provisions comprises pour la projection ; la structure des coûts suit la même règle, et la vue des
risques compte ses risques sans pondération. `mockportfoliotime` tire pour chaque offre la part de
son devis que portent ses lignes de provision, de 2 à 8 %. La courbe court sur les douze mois qui
précèdent celui de la date de calcul, puis sur les `horizon_months` mois à partir de lui, six par
défaut, et non plus sur six mois de part et d'autre : de juin 2025 à novembre 2026 ;
`portfolio_cost_curve_credit` est lue à un mois d'horizon, de décembre 2024 à décembre 2025 (« Le
portefeuille : horizon, projets terminés, couverture, offres », dans « Le contrat figé »).*

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
facultatif (retiré par EP-02/L42e). Le taux de charge reste propre au plan agrégé du portefeuille (WF-PTF-0060), où
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

*Remplacé en partie par US-0701/L6 (#1606, G-06 ; WF-PTF-0090 de la spécification du 9 octobre 2026,
constat C-205, recadrage du 2026-10-28) : la réserve et la couverture agrégées sont les sommes de
celles des projets en cours et terminés du périmètre ; aucun projet de la liste n'est terminé, et
l'exemple ne change pas (« Le portefeuille : horizon, projets terminés, couverture, offres »,
dans « Le contrat figé »).*

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
révision marquée. La description de la référence passe de `mockhistory` à `mockwitnessrisks`, que
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
trois chaînes et un jalon ; `wftools.mockdating` date le tout ensemble, en heures de travail sur le
calendrier des rôles de chaque tâche, le chiffre, et `mockcore` l'émet. Les compteurs du §4.6.2 sont gardés :
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

*Réécrit par US-0701/L2 (#1602, L-14) : WF-REV-0050, réécrite le 2026-10-10, fait donner par la
fusion aux lignes désignées les grandeurs de référence du différentiel, et aussi leurs grandeurs
courantes quand la tâche n'est pas démarrée et que personne n'a réestimé la ligne ; les autres
lignes gardent grandeurs courantes et réestimé. Décision du recadrage du 2026-10-28, « la règle
des autres majeurs ». La ligne que l'avenant 1 désigne, d'une tâche alors non démarrée, change
déjà son budgété et son réestimé dans la comparaison : le témoin suit la règle nouvelle.*

*Remplacé en partie par US-0701/L1 (#1601, M-08, WF-RAE-0010 du 2026-10-22, recadrage du
2026-10-28) : les tâches non démarrées comptent au reste à engager le montant réestimé de leurs lignes, aux taux de 2026 que la
révision conserve, et non leur budget projeté, aux taux de l'offre.*

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

### Les lectures sur toute la structure (EP-14/L45a)

**Ce qui sommait le seul cœur somme la structure de mille tâches** (#618, partie de #528 ; décision
4 du cadrage de #287, option (a) de l'auteur du 2026-10-07, reprise par la conception d'EP-14,
« L'univers témoin à l'échelle »). Les indicateurs du projet, du devis et du reste à engager,
l'histoire — l'offre et la référence décrites sur les mille tâches, leur comparaison —, les courbes
de coûts et de valeur acquise, le plan de charge, les coûts réels et la ligne du témoin au
portefeuille lisent la structure entière, le cœur en tête, par les mêmes générateurs
(`mockindicators`, `mockcurves`, `mocktoday`, `mockhistory`, `mockcosts`), depuis la seule
description du témoin. Les résumés « sur le seul cœur, jusqu'à EP-02/L45 » de ces exemples
disparaissent. Écarté : un second jeu d'exemples figé pour les tests du front, qui ferait deux
univers ; les tests qui assertaient des valeurs du cœur sont réécrits sur celles de la structure.

**L'offre et la référence portent sur les mille tâches.** Toute ligne tirée était dans l'offre, et
l'avenant 1 n'en désigne aucune : une ligne de main-d'œuvre tirée garde dans la référence le budget
que l'offre lui avait fixé, ses heures au taux de 2025 de sa catégorie, et est réestimée au taux de
2026, comme « Câblage sur site » et « Mise en service sur site » (WF-REV-0050, WF-DEV-0020, #467) ;
une ligne de débours est budgétée à son montant. La marche de l'avenant 1 reste 2 865 ; la
comparaison de l'offre et de la référence dit 2 768 lignes réestimées sans être désignées, 2 770
nœuds modifiés, et un écart de main-d'œuvre de 177 541,25 — les 3 515 du cœur et 1,50 de l'heure
sur les 116 017,5 h tirées. Dans l'offre, la réception usine n'existait pas : ce qui la suit
aujourd'hui — le montage sur site, les lots du poste de commande tirés autour du cœur — suivait le
câblage des armoires, qu'elle termine, aux mêmes dates.

**Les tâches tirées déjà terminées reçoivent des coûts réels** (`mockcosts.drawn`, WF-CRE-0010,
WF-CRE-0020). Chaque tâche de travail tirée et terminée le 3 juin — 21, du 1er mai au 1er juin,
dans les lots « Ligne d'essais » et « Utilités » de la première phase, ceux du poste de commande
suivant la réception usine du 30 juin — a reçu la facture de son fournisseur, datée du jour de sa
fin, à quelques centièmes du montant de la tâche (de 90 à 110 %, tirés), imputée au sous-projet de
son lot par le code de son OTP (`SP-ESS`) ou au seul projet, apportée par les imports dont la
période couvre sa date — ceux d'avril et de mai, jamais le fichier sans période —, et numérotée
dans une famille d'identifiants qui lui est propre (`lignes de coût réel engendrées`). Le
sous-projet « Essais et mise en service » porte donc des coûts réels, et ne se supprime plus
(`subprojects`, WF-PRJ-0050) — `subprojects_with_actual_costs`, la lecture filtrée, coïncide depuis
avec la liste entière, et seul son paramètre la distingue ; `subproject_updated`, le sous-projet
renommé, le garde chargé, sans quoi la ligne relue serait redevenue supprimable dans la maquette —
ce que, depuis EP-14/L42l, sa citation par la référence marquée empêche aussi — ; la consultation
des coûts compte 27 lignes, le journal 22 lignes créées par l'import de mai.

**Ce que les exemples valent.** Le budget de référence passe de 120 534,56 à 65 430 697,64 — les
budgétés de la grille moins les 250 de la provision — ; la valeur planifiée de 101 223,69 à
1 671 458,13, la valeur acquise de 100 000 à 1 449 858,33 — les études de détail et les 21 tâches
tirées terminées —, le coût réel de 105 400 à 1 412 970,20, le reste à engager de 21 234,56 à
66 793 528,72, les tâches non démarrées y comptant leur budget projeté sur leur année de
consommation (WF-DEV-0040), d'où une projection du chef de projet de 68 206 498,92 et une marge de
-2 775 801,28 ; l'indice de coût vaut 1,0261 (nominal), l'indice de délai 0,8674 (vigilance), les
tâches tirées en cours ayant une valeur planifiée et pas encore de valeur acquise. Le devis vaut
65 605 723,89, celui de la structure : `estimate_indicators_volume` est désormais la lecture du
témoin lui-même, et les écarts qu'EP-02/L27 disait mêler deux échelles n'en mêlent plus qu'une
(−210 à la référence). La révision « Référence » conservait un reste à engager de 68 242 478,05.
La courbe des coûts porte le budget de référence jusqu'au 30 août 2029, en 756 points — la règle
d'EP-02/L24, un point par jour où un montant commence ou finit, gardée — ; la couverture des
risques ne change pas (910 face à 500 et 200). Le plan de charge compte 1 465,75 h d'ingénieur
électricien en juin 2026, dont les 12,5 du cœur ; la ligne du témoin au portefeuille est celle de
ses indicateurs, et les vues du portefeuille la somment.

*Remplacé en partie par US-0701/L1 (#1601, L-01 et M-08 ; spécification des 10 et 22 octobre 2026,
recadrage du 2026-10-28) : les montants sont inflation comprise, et
les tâches non démarrées comptent leur montant réestimé ; le reste à engager, le budget de référence
et le devis du témoin changent (« Le contrat figé »).*

**Les variantes déclarées.** `cost_curve_subproject_empty` et sa variante aux délais de paiement,
qui montraient un sous-projet dont aucune ligne ne relève, deviennent des variantes
contrefactuelles lues sur le seul cœur (`mocktoday.alone`), les lots « Ligne d'essais » relevant du
sous-projet « Essais et mise en service » dans la structure ; `nodes_core`, `nodes_nested` et
`nodes_summaries` restent celles d'EP-02/L27. Les sommes des courbes par maille retrouvent celle du
projet au centime de chaque maille près.

**Ce que ce lot laisse**, à EP-14/L45b (#528) : le registre des risques, sa matrice et sa
couverture lisent la gravité de 751, 752 et 753 sur le budget de référence du seul cœur
(`mockhistory.register_budget`), 12 000 valant un centième de centième de celui de la structure ;
les deux Kanban ne présentent que les tâches du cœur. Leurs résumés le disent
(`mocktext.CORE_ONLY`, « jusqu'à EP-14/L45b »).

**Le générateur à cette échelle.** Une structure est datée et émise une fois pour une date, des taux
et une revue précédente donnés (`mockcore.core`, `mockdating.schedule`), une révision lue une fois
(`mockindicators.read`) ; les flux d'une courbe sont sommés d'un coup une fois dépensés en entier et
lus un à un tant qu'ils courent (`mockcurves.Spread`), les bornes de chacun comptées une fois sur son
calendrier. `make mock-data` écrit le tout en une quinzaine de secondes.

### Les risques à l'échelle et le Kanban de toute la structure (EP-14/L45b)

**751 et 753 sont portés à l'échelle de la structure de mille tâches ; 752 garde les chiffres de son
Vérif** (#619, fin de #528 ; décision 4 du cadrage de #287, option (a) de l'auteur du 2026-10-07,
reprise par la conception d'EP-14, « L'univers témoin à l'échelle »). La gravité reste mesurée en
part du budget de référence (WF-RIS-0040, décision de #287) — celui de toute la structure,
65 430 697,64, que la provision ne touche pas (WF-RIS-0050) — ; `mockhistory.register_budget`, le
budget du seul cœur, disparaît, et avec lui les résumés « Lu sur le seul cœur du témoin, jusqu'à
EP-14/L45b » (`mocktext.CORE_ONLY`). La description du témoin dit l'échelle une fois
(`mockwitness.RISK_SCALE`) : les gravités que les réexamens de 751 et 753 retiennent sont leurs
chiffres du cœur multipliés par mille, et la ligne de provision de 751 dans le cœur porte la
provision du risque, budgétée à celle que la référence connaissait — un test tient l'une à l'autre.
« Risque de reprise du câblage » est identifié à 1 000 000 à 25 %, porté à 1 250 000, puis à 40 % :
sa provision vaut 500 000, et 250 000 au marquage de la référence. « Indisponibilité de
l'automaticien » est identifié et écarté à 12 000 000 à 5 % : 600 000 dans la référence. « Retard de
livraison des armoires » reste à 200 à 30 %, survenu, ses lignes de 120 et 80 (WF-RIS-0060).

**Ce que les exemples valent.** La réserve pour risques de la référence passe de 910 à 850 060 ; les
totaux du registre, de 500, 60 et 600 à 500 000, 60 et 600 000, leur somme de 1 160 à 1 100 060 ; la
couverture oppose 850 060 aux 500 000 de provision et aux 200 des lignes fusionnées, et l'écart passe
de 210 à 349 860. Dans la matrice, 751 est à 1,91 % du budget, au niveau 2 de gravité, dans la case
de vigilance où il était ; 752, sous le centième de pour cent, au niveau 1 ; 753, à 18,34 %, au
niveau 4, case (1, 4), de vigilance — sur le budget du seul cœur, il était à 9,96 %, au niveau 3,
case nominale. La provision suit dans toutes les lectures de la révision courante : le devis passe
de 65 605 723,89 à 66 105 223,89, ses provisions de 500 à 500 000, le lot « Poste de commande » de
2 934,56 à 502 434,56 ; le reste à engager de 66 793 528,72 à 67 293 028,72, la projection du chef de
projet de 68 206 498,92 à 68 705 998,92, la marge de -2 775 801,28 à -3 275 301,28, et l'avancement
financier du projet (`project_indicators`), le coût réel sur la projection, de 0,0207 à 0,0206 ;
la révision « Référence » conservait un reste à engager de 69 091 628,05, et non plus
68 242 478,05 ; le budget de référence, les indices et les courbes de valeur acquise ne bougent pas. **Les écarts de
`estimate_indicators_volume` sont à une seule échelle** : le devis de la structure face à la
référence de la structure, -349 860 — les 500 000 de provision et les 200 des lignes fusionnées,
face aux 850 060 de provisions que la référence portait. Le portefeuille somme ces lectures en
mémoire, comme avant : ses provisions identifiées, sa réserve agrégée et ses écartés suivent, et
ses projections du chef de projet gagnent les 499 500 de provision ajoutés au poste de commande — de
2 794 900 868,92 à 2 795 400 368,92 dans `portfolio_performance`, l'écart de 132 280 671,28 à
132 780 171,28 ; chaque point de la projection de `portfolio_cost_curve` après la date du jour,
jusqu'à 2 143 593 192,97 fin novembre ; la prévision de juin des décaissements de
`portfolio_cost_curve_payment_delays`, de 30 915 524,64 à 31 415 024,64.

**Les deux Kanban présentent toute la structure** (`startable_tasks`, `startable_tasks_milestone`,
WF-RAE-0030) : les 960 tâches qui ne sont pas des récapitulatives — 925 non démarrées, 8 démarrées
dont les pupitres opérateurs et le câblage des armoires, 27 terminées dont les 21 tâches tirées que
L45a a terminées —, et après le geste qui termine le câblage, 925, 7 et 28, la réception usine seule
signalée à terminer. Leur résumé compte chaque colonne et nomme les tâches du cœur, depuis la
réponse (`mocktext.kanban`) ; `mockdata.of_core` disparaît. Le contrat ne change pas :
`listStartableTasks` n'a ni filtre ni page, et la conception d'EP-14 veut le Kanban de toute la
structure.

**L'exemple trié du devis du poste de commande se trie par montant décroissant**
(`nodes_estimate_sorted`, #526). Trié par montant croissant, il plaçait la provision de 500 avant la
main-d'œuvre et le débours sous le câblage ; à 500 000, elle vient après eux, et le tri croissant
laisserait les lignes dans l'ordre du plan : l'exemple ne montrerait plus de tri, ni le Vérif de
WF-IHM-0060-A, « le tri par montant réordonne les lignes sous chaque tâche sans déplacer les
tâches ». Trié par montant décroissant, il renverse les trois lignes du câblage — la provision de
500 000, « Borniers » de 1 234,56, puis la main-d'œuvre de 1 000 — et laisse les tâches à leur
place ; sa phrase est tirée de sa réponse, comme celle du tri par heures (`nodes_estimate_hours`),
qui reste. Sous le tri décroissant, aucune ligne du câblage n'est suivie à l'écran de celle qui la
suit dans le plan : le collage sous un tri, refusé depuis la provision et accepté depuis
« Borniers », s'éprouve sur l'exemple trié par heures, où le débours et la provision se suivent
encore. Écarté : le tri par libellé, qui déplaçait aussi les lignes, mais ne prouvait plus le Vérif,
qui parle du montant, et rendait sous le câblage le même ordre que l'exemple trié par heures, qu'il
doublait.

**Options écartées.** Porter 751 et 753 à la même part du budget que sur le cœur (× 542,84) : des
montants sans rondeur, et 753 à 9,96 %, au ras de la borne de 10 % ; mesurer la gravité sur le seul
cœur, variante déclarée (option (c) soumise sur #376), que l'auteur n'a pas retenue ; porter aussi
752 à l'échelle, contre la décision 4, qui lui garde les chiffres de son Vérif ; un Kanban filtré au
cœur, que le contrat ne permet pas et que la conception écarte.

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

*Réécrit en partie par US-0701/L7 (#1607, I-07, K-07, L-19 ; WF-DAT-0120 du 2026-10-09,
recadrage du 2026-10-28) : le fichier d'un export est stocké jusqu'à son premier téléchargement
complet, ou vingt-quatre heures ; un résultat supprimé, téléchargé ou expiré, est un 404, et non
plus le 409 que la route du front recevait. La route n'en change pas : elle traite tout refus de
même.*

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
identifiant, code — nul pour un projet qui n'en avait pas encore —, libellé et `can_open`, qui dit
si le lecteur peut le consulter), et l'identifiant de corrélation de la requête qui l'a produite
(WF-OBS-0020). Le libellé est gardé dans l'inscription, et non relu de l'objet : le journal d'un
projet terminé depuis cinq ans doit se lire tel quel, quand l'objet a changé de nom ou n'est plus
consultable. Aucune opération n'inscrit, ne modifie ni ne supprime une inscription : seule l'action
la produit (EP-03, US-0410).

*Note du 2026-10-30 : la phrase sur `AuditProject` est réécrite ; la spécification a changé le
2026-10-09 (WF-ADM-0190), recadrage d'EP-16 décidé le 2026-10-28.*

- **Une action qui en produit d'autres les inscrit toutes**, au même instant et sous la même
  corrélation (décision de la revue d'EP-02/L42b) : la fusion d'un différentiel inscrit
  `structure_merge` sur sa structure, puis `revision_mark` et `reference_designate` sur la
  révision qui en résulte, que WF-REV-0050 marque et fait référence. Sans elles, le journal
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
  mots du catalogue des permissions et des tâches de fond : `project_create` et `revision_abandon`
  (#1577, plus bas), `revision_mark`, `reference_designate`, `structure_merge` — la fusion d'un
  différentiel (WF-REV-0050) —, `risk_occurrence`, `project_exit`, `cost_line_exclude` et
  `cost_line_reinstate`, `import_apply`, `user_create`, `user_update`, `user_deactivate`,
  `user_reactivate`, `password_link_create` — le lien de mot de passe, que `createPasswordSetupLink`
  disait déjà inscrit, sans son jeton —, `access_role_create`, `access_role_update`,
  `access_role_delete`, `user_access_roles_set` — l'attribution des rôles —, `backup` et `restore`.
  La suppression d'un rôle est rangée avec sa modification, une désactivation de compte avec la
  sienne : WF-SEC-0030 dit « la création et la modification ». La fusion s'est d'abord appelée
  `amendment_merge`, « la contractualisation d'un avenant » : la revue du contrat avant le gel
  (K-04, `2026-10-28-contrat-avant-gel.md`, US-0640/L6b #1594) l'a renommée `structure_merge`, à son
  rang, quand la spécification eut retiré « avenant » de WF-SEC-0030 (le 2026-10-09) — le nom que la
  permission et la tâche de fond lui donnaient déjà (EP-02/L29, #384) : un même geste ne porte plus
  deux noms dans le contrat. Le back sert encore `amendment_merge` jusqu'à EP-04 (#1577, plus bas).
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
  du catalogue dans ce cas, et le front la compte parmi les fonctions de la navigation, son écran
  venu, comme une fonction sans permission de modifier (`FunctionPermission`, EP-02/L41e, #517).
  Elle ouvre le journal entier : un projet s'y nomme par son code et son libellé, que l'appelant en
  soit contributeur ou non, comme les vues du portefeuille nomment les projets qu'elles comptent ;
  le lien vers l'objet ne vaut que pour qui peut le consulter (WF-ADM-0110). Les exemples l'accordent au rôle prédéfini d'administrateur et à
  « Direction de projet », qui porte tout le catalogue, donc aux sessions de Camille Martin, et à
  « Auditeur », un rôle composé qui ne porte qu'elle, celui de Noé Vidal (`me_auditor`) : la
  session d'un auditeur qui ne lit ni les comptes ni les projets dont il n'est pas contributeur
  (EP-02/L41e).
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

## Les listes du référentiel par pages, leurs filtres et leurs commandes (EP-02/L42a)

Quatre constats d'EP-02 rangés dans EP-02/L42 sur décision de l'auteur du 2026-10-08 (#509, #510,
#532, #533), chacun selon la proposition de son issue, sauf là où il est dit.

**Les listes du référentiel se paginent comme les autres** (#509, #510, #533).
`listResourceRoles`, `listCalendars`, `listCostTypes` et `listCostCategories` rendent `items` et
`meta` (`PaginationMeta`), sous `limit` et `offset`, comme `listUsers` ou `listProjects` ;
`meta.total` compte les objets que la recherche et les filtres retiennent. `getHourlyRateGrid`
aussi : la grille garde sa forme, `years` et `rows`, et gagne `meta` ; `rows` est la page, et
`years` les colonnes de toute la grille, quelles que soient la page, la recherche et le tri,
comme la recherche le faisait déjà (US-0250/L1). La spécification n'y oblige pas : l'auteur veut
des tables uniformes. `listOrgNodes` ne se pagine pas : un arbre ne se lit pas par pages, comme
`listNodes`. Une liste qui sert de choix — les catégories et les rôles d'une ligne de devis —
se lit page après page jusqu'au total, par la plus grande page, comme les révisions (#303).
Écarté : renommer `rows` en `items`, qui changerait la forme de la grille sans rien y gagner ;
laisser la grille seule de son espèce, sans pages.

**La grille des taux se trie sur chaque colonne** (#509, WF-IHM-0060). `sort_by` y vaut `code`,
`label`, `is_active`, ou `rate.<année>`, le taux de cette année : nommé comme
`passthrough.<colonne>` des coûts réels nomme une colonne qui n'est pas une propriété du schéma,
plutôt que `rate:2026`, que l'issue proposait. Une catégorie sans taux cette année-là vient après
les autres dans l'ordre croissant, avant dans le décroissant, comme une ligne sans valeur des coûts
réels ; à taux égal, ou sans taux, l'ordre du code, celui de la grille sans tri. Une année que la
grille ne porte pas n'est pas refusée : elle laisse l'ordre du code.

**Chaque colonne des tables du référentiel se filtre** (#533, #510, #545, WF-IHM-0060,
WF-IHM-0130). Les rôles par catégorie (`cost_category_id`) et par calendrier (`calendar_id`), en
plus du nœud ; les nœuds par code (`code`, qui le contient) et par profondeur (`level`) ; les
cinq listes et la grille par état, `is_active`, un paramètre partagé : vrai, les actifs seuls ;
faux, les désactivés seuls, sous la permission qu'exige `include_inactive`, auquel il prime —
`include_inactive` reste refusé sans sa permission, même quand `is_active` le rend sans effet : la
permission se juge sur la requête. Un filtre de l'arbre rend aussi les ancêtres des nœuds retenus,
comme sa recherche. La portée de chaque recherche est dite : le libellé pour les rôles et les
calendriers ; le code et le libellé pour les nœuds et la grille, comme avant, et pour les natures ;
le code, le libellé et le code comptable pour les catégories, le code comptable n'ayant pas d'autre
filtre. Les colonnes de nombres se bornent, selon la convention qui suit : les heures mensuelles et
l'effectif d'un rôle (`monthly_hours_min`, `monthly_hours_max`, `headcount_min`,
`headcount_max`), les heures de chaque jour d'un calendrier (`monday_min` à `sunday_max`), et le
taux d'une année de la grille (`rate_min`, `rate_max`, l'année nommée par `rate_year`, exigée avec
eux : un nom de paramètre ne peut pas porter l'année comme `rate.<année>` la porte dans une valeur de
tri ; une catégorie sans taux cette année-là n'est retenue par aucune borne). Le calendrier par
défaut ne se filtre pas : un seul l'est, que le tri par `is_default` met en tête.

**Une colonne de nombres se filtre par deux bornes, pour tout le contrat** (#545, décision de
l'auteur du 2026-10-08). `<colonne>_min` et `<colonne>_max`, nommées comme la colonne que
`sort_by` trie, toutes deux incluses, l'une ou l'autre ou les deux ; dans le type de la colonne, un
entier pour un entier, une chaîne pour un décimal exact (WF-DAT-0100). Une borne supérieure
inférieure à la borne inférieure est refusée par 422, `VALIDATION_FAILED`, `fields[]` désignant la
borne supérieure (`/query/<colonne>_max`) par `VALUE_OUT_OF_RANGE`, `params.minimum` la borne
inférieure donnée — la période inversée des coûts réels (#293) ne nomme pas son début, la borne la
nomme, que l'écran rappelle ; une borne qui n'est pas un nombre de son type, `/query/<borne>` par
`NUMBER_INVALID`. Exemples `resource_roles_bounds_inverted`, `calendars_bounds_inverted`,
`hourly_rate_grid_bounds_inverted`, et `hourly_rate_grid_rate_year_missing` pour une borne du taux
sans son année ; `rate_year` seul est sans effet. La profondeur des nœuds, entière, se borne de
même (`level_min`, `level_max`), `level` restant l'égalité que le filtre de la colonne emploie. Les
deux conventions — bornes et départage — sont au tableau de `docs/api/README.md`. Une grille qui ajoute une colonne de nombres ajoute ses deux
bornes. Écarté : un seul paramètre en intervalle (`10..20`), qu'il faudrait analyser et qu'aucune
liste du contrat n'emploie.

**Un tri à égalité se départage, pour tout le contrat** : par l'ordre de la liste sans tri, puis
par l'identifiant. Une liste paginée qui laisserait l'égalité au hasard de la base pourrait rendre
une ligne sur deux pages, et en omettre une autre. Les descriptions de `sort_by` du référentiel le
disent ; la règle vaut pour toute liste triée.

**Les heures d'un jour d'un calendrier se trient** (#533) : `sort_by` prend `monday` à `sunday`,
une colonne de la grille chacun ; `weekly_hours`, leur somme, reste, pour une colonne qui la
montrerait.

**Chaque objet du référentiel porte sa commande** (`available_commands`, #532, WF-IHM-0090), sur
le modèle de `Risk.available_commands` : `ReferenceCommand`, `deactivate` ou `reactivate`, et ses
conditions manquantes. Un objet ne porte que celle qui change son état : l'une est le contraire de
l'autre, par la même opération, et un écran qui présenterait la réactivation indisponible sur
chaque objet actif dirait ce qui va de soi. Trois conditions s'ajoutent à `CommandCondition` :
`org_node_parent_active` et `org_node_active` (WF-REF-0080), `calendar_not_default`
(WF-REF-0120). La commande suit la permission de modification de la fonction
(`resource_settings.write`, `cost_settings.write`) : la liste est vide pour qui lit le référentiel
sans elle, l'estimateur qui choisit le rôle d'une ligne. Une image figée par une révision marquée
n'a pas de commandes : `EmployedReference` lit `ResourceRoleImage`, `CalendarImage` et
`CostCategoryImage`, auxquels l'objet lu aujourd'hui ajoute les siennes
(`ReferenceObjectCommands`). Écarté : la commande `update`, que rien ne rend indisponible ;
`set_default` des calendriers, indisponible pour un calendrier désactivé, laissée au lot qui
l'offrira.

**Les opérations d'activation déclarent leurs refus** (#532). Les cinq déclarent le 412,
`STALE_LOCK_VERSION`, `params.expected_lock_version`, comme toute écriture qui porte une version
(#296). Le 409, `STATE_FORBIDS_OPERATION`, `params.missing_condition`, là où une condition existe :
la réactivation d'un nœud sous un parent désactivé (`org_node_parent_active`) ou d'un rôle sous un
nœud désactivé (`org_node_active`), `params.conflicting_object_id` nommant le nœud à réactiver
d'abord, puisque WF-IHM-0090 veut que le refus dise ce qu'il faut faire ; la désactivation du
calendrier par défaut (`calendar_not_default`), dont le 409 était déclaré sans son code. Les
natures et les catégories n'ont pas de 409, à l'écart de l'issue, qui le proposait sur les cinq :
aucune exigence ne conditionne leur activation — une catégorie se réactive même sous une nature
désactivée —, et un 409 déclaré sans cas promettrait un refus que le serveur ne fait jamais.

*Remplacé en partie par EP-14/L42s : C-291 est au contrat — « une catégorie ne peut être réactivée
que si sa nature est active » (WF-REF-0010) —, et `setCostCategoryActivation` déclare son 409,
`cost_type_active`.*

**La réactivation ne cascade pas** (WF-REF-0080). L'exigence dit la cascade de la désactivation —
les descendants du nœud et les rôles rattachés à lui ou à l'un d'eux —, et rien de la
réactivation. Le contrat la lit sans cascade : réactiver un nœud ne rend actif que lui, et ses
descendants se réactivent un à un, chacun sous un parent redevenu actif ; la réponse de
`setOrgNodeActivation` ne porte alors que lui. Le motif de l'exigence va dans ce sens — les rôles
d'un service fermé sont recréés sous les nouveaux nœuds, non ranimés —, et une réactivation en
cascade ranimerait d'un coup ce qu'une réorganisation a fermé, y compris ce qui l'était avant elle.
Ni la désactivation d'un rôle, ni celle d'un calendrier, d'une nature ou d'une catégorie ne
cascade : aucune exigence ne le dit, et WF-REF-0020 laisse les projets intacts.

**Exemples.** `resource_roles`, `calendars` et `cost_types`, écrits à la main, prennent `items` et
`meta`, et chacun de leurs objets sa commande, comme ceux d'`org_nodes`. Le référentiel compte un
service fermé : le bureau d'études automatismes (474), désactivé sous la direction technique, et
sous lui la cellule robotique (475), désactivée avec lui. `org_nodes_with_inactive` est l'arbre lu
avec eux, le premier réactivable, la seconde non, `org_node_parent_active` manquante ; `org_nodes`,
l'arbre lu par défaut, ne les rend pas, comme `calendars` ne rend pas la semaine de trente-neuf
heures. Le programmeur d'automates (455), désactivé avec son service, est le rôle du Vérif de
WF-REF-0080 : `resource_roles` le porte, sa réactivation indisponible, `org_node_active`
manquante, et `resource_role_reactivation_refused` est son refus.
`resource_role_activation_stale` est la réactivation de l'automaticien envoyée avec la version que
`resource_role_reactivated` a dépassée. Engendrés par `wftools.mockreference` : les deux cents
catégories lues en une page de cinq cents, comme une liste de choix les lit, et leur deuxième page
de cinquante (`cost_categories_page`) ; la grille entière en une page, et sa première page triée
par le taux de 2026 décroissant (`hourly_rate_grid_by_rate`), ses quinze années toutes là. Les
catégories engendrées viennent dans l'ordre du code, celui de la liste sans tri.

**Une lecture sans droit d'écriture, et les refus de l'activation, ont leurs exemples** (revue de
L42a). `*_reader` — `org_nodes_reader`, `resource_roles_reader`, `calendars_reader`,
`cost_types_reader`, `cost_categories_reader` — est chaque liste lue par une session qui ne peut
pas modifier sa fonction : les objets actifs seuls, puisqu'elle ne peut pas demander
`include_inactive`, et aucune commande ; le front s'en remet à `available_commands` et ne vérifie
plus la permission. Engendrés par `wftools.mockreference` des listes écrites à la main, comme
`org_node_reactivated` — le bureau d'études automatismes réactivé, seul, la cellule robotique et le
programmeur d'automates restés désactivés — et `resource_roles_bounded`, les rôles d'au moins
485 324 heures mensuelles, celles du technicien de mise en service, retenu par la borne incluse ;
`hourly_rate_grid_bounded`, les catégories dont le taux de 2026 atteint 99,12, celui de MO-066 et
de MO-137, retenues avec lui. Écrits à la main : `org_node_reactivation_refused` (la cellule robotique,
`org_node_parent_active`, son parent nommé), `calendar_deactivation_refused` (la semaine standard,
`calendar_not_default`), `calendars_with_inactive` (la semaine de trente-neuf heures, 483,
réactivable), `org_node_activation_stale` et `calendar_activation_stale`.

**`DEFAULT_CALENDAR_REQUIRED` est retiré du catalogue.** Aucune réponse ne le déclarait ; la
désactivation du calendrier par défaut est refusée par `STATE_FORBIDS_OPERATION`,
`params.missing_condition` à `calendar_not_default`, comme toute commande qu'un état rend
indisponible : un seul code pour un seul refus.

**Une écriture qui change la disponibilité d'autres commandes ne les rend pas** :
`setOrgNodeActivation` change la réactivation des enfants et des rôles du nœud, `setDefaultCalendar`
la désactivation de deux calendriers ; le client relit les listes, comme ces opérations le disent.
`HourlyRateGrid.years` dit enfin ce que sont les colonnes sans `include_inactive` : les années que
portent les catégories actives, une année que seules des désactivées portent n'en étant pas une.

## Le tri des grilles arborescentes (EP-02/L42c)

**Une grille arborescente ne trie que les lignes de devis sous chaque tâche** (#526, décision de
l'auteur du 2026-10-08, option (a)). Le contrat disait que le tri de `listNodes` ordonnait les
nœuds frères entre eux sans défaire l'arbre : trier le devis par montant aurait aussi déplacé les
tâches. Il suit désormais la spécification (WF-IHM-0060) : les tâches et leurs sous-arbres gardent
l'ordre de l'arbre, et le tri ne permute les lignes d'une tâche qu'entre les places que ses lignes
tiennent. Des lignes d'une même valeur gardent l'ordre du plan, comme tout tri à égalité ; une
colonne de la seule tâche, que les lignes n'ont pas, les y laisse donc toutes. `row_number` ne
change pas, ni les totaux. La description de `sort_by` dit quelles grilles trient : le devis et le
reste à engager, par les colonnes qu'ils présentent pour les lignes ; le planning ne trie plus
depuis #525, ni le diagramme de Gantt, l'arborescence de tâches ou une chronologie. Écartée,
l'option (b) : réviser §3.4 pour que le tri déplace les tâches — une tâche ne change pas de place
parce qu'on trie des montants, et MS Project, que la spécification prend pour modèle, ne le fait
pas.

**Deux lignes se comparent comme partout ailleurs dans le contrat** (revue d'EP-02/L42c). Un
nombre par sa valeur ; le libellé en texte, et la catégorie, le rôle et le sous-projet par leur
libellé, caractère par caractère dans l'ordre des points de code Unicode, comme les textes des
coûts réels et des tables plates (#292, #387) ; une ligne sans valeur — un débours sans heures, une
ligne sans rôle ou sans sous-projet — vient après les autres dans l'ordre croissant, avant dans le
décroissant, comme une ligne sans valeur des coûts réels ou une catégorie sans taux de la grille
des taux (#509). La description de `sort_by` le dit ; celle de `NodeColumn` ne laisse plus croire
que le planning trie.

Deux exemples, engendrés par `wftools.mocksort` (`LineSort`, ses colonnes typées comme celles de
la ligne que nomme `NodeColumn`) et ordonnés par `wftools.mockcore`, lisent le devis du lot
« Poste de commande » : `estimate_sorted`, trié par montant à l'année de référence, croissant —
sous le câblage, la provision, la main-d'œuvre puis le débours (revu par EP-14/L45b : trié depuis
par montant décroissant, la provision, le débours puis la main-d'œuvre) ; le jalon de réception
usine, de montant nul, que le tri des frères aurait mis en tête, reste le dernier — et `estimate_hours`,
trié par heures, décroissant — le débours et la provision, sans heures, d'abord, dans l'ordre du
plan, puis la main-d'œuvre. Sous un tri, le
collage d'un bloc qui écrirait dans une ligne du plan autre que celle affichée à la suite est
refusé par le front, la garde de L41a, quelle que soit la colonne.

## Le dernier administrateur, les nœuds désactivés, le journal trié et ses facettes (EP-02/L42d)

Trois constats d'EP-02 rangés dans EP-02/L42 (#507) : #540, #547 et #550, chacun selon la
proposition de son issue, sauf là où il est dit. Les écarts à ces propositions sont des décisions
de l'agent de livraison du lot, chacune avec sa raison, qui est l'exigence appliquée à la lettre ;
aucune n'est une décision de l'auteur.

**Un compte porte ses commandes** (`User.available_commands`, #540 ; WF-ADM-0120, WF-IHM-0090), sur
le modèle de `Risk.available_commands` et de `ReferenceCommand` : `UserCommand` vaut `deactivate`,
`reactivate` — un compte ne porte que celle qui change son état, l'une étant le contraire de l'autre
par la même opération — et `set_access_roles`, toujours listée. Toutes suivent `users.write` : la
liste est vide pour qui lit les comptes sans pouvoir les modifier. WF-ADM-0120 veut qu'au moins un
compte actif porte les permissions de modifier les comptes et les rôles d'habilitation ; le front ne
peut pas trouver ce compte lui-même — il ne rapproche pas les rôles des comptes (WF-ARC-0020), et la
liste est paginée. Le compte le dit donc : une condition s'ajoute à `CommandCondition`,
`last_administrator`, qui manque à la désactivation du dernier compte actif qui porte
`users.write` et `access_roles.write` ; elle redevient disponible dès qu'un second compte actif
les porte. **L'attribution de ses rôles reste disponible**, à l'écart de l'issue, qui la proposait
indisponible — décision de l'agent de livraison, appliquant WF-ADM-0120 à la lettre : l'exigence
n'interdit que de *retirer* au dernier administrateur l'une de ces permissions, et lui en donner
davantage reste possible ; une commande n'est présentée indisponible que si elle l'est
(WF-IHM-0090). Le compte de la session n'a pas ces commandes : `UserSelf` lit désormais
`UserAccount`, le compte sans ses commandes, que `User` complète des siennes, comme
`ResourceRoleImage` et `ResourceRole` — la session ne s'administre pas par elle. Écarté : une
commande de modification du compte (`update`), que rien ne rend indisponible.

**Deux refus du dernier administrateur, selon ce que la commande dit d'avance** (#540). La
désactivation, que la commande annonce indisponible, est refusée comme toute commande qu'un état
rend indisponible : 409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à
`last_administrator` (`setUserActivation`, exemple `user_deactivation_refused`). Le retrait d'une
permission par `setUserAccessRoles` ou `updateAccessRole` dépend des rôles ou des permissions
envoyés : aucune commande ne peut le dire d'avance, la commande restant offerte. Il est refusé par
409 `LAST_ADMINISTRATOR`, sans condition, comme `LAST_PROJECT_MANAGER` refuse une liste de
contributeurs qui ne garderait aucun chef de projet (exemples `user_access_roles_refused`,
`access_role_update_refused`). `LAST_ADMINISTRATOR` reste donc au catalogue — décision de l'agent de
livraison sur la revue du lot : la retirer, comme le premier passage le faisait sur le modèle de
`DEFAULT_CALENDAR_REQUIRED` (EP-02/L42a), aurait nommé une condition qu'aucune commande ne porte
manquante, et fait mentir le critère de US-0360 d'EP-03 et sa conception, que ce lot précise.
`setUserActivation`, `setUserAccessRoles` et `updateAccessRole` déclaraient un 409 sans son code ou
générique ; ils le nomment, rien n'étant écrit. `users` et `users_page`, écrits à la main, portent
les commandes de chaque compte : Camille Martin, seule active à porter ces permissions, a sa
désactivation indisponible et l'attribution de ses rôles disponible ; `test_mockuniverse.py` le
tient, calculé des rôles, et lie le code de chaque refus à sa commande. Les corrélations écrites à
la main ayant rempli leur plage, elles en prennent une seconde, 1010 à 1099 (`mockids`).

**Créer ou déplacer un objet actif sous un nœud désactivé est refusé par champ** (#547 ;
WF-REF-0080). La règle n'était tenue que par les opérations d'activation ; `createOrgNode`, sous un
parent désactivé, `updateOrgNode`, qui y déplacerait un nœud actif, et `createResourceRole`, sous
un nœud désactivé, sont refusés par 422, `VALIDATION_FAILED`, `fields` désignant `/parent_id` ou
`/org_node_id` par `INACTIVE_REFERENCE_OBJECT`. Décision de l'agent de livraison, que l'issue
laissait ouverte, appliquant la convention des refus par champ (#293, et `UPLOAD_PURPOSE_MISMATCH`,
EP-02/L38) : la valeur d'un champ ne convient pas — elle désigne un objet que WF-REF-0010 ne propose
plus à la saisie —, l'objet écrit n'a pas d'état qui l'interdise, et le motif existe pour cela,
celui d'une ligne de devis qui emploierait un objet désactivé. Le 409 `STATE_FORBIDS_OPERATION`
reste à la réactivation, où c'est l'état de l'objet même qui change, et que sa commande dit
d'avance. Un nœud désactivé se déplaçait sous un nœud désactivé : il n'y était pas actif, et le motif
de l'exigence, qu'aucun objet actif ne subsiste dans un service fermé, tenait — exception retirée par
EP-14/L42j, WF-REF-0070 révisé ne déplaçant un nœud que sous un nœud actif. Exemples
`org_node_creation_refused`, `org_node_move_refused` (l'atelier de câblage, actif, vers le bureau
d'études automatismes) et `resource_role_creation_refused`, sous le bureau d'études automatismes,
désactivé ; `test_mockuniverse.py` les tient.

**Un rôle ne change pas de nœud** (#547). Décision de l'agent de livraison, appliquant le
§3.4.4.2.1 : « les rôles ne se déplacent pas d'un nœud à l'autre, ils sont recréés sous les
nouveaux nœuds ». `ResourceRoleUpdate` perd `org_node_id`, et ne reprend plus `ResourceRoleWrite`,
dont il garde le reste ; `updateResourceRole` n'a donc plus de rattachement à refuser. Le nœud se
fixe à la création.

**Le journal se trie sur chacune de ses colonnes** (#550 ; WF-IHM-0060, qui veut chaque colonne
d'une table plate triable). `sort_by` de `listAuditEvents` vaut `occurred_at`, par défaut, `actor`,
`action`, `object_kind`, `object_label`, `project` et `correlation_id`. L'auteur se compare par son
nom affiché, le libellé de l'objet tel que l'inscription le garde, le projet par son code et la
corrélation, en points de code Unicode, comme les textes des tables plates (#292) ; la plateforme,
qui n'a pas de nom, un objet sans libellé — une sauvegarde — et une inscription sans projet viennent
après les autres dans l'ordre croissant, comme une valeur nulle. L'action et la nature de l'objet se
rangent dans l'ordre de leur énumération — celui de WF-SEC-0030 pour `AuditAction` —, à l'écart de
la comparaison des libellés, décision de l'agent de livraison : l'API ne rend pas leur libellé, que
le front choisit dans la langue du lecteur (WF-ARC-0110), et un tri par le code anglais ne suivrait
l'ordre d'aucune langue. Une égalité se départage par l'ordre sans tri, puis par l'identifiant
(EP-02/L42a). `sort_order` absent vaut décroissant pour la date, croissant pour une autre colonne.
Exemples `audit_events_by_actor` et `audit_events_by_object_label`, triés par `mockaudit.sorted_by`.

**Le journal se filtre par corrélation et se cherche sur le libellé de l'objet** (#550 ;
WF-IHM-0130, WF-OBS-0020). `correlation_id` retient les inscriptions d'une requête et de la tâche
de fond qu'elle déclenche — la fusion d'un avenant et les deux inscriptions qu'elle produit
(`audit_events_correlation`) ; `search`, le paramètre partagé, porte sur le libellé que l'inscription
garde, sans égard à la casse (`audit_events_search`, les imports de coûts réels de mai, cherchés
dans une autre casse que la leur). Une sauvegarde, sans libellé, n'est retenue par aucune recherche.

**Un objet qui vit dans une révision la nomme** (`AuditObject.revision`, `AuditRevision`, #550),
par son identifiant et son nom de version au moment de l'action, nul pour une révision en cours qui
n'en a pas : le risque, dans la révision dont le registre le porte — pour une survenance, la
révision en cours où elle fusionne son devis propre (WF-RIS-0060) —, le différentiel d'un avenant,
dans la sienne (`CostStructure.revision_id`), l'import d'un planning, d'un devis ou d'un reste à
engager, dans celle où il s'applique (WF-INTF-0090). **Une ligne de coût réel et l'import des coûts
réels n'en ont pas**, à l'écart de l'issue, qui les citait — décision de l'agent de livraison,
appliquant WF-INTF-0090 et WF-CRE-0010 : une ligne de coût est imputée au projet et à son
sous-projet, non à une révision (WF-CRE-0010), et seuls les imports d'un planning, d'un devis ou
d'un reste à engager s'appliquent à une révision (WF-INTF-0090) ; `listActualCosts` et
`listCostImports` vivent sous `/projects/{project_id}`. Leur inventer une révision dirait faux. Le
projet, une révision elle-même, un compte, un rôle, une sauvegarde et un dépôt n'en ont pas non
plus. Le champ est exigé, nul quand il ne s'applique pas, comme `AuditEvent.project`. Dans les
exemples, la survenance de 752 nomme la révision en cours, 102, et la fusion de l'avenant 1 la
révision 101, « Référence » ; `audit_events_import_applied`, le journal du témoin juste après
l'application de l'import du devis analysé ce matin — la suite de `task_import_succeeded`, à
14 h 08 min 30 s, par Camille Martin —, nomme pour cet import la révision en cours, 102, sans nom
de version. Comme la sortie du cycle de vie (`audit_events_exited`), c'est une variante : l'une ne
suit pas l'autre, et leurs inscriptions ont chacune leur identifiant et leur corrélation. La description de `CommandCondition`, qui citait WF-INTF-0080 pour
dire que l'import des coûts réels n'écrit pas dans la révision, cite de même WF-INTF-0090 et
WF-CRE-0010.

**Les auteurs et les projets du journal se lisent à part** (`listAuditFacets`,
`GET /audit-events/facets`, #550 ; WF-SEC-0030, WF-ADM-0100, WF-IHM-0130). Les filtres de l'écran
s'appuyaient sur `listUsers`, offert seulement avec `users.read`, et sur `listProjects`, qui n'offre
que les projets ouvrables, quand `audit_log.read` ouvre tout le journal : un auditeur, dont la
fonction en lecture seule n'a que la permission de consulter (WF-ADM-0100), ne pouvait filtrer ni
par auteur ni par projet. L'opération rend `AuditFacets` : les comptes auteurs d'au moins une
inscription, désactivés compris, par leur nom affiché d'aujourd'hui, et les projets d'au moins une
inscription, consultables ou non, par leur code et leur libellé d'aujourd'hui, chacun une fois, par
nom ou par code puis par identifiant. Elle ne prend **aucun filtre** — le journal entier —,
décision de l'agent de livraison, sur la recommandation de l'issue : une liste de choix qui se
viderait au gré des autres filtres empêcherait d'en changer un sans lever les autres, et le journal
entier se calcule une fois. **Sans pagination** : au plus autant d'auteurs que de comptes et de
projets que l'installation en conserve, soit au plus 500 comptes et 600 projets conservés sur vingt
ans aux volumes du §4.6.2 — une réponse de l'ordre de cent kilo-octets, quand une page de cinquante
inscriptions en pèse une vingtaine. La plateforme n'y est pas, `actor_kind` la retient. Gardée par
`audit_log.read` comme `listAuditEvents`, 404 sans elle ; un sous-chemin du journal, comme
`risks/matrix` l'est des risques. Exemple engendré, `audit_facets` : la seule autrice, Camille
Martin, et le témoin.

**`PermissionCode` ne dit plus que la spécification « doit » donner FBS-1.5** (#550) : #518 est
fusionnée, et sa description dit la fonction « Journal d'audit » que WF-ADM-0100 admet en lecture
seule ; le résumé d'`access_roles` perd son « à confirmer par #518 ».

Engendrés par `wftools.mockaudit` : `audit_events_by_actor`, `audit_events_by_object_label`,
`audit_events_import_applied`,
`audit_events_correlation`, `audit_events_search`, `audit_facets`, et la révision de l'objet dans
toutes les lectures du journal ; `test_mockaudit.py` les tient au journal, et éprouve le tri, la
recherche et les facettes sur des inscriptions de synthèse. Le client est régénéré ; le front les
adopte.

## Les filtres des listes du projet et les courbes d'un sous-projet (EP-02/L42e)

Les quatre premiers constats de #536 et son sixième, rangés dans EP-02/L42 (#507). Le cinquième —
les filtres par colonne des comptes, des rôles d'habilitation et du lotissement — reste ouvert dans
#536. Les décisions sont de l'agent de livraison du lot, chacune avec sa raison ; aucune n'est une
décision de l'auteur.

**L'accueil nomme les états qu'il retient** (`ProjectListMeta.states`, #536). `listProjects`
partage `states` avec les vues du portefeuille (`PortfolioStates`), dont le défaut, les projets en
cours, est le périmètre de WF-PTF-0010. La spécification ne fixe aucun défaut d'état pour
l'accueil : WF-IHM-0120 n'y nomme que le filtre des projets dont l'utilisateur est contributeur, et
son Vérif — un contributeur de deux projets les voit à sa connexion — veut un accueil qui nomme tous
les états, ce que le front fait. Décision de l'agent de livraison : le défaut ne change pas, et la
réponse dit les états retenus, nommés ou par défaut, chacun une fois, dans l'ordre de
`ProjectState`. Changer le défaut du paramètre partagé aurait changé six vues du portefeuille, que
WF-PTF-0010 fixe ; donner à `listProjects` un paramètre à lui, de même nom et d'un autre défaut,
aurait fait d'un nom deux règles. Un client qui ne nomme aucun état ne lit donc que les projets en
cours, et le lit dans `meta.states` ; l'accueil, qui les nomme toujours, montre ceux de son adresse.
`projects` et `projects_empty`, écrits à la main, nomment les six états, comme l'accueil
les demande ; `projects_default_states`, engendré, rend les projets en cours seuls.

**L'accueil se filtre par période sur l'instant de la dernière modification** (`from`, `to`, #536,
#522). #522 demande un filtre par période sans dire sur quoi ; la liste n'a qu'une colonne de date,
la dernière modification (`audit.updated_at`), que `sort_by` trie déjà. Décision de l'agent de
livraison, appliquant WF-IHM-0130 — toute table se filtre sur chacune de ses colonnes — : la période
borne cet instant, dans la forme du journal d'audit (`listAuditEvents`), sur la revue du lot : deux
`Timestamp`, le début inclus, la fin exclue. Le front tire ces instants des jours de son lecteur —
mars à Paris va de `2026-02-28T23:00:00Z` à `2026-03-31T22:00:00Z` —, ce qu'un jour en temps
universel, le premier passage, ne permettait pas : une modification faite à 23 h 30 UTC le 28 février
est du 1er mars à Paris. Une colonne d'horodatage se filtre donc comme le journal, une colonne de
dates de planning comme les coûts réels. Écartée : la période du portefeuille (`PortfolioFrom`), qui
ne retient que les projets terminés dans la période (WF-PTF-0010) — elle ne dit rien d'un projet
d'un autre état, et l'accueil n'est pas une vue du portefeuille. Exemples `projects_period`, mars à
Paris, et `projects_period_inverted`. La recherche porte sur le libellé et sur le code, comme #522 le
demande : `projects_search_code` trouve l'offre par son code, qu'aucun libellé ne contient. Le tri dit
enfin comment il compare : les textes en points de code, un projet sans code après les autres dans
l'ordre croissant, l'état dans l'ordre du cycle de vie (`ProjectState`), une égalité par l'ordre
sans tri, puis l'identifiant (EP-02/L42a) ; `projects`, écrit à la main, suit cet ordre, les plus
récemment modifiés d'abord, et `test_mocklists.py` le tient de chaque exemple de `listProjects`.

**Une période inversée est refusée par une seule règle, pour tout le contrat** (revue du lot). Une
fin qui précède le début : 422 `VALIDATION_FAILED`, `fields[]` désignant `/query/to` par
`VALUE_OUT_OF_RANGE`, `params.minimum` le début donné, comme une borne supérieure inférieure à
l'inférieure (#545) ; un début ou une fin mal formés, `/query/from` ou `/query/to` par
`DATE_INVALID`. `listProjects`, `listActualCosts` et `listAuditEvents` la déclarent :
`actual_costs_period_inverted`, qui ne nommait pas le début, le nomme, et le journal gagne son
exemple, `audit_events_period_inverted`, ainsi que `DATE_INVALID`. La convention est au tableau de
`docs/api/README.md` ; `test_mockuniverse.py` tient chaque exemple `*_period_inverted` à la règle, le
début dans le type de `from`. Une fin égale au début est une période vide pour un instant, d'un jour
pour une date, jamais un refus.

**Une maille inconnue est refusée** (`scope`, revue du lot ; WF-IND-0020). Un sous-projet que le
projet n'a pas, ou un identifiant mal formé : 422 `VALIDATION_FAILED`, `fields[]` désignant
`/query/scope` par `UNKNOWN_SUBPROJECT`, comme le sous-projet des coûts réels (#293), plutôt que des
indicateurs nuls qu'on prendrait pour ceux d'un sous-projet vide. Les cinq opérations qui prennent
`scope` le déclarent : `getEstimateIndicators`, `getProjectIndicators`, `getCostCurve`,
`getEarnedValueCurves` et `getIndexHistory`, exemple `indicators_scope_unknown`, écrit à la main ; le
paramètre partagé le dit.

**Les sous-projets se trient et se filtrent sur chaque colonne** (#536 ; WF-IHM-0060,
WF-IHM-0130). `sort_by` vaut `code`, l'ordre sans tri, `label` et `has_actual_costs` ; la colonne
des coûts réels range ceux qui en portent d'abord dans l'ordre croissant, comme l'état des comptes
range les actifs et la nature des rôles les prédéfinis. Le code et le libellé se filtrent par la
recherche, qui les lisait déjà ; la colonne des coûts réels par `has_actual_costs`. **Aucune
borne**, à l'écart de la demande, qui proposait `_min` et `_max` sur les colonnes de coûts réels —
décision de l'agent de livraison : `Subproject` ne porte aucun montant, seulement le fait qu'un coût
réel lui est imputé, qui le rend insupprimable (WF-PRJ-0050). Les bornes valent pour une colonne de
nombres ; en inventer une ici — le coût réel du sous-projet — ajouterait à la liste un calcul que
WF-PRJ-0050 ne demande pas, et que les indicateurs restreints au sous-projet rendent déjà
(WF-IND-0020). Exemples `subprojects_by_label` et `subprojects_with_actual_costs`.

**Les contributeurs se cherchent, se trient et se filtrent** (#536). `search` porte sur le nom
affiché du compte, la seule colonne de texte de la liste ; `is_active` filtre l'état du compte, un
compte désactivé depuis l'inscription restant listé (WF-ADM-0060) ; `kinds` filtrait déjà la
qualité. `sort_by` vaut `display_name`, comparé en points de code, `kind`, dans l'ordre de
`ContributorKind`, les chefs de projet d'abord, et `is_active`, les actifs d'abord. Sans tri, les
chefs de projet d'abord, puis le nom de famille et le prénom du compte, l'ordre des comptes
(`listUsers`) : celui que `contributors`, écrit à la main, suivait sans que le contrat le dise. Le
compteur restait celui de toute la liste, quels que soient le tri et les filtres : `setContributors`
écrit la liste entière (WF-IHM-0110) — revu par EP-02/L42f, une lecture filtrée n'ayant plus de
compteur. Exemples `contributors_by_name`, `contributors_search` et
`contributors_inactive`.

**La courbe de coûts cumulés et l'évolution des indices se restreignent au sous-projet** (`scope`,
#536, #495 ; WF-IND-0020), comme `getProjectIndicators` et `getEarnedValueCurves`. Restreinte, la
courbe ne compte que les lignes de la maille — budget, coût réel par date de pièce, reste à engager,
provisions —, et sa marche est ce que l'avenant a changé du budget de la maille ; l'évolution des
indices rend la seule maille demandée, et chaque maille sans `scope`, comme avant. `context.scope`
nomme la maille. **Le diagramme temps/temps ne prend pas de sous-projet**, à l'écart de la demande —
décision de l'agent de livraison, appliquant WF-IND-0020 à la lettre : « Le diagramme temps/temps se
calcule pour le seul projet : il suit des jalons, qu'un sous-projet n'a pas. » Sa description le
dit. Exemples engendrés par `wftools.mocktoday` : `cost_curve_subproject`, le poste de commande —
la marche de l'avenant 1, tout son budget, l'offre ne déclarant aucun sous-projet, puis son budget
cumulé sur les dates de la référence —, et `index_history_subproject` ; `test_mocktoday.py` tient que les courbes des mailles
somment celle du projet, à chaque date qu'elles partagent avec elle — le coût réel à chaque date de
la sienne —, avec et sans les délais de paiement, et les décaissements mois par mois.

**Une maille sans rien à tracer rend des séries sans point** (revue du lot). Les essais et la mise en
service ne portent aucune ligne du cœur ni aucun coût réel : leur courbe, qui faisait échouer le
générateur, rend ses trois séries sans point, aucune marche et, avec les délais de paiement, aucun
mois de décaissement — `cost_curve_subproject_empty`. Décision de l'agent de livraison : `CurveSeries`
exige ses séries, non leurs points, et une série vide dit « rien à tracer », que l'écran dit, là où
une série de zéros ferait croire à un budget nul planifié. Une marche ne se rend que si l'avenant
change le budget de la maille : celle des essais n'en a aucune, celle du poste de commande la sienne.
Une seule série peut aussi être sans point : `cost_curve_subproject_unbudgeted`, variante
contrefactuelle déclarée, lit le poste de commande comme si l'avenant 1 n'avait pas été
contractualisé — l'offre, qui ne déclarait aucun sous-projet, restant la référence, la révision en
cours et les pièces inchangées. Le témoin n'a pas de maille à lignes ou à pièces sans budget ; cette
variante l'obtient sans toucher à l'univers, comme `cost_curve_amendment` en ajoute un second, et
l'écran y éprouve un budget sans point à côté d'un coût réel et d'une projection tracés.

**Le plan de charge d'un projet perd `load_ratio`** (#536 ; WF-DEV-0070, WF-PTF-0060). Le champ
restait facultatif et sans description depuis la décision de l'auteur sur #375, option b, qui
retire le taux de charge du plan d'un projet ; le retirer du schéma dit qu'aucun service ne le
calcule pour un projet. `zone` reste, et se décrit : l'alerte d'un mois dont les heures dépassent la
capacité du rôle, nominal sinon. **Elle ne vaut plus jamais `watch`** (revue du lot) : la vigilance du
plan de charge est la sous-charge, un taux de charge sous le seuil que l'utilisateur choisit
(WF-PTF-0060), sans base dans un plan qui n'a pas de taux ; WF-DEV-0070 ne demande que la capacité en
regard. Ses valeurs sont restreintes à `nominal` et `alert`, celles d'`AlertZone`, par un schéma à
lui, `WorkloadZone`, dont le front catalogue les deux libellés. Le plan agrégé du
portefeuille garde son `load_ratio`, exigé, et sa vigilance.

Engendrés par `wftools.mocklists`, des listes écrites à la main (`projects`, `subprojects`,
`contributors`) : `projects_default_states`, `projects_search_code`, `projects_period`,
`subprojects_by_label`, `subprojects_with_actual_costs`, `contributors_by_name`,
`contributors_search`, `contributors_inactive` ; `test_mocklists.py` éprouve le tri, la recherche et
les filtres sur des lignes de synthèse. Le client est régénéré ; le front les adopte.

## Les écritures des paramètres de coûts (EP-02/L43a)

Les écritures des natures et des catégories de coût, que les écrans de la maquette exercent (#512),
reçoivent chacune l'exemple de leur succès, la suite d'une écriture faite aujourd'hui par Camille
Martin, le 3 juin 2026 à 14 h 05 : `cost_type_created` (la nature FRN « Fournitures », hors
main-d'œuvre, 464), `cost_type_updated` (les débours renommés « Débours et achats », version 2),
`cost_type_deactivated` (les débours désactivés, version 2, leur réactivation offerte),
`cost_category_created` (FRN-001 « Petites fournitures » sous les débours, code comptable 606001,
406), `cost_category_updated` (la sous-traitance renommée « Sous-traitance générale », version 2) et
`cost_category_deactivated` (le matériel électrique désactivé, version 2). Chacun ne vaut que pour
la réponse de son écriture : aucune lecture n'en tient compte. Les refus que ces écritures
opposeraient, que le contrat ne disait pas (« Interface contract issue » relevée par EP-02/L43a,
#562), sont dits par EP-02/L42g, section suivante.

## Les filtres des comptes, des rôles d'habilitation et du lotissement (EP-02/L42f)

Le cinquième constat de #536, détaché en #560, et son complément sur les périodes du portefeuille,
rangés dans EP-02/L42 (#507). Les décisions sont de l'agent de livraison du lot, chacune avec sa
raison ; aucune n'est une décision de l'auteur. Les noms suivent la convention du contrat plutôt que
ceux que l'issue proposait : un filtre porte le nom de sa colonne — `has_actual_costs`,
`is_active`, `is_critical` —, une borne celui de la colonne qu'elle borne (`<colonne>_min`, #545),
et un filtre à plusieurs valeurs est au pluriel.

**Les comptes se filtrent par leurs rôles d'habilitation** (`access_role_ids`, #560 ;
WF-IHM-0130, WF-ADM-0050). Une liste d'identifiants, séparés par des virgules comme toute liste
de la requête, au pluriel comme `origins` et le champ `User.access_role_ids` qu'elle filtre ;
`access_role_id`, proposé par l'issue, aurait nommé au singulier un filtre à plusieurs valeurs. Un
compte est retenu dès qu'il porte l'un au moins des rôles nommés — la colonne présente plusieurs
rôles par compte, et l'écran choisit les rôles qu'il veut voir, comme les origines. Un compte sans
rôle n'est retenu par aucune valeur ; un identifiant qui ne désigne aucun rôle ne retient aucun
compte, sans refus, comme `org_node_id` un nœud inconnu : les valeurs viennent de
`listAccessRoles`. Écarté : une valeur « aucun rôle », à la manière d'`unassigned` des
sous-projets, qu'aucune exigence ne demande. Exemple `users_by_access_role` : les porteurs du chef
de projet ou du manager, Alix Moreau, désactivée, comprise.

**La recherche des comptes porte sur le nom, le prénom, l'adresse et le nom affiché** (#560). Ce
sont les trois textes que WF-ADM-0050 donne à un compte, et le nom affiché — le prénom, une espace,
puis le nom —, que la liste des contributeurs cherche déjà (EP-02/L42e) : « Camille Martin » trouve
le compte, qu'aucune colonne ne porte entier. Le texte se compare comme toute recherche, sans égard
à la casse ni aux accents (paragraphe suivant). Le paramètre est propre à l'opération, comme celui
des contributeurs, le paramètre partagé disant « le libellé », qu'un compte n'a pas. Exemple
`users_search` : « ines roux » trouve Inès Roux par le prénom suivi du nom, sans son accent ni
sa casse. *Reformulé par EP-03/US-0350/L1, décision 7 : le comportement ne change pas, le « nom
affiché » n'est pas un champ du contrat.*

**Une recherche ignore la casse et les accents** (décision de l'auteur du 2026-10-09). Le premier
passage du lot comparait les textes cherchés dans leurs points de code, accents compris, sans égard
à la casse seule, et chaque opération le disait ou le taisait à sa façon. La règle est désormais une
convention du contrat, écrite une fois au tableau de `docs/api/README.md` : un texte est retenu dès
qu'il contient le texte cherché, l'un et l'autre translittérés comme par `unaccent` de PostgreSQL
avec sa table livrée, puis mis en minuscules (paragraphe suivant) — « etudes », « ETUDES » et
« Études » trouvent « Études ».
Elle vaut pour `search` partout — le paramètre partagé et ceux des comptes, des sous-projets, des
contributeurs, des révisions et du lotissement, qui y renvoient — et pour un filtre qui retient un
texte contenant le texte donné (`code` de `listOrgNodes`, « comparé comme la recherche »). Elle
remplace ce que le journal disait de sa recherche, sans égard à la casse seule (EP-02/L42d). Un tri,
lui, compare toujours les textes dans l'ordre des points de code, accents et casse compris : ranger
n'est pas trouver, et le README le dit sur la même ligne. Le faux back l'applique par une seule
fonction (`mocktext.folded`), que toutes ses recherches emploient — structure, journal, projets,
comptes, contributeurs, lotissement ; `audit_events_search` cherche désormais « Coûts-Réels-2026-05 »
et retient les imports « couts-reels-2026-05… », que seule cette comparaison trouve, et
`test_mocktext.py` éprouve la règle, chaque recherche ayant son cas accentué.

**Une recherche translittère comme `unaccent`, puis met en minuscules** (décision de l'auteur du
2026-10-09, revue 3 du lot). La revue 2 avait remplacé le repli de la casse (`casefold`) par la
décomposition NFD, le retrait des marques combinantes et `lower()`, au motif que
`lower(unaccent(…))` de PostgreSQL laisserait « ß » intact. C'était faux : la table que PostgreSQL
livre avec `unaccent` translittère aussi les ligatures et les lettres barrées — « ß » en « ss »,
« ẞ » en « SS », « œ » en « oe », « æ » en « ae », « ø » en « o », « ł » en « l », « đ » en « d »
—, et la règle de la revue 2 divergeait du service : « main-d'oeuvre » ne trouvait pas
« Main-d'œuvre », une nature de l'univers témoin. Une recherche translittère donc comme `unaccent`
avec sa table livrée, puis met en minuscules : « oeuvre » trouve « Main-d'œuvre », « strasse »
trouve « Straße », « soren » trouve « Søren », et la casse et les accents restent ignorés. EP-03
réalisera la recherche par `lower(unaccent(…))` avec cette table. La table translittère aussi
quelques signes — le tiret « — » s'y lit « - », le guillemet « « » « << », « ¼ » « 1/4 » — ; une
recherche les lit de même.
Le faux back ne dépend pas du fichier du système : la table est versionnée dans
`tools/src/wftools/unaccent.rules`, copie de celle de PostgreSQL 16 avec sa provenance et sa licence
(PostgreSQL, `LICENSES/PostgreSQL.txt`) en tête, et `mocktext.folded` l'applique, la plus longue
source d'abord comme `unaccent`, puis `lower()`. La décomposition NFD est abandonnée : un caractère
que la table ne nomme pas reste lui-même, comme `unaccent` le laisse (« й », « Ǣ »), et elle
différait de la table sur 675 des textes des exemples — tirets, guillemets, « œ ». Le faux back a
été comparé à un PostgreSQL 16 : sa table au `unaccent` livré sur chaque point de code Unicode,
`folded` à `lower(unaccent(…))` sur chaque texte des exemples, sans aucune différence. Aucun exemple engendré ne change, et
aucun ne cherche les natures de coût : `test_mocktext.py` éprouve la règle, la nature
« Main-d'œuvre » du témoin comprise.

**Les rôles d'habilitation se filtrent par nature et par nombre de porteurs** (#560 ;
WF-IHM-0130). `is_predefined`, le nom de la colonne et du champ, plutôt que `predefined` : vrai,
les trois rôles livrés (WF-ADM-0010) ; faux, les rôles composés ensuite (WF-ADM-0090) ; absent, les
deux. `holder_count_min` et `holder_count_max`, plutôt que `holders_min` et `holders_max` : la
colonne se nomme `holder_count` dans `sort_by` et dans `AccessRole`, et la convention nomme la
borne d'après la colonne. Deux entiers positifs ou nuls, inclus ; une borne mal formée est refusée
par `NUMBER_INVALID`, une borne supérieure inférieure à l'inférieure par `VALUE_OUT_OF_RANGE` sur
`/query/holder_count_max`, `params.minimum` la borne inférieure donnée, un entier comme la colonne
(`access_roles_bounds_inverted`, écrit à la main). Le nombre de porteurs compte les comptes
désactivés, ce que le témoin faisait déjà (Alix Moreau, chef de projet) et que la description dit
désormais. Exemples `access_roles_composed` et `access_roles_unheld` — `holder_count_max=0`, les
rôles que personne ne porte, ceux qu'on peut supprimer (WF-ADM-0090).

**Le lotissement se cherche sur ses libellés et se filtre par nature** (`search`, `kinds`, #560 ;
WF-IHM-0130, WF-IHM-0060). L'issue demandait une recherche sur le libellé et le code : **aucun
code**, à l'écart de la demande — WF-PRJ-0020 ne donne à un poste, un lot ou un livrable qu'un
libellé, et en ajouter un modifierait la spécification. Le filtre retenu est celui de la seconde
colonne de l'écran, la nature — poste, lot, livrable (`WorkBreakdownKind`) —, au pluriel comme les
filtres de la colonne de nature d'une liste, la qualité des contributeurs (`kinds` de
`listContributors`) et la nature des types de coût (`kinds` de `listCostTypes`) ; celui de
`listNodes` n'est pas un filtre — il choisit ce que la grille rend, sans toucher aux totaux — et
n'est pas le modèle de celui-ci. WF-IHM-0130 veut chaque colonne filtrée, et la grille
du lotissement n'en a que deux, le libellé et la nature. Écartés : un filtre sur le rattachement à
une tâche (WF-PLA-0130), que `WorkBreakdown` ne porte pas et que la grille ne montre pas ; un filtre
des lots sans livrable, qui n'est la valeur d'aucune colonne. Dans un arbre, un filtre retient les
éléments qui le satisfont, les filtres se combinant, et rend les postes et les lots qui contiennent
un élément retenu, pour que l'arbre reste lisible (WF-IHM-0060), **sans les autres éléments qu'ils
contiennent** : la règle de la recherche dans la grille de planning, qui « ne laisse voir que les
tâches correspondantes et leurs parents » (Vérif de WF-PLA-0080). Exemples engendrés du témoin : `work_breakdown_search` (« Montage » : le poste, sans
son lot) et `work_breakdown_work_packages` (`kinds=work_package` : le lot, sans son livrable, sous
son poste).

*Remplacé en partie par US-0450/L1 : la nature liste lot, poste, livrable, dans l'ordre des niveaux
(`[work_package, order_item, deliverable]`) ; `work_breakdown_work_packages` devient
`work_breakdown_order_items` (`kinds=order_item` : le poste, sans son livrable, sous son lot), et
`work_breakdown_search` cherche « lot », section « Le lotissement en lots, postes et livrables ».*

**Une lecture filtrée n'a pas de compteur** (revue du lot ; WF-IHM-0110). `setWorkBreakdown` et
`setContributors` écrivent le lotissement et la liste des contributeurs entiers : une lecture
filtrée, renvoyée telle quelle avec le compteur du tout, supprimerait sans un mot ce qu'elle omet,
et le 412 ne l'arrêterait pas, le compteur étant à jour. Décision de l'agent de livraison, l'option
(a) de la revue : la lecture a son schéma, `WorkBreakdownReading`, distinct de l'écriture
`WorkBreakdown`, et son compteur est nul dès que `search` ou `kinds` est présent, même si le filtre
retient tout ; celui de `ContributorList` est nul dès que `search`, `kinds` ou `is_active` l'est —
un tri seul n'omet rien, et garde le compteur. L'écriture exige un compteur entier : un renvoi tel
quel est refusé par 422, `VALIDATION_FAILED`, `fields` désignant `/lock_version` par
`VALUE_REQUIRED`. Un écran qui filtre relit la liste entière avant d'écrire. Écartés : garder le
compteur et l'avertir dans la description, la décision du premier passage, qu'un client ne lit pas ;
refuser un filtre sur une liste qui s'écrit, contraire à WF-IHM-0130. `contributors_search`,
`contributors_inactive`, `work_breakdown_search` et `work_breakdown_work_packages` sont sans
compteur ; `contributors`, `contributors_by_name`, `work_breakdown` et `work_breakdown_default` le
gardent, ce que `test_mocklists.py` tient de chaque exemple que le contrat cite. Une écriture,
elle, rend toujours le tout avec son compteur suivant, jamais nul : la réponse 200 de
`setContributors`, dont le schéma `ContributorList` admet désormais un compteur nul, le dit (revue
2 du lot) ; celle de `setWorkBreakdown` rend `WorkBreakdown`, dont le compteur n'est jamais nul.

*Remplacé par EP-14/L42k (relecture 1) : `setWorkBreakdown` rend sa lecture,
`WorkBreakdownReading`, entière, chaque élément retenu, avec son compteur suivant, jamais nul, comme
`setContributors` rend la sienne — section « Le squelette, le rattachement, les chronologies et les
nœuds retenus d'un lotissement filtré (EP-14/L42k) ». Le texte ci-dessus est gardé pour
l'histoire.*

*Remplacé en partie par US-0450/L1 : `work_breakdown_work_packages` devient `work_breakdown_order_items`.*

**Les comptes se filtrent par leur état** (`is_active`, revue du lot ; WF-IHM-0130, WF-ADM-0060).
`include_inactive` ne faisait qu'ajouter les désactivés aux actifs : la colonne de l'état ne se
filtrait pas sur les seuls désactivés. `is_active`, vrai ou faux, prime sur `include_inactive`,
comme celui du référentiel (`IsActive`) ; le paramètre est propre à l'opération, celui du
référentiel parlant de la permission que ses désactivés exigent, que les comptes n'ont pas. Exemple
`users_inactive` : Alix Moreau, seule.

**Les vues du portefeuille déclarent le refus d'une période** (complément de #560, relevé par
EP-02/L42e ; WF-IHM-0130, WF-PTF-0010). `getPortfolioProjects`, `getPortfolioValue`,
`getPortfolioPerformance` et `getPortfolioRisks` prennent `from` et `to` sans déclarer de 422. Elles
déclarent la règle de toute période du contrat : une fin qui précède le début, 422
`VALIDATION_FAILED`, `fields[]` désignant `/query/to` par `VALUE_OUT_OF_RANGE`, `params.minimum` le
début donné, une date de planning comme `from` ; un début ou une fin mal formés, `DATE_INVALID`.
Une réponse partagée, `PortfolioPeriodRefused`, porte la description et l'exemple
`portfolio_period_inverted`, écrit à la main, pour que les quatre vues ne divergent pas ; `to`, qui
n'avait pas de description, dit sa fin incluse et son refus. **Une borne seule se complète par celle
de la période par défaut** (revue du lot), les douze mois qui finissent à la date de calcul (« La
période des statistiques, par défaut », US-0240/L5) : sans `to`, la fin est la date de calcul ;
sans `from`, le début est la date de calcul moins douze mois, puis le lendemain — un 29 février
reculant au 28 février, le 29 février 2028 donne le 1er mars 2027 (revue 2 du lot : « un an plus
tôt » taisait ce cas). La période complétée suit la même règle, et le refus désigne la borne
envoyée, celle que l'utilisateur corrige, `params` nommant la borne complétée : un début postérieur à la date de calcul, `/query/from` par
`VALUE_OUT_OF_RANGE`, `params.maximum` la fin complétée ; une fin antérieure au début par défaut,
`/query/to`, `params.minimum` le début complété. `maximum` rejoint les paramètres de l'enveloppe
(`Problem.params`), le pendant de `minimum`. Exemple `portfolio_open_period_inverted` : un début au
1er septembre 2026, sans fin, le 3 juin 2026. `test_mockuniverse.py` tient l'exemple
à la règle (`test_every_inverted_period_is_refused_by_one_rule`), les deux exemples du portefeuille
compris, et chaque opération qui prend `to` — en propre ou par un paramètre partagé — à la
déclaration de son refus, avec un exemple de période inversée.

*Complété par US-0701/L6 (#1606, G-05) : `getPortfolioCostStructure` et `getPortfolioCostCurve`
prennent aussi `from` et `to` et déclarent `PortfolioPeriodRefused` ; six vues le partagent.*

Engendrés par `wftools.mocklists`, des comptes et des rôles écrits à la main et du lotissement du
témoin, dont il écrit désormais la forme pour `mockdata` : `users_by_access_role`, `users_search`,
`users_inactive`, `access_roles_composed`, `access_roles_unheld`, `work_breakdown_search`,
`work_breakdown_work_packages` ; `test_mocklists.py` éprouve la recherche, les filtres et les bornes
sur des lignes de synthèse, et chaque exemple contre ce qu'il lit. Le client est régénéré ; le front
les adoptera.

*Remplacé en partie par US-0450/L1 : `work_breakdown_work_packages` devient `work_breakdown_order_items`.*

## Les écritures des paramètres de ressources (EP-02/L43b)

Les écritures de l'organisation, des rôles et des calendriers, que l'écran des paramètres de
ressources exerce (#512), reçoivent de même l'exemple de leur succès, écrit aujourd'hui par Camille
Martin : `org_node_created` (le bureau d'études mécanique BE-MECA sous la direction technique, 476),
`org_node_updated` (l'atelier de câblage déplacé sous la direction technique, au deuxième niveau,
version 2), `org_node_deactivated` (l'atelier désactivé, et avec lui le monteur câbleur, sa
réactivation indisponible tant que son nœud l'est — second exemple de `setOrgNodeActivation`, après
la réactivation), `resource_role_created` (le dessinateur électricien, trois personnes, 520 heures par
mois sur la semaine standard, 456), `resource_role_updated` (le technicien de mise en service renommé,
version 2), `resource_role_deactivated` (l'ingénieur électricien désactivé — second exemple, après la
réactivation), `calendar_created` (la semaine de trente-cinq heures, 484), `calendar_updated` (la
semaine de quatre jours renommée, version 2), `calendar_deactivated` (la même désactivée) et
`calendar_default` (la même désignée par défaut, sa désactivation devenue indisponible). Chacun ne vaut
que pour la réponse de son écriture : aucune lecture n'en tient compte. Les refus que ces écritures
opposeraient sans que le contrat les dise sont des « Interface contract issue » relevées par
EP-02/L43b, #575, sous #507.

## Les refus des écritures des paramètres de coûts (EP-02/L42g)

Les six constats de #562, relevés par EP-02/L43a. Le quatrième suit la décision de l'auteur du
2026-10-09 ; les autres, la proposition de l'issue, et ce qu'elle laissait ouvert est une décision
de l'agent de livraison du lot, dite à sa place avec sa raison.

**Le code comptable d'une catégorie est exigé et unique** (point 4, décision de l'auteur du
2026-10-09 ; WF-REF-0040, « porte un code comptable unique »). `CostCategoryWrite.accounting_code`
et `CostCategoryImage.accounting_code` sont requis, une chaîne d'un à vingt caractères, comme le
code, jamais nulle : le contrat suit la spécification, que le schéma contredisait. Le tri par code
comptable ne prévoit plus de catégorie sans code. Les exemples en portaient déjà chacun un,
distinct — les catégories engendrées le leur, `641nnn`, `604nnn` et `681nnn` selon leur nature, et
celle créée aujourd'hui, 606001, qu'aucune autre ne porte ; `make mock-data` ne change rien. La
borne de vingt caractères est celle du code : la spécification n'en fixe pas, et une colonne en a
une.

**La modification du type d'une nature est une commande de la nature** (point 1 ; WF-REF-0030,
WF-IHM-0090). `CostType.available_commands` lit `CostTypeCommand` — `deactivate`, `reactivate` et
`change_kind` —, sur le modèle de `UserCommand` (EP-02/L42d) : celle qui change l'état de la nature,
toujours disponible, et une seconde commande, toujours listée, dont une condition dit la
disponibilité, comme `set_access_roles`. `change_kind` est indisponible dès qu'une catégorie
rattachée à la nature est employée, la condition `cost_type_unused` manquante, nouvelle au catalogue
(`CommandCondition`) ; le code et le libellé se modifient toujours. Une catégorie est employée dès
qu'une ligne d'une révision, marquée ou non, la porte : c'est le motif de l'exigence, qu'un type
modifié après coup rende incohérentes les lignes déjà saisies, et une ligne d'une révision marquée
en est une. Le refus, `updateCostType` envoyé avec un autre `kind` malgré la commande, est le 409 de
toute commande qu'un état rend indisponible : `STATE_FORBIDS_OPERATION`, `params.missing_condition`
à `cost_type_unused`, sans `conflicting_object_id` — aucune action de l'utilisateur ne rend une
catégorie inemployée, et WF-IHM-0090 ne demande de dire quoi faire que lorsque la condition est
atteignable. Écartés : une condition seule, sans commande, qu'aucun objet n'aurait portée ;
`change_kind` dans `ReferenceCommand`, que les autres objets du référentiel partagent et qui ne
porte que la commande de l'état (`maxItems: 1`, EP-02/L42a) ; une commande `update`, dont seul le
type est indisponible. Les natures du témoin — main-d'œuvre, débours, provision — ont chacune une
catégorie que le devis du projet témoin emploie : leur type est figé ; la nature créée aujourd'hui
(FRN, `cost_type_created`), sans catégorie, a le sien libre. Une catégorie employée rattachée à une
nature d'un autre type changerait de même le type de ses lignes : c'est la « Specification
finding » #577, tranchée par l'auteur le 2026-10-09, section suivante.

*Remplacé en partie par EP-14/L42r : `change_kind` manque aussi `cost_type_unrated` quand une
catégorie de la nature porte un taux horaire, et `cost_type_without_role` quand un rôle lui est
rattaché (WF-REF-0030) ; le 409 nomme la première qui manque, et pour la dernière, atteignable, les
rôles en cause (`params.resource_roles`, WF-IHM-0090).*

*Remplacé en partie par EP-14/L42s : une catégorie employée se rattache à une autre nature du même
type, ce qui n'est jamais indisponible ; `cost_type_unused` est atteignable, et le 409 nomme les
catégories en cause (`params.cost_categories`, #766), comme celles qui portent un taux pour
`cost_type_unrated`.*

**Une valeur unique déjà portée est refusée par champ** (points 2 et 3 ; WF-REF-0030,
WF-REF-0040). Le 409 `ALREADY_EXISTS` dit quel champ porte la valeur prise : `fields`, chaque champ
désigné par `ALREADY_EXISTS`, `fields[].params.conflicting_object_id` l'objet qui la porte, actif ou
désactivé — l'utilisateur sait alors quelle catégorie porte déjà le code, et peut la réactiver
plutôt que d'en créer une seconde (WF-IHM-0090). La règle vaut pour tout `ALREADY_EXISTS` du
contrat, au tableau de `docs/api/README.md`, et les 409 d'unicité qui existaient la disent
désormais (revue de L42g) : `createOrgNode` et `updateOrgNode` (`/code`), `createUser` et
`updateUser` (`/email`), `markRevision` (`/version_name`), `createProject` et `updateProject`
(`/code`), `createSubproject` et `updateSubproject` (`/code`), chacun par un 409 décrit en place —
ceux des nœuds et d'`updateProject` renvoyaient à la réponse partagée `Conflict`.
`updateSubproject` ne déclarait aucun 409, alors que le code d'un sous-projet est unique dans le
projet (WF-PRJ-0050) : il le déclare, exemple `subproject_code_taken` (les essais et mise en
service recodés SP-CMD, le code du poste de commande). Écarté : un test qui chercherait de
lui-même toute opération dont le corps porte un champ unique — l'unicité n'est dite qu'en prose,
dans les descriptions, et un tel test la devinerait d'après des mots. `test_mockcostsettings.py`
tient à la place une table explicite (`UNIQUE`) des treize écritures d'une valeur unique et de
leur champ, chacune devant déclarer en place un 409 qui dit `ALREADY_EXISTS`, son pointeur et
`conflicting_object_id` ; une écriture nouvelle d'une valeur unique s'y ajoute.

**Le nom d'un compte externe se refuse par 409** (revue 3 de L42g, décision de l'agent de
livraison). `updateUser` renvoyait à `Conflict` ; son 409 décrit en place ne disait plus que
l'adresse prise, et le refus de modifier le nom, le prénom ou l'adresse d'un compte venu d'un
fournisseur externe (WF-ADM-0050) n'avait plus de statut. C'est un 409
`STATE_FORBIDS_OPERATION`, sans paramètre : aucune condition du catalogue ne dit l'origine d'un
compte, que la lecture porte déjà (`User.origin`), et en ajouter une pour un refus que le
formulaire évite d'avance en ne présentant pas ces champs n'apporterait rien. Exemple
`user_external_update_refused` (le nom de Dominique Bernard, venu de l'annuaire). Une exception, une seule : une clé portée par le chemin et non par le
corps n'a pas de champ à désigner — la catégorie et l'année d'un taux horaire, dont le 409 de
`setHourlyRate` n'a pas de `fields` ; `Problem.fields` et le tableau le disent. La réponse
partagée `Conflict`, qui sert aussi bien un état qui interdit l'opération (`deleteNode`,
`setLineRemaining`, `updateProject`, `redoLastUndo`…), reste générique, ces deux codes donnés en
exemple. Le code d'une nature est unique parmi les natures
(WF-REF-0030), le code et le code comptable d'une catégorie parmi les catégories, désactivées
comprises, comme le code d'un nœud : la spécification ne dit unique que le code comptable, et le
contrat fait du code d'une catégorie ce qu'il fait de celui d'une nature ou d'un nœud, ce que
l'issue tenait pour acquis, pour qu'un code désigne une seule catégorie, à l'écran comme dans la
liste triée par code.
L'unicité vaut à la modification : `updateCostCategory` déclare le 409, `updateCostType` le dit
avec le refus du type.

**Les refus par champ d'une nature et d'une catégorie** (points 2 et 3, convention #293). Les deux
créations et les deux modifications déclarent leur 422 `VALIDATION_FAILED`, `fields` désignant
chaque champ : `/code`, `/label` et, pour une catégorie, `/accounting_code` vides, `VALUE_REQUIRED`,
ou plus longs que le schéma ne l'admet, `VALUE_TOO_LONG` ; `/cost_type_id` absente ou nulle,
`VALUE_REQUIRED` — la catégorie sans nature que le Vérif de WF-REF-0040 refuse (revue de L42g) — ;
d'une nature que le référentiel n'a pas, `UNKNOWN_COST_TYPE`, nouveau au catalogue — il n'y avait pas de code générique
d'une référence inconnue, chaque objet a le sien (`UNKNOWN_COST_CATEGORY`, `UNKNOWN_RESOURCE_ROLE`,
`UNKNOWN_SUBPROJECT`) — ; d'une nature désactivée, `INACTIVE_REFERENCE_OBJECT`, comme un rôle
sous un nœud désactivé (#547) : une nature désactivée n'est plus proposée à la saisie
(WF-REF-0010). À la modification, seulement quand elle change la catégorie de nature : une catégorie
se réactive sous une nature désactivée (EP-02/L42a), et la garder sous elle en la renommant ne
choisit rien. Écarté : la longueur admise en paramètre de `VALUE_TOO_LONG`, que le schéma dit déjà
et que le formulaire contrôle avant l'envoi.

*Remplacé en partie par EP-14/L42s : une catégorie ne se réactive plus sous une nature désactivée, que
sa désactivation désactive avec ses catégories (C-291, `cost_type_active`) ; la règle de la
modification reste.*

**Les refus d'un taux horaire** (point 5 ; WF-REF-0050). Un montant nul ou négatif — `Money`
admet le signe — est refusé par 422 `VALIDATION_FAILED`, `/amount` par `VALUE_OUT_OF_RANGE`,
`fields[].params.minimum` à `0.01`, le plus petit montant positif à deux décimales : le front le
dit, comme le minimum de la rétention des sauvegardes. La spécification ne dit pas qu'un taux est
positif ; un taux nul chiffrerait des heures pour rien, ce qu'aucun écran ne doit laisser saisir par
mégarde, et tous les taux de l'univers témoin l'atteignent. Une catégorie hors main-d'œuvre, qui ne
porte pas de taux, est refusée par 422 `LABOUR_CATEGORY_REQUIRED`, au catalogue sans qu'aucune
réponse le déclare, et dont c'est le sens : sans `fields`, la catégorie étant celle du chemin, qu'un
pointeur ne désigne pas. Le 409 est le second taux d'une année que le Vérif refuse : une première
saisie, sans `lock_version`, pour une année qui porte déjà un taux, `ALREADY_EXISTS`, sans
paramètre — le taux se relit, et se corrige avec sa version.

**Une seule règle pour les paramètres d'un 412** (point 6, #296). `STALE_LOCK_VERSION` porte
`params.expected_lock_version`, la version courante de l'objet que le chemin nomme, et rien
d'autre : c'est ce que disaient les 412 déclarés en place et leurs exemples. Le commentaire
d'`ErrorCode`, qui disait `params.conflicting_object_id`, et la réponse partagée
`PreconditionFailed`, qui disait « l'objet en conflit », le disent désormais ; la règle est au
tableau de `docs/api/README.md`.

**Exemples**, écrits à la main, aux corrélations 1022 à 1029, 1032 et 1037 à 1039 (1019 à 1021 sont celles des
refus de période et de bornes d'EP-02/L42f). `cost_types`, `cost_type_created`,
`cost_type_updated` et `cost_type_deactivated` portent `change_kind`. Refus : `cost_type_code_taken`
(FRN « Fournitures » créée sous le code DEB, celui des débours), `cost_type_creation_refused` (un
code de trente-six caractères, un libellé vide), `cost_type_kind_refused` (les débours passés en
main-d'œuvre), `cost_type_update_refused` (les débours sans libellé),
`cost_category_codes_taken` (le code ACH-002 du matériel électrique et le code comptable 604001 de
la sous-traitance, chacun nommant sa catégorie), `cost_category_creation_refused` (une nature
inconnue, un code comptable vide), `cost_category_without_type_refused` (une catégorie créée sans
nature), `cost_category_accounting_code_taken` (la sous-traitance sous le
code comptable 604002 du matériel électrique), `cost_category_update_refused` (un libellé de deux
cent un caractères), `hourly_rate_already_entered` (une première saisie du taux de 2016 de
l'ingénierie mécanique de niveau 1, qui en porte un), `hourly_rate_amount_refused` (ce taux corrigé
à 0,00) et `hourly_rate_non_labour_refused` (un taux de 2026 pour la sous-traitance). La
désactivation d'une nature n'a pas d'exemple de refus à la création d'une catégorie : aucune nature
de l'univers n'est désactivée, `cost_type_deactivated` ne valant que pour sa réponse.
`cost_types_with_inactive`, cité par `listCostTypes` comme `listOrgNodes` et `listCalendars`
citent le leur, est la lecture des natures avec les désactivées (`include_inactive`), les débours
désactivés tels que `cost_type_deactivated` les répond (revue 3 de la partie front de L42g) :
l'univers témoin n'a aucune nature désactivée, et l'exemple ne vaut que pour cette lecture, celle
que fait le formulaire d'une catégorie pour connaître le type de chaque nature ; `make mock-data` ne
l'écrit pas, et `test_mockcostsettings.py` le tient contre `cost_types` et `cost_type_deactivated`.
`test_mockcostsettings.py` les tient contre l'univers — le type figé des natures dont une ligne
emploie une catégorie, le code pris nommé par l'objet qui le porte, l'unicité des codes comptables,
le minimum que tous les taux atteignent, une grille sans catégorie hors main-d'œuvre —, confronte
chaque refus à ce que dit son résumé — ses champs et leurs motifs dans l'ordre, la nature ou la
catégorie qu'il nomme, la longueur qu'il dit trop grande au `maxLength` du schéma —, tient que tout
`ALREADY_EXISTS` désigne ses champs sauf la clé d'un chemin, et tient la règle des 412, dans les
exemples et dans le texte du contrat.

## La nature d'une catégorie employée (EP-02/L42g, #577)

**Une catégorie employée ne se rattache qu'à une nature du même type, et une catégorie qui porte
des taux ne quitte pas la main-d'œuvre** (décision de l'auteur du 2026-10-09, option (a) de #577 ;
WF-REF-0030, WF-REF-0050). `CostCategoryUpdate` porte `cost_type_id` : sans cette règle, une
catégorie employée passée sous une nature d'un autre type changeait le type de ses lignes, ce que
WF-REF-0030 interdit à la nature, et une catégorie de main-d'œuvre passée ailleurs gardait des taux
que WF-REF-0050 refuse aux autres natures. La phrase que la décision demande à WF-REF-0040 — « Une
catégorie employée ne se rattache qu'à une nature du même type », et une catégorie qui porte des
taux ne quitte pas la main-d'œuvre — reste à écrire dans la spécification : ce lot ne touche pas
`docs/spec`, et le contrat la cite par #577 en attendant.

*Mise à jour par EP-14/L42r : la phrase est dans WF-REF-0040, qui y ajoute la catégorie à
laquelle un rôle de ressource est rattaché (`cost_category_without_role`) ; les descriptions que
L42r touche la citent à côté de #577.*

**La commande dit le rattachement à une nature d'un autre type, et lui seul.**
`CostCategory.available_commands` lit `CostCategoryCommand` — `deactivate`, `reactivate` et
`change_cost_type` —, comme la nature lit `CostTypeCommand` : la commande de l'état, toujours
disponible, puis `change_cost_type`, toujours listée, qui rattache la catégorie à une nature dont le
`kind` diffère du sien. Le rattachement à une autre nature du même type reste permis, employée ou
non, taux ou non : il n'est pas une commande, rien ne le rendant indisponible, comme la modification
du libellé — l'écart de `update` d'EP-02/L42a. Décision de l'agent de livraison, entre les deux
formes que la décision laissait : une commande « changer de nature » que la condition rendrait
indisponible dirait indisponible un changement vers une nature du même type qui ne l'est pas, et
WF-IHM-0090 ne présente indisponible que ce qui l'est ; la commande restreinte au cas refusé le
dit juste, et le front propose les natures du même type sans réserve, les autres selon la
commande. Le nom suit celui que la demande donnait ; sa description le restreint.

**Deux conditions, parce que deux causes se lèvent séparément.** `cost_category_unused` manque
tant que la catégorie est employée — portée par une ligne d'une révision, marquée ou non, comme pour
une nature —, `cost_category_unrated` tant qu'elle porte des taux horaires. L'emploi ne couvre pas
les taux : une catégorie de main-d'œuvre porte ses taux sans qu'aucune ligne l'emploie, ainsi les
cent quarante-huit catégories de la grille que le devis du témoin n'emploie pas. Une catégorie hors
main-d'œuvre ne porte pas de taux (WF-REF-0050) : seule une catégorie de main-d'œuvre peut manquer
la seconde, et tout autre type la sort de la main-d'œuvre. Le refus, `updateCostCategory` envoyé
avec une nature d'un autre type malgré la commande, est le 409 de toute commande qu'un état rend
indisponible : `STATE_FORBIDS_OPERATION`, `params.missing_condition` la première des conditions que
la commande dit manquantes, `cost_category_unused` avant `cost_category_unrated` — un seul paramètre,
comme les autres refus d'une commande ; la commande, relue, les dit toutes. Sans
`conflicting_object_id` : ni l'emploi ni les taux ne se lèvent par une action que le refus pourrait
désigner.

**Exemples.** Les catégories engendrées (`cost_categories`, sa page) portent `change_cost_type`,
calculée de l'emploi réel — les cinq catégories que portent les lignes du cœur du témoin, dont les
lignes engendrées après lui reprennent les catégories (`mockreference.employed`) — et des taux de
la grille : 47 libres, 3 employées (la sous-traitance, le matériel électrique, la provision), 148
qui portent des taux, 2 les deux (l'ingénierie électrique, MO-001, et la mise en service, MO-002).
`cost_category_created` l'a disponible, `cost_category_updated` et `cost_category_deactivated`
indisponible, `cost_category_unused` manquante. Refus : `cost_category_kind_refused` (MO-001,
employée, passée sous les débours : `cost_category_unused`, la première de ses deux conditions) et
`cost_category_rated_kind_refused` (MO-003, qu'aucune ligne n'emploie, passée sous les débours :
`cost_category_unrated`), corrélations 1030 et 1031. `test_mockcostsettings.py` les tient contre
l'emploi et les taux que lisent les exemples, et tient que seules les catégories portent
`change_cost_type`, et seules les natures `change_kind`.

## La dernière nature provision et sa dernière catégorie (EP-02/L42g, #578)

*Remplacée par EP-14/L42p (#579) : la règle est retirée, ses deux conditions et ses exemples avec
elle — section « La catégorie et le sous-projet de la provision d'un risque, la provision pour
risques (EP-14/L42p) ». Le texte qui suit est gardé pour l'histoire.*

**Il reste toujours au moins une nature de type provision active, qui porte au moins une catégorie
active** (décision de l'auteur du 2026-10-09, option (b) de #578 ; WF-REF-0030). L'exigence crée à
l'amorçage une nature provision et sa catégorie, « c'est cette catégorie que portent les lignes de
provision des risques » ; rien n'empêchait de les désactiver, ou de changer le type de la nature,
et la déclaration d'un risque n'aurait plus eu de catégorie où se ranger. Sont refusés : la
désactivation et le changement de type de la dernière nature provision active à porter une
catégorie active ; la désactivation et le rattachement à une nature d'un autre type de la seule
catégorie active des natures provision actives. La phrase que la décision demande à WF-REF-0030
reste à écrire dans la spécification : ce lot ne touche pas `docs/spec`, et le contrat cite #578 en
attendant.

**Deux conditions, portées par les commandes qu'elles rendent indisponibles.**
`cost_type_not_last_provision` manque à `deactivate` et à `change_kind` de la nature ;
`cost_category_not_last_provision` à `deactivate` et à `change_cost_type` de la catégorie. La
désactivation d'une nature ou d'une catégorie n'était jamais indisponible (EP-02/L42a, et les
descriptions de `CostTypeCommand` et `CostCategoryCommand` de L42g) : elle l'est désormais dans ce
seul cas, et `setCostTypeActivation` et `setCostCategoryActivation`, qui n'avaient pas de 409 faute de
cas, en déclarent un. « Dernière » se juge sur l'invariant, pas sur un compte : une nature provision
n'est la dernière que si aucune autre nature provision active ne porte de catégorie active, et une
catégorie que si elle est la seule active de toutes les natures provision actives — deux natures
provision, chacune avec sa catégorie, et aucune n'est la dernière. Le rattachement de la dernière
catégorie à une autre nature provision active la laisse provision et reste permis ; vers une nature
d'un autre type, c'est `change_cost_type`, qui le dit simplement. Les refus sont le 409 de toute
commande indisponible : `STATE_FORBIDS_OPERATION`, `params.missing_condition`, la première des
conditions manquantes quand il y en a plusieurs — `cost_type_unused` avant
`cost_type_not_last_provision`, et `cost_category_unused`, `cost_category_unrated`,
`cost_category_not_last_provision` dans cet ordre —, sans `conflicting_object_id` : la condition se
lève en créant une autre nature provision et sa catégorie, que le refus ne peut pas désigner.
Écarté : une seule condition pour la nature et la catégorie, qui aurait laissé le front deviner
laquelle des deux est la dernière.

**Dans le témoin**, la provision (PRV, 463) est la seule nature provision, et les provisions pour
risques (PRV-001, 404) sa seule catégorie : `cost_types` porte sa désactivation indisponible et la
modification de son type avec ses deux conditions ; `cost_categories`, engendré
(`mockreference.last_provision`), la désactivation de PRV-001 indisponible et son rattachement avec
`cost_category_unused` et `cost_category_not_last_provision`. Exemples :
`cost_type_last_provision_refused` (la désactivation de la provision) et
`cost_category_last_provision_refused` (celle de PRV-001), corrélations 1033 et 1034.
`test_mockcostsettings.py` calcule la dernière nature et la dernière catégorie des natures et des
catégories lues, et tient les commandes et les refus contre elles.

**Pour EP-03.** « Dernière » se juge sur un ensemble d'objets : deux désactivations concurrentes de
deux natures provision, chacune non dernière quand elle est lue, briseraient l'invariant ; le back
verrouille donc l'ensemble des natures et des catégories provision, avant de le lire, sur les
quatre écritures qui peuvent l'entamer — les deux activations et les deux modifications —, et pas
sur la seule route modifiée (`docs/dev/python.md`, défaut n° 2). Laquelle des catégories provision
porte la ligne de provision d'un risque quand il y en a plusieurs reste ouvert : #579.

**Une écriture qui change les commandes d'autres objets le dit** (revue 2 de L42g), comme
`setOrgNodeActivation` et `setDefaultCalendar` : la réponse ne porte que l'objet écrit, et le client
relit les listes. `setCostTypeActivation`, `setCostCategoryActivation`, `updateCostType`,
`updateCostCategory` et `createCostCategory` changent la désactivation et le changement de type des
natures provision, la désactivation et le rattachement des catégories provision (#578) ;
`updateCostCategory` aussi le changement de type de l'ancienne et de la nouvelle nature (#577), et
`setHourlyRate`, par un premier taux, le rattachement de la catégorie à une nature d'un autre type
(`cost_category_unrated`). `test_mockcostsettings.py` exige « relit » de chacune ; le résumé de
`cost_categories` dit la désactivation de PRV-001 indisponible.

## L'authentification déléguée, les comptes et la sauvegarde de la plateforme (EP-03/US-0350/L1)

Les dix modifications du contrat de la conception d'EP-03 (« Modifications du contrat »),
faites par le premier lot avant le code qui les consomme. Elles défont, pour la première, une
décision d'EP-02 (« Session et erreurs ») ; chacune dit l'option écartée.

**1. Le schéma de sécurité est `bearer`.** Voir « Session et erreurs ». La règle
`rule/session-operation-declares-401` de `redocly.yaml` garde son nom — la conception d'EP-03 et
d'EP-02 la citent — et son sens : toute opération gardée déclare le 401, une opération publique
le dit par `security: []`. Le 401 porte désormais le jeton absent, expiré ou invalide, et le
compte désactivé.

**2. La famille `session` disparaît.** Retirées : `listAuthProviders`, `getCurrentSession`,
`openSession`, `startOidcSession`, `completeOidcSession`, `requestPasswordReset`,
`confirmPasswordReset`, `changeMyPassword`, avec `AuthProviderKind`, `AuthProvider`,
`LocalCredentials`, `Session`, `PasswordResetRequest`, `PasswordResetConfirm`, `PasswordChange`,
et leurs exemples (`auth_providers*`). Le fournisseur d'identité authentifie, réinitialise et
change les mots de passe sur ses pages ; Waterfall n'en voit aucun (WF-ADM-0140). `closeSession`
devient `closeMySessions` (`DELETE /me/sessions`, famille `me`) et ferme toutes les sessions du
compte, sur tous ses postes : c'est la lecture de WF-SEC-0020, « à la requête suivante, sur tous
ses postes ». Écarté : ne fermer que la session du navigateur, qui ne tient pas la phrase.
Les opérations de la famille `me` (`getMe`, `updateMyPreferences`, `putMyAvatar`,
`deleteMyAvatar`) vivent dans `paths/me.yaml`, qui remplace `paths/session.yaml`.

**3. `getMe` porte les permissions.** `UserSelf.permissions` est l'union des permissions des
rôles du compte, ce que `Session.permissions` portait ; `expires_at` et `idle_expires_at`
disparaissent, la durée de la session étant celle du fournisseur d'identité. Les exemples de
session deviennent des exemples de `getMe`, un par ancien exemple : `session` → `me`,
`session_english` → `me_english`, `session_without_preferences` → `me_without_preferences`,
`session_dark` → `me_dark`, `session_without_administration` → `me_without_administration`,
`session_grid_settings` → `me_grid_settings`, `session_estimator` → `me_estimator`,
`session_without_roles` → `me_without_roles`, `session_manager` → `me_manager`,
`session_auditor` → `me_auditor` ; les exemples `me*` qui existaient (`me_directory`,
`me_with_avatar` compris) gagnent leurs permissions. Écarté : une opération de plus pour lire
les permissions, un aller-retour de plus à chaque page pour une donnée du même compte.

**4. Codes d'erreur.** `ACCOUNT_DEACTIVATED` (401) entre ; `INVALID_CREDENTIALS`,
`ACCOUNT_LOCKED` et `PASSWORD_RESET_TOKEN_INVALID` sortent, le fournisseur d'identité tenant les
identifiants, le verrouillage et le lien de réinitialisation. Un compte désactivé est un 401 et
non un 403 : toute opération gardée le déclare déjà, et le front distingue le code, ne renvoie
pas à la connexion, qui bouclerait. Par champ entrent `UNKNOWN_ACCESS_ROLE`, `UNKNOWN_ORG_NODE`
et `FIELD_READ_ONLY`, et `createUser`, `updateUser`, `setUserAccessRoles` déclarent leur 422,
`VALIDATION_FAILED` avec `fields`, comme les écritures du référentiel. Le refus du nom, du
prénom ou de l'adresse d'un compte qui ne vient pas de Waterfall, qui était un 409
`STATE_FORBIDS_OPERATION` sans paramètre (EP-02/L42g), devient un 422 par champ,
`FIELD_READ_ONLY` sur le champ en défaut (`user_external_update_refused` change de statut) :
c'est un refus de champ, que le formulaire peut montrer sur le champ. Écarté : garder le 409,
qui ne dit pas quel champ.

**5. Le lien de fixation mène au fournisseur d'identité.** `PasswordSetupLink.url` est une
adresse de la page du fournisseur d'identité qui fixe le mot de passe, non plus `/login/reset`
du front, qui n'existe plus. Le 409 de `createPasswordSetupLink` nomme sa condition par
`params.missing_condition`, deux valeurs de plus de `CommandCondition` : `is_local_account`,
`is_active_account`. Écarté : `params.state`, que #413 dit ambigu, et qui n'a de sens que pour
`ProjectState`.

**6. La lecture des comptes passe par le fournisseur d'identité.** `/directory-syncs` devient
`/identity-syncs` (`startIdentitySync`, `getLatestIdentitySync`) ; `BackgroundTaskRef.kind`
`directory_sync` devient `identity_sync` ; `DirectorySyncResult` devient `IdentitySyncReport`, dont
chaque signalement (`skipped[].code`) est un `ErrorCode` et non une chaîne libre ; le 409 « aucun
annuaire activé » disparaît, une installation sans annuaire lisant simplement zéro compte ;
`PlatformComponent` remplace `directory` par `identity_provider`, et, qui suivent, l'alerte
`directory_sync_failed` devient `identity_sync_failed` et `SystemStatus.last_directory_sync`
`last_identity_sync`. Waterfall ne lit jamais l'annuaire lui-même (WF-ADM-0070, WF-ADM-0180).
Écarté : lire l'annuaire en LDAP depuis Waterfall, un second chemin vers l'annuaire que la
spécification révisée a retiré.

**7. Les tables des comptes et des rôles.** EP-02/L42f avait déjà ajouté les filtres que la
conception d'EP-03 nomme sous d'autres noms : sur `listUsers`, les rôles (`access_role_ids`) et
l'état (`is_active`, avec `include_inactive`, plus riche qu'une liste d'états) ; sur
`listAccessRoles`, la nature (`is_predefined`) et les porteurs (`holder_count_min`,
`holder_count_max`, plus riches qu'un booléen « a des porteurs » : `holder_count_max=0` dit « sans
porteur »). Ils restent, ce lot n'en ajoute pas un second jeu qui ferait deux façons de
filtrer la même colonne. Ce que le lot ajoute : le départage par identifiant, dit dans les
descriptions des deux listes et de leur `sort_by`, qui rend les pages stables ; la règle générale
du README (« un tri à égalité se départage… par l'identifiant ») s'y applique désormais en
terminant par l'identifiant du compte ou du rôle, dans le sens du tri. La recherche de
`listUsers` porte sur le nom, le prénom et l'adresse, et sur « le prénom suivi du nom, tels que la
table les montre » : « ines roux » trouve Inès Roux sans qu'un « nom affiché » soit un champ du
contrat (L42f). `listAccessRoles` rend un tableau nu : le nombre de rôles retenus se lit de sa
longueur, la liste n'étant pas paginée.

**8. La suppression d'un rôle est logique.** `deleteAccessRole` le dit (WF-DAT-0080) : le rôle
n'est plus proposé, sa trace est conservée, et il est un 404 ensuite. Écarté : la suppression
physique, contraire à WF-DAT-0080.

**9. La sauvegarde couvre les deux bases.** `Backup`, `startBackup` et `startRestore` disent que
la sauvegarde est celle des deux bases de la plateforme, Waterfall et le fournisseur d'identité
(WF-ADM-0150), que le journal d'audit n'est pas restauré mais laissé en place, la restauration
s'y inscrivant (WF-ADM-0160 révisée), et que la plateforme est en maintenance pendant la
restauration : 503 `COMPONENT_UNAVAILABLE`. Le refus d'une sauvegarde d'une version plus récente
que l'installation se nomme `BACKUP_FROM_NEWER_VERSION` et est le fait de **la tâche `restore`**, que
la conception d'EP-03 charge de refuser l'archive avant de mettre la plateforme en maintenance :
elle échoue, `BackgroundTaskRef.problem` portant le code, avec `backup_version` et
`installed_version` dans ses `params` (exemple `task_restore_backup_newer_version`), et aucune
session n'est fermée pour rien. Écarté : un 422 synchrone de `startRestore`, qui obligerait l'API à
lire l'archive dans la requête (défaut n° 4 de `docs/dev/python.md`, un traitement lent dans la
requête). `BackgroundTaskRef.kind` possédait déjà `restore` : une tâche suit toute la restauration,
de la mise en maintenance à sa levée, et ne passe à `succeeded` qu'à la levée. Écarté : une tâche
par phase, qui rendrait une restauration « réussie » avant que la plateforme ne réponde. Reste une
question ouverte, **#604** : pendant la maintenance l'API répond 503 et la tâche vit dans la base
recréée, de sorte que la façon de suivre la fin d'une restauration n'est pas tranchée ; le lot de
la restauration (US-0440/L2) la règlera, et le contrat n'y touche pas ici.

**10. Le dépôt par morceaux d'une sauvegarde** (#350). Un dépôt s'ouvre, reçoit ses morceaux et se
termine : `openChunkedUpload` (`POST /chunked-uploads`, `ChunkedUploadOpen` → `ChunkedUpload`),
`uploadChunk` (`PUT /chunked-uploads/{chunked_upload_id}/parts/{part_number}`, octets bruts →
`ChunkedUpload`), `completeChunkedUpload` (`POST /chunked-uploads/{chunked_upload_id}/completion`
→ `FileUpload`, `purpose` à `external_backup`). Le serveur fixe à l'ouverture la taille d'un
morceau (`part_size_bytes`, entre 5 Mio, le plus petit morceau que le stockage objet assemble, et
10 Mio, la borne du corps d'une action serveur du front, celle des imports, « Un dépôt dit son
usage » : la raison d'être des morceaux est de passer sous cette borne). À 5 Mio, une sauvegarde
de 20 Gio, la valeur d'`Installation` du témoin, fait 20 Gio ÷ 5 Mio = 4 096 morceaux, sous la
limite des dépôts en plusieurs parties du stockage objet (10 000), que `ChunkedUpload.part_count`
porte en `maximum`. Le serveur choisit `part_size_bytes` dans ses bornes pour tenir sous 10 000
morceaux ; l'ouverture est refusée par 413 `FILE_TOO_LARGE` au-delà d'`external_backup_max_bytes`
**ou** au-delà de 10 000 morceaux de 10 Mio (10 000 × 10 Mio, environ 97 Gio). Le réglage
`external_backup_max_bytes` n'est pas borné pour autant : le refus est celui de l'ouverture.
Chaque morceau est de la taille exacte (`part_size_bytes`, le reste pour le dernier), sinon
422 `VALIDATION_FAILED`, `/body` par `VALUE_OUT_OF_RANGE` (`params.minimum` et `maximum`
égaux à la taille attendue : aucun code nouveau) ; un morceau redéposé remplace le précédent,
ce qui reprend un envoi interrompu à partir de la dernière réponse.
Les trois opérations exigent `platform_restore`, comme `startRestore` (403). Le 409 de
`completeChunkedUpload` dit dans `params.missing_parts` les numéros manquants (exemple
`chunked_upload_incomplete`). **Pas d'opération de lecture d'un
dépôt** : la conception dit trois temps, ouvrir, recevoir, terminer ; un envoi que le client ne
peut plus suivre — un rechargement de page — recommence par une ouverture, le dépôt précédent
expirant ; une lecture serait une surface de plus pour un cas que l'expiration couvre. L'assemblage est celui du
dépôt en plusieurs parties du stockage objet (WF-ARC-0050), et l'identifiant du `FileUpload` rendu
est celui que `startRestore` désigne. `uploadFile` garde sa forme et ne sert plus que les
imports : `purpose` à `external_backup` y est refusé par `UPLOAD_PURPOSE_MISMATCH`. Écartés
(« Décisions » du fichier d'EP-03) : une action serveur, dont la taille de corps est bornée ; une
adresse signée du stockage objet, où le navigateur parlerait au stockage, hors des flux du
§4.3.2 ; un gestionnaire de route qui relaie l'API, écarté par EP-02 (WF-ARC-0020). Écarté
aussi : une opération d'abandon, l'expiration (24 heures, comme un fichier d'import) suffit.
*Complété par EP-03/US-0440/L2c (#1006)* : le `FileUpload` que rend `completeChunkedUpload` porte
`backup_taken_at`, la date que dit le manifeste, en tête de l'archive, lue à l'achèvement ; une
archive dont la tête n'en dit pas est refusée là (422 `FILE_FORMAT_UNREADABLE`, le dépôt reste
inachevé) : un dépôt sans date serait restaurable sous n'importe quelle date confirmée. C'est la
date que la confirmation de `startRestore` doit nommer, et l'écran ne la connaîtrait sinon qu'en
lisant l'archive dans le navigateur, une seconde lecture du manifeste, fragile, que le service fait
déjà (écarté). Le champ n'existe que pour `external_backup`.

## Les écritures des sauvegardes (EP-02/L43c)

Les écritures que l'écran des sauvegardes exerce (#519) reçoivent l'exemple de leur succès, chacune à
son instant, avant celui de l'univers : `task_backup_queued` (une sauvegarde manuelle mise en file à
14 h 04), `backup_retained` (la sauvegarde de la nuit marquée à conserver), `backup_released` (celle
du 30 janvier qui ne l'est plus) et `task_restore_queued` (une restauration mise en file à 14 h 04 min
30 s). Chacun ne vaut que pour la réponse de son écriture : aucune lecture n'en tient compte.

**Le téléchargement d'une sauvegarde est gardé par la permission de la restauration**
(`platform_restore`, décision de l'auteur du 2026-10-09, #588) : une sauvegarde porte toute la base,
comptes et projets compris, et la copier hors de la plateforme se confie aussi peu que la
restaurer. `downloadBackup` le dit ; l'écran n'offre « Télécharger » qu'à une session qui la porte.
Les refus que ces écritures opposeraient sans que le contrat les dise sont des « Interface contract
issue » relevées par EP-02/L43c, sous #507.

*Remplacé en partie à la reprise de `main` après EP-03 : le téléchargement est sous `backups.read` et
`backups.write` (#705).*

## La création, la modification et le prochain état d'un projet (EP-02/L44a)

La création et la modification d'un projet, que la maquette exerce (#513, #524), reçoivent l'exemple
de leur succès, écrit aujourd'hui par Camille Martin, le 3 juin 2026 à 14 h 05 : `project_created`
(« Rénovation du poste de livraison », 3, sans code — il se chiffrera sans lui, WF-PRJ-0010 —, à
l'état Créé, ses taux à zéro, sans révision, les commandes d'un chef de projet sur un projet créé) et
`project_updated` (le témoin, sa description saisie, version 8 ; la probabilité de gain reste figée
depuis En cours). `getProject` cite en outre `project_created`, le projet lu après sa création, et
`project_completed`, le témoin lu après sa sortie, que l'écran de ses paramètres présente sa
modification indisponible. `getProjectNextState`, qui n'en avait aucun, reçoit quatre exemples : `next_state`
(le témoin, en cours, qu'aucun fait ne mène plus loin : prochain état et déclencheur nuls, aucune
condition), `next_state_pricing` (l'offre en chiffrage, qui porte son code : En cours à la
désignation de sa révision de référence, la seule condition qui lui reste, WF-CYC-0030),
`next_state_created` (le projet créé : Chiffrage à la création de sa première révision, sans
condition) et `next_state_completed` (le témoin terminé, clos : aucun état ne le suit). Le déclencheur, que le contrat ne nomme que par un code libre (`NextState.trigger`),
y prend les deux codes de la figure 8, `first_revision_created` et
`reference_designated_and_code_set`, que le front rend par son catalogue ; leur énumération au
contrat, et ce que l'opération rend d'un projet en cours ou terminal, sont des « Interface contract
issue » relevées par EP-02/L44a, sous #507. Chacun ne vaut que pour la réponse de son opération :
aucune lecture n'en tient compte.

## Les sauvegardes et les réglages : commandes, filtres et refus (EP-14/L42h)

Les cinq constats de #588, relevés par EP-02/L43c, et le huitième point de #575, les réglages,
rangés dans #507 et regroupés au cadrage d'EP-14 par l'écran qui les consomme — la grille des
sauvegardes de L43c, le formulaire de la planification de L43d, ceux des réglages de L43e. La
permission du téléchargement est la décision de l'auteur du 2026-10-09 ; le reste est de l'agent
de livraison du lot, chaque fois avec sa raison, et les noms que le cadrage et les issues
proposaient sont arrêtés ici.

**Chaque sauvegarde porte ses commandes** (`Backup.available_commands`, `BackupCommand` ; #588,
WF-IHM-0090), sur le modèle de `UserCommand` : au plus trois, dans l'ordre de l'énumération —
celle des deux qui change son marquage, `retain` ou `release` (`retainBackup`, WF-ADM-0170), comme
un objet du référentiel ne porte que celle qui change son état (EP-02/L42a) ; `download`
(`downloadBackup`, WF-ADM-0150) ; `restore` (`startRestore`, WF-ADM-0160). Aucune ne supprime :
la rotation seule le fait. Le serveur ne liste que ce que l'appelant a la permission d'exercer —
le marquage sous `backups.write`, le téléchargement et la restauration sous `platform_restore`
(décision de l'auteur, EP-02/L43c) — et la liste est vide pour qui n'a que `backups.read` ; le
front cesse de déduire les colonnes de commandes des permissions de la session. Trois conditions
s'ajoutent au catalogue (`CommandCondition`), nommées comme ce qui doit tenir, à la manière de
`no_background_task_running` et de `calendar_not_default`, et non comme l'état qui l'empêche :
`backup_verified`, `no_backup_running`, `no_restore_running`. Écartés : `backup_running`,
`restore_running` et `verification_failed`, les noms du cadrage, qui auraient fait lire « condition
manquante : sauvegarde en cours » ; déduire les disponibilités de l'état de la sauvegarde dans le
front, que la conception d'EP-02 interdit. Ce que chaque condition retient, et pourquoi :

- `backup_verified` manque au téléchargement et à la restauration d'une sauvegarde dont la
  vérification n'a pas réussi, en attente ou échouée : « la vérification est ce qui distingue une
  sauvegarde d'un fichier qu'on espère restaurable » (motif de WF-ADM-0150), et le Vérif ne la fait
  télécharger qu'avec « une vérification réussie » ; la copie planifiée attend de même la
  vérification (`BackupExternalCopy`). Le marquage reste disponible : conserver une sauvegarde en
  attente de vérification ne fait rien perdre. Écarté : le téléchargement d'une sauvegarde non
  vérifiée, qui ferait sortir de la plateforme un fichier qu'on ne sait pas restaurable ;
- `no_backup_running` manque, pendant qu'une sauvegarde s'exécute — de sa mise en file à la
  production du fichier : la vérification qui suit n'empêche rien, et une sauvegarde en attente de
  vérification (`backup_pending`) ne retient ni une restauration ni une autre sauvegarde, comme
  `backup_pending` en porte le marquage disponible —, à la restauration, qui lirait une base en
  cours de remplacement et ne serait d'aucun état cohérent, et au déclenchement d'une seconde
  sauvegarde, qui lirait la même base pour rien ;
- `no_restore_running` manque, pendant qu'une restauration s'exécute — de sa mise en file à la
  déconnexion des utilisateurs (WF-ADM-0160) —, à la restauration, au déclenchement d'une
  sauvegarde et au marquage, qui s'écrirait dans la base que la restauration remplace. Le
  téléchargement lit un fichier qu'aucune des deux ne touche : il reste disponible pendant l'une et
  l'autre, et n'est indisponible que ce qui l'est (WF-IHM-0090). Écarté : rendre toute commande
  indisponible pendant une restauration, plus simple, et faux pour le téléchargement.

**Les 409 des sauvegardes sont ceux de toute commande qu'un état rend indisponible** (#588, points
4 et 5) : `STATE_FORBIDS_OPERATION`, `params.missing_condition` nommant la condition, comme les
activations du référentiel (EP-02/L42a) et le type d'une nature (EP-02/L42g). `startBackup` le
déclare pour `no_backup_running` et `no_restore_running` ; `retainBackup` pour
`no_restore_running` ; `downloadBackup` pour `backup_verified` ; `startRestore`, dont le 409
renvoyait à la réponse partagée `Conflict`, le décrit en place pour les trois. Écartés :
`BACKUP_IN_PROGRESS` et `RESTORE_IN_PROGRESS`, les codes que #588 proposait — deux codes pour un
refus que la condition nomme déjà, ce pour quoi `DEFAULT_CALENDAR_REQUIRED` a été retiré (EP-02/L42a).
`startRestore` dit aussi ce qui est refusé pendant qu'une restauration court : en déclencher une
autre (`restore_during_restore_refused`), une sauvegarde, un marquage ; le téléchargement d'une
sauvegarde vérifiée reste possible. Écarté : une disponibilité dite d'avance pour « Sauvegarder
maintenant » — `startBackup` n'est porté par aucune liste, aucun objet ne le liste parmi ses
commandes ; le front le garde par la permission `backups.write`, et le 409 nommé suffit à dire
pourquoi une sauvegarde est refusée. Une liste de commandes de la plateforme viendra quand un
écran en aura besoin.

**Une date confirmée qui n'est pas celle de la sauvegarde est refusée par champ** (#588, point 4 ;
WF-ADM-0160) : 422 `VALIDATION_FAILED`, `fields` désignant `/acknowledged_backup_taken_at` par
`BACKUP_DATE_MISMATCH`, nouveau au catalogue comme `UPLOAD_PURPOSE_MISMATCH`, le refus voisin de
la même opération : aucun motif existant ne dit « pas celle de l'objet désigné ». Les deux dates
se comparent comme des instants, quelle que soit l'écriture du fuseau. Sans paramètre : la
confirmation énonce la date que la liste donne, et une date de sauvegarde ne change jamais — le
refus ne survient que si la liste lue n'est plus celle de la sauvegarde désignée, et l'écran
relit. Écarté : nommer la date de la sauvegarde dans `fields[].params`, que la liste porte déjà.

*Remplacé à la reprise de `main` après EP-03 : une date confirmée qui n'est pas celle de la
sauvegarde est refusée par 400 `CONFIRMATION_REQUIRED` (EP-03/US-0440/L2), `BACKUP_DATE_MISMATCH`
retiré, et le téléchargement est sous `backups.read` et `backups.write` (#705).*

**Le téléchargement vient nommé et mesuré** (#588, point 2 ; WF-ADM-0150). `downloadBackup`
déclare deux en-têtes exigés, comme le résultat d'une tâche (`getBackgroundTaskResult`,
EP-02/L15) : `Content-Disposition`, `attachment` et le nom que le serveur donne au fichier —
`waterfall-backup-`, l'instant de la sauvegarde en temps universel sans séparateur, et l'extension
de son archive, que l'exploitation fixe (§3.4.2.4 : la façon dont une sauvegarde est réalisée
relève de l'architecture technique ; l'exemple dit `.tar`, une archive des deux bases) ; et
`Content-Length`, égal à `size_bytes`, le corps transmis tel qu'il est conservé. Seul le nom a un
exemple : une valeur d'exemple de `Content-Length` serait rejouée par le faux back — 1 313 656 012
octets annoncés pour un corps de quelques octets —, et la route du front qui relaie le
téléchargement recopie l'en-tête ; le contrat exige l'en-tête du vrai back, et la route relaie sans
lui, le nom seul étant exigé pour relayer. Le nom est en ASCII : `filename` suffit, et `filename*`
(RFC 8187), que #588 proposait, n'a rien à redire — écarté. La route du front qui relaie le
téléchargement lit déjà l'un et l'autre, et n'a plus de nom à inventer. La permission est celle de la restauration, `platform_restore`, décidée par
l'auteur le 2026-10-09 et dite depuis EP-02/L43c.

**Les sauvegardes se filtrent et se trient sur chaque colonne** (#588, point 1 ; WF-IHM-0130,
WF-IHM-0060), selon les conventions du contrat : la date par une période d'instants, `from` compris
et `to` exclu, comme le journal et l'accueil (EP-02/L42e), refusée par la règle de toute période
(`backups_period_inverted`) ; l'origine et la vérification par des listes au pluriel, `origins` et
`verifications`, `explode: false` ; le marquage par `is_retained`, le nom de la colonne ; la taille,
colonne de nombres, par ses deux bornes incluses, `size_bytes_min` et `size_bytes_max` (#545,
`backups_bounds_inverted`) — que #588 ne demandait pas, et que la convention impose à toute grille
qui a une colonne de nombres. `sort_by` prend les cinq colonnes, `taken_at` par défaut,
décroissante, les plus récentes d'abord, croissante pour les autres, comme la date du journal ; la
vérification et l'origine se trient dans l'ordre de leur énumération, l'API ne rendant pas leur
libellé ; le marquage range les sauvegardes conservées d'abord dans l'ordre croissant, comme
l'état des comptes range les actifs ; une égalité se départage par l'ordre sans tri, puis
l'identifiant. Les deux énumérations prennent un nom, `BackupVerification` et `BackupOrigin`,
pour que les paramètres de liste les citent sans les recopier ; le front renomme leurs clés
(`enums.BackupVerification`, `enums.BackupOrigin`). `origin` devient exigé : une colonne qui se
filtre et se trie ne peut manquer, et chaque exemple le portait.

**La planification reçoit l'exemple de son succès** (`backup_schedule_set`, WF-ADM-0170) : celle
du témoin enregistrée aujourd'hui par Camille Martin, quatorze sauvegardes conservées, la copie
vers Lyon gardée, version 3 ; `test_mockuniverse.py` tient que ses trente copies restent au moins
autant que la rétention (WF-EXP-0050). Il ne vaut que pour la réponse de l'écriture.

**Chaque champ des paramètres communs relève de la permission de sa fonction** (#575, point 8 ;
WF-ADM-0100). `updateReferenceSettings` le dit : la matrice (`risk_matrix`) sous
`risk_settings.write`, les seuils et le délai (`index_thresholds`, `max_weeks_between_reviews`) sous
`indicator_settings.write`. Une requête ne porte que ce qu'elle écrit, avec le compteur lu — commun
à tous les paramètres, qui sont un seul objet —, et un champ absent reste tel qu'il est, ce que le
schéma d'écriture permettait déjà sans le dire (`ReferenceSettingsWrite`, tout facultatif sauf
`lock_version`) : chaque écran de L43e envoie son seul sous-objet. Un champ dont la session ne
porte pas la permission est refusé par 403 `PERMISSION_MISSING`, `params.missing_permission` la
nommant, rien n'étant écrit — même si la requête porte un autre champ qu'elle pourrait écrire :
une écriture s'applique entière ou pas du tout. Écartés : deux opérations, une par fonction, qui
feraient deux chemins pour un objet et deux compteurs à tenir ; écrire ce que la session peut et
taire le reste, qui ferait croire à un succès entier. `default_language` ne relève d'aucune des
deux fonctions : il quitte le schéma d'écriture (`ReferenceSettingsWrite`) et reste en lecture
(`ReferenceSettings`) — un champ que l'on peut envoyer relève de la permission de sa fonction, et
la langue n'en a aucune ici ; aucun écran du référentiel ne l'écrit, et la langue par défaut de
l'installation (WF-INTF-0160) s'écrira là où EP-03 le décidera, dont c'est le domaine. Écarté : lui
inventer une permission.

**Les refus par champ des réglages** (#575, point 8 ; WF-REF-0160, WF-REF-0170). Deux motifs
nouveaux au catalogue, les noms que #575 proposait, arrêtés : `BOUNDS_NOT_ORDERED` sur le rang de
la borne de la matrice qui n'est pas strictement supérieure à la précédente
(`/risk_matrix/severity_bounds/1` : la deuxième borne de gravité, 1 %, sous la première, 5 %), et
`THRESHOLD_NOT_BELOW_WATCH` sur le seuil d'alerte qui n'est pas strictement inférieur au seuil de
vigilance de son indice (`/index_thresholds/cost_alert`, `/index_thresholds/schedule_alert`),
chacun à son champ, les deux indices dans un même refus quand les deux fautent. Écarté :
`VALUE_OUT_OF_RANGE` avec `params.minimum` ou `params.maximum`, dont la borne est incluse quand
l'ordre est strict — « minimum : 0,1 » aurait admis 0,1. Les seuils prennent un schéma,
`IndexThreshold`, un décimal strictement entre 0 et 1 : WF-REF-0170 les dit « inférieurs à 1 », et
un seuil nul ou égal à 1 ne laisserait aucune zone ; les bornes de la matrice restent des
`Percent`, une gravité pouvant dépasser le budget. Le 412 est celui de toute écriture
(`STALE_LOCK_VERSION`, `params.expected_lock_version`, EP-02/L42g), décrit en place : les deux
écrans partagent le compteur, et l'un périme la lecture de l'autre. Exemples, écrits à la main aux
corrélations 1049 à 1052 : `reference_settings_thresholds_updated` (les seuils à 0,95 et 0,85 et
six semaines entre deux revues, version 2), `reference_settings_matrix_updated` (les probabilités à
10, 25 et 50 %, les gravités à 2, 5 et 10 %, version 2), `reference_settings_bounds_refused`,
`reference_settings_thresholds_refused`, `reference_settings_stale` (les seuils envoyés en version
1 quand la matrice est en version 2) et `reference_settings_permission_missing` (la matrice
envoyée par une session qui n'a qu'`indicator_settings.write`). Chaque succès ne vaut que pour la
réponse de son écriture : aucune lecture n'en tient compte.

**Exemples des sauvegardes.** Écrits à la main : `backups`, `backup_retained` et `backup_released`
portent leurs commandes, celles de la session de Camille Martin, qui a les deux permissions, toutes
disponibles, rien ne s'exécutant aujourd'hui ; `backup`, la sauvegarde de la nuit lue seule ;
`backup_pending`, la sauvegarde manuelle mise en file à 14 h 04 (`task_backup_queued`), prise à
14 h 04 min 50 s et lue avant que sa vérification n'aboutisse — son marquage disponible, son
téléchargement et sa restauration non, `backup_verified` manquante ; l'identifiant 908 de la
famille des sauvegardes —, la suite d'une écriture faite aujourd'hui ; aux corrélations 1040 à
1048, `backups_period_inverted`, `backups_bounds_inverted`, `backup_start_refused` et
`backup_start_during_restore_refused`, `backup_retain_refused` (la sauvegarde conservée du
30 janvier, dont la commande est `release`, que l'on marque à ne plus conserver pendant la
restauration de 14 h 04 min 30 s, `task_restore_queued` : elle reste marquée),
`backup_download_refused`, `restore_during_backup_refused`, `restore_unverified_refused`,
`restore_date_mismatch` (la sauvegarde du 3 juin confirmée avec la date de celle du 2) ; à la
corrélation 1053, `restore_during_restore_refused` (une seconde restauration pendant la
première). Engendrés par `wftools.mocklists`
de `backups`, comme les listes de l'administration (EP-02/L42f) : `backups_reader` (aucune
commande), `backups_during_backup` (la restauration indisponible sur chacune, `no_backup_running`),
`backups_manual`, `backups_retained`, `backups_period` (juin 2026 à Paris), `backups_by_size` ;
`test_mocklists.py` éprouve les filtres, les tris et les commandes sur des lignes de synthèse, et
chaque exemple contre la liste écrite à la main ; `test_mockuniverse.py` tient `listBackups` à la
règle des périodes. Le client est régénéré ; la grille de L43c adoptera les commandes, le tri et
les filtres en L43f, les formulaires sont à L43d et L43e.

## Le projet, les sous-projets et les contributeurs : commandes, bornes et refus (EP-14/L42i)

Les écarts au contrat relevés par EP-02/L44a (#590) et EP-02/L44b (#592), rangés dans #507 et
regroupés au cadrage d'EP-14 par les écrans qui les consomment — les paramètres et le cycle de vie
du projet, ses sous-projets et ses contributeurs —, et le point de #625 qui touche un exemple du
sous-projet. Les décisions sont de l'agent de réalisation du lot (#612), chaque fois avec sa
raison ; les noms que le cadrage et les issues proposaient sont arrêtés ici. Le lot ne touche au
front que pour compiler sur le client régénéré ; l'adoption par les écrans de L44a et L44b suit.

**Le déclencheur du prochain état est énuméré** (`LifecycleTrigger`, #590 ; WF-CYC-0020,
WF-CYC-0050) : `first_revision_created` et `reference_designated_and_code_set`, les deux faits de la
figure 8, que les exemples de L44a nommaient déjà et que le front rendait par son catalogue en
tenant pour « non reconnu » tout autre code. `NextState.trigger` les cite, nul avec `next_state`.
D'un projet en cours ou dans un état terminal, `getProjectNextState` répond 200, le prochain état
et le déclencheur nuls, aucune condition — ce que `next_state` et `next_state_completed` montraient
sans que l'opération le dise. Écartés : un 404 ou un 409, qui feraient d'une lecture un refus et
obligeraient l'écran du cycle de vie à distinguer deux chemins pour dire « aucun fait ne mène plus
loin » ; un troisième déclencheur pour les sorties du cycle de vie, qui sont des commandes du projet
(WF-CYC-0060), pas un prochain état. Le catalogue reçoit `enums.LifecycleTrigger` ; l'écran de L44a,
qui garde encore sa liste et son « déclencheur non reconnu », l'adoptera.

**La probabilité de gain est dite figée d'avance** (`ProjectCommand.update_win_probability`,
`CommandCondition.project_before_in_progress` ; #590, WF-PRJ-0090, WF-IHM-0090). Une commande du
projet, toujours listée juste après `update`, dont elle est une part : disponible aux états Créé et
Chiffrage, `project_before_in_progress` manquante dès En cours — `project_not_terminal` avec elle sur
un projet clos, comme `update` la nomme (`project_completed`) ; **réécrit par US-0702/L3** (#1657) :
un projet clos ne liste plus la commande, et seul le 409 de l'appel direct nomme
`project_not_terminal`. La règle d'EP-02 : un objet dit ses
commandes d'avance, et l'écran ne déduit rien de son état. Écartés : un booléen du projet
(`is_win_probability_frozen`), qui doublerait une commande sans nommer sa condition ; garder le
champ dans `update` seule, qui ne peut dire qu'une part de ses champs est figée ; la condition
nommée par l'effet (`win_probability_editable`) plutôt que par le fait qui doit tenir, à la manière
de `project_not_terminal` ; `project_in_pricing`, qui existe mais exclut Créé. La valeur envoyée
malgré la commande est refusée comme toute commande qu'un état rend indisponible (EP-02/L42a) :
409 `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `project_before_in_progress`
(`project_win_probability_frozen`) — l'enveloppe du `kind` figé d'une nature de coût, que
`updateCostType` refuse par `cost_type_unused` (EP-02/L42g) : un champ qu'une commande fige se refuse
par la condition de cette commande, et le front n'a qu'une lecture pour les deux.
`WIN_PROBABILITY_FROZEN`, qui figurait au catalogue sans qu'aucune réponse le déclare, en est retiré,
comme `HAS_ACTUAL_COSTS`. Écartés, à la relecture : un 422 `VALIDATION_FAILED`, `fields` désignant
`/win_probability` par `WIN_PROBABILITY_FROZEN`, que la première rédaction du lot avait retenu — il
donnait au même fait deux enveloppes selon l'écran, et un motif par champ sans paramètre là où la
condition existe déjà ; un 409 `WIN_PROBABILITY_FROZEN` sans paramètre, la lecture qu'autorisait
l'ancien catalogue. Le formulaire, qui dit au champ les refus par champ, dit celui-ci en alerte, par
`problemMessage`, comme le `kind` figé. Absente de la requête, la valeur ne change pas : c'est un
`PATCH`. `test_mockproject.py` tient la règle en travers des exemples : tout refus de ce lot qui
nomme une `missing_condition` est un 409 `STATE_FORBIDS_OPERATION`.

**Les deux taux sont bornés** (#590 ; WF-PRJ-0040, WF-PRJ-0090) : `inflation_rate` et
`win_probability` sont des rapports, de `0` à `1` inclus — `0.03` pour 3 %, les écrans saisissant en
pourcentages et envoyant en rapports (L44a) —, hors desquels `updateProject` refuse la valeur par
champ : 422 `VALIDATION_FAILED`, `VALUE_OUT_OF_RANGE`, `fields[].params.minimum` ou `maximum` la
seule borne franchie, comme la fin d'une période antérieure à son début ne porte que `minimum`.
Écartés : contraindre `Percent` lui-même, qu'une borne de gravité de la matrice des risques dépasse
(EP-14/L42h) ; des `minimum` et `maximum` du schéma, qu'une chaîne décimale ne porte pas. L'exemple
(`project_rates_out_of_range`) envoie 40 — un pourcentage pour un rapport, l'erreur que l'écran
préviendra — et -0,01.

**Le porteur d'un code pris est nommé par son libellé** (`fields[].params.conflicting_object_label`,
le compagnon de `conflicting_object_id`, le nom que #590 proposait ; #592 ; WF-PRJ-0010,
WF-PRJ-0050), par `createProject` et `updateProject` pour le code d'un projet, `createSubproject` et
`updateSubproject` pour celui d'un sous-projet, et la convention du README le dit. EP-02/L42g nomme
le porteur par le seul identifiant dans le référentiel, dont les formulaires ont la liste ; ce lot
ajoute le libellé là où le formulaire ne connaît pas la liste qui porte le code — l'accueil est
paginé et filtré par état, la liste des sous-projets peut être lue filtrée —, et où un chef de
projet peut ne pas avoir la permission de lire le projet qui le porte, que relire par son
identifiant lui répondrait 404 (WF-ADM-0110). Écartés : un code propre (`PROJECT_CODE_TAKEN`), le
motif étant celui de toute valeur unique ; rendre l'objet entier dans `params`, dont l'écran ne
dirait que le libellé ; `label` tout court, que la première rédaction du lot avait retenu et qui ne
disait pas de quoi il est le libellé, quand `tasks[].label` nomme déjà une tâche dans `params`.
`project_code_taken` (PRJ-001, le code du témoin, donné à la rénovation du poste de livraison, à sa
création comme à sa modification) et `subproject_code_taken` le montrent.

**Les refus de `createProject` sont exemplifiés** (#590) : `project_reference_incomplete`, 409
`REFERENCE_INCOMPLETE`, `params.missing_prerequisites` nommant chaque prérequis par une valeur de
`ReferenceReadiness.missing` — une variante contrefactuelle, le référentiel du témoin étant
complet —, et `project_creation_refused`, 422, le libellé absent (`VALUE_REQUIRED`, WF-PRJ-0080) et
un code de cinquante-et-un caractères (`VALUE_TOO_LONG`). Les 422 de `createProject`, `updateProject`,
`createSubproject` et `updateSubproject`, qui renvoyaient à la réponse partagée, sont décrits en place.

**Chaque sous-projet porte ses commandes** (`Subproject.available_commands`, `SubprojectCommand`,
`SubprojectCommandAvailability` ; #592, WF-IHM-0090), sur le modèle de `UserCommand` et de
`BackupCommand` : au plus deux, dans l'ordre de l'énumération, `update` (`updateSubproject`) et
`delete` (`deleteSubproject`). Elles suivent la commande `update` du projet : la liste est vide pour
qui ne la porte pas, et toutes deux nomment `project_not_terminal` sur un projet clos (WF-CYC-0100 ;
réécrit par US-0702/L3, #1657 : un projet clos n'en liste aucune) ;
la création d'un sous-projet, qu'aucun sous-projet ne peut lister, suit `update` aussi. Une
condition s'ajoute au catalogue, nommée comme ce qui doit tenir : `subproject_without_actual_costs`
manque à la suppression d'un sous-projet auquel des coûts réels sont imputés (WF-PRJ-0050) — les
deux du témoin, le Poste de commande par la facture des écrans, les essais et la mise en service par
celles des tâches tirées depuis EP-14/L45a. Aucun exemple ne montre donc la suppression disponible,
le témoin chargeant tous ses sous-projets : `test_mockproject.py` fixe sur une variante construite
dans le test (`has_actual_costs` faux, `delete` disponible) la règle qu'il applique aux exemples,
plutôt que par un exemple de plus. Le lot en avait fait la seule, et retiré la `subproject_not_cited`
que le cadrage d'EP-14 et #592 portaient, en suivant le Vérif de WF-DAT-0080, qui dit que la
suppression d'un sous-projet référencé par une révision marquée *le marque supprimé* ; l'auteur a
tranché le contraire le 2026-10-10 (#634) : un sous-projet qu'une révision marquée cite ne se
supprime pas, et la condition revient, première des deux (EP-14/L42l, plus bas). La modification
reste disponible, coûts imputés ou non : rien ne l'interdit. Écartés : déduire la suppression de
`has_actual_costs` dans le front, ce que L44b faisait faute de mieux ; un booléen de plus pour la
permission, que la commande dit ; `HAS_ACTUAL_COSTS`, retiré du catalogue des codes : aucune réponse
ne le déclarait, et le refus d'une commande qu'un état rend indisponible est
`STATE_FORBIDS_OPERATION` (EP-02/L42a). Le 409 de `deleteSubproject` le dit,
`params.missing_condition` nommant la première condition qui manque
(`subproject_delete_refused`) — `project_not_terminal` en dernier sur un projet clos (EP-14/L42l,
plus bas ; réécrit par US-0702/L3, #1657 : le projet clos ne liste plus la commande, et seul ce 409
la nomme).

**`update` couvre le paramétrage du projet, sous-projets compris** (#592, point 3 ; FBS-4.2.3,
WF-PRJ-0050, WF-PRJ-0060) : la description de `ProjectCommand` le dit — les attributs
(WF-PRJ-0080), le lotissement (WF-PRJ-0020) et les sous-projets (WF-PRJ-0050), que chaque sous-projet
détaille. Écarté : `manage_subprojects`, une commande du projet de plus, qui aurait la permission, les
porteurs et la condition d'`update` — les chefs de projet, `project_not_terminal`, qu'un projet clos
ne liste plus depuis US-0702/L3 — et doublerait ce
que chaque sous-projet dit déjà : une permission, une commande. `manage_contributors` reste à part,
parce que la liste des contributeurs a son propre compteur et sa propre règle (WF-PRJ-0060).

**Le sous-projet créé porte déjà des coûts** (`subproject_created`, #625 ; WF-CRE-0020) : la facture
FA-2026-0295, « Réception du client sur site », importée sous le code SP-REC et imputée jusque-là au
seul projet — exclue du périmètre suivi, elle n'en reste pas moins sa ligne —, lui est imputée dès
sa création, `has_actual_costs` vrai et `delete` indisponible aussitôt. `test_mockuniverse.py`
confronte aux lignes imputées chaque exemple qui lit ou écrit un sous-projet (`CHARGED`) : les
listes lues, celle que répond un renommage, et le sous-projet créé — un seul tuple depuis la reprise
d'EP-14/L45a, qui y ajoutait les siens.

**Un compte inconnu ou désactivé est refusé à sa ligne** (`setContributors`, #592 ; WF-PRJ-0060,
WF-ADM-0060) : 422 `VALIDATION_FAILED`, `fields` désignant `/contributors/<n>/user_id` par
`UNKNOWN_USER`, pour un compte que l'installation n'a pas, ou `USER_INACTIVE`, pour un compte
désactivé inscrit ou changé de qualité, sans paramètre : la ligne dit le compte, et le formulaire le
nomme. Deux motifs nouveaux au catalogue, à côté d'`UNKNOWN_SUBPROJECT` et `UNKNOWN_RESOURCE_ROLE`,
nommés comme `User.is_active` et `Contributor.is_active`. Écartés : `INACTIVE_REFERENCE_OBJECT`, un
compte n'étant pas un objet du référentiel ; `UNKNOWN_OBJECT`, trop large pour un formulaire qui le
dit à un champ. Un contributeur désactivé depuis son inscription reste dans la liste, tel qu'il a
été lu, et la liste renvoyée avec lui n'est pas refusée — WF-ADM-0060 veut qu'il y reste et y soit
signalé ; écarté : refuser toute liste qui le garde, qui obligerait à retirer Alix Moreau pour
changer la qualité de Lucas Petit. `LAST_PROJECT_MANAGER` reste un code propre, 409 sans paramètre,
que `contributors_without_manager_refused` montre : la liste envoyée décide, qu'aucune commande ne
dit d'avance, comme `LAST_ADMINISTRATOR` (EP-02/L42d) ; `setContributors` nomme aussi son 409 sur un
projet clos, `project_not_terminal`.

**Une proposition nomme son nœud et ses rôles, et dit que le compte est actif**
(`ContributorSuggestion.org_node_label`, `resource_role_labels`, `is_active` ; #592, WF-PRJ-0070,
WF-ADM-0060) : les libellés dans l'ordre des identifiants, pour que l'écran dise pourquoi un compte
est proposé sans relire le référentiel (WF-ARC-0020) ; `is_active` toujours vrai — un compte
désactivé n'est plus proposé, et l'inscrire serait refusé —, rendu comme `Contributor.is_active`
pour que la proposition confirmée prenne place dans la liste telle quelle. Écartés : le taire, ce
qui ferait supposer à l'écran ce que le serveur sait ; emboîter un `Contributor`, dont la qualité
n'est pas celle d'une proposition. `listContributorSuggestions` dit d'où viennent les propositions :
les comptes actifs rattachés aux nœuds d'organisation des rôles de ressources qu'emploient les
lignes de devis du projet, que la liste ne compte pas encore ; l'ancienne description disait « le
planning » là où WF-PRJ-0070 nomme les lignes de devis. Quelle révision porte ces lignes — celles de
la révision en cours, ou de la dernière révision marquée quand il n'en a pas — est une décision de ce
lot, que ni WF-PRJ-0070 ni la conception d'EP-14 ne posent : la révision en cours est celle qu'un
chef de projet chiffre quand il compose sa liste, et un projet sans révision en cours n'a que ses
révisions marquées ; EP-04, qui écrit le back des projets, la confirme ou la change.

**Aucune opération ne liste les candidats inscriptibles** (#592, point 5) — écarté. L'écran de L44b
n'inscrit que les propositions, et WF-PRJ-0070 ne décrit que cela ; une opération qui ouvrirait à
tout chef de projet le répertoire des comptes de l'installation contournerait la permission
`users.read` (WF-ADM-0100), et celui qui la porte a `listUsers`. EP-04, qui écrit le back des
projets, dira s'il en faut une.

**Exemples.** Écrits à la main, aux corrélations 1060 à 1067 : `project_code_taken`,
`project_reference_incomplete`, `project_creation_refused`, `project_win_probability_frozen` (la
probabilité du témoin, en cours, ramenée à 0,8), `project_rates_out_of_range` (l'offre, en
chiffrage), `subproject_delete_refused` (le Poste de commande ; la réception sur site depuis
EP-14/L42l), `contributors_without_manager_refused` (Camille Martin passée contributrice) et
`contributors_accounts_refused` (Alix Moreau, désactivée, passée chef de projet à la deuxième ligne,
et un compte inconnu à la cinquième, hors des quatre lignes de la liste du témoin). Chaque lecture
d'un projet qui liste `update` liste `update_win_probability` à sa suite ; chaque lecture ou
écriture d'un sous-projet porte ses commandes ; `contributor_suggestions` nomme l'atelier de câblage
et le monteur câbleur ; les listes engendrées par `wftools.mocklists` en dérivent sans retouche de
l'outil.
`tools/tests/test_mockproject.py` tient chacun contre l'univers et contre le contrat : la commande qui
suit `update` et son état, les taux dans leurs bornes, le prochain état de chaque projet, les
commandes de chaque sous-projet d'après ses coûts — et, depuis EP-14/L42l, d'après sa citation par
une révision marquée —, le libellé du porteur d'un code pris, les lignes désignées
d'une liste refusée, ce que chaque proposition nomme, et le 409 de tout refus qui nomme une
condition. Le client est régénéré ; le front reçoit l'icône de la commande, ses catalogues
(`enums.ProjectCommand.update_win_probability`, `enums.CommandCondition.project_before_in_progress` et
`subproject_without_actual_costs`, `enums.LifecycleTrigger`, `enums.SubprojectCommand`,
`errors.UNKNOWN_USER` et `USER_INACTIVE`, `HAS_ACTUAL_COSTS` et `WIN_PROBABILITY_FROZEN` retirés) et
le test de la suppression refusée adapté au 409 nommé ; les écrans de L44a et L44b adoptent le reste
dans un lot propre.

## La suppression d'un sous-projet cité par une révision marquée (EP-14/L42l)

*Corrigée par C-256 ; complétée par EP-14/L42q (C-273), section « Le sous-projet porté par le devis
en cours, le collage partiel (EP-14/L42q) ». Le texte qui suit est gardé tel quel.*

**Un sous-projet qu'une révision marquée cite ne se supprime pas** (#647 ; décision de l'auteur du
2026-10-10 sur #634 ; §4.4.1, WF-PRJ-0050, WF-IHM-0090). Les sous-projets déterminent la courbe de la
valeur acquise : supprimer un sous-projet qu'une révision marquée cite y aurait des effets de bord
difficilement maîtrisables. La prose du §4.4.1 le disait déjà — un sous-projet référencé par une
révision marquée « ne l'est pas davantage », supprimable — ; le corps et le Vérif de WF-DAT-0080
disent le contraire : « Celle d'un sous-projet référencé par une révision marquée le marque
supprimé ». C'est ce Vérif que L42i avait suivi en retirant la condition. **Le contrat suit la
décision, contre le Vérif**, dont la correction est proposée à l'auteur dans `docs/spec/TODO.md`, § 2
(#634, PR #649) : aucun agent ne modifie la spécification, et la contradiction demeure jusqu'à ce
qu'il l'écrive. Le refus d'un risque cité (`risk_not_cited`) est le précédent : même cause, même
forme.

`subproject_not_cited` rejoint le catalogue, nommée comme ce qui doit tenir, avant
`subproject_without_actual_costs` : elle manque à la commande `delete` d'un sous-projet que cite une
ligne d'une révision marquée. Quand les deux manquent, la commande les liste toutes deux,
`subproject_not_cited` d'abord, et le 409 de `deleteSubproject` (`STATE_FORBIDS_OPERATION`, sans
`fields`) nomme celle-là : la citation ne se lève jamais — une révision marquée est immuable
(WF-DAT-0020) —, quand des coûts imputés laisseraient croire qu'en les retirant la suppression
aboutirait ; c'est la raison que `deleteRisk` donne pour nommer `risk_not_occurred` avant
`risk_not_cited`. Un sous-projet qu'aucune révision marquée ne cite et qu'aucun coût ne charge est
retiré de la base, 204 ; aucun sous-projet n'est plus « marqué supprimé ». La description de
`deleteSubproject` le dit, avec la décision et le Vérif qu'elle contredit.

**Sur un projet clos, `project_not_terminal` vient en dernier** (revue de L42l ; WF-CYC-0100). La
commande `delete` d'un sous-projet cité et chargé d'un projet clos manque alors de trois conditions,
listées `subproject_not_cited`, `subproject_without_actual_costs`, `project_not_terminal`, et le 409
nomme la première qui manque. C'est l'ordre dans lequel le projet liste déjà les siennes : la
condition propre à la commande d'abord, celle du projet ensuite — `update_win_probability` d'un
projet terminé manque de `project_before_in_progress` puis de `project_not_terminal`
(`project_completed`) ; `create_revision` d'un projet terminé, qui n'a pas de révision en cours,
ne nomme que `project_not_terminal`, comme `update`, qui n'a pas de condition propre. Écarté :
`project_not_terminal` d'abord, que la relecture proposait — l'ordre du contrat aurait dépendu de
l'objet qui porte la commande. Aucun exemple ne lit les sous-projets d'un projet clos :
`test_mockproject.py` fixe sur une variante construite dans le test la règle qu'il applique aux
exemples, et la confronte à `project_completed`. **Réécrit par US-0702/L3** (#1657) : un projet clos
ne liste plus aucune commande, ni ses sous-projets ; l'ordre décidé ici reste celui du 409 de
`deleteSubproject`, `project_not_terminal` en dernier.

Écartés : garder la suppression logique de L42i jusqu'à ce que l'auteur corrige le Vérif — le contrat
aurait promis ce que l'auteur a refusé, et l'écran de L44e l'aurait appris ; nommer
`subproject_without_actual_costs` d'abord, qui aurait gardé tel quel l'exemple de refus de L42i, mais
renvoyé vers des coûts dont le retrait ne suffit pas, et laissé `subproject_not_cited` sans aucun
sous-projet du témoin pour la montrer ; une information de lecture de plus (« cité par une révision
marquée »), que la commande dit déjà.

**Les deux sous-projets du témoin sont cités**, non le seul Poste de commande : depuis EP-14/L45a, la
référence marquée le 1er février porte toute la structure, et les lots « Ligne d'essais » citent les
essais et la mise en service comme le cœur et les lots « Poste de commande » citent le Poste de
commande ; l'offre v1.0, marquée le 15 décembre 2025, précède leur déclaration et n'en cite aucun.
Leurs lectures (`subprojects`, et `subprojects_by_label` et `subprojects_with_actual_costs`, qu'en
dérive `make mock-data`) et le renommage (`subproject_updated`) portent les deux conditions ; le
sous-projet créé aujourd'hui (`subproject_created`), qu'aucune révision marquée ne cite, la seule de
ses coûts. Exemples : `subproject_delete_cited` (corrélation 1068), la suppression du Poste de
commande refusée par `subproject_not_cited` ; `subproject_delete_refused`, que L42i écrivait pour le
Poste de commande, refuse désormais celle de la réception sur site, aussitôt chargée de la facture
FA-2026-0295, par `subproject_without_actual_costs` — l'un et l'autre réels, sans contrefactuel. Les
exemples écrits à la main le restent (`subprojects`, `subproject_updated`, `subproject_created`, les
deux refus) ; les listes dérivées sont engendrées. `tools/tests/test_mockproject.py` applique aux
exemples la règle qu'il fixe : les conditions de chaque sous-projet viennent de sa citation par une
révision marquée, lue dans la référence sur toute la structure, puis de ses coûts ; et le test
transversal des refus tient le nouveau 409 sans `fields`. Les catalogues reçoivent
`enums.CommandCondition.subproject_not_cited` ; le client est régénéré, et l'adoption par l'écran
des sous-projets revient à L44e.

## La date confirmée d'une restauration déposée, le refus hors plage des paramètres (EP-14/L42m)

Deux constats de contrat, #628, relevé par la relecture de L42h, et #659, relevé par celle de
L43e, rangés dans #507 et réalisés par un lot de contrat d'EP-14 (#663). Les décisions sont de
l'agent de réalisation du lot, chaque fois avec sa raison.

**La date confirmée d'une sauvegarde déposée est l'instant que porte son archive, lu au dépôt**
(`FileUpload.backup_taken_at` ; #628, WF-ADM-0160). WF-ADM-0160 veut une confirmation qui « énonce
la date de la sauvegarde », et son Vérif, une confirmation qui « nomme la date de la sauvegarde » :
pour une sauvegarde de la liste, c'est `Backup.taken_at` (EP-14/L42h) ; une sauvegarde copiée hors
de la plateforme puis déposée (`external_backup_upload_id`) n'a pas de `Backup`. L'archive que la
plateforme écrit porte l'instant de sa sauvegarde — celui que le nom de son fichier écrit aussi,
`waterfall-backup-<instant>.tar` (L42h) — : le dépôt d'une sauvegarde le lit et le rend, comme la
liste rend celui d'une sauvegarde qu'elle porte, et `startRestore` compare la date confirmée à cet
instant, refusée sinon par le même 422 que pour une sauvegarde de la liste
(`/acknowledged_backup_taken_at`, `BACKUP_DATE_MISMATCH`, sans paramètre). Le champ est exigé de
tout dépôt, nul pour le fichier d'un import, qui n'a pas de date de sauvegarde : la date ne se
compare qu'à un dépôt de sauvegarde, et une restauration demandée sur un dépôt d'import est refusée
par `UPLOAD_PURPOSE_MISMATCH` seul (revue de L42m). Côté écriture, le téléchargement
(`downloadBackup`) et la copie externe (`BackupExternalCopy`) disent que l'archive porte l'instant
de sa sauvegarde, que le dépôt relit. Une archive dont
l'instant ne se lit pas n'est pas une sauvegarde de Waterfall : le dépôt est refusé, 422
`FILE_FORMAT_UNREADABLE`, sans paramètre — `expected_format` nomme une nature d'échange, et aucune
n'est celle des sauvegardes ; le fichier d'un import, lui, n'est lu qu'à l'analyse (`openImport`).
Écartés :

- la date attendue dans `params` du 422 de `startRestore`, seule — l'autre proposition de #628 : la
  confirmation doit énoncer la date *avant* que la restauration soit demandée, et un écran qui ne la
  connaîtrait que par un premier refus ferait confirmer à l'aveugle ; ajoutée au dépôt, elle
  doublerait ce que le dépôt rend, comme L42h a écarté de nommer dans `params` la date que la liste
  porte ;
- la date lue dans le nom du fichier déposé : un nom se change, et le serveur comparerait la
  confirmation à ce que le client lui a dit ;
- faire d'un dépôt une sauvegarde de la liste (une origine `uploaded` de plus) : un dépôt est en
  transit et expire en un jour (WF-DAT-0120), quand la liste est celle de la rotation et du
  marquage (WF-ADM-0170) ; ses commandes et ses filtres auraient à l'exclure partout ;
- une opération qui relise un dépôt (`getFileUpload`), pour le seul champ que le dépôt rend déjà ;
- lire l'instant à la restauration, dans le worker : trop tard pour la confirmation ;
- accepter un dépôt dont l'instant ne se lit pas, la date nulle, et refuser sa restauration : un
  dépôt de plusieurs gigaoctets gardé un jour pour rien ; un code propre (`BACKUP_UNREADABLE`), là
  où le format illisible d'un fichier a déjà le sien.

*Remplacé en partie à la reprise de `main` après EP-03 : une sauvegarde se dépose par morceaux,
sa date lue au manifeste à l'achèvement (`completeChunkedUpload`, #1006), et la date confirmée qui
n'est pas la sienne est refusée par 400 `CONFIRMATION_REQUIRED` ; `file_upload_external_backup`
devient un exemple de l'achèvement, `file_upload_backup_unreadable` est retiré.*

Exemples, écrits à la main : `file_upload_external_backup`, la copie de la sauvegarde planifiée de
la nuit du 20 mai que le site de secours de Lyon garde parmi ses trente copies quand la plateforme
n'en conserve plus que sept, déposée aujourd'hui à 13 h 50, sa taille sur la ligne des sauvegardes
de la liste, qui croissent chaque nuit du même pas (identifiant …0a15) ; aux corrélations 1069 et
1070, `restore_external_date_mismatch`, sa restauration confirmée avec la date de la sauvegarde du
2 juin que la liste donne, et `file_upload_backup_unreadable`. `file_upload` porte la date nulle.
`test_mockuniverse.py` tient le dépôt contre la liste et la planification — une nuit planifiée plus
ancienne que la liste, dans les copies de Lyon, nommée comme la plateforme nomme ses sauvegardes —,
et chaque refus contre son enveloppe et son opération. Que la vérification d'une sauvegarde déposée
soit énoncée, comme celle d'une sauvegarde de la liste, n'est pas tranché ici : rien dans #628.

**Un délai hors de sa plage est refusé par `VALUE_OUT_OF_RANGE`, la borne franchie ; un seuil
hors de ]0, 1[, par un motif propre aux seuils** (#659, point 1 ; WF-REF-0170, WF-REF-0180). Le
délai entre deux revues (`/max_weeks_between_reviews`) va de `1` à `104` semaines, les bornes que le
schéma publiait sans que l'opération dise leur refus : 422 `VALIDATION_FAILED`,
`VALUE_OUT_OF_RANGE`, `fields[].params.minimum` ou `maximum` la seule borne franchie, comme les deux
taux d'un projet (EP-14/L42i, `project_rates_out_of_range`) — des entiers, bornes admises. Un seuil
(`/index_thresholds/<seuil>`) est une valeur de l'indice « inférieure à 1 » (WF-REF-0170),
strictement positive pour laisser une zone d'alerte (`IndexThreshold`, L42h), sans précision fixée :
l'intervalle ]0, 1[ est ouvert, et n'a ni plus petite ni plus grande valeur admise que `minimum` ou
`maximum` pourraient nommer — la raison même pour laquelle L42h avait écarté `VALUE_OUT_OF_RANGE`
pour l'ordre strict des seuils. Il est donc refusé par un motif par champ nouveau au catalogue,
`THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE`, sans paramètre, sur le modèle de `THRESHOLD_NOT_BELOW_WATCH` :
sa phrase reprend `IndexThreshold` (« compris entre 0 et 1, l'un et l'autre exclus »), WF-REF-0170
ne disant que « inférieures à 1 ». Le motif d'`IndexThreshold` reprend celui de L42h, élargi aux
zéros de tête (revue 3 de L42m) : il admet `0.875` et `00.5`, et il est exactement, parmi les
décimaux de `Decimal`, celui des valeurs strictement entre 0 et 1 — sans quoi `00.5` aurait reçu le
code de la plage, une fausse cause. Un seuil se juge en trois temps, chacun par sa contrainte (revue 2 de L42m) : la
forme d'abord — un seuil qui n'est pas un décimal, le motif de `Decimal` (`0,9`, `.5`), est refusé
par `NUMBER_INVALID`, comme toute valeur décimale mal écrite ; la plage ensuite — un décimal que le
motif du seuil refuse (`0`, `1`, `1.5`), par `THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE` ; l'ordre enfin —
`THRESHOLD_NOT_BELOW_WATCH`, entre seuils dans ]0, 1[ seulement. Écarté : un motif large
(`^\d+(\.\d+)?$`) avec la plage dite en texte, qui perdrait une contrainte lisible par machine
sans rien gagner, `allOf` séparant déjà la forme (`Decimal`) de la plage (`IndexThreshold`).
Le premier exemple du 422 reste `bounds_not_ordered`, celui que le faux back sert à une requête invalide ; le nouveau,
`reference_settings_out_of_range` (corrélation 1071 : la vigilance de l'indice de coût à 1, refusée
par le nouveau motif, zéro semaine entre deux revues, refusée par `VALUE_OUT_OF_RANGE`), vient en
dernier. Décision de l'agent de livraison à la relecture de L42m, qui renverse la première rédaction.
Écartés : deux décimales au plus, de `0.01` à `0.99`, sur le modèle du taux horaire, que la première
rédaction retenait — elle restreignait WF-REF-0170, qui ne fixe aucune précision (les deux décimales
du taux venaient de `Money`, WF-DAT-0100), et aurait refusé `0.875` par une fausse cause ; un
paramètre générique d'exclusion (`exclusive: true`) à côté de `minimum` et `maximum`, pour un seul
champ du contrat ; `VALUE_OUT_OF_RANGE` nommant `0` et `1`, que le paramètre donne pour des bornes
admises et que le front dirait comme telles (« Valeur minimale : 0 »).

**La rétention des sauvegardes hors de sa plage est refusée de même** (le jumeau de #659, relevé
par la relecture de L43d ; WF-ADM-0170) : `setBackupSchedule` publiait `minimum: 1` et
`maximum: 365` sur `retained_count` et `external_copy.retained_count` sans que son 422 dise leur
refus. Hors de ces bornes : `VALUE_OUT_OF_RANGE`, `params.minimum` ou `maximum` la seule borne
franchie, sur `/retained_count` ou `/external_copy/retained_count` ; le minimum de la copie reste la
rétention de la plateforme (WF-EXP-0050), `1` quand celle-ci est elle-même hors de ses bornes.
L'exemple `backup_schedule_retention_out_of_range` (corrélation 1072 : aucune sauvegarde gardée,
quatre cents copies) vient en dernier sous le 422, `unknown_location` restant le premier ;
`test_mockuniverse.py` le tient contre les bornes du schéma et chaque planification des exemples
dans leur plage. Le jour d'une sauvegarde hebdomadaire (`weekday`, de 1 à 7) publie aussi des bornes
sans refus décrit : relevé, non traité ici.

**La réponse de la matrice change une zone** (`reference_settings_matrix_updated` ; #659, point 2 ;
WF-REF-0160) : la case de la plus faible probabilité et de la plus forte gravité, p1/g4, rang 3,
passe de vigilance à alerte, la case que #659 proposait et que le test du formulaire de la matrice
(L43e, `settings-forms.dom.test.tsx`) change déjà dans la requête qu'il envoie — la réponse est
celle de cette requête, pour que le test prouve qu'une zone répondue remplace la zone lue. La
requête porte la matrice entière, les trois listes étant exigées (`RiskMatrixSettings`). Écarté :
mettre aussi p2/g4 en alerte, pour une matrice qui ne soit jamais moins sévère à une probabilité
plus haute — aucune exigence ne le demande (WF-REF-0160 ne règle que les bornes), et la réponse
n'aurait plus été celle de la requête du test.
`tools/tests/test_mocksettings.py` tient chaque réponse contre la lecture des paramètres — ce qui
change, et rien d'autre —, le motif d'un seuil, les bornes du délai contre le schéma, chaque seuil et
chaque délai des exemples — l'historique des indices compris — dans leur plage, le refus à ses
pointeurs, et l'ordre des exemples du 422.

Le client est régénéré ; le front reçoit la phrase du nouveau motif
(`errors.THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE`) et ne change pas autrement — les tests du formulaire
des réglages (L43e, livré) qui disent le refus hors plage et la zone répondue, et la restauration
depuis un fichier (L43d), qui énonce la date du dépôt, viennent ensuite.

## Les comptes non admis, les adresses et le 503 des opérations gardées (EP-03, #664, #665, #666)

Décisions de l'auteur du 2026-10-10, sur trois constats de la revue d'US-0350/L3.

**Un compte que Waterfall n'admet pas est refusé par 401 `ACCOUNT_NOT_ADMITTED`** (#664). Un
compte local du fournisseur que Waterfall n'a pas créé (WF-ADM-0070), sans nom, sans prénom ou
sans adresse, ou dont l'adresse est déjà portée par un autre (WF-ADM-0050), n'est pas un compte
désactivé : `ACCOUNT_DEACTIVATED` le lui dirait à tort. Le front le traite comme lui, un refus
sans renvoi à la connexion, qui bouclerait. Écarté : `SESSION_REQUIRED`, qui ferait boucler ;
un 403, que chaque opération devrait déclarer. Une personne de l'annuaire dont l'adresse est
déjà portée par un compte de Waterfall est rattachée à ce compte, l'annuaire étant ce qui
reconnaît la personne par son adresse (motif de WF-ADM-0050) ; venue d'un fournisseur externe,
elle est refusée : un fournisseur peu rigoureux sur les adresses ouvrirait le compte d'un autre.

**Une adresse est reçue telle qu'elle est écrite** (#665). La règle est au tableau du README :
une forme simple, casse gardée, comparée sans égard à la casse, domaines à usage spécial et sans
point admis. Waterfall n'envoie aucun courriel lui-même, le fournisseur d'identité le fait : il
n'a pas à être plus strict que l'annuaire qu'il lit, et un annuaire d'entreprise en `.local`
donnerait des comptes qu'il ne saurait pas créer. Écarté : la validation d'email-validator
(`EmailStr`), qui refuse ces domaines et récrit la casse.

**Toute opération gardée déclare 503** (#666). La lecture des clés du royaume, à la première
requête ou après une rotation, et l'admission d'un compte inconnu attendent le fournisseur
d'identité ; s'il ne répond pas, l'opération rend 503 `COMPONENT_UNAVAILABLE`
(`params.component` à `identity_provider`). La règle `rule/protected-operation-declares-503` le
vérifie, comme celle du 401. Écarté : la règle écrite au seul README, qu'une réponse validée
contre le contrat contredirait.

## Les refus des écritures des paramètres de ressources (EP-14/L42j)

Les points 1 à 7 de #575, relevés par EP-02/L43b, et son complément de la revue d'EP-02/L42g, les
références inconnues ; le point 8 est fait par EP-14/L42h. Les décisions sont de l'agent de
réalisation du lot (#613), chacune avec sa raison. Deux suivent la spécification révisée le
2026-10-09 (#581), que le contrat ne suivait pas encore : le libellé unique d'un calendrier
(WF-REF-0110) et le déplacement d'un nœud sous un nœud actif seulement (WF-REF-0070). Trois autres
règles de cette révision sortent du périmètre et attendent une décision (#684) : le code unique d'un
rôle (WF-REF-0090), la catégorie d'un rôle gardée dans la main-d'œuvre (WF-REF-0030, WF-REF-0040),
le projet que nomme le refus d'un calendrier (WF-PLA-0010). Le lot ne touche au front que pour
compiler ; l'adoption par les écrans de L43b revient à L43g (#685).

**La désignation par défaut est une commande du calendrier** (`CalendarCommand`, point 1 ;
WF-REF-0120, WF-IHM-0090), sur le modèle de `CostTypeCommand` : `deactivate`, `reactivate`,
`set_default`, au plus deux — celle qui change l'état, puis la désignation, listée pour tout
calendrier qui n'est pas celui par défaut, indisponible pour un calendrier désactivé, faute de
`calendar_active`, nouvelle au catalogue et nommée comme `org_node_active`. Écartés : `set_default`
dans `ReferenceCommand`, que #575 proposait — les nœuds et les rôles la partagent, à une commande
(`maxItems: 1`, EP-02/L42a), ce pour quoi L42g a écarté `change_kind` ; la désignation listée,
indisponible, sur le calendrier par défaut, qui dirait ce qui va de soi, comme la réactivation d'un
objet actif.

**`setDefaultCalendar` porte la version lue, et ses refus sont nommés** (point 2). Le corps porte le
`lock_version` du calendrier désigné, seul : la désignation retirée au précédent est un effet que le
serveur décide, comme une désactivation en cascade n'envoie pas la version de ce qu'elle désactive ;
sa version avance, et le client relit la liste. 412 `STALE_LOCK_VERSION` (EP-02/L42g) ; 409
`STATE_FORBIDS_OPERATION`, `params.missing_condition` à `calendar_active`, sans
`conflicting_object_id` — c'est le calendrier même qui se réactive —, à la place de la réponse
partagée `Conflict` ; le 422 `TASK_WITHOUT_WORKING_HOURS` reste. Désigner le calendrier qui l'est
déjà, que sa commande ne liste pas, ne change rien et répond 200, comme un `PUT` répété — la version
contrôlée d'abord, 412 si elle est périmée, comme toute écriture versionnée (revue 1) ; écarté : un 409
pour un effet déjà atteint.

**Une catégorie dit le type de sa nature** (`CostCategoryImage.cost_type_kind`, point 3 ; WF-REF-0090,
WF-ARC-0020), exigé, résolu à la lecture comme `cost_type_label` : le formulaire d'un rôle ne propose
que les catégories de main-d'œuvre sans relire les natures. Écarté : un filtre `cost_type_kinds`, que
#575 proposait aussi — la page lit déjà toutes les catégories pour filtrer les rôles, et le faux back,
qui ne filtre rien, servirait au formulaire des catégories hors main-d'œuvre. `make mock-data` l'écrit
dans les catégories engendrées.

**Les refus par champ d'un rôle** (point 4 et complément ; WF-REF-0090, WF-REF-0100).
`createResourceRole` et `updateResourceRole` décrivent leur 422 `VALIDATION_FAILED` : `/label` vide ou
trop long, comme une nature (L42g) ; un rattachement absent ou nul, `VALUE_REQUIRED`, les trois étant
obligatoires ; inconnu, `UNKNOWN_ORG_NODE` ou `UNKNOWN_CALENDAR`, nouveaux au catalogue — chaque objet
a le sien depuis `UNKNOWN_COST_TYPE` —, ou `UNKNOWN_COST_CATEGORY` ; une catégorie hors main-d'œuvre,
`LABOUR_CATEGORY_REQUIRED`, le code du taux d'une telle catégorie (L42g), qui devient motif par champ —
écarté : un second code pour le même fait ; un rattachement désactivé, `INACTIVE_REFERENCE_OBJECT`, les
rattachements « désignent des objets actifs au moment où ils sont faits » — à la modification, quand
elle change la catégorie ou le calendrier seulement : un rôle qui garde les siens, désactivés depuis,
se modifie, comme une catégorie sous sa nature désactivée ; une capacité négative, point 6. Un champ ne
porte qu'un motif, inconnu, puis hors main-d'œuvre, puis désactivé : réactiver une catégorie hors
main-d'œuvre ne lèverait rien, et la condition qui ne se lève pas vient d'abord, comme pour
`deleteSubproject` (L42l). `LABOUR_CATEGORY_REQUIRED` vaut aussi pour une catégorie gardée : un rôle
dont la catégorie a quitté la main-d'œuvre ne se modifie pas sans en changer, le corps de WF-REF-0090
ne rattachant un rôle qu'à une catégorie de main-d'œuvre, en attendant que le contrat empêche la
catégorie d'un rôle de quitter la main-d'œuvre (#684, point 2 ; revue 1). `updateResourceRole` garde
l'autre enveloppe de son 422, `TASK_WITHOUT_WORKING_HOURS`.

*Remplacé en partie par EP-14/L42r : le contrat empêche désormais la catégorie d'un rôle de quitter
la main-d'œuvre (`cost_category_without_role`, `cost_type_without_role`) ; la catégorie qu'un rôle
garde est toujours de main-d'œuvre, et « en attendant » n'a plus d'objet.*

**Un nœud ne se place que sous un nœud actif, ni sous lui-même ni sous ses descendants** (point 5 ;
WF-REF-0070, WF-REF-0080). `/parent_id` est refusé par `UNKNOWN_ORG_NODE` ; par `ORG_NODE_CYCLE`,
nouveau, sans paramètre, pour le nœud lui-même ou l'un de ses descendants — écartés : `LINK_CYCLE`,
dont la phrase parle des liaisons entre tâches, et `VALUE_OUT_OF_RANGE`, sans borne à nommer — ; par
`INACTIVE_REFERENCE_OBJECT` pour un nœud désactivé, quel que soit l'état du nœud déplacé : WF-REF-0070
révisé ne déplace un nœud que « sous un autre nœud actif ou à la racine », et son Vérif refuse « le
déplacement sous un nœud désactivé ». L'exception d'EP-02/L42d, un nœud désactivé déplacé sous un
nœud désactivé, est retirée. Un seul motif, le premier dans cet ordre : inconnu, puis boucle, puis
désactivé. Seul le déplacement est contraint (revue 1) : à la modification, `INACTIVE_REFERENCE_OBJECT`
ne vaut que si elle change le parent, jugé sur la valeur envoyée : un nœud désactivé qui garde son
parent désactivé se modifie, comme un rôle qui garde sa catégorie, ou une catégorie sa nature
désactivée (L42g) — `org_node_renamed_under_inactive`, la cellule robotique renommée sous le bureau
d'études automatismes. Le parent est donc exigé à la modification (`OrgNodeUpdate`), nul pour une
racine (revue 2), et son absence refusée par `VALUE_REQUIRED` sur `/parent_id` (revue 3) ; écarté : un parent absent qui garderait le parent lu, une règle de plus à tenir,
contraire à l'envoi du corps entier.

**Une valeur unique prise nomme son porteur.** Le code d'un nœud, par `conflicting_object_label` en
plus de son identifiant, comme un projet (L42i) : l'arbre lu sans les désactivés, ou filtré, peut ne
pas montrer le porteur, que l'utilisateur réactivera plutôt que d'en créer un second (WF-IHM-0090) —
BE-AUTO, désactivé, dans `org_node_code_taken`. Le libellé d'un calendrier est unique, désactivés
compris (WF-REF-0110 révisé : « deux calendriers de même libellé sont refusés ») : 409
`ALREADY_EXISTS` sur `/label`, l'identifiant du porteur seul, son libellé étant la valeur envoyée. La
table `UNIQUE` de `test_mockcostsettings.py` compte désormais quinze écritures.

**Les heures d'un jour et la capacité sont bornées** (points 6 et 7 ; WF-REF-0110, WF-REF-0100) : de
`0` à `24` pour une heure d'un jour (`/weekly_hours/<jour>`), `0` au moins pour les heures mensuelles
et l'effectif (`/capacity/...`), refusés par 422 `VALUE_OUT_OF_RANGE`, `fields[].params.minimum` ou
`maximum` la seule borne franchie, comme les taux d'un projet (L42i) : bornes et zéro sont admis, un
jour chômé, une capacité nulle que rien n'interdit. Écartés : un motif sans signe sur `Hours`, que
lectures et écritures partagent jusqu'aux durées des tâches, et qui ne nommerait pas la borne ; un
plafond de la capacité, qu'aucune exigence ne donne. `createCalendar` et `updateCalendar` décrivent
leur 422, et les quatre modifications leur 412 en place, chacune avec son exemple.

**Exemples**, écrits à la main aux corrélations 1080 à 1090 : `org_node_code_taken`,
`org_node_move_cycle_refused` (la direction technique sous l'atelier de câblage),
`org_node_update_stale`, `resource_role_attachments_refused` (un nœud inconnu, la sous-traitance, la
semaine de trente-neuf heures désactivée), `resource_role_update_refused` (le technicien de mise en
service passé à cette semaine, un effectif de -1), `resource_role_update_stale`,
`calendar_label_taken`, `calendar_hours_refused` (25 heures le lundi, -7 le samedi),
`calendar_update_stale`, `calendar_default_refused`, `calendar_default_stale`. Les calendriers lus et
écrits portent leur désignation. `tools/tests/test_mockresourcesettings.py` tient chacun contre
l'univers et contre le contrat ; le test transversal des refus tient le nouveau 409. Le front reçoit
ses catalogues (`errors.UNKNOWN_ORG_NODE`, `UNKNOWN_CALENDAR`, `ORG_NODE_CYCLE`,
`enums.CommandCondition.calendar_active`, `enums.CalendarCommand`) et envoie la version lue à la
désignation.

## Les bornes sans refus, la restauration depuis un dépôt, la précision d'une part, les sous-projets d'un projet clos (EP-14/L42o)

Cinq constats de #507 relevés pendant L42m, L43d, L44e et L51, regroupés dans un lot de contrat
(#698) : #677, #679, #694, le point 2 de #683 et le point 1 de #673. Les décisions sont de l'agent
de réalisation du lot, chacune avec sa raison, et, à la relecture 1, de l'agent de livraison pour la
somme des parts.

**Les bornes de #677 ont leur refus.** `setBackupSchedule` (`/weekday`, de 1 à 7), `createNode`
(`/position`, `/estimate_line/payment_delay_days`, au moins 0), `updateEstimateLine`
(`/payment_delay_days`), `moveNodes` (`/position`) et `requestExport` (`/depth`, au moins 1)
publiaient leurs bornes sans que leur 422 dise le refus : 422 `VALIDATION_FAILED`,
`VALUE_OUT_OF_RANGE`, `fields[].params.minimum` ou `maximum` la seule borne franchie, comme la
rétention des sauvegardes (EP-14/L42m) et les taux d'un projet (EP-14/L42i). `lock_version` reste à
part : un compteur, dont la version périmée se dit par 412. Les autres corps du contrat ne sont pas
parcourus ici : la largeur d'une colonne des préférences de grille (`GridPreferences.column_widths`,
au moins 20), que `updateMyPreferences` publie sans 422, part à une issue de l'agent de livraison.
Écarté : un motif propre à la position (`POSITION_INVALID`), qui ne nommerait pas la borne.
Exemples, écrits à la main aux corrélations 1091 à 1095 : `backup_schedule_weekday_out_of_range` (le
dimanche numéroté 0, à l'américaine), `node_create_out_of_range` (une ligne placée à -1 et payée
d'avance, -30 jours), `estimate_line_payment_delay_out_of_range` (les « Borniers », délai -30),
`nodes_move_position_out_of_range` (les « Borniers » déplacés à -1) et `export_depth_out_of_range`
(l'arborescence au niveau 0). Sous `setBackupSchedule` et `createNode`, le nouvel exemple vient en
dernier, le premier inchangé ; `updateEstimateLine`, `moveNodes` et `requestExport` n'avaient aucun
exemple sous leur 422 : le nouveau est le premier, celui que le faux back sert.
`tools/tests/test_mockbounds.py` lit chaque borne dans le schéma du corps, confronte l'exemple à la
borne du côté franchi, et vérifie qu'aucune autre borne de ces cinq corps — hors `lock_version` et
les rétentions de L42m — n'est publiée sans refus.

*Remplacé en partie par EP-14/L42r : `updateMyPreferences` déclare le refus de la largeur d'une
colonne (#711), et `test_mockbounds.py` parcourt les corps de toutes les écritures, chaque borne
publiée devant avoir son refus et son exemple.*

*Remplacé en partie par US-0460/L3b (#1183) : `createNode` et `moveNodes` n'écrivent plus de
`position` — leur place se désigne par `after_node_id`, refusé par `NODE_NOT_SIBLING` —, et
n'en publient plus la borne ; `nodes_move_position_out_of_range` est remplacé par
`nodes_move_after_not_sibling`, et `node_create_out_of_range` ne garde que le délai de paiement.*

**Une sauvegarde déposée est vérifiée par sa restauration, avant toute déconnexion** (#679 ;
WF-ADM-0150, WF-ADM-0160, WF-ARC-0090). Une sauvegarde de la liste ne se restaure que vérifiée
après sa production (`backup_verified`, EP-14/L42h) ; une archive déposée n'avait aucune
vérification dite, et une archive altérée aurait échoué après la déconnexion des utilisateurs. La
restauration la vérifie d'abord, dans le worker, de la même vérification, qui confirme aussi
l'instant que le dépôt a lu (`backup_taken_at`) ; la déconnexion ne vient qu'après. Une archive qui
ne la passe pas fait échouer la tâche (`failed`), son `problem` à `STATE_FORBIDS_OPERATION`,
`params.missing_condition` à `backup_verified` — la condition qui manque à une sauvegarde de la
liste non vérifiée (`restore_unverified_refused`), avec sa phrase au catalogue : aucun utilisateur
n'a été déconnecté, aucune base remplacée, et l'écran qui a lancé la restauration le lit sur la
tâche (`getBackgroundTask`, WF-IHM-0080). Le dépôt, lui, ne lit que l'instant de l'archive ; celui
qu'une restauration acceptée désigne est gardé jusqu'à la fin de sa tâche, même au-delà de son jour,
pour que la purge (WF-DAT-0120) ne le retire pas en route. Écartés :

- la vérification au dépôt, dans la requête : une archive de plusieurs gigaoctets vérifiée hors du
  worker, une opération longue qui ne rendrait pas la main, contre WF-ARC-0090 ;
- une vérification au dépôt confiée au worker, dont `FileUpload` dirait l'état et que la
  confirmation attendrait : un état, une condition et une relecture du dépôt de plus — L42m a déjà
  écarté `getFileUpload` —, pour avancer de quelques secondes un échec que la restauration dit
  aussi avant de déconnecter quiconque ;
- `FILE_FORMAT_UNREADABLE`, que la première rédaction du lot retenait : l'archive est reconnue — le
  dépôt en a lu l'instant —, mais altérée, et le format illisible n'aurait pas dit la vraie cause
  (relecture 1) ;
- un code propre (`BACKUP_VERIFICATION_FAILED`), là où la condition de la commande `restore` dit
  déjà ce qui manque.

**`startRestore` déclare son 404**, sur le modèle d'`openImport` : une sauvegarde que la liste n'a
pas, un dépôt inconnu ou expiré — un dépôt ne vit qu'un jour (WF-DAT-0120) —, `NOT_FOUND`, sans
paramètre ni `fields`, sans distinguer l'objet inconnu de l'objet disparu (WF-ADM-0110) ; l'écran
sait lequel il a désigné. Écartés : un 410 pour le dépôt expiré, que rien d'autre dans le contrat
n'emploie et qui révélerait qu'il a existé ; un 422 `UNKNOWN_*` au champ, la forme d'une référence
inconnue d'un formulaire, quand l'objet que la restauration désigne est le sujet de l'opération,
comme le dépôt d'un import. Exemples, écrits à la main : `restore_not_found` (corrélation 1096, la
copie de Lyon déposée la veille à 11 h, restaurée ce matin à 11 h 30, son dépôt expiré : c'est elle
que le dépôt de 13 h 50 redépose) et `task_restore_verification_failed` (tâche …0938, une variante
déclarée : la même copie altérée sur l'emplacement, sa restauration échouée à la vérification à
14 h 03 min 40 s). `test_mockuniverse.py` les tient contre le dépôt et l'opération.

*Complétée par EP-14/L55 : `partition` ne lève plus sur un total nul ; la part d'un total nul est
non calculable, de motif `no_total` (2026-10-29, #1633, G-02 : « La part d'un total nul »).*

**Une part, un avancement ou un taux calculé est donné à quatre décimales, jamais nul quand il ne
l'est pas, et les parts d'une répartition somment à un** (#694 ; README, « Une part… » ;
WF-DAT-0100, WF-DEV-0060, WF-PTF-0080, #626). Le contrat ne disait pas la précision d'un rapport
calculé : la part d'une répartition (`share` d'`AmountByKey` et de `ComputableAmountByKey`), les
avancements, la consommation du budget, le taux de charge et le taux de transformation. Il la dit
désormais une fois, dans les conventions du README, et chaque champ y renvoie : quatre décimales, le
centième de pour cent qu'un écran montre, arrondi au plus proche, une demie s'éloignant de zéro,
comme l'arrondi d'`Intl` qui la montre ; une valeur non nulle que quatre décimales rendraient nulle
est donnée à son premier chiffre significatif — `0.00003` pour 0,0000309 —, ce que l'auteur a
décidé pour l'écran (#626) : une part non nulle ne se lit pas « 0 % », et le front dit « < 0,01 % »
d'après la part seule. Près de 1, l'arrondi ordinaire demeure (0,99996 est donnée `1`) : #626 n'a
tranché que le côté de zéro. Les parts d'une répartition du total — par nature, par sous-projet, par
nœud — somment exactement à 1 : le reste de leurs arrondis, plancher compris, est porté sur la plus
grande, qui peut alors porter plus de quatre décimales (`0.99999997` à côté de `0.00000003`). Les
Vérif de WF-DEV-0060 (« la somme de leurs pourcentages vaut cent ») et de WF-PTF-0080 (« la somme des
parts par nature vaut cent pour cent ») l'exigent — décision de l'agent de livraison à la relecture
1, qui renverse la première rédaction. Les parts des postes, qui ne portent qu'une partie des lignes,
et une valeur isolée — un avancement, la consommation du budget, le taux de charge, le taux de
transformation — ne sont pas des répartitions : quatre décimales et le plancher, sans report.
WF-DAT-0100 n'est pas contredit : il veut des pourcentages conservés exacts, non arrondis *avant* les
calculs ; un quotient, souvent sans écriture décimale finie, ne s'arrondit qu'à la valeur rendue, le
serveur calculant sur les montants exacts. `AmountByKey.share` quitte `Percent` pour `Decimal` : un
quotient calculé, non un pourcentage conservé. Écartés :

- la somme libre, chaque part son propre quotient, que la première rédaction retenait : contraire
  aux Vérif de WF-DEV-0060 et de WF-PTF-0080 ;
- douze décimales ou plus, que #694 proposait : toutes les parts des exemples auraient changé, et
  l'écran, qui montre chaque décimale qu'il reçoit (`formatPercent`) tant que `formatShare` (L51)
  n'a pas pris sa place, les aurait toutes montrées ;
- quatre décimales et la plus petite part, `0.0001`, pour une part non nulle que l'arrondi
  annulerait : l'écran n'aurait pas su distinguer 0,003 % de 0,01 % ;
- le pont du front de L51 officialisé — une part donnée nulle à côté d'un montant non nul dite
  « < 0,01 % » — : le plancher le rend inutile, une part donnée nulle l'étant.

Les indices (`IndexValue`), que le faux back donne aussi à quatre décimales, ne sont pas traités :
#694 ne les nomme pas, et leur zone est classée par le serveur. `wftools.mockstructure.share`
arrondit ainsi chaque rapport des exemples engendrés, et `wftools.mockstructure.partition` les parts
d'une répartition — du devis, du reste à engager, de la structure des coûts du portefeuille — ;
`make mock-data` les réécrit. `tools/tests/test_mocktoday.py` tient la règle, la somme des
répartitions à un et qu'aucune part d'un montant non nul n'est nulle dans les exemples ;
`test_mockdata.py`, la somme des répartitions du devis et du portefeuille.

**Les sous-projets d'un projet clos ont leur exemple** (#673, point 1 ; WF-CYC-0100) :
`subprojects_completed`, les deux sous-projets du témoin terminé (`project_completed`), la
modification indisponible faute de `project_not_terminal`, la suppression faute de
`subproject_not_cited`, `subproject_without_actual_costs`, puis `project_not_terminal`, dans l'ordre
de L42l. Écrit à la main comme `project_completed`, variante qu'il suit, et cité sous
`listSubprojects` après `subprojects`, qui reste le premier. `test_mockproject.py` lui applique la
règle `_listed` d'un projet clos, et vérifie que ce sont les sous-projets du projet en cours, leurs
commandes à part. **Réécrit par US-0702/L3** (#1657) : un projet clos ne liste aucune commande, et
ses sous-projets non plus ; `subprojects_completed` les garde, sans commande, et l'ordre de L42l
reste celui du 409 de `deleteSubproject`. Le point 2 de #683 : `test_mocksettings.py` dit le motif de chaque seuil, `0.`
refusé par la forme (`NUMBER_INVALID`), `00.5` admis.

Le client est régénéré. Le front n'est touché que par le client régénéré et par la valeur attendue
d'un test de `formatShare`, la part du poste n'étant plus nulle ; il adoptera
`subprojects_completed` dans le test d'un projet clos (#673), lira l'échec de la vérification d'une
restauration depuis un fichier et son 404 quand cet écran se construira, et `formatShare` (L51)
pourra retirer la branche du montant : une part donnée nulle l'est.

## La catégorie et le sous-projet de la provision d'un risque, la provision pour risques (EP-14/L42p)

Le contrat suit la spécification révisée par #708 et reprise dans `epic/EP-14` par #710 : #579
(C-257, avec C-261, qui en complète la règle dans le même corps de WF-RIS-0010), C-299 et C-258. Les
points 3 et 5 de #712 — C-273, la suppression d'un sous-projet que portent des lignes de devis de la
révision en cours, et le collage partiellement invalide de WF-IHM-0050 — sont partis dans EP-14/L42q
(#727), coupé de ce lot pour tenir sa taille. Les décisions sont de l'agent de réalisation du lot
(#712), chacune avec sa raison. Le lot ne touche au front que pour compiler sur le client régénéré et
tenir ses catalogues ; l'adoption par les écrans revient à un lot du front.

**Une catégorie de provision pour risques active est un prérequis de la création d'un projet**
(WF-CYC-0120 : « au moins une catégorie de coût active dont la nature est de type provision pour
risques » ; Vérif : « Sur un référentiel dont aucune catégorie de type provision pour risques n'est
active, la création est refusée en nommant ce prérequis. »). `ReferenceReadiness.missing` gagne
`active_provision_category`, entre la catégorie de main-d'œuvre et le rôle — l'ordre de l'exigence,
que l'énumération et les listes suivent désormais —, et le 409 `REFERENCE_INCOMPLETE` de
`createProject` le nomme dans `params.missing_prerequisites` comme les autres. Exemples, chacun en
dernier sous son statut : `reference_readiness_without_provision` et
`project_reference_without_provision` (corrélation 1100), variantes contrefactuelles — PRV-001, seule
catégorie de ce type du témoin, désactivée. Écarté : renommer `active_cost_category` en une valeur
qui dise la main-d'œuvre — la description le dit, et le changement aurait cassé le client pour un
nom ; le libellé « une catégorie de coût active » des catalogues reste au lot du front.

**La règle « dernière nature ou catégorie de provision » de #578 disparaît** (WF-REF-0030, Vérif :
« La désactivation de la dernière catégorie active de type provision pour risques est acceptée ; la
création d'un projet (WF-CYC-0120), la déclaration d'un risque et le retour d'un risque écarté à
l'état identifié (WF-RIS-0010) sont alors refusés. »). Elle remplace la section « La dernière nature
provision et sa dernière catégorie (EP-02/L42g, #578) », gardée pour l'histoire. Les conditions
`cost_type_not_last_provision` et `cost_category_not_last_provision` quittent le catalogue, les
commandes des natures et des catégories, et les descriptions ; la désactivation d'une nature ou
d'une catégorie redevient toujours disponible, et `setCostTypeActivation` et
`setCostCategoryActivation` perdent le 409 qu'elles n'avaient que pour ce cas ; `updateCostType`
nomme `cost_type_unused` seule, `updateCostCategory` `cost_category_unused` puis
`cost_category_unrated`. Les exemples `cost_type_last_provision_refused` et
`cost_category_last_provision_refused` (corrélations 1033 et 1034) sont retirés ; `cost_types`,
`cost_types_with_inactive` et les catégories engendrées (`mockreference`, qui perd
`last_provision`) disent la désactivation de PRV et de PRV-001 disponible. `createCostCategory`,
`updateCostType`, `setCostTypeActivation` et `setCostCategoryActivation` ne changent plus les
commandes d'autres objets et ne disent plus « relit » ; `updateCostCategory` et `setHourlyRate` le
disent encore (#577). Le verrou de l'ensemble des natures et des catégories provision que la section
de #578 demandait à EP-03 tombe avec la règle. Écarté : garder les conditions jusqu'au lot du front,
qui aurait présenté indisponible ce que le Vérif accepte.

*Remplacé en partie par EP-14/L42r : `updateCostType` nomme `cost_type_unused`, puis
`cost_type_unrated`, puis `cost_type_without_role`, et `updateCostCategory` `cost_category_unused`,
puis `cost_category_unrated`, puis `cost_category_without_role`, avec les rôles en cause pour la
dernière (`params.resource_roles`).*

*Remplacé en partie par EP-14/L42s : `setCostCategoryActivation` a de nouveau un 409, la réactivation
d'une catégorie sous une nature désactivée (`cost_type_active`, C-291), et `setCostTypeActivation`
change de nouveau les commandes d'autres objets, les catégories de la nature qu'elle désactive :
elle le dit et rejoint `RELIT`.*

**Le risque désigne la catégorie de sa provision** (WF-RIS-0010 : « La ligne de provision porte la
catégorie que le risque désigne à sa déclaration parmi les catégories actives de type provision pour
risques (WF-REF-0030) ; lorsqu'il n'en existe qu'une, elle est retenue sans être demandée. Tant que le
risque est identifié, cette catégorie peut être changée pour une autre catégorie active de ce
type. »). `RiskWrite.provision_cost_category_id`, facultative : omise, la seule catégorie active de
ce type ; omise quand il y en a plusieurs, 422 `VALUE_REQUIRED` ; inconnue, `UNKNOWN_COST_CATEGORY` ;
désactivée, `INACTIVE_REFERENCE_OBJECT` ; d'une autre nature, `PROVISION_CATEGORY_REQUIRED`, nouveau,
le pendant de `LABOUR_CATEGORY_REQUIRED` — écarté : `PROVISION_CATEGORY_RESERVED`, qui dit le
contraire, une catégorie de provision donnée à une ligne saisie. `Risk` dit la catégorie et le
sous-projet de sa provision par leur identifiant et leur libellé, résolus à la lecture
(`provision_cost_category_id`, `_label`, `provision_subproject_id`, `_label`), comme une ligne de
devis (WF-ARC-0020) ; un risque écarté garde la sienne. Le changement se fait par `updateRisk`, la
valeur omise restant celle du risque, et se dit d'avance par une commande, `update_provision`,
toujours listée après `update` et indisponible, `risk_identified` manquante, pour un risque qui n'est
pas identifié — comme `update_win_probability` pour la probabilité de gain d'un projet (L42i) ;
envoyé malgré elle, le changement est refusé par 409 `STATE_FORBIDS_OPERATION`, la même condition.
Écarté : laisser le front déduire de l'état du risque ce qu'il peut changer, que la conception
d'EP-02 interdit.

**Le retour d'un risque écarté à l'état identifié** suit le même corps (C-261 : « Lorsqu'un risque
écarté redevient identifié, sa ligne de provision reprend la catégorie qu'il désignait si elle est
encore active. Sinon, la catégorie est demandée, comme à la déclaration. ») :
`RiskReviewWrite.provision_cost_category_id`, lue seulement quand la catégorie désignée n'est plus
active, aux refus de la déclaration. Sans aucune catégorie active de ce type, la
déclaration et ce retour sont refusés par 409 `STATE_FORBIDS_OPERATION`,
`params.missing_condition` à `active_provision_category`, nouvelle au catalogue, du même nom que le
prérequis. **Aucune commande ne la liste** : la saisie des risques (`edit_risks`) couvre aussi la
modification, le réexamen et la suppression, qui n'en dépendent pas, et le formulaire de la
déclaration la sait d'avance par les catégories qu'il lit pour proposer le choix, dont il retient
les actives dont la nature est active et de type provision pour risques (`listCostCategories`,
lisible de qui consulte un projet, `cost_type_is_active`, `cost_type_kind`) ; celle d'un risque
écarté, par `provision_cost_category_is_active` (revue 1). `CostCategoryImage.cost_type_is_active`,
résolu à la lecture comme le type de la nature, est ajouté pour cela (revue 2) : écarté, laisser le
formulaire relire les natures, ou ne lire que l'état de la catégorie, qui aurait proposé une
catégorie active sous une nature désactivée que la déclaration refuse. Écartés : la condition
sur `edit_risks`, qui aurait fermé toute la saisie des risques ; une commande `declare_risk` de plus
sur le projet et la révision, qui aurait doublé `edit_risks` pour un cas que la création d'un projet
exclut déjà et qu'une désactivation seule ramène.

*Remplacé en partie par EP-14/L42s : la déclaration a sa commande, `declare_risk`, qui dit d'avance,
après les conditions d'état de la saisie des risques, `at_least_one_task` puis
`active_provision_category` — l'option écartée ici, une structure principale sans tâche n'étant pas
un cas que la création d'un projet exclut —, et
`cost_type_is_active` ne sert plus au formulaire, une catégorie active l'étant toujours sous une
nature active (C-291).*

**Le risque désigne aussi, facultativement, le sous-projet de sa provision** (C-299, WF-RIS-0010 :
« La ligne de provision appartient au sous-projet que le risque désigne, facultativement, à sa
déclaration, et qui peut être changé tant qu'il est identifié ; à défaut, elle compte dans l'ensemble
« hors sous-projet » (WF-RAE-0020). »). `RiskWrite.provision_subproject_id`, nul ou omis à la
déclaration pour une provision hors sous-projet, `null` à la modification pour l'y remettre ; un
sous-projet que le projet n'a pas, 422 `UNKNOWN_SUBPROJECT` ; le changement suit `update_provision`.
Les trois risques du témoin désignent PRV-001 et aucun sous-projet : la ligne de provision de 751 est
déjà hors sous-projet, ce que C-047 supposait. `mockhistory` écrit les quatre champs ; exemples, à
la main : `risk_provision_refused` (corrélation 1102, l'ingénierie électrique et un sous-projet
inconnu), `risk_without_provision_category` (1103, contrefactuel), `risk_provision_frozen` (1104,
753, écarté, dont la provision passerait aux essais).

**Le type « provision » s'appelle « provision pour risques »** (C-258) : la description de
`CostTypeKind`, qui dit aussi qu'une provision saisie et non pondérée relève d'une nature hors
main-d'œuvre, et chaque description du contrat qui nommait une « nature provision » ; les catalogues
du front (`enums.CostTypeKind.provision` : « Provision pour risques », « Provision for risks »).
Écartés : renommer la valeur `provision` de l'énumération, un changement du client et du back sans
gain de sens, le code n'étant pas lu ; renommer la nature PRV du témoin, « Provision », un libellé
saisi, modifiable comme tout libellé (WF-EXP-0020).

**La définition provisoire d'une catégorie active de type provision pour risques** (revue 1).
C-291 — désactiver une nature désactive ses catégories — n'est pas au contrat (#728) : sans lui,
désactiver la dernière nature de type provision pour risques laisserait sa catégorie active, et rien
ne manquerait. Jusqu'à C-291, `active_provision_category` signifie donc « une catégorie active sous
une nature active de type provision pour risques », dans `ReferenceReadiness.missing`, dans
`CommandCondition`, dans les descriptions de `CostTypeCommand` et de `setCostTypeActivation` ; une
catégorie désignée sous une nature désactivée est refusée par `INACTIVE_REFERENCE_OBJECT`. Écarté :
attendre C-291, le contrat affirmant entre-temps un refus que rien ne produit.

*Remplacé par EP-14/L42s : C-291 est au contrat ; une catégorie active l'est toujours sous une nature
active, et la définition provisoire disparaît.*

**Une catégorie inchangée, désactivée depuis, se garde** (revue 1). À la modification d'un risque,
`INACTIVE_REFERENCE_OBJECT` ne vaut sur `/provision_cost_category_id` que si la valeur change la
catégorie, comme le parent d'un nœud ou la catégorie d'un rôle (L42j) : un risque se modifie sans
avoir à changer une catégorie désactivée après sa désignation.

**Le sous-projet d'une ligne de provision est celui que son risque désigne, calculé** (revue 1). La
grille et le collage écrivaient aussi `estimate_line.subproject_id` de la ligne de provision, un
second chemin qui contournait `update_provision` : il quitte les `editable_fields` de la ligne et
rejoint ses champs calculés (`computed_fields`, dépendance `risk`) ; envoyé, il est refusé par 422
`COMPUTED_VALUE`, comme ses grandeurs, et un collage refuse la cellule de même. `nodes_estimate` et
les lectures du nœud 555 sont engendrés en conséquence. Écarté : laisser l'écriture de la ligne
réécrire la désignation du risque, qui contournerait `risk_identified`. Le délai de paiement de la
même ligne, antérieur au lot, est suivi par #733.

**Un sous-projet supprimé ôte sa désignation aux risques non identifiés** (revue 1 ; tranché par
l'auteur le 2026-10-10, décision de l'auteur, #732). Un risque écarté ou survenu peut désigner un
sous-projet sans ligne de provision pour le porter : sa suppression passe cette désignation à nul,
et le risque redevenu identifié porte sa provision hors sous-projet. `deleteSubproject`,
`Risk.provision_subproject_id` et `RiskReviewWrite` le disent. Écarté : une condition « aucun risque
ne le désigne », qui aurait gardé indéfiniment un sous-projet pour un risque écarté.

**Ce que la lecture et la commande disent** (revue 1). `Risk.provision_cost_category_is_active`,
résolu à la lecture — la catégorie et sa nature actives —, dit d'avance qu'un retour à l'état
identifié demandera une catégorie : le front ne compare rien aux listes du référentiel, ce qui suit
la raison même d'`update_provision`. `update_provision` ne nomme que `risk_identified`, pour un risque
survenu comme pour un écarté. Une seule commande pour la catégorie et le sous-projet : ils suivent la
même règle, « tant qu'il est identifié ». Écartés pour C-299 : deux commandes, qui diraient deux fois
la même condition ; un sous-projet porté par la seule ligne de provision, qui disparaît avec la ligne
quand le risque est écarté et ne laisserait rien à reprendre au retour. Les refus de `createRisk` se
jugent dans l'ordre `at_least_one_task` — dont le 409 attend #728 — puis
`active_provision_category`, et ce 409 précède le 422 : sans catégorie active, aucune désignation ne
serait valable. L'annulation d'`updateRisk` rend la catégorie et le sous-projet d'avant ; celle de
`reviewRisk`, la catégorie désignée avant un retour à l'état identifié (WF-IHM-0110).

*Remplacé en partie par EP-14/L42s : le 409 de `at_least_one_task` est décrit, avec son exemple
(`risk_without_task`).*

**Ce qu'une désignation passée à nul fait au risque, et ce que l'annulation ne rend pas** (revue 2 ;
#732). Une désignation passée à nul par la suppression d'un sous-projet est une écriture du risque :
son `lock_version` avance, et son audit nomme l'auteur de la suppression. Toute annulation et tout
rétablissement qui rendraient un sous-projet supprimé depuis — la création, la modification ou la
suppression d'un risque, toute écriture de la grille, la suppression d'une ligne ou d'une tâche et
de ses lignes comprise — sont refusés par 409 `STATE_FORBIDS_OPERATION`,
`params.missing_condition` à `restored_subproject_exists`, nouvelle au catalogue — aucune condition
existante ne disait un objet que l'annulation rendrait —, et ne défont ni ne rétablissent rien
(revue 3 : la règle vaut sur tous les chemins frères, et `redoLastUndo` a son propre 409). Le texte
est le même dans L42q, qui l'écrit aussi dans `UndoResult`. Écartés : rendre le risque hors sous-projet en silence, une annulation qui ne
rendrait pas ce qu'elle annonce ; recréer le sous-projet, que l'annulation d'une saisie de risque ne
peut pas faire. L42q prend la même condition pour une ligne de devis passée par la grille à un
sous-projet supprimé depuis.

**Corrélations** 1100 et 1102 à 1104 — 1101 est à L42q ; la plage des corrélations écrites à la main,
pleine jusqu'à 1099, va désormais jusqu'à 1199 (`mockids`). `tools/tests/test_mockprovision.py` tient
le prérequis, les refus du risque et sa commande ; `test_mockproject.py` l'ordre des prérequis ;
`test_mockhistory.py` la catégorie et le sous-projet de chaque risque contre sa ligne de provision ;
`test_mockcostsettings.py` et `test_mockreference.py` le retrait de #578. Les catalogues reçoivent
`active_provision_category`, `update_provision` et `PROVISION_CATEGORY_REQUIRED`, et perdent les deux
conditions retirées.

**Hors du lot, relevés pour la suite** — ouverts en #728, sous-issue de #712. C-291 — la
désactivation d'une nature désactive ses catégories, et une catégorie ne se réactive que sous une
nature active — n'est pas au contrat : `setCostCategoryActivation` dit encore qu'une catégorie se
réactive sous une nature désactivée. Le résumé de `reference_readiness_incomplete` décrit une
installation neuve sans calendrier par défaut, quand WF-EXP-0020 en crée un et que le Vérif de
WF-CYC-0120 nomme la catégorie de main-d'œuvre et le rôle manquants. La déclaration d'un risque sur
une structure principale sans tâche, refusée « en nommant la condition manquante » (WF-RIS-0010), n'a
pas de 409 décrit à `createRisk`.

## Le sous-projet porté par le devis en cours, le collage partiel (EP-14/L42q)

Les points 3 et 5 de #712, coupés d'EP-14/L42p pour tenir sa taille et réalisés dans ce lot (#727) :
le contrat suit la spécification révisée par #708 — C-273 et le Vérif de WF-IHM-0050, que le critère
d'US-0130 reprend désormais. L42q se fusionne après L42p, dont il prend la plage des corrélations
élargie. Les décisions sont de l'agent de réalisation du lot, chacune avec sa raison. Le lot ne touche
au front que pour compiler sur le client régénéré, tenir ses catalogues et ses tests ; l'adoption par
les écrans revient à un lot du front.

**La suppression d'un sous-projet que portent des lignes de devis de la révision en cours est
refusée** (C-273, décision de l'auteur, voie B ; WF-PRJ-0050 : « Un sous-projet auquel des coûts
réels sont imputés, qu'une révision marquée cite, ou que portent des lignes de devis de la révision
en cours, ne peut pas être supprimé » ; WF-DAT-0080, Vérif : « Celle d'un sous-projet que portent des
lignes de devis de la révision en cours est refusée et nomme ces lignes ; elle aboutit une fois ces
lignes passées hors sous-projet ou à un autre sous-projet. »). `subproject_without_estimate_lines`
rejoint le catalogue et la commande `delete` du sous-projet, **après** `subproject_not_cited` et
`subproject_without_actual_costs`, avant `project_not_terminal` : des conditions qui ne se lèvent pas —
une révision marquée est immuable, un coût imputé le reste, exclu ou non — à celle que lève le passage
des lignes, la raison que L42l donnait. Une ligne de provision dont le risque a désigné le sous-projet
(C-299, EP-14/L42p) compte, comme toute ligne de la révision en cours, dans quelque structure
qu'elle soit. Le 409 de
`deleteSubproject` nomme la première qui manque ; quand c'est celle-ci, il nomme aussi les lignes,
comme le Vérif le demande : `params.estimate_lines`, toutes, chacune par sa structure, son nœud, son
numéro de ligne et son libellé, la structure principale d'abord, sans borne — un sous-projet n'en
porte au plus que les lignes d'une révision, et l'utilisateur doit pouvoir toutes les déplacer
(revue 1). Écartés : un compte de lignes, que
l'utilisateur n'aurait pas pu retrouver ; les lignes dans la lecture du sous-projet, qui aurait
alourdi chaque lecture pour le seul refus ; la condition avant les coûts, qui aurait renvoyé vers des
lignes dont le passage ne suffit pas. Les deux sous-projets du témoin sont portés par des lignes de
la révision en cours, sur toute la structure : `subprojects` et `subproject_updated`, écrits à la
main, listent les trois conditions, les listes dérivées sont engendrées, et `subproject_delete_cited`
dit « la première des trois » ; le sous-projet créé n'en porte aucune ; ceux du projet clos
(`subprojects_completed`, EP-14/L42o), dont la révision en cours reste la 102, listent la nouvelle
condition avant `project_not_terminal` (réécrit par US-0702/L3, #1657 : ces sous-projets ne listent
plus aucune commande, et seul le 409 nomme `project_not_terminal`). Nouvel exemple, en dernier :
`subproject_delete_estimated` (corrélation 1101), contrefactuel — la réception sur site délestée de
sa facture, à laquelle les lignes 10 et 11, « Raccordement des borniers » et « Borniers », auraient
été passées. La description de `deleteSubproject` ne dit plus que la décision de L42l contredit le
Vérif de WF-DAT-0080 : C-256 l'a corrigé.

**Un collage partiellement invalide écrit les lignes valides** (WF-IHM-0050 : « après confirmation,
les lignes valides sont écrites en une seule opération, et les lignes refusées ne le sont pas » ;
Vérif : « Un bloc dont une cellule porte une catégorie inconnue signale cette ligne ; confirmé, il
écrit les autres lignes et non celle-ci ; abandonné, il ne modifie aucune ligne. »). `applyPaste`
rend `PasteApplied` : `NodesWritten` et `rejected`, les refus de l'aperçu, ligne par ligne — la ligne,
la colonne, le motif (`PasteRejection`, extrait de `PastePlan`) —, que la confirmation n'a pas écrits ;
un succès partiel se lit à ce que `rejected` n'est pas vide. Une ligne dont une cellule est refusée
l'est entière. Le plan retient le compteur de la structure lu à l'aperçu, et la confirmation est
refusée par 412 si la structure a changé depuis, quel que soit le compteur envoyé (revue 2) : un
compteur relu entre l'aperçu et la confirmation ne doit pas faire écrire un plan jugé sur une autre
structure. Le référentiel n'a pas de compteur : à la confirmation, les lignes acceptées sont jugées
de nouveau (revue 1), et une ligne devenue invalide — une catégorie ou un rôle désactivés
entre-temps — passe dans `rejected` avec son motif. Toute annulation et tout rétablissement qui
rendraient un sous-projet supprimé depuis — une écriture de la grille, la suppression d'une ligne ou
d'une tâche et de ses lignes comprise, comme une saisie de risque — sont refusés par 409,
`restored_subproject_exists`, la condition de L42p, dans les mêmes mots qu'elle (revues 2 et 3,
#732). Sans aucune ligne valide, rien n'est écrit, le compteur reste, et aucune entrée
d'annulation n'est créée (WF-IHM-0110) : il n'y aurait rien à annuler. `rejected` est exigé,
vide pour un collage entier : `paste_applied`, le premier exemple, garde son scénario et y gagne
`"rejected": []` ; `paste_applied_partial`, engendré par `make mock-data` (`mockwrites`), confirme le
bloc de `paste_plan_unknown_category` — les lignes 28 et 30 écrites, la 29 laissée, son refus redit —,
dont le résumé ne dit plus qu'un collage partiellement invalide ne s'applique pas. Écartés : refuser
la confirmation d'un plan qui porte un refus, la forme d'avant, contraire au Vérif ; se fier au plan
sans juger de nouveau les lignes, le compteur de la structure ne couvrant pas le référentiel, qui
aurait laissé écrire une ligne sur une catégorie désactivée depuis l'aperçu ; `rejected` sur
`NodesWritten`, que toutes les écritures de grille partagent ; un statut 207, que le contrat
n'emploie nulle part.

**Corrélation** 1101 ; la plage des corrélations écrites à la main va jusqu'à 1199 (`mockids`), le
même changement que L42p. `test_mockproject.py` tient la nouvelle condition, son ordre et les lignes
nommées contre la révision en cours ; `test_mockwrites.py` le collage partiel contre le plan. Les
catalogues reçoivent `subproject_without_estimate_lines`.

## Le code d'un rôle, la catégorie d'un rôle gardée, le projet du refus d'un calendrier, la largeur d'une colonne (EP-14/L42r)

Les trois points de #684, que l'auteur a décidé le 2026-10-10 de traiter dans EP-14, les quatre
mineurs de L42j (#691) et le refus de la largeur d'une colonne des préférences de grille (#711). Les
décisions sont de l'agent de réalisation du lot (#759), chacune avec sa raison. Le lot ne touche au
front que pour compiler, tenir ses catalogues et saisir le code d'un rôle ; le reste de l'adoption
revient au lot du front qui suit.

**Un rôle porte un code unique** (WF-REF-0090 : « Un rôle de ressource porte un code unique et un
libellé. » ; Vérif : « La création d'un rôle dont le code existe déjà est refusée. » ; WF-DAT-0090,
qui déclare en base l'unicité du « code de rôle de ressource »). `code`, d'un à vingt caractères
comme celui d'un nœud, est exigé sur `ResourceRoleImage` — donc sur `ResourceRole` et sur l'image
qu'une révision marquée fige —, sur `ResourceRoleWrite` et sur `ResourceRoleUpdate`, et se modifie
comme le code d'un nœud. Il est unique parmi les rôles, désactivés compris. Un code déjà porté est
refusé par 409 `ALREADY_EXISTS` sur `/code`, avec `conflicting_object_id` et
`conflicting_object_label` : la liste des rôles lue sans les désactivés, filtrée ou paginée, peut ne
pas montrer le porteur, que l'utilisateur réactivera plutôt que d'en créer un second, comme pour un
nœud (L42j). Le 422 dit `/code` vide (`VALUE_REQUIRED`) ou trop long (`VALUE_TOO_LONG`).
`listResourceRoles` cherche aussi sur le code, le filtre (`code`, qui contient le texte donné, comme
celui des nœuds) et le trie (`sort_by=code`). Écartés :

- trier par code sans `sort_by`, comme les natures et les catégories : WF-IHM-0060 n'impose aucun
  tri par défaut, et changer celui de la liste des rôles, le libellé, serait une modification du
  contrat qu'aucune exigence ne demande ; le libellé reste ;
- le code du rôle sur les lignes de devis (`resource_role_code`), que #684 et #759 annonçaient avec
  les lignes, `volume/nodes_thousand` et `mockcore` : une ligne nomme son rôle par son identifiant
  et son libellé, comme sa catégorie, sans en porter l'image, et aucun Vérif ne demande le code à la
  ligne ; aucun exemple ne porte non plus d'image figée, `Revision.snapshot` étant nul partout. Les
  lectures et les écritures des rôles sont les seuls exemples touchés.

Les codes du témoin : ING-ELEC, TECH-MES, AUTOM, MONT-CAB, PROG-AUTO, et DESS-ELEC pour le rôle
créé. Exemple `resource_role_code_taken` (corrélation 1110) : AUTOM, le code de l'automaticien,
désactivé, donné au dessinateur électricien à sa création comme au technicien de mise en service à
sa modification, cité sous le 409 de `createResourceRole` et d'`updateResourceRole` ;
`test_mockcostsettings.py` tient que tout exemple d'une valeur prise cité sous une création et une
modification dit l'une et l'autre. La table `UNIQUE` compte dix-sept écritures.

**Une catégorie rattachée à un rôle, ou qui porte des taux, ne quitte pas la main-d'œuvre**
(WF-REF-0040 : « Une catégorie qui porte des taux horaires, ou à laquelle un rôle de ressource est
rattaché, ne quitte pas la main-d'œuvre. » ; WF-REF-0030 : « Ce type ne peut plus être modifié dès
qu'une catégorie rattachée à la nature est employée par une ligne de devis ou de reste à engager,
porte un taux horaire ou est rattachée à un rôle de ressource. » ; Vérif : « La modification du type
est refusée pour une nature dont une catégorie est employée, porte un taux ou est rattachée à un
rôle de ressource. »). `change_kind` d'une nature manque désormais `cost_type_unrated` quand une de
ses catégories porte un taux horaire, et `cost_type_without_role` quand un rôle est rattaché à l'une
d'elles ; `change_cost_type` d'une catégorie manque `cost_category_without_role` quand un rôle lui
est rattaché. Le 409 de `updateCostType` et celui d'`updateCostCategory` nomment la première qui
manque, comme L42g. Les choix :

- deux conditions pour la nature, et non `cost_type_unrated_and_unattached`, que #684 proposait
  aussi : les deux causes se lèvent séparément, comme L42g l'a dit des catégories ;
- l'ordre des exigences — employée, puis un taux, puis un rôle —, qui met d'abord ce qu'aucune
  action ne lève : une ligne d'une révision marquée demeure, un taux se corrige sans se retirer, un
  rôle se rattache à une autre catégorie de main-d'œuvre ;
- un rôle désactivé compte : il garde sa catégorie et se réactive sans qu'elle soit regardée
  (`setResourceRoleActivation`). Écarté : ne compter que les rôles actifs, qui aurait laissé un rôle
  réactivé sur une catégorie hors main-d'œuvre, contre WF-REF-0090 ;
- le refus nomme les rôles : quand `missing_condition` nomme `cost_type_without_role` ou
  `cost_category_without_role`, le 409 porte `params.resource_roles`, tous les rôles en cause,
  actifs ou désactivés, chacun par son identifiant, son code et son libellé (`resource_role_id`,
  `code`, `label`) — la condition se lève en les rattachant à une catégorie de main-d'œuvre hors de
  la catégorie, ou de la nature, refusée, et WF-IHM-0090 veut qu'un refus dont la condition est
  atteignable dise quoi faire (relectures 1 et 2). Le code et le libellé y sont parce que l'écran
  des paramètres de coûts, qu'ouvre `cost_settings.write`, ne lit pas forcément les rôles :
  `listResourceRoles` refuse les désactivés à qui n'a pas la permission des paramètres de
  ressources. Montrer le code et le libellé d'un rôle désactivé à qui ne peut pas les lire suit le
  précédent de `conflicting_object_label`, le libellé de l'objet qui porte une valeur unique, donné
  quand le formulaire ne connaît pas la liste qui le porte (L42i, L42j). Écartés : les seuls
  identifiants (`resource_role_ids`), que la première correction retenait — l'écran des coûts
  n'aurait pas su les nommer ; ne nommer personne et renvoyer à `listResourceRoles` filtré par
  `cost_category_id`, pour la même raison ; `conflicting_object_id`, qui ne nomme qu'un objet quand
  plusieurs rôles peuvent être rattachés.

*Remplacé en partie par EP-14/L42s : l'ordre reste, celui de l'exigence, mais `cost_type_unused` et
`cost_type_unrated` se lèvent en rattachant les catégories en cause à une autre nature du même type,
et le refus les nomme (`params.cost_categories`, #766), comme `cost_type_without_role` se lève en
rattachant ailleurs les rôles qu'il nomme ; la raison « ce qu'aucune action ne lève » tombe.*

Une écriture qui change les commandes d'autres objets le dit (L42g) : `createResourceRole` et
`updateResourceRole`, qui figent la catégorie et sa nature ou libèrent l'ancienne, et
`setHourlyRate`, dont le premier taux fige aussi le type de la nature. Elles rejoignent `RELIT` dans
`test_mockcostsettings.py`. Le refus de `LABOUR_CATEGORY_REQUIRED` pour une catégorie gardée par
`updateResourceRole` n'a plus de cas : la mention de la section de L42j le dit.

Exemples. Les natures écrites à la main (`cost_types`, `cost_types_with_inactive`) donnent à la
main-d'œuvre ses trois conditions. Le premier exemple de `listCostTypes` change donc, parce que la
règle le demande ; `test_mockcostsettings.py` calcule les commandes de chaque nature d'après
l'emploi, les taux et les rôles des exemples. Les catégories engendrées (`cost_categories`, sa page)
ajoutent `cost_category_without_role` à MO-001 et MO-002, les deux catégories des rôles
(`mockreference.attached`). Aucune nature ni catégorie du témoin ne manque une nouvelle condition
sans manquer d'abord une plus ancienne : chaque catégorie de main-d'œuvre porte des taux (§4.6.2),
et les deux catégories des rôles sont employées. Le refus qui nomme les rôles a donc son exemple en
variante contrefactuelle déclarée, sur le précédent de `reference_readiness_without_provision`
(L42p) : `cost_category_role_kind_refused` (corrélation 1113), cité en dernier sous le 409
d'`updateCostCategory`, le premier inchangé — une catégorie de main-d'œuvre inemployée et sans taux,
à laquelle seul l'automaticien, désactivé, est rattaché, passée sous les débours, le refus nommant
AUTOM, « Automaticien » ; elle déclare ses deux écarts au témoin, où aucune catégorie de
main-d'œuvre n'est sans taux et où l'automaticien est rattaché à l'ingénierie électrique, employée
et qui porte des taux. `test_mockcostsettings.py` confronte le code et le libellé à
`resource_roles`. La nature n'a pas d'exemple propre : son refus prend la même forme.

**Le refus d'un calendrier nomme chaque projet par son libellé et son code, sans autre détail**
(WF-PLA-0010 : « La modification d'un calendrier du référentiel qui produirait le même effet est
refusée en nommant les rôles et, pour chaque projet en cause, son libellé et, lorsqu'il est
renseigné, son code, sans autre détail. » ; Vérif : « La modification d'un calendrier qui laisserait
une tâche sans heure dans un projet que le manager ne peut pas consulter est refusée en nommant ce
projet par son libellé et son code ; un projet en chiffrage sans code est nommé par son seul
libellé. » ; décision de l'agent de livraison à la relecture 1, option (a) de #762).
`updateCalendar`, `setDefaultCalendar` et `updateResourceRole` refusent `TASK_WITHOUT_WORKING_HOURS`
par `params.projects` : un élément par projet en cause, `{ project_label, project_code }`, ce
dernier nul pour un projet sans code, sans identifiant de projet ni tâche — WF-ADM-0110 réserve le
détail d'un projet à qui le consulte. Les rôles en cause restent nommés par
`params.resource_role_ids`. Les saisies d'une révision gardent `params.tasks` dans sa forme d'avant
ce lot (`project_id`, `node_id`, `label`), sans `project_label` ni `project_code` : l'auteur d'une
saisie consulte son projet, et WF-PLA-0010 y demande de nommer « les rôles et la tâche en cause ».
Cette décision remplace la raison « un code, une forme » de la première rédaction, qui donnait à
chaque tâche le libellé et le code de son projet et gardait son nœud et son libellé, contre « sans
autre détail ». Écartée : l'option (b) de #762, garder `params.tasks` et passer à nul le nœud et le
libellé d'une tâche d'un projet que l'appelant ne consulte pas — la forme du refus aurait dépendu de
ce que l'appelant consulte, et un même refus se serait lu autrement d'une session à l'autre.

Exemple `calendar_update_without_hours` (corrélation 1112), cité sous le 422 d'`updateCalendar`
après `hours_out_of_range`, qui reste le premier : la semaine de quatre jours, le calendrier du
monteur câbleur, vidée de ses heures. Ce rôle travaille seul sur les cent trois tâches de câblage de
la structure principale du témoin, qui n'auraient plus aucune heure travaillée, et aucun projet
engendré ne l'emploie : le refus nomme le monteur câbleur et « Modernisation du poste de commande »,
PRJ-001. La première rédaction disait à tort que le témoin n'offrait pas un tel refus (relecture 1),
puis vidait la semaine standard, ce qui mettait aussi en cause les trente offres engendrées, en
chiffrage avec un devis courant, dont la main-d'œuvre est celle de l'ingénieur électricien et du
technicien de mise en service (relecture 3, option (b) de l'agent de livraison).

`test_mockresourcesettings.py` le tient. Les rôles en cause se calculent tâche par tâche sur la
structure principale du témoin (`nodes`, `volume/nodes_thousand`) — la seule que les exemples
donnent, les devis propres des risques 204 et 206 n'en ayant pas — : l'union des rôles des tâches
qui portent au moins un rôle de la semaine vidée. Les projets se calculent sur l'installation
entière : ceux de `projects` qui ont une révision en cours, et ceux de `volume/portfolio_projects`
qui en ont une et emploient l'un de ces rôles d'après `mockportfolio.role_shares`. L'univers ne dit
pas quels projets engendrés en cours ont une révision en cours ; le test suppose que ce sont ceux
dont la liste montre un devis courant, les trente offres, et vérifie qu'aucun projet engendré
n'emploie le monteur câbleur, si bien que la supposition ne change rien. Il tient aussi qu'aucune
tâche ni aucun identifiant de projet n'est nommé, et le texte de `Problem.params` et des trois 422.

Les refus de calendrier gardent `params.resource_role_ids`, sans code ni libellé, à la différence
des refus d'une nature ou d'une catégorie (relecture 3) : la session de `updateCalendar`,
`setDefaultCalendar` et `updateResourceRole` peut lire tous les rôles, désactivés compris, la
permission des paramètres de ressources ouvrant `include_inactive` ; le front devra relire toutes
les pages de `listResourceRoles` avec `include_inactive` pour les nommer ; une saisie d'une révision
connaît le libellé de ses rôles par ses lignes (`resource_role_label`). Le compte rendu d'un import,
qui ne porte que les identifiants, est suivi par #768. `Problem.params` le dit, et
`test_mockresourcesettings.py` en tient le texte.

**La largeur d'une colonne a son refus** (#711). `GridPreferences.column_widths` publie `minimum:
20`, et `updateMyPreferences` ne déclarait aucun 422. Il déclare désormais `VALIDATION_FAILED`,
`/grids/<grille>/column_widths/<colonne>` par `VALUE_OUT_OF_RANGE`, `fields[].params.minimum` à
`20`, comme toute borne d'une écriture (L42o). Écarté : le 400 partagé, réservé à une requête mal
formée, quand la largeur est bien formée et seulement trop petite. Exemple
`preferences_column_width_out_of_range` (corrélation 1111), seul sous ce 422 : la colonne du libellé
de la grille de devis réduite à 12 points.

`test_mockbounds.py` dérive désormais les corps de tous les `requestBody` du contrat, soixante-huit,
en suivant les schémas qu'ils citent — propriétés, dictionnaires, listes, compositions, et les
éléments d'une liste écrits `- { $ref: … }`. Chaque borne que le schéma publie en `minimum` ou en
`maximum` — ou en borne exclusive, entière ou décimale —, hors `lock_version`, doit avoir son refus
à son pointeur, sous le 422 de l'opération, avec son exemple. Un garde-fou tient qu'aucune ligne du
contrat hors d'un texte plié ne cite un schéma ou une borne sans que la lecture la place. Les bornes
de L42m, la rétention et le délai entre deux revues, entrent dans sa table, et tous les exemples qui
portent des largeurs de colonnes, la session comprise, restent au-dessus de la plus petite.
Écartés : lire le contrat assemblé (`make build-openapi`), que les tests ne lisent pas, un
assemblage laissé sur le disque pouvant être périmé ; une bibliothèque YAML, dont les outils ne
dépendent pas.

**Les mineurs de L42j** (#691) :

1. la note de L42j dit la création sous un nœud désactivé, refusée comme le déplacement ;
2. l'ordre de construction de la conception nomme L43g après L42j ;
3. `test_mockresourcesettings.py` tient qu'`org_node_updated` reste le premier exemple du 200
   d'`updateOrgNode`, et que le nœud renommé est le nœud lu, hors `label`, `lock_version` et
   `audit.updated_*` ;
4. deux lignes trop longues de `paths/reference.yaml` sont coupées, dans la description de
   `setDefaultCalendar` et dans le 422 d'`updateResourceRole`.

**Corrélations** 1110 à 1113. Le front reçoit les phrases des trois conditions
(`enums.CommandCondition`), et compile sur le client régénéré. Le formulaire du rôle saisit le code,
exigé, premier de ses champs comme celui d'un nœud : le faux back valide les corps d'après le
contrat, et une création sans code y était refusée, ce que le parcours de bout en bout des rôles a
montré. Écartée : envoyer le code du rôle à la modification et aucun à la création, le minimum que
le lot visait d'abord. Le code dans la grille — colonne, recherche, filtre, tri —, le code pris
éprouvé au champ, et #714 point 1 reviennent au lot du front qui suit, avec les rôles que nomme le
refus d'une nature ou d'une catégorie (`params.resource_roles`) et les projets que nomme le refus
d'un calendrier (`params.projects`) ; le formulaire d'une catégorie dit déjà la troisième condition
de MO-001 (`cost-form.dom.test.tsx`).

## La part d'un total nul (EP-14/L55, tranchée le 2026-10-29 par #1633, G-02)

Constat #718 de la relecture 2 de L42o : `wftools.mockstructure.partition` levait sur une
répartition sans montant (`max` d'une suite vide) et sur un total nul (une division par zéro) — un
devis encore sans ligne, un reste à engager entièrement nul, un portefeuille sans projet en cours.
EP-14/L55 l'a fait ne plus lever : une répartition sans montant n'a aucune part, et chaque montant
d'un total nul n'en a pas non plus (`None`). La question de ce que le contrat donne alors restait
ouverte (#774, L42t) ; le générateur omettait la part, en attendant.

**Décision de l'auteur du 2026-10-29 (#1633, G-02, option A) : la part d'un total nul est non
calculable.** WF-IND-0010 veut qu'une valeur dont le dénominateur est nul soit présentée non
calculable, jamais comme zéro ni comme l'infini, et la décision « Une enveloppe `Computable` pour ce
qui peut ne pas se calculer », en tête de ce fichier, en fait une règle du contrat. `share` est
exigé dans `AmountByKey` et dans `ComputableAmountByKey` ; `AmountByKey.share` passe de `Decimal` à
`Computable`, comme l'était déjà celle de `ComputableAmountByKey` ; un total nul donne
`{ is_computable: false, value: null, reason: "no_total" }`. `no_total` s'ajoute à
`NotComputableReason` : aucun motif existant ne disait « total nul » — `no_reference_budget` et
`no_budgeted_amount` nomment des assiettes précises, non la somme d'une répartition. Écartés : une
part nulle, lue comme « rien » ; `null`, qui n'a pas de motif ; une part facultative, que le client
engendré verrait `?`.

**Ce que fait l'outil.** `mockstructure.part_share` donne toute part : `Computable` calculable, ou
non calculable de motif `no_total` quand `partition` ou `share` n'en trouve pas ; le devis, le reste
à engager et la structure des coûts du portefeuille l'emploient, et un lot sans tâche garde
`work_package_without_task`, que montre `estimate_indicators_work_package_without_task` depuis
US-0660/L2. Aucun exemple n'a de total nul ; ceux de `AmountByKey` (le reste à
engager, la structure des coûts) prennent la forme `Computable`, engendrés par `make mock-data`.
`tools/tests/test_mocktoday.py` tient la part d'un total nul sur l'outil, sur le devis et le reste à
engager d'une structure sans ligne, et sur la structure des coûts d'un portefeuille sans projet en
cours, et que toute part de tout exemple est un `Computable`.

## Le squelette, le rattachement, les chronologies et les nœuds retenus d'un lotissement filtré (EP-14/L42k)

La partie L42k de #507 (#614), au périmètre revu le 2026-10-10 : le squelette et le rattachement
(#586), les chronologies, les nœuds retenus d'un lotissement filtré (#574) ; la catégorie de la
provision (#579), qu'elle portait au cadrage, est sortie, réalisée par EP-14/L42p. Le contrat suit
la spécification à jour depuis #708. Les décisions sont de l'agent de réalisation du lot, chacune
avec sa raison, et celles de la relecture 1 de l'agent de livraison, dites comme telles. Le lot ne
touche au front que pour compiler sur le client régénéré, tenir ses catalogues et ses tests ;
l'adoption revient à EP-14/L44c — la grille du lotissement et les chronologies — et EP-14/L44d — le
squelette et la colonne du rattachement. Ni #574 ni #586 ne se ferment ici : la troisième Vérif
de #574, le total des seuls retenus à l'écran, revient à L44c, et #586 garde ce que #771 reprend.

**La révision liste le squelette parmi ses commandes** (`RevisionCommand.generate_skeleton` ;
WF-PRJ-0030 : « La génération n'est proposée que sur la structure principale (WF-PLA-0170), et
seulement lorsqu'elle ne comporte aucune tâche » ; Vérif : « Elle n'est plus proposée dès que la
structure principale comporte une tâche, et ne l'est jamais sur un différentiel ni sur le devis
propre d'un risque. »). Une saisie du planning, juste après `edit_planning`, gardée par la même
permission, `planning.write`. La condition nouvelle, `main_structure_without_tasks`, manque dès que
la structure principale de la révision comporte une tâche ; elle vient la première, la condition
propre d'abord, puis celles de toute saisie de la révision en cours — `no_background_task_running`
pendant un marquage, un import, le traitement d'une survenance de risque ou une fusion, comme
`merge_structure` après `unmerged_amendment_exists` ; sur une révision marquée, la commande ne
manque que de `revision_draft`, comme `merge_structure` (hors de la dernière révision marquée d'un
projet sans révision en cours, depuis EP-16/US-0640/L3). Le 409 de `generatePlanningSkeleton` est
`STATE_FORBIDS_OPERATION`, `params.missing_condition` nommant la première qui manque ; une révision
marquée ou un projet terminal restent des 403, comme toute saisie. *Remplacé par US-0702/L1
(#1610), sur la décision de l'auteur du 2026-10-28 (D-05, J-01, J-02) : une révision marquée —
toute révision d'un projet terminal l'est — refuse le squelette par 409 `STATE_FORBIDS_OPERATION`,
`revision_draft`, la seule condition que `generate_skeleton` nomme alors, comme toute saisie
(`skeleton_marked_refused`) ; plus aucun état n'est un 403. La phrase est gardée pour l'histoire.*
Ni différentiel ni devis propre
d'un risque : la commande est de la révision, et l'opération, qui ne nomme aucune structure,
engendre sur la principale. Les révisions des huit exemples écrits à la main qui listent
`edit_planning` listent la commande : indisponible dans les sept qui portent les tâches du témoin,
disponible dans `revision_without_tasks`, sans tâche. Exemple `skeleton_structure_not_empty`, sous
le 409 qui n'en avait aucun (corrélation 1132). Écartés : une commande absente dès la première
tâche, que « n'est plus proposée » permettait de lire, quand une commande indisponible dit pourquoi
(WF-IHM-0090) et que le cadrage l'a voulue indisponible ; la commande sur la structure
(`CostStructure`), que l'écran du planning ne lit pas pour offrir le squelette et que l'opération ne
vise pas ; la permission du paramétrage du projet (`update`, `project_settings.write`), réservée aux
chefs de projet (WF-PRJ-0060), au motif que le squelette naît du lotissement — il écrit des tâches
dans le planning de la révision, comme une saisie de la grille, et la conception d'EP-14 l'offre
dans la grille de planning vide, à qui peut y saisir (relecture 1).

**L'état où le squelette est proposé a ses exemples** (relecture 1) : `revision_without_tasks`
(`getRevision`), la révision ouverte aujourd'hui sur le projet créé à 14 h 05, « Rénovation du poste
de livraison » (révision 103), `generate_skeleton` disponible, ses autres commandes celles de la
révision courante du témoin ; `structures_without_tasks` (`listCostStructures`), sa structure
principale (207), son compteur à 0 ; `nodes_empty` (`listNodes`), sa lecture, sans nœud, des totaux
nuls, engendrée par `make mock-data` (`mockcore.whole` d'une structure vide, relecture 2) ; et
`project_revision_opened` (`getProject`, relecture 2), le projet créé, passé en Chiffrage, qui porte
cette révision en cours (WF-CYC-0020). Chacun vient en dernier sous son statut ;
`test_mockbreakdown.py` tient que la commande n'est disponible que là où la lecture de la même
structure est vide, et que le squelette engendré y porte le compteur lu plus un.

**Le squelette rend ce que rend une écriture de grille** (`NodesWritten` ; convention du README : «
Toute écriture de grille — […] création […] — rend `NodesWritten` »). La réponse 201 rendait un
tableau de nœuds : la grille vide qui se remplit (L44d) n'aurait eu ni les totaux ni le compteur de
la structure, qu'exige la saisie suivante (WF-IHM-0110), sans relire toute la structure. Les tâches
créées sont dans `nodes`, dans l'ordre du plan ; aucun ancêtre hors d'elles, aucune tâche redatée —
`NodesWritten.ancestors` le dit désormais : les ancêtres hors des nœuds écrits. Écarté : garder le
tableau et relire `listNodes` après chaque génération, une lecture de plus pour ce que l'écriture
sait. Exemple `skeleton_generated`, écrit à la main, sur la révision 103 et le lotissement par
défaut du projet créé (`work_breakdown_default`) — « Sur le lotissement par défaut, la génération
produit une récapitulative de poste, une récapitulative de lot sans feuille, et leurs deux jalons de
fin » (Vérif de WF-PRJ-0030), les récapitulatives rattachées au poste et au lot, le jalon du poste
succédant à celui du lot, sur les nœuds 571 à 574 et leurs lignées 671 à 674. Les jalons sont datés
comme le cœur, par `mockcalendar.follow` (relecture 1) : celui du lot à la première heure de la
structure, le 3 juin ; celui du poste, que la liaison de fin à début lit comme une fin, à la fin de
la journée de travail du 2 juin (WF-PLA-0050) ; chaque récapitulative couvre ses subordonnées
(WF-PLA-0040).

**Le lotissement par défaut porte le libellé du projet** (WF-PRJ-0020 : « en son absence, le
lotissement vaut un poste et un lot qui portent le libellé du projet, sans livrable » ; relecture
1). `getWorkBreakdown`, `WorkBreakdown` et l'exemple `work_breakdown_default` le disent, désormais
celui du projet créé aujourd'hui, « Rénovation du poste de livraison »
(`mockwitness.CREATED_PROJECT`) ; ses libellés « Commande » et « Lot unique », que la spécification
ne nommait pas, disparaissent, et le squelette engendré en suit le libellé, ses jalons « Fin de «
Rénovation du poste de livraison » ».

**`setWorkBreakdown` ne fait forger aucun identifiant au client** (WF-DAT-0060 ; décision de l'agent
de livraison à la relecture 1). L'écriture entière ne pouvait rien créer sans un identifiant inventé
par le client, que le README refuse. Dans l'écriture, l'identifiant d'un poste, d'un lot ou d'un
livrable est facultatif (`OrderItem`, `WorkPackage`, `Deliverable`) : absent, l'élément est nouveau,
le serveur engendre son identifiant, et la réponse le porte ; présent, c'est l'élément que le
lotissement lu porte, renommé ou rangé ailleurs ; un identifiant que le lotissement lu n'a pas —
inconnu, d'un élément d'une autre nature, ou d'un élément marqué supprimé (WF-DAT-0080) — est refusé
par 422 `UNKNOWN_WORK_BREAKDOWN_ITEM` sur son champ. Écartés : un identifiant engendré par le
client, contraire à WF-DAT-0060 ; des opérations par élément — créer, renommer, supprimer —, que la
conception d'EP-14 a écartées pour l'écriture entière ; une clé provisoire du client pour retrouver
dans la réponse l'élément créé, quand l'ordre saisi, que la réponse garde, le désigne déjà.
L'exemple de la requête, `work_breakdown_entered`, est la lecture entière du témoin, ses marques
laissées, le lot « Mise en service sur site » et son livrable ajoutés sans identifiant ; la réponse,
`work_breakdown_saved`, les rend avec 716 et 717. Sous le 422, `work_breakdown_label_required`
(corrélation 1134), le premier, que prism sert à une saisie invalide, refuse cette saisie quand le
lot ajouté n'a pas de libellé, `work_breakdown_unknown_item` (corrélation 1133) quand il porte
l'identifiant 713, celui du livrable (relecture 2), et `work_breakdown_duplicate_item` (corrélation
1135) quand il porte 712, celui d'« Armoires », que la saisie porte déjà (relecture 3). Tous sont
engendrés par `make mock-data` (`mocklists`, `breakdown_refusal` jugeant la saisie contre la lecture
entière) ; `test_mocklists.py` rejoue l'ajout depuis la lecture entière, affirme la liste littérale
des champs de chaque refus, l'indice du lot ajouté tiré de la lecture, et deux identifiants d'une
autre nature refusés comme inconnus — un poste envoyé pour un lot, un lot pour un livrable. **Un
identifiant envoyé deux fois est refusé** (décision de l'agent de livraison à la relecture 3) :
chaque occurrence après la première, par 422 `DUPLICATE_WORK_BREAKDOWN_ITEM` sur `/…/<nature>_id`,
code nouveau. Écartés : `UNKNOWN_WORK_BREAKDOWN_ITEM`, l'identifiant étant connu, qui ne dirait pas
la vraie cause (défaut n° 10 du guide) ; « le dernier gagne », qui supprimerait sans un mot
l'occurrence précédente et ce qu'elle porte ; fusionner les livrables des deux occurrences, une
écriture que personne n'a saisie. Le texte du front pour `UNKNOWN_WORK_BREAKDOWN_ITEM` devient
générique — un élément qui ne fait pas partie du lotissement lu, inconnu, d'une autre nature ou
supprimé —, le code servant désormais à `setWorkBreakdown` comme au rattachement.

**`setWorkBreakdown` rend sa lecture** (relecture 1) : `WorkBreakdownReading`, entière, chaque
élément retenu, avec son compteur suivant, jamais nul, comme `setContributors` rend sa lecture ; la
décision d'EP-02/L42f, qui lui faisait rendre `WorkBreakdown`, est remplacée, une mention le disant
à sa place. Son 422 déclare chaque champ refusé : le compteur nul d'une lecture filtrée
(EP-02/L42f), un libellé vide ou trop long — `VALUE_REQUIRED` ou `VALUE_TOO_LONG` sur
`/order_items/<i>/label`, `/order_items/<i>/work_packages/<j>/label` ou celui d'un livrable, comme
`createTimeline` —, un identifiant que le lotissement lu n'a pas.

**Le rattachement d'un poste ou d'un lot déjà porté nomme la tâche qui le porte, par son nœud et son
libellé** (`WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED` ; WF-PLA-0170 : « un poste ou un lot n'y est porté
que par une tâche à la fois » ; Vérif : « Le rattachement d'une tâche à un lot déjà porté par une
autre est refusé, comme celui d'une même tâche à un poste et à un lot. »). `fields[].params` porte
`conflicting_object_id` et `conflicting_object_label`, les paramètres de toute valeur déjà portée
quand le formulaire ne connaît pas la liste qui la porte : la grille de planning, cherchée ou
filtrée — par sous-arbre, par poste, par chronologie —, peut ne pas lire la tâche, que la cellule
doit nommer (conception d'EP-14, L44d). Ils remplacent `attached_node_id` (EP-02/L29), qui n'en
donnait que le nœud ; aucun écran ne le lisait. La convention du README nomme cette exception : la
même paire sous un 422. Écartés : garder `attached_node_id` et lui adjoindre un libellé, deux noms
pour un même rôle ; un 409 `ALREADY_EXISTS`, quand les autres refus du rattachement sont des motifs
par champ du même 422 et qu'une cellule n'attend qu'une enveloppe. La tâche rattachée à la fois à un
poste et à un lot — « jamais aux deux » — est refusée par `WORK_BREAKDOWN_ITEMS_EXCLUSIVE`, sans
paramètre, la cellule connaissant la tâche qu'elle écrit ; envoyés tous deux non nuls, chacun est
refusé à son champ. `fields` porte une entrée par motif qui s'applique :
`WORK_BREAKDOWN_ITEMS_EXCLUSIVE` et `WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED` sont rendus ensemble
quand l'un et l'autre s'appliquent (relecture 1). Exemples, en dernier sous le 422
d'`updateTaskFacet` : `task_attach_refused`, le premier, garde son scénario et nomme le « Poste de
commande » par ses deux paramètres ; `task_attach_exclusive` (corrélation 1130), le lot « Armoires »
envoyé à la récapitulative qui porte déjà son poste.

**Le rattachement n'existe que dans la structure principale** (#586, point 1 ; WF-PLA-0170 : « Le
rattachement n'existe que dans la structure principale […]. Les structures différentielles et les
devis propres des risques n'en portent pas »). Une tâche d'un différentiel ou du devis propre d'un
risque ne nomme ni `task.order_item_id` ni `task.work_package_id` parmi ses champs
(`editable_fields`) et les porte nuls ; une écriture qui en pose un — `updateTaskFacet`,
`createNode` — est refusée par 422, sur le champ, motif nouveau
`WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY`, `null` restant accepté ; un collage refuse la cellule de la
colonne `work_breakdown` par le même motif (`PasteRejection`, relecture 1). Écartés :
`COMPUTED_VALUE`, le rattachement n'étant pas calculé, et `UNKNOWN_WORK_BREAKDOWN_ITEM`, qui dirait
le poste inconnu et non la vraie cause (défaut n° 10 du guide). Exemple
`task_attach_main_structure_only` (corrélation 1131). La restriction remplace « Toute tâche porte
son rattachement » d'EP-02/L30, une mention le disant à sa place.

**Un lot rangé sous un autre poste retire le rattachement de sa tâche, sans refus** (#586, point 3 ;
WF-PLA-0170 : « Le déplacement d'un lot sous un autre poste retire de même le rattachement de sa
tâche lorsqu'elle n'est pas dans le sous-arbre de la tâche de ce poste. »). `setWorkBreakdown` ne
refuse plus par `WORK_PACKAGE_OUTSIDE_ORDER_ITEM` : la saisie aboutit, et la tâche du lot, dans la
révision en cours, ne porte plus le lot ; les révisions marquées le conservent. La décision de
l'auteur à la revue d'EP-02/L30, qui refusait, précédait la spécification acceptée le 2026-10-09 ;
elle est remplacée, une mention le disant à sa place. `params.work_package_id` disparaît avec le
refus. Écarté : nommer dans la réponse la tâche qui perd son lot, que rien n'exige — la réponse est
le lotissement lu, et la grille de planning relue montre la tâche sans rattachement ; la
confirmation de L44c le dit d'avance pour une suppression (conception d'EP-14). Ce que l'écriture
fait pendant un traitement de fond, et les compteurs qu'elle avance, sont ouverts en #775.

*Remplacé en partie par EP-14/L42s : la saisie attend la fin d'un traitement de fond
(`update_work_breakdown`, `no_background_task_running`), et dit les compteurs qu'elle avance (#775).*

*Remplacé en partie par US-0450/L1 : c'est un poste rangé sous un autre lot qui retire le
rattachement de sa tâche, hors du sous-arbre de la tâche de ce lot, section « Le lotissement en
lots, postes et livrables ».*

**Une fusion qui sortirait la tâche d'un lot du sous-arbre de celle de son poste échoue en nommant
les tâches** (#586, point 2 ; WF-PLA-0170 : « Une fusion qui déplacerait la tâche d'un lot hors du
sous-arbre de la tâche de son poste est refusée en nommant la tâche » ; WF-IHM-0080 : « l'échec
nomme ce qui a échoué »). Sur le modèle de `TASK_WITHOUT_WORKING_HOURS`, la tâche de fond de
`mergeCostStructure` finit en échec sans rien fusionner, `problem.code` à
`WORK_PACKAGE_OUTSIDE_ORDER_ITEM`, `params.order_item_task` et `work_package_tasks` nommant la tâche
du poste et celles des lots, chacune par son nœud et son libellé (relecture 1). Écartés : le nœud
seul, que l'écran d'une tâche de fond, qui ne lit pas la structure, n'aurait pas pu nommer ; un
refus synchrone à la demande de fusion, que la fusion, confiée au worker (WF-ARC-0090), ne sait
qu'en fusionnant — le compte rendu préalable de la fusion (WF-REV-0050 : « Avant application, la
fusion présente un compte rendu : […] et motifs de refus »), que le contrat n'a pas, le dira avant
l'application, et il est ouvert en #771. Exemple `task_merge_outside_order_item`
(`getBackgroundTask`, tâche de fond 939), une variante déclarée : « Câblage des armoires » porterait
le lot « Armoires » sous « Poste de commande ». Le même manque pour `moveNodes`, antérieur au lot,
est ouvert en #775.

*Remplacé en partie par EP-14/L42s : le compte rendu préalable de la fusion existe
(`getStructureMergeReport`, #771), et le refus de `moveNodes` nomme les tâches de même (#775).*

*Remplacé en partie par US-0450/L1 : la fusion échoue par `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, qui
nomme la tâche du lot et celles des postes (`work_package_task`, `order_item_tasks`), exemple
`task_merge_outside_work_package`, section « Le lotissement en lots, postes et livrables ».*

**Le compte rendu d'un import nomme le poste ou le lot qui perd sa tâche** (#586, point 4 ;
WF-INTF-0040 : « La suppression d'une tâche rattachée est appliquée, et le compte rendu nomme le
poste ou le lot qui perd sa tâche. »). `ImportDifference.work_breakdown_label`, nullable et
facultatif, porte son libellé sur le retrait d'une tâche rattachée, comme la facette de la tâche le
porte ; aucun exemple du témoin ne retire une tâche rattachée. Écarté : l'identifiant du poste ou du
lot, que l'écran du compte rendu devrait résoudre en lisant le lotissement. Le point voisin du
constat — un fichier qui sortirait la tâche d'un lot du sous-arbre de son poste « est rejeté au
compte rendu, qui nomme les deux tâches, comme un planning qui dépasse l'horizon » (WF-INTF-0040) —
demande de dire qu'un compte rendu n'est pas applicable, ce que le contrat ne dit pas non plus de
l'horizon (WF-PLA-0150) ; il est ouvert en #771, avec le point 5 de #586,
`EstimateIndicators.by_order_item` face à WF-DEV-0060 (« un poste sans tâche rattachée est présenté
sans total »), que ni L44c ni L44d ne consomme.

*Remplacé en partie par EP-14/L42s : le fichier qui sortirait la tâche d'un lot du sous-arbre de son
poste, ou dépasserait l'horizon, est rejeté entier (`ImportReport.refusals`), et le poste sans tâche
rattachée est présenté sans total (#771).*

*Remplacé en partie par US-0450/L1 : c'est la tâche d'un poste qui ne sort pas du sous-arbre de
celle de son lot, et le total est celui des lots (`by_work_package`), section « Le lotissement en
lots, postes et livrables ».*

**Le projet liste les chronologies parmi ses commandes** (`ProjectCommand.manage_timelines` ;
WF-PLA-0140 : « Un projet peut porter plusieurs chronologies. Chacune porte un nom, conserve la
liste des tâches et des jalons qui y sont inscrits, peut être supprimée, et peut être exportée au
format PNG. »). Une commande pour créer et supprimer, après `manage_contributors`, gardée par
`planning.write` — les chronologies sont une vue du planning (FBS-4.3.1) —, non réservée aux chefs
de projet, indisponible sur un projet terminal (`project_not_terminal`, WF-CYC-0100 ; **réécrit par
US-0702/L3**, #1657 : un projet terminal ne la liste plus, et seul le 409 de l'appel direct nomme
`project_not_terminal`). Écartés : deux
commandes, créer et supprimer, quand un seul écran les offre sous la même permission et les mêmes
conditions, comme `manage_contributors` ; des commandes sur chaque chronologie, qu'aucune condition
propre ne distinguerait ; la seule permission de la session, contraire à la règle d'EP-02 qu'un
objet du projet liste ses commandes (conception d'EP-14). Les projets des sept exemples écrits à la
main que lit une session qui porte `planning.write` listent la commande ; les listes dérivées sont
engendrées.

**`deleteTimeline` reste un 204 sans 409** (WF-DAT-0080 : « Un livrable ou une chronologie se
supprime physiquement. »). Le cadrage disait qu'une chronologie citée par une révision marquée
serait marquée supprimée ; la spécification à jour depuis #708 la supprime physiquement, et la
conclusion ne change pas : rien ne la refuse. La conception d'EP-14 est corrigée de même. Un projet
terminal reste un 403, comme toute écriture. *Remplacé par US-0702/L1 (#1610), sur la décision de
l'auteur du 2026-10-28 (D-05, J-01, J-02) : un projet terminal refuse la création et la suppression
d'une chronologie par 409 `STATE_FORBIDS_OPERATION`, `project_not_terminal`, comme
`manage_timelines` le dit d'avance et comme toute autre écriture du projet
(`timeline_create_terminal`, `timeline_delete_terminal`) ; la suppression n'a pas d'autre 409. La
phrase est gardée pour l'histoire. **Réécrit par US-0702/L3** (#1657) : `manage_timelines` ne dit
plus rien d'avance sur un projet terminal, qui ne liste aucune commande ; le 409 reste, pour
l'appel direct.* `createTimeline` déclare son 422 — un nom vide ou trop
long, `VALUE_REQUIRED` ou `VALUE_TOO_LONG` sur `/label` — et dit le nom non unique, la spécification
ne l'exigeant pas. Écarté : un nom unique dans le projet, refusé par 409 `ALREADY_EXISTS`, que
WF-PLA-0140 ne demande pas et qui empêcherait deux chronologies du même nom pour deux publics, un
comité et un client par exemple. Exemple de succès `timeline_created`, engendré par `make mock-data`
(`mockdata`) : « Réunion de chantier », chronologie 1002, sans inscription.

**Chaque élément d'une lecture du lotissement dit s'il est retenu** (#574 ; WF-IHM-0130 : « Toute
table se filtre sur chacune de ses colonnes, et le filtre s'applique aux totaux qu'elle présente » ;
WF-IHM-0060 : « dans une grille arborescente, le filtre laisse visibles les parents des lignes
retenues »). `is_match`, exigé sur chaque poste, lot et livrable de `WorkBreakdownReading` : vrai
quand les filtres le retiennent, et toujours sans filtre ; faux quand il n'est rendu que parce qu'il
contient un élément retenu. La grille ne compte que les retenus : `work_breakdown_work_packages`
rend le poste marqué faux, et la ligne des totaux dira « 1 lot », non « 1 poste ». Un livrable ne
contient rien et n'est rendu que retenu : sa marque, toujours vraie, garde une même lecture de
chaque ligne. La lecture a ses éléments (`OrderItemReading`, `WorkPackageReading`,
`DeliverableReading`), et l'écriture garde les siens : la marque n'entre pas dans
`setWorkBreakdown`. Écartés : la liste des identifiants retenus au niveau de la lecture, l'autre
proposition du constat, que la grille aurait dû croiser avec l'arbre ; des comptes par nature, qui
auraient servi la ligne des totaux sans marquer les lignes de contexte ; la marque sur les éléments
partagés avec l'écriture, qu'un client aurait renvoyée ; le nom `matched` du constat, le contrat
nommant ses booléens `is_…`. Les quatre lectures engendrées du lotissement portent la marque.

*Remplacé en partie par US-0450/L1 : `work_breakdown_order_items`, qui remplace
`work_breakdown_work_packages`, rend le lot marqué faux, et la ligne des totaux dit « 1 poste » ;
chaque lot et chaque poste lus portent aussi `attached_task`, section « Le lotissement en lots,
postes et livrables ».*

**Identifiants et corrélations** : 1130 à 1135 ; la tâche de fond 939 ; la révision 103 et sa
structure 207, réemployées par `revision_without_tasks`, `structures_without_tasks`, `nodes_empty`,
`skeleton_generated` et `project_revision_opened`, qui décrivent la même révision ; les nœuds 571 à
574 et leurs lignées ; le lot 716 et son livrable 717 ; la chronologie 1002. `test_mockbreakdown.py`
tient la commande du squelette, où elle est offerte, son refus et l'exemple du lotissement par
défaut, ses dates comprises, les refus du rattachement, la tâche qu'ils nomment et la fusion qui
échoue, le projet qui porte la révision sans tâche, la commande des chronologies et la chronologie
créée ; `test_mocklists.py`, la marque des éléments retenus, le libellé du lotissement par défaut,
l'écriture du lotissement, ses refus et sa réponse ; `test_mockwitness.py` admet un nœud de la
structure pour `conflicting_object_id`. Les catalogues reçoivent `generate_skeleton`,
`manage_timelines`, `main_structure_without_tasks`, `WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY` et
`DUPLICATE_WORK_BREAKDOWN_ITEM`.

## Toute opération à corps déclare 400 et 422 (EP-03, #748)

Décision de l'auteur du 2026-10-11. `updateAccessRole` recevait le corps de `createAccessRole`,
plus `lock_version`, sans déclarer ni 400 ni 422 ; le relevé a trouvé soixante opérations à corps
dans le même cas, presque toutes d'EP-02. Le service rend pourtant les deux pour toute opération
à corps : un corps illisible, absent ou qui n'est pas un objet, par 400 `MALFORMED_REQUEST` ; un
champ manquant, d'un autre type ou refusé, par 422 et le code du champ
(`backend/src/waterfall/api/problems.py`). Les deux réponses sont déclarées partout où il y a un
corps (58 `400`, 29 `422` ajoutés), et la règle `rule/operation-with-body-declares-400-and-422`
le tient. Écarté : ne corriger que `updateAccessRole`, l'oubli se serait reproduit à la prochaine
opération.

## C-291 et la préparation, le risque sans tâche, la ligne de provision, les catégories d'un changement de type, la fusion et l'import, le lotissement pendant un traitement de fond (EP-14/L42s)

Les écarts du contrat à la spécification relevés pendant L42p, L42r et L42k (#773) : #728, #733,
#766, #771, qui ferme ce qui restait de #586, et #775, ajouté au lot le 2026-10-10 avec le
commentaire de la relecture 2 de L42k. Les décisions sont de l'agent de réalisation du lot, chacune
avec sa raison. Le lot ne touche au front que pour compiler sur le client régénéré, tenir ses
catalogues et ses tests ; l'adoption par les écrans revient à un lot du front.

**Désactiver une nature désactive ses catégories** (C-291 ; WF-REF-0010 : « Désactiver une nature de
coût désactive ses catégories ; une catégorie ne peut être réactivée que si sa nature est active » ;
Vérif : « La désactivation d'une nature désactive ses catégories. La réactivation d'une catégorie
dont la nature est désactivée est refusée. »). `setCostTypeActivation` désactive chaque catégorie
active de la nature, dont le compteur avance et l'audit nomme l'auteur de la désactivation ; la
réactivation ne rend active que la nature, comme celle d'un nœud (« La réactivation ne cascade
pas », EP-02/L42a). La réactivation d'une catégorie sous une nature désactivée manque d'une
condition nouvelle, `cost_type_active`, que la commande `reactivate` de la catégorie dit d'avance et
que le 409 de `setCostCategoryActivation`, nouveau, nomme ; exemple
`cost_category_reactivation_refused` (corrélation 1151), la suite de `cost_type_deactivated`, dont
le résumé dit la cascade. La définition provisoire de L42p disparaît : `active_provision_category`
est une catégorie active de type provision pour risques, une catégorie active l'étant toujours sous
une nature active ; `CostCategoryImage.cost_type_is_active` reste, une information de lecture. Les
générateurs suivent (`mockdata.categories_of`, `mockreference.category_commands`,
`mockhistory.is_active_provision`) ; les natures du témoin sont actives, et aucun exemple engendré
ne change. Écartés : rendre les catégories désactivées dans la réponse, comme `setOrgNodeActivation`
— le schéma de la réponse aurait changé pour un écran qui lit une nature, et qui relit ses
catégories ; réactiver les catégories avec la nature, que l'exigence ne dit pas. Le 409 nomme la
nature à réactiver d'abord (`params.conflicting_object_id`), comme celui d'un nœud nomme son parent
(`org_node_reactivation_refused`, EP-02/L42a, #532 ; relecture 1) — écarté : laisser l'écran la lire
sur la catégorie, quand le refus d'une condition atteignable dit quoi faire (WF-IHM-0090).
L'écriture change l'état et les commandes d'autres objets, et le dit (L42g) :
`setCostTypeActivation` rejoint `RELIT` dans `test_mockcostsettings.py`.

**Une installation neuve manque de la catégorie de main-d'œuvre et du rôle** (WF-EXP-0020, qui crée
le calendrier par défaut et la catégorie de provision ; Vérif de WF-CYC-0120 : « Sur une
installation neuve, dont la seule catégorie est celle des provisions pour risques, la création est
refusée en nommant la catégorie de main-d'œuvre et le rôle manquants. »).
`reference_readiness_incomplete`, le second exemple de `getReferenceReadiness`, nomme
`active_cost_category` et `active_resource_role`, et son résumé le dit ; `ReferenceReadiness` et
`getReferenceReadiness` disent le prérequis « une catégorie de main-d'œuvre active », le libellé des
catalogues depuis EP-14/L53. Écarté : garder le calendrier parmi les manques, que l'amorçage crée.

**Le risque déclaré sur une structure principale sans tâche** (WF-RIS-0010 : « La déclaration d'un
risque sur une structure principale sans tâche est refusée, en nommant la condition manquante. »).
Le 409 de `createRisk` nomme `at_least_one_task`, avant `active_provision_category`, ce que L42p
avait arrêté ; `CommandCondition` décrit la condition, qui existait sans emploi. Exemple
`risk_without_task` (corrélation 1150), en dernier : le projet créé aujourd'hui, passé en Chiffrage
avec sa révision 103, dont la structure principale n'a encore aucune tâche — un état du témoin, non
une variante. Une commande nouvelle, `declare_risk`, le dit d'avance (relecture 1, décision de
l'agent de livraison) : toujours listée juste après `edit_risks`, là où elle l'est — la révision en
cours, ou le projet qui n'en a pas —, sous `risks.write`, ses conditions dans l'ordre du 409 : les
conditions d'état d'`edit_risks` d'abord, `project_not_terminal` puis `no_background_task_running`,
puis ses conditions propres, `at_least_one_task` puis `active_provision_category`, puis les autres
conditions d'`edit_risks`, `may_create_revision` sur le projet (relecture 2, décision de l'agent de
livraison, comme `update_work_breakdown`) : l'état prime sur le contenu, car sur un projet terminal
ou pendant un traitement de fond, ajouter une tâche ne rendrait pas la déclaration possible, et
nommer `at_least_one_task` inviterait à une saisie elle-même refusée. Sur un projet terminal,
`createRisk` refuse donc par ce 409, comme `updateProject` et `setWorkBreakdown`, la condition que
la commande annonce ; la première rédaction mettait les conditions propres d'abord. Ce 409 ne
contredit pas les 403 des saisies de la révision, dont celui du squelette (EP-14/L42k) : un projet
terminal n'a pas de révision en cours, si bien que la déclaration y passe par le projet, qui porte
alors `edit_risks` et `declare_risk` et nomme `project_not_terminal`, comme les imports qu'il porte
refusent un projet terminal par leur 409 ; une saisie de la révision, elle, n'a plus de révision en
cours où s'écrire, et reste un 403. *Remplacé par US-0702/L1 (#1610), sur la décision de l'auteur
du 2026-10-28 (D-05, J-01, J-02) : une saisie de la révision sur une révision marquée — toute
révision d'un projet terminal l'est — se refuse, elle aussi, par le 409 de sa condition,
`revision_draft`, et non par un 403 : le 409 de `createRisk` et celui des saisies de la révision ne
font plus qu'une règle. La phrase est gardée pour l'histoire.* **Réécrit par US-0702/L3** (#1657) :
sur un projet terminal, ni `edit_risks` ni `declare_risk` ne sont listées ; le 409 de `createRisk`
nomme `project_not_terminal` pour l'appel direct, et l'ordre ci-dessus ne vaut que pour les états
non terminaux. Sur le projet,
la structure jugée est celle de la révision que la déclaration créerait, sans tâche quand le projet
n'a aucune révision marquée. Les révisions et les projets écrits à la main qui listent `edit_risks`
listent la commande : indisponible sur la révision 103, sur le projet créé et sur l'offre en
chiffrage, sans révision, faute de tâche ; pendant un marquage ou un import, faute de ce qui manque
à `edit_risks` ; disponible ailleurs. L42p avait écarté cette commande pour
`active_provision_category`, « un cas que la création d'un projet exclut déjà » : la raison ne vaut
pas pour `at_least_one_task`, un projet tout juste créé n'ayant aucune tâche. Écartés : aucune
commande, le formulaire lisant les totaux de la structure principale (`listNodes`,
`totals.task_count`), que la première rédaction retenait — le front aurait déduit la règle de
l'état, ce que L42p a écarté pour `update_provision` ; la condition sur `edit_risks`, qui aurait
fermé la modification, le réexamen et la suppression d'un risque, qui n'en dépendent pas.

**La ligne de provision ne porte pas de délai de paiement** (#733 ; WF-DEV-0020 : « un délai de
paiement, en jours, qui […] reste saisissable sur toute ligne autre qu'une ligne de provision, qui
n'en porte pas » ; WF-IND-0100 : « une ligne de provision, qui n'en porte pas, reste à la date de la
tâche qui la porte »). Le délai quitte les `editable_fields` de la ligne de provision, sa lecture le
rend nul, et la courbe des décaissements la laisse à la date de sa tâche (`mockdating.payment_delay`,
`mockindicators.delays`) ; envoyé, il est refusé par 422, `fields` sur `/payment_delay_days`, motif
`FIELD_NOT_ACCEPTED`, code nouveau, celui de tout champ qu'un nœud n'accepte pas, ni saisi ni
calculé pour lui, que le contrat refusait jusqu'ici sans le nommer : un champ d'une autre nature de
ligne (`EstimateLineWrite`, `EstimateLineUpdate`, `createNode`, `updateEstimateLine`), la durée d'un
jalon (`TaskFacetUpdate`), une cellule collée sur une telle colonne (`PastePreview` ; relecture 1).
Le délai de paiement d'une ligne de main-d'œuvre, que le contrat n'offre pas quand la spécification
le veut saisissable, n'est pas codifié : #785 (décision de l'agent de livraison). `nodes_estimate`
et les lectures du nœud 555 sont engendrées en conséquence. Écartés : `COMPUTED_VALUE`, que l'issue
suggérait, qui dirait calculé un délai que la ligne ne porte pas (défaut n° 10 du guide) ; garder 0
à la lecture, une valeur que la ligne n'a pas ; un refus sans code, contraire à « une erreur est un
code ».

**Le calendrier d'un rôle seul sur sa tâche** (#766, point 1 ; WF-PLA-0010). Le 422
d'`updateResourceRole` dit les deux cas qui laissent une tâche sans heure : un calendrier qui ne
recoupe jamais celui d'un autre rôle de ses lignes, ou, sur une tâche dont ce rôle est le seul, un
calendrier sans heure ; et de même `createNode`, le 422 d'`updateEstimateLine` et
`Problem.params.resource_role_ids`, qui nomme alors ce rôle seul (relecture 1). La mention de la
section d'EP-02/L30 le dit. Pas d'exemple nouveau : le refus a la forme de
`calendar_update_without_hours`.

**Le refus d'un changement de type nomme les catégories en cause** (#766, point 2 ; WF-IHM-0090 :
« Tout refus nomme la condition manquante et, lorsqu'elle est atteignable par l'utilisateur, ce
qu'il faut faire pour la satisfaire »). Rattacher une catégorie à une autre nature du même type
n'est jamais indisponible (`CostCategoryCommand`) : `cost_type_unused` et `cost_type_unrated` se
lèvent en rattachant ailleurs les catégories en cause, et sont atteignables. Nommant l'une ou
l'autre, le 409 d'`updateCostType` porte `params.cost_categories` : les catégories de la nature
employées pour `cost_type_unused`, celles qui portent un taux pour `cost_type_unrated`, actives ou
désactivées, chacune par son identifiant, son code et son libellé, dans l'ordre de leur code — la
forme de `params.resource_roles`. La troisième, `cost_type_without_role`, nomme des rôles
(`params.resource_roles`, L42r). L'ordre des trois conditions reste, celui de l'exigence ; la raison
de L42r, « ce qu'aucune action ne lève », tombe. `cost_type_kind_refused`, le premier exemple, garde
son scénario et nomme la sous-traitance et le matériel électrique ; le taux n'a pas d'exemple propre
— la main-d'œuvre du témoin porte cent quarante-huit catégories à taux, toutes nommées, et le refus
a la même forme —, et `test_mockcostsettings.py` calcule les catégories nommées depuis les lignes
des exemples. Écartés : les seuls identifiants, que l'écran des paramètres de coûts, paginé et
filtré, aurait dû relire ; nommer à la fois les catégories des trois conditions, quand le refus dit
la première qui manque.

**Le compte rendu préalable de la fusion** (#771, point 1 ; WF-REV-0050 : « Avant application, la
fusion présente un compte rendu : tâches et lignes ajoutées, modifiées et retirées, tâches démarrées
qui seront terminées, et motifs de refus (WF-PLA-0030, WF-PLA-0150, WF-PLA-0170) » ; Vérif : « Le
compte rendu d'une fusion dont le différentiel retire une tâche démarrée nomme cette tâche comme
terminée ; l'abandon à cette étape laisse la révision en cours et la référence inchangées. »).
`getStructureMergeReport`, une lecture sur le chemin de la fusion, comme `getRateUpdateProposal` sur
celui de `applyRateUpdate`, rend `StructureMergeReport` : les écarts du différentiel
(`ImportDifference`), les tâches démarrées qu'il retire et que la fusion termine
(`ImportCompletedTask`, `completed_on` nul avant l'application), et les motifs qui la refusent
(`ReportRefusal`, partagé avec l'import). Abandonner, c'est ne pas confirmer ; une structure qui
n'est pas un différentiel non fusionné de la révision en cours a le 409 de sa fusion. **La
confirmation porte les compteurs lus** (relecture 1) : le compte rendu rend ceux de la structure
principale et du différentiel (`main_structure_lock_version`, `amendment_lock_version`), que
`StructureMerge` exige ; l'une ou l'autre changée depuis — une tâche démarrée, une ligne réestimée,
le différentiel modifié —, `mergeCostStructure` refuse par 412, et rien n'est fusionné :
l'utilisateur ne confirme que ce qu'il a lu, comme un collage depuis L42q.
`params.expected_lock_version` est toujours le compteur courant du différentiel, l'objet que le
chemin nomme, même quand seule la structure principale a changé, et rien d'autre, la règle unique
des 412 (#296) ; le client relit le compte rendu, qui rend l'un et l'autre (relecture 2). Le
contrôle des deux compteurs et le dépôt de la tâche de fusion se font en une seule transaction, sous
le verrou des deux structures, faute de quoi une écriture glissée entre eux ferait appliquer un
compte rendu périmé. Une saisie dans l'un des deux arbres fait ainsi refuser la confirmation ; ce
qui change hors d'eux — un calendrier du référentiel, le lotissement — fait échouer la tâche de fond
sur le motif du refus, la fusion jugeant encore ses refus à l'exécution, comme L42k l'a dit.
Écarté : nommer le compteur de la première structure changée, la rédaction de la relecture 1,
contraire à #296. Exemples, variantes déclarées : `structure_merge_report`, le premier, un
différentiel qui retire les « Pupitres opérateurs », démarrés, conservés et terminés, et
`structure_merge_report_refused`, celui de `task_merge_outside_order_item` ; leurs compteurs, 1 pour
la structure principale, comme `structures` le dit, et 2 pour le différentiel. Le premier reste une
variante tant que la révision courante du témoin ne porte aucun différentiel, l'avenant 2 de la
référence n'y étant pas repris : #791. Écartés : une analyse en tâche de fond, comme celle d'un
import — il n'y a pas de fichier à lire, et le compte rendu se calcule comme toute écriture de
grille, qui redate la structure de façon synchrone (`NodesWritten`) ; confirmer sans compteur, la
fusion re-jugeant seule ses refus — la première rédaction, qui aurait appliqué un compte rendu
périmé, une tâche démarrée depuis étant retirée au lieu d'être terminée ; un compteur de la
révision, que les écritures de ses structures n'avancent pas ; un compte rendu retenu par le serveur
et nommé par la confirmation, comme le plan d'un collage, un état de plus pour ce que deux compteurs
disent ; une forme d'écart propre à la fusion, qui aurait doublé `ImportDifference`.

**Un fichier d'import rejeté entier** (#771, point 2 ; WF-INTF-0040 : « Un fichier qui déplacerait
la tâche d'un lot hors du sous-arbre de la tâche de son poste est rejeté au compte rendu, qui nomme
les deux tâches, comme un planning qui dépasse l'horizon (WF-PLA-0150) » ; Vérif de WF-PLA-0150 :
« Un import MS Project dont le planning s'étend sur seize ans est rejeté au compte rendu. »).
`ImportReport.refusals`, exigé, vide quand le fichier s'applique : chaque motif qui rejette le
fichier entier, à côté des lignes rejetées (`rejected`) ; `WORK_PACKAGE_OUTSIDE_ORDER_ITEM` quitte
les motifs d'une ligne (`ImportRejection`), et `PROJECT_HORIZON_EXCEEDED`, code nouveau, nomme la
tâche en cause (`params.task`, son nœud, nul pour une tâche que le fichier crée, et son libellé).
`applyImport` refuse un tel compte rendu par 409, `missing_condition` à `import_file_accepted`,
condition nouvelle, après un compte rendu expiré ou déjà appliqué et avant les conditions de droits
et d'état revérifiées ; refusé, le fichier est supprimé, comme celui de tout import refusé à
l'application (WF-ARC-0100) ; et l'application rejuge les refus, échouant sur leur motif quand une
saisie faite depuis l'analyse ferait rejeter le fichier (relecture 1). Exemples :
`import_planning_rejected` (`getImport`, import a16), une variante déclarée qui porte les deux
motifs, et `import_apply_rejected` (corrélation 1153) ; les quatre comptes rendus existants portent
`"refusals": []`. Écartés : un état `rejected` de l'import, l'analyse ayant abouti ; un booléen
`is_applicable`, qui doublerait la liste, comme le collage partiel se lit à `rejected` (L42q) ;
garder la ligne rejetée, contre « comme un planning qui dépasse l'horizon ». Le code de l'horizon
n'est encore déclaré ni par les saisies ni par la fusion : #788.

*Remplacé en partie par US-0450/L1 : le motif rejeté entier est `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`,
la tâche d'un poste hors du sous-arbre de celle de son lot, section « Le lotissement en lots, postes
et livrables ».*

*Complété par US-0460/L2 : les saisies déclarent le code de l'horizon, section « Les gestes de
structure et la saisie des tâches » ; la fusion reste à EP-16 (#788).*

**Un poste sans tâche rattachée est présenté sans total** (#771, point 3 ; WF-DEV-0060 : « un poste
sans tâche rattachée est présenté sans total » ; Vérif : « les totaux par poste sont absents plutôt
que nuls »). `EstimateIndicators.by_order_item` n'est plus nullable : chaque poste du lotissement,
dans l'ordre saisi — il y en a toujours un, le lotissement par défaut en ayant un —, son montant et
sa part non calculables, motif `order_item_without_task`, nouveau, quand aucune tâche ne le porte
(`mockindicators.by_order_item`, qui lève sur un poste porté que le lotissement n'a pas, au lieu de
l'écarter). `minItems: 1` le dit ; les indicateurs conservés d'une révision marquée rendent les
postes de son marquage, un poste supprimé depuis compris (relecture 1). Le poste du témoin est
porté : aucun exemple ne change. Aucun exemple ne montre `order_item_without_task` : les seuls
indicateurs où il se lirait sans variante sont ceux du projet créé aujourd'hui, dont le devis vide a
un total nul, et la part d'un total nul est non calculable (`no_total`, 2026-10-29, #1633) —
l'exemple y viendra. Écartés :
omettre le poste, que l'écran ne pourrait présenter sans relire le lotissement ; un montant nul dans
un schéma propre, quand l'enveloppe `Computable` dit déjà qu'une valeur ne se calcule pas ; la liste
nulle, qui ne présente aucun poste.

*Remplacé en partie par US-0450/L1 : le total est celui des lots,
`EstimateIndicators.by_work_package`, motif `work_package_without_task`, section « Le lotissement en
lots, postes et livrables ».*

*Complété par US-0660/L2 : l'exemple du lot sans tâche rattachée vient d'une variante déclarée du
témoin, non du projet créé aujourd'hui, section « Le lot sans tâche rattachée, présenté sans total ».*

**Le lotissement attend la fin d'un traitement de fond** (#775, point 1 ; WF-PLA-0170, WF-IHM-0090).
La saisie du lotissement retire le rattachement des tâches de la révision en cours : pendant un
marquage, une fusion, une survenance ou l'application d'un import, elle est indisponible. Une
commande nouvelle du projet, `update_work_breakdown`, toujours listée après `update_win_probability`
et sous les conditions d'`update`, le dit (`no_background_task_running`), comme
`update_win_probability` dit la probabilité figée (L42i) ; `setWorkBreakdown` déclare son 409, qui
nomme la première condition qui manque dans l'ordre de la commande, `project_not_terminal` puis
`no_background_task_running` (depuis US-0702/L3, #1657, la commande n'est plus listée sur un projet
terminal, et cet ordre ne vaut d'avance que pour les états non terminaux ; relecture 1 ; défaut n° 2 du guide, la route sœur d'`updateProject`) ;
exemple `work_breakdown_background_task` (corrélation 1154). Les compteurs : celui du lotissement,
toujours ; quand des rattachements sont retirés, celui de chaque tâche touchée et celui de la
structure principale, comme une écriture de grille. Les huit projets écrits à la main listent la
commande ; les listes dérivées sont engendrées. Écartés : la condition sur `update`, qui aurait
fermé l'identité du projet pendant un marquage ; le 409 seul, une commande que l'état rend
impossible devant être présentée indisponible (WF-IHM-0090).

*Complété par US-0660/L2 : la commande présentée indisponible a son exemple,
`project_background_task_running` de `getProject`, section « La saisie du lotissement indisponible
pendant un traitement de fond ».*

**Les tâches du refus d'un lot hors de son poste sont nommées par leur libellé** (#775, point 2, et
le commentaire de la relecture 2 de L42k ; WF-PLA-0170, WF-IHM-0080).
`fields[].params.order_item_task` et `work_package_tasks`, chacune par son nœud et son libellé,
remplacent `order_item_node_id` et `work_package_node_ids` dans les refus d'`updateTaskFacet`, de
`createNode` et de `moveNodes`, comme l'échec d'une fusion et le rejet d'un import.
`task_attach_outside_order_item` les porte ; exemple `nodes_move_outside_order_item` (corrélation
1152), en dernier sous le 422 de `moveNodes`, la variante de la fusion. Les paramètres valent aussi
pour la tâche que `createNode` crée, son nœud nul, et pour une cellule `work_breakdown` collée
(`PasteRejection.params` ; relecture 1). `test_mockbounds.py` tient que les refus des bornes forment
un bloc contigu après le premier exemple — et non juste après lui : deux opérations citent d'autres
refus avant ceux de leurs bornes. Écarté : garder les identifiants et leur adjoindre des libellés,
deux noms pour un rôle.

*Remplacé en partie par US-0450/L1 : le refus est `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, ses paramètres
`work_package_task` et `order_item_tasks`, ses exemples `task_attach_outside_work_package` et
`nodes_move_outside_work_package`, section « Le lotissement en lots, postes et livrables ».*

**Corrélations** 1150 à 1154 ; l'import a16. `test_mockprovision.py` tient C-291, l'installation
neuve et le risque sans tâche ; `test_mockcostsettings.py` les catégories nommées ;
`test_mockbreakdown.py` les tâches nommées, les comptes rendus et le lotissement ;
`test_mockhistory.py` la ligne de provision ; `test_mocktoday.py` le poste sans total ;
`test_mockresourcesettings.py` le 422 du rôle. Les catalogues reçoivent `cost_type_active`,
`import_file_accepted`, `update_work_breakdown`, `declare_risk`, `PROJECT_HORIZON_EXCEEDED`,
`FIELD_NOT_ACCEPTED` et `order_item_without_task`.

**Hors du lot, relevés pour la suite**, ouverts en sous-issues de #773 : le délai de paiement d'une
ligne de main-d'œuvre, que WF-DEV-0020 dit saisissable depuis C-237 et C-330 et que le contrat
refuse (#785) ; la tâche qui porte la provision d'un risque, que sa déclaration ne désigne pas
(WF-RIS-0010, #786) ; le retour d'un risque écarté à l'état identifié sur une structure sans tâche,
que la spécification ne dit pas (#787, à trancher par l'auteur) ; l'horizon et le cycle de liaisons,
sans code pour les saisies ni échec décrit pour la fusion (WF-PLA-0150, WF-PLA-0030, #788) ; les
comptes rendus d'un import et d'une fusion, qui ne signalent ni la ligne de provision déplacée
(WF-RIS-0010) ni une tâche rangée ailleurs dans l'arbre (#789) ; la fusion sur un projet sans
révision en cours (#790) ; la révision courante du témoin, qui ne reprend pas l'avenant 2 de la
référence (#791) ; `mockhistory.is_active_provision`, qui relit sur le disque une liste engendrée
par la même commande (#792).

## Le 412 de la désactivation d'un compte (EP-03/US-0360/L2, #828)

`setUserActivation` reçoit le `lock_version` du compte sans déclarer le 412 qu'un compteur
périmé donne, que toute écriture qui porte une version déclare (#296, #532) : il est déclaré,
`STALE_LOCK_VERSION`, `params.expected_lock_version`. Écarté : ignorer le compteur reçu, une
désactivation écraserait alors une modification que l'administrateur n'a pas vue (WF-IHM-0110).
Son corps devient un schéma nommé, `UserActivationWrite`, comme `UserRolesWrite` : le service en
engendre le modèle, que le générateur ne tire pas d'un corps décrit en place.

## Le lien de fixation, enfin au contrat (EP-03/US-0350/L5)

`createPasswordSetupLink` (`POST /users/{user_id}/password-link`) était décrit dans
`paths/access.yaml` depuis EP-02/L29 (#388), mais la racine du contrat ne le référençait pas :
il manquait au contrat assemblé, donc au client du front, aux modèles du service et au faux back.
La racine le référence, sans rien changer à sa description, au moment où le service le sert.

## Aucun libellé fait seulement de blancs (EP-03, #837)

Décision de l'auteur du 2026-10-11. Le libellé d'un rôle n'exigeait qu'un caractère : « ␣␣␣ » était
accepté, et le rôle n'avait plus de nom visible dans la matrice. Les quarante-quatre libellés, noms
et codes du contrat qui exigeaient un caractère exigent désormais un caractère qui n'est pas un
blanc (`pattern: '\S'`) ; le service, dont les modèles sont engendrés du contrat, le refuse par 422
`VALIDATION_FAILED` au pointeur du champ. Écarté : ne corriger que le libellé d'un rôle, l'oubli
serait resté sur les noms d'un compte et les libellés du référentiel.

## Les préférences d'affichage ont une taille bornée (EP-03, #874)

Décision de l'auteur du 2026-10-11. `DisplayPreferences` ne bornait ni le nombre de grilles, ni la
taille de leurs filtres, ni la longueur des noms : chaque `updateMyPreferences` pouvait ajouter des
grilles, et les préférences sont relues avec le compte à chaque requête de son titulaire et dans la
liste des comptes. Bornes : cent grilles ; un nom de grille, de colonne ou de filtre de 64
caractères ; par grille, 64 colonnes masquées et 64 largeurs ; 20 filtres, chacun un texte de 500
caractères au plus. Les noms d'aujourd'hui en ont moins de vingt, et la recherche elle-même s'arrête
à 200 caractères. Un filtre devient un texte, ce que le front écrit déjà : la valeur du paramètre de
l'adresse qui le porte. Le service, dont les modèles sont engendrés du contrat, refuse une borne
passée par 422 `VALUE_TOO_LONG` ; un nom trop long l'est au pointeur de l'objet qui le porte, comme
un NUL dans un nom, une clé n'étant pas un champ. Écarté : une borne sur la taille du document
entier, que le contrat ne sait pas dire et qu'un code d'erreur par champ ne pointerait pas.

## Le 412 et le 422 de chaque opération qui peut les rendre, les refus du fournisseur (EP-03, #799, #827, #814, #815)

Décisions de l'auteur du 2026-10-11. Le service refuse un paramètre de requête hors de son schéma
par 422 `VALIDATION_FAILED`, sur toute opération qui en a, et un `lock_version` périmé par 412
`STALE_LOCK_VERSION`, sur toute écriture qui en porte. Vingt-quatre opérations à paramètres de
requête ne déclaraient pas leur 422 (#799), et `setNodeTracking` pas son 412 (#827) : elles les
déclarent. Deux tests du service (`backend/tests/test_contract_declarations.py`) le tiennent, en
lisant le contrat références suivies — ce que les règles de `redocly.yaml` ne savent pas faire
pour la place d'un paramètre ou les propriétés d'un corps.

`createUser` dit deux cas que le service connaît : son 409 n'a pas de `conflicting_object_id`
quand seul le fournisseur d'identité porte l'adresse (#814) ; son 422 refuse aussi une adresse
ou un nom que le fournisseur refuse alors que la règle du contrat les admet (#815). Écarté :
resserrer la règle des adresses sur celle du fournisseur, qui défait la décision de #665.

## Attribuer un rôle, et l'invitation d'un compte créé (EP-03/US-0360/L2b, #834, #816)

**Attribuer un rôle exige la permission de modifier les rôles** (#834 ; décision de l'auteur du
2026-10-11). `setUserAccessRoles` n'exigeait que `users.write` : qui la portait sans
`access_roles.write` lisait l'identifiant du rôle administrateur dans les `access_role_ids` d'un
compte, se le donnait, et obtenait la gestion des rôles. Le corps de WF-ADM-0090 (FBS-1.2) range
« attribuer ou retirer des rôles aux comptes » parmi ce que fait l'utilisateur habilité aux rôles :
l'opération exige désormais, outre `users.write`, `access_roles.write`, et refuse sans elle par 403
`PERMISSION_MISSING`. La commande `set_access_roles` d'un compte ne se liste que pour qui porte les
deux, ce qui amende « Toutes suivent `users.write` » (EP-02/L42d). Écartés : refuser seulement un
rôle qui porte une permission que l'appelant n'a pas, une règle de plus à tenir à chaque
modification d'un rôle ; assumer l'élévation par écrit, contraire à WF-ADM-0090.

**`createUser` dit si l'invitation est partie** (#816 ; décision de l'auteur du 2026-10-11). Quand
le courriel qui porte le lien de fixation ne part pas — royaume sans messagerie (WF-CMP-0030),
serveur de courriel en échec, fournisseur injoignable —, le compte existe tout de même et `createUser`
rendait 201 sans le dire : la personne attendait un courriel qui ne viendrait pas. La réponse est
désormais `UserCreated`, le compte (`User`) et `invitation_sent`, un booléen exigé ; faux, l'écran
des comptes propose aussitôt le lien de fixation (`createPasswordSetupLink`). Écarté : une règle
d'écran qui propose toujours le lien, que l'administrateur remettrait aussi à qui l'a déjà reçu.

## L'anonymisation d'un compte (EP-03/US-0360/L2b, #702, #832)

**Un compte anonymisé garde sa ligne, ses noms et son adresse à nul** (#832 ; décision de l'auteur
du 2026-10-11). `UserAccount` rend `last_name`, `first_name` et `email` nuls pour un compte
anonymisé seulement, et `anonymized_at`, exigé, nul tant qu'il ne l'est pas ; `ActorRef.display_name`
et `AuditActorFacet.display_name` sont nuls pour lui, `AuditObject.label` aussi. Le front présente
un nom nul d'un compte sous le libellé neutre de son catalogue : l'API ne rend aucune phrase
(WF-ARC-0110). Écartés : un libellé neutre écrit en base, une phrase que l'API rendrait ; une
adresse de remplacement, une valeur qu'aucune personne ne porte.

**`anonymizeUser`, `POST /users/{user_id}/anonymization`** : l'anonymisation est irréversible, et
mérite un verbe comme le marquage (« Forme des chemins ») ; elle porte le `lock_version` lu, d'où
son 412, et rend le compte (`User`) ; aucune confirmation côté API, l'écran la demande. Elle
refuse un compte actif par 409 `STATE_FORBIDS_OPERATION`, `missing_condition` à
`is_deactivated_account`, une condition de plus, miroir de `is_active_account`, et un compte déjà
anonymisé par `is_not_anonymized` (#856 ; décision de l'auteur du 2026-10-11). La commande
`anonymize` ne se liste que pour un compte désactivé, comme `reactivate` qu'elle suit : disponible
tant qu'il n'est pas anonymisé, indisponible ensuite, `is_not_anonymized` manquante. Un compte
local est retiré du fournisseur d'identité **avant** l'écriture, hors transaction (#669), après
une vérification sous transaction courte — le compte, son état, sa version — : si le fournisseur
ne répond pas, 503 et rien n'est écrit, et l'anonymisation se redemande ; un compte que le
fournisseur ne tient déjà plus est retiré. Une modification glissée entre la vérification et
l'écriture fait refuser l'écriture, le compte étant déjà retiré du fournisseur : si c'est une
réactivation, le compte local est actif hors du fournisseur, et personne ne s'y connecte, jusqu'à
ce qu'on le désactive puis l'anonymise de nouveau, le retrait étant sans effet sur un compte que
le fournisseur ne tient plus. Fermer cet écart est à trancher (#868). Un compte de l'annuaire ou
d'un fournisseur externe n'est pas touché dans le fournisseur, et la lecture des comptes ne le
recrée pas (WF-ADM-0070). Écarté : retirer le compte local après la validation, un échec du
fournisseur seulement journalisé, qui laisse un compte anonymisé dans le fournisseur sans que
personne le sache. La commande `reactivate` d'un compte anonymisé est indisponible,
`is_not_anonymized` manquante, que `setUserActivation` nomme dans son 409 ; `updateUser` la nomme
aussi pour un nom, un prénom ou une adresse envoyés à un compte anonymisé, que la contrainte de la
table refuserait. `user_anonymize` s'ajoute à `AuditAction` (WF-SEC-0030), l'objet le compte, sans
libellé ni paramètre. La base n'admet l'oubli d'un nom dans le journal que pour un compte anonymisé
(#865) : le déclencheur du journal n'admet que le passage à nul de `actor_display_name` ou
`object_label`, l'un au moins, le reste de la ligne inchangé, et un déclencheur du module des
comptes sur le journal refuse ce passage quand le compte désigné n'a pas `anonymized_at` ; la
plateforme ne lit la table d'aucun module (`docs/dev/sql.md`). Écarté : laisser la vérification au
service seul, qu'une écriture qui le contourne ne rencontre pas.
`User.available_commands` admet trois commandes.

## Le journal d'audit rend les paramètres de l'action (EP-03/US-0410/L2, #706)

Décision de l'auteur du 2026-10-10. `AuditEvent` disait qui avait changé les rôles de qui, mais
pas lesquels : l'« afin de » d'US-0410, dire après coup qui a donné quel droit, ne se lisait pas,
quand l'inscription garde ces données depuis US-0410/L1. Il rend `params`, un `AuditParams` : un
seul objet fermé, dont chaque propriété dit l'action qui la porte — l'origine d'un compte créé,
les champs d'une identité modifiée et, quand la modification le rattache à une personne de
l'annuaire qui porte son adresse, ce rattachement (`attached`, #707), les permissions d'un rôle
créé, données ou retirées par sa modification et son libellé d'avant, les rôles donnés ou
retirés à un compte, chacun par son identifiant et son libellé du moment —, en codes, en
identifiants et en libellés, jamais en phrase (WF-ARC-0110). Une action qui n'a rien à dire de
plus que son objet rend un objet vide, dit tel dans `AuditParams`, sauf celles dont la
spécification demande un paramètre : la sortie du cycle de vie rend son état d'arrivée et son
motif (WF-CYC-0060, WF-CYC-0130), la restauration la date de la sauvegarde remise en place
(WF-ADM-0160), l'application d'un import sa nature.
Écarté : un schéma par action, choisi par `action` (`oneOf` à discriminant), que le discriminant
d'OpenAPI ne sait pas lire hors de l'objet qu'il choisit et que le client engendré rendrait en
dix-neuf types pour neuf actions servies ; les valeurs d'une identité modifiée, avant et après,
qu'aucune exigence ne demande et qu'une anonymisation devrait aussi effacer.

L'exemple `administration` de `listAuditEvents` (`audit_events_administration`, US-0410/L2b, #961)
donne ces paramètres tels que le service les inscrit, sur les écritures d'aujourd'hui des comptes
et des rôles : un rôle créé sans permission, enregistré sans
changement, renommé en recevant et en perdant des permissions ; un compte créé avec son premier
rôle, que la requête de la création inscrit après lui sous sa corrélation ; un nom corrigé ; un
rattachement à l'annuaire ; une attribution qui ne fait que retirer. Une attribution qui ne change
rien n'y est pas : le service ne l'inscrit pas. Ce que les autres exemples ne répondent pas y est
une liberté déclarée, dans le résumé comme ici :
- une modification combinée, renommage et permissions, qu'aucun exemple d'`updateAccessRole` ne
  répond — chacun renomme ou change les permissions, jamais les deux ; son état après est écrit
  par `mockaudit` (les permissions de `access_role_updated` moins celles de la saisie des
  paramètres de coûts et de ressources), et ce qu'elle accorde et retire s'en lit comme le
  service le lit, dans l'ordre du catalogue ;
- une création avec premier rôle qu'aucun exemple de `createUser` ne répond — chacun crée son
  compte sans rôle : le compte de `user_created` reçoit « Chiffreur » de la requête qui le crée ;
- un rattachement à l'annuaire, par la plateforme, qu'aucun exemple ne répond : Noé Vidal, tel que
  la liste des comptes le donne, prend le nom que l'annuaire donne à la personne qui porte son
  adresse, « Vidal-Roux » (`mockaudit.DIRECTORY_LAST_NAME`).

*Note du 2026-10-30 : la phrase sur les actions sans paramètre est réécrite ; recadrage d'EP-16
décidé le 2026-10-28.*

Une inscription lue d'un exemple est de l'auteur de sa dernière mise à jour (`audit.updated_by`) ;
`test_mockaudit.py` le tient.

## Le journal d'audit dans la sauvegarde, la permission du téléchargement (EP-03/US-0440/L1, #705)

Décision de l'auteur du 2026-10-10 (#705), suivant WF-SEC-0030 révisée : le journal d'audit est
sauvegardé avec la base de Waterfall. `Backup`, `Backup.scope` et `startBackup` le disent, à la
place de « à l'exception du journal d'audit » qu'écrivait la décision 9 d'US-0350/L1 ; la
restauration, qui relit les inscriptions postérieures à la sauvegarde et les réinscrit, reste à
dire par son lot (US-0440/L2). `startBackup` est sous `backups.write`, comme toute écriture de la
fonction ; `downloadBackup` demande `backups.read` puis `backups.write` : l'archive porte les deux
bases entières, comptes et réglages du fournisseur d'identité compris, et son 403 déclaré n'avait
pas d'autre permission à nommer. Écarté : `backups.read` seule, qui ferait sortir de la
plateforme tout ce qu'elle garde à qui ne peut que lire la liste.

## La restauration et sa maintenance (EP-03/US-0440/L2, #604, #892)

Décision de l'auteur du 2026-10-10 (#604) : `getLiveness`, publique, dit la maintenance d'une
restauration (`status` à `maintenance`) et sa levée (`ok`), et le front l'interroge pour savoir
quand la restauration a abouti. L'état de maintenance ne dépend pas de la base que la
restauration recrée, où vit la tâche ; `getBackgroundTask` n'est pas servie pendant la
maintenance, et toute opération autre que la sonde répond 503 `COMPONENT_UNAVAILABLE`,
`component` à `database`. La sonde reste à 200 en maintenance : la plateforme est vivante, et un
orchestrateur qui la redémarrerait interromprait la restauration. Écarté : `getBackgroundTask`
servie pendant la maintenance, sa ligne réécrite dans la base restaurée, qui ferait lire à l'API la
base qu'on remplace.

`startRestore` déclare ce qu'elle refuse : une date confirmée qui n'est pas celle de la sauvegarde
désignée est une confirmation qui ne la nomme pas, 400 `CONFIRMATION_REQUIRED` (WF-ADM-0160 : « La
confirmation nomme la date de la sauvegarde ») ; une sauvegarde ou un dépôt inconnus, 404 ; une
restauration déjà en file ou en cours, 409 `STATE_FORBIDS_OPERATION`. Écarté : un 422 par champ
sur `acknowledged_backup_taken_at`, qui dirait la valeur invalide quand c'est la confirmation qui
manque.

Décision de l'auteur du 2026-10-12 (#892) : une tâche que la restauration trouve en file ou en
cours dans la base restaurée échoue par `TASK_INTERRUPTED_BY_RESTORE` (409), code propre, sans
reprendre ; exemple `task_interrupted_by_restore`, variante contrefactuelle. Décision de l'auteur du
2026-10-13 (#987) : les tâches que la restauration garde — la sienne et celles des sauvegardes, que
la liste garde (#893) — reprennent l'état gardé, plus récent que la sauvegarde, et seules les autres
tâches restaurées en file ou en cours échouent ainsi ; l'exemple, qui figeait une sauvegarde
interrompue, devient une lecture des comptes en file. Écarté : faire échouer la tâche d'une
sauvegarde que la liste tient vérifiée, un succès présenté comme un échec (WF-EXP-0040).

Décisions de l'auteur du 2026-10-12 (#953, #954, #955) : la restauration est exécutée par un
service à part, seul à tenir l'adresse du propriétaire des bases et le client d'administration
du fournisseur d'identité, et non par le worker ; le contrat n'en change pas — `startRestore`
dépose toujours une tâche `restore`, que la sonde de vie suit. Après le remplacement des bases, le
royaume de l'installation qui restaure est réappliqué : la description de `startRestore` dit que
ses clients et ses adresses restent ceux de la cible, ses comptes et leurs mots de passe ceux de
la sauvegarde (#955).

## Le compte rendu de la lecture des comptes (EP-03/US-0370/L2, #707, #811)

`IdentitySyncReport` dit de quelle lecture il rend compte et quand elle a fini (`task_id`,
`finished_at`) : la plateforme en planifie une chaque jour, et l'écran des comptes montre la
dernière qui a abouti, demandée ou non. Il nomme aussi, dans `removed`, les adresses des comptes
locaux que la lecture retire du fournisseur d'identité — inconnus de Waterfall, sans mot de
passe, laissés par une création interrompue —, décision de l'auteur du 2026-10-11 (#811). Le
compte rendu s'inscrit dans la transaction de la lecture, et le retrait ne suit que sa
validation : une adresse de `removed` est celle d'un compte retiré, ou à retirer. Un retrait qui
échoue est journalisé, et la lecture suivante, qui retrouve le compte, nomme de nouveau son
adresse. Un
rattachement par l'adresse d'une personne de l'annuaire à un compte existant (#707) compte parmi
les mises à jour : il change le compte que le fournisseur désigne, son nom, son prénom et son
adresse, et s'inscrit au journal comme une modification du compte, `params.attached` à vrai.
`ALREADY_EXISTS` et `VALIDATION_FAILED` rejoignent `LAST_ADMINISTRATOR` parmi les motifs d'un
compte laissé tel quel.
`startIdentitySync` est sous `users.write`, comme toute écriture des comptes ;
`getLatestIdentitySync` sous `users.read`, 404 tant qu'aucune lecture n'a abouti. Écarté : un
compteur de rattachements à part, que l'écran ne présente pas autrement qu'une mise à jour.

## Le compte rendu de la lecture des comptes, sans donnée d'un compte (EP-03/US-0370/L2b, #918, #919, #920)

Décisions de l'auteur du 2026-10-12. Une entrée de `IdentitySyncReport.skipped`
(`IdentitySyncSkipped`) dit par `kind` ce qu'elle désigne :

- **un compte de Waterfall** (`account`) — le dernier administrateur gardé, un compte dont la
  nouvelle adresse est portée par un autre, dont le nouveau nom ne se garde pas ou dont le
  fournisseur ne tient plus d'adresse — n'est gardé dans le compte rendu que par son
  identifiant : le compte rendu n'en copie ni le nom ni l'adresse, que l'anonymisation devrait
  sinon poursuivre dans chaque compte rendu (#920). Son nom, son prénom et son adresse sont lus à
  la consultation, nuls pour un compte anonymisé depuis, que le front présente sous le libellé
  neutre ;
- **une personne du fournisseur** sans compte (`person`) est nommée par son identifiant chez lui,
  `subject`, son nom, son prénom et son adresse, nulle s'il n'en tient pas : `EMAIL_MISSING`
  entre au catalogue pour elle (#918) — une personne sans adresse, que Waterfall ne sait pas
  reconnaître, n'est plus ignorée en silence. Sauf celle qu'un compte de Waterfall prive de son
  adresse (`ALREADY_EXISTS`, une personne relayée par un fournisseur externe, #707) : cette
  adresse est celle du compte, que le compte rendu ne copie pas plus que son nom, et
  l'anonymisation du compte l'y laisserait. L'entrée garde l'identifiant de la personne chez le
  fournisseur, `subject`, et celui du compte qui porte l'adresse, `user_id` — nul si aucun ne la
  portait plus quand elle a été écartée —, rien de personnel ; son nom, son prénom et son adresse
  sont ceux du compte, lus à la consultation comme pour une entrée `account`, nuls s'il est
  anonymisé depuis (décision de livraison, application de #920). `account` porte donc `user_id`
  et jamais `subject` ; `person` porte toujours `subject`, et `user_id` pour `ALREADY_EXISTS`
  seulement. Écartées : le nom que le fournisseur tient de la personne, gardé à côté de
  l'identifiant du compte — deux identités dans une entrée, que l'écran ne distinguerait que par
  son motif ; une entrée `account` désignant le compte porteur — elle dirait laissé tel quel un
  compte que la lecture n'a pas touché.

Une seule forme, fermée — `additionalProperties: false`, chaque propriété exigée, nulle quand elle
ne vaut pas pour la nature de l'entrée —, comme `ActorRef` dit par `kind` un compte ou la
plateforme. Écartées : l'adresse rendue facultative dans la forme `{email, code}` — une entrée
sans adresse ne désignerait plus personne, et l'adresse d'un compte de Waterfall resterait
copiée ; deux formes réunies par `oneOf` — le contrat n'en compose aucune de deux objets, que le
client du service et ses tests ne lisent pas (`AmbiguousCompositionError`) ; une liste à part pour
les personnes sans adresse — une seconde forme pour un même signalement.

`restored` compte les comptes locaux dont la lecture rétablit l'identité dans le fournisseur : le
nom, le prénom ou l'adresse que Keycloak en tient diffèrent de ceux de Waterfall, qui en fait foi
(WF-ADM-0050) — un report d'`updateUser` resté sans réponse, ou une modification faite dans la
console du fournisseur (#919). L'adresse s'y compare sans égard à la casse, que le fournisseur ne
garde pas. Comme `removed`, le compte suit la validation de la lecture : rétabli, ou à rétablir.
Un compteur plutôt que la liste des comptes : l'écran ne nomme pas plus les comptes rétablis que
les comptes mis à jour, et le journal de la plateforme dit chacun. Écarté : les compter dans
`updated`, qui dit les comptes que la lecture change dans Waterfall.

## La session révoquée (EP-03/US-0350/L5c, #855)

Décision de l'auteur du 2026-10-11 (#855). Un jeton dont la connexion (`auth_time`, à défaut
`iat`) précède la dernière fermeture des sessions du compte, ou tombe dans sa seconde, est refusé
par 401 `SESSION_REVOKED`, et non plus `SESSION_EXPIRED`, que garde la seule expiration du jeton.
La fermeture que le fournisseur d'identité a manquée — une panne pendant la déconnexion ou la
désactivation — laisse vivre sa session : une connexion ordinaire en rendrait un jeton de la même
connexion, de nouveau refusé, jusqu'à la fin de cette session, deux heures plus tard au moins. Sur
ce code seulement, le front mène à une connexion qui force l'authentification (`prompt=login`),
et le fournisseur renouvelle `auth_time` ; une expiration ne redemande pas d'identifiants. Le
retrait de tous les rôles d'un compte note aussi l'heure de la fermeture (`setUserAccessRoles`),
comme la déconnexion et la désactivation : une fermeture manquée n'y survit pas à un rôle rendu.
Un jeton à la fois expiré et antérieur à la fermeture reçoit `SESSION_EXPIRED` : l'expiration
prime, constatée par la validation du jeton avant que le compte soit lu ; le front rafraîchit
alors, et le jeton rafraîchi, de la même connexion, reçoit `SESSION_REVOKED` si le fournisseur a
manqué la fermeture ; s'il a fermé la session, c'est le rafraîchissement lui-même qu'il refuse
(#940).
Écartés : redemander les identifiants à toute expiration, que rien ne justifie après cinq
minutes de jeton d'accès ; laisser `closeMySessions` accepter un jeton antérieur à la fermeture,
qui ne sort de l'impasse que la personne qui sait se déconnecter.

## Les colonnes d'audit des comptes et des rôles (EP-03/US-0360/L4, #936)

Décision de l'auteur du 2026-10-12 (#936, option (a)) : les tables des comptes et des rôles
d'habilitation présentent « Créé le », « Créé par », « Modifié le » et « Modifié par », que
`User.audit` et `AccessRole.audit` portaient déjà, et chacune se trie et se filtre (WF-IHM-0060,
WF-IHM-0130) ; l'écart de WF-ADM-0060-A — un compte désactivé reste nommé partout où il est cité
— s'y constate. Les noms et les règles suivent ce que le contrat a déjà ; ce qui suit est de
l'agent du lot, chacun avec sa raison.

- **Le tri** : `sort_by` de `listUsers` et de `listAccessRoles` gagne `created_at`, `created_by`,
  `updated_at` et `updated_by`, les noms des champs d'`Audit`. Un auteur se range comme celui du
  journal (`sort_by=actor` de `listAuditEvents`, EP-02/L42d) : un compte par son nom affiché, le
  prénom puis le nom, comparé dans l'ordre des points de code ; dans l'ordre croissant, un compte
  anonymisé, qui n'a plus de nom, après les noms, et la plateforme, qui n'en a pas, après les
  comptes. À égalité, l'ordre de la liste sans tri, puis l'identifiant (#741).
- **Les périodes** : une par colonne de date, `created_at_from` et `created_at_to`,
  `updated_at_from` et `updated_at_to`, deux instants, le début inclus, la fin exclue, comme la
  période du journal et de la liste des projets. Une table qui a deux colonnes de dates ne peut
  pas les filtrer toutes deux par `from` et `to` : chaque borne prend le nom de sa colonne, comme
  `<colonne>_min` et `<colonne>_max` d'une colonne de nombres (EP-02/L42f), et le README étend la
  règle des périodes à cette forme, le refus d'une période inversée désignant
  `/query/<colonne>_to`. Exemples `users_period_inverted` et `access_roles_period_inverted`,
  écrits à la main ; `test_mockuniverse.py` les tient à la règle, et les deux opérations à la
  déclaration de leur 422.
- **Les auteurs** : `created_by_user_id` et `created_by_kind`, `updated_by_user_id` et
  `updated_by_kind`, sur le modèle de l'auteur du journal (`user_id`, `actor_kind`,
  `AuditActorKind`) : un compte, désactivé ou anonymisé compris, ou la plateforme, un traitement
  automatique (WF-DAT-0070). Les huit paramètres sont partagés (`parameters.yaml`), pour que les
  deux tables ne divergent pas. Écartés : une recherche sur le nom de l'auteur, qui ne trouverait
  pas un compte anonymisé, dont l'API ne rend aucun libellé ; une opération des auteurs à la
  manière de `listAuditFacets`, que la conception d'EP-03 ne prévoit pas : la liste des rôles,
  non paginée, nomme elle-même ses auteurs, et l'écran des comptes choisit un compte parmi les
  comptes qu'il lit.
- **Un auteur désactivé reste nommé, un anonymisé ne l'est plus** : `ActorRef.display_name` le dit
  déjà (WF-ADM-0060), et les descriptions des deux opérations le rappellent. Le témoin n'a aucune
  ligne de ces tables écrite par Alix Moreau, cheffe de projet sans permission sur les comptes ni
  sur les rôles : la lui donner ferait changer les porteurs du témoin et le journal qui en est
  engendré. Deux variantes contrefactuelles déclarées, écrites à la main comme celles du journal
  (`audit_events_anonymized_actor`), la montrent : `access_roles_updated_by_deactivated`, une
  installation où, habilitée alors, elle aurait modifié « Chef de projet » le 10 février 2026,
  avant sa désactivation — « Modifié par » la nomme — ; `access_roles_updated_by_anonymized`, la
  même après l'anonymisation de son compte, le nom de l'auteur nul. `test_mocklists.py` les tient
  au rôle du témoin, dont seuls l'audit et le compteur diffèrent.
- **Pas d'index** : au plus 500 comptes aux volumes du §4.6.2, et quelques rôles ; les deux tables
  se trient en mémoire de PostgreSQL sans en avoir besoin.

Exemples engendrés par `wftools.mocklists` du témoin : `users_created_by_platform`
(`created_by_kind=platform`), `users_by_created_at` (`sort_by=created_at`) et
`access_roles_by_updated_by` (`sort_by=updated_by`, la plateforme après Camille Martin). Le
client est régénéré.

## La reprise de `main` après EP-03 : les sauvegardes, les dépôts et les règles d'EP-03 (EP-14)

`epic/EP-14` reprend `main` après la livraison d'EP-03 (#1029), par une fusion, comme le dit son
fichier (« Reprise de `main` après la livraison d'EP-03 »). Les deux EPIC avaient écrit chacun une
part du contrat des sauvegardes : EP-03 en a fait le service (US-0350/L1, US-0440), EP-14 la
maquette et ses parties de contrat (EP-02/L43c, EP-14/L42h, L42m, L42o). Pour chaque règle, la
fusion garde celle qui est en vigueur ; là où les deux côtés divergent, le choix et l'option
écartée sont ceux-ci. Ailleurs, les deux côtés sont gardés.

**Une date confirmée qui n'est pas celle de la sauvegarde est une confirmation manquante, 400
`CONFIRMATION_REQUIRED`** (EP-03/US-0440/L2, décision de l'auteur du 2026-10-10, que le service
tient et ses tests éprouvent). Écarté : le 422 par champ d'EP-14/L42h,
`/acknowledged_backup_taken_at` par `BACKUP_DATE_MISMATCH`, qu'EP-03 a écarté nommément. Le code
`BACKUP_DATE_MISMATCH` quitte le catalogue et les deux catalogues du front ;
`restore_date_mismatch`, doublon de `restore_confirmation_mismatch` (EP-03), est retiré, et
`restore_external_date_mismatch`, le même refus pour une sauvegarde déposée, devient ce 400, cité
après lui.

**Le téléchargement d'une sauvegarde est sous `backups.read` et `backups.write`** (EP-03/US-0440/L1,
#705, décision de l'auteur du 2026-10-10 : l'archive porte les deux bases entières ; le service le
tient ; confirmée par l'auteur le 2026-10-18). Écartée : la permission de la restauration, `platform_restore`, décision de l'auteur du
2026-10-09 (#588, EP-02/L43c), que la décision suivante remplace. `BackupCommand` le dit : le
marquage sous `backups.write`, le téléchargement sous les deux, la restauration sous
`platform_restore`.

**Une sauvegarde se dépose par morceaux, et sa date se lit au manifeste, à l'achèvement**
(EP-03, #350, #1006 : `openChunkedUpload`, `uploadChunk`, `completeChunkedUpload`). Écarté : son
dépôt par `uploadFile`, qui lisait l'instant de l'archive au dépôt (EP-14/L42m) ; `uploadFile` ne
sert plus que les imports et refuse `external_backup`. De L42m, la fusion garde la forme de
`FileUpload.backup_taken_at`, exigé et nul pour le fichier d'un import (`file_upload`), que le
service, qui ne rend que des dépôts de sauvegarde, tient sans changer ; écartée, sa présence pour
les seuls dépôts de sauvegarde (#1006), qui aurait retiré à l'exemple d'un import sa date nulle.
`file_upload_external_backup`, la copie de Lyon, devient un exemple de `completeChunkedUpload`,
après `chunked_upload_completed` ; `file_upload_backup_unreadable` est retiré au profit de
`chunked_upload_unreadable`, le même refus à l'achèvement.

**Le 409 de `startRestore` nomme sa condition** (EP-14/L42h : `no_restore_running`,
`no_backup_running`, `backup_verified`). Il étend celui d'EP-03, une restauration déjà en file ou
en cours, sans paramètre : `restore_already_pending`, doublon de `restore_during_restore_refused`,
est retiré. Le service rend aujourd'hui ce 409 sans `params` et ne refuse pas encore une
sauvegarde non vérifiée ni une sauvegarde en cours : un écart du service au contrat, relevé par
la reprise. Le 404 garde le texte des deux : une sauvegarde inconnue, ou que l'appelant ne peut
pas lire, un dépôt inconnu ou expiré, sans distinction.

**Les ajouts d'EP-14 que rien d'EP-03 ne contredit restent** : les commandes que liste chaque
sauvegarde (`Backup.available_commands`), les filtres et le tri de `listBackups`, les 409 de
`startBackup`, `retainBackup` et `downloadBackup`, les en-têtes du téléchargement, la vérification
d'une sauvegarde déposée par sa restauration, avant la maintenance (L42o). L'exemple
`backups_unverified` (EP-03) reçoit les commandes de la session de Camille Martin, le téléchargement
et la restauration indisponibles faute de `backup_verified`, et sa sauvegarde de la nuit l'identifiant
de celle du témoin (…0907). Le service, dont les réponses sont éprouvées contre le contrat, rend
désormais les commandes de chaque sauvegarde (`waterfall.api.backups`, une sauvegarde courant de
sa mise en file à la fin de sa tâche, vérification comprise) et la longueur du téléchargement ;
il ne refuse pas encore par les 409 nommés de `startBackup` et de `downloadBackup` : relevé par
la reprise, reporté à EP-15 (#1035). Les exemples de la mise en file d'une sauvegarde et d'une restauration,
écrits des deux côtés, sont ceux d'EP-14, que l'univers témoin enchaîne (14 h 04 et
14 h 04 min 30 s) ; la seconde dit en plus la maintenance que la sonde de vie suit (#604).

**Les règles d'EP-03, appliquées aux opérations d'EP-14.** `make lint-openapi` a relevé
`getStructureMergeReport` (L42s), sans 503, et `setDefaultCalendar`, dont le corps du compteur
(L42r) n'avait pas de 400 ; le 422 de celle-ci dit aussi le compteur refusé. Les autres opérations
d'EP-14 ont reçu leurs 400, 422 et 503 de la fusion même, EP-03 les ayant écrits sur les opérations
qu'elles complètent ; les codes de rôle (L42r) et le libellé d'un calendrier exigent un caractère
qui n'est pas un blanc. `openChunkedUpload` publiait la borne de `size_bytes` sans dire son refus,
que la règle d'EP-14/L42r (`test_mockbounds.py`) exige : son 422 le dit, avec l'exemple
`chunked_upload_size_out_of_range`. `UNKNOWN_ORG_NODE`, ajouté des deux côtés, n'est plus qu'une
fois au catalogue.

**Les identifiants des exemples.** Les deux EPIC avaient pris les mêmes numéros de corrélation
(1040 à 1053) : ceux d'EP-03, qu'aucun texte ne cite, passent à 1155–1166 (#1007 demande une règle
d'attribution) ; deux tâches d'EP-03 (`task_restore_backup_newer_version`,
`task_interrupted_by_restore`) prennent les identifiants libres …0945 et …0946, la première mise en
file à 14 h 08, et la lecture des comptes (`identity_sync_queued`, `identity_sync_succeeded`) à
14 h 03 min 30 s : chaque tâche à son instant (`test_mockuniverse.py`).

## Le lotissement en lots, postes et livrables (EP-15/US-0450)

**Le lotissement découpe la commande en lots, qui contiennent des postes, qui contiennent des
livrables** (C-350, WF-PRJ-0020 : « Le lotissement découpe la commande en lots, chaque lot contenant
des postes, chaque poste contenant des livrables »). La spécification inversait les deux premiers
niveaux, et le contrat l'avait suivie (#1054). Les identifiants gardent leur sens, comme le tableau
du §4.4.1 le dit désormais — « Lot, Poste, Livrable — work_package, order_item, deliverable » — :
`WorkPackage` désigne toujours un lot et `OrderItem` un poste ; c'est leur imbrication qui s'inverse
(décision 2 de #1054). `WorkBreakdown` et `WorkBreakdownReading` portent `work_packages` au
niveau 1, chaque lot ses `order_items`, chaque poste ses `deliverables` ; `WorkBreakdownKind` liste
`[work_package, order_item, deliverable]`, dans l'ordre des niveaux, et les pointeurs des refus de
`setWorkBreakdown` suivent (`/work_packages/<i>/order_items/<j>/…`). Chaque règle reste attachée à
son niveau : « la suppression d'un lot emporte ses postes » (WF-DAT-0080), « lorsque le lot d'un
poste est rattaché, la tâche de ce poste se trouve dans le sous-arbre de la tâche de ce lot »
(WF-PLA-0170), et le squelette engendre la récapitulative d'un poste sous celle de son lot
(WF-PRJ-0030). Écarté : échanger les identifiants avec les noms, `order_items` au niveau 1, qui
ferait lire « poste » là où le code dit `work_package` et changerait le sens de chaque rattachement
déjà écrit.

**Ce qui s'attache à un niveau le suit, nom compris** (défaut n° 10 du guide : un nom qui dit autre
chose que la cause). Le total par niveau de WF-DEV-0060 est celui des lots, au niveau 1 :
`EstimateIndicators.by_order_item` devient `by_work_package`, et son motif
`order_item_without_task` devient `work_package_without_task` (« un lot sans tâche rattachée est
présenté sans total »). La règle du sous-arbre prend le code `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, à la
place de `WORK_PACKAGE_OUTSIDE_ORDER_ITEM`, et ses paramètres `params.work_package_task` — la tâche
du lot — et `params.order_item_tasks` — celles des postes qui en sortiraient —, partout où elle
refuse : `updateTaskFacet`, `createNode`, `moveNodes`, l'échec de `mergeCostStructure`, les
`refusals` de `ImportReport` et de `StructureMergeReport`, `PasteRejection`. Écarté : garder les
codes et les noms d'ancienne lecture avec une description inversée. Les clés des deux catalogues
qui nomment un niveau suivent : `errors.ORDER_ITEM_OUTSIDE_WORK_PACKAGE`,
`enums.NotComputableReason.work_package_without_task`, `enums.WorkBreakdownKind` dans l'ordre des
niveaux ; « poste » au sens du poste de travail ou d'un rôle de ressource ne bouge pas.

**Chaque lot et chaque poste lus disent la tâche qui les porte** (#802 ; WF-PLA-0170 : « un lot ou
un poste n'y est porté que par une tâche à la fois »). `WorkPackageReading` et `OrderItemReading`
portent `attached_task`, exigé, `AttachedTask` — le nœud et le libellé de la tâche de la structure
principale de la révision en cours qui porte l'élément, comme les refus du rattachement nomment une
tâche — ou nul : l'écran qui supprime un lot ou un poste ne confirme que ce qui est porté, et nomme
la tâche qui perdra son rattachement. Un livrable n'en porte pas : aucune tâche ne porte un
livrable. L'écriture ne le porte pas, comme `is_match` : un renvoi de la lecture le laisse. Écarté :
un booléen `is_attached`, qui obligerait l'écran à relire le planning pour nommer la tâche.

**Les exemples suivent le témoin renommé** : son lot 711, « Lot 1 », porté par la récapitulative
« Poste de commande », son poste 712, « Poste 1.1 », qu'aucune tâche ne porte, et le livrable 713 ;
le poste 716, « Poste 1.2 », ajouté par `work_breakdown_entered`. `work_breakdown_work_packages`
devient `work_breakdown_order_items` (`kinds=order_item`, les postes sous leur lot), et les variantes
`task_attach_outside_order_item`, `task_merge_outside_order_item`, `nodes_move_outside_order_item`
deviennent `…_outside_work_package`, leurs noms d'exemple aussi (`outside_work_package`,
`merge_outside_work_package`). Exemples ajoutés ou repris pour `updateTaskFacet` (#817 point 2a,
#819 points 9 et 10) : `task_attached`, engendré, le succès d'un rattachement — le jalon
« Réception usine » porte le poste 1.1, une feuille sous la récapitulative qui porte le lot ;
`task_attach_refused` refuse désormais sur `/work_package_id` le lot déjà porté par « Poste de
commande » ; `task_attach_exclusive` refuse `WORK_BREAKDOWN_ITEMS_EXCLUSIVE` sur `/order_item_id`,
le scénario que le front produit : une grille lue avant que la récapitulative porte son lot, qui
envoie le poste sans mettre le lot à nul.

**Ce que ces décisions remplacent en partie**, une mention le disant à sa place : « Le devis dit son
écart à la référence et ses totaux par poste » (#160) ; « Toute tâche porte son rattachement au
lotissement » (#411) ; « Le lotissement se cherche sur ses libellés et se filtre par nature »
(#560) ; et, d'EP-14, « Un lot rangé sous un autre poste retire le rattachement de sa tâche, sans
refus », « Une fusion qui sortirait la tâche d'un lot du sous-arbre de celle de son poste échoue en
nommant les tâches », « Le compte rendu d'un import nomme le poste ou le lot qui perd sa tâche »
(#586), « Chaque élément d'une lecture du lotissement dit s'il est retenu » (#574), « Un fichier
d'import rejeté entier », « Un poste sans tâche rattachée est présenté sans total » (#771) et « Les
tâches du refus d'un lot hors de son poste sont nommées par leur libellé » (#775),
« Une lecture filtrée n'a pas de compteur » (revue du lot, EP-02/L42f) et la liste des exemples que
`mocklists` engendre (EP-02/L42f). Leur texte est gardé pour l'histoire.

## La structure lue, sa phase et son diff (EP-15/US-0460, US-0480, US-0500)

**Chaque structure dit ses commandes de saisie** (C-358, #1067 ; WF-DEV-0050, WF-RAE-0040,
WF-IHM-0090). En chiffrage, le planning et le devis travaillent la structure principale ; en
réalisation, le planning et le reste à engager, la grille de devis restant lisible en lecture
seule. Le serveur ne refuse aucune écriture selon la grille qui l'envoie — une tâche créée sur la
structure principale d'un projet En cours est la même écriture depuis le planning et depuis le
reste à engager —, si bien que la lecture seule du devis est une règle de présentation, que le
serveur doit dire et que le front ne déduit pas de l'état du projet. `CostStructure` porte
`available_commands`, exigé, une liste de `StructureCommandAvailability` sur une énumération
nouvelle, `StructureCommand` : `edit_planning`, `edit_estimate`, `edit_remaining`, chacune gardée
par la permission de la commande de même nom de la révision, présente ou absente comme elle. Sur
la structure principale, `edit_estimate` manque de `project_before_in_progress` dès En cours, ou
dans un état terminal — la condition existait pour la probabilité de gain (#590), et dit le même
fait — ; `edit_remaining` manque de `project_in_progress` hors de l'état En cours, avant comme
après — la condition existait aussi, pour la clôture et l'import des coûts réels : elle est
nouvelle pour cette commande, sans valeur nouvelle de `CommandCondition`. Sur un différentiel et
sur le devis propre d'un risque, `edit_planning` et `edit_estimate` n'ont pas de condition de
phase (WF-DEV-0050), et `edit_remaining` n'est jamais listée (WF-RAE-0040 : seule la principale).
La condition de phase vient d'abord, puis les conditions d'état de la révision — `revision_draft`,
`no_background_task_running`, `project_not_terminal` — telles que la commande de même nom de la
révision les nomme : la condition propre à la commande d'abord, comme `update_win_probability`
(« Sur un projet clos, `project_not_terminal` vient en dernier » ; réécrit par US-0702/L3, #1657 :
sur un projet clos, aucune n'est listée). Les commandes de la révision
(`RevisionCommand`) ne changent pas, et gardent ce qui ne lit pas une structure : le squelette, le
marquage, les exports, les risques. Écartés : une condition sur `RevisionCommand.edit_estimate`,
qui aurait fermé avec la principale le devis propre d'un risque et le différentiel ; des
`editable_fields` vides sur le devis d'un projet En cours, qui ne disent rien de la création ni de
la suppression ; lire `Project.state`, que le front ne déduit pas. Les exemples `structures`,
`structures_amendments` et `structures_without_tasks`, écrits à la main, disent leurs commandes ;
`test_mockphase.py` les confronte à la révision et au projet qu'ils lisent.

**L'inscription aux chronologies est un champ que la tâche accepte** (#1065 ; WF-PLA-0060).
`EditableField` gagne `task.tracking`, que nomme toute tâche de la structure principale,
récapitulative, feuille ou jalon, en dernier, et aucune autre : la grille de planning offre le
sous-menu des chronologies d'après le nœud, sans le déduire de la structure lue. L'écriture reste
`setNodeTracking`, sous la commande de saisie du planning, comme les autres champs de la tâche :
`editable_fields` dit ce que le nœud accepte, la commande ce que l'appelant a le droit d'écrire.
Écarté : une commande propre à la tâche, qui doublerait une liste que le nœud porte déjà.

**Une ligne d'une tâche démarrée ne quitte pas un sous-projet qui a reçu des coûts réels** (C-359,
#1066, #1067 ; WF-PRJ-0050). `updateEstimateLine` le refuse par 422 `VALIDATION_FAILED`, `fields`
sur `/subproject_id`, motif nouveau `SUBPROJECT_HAS_ACTUAL_COSTS`, `params.subproject` nommant le
sous-projet quitté par son identifiant et son libellé — « est refusé et nomme ce sous-projet » —,
et la ligne ne nomme pas `estimate_line.subproject_id` dans `editable_fields` : la grille n'offre
pas d'avance un choix qu'elle refuserait. Le champ n'est pas pour autant calculé, et ne va pas dans
`computed_fields`. « Démarrée » s'entend comme le complément de « non démarrée », la seule à
pouvoir changer de sous-projet : une tâche terminée retient ses lignes comme une tâche démarrée. Le
pointeur est celui du corps de `updateEstimateLine`, `EstimateLineUpdate`, plat comme pour
`/payment_delay_days` et `/cost_category_id` — la conception d'EP-15 l'écrivait
`/estimate_line/subproject_id`, le chemin d'un `NodeCreate`, que ce refus ne concerne pas. Écarté :
un 409 `STATE_FORBIDS_OPERATION`, qui aurait dit l'état d'un objet là où c'est la valeur d'un champ
qui est refusée. Exemples engendrés (`mockwrites`) : `estimate_line_subproject_changed`, la ligne
« Mise en service sur site », d'une tâche non démarrée, passée du Poste de commande aux Essais et
mise en service ; `estimate_line_subproject_has_actual_costs`, la main-d'œuvre du câblage, démarré,
refusée hors du Poste de commande, qui a reçu la facture des écrans. Les deux sous-projets du témoin
ayant reçu des coûts réels, les lignes des tâches démarrées ou terminées qui portent l'un d'eux ne
nomment plus le champ, dans le cœur comme dans la structure de mille tâches.

**La création d'un nœud ne dépend pas de la grille qui l'envoie** (K9 de la conception d'EP-15 ;
WF-DEV-0050, WF-RAE-0040, WF-RAE-0050). La description de `createNode` le dit : aucun refus de
phase, la phase étant une commande de la structure ; une tâche créée sans mode ni durée — depuis la
grille de devis ou de reste à engager, qui ne les présentent pas — est une feuille en mode
automatique, d'un jour, sans prédécesseur ; une ligne ajoutée après la référence porte un montant
budgété nul. La phrase « une tâche ajoutée après la référence porte un montant budgété nul » devient
celle d'une ligne : une tâche n'a de montant que la somme de ses lignes.

**Un exemple ajouté par un lot de front, hors conception : `structures_estimator`** (US-0460/L3,
#1094 ; WF-IHM-0090, WF-DEV-0050). Aucun exemple existant ne dit la structure d'un estimateur — il
n'a ni `planning.write` ni `remaining.write`, si bien que la principale ne liste que
`edit_estimate`, disponible. L'exemple se lit sur la révision `revision_without_tasks` et sa
structure principale, d'un projet qui n'est pas En cours, où le devis se saisit, comme
`structures_without_tasks` ; il ne porte pas ceux du témoin, dont le projet est En cours. Il sert
aux tests de l'écran de devis : l'estimateur y saisit les lignes, non le libellé d'une tâche, qui
est au planning.

## Les gestes de structure et la saisie des tâches (EP-15/US-0460, US-0470, US-0480)

**Chaque geste de structure et chaque saisie d'une tâche a son exemple de succès** (K3 de la
conception d'EP-15, #1056, #1073, #1065 ; WF-IHM-0040). Les grilles d'US-0460 à US-0480 créent,
déplacent, mettent en retrait et suppriment, saisissent le mode, les dates, la durée et la
description d'une tâche, ses prédécesseurs et ses inscriptions ; le contrat ne donnait l'exemple que
de quelques-unes de ces écritures. Ils sont engendrés, comme les autres écritures de grille, par la
différence de deux lectures du témoin (`wftools.mockgestures`, qui reprend `wftools.mockwrites`) :
`node_created`, une tâche créée à côté du dossier de conception, son libellé seul envoyé — une
feuille automatique d'un jour, sans prédécesseur, à la date de début de planning, non démarrée
(K9) ; `node_created_child`, une sous-tâche créée sous elle, qui en fait sa récapitulative — elle
suit la première, la structure à sa troisième version (#421) — ; `estimate_line_created`, une ligne
de matériel sous la mise en service, au budgété nul (WF-RAE-0050) ; `nodes_moved`, une sélection de
deux lignes d'une tâche tirée autour du cœur déplacées sous la suivante ; `nodes_indented`,
l'installation sur site mise en retrait sous le poste de commande — une mise en retrait est un
déplacement sous la tâche au-dessus, sans opération propre — ; `node_summary_deleted`,
l'installation, non démarrée, supprimée avec ses subordonnées, leurs lignes et leurs liaisons
(Vérif de WF-PLA-0070 : « le devis diminue d'autant ») ; `task_mode_changed`, la mise en service
passée en mode manuel à ses dates, son prédécesseur devenu critique, puis `task_dates_entered`, ses
dates saisies en 2027, qui la suit ; `task_duration_entered`, une durée saisie en semaines et rendue
dans cette unité (WF-PLA-0160) ; `task_description_entered` ; `predecessors_entered`, deux liaisons
de types différents, le décalage en semaines ; `node_tracked`, la revue de conception inscrite à la
chronologie « Revue client ». Un nœud créé est rendu à sa première version, et les anciens ancêtres
d'un nœud déplacé avec ses nouveaux, comme `NodesWritten` le dit déjà. Le témoin gagne ce qu'il faut
pour les engendrer : une tâche porte l'unité de sa durée, une description et ses inscriptions quand
une écriture les lui donne. Chaque nœud écrit l'est par ce seul exemple à sa version : les nœuds
créés sont les tâches 581 et 582 et la ligne 583. La règle de #421 — deux exemples ne rendent
jamais un même nœud, à une même version, avec deux contenus — vise les nœuds écrits, `nodes`, et
non les `ancestors` : un exemple qui en suit un autre (`following`) fait évoluer ses ancêtres sans
changer leur version, puisqu'il ne les écrit pas. Ainsi le nœud 581, feuille à sa version 1 dans
`node_created`, revient à la même version, devenu récapitulative, parmi les ancêtres de
`node_created_child`.

**Une date calculée envoyée est refusée sans paramètre** (WF-PLA-0020, WF-IHM-0030).
`task_date_computed_refused` : la fin du montage, en mode automatique, envoyée à `updateTaskFacet`,
refusée par 422 `VALIDATION_FAILED`, `fields` sur `/finish`, motif `COMPUTED_VALUE`, comme le
contrat le disait. Ce dont la valeur dépend se lit par `getComputedValueDependencies`, que la grille
appelle déjà : le refus ne le recopie pas.

**Les refus des liaisons sont des 422, et la boucle nomme ses tâches** (WF-PLA-0030, WF-PLA-0040 ;
#788). `setPredecessors` déclarait `LINK_CYCLE` et `LINK_FORBIDDEN` sous un 409, quand le
catalogue des codes les range parmi les 422 des règles métier et que la conception d'EP-15 dit « le
422 `LINK_CYCLE` » : ce n'est pas l'état d'un objet qui refuse, c'est la valeur envoyée. Le 409 de
l'opération reprend la réponse commune des conflits d'état. `LINK_CYCLE` porte `params.cycle`, les
tâches de la boucle, chacune par son nœud et son libellé, de la tâche saisie au prédécesseur envoyé
qui la suit déjà, chacune précédant la suivante — « la raison en est nommée à l'utilisateur »
(Vérif de WF-PLA-0030), la grille, filtrée, pouvant ne pas les lire ; `LINK_FORBIDDEN`, la liaison
d'une récapitulative et de sa subordonnée, n'a pas de paramètre, son code disant la raison et la
conception n'en prévoyant pas. Exemples : `predecessors_cycle_refused`, la réception usine donnée à
suivre la mise en service, qui la suit par le montage — trois tâches, dans l'ordre des liaisons — ;
`predecessors_forbidden`, le montage donné à suivre sa propre récapitulative. Écartés : garder le
409, contre le catalogue ; un refus par champ, `/predecessors/<n>`, qui localiserait la liaison mais
pas la boucle, faite de liaisons déjà enregistrées.

**Un déplacement ou une mise en retrait refusent les mêmes liaisons** (#1164, tranché par l'auteur
le 2026-10-19, et #1167 ; WF-PLA-0030, WF-PLA-0040). Une récapitulative couvre ses subordonnées : ce
qui la précède les précède, ce qui la suit les suit. Mettre en retrait B sous A quand A est le
prédécesseur de B fait de A la récapitulative de B avec la liaison A → B, celle que WF-PLA-0030
refuse ; déplacer une tâche sous une autre qu'elle suit déjà par une chaîne de liaisons ferme une
boucle à travers la hiérarchie. `moveNodes` déclare donc `LINK_FORBIDDEN`, sans paramètre comme pour
`setPredecessors`, et `LINK_CYCLE`, `params.cycle` nommant les tâches de la chaîne, de la
récapitulative qui recevrait le nœud — ou de l'un de ses ancêtres — à la tâche reçue ou à l'une de
ses subordonnées, ou dans l'autre sens, chacune précédant la suivante, la plus courte rendue. Une
chaîne d'une seule liaison est la liaison interdite : le code le plus précis l'emporte. Exemples,
engendrés par `wftools.mockgestures` : `nodes_indent_forbidden`, la mise en service mise en retrait
sous le montage, la tâche au-dessus d'elle et son prédécesseur ; `nodes_move_cycle_refused`,
« Documentation 1.1.7 », tâche tirée autour du cœur, déplacée sous « Préparation 1.1.1 », qu'elle
suit par « Réalisation 1.1.4 ». `mockdating.schedule` refuse les deux structures que ces gestes
laisseraient, comme celle que `predecessors_cycle_refused` laisserait : le faux back ne date pas ce
que le serveur refuse. `createNode` ne déclare ni l'un ni l'autre (#1167, tranché par l'auteur le
2026-10-19) : son corps ne porte pas de liaison (`TaskFacetWrite`, sans `predecessors`), et créer un
enfant sous une tâche ne lie ni elle ni l'un de ses ancêtres au nœud créé — les deux refus y sont
inatteignables. #1164 les y étendait ; une création qui portera des liaisons les déclarera avec
elles. Écartés : nommer la liaison interdite par un paramètre, que la conception ne prévoit pas plus
que pour `setPredecessors` ; un 409, pour la raison dite plus haut.

**L'horizon refuse les saisies qui déplacent une date** (WF-PLA-0150 : « une saisie, un import ou une
fusion qui la porterait au-delà est refusé, et le refus nomme la tâche en cause » ; #788, part
« saisies »). `PROJECT_HORIZON_EXCEEDED`, code du rejet entier d'un import (EP-14/L42s), devient
aussi le refus, par 422 sans `fields`, de `updateTaskFacet`, `setPredecessors`, `createNode` et
`moveNodes` ; `params.task` nomme la tâche que la saisie écrit — celle dont la durée, les dates ou
les prédécesseurs se saisissent, celle que la création ajouterait, par le libellé envoyé et son
nœud nul comme une tâche qu'un fichier crée, la tâche déplacée ou celle qui reçoit la ligne
déplacée —, pas la dernière tâche de la structure qu'elle repousse : c'est la cellule saisie que la
grille marque (Vérif : « le déplacement d'une tâche … est refusé, et la tâche est nommée »). Un
refus sans `fields`, parce que la cause n'est pas une valeur hors de ses bornes mais la durée du
projet entier. Exemples : `task_horizon_exceeded`, la fin des pupitres opérateurs, manuels, saisie
quinze ans et un jour après le début du projet, le 2 mars 2026 — le Vérif mot pour mot — ;
`predecessors_horizon_exceeded`, la mise en service décalée de deux cents mois de travail ;
`node_create_horizon_exceeded`, une tâche créée de deux cents mois. `moveNodes` n'a pas d'exemple :
un déplacement ne change une date qu'en changeant le calendrier d'une tâche, et aucun déplacement du
témoin ne porte si loin. Les refus sont engendrés avec les succès, pour que leurs libellés soient ceux
des lectures ; la conception d'EP-15 les disait écrits à la main. La part « fusion » de #788 — le
refus de l'horizon et du cycle par `mergeCostStructure` et son compte rendu — reste à EP-16.

*Complété par EP-16/US-0640/L3 : la fusion échoue sur une boucle et sur l'horizon, son compte rendu
le dit, section « La fusion : cycle, horizon, et fusion sans révision en cours ».*

**Le suivi temps/temps d'une tâche qui n'est pas un jalon n'a pas encore d'exemple.** La conception
nomme `node_tracking_milestone_refused`, un 422, sans dire le code ni le pointeur, que le catalogue
n'a pas : ce lot ne l'invente pas, et le refus reste à trancher avant le lot d'écran qui le
dit.

**Le collage et l'import ne déplacent pas une ligne retenue par son sous-projet** (C-359, #1152 ;
WF-PRJ-0050, WF-IHM-0050, WF-INTF-0100, WF-INTF-0120 ; décision de l'auteur du 2026-10-19). Une
ligne dont la tâche est démarrée ou terminée, et dont le sous-projet a reçu des coûts réels, ne
nomme plus `estimate_line.subproject_id` dans `editable_fields` depuis US-0460/L1 : par la règle
générale du collage, sa cellule aurait été refusée par `FIELD_NOT_ACCEPTED`, un code qui ne dit pas
la cause (défaut n° 10 du guide). Elle l'est par `SUBPROJECT_HAS_ACTUAL_COSTS`, le motif de
`updateEstimateLine`, avec le même `params.subproject` (`subproject_id`, `label`), sur la colonne
`subproject` (`PasteRejection`) ; au compte rendu d'un import, la ligne est rejetée de même par son
rang (`ImportRejection`) — placée, dans un reste à engager, dans l'onglet d'un autre sous-projet ou
dans « Hors sous-projet », ou portant, dans un devis, un autre sous-projet ou une cellule vide —, et
le compte rendu « nomme ce sous-projet » (WF-INTF-0120) : celui que la ligne ne peut pas quitter, ce
que le refus de `updateEstimateLine` nomme déjà. La spécification ne dit pas la forme du motif : ce
lot prend la plus proche des refus existants, le code et les paramètres que la ligne recevrait
saisie, comme `ORDER_ITEM_OUTSIDE_WORK_PACKAGE` au collage et `TASK_WITHOUT_WORKING_HOURS` à
l'import. Une cellule ou un onglet qui nomme le sous-projet de la ligne ne la déplace pas, et n'est
pas refusé : un bloc ou un fichier repris d'un export porte les sous-projets tels qu'ils sont. Une
cellule vide se lit autrement au collage et à l'import : collée, elle n'écrit rien, comme toute
cellule vide (`PastePreview`), et n'est pas refusée ; importée dans la colonne d'un devis, elle
laisserait la ligne hors sous-projet — ce qu'un reste à engager dit par son onglet « Hors
sous-projet » —, et la ligne est rejetée. Une ligne d'une tâche non démarrée change de sous-projet, et le compte rendu le présente comme un écart,
`fields` à `subproject`. Exemples engendrés (`wftools.mockexchanges`), jugés sur la lecture du
témoin comme le serveur les juge : `paste_plan_subproject_held`, deux sous-projets collés depuis la
main-d'œuvre du câblage, démarré — l'un refusé, l'autre, celui des borniers, le leur, accepté — ;
`import_remaining_subproject_held`, un reste à engager dont l'onglet « Essais et mise en service »
porte la mise en service sur site, non démarrée, qui en change, et la main-d'œuvre du câblage,
rejetée, le Poste de commande nommé. Écarté : garder `FIELD_NOT_ACCEPTED` au collage, qui aurait fait
dire à la grille « ce champ ne s'écrit pas » d'une ligne que la saisie refuse pour une autre raison.

**Une ligne rejetée d'un import est désignée par son onglet** (#1162, tranché par l'auteur le
2026-10-19 ; WF-INTF-0080, WF-INTF-0180). ANNEXE B place chaque lot d'un devis et chaque
sous-projet d'un reste à engager dans un onglet : le rang seul, `ImportRejection.row`, ne disait pas
lequel, et deux lignes de deux onglets peuvent avoir le même rang ; l'utilisateur doit pouvoir
retrouver dans son fichier la ligne que le compte rendu rejette. `ImportRejection` gagne `sheet`,
le nom de l'onglet tel que le fichier le porte — le lot ou le sous-projet, ou « Hors lot » et « Hors
sous-projet », que Waterfall fixe sans égard à la langue (WF-INTF-0180) —, nul pour un fichier à un
seul onglet, un planning MS Project ou une extraction de coûts réels. Le champ n'est pas exigé :
un compte rendu sans onglet reste lisible. L'exemple engendré `import_remaining_subproject_held` le
renseigne, l'onglet « Essais et mise en service », et son résumé dit la ligne 3 de cet onglet.
L'exemple écrit à la main `import_analysed`, un devis Excel dont deux lignes sont rejetées, ne le
porte pas encore : il n'est pas réécrit ici, mais l'a été depuis, par US-0500/L1. Le contrat
garde sa citation de WF-INTF-0100, dont le texte complété attend son intégration par l'auteur
(#1166).

**L'import du devis est refusé sur la structure principale d'un projet En cours** (C-358, #1153 ;
WF-INTF-0100 : « l'import du devis est refusé sur la structure principale, en nommant la
condition »). `openImport` le refuse par 409 `STATE_FORBIDS_OPERATION`,
`params.missing_condition` à `project_before_in_progress` — la condition que la structure principale
nomme déjà à la saisie de son devis (`StructureCommand.edit_estimate`, K2) —, et rien n'est analysé ;
`applyImport` la nomme de même pour un devis analysé avant le passage à En cours, l'état étant
revérifié à l'exécution (WF-ARC-0100). La spécification dit « en nommant la condition » sans la
nommer : ce lot reprend celle qui existe, plutôt qu'une condition nouvelle qui dirait la même chose.
`ProjectCommand.import_estimate` reste disponible sur un projet En cours, l'import restant ouvert
sur un différentiel et sur le devis propre d'un risque : le front lit la commande de la structure
visée. Exemple engendré : `import_estimate_main_in_progress`, sa condition lue à la structure
principale de `structures`. Écartés : un motif au compte rendu (`ImportReport.refusals`), qui aurait
lu le fichier pour refuser ce que l'état du projet suffit à refuser ; une condition sur
`import_estimate`, qui aurait fermé l'import du différentiel avec celui de la principale. Les
descriptions d'`openImport`, `getImport` et `applyImport` citent WF-INTF-0100 et, pour les deux
premières, WF-INTF-0120.

## La place d'un nœud créé ou déplacé (EP-15/US-0460/L3b, #1183)

**Une création et un déplacement désignent leur place par le nœud qu'ils suivent** (décision de
l'auteur du 2026-10-20, #1183, relevée à la revue de US-0460/L3b). Le contrat ne disait pas le sens
de `position` à l'écriture — un index parmi les frères, à partir de 0 ou de 1, ou une clé d'ordre —,
et les exemples se contredisaient : l'unique racine de `nodes_estimate` portait 1, son index étant
0. Une grille filtrée ne lit qu'une partie des frères d'un nœud : elle ne peut pas compter un rang,
seulement nommer le nœud qu'elle montre. `NodeCreate` et `NodeMove` portent donc `after_node_id`,
le nœud après lequel se placer parmi les frères sous `parent_id` : nul, le nœud se place en tête de
son genre ; absent, à la fin de son genre, ce que font les gestes existants — une sous-tâche, une
ligne sous une tâche, un déplacement sous une autre tâche (`node_created`, `estimate_line_created`,
`nodes_moved`, `nodes_indented`) ; le paragraphe suivant dit les deux genres, les lignes d'une
tâche puis ses sous-tâches. Les nœuds déplacés se suivent dans l'ordre de `node_ids`. `position`
n'est plus écrit.

**Les lignes d'une tâche précèdent toujours ses sous-tâches**, à la création comme au déplacement
(relevé à la revue du contrat de L3b, à valider avec le reste de #1187). Une ligne et une tâche
sont frères sous une même tâche, et `after_node_id` peut nommer un frère de l'autre genre ;
« absent, en fin » ne disait pas où va une ligne sous une tâche qui a des sous-tâches. La règle
retenue est celle que `Node.position` lisait déjà et que suit le témoin, `wftools.mockcore`, qui
rend les lignes d'une tâche puis ses subordonnées : nul, une ligne se place en tête des lignes,
une tâche en tête des sous-tâches ; absent, une ligne après la dernière ligne, une tâche après la
dernière sous-tâche ; un `after_node_id` d'un autre genre se replie sur la frontière entre lignes
et sous-tâches — une ligne envoyée après une sous-tâche se place après la dernière ligne, une
tâche envoyée après une ligne en tête des sous-tâches. Une sélection de `moveNodes` qui mêle
lignes et tâches applique la règle à chaque nœud, dans l'ordre de `node_ids` : le premier nœud de
chaque genre prend la place que la règle lui donne après `after_node_id`, chacun des suivants se
place après le précédent de son genre. Écartés : refuser un `after_node_id` de l'autre genre, un
refus de plus pour une place que la règle sait dire ; mêler lignes et sous-tâches dans un ordre
libre, que ni la lecture ni le témoin ne connaissent. Exemple engendré par
`wftools.mockgestures` : `estimate_line_created_after_subtask`, une ligne créée sous le poste de
commande, qui n'en porte aucune, après la réception usine, sa dernière subordonnée — elle devient
son premier enfant, au rang 1, avant le câblage des armoires.

**Un `after_node_id` qui n'est pas un frère est refusé** : 422 `VALIDATION_FAILED`,
`fields[].pointer` à `/after_node_id`, motif nouveau `NODE_NOT_SIBLING`, sans paramètre — la grille
nomme le nœud qu'elle a envoyé —, rien n'étant écrit. Est un tel nœud celui d'un autre parent, l'un
des nœuds déplacés, ou un nœud que la structure n'a pas. Écartés : `UNKNOWN_TASK`, qui dit une tâche
inconnue alors que le nœud suivi peut être une ligne, et connu sous un autre parent ;
`VALUE_OUT_OF_RANGE`, qui dit une borne. Exemples engendrés par `wftools.mockgestures`, aux
corrélations 1178 et 1179 : `node_create_after_not_sibling` (une tâche créée sous les études après
le câblage des armoires, du poste de commande) et `nodes_move_after_not_sibling` (les borniers
déplacés sous la mise en service après le raccordement des borniers, qui reste sous le câblage),
celui-ci premier sous le 422 de `moveNodes`, à la place de `nodes_move_position_out_of_range`.

**`Node.position` reste lu, en lecture seule** : le rang du nœud parmi les frères de son parent —
ses tâches et ses lignes, dans l'ordre du plan —, à partir de 1. Le témoin le portait à partir de 0,
lignes et sous-tâches comptées à part : `wftools.mockcore` le compte désormais à partir de 1, les
lignes d'une tâche puis ses subordonnées, et `make mock-data` réécrit les lectures et les écritures
qui le portent ; l'exemple écrit à la main `skeleton_generated` suit.
`test_positions_count_the_siblings_of_one_parent_from_one` (`tools/tests/test_mockstructure.py`) le
tient. Le front envoie `after_node_id` : le nœud actif pour « Insérer au-dessous » et pour une
ligne sous une ligne, rien pour une sous-tâche et une ligne sous une tâche, qui vont en fin
(`bodyOf`, `structure-rules.ts`) ; `errors.NODE_NOT_SIBLING` a sa phrase dans les deux catalogues.

## Le diff d'un différentiel, la comparaison en arbre, l'avenant 2 du témoin (EP-15/US-0500/L1)

**Le serveur rend l'écart de chaque nœud, le front ne calcule rien** (C-361, #1060 ; WF-REV-0080,
WF-REV-0100 ; partie K2 de la conception d'EP-15). `Node` gagne `difference`, sur une énumération
nouvelle `NodeDifference` — `added`, `removed`, `modified`, `unchanged` —, et `changes`, l'énumération
qu'avait `ComparedNode.changes`, nommée `NodeChange`, `parent` compris. Ils sont rendus sur deux
lectures, toujours, que `fields` les nomme ou non : la lecture d'un différentiel (`listNodes`), par
rapport à la structure principale de sa révision, et la comparaison de deux révisions, par rapport
à la révision de base ; nuls, ou omis, sur la principale et sur le devis propre d'un risque, qui ne
se lisent par rapport à rien. Les nœuds sont rapprochés par la lignée. Un nœud retiré est rendu à la
place qu'il avait, après le dernier des frères qui le précédaient et que l'arbre rendu garde sous le
même parent, en lecture seule (`editable_fields` vide) ; il occupe sa ligne, si bien que
`row_number` et `position` comptent l'arbre rendu, nœuds retirés compris, et qu'un prédécesseur est
nommé par la ligne où il est rendu. Un nœud déplacé est rendu une fois, à sa place nouvelle,
`parent` parmi ses `changes`. Une tâche est `modified` par ses propres valeurs — dates, durée,
avancement, parent —, une ligne par ses montants ou son parent, et une tâche aussi par son seul
contenu, `changes` vide : une ligne ou une subordonnée ajoutée, retirée ou modifiée sous elle, ou
déplacée d'elle — la marque « M » d'une récapitulative dont le contenu change, que l'US-0500 veut.
Les totaux d'une lecture d'un différentiel ne comptent pas les nœuds retirés. Les tâches modifiées
par leurs propres valeurs se comptent sur un `changes` non vide, celles modifiées par leur seul
contenu ayant un `changes` vide (relecture 1) ; les descriptions de `NodeDifference`, de
`Node.row_number` et de `Node.position` le disent, et que les nœuds retirés comptent dans le rang et
la ligne. Écartés : le diff
calculé par le front, en lisant deux structures, contraire au principe que le front ne déduit rien
(WF-ARC-0020) ; un nœud retiré rendu à part, en fin de lecture, qui ne se lirait pas « à sa place ».

**`RevisionComparison` rend l'arbre comparé** : `nodes`, la structure principale de la révision
comparée dans l'ordre du plan, sans pagination, comme `listNodes`, chaque nœud avec sa marque et les
champs que `fields` nomme — `compareRevisions` prend `fields`, le paramètre `NodeFields` partagé avec
`listNodes`, et déclare son 400 —, à la place de `added`, `removed` et `changed`. `amount_deltas`
reste. `ComparedNode` disparaît ; ses clés de catalogue deviennent `enums.NodeChange`, et
`enums.NodeDifference` s'ajoute. Une paire identique rend chaque nœud inchangé. L'exemple
`comparison`, engendré, rend l'arbre entier de la référence 101 comparée à l'offre 100 — 5 999
nœuds rendus entiers, puisqu'un exemple sans `fields` les rend tels, 7,4 Mo —, `comparison_identical`
devient engendré, le cœur de l'offre comparé à lui-même, variante déclarée : la structure entière
de l'offre aurait pesé autant que `comparison` pour ne rien montrer de plus.

**L'avenant 2 « reprise des essais » est un différentiel non fusionné de la révision courante 102**
(#791, constat de la relecture 1 d'EP-14/L42s). Il coexistait dans la référence 101 avec l'avenant
1 ; la révision 102, créée d'elle, l'a repris (WF-REV-0100) : `structures` le liste, structure 203,
`edit_planning` et `edit_estimate` disponibles, compteur 2. `wftools.mockamendment` le décrit sur la
structure principale de 102 : sous l'installation sur site, une récapitulative « Essais sur site »
porte la « Reprise des essais de câblage », nouvelle, avec sa ligne, et la « Mise en service »,
déplacée sous elle, liée à la reprise au lieu du montage, allongée à quinze jours et sa ligne à
120 h ; l'« Assistance aux essais de câblage » est retirée du montage. Ses tâches ne portent ni
lot, ni poste, ni inscription, et ne nomment pas `task.order_item_id`, `task.work_package_id` ni
`task.tracking` (WF-PLA-0170, WF-PLA-0060). `wftools.mockdiff` marque l'arbre, pour le différentiel
comme pour la comparaison. Exemples engendrés : `nodes_amendment`, l'installation sur site lue sur
le différentiel (`subtree_of`) ; `structure_merge_report`, devenu une lecture du témoin — les tâches
et la ligne ajoutées, la liaison de la mise en service, sa durée et la charge de sa ligne, la ligne
retirée ; aucune tâche démarrée retirée. Le Vérif de WF-REV-0050 qu'il portait (« Le compte rendu
d'une fusion dont le différentiel retire une tâche démarrée nomme cette tâche comme terminée ») passe
à une variante déclarée, écrite à la main, `structure_merge_report_started_task`, l'ancien premier
exemple (« Avenant 3 — pupitres déportés »). Le déplacement de la mise en service ne se disait pas
au compte rendu, `ImportDifference.fields` ne nommant que des colonnes (`NodeColumn`) ; il s'y dit
depuis par `parent` (#1194, EP-15/US-0490/L1, ci-dessous), avec la liaison et la durée.

**La révision courante offre la fusion** (relecture 1). Puisqu'elle porte l'avenant 2 non fusionné,
`merge_structure` y est disponible, sans condition manquante, dans `revision` et l'item 102 de
`revisions` ; pendant un marquage ou un import (`revision_marking`, `revision_importing`), il ne
manque que de `no_background_task_running`. `revision_without_tasks`, sur le projet créé
aujourd'hui, sans différentiel, garde `unmerged_amendment_exists`.
`test_a_revision_offers_the_merge_and_not_a_differential_iff_it_bears_one_not_merged`
(`tools/tests/test_mockcycle.py`, depuis EP-15/US-0490/L1) tient, sur la révision courante et sur
celle du projet créé aujourd'hui, que la commande est disponible si et seulement si `structures`
liste un différentiel non fusionné, dans les deux sens (#1196). La variante
`cost_curve_amendment`, dont la marche du 10 mars s'appelait « avenant 2 », dit désormais « un
autre avenant » que celui du témoin (`mocktoday.OTHER_AMENDMENT`).

**Un nœud, à une version, n'a qu'un contenu, sur toutes les lectures d'une révision** (#421 étendu,
relecture 1). Les nœuds de l'avenant 2 portaient les identifiants de ceux de la structure principale
qu'ils copient — l'installation sur site, 561 à 566, à la version 1 —, avec d'autres valeurs : deux
lectures rendaient un même nœud, à une même version, sous deux contenus. Ils ont désormais leurs
identifiants à eux, sur une plage dédiée : le nœud 5nn de la principale est 12nn dans le
différentiel, un nœud tiré a sa famille engendrée (`mockids`, `mockamendment.own_id`), et ceux que
l'avenant ajoute vont de 1291 à 1293 ; ils gardent la lignée de la principale, qui les rapproche
(6nn, de 691 à 693 pour les ajoutés), si bien que le compte rendu de la fusion et l'import du devis
de l'avenant (`import_analysed` : 663 retirée, 693 mise à jour), qui nomment des lignées, ne changent
pas. Le parent et les prédécesseurs d'un nœud du différentiel sont nommés par ces identifiants, et
une ligne est numérotée dans l'arbre rendu. La règle : deux exemples ne rendent jamais un même nœud,
à une même version, avec deux contenus — sur les clés que tous deux rendent, une lecture ne rendant
que les champs qu'elle demande —, qu'il s'agisse des lectures d'une structure ou des réponses de
ses écritures (`nodes`). En sont exemptés, nommément : la comparaison de deux révisions marquées
(`comparison`), qui nomme ses nœuds par les identifiants de la révision courante selon la
convention de #287 (C12) ; les variantes contrefactuelles déclarées, dont le résumé s'ouvre par
« Variante contrefactuelle » — `comparison_identical`, `nodes_summaries`, lecture de la variante à
quatre niveaux, et `startable_tasks_milestone`, le Kanban du câblage supposé terminé, une lecture
contrefactuelle et non la suite d'une écriture (#1196) — ; et ce qu'une écriture rend sans l'écrire
(`ancestors`, `rescheduled`, `reinflated`), qui évolue sans changer de version.
`test_two_examples_never_render_one_node_at_one_version_with_two_contents`
(`tools/tests/test_mockversions.py`, où le test des écritures est passé) la tient.

**Le suivi temps/temps d'une tâche qui n'est pas un jalon est refusé** (#1159, décision de l'auteur
du 2026-10-19 ; WF-PLA-0060). `setNodeTracking` le refuse par 422 `VALIDATION_FAILED`,
`fields[].pointer` sur le genre de l'entrée qui le demande, `/entries/<n>/kind`, `n` son rang dans
`entries` à partir de 0, motif nouveau `MILESTONE_REQUIRED`, sans paramètre, rien n'étant écrit ;
`errors.MILESTONE_REQUIRED` a sa phrase dans les deux catalogues. Exemple engendré par
`wftools.mockgestures`, corrélation 1180 : `node_tracking_milestone_refused`, la mise en service
envoyée avec son inscription au comité de pilotage et une entrée au suivi temps/temps, la seconde.

**L'import du devis du témoin vise l'avenant 2** (#1161, décision de l'auteur du 2026-10-19 ; C-358,
WF-INTF-0100). Il visait la structure principale de PRJ-001, En cours, que C-358 refuse
(`import_estimate_main_in_progress`). `import_analysed`, écrit à la main, est réécrit comme l'import
du devis de l'avenant 2, le résumé nommant sa structure par son `structure_id` : ses lignes sont
celles du différentiel (`nodes_amendment`), et ses deux lignes rejetées nomment leur onglet,
« Hors lot », aucune tâche d'un différentiel ne portant de lot (#1168). `imports`, `import_analysing`,
`file_upload`, `task_import_queued`, `task_import_succeeded` et le journal d'audit qui l'applique
(`mockaudit`) suivent son nom de fichier et son résumé ; `imports_page`, qui ne le liste pas, ne
change pas. `test_no_import_of_the_estimate_of_the_witness_aims_at_the_main_structure_in_progress`
(`tools/tests/test_mockuniverse.py`) tient qu'aucun import du devis du témoin ne vise la principale
d'un projet En cours.

**Deux corrections de rédaction** (#1170). La description d'`ImportReport.rejected` dit chaque
ligne « par son rang, et son onglet quand le fichier en a plusieurs », `sheet` étant nul pour un
fichier à un seul onglet. Le résumé d'`import_remaining_subproject_held` écrit « qu'imports », et
tire ses heures des instants de l'import (`mocktext.hour`).

## La comparaison de révisions se lit comme `listNodes` (EP-15/US-0500/L5)

**`compareRevisions` adopte la mécanique de `listNodes`** (décision de l'auteur du 2026-10-20 sur
#1193). L'arbre entier de la comparaison — 5 999 nœuds rendus entiers, un exemple `comparison` de
7,4 Mo (US-0500/L1, ci-dessus) — se lisait autrement que les grilles de la structure ; il se lit
désormais comme elles, et la grille dense, déjà virtualisée, le lira comme les autres. Les mêmes
paramètres : les filtres, la recherche et le tri de `listNodes`, écrits jusqu'ici dans son chemin,
deviennent des paramètres partagés — `NodeKinds`, `NodeSubtreeOf`, `NodeCostTypeFilter`,
`NodeOrderItemFilter`, `NodeWorkPackageFilter`, `NodeCostCategoryFilter`, `NodeResourceRoleFilter`,
`NodeProgressFilter`, `NodeCriticalFilter`, `NodeSummariesOnly`, `NodeMaxLevel`,
`NodeTimelineFilter`, `NodeSortBy` —, que les deux opérations citent avec `Search`,
`SubprojectFilter`, `SortOrder` et `NodeFields`, sans que `listNodes` en change. La même réponse :
`RevisionComparison` rend `items`, à la place de `nodes`, `totals` (`NodeTotals`) et `meta`
(`NodeListMeta`), de la révision comparée, à côté de `from_revision_id`, `to_revision_id` et
`amount_deltas`. La même mécanique : `listNodes` rend la structure entière, sans pagination — un
arbre ne se lit pas par pages, une page couperait une tâche de ses lignes (EP-02, « `listNodes` rend
la structure entière ») —, et une lecture filtrée en est une fenêtre ; la comparaison de même, ses
filtres s'appliquant comme à la lecture d'un différentiel. `difference` et `changes` restent
toujours rendus, `totals` ne compte pas les nœuds retirés, qui ne sont plus de la structure
comparée.

**`amount_deltas` vient dans chaque réponse, comme `totals`**, et se calcule de même sur les lignes
que la lecture retient — les lignes retirées comprises, rendues à leur place —, quel que soit
`kinds` : sans filtre, les écarts de toute la structure ; d'un sous-arbre, les siens. `listNodes`
n'ayant pas de pagination, il n'y a pas de « première fenêtre » : chaque lecture porte ses écarts,
comme chaque lecture de `listNodes` ses totaux. Écarté : des écarts toujours de toute la structure,
qui feraient d'`amount_deltas` la seule valeur de la réponse que ses filtres ne restreignent pas.

**L'écart se compte par ligne retenue, selon le parent de la révision comparée.** Le diff rend un
nœud déplacé une fois, à sa place nouvelle ; la fenêtre le retient par cette place, et ses écarts
de même : une ligne déplacée dans un sous-arbre y apporte son écart entier — son montant dans la
révision comparée moins celui de la révision de base —, une ligne déplacée hors de lui n'y compte
plus rien. Les écarts de sous-arbres disjoints s'ajoutent ainsi à ceux de la structure entière,
chaque ligne comptée une fois. Écarté : compter une ligne déplacée dans chaque fenêtre, pour son
montant de base dans celle qu'elle quitte et son montant comparé dans celle où elle entre — la
ligne y serait sans être rendue, et une fenêtre compterait ce qu'elle ne montre pas.

**`subtree_of` sur une tâche retirée** rend le sous-arbre qu'elle avait dans la révision de base,
ses nœuds retirés à leur place : la tâche est de l'arbre rendu, et la grille offre de la déplier
comme les autres. Ses totaux sont nuls, la révision comparée n'en ayant aucune ligne, et ses écarts
sont ceux de ses lignes retirées. Écarté : un refus 422, qui rendrait illisible une tâche que la
comparaison rend. **Le tri** ne réordonne que les lignes sous chaque tâche ; la place qu'il donne
à une ligne retirée, dans une comparaison comme dans la lecture d'un différentiel par `listNodes`,
restait à trancher (#1201, point 4) ; tranché depuis (#1205, EP-15/US-0490/L1, ci-dessous) : sur
ses valeurs de base, comme tout nœud. `NodeSortBy`, partagé, dit le tri sans nommer les exemples ni
les grilles de `listNodes`, que son chemin dit désormais.

**Les exemples sont des fenêtres**, engendrés par `wftools.mockcomparisons`. `comparison`, le premier,
est le sous-arbre de l'installation sur site (`subtree_of`), comme `nodes_amendment` sur le
différentiel : 9 nœuds, et chaque marque — deux ajoutés, la tâche et la ligne retirées, à leur
place, deux lignes réestimées, trois tâches modifiées par leur seul contenu —, les totaux de
`listNodes` sur ce sous-arbre de la référence, les écarts de ses lignes ; 13 ko au lieu de 7,4 Mo.
`comparison_identical` garde le cœur de l'offre comparé à lui-même, lu entier. Le sous-arbre d'un
arbre marqué se prend par `wftools.mockdiff.window`, que `nodes_amendment` emploie aussi. Les faits
de toute la structure — 5 999 nœuds, 2 770 modifiés par leurs valeurs, 1 027 251,25 d'écart — restent
tenus par `tools/tests/test_mockhistory.py` sur la comparaison lue entière, que le générateur calcule
sans qu'un exemple la rende. Aucune variante ne montre une page suivante : `listNodes` n'en a pas.

## L'exemple de volume de la comparaison, et ses nœuds partiels (EP-15/US-0500/L6)

**Un exemple de volume pour la comparaison** (décision de l'auteur du 2026-10-20 sur #1201,
point 2). Les fenêtres de L5 ne disent pas ce que pèse la comparaison que l'écran lit entière ;
`volume`, cité en deuxième sous `compareRevisions`, la rend : la comparaison de l'offre et de la
référence sur toute la structure du témoin, 5 999 nœuds, lue sans filtre et avec `fields` réduit à
ce que l'écran montre — `kind`, `task.label`, `estimate_line.label` —, 1,3 Mo au lieu de 7,4 Mo.
Il est engendré par `wftools.mockcomparisons` comme `nodes_thousand` pour `listNodes`
(`fixtures/api/volume/comparison_volume.json`), la lecture avec `fields` par
`wftools.mockcore.with_fields`. US-0500/L4 éprouve dessus la borne de 15 s d'US-0500, et le fera
passer en premier.

**Les nœuds de la comparaison sont décrits par un schéma partiel** (décision de l'auteur du
2026-10-20, #1208). « Une lecture de `listNodes` choisit les champs qu'elle rend » (#166, ci-dessus)
laissait aux schémas le nœud entier, que rend une lecture sans `fields`, et à une lecture avec
`fields` des propriétés exigées qu'elle omet ; un exemple ainsi lu n'était pas conforme, et
`make lint-openapi` le refusait. `RevisionComparison.items` est désormais un tableau de
`ComparedNodeRead`, dont seules sont exigées les propriétés toujours rendues — `node_id`,
`row_number`, `level`, `lock_version` — et la marque du nœud, `difference`, jamais nul, et
`changes` ; ses facettes, `ComparedTaskFacet` et `ComparedEstimateLineFacet`, n'exigent rien. Le
schéma de `listNodes`, `Node` et ses facettes, ne change pas : il reste la seule réponse dont le
schéma ne dit pas tout d'une lecture avec `fields`. Les propriétés sont reprises de `Node`, de
`TaskFacet` et d'`EstimateLineFacet` par des ancres YAML (`&node_properties`, `<<:`), que le
bundle résout en copies : une propriété ajoutée au nœud l'est aux deux, et aucune ne dérive.
Écartés : un `$ref` par propriété (`#/Node/properties/…`), que le bundle hisse en composants
renommés (`budgeted_amount-2`) et dont les modèles du service faisaient des classes vides ; une
exception dans `.redocly.lint-ignore.yaml`, qui laisserait l'exemple non vérifié. Le front de la
comparaison lit les types partiels : il ne suppose plus `kind` ni `lineage_id`, ses lignes sont
clés par `node_id`, toujours rendu.

## La saisie et le collage sur l'avenant, et les prédécesseurs que la tâche accepte (EP-15/US-0500/L4)

**La saisie et le collage du devis sur l'avenant ont leurs exemples** (décision de l'auteur du
2026-10-22 sur #1277). Le faux back servait `nodes_amendment` à l'adresse de la structure 203
(#1219), mais `updateEstimateLine`, `previewPaste` et `applyPaste` y répondaient des nœuds du
témoin, que l'avenant ne contient pas : la grille les lisait comme une autre ligne, et les parcours
de saisie et de collage lisaient le devis propre d'un risque. Trois exemples, nommés `amendment`
sous leur opération, engendrés par `wftools.mockamendmentwrites` comme les gestes du devis sur
l'avenant (#1214) : `estimate_line_updated_amendment`, la charge de la ligne que l'avenant ajoute,
« Assistance à la reprise des essais » (nœud 1293), portée de 40 à 48 h ; `paste_plan_amendment`,
un bloc de trois lignes et quatre colonnes collé sur son libellé, et `paste_applied_amendment`, ce
bloc confirmé. Chaque ligne du bloc écrit la ligne de la grille à la même distance sous la cellule
visée (`PastePreview`) : les lignes 7 à 9 de `nodes_amendment`, la ligne ajoutée, la mise en
service et sa ligne. La mise en service est une tâche : elle prend son libellé, et ses cellules
vides, qui tombent sur des colonnes de ligne, n'écrivent rien ; le bloc est accepté entier, ce que
dit le premier Vérif de WF-IHM-0050. Le collage suit la saisie, comme celui du témoin suit son
libellé saisi (#421) : la ligne 1293 y est à la version 3, la structure au compteur 4. Sur un
différentiel, le budgété suit les grandeurs, d'où la fusion tirera le budget (WF-REV-0050).
`wftools.mock` répète, pour chaque différentiel que liste le premier exemple de
`listCostStructures`, les chemins de ces trois opérations avec celui de `listNodes`, et y place
l'exemple `amendment` en tête ; Prism classe un chemin par ses segments écrits, devant celui qui
les laisse en gabarit. Les autres chemins de l'avenant — ses gestes, son planning — répondent comme
ceux de la principale. Écartés : un aperçu commun au témoin et à l'avenant, dont le collage
identifié (`paste_id`) n'aurait pas été celui du bloc collé ; l'aiguillage des avenants 212 et 213
et des structures de risque, qui va à EP-16 avec la même décision.

**Une réponse d'écriture ne rend pas parmi les ancêtres un nœud qu'elle écrit** (`NodesWritten`,
« hors des nœuds écrits »). Le collage sur l'avenant écrit une tâche et sa ligne : la tâche est un
nœud écrit, rendu dans `nodes`, et non dans `ancestors`. `wftools.mockwrites.written` l'écarte
désormais ; aucun exemple existant n'écrivait un nœud et l'un de ses ancêtres à la fois.

**Les prédécesseurs sont un champ que la tâche accepte** (décision de l'auteur du 2026-10-22 sur
#1257, point 2). La cellule des prédécesseurs était offerte à toute tâche lue avec sa tâche, faute
de champ qui la nomme : un nœud retiré d'un différentiel, en lecture seule, l'aurait gardée
saisissable, une commande que le service refuserait (WF-IHM-0090). `EditableField` gagne
`task.predecessors`, écrit par `setPredecessors` (WF-PLA-0030), que nomme toute tâche,
récapitulative, feuille ou jalon, de toute structure, après ses autres champs de planning et avant
le rattachement au lotissement ; un nœud retiré n'en nomme aucun (`editable_fields` vide). Une
liaison n'est refusée qu'à sa saisie, par ce qu'elle relie — une récapitulative et sa subordonnée
(`LINK_FORBIDDEN`), une boucle (`LINK_CYCLE`) — : la tâche ne dit pas d'avance une liaison qu'elle
refuserait. `editable_fields` dit ce que le nœud accepte, `edit_planning` ce que l'appelant a le
droit d'écrire, comme pour `task.tracking`. Écarté : garder la colonne par la marque du différentiel
dans la grille (US-0500), qui déduirait la règle de la structure lue au lieu de la lire au nœud.

## Du projet créé au projet En cours, et l'avenant (EP-15/US-0490, US-0510)

**Le cycle des révisions a ses exemples de succès** (partie K4 de la conception d'EP-15, #1074,
#1072, #1061 ; US-0490/L1). Ils sont écrits à la main dans la chronologie du témoin, et
`tools/tests/test_mockcycle.py` les date et les confronte aux lectures qu'ils suivent. Ces tests
devaient aller dans `test_mockhistory.py`, mais il aurait dépassé les mille lignes.
- `revision_created` (201) : la révision 103, ouverte aujourd'hui à 14 h 05 sur le projet créé à
  la même heure. C'est celle que lit `revision_without_tasks`, à sa première version.
- `reference_designated` (200) : le projet témoin le 15 janvier 2026 à 11 h, au moment où l'offre
  v1.0, marquée pendant le chiffrage, est désignée référence à la commande. Le projet porte son
  code, et passe donc En cours à cet instant, comme ses transitions et le journal le disent. Sa
  version est 5 : la fusion de l'avenant 1 et l'ouverture de la révision courante la porteront à
  7.
- `rate_update_applied` (200) : la révision 101, le 12 janvier 2026 à 10 h 15. Ouverte un quart
  d'heure plus tôt par une saisie de risque, elle portait les taux de l'offre projetés. La mise à
  jour, toujours proposée depuis la révision en cours, est acceptée ensuite (C-362, WF-REV-0060).
  Une version de plus : les lectures de la 101 marquée la portent désormais à 2, au lieu de 1,
  qu'aucune écriture n'expliquait. `mockwitness.RATES_UPDATED` date cet instant antérieur, que
  `test_mockhistory.py` admet pour cet exemple seul.
- `amendment_created` (201) : l'avenant 2 « reprise des essais », ouvert dans la révision 101
  alors en cours, pendant que l'avenant 1 « extension du poste » l'est encore, à sa première
  version. Deux différentiels coexistent ainsi dans une même révision (WF-REV-0100, #1211).
- `task_merge_queued` (202) : la fusion de l'avenant 2, confirmée aujourd'hui à 14 h 09, la suite
  d'une écriture, à un instant à elle.
- `merge_running` et `merge_succeeded` (`getBackgroundTask`, fichiers `task_merge_running` et
  `task_merge_succeeded` ; #1362, US-0510) : la même tâche que `task_merge_queued` (…948,
  `structure_merge`, soumise à 14 h 09), en cours à 60 %, puis aboutie à 14 h 10 min 30 s. Les
  tâches de fond suivent ainsi la fusion par son propre identifiant, comme l'import et l'export ;
  `task_running` et `task_succeeded` restent le marquage …931, premier exemple servi. Les lectures
  des structures, d'avant la confirmation, montrent encore l'avenant 2 à fusionner : aucun exemple
  ne lit la structure après la fusion, et #421 n'est pas en jeu, une tâche n'ayant pas de version.
  Écrits à la main, comme les autres tâches ; `test_mockcycle.py` les tient à la tâche en file.

**L'abandon est hors de l'annulation** (C-363, WF-IHM-0110). La description d'`abandonRevision`
le dit : l'abandon est irréversible, et l'écran le dit dans sa confirmation. Celle
d'`applyRateUpdate` dit qu'une mise à jour refusée à la création s'accepte ensuite, tant que la
révision n'est pas marquée (C-362).

**Les refus du cycle, chacun avec son exemple** (corrélations 1181 à 1185) :
- **`designateReferenceRevision`** dit son 409 dans l'ordre de la commande `designate_reference`.
  - `revision_marked` d'abord.
  - Puis la condition nouvelle `revision_has_tasks_and_lines` : une révision dont la structure
    principale ne porte aucune tâche ou aucune ligne de devis (WF-CYC-0030).
    `reference_without_tasks` montre ce refus sur la révision du projet créé aujourd'hui, marquée
    sitôt ouverte. `revision_without_tasks` nomme aussi cette condition parmi celles qui manquent
    à sa désignation.
  - Puis `reference_correctable`, refusée par son code propre, `REFERENCE_NOT_CORRECTABLE`, sans
    paramètre (WF-REV-0040 ; `reference_not_correctable`, l'offre désignée de nouveau
    aujourd'hui). La révision courante 102 la nomme aussi, après `revision_marked` : le témoin a
    reçu des coûts réels et marqué la 101 depuis la désignation de l'offre. `revision`,
    `revisions`, `revision_marking` et `revision_importing` la portent, et
    `test_mockcycle.py` le tient.

  Écartée : l'enveloppe commune, `STATE_FORBIDS_OPERATION` à `reference_correctable`. Le
  catalogue porte ce code depuis EP-02, comme `CURRENT_REVISION_EXISTS` pour `createRevision`, et
  le cadrage le nomme. `test_mockproject.py` tient qu'un refus qui nomme une condition est celui de
  l'enveloppe commune : ce code n'en nomme donc aucune.
- **`applyRateUpdate`** refuse une révision marquée par 409 `STATE_FORBIDS_OPERATION` à
  `revision_draft` (`rate_update_revision_marked`). C'est une écriture de la révision, comme son
  marquage, et non une saisie d'une grille, qu'une révision marquée refuse par 403. Aucune
  `RevisionCommand` ne la dit d'avance : son 409 seul nomme `revision_draft`, ou
  `no_background_task_running` pendant un traitement de fond sur la révision.
  *Remplacé par US-0640/L6 (#1351) : `RevisionCommand.apply_rate_update` la dit d'avance, et le
  409 nomme la première condition qui manque à la commande.* *Et depuis US-0702/L1 (#1610, décision de
  l'auteur du 2026-10-28), une saisie de grille sur une révision marquée l'est de même par 409,
  `revision_draft`, et non par 403.*
- **`mergeCostStructure`** a l'exemple de son 412 : `merge_report_stale`, dont
  `expected_lock_version` est le compteur courant du différentiel.

**La désignation proposée a son exemple** (US-0490/L2, WF-REV-0040). Aujourd'hui, aucune révision
du témoin ne propose sa désignation : il a reçu des coûts réels et marqué la 101 depuis celle de
l'offre. Le Vérif — « proposée tant que le projet n'a ni coût réel ni révision marquée depuis la
dernière désignation » — n'avait donc aucun exemple du côté où elle l'est.
`revisions_designation_open`, de `listRevisions`, lit l'historique à un instant antérieur de la
même chronologie : le 15 janvier 2026 à 10 h 59 (`mockcycle.READ_AT`), juste avant la réception de
la commande et la désignation de 11 h (`reference_designated`), sans coût réel encore. L'offre
v1.0 y liste `designate_reference` disponible, et c'est la seule révision marquée. La 101, alors
en cours, attend son marquage ; la 102 n'est pas ouverte. L'exemple est engendré par
`wftools.mockcycle` : l'offre est celle que liste `revisions`, à la même version, sa seule
désignation changée, et la 101 celle que rend `rate_update_applied`, sa dernière écriture.
L'égalité de #421 — une révision rendue à une version n'a qu'un contenu — tient pour l'offre 100
et pour la 101 : brouillon à sa version 2 ici et dans `rate_update_applied`, son marquage porte
une version de plus, la 3, dans `revisions`, `revisions_marked` et `revision_marked` (#1352,
US-0640/L4) ; `revisions` est trié de la plus récente à la plus ancienne, comme le dit le contrat.
`test_mockversions.py` le tient pour toutes les révisions que les exemples rendent ;
`test_mockhistory.py` date la 101
de la mise à jour des taux, comme dans `rate_update_applied`. Écartée : une variante
contrefactuelle du témoin aujourd'hui, qui aurait contredit ses coûts réels.

**Un avenant non fusionné empêche d'en ouvrir un autre** (#1061, #1195). `create_structure` est
indisponible sur la révision courante 102, qui porte l'avenant 2. La condition qui manque est
nouvelle, `no_unmerged_amendment`. C'est le contraire d'`unmerged_amendment_exists`, qui manque à
la fusion quand aucun différentiel n'est à fusionner : garder un seul nom pour les deux aurait
nommé la cause à l'envers. `createCostStructure` la nomme dans son 409, pour un différentiel
(`amendment_unmerged_exists`). Pendant un marquage ou un import, la condition vient avant
`no_background_task_running`, comme pour la fusion. La révision du projet créé aujourd'hui, sans
différentiel, garde la commande disponible. Le test du « si et seulement si » de #1196 tient les
deux commandes, dans les deux sens, sur les deux révisions en cours.

La règle contredisait WF-REV-0100 : son corps dit que plusieurs différentiels coexistent, et son
Vérif qu'il y en a deux dans une même révision. Elle contredisait aussi le témoin, dont la
révision 101 a porté les avenants 1 et 2 ensemble.

*Remplacé par la décision de l'auteur du 2026-10-20 sur #1211, réalisée par US-0490/L1 : on suit
WF-REV-0100, et plusieurs avenants non fusionnés coexistent. `create_structure` reste disponible
quand un avenant de la révision n'est pas fusionné ; la condition `no_unmerged_amendment`, sa clé
de catalogue, le 409 `amendment_unmerged_exists` de `createCostStructure` et son exemple sont
retirés, et `createCostStructure` garde la réponse 409 commune. `unmerged_amendment_exists` reste
la condition qui manque à `merge_structure` quand aucun différentiel n'est à fusionner.
`amendment_created` montre l'ouverture de l'avenant 2 pendant que l'avenant 1 est ouvert. Le test
du « si et seulement si » de #1196 tient la fusion dans les deux sens, et l'ouverture offerte sur
les deux révisions en cours. Le texte ci-dessus est gardé pour l'histoire.*

**Le compte rendu de la fusion dit le déplacement d'un nœud** (#1194, tranché par l'auteur le
2026-10-20). `ImportDifference.fields` gagne `parent`, comme `NodeChange`, par un schéma nommé,
`ImportDifferenceField`. Aucune colonne ne le présente, et le front le rend par sa clé
`enums.ImportDifferenceField.parent`.
`structure_merge_report` dit la « Mise en service » déplacée sous les « Essais sur site ».

**Un filtre et un tri jugent un nœud retiré sur ses valeurs de base** (#1205, tranché par l'auteur
le 2026-10-20). Un nœud retiré d'un différentiel n'a plus que les valeurs de la structure
principale, ou de la révision de base pour une comparaison. Un filtre sur une tâche, la recherche
et un tri le jugent sur ces valeurs, comme tout autre nœud sur les siennes. Sans tri, il reste à
la place qu'il avait. Les descriptions de `listNodes` et de `compareRevisions` le disent, à la
place du renvoi à #1201. Écarté : le placer en fin de ses frères, ce qui l'aurait sorti de la
place que le diff lui donne.

**La boucle d'un déplacement traverse la hiérarchie** (#1169). `mocklinks` refuse déjà une boucle
qui passe par une récapitulative. Exemple : P → W, W récapitulative d'une tâche Z qui précède M, et
M déplacée sous P. `params.cycle` ne parlait que de chaînes de liaisons. Désormais, une chaîne
suit les liaisons et traverse la hiérarchie, pour un déplacement comme pour des prédécesseurs :
- d'une tâche atteinte à son début vers ses subordonnées, que ce qui la précède précède ;
- d'une tâche vers sa récapitulative, que ce qui la suit suit.

Elle nomme chaque tâche traversée : P, W, Z, M. `wftools.mocktree` (`chain`, `move_loop`,
`cycle`) le calcule sur la structure que le déplacement laisserait. Les exemples existants ne
changent pas. Une sélection se juge sur la structure que le déplacement laisserait, tous ses
nœuds déplacés : un refus qui nomme un nœud nomme le premier en cause dans l'ordre du plan de la
structure lue, et `cycle` la boucle que ferme celui-ci (`NodeMove`). L'ordre du refus est celui du
plan ; celui de `node_ids` ne règle que le placement. `move_loop` juge ainsi une sélection, et
lève une `ValueError` pour un parent qui est l'une des tâches déplacées ou l'une de leurs
subordonnées. Entre deux chaînes aussi courtes, `chain` prend, à chaque tâche, les liaisons avant
la hiérarchie, les subordonnées avant la récapitulative ; `params.cycle` le dit, et des tests de
`tools/tests/test_mockgestures.py` le fixent, comme le jugement d'une sélection.

**La règle du rang est une fonction, éprouvée cas par cas** (#1188).
- `mocktree.placed` dit la règle de `NodeCreate` et `NodeMove`. Les gestes engendrés passent par
  elle.
- `test_the_rank_follows_the_rule_of_the_contract` (`tools/tests/test_mockgestures.py`) en
  éprouve les cas : nul pour une ligne et pour une tâche, absent, après un frère de chaque genre,
  la sélection mêlée, et les nœuds déplacés.
- « Absent » se lit hors nœuds déplacés : un nœud déplacé ne compte pas parmi les frères qu'il
  suivrait.
- L'exemple de requête `nodes_move_mixed` montre une sélection mêlée : une ligne et une tâche sous
  le poste de commande, après le câblage, sur l'avenant 2 (structure 203), dont le devis est
  ouvert. La structure principale d'un projet En cours ne saisit plus son devis (WF-DEV-0050), et
  une ligne déplacée change de tâche.
- Les descriptions de `Node.position`, `NodeCreate`, `NodeMove` et `deleteNode` sont refluées.

**Les gestes ont les exemples de leurs refus** (#1184).
- `estimate_line_completed_refused` : une ligne créée sous les « Études de détail », terminées,
  sur l'avenant 2 (structure 203), refusée par 409 `STATE_FORBIDS_OPERATION` à
  `task_not_completed` (WF-DEV-0050, WF-RAE-0030 ; corrélation 1186). Sur la structure principale,
  le projet étant En cours, la création d'une ligne manquerait d'abord le devis lui-même.
  `CommandCondition` dit que `task_not_completed` manque aussi à la création d'une ligne.
- Le 412 de `deleteNode` n'a pas d'exemple : la requête ne porte aucun compteur, et le 412 est
  inatteignable (#1210, à trancher).
  *Tranché par l'auteur le 2026-10-20 et réalisé par US-0520/L1 : `deleteNode` reçoit le compteur
  du nœud, et son 412 a son exemple, `node_delete_stale`.*

**Les exemptions de #421 se réduisent** (#1196). `ELSEWHERE` ne garde que `comparison`. Les
résumés de `nodes_summaries` et de `startable_tasks_milestone` s'ouvrent par « Variante
contrefactuelle » : la seconde est une lecture contrefactuelle, et non la suite d'une écriture.

**Un collage saute les nœuds qu'un différentiel retire** (décision de l'auteur du 2026-10-22,
#1278 ; US-0510). La lecture d'un différentiel rend ses nœuds retirés à leur place, en lecture
seule (`NodeDifference`), et `PastePreview` voulait que chaque ligne du bloc écrive « la ligne de la
grille à la même distance sous le nœud visé » : un bloc qui couvrait une ligne retirée serait tombé
sur un nœud que rien n'écrit. Un tel bloc saute les nœuds retirés et remplit les suivants, sans
refus : chaque ligne du bloc écrit le nœud suivant qui n'est pas retiré, et `PastePlan.accepted`
comme `PasteRejection.row` comptent les lignes du bloc, jamais les nœuds sautés. `previewPaste`,
`applyPaste` et `PastePreview` le disent, et `PastePlan.accepted` comme `PasteRejection.row` y
renvoient. Deux exemples engendrés par `wftools.mockamendmentwrites`, sur l'avenant 2 (structure
203), le montrent : un bloc de deux lignes collé sur le libellé du « Câblage sur site » (nœud 1263),
la ligne qui précède l'« Assistance aux essais de câblage » que l'avenant retire (1264), aperçu
(`paste_plan_amendment_skipping`, deux lignes acceptées, aucun refus, collage 995) puis appliqué
(`paste_applied_amendment_skipping`) : le câblage passe à deux ingénieurs, et la seconde ligne,
sautant la ligne retirée, renomme les « Essais sur site » que l'avenant ajoute (1291) ; les deux
nœuds écrits à leur version 2, le compteur du différentiel à 3, comme toute écriture qui suit sa
lecture (#421). C'est le seul endroit de `nodes_amendment` où une ligne retirée en précède d'autres.
`wftools.mockamendmentwrites.paste_targets` écarte désormais les nœuds retirés ; le bloc des
parcours, sur les lignes 7 à 9, n'en couvre aucun, et son exemple ne change pas. Ce que devient un
collage dont la cellule visée est elle-même sur un nœud retiré, qui ne nomme aucun champ
(`editable_fields` vide), n'est pas tranché ici. Écarté : un refus de la ligne du bloc tombée sur un
nœud retiré, que la décision écarte.
*Tranché au recadrage d'EP-16 et écrit par US-0640/L6 (#1361) : le collage entier est refusé,
`PASTE_TARGET_REMOVED` sur l'ancre.*

## L'encart « Démarrer le projet » sur un projet sans révision (EP-15/US-0490/L4, #1358)

**Ce que le front lit.** Décision de l'auteur du 2026-10-23 sur #1358 : l'encart paraît dès la
création d'un projet, quand il n'a encore aucune révision (`current_revision_id` nul). Le front ne
déduit rien : il lui faut savoir, d'une lecture du projet, si le squelette s'engendrerait et si
l'appelant peut écrire le planning. `create_revision` ne le dit pas : elle est gardée par
`revisions.write`, et ne dit rien de la structure que la révision ouverte copierait. Le projet
porte donc une commande nouvelle, `ProjectCommand.generate_skeleton`, sur le modèle des imports
et de la saisie des risques :
- listée tant que le projet n'a pas de révision en cours, à qui a la permission du planning,
  `planning.write`, comme `RevisionCommand.generate_skeleton`, et juste avant les imports ; dès
  qu'une révision est en cours, c'est elle qui la liste, et le projet ne la liste plus ;
- jugée sur la révision que l'ouverture créerait, une copie de la dernière révision marquée
  (WF-REV-0010) : `main_structure_without_tasks` manque quand sa structure principale comporte
  une tâche, comme `at_least_one_task` à `declare_risk` quand elle n'en comporte aucune ;
- ses conditions dans l'ordre de `declare_risk`, sa sœur au niveau du projet : celles de l'état
  d'abord, `project_not_terminal` puis `no_background_task_running` (la première, depuis
  US-0702/L3, #1657, nommée par le seul 409 : un projet terminal ne liste plus la commande), puis
  la condition propre, `main_structure_without_tasks`, puis `may_create_revision` à qui ne peut pas ouvrir la
  révision, comme pour les imports et `declare_risk`. C'est l'exception du 2026-10-05
  (`Project.available_commands`), étendue à cette commande.

**L'ordre des conditions** (relecture 1 du lot). La première rédaction mettait la condition
propre avant le traitement de fond, « comme sur la révision » (`RevisionCommand.generate_skeleton`,
EP-14/L42k). Sur le projet, l'ordre de `declare_risk` l'emporte : la structure jugée n'existe pas
encore, c'est celle de la révision qu'une ouverture créerait, et un traitement de fond qui court
est justement en train d'en créer une autre ; nommer `main_structure_without_tasks` à ce moment
dirait un état que la fin du traitement rendra faux, comme `at_least_one_task` à `declare_risk`
inviterait à une saisie elle-même refusée (EP-14/L42s). Sur la révision, la structure existe et
l'ordre de L42k reste, celui du 409 de `generatePlanningSkeleton`. Le front ne lit que la présence
de `main_structure_without_tasks`, et l'ordre ne change rien à l'encart.

**`no_background_task_running` sur un projet sans révision en cours** (relecture 1 du lot). La
condition est atteignable, et elle reste. L'application d'un import de planning, de devis ou de
reste à engager écrit en une seule transaction (`applyImport`, WF-INTF-0080) et crée la révision
en cours au besoin (WF-INTF-0090) ; le traitement d'une survenance la crée de même au préalable
(`declareRiskOccurrence`, WF-RIS-0060). Pendant ces traitements, confiés au worker, le projet lu
n'a pas encore de révision en cours, et ce sont eux qui la créent : ouvrir une révision et y
engendrer le squelette se heurterait à la leur — `createRevision` refusé par
`CURRENT_REVISION_EXISTS` à leur fin, ou leur révision refusée à la sienne. C'est le cas qui fait
déjà nommer la condition aux imports, à `edit_risks` et à `declare_risk` que porte un projet sans
révision en cours ; `CommandCondition` le dit désormais pour les quatre. Aucun exemple ne le
montre : le témoin abandonné n'a ni import ni survenance qui court. Écarté : retirer la condition,
ce qui aurait fait de `generate_skeleton` la seule commande du projet sans révision qui ne la
nomme pas.

**Le refus de `createRevision`** (relecture 1 du lot). Son 409 n'avait pas d'exemple, et le test
de l'encart en inventait un, `STATE_FORBIDS_OPERATION`, quand le code est
`CURRENT_REVISION_EXISTS`, sans paramètre, au catalogue depuis EP-02. L'exemple
`current_revision_exists` (corrélation 1308, seconde suite) le donne : une seconde ouverture sur
le projet créé aujourd'hui, demandée depuis un écran lu avant que sa révision 103 ne s'ouvre. Le
409 le décrit, et `tools/tests/test_mockstart.py` le tient.

L'encart s'offre ainsi quand le projet liste `generate_skeleton` sans
`main_structure_without_tasks`, ou, avec une révision en cours, quand celle-ci la liste ainsi,
comme jusqu'ici. Le choix du fichier MS Project suit `import_planning`, que le projet liste déjà.

**Ce que chaque choix appelle.** La spécification ne fait créer la révision en cours que par un
import (« Lorsque le projet n'en comporte pas, l'import en crée une », WF-INTF-0040) et par une
saisie des risques (WF-RIS-0020) ; WF-PRJ-0030 ne le dit pas de la génération. La voie la plus
sobre est retenue : aucune opération nouvelle, et la génération n'ouvre pas la révision.
- **Lotissement puis squelette.** Le lotissement est une donnée du projet, saisi sans révision
  (`setWorkBreakdown`, `update_work_breakdown`). « Engendrer le planning » ouvre la révision en
  cours (`createRevision`, sans corps obligatoire), puis engendre le squelette sur la révision
  rendue (`generatePlanningSkeleton`), qui liste `generate_skeleton`. Si la génération est
  refusée, la révision reste ouverte, sa structure vide : l'encart la relit et l'offre de
  nouveau, ce qui est l'état d'avant cette décision. Un 409 de `createRevision` — une révision
  ouverte entre-temps — se relit de même.
- **Fichier MS Project.** `uploadFile` puis `openImport` `ms_project_schedule`, comme l'écran
  FBS-4.3.4 : l'import crée la révision (WF-INTF-0040), rien ne change au contrat.

Les descriptions de `ProjectCommand`, `RevisionCommand.generate_skeleton`, `CommandCondition`
(`may_create_revision`, `main_structure_without_tasks`), `createRevision` et
`generatePlanningSkeleton` le disent. Écartés : faire ouvrir la révision par la génération, ou
une opération du projet qui engendre, que la spécification ne prévoit pas et qui aurait donné deux
chemins pour une même génération ; lire `create_revision`, qui ne dit ni la permission du
planning ni la structure copiée.

**Les exemples.** Écrits à la main, comme le projet. `project_created` (le projet créé
aujourd'hui, sans révision), `project_pricing` et l'offre de `projects` (en chiffrage, sans
révision marquée) listent `generate_skeleton` disponible ; `project_without_current_revision` (le
témoin, sa révision courante abandonnée) l'indisponible, `main_structure_without_tasks` manquante,
sa dernière révision marquée portant des tâches. `project_pricing_estimator` ne la liste pas : le
chiffreur n'a pas `planning.write`. Les lectures triées et filtrées de l'accueil suivent
(`make mock-data`). Le parcours se lit ensuite sur les exemples qui existent : `revision_created`,
la révision 103 ouverte à 14 h 05 et qui liste `generate_skeleton` disponible, puis
`skeleton_generated`. `tools/tests/test_mockstart.py` les tient.

**Le faux back sert le projet créé à son adresse** (`wftools.mock`, `CREATED_PATHS`). Prism sert
le premier exemple d'une opération quel que soit le chemin : la page du projet …003, où mène la
création (`createProject`, `created`), aurait lu le témoin. Quatre chemins sont répétés, son
identifiant écrit, chacun menant par l'exemple qui le décrit : `getProject` par `created`,
`getProjectNextState` par `created`, `listRevisions` par `empty`, `getWorkBreakdown` par
`default`. Un chemin dont la lecture n'a pas cet exemple fait échouer la dérivation. Le parcours
de bout en bout qui créait un projet et lisait le témoin à sa place lit désormais le projet créé.

## La déclaration d'un risque désigne la tâche de sa provision, et les saisies du risque ont leurs exemples (EP-15/US-0520)

**La tâche de la provision se désigne** (partie K5 de la conception d'EP-15, #786 ; US-0520/L1).
WF-RIS-0010 veut la ligne de provision « portée par la tâche de la structure principale que
l'utilisateur désigne à la déclaration du risque », déplaçable sur une autre, et « à défaut de
désignation » portée par la première tâche de premier niveau. Le contrat ne permettait ni l'un ni
l'autre.
- `RiskWrite.provision_task_id`, facultatif, nul ou omis à la déclaration : la première tâche de
  premier niveau. Une récapitulative la porte comme une feuille, la ligne n'entrant pas dans
  l'état de sa tâche.
- À la modification (`RiskUpdate`), omis, il garde la tâche ; nul, il rend la ligne à la première
  tâche de premier niveau ; une autre tâche y déplace la ligne, le total du devis inchangé. Il
  relève d'`update_provision`, comme la catégorie et le sous-projet : changé pour un risque qui
  n'est pas identifié, 409 à `risk_identified`.
- Un nœud qui n'est pas une tâche de la structure principale de la révision en cours — une ligne,
  une tâche d'un différentiel, un identifiant inconnu — est refusé par 422 `VALIDATION_FAILED`,
  `/provision_task_id`, `UNKNOWN_TASK`, code que `FieldErrorCode` portait déjà.
- `Risk.provision_task`, exigé, `{node_id, label}` par un schéma nommé, `ProvisionTask`, comme
  `AttachedTask` nomme la tâche d'un lot : la tâche qui porte la ligne, nulle quand le risque
  n'est pas identifié et ne porte donc pas de ligne, comme `provision_node_id`. Le formulaire la
  présente sans relire la structure. `risks`, `risk` et `risk_occurred_detail` la nomment : le
  « Câblage des armoires » pour 751, rien pour 752, survenu, ni pour 753, écarté.

Écarté : un `provision_task_id` exigé, que la spécification dit facultatif. Deux points restaient
hors de cette partie, tranchés par l'auteur le 2026-10-21 (#1227) et portés par US-0570/L1 :
- **`moveNodes` refuse une ligne de provision.** La ligne se déplace par le formulaire de son
  risque, seul chemin : une ligne de provision parmi `node_ids` est refusée par 422
  `VALIDATION_FAILED`, `fields` sur elle (`/node_ids/<n>`), motif nouveau
  `PROVISION_LINE_MOVED_BY_RISK`, `fields[].params.risk` nommant le risque par `risk_id` et
  `label`, que la grille ne lit pas et vers le formulaire duquel le front renvoie. Une tâche qui
  porte une ligne de provision se déplace avec elle : la tâche de la ligne ne change pas. Exemple
  engendré par `wftools.mockriskwrites`, `nodes_move_provision_refused` : la ligne de 751 envoyée
  du « Câblage des armoires » sous le « Montage des armoires sur site » (corrélation 1304).
  Écarté : accepter le déplacement comme un changement de `provision_task_id`, un second chemin
  vers la même écriture.
- **Le risque écarté qui redevient identifié** : sa ligne de provision est portée par la tâche
  qu'il désignait si elle est encore une tâche de la structure principale, et sinon par la
  première tâche de premier niveau ; `provision_task` reste nul tant qu'il est écarté. La
  description de `reviewRisk` le dit ; le texte de WF-RIS-0010 est intégré par l'auteur (#1227).

**Les saisies du risque ont leurs exemples** (#763). Elles sont engendrées, depuis les risques de
`mockwitness` et la lecture du registre (`mockhistory.risk_item`), par `wftools.mockriskwrites` :
`mockhistory` aurait passé les mille lignes. `tools/tests/test_mockriskwrites.py` les tient.
- `risk_created` (201) : « Indisponibilité de la grue de levage », 754, déclaré aujourd'hui à
  20 % sans tâche désignée. Sa structure propre, 208, est ouverte vide : sa gravité et sa
  provision sont nulles jusqu'au chiffrage de son devis propre. Sa ligne de provision, 585, est
  portée par « Études », la première tâche de premier niveau. À sa première version.
- `risk_updated` (200) : le même, sa ligne déplacée sur le « Montage des armoires sur site » et
  ses actions de mitigation saisies, une version de plus.
- `risk_reviewed` (201) : 751 confirmé aujourd'hui sans modification, un réexamen daté du jour,
  une version de plus que `risk`.
- `task_occurrence_queued` (202) : la survenance de 752, confirmée le 20 février 2026 à 16 h, la
  tâche de fond 949 en file : un instant antérieur de la chronologie, celui de son dernier
  réexamen.
- `risk_provision_task_refused` (422) : une provision désignée sur la « Reprise des essais de
  câblage », que seul l'avenant 2 porte (corrélation 1193).
- `risk_probability_out_of_range` (422) : une probabilité de 120, un pourcentage envoyé pour un
  rapport, refusée sur `/probability` par `VALUE_OUT_OF_RANGE`, `params.maximum` à `1`
  (corrélation 1306). Celui-là est écrit à la main, hors de `paths.toml` : un refus statique, que
  rien du témoin ne fait varier, comme `project_rates_out_of_range`. Le front s'en sert pour dire
  la borne en pourcentage ; le schéma la dit sur `RiskWrite.probability`.

**La modification dit la même borne de la probabilité** (US-0520/L2b, #1371). `RiskUpdate`
portait déjà la borne de `RiskWrite.probability`, un rapport de 0 à 1 inclus, mais le 422
d'`updateRisk` ne la disait pas : il la dit, `/probability` hors de 0 à 1 refusé par
`VALUE_OUT_OF_RANGE`, la borne franchie dans `params`, comme celui de `createRisk`. Son exemple
est propre, `risk_update_probability_out_of_range` : la même probabilité de 120 envoyée en
modifiant le risque, `params.maximum` à `1` (corrélation 1307), écrit à la main comme celui de la
déclaration. Le résumé de chacun dit son geste, et le test 422 de « Modifier »
(`risk-commands.dom.test.tsx`) lit l'exemple de l'opération qu'il éprouve, et non celui de
`createRisk`. Écarté : citer `risk_probability_out_of_range` sous les deux opérations, son résumé
élargi aux deux gestes — un résumé qui ne dirait plus lequel l'exemple montre, et que le réexamen
d'US-0520/L3 aurait à élargir encore. Le réexamen (`reviewRisk`) dira sa borne avec US-0520/L3
(#1114).

*Remplacé par US-0701/L4 (#1604, H-04) : la modification ne reçoit plus la probabilité, que seul
le réexamen écrit (WF-RIS-0010, WF-RIS-0040 ; décision du recadrage du 2026-10-28, « Les
risques ») ; `risk_update_probability_out_of_range` est retiré, et la corrélation 1307 n'est plus
employée (« Les risques », dans « Le contrat figé »).*

**Le réexamen dit la même borne, et ses réponses ont leurs exemples** (US-0520/L3, #1371, #1114).
`RiskReviewWrite.probability`, le corps du réexamen, dit la borne de `RiskWrite.probability` : « De
`0` à `1` inclus, un rapport (WF-RIS-0010). » ; le 422 de `reviewRisk` dit `/probability` hors de 0 à
1 refusé par `VALUE_OUT_OF_RANGE`, la borne franchie dans `params`, avec son exemple propre,
`risk_review_probability_out_of_range` (corrélation 1309), écrit à la main comme ceux de la
déclaration et de la modification, le résumé disant le geste du réexamen. `RiskReview`, le réexamen
lu dans l'historique, ne la redit pas, comme `Risk.probability` : la borne est celle de ce qui
s'envoie. Les autres réponses du réexamen, dont le formulaire « Réexaminer » a besoin :
- `risk_dismissed` (201), engendré par `wftools.mockriskwrites` : 751 écarté aujourd'hui, sa
  probabilité inchangée, sans ligne ni tâche de provision, `update_provision` et
  `declare_occurrence` indisponibles par `risk_identified`. Variante contrefactuelle : le témoin
  confirme 751 aujourd'hui (`risk_reviewed`), à la version que l'écarter lui donnerait (#421).
- `risk_reidentified` (201), engendré : 753, écarté le 2 février, redevenu identifié aujourd'hui à
  sa probabilité ; sa catégorie encore active n'est pas redemandée, et sa ligne de provision,
  recréée, est le nœud 586, qu'aucune lecture du témoin ne rend, porté par la « Mise en service »,
  la tâche qui portait sa ligne dans la référence et que la structure principale porte encore
  (#1227). La suite d'une écriture faite aujourd'hui, comme la confirmation de 751.
- `risk_reviews_reviewed` (200 de `listRiskReviews`), engendré : l'historique de 751 relu après sa
  confirmation, le réexamen daté du jour en tête — ce que l'historique rendu porte après
  « Réexaminer » (Vérif de WF-RIS-0010).
- `risk_review_occurred` (409), écrit à la main : le réexamen de 752, survenu, refusé par
  `risk_not_occurred`, la condition que sa commande `review` dit manquante (corrélation 1310).

Prism sert le premier exemple de chaque réponse : la confirmation de 751 (`risk_reviewed`) et
l'historique du témoin (`risk_reviews`) le restent. `deleteRisk` avait déjà ce dont « Supprimer le
risque » a besoin : le refus `risk_delete_cited`, et la commande `delete` indisponible par
`risk_not_cited` dans `risk` et `risks`. `declareRiskOccurrence` a sa mise en file
(`task_occurrence_queued`), la structure qui en résulte (`nodes_risk_occurred`) et le risque survenu
(`risk_occurred_detail`), mais aucune opération ne rend le compte rendu préalable de la fusion du
devis propre : à trancher (#1383).

Le résumé de `risk_created` s'ouvre par « Variante contrefactuelle », comme le veut la convention
de #1196 (#1228).

Écarté : la déclaration de 751 le 12 janvier, que le registre aurait donnée. Le témoin la dit
identifiée avec une gravité de 1 000 000, quand une structure propre vide, à la création, n'en
porterait aucune ; et la révision 101 de ce jour-là n'est pas celle dont les exemples nomment les
nœuds.

**`deleteNode` porte le compteur du nœud supprimé** (#1210, tranché par l'auteur le 2026-10-20).
Le 412 que l'opération déclarait était inatteignable : la requête ne portait aucun compteur. Elle
reçoit `lock_version`, paramètre de requête exigé, le compteur lu du nœud désigné, comme toute
modification ; les subordonnées qu'une récapitulative emporte ne se jugent pas. Elle déclare donc
aussi 422, pour un paramètre de requête hors de son schéma. Son 412 a son exemple engendré,
`node_delete_stale` : sur l'avenant 2, la ligne « Matériel » supprimée avec le compteur lu, 1, que
le déplacement de la sélection (`nodes_moved`) a porté à 2 (corrélation 1194) — une écriture que la
grille d'un différentiel propose quel que soit l'état du projet. Le front envoie
le compteur de la ligne (`src/api/actions/nodes.ts`), et `structure-gestures.dom.test.tsx` lit cet
exemple au lieu du refus qu'il écrivait : il le rejoue sur une grille de devis de la structure
principale, et n'en consomme que le corps — le code, le statut et le compteur rendu —, son résumé
décrivant le différentiel de l'avenant (#1228). `test_every_writing_that_declares_a_412_sends_a_counter`
(`backend/tests/test_contract_declarations.py`) tient le sens inverse de
`test_every_writing_that_carries_a_lock_version_declares_its_412` : une écriture qui déclare un
412 envoie un compteur, `lock_version` ou `…_lock_version`, dans son corps ou ses paramètres. Écarté :
retirer le 412 (proposition (a) de #1210).

**Les gestes du devis s'écrivent sur l'avenant 2** (#1214, tranché par l'auteur le 2026-10-20).
Sur un projet En cours, la grille de devis de la structure principale ne propose aucune saisie
(Vérif de WF-DEV-0050, `structures`). `estimate_line_created`, `estimate_line_created_after_subtask`
et `nodes_moved` portent donc sur l'avenant 2, structure 203, par ses identifiants propres
(`mockamendment.own_id`) : chaque réponse est la différence de deux lectures du différentiel,
marquées contre la structure principale, la ligne créée `added`, les lignes déplacées `modified`
par leur parent, le compteur du différentiel passé à 3. Une ligne créée sur un différentiel porte
les grandeurs de référence d'où la fusion tirera son budget (WF-REV-0050), comme la reprise des
essais : son montant budgété est son montant, et non le budget nul d'une ligne ajoutée en revue
périodique. `wftools.mockamendmentwrites` les engendre, avec `nodes_move_mixed` et
`estimate_line_completed_refused` que `mockgestures` portait : il aurait passé les mille lignes.
- Le refus de `moveNodes` vers une tâche terminée est décrit : « le déplacement d'une ligne vers
  elle, est refusé » (Vérif de WF-DEV-0050). 409 `STATE_FORBIDS_OPERATION` à
  `task_not_completed`, pour une ligne déplacée vers une tâche terminée ou depuis elle, à la place
  de la réponse 409 commune. Exemple engendré, `nodes_move_completed_refused` : les « Borniers »
  déplacés sous les « Études de détail », sur l'avenant 2 (corrélation 1195). `CommandCondition`
  le dit.
- `row-selection.dom.test.tsx` lit le compteur que rend `nodes_moved` au lieu de l'écrire.

**Le tri d'un nœud retiré passe par celui du faux back** (#1216). Le test de #1205
(`tools/tests/test_mockdiff.py`) lit le différentiel marqué comme `listNodes` le lit, trié par le
montant décroissant par `mockcore.subtree(…, sort=…)`, la ligne retirée lue sur ses valeurs de base
et dernière de ses sœurs, au lieu de refaire le tri à la main.

## Le nombre de lignes par page, la disposition d'une chronologie, les calendriers sans bornes d'heures, les unités de durée (EP-15/US-0530, US-0570)

Partie K8 de la conception d'EP-15 (US-0570/L1), sur les décisions de l'auteur du 2026-10-18
(#1045, #1068, #1047, #1049).

**Le nombre de lignes par page est une préférence de la grille** (C-351, #1045).
`GridPreferences.page_size`, un entier parmi 10, 25, 50 et 100, absent pour 50, le défaut de
`limit` : la table plate l'envoie en `limit` à chaque lecture, et le retrouve à sa réouverture
sans changer celui des autres tables (WF-IHM-0060). Une autre valeur est refusée par 422
`VALIDATION_FAILED`, `/grids/<grille>/page_size` par `VALUE_OUT_OF_RANGE`, sans paramètre : ce
ne sont pas des bornes mais quatre valeurs, que le schéma énumère et que `minimum` ni `maximum` ne
diraient. Le service, dont les modèles sont engendrés du contrat, dit ainsi un entier — ni un
booléen, ni une chaîne — envoyé à une énumération dont toutes les valeurs sont des entiers, et
qu'elle n'admet pas (`waterfall.api.problems`, d'après les valeurs attendues que Pydantic nomme) ;
toute autre valeur refusée par une énumération l'est par `VALIDATION_FAILED`, ainsi un entier
envoyé au thème, une énumération de mots (`{"theme": 3}`) : ce n'est pas une valeur hors de sa
plage, mais une valeur d'une autre nature. Une chaîne qui se lit comme l'une des quatre (`"25"`)
est admise par conversion, comme tout entier d'un corps. Un nul est refusé comme les autres
réglages d'une grille. Exemples `preferences_page_size` et
`preferences_page_size_out_of_range` (corrélation 1300) ; `me_grid_settings` lit 25 lignes sur la
table des comptes. Écarté : un nombre libre borné entre 10 et 100, que l'écran n'offrirait pas.

**La disposition d'une chronologie est une préférence d'affichage, par chronologie** (#1068,
WF-PLA-0140, WF-ADM-0040). `DisplayPreferences.timelines`, une table par `timeline_id` de
`TimelinePreferences` — `lanes`, exigé, le couloir de chaque tâche placée par son `node_id`, un rang
à partir de 0 —, bornée comme `grids` (#874) : cent chronologies, 64 tâches placées par chronologie,
des noms de 64 caractères au plus, `VALUE_TOO_LONG` au-delà. Une modification ne remplace que les
chronologies qu'elle nomme, chacune entière, et une chronologie à `null` retrouve sa disposition
automatique ; une tâche absente prend le couloir automatique, une tâche qui n'est plus inscrite
s'ignore. Un couloir négatif est refusé par `VALUE_OUT_OF_RANGE`,
`/timelines/<chronologie>/lanes/<tâche>`, `params.minimum` à `0`, comme toute borne d'une écriture
(`tools/tests/test_mockbounds.py`). Exemples `preferences_timeline_lanes` et
`preferences_lane_out_of_range` (corrélation 1301), sur le « Comité de pilotage » du témoin ;
`me_grid_settings` porte la même disposition, et le couloir d'une tâche (#1406, plus bas). Le
refus d'un couloir où un rectangle en chevaucherait un autre se tranche au lot d'écran
(US-0530/L3).

**La table des calendriers ne se filtre pas sur les heures de ses jours** (C-352, #1047). Les
quatorze paramètres `monday_min` à `sunday_max` de `listCalendars` sont retirés, avec l'exemple
`calendars_bounds_inverted` : WF-IHM-0130 fait de ces heures une exception à la règle commune.
Elles se trient toujours ; la recherche et le filtre d'état restent. La convention des bornes
(#545, ci-dessus) vaut pour les autres colonnes de nombres. Le front cesse d'envoyer
ces bornes (`src/app/reference/resources/page.tsx`) ; la barre qui les saisit est retirée par
US-0570/L3.

**Les unités de durée ont leurs exemples** (C-360, #1049). `setDurationUnits` répond
`duration_units_updated` — 7 heures par jour et 35 par semaine, réglées aujourd'hui, à la
version 2 : « 2 j » vaut quatorze heures dans les révisions en cours, recalculées, seize dans une
révision marquée —, refuse une constante nulle par `duration_units_zero` (422, `/hours_per_day`
par `DURATION_UNIT_NOT_POSITIVE`, sans paramètre ; corrélation 1302) et une version périmée par
`duration_units_stale` (412, la version 2 rendue ; corrélation 1303). Sa description dit le recalcul
des plannings en cours et les heures gardées d'une révision marquée (WF-PLA-0160, WF-REF-0130).
Une constante est strictement positive : l'intervalle ]0, ∞[ est ouvert et n'a pas de plus petite
valeur admise que `params.minimum` pourrait nommer — la raison pour laquelle EP-14/L42h et L42m
ont écarté `VALUE_OUT_OF_RANGE` pour les seuils d'indice, et pour laquelle `waterfall.api.problems`
dit une borne exclusive par `VALIDATION_FAILED`. Elle est donc refusée par un motif par champ
nouveau au catalogue, `DURATION_UNIT_NOT_POSITIVE`, sur le modèle de
`THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE`, que le front dit en clair (« La constante doit être
strictement positive ») ; une constante qui n'est pas un décimal sans signe garde
`VALIDATION_FAILED` au même pointeur. `tools/tests/test_mockbounds.py` tient que seul un nombre
de lignes par page hors des quatre est refusé par `VALUE_OUT_OF_RANGE` sans paramètre. Écartés :
`VALUE_OUT_OF_RANGE` sans paramètre, qui donnerait une borne exclue pour une borne franchie ;
`VALUE_OUT_OF_RANGE` nommant `minimum` à `0`, que le front dirait admis ; `VALIDATION_FAILED` seul
au pointeur, qui ne distinguerait pas zéro d'une valeur mal écrite.

**Le service suit le contrat engendré** (revue 1 de US-0570/L1). La conception d'EP-15 ne prévoit
ni table, ni migration, ni module du noyau pour K8, et le lot n'en ajoute pas ; mais ses modèles
étant engendrés du contrat, le back qui sert déjà les préférences change avec lui, sans quoi il le
contredirait : `waterfall.core.users.personal.merged` fusionne `timelines` chronologie par
chronologie, comme `grids` grille par grille ; `waterfall.api.me` refuse un `timelines` ou un
`page_size` nul, comme les autres réglages qui ne le sont jamais ; `waterfall.api.problems` dit un
entier hors d'une énumération d'entiers par `VALUE_OUT_OF_RANGE`, comme ci-dessus. Le refus du
déplacement d'une ligne de provision (`PROVISION_LINE_MOVED_BY_RISK`) n'est que dans le contrat et
ses exemples : le back ne sert pas encore `moveNodes`.

**Les corrélations écrites à la main ouvrent une nouvelle plage** (#1228). La famille
« corrélations, suite » (1010-1199) étant presque épuisée, « corrélations, seconde suite »
(1300-1599, `wftools.mockids`) la prolonge après les nœuds de l'avenant 2 ; les exemples de ce lot
l'emploient, de 1300 à 1304. Les suivantes la prennent après eux : 1305 pour
`task_hours_beyond_day` (US-0470/L2), 1306 pour `risk_probability_out_of_range` (US-0520/L2),
1307 pour `risk_update_probability_out_of_range` (US-0520/L2b), 1309 pour
`risk_review_probability_out_of_range` et 1310 pour `risk_review_occurred` (US-0520/L3).

## Le plan de charge agrégé porte sa capacité, la matrice ses points (EP-15/US-0550)

Partie K7 de la conception d'EP-15 (US-0550/L1), sur les décisions de l'auteur du 2026-10-18
(#1051, #1053). Le front ne calcule rien de ce qu'il trace (WF-ARC-0020) : ce que les graphiques
d'US-0550 placent, le serveur le rend.

**Le plan agrégé porte la capacité de son périmètre et le total de chaque mois** (#1051).
`PortfolioWorkload.capacity_monthly_hours` est la somme des `capacity_monthly_hours` des rôles
retenus : tous les rôles actifs sans filtre, ceux du nœud d'organisation avec lui (`org_node_id`).
Un rôle sans charge y compte, comme il figure au plan depuis la décision du 2026-10-08 sur #375 :
le plan sert à voir la disponibilité. C'est la droite en pointillés du graphique. `monthly_totals`
donne le total des heures des rôles retenus pour chaque mois de `months`, dans le même ordre, un
mois sans charge compris : c'est l'étiquette du sommet de chaque barre. Chaque total nomme son mois
(`month`, `hours`), comme les mois d'un rôle. Le plan d'un projet ne change pas : il reste sans
capacité tracée ni taux de charge (#375, option b, confirmée sur #1051), et `Workload` garde sa
forme. Les exemples sont `portfolio_workload` (1 360 640,5 heures par mois, les trois rôles, le
monteur câbleur sans charge compris) et `portfolio_workload_org_node`, dont le nœud retient les
trois mêmes rôles, et donc la même capacité et les mêmes totaux. Écartés : la somme des rôles
faite par le front, qui ne calcule pas ce qu'il présente ; une liste de nombres nus pour les
totaux, qui ne se lirait qu'en la rapprochant de `months`.

**La matrice rend un point par risque qu'elle compte** (#1053). `RiskMatrix.points`, chacun un
`RiskMatrixPoint`, porte les mêmes risques que ceux que comptent les cases. Dans la matrice d'un
projet, ce sont tous les risques de la révision lue, quel que soit leur état : l'écran retient les
bulles par son filtre d'état, comme la grille (décision 1 de #1053). Dans celle du portefeuille,
ce sont les risques identifiés des projets en cours. Un point porte `risk_id`, `label`,
`probability`, `severity_amount` (la gravité, `Risk.severity`), `severity_ratio`,
`provision_amount`, `state` et `zone`, la zone de sa case. `severity_ratio` est la gravité en part
de l'assiette du projet, arrondie à quatre décimales (README, « Une part… »). La case et la zone
du point sont celles de la part exacte, que classent les bornes de gravité (WF-REF-0160) avant
l'arrondi : une bulle à moins d'un demi-centième de pour cent d'une borne peut être tracée sur la
ligne de cette borne, sa zone restant celle de sa case. Dans la matrice du portefeuille, le point
nomme aussi son projet : `project_id`, `project_label`, et `can_open` comme
`PortfolioRisks.heaviest[]` (WF-PTF-0030). Ces trois champs vont ensemble : présents tous les trois
dans la matrice du portefeuille, absents tous les trois dans celle d'un projet. `cells` reste au contrat, pour la table du décompte sous le graphique (décision 2 de
#1053). Les exemples sont `risk_matrix`, avec trois points (1,91 % ; moins d'un centième de pour
cent, donné à son premier chiffre, `0.000003` ; 18,34 %), et le volume `portfolio_risks`, avec un
point par risque identifié, 429, dont 50 d'un projet que le lecteur ne peut pas ouvrir. Écartés :
un point sans sa part de gravité, que le front calculerait sur une assiette qu'il ne lit pas ; deux
schémas, un pour le projet et un pour le portefeuille, alors que `RiskMatrix` est déjà commun aux
deux.

**Un volume écrit une ligne par élément d'une longue liste, à toute profondeur.** Sous la valeur
d'un exemple, un objet qui tient une liste de plus de cinquante éléments est déplié
(`wftools.mockdata.render`). La matrice de `portfolio_risks`, qui tenait sur une ligne, s'écrit
désormais un point par ligne : un point changé se lit dans le diff. Aucun autre exemple ne change.

**Un nombre de lignes par page envoyé autrement qu'en entier** (#1236, revue de US-0570/L1).
`page_size` à `30` est refusé par `VALUE_OUT_OF_RANGE`. À `"30"` ou à `30.0`, il est refusé par
`VALIDATION_FAILED`. À `"25"` ou à `25.0`, il est admis comme 25. Le service ne dit « hors plage »
que pour un entier envoyé : Pydantic lui rend la valeur telle qu'envoyée, et il ne la reconvertit
pas pour classer le refus. Le front, lui, n'envoie que l'une des quatre valeurs, en entier.
`backend/tests/test_users_personal.py` fixe ces deux refus. `waterfall.api.problems` reconnaît une
énumération d'entiers à la façon dont Pydantic en écrit les valeurs dans `ctx.expected` : nues
pour des entiers (« 10 or 25 »), entre apostrophes pour des mots (« '10' or '25' »), même faits de
chiffres. `backend/tests/test_api_problems.py` l'éprouve sur ses propres modèles, une `IntEnum` et
une `StrEnum` de chiffres, qui ne doivent rien au contrat. Une dérive de cette écriture échoue
donc là, et un changement du contrat échoue aux tests de ses champs. Écarté pour ce lot : lire le
type du champ que désigne `loc` dans le modèle, comme le proposait #1236, puisque le test suffit à
dire la dérive.

## Les heures d'une date saisie, complétées par le serveur ; un jour chômé refusé (EP-15/US-0470, #1244, #1271)

**Une date de début ou de fin se saisit sans ses heures** (décision de l'auteur du 2026-10-21,
#1244 ; WF-PLA-0010, WF-PLA-0020, WF-DAT-0100). `TaskFacetUpdate.start` et `finish` exigeaient un
`WorkInstant` entier, la date et les heures de travail écoulées ce jour-là sur le calendrier
applicable ; or le front ne connaît pas ce calendrier. La grille reprenait donc les heures que la
tâche portait à son ancienne date, ou `0` : un début à `4` déplacé à un jour de moins de quatre
heures aurait porté des heures que le calendrier n'accorde pas. L'entrée de `updateTaskFacet`
prend un schéma propre, `WorkInstantWrite`, dont `hours` est facultatif ; `WorkInstant` reste
celui des lectures, `hours` exigé. Sans `hours`, le serveur complète sur le calendrier applicable
de la tâche : le début au début de son jour (`0`), la fin au bout des heures que le calendrier
accorde ce jour-là. Envoyées, les heures sont prises telles quelles. Le front affiche, il ne
calcule pas.

**Des heures envoyées au-delà de celles du jour sont refusées, jamais bornées** (revue de #1244).
Un `WorkInstant` compte les heures de travail écoulées ce jour-là sur le calendrier applicable
(WF-DAT-0100) : il n'y en a jamais plus que le calendrier n'en accorde, ni moins de `0`. Des
heures hors de ces bornes — `{"date": <samedi>, "hours": "6"}` sur un calendrier sans samedi —
sont refusées par 422 `VALIDATION_FAILED`, `fields` sur `/start/hours` ou `/finish/hours` par
`VALUE_OUT_OF_RANGE`, `fields[].params` portant la seule borne franchie, `minimum` à `0` ou
`maximum` aux heures du jour, jamais nul depuis #1271 — un jour chômé est refusé par sa date, ses
heures n'étant pas jugées ; rien n'est écrit. Écarté :
borner les heures au maximum du jour. « Prises telles quelles » ne le permet pas — le serveur
écrirait une autre valeur que celle envoyée, sans le dire, et une fin envoyée à `10` sur un jour
de huit heures deviendrait `8` sans que le client le sache ; le refus dit la borne, que le client
connaît dès lors sans connaître le calendrier. Le motif est celui de toute borne incluse
franchie, `VALUE_OUT_OF_RANGE` (« Session et erreurs ») : aucun code nouveau, et le front le dit
déjà. La borne dépend du calendrier et du jour : le schéma ne la publie pas en `maximum`.
Exemple engendré : `task_hours_beyond_day`, la fin de la mise en service envoyée le vendredi
15 janvier 2027 à dix heures, refusée, `maximum` à `8` — un samedi à six heures jusqu'à #1271, où
`maximum` valait `0`.

**Un jour sans heure travaillée est refusé à la saisie, nommant le jour travaillé suivant ;
gardé et signalé à l'import** (décision de l'auteur du 2026-10-22, #1271 ; WF-PLA-0020 tel que
#1289 l'a réécrit). Elle remplace la règle de #1244 (commit 289c868e), qui gardait une telle date
le début et la fin à `0`, faute d'un texte. WF-PLA-0020 dit désormais : « Une date saisie sur un
jour sans aucune heure travaillée au calendrier applicable est refusée, et le refus nomme le jour
travaillé suivant ; rien n'est écrit. L'import d'un fichier MS Project garde une telle date telle
quelle, et le compte rendu la signale », et son Vérif : « Sur un calendrier du lundi au vendredi,
la date de début d'une tâche manuelle saisie un samedi est refusée, et le refus nomme le lundi
suivant ; la même date importée d'un fichier MS Project est gardée et signalée au compte rendu ».

- *La saisie* (`updateTaskFacet`) : 422 `VALIDATION_FAILED`, `fields` sur `/start/date` ou
  `/finish/date` par un motif nouveau, `NON_WORKING_DAY`, `fields[].params.date` la date envoyée
  et `next_working_day` le premier jour suivant qui compte des heures au calendrier applicable de
  la tâche — le front dit « le samedi 19 n'est pas travaillé sur le calendrier de la tâche ;
  saisis le lundi 21 » sans connaître ce calendrier. Une date chômée n'a pas d'heures : celles
  qu'on envoie avec elle ne sont pas jugées, et `VALUE_OUT_OF_RANGE` ne nomme plus jamais un
  `maximum` à `0`. Le début et la fin chômés tous deux font deux refus, un par champ.
- *L'import MS Project* : la date est gardée telle que le fichier la porte, le début et la fin à
  `0` comme la formule de #1244 le donne, et le compte rendu la signale dans un tableau nouveau,
  `ImportReport.signals`, toujours rendu comme les autres : un `ImportSignal` par date — la
  tâche (`lineage_id`, `label`), la colonne (`start`, `finish`), et le même motif avec les mêmes
  paramètres, pour que la saisie et l'import se disent d'une même phrase (WF-ARC-0110). Ni rejet
  ni confirmation : WF-PLA-0020 garde la date. Le signalement suit la cellule, non le jour, comme
  le refus de la saisie suit le champ : un jalon dont le début et la fin tombent le même jour
  chômé est signalé deux fois, `start` et `finish`, comme une tâche dont les deux dates sont
  chômées — les deux cellules de la grille portent la date, et un seul
  signalement laisserait l'une sans motif. `ImportSignal.code` est tenu à `NON_WORKING_DAY`
  (`const` à côté d'`ErrorCode`), seul signalement qui existe : un autre élargira la liste par
  une modification du contrat. Les modèles engendrés du service n'en gardent que `ErrorCode`.

Écartés : un code d'heure (`VALUE_OUT_OF_RANGE` sur `/start/hours`), qui ne dit pas la vraie cause
— le jour, non ses heures (défaut n° 10 du guide) — ni le jour suivant ; reporter la date au jour
suivant, que WF-PLA-0020 ne permet pas (« rien n'est écrit ») ; `TASK_WITHOUT_WORKING_HOURS`, qui
juge la semaine d'un calendrier, non un jour ; signaler l'import par `date_mismatches`, qui dit un
écart avec le recalcul de Waterfall, ou par `ignored`, qui dit ce qui n'est pas lu, quand la date
est lue et gardée.

**La création n'est pas touchée.** `TaskFacetWrite` (`createNode`) garde `WorkInstant` : la
décision vise la saisie d'une date dans la grille ; une création qui portera des dates saisies
suivra la même règle, par une modification du contrat.
*Remplacé par US-0640/L6 (#1345) : `createNode` refuse aussi une date manuelle un jour chômé.*

Exemple engendré (`wftools.mockgestures`) : `task_dates_sent`, le corps de `updateTaskFacet` qui
donne `task_dates_entered` — les dates de la mise en service, manuelle, envoyées par leur seule
date, rendues à `0` et `8` heures sur son calendrier. Le faux back complète désormais
les heures d'une tâche manuelle sur son calendrier applicable (`wftools.mockcore`), et non plus à
huit heures ; aucune réponse engendrée n'en change.

Exemples engendrés par `wftools.mocknonworking` (#1271) : `task_date_non_working_day`, le début de
la mise en service, manuelle, envoyé le samedi 19 décembre 2026, refusé, le lundi 21 nommé ; et
`import_planning_non_working_day` (`getImport`), le planning de la structure principale exporté
aujourd'hui et réimporté, la mise en service passée en mode manuel et commencée ce samedi : un
écart sur `scheduling_mode` et `start`, la date gardée et signalée, le lundi 21 nommé, les deux
calendriers du fichier ignorés et dits — une variante qu'`imports` ne reprend pas. Les autres
comptes rendus d'import portent `signals` vide. Le témoin #421 n'en est pas touché : aucun de ces
exemples ne rend de nœud.

## Les gestes du Kanban (EP-15/US-0540)

Partie K6 de la conception d'EP-15 (US-0540/L1, #1129), sur la décision de l'auteur du 2026-10-18
(#1070), et les décisions du 2026-10-21 que le lot reprend (#1235, #1240, #1247, #1154, #1273).

**Chaque carte liste ses gestes** (WF-RAE-0030, WF-IHM-0090). Les trois colonnes de
`listStartableTasks` rendent des `KanbanTask` : le nœud et `available_commands`, des
`KanbanCommandAvailability` sur `KanbanCommand` — `start`, `complete`, `reopen`,
`enter_remaining` —, chacun disponible ou non avec les conditions qui lui manquent ; une tâche non
démarrée est un `NotStartedTask`, qui garde `predecessors_completed`. Une carte ne liste que les
gestes que son état et sa nature admettent : `start` sur une tâche non démarrée qui n'est pas un
jalon, qui ne démarre jamais (WF-PLA-0050) ; `complete` sur toute carte non terminée, qui manque
de `task_is_milestone` pour une tâche non démarrée qui n'est pas un jalon, et de
`task_without_lines` pour une tâche qui porte une ligne hors provision ; `reopen` sur toute carte
terminée ; `enter_remaining`, qui renvoie à la grille de reste à engager sans rien écrire, sur
une carte non terminée qui porte une ligne hors provision. Une ligne de provision ne retient pas
une tâche de se terminer depuis le Kanban (WF-PLA-0050). Après les conditions du geste viennent
celles de `StructureCommand.edit_remaining` de la structure principale, `project_in_progress`
puis `no_background_task_running` : le Kanban est une saisie du reste à engager (FBS-4.5.3),
sous `remaining.write`, sans laquelle la liste est vide. Chaque geste dit aussi l'état qu'il
envoie à `setTaskProgress` (`progress`) : la réouverture d'un jalon envoie `not_started`, celle
de toute autre tâche `started`, et le front n'a pas à le déduire de `task.is_milestone`. Quatre
conditions s'ajoutent à `CommandCondition` : `task_is_milestone`, `task_not_milestone`,
`task_without_lines` et `completed_milestone`. Écartés : lister les quatre gestes sur chaque
carte, indisponibles hors de leur colonne, ce qui ferait nommer une condition à un geste qu'aucun
état de la tâche n'ouvrira jamais — la convention est celle de `edit_remaining`, jamais listée sur
un différentiel ; laisser au front le choix de l'état d'une réouverture.

**`not_started` pour un jalon terminé, et lui seul** (WF-RAE-0030). `ProgressUpdate.progress`
prend toute valeur de `TaskProgress`. « Un jalon terminé que l'on rouvre redevient non démarré,
seul cas où une tâche revient à cet état, et sa date de terminaison est effacée » ; `not_started`
envoyé pour toute autre tâche est refusé par 409 `STATE_FORBIDS_OPERATION`,
`params.missing_condition` à `completed_milestone` — une tâche démarrée par erreur se corrige en
annulant la saisie (WF-IHM-0110). La description de `ProgressUpdate`, qui disait qu'« aucun geste
ne la ramène à “non démarrée” », est réécrite. Le 409 de `setTaskProgress` nomme la première
condition qui manque, comme la carte : `task_is_milestone`, `task_without_lines`,
`task_not_milestone` (un jalon envoyé à `started`), `completed_milestone`.

**Le 200 de `setTaskProgress` ne rend pas les lignes de la tâche** (#1154). Elles ne sont pas
écrites ; ce qu'elles acceptent suit pourtant l'état de leur tâche — une ligne d'une tâche démarrée
dont le sous-projet a reçu des coûts réels ne nomme plus `estimate_line.subproject_id`, une ligne
d'une tâche terminée n'accepte plus la réestimation. Le contrat dit qu'une grille qui les tient
les relit (`listNodes`, `subtree_of`). Écarté : les rendre dans `nodes`, à la version qu'elles
gardent, ce qui ferait rendre un même nœud à une même version avec deux contenus (#421).

Exemples engendrés par `wftools.mockkanban` : `startable_tasks` et `startable_tasks_milestone`
disent les gestes de chaque carte ; `task_started`, le montage des armoires sur site démarré le
3 juin, à la suite de `predecessor_set` qui l'avait écrit, une version de plus, ses dates
inchangées et sa date de démarrage celle du geste ; `milestone_completed`, la réception usine,
jalon sans ligne, terminée le 3 juin à la suite de `task_attached`, sa date prévue du 30 juin
gardée ; `task_reopened`, les études de détail rouvertes, démarrées ; `milestone_reopened`, la
réception des études rouverte, non démarrée ; `task_reopen_not_started_refused`, les études de
détail envoyées à l'état non démarré. Le faux back date désormais un geste du Kanban par le jour
où il est fait (`Task.declared_on`), et non plus par les dates de la tâche (WF-PLA-0130) ; aucune
autre réponse engendrée n'en change.

*Réécrit en partie par US-0701/L3 (#1603, F-13, L-13 ; WF-PLA-0130 du 2026-10-10, recadrage du
2026-10-28) : un jalon terminé, qui ne passe jamais par l'état démarré, prend pour date de
démarrage celle de sa terminaison, et rouvert, perd l'une et l'autre ; `milestone_completed` porte
`started_on` au 3 juin.*

**Le plafond des préférences se vérifie une fois la modification fusionnée** (#1235).
`grids` et `timelines` étaient bornés à cent entrées par requête, mais des `PATCH` successifs
faisaient grandir la table gardée. Le service compte les entrées après la fusion : une
modification qui porterait l'une ou l'autre au-delà de cent est refusée par 422
`VALIDATION_FAILED`, `fields` sur `/grids` ou `/timelines` par `VALUE_TOO_LONG`, rien n'étant
écrit. Une modification qui n'accroît pas la table — qui en oublie ou en remplace des entrées —
n'est jamais refusée pour sa taille : une table déjà plus grande, gardée avant cette règle, peut
toujours décroître. Une modification qui porte aussi la langue l'a déjà dite au fournisseur
d'identité quand elle est refusée ; le choix de la langue renvoyé répare le désaccord, comme le
dit « Les préférences d'affichage… ». `backend/tests/test_users_personal.py` cumule cent une
chronologies, puis cent une grilles, sur deux `PATCH`.

**La part de gravité d'un risque sur une assiette nulle** (#1240). `RiskMatrixPoint.severity_ratio`
passe dans l'enveloppe `Computable`. Sur une assiette nulle — un projet sans budget de référence
dont le devis ne porte encore que des provisions —, elle n'est pas calculable, motif
`no_reference_budget`, et le risque est au niveau de gravité le plus bas, compté dans la case de
sa probabilité ; le graphique ne trace pas de bulle sans ordonnée. Le motif existant dit la cause
— l'assiette est le budget de référence, et à défaut un total qui ne le remplace pas ici — sans
clé nouvelle à traduire. Écartés : un motif nouveau, qui dirait la même chose ; le risque hors de
la matrice, que les cases ne compteraient plus alors que le registre le liste. Exemple :
`risk_matrix_no_basis`, variante contrefactuelle, le registre du témoin lu sur une assiette nulle.

**Le plan de charge du projet porte le total de chaque mois** (#1247). `WorkloadPlan.monthly_totals`
donne, comme `PortfolioWorkload.monthly_totals`, des `{month, hours}`, la somme des heures des
rôles retenus : du premier au dernier mois qu'un rôle charge, croissants et sans trou, un mois
sans charge à zéro, vide quand aucun rôle n'est chargé. Le plan d'un projet n'a pas de `months` à
la racine — chaque rôle ne porte que les mois qu'il charge — : chaque total nomme son mois.
Les quatre exemples `workload*` le portent ; le front le dessine en US-0550/L5 (#1259).

**Les heures d'un instant de travail dans le catalogue de `Problem.params`** (#1273).
`/start/hours` et `/finish/hours` de `updateTaskFacet` y sont nommés, `minimum` à `0` et
`maximum` aux heures du jour. Le type `Hours` est un décimal signé, qui n'interdit pas le négatif :
la borne `minimum` reste, et a son exemple, `task_hours_below_zero`, un début envoyé à `-1` heure.

## L'état replié d'un graphique est une préférence d'affichage, par graphique (EP-15/US-0550/L6)

Décision de l'auteur du 2026-10-22 sur #1275, point 1 : la matrice des risques de l'écran d'un
projet démarre repliée (#1252), et son dépliage se garde dans les préférences de l'utilisateur.

**Une table par graphique, comme les grilles et les chronologies.** `DisplayPreferences.charts`,
une table par nom de graphique de `ChartPreferences` — `folded`, un booléen exigé —, bornée comme
`grids` et `timelines` (#874, #1235) : cent graphiques, des noms de 64 caractères au plus,
`VALUE_TOO_LONG` sur `/charts` au-delà, y compris une fois la modification fusionnée. Une
modification ne remplace que les graphiques qu'elle nomme ; un graphique à `null` retrouve l'état
que son écran lui donne d'abord, et un graphique absent le prend aussi. `charts` à `null` et
`folded` nul ou absent sont refusés par `VALIDATION_FAILED` à leur pointeur, comme les autres
réglages qui ne le sont jamais. Le nom est celui du graphique sur son écran, comme celui d'une
grille : `risk_matrix`, la matrice de l'écran des risques d'un projet, une seule préférence pour
tous les projets — l'écran se retrouve tel que l'utilisateur l'a laissé, quel que soit le projet
ouvert. Le back sert le champ sans table ni migration : `waterfall.core.users.personal` fusionne
`charts` graphique par graphique, et `waterfall.api.me` en refuse le nul. Exemples
`preferences_risk_matrix_unfolded`, dernier des réponses de `updateMyPreferences`, et
`me_grid_settings`, qui porte la matrice dépliée ; `tools/tests/test_mockbounds.py` tient les noms
et les états des exemples.

Écartés : un booléen à la racine des préférences (`risk_matrix_folded`), qui obligerait un champ
nouveau du contrat pour chaque graphique qui se replie ; un état par projet, une table par
`project_id`, que la décision ne demande pas et qui ferait redéplier la matrice à chaque projet
ouvert ; et une table par écran plutôt que par graphique, qui confondrait deux graphiques d'un même
écran.

## La lecture du planning dit sa date de calcul et ses jours chômés (EP-15/US-0530)

Partie K10 de la conception d'EP-15 (US-0530/L4), sur les décisions de l'auteur du 2026-10-24
(#1404, #1406, #1410) : les exports d'image du Gantt et d'une chronologie nomment la date de calcul
(WF-IHM-0130), et le Gantt teinte les jours chômés de chaque tâche ; ni l'une ni les autres
n'étaient dans la lecture du planning.

**La date de calcul est un fait de la lecture** (#1404). `NodeListMeta.scheduled_at`, un
`Timestamp` exigé : l'instant du dernier calcul des dates de la structure lue — la dernière écriture
qui l'a redatée, sa création comprise, ou son import —, quels que soient les filtres, la recherche,
`kinds` et `fields`, comme `summary_depth`. Une révision marquée n'étant plus redatée (WF-DAT-0020),
elle garde l'instant du dernier calcul qui a précédé son marquage. `RevisionComparison.meta`
reprenant `NodeListMeta`, une comparaison le porte aussi, pour la révision comparée : elle se lit
comme `listNodes` (#1193, ci-dessus), et sa conséquence ne demande aucun schéma de plus. Le faux back
dit l'instant du témoin, le 3 juin 2026 à 14 h 05, de toute lecture d'une structure en cours
(`mockwitness.SCHEDULED_AT`) — il date une structure en la lisant, et aucune écriture du témoin ne
vient après —, et l'instant de son marquage d'une révision comparée (`mockcomparisons`, d'après
`mockhistory.REVISIONS`) : la fusion de l'avenant 1, qui redate la référence et la marque, le 1er
février 2026 à 9 h, et le marquage de l'offre, le 15 décembre 2025 à 16 h, pour la paire
identique — le témoin ne datant aucune des écritures qui ont précédé ce marquage, le faux back tient
le marquage pour leur dernier calcul. Une révision comparée non marquée, en cours, est lue comme toute structure en cours : à l'instant du témoin. Écartée : `CostStructure.scheduled_at`, qui obligerait le front à lire la liste des
structures pour dater ce qu'il lit des nœuds, quand `NodeListMeta` dit déjà ce que la lecture dit
de la structure lue.

**Chaque tâche porte les heures de son calendrier applicable, `TaskFacet.calendar_hours`** (#1410,
option A). Un `WeeklyHours` exigé, calculé : chaque jour, le plus petit des nombres d'heures que les
calendriers des rôles des lignes de main-d'œuvre de la tâche lui accordent, le calendrier par
défaut sans aucune (WF-PLA-0010) ; un jour à 0 heure est un jour chômé, le contrat ne connaissant
pas de jours fériés (WF-REF-0110). C'est une propriété de `Node` que `fields` nomme
(`task.calendar_hours`), rendue de toute lecture sans `fields` ; sur une révision marquée, ce sont
les heures des calendriers qu'elle fige (`EmployedReference`).
- *Le nom.* `calendar_hours` se range à côté de `calendar_id` et dit ce qu'il porte, les heures du
  calendrier ; `weekly_hours`, le nom de la même forme dans `CalendarImage`, aurait fait lire un
  calendrier du référentiel là où une tâche à deux rôles porte leur intersection, qui n'en est aucun,
  et, dans une facette où `hours` et les totaux comptent la charge, les heures de travail de la
  tâche. `calendar_id` ne suffit pas : une intersection n'a pas d'identifiant, et le front devrait
  lire le référentiel et la recalculer, ce que WF-ARC-0020 refuse à un écran.
- *Les récapitulatives et les jalons.* La même règle, sur les seules lignes qu'ils portent : une
  récapitulative tire de ses subordonnées ses dates, sa durée et son état, non son calendrier, et sa
  durée est le temps de travail entre ses dates « sur son calendrier applicable » (WF-PLA-0040) ; un
  jalon a une date, refusée saisie sur un jour sans heure de ce calendrier (WF-PLA-0020). Le Gantt teinte ainsi la
  barre d'une récapitulative sur le calendrier même où sa durée se compte. Écartés : une
  récapitulative sans calendrier, nul ou omis, dont la barre ne se teinterait pas ; l'intersection
  des calendriers de son sous-arbre, qu'aucune exigence ne dit, et qui contredirait celui de sa
  durée ; et les seules `WeeklyHours` du calendrier par défaut dans `NodeListMeta`, qui montreraient
  travaillé un jour que le rôle d'une tâche ne travaille pas.

Le générateur calcule le calendrier applicable depuis les lignes (`wftools.mockcalendar.applicable`),
et date désormais une récapitulative sur le sien, non sur le calendrier par défaut — aucune
récapitulative du témoin ne porte de ligne de main-d'œuvre, et rien ne change de ses dates. Les
lectures et les écritures de nœuds régénérées le rendent : sur la semaine standard pour presque
toutes, sur la semaine de quatre jours de dix heures pour les tâches du monteur câbleur, et, dans
`estimate_line_redated`, sur l'intersection des deux — huit heures du lundi au jeudi — quand le câblage
sur site passe au monteur câbleur à côté du technicien de mise en service ; `skeleton_generated`,
écrit à la main, porte le calendrier par défaut. `tools/tests/test_mockcore.py`, qui tient les
lectures de `listNodes`, confronte le calendrier de chaque tâche lue aux calendriers et aux rôles
écrits à la main, et la date de calcul de chaque lecture à la chronologie du témoin ;
`tools/tests/test_mockdating.py` date une récapitulative qui porte une ligne du monteur câbleur sur
son propre calendrier, trois jours et demi pour les trois jours de sa subordonnée.
`test_mocklists.py`, que nomme la conception, tient les listes écrites à la main (`wftools.mocklists`),
non les lectures des nœuds.

**Le couloir d'une tâche dans `me_grid_settings`** (#1406). La disposition du « Comité de
pilotage » range aussi la « Mise en service » (`…0565`) au couloir 2, sous les études, à côté
desquelles l'empilement automatique la range : jusque-là, l'exemple ne plaçait que deux jalons, qu'une
frise ne range pas, et sa disposition se dessinait comme l'automatique.

## Le contrat figé (EP-16)

EP-16 fige le contrat : `info.version` passe à `1.0.0` par son dernier lot de contrat (US-0640/L5).
Chaque modification qu'il y apporte a son entrée ici, avec ses exemples ; ensuite, toute
modification du contrat par un EPIC de domaine passe par une issue « contrat » que l'auteur tranche,
et s'inscrit à son tour dans cette section (décision de l'auteur du 2026-10-22, conception
d'EP-16).

### Le nom de l'entreprise dans les paramètres communs (US-0600, #1314)

WF-EXP-0020 fait saisir à l'installation le nom de l'entreprise utilisatrice, modifiable ensuite,
que portent les fichiers exportés ; le contrat ne le lisait ni ne l'écrivait. Décision de l'auteur
du 2026-10-22 : il se range dans les paramètres communs, à côté de la devise.

- **La lecture.** `ReferenceSettings.company_name`, exigé : un texte de 1 à 200 caractères, qui
  n'est pas fait seulement de blancs (`pattern: '\S'`, « Aucun libellé fait seulement de
  blancs »). Deux cents caractères, comme le libellé d'une nature ou d'une catégorie.
- **L'écriture.** `ReferenceSettingsWrite.company_name`, facultatif comme les autres champs de
  `updateReferenceSettings` : absent, le nom reste tel qu'il est. Il relève de
  `cost_settings.write`, la fonction des paramètres de coûts, dont l'écran le montre à côté de la
  devise, sur le modèle de la permission par champ qu'a déjà l'opération — la matrice sous
  `risk_settings.write`, les seuils et le délai sous `indicator_settings.write`. Une session qui
  ne la porte pas est refusée par 403, `PERMISSION_MISSING`, `params.missing_permission` à
  `cost_settings.write` ; rien n'est écrit. Il prend le compteur commun des paramètres, si bien
  qu'une écriture du nom rend périmée une lecture que l'écran des risques ou des indicateurs
  tenait, et inversement (412, WF-IHM-0110).
- **Les refus.** Le nom ne peut être ni vide ni blanc ; absent, il reste tel qu'il est. Un nom
  vide est refusé par 422 `VALIDATION_FAILED`, `fields` désignant `/company_name` par
  `VALUE_REQUIRED` ; un nom de plus de 200 caractères, par `VALUE_TOO_LONG` ; un nom fait
  seulement de blancs, comme tout libellé, par le code de champ `VALIDATION_FAILED` au même
  pointeur.
- **Les exemples**, écrits à la main : le témoin s'appelle « Delmas Automatismes » dans
  `reference_settings` et dans les deux écritures qui le laissent tel qu'il est
  (`reference_settings_matrix_updated`, `reference_settings_thresholds_updated`) ;
  `reference_settings_company_updated`, dernier des 200, le corrige en « Delmas Automatismes
  Industriels », version 2 ; `reference_settings_company_refused`, un nom vide, vient parmi les 422
  après le refus des bornes, que le faux back sert d'abord. Aucun nouvel exemple de 403 :
  `reference_settings_permission_missing` montre déjà la forme du refus, que la description de
  l'opération étend à `cost_settings.write`. `tools/tests/test_mocksettings.py` tient le nom de
  chaque lecture, la seule différence de l'écriture du nom, son refus et sa permission.

Écarté : un réglage dans `Installation`, que `getInstallation` rend sans session, quand le nom ne
sert qu'aux fichiers exportés.

### Le client d'un projet et le code borné d'un sous-projet (US-0610, #1316)

WF-PRJ-0080 fait porter au projet le nom de son client, facultatif, que présente un devis exporté ;
WF-PRJ-0050 veut que le code d'un sous-projet nomme son onglet dans le fichier de reste à engager
(ANNEXE B), ce qu'Excel borne. Le contrat ne lisait pas le client et bornait le code à 50
caractères, sans autre règle (C-372, D-7 de la reprise du 2026-10-22).

- **Le client.** `Project.client`, `ProjectCreate.client` et `ProjectUpdate.client`, un même
  schéma, `ProjectClient` : de 1 à 300 caractères comme le libellé, jamais blanc, nullable et
  facultatif — aucune transition ne l'exige. `createProject` et `updateProject` l'écrivent ; nul,
  `updateProject` l'efface, absent, il ne change pas. Un client vide est refusé par 422
  `VALIDATION_FAILED`, `fields` désignant `/client` par `VALUE_REQUIRED`, trop long par
  `VALUE_TOO_LONG`, fait seulement de blancs, comme tout libellé, par `VALIDATION_FAILED`.
  Il n'est pas exigé dans la lecture, comme la description et le code du projet.
- **Le code d'un sous-projet déclaré.** `Subproject.code` et `SubprojectWrite.code` (donc
  `SubprojectUpdate`) partagent `DeclaredSubprojectCode` : de 1 à 31 caractères — la borne d'un
  nom d'onglet —, sans `:`, `\`, `/`, `?`, `*`, `[` ni `]`, et ni « Synthèse » ni « Hors
  sous-projet », les deux onglets que Waterfall nomme, comparés sans égard à la casse. Le motif
  le dit par une anticipation négative, chaque lettre des deux noms écrite dans ses deux casses :
  JSON Schema n'a pas de comparaison sans casse, et le motif se lit pareil en ECMAScript et en
  Python (les modèles engendrés du service le compilent par `re`), à une exception près : un saut
  de ligne final. En Python, `$` s'arrête aussi avant un `\n` final, si bien que « Synthèse\n »
  est refusé ; en ECMAScript, `$` est strict et « Synthèse\n » passe.
- **Les refus.** Un code trop long : 422 `VALIDATION_FAILED`, `fields` désignant `/code` par
  `VALUE_TOO_LONG`, `fields[].params.max_length` à `31`. Un caractère interdit ou un nom réservé :
  un code nouveau, `SUBPROJECT_CODE_INVALID`, avec `fields[].params.forbidden_characters`, les
  caractères interdits que porte le code, chacun une fois, dans l'ordre où il les porte — ce que le
  formulaire peut nommer — ou `fields[].params.reserved_name`, le nom réservé tel que Waterfall
  l'écrit. Le front dit ce code par son catalogue (`errors.SUBPROJECT_CODE_INVALID`) ; les
  paramètres, l'écran du sous-projet les lira (US-0610/L2).
- **Ce qui garde sa borne.** `ActualCostLine.subproject_code`, le code lu dans l'élément d'OTP
  d'une ligne de coût réel, garde ses 50 caractères : une ligne au code inconnu se conserve telle
  quelle (WF-CRE-0020), et la borne d'un sous-projet déclaré ne vaut qu'à son écriture (conception
  d'EP-16).
- **Les exemples.** Le témoin, PRJ-001, a pour client « Papeteries de la Vienne » dans chacune de
  ses lectures ; PRJ-002 et le projet créé aujourd'hui n'en ont pas (`null`). Écrit à la main,
  `subproject_code_invalid`, un sous-projet créé ou recodé sous « SP/01 », le code de la Vérif
  de WF-PRJ-0050, refusé, la barre oblique nommée — cité par `createSubproject` et
  `updateSubproject`. Engendré, `import_remaining_subproject_held` nomme son onglet par le code du
  sous-projet, « SP-ESS », et non plus par son libellé. Les codes du témoin, « SP-CMD » et
  « SP-ESS », respectaient déjà la borne : `tools/tests/test_mockclientcode.py` tient chaque code
  de sous-projet des exemples sous le motif, le motif contre les codes de la Vérif, et le client de
  chaque lecture d'un projet.

Écarté : `not: { enum: [...] }` pour les noms réservés, qui comparerait avec la casse ; et un motif
appliqué aussi au code lu d'une ligne de coût réel, qui refuserait d'importer une ligne que
WF-CRE-0020 veut conserver.

### La correspondance de l'extraction des coûts réels (US-0620, #1318)

WF-REF-0190 fait déclarer, pour l'installation, les intitulés sous lesquels l'extraction de l'ERP
nomme les cinq colonnes que l'import lit, et les colonnes qu'il conserve (C-374) ; le contrat ne
la lisait ni ne l'écrivait, et l'élément d'OTP du témoin portait un préfixe `WF.` que C-373 a
retiré de la spécification. Ce que la conception d'EP-16 décide est repris tel quel ; ce qui suit
dit aussi ce que le lot (US-0620/L1) a fixé de forme, là où elle se taisait.

- **Un objet unique de l'installation**, lu et remplacé entier avec son compteur, comme les
  unités de durée : `getActualCostMapping` (`GET /reference/actual-cost-mapping`, sous
  `cost_settings.read`, 404 sans elle comme toute lecture interdite) et `setActualCostMapping`
  (`PUT`, sous `cost_settings.write`, 403 `PERMISSION_MISSING` sans elle, 412
  `STALE_LOCK_VERSION` sur un compteur périmé). Écartée par la conception : une opération par
  colonne, la règle des doublons portant sur toute la correspondance.
- **La lecture** (`ActualCostMapping`) : `columns`, les cinq `ActualCostSourceColumn` dans l'ordre
  fixe de l'énumération — `wbs_element`, `document_number`, `document_item`, `document_date`,
  `amount` —, chacune avec `required`, rendu par le serveur (faux pour le seul poste), et
  `labels`, au plus 20 ; `kept_columns`, au plus 50 ; `is_complete` et `missing_columns`,
  calculés — les colonnes exigées sans intitulé, dans l'ordre de la correspondance — ;
  `lock_version` et `audit`. Une correspondance vide naît à l'installation, par la plateforme, à
  sa version 1, comme les unités de durée.
- **L'écriture** (`ActualCostMappingWrite`), choix de forme du lot : le corps reprend celui de la
  lecture, sans ce que le serveur rend — ni `required`, ni `is_complete`, ni `missing_columns`, ni
  `audit` —, si bien que l'écran renvoie ce qu'il a lu, modifié. Les cinq colonnes y viennent
  chacune une fois, dans l'ordre de l'énumération ; un corps qui ne les porte pas ainsi est refusé
  par 422 `VALIDATION_FAILED` au pointeur `/columns`. Écartés : `prefixItems`, qui l'aurait dit au
  schéma mais que les générateurs du client et des modèles du service ne lisent pas sûrement ; un
  objet indexé par colonne, qui aurait donné à l'écriture une autre forme que la lecture.
- **Un intitulé** (`ActualCostColumnLabel`) a de 1 à 200 caractères et n'est jamais blanc
  (`pattern: '\S'`), règle de tout libellé du contrat, choix de forme du lot : un intitulé blanc
  se normaliserait en vide et ne désignerait rien. Vide, il est refusé par `VALUE_REQUIRED`,
  trop long par `VALUE_TOO_LONG`, blanc par `VALIDATION_FAILED` ; une liste trop longue par
  `VALUE_TOO_LONG` à son pointeur, comme le service le rend pour toute liste bornée.
- **Les doublons** : `DUPLICATE_COLUMN_LABEL`, nouveau code, motif par champ d'un 422
  `VALIDATION_FAILED`, au pointeur de l'intitulé en double, `fields[].params.duplicate_of` le
  pointeur de l'autre. Choix de forme du lot : de deux intitulés qui se doublent, le second dans
  l'ordre du corps — les colonnes lues dans leur ordre, chacune ses intitulés dans le leur, puis
  les colonnes conservées — est désigné ; de trois ou plus, chacun après le premier, que tous
  nomment, comme `DUPLICATE_WORK_BREAKDOWN_ITEM`. La comparaison est celle de WF-REF-0190 : sans
  égard à la casse, aux accents ni aux espaces en bout.
- **Le refus de l'import** : `actual_cost_mapping_complete` rejoint `CommandCondition`. La
  commande `import_actual_costs` du projet la nomme, après les conditions de l'état du projet et
  des traitements de fond — choix de forme du lot : l'état du projet dit d'abord pourquoi rien ne
  s'y importe, et la correspondance est une condition de l'installation, que le projet ne règle
  pas. `openImport` d'un fichier de coûts réels la nomme dans son 409 `STATE_FORBIDS_OPERATION`,
  `params.columns` les colonnes exigées sans intitulé, dans l'ordre de la correspondance.
- **La colonne exigée absente** : 422 `FILE_FORMAT_UNREADABLE`, `params.missing_columns` chaque
  colonne exigée que le fichier ne porte sous aucun de ses intitulés, `{column, labels}`, les
  intitulés que la correspondance déclare ; sans `expected_version`, une extraction de l'ERP n'en
  ayant pas (D-2). Choix de forme du lot : `params.expected_format` à `actual_costs` reste, le
  refus nommant le format attendu (WF-INTF-0070) comme pour les autres formats.
- **Les colonnes ignorées** : `ImportIgnoredKind` gagne `columns`, les colonnes du fichier ni lues
  ni déclarées conservées, nommées par leur intitulé tel que le fichier le porte, dans son ordre
  (`ImportIgnored.labels`).
- **Un import analysé s'applique tel qu'il a été analysé**, même si la correspondance change
  entre-temps : le compte rendu confirmé est ce qui s'applique (WF-INTF-0080), et une modification
  de la correspondance ne change aucune ligne déjà importée (WF-REF-0190). `applyImport`,
  `openImport` et `setActualCostMapping` le disent. Écarté par la conception : un 409 à
  l'application.
- **L'élément d'OTP n'est pas exposé** à la consultation : il se reconstruit du code projet et de
  `subproject_code`. Colonne lue, il ne peut être aussi conservé — son intitulé doublerait le
  sien —, et le témoin le retire de ses colonnes conservées.
- **Les exemples**, écrits à la main : `actual_cost_mapping`, la correspondance du témoin, premier
  exemple, déclarée par Camille Martin le 3 avril 2026 à 8 h 15, avant le premier import, avec les
  intitulés du Vérif (« Elément d'OTP », « Nº pièce référence », « Date de la pièce », « Val./Devise
  objet »), sans poste — « Poste » depuis US-0630 —, et les colonnes conservées du témoin,
  « Fournisseur » et « Texte de commande » ; `actual_cost_mapping_empty`, celle d'une installation
  neuve ; `actual_cost_mapping_updated`, « Document d'achat » déclarée conservée aujourd'hui,
  version 3 ; `actual_cost_mapping_duplicate`, « Élément d'OTP » déclarée conservée, refusée comme
  doublant l'élément d'OTP ; `actual_cost_mapping_stale` ; `project_actual_cost_mapping_incomplete`,
  le projet témoin dont la commande attend la correspondance, et
  `import_actual_cost_mapping_incomplete`, le 409 d'`openImport`, variantes contrefactuelles sur une
  installation à la correspondance vide ; `import_actual_costs_column_missing`, une extraction sans
  montant ; `import_actual_costs_column_ignored`, l'extraction d'avril rejouée, variante
  contrefactuelle qui porte aussi « Nom Matricule », ignorée.
- **Le témoin**, engendré : « Élément d'OTP » quitte ses colonnes conservées
  (`mockwitnesscosts.PASSTHROUGH`), si bien que les consultations et les écritures de ses coûts
  réels ne le restituent plus ; son élément d'OTP est le code projet, suivi de `/` et du code
  sous-projet pour une ligne qui en a un, sans préfixe (`mockcosts.wbs_element`, C-373), et le
  résumé de `actual_costs` le nomme. `tools/tests/test_mockmapping.py` tient la correspondance du
  témoin et les colonnes conservées de ses lignes d'accord, chaque correspondance lue, la règle des
  doublons, les refus de l'import et les éléments d'OTP des exemples.

### Le poste d'une ligne de coût (US-0630, #1322)

WF-INTF-0140 et WF-CRE-0010 font porter à une ligne de coût le numéro de son poste dans la pièce,
facultatif, et l'identifient par sa pièce et son poste : une facture ventilée sur deux éléments
d'OTP donne deux lignes. Le contrat ne connaissait que le numéro de pièce. Décision D-4 de la
reprise du 2026-10-22 : une ligne de coût est identifiée par le projet, le numéro de pièce et le
numéro de poste ; la contrainte d'unicité, sa migration et l'idempotence de WF-DAT-0110 sur ce
triplet sont le service, en EP-09.

- **La lecture.** `ActualCostLine.document_item`, exigé et nullable, comme `subproject_code` : un
  texte tel que l'extraction le porte, sans borne, comme le numéro de pièce ; nul quand
  l'extraction n'en donne pas — la correspondance ne déclare pas le poste, ou la cellule est vide.
  Un poste nul est une valeur comme une autre : deux lignes de la même pièce sans poste sont la
  même ligne.
- **Le tri.** `ActualCostColumn` et le `sort_by` de `listActualCosts` gagnent `document_item`,
  comparé en texte comme le motif et les colonnes conservées, une ligne sans poste après les
  autres dans l'ordre croissant. Comme le numéro de pièce, il identifie la ligne et n'est jamais un
  champ d'un écart `updated` : un autre poste de la même pièce est une autre ligne.
- **Le compte rendu.** `ImportDifference.document_item`, facultatif et nullable : pour une ligne de
  coût, le poste de la pièce que nomme `label` ; nul ou absent pour tout autre objet. Choix de forme
  du lot : un champ à côté de `label` plutôt qu'un libellé composé (« FA-2026-0412 / 10 »), que le
  front n'aurait pu ni trier ni dire dans la langue du lecteur.
- **Les lignes en double** : `DUPLICATE_COST_LINE`, nouveau code, motif d'un `ImportRejection`
  d'une extraction de coûts réels. Chacune des lignes du fichier qui portent la même pièce et le
  même poste, nul compris, est rejetée, `params.rows` nommant les rangs des autres dans l'ordre du
  fichier : aucune n'est préférée, puisque rien ne dit laquelle l'ERP voulait. `sheet` est nul,
  l'extraction n'ayant qu'un onglet. `applyImport` dit qu'un import insère ou met à jour sur la
  pièce et le poste.
- **Le témoin.** Avec la facture ventilée sur deux éléments d'OTP, la consultation des coûts passe
  de 27 à 28 lignes ; l'entrée plus haut qui en compte 27 reste l'état d'alors.
- **Les exemples.** Écrits à la main : la correspondance du témoin (`actual_cost_mapping`, et
  `actual_cost_mapping_updated` qui la reprend) déclare le poste sous « Poste » depuis le 3 avril
  2026, ses lignes en portant un — ce qui remplace « sans poste » de l'entrée d'US-0620 ;
  `import_actual_costs_analysed` et `import_actual_costs_column_ignored` désignent l'avoir
  AV-2026-0388, sans poste, et la facture FA-2026-0412, poste 10 ;
  `import_actual_costs_duplicate_line`, l'extraction d'avril rejouée, variante contrefactuelle
  dont le fichier porte aussi deux lignes de FA-2026-0417 sans poste, aux rangs 4 et 5, chacune
  rejetée en nommant l'autre — cité par `getImport`. Engendrés : chaque ligne du témoin porte son
  poste, 10 pour une pièce d'un poste — les factures des tâches tirées comprises
  (`mockcosts.INVOICE_ITEM`) —, aucun pour l'avoir ; la facture de l'automate, FA-2026-0301, est
  ventilée sur PRJ-001/SP-AUT et PRJ-001/SP-CAB en deux postes, 10 et 20, de 1 100,00 et 300,00,
  si bien que ses 1 400,00, sa date et son imputation au seul projet ne changent pas, ni aucun
  indicateur ni aucune courbe ; la consultation compte une ligne de plus, l'extraction de mars en
  crée trois et la réextraction en met six à jour. `tools/tests/test_mockcostitem.py` tient le poste
  de chaque ligne lue, la facture ventilée, la correspondance qui lit le poste, le compte rendu qui
  désigne une ligne par sa pièce et son poste, et le rejet des lignes en double.

Écarté : un rejet de la seule seconde ligne, qui aurait importé la première comme si l'ordre du
fichier disait laquelle compte.

### La résolution d'un numéro de ligne et les colonnes connues d'une grille (US-0650, #1326)

Deux constats reportés d'EP-15. La colonne des prédécesseurs de la grille de planning refusait comme
inconnu un numéro que les lignes lues ne portaient pas — une tâche écartée par la recherche ou un
filtre —, l'écriture ne prenant que `predecessor_node_id` (#1288, de #1257 point 1). Une colonne
masquée par défaut ne l'était que pour un compte qui n'avait jamais écrit `hidden_columns`, que
toute écriture de la grille enregistre (#1260, de #1232). Décisions de l'auteur du 2026-10-21 et du
2026-10-22, conception d'EP-16.

- **La résolution.** `resolveRowNumber`, `GET
  /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rows/{row_number}`, une
  lecture qui rend `RowNumberResolution` : `node_id`, `row_number`, `label` et `kind`, tous exigés,
  du nœud qui porte ce numéro dans la numérotation de toute la structure, celle de
  `Node.row_number`, quels que soient la recherche, les filtres et le tri. L'écriture reste en
  `predecessor_node_id` (`setPredecessors`), seule juge de la liaison. Choix du lot :
  - `kind` est un `NodeKind`, le type que `Node.kind` porte déjà : le front y lit qu'un numéro
    désigne une ligne de devis, qu'il refuse comme inconnu, puisque ce n'est pas une tâche ; la
    lecture ne refuse pas elle-même une ligne, qui a son numéro comme une tâche ;
  - `label`, celui de la tâche ou de la ligne, sans borne, comme `DependencyRow.label` : une
    lecture, que le front montre avec le numéro ;
  - un numéro qu'aucun nœud ne porte est un 404 `NOT_FOUND`, sans paramètre, comme un objet
    inexistant (README, 404 contre 403) : le numéro nomme un objet par le chemin. Un numéro qui
    n'est pas un entier d'au moins 1 est, lui, refusé par 422 `VALIDATION_FAILED` au pointeur
    `/path/row_number`, comme tout paramètre de chemin autre qu'un identifiant (« Un identifiant de
    chemin mal formé est un 404 ») ;
  - sur un différentiel, la numérotation est celle de `listNodes`, où chaque nœud retiré compte pour
    sa ligne ; le numéro d'un nœud retiré répond 404, ce nœud n'étant plus de la structure ;
  - les droits et les autres refus sont ceux de `listNodes` : la consultation du projet, un
    projet, une révision ou une structure invisibles répondant 404 sans rien distinguer ;
  - le chemin, `…/structures/{structure_id}/rows/{row_number}`, à côté de `nodes` : un numéro
    n'est pas un identifiant de nœud, et `nodes/{node_id}` le refuserait comme tel.
- **Les colonnes connues.** `GridPreferences.known_columns` : les clés des colonnes que la grille
  offrait à la dernière écriture de ses préférences, au plus 64, de 64 caractères au plus, comme
  `hidden_columns`, refusées au-delà par 422 `VALUE_TOO_LONG` (#874) ; écrite par
  `updateMyPreferences`, avec la grille remplacée entière, et lue par `getMe`. Une colonne masquée
  par défaut et absente de cette liste est masquée ; une colonne absente de la liste et non masquée
  par défaut est montrée. Choix du lot :
  - une colonne que `hidden_columns` nomme est masquée, connue ou non : la liste ne fait que dire
    ce que la grille connaissait, pour juger une colonne qu'elle ne nomme pas ;
  - la liste est facultative, comme les autres réglages d'une grille, mais jamais nulle : envoyée à
    `null`, elle est refusée par 422 `VALIDATION_FAILED` à son pointeur, comme `hidden_columns`
    (`NEVER_NULL_IN_A_GRID` du service) ;
  - absente — un compte qui ne l'a jamais écrite —, elle vaut une liste vide : toute colonne masquée
    par défaut que `hidden_columns` ne nomme pas est masquée. Une colonne masquée par défaut qu'un
    compte avait choisi d'afficher avant EP-16 se retrouve masquée une fois ; aucune installation ne
    précède la version 1.0.0 du contrat. Écartée : une liste absente valant toutes les colonnes de
    la grille, qui garderait le défaut constaté pour les comptes déjà réglés ;
  - le serveur la garde telle qu'elle est écrite : il ne connaît les colonnes d'aucune grille.

  Écartée : une liste des colonnes affichées, qui masquerait aussi une colonne nouvelle montrée par
  défaut (conception d'EP-16).
- **Les exemples**, écrits à la main : `row_number_task`, premier exemple, que le faux back sert
  quel que soit le numéro — le numéro 9 de la structure principale du témoin, « Câblage des
  armoires », une tâche que la grille de planning du groupe « Études » (`nodes_planning`) ne rend
  pas — ; `row_number_estimate_line`, le numéro 10, « Raccordement des borniers », une ligne ;
  `row_number_unknown`, le numéro 6001 d'une structure de 6 000 lignes, 404 (corrélation 1550).
  Les grilles de `me_grid_settings`, `me_auditor` et `preferences_page_size` portent les colonnes
  qu'elles offrent ; la grille de devis de `me_grid_settings`, réglée avant la colonne
  « Sous-projet », masquée par défaut, ne la connaît pas, si bien qu'elle reste masquée.
  `tools/tests/test_mockrownumber.py` tient chaque résolution au nœud que le premier exemple de
  `listNodes` numérote ainsi, le refus au-delà de la dernière ligne, et les colonnes masquées et
  élargies de chaque grille parmi celles qu'elle connaît.

Le front — la colonne des prédécesseurs qui résout un numéro hors des lignes lues, `grid/settings.ts`
qui lit et écrit `known_columns` — est US-0650/L2.

### Les exemples manquants et les descriptions du contrat (US-0640/L1, #1329)

Les mineurs des relectures d'EP-14 (L42p, L42q, L42s, L44c, L44d, L53) reportés jusqu'ici : #764,
#803, #817 point 2b, #747 points 2 à 9, #752 points 1 à 4, #795 ; et #1507. Chaque point a été relu
sur le contrat qu'EP-15 a laissé ; les points devenus sans objet sont dits dans leur issue, et
listés ici. Aucune opération nouvelle.

Sans objet ou hors du lot :

- #747 point 6, caduc : `risk_without_task.json` existait déjà, cité dans le 409 de `createRisk`.
- #752 point 4, la part M2, écartée : `deleteSubproject` répond 204, aucune réponse ne rend le
  risque modifié (voir le 412 du collage, ci-dessous).
- #747 point 1 et #817 point 1, qui touchent le front : hors de ce lot.

- **Le rejugement du collage** (#764, #747 points 7 et 8). `PasteRejection` dit les refus que la
  confirmation ajoute en jugeant de nouveau les lignes acceptées, et la règle d'EP-14/L42j y vaut :
  une cellule qui nomme une catégorie ou un rôle désactivés n'est refusée, à l'aperçu comme à la
  confirmation, par `INACTIVE_REFERENCE_OBJECT`, que si elle change la catégorie ou le rôle de sa
  ligne ; celle qui nomme ce que la ligne porte déjà n'est pas refusée, comme le parent d'un nœud,
  la catégorie d'un rôle ou celle d'un risque. Écarté : refuser toute cellule qui nomme un objet
  désactivé, qui refuserait de recoller une ligne telle qu'elle est. Exemple engendré,
  `paste_applied_rejudged`, dernier des 200 d'`applyPaste`, variante contrefactuelle déclarée : le
  bloc des parcours dont la deuxième ligne passe à « Ingénierie électrique », que la première garde,
  désactivée entre l'aperçu et la confirmation — la deuxième refusée, la première écrite et signalée
  (`uses_inactive_object`). Le bloc des parcours (`paste_plan`) nomme pour chaque ligne la catégorie
  qu'elle porte déjà : il ne pouvait pas montrer ce refus.
- **Le 412 du collage** (#752 points 3 et 4). La description d'`applyPaste` dit le compteur retenu à
  l'aperçu, que seuls `PasteApply` et `PasteApplied` disaient. Exemple engendré, `paste_stale` : la
  version que l'écriture d'après l'aperçu laisse, celle que `paste_applied` aurait prise ; le test
  la confronte à la réponse au lieu des seules phrases. Le test de M2 — la désignation passée à nul
  fait avancer le risque — reste un test de phrases : aucune réponse ne rend le risque modifié par
  `deleteSubproject` (204), et le service d'EP-08 l'éprouvera.
- **La dépendance du sous-projet d'une ligne de provision** (#764). Exemple engendré,
  `dependencies_provision_subproject` : `estimate_line.subproject_id`, que la ligne de provision
  calcule depuis EP-14/L42p, dépend de son risque.
- **Les lignes nommées par le refus de suppression d'un sous-projet** (#764). Chaque élément de
  `params.estimate_lines` porte `structure_label` : deux lignes de deux structures peuvent porter le
  même numéro, et l'écran les distingue sans lire `listCostStructures`. Écarté, comme l'issue le
  proposait : laisser l'écran lire les structures. `subproject_delete_estimated` le porte.
- **Un sous-projet que les lignes seules retiennent** (#764). Exemple écrit à la main,
  `subprojects_estimated`, dernier des 200 de `listSubprojects` : la variante de
  `subproject_delete_estimated`, la réception sur site délestée de sa facture et portant les lignes
  10 et 11, dont la suppression ne manque que de `subproject_without_estimate_lines`. Il remplace la
  variante que les tests du front construisaient.
- **Les refus des chronologies et du lotissement** (#803). Exemples, chacun en dernier sous son
  statut : `timeline_label_required` (422, `/label` par `VALUE_REQUIRED`, écrit à la main),
  `timeline_delete_terminal` (403 `PROJECT_TERMINAL`, écrit à la main), `work_breakdown_stale`
  (412, engendré par `wftools.mocklists` : le compteur de `work_breakdown_saved`). Le 403 d'un projet
  terminal porte `params.missing_condition` à `project_not_terminal`, comme le catalogue le dit des
  403 (`ErrorCode`, `Forbidden`) : c'est le premier exemple de ce refus.
*Remplacé par US-0702/L1 (#1610), sur la décision de l'auteur du 2026-10-28 (D-05, J-01, J-02) : `timeline_delete_terminal` est
  un 409 `STATE_FORBIDS_OPERATION`, `project_not_terminal` ; `PROJECT_TERMINAL` sort du catalogue, et
  le 403 ne dit plus que la permission ou la qualité de l'appelant. Le texte ci-dessus est gardé pour l'histoire.*
- **Un refus du rattachement à deux motifs** (#817 point 2b). Exemple écrit à la main,
  `task_attach_exclusive_attached`, dernier des 422 d'`updateTaskFacet` : « Câblage des armoires »
  envoyée avec le lot et le poste à la fois, le lot porté par « Poste de commande » —
  `WORK_BREAKDOWN_ITEMS_EXCLUSIVE` sur chaque champ et `WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED` sur le
  lot, que `TaskFacetUpdate` dit rendus ensemble.
- **La préséance des refus d'`updateRisk`** (#747 point 5). Le 409 `risk_identified` précède le 422
  de la catégorie, comme à la déclaration : une autre catégorie envoyée pour un risque écarté est
  refusée par l'état, qu'elle soit désactivée, inconnue ou d'un autre type.
- **L'ordre de `restored_subproject_exists`** (#752 point 1). La description de `CommandCondition` la
  dit après `may_create_revision`, où l'énumération et les catalogues la rangent ; son libellé
  anglais devient « subproject restored by the undo or redo not deleted since » (point 2), et le
  français « sous-projet rendu par l’annulation ou le rétablissement encore existant » : la condition
  vaut pour l'un comme pour l'autre.
- **Le projet terminal n'a pas de révision en cours** (#795 point 3). `project_completed` porte
  `current_revision_id` à nul, et `edit_risks` puis `declare_risk` après `abandon`, indisponibles,
  `project_not_terminal` seule manquant : la condition d'état vient avant `may_create_revision`, et
  le témoin a des tâches et une catégorie de provision active. Un projet sans révision en cours
  listant aussi `generate_skeleton`, avant les imports, le fichier le porte, indisponible,
  `project_not_terminal` puis `main_structure_without_tasks`. `wftools.mockaudit` ne lit de ce
  fichier que la date et l'auteur de la sortie. *Réécrit par US-0702/L3 (#1657) : le projet
  terminal ne liste plus aucune de ces commandes ; `project_not_terminal` n'est plus nommée que
  par le 409 de l'appel direct.*
  *Complétée par US-0701/L9 (#1609, D-01, D-02) : WF-CYC-0090, réécrite le 2026-10-10, dit
  comment le projet terminal n'en porte aucune — la sortie marque ou abandonne la révision en
  cours ; celle du témoin abandonne la 102, et `project_completed` ne liste plus aucune sortie
  (« Les projets : la sortie marque ou abandonne la révision en cours », dans « Le contrat
  figé »).*
- **Le rôle seul d'une tâche, au refus d'`updateCalendar`** (#795 point 1). Le 422 dit le second cas,
  comme ses routes sœurs depuis EP-14/L42s : le calendrier du seul rôle d'une tâche qui n'a plus
  aucune heure dans la semaine.
- **Une catégorie de provision passée à une nature d'un autre type** (#747 point 4). Une catégorie
  que désigne un risque écarté, que plus aucune ligne n'emploie, peut être rattachée à une nature
  d'un autre type (`cost_category_unused`, WF-REF-0030). `Risk.provision_cost_category_is_active`
  devient vrai quand la catégorie est « active et de type provision pour risques », et
  `RiskReviewWrite` comme `reviewRisk` reprennent la catégorie désignée à cette double condition,
  et la demandent sinon : WF-RIS-0010 désigne la catégorie « parmi les catégories actives de type
  provision pour risques », et WF-REF-0030 fait porter aux lignes de provision « la catégorie que
  chaque risque désigne ». Le nom du champ reste : il ne se renomme pas pour un cas que la
  désactivation couvrait déjà. Écarté : la seule activité, qui recréerait une ligne de provision
  sur une catégorie qui n'est plus de provision. `is_active_provision` lit le type de la nature,
  et un test l'éprouve sur la catégorie du témoin passée à « Débours ».
- **L'annulation et le rétablissement qui recréeraient une provision** (#795 point 2).
  `undoLastChange` et `redoLastUndo` sont refusés par 409 `STATE_FORBIDS_OPERATION` quand ils
  recréeraient la ligne de provision d'un risque — l'annulation de la suppression d'un risque
  identifié, du réexamen qui l'a écarté ou du changement de la catégorie de sa provision ; le
  rétablissement de sa création, du réexamen qui l'a rendu identifié ou de ce changement — sur une
  structure principale sans tâche, `at_least_one_task`, ou avec une catégorie qui n'est plus
  active et de type provision pour risques, `active_provision_category` : une annulation « subit
  les mêmes règles » (motif de WF-IHM-0110), et WF-RIS-0010 refuse le retour d'un risque écarté à
  l'état identifié dans ces deux cas. Aucune condition nouvelle, sur le modèle de
  `restored_subproject_exists` ; les trois se jugent dans l'ordre de l'énumération,
  `at_least_one_task`, `restored_subproject_exists`, `active_provision_category`, le refus nommant
  la première. N'envoyant rien, l'annulation ne peut pas désigner une autre catégorie : le refus
  vaut dès que la catégorie qu'elle rendrait n'est plus de provision active, même s'il en reste
  une autre — `CommandCondition` l'étend ainsi, pour ces deux opérations seules. Écarté : recréer
  la ligne sur la seule catégorie active restante, que l'utilisateur n'aurait pas choisie.
  Exemples écrits à la main, aucun outil ne jouant l'annulation : `undo_risk_without_task` (409
  d'`undoLastChange`, l'annulation du réexamen qui a écarté un risque d'un projet vidé de sa seule
  tâche) et `redo_risk_category_deactivated` (409 de `redoLastUndo`, le rétablissement du retour
  de `risk_reidentified` après la désactivation de sa catégorie). Le faux back ne joue pas ces
  opérations ; aucun test du front ne fabriquait leur enveloppe.
- **Le retour d'un risque écarté sur une structure principale sans tâche** (#787, que #795 point 2
  suppose). La décision de l'auteur du 2026-10-11 (option A), intégrée à WF-RIS-0010 par C-354,
  attendait encore le contrat : `reviewRisk` nomme `at_least_one_task` dans son 409, entre
  `risk_not_occurred` et `active_provision_category`, comme `createRisk`, et `RiskReviewWrite` le
  dit. Sans elle, l'annulation refusée par `at_least_one_task` aurait été plus stricte que le
  réexamen qu'elle rejoue. La commande `review` reste disponible : elle confirme et écarte sans
  tâche, et seul le retour est refusé, comme pour la catégorie. Exemple écrit à la main,
  `risk_review_without_task`, dernier des 409 de `reviewRisk`.
- **Les outils** (#747 points 2, 3 et 9 ; #1507). La docstring d'`is_active_provision` dit ce
  qu'elle lit, et un test l'éprouve sur la nature désactivée, la valeur fausse n'étant portée par
  aucun exemple ; celle de `_borne_by_the_current_revision` dit que l'univers ne tire aucune ligne
  dans les devis propres ; `test_mockclientcode.py` tient `subproject_code_reserved`.

**Corrélations** 1551 à 1558.

### Les comptes rendus et les paramètres des refus (US-0640/L2, #1330)

Les constats #768, #789 et #785 des relectures d'EP-14, relus sur le contrat qu'EP-15 a laissé, et
#1514, confié à ce lot par l'auteur le 2026-10-27. Aucune opération nouvelle.

Sans objet :

- #789, la tâche rangée ailleurs, caduc : `ImportDifference.fields` nomme `parent` depuis #1194
  (`ImportDifferenceField`), et `structure_merge_report` présente déjà la « Mise en service »
  déplacée sous les « Essais sur site » par un écart `updated` sur `duration` et `parent`. Les deux
  exemples que le constat visait ne s'en servaient pas encore : `structure_merge_report_refused` et
  `import_planning_rejected`, qui rangent « Câblage des armoires » sous « Installation sur site »,
  présentent désormais la tâche modifiée par son parent, à côté du motif qui les refuse.

- **Les paramètres des refus reçoivent un schéma** (#768, point 3 ; décision du cadrage d'EP-16).
  `ProblemParams` déclare, facultatifs et typés, ceux que plusieurs refus partagent, chacun dans la
  forme que ses refus et ses exemples lui donnaient déjà : `resource_roles`
  (`ProblemResourceRole` : `resource_role_id`, `code`, `label`), `projects` (`ProblemProject` :
  `project_label`, `project_code` nul pour un projet sans code), `tasks` (`ProblemTask` :
  `project_id`, `node_id`, `label`, ou `ProblemImportedTask` au motif d'une ligne importée,
  ci-dessous), `estimate_lines` (`ProblemEstimateLine` : `structure_id`, `structure_label`,
  `node_id`, `row_number`, `label`), `subproject` (`ProblemSubproject` : `subproject_id`, `label`),
  `columns` (des `ActualCostSourceColumn`) et `missing_columns` (`ProblemMissingColumn` : `column`,
  `labels`), avec `state_enum` et la règle qui le lie à `state`. Il reste ouvert aux autres
  (`additionalProperties: true`), que la description de `Problem.params` continue de dire. Il est
  le schéma de `Problem.params`, et aussi de `FieldProblem.params`, `PasteRejection.params`,
  `ImportRejection.params`, `ReportRefusal.params` et `ImportSignal.params` : chacun « porte les
  paramètres de son code dans un refus », que le front lit d'une même fonction
  (`i18n/problem.ts`), et `subproject` n'existe que dans les paramètres d'un champ, d'une cellule
  ou d'une ligne. Le client les reçoit typés, non plus en `unknown`. Écarté par le cadrage : un
  schéma par code d'erreur (`oneOf`), qui doublerait le catalogue. Le service range ses paramètres
  dans `ProblemParams` et laisse absent ce que l'erreur ne donne pas, sans écrire `null` : un nul
  que les paramètres portent, le code d'un projet qui n'en a pas, n'est plus retiré de l'enveloppe
  (`waterfall.api.problems`) ; une propriété typée donnée à `None` est laissée absente, et une forme
  que le schéma ne donne pas est une défaillance du service (500 `INTERNAL_ERROR`). Le nom du
  modèle engendré change avec le schéma (`Params` devient `ProblemParams`), et les objets ouverts
  que le test « aucune phrase » admet se réduisent à lui.
- **Le compte rendu d'import nomme le rôle et la tâche d'une ligne rejetée** (#768, points 1 et 2).
  Une ligne de main-d'œuvre importée qui laisserait sa tâche sans heure travaillée
  (`TASK_WITHOUT_WORKING_HOURS`, `ImportRejection`) nomme ses rôles par `resource_roles`, chacun
  par son identifiant, son code et son libellé, actifs ou désactivés, comme les refus des coûts
  depuis EP-14/L42r : le compte rendu se lit sans relire les rôles, qu'un utilisateur sans
  `resource_settings.read` ne lit pas. Elle nomme sa tâche par sa lignée et son libellé (`tasks`,
  `ProblemImportedTask` : `lineage_id`, `label`), comme `ImportDifference` nomme les objets d'un
  import : un import sur un projet sans révision en cours n'a encore aucun nœud de la révision qu'il
  écrira (WF-INTF-0090). Le refus d'une saisie, d'un collage et d'une fusion garde
  `resource_role_ids` et les tâches par leur nœud : l'auteur y consulte son projet et en lit les
  rôles d'après ses lignes. Aucune situation du témoin ne laisse une tâche sans heure travaillée
  par une ligne importée, les calendriers de l'univers se recoupant tous du lundi au jeudi : l'exemple
  est une variante déclarée, écrite à la main comme `structure_merge_report_refused`,
  `import_estimate_task_without_hours` (`getImport`, dernier des 200). Il reprend l'import du devis
  de `import_analysed` et rejette sa quatrième ligne de l'onglet « Hors lot » : `resource_roles` y
  nomme le monteur câbleur et le technicien de mise en service, `tasks` le « Câblage des armoires »
  par sa lignée. Un test d'outil le recoupe avec les rôles et le cœur du témoin, un test du back le
  fait lire en entier par le modèle engendré.
- **La ligne de provision déplacée, au compte rendu** (#789, WF-RIS-0010). Quand l'import d'un
  planning ou la fusion d'un différentiel retire la tâche qui porte une ligne de provision, la ligne
  passe sur la tâche parente — ou, pour une tâche de premier niveau, sur la première tâche de
  premier niveau restante —, « et la confirmation ou le compte rendu le signale ». Le compte rendu le
  dit par un écart `updated` de la ligne (`target` à `estimate_line`) sur `parent`, le mécanisme
  d'une ligne déplacée sous une autre tâche (#1194), à côté du retrait de la tâche : aucun schéma
  nouveau, et la ligne se lit comme toute ligne du compte rendu, par sa lignée et son libellé.
  Écarté : un écart propre à la provision, ou le nom de la tâche qui la reçoit, que le compte rendu
  ne donne pour aucune ligne déplacée. Exemples écrits à la main, variantes déclarées : la ligne de
  provision du « Risque de reprise du câblage » portée par le « Montage des armoires sur site », non
  démarré, au lieu du « Câblage des armoires », démarré, dont le retrait serait conservé
  (`kept`) — `structure_merge_report_provision_moved`, dernier des 200 de
  `getStructureMergeReport`, la fusion d'un « Avenant 4 » qui retire le montage, et
  `import_planning_provision_moved`, dernier des 200 de `getImport`, un planning qui ne le porte
  plus ; l'un et l'autre présentent la tâche retirée, ses deux lignes, sa liaison à la « Mise en
  service », et la ligne de provision passée sur « Installation sur site ».
- **Le délai de paiement d'une ligne de main-d'œuvre** (#785, WF-DEV-0020). WF-DEV-0020 le veut
  « saisissable sur toute ligne autre qu'une ligne de provision », nul par défaut pour la
  main-d'œuvre, et le Vérif de WF-IND-0100 le saisit « sur toutes les lignes, main-d'œuvre
  comprise ». `editable_fields` d'une ligne de main-d'œuvre nomme `estimate_line.payment_delay_days`,
  après sa charge et avant son sous-projet (`wftools.mockstructure.line_fields`) ; la description
  d'`EstimateLineUpdate` ne le dit plus suivi. `EstimateLineWrite` et `EstimateLineUpdate`
  portaient déjà le champ : seuls la ligne et ses exemples changent, régénérés. La cellule du devis
  suit `editable_fields`, sans code propre (US-0640). Exemple engendré,
  `estimate_line_payment_delay_amendment`, dernier des 200 d'`updateEstimateLine` : sur l'avenant 2,
  le délai du « Raccordement des borniers » saisi à 30 jours, aucun montant ni aucune date ne
  changeant ; le témoin des parcours (`test_the_marks_the_journeys_read`) nomme le champ sur la
  ligne 28.
- **Les refus de la correspondance des coûts réels** (#1514). Deux exemples écrits à la main,
  derniers des 422 de `setActualCostMapping` : `actual_cost_mapping_labels_refused`, trois
  intitulés refusés à la fois, dans l'ordre du corps — un intitulé vide d'une colonne lue
  (`VALUE_REQUIRED`), une colonne conservée de 201 caractères (`VALUE_TOO_LONG`) et un doublon
  d'une colonne conservée (`DUPLICATE_COLUMN_LABEL`, `duplicate_of` à `/kept_columns/0`) — ; et
  `actual_cost_mapping_kept_columns_too_many`, cinquante et une colonnes conservées, refusées au
  pointeur de la liste (`/kept_columns`), qu'aucune ligne du formulaire ne présente seule. Les
  tests de la page qui les lisent sont du front (#1514).

**Corrélations** 1559 et 1560 ; **import** `…0a19`.

### La fusion : cycle, horizon, et fusion sans révision en cours (US-0640/L3, #1331)

Les constats #788, part « fusion », et #790 des relectures d'EP-14/L42s, relus sur le contrat
qu'EP-15 a laissé ; la conception d'EP-16 tranche le second (« Une fusion sans révision en cours »).
Aucune opération nouvelle.

- **La fusion échoue sur une boucle de liaisons et sur l'horizon** (#788 ; WF-REV-0050 cite
  WF-PLA-0030 et WF-PLA-0150 parmi les motifs de refus d'une fusion ; WF-PLA-0150 : « le refus nomme
  la tâche en cause »). Sur le modèle de `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, la tâche de fond de
  `mergeCostStructure` finit en échec sans rien fusionner, `problem.code` à `LINK_CYCLE` ou
  `PROJECT_HORIZON_EXCEEDED`, et le compte rendu préalable porte le même motif, avec les mêmes
  paramètres (`ReportRefusal`). Chaque tâche est nommée par son nœud de la structure principale et
  son libellé, le nœud nul pour une tâche que le différentiel ajoute, comme `params.task` le disait
  déjà d'un différentiel. `params.cycle` nomme la boucle que porterait la structure fusionnée, de sa
  première tâche dans l'ordre du plan à celle qui la précède, chacune précédant la suivante ; la plus
  courte quand il y en a plusieurs, puis celle dont la première tâche vient d'abord. Ce n'est pas la
  règle d'une saisie, qui part de la tâche saisie : une fusion n'a pas de tâche saisie, et le
  différentiel peut fermer la boucle par une liaison comme par un déplacement. `params.task` nomme la
  tâche de la structure fusionnée qui finit la dernière, hors récapitulatives, qui tirent leurs dates
  de leurs subordonnées (WF-PLA-0040) — sans quoi la récapitulative de premier niveau, première dans
  le plan, serait toujours nommée —, puis la première dans l'ordre du plan. Une boucle laisse les
  dates sans calcul : l'horizon n'est alors pas jugé, et les deux motifs ne vont jamais ensemble.
  `cycle` reste un paramètre ouvert de `ProblemParams`, comme pour `setPredecessors` et `moveNodes` :
  la conception ne l'a pas compté parmi les paramètres typés. Exemples écrits à la main, variantes
  déclarées : `structure_merge_report_link_cycle` et `task_merge_link_cycle` (tâche de fond 952), un
  différentiel qui donne la « Mise en service » pour prédécesseur à la « Réception usine », la boucle
  étant celle de `predecessors_cycle_refused` ; `structure_merge_report_horizon_exceeded` et
  `task_merge_horizon_exceeded` (tâche de fond 953), la « Mise en service » allongée de deux cents
  mois de travail, comme `predecessors_horizon_exceeded`.
- **Une fusion sans révision en cours** (#790, WF-REV-0050 : « Lorsque le projet ne comporte pas de
  révision en cours, elle en crée une au préalable » ; conception d'EP-16). Elle se demande sur le
  différentiel de la dernière révision marquée, par le même chemin et le même corps : la commande
  `merge_structure` de cette révision y est disponible, et `mergeCostStructure` crée la révision en
  cours par copie (WF-REV-0010), y fusionne la copie du différentiel et la marque, dans la même
  tâche de fond ; la révision marquée ne change pas. Écarté par la conception : exiger d'ouvrir
  d'abord une révision, contraire à WF-REV-0050. Ce que la conception laissait au lot :
  - *Le compte rendu le dit* par `StructureMergeReport.creates_current_revision`, un booléen exigé,
    faux pour un différentiel de la révision en cours. Il ne nomme pas la révision créée : elle
    n'existe pas encore, et elle prendra le nom de version que la confirmation porte
    (`StructureMerge.version_name`) ; sa source est la révision du chemin. Ses écarts et ses refus
    se jugent sur la structure principale de la révision marquée, que la copie reprend telle quelle,
    et ses compteurs sont ceux de ses structures, que le marquage a figés. Écartés : un objet
    décrivant la révision à créer, qui ne dirait rien de plus que le chemin et la confirmation ; une
    lecture à part, sur le projet.
  - *Les conditions de la commande.* Sur la dernière révision marquée d'un projet sans révision en
    cours, `merge_structure` nomme, dans cet ordre, `project_not_terminal` (avant US-0702/L3, #1657 ;
    un projet terminal ne liste plus la commande, et seul le 409 de l'appel direct la nomme),
    `no_background_task_running` pendant un traitement qui crée la révision en cours — un import
    appliqué, une survenance, une autre fusion de cette révision —, `unmerged_amendment_exists`,
    puis `may_create_revision` à qui n'a pas `revisions.write`, comme les autres commandes qui
    créent la révision en cours (imports, `edit_risks`, `declare_risk`, `declare_occurrence`).
    Partout ailleurs sur une révision marquée — une plus ancienne, ou celle-ci dès qu'une révision
    est en cours —, elle ne manque que de `revision_draft`, comme avant. La fusion qui court crée une
    révision invisible jusqu'à sa fin : le projet nomme `no_background_task_running` aux commandes
    qui créeraient ou ouvriraient la révision en cours, comme pendant un import ou une survenance.
  - *Le 409.* Le compte rendu et la fusion d'une structure que la commande ne dit pas fusionnable
    sont refusés par `STATE_FORBIDS_OPERATION`, `params.missing_condition` la première condition
    qui manque — `revision_draft` quand une révision a été ouverte, ou une révision plus récente
    marquée, depuis la lecture du compte rendu. C'est le refus d'`applyRateUpdate` sur une révision
    marquée (`rate_update_revision_marked`) : une écriture de la révision, comme son marquage, non
    une saisie de grille, qu'une révision marquée refuse par 403. Le contrôle et le dépôt de la
    tâche se font sous le verrou du projet, qui tient sa révision en cours. Les compteurs d'une
    révision marquée ne bougent pas : c'est ce 409, et non le 412, qui dit qu'un compte rendu lu sans
    révision en cours ne vaut plus. *Depuis US-0702/L1 (#1610, décision de l'auteur du 2026-10-28), une
    saisie de grille sur une révision marquée est refusée par ce même 409, et non par 403.*
  - *L'échec après la création.* La tâche est une seule opération, comme la fusion que WF-REV-0050
    dit appliquée « en une seule opération », et comme le marquage (§ « Le marquage d'une
    révision ») : en échec, sur un cycle, l'horizon ou tout autre motif, elle ne laisse ni révision en
    cours ni fusion, et le projet reste sans révision en cours. Écarté : garder la révision créée,
    qu'aucun utilisateur n'a demandée et qu'il faudrait abandonner.
  - *Les taux.* La révision créée est chiffrée aux taux conservés, projetés ; pour la chiffrer aux
    taux de la nouvelle année, on la crée d'abord (`createRevision`), et la fusion se demande sur
    elle (WF-REV-0060, qui le dit mot pour mot).

  - *Sans `revisions.write`.* Sur la dernière révision marquée d'un projet sans révision en cours,
    la fusion refusée à qui ne peut pas créer la révision l'est par ce même 409,
    `params.missing_condition` à `may_create_revision`, non par un 403 : c'est la commande qui dit la
    condition, comme pour les imports et `declare_risk`.

  Exemples : `revision_marked_merge_offered` (`getRevision`), la référence le 1er février 2026,
  juste après son marquage par la fusion de l'avenant 1 et avant que le réexamen du 2 février
  n'ouvre la révision 102 — un instant antérieur de la même chronologie, non une variante — : la
  fusion de l'avenant 2, non fusionné, y est offerte, engendré depuis `revision_marked`, la commande
  seule changée (`wftools.mockamendment`) ; `merge_may_create_revision_refused`, engendré, le 409 de
  cette fusion demandée sans `revisions.write` ; et, écrits à la main,
  `structure_merge_report_without_current_revision`, son compte rendu, `creates_current_revision`
  vrai, les écarts de l'avenant que la révision 102 a repris avec lui, et
  `merge_revision_marked_refused`, le 409 de la même fusion demandée aujourd'hui sur la référence,
  la révision 102 étant en cours. `structure_merge_report`, engendré, et les trois comptes rendus
  écrits à la main portent `creates_current_revision` faux. Les tests d'outil sont dans
  `tools/tests/test_mockmerge.py`.

- **La fusion échoue sur une liaison entre une récapitulative et sa subordonnée** (#1582, décision de
  l'auteur du 2026-10-28, option 1 ; WF-PLA-0030 refuse ce lien, WF-REV-0050 cite ses refus parmi
  ceux d'une fusion). À l'image de `LINK_CYCLE` : la tâche de fond de `mergeCostStructure` finit en
  échec sans rien fusionner, `problem.code` à `LINK_FORBIDDEN`, et le compte rendu préalable porte le
  même motif, avec les mêmes paramètres. `params.link` nomme les deux tâches, la récapitulative
  puis sa subordonnée, chacune par son nœud de la structure principale et son libellé, le nœud nul
  pour une tâche que le différentiel ajoute. Une saisie ou un déplacement refusés par ce code restent
  sans paramètre. Écarté : le traiter comme une boucle, `LINK_CYCLE` (option 2), qui ne dirait pas
  la raison du refus. Écarté aussi : `tasks`, propriété typée de `ProblemParams`, dont chaque élément
  exige un projet et un nœud non nul (`ProblemTask`) quand la fusion nomme une tâche ajoutée par un
  nœud nul et ne porte pas de projet ; `link` reste ouvert, comme `cycle` et `task`. Exemples écrits
  à la main, variantes déclarées : `structure_merge_report_link_forbidden` et
  `task_merge_link_forbidden` (tâche de fond 954), un différentiel qui donne à l'« Installation sur
  site » le « Montage des armoires sur site », l'une de ses subordonnées, pour prédécesseur.

**Corrélation** 1561 et 1562 ; **tâches de fond** 952, 953 et 954.

### Les constats de contrat des lots d'EP-15 (US-0640/L6, #1457)

Les constats de contrat que les lots d'EP-15 ont relevés en livrant, tranchés au recadrage d'EP-16
(« Ce que le cadrage décide », #1445), et ceux que l'auteur a confiés à ce lot le 2026-10-28 : #870,
#1401, #1531, #1566, #1573 (sa part back) et #1577. Aucune opération nouvelle. Les écrans qui les
adoptent sont d'US-0660/L3 et L4.

- **« Appliquer la mise à jour des taux » est une commande de la révision** (#1351, WF-REV-0060 : « la
  présentation reste proposée depuis la révision en cours tant qu'elle n'est pas marquée »).
  `RevisionCommand.apply_rate_update`, rangée après la fusion et avant le marquage — les écritures
  de la révision qui ne la figent pas, puis celles qui la figent —, et une condition nouvelle,
  `rate_update_available`, rangée après `unmerged_amendment_exists` : elle manque quand la
  proposition (`getRateUpdateProposal`) ne présente aucune catégorie. Ce que le lot a fixé :
  - *La permission* est `revisions.write`, la gestion des révisions (FBS-4.1, que WF-REV-0060 nomme
    d'abord) : celle de `createRevision`, qui applique déjà la mise à jour à la création
    (`RevisionCreate.apply_rate_update`), et la mise à jour est une écriture de la révision, comme son
    marquage (« Les refus du cycle », plus haut). Écartée : `estimate.write`, que la lecture de
    US-0490/L2 supposait (`edit_estimate`) : le devis de la structure principale ne se saisit plus
    dès En cours, quand la mise à jour s'y accepte encore — le Vérif l'accepte sur une révision créée
    par un import de reste à engager. Un chiffreur (`revision_estimator`) ne la voit donc pas.
  - *L'ordre des conditions.* Sur la révision en cours, la condition propre d'abord,
    `rate_update_available`, puis `no_background_task_running` pendant un marquage, l'application
    d'un import, une survenance ou une fusion, comme `generate_skeleton` ; sur une révision marquée,
    `revision_draft` seule, la proposition n'y étant pas jugée. Le 409 d'`applyRateUpdate` nomme la
    première qui manque, dans cet ordre.
  - *Les exemples.* Chaque révision des exemples porte la commande, indisponible : la 102, la 101 à
    sa version 2 et la 103 par `rate_update_available` (`rate_update_none` ; la 101 a accepté
    chaque catégorie présentée ; la 103 n'a pas de révision précédente), la 102 pendant un marquage
    ou un import aussi par `no_background_task_running`, les révisions marquées par
    `revision_draft`. Engendré par `wftools.mockcycle`, `revision_rate_update_offered`
    (`getRevision`) : la 101 le 12 janvier 2026 à 10 h, à sa création par l'identification des
    risques, à sa version 1, la mise à jour offerte, disponible — `rate_update_applied` à sa
    version, la commande seule changée —, un instant antérieur de la même chronologie. Écrit à la
    main, `rate_update_not_available`, le 409 d'une mise à jour envoyée pour la 102.
- **Le registre des risques se pagine** (#1367, WF-IHM-0060). `listRisks` reçoit `Limit` et
  `Offset`, et sa réponse `meta` (`PaginationMeta`), exigé, comme `listActualCosts` ; `totals` reste
  calculé sur tous les risques que les filtres et la recherche retiennent, non sur la page lue —
  `ProvisionTotals` le dit. `risks`, engendré, et `risks_empty`, écrit à la main, portent `meta`
  (cinquante lignes par page, trois risques, aucun).
- **`createNode` refuse une date manuelle un jour chômé** (#1345, WF-PLA-0020 : « une date
  saisie »). Comme `updateTaskFacet` : 422 `VALIDATION_FAILED`, `fields` sur `/task/start/date` ou
  `/task/finish/date` par `NON_WORKING_DAY`, `params.date` et `next_working_day`, rien n'étant créé.
  Le calendrier qui juge est celui de la tâche créée : sans ligne de main-d'œuvre, le calendrier par
  défaut (WF-PLA-0010). `TaskFacetWrite` garde `WorkInstant` — la création porte ses heures — :
  seule la date d'un jour chômé est refusée. Exemple engendré par `wftools.mocknonworking`,
  `node_create_non_working_day` : une tâche « Réception provisoire sur site » créée en mode manuel
  sous l'« Installation sur site », son début envoyé le samedi 19 décembre 2026, le lundi 21 nommé.
- **Un collage ancré sur un nœud retiré est refusé entier** (#1361 ; écarté par la décision :
  reporter l'ancre au nœud suivant, qui écrirait ailleurs que là où l'utilisateur a cliqué). La forme,
  fixée par le lot : un code nouveau, `PASTE_TARGET_REMOVED`, une seule `PasteRejection`, sur la
  première ligne du bloc (`row` à `0`) et la colonne visée, et `PastePlan.accepted` à `0`, aucune
  autre ligne n'étant jugée ; confirmé, le plan n'écrit rien et le compteur de la structure n'avance
  pas. Écarté : `FIELD_NOT_ACCEPTED` sur chaque cellule de la première ligne, que la règle générale
  du collage aurait donné, et qui ne dit pas la cause (défaut n° 10 du guide, comme pour
  `SUBPROJECT_HAS_ACTUAL_COSTS`). `PastePreview`, `previewPaste` et `applyPaste` le disent. Exemple
  engendré par `wftools.mockamendmentwrites`, `paste_plan_amendment_target_removed` (collage 996) :
  le bloc qui saute la ligne retirée, collé sur cette ligne même, l'« Assistance aux essais de
  câblage » de l'avenant 2.
- **#1368 est écarté sans changement de contrat** (WF-RIS-0020, décision de l'auteur du
  2026-10-28). `ProjectCommand.declare_risk` n'exige pas de révision en cours : le projet la porte
  précisément quand il n'en a pas, et la déclaration en crée une au préalable (« lorsque le projet
  n'en comporte pas, la saisie en crée une au préalable »).
- **Les exemples de l'encart et de l'analyse échouée** (#1379). Engendré par `wftools.mockcycle`,
  `revisions_project_created` (`listRevisions`) : la seule révision 103 du projet créé aujourd'hui,
  telle que la lit `revision_without_tasks`. Écrit à la main, `task_import_analysis_failed`
  (`getBackgroundTask`, tâche de fond 934, celle d'`import_analysing`) : l'analyse échouée à 8 h 41,
  variante contrefactuelle, sur `INTERNAL_ERROR` — le format et la version d'un fichier se jugent à
  l'ouverture de l'import (`openImport`, 422), si bien qu'une analyse n'échoue que sur une
  défaillance.
- **Deux risques dérivés d'exemples dans les tests du front** (#1384, point 1). Engendrés par
  `wftools.mockhistory`, variantes contrefactuelles déclarées, chacune un risque du registre tel
  qu'il le lit, une valeur changée : `risk_dismissed_category_deactivated`, « Indisponibilité de
  l'automaticien », écarté, la catégorie de sa provision désactivée depuis
  (`provision_cost_category_is_active` faux) ; `risk_uncited`, « Risque de reprise du câblage »,
  qu'aucune révision marquée ne citerait, sa suppression disponible. Le point 2, le libellé de
  `ReferenceForm`, est à EP-17 (#1568), et le point 3, `task_occurrence_succeeded`, l'y suit
  (décision de l'auteur du 2026-10-28).
- **Le choix d'états de la liste de l'accueil** (#1401, décision de l'auteur du 2026-10-28 : une
  préférence). Aucun schéma ne change : la clé de `grids` est `projects`, celle sous laquelle la
  grille de la liste des projets de l'accueil garde déjà ses réglages (`PROJECT_LIST_GRID.key`) — un
  nom propre à cette liste, que le portefeuille ne partage pas (`portfolio_projects`) —, et
  `filters.states` garde les états choisis comme l'adresse de l'accueil les écrit, sous le nom du
  paramètre, `states`, leurs valeurs séparées par des virgules, comme tout filtre d'une grille
  (`GridPreferences.filters`, US-0380). Écartés : une clé nouvelle, `home_projects` par exemple, qui
  séparerait des autres réglages de la même grille le filtre que l'écran garde avec eux ; une
  propriété typée de `GridPreferences`, qui changerait le schéma. Le défaut — Chiffrage et En cours
  — reste celui de l'écran (US-0660/L4), qu'un compte qui n'a rien écrit prend ; « Tous les états »
  s'écrit comme l'adresse l'écrira, ce qu'US-0660/L4 fixe ; le serveur garde le filtre tel qu'il est
  écrit. `getPortfolioProjects` et `PortfolioStates` ne changent pas. Exemple écrit à la main,
  `preferences_project_states` (`updateMyPreferences`) : Chiffrage, En cours et Terminé choisis
  (`pricing,in_progress,completed`).
- **Le nom d'un contributeur anonymisé** (#870, décision de l'auteur du 2026-10-28).
  `Contributor.display_name` et `ContributorSuggestion.display_name` sont nullables, comme
  `ActorRef.display_name` : nul pour un compte anonymisé, que le front nomme par le libellé neutre de
  son catalogue (`useAccountNaming`), le service ne rendant ni son nom (WF-ADM-0060) ni une phrase
  (WF-ARC-0110) ; une proposition n'est jamais anonymisée, un compte anonymisé étant désactivé.
  `listContributors` range un compte anonymisé après les noms dans l'ordre croissant — sans tri,
  après les autres comptes de sa qualité —, comme `listUsers` range un auteur anonymisé, et la
  recherche sur le nom ne le retient pas. Exemple engendré par `wftools.mocklists`,
  `contributors_anonymized` : la liste du témoin une fois le compte d'Alix Moreau anonymisé
  (`users_anonymized`), son nom nul, en dernier, le compteur de la liste inchangé. Le service est
  d'EP-04.
- **La création d'un projet et l'abandon d'une révision au journal d'audit** (#1577, WF-SEC-0030).
  `AuditAction` gagne `project_create`, avant `revision_mark`, et `revision_abandon`, après lui,
  dans l'ordre de WF-SEC-0030 ; `AuditObjectKind` ne change pas. Leurs `params` sont vides, et
  `AuditParams` dit pourquoi : la création d'un projet le nomme déjà par son code et son libellé du
  moment (`AuditEvent.project`, `AuditObject.label`) ; l'abandon nomme la révision par son
  identifiant et par son projet, une révision en cours n'ayant pas de nom de version
  (`AuditObject.label` nul). Écarté : répéter le code et le libellé du projet dans `params`, ce que
  l'inscription dit deux fois déjà. Le journal du témoin (`wftools.mockaudit`) inscrit la création
  de PRJ-001 par Camille Martin le 6 octobre 2025 à 9 h, à l'instant de son audit, après la création
  du compte de Noé Vidal au même instant ; et l'abandon de sa révision 102, aujourd'hui à 14 h 05,
  la suite d'une écriture de `project_without_current_revision`, lue seule dans
  `audit_events_revision_abandoned`. Les inscriptions suivantes en prennent un numéro de plus :
  `audit_events_anonymized_object` et `audit_events_anonymized_actor`, écrits à la main, suivent
  (inscriptions 41 et 42). Livré par US-0640/L6b (#1594), avec le renommage de K-04
  (`structure_merge`, ci-dessus). Le back reste en retard sur le contrat jusqu'à EP-04, sans
  migration dans EP-16 (décision de l'auteur du 2026-10-28, option b, sur #1457) : il ne sert ni
  `project_create`, ni `revision_abandon`, ni `structure_merge`, et sert encore `amendment_merge` ;
  `test_audit_journal.py` nomme ces écarts et échoue dès que le back en comble un. EP-04 servira
  aussi le libellé nul d'une révision en cours abandonnée, qui n'a pas encore de nom de version : la
  contrainte `OBJECT_LABELED` de la migration 0011 n'admet un libellé nul que pour une sauvegarde ou
  un compte, et refuse une révision.
- **Le délai de paiement, écart d'un différentiel** (#1566, WF-DEV-0020, WF-IND-0100).
  `NodeChange` gagne `payment_delay_days`, après les montants et avant le parent : une ligne dont
  seul le délai change est `modified`, quand aucun montant ne bouge, et ses tâches porteuses le sont
  par leur contenu. L'écart d'un import le disait déjà : `ImportDifference.fields` nomme les colonnes
  de `NodeColumn`, dont `payment_delay_days`. `estimate_line_payment_delay_amendment`, régénéré,
  présente le « Raccordement des borniers » modifié par son délai, et ses ancêtres par leur contenu.
- **Les refus de l'annulation et du rétablissement** (#1531). Écrits à la main, variantes
  contrefactuelles : `undo_later_change` et `redo_later_change`, `UNDO_CONFLICT` sans paramètre, la
  charge du « Raccordement des borniers » modifiée depuis par Lucas Petit ;
  `undo_restored_subproject_deleted`, `STATE_FORBIDS_OPERATION` à `restored_subproject_exists`,
  une ligne rendue à un sous-projet supprimé depuis. Les descriptions des deux 409 nomment
  `UNDO_CONFLICT`. *Depuis US-0702/L1 (#1610, E-07), `UNDO_CONFLICT` nomme l'objet en conflit
  (`params.conflicting_object_id`, `conflicting_object_label`), et un historique vide a sa
  condition ; « sans paramètre » ne vaut plus.*
- **#1573, la part back** : la ligne trop longue de l'entrée « Les comptes rendus et les paramètres
  des refus » est coupée, et le test des paramètres typés valides prend un paramètre `(nom, valeur)`
  au lieu de la clé factice `tasks_imported`.

**Corrélations** 1563 à 1567 ; **collage** 996.

### Les montants inflation comprise (US-0701/L1, #1601, L-01)

La spécification a tranché, les 10 et 22 octobre 2026, que les montants budgété et réestimé d'une
ligne sont « exprimés inflation comprise, à l'année de consommation de la ligne (WF-DEV-0030,
WF-DEV-0040) : c'est à ce titre qu'ils entrent au budget de référence, au reste à engager, à la
valeur planifiée et à la valeur acquise » ; « le montant aux taux de l'année de référence, avant
inflation, est une valeur de lecture » (WF-DEV-0020, WF-DEV-0050, glossaire). L'auteur l'a suivie
au recadrage du 2026-10-28 (L-01 de la revue du contrat avant le gel), et réécrit EP-02/L7 (#235),
EP-02/L16 et EP-02/L30 (#352), plus haut. Écarté : garder #235 et #352 et faire corriger la
spécification, quand le glossaire, WF-RIS-0050 et le budget de référence en dépendent.

- **Trois montants par ligne, et par tâche et aux totaux.** `base_amount`, aux taux de l'année de
  référence, avant inflation ; `budgeted_amount` et `reestimated_amount`, inflation comprise.
  `inflated_amount` disparaît d'`EstimateLineFacet`, de `TaskFacet`, de `NodeTotals`, de
  `NodeColumn` et de `ComputedValueField` ; `inflation` reste dans `ComputedDependency`, pour la
  projection du budgété et du réestimé. La grille de devis présente `base_amount` et
  `reestimated_amount` (WF-DEV-0050), celle de reste à engager le budgété et le réestimé.
- **Le budgété est projeté sur l'année où la référence consommait la ligne** (WF-RAE-0010 : « le
  montant budgété de la ligne reporté de l'année de consommation que lui donnait la référence ») :
  fixé par elle, il ne suit pas les dates de la révision courante. Le réestimé suit l'année de
  consommation courante. Sur un projet sans révision de référence, les deux sont confondus
  (WF-DEV-0050). `NodeInflation` porte donc les deux, au lieu du seul montant corrigé.
- **Une ligne de provision n'est pas projetée** (WF-DEV-0030, WF-PRJ-0040) : son montant est celui
  que son risque calcule, le devis propre du risque portant déjà sa propre projection. La règle est
  dite sur la facette de la ligne et sur `ComputedDependency.inflation`.
- **Les indicateurs.** `EstimateIndicators.total`, ses ventilations et ses écarts sont des montants
  réestimés, inflation comprise — `total` vaut `NodeTotals.reestimated_amount` — ; le reste à
  engager et la marge de `RemainingIndicators` aussi, à l'année de consommation courante (le doute
  de la revue sur « l'année des montants du reste à engager », lié à M-08, est levé ainsi).
- **Le témoin.** `mockdating.price` projette le budgété et le réestimé ; `mockcore` lit l'année de
  consommation que la référence 101, revue précédente de la révision 102, donnait à chaque ligne.
  Toutes les révisions du témoin sont projetées depuis 2026, l'offre de 2025 comprise : une
  simplification déclarée, qui garde à la référence le budget que l'offre a fixé aux lignes que
  l'avenant 1 ne désigne pas (#467). L'auteur l'a tranchée le 2026-10-29 (#1628) : la décision
  d'appliquer est prise (l'offre et la référence recevront la même année de référence), sa mise
  en œuvre est en question — WF-REV-0060 oblige à redater l'offre en 2026, ce qui retire au témoin
  son récit de mise à jour des taux (commentaire de #1628) — et la part détachée US-0701/L2b
  (#1641) la porte ; le raccourci reste déclaré tant que #1641 n'est pas livré. Le Vérif de
  WF-REV-0080 (`test_mockcomparison.py`, aujourd'hui 2 768 lignes de main-d'œuvre réestimées
  seules, aux taux de 2026) et les récits du témoin en dépendent. Le devis du témoin vaut
  68 923 691,06, son budget de référence 68 241 568,05 ; la valeur planifiée et la valeur acquise
  ne bougent pas, les tâches terminées étant de 2026. Le reste à engager, d'abord inchangé,
  change avec M-08 (« Le réestimé d'une ligne non réestimée », plus bas) : 67 470 132,98 dans
  l'état final, et le poste de commande, qui ne devait plus être dépassé que de la facture des
  écrans, 2 400,00, l'est de 64 699,97.
  `tools/tests/test_mockinflation.py` tient le Vérif de WF-DEV-0050 (4,04 % à 2 %, deux ans après
  l'année de référence) et celui de la provision de WF-DEV-0030.
- **Les préférences d'affichage** : une colonne gardée sous `inflated_amount` ne s'applique plus, et
  revient à son réglage par défaut, comme au changement de clé d'EP-02/L16 ; `me_grid_settings`
  connaît désormais `reestimated_amount`.

### Les deux écarts de la comparaison (US-0701/L1, #1601, E-02)

WF-REV-0080 présente « les écarts de montants budgétés et de montants réestimés, par nature de coût
et par sous-projet », et son Vérif les distingue : « une ligne existante dont le différentiel ne
modifie que le montant budgété ne présente aucun écart de montant réestimé ». Le contrat n'en
portait qu'un, `delta`, d'une troisième grandeur, le montant à l'année de référence.
`RevisionComparison.amount_deltas[]` porte désormais `budgeted_delta` et `reestimated_delta`,
exigés, inflation comprise (« Les montants inflation comprise », ci-dessus), dans le sens d'EP-02/L35
(la révision comparée moins la révision de base) ; `delta` disparaît. Écarté : le garder sous le nom
de `base_delta`, l'écart du montant avant inflation — aucune grille ne le présente, et l'écran de la
comparaison lit les deux écarts que la spécification nomme. Une clé dont les deux écarts sont nuls
reste omise. `mockcomparisons` les calcule sur le budgété et le réestimé des lignes retenues ;
`comparison*.json` et `volume/comparison_volume.json` sont régénérés, et
`test_mockcomparison.py` tient le Vérif sur une révision dont un différentiel ne change que le
budget d'une ligne.

### Le réestimé d'une ligne non réestimée (US-0701/L1, #1601, M-08)

WF-RAE-0010, réécrite le 2026-10-22, compte au reste à engager une tâche non démarrée pour « le
montant réestimé de ses lignes, qui, faute de réestimation, se calcule depuis les grandeurs de la
référence, aux taux conservés par la révision courante (WF-REV-0060) et sur son année de
consommation courante » ; « à taux horaires inchangés, c'est le montant budgété de la ligne reporté
de l'année de consommation que lui donnait la référence sur son année de consommation courante ».
Le contrat ne disait rien de la valeur de `reestimated_amount` d'une ligne jamais réestimée, et deux
décisions d'EP-02 disaient l'ancienne règle, « le budgété projeté d'une tâche non démarrée »
(EP-02/L24, EP-02/L27, EP-14/L45a, réécrites plus haut). La proposition de la revue s'applique
(décision de l'auteur du 2026-10-28, « la règle des autres majeurs ») :

- **`EstimateLineFacet.reestimated_amount`** est celui de la dernière réestimation (WF-RAE-0040) ;
  pour une ligne jamais réestimée, il est calculé depuis ses grandeurs courantes — celles de la
  référence, ou de l'avenant dont la fusion les a changées (WF-REV-0050) — aux taux conservés par la
  révision, sur son année de consommation courante. Le reste à engager compte ce montant pour toute
  ligne d'une tâche non terminée (`RemainingIndicators`).
- **Pas de booléen `is_reestimated`.** La revue le proposait « à trancher », pour que la grille
  distingue une ligne réestimée et que l'avenant sache quelles lignes recalculer. La spécification
  ne le rend pas nécessaire au contrat : WF-RAE-0010 compte le même montant réestimé dans les deux
  cas, seule sa source change, et c'est le serveur qui la connaît ; WF-RAE-0040 présente à chaque
  ligne ses grandeurs et son montant réestimé, précédents et courants, sans distinguer une ligne
  réestimée d'une autre ; et la fusion d'un avenant (WF-REV-0050), qui ne donne ses grandeurs qu'à
  la ligne « que personne n'a réestimée », est une écriture du serveur, dont le compte rendu
  présente les lignes modifiées sans cet état. Ajouter le champ plus tard ne romprait aucun client.
- **L'année des montants** : le reste à engager est inflation comprise, à l'année de consommation
  courante de chaque ligne, comme le réestimé qu'il somme (L-01, ci-dessus) — le doute de la revue
  est levé sans second total.
- **Le témoin.** `mockindicators.remaining_of` compte le réestimé de toute ligne d'une tâche non
  terminée, la provision d'un risque identifié pour son montant, et rien pour une tâche terminée.
  Les lignes de main-d'œuvre tirées des tâches non démarrées, que l'avenant 1 ne désigne pas,
  gardent le budget de l'offre, aux taux de 2025, et comptent désormais leurs heures aux taux de
  2026 que la révision conserve : le reste à engager du témoin passe de 67 293 028,72 à
  67 470 132,98, sa marge sur le budget de référence à -641 535,13, et le poste de commande dépasse
  son budget de 64 699,97. `test_mockinflation.py` tient le Vérif de WF-RAE-0010 sur elles.

### Le compte rendu préalable de la survenance d'un risque (US-0680/L1, #1453)

US-0520 veut que « Déclarer survenu » présente, avant confirmation, ce que la survenance ferait de la
structure principale, dans les marques `+`, `-`, `M` ; le contrat n'avait que la mise en file,
`declareRiskOccurrence`, sans compteur lu, et aucun exemple ne décrivait le devis propre d'un risque
identifié du témoin (#1383). Décision du recadrage d'EP-16 (2026-10-25, #1445), option (a) :
l'écart est calculé par le serveur, comme pour un différentiel (C-361). Écartée : (b), le front
compose le compte rendu depuis `listNodes` et `getRisk`, qui ne montre ni la tâche porteuse modifiée
ni le cas du jalon.

- **La lecture.** `getRiskOccurrenceReport`
  (`GET /projects/{project_id}/risks/{risk_id}/occurrence`), une lecture qui n'écrit rien, sur le
  modèle de `getStructureMergeReport` : sans 403, comme toute lecture du projet. Elle rend
  `RiskOccurrenceReport`.
- **Le compte rendu** (`RiskOccurrenceReport`) : `main_structure_lock_version` et
  `risk_lock_version`, les compteurs lus ; `creates_current_revision` (ci-dessous) ;
  `differences`, des `ImportDifference`, dans cet ordre — les tâches et les lignes du devis propre
  ajoutées dans l'ordre de son plan, la tâche porteuse modifiée, la ligne de provision retirée — ;
  `provision_amount`, le montant de la ligne retirée du reste à engager ; `refusals`, des
  `ReportRefusal`, dont `TASK_WITHOUT_WORKING_HOURS`. Les deux tableaux sont toujours rendus. Choix
  de forme du lot, là où la conception se taisait :
  - un ajout n'a pas de lignée, et les liaisons internes du devis propre ne sont pas des écarts à
    part : elles viennent avec ses tâches, comme celles des tâches qu'un différentiel ajoute
    (`structure_merge_report`) ;
  - la tâche porteuse, devenue la récapitulative des tâches placées sous elle, est un `updated`
    dont `fields` nomme ce qui change de ses dates et de sa durée (`duration`, `start`, `finish`,
    dans l'ordre de `NodeColumn`) : elle couvre désormais les dates de ses subordonnées
    (WF-PLA-0040), qui gardent celles du devis propre (WF-RIS-0060). Les tâches que ce changement
    redate ailleurs ne sont pas des écarts, comme au compte rendu d'une fusion ;
  - un jalon porteur reste un jalon sans sous-tâche (Vérif de WF-RIS-0060) : il n'est pas modifié,
    et les tâches sont ajoutées après lui.
- **Le refus.** Un risque qui n'est pas identifié — survenu ou écarté — : 409
  `STATE_FORBIDS_OPERATION`, `params.missing_condition` à `risk_identified`, la condition que nomme
  déjà la commande `declare_occurrence` du risque, au compte rendu comme à la survenance.
- **La confirmation.** `RiskOccurrence` exige les deux compteurs lus, comme `StructureMerge`
  (WF-IHM-0110) : la structure principale ou le risque changés depuis, `declareRiskOccurrence` est
  refusée par 412 `STALE_LOCK_VERSION`, `params.expected_lock_version` le compteur courant du
  risque, l'objet que le chemin nomme, même quand seule la structure principale a changé (#296).
  Le 412 ne dit donc pas lequel des deux compteurs a avancé : le client ne rejoue pas avec
  `expected_lock_version`, il relit le compte rendu et le remontre.
- **Le devis propre gardé par le compteur du risque** (revue locale d'US-0680/L1, question à
  l'auteur, décision du 2026-10-28, option (b), #1453). Le compte rendu liste les tâches et les
  lignes du devis propre, mais une saisie dans sa structure ne faisait avancer ni le compteur de
  la structure principale ni celui du risque : lu par A, modifié par B, le devis aurait été
  fusionné sans que personne l'ait vu. Toute saisie dans le devis propre du risque — une cellule,
  un collage, un déplacement, une création, une suppression, ce qui fait avancer
  `CostStructure.lock_version` de sa structure — fait aussi avancer `Risk.lock_version`
  (`Risk.lock_version`, `CostStructure.lock_version`, `RiskOccurrence`, `RiskOccurrenceReport`,
  `declareRiskOccurrence`) : la gravité du risque est le total de son devis propre (WF-RIS-0010),
  le risque change donc quand son devis change, comme il change à la suppression du sous-projet
  qu'il désignait (#732). La conception reste à deux compteurs, et la phrase « n'applique jamais un
  compte rendu que personne n'a vu » reste vraie. Écartées : (a), un troisième compteur
  `own_structure_lock_version`, qui s'écarte des « deux compteurs » de la conception ; (c), dire
  que le devis propre n'est pas gardé. Tenu par le service d'EP-08 ; ce lot l'écrit au contrat.
- **Sans révision en cours** (même revue, décision du 2026-10-28, option (a), #1453).
  WF-RIS-0060 : sans révision en cours, la survenance en crée une au préalable, par copie de la
  dernière révision marquée (WF-REV-0010). Le compte rendu se juge alors comme celui de la fusion
  d'un différentiel de la dernière révision marquée (#790) : ses écarts et ses motifs de refus sur
  la structure principale de la révision marquée, que la copie reprend telle quelle, et
  `main_structure_lock_version` est le compteur de celle-ci, que le marquage a figé — la révision
  aussi que lit le risque, `revision_id` absent (`getRisk`). Écartée : (b), laisser la question
  ouverte pour EP-08.
- **`creates_current_revision`** (tour 2 de la même revue, question Q3, décision du 2026-10-29,
  option (a), #1453). Les deux compteurs ne suffisaient pas à refuser une révision en cours née
  depuis la lecture : si la copie qui la crée reprend le compteur de la structure marquée, rien
  n'avance ; et « dès qu'une révision en cours existe », pris à la lettre, refusait aussi le cas
  normal, un compte rendu lu avec la révision en cours. Pour la fusion, le chemin nomme la
  révision marquée et le 409 `revision_draft` se décide sur lui ; ici le chemin nomme le risque, et
  c'est le corps qui porte l'information. Le compte rendu rend `creates_current_revision`, comme
  `StructureMergeReport` (#790), vrai quand il est jugé sur la dernière révision marquée ;
  `RiskOccurrence` l'exige et le renvoie tel que lu ; vrai alors qu'une révision en cours est née
  depuis la lecture, ou faux alors qu'il n'y en a plus, la confirmation est refusée par 412
  `STALE_LOCK_VERSION`, comme un compteur périmé (`getRiskOccurrenceReport`,
  `declareRiskOccurrence`, `RiskOccurrence`, `RiskOccurrenceReport`). Écartées : (b), une règle
  de compteur — la révision en cours créée ouvre sa structure principale à un compteur supérieur
  à celui de la marquée —, qui touche toute copie au-delà de la survenance ; (c), faire avancer le
  compteur de chaque risque du projet à l'ouverture d'une révision, qui périme toutes les vues de
  risques. Tenu par le service d'EP-08.
- **Le témoin.** Le devis propre du risque 751, « Risque de reprise du câblage », structure 204,
  est décrit dans `wftools.mockwitness` (`REWORK_ESTIMATE`, nœuds 531 à 534, lignées 631 à 634) :
  le « Diagnostic des défauts de câblage », en mode manuel du 1er au 7 juillet 2026, et la
  « Reprise du câblage des armoires » à sa suite, sous-traitées, 250 000,00 et 1 000 000,00 —
  1 250 000,00, la gravité du risque. Sa provision est portée par le « Câblage des armoires »,
  qui n'est pas un jalon.
- **Les exemples**, engendrés par `wftools.mockriskwrites` : `nodes_risk_estimate`, dernier
  exemple de `listNodes`, le devis propre lu, que le faux back n'aiguille pas sur la structure 204
  (les parcours qui y jouent lisent le premier exemple) ; `risk_occurrence_report`, les deux
  tâches et leurs lignes ajoutées sous le « Câblage des armoires », celui-ci modifié par sa durée,
  son début et sa fin, la provision de 500 000,00 retirée, les compteurs 1 et 4,
  `creates_current_revision` faux, le témoin ayant une révision en cours ;
  `risk_occurrence_sent`, la confirmation, exemple du corps de `declareRiskOccurrence`, qui
  renvoie ces trois valeurs ; `risk_occurrence_not_identified`, le 409, sur « Indisponibilité de
  l'automaticien », écarté le 2 février, cité par les deux opérations ;
  `risk_occurrence_report_stale`, le 412, un compte rendu lu avant le réexamen du 2 mars.
  `tools/tests/test_mockriskwrites.py` les tient contre le registre, les structures et la
  structure principale.

**Corrélation** 1591 et 1592.

### Les indicateurs exigés (US-0701/L5, #1605, G-02)

Des indicateurs que la spécification exige étaient facultatifs dans les schémas : une réponse
conforme pouvait omettre l'avancement financier, les écarts, les écarts des projections, la
capacité d'un rôle ou la zone d'un mois, et le client engendré les voyait facultatifs. Les rendre
exigés après le gel resserrerait le contrat du côté du producteur ; la proposition de la revue
s'applique (décision de l'auteur du 2026-10-28, « la règle des autres majeurs »), sur le précédent
de `under_load_threshold` (US-0240/L5, plus haut). Sont exigés : dans `ProjectIndicators`,
`financial_progress`, `budget_consumption`, `physical_progress`, `cost_variance` et
`schedule_variance` (WF-IND-0040, WF-IND-0060 à WF-IND-0080) ; dans `Projections`, les trois écarts
au budget, `variance_at_observed_rate` restant nul tant que sa projection ne se calcule pas
(WF-IND-0050) ; dans `CalculationContext`, `revision_status` et `is_stored`, que toutes les
descriptions prennent pour pivot ; la capacité d'un rôle dans `WorkloadPlan.roles[]` et
`PortfolioWorkload.roles[]` (WF-DEV-0070, WF-PTF-0060), et la zone d'un mois du plan agrégé ; dans
`PortfolioPerformance`, `reference_budget`, `cost_variance` et `schedule_variance` (WF-PTF-0070).
Tous les exemples les portaient déjà : aucun ne change.

**La part d'une répartition (`share`) fut laissée facultative par US-0701/L5**, faute d'une forme
pour la part d'un total nul. Elle est exigée depuis la décision du 2026-10-29 (« La part d'un total
nul », EP-14/L55 : #1633, G-02, option A), dans `AmountByKey` et `ComputableAmountByKey`.

**Les mineurs de ces fichiers** (règle du recadrage : un mineur d'un fichier qu'un lot modifie est
corrigé par lui). `actual_cost` compte les pièces datées « antérieure ou égale » à la date de
calcul (G-09, WF-IND-0010) ; la valeur planifiée et le plan de charge s'étalent « au prorata des
heures travaillées », et non linéairement, la charge restante sur la part de la durée postérieure à
la date de calcul (G-10, WF-DEV-0080, WF-DEV-0070) ; `PortfolioProjectRow.delta_to_reference`
remplace le schéma qui n'existe pas (G-12) ; `IndexValue.value` est à quatre décimales (la part
`indicators.yaml` de G-08 ; l'arrondi du portefeuille est à US-0701/L6), et `IndexValue.zone` dit
les bornes des zones (la part `indicators.yaml` de M-13, WF-REF-0170) et qu'elle se classe à la
lecture sur les seuils courants, pour un indice conservé aussi, comme `IndexHistory.thresholds`
(M-14, WF-REF-0130). L-24 était déjà appliqué (`EstimateIndicators.delta_to_reference`).

### Les courbes au pas du mois, conservées au marquage (US-0701/L5, #1605, G-01, M-02, M-03)

Les passes de cohérence des 9 et 10 octobre 2026 ont écrit dans la spécification trois règles que
le contrat ne suivait pas ; la proposition de la revue s'applique à chacune (décision de l'auteur du
2026-10-28, « la règle des autres majeurs »), et les décisions antérieures qu'elles contredisent
sont réécrites : #247 et #365 (EP-02/L18, EP-02/L35), EP-02/L24 deux fois.

- **Le pas du mois** (G-01). « Les courbes se calculent et se présentent au pas du mois, chaque
  point portant le cumul à la fin du mois ; la révision en cours et les révisions marquées sont
  présentées au même pas » (WF-IND-0100, WF-IND-0110, WF-DAT-0040). `CurveSeries` le dit : la
  première valeur à la fin du mois qui précède le premier montant, nulle ; la date de calcul, un
  point de plus sur les séries qui s'y arrêtent ou en partent (`actual_cost`, `earned_value`,
  `project_manager_projection`) ; une marche d'avenant, deux points à sa date, avant et après, comme
  le voulait EP-02/L24. Une tâche terminée fait sa marche dans la valeur acquise au point du mois de
  sa terminaison. La courbe en S du portefeuille, déjà au pas du mois, raconte désormais la même
  histoire que celle du projet (WF-PTF-0100). Écarté : garder le point par jour pour la maquette,
  contraire aux trois exigences, et un changement de nature des points après le gel.
- **Les courbes d'une révision marquée sont conservées** (M-02). WF-IND-0010 : « Pour une révision
  marquée, ce sont les lignes connues à son marquage, telles qu'elles étaient alors […]. Les courbes
  d'une révision marquée sont conservées avec ses indicateurs ». `IndicatorsRevision`, `getCostCurve`
  et `getEarnedValueCurves` perdent les phrases « connues aujourd'hui », et `is_stored` est vrai
  pour ce que le marquage a conservé, indicateurs et courbes ; faux pour la révision en cours et
  pour le calcul au jour courant d'un projet sans révision en cours. Le point ouvert de #247, des
  courbes recalculées qui pouvaient s'écarter des indicateurs, est clos par la spécification.
- **Les indicateurs du jour d'un projet sans révision en cours** (M-03). WF-IND-0010 : « ses
  indicateurs au jour courant se calculent sur sa dernière révision marquée, avec le coût réel au
  jour courant » ; WF-IND-0130 et WF-IND-0090 en tirent le dernier point, WF-PTF-0010 la
  contribution au portefeuille (« Un projet dont la revue vient d'être marquée et qui n'a pas de
  révision en cours contribue par cette revue »). `IndicatorsRevision`, `AsOf`, `getProjectIndicators`,
  `getIndexHistory`, `IndexHistory`, `IndexHistoryPoint`, l'en-tête de `portfolio.yaml` et
  `PortfolioScope` le disent : `is_stored` faux, `context.revision_id` nommant la révision marquée,
  le dernier point de l'évolution `version_name` nul. Le risque avait déjà sa règle (`RiskRevision`,
  US-0230/L2).
- **Le témoin.** `mockcurves` lit chaque courbe aux fins de mois (`days_of`, `up_to`) : 46 points
  pour le budget de référence de `cost_curve` au lieu de 756, du 31 janvier 2026 au 31 août 2029 ;
  le coût réel et la valeur acquise s'arrêtent au 3 juin, d'où part la projection. Une lecture est
  conservée quand elle est celle de sa révision à l'instant de son marquage
  (`mockindicators.Reading.is_stored`), qui donne `is_stored` aux courbes comme aux indicateurs.
  Exemple nouveau, `project_indicators_without_current_revision`, une variante contrefactuelle
  déclarée : la révision 102 abandonnée ce matin, ses saisies défaites — terminaisons comprises —,
  les indicateurs du jour se calculent sur la référence 101 avec le coût réel du jour, 1 412 970,20,
  sans valeur acquise, d'où un indice de coût nul et une projection au rythme constaté non
  calculable ; ceux que la référence a conservés (`project_indicators_marked`) ne changent pas.
  `tools/tests/test_mockcurves.py` tient le pas du mois, la marche de la valeur acquise au point du
  mois et les deux lectures d'un projet sans révision en cours (WF-IND-0100, WF-IND-0110,
  WF-IND-0010). Aucun exemple ne lit une courbe d'une révision marquée : le témoin ne modélise pas
  la date d'import d'une pièce, que la conservation demanderait.

### Les décaissements, la revue précédente, le diagramme temps/temps et l'avancement d'une récapitulative (US-0701/L5, #1605, M-06, M-09, M-10, M-11)

Quatre règles de calcul que les passes de cohérence des 9 et 10 octobre 2026 ont précisées ; la
proposition de la revue s'applique à chacune (décision de l'auteur du 2026-10-28), et les décisions
antérieures qu'elles contredisent sont réécrites, plus haut : la révision du 2026-10-04 et deux
passages d'EP-02/L24 (M-06), #466 (M-09), EP-02/L23 et EP-02/L24 (M-10), #245 (M-11).

- **Les décaissements** (M-06, WF-IND-0100). « Le coût réel n'est pas décalé » ; « le reste à
  engager de chaque ligne est étalé, au prorata des heures travaillées, sur la part de la durée de
  sa tâche postérieure à la date de calcul, et porté entier à la date de calcul lorsque la fin de la
  tâche est dépassée » ; une ligne de provision « reste à la date de la tâche qui la porte ».
  `getCostCurve`, `CurveSeries.payment_delays` et `cash_out_by_month` le disent : « date de pièce
  décalée » et « étalé sur les dates de la révision courante » disparaissent. La projection part
  du coût réel à la date de calcul, comme le veut le Vérif ; ce qu'une tâche en retard porte
  encore compte au point de la fin du mois de la date de calcul. `mockcurves.ahead` porte ce
  reste à la date de calcul, et non plus au premier jour ouvré qui la suit, la provision d'une tâche
  passée aussi : au pas du mois, les exemples ne changent pas.
- **La revue précédente** (M-09, WF-RAE-0020). L'écart au reste à engager précédent ne compte que
  la révision marquée précédente « lorsque celle-ci a été marquée à l'état En cours » : nul quand
  aucune ne l'a été avant celle qui est lue, une offre marquée en chiffrage n'étant pas une revue.
  `mockindicators.remaining_indicators` lit l'état du projet au marquage de la révision donnée
  (`state_at`). Le témoin compare la révision courante à la référence 101, marquée En cours :
  aucun exemple ne change. `EstimateLineFacet.previous_*`, « nulles avant la première revue »,
  n'est pas touché : `revisions.yaml` est aux lots US-0701/L2 et L3, et WF-RAE-0040 ne dit pas que
  le reste à engager précédent de la grille soit celui d'une révision marquée En cours.
- **Le diagramme temps/temps** (M-10, WF-IND-0090). « Les révisions marquées avant l'état En cours
  ne donnent aucun point » ; la courbe d'un jalon s'arrête par un point à sa terminaison, en
  abscisse comme en ordonnée ; le dernier point est celui du jour courant, par la révision en cours
  ou, à défaut, la dernière révision marquée. `MilestoneTracking`, ses points et `marked_at` —
  l'abscisse, qui est aussi la terminaison à minuit ou l'instant du calcul — le disent.
  `mockindicators.milestone_tracking` écarte les révisions marquées avant l'état En cours :
  `milestone_tracking` perd le point de l'offre du 15 décembre 2025, la réception des études n'a
  plus que la référence et sa terminaison.
- **L'avancement d'une récapitulative** (M-11, WF-IND-0060, WF-IND-0030, WF-IND-0020). Le rapport
  des montants budgétés acquis dans son sous-arbre, ses lignes propres comprises, au total de ce
  sous-arbre, hors lignes de provision de part et d'autre (`TaskFacet.physical_progress`, la seule
  description de `revisions.yaml` que ce lot touche) ; la valeur acquise hors lignes de provision
  (`ProjectIndicators.earned_value`) ; le budget d'un sous-projet sur ses lignes de la référence,
  hors provisions, son reste à engager sur celles de la révision courante
  (`SubprojectBalance.budget`, `remaining`). `mockcore` compte désormais les lignes propres de la
  récapitulative et écarte les provisions. Sur le témoin, rien ne change : la récapitulative
  « Poste de commande » (551) vaut 0, aucune de ses tâches n'étant terminée, et 552 n'est pas une
  récapitulative. `tools/tests/test_mockcurves.py` tient le Vérif de WF-IND-0060 (50 %) sur une
  structure déclarée, une provision sur la deuxième tâche, et celui de WF-RAE-0020, de WF-IND-0090
  et de WF-IND-0100 sur le témoin.

### Le portefeuille : horizon, projets terminés, couverture, offres (US-0701/L6, #1606)

La spécification du 9 octobre 2026 (constats C-122, C-199 et C-205 de sa revue) a dit ce qu'une
offre et un projet terminé apportent au portefeuille ; la proposition de la revue du contrat
s'applique à chaque constat, et la décision de l'auteur du 2026-10-28 (« Le portefeuille ») tranche
les deux points qu'elle laissait ouverts. Réécrits, plus haut : le choix déclaré d'EP-02/L26 (M-07),
sa courbe sur six mois de part et d'autre (G-04), son évolution de 2025-T3 à 2026-T2 (G-03) et sa
couverture « des projets en cours » (G-06) ; complétées, la période par défaut d'US-0240/L3 et le
refus d'une période d'EP-02/L42e (G-05).

- **L'évolution trimestrielle** (G-03, WF-PTF-0070). Un point par trimestre civil que la période
  touche, du plus ancien au plus récent, chaque indice lu au dernier jour du trimestre, et à la date
  de calcul pour celui qui la contient ; `scope.from` et `scope.to` rendent la période. Sur la
  période par défaut, du 4 juin 2025 au 3 juin 2026 : cinq trimestres, de 2025-T2 à 2026-T2, les
  deux premiers non calculables. `mockportfolio.quarters` les tire de la période.
- **L'horizon** (G-04, WF-PTF-0060, WF-PTF-0100). `horizon_months` compte les mois à partir de
  celui de la date de calcul, six par défaut ; la courbe en S les fait précéder des douze mois
  passés, quel que soit l'horizon. Décision de l'auteur ; écartés : le futur seul partout, un
  paramètre de plus. `portfolio_cost_curve` court de juin 2025 à novembre 2026, dix-huit mois ;
  `portfolio_cost_curve_credit`, lue au 31 décembre 2025 à un mois d'horizon, de décembre 2024 à
  décembre 2025, ses dix premiers mois nuls.
- **La période des projets terminés** (G-05, WF-PTF-0010). `getPortfolioCostStructure` et
  `getPortfolioCostCurve` prennent `PortfolioFrom`, `PortfolioTo` et `PortfolioPeriodRefused`, la
  période par défaut comprise, qu'elles rendent dans `scope` ; elle ne borne pas les mois de la
  courbe. `getPortfolioWorkload` et `getPortfolioPilotHealth` disent qu'un état autre que ceux qui
  y contribuent — en cours, et en chiffrage pour la charge — est sans effet, et ne prennent pas de
  période. Décision de l'auteur ; écarté : la période sur les quatre vues.
- **La couverture agrégée** (G-06, WF-PTF-0090). La réserve et la couverture portent sur les projets
  en cours et terminés du périmètre, un projet en chiffrage n'ayant pas de référence. Aucun projet
  de la liste n'est terminé : l'exemple ne change pas, et un test déclare un projet terminé.
- **La contribution d'une offre** (M-07, WF-PTF-0020, WF-PTF-0080, WF-PTF-0090, WF-PTF-0100).
  Son devis courant pondéré par sa probabilité de gain, hors lignes de provision au budget de
  référence (courbe et structure des coûts), provisions comprises au reste à engager et à la
  projection ; ses risques identifiés et leurs provisions sans pondération dans la vue des risques.
  `mockportfoliotime.offer_course` porte le Vérif de WF-PTF-0100 (100 hors provisions, 50 de
  provision, 40 % : 40 au budget, 60 à la projection) ; chaque offre engendrée tire la part de son
  devis que portent ses lignes de provision, de 2 à 8 %. L'exemple de la structure des coûts et
  celui des risques ne retiennent pas d'offre ; leurs générateurs ne la modélisent pas.
- **Les mineurs de ces fichiers.** Le budget de référence agrégé ne porte plus de nature
  « Provision » (G-15, WF-IND-0020) ; les états hors du périmètre et l'état à la date de calcul
  (`PortfolioStates`, G-11, WF-CYC-0130) — un projet créé, perdu ou abandonné est sans effet, la
  forme qu'a retenue la décision sur G-05, l'autre étant un refus ; la zone d'un mois du plan agrégé
  et son 422 (G-13) ; la performance sur les seuls projets en cours, `scope.states` les états
  demandés (G-14) ; le dénominateur du taux de transformation, une offre abandonnée ne comptant pas
  (M-15) ; la projection au rythme constaté agrégée (M-16) ; les indices du portefeuille à quatre
  décimales (la part du portefeuille de G-08, qu'US-0701/L5 lui laissait). Le dernier trimestre de
  l'évolution égale ainsi les deux indices du jour : le témoin y compte sa valeur planifiée du jour,
  que sa courbe, au pas du mois, ne porte pas.
- **Les tests.** `tools/tests/test_mockportfoliotime.py` tient les Vérif de WF-PTF-0100 (l'offre) et
  de WF-PTF-0090 (le projet terminé), l'horizon, les trimestres et l'effet nul d'un autre état ;
  `test_mockcurves.py` tient celui de WF-IND-0030 sur une structure déclarée (#1634).

### Les révisions et les structures : date de début de planning, fusion, historique annulable (US-0701/L2, #1602)

Les constats E-01, E-03, E-04, E-06, E-08, E-09, E-10, E-11, L-05, L-14 et L-16 de la revue du
contrat avant le gel. La spécification les a tranchés dans ses passes des 9 et 10 octobre 2026 ;
les décisions de l'auteur du 2026-10-28 (« La date de début de planning », « L'historique
annulable », « Les risques ») tranchent ce qu'elle laissait ouvert, et la proposition de la revue
s'applique au reste (« la règle des autres majeurs »). Réécrits, plus haut : le plan de charge
d'EP-02/L7 (L-16), la fusion de l'avenant 1 d'EP-02/L27 (#467, L-14) et l'annulation d'EP-02
(« Collage et annulation », E-06).

- **La date de début de planning** (E-01, WF-PLA-0020 et WF-REV-0100 du 2026-10-09, C-142 de leur
  revue). `CostStructure.planning_start_on`, exigé ; `updateCostStructure`,
  `PATCH …/structures/{structure_id}`, écrit la date et le libellé avec le compteur
  (`StructureUpdate`), sous `edit_planning` de la structure, et rend `NodesWritten`, sans nœud
  écrit : les tâches automatiques sans prédécesseur et leurs successeurs redatés. Décision de
  l'auteur ; écarté : la date seule, un second PATCH viendrait pour le libellé. Deux points que ni
  la spécification ni la revue ne disent, choisis au plus près d'elles : la date se juge sur le
  calendrier par défaut, la structure n'ayant pas de calendrier propre et une tâche sans ligne de
  main-d'œuvre étant sur lui (WF-PLA-0010) — refus `NON_WORKING_DAY` sur `/planning_start_on`,
  comme une date saisie ; et un différentiel, copie de la structure principale à sa création, en
  prend la date, sans quoi toutes ses tâches automatiques glisseraient au jour de sa création et
  son compte rendu de fusion les dirait toutes redatées. La modification s'inscrit à l'historique
  annulable (`UndoneKind.structure_update`) : WF-IHM-0110 ne l'en excepte pas. Le témoin :
  `mockwitness.PLANNING_START`, le 2 mars 2026, date la structure principale et les différentiels
  (`structures`, `structures_amendments`, `amendment_created`) ; un devis propre de risque porte
  le jour où son risque a été identifié, le 12 janvier 2026, sans effet, sa première tâche étant
  en mode manuel ; la structure du projet créé aujourd'hui, le 3 juin 2026. L'exemple
  `structure_planning_start_advanced` (`volume/`) est une variante contrefactuelle déclarée, lue
  le 20 février 2026, avant qu'aucune tâche ne démarre par ses dates : la date avancée d'une
  semaine, au 23 février, redate 958 tâches (959 avant US-0701/L4, qui passe en mode manuel la
  « Relance du fournisseur » fusionnée par la survenance) — aujourd'hui, avancer la date d'une
  structure dont les tâches ont démarré changerait leur état, que le générateur lit des dates. `mockdating` et
  `mockcore` prennent la date de début de planning en paramètre ;
  `tools/tests/test_mockrevisions.py` tient le Vérif de WF-PLA-0020 sur l'exemple, et
  `structure_start_non_working_day` (`mocknonworking`) montre le refus. La lecture de la date par
  l'import MS Project et son changement au compte rendu (I-03, K-05) sont d'US-0701/L7 (#1607).
- **Le taux d'inflation, la probabilité de gain et la révision source** (E-03, L-05 ; WF-REV-0090,
  WF-REV-0070, WF-IHM-0020 du 2026-10-10). `Revision.inflation_rate` et `win_probability`, exigés,
  en lecture seule, comme `reference_year` l'a été pour la même raison (« Ce que la révision de la
  spécification demande », EP-02/L29) : ceux du marquage sur une révision marquée, ceux du projet
  sur la révision en cours. `RevisionSnapshot` est réduit à `employed_reference`, sans double.
  `source_revision_id` et `source_version_name`, exigés et nuls pour la première révision d'un
  projet, conservés une fois la révision marquée. Écarté : les porter aussi dans
  `CalculationContext`, que la revue proposait « si les indicateurs se lisent sans relire la
  révision » — le contexte ne porte pas non plus le nom de version de la révision lue, et tout écran
  de projet lit déjà la révision. `snapshot` est rendu par `getRevision` pour une révision marquée,
  omis ailleurs ; `revision_marked` et `revision_offer` portent l'instantané de la référence et de
  l'offre, et sont désormais engendrés (`mocksnapshot`), depuis `revisions` et les lignes de
  chacune ; `revision_marked_merge_offered` le reprend. Le témoin n'a jamais changé son taux
  d'inflation, 3 %, ni sa probabilité de gain, 100 % : chaque révision les conserve.
  Ce témoin ne prouve donc pas la conservation : comme la valeur conservée à chaque marquage et la
  valeur courante du projet sont égales partout, `test_mockrevisions.py` ne distingue pas « conservé
  au marquage » de « suit le projet » (WF-REV-0070, WF-REV-0090). Une révision au taux ou à la
  probabilité différents obligerait à réécrire les récits chiffrés du témoin, hors de ce lot.
  Aujourd'hui, aucun test n'éprouve la conservation : ni le faux back, dont le témoin a des valeurs
  égales partout, ni le back, car EP-16 n'écrit pas le service de révision. Le service de
  l'EPIC EP-04 (WF-REV-0070-A, WF-REV-0090-A), qui réalise les révisions, l'éprouvera sur des
  données qui changent.
- **Les images des taux conservés** (E-11, WF-REV-0030). `EmployedReference.hourly_rates` lit
  `HourlyRateImage` — catégorie, année, montant —, sans l'audit ni le compteur du taux du
  référentiel, qui bougent après le marquage. Les trois autres images gardent les leurs, celles
  de l'objet tel qu'il était au marquage (EP-02/L42a, « Les listes du référentiel par pages »).
- **La description à la fusion, et les grandeurs qu'elle donne** (E-04, L-14 ; WF-REV-0020,
  WF-REV-0050 du 2026-10-10). `StructureMerge.description`, facultative, comme au marquage. La
  fusion donne aux lignes désignées les grandeurs de référence du différentiel, et aussi leurs
  grandeurs courantes quand la tâche n'est pas démarrée et que personne n'a réestimé la ligne ; les
  deux descriptions qui disaient l'ancienne règle (`mergeCostStructure`, `StructureMerge`) la
  suivent. Le compte rendu ne distingue pas les deux cas d'un écart `updated` : l'état réestimé
  d'une ligne reste au serveur (« Le réestimé d'une ligne non réestimée », plus haut, M-08).
- **Les compteurs du compte rendu sans révision en cours** (E-10). Ceux des structures 211 et 213
  de la référence, 3 et 1, que `structures_amendments` liste ; l'exemple, écrit à la main, portait
  ceux de la révision courante. `test_mockrevisions.py` les tient l'un à l'autre.
- **`StructureCreate.kind` réduit à `amendment`** (E-09 ; WF-REV-0100, WF-RIS-0030), `risk_id`
  retiré, résumé « Ouvrir un différentiel » : le devis propre d'un risque naît et disparaît avec
  lui (`createRisk`). Décision de l'auteur ; écarté : une règle pour `risk_id`, deux chemins pour
  le même objet.
- **L'historique annulable** (E-06, E-08, L-18 ; WF-IHM-0110 du 2026-10-10). Tenu par le serveur,
  décision de l'auteur : une pile par révision et par utilisateur, le temps de sa session (le
  jeton `bearer`), finie au marquage et à l'abandon de la révision, d'au moins cinquante niveaux ;
  la liste des actions hors annulation reçoit l'abandon et la réintégration d'une ligne de coût
  (WF-CRE-0030, C-363). Écarté : le front qui rejoue l'inverse de chaque saisie — `undo` et `redo`
  retirés, et chaque écriture devant rendre l'état antérieur. La spécification dit encore
  l'historique « tenu par le front » ; l'issue de spécification #1595 demande à l'auteur de la
  corriger. `UndoResult.written` rend `NodesWritten` — nul pour une saisie de risque —, pour que la
  grille garde le compteur de la structure, et `undone.kind` est une énumération (`UndoneKind`),
  celle de la revue et `structure_update`. La forme des refus de l'annulation (E-07) est
  d'US-0702.
- **Le plan de charge sur une révision marquée** (L-16, WF-DEV-0070 du 2026-10-10). Une révision
  marquée est une base dès qu'elle existe, en chiffrage comme en réalisation ; seule
  `reference_budget` est refusée sans révision de référence, et `current_remaining` sans révision
  en cours. Sur une révision marquée, la date de calcul est sa date de marquage, et le reste s'y
  répartit après elle, comme sur la révision en cours ; le plan est en heures, et `WorkloadBasis`
  le dit. `workload_marked_remaining` est calculé au 1er février 2026, son contexte le dit ; ses
  heures ne changent pas, aucune tâche n'ayant démarré au marquage. Écarté : un exemple sur un
  projet en chiffrage, que la revue suggérait — le témoin n'en porte pas avec une révision
  marquée, et la règle se lit sur le refus et la description.

### Les échanges : journal, rejets, compte rendu MS Project, date de la revue, format à l'ouverture (US-0701/L7, #1607)

Les constats I-01 à I-05 et I-07 à I-11 de la revue du contrat avant le gel, et leurs doublons
K-05, K-06, K-07 et L-19. La spécification les a tranchés dans ses passes des 9 et 10 octobre
2026 ; les décisions de l'auteur du 2026-10-28 (« La date de terminaison par import », « Le format
d'un import », « La date de début de planning ») tranchent ce qu'elle laissait ouvert, et la
proposition de la revue s'applique au reste (« la règle des autres majeurs »). Réécrits, plus haut :
le compte rendu d'EP-02/L35 (#383) et la tâche non démarrée de #486 (I-09), le journal d'EP-02/L25
(I-01), le téléchargement d'EP-02/L38 (I-07).

- **Le journal et le compte rendu comptent les inchangées et les rejetées** (I-01 ; WF-CRE-0050,
  WF-INTF-0140). `CostImport` porte `unchanged_count` et `rejected_count`, exigés, à la place
  d'`ignored_count` ; `period_from` et `period_to` deviennent exigés, nullables. `ImportReport`
  porte `unchanged_count`, exigé : les objets lus que l'import laisse tels quels, ni rejetés, ni
  ignorés, ni présentés ajoutés ou modifiés. Écarté : la mention que l'inchangé se déduit de
  `read_count`, que la revue offrait aussi — d'un planning, `differences` porte des liaisons et
  des lignes que le fichier ne compte pas parmi ses objets lus, et la soustraction ne tomberait
  pas juste. Le témoin ne rapporte aucune ligne à l'identique : la réextraction du 11 mai garde
  ses six lignes mises à jour, comme leur audit le dit (`mockcosts.counts`).
- **Le rejet d'une ligne de coût pour son élément d'OTP** (I-02 ; WF-CRE-0020). Deux codes,
  `WBS_ELEMENT_INVALID` et `WBS_ELEMENT_OUTSIDE_PROJECT`, `params.wbs_element` l'élément lu et,
  pour le second, `params.project_code` le code projet lu. L'exemple engendré
  `import_actual_costs_first` (`mockexchanges`) est l'extraction d'avril telle que son analyse la
  présenta le 4 mai, avant son application : trois lignes ajoutées, la ligne d'un autre projet que
  le journal compte rejetée, et les deux motifs de confirmation. Il est aussi le premier import de
  coûts réels que la revue demandait (I-20).
- **Le compte rendu d'un planning MS Project** (I-03, I-04, K-05 ; WF-INTF-0040 du 2026-10-09).
  La date de début du projet du fichier devient la date de début de planning de la structure, et
  le compte rendu la présente quand elle diffère : un écart `updated` de cible `cost_structure`,
  `fields` à `planning_start_on` (`ImportDifferenceField`), `lineage_id` nul, la structure étant
  celle de l'import, comme la revue le proposait sous I-03 ; la valeur ne voyage pas, comme pour
  tout autre écart. Écarté : le champ `planning_start_change` de K-05, une forme de plus pour un
  seul écart. Le nom du champ suit `CostStructure.planning_start_on`, et non le `planning_start`
  de la revue. `ImportSignal.code` s'ouvre à `SUMMARY_TASK_DERIVED`, le code qui refuse à la
  saisie des dates sur une récapitulative : une récapitulative manuelle du fichier importée en
  automatique, `column` à `scheduling_mode`, `params.start` et `params.finish` les dates du
  fichier, l'écart recalculé dans `date_mismatches`. L'exemple écrit à la main
  `import_planning_mismatch` porte l'un et l'autre : le projet du fichier commence le 23 février,
  et la récapitulative des « Études » (621) y est manuelle.
- **Les lignes de provision d'un devis et d'un reste à engager** (I-05, K-06 ; WF-INTF-0100 du
  2026-10-09, WF-INTF-0120). `ImportIgnoredKind` gagne `provision_lines`, les lignes du fichier
  qui portent la lignée d'une provision, ignorées et nommées ; `kept` s'étend à la provision
  qu'un devis ne porte plus, conservée ; un reste à engager laisse inchangées, sans les signaler,
  toutes les lignes absentes de son fichier, la sienne comprise. `import_remaining_analysed` signale
  la provision du risque 751, que son fichier portait.
- **L'export est stocké jusqu'à son premier téléchargement complet** (I-07, K-07, L-19 ;
  WF-DAT-0120 du 2026-10-09, WF-ARC-0040). `requestExport`, `ExportRequest` et
  `getBackgroundTaskResult` le disent ; un résultat supprimé est un 404, et `result_url` d'un
  export devient nul. Le 409 générique de `getBackgroundTaskResult` reste à US-0702 (A-05).
- **La lecture d'un import dit ce que son ouverture a reçu** (I-08 ; WF-INTF-0090, WF-CRE-0050).
  `Import.structure_id`, `revision_id`, `period_from` et `period_to`, exigés, nullables : la
  structure résolue, la principale quand la requête n'en nommait pas ; la révision en cours, nulle
  tant que l'import la créera ; une extraction de coûts réels n'a ni structure ni révision — ses
  lignes sont du projet —, mais sa période. Écarté : la structure principale pour une extraction,
  que la revue laissait entendre, une structure que l'import n'écrit pas.
- **La date de terminaison par import** (I-09 ; WF-INTF-0120, WF-INTF-0130 des 9 et 10 octobre
  2026). Décision de l'auteur : la date de la revue que porte le fichier, connue dès l'analyse ;
  `ExportRequest.review_date`, nullable, le jour de la demande par défaut, que l'export du reste à
  engager écrit en « Synthèse » ; la fusion garde le jour de son application. Écarté : le jour de
  l'application. L'issue de spécification #1596 (WF-PLA-0130) est à l'auteur.
- **Le format se contrôle à l'ouverture** (I-10 ; WF-INTF-0070, WF-ARC-0100). Décision de
  l'auteur : `openImport` lit l'en-tête — format, version, intitulés — avant de mettre l'analyse
  en file, et refuse par 422 ; l'analyse ne refuse plus de format. Écarté : le refus porté par
  l'échec de la tâche d'analyse. Les exemples ne changent pas : le seul échec d'analyse,
  `task_import_analysis_failed`, est une défaillance du service.
- **Le libellé ambigu et la valeur lue** (I-11 ; ANNEXE B, WF-INTF-0100). `AMBIGUOUS_TASK_LABEL`,
  `params.label` et `params.tasks`, les tâches par leur lignée et leur libellé
  (`ProblemImportedTask`) ; `UNKNOWN_TASK`, `UNKNOWN_RESOURCE_ROLE` et `UNKNOWN_SUBPROJECT`
  nomment la valeur lue, `params.value`, que `import_analysed` montre. Le témoin n'a pas deux
  tâches de même libellé : le libellé ambigu n'a pas d'exemple.
- **Les mineurs des fichiers touchés** (I-12 à I-16, I-19, I-20 en partie). `format_version` nul
  pour une extraction de coûts réels, décrit ; `format_version`, `requires_confirmation_reasons`,
  `ImportDifference.label`, `ActualCostLine.excluded_reason` et `passthrough` exigés ;
  `Import.status` décrit, `expires_at` nul tant que l'analyse court ; les champs de l'ouverture et
  leurs refus décrits ; `ExportKind` nommé ; les filtres de `listActualCosts` décrits ; un 404
  d'export (`export_revision_not_found`). I-18 : l'abandon (`abandonImport`) est déclaré
  idempotent — un import déjà abandonné ou expiré rend 204 sans effet, son état restant lu et son
  fichier supprimé (WF-ARC-0100). Pour un import appliqué ou en cours d'application, la
  spécification ne dit rien : le refus, qui demanderait une condition nouvelle de
  `CommandCondition`, reste à la forme des refus d'US-0702. Restent au gel : d'I-20, une liste
  `completed_tasks` non vide et le 409 d'une application refusée pour l'état.

### L'arbre commun : récapitulatives, liaisons, colonnes, lignes de devis, paramètres de filtre (US-0701/L3, #1603, F-01, F-02, F-06, F-07, F-08, F-09, F-10, F-13, F-14)

Les constats F-01, F-02, F-06 (ses paramètres), F-07 à F-10, F-13 et F-14 de la revue du contrat
avant le gel, et leurs doublons L-07, L-09, L-10, L-12, L-13 et F-15. La spécification les a
tranchés dans ses passes des 9 et 10 octobre 2026 (WF-PLA-0040, WF-PLA-0080, WF-PLA-0100 du
2026-10-09 ; WF-PLA-0020, WF-PLA-0130 du 2026-10-10) ; la proposition de la revue s'applique
(décision de l'auteur du 2026-10-28, « la règle des autres majeurs »), et la décision du
recadrage « Les filtres de colonnes » fixe le partage de F-06. Réécrits en partie, plus haut : « Les
gestes du Kanban » (EP-15/US-0540, F-13) et « Toute liste se filtre sur ce que son écran présente »
(EP-02, F-07).

- **La marge et la criticité d'une récapitulative** (F-01, L-10 ; WF-PLA-0100). `TaskFacet` exige
  `total_float`, nullable, et `is_critical` : une récapitulative porte la plus petite marge de
  celles de ses subordonnées qui en portent une, nulle quand aucune n'en porte, et elle est
  critique dès que l'une d'elles l'est ; une tâche en mode manuel n'a pas de marge et n'est jamais
  critique. Le client engendré ne distingue plus une récapitulative sans marge d'une valeur
  absente. `ComputedDependency.subordinates` le dit ; la dépendance de la marge d'une
  récapitulative n'a pas d'exemple propre. `mockdating.float_of` la calcule, et toutes les lectures
  et les `ancestors` des écritures sont régénérés : « Études » porte une marge nulle et est
  critique.
- **La liaison en conflit** (F-02, L-07 ; WF-PLA-0020, WF-PLA-0100). La forme de L-07 :
  `TaskFacet.link_conflicts` et `NodeSchedule.link_conflicts`, exigés, toujours rendus, vides sans
  conflit, des `LinkConflict` `{predecessor_node_id, successor_node_id, link_type}` — sur la tâche
  manuelle, les liaisons que ses prédécesseurs automatiques ne peuvent pas satisfaire ; sur le
  prédécesseur, celles qu'il ne satisfait pas. La spécification signale « la tâche manuelle et ce
  prédécesseur », et le signalement « nomme la liaison en cause » : les deux tâches lisent la
  liaison sur leur propre nœud, et `rescheduled` suit l'écriture qui crée ou lève le conflit.
  Écartée : la forme de F-02, `Predecessor.is_conflicting` et
  `NodeSchedule.conflicting_predecessor_node_ids` — elle ne marque la liaison que du côté du
  successeur, et le Gantt devrait parcourir les prédécesseurs de chaque successeur pour signaler
  le prédécesseur, que seule sa marge négative distinguerait, ce que WF-ARC-0020 interdit ; le
  type de la liaison, qui décide de ce qui est jugé, n'y serait pas. Le témoin n'a pas de tâche
  manuelle liée à un prédécesseur automatique : l'exemple engendré `task_dates_conflicting`
  (`mockgestures`) passe « Préparation 1.2.17 », tâche tirée autour du cœur, en mode manuel du 16
  juin au 8 juillet, avant que son prédécesseur, « Reprise 1.2.14 », puisse finir le 23 juin ;
  les deux nomment la liaison, le prédécesseur porte une marge de -6 jours, et la chaîne qui le
  précède devient critique.
- **Les filtres de colonne de `listNodes`** (F-06 ; WF-IHM-0060, WF-IHM-0130). Décision du
  recadrage : les paramètres entrent au contrat et au faux back, leur présentation dans les trois
  grilles va à EP-17. Chaque colonne des grilles de planning, de devis et de reste à engager, selon
  la convention du README : les bornes `<colonne>_min` et `<colonne>_max` de la durée, de
  l'avancement physique, de la marge, de la quantité, de la charge, du débours unitaire, du délai
  de paiement, de l'année de consommation, des trois montants et des quatre grandeurs
  précédentes ; les périodes `<colonne>_from` et `<colonne>_to` du début, de la fin, des dates de
  démarrage et de terminaison ; `scheduling_mode` en liste ; `is_milestone`, `finish_overdue`,
  `uses_inactive_object` ; `description`, un texte contenu, comme `search`. La liste de la revue
  est corrigée : `inflated_amount` a disparu (L-01, US-0701/L1) ; l'avancement physique et les
  grandeurs précédentes, colonnes que la revue omettait, y entrent. Deux points que ni la
  spécification ni la revue ne disent, choisis au plus près du contrat : la durée, portée dans
  l'unité de sa saisie, se borne en jours de travail, comme la marge, convertie par les
  constantes de l'installation (`DurationUnits`) ; les prédécesseurs, une liste de liaisons et
  non une valeur, ne se filtrent pas. Un filtre de la tâche retient la tâche avec ses lignes, un
  filtre de la ligne la ligne, la borne d'un montant portant sur la ligne ; les refus sont ceux du
  README. `compareRevisions` les reçoit aussi, les mêmes `$ref` et le même 422 : WF-IHM-0130 veut
  que toute table se filtre sur chacune de ses colonnes, sa grille est celle des structures, et sa
  description dit déjà partager les paramètres de `listNodes` (#1193). Les nœuds comparés
  (`Compared*`) portent toutes les colonnes ; un filtre y porte sur la grandeur que la comparaison
  affiche, celle de la révision comparée, jamais sur l'écart que `difference` dit, et sur la valeur
  de base pour un nœud retiré, comme le tri et la recherche (#1205). Exemples engendrés
  (`mocksort`) : `nodes_estimate_filtered`, le devis du lot « Poste de commande » borné de 1 000,00
  à 10 000,00 réestimés — le raccordement des borniers et les borniers, leurs tâches rendues pour
  la lisibilité de l'arbre — ; `nodes_bounds_inverted`, la borne haute du montant réestimé sous la
  basse, refusée sur `/query/reestimated_amount_max`, `params.minimum` la borne basse, sous le 422
  de `listNodes` et de `compareRevisions` avec `nodes_period_inverted`.
- **Les colonnes de la grille de planning** (F-07, L-12 ; WF-PLA-0080). `NodeColumn` reçoit
  `started_on` et `completed_on` après `is_critical`, à la place que WF-PLA-0080 leur donne, avant
  les prédécesseurs et le rattachement, qui reste dernier (EP-02/L30) ; ce sont des colonnes de
  lecture, qu'un collage refuse par `FIELD_NOT_ACCEPTED`. `progress` en sort : la spécification est
  claire, l'état est « signalé par une marque visuelle et non par une colonne » (Vérif : « une
  tâche terminée se distingue d'une tâche démarrée sans lire de colonne »), et seul le Kanban
  l'écrit. Écarté : le garder comme colonne non saisissable, que la grille ne présente pas. Le
  filtre `progress` reste, la grille de planning filtrant « sur les tâches démarrées ».
  `paste_too_wide` ne change pas — sa largeur est celle d'une ligne, de son libellé à la dernière
  colonne —, ni `known_columns` de `me_grid_settings`, qui ne connaît que la grille de devis.
- **Le libellé composé** (F-08 ; WF-DEV-0020). `EstimateLineWrite.label` est facultatif :
  absent, le serveur compose celui de la tâche porteuse et, s'il existe, celui du rôle ; envoyé,
  il est pris tel quel. La forme, que ni la spécification ni la revue ne donnent, suit celle des
  libellés du témoin qui joignent deux noms (« Provision — risque de reprise du câblage ») : les
  deux séparés par un tiret cadratin entre deux espaces, tronqués à 300 caractères. Exemple engendré
  `estimate_line_created_labelled` (`mockamendmentwrites`), une ligne de main-d'œuvre créée sous la
  mise en service de l'avenant 2, son rôle seul envoyé : « Mise en service — Technicien de mise en
  service ».
- **La catégorie d'une ligne de main-d'œuvre** (F-09 ; Vérif de WF-DEV-0020). Elle est celle du
  rôle, calculée : `estimate_line.cost_category_id` entre dans `ComputedField` et
  `ComputedValueField`, les lignes de main-d'œuvre la portent dans `computed_fields` et non plus
  dans `editable_fields`, et `ComputedDependency.resource_role` la nomme. `EstimateLineWrite`
  n'exige plus la catégorie quand le rôle est envoyé ; sans rôle, elle est exigée
  (`VALUE_REQUIRED`). Une catégorie envoyée qui n'est pas celle du rôle est refusée par
  `COMPUTED_VALUE`, à la création comme à la modification ; la sienne ne change rien. Écarté : le
  motif `FIELD_NOT_ACCEPTED` de la revue, qui dit un champ que le nœud ne porte pas, quand la
  catégorie est une valeur calculée pour lui, que WF-IHM-0030 refuse « en nommant ce dont elle
  dépend » — la proposition range elle-même la catégorie dans `computed_fields`. Exemples
  engendrés `estimate_line_category_mismatch` et `dependencies_labour_category`.
- **La ligne de provision ne se réestime pas** (F-10 ; WF-RIS-0010, WF-RAE-0010). Sa
  `remaining_entry` est indisponible, `missing_conditions` à `line_not_provision`, condition
  nouvelle de `CommandCondition`, après `task_not_completed` sous une tâche terminée ;
  `setLineRemaining` déclare son 409. Exemple engendré `remaining_provision_refused`
  (`mockriskwrites`).
- **Le jalon terminé est daté** (F-13, L-13 ; WF-PLA-0130 du 2026-10-10). La revue le laissait « à
  trancher » ; la spécification est sans exception : « une tâche terminée sans avoir été démarrée
  prend pour date de démarrage celle de sa terminaison ». Un jalon terminé depuis le Kanban porte
  `started_on` égal à `completed_on`, sans passer par l'état démarré ; rouvert, il perd l'une et
  l'autre. `TaskFacet.started_on`, `ProgressUpdate`, `RemainingUpdate.completed_on`, `KanbanCommand`
  et `setTaskProgress` le disent ; `milestone_completed`, `milestone_reopened` et toutes les
  lectures où la « Réception des études » est terminée sont régénérés. Écartée : la lecture « un
  jalon ne démarre jamais, `started_on` nul », que la passe du 10 octobre a retirée.
- **Le mode d'une récapitulative** (F-14, L-09, F-15 ; WF-PLA-0040 du 2026-10-09). Toujours
  automatique, calculé : `task.scheduling_mode` entre dans `ComputedField` et
  `ComputedValueField`, chaque récapitulative le nomme dans `computed_fields`, et sa saisie, même
  `automatic`, est refusée par `COMPUTED_VALUE` (`TaskFacetUpdate`, `updateTaskFacet`) ; une feuille
  manuelle qui reçoit une subordonnée devient une récapitulative automatique (`createNode`,
  `moveNodes`). La récapitulative qui perd sa dernière subordonnée — feuille automatique de la
  durée qu'elle calculait, jalon si cette durée est nulle et qu'elle n'est pas démarrée, feuille
  d'un jour si elle l'est — est dite dans `deleteNode`, `moveNodes` et `NodesWritten.ancestors` ;
  les refus de `deleteNode` (F-04) sont à US-0702. Exemple engendré `node_summary_emptied`
  (`mockgestures`), sous le 200 de `deleteNode` : la suppression de la tâche « Relevé des réglages
  existants », seule subordonnée de « Note de calcul des protections » que `node_created_child` a
  faite récapitulative, laisse celle-ci feuille automatique d'un jour, rendue telle qu'elle
  devient dans `ancestors` ; le témoin n'a pas de récapitulative de dix jours à une seule
  subordonnée, celle-ci en tient lieu (WF-PLA-0040).
- **Les mineurs des fichiers touchés.** F-12 l'était déjà par US-0701/L1 (`rescheduled` dit
  qu'une tâche rendue entière dans `ancestors` y paraît aussi). F-16 : `Lag.value` en `percent` est
  un nombre de pour cent, `50` pour la moitié, comme MS Project — sans exemple, aucun prédécesseur
  du témoin n'étant en pourcentage. F-18 : `NodeKinds` n'est pas un filtre ; `calendar_id` est nul
  pour une intersection de calendriers. F-19 : `getComputedValueDependencies` refuse un `field`
  hors de l'énumération par 422 sur `/query/field`, comme `resolveRowNumber` le numéro de ligne,
  sans 400. De F-17, ce lot ne fait que les exemples des refus qu'il crée — la catégorie
  discordante, la ligne de provision réestimée — ; le reste est à US-0702/L1 (#1610).

### Les risques : coût à la survenance, provision de référence, probabilité par le réexamen (US-0701/L4, #1604, H-01, H-02, H-03, H-04, M-01, M-04, M-05)

La passe de cohérence de la spécification du 2026-10-09 donne au risque survenu son **coût à la
survenance**, fait de la réserve un cumul à travers les références, dit ce que l'abandon fait des
risques et où la survenance range ses tâches (WF-RIS-0010, WF-RIS-0020, WF-RIS-0050, WF-RIS-0060,
glossaire). La décision de l'auteur du 2026-10-28 (« Les risques », recadrage d'EP-16) tranche ce
que la revue laissait au choix ; la proposition de la revue s'applique au reste (« la règle des
autres majeurs »). Réécrits, plus haut : la couverture de la « Révision de la spécification du
2026-10-04 » (décision de l'auteur du 2026-10-06, « le coût réestimé des lignes issues des risques
survenus »), la réserve d'US-0230/L2 et la borne de la modification d'US-0520/L2b ; complétée : « La
survenance d'un risque ne budgète rien ».

- **Le coût à la survenance** (H-01, H-02). `Risk.occurrence_cost`, exigé, nul pour un risque
  identifié ou écarté : le total du devis propre au moment de la survenance, qui ne change plus.
  `RiskCoverageTotals.occurred_cost` en est la somme, et la couverture le compare à la réserve ; le
  nom du champ reste (compatible, et `occurred` dit l'état des risques sommés). La couverture du
  portefeuille, qui reprend `RiskCoverageTotals`, le dit aussi. Sur le témoin, 200,00 pour « Retard
  de livraison des armoires », la gravité que retient le réexamen de sa survenance, égale aux 120 et
  80 réestimés de ses lignes fusionnées tant que rien n'a bougé : `mockhistory.coverage` somme
  désormais les coûts à la survenance, et non ces lignes ; les valeurs des exemples ne changent pas.
  `tools/tests/test_mockriskcoverage.py` tient le Vérif de WF-RIS-0050 : les lignes fusionnées
  réestimées et leurs tâches terminées, le coût des survenus et l'écart restent.
- **La provision d'un survenu ou d'un écarté** (H-03). `Risk.provision_amount` est la provision
  courante d'un risque identifié, et pour un survenu ou un écarté la provision qu'il portait dans la
  révision de référence, `0.00` s'il n'y était pas identifié : la ligne du registre se somme aux
  totaux, et le tri par provision compare des grandeurs de même nature. `RiskMatrixPoint` la
  reprend. `mockhistory.provision_amount` le calcule, comme les totaux le faisaient ; 752 et 753
  valaient déjà, par coïncidence, leur provision de référence. Écarté (décision de l'auteur) : un
  second champ, `reference_provision_amount`.
- **La probabilité par le seul réexamen** (H-04). `RiskUpdate` est défini en propre — libellé,
  description, actions de mitigation, catégorie, sous-projet et tâche de la provision, compteur —,
  sans `probability` ; `updateRisk` le dit, son 422 n'a plus d'exemple de probabilité, et
  `risk_update_probability_out_of_range` est retiré. Écarté (décision de l'auteur) : un réexamen
  implicite produit par `updateRisk`, deux chemins pour la même grandeur. Le formulaire de
  modification présente encore la probabilité : US-0703/L3 (#1614) la retire de l'écran.
- **La réserve cumulée** (M-01). `RiskCoverageTotals.reserve` dit la règle une fois — les lignes de
  provision de la référence, augmentées de la provision que portaient, dans la référence
  précédente, les risques survenus ou écartés avant elle ; un avenant ne la diminue jamais —, et
  `ProvisionTotals.reserve`, `EstimateLineFacet.budgeted_amount`, `getProjectRiskCoverage` et le
  portefeuille y renvoient. Le témoin n'a qu'une référence, marquée quand ses trois risques étaient
  identifiés : sa réserve reste 850 060,00, et aucun exemple ne montre un second avenant fusionné.
- **L'abandon ramène l'évaluation des risques** (M-04). `abandonRevision` dit qu'un risque créé
  dans la révision abandonnée disparaît, qu'un réexamen est défait, et qu'un risque déclaré survenu
  redevient identifié avec sa ligne de provision et sans coût à la survenance ; `RiskState`,
  `RiskOccurrence` et `declareRiskOccurrence` disent la survenance définitive, sauf par l'abandon.
  Sans exemple : le témoin n'abandonne aucune révision qui porte une saisie de risque (« Révisions
  et risques », EP-02/L23), et un exemple contrefactuel ne montrerait qu'un registre déjà lu.
- **La place des tâches fusionnées** (M-05). `declareRiskOccurrence` et `RiskOccurrence` disent la
  règle de WF-RIS-0060 — en dernière position sous la tâche porteuse, ou immédiatement après un
  jalon porteur, qui reste un jalon sans sous-tâche ; subordonnées, liaisons internes, durées et
  modes conservés ; une tâche sans prédécesseur dans le devis propre en mode manuel aux dates
  qu'elle y avait ; le réestimé recalculé des grandeurs et des dates —, que le compte rendu
  préalable d'US-0680/L1 disait déjà. Sur le témoin, la « Relance du fournisseur », sans
  prédécesseur dans le devis propre de 752, est en mode manuel du 4 au 8 mai 2026, ses dates
  d'avant, sans la liaison au « Câblage des armoires » qu'elle portait ; et la provision de 752 était
  portée, dans la référence, par le « Poste de commande », sous lequel ses tâches sont fusionnées.
  `structure_planning_start_advanced` redate une tâche de moins, 958. Le témoin tient la règle de
  placement : le sous-arbre fusionné (541, « Risque survenu — Retard de livraison des armoires ») est
  le dernier enfant du « Poste de commande » (551), après la « Réception usine », qui garde son
  seul prédécesseur, le « Câblage des armoires » ; ses lignes viennent donc après celle-là dans
  l'ordre du plan, jusqu'à la racine suivante (`tools/tests/test_mockriskcoverage.py`, WF-RIS-0060-A).
  Les numéros de ligne des nœuds qui suivent, dont la « Réception usine » et l'« Installation sur
  site », en sont décalés dans les exemples (`make mock-data`).
- **Les mineurs des fichiers touchés.** H-06 : l'axe des gravités est « en pourcentage de
  l'assiette du projet » (`RiskMatrixLevel`, `RiskMatrix.severity_levels`, `getProjectRiskMatrix`,
  `RiskMatrixSettings`). H-07 : `description`, `mitigation_notes`, `provision_node_id`,
  `matrix_cell` et `last_review_on` sont exigés, toujours rendus. H-09 : `states` a sa description,
  et les 409 d'`updateRisk`, `reviewRisk` et `deleteRisk` nomment les conditions d'état de la saisie
  des risques, jugées avant celles du risque, comme `createRisk`. H-08 l'était déjà (US-0700/L1) ;
  H-05 et H-10 sont à US-0702 et à US-0701/L6.

### La plateforme : lecture des comptes planifiée, renvoi de l'invitation, écran d'état, journal, devise (US-0701/L8, #1608, A-01 à A-04, B-01 à B-06, C-02, C-03, K-04)

Les constats de la plateforme de la revue du contrat avant le gel. La spécification les a écrits
dans ses passes du 6 octobre (le renvoi de WF-ADM-0140), du 9 octobre (la périodicité de
WF-ADM-0070, la planification livrée de WF-ADM-0170, le lien de WF-ADM-0190) et du 10 octobre (les
paramètres d'exploitation de WF-ADM-0130) ; la décision de l'auteur du 2026-10-28 (« La
plateforme », « La devise (C-02) », recadrage d'EP-16) tranche ce que la revue laissait au choix,
et sa proposition s'applique au reste (« la règle des autres majeurs »). Complétées, plus haut : le
journal d'EP-02/L42 (B-01, B-03) et ses paramètres de #706 (B-02).

- **La périodicité de la lecture des comptes** (A-02, WF-ADM-0070). `getIdentitySyncSchedule` et
  `setIdentitySyncSchedule` (`/identity-sync-schedule`), symétriques de la planification des
  sauvegardes : `IdentitySyncSchedule`, activation, fréquence, heure en temps universel, jour ISO
  d'une hebdomadaire, compteur ; lecture sous `users.read`, écriture sous `users.write`, celle de
  la lecture à la demande. Livrée activée et quotidienne, à `01:30` UTC, une demi-heure après la
  sauvegarde livrée ; l'heure livrée est un choix du lot, la spécification ne la donnant pas, et
  l'exemple du témoin la garde (`identity_sync_report`, achevée à 2 h). Écarté (décision de
  l'auteur) : un paramètre d'exploitation, contraire à « choisie par un utilisateur habilité ».
  Le schéma vit dans `platform.yaml`, à côté d'`IdentitySyncReport`.
- **Le renvoi de l'invitation** (A-04, WF-ADM-0140). `resendInvitation`,
  `POST /users/{user_id}/invitation` : 204 quand le fournisseur a envoyé le courriel, les refus du
  lien (`is_local_account`, `is_active_account`), et 503 `identity_provider` pour un courriel qui
  ne part pas, jamais présenté comme parti (WF-EXP-0040), l'écran proposant alors le lien. Le renvoi
  s'inscrit comme la demande d'un lien, `password_link_create` : c'est le même lien, remis par un
  autre canal, et `AuditAction` n'a pas d'action de plus. Écartés : le renvoi par la console du
  fournisseur d'identité (décision de l'auteur) ; une réponse 202, quand l'envoi se fait dans la
  requête comme le lien ; une action d'audit propre.
- **Les paramètres d'exploitation** (A-03, WF-ADM-0130, §4.5.1).
  `SystemStatus.operating_parameters`, exigé, un champ nommé par paramètre, sa valeur livrée dite
  dans sa description — l'objet de la première proposition de la revue plutôt que la liste de codes
  de sa seconde (K-02), qu'un client engendré ne type pas. La liste relevée dans la spécification,
  chaque paramètre qu'elle cite avec sa valeur par défaut : la durée de validité du cache, dix
  minutes (WF-DAT-0130) ; la rétention d'une tâche de fond, trente jours (§4.4.1) ; la taille d'un
  avatar, 512 Ko (§4.4.1) ; les trois seuils
  d'alerte de WF-OBS-0030, quinze minutes d'attente en file, 85 % d'occupation, 5 % d'erreurs — et
  la fenêtre de cinq minutes de ce dernier, part de sa valeur. Le fichier d'un export, supprimé au
  bout de vingt-quatre heures (WF-DAT-0120), et la durée du lien de fixation, une heure
  (WF-ADM-0140), sont des règles et non des paramètres ; la rétention des sauvegardes est un réglage
  de l'utilisateur (`BackupSchedule`). Le témoin a ses valeurs livrées, sauf l'avatar, porté à
  2 Mio comme `installation` le dit. La description de `SystemStatus` dit d'où vient chaque valeur
  (K-10), et les quatre dernières opérations sont exigées (B-08). Écarté (décision de l'auteur) :
  les cinq paramètres de la revue seulement.
- **Le Manager du témoin** (A-01, K-09 ; WF-INTF-0020, WF-ADM-0010). Le rôle prédéfini reçoit
  `risk_settings.write` et `indicator_settings.write` : `access_roles`, `access_role_updated`,
  `access_role_renamed`, `me_manager` et `me_directory`, écrits à la main, et les exemples engendrés
  qui les relisent (`make mock-data`) ; `mockaudit.WITHDRAWN` ne change pas, la modification de
  l'administration ne retirant que la saisie des coûts et des ressources. Le service, en retard
  sur le contrat jusqu'à EP-04 (option b de l'auteur, #1457), amorce encore le Manager sans elles :
  `test_access_roles_guard.py` nomme l'écart (`TO_SEED_BY_EP04`) et échoue dès qu'il est comblé.
- **Le journal** (B-01, B-02, B-03). `AuditProject.code` nul pour un projet sans code, rangé après
  les autres au tri par projet ; `AuditProject.can_open`, exigé : le contrat veut qu'il soit évalué
  pour l'appelant comme le portefeuille le fait (#389), dans les inscriptions et les facettes —
  faux pour un projet qui n'existe plus ; un objet qui vit dans un projet ne mène à lui que si le
  projet s'ouvre ; le service, jusqu'à EP-04, rend faux (voir plus bas).
  `audit_events_auditor` lit le journal du témoin par l'auditeur, qui n'ouvre aucun projet.
  `AuditParams` reçoit `to_state` et `reason` (`project_exit`), `backup_taken_at` (`restore`) et
  `import_kind` (`import_apply`) ; `mockaudit` les inscrit, la sortie du témoin vers `completed`
  sans motif, chaque import par sa nature. Écarté (décision de l'auteur) : aucun paramètre.
  **Le service, qui n'a aucun projet avant EP-04, rend `can_open` faux** (`PROJECT_OPENS`,
  `api/audit.py`) : un projet qu'il ne tient pas ne se consulte pas, et le modèle engendré, qui
  exige le champ, refusait sinon toute inscription d'un projet. C'est la seule ligne du service que
  le lot touche, à confirmer (option b de l'auteur sur #1457) ; EP-04 l'évaluera par appelant.
- **`AuditEvent` garde son nom** (B-06 ; §4.4.1, table 10). La table nomme l'objet `audit_entry`, et
  `user_account` le compte ; le contrat dit `AuditEvent`, `audit_event_id`, `/audit-events`, et
  `User`, `user_id`, `/users`. `event` est le mot des journaux structurés de la plateforme, dont
  l'inscription reprend la corrélation (WF-OBS-0020), et `User` celui de toutes les écritures des
  comptes ; la table vaut pour les tables de la base, que le service nomme `audit_entry`
  (migration 0003) et `user_account`. Écarté (décision de l'auteur) : le renommage en
  `audit_entry`, un chemin et un client changés sans gain de sens.
- **La sauvegarde planifiée** (B-04, B-05, K-12 ; WF-ADM-0170). `BackupSchedule` exige fréquence,
  heure et jour, nul pour une quotidienne ; un jour nul pour une hebdomadaire est refusé par
  `VALUE_REQUIRED`, un jour donné à une quotidienne par le motif `VALIDATION_FAILED`, sur
  `/weekday` (`backup_schedule_weekday_missing`). La rétention compte toutes les sauvegardes non
  marquées, manuelles ou planifiées, et la plus ancienne non marquée est supprimée au-delà :
  `backup_released` le dit de la manuelle du 30 janvier. La planification livrée, activée,
  quotidienne, à `01:00` UTC, sept conservées, sans copie externe, est la proposition de K-12 ; la
  spécification ne donne que « quotidienne ».
- **La devise** (C-02, WF-REF-0140). `getReferenceSettings` est lisible par toute session ouverte,
  sans 404 ; l'écriture garde ses permissions par champ. Écarté (décision de l'auteur) :
  `Installation.currency_code`, lisible sans session, quand la devise ne sert qu'à qui voit un
  montant. Le front lit encore la devise sur le seul écran des coûts : US-0703 la montre avec chaque
  montant.
- **Le code comptable non blanc** (C-03, WF-REF-0040, WF-ARC-0110). `pattern: '\S'` sur le code
  comptable reçu et lu, et sur les codes lus des nœuds, des natures et des catégories, comme
  #837 l'a fait des autres ; les 422 de la création et de la modification d'une catégorie le disent.
- **`structure_merge`** (K-04) était soldé par US-0640/L6b (#1594) — énumération, descriptions,
  générateur, exemples et décision, plus haut ; le back sert encore `amendment_merge` jusqu'à EP-04.
- **Les mineurs des fichiers touchés.** A-06 : la préférence des tâches ajoutées dit aussi les
  lignes à budget nul. A-07 : `ActorRef` exige l'identifiant et le nom d'un compte (`if`/`then`, qui
  garde le type engendré). A-08 : `org_node_id` et `has_avatar` exigés. A-09 : `BackgroundTaskRef`
  exige ses huit champs, `result_url` une `uri-reference`. A-10 : `access_role`, engendré par
  `mocklists`, `access_role_delete_refused`, `readiness` et `tasks_status_invalid`. A-11 :
  « rôle d'habilitation », et le 409 de `TASK_INTERRUPTED_BY_RESTORE` dit. B-09 : `confirmed`
  absent ou faux est un 400 `CONFIRMATION_REQUIRED`, deux sauvegardes ou aucune un 422. B-10 : la
  date d'une restauration et le dépôt sans projet. B-11 : la permission de `getBackup` et de
  `getBackupSchedule`. C-05 : `listHourlyRates` cite WF-DEV-0010. C-06 : `ReferenceSettings` et
  `DurationUnits` portent leur `audit`. C-07 : les cinq refus sans exemple ont le leur, et
  `cost_type_code_taken` est cité sous la modification. C-09 : un nœud autre que celui du rôle est
  refusé par `FIELD_READ_ONLY`. M-12 : l'emploi du code comptable par les fichiers de devis. M-13 :
  les bornes des zones d'un indice. J-12 : `listAccessRoles` dit pourquoi il n'est pas paginé.
  K-11 et J-16 : le point de métriques, interne au cluster, et son 404. B-07 n'est pas touché :
  ses exemples ne le sont pas. A-05 et C-01 sont à US-0702.

**Corrélations** 1594 à 1605 ; « corrélations, troisième suite » (1600-1999), la seconde étant
pleine.

### Les projets : la sortie marque ou abandonne la révision en cours (US-0701/L9, #1609, D-01, D-02, D-06, D-07)

Les constats des projets de la revue du contrat avant le gel. La spécification les a écrits dans
ses passes du 9 octobre (l'inscription d'un chef de projet par un non-contributeur, WF-PRJ-0060,
WF-ADM-0110) et du 10 octobre (le sort de la révision en cours à la sortie, WF-CYC-0090 ; la
présence des sorties, Vérif de WF-CYC-0060 ; la qualité nommée, WF-IHM-0090) ; la décision de
l'auteur du 2026-10-28 (« La sortie (D-01, L-02) », recadrage d'EP-16) tranche la réponse de la
sortie, et la proposition de la revue s'applique au reste (« la règle des autres majeurs »).
Complétées, plus haut : « Le projet terminal n'a pas de révision en cours » (US-0640/L1, #795) et
« Le projet et la révision portent leurs commandes disponibles » (EP-02).

- **La sortie reçoit le sort de la révision en cours** (D-01, L-02 ; WF-CYC-0090).
  `ProjectExit.current_revision` (`CurrentRevisionFate`) : deux variantes en `oneOf`, que
  `action` distingue (`discriminator`) — `CurrentRevisionMark` (`mark`), qui exige le nom de
  version, borné comme celui de `markRevision`, et porte sa description, et `CurrentRevisionAbandon`
  (`abandon`), qui n'en porte aucun —, pour que les générateurs tirent du contrat une union typée
  et non un `if/then` qu'ils ignorent ; l'énumération `CurrentRevisionFateAction` disparaît, le
  discriminant en tenant lieu. Exigé
  quand le projet porte une révision en cours : absent ou nul, 422 `VALIDATION_FAILED`,
  `/current_revision` par `VALUE_REQUIRED`, la forme du contrat pour un champ exigé ; un marquage
  sans nom, `/current_revision/version_name` par `VALUE_REQUIRED`
  (`project_exit_version_name_required`) ; un nom pris, 409 `ALREADY_EXISTS` sur ce pointeur,
  comme `markRevision` (`project_exit_version_name_taken`). Marquer rend 202 `BackgroundTaskRef` de
  nature `revision_mark`, la sortie s'appliquant quand la tâche réussit, rien quand elle échoue ;
  abandonner, ou sortir un projet sans révision en cours, rend 200 `Project`. Écartés (décision de
  l'auteur) : toujours 200, le marquage fait dans la requête, contraire à WF-ARC-0090 ; toujours
  202, quand rien n'est à calculer. Écartés par le lot : une nature de tâche `project_exit` — la
  tâche est le marquage, la transition sa suite — ; l'identifiant de la révision dans le sort,
  le projet n'en portant qu'une en cours. Pendant le marquage, comme pendant tout traitement de
  fond qui écrit dans la révision en cours ou la fige, les trois sorties nomment
  `no_background_task_running`, comme `update_work_breakdown`. Le journal inscrit l'abandon et la
  sortie, ou le marquage et la sortie, sous une corrélation : `mockaudit` inscrit l'abandon de la
  102 avant la sortie du témoin (`audit_events_exited`). Les exemples : `project_exit_abandoning`,
  dont la réponse est `project_completed`, qui dit la 102 abandonnée ; `project_exit_marking`, dont
  la réponse est `task_exit_mark_queued`, sous « Clôture » ; `project_exit_revision_required`. Les
  trois premiers disent mot pour mot qu'« après la sortie, le projet n'a plus de révision en cours,
  et ses indicateurs se lisent dans sa dernière révision marquée » (Vérif de WF-CYC-0090,
  `tools/tests/test_mockexit.py`). `subprojects_completed` ne nomme plus
  `subproject_without_estimate_lines` : aucune révision en cours ne porte plus leurs lignes. Restent
  à US-0702 : le compteur de la sortie (E-13, E-24) — le sort ne porte pas celui de la révision — et
  les codes des autres refus d'`exitProject` (D-03), dont un sort envoyé à un projet sans révision
  en cours, que ni la spécification ni la revue ne disent.
- **Une sortie qui ne le deviendra jamais n'est pas listée** (D-02, L-03 ; Vérif de
  WF-CYC-0060). `ProjectCommand` dit la règle : `complete` listée à tout état non terminal,
  `project_in_progress` manquante avant En cours ; `lose` aux états Créé, `project_in_pricing`
  manquante, et Chiffrage, absente dès En cours ; `abandon` à tout état non terminal. Un projet
  clos n'en liste aucune, à la lettre de la spécification : aucune ne le deviendra (WF-CYC-0080), et
  WF-IHM-0090 ne présente indisponible que ce qu'un état rend « momentanément » impossible.
  Écartée : les lister avec `project_not_terminal`, la règle antérieure du contrat, qui présente
  une commande qui ne sera jamais possible. **Réécrit par US-0702/L3** (décision de l'auteur du
  2026-10-30, #1657) : les autres commandes d'un projet clos suivent la même règle, aucune n'est
  listée. `lose` quitte `project`, `project_updated`,
  `project_without_current_revision`, `project_actual_cost_mapping_incomplete`,
  `reference_designated` et le projet en cours de `projects` ; les trois sorties quittent
  `project_completed`.
- **L'inscription d'un chef de projet par un non-contributeur** (D-06, L-17 ; WF-PRJ-0060).
  Quand aucun chef de projet du projet n'a de compte actif, l'appelant qui porte
  `project_settings.write` et `all_projects_read` écrit la liste sans être contributeur, pour y
  inscrire un chef de projet ; il la lit avec son compteur par `listContributors`, que « consulter
  tous les projets » lui ouvre. Sans chef de projet actif, sa liste est refusée par 409
  `LAST_PROJECT_MANAGER` ; toute autre saisie lui reste refusée par 403 `NOT_CONTRIBUTOR`, la règle
  commune, dont l'exception ne couvre que cette inscription. `manage_contributors` lui est listée,
  disponible, dans ce seul cas. Écartée : une condition `project_manager_active` (L-17), qu'une
  commande disponible n'a pas à nommer. Les exemples sont une variante contrefactuelle — Camille
  Martin désactivée, Dominique Bernard portant aussi « Direction de projet » —, aucun compte du
  témoin ne réunissant les deux permissions sans être contributeur :
  `contributors_without_active_manager`, `contributors_set_by_rescuer` (Inès Roux passée cheffe de
  projet) et `project_rescue`.
- **La qualité nommée** (L-25, J-18 ; WF-IHM-0090). Une commande que la permission donne et que
  la qualité ne permet pas est listée indisponible : `is_contributor` à un non-contributeur, et
  `is_project_manager` avec elle pour une commande réservée ; `is_project_manager` seule à un
  participant ; la qualité avant les conditions d'état, comme le 403 vient avant le 409. Les
  commandes réservées du projet sont le paramétrage (FBS-4.2 : attributs, lotissement,
  contributeurs) et les actions structurantes qu'il porte — les sorties, la survenance, l'exclusion
  d'une ligne (WF-ADM-0100) — ; `manage_timelines`, les imports et l'ouverture d'une révision ne le
  sont pas. `project_participant` le montre pour Inès Roux ; `project_reader` reste vide, le
  Manager n'ayant aucune permission d'écriture du projet. `task_not_milestone` (J-18) reste sans
  exemple : il tient à `setTaskProgress`, hors des fichiers du lot.
- **Le code projet borné** (D-07 ; WF-PRJ-0010, WF-CRE-0020). `ProjectCode`, partagé par
  `Project`, `ProjectSummary`, `ProjectCreate` et `ProjectUpdate` : de 1 à 50 caractères, jamais
  blanc, sans barre oblique. Vide, `VALUE_REQUIRED` ; blanc, `VALIDATION_FAILED`, comme tout libellé
  (#837) ; une barre oblique, `PROJECT_CODE_INVALID`, nouveau au catalogue comme
  `SUBPROJECT_CODE_INVALID` l'est pour le sous-projet (US-0610), et son exemple,
  `project_code_invalid`, qui porte `forbidden_characters: ["/"]` comme celui du sous-projet. Un
  code à la fois blanc et porteur d'une barre oblique reçoit `PROJECT_CODE_INVALID`, la barre
  oblique d'abord. Écarté : le motif commun `VALIDATION_FAILED` pour la barre oblique, qui
  ne laisserait pas le formulaire dire pourquoi. Le doute de la revue sur `code: null` d'un projet
  en cours n'est pas tranché ici.
- **Les mineurs des fichiers touchés.** D-04 : `updateProject` dit le 409 de la probabilité
  figée. D-08 : les sous-projets regroupent des lignes de devis, jamais une tâche. D-09 : le
  lotissement reproduit le bon de commande. D-11 : une saisie porte au moins un lot (`minItems`,
  422 `VALUE_REQUIRED` sur `/work_packages`), et le lotissement par défaut suit le libellé du
  projet tant qu'aucune saisie ne l'a écrit ; écartée, la saisie vide qui ramènerait le défaut,
  sous des identifiants nouveaux. D-12, J-13 : `TimelineCreate`, son nom jamais blanc. D-10 est à
  US-0702/L2 (#1611), D-13 à US-0702.

**Corrélations** 1606 et 1607 ; la tâche de fond 955.

### Une seule forme pour chaque refus (US-0702/L1, #1610)

La revue du contrat avant le gel (`2026-10-28-contrat-avant-gel.md`, D-05, J-01 à J-11, E-07, F-05)
relevait deux formes pour un même refus et un catalogue qui porte des codes que rien ne rend. Le
lot donne à chaque refus un statut, un code, ses paramètres et un exemple, ou retire le code ; les
exemples nouveaux sont engendrés par `make mock-data` (`wftools.mockrefusals`). Les décisions
qu'il contredit sont réécrites à leur place, en citant la décision de l'auteur du 2026-10-28.

- **La règle unique des refus d'état** (D-05, J-01, J-02 ; décision de l'auteur du 2026-10-28 ;
  WF-IHM-0090, WF-CYC-0100, WF-DAT-0020). La règle d'EP-02/L42a — « le refus d'une commande qu'un
  état rend indisponible est `STATE_FORBIDS_OPERATION` » — devient celle de tout le contrat, et le
  README la dit (« Conventions ») : 409, `params.missing_condition` la condition que l'objet dit
  d'avance de sa commande ; un projet terminal, `project_not_terminal`, une révision marquée,
  `revision_draft`. `createTimeline` et `deleteTimeline` déclarent ce 409
  (`timeline_create_terminal`, engendré ; `timeline_delete_terminal`, écrit à la main par #803,
  passé de 403 à 409) ; `createNode` et `generatePlanningSkeleton` le nomment sur une révision
  marquée (`node_create_marked_refused`, `skeleton_marked_refused`, sur la référence 101). Toute
  révision d'un projet terminal est marquée — la sortie marque ou abandonne la révision en cours
  (US-0701/L9) — : une saisie de grille sur un projet terminal n'a donc que `revision_draft` à
  nommer. `PROJECT_TERMINAL` et `REVISION_MARKED` sortent d'`ErrorCode` ; `Forbidden` ne dit plus
  que la permission (`PERMISSION_MISSING`) ou la qualité de l'appelant (`NOT_CONTRIBUTOR`,
  `NOT_PROJECT_MANAGER`), et `Conflict` dit la règle. Réécrits : EP-14/L42k (le squelette et la
  chronologie restés des 403), EP-14/L42s (« les 403 des saisies de la révision ») et
  US-0640/L1 #803 (« le premier exemple de ce refus »). Écartés, par l'auteur : 409 hors grille et
  403 sur la grille, deux règles pour un même fait ; 403 partout, contraire à L42a, L42i, L42l et à
  la lecture commune des conditions par le front. **Réécrit par US-0702/L3** (décision de l'auteur
  du 2026-10-30, #1657) : les commandes d'un projet clos ne sont plus listées ; le 409 reste.

- **Le catalogue sans code mort** (J-03, J-11 ; WF-ARC-0110, WF-IHM-0090). Chaque code
  d'`ErrorCode` est nommé par une opération ou un schéma, et chaque valeur de `CommandCondition`
  dite par sa description et nommée par une opération, un schéma ou un exemple :
  `tools/tests/test_contract_catalogue.py` le tient, et tient aussi que chaque code est porté par un
  exemple, sans liste d'attente. Les onze codes rendus par une opération sans exemple — J-17 et les
  deux motifs d'une ligne importée — ont le leur, engendré (`wftools.mockrefusals`), sous
  l'opération qui le déclare : `SESSION_REQUIRED` (réponse commune `Unauthorized`),
  `ACCOUNT_DEACTIVATED` et `ACCOUNT_NOT_ADMITTED` (`getMe`), `MALFORMED_REQUEST` et
  `FILE_TOO_LARGE` (`putMyAvatar`, qui déclare ses deux réponses), `NOT_CONTRIBUTOR`
  (`updateProject`), `NUMBER_INVALID` et `DATE_INVALID` (`listAccessRoles`), `UNKNOWN_CALENDAR`
  (`createResourceRole`), `WBS_ELEMENT_INVALID` (`getImport`, variante de l'extraction d'avril,
  l'élément « /SP-CAB ») et `AMBIGUOUS_TASK_LABEL` (`getImport`, un reste à engager dont une ligne
  cite « Mise en service », libellé que portent deux tâches du témoin). Aucun code n'est retiré
  pour cette raison. Rendus : `NOT_PROJECT_MANAGER`, le 403 de qui n'est que
  contributeur pour une commande réservée, `params.missing_condition` à `is_project_manager`
  (`project_update_not_manager`, le modèle d'EP-02/L7, enfin rattaché à une opération) ;
  `project_code_set`, que `getProjectNextState` nomme tant que le code manque
  (`next_state_pricing_without_code`, Vérif de WF-PRJ-0010) ; `project_in_pricing`,
  `no_current_revision`, `project_not_terminal`, `project_in_progress`, `revision_draft` et
  `reference_revision_designated`, employés et désormais décrits. Retirés : `TASK_ALREADY_STARTED`
  et `TASK_COMPLETED`, doublons de `STATE_FORBIDS_OPERATION` sous la règle unique — le refus de
  `deleteNode` sur une tâche démarrée ou terminée sera une condition (F-04, US-0702/L2, #1611).
  **Écart soldé :** de ce lot à US-0702/L2, `deleteNode` n'avait aucun refus nommé pour une tâche
  démarrée ou terminée ; US-0702/L2 le rend par `task_not_started` (F-04, plus bas). Retirés aussi :
  `PROJECT_CODE_REQUIRED`, que rien ne refuse, le passage à En cours étant automatique et sa
  condition nommée par `project_code_set` ; `at_least_one_estimate_line` et `hourly_rates_set`,
  qu'aucune commande ne nomme. Écarté : garder les codes d'état pour `deleteNode`, deux formes pour
  un même refus.
- **Le taux manquant et le rôle absent nommés** (J-06 ; WF-DEV-0010, WF-DEV-0020). Le calcul
  qu'une ligne demanderait sans taux horaire pour l'année de référence est refusé par 422
  `HOURLY_RATE_MISSING`, sans `fields`, `params.missing_rates` nommant les catégories (`MissingRate`,
  le schéma de `getMissingRates`), sur `createNode` et `updateEstimateLine`
  (`estimate_line_rate_missing`, l'ingénierie électrique sans taux 2026, comme `missing_rates` le
  suppose) ; l'échec d'un marquage porte le même motif (`markRevision`, `BackgroundTaskRef.kind`,
  `task_failed`, écrit à la main, qui reçoit les paramètres). Le rôle retiré d'une ligne de
  main-d'œuvre, `/resource_role_id` par `RESOURCE_ROLE_REQUIRED` (`estimate_line_role_required`).
  `missing_rates` est typé dans `ProblemParams`. Écarté : un motif par champ sur
  `/cost_category_id`, que la revue proposait — la catégorie d'une ligne de main-d'œuvre est celle
  de son rôle et ne se saisit plus (F-09, US-0701/L3), et une saisie de la seule charge n'aurait
  aucun champ à désigner : c'est le calcul de la ligne qui est refusé, comme celui du marquage.
- **L'annulation refusée en nommant l'objet en conflit** (E-07, J-05 ; WF-IHM-0110). Une
  annulation ou un rétablissement qui défairait une modification postérieure sur le même objet :
  409 `UNDO_CONFLICT`, `params.conflicting_object_id` et `conflicting_object_label` — les
  paramètres que le front lit déjà pour l'objet en conflit (`conflictingOf`, #714) —, sur
  `undo_later_change` et `redo_later_change`, variantes écrites à la main qui reçoivent la ligne du
  « Raccordement des borniers ». Un historique vide n'est pas un conflit : 409
  `STATE_FORBIDS_OPERATION`, `undo_history_not_empty` ou `redo_history_not_empty`, conditions
  nouvelles qu'aucune commande ne dit d'avance (`undo_history_empty`, `redo_history_empty`).
  Écartés : un paramètre par nature d'objet (`conflicting_node_id`, `conflicting_risk_id`), puis un
  `conflicting_object_kind`, que la revue proposait — l'identifiant et le libellé suffisent à
  nommer l'objet, comme pour `ALREADY_EXISTS`.
- **Les valeurs d'une récapitulative** (F-05, J-04 ; WF-PLA-0040, WF-IHM-0030). Son état envoyé à
  `setTaskProgress` est refusé par 422 `SUMMARY_TASK_DERIVED`, `params.subordinate_node_ids` ses
  subordonnées directes dans l'ordre du plan (`task_progress_summary_refused`, « Études ») ; une
  date envoyée à `updateTaskFacet`, par le même code en motif de champ, `fields[].params`
  (`task_summary_date_refused`, « Poste de commande », Vérif de WF-IHM-0030). `COMPUTED_VALUE`
  reste le motif d'une date d'une tâche en mode automatique qui n'est pas une récapitulative, et
  celui du mode d'une récapitulative (US-0701/L3). `subordinate_node_ids` est typé dans
  `ProblemParams`. La décision « Calculé contre saisi » (EP-02) reçoit enfin ses opérations.
  Écarté : `COMPUTED_VALUE` avec les subordonnées, et `SUMMARY_TASK_DERIVED` retiré — le code
  dit déjà la récapitulative au compte rendu d'un import (`ImportSignal`).

- **Le 500 déclaré** (J-07 ; WF-ARC-0060, WF-OBS-0020). Une réponse partagée, `InternalError` —
  `INTERNAL_ERROR`, sans paramètre, son `correlation_id` la référence que le front affiche
  (`internal_error`) —, que chacune des 168 opérations déclare sous `'500'`, et une règle de
  `redocly.yaml`, `rule/operation-declares-500`, qui le tient, comme le 401 et le 503 des
  opérations gardées. Le service la rend déjà (US-0640/L2, `CorrelationMiddleware`). Écarté : une
  réponse `default`, qui coûtait autant de lignes et aurait promis l'enveloppe `Problem` pour tout
  statut non déclaré — un 502 ou un 504 d'une passerelle n'en porte pas, et le front le lit comme
  l'API injoignable —, et que le client engendré n'aurait pas lue plus précisément qu'un 500
  nommé ; une règle seule, sans la réponse dans les opérations, que le client engendré ne verrait
  pas.
- **`fields` refusé en 422** (J-10 ; WF-ARC-0110, WF-IHM-0130). Une propriété inconnue de
  `fields` : 422 `VALIDATION_FAILED`, `/query/fields` par `FIELD_NOT_ACCEPTED`
  (`nodes_fields_unknown`, cité par `listNodes` et `compareRevisions`) ; le `400` sort de ces deux
  lectures, les seules opérations sans corps qui le déclaraient. Réécrit : EP-02/L4 (« refusée
  (400) »).

- **Les refus de l'arbre commun sans exemple** (F-17, #1648). Engendrés : une ligne de
  main-d'œuvre qui laisserait le « Câblage des armoires » sans heure travaillée, créée
  (`node_create_without_hours`) ou passée à un autre rôle (`estimate_line_without_hours`), les
  calendriers supposés autres, comme `import_estimate_task_without_hours` le fait — ceux du témoin
  se recoupent tous ; un champ que le nœud n'accepte pas, sur `createNode`, `updateTaskFacet` — la
  durée d'un jalon — et `updateEstimateLine` (`node_create_field_not_accepted`,
  `task_milestone_duration_refused`, `estimate_line_field_not_accepted`) ; une catégorie de
  provision donnée à une ligne saisie (`estimate_line_provision_reserved`) ; une ligne d'une tâche
  terminée réestimée (`remaining_completed_refused`). Le 409 d'`applyPaste` est décrit : la
  commande de la structure, une ligne refusée du bloc restant dans `rejected`. `COMPUTED_VALUE`
  était déjà nommé dans le 422 d'`updateEstimateLine`.
- **Les mineurs des fichiers touchés.** #1646 : les lignes orphelines du repli à 100 colonnes de
  `paths/revisions.yaml`. #1647 : le test de `nodes_bounds_inverted` liste les opérations qui le
  citent, l'en-tête de `test_mockbreakdown.py` ne compte plus ses tests, la docstring de
  `mockcore.dependencies` est refluée. #1654 : le test des rôles prédéfinis dit ce qu'il couvre de
  la Vérif de WF-ADM-0010-A et où le reste est éprouvé. Les autres refus — D-03, E-05, E-12 à
  E-14, F-03, F-04, F-11, H-08, I-06, I-17, A-05, C-01, et le compteur des cinq écritures — sont
  ceux d'US-0702/L2 (#1611), ci-dessous.

**Corrélations** 1610 à 1637 ; les deux imports nouveaux, A30 et A31, et leurs tâches d'analyse,
956 et 957.

### Les refus sans code ni exemple, et le compteur des écritures concurrentes (US-0702/L2, #1611)

La revue du contrat avant le gel relevait des refus déclarés sans code, sans condition ni exemple
(D-03, D-10, E-05, E-12 à E-14, F-03, F-04 et son double H-05, F-11, H-08, I-06, I-17, A-05,
C-01), et cinq écritures sans compteur (E-13, E-24, « Doutes »). Chaque refus suit la règle unique
d'US-0702/L1 ; ses exemples sont engendrés par `make mock-data` (`wftools.mockdeclared`).

- **Le compteur des cinq écritures** (décision de l'auteur du 2026-10-28 ; WF-IHM-0110).
  `abandonRevision`, `deleteRisk` et `deleteSubproject`, suppressions sans corps, exigent
  `lock_version` en paramètre, le compteur de l'objet supprimé, comme `deleteNode` (#1210), et
  déclarent le 412 ; un compteur absent ou mal formé est le 422 partagé `LockVersionInvalid`,
  que `deleteNode` reprend. `exitProject` et `designateReferenceRevision` le portent dans leur
  corps (`ProjectExit.lock_version`, `ReferenceDesignation.lock_version`), celui du projet,
  qu'elles écrivent. **Exception écrite** : le `PUT` du périmètre suivi
  (`setActualCostTrackedScope`) reste idempotent, sans compteur ni 412 — il pose l'état visé sans
  dépendre d'aucune autre valeur de la ligne, et deux requêtes concurrentes ne peuvent que donner
  le même état ou le dernier demandé ; sa description et le README (« Conventions ») le disent.
  Réécrit : « Un état est une ressource, pas un verbe » (plus haut) — `designateReferenceRevision`
  n'est plus rejouable telle quelle, son compteur ayant avancé à la première désignation. Écartés,
  par l'auteur : le compteur partout, `tracked-scope` compris, dont l'idempotence était décidée ;
  rien, contraire à la convention.
- **La sortie** (D-03 ; WF-CYC-0060, WF-CYC-0080, WF-CYC-0090). Son 409 est
  `STATE_FORBIDS_OPERATION`, la première condition de sa commande : `project_not_terminal` pour
  toute sortie d'un projet terminal, où la commande n'est jamais listée depuis US-0702/L3, #1657
  (`project_exit_terminal`),
  puis `project_in_progress` pour Terminé, `project_in_pricing` pour Perdu
  (`project_exit_lost_in_progress`, Perdu depuis En cours), puis `no_background_task_running`.
  `confirmed` absent ou faux est un 400 `CONFIRMATION_REQUIRED` (`project_exit_unconfirmed`),
  comme pour la restauration (B-09, US-0701/L8) ; le schéma le laisse à la garde depuis US-0702/L3
  (#1664), sans `const: true` ni `required`. Écarté : un 422 `VALUE_REQUIRED` sur
  `/confirmed`, que la revue proposait aussi — le catalogue dit déjà la confirmation absente par
  ce 400, et deux formes pour une même garde en feraient deux règles.
- **Les révisions et leurs structures** (E-05, E-12 à E-14 ; WF-REV-0010, WF-REV-0020,
  WF-REV-0100). Le marquage, l'abandon et l'ouverture d'un différentiel nomment `revision_draft`
  puis `no_background_task_running` (`mark_revision_marked`, `revision_abandon_marked`,
  `structure_create_revision_marked`, sur la référence 101) ; `RevisionCommand` dit les conditions
  de `mark`, `abandon` et `designate_reference`. `project_not_terminal` n'y est pas nommée : toute
  révision d'un projet terminal est marquée, et `revision_draft` y suffit (US-0702/L1).
  L'ouverture d'une révision nomme aussi `project_not_terminal` et `no_background_task_running`
  pendant un traitement qui la crée (`revision_create_background_running`, variante de l'offre).
  Le nom de version déjà employé est refusé par le marquage et par la fusion comme par la sortie,
  `ALREADY_EXISTS` sur `/version_name` (`mark_version_name_taken`, `merge_version_name_taken`),
  jugé au dépôt de la fusion : aucune révision en cours n'est créée pour échouer au marquage
  (#790). Un différentiel naît copie de la structure principale, ses nœuds `unchanged` ; son
  libellé n'est pas unique, plusieurs coexistant (#1211).
- **L'arbre commun** (F-03, F-04, H-05, F-11 ; WF-PLA-0030, WF-PLA-0060, WF-PLA-0070,
  WF-RIS-0010). Un prédécesseur nommé deux fois : 422, motif nouveau `DUPLICATE_PREDECESSOR`
  sur chaque occurrence après la première (`predecessors_duplicate`) — ni `ALREADY_EXISTS`, l'unicité
  d'un objet, ni `DUPLICATE_WORK_BREAKDOWN_ITEM`, propre au lotissement. La suppression d'une tâche
  démarrée ou terminée, ou d'une récapitulative dont une subordonnée l'est : condition nouvelle
  `task_not_started` (`node_delete_started_refused`, le « Câblage des armoires »), que l'état de
  la tâche montre d'avance, aucune commande du nœud ne la disant ; la citation fautive « portant un
  coût réel » est retirée. Les lignes de provision des tâches supprimées passent sur la tâche que
  WF-RIS-0010 désigne, rendues dans `nodes` ; la suppression qui laisserait sans tâche une
  structure principale qui en porte est refusée par `at_least_one_task`, la condition qui dit déjà
  qu'une ligne de provision doit avoir une tâche où se ranger, `params.risks` nommant les risques
  (`ProblemRisk` ; `node_delete_last_provision_task_refused`, variante contrefactuelle). Le déplacement a son exemple
  engendré, `node_deleted_provision_moved` (L-11) : variante contrefactuelle du témoin, dont la seule
  tâche porteuse de provision est démarrée, où une tâche non démarrée la porte seule ; `nodes` rend la
  ligne sous sa tâche parente, le risque, que `NodesWritten` ne porte pas, se relit par `getRisk`. Écartés :
  `TASK_ALREADY_STARTED` et `TASK_COMPLETED`, retirés par US-0702/L1 ; une condition nouvelle
  pour la dernière tâche, que la revue proposait (`provision_task_remaining`), quand
  `at_least_one_task` dit le même fait. L'inscription aux suivis a son 409, celui de
  `edit_planning` (`node_tracking_marked_refused`) ; `TrackingEntry` dit sa règle : `timeline_id`
  exigé pour `timeline` (`VALUE_REQUIRED`), d'une chronologie du projet (motif nouveau
  `UNKNOWN_TIMELINE`), refusé pour `milestone_tracking` (`FIELD_NOT_ACCEPTED`), une entrée répétée
  à l'identique n'en faisant qu'une (`node_tracking_timeline_required`,
  `node_tracking_timeline_unknown`). Écarté : refuser l'entrée répétée, qui ne porte rien d'autre
  que ce qu'elle répète.
- **La survenance, le périmètre suivi, l'export, le résultat d'une tâche** (H-08, I-06, I-17,
  A-05). Le 409 de `declareRiskOccurrence` dit l'ordre : les conditions du projet, puis celles du
  risque (`risk_occurrence_not_identified`, US-0700/L1). Celui de `setActualCostTrackedScope` nomme
  `project_not_terminal` puis `project_in_progress`, comme `exclude_cost_lines`
  (`actual_cost_scope_terminal`) ; depuis US-0702/L3 (#1657), un projet terminal ne liste plus
  ces commandes, et seul ce 409 nomme `project_not_terminal`. Le 409 de `requestExport` est retiré : un export ne manque
  d'aucune condition (EP-02/L17). Celui de `getBackgroundTaskResult` nomme la condition nouvelle
  `task_succeeded` pour une tâche en file, en cours ou en échec (`task_result_not_succeeded`) ; une
  tâche qui ne produit pas de fichier est un 404, comme un résultat supprimé. Écarté : le même
  `task_succeeded` pour une tâche aboutie sans fichier, que la revue proposait — la condition ne
  dirait pas la vraie cause.
- **Le référentiel** (C-01, D-10 ; WF-REF-0150, WF-ADM-0100, WF-ADM-0110). `listOrgNodes`,
  `listCalendars` et `listCostTypes` déclarent le 403 de `include_inactive` et `is_active` faux,
  `PERMISSION_MISSING` à `resource_settings.write` ou `cost_settings.write`, avec un exemple chacune
  (`*_inactive_forbidden`). La question « qui lit les objets actifs », que la revue laissait au
  passage, n'est pas tranchée ici : le 404 reste tel qu'il était. `createSubproject` déclare le 404.
- **L'outil** (#1662). `mockrefusals.problem`, `state_refused` et `field_refused` restent publics :
  `mockdeclared` les reprend, et aucune règle ne demande le préfixe à une fonction partagée entre
  générateurs ; le rapport d'import qu'il réécrit est typé (`_ImportReport`) au lieu de
  `dict[str, Any]`.

**Corrélations** 1638 à 1657.

### Un projet clos ne liste aucune commande ; la confirmation laissée à la garde (US-0702/L3, #1667)

Deux décisions de l'auteur du 2026-10-30, sur les recommandations de US-0702/L1 (#1657) et de
US-0702/L2 (#1664). Les décisions qu'elles contredisent sont réécrites à leur place.

- **Un projet clos ne liste aucune commande** (#1657 ; WF-IHM-0090, WF-CYC-0060, WF-CYC-0080,
  WF-CYC-0100). La règle d'EP-02/L42a, devenue celle de tout le contrat par US-0702/L1, reçoit sa
  borne : un projet terminal ne liste aucune commande, ni sur lui-même, ni sur ses sous-projets,
  ses révisions, leurs structures et leurs nœuds, ses risques — seuls les exports d'une révision
  restent listés, disponibles, qui ne le modifient pas (WF-CYC-0110). WF-IHM-0090 ne présente
  indisponible que ce qu'un état rend « momentanément » impossible, et un état terminal est
  irréversible (WF-CYC-0080) : aucune de ces commandes ne le redeviendra. C'est la règle qu'US-0701/L9
  posait pour les trois sorties (« Une sortie qui ne le deviendra jamais n'est pas listée », Vérif de
  WF-CYC-0060), étendue à toutes. Le README (« Conventions ») et `Project.available_commands` le
  disent ; `Subproject`, `Revision`, `CostStructure` (`StructureCommand`) et `Risk` le rappellent.
  Un appel direct reste refusé par la règle unique : 409 `STATE_FORBIDS_OPERATION`,
  `params.missing_condition` à `project_not_terminal`, dans l'ordre que chaque opération dit
  (`timeline_create_terminal`, `timeline_delete_terminal`, `project_exit_terminal`,
  `actual_cost_scope_terminal`). `project_completed` ne liste plus rien, ses quinze commandes
  indisponibles retirées ; `subprojects_completed` garde ses deux sous-projets, sans commande. Réécrits :
  US-0701/L9 (« Les autres commandes d'un projet clos gardent leur forme »), US-0702/L1 (« Les
  commandes d'un projet clos restent listées »), EP-14/L42o et L42l (les commandes des sous-projets
  d'un projet clos, toutes indisponibles, `project_not_terminal` en dernier — ce dernier ordre reste
  celui du 409 de `deleteSubproject`).
  **`project_not_terminal` reste dans `CommandCondition`** : aucune commande listée ne la nomme plus,
  mais le 409 d'un appel direct la nomme, et `ProblemParams.missing_condition` est une
  `CommandCondition` (J-03, J-11 : la condition est rendue par des opérations, avec leurs exemples).
  Sa description le dit. Écartées : la retirer de l'énumération, qui laisserait le 409 sans valeur
  typée ; lister les commandes avec elle, la règle antérieure, qui présente des commandes qui ne
  seront jamais possibles.
- **`confirmed` laissé à la garde** (#1664 ; WF-CYC-0090, WF-ADM-0160 ; B-09, D-03). `ProjectExit`,
  `ReferenceDesignation` et le corps de `startRestore` (`RestoreRequest`) ne portent plus
  `const: true`, et `confirmed` sort de leur `required` : `type: boolean`. Absente ou fausse, la
  confirmation est refusée par 400 `CONFIRMATION_REQUIRED`, sans paramètre, comme US-0702/L2 et B-09
  l'ont décidé ; avec `const: true` ou `required`, les modèles engendrés du service répondaient 422
  `VALIDATION_FAILED` avant la garde, contre ce que le contrat promettait. `startRestore` le rend
  (`waterfall.api.restores`) ; `designateReferenceRevision` décrit son 400. Écarté : garder
  `confirmed` exigé, qui laisserait la confirmation absente au 422 du corps — deux formes pour une
  même garde, que US-0702/L2 a écartées. Le client du front reçoit `confirmed?: boolean`. Les autres
  confirmations du contrat (`ImportApply`, `StructureMerge`, `PasteApply`, `RiskOccurrence`) gardent
  `const: true` : elles ne promettent aucun 400.

### Le filtre des écarts et le décompte de la matrice des risques (US-0700/L1, #1455, #1398, #1395)

Les décisions de l'auteur du 2026-10-23 dans #1398 et #1395 font foi ; les « à trancher au lot »
qu'elles nomment le sont ici. Rien ne filtrait encore sur l'écart d'un nœud : les filtres de
colonne d'US-0701/L3 portent sur la grandeur que la comparaison affiche, « jamais sur l'écart que
`difference` dit », et restent tels ; ce lot ajoute le seul filtre qui manquait.

- **Le filtre `difference`** (#1398 ; WF-REV-0080, WF-REV-0100, WF-IHM-0130). Un paramètre partagé,
  `NodeDifferenceFilter`, que `listNodes` et `compareRevisions` citent comme les autres filtres de
  l'arbre (#1193), une liste (`explode: false`) de `added`, `removed` et `modified` ; « Écarts
  seulement » les nomme toutes trois. `unchanged` n'en est pas : ce n'est pas un écart. Chaque
  nœud, tâche ou ligne, se juge sur sa propre marque — une tâche retenue n'emporte pas ses lignes
  inchangées, à la différence d'un filtre sur la tâche, qui retient ses lignes : l'écran ne montre
  que ce qui change, et une ligne qui change est retenue par sa marque. Les ancêtres d'un nœud
  retenu sont rendus, comme pour tout filtre, et sont `modified` par leur contenu (`NodeDifference`,
  US-0500/L1) : avec `modified` parmi les valeurs, ils sont retenus par leur propre marque ; avec `added` ou
  `removed` seuls, ils ne le sont que pour que l'arbre reste un arbre. Un nœud déplacé est retenu à sa place nouvelle, `parent` parmi ses
  `changes`. `modified` ne se scinde pas entre « par ses valeurs » et « par son contenu » : la
  grille le dit déjà par `changes`, comme l'auteur le pressentait.
- **Les totaux ne changent pas avec lui** (#1398, recommandation de l'issue). `totals` est celui de
  la lecture sans `difference` : de la structure entière sans autre filtre, comme l'issue le
  recommande, et d'un sous-arbre lu par ses écarts, celui du sous-arbre. La somme des seules lignes
  ajoutées et modifiées ne serait la grandeur de rien ; la grille d'un différentiel garde le total
  de l'avenant, et l'écart se lit dans `amount_deltas`, qui reste « sur les lignes retenues »
  (US-0500/L5) : celles que le filtre retient. **Réécrit, sous ce seul filtre** : « Les totaux sont
  ceux des lignes retenues » (`listNodes`, `NodeTotals`) et le parallèle d'US-0500/L5, où
  `amount_deltas` « se calcule de même » que `totals` ; `difference` se range avec `kinds`, qui ne
  change pas les totaux (#487). `NodeTotals`, `RevisionComparison.totals`, `amount_deltas` et les
  deux opérations le disent. Une ligne dont seul le sous-projet change reste `unchanged` —
  `NodeChange` ne nomme pas le sous-projet — : « Écarts seulement » ne la retient pas, et ses écarts
  par sous-projet, que la comparaison lue entière compte, n'y sont pas (relevé hors de ce lot).
- **Sans effet sur la structure principale et le devis propre d'un risque**, où `difference` est
  nul (#1398, « soit un refus, soit une lecture inchangée ») : la lecture est celle sans lui. Choisie
  au plus près du contrat : l'auteur le dit « sans effet » ; `PortfolioStates` est déjà « sans
  effet » sur ce que sa vue ne compte pas ; et aucun filtre de l'arbre n'est refusé pour ce qu'il
  retiendrait — `subtree_of` sur une tâche retirée, dont le refus a été écarté (US-0500/L5),
  `work_package_id` sur un différentiel. Écartés : un 422 `VALIDATION_FAILED`, `/query/difference`
  par `FIELD_NOT_ACCEPTED`, motif qui dit un champ que le nœud ou `fields` n'accepte pas, et ne
  dirait pas la vraie cause ; un 409 `STATE_FORBIDS_OPERATION`, une lecture n'étant pas une
  commande, et aucune `CommandCondition` ne disant la nature d'une structure ; un code nouveau, hors
  du catalogue unique d'US-0702/L1 ; une lecture vide, lecture stricte d'une marque nulle, qui
  viderait la grille de la principale pour un paramètre qui n'y a pas de sens. Le front ne l'offre
  que sur un différentiel et sur la comparaison (US-0700/L2).
- **Les exemples**, engendrés, nommés comme leurs voisins (`nodes_estimate_filtered`,
  `comparison_moved`) : `nodes_amendment_differences` (`listNodes`, `amendment_differences`),
  l'avenant 2 lu entier par « Écarts seulement », 8 nœuds des 6 003 de l'arbre marqué, ses totaux
  ceux du différentiel entier ; `comparison_differences` (`compareRevisions`, `differences`), l'offre
  et la référence sur toute la structure par `difference=added,removed`, deux valeurs combinées —
  5 ajoutés, 2 retirés et leurs 5 ancêtres modifiés par leur seul contenu —, les totaux de la
  référence entière, ceux de `comparison_volume`, et les écarts des seules lignes retenues.
  `comparison_differences` est exempté de #421 comme `comparison`, dont il nomme les nœuds de même
  (`tools/tests/test_mockversions.py`). `mockdiff.differences` filtre l'arbre marqué ; prism, qui
  ne lit pas les paramètres de requête, sert le premier exemple comme pour tout filtre.
- **Le décompte de la matrice des risques** (#1395, part contrat ; WF-RIS-0040, WF-ARC-0020).
  `RiskMatrix.cells` compte, par case, les seuls risques identifiés, ceux que le graphique trace en
  bulles ; le serveur compte, le front jamais. `points` garde les risques lus avec leur état, que
  l'écran filtre (#1053) — retirer du graphique les survenus et les écartés est la part front de
  #1395, à EP-17 —, et `totals` reste sur les trois états. **Réécrit** : « Elle les compte par case
  et les rend un par un, les mêmes » (`RiskMatrix`, #1053), et les points « que comptent ses
  cases ». La matrice du portefeuille comptait et rendait déjà les seuls identifiés
  (`identified_risks`, WF-PTF-0090) : `volume/portfolio_risks` ne change pas. `risk_matrix` compte
  1 risque au lieu de 3, le « Risque de reprise du câblage », `risk_matrix_no_basis` de même.
  Écarté : restreindre aux identifiés les points d'un projet, qui changerait ce que l'écran lit
  avant qu'EP-17 n'en change la présentation.

### Les tâches qu'un reste à engager termine (US-0703/L7, #1618)

L'adoption par le front du compte rendu des imports l'a révélé : aucun exemple ne portait un
`completed_tasks` non vide, et l'écran des tâches terminées par un import ne s'éprouvait que sur un
objet écrit à la main (WF-INTF-0120, WF-INTF-0130). Le manque se corrige au contrat, dans l'US.

- **`import_remaining_completed_tasks`**, nouvel exemple de `getImport`, engendré par
  `wftools.mockexchanges`. Un reste à engager analysé aujourd'hui, une variante qu'`imports` ne
  reprend pas, dont le fichier porte en « Synthèse » la revue du 1er juin 2026 : ses six lignes,
  chacune dans l'onglet de son sous-projet, ramenées à zéro, un écart chacune ; ses deux tâches
  terminées à cette date, non au jour de l'import — « Mise en service », du cœur, non démarrée et
  qui n'est pas un jalon, et la première tâche tirée démarrée dont aucune ligne n'est une provision,
  « Revue 1.2.11 », démarrée le 29 mai.
- **Aucune `completed_on` nulle** : d'un import, elle est la date de la revue que porte le fichier,
  lue dès l'analyse et jamais nulle (`ImportCompletedTask`). La date nulle n'est que d'une fusion
  non appliquée, que `structure_merge_report_started_task` montre déjà.

**Import** `…0a1b` ; **tâche de fond** 958.

### La catégorie sous une nature désactivée, et la tâche sans heure d'un déplacement et d'un collage (US-0660/L1, #1335, #1142, #779)

L'adoption par le front des refus du référentiel et de WF-PLA-0010 l'a révélé : la catégorie
désactivée en cascade (C-291) et `TASK_WITHOUT_WORKING_HOURS` hors de `createNode` et
`updateEstimateLine` n'avaient aucun exemple, et les tests du front les dérivaient à la main. Le
manque se corrige au contrat, dans l'US. Aucun schéma ne change.

- **`cost_categories_type_deactivated`** (`volume/`, `listCostCategories`, `type_deactivated`),
  engendré par `wftools.mockreference` : variante contrefactuelle déclarée, la suite de
  `cost_type_deactivated`, comme `cost_types_with_inactive` — l'univers témoin n'a aucune nature
  désactivée. Les 49 catégories des débours relues avec les désactivées, restreintes à leur nature,
  en une page de cinquante : chacune désactivée, `cost_type_is_active` faux, son compteur avancé et
  son audit nommant l'auteur de la désactivation à son instant, comme le dit
  `setCostTypeActivation` ; `reactivate` indisponible, `cost_type_active` manquante ;
  `change_cost_type` tel que sans la cascade, la nature n'y étant pour rien.
- **`nodes_move_without_hours`** (`moveNodes`, 422, `without_hours`), engendré par
  `wftools.mockrefusals` comme `node_create_without_hours` : la ligne du technicien de mise en
  service déplacée sous le « Câblage des armoires », qui porte celle de l'ingénieur, les
  calendriers supposés autres ; les deux rôles nommés, comme le Vérif de WF-PLA-0010
  (corrélation 1658).
- **Le collage refuse la ligne, non le bloc.** WF-PLA-0010 refuse « une saisie » qui laisserait
  une tâche sans heure, et `ProblemParams.tasks` nommait déjà « le motif d'une ligne collée » ;
  `PasteRejection` le dit désormais : la cellule de rôle refusée par
  `TASK_WITHOUT_WORKING_HOURS`, `params.resource_role_ids` et `params.tasks` comme pour une saisie
  — non `resource_roles`, propre au compte rendu d'un import (#768). Exemple
  `paste_plan_without_hours` (`previewPaste`, `without_hours`), engendré par
  `wftools.mockrefusals` : le bloc de `paste_plan` dont la deuxième ligne passe la ligne 29 au monteur câbleur, la tâche
  « Préparation 1.1.1 » gardant l'ingénieur ; variante contrefactuelle déclarée, `paste_id` 997.
  La confirmation redit ce refus comme tout refus de l'aperçu (`PasteApplied.rejected`) : aucun
  exemple de `applyPaste` n'est ajouté, `paste_applied_partial` montrant déjà la forme.

### Le lot sans tâche rattachée, présenté sans total (US-0660/L2, #1336, #1142)

L'adoption par le front de WF-DEV-0060 l'a révélé (#1142, point 4) : aucun exemple ne portait un
lot de `by_work_package` à total non calculable, et l'écran du devis ne pouvait montrer le lot
« présenté sans total » que sur un objet écrit à la main. Le manque se corrige au contrat, dans
l'US. Aucun schéma ne change.

- **`estimate_indicators_work_package_without_task`**, nouvel exemple de `getEstimateIndicators`
  (`work_package_without_task`), engendré par `wftools.mocktoday` : variante contrefactuelle
  déclarée, le devis de la révision courante aujourd'hui si le lotissement avait, après « Lot 1 »,
  un second lot, « Lot 2 », sans poste, qu'aucune tâche ne porte — le témoin n'a qu'un lot, que
  porte la récapitulative « Poste de commande ». Tout le reste est `estimate_indicators` ; le lot
  ajouté a son montant et sa part non calculables, motif `work_package_without_task`, plutôt que
  nuls (`mockindicators.estimate`, qui reçoit le lotissement, celui du témoin par défaut).
- **Non le projet créé aujourd'hui**, dont le lotissement par défaut n'est porté par aucune tâche :
  son devis vide a un total nul, et l'exemple n'aurait montré le lot sans total qu'à côté d'aucun
  lot calculé ; la variante montre l'un à côté de l'autre, comme l'écran les présente.

Clé `universe(718)`.

### La saisie du lotissement indisponible pendant un traitement de fond (US-0660/L2, #1336, #1142)

L'adoption par le front de la saisie du lotissement l'a révélé (#1142, point 5) : aucun exemple
de projet ne lisait `update_work_breakdown` indisponible, `no_background_task_running`
manquante — seul le 409 de `setWorkBreakdown` la nommait (`work_breakdown_background_task`) —,
et le test de l'écran construisait la liste à la main. Le manque se corrige au contrat, dans
l'US. Aucun schéma ne change.

- **`project_background_task_running`**, nouvel exemple de `getProject` (`background_task_running`),
  engendré par `wftools.mockproject` : variante contrefactuelle déclarée, le projet témoin lu
  pendant que court le marquage de sa révision en cours, celui que montre `revision_marking`. Les
  commandes que ce traitement rendrait caduques, comme `CommandCondition` les nomme — la saisie du
  lotissement, les sorties listées au témoin (`complete`, `abandon` ; `lose`, absente dès En cours,
  n'y figure pas), la déclaration d'un risque survenu et les trois imports qui écriraient dans la
  révision —, sont indisponibles, `no_background_task_running` ajoutée après leurs conditions d'état
  (`mockproject.SUSPENDED`) ; les autres, ses attributs et son compteur sont ceux de `project`, le
  marquage n'écrivant rien dans le projet.
- **Le marquage, non un import ni une survenance** : `revision_marking` et
  `work_breakdown_background_task` en montrent déjà la révision et le refus, et l'exemple les
  rejoint au même instant ; l'application d'un import suspend les mêmes commandes du projet.
- **L'exigence citée.** Aucun Vérif ne porte ce cas : celui de WF-PLA-0170 ne dit rien du
  traitement de fond, celui de WF-IHM-0090 parle de la terminaison d'un projet en chiffrage. Le
  test, `test_during_a_marking_the_commands_it_would_make_stale_name_the_task_in_the_background`
  (`tools/tests/test_mockexit.py`), cite WF-IHM-0090 par son corps, comme celui de la qualité ;
  `test_the_work_breakdown_follows_update_and_its_409_names_the_conditions_in_its_order`
  (`tools/tests/test_mockbreakdown.py`) tient la commande sous les conditions d'`update`, puis
  celle du traitement de fond dans ce seul exemple.

Aucun identifiant nouveau.

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

*Confirmée et précisée par US-0701/L2 (#1602, E-06, E-08, L-18) : WF-IHM-0110, réécrite le
2026-10-10, dit l'historique « tenu par le front » ; l'auteur l'a gardé au serveur au recadrage du
2026-10-28, et le contrat dit désormais sa session, sa pile par révision et par utilisateur, sa
fin au marquage et à l'abandon et ses cinquante niveaux ; l'annulation rend `NodesWritten`
(« Les révisions et les structures », dans « Le contrat figé »). #1595 demande la correction de la
spécification.*

## Organisation des fichiers

**Les schémas sont groupés par famille**, un fichier par famille, et non un fichier par schéma —
l'ancien contrat en avait cent quatre-vingt-un. Cent quarante-sept fichiers d'une douzaine
de lignes se relisent moins bien que quelques fichiers cohérents, et les schémas d'une même
famille se citent entre eux. Les chemins suivent la même règle, un fichier de `paths/` par
famille ; l'inventaire (`make inventory`) déclare chaque famille sous son titre, et échoue en le
nommant sur un fichier de `paths/` qu'il ne déclare pas, ou une famille sans fichier : une
famille nouvelle n'échappe plus en silence au contrôle des exigences que cite chaque opération
(#538).

**Le lotissement s'écrit d'un coup**, `PUT /projects/{id}/work-breakdown` sur l'arbre
entier, plutôt que trois familles de CRUD pour les postes, les lots et les livrables. C'est
un petit arbre saisi en une fois, jamais modifié ligne à ligne.

## Vocabulaire

Les noms du tableau de correspondance du §4.4.1 font loi, et deux d'entre eux corrigent
l'ancien contrat : `estimate_line` est une ligne de devis, `cost_line` une ligne de coût
réel. L'ancien contrat appelait `cost-lines` les lignes de devis, ce qui aurait donné deux
sens au même mot le jour où les coûts réels arrivent. De même, `org_node` pour
l'organisation, réservé face aux nœuds de l'arbre commun.

**`labor` et `LABOUR` coexistent** (C-08, US-0701/L8) : `CostTypeKind` écrit `labor` et
`non_labor`, le catalogue des erreurs `LABOUR_CATEGORY_REQUIRED`. Les deux restent : renommer l'un
ou l'autre change le client et le service sans gain de sens, comme `provision` (EP-14/L42p), et le
front rend l'un et l'autre par son catalogue.

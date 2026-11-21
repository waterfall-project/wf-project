# Revue — Spécification, première moitié fonctionnelle (`docs/spec/waterfall-spec.md`, lignes 1 à 1904)

Périmètre : chapitres 1 et 2, §3.1 (contexte, flux, langue), §3.2 (modèle conceptuel), §3.3 (cycles de
vie), §3.4.1 à §3.4.4 (arborescence, FBS-1 Administration, FBS-2 Portefeuille, FBS-3 Paramètres
applicatifs). Révision lue : 1.0.6, commit `29785cc`. Les numéros de ligne de la spécification sont
ceux du Markdown engendré ; les identifiants d'exigence servent d'ancre dans Word.

## Synthèse

Le texte de cette moitié est mûr : dix-sept passes de revue y ont laissé peu de contradictions, et
tous les exemples chiffrés que j'ai refaits sont justes (WF-PTF-0020, 0040, 0050, 0060, 0070, 0080,
0100 ; WF-REF-0100, 0160, 0170). Aucun constat bloquant.

Ce qui inquiète tient à trois endroits où la spécification et ce qui est livré ne disent plus la
même chose, sans que la spécification ait été révisée :

- un compte **sans aucun rôle** lit tout le référentiel actif (organigramme, rôles de ressources et
  leurs effectifs, calendriers, natures, catégories, matrice, seuils), par une décision du
  2026-11-01 qui contredit « sans rôle, il n'a aucune permission » (SPA-01) ;
- « action structurante » n'a pas d'extension : l'exclusion d'une ligne de coût, que la lettre de
  WF-PRJ-0060 réserve aux chefs de projet, est livrée ouverte à tout contributeur (SPA-02) ;
- deux des quatre signaux de la santé du pilotage (WF-PTF-0110, non encore réalisé) s'allument,
  tels qu'écrits, sur tout projet qui vient de faire correctement sa revue (SPA-03).

Le reste est fait de trous que le contrat ou le code ont comblés sans que la spécification le dise
(bornes, boucle de l'arbre, permission qui ouvre un projet, champ MS Project de la lignée), et de
cas que personne ne règle (compte désactivé dans l'annuaire, dernier administrateur qui ne peut pas
se connecter, rôle actif sur catégorie désactivée).

Ce qui est solide : l'évaluation des habilitations, la garde du dernier administrateur, la
révocation de session, l'anonymisation, le cycle de vie du projet et la politique de mot de passe
tiennent leur Vérif, lus de bout en bout dans le code.

## Constats bloquants

Aucun.

## Constats majeurs

### SPA-01 — Un compte sans rôle lit le référentiel actif : la décision #1745/#1746 contredit quatre exigences, et la spécification n'a pas suivi

- **Issue** : #3349 (fermée), #3960 (ouverte), #3962 (ouverte).
- **Où** : spécification — `WF-ADM-0020-A` (l. 1320 : « Toute action de Waterfall est soumise à une
  permission portée par un rôle d'habilitation »), `WF-ADM-0090-A` (l. 1332 : « sans rôle, il n'a
  aucune permission »), `WF-ADM-0070-A` (l. 1230 : « un compte ainsi créé n'a aucun droit »),
  `WF-ADM-0180-A` Vérif (l. 1256 : « elle n'a aucun droit tant qu'un rôle ne lui est pas donné »),
  `WF-ADM-0100-A` (l. 1344, deux permissions par fonction). Décision : `docs/api/DECISIONS.md:10448-10476`.
  Livré : `backend/src/waterfall/api/org_nodes.py:48-50`, `resource_roles.py:74-76` (la réponse
  porte `capacity.headcount` et `monthly_hours`, l. 159-162), `calendars.py:73-75`,
  `cost_types.py:66`, `reference_settings.py:39` (matrice de risques, seuils, délai entre revues,
  nom de l'entreprise), `reference.py:24` ; `Requires()` sans permission (`api/evaluation.py:49-64`) ;
  aucune condition de rôle à l'ouverture de session (`api/authentication.py:124-146`).
- **Quoi** : toute session ouverte, y compris celle d'un compte qui ne porte aucun rôle, lit les
  objets actifs des cinq listes du référentiel et les paramètres communs ; `resource_settings.read`,
  `risk_settings.read` et `indicator_settings.read` ne gardent plus rien dans l'API (« ouvrent la
  présentation des écrans », `docs/api/components/schemas/access.yaml`, `PermissionCode`).
- **Scénario** : une entreprise relaie son fournisseur d'identité (WF-ADM-0180). Une personne
  quelconque de l'entreprise se connecte : son compte est créé sans rôle (`core/users/provider.py`,
  `admit`). Elle appelle `GET /reference/org-nodes`, `/reference/resource-roles`,
  `/reference/settings` et obtient l'organigramme, l'effectif de chaque poste, les calendriers, le
  plan des catégories de coût et la politique de risques. La Vérif de WF-ADM-0180, close « entière »
  par EP-03, dit qu'elle n'a aucun droit.
- **Vérifié** : la décision est consignée et voulue (les formulaires des projets doivent nommer ce
  qu'ils citent) ; les taux horaires restent sous `cost_settings.read` (`hourly_rates.py:56-57`).
  Ce n'est donc pas un oubli du code, c'est une entorse décidée que la spécification contredit —
  d'où majeur et non bloquant.
- **Proposition** : trancher dans Word, puis aligner. Soit la spécification adopte la décision —
  WF-ADM-0100 : « Les objets actifs du référentiel, vocabulaire des projets, se lisent par tout
  compte qui porte au moins une permission ; la permission de consulter FBS-3.x ouvre les écrans du
  référentiel et, pour FBS-3.1, la grille des taux et la correspondance » — et le service exige
  alors au moins une permission (un `Requires` « non vide ») ; soit la lecture repasse sous les
  permissions de consultation, que le rôle « chef de projet » porte déjà. Test : un compte sans
  rôle reçoit 404 sur les cinq listes et sur `/reference/settings`.
- **Confiance** : confirmé (routes, dépendance et admission lues ; aucun test lancé).

### SPA-02 — « Action structurante » n'est définie nulle part : l'exclusion d'une ligne de coût est livrée ouverte aux participants

- **Issue** : #3350 (fermée), #3973 (ouverte).
- **Où** : `WF-ADM-0110-A` (l. 1356 : « pour une action structurante ou le paramétrage du projet,
  s'il y est chef de projet »), `WF-PRJ-0060-A` (l. 2169 : « Les actions structurantes du catalogue
  (WF-ADM-0100) … sont réservé[e]s à ses chefs de projet »), `WF-ADM-0100-A` (l. 1344 : dix
  permissions distinctes « pour les actions irréversibles ou structurantes », sans dire lesquelles
  sont l'un ou l'autre). Livré : `backend/src/waterfall/api/actual_costs.py:155`
  (`RequiresProject(EXCLUDE)`, sans `manager=True`), `core/projects/commands.py:70`
  (`Rule("exclude_cost_lines", "cost_line_exclude")`, sans `manager`), alors que le marquage,
  l'abandon, la désignation et la sortie exigent la qualité (`api/revisions.py:332,361`,
  `api/lifecycle.py:169,251`). Le catalogue range huit permissions sous `irreversible` et deux
  seulement sous `structuring` — `project_create` et `all_projects_read`, qu'on ne peut réserver au
  chef de projet d'aucun projet (`migrations/versions/0005_permission_catalogue.py:58-67`).
- **Quoi** : la règle « réservé aux chefs de projet » porte sur un ensemble que le texte ne
  délimite pas. Lue à la lettre (toutes les permissions distinctes du catalogue), elle réserve
  l'exclusion ; le livré la laisse à tout contributeur qui porte `cost_line_exclude`, sans décision
  consignée (EP-09 dit seulement « sous `cost_line_exclude` et la qualité de contributeur »,
  `docs/roadmap/EP-09-couts-reels-et-reste-a-engager.md:685`). La Vérif de WF-PRJ-0060 n'éprouve
  que le marquage.
- **Scénario** : un rôle sur mesure donne `cost_line_exclude` à un contrôleur de gestion inscrit
  comme participant. Il exclut des lignes de coût réel du périmètre suivi : le coût réel, l'indice
  de coût et la projection du projet changent, sans que le chef de projet l'ait décidé — alors que
  le glossaire dit que seuls les chefs de projet « décident de ce qui engage l'affaire ».
  Même question, ouverte pour EP-08, sur la déclaration d'un risque survenu et la fusion.
- **Proposition** : WF-ADM-0100 énumère, parmi les permissions distinctes, celles qu'un projet
  réserve à ses chefs de projet (proposition : marquer, abandonner, désigner la référence,
  fusionner, déclarer une sortie, déclarer un risque survenu, exclure ou réintégrer une ligne de
  coût) et WF-PRJ-0060 y renvoie ; la Vérif gagne « un participant porteur de la permission
  d'exclure ne peut pas exclure une ligne ». Si l'auteur retient au contraire la lecture livrée,
  l'écrire, et la consigner dans `DECISIONS.md`. Test du service : `setActualCostTrackedScope` par
  un participant → 403 `NOT_PROJECT_MANAGER`.
- **Confiance** : confirmé pour les faits (texte, route, règle, catalogue) ; l'intention de
  l'auteur est la pièce non vérifiée.

### SPA-03 — Santé du pilotage : deux signaux s'allument sur tout projet qui vient de faire sa revue (non encore réalisé, EP-11)

- **Issue** : #3351 (fermée).
- **Où** : `WF-PTF-0110-A` (l. 1608) : « ceux dont des risques identifiés n'ont pas été réexaminés
  depuis leur dernière révision marquée ; ceux dont aucun coût réel n'a été importé depuis leur
  dernière révision marquée ». À rapprocher du §3.5 (l. 3199) et du glossaire « Revue périodique »
  (l. 4939) : la revue « réexamine les risques, importe les coûts réels, **puis** marque la
  révision ».
- **Quoi** : le repère « depuis la dernière révision marquée » est pris après les actes qu'il doit
  constater. À l'instant du marquage, aucun risque n'a été réexaminé et aucun coût importé
  *depuis* : les deux signaux sont vrais pour tout projet sain, et le restent jusqu'à ce que la
  revue suivante commence. La Vérif n'éprouve que le premier et le quatrième signal, et ne le
  révèle donc pas. (C-057 et C-058 ont daté le réexamen et l'import ; ils n'ont pas touché au repère.)
- **Scénario** : un chef de projet importe ses coûts le 28, réexamine ses risques le 29, marque sa
  revue le 30. Le 1er, le manager ouvre la santé du pilotage : le projet y figure deux fois.
- **Proposition** : « ceux dont un risque identifié n'a pas été réexaminé, ou dont aucun coût réel
  n'a été importé, **entre l'avant-dernière et la dernière révision marquée** — ou, à défaut
  d'avant-dernière, depuis le passage à En cours » ; compléter la Vérif : « Un projet dont la revue
  marquée ce jour a réexaminé chaque risque et importé des coûts n'apparaît pour aucun de ces deux
  signaux ; un projet dont la dernière revue n'a importé aucun coût apparaît. »
- **Confiance** : confirmé (lecture des trois passages) ; constat de texte, EP-11 non livré.

## Constats mineurs

### SPA-04 — Le code d'un projet En cours peut être effacé — déjà connu (revue du contrat du 2026-10-31, D-06 ; « reste ouvert », `docs/api/DECISIONS.md:11063` ; aucune issue ni EPIC trouvés)

- **Issue** : #3353 (fermée), #3989 (ouverte).
- **Où** : `WF-CYC-0030-A` (l. 985), `WF-PRJ-0010-A` (l. 2075 : « peut être renseigné à tout moment ») ;
  `backend/src/waterfall/core/projects/interface/projects.py:714-739` (seul l'état terminal refuse),
  `api/projects.py:77` (`NEVER_NULL` ne compte pas `code`), aucune contrainte en base
  (`core/projects/tables.py:105-121`).
- **Quoi** : la spécification ne dit pas ce que devient l'un des deux faits du passage à En cours
  quand il cesse d'être vrai ; le service accepte `{"code": null}` sur un projet En cours.
- **Scénario** : un chef de projet vide le champ ; l'état reste En cours, et l'import suivant des
  coûts réels rejette toutes ses lignes (`core/costs/extraction.py:265-281`), jusqu'à ressaisie.
- **Proposition** : WF-PRJ-0010 : « À partir de l'état En cours, le code se corrige mais ne
  s'efface plus » ; refus 409 `STATE_FORBIDS_OPERATION`, condition `project_before_in_progress` ;
  test sur `updateProject`. Je signale que la question reste sans issue ni EPIC qui la porte.
- **Confiance** : confirmé.

### SPA-05 — « La permission de consulter » un projet n'est pas nommée ; deux permissions du catalogue n'ouvrent rien

- **Issue** : #3354 (fermée), #3974 (ouverte), #3975 (ouverte).
- **Où** : `WF-ADM-0110-A` (l. 1356-1358), `WF-PRJ-0060-A` (l. 2169), `WF-ADM-0100-A` (l. 1344-1346).
  Livré : `backend/src/waterfall/api/projects.py:66` (`CONSULT = "project_settings.read"` garde
  `listProjects` et `getProject`) ; `lifecycle.write` et `project_indicators.write` ne sont lues
  par aucune route (`grep` sur `backend/src/waterfall`, hors catalogue).
- **Quoi** : (a) neuf permissions de consultation existent sous FBS-4 ; la spécification ne dit pas
  laquelle fait qu'un projet « se voit ». Le livré a retenu FBS-4.2. Un rôle composé de
  `planning.read`/`planning.write` seuls, que WF-ADM-0020 permet, ne liste ni n'ouvre aucun projet.
  (b) WF-ADM-0100 donne « modifier » à FBS-4.8 et FBS-4.9, où aucune exigence ne décrit de saisie
  (les transitions sont automatiques ou sous « déclarer une sortie », les indicateurs sont
  calculés) : l'administrateur compose des rôles avec deux cases sans effet. (c) « le refus nomme la
  condition manquante » (WF-ADM-0110) est contredit, dans la même exigence, par « le même écran
  pour un objet inexistant » : une consultation refusée ne nomme rien (404, `core/access_roles/evaluation.py:124-134`).
- **Proposition** : WF-ADM-0110 : « Un projet est consultable par qui porte la permission de
  consulter FBS-4.2 … ; chaque fonction d'un projet exige en outre sa propre permission » ; ajouter
  FBS-4.8 et FBS-4.9 aux fonctions en lecture seule de WF-ADM-0100 (ou dire ce que leur
  modification permet) ; excepter la consultation de « le refus nomme la condition ».
- **Confiance** : confirmé.

### SPA-06 — Le rôle « chef de projet » livré porte cinq permissions que WF-INTF-0010 ne nomme pas, dont la liste du portefeuille

- **Issue** : #3355 (ouverte).
- **Où** : `WF-INTF-0010-A` (l. 393-395), `WF-ADM-0010-A` (l. 1308) ;
  `backend/src/waterfall/core/access_roles/predefined.py:48-53` (`portfolio_projects.read`,
  `cost_settings.read`, `resource_settings.read`, `risk_settings.read`, `indicator_settings.read`).
- **Quoi** : « couvrent les usages » n'est pas une liste fermée ; la Vérif ne peut pas dire si le
  rôle livré est le bon. La consultation du référentiel (les taux compris) est un usage réel que
  l'exigence oublie. `portfolio_projects.read` l'est moins : le jour où EP-11 livre WF-PTF-0040,
  tout chef de projet lira le libellé, l'état, le budget et les indices de tous les projets
  (WF-PTF-0030), alors que la Vérif de WF-ADM-0110 dit qu'« un contributeur sans "consulter tous
  les projets" ne voit que ses projets ».
- **Proposition** : WF-INTF-0010 nomme la consultation du référentiel (FBS-3) parmi les usages et
  dit si le chef de projet lit la liste du portefeuille ; à défaut, retirer `portfolio_projects.read`
  du rôle amorcé. Vérif : « le rôle prédéfini porte exactement les permissions suivantes ».
- **Confiance** : confirmé pour le contenu du rôle ; l'effet sur le portefeuille est non encore
  réalisé (EP-11).

### SPA-07 — Qui est chef de projet d'un projet ne laisse aucune trace, sauvetage par un non-contributeur compris

- **Issue** : #3356 (fermée), #3988 (ouverte).
- **Où** : §3.4.2.2 (l. 1299), `WF-PRJ-0060-A` (l. 2169), `WF-SEC-0030-A` (l. 4334, liste des
  actions inscrites — hors de mes lignes, citée par WF-ADM-0190) ;
  `backend/src/waterfall/core/projects/interface/contributors.py:409-449` (aucune inscription au
  journal, ni `updated_by` du projet), `core/projects/tables.py:169-184` (`contributor` porte un
  `kind` modifiable et aucune colonne d'audit, cf. WF-DAT-0070).
- **Quoi** : la qualité de chef de projet décide de qui marque, désigne la référence et sort le
  projet ; ni la spécification ni le livré n'en gardent l'histoire. Le sauvetage — seule saisie
  ouverte à un non-contributeur — réécrit en outre la liste entière (`_replace`, l. 389-406), pas
  seulement « inscrire un chef de projet ».
- **Scénario** : le dernier chef de projet d'une affaire est désactivé ; un porteur de « modifier
  FBS-4.2 » et « consulter tous les projets » s'inscrit lui-même chef de projet, retire deux
  participants, puis marque une révision. Le journal montre le marquage ; rien ne dit qui l'a
  rendu possible.
- **Proposition** : ajouter à WF-SEC-0030 « l'inscription, le retrait et le changement de qualité
  d'un chef de projet » (au moins le sauvetage) ; borner le sauvetage à l'ajout de chefs de projet.
  Test : après un sauvetage, `listAuditEvents` présente l'inscription, et une liste qui retire un
  participant est refusée au sauveteur.
- **Confiance** : confirmé (lecture du code) ; le rattachement à WF-DAT-0070 est à confirmer par
  le relecteur de l'architecture.

### SPA-08 — Le « dernier administrateur » peut être un compte qui ne peut pas se connecter

- **Issue** : #3357 (fermée), #3358 (fermée), #3987 (ouverte).
- **Où** : `WF-ADM-0120-A` (l. 1368-1370), `WF-ADM-0140-A` (l. 1242 : un compte local créé « ne peut
  pas se connecter avant » d'avoir fixé son mot de passe, lien valable une heure) ;
  `backend/src/waterfall/core/access_roles/administrators.py:44-58` (compte actif porteur des deux
  permissions, sans autre condition).
- **Quoi** : la garde compte un compte actif qui n'a pas de mot de passe, ou dont l'annuaire ne
  veut plus (SPA-09). La Vérif dit en outre « la permission » au singulier là où le corps en exige deux.
- **Scénario** : l'administrateur crée le compte de son successeur, lui donne le rôle, puis
  désactive le sien : accepté. Le lien expire au bout d'une heure ; plus personne ne peut le
  renvoyer. C'est « l'intervention technique » que le Motif veut éviter.
- **Proposition** : « Au moins un compte actif **en mesure de se connecter** — un compte local qui
  a fixé son mot de passe, ou un compte fédéré que le fournisseur connaît — porte… » ; ou, plus
  simple, refuser à un compte de désactiver ou de dépouiller le sien quand il est le seul
  administrateur à s'être déjà connecté. Vérif à l'appui.
- **Confiance** : confirmé pour la garde ; le scénario n'a pas été joué.

### SPA-09 — La lecture des comptes ne désactive que les comptes disparus : ni un compte désactivé dans l'annuaire, ni un compte relayé par un fournisseur externe

- **Issue** : #3357 (fermée), #3358 (fermée), #3986 (ouverte).
- **Où** : `WF-ADM-0070-A` (l. 1230), `WF-ADM-0180-A` (l. 1254 : « La lecture suivante désactive ceux
  que le fournisseur ne connaît plus ») ; `backend/src/waterfall/platform/keycloak_admin.py:311-333`
  (`enabled` n'est pas lu), `worker/identity_sync.py:110-115`.
- **Quoi** : une entreprise désactive le compte d'un salarié parti, elle le supprime rarement ; et
  le fournisseur livré garde indéfiniment le compte d'une personne relayée par un fournisseur
  externe. Dans les deux cas le compte reste actif dans Waterfall : proposé comme contributeur,
  compté comme administrateur (SPA-08). Il ne peut plus s'authentifier, donc sans risque d'accès.
- **Proposition** : WF-ADM-0070 : « … désactive les comptes que le fournisseur ne connaît plus **ou
  qu'il tient pour désactivés** » ; dire, pour un fournisseur externe, que la désactivation est
  manuelle. Test : un compte fédéré `enabled: false` est désactivé à la lecture suivante.
- **Confiance** : confirmé pour le code ; plausible pour le comportement de Keycloak sur un
  annuaire (non éprouvé ici).

### SPA-10 — Un rôle de ressource actif peut reposer sur une catégorie ou un calendrier désactivés

- **Issue** : #3359 (fermée), #3985 (ouverte).
- **Où** : `WF-REF-0010-A` (l. 1634), `WF-REF-0080-A` (l. 1800), `WF-REF-0090-A` (l. 1816),
  `WF-CYC-0120-A` (l. 902) ; `backend/src/waterfall/core/cost_settings/commands.py:53-58` (la
  désactivation d'une catégorie est toujours disponible, rôles rattachés ou non).
- **Quoi** : la cascade va du nœud au rôle et de la nature à la catégorie, jamais de la catégorie
  ou du calendrier au rôle. Un rôle actif reste « proposé à la saisie » et crée des lignes neuves
  sur une catégorie que l'entreprise a désactivée — ce que la désactivation devait empêcher. Le
  référentiel minimal est de même satisfait par un rôle actif dont la catégorie ne l'est plus.
- **Proposition** : au choix de l'auteur — la désactivation d'une catégorie ou d'un calendrier que
  portent des rôles actifs est refusée en les nommant, ou le rôle cesse d'être proposé tant que
  l'un de ses rattachements est désactivé. Vérif correspondante dans WF-REF-0010.
- **Confiance** : confirmé (texte et commande) ; pas relevé par les revues passées.

### SPA-11 — L'identifiant de lignée ne voyage pas dans « le champ d'identifiant unique de MS Project »

- **Issue** : #3361 (fermée).
- **Où** : `WF-INTF-0050-A` (l. 447), `WF-INTF-0040-A` (l. 435 : « les champs personnalisés ne sont
  jamais importés ») ; `backend/src/waterfall/core/planning/msproject/model.py:101-112`,
  `reader.py:219-248` ; conception EP-06 (`docs/roadmap/EP-06-planification.md:513,531`).
- **Quoi** : l'`UID` de MS Project est un entier ; l'export écrit la lignée dans le champ
  personnalisé `Text1` (alias `Waterfall.lineage`), que l'import relit — seul champ personnalisé
  lu, contre la lettre de WF-INTF-0040. Un utilisateur dont le modèle emploie déjà `Text1` n'en est
  prévenu nulle part.
- **Proposition** : WF-INTF-0050 : « … dans un champ de texte personnalisé de la tâche, que
  Waterfall réserve à cet usage » ; WF-INTF-0040 : « les champs personnalisés, hors celui qui porte
  l'identifiant Waterfall ».
- **Confiance** : confirmé.

### SPA-12 — WF-INTF-0120 : deux règles de terminaison d'une tâche, et une incise mal placée

- **Issue** : #3362 (fermée).
- **Où** : `WF-INTF-0120-A` (l. 531 et Vérif l. 533).
- **Quoi** : « Une tâche dont toutes les lignes **du fichier** portent un reste nul est terminée »,
  puis « n'est terminée … que si … aucune de ses lignes, **celles absentes du fichier comprises**,
  ne garde de reste ». Pour une tâche de deux lignes dont une seule figure au fichier, à zéro, la
  première phrase et la Vérif terminent la tâche, la seconde non. Par ailleurs « la ligne est alors
  rejetée … et, pour une ligne de main-d'œuvre, affectée au rôle indiqué » fait affecter un rôle à
  une ligne rejetée.
- **Proposition** : supprimer la première phrase au profit de la seconde ; Vérif : « Une tâche
  démarrée dont toutes les lignes, celles absentes du fichier comprises, sont à zéro après
  l'import, et dont le fichier en met au moins une à zéro, est terminée » ; replacer l'incise
  après « portée par la tâche qu'elle désigne ».
- **Confiance** : confirmé (texte) ; l'implémentation d'EP-09 n'a pas été confrontée.

### SPA-13 — La liste des contributeurs d'un projet terminal est figée : personne ne peut plus y être admis

- **Issue** : #3363 (fermée), #3990 (ouverte).
- **Où** : `WF-CYC-0100-A` (l. 1057), `WF-CYC-0110-A` (l. 1069-1070 : « relu, pour chiffrer le
  suivant »), `WF-PRJ-0060-A` ; `core/projects/interface/contributors.py:430-431`.
- **Quoi** : « toutes ses données » en lecture seule emporte la liste des contributeurs. Celui qui
  chiffre l'affaire suivante n'était pas contributeur de la précédente : il ne la relit qu'avec
  « consulter tous les projets », qui ouvre toute l'entreprise.
- **Proposition** : dire le choix. Soit l'excepter (« l'inscription d'un participant reste
  possible sur un projet terminal »), soit l'assumer dans le Motif de WF-CYC-0110.
- **Confiance** : confirmé.

### SPA-14 — Règles de saisie du référentiel que la spécification tait et que le contrat ou le code ont fixées

- **Issue** : #3364 (fermée).
- **Où** : `WF-REF-0070-A` (l. 1788 : rien sur le déplacement d'un nœud sous l'un de ses
  descendants — refusé par le code, `core/resource_settings/interface/org_nodes.py:239,332`) ;
  `WF-REF-0110-A` (heures d'un jour : 0 à 24 selon `calendars.py:7`) ; `WF-REF-0180-A` (1 à 104
  semaines, `docs/api/components/schemas/reference.yaml:818`) ; `WF-REF-0050-A` (bornes d'un taux,
  `DECISIONS.md`, « La borne haute du taux horaire est déclarée ») ; `WF-REF-0190-A` (un même
  intitulé déclaré pour deux colonnes — refusé, `actual_cost_mapping.py:235`) ; `WF-REF-0010-A`
  (réactiver une nature ne dit rien de ses catégories).
- **Quoi** : six refus livrés qu'aucune Vérif ne peut constater, faute d'énoncé.
- **Proposition** : une phrase par exigence, reprise de ce que le contrat a décidé ; coût faible,
  et la spécification redevient la source de ces bornes.
- **Confiance** : confirmé pour les quatre premiers et le cinquième ; les bornes du taux lues dans
  le titre de la décision seulement.

### SPA-15 — Vocabulaire et traçabilité

- **Issue** : #3365 (fermée).
- **« Chef de projet »** désigne trois choses — l'acteur (§3.1.3), le rôle prédéfini (WF-ADM-0010),
  la qualité d'un contributeur (WF-PRJ-0060) — et n'a pas d'entrée au glossaire, pas plus que
  « participant ». « La projection du chef de projet » ou « sauf si le chef de projet l'a
  réestimée » (l. 837) se lisent mal quand un participant saisit le reste à engager.
  Proposition : une entrée « Chef de projet (qualité) » et « Participant ».
- **« Capacité »** : un effectif selon WF-REF-0100 (l. 1828 : « une capacité unique : son
  effectif »), des heures par mois selon le glossaire (l. 4862) et WF-PTF-0060.
- **WF-ADM-0010** (l. 1308) : « modifiables et supprimables par un administrateur » contredit
  WF-ADM-0020 ; écrire « par un utilisateur habilité ».
- **WF-INTF-0080** (l. 481-483) traite des imports MS Project et ne cite pas FBS-4.3.4 : la
  recherche des exigences d'une fonction (§3.4.1) ne la trouve pas.
- **Confiance** : confirmé.

## Points forts

- **Évaluation d'une action (WF-ADM-0110)** : une seule fonction (`core/access_roles/evaluation.py:155-180`)
  rend 404 pour l'inexistant comme pour le non-consultable, puis nomme la permission ou la qualité
  manquante ; les permissions sont relues à chaque requête (WF-ADM-0090).
- **Dernier administrateur (WF-ADM-0120)** : verrou consultatif de transaction, lecture avant et
  après l'écriture (`administrators.py:69-84`) — deux désactivations croisées ne passent pas.
- **Attribution d'un rôle** sous `access_roles.write` en plus de `users.write`
  (`api/users.py:125-134`), comme WF-ADM-0090 le demande.
- **Compte désactivé, session révoquée** : état relu à chaque requête, jeton d'avant la fermeture
  refusé (`api/authentication.py:124-160`).
- **Mot de passe (WF-ADM-0140)** : `deploy/keycloak/realm/waterfall.yaml:46-82` tient chaque valeur
  (douze caractères, ni adresse ni nom — fournisseur `not-last-name` écrit pour cela —, dix échecs,
  quinze minutes, lien d'une heure).
- **Lecture des comptes (WF-ADM-0070)** : chaque compte « disparu » est relu un à un avant d'être
  désactivé (`worker/identity_sync.py:110-115`) ; les comptes locaux et anonymisés ne sont jamais touchés.
- **Cycle de vie (WF-CYC-0030, 0060, 0090, 0100, 0130)** : passage à En cours dans la transaction
  du fait, dans les deux ordres ; sortie jugée sous le verrou, révision en cours disposée dans la
  même opération ; quatre écritures de projet sondées refusent l'état terminal.
- **Référentiel minimal (WF-CYC-0120)** : catégorie active sous nature active, une seule fonction
  pour l'accueil et la création (`cost_settings/interface/readiness.py:33-68`).
- **Exemples chiffrés** : tous justes (0,917 ; 1 050 / 50 ; 40 % ; 250 h ; 2 222 ; 303,33 et 75,83 ;
  niveaux de la matrice et zones des indices aux bornes).

## Couverture

- **Lu en entier** : `docs/spec/waterfall-spec.md` lignes 1 à 1904 ; `docs/spec/revue/PROMPT.md` ;
  les titres des constats de `docs/spec/revue/constats/2026-10-*.md` et les constats C-057, C-058.
- **Lu sur renvoi, hors de mes lignes** : WF-PRJ-0010, WF-PRJ-0060, WF-REV-0010, WF-PLA-0010,
  WF-PLA-0060, WF-CRE-0030, WF-SEC-0030, WF-DAT-0070, WF-IHM-0130, le glossaire (titres et sept entrées).
- **Sondé dans le livré** (dix-neuf exigences) : WF-ADM-0010, 0050, 0060, 0070, 0090, 0100, 0110,
  0120, 0140, 0180, 0190 ; WF-CYC-0030, 0060, 0090, 0100, 0120, 0130 ; WF-REF-0070, 0080, 0090,
  0120 ; WF-INTF-0040/0050 (champ de la lignée) ; WF-INTF-0160. Fichiers : `core/access_roles/*`,
  `core/users/provider.py`, `identity.py`, `api/authentication.py`, `api/evaluation.py`,
  `api/users.py` (en-tête et attribution), `api/projects.py`, `api/lifecycle.py`,
  `core/projects/commands.py`, `interface/lifecycle.py`, `interface/contributors.py` (écriture),
  `interface/projects.py` (`update_project`), `cost_settings/commands.py`, `readiness.py`,
  `worker/identity_sync.py` (orchestration), `deploy/keycloak/realm/waterfall.yaml` (politique),
  `docs/api/DECISIONS.md` (cinq entrées), `docs/api/components/schemas/access.yaml` (`PermissionCode`).
- **Non lu, non sondé** : la sauvegarde et la restauration (WF-ADM-0150, 0160, 0170) ; l'avatar et
  les préférences (WF-ADM-0040, 0080) ; l'écran d'état (WF-ADM-0130, EP-13) ; les imports et
  exports Excel et MS Project au-delà du champ de la lignée (WF-INTF-0040 à 0140) ; tout le front ;
  les écrans du portefeuille sur le faux back ; l'extension Java de Keycloak. Aucun test, lint ni
  typage lancé.
- **Noté sans en faire un constat** : `AuditProject.can_open` vaut toujours `False`
  (`backend/src/waterfall/api/audit.py:106-111`) ; le lien du journal vers le projet est dû par
  WF-ADM-0190, que EP-13 (non livré) clôt sans US nommée (`docs/roadmap/EP-13-exploitation.md:85`).

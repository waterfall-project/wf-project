---
id: EP-05
titre: Décrire l'entreprise que les projets emploient : organisation, ressources, calendriers, coûts
statut: prêt
depend_de: EP-16
famille: front, back
issue:
---

# EP-05 — Référentiel de l'entreprise

## Objet

Le référentiel commun (FBS-3) : l'arbre d'organisation, les rôles de ressources et leur
capacité, les calendriers, les natures et catégories de coût, les taux horaires annuels, la
matrice de risques, les seuils d'alerte des indices, le délai maximal entre deux revues et la
devise. Aucun de ces objets ne se supprime : il se désactive.

Il vient avant les projets parce qu'un projet ne se crée pas sans lui (WF-CYC-0120) : il y faut
un calendrier par défaut, une catégorie de coût et un rôle de ressource. Plusieurs de ses
exigences ne se vérifient pourtant que sur des révisions chiffrées — la désactivation et la
modification sans effet sur les projets (WF-REF-0020, WF-REF-0130) : elles s'écrivent ici et se
closent en EP-07.

## Ce qui en fait partie

- l'arbre d'organisation, sa désactivation en cascade, et le rattachement d'un compte à un
  nœud, qui n'accorde aucune permission ;
- les rôles de ressources, leurs rattachements et leur capacité ;
- les calendriers, le calendrier par défaut, et celui que crée l'installation (WF-EXP-0020) ;
- les natures et catégories de coût, les taux horaires annuels et le taux de l'année en cours ;
- la matrice de risques, les seuils d'alerte des indices, le délai maximal entre deux revues et
  la devise de l'installation ;
- le nom de l'entreprise utilisatrice, demandé par l'amorçage, gardé par la base et modifiable sous
  `cost_settings.write` (WF-EXP-0020, C-371) ;
- la correspondance de l'extraction des coûts réels (WF-REF-0190, C-374) :
  - stockée, vide à l'installation ;
  - ses intitulés comparés sans égard à la casse, aux accents ni aux espaces en bout ;
  - complète quand les quatre colonnes exigées ont un intitulé ;
  - EP-09 lit l'extraction selon elle et clôt l'exigence ;
- la désactivation à la place de la suppression, et l'affichage des objets désactivés ;
- les usages du manager sur le référentiel (WF-INTF-0020) ;
- les écrans du référentiel de la maquette, branchés sur le service ;
- la tranche du référentiel du jeu de données de référence (WF-QUA-0040, #1402) : l'univers
  témoin chargé sur une plateforme neuve par une commande du back, avec ses identifiants, par
  les interfaces du noyau (décision de l'auteur du 2026-10-28) ;
- les parcours du référentiel écrits sur le faux back, rejoués tels quels contre le service, le
  témoin chargé.

## Ce qui n'en fait pas partie

- l'emploi de ces objets par les projets : leur conservation dans une révision, l'absence
  d'effet d'une désactivation ou d'une modification sur une révision marquée — EP-07, où les
  révisions portent des montants ;
- l'application des seuils aux indices — EP-10 ; le signalement des projets en retard de
  revue — EP-11 ; le portefeuille, second usage du manager — EP-11 ;
- l'import du référentiel par fichier : aucun flux du tableau ne le prévoit (WF-INTF-0150).
- les autres tranches du jeu de données de référence — projets et révisions (EP-04), tâches
  (EP-06), lignes (EP-07), coûts (EP-09) — et les trois cents projets du §4.6.2 (EP-13) ;
- l'écriture de la langue par défaut de l'installation : aucune opération ne l'écrit, et le
  contrat la laisse à EP-03 ;
- les tables images d'une révision (`revision_role`, `revision_calendar`, `revision_category`,
  `revision_rate`, §4.4.1) — EP-04 et EP-07.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
Six exigences que le fichier disait entières ont une phrase de Vérif qui demande des lignes de
devis, un projet, un risque ou le plan de charge agrégé : elles se commencent ici et se closent
en EP-07, EP-08 ou EP-11 (décision de l'auteur du 2026-10-28, au cadrage). Chaque US cite les
exigences dont une phrase de Vérif tient dans le référentiel ; les phrases qui demandent un
projet, une révision ou une vue sont des écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-07 | US-0810 |
| `WF-CYC-0120-A` | Référentiel minimal requis pour créer un projet | début — close en EP-04 | US-0810 |
| `WF-REF-0140-A` | Devise de l'installation | début — close en EP-07 | US-0810 |
| `WF-REF-0160-A` | Matrice de risques | début — close en EP-08 | US-0810 |
| `WF-REF-0170-A` | Seuils d'alerte des indices | début — close en EP-10 | US-0810 |
| `WF-REF-0180-A` | Délai maximal entre deux revues | début — close en EP-11 | US-0810 |
| `WF-REF-0030-A` | Natures de coût | début — close en EP-07 | US-0820 |
| `WF-REF-0040-A` | Catégories de coût | début — close en EP-07 | US-0820 |
| `WF-REF-0050-A` | Taux horaires annuels | entière | US-0830 |
| `WF-REF-0060-A` | Taux de l'année en cours | entière | US-0830 |
| `WF-REF-0070-A` | Arbre d'organisation | début — close en EP-11 | US-0840 |
| `WF-ADM-0030-A` | Rattachement d'un utilisateur à l'organisation | entière | US-0840 |
| `WF-REF-0080-A` | Désactivation en cascade | entière | US-0850 |
| `WF-REF-0090-A` | Rattachements d'un rôle de ressource | entière | US-0850 |
| `WF-REF-0100-A` | Capacité d'un rôle | début — close en EP-11 | US-0850 |
| `WF-REF-0110-A` | Contenu d'un calendrier | entière | US-0860 |
| `WF-REF-0120-A` | Calendrier par défaut | entière | US-0860 |
| `WF-PLA-0160-A` | Unités de durée | début — close en EP-06 | US-0860 |
| `WF-REF-0190-A` | Correspondance de l'extraction des coûts réels | début — close en EP-09 | US-0870 |
| `WF-REF-0010-A` | Désactivation plutôt que suppression | début — close en EP-07 | US-0880 |
| `WF-REF-0150-A` | Affichage des objets désactivés | entière | US-0880 |
| `WF-REF-0020-A` | Désactivation sans effet sur les projets | début — close en EP-07 | US-0880 |
| `WF-REF-0130-A` | Modification sans effet rétroactif | début — close en EP-07 | US-0880 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13 | US-0890 |
| `WF-INTF-0020-A` | Usages du manager | début — close en EP-11 | US-0900 |
| `WF-ADM-0020-A` | Aucune action réservée à un acteur | fin — amorcée en EP-03 | US-0900 |

Les exigences du front que les écrans du référentiel tiennent déjà — WF-IHM-0060, WF-IHM-0090,
WF-IHM-0130, closes par EP-02, EP-14 et EP-15 ou commencées par eux — restent où elles sont :
leurs tests du front continuent de les citer, et les parcours rejoués contre le service ne les
contredisent pas.

## Opérations du contrat

Servies ici pour la première fois, les trente et une de `reference`, dans l'état du contrat
d'`epic/EP-16` au 2026-10-28 ; aucune n'est ajoutée ni modifiée, et la liste se relit à la fusion
d'US-0640/L6 et au gel (« Préalables ») :

- les paramètres communs et le référentiel minimal : `getReferenceReadiness`,
  `getReferenceSettings`, `updateReferenceSettings` (US-0810) ;
- les natures et les catégories : `listCostTypes`, `createCostType`, `updateCostType`,
  `setCostTypeActivation`, `listCostCategories`, `createCostCategory`, `updateCostCategory`,
  `setCostCategoryActivation` (US-0820) ;
- les taux : `getHourlyRateGrid`, `listHourlyRates`, `setHourlyRate` (US-0830) ;
- l'arbre : `listOrgNodes`, `createOrgNode`, `updateOrgNode`, `setOrgNodeActivation` (US-0840) ;
- les rôles : `listResourceRoles`, `createResourceRole`, `updateResourceRole`,
  `setResourceRoleActivation` (US-0850) ;
- les calendriers et les unités : `listCalendars`, `createCalendar`, `updateCalendar`,
  `setDefaultCalendar`, `setCalendarActivation`, `getDurationUnits`, `setDurationUnits`
  (US-0860) ;
- la correspondance : `getActualCostMapping`, `setActualCostMapping` (US-0870).

Déjà servies par EP-03, et reprises ici pour ce que cet EPIC y ajoute — le rattachement d'un
compte à un nœud (`org_node_id`, `org_node_label`) : `listUsers`, `getUser`, `updateUser`, `getMe`
(US-0840).

## Constats reçus

- #1338, pour #1304, points 1 et 3 — le service de la reprise de la spécification du 2026-10-22 (#1306, C-371 à C-375 ; #1304), dont EP-16 écrit le contrat, le faux back et les écrans (décision de l'auteur du 2026-10-22, au cadrage d'EP-16) :
  le nom de l'entreprise à l'amorçage et dans les paramètres communs, et la correspondance de
  l'extraction des coûts réels, stockée avec ses règles.
- #351 — un chiffreur sans permission du référentiel ne peut saisir ni catégorie ni rôle :
  la garde de `include_inactive` sur les lectures du référentiel, reportée d'EP-03 par son
  cadrage (2026-10-07).
- #299 — ajouter une année à la grille des taux horaires (WF-REF-0060) : la commande appartient
  au référentiel réel, reportée d'EP-02 (2026-10-07). Rangé le 2026-10-08 dans EP-02/L41 (#506),
  qui fait la part de la maquette (L41b) : la grille offre, à qui peut saisir les taux, d'ajouter
  la colonne d'une année qu'elle n'a pas, vide, refusée pour une année déjà présente ou hors des
  bornes de `Year`. Le contrat n'a aucune opération pour créer une colonne — une année entre dans
  la grille par le premier taux qu'on y saisit (`getHourlyRateGrid`) — : la colonne est celle du
  front jusqu'à ce premier taux, écrit par `setHourlyRate` sans version. Reste à EP-05 la part
  du service : refuser un second taux pour la même année (WF-REF-0050) et rendre l'année dans
  `years` dès son premier taux, que le parcours éprouvera contre le service réel. Le refus d'une
  colonne déjà présente reste au front, faute d'opération qui crée une colonne.
- #300 — les écrans du référentiel ne montrent ni ne réactivent les objets désactivés
  (WF-REF-0150), reportée d'EP-02 (2026-10-07). Rangé le 2026-10-08 dans EP-02/L41 (#506),
  qui fait la part de la maquette (L41b) : les paramètres de coûts et de ressources lisent les
  objets actifs seuls, et les désactivés aussi quand l'adresse le demande (`include_inactive`), à
  une session qui porte la permission de lecture de leur partie du référentiel ; un objet
  désactivé s'y réactive par la commande d'activation de sa nature, pour qui peut modifier
  cette partie. Le faux back ignorant `include_inactive` et ne gardant rien, la maquette
  n'éprouve que ce que l'écran demande. Reste à EP-05 la part du service : ne rendre les
  désactivés qu'avec `include_inactive`, refuser celui-ci sans la permission (403), et appliquer
  la réactivation, que le parcours éprouvera contre le service réel.
- #512 — les commandes d'écriture du référentiel dans la maquette, sur décision de l'auteur du
  2026-10-08 (EP-02/L43), une entorse assumée au cadrage qui laissait les formulaires à cet EPIC.
  EP-02/L43a fait les paramètres de coûts : créer et modifier une nature ou une catégorie dans un
  formulaire validé côté front, désactiver et réactiver comme l'objet le liste, saisir un taux dans
  la grille ; un succès remplace la ligne par ce que le serveur rend, un refus se dit au champ ou
  sous le formulaire, et l'écran dit que le faux back ne garde rien (`MockupNotice`). Restent à
  EP-05 : le back de ces écritures ; la conformité de leurs réponses au contrat, refus compris — code
  déjà pris, code comptable déjà pris, type d'une nature dont une catégorie est employée, nature
  absente, inconnue ou désactivée, version périmée —, que les « Interface contract issue » relevées
  par L43a précisent d'abord ; les parcours contre le service, une création qui apparaît dans la
  liste relue ; et le retrait de l'avis de la maquette, l'écran branché sur le service.
  EP-02/L43b fait de même les paramètres de ressources : créer et modifier un nœud — le déplacer
  sous un parent actif —, un rôle — sans changer de nœud — et un calendrier, désactiver et réactiver
  chacun comme il le liste, désigner le calendrier par défaut. Restent à EP-05 : le back de ces
  écritures, la cascade d'une désactivation (WF-REF-0080) comprise ; la conformité de leurs réponses
  au contrat, refus compris — code déjà pris, parent ou nœud désactivé, nœud déplacé sous lui-même ou
  ses descendants, catégorie hors main-d'œuvre ou rattachement désactivé d'un rôle (WF-REF-0090),
  heures hors bornes, version périmée —, que les « Interface contract issue » relevées par L43b
  précisent d'abord ; les parcours contre le service ; et le retrait de l'avis de la maquette.
- La saisie du rattachement d'un compte dans sa cellule de l'écran des comptes — une liste
  déroulante des nœuds de l'organigramme, écrite par `updateUser` ; la colonne « Rattachement »
  reste aujourd'hui en lecture seule (#379, renvoyé par US-0360 : « reste en lecture… jusqu'à
  EP-05 »).
- #1402 — cadrage : le jeu de données de référence part de l'univers témoin, chargé par
  tranches (relevé avec l'auteur le 2026-10-23, à trancher au cadrage d'EP-05) : tranché le
  2026-10-28 — WF-QUA-0040 démarre ici, le chargeur est une commande du back, les mêmes parcours
  jouent dans les deux modes, les dates sont celles du chargement (US-0890, « Conception »).

## Préalables

EP-03 livré : chaque écriture du référentiel est évaluée contre une permission. EP-16 livré : le
contrat que cet EPIC sert est figé en 1.0.0 (décision de l'auteur du 2026-10-22, au cadrage
d'EP-16). Le cadrage du 2026-10-28 s'est fait sur le contrat d'`epic/EP-16` avant le gel :
US-0640/L6 (#1457, les constats de contrat relevés par les lots d'EP-15) et US-0640/L5 (#1333, le
gel) touchent encore le contrat, sans qu'aucune issue ouverte ne porte sur le référentiel. À
leur fusion, la liste des opérations, les refus que les US nomment et les exemples que les tests
lisent se relisent ; un écart devient une « Interface contract issue » que l'auteur tranche, le
contrat figé ne se modifiant plus qu'ainsi.

## Définition de fini

- chaque objet du référentiel se crée, se modifie et se désactive depuis son écran, contre le
  service, et aucune commande ne le supprime ;
- la désactivation d'un nœud d'organisation se propage comme WF-REF-0080 le fixe ;
- un objet désactivé reste affiché là où il est employé et n'est plus proposé à la saisie ;
- un compte rattaché à un nœud n'y gagne aucun accès ;
- une installation neuve, amorcée par `waterfall-api install`, porte le calendrier par défaut, la
  nature et la catégorie de provision, les réglages livrés, la devise et le nom de l'entreprise
  de son environnement, et `getReferenceReadiness` y nomme la catégorie de main-d'œuvre et le
  rôle manquants ;
- les exemples chiffrés des Vérif du §3.4.4 sont des tests qui passent (WF-QUA-0020) ;
- la tranche du référentiel de l'univers témoin se charge sur une plateforme neuve par la commande
  du back, avec les identifiants du témoin, et deux chargements donnent les mêmes identifiants ;
- les parcours du référentiel (`frontend/e2e/reference.spec.ts` et les lectures du référentiel des
  autres fichiers) passent sans réécriture de leurs attendus de lecture contre le service, le
  témoin chargé, dans `make e2e-service`, comme contre le faux back dans `make e2e` ;
- les cinq écrans du référentiel ne portent plus l'avis de la maquette ;
- `make check` passe sur la branche de l'EPIC, les tests du back citent leurs exigences, et aucun
  fichier de `docs/api` ne change hors d'une « Interface contract issue » tranchée.

## Conception

EP-05 est le premier EPIC de domaine du back : il crée les tables du régime « référentiel » du
§4.4.1, quatre modules du noyau, les routes des trente et une opérations de `reference`, complète
l'amorçage, écrit la commande qui charge le témoin, et branche sur le service des écrans déjà
écrits. Il **ne modifie pas le contrat**, figé en 1.0.0 : un manque que le service ou le
branchement révèle devient une « Interface contract issue » que l'auteur tranche. Ce qui suit fixe
ce que chaque lot devrait sinon décider seul. Validée par l'auteur le 2026-10-28.

### Ce que le cadrage décide

Décisions de l'auteur du 2026-10-28, sur les questions du cadrage, chacune avec l'option écartée :

- **WF-QUA-0040 démarre ici** (#1402), par la tranche du référentiel de l'univers témoin ; le
  principe est écrit une fois dans le README de la roadmap. Écarté : EP-04, où il serait né sans
  référentiel et d'un second générateur.
- **Le chargeur est une commande du back**, `waterfall-api load-witness`, au sommet des couches
  comme l'amorçage : elle lit la description du témoin et écrit par les interfaces des modules,
  avec les identifiants du témoin. Écartés : un outil de `tools/` qui appellerait l'API, qui ne
  peut imposer aucun identifiant ; des `INSERT`, qui passeraient à côté des règles ; un outil qui
  produirait un fichier de chargement que le back lirait, deux pièces à tenir d'accord.
- **Un identifiant s'impose par un paramètre des interfaces** (`identifier: UUID | None`), que
  seule la commande passe ; l'API n'en passe jamais, et un identifiant déjà porté échoue.
  Écartée : une table de correspondance entre identifiants du témoin et identifiants engendrés,
  qui ferait relire chaque attendu des tests.
- **Les dates et les auteurs des objets chargés sont ceux du chargement** : la plateforme,
  `created_at` au moment du chargement (WF-DAT-0070). Écarté : imposer un `Stamp` du témoin, qui
  tirerait ses comptes dans la tranche ; l'horloge du témoin se pose à EP-04.
- **Les mêmes fichiers de parcours jouent dans les deux modes**, par une fixture commune.
  Écarté : des parcours du service à part, comme EP-03, qui recopieraient les repères.
- **Les assertions qui affirmaient la réponse du faux back à une écriture affirment ce qui a été
  écrit** ; contre le faux back, l'assertion se borne à ce que les deux modes partagent. Écarté :
  laisser les écritures au faux back et écrire chaque écriture à part.
- **L'amorçage lit `WATERFALL_CURRENCY` et `WATERFALL_COMPANY_NAME`** de l'environnement, comme
  l'adresse et la langue. Écarté : des arguments de la commande, deux façons de passer un réglage.
- **Quatre modules, un par bloc FBS de second niveau** — `cost_settings`, `resource_settings`,
  `risk_settings`, `indicator_settings` —, la table `reference_setting` possédée par
  `cost_settings`, qui expose sa lecture et son écriture champ par champ aux deux autres.
  Écartés : un seul module `reference`, qui déroge à la règle du guide ; deux modules, qui
  laissent FBS-3.3 et FBS-3.4 sans module.
- **Six exigences dites entières se closent en EP-07, EP-08 et EP-11** (WF-REF-0010, 0030, 0040 ;
  0160 ; 0070, 0100) : une phrase de leur Vérif demande des lignes, un risque ou le plan de
  charge agrégé. Écarté : les garder entières avec des écarts sans EPIC qui les clôt.
- **Aucune inscription au journal d'audit pour le référentiel** : WF-SEC-0030 n'énumère ni la
  désactivation ni la modification d'un objet du référentiel, et `AuditAction` du contrat, figé,
  ne les porte pas ; les colonnes d'audit de chaque table disent qui a touché la ligne en dernier.
  Écartée : une action nouvelle, qui serait une modification du contrat et irait au-delà de la
  spécification. (Le critère qu'US-0880 portait à ce sujet au premier jet est retiré.)
- **`include_inactive` et `is_active` faux relèvent de la permission de lecture de la partie**
  (`cost_settings.read`, `resource_settings.read`), les écritures de sa permission de
  modification (DECISIONS.md, « Le référentiel » ; #300, #351). Écarté : la permission de
  modification pour les désactivés, qui priverait un lecteur du référentiel de ce que WF-REF-0150
  lui promet.
- **US-0810 crée toutes les tables en une fois**, pour que chaque US d'objet n'ait que son module,
  ses routes et ses tests à écrire. Écarté : une migration par US, qui ferait six fois la revue
  des droits du rôle du service.
- **Le cadrage s'est fait sur le contrat d'`epic/EP-16` avant le gel** ; la liste des opérations
  et des refus se relit à la fusion d'US-0640/L6 et L5 (« Préalables »). Écarté : attendre le
  gel, qui aurait retardé EP-05 de plusieurs jours pour un contrat que nulle issue ouverte ne
  touche dans le référentiel.

### Tables et migrations

Toutes du régime « référentiel » (§4.4.1) : jamais supprimées, désactivées par `is_active` ;
UUID v7 engendrés par le service, ou imposés par le chargeur ; colonnes d'audit `created_at`,
`created_by`, `updated_at`, `updated_by` (clé vers `user_account`, nulle pour la plateforme) et
`lock_version` sur chaque table dont les lignes se modifient ; les textes triés en collation `C`,
cherchés par `contains` (`unaccent`, `und-x-icu`) ; les règles SQL du guide pour le reste. Les
codes et les libellés sont bornés comme le contrat les borne (20 et 200), jamais blancs
(`\S`), par contrainte.

| Table | Contenu | Contraintes |
|---|---|---|
| `reference_setting` | une seule ligne : `currency_code`, `company_name`, les trois bornes de probabilité et les trois de gravité (`numeric`, en fraction comme le contrat les écrit), les seize zones de la matrice (`risk_zones`, un tableau de seize valeurs d'`AlertZone`), les quatre seuils des indices (`numeric`), `max_weeks_between_reviews`, audit, `lock_version` | une seule ligne (`id = 1`) ; `currency_code` sur `^[A-Z]{3}$` ; `company_name` de 1 à 200, non blanc ; bornes strictement croissantes sur chaque axe ; seuils dans ]0, 1[ et chaque alerte < sa vigilance ; délai de 1 à 104 ; seize zones parmi les valeurs d'`AlertZone` ; écrite par l'amorçage, modifiée par le service (`SELECT`, `UPDATE`) |
| `duration_unit` | une seule ligne : `hours_per_day`, `hours_per_week`, `days_per_month` (`numeric`), audit, `lock_version` propre (`DurationUnits.lock_version`) | une seule ligne ; chaque constante strictement positive ; 8, 40, 20 à l'amorçage |
| `cost_type` | `code`, `label`, `kind`, `is_active`, audit, `lock_version` | `code` unique, désactivées comprises ; `kind` dans `labor`, `non_labor`, `provision` |
| `cost_category` | `code`, `label`, `accounting_code`, `cost_type_id`, `is_active`, audit, `lock_version` | `code` et `accounting_code` uniques, désactivées comprises ; clé vers `cost_type` en refus |
| `hourly_rate` | `cost_category_id`, `year`, `amount` (`numeric(12,2)`), audit, `lock_version` | unique sur (`cost_category_id`, `year`) ; `amount >= 0.01` ; `year` dans les bornes de `Year` du contrat ; clé vers `cost_category` en refus |
| `org_node` | `code`, `label`, `parent_id`, `is_active`, audit, `lock_version` | `code` unique, désactivés compris ; `parent_id` clé vers `org_node`, nulle pour une racine, en refus ; `parent_id <> id` ; l'absence de boucle est tenue par le service, sous verrou |
| `calendar` | `label`, `monday` … `sunday` (`numeric(4,2)`), `is_default`, `is_active`, audit, `lock_version` | `label` unique, désactivés compris ; chaque jour de 0 à 24 ; un seul `is_default` (index unique partiel) ; `is_default` implique `is_active` |
| `resource_role` | `code`, `label`, `org_node_id`, `cost_category_id`, `calendar_id`, `monthly_hours`, `headcount` (`numeric`), `is_active`, audit, `lock_version` | `code` unique, désactivés compris ; trois clés en refus, non nulles ; `monthly_hours >= 0`, `headcount >= 0` |
| `actual_cost_mapping` | une seule ligne : audit, `lock_version` | une seule ligne, vide à l'amorçage, version 1 |
| `actual_cost_mapping_label` | un intitulé de la correspondance : `kind` (`read`, `kept`), `column` (une valeur d'`ActualCostSourceColumn`, nulle pour une colonne conservée), `position`, `label`, `folded` (l'intitulé sans casse, sans accents, sans espaces en bout) | `folded` unique sur toute la table — la règle des doublons de WF-REF-0190 — ; `column` non nul si `kind = read` et nul sinon ; `label` de 1 à 200, non blanc ; au plus 20 par colonne lue et 50 conservées, tenus par le service |
| `user_account` | `org_node_id` ajouté | clé vers `org_node` en refus, nulle sans rattachement (WF-DAT-0090 ; EP-03, « Tables et migrations ») |

- **Deux migrations** : `0015_reference_tables`, les dix tables et les droits du rôle du service
  (`SELECT`, `INSERT`, `UPDATE` ; jamais `DELETE`, sauf sur `actual_cost_mapping_label`, que
  l'écriture entière de la correspondance remplace ligne à ligne — une table qui ne porte qu'un
  intitulé, comme une association) ; `0016_user_account_org_node`, la colonne et sa clé.
  Aucune migration de données : les permissions du référentiel sont au catalogue depuis EP-03,
  et les lignes uniques sont écrites par l'amorçage, jamais par une migration (guide,
  « Migrations »).
- **Les clés étrangères refusent** (`ON DELETE RESTRICT`) : aucune cascade, le référentiel ne
  supprime rien.
- Les tests : `test_migrations.py` (schéma, droits, `SERVICE_RIGHTS`), un test par contrainte
  dans `test_database_constraints.py`, chacun citant son exigence.

### Modules

| Module | Tables | Interface offerte |
|---|---|---|
| `waterfall.core.cost_settings` (FBS-3.1) | `cost_type`, `cost_category`, `hourly_rate`, `reference_setting`, `actual_cost_mapping`, `actual_cost_mapping_label` | les paramètres communs lus entiers et écrits champ par champ, chaque champ sous sa permission, avec le compteur commun ; les natures, les catégories et les taux — lecture, listes, création, modification, activation — ; le libellé et le type de nature d'une catégorie (`category_label`, pour un rôle) ; `labour_categories_exist()`, `provision_category_active()` (le référentiel minimal) ; `category_is_employed(id)`, toujours faux ici, qu'EP-07 remplit ; la correspondance lue et remplacée, et sa forme repliée (`folded`) pour EP-09 |
| `waterfall.core.resource_settings` (FBS-3.2) | `org_node`, `resource_role`, `calendar`, `duration_unit` | l'arbre, les rôles, les calendriers et les unités — lecture, listes, création, modification, déplacement, activation, désignation par défaut — ; `node_label(id)` (pour un compte), `node_is_active(id)` (le rattachement d'un compte) ; `default_calendar_has_hours()`, `active_role_exists()` (le référentiel minimal) ; les calendriers des rôles pour EP-06 ; `calendar_change_is_admissible(...)`, toujours vrai ici, qu'EP-06 remplit (`TASK_WITHOUT_WORKING_HOURS`) |
| `waterfall.core.risk_settings` (FBS-3.3) | aucune | la matrice lue et écrite, par `cost_settings` ; la zone d'un couple (probabilité, gravité) pour EP-08 |
| `waterfall.core.indicator_settings` (FBS-3.4) | aucune | les seuils et le délai lus et écrits, par `cost_settings` ; la zone d'un indice pour EP-10 |

- Les deux derniers modules n'ont pas de table : ils portent les règles de leur bloc — l'ordre
  des bornes, l'ordre des seuils — et lisent la ligne par l'interface de `cost_settings`. Le
  contrat d'import-linter les ajoute.
- **Le référentiel minimal** (`getReferenceReadiness`) se compose dans la route, des quatre
  questions que les deux premiers modules exposent, dans l'ordre de l'énumération.
- **`users` reçoit le rattachement** : `change_account` écrit `org_node_id` après avoir demandé à
  `resource_settings` si le nœud existe et est actif (422 sinon), et `read_account` nomme le nœud
  par `node_label`. L'évaluation d'une action (`access_roles`) ne lit jamais le rattachement
  (WF-ADM-0030).
- **Les commandes d'un objet** (`available_commands`) se calculent dans le module, à partir des
  permissions de l'acteur et de l'état de l'objet et de ses voisins — la nature d'une catégorie,
  le nœud d'un rôle, le calendrier par défaut —, par les mêmes fonctions que les refus 409 : une
  commande dite indisponible et l'appel refusé disent la même condition.
- **Les listes** suivent `api/queries.py` (EP-03) : recherche par `contains`, filtres, tri par
  colonne avec l'ordre de rupture du contrat (l'ordre sans tri, puis l'identifiant), pages
  `limit`/`offset` et `meta.total` ; l'arbre des nœuds se lit entier, en profondeur, et ses
  filtres rendent les ancêtres ; la grille des taux se construit en deux lectures, les années de
  toute la grille puis la page des catégories.
- **Les verrous** : une cascade (désactivation d'un nœud, d'une nature), une réactivation, un
  déplacement de nœud et la désignation du calendrier par défaut prennent un verrou consultatif
  de transaction, un par règle — l'arbre, les natures, les calendriers — avant de lire ; une
  modification teste son `lock_version` dans l'écriture même (règles SQL, « Verrous »).

### Le service d'API

- Un routeur par module — `api/cost_settings.py`, `api/resource_settings.py`,
  `api/risk_settings.py`, `api/indicator_settings.py` — et `api/reference.py` pour le référentiel
  minimal, enregistrés dans `app.py` ; les modèles Pydantic du contrat existent déjà
  (`api/contract/models.py`, engendrés).
- Chaque route déclare ses permissions par `Requires(...)` comme le contrat les dit ; une lecture
  qui demande `include_inactive` ou `is_active` faux ajoute la permission de lecture de la partie
  par une dépendance qui lit la requête ; une écriture des paramètres communs juge la permission
  de chaque champ porté avant d'écrire quoi que ce soit (403 au premier champ refusé) ;
  `test_access_evaluation.py` reçoit chaque opération.
- Les refus sont ceux que le contrat nomme, code par code (`ALREADY_EXISTS` avec
  `conflicting_object_id` et, pour un nœud ou un rôle, `conflicting_object_label` ;
  `STATE_FORBIDS_OPERATION` avec `missing_condition` ; `VALIDATION_FAILED` et ses codes de
  champ ; `LABOUR_CATEGORY_REQUIRED` sans `fields` sur un taux ; `DUPLICATE_COLUMN_LABEL` avec
  `duplicate_of`) ; chaque réponse d'un test passe par `ContractClient`.
- `TASK_WITHOUT_WORKING_HOURS` (un calendrier ou un rôle qui laisserait une tâche sans heure) et
  `cost_type_unused`, `cost_category_unused` (une catégorie employée) sont prévus par les
  interfaces et ne surviennent jamais en EP-05 : EP-06 et EP-07 les remplissent sans toucher les
  routes.

### L'amorçage

`waterfall-api install` (EP-03, « Amorçage ») ajoute à son étape 3, dans la même transaction que
l'installation, et sous le même verrou :

- `InstallationSettings` reçoit `currency` (`WATERFALL_CURRENCY`, trois lettres majuscules) et
  `company_name` (`WATERFALL_COMPANY_NAME`, 1 à 200 caractères, jamais blanc), exigées ; un
  réglage absent ou mal formé arrête la commande en le nommant (WF-SEC-0010), avant tout appel ;
- la ligne `reference_setting` : la devise et le nom, les bornes 25 %, 50 %, 75 % et 1 %, 5 %,
  10 %, les seize zones livrées (celles de l'exemple `reference_settings` du contrat), les seuils
  0,9 et 0,8 pour chaque indice, six semaines ; la ligne `duration_unit` à 8, 40, 20 ; la ligne
  `actual_cost_mapping`, vide ;
- le calendrier par défaut, actif, huit heures du lundi au vendredi, zéro le week-end ; la nature
  de type provision pour risques et sa catégorie, avec un code et un code comptable livrés — les
  libellés de ces trois objets dans la langue par défaut, modifiables ensuite comme tout
  libellé ;
- relancée, elle ne crée rien de tout cela et dit ignorés une autre devise ou un autre nom
  (`installation.currency_ignored`, `installation.company_name_ignored`), comme l'adresse.

Le Compose de service (`install`), `make service-install`, le Compose de production et
`production.env.example` passent les deux variables ; la famille `service` de `tools/paths.toml`
les lit déjà par le Compose. Le libellé livré de chaque objet et les codes de la provision se
fixent au lot, dans les deux langues, à côté des libellés des rôles prédéfinis.

### Le chargeur du témoin

- **La commande** : `waterfall-api load-witness`, troisième verbe du point d'entrée après
  `install`, dans un module `waterfall.witness` au sommet des couches, importé par aucun ; elle
  lit `WATERFALL_DATABASE_URL` du rôle du service (elle n'écrit que par les interfaces) et
  `WATERFALL_WITNESS_PATH`, le répertoire de la description du témoin.
- **Ce qu'elle lit** : les fichiers de `fixtures/api/` que `make mock-data` tient —
  `reference_settings.json`, `duration_units.json`, `cost_types.json`,
  `volume/cost_categories.json`, `volume/hourly_rate_grid.json`, `calendars.json`,
  `org_nodes_with_inactive.json`, `resource_roles.json` (désactivés compris),
  `actual_cost_mapping.json` —, validés par les modèles du contrat (`api/contract/models.py`) : le
  témoin est lu dans la forme du contrat, et un fichier qui s'en écarte arrête la commande. Elle ne
  recopie rien dans le paquet.
- **Ce qu'elle écrit, dans l'ordre des dépendances** : les paramètres communs (la matrice, les
  seuils, le délai du témoin, sous la permission de la plateforme ; la devise et le nom restent
  ceux de l'amorçage), les unités, les natures, les catégories, les taux, les calendriers et le
  calendrier par défaut du témoin, les nœuds — chacun sous son parent, puis la désactivation de
  ceux que le témoin dit désactivés, en cascade —, les rôles, puis la désactivation des rôles
  désactivés, la correspondance. La nature et la catégorie de provision de l'amorçage restent ;
  celles du témoin s'ajoutent.
- **L'identifiant imposé** passe aux interfaces ; une collision — le témoin déjà chargé, ou un
  objet qui porte l'identifiant — arrête la commande en le disant, rien n'étant écrit : une seule
  transaction, sous un verrou consultatif propre. Une seconde exécution sur une plateforme
  chargée s'arrête avant d'écrire, avec succès, en disant que le témoin est là.
- **Dans le Compose de service**, un service `witness` sur le modèle d'`install` (profil
  `witness`, le répertoire `../../fixtures/api` monté en lecture seule), `make service-witness`
  pour la main, et `make e2e-service` le lance après `install` ; le Compose de production ne
  l'offre pas : une installation réelle ne porte pas le témoin.
- **Dans la chaîne**, la famille `service` lit `fixtures/**` en plus (`tools/paths.toml`).
- Ce que le guide écrit : la commande, ses variables, ce qu'elle charge et dans quel ordre, et
  que `fixtures/api/` et Prism restent les exemples du contrat et le faux back des écrans que le
  service ne sert pas.

### Le front

- **L'avis de la maquette** (`MockupNotice`) est retiré des cinq pages de `app/reference/` ; les
  commentaires d'en-tête de ces pages et des composants de `components/reference/` qui le
  nomment sont réécrits : un succès est ce que le service a gardé, relu.
- **Le rattachement d'un compte** : `admin/user-cells.tsx` rend la colonne « Rattachement » en
  cellule saisissable, une liste déroulante des nœuds actifs lus par `listOrgNodes` (sous
  `resource_settings.read` ; sans elle, la colonne reste en lecture), écrite par `updateUser`
  avec `org_node_id` et le compteur lu, comme les autres cellules de la table (#379) ; un nœud
  désactivé auquel un compte reste rattaché se montre par `org_node_label` et n'est pas proposé.
  La table se filtre sur le rattachement (`org_node_id`, que le contrat prévoit). Le catalogue
  reçoit l'infobulle de la commande.
- **Les aides** `frontend/help/fr/FBS-3*.md` retirent ce qu'elles disaient du faux back.
- Rien d'autre : les écrans sont ceux d'EP-02/L43, d'EP-14 et d'EP-15.

### Le harnais

- **Une fixture commune**, `frontend/e2e/mode.ts`, exporte `test` (le `test` de Playwright
  étendu) et `inService` : hors du service, rien ne change — le faux back accorde la session — ;
  avec `WATERFALL_API_ADDRESS`, un `beforeEach` connecte, par `signIn` de `service/realm.ts`, un
  compte de la course qui porte « manager », créé par l'administrateur de l'installation
  (`accountAdministrator`), un par worker, et `heldToTheContract()` s'applique. Les parcours
  partagés importent `test` de `./mode` et non de `@playwright/test`.
- **Un projet Playwright `shared`** en mode service, après `installation` : `testMatch` sur la
  liste des parcours partagés (`SHARED_PATHS` : `reference.spec.ts`, `admin.spec.ts`,
  `navigation.spec.ts`), que le projet `chromium` continue de jouer contre le faux back ; la
  liste grandit avec chaque EPIC qui branche un écran.
- **Les assertions d'écriture** : le taux saisi est affirmé par `inService` ; contre le faux
  back, la cellule répondue, non occupée et le focus passé. Les lectures sont inchangées : le
  témoin chargé rend les mêmes libellés, codes, comptes et ordres que les exemples.
- **Ce qui ne se rejoue pas**, écrit dans le guide (« Un parcours de bout en bout ») : les dates
  d'audit, les parcours des écrans que le service ne sert pas.
- `make e2e-service` charge le témoin (ci-dessus) ; `make e2e` ne change pas.

### Les tests du back

- Un fichier par module et par objet (`test_cost_settings_types.py`, `…_categories.py`,
  `…_rates.py`, `test_resource_settings_nodes.py`, `…_roles.py`, `…_calendars.py`,
  `test_reference_settings.py`, `test_actual_cost_mapping.py`, `test_reference_readiness.py`,
  `test_witness.py`, `test_bootstrap_reference.py`), chaque test citant son exigence, chaque
  réponse validée contre le contrat ; les exemples chiffrés des Vérif — 25/50/75, 1/5/10, 0,9/0,8,
  six semaines, huit heures — sont des tests sans base quand ils le peuvent (`tests/examples`).
- Les tests des listes lisent les exemples du contrat comme oracle : le témoin chargé dans une
  base de test par la commande, les réponses du service comparées aux fixtures que le faux back
  sert (`cost_types.json`, `org_nodes_with_inactive.json`, `hourly_rate_grid_by_rate.json`…),
  aux colonnes d'audit près — c'est le principe du jeu de données : le calculé devient l'attendu.
- Un test de concurrence par règle d'ensemble : la cascade, le calendrier par défaut, le code
  unique sous deux créations.

### L'ordre de construction

1. **US-0810** : les tables et les migrations, les quatre modules à vide, les paramètres communs
   et le référentiel minimal, l'amorçage complété ; les parcours du service existants passent
   toujours.
2. **US-0820, US-0860, US-0840**, dans cet ordre : les natures et catégories, les calendriers et
   unités, l'arbre — ce dont un rôle a besoin — ; US-0830 (les taux) après US-0820, en parallèle
   des deux autres.
3. **US-0850** : les rôles et la cascade, qui demandent les trois.
4. **US-0870** : la correspondance, indépendante, à tout moment après US-0810.
5. **US-0890** : la commande du témoin, le service `witness`, puis la fixture, le projet
   `shared` et les parcours rejoués — dès qu'US-0830, US-0850 et US-0870 sont fusionnées.
6. **US-0880** : la désactivation transverse, après US-0890 (décision de l'auteur du 2026-10-28,
   au plan de lots) : son dernier critère joue les désactivés contre le service, par la fixture
   qu'US-0890 écrit.
7. **US-0900** en dernier : l'avis retiré, le parcours du manager, le rôle sur mesure.

---

## US-0810 — Le socle du référentiel : tables, modules, amorçage et paramètres communs

- **statut** : à faire
- **exigences** : `WF-EXP-0020-A`, `WF-CYC-0120-A`, `WF-REF-0140-A`, `WF-REF-0160-A`,
  `WF-REF-0170-A`, `WF-REF-0180-A`
- **opérations** : `getReferenceReadiness`, `getReferenceSettings`, `updateReferenceSettings`
- **issue** :

**En tant que** manager, **je veux** qu'une installation neuve porte dès son amorçage le
calendrier par défaut, la nature et la catégorie de provision, la devise, le nom de l'entreprise
et les réglages livrés, et régler ensuite la matrice de risques, les seuils d'alerte, le délai
entre deux revues et le nom de l'entreprise, chacun sous sa permission, **afin que** le
référentiel existe avant tout projet et dise ce qui lui manque encore.

**Critères d'acceptation.**

- `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %, 50 % et
  75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines, et le
  calendrier par défaut compte huit heures du lundi au vendredi et aucune le week-end. » :
  `waterfall-api install` les écrit, avec la nature de type provision pour risques et sa
  catégorie, leurs libellés dans la langue par défaut, la devise de `WATERFALL_CURRENCY` et le nom
  de l'entreprise de `WATERFALL_COMPANY_NAME` (décision de l'auteur du 2026-10-28) ;
- `WF-EXP-0020-A` — « Une seconde exécution de l'installation ne crée ni compte, ni calendrier, ni
  nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent, tant que
  l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » : pour le calendrier,
  la nature, la catégorie et les réglages, qu'une seconde exécution laisse tels qu'ils sont, une
  autre devise ou un autre nom dits ignorés ; le compte et le lien, constatés par EP-03 ;
- écart : `WF-EXP-0020-A` — « Le nom de l'entreprise saisi à l'installation figure sur un devis
  exporté ; modifié, il figure sur le suivant. » : saisi à l'installation, gardé par
  `reference_setting`, lu et modifié par `ReferenceSettings` sous `cost_settings.write` ; le devis
  exporté est d'EP-07, qui clôt l'exigence ;
- écart : `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le
  lien produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles
  prédéfinis et le catalogue des permissions. » : constaté par EP-03 (US-0420), livré ;
- écart : `WF-EXP-0020-A` — « La création d'un projet est refusée et nomme les prérequis manquants,
  jusqu'à ce qu'une catégorie de coût de main-d'œuvre et un rôle de ressource aient été saisis. » :
  la création d'un projet est d'EP-04, le devis exporté d'EP-07, qui clôt ; ici,
  `getReferenceReadiness` les nomme
  (ci-dessous) ;
- écart : `WF-EXP-0020-A` — « Le lien produit à l'installation est accepté plus d'une heure après
  sa production. » : constaté par EP-03 (US-0420) ;
- `WF-CYC-0120-A` — « Sur une installation neuve, dont la seule catégorie est celle des provisions
  pour risques, la création est refusée en nommant la catégorie de main-d'œuvre et le rôle
  manquants. » : `getReferenceReadiness` rend `is_complete` faux et `missing` à
  `active_cost_category` puis `active_resource_role`, dans l'ordre de l'énumération ; le refus de
  la création est d'EP-04 ;
- `WF-CYC-0120-A` — « Sur un référentiel dont aucune catégorie de type provision pour risques n'est
  active, la création est refusée en nommant ce prérequis. » : `missing` porte
  `active_provision_category` dès que la dernière catégorie active de ce type est désactivée ;
- écart : `WF-CYC-0120-A` — « Sur une plateforme dont le référentiel est incomplet, la création
  d'un projet est refusée, et le refus nomme chaque prérequis manquant. » : le refus est d'EP-04,
  qui clôt ; `missing` nomme ici chaque prérequis, `default_calendar_with_hours` compris quand le
  calendrier par défaut n'a aucune heure dans la semaine ;
- écart : `WF-CYC-0120-A` — « La création aboutit dès que tous les prérequis sont satisfaits. » :
  EP-04 ; ici, `is_complete` passe vrai dès la catégorie de main-d'œuvre et le rôle créés ;
- écart : `WF-CYC-0120-A` — « L'énoncé des prérequis manquants à l'accueil relève de
  WF-IHM-0120. » : l'accueil, EP-04 ;
- `WF-REF-0140-A` — « La devise apparaît partout où un montant est affiché ou exporté, et aucun
  écran ne propose d'en changer ni d'en saisir une seconde. » : la devise est celle de
  l'amorçage, `currency_code` de `ReferenceSettings`, que rien n'écrit — ni
  `updateReferenceSettings`, qui ne la porte pas, ni aucun écran — ; les montants affichés et
  exportés sont d'EP-07, qui clôt ;
- `WF-REF-0160-A` — « Les six bornes sont saisissables et ordonnées. » : `updateReferenceSettings`
  sous `risk_settings.write` ; une borne qui n'est pas strictement supérieure à la précédente est
  refusée par 422, `BOUNDS_NOT_ORDERED` au rang qui rompt l'ordre, et rien n'est écrit ;
- écart : `WF-REF-0160-A` — « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité
  60 est au troisième niveau sur un projet de budget 1 000 (6 %) et au deuxième sur un projet de
  budget 2 000 (3 %). » : le classement d'un risque est d'EP-08, qui clôt ;
- écart : `WF-REF-0160-A` — « Sur un projet en chiffrage, un risque est classé d'après le total
  hors provisions de son devis courant ; la désignation de la révision de référence ne change pas
  son niveau si ce total égale le budget de référence. » : EP-08 ;
- écart : `WF-REF-0160-A` — « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité
  50 sur un projet de budget 1 000 est au troisième niveau. » : EP-08 ;
- `WF-REF-0170-A` — « Les quatre seuils sont saisissables, et le seuil d'alerte de chaque indice
  est inférieur à son seuil de vigilance. » : sous `indicator_settings.write` ; un seuil d'alerte
  qui n'est pas strictement inférieur à son seuil de vigilance est refusé par 422,
  `THRESHOLD_NOT_BELOW_WATCH`, un seuil hors de ]0, 1[ par `THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE`,
  la forme jugée avant la plage ;
- écart : `WF-REF-0170-A` — « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à
  0,5, avec des seuils fixés à 0,9 et 0,8. » : les indices sont d'EP-10, qui clôt ;
- écart : `WF-REF-0170-A` — « Avec des seuils à 0,9 et 0,8, un indice de 0,9 est nominal et un
  indice de 0,8 en vigilance. » : EP-10 ;
- `WF-REF-0180-A` — « Le délai est saisissable en semaines. » : sous `indicator_settings.write`,
  de 1 à 104, un délai hors de ces bornes refusé par 422, `VALUE_OUT_OF_RANGE` ;
- écart : `WF-REF-0180-A` — « Un projet dont la dernière révision marquée date de plus que ce délai
  est signalé ; il ne l'est plus après un marquage. » : la santé du pilotage, EP-11, qui clôt ;
- propre à l'US : les tables du régime « référentiel » du §4.4.1 — `org_node`, `resource_role`,
  `calendar`, `cost_type`, `cost_category`, `hourly_rate`, `reference_setting`, et celle de la
  correspondance — existent par des migrations écrites à la main, chacune compatible avec le
  code voisin, leurs contraintes déclarées et éprouvées, les droits du rôle du service accordés ;
  `user_account.org_node_id` reçoit sa clé étrangère vers `org_node` (WF-DAT-0090) ;
- propre à l'US : les quatre modules du noyau — `cost_settings`, `resource_settings`,
  `risk_settings`, `indicator_settings` (FBS-3.1 à FBS-3.4) — existent avec leur interface, et
  `make imports-back` les tient ;
- propre à l'US : un champ de `ReferenceSettingsWrite` dont la session ne porte pas la permission
  est refusé par 403, `PERMISSION_MISSING` nommant `cost_settings.write`, `risk_settings.write`
  ou `indicator_settings.write`, même si la requête en porte un autre qu'elle pourrait écrire,
  et rien n'est écrit ; un `lock_version` périmé par 412, commun à tous les paramètres ; un nom
  de l'entreprise vide ou blanc par 422 (`VALUE_REQUIRED`, `VALIDATION_FAILED`), trop long par
  `VALUE_TOO_LONG` ;
- propre à l'US : chaque réponse des trois opérations est validée contre le contrat dans les
  tests du service, et la route de chacune déclare ses permissions (`test_access_evaluation.py`).

**Notes de réalisation.** L'amorçage ajoute à l'étape 3 de `waterfall-api install` (EP-03,
« Amorçage ») ce que WF-EXP-0020 lui demande du référentiel ; `WATERFALL_CURRENCY` (trois lettres
majuscules) et `WATERFALL_COMPANY_NAME` (1 à 200 caractères, jamais blanc) sont exigées à
l'amorçage comme `WATERFALL_ADMIN_EMAIL`, et le Compose de service, `make service-install` et le
Compose de production les passent. La langue par défaut reste dans `installation`, lue par
`ReferenceSettings.default_language` (décision d'EP-03). Les tables se créent ici en une fois pour
que chaque US suivante n'ait que son module à écrire ; la conception fixe colonnes et contraintes.

**Hors périmètre.** La création d'un projet (EP-04) ; le classement d'un risque (EP-08) ; les
indices (EP-10) ; la santé du pilotage (EP-11).

---

## US-0820 — Les natures et les catégories de coût

- **statut** : à faire
- **exigences** : `WF-REF-0030-A`, `WF-REF-0040-A`
- **opérations** : `listCostTypes`, `createCostType`, `updateCostType`, `setCostTypeActivation`,
  `listCostCategories`, `createCostCategory`, `updateCostCategory`, `setCostCategoryActivation`
- **issue** :

**En tant que** manager, **je veux** décrire les natures de coût et leurs catégories, avec leurs
codes, et changer le type d'une nature ou la nature d'une catégorie tant que rien ne s'y oppose,
**afin que** chaque dépense d'un devis se ventile et se nomme comme la comptabilité la reconnaît.

**Critères d'acceptation.**

- `WF-REF-0030-A` — « Une nature de chacun des trois types peut être créée. »
- `WF-REF-0030-A` — « La création d'une nature dont le code existe déjà est refusée. » : 409,
  `ALREADY_EXISTS` sur `/code`, parmi les natures actives ou désactivées, `conflicting_object_id`
  la nature qui le porte ;
- `WF-REF-0030-A` — « La modification du type est refusée pour une nature dont une catégorie est
  employée, porte un taux ou est rattachée à un rôle de ressource. » : pour un taux
  (`cost_type_unrated`) et un rôle (`cost_type_without_role`), 409 `STATE_FORBIDS_OPERATION`,
  `params.cost_categories` ou `params.resource_roles` nommant les objets en cause, la commande
  `change_kind` le disant d'avance ; une catégorie employée par une ligne (`cost_type_unused`) est
  d'EP-07, qui clôt — ici, aucune ligne n'existe, et la condition ne manque jamais ;
- `WF-REF-0030-A` — « Sur une installation neuve, la nature de type provision pour risques et sa
  catégorie existent. » : constaté par US-0810 ; `listCostTypes` et `listCostCategories` les
  rendent après l'amorçage ;
- écart : `WF-REF-0030-A` — « Une fois saisis la catégorie de main-d'œuvre et le rôle de ressource
  qu'exige WF-CYC-0120, un projet se crée, et la déclaration d'un risque y aboutit sans
  qu'aucune catégorie de provision ait été saisie. » : le projet est d'EP-04, le risque d'EP-08 ;
  EP-07 constate la clôture ;
- `WF-REF-0030-A` — « La désactivation de la dernière catégorie active de type provision pour
  risques est acceptée ; la création d'un projet (WF-CYC-0120), la déclaration d'un risque et le
  retour d'un risque écarté à l'état identifié (WF-RIS-0010) sont alors refusés. » : acceptée,
  et `getReferenceReadiness` nomme alors `active_provision_category` ; les refus du projet et du
  risque sont d'EP-04 et d'EP-08 ;
- `WF-REF-0040-A` — « La création d'une catégorie sans nature est refusée. » : 422,
  `VALUE_REQUIRED` sur `/cost_type_id` ; une nature inconnue par `UNKNOWN_COST_TYPE`, désactivée par
  `INACTIVE_REFERENCE_OBJECT` ;
- `WF-REF-0040-A` — « La création d'une catégorie dont le code comptable existe déjà est
  refusée. » : 409, `ALREADY_EXISTS` sur `/accounting_code`, comme sur `/code`, parmi les
  catégories actives ou désactivées ;
- `WF-REF-0040-A` — « La création d'une catégorie sans libellé est refusée. » : 422,
  `VALUE_REQUIRED` sur `/label` ;
- `WF-REF-0040-A` — « Le rattachement d'une catégorie employée à une nature d'un autre type est
  refusé, de même que celui d'une catégorie qui porte un taux, ou à laquelle un rôle de ressource
  est rattaché, à une nature hors main-d'œuvre ; le rattachement d'une catégorie inemployée, sans
  taux ni rôle, à une nature d'un autre type est accepté. » : pour le taux
  (`cost_category_unrated`) et le rôle (`cost_category_without_role`), 409
  `STATE_FORBIDS_OPERATION`, la commande `change_cost_type` le disant d'avance ; vers une nature du
  même type, toujours accepté ; une catégorie employée (`cost_category_unused`) est d'EP-07, qui
  clôt ;
- propre à l'US : les listes se trient, se cherchent, se filtrent et se paginent par le serveur
  comme leurs opérations le disent — la recherche sur le code et le libellé, et le code
  comptable pour les catégories ; `kinds`, `cost_type_id`, `is_active` ; les désactivées après les
  actives —, et `meta.total` compte ce qui est retenu ; les catégories actives se lisent sans la
  permission du référentiel, `include_inactive` et `is_active` faux sont refusés par 403 sans
  `cost_settings.read` ;
- propre à l'US : « Désactiver une nature de coût désactive ses catégories » : chaque catégorie
  active de la nature est désactivée avec elle, son compteur avance, son audit nomme l'auteur ;
  la réactivation ne rend active que la nature, et celle d'une catégorie sous une nature
  désactivée est refusée par 409, `cost_type_active` manquante, `conflicting_object_id` la nature ;
- propre à l'US : chaque réponse — les listes, les 201, les refus 403, 409, 412 et 422 — est
  validée contre le contrat dans les tests du service, sur les exemples que le contrat donne
  (`cost_type_code_taken`, `cost_category_kind_refused`, `cost_category_reactivation_refused`…).

**Notes de réalisation.** Les refus que le contrat nomme viennent des « Interface contract issue »
d'EP-02/L43a (#512) : le service les rend tels quels. Une catégorie « employée » ne l'est jamais
en EP-05 — aucune ligne de devis n'existe avant EP-07 — : `cost_type_unused` et
`cost_category_unused` sont prévus par l'interface (une fonction qui dit si une catégorie est
employée, toujours fausse ici, qu'EP-07 remplit) et ne manquent jamais.

**Hors périmètre.** Les lignes de devis qui emploient une catégorie (EP-07) ; les taux
(US-0830) ; les rôles (US-0850).

---

## US-0830 — Les taux horaires annuels

- **statut** : à faire
- **exigences** : `WF-REF-0050-A`, `WF-REF-0060-A`
- **opérations** : `getHourlyRateGrid`, `listHourlyRates`, `setHourlyRate`
- **issue** :

**En tant que** manager, **je veux** saisir, année par année, le taux horaire de chaque catégorie
de main-d'œuvre, et ouvrir la colonne d'une année nouvelle quand je connais ses taux, **afin que**
tout chiffrage parte d'un taux constaté.

**Critères d'acceptation.**

- `WF-REF-0050-A` — « La saisie d'un second taux pour une même catégorie et une même année est
  refusée. » : une première saisie, sans `lock_version`, pour une année qui porte déjà un taux est
  refusée par 409, `ALREADY_EXISTS`, rien n'étant écrit ; le taux se relit et se corrige avec sa
  version, un compteur périmé refusé par 412 ;
- `WF-REF-0050-A` — « Aucun taux ne peut être saisi pour une catégorie hors main-d'œuvre. » : 422,
  `LABOUR_CATEGORY_REQUIRED`, sans `fields` ; un montant nul ou négatif par `VALUE_OUT_OF_RANGE`,
  `minimum` à `0.01` ;
- `WF-REF-0060-A` — « L'ajout d'une colonne pour une année déjà présente est refusé. » : par la
  grille du front, faute d'opération qui crée une colonne (#299) — la colonne est celle du front
  jusqu'au premier taux —, contre le service comme contre le faux back ;
- `WF-REF-0060-A` — « Une colonne ajoutée est vide, et les taux des années précédentes sont
  inchangés. » : le premier taux saisi dans la colonne fait entrer l'année dans `years` de
  `getHourlyRateGrid`, à la relecture ; les autres cellules de l'année sont nulles, et les taux
  des autres années ceux d'avant ;
- propre à l'US : la grille rend une ligne par catégorie de main-d'œuvre, active — désactivée
  aussi avec `include_inactive`, sous `cost_settings.read`, refusé par 403 sans elle —, les
  années de toute la grille quels que soient la page, la recherche (`search` sur le code et le
  libellé), les bornes (`rate_year`, `rate_min`, `rate_max`) et le tri (`rate.<année>`, les
  catégories sans taux après les autres dans l'ordre croissant) ; `listHourlyRates` rend les taux
  d'une catégorie ;
- propre à l'US : le premier taux d'une catégorie rend indisponibles `change_cost_type` de la
  catégorie (`cost_category_unrated`) et `change_kind` de sa nature (`cost_type_unrated`), relus
  dans leurs listes ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et le
  parcours `reference.spec.ts` saisit un taux contre le service, qui répond ce qui a été saisi.

**Notes de réalisation.** `hourly_rate` est à la catégorie et à l'année, unique sur les deux
(`numeric` pour le montant, jamais un flottant — règles SQL). La grille du témoin, cent cinquante
catégories sur quinze ans, est chargée par US-0890 : les tests de la grille se jouent dessus.

**Hors périmètre.** L'emploi du taux par un montant (EP-07) ; l'inflation (EP-07).

---

## US-0840 — L'arbre d'organisation et le rattachement d'un compte

- **statut** : à faire
- **exigences** : `WF-REF-0070-A`, `WF-ADM-0030-A`
- **opérations** : `listOrgNodes`, `createOrgNode`, `updateOrgNode`, `setOrgNodeActivation` ;
  `listUsers`, `getUser`, `updateUser`, `getMe` (le rattachement)
- **issue** :

**En tant que** manager, **je veux** dessiner l'organigramme de l'entreprise sans limite de
profondeur, déplacer un nœud avec tout ce qu'il porte, et, administrateur, rattacher un compte à un
nœud, **afin de** classer les rôles par service et situer chaque personne, sans qu'un rattachement
donne un droit.

**Critères d'acceptation.**

- `WF-REF-0070-A` — « Un arbre de six niveaux peut être créé. » : `level` va de 1 à 6, résolu à la
  lecture ; `listOrgNodes` rend l'arbre en profondeur, les enfants d'un même parent triés par
  libellé dans l'ordre des points de code, sans page ni tri ;
- `WF-REF-0070-A` — « La création d'un nœud dont le code existe déjà est refusée. » : 409,
  `ALREADY_EXISTS` sur `/code`, parmi les nœuds actifs ou désactivés, `conflicting_object_id` et
  `conflicting_object_label` ;
- `WF-REF-0070-A` — « Le déplacement d'un nœud sous un autre emporte ses descendants et ses rôles ;
  le plan de charge agrégé filtré sur le nœud d'arrivée inclut désormais ces rôles, et les valeurs
  par rôle sont inchangées. » : le déplacement (`updateOrgNode`, `parent_id`) emporte les
  descendants, dont `level` suit, et les rôles, que `listResourceRoles?org_node_id=<arrivée>` rend
  désormais ; un nœud ne se déplace ni sous lui-même ni sous un descendant (422,
  `ORG_NODE_CYCLE`) ; le plan de charge agrégé est d'EP-11, qui clôt ;
- `WF-REF-0070-A` — « Le déplacement sous un nœud désactivé est refusé. » : 422,
  `INACTIVE_REFERENCE_OBJECT` sur `/parent_id`, jugé sur le parent envoyé quand il change ; un
  parent inconnu par `UNKNOWN_ORG_NODE`, absent par `VALUE_REQUIRED` (`null` est la racine) ; un
  seul motif, inconnu, puis boucle, puis désactivé ;
- `WF-ADM-0030-A` — « Un utilisateur rattaché à un nœud ne dispose d'aucun accès supplémentaire. » :
  les permissions effectives d'un compte rattaché sont celles de ses rôles, et une action refusée
  avant le rattachement l'est encore après ;
- `WF-ADM-0030-A` — « Le retrait du rattachement ne modifie aucune habilitation. » :
  `updateUser` avec `org_node_id` nul laisse les permissions effectives telles quelles ;
- propre à l'US : `updateUser` écrit `org_node_id` — un nœud inconnu ou désactivé refusé par 422
  comme à la création d'un rôle —, et `listUsers`, `getUser` et `getMe` rendent `org_node_id` et
  `org_node_label`, résolu à la lecture, actif ou désactivé ; la table des comptes se filtre sur le
  rattachement ;
- propre à l'US : la colonne « Rattachement » de l'écran des comptes se saisit dans sa cellule,
  par une liste déroulante des nœuds actifs de l'organigramme, pour qui porte `users.write`
  (#379) ; un nœud désactivé auquel un compte reste rattaché s'y affiche par son libellé ;
- propre à l'US : `listOrgNodes` cherche sur le libellé et le code, se filtre par `code`, `level`,
  `level_min`, `level_max` et `is_active`, et rend les nœuds retenus avec leurs ancêtres ; les
  désactivés ne sont rendus qu'avec `include_inactive`, sous `resource_settings.read`, refusé par
  403 sans elle ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** `org_node.parent_id` est une clé étrangère vers `org_node`, nulle pour
une racine ; la profondeur se résout à la lecture (une requête récursive, ou le chemin calculé
par le noyau), jamais stockée. L'évaluation d'une action (`waterfall.core.access_roles`) ne lit
pas le rattachement : c'est ce que le test de WF-ADM-0030 constate. La cascade d'une
désactivation est d'US-0850, qui a les rôles.

**Hors périmètre.** Les rôles rattachés (US-0850) ; la cascade (US-0850) ; le plan de charge
agrégé (EP-11).

---

## US-0850 — Les rôles de ressources, leur capacité et la désactivation en cascade

- **statut** : à faire
- **exigences** : `WF-REF-0090-A`, `WF-REF-0100-A`, `WF-REF-0080-A`
- **opérations** : `listResourceRoles`, `createResourceRole`, `updateResourceRole`,
  `setResourceRoleActivation` ; `setOrgNodeActivation` (la cascade)
- **issue** :

**En tant que** manager, **je veux** décrire chaque poste par un rôle — son nœud, sa catégorie de
main-d'œuvre, son calendrier, sa capacité — et fermer un service d'un geste, **afin que** le plan
de charge confronte la charge des projets à ce que l'entreprise peut fournir.

**Critères d'acceptation.**

- `WF-REF-0090-A` — « La création d'un rôle auquel manque l'un des trois rattachements est
  refusée, de même que son rattachement à une catégorie hors main-d'œuvre ou à un objet
  désactivé. » : 422, `VALUE_REQUIRED` sur `/org_node_id`, `/cost_category_id` ou `/calendar_id` ;
  `LABOUR_CATEGORY_REQUIRED` pour une catégorie hors main-d'œuvre ; `INACTIVE_REFERENCE_OBJECT`
  pour un rattachement désactivé ; `UNKNOWN_ORG_NODE`, `UNKNOWN_COST_CATEGORY`,
  `UNKNOWN_CALENDAR` pour un inconnu ; un champ ne porte qu'un motif ;
- `WF-REF-0090-A` — « La création d'un rôle dont le code existe déjà est refusée. » : 409,
  `ALREADY_EXISTS` sur `/code`, parmi les rôles actifs ou désactivés ;
- `WF-REF-0090-A` — « La modification du nœud d'un rôle existant est refusée ; celle de sa
  catégorie, vers une catégorie de main-d'œuvre active, est acceptée. » : `ResourceRoleUpdate` ne
  porte pas de nœud, et un rôle relu après toute modification garde celui de sa création ; la
  catégorie et le calendrier se modifient vers des objets actifs, refusés comme à la création, un
  rôle qui garde les siens, désactivés depuis, se modifiant ;
- `WF-REF-0100-A` — « Un rôle ne porte qu'une capacité, sans date de validité. » : `capacity`,
  heures par mois et effectif, jamais négatifs (422, `VALUE_OUT_OF_RANGE`, `minimum` à `0`), une
  seule par rôle, sans date ;
- écart : `WF-REF-0100-A` — « Le plan de charge agrégé compare la charge mensuelle de chaque rôle
  à son nombre d'heures. » : le plan de charge agrégé est d'EP-11, qui clôt ;
- `WF-REF-0080-A` — « La désactivation d'un nœud portant deux niveaux de descendants et des rôles
  les désactive tous. » : `setOrgNodeActivation` désactive les descendants et les rôles rattachés
  à lui ou à l'un d'eux, chacun son compteur avancé et son audit nommant l'auteur, dans la même
  transaction ; la réponse ne les porte pas, les listes relues les montrent ;
- `WF-REF-0080-A` — « La réactivation d'un rôle dont le nœud est désactivé est refusée. » : 409,
  `STATE_FORBIDS_OPERATION`, `org_node_active` manquante, `conflicting_object_id` le nœud, la
  commande `reactivate` du rôle le disant d'avance ; de même la réactivation d'un nœud dont le
  parent est désactivé, `org_node_parent_active` ; une réactivation ne rend actif que l'objet ;
- propre à l'US : les rôles actifs se lisent sans la permission du référentiel (WF-DEV-0020) ;
  les désactivés (`include_inactive`, `is_active` faux) et toute écriture sous
  `resource_settings` ; la liste cherche sur le libellé et le code, se filtre par `code`,
  `org_node_id` (le nœud et ses descendants), `cost_category_id`, `calendar_id`, `is_active`, se
  borne sur `monthly_hours` et `headcount`, se trie par chaque colonne, et `meta.total` compte ;
- propre à l'US : la création ou le changement de catégorie d'un rôle rend indisponibles
  `change_cost_type` de la catégorie (`cost_category_without_role`) et `change_kind` de sa nature
  (`cost_type_without_role`), relus dans leurs listes ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Le refus `TASK_WITHOUT_WORKING_HOURS` d'`updateResourceRole` — un
calendrier qui laisserait une tâche sans heure (WF-PLA-0010) — est d'EP-06, qui a les tâches :
l'interface du module prévoit la question, toujours sans objet ici. La cascade et la réactivation
se font sous un verrou consultatif par arbre (règles SQL, « Verrous »), pour que deux
désactivations croisées ne laissent pas un rôle actif sous un nœud fermé.

**Hors périmètre.** Les lignes de devis d'un rôle (EP-07) ; `TASK_WITHOUT_WORKING_HOURS` (EP-06).

---

## US-0860 — Les calendriers, le calendrier par défaut et les unités de durée

- **statut** : à faire
- **exigences** : `WF-REF-0110-A`, `WF-REF-0120-A`, `WF-PLA-0160-A`
- **opérations** : `listCalendars`, `createCalendar`, `updateCalendar`, `setDefaultCalendar`,
  `setCalendarActivation`, `getDurationUnits`, `setDurationUnits`
- **issue** :

**En tant que** manager, **je veux** décrire le rythme de travail de chaque poste par sept
nombres d'heures, désigner le calendrier qui vaut par défaut, et régler les constantes qui
convertissent jours, semaines et mois en heures, **afin que** le planning sache quand on
travaille.

**Critères d'acceptation.**

- `WF-REF-0110-A` — « Un calendrier se saisit par un libellé et sept valeurs d'heures, du lundi au
  dimanche, et aucune autre donnée n'est demandée ; deux calendriers de même libellé sont
  refusés. » : `CalendarWrite` ne porte que `label` et `weekly_hours`, chaque jour de 0 à 24
  (422, `VALUE_OUT_OF_RANGE`) ; un libellé déjà porté, actif ou désactivé, refusé par 409,
  `ALREADY_EXISTS` sur `/label` ;
- `WF-REF-0120-A` — « Désigner un calendrier par défaut retire cette désignation au précédent. » :
  `setDefaultCalendar`, le compteur du précédent avancé ; un calendrier désactivé ne se désigne
  pas (409, `calendar_active` manquante) ; désigner celui qui l'est déjà répond 200 sans rien
  changer, la version contrôlée d'abord ;
- `WF-REF-0120-A` — « La désactivation du calendrier par défaut est refusée tant qu'un autre n'a
  pas été désigné. » : 409, `STATE_FORBIDS_OPERATION`, `calendar_not_default` manquante, la
  commande `deactivate` le disant d'avance ;
- `WF-PLA-0160-A` — « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans une
  révision en cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision
  marquée, elle vaut toujours seize heures. » : `setDurationUnits` écrit les trois constantes,
  strictement positives (422, `DURATION_UNIT_NOT_POSITIVE`), avec leur compteur (412), sous
  `resource_settings.write`, et `getDurationUnits` les rend à quiconque consulte un projet, 8, 40
  et 20 à l'installation ; le recalcul des durées et des dates est d'EP-06, qui clôt ;
- écart : `WF-PLA-0160-A` — « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize
  heures, « 1 sem » quarante heures et « 1 m » cent soixante heures. » : constaté par EP-15 dans la
  maquette ; EP-06 clôt ;
- écart : `WF-PLA-0160-A` — « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer
  d'unité. » : EP-06 ;
- écart : `WF-PLA-0160-A` — « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur
  finit à la dernière heure travaillée d'un vendredi s'achève le dimanche ; le successeur, sur un
  calendrier du lundi au vendredi, commence le lundi à la première heure travaillée, de même
  qu'avec un décalage de 2 eh. » : EP-06 ;
- écart : `WF-PLA-0160-A` — « Un décalage de 2 j sur la même liaison le fait commencer le
  mercredi. » : EP-06 ;
- écart : `WF-PLA-0160-A` — « Un fichier MS Project dont les constantes diffèrent de celles de
  l'installation est importé avec les mêmes durées en heures, et le compte rendu signale la
  différence. » : EP-06 ;
- écart : `WF-PLA-0160-A` — « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans
  chacune des langues de l'interface. » : constaté par EP-15 (US-0470) ; EP-06 clôt ;
- écart : `WF-PLA-0160-A` — « En anglais, « 1 j » et « 1 d » valent chacun un jour ; « 3 », saisi
  sans suffixe, vaut trois jours. » : constaté par EP-15 (US-0470) ; EP-06 clôt ;
- propre à l'US : `listCalendars` cherche sur le libellé, filtre l'état, trie chaque colonne, les
  heures de chaque jour et leur somme comprises, le calendrier par défaut en tête par
  `is_default`, et ne filtre pas les heures (C-352) ; les désactivés avec `include_inactive`,
  sous `resource_settings.read` ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Les refus `TASK_WITHOUT_WORKING_HOURS` d'`updateCalendar` et de
`setDefaultCalendar` — un calendrier qui laisserait une tâche sans heure (WF-PLA-0010) — sont
d'EP-06 : l'interface prévoit la question, sans objet ici. Un seul calendrier par défaut : une
contrainte de la base (un index unique partiel sur `is_default`), et la désignation sous un
verrou. Les unités de durée sont trois colonnes de `reference_setting`, ou une ligne à part, au
choix de la conception, avec leur propre compteur (`DurationUnits.lock_version`).

**Hors périmètre.** Le calendrier applicable à une tâche (EP-06) ; les jours chômés d'un Gantt.

---

## US-0870 — La correspondance de l'extraction des coûts réels

- **statut** : à faire
- **exigences** : `WF-REF-0190-A`
- **opérations** : `getActualCostMapping`, `setActualCostMapping`
- **issue** :

**En tant que** manager, **je veux** déclarer sous quels intitulés l'extraction de l'ERP nomme
les colonnes que l'import des coûts réels lit, et quelles colonnes il conserve, **afin que**
l'import lise l'extraction telle qu'elle sort, sans qu'on renomme ses colonnes à chaque revue
(#1338).

**Critères d'acceptation.**

- `WF-REF-0190-A` — « Sur une installation neuve, l'import d'un fichier de coûts réels est refusé
  et nomme la correspondance à régler. » : la correspondance naît vide à l'installation, à la
  version 1, `is_complete` faux et `missing_columns` les quatre colonnes exigées dans l'ordre de
  l'énumération ; le refus de l'import est d'EP-09, qui clôt ;
- `WF-REF-0190-A` — « Après déclaration de « Elément d'OTP », « Nº pièce référence », « Date de la
  pièce » et « Val./Devise objet », une extraction dont l'en-tête est « Élément d'OTP »
  s'importe. » : la déclaration s'enregistre entière, avec son compteur, sous
  `cost_settings.write` ; les intitulés se comparent sans égard à la casse, aux accents ni aux
  espaces en bout, et un intitulé qui en double un autre ainsi comparé — « élément d'otp  » après
  « Élément d'OTP », d'une même colonne, de deux colonnes lues, ou d'une lue et d'une conservée —
  est refusé par 422, `DUPLICATE_COLUMN_LABEL`, `duplicate_of` le pointeur du premier, rien n'étant
  écrit ; l'import est d'EP-09 ;
- écart : `WF-REF-0190-A` — « Une colonne « Nom Matricule » non déclarée n'est pas conservée, et le
  compte rendu la nomme ; déclarée conservée, elle est restituée à la consultation des lignes
  importées ensuite. » : `kept_columns` se déclare et se relit ici ; l'import et la consultation
  sont d'EP-09 ;
- écart : `WF-REF-0190-A` — « Une extraction à laquelle manque une colonne exigée est refusée, et
  le message nomme la colonne attendue. » : EP-09 ;
- propre à l'US : une correspondance incomplète s'enregistre ; `is_complete` devient vrai dès que
  les quatre colonnes exigées ont un intitulé, le poste restant facultatif ; un corps qui ne porte
  pas les cinq colonnes, chacune une fois, dans l'ordre d'`ActualCostSourceColumn`, est refusé par
  422 sur `/columns` ; plus de 20 intitulés ou 50 colonnes conservées par `VALUE_TOO_LONG` ;
- propre à l'US : la lecture relève de `cost_settings.read` (404 sans elle), l'écriture de
  `cost_settings.write` (403), un compteur périmé de 412 ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service, et la
  page `/reference/costs/actual-cost-mapping` (EP-16/US-0620) joue contre le service.

**Notes de réalisation.** La comparaison des intitulés se fait sur une forme repliée — minuscules,
accents retirés (`unaccent`, que les règles SQL emploient déjà pour la recherche), espaces en bout
ôtés —, gardée en colonne à côté de l'intitulé tel que saisi, pour que l'unicité soit une
contrainte de la base et non un parcours. EP-09 lit l'extraction selon cette forme.

**Hors périmètre.** L'import des coûts réels (EP-09).

---

## US-0880 — La désactivation à la place de la suppression, et les objets désactivés

- **statut** : à faire
- **exigences** : `WF-REF-0010-A`, `WF-REF-0150-A`, `WF-REF-0020-A`, `WF-REF-0130-A`
- **opérations** : les opérations d'activation et les listes du référentiel, servies par
  US-0820 à US-0860
- **issue** :

**En tant que** manager, **je veux** qu'aucun objet du référentiel ne se supprime, qu'un objet
désactivé disparaisse des choix sans disparaître de ce qui l'emploie, et le retrouver pour le
réactiver, **afin que** l'histoire des projets reste lisible et qu'une erreur se répare.

**Critères d'acceptation.**

- `WF-REF-0010-A` — « Aucun écran ne propose de supprimer un objet du référentiel. » : aucune
  opération du contrat ne supprime un objet du référentiel, et aucune commande des cinq écrans ;
- `WF-REF-0010-A` — « Un objet désactivé n'apparaît plus dans les listes de choix, mais reste
  affiché sur les éléments qui l'emploient. » : les listes de choix des formulaires — la nature
  d'une catégorie, le nœud, la catégorie et le calendrier d'un rôle, le nœud d'un compte — ne
  proposent que les actifs ; un rôle rattaché à une catégorie, un calendrier ou un nœud désactivés
  les nomme toujours (`cost_category_label`, `calendar_label`, `org_node_label`), une catégorie sa
  nature désactivée, un compte son nœud désactivé ; les lignes de devis sont d'EP-07 ;
- `WF-REF-0010-A` — « Une fois réactivé, il est de nouveau proposé. »
- écart : `WF-REF-0010-A` — « Après désactivation d'un rôle de ressource, les lignes qui le
  portent sont signalées dans la grille de devis et dans celle du reste à engager, et restent
  lisibles. » : les lignes sont d'EP-07, qui clôt ;
- `WF-REF-0010-A` — « La désactivation d'une nature désactive ses catégories. » : constaté par
  US-0820 ;
- `WF-REF-0010-A` — « La réactivation d'une catégorie dont la nature est désactivée est
  refusée. » : constaté par US-0820 ;
- `WF-REF-0150-A` — « Un objet désactivé n'apparaît pas dans la liste par défaut, apparaît lorsque
  l'affichage des objets désactivés est demandé, et peut y être réactivé. » : contre le service,
  pour chacune des cinq listes — nœuds, rôles, calendriers, natures, catégories — et la grille des
  taux : sans `include_inactive`, les actifs seuls ; avec, les désactivés aussi, à une session
  qui porte la permission de lecture de la partie (`cost_settings.read`,
  `resource_settings.read`), refusé par 403 sans elle (#300, #351) ; `is_active` faux de même ; un
  objet désactivé s'y réactive par sa commande, pour qui porte la permission de modification ;
- écart : `WF-REF-0020-A` — « On désactive un rôle de ressource et une catégorie de coût employés
  par une révision en cours. » : la révision est d'EP-07, qui clôt ; ici, la désactivation n'écrit
  que l'objet et ce que la cascade nomme, rien d'autre ;
- écart : `WF-REF-0020-A` — « La révision reste calculable et peut être marquée sans que ses
  lignes soient modifiées. » : EP-07 ;
- écart : `WF-REF-0130-A` — « Après correction d'un taux horaire et changement de la catégorie
  d'un rôle, les montants d'une révision marquée qui les employait sont identiques à ceux relevés
  avant la modification. » : EP-07, qui clôt ; ici, une modification n'écrit que l'objet, et les
  tables images d'une révision (`revision_role`, `revision_calendar`, `revision_category`,
  `revision_rate`, §4.4.1) ne sont pas d'EP-05 ;
- écart : `WF-REF-0130-A` — « Après abaissement du seuil d'alerte, la zone de l'indice de coût
  d'une révision marquée peut changer, sa valeur non. » : EP-07 constate avec EP-10 ;
- propre à l'US : les colonnes d'audit de l'objet désactivé ou réactivé nomment l'auteur et le
  moment (WF-DAT-0070) ; aucune inscription au journal d'audit, que WF-SEC-0030 n'énumère pas pour
  le référentiel (« Conception ») ;
- propre à l'US : les parcours de chaque écran du référentiel montrent, contre le service, les
  désactivés par le filtre de l'écran et les réactivent (`reference.spec.ts`, en mode service).

**Notes de réalisation.** L'US ferme ce que chaque US d'objet a amorcé : elle ne crée aucune
opération, et ses tests parcourent les cinq listes avec les trois sessions — sans permission du
référentiel, lecture seule, modification.

**Hors périmètre.** Les lignes et les révisions qui emploient un objet (EP-07) ; le signalement
dans les grilles (EP-07).

---

## US-0890 — Le témoin chargé, et les parcours rejoués contre le service

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`
- **opérations** : aucune en propre ; le chargement passe par les interfaces du noyau
- **issue** :

**En tant que** développeur, **je veux** charger sur une plateforme neuve la tranche du
référentiel de l'univers témoin, avec ses identifiants, par une commande du back, et rejouer
contre le service les parcours écrits sur le faux back, **afin que** les tests déjà écrits
prouvent le service sans réécriture de leurs attendus (#1402).

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour la tranche du référentiel — les nœuds du témoin, deux désactivés compris,
  ses cinq rôles dont deux désactivés, ses deux calendriers, ses trois natures, ses deux cents
  catégories, la grille de cent cinquante catégories de main-d'œuvre sur quinze ans, ses unités de
  durée, ses réglages et sa correspondance —, chargée par `waterfall-api load-witness` (nom à fixer
  à la conception) sur une plateforme amorcée, par les interfaces des modules, jamais par un
  `INSERT`, avec les identifiants du témoin (`universe(n)`) et les objets désactivés désactivés
  après leur création ; les autres tranches sont d'EP-04 à EP-10, les volumes entiers d'EP-13, qui
  clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes
  identiques. » : deux plateformes neuves chargées portent les mêmes identifiants, codes et
  libellés ; une seconde exécution sur la même plateforme ne crée rien et le dit ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  la tranche ne porte aucune adresse ; ses libellés sont ceux du témoin, fictifs
  (`test_mockuniverse.py` les tient) ;
- propre à l'US : la commande lit la description du témoin que `make mock-data` tient —
  `fixtures/api/org_nodes_with_inactive.json`, `resource_roles` (avec les désactivés),
  `calendars`, `cost_types`, `volume/cost_categories.json`, `volume/hourly_rate_grid.json`,
  `duration_units`, `reference_settings`, `actual_cost_mapping` — et échoue, en le disant, sur un
  témoin que les règles du référentiel refusent ; le code de calcul du faux back n'est pas
  réemployé ;
- propre à l'US : les dates et les auteurs des objets chargés sont ceux du chargement — la
  plateforme (WF-DAT-0070) —, non ceux du témoin (décision de l'auteur du 2026-10-28) ;
- propre à l'US : `make e2e-service` charge le témoin après l'amorçage, par un service du Compose
  de service (`witness`, modèle d'`install`), et un `make service-witness` le fait à la main ;
- propre à l'US : les parcours du référentiel — `reference.spec.ts`, et les lectures du
  référentiel d'`admin.spec.ts` et de `navigation.spec.ts` — se jouent dans le projet `service`
  de Playwright sans réécriture de leurs attendus de lecture, par une fixture commune qui accorde
  la session sur le faux back et se connecte sur le service ; les assertions qui affirmaient la
  réponse du faux back à une écriture affirment ce qui a été écrit (décision de l'auteur du
  2026-10-28) ; ce qui dépend de l'horloge ou d'un calcul que le service ne fait pas encore se
  note comme non rejoué, et la liste est dans le guide ;
- propre à l'US : `docs/roadmap/README.md` dit une fois le principe du jeu de données (le saisi
  se charge par la couche de service, le calculé devient l'attendu, la spécification arbitre, pas
  de réemploi du calcul du faux back, chaque EPIC du back nomme sa tranche), et le guide dit la
  commande, ce qu'elle charge et ce que deviennent `fixtures/api/` et Prism pour les écrans non
  branchés.

**Notes de réalisation.** Décisions de l'auteur du 2026-10-28 sur #1402 : WF-QUA-0040 démarre ici
avec la tranche du référentiel ; le chargeur est une commande du back, au sommet des couches comme
l'amorçage, avec un paramètre d'identifiant imposé que seule cette voie emploie et que l'API
n'offre jamais ; les mêmes fichiers de parcours jouent dans les deux modes. La grille des taux
du témoin compte cent cinquante lignes sur quinze ans, deux mille deux cent cinquante taux au
plus : le chargement reste court. Le faux back reste pour les écrans que le service ne sert pas,
et `fixtures/api/` restent les exemples du contrat.

**Hors périmètre.** Les autres tranches du témoin (EP-04 et suivants) ; les trois cents projets
(EP-13) ; les parcours des écrans non branchés.

---

## US-0900 — Les écrans du référentiel branchés sur le service, et les usages du manager

- **statut** : à faire
- **exigences** : `WF-INTF-0020-A`, `WF-ADM-0020-A`
- **opérations** : toutes celles de `reference`, lues par les cinq écrans
- **issue** :

**En tant que** manager, **je veux** mener à leur terme, depuis les écrans du référentiel, le
paramétrage de chacune de ses fonctions avec le seul rôle prédéfini « manager », **afin de**
tenir le référentiel de l'entreprise sans l'administrateur ; et, **en tant qu'**administrateur,
composer un rôle sur mesure qui cumule ce que deux acteurs font.

**Critères d'acceptation.**

- `WF-INTF-0020-A` — « Un utilisateur porteur du rôle prédéfini « manager » mène à leur terme le
  paramétrage de chacune des fonctions FBS-3.1 à FBS-3.4 — nœuds d'organisation, rôles de
  ressources, calendriers, natures et catégories de coût, taux horaires, correspondance de
  l'extraction des coûts réels, bornes de la matrice de risques, seuils d'alerte, délai maximal
  entre deux revues —, ouvre les vues du portefeuille (FBS-2), lesquelles portent sur l'ensemble des
  projets, et ouvre un projet dont il n'est pas contributeur. » : un parcours contre le service,
  connecté par un compte qui ne porte que « manager », crée ou règle chacun des neuf objets depuis
  son écran et relit ce qu'il a écrit ; les vues du portefeuille et le projet sont d'EP-11, qui
  clôt ;
- `WF-ADM-0020-A` — « Un rôle d'habilitation composé sur mesure permet à un utilisateur de cumuler
  des permissions relevant de deux acteurs différents. » : un rôle composé de
  `cost_settings.write` et d'`users.write` permet au même compte de créer une nature et un compte
  local, contre le service ;
- `WF-ADM-0020-A` — « Réciproquement, un rôle privé d'une permission empêche l'action
  correspondante, quel que soit l'acteur auquel l'utilisateur ressemble. » : un rôle qui porte
  tout « manager » sauf `resource_settings.write` lit les rôles de ressources et se voit refuser
  leur création par 403, `PERMISSION_MISSING` nommant la permission ;
- propre à l'US : les cinq écrans du référentiel — `/reference/costs`,
  `/reference/costs/actual-cost-mapping`, `/reference/resources`, `/reference/risks`,
  `/reference/indicators` — ne portent plus `MockupNotice` : un succès y est ce que le service a
  gardé, relu ;
- propre à l'US : les aides de ces écrans (`frontend/help/fr/FBS-3*.md`) disent ce que le service
  fait, là où elles disaient ce que le faux back n'appliquait pas.

**Notes de réalisation.** Les écrans sont ceux d'EP-02/L43 (#512), d'EP-14 et d'EP-15, déjà
branchés au contrat : cette US ne les réécrit pas ; elle retire l'avis de la maquette, joue le
parcours du manager contre le service, et solde ce que #512 laissait à EP-05 — le retrait de
l'avis, l'écran branché sur le service. Un manque que le branchement révèle — un refus que
l'écran ne dit pas, un exemple qui ne vaut pas contre le service — devient une issue, tranchée
selon le README ; un manque du contrat, une « Interface contract issue », le contrat étant figé.

**Hors périmètre.** Les vues du portefeuille et le projet non contributeur (EP-11) ; les écrans
hors du référentiel.

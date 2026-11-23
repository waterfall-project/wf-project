---
id: EP-32
titre: Corriger le moteur de planning sur les liaisons de récapitulatives, l'état d'une feuille qui devient récapitulative et le redatage, et le Gantt zoomé
statut: en cours
depend_de: EP-08
famille: front, back
issue: 4549
---

# EP-32 — Planning : moteur et Gantt

## Objet

Le moteur de planning rend des marges négatives et un chemin critique faux sur un planning tout
automatique dès qu'une liaison part d'une récapitulative, une feuille démarrée qui reçoit une sous-
tâche perd son état, et un calendrier de rôle modifié ne redate aucune révision en cours (revue du
2026-11-14, bloquants B1 et B2, foyer « le moteur de planning »). Cet EPIC les corrige, avec les
constats voisins du même code — `core/planning` et le diagramme de Gantt —, et apporte la preuve par
le back de WF-PLA-0090, qu'aucun test du service ne cite.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Cadré le 2026-11-21 : sept US, d'US-3290 à
US-3350.

## Ce qui en fait partie

- les liaisons qui partent d'une récapitulative ou la visent, et les durées écoulées de moins d'un
  jour, d'un seul tenant, avec un test de propriété sur le moteur ;
- le conflit d'une tâche manuelle sous une récapitulative liée, signalé (spécification 1.0.7), et la
  passe arrière calculée une fois par liaison ;
- l'état d'une feuille démarrée ou terminée qui reçoit une sous-tâche : elle le garde (décision de
  l'auteur du 2026-11-21, que la spécification 1.0.10 écrit) ;
- le redatage et le rechiffrage des révisions en cours quand un calendrier de rôle change, ou qu'un
  rôle change de calendrier ;
- « tâche sans heure travaillée » traduite en refus nommé, à l'ouverture d'une révision comme
  ailleurs ;
- les inscriptions orphelines à l'abandon d'une révision, et le jour de l'installation dans l'image
  de l'arborescence et le jugement « en retard » ;
- la preuve de WF-PLA-0090-A par un test du service, avant que la porte de publication ne joue
  (US-3000, EP-13) ;
- le Gantt zoomé : les barres et les liaisons placées à l'heure, l'axe dessiné sur la fenêtre
  visible, la barre de la tâche active ramenée dans le cadre au clavier, et le lien vertical que
  coupe la ligne de marque d'une suite repliée (#3785).

## Ce qui n'en fait pas partie

- la saisie en grille et le collage du planning — EP-34 ;
- l'import d'un planning MS Project — EP-33 ;
- les lectures de `node` qui parcourent toutes les partitions, et la garde des calendriers qui lit
  les lignes de devis de toutes les révisions (#4485) — EP-40 ;
- les récursions non bornées sur la profondeur de l'arbre (#4464) — EP-38 ;
- ce que `make requirements` ne lit pas d'un parcours joué contre le service — EP-36 ;
- étendre la garde de la modification d'un calendrier aux projets sans révision en cours — écarté
  au cadrage : WF-PLA-0010 ne la demande que pour une révision en cours, et l'ouverture refuse ;
- refuser une sous-tâche sous une feuille démarrée — écarté au cadrage : elle garde son état ;
- des touches qui font défiler l'axe du Gantt, et la mesure du Gantt zoomé — écartées au cadrage.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Comme EP-17,
EP-18 et EP-23 (décision de l'auteur du 2026-10-28), chaque US cite, avec tout leur Vérif, les
exigences dont ses tests relèvent ; les phrases qu'elle ne touche pas sont des écarts qui disent qui
les constate. Leur portée reste celle des EPIC qui les ouvrent et les closent : `WF-PLA-0020-A`,
`WF-PLA-0030-A`, `WF-PLA-0090-A`, `WF-PLA-0100-A` et `WF-PLA-0160-A` (closes par EP-06),
`WF-PLA-0010-A` et `WF-DAT-0010-A` (EP-07), `WF-PLA-0040-A` (EP-08), `WF-PLA-0070-A` (EP-09),
`WF-REF-0130-A` (EP-10), `WF-IHM-0100-A` (EP-14).

US-3310 réalise une règle que la spécification n'écrit pas encore : WF-PLA-0040 est amendée par la
1.0.10, et les deux phrases que l'US cite comme « texte proposé » deviennent des citations à sa
fusion ; les US d'EP-06, EP-08, EP-09, EP-17 et EP-22 qui citent WF-PLA-0040 les reçoivent alors en
écart.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Consommées ou servies, sans changement de leur forme : `listNodes`, `createNode`, `moveNodes`,
`deleteNode`, `applyPaste`, `applyImport`, `abandonRevision`, `deleteRisk`, `requestExport`,
`updateCalendar`, `updateResourceRole`, `getDurationUnits`.

Modifications du contrat, que la conception arrête et qui précèdent le code :

- `createRevision` déclare le 422 `TASK_WITHOUT_WORKING_HOURS`, tâche et rôles nommés (US-3330) ;
- `updateResourceRole` déclare les refus que le redatage peut rendre, comme `updateCalendar` les
  déclare déjà : 422 `PROJECT_HORIZON_EXCEEDED`, et la ligne rechiffrée au-delà de sa colonne
  (US-3320) ;
- le signalement d'un conflit qui nomme la subordonnée manuelle d'une récapitulative liée
  (US-3300), si `link_conflicts` ne le porte pas tel quel.

Aucune opération ne manque.

## Préalables

EP-08 fusionné, qui touche `core/planning` (gardes de calendrier, structures différentielles).

L'EPIC est `prêt`, non `en cours`, par décision de l'auteur du 2026-11-21 : ses issues sont ouvertes
d'avance (#4549, ses US et ses lots), et leurs numéros restent dans ce fichier, mais la livraison
attend son accord. C'est un écart à la définition du README (« en cours : son plan de lots est
validé, et ses issues sont ouvertes sur GitHub »), écrit ici pour qu'il ne se lise pas comme un
oubli ; l'EPIC passe `en cours` quand l'auteur le décide.

La règle de #3336 est tranchée (2026-11-21) : la feuille garde son état. US-3310, et elle seule,
attend la fusion de la spécification 1.0.10, qui amende WF-PLA-0040 ; les autres US ne l'attendent
pas.

US-3290 se fusionne avant US-3000 (EP-13), qui branche `make requirements-release` sur la
publication.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.

## Définition de fini

- un test du back cite `WF-PLA-0090-A`, et `make requirements` ne la range plus parmi les exigences
  citées par le front seul ;
- S = {A 1 j ; B 1 j ; A → B} liée début à début à T de 5 j rend A 0, B 3 j, S 0, T 0, sans conflit ;
  A (13 h) → B (0,5 eh) → C (1 j), avec D (2 j) → C, rend A et B à 0,3125 j ; le test de propriété
  « une structure sans tâche manuelle ne rend aucune marge négative ni aucun conflit » passe, durées
  écoulées et liaisons de récapitulatives comprises ;
- un prédécesseur lié fin à début à une récapitulative dont une subordonnée manuelle est datée avant
  sa fin est signalé avec elle ;
- deux récapitulatives de 500 feuilles reliées se calculent en un nombre de bornes de l'ordre de
  leur somme ; les dates du corpus MS Project et du témoin n'ont pas changé ;
- une feuille démarrée qui reçoit une sous-tâche se lit démarrée à sa date, refuse sa suppression,
  et retrouve son état en redevenant feuille ; la spécification 1.0.10 le dit, et l'US la cite ;
- `updateCalendar` sur un calendrier qui n'est pas le calendrier par défaut, et `updateResourceRole`
  qui change le calendrier d'un rôle, redatent et rechiffrent les révisions en cours dans leur
  transaction, et laissent intacte une révision marquée ;
- `createRevision` sur un projet dont une tâche n'a plus d'heure travaillée répond 422
  `TASK_WITHOUT_WORKING_HOURS`, la tâche et les rôles nommés ; `make build-openapi`,
  `make inventory`, `make client-up-to-date` et `make server-models-up-to-date` passent, et
  `docs/api/DECISIONS.md` a ses entrées ;
- l'abandon d'une révision qui a créé puis inscrit une tâche ne laisse aucune `tracking_entry` de sa
  lignée ; à 23 h 30 en temps universel, une installation au fuseau de Paris date l'image de
  l'arborescence du lendemain ;
- dans le Gantt, deux tâches de 4 h enchaînées le même jour se suivent, la liaison arrive à droite
  de son départ ; zoomé, une ligne ne dessine que les graduations de la fenêtre visible, et la
  flèche bas ramène la barre de la tâche active dans le cadre ; un lien vertical traverse la ligne
  de marque d'une suite repliée ;
- `make check` passe sur la branche de l'EPIC, la file de fusion est verte ; `make roadmap` et
  `make requirements` passent ;
- les douze constats reçus sont fermés par la fusion de leur lot.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3335 — back : une liaison début-à-début ou début-à-fin qui part d'une récapitulative rend des
  marges négatives et un chemin critique faux (WF-PLA-0100)
- #3336 — back : une feuille démarrée ou terminée qui reçoit une sous-tâche perd son état et devient
  supprimable (WF-PLA-0040, WF-PLA-0070)
- #3984 — back : le conflit d'une subordonnée manuelle d'une récapitulative liée n'est pas signalé
  (WF-PLA-0020, WF-PLA-0030)
- #3785 — front : un lien vertical du Gantt est coupé par la ligne de marque d'une suite repliée —
  laissée en dette le 2026-11-17, reprise par décision de l'auteur du 2026-11-21 (US-3350)

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4411 — le redatage des révisions en cours quand le calendrier d'un rôle change, ou qu'un rôle
  change de calendrier (BRC-01, BCH-07)
- #4412 — une durée écoulée de moins d'un jour donne une marge négative sans conflit (BPL-03,
  BPL-08) — à reprendre avec #3335
- #4413 — « tâche sans heure travaillée » levée par le moteur n'est traduite nulle part : 500 à
  l'ouverture d'une révision (BPL-05)
- #4414 — la passe arrière du moteur, quadratique sur une liaison entre récapitulatives (BPL-04) —
  reste d'un majeur : EP-26 a retiré le rejeu des saisies inertes
- #4415 — WF-PLA-0090-A, close par EP-06, n'est citée par aucun test du back (FTE-01, RMP-05) —
  avant US-3000
- #4416 — le jour en temps universel hors du jour de l'installation, dans l'image de l'arborescence
  et le jugement « en retard » (BEX-15)
- #4417 — les inscriptions orphelines à l'abandon d'une révision (BPL-10)
- #4418 — le Gantt zoomé : niveau heures, axe, clavier (FPL-04, FPL-05, FPL-06)

Ouverts au cadrage du 2026-11-21, avec les issues de l'EPIC :

- #4564 — spec : WF-PLA-0040, une feuille démarrée ou terminée qui reçoit une sous-tâche garde son
  état — bloque US-3310, jusqu'à la fusion de la spécification 1.0.10
- #4565 — contrat : `LinkConflict` nomme la tâche manuelle en cause
- #4566 — contrat : `createRevision` déclare le refus d'une tâche sans heure travaillée
- #4567 — contrat : `updateResourceRole` déclare les refus du redatage

Relevés à la livraison, arbitrés le 2026-11-23 :

- #4749 — back : une tâche suivie d'une durée écoulée qui atteint la fin du jour est critique malgré
  un jeu apparent — écarté, la marge reste nulle ; l'écart est dit dans la conception (« Durée
  écoulée »)
- #4777 — front : deux tests de la ligne de marque disent plus qu'ils ne prouvent — reporté → EP-34,
  au prochain lot qui touche `folded-runs.dom.test.tsx`
- #4788 — back : le changement de catégorie d'un rôle ne rechiffre pas les révisions en cours —
  reporté → EP-35, à vérifier d'abord par un test de service
- #4789 — back : aucun test ne couvre le 409 du code tenu à la mise à jour d'un rôle, avant et après
  le redatage — reporté → EP-35, qui touche `resource_roles.py`
- #4799 — contrat : l'import MS Project rend 500 sur une tâche créée sans heure travaillée, le
  contrat ne sait pas la nommer — reporté → EP-33 (US-3210b), qui écrit l'import MS Project ; il
  attend la livraison d'EP-32, qui apporte `TASK_WITHOUT_WORKING_HOURS`

## Conception

Écrite le 2026-11-21, contre `main` (12a58bc27) et `epic/EP-08` (99d036957), dont EP-32 part une
fois fusionnée. `scheduling/engine.py` et `scheduling/links.py` sont identiques, octet pour octet,
sur `main` et sur les branches d'EP-08, d'EP-11 et d'EP-13.

### Ce que le cadrage décide

Sept décisions de l'auteur du 2026-11-21, chacune avec l'option écartée :

| Sujet | Retenu | Écarté, et pourquoi |
|---|---|---|
| une feuille démarrée qui reçoit une sous-tâche (#3336) | elle garde son état, qui entre dans l'état dérivé | refuser la sous-tâche (422, comme `MILESTONE_HAS_NO_SUBTASK`) : on ne détaillerait plus une tâche démarrée, et le refus se répéterait à chaque entrée — création, déplacement, collage, import, fusion, greffe et mise à jour d'un différentiel |
| la spécification de cette règle | un constat de spécification, porté par la 1.0.10 ; seul le lot d'US-3310 attend sa fusion | faire attendre tout l'EPIC, comme EP-30 : les bloquants du moteur n'ont rien à voir avec elle ; livrer sans attendre : la spécification précède le code |
| une tâche sans heure à l'ouverture (#4413) | `createRevision` refuse, 422 `TASK_WITHOUT_WORKING_HOURS` | étendre la garde de la modification d'un calendrier à la dernière révision marquée des projets au repos : au-delà de WF-PLA-0010 (« d'une révision en cours »), et un projet au repos depuis des mois bloquerait le référentiel |
| le niveau des heures du Gantt (FPL-04) | les barres et les liaisons placées à l'heure, à tous les niveaux | retirer le niveau des heures : la flèche en arrière de deux tâches du même jour restait aux autres niveaux |
| l'axe zoomé (FPL-05) | corrigé sans mesure, prouvé par un compte d'éléments | mesurer d'abord : la mesure prend le poste entier, et le placement à l'heure touche déjà ce dessin ; abandonner |
| le clavier dans le Gantt zoomé (FPL-06) | la barre de la tâche active est ramenée dans le cadre | des touches de défilement de l'axe : un raccourci de plus, à tenir hors de ceux du navigateur |
| #3785, le lien coupé par une ligne de marque | corrigé par US-3350 | la laisser en dette : c'était la décision du 2026-11-17, relayée par le pilote d'EP-27 ; celle du 2026-11-21 la renverse |

Et ce que la conception tranche elle-même :

| Sujet | Retenu | Écarté, et pourquoi |
|---|---|---|
| les marges et le chemin critique déjà conservés, faux par #3335 et #4412 | aucun rejeu : une révision en cours les retrouve justes à sa prochaine écriture ou à son prochain redatage, une révision marquée garde ceux qu'elle a figés (WF-REF-0130) | une migration qui rejoue le moteur : une migration de schéma n'appelle pas le noyau, et elle tiendrait le verrou de toutes les structures en cours ; les dates, elles, n'ont jamais été fausses |
| ce qu'un conflit nomme sous une récapitulative (#3984) | `LinkConflict` gagne `manual_node_id`, la tâche manuelle en cause ; les tâches manuelles en conflit d'une liaison sont conservées dans une table | signaler à la lecture toutes les subordonnées manuelles de la récapitulative : une subordonnée datée assez tard serait signalée à tort, et la lecture ne rejoue pas le moteur |
| le redatage au changement d'un calendrier de rôle (#4411) | toutes les structures des révisions en cours, par `recalculate` tel qu'il est, dès que les heures d'un calendrier changent | ne rejouer que les structures dont une tâche emploie le calendrier : une lecture de plus des lignes de devis de toutes les révisions en cours, celle que #4485 (EP-40) reproche déjà à la garde ; le coût du rejeu est borné par US-3300 |
| le rechiffrage d'une tâche que le redatage ne déplace pas (BCH-07) | `reschedule_current_structures` rechiffre toutes les tâches des structures qu'il rejoue | ne rechiffrer que les tâches des rôles touchés : le défaut existe aussi pour le calendrier par défaut et les constantes d'unités, qui passent par la même fonction |
| où se traduit le refus du moteur (#4413) | dans `dated`, le seul appel du moteur, pour toutes les écritures | l'attraper dans `create_revision` seul : `createNode` sur un calendrier par défaut vide rendrait encore 500 |
| une récapitulative dont la facette porte déjà un état | lue telle quelle comme son état propre, sans migration | une migration qui remet à « non démarrée » la facette des récapitulatives : elle effacerait l'état des feuilles démarrées que le défaut n'a pas encore écrasé, celles que la correction rétablit |

### Tables et migrations

Une seule table nouvelle, `task_link_conflict`, par US-3300 : pour une liaison en conflit, les
tâches manuelles que son prédécesseur ne peut pas satisfaire.

- colonnes : `project_id`, `link_id`, `node_id` — la clé —, `revision_id`, `structure_id` ;
- partitionnée par projet, comme `task_link` ; clés étrangères vers `task_link` et vers `node`, qui
  suivent la suppression de la liaison ou de la tâche à l'intérieur d'une révision en cours (§4.4.1) ;
  le déclencheur des révisions marquées la tient en lecture seule comme les autres tables d'une
  révision ;
- écrite par `kept` (`dating.py`), dans l'écriture qui pose `task_link.in_conflict`, lequel reste :
  une liaison est en conflit dès qu'elle a une ligne ici ;
- copiée à l'ouverture d'une révision avec les liaisons, puis récrite par `redate_copy` ; supprimée à
  l'abandon avec elles (WF-DAT-0010) ;
- la migration la crée vide et la remplit, pour chaque liaison `in_conflict` dont le successeur est
  une feuille manuelle, de ce successeur : c'est ce que le moteur sait dire aujourd'hui. Les
  conflits des récapitulatives liées naissent au premier rejeu.

US-3310 n'ajoute ni colonne ni migration : l'état propre d'une récapitulative est celui que sa
facette `task` porte déjà (`progress`, `started_on`), que la lecture ignorait.

US-3340 n'en ajoute pas non plus : `tracking_entry` ne tient à ses nœuds par aucune clé, et c'est
voulu — une inscription suit la lignée d'une révision à l'autre.

### Les modules du noyau

**`core/planning/scheduling` (US-3300).** Le moteur seul, sans base.

- *Passe arrière.* Pour chaque liaison, la borne que ses successeurs laissent — le plus tôt des
  instants que rendent les feuilles du successeur — se calcule une fois, dans la mesure du
  successeur, puis se rapporte au calendrier de chaque feuille du prédécesseur. Les feuilles d'une
  tâche se mémorisent (`Plan.leaves`). Une liaison qui part d'une fin borne chaque feuille du
  prédécesseur ; une liaison qui part d'un début ne borne que les feuilles dont le début au plus tôt
  est celui de la récapitulative, les autres n'en reçoivent aucune borne (#3335).
- *Durée écoulée.* `latest_start` cherche le dernier départ du jour dont la fin placée tient encore
  le compte, au lieu de la première heure du jour (BPL-03). `entries.finish_after` borne la fin
  d'une tâche manuelle à durée écoulée par `calendar.bounded`, comme `placed` (BPL-08).
  Écart retenu (#4749, arbitré le 2026-11-23) : une tâche suivie d'une durée écoulée qui atteint la
  fin du jour garde une marge nulle, et toutes deux sont critiques, malgré un jeu apparent. Sur un
  calendrier de 8 h, A (13 h) → B (10 eh) : A finit le mardi à 5 h, B va de 5 h à 8 h ; A pourrait
  finir jusqu'à 8 h sans retarder B, mais décalée de ces 3 h elle pousserait B au mercredi. Ce jeu
  est une borne qu'aucun décalage n'atteint, non une marge : la marge reste nulle, et l'invariant
  des exemples (#2832) tient — une tâche décalée de sa marge laisse la fin du projet inchangée.
  Écarté : une marge « strictement inférieure à » pour ces durées.
- *Conflits.* `conflicts` juge chaque feuille manuelle sous le successeur d'une liaison, comme
  `place` et `backward` le font ; `LinkConflict` porte la tâche manuelle en cause, qui est le
  successeur quand celui-ci est une feuille.
- *Le test de propriété* tire ses structures d'un générateur à graine fixe, écrit dans les tests :
  le back n'a pas de bibliothèque de tests de propriété, et n'en reçoit pas pour un test. Le compte
  des bornes se lit par un compteur que le moteur expose aux tests, non par un chronomètre.
- La passe avant ne change pas : aucune date ne bouge.

**`core/planning`, l'état (US-3310).** `state_of` donne à `_derived` l'état propre de la
récapitulative, lu sur sa facette : démarrée ou terminée comme feuille, elle est au moins démarrée,
et sa date de démarrage entre dans le minimum. `emptied` écrit donc sur la feuille retrouvée un état
qui contient déjà le sien. `closed_above` et `reopened` gardent leur rôle — une terminaison périmée
est effacée, la date de démarrage reste. La garde de `deleteNode` et le Kanban lisent `state_of` :
ils suivent sans être touchés. `states_without` passe par les mêmes fonctions. Rien ne change pour
une récapitulative dont la facette est « non démarrée ».

**`core/planning`, le référentiel (US-3320, US-3330).**

- `reschedule_current_structures` rejoue chaque structure avec toutes ses tâches à rechiffrer
  (`Holding.repriced`) : calendrier de rôle, calendrier par défaut et constantes d'unités passent
  par elle.
- `dated` traduit `TaskWithoutWorkingHoursError` en 422 `TASK_WITHOUT_WORKING_HOURS`, la tâche
  nommée par son nœud et son libellé, ses rôles par ceux de ses lignes de main-d'œuvre, que le
  crochet des calendriers du devis sait déjà lire. Les opérations d'EP-08 qui attrapent l'exception
  avant elle (`grafting`, `merging`, `rebasing`) gardent leur traduction.
- `redate_copy` ne change pas : le refus remonte de `dated`, et l'ouverture, qui est une
  transaction, n'écrit rien.

**`core/resource_settings` (US-3320).** `update_calendar` appelle `recalculate` dès que des heures
changent, quel que soit le calendrier. `update_role` prend le verrou du référentiel avant celui du
rôle, puis appelle `recalculate` quand le calendrier du rôle change ; l'ordre reste celui d'EP-06 :
le référentiel, la ligne, les structures. Le module n'apprend rien du planning : il passe par le
registre `register_recalculation`, comme aujourd'hui.

**`core/planning`, l'abandon et le jour (US-3340).** La suppression des inscriptions des lignées
qu'aucun nœud du projet ne porte plus, aujourd'hui dans `shaping.deleted`, devient une fonction
privée commune, que `closing._delete_where` appelle aussi — pour l'abandon d'une révision comme pour
la structure qui part avec son propriétaire. `task_tree.py` et `views.py` lisent le jour par
`current_day`, de l'interface des projets, que le planning importe déjà.

**Ce que chacun expose aux autres.** Rien de nouveau : aucune interface de module ne change de
signature, hors `LinkConflict` et `ConflictView`, qui gagnent la tâche manuelle.

### Le contrat

Trois modifications, faites avant le code qui les sert, chacune avec son entrée dans
`docs/api/DECISIONS.md` :

1. `LinkConflict.manual_node_id`, requis : la tâche manuelle que le prédécesseur ne peut pas
   satisfaire — le successeur lui-même, ou sa subordonnée manuelle quand il est une récapitulative.
   `link_conflicts` est rendu sur le prédécesseur et sur cette tâche manuelle. Le témoin n'a aucun
   conflit sous une récapitulative : ses exemples gagnent le champ, égal au successeur, et le faux
   back le rend de même.
2. `createRevision` déclare le 422 `TASK_WITHOUT_WORKING_HOURS`, `params.tasks` et
   `params.resource_roles` comme une saisie les rend. Pas d'exemple : aucune tâche du témoin n'est
   sans heure.
3. `updateResourceRole` déclare les deux refus du redatage, dans les termes d'`updateCalendar` :
   422 `PROJECT_HORIZON_EXCEEDED`, projets nommés, et le refus d'une ligne rechiffrée au-delà de sa
   colonne, sur `/calendar_id` (#3401).

Le front suit la première : la grille et le Gantt signalent la tâche de `manual_node_id`. Les deux
autres sont des refus que les écrans montrent déjà par leur message.

### Le front (US-3350)

- *Placement* (`layout.ts`). L'instant d'une tâche se place à son jour plus ses heures rapportées
  aux heures de ce jour sur son calendrier (`calendar_hours`) ; sans calendrier — la frise d'une
  chronologie —, ou un jour sans heure, le placement au jour d'aujourd'hui. `gantt-image.ts` lit la
  même mise en place : l'image exportée suit.
- *Axe* (`gantt.tsx`). `Months` et `DaysOff` ne dessinent que ce qui tombe dans la fenêtre que la
  vue connaît, décalage et largeur du cadre ; la vue, valeur du contexte, est mémoïsée.
- *Clavier.* Quand la ligne active de la grille change et que le Gantt est zoomé, `reveal` ramène la
  barre de cette ligne dans le cadre. Rien ne s'écrit, aucune touche n'est ajoutée.
- *Ligne de marque* (#3785). La ligne de marque d'une suite repliée dessine dans sa cellule du Gantt
  le tronçon des liaisons qui la traversent ; `folded-runs.tsx` n'est touché que pour cela.
- Le guide (`docs/dev/README-fr.md`, et `README.md`) dit le placement à l'heure.

### L'ordre de construction

1. US-3290, des tests seuls : rien ne la précède, et elle doit être fusionnée avant US-3000.
2. Le contrat, d'un bloc : les trois modifications, le client et les modèles engendrés, le faux
   back. Tout le reste le suit.
3. Le moteur (US-3300) : la passe arrière et les durées écoulées d'abord, sans base ; puis la table
   et les conflits, qui demandent la migration et le contrat.
4. En parallèle une fois le contrat posé : le redatage (US-3320), dans `reference.py` et le
   référentiel ; le refus nommé (US-3330), dans `dating.py`, que les conflits d'US-3300 écrivent
   aussi ; l'abandon et le jour (US-3340), qui n'attendent pas le contrat.
5. Le Gantt (US-3350), après le contrat, sans dépendre du back : le placement, puis l'axe et le
   clavier, puis la ligne de marque.
6. US-3310 en dernier, quand la spécification 1.0.10 est fusionnée.

### Les EPIC voisins

- **EP-08** touche `rescheduling.py` et les gardes de calendrier (US-3060/L9, #4389) : EP-32 part de
  sa fusion, et ne reprend aucun de ses lots.
- **EP-30** écrit `core/planning` pour les différentiels des risques (`rebasing`, `merging`,
  `grafting`) : il ne touche ni le moteur, ni `views.py` pour l'état. La règle retenue pour #3336
  ne lui ajoute aucun refus.
- **EP-34** tient la saisie en grille et le collage : `folded-runs.tsx` est le seul fichier de la
  grille qu'EP-32 touche, pour le tracé d'un lien.
- **EP-35** reçoit #3985, la désactivation d'un calendrier que portent des rôles actifs, dans le même
  `calendars.py` du référentiel que US-3320 : fonctions distinctes, EP-35 vient après.
- **EP-40** reçoit #4485, la garde des calendriers qui lit toutes les révisions : US-3320 ne
  l'étend pas.
- **EP-13** (US-3000) attend US-3290.

---

## US-3290 — Le chemin critique que le Gantt montre est prouvé par un test du service

- **statut** : fini
- **exigences** : `WF-PLA-0090-A`
- **opérations** : `listNodes`
- **issue** : #4550

**En tant que** développeur, **je veux** qu'un test du back cite `WF-PLA-0090-A` sur ce que le
service doit au diagramme de Gantt — la hiérarchie, les liaisons et le chemin critique qu'il rend —,
**afin que** l'exigence, close par EP-06 (`front, back`), ne soit plus comptée « front seul » et que
la porte de publication d'US-3000 (EP-13) ne la nomme pas en échec (#4415).

**Critères d'acceptation.**

- `WF-PLA-0090-A` — « Les liaisons et la hiérarchie sont visibles, ainsi que le chemin critique. » : la part que le service en doit : sur le planning à deux branches parallèles de durées différentes du Vérif de WF-PLA-0100, sous une récapitulative, `listNodes` rend chaque tâche avec son parent, ses prédécesseurs et `is_critical` — vrai sur la branche la plus longue et sur la récapitulative, faux sur l'autre branche ; un test du back le tient et cite `WF-PLA-0090-A`.
- écart : `WF-PLA-0090-A` — « Aucune action de la souris ou du clavier ne modifie une tâche depuis le Gantt. » : constaté par le front, EP-06 (US-1470) et EP-15 (US-0530), inchangé.
- écart : `WF-PLA-0090-A` — « Une récapitulative pliée dans la grille l'est dans le Gantt, et réciproquement. » : constaté par le front, EP-06 (US-1470) et EP-15 (US-0530), inchangé.
- propre à l'US : `make requirements` ne range plus `WF-PLA-0090-A` parmi les exigences citées par
  le front seul, et `make requirements-release` ne la nomme pas.

**Notes de réalisation.** La proposition (a) de FTE-01
(`docs/reviews/2026-11-14-revue-complete/front-tests.md`) : le test va à côté de ceux de
WF-PLA-0100. Cette US se livre la première, et ne touche que des tests : rien n'empêche de la
fusionner avant US-3000.

**Hors périmètre.** Déplacer `planning-service.spec.ts` sous `e2e/service/`, ou faire lire
l'étiquette `@shared` à `wftools.coverage` : ce que `make requirements` ne lit pas est à EP-36.

---

## US-3300 — Le moteur de planning : les liaisons d'une récapitulative et les durées écoulées de moins d'un jour rendent des marges justes, et une liaison entre récapitulatives se calcule une fois

- **statut** : en cours
- **exigences** : `WF-PLA-0100-A`, `WF-PLA-0020-A`, `WF-PLA-0030-A`, `WF-PLA-0160-A`
- **opérations** : aucune en propre — le moteur ; `listNodes` rend les marges, le chemin critique et
  les conflits qu'il calcule
- **issue** : #4551

**En tant que** chef de projet, **je veux** qu'un planning tout automatique ne porte aucune marge
négative ni aucune tâche critique à tort, qu'une liaison parte d'une récapitulative ou qu'une durée
soit écoulée, et que le conflit d'une tâche manuelle sous une récapitulative liée me soit signalé,
**afin de** lire dans la grille et le Gantt un chemin critique que le marquage peut figer (#3335,
#3984, #4412) ; **et** qu'une saisie sur un planning dont les phases s'enchaînent par leurs
récapitulatives ne tienne pas le verrou de la structure plusieurs secondes (#4414).

**Critères d'acceptation.**

- `WF-PLA-0100-A` — « Sur un planning à deux branches parallèles de durées différentes, la branche la plus longue est critique et l'autre porte une marge égale à leur écart. » : sa forme pour une liaison qui part du début d'une récapitulative (#3335) : sur un calendrier de 8 h du lundi au vendredi, sans tâche manuelle, la récapitulative S = {A 1 j ; B 1 j ; A → B fin à début} et T de 5 j, S → T début à début : A porte une marge nulle, B une marge de 3 j, S une marge nulle, T une marge nulle, sans `link_conflicts` ; les dates sont celles d'aujourd'hui (A lundi, B mardi, T du lundi au vendredi) ; de même pour une liaison début à fin.
- écart : `WF-PLA-0100-A` — « Allonger une tâche de la branche courte au-delà de sa marge la rend critique à son tour. » : constaté par EP-06 (US-1390) et EP-23 (US-1820), inchangé.
- écart : `WF-PLA-0100-A` — « Une tâche en mode manuel n'affiche aucune marge et n'apparaît jamais sur le chemin critique, alors que ses successeurs automatiques voient leurs marges calculées à partir de ses dates. » : constaté par EP-06 (US-1390) et EP-23 (US-1820), inchangé.
- `WF-PLA-0100-A` — « Un prédécesseur automatique qui ne peut pas finir avant le début d'une tâche manuelle porte une marge négative, apparaît sur le chemin critique et est signalé. » : sa forme quand la liaison vise la récapitulative de la tâche manuelle (BPL-06) : P de 5 j, lié fin à début à S, dont la subordonnée M est manuelle et datée le mercredi : P porte une marge de −3 j, apparaît sur le chemin critique, et P et M sont signalés par la liaison P → S.
- écart : `WF-PLA-0100-A` — « Une récapitulative dont une subordonnée est critique est critique et affiche la marge de cette subordonnée, nulle ou négative. » : constaté par EP-06 (US-1390) et EP-23 (US-1820), inchangé.
- écart : `WF-PLA-0100-A` — « Un prédécesseur lié début à début à une tâche manuelle, et qui ne peut pas commencer avant elle, porte une marge négative et est signalé. » : constaté par EP-06 (US-1390) et EP-23 (US-1820), inchangé.
- écart : `WF-PLA-0020-A` — « Le déplacement d'une tâche prédécesseur déplace ses successeurs en mode automatique et laisse inchangés ceux en mode manuel. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0020-A` — « Les dates d'une tâche en mode automatique ne sont pas saisissables. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0020-A` — « Une tâche en mode automatique sans prédécesseur commence à la date de début de planning ; avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs automatiques. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0020-A` — « Une tâche manuelle datée avant la fin calculée de son prédécesseur est signalée dans la grille et dans le Gantt, avec ce prédécesseur ; la retarder au-delà de cette fin, ou raccourcir le prédécesseur, fait disparaître le signalement. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0020-A` — « Sur un calendrier du lundi au vendredi, la date de début d'une tâche manuelle saisie un samedi est refusée, et le refus nomme le lundi suivant ; la même date importée d'un fichier MS Project est gardée et signalée au compte rendu. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0020-A` — « Le successeur d'une tâche d'un jour, lié fin à début avec une avance de cinq jours, commence avant la date de début de planning. » : constaté par EP-06 (US-1390), inchangé.
- `WF-PLA-0020-A` — « Un prédécesseur lié fin à début à une récapitulative, dont une subordonnée manuelle est datée avant sa fin, est signalé avec cette subordonnée. » : A (10 j, automatique) précède fin à début la récapitulative S, dont la seule subordonnée M est manuelle et datée avant la fin de A : A porte une marge négative, et `link_conflicts` signale A et M par la liaison A → S ; retarder M au-delà de la fin de A fait disparaître le signalement (#3984).
- écart : `WF-PLA-0030-A` — « Les quatre types et un décalage négatif sont importés, saisis et exportés sans perte. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0030-A` — « La création d'une liaison fermant un cycle, ou reliant une récapitulative à l'une de ses subordonnées, est refusée, et la raison en est nommée à l'utilisateur. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0030-A` — « Un décalage saisi en semaines ou en mois est conservé dans son unité, importé et exporté sans conversion. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0030-A` — « Un décalage de 50 % sur un prédécesseur de dix jours vaut cinq jours de travail. » : constaté par EP-06 (US-1390), inchangé.
- `WF-PLA-0030-A` — « Une liaison fin à début vers une récapitulative fait commencer chacune de ses subordonnées automatiques sans prédécesseur après la fin du prédécesseur. » : inchangé en passe avant, et un test épingle ce que la spécification 1.0.7 a tranché pour les autres types (« s'impose à chacune de ses subordonnées », #3368, BPL-07) : P de 5 j, qui finit le vendredi, lié fin à fin à S = {A 1 j ; B 1 j ; A → B fin à début} : A finit le vendredi et B le lundi.
- écart : `WF-PLA-0160-A` — « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize heures, « 1 sem » quarante heures et « 1 m » cent soixante heures. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- écart : `WF-PLA-0160-A` — « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer d'unité. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- `WF-PLA-0160-A` — « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit à la dernière heure travaillée d'un vendredi s'achève le dimanche ; le successeur, sur un calendrier du lundi au vendredi, commence le lundi à la première heure travaillée, de même qu'avec un décalage de 2 eh. » : la passe avant, inchangée, reste éprouvée ; en passe arrière, une durée écoulée de moins d'un jour recule juste (#4412, BPL-03) : sur un calendrier de 8 h, A (13 h) → B (0,5 eh) → C (1 j), et D (2 j) → C : A et B portent une marge de 0,3125 j, celle que A porte quand B dure 0,5 h de travail, et aucune n'est critique ; de même pour B de 2 eh et de 30 emin.
- écart : `WF-PLA-0160-A` — « Un décalage de 2 j sur la même liaison le fait commencer le mercredi. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- écart : `WF-PLA-0160-A` — « Un fichier MS Project dont les constantes ou le calendrier diffèrent de ceux de l'installation est signalé au compte rendu ; importé en gardant les durées, une tâche de « 2 j » saisie à 7 h par jour vaut deux jours, soit seize heures avec les valeurs par défaut ; importé en gardant les dates, sa durée est le temps de travail entre ses dates du fichier sur son calendrier Waterfall. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- écart : `WF-PLA-0160-A` — « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des langues de l'interface. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- écart : `WF-PLA-0160-A` — « En anglais, « 1 j » et « 1 d » valent chacun un jour ; « 3 », saisi sans suffixe, vaut trois jours. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- écart : `WF-PLA-0160-A` — « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans une révision en cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision marquée, elle vaut toujours seize heures. » : constaté par EP-06 (US-1390), EP-23 (US-1820) et EP-24 (US-2000), inchangé.
- propre à l'US : un test de propriété tire au sort des structures sans tâche manuelle —
  récapitulatives sur plusieurs niveaux, liaisons des quatre types entre feuilles, vers une
  récapitulative et depuis une récapitulative, décalages et durées en temps de travail et en temps
  écoulé, `emin`, `eh` et `ej` compris — : aucune ne rend de marge négative ni de `link_conflicts`,
  et la fin de la structure est la fin au plus tard d'au moins une tâche.
- propre à l'US : la fin d'une tâche manuelle à durée écoulée est bornée aux heures travaillées du
  jour qu'elle atteint, comme le moteur borne la même durée en mode automatique (BPL-08) : commencée
  un lundi à la première heure sur un calendrier de 8 h, une durée saisie « 10 eh » finit le lundi à
  8 h, non à 10 h ; « 1 ej » saisi depuis un vendredi finit où le moteur le finit en automatique.
- propre à l'US : la borne qu'une liaison laisse à son prédécesseur se calcule une fois par liaison,
  non une fois par paire de feuilles (#4414, BPL-04) : sur deux récapitulatives de 500 feuilles
  reliées par une liaison, et sur dix phases de 100 feuilles enchaînées phase à phase, le nombre de
  bornes calculées croît comme la somme des feuilles, non comme leur produit ; un test le tient par
  un compte, sans chronomètre.
- propre à l'US : les dates ne changent pas : le corpus MS Project, les exemples de
  `test_scheduling_examples.py` et le témoin rendent les dates d'avant ; seules des marges, des
  appartenances au chemin critique et des conflits changent, et aucune fixture du témoin — il ne
  porte ni liaison de récapitulative ni durée écoulée de moins d'un jour.

**Notes de réalisation.** Les propositions de #3335, de BPL-03, BPL-04, BPL-06 et BPL-08
(`docs/reviews/2026-11-14-revue-complete/back-planning.md`) font foi ; le scénario de chacune y est
rejoué. La passe avant n'est pas touchée. `total_float_days` et `is_critical` sont conservés en base
: une révision en cours les retrouve justes à sa prochaine écriture ou à son prochain redatage, une
révision marquée garde ceux qu'elle a figés (WF-REF-0130) — la conception dit s'il faut les rejouer.

**Hors périmètre.** Les récursions non bornées sur la profondeur de l'arbre (BPL-09, #4464) — EP-38
; le rejeu du moteur par une saisie qui ne change aucune date — fait par EP-26 (US-2250) pour les
champs inertes ; les lectures de `node` sans le projet — EP-40.

---

## US-3310 — Une feuille démarrée ou terminée qui reçoit une sous-tâche garde son état, et ne se supprime pas

- **statut** : à faire
- **exigences** : `WF-PLA-0040-A`, `WF-PLA-0070-A`
- **opérations** : `createNode`, `moveNodes`, `applyPaste`, `applyImport`, `deleteNode`, `listNodes`
- **issue** : #4556

**En tant que** chef de projet, **je veux** qu'une tâche démarrée que je détaille en sous-tâches
reste démarrée, à sa date, **afin que** l'avancement constaté ne disparaisse ni du Kanban, ni des
indicateurs, et que la tâche ne devienne pas supprimable (#3336, bloquant B2 de la revue du
2026-11-14).

**Critères d'acceptation.**

- écart : `WF-PLA-0040-A` — « Après déplacement d'une récapitulative portant deux niveaux de subordonnées, les tâches et les lignes déplacées sont inchangées, et le devis totalise le même montant. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Les dates et l'état d'une récapitulative ne sont pas saisissables. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Une récapitulative dont une subordonnée est démarrée est démarrée ; elle n'est terminée qu'après la dernière. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre porte un reste à engager de 500 est démarrée et signalée ; la saisie d'un reste nul sur cette ligne la termine. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- `WF-PLA-0040-A` — « La suppression de la seule subordonnée d'une récapitulative de dix jours laisse une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être ajoutée. » : le retour en feuille rend l'état d'avant : P, feuille démarrée le 1er mars 2026, reçoit la sous-tâche C, non démarrée, puis la perd — par suppression de C ou par sa désindentation — : P est une feuille démarrée le 1er mars 2026, non une feuille non démarrée.
- écart : `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont la seule ligne propre est une provision de 40 est terminée et n'est pas signalée. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Une récapitulative dont la seule subordonnée est un jalon terminé et dont une ligne propre garde un reste à engager, privée de ce jalon, est une feuille démarrée d'un jour, non un jalon. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Une récapitulative terminée dont la seule subordonnée, un jalon, est déplacée devient un jalon terminé. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Le déplacement d'une sélection qui contient une récapitulative et l'une de ses subordonnées laisse la subordonnée sous la récapitulative : le groupe est déplacé entier, sans être aplati. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0040-A` — « Un déplacement qui placerait un nœud sous lui-même ou sous l'un de ses subordonnés est refusé. » : constaté par EP-06 (US-1380), EP-09 (US-1590) et EP-08 (US-2580), inchangé.
- écart : `WF-PLA-0070-A` — « La suppression d'une récapitulative supprime ses subordonnées et leurs lignes, et le devis diminue d'autant. » : constaté par EP-06 (US-1380), inchangé.
- `WF-PLA-0070-A` — « La suppression d'une tâche démarrée est refusée, et l'utilisateur est renvoyé vers la mise à zéro de son reste à engager. » : sa forme pour une récapitulative née d'une feuille démarrée : P, feuille démarrée, reçoit une sous-tâche non démarrée ; `deleteNode(P)` est refusé (409, `task_not_started`), et ni P, ni sa sous-tâche, ni ses lignes ne sont supprimées.
- propre à l'US, texte proposé pour `WF-PLA-0040-A` (spécification 1.0.10) : « Une feuille démarrée
  qui reçoit une sous-tâche non démarrée est une récapitulative démarrée, à sa date de démarrage ;
  privée de cette sous-tâche, elle redevient une feuille démarrée à cette date. » : par `createNode`
  sous P comme par `moveNodes` vers P (indentation), `listNodes` rend P `started`, `started_on` au
  1er mars 2026 ; P reste dans la colonne des tâches démarrées du Kanban, et `finish_overdue` est
  jugé sur elle.
- propre à l'US, texte proposé pour `WF-PLA-0040-A` (spécification 1.0.10) : « Une feuille terminée
  qui reçoit une sous-tâche non terminée est une récapitulative démarrée, à sa date de démarrage. »
  : la terminaison, périmée, est effacée comme elle l'est aujourd'hui (#2769) ; la date de démarrage
  est gardée, et P redevient terminée quand sa sous-tâche l'est et que le reste à engager de ses
  lignes propres est nul.
- propre à l'US : la date de démarrage d'une récapitulative est la plus ancienne entre celle qu'elle
  portait comme feuille et celles de ses subordonnées.
- propre à l'US : la règle vaut quelle que soit l'entrée — création, déplacement, collage
  (`applyPaste`), import MS Project (`applyImport`) — : aucune ne refuse la sous-tâche, et aucun
  refus n'est ajouté au contrat.
- propre à l'US : une récapitulative qui n'a jamais été une feuille démarrée se lit comme
  aujourd'hui : non démarrée tant qu'aucune subordonnée ne l'est.

**Notes de réalisation.** Règle tranchée par l'auteur au cadrage (2026-11-21) : garder l'état ;
écarté : refuser la sous-tâche par un 422 sur le modèle de `MILESTONE_HAS_NO_SUBTASK`, qui
interdirait de détailler une tâche démarrée et se répéterait à chaque entrée, fusion d'un
différentiel comprise. La phrase de WF-PLA-0040 « tire de ses subordonnées […] son état » est
amendée par un constat de spécification, que la 1.0.10 porte : **le lot de cette US attend la fusion
de la 1.0.10**, et elle seule dans l'EPIC (décision du même jour) ; les deux phrases proposées
deviennent alors des citations. Les fonctions en cause : `state_of` et `_derived`
(`core/planning/views.py`), `emptied` et `closed_above` (`shaping.py`), la garde de `deleteNode`.

**Hors périmètre.** L'état d'une récapitulative reste non saisissable ; une feuille démarrée à tort
se corrige avant de la détailler. Les révisions où une feuille démarrée a déjà perdu son état par ce
défaut ne sont pas réparées : la date effacée n'est écrite nulle part.

---

## US-3320 — Un calendrier de rôle modifié, ou un rôle changé de calendrier, redate et rechiffre les révisions en cours

- **statut** : à faire
- **exigences** : `WF-PLA-0010-A`, `WF-REF-0130-A`
- **opérations** : `updateCalendar`, `updateResourceRole`, `listNodes`
- **issue** : #4552

**En tant que** chef de projet, **je veux** que les dates et les montants de ma révision en cours
suivent le calendrier d'un rôle dès qu'il change, **afin qu'**ils ne sautent pas plus tard, à la
saisie sans rapport d'un autre, et qu'une révision marquée entre-temps ne fige pas des dates fausses
(#4411 : BRC-01, BCH-07).

**Critères d'acceptation.**

- `WF-PLA-0010-A` — « Une tâche de seize heures en mode automatique, commencée un lundi matin sur un calendrier de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre heures, elle finit le jeudi. » : sa forme au changement du référentiel : une tâche de seize heures en mode automatique d'une révision en cours, commencée un lundi matin, porte une ligne de main-d'œuvre du rôle R, dont le calendrier, qui n'est pas le calendrier par défaut, compte huit heures du lundi au vendredi : elle finit le mardi ; ce calendrier passé à quatre heures par `updateCalendar`, elle finit le jeudi à la lecture suivante de `listNodes`, sans autre écriture ; de même quand R reçoit par `updateResourceRole` un autre calendrier, de quatre heures.
- écart : `WF-PLA-0010-A` — « Une tâche dont les deux rôles travaillent huit et six heures le lundi est planifiée sur six heures ce jour-là. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « L'ajout, à une tâche dont un rôle travaille du lundi au vendredi, d'une ligne d'un rôle qui ne travaille que le week-end est refusé en nommant les deux rôles, et la tâche reste inchangée. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- `WF-PLA-0010-A` — « La répartition mensuelle de la charge d'une ligne suit les heures du calendrier de son rôle. » : sa forme pour une tâche que le changement ne déplace pas (BCH-07) : une tâche manuelle du 28 décembre au 8 janvier porte une ligne de 1 000 à 3 % d'inflation ; son rôle passe de cinq jours de 8 h à quatre jours de 10 h : la répartition entre les deux années passe de 40/60 à 50/50, et le réestimé de 1 018,00 à 1 015,00, dans la transaction du changement.
- écart : `WF-PLA-0010-A` — « L'import d'un fichier de devis dont une ligne donnerait ce résultat rejette cette ligne au compte rendu et applique les autres. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « La modification d'un calendrier qui laisserait une tâche sans heure dans un projet que le manager ne peut pas consulter est refusée en nommant ce projet par son libellé et son code ; un projet en chiffrage sans code est nommé par son seul libellé. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- `WF-REF-0130-A` — « Après correction d'un taux horaire et changement de la catégorie d'un rôle, les montants d'une révision marquée qui les employait sont identiques à ceux relevés avant la modification. » : sa forme pour le calendrier : après modification des heures du calendrier d'un rôle, puis changement du calendrier de ce rôle, les dates et les montants d'une révision marquée qui l'employait sont identiques à ceux relevés avant.
- écart : `WF-REF-0130-A` — « Après abaissement du seuil d'alerte, la zone de l'indice de coût d'une révision marquée peut changer, sa valeur non. » : constaté par EP-10 (US-1670), inchangé.
- propre à l'US : un changement qui ne touche que le libellé d'un calendrier, ou un rôle dont le
  calendrier ne change pas, ne redate ni ne rechiffre rien.
- propre à l'US : le changement qui porterait un projet au-delà de quinze ans est refusé, projets
  nommés par leur libellé et leur code (422 `PROJECT_HORIZON_EXCEEDED`), et celui qui rechiffrerait
  une ligne au-delà de sa colonne l'est au champ saisi (#3401), comme pour le calendrier par défaut
  ; rien n'est écrit.
- propre à l'US : le test qui épinglait l'ancien comportement (`test_registries.py`, « A calendar
  that is not the default redates nothing ») dit le nouveau.

**Notes de réalisation.** Les propositions de BRC-01 (`back-referentiel-couts.md`) et de BCH-07
(`back-chiffrage.md`) font foi. WF-PLA-0020 le demande dans son corps : les dates sont « recalculées
à chaque modification d'une durée, d'une liaison, d'un calendrier ou de la structure de l'arbre ».
L'ordre des verrous est celui d'EP-06 : le référentiel, la ligne, puis les structures ;
`updateResourceRole` ne prend pas aujourd'hui celui du référentiel.

**Hors périmètre.** La garde des calendriers qui lit les lignes de devis de toutes les révisions
(#4485) — EP-40 ; la désactivation d'un calendrier que portent des rôles actifs (#3985) — EP-35.

---

## US-3330 — Une tâche sans heure travaillée refuse l'ouverture d'une révision en la nommant, au lieu d'une erreur inattendue

- **statut** : à faire
- **exigences** : `WF-PLA-0010-A`
- **opérations** : `createRevision`, `createNode`
- **issue** : #4553

**En tant que** chef de projet, **je veux** que l'ouverture d'une révision dont une tâche n'a plus
d'heure travaillée — un calendrier a changé pendant que le projet était au repos — soit refusée en
nommant la tâche et ses rôles, **afin de** savoir quoi faire corriger au référentiel au lieu de
recevoir une erreur 500 à chaque essai (#4413, BPL-05).

**Critères d'acceptation.**

- écart : `WF-PLA-0010-A` — « Une tâche de seize heures en mode automatique, commencée un lundi matin sur un calendrier de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre heures, elle finit le jeudi. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « Une tâche dont les deux rôles travaillent huit et six heures le lundi est planifiée sur six heures ce jour-là. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « L'ajout, à une tâche dont un rôle travaille du lundi au vendredi, d'une ligne d'un rôle qui ne travaille que le week-end est refusé en nommant les deux rôles, et la tâche reste inchangée. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « La répartition mensuelle de la charge d'une ligne suit les heures du calendrier de son rôle. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- écart : `WF-PLA-0010-A` — « L'import d'un fichier de devis dont une ligne donnerait ce résultat rejette cette ligne au compte rendu et applique les autres. » : constaté par EP-06 (US-1390) et EP-07 (US-1490, US-1500), inchangé.
- `WF-PLA-0010-A` — « La modification d'un calendrier qui laisserait une tâche sans heure dans un projet que le manager ne peut pas consulter est refusée en nommant ce projet par son libellé et son code ; un projet en chiffrage sans code est nommé par son seul libellé. » : inchangé : la garde de la modification ne lit que les révisions en cours, comme le corps de l'exigence le dit (« d'une révision en cours ») ; le projet au repos est rattrapé à l'ouverture, ci-dessous (décision de l'auteur du 2026-11-21 ; écarté : étendre la garde à la dernière révision marquée de chaque projet au repos).
- propre à l'US : le projet P est au repos — dernière révision marquée, aucune en cours — ; une de
  ses tâches porte des lignes de deux rôles ; le calendrier de l'un change, et les deux n'ont plus
  de jour commun : `createRevision` répond 422 `TASK_WITHOUT_WORKING_HOURS`, la tâche et les rôles
  nommés, et aucune révision n'est créée ; le calendrier corrigé, l'ouverture aboutit.
- propre à l'US : le calendrier par défaut passé à zéro heure alors qu'aucune révision en cours n'a
  de tâche, le premier `createNode` d'une tâche automatique répond le même 422, et non 500.
- propre à l'US : aucune écriture qui rejoue le moteur ne rend 500 sur ce refus : il est traduit là
  où le moteur est appelé, pour toutes.

**Notes de réalisation.** La proposition de BPL-05 (`back-planning.md`) fait foi, par sa seconde
branche. Le code est déjà au contrat ; `createRevision` ne le déclare pas : c'est une modification
du contrat, que la conception prévoit. Le statut 500 d'aujourd'hui est déduit du type de
l'exception, non rejoué : le lot commence par le reproduire.

**Hors périmètre.** La garde de la modification d'un calendrier, inchangée ; l'écran de l'ouverture
d'une révision, qui montre déjà un refus 422 par son message.

---

## US-3340 — L'abandon d'une révision ne laisse aucune inscription orpheline, et le jour d'un planning est celui de l'installation

- **statut** : fini
- **exigences** : `WF-DAT-0010-A`
- **opérations** : `abandonRevision`, `deleteRisk`, `listNodes`, `requestExport`
- **issue** : #4554

**En tant qu'**exploitant, **je veux** que l'abandon d'une révision supprime les inscriptions des
tâches qu'elle seule portait, **afin qu'**aucune ligne invisible ne reste en base (#4417, BPL-10) ;
**en tant que** chef de projet, que le « Calculé le » de l'image de l'arborescence et le signalement
d'une tâche en retard lisent le jour de l'installation, non celui du temps universel (#4416,
BEX-15).

**Critères d'acceptation.**

- écart : `WF-DAT-0010-A` — « Après marquage d'une révision puis création de la suivante, le nombre de lignes de chaque table portant l'identifiant de la nouvelle révision égale celui de la révision marquée, hors les lignes des structures différentielles fusionnées, de leur base (WF-REV-0110) et des structures propres des risques survenus. » : constaté par EP-04 (US-0960) et EP-07 (US-1490), inchangé.
- écart : `WF-DAT-0010-A` — « Une modification dans la révision en cours ne change aucune ligne portant l'identifiant d'une révision marquée. » : constaté par EP-04 (US-0960) et EP-07 (US-1490), inchangé.
- `WF-DAT-0010-A` — « L'abandon d'une révision en cours ne laisse aucune ligne portant son identifiant. » : sa forme pour les inscriptions, qui ne portent pas l'identifiant d'une révision mais une lignée : une tâche créée dans la révision en cours est inscrite à une chronologie, puis la révision est abandonnée : aucune `tracking_entry` ne reste pour sa lignée ; l'inscription d'une lignée qu'une révision marquée porte encore reste.
- propre à l'US : de même pour la structure qui part avec son propriétaire — le devis propre d'un
  risque supprimé (`deleteRisk`) — : les inscriptions des lignées qu'aucun nœud du projet ne porte
  plus sont supprimées, et l'annulation de la suppression les rétablit.
- propre à l'US : sur une installation au fuseau de Paris, à 23 h 30 en temps universel un 31 mars,
  le « Calculé le » de l'image de l'arborescence des tâches est le 1er avril, et une tâche démarrée
  dont la fin est le 31 mars est signalée en retard (`finish_overdue`) ; les deux lisent
  `current_day`.

**Notes de réalisation.** Les propositions de BPL-10 (`back-planning.md`) et de BEX-15
(`back-echanges.md`) font foi. La suppression des inscriptions par lignée existe pour la suppression
d'une tâche (`shaping.deleted`) : elle se met en commun. Le second site du jour, `views.py`
(`scheduled_on`), est celui que l'issue #4416 demande de vérifier dans la même grappe.

**Hors périmètre.** Les autres lectures du jour, corrigées par US-2200 (EP-25).

---

## US-3350 — Le Gantt zoomé : les barres et les liaisons à l'heure, un axe dessiné sur la seule fenêtre visible, la barre de la tâche active ramenée dans le cadre

- **statut** : fini
- **exigences** : `WF-PLA-0090-A`, `WF-IHM-0100-A`
- **opérations** : `listNodes`, `getDurationUnits`
- **issue** : #4555

**En tant que** chef de projet, **je veux** qu'au niveau des heures le Gantt place chaque tâche aux
heures où elle se fait, que deux tâches enchaînées le même jour se suivent au lieu de se superposer,
et qu'au clavier la barre de la tâche active reste sous mes yeux, **afin de** lire les enchaînements
d'un planning zoomé sans souris (#4418 : FPL-04, FPL-05, FPL-06 ; #3785).

**Critères d'acceptation.**

- `WF-PLA-0090-A` — « Les liaisons et la hiérarchie sont visibles, ainsi que le chemin critique. » : à l'heure (FPL-04) : sur l'exemple du contrat — A de 4 h et B de 4 h le même jour de 8 h, liées fin à début —, la barre de A couvre la première moitié du jour, celle de B la seconde, et la liaison arrive à droite de son départ, à tous les niveaux de l'échelle ; l'instant d'une tâche se place à son jour plus ses heures rapportées aux heures de ce jour sur son calendrier (`calendar_hours`) ; l'image exportée suit le même placement. Et un lien vertical qui traverse la ligne de marque d'une suite repliée par « Écarts seulement » n'est plus coupé sur sa hauteur (#3785).
- `WF-PLA-0090-A` — « Aucune action de la souris ou du clavier ne modifie une tâche depuis le Gantt. » : tenu : ramener la barre de la tâche active dans le cadre n'écrit rien, et le Gantt ne prend toujours aucune saisie.
- écart : `WF-PLA-0090-A` — « Une récapitulative pliée dans la grille l'est dans le Gantt, et réciproquement. » : constaté par EP-06 (US-1470) et EP-15 (US-0530), inchangé.
- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » : sa forme pour le Gantt zoomé (FPL-06) : quand la cellule active de la grille change de ligne, au clavier, la barre de la tâche active est ramenée dans le cadre du Gantt ; sur un planning de deux ans zoomé deux fois, la flèche bas jusqu'à une tâche tardive amène sa barre dans le cadre.
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » : constaté par EP-14 (US-0200), inchangé.
- écart : `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » : constaté par EP-14 (US-0200), inchangé.
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé associé ni aucune image porteuse d'information sans description. » : constaté par EP-14 (US-0200), inchangé.
- propre à l'US : zoomé, une ligne du Gantt ne dessine que les graduations et les bandes de jours
  non travaillés de la fenêtre visible (FPL-05) : leur nombre est borné par la largeur du cadre, non
  par la durée du projet — au niveau des heures, sur un projet de trois ans, une ligne en dessine
  quelques dizaines, non 8 800 ; un test du composant le tient par un compte, sans mesure.
- propre à l'US : le guide (`docs/dev/README-fr.md`, « Rien n'y est planifié… ») dit le placement à
  l'heure, et `README.md` le suit.

**Notes de réalisation.** Décisions de l'auteur au cadrage (2026-11-21) : placer à l'heure — écarté
: retirer le niveau des heures, qui laissait la flèche en arrière aux autres niveaux ; corriger
l'axe sans mesurer — écarté : mesurer d'abord, la mesure demandant le poste entier ; la barre active
suit — écarté : des touches de défilement de l'axe, un raccourci de plus à apprendre. #3785, laissée
en dette le 2026-11-17 au pilote d'EP-27, est reprise ici par décision du 2026-11-21, qui renverse
la première. Les propositions de FPL-04 à FPL-06 (`front-planning.md`) font foi pour le reste.

**Hors périmètre.** La frise d'une chronologie garde son placement au jour : elle n'offre pas le
niveau des heures. Les navigateurs et les largeurs — EP-13 (US-0290).

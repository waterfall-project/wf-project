---
id: EP-06
titre: Construire le planning d'un projet, et le lire en grille, en Gantt et en arborescence
statut: en cours
depend_de: EP-04
famille: front, back
issue: 2316
---

# EP-06 — Planification

## Objet

Les tâches et leur hiérarchie, les jalons, les liaisons, le calendrier applicable, les modes de
planification et l'horizon d'un projet ; la grille de planning ; le diagramme de Gantt et le
chemin critique ; l'arborescence de tâches et son export ; les chronologies nommées ; le
squelette de planning engendré du lotissement ; l'import et l'export MS Project et leur
réversibilité, avec la mécanique d'import en deux temps qu'ils sont les premiers à employer.

Les lignes de devis sont portées par les tâches — l'arbre est commun —, si bien que le planning
précède le chiffrage. C'est aussi la première grille dont les saisies sont conservées :
l'annulation multi-niveaux (WF-IHM-0110) s'y construit, conflits entre contributeurs compris.
L'aller-retour avec MS Project se valide ici, dans son bloc fonctionnel, et non dans un EPIC
d'échanges séparé (revue de la ventilation, 2026-10-09 : EP-12 abandonné) : le premier
planning d'un projet vient souvent de MS Project (motif de WF-INTF-0040).

## Ce qui en fait partie

- l'arbre des tâches de la structure principale : création, modification, déplacement,
  indentation, suppression ;
- les attributs d'une tâche, son état et ses dates de démarrage et de terminaison, les jalons,
  les liaisons, le calendrier applicable, le mode de planification et l'horizon de quinze ans ;
- le calcul des dates, des marges et du chemin critique, et son recalcul quand les unités de
  durée ou le calendrier par défaut changent ;
- la date de début de planning d'une structure, sa colonne et sa saisie (`updateCostStructure`,
  #2170) ;
- la grille de planning, avec la saisie au clavier, le collage depuis un tableur et l'annulation
  servis par le serveur, le menu contextuel de ses cellules et le branchement de ses commandes —
  l'arbre pliable et le pliage commun avec le Gantt sont déjà faits par EP-02/L40, qu'EP-06
  reprend sur le service ;
- le diagramme de Gantt et l'arborescence de tâches, en lecture seule, et l'export PNG de
  l'arborescence par le worker ;
- les chronologies nommées, l'inscription des tâches et des jalons ;
- le squelette de planning engendré du lotissement ;
- l'import et l'export MS Project (FLX-01, FLX-02) et leur réversibilité, la description d'une
  tâche passant par ses notes dans les deux sens (C-375), et le corpus de plannings de référence
  (WF-QUA-0080) ;
- la mécanique d'import en deux temps — dépôt du fichier (`uploadFile`), analyse par le worker,
  compte rendu conservé en codes, confirmation, application en une transaction par le worker,
  revérification à l'exécution, expiration et purge, fichier en transit sur le stockage objet
  qu'EP-03 a posé, `available_commands` —, avec une interface où un format s'ajoute sans rouvrir
  le module, que les imports du devis (EP-07), du reste à engager et des coûts réels (EP-09)
  reprennent ;
- l'application d'un import à la révision en cours, créée au besoin ;
- la purge planifiée des fichiers en transit expirés et des exports non téléchargés
  (WF-DAT-0120) ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — les mille tâches de la structure
  principale de PRJ-001, leurs liaisons, leurs états, leurs inscriptions, les chronologies et la
  date de début de planning —, chargée par le chargeur après celle des projets ;
- les écrans du planning, du Gantt, de l'arborescence, des chronologies et de l'import de la
  maquette, branchés sur le service, et les parcours écrits sur le faux back rejoués contre lui.

## Ce qui n'en fait pas partie

- les lignes de devis — EP-07 ; l'avancement physique que la grille affiche, calculé sur
  elles — EP-10 ; la facette ligne de la table des nœuds, qu'EP-07 ajoute par sa migration ;
- la suppression d'une tâche démarrée, renvoyée vers la mise à zéro de son reste à engager, et
  le démarrage par le Kanban — EP-09 ; `setTaskProgress` est servie ici par l'API, sans écran
  (décision de l'auteur du 2026-11-07) ;
- le diagramme temps/temps, qui lit l'inscription des jalons faite ici — EP-10 ;
- les imports et exports Excel : le devis — EP-07, le reste à engager et les coûts réels — EP-09 ;
- l'export PNG d'une chronologie et du Gantt, faits par le front (EP-15, US-0530) : ici, ils se
  rejouent contre le service.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
Sept exigences que le fichier disait entières ou closes ici ont une phrase de Vérif qui demande
des lignes de devis, un import de devis, le reste à engager, le Kanban ou le réexamen d'un
risque : elles se commencent ici et se closent en EP-07, EP-08 ou EP-09 (décision de l'auteur du
2026-11-07, au cadrage). Chaque US cite les exigences dont une phrase de Vérif tient avec des
tâches, des liaisons et des structures sans ligne ; les phrases qui demandent plus sont des
écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-PLA-0040-A` | Hiérarchie des tâches | début — close en EP-08 | US-1380 |
| `WF-PLA-0050-A` | Jalons | début — close en EP-08 | US-1380 |
| `WF-PLA-0070-A` | Suppression d’une tâche | début — close en EP-09 | US-1380 |
| `WF-PLA-0170-A` | Rattachement au lotissement | début — close en EP-08 | US-1380, US-1460 |
| `WF-PLA-0150-A` | Horizon d’un projet | entière | US-1380, US-1430 |
| `WF-PLA-0010-A` | Calendrier applicable à une tâche | début — close en EP-07 | US-1390 |
| `WF-PLA-0020-A` | Mode de planification | fin — amorcée en EP-15 | US-1390 |
| `WF-PLA-0030-A` | Liaisons entre tâches | fin — amorcée en EP-15 | US-1390 |
| `WF-PLA-0100-A` | Chemin critique | entière | US-1390 |
| `WF-PLA-0160-A` | Unités de durée | fin — amorcée en EP-15, EP-05 | US-1390 |
| `WF-PLA-0060-A` | Inscription aux suivis | début — close en EP-10, amorcée aussi en EP-15 | US-1400 |
| `WF-PLA-0140-A` | Chronologies nommées | fin — amorcée en EP-15 | US-1400 |
| `WF-PLA-0130-A` | Attributs d’une tâche | début — close en EP-10 | US-1410 |
| `WF-ARC-0100-A` | Import en deux temps | entière | US-1420 |
| `WF-INTF-0080-A` | Contrôle et confirmation des imports Excel | début — close en EP-07 | US-1420 |
| `WF-INTF-0090-A` | Imports et révisions marquées | début — close en EP-08 | US-1420 |
| `WF-ARC-0110-A` | Le texte est rendu au plus près du lecteur | fin — amorcée en EP-03 | US-1420 |
| `WF-DAT-0120-A` | Contenu et purge du stockage objet | fin — amorcée en EP-03 | US-1420, US-1430 |
| `WF-DAT-0150-A` | Écritures concurrentes | entière | US-1380 |
| `WF-INTF-0040-A` | Imports MS Project | début — close en EP-07 | US-1430 |
| `WF-INTF-0050-A` | Exports MS Project | début — close en EP-07 | US-1430 |
| `WF-INTF-0060-A` | Réversibilité de l’échange MS Project | début — close en EP-07 | US-1430 |
| `WF-QUA-0080-A` | Corpus de plannings de référence et schéma d’échange | entière | US-1430 |
| `WF-PLA-0110-A` | Vue en arborescence de tâches | entière | US-1440 |
| `WF-PLA-0120-A` | Export de l’arborescence de tâches | entière | US-1440 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | début — close en EP-08, amorcée aussi en EP-02 | US-1450 |
| `WF-PRJ-0030-A` | Squelette de planning | fin — amorcée en EP-15 | US-1460 |
| `WF-PLA-0080-A` | Grille de planning | fin — amorcée en EP-15 | US-1470 |
| `WF-PLA-0090-A` | Diagramme de Gantt | fin — amorcée en EP-15 | US-1470 |
| `WF-ADM-0110-A` | Évaluation d’une action | fin — amorcée en EP-03, EP-04 | US-1470 |
| `WF-INTF-0010-A` | Usages du chef de projet | début — close en EP-08 | US-1470 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04 | US-1480 |

WF-PLA-0080 et WF-PLA-0090 sont partiels avant cet EPIC : l'arbre pliable des grilles et le pliage
commun de la grille et du Gantt sont faits par EP-02/L40, dans la maquette, sans qu'aucune US
d'EP-02 les cite. Ils se closent ici : EP-06 les vérifie en entier, sur le service, et
garde la saisie, le menu contextuel des cellules et le branchement des commandes.

## Opérations du contrat

Servies ici pour la première fois (27) :

- `system` : `getBackgroundTaskResult` (US-1430) ;
- `projects` : `listTimelines`, `createTimeline`, `deleteTimeline` (US-1400) ;
- `revisions` : `listNodes`, `createNode`, `deleteNode`, `moveNodes`, `updateTaskFacet`,
  `resolveRowNumber`, `getComputedValueDependencies` (US-1380) ; `setPredecessors`,
  `updateCostStructure` (US-1390) ; `setNodeTracking` (US-1400) ; `setTaskProgress` (US-1410) ;
  `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo` (US-1450) ;
  `generatePlanningSkeleton` (US-1460) ;
- `exchanges` : `uploadFile`, `listImports`, `openImport`, `getImport`, `abandonImport`,
  `applyImport` (US-1420) ; `requestExport` (US-1430, US-1440).

`uploadFile` n'est pas servie par EP-03, qui ne sert que le dépôt par morceaux d'une sauvegarde
(`openChunkedUpload`, `uploadChunk`, `completeChunkedUpload`, qui restent d'EP-03) : le dépôt
d'un fichier d'import commence ici. `updateCostStructure` et `resolveRowNumber` n'étaient
rattachées à aucun EPIC du back ; elles sont d'EP-06 (cadrage du 2026-11-07). Les opérations
servies par EP-04 et EP-05 que les écrans de cet EPIC lisent — `getRevision`,
`listCostStructures`, `getWorkBreakdown`, `getDurationUnits`, `getBackgroundTask` — ne changent
pas.

## Préalables

`epic/EP-06` se tire d'`epic/EP-04` dès l'ouverture des issues, sans attendre la livraison
d'EP-04, dont il ne reste qu'US-0990/L2 à fusionner (décision de l'auteur du 2026-11-07, pour
toute la série EP-06 → EP-07 → EP-09 → EP-10 → EP-08 ; l'exception du README, « Branches ») :
elle reprend `epic/EP-04` à chaque lot que celui-ci fusionne et se fusionne dans `main` après
elle. Ce qu'EP-06 suppose d'EP-04 est déjà fusionné : les tables `revision` et `cost_structure`,
le registre `core/revisions` et ses points d'extension (`register_copy`,
`register_tasks_and_lines`), l'évaluation à deux termes (`RequiresProject`), le chargeur par
tranches et sa chronologie, le projet `shared` et la fixture `mode.ts`.

EP-16 livré, le contrat figé en 1.0.0 : un écart devient une « Interface contract issue » que
l'auteur tranche.

Le corpus de plannings de référence (WF-QUA-0080) est fourni par l'auteur, avant le lot du
format MS Project : des fichiers XML enregistrés par MS Project 2013 ou plus, avec les dates que
MS Project a calculées, couvrant les cas du corps de WF-QUA-0080 et la contrainte « Pas avant
le » de WF-INTF-0040, déposés dans le répertoire que la conception nomme ; le schéma XSD de
Microsoft n'est pas versionné, un réglage le désigne et le test qui l'emploie se déclare non
exécuté sans lui (décision de l'auteur du 2026-11-07).

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.3 sont des tests qui passent (WF-QUA-0020) ;
- chaque planning du corpus de WF-QUA-0080 est daté comme MS Project l'a daté, sans MS Project,
  base ni navigateur ;
- le planning du plus gros projet du jeu de données de référence s'affiche en grille, en Gantt
  et en arborescence ;
- cinquante saisies de la grille s'annulent puis se rétablissent, et l'annulation d'une
  modification qu'un autre contributeur a reprise est refusée en nommant l'objet ;
- un collage depuis un tableur est prévisualisé, puis écrit les lignes collées : sur les tâches
  existantes, et, au-delà de la dernière, en créant une tâche par ligne du bloc (contrat,
  `previewPaste`, décision de l'auteur du 2026-11-08, #2559, option B) ;
- un fichier MS Project s'importe en deux temps dans la révision en cours, créée au besoin, un
  abandon laisse le projet inchangé, et un planning exporté puis réimporté ne présente aucun
  écart ;
- l'export de l'arborescence et celui d'une chronologie produisent leurs fichiers ;
- le parcours de bout en bout construit un planning contre le service réel ;
- `make check` passe sur la branche de l'EPIC, les tests du back citent leurs exigences, et aucun
  fichier de `docs/api` ne change hors d'une « Interface contract issue » tranchée.

## Constats reçus

Relevés par la revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`)
et tranchés par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), que le service
suit une fois figé.

- #1770 — `createNode` complète les heures d'une tâche datée, comme la modification (F-03 ;
  contrat #1769). US-1380.
- #1772 — une tâche refusée sous un jalon, à la création, au déplacement, à l'import et au collage
  (F-04 ; contrat #1771). US-1380 (création, déplacement), US-1430 (import), US-1450 (collage) :
  #2559 tranche pour l'option B (2026-11-08) — le collage crée les tâches des lignes du bloc au-delà
  de la dernière, par la fonction de création, qui porte le refus ; la preuve par parcours est
  d'EP-07, US-1560 (« Le collage qui crée »).
- #1790 — le cycle de vie d'un import : l'état `refused`, les conditions de l'application et de
  l'abandon, le dépôt consommé, et les conditions de l'ouverture (I-01 à I-04 ; contrat #1789,
  #1792). EP-12 ayant été abandonné, EP-06 construit le premier ce cycle. US-1420.

- #1339, pour #1304, point 7 — le service de la reprise de la spécification du 2026-10-22 (#1306, C-371 à C-375 ; #1304), dont EP-16 écrit le contrat, le faux back et les écrans (décision de l'auteur du 2026-10-22, au cadrage d'EP-16) :
  - l'import MS Project lit la description d'une tâche dans ses notes, et l'export l'y écrit
    (WF-INTF-0040, WF-INTF-0050) ;
  - l'aller-retour la restitue (WF-INTF-0060) ;
  - le contrat la porte déjà (`description` de la facette de la tâche). US-1430.
- #196 [EP-06] US-0120 : le recalcul qui suit une saisie tient la seconde du §4.6.2 — écart
  déclaré par US-0120 d'EP-02 : il n'y a pas de recalcul sur le faux back ; la mesure, contre le
  vrai service, du temps entre la validation d'une cellule de la grille (`updateEstimateLine`,
  `updateTaskFacet`) et l'application de la ligne rendue revient à EP-06, et s'écrit au relevé
  de livraison. US-1470 ; aucune optimisation sans mesure.
- #496 [EP-02] retirer les replis de `listNodes` du front — décidé pendant EP-02/L36 (#475) :
  le faux back ignore les filtres `summaries_only`, `max_level`, `timeline_id` et `kinds` de
  `listNodes`, et le front les applique aussi à la réponse. Quand le back d'EP-06, premier à
  servir `listNodes`, tiendra ces filtres et que les parcours tourneront contre lui : retirer
  ces replis, vérifier que les parcours de l'arborescence et des chronologies restent verts, et
  retirer l'écart du fichier d'EP-02. Reporté d'EP-03, qui ne sert pas `listNodes`
  (2026-10-10). US-1440 (l'arborescence), US-1400 (les chronologies).
- #620 [EP-06] `DenseGrid` ne mémorise ni ses lignes ni ses cellules — relevé par EP-02/L46 :
  chaque déplacement de la cellule active les rend toutes ; aucun défaut n'est démontré en
  production. EP-06, qui construit la grille de planning réelle, mesure contre le service avant
  toute optimisation. Reporté d'EP-14 au cadrage, retitré le 2026-10-18. US-1470 ; la mesure
  s'écrit au relevé de livraison, aucune optimisation sans elle.
- #1057 [EP-06] e2e : un geste de structure dans une grille se reporte dans l'autre, contre le
  service — relevé par l'auteur à la validation de la maquette (2026-10-18) : le report d'un
  geste de la grille de devis vers la grille de planning (Vérif de WF-DEV-0050, que EP-07 clôt),
  et Annuler et Rétablir branchés. US-1450 (Annuler et Rétablir), US-1470 (le parcours du
  report, joué sur des tâches, les lignes étant d'EP-07).

- #2485 [EP-06] contrat : une lecture de `listNodes` avec `fields` ne se valide pas contre le
  schéma `Node` — relevé par US-1380/L2 (#2335), reporté vers EP-07 puis ramené ici par
  l'utilisateur le 2026-11-08 : corrigé par `[US-1400/L3]` (#2535) (« La projection de `listNodes` »).

Reportés d'EP-04 le 2026-11-06 (relevés par la revue d'US-0960, #2061) :

- #2170 — `CostStructure.planning_start_on` n'a pas de colonne : US-0960 la dérive de la date de
  création de la structure d'origine de la lignée. EP-06 ajoute la colonne à `cost_structure`,
  la remplit par la valeur dérivée pour les lignes existantes, la reprend dans `copy_revision`,
  et sert `updateCostStructure`. US-1380 (la colonne, par le socle), US-1390 (sa saisie).
- #2180 — point 1 : les points d'extension de `core/revisions` (`register_copy`,
  `register_tasks_and_lines`, `register_indicators`) sont remplis à l'import de l'interface du
  module qui enregistre ; un processus qui ne l'importe pas a un registre incomplet sans erreur.
  EP-06, premier à enregistrer, ajoute un test qui, pour chaque point d'entrée — l'API, le
  worker, le chargeur du témoin —, vérifie que les registres portent les extensions attendues.
  Le point 2, la politique d'erreur de `compute_indicators`, est d'EP-10. US-1380.

#646 (le Kanban rend ses 960 cartes en listes simples) passe à EP-09, qui construit le Kanban
(décision de l'auteur du 2026-11-07) : il est noté dans ses « Constats reçus », et son issue est
retitrée et relabellisée à l'ouverture des issues d'EP-06.

- #2305 [EP-06] contrat : `updateProject` refuse `inflation_rate` et `win_probability` à plus de
  quatre décimales (`VALIDATION_FAILED` sans `params`, `_ratio_faults`), et le 422 du contrat ne
  décrit pas ce refus. Une « Interface contract issue » dit la précision au schéma et le refus au
  422, au lot d'EP-06 qui touche le projet ; relevé par US-0990/L2 (EP-04), reporté ici par l'auteur
  le 2026-11-07, au tableau de #2316.


## Conception

EP-06 est le troisième EPIC de domaine du back, et le premier qui écrit dans une révision : il
crée la table des nœuds et sa facette tâche, les liaisons, les chronologies et les inscriptions,
les comptes rendus d'import, l'historique annulable et le plan de collage ; trois modules du
noyau ; les routes de ses vingt-sept opérations ; trois traitements du worker et un verbe de
purge ; le moteur de dates ; la mécanique d'import en deux temps et son premier format ; la
tranche des tâches du témoin ; et il branche sur le service les écrans du planning. Il **ne
modifie pas le contrat**, figé en 1.0.0 : un manque devient une « Interface contract issue » que
l'auteur tranche — deux l'ont été, #2485 et #2559. Ce qui suit fixe ce que chaque lot devrait sinon décider seul.

### Ce que le cadrage décide

Décisions de l'auteur du 2026-11-07, sur les questions du cadrage, chacune avec l'option écartée :

- **Une seule collection de nœuds, `node`, à deux facettes** (`kind` : `task` ici,
  `estimate_line` par EP-07), comme le contrat la lit (« Arbre commun ») : l'ordre, la lignée,
  `row_number`, `position`, `moveNodes` qui mêle lignes et tâches et `after_node_id` d'un autre
  genre sont d'une seule table. La facette est une table à part, une ligne par nœud — `task`
  ici, `estimate_line` par la migration d'EP-07 —, parce qu'un module ne possède que ses tables
  (guide, « Le back et les frontières du noyau ») : `core/planning` possède `node` et `task`, le
  module du devis d'EP-07 possédera `estimate_line`. Le Tableau 10 du §4.4.1 ne nomme pas
  `node` : une issue « Specification finding », ouverte à l'ouverture des issues, demande de l'y
  ajouter, avec `undo_entry` et `paste_plan` parmi les lignes techniques. Écarté : deux tables
  `task` et `estimate_line` sans tronc commun, où `position` et `row_number` se calculent sur
  l'union, et où une sélection déplacée écrit dans les deux ; des colonnes de la facette ligne
  dans `node` même, qu'un autre module aurait écrites.
- **Sept portées recalées** (voir « Exigences réalisées »). Écarté : les clore ici avec des
  écarts, contre la règle du README.
- **Onze US, le socle en lot technique de la première**, lot pivot d'EP-07. Écarté : un socle en
  US propre sans exigence à lui.
- **Le corpus de WF-QUA-0080 est fourni par l'auteur** (« Préalables »), dans
  `fixtures/msproject/`, un fichier par cas, et le lot du format ne part pas sans lui ; le schéma
  XSD de Microsoft est désigné par la variable `WATERFALL_MSPDI_SCHEMA_PATH`, lue par le seul
  test qui l'emploie, qui se déclare non exécuté sans elle ; le lecteur et l'écrivain se prouvent
  d'abord sans lui, par l'aller-retour structurel et le schéma, et le test du corpus vient avec
  l'analyse (plan de lots). Écartés : un corpus écrit à la main
  d'après le schéma, daté par le moteur de Waterfall lui-même, qui ne confronterait rien ; le
  report de WF-QUA-0080.
- **La purge est un verbe du worker, `waterfall-worker purge`**, planifié par le service
  `scheduler` du Compose comme `enqueue identity_sync`, à l'intervalle de
  `WATERFALL_PURGE_INTERVAL` (dix minutes par défaut) ; aucun genre de tâche de fond, donc aucun
  changement du contrat, et l'état d'un import se juge aussi à la lecture. Écartés : une
  expiration paresseuse qui ne supprimerait aucun fichier sans passage ; la purge dans la boucle
  du worker, qu'un worker arrêté ne ferait plus sans rien dire.
- **L'historique annulable et le plan de collage vivent dans PostgreSQL**, `undo_entry` et
  `paste_plan`, dans la transaction de la saisie qu'ils gardent. Écarté : Redis, que le §4.4.5
  réserve au cache et à la session du front, et qui séparerait la saisie de son entrée.
- **`setTaskProgress` est servie ici, sans écran** ; le Kanban d'EP-09 ne fait que brancher.
  Écarté : la reporter à EP-09, et poser les états du témoin et des tests autour du service.
- **WF-QUA-0040 entre au tableau** pour la tranche des tâches. Écarté : une US du témoin sans
  exigence propre.
- **La bibliothèque XML est `lxml`** : WF-QUA-0080 exige la validation contre le XSD, que la
  bibliothèque standard ne sait pas faire, et `defusedxml.lxml` est déprécié. Un fichier déposé
  par un utilisateur se lit par un analyseur durci — `resolve_entities=False`, `no_network=True`,
  `huge_tree=False`, `load_dtd=False` —, écrit une fois dans `core/exchanges` et employé par tout
  format XML ; le relecteur Python le cherche. Écarté : `xml.etree` et `defusedxml`, sans
  validation.
- **L'image de l'arborescence est dessinée par Pillow**, avec une police embarquée dans le
  dépôt — DejaVu Sans, `backend/src/waterfall/core/exchanges/fonts/`, sa licence déclarée dans
  `REUSE.toml` et `LICENSES/` — pour que l'image ne dépende pas des polices de l'image Docker du
  worker. Écarté : une bibliothèque de rendu vectoriel (Cairo), qui demande des paquets système.
- **Les fichiers en transit et les exports vivent dans le compartiment déjà réglé**
  (`backups_bucket`), sous les préfixes `uploads/` — celui d'EP-03 — et `exports/` : les « trois
  compartiments » de WF-DAT-0120 sont lus comme trois préfixes aux règles de disparition
  distinctes, comme EP-03 l'a déjà fait pour `uploads/` ; la « Specification finding » de l'EPIC
  fixe cette lecture d'une phrase, pour qu'aucun relecteur ne la rouvre. Rien ne change au script
  qui crée les compartiments ; le Compose, lui, change pour la purge (ci-dessous). Écarté : trois
  compartiments S3 et trois réglages.
- **Le recalcul au changement des unités de durée ou du calendrier par défaut est fait dans la
  transaction de l'écriture du référentiel**, pour toutes les structures des révisions en cours :
  trois cents projets de mille tâches au plus (§4.6.2), un acte d'administration rare, sous la
  permission d'écriture du référentiel, borné par le verrou de l'objet écrit ; `scheduled_at` de
  chaque structure avance. L'ordre des verrous est fixé : le référentiel d'abord (l'objet écrit,
  puis le verrou consultatif de sa règle), puis chaque `cost_structure` `FOR UPDATE` dans l'ordre
  stable de (`project_id`, `id`) ; une saisie du planning ne verrouille jamais le référentiel,
  qu'elle lit sans verrou, et prend sa structure seule — aucun interblocage possible, la saisie
  attendant le recalcul ou l'inverse. Écarté : un recalcul paresseux à la lecture suivante, par comparaison
  de `scheduled_at` à l'instant du changement, qui ferait écrire une lecture et dater une structure
  sous `FOR UPDATE` dans un `GET`.
- **Une seule chaîne de migrations pour EP-06, dans le socle**, `0022` le schéma et `0023` les
  données (`planning_start_on` remplie), aux prochains numéros libres à la création
  d'`epic/EP-06` — `epic/EP-04` est à `0021` ; aucun lot d'EP-06 n'écrit de migration après le
  socle, et EP-07 chaîne la sienne sur `0023`, sans révision de fusion. Écarté : une migration par
  US, qui donnerait deux têtes à la fusion d'EP-07.
- **La tranche des tâches s'insère dans la chronologie d'EP-04 par un registre du chargeur** :
  `witness/revisions.py` offre `register_revision_filler`, et appelle chaque remplisseur
  enregistré après l'ouverture d'une révision et avant l'événement suivant ; la tranche des
  tâches remplit ainsi les révisions 100, 101 et 102 avant leur marquage, par la réconciliation
  de leur contenu décrit avec ce que la copie leur a donné. Écarté : une tranche après celle des
  projets, qui ne pourrait plus écrire dans une révision marquée.

### Tables et migrations

Régime « révisionné » (§4.4.1), partitionnées par projet comme `cost_structure`, pour `node`,
`task` et `task_link` ; régime « projet » pour `timeline`, `tracking_entry` et `import_report` ;
lignes techniques pour `undo_entry` et `paste_plan`. UUID v7 engendrés par le service, ou
imposés par le chargeur ; colonnes d'audit et `lock_version` sur chaque table dont les lignes se
modifient ; textes triés en collation `C` ; règles SQL du guide pour le reste. Chaque clé refuse
(`RESTRICT`), sauf à l'intérieur d'une révision en cours, où le §4.4.1 autorise la cascade et où
elle évite un oubli à chaque chemin de suppression : la facette `task` suit son nœud, une liaison
suit l'une ou l'autre de ses tâches, un nœud suit sa structure et son parent, une inscription suit
sa chronologie ; une révision marquée ne supprime rien, ses déclencheurs d'immuabilité le
refusant avant toute cascade. L'abandon d'une révision pleine (EP-04, `delete_structures`)
supprime donc ses nœuds avec ses structures, et un test l'éprouve.

| Table | Contenu | Contraintes |
|---|---|---|
| `node` | `project_id` (clé de partition), `id`, `revision_id`, `structure_id`, `lineage_id`, `kind`, `parent_id`, `rank`, `origin_risk_id` (nul ici, posé par EP-08), audit, `lock_version` | clé primaire (`project_id`, `id`) et unique (`project_id`, `id`, `kind`), que la facette cite ; `kind` dans `task`, `estimate_line` ; clé composite vers `cost_structure` et vers `node` (le parent, du même projet, nul pour une racine), toutes deux en cascade ; `rank` entier ≥ 1, unique sous (`structure_id`, `parent_id`, `kind`) par `UNIQUE NULLS NOT DISTINCT` — les racines, `parent_id` nul, comprises —, renuméroté parmi ses frères à chaque écriture — les lignes d'une tâche précèdent ses sous-tâches à la lecture, `position` et `row_number` calculés ; le parent d'une ligne est une tâche, celui d'une tâche jamais un jalon ni une ligne : tenu par le service, sous le verrou de la structure ; déclencheur d'immuabilité comme `cost_structure` |
| `task` | `project_id`, `node_id` (clé primaire avec lui), `kind` (`CHECK (kind = 'task')`, clé composite (`project_id`, `node_id`, `kind`) vers `node` en cascade : un nœud `task` ne reçoit jamais une autre facette, sans que le service y veille ; « exactement une facette par nœud » reste au service, dans la transaction de la création), `label`, `description`, `scheduling_mode`, `duration_value` (`numeric`), `duration_unit`, `start_date`, `start_hours`, `finish_date`, `finish_hours`, `progress`, `started_on`, `completed_on`, `external_id`, `order_item_id`, `work_package_id`, `total_float_days` (`numeric`, nul en manuel), `is_critical` | `label` de 1 à 300 non blanc ; `scheduling_mode` dans `automatic`, `manual` ; `duration_unit` dans les dix unités de `DurationUnit` ; `duration_value` ≥ 0 ; `progress` dans les trois états ; `started_on` non nul si `progress` ≠ `not_started`, `completed_on` non nul si et seulement si `completed` ; `external_id` de 200 au plus ; `order_item_id` et `work_package_id` clés en refus, jamais tous deux non nuls ; un poste ou un lot porté par un seul nœud par structure (index unique partiel) ; les dates calculées sont conservées — une révision marquée garde les siennes —, l'instant du calcul étant celui de la structure (`cost_structure.scheduled_at`, que `NodeListMeta` lit) ; déclencheur d'immuabilité |
| `task_link` | `project_id`, `id`, `revision_id`, `structure_id`, `predecessor_id`, `successor_id`, `link_type`, `lag_value`, `lag_unit`, `in_conflict` | clés composites vers `node` en cascade — la liaison suit l'une ou l'autre de ses tâches — ; `predecessor_id <> successor_id` ; unique (`structure_id`, `predecessor_id`, `successor_id`) — « deux tâches ne sont reliées que par une liaison au plus » — ; `link_type` dans les quatre types, `lag_unit` dans les onze unités de `LagUnit` ; l'absence de boucle et de liaison récapitulative–subordonnée est tenue par le service ; déclencheur d'immuabilité |
| `cost_structure` | reçoit `planning_start_on` (`date`, nulle : le jour de la création de l'origine de la lignée, que le code calcule encore ; remplie par `0023` ; #2170) et `scheduled_at` (`timestamptz`, nul : l'instant de création) | aucune autre contrainte ; `copy_revision` reprend les deux |
| `timeline` | `id`, `project_id`, `label`, audit | `label` de 1 à 200 non blanc, non unique ; clé vers `project` en refus ; supprimée physiquement |
| `tracking_entry` | `id`, `project_id`, `lineage_id` (la lignée de la tâche), `kind` (`timeline`, `milestone_tracking`), `timeline_id` (nul pour `milestone_tracking`), audit | unique (`lineage_id`, `kind`, `timeline_id`) par `UNIQUE NULLS NOT DISTINCT` — une seule inscription au suivi temps/temps par lignée, `timeline_id` nul — ; clé vers `timeline` en cascade — une chronologie supprimée emporte ses inscriptions — ; `timeline_id` non nul si et seulement si `kind = timeline` |
| `import_report` | `id`, `project_id`, `kind` (`ExchangeKind`), `filename`, `upload_id`, `object_key`, `structure_id`, `revision_id`, `period_from`, `period_to`, `status`, `report` (`jsonb`, codes et paramètres), `task_id` (la dernière tâche de fond), `requested_by`, `created_at`, `analysed_at`, `expires_at`, `applied_at` | `status` dans les huit valeurs d'`Import.status` ; `expires_at` non nul si et seulement si `analysed`, `applying`, `applied`, `abandoned` ou `expired` ; `report` objet ou nul ; clé vers `project` en refus ; `upload_id` unique — un dépôt ne sert qu'un import — |
| `undo_entry` | `id`, `project_id`, `revision_id`, `user_account_id`, `session_id` (le `sid` du jeton), `rank`, `kind` (`UndoneKind`), `node_ids`, `before`, `after` (`jsonb` : les lignes de `node`, `task`, `task_link` et `tracking_entry` touchées, telles qu'elles étaient et telles qu'elles sont), `undone`, `created_at` | unique (`revision_id`, `user_account_id`, `session_id`, `rank`) ; clé vers `revision` en refus — le marquage et l'abandon suppriment les entrées d'abord — |
| `paste_plan` | `id`, `project_id`, `revision_id`, `structure_id`, `user_account_id`, `target_node_id`, `target_column`, `rows` (`jsonb`), `structure_lock_version`, `created_at`, `expires_at` | une heure de vie ; clé vers `revision` en refus |

- **Deux migrations, toutes deux dans le socle** (US-1380/L1), aux numéros `0022` et `0023` —
  les prochains libres à la création d'`epic/EP-06`, à relire alors : `0022` crée les huit tables,
  les deux colonnes de `cost_structure`, remplace `create_project_partitions` pour qu'elle crée
  les partitions de `node`, `task` et `task_link` et crée celles des projets existants, pose les
  déclencheurs d'immuabilité de ces trois tables sur le modèle de `cost_structure`, accorde les
  droits du rôle du service — `SELECT`, `INSERT`, `UPDATE`, `DELETE` sur les huit tables : le
  contenu d'une révision en cours, une chronologie, une inscription, un plan et une entrée
  d'historique se suppriment physiquement, un compte rendu à son expiration ou à l'abandon
  (§4.4.1) — et les déclare dans `SERVICE_RIGHTS` ; `0023` remplit `planning_start_on` de chaque structure par la date de
  création de l'origine de sa lignée, et `scheduled_at` par la date de création de la structure,
  comme le code les dérive aujourd'hui (règle 3 des migrations, « une donnée change dans sa propre
  migration »). Les deux colonnes restent nullables (règle 1) : le code lit un nul comme la valeur
  dérivée. **Aucune migration d'EP-06 après le socle** ; EP-07 chaîne la sienne sur `0023`.
- **La partition** : `node_p_<uuid>`, `task_p_<uuid>`, `task_link_p_<uuid>`, par la fonction
  remplacée (`CREATE OR REPLACE`), avec leur déclencheur de `TRUNCATE` ; la migration crée les
  partitions des projets existants en lisant `project`.
- **L'immuabilité** : une fonction de déclencheur par table révisionnée, dans le module
  `planning`, qui lit l'état de la révision par `revision_id` sous `FOR KEY SHARE`, propriétaire
  compris, comme `cost_structure_refuse_marked_change`.
- Les tests : `test_migrations.py` (schéma, droits, partitions d'un projet créé),
  `test_database_constraints.py` (une contrainte, un test), `test_revision_immutability.py`
  étendu aux trois tables.

### Modules

| Module | Tables | Interface offerte |
|---|---|---|
| `waterfall.core.planning` (FBS-4.3) | `node`, `task`, `task_link`, `timeline`, `tracking_entry` | les nœuds lus (`listNodes` : filtres, `fields`, recherche, `row_number`, `summary_depth`, `scheduled_at`, totaux), une tâche créée, modifiée, supprimée, des nœuds déplacés, un numéro résolu, les dépendances d'une valeur calculée ; les prédécesseurs remplacés ; la date de début et le libellé d'une structure écrits ; l'état d'une tâche ; les chronologies et les inscriptions ; le squelette ; le moteur (`scheduling`, pur) et `reschedule(structure)` ; `revision_has_tasks(revision_id)` ; `copy_nodes(RevisionCopy)` ; `work_breakdown_item_cited(item_id)` et `detach_work_breakdown_item(project_id, item_id)` pour `core/projects` ; `tasks_left_idle(calendar…)` et `reschedule_current_structures()` pour `resource_settings` ; `lines_of(task)` et les règles de placement qu'EP-07 appelle pour une ligne ; `register_facet(kind, FacetHooks)`, par lequel EP-07 enregistre la lecture, la copie et la suppression de sa facette ; `load_*` avec identifiants et instants imposés |
| `waterfall.core.history` (WF-IHM-0110, WF-IHM-0050) | `undo_entry`, `paste_plan` | `recording(session, change)` — un encadrement de l'écriture : `planning` lui donne, par son interface, l'instantané des nœuds touchés avant l'écriture puis après elle (`snapshot(node_ids)`), et `history` les garde sans lire aucune table d'un autre module — ; `undo(revision, actor)`, `redo(revision, actor)`, chacun rendant les nœuds à restituer que `planning` réécrit et redate ; `depth(revision, actor)` ; `close_history(revision_id)` pour le marquage et l'abandon ; `keep_plan`, `read_plan`, `drop_plan` ; `purge(before)` |
| `waterfall.core.exchanges` (FBS-4.3.4, FLX-01 à FLX-07) | `import_report` | `register_format(ExchangeKind, Format)` et `register_exporter(ExportKind, Exporter)` ; le dépôt d'un fichier d'import (`deposit`), l'ouverture (`open_import` : l'en-tête par le format, les conditions, la tâche d'analyse), la lecture et la liste, l'abandon, l'application (`apply_import` : la revérification, la tâche) ; `run_analysis(task)`, `run_apply(task)`, `run_export(task)` pour le worker ; `result_of(task)` pour `getBackgroundTaskResult` et `consumed(task)` ; `purge(now)` : imports échus, dépôts expirés, exports échus ; l'analyseur XML durci, pour tout format XML |

- **Le moteur** (`core/planning/scheduling/`) est pur : il reçoit une structure — les tâches
  (identifiant, parent, mode, durée et unité, dates manuelles, heures hebdomadaires de leur
  calendrier applicable), les liaisons, la date de début de planning, les constantes d'unités —
  et rend pour chaque tâche son début et sa fin (`WorkInstant`), sa marge totale en jours, sa
  criticité, les liaisons en conflit, et la tâche qui porterait la fin au-delà de quinze ans. Il
  compte en heures de travail sur le calendrier de chaque tâche, les durées et décalages
  convertis par les constantes, les décalages écoulés sur vingt-quatre heures dont les heures
  travaillées occupent les premières positions (WF-PLA-0160) ; une tâche manuelle est une date
  imposée qui borne ses voisines (WF-PLA-0100) ; une récapitulative couvre ses subordonnées, et
  porte la plus petite marge de celles qui en portent. Il refuse une boucle et une liaison entre
  une récapitulative et sa subordonnée en nommant la chaîne la plus courte, au plus près du
  contrat. Les tests des Vérif et le corpus l'éprouvent sans base.
- **Chaque écriture de nœud** se fait sous le verrou de la structure (`cost_structure` `FOR
  UPDATE`, après celui de la révision quand elle juge `revision_draft`), appelle le moteur sur la
  structure entière, écrit les dates et les marges qui changent, avance `scheduled_at`, inscrit
  son entrée d'historique (`history.record`), et rend `NodesWritten` — `rescheduled` les tâches
  dont le calendrier a changé, `ancestors` les récapitulatives recalculées, `reinflated` vide
  jusqu'à EP-07.
- **Le calendrier applicable** d'une tâche est, ici, le calendrier par défaut : `planning`
  demande à `resource_settings` le calendrier par défaut et offre `register_facet` à EP-07, qui
  lui donnera les calendriers des rôles de ses lignes et leur intersection, par la même fonction
  `calendar_of(task)`.
- **Les commandes** de la révision, des structures, du projet et de l'import se calculent par les
  mêmes fonctions que les refus 409, dans l'ordre du contrat ; `generate_skeleton`,
  `manage_timelines`, `export_planning`, `export_task_tree_image` et `edit_planning` sont ajoutées
  par `planning` aux commandes qu'EP-04 rend, par les fonctions que `core/projects` et
  `core/revisions` lui exposent déjà ou qu'il complète.

### Les points d'extension

EP-06 est le premier EPIC à remplir ceux d'EP-04 et à créer ceux qu'EP-05 a laissés en
promesse ; chacun est un registre ordonné sur le modèle de `core/revisions/registry.py`, rempli à
l'import de l'interface du module qui enregistre, et le test des points d'entrée de #2180 les
couvre tous : pour chaque processus — l'API (`create_app`), le worker (`handlers`), le chargeur
(`load_witness`) — et chaque registre, les extensions attendues sont présentes.

| Module | Registre | Qui le remplit | Ce qu'il fait |
|---|---|---|---|
| `core/revisions` | `register_copy` (EP-04) | `planning` (les nœuds, leur facette tâche, les liaisons, après les structures) ; EP-07 (la facette ligne, les images) | `copy_revision` |
| `core/revisions` | `register_tasks_and_lines` (EP-04) | `planning` (`revision_has_tasks`) ; EP-07 (les lignes) | la désignation de la référence |
| `core/revisions` | `register_closing` (nouveau, créé par le socle) | `history` (`close_history`), puis `planning` (`delete_nodes`, à l'abandon seul, dès le lot qui crée des nœuds) | le crochet commun du marquage et de l'abandon, appelé avant que la révision ne s'écrive, chaque module y faisant sa part dans l'ordre de l'enregistrement — l'historique et les plans d'abord, puis les nœuds, puis les structures d'EP-04 (`delete_structures`) : l'abandon d'une révision pleine ne laisse aucune ligne (WF-DAT-0010) ; la cascade des clés tient le même ordre si un chemin l'oublie |
| `core/resource_settings` | `register_idle_task_guard` (nouveau ; remplace le `True` de `calendar_change_is_admissible`) | `planning` (`tasks_left_idle` : les projets dont une tâche d'une révision en cours n'aurait plus aucune heure dans la semaine) | `updateCalendar`, `setDefaultCalendar`, `updateResourceRole` refusent par `TASK_WITHOUT_WORKING_HOURS`, `params.projects` ; ici le calendrier par défaut, EP-07 les rôles |
| `core/resource_settings` | `register_recalculation` (nouveau) | `planning` (`reschedule_current_structures`) | `set_duration_units` et l'écriture d'un calendrier redatent, dans leur transaction, les structures des révisions en cours |
| `core/projects` | `register_attachments` (nouveau) | `planning` (`work_breakdown_item_cited`, `detach_work_breakdown_item`) | `set_work_breakdown` marque supprimé un lot ou un poste qu'une tâche d'une révision marquée porte (`deleted_at`), le supprime sinon, et retire le rattachement des tâches de la révision en cours ; `follow_project_label` ne change pas |
| `core/planning` | `register_facet` (nouveau) | EP-07 (`estimate_line`) | `listNodes` rend la facette, la copie et la suppression d'un nœud l'emportent, `calendar_of` lit ses rôles |
| `core/exchanges` | `register_format`, `register_exporter` (nouveaux) | `planning` (`ms_project_schedule`, `task_tree_image`) ; EP-07, EP-09 | l'ouverture, l'analyse, l'application et l'export d'une nature |
| `witness/revisions` | `register_revision_filler` (nouveau) | `witness/tasks` ; EP-07 | le contenu d'une révision écrit entre son ouverture et l'événement suivant |

### L'import en deux temps et les formats

- **Un format** est un objet qui sait trois choses : lire l'en-tête d'un fichier déposé et dire
  s'il le reconnaît (`FILE_FORMAT_UNREADABLE`, `expected_format`, `expected_version`) ;
  analyser le fichier contre la structure visée et produire un `ImportReport` en codes, sans rien
  écrire ; appliquer un compte rendu à la structure, dans la transaction de la tâche, en rejugeant
  ce que l'analyse acceptait. `exchanges` ne connaît aucun format : il résout celui de `kind`
  dans son registre, et ne lit du fichier que ce que le format lui demande.
- **Le dépôt** (`uploadFile`) écrit l'objet sous `uploads/<upload_id>` et une ligne de
  `file_upload` (EP-03, `purpose: import`, `completed_at` posé, sans morceaux — la table admet un
  dépôt d'une seule pièce : `part_count` à 1, `part_size_bytes` à la borne), vingt-quatre heures
  de vie ; 413 au-delà de 10 Mio, 422 pour `external_backup`.
- **L'ouverture** juge, dans l'ordre du contrat, `project_not_terminal`, le dépôt (404 inconnu,
  expiré ou déjà employé — `import_report.upload_id` unique), l'usage (422
  `UPLOAD_PURPOSE_MISMATCH`), la structure (404), `no_background_task_running`,
  `may_create_revision`, puis lit l'en-tête par le format, écrit la ligne `analysing` et dépose
  `import_analysis` dans la transaction, sous le verrou du projet.
- **L'analyse** (worker) lit le fichier du stockage en flux, appelle le format sur la structure
  visée — celle de la révision en cours, ou de la dernière marquée quand l'application créera la
  révision —, écrit le compte rendu et `expires_at` à vingt-quatre heures, passe `analysed` ; une
  exception typée passe l'import `failed`, le fichier supprimé.
- **L'application** (`applyImport`) revérifie la permission et la qualité de contributeur de
  l'appelant, l'état de l'import (`import_awaiting_decision`, `import_file_accepted`), puis les
  conditions de l'ouverture, et dépose `import_apply` ; refusée par l'une d'elles, elle passe
  l'import `refused` et supprime le fichier (#1790). Le worker, dans la transaction de la tâche,
  revérifie de nouveau, crée la révision en cours au besoin par `create_revision` (EP-04),
  applique par le format sous le verrou de la structure, redate, passe `applied`, supprime le
  fichier, et l'historique annulable ne reçoit rien (WF-IHM-0110). Une tâche en file ou en cours
  qui vise le projet rend `no_background_task_running` manquante aux autres écritures (EP-04).
- **L'expiration** se juge à la lecture (`analysed` dont `expires_at` est passé se lit
  `expired`, et `apply` le refuse) et s'écrit par la purge.
- **Le compte rendu** est conservé en codes et paramètres (`ImportReport` tel que le contrat le
  lit) ; l'écran le rend par son catalogue (WF-ARC-0110).

### Le format MS Project

- **Lecture** : XML MSPDI (`Project`, `Tasks/Task`, `PredecessorLink`, `Calendars`,
  `Resources`, `Assignments`, `ExtendedAttributes`), par l'analyseur durci de `exchanges`, en un
  modèle en mémoire (`core/planning/msproject/model.py`) sans base : l'arbre par `OutlineLevel` et
  l'ordre du fichier, le libellé, les notes (la description, C-375), `Manual`, `Duration` et son
  format (unité et temps écoulé), `Start`/`Finish`, `Milestone`, `ConstraintType`, les liaisons
  (`Type`, `LinkLag`, `LagFormat`), `StartDate` du projet, `MinutesPerDay`, `MinutesPerWeek`,
  `DaysPerMonth`, et `GUID` ou un champ étendu `Waterfall.lineage` pour la lignée que l'export
  écrit ; `UID` conservé comme `external_id`. Ce que le fichier porte en plus est compté dans
  `ignored` par nature.
- **Analyse** : rapprochement par la lignée, puis par `external_id` ; les tâches sans
  identifiant créées, les absentes supprimées selon WF-PLA-0070 (démarrées et terminées `kept`) ;
  les liaisons remplacées et leurs écarts présentés ; une récapitulative manuelle importée en
  automatique (`SUMMARY_TASK_DERIVED` dans `signals`) ; une date manuelle chômée gardée et
  signalée (`NON_WORKING_DAY`) ; une tâche sous un jalon rejetée (`MILESTONE_HAS_NO_SUBTASK`) ;
  la date de début du projet comparée à `planning_start_on` (écart `cost_structure`) ; les
  constantes d'unités du fichier converties en heures et leur différence signalée par
  `ImportReport.unit_constants` (#2580, « Les constats des lots livrés ») ; le moteur
  rejoué sur la structure résultante pour `date_mismatches`, `PROJECT_HORIZON_EXCEEDED` et
  `ORDER_ITEM_OUTSIDE_WORK_PACKAGE` (`refusals`) ; les ressources, calendriers, avancement, coûts,
  champs personnalisés et contraintes ignorés et nommés.
- **Export** : le worker écrit le XML — `StartDate` à `planning_start_on`, les constantes
  d'unités, un calendrier de projet et un calendrier de tâche par calendrier applicable distinct
  (`calendar_hours`), chaque tâche avec `UID`, `OutlineLevel`, `Name`, `Notes` (la description),
  `Manual`, `Duration` dans son unité, `Start`, `Finish`, `Milestone`, `CalendarUID`, sa lignée
  en `GUID`, les `PredecessorLink` avec `Type`, `LinkLag`, `LagFormat` —, dans l'ordre du schéma,
  et le dépose sous `exports/<task_id>.xml`.
- **Le corpus** : `fixtures/msproject/*.xml`, un test par fichier qui le lit, donne au moteur
  les calendriers du fichier, et compare chaque début et chaque fin à ceux du fichier ; un test
  qui liste les cas du corps et nomme ceux qu'aucun fichier ne porte ; un test de validation de
  l'export contre le XSD, non exécuté sans `WATERFALL_MSPDI_SCHEMA_PATH`.

### Les exports

- `requestExport` dépose une tâche `export` (202), gardée par la commande `export_*` de la
  révision — présente ou absente, sans condition — ; le worker appelle l'exporteur de `kind`,
  qui rend le fichier, son type et son nom, déposés sous `exports/<task_id>.<ext>` ; la tâche
  réussit avec un résultat `{object_key, filename, media_type}`, et `result_url` de la tâche est
  la route de `getBackgroundTaskResult` : US-1430 étend `result_url` dans `api/tasks.py` pour les
  tâches `export` réussies et consommées, et corrige le commentaire qui l'attendait d'EP-07 ; une
  seule US de l'EPIC touche ce fichier.
- `getBackgroundTaskResult` répond 409 `task_succeeded` avant l'aboutissement, transmet le
  fichier en flux (`Content-Disposition`, `filename*` en UTF-8), et, une fois le dernier octet
  envoyé, supprime l'objet et marque le résultat consommé (`result_url` nul, 404 ensuite) ; un
  flux interrompu laisse l'objet. La purge supprime les exports de plus de vingt-quatre heures.
- L'image de l'arborescence : Pillow, la police embarquée, le premier niveau à l'horizontale et
  les suivants à la verticale sous leur parent, l'image à la taille de son contenu, un en-tête
  — le projet, la révision, la date de calcul — dans la langue du compte demandeur, par un petit
  catalogue du back à deux langues (WF-ARC-0110).

### L'historique annulable et le collage

- **Une entrée par saisie**, écrite dans la transaction de la saisie par `history.recording`, un
  encadrement que chaque écriture de `planning` ouvre avant d'écrire et ferme après : des deux
  côtés, `planning` prend lui-même l'instantané des nœuds qu'elle crée, modifie ou supprime — leurs
  lignes de `node`, `task`, `task_link` et `tracking_entry`, par sa fonction `snapshot` — et le
  donne à `history`, qui le garde en JSONB sans lire aucune table de `planning` (guide, « les
  modules du noyau ne se lisent que par leur interface »). La pile est par révision, par
  compte et par session de connexion : le `sid` du jeton d'accès, que `platform/keycloak.py`
  ajoute à `Bearer` (il ne lit aujourd'hui que `sub` et `auth_time`) et que `Caller` porte — il
  survit aux rafraîchissements du jeton, toutes les cinq minutes, qui videraient une pile liée au
  jeton lui-même. Une saisie nouvelle supprime les entrées défaites de la pile.
- **L'annulation** lit la dernière entrée non défaite, vérifie que chaque nœud d'`after` est
  toujours à sa version — sinon 409 `UNDO_CONFLICT`, l'objet repris nommé —, restitue `before`
  (lignes recréées, modifiées ou supprimées) sous les règles de la saisie, redate la structure,
  marque l'entrée défaite et rend `UndoResult` avec `NodesWritten` ; le rétablissement fait de
  même avec `after`. Au moins cinquante entrées par pile ; le marquage et l'abandon
  (`register_closing`) les suppriment ; la purge retire celles d'une session de plus de
  `WATERFALL_UNDO_RETENTION_HOURS`, douze par défaut — la durée maximale d'une session du royaume
  (`ssoSessionMaxLifespan: 43200`, deux heures d'inactivité). Écart assumé : une pile survit à la
  fin de sa session jusqu'au passage de la purge, le serveur n'apprenant pas la fin d'une session
  de Keycloak ; aucune requête ne la lit plus, son `sid` étant mort, et aucun Vérif ne l'éprouve.
- **Le collage** : `previewPaste` juge chaque cellule du bloc sur la facette tâche dans l'ordre
  de `NodeColumn` par les mêmes fonctions que la saisie d'une cellule, garde le plan dans
  `paste_plan` avec le compteur de la structure, et rend `PastePlan` ; `applyPaste` relit le plan,
  refuse par 412 une structure qui a bougé, rejuge, écrit les lignes acceptées en une opération et
  une seule entrée d'historique (`paste`), et rend `PasteApplied`. Les lignes du bloc au-delà du dernier nœud créent des tâches (ci-dessous,
« Le collage qui crée »).

### La purge

`waterfall-worker purge` : sous un verrou consultatif de transaction, il passe `expired` les
imports `analysed` échus et supprime leur fichier, supprime les dépôts de `file_upload` échus et
leur objet — ceux d'EP-03 compris, par morceaux inachevés —, supprime les objets des exports
réussis de plus de vingt-quatre heures et marque leur résultat consommé, retire les plans de
collage échus et les entrées d'historique des sessions anciennes ; chaque suppression du stockage
hors transaction, après la validation, comme EP-03 fait ses dépôts. Le service `scheduler` du
Compose de service et de celui de production reçoit une seconde boucle, qui l'appelle à
l'intervalle de `WATERFALL_PURGE_INTERVAL` (600 s), la variable passée par les deux Compose et
`production.env.example` ; `make service-purge` pour la main. C'est la seule modification du Compose
de l'EPIC.

### Le service d'API

- Un routeur par US — `api/nodes.py` (US-1380), `api/scheduling.py` (US-1390 : `setPredecessors`,
  `updateCostStructure`), `api/timelines.py` (US-1400), `api/progress.py` (US-1410),
  `api/imports.py` (US-1420, `uploadFile` compris), `api/exports.py` (US-1430, US-1440 :
  `requestExport`, `getBackgroundTaskResult`), `api/history.py` (US-1450), `api/skeleton.py`
  (US-1460) —, créés vides et enregistrés dans `app.py` par le socle, chacun rempli par son US ;
  chaque routeur a son fichier `asked_*.py` de la table des permissions et des qualités.
- Chaque route d'un projet déclare `RequiresProject(...)` : la consultation (`planning.read`) pour
  les lectures ; la qualité de contributeur et `planning.write` pour les écritures du planning,
  `remaining.write` pour `setTaskProgress`, `planning.write` pour les imports de planning et les
  chronologies, la permission de consulter la nature pour un export ; `getBackgroundTaskResult`
  lit la tâche du seul appelant, comme `getBackgroundTask`.
- Les refus sont ceux du contrat, code par code, dans l'ordre que chaque opération écrit ; chaque
  réponse d'un test passe par `ContractClient` ; `test_access_evaluation.py` reçoit chaque
  opération avec ses deux termes.

### Le worker

Trois gestionnaires enregistrés dans `handlers` par le socle — `import_analysis`,
`import_apply`, `export` — dans `worker/exchanges.py`, qui appellent l'interface de `exchanges` ;
une tâche échoue avec le code de son exception typée, rien n'étant écrit ; le verbe `purge` dans
`worker/main.py`. Le worker importe l'interface de `planning` pour que les registres soient
remplis (#2180).

### Le chargeur du témoin

- **Un lot d'outil**, `make mock-data` écrit `fixtures/api/witness_tasks.json`, à côté de la
  chronologie : pour chaque révision de PRJ-001 (100, 101, 102), ses tâches par lignée — le
  parent par sa lignée, le rang, la facette, les liaisons, l'état et ses dates, les inscriptions
  — et la date de début de planning de la structure, depuis `wftools.mockwitness`,
  `mockstructure` et `mockhistory` ; le back le lit par un modèle propre, strict, sans importer
  `wftools`.
- **La tranche** : `witness/tasks.py` s'enregistre par `register_revision_filler` et, après
  l'ouverture d'une révision par la tranche des révisions, réconcilie par lignée les tâches que
  la copie lui a données avec celles que le fichier décrit pour cette révision — création,
  modification, suppression, liaisons, états, inscriptions — par l'interface de `planning`, aux
  identifiants et à l'instant imposés, puis laisse le marquage venir ; `witness/timelines.py`
  charge les deux chronologies de PRJ-001 dans la tranche des projets, après le lotissement et
  avant les révisions, pour que les inscriptions des tâches les trouvent.
  Les dates sont celles que le moteur calcule : le calculé devient l'attendu, et un désaccord
  avec `nodes_planning` se tranche par la spécification, la fixture corrigée.
- **Dans l'ordre d'EP-04** : la tranche des tâches ne touche ni `loader.py` ni l'ordre des
  tranches des projets ; le socle attend la fusion d'US-0990/L2 (#2069), qui écrit encore
  `witness/revisions.py`, avant d'y déclarer le registre.

### La projection de `listNodes` (décision de l'utilisateur du 2026-11-08, #2485)

La lecture d'`listNodes` avec `fields` ne se validait pas contre le contrat : `items` était `Node`,
dont les propriétés exigées ne le sont pas d'une lecture qui en nomme (`DECISIONS.md`, « Une lecture
de `listNodes` choisit les champs qu'elle rend »), et `ContractClient` comme le proxy du contrat
(Prism) la refusent — les parcours `@shared` de l'arbre, de la grille et des chronologies ne
passent pas contre le service. Le cadrage l'avait reporté vers EP-07 ; la décision du 2026-11-08 le
ramène ici, par **un lot technique, `[US-1400/L3]`**, sous US-1400 qu'il prépare en premier
(numéro suivant, livré avant US-1400/L2), qui ne ferme aucun critère et sert WF-ARC-0060-A. C'est
une « Interface contract issue » tranchée : la modification du contrat que la conception ne
prévoyait pas, et la seule d'EP-06. Elle assouplit une réponse, la version reste `1.0.0`.

- **`NodeProjection`** (`docs/api/components/schemas/revisions.yaml`) : les propriétés de `Node`
  reprises par l'ancre `&node_properties`, comme `ComparedNodeRead`, dont seules `node_id`,
  `row_number`, `level` et `lock_version` sont exigées ; ses facettes sont `ComparedTaskFacet` et
  `ComparedEstimateLineFacet`, aucune propriété exigée, leurs descriptions élargies à `listNodes`.
  Les `items` du `200` de `listNodes` deviennent `NodeProjection`, et sa description dit : sans
  `fields`, chaque nœud est entier ; avec, il est projeté. `Node` ne change pas : les écritures
  (`NodesWritten`, `KanbanTask`) le rendent entier. `compareRevisions` n'est pas touché, son
  `ComparedNodeRead` faisant déjà ce travail (#1208).
- **`DECISIONS.md`** : l'entrée « Une lecture de `listNodes` choisit les champs qu'elle rend »
  perd la phrase « la seule réponse du contrat dont le schéma ne dit pas tout », et la décision se
  note avec les options écartées. Les modèles du service et le client du front se régénèrent
  (`make generate-client`, `server-models-up-to-date`).
- **Le back** : `test_fields_returns_what_it_names_and_the_four_always_returned` repasse par
  `ContractClient`. La garde perdue sur les lectures sans `fields` est compensée dans
  `test_nodes.py` : le test des lectures entières valide en plus chaque nœud contre `Node`, strict
  — la compensation est locale à ce test, `ContractClient` ne change pas.
- **Le front** : `NodeList` (`components/grid/nodes.tsx`) se redéfinit en un seul endroit,
  `Omit<réponse de listNodes, "items"> & { items: Node[] }`, avec un commentaire : une grille ne
  lit que ce qu'elle a demandé par `fields`. Les consommateurs ne changent pas.
- **Options écartées** : des facettes de projection neuves ou le renommage de `Compared*` (un lot
  de plus pour rien) ; retyper chaque consommateur en `NodeProjection` (plus de 1 000 lignes, et
  EP-07 reprend la grille) ; un exemple `nodes_fields.json` (le test du back et le parcours
  `@shared` d'US-1400/L2 en font la preuve) ; laisser le constat à EP-07, qui laissait sans preuve
  tous les parcours `@shared` d'EP-06 ; une garde générale dans `ContractClient` selon la requête.
- **Ordre** : le lot précède US-1400/L2 (#2340) et, par elle, US-1470 et US-1480/L2 ; il est
  « pas avec » US-1380/L4 (#2519), qui écrit les mêmes fichiers du contrat et leurs dérivés.

### Les catalogues du front et le collage (décisions de l'utilisateur du 2026-11-08, #2537, #2559)

Deux questions d'US-1450/L2 (#2344), tranchées par l'utilisateur sur la recommandation du cadrage :

- **Le lot qui ajoute un code d'erreur au contrat écrit sa seule clé `errors.<CODE>` dans les deux
  catalogues du front**, `frontend/messages/fr.json` et `en.json`, avec son test dans
  `frontend/src/i18n/problem.test.ts` ; il n'y écrit rien d'autre. La règle du plan de lots
  « aucun lot n'écrit les catalogues `messages/*.json`, une clé manquante devient une issue »
  (corps de #2316, repris dans chaque issue de lot et par EP-07, « Ce qu'EP-06 écrit encore ») est
  amendée en ce sens : `typecheck-front` et `make catalogs` exigent la clé dès que le client
  engendré porte le code, et la règle rendait infusible tout lot qui déclare un refus — US-1380/L4
  (#2519, option (a), `NODE_CYCLE`) l'avait déjà levée une fois, US-1450/L2 (`SESSION_ID_MISSING`,
  #2472) la lève la seconde, et la décision vaut pour les suivants. Deux lots qui ajoutent chacun
  un code touchent le même fichier : ils sont « pas avec » l'un l'autre par les fichiers du
  contrat qu'ils écrivent déjà. **Amendement du 2026-11-08 (#2559, #2563)** : le lot qui porte un
  écran écrit aussi les clés non-erreur de ce seul écran dans `fr.json` et `en.json` — le texte qui
  annonce Annuler et Rétablir, qu'US-1450/L3 a fusionné sans (#2563) et qu'écrit US-1450/L6, celui qui dit combien de tâches un collage crée et le
  retrait de `grid.paste.beyondRows` (US-1450/L6) —, avec son test ; toute clé d'un autre écran
  manquante reste une issue. Écartés : reporter le code au lot du front de l'US (US-1450/L3), qui
  laissait les routes refuser sans code déclaré et revenait sur #2472 ; un lot de catalogue par
  clé, une issue, une branche et une fusion pour deux lignes.
- **Le refus `MILESTONE_HAS_NO_SUBTASK` au collage (#1772) n'avait aucun site**, le contrat n'écrivant
  par `previewPaste` que des cellules de nœuds existants. #2559 a tranché le 2026-11-08 pour B (la
  section suivante). Pendant US-1450/L2, le critère d'US-1450 ne le citait pas. Écarté : A — le
  collage n'écrit que des lignes existantes —, qui aurait retiré la phrase de `PasteRejection`.

### Le collage qui crée (décision de l'utilisateur du 2026-11-08, #2559, option B)

Le collage **crée** les tâches des lignes du bloc qui tombent au-delà du dernier nœud de la
structure. Trois lots d'US-1450 le construisent après L3 : L4 le contrat et le faux back, L5 le
service, L6 la grille. Le contrat reste en `1.0.0` : c'est une « Interface contract issue » tranchée,
la seconde d'EP-06 avec #2485.

- **La règle.** Une ligne du bloc au-delà du dernier nœud de la structure, dans l'ordre du plan,
  crée un nœud sœur de ce dernier nœud — même parent, rang à la suite, dans l'ordre du bloc —, du
  genre du nœud visé. Le dernier nœud de la structure est l'ancre, qu'il ait été écrit ou que sa
  ligne ait été refusée (précision du cadrage : « le dernier nœud écrit » du relais de #2559 ne dit
  rien d'une ligne refusée). Le libellé est requis : la cellule `label` de la ligne est vide ou
  absente — le bloc ne commence pas à la colonne `label`, seule à précéder les autres —, la ligne est
  refusée par `VALIDATION_FAILED`, `column` à `label`, et n'est pas créée. Aucun code nouveau, donc
  aucune clé de catalogue. Les autres cellules de la ligne prennent d'abord les valeurs par défaut de
  `createNode` (automatique, un jour, sans prédécesseur : WF-DEV-0050), puis se jugent dans l'ordre
  de `NodeColumn` par `judge_cell`, avec les mêmes refus qu'à la saisie ; une ligne dont une cellule
  est refusée l'est entière, comme les lignes existantes. Aucune borne nouvelle : `PASTE_TOO_WIDE` et
  la taille de la requête (413) suffisent.
- **Le refus sous un jalon.** La création passe par la fonction de création de `createNode`
  (`core/planning/interface/nodes.py`), qui refuse déjà `MILESTONE_HAS_NO_SUBTASK`
  (US-1380/L3) ; le collage la rend ligne par ligne, `params` nommant le jalon (`PasteRejection`,
  dont la phrase ne change pas). Le site existe, mais EP-06 ne l'atteint pas par un geste : le parent
  de l'ancre est celui d'une tâche, jamais un jalon ; il ne le devient qu'avec une ligne de devis
  sous un jalon, dernier nœud de la structure et ancre d'une tâche à créer. Un test unitaire de la
  fonction l'éprouve ici ; le parcours est d'US-1560 (EP-07), qui clôt la part de #1772 au collage.
- **Le contrat (L4)** : `PastePreview` énonce la règle, pour les deux genres — la création d'une
  ligne de devis par collage est servie par EP-07 (US-1560), le service d'EP-06 ne crée que des
  tâches, le genre ligne n'existant pas encore — et retire la phrase « No cell is shifted » comme
  seule limite de hauteur ; `PastePlan` gagne `created` (entier ≥ 0, requis ; les lignes qui
  créent, comptées aussi dans `accepted`), `0` dans tous les exemples existants ; `PasteApplied`
  n'a pas de champ de plus : les nœuds créés sont dans `nodes` (`NodesWritten`) ; `applyPaste` et
  `previewPaste` le disent. Deux exemples neufs, `paste_plan_creating` et `paste_applied_creating`,
  engendrés par `make mock-data` (`mockwrites`, tâches seules : le faux back ne crée que des
  tâches ; l'écriture de ses lignes de devis reste celle d'aujourd'hui). La décision s'écrit dans
  `DECISIONS.md` avec ses options écartées ; les modèles du service et le client du front se
  régénèrent. Le même lot ajoute les exemples 200 d'`undoLastChange` et `redoLastUndo` (#2564).
- **Le service (L5)** : `paste.py` remplace le refus `NOT_FOUND` d'une ligne au-delà du dernier nœud
  par la création ; le plan (`paste_plan.rows`) garde pour chaque ligne qu'elle crée ; `applyPaste`
  rejuge, crée et écrit sous le verrou de la structure, redate une seule fois, et inscrit une seule
  entrée `paste` dont l'instantané « avant » ignore les nœuds créés : annuler les supprime, rétablir
  les recrée, comme pour `createNode`. Aucune migration, aucun module nouveau.
- **Le front (L6)** : la garde locale de `paste-dialog.tsx` ne refuse plus un bloc plus haut que les
  lignes que la grille montre ; elle garde les colonnes masquées et les lignes pliées. L'aperçu dit
  combien de lignes créent (`created`), et la grille insère les nœuds créés que `PasteApplied` rend.
- **Ordre** : L4 avant L5 (les modèles régénérés) ; L6 après L3, L4 et L5. US-1480/L3 les reçoit en
  dépendances ; US-1480/L2, qui ne rejoue que `timelines.spec.ts`, n'attend pas. Le tableau « Ce
  qu'EP-06 écrit encore » d'EP-07 nomme L5 pour le collage, que US-1560 attend.
- **Options écartées** : A (voir ci-dessus) ; une opération `createRows` à part, un appel de plus pour
  un geste ; un libellé par défaut aux lignes sans libellé, qui écrirait ce que l'utilisateur n'a
  pas collé ; refuser tout le bloc si une ligne de création est refusée, contre la règle de
  WF-IHM-0050 (« les lignes valides sont écrites ») ; des sous-tâches de l'ancre plutôt que ses
  sœurs ; un code `PASTE_LABEL_REQUIRED`, une clé de catalogue pour un refus que
  `VALIDATION_FAILED` dit déjà ; laisser le dialogue déduire le nombre de créations des lignes
  au-delà de la grille, qu'il ne connaît que par ce qu'il montre.

### Le corpus partiel, les durées écoulées, la frise du témoin (décisions du 2026-11-09)

Trois questions d'US-1430/L3 (#2342) et d'US-1480/L2 (#2347), tranchées par l'utilisateur sur la
recommandation du pilote. Le corpus complet ne sera pas déposé tout de suite, et le chemin
d'EP-07 jusqu'à l'aller-retour Excel (US-1550/L4) passe par US-1430/L3 puis L4 :

- **US-1430/L3 fusionne sur le corpus partiel** : les fichiers 01, 02, 03, 05 et 13 et leur
  manifeste (#2568). Le test des cas marque non exécutés, en citant #2645, ceux qu'aucun fichier
  ne déclare encore, et les nomme au rapport. WF-QUA-0080-A reste entière en EP-06, mais n'est
  pas close par US-1430/L3 : elle se clôt au dépôt des fichiers manquants (#2645), par un lot de
  suite d'US-1430 qui lève ces marques et corrige le moteur si un fichier révèle un écart.
  US-1480/L3, qui clôt l'EPIC, l'attend.
  Écartés : un corpus engendré d'après le schéma et daté par le moteur de Waterfall, déjà écarté
  au cadrage (« Ce que le cadrage décide »), qui rendrait le test vrai par construction ;
  attendre le corpus complet, qui bloquait aussi EP-07.
- **La fin d'une durée écoulée garde le jour atteint (#2342, point 2, option A).** Le fichier 03
  le montre : MS Project finit 2 ej, 2 esem et 1 em commencées un lundi à 09:00 au jour atteint, à
  09:00 ; le moteur d'US-1390 rendait la fin de la veille ouvrée. Le moteur est retouché dans
  US-1430/L3, ses heures bornées à celles du jour atteint, et le test d'exemple
  `test_an_elapsed_duration_runs_over_the_days_without_hours_of_work` change avec lui. Écarté :
  comparer des instants de travail (option B), qui afficherait un autre jour que MS Project et
  ferait rendre à l'aller-retour d'US-1430/L4 des `date_mismatches` sur ces tâches.
- **La frise et le focus de `timelines.spec.ts` passent `@shared` en EP-07 (#2347, option A ;
  #2594 reporté).** Les 103 tâches à calendrier 4×10 h du témoin tiennent ce calendrier du rôle de
  leurs lignes, qui sont d'EP-07 : avant elles, le moteur date autrement 401 tâches par révision,
  et les parcours de la frise et du focus ne concordent pas contre le service. US-1480/L2
  fusionne avec l'export PNG et les sélections `@shared` ; la frise et le focus restent sur le
  faux back, sautés contre le service par un `test.skip` qui cite #2594, et US-1570 (EP-07) les
  étiquette `@shared` quand les lignes donnent leurs calendriers. Le critère d'US-1480 est amendé
  en ce sens. Écartés : corriger les générateurs dès EP-06 (option B), un lot d'outil de plus qui
  touchait `docs/api` ; charger dès EP-06 les calendriers des tâches (option C), hors de la
  conception.

### Les constats des lots livrés (décisions de l'auteur du 2026-11-10)

Les constats qu'EP-06 laissait « à trancher », tranchés le 2026-11-10, chacun avec l'option
écartée :

- **Le compte rendu d'un import MS Project signale des constantes d'unités autres que celles de
  l'installation par un champ** (#2580, option A) : `ImportReport.unit_constants`, toujours rendu,
  nul sans objet et pour les autres formats, porte les constantes du fichier et celles de
  l'installation (`hours_per_day`, `hours_per_week`, `days_per_month`) ; le catalogue du front
  reçoit sa phrase, le faux back un exemple (`DECISIONS.md`). Écartés : un `ImportSignal`, qui
  nomme une tâche et une colonne, et une nature d'élément ignoré, qui compte sans dire les valeurs
  que l'écran doit montrer. Le contrat le reçoit par le lot de
  suite d'US-1430, ouvert au dépôt du corpus complet (#2645), qui prend aussi la docstring de la fin
  d'une durée écoulée (#2647) et sonde la passe arrière d'une tâche écoulée, corrigée s'il y a écart
  (#2648) ; le Vérif de WF-PLA-0160-A se clôt avec lui.
- **Toute ressource naît à `lock_version` 1** (#2542, E-16 ; la règle est déjà celle du contrat,
  `DECISIONS.md`, « Un objet naît à la version 1 », 2026-11-07) : le service s'aligne pour la
  structure principale d'une révision, qu'il créait à 0, et `test_skeleton.py` compare le compteur
  de l'exemple `skeleton_generated` en absolu. Écartée : la naissance à 0, déjà écartée le
  2026-11-07.
- **Les formes `one` et `other` de l'annonce d'Annuler et de Rétablir s'éprouvent** (#2626) : le
  contrat reçoit deux exemples d'`UndoResult`, l'un à `remaining_depth` 1, l'autre à 2 ou 3, et
  `undo-wired.dom.test.tsx` lit les trois formes, en français et en anglais.
- **Un lot de finitions d'EP-06** (US-1480/L4 #2750), avant la vérification d'ensemble US-1480/L3,
  porte ces deux points de contrat et les mineurs : le test de la purge du worker attend aussi la
  disparition de l'objet du compartiment (#2566) ; les quatre points de la purge (#2533), dont les
  orphelins que `SWEEP_LIMIT` laisse derrière des clés désignées — balayés au-delà d'elles, ou, si
  le lot établit que le cas ne peut se produire, la docstring le dit et un test le prouve — et le
  plafond de `deposits_before` éprouvé ; `NO_BACKGROUND_TASK_RUNNING`, `STATE_FORBIDS_OPERATION` et
  `BEFORE_IN_PROGRESS` exportées une fois par l'interface du module qui les possède (#2555) ; une
  garde du chargeur du témoin qui refuse une installation qui a déjà des projets sans ses
  calendriers (#2556) ; les deux tests à forme supposée (#2547) ; le marqueur WF-DEV-0050-A retiré
  de `test_mockundoable.py` et de sa docstring (#2593) ; la citation du test de `CurrencyCode` et la
  ligne trop longue de « Le format MS Project » (#2682).
- **Reportés** : la préparation d'un fichier importé hors du verrou de l'application (#2582) et la
  lecture figée des tâches d'export et d'analyse (#2679) passent à un lot d'EP-09, après
  l'application des coûts réels (US-1610/L2), avec #2739, pour tous les formats ; le parcours FLX-01
  qui confirme l'import (#2683) et l'assistant e2e d'un contexte neuf (#2653) au lot de corrections
  d'EP-07 ; le validateur du corps `application/xml` (#2675) au lot d'outillage des tests d'EP-07,
  qui possède `support.py`. La borne en temps réel du test de l'en-tête MS Project (#2583) reste :
  risque accepté, sa marge est d'environ mille fois la mesure, et l'issue se rouvre si la chaîne la
  voit échouer.
- **La spécification** : WF-DAT-0080-A nomme les cinq lignes techniques (#2529, porté par #2740) ;
  le Vérif de WF-PLA-0040-A nomme le refus d'un déplacement sous soi-même (#2546, porté par #2741).
- **Les constats du lot de finitions** (décisions de l'auteur du 2026-11-10, soir), portés par la
  vérification d'ensemble US-1480/L3 #2348 :
  - **le projet et son lotissement naissent à `lock_version` 1** (#2762, part de `core/projects`) :
    la création d'un projet pose 1, et le lotissement par défaut aussi, « jamais écrit » se lisant
    alors à 1 ou par un drapeau propre ; les tests qui affirment 0 passent à 1. Les rôles
    d'habilitation et les comptes (EP-03), qui naissent encore à 0, sont une dette hors EP-06, hors
    de la livraison du 2026-11-13 (#2779). Écarté : un lot d'EP-04, livré, pour le projet ;
  - **`STALE_LOCK_VERSION`, `NOT_FOUND` et `VALIDATION_FAILED` sont déclarés une seule fois**
    (#2763), par le module qui les possède — vraisemblablement `platform/errors.py`, ces codes étant
    transverses —, les copies remplacées par des imports, et les trois ajoutés à l'ensemble `SHARED`
    de `test_boundaries.py` ;
  - **`problem.test.ts` lit ses exemples sans cast** (#2764), comme celui de `NODE_CYCLE` :
    `toMatchObject` sur ce que le test lit de l'exemple, puis un `ProblemText` littéral.

### Les constats laissés après la livraison (décisions de l'auteur du 2026-11-11)

EP-06 reste fini ; rien de ce qui suit ne se corrige avant la livraison du 2026-11-13 :

- **La passe arrière d'un décalage écoulé qui atteint un jour sans heure de travail** (#2816) et
  **le départ au plus tard d'une durée écoulée éprouvé pour d'autres durées** (#2832) sont reportés
  à un lot de suite d'EP-06, ouvert après la livraison, et pas avant.
- **Le projet et son lotissement nés à 1, « jamais écrit » lu à `lock_version` 1** (#2843,
  option A) : rien avant la v1, aucune installation ne portant de données au-delà du témoin ; ni
  migration, ni drapeau. Écartées : une migration en EP-07 qui décale les compteurs existants, et
  un drapeau propre `work_breakdown_written`.

### Le lot de suite d'US-1430 (2026-11-10)

L'auteur a complété le corpus (PR #2811, vers `main`, qu'il fusionne). Essayé sur `epic/EP-06`
avec le manifeste complet, le test du corpus fait passer 65 contrôles et échouer trois fichiers.
Le lot de suite que la décision du 2026-11-09 annonçait est **US-1430/L5 (#2813)**. Il ferme #2645,
ainsi que #2580, #2647 et #2648 (« Les constats des lots livrés »), et clôt WF-QUA-0080-A.
US-1480/L3 (#2348) l'attend.

- **La reprise de `main` se fait dans le lot.** Le manifeste complet fait échouer le test du
  corpus tant que les trois écarts ne sont pas corrigés : une reprise seule d'`epic/EP-06` ne
  passerait pas la chaîne. Écartée : reprendre `main` dans `epic/EP-06` avant le lot.
- **Le décalage en pourcentage** (02, T12 et T13 ; `LagFormat` 19, `LinkLag` = 10) : 10 % d'une
  tâche de 8 h valent 48 min pour MS Project, environ 5 min pour Waterfall. C'est une anomalie, du
  lecteur ou du moteur, que le lot corrige. L'écrivain la suit en miroir.
- **La récapitulative manuelle** (06, Manuelle 4 ; `manual_summary`) : MS Project garde ses dates
  saisies, Waterfall la calcule toujours. L'import la rend automatique et la signale
  (`SUMMARY_TASK_DERIVED`, « Le format MS Project »). Le test du corpus ne compare pas cette tâche
  aux dates du fichier, mais il affirme l'écart à part : ses dates sont dérivées de ses
  subordonnées, et elles diffèrent de celles du fichier. Le test de l'import établit le signal.
  Aucune autre tâche n'est exclue de la comparaison. Écarté : garder les dates saisies d'une
  récapitulative, que la spécification calcule toujours.
- **Les contraintes** (08 ; SNET, MFO, FNLT) : le test du corpus donne ces tâches au moteur en mode
  manuel, aux dates du fichier, comme l'import les fige (README du corpus, point 9 ; WF-INTF-0040).
- **`lag_negative_w` reste non exécuté** (#2812) : aucun planning ne porte un décalage négatif en
  semaines, le seul décalage négatif du 02 étant en jours. Le cas ne bloque ni le lot ni
  US-1480/L3. Son marquage cite #2812 au lieu de #2645, et WF-QUA-0080-A se clôt en EP-06 avec cet
  écart. Le texte de la spécification n'est pas en cause : c'est le corpus qui manque d'un fichier,
  et l'auteur désigne l'EPIC qui le recevra.

### Le front

- Les écrans sont ceux d'EP-02, d'EP-14 et d'EP-15 ; chaque US branche le sien et retire
  `MockupNotice` de la page qu'elle sert en dernier : les chronologies par US-1400, les échanges
  et l'encart « Démarrer le projet » par US-1430, l'arborescence par US-1440, le planning par
  US-1470. Les aides `frontend/help/fr/FBS-4.3*.md` disent ce que le service fait, par l'US de
  leur écran.
- Les replis de `listNodes` (#496) sont retirés par US-1400 (`inscribedTo`) et US-1440
  (`summaryTree`), et l'écart d'EP-02 retiré avec le second.
- Annuler et Rétablir sont branchées par US-1450 (`undo-commands.tsx`) sur `undoLastChange` et
  `redoLastUndo` ; le collage du planning joue contre le service.
- La route `/tasks/[taskId]/result` du front (EP-02/L38) transmet déjà le résultat ; US-1430 la
  joue contre le service.

### Le harnais

Chaque US étiquette `@shared` les tests dont l'écran est servi : US-1400 `timelines.spec.ts` ;
US-1430 `exchanges.spec.ts` et `tasks.spec.ts` ; US-1440 l'arborescence de `planning.spec.ts` ;
US-1450 `undo.spec.ts` et `paste.spec.ts` pour le planning ; US-1460 les étapes du squelette de
`project-start.spec.ts` (`BEFORE_EP06` levé) ; US-1470 `planning.spec.ts`, `structure.spec.ts`,
`computed.spec.ts`, `keyboard.spec.ts`, la part du planning de `grid.spec.ts` et de
`context.spec.ts` (`BEFORE_THE_DATA` levé pour le planning). Les parcours qui écrivent le font sur
un projet que la course crée (#2193) ; les lectures du témoin se jouent des deux côtés. Ce qui ne
se rejoue pas avant EP-07 — les lignes, les montants, le devis — reste gardé par `inService` et
listé dans le guide, chaque entrée nommant l'EPIC qui la lève.

### Les tests du back

Un fichier par objet et par règle — `test_nodes.py`, `test_nodes_move.py`, `test_scheduling.py`
(le moteur, sans base), `test_scheduling_links.py`, `test_planning_start.py`,
`test_timelines.py`, `test_tracking.py`, `test_progress.py`, `test_imports.py` (la mécanique, avec
un format d'essai des tests), `test_msproject.py`, `test_msproject_corpus.py`,
`test_exports.py`, `test_task_tree_image.py`, `test_history.py`, `test_paste.py`,
`test_skeleton.py`, `test_purge.py`, `test_registries.py` (#2180), `test_witness_tasks.py` —,
chaque test citant son exigence, chaque réponse validée contre le contrat ; les exemples
chiffrés des Vérif sont des tests sans base quand ils le peuvent (`tests/examples`). Les fixtures
communes du planning — une structure avec ses tâches par l'interface, les sessions — vivent dans
`tests/planning_support.py`, écrit par le socle. Un test de concurrence par règle d'ensemble :
deux écritures d'une même structure, deux applications d'un même import, deux annulations.

### L'ordre de construction

Le socle d'abord, puis ce qui ne dépend que de lui en largeur quatre, l'arbre dès que le moteur
est là, les écrans par l'US qui sert leur objet, la vérification d'ensemble en dernier ; le plan
de lots (étape 3) le détaille en vagues.

1. **US-1380/L1**, le socle — après la fusion d'US-0990/L2 d'EP-04 (#2069) : les deux
   migrations, les trois modules à vide et leurs interfaces en paquet — hors le sous-paquet
   `core/planning/scheduling/`, que le lot du moteur possède entier, et avec le fichier de
   l'analyseur XML durci de `core/exchanges` et son réexport, pour que les lots de la vague 2
   n'écrivent que leurs fichiers —, les registres nouveaux
   déclarés dans `core/revisions`, `core/projects`, `resource_settings` et `witness/revisions`,
   les routeurs vides, les gestionnaires du worker et le verbe `purge` déclarés, les fichiers de
   tranche, de tests et `planning_support.py`, le test des points d'entrée (#2180). **Lot pivot
   d'EP-07** : `epic/EP-07` se tire d'`epic/EP-06` dès sa fusion. Il lui garantit la table `node`
   avec `kind` à deux valeurs, la facette `task`, `task_link`, les registres `register_copy`,
   `register_tasks_and_lines`, `register_closing` et `register_facet`, l'interface de
   `core/exchanges` (`register_format`, `register_exporter`) et celle de `core/history`, la chaîne
   des migrations arrêtée à `0023` ; EP-07 ajoute par sa migration la table `estimate_line`
   (clé vers `node`), les tables images de la révision, et chaîne sur `0023` ; ses lots qui créent
   des lignes attendent aussi les deux lots suivants de l'arbre. En parallèle, dès la création de
   la branche : **le moteur pur** (US-1390), sans table ni dépendance nouvelle, qui possède
   `core/planning/scheduling/` entier ; et le lot d'outil d'US-1480 (`witness_tasks.json`).
2. **La mécanique d'import** (US-1420), **les chronologies** (US-1400, la lecture et l'écriture
   des chronologies), **le lecteur et l'écrivain MS Project** (US-1430, purs, éprouvés par
   l'aller-retour structurel et la validation XSD — le test du corpus attend l'analyse, en 5) et
   **l'historique** (US-1450, `recording`, `undo`, `redo` sur des instantanés posés) : tout ce qui
   ne dépend que du socle.
3. **L'arbre des tâches** (US-1380 : lecture, création, modification, dépendances, numéro — et
   la suppression des nœuds à l'abandon d'une révision, dès ce lot, pour que l'abandon ne casse
   pas entre deux vagues —, puis suppression, déplacement, rattachement), après le moteur et
   l'historique ; **les exports** (US-1430 : la tâche `export`, le stockage,
   `getBackgroundTaskResult`), sans rien de la purge ; **le rendu de l'image** (US-1440, pur).
4. **Les liaisons et la date de début** (US-1390), **les inscriptions** (US-1400), **l'état**
   (US-1410), après l'arbre ; **la purge entière** (US-1420), après les exports.
5. **L'analyse et l'application MS Project** (US-1430, avec le test du corpus), **le collage**
   (US-1450), **le squelette** (US-1460), **l'image de l'arborescence branchée** (US-1440), après
   l'arbre et les liaisons.
6. **La grille et le Gantt** (US-1470), **l'export et l'écran des échanges** (US-1430), **les
   commandes Annuler et Rétablir** (US-1450), **la tranche des tâches** (US-1480), après tout ce
   qui écrit ; puis **la vérification d'ensemble** (US-1480), seule.

---

## US-1380 — L'arbre des tâches de la structure principale

- **statut** : à faire
- **exigences** : `WF-PLA-0040-A`, `WF-PLA-0050-A`, `WF-PLA-0070-A`, `WF-PLA-0170-A`,
  `WF-PLA-0150-A`, `WF-DAT-0150-A`
- **opérations** : `listNodes`, `createNode`, `updateTaskFacet`, `deleteNode`, `moveNodes`,
  `resolveRowNumber`, `getComputedValueDependencies`
- **issue** : 2317

**En tant que** chef de projet, **je veux** créer les tâches et les jalons de la structure
principale, les nommer, les décrire, les rattacher à un lot ou à un poste, les déplacer et les
indenter, les supprimer, et relire l'arbre tel que le serveur le calcule, **afin de** construire le
planning dont le devis portera les lignes.

**Critères d'acceptation.**

- `WF-PLA-0040-A` — « Après déplacement d’une récapitulative portant deux niveaux de subordonnées,
  les tâches et les lignes déplacées sont inchangées, et le devis totalise le même montant. » :
  `moveNodes` d'une récapitulative emporte son sous-arbre, chaque tâche inchangée hors son parent
  et sa place ; les lignes et le devis sont d'EP-07, EP-09 clôt ;
- `WF-PLA-0040-A` — « Les dates et l’état d’une récapitulative ne sont pas saisissables. » :
  `updateTaskFacet` refuse une date par 422 `SUMMARY_TASK_DERIVED`, `subordinate_node_ids` les
  nommant, et le mode par `COMPUTED_VALUE` ; `computed_fields` les nomme ; l'état, par
  `setTaskProgress` (US-1410) ;
- `WF-PLA-0040-A` — « Une récapitulative dont une subordonnée est démarrée est démarrée ; elle
  n’est terminée qu’après la dernière. » : l'état dérivé, lu par `listNodes`, constaté par
  US-1410 qui pose les états ;
- écart : `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et
  dont une ligne propre porte un reste à engager de 500 est démarrée et signalée ; la saisie d’un
  reste nul sur cette ligne la termine. » : les lignes et le reste à engager sont d'EP-07 et
  d'EP-09, qui clôt ; `awaiting_own_lines` est toujours faux ici ;
- `WF-PLA-0040-A` — « La suppression de la seule subordonnée d’une récapitulative de dix jours
  laisse une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être
  ajoutée. » : `deleteNode` rend la récapitulative dans `ancestors` devenue feuille automatique de
  dix jours, et `createNode` sous elle aboutit ;
- écart : `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et
  dont la seule ligne propre est une provision de 40 est terminée et n’est pas signalée. » : les
  lignes de provision sont d'EP-08, EP-09 clôt ;
- écart : `WF-PLA-0040-A` — « Une récapitulative dont la seule subordonnée est un jalon terminé et
  dont une ligne propre garde un reste à engager, privée de ce jalon, est une feuille démarrée
  d’un jour, non un jalon. » : la règle « démarrée, une durée d'un jour » est écrite ici et
  éprouvée sur une récapitulative démarrée sans ligne ; la ligne propre est d'EP-07, EP-09 clôt ;
- `WF-PLA-0040-A` — « Une récapitulative terminée dont la seule subordonnée, un jalon, est
  déplacée devient un jalon terminé. » : `moveNodes` rend l'ancienne récapitulative dans
  `ancestors`, jalon terminé, états posés par US-1410 ;
- `WF-PLA-0040-A` — « Le déplacement d’une sélection qui contient une récapitulative et l’une de ses
  subordonnées laisse la subordonnée sous la récapitulative : le groupe est déplacé entier, sans
  être aplati. » : `moveNodes` ignore une tâche nommée dont une ancêtre est aussi nommée
  (spécification 1.0.3, #2521), réalisé par US-1380/L4 (#2519) ;
- `WF-DAT-0150-A` — « Deux contributeurs lisent la même tâche ; le premier la modifie ; la
  modification du second, fondée sur sa lecture, est refusée, le refus le dit, et la tâche garde la
  valeur du premier. Relue, la tâche se modifie. » : 412 `STALE_LOCK_VERSION` sur le `lock_version`
  des écritures de l’arbre ; les tests du 412 la citent (#2525), redressés par US-1480/L3 (#2348) ;
- `WF-PLA-0050-A` — « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. » :
  `createNode` et `moveNodes` refusent par 422 `MILESTONE_HAS_NO_SUBTASK` sur `/parent_id`,
  `node_id` et `label` du jalon (#1772) ; une ligne de devis sous un jalon reste permise (EP-07) ;
- `WF-PLA-0050-A` — « Une récapitulative dont la seule subordonnée est un jalon a une durée
  nulle et reste une récapitulative. » : `is_summary` vrai, `is_milestone` faux, durée `0` ;
- écart : `WF-PLA-0050-A` — « Un jalon portant une ligne de devis passe de non démarré à terminé
  par la saisie d’un reste à engager nul ; un jalon sans ligne est terminé depuis le Kanban. » :
  le passage direct d'un jalon à terminé est servi par US-1410 (`setTaskProgress`) ; la ligne, le
  reste à engager et le Kanban sont d'EP-07 et d'EP-09, qui clôt ;
- écart : `WF-PLA-0050-A` — « La terminaison depuis le Kanban d’un jalon portant une ligne est
  refusée en renvoyant à la saisie de son reste à engager. » : `task_without_lines` est écrite par
  US-1410, jamais manquante sans ligne ; EP-09 clôt ;
- écart : `WF-PLA-0050-A` — « Un jalon qui ne porte qu’une ligne de provision est terminé depuis
  le Kanban. » : EP-08 et EP-09 ;
- `WF-PLA-0070-A` — « La suppression d’une récapitulative supprime ses subordonnées et leurs
  lignes, et le devis diminue d’autant. » : `deleteNode` supprime physiquement le sous-arbre et
  ses liaisons, rend ses ancêtres et les totaux recalculés ; les lignes et le devis sont d'EP-07,
  EP-09 clôt ;
- `WF-PLA-0070-A` — « La suppression d’une tâche démarrée est refusée, et l’utilisateur est
  renvoyé vers la mise à zéro de son reste à engager. » : 409 `STATE_FORBIDS_OPERATION`,
  `task_not_started`, pour une tâche démarrée ou terminée ou une récapitulative dont une
  subordonnée l'est (états posés par US-1410) ; le renvoi de l'écran vers le reste à engager est
  d'EP-09, qui clôt ;
- `WF-PLA-0170-A` — « Une feuille peut être rattachée à un poste ; une récapitulative rattachée
  dont on supprime la dernière subordonnée garde son rattachement. »
- `WF-PLA-0170-A` — « Le rattachement d’une tâche à un poste déjà porté par une autre est refusé,
  comme celui d’une même tâche à un lot et à un poste. » : 422 `WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED`
  avec `conflicting_object_id` et `conflicting_object_label`, `WORK_BREAKDOWN_ITEMS_EXCLUSIVE`,
  rendus ensemble quand les deux s'appliquent ; `UNKNOWN_WORK_BREAKDOWN_ITEM` pour un élément que
  le lotissement n'a pas ou marqué supprimé ;
- `WF-PLA-0170-A` — « Le déplacement de la tâche d’un poste hors du sous-arbre de la tâche de son
  lot est refusé. » : `moveNodes` et `updateTaskFacet` par 422 `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`,
  `work_package_task` et `order_item_tasks` nommés ;
- `WF-PLA-0170-A` — « La suppression d’un poste porté par une tâche de la révision en cours
  aboutit ; la tâche reste et ne porte plus de rattachement ; une révision marquée qui la citait
  l’affiche toujours rattachée. » : `setWorkBreakdown` (EP-04) marque le poste supprimé dès qu'une
  tâche d'une révision marquée le porte, le supprime sinon, et retire le rattachement des tâches
  de la révision en cours par l'interface du planning ; la révision marquée garde sa ligne, et
  `work_breakdown_label` y résout le libellé de l'élément marqué supprimé ;
- `WF-PLA-0170-A` — « Après suppression d’un poste sur un projet sans révision en cours, la
  révision créée ensuite ne porte plus ce rattachement ; la révision marquée l’affiche
  toujours. » : la copie des tâches (`register_copy`) laisse nul le rattachement à un élément
  marqué supprimé ;
- `WF-PLA-0170-A` — « La génération du squelette n’est pas proposée sur le devis propre d’un
  risque. » : constaté par US-1460 ;
- écart : `WF-PLA-0170-A` — « La fusion d’un différentiel qui déplacerait la tâche d’un poste hors
  du sous-arbre de la tâche de son lot est refusée en nommant la tâche. » : la fusion est
  d'EP-08, qui clôt ;
- écart : `WF-PLA-0170-A` — « Une tâche rattachée au poste 2 dont un différentiel allonge la
  durée porte toujours ce rattachement après la fusion. » : EP-08 ;
- `WF-PLA-0150-A` — « Le déplacement d’une tâche qui porterait la fin du projet à quinze ans et
  un jour de son début est refusé, et la tâche est nommée. » : `updateTaskFacet`, `createNode` et
  `moveNodes` par 422 `PROJECT_HORIZON_EXCEEDED`, `params.task` la tâche saisie, créée ou déplacée ;
  `setPredecessors`, par US-1390 ;
- `WF-PLA-0150-A` — « Un import MS Project dont le planning s’étend sur seize ans est rejeté au
  compte rendu. » : constaté par US-1430 (`ImportReport.refusals`) ;
- propre à l'US : `listNodes` rend la structure entière, en profondeur d'abord, `row_number` et
  `level` calculés, `summary_depth` et `scheduled_at` dans `meta`, les totaux ; tient `kinds`,
  `fields`, `search`, `subtree_of`, `summaries_only`, `max_level`, `timeline_id`,
  `work_package_id`, `order_item_id`, `progress`, `is_critical`, les filtres de colonne de la
  tâche (description, mode, durée, début, fin, marge, démarrage, terminaison, jalon, fin dépassée)
  et leurs refus (`NUMBER_INVALID`, `DATE_INVALID`, `VALUE_OUT_OF_RANGE`, `FIELD_NOT_ACCEPTED`) ;
  les filtres de la ligne sont déclarés et sans effet jusqu'à EP-07 ; une révision marquée se lit
  comme la révision en cours ;
- propre à l'US : `createNode` crée une tâche — feuille automatique d'un jour sans mode ni durée,
  manuelle aux dates saisies par leur seule date, les heures complétées sur le calendrier par
  défaut (#1770), `NON_WORKING_DAY` nommant le jour travaillé suivant, `after_node_id` et
  `NODE_NOT_SIBLING`, une feuille manuelle qui reçoit une sous-tâche devenue récapitulative
  automatique — et rend `NodesWritten` ; `updateTaskFacet` écrit le libellé, la description, le
  mode, la durée avec son unité, les dates d'une tâche manuelle et le rattachement, seul ce qui
  est envoyé, au compteur lu (412), `FIELD_NOT_ACCEPTED` pour la durée d'un jalon ;
  `getComputedValueDependencies` nomme les subordonnées d'une récapitulative (`subordinates`) et
  refuse un champ saisissable ; `resolveRowNumber` rend le nœud d'un numéro de toute la structure,
  404 au-delà de la dernière ligne, 422 sur `/path/row_number` ;
- propre à l'US : chaque écriture est refusée sur une révision marquée (409 `revision_draft`), sur
  un projet terminal (`project_not_terminal`), pendant un traitement de fond
  (`no_background_task_running`), par un non-contributeur (403 `NOT_CONTRIBUTOR`) et sans
  `planning.write` (403) ; chaque réponse est validée contre le contrat dans les tests du
  service, et la route de chaque opération déclare ses permissions ;
- propre à l'US (lot technique) : les tables `node`, `task_link`, `timeline`, `tracking_entry`,
  `import_report`, `undo_entry` et `paste_plan`, la colonne `cost_structure.planning_start_on`
  remplie (#2170), `create_project_partitions` remplacée, les déclencheurs d'immuabilité, les
  droits du rôle du service ; les modules `core/planning` et `core/exchanges` avec leur interface
  en paquet, enregistrés dans les registres de `core/revisions` (la copie des tâches, des
  liaisons et des inscriptions ; `revision_has_tasks_and_lines` pour les tâches) et dans ceux de
  `resource_settings` ; un routeur vide par US enregistré dans `app.py`, les fichiers de tests et
  de tranche du témoin, la déclaration des opérations et des permissions par routeur ; un test
  par point d'entrée — l'API, le worker, le chargeur — vérifie que les registres portent les
  extensions attendues (#2180) ; `make check` passe sur ce socle, tiré d'`epic/EP-04`.

**Notes de réalisation.** La table des nœuds est unique, `node`, à deux facettes selon `kind`
(`task` ici, `estimate_line` par la migration d'EP-07 ; décision de l'auteur du 2026-11-07,
contre le Tableau 10 du §4.4.1, qui nomme `task` et `estimate_line` — une issue de spécification
le dit). La tâche porteuse d'une ligne est son parent. L'ordre d'un nœud parmi ses frères est
une clé d'ordre, les lignes d'une tâche précédant ses sous-tâches, et `position` comme
`row_number` se calculent à la lecture. Les dates et les marges viennent du moteur d'US-1390 à
chaque écriture ; les états sont posés par US-1410. Le socle de l'EPIC est le premier lot de cette
US, et le lot pivot d'EP-07.

**Hors périmètre.** Les lignes de devis et leur facette (EP-07) ; les liaisons (US-1390) ; les
inscriptions (US-1400) ; l'état (US-1410) ; le collage et l'annulation (US-1450) ; les écrans
(US-1470).

---

## US-1390 — Le calcul des dates, des marges et du chemin critique, et les liaisons

- **statut** : à faire
- **exigences** : `WF-PLA-0010-A`, `WF-PLA-0020-A`, `WF-PLA-0030-A`, `WF-PLA-0100-A`,
  `WF-PLA-0160-A`
- **opérations** : `setPredecessors`, `updateCostStructure` ; `listNodes`, `createNode`,
  `updateTaskFacet`, `moveNodes`, `deleteNode` pour ce qu'elles rendent de redaté
- **issue** : 2318

**En tant que** chef de projet, **je veux** que les dates de mes tâches automatiques, leurs marges
et le chemin critique se calculent sur leur calendrier, à partir de leurs durées, de leurs
liaisons et de la date de début de planning de la structure, et que mes liaisons se saisissent
comme dans MS Project, **afin de** lire un planning juste sans le dater à la main.

**Critères d'acceptation.**

- `WF-PLA-0010-A` — « Une tâche de seize heures en mode automatique, commencée un lundi matin sur
  un calendrier de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre
  heures, elle finit le jeudi. » : un test sans base du moteur ;
- `WF-PLA-0010-A` — « Une tâche dont les deux rôles travaillent huit et six heures le lundi est
  planifiée sur six heures ce jour-là. » : l'intersection des calendriers est une fonction du
  moteur, éprouvée sans base sur deux calendriers donnés ; les rôles d'une tâche viennent de ses
  lignes, d'EP-07, qui clôt ;
- `WF-PLA-0010-A` — « Une tâche sans ligne de main-d’œuvre est planifiée sur le calendrier par
  défaut. » : toute tâche d'EP-06 ; `calendar_hours` le rend ;
- écart : `WF-PLA-0010-A` — « L’ajout, à une tâche dont un rôle travaille du lundi au vendredi,
  d’une ligne d’un rôle qui ne travaille que le week-end est refusé en nommant les deux rôles, et
  la tâche reste inchangée. » : les lignes sont d'EP-07, qui clôt ; le moteur refuse déjà une
  tâche sans aucune heure dans la semaine ;
- écart : `WF-PLA-0010-A` — « La répartition mensuelle de la charge d’une ligne suit les heures du
  calendrier de son rôle. » : EP-07 ;
- écart : `WF-PLA-0010-A` — « L’import d’un fichier de devis dont une ligne donnerait ce résultat
  rejette cette ligne au compte rendu et applique les autres. » : EP-07 ;
- `WF-PLA-0010-A` — « La modification d’un calendrier qui laisserait une tâche sans heure dans un
  projet que le manager ne peut pas consulter est refusée en nommant ce projet par son libellé et
  son code ; un projet en chiffrage sans code est nommé par son seul libellé. » : la garde
  `calendar_change_is_admissible` d'EP-05 est remplie par un registre de `resource_settings`
  qu'EP-06 alimente ; ici elle juge le calendrier par défaut, dont relèvent toutes les tâches sans
  ligne, et refuse par `TASK_WITHOUT_WORKING_HOURS`, `params.projects` nommant chaque projet par
  son libellé et son code, nul sans code ; les calendriers des rôles sont d'EP-07, qui clôt ;
- `WF-PLA-0020-A` — « Le déplacement d’une tâche prédécesseur déplace ses successeurs en mode
  automatique et laisse inchangés ceux en mode manuel. » : `rescheduled` les rend ;
- `WF-PLA-0020-A` — « Les dates d’une tâche en mode automatique ne sont pas saisissables. » :
  422 `COMPUTED_VALUE` sur `/start` ou `/finish`, `computed_fields` les nomme (US-1380) ;
- `WF-PLA-0020-A` — « Une tâche en mode automatique sans prédécesseur commence à la date de début
  de planning ; avancer cette date d’une semaine l’avance d’autant, ainsi que ses successeurs
  automatiques. » : `updateCostStructure` écrit `planning_start_on` et rend les tâches redatées
  (`rescheduled`), les manuelles inchangées ; un jour chômé au calendrier par défaut est refusé
  par `NON_WORKING_DAY` ; une structure reprise d'une révision marquée conserve la sienne
  (#2170) ;
- `WF-PLA-0020-A` — « Une tâche manuelle datée avant la fin calculée de son prédécesseur est
  signalée dans la grille et dans le Gantt, avec ce prédécesseur ; la retarder au-delà de cette
  fin, ou raccourcir le prédécesseur, fait disparaître le signalement. » : `link_conflicts` sur
  les deux tâches, le prédécesseur de marge négative et critique, rendus par `rescheduled` à
  l'écriture qui crée ou lève le conflit ; la grille et le Gantt, par US-1470 ;
- `WF-PLA-0020-A` — « Sur un calendrier du lundi au vendredi, la date de début d’une tâche
  manuelle saisie un samedi est refusée, et le refus nomme le lundi suivant ; la même date
  importée d’un fichier MS Project est gardée et signalée au compte rendu. » : la saisie, par
  US-1380 (`NON_WORKING_DAY`, `next_working_day`) ; l'import, par US-1430 (`ImportReport.signals`) ;
- `WF-PLA-0030-A` — « Les quatre types et un décalage négatif sont importés, saisis et exportés
  sans perte. » : saisis par `setPredecessors`, conservés avec leur type, leur valeur et leur
  unité ; importés et exportés, par US-1430 ;
- `WF-PLA-0030-A` — « La création d’une liaison fermant un cycle, ou reliant une récapitulative à
  l’une de ses subordonnées, est refusée, et la raison en est nommée à l’utilisateur. » :
  422 `LINK_CYCLE` avec `params.cycle` dans l'ordre des liaisons, la plus courte, et
  `LINK_FORBIDDEN` ; `moveNodes` refuse de même une boucle ou une liaison à travers la hiérarchie
  (US-1380) ; un prédécesseur envoyé deux fois, `DUPLICATE_PREDECESSOR` ;
- `WF-PLA-0030-A` — « Un décalage saisi en semaines ou en mois est conservé dans son unité,
  importé et exporté sans conversion. » : conservé ; importé et exporté, par US-1430 ;
- `WF-PLA-0030-A` — « Un décalage de 50 % sur un prédécesseur de dix jours vaut cinq jours de
  travail. » : un test sans base du moteur ;
- `WF-PLA-0100-A` — « Sur un planning à deux branches parallèles de durées différentes, la
  branche la plus longue est critique et l’autre porte une marge égale à leur écart. »
- `WF-PLA-0100-A` — « Allonger une tâche de la branche courte au-delà de sa marge la rend critique
  à son tour. »
- `WF-PLA-0100-A` — « Une tâche en mode manuel n’affiche aucune marge et n’apparaît jamais sur le
  chemin critique, alors que ses successeurs automatiques voient leurs marges calculées à partir
  de ses dates. »
- `WF-PLA-0100-A` — « Un prédécesseur automatique qui ne peut pas finir avant le début d’une
  tâche manuelle porte une marge négative, apparaît sur le chemin critique et est signalé. »
- `WF-PLA-0100-A` — « Une récapitulative dont une subordonnée est critique est critique et
  affiche la marge de cette subordonnée, nulle ou négative. »
- `WF-PLA-0100-A` — « Un prédécesseur lié début à début à une tâche manuelle, et qui ne peut pas
  commencer avant elle, porte une marge négative et est signalé. » : les six, des tests sans base
  du moteur, et `total_float`, `is_critical`, `link_conflicts` lus par `listNodes` ;
- `WF-PLA-0160-A` — « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize heures,
  « 1 sem » quarante heures et « 1 m » cent soixante heures. » : la conversion par les constantes
  de `getDurationUnits` (EP-05), un test sans base ;
- `WF-PLA-0160-A` — « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer
  d’unité. » : constaté par US-1430 ;
- `WF-PLA-0160-A` — « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit à
  la dernière heure travaillée d’un vendredi s’achève le dimanche ; le successeur, sur un
  calendrier du lundi au vendredi, commence le lundi à la première heure travaillée, de même
  qu’avec un décalage de 2 eh. »
- `WF-PLA-0160-A` — « Un décalage de 2 j sur la même liaison le fait commencer le mercredi. » :
  les deux, des tests sans base du moteur ;
- `WF-PLA-0160-A` — « Un fichier MS Project dont les constantes diffèrent de celles de
  l’installation est importé avec les mêmes durées en heures, et le compte rendu signale la
  différence. » : constaté par US-1430 ;
- `WF-PLA-0160-A` — « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des
  langues de l’interface. » : constaté par EP-15 (US-0470), le serveur recevant l'unité du
  contrat ;
- `WF-PLA-0160-A` — « En anglais, « 1 j » et « 1 d » valent chacun un jour ; « 3 », saisi sans
  suffixe, vaut trois jours. » : constaté par EP-15 (US-0470) ;
- `WF-PLA-0160-A` — « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans
  une révision en cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision
  marquée, elle vaut toujours seize heures. » : `set_duration_units` (EP-05) appelle, par un
  registre de `resource_settings`, le recalcul de toutes les structures des révisions en cours
  dans sa transaction, `scheduled_at` avançant ; une révision marquée n'est pas redatée et garde
  ses dates ;
- propre à l'US : le moteur est un module pur de `core/planning` — tâches, liaisons, calendrier
  par tâche et constantes en entrée ; dates au plus tôt et au plus tard, marges, criticité,
  conflits et horizon en sortie —, sans base ni session, que les tests des Vérif et le corpus de
  WF-QUA-0080 (US-1430) éprouvent ; chaque écriture de nœud de l'EPIC l'appelle sur la structure
  entière et rend `rescheduled` et `ancestors` ;
- propre à l'US : `setPredecessors` remplace les liaisons de la tâche, `predecessor_row_number`
  calculé à la lecture, `PROJECT_HORIZON_EXCEEDED` nommant la tâche saisie ; `updateCostStructure`
  écrit aussi le libellé, exige un champ avec le compteur, est gardée par `edit_planning` ;
  chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Le calcul est en heures de travail sur le calendrier de la tâche
(WF-PLA-0010) : un `WorkInstant` est une date et les heures écoulées ce jour-là. Les contraintes
de date de MS Project ne sont pas gérées : une tâche à contrainte est importée en mode manuel
(WF-INTF-0040). Le moteur et son branchement se livrent en deux lots, le moteur pur d'abord.

**Hors périmètre.** Les calendriers des rôles d'une tâche, portés par ses lignes (EP-07) ; la
répartition de la charge (EP-07).

---

## US-1400 — Les chronologies nommées et les inscriptions aux suivis

- **statut** : à faire
- **exigences** : `WF-PLA-0140-A`, `WF-PLA-0060-A`
- **opérations** : `listTimelines`, `createTimeline`, `deleteTimeline`, `setNodeTracking` ;
  `listNodes` avec `timeline_id`
- **issue** : 2320

**En tant que** chef de projet, **je veux** nommer des chronologies, y inscrire des tâches et des
jalons ou les en retirer, inscrire un jalon au suivi temps/temps, et lire chaque chronologie en
frise, **afin de** présenter à chaque public les jalons qui le concernent.

**Critères d'acceptation.**

- `WF-PLA-0140-A` — « Deux chronologies d’un même projet portent des sélections distinctes et se
  retrouvent d’une session à l’autre. » : les inscriptions sont des lignes de `tracking_entry`,
  par lignée de la tâche et par chronologie, lues par `listNodes` avec `timeline_id`, que la
  révision suivante retrouve (WF-DAT-0030) ;
- `WF-PLA-0140-A` — « L’export produit un fichier PNG de la chronologie affichée. » : la frise
  d'EP-15 (US-0530/L3b) exporte son PNG contre le service, le parcours étiqueté `@shared` ;
- `WF-PLA-0060-A` — « Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu’elle
  est retirée. » : `setNodeTracking` remplace les inscriptions de la tâche, et `listNodes` avec
  `timeline_id` la rend puis ne la rend plus ;
- écart : `WF-PLA-0060-A` — « Le diagramme temps/temps ne suit que les jalons inscrits. » :
  l'entrée `milestone_tracking` est écrite ici, refusée sur une tâche qui n'est pas un jalon par
  `MILESTONE_REQUIRED` ; le diagramme est d'EP-10, qui clôt ;
- propre à l'US : `createTimeline` et `deleteTimeline` suivent `ProjectCommand.manage_timelines`
  (`planning.write`, projet non terminal, 409 `project_not_terminal`), le nom n'est pas unique,
  la suppression est physique et emporte les inscriptions, sans compteur (#1733) ; `listTimelines`
  rend les chronologies du projet ; `setNodeTracking` refuse `timeline_id` absent (`VALUE_REQUIRED`),
  d'un autre projet (`UNKNOWN_TIMELINE`), sur `milestone_tracking` (`FIELD_NOT_ACCEPTED`), sous
  `edit_planning` ;
- propre à l'US : l'écran des chronologies (`…/timelines`) travaille contre le service, le front
  n'applique plus le critère `timeline_id` à la réponse (#496) et le parcours
  `timelines.spec.ts` porte `@shared` ; `load-witness` charge les chronologies du témoin et les
  inscriptions de ses tâches dans le fichier `timelines` de la tranche ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** `timeline` et `tracking_entry` sont du régime « projet » (§4.4.1) : une
inscription nomme une lignée, non un nœud, et survit aux révisions ; la lecture d'une révision la
résout par la lignée de chaque tâche. La colonne « Chronologies » de la grille (US-0480) se lit
par `task.tracking`.

**Hors périmètre.** Le diagramme temps/temps (EP-10) ; la disposition des couloirs, une
préférence d'affichage (EP-03, EP-15).

---

## US-1410 — L'état des tâches

- **statut** : à faire
- **exigences** : `WF-PLA-0130-A`
- **opérations** : `setTaskProgress`
- **issue** : 2324

**En tant que** chef de projet, **je veux** qu'une tâche porte son état et ses dates de démarrage
et de terminaison, qu'une récapitulative les tire de ses subordonnées, et qu'un jalon passe de non
démarré à terminé, **afin que** le planning dise où en est chaque tâche avant que le Kanban
(EP-09) n'en fasse un écran.

**Critères d'acceptation.**

- `WF-PLA-0130-A` — « Chacun de ces attributs est affiché dans la grille de planning, et ceux que
  MS Project connaît sont transportés par l’export. » : la grille, par US-1470 ; l'export, par
  US-1430 ; ici, `listNodes` rend chacun — libellé, description, durée, début, fin, mode,
  rattachement, état, `started_on`, `completed_on`, `total_float`, `is_critical` — ;
  `physical_progress` est d'EP-10, qui clôt, nul ici ;
- `WF-PLA-0130-A` — « Le passage à l’état démarré ou terminé demande une date, proposée au jour
  courant et modifiable. » : `setTaskProgress` écrit `occurred_on`, le jour du geste par défaut ;
  l'écran qui la propose est le Kanban d'EP-09 ;
- écart : `WF-PLA-0130-A` — « Un import de reste à engager qui met une tâche à zéro la date de la
  revue que porte le fichier ; une récapitulative porte la date de terminaison de sa dernière
  subordonnée. » : la récapitulative, ici ; l'import de reste à engager est d'EP-09, EP-10 clôt ;
- `WF-PLA-0130-A` — « La durée d’un jalon est nulle et n’est pas modifiable ; les dates d’une
  récapitulative ne sont pas saisissables. » : constaté par US-1380 ;
- `WF-PLA-0130-A` — « La marge totale, la criticité et l’avancement physique s’affichent et ne
  sont pas saisissables. » : la marge et la criticité, par US-1390 et US-1470 ; l'avancement
  physique est d'EP-10, qui clôt ;
- `WF-PLA-0130-A` — « Une terminaison datée avant le démarrage de la tâche est refusée. » :
  `setTaskProgress` refuse par 422 `VALUE_OUT_OF_RANGE` sur la date (US-1380/L4, #2519) ; écart :
  le jour par défaut se lit dans le fuseau horaire de l’installation (spécification 1.0.3, #2524),
  qui n'existe pas encore — le jour courant est pris en UTC, et le fuseau est reporté vers EP-07
  (#2527), qui clôt ;
- propre à l'US : `setTaskProgress` démarre, termine ou rouvre une tâche feuille, au compteur lu,
  et refuse par 409 — `task_is_milestone`, `task_without_lines` (jamais manquante sans ligne),
  `task_not_milestone`, `completed_milestone`, puis `project_in_progress` et
  `no_background_task_running` de `edit_remaining` — et par 422 `SUMMARY_TASK_DERIVED` sur une
  récapitulative ; un jalon terminé porte `started_on` égal à `completed_on`, rouvert il perd les
  deux ; une récapitulative est démarrée dès qu'une subordonnée l'est, terminée après la dernière,
  et porte la date de la première démarrée et de la dernière terminée ; `finish_overdue` est vrai
  pour une tâche démarrée dont la fin précède la date de calcul ;
- propre à l'US : `load-witness` pose les états des tâches du témoin par l'interface, et chaque
  réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** `setTaskProgress` est servie ici par l'API, sans écran (décision de
l'auteur du 2026-11-07) ; le Kanban d'EP-09 branche l'écran. La condition `project_in_progress`
se pose autour du service dans les tests, comme EP-04 l'a fait.

**Hors périmètre.** Le Kanban, la réestimation, la suppression renvoyée vers le reste à engager
(EP-09) ; l'avancement physique (EP-10).

---

## US-1420 — L'import en deux temps

- **statut** : à faire
- **exigences** : `WF-ARC-0100-A`, `WF-INTF-0080-A`, `WF-INTF-0090-A`, `WF-ARC-0110-A`,
  `WF-DAT-0120-A`
- **opérations** : `uploadFile`, `listImports`, `openImport`, `getImport`, `abandonImport`,
  `applyImport`
- **issue** : 2319

**En tant que** chef de projet, **je veux** déposer un fichier, lire le compte rendu de son
analyse, puis l'appliquer ou l'abandonner, **afin que** rien ne change dans mon projet sans que
je l'aie vu et confirmé — et que le devis (EP-07), le reste à engager et les coûts réels (EP-09)
s'importent de la même façon.

**Critères d'acceptation.**

- `WF-ARC-0100-A` — « Entre l’analyse et la confirmation, aucune donnée du projet n’a changé. » :
  la tâche `import_analysis` ne lit que le fichier et la structure, et n'écrit que le compte
  rendu ;
- `WF-ARC-0100-A` — « L’interruption de l’application laisse le projet dans son état
  antérieur. » : la tâche `import_apply` écrit en une transaction, un worker arrêté pendant elle
  laisse la base inchangée ;
- `WF-ARC-0100-A` — « Un compte rendu expiré ne peut plus être appliqué, et son fichier n’est
  plus sur le stockage objet. » : `applyImport` refuse par 409 `import_awaiting_decision` un
  import dont `expires_at` est passé, qu'il se lise `expired` ; la purge l'a passé `expired` et
  a supprimé son fichier ;
- `WF-ARC-0100-A` — « Un import confirmé par un utilisateur dont la permission est retirée avant
  l'exécution n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus
  sur le stockage objet. » : `applyImport` et la tâche revérifient la permission, la qualité de
  contributeur et l'état ; refusé, l'import passe `refused`, son fichier supprimé (#1790) ;
- `WF-ARC-0100-A` — « Il en va de même si le projet est passé dans un état terminal
  entre-temps. » : `project_not_terminal` ;
- `WF-ARC-0100-A` — « Une application refusée parce qu’un marquage est en cours sur le projet peut
  être redemandée après lui, sans nouveau dépôt. » : un refus passager laisse le compte rendu
  applicable et son fichier en place (spécification 1.0.3, #2523), réalisé par US-1380/L4 (#2519) ;
- `WF-INTF-0080-A` — « Pour un fichier qui contient des lignes invalides, le compte rendu les
  liste avec leur motif avant la confirmation. » : `ImportReport.rejected`, par le format
  (US-1430 pour MS Project) ; les lignes d'un devis sont d'EP-07, qui clôt ;
- `WF-INTF-0080-A` — « Si l’utilisateur abandonne à cette étape, le projet reste inchangé. » :
  `abandonImport`, 204, le fichier supprimé, idempotent sur un import terminé sans écrire, refusé
  par `import_not_applied` sur `applying` et `applied` ;
- `WF-INTF-0080-A` — « Si l’import est interrompu pendant son application, le projet revient à
  son état antérieur. »
- `WF-INTF-0090-A` — « On importe un planning MS Project, puis un devis, dans un projet qui
  comporte une révision marquée. » : le planning, par US-1430 ; le devis est d'EP-07, qui clôt ;
- `WF-INTF-0090-A` — « Seule la révision en cours est modifiée : les tâches, les dates et les
  montants de la révision marquée sont identiques avant et après chaque import. » : les tâches et
  les dates, ici ; les montants, EP-07 ;
- `WF-INTF-0090-A` — « Un import sur un projet dont toutes les révisions sont marquées crée une
  révision en cours d’élaboration et s’y applique ; les révisions marquées sont inchangées. » :
  l'application crée la révision par `create_revision` (EP-04), `may_create_revision` jugée à
  l'ouverture, `Import.revision_id` nul jusque-là ;
- écart : `WF-INTF-0090-A` — « L’import d’un planning sur la structure principale d’une révision
  qui porte un devis propre de risque laisse ce devis propre inchangé, tâches comprises ; l’import
  du même fichier sur ce devis propre laisse la structure principale inchangée. » : la structure
  visée (`structure_id`) est seule écrite ; une seconde structure ne se pose pas autour du service
  (`cost_structure.kind` n'admet que `main`), et les devis propres sont d'EP-08, qui clôt (cadrage
  d'EP-07, décision de l'auteur du 2026-11-07) ;
- `WF-ARC-0110-A` — « Aucune réponse de l'API ne contient de phrase destinée à l'utilisateur. »
- `WF-ARC-0110-A` — « Un import fait par un utilisateur en français, relu par un utilisateur en
  anglais, présente son compte rendu en anglais. » : le compte rendu est conservé en codes et
  paramètres (`import_report`), et l'écran le rend par son catalogue ;
- `WF-ARC-0110-A` — « Le journal d'audit d'une même action se lit dans la langue de chaque
  lecteur. » : constaté par EP-03 ;
- `WF-ARC-0110-A` — « Un courriel de réinitialisation part du fournisseur d'identité, dans la
  langue du compte. » : constaté par EP-03 ;
- `WF-DAT-0120-A` — « Après application ou abandon d’un import, le fichier correspondant n’est
  plus sur le stockage objet. »
- `WF-DAT-0120-A` — « Un fichier déposé et jamais confirmé disparaît au terme du délai
  d’expiration. » : `waterfall-worker purge`, lancé par le planificateur du Compose, passe
  `expired` les imports `analysed` échus et supprime leur fichier, et supprime les dépôts
  (`file_upload`) expirés, ceux d'EP-03 compris ;
- `WF-DAT-0120-A` — « Un export téléchargé jusqu’au bout n’est plus sur le stockage objet ; un
  téléchargement interrompu le laisse disponible ; un export jamais téléchargé en disparaît au
  terme de vingt-quatre heures. » : la purge supprime les exports échus ; le téléchargement et
  son export sont d'US-1430 ;
- propre à l'US : `uploadFile` dépose un fichier d'import en une fois (`purpose: import`), refuse
  au-delà de 10 Mio (413), refuse `external_backup` (422 `UPLOAD_PURPOSE_MISMATCH`) ; `openImport`
  lit l'en-tête par le format de `kind`, refuse par 422 `FILE_FORMAT_UNREADABLE` avec
  `expected_format`, 404 un dépôt inconnu, expiré ou consommé, 409 `project_not_terminal`,
  `no_background_task_running`, `may_create_revision`, résout la structure principale par défaut,
  et dépose `import_analysis` (202) ; `getImport` rend le compte rendu, la tâche et les commandes
  `apply` (`import_awaiting_decision`, `import_file_accepted`) et `abandon` (`import_not_applied`) ;
  `listImports` pagine du plus récent au plus ancien ; `applyImport` dépose `import_apply` (202),
  409 dans l'ordre d'I-01 ; les statuts `analysing`, `analysed`, `applying`, `applied`,
  `abandoned`, `expired`, `failed`, `refused` ; le fichier en transit vit sous un préfixe du
  compartiment du stockage objet ;
- propre à l'US : un format s'enregistre auprès du module par une interface — lire l'en-tête,
  analyser en un compte rendu, appliquer un compte rendu — sans que le module le nomme ; la
  mécanique est éprouvée par un format d'essai des tests, avant tout format réel ; chaque réponse
  est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Le module `core/exchanges` porte la table `import_report` (régime
« projet », §4.4.1) : l'import, son état, sa période, et son compte rendu en JSONB de codes. Les
genres de tâche `import_analysis` et `import_apply` existent au contrat et dans `background_task`.
Le verbe `purge` est une commande du worker comme `enqueue`, sous un verrou consultatif, planifiée
par le service `scheduler` du Compose (décision de l'auteur du 2026-11-07). Le contrat dit que
l'ouverture refuse le format et que l'analyse ne refuse plus (I-10).

**Hors périmètre.** Le format MS Project (US-1430) ; les formats Excel (EP-07, EP-09) ; l'écran
des échanges, branché par US-1430.

---

## US-1430 — Le format MS Project : import, export et aller-retour

- **statut** : à faire
- **exigences** : `WF-INTF-0040-A`, `WF-INTF-0050-A`, `WF-INTF-0060-A`, `WF-QUA-0080-A`,
  `WF-DAT-0120-A`
- **opérations** : `requestExport` (`ms_project_schedule`), `getBackgroundTaskResult` ;
  `openImport`, `getImport`, `applyImport` pour `ms_project_schedule`
- **issue** : 2321

**En tant que** chef de projet, **je veux** importer un planning MS Project dans ma révision en
cours, le retravailler dans MS Project et le réimporter sans perdre mes tâches, et exporter mon
planning pour qu'il s'ouvre dans MS Project aux mêmes dates, **afin de** démarrer et de partager
un planning avec l'outil que mes interlocuteurs connaissent.

**Critères d'acceptation.**

- `WF-INTF-0040-A` — « Un fichier XML produit par MS Project 2013 est importé sans erreur. » : un
  fichier du corpus, importé contre le service ;
- `WF-INTF-0040-A` — « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD,
  FF ou DF, et décalage — sont identiques à celles du fichier source ; une tâche en mode manuel
  du fichier est en mode manuel aux mêmes dates ; une tâche portant une contrainte « Pas avant
  le » est en mode manuel et signalée ; une tâche à 50 % d’avancement est importée non démarrée ;
  aucune ressource et aucun calendrier présents dans le fichier n’a été créé dans Waterfall, et
  l’utilisateur est informé que ces éléments ont été ignorés. » : `ImportReport.ignored` nomme
  les ressources, les calendriers, l'avancement, les coûts, les champs personnalisés et les
  contraintes de date ;
- écart : `WF-INTF-0040-A` — « Un planning exporté, retravaillé dans MS Project puis réimporté
  conserve les lignes de devis et les lignées de ses tâches, et ses tâches démarrées. » : les
  lignées, par l'identifiant unique que l'export écrit, et les tâches démarrées, conservées et
  signalées (`kept`), ici ; les lignes de devis sont d'EP-07, qui clôt ;
- `WF-INTF-0040-A` — « Un fichier qui place la tâche d’un poste hors du sous-arbre de la tâche de
  son lot est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée
  a disparu est appliqué et le compte rendu nomme le poste qu’elle portait ; une tâche rattachée
  réimportée conserve son rattachement. » : `refusals` par `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`,
  `ImportDifference.work_breakdown_label`, le rattachement intouché ;
- `WF-INTF-0050-A` — « Vérifiée en recette pour l’ouverture dans MS Project ; l’égalité des dates
  est couverte par le corpus de WF-QUA-0080. » : une phrase de méthode — l'ouverture dans MS
  Project est constatée en recette par l'auteur, aucun test à écrire ; l'égalité des dates, par le
  corpus ;
- `WF-INTF-0050-A` — « Un planning Waterfall exporté au format XML s’ouvre sans erreur dans les
  versions de MS Project visées par WF-INTF-0040. » : constaté en recette par l'auteur ; ici, le
  fichier est valide contre le schéma quand il est présent ;
- écart : `WF-INTF-0050-A` — « Les calendriers Waterfall y figurent et sont affectés aux tâches,
  et chaque tâche porte son identifiant Waterfall et, dans ses notes, sa description. » : le
  calendrier par défaut, la lignée et la description (#1339), ici ; les calendriers des rôles
  sont d'EP-07, qui clôt ;
- `WF-INTF-0050-A` — « En mode automatique, MS Project recalcule pour chaque tâche des dates de
  début et de fin identiques à celles affichées par Waterfall. » : par le corpus ;
- `WF-INTF-0060-A` — « Vérifiée en recette pour l’ouverture dans MS Project ; l’absence d’écart
  de dates est couverte par le corpus de WF-QUA-0080. » : une phrase de méthode — constatée en
  recette par l'auteur, aucun test à écrire ; l'absence d'écart, par le corpus ;
- écart : `WF-INTF-0060-A` — « Un planning comportant au moins une tâche récapitulative, un
  jalon, les quatre types de liaison, et des tâches portant des rôles de ressources aux
  calendriers différents, est exporté, ouvert dans MS Project sans y être modifié, puis
  réimporté. » : l'aller-retour sans ouverture dans MS Project, sur un planning à récapitulative,
  jalon et quatre types de liaison, ici ; les rôles sont d'EP-07, qui clôt ;
- `WF-INTF-0060-A` — « Le compte rendu ne présente aucun écart de dates ni de durées, et le
  planning obtenu est identique à celui relevé avant l’export. » : `differences` et
  `date_mismatches` vides ;
- `WF-INTF-0060-A` — « La date de début de planning est identique avant et après
  l’aller-retour. »
- `WF-INTF-0060-A` — « La description de chaque tâche est identique avant et après
  l’aller-retour. » (#1339) ;
- `WF-QUA-0080-A` — « Chaque cas cité par le corps figure dans au moins un planning du corpus. » :
  un test lit le corpus et nomme le cas qui manque ; sur le corpus partiel, il marque non
  exécutés, en citant #2645, les cas qu'aucun fichier ne déclare encore, et le lot de suite du
  dépôt les lève (décision du 2026-11-09) ; écart : `lag_negative_w`, qu'aucun planning ne porte,
  reste non exécuté en citant #2812 (« Le lot de suite d'US-1430 ») ;
- `WF-QUA-0080-A` — « La modification de la règle de calcul des dates fait échouer au moins un
  test du corpus. »
- `WF-QUA-0080-A` — « Leur exécution ne demande ni MS Project, ni base de données, ni
  navigateur. » : le lecteur et le moteur d'US-1390 sont purs ;
- `WF-QUA-0080-A` — « Chaque planning du corpus réimporté puis exporté par Waterfall est valide
  contre le schéma ; un élément exporté hors de l’ordre du schéma fait échouer ce test, et
  l’absence du schéma le marque non exécuté. » : le schéma est désigné par un réglage, le test
  `skip` sans lui ;
- `WF-DAT-0120-A` — « Après application ou abandon d’un import, le fichier correspondant n’est
  plus sur le stockage objet. » : constaté par US-1420 ;
- `WF-DAT-0120-A` — « Un fichier déposé et jamais confirmé disparaît au terme du délai
  d’expiration. » : constaté par US-1420 ;
- `WF-DAT-0120-A` — « Un export téléchargé jusqu’au bout n’est plus sur le stockage objet ; un
  téléchargement interrompu le laisse disponible ; un export jamais téléchargé en disparaît au
  terme de vingt-quatre heures. » : `getBackgroundTaskResult` transmet le fichier en flux et le
  supprime à la fin du premier téléchargement complet, `result_url` devenant nul ; un
  téléchargement interrompu le laisse ; la purge d'US-1420 supprime l'export échu ;
- propre à l'US : l'analyse rapproche les tâches par la lignée que l'export écrit, puis par
  `external_id`, crée les tâches sans identifiant, supprime celles absentes du fichier selon
  WF-PLA-0070 (démarrées et terminées conservées et signalées), remplace les liaisons et présente
  leurs écarts, lit la date de début du projet dans `planning_start_on` et la présente quand elle
  diffère (`cost_structure`, `planning_start_on`), signale une date manuelle chômée
  (`NON_WORKING_DAY`) et une récapitulative manuelle importée en automatique
  (`SUMMARY_TASK_DERIVED`), présente `date_mismatches`, rejette une tâche sous un jalon
  (`MILESTONE_HAS_NO_SUBTASK`, #1772), refuse le fichier entier par `PROJECT_HORIZON_EXCEEDED`
  (WF-PLA-0150) ou `ORDER_ITEM_OUTSIDE_WORK_PACKAGE`, signale des constantes d'unités autres que
  celles de l'installation, et compte `read_count` et `unchanged_count` ; `openImport` refuse un
  fichier qui n'est pas un XML MS Project par `FILE_FORMAT_UNREADABLE`, `expected_format` à
  `ms_project_schedule` ;
- propre à l'US : `requestExport` dépose une tâche `export` (202) pour la révision nommée, en
  cours ou marquée, la structure principale par défaut, sous `export_planning` ; le worker écrit
  le fichier XML — la date de début du projet, les constantes d'unités, chaque tâche avec son
  identifiant de lignée, ses notes, son mode, sa durée, ses dates, son calendrier de tâche, les
  liaisons avec leur type et leur décalage dans son unité — sur le stockage objet, et
  `BackgroundTaskRef.result_url` le désigne ; `getBackgroundTaskResult` répond 409
  `task_succeeded` avant, 404 après ;
- propre à l'US : l'écran des échanges (`…/exchanges`) et l'encart « Démarrer le projet »
  (import d'un fichier MS Project) travaillent contre le service, `MockupNotice` retiré de
  l'écran des échanges, les parcours `exchanges.spec.ts` et `tasks.spec.ts` étiquetés `@shared`
  pour ce que le service sert ; chaque réponse est validée contre le contrat dans les tests du
  service.

**Notes de réalisation.** Le corpus de WF-QUA-0080 est un préalable fourni par l'auteur
(« Préalables ») ; la bibliothèque XML et la place du corpus se fixent à la conception. L'export
est le premier résultat de tâche à télécharger : `result_url` des tâches `export` est la route de
`getBackgroundTaskResult`. Les constantes d'unités du fichier (`MinutesPerDay`, `MinutesPerWeek`,
`DaysPerMonth`) sont lues pour convertir les durées en heures et signalées quand elles diffèrent
(WF-PLA-0160).

**Hors périmètre.** Les formats Excel (EP-07, EP-09) ; l'image de l'arborescence (US-1440) ; les
lignes d'une tâche réimportée (EP-07).

---

## US-1440 — L'arborescence de tâches et son export PNG

- **statut** : à faire
- **exigences** : `WF-PLA-0110-A`, `WF-PLA-0120-A`
- **opérations** : `listNodes` (`summaries_only`, `max_level`) ; `requestExport`
  (`task_tree_image`), `getBackgroundTaskResult`
- **issue** : 2323

**En tant que** chef de projet, **je veux** lire les récapitulatives de mon planning en
arborescence jusqu'au niveau que je choisis, et en exporter une image à imprimer, **afin de**
présenter la structure du projet sans ses détails.

**Critères d'acceptation.**

- `WF-PLA-0110-A` — « Sur un planning de quatre niveaux, l’affichage demandé au niveau 2 ne
  représente que les récapitulatives des deux premiers niveaux, sous le nœud du projet. » :
  `listNodes` avec `kinds=task`, `summaries_only` et `max_level=2`, le front n'appliquant plus le
  critère à la réponse (#496), et `summary_depth` à 4 quel que soit `max_level` ;
- `WF-PLA-0110-A` — « Aucun jalon ni aucune tâche feuille n’apparaît, quel que soit le niveau
  demandé. »
- `WF-PLA-0110-A` — « Un planning composé uniquement de tâches feuilles produit une arborescence
  réduite au nœud du projet. » : `summary_depth` à 0, aucun nœud rendu ;
- `WF-PLA-0120-A` — « L’export d’un planning de trois niveaux produit un fichier PNG dont le
  premier niveau est disposé horizontalement et les suivants verticalement. » : la tâche `export`
  de genre `task_tree_image`, dessinée par le worker, téléchargée par `getBackgroundTaskResult`
  (`image/png`) ;
- `WF-PLA-0120-A` — « Le contenu ne dépend que du niveau demandé. » : `ExportRequest.depth`, 422
  `VALUE_OUT_OF_RANGE` sous 1 ;
- `WF-PLA-0120-A` — « L’export d’une arborescence trop large pour une page produit une image plus
  large que la page, sans réduction. »
- `WF-PLA-0120-A` — « L’export d’une arborescence dont l’image dépasserait cent millions de pixels
  échoue, et l’échec le dit. » : `TASK_TREE_IMAGE_TOO_LARGE`, calculé avant le rendu (spécification
  1.0.3, #2522), réalisé par US-1440/L2 (#2343) ;
- propre à l'US : l'image porte le libellé du projet, de la révision et la date de calcul, dans
  la langue du compte demandeur (WF-ARC-0110) ; l'écran de l'arborescence (`…/task-tree`)
  travaille contre le service, offre l'export sous `export_task_tree_image`, et son parcours
  (`planning.spec.ts`, l'arborescence) porte `@shared` ; chaque réponse est validée contre le
  contrat dans les tests du service.

**Notes de réalisation.** La bibliothèque d'image du worker se fixe à la conception. Le témoin
offre `nodes_nested`, une variante à quatre niveaux ; contre le service, l'arborescence de
PRJ-001 a la profondeur que `summary_depth` dit.

**Hors périmètre.** Les exports PNG du Gantt et d'une chronologie, faits par le front (EP-15).

---

## US-1450 — Le collage et l'annulation servis par le serveur

- **statut** : à faire
- **exigences** : `WF-IHM-0110-A`
- **opérations** : `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo`
- **issue** : 2322

**En tant que** chef de projet, **je veux** coller dans la grille de planning un bloc venu d'un
tableur après en avoir vu le compte rendu, annuler mes saisies une par une et les rétablir, et
être prévenu quand un autre contributeur a repris ce que je voudrais annuler, **afin de** saisir
vite sans craindre une fausse manœuvre.

**Critères d'acceptation.**

- `WF-IHM-0110-A` — « La suppression d’une tâche puis son annulation restituent la tâche, ses
  lignes et ses liaisons. » : la tâche et ses liaisons, ici, avec ses inscriptions ; les lignes
  sont d'EP-07, EP-08 clôt ;
- écart : `WF-IHM-0110-A` — « Le réexamen d’un risque puis son annulation lui rendent sa
  probabilité et son état précédents. » : les risques sont d'EP-08, qui clôt ;
- `WF-IHM-0110-A` — « Cinquante modifications successives s’annulent une par une, puis se
  rétablissent dans l’ordre. » : contre le service, par l'API et par la grille (US-1470) ;
- `WF-IHM-0110-A` — « L’annulation d’une modification qu’un autre contributeur a depuis reprise
  est refusée en nommant l’objet en conflit. » : 409 `UNDO_CONFLICT`, `conflicting_object_id` et
  `conflicting_object_label`, jugé sur le compteur des nœuds que l'entrée a écrits ;
- `WF-IHM-0110-A` — « Aucune commande n’annule un marquage, un import appliqué, une déclaration
  de survenance ou une exclusion de ligne de coût. » : le marquage et l'abandon vident
  l'historique de la révision, un import appliqué n'y entre pas ; la survenance et l'exclusion
  sont d'EP-08 et d'EP-09, EP-08 clôt ;
- propre à l'US : chaque écriture de nœud de l'EPIC — cellule, création, suppression,
  déplacement, collage, liaison, avancement, inscription, structure — inscrit dans la transaction
  une entrée d'`undo_entry` (révision, compte, session de connexion, nature `UndoneKind`, instantanés
  avant et après) ; `undoLastChange` et `redoLastUndo` défont et refont la dernière, rendent
  `UndoResult` avec `NodesWritten` et `remaining_depth`, refusent par `undo_history_not_empty` et
  `redo_history_not_empty`, et une annulation subit les règles de la saisie ; l'historique garde
  au moins cinquante entrées par révision et par utilisateur, et ne survit ni au marquage, ni à
  l'abandon, ni à la session ;
- propre à l'US : `previewPaste` juge un bloc collé sur la facette tâche dans l'ordre de
  `NodeColumn` — `COMPUTED_VALUE`, `FIELD_NOT_ACCEPTED`, `NON_WORKING_DAY`, les règles du
  rattachement ; chaque ligne du bloc écrit le nœud existant à la même distance sous le nœud visé,
  et chaque ligne au-delà du dernier nœud de la structure crée une tâche, sœur du dernier nœud
  écrit (même parent, même genre que le nœud visé), dont le libellé est requis — la ligne dont il
  manque est refusée, sa colonne nommée — et dont les autres cellules se jugent comme celles d'une
  tâche qui s'écrit ; le compte rendu dit combien de lignes écrivent et combien créent
  (`created`) ; il refuse un bloc trop large (422 `PASTE_TOO_WIDE`,
  `max_columns`), et garde le plan (`paste_plan`) avec le compteur de la structure ;
- écart : #1772 au collage — une ligne du bloc qui placerait une tâche sous un jalon est refusée
  par `MILESTONE_HAS_NO_SUBTASK`, `params` nommant le jalon, la ligne n'étant pas écrite : la
  création du collage passe par la fonction de `createNode`, qui porte déjà ce refus, et un test
  unitaire l'éprouve ; aucun parcours d'EP-06 ne l'atteint, une tâche créée sœur d'une tâche n'ayant
  jamais un jalon pour parent, et le cas — la sœur d'une ligne de devis d'un jalon — demande des
  lignes : la preuve par parcours est d'EP-07, US-1560, qui clôt ;
- propre à l'US : `applyPaste` écrit les lignes acceptées, existantes et créées, en une opération et
  une seule entrée d'historique, rejuge, 412 si la structure a changé, et rend `PasteApplied`, dont
  `nodes` porte les tâches créées ; annuler le collage supprime les tâches qu'il a créées, le
  rétablir les recrée ; un plan abandonné n'écrit ni ne crée rien ;
- propre à l'US : Annuler et Rétablir de la grille de planning sont branchées (`undo-commands.tsx`,
  #1057), leur refus dit par le catalogue, le collage de la grille de planning joue contre le
  service, et les parcours `undo.spec.ts` et `paste.spec.ts` portent `@shared` pour ce qu'ils
  jouent sur le planning ; chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** L'historique et le plan de collage vivent dans PostgreSQL
(`undo_entry`, `paste_plan` ; décision de l'auteur du 2026-11-07), hors du Tableau 10 du §4.4.1,
que l'issue de spécification de l'EPIC demande de compléter. La session est la session de
connexion de Keycloak, dont la revendication `sid` du jeton survit à ses rafraîchissements — lier la
pile au jeton d'accès lui-même la viderait à chaque rafraîchissement, toutes les cinq minutes ;
la conception dit où l'API lit `sid` ; un jeton valide sans `sid` est refusé par `undoLastChange`
et `redoLastUndo` (403 `SESSION_ID_MISSING`, #2472), dont le lot écrit la clé de catalogue (#2537,
« Les catalogues du front et le collage »). La purge d'US-1420 retire les entrées d'une session
finie et les plans échus. Le collage qui crée les tâches au-delà de la dernière ligne (#2559,
option B) est décidé après les lots L1 à L3 : les lots suivants le construisent (« Le collage qui
crée »), et l'US n'est finie qu'à leur fusion.

**Hors périmètre.** Les colonnes de la ligne de devis dans un collage (EP-07) ; l'annulation des
saisies de risque (EP-08).

---

## US-1460 — Le squelette de planning engendré du lotissement

- **statut** : à faire
- **exigences** : `WF-PRJ-0030-A`, `WF-PLA-0170-A`
- **opérations** : `generatePlanningSkeleton` ; `getWorkBreakdown`, `createRevision`
- **issue** : 2325

**En tant que** chef de projet, **je veux** engendrer d'un coup, depuis mon lotissement, les
récapitulatives, les livrables et les jalons de fin de mon planning, **afin de** ne pas ressaisir
une structure que le bon de commande donne déjà.

**Critères d'acceptation.**

- `WF-PRJ-0030-A` — « La génération sur un lotissement de deux lots et trois postes produit les
  récapitulatives, rattachées à leur lot ou à leur poste, les feuilles et les jalons attendus,
  avec leurs liaisons. »
- `WF-PRJ-0030-A` — « Elle n’est plus proposée dès que la structure principale comporte une tâche,
  et ne l’est jamais sur un différentiel ni sur le devis propre d’un risque. » :
  `RevisionCommand.generate_skeleton` et `ProjectCommand.generate_skeleton`,
  `main_structure_without_tasks` puis `no_background_task_running`, `revision_draft` sur une
  révision marquée ; l'opération ne nomme aucune structure ;
- `WF-PRJ-0030-A` — « Renommer un poste ensuite ne change aucune tâche ; le supprimer ne déplace
  ni ne supprime aucune tâche, et retire le seul rattachement de celle qui le portait
  (WF-PLA-0170). »
- `WF-PRJ-0030-A` — « Sur le lotissement par défaut, la génération produit une récapitulative de
  lot, une récapitulative de poste sans feuille, et leurs deux jalons de fin. » : l'exemple
  `skeleton_generated`, rejoué contre le service ;
- `WF-PLA-0170-A` — « Une feuille peut être rattachée à un poste ; une récapitulative rattachée
  dont on supprime la dernière subordonnée garde son rattachement. » : constaté par US-1380 ;
- `WF-PLA-0170-A` — « Le rattachement d’une tâche à un poste déjà porté par une autre est refusé,
  comme celui d’une même tâche à un lot et à un poste. » : constaté par US-1380 ;
- `WF-PLA-0170-A` — « Le déplacement de la tâche d’un poste hors du sous-arbre de la tâche de son
  lot est refusé. » : constaté par US-1380 ;
- `WF-PLA-0170-A` — « La suppression d’un poste porté par une tâche de la révision en cours
  aboutit ; la tâche reste et ne porte plus de rattachement ; une révision marquée qui la citait
  l’affiche toujours rattachée. » : constaté par US-1380 ;
- `WF-PLA-0170-A` — « Après suppression d’un poste sur un projet sans révision en cours, la
  révision créée ensuite ne porte plus ce rattachement ; la révision marquée l’affiche
  toujours. » : constaté par US-1380 ;
- `WF-PLA-0170-A` — « La génération du squelette n’est pas proposée sur le devis propre d’un
  risque. » : la commande est de la révision et engendre sur la principale ; les devis propres
  sont d'EP-08 ;
- écart : `WF-PLA-0170-A` — « La fusion d’un différentiel qui déplacerait la tâche d’un poste hors
  du sous-arbre de la tâche de son lot est refusée en nommant la tâche. » : EP-08, qui clôt ;
- écart : `WF-PLA-0170-A` — « Une tâche rattachée au poste 2 dont un différentiel allonge la
  durée porte toujours ce rattachement après la fusion. » : EP-08 ;
- propre à l'US : les jalons de fin de poste ont pour prédécesseurs les livrables du poste, le
  jalon de fin de lot ceux de ses postes, les feuilles sont automatiques d'un jour, la réponse est
  `NodesWritten` dans l'ordre du plan ; l'encart « Démarrer le projet » et « Engendrer le
  planning » du lotissement travaillent contre le service, et `project-start.spec.ts` perd son
  garde `BEFORE_EP06` ; chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** L'écran est celui d'EP-14/L44d et d'EP-15/US-0490. Sur un projet sans
révision en cours, l'écran ouvre la révision d'abord (`createRevision`, EP-04), puis engendre.

**Hors périmètre.** Les devis propres et les différentiels (EP-08).

---

## US-1470 — La grille de planning et le Gantt branchés sur le service

- **statut** : à faire
- **exigences** : `WF-PLA-0080-A`, `WF-PLA-0090-A`, `WF-ADM-0110-A`, `WF-INTF-0010-A`
- **opérations** : toutes celles de l'EPIC que la grille de planning et le Gantt lisent et
  écrivent
- **issue** : 2326

**En tant que** chef de projet, **je veux** que la grille de planning et le Gantt travaillent
contre le service — saisie, prédécesseurs, rattachement, date de début de planning, menu
contextuel, commandes, chemin critique et conflits — **afin de** construire un planning sans faux
back.

**Critères d'acceptation.**

- `WF-PLA-0080-A` — « Chacune des colonnes citées est présente. » : contre le service, chaque
  colonne lue de `listNodes` ;
- `WF-PLA-0080-A` — « L’indentation d’un groupe de tâches déplace le groupe entier sous la tâche
  précédente. » : `moveNodes` contre le service, le report lu dans la grille de devis
  (#1057, sur des tâches) ;
- `WF-PLA-0080-A` — « La recherche sur un libellé ne laisse voir que les tâches correspondantes
  et leurs parents. » : `search` tenu par le serveur ;
- `WF-PLA-0080-A` — « Les trois sortes de tâches se distinguent sans lire leur durée. » :
  `is_summary` et `is_milestone` du serveur ;
- `WF-PLA-0080-A` — « Une tâche terminée se distingue d’une tâche démarrée sans lire de colonne ;
  une feuille ne porte pas d’avancement physique. » : `progress` et `physical_progress` nul du
  serveur, sur les tâches du témoin ;
- `WF-PLA-0080-A` — « Le filtre sur un poste ne laisse voir que la tâche qui le porte, son
  sous-arbre et ses parents. » : `order_item_id` tenu par le serveur ;
- `WF-PLA-0090-A` — « Les liaisons et la hiérarchie sont visibles, ainsi que le chemin
  critique. » : `is_critical` du serveur ;
- `WF-PLA-0090-A` — « Aucune action de la souris ou du clavier ne modifie une tâche depuis le
  Gantt. »
- `WF-PLA-0090-A` — « Une récapitulative pliée dans la grille l’est dans le Gantt, et
  réciproquement. » : constaté par EP-02/L40, rejoué contre le service ;
- `WF-ADM-0110-A` — « Un utilisateur habilité à modifier le planning et porteur de « consulter
  tous les projets », mais non contributeur d’un projet, voit ce planning et ne peut pas le
  modifier, ni par la grille ni par import. » : 200 sur `listNodes`, 403 `NOT_CONTRIBUTOR` sur
  chaque écriture et sur `openImport` (US-1420) ;
- `WF-ADM-0110-A` — « Inscrit comme contributeur, il le modifie. »
- `WF-ADM-0110-A` — « Un utilisateur sans la permission de consultation ne voit pas le projet,
  même contributeur ; un contributeur sans « consulter tous les projets » ne voit que ses
  projets. » : constaté par EP-04 ;
- `WF-ADM-0110-A` — « Une adresse d’objet inexistant et une adresse d’objet non consultable mènent
  au même écran. » : constaté par EP-04 ; ici, le même 404 sur une structure, un nœud, un numéro
  de ligne ;
- `WF-ADM-0110-A` — « Un utilisateur connaît la liste de ses permissions effectives, et elle
  change immédiatement lorsqu'un de ses rôles est modifié. » : constaté par EP-03 ;
- `WF-INTF-0010-A` — « Un utilisateur porteur du rôle prédéfini « chef de projet » crée un projet
  et atteint, sur un projet où il est habilité, les fonctions de gestion des révisions (FBS-4.1),
  de paramétrage du projet, contributeurs compris (FBS-4.2), de planification (FBS-4.3), de
  chiffrage (FBS-4.4), de gestion des risques (FBS-4.6), d’estimation du reste à engager
  (FBS-4.5), de gestion des coûts réels (FBS-4.7), de lecture des indicateurs (FBS-4.8), de
  sortie du cycle de vie (FBS-4.9) et d’échange des fichiers du tableau des flux (FLX-01 à
  FLX-07), et les mène jusqu’à leur terme, marquage d’une révision, exclusion d’une ligne de coût
  et déclaration d’une sortie compris. » : la planification (FBS-4.3) et les flux FLX-01 et
  FLX-02, ici, par le compte « chef de projet » de la course ; les révisions, le paramétrage et la
  sortie, constatés par EP-04 ; le chiffrage, les risques, le reste à engager, les coûts réels,
  les indicateurs et les autres flux sont d'EP-07 à EP-10, EP-08 clôt ;
- propre à l'US : la grille de planning lit `listNodes` servi, écrit chaque cellule par
  `updateTaskFacet`, les prédécesseurs par `setPredecessors` et `resolveRowNumber`, la date de
  début par `updateCostStructure`, le rattachement, les commandes de structure, et montre les
  tâches redatées, les conflits et le chemin critique que le serveur rend ; `MockupNotice` est
  retiré de l'écran du planning et les aides `frontend/help/fr/FBS-4.3*.md` disent ce que le
  service fait ; les parcours `planning.spec.ts`, `structure.spec.ts`, `computed.spec.ts`,
  `keyboard.spec.ts` et la part du planning de `grid.spec.ts` et de `context.spec.ts` portent
  `@shared` pour ce qu'ils jouent contre le service ; le parcours du report d'une grille à l'autre
  (#1057) crée une tâche depuis la grille de devis et la lit dans le planning ;
- propre à l'US : la mesure, contre le service, du temps entre la validation d'une cellule et
  l'application de la ligne rendue (#196) et du coût d'un déplacement de la cellule active sur
  les mille tâches de PRJ-001 (#620) s'écrit au relevé de livraison ; aucune optimisation sans
  elle.

**Notes de réalisation.** Les écrans sont ceux d'EP-02/L40, d'EP-14 et d'EP-15 (US-0460 à
US-0530) ; cette US ne les réécrit pas. Un manque que le branchement révèle devient une issue ;
un manque du contrat, une « Interface contract issue ».

**Hors périmètre.** La grille de devis et celle du reste à engager (EP-07, EP-09) ; l'avancement
physique (EP-10).

---

## US-1480 — Le témoin : la tranche des tâches, et les parcours rejoués

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`
- **opérations** : aucune en propre ; le chargement passe par les interfaces du noyau
- **issue** : 2327

**En tant que** développeur, **je veux** charger sur une plateforme qui porte les projets du
témoin les mille tâches de PRJ-001, leurs liaisons, leurs états, leurs inscriptions et ses
chronologies, et rejouer contre le service tous les parcours du planning écrits sur le faux back,
**afin que** les tests déjà écrits prouvent le service et que le planning du plus gros projet
s'affiche.

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les
  volumes annoncés. » : pour la tranche des tâches — les mille tâches de la structure principale
  de la révision en cours de PRJ-001 et des révisions marquées 100 et 101, leurs liaisons, leurs
  modes et leurs durées, leurs états et leurs dates de démarrage et de terminaison, les
  inscriptions, les deux chronologies, la date de début de planning —, chargée par
  `waterfall-api load-witness` après celle des projets, par les interfaces, avec les identifiants
  et les instants du témoin, les tâches des révisions marquées chargées avant leur marquage ; les
  lignes sont d'EP-07, les volumes entiers d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes
  identiques. » : deux plateformes chargées portent les mêmes identifiants, lignées et dates ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les libellés sont ceux du témoin, fictifs ;
- propre à l'US : `make mock-data` écrit, à côté des exemples, le fichier de la tranche des
  tâches que la commande lit, sans que le back importe `wftools` ; la commande lit ce fichier,
  `timelines.json` et les exemples de `listNodes`, validés par les modèles du contrat ; les
  lectures du témoin chargé — `nodes_planning`, `nodes_summaries`, `nodes_timeline`,
  `nodes_milestone`, `volume/nodes_thousand` — sont comparées aux exemples, aux colonnes d'audit
  et aux montants près, listés dans le test ;
- propre à l'US : tous les parcours du planning, du Gantt, de l'arborescence, des chronologies
  et des échanges étiquetés `@shared` passent contre le service, le témoin chargé — la frise et le
  focus de `timelines.spec.ts`, dont les dates dépendent des calendriers des lignes, sont
  étiquetés `@shared` par US-1570 en EP-07 (#2594, décision du 2026-11-09) — ; la définition
  de fini est constatée — cinquante saisies annulées puis rétablies, un collage prévisualisé puis
  appliqué, un import MS Project appliqué, un aller-retour sans écart, les exports produits — ;
  les entrées du guide que `BEFORE_EP06` et `BEFORE_THE_DATA` (le planning) gardaient sont
  levées, et le guide dit ce que la tranche charge et ce qu'EP-07 y ajoute.

**Notes de réalisation.** La tranche suit les règles du chargeur d'EP-05 et la chronologie d'EP-04
(`Act.at`) : les tâches des révisions 100 et 101 s'écrivent avant leur marquage, dans l'ordre des
événements, et les dates sont celles que le moteur calcule — le calculé devient l'attendu, et un
désaccord avec une fixture se tranche par la spécification. Le fichier de la tranche est un lot
d'outil, lançable tôt, comme US-0990/L1.

**Hors périmètre.** Les lignes, les risques et les coûts du témoin (EP-07 à EP-09) ; les trois
cents projets (EP-13).

---
id: EP-10
titre: Lire où en est un projet : avancement, indices, projections et courbes
statut: en cours
depend_de: EP-09
famille: front, back
issue: 2427
---

# EP-10 — Indicateurs de projet

## Objet

La date et le périmètre de calcul, la granularité par sous-projet, la valeur acquise,
l'avancement financier et physique, les projections à terminaison, les indices de coût et de
délai et leurs seuils, le diagramme temps/temps, la courbe des coûts cumulés avec sa lecture
en décaissements, et les courbes de valeur acquise. Les indicateurs d'une révision marquée sont
calculés dans la transaction qui la marque et conservés ; ceux de la révision en cours sont
calculés à la demande et mis en cache.

Il vient dès qu'un projet a une référence, des coûts réels et un reste à engager, avant les
risques et les avenants (revue de la ventilation, 2026-10-09) : le pilotage d'un projet en
cours sert avant ces événements plus rares, qui le modifient ensuite. C'est ici que se closent
les Vérif des EPIC antérieurs qui citaient un indicateur — les tâches ajoutées en cours
d'exécution, l'avancement physique de la grille de planning — ; celles qui citent un risque
survenu, une fusion ou un avenant se closent en EP-08, qui dispose alors des indicateurs.

## Ce qui en fait partie

- chacun des indicateurs du §3.4.5.8, pour le projet et pour chaque sous-projet, l'ensemble
  « hors sous-projet » compris ;
- la présentation « non calculable » d'un indicateur au dénominateur nul ;
- les seuils de vigilance et d'alerte appliqués aux indices, sur l'échelle de signalement
  commune ;
- le calcul au marquage, dans la même transaction, et la conservation des indicateurs ;
- le cache des indicateurs de la révision en cours et son invalidation ;
- le diagramme temps/temps sur l'identité de lignée des jalons inscrits ;
- les courbes, rendues par Apache ECharts ;
- les écrans des indicateurs de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- les indicateurs devant un risque survenu, une fusion ou un avenant — EP-08, qui clôt
  WF-IND-0030 et WF-IND-0100 sur ces cas ;
- l'agrégation sur plusieurs projets — EP-11 ;
- la mesure des temps de réponse aux volumes du §4.6.2 — EP-13.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
WF-REF-0130 est commencée par EP-05 et EP-07 et close ici : son Vérif demande la zone de l'indice
de coût d'une révision marquée (cadrage d'EP-07, décision de l'auteur du 2026-11-07). WF-RAE-0030
est commencée par EP-15 et EP-09 et close ici : son Vérif demande la valeur acquise (cadrage
d'EP-09, décision de l'auteur du 2026-11-07). WF-DAT-0040, que le tableau disait close ici, est
recalée (décision de l'auteur du 2026-11-07, au cadrage d'EP-10) : une phrase de son Vérif demande
une vue de portefeuille à une date passée sur trois cents projets, risques compris, qu'EP-11
construit — EP-10 la commence, conserve au marquage ce que ses lectures et celles d'EP-07 et d'EP-09
servent, et EP-11 clôt en conservant de plus ce que le portefeuille lit. Deux exigences qu'EP-10
réalise en partie entrent au tableau en portée « début », pour que l'US du témoin les cite et que
les tests les nomment (même décision) : WF-QUA-0040 et WF-INTF-0010. Chaque US cite les
exigences dont une phrase de Vérif tient avec une référence, des tâches, des lignes, des coûts
réels et un reste à engager ; les phrases qui demandent un risque, un avenant ou le portefeuille
sont des écarts, qui nomment l'EPIC qui les clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IND-0010-A` | Date et périmètre de calcul | entière | US-1660, US-1670 |
| `WF-IND-0020-A` | Granularité des indicateurs | entière | US-1660 |
| `WF-IND-0030-A` | Valeur acquise | début — close en EP-08 | US-1660 |
| `WF-IND-0040-A` | Avancement financier et consommation du budget | entière | US-1660 |
| `WF-IND-0050-A` | Projections à terminaison | entière | US-1660 |
| `WF-IND-0060-A` | Avancement physique | entière | US-1660, US-1680 |
| `WF-IND-0070-A` | Indice de coût | entière | US-1660 |
| `WF-IND-0080-A` | Indice de délai | entière | US-1660 |
| `WF-RAE-0050-A` | Tâches ajoutées en cours d’exécution | fin — amorcée en EP-09 | US-1660 |
| `WF-REF-0170-A` | Seuils d’alerte des indices | fin — amorcée en EP-05 | US-1660 |
| `WF-DAT-0040-A` | Conservation des indicateurs des révisions marquées | début — close en EP-11, amorcée aussi en EP-04 | US-1670 |
| `WF-CYC-0090-A` | Confirmation des sorties | fin — amorcée en EP-04 | US-1670 |
| `WF-REF-0130-A` | Modification sans effet rétroactif | fin — amorcée en EP-05, EP-07 | US-1670 |
| `WF-PLA-0130-A` | Attributs d’une tâche | fin — amorcée en EP-06 | US-1680 |
| `WF-IND-0100-A` | Courbe de coûts cumulés | début — close en EP-08 | US-1690 |
| `WF-IND-0110-A` | Courbes de valeur acquise | entière | US-1690 |
| `WF-IND-0130-A` | Évolution des indices | entière | US-1700 |
| `WF-IND-0090-A` | Diagramme temps/temps | entière | US-1710 |
| `WF-PLA-0060-A` | Inscription aux suivis | fin — amorcée en EP-06, EP-15 | US-1710 |
| `WF-DAT-0030-A` | Identité de lignée des objets d’une révision | fin — amorcée en EP-04 | US-1710 |
| `WF-RAE-0030-A` | Démarrage d’une tâche | fin — amorcée en EP-15, EP-09 | US-1710 |
| `WF-DAT-0130-A` | Contenu et invalidation du cache | entière | US-1720 |
| `WF-ARC-0070-A` | Autorité du serveur | fin — amorcée en EP-04 | US-1730 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06, EP-07, EP-09 | US-1740 |
| `WF-INTF-0010-A` | Usages du chef de projet | début — close en EP-08, amorcée aussi en EP-06, EP-07, EP-09 | US-1740 |

## Opérations du contrat

Servies ici pour la première fois (5) :

- `analysis` : `getProjectIndicators` (US-1660), `getCostCurve`, `getEarnedValueCurves` (US-1690),
  `getIndexHistory` (US-1700), `getMilestoneTracking` (US-1710).

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute :

- `revisions` : `markRevision` et `exitProject` (le calcul et la conservation des indicateurs dans
  la transaction du marquage, par le registre d'EP-04), `listNodes` (`TaskFacet.physical_progress`,
  nul depuis EP-06), `createNode`, `setTaskProgress`, `updateEstimateLine`, `setLineRemaining`,
  `setNodeTracking` (ce que chacune change aux indicateurs, à la valeur acquise et au temps/temps) ;
- `analysis` : `getEstimateIndicators` (EP-07) et `getRemainingIndicators` (EP-09), dont
  `context.is_stored` devient vrai pour une révision marquée, lue sur ce que son marquage a
  conservé ;
- `reference` : `getReferenceSettings`, `updateReferenceSettings` (les seuils, qui classent les
  indices à la lecture) ;
- `exchanges` : `applyImport` et `costs` : `setActualCostTrackedScope` (ce qu'un import de coûts et
  une exclusion changent au calcul du jour, et ne changent pas aux indicateurs conservés).

Aucune opération ne manque au contrat, figé en 1.0.0 : un écart devient une « Interface contract
issue » que l'auteur tranche. Le cadrage en relève un, « à trancher » : le refus de `as_of`
antérieur à toute révision marquée à l'état En cours, que le contrat ne décrit pas (#2449 ; US-1670,
« Notes de réalisation »).

## Constats reçus

Relevés par la revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`)
et tranchés par l'auteur le 2026-11-01 : EP-16 en écrit le contrat (US-0704 #1735), que le service
suit une fois figé.

- #1779 — l'évolution des indices et le temps/temps avant l'état En cours : aucun point pour une
  révision marquée en chiffrage, et le 409 des autres lectures d'indicateurs projets (G-01, G-02 ;
  contrat #1777, #1778). US-1670 (le 409 de `getProjectIndicators` et des courbes, l'offre sans
  indicateur conservé), US-1700 (`getIndexHistory` : aucun point, le point non calculable jamais
  omis, le 409), US-1710 (`getMilestoneTracking` : aucun point, le 409).

Relevé par la revue locale d'US-0960 (EP-04, #2061) et reporté au cadrage d'EP-06 (décision du
2026-11-06) :

- #2180, point 2 — `compute_indicators` n'écrit pas sa politique d'erreur : le point 1, le test
  des points d'entrée, est corrigé par US-1380/L1 #2328 d'EP-06, qui n'est pas fusionné à
  l'ouverture des issues d'EP-10 ; le point 2 s'ouvre en constat propre d'EP-10 (#2450), rattaché à
  US-1670/L1 #2440 — « le marquage échoue entièrement si le calcul de ses indicateurs échoue »
  (WF-DAT-0040), une exception du calcul fait échouer la tâche avec son code, rien n'étant écrit,
  et le test des points d'entrée dit à partir de quel lot le worker porte l'extension.

## Préalables

`epic/EP-10` se tire d'`epic/EP-09` dès la fusion de son lot pivot, **US-1580/L1 #2398** — le socle
d'EP-09, qui pose `cost_line` et `cost_import`, les colonnes `previous_*` et `reestimated_at`
d'`estimate_line`, la chaîne des migrations arrêtée à `0025`, et l'interface déclarée que les
indicateurs liront : `actual_costs_until` et `actual_cost_by_subproject` de `core/costs`,
`remaining_of_revision` et `startable_tasks` de `core/estimate` —, et non de `main` à la livraison
d'EP-09 (décision de l'auteur du 2026-11-07, pour toute la série EP-06 → EP-07 → EP-09 → EP-10 →
EP-08 ; l'exception du README, « Branches ») : elle reprend `epic/EP-09` à chaque lot que celui-ci
fusionne — qui reprend elle-même `epic/EP-07`, qui reprend `epic/EP-06` — et se fusionne dans
`main` après elle. Les lots d'EP-10 qui lisent des coûts attendent aussi US-1610/L2 #2404
(l'application d'une extraction, le journal), ceux qui lisent un reste US-1580/L2 #2399 (la
réestimation, `previous_*`), ceux qui lisent l'avancement des tâches US-1410 #2324 d'EP-06, ceux
qui lisent la valeur planifiée US-1520/L1 #2376 et L2 #2377 d'EP-07, ceux qui lisent les jalons
inscrits US-1400/L2 #2340 d'EP-06, ceux qui remplissent le marquage US-1500/L2 #2375 d'EP-07
(`register_marking`, avant `compute_indicators`) ; chaque lot nomme ceux qu'il attend par leur
numéro (conception, « Ce qu'EP-09 écrit encore », « Ce qu'EP-07 écrit encore », « Ce qu'EP-06
écrit encore »). La valeur acquise, les indices et les projections se calculent sur la
référence, les coûts réels et le reste à engager.

EP-16 livré, le contrat figé en 1.0.0 : un écart devient une « Interface contract issue » que
l'auteur tranche.

## Définition de fini

- les exemples chiffrés des Vérif du §3.4.5.8 qui ne citent ni risque survenu ni avenant, et
  ceux de WF-RAE-0050, sont des tests qui passent (WF-QUA-0020) ;
- le marquage échoue entièrement si le calcul de ses indicateurs échoue, et les indicateurs
  conservés sont inchangés après un import de coûts postérieur ; une offre marquée en chiffrage
  conserve son devis et aucun indicateur projet ;
- après vidage du cache, les valeurs recalculées sont identiques, et l'indisponibilité du cache
  n'empêche ni lecture ni saisie ;
- un indicateur affiché est identique à celui que l'API renvoie pour la même date et le même
  périmètre ; la grille de planning affiche l'avancement physique des récapitulatives ;
- le parcours de bout en bout lit les indicateurs et les courbes d'un projet, contre le service
  réel ; PRJ-001, chargé, porte les indicateurs conservés de sa révision 101 et ceux du jour ;
- `make check` passe sur la branche de l'EPIC, les tests du back citent leurs exigences, et aucun
  fichier de `docs/api` ne change hors d'une « Interface contract issue » tranchée.

## Conception

EP-10 est le sixième EPIC de domaine du back, et le premier qui ne crée aucun objet saisi : il met
en relation ce que les cinq précédents ont construit — la référence et ses lignes (EP-07), les
tâches, leurs états et leurs dates (EP-06), les coûts réels et le reste à engager (EP-09) — dans un
module du noyau qui calcule, conserve au marquage et cache au jour courant ; il ajoute une table du
Tableau 10, les routes de ses cinq opérations nouvelles, un crochet dans `core/planning` pour
l'avancement physique, un module de cache sur Redis, et il branche sur le service l'écran des
indicateurs. Il **ne modifie pas le contrat**, figé en 1.0.0 : un manque devient une « Interface
contract issue » que l'auteur tranche — le cadrage en ouvre une, le refus d'`as_of`. Ce qui suit
fixe ce que chaque lot devrait sinon décider seul. Il se livre pendant les lots d'EP-09, d'EP-07 et
les derniers d'EP-06, sur une branche tirée de celle d'EP-09 : les sections « Ce qu'EP-09 écrit
encore », « Ce qu'EP-07 écrit encore » et « Ce qu'EP-06 écrit encore » disent ce que les lots
d'EP-10 n'écrivent pas avant le lot qui le possède.

### Ce que le cadrage décide

Décisions de l'auteur du 2026-11-07, sur les questions du cadrage, chacune avec l'option écartée :

- **Neuf US, le socle en lot technique de la première**, lot pivot d'EP-08 : la migration, le module
  à vide et ses routeurs ; EP-08 tire sa branche dès sa fusion et attend par leur numéro les lots du
  calcul, de la conservation et des courbes. Écarté : un pivot au dernier lot du calcul et de la
  conservation, qui laissait dormir des créneaux deux vagues de plus.
- **WF-DAT-0040 est recalée vers EP-11** (« Exigences réalisées ») : EP-10 conserve au marquage ce
  que ses lectures et celles d'EP-07 et d'EP-09 servent, EP-11 conserve de plus ce que le
  portefeuille lit, par un second enregistrement de `register_indicators`, et clôt. Écartés : clore
  ici avec un écart, contre la règle du README ; conserver dès maintenant la charge par rôle et par
  mois et les totaux par nœud d'organisation, sans lecteur avant EP-11.
- **WF-QUA-0040 et WF-INTF-0010 entrent au tableau** en portée « début ». Écarté : les laisser en
  « propre à l'US ».
- **Le module est `core/indicators`** (FBS-4.8), au sommet des modules du domaine : il importe les
  interfaces d'`estimate`, de `costs`, de `planning`, de `revisions`, de `projects` et
  d'`indicator_settings`, et aucun ne l'importe ; ce qu'il leur donne passe par les registres
  d'EP-04 (`register_indicators`) et par un crochet de `planning` (`register_physical_progress`).
  Les lectures qui lui manquent — les lignes d'une révision avec leur calendrier, les tâches d'une
  révision avec leurs états, les dates d'une lignée dans les révisions marquées, les empreintes du
  cache — sont des fichiers nouveaux de l'interface d'`estimate` et de `planning`, sur le modèle
  d'`open_lines.py` d'EP-09 : le lot du calcul du jour (US-1660/L3), premier lot d'EP-10 à pouvoir
  écrire ces deux `__init__` après le dernier lot qui les possède, les crée tous à vide et les
  réexporte, et chaque lot suivant ne remplit que son fichier.
  Écartés : la valeur acquise et l'avancement physique dans `core/estimate`, qui aurait mêlé le
  pilotage au devis ; une requête SQL sur les tables d'un autre module, que le guide interdit.
- **Le calcul reçoit l'instant du marquage** : `compute_indicators(session, revision_id, act)` et
  les entrées de `register_indicators` prennent l'`Act` que `run_marking` forme sous ses verrous ;
  le socle change la signature dans `core/revisions/interface/marking.py` (EP-04, dans `main` ;
  US-1490/L1 #2370 d'EP-07 l'a écrit avant la branche), l'ordre d'EP-04 — calculé avant que rien ne
  s'écrive — étant conservé. Écarté : écrire `marked_at` avant le calcul et le relire.
- **`revision_indicator` conserve un document JSON par révision, nature et maille** — la réponse du
  contrat telle que le marquage l'a calculée, zones exclues —, sous une clé unique
  (`revision_id`, `kind`, `scope`) ; EP-11 ajoute ses natures sans migration. Écarté : des colonnes
  typées par indicateur et une table de points, six tables et une migration par nature nouvelle.
- **Les indicateurs de devis et de reste à engager d'une révision marquée sont conservés et servis
  conservés** (`is_stored` vrai), par les routes d'EP-07 et d'EP-09 complétées après leurs lots
  (US-1510 #2363, US-1600 #2392) ; une offre marquée en chiffrage ne conserve que ces deux natures
  (WF-DAT-0040). Écarté : les laisser calculés à la lecture, contre la description du contrat.
- **Les courbes sont conservées au marquage**, dans leurs deux variantes de délais de paiement, et
  rendues telles quelles pour une révision marquée. Écarté : les recalculer à la lecture sur « les
  lignes connues au marquage telles qu'elles étaient alors », qu'aucune table ne garde — une ligne
  de coût mise à jour ou exclue n'a pas d'historique.
- **Le cache est à clé versionnée** : la clé d'une entrée est l'empreinte de ce dont les
  indicateurs du jour dépendent, lue à chaque consultation par des lectures des interfaces
  (« Le cache ») ; aucune écriture d'EP-06, d'EP-07 ni d'EP-09 n'appelle le cache. Écarté :
  l'invalidation explicite par un registre appelé dans chaque chemin d'écriture — des dizaines
  d'appels dans des fichiers que quatorze lots en vol écrivent encore, et un oubli servi dix
  minutes.
- **Le cache vit dans la plateforme**, `platform/cache.py`, sur le Redis de la file des tâches, sous
  un préfixe propre, comme `maintenance.py` ; sa durée de validité est
  `WATERFALL_INDICATORS_CACHE_TTL`, en secondes, six cents par défaut, un réglage de l'API ; une
  erreur de Redis rend le calcul. Écartés : un second Redis ; un cache en mémoire du processus, que
  deux instances de l'API ne partageraient pas.
- **La zone d'un indice n'est jamais conservée ni cachée** : elle se classe à la lecture sur les
  seuils courants (`index_zone` d'EP-05, WF-REF-0130), pour un indice conservé comme pour un indice
  du jour. Écarté : conserver la zone, qu'un seuil abaissé rendrait fausse.
- **L'avancement physique d'une récapitulative se calcule quel que soit l'état du projet** : le
  rapport des budgétés acquis au total du sous-arbre, 0 % avant En cours faute de tâche terminée,
  `no_budgeted_amount` sur un sous-arbre sans montant ; `core/indicators` le calcule, `planning` le
  rend par un registre. Écartés : nul avant En cours, un cas d'état de plus dans la grille ; le
  calcul par `estimate`.
- **La valeur planifiée et les séries s'étalent par le module pur d'EP-07** (`spreading`, US-1520/L1
  #2376), ligne par ligne, en un passage qui donne le point du jour et les fins de mois ;
  `planned_value(reference, at)` d'EP-07 est l'oracle d'un test d'égalité à la maille du projet.
  Écarté : un appel de `planned_value` par point et par maille, cinq mille lignes étalées des
  centaines de fois par courbe.
- **« Marquée à l'état En cours » se lit dans `revision_indicator`** : une révision marquée donne un
  point à l'évolution des indices et au temps/temps si et seulement si son marquage a conservé un
  document de nature `project` — ce que le marquage décide une fois, sous le verrou du projet, sur
  son état. Écarté : comparer `marked_at` aux transitions à chaque lecture.
- **Rien n'est conservé pour le temps/temps** : les dates d'un jalon dans chaque révision marquée
  sont des lignes immuables de `task`, lues par la lignée (WF-DAT-0030) ; WF-DAT-0040 ne le demande
  pas. Écarté : un document `milestones` conservé au marquage, redondant.
- **Le refus d'`as_of` sans révision marquée En cours est un 409** `STATE_FORBIDS_OPERATION` sans
  `params.state`, comme l'offre : un constat « contrat », « à trancher », propose la phrase pour la
  description du 409 des trois opérations ; les lots suivent la décision. Écartés : 422 sur
  `/query/as_of` ; 200 sur le calcul du jour, contre la description d'`as_of`.
- **Le témoin ne charge aucune tranche** : la conservation est un effet du marquage rejoué par
  `load_marking` ; ses lectures se comparent aux exemples à la référence près — l'offre 100 reste la
  référence jusqu'à EP-08 (US-1570 d'EP-07) —, les écarts listés. Écarté : désigner la 101 après
  coup, contre WF-REV-0040 et #1402.
- **Une seule migration, `0026`, dans le socle**, chaînée sur `0025`, aucune donnée à reprendre ;
  aucune migration d'EP-10 après le socle, EP-08 chaîne la sienne sur `0026`. Écarté : une migration
  par US.
- **Les quatre routes nouvelles sont sous `project_indicators.read`** (le catalogue d'EP-03), un
  routeur par US, créés vides par le socle.

### Tables et migrations

Régime « révisionné » (§4.4.1) pour `revision_indicator`, partitionnée par projet comme
`cost_structure` ; UUID v7 engendrés par le service ; textes en collation `C` ; règles SQL du guide.
Une ligne ne se modifie ni ne se supprime jamais : écrite par le marquage, protégée ensuite par
l'immuabilité de sa révision (WF-DAT-0020) ; une révision en cours n'en a aucune, l'abandon n'a donc
rien à emporter.

| Table | Contenu | Contraintes |
|---|---|---|
| `revision_indicator` | `project_id` (clé de partition), `id`, `revision_id`, `kind` (`estimate`, `remaining`, `project`, `cost_curve`, `cost_curve_payment_delays`, `earned_value_curves` ; EP-11 ajoute les siennes), `scope` (`project`, `unassigned`, ou l'identifiant du sous-projet en texte, comme le contrat l'écrit), `document` (`jsonb`, la réponse du contrat de cette nature pour cette maille, `context` compris, `zone` nulle sur chaque indice), `computed_at` (l'instant du marquage), `created_at`, `created_by` | clé primaire (`project_id`, `id`) ; unique (`project_id`, `revision_id`, `kind`, `scope`) ; clé composite (`project_id`, `revision_id`) vers `revision` en refus ; `kind` dans les six natures, `scope` de 1 à 36 non blanc ; `document` objet ; index sur (`project_id`, `revision_id`) ; déclencheur d'immuabilité comme `cost_structure`, et un déclencheur qui refuse l'écriture d'une ligne dont la révision n'est pas en cours de marquage — la révision verrouillée `FOR UPDATE` par le marquage, encore `draft` à l'instant de l'écriture |

- **Une migration, `0026`, dans le socle** (US-1660/L1) : la table, `create_project_partitions`
  remplacée pour qu'elle crée sa partition (`revision_indicator_p_<uuid>`) et celles des projets
  existants, les déclencheurs, les droits du rôle du service — `SELECT`, `INSERT` : rien ne se met à
  jour ni ne se supprime — déclarés dans `SERVICE_RIGHTS`. Aucune migration de données.
- **La nature `project` n'existe que pour une révision marquée à l'état En cours** : c'est ce que
  l'évolution des indices, le temps/temps et le 409 de l'offre lisent.
- Les tests : `test_migrations.py` (schéma, droits, partition d'un projet créé),
  `test_database_constraints.py` (une contrainte, un test), `test_revision_immutability.py` étendu.

### Modules

| Module | Tables | Interface offerte |
|---|---|---|
| `waterfall.core.indicators` (FBS-4.8) | `revision_indicator` | `project_indicators(project_id, selection, scope)` — la révision en cours ou la dernière marquée au jour courant, une révision marquée nommée, ou une date — ; `cost_curve(…, payment_delays)`, `earned_value_curves(…)` ; `index_history(project_id, scope)` ; `milestone_tracking(project_id)` ; `store_indicators(session, revision_id, act)`, l'entrée de `register_indicators` ; `physical_progress(session, revision_id, node_ids)`, l'entrée du crochet de `planning` ; `stored_document(revision_id, kind, scope)` pour les routes d'EP-07 et d'EP-09 ; le sous-paquet pur `formulas/` (les ratios, les indices, les projections, l'enveloppe `Computable`, l'arrondi) et `series/` (les séries au pas du mois, les décaissements) ; `invalidate_nothing` — aucune fonction d'invalidation : la clé change par construction |
| `waterfall.platform.cache` (PBS-3.2) | aucune (Redis) | `IndicatorsCache.of(queue, ttl)` : `read(key)`, `write(key, document)`, chaque erreur de Redis rendue `None` ou ignorée et journalisée une fois par processus et par cause ; la clé `waterfall:indicators:<project_id>:<empreinte>` |

- **La couche** : `indicators` importe `estimate`, `costs`, `planning`, `revisions`, `projects`,
  `indicator_settings`, `cost_settings` (les seuils) et `platform` ; aucun module du domaine ne
  l'importe ; `api` et `worker` l'importent — le worker après US-1610/L2 #2404. Le socle ajoute
  `indicators` au contrat de couches d'import-linter, au-dessus d'`estimate` et de `costs`.
- **Ce que les autres modules déclarent pour lui**, chacun dans un fichier nouveau de son
  interface, réexporté par son `__init__` après le dernier lot qui l'écrit :
  - `core/estimate/interface/indicator_lines.py` (après US-1580/L1 #2398, qui a écrit le dernier
    `__init__`) : `lines_for_indicators(revision_id)` — par ligne hors provision : le nœud, la
    lignée, la tâche porteuse, le sous-projet, le montant budgété, le réestimé, le délai de
    paiement, les heures hebdomadaires du calendrier de son rôle (celui de la tâche hors
    main-d'œuvre), lues sur les images pour une révision marquée — ; `lines_stamp(revision_id)`,
    le nombre et le dernier `updated_at` de ses lignes ; `remaining_of_revision` (EP-09, US-1580/L2
    #2399), `estimate_indicators` (EP-07, US-1510 #2363) et `remaining_indicators` (EP-09, US-1600
    #2392) servent tels quels ;
  - dans `core/planning/interface/`, quatre fichiers (après US-1390/L2 #2339 et US-1590/L1 #2401,
    les deux derniers à écrire `__init__`) : `indicator_tasks.py`, `tasks_for_indicators(revision_id)`
    — par tâche de la structure principale : le nœud, la lignée, le parent, récapitulative ou jalon,
    `progress`, `started_on`, `completed_on`, le début et la fin calculés, les heures hebdomadaires de
    son calendrier applicable — ; `milestone_dates.py`, `milestone_forecasts(project_id, lineage_ids,
    revision_ids)`, la date de fin de chaque lignée dans chaque révision nommée, et
    `tracked_milestones(project_id)`, les lignées inscrites au suivi temps/temps (US-1400/L2 #2340) ;
    `indicator_stamps.py`, `revision_content_stamp(revision_id)`, le nombre et le dernier `updated_at`
    de ses nœuds, tâches et liaisons ; `physical_progress.py`, `register_physical_progress`, le
    crochet (« Les points d'extension ») ;
  - `core/costs/interface/indicator_costs.py` (après US-1610/L2 #2404 et US-1610/L3 #2405) :
    `costs_stamp(project_id)`, le dernier `imported_at` de `cost_import` et le dernier
    `updated_at` de `cost_line` ; `actual_costs_until` et `actual_cost_by_subproject` (EP-09)
    servent tels quels ;
  - `core/revisions` et `core/projects` servent par leurs lectures existantes : `found_revision`,
    `current_revision`, `list_revisions`, `read_revision` (`marked_at`, `is_reference`, le statut) ;
    `project_facts`, `read_project` (la référence, l'état), `stored_lock_version`,
    `subprojects_present`, `list_subprojects`, `list_state_transitions`.
- **La signature du registre** : `register_indicators(compute)` avec
  `compute: Callable[[Session, UUID, Act], None]`, et `compute_indicators(session, revision_id, act)`
  appelé par `mark_revision` avec l'`Act` du marquage ; `load_marking` passe celui du témoin.

### Les points d'extension

Chaque registre est un `Registry` de `core/revisions/registry.py`, rempli à l'import de
`core/indicators/interface`, et le test des points d'entrée d'EP-06 (#2180, `test_registries.py`)
s'étend à chacun : l'API et le chargeur l'attendent dès le socle, le worker à partir du lot qui
importe l'interface (US-1670/L1).

| Module | Registre | Qui le déclare | Qui le remplit | Ce qu'il fait |
|---|---|---|---|---|
| `core/revisions` | `register_indicators` (EP-04) | EP-04 ; la signature changée par le socle | `indicators` (`store_indicators`) | dans la transaction du marquage, après `register_marking` d'EP-07 (les images et les taux, dont les montants dépendent), avant que la révision ne s'écrive : les documents conservés de la révision (« La conservation au marquage ») ; une exception fait échouer le marquage ; EP-11 enregistre ensuite les siens |
| `core/planning` | `register_physical_progress` (nouveau) | US-1680, après #2339 et #2401 | `indicators` (`physical_progress`) | la lecture de la facette tâche (`interface/nodes.py`, `facets.py` : après US-1380/L2 #2335, US-1560/L1 #2382 et US-1590/L1 #2401) appelle le registre pour les récapitulatives rendues, en une fois, et pose `TaskFacet.physical_progress` ; sans entrée, nul |
| `core/revisions` | `register_closing` (EP-06) | EP-06 | personne | une révision en cours n'a aucune ligne de `revision_indicator` : rien à faire à l'abandon |

### Le calcul des indicateurs

- **La sélection** (`IndicatorsRevision`, `AsOf`) : `revision_id` absent ou celui de la révision en
  cours → le calcul au jour courant sur la révision en cours, ou, sans elle, sur la dernière
  révision marquée (`marked_at` le plus récent), `context.revision_id` la nommant, `is_stored` faux ;
  `revision_id` d'une révision marquée → le document conservé, `is_stored` vrai, 409
  `STATE_FORBIDS_OPERATION` sans `params.state` si elle n'a pas de document `project` (marquée avant
  En cours) ; `as_of` → la dernière révision marquée dont `marked_at` ≤ la fin de la date, parmi
  celles qui ont un document `project`, sinon le même 409 (constat « contrat ») ; les deux ensemble
  → 422 sur `/query/revision_id` ; un projet antérieur à En cours → 409 avec `params.state` et
  `params.state_enum`, avant toute autre lecture. `scope` : `project`, `unassigned`, ou un identifiant
  parmi `subprojects_present` du projet, sinon 422 `UNKNOWN_SUBPROJECT` sur `/query/scope`.
- **La date de calcul** D : le jour courant en temps universel pour le calcul du jour (`computed_at`
  l'instant), le jour de `marked_at` pour le marquage ; la révision de référence Ref est celle du
  projet à l'instant du calcul (la lecture du projet, sous son verrou au marquage).
- **Les grandeurs d'une maille S**, en `Decimal`, arrondies une fois (`ROUND_HALF_EVEN`,
  WF-DAT-0100) — les montants au centime, les ratios et les indices à quatre décimales :
  - le budget de référence : la somme des budgétés des lignes de Ref hors provision dont le
    sous-projet dans Ref est S (`unassigned` : nul) ;
  - la valeur planifiée à D : chaque ligne de Ref de la maille étalée sur les dates de sa tâche dans
    Ref, au prorata des heures travaillées de son calendrier (`spreading`), la part écoulée à la fin
    de D ; une ligne d'un jalon compte entière à sa date ;
  - la valeur acquise à D : la somme des budgétés des lignes de Ref de la maille dont la tâche, par
    sa lignée, est `completed` dans la révision calculée R avec `completed_on` ≤ D ; une ligne dont
    la lignée de tâche n'est pas dans R compte zéro ; les lignes de provision et les tâches de
    survenance (`origin_risk_id`, EP-08) sont exclues par construction ;
  - le coût réel à D : `actual_costs_until(project_id, D, S)` d'EP-09, les lignes suivies connues au
    moment du calcul dont la date de pièce ≤ D, `unassigned` les lignes au `subproject_id` nul ;
  - le reste à engager : `remaining_of_revision(R)` par ligne, filtré par le sous-projet de la ligne
    dans R ;
  - puis `financial_progress` = CR ÷ (CR + RAE) (`no_actual_or_remaining`), `budget_consumption` =
    CR ÷ BR et `physical_progress` = VA ÷ BR (`no_reference_budget`), `cost_index` = VA ÷ CR
    (`no_actual_cost`), `schedule_index` = VA ÷ VP (`no_planned_value`), `cost_variance` = VA − CR,
    `schedule_variance` = VA − VP, `at_budget` = CR + BR − VA, `project_manager` = CR + RAE,
    `at_observed_rate` = BR ÷ CPI (`no_actual_cost` tant que CR est nul, `no_earned_value` quand
    VA l'est), et les écarts au budget, `variance_at_observed_rate` nul quand la projection ne se
    calcule pas ; la zone par `index_zone` sur `IndexThresholds` du référentiel, nulle pour un
    indice non calculable.
- **Un passage pour toutes les mailles** : les lignes de Ref et de R, les tâches de R et de Ref et
  les coûts se lisent une fois par calcul, et les douze mailles s'en déduisent en mémoire ; c'est ce
  que le marquage conserve d'un coup et ce que le cache tient d'un coup.
- **Les exemples chiffrés** (WF-IND-0040 à WF-IND-0080, WF-REF-0170) sont des tests sans base de
  `formulas/` (`tests/examples`), et les mêmes sur le service.

### La conservation au marquage

- `store_indicators(session, revision_id, act)` lit l'état du projet (verrouillé par `run_marking`
  avant `mark_revision` ; le chargeur, en une transaction, le lit sans verrou) et la référence, puis
  écrit, pour le projet, chaque sous-projet et `unassigned` : `estimate` (le document
  d'`estimate_indicators` d'EP-07 pour la révision et la maille), `remaining` (celui de
  `remaining_indicators` d'EP-09, la couverture à zéro jusqu'à EP-08), et, si le projet est
  `in_progress`, `project` (le calcul ci-dessus à la date du marquage) et les trois natures de
  courbes (« Les courbes ») ; `context` de chaque document porte `revision_status` `marked`,
  `computed_at` = `act.at`, `is_stored` vrai ; `created_by` l'auteur de l'`Act`.
- **La politique d'erreur** (#2180, point 2) : rien n'est attrapé ; une exception du calcul remonte
  à `mark_revision`, qui n'a encore rien écrit, et au worker, qui fait échouer la tâche avec son code
  (`BackgroundTask.problem` ; une exception non typée, le code d'une erreur interne) ; la révision
  reste en cours, un nouveau `markRevision` la relance ; la docstring de `compute_indicators` le dit,
  et `test_indicators_failure.py` l'éprouve avec une entrée de registre qui lève.
- **La lecture** : `project_indicators` avec le `revision_id` d'une révision marquée rend le
  document de la maille, la zone de chaque indice classée à la lecture ; `getEstimateIndicators` et
  `getRemainingIndicators` (routes d'EP-07 et d'EP-09) lisent `stored_document` pour une révision
  marquée et gardent leur calcul pour la révision en cours — leurs documents conservés portent
  déjà `is_stored` vrai.
- **Le témoin** : `load_marking` → `mark_revision` → `compute_indicators` : la 100 conserve
  `estimate` et `remaining`, la 101 les quatre natures ; aucune tranche.

### L'avancement physique

- `physical_progress(session, revision_id, node_ids)` : les lignes de la révision hors provision
  (`lines_for_indicators`), les tâches (`tasks_for_indicators`) ; pour chaque récapitulative
  demandée, le total des budgétés de son sous-arbre, lignes propres comprises, et la part portée par
  les tâches `completed` du sous-arbre — ses lignes propres acquises si elle est elle-même
  `completed` — ; `Computable` à quatre décimales, `no_budgeted_amount` sur un total nul ; une
  requête par lecture, jamais une par tâche.
- `planning` l'appelle à la lecture de la facette pour les récapitulatives rendues, sur la révision
  lue, en cours ou marquée ; le résultat n'est pas conservé : sur une révision marquée, lignes et
  états sont immuables.

### Les courbes

- **Le pas** (`CurveSeries`, `docs/api/DECISIONS.md`, G-01, M-02, M-06) : un point par fin de mois,
  du mois qui précède le premier montant — nul — à la fin de la dernière tâche de Ref (le budget, la
  valeur planifiée) ou de R (la projection) ; la date de calcul en point de plus sur `actual_cost`,
  `earned_value` et `project_manager_projection`, qui s'y arrêtent ou en partent.
- **Les séries** : `reference_budget` et `planned_value`, le budgété de chaque ligne de Ref de la
  maille étalé sur les dates de sa tâche dans Ref (`spreading`), cumulé par fin de mois —
  identiques tant qu'aucun avenant ne déplace la référence, et `planned_value` se prolonge jusqu'à
  la fin de Ref — ; `earned_value`, les budgétés cumulés par mois de `completed_on` ; `actual_cost`,
  les lignes suivies cumulées par mois de date de pièce jusqu'à D ; `project_manager_projection`,
  depuis le coût réel à D, le reste de chaque ligne de R (`remaining_of_revision`) étalé sur la
  part de sa tâche postérieure à D, porté entier à D quand la fin est dépassée, jusqu'à
  `projections.project_manager` ; `steps` vide (EP-08 écrit les marches).
- **Les décaissements** (`payment_delays`) : chaque part du budget et de la projection décalée du
  `payment_delay_days` de sa ligne avant le cumul mensuel, le coût réel non ; `cash_out_by_month`
  du premier au dernier mois, `past` par mois de date de pièce, `forecast` par mois de part
  décalée, le mois de D portant les deux ; la somme des `forecast` égale le reste à engager.
- **Les mailles** : une maille sans ligne dans Ref ni dans R et sans coût réel a des séries sans
  point ; le budget d'une maille qu'aucune référence ne budgète est une série sans point ; le coût
  réel d'une maille qui a des lignes et aucune pièce est tracé nul.
- **La conservation** : `cost_curve`, `cost_curve_payment_delays` et `earned_value_curves` par
  maille, au marquage ; une révision marquée les rend telles quelles.

### L'évolution des indices et le temps/temps

- `index_history` : pour chaque maille (le projet, les sous-projets dans l'ordre de
  `listSubprojects`, `unassigned` ; ou la seule maille de `scope`), un point par document `project`
  conservé du projet, par `marked_at` croissant — `at` = `computed_at`, `revision_id`,
  `version_name`, les deux `IndexValue` du document, zone classée sur les seuils courants — ; puis le
  point du jour, `version_name` nul, le calcul au jour courant (le cache) ; `thresholds` les seuils
  courants ; 409 avant En cours.
- `milestone_tracking` : les lignées de `tracked_milestones` ; la révision du jour (en cours ou
  dernière marquée) donne `label` et `completed_on` ; les révisions marquées qui ont un document
  `project`, par `marked_at` croissant, donnent chacune un point `{marked_at, finish}` par
  `milestone_forecasts`, jusqu'à la terminaison — aucune révision marquée après `completed_on` n'en
  ajoute — ; puis, terminé, `{completed_on à minuit UTC, completed_on}` ; non terminé,
  `{computed_at, finish dans la révision du jour}` ; une lignée absente d'une révision marquée n'y a
  pas de point ; 409 avant En cours ; `context` celui de la révision du jour, `is_stored` faux.

### Le cache

- **La clé** : `waterfall:indicators:<project_id>:<empreinte>`, l'empreinte étant le haché
  (SHA-256, tronqué) d'un texte canonique formé de : l'état, la révision en cours, la référence et le
  compteur du projet (`project_facts`, `read_project`, `stored_lock_version`) ; la révision calculée
  R et sa référence Ref ; `revision_content_stamp(R)` et `lines_stamp(R)` ; `costs_stamp(project)` ;
  le nombre de sous-projets ; le jour D en temps universel. Toute écriture dont une entrée dépend
  change l'empreinte : une saisie de nœud, de ligne ou d'état (les `updated_at` et les comptes), un
  marquage ou un abandon (la révision en cours), une désignation (la référence, le compteur), un
  import ou une exclusion de coût (`costs_stamp`), un sous-projet créé (le nombre ; les lignes
  imputées bougent `costs_stamp`), le passage d'un jour. L'empreinte coûte six lectures indexées ;
  la seule écriture qui lui échappe est un changement de seuil, que la zone classée à la lecture
  n'a pas besoin de voir.
- **L'entrée** : un seul document JSON par projet et par jour — les `ProjectIndicators` et les trois
  `CurveSeries` de chaque maille, zones nulles —, écrit après un calcul complet avec la durée de
  validité ; `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves` au jour courant et le
  dernier point de `getIndexHistory` le lisent ; aucune lecture d'une révision marquée ne passe par
  le cache. Deux lectures parallèles d'une entrée absente calculent toutes deux et écrivent la même
  valeur : aucun verrou.
- **L'indisponibilité** : `IndicatorsCache` attrape `redis.exceptions.RedisError` et les délais
  (`socket_timeout` d'une seconde, comme `DEPOSIT_TIMEOUT`), rend `None` à la lecture, ignore à
  l'écriture, et journalise `indicators.cache_unavailable` une fois par cause ; le calcul est rendu.
  Les saisies ne touchent pas Redis.
- **Les tests** : contre Redis (guide, « Un test contre Redis »), sur une base propre au test : une
  entrée servie, une entrée ignorée après chaque écriture du Vérif, `FLUSHDB` puis l'identité, Redis
  pointé sur un port fermé.

### Le service d'API

- Un routeur par US — `api/project_indicators.py` (US-1660 : `getProjectIndicators` ; US-1670 y
  ajoute `revision_id` marqué et `as_of`), `api/indicator_curves.py` (US-1690 : `getCostCurve`,
  `getEarnedValueCurves`), `api/index_history.py` (US-1700), `api/milestone_tracking.py` (US-1710)
  —, créés vides et enregistrés dans `app.py` par le socle, chacun avec son `asked_*.py` ;
  `api/estimate_indicators.py` (EP-07, #2363) et `api/remaining_indicators.py` (EP-09, #2392) sont
  complétés par US-1670 pour la révision marquée ; `listNodes` reste au routeur d'EP-06, qui rend ce
  que `planning` lui donne.
- Chaque route déclare `RequiresProject(project_indicators.read)` ; les refus sont ceux du contrat,
  dans l'ordre que chaque opération écrit — 404, 403, 409 de l'état, 422 des paramètres, 409 de la
  révision nommée — ; chaque réponse d'un test passe par `ContractClient` ;
  `test_access_evaluation.py` reçoit chaque opération avec ses deux termes.

### Le worker

Aucun gestionnaire nouveau : le marquage est celui d'EP-04 (`run_marking`), qui appelle
`compute_indicators`, dont la signature change. Le worker doit importer l'interface d'`indicators`
pour que `register_indicators` soit rempli (#2180) ; `worker/main.py` est écrit par #2341 (EP-06),
#2375 (EP-07) puis #2404 (EP-09) : l'import est du lot d'US-1670 qui conserve, après #2404. Le test
des points d'entrée (`test_registries.py`), que le socle étend, dit que l'extension d'`indicators`
n'est attendue du worker qu'à partir de ce lot — l'API et le chargeur l'attendent dès le socle.

### Le chargeur du témoin

Aucune tranche, aucun fichier d'outil : `witness/revisions.py` marque par `load_marking`, et le
marquage conserve dès que le chargeur porte l'extension (l'interface importée par `waterfall.witness`
dès le socle). `test_witness_indicators.py` (US-1740) compare les lectures du témoin chargé aux
exemples — `project_indicators`, `project_indicators_marked`, `project_indicators_offer`,
`index_history`, `index_history_subproject`, `milestone_tracking`, `cost_curve`,
`cost_curve_payment_delays`, `cost_curve_subproject`, `earned_value_curves`, `estimate_indicators`
et `remaining_indicators` de la 101 — à la référence, aux provisions, aux risques et aux montants
qui en dépendent près, listés ; tels quels les contextes, `is_stored`, le coût réel, le reste, les
dates des jalons, les formes ; et prouve les invariants sur le témoin. Les fixtures ne changent pas :
aucune pièce du témoin n'est datée avant le marquage de la 101, et les exemples les lisent déjà
conservés ; un désaccord hors de la liste se tranche par la spécification, par une issue.

### Le front

- L'écran est celui d'EP-02 (US-0240), d'EP-14 et d'EP-15 (US-0530) ; US-1730 le branche et ne le
  réécrit pas ; il n'a pas de `MockupNotice`. Les aides `frontend/help/fr/FBS-4.8*.md` disent ce que
  le service fait, par US-1730. La grille de planning (EP-06, US-1470 #2326) montre l'avancement
  physique sans changement : sa colonne lit `physical_progress`.
- Le front ne calcule rien : les montants, les ratios, les zones et les séries viennent du service
  (WF-ARC-0070). Un manque que le branchement révèle devient une issue ; un manque du contrat, une
  « Interface contract issue ».

### Le harnais

US-1730 étiquette `@shared` `indicators.spec.ts` et lève la part des indicateurs de `context.spec.ts`
(`BEFORE_THE_DATA`, après US-1470 #2326 d'EP-06 et US-1560/L2 #2383 d'EP-07) ; US-1740 garde par
`inService` les chiffres de `review.spec.ts`, qui sont ceux de la référence 101, et écrit l'entrée du
guide qu'EP-08 lève ; les parcours qui marquent le font sur un projet que la course crée (#2193). La
liste des entrées non rejouées n'est écrite que par le dernier lot d'US-1740, après US-1650/L3 #2416
d'EP-09.

### Les tests du back

Un fichier par objet et par règle — `test_indicators_formulas.py` (pur), `test_indicators_series.py`
(pur), `test_indicators_scope.py`, `test_earned_value.py`, `test_project_indicators.py`,
`test_indicators_stored.py`, `test_indicators_failure.py` (#2180), `test_indicators_marked_read.py`,
`test_physical_progress.py`, `test_cost_curve.py`, `test_cash_out.py`,
`test_earned_value_curves.py`, `test_index_history.py`, `test_milestone_tracking.py`,
`test_indicators_cache.py`, `test_witness_indicators.py` —, chaque test citant son exigence, chaque
réponse validée contre le contrat ; les exemples chiffrés des Vérif sont des tests sans base
(`tests/examples`). Les fixtures communes — un projet En cours avec sa référence désignée, ses
tâches, ses lignes, des tâches terminées, des lignes de coût chargées, l'horloge posée — vivent
dans `tests/indicators_support.py`, écrit par le socle, par les interfaces d'EP-04 à EP-09. Un test de
concurrence par règle d'ensemble : un marquage pendant une saisie, deux lectures d'une entrée de
cache absente.

### Ce qu'EP-09 écrit encore

Les lots d'EP-10 se livrent pendant ceux d'EP-09, et `epic/EP-10` reprend `epic/EP-09` à chaque
fusion. Un fichier qu'un lot d'EP-09 non fusionné possède, les lots d'EP-10 ne l'écrivent pas avant
ce lot, ou en dépendent par son numéro :

| Fichier | Lot d'EP-09 qui le possède | Lots d'EP-10 qui l'attendent |
|---|---|---|
| `core/estimate/remaining/` : `set_line_remaining`, `remaining_entry` et `previous_*`, `remaining_of_revision` | US-1580/L2 #2399 | US-1660 (le reste par ligne), US-1690 (la projection) |
| `core/estimate/remaining/` : les indicateurs du reste, `api/remaining_indicators.py` | US-1600 #2392 | US-1670 (le document `remaining`, la route conservée) |
| `core/estimate/remaining/excel/`, le format `remaining` | US-1630/L1 #2408 à L4 #2411 | aucun |
| `core/planning/interface/__init__.py`, `register_open_lines`, `progress_commands`, la lecture de la facette (`awaiting_own_lines`) | US-1590/L1 #2401 | US-1660 (`indicator_tasks.py` réexporté), US-1680 (le crochet et son appel), US-1710 |
| `core/costs` : l'en-tête et l'analyse d'une extraction | US-1610/L1 #2403 | aucun |
| `core/costs` : l'application, `cost_import`, `actual_costs_until` servie ; `core/projects/commands.py` ; `worker/main.py` | US-1610/L2 #2404 | US-1660 (le coût réel), US-1670 (l'import dans le worker), US-1720 (`costs_stamp`) |
| `core/costs` : `register_cost_facts`, `core/projects/interface/subprojects.py` | US-1610/L3 #2405 | US-1720 (`indicator_costs.py` réexporté) |
| `core/costs` : la consultation, l'exclusion | US-1620/L1 #2406 | US-1720 (l'exclusion qui change la clé, en test) |
| `core/revisions/commands.py` (`export_remaining`), `exchanges.spec.ts` | US-1630/L4 #2411 | aucun |
| `remaining.spec.ts`, les aides FBS-4.5*, les grilles | US-1640/L1 #2412, L2 #2413 | aucun |
| `wftools`, `make mock-data` | US-1650/L1 #2414 | aucun : EP-10 n'écrit pas d'outil |
| `witness/costs.py`, `witness/revisions.py`, `witness/timeline.py`, `core/exchanges/interface` | US-1650/L2 #2415 | US-1740 (le témoin chargé coûts compris) |
| le guide, la liste des entrées non rejouées | US-1650/L3 #2416 | US-1740 (la vérification d'ensemble) |
| `app.py`, `core/estimate/interface/__init__.py`, `core/costs/interface/__init__.py`, `test_registries.py`, `chronology.py` | US-1580/L1 #2398, fusionné avant la branche | aucun |

### Ce qu'EP-07 écrit encore

| Fichier | Lot d'EP-07 qui le possède | Lots d'EP-10 qui l'attendent |
|---|---|---|
| `core/estimate` : les taux, le marquage (`register_marking` rempli), `api/revisions.py`, `worker/main.py` | US-1500/L1 #2374, US-1500/L2 #2375 | US-1670 (les images avant le calcul) |
| `core/estimate` : `estimate_indicators`, `api/estimate_indicators.py` | US-1510 #2363 | US-1670 (le document `estimate`, la route conservée) |
| `core/estimate` : `workload`, `planned_value`, `api/workload.py` | US-1520/L2 #2377 | US-1660 (l'oracle du test de la valeur planifiée) |
| `core/estimate` : la comparaison, `revisions.spec.ts` | US-1530 #2365 | aucun |
| `core/estimate` : le passage En cours, les contributeurs | US-1540 #2366 | aucun : la transition est d'EP-04, la désignation exige des lignes (#2373) |
| `core/estimate/excel/`, le format `estimate`, `core/projects/commands.py`, `core/revisions/commands.py`, `exchanges.spec.ts` | US-1550/L1 #2378 à L4 #2381 | aucun |
| `core/planning` : `FacetHooks.judge_cell` (`facets.py`), la grille de devis, `context.spec.ts` (le devis) | US-1560/L1 #2382, L2 #2383 | US-1680 (l'appel du crochet dans la lecture de la facette), US-1730 (`context.spec.ts`) |
| `wftools`, `DECISIONS.md` (L-01) ; `witness/estimate_lines.py`, `witness/revisions.py`, `witness/timeline.py` ; le guide | US-1570/L1 #2384, L2 #2385, L3 #2386 | US-1740 (le témoin En cours, lignes comprises) |
| `core/estimate/interface/__init__.py`, `pricing/`, `spreading/`, la facette lue et créée, `update_line`, la suppression, `core/projects` (`register_estimate_facts`), `core/revisions/interface/marking.py` (`register_marking` déclaré) | US-1490/L1 #2370 à L4 #2373, US-1520/L1 #2376, fusionnés avant la branche | aucun |

### Ce qu'EP-06 écrit encore

| Fichier | Lot d'EP-06 qui le possède | Lots d'EP-10 qui l'attendent |
|---|---|---|
| `core/planning` : la lecture et la création des nœuds (`interface/nodes.py`, `facets.py`) | US-1380/L2 #2335 | US-1660 (`tasks_for_indicators`), US-1680 (l'appel du crochet) |
| `core/planning` : la suppression et le déplacement, `core/projects` (`register_attachments`) | US-1380/L3 #2338 | aucun |
| `core/planning/interface/__init__.py`, le moteur, `setPredecessors`, `resource_settings` | US-1390/L1 #2329, L2 #2339 | US-1660, US-1680, US-1710 (le réexport d'`indicator_tasks.py`) |
| `core/planning` : les chronologies, `core/projects/commands.py` ; les inscriptions (`tracking_entry`, `listNodes` avec `timeline_id`) | US-1400/L1 #2331, L2 #2340 | US-1710 (`tracked_milestones`) |
| `core/planning` : l'état des tâches (`setTaskProgress`, `started_on`, `completed_on`) | US-1410 #2324 | US-1660 (la valeur acquise), US-1680, US-1690, US-1710 |
| `core/exchanges` : la mécanique d'import, les formats ; la purge, `worker/main.py`, les Compose, `production.env.example`, le Makefile | US-1420/L1 #2332, L2 #2341 | US-1720 (`WATERFALL_INDICATORS_CACHE_TTL` dans `production.env.example`) |
| `core/revisions/commands.py` (`export_*`), `api/tasks.py`, `api/exports.py` ; `core/planning` : le collage, `api/history.py` ; `REUSE.toml` | US-1430/L2 #2336, US-1440/L1 #2337, L2 #2343, US-1450/L2 #2344 | aucun |
| la grille et le Gantt, `planning.spec.ts`, `context.spec.ts` (le planning) | US-1470 #2326 | US-1680 (la colonne lue contre le service), US-1730 (`context.spec.ts`) |
| `wftools` ; `witness/tasks.py` ; le guide | US-1480/L1 #2330, L2 #2347, L3 #2348 | US-1740 |
| `app.py`, `pyproject`, `tests/planning_support.py`, `test_registries.py`, `chronology.py`, `witness/revisions.py` (`register_revision_filler`) | US-1380/L1 #2328, fusionné avant la branche | aucun |

Les catalogues `messages/*.json`, `conftest.py`, `support.py`, `api/queries.py`, `loader.py` et
`mode.ts` ne s'écrivent dans aucun des quatre EPIC : une clé ou une fixture qui manque devient une
issue. `platform/settings.py` (le réglage du cache) et `platform/cache.py` ne sont nommés par aucun
lot des trois autres : EP-10 les écrit (US-1720).

### Ce que le cadrage laisse à EP-08

Le socle (US-1660/L1 #2437) est le **lot pivot d'EP-08** : `epic/EP-08` se tire d'`epic/EP-10` dès sa
fusion. Il lui garantit `revision_indicator` et sa partition, la chaîne des migrations arrêtée à
`0026`, le module `core/indicators` avec son interface déclarée — `project_indicators`,
`cost_curve`, `earned_value_curves`, `index_history`, `milestone_tracking`, `store_indicators`,
`physical_progress` — et la signature du registre avec l'`Act`. Les lots d'EP-08 qui lisent les
indicateurs devant un risque survenu, une fusion ou un avenant attendent par leur numéro le calcul
du jour (US-1660/L3), la conservation et la lecture conservée (US-1670/L1, L2) et les courbes
(US-1690/L2, L3) ; ils y ajoutent les marches d'avenant (`steps`, la référence en vigueur à chaque
date), les lignes de provision dans la projection et les décaissements, l'exclusion des tâches de
survenance de la valeur acquise (`origin_risk_id`, déjà prévue dans la sélection des lignes), la
couverture des risques dans le document `remaining`, et leurs propres compteurs dans l'empreinte du
cache (les structures des risques, les risques eux-mêmes).

### L'ordre de construction

Le socle d'abord, dès #2398 ; puis les modules purs et ce qui ne dépend que de lots déjà fusionnés,
en largeur quatre ; le calcul du jour avant la conservation, la conservation avant les lectures
historiques, les courbes conservées après les deux ; l'écran et le témoin après tout ce qui sert ; la
vérification d'ensemble en dernier ; le plan de lots (étape 3) le détaille en vagues.

1. **US-1660/L1**, le socle — dès la fusion d'US-1580/L1 #2398 : la migration `0026`, le module
   `core/indicators` à vide avec son interface en paquet — hors les sous-paquets `formulas/` et
   `series/`, que leurs lots possèdent entiers, comme `pricing/` et `spreading/` en EP-07 —,
   l'enregistrement à vide dans `register_indicators` et la signature changée dans `marking.py`,
   le contrat de couches, les quatre routeurs vides et leurs `asked_*`, `tests/indicators_support.py`,
   les fichiers de tests, le test des points d'entrée étendu. **Lot pivot d'EP-08.** Ni
   `core/planning`, ni `core/estimate`, ni `core/costs`, ni le worker. En parallèle, dès la
   branche : **les formules** (US-1660, pur : les ratios, les indices, les projections, l'enveloppe
   et l'arrondi, les exemples chiffrés sans base) et **les séries** (US-1690, pur : le pas du mois,
   l'étalement par `spreading` d'EP-07 #2376, les décaissements).
2. **Le calcul du jour** (US-1660 : `indicator_lines.py`, `indicator_tasks.py`, `getProjectIndicators`
   sur la révision en cours ou la dernière marquée, les mailles, après #2324, #2339, #2399, #2401 et
   #2404), **l'avancement physique** (US-1680 : le crochet et son appel, après #2335, #2382, #2401,
   #2324), **le temps/temps** (US-1710 : `tracked_milestones`, `milestone_forecasts`,
   `getMilestoneTracking`, après #2340, #2324, #2401 — la lecture des documents `project` conservés
   attend la conservation : le lot livre sur les transitions d'état d'abord, et se branche sur les
   documents par US-1670), puis **la conservation** (US-1670/L1 : `store_indicators`, l'import dans le
   worker après #2375 et #2404, la politique d'erreur, les 409 de l'offre, après le calcul du jour).
3. **Les courbes du jour** (US-1690 : `getCostCurve`, `getEarnedValueCurves`, après le calcul du
   jour), **l'évolution des indices** (US-1700, après la conservation), **le cache** (US-1720, après
   le calcul du jour, #2341, #2405 et #2406), **la lecture conservée** (US-1670/L2 : `revision_id`,
   `as_of`, les routes d'EP-07 et d'EP-09, après la conservation, #2363 et #2392).
4. **Les courbes conservées** (US-1690, après la conservation et les courbes du jour), **l'écran**
   (US-1730, après toutes les lectures, #2326 et #2383), **le témoin comparé** (US-1740, après la
   lecture conservée, les courbes conservées et #2415) ; puis **la vérification d'ensemble**
   (US-1740, après #2416), seule.

---

## US-1660 — Les indicateurs de valeur acquise au jour courant : la date et le périmètre, les avancements, les indices et leurs zones, les projections

- **statut** : à faire
- **exigences** : `WF-IND-0010-A`, `WF-IND-0020-A`, `WF-IND-0030-A`, `WF-IND-0040-A`,
  `WF-IND-0050-A`, `WF-IND-0060-A`, `WF-IND-0070-A`, `WF-IND-0080-A`, `WF-RAE-0050-A`,
  `WF-REF-0170-A`
- **opérations** : `getProjectIndicators` ; `createNode`, `setTaskProgress`, `updateEstimateLine`,
  `setLineRemaining`, `applyImport`, `updateReferenceSettings` pour ce que chacune change au
  calcul
- **issue** : 2428

**En tant que** chef de projet, **je veux** lire, pour mon projet En cours et pour chacun de ses
sous-projets, l'ensemble « hors sous-projet » compris, le budget de référence, la valeur planifiée,
la valeur acquise, le coût réel et le reste à engager au jour courant, les avancements financier et
physique, la consommation du budget, les deux indices avec leur zone et leur écart, et les trois
projections à terminaison — chacun présenté non calculable, jamais zéro ni infini, quand une
grandeur manque —, **afin de** savoir où en est mon projet entre deux revues.

**Critères d'acceptation.**

- `WF-IND-0010-A` — « Les indicateurs d’une révision marquée ne changent pas après son marquage,
  même après l’import d’une ligne de coût datée avant le marquage, qui n’entre ni dans son coût
  réel ni dans ses courbes. » : par US-1670, qui conserve au marquage ; ici, le calcul au jour
  courant lit les lignes de coût connues au moment du calcul ;
- `WF-IND-0010-A` — « Une ligne de coût datée après la date de marquage n’entre pas dans le coût
  réel de cette révision. » : par US-1670 ; ici, le coût réel au jour courant est la somme des
  lignes du périmètre suivi dont la date de pièce est antérieure ou égale au jour du calcul
  (`actual_costs_until` d'EP-09), une ligne datée du lendemain n'y entrant pas ;
- `WF-IND-0010-A` — « Sur un projet à l’état Chiffrage, aucun indicateur projet n’est proposé. » :
  `getProjectIndicators` refuse un projet antérieur à En cours par 409 `STATE_FORBIDS_OPERATION`,
  `params.state` et `params.state_enum` ; les trois autres lectures d'indicateurs projets, par
  US-1690, US-1700 et US-1710 ; les indicateurs de devis restent servis (EP-07) ;
- `WF-IND-0010-A` — « Un indice de coût sans coût réel est affiché non calculable. » :
  `cost_index.value` est `{is_computable: false, value: null, reason: no_actual_cost}`, sa `zone`
  nulle ; l'écran, par US-1730 ;
- `WF-IND-0010-A` — « Sur un projet sans révision en cours, un import de coûts réels change les
  indicateurs au jour courant et laisse inchangés ceux conservés de la dernière révision
  marquée. » : sans révision en cours, `getProjectIndicators` sans `revision_id` calcule sur la
  dernière révision marquée avec le coût réel du jour, `context.revision_id` la nommant,
  `revision_status` `marked`, `is_stored` faux ; après l'application d'une extraction (EP-09), ce
  calcul change ; ceux conservés, par US-1670 ;
- `WF-IND-0020-A` — « La somme des valeurs acquises des sous-projets, ensemble « hors
  sous-projet » compris, égale celle du projet, de même pour le budget de référence, le coût réel,
  la valeur planifiée et le reste à engager. » : sur un projet à deux sous-projets et des lignes
  et des coûts hors sous-projet, les cinq montants lus avec `scope` sur chaque sous-projet et sur
  `unassigned` somment à ceux du projet, au centime ;
- `WF-IND-0020-A` — « Une ligne passée du sous-projet A au sous-projet B après la référence
  acquiert sa valeur dans A, et compte son reste à engager dans B. » : le budget de référence, la
  valeur planifiée et la valeur acquise d'un sous-projet se calculent sur les lignes qui lui
  appartiennent dans la révision de référence, le reste à engager sur celles qui lui appartiennent
  dans la révision calculée ; une ligne portée de A à B par `updateEstimateLine` (EP-07) sur la
  révision en cours, puis terminée, est acquise dans A et comptée au reste dans B ;
- `WF-IND-0030-A` — « Une tâche terminée le 12 du mois contribue à la valeur acquise dès cette
  date, non à la revue suivante. » : la valeur acquise au jour courant compte les montants budgétés
  des lignes de la référence dont la tâche, par sa lignée, est terminée dans la révision calculée
  à une date antérieure ou égale au jour du calcul (`completed_on`, EP-06) ; terminée le 12, elle
  compte dès le 12 ;
- `WF-IND-0030-A` — « Une tâche dont le coût réel dépasse le montant budgété contribue pour le
  montant budgété. » : la valeur acquise ne lit aucune ligne de coût ;
- `WF-IND-0030-A` — « La valeur acquise d’un projet dont toutes les tâches sont terminées égale
  son budget de référence ; les tâches issues d’un risque survenu n’y contribuent pas. » : toutes
  les tâches terminées, la valeur acquise vaut le budget de référence ; les lignes de provision et
  les tâches issues d'un risque survenu (`origin_risk_id`, nul avant EP-08) sont d'EP-08, qui
  clôt — la règle « hors provision, hors survenance » est écrite dans la sélection des lignes ;
- `WF-IND-0040-A` — « Sur un sous-projet de budget 100, de coût réel 70 et de reste à engager 70,
  l’avancement financier vaut 50 % et la consommation 70 %. » : `financial_progress` `0.5000`,
  `budget_consumption` `0.7000`, un test sans base du module et le même sur le service ;
- `WF-IND-0040-A` — « Un sous-projet sans coût réel ni reste à engager affiche un avancement
  financier non calculable. » : `no_actual_or_remaining` ;
- `WF-IND-0050-A` — « Sur un projet de budget 1 000, de valeur acquise 400, de coût réel 500 et de
  reste à engager 550, les projections valent 1 100 au budget, 1 050 pour le chef de projet et
  1 250 au rythme constaté. » : `projections.at_budget`, `project_manager`, `at_observed_rate`,
  et leurs écarts au budget `100.00`, `50.00`, `250.00` ; un test sans base et le même sur le
  service ;
- `WF-IND-0050-A` — « Avant tout coût réel, la projection au rythme constaté est non calculable et
  les deux autres sont affichées. » : `at_observed_rate` `no_actual_cost`,
  `variance_at_observed_rate` nul, les deux autres présentes ; sans valeur acquise mais avec un
  coût réel, `no_earned_value` ;
- `WF-IND-0060-A` — « Sur un budget de 1 000 dont 400 sont portés par des tâches terminées,
  l’avancement physique vaut 40 %. » : `physical_progress` `0.4000`, le rapport de la valeur
  acquise au budget de référence, `no_reference_budget` sur un budget nul ;
- `WF-IND-0060-A` — « Une tâche démarrée à 90 % de son temps ne contribue pas. » : seule la
  terminaison acquiert ; une tâche démarrée compte zéro ;
- `WF-IND-0060-A` — « Une récapitulative sans ligne propre dont les deux premières de trois
  subordonnées, de montants budgétés 100, 100 et 200, sont terminées affiche 50 % ; si la
  troisième est terminée à la place de la deuxième, 75 %. » : l'avancement physique d'une
  récapitulative, par US-1680 ;
- `WF-IND-0070-A` — « Une valeur acquise de 400 pour un coût réel de 500 donne 0,8. » :
  `cost_index.value.value` `0.8000`, à quatre décimales ;
- `WF-IND-0070-A` — « L’indice change de zone quand il franchit un seuil, dans un sens comme dans
  l’autre. » : la zone est classée à chaque lecture sur les seuils courants du référentiel
  (`index_zone` d'EP-05, `getReferenceSettings`) : un indice de 0,85 est en vigilance aux seuils
  0,9 et 0,8, nominal après `updateReferenceSettings` à 0,85 et 0,7, en alerte à 0,95 et 0,9 ;
- `WF-IND-0070-A` — « Avant le premier import de coûts réels, il est affiché non calculable. » :
  `no_actual_cost`, zone nulle ;
- `WF-IND-0070-A` — « Une valeur acquise de 400 pour un coût réel de 500 donne un écart de coût de
  −100. » : `cost_variance` `-100.00` ;
- `WF-IND-0080-A` — « Une valeur acquise de 400 pour une valeur planifiée de 500 donne 0,8. » :
  `schedule_index.value.value` `0.8000` ;
- `WF-IND-0080-A` — « Avant la date de début de la première tâche de la référence, l’indice est non
  calculable. » : la valeur planifiée au jour du calcul est nulle avant le début de la première
  tâche de la référence qui porte une ligne budgétée de la maille, `no_planned_value`, zone nulle ;
- `WF-IND-0080-A` — « Un projet dont toutes les tâches sont terminées à la date de fin prévue par
  la référence affiche 1. » : à cette date, valeur acquise et valeur planifiée valent toutes deux
  le budget de référence, `1.0000`, nominal ;
- `WF-IND-0080-A` — « Une valeur acquise de 400 pour une valeur planifiée de 500 donne un écart de
  délai de −100. » : `schedule_variance` `-100.00` ;
- `WF-RAE-0050-A` — « Après ajout d’une tâche chiffrée en revue périodique, le reste à engager et
  la projection du chef de projet augmentent de son montant ; le budget de référence, la
  projection au budget, la projection au rythme constaté et l’indice de coût sont inchangés. » :
  une tâche créée avec une ligne sur la structure principale d'un projet En cours (EP-06, EP-07 ;
  budgété nul, EP-09) : `remaining` et `projections.project_manager` augmentent de son réestimé,
  `reference_budget`, `at_budget`, `at_observed_rate` et `cost_index` ne bougent pas ;
- `WF-RAE-0050-A` — « Lorsque la dépense de cette tâche est importée au coût réel, la valeur acquise
  ne change pas et l’indice de coût baisse. » : après l'application d'une extraction qui porte une
  pièce de cette tâche (EP-09, US-1610), `earned_value` est inchangée, `actual_cost` augmente et
  `cost_index` baisse ;
- `WF-REF-0170-A` — « Les quatre seuils sont saisissables, et le seuil d’alerte de chaque indice
  est inférieur à son seuil de vigilance. » : constaté par EP-05 (US-0810) ;
- `WF-REF-0170-A` — « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à 0,5,
  avec des seuils fixés à 0,9 et 0,8. » : un test sans base d'`index_zone` sur la suite 1, 0,95,
  0,9, 0,85, 0,8, 0,75, 0,5 — nominal jusqu'à 0,9 compris, vigilance jusqu'à 0,8 compris, alerte
  ensuite — et le même sur le service, l'indice de coût d'un projet dont le coût réel croît ;
- `WF-REF-0170-A` — « Avec des seuils à 0,9 et 0,8, un indice de 0,9 est nominal et un indice de
  0,8 en vigilance. » : `zone` `nominal` à 0,9, `watch` à 0,8 ;
- propre à l'US : `getProjectIndicators` lit la révision en cours — `revision_id` absent, ou celui
  de la révision en cours — au jour courant, ou la dernière révision marquée sans elle ; pour le
  projet, un sous-projet ou « hors sous-projet » (`scope` ; un sous-projet que le projet n'a pas
  ou un identifiant mal formé, 422 `VALIDATION_FAILED`, `UNKNOWN_SUBPROJECT` sur `/query/scope` ;
  `revision_id` et `as_of` ensemble, 422 sur `/query/revision_id`) ; `context` dit la révision, son
  état, `computed_at` l'instant du calcul, `scope`, `is_stored` faux ; `reference_budget` est la
  somme des montants budgétés des lignes de la référence de la maille, hors provision ;
  `planned_value` leur étalement sur les dates de la référence au prorata des heures travaillées,
  par le module pur d'EP-07 (`spreading`), à la date du calcul ; `earned_value` et `remaining`
  comme ci-dessus ; les montants au centime, les ratios et les indices à quatre décimales, arrondis
  une fois (`ROUND_HALF_EVEN`, WF-DAT-0100) ; sous `project_indicators.read` ; chaque réponse est
  validée contre le contrat dans les tests du service, et `test_access_evaluation.py` reçoit
  l'opération avec ses deux termes ;
- propre à l'US (lot technique) : la migration d'EP-10, chaînée sur `0025` et seule de l'EPIC —
  la table `revision_indicator` du Tableau 10, régime révisionné, partitionnée par projet, son
  déclencheur d'immuabilité, sa partition créée par `create_project_partitions`, les droits du rôle
  du service — ; le module `core/indicators` à vide avec son interface en paquet, enregistré à vide
  dans `register_indicators` d'EP-04 ; le contrat de couches ; un routeur vide par US enregistré
  dans `app.py` avec la déclaration des opérations et des permissions par routeur ; les fichiers de
  tests et `tests/indicators_support.py` ; le test des points d'entrée (#2180) étendu à ce que
  l'API, le worker et le chargeur attendent d'EP-10, et à partir de quel lot ; `make check` passe
  sur ce socle, tiré d'`epic/EP-09`. **Lot pivot d'EP-08.**

**Notes de réalisation.** Le module est `core/indicators` (FBS-4.8), au-dessus de `estimate`,
`costs`, `planning`, `revisions`, `projects` et `indicator_settings`, qu'il lit par leurs
interfaces et qu'aucun n'importe : les lignes et leurs montants par `core/estimate` (EP-07, EP-09 :
`remaining_of_revision`, `spreading`, `planned_value` pour l'épreuve), les tâches, leurs états et
leurs dates par `core/planning` (EP-06, US-1410 #2324), les coûts par `core/costs`
(`actual_costs_until`, US-1610/L2 #2404), la zone par `index_zone` (EP-05). Le périmètre d'une
maille se décide par le sous-projet de la ligne dans la révision lue (WF-IND-0020). La conception
fixe les lectures nouvelles que `core/estimate` et `core/planning` déclarent pour lui, et
l'arrondi. Le socle de l'EPIC est le premier lot de cette US, et le lot pivot d'EP-08.

**Hors périmètre.** La conservation au marquage et la lecture d'une révision marquée (US-1670) ;
l'avancement physique des récapitulatives (US-1680) ; les courbes (US-1690) ; l'évolution des
indices (US-1700) ; le cache (US-1720) ; l'écran (US-1730) ; la valeur acquise devant un risque
survenu et le budget devant un avenant (EP-08) ; le portefeuille (EP-11).

---

## US-1670 — Le calcul au marquage et la conservation des indicateurs d'une révision marquée

- **statut** : à faire
- **exigences** : `WF-DAT-0040-A`, `WF-IND-0010-A`, `WF-CYC-0090-A`, `WF-REF-0130-A`
- **opérations** : `markRevision`, `exitProject` (la transaction du marquage) ;
  `getProjectIndicators` (`revision_id`, `as_of`), `getEstimateIndicators`,
  `getRemainingIndicators` (`is_stored`) ; `applyImport`, `setActualCostTrackedScope`,
  `updateReferenceSettings` pour ce qu'ils ne changent pas
- **issue** : 2429

**En tant que** chef de projet, **je veux** que le marquage d'une révision calcule ses indicateurs à
sa date, pour le projet et pour chaque sous-projet, et les conserve avec elle, que je les relise
tels quels ensuite quelles que soient les lignes de coût importées, exclues ou mises à jour depuis,
et qu'une offre marquée en chiffrage ne conserve que son devis, **afin que** mes revues passées
restent ce qu'elles étaient le jour où je les ai tenues.

**Critères d'acceptation.**

- `WF-DAT-0040-A` — « Le marquage d’une révision échoue entièrement si le calcul de ses indicateurs
  échoue. » : le calcul enregistré par `register_indicators` s'exécute dans la transaction du
  marquage, après les images d'EP-07 (`register_marking`) et avant que la révision ne s'écrive ;
  une exception du calcul — une erreur de données, une exception typée — fait échouer la tâche
  `revision_mark` avec son code (`BackgroundTask.problem`), rien n'est écrit, la révision reste en
  cours et un nouveau `markRevision` la relance ; c'est la politique d'erreur de
  `compute_indicators` que #2180 (point 2) demandait : aucune exception n'est attrapée ni
  remplacée par un indicateur absent ;
- écart : `WF-DAT-0040-A` — « Aucune vue de portefeuille à une date passée, sur trois cents projets
  — plan de charge agrégé, structure des coûts et risques compris —, ne lit de ligne de tâche ni
  de ligne de devis. » : le portefeuille est d'EP-11, qui clôt, et conserve de plus au marquage ce
  qu'il lit (la charge par rôle et par mois, les totaux par nature et par nœud d'organisation) ; les
  risques sont d'EP-08 ;
- `WF-DAT-0040-A` — « Les indicateurs conservés d’une révision marquée sont identiques avant et
  après un import de coûts réels postérieur. » : après le marquage, l'application d'une extraction
  (EP-09) qui apporte une ligne datée avant le marquage et met à jour une ligne connue au marquage,
  `getProjectIndicators` avec `revision_id` de la révision marquée rend la même réponse, octet pour
  octet hors rien, `is_stored` vrai ;
- `WF-DAT-0040-A` — « Le marquage d'une offre, sur un projet en chiffrage, aboutit et conserve le
  total du devis sans aucun indicateur projet. » : sur un projet en Chiffrage, le marquage conserve
  les indicateurs de devis par maille (`EstimateIndicators`) et aucun indicateur projet ; `getProjectIndicators`,
  `getCostCurve` et `getEarnedValueCurves` refusent cette révision par 409 `STATE_FORBIDS_OPERATION`
  sans `params.state`, le projet fût-il passé En cours depuis (#1779, G-02) ;
- `WF-DAT-0040-A` — « La courbe de coût réel d’une révision marquée est identique avant et après
  l’exclusion d’une ligne de coût connue à son marquage. » : les courbes conservées, par US-1690 ;
  ici, le document conservé des indicateurs ne change pas après `setActualCostTrackedScope` ;
- `WF-IND-0010-A` — « Les indicateurs d’une révision marquée ne changent pas après son marquage,
  même après l’import d’une ligne de coût datée avant le marquage, qui n’entre ni dans son coût
  réel ni dans ses courbes. » : le coût réel conservé est la somme des lignes suivies connues au
  marquage, telles qu'elles étaient alors, datées au plus tard du jour du marquage ; une ligne
  importée ensuite, quelle que soit sa date de pièce, n'y entre pas ; les courbes, par US-1690 ;
- `WF-IND-0010-A` — « Une ligne de coût datée après la date de marquage n’entre pas dans le coût
  réel de cette révision. » : une ligne connue au marquage et datée du lendemain compte zéro
  (`actual_costs_until` à la date du marquage) ;
- `WF-IND-0010-A` — « Sur un projet à l’état Chiffrage, aucun indicateur projet n’est proposé. » :
  le marquage n'en calcule aucun avant l'état En cours — l'état du projet lu sous son verrou, dans
  la transaction du marquage — ; la lecture, par US-1660 ;
- `WF-IND-0010-A` — « Un indice de coût sans coût réel est affiché non calculable. » : constaté
  par US-1660 ; ici, le document conservé porte l'enveloppe non calculable telle quelle ;
- `WF-IND-0010-A` — « Sur un projet sans révision en cours, un import de coûts réels change les
  indicateurs au jour courant et laisse inchangés ceux conservés de la dernière révision
  marquée. » : le calcul du jour, par US-1660 ; ici, les documents conservés de la dernière
  révision marquée sont identiques avant et après l'import ;
- `WF-CYC-0090-A` — « La confirmation nomme l’état visé et le passage en lecture seule du projet et
  de toutes ses données, et propose la saisie d’un motif ; une sortie confirmée sans motif est
  appliquée. » : constaté par EP-04 (US-0980) ;
- `WF-CYC-0090-A` — « La sortie d’un projet qui porte une révision en cours demande de la marquer ou
  de l’abandonner ; après la sortie, le projet n’a plus de révision en cours, et ses indicateurs se
  lisent dans sa dernière révision marquée (WF-IND-0010). » : la demande et la sortie, constatées
  par EP-04 ; ici, une sortie qui marque calcule et conserve les indicateurs de la révision
  marquée dans la même transaction, et `getProjectIndicators` sans `revision_id` sur le projet
  sorti calcule sur elle avec le coût réel du jour, `revision_id` la nommant, `is_stored` faux ;
  avec son `revision_id`, le document conservé ;
- `WF-REF-0130-A` — « Après correction d’un taux horaire et changement de la catégorie d’un rôle,
  les montants d’une révision marquée qui les employait sont identiques à ceux relevés avant la
  modification. » : constaté par EP-07 (US-1500) ;
- `WF-REF-0130-A` — « Après abaissement du seuil d’alerte, la zone de l’indice de coût d’une
  révision marquée peut changer, sa valeur non. » : le document conservé porte la valeur de
  l'indice, jamais sa zone ; la zone est classée à la lecture sur les seuils courants
  (`IndexValue.zone`), et `updateReferenceSettings` la change sans toucher la valeur ;
- propre à l'US : `revision_indicator` conserve, par révision marquée, un document par nature et
  par maille — les indicateurs de devis (`EstimateIndicators`, toute révision marquée), les
  indicateurs de reste à engager (`RemainingIndicators`, toute révision marquée), les indicateurs
  projet (`ProjectIndicators`, à partir de l'état En cours), les courbes par US-1690 —, pour le
  projet, chaque sous-projet et « hors sous-projet », avec l'instant du calcul, celui du marquage
  (`marked_at`) ; une révision marquée ne conserve rien d'autre (WF-DAT-0020 : le déclencheur
  d'immuabilité refuse toute écriture ensuite) ;
- propre à l'US : `getProjectIndicators` avec le `revision_id` d'une révision marquée rend le
  document conservé de la maille, `context.is_stored` vrai, `computed_at` l'instant du marquage,
  `revision_status` `marked` ; avec `as_of`, celui de la dernière révision marquée antérieure ou
  égale à la date, `context.revision_id` la nommant ; `as_of` qui ne désigne aucune révision
  marquée à l'état En cours est refusé par 409 `STATE_FORBIDS_OPERATION`, sans `params.state`,
  comme l'offre (proposition du constat « contrat » de l'EPIC, que l'auteur tranche) ;
- propre à l'US : `getEstimateIndicators` (EP-07) et `getRemainingIndicators` (EP-09) avec le
  `revision_id` d'une révision marquée rendent le document conservé, `is_stored` vrai, les parts et
  la couverture telles qu'elles étaient au marquage ; sur la révision en cours, le calcul à la
  lecture d'EP-07 et d'EP-09, `is_stored` faux, inchangé ;
- propre à l'US : le worker porte l'extension — il importe l'interface de `core/indicators`, après
  US-1610/L2 #2404 d'EP-09, dernier lot à écrire `worker/main.py` — et le test des points d'entrée
  (#2180) dit que l'API et le chargeur l'attendent dès le socle, le worker à partir de ce lot ;
  `load-witness` conserve les indicateurs des révisions marquées du témoin par la même transaction
  (`load_marking`), sans tranche propre ; chaque réponse est validée contre le contrat dans les
  tests du service.

**Notes de réalisation.** Le registre est celui d'EP-04 (`register_indicators` de
`core/revisions`), appelé par `mark_revision` avant que la révision ne s'écrive ; le calcul reçoit
l'instant du marquage, que la transaction prend sous ses verrous (la conception dit comment). La
politique d'erreur est le point 2 de #2180, ouvert en constat de l'EPIC. L'état du projet au
marquage se lit sous le verrou du projet, pris après celui de la révision (l'ordre d'EP-04). Les
routes d'EP-07 (`api/estimate_indicators.py`, US-1510 #2363) et d'EP-09
(`api/remaining_indicators.py`, US-1600 #2392) sont complétées après ces lots pour lire le document
conservé d'une révision marquée. Le constat « contrat » du refus d'`as_of` s'ouvre avec les issues
de l'EPIC, « à trancher » ; le lot suit la décision.

**Hors périmètre.** Le calcul lui-même (US-1660) ; les courbes conservées (US-1690) ; l'évolution
des indices (US-1700) ; la charge par rôle et par mois, les totaux par nœud d'organisation et les
risques conservés pour le portefeuille (EP-11, EP-08).

---

## US-1680 — L'avancement physique des récapitulatives dans la grille de planning

- **statut** : à faire
- **exigences** : `WF-IND-0060-A`, `WF-PLA-0130-A`
- **opérations** : `listNodes` (`TaskFacet.physical_progress`), `setTaskProgress`
- **issue** : 2430

**En tant que** chef de projet, **je veux** lire dans la grille de planning l'avancement physique de
chaque récapitulative — la part des montants budgétés de son sous-arbre que ses tâches terminées
ont acquise —, **afin de** voir l'avancement de chaque phase sans rien saisir.

**Critères d'acceptation.**

- `WF-IND-0060-A` — « Sur un budget de 1 000 dont 400 sont portés par des tâches terminées,
  l’avancement physique vaut 40 %. » : pour le projet et les sous-projets, constaté par US-1660 ;
  ici, une récapitulative dont le sous-arbre porte 1 000 de budgété dont 400 sur des tâches
  terminées affiche `0.4000` ;
- `WF-IND-0060-A` — « Une tâche démarrée à 90 % de son temps ne contribue pas. » : une subordonnée
  démarrée compte zéro dans l'avancement de sa récapitulative ;
- `WF-IND-0060-A` — « Une récapitulative sans ligne propre dont les deux premières de trois
  subordonnées, de montants budgétés 100, 100 et 200, sont terminées affiche 50 % ; si la
  troisième est terminée à la place de la deuxième, 75 %. » : `TaskFacet.physical_progress`
  `0.5000` puis `0.7500`, un test sans base du module et le même sur le service par `listNodes` ;
  les lignes propres de la récapitulative comptent au total et s'acquièrent quand elle est
  terminée ; une récapitulative dont le sous-arbre ne porte aucun montant budgété est non
  calculable (`no_budgeted_amount`) ; une feuille et un jalon portent `null` ;
- `WF-PLA-0130-A` — « Chacun de ces attributs est affiché dans la grille de planning, et ceux que
  MS Project connaît sont transportés par l’export. » : constaté par EP-06 (US-1410, US-1430,
  US-1470) ; ici, la colonne « Avancement physique » de la grille (EP-02, US-0220) lit
  `physical_progress` du service, en pourcentage, avec « non calculable » dit ;
- `WF-PLA-0130-A` — « Le passage à l’état démarré ou terminé demande une date, proposée au jour
  courant et modifiable. » : constaté par EP-06 (US-1410) et EP-09 (US-1590) ;
- `WF-PLA-0130-A` — « Un import de reste à engager qui met une tâche à zéro la date de la revue que
  porte le fichier ; une récapitulative porte la date de terminaison de sa dernière
  subordonnée. » : constaté par EP-09 (US-1630) et EP-06 (US-1410) ;
- `WF-PLA-0130-A` — « La durée d’un jalon est nulle et n’est pas modifiable ; les dates d’une
  récapitulative ne sont pas saisissables. » : constaté par EP-06 (US-1380) ;
- `WF-PLA-0130-A` — « La marge totale, la criticité et l’avancement physique s’affichent et ne sont
  pas saisissables. » : la marge et la criticité, constatées par EP-06 (US-1390, US-1470) ; ici,
  `physical_progress` est rendu par `listNodes`, absent de `TaskFacetWrite`, et la cellule de la
  grille est calculée (`computed_fields`) ;
- propre à l'US : `core/planning` déclare un registre nouveau, dans un fichier propre de son
  interface, que `core/indicators` remplit — « pour ces récapitulatives, l'avancement physique de
  chacune » — et l'appelle à la lecture de la facette tâche pour les récapitulatives rendues, une
  requête par lecture, jamais une par tâche ; sur une révision marquée, le calcul se fait sur ses
  propres lignes et états, immuables ; sur un projet avant En cours, le calcul vaut aussi, aucune
  tâche n'y étant terminée ; chaque réponse est validée contre le contrat dans les tests du service
  ; la grille de planning (EP-06, US-1470 #2326) montre la colonne contre le service, son parcours
  de `planning.spec.ts` déjà `@shared`.

**Notes de réalisation.** Le crochet est de la même forme que `register_open_lines` d'EP-09 : un
fichier nouveau de `core/planning/interface/`, réexporté par `core/planning/interface/__init__.py`
— qu'EP-06 écrit jusqu'à US-1390/L2 #2339 et EP-09 jusqu'à US-1590/L1 #2401 —, appelé par la lecture
de la facette (US-1380/L2 #2335, puis #2401 pour `awaiting_own_lines`) ; le lot attend ces trois
numéros et US-1410 #2324 (les états). Le module des indicateurs calcule : les montants budgétés
des lignes hors provision du sous-arbre par `core/estimate`, l'état des tâches par `core/planning`.

**Hors périmètre.** L'avancement physique du projet et des sous-projets (US-1660) ; la grille
elle-même (EP-06) ; les lignes de provision et les tâches issues d'un risque survenu (EP-08).

---

## US-1690 — Les courbes : coûts cumulés, décaissements, valeur acquise, conservées au marquage

- **statut** : à faire
- **exigences** : `WF-IND-0100-A`, `WF-IND-0110-A`
- **opérations** : `getCostCurve`, `getEarnedValueCurves` ; `markRevision` (les courbes conservées)
- **issue** : 2431

**En tant que** chef de projet, **je veux** lire, au pas du mois, la courbe des coûts cumulés — le
budget de référence, le coût réel jusqu'au jour du calcul, puis la projection du chef de projet —,
la même décalée des délais de paiement avec les décaissements par mois, et les courbes de valeur
acquise — valeur planifiée, valeur acquise, coût réel —, pour le projet ou pour une maille, sur la
révision en cours ou telles qu'une révision marquée les a conservées, **afin de** voir d'un regard si
le projet dépense au rythme prévu et où il atterrira.

**Critères d'acceptation.**

- `WF-IND-0100-A` — « La courbe du budget de référence atteint le budget de référence à la date de
  fin de la référence. » : la série `reference_budget`, le budgété de chaque ligne de la référence
  hors provision étalé sur les dates de sa tâche au prorata des heures travaillées (le module pur
  d'EP-07), cumulé à chaque fin de mois, vaut le budget de référence au point du mois de la fin de
  la dernière tâche de la référence et ne bouge plus ensuite ;
- `WF-IND-0100-A` — « Celle du coût réel s’arrête à la date de calcul, et la projection part de ce
  point pour atteindre la projection du chef de projet. » : `actual_cost` cumule les lignes suivies
  par mois de date de pièce jusqu'à la date de calcul, point de plus ; `project_manager_projection`
  part de ce point, le reste à engager de chaque ligne (EP-09, `remaining_of_revision`) étalé sur la
  part de la durée de sa tâche postérieure à la date de calcul et porté entier au point du mois de
  la date de calcul quand la fin de la tâche est dépassée, et atteint `projections.project_manager`
  d'US-1660 ;
- écart : `WF-IND-0100-A` — « Après contractualisation d’un avenant qui porte le budget de 1 000 à
  1 200, la courbe du budget présente, au point du mois de l’avenant, une marche égale à l’écart des
  deux cumulés à cette date, et atteint 1 200 à la date de fin de la nouvelle référence. » :
  l'avenant est d'EP-08, qui clôt ; ici, `steps` est rendu vide, et la série du budget lit la seule
  référence désignée ;
- `WF-IND-0100-A` — « Avec un délai de paiement de 60 jours saisi sur toutes les lignes,
  main-d’œuvre comprise, la courbe du budget de référence décalée est la courbe non décalée
  translatée de 60 jours ; la projection l’est aussi, hormis les lignes de provision, qui restent à
  leur date ; le coût réel n’est pas décalé. » : avec `payment_delays`, chaque part du budget et de
  la projection est décalée du `payment_delay_days` de sa ligne avant le cumul mensuel, le coût réel
  non ; les lignes de provision sont d'EP-08, qui clôt, et aucune n'existe ici ;
- `WF-IND-0100-A` — « La somme des décaissements à venir égale le reste à engager, provisions des
  risques identifiés comprises. » : la somme des `forecast` de `cash_out_by_month` égale `remaining`
  d'US-1660 au centime ; les provisions sont d'EP-08, qui clôt, et comptent zéro ici ;
- `WF-IND-0110-A` — « À la date de calcul, l’écart vertical entre la courbe de valeur acquise et
  celle du coût réel égale la différence des deux grandeurs. » : au point de la date de calcul,
  `earned_value` moins `actual_cost` des séries vaut `cost_variance` d'US-1660 ;
- `WF-IND-0110-A` — « La courbe de valeur planifiée atteint le budget de référence à la fin de la
  référence. » : `planned_value` se prolonge jusqu'à la fin de la référence et y vaut le budget ;
- `WF-IND-0110-A` — « Une tâche terminée produit une marche dans la valeur acquise au point du mois
  de sa date de terminaison. » : la valeur acquise cumule les montants budgétés par mois de
  `completed_on` ; le point du mois de la terminaison porte la marche, le précédent non ;
- propre à l'US : chaque série porte un point par fin de mois (`CurveSeries`) — le premier, nul, à
  la fin du mois qui précède le premier montant ; la date de calcul en point de plus sur
  `actual_cost`, `earned_value` et `project_manager_projection` — ; `payment_delays` dit si les
  séries sont celles des décaissements, `cash_out_by_month` les détaille alors, le passé par mois de
  date de pièce, l'avenir par mois de part décalée, le mois de la date de calcul portant les deux,
  nul sinon ; `scope` restreint chaque série aux lignes et aux coûts de la maille — une maille sans
  ligne dans la référence ni dans la révision calculée et sans coût réel a des séries sans point,
  `steps` vide et `cash_out_by_month` vide avec les délais ; le budget d'une maille qu'aucune
  référence ne budgète est une série sans point — ; les refus sont ceux de `getProjectIndicators`
  (409 avant En cours et sur une révision marquée avant lui, 422 sur `scope`, sur `revision_id` et
  `as_of` ensemble) ; sous `project_indicators.read` ; chaque réponse est validée contre le
  contrat dans les tests du service ;
- propre à l'US : les deux courbes de chaque maille sont conservées au marquage avec les
  indicateurs (US-1670), sur les lignes de coût connues au marquage telles qu'elles étaient alors,
  et rendues telles quelles pour une révision marquée, `is_stored` vrai : la courbe de coût réel
  conservée est identique avant et après l'exclusion d'une ligne connue au marquage et avant et
  après un import postérieur (WF-DAT-0040, WF-IND-0010) ; les deux variantes de `payment_delays`
  sont conservées ; sur la révision en cours, ou au jour courant sans elle, les courbes se
  calculent à la lecture, `is_stored` faux.

**Notes de réalisation.** L'étalement est celui d'EP-07 (`spreading`, US-1520/L1 #2376 : au
prorata des heures travaillées du calendrier du rôle de la ligne, du calendrier applicable de la
tâche sinon), les dates des tâches celles d'EP-06, le reste par ligne celui d'EP-09 (US-1580/L2
#2399), les lignes de coût celles d'US-1610/L2 #2404. Le lot des courbes conservées attend le lot de
la conservation (US-1670). Le pas du mois et les points de la date de calcul suivent
`docs/api/DECISIONS.md`, « Les courbes au pas du mois, conservées au marquage » (G-01, M-02) et
« Les décaissements… » (M-06).

**Hors périmètre.** Les marches d'avenant et les lignes de provision dans les décaissements
(EP-08) ; la courbe en S du portefeuille (EP-11) ; l'écran (US-1730).

---

## US-1700 — L'évolution des indices

- **statut** : à faire
- **exigences** : `WF-IND-0130-A`
- **opérations** : `getIndexHistory` ; `getReferenceSettings` (les seuils tracés)
- **issue** : 2432

**En tant que** chef de projet, **je veux** lire, pour le projet et pour chaque sous-projet,
l'évolution de l'indice de coût et de l'indice de délai — un point par revue marquée, et le dernier
au jour courant — avec les seuils de vigilance et d'alerte, **afin de** lire chaque indice avec sa
tendance.

**Critères d'acceptation.**

- `WF-IND-0130-A` — « Sur un projet de trois révisions marquées à partir de l’état En cours, chaque
  courbe porte quatre points, le dernier au jour courant ; une révision marquée pendant le
  chiffrage n’en donne aucun (WF-DAT-0040) ; les deux seuils sont tracés ; un sous-projet a ses
  courbes. » : trois révisions marquées En cours et une offre marquée en chiffrage, chaque maille a
  quatre points — un par révision marquée En cours, à `marked_at`, `revision_id` et `version_name`,
  ses deux indices tels que le marquage les a conservés (US-1670), leur zone classée sur les seuils
  courants, un indice non calculable au marquage rendu non calculable, jamais omis (#1777) ; le
  dernier à l'instant du calcul, `version_name` nul, sur la révision en cours ou, sans elle, sur la
  dernière révision marquée avec le coût réel du jour, le calcul d'US-1660 — ; `thresholds` porte
  les quatre seuils du référentiel ; `scopes` liste le projet, chaque sous-projet avec son libellé
  dans l'ordre de `listSubprojects`, puis « hors sous-projet » ;
- propre à l'US : `getIndexHistory` refuse un projet antérieur à En cours par 409
  `STATE_FORBIDS_OPERATION`, `params.state` et `params.state_enum` (#1778) ; avec `scope`, la seule
  maille demandée, que `context.scope` nomme, `UNKNOWN_SUBPROJECT` sur une autre ; `context` est
  celui du dernier point ; sous `project_indicators.read` ; chaque réponse est validée contre le
  contrat dans les tests du service.

**Notes de réalisation.** Les points conservés se lisent dans `revision_indicator` (US-1670), les
indices seuls, la zone classée à la lecture (WF-REF-0130) ; le dernier point est le calcul du jour
d'US-1660 pour chaque maille, que le cache d'US-1720 porte. #1779 (G-01, G-02) se ferme ici et par
US-1710.

**Hors périmètre.** Le diagramme temps/temps (US-1710) ; l'écran (US-1730).

---

## US-1710 — Le diagramme temps/temps

- **statut** : à faire
- **exigences** : `WF-IND-0090-A`, `WF-PLA-0060-A`, `WF-DAT-0030-A`, `WF-RAE-0030-A`
- **opérations** : `getMilestoneTracking` ; `setNodeTracking`, `setTaskProgress` (ce qu'ils y
  changent)
- **issue** : 2433

**En tant que** chef de projet, **je veux** lire, pour chaque jalon inscrit au suivi, la date que
chaque revue marquée prévoyait pour lui en fonction de la date de cette revue, jusqu'à sa
terminaison, et le point du jour courant, **afin de** voir un jalon glisser de revue en revue avant
que quiconque ne l'ait dit.

**Critères d'acceptation.**

- `WF-IND-0090-A` — « Un jalon prévu au 30 juin dans trois revues successives trace une
  horizontale. » : trois révisions marquées En cours qui datent le jalon au 30 juin donnent trois
  points de `forecast_date` `2026-06-30` à leurs `marked_at`, puis le point du jour ;
- `WF-IND-0090-A` — « Un jalon repoussé d’un mois à chacune de trois revues mensuelles trace une
  droite de pente 1. » : les `forecast_date` des trois points avancent d'un mois comme leurs
  `marked_at` ;
- `WF-IND-0090-A` — « Un jalon terminé n’a plus de point après sa terminaison, et son dernier point
  est sur la diagonale. » : les révisions marquées après `completed_on` n'ajoutent aucun point, le
  dernier point est `{marked_at: <completed_on à minuit>, forecast_date: completed_on}`, et le point
  du jour courant n'est pas rendu ;
- `WF-PLA-0060-A` — « Une tâche inscrite apparaît dans la chronologie et disparaît lorsqu’elle est
  retirée. » : constaté par EP-06 (US-1400) ;
- `WF-PLA-0060-A` — « Le diagramme temps/temps ne suit que les jalons inscrits. » : seules les
  lignées qui portent une inscription `milestone_tracking` (EP-06, `tracking_entry`) sont rendues ;
  un jalon retiré du suivi par `setNodeTracking` disparaît à la lecture suivante ;
- `WF-DAT-0030-A` — « Une tâche renommée et déplacée dans la révision en cours est rapprochée de la
  tâche d’origine par la comparaison avec la révision marquée précédente. » : constaté par EP-07
  (US-1530) ;
- `WF-DAT-0030-A` — « Un jalon renommé conserve sa courbe sur le diagramme temps/temps. » : les
  points se lisent par `lineage_id` dans chaque révision marquée ; renommé dans la révision en
  cours, le jalon garde ses points, `label` étant celui de la révision du jour ;
- `WF-DAT-0030-A` — « Deux tâches créées séparément n’ont jamais le même identifiant de lignée. » :
  constaté par EP-06 (US-1380) ;
- `WF-RAE-0030-A` — « Une tâche passée à l’état démarré voit ses lignes apparaître dans la grille
  de reste à engager. » : constaté par EP-09 (US-1590, US-1640) ;
- `WF-RAE-0030-A` — « Une tâche non démarrée n’y apparaît qu’à la demande. » : constaté par EP-09 ;
- `WF-RAE-0030-A` — « Le passage direct de non démarrée à terminée n’est possible que pour un
  jalon, ou par la saisie d’un reste à engager nul sur toutes les lignes d’une tâche non démarrée
  (WF-RAE-0040) ; un jalon sans ligne de devis est terminé depuis le Kanban, à une date saisie. » :
  constaté par EP-06 et EP-09 ;
- `WF-RAE-0030-A` — « Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non
  démarré tant que personne ne le termine. » : constaté par EP-09 (US-1590) ;
- `WF-RAE-0030-A` — « Aucune commande ne fait passer une tâche démarrée à l’état non démarré. » :
  constaté par EP-06 et EP-09 ;
- `WF-RAE-0030-A` — « Un jalon terminé que l’on rouvre est non démarré et ne contribue plus à la
  valeur acquise. » : rouvert (EP-06, `setTaskProgress`), constaté par EP-09 ; ici, la valeur
  acquise au jour courant (US-1660) ne compte plus ses lignes, et son suivi temps/temps reçoit de
  nouveau le point du jour, `completed_on` nul ;
- `WF-RAE-0030-A` — « Une tâche feuille démarrée sans ligne de devis est terminée depuis le
  Kanban. » : constaté par EP-09 ;
- propre à l'US : `getMilestoneTracking` est calculé pour le seul projet, sans `scope` ; un point
  par révision marquée après le passage En cours du projet — l'instant de la transition, lu par
  l'interface des projets, comparé à `marked_at` — qui porte la lignée, à sa date de marquage, la
  date de fin du jalon dans cette révision pour ordonnée ; les révisions marquées avant En cours ne
  donnent aucun point ; le point du jour courant vient de la révision en cours ou, sans elle, de la
  dernière révision marquée, à l'instant du calcul ; `label` et `completed_on` sont ceux de la
  révision du jour ; `context` nomme cette révision, `is_stored` faux ; un projet antérieur à En
  cours est refusé par 409 `STATE_FORBIDS_OPERATION`, `params.state` et `params.state_enum`
  (#1778) ; sous `project_indicators.read` ; chaque réponse est validée contre le contrat dans les
  tests du service.

**Notes de réalisation.** Rien n'est conservé pour le temps/temps : les dates d'un jalon dans
chaque révision marquée sont des lignes immuables de `task` (EP-06), lues par la lignée ; la
conception nomme la lecture que `core/planning` déclare pour cela (les tâches d'une lignée dans les
révisions marquées d'un projet, après US-1380/L2 #2335, US-1390/L2 #2339 et US-1590/L1 #2401) et
celle des inscriptions (US-1400/L2 #2340). Le lot attend aussi US-1410 #2324 (les terminaisons).
#1779 (G-02) se ferme ici et par US-1700.

**Hors périmètre.** L'évolution des indices (US-1700) ; l'export PNG et l'écran (EP-02 ; US-1730) ;
l'inscription elle-même (EP-06).

---

## US-1720 — Le cache des indicateurs au jour courant

- **statut** : à faire
- **exigences** : `WF-DAT-0130-A`
- **opérations** : `getProjectIndicators`, `getCostCurve`, `getEarnedValueCurves`,
  `getIndexHistory` (le dernier point) ; `updateEstimateLine`, `setActualCostTrackedScope`,
  `abandonRevision` pour ce qu'ils invalident
- **issue** : 2434

**En tant qu'** exploitant, **je veux** que les indicateurs au jour courant d'un projet soient tenus
dans Redis, invalidés par toute écriture dont ils dépendent et bornés par une durée de validité, et
que l'indisponibilité de Redis n'empêche ni une lecture ni une saisie, **afin que** la vue vivante
reste juste et que le service ne recalcule pas ce que rien n'a changé.

**Critères d'acceptation.**

- `WF-DAT-0130-A` — « La modification d'une ligne de devis change les indicateurs de la révision en
  cours à la lecture suivante. » : après `updateEstimateLine` (EP-07) ou `setLineRemaining` (EP-09)
  sur la révision en cours, `getProjectIndicators` lu aussitôt rend le reste à engager et les
  projections changés — l'entrée précédente n'est plus servie ;
- `WF-DAT-0130-A` — « Après vidage complet du cache, toutes les valeurs sont recalculées et
  identiques à celles qu'il portait. » : les quatre lectures, lues, le cache vidé par `FLUSHDB` de
  la base des tests, relues, rendent les mêmes réponses, `computed_at` excepté ;
- `WF-DAT-0130-A` — « L'indisponibilité du cache des indicateurs n'empêche aucune lecture ni aucune
  saisie faite par l'API ; la session du front, elle, n'est pas disponible pendant cette
  indisponibilité (§4.5.4). » : Redis pointé sur une adresse qui ne répond pas, `getProjectIndicators`
  répond 200 avec le calcul, dans le délai d'une requête, et une saisie de ligne répond 200 ; la
  session du front, constatée par EP-03 (US-0340) ;
- `WF-DAT-0130-A` — « L'exclusion d'une ligne de coût change l'indice de coût au jour courant à la
  lecture suivante ; l'abandon de la révision en cours présente à la lecture suivante les
  indicateurs de la dernière révision marquée au jour courant. » : après `setActualCostTrackedScope`
  (EP-09), `cost_index` est recalculé ; après `abandonRevision` (EP-04), `getProjectIndicators`
  sans `revision_id` rend le calcul sur la dernière révision marquée avec le coût réel du jour,
  `context.revision_id` la nommant ;
- propre à l'US : l'entrée d'un projet est désignée par une clé qui porte l'empreinte de ce dont les
  indicateurs du jour dépendent, lue à chaque consultation — l'état, la révision en cours, la
  référence et le compteur du projet ; `scheduled_at` et le compteur des structures de la révision
  calculée, le nombre et le dernier `updated_at` de ses nœuds, de ses tâches et de ses lignes ; le
  dernier `imported_at` de `cost_import` et le dernier `updated_at` de `cost_line` du projet ; le
  nombre de sous-projets ; le jour du calcul — : toute écriture dont une entrée dépend change sa clé,
  et une entrée n'est jamais servie pour une clé qui n'est plus celle du projet ; le marquage, la
  désignation, l'application d'un import, l'exclusion et la création d'un sous-projet imputé
  changent ainsi la clé sans qu'aucun de leurs chemins n'appelle le cache ;
- propre à l'US : l'entrée porte, pour chaque maille, les indicateurs et les deux courbes du jour,
  valeurs des indices comprises mais jamais leur zone, classée à la lecture ; sa durée de validité
  est `WATERFALL_INDICATORS_CACHE_TTL`, en secondes, dix minutes par défaut, lue par les réglages
  de l'API ; Redis est celui de la file des tâches, dans la même base, sous un préfixe propre ; une
  erreur de Redis — connexion, délai, réponse — à la lecture comme à l'écriture d'une entrée est
  journalisée une fois et le calcul rendu ; aucune lecture d'une révision marquée ne passe par le
  cache ; un test contre Redis (guide, « Un test contre Redis ») éprouve l'entrée servie, la clé
  changée et l'indisponibilité.

**Notes de réalisation.** La clé versionnée est la décision de l'auteur du 2026-11-07 au cadrage,
contre l'invalidation explicite dans chaque écriture d'EP-06, d'EP-07 et d'EP-09 (conception, « Ce
que le cadrage décide ») ; la conception nomme les lectures qui composent l'empreinte et le module
de la plateforme qui porte le cache, sur le modèle de `platform/queue.py` et de `maintenance.py`.
La variable d'exploitation entre dans `production.env.example` après US-1420/L2 #2341 d'EP-06,
dernier lot à l'écrire.

**Hors périmètre.** La session du front (EP-03) ; les indicateurs conservés, qui ne se cachent pas
(US-1670) ; le portefeuille au jour courant, qui lira ce cache (EP-11).

---

## US-1730 — L'écran des indicateurs branché sur le service

- **statut** : à faire
- **exigences** : `WF-ARC-0070-A`
- **opérations** : `getProjectIndicators`, `getIndexHistory`, `getMilestoneTracking`,
  `getCostCurve`, `getEarnedValueCurves` ; `getRevision`, `listSubprojects`, `listRevisions` que
  l'écran lit
- **issue** : 2435

**En tant que** chef de projet, **je veux** que l'écran des indicateurs — les cartes, l'évolution
des indices, le diagramme temps/temps, la courbe des coûts cumulés et ses décaissements, les
courbes de valeur acquise, par sous-projet, sur une révision marquée ou à une date — travaille
contre le service, **afin de** piloter mon projet sur les chiffres que le serveur calcule.

**Critères d'acceptation.**

- `WF-ARC-0070-A` — « Un appel direct à l’API qui tente de modifier une révision marquée, un projet
  terminal, ou un projet dont l’utilisateur n’est pas contributeur est refusé, alors même que le
  front n’en propose pas l’action. » : constaté par EP-04 (US-0910, US-0970), EP-06 et EP-07 ;
- `WF-ARC-0070-A` — « Un indicateur affiché est identique à celui que l’API renvoie pour la même
  date et le même périmètre. » : le parcours contre le service lit `getProjectIndicators` pour la
  révision et la maille de l'écran et compare chaque chiffre des cartes — montants, pourcentages,
  indices, zones — à la réponse, formatée par le front sans aucun calcul ; les tableaux des
  courbes portent les points de l'API ;
- propre à l'US : l'écran `…/indicators` (EP-02 US-0240, EP-14, EP-15 US-0530) travaille contre le
  service pour PRJ-001 : les cartes et l'évolution des indices sur la révision en cours, la
  révision 101 marquée lue telle que conservée, l'offre 100 refusée et dite, `as_of`, le filtre
  d'un sous-projet et « hors sous-projet », les délais de paiement, le temps/temps sur le projet
  entier, les exports PNG (WF-IHM-0130) ; l'écran ne porte pas de `MockupNotice` ; les aides
  `frontend/help/fr/FBS-4.8*.md` disent ce que le service fait ; `indicators.spec.ts` porte
  `@shared`, et la part des indicateurs de `context.spec.ts` (`BEFORE_THE_DATA`) est levée ; un
  manque que le branchement révèle devient une issue, un manque du contrat une « Interface
  contract issue ».

**Notes de réalisation.** Le front ne calcule rien (US-0240) : les courbes sont rendues par Apache
ECharts à partir des séries du serveur (`components/indicators/`, `components/chart/`). L'US ne
réécrit pas l'écran ; elle le branche et prouve l'identité des chiffres. Elle attend les US qui
servent chaque lecture (US-1660, US-1670, US-1690, US-1700, US-1710).

**Hors périmètre.** Les écrans du portefeuille (EP-11) ; l'écran des risques (EP-08) ; le témoin
et les autres parcours (US-1740).

---

## US-1740 — Le témoin : les indicateurs conservés et au jour courant de PRJ-001, et les parcours rejoués

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`, `WF-INTF-0010-A`
- **opérations** : aucune en propre ; les lectures de l'EPIC sur le témoin chargé
- **issue** : 2436

**En tant que** développeur, **je veux** que PRJ-001, chargé, porte les indicateurs que le marquage
rejoué de sa révision 101 a conservés et ceux du jour, que le service les compare aux exemples du
contrat, et que tous les parcours des indicateurs écrits sur le faux back se rejouent contre le
service, **afin que** les tests déjà écrits prouvent le service sur le plus gros projet.

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour les indicateurs — les documents conservés de la révision 101 de PRJ-001, pour
  le projet, ses deux sous-projets et « hors sous-projet », calculés par le marquage rejoué du
  chargeur (`load_marking`, EP-04) à son instant, le 1er février 2026 à 9 h, sans tranche propre ;
  l'offre 100 sans indicateur projet ; les indicateurs du jour sur la révision 102 —, chargés par
  `waterfall-api load-witness` ; les risques et les provisions sont d'EP-08, les révisions marquées
  suivantes et les volumes entiers d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes
  identiques. » : deux plateformes chargées portent les mêmes documents conservés, au centime ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  rien n'est ajouté au témoin ;
- écart : `WF-INTF-0010-A` — « Un utilisateur porteur du rôle prédéfini « chef de projet » crée un
  projet et atteint, sur un projet où il est habilité, les fonctions de gestion des révisions
  (FBS-4.1), de paramétrage du projet, contributeurs compris (FBS-4.2), de planification (FBS-4.3),
  de chiffrage (FBS-4.4), de gestion des risques (FBS-4.6), d’estimation du reste à engager
  (FBS-4.5), de gestion des coûts réels (FBS-4.7), de lecture des indicateurs (FBS-4.8), de sortie
  du cycle de vie (FBS-4.9) et d’échange des fichiers du tableau des flux (FLX-01 à FLX-07), et les
  mène jusqu’à leur terme, marquage d’une révision, exclusion d’une ligne de coût et déclaration
  d’une sortie compris. » : la lecture des indicateurs (FBS-4.8), ici, par le compte « chef de
  projet » de la course, sur un projet qu'il crée, chiffre, passe En cours et dont il marque une
  revue ; les autres fonctions sont constatées par EP-04, EP-06, EP-07 et EP-09 ; les risques sont
  d'EP-08, qui clôt ;
- propre à l'US : les lectures du témoin chargé — `project_indicators`, `project_indicators_marked`,
  `project_indicators_offer`, `index_history`, `index_history_subproject`, `milestone_tracking`,
  `cost_curve`, `cost_curve_payment_delays`, `cost_curve_subproject`, `earned_value_curves`,
  `estimate_indicators` et `remaining_indicators` sur la révision 101 — sont comparées aux exemples,
  à la référence, aux provisions, aux risques et aux montants qui en dépendent près, listés dans le
  test : la référence du témoin chargé reste l'offre 100 jusqu'à la fusion de l'avenant 1 (EP-08),
  quand les exemples lisent la 101 ; se comparent tels quels les contextes, `is_stored`, le coût
  réel, le reste à engager, les dates des jalons, les formes et les pas des séries, et se prouvent
  sur le témoin les invariants — les sommes des mailles, la projection du chef de projet, l'offre
  refusée, les points du temps/temps — ; un désaccord avec une fixture hors de cette liste se
  tranche par la spécification, la fixture corrigée par un lot d'outil ;
- propre à l'US : tous les parcours des indicateurs étiquetés `@shared` passent contre le service,
  le témoin chargé ; `review.spec.ts`, dont les chiffres sont ceux de la référence 101, garde ses
  assertions de chiffres par `inService` jusqu'à EP-08, l'entrée du guide le disant ; la définition
  de fini est constatée — le marquage échoue si le calcul échoue, les conservés inchangés après un
  import, le cache vidé puis recalculé identique, l'écran identique à l'API — ; les entrées du
  guide qu'EP-07 et EP-09 ont marquées « levées par EP-10 » (les indicateurs, la part des
  indicateurs de `BEFORE_THE_DATA`) sont levées, le guide disant ce que le marquage rejoué conserve
  et ce qu'EP-08, EP-11 et EP-13 y ajoutent ; le statut de cette US est passé `fini` dans le
  fichier — chaque autre US l'est par le lot qui la termine.

**Notes de réalisation.** EP-10 ne charge aucune tranche : la conservation est un effet du
marquage, que le chargeur rejoue par la transaction du worker (`load_marking`) ; les indicateurs
conservés de la 101 existent dès que le worker et le chargeur portent l'extension (US-1670). Le
calculé devient l'attendu, et la spécification arbitre (README, « Le jeu de données de
référence ») ; l'écart de référence est celui qu'EP-07 a décidé (US-1570 : « la référence reste
l'offre 100 jusqu'à la fusion de l'avenant 1 ») et qu'EP-08 lèvera. Le lot de la vérification
d'ensemble attend US-1650/L3 #2416 d'EP-09, dernier lot à écrire la liste des entrées non rejouées
du guide.

**Hors périmètre.** La référence 101, les risques et les provisions (EP-08) ; les révisions
marquées de plus et les trois cents projets (EP-13) ; le portefeuille (EP-11).

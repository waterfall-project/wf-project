# Revue — Chiffrage, devis et reste à engager (EP-07, part « reste à engager » d'EP-09)

Périmètre : `backend/src/waterfall/core/estimate/` (63 fichiers), `api/estimate_lines.py`,
`api/estimate_indicators.py`, `api/remaining_lines.py`, `api/remaining_indicators.py`,
`api/rate_update.py`, `platform/decimals.py`, tests par échantillon. Commit `29785cc`.
Les chemins ci-dessous sont relatifs à `backend/src/waterfall/` sauf mention contraire.

## Synthèse

Le cœur du calcul est solide : `Decimal` partout dans les chemins d'argent (les seuls `float` sont
les cellules écrites dans Excel), un arrondi unique par ligne en `ROUND_HALF_UP` conforme à
`Money`, des parts réparties en fractions exactes dont la dernière absorbe le reliquat (la somme
des parts égale le total, vérifié par calcul), une projection sommée avant arrondi, des parts de
ventilation qui somment à 1. Les exemples chiffrés du Vérif que j'ai rejoués sur les modules purs
(WF-DEV-0020/0030/0040/0050/0070/0080, WF-RAE-0020) donnent les valeurs attendues. Le changement
de taux ne touche que les révisions en cours, sous le verrou de la révision puis de chaque
structure, dans une seule transaction. Les classeurs exportés n'écrivent aucun texte saisi comme
formule (`strings_to_formulas` faux), et openpyxl ne résout pas les entités externes (vérifié).

Ce qui inquiète : (1) la saisie accepte jusqu'à dix décimales pour des grandeurs que la base
garde à deux ou quatre — le montant est calculé sur la valeur saisie, la grandeur est arrondie
par PostgreSQL, et le montant change au premier rechiffrage ; (2) une date de tâche hors de
2000-2100 fait tomber toute écriture de ligne et tout redatage en 500 ; (3) une colonne lue
absente d'un onglet se lit comme des cellules vides, ce qui, au reste à engager, met des restes à
zéro et termine des tâches, ou duplique toutes les lignes ; (4) la base « référence » du plan de
charge et la valeur planifiée lisent les calendriers du jour et non ceux que la référence a
conservés. Le reste est de moindre portée (performance de l'import, cas limites).

Les tests échantillonnés affirment des valeurs précises et citent leur exigence ; les quatre
points ci-dessus n'ont aucun test.

## Constats bloquants

### BCH-01 — Grandeurs saisies à plus de décimales que leur colonne : montant calculé sur la saisie, grandeur arrondie en base

- **Issue** : #3338.
- **Où** : `core/estimate/entries.py:167-176` (`_kept`), `:252-274` (`_figure`), `:323-331`
  (`_scalars`) ; `platform/decimals.py:29,33-43` (borne à dix décimales) ;
  `core/estimate/tables.py:46-49,132-136` (`quantity numeric(14,4)`, `hours numeric(12,2)`,
  `unit_disbursement numeric(14,2)`) ; `core/estimate/writing.py:123-133,250-257` (le produit est
  calculé sur le brouillon, puis la grandeur est écrite telle quelle) ;
  `core/estimate/importing.py:429-432` et `core/estimate/pasting.py:81-87` (aucune borne d'échelle
  à l'import Excel ni au collage) ; `api/nodes.py:559-566` (`_money_of` lit quantité et heures
  sans échelle).
- **Quoi** : une charge à 3-10 décimales, une quantité à 5-10 décimales (API, collage, import
  Excel) ou un débours unitaire à 3-10 décimales (collage et import Excel, où le motif `Money` ne
  joue pas) sont acceptés ; le montant est calculé sur la valeur saisie, mais PostgreSQL arrondit
  la grandeur à l'échelle de la colonne à l'écriture. Le montant conservé ne correspond plus à la
  grandeur conservée.
- **Scénario** : `updateEstimateLine` avec `hours: "7.333"` sur une ligne de quantité 1 au taux
  100,00. `_kept` laisse passer (dix décimales admises), `base_amount` = 733,30 ; la colonne garde
  7,33. La réponse (relue en base) affiche 7,33 h et 733,30. Au premier rechiffrage sans saisie —
  tâche redatée, taux d'inflation modifié, `applyRateUpdate` (`writing.reprice`, qui relit
  `row.hours`) — le montant devient 733,00. Avec quantité 1000, 7,455 h, taux 100 : 745 500,00
  puis 746 000,00, soit 500 d'écart apparu sans aucune saisie (valeurs calculées sur
  `pricing.labour_base_amount`). Même chose pour `quantity: "1.23456"`, pour un débours « 12,345 »
  collé ou importé. Conséquences annexes : le classeur d'origine réimporté présente la ligne
  « modifiée » à chaque import (7,333 ≠ 7,33, `importing.changed_columns`), contre WF-INTF-0100
  (« un second import du même fichier donne un devis identique ») ; le contrat promet pour `Hours`
  « An entry keeps the decimals it was sent with » (`docs/api/components/common.yaml:28-36`).
  L'import du reste à engager, lui, arrondit bien à la colonne (`remaining/analysing.py:163-170`) :
  le défaut est propre à la saisie, au collage et à l'import du devis.
- **Ce que j'ai vérifié** : la chaîne API → `LineEntry` → `judged_line` → `_priced_draft` →
  `change_line` ; aucune quantification ni refus entre la saisie et l'écriture ;
  `exceeds_precision(Decimal("7.333"), 10)` et `(Decimal("1.23456"), 10)` rendent faux (exécuté) ;
  `tests/test_decimal_precision.py:155-235` n'éprouve que onze décimales et plus, et la valeur à
  l'échelle exacte. Non exécuté : l'écriture en base elle-même (l'arrondi d'un `numeric(p,s)` à
  l'affectation est le comportement documenté de PostgreSQL).
- **Proposition** : juger l'échelle de chaque grandeur contre sa colonne (`QUANTITY_SCALE`,
  `HOURS_SCALE`, `DISBURSEMENT_SCALE`, déjà déclarées dans `tables.py`) : refus 422 au champ pour
  l'API et le collage ; pour l'import Excel, le même refus par ligne (ou un arrondi explicite,
  comme les coûts réels l'ont décidé en #2721) — à trancher, le contrat de `Hours` disant
  l'inverse. Tests : charge « 7.333 » refusée (ou arrondie) à la création, à la modification, au
  collage, à l'import ; après un redatage, `base_amount` inchangé ; un classeur importé deux fois
  sans écart avec une charge à trois décimales.
- **Confiance** : confirmé (lecture de bout en bout et calcul pur ; écriture en base non jouée).

## Constats majeurs

### BCH-02 — Une tâche datée hors de 2000-2100 fait répondre 500 à toute écriture de ligne et à tout redatage

- **Issue** : #4439 (EP-35), ouverte le 2026-11-21.
- **Où** : `core/estimate/costing.py:172-187` (`priced` rend l'année de la part la plus lourde,
  sans borne) ; `core/estimate/writing.py:206,257,305` (écriture de `consumption_year`) ;
  `core/estimate/tables.py:104-106` (`ck_estimate_line_consumption_year_bound`, 2000-2100).
- **Quoi** : le planning admet toute date (`core/planning/interface/structures.py:100-112` ne juge
  de `planning_start_on` que le jour ouvré ; l'horizon de quinze ans est relatif au début de la
  première tâche, `core/planning/scheduling/engine.py:252-271`), mais l'année de consommation
  d'une ligne est contrainte en base : la violation remonte en `IntegrityError`, qu'aucune couche
  ne traduit (aucun traitement d'`IntegrityError` dans `api/`), donc 500 au lieu d'un 422.
- **Scénario** : sur une structure qui porte des lignes, le chef de projet saisit un début de
  planning « 1999-01-04 » (ou « 2926-… », faute de frappe sur l'année) par
  `updateCostStructure` : le moteur redate, `reinflate` rechiffre, `consumption_year` = 1999,
  violation, 500. Variante : structure datée en 1999 sans ligne, puis `createNode` d'une ligne :
  500 à chaque tentative, sans motif. `priced` rend bien 1999 et 2101 sur de telles tâches
  (exécuté sur le module pur).
- **Proposition** : refuser dans `priced` (ou à l'entrée du planning) une année hors des bornes
  de `Year` par un 422 `VALUE_OUT_OF_RANGE` portant `minimum`/`maximum`, nommant la tâche — ou
  borner les dates du planning aux années du contrat. Test : début de planning en 1999 sur une
  structure à lignes → 422, rien écrit ; création d'une ligne sous une tâche de 2101 → 422.
- **Confiance** : confirmé par lecture (chemin complet, contrainte en base, absence de
  traduction) ; requête non jouée.

### BCH-03 — Une colonne lue absente d'un onglet se lit comme des cellules vides : restes mis à zéro, tâches terminées, lignes dupliquées

- **Issue** : #4421 (EP-33), ouverte le 2026-11-21.
- **Où** : `core/estimate/excel/reader.py:361-369` et
  `core/estimate/remaining/excel/reader.py:275-285` (le lecteur calcule `missing_headers` et
  `unread_sheets`, « the policy is the analysis' ») ; `core/estimate/importing.py:490-531` et
  `core/estimate/remaining/analysing.py:235-277` (l'analyse ne les lit jamais — `grep` : aucun
  autre emploi dans `src/`) ; `core/estimate/remaining/analysing.py:369` (`typed = … or NOUGHT`).
- **Quoi** : un en-tête lu manquant (colonne supprimée ou renommée) donne des cellules `None`,
  que l'analyse traite comme des cellules effacées. La règle « cellule vide = zéro » de
  WF-INTF-0120 est justifiée par « l'export ne laisse jamais ces cellules vides, et l'effacement
  est volontaire » : elle ne vaut pas pour une colonne absente, que rien ne distingue au compte
  rendu.
- **Scénario** : (a) reste à engager : dans l'onglet d'un sous-projet, l'utilisateur renomme
  « Débours restant » en « Débours restant (€) » ou supprime la colonne. Chaque ligne hors
  main-d'œuvre connue lit 0, diffère de son réestimé, est planifiée à `unit_disbursement` 0 ; les
  tâches dont toutes les lignes tombent à zéro entrent dans `completed_tasks` à la date de la
  revue (`_close`, `:410-461`). Le compte rendu les montre comme des mises à jour ordinaires ;
  confirmé, il termine les tâches. (b) « ID ligne » absent (colonne masquée perdue par un
  outil) : au reste à engager, chaque ligne devient une ligne nouvelle à budgété nul
  (`_create`, `:293-316`) et les lignes existantes restent — le reste à engager double ; au devis,
  toutes les lignes sont recréées et les anciennes supprimées, lignées et budgétés perdus.
  (c) « Quantité » ou « Heures » absent au devis : toutes les lignes passent à 0.
- **Ce que j'ai vérifié** : `at()` rend `None` pour une colonne absente, `read_number(None)` rend
  `(None, True)` ; les tests du lecteur affirment `missing_headers`
  (`tests/test_remaining_excel_read.py:179`, `tests/test_estimate_excel_read.py:366`) mais aucun
  test d'analyse ne l'emploie ; rien dans la Conception d'EP-07/EP-09 ni dans `DECISIONS.md` ne
  décide ce cas (le format « Coûts réels », lui, refuse une colonne exigée absente).
- **Proposition** : refuser le fichier (422 `FILE_FORMAT_UNREADABLE` avec les colonnes
  manquantes, comme les coûts réels) ou rejeter chaque ligne de l'onglet quand manque un en-tête
  dont l'absence change des données : « ID ligne », « Jours restants », « Débours restant » au
  reste à engager ; « ID ligne », « Quantité », « Heures », « Débours unitaire » au devis. Tests :
  un onglet sans « Débours restant » ne met aucun reste à zéro ; un onglet sans « ID ligne » ne
  crée ni ne supprime aucune ligne.
- **Confiance** : confirmé par lecture (le compte rendu montre bien les écarts : le défaut est
  l'absence de signal distinct et l'effet de masse à la confirmation).

### BCH-04 — La base « référence » lit les calendriers du jour, non les images de la révision de référence

- **Issue** : #4441 (EP-35), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec BCH-08.
- **Où** : `core/estimate/workloading.py:234` (`is_stored=False` pour `reference_budget`),
  `:323-325` (`kept_reference` lu seulement si `is_stored`, puis `role_weeks(…, kept)`) ;
  `core/estimate/valuing.py:45-49` (`role_weeks` appelé sans images) ;
  `core/estimate/placing.py:75-91`.
- **Quoi** : la révision de référence est marquée et conserve les calendriers de ses rôles, mais
  le plan de charge sur `reference_budget` et `planned_value` étalent ses lignes sur les
  calendriers du référentiel courant. `is_stored` — une information du contexte, que le contrat
  veut faux pour cette base — sert à tort de condition à la lecture des images. L'en-tête du
  module dit pourtant « The roles, the calendars and the capacities of a marked revision are read
  on its images ».
- **Scénario** : la référence est marquée avec un rôle sur un calendrier du lundi au vendredi.
  Plus tard, l'administrateur passe ce rôle (ou son calendrier) sur quatre jours. Le plan de
  charge « référence » et la valeur planifiée d'une tâche à cheval sur deux mois changent de
  répartition, sans qu'aucune révision n'ait bougé — contre WF-REF-0130 (« le rattachement […] à
  un calendrier […] n'affecte aucune révision marquée ») et WF-DEV-0080 (la valeur planifiée se
  lit « telle que la révision de référence la date »). `marked_remaining`, lui, lit bien les
  images. La valeur planifiée n'a pas encore de route (EP-10 la lira) : le défaut de `valuing`
  faussera les courbes de délai dès leur livraison.
- **Proposition** : lire `kept_reference` dès que la révision lue est marquée (référence
  comprise) et le passer à `role_weeks` dans les deux modules ; garder `is_stored` pour le seul
  contexte. La capacité affichée en regard (du jour ou conservée) reste à dire. Tests : après
  changement du calendrier d'un rôle, le plan `reference_budget` et `planned_value` de la
  référence sont identiques à ceux d'avant.
- **Confiance** : confirmé par lecture ; aucun test ne couvre le cas
  (`tests/test_workload.py`, `tests/test_planned_value.py`).

### BCH-05 — Import du devis : les lignes absentes du fichier sont supprimées une écriture de l'arbre chacune

- **Issue** : #4422 (EP-33), ouverte le 2026-11-21.
- **Où** : `core/estimate/applying.py:88-90` ; `core/planning/interface/nodes.py:802-846`
  (`delete_node` : verrou, lecture de l'arbre, rejeu du moteur, relecture, par appel).
- **Quoi** : l'application supprime les lignes retirées nœud par nœud, chacune dans un cadre
  d'écriture complet, dans la transaction de la tâche qui tient le verrou de la structure. La
  mesure de #2637/#2693 (23 à 29 s pour 4 883 créations) portait sur les créations, faites en une
  seule écriture ; les suppressions n'ont pas été mesurées.
- **Scénario** : un devis construit dans Excel (sans « ID ligne ») est importé, corrigé dans
  Excel, puis réimporté : toutes les lignes sont nouvelles et les N existantes « removed ». Pour
  le devis de PRJ-001, cela fait près de 5 000 rejeux du moteur sur un arbre de 5 000 lignes
  avant la première création ; la tâche dure N fois le coût d'une écriture unitaire, verrou tenu.
- **Proposition** : supprimer les lignes retirées dans la même écriture que `write_lines` (une
  entrée `removed` de `LinesWrite`, un seul rejeu) ; mesurer le réimport d'un devis sans lignée à
  la volumétrie du témoin et le borner par un test de durée.
- **Confiance** : plausible — le coût par suppression est lu dans le code, la durée totale n'est
  pas mesurée.

### BCH-06 — Ouverture d'un import : le classeur entier est décompressé et analysé dans la requête, sous le verrou du projet, sans borne de taille décompressée

- **Issue** : #4419 (EP-33), ouverte le 2026-11-21, avec BEX-03, BRC-02, BRC-03, BEX-05.
- **Où** : `core/estimate/excel/reader.py:186-209` (`check_header`), `:317-331` (`load_sheets`) ;
  `core/estimate/interface/excel.py:50-54,70-76` et
  `core/estimate/interface/remaining_excel.py:49,68-75` (`HEADER_LENGTH = LARGEST_FILE`) ;
  appelant : `core/exchanges/interface/imports.py:437` (verrou du projet) puis `:452`
  (`form.read_header`).
- **Quoi** : `load_workbook(read_only=True)` charge toujours la table des chaînes partagées en
  entier (`openpyxl/reader/excel.py:291`, `read_strings`), avant de lire les deux premières
  lignes. Un `.xlsx` de 10 Mio compressé peut en contenir plusieurs Gio ; l'ouverture se fait
  dans le processus de l'API, verrou du projet tenu (défaut déjà rencontré n° 4 de `python.md`).
  À l'analyse, `load_sheets` matérialise en listes toutes les lignes de tous les onglets, y
  compris ceux que le format ne lit pas, sans plafond de lignes ni de colonnes.
- **Scénario** : un contributeur titulaire d'`estimate.write` dépose un classeur dont
  `sharedStrings.xml` est très répétitif (10 Mio compressés), puis appelle `openImport` : l'API
  décompresse et analyse des Gio en mémoire en tenant le verrou du projet. Sans malveillance : un
  gros classeur ralentit toutes les écritures du projet pendant l'ouverture.
- **Proposition** : avant `load_workbook`, sommer `ZipInfo.file_size` des membres et refuser
  au-delà d'un plafond (422 `FILE_FORMAT_UNREADABLE`) ; lire l'en-tête avant de verrouiller le
  projet (comme #2582 l'a fait pour la préparation de l'application) ; à l'analyse, ne lire que
  les onglets de lignes et borner lignes et colonnes. Test : un zip dont la taille décompressée
  dépasse le plafond est refusé sans être analysé.
- **Confiance** : plausible — chargement des chaînes et appel sous verrou lus dans le code ;
  l'épuisement de mémoire n'a pas été joué, et je n'ai pas cherché de borne en amont dans
  `core/exchanges` (autre relecteur). Vérifié par ailleurs : une entité externe dans
  `sharedStrings.xml` est refusée (`ParseError`, donc `FILE_FORMAT_UNREADABLE`), pas de XXE.

## Constats mineurs

### BCH-07 — Pas de rechiffrage quand le calendrier d'un rôle change sans déplacer la tâche

- **Issue** : #4411 (EP-32), ouverte le 2026-11-21, avec BRC-01.
- **Où** : `core/planning/interface/reference.py:101-103` (`reschedule` sans `Holding.repriced`),
  `core/planning/rescheduling.py:124-130` (seules les tâches déplacées sont rechiffrées) ;
  dépendance côté chiffrage : `core/estimate/costing.py:179` (répartition sur le calendrier du
  rôle).
- **Quoi** : la part d'une ligne par année dépend du calendrier de son rôle ; un changement de
  calendrier qui ne déplace pas la tâche (tâche en mode manuel, ou rôle qui n'est pas celui qui
  borne l'intersection) laisse `reestimated_amount` et `consumption_year` calculés sur l'ancien
  calendrier, jusqu'à la prochaine écriture, où ils changent sans saisie. C'est le défaut n° 7 de
  `python.md` (valeur dérivée recalculée sur un chemin, pas sur les autres).
- **Scénario** : tâche manuelle du 28/12 au 8/01, ligne de 1 000 à 3 % d'inflation, rôle passé de
  cinq jours de 8 h à quatre jours de 10 h : la répartition passe de 40/60 à 50/50, le réestimé
  attendu de 1 018,00 à 1 015,00 ; il reste à 1 018,00.
- **Proposition** : rechiffrer toutes les lignes de main-d'œuvre des structures rejouées par
  `reschedule_current_structures` (passer `Holding(repriced=…)`), ou celles des rôles touchés.
  Test : calendrier d'un rôle modifié, tâche manuelle à cheval sur deux années, montant rechiffré.
- **Confiance** : confirmé par lecture ; effet limité aux tâches à cheval sur deux années.

### BCH-08 — Export du reste à engager d'une révision marquée : coefficient d'inflation au taux courant du projet

- **Issue** : #4441 (EP-35), ouverte le 2026-11-21, avec BCH-04.
- **Où** : `core/estimate/remaining/exporting.py:157,239` ; `core/estimate/costing.py:91-102`
  (`basis_of` lit `project_facts(...).inflation_rate`, « a marked one writes none »).
- **Quoi** : `basis_of`, écrit pour les écritures d'une révision en cours, sert à lire une
  révision marquée : la colonne « Coefficient » de « Tâches » suit le taux d'inflation du jour, non
  celui que la révision a conservé (`revision.inflation_rate`, WF-REV-0030).
- **Scénario** : révision marquée à 3 %, taux du projet passé à 5 %, export du reste à engager de
  la révision marquée : les formules « Main-d'œuvre » du classeur projettent à 5 % des montants
  que Waterfall a conservés à 3 %.
- **Proposition** : pour une révision marquée, lire le taux conservé (l'interface des révisions
  le porte depuis le marquage). Test : export d'une révision marquée après changement du taux,
  coefficient inchangé.
- **Confiance** : confirmé par lecture (les montants de Waterfall dans le fichier restent justes ;
  seules les formules de lecture sont faussées).

### BCH-09 — Collage : l'espace fine insécable (U+202F) des milliers fait refuser le nombre

- **Issue** : #4435 (EP-34), ouverte le 2026-11-21, avec FGR-07.
- **Où** : `core/estimate/pasting.py:81-87`.
- **Quoi** : `_number` retire l'espace et U+00A0, pas U+202F, séparateur de milliers du français
  dans les tableurs et navigateurs récents : « 1 234,56 » est refusé `NUMBER_INVALID` (exécuté :
  `_number("1 234,56")` rend `None`, `"1 234,56"` rend 1234.56).
- **Proposition** : retirer aussi U+202F (et U+2009). Test paramétré sur les trois espaces.
- **Confiance** : confirmé (exécuté sur le module) ; je n'ai pas vérifié si le front normalise
  avant l'envoi.

### BCH-10 — Import : le taux manquant et le débordement de montant ne sont jugés qu'à l'application

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-08 (US-2660/L2, #3827, commits
  `ad1b9e4cf`, `296606006`, `100964315`), `judged` appelle `judged_amounts` après `judged_line` pour
  toute ligne nouvelle ou modifiée : un montant débordé rejette la ligne à l'analyse, et
  `HOURLY_RATE_MISSING` devient un rejet de la ligne au compte rendu, à l'en-tête « Rôle ou
  catégorie », avec `missing_rates`. Un test l'affirme.
- **Où** : `core/estimate/importing.py:456-480` (`judged` appelle `judged_line`, non
  `judged_priced`) ; refus levés à l'application par `core/estimate/writing.py:121-122,131-138`.
- **Quoi** : une ligne de main-d'œuvre dont la catégorie n'a pas de taux pour l'année de la
  révision est « acceptée » au compte rendu ; après confirmation, l'application échoue en entier
  (`HOURLY_RATE_MISSING`), en nommant une seule catégorie — celle de la première ligne
  rencontrée — là où WF-DEV-0010 veut que le refus les énumère. Le cas du débordement est connu
  et testé ainsi (`tests/test_estimate_import_application.py:711`) ; celui du taux n'a aucun test
  d'import.
- **Proposition** : juger le taux à l'analyse et rejeter la ligne au compte rendu, catégories
  nommées. Test : classeur avec un rôle sans taux, ligne rejetée, les autres appliquées.
- **Confiance** : confirmé par lecture.

### BCH-11 — Reste à engager importé en montant : le montant obtenu n'est pas toujours le montant saisi

- **Issue** : #4428 (EP-33), ouverte le 2026-11-21.
- **Où** : `core/estimate/remaining/analysing.py:168-170,384-386`.
- **Quoi** : le débours unitaire est arrondi au centime après division par quantité × coefficient
  (décision de la Conception d'EP-09). La décision #2797 dit pourtant que « le débours d'une
  tâche à cheval sur deux années rend le montant saisi » : ce n'est vrai ni pour une quantité
  autre que 1 (100,00 saisi sur une quantité 3 → 33,33 × 3 = 99,99), ni toujours à quantité 1 dès
  que le coefficient dépasse 1 (coefficient 1,03 : 100,08 saisi → 100,09 ; 12 montants sur 400
  entre 100,00 et 104,00, calculé). Le compte rendu n'annonce pas le montant qui sera écrit.
- **Proposition** : soit ramener la quantité à 1 quand le montant saisi ne se divise pas (option
  écartée par la Conception), soit dire l'écart au compte rendu ; au minimum, corriger le texte de
  la décision. Test : montant saisi, montant réestimé relu.
- **Confiance** : confirmé (calcul sur `unit_disbursement` et `round_to_cent`).

### BCH-12 — Lectures non bornées par la révision

- **Issue** : #4485 (EP-40), ouverte le 2026-11-21, avec DON-02.
- **Où** : `core/estimate/interface/contributors.py:28-49` (`roles_employed`) et `:52-67`
  (`marked_revision_has_lines`) ; `core/estimate/costing.py:139-148` (`reference_rates`, une
  requête par catégorie) ; `core/estimate/indicating.py:175-186`, `core/estimate/keeping.py:115-130`
  (`IN` de plusieurs milliers d'identifiants là où `among()` existe).
- **Quoi** : `roles_employed` et `marked_revision_has_lines` lisent les lignes de toutes les
  révisions du projet (révisions × lignes) pour n'en garder qu'une révision en Python ; la
  seconde sert l'état suivant du projet, lu souvent.
- **Proposition** : filtrer par la révision dans la requête (une fonction de l'interface du
  planning qui rend les lignes d'une révision existe : `lines_of_revision`), `EXISTS` pour la
  question booléenne. Coût faible, gain proportionnel au nombre de révisions.
- **Confiance** : confirmé par lecture ; impact non mesuré.

### BCH-13 — Critères `SOMME.SI.ENS` construits depuis des libellés libres

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — il ne valait que par sa jonction à
  #4317 (EP-08), dont le périmètre ne s'élargit pas : les sous-totaux sont en lecture seule, et le
  nom de nature qui casserait le critère est improbable.
- **Où** : `core/estimate/excel/writer.py:564-572`, `core/estimate/remaining/excel/writer.py:415-419`.
- **Quoi** : le nom d'une nature et un code comptable entrent tels quels (guillemets doublés)
  dans un critère de `SUMIFS` ; un nom qui commence par `<`, `>`, `=` ou contient `*`, `?`, `~`
  est lu par Excel comme un opérateur ou un joker : sous-totaux de la synthèse faux (lecture
  seule, non réimportés ; pas d'exécution de formule).
- **Proposition** : préfixer le critère par `=` et échapper `~`, `*`, `?`. Test d'écriture avec
  une nature « <Divers ».
- **Confiance** : plausible (comportement d'Excel non joué).

## Points forts

- Arrondi : un seul point d'arrondi des montants (`pricing/amounts.py:48-56`), `ROUND_HALF_UP`
  comme `Money` ; `sum_amounts` refuse un montant non arrondi plutôt que de l'arrondir ; la
  répartition (`spreading/spread.py:130-150`) travaille en `Fraction`, la dernière part prend le
  reste : somme des parts = total (rejoué : 1 000,00 → 400 + 600 ; 100,01 → 40,004 + 60,006).
- Exemples du Vérif rejoués et justes : 7 550,00 × 1,0609 = 8 009,80 ; +4,04 % à deux ans et 2 % ;
  part d'une année antérieure non projetée ; 80 h restantes sur deux mois (38,18/41,82 au prorata) ;
  valeur planifiée 0 avant le début, 477,27 à la fin du premier mois, 1 000 à la fin ; jalon
  compté entier à sa date ; parts 0,3333/0,3333/0,3334.
- Indicateurs : division par zéro traitée partout (`no_total`), montant non calculable distinct
  de zéro (`hourly_rate_missing`), marge par sous-projet sommant à celle du projet par
  construction, écart à la revue précédente absent plutôt que nul.
- Changement de taux : révision verrouillée `FOR UPDATE` et compteur vérifié avant toute
  écriture, proposition recalculée sous le verrou, structures verrouillées avant la lecture des
  lignes, une seule transaction, 412 au rejeu ; `reprice_after_rate` ne touche que les révisions
  en cours de l'année, sans taux conservé.
- Excel : textes jamais écrits comme formules ni comme liens, noms d'onglets ramenés aux règles
  d'Excel, en-têtes lus par leur nom, nombre en texte rejeté, lignée en double rejetée des deux
  côtés, application rejugée sous le verrou contre le compte rendu confirmé, tout ou rien.
- Frontières : aucun SQL en texte, planning lu par son interface, aucun commentaire d'exemption
  dans le périmètre ; tests échantillonnés précis (`tests/test_rate_update.py`,
  `tests/examples/*`), chacun citant son exigence et reprenant la phrase du Vérif.

## Couverture

- **Lu en entier** : `core/estimate/` — `pricing/`, `spreading/`, `costing.py`, `valuing.py`,
  `shares.py`, `placing.py`, `entries.py`, `writing.py`, `keeping.py`, `recalling.py`,
  `loading.py`, `repricing.py`, `indicating.py`, `reading.py`, `tables.py`, `applying.py`,
  `importing.py`, `exporting.py`, `pasting.py`, `comparing.py`, `uniting.py`, `workloading.py`,
  `excel/{reader,writer,model,names}.py`, `remaining/{analysing,applying,reviewing,summing,
  balancing,comparing,exporting,kanban}.py`, `remaining/excel/{model,layout,reader}.py`,
  `interface/{facet,rates,lines,indicators,remaining,remaining_indicators,excel,remaining_excel,
  employment,calendars,workload}.py` ; les cinq routes de `api/` ; `platform/decimals.py`.
  Spécification : §3.2.5, FBS-4.4 et FBS-4.5 en entier, annexe B, WF-REV-0030/0060, WF-REF-0130,
  WF-INTF-0080/0100/0110/0120/0130. Conception d'EP-07 jusqu'à « Le worker ».
- **Échantillonné** : `imaging.py` (en-tête, `keep_images`, `_employed`), `interface/__init__.py`
  (en-tête et enregistrements), `interface/contributors.py`, `interface/kanban.py`,
  `remaining/excel/writer.py` (options du classeur et formules seulement) ; côté planning et
  échanges, les seules fonctions appelées (`write_facet`, `delete_node`, `replayed`,
  `reschedule_current_structures`, `open` des imports). Tests : `test_rate_update.py`,
  `test_decimal_precision.py`, `examples/test_pricing_examples.py`,
  `examples/test_estimate_spreading_examples.py` lus ; pour les autres fichiers `test_estimate_*`
  et `test_remaining_*`, les noms des tests et le compte par exigence. Contrat :
  `EstimateLineWrite`/`Update`, `Decimal`/`Money`/`Hours`, `CalculationContext`, `ImportReport`,
  `getEstimateIndicators`, `getRemainingIndicators`. Conception d'EP-09 : « Ce que le cadrage
  décide » (extraits), « Les indicateurs du reste à engager », « Le format Excel du reste à
  engager ». Prototypes `prototype_devis.py` et `prototype_rae.py` : parties de calcul (ils
  emploient `float` et `round`, et leur README dit qu'ils ne font pas foi).
- **Non lu** : `interface/comparison.py` ; la migration `0025`/`0027` ; `estimate_support.py`,
  `remaining_support.py`, les `asked_*.py` ; le corps de la plupart des tests ; les critères
  d'acceptation US par US ; `paths/revisions.yaml` au-delà des schémas cités ; `api/nodes.py`,
  `api/workload.py`, `api/comparison.py` (hors de la liste de la mission, sauf `line_entry` et
  `_money_of`). Aucun test ni outil lourd n'a été lancé ; les vérifications exécutées sont de
  petits calculs sur les modules purs et un essai d'entité externe sur openpyxl, en mémoire.

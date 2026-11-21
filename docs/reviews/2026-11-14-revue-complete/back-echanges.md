# Revue — échanges de fichiers : mécanique commune d'import/export et MS Project (EP-06, EP-07, EP-09, EP-24)

Commit relu : `29785cc`. Préfixe des constats : `BEX`. Tous les chemins sont relatifs à
`/home/user/wf-project`.

## Synthèse

La mécanique commune est soignée : machine à états jugée à la lecture comme à l'écriture par un
seul jugement, verrou de l'import relu sous verrou, tâche du worker dans une seule transaction avec
trace d'échec (`UndoneError`), double application fermée (verrou de ligne + `task_id`), purge qui ne
supprime qu'après validation, analyseur XML durci (XXE, entités, DTD : vérifié par exécution),
`Content-Disposition` assaini, clés de stockage engendrées par le serveur, fichier d'export lisible
par son seul demandeur. Les tests du périmètre affirment réellement (états, fichiers, refus).

Ce qui inquiète :

- **le rapprochement des tâches à la réimportation MS Project** (BEX-01) : une tâche ajoutée dans
  MS Project peut prendre le nœud — donc les lignes de devis, l'état et la lignée — d'une tâche
  existante, parce que le repli par `external_id` est consulté avant que les lignées aient toutes
  été servies, et que l'export numérote ses `UID` dans un autre espace que les `external_id` gardés ;
- **le compte rendu confirmé n'est pas ce qui s'applique** pour un planning (BEX-02) : le plan est
  reconstruit à l'application sans rien comparer au compte rendu, alors que la fusion et le collage
  portent un compteur pour cela ;
- **aucune borne de décompression des classeurs** (BEX-03) : un `.xlsx` de 68 Ko fait tenir 64 Mo
  en mémoire à `openImport` (mesuré) ; 10 Mio en donnent ~10 Gio, dans le processus de l'API.

Le reste est mineur : un écouteur `after_commit` qui part à la libération du point de sauvegarde
du worker, l'en-tête d'un classeur analysé sous le verrou du projet, un dépôt de sauvegarde que la
purge ne protège pas pendant sa restauration, un 500 sur un import du témoin, des entrées hostiles
qui finissent en `INTERNAL_ERROR`.

## Constats bloquants

### BEX-01 — Réimport MS Project : une tâche nouvelle peut s'approprier le nœud d'une tâche existante

- **Issue** : #3337.
- **Où** : `backend/src/waterfall/core/planning/importing.py:260-280` (`_matched`, boucle unique
  lignes 270-279) ; l'espace des `UID` de l'export : `core/planning/exporting.py:194`
  (`UID` = rang 1..n) ; l'`external_id` gardé : `core/planning/applying.py:166` (`UID` du fichier
  d'origine, jamais récrit pour une tâche rapprochée).
- **Quoi** : le rapprochement se fait en une seule passe dans l'ordre du fichier ; une ligne sans
  lignée (tâche créée dans MS Project) est rapprochée par `by_external[str(uid)]` d'une tâche de la
  structure qu'une ligne *ultérieure* du fichier désigne pourtant par sa lignée. Or les `UID` d'un
  fichier exporté (rangs 1..n) n'ont aucun rapport avec les `external_id` de la structure (`UID` du
  fichier MS Project d'origine) : la collision est fortuite, pas un rapprochement.
- **Scénario** (exécuté sur `_matched` avec un arbre factice) : une structure importée d'un fichier
  MS Project dont les `UID` ont des trous (1, 2, 3, 5, 8, 9, 12 — courant : MS Project ne réemploie
  jamais un `UID` supprimé ; ou des tâches supprimées depuis dans Waterfall). Export : `UID` 1..7 et
  lignées. Dans MS Project, l'utilisateur insère une tâche après la ligne 2 : elle reçoit le `UID`
  suivant, 8, sans lignée. Réimport : la ligne 3 « NEW TASK » (uid 8) est rapprochée de T5
  (`external_id` "8") ; la ligne de T5, qui porte la lignée de T5, trouve son nœud « pris », retombe
  sur `by_external["5"]` (T4, déjà prise) et est **créée**. Résultat appliqué : « NEW TASK » hérite
  de la lignée, des lignes de devis, de l'état d'avancement, du rattachement et des inscriptions de
  T5 ; T5 est un nœud neuf, sans ligne. Le compte rendu le montre comme « T5 mise à jour (libellé…) »
  et « T5 ajoutée », rien ne signale l'échange. Si la ligne retombée trouve un `external_id` libre,
  elle vole à son tour une autre tâche (cascade). Contredit le Vérif de WF-INTF-0040 (« Un planning
  exporté, retravaillé dans MS Project puis réimporté conserve les lignes de devis et les lignées de
  ses tâches »), clos par EP-06/EP-07.
- **Ce que j'ai vérifié** : aucun garde en aval (`plan_import`, `apply_plan`) ; le test
  `tests/test_msproject_import.py:508` rapproche par `GUID` puis par `UID` sans collision ; le test
  qui cite « retravaillé » (`tests/test_estimate_export.py:586`) réimporte un fichier **non
  modifié**. Non vérifié : la numérotation des `UID` par MS Project lui-même pour une tâche ajoutée
  à un fichier ouvert depuis l'XML (hypothèse : plus grand `UID` + 1, son comportement documenté).
- **Proposition** : deux passes — d'abord toutes les lignes qui portent une lignée connue, puis,
  pour les lignes restantes, le repli par `external_id` parmi les tâches non prises ; et ne pas
  replier par `external_id` une ligne sans lignée d'un fichier qui déclare le champ des lignées
  (`_lineage_field` non nul : c'est un export de Waterfall, dont les `UID` sont des rangs) — ou faire
  écrire à l'export `UID = external_id` quand la tâche en a un. Test : le scénario ci-dessus contre
  le service, avec des lignes de devis sous T5, qui affirme que T5 garde lignée et lignes et que la
  tâche nouvelle est « added ».
- **Confiance** : confirmé pour la logique (exécutée) ; plausible pour la fréquence, qui dépend de
  la numérotation de MS Project.

## Constats majeurs

### BEX-02 — Planning : ce qui s'applique n'est pas le compte rendu confirmé, et rien ne le compare

- **Issue** : #4420 (EP-33), ouverte le 2026-11-21, avec CTB-01.
- **Où** : `core/planning/interface/msproject.py:100-117` (`del report`, ligne 113 ; plan refait
  ligne 116) ; `core/planning/importing.py:599-602` (tâches absentes → `removed`) ;
  `core/planning/applying.py:137-138` (suppression, lignes de devis en cascade) ;
  `core/exchanges/running.py:210` ; aucune version de structure dans `import_report`
  (`core/exchanges/tables.py`).
- **Quoi** : l'application reconstruit le plan sous verrou depuis le fichier et l'état courant de
  la structure, ne rejuge que les `refusals`, et écrit — sans comparer au compte rendu que
  l'utilisateur a lu jusqu'à vingt-quatre heures plus tôt. Le contrat dit pourtant « the confirmed
  report is what applies (WF-INTF-0080) » (`docs/api/paths/exchanges.yaml:480-482`).
- **Scénario** : A analyse un planning à 9 h (compte rendu : 3 mises à jour, aucune suppression).
  À 9 h 30, B crée dans la grille la tâche X, non démarrée, et trois lignes de devis dessous (rien
  ne l'interdit : l'analyse ne nomme pas le projet). À 10 h, A confirme : X, absente du fichier,
  est supprimée avec ses lignes (WF-INTF-0090), le compte rendu conservé ne la mentionne pas, et
  l'historique annulable ne reçoit rien (WF-IHM-0110). Variante : un libellé modifié depuis est
  écrasé par celui du fichier alors que le compte rendu le disait « inchangé ». Variante :
  `setImportDurationRule` après le marquage de la révision réanalyse contre la structure de la
  révision marquée (`interface/imports.py:732-737`).
- **Ce que j'ai vérifié** : la décision de la fusion écarte explicitement ce cas (« confirmer sans
  compteur […] aurait appliqué un compte rendu périmé », `docs/api/DECISIONS.md:6058-6081`), et le
  collage porte `structure_lock_version` (EP-06, table `paste_plan`) ; pour l'import, la décision
  ne couvre que les refus (`DECISIONS.md:6096-6098`). `ImportApply` ne porte que `confirmed`. Le
  test `test_msproject_import.py:643` n'éprouve qu'un refus né depuis l'analyse. Les formats du
  devis et des coûts reçoivent, eux, le compte rendu (`estimate/interface/excel.py:114`,
  `costs/interface/actual_costs.py:130`) — hors de mon périmètre, à vérifier par leurs relecteurs.
- **Proposition** : garder à l'analyse le compteur de la structure lue (dans `import_report`), le
  comparer sous le verrou à l'application, et faire échouer l'import sur un motif nommé quand il a
  changé (ou, à moindre coût de contrat : recalculer `report_of` sous verrou et échouer si
  `differences`/`rejected` diffèrent du compte rendu gardé). Test : une tâche créée entre l'analyse
  et la confirmation n'est pas supprimée, l'import échoue en le disant. C'est une modification de
  conception (et peut-être du contrat) : à trancher par l'auteur.
- **Confiance** : confirmé (chemin lu de bout en bout).

### BEX-03 — Classeurs téléversés : aucune borne de décompression (bombe zip), dès `openImport`, dans l'API

- **Issue** : #4419 (EP-33), ouverte le 2026-11-21, avec BRC-02, BCH-06, BRC-03, BEX-05.
- **Où** : mécanique commune : `core/exchanges/interface/imports.py:452` (`form.read_header`, appelé
  par la requête) et `core/exchanges/interface/damages.py` (seul outil commun des classeurs, sans
  borne) ; sites d'ouverture, tenus par d'autres relecteurs : `core/estimate/excel/reader.py:199`
  et `:325`, `core/costs/extraction.py:100` et `:105` (`list(iter_rows(...))` sans borne de
  lignes) ; `HEADER_LENGTH = LARGEST_FILE` (`core/estimate/interface/excel.py:54`,
  `core/costs/interface/actual_costs.py:46`).
- **Quoi** : `load_workbook(BytesIO(content), read_only=True)` lit en entier, sans plafond, des
  membres du zip (`xl/theme/theme1.xml` par `archive.read`, `workbook.xml`, `styles.xml`, toutes
  les chaînes partagées en liste) : la borne de 10 Mio porte sur le fichier compressé seulement.
  `defusedxml` n'est pas installé ; les analyseurs XML d'openpyxl ne résolvent pas d'entité, le
  défaut est la décompression.
- **Scénario** (mesuré) : un classeur de **68 515 octets** dont `theme1.xml` contient 64 Mio
  d'espaces ; `load_workbook` tient 64 Mio (`ru_maxrss` +65 Mo) et `check_header` le charge avant
  de le refuser. À 10 Mio de fichier, ~10 Gio. Un contributeur portant `estimate.write`,
  `remaining.write` ou `actual_costs.write` dépose le fichier puis appelle `openImport` : le
  processus de l'API est tué par manque de mémoire (toutes les requêtes en cours avec lui), et ce
  sous le verrou du projet (BEX-05) ; l'analyse dans le worker le tuerait de même, trois tentatives
  de suite.
- **Proposition** : un ouvreur commun dans `core/exchanges/interface` (comme `hardened_parser`
  pour l'XML) qui lit `zipfile.ZipFile(...).infolist()`, refuse par `FILE_FORMAT_UNREADABLE` un
  classeur dont la somme des `file_size` déclarés ou le nombre de membres passe une borne (zipfile
  ne lit jamais plus que `file_size`), puis seulement appelle `load_workbook` ; une borne de lignes
  dans `sheet_rows`/`read_workbook`. Test : le classeur ci-dessus est refusé à l'ouverture sans que
  la mémoire du processus ne monte.
- **Confiance** : confirmé (exécuté à 64 Mio ; l'extrapolation à 10 Gio suit le taux de deflate).

## Constats mineurs

### BEX-04 — Le fichier d'un import appliqué est supprimé avant la validation de la tâche, et sous ses verrous

- **Issue** : #4476 (EP-39), ouverte le 2026-11-21, avec BSO-04.
- **Où** : `core/exchanges/records.py:73-86` (`event.listen(session, "after_commit", …, once=True)`),
  appelé par `core/exchanges/running.py:219`, dans le point de sauvegarde de
  `worker/runner.py:267`.
- **Quoi** : SQLAlchemy (2.1.8, `orm/session.py:1414-1422`) émet `after_commit` aussi à la
  libération d'un point de sauvegarde. L'écouteur, inscrit dans le `begin_nested()` du worker, part
  donc à la sortie du gestionnaire : avant `end()` et avant le COMMIT de la tâche, et même si
  celui-ci échoue (vérifié sur SQLite : l'écouteur a tourné, la transaction englobante a été
  annulée). Contraire à la docstring du module (« once the transaction that ends it is committed,
  never before »). Deuxième effet : l'appel au stockage se fait tous verrous tenus (import,
  révision, projet, structure) ; un stockage lent ou muet (5 s + 60 s, trois essais) retient
  d'autant toute écriture du projet.
- **Scénario** : le worker est arrêté, ou la base coupée, entre la libération du point de
  sauvegarde et le COMMIT : l'import reste `applying`, sa tâche est reprise, le fichier n'est plus
  là, l'import finit `failed` — l'utilisateur doit redéposer.
- **Proposition** : employer la forme que `worker/identity_sync.py:273-300` a déjà écrite
  (n'agir que hors de tout point de sauvegarde, et pas si la transaction d'inscription est
  annulée), la remonter dans `platform/database.py`, et l'employer aussi pour le dépôt en file de
  `platform/tasks.py:181`, qui a le même défaut latent. Test : un `commit` qui échoue après une
  application laisse l'objet sur le stockage.
- **Confiance** : confirmé (mécanisme exécuté ; fenêtre étroite).

### BEX-05 — L'en-tête d'un classeur est analysé sous le verrou du projet (défaut n° 4 de python.md)

- **Issue** : #4419 (EP-33), ouverte le 2026-11-21, avec BEX-03, BRC-02, BCH-06, BRC-03.
- **Où** : `core/exchanges/interface/imports.py:437` (`lock_project`) puis `:452`
  (`form.read_header(session, head)`).
- **Quoi** : la lecture du stockage a été sortie de la transaction, pas l'analyse : pour les trois
  formats Excel, `read_header` ouvre le classeur entier (jusqu'à 10 Mio : styles, chaînes
  partagées) sous `FOR UPDATE` du projet et du dépôt. Sans effet pour MS Project (une expression
  régulière sur 4 Kio).
- **Scénario** : l'ouverture d'un devis de 10 Mio retient plusieurs secondes toute écriture qui
  verrouille le projet (marquage, application d'un import, transitions) ; avec BEX-03, sans borne.
- **Proposition** : donner au format une étape pure hors verrou (`parse_header(head)`, comme
  `prepare` pour l'application, #2582), jugée ensuite sous le verrou ; l'extraction des coûts ne lit
  la correspondance qu'au jugement. Test : comme `test_imports_application.py:456`, pour
  l'ouverture.
- **Confiance** : confirmé.

### BEX-06 — La purge supprime le dépôt d'une sauvegarde qu'une restauration acceptée désigne

- **Issue** : #4471 (EP-39), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec BSO-01.
- **Où** : `core/exchanges/interface/purge.py:177-203` (`_deposits_expired`) ; promesse :
  `docs/api/components/schemas/exchanges.yaml:10-13` et `:25-27` (« kept until the end of its
  task, even beyond `expires_at` »).
- **Quoi** : tout dépôt échu est supprimé, objet compris, sauf celui qu'un import garde ; rien
  n'épargne celui qu'une tâche `restore` en file ou en cours nomme (`api/restores.py:89-100` ne
  repousse pas `expires_at`).
- **Scénario** : une sauvegarde de plusieurs Gio déposée par morceaux, restauration demandée peu
  avant la 24ᵉ heure ; la purge passe pendant le téléchargement de l'archive
  (`restore/task.py:103`) ou avant une nouvelle tentative : l'objet disparaît, la restauration
  échoue (404).
- **Proposition** : épargner dans `_deposits_expired` et `_named_uploads` les dépôts qu'une tâche
  `restore` non finie nomme dans sa charge (`upload_id`). Test dans `test_purge.py`.
- **Confiance** : confirmé à la lecture ; fenêtre étroite.

### BEX-07 — `getImport` répond 500 sur un import sans tâche (ceux du témoin)

- **Issue** : #4425 (EP-33), ouverte le 2026-11-21, avec BEX-10, BEX-11, DON-05, FCO-06.
- **Où** : `backend/src/waterfall/api/imports.py:238` (`session.get_one(BackgroundTask,
  view.task_id)`) ; `core/exchanges/interface/loading.py:91` (`task_id=None`).
- **Quoi** : `get_one` avec une clé nulle lève `NoResultFound` (vérifié), qu'aucun gestionnaire ne
  traduit ; le contrat exige `ImportDetail.task` non nul.
- **Scénario** : sur une plateforme qui porte le témoin (service, e2e), ouvrir depuis le journal
  des imports le compte rendu d'un des imports chargés (`?import=<id>`, `shown-import.ts`) : 500.
- **Proposition** : faire écrire par `load_import` une tâche terminée (ce que le contrat suppose),
  ou rendre la tâche facultative au contrat ; test : `getImport` de chaque import du témoin.
- **Confiance** : confirmé (témoin seulement).

### BEX-08 — Des valeurs hostiles sortent du lecteur en exception brute : `INTERNAL_ERROR` au lieu du refus du format

- **Issue** : #4426 (EP-33), ouverte le 2026-11-21, avec BEX-09, BEX-14.
- **Où** : `core/planning/msproject/reader.py:178-189` (`<Duration>PT999…H` → `OverflowError`,
  exécuté) ; `core/planning/importing.py:523-528` (un plan de ≥ 1 000 niveaux d'`OutlineLevel` →
  `RecursionError` du moteur, exécuté ; seules deux exceptions sont traduites) ;
  `core/planning/applying.py:166` (un `UID` de plus de 200 chiffres passe l'analyse et viole
  `external_id_length` à l'application) ; `api/imports.py:158` et
  `core/exchanges/interface/imports.py:330-334` (un nom de fichier portant un octet NUL passe
  `judge_deposit` et fait échouer l'insertion : 500 — le corps JSON est protégé par `Text`, #2891,
  pas le nom d'un fichier multipart).
- **Quoi** : l'import finit `failed` avec `INTERNAL_ERROR` (ou l'application échoue après un compte
  rendu accepté), là où le format promet `FILE_FORMAT_UNREADABLE`. Aucune écriture, aucun blocage.
- **Proposition** : borner dans le lecteur (chiffres d'un entier, durée, profondeur) et lever
  `UnreadableProjectError` ; refuser le NUL dans `judge_deposit` (422 `/file`). Tests unitaires du
  lecteur, un par valeur.
- **Confiance** : confirmé pour les trois premiers (exécutés ou lus) ; plausible pour le NUL (non
  exécuté contre PostgreSQL).

### BEX-09 — Une tâche manuelle devient automatique, sans signal, quand le fichier ne nomme pas le calendrier de son projet

- **Issue** : #4426 (EP-33), ouverte le 2026-11-21, avec BEX-08, BEX-14.
- **Où** : `core/planning/msproject/translation.py:181-186` (`calendar_of` rend `None` sans
  `CalendarUID`, alors que la docstring du module, lignes 16-18, et `calendar_gap.py:68-76` prennent
  le calendrier « Standard » de MS Project) ; `core/planning/importing.py:392-394` et `:429-430`.
- **Quoi** : sans calendrier résolu, `file_dates` est nul : une tâche manuelle ou à contrainte de
  date est importée automatique, sans `signals`, et `date_mismatches` ne compare rien (le compte
  rendu se lit « aucun écart »).
- **Scénario** : un MSPDI écrit par un autre outil que MS Project (sans `CalendarUID` de projet, ou
  qui nomme un calendrier absent du fichier). MS Project lui-même écrit toujours les deux.
- **Proposition** : replier sur `STANDARD` dans `calendar_of`, comme l'écart de calendrier ; test :
  un fichier sans `Calendars` garde sa tâche manuelle à ses dates. De même, une tâche inactive
  (`<Active>0</Active>`, MS Project 2010+) est importée comme une tâche vivante, sans signal — à
  faire dire par `ignored` (plausible, non éprouvé sur un fichier réel).
- **Confiance** : confirmé à la lecture ; portée faible.

### BEX-10 — Requêtes non bornées de la purge et de la liste des imports

- **Issue** : #4425 (EP-33), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec BEX-07, BEX-11, DON-05, FCO-06.
- **Où** : `core/exchanges/interface/purge.py:156-174` (`_exports_old` : tous les exports réussis
  de plus d'un jour, déjà consommés compris, chargés et verrouillés `FOR UPDATE` toutes les dix
  minutes) ; `core/exchanges/interface/imports.py:571-578` (`list_imports` charge le `report`
  JSONB de chaque ligne, que `_listed` ne rend pas ; jusqu'à 500 lignes).
- **Quoi** : la première croît avec chaque export jamais fait, tant qu'aucune purge ne retire les
  tâches de fond (EP-13) ; la seconde lit des comptes rendus de plusieurs centaines de Ko pour rien.
- **Proposition** : ajouter à `_exports_old` le filtre que `_named_exports` emploie déjà
  (`result["consumed"]` distinct de `true`) ; différer la colonne `report` dans la liste.
- **Confiance** : confirmé.

### BEX-11 — Un compte rendu d'import n'est jamais supprimé, contre §4.4.1 et la docstring de sa table

- **Issue** : #4425 (EP-33), ouverte le 2026-11-21, avec BEX-07, BEX-10, DON-05, FCO-06.
- **Où** : `core/exchanges/tables.py:8-10` (« It is deleted at its expiry or its abandonment ») ;
  `core/exchanges/interface/purge.py:132-153` (passe `expired`/`failed`, ne supprime rien) ; spec
  §4.4.1, ligne 3984 (« un compte rendu d'import [se supprime physiquement] à son expiration ou à
  l'abandon de l'import »).
- **Quoi** : le contrat, qui fait foi, liste les imports expirés et abandonnés (`listImports`,
  `imports.json`) et le témoin charge un import `expired` avec son compte rendu ; la spécification
  et la docstring disent l'inverse, et la table croît sans borne, comptes rendus compris.
- **Proposition** : une « Specification finding » pour accorder §4.4.1 au contrat (ou vider
  `report` à l'expiration et à l'abandon), et corriger la docstring.
- **Confiance** : confirmé (incohérence de textes ; aucun effet fonctionnel aujourd'hui).

### BEX-12 — Les routes des imports gardées par `planning.read`, quel que soit le genre — déjà connu (#2473, EP-08)

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-08 (commit `1b644a73b`, #2473
  fermée le 2026-11-18), les routes ne gardent que la visibilité du projet et le genre est jugé par
  les échanges : `read_import` rend 404 pour un genre que l'appelant ne consulte pas, `list_imports`
  ne liste et ne compte que les genres lisibles. La face de lecture ajoutée par la revue est donc
  fermée aussi.
- **Où** : `backend/src/waterfall/api/imports.py:84-94` ; `backend/tests/asked_imports.py`.
- **Quoi** : connu pour l'écriture (importer un devis ou des coûts réels demande `planning.read`).
  J'ajoute la face de lecture, que l'issue ne dit pas : un rôle composé avec `planning.read` seul
  lit par `listImports`/`getImport` les comptes rendus des devis et des extractions de coûts
  (libellés de lignes, numéros de pièces, colonnes conservées), alors que `listCostImports` exige
  `actual_costs.read` (`api/cost_imports.py:25`). Pas de montant dans ces comptes rendus.
- **Confiance** : confirmé.

### BEX-13 — Une panne passagère du stockage fait échouer l'import pour de bon

- **Issue** : #4427 (EP-33), ouverte le 2026-11-21.
- **Où** : `core/exchanges/running.py:136-142` et `:192-197` (`except Exception` autour de
  `_content`) ; `platform/storage.py:212-219` (les erreurs de lecture en cours de flux échappent à
  `reached()` et sortent brutes).
- **Quoi** : un 503 du stockage pendant l'analyse ou l'application passe l'import `failed`, fichier
  à supprimer : un import confirmé est perdu pour une coupure de quelques secondes, alors que les
  trois tentatives de la tâche existent pour cela. La conception le décide pour une « exception
  typée » du format, pas pour une indisponibilité.
- **Proposition** : laisser remonter `UnavailableError` sans trace (la tâche est reprise), et
  n'échouer l'import que sur `MissingObjectError` ou un refus du format.
- **Confiance** : confirmé à la lecture.

### BEX-14 — Aucune borne au nombre de tâches ni à la profondeur qu'un planning importé crée

- **Issue** : #4426 (EP-33), ouverte le 2026-11-21, avec BEX-08, BEX-09.
- **Où** : `core/planning/msproject/reader.py:62-79`, `core/planning/importing.py:586-646`.
- **Quoi** : mesuré : un MSPDI de 6,6 Mio de 90 000 tâches emboîtées est lu en 2,5 s pour 355 Mo
  de mémoire (≈ 55 fois le fichier), et seule la récursion du moteur l'arrête (BEX-08) ; à plat,
  ~190 000 tâches tiennent dans 10 Mio, passent l'analyse (moteur linéaire, mesuré) et seraient
  appliquées, pour un volume prévu de mille tâches par projet (§4.6.2). Le compte rendu, rendu
  entier par `getImport`, grossit d'autant.
- **Proposition** : une borne de tâches dans le lecteur ou un motif de `refusals`, à fixer par
  l'auteur (la spécification n'en donne pas).
- **Confiance** : confirmé (mesures sur les fonctions pures).

### BEX-15 — La date « Calculé le » de l'image de l'arborescence ne passe pas par `current_day`

- **Issue** : #4416 (EP-32), ouverte le 2026-11-21.
- **Où** : `core/planning/interface/task_tree.py:95` (`facts.scheduled_at.date()`).
- **Quoi** : le jour est celui du temps universel, lu sans `current_day` de l'interface des
  projets : quand US-2200 donnera son fuseau à l'installation, ce site ne suivra pas. Déjà connu
  pour la règle (#2527, US-2200 d'EP-25) ; ce site-ci n'y est pas nommé.
- **Confiance** : confirmé.

## Points forts

- **XML** : un seul analyseur (`core/exchanges/interface/xml.py`), aucune autre construction de
  parseur dans `backend/src` ; exécuté : entité interne et externe non résolues, « billion laughs »
  refusé (libxml2 2.14.6), et un `DOCTYPE` ne passe pas `recognised` (`msproject/header.py`), dont
  l'expression régulière est possessive et linéaire. Test d'XXE présent (`test_msproject.py:747`).
- **Chemins et en-têtes** : clés `uploads/<uuid>` et `exports/<task_id><suffixe>` engendrées par le
  serveur ; le nom du fichier déposé n'entre dans aucune clé ; `disposition` neutralise CR/LF,
  guillemet et barre inverse, et encode `filename*` (`test_exports.py:359`). Le type réel est jugé
  par le format, jamais par l'extension. Dépôt borné à la lecture, avec ou sans `Content-Length`.
- **Machine à états** : un jugement unique pour la lecture, les commandes et les refus
  (`states.py`) ; contrainte `expires_at_when_analysed` en base ; double application fermée par le
  verrou de ligne et le `task_id` (`test_imports_application.py:563`) ; abandon pendant l'analyse
  gagnant ; reprise après arrêt du worker sans rien d'écrit ; refus définitif contre condition
  passagère (`PASSING`) tenu, la course avec le marquage fermée par le verrou du projet des deux
  côtés.
- **Exports** : tâche lue par son seul demandeur (404 sinon), permission du genre jugée par la
  commande `export_*`, lecture figée (`REPEATABLE READ`), fichier supprimé après le dernier octet,
  téléchargement interrompu repris. Formules : `strings_to_formulas` et `strings_to_urls` coupés
  dans l'écrivain du devis (`estimate/excel/writer.py:757-758`).
- **Police** : DejaVu Sans déclarée dans `REUSE.toml` (Bitstream-Vera), licence dans `LICENSES/`.
- **Purge** : liste avant le verrou, suppression après validation, balayage borné qui passe les
  objets nommés, course avec l'ouverture d'un import fermée par `FOR UPDATE`.
- Aucun commentaire d'exemption, aucun SQL en texte dans le périmètre ; `core/exchanges` ne lit
  que ses tables et celles de la plateforme.

## Couverture

- **Lu en entier** : `backend/src/waterfall/core/exchanges/` (tous les `.py`) ;
  `core/planning/msproject/` (six fichiers), `importing.py`, `applying.py`, `exporting.py`,
  `calendar_gap.py`, `task_tree_image.py`, `interface/msproject.py`, `interface/task_tree.py` ;
  `api/imports.py`, `exports.py`, `cost_imports.py`, `uploads.py`, `tasks.py` ;
  `worker/exchanges.py`, `runner.py`, `marking.py` ; `platform/uploads.py`, `platform/storage.py` ;
  `docs/dev/python.md`, `sql.md`, les sections demandées d'`agents.md` et du guide ;
  `docs/api/paths/exchanges.yaml` (imports, exports, dépôt) ; spec §3.1.4 (WF-INTF-0040 à 0140),
  WF-ARC-0100, §4.4.3, §4.4.4 ; Conception d'EP-06 (cadrage, tables, import en deux temps, format
  MS Project, exports, purge, API, worker) et US-1430.
- **Échantillonné** : `docs/api/components/schemas/exchanges.yaml` (`FileUpload`, `ImportDetail`,
  `ImportApply`, `ExportRequest`) ; `docs/api/DECISIONS.md` (fusion, fichier rejeté entier) ; tests
  `test_msproject_import.py`, `test_msproject_export.py`, `test_estimate_export.py` (aller-retour),
  `test_imports.py`, `test_imports_application.py`, `test_exports.py`, `test_purge.py` (noms de tous
  les tests, corps d'une dizaine) ; `worker/main.py` (verbe `purge`) ; `restore/task.py`,
  `api/restores.py` (pour le dépôt restauré) ; `core/estimate/excel/reader.py`,
  `core/costs/extraction.py`, `core/estimate/interface/excel.py`,
  `core/costs/interface/actual_costs.py` (ouverture des classeurs seulement) ; EP-24 (US-1990,
  US-2000, titres et critères) ; `docs/roadmap/EP-08` (constats reçus).
- **Non lu** : `core/planning/reading.py`, `views.py`, `interface/__init__.py` (hors périmètre
  réel : le `grep` ne les retenait que pour un mot) ; `test_msproject.py`, `test_msproject_corpus.py`,
  `test_msproject_calendar_gap.py`, `test_task_tree_*.py`, `test_worker*.py`, `test_uploads.py`,
  `imports_trial.py`, `backend/tests/examples/` ; les Conceptions d'EP-07 et d'EP-09 pour leurs
  échanges (lues par recherche de mots seulement) ; l'annexe B ; le front. Le moteur de dates
  (`scheduling.py`) n'a été qu'exécuté, pas relu. Aucune recette dans MS Project réel.
- **Sondes** : quelques scripts `python3` sur les fonctions pures (lecteur MSPDI, `_matched`,
  moteur, openpyxl, SQLAlchemy sur SQLite en mémoire), sans base ni réseau ; ils n'ont rien écrit de
  versionné, mais ont pu laisser des `__pycache__` (ignorés par git) sous `backend/src`.

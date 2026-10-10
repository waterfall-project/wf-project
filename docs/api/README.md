# Contrat d'interface de Waterfall

Ce répertoire porte le contrat OpenAPI de l'API de Waterfall. Il est **écrit à la main et
fait foi** : tout endpoint, tout schéma et toute erreur qu'un client peut rencontrer y
figurent, le client du front en est engendré, et la chaîne rejette une version des
services dont une réponse s'en écarte (WF-ARC-0060, annexe C de la spécification).

La spécification est dans `../spec`. Chaque opération cite dans ses propres mots — résumé
ou description — les exigences qu'elle réalise : c'est ce qui rend la traçabilité vérifiable
dans les deux sens, et `make inventory` échoue sur une opération qui n'en cite aucune. Il échoue
aussi, avant d'écrire, sur un fichier de `paths/` dont il ne déclare pas la famille, ou une famille
déclarée sans fichier : une famille nouvelle se déclare dans `tools/inventory.py`, sous son titre,
pour que ses opérations n'échappent pas à ce contrôle (#538).

## Organisation

| Chemin | Contenu |
|---|---|
| `openapi.yaml` | racine : information, serveurs, étiquettes, sécurité, et un renvoi par chemin |
| `paths/<famille>.yaml` | les opérations, une famille par fichier |
| `components/common.yaml` | types élémentaires, enveloppe d'erreur, référence de tâche de fond |
| `components/parameters.yaml` | paramètres partagés |
| `components/responses.yaml` | réponses d'erreur partagées |
| `components/schemas/<famille>.yaml` | schémas, plusieurs par fichier |
| `INVENTORY.md` | inventaire des endpoints et couverture des exigences, régénérable |

Les schémas sont groupés par famille plutôt qu'un fichier par schéma : autant de
fichiers d'une douzaine de lignes que de schémas se reliraient moins bien que la douzaine
de fichiers cohérents que voici.

## Conventions

Chacune est dictée par une exigence, et aucune ne se discute au cas par cas.

| Convention | Exigence |
|---|---|
| Identifiants UUID engendrés par le serveur, jamais séquentiels dans une URL | WF-DAT-0060 |
| `snake_case` pour les chemins, les champs et les paramètres | — |
| `camelCase` pour l'`operationId`, qui devient un nom de méthode dans les clients générés | `listProjects` |
| Les noms du tableau de correspondance du §4.4.1 : `estimate_line` est une ligne de devis, `cost_line` une ligne de coût réel | §4.4.1 |
| Décimaux exacts transportés en chaîne, dates de planning sans heure, début et fin d'une tâche en date et heures de travail écoulées (`WorkInstant`), horodatages en temps universel | WF-DAT-0100 |
| Une part, un avancement ou un taux calculé — le rapport de deux grandeurs : la part d'une répartition (`share`), les avancements, la consommation du budget, le taux de charge (`load_ratio`), le taux de transformation (`conversion_rate`) — est un décimal exact donné à quatre décimales, le centième de pour cent, arrondi au plus proche, une demie s'éloignant de zéro ; une valeur non nulle n'est jamais donnée nulle : celle que quatre décimales rendraient nulle est donnée à son premier chiffre significatif, arrondi de même — 0,0000309 est donnée `0.00003`, 0,99996 est donnée `1`. Les parts d'une répartition du total somment exactement à 1 : le reste de leurs arrondis, plancher compris, est porté sur la plus grande, qui peut alors porter plus de quatre décimales — `0.99999997` à côté de `0.00000003` ; une valeur isolée, ou la part d'un poste, qui ne porte qu'une partie des lignes, n'en reçoit aucun. L'arrondi ne vaut que pour la valeur rendue : le serveur calcule sur les grandeurs exactes, jamais sur une valeur arrondie | WF-DAT-0100, WF-DEV-0060, WF-PTF-0080 |
| Une seule enveloppe d'erreur, portant un code machine et ses paramètres, jamais une phrase | WF-ARC-0110 |
| 404 lorsque la permission de consultation manque, 403 lorsque c'est l'écriture ou la qualité de contributeur | WF-ADM-0110 |
| `lock_version` sur les écritures concurrentes, refus par 412 `STALE_LOCK_VERSION`, `params.expected_lock_version` la version courante, et rien d'autre | WF-IHM-0110 |
| Une valeur unique déjà portée est refusée par 409 `ALREADY_EXISTS`, `fields[]` désignant chaque champ dont la valeur est prise, `fields[].params.conflicting_object_id` l'objet qui la porte — et `fields[].params.conflicting_object_label` son libellé quand le formulaire ne connaît pas la liste qui le porte : le code d'un projet, celui d'un sous-projet, celui d'un nœud d'organisation, celui d'un rôle de ressource — ; une clé portée par le chemin — la catégorie et l'année d'un taux (`setHourlyRate`) — n'a pas de `fields` | WF-REF-0030, WF-REF-0040, WF-REF-0070, WF-REF-0090, WF-REF-0110, WF-PRJ-0010, WF-PRJ-0050 |
| Un seul préfixe de version, `/api/v1` | — |
| Une liste de la requête en un seul paramètre, ses valeurs séparées par des virgules (`explode: false`) : `kinds=task,estimate_line` ; `make lint-openapi` le vérifie (`rule/array-parameter-*` de `redocly.yaml`) | — |
| Une colonne de nombres se filtre par deux bornes, `<colonne>_min` et `<colonne>_max`, incluses, dans le type de la colonne ; une borne mal formée est refusée par 422 `NUMBER_INVALID`, une borne supérieure inférieure à l'inférieure par 422 `VALUE_OUT_OF_RANGE` sur `/query/<colonne>_max` | WF-IHM-0130 |
| Une période se filtre par `from` et `to`, le début inclus ; un instant (`Timestamp`) a sa fin exclue, une date de planning sa fin incluse. Une fin qui précède le début est refusée par 422 `VALIDATION_FAILED`, `fields[]` désignant `/query/to` par `VALUE_OUT_OF_RANGE`, `params.minimum` le début donné ; un début ou une fin mal formés, `/query/from` ou `/query/to` par `DATE_INVALID` | WF-IHM-0130 |
| Un tri à égalité se départage par l'ordre de la liste sans tri, puis par l'identifiant | WF-IHM-0060 |
| Une recherche (`search`, et tout filtre qui retient un texte qui contient le texte donné, comme `code` des nœuds d'organisation) ignore la casse et les accents : un texte est retenu dès qu'il contient le texte cherché, l'un et l'autre translittérés comme par la fonction `unaccent` de PostgreSQL avec sa table livrée (lettres accentuées, ligatures et lettres barrées), puis mis en minuscules — « etudes », « ETUDES » et « Études » trouvent « Études », « ines » trouve « Inès », « main-d'oeuvre » trouve « Main-d'œuvre », « strasse » trouve « Straße ». Un tri, lui, compare les textes dans l'ordre des points de code Unicode, accents et casse compris : ranger n'est pas trouver | WF-IHM-0130, WF-IHM-0060 |
| Toute écriture de grille — cellule, collage, déplacement, création, liaison, avancement, réestimation, inscription, suppression — rend `NodesWritten` : nœuds écrits, ancêtres recalculés, tâches redatées (`NodeSchedule`), totaux de la structure, compteur de la structure | WF-IHM-0040, WF-DEV-0050, WF-PLA-0020, WF-ARC-0020 |
| Toute opération gardée par la session déclare le `401` ; une opération publique le dit par `security: []` ; `make lint-openapi` le vérifie (`rule/session-operation-declares-401` de `redocly.yaml`) | WF-SEC-0020, WF-ARC-0060 |
| Une opération longue renvoie une tâche de fond, jamais un résultat | WF-ARC-0090 |
| L'API ne localise rien ; seuls les documents qu'elle engendre suivent la langue du destinataire | WF-ARC-0110, WF-INTF-0180 |

## Vérifier, assembler, simuler

Depuis la racine du dépôt :

```bash
make lint-openapi     # contrôles, bloquants en CI
make build-openapi    # contrôle puis assemble en un fichier
make mock             # sert un faux back depuis le contrat
make inventory        # régénère INVENTORY.md
```

Le fichier assemblé n'est pas versionné : il se régénère. Les mocks de la maquette sont
engendrés du contrat, jamais écrits à la main — un mock écrit à la main dérive et ne
valide plus rien. Leurs jeux de données sont les exemples chiffrés des champs Vérif de la
spécification (WF-QUA-0020), aux volumes du §4.6.2.

## Ce que le contrat ne porte pas

Une partie des exigences n'a pas de surface d'API, et il vaut mieux qu'elles n'en aient pas :
architecture interne, exploitation, migrations, invariants d'interface, chaîne de
vérification. `INVENTORY.md` les compte et les liste avec leur raison, à chaque
`make inventory`.

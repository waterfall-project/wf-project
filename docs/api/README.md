# Contrat d'interface de Waterfall

Ce répertoire porte le contrat OpenAPI de l'API de Waterfall. Il est **écrit à la main et
fait foi** : tout endpoint, tout schéma et toute erreur qu'un client peut rencontrer y
figurent, le client du front en est engendré, et la chaîne rejette une version des
services dont une réponse s'en écarte (WF-ARC-0060, annexe C de la spécification).

La spécification est dans `../spec`. Chaque opération cite dans ses propres mots — résumé
ou description — les exigences qu'elle réalise : c'est ce qui rend la traçabilité vérifiable
dans les deux sens, et `make inventory` échoue sur une opération qui n'en cite aucune.

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
| Une seule enveloppe d'erreur, portant un code machine et ses paramètres, jamais une phrase | WF-ARC-0110 |
| 404 lorsque la permission de consultation manque, 403 lorsque c'est l'écriture ou la qualité de contributeur | WF-ADM-0110 |
| `lock_version` sur les écritures concurrentes, refus par 412 | WF-IHM-0110 |
| Un seul préfixe de version, `/api/v1` | — |
| Une liste de la requête en un seul paramètre, ses valeurs séparées par des virgules (`explode: false`) : `kinds=task,estimate_line` ; `make lint-openapi` le vérifie (`rule/array-parameter-*` de `redocly.yaml`) | — |
| Toute écriture de grille — cellule, collage, déplacement, création, liaison, avancement, réestimation, inscription, suppression — rend `NodesWritten` : nœuds écrits, ancêtres recalculés, totaux de la structure, compteur de la structure | WF-IHM-0040, WF-DEV-0050, WF-ARC-0020 |
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

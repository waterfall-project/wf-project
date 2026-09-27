# Contrat d'interface de Waterfall

Ce répertoire porte le contrat OpenAPI de l'API de Waterfall. Il est **écrit à la main et
fait foi** : tout endpoint, tout schéma et toute erreur qu'un client peut rencontrer y
figurent, le client du front en est engendré, et la chaîne rejette une version des
services dont une réponse s'en écarte (WF-ARC-0060, annexe C de la spécification).

La spécification est dans `../spec`. Chaque description cite les exigences qu'elle
réalise : c'est ce qui rend la traçabilité vérifiable dans les deux sens.

## Organisation

| Chemin | Contenu |
|---|---|
| `openapi.yaml` | racine : information, serveurs, étiquettes, sécurité, et un renvoi par chemin |
| `paths/<famille>.yaml` | les opérations, une famille par fichier |
| `components/common.yaml` | types élémentaires, enveloppe d'erreur, référence de tâche de fond |
| `components/parameters.yaml` | paramètres partagés |
| `components/responses.yaml` | réponses d'erreur partagées |
| `components/schemas/<famille>.yaml` | schémas, plusieurs par fichier |
| `INVENTAIRE.md` | inventaire des endpoints et couverture des exigences, régénérable |

Les schémas sont groupés par famille plutôt qu'un fichier par schéma : cent
quarante-sept fichiers d'une douzaine de lignes se relisent moins bien qu'une douzaine de
fichiers cohérents.

## Conventions

Chacune est dictée par une exigence, et aucune ne se discute au cas par cas.

| Convention | Exigence |
|---|---|
| Identifiants UUID engendrés par le serveur, jamais séquentiels dans une URL | WF-DAT-0060 |
| `snake_case` partout, sans exception | — |
| Les noms du tableau de correspondance du §4.4.1 : `estimate_line` est une ligne de devis, `cost_line` une ligne de coût réel | §4.4.1 |
| Décimaux exacts transportés en chaîne, dates de planning sans heure, horodatages en temps universel | WF-DAT-0100 |
| Une seule enveloppe d'erreur, portant un code machine et ses paramètres, jamais une phrase | WF-ARC-0110 |
| 404 lorsque la permission de consultation manque, 403 lorsque c'est l'écriture ou la qualité de contributeur | WF-ADM-0110 |
| `lock_version` sur les écritures concurrentes, refus par 412 | WF-IHM-0110 |
| Un seul préfixe de version, `/api/v1` | — |
| Une opération longue renvoie une tâche de fond, jamais un résultat | WF-ARC-0090 |
| L'API ne localise rien ; seuls les documents qu'elle engendre suivent la langue du destinataire | WF-ARC-0110, WF-INTF-0180 |

## Vérifier, assembler, simuler

Depuis la racine du dépôt :

```bash
make lint-openapi     # contrôles, bloquants en CI
make build-openapi    # contrôle puis assemble en un fichier
make mock             # sert un faux back depuis le contrat
make inventory        # régénère INVENTAIRE.md
```

Le fichier assemblé n'est pas versionné : il se régénère. Les mocks de la maquette sont
engendrés du contrat, jamais écrits à la main — un mock écrit à la main dérive et ne
valide plus rien. Leurs jeux de données sont les exemples chiffrés des champs Vérif de la
spécification (WF-QUA-0020), aux volumes du §4.6.2.

## Ce que le contrat ne porte pas

Vingt-six exigences n'ont pas de surface d'API, et il vaut mieux qu'elles n'en aient pas :
architecture interne, exploitation, migrations, invariants d'interface, chaîne de
vérification. `INVENTAIRE.md` les liste avec leur raison.

# Règles de codage — Java

Pour l'extension Keycloak de Waterfall (`deploy/keycloak/extension/`), et pour elle seule : le
point d'entrée `password-setup-link` et la règle de politique `not-last-name` (EP-03,
« Conception », « L'extension Keycloak »). Ce fichier complète le [guide](README.md) et les
règles de [Python](python.md), dont il reprend la forme ; il ne recopie ni la conception
d'EP-03, ni la documentation de Keycloak.

Une règle qu'un outil contrôle nomme son contrôle. Une règle que rien ne contrôle le dit :
c'est la revue qui la tient.

## Ce que les outils tiennent

| Règle | Où | Contrôle |
|---|---|---|
| Tout avertissement de `javac` est une erreur ; aucun processeur d'annotations | `-Xlint:all -Werror`, `<proc>none</proc>` dans `pom.xml` | `make build-keycloak` |
| Les tests JUnit passent : l'image ne se construit pas sans eux | `mvn package`, dans le Dockerfile | `make build-keycloak` |
| Ni `@SuppressWarnings`, ni commentaire d'analyseur (`NOSONAR`, `NOPMD`, `CHECKSTYLE:OFF`) ; un `TODO` cite son issue ; 1 000 lignes au plus | `tools/src/wftools/sources.py` | `make sources` |
| L'extension répond sur la plateforme, son royaume appliqué | `backend/tests/test_keycloak_platform.py` | `make test-keycloak`, `make check-keycloak` |
| Le Dockerfile | hadolint | `make lint-docker` |

Aucun poste n'a besoin d'une JVM : l'extension se compile et se teste dans l'image, dont la
chaîne lance la construction à chaque modification de `deploy/keycloak/` (famille `keycloak`
de `tools/paths.toml`). Aucun formateur n'est branché : le code suit la mise en forme de Google
(deux espaces, cent colonnes), et la revue la tient.

## Règles de conception

### Le moins de Java possible

L'extension ne fait que ce que la configuration de Keycloak ne sait pas faire. Ce qu'un
réglage du royaume peut dire — durées, politique de mot de passe, verrouillage, clients —
s'écrit dans `deploy/keycloak/realm/waterfall.yaml`, jamais dans le code.

*Pourquoi* : chaque ligne de Java suit les versions de Keycloak, un réglage du royaume non.
*Contrôle* : la revue.

### Keycloak seul, à la version de l'image

Les dépendances sont celles de Keycloak, en portée `provided` : rien d'autre n'entre dans le
jar. `keycloak.version` du `pom.xml` est la version de l'image du Dockerfile ; elles montent
ensemble, keycloak-config-cli avec elles. Les interfaces que l'extension implémente sont
internes à Keycloak (il le dit au démarrage, `KC-SERVICES0047`) : une montée de version se fait
avec `make check-keycloak`, qui éprouve l'extension sur la plateforme.

*Pourquoi* : un jar tiers dans `providers/` est une dépendance que personne ne met à jour ;
une extension compilée contre une autre version que celle qui l'exécute casse sans prévenir.
*Contrôle* : `make check-keycloak` ; l'accord des deux versions, la revue.

### Un point d'entrée authentifie, puis autorise, avant de lire

Un point d'entrée vérifie lui-même le jeton porteur du royaume, puis le rôle qu'il exige, avant
de lire quoi que ce soit du compte visé. Il refuse par un statut et un code machine en
`snake_case`, `{"error": "not_allowed"}`, jamais par une phrase : 401 sans jeton valable, 403
sans le rôle, 404 pour un compte inconnu, 409 pour un état qui l'interdit.

*Pourquoi* : le royaume ne protège pas un point d'entrée ajouté ; et le service, qui traduit
ces refus dans l'enveloppe du contrat, lit un code, pas un texte (`python.md`, « Une erreur est
un code, jamais une phrase »). *Contrôle* : les tests de `test_keycloak_platform.py`, un par
refus.

### Un texte montré est une clé de message du thème

Ce que Keycloak montre à une personne — le refus d'une règle de politique, un courriel — est
une clé des messages du thème (`deploy/keycloak/themes/waterfall/`), traduite en français et en
anglais. Le code ne porte que la clé.

*Pourquoi* : WF-QUA-0070, comme pour le front. *Contrôle* : la revue.

### Un lien d'action est un secret

Un lien d'action, un jeton, un nonce ne se journalisent pas, et ne sortent du point d'entrée que
dans sa réponse.

*Pourquoi* : le lien suffit à fixer le mot de passe d'un compte (WF-SEC-0030, WF-OBS-0020).
*Contrôle* : la revue.

### Les tests

- Ce qui se calcule sans Keycloak — une comparaison, une date écrite — est une méthode
  statique de portée paquet, éprouvée par JUnit (`src/test/java/`).
- Le reste s'éprouve contre le Keycloak de la plateforme, par
  `backend/tests/test_keycloak_platform.py` : aucune doublure de Keycloak, pas plus qu'une
  doublure de PostgreSQL pour le back.
- Un refus a son test, comme le cas nominal ; un test affirme un résultat.

*Pourquoi* : une doublure de Keycloak accepte ce que Keycloak refuse. *Contrôle* :
`make check-keycloak` ; la valeur d'une assertion, la revue.

## Défauts déjà rencontrés

Aucun encore. Un défaut trouvé en revue et qui peut revenir s'ajoute ici, comme dans
`python.md`.

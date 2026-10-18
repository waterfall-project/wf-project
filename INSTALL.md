# Installer un poste de développement

Cette notice prépare un poste pour développer et vérifier Waterfall :
- la maquette contre le faux back ;
- les contrôles de la chaîne ;
- la plateforme de service.

Pour installer une plateforme de démonstration à partir des images publiées, lire plutôt
[`deploy/compose/README.md`](deploy/compose/README.md).

## Prérequis

| Outil | Pour quoi |
|---|---|
| [uv](https://docs.astral.sh/uv/) | Python 3.13 et les dépendances du back et des outils du dépôt |
| Python 3.11 ou plus, sous le nom `python3` | la projection de la spécification |
| Node 24 | le front ; son corepack apporte pnpm |
| Docker et son greffon Compose | `make dev`, la plateforme de service, les images |
| `pandoc` 3.1.11.1 | la projection de la spécification (une autre version écrit un autre Markdown) |
| `mmdc` (`npm i -g @mermaid-js/mermaid-cli`) | facultatif : la validation des diagrammes |

`make check-tools` dit ce qui manque.

**Aucun environnement virtuel à créer.** Chaque commande Python du Makefile passe par
`uv run --frozen`. uv crée alors l'environnement du projet concerné (`backend/.venv`,
`tools/.venv`), installe Python 3.13 au besoin, puis les paquets tels que `uv.lock` les fixe.

## Le dépôt

```bash
git clone -b epic/EP-nn https://github.com/waterfall-project/wf-project.git   # ou sans -b, pour main
cd wf-project
```

Une branche d'EPIC (`epic/EP-nn`) porte le travail en cours ; `main` porte ce qui est livré.

## Une seule fois

```bash
make check-tools          # tout doit être « ok »
corepack enable pnpm      # pnpm à la version que le front épingle
make install-front        # les dépendances du front, telles que pnpm-lock.yaml les fixe
make e2e-browsers         # le navigateur des parcours de bout en bout (Chromium de Playwright)
```

Les environnements Python se créent à la première commande qui en a besoin : `make test-tools`,
`make check-back`, etc.

## La maquette contre le faux back

```bash
make dev                  # http://localhost:3000, le faux back sur http://localhost:4010
make dev-down             # l'arrête
```

`make dev` lance, sous Docker, deux services :
- le faux back : Prism, qui sert les exemples du contrat ;
- le front, en mode `mock`.

La session y est accordée d'office, sans Keycloak ni base de données.

## Les contrôles

```bash
make check BASE=origin/epic/EP-nn   # ce que la modification touche, avant de pousser
make check-all                      # toutes les familles, comme la chaîne
make e2e                            # les parcours de bout en bout contre le faux back
```

**Services de test.** Certains tests du back demandent de vrais services, que des variables
désignent ; sans sa variable, un tel test échoue en le disant :

| Service | Variable |
|---|---|
| PostgreSQL | `WATERFALL_TEST_DATABASE_URL` |
| Redis | `WATERFALL_TEST_REDIS_URL` (les tests du front sur les sessions la demandent aussi) |
| Garage, le stockage objet | `WATERFALL_TEST_STORAGE_URL` |

On peut prendre ceux de la plateforme de service (ci-dessous) ou lancer des services jetables. Les
sections « Un test contre PostgreSQL », « Un test contre le stockage objet » et « Un test contre
Redis » du [guide de développement](docs/dev/README.md) donnent la forme des adresses et les
commandes.

## La plateforme de service

La plateforme de service est décrite dans `deploy/compose/compose.service.yaml`. Elle démarre ces
services :
- PostgreSQL ;
- Redis ;
- Garage, le stockage objet ;
- l'API, le worker et son planificateur ;
- le service de la restauration ;
- Keycloak, servi en HTTPS ;
- OpenLDAP et Mailpit.

Elle refuse de démarrer sans ses secrets. Aucun fichier ne les porte : le tableau de la section
« Commandes » du [guide de développement](docs/dev/README.md) les liste. Sur un poste, des
valeurs de poste suffisent, par exemple celles de `.github/workflows/keycloak.yml` :

```bash
export WATERFALL_POSTGRES_PASSWORD=devpostgres
export WATERFALL_SERVICE_DATABASE_PASSWORD=devservice
export WATERFALL_BACKUP_DATABASE_PASSWORD=devbackup
export WATERFALL_REDIS_PASSWORD=dev-redis
export WATERFALL_KEYCLOAK_DATABASE_PASSWORD=dev-keycloak-database
export WATERFALL_KEYCLOAK_ADMIN_PASSWORD=dev-keycloak-admin
export WATERFALL_FRONT_CLIENT_SECRET=dev-front-client
export WATERFALL_SERVICE_CLIENT_SECRET=dev-service-client
export WATERFALL_INSTALLATION_CLIENT_SECRET=dev-installation-client
export WATERFALL_STORAGE_SECRET=dev-storage-secret
export WATERFALL_STORAGE_RPC_SECRET=$(openssl rand -hex 32)
```

Les mots de passe de PostgreSQL ne doivent contenir que des lettres et des chiffres, parce qu'ils
s'écrivent dans une URL.

Une fois les secrets exportés :

```bash
make service-up           # démarre la plateforme ; Keycloak sur https://localhost:8443/auth
make service-install      # amorce l'installation et écrit le lien du premier administrateur
make service-logs         # les journaux (SERVICES="api keycloak" pour n'en voir que certains)
make service-down         # l'arrête ; WATERFALL_RESET_DATA=yes supprime aussi ses données
```

**À savoir sur ces commandes :**
- **Secrets.** Ils doivent rester les mêmes d'un démarrage à l'autre. Le mot de passe de
  l'administrateur de Keycloak n'est lu qu'au premier démarrage : pour en changer, il faut
  `make service-down WATERFALL_RESET_DATA=yes`.
- **Le lien de `make service-install`.** Il fixe le mot de passe de l'administrateur
  (`administrateur@waterfall.test` par défaut, ou `WATERFALL_ADMIN_EMAIL`) et vaut jusqu'à son
  emploi.
- **Certificat de Keycloak.** Il vient d'une autorité locale, dont `make service-up` copie la racine
  dans `deploy/compose/.authority/root.crt`. Le navigateur avertit, sauf si on importe cette
  racine.
- **Courriels.** Mailpit les montre sur `http://127.0.0.1:8025`.

### Le front contre la plateforme de service

Le front se lance alors sur le poste, avec les réglages que `make e2e-service` lui donne, mais
cette fois sans le mandataire Prism. Cette façon de faire n'est pas éprouvée par la chaîne :
seul `make e2e-service` l'est.

```bash
cd frontend
WATERFALL_API_ADDRESS=http://127.0.0.1:8000 \
WATERFALL_KEYCLOAK_ADDRESS=https://localhost:8443/auth \
WATERFALL_FRONT_ADDRESS=http://localhost:3000 \
WATERFALL_REDIS_URL="redis://:${WATERFALL_REDIS_PASSWORD}@127.0.0.1:6379/0" \
NODE_EXTRA_CA_CERTS=../deploy/compose/.authority/root.crt \
pnpm exec next dev --hostname 0.0.0.0
```

**Pourquoi ces réglages :**
- **Le secret du client du front.** `WATERFALL_FRONT_CLIENT_SECRET` est déjà exporté.
- **L'écoute sur toutes les interfaces.** Keycloak notifie la fermeture des sessions au front par
  `http://host.docker.internal:3000`. Le front doit donc écouter sur toutes les interfaces du
  poste.
- **L'adresse du front.** Le royaume l'apprend à chaque `make service-up` (`WATERFALL_FRONT_ADDRESS`,
  `http://localhost:3000` par défaut), et `make e2e-service` la remplace par celle de ses
  parcours jusqu'au démarrage suivant. Après un `make e2e-service`, relancer `make service-up`.

## Pour aller plus loin

- [`CONTRIBUTING.md`](CONTRIBUTING.md) : comment changer la spécification, le contrat ou le code.
- [`docs/dev/README.md`](docs/dev/README.md) : le guide de développement, avec toutes les commandes
  (« Commandes »), la chaîne (« Chaîne ») et les tests (« Tests »).
- `make help` : la liste des commandes.

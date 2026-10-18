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

**Toutes les commandes `make` se lancent depuis la racine du clone.** Dans un sous-dossier,
`frontend/` par exemple, `make` répond `No rule to make target`.

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

**Elle ne contient pas le front** : on le lance sur le poste (étape 3 ci-dessous).

**Le service ne sert que ce qui est livré dans `main`**, soit, depuis EP-03 :
- les comptes et les rôles ;
- la session ;
- le journal d'audit ;
- les sauvegardes et la restauration.

Contre lui, les écrans des projets et du référentiel n'ont pas de données : leurs lectures
répondent 404, parce qu'EP-04 et EP-05 ne sont pas livrés.

Le front ne lit qu'une adresse d'API à la fois, il n'y a pas de mode mixte. Pour parcourir ces
écrans, on lance la maquette (`make dev`) à la place du front contre le service : les deux
prennent le port 3000.

### 1. Les secrets

La plateforme refuse de démarrer sans ses secrets. Aucun fichier ne les porte : le tableau de la
section « Commandes » du [guide de développement](docs/dev/README.md) les liste. Sur un poste,
des valeurs de poste suffisent, par exemple celles de `.github/workflows/keycloak.yml`. On les
exporte dans le terminal d'où l'on lancera la plateforme et le front :

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

**Les secrets ne sont lus qu'au premier démarrage.** PostgreSQL, Keycloak et Garage les
retiennent dans leurs volumes. Ces volumes appartiennent au projet Compose `waterfall-service`, le
même quel que soit le dossier du clone : une plateforme déjà démarrée sur ce poste, même depuis un
autre clone ou avec d'autres secrets, est réutilisée.

Si les mots de passe ne correspondent plus, `make service-up` échoue sur `migrate` ou
`keycloak-database`, et `make service-logs SERVICES=migrate` dit `password authentication
failed`. Deux façons d'en sortir :
- réexporter les secrets du premier démarrage ;
- repartir de zéro : `make service-down WATERFALL_RESET_DATA=yes` supprime les bases, le
  stockage, l'annuaire et l'autorité de Keycloak.

`docker volume ls | grep waterfall-service` montre les volumes présents.

### 2. Démarrer la plateforme

```bash
make service-up           # Keycloak sur https://localhost:8443/auth, l'API sur http://127.0.0.1:8000
```

Le certificat de Keycloak vient d'une autorité locale, dont `make service-up` copie la racine dans
`deploy/compose/.authority/root.crt`. Le navigateur avertit, sauf si on importe cette racine.

### 3. Lancer le front

Dans le même terminal, depuis la racine, avant d'ouvrir le lien de l'étape 4 : à la fin de
l'amorçage, Keycloak renvoie au front, sur `http://localhost:3000`.

```bash
(cd frontend && \
  WATERFALL_API_ADDRESS=http://127.0.0.1:8000 \
  WATERFALL_KEYCLOAK_ADDRESS=https://localhost:8443/auth \
  WATERFALL_FRONT_ADDRESS=http://localhost:3000 \
  WATERFALL_REDIS_URL="redis://:${WATERFALL_REDIS_PASSWORD}@127.0.0.1:6379/0" \
  NODE_EXTRA_CA_CERTS=../deploy/compose/.authority/root.crt \
  pnpm exec next dev --hostname 0.0.0.0)
```

**À propos de cette commande :**
- **Les parenthèses.** Elles lancent la commande dans un sous-shell : le terminal reste à la racine,
  où les commandes `make` se lancent.
- **Le secret du client du front.** `WATERFALL_FRONT_CLIENT_SECRET` est déjà exporté (étape 1).
- **L'écoute sur toutes les interfaces.** Keycloak notifie la fermeture des sessions au front par
  `http://host.docker.internal:3000`. Le front doit donc écouter sur toutes les interfaces du
  poste.
- **L'adresse du front.** Le royaume l'apprend à chaque `make service-up` (`WATERFALL_FRONT_ADDRESS`,
  `http://localhost:3000` par défaut), et `make e2e-service` la remplace par celle de ses
  parcours jusqu'au démarrage suivant. Après un `make e2e-service`, relancer `make service-up`.
- **Ce que la chaîne éprouve.** Ce lancement a été vérifié sur un poste. La chaîne, elle,
  n'éprouve que `make e2e-service`, qui donne les mêmes réglages au front, mais à travers le
  mandataire Prism.

### 4. Amorcer l'installation

Dans un second terminal, à la racine, les secrets exportés :

```bash
make service-install
```

La commande écrit le lien qui fixe le mot de passe du premier administrateur
(`administrateur@waterfall.test` par défaut, ou `WATERFALL_ADMIN_EMAIL`). Le lien vaut jusqu'à son
emploi. On l'ouvre dans le navigateur, on fixe le mot de passe, puis le bouton de retour mène au
front, où l'on se connecte. Les courriels des autres comptes arrivent dans Mailpit, sur
`http://127.0.0.1:8025`.

### Arrêter

```bash
make service-logs         # les journaux (SERVICES="api keycloak" pour n'en voir que certains)
make service-down         # arrête la plateforme ; WATERFALL_RESET_DATA=yes supprime aussi ses données
```

## Pour aller plus loin

- [`CONTRIBUTING.md`](CONTRIBUTING.md) : comment changer la spécification, le contrat ou le code.
- [`docs/dev/README.md`](docs/dev/README.md) : le guide de développement, avec toutes les commandes
  (« Commandes »), la chaîne (« Chaîne ») et les tests (« Tests »).
- `make help` : la liste des commandes.

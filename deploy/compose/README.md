<!--
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only
-->

# Déployer une plateforme de démonstration

Cette notice installe Waterfall sur une machine seule, à partir des images que la chaîne publie
sur `ghcr.io/waterfall-project`, derrière un frontal HTTPS (US-0430, WF-ARC-0050). Le fichier
Compose est `compose.prod.yaml` ; les autres fichiers de ce répertoire servent la plateforme de
développement et la plateforme de service, sauf ceux qu'il monte : `Caddyfile.prod`,
`garage.toml`, `storage-buckets.sh` et les scripts SQL des rôles et des bases.

La plateforme compte un frontal Caddy, seul port ouvert, qui obtient ses certificats de Let's
Encrypt et sert le front à la racine et Keycloak sous `/auth`, hors sa console ; le front, l'API, le worker et le
planificateur de ses tâches ; PostgreSQL, qui porte deux bases, celle de Waterfall et celle de
Keycloak ; Redis ; Garage, le stockage objet, et ses compartiments `backups` et `imports` ;
Keycloak et l'application de son royaume. Les données vivent dans des volumes nommés.

Une démonstration n'a pas de messagerie : les liens par lesquels un compte fixe son mot de passe
se remettent depuis l'écran des comptes (WF-CMP-0030). Le chiffrement entre les services, plusieurs
instances de l'API et la mise à jour sans interruption relèvent d'EP-13.

## Installer

Il faut :

- une machine Linux avec Docker Engine et son greffon Compose (`docker compose version`) ;
- un nom pour elle, que le DNS fait pointer sur son adresse publique ;
- les ports 80 et 443 ouverts depuis Internet : Let's Encrypt vérifie le nom par le port 80, et
  Caddy y renvoie tout vers HTTPS ;
- ce répertoire, `deploy/compose`, copié sur la machine — ou le dépôt cloné.

Puis :

1. Choisir l'étiquette des images : une version publiée (`0.1.0`), l'empreinte entière d'un commit
   de `main` ou d'une branche d'EPIC, ou une branche mise en forme d'étiquette (`epic-EP-03`). Si
   les paquets de l'organisation ne sont pas publics, se connecter au registre :
   `docker login ghcr.io`, avec un jeton qui lit les paquets.
2. Copier le modèle de réglages et le protéger :

   ```sh
   cd deploy/compose
   cp production.env.example .env
   chmod 600 .env
   ```

3. Remplir `.env` : le nom de la machine (`WATERFALL_DOMAIN`), l'adresse que Let's Encrypt
   prévient (`WATERFALL_ACME_EMAIL`), l'étiquette (`WATERFALL_IMAGE_TAG`), l'adresse du premier
   administrateur (`WATERFALL_ADMIN_EMAIL`), la langue de l'installation, et chaque secret, tiré
   au hasard comme le modèle l'indique. Git ignore `.env` ; en garder une copie à part.
4. Démarrer :

   ```sh
   docker compose -f compose.prod.yaml up --detach --wait
   ```

   Compose tire les images, puis démarre les services dans l'ordre : PostgreSQL, la base de
   Waterfall et son propriétaire, les rôles et la base de Keycloak, les migrations, l'API, le worker, Keycloak, l'application du royaume, le
   front. Un réglage ou un secret absent de `.env` arrête la commande en nommant la variable. Au
   premier démarrage, Caddy obtient le certificat du nom : la plateforme répond ensuite sur
   `https://<nom>`. En HTTP, Caddy renvoie à la même page sur cette adresse ; en HTTPS, il demande
   au navigateur de ne plus revenir qu'en HTTPS pendant un an (HSTS), et interdit à un autre site
   d'encadrer ses pages.

PostgreSQL a son administrateur, `postgres`, dont le mot de passe,
`WATERFALL_POSTGRES_ADMIN_PASSWORD`, ne sert qu'aux services d'initialisation qui créent, à chaque
démarrage et s'ils manquent, les rôles et les bases (`waterfall-database.sql`,
`keycloak-database.sql` et les scripts des rôles) ; il n'est lu qu'au premier démarrage, qui le
crée. Pour le changer ensuite, on le change dans le serveur, puis dans `.env` :

```sh
docker compose -f compose.prod.yaml exec postgres psql -U postgres -c "ALTER ROLE postgres PASSWORD '<nouveau>'"
```

Les migrations et l'amorçage passent par `waterfall`, propriétaire de la base et de ses
tables, qui n'est pas superutilisateur et ne crée ni rôle ni base (`WATERFALL_POSTGRES_PASSWORD`) ;
l'API, le worker et le planificateur, par le rôle du service, qui ne tient que ce que les tables lui
accordent ; les sauvegardes, par le rôle de sauvegarde.

## Amorcer

Une fois la plateforme démarrée, l'amorçage (US-0420) crée l'installation, ses trois rôles
prédéfinis et son administrateur local, dans Keycloak et dans Waterfall, et écrit sur sa sortie le
lien par lequel celui-ci fixe son mot de passe :

```sh
docker compose -f compose.prod.yaml run --rm install
```

Ouvrir ce lien dans un navigateur, fixer le mot de passe, puis se connecter sur `https://<nom>`.
Le lien vaut jusqu'à son emploi. Relancée, la commande ne crée rien : elle écrit un nouveau lien,
qui remplace le précédent, tant que l'administrateur n'a pas de mot de passe, et aucun ensuite.

L'amorçage est un service à lui, `install`, que `up` ne démarre jamais : il passe par le
propriétaire des tables (#701) et tient seul le secret du client de l'amorçage (#652), que ni
l'API ni le worker ne tiennent. C'est la même image que l'API, sous la commande
`waterfall-api install`.

## Administrer Keycloak

La console d'administration de Keycloak et son royaume `master`, dont l'administrateur `admin`
tient tous les royaumes, ne sont pas servis par Caddy : `/auth/admin` et `/auth/realms/master`
répondent 404. Le royaume `waterfall` se règle par son fichier, que `keycloak-realm` applique à
chaque démarrage ; un réglage fait à la main dans la console y revient.

Pour ouvrir la console quand même, le temps d'une intervention, une surcharge Compose locale
publie Keycloak sur la seule boucle locale de la machine, et lui dit que sa console s'y trouve.
Elle s'écrit à côté des autres, sous le nom `compose.admin.yaml` par exemple :

```yaml
services:
  keycloak:
    environment:
      KC_HOSTNAME_ADMIN: http://localhost:8080/auth
    ports:
      - "127.0.0.1:8080:8080"
```

```sh
docker compose -f compose.prod.yaml -f compose.admin.yaml up --detach --wait keycloak
```

Depuis un poste, un tunnel SSH y mène : `ssh -L 8080:127.0.0.1:8080 <machine>`, puis
`http://localhost:8080/auth/admin/master/console/` dans le navigateur du poste, avec
l'utilisateur `admin` et le mot de passe `WATERFALL_KEYCLOAK_ADMIN_PASSWORD`. L'intervention
finie, Keycloak redémarre sans la surcharge, et le port se referme :

```sh
docker compose -f compose.prod.yaml up --detach --wait keycloak
```

## Mettre à jour

1. Prendre une sauvegarde (ci-dessous).
2. Changer `WATERFALL_IMAGE_TAG` dans `.env`.
3. Tirer les images et relancer :

   ```sh
   docker compose -f compose.prod.yaml pull
   docker compose -f compose.prod.yaml up --detach --wait
   ```

Le service `migrate` applique les migrations sous le rôle propriétaire avant que l'API, qui ne
tient que le rôle du service, ne démarre (#701, WF-DAT-0140) ; `keycloak-realm` applique de
nouveau le royaume de l'image, et un réglage changé à la main dans la console y revient.
L'interruption dure le temps du redémarrage.

## Sauvegarder

La sauvegarde de Waterfall (WF-ADM-0150) est une tâche du worker, que demande un administrateur
(`startBackup`) et qu'il télécharge ensuite (`downloadBackup`) : le worker vide les deux bases par
le rôle de sauvegarde, membre de `pg_read_all_data`, qui ne peut ni écrire ni couper un déclencheur
(#895), et range l'archive dans le compartiment `backups` de Garage, dans le volume
`storage-data`. Une copie hors de la machine se fait en téléchargeant l'archive. L'écran des
sauvegardes de l'administration la demande et la télécharge une fois branché sur le service
(US-0440/L3).

Une copie à froid des volumes reste possible, plateforme arrêtée (`down`, sans `--volumes`) :

```sh
docker run --rm -v waterfall_postgres-data:/data:ro -v "$PWD:/copy" alpine \
  tar -czf /copy/postgres-data.tar.gz -C /data .
```

et de même pour `waterfall_storage-data`. Garder aussi une copie de `.env` : ses secrets sont ceux
de l'installation.

## Arrêter

```sh
docker compose -f compose.prod.yaml down
```

arrête et retire les conteneurs, et garde les volumes : `up` repart sur les mêmes données et les
mêmes certificats. `down --volumes` supprime en plus les bases, le stockage objet et les
certificats : toutes les données de l'installation sont perdues.

## Essayer sur un poste

Un nom local — `localhost`, `*.localhost`, `*.internal` — n'a pas de certificat de Let's Encrypt :
Caddy le fait de sa propre autorité. Le front, qui joint Keycloak par Caddy en HTTPS, doit alors se
fier à sa racine ; le fichier `compose.prod.local.yaml` le fait, donné après l'autre :

```sh
docker compose -f compose.prod.yaml -f compose.prod.local.yaml up --detach --wait
```

Le navigateur, lui, avertit sur ce certificat. `WATERFALL_HTTPS_PORT` et `WATERFALL_HTTP_PORT`
déplacent les ports publiés ; un port HTTPS autre que 443 entre dans l'adresse de la plateforme.

`make production-trial` fait ainsi l'essai de la chaîne (`wftools.production`) : sur les images de
`WATERFALL_IMAGE_TAG` — le commit du dépôt par défaut, que `make images` construit —, sous le nom
`waterfall.localhost`, il démarre la plateforme, l'amorce, vérifie la sonde de vie de l'API, que
HTTP renvoie à la même page sur l'adresse publiée, port compris, que HTTPS répond avec HSTS et les
autres en-têtes de Caddy, que la console de Keycloak et le royaume `master` répondent 404, et que le premier administrateur fixe son mot de passe par le lien, se
connecte par le front et Keycloak et que le front le nomme ; puis il retire la plateforme et ses
volumes. Ses secrets viennent de l'environnement, comme `production.env.example` les nomme.

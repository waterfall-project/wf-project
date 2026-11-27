<!--
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only
-->

# Déployer une plateforme de démonstration

Cette notice installe Waterfall sur une machine seule, à partir des images que la chaîne publie
sur `ghcr.io/waterfall-project`, derrière un frontal HTTPS (US-0430, WF-ARC-0050). Le fichier
Compose est `compose.prod.yaml` ; les autres fichiers de ce répertoire servent la plateforme de
développement et la plateforme de service, sauf ceux qu'il monte : `Caddyfile.prod`,
`garage.toml`, `storage-buckets.sh`, `postgres-volume.sh`, les scripts SQL des rôles et des
bases, ceux de Prometheus : `prometheus.sh`, `prometheus.yml` et `prometheus-alerts.yml`, ceux
d'Alertmanager, `alertmanager.sh`, `alertmanager-web.yml` et `alertmanager-client.yml`, ceux de
Grafana : `grafana-datasource.yml`, `grafana-dashboards.yml` et `grafana-dashboard.json`, et ceux
du chiffrement : `pg_hba.conf`, `Caddyfile.storage`, `Caddyfile.front`, `prometheus-web.yml` et
`prometheus-client.yml`.

La plateforme compte un frontal Caddy, seul port ouvert, qui obtient ses certificats de Let's
Encrypt et sert le front à la racine, Keycloak sous `/auth`, hors sa console, et Grafana sous `/grafana` ; le front, l'API, le worker et le
planificateur de ses tâches ; PostgreSQL, qui porte deux bases, celle de Waterfall et celle de
Keycloak ; Redis ; Garage, le stockage objet, et ses compartiments `backups` et `imports` ;
Keycloak et l'application de son royaume ; Prometheus, qui collecte les métriques du front, de
l'API et du worker et évalue les règles des alertes, Alertmanager, qui les notifie par courriel, et Grafana, le tableau
de bord de l'exploitant (« Superviser »). Les données vivent dans des
volumes nommés.

Redis est employé sous la licence AGPLv3, comme Waterfall lui-même, depuis sa version 8 ; le dépôt
ne redistribue pas Redis : la plateforme tire son image du registre public.

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
   prévient (`WATERFALL_ACME_EMAIL`), les empreintes des images (`WATERFALL_DIGEST_FRONT`,
   `WATERFALL_DIGEST_WATERFALL`, `WATERFALL_DIGEST_KEYCLOAK`, les trois lignes de `digests.env`,
   l'artefact du passage de `images.yml` qui a publié la version, que « Mettre à jour » dit où
   retrouver), l'adresse du premier
   administrateur (`WATERFALL_ADMIN_EMAIL`), la langue de l'installation, sa devise
   (`WATERFALL_CURRENCY`, trois lettres majuscules, qui ne change plus ensuite) et le nom de
   l'entreprise (`WATERFALL_COMPANY_NAME`, que portent les fichiers exportés), son fuseau horaire
   (`WATERFALL_TIME_ZONE`, un nom de la base IANA comme `Europe/Paris`, `UTC` si on le laisse vide, dans
   lequel s'entend le jour courant, et qui ne change plus ensuite), la capacité en octets de l'espace
   où PostgreSQL et le stockage objet gardent leurs données (`WATERFALL_DATABASE_CAPACITY_BYTES`,
   `WATERFALL_STORAGE_CAPACITY_BYTES`, sans lesquelles l'alerte d'un stockage plein ne pourrait pas
   apparaître), le serveur de messagerie des alertes s'il y en a un (`WATERFALL_ALERT_SMTP_HOST` et
   les valeurs qui le suivent dans le modèle), et chaque secret, dont le mot de passe du tableau de
   bord (`WATERFALL_GRAFANA_ADMIN_PASSWORD`, sans lequel Grafana ne démarre pas), tiré au hasard comme le modèle l'indique. Git ignore `.env` ; en garder une copie à part.
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

### Le chiffrement entre les services

Tout échange à l'intérieur de la plateforme est chiffré (US-2840, WF-SEC-0010) : PostgreSQL, Redis,
l'API, Keycloak, Prometheus — que l'API et Grafana lisent en HTTPS (TFX-14,
`prometheus-web.yml`) —, Alertmanager — à qui Prometheus envoie les alertes en HTTPS
(`alertmanager-web.yml`) — et Grafana ne servent qu'en TLS, le stockage objet derrière un
mandataire TLS (`storage-proxy`, `Caddyfile.storage`) — Garage, qui ne chiffre pas, n'est joint que
par lui, sur un réseau qu'ils sont seuls à partager —, et le front de même (`front-proxy`,
`Caddyfile.front`) : le serveur de Next n'écoute que sur le réseau `front`, qu'il est seul à partager
avec son mandataire, à son nom sur ce réseau, `front-next`, et la porte, comme Keycloak sur son
canal arrière (TFX-17), le joint à `https://front-proxy:3443` (#4508). Chacun des deux redémarre
seul : le mandataire retrouve le front par ce nom. Chaque client — la porte comprise, vers le front,
Keycloak et Grafana — vérifie le certificat du serveur et son nom contre la racine de l'autorité de
la plateforme ; une connexion en clair est refusée. Keycloak, seule instance, garde ses caches pour
lui (`KC_CACHE=local`) : il n'ouvre aucun port de grappe, ni 7800 ni 57800, où JGroups parlerait en
clair. Seuls les points de métriques restent en HTTP, sur un port que la porte ne route pas
(TFX-09).

Cette autorité est celle de l'exploitant s'il la fournit : son certificat, `ca.crt` — suivi au
besoin de ceux qui mènent à la racine —, et sa clé, `ca.key`, non chiffrée, dans le répertoire
`authority` voisin de ce fichier (ou celui que nomme `WATERFALL_AUTHORITY_DIRECTORY`), lisible de
root seul ; git l'ignore. Sinon, le service `authority` en crée une au premier démarrage et la
garde dans le volume `authority`, que nul autre service ne monte. À chaque démarrage, il émet de
nouveau le certificat de chaque serveur, valable deux ans, dans un volume propre à ce serveur, et
écrit la racine dans le volume `trust`, que lisent les clients. Une autorité fournie qu'il ne lit
pas — clé absente, chiffrée ou qui n'est pas celle du certificat, certificat qui n'est pas d'une
autorité ou n'est plus valable — l'arrête en le disant, et la plateforme avec lui. Un serveur
démarré sans son certificat s'arrête en nommant le fichier ; un processus de l'API, du worker ou
de la restauration refuse de démarrer sur une adresse en clair, en la nommant.

Rien d'autre ne renouvelle ces certificats : une plateforme qui ne redémarre pas en deux ans les
voit expirer, et ses services ne se joignent plus. Redémarrer le service `authority` les renouvelle ;
chaque serveur ne relit le sien qu'à son propre démarrage, d'où le plus simple, arrêter la
plateforme et la redémarrer (`down`, sans `--volumes`, puis `up --detach --wait`), qui relance
`authority` avant tout autre service.

Pour changer d'autorité, déposer la nouvelle dans `authority`, puis arrêter la plateforme et la
redémarrer (`down`, sans `--volumes`, puis `up --detach --wait`) : chaque serveur relit alors un
certificat qu'elle signe, et chaque client la nouvelle racine. Pour que la plateforme en recrée une
à elle, retirer le volume `authority` à l'arrêt.

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
Keycloak ne sert qu'en HTTPS, avec le certificat que l'autorité de la plateforme lui a émis, qui
vaut aussi pour `localhost` (« Le chiffrement entre les services »). La surcharge s'écrit à côté
des autres, sous le nom `compose.admin.yaml` par exemple :

```yaml
services:
  keycloak:
    environment:
      KC_HOSTNAME_ADMIN: https://localhost:8443/auth
    ports:
      - "127.0.0.1:8443:8443"
```

```sh
docker compose -f compose.prod.yaml -f compose.admin.yaml up --detach --wait keycloak
```

Depuis un poste, un tunnel SSH y mène : `ssh -L 8443:127.0.0.1:8443 <machine>`, puis
`https://localhost:8443/auth/admin/master/console/` dans le navigateur du poste — qui avertit,
sauf si on y importe la racine de la plateforme, que donne `docker compose -f compose.prod.yaml cp
caddy:/trust/root.crt .` —, avec
l'utilisateur `admin` et le mot de passe `WATERFALL_KEYCLOAK_ADMIN_PASSWORD`. L'intervention
finie, Keycloak redémarre sans la surcharge, et le port se referme :

```sh
docker compose -f compose.prod.yaml up --detach --wait keycloak
```

## Mettre à jour

1. Prendre une sauvegarde (ci-dessous).
2. Remplacer dans `.env` les trois empreintes `WATERFALL_DIGEST_…` par celles de la nouvelle
   version. La plateforme ne désigne ses images que par leur empreinte, jamais par une étiquette,
   qu'un travail qui peut écrire les paquets du registre pourrait déplacer (#3726). On les trouve :

   - dans l'artefact `digests` du passage d'`images.yml` qui a publié la version : le fichier
     `digests.env`, dont les trois lignes se copient telles quelles dans `.env`. L'artefact expire
     après 90 jours et se télécharge avec une session GitHub : on garde ces lignes avec les
     secrets, version par version, dès qu'on les a ;
   - à défaut, en les lisant au registre, une image après l'autre :

     ```sh
     for image in front waterfall keycloak; do
       docker buildx imagetools inspect ghcr.io/waterfall-project/$image:0.3.0 --format '{{.Manifest.Digest}}'
     done
     ```

     Cette lecture se fait **par l'étiquette** de la version (`0.3.0` ici), que quelqu'un qui peut
     écrire les paquets aurait pu déplacer : on la fait **une fois**, on vérifie que la version et
     les trois empreintes sont bien celles de la publication annoncée (étiquette de commit de
     l'image, ou passage d'`images.yml`), et on garde les empreintes lues.

3. Tirer les images et relancer :

   ```sh
   docker compose -f compose.prod.yaml pull
   docker compose -f compose.prod.yaml up --detach --wait
   ```

Le service `components` contrôle d'abord les composants (`waterfall-check-components`, WF-CMP-0020-A) :
PostgreSQL en version majeure 18 et réglé pour au moins 1 024 verrous par transaction, Redis en
version 8 ou plus et jamais en mode cluster (Redis Cluster n'est pas pris en charge), Keycloak en
version 26 ou plus. Un composant qui ne convient pas arrête la plateforme avant les migrations, en le
disant (`docker compose logs components`) ; il lit la version de Keycloak par l'extension, avec le compte de
service du royaume (`WATERFALL_SERVICE_CLIENT_SECRET`), et attend donc que `keycloak-realm` ait
appliqué le royaume : il ne tient pas le mot de passe de l'administrateur de `master`. L'API, le worker et le
service de restauration refusent aussi de démarrer sur un PostgreSQL qui ne convient pas (#3964).

La plateforme entière — composants de données et supervision compris — tient sur une machine de quatre
cœurs et de huit gigaoctets (WF-CMP-0020-A) : la chaîne démarre ce Compose, avec la sauvegarde, la
restauration et le test de restauration, dans une tranche de cgroups bornée à ces ressources, sans
swap (`.github/actions/bound-platform`, `wftools.bounded`). Mesuré sur le Compose seul : 2,4 Gio au
repos, 4,9 Gio au démarrage, où Keycloak et l'application du royaume sont deux JVM à la fois ; la
supervision en pèse 5 %, et ses limites de mémoire (`mem_limit`) sont fixées dans `compose.prod.yaml`,
avec la mesure. Le nombre de processus de l'API (`WATERFALL_API_PROCESSES`) se choisit avec cette
mémoire : un processus tient de 0,6 à 1,2 Go.

Le service `migrate` applique ensuite les migrations sous le rôle propriétaire avant que l'API, qui ne
tient que le rôle du service, ne démarre (#701, WF-DAT-0140) ; `keycloak-realm` applique de
nouveau le royaume de l'image, et un réglage changé à la main dans la console y revient.
L'interruption dure le temps du redémarrage.

**Le passage à PostgreSQL 18 ne garde pas les données.** La première version publiée après
`0.1.0` — et les images de `main` depuis l'EPIC qui monte les dépendances, EP-20 — passe de
PostgreSQL 16 à PostgreSQL 18, et de Redis 7 à Redis 8. Elle ne reprend pas les données d'une
plateforme 16 : ni `pg_upgrade`, ni sauvegarde prise sur la 16 dont la restauration sur la 18 soit
garantie. On retire la plateforme avec ses volumes, puis on la réinstalle et on l'amorce
(« Installer », « Amorcer ») :

```sh
docker compose -f compose.prod.yaml down --volumes
```

Toutes les données de l'installation sont perdues, comme le dit « Arrêter » ; celles de Redis et de
Garage ne se reprennent pas non plus. Si on l'oublie, la plateforme refuse de démarrer : le service
`postgres-volume`, qui lit le volume de PostgreSQL avant que le serveur ne démarre, nomme la version
des données trouvées et celle attendue, 18, et renvoie ici
(`docker compose -f compose.prod.yaml logs postgres-volume`). Il refuse de même les données de
toute autre majeure que celle de la plateforme.

Depuis l'arrivée de Prometheus (US-2880), `.env` déclare les deux capacités de l'étape 3 de
« Installer » : sans elles, la plateforme ne démarre plus, et le dit.

## Superviser

Prometheus collecte, dans le réseau de la plateforme et sur des ports qu'aucune porte ne sert, les
métriques du front et du worker (`WATERFALL_METRICS_PORT`) et celles de l'API ; il garde ses séries
quinze jours dans le volume `prometheus-data`, et ne publie aucun port. Il évalue les règles des sept
alertes de WF-OBS-0030 — un composant arrêté, une tâche en file depuis plus que le seuil, l'échec
d'une sauvegarde planifiée, de sa copie externe et d'une lecture des comptes, un espace occupé au-delà
du seuil, un taux d'erreur des requêtes au-delà du seuil sur sa fenêtre —, chacune nommée par son
code du contrat, et qui cesse avec sa cause ; et une huitième, `restoration_abandoned`, tant
qu'une restauration abandonnée garde la plateforme en maintenance (« Restaurer », #1016), que
l'écran d'état, non servi en maintenance, ne montre pas : l'écran de maintenance le dit.

Les seuils et la fenêtre sont des réglages de `.env`, livrés à quinze minutes, 85 % et 5 % sur cinq
minutes : `WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS`, `WATERFALL_STORAGE_USAGE_THRESHOLD`,
`WATERFALL_ERROR_RATE_THRESHOLD` et `WATERFALL_ERROR_RATE_WINDOW_SECONDS`. `prometheus.sh` les
écrit dans les règles à chaque démarrage de Prometheus, et refuse de démarrer, en la nommant, une
valeur qui n'en est pas une. Pour en changer un : le modifier dans `.env`, puis
`docker compose -f compose.prod.yaml up --detach --wait`, qui recrée Prometheus. Les alertes en
cours se lisent dans Prometheus lui-même :

```sh
docker compose -f compose.prod.yaml exec prometheus wget -qO- http://127.0.0.1:9090/api/v1/alerts
```

Alertmanager notifie chaque alerte par courriel, par le serveur de messagerie que `.env` nomme :
`WATERFALL_ALERT_SMTP_HOST` (`hôte:port`), l'expéditeur `WATERFALL_ALERT_SMTP_FROM` et le
destinataire `WATERFALL_ALERT_RECIPIENT`, avec `WATERFALL_ALERT_SMTP_USER` et le secret
`WATERFALL_ALERT_SMTP_PASSWORD` si le serveur demande de s'authentifier, et
`WATERFALL_ALERT_SMTP_REQUIRE_TLS=false` s'il ne parle pas TLS. Sans serveur, il ne notifie rien :
les alertes restent sur l'écran d'état et sur le tableau de bord. `alertmanager.sh` écrit sa
configuration à chaque démarrage, et refuse de démarrer, en la nommant, une valeur qui n'en est pas
une.

Grafana porte le tableau de bord de l'exploitant, livré par `grafana-dashboard.json` : les composants,
la file, les espaces, le taux d'erreur et les alertes en cours, lus sur la seule source Prometheus. Il
se sert à `https://<domaine>/grafana`, par la porte, avec son compte propre, hors de Keycloak :
`WATERFALL_GRAFANA_ADMIN_USER` (`operator` par défaut) et `WATERFALL_GRAFANA_ADMIN_PASSWORD`, sans
lequel Grafana ne démarre pas. Il ne lit ni PostgreSQL ni Redis, et n'a pas de volume : son compte
est réécrit à chaque démarrage, si bien que le mot de passe de `.env` est celui qui l'ouvre. Pendant
l'arrêt de PostgreSQL, l'alerte d'indisponibilité s'y lit toujours.

## Sauvegarder

La sauvegarde de Waterfall (WF-ADM-0150) est une tâche du worker, que demande un administrateur
(`startBackup`) et qu'il télécharge ensuite (`downloadBackup`) : le worker vide les deux bases par
le rôle de sauvegarde, membre de `pg_read_all_data`, qui ne peut ni écrire ni couper un déclencheur
(#895), et range l'archive dans le compartiment `backups` de Garage, dans le volume
`storage-data`. De chaque base, il ne vide que le schéma `public`, avec les extensions et les
grands objets : le schéma `platform` de Waterfall, où la restauration tient la maintenance, reste à
l'installation (US-2830). Keycloak doit donc garder ses tables dans `public`, où il les met par
défaut : ne réglez pas `KC_DB_SCHEMA`, ou ses tables manqueraient à la sauvegarde. `pg_read_all_data`
ne lit pas les grands objets que Keycloak écrit (`cluster_event`) : à chaque démarrage, `backup-database-role`
les rend lisibles au rôle de sauvegarde, ceux qui existent et ceux que Keycloak écrira (#4170). Une copie hors de la machine se fait en téléchargeant l'archive. L'écran des
sauvegardes de l'administration la demande et la télécharge une fois branché sur le service
(US-0440/L3).

Une sauvegarde planifiée se copie d'elle-même sur un emplacement externe — un compartiment S3 d'un
autre site, ou un partage monté — que déclare un fichier JSON, un secret, que l'API et le worker
montent tous deux (`WATERFALL_EXTERNAL_LOCATIONS_FILE` du `.env`, `external-locations.none.json`,
qui ne déclare rien, à défaut). Son format, le montage d'un partage, la copie et sa relecture hors
de la plateforme : `docs/exploitation/copie-externe.md`.

Une copie à froid des volumes reste possible, plateforme arrêtée (`down`, sans `--volumes`) :

```sh
docker run --rm -v waterfall_postgres-data:/data:ro -v "$PWD:/copy" alpine \
  tar -czf /copy/postgres-data.tar.gz -C /data .
```

et de même pour `waterfall_storage-data`. Garder aussi une copie de `.env` : ses secrets sont ceux
de l'installation.

## Restaurer

La restauration (WF-ADM-0160) se demande à l'écran des sauvegardes de l'administration
(US-0440/L3) ou par l'API (`startRestore`), la date de la sauvegarde confirmée : le service
`restore`, démarré avec la plateforme et relancé s'il s'arrête, l'exécute, et l'exploitant n'a
rien à lancer. Elle remplace les deux bases, Waterfall et Keycloak, par celles de la sauvegarde.
Pendant ce temps, la plateforme est en maintenance — l'API répond 503 et sa sonde de vie dit
`maintenance` — et toutes les sessions sont fermées, avant et après. Le journal d'audit et la liste
des sauvegardes gardent ce qu'ils tenaient, et la restauration s'y inscrit la dernière.
`keycloak-realm`, qui reste démarré, applique ensuite de nouveau le royaume de l'installation : ses
clients, leurs secrets et ses adresses viennent de `.env`, les comptes et leurs mots de passe de la
sauvegarde, et l'administrateur `admin` du royaume `master` garde `WATERFALL_KEYCLOAK_ADMIN_PASSWORD`.

Reproduire une installation, c'est installer et amorcer la cible avec son propre `.env`, puis y
déposer la sauvegarde téléchargée de la source — l'écran l'envoie par morceaux, quelle que soit sa
taille, jusqu'à la borne de l'installation — et la restaurer : la cible garde son domaine, ses
secrets et le mot de passe de l'administrateur de Keycloak, et prend de la source les comptes de
Waterfall et leurs mots de passe. Une sauvegarde d'une version plus récente que la cible est
refusée, avant que rien ne change.

Une restauration interrompue — le service arrêté, une base ou Keycloak injoignable — reprend depuis
le début, et ne lève la maintenance qu'une fois finie. Avant de garder le journal et la liste des
sauvegardes, elle attend la fin des écritures admises avant la maintenance — le verrou de vidange,
que chaque écriture de l'API et du worker prend en partage et qu'elle prend en exclusif —, et
refuse en 503 celles qui arrivent après (#2229). Elle ne tient pas la maintenance plus de quatre
heures, le délai de remise en service de WF-EXP-0050 (#1016) : après trois tentatives, ou ce délai
passé, ou une maintenance posée sans l'état de sa restauration, le service `restore` l'abandonne —
à la tentative suivante, à son démarrage ou dans la minute — et passe sa tâche en échec. Les
journaux disent pourquoi (`task.failed`, avec `reason`) :

```sh
docker compose -f compose.prod.yaml logs restore keycloak-realm
```

Ce délai n'est vérifié qu'entre deux tentatives : une tentative dont `pg_restore` pend tient la
maintenance au-delà de quatre heures, tant qu'elle ne finit ni n'échoue.

Interrompue une fois les bases sur le point d'être remplacées, une restauration peut trouver
Keycloak servant le royaume de la sauvegarde, dont les secrets ne sont pas ceux de `.env` — ses
caches vidés, ou Keycloak redémarré seul (#1017) : sa reprise fait d'abord appliquer de nouveau le
royaume de l'installation par `keycloak-realm`. Si cela échoue, le journal de `restore` le dit
(`restore.realm_not_given_back`) avec le recours, que l'exploitant applique avant la tentative
suivante — `keycloak-realm` applique le royaume de l'installation à chaque démarrage, quel que
soit l'administrateur du royaume `master` que la base de Keycloak tient :

```sh
docker compose -f compose.prod.yaml restart keycloak
docker compose -f compose.prod.yaml restart keycloak-realm
```

Abandonnée avant de toucher aux bases, une restauration les laisse telles qu'elles étaient : ce
qu'elle avait gardé est retiré, la maintenance levée, et la plateforme reprend son service.
Abandonnée une fois le remplacement des bases commencé, ou sans l'état qui dirait s'il l'était, elle
les laisse telles que la tentative les a laissées, à demi remplacées peut-être : la maintenance
est **gardée**, et rien ne la lève seul (#1016). Le journal le dit (`databases_changed` à vrai,
avec l'action à mener), l'alerte `restoration_abandoned` se déclenche, et l'écran de maintenance du
front le dit, renvoyant ici. La maintenance est la ligne de la table `platform.maintenance` de la
base `waterfall`, hors du schéma `public` que la restauration remplace : vider Redis ne la lève
pas (#956). La table `platform.restoration` nomme la tâche de la restauration, compte ses
tentatives, dit depuis quand elle tient la maintenance (`held_at`), si le remplacement des bases a
pu commencer (`caches_cleared`) et si elle est abandonnée, la maintenance gardée (`abandoned`) :

```sh
docker compose -f compose.prod.yaml exec postgres psql -U postgres -d waterfall \
  -c "SELECT task_id, attempts, held_at, caches_cleared, abandoned FROM platform.restoration"
```

Aucune commande de Waterfall ne lève cette maintenance : l'exploitant agit sur ces deux tables,
après avoir lu le journal de `restore` et corrigé la cause (Keycloak, l'espace, l'archive). Le
recours sûr est de **relancer la restauration** abandonnée : elle reprend depuis le début, avec la
même sauvegarde, trois tentatives et un nouveau délai de quatre heures, reprend ce qu'elle avait
gardé, et lève la maintenance une fois finie :

```sh
docker compose -f compose.prod.yaml exec postgres psql -U postgres -d waterfall \
  -c "UPDATE platform.restoration SET abandoned = false, attempts = 1, held_at = now()"
```

Le service `restore` la redépose dans la minute. Une maintenance posée sans l'état de sa
restauration ne se relance pas ainsi : rien ne dit quelle sauvegarde elle restaurait (sa ligne de
`platform.restoration` a un `payload` vide). Un `UPDATE` qui la remet en marche la retrouve
abandonnée aussitôt, le journal disant `no_payload` : elle ne se lève que par ce qui suit. Sinon,
après avoir vérifié que les deux bases sont utilisables — remplacées entières, ou jamais
touchées —, l'exploitant **lève la maintenance** ; ce que la restauration avait gardé reste,
qu'une restauration demandée ensuite à l'écran des sauvegardes reprend :

```sh
docker compose -f compose.prod.yaml exec postgres psql -U postgres -d waterfall \
  -c "DELETE FROM platform.restoration; DELETE FROM platform.maintenance"
```

## Les processus de l'API

L'API sert ses requêtes sur `WATERFALL_API_PROCESSES` processus (US-2230) : un par défaut pour la
production ; quatre par défaut sur la plateforme de service — celle de `make e2e-service`,
de `make measure` et de la chaîne —, où `WATERFALL_API_PROCESSES=1` revient à un processus ; et
`production.env.example` en conseille quatre ; un réglage de `.env`, qui prend effet au prochain
`up`. Ce `up` recrée aussi PostgreSQL, dont `max_connections` ne change pas à chaud : il interrompt
brièvement tout le service. Chaque processus construit son application, ouvre ses propres services —
la base, Keycloak, Redis, le stockage — et les ferme quand il s'arrête ; aucun ne garde d'un
utilisateur ce qu'un autre ignorerait (WF-ARC-0080) : une requête est servie de même par n'importe
lequel.

Chaque processus garde une réserve de quinze connexions à PostgreSQL : pour les requêtes, cinq
ouvertes et huit de plus quand elles sont toutes prises ; deux de plus, à part, pour la sonde de la
base et la lecture de son état (`/health/ready` et `/metrics`), qu'une lecture lente ne prive pas de
la sonde, et qui répondent même quand toutes
celles des requêtes sont prises. Le serveur porte les deux bases, celle de Waterfall et celle de
Keycloak, et `max_connections` doit tenir toutes les connexions à la fois. Le fichier Compose le
calcule au démarrage de PostgreSQL, à partir du même réglage :

```text
max_connections = 15 × WATERFALL_API_PROCESSES + 200
```

Les deux cents restants se comptent ainsi, chaque réserve à son plein :

| Qui | Connexions |
|---|---|
| le worker, et le `pg_dump` d'une sauvegarde | 15 + 1 |
| le planificateur : la purge et le dépôt de la lecture des comptes, qui peuvent se croiser | 15 + 15 |
| le service de la restauration : sa base, le propriétaire pendant une restauration, `pg_restore` | 15 + 15 + 1 |
| l'amorçage (`install`), lancé à la main | 15 |
| Keycloak, sa réserve par défaut (`db-pool-max-size`) | 100 |
| l'application du royaume, l'administrateur temporaire qu'elle crée | 1 |
| les connexions réservées à l'administrateur `postgres` (`superuser_reserved_connections`) | 3 |
| la marge des services d'initialisation, qui se terminent avant que l'API ne démarre | 4 |
| **total** | **200** |

À un processus, le serveur accepte 215 connexions ; à quatre, 260. Chaque connexion admise coûte
au serveur de la mémoire partagée, même inemployée — avec `max_locks_per_transaction=1024`, de
l'ordre de 300 Ko : le nombre de processus se choisit avec la mémoire de la machine, pas seulement
ses cœurs.

Le nombre se règle sur les cœurs, tant que la mémoire et les connexions tiennent. La mesure de
`docs/measures/processes.json` (`make measure` à un, quatre et huit utilisateurs, à un, deux et
quatre processus, sur un poste de 32 cœurs) dit pourquoi quatre : à huit utilisateurs qui lisent le
même projet, l'ouverture du planning passe de 4,2 s à 2,9 s puis 1,7 s, le devis de 11,2 s à 5,7 s
puis 3,1 s, et `getMe` de 374 ms à 130 ms puis 39 ms : chaque doublement gagne encore pour
l'ouverture du planning et le devis, non pour tout. À huit utilisateurs, `planning.label` passe de
2,16 s (deux processus) à 3,56 s (quatre) ; à quatre, `planning.duration` est plus lent à deux
processus qu'à un (2,47 s contre 1,77 s) — dans la dispersion des passes, versionnée avec la mesure.
Un processus tient, après huit lectures entières du projet, de 0,6 à 0,7 Go (1,2 Go quand un seul
les porte toutes) : quatre processus, 2,4 Go ; la mémoire à deux n'a pas été relevée. Le nombre de
connexions ouvertes pendant la mesure ne l'a pas été non plus : la tenue repose sur
`max_connections` = 15 × processus + 200. Le parcours de `make measure` de la référence
`reference.json` des rapports de version a été pris à un processus, et ces rapports se comparent à
lui. Au-delà de quatre, rien n'a été
mesuré : un poste qui a plus de cœurs et de mémoire monte le nombre d'un cran à la fois, et en
rejoue la mesure.

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
`WATERFALL_IMAGE_TAG` — le commit du dépôt par défaut, que `make images` construit —, désignées par
leur empreinte, comme en production. Si l'environnement donne les trois `WATERFALL_DIGEST_…` (ceux
de la publication), ce sont ceux-là, du registre de ghcr.io. Sinon l'image construite ici n'a pas
d'empreinte que Docker retrouve, et le commit d'une pull request n'est pas publié : l'essai démarre un
registre qui ne vit que le temps de l'essai (`compose.registry.local.yaml`, sur 127.0.0.1), y pousse
les trois images, lit l'empreinte que chaque envoi annonce et démarre la plateforme depuis ce
registre (`WATERFALL_REGISTRY`) par ces empreintes, puis le retire. Sous le nom
`waterfall.localhost`, il démarre la plateforme, l'amorce, vérifie la sonde de vie de l'API, que
HTTP renvoie à la même page sur l'adresse publiée, port compris, que HTTPS répond avec HSTS et les
autres en-têtes de Caddy, que la console de Keycloak et le royaume `master` répondent 404, et que le premier administrateur fixe son mot de passe par le lien, se
connecte par le front et Keycloak et que le front le nomme ; avec `WATERFALL_TRIAL_RESTORATION=1`,
il demande à l'API une sauvegarde puis sa restauration, qu'il suit par la sonde de vie jusqu'à
`ok` — la chaîne la demande, un essai sur un poste peut la laisser de côté ; puis il retire la
plateforme et ses volumes. Ses secrets viennent de l'environnement, comme `production.env.example` les nomme.

## Déployer la démonstration publique

`compose.demo.yaml` sert une maquette ouverte aux utilisateurs, sans rien de la plateforme
ci-dessus : l'image de production du front contre le faux back — Prism, qui répond avec les
exemples du contrat —, derrière Caddy et un mot de passe partagé. Ni Keycloak, ni base, ni Redis :
`WATERFALL_AUTH=mock` accorde à tout visiteur la même session, et une écriture reçoit sa réponse
sans être gardée nulle part. L'image de production n'accepte ce mode qu'avec `WATERFALL_DEMO=1`,
que le fichier pose (`frontend/src/api/server.ts`).

Les fichiers sont `compose.demo.yaml`, `Caddyfile.demo`, `mock.Dockerfile` et `demo.env.example`.
Seul Caddy publie des ports (80 et 443). Le front et Prism vivent sur un réseau interne, sans accès
à Internet, et tournent sans privilège, en lecture seule, avec une mémoire bornée.

### Installer

Sur le poste, dans le dépôt, produire le contrat que Prism sert, et le copier avec les fichiers :

```sh
make mock-spec
ssh vps 'mkdir -p ~/waterfall-demo'
scp docs/api/waterfall.mock.json deploy/compose/{compose.demo.yaml,Caddyfile.demo,mock.Dockerfile,demo.env.example} vps:~/waterfall-demo/
```

Sur la machine, le DNS de `demo.waterfall-project.pro` pointant déjà vers elle (A et AAAA) :

```sh
cd ~/waterfall-demo
mv demo.env.example .env && chmod 600 .env
docker run --rm -it caddy:2.11.9-alpine caddy hash-password   # demande le mot de passe, rend son hash
openssl rand -base64 32                                        # rend la clé des actions serveur
```

Écrire dans `.env` l'adresse de `WATERFALL_ACME_EMAIL`, le tag de `WATERFALL_IMAGE_TAG`, le hash dans
`WATERFALL_DEMO_PASSWORD_HASH`, **entre apostrophes** (ses `$` seraient sinon pris pour des
variables), et la clé dans `WATERFALL_SERVER_ACTIONS_KEY`. Puis :

```sh
sudo mkdir -p /var/log/caddy
docker login ghcr.io                                       # seulement si l'image du front n'est pas publique
docker compose -f compose.demo.yaml up --detach --build --wait
```

La démonstration désigne l'image du front par une étiquette, `WATERFALL_IMAGE_TAG`, et non par une
empreinte, à dessein : la désignation par empreinte (#3726) vise la plateforme de production et le
chart, qui gardent des données ; la maquette n'en garde aucune et ne sert qu'un front contre un faux
back.

Le compte partagé est `WATERFALL_DEMO_USER` et le mot de passe dont on a mis le hash. Sans eux,
Caddy répond 401 à toute requête, hors `/robots.txt`, qui interdit l'indexation.

### Mettre à jour

Un nouveau contrat : refaire `make mock-spec`, copier `waterfall.mock.json`, puis
`docker compose -f compose.demo.yaml restart mock`. Une nouvelle image du front : changer
`WATERFALL_IMAGE_TAG` dans `.env`, puis `docker compose -f compose.demo.yaml up --detach --wait`.
Changer le mot de passe : un nouveau hash dans `.env`, puis `up --detach` recrée Caddy.

### Ouvrir la démonstration au public

Le mot de passe est comparé en bcrypt, ce qui ralentit chaque essai, mais rien ne limite leur
nombre. Caddy écrit chaque requête dans `/var/log/caddy/access.log` ; fail2ban bannit ceux qui
accumulent les 401 :

```ini
# /etc/fail2ban/filter.d/caddy-demo.conf
[Definition]
failregex = "remote_ip":"<HOST>".*"status":401
```

```ini
# /etc/fail2ban/jail.d/caddy-demo.local
[caddy-demo]
enabled  = true
filter   = caddy-demo
logpath  = /var/log/caddy/access.log
maxretry = 10
findtime = 10m
bantime  = 1h
# Docker publie les ports hors des chaînes INPUT : le bannissement passe par DOCKER-USER, que seule
# l'action iptables sait viser (celle de Debian 13 par défaut, nftables, ne le fait pas).
banaction = iptables-multiport
chain     = DOCKER-USER
# Debian 13 lit les journaux de systemd par défaut : ici, un fichier.
backend  = auto
```

Sous Debian 13, `ufw`, `fail2ban` et `unattended-upgrades` ne sont pas installés d'office
(`apt install ufw fail2ban unattended-upgrades`), et Docker se prend dans son dépôt officiel, qui
apporte `iptables`.

Sur la machine : clés SSH seules, `ufw` ouvert sur 22, 80 et 443 (Docker contourne `ufw` pour ses
ports publiés : on n'en publie pas d'autres que ceux de Caddy), mises à jour de sécurité
automatiques. Les exemples du contrat sont ce que voit tout visiteur : aucune donnée réelle n'y
a sa place.

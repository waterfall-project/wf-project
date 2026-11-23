# Revue — Paramétrage de la plateforme : déploiement, images, Keycloak, annuaire, configuration du service

## Synthèse

Le périmètre est soigné, et nettement au-dessus de ce qu'on attend d'un Compose « de
démonstration » : aucun secret par défaut dans `compose.prod.yaml` (chaque variable est en `:?`),
aucun port de donnée publié en production (Caddy seul, 80/443), trois rôles PostgreSQL au moindre
privilège (propriétaire non superutilisateur, service, sauvegarde `pg_read_all_data`), images tierces
épinglées par empreinte, images du dépôt multi-étapes et non root, royaume Keycloak strict (clients
confidentiels, PKCE S256, ni flux implicite ni « direct access grants », `redirectUris` exacte, jeton
5 min, session 2 h/12 h, rotation du jeton de rafraîchissement, verrouillage 10 échecs/15 min,
inscription fermée), console et royaume `master` non servis par Caddy, HSTS et en-têtes posés.
La configuration que `settings.py` attend est fournie par chaque service de chaque Compose : je n'ai
trouvé aucune variable requise absente.

Aucun constat bloquant. Un constat majeur, donné comme plausible (non exécuté) : la page « mot de
passe oublié » reste offerte sur la plateforme de production, qui n'a par construction aucune
messagerie. Le reste est mineur : un mot de passe Redis qui finit dans la ligne de commande du
processus alors que les fichiers affirment l'éviter ; `realm-service` qui suppose à jamais le compte
`admin` du royaume `master` ; la lecture des comptes planifiée par un `sleep` que tout redémarrage
remet à zéro ; quelques épinglages incohérents ; et de la documentation périmée, dont `SECURITY.md`,
qui dit encore qu'aucun code n'existe.

Ce qui relève d'EP-13 n'est pas reproché (chiffrement entre services, sauvegarde planifiée et copie
externe, persistance de Redis — #956 —, limites de ressources et WF-CMP-0020, métriques, plusieurs
instances, mise à jour sans interruption, CSP et durcissement de production).

## Constats bloquants

Aucun.

## Constats majeurs

### PLD-01 — « Mot de passe oublié » offert sur une plateforme sans messagerie

- **Issue** : #4474 (EP-39), ouverte le 2026-11-21.
- **Où** : `deploy/keycloak/realm/waterfall.yaml:27` (`resetPasswordAllowed: true`) ;
  `deploy/compose/compose.prod.yaml:392-394` (« No mail server ») ; aucun `smtpServer` dans le
  royaume de l'image, aucune variable SMTP dans `deploy/compose/production.env.example` ;
  `deploy/compose/README.md:24-25`.
- **Quoi** : le royaume de l'image offre le parcours « mot de passe oublié » de Keycloak, qui envoie
  un courriel, alors que la plateforme de production livrée n'a aucun serveur de messagerie
  (WF-CMP-0030 : sans messagerie, la réinitialisation se fait par le lien qu'un utilisateur habilité
  obtient depuis Waterfall).
- **Scénario** : sur une plateforme installée par `compose.prod.yaml`, une personne clique « Mot de
  passe oublié ? » sur la page de connexion et saisit son adresse. Pour un compte existant, Keycloak
  tente l'envoi, échoue faute de serveur, et répond sa page d'erreur (« Failed to send email », 500).
  Pour une adresse inconnue, il répond « vous devriez recevoir un courriel ». Deux effets : la
  personne est menée à une impasse que rien n'explique, et la différence des deux réponses dit à
  n'importe qui, depuis Internet, quelles adresses ont un compte (énumération), ce que Keycloak
  évite justement quand la messagerie marche.
- **Proposition** : ne déclarer `resetPasswordAllowed` vrai que là où une messagerie existe — une
  variable du royaume (`$(env:…)`), fausse dans `compose.prod.yaml`, vraie dans
  `compose.service.yaml` (Mailpit), documentée dans `production.env.example` pour l'exploitant qui
  raccorde sa messagerie dans la console. Preuve : dans `test_keycloak_platform.py`, sous
  `mail_server({})`, la page de connexion ne porte plus de lien `login-actions/reset-credentials` ;
  et `wftools.production` l'affirme sur la page de connexion de l'essai.
- **Confiance** : plausible. Lu : le royaume, les deux Compose, la notice, l'absence de test du
  parcours sans messagerie (le seul test « sans messagerie » porte sur l'invitation de l'extension,
  `backend/tests/test_keycloak_platform.py:690`). Non vérifié : le comportement exact de
  Keycloak 26.8.1 à l'échec de l'envoi (connu de moi par le code de `ResetCredentialEmail`, non
  exécuté ici — aucune commande `docker`).

## Constats mineurs

### PLD-02 — Le mot de passe de Redis est dans la ligne de commande du processus

- **Issue** : #4479 (EP-39), ouverte le 2026-11-21.
- **Où** : `deploy/compose/compose.prod.yaml:162`, `deploy/compose/compose.service.yaml:123`
  (`exec redis-server --requirepass "$$REDISCLI_AUTH"`) ; l'affirmation contraire :
  `compose.prod.yaml:17-19`, `compose.service.yaml:14-15` et `:119-120` ; le test qui l'annonce :
  `backend/tests/test_platform_images.py:40-48`.
- **Quoi** : le shell lit bien le mot de passe dans l'environnement, mais `exec` le passe en
  argument à `redis-server` : il se lit dans `/proc/<pid>/cmdline`, donc par `ps` et `docker top`
  sur la machine, par tout compte local. Les en-têtes des deux fichiers disent que « ce que ces
  fichiers évitent, c'est un secret dans une ligne de commande », et le test
  `…its_command_does_not_carry_the_secret` ne regarde que le texte du Compose.
- **Scénario** : un compte sans privilège de la machine lance `ps -ef | grep redis-server`, lit le
  mot de passe, joint Redis sur l'adresse du conteneur (le pont Docker est routable depuis l'hôte)
  et lit les sessions du front, jetons compris.
- **Proposition** : donner la configuration par l'entrée standard, que `redis-server -` lit :
  `sh -c 'printf "requirepass %s\nsave \"\"\n" "$REDISCLI_AUTH" | exec redis-server -'` (ou un
  fichier écrit dans un tmpfs). Preuve : un test de la plateforme lit `/proc/1/cmdline` du conteneur
  (`docker compose exec redis cat /proc/1/cmdline`) et n'y trouve pas le secret.
- **Confiance** : confirmé (lecture ; comportement standard d'`exec` et de `/proc`).

### PLD-03 — `realm-service` suppose à jamais le compte `admin` de `master`, et remet son mot de passe à chaque démarrage

- **Issue** : #4481 (EP-39), ouverte le 2026-11-21, avec PLD-05.
- **Où** : `deploy/keycloak/realm-service.sh:113-116` ; ce que disent les fichiers :
  `deploy/compose/compose.prod.yaml:399`, `deploy/compose/production.env.example:62`,
  `deploy/compose/compose.service.yaml:396`, `docs/dev/README-fr.md:3041` ; la notice,
  `deploy/compose/README.md:106-137`.
- **Quoi** : à chaque application du royaume (chaque démarrage, chaque restauration), le script
  fixe le mot de passe de `KEYCLOAK_USER` (`admin`) à celui de `.env` ; si cela échoue,
  l'application est dite échouée (`outcome=1`, puis `exit 1`). Les commentaires et le guide disent
  au contraire que ce mot de passe « n'est lu qu'au premier démarrage » et que keycloak-config-cli
  applique le royaume avec lui — il l'applique depuis #991 sous un administrateur temporaire.
- **Scénario** : (a) l'exploitant ouvre la console comme la notice l'indique, y change le mot de
  passe d'`admin` : au redémarrage suivant il revient, sans un mot, à celui de `.env`. (b) Il suit
  le bandeau de Keycloak, qui recommande de remplacer l'administrateur d'amorçage par un compte
  permanent, et supprime `admin` : au démarrage suivant `kcadm set-password --username admin`
  échoue, `keycloak-realm` sort en 1 et redémarre en boucle, sa sonde ne passe plus, et `up --wait`
  ne démarre ni `front` ni `restore`, qui en dépendent (`compose.prod.yaml:112`, `:330`).
- **Proposition** : recréer `admin` s'il manque (ou ne pas faire de son absence un échec de
  l'application du royaume, en le journalisant), et dire dans « Administrer Keycloak » que ce compte
  et son mot de passe sont tenus par la plateforme ; corriger les quatre commentaires. Preuve : un
  test de la plateforme supprime `admin` de `master`, relance `keycloak-realm`, attend sa sonde.
- **Confiance** : (a) confirmé par lecture ; (b) plausible — non vérifié : le code de retour de
  `kcadm set-password` pour un compte absent, et la présence du bandeau en 26.8.1. Le script n'a
  aucun test propre (seuls l'essai de production et le démarrage de la plateforme l'exercent).

### PLD-04 — La lecture planifiée des comptes repart de zéro à chaque redémarrage du planificateur

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — sur EP-13 (US-2830/L2, commit
  0258a2d94), le planificateur appelle `waterfall-worker schedule` toutes les cinq minutes, et
  l'échéance de `identity_sync` se lit dans la table des tâches (`last is None or now - last >=
  interval`) : elle ne vit plus dans le processus, un redémarrage ne la repousse plus, et une
  installation neuve dépose la première lecture au premier passage.
- **Où** : `deploy/compose/compose.prod.yaml:296-298`, `deploy/compose/compose.service.yaml:250-252`.
- **Quoi** : `while sleep "$INTERVAL"; do waterfall-worker enqueue identity_sync; done` dort d'abord.
  L'échéance ne vit que dans le processus : chaque redémarrage du conteneur (mise à jour,
  `down`/`up` d'une copie à froid que la notice décrit, redémarrage de la machine) la repousse d'un
  intervalle entier, un jour par défaut.
- **Scénario** : une plateforme arrêtée chaque nuit pour sa copie à froid, ou mise à jour plus d'une
  fois par jour, ne dépose jamais la lecture des comptes ; une personne ajoutée à l'annuaire n'a de
  compte qu'à sa première connexion ou sur une lecture demandée à la main (WF-ADM-0070 : « sans
  intervention »). Sur une installation neuve, la première lecture n'a lieu qu'au bout de 24 h.
- **Proposition** : déposer d'abord, dormir ensuite (`enqueue` ne dépose rien si une lecture est en
  file ou en cours), ou dormir jusqu'à l'échéance calculée depuis la dernière lecture en base. La
  CronJob d'EP-13 (EP-03, « Worker, file et planification ») règle le cas Kubernetes, pas le Compose.
  Preuve : un test du script du planificateur avec un `sleep` doublé, qui voit le dépôt avant la
  première attente.
- **Confiance** : confirmé (lecture). La purge, à dix minutes, n'en souffre pas en pratique.

### PLD-05 — La console de Keycloak est cachée par une liste de refus, éprouvée sur deux chemins seulement

- **Issue** : #4481 (EP-39), ouverte le 2026-11-21, avec PLD-03.
- **Où** : `deploy/compose/Caddyfile.prod:56-64` ; l'essai, `tools/src/wftools/production.py:97`
  (`HIDDEN = ("/auth/admin/", "/auth/realms/master/")`).
- **Quoi** : Caddy répond 404 à `/auth/admin*` et `/auth/realms/master*`, puis envoie tout le reste
  de `/auth/*` à Keycloak. Caddy et Keycloak ne normalisent pas un chemin de la même façon : Caddy
  nettoie les `//` et la casse, mais laisse passer un segment à paramètre de matrice
  (`/auth/admin;x/master/console/`, `/auth/realms/master;x/…`), que la couche JAX-RS de Keycloak peut
  lire comme `/auth/admin/…`.
- **Scénario** : depuis Internet, `GET https://<nom>/auth/realms/master;a/.well-known/openid-configuration` :
  Caddy ne reconnaît pas le motif, Keycloak sert le royaume `master`, dont le client `admin-cli`
  accepte un mot de passe — la porte que la notice dit fermée est entrouverte (il faut encore le mot
  de passe d'`admin`, que rien ne verrouille dans `master`).
- **Proposition** : une liste d'admission plutôt que de refus — ne relayer à Keycloak que
  `/auth/realms/waterfall/*`, `/auth/resources/*` (et ce que ses pages chargent), 404 pour le reste ;
  à défaut, refuser tout chemin de `/auth/` qui contient `;`. Preuve : ajouter à `HIDDEN` les
  variantes `;`, `%3B`, `//`, casse, et les voir répondre 404 dans l'essai de production.
- **Confiance** : plausible. Lu : le Caddyfile, l'essai. Non vérifié : ce que Keycloak 26.8.1 fait
  d'un `;` dans un chemin (ses versions récentes refusent certains chemins non normalisés) — d'où un
  constat mineur, dont la preuve proposée tranche à peu de frais.

### PLD-06 — `SECURITY.md` décrit un dépôt sans code ni version

- **Issue** : #4482 (EP-39), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec PLD-09, PLD-11.
- **Où** : `SECURITY.md:5-12`, `SECURITY.md:33-34`.
- **Quoi** : la politique dit « no released version … the implementation has not started » et
  « Version : none released yet », alors que `main` porte le service en 0.3.0
  (`backend/pyproject.toml:6`), que la chaîne publie trois images à chaque fusion
  (`.github/workflows/images.yml`) et qu'une démonstration publique est décrite
  (`deploy/compose/demo.env.example:9`). Elle résume aussi WF-SEC-0020 par « sessions kept in the
  database » ; la spécification les met dans Redis (§4.5.4, WF-ARC-0040).
- **Scénario** : qui trouve une faille dans une image publiée lit qu'il n'y a « no vulnerable build
  to report against », et ne sait ni quelles versions sont suivies ni quoi signaler.
- **Proposition** : réécrire les deux premiers paragraphes et le tableau des versions (les images
  publiées, la démonstration), corriger la phrase sur les sessions. Coût : une page ; pas de test.
- **Confiance** : confirmé.

### PLD-07 — Deux empreintes pour la même image `caddy:2.11.7-alpine`

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — les quatre Compose et le manifeste
  portent la même `caddy:2.11.9-alpine@sha256:003a9780…`. US-2490/L3 (EP-28, commit b4a847bbb) a
  posé `deploy/images/Dockerfile`, une ligne par image que Dependabot suit, et un test des outils
  qui échoue dès qu'une référence d'un fichier n'est pas celle du manifeste, étiquette et empreinte.
- **Où** : `deploy/compose/compose.prod.local.yaml:21` (`sha256:d8542f48…`) ; partout ailleurs
  `sha256:e70b164d…` (`compose.prod.yaml:75`, `compose.service.yaml:429`, `compose.demo.yaml:22`).
- **Quoi** : le service `authority` de l'essai local tire une autre construction de Caddy que le
  frontal qu'il accompagne ; l'une des deux empreintes est restée en arrière d'une montée.
- **Scénario** : l'essai de production (chaîne et poste) tire et garde dans le miroir deux images
  pour une ; une montée de sécurité de Caddy faite sur un fichier laisse l'autre sur l'ancienne.
- **Proposition** : aligner l'empreinte, et tenir l'égalité par le test qui tient déjà celles de
  PostgreSQL et de Redis (`backend/tests/test_platform_images.py`), étendu à Caddy sur les fichiers
  de `deploy/compose/`. Vérifier que Dependabot (`docker-compose`, `.github/dependabot.yml`) lit bien
  `compose.prod.local.yaml`, dont le nom a deux suffixes.
- **Confiance** : confirmé pour l'écart ; la cause (Dependabot) est une hypothèse.

### PLD-08 — L'image de Keycloak : un frontal de construction non épinglé, et un JDK qui n'est pas celui que disent le commentaire et EP-20

- **Issue** : #4483 (EP-39), ouverte le 2026-11-21, avec PLD-10, PLD-12.
- **Où** : `deploy/keycloak/Dockerfile:1` (`# syntax=docker/dockerfile:1`) ;
  `deploy/keycloak/Dockerfile:15-19` (`maven:3-eclipse-temurin-26@sha256:…`, sous un commentaire
  « The JDK is 25 ») ; `docs/roadmap/EP-20-migration-des-dependances.md:366` et `:785-786`
  (« Maven 3.10.0 sur un JDK 25, épinglé par empreinte »).
- **Quoi** : (a) la ligne `syntax` fait tirer `docker/dockerfile:1` de Docker Hub à chaque
  construction, par une étiquette mobile, hors du miroir — ce que `deploy/e2e/Dockerfile:15-16`
  écarte expressément et ce qu'US-1900 voulait supprimer ; c'est du code qui exécute la
  construction. (b) L'étape `extension` part d'une étiquette `3-…-26` : un JDK 26, non LTS, sous une
  étiquette de Maven flottante, là où le critère clos d'US-1180 et le commentaire disent 3.10.0 et
  JDK 25. L'empreinte fige le contenu ; `release 21` tient la cible.
- **Scénario** : (a) Docker Hub ne répond pas (« failed to fetch oauth token », le motif
  d'US-1900) : `make build-keycloak` échoue malgré le miroir. (b) Une montée de l'empreinte passe à
  un Maven ou à un JDK d'une autre série sans que l'étiquette le dise.
- **Proposition** : retirer la ligne `syntax` (le frontal intégré lit `RUN --mount=type=cache`) ;
  revenir à `maven:3.10.0-eclipse-temurin-25@sha256:…`, ou corriger le commentaire et le critère.
  Preuve : `tools/tests/test_mirror.py` refuse une ligne `syntax` dans un Dockerfile scruté.
- **Confiance** : confirmé (lecture).

### PLD-09 — La notice fait écrire le mot de passe de l'administrateur PostgreSQL sur une ligne de commande

- **Issue** : #4482 (EP-39), ouverte le 2026-11-21, avec PLD-06, PLD-11.
- **Où** : `deploy/compose/README.md:78-80` ; repris par `deploy/compose/compose.prod.yaml:133-134`
  et `deploy/compose/production.env.example:47-48`. Accessoirement, les quatre scripts de rôles :
  `deploy/compose/waterfall-database.sql:15-16`, `keycloak-database.sql:10`,
  `service-database-role.sql:10`, `backup-database-role.sql:13-14`.
- **Quoi** : `docker compose … exec postgres psql -U postgres -c "ALTER ROLE postgres PASSWORD '<nouveau>'"`
  met le nouveau mot de passe du superutilisateur dans l'historique du shell et dans la liste des
  processus de la machine — ce que les scripts SQL voisins prennent soin d'éviter (« never from a
  command line »). Par ailleurs, un `ALTER ROLE … PASSWORD` qui échoue (rôle absent) est écrit avec
  son texte, mot de passe compris, dans le journal du serveur (`log_min_error_statement`, par
  défaut `error`) — WF-OBS-0020.
- **Scénario** : l'exploitant change le mot de passe comme la notice le dit ; il reste dans
  `~/.bash_history`.
- **Proposition** : dans la notice, `docker compose exec -it postgres psql -U postgres` puis
  `\password postgres` (haché côté client, jamais affiché) ; en tête des quatre scripts,
  `SET log_min_error_statement = panic;` (ils s'exécutent en superutilisateur). Coût : cinq lignes.
- **Confiance** : confirmé pour la notice ; plausible pour le journal (comportement documenté de
  PostgreSQL, non exécuté).

### PLD-10 — La plateforme de développement publie le front et le faux back sur toutes les interfaces

- **Issue** : #4483 (EP-39), ouverte le 2026-11-21, avec PLD-08, PLD-12.
- **Où** : `deploy/compose/compose.dev.yaml:30-31` (`"4010:4010"`), `:48-49` (`"3000:3000"`).
- **Quoi** : tous les autres Compose publient sur `127.0.0.1` ; celui-ci ouvre Prism et `next dev`
  au réseau du poste. Le front s'y veut joignable (#481, `WATERFALL_DEV_ORIGINS`) ; rien ne le
  demande pour le faux back, que `INSTALL.md:138` annonce sur `http://localhost:4010`.
- **Scénario** : sur un réseau partagé, n'importe quel poste lit le faux back et atteint le serveur
  de développement de Next d'un collègue.
- **Proposition** : `127.0.0.1:4010:4010` ; pour le front, une variable d'adresse d'écoute,
  `127.0.0.1` par défaut. Preuve : `make lint-compose` et un test des outils sur les ports publiés.
- **Confiance** : confirmé (lecture).

### PLD-11 — Commentaires et notice en retard sur le code

- **Issue** : #4482 (EP-39), ouverte le 2026-11-21, avec PLD-06, PLD-09.
- **Où et quoi** :
  - `deploy/compose/README.md:101-103` : l'amorçage « tient seul » le secret du client de
    l'amorçage ; `deploy/keycloak/realm/waterfall.yaml:167-169` : « given to the bootstrap only ».
    Les services `restore` et `keycloak-realm` le tiennent aussi, en permanence
    (`compose.prod.yaml:319`, `:435`), avec `manage-realm` (`waterfall.yaml:206-213`).
  - `backend/Dockerfile:11-12` : « the major version of the server of the platform, 16 » ; l'image
    installe le client 18 (`:44`, `:61`).
  - `backend/src/waterfall/platform/keycloak_admin.py:488` et `:498` : le comportement d'un `PUT`
    est décrit pour « Keycloak 26.5.7 » ; l'image est en 26.8.1 depuis EP-20.
  - `deploy/compose/README.md:18` et `compose.prod.yaml:377`, `:385` : le compartiment `imports` est
    créé et annoncé, mais plus rien ne le lit depuis EP-06 (un seul compartiment, trois préfixes :
    `backend/src/waterfall/platform/storage.py:103-119` ; EP-06, « Conception », l. 324-330, qui
    décide de ne pas toucher au script). Décidé, donc non reproché en soi ; la notice, elle, laisse
    croire que les fichiers d'import y vivent.
- **Scénario** : un exploitant qui évalue à qui il confie quel secret, ou qui cherche les fichiers
  d'import, lit une chose fausse.
- **Proposition** : corriger les quatre textes. Aucun risque, aucun test.
- **Confiance** : confirmé.

### PLD-12 — Trois sources de construction ou d'exécution ne sont pas verrouillées

- **Issue** : #4483 (EP-39), ouverte le 2026-11-21, avec PLD-08, PLD-10.
- **Où** : `deploy/compose/mock.Dockerfile:13-15` (`npm install --global @stoplight/prism-cli@…`) ;
  `deploy/compose/compose.dev.yaml:14-17` et `deploy/compose/compose.service.yaml:546-548`
  (`npx --yes @stoplight/prism-cli@…` au démarrage du conteneur) ; `backend/Dockerfile:29`
  (`pip install uv==0.13.7`, sans empreinte, quand `deploy/e2e/Dockerfile:25` épingle uv 0.13.8 par
  son empreinte).
- **Quoi** : la version de Prism est fixée, pas ses dépendances, résolues à chaque construction ou
  premier démarrage hors du verrou de `frontend/pnpm-lock.yaml` ; uv entre dans l'étape de
  construction de l'image `waterfall` sans vérification d'empreinte.
- **Scénario** : une dépendance transitive de Prism publiée entre deux constructions change le faux
  back de la démonstration publique sans qu'aucun fichier du dépôt ne bouge.
- **Proposition** : copier uv depuis son image épinglée (`COPY --from=ghcr.io/astral-sh/uv:…@sha256`),
  comme le fait l'image e2e ; installer Prism depuis le verrou du front (un `pnpm deploy` du seul
  paquet) plutôt que par `npm`/`npx`. Coût : modéré pour Prism ; gain : la reproductibilité que le
  reste du dépôt tient déjà. Risque à ne rien faire : faible (démonstration durcie, réseau interne).
- **Confiance** : confirmé (lecture).

## Points forts

- **Secrets** : aucun mot de passe par défaut en production ; chaque secret manquant arrête Compose
  en nommant la variable (`:?`) ; `settings.py` refuse de démarrer en nommant la variable, sans
  jamais écrire la valeur ; `SecretStr` et masque par valeur dans les journaux, mots de passe d'URL
  compris ; les scripts SQL lisent les mots de passe par `\getenv`, `storage-buckets.sh` par un
  fichier de configuration de curl, `realm-service.sh` passe tous ses secrets par l'environnement.
  Les valeurs de développement sont nommées comme telles (`development-only-…`, `chain-only-…`) et
  `development/` n'entre pas dans l'image (`deploy/keycloak/.dockerignore`).
- **Royaume** : clients confidentiels, PKCE S256, `implicitFlowEnabled` et
  `directAccessGrantsEnabled` à faux partout (y compris `admin-cli`), `redirectUris` sans joker,
  `webOrigins` vide, `fullScopeAllowed: false`, audience `waterfall-api` par mapper, pas de jeton
  hors ligne, durées de WF-SEC-0020, politique et verrouillage de WF-ADM-0140 avec le raisonnement
  écrit (`maxDeltaTimeSeconds: 899`). Le client de test à mot de passe n'existe que dans le fichier
  de développement.
- **Extension Java** : authentifie, puis autorise, puis lit ; refus par statut et code machine ;
  usage unique tenu en base (nonce, date du mot de passe) et non en mémoire ; rien n'est lu du jeton
  pour la redirection ; dépendances `provided` seules, `-Xlint:all -Werror` ; un test de plateforme
  par refus (401, 403, 404, 409, 502). Aucune exemption, aucun journal du lien.
- **Réseau** : PostgreSQL, Redis, Garage, l'API et Keycloak ne publient aucun port en production ;
  la plateforme de service publie sur `127.0.0.1` ; la démonstration isole front et faux back sur un
  réseau interne, en lecture seule, sans capacités.
- **Données** : propriétaire non superutilisateur, rôle de service sans droit de connexion avant
  son script, rôle de sauvegarde en lecture seule ; contrôle de la majeure du volume PostgreSQL
  avant démarrage ; verrou consultatif des migrations (`migrations/env.py`) et de l'amorçage.
- **Images** : multi-étapes, utilisateur 1000, fichiers à root, `.dockerignore` qui écarte `.env*`
  et les tests, clé PGDG versionnée et vérifiée par empreinte, client PostgreSQL à la majeure du
  serveur ; l'empreinte SHA-256 de `backend/pgdg.asc`, recalculée, est bien celle que
  `backend/Dockerfile:55` vérifie (`0144068502a1…`).
- **Cohérence configuration ↔ code** : chaque champ requis des classes de `settings.py` est fourni
  par le service qui les charge, dans `compose.prod.yaml` comme dans `compose.service.yaml` ; les
  variables du front (`session/settings.ts`, `startup.ts`) aussi. `INSTALL.md` : les cibles `make`,
  les fichiers et les onze variables citées existent ; la commande `sed` produit bien onze lignes
  depuis `keycloak.yml`.
- **Versions** : PostgreSQL 18, Redis 8, Keycloak 26.8.1, Python 3.14, Node 26, Caddy 2.11.7,
  Garage v2.5, Mailpit v1.33 — conformes à WF-CMP-0020 et à EP-20 (hors PLD-08).

## Couverture

- **Lu en entier** : `deploy/compose/` (les six `compose.*.yaml`, les trois Caddyfile, les quatre
  `.sql`, les deux `.sh`, `garage.toml`, les deux `.env.example`, `mock.Dockerfile`, `README.md`) ;
  `deploy/keycloak/` (Dockerfile, `.dockerignore`, `apply-realm.sh`, `realm-service.sh`,
  `realm/waterfall.yaml`, `development/*`, `extension/pom.xml`, les neuf classes Java, les
  `META-INF/services`, les `theme.properties`, les messages, `footer.ftl`) ; `deploy/openldap/` ;
  `deploy/e2e/Dockerfile` ; `backend/Dockerfile`, `backend/.dockerignore`, `frontend/Dockerfile`,
  `frontend/.dockerignore` ; `INSTALL.md`, `SECURITY.md` ; `platform/settings.py`,
  `platform/installation.py`, `bootstrap.py`, `platform/keycloak.py`, `platform/keycloak_admin.py`,
  `platform/storage.py`, `platform/logs.py`, `migrations/runner.py` ; `.github/workflows/images.yml`,
  `production.yml`, `keycloak.yml` ; `.github/dependabot.yml` ; `docs/dev/java.md` ; spec §4.3,
  §4.5, §4.6 et annexe C (lignes longues tronquées à l'affichage) ; EP-13 (objet, portée, liste des
  constats reçus).
- **Échantillonné** : le `Makefile` (cibles `service-*`, `lint-*`, `build-keycloak`, `images`,
  `production-trial`, `test-keycloak`, créneaux) ; `.github/workflows/service.yml` ;
  `tools/src/wftools/mirror.py` (début), `production.py` (par `grep`) ; les tests Java et
  `backend/tests/test_keycloak_platform.py`, `test_platform_images.py` (titres et assertions) ;
  EP-03 « Conception » (authentification, planification, déploiement, stockage, début de
  sauvegarde) ; EP-06 (décision du compartiment) ; EP-20 (par `grep`) ; `docs/dev/README-fr.md`
  « Commandes » (tableau des secrets et la plateforme de service) et « Chaîne » (début) ;
  `frontend/src/startup.ts`, `session/settings.ts`, `app/login/route.ts` (pour les variables).
- **Non lu** : `.github/workflows/front-image.yml` ; `tools/src/wftools/images.py` ;
  `deploy/keycloak/themes/…/waterfall.css` (cherché pour les ressources externes seulement) et les
  fichiers binaires du thème ; le module `restore/` et `worker/backup.py` (autre
  périmètre).
- **Non exécuté** : rien n'a été lancé (ni `docker`, ni `make`) ; les comportements de Keycloak, de
  `kcadm` et de PostgreSQL cités en PLD-01, PLD-03 (b), PLD-05 et PLD-09 sont tirés de la lecture et
  marqués « plausible ».

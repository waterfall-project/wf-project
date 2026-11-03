---
id: EP-19
titre: Rendre le dépôt et ses agents sûrs pour plusieurs livreurs à la fois sur un même poste
statut: en cours
depend_de: rien
famille: plateforme
issue: 1881
---

# EP-19 — Livreurs en parallèle

## Objet

Le pilote ne lance aujourd'hui qu'un livreur à la fois (`docs/dev/agents.md`, « Le pilote ») :
le poste s'est effondré trois fois sous les tests de plusieurs agents (2026-10-19, 21 et 22).
L'auteur attend une machine qui doit en porter au moins quatre. Or le dépôt suppose partout un
seul agent par poste : un verrou exclusif pour les exécutions lourdes, des ports et des noms de
conteneurs fixes, des services de test démarrés à la main, deux worktrees au plus, un tableau de
suivi réécrit sans précaution, et rien qui empêche une session d'arrêter par motif le
`make check` d'une autre (`pkill -f "^make check"`, 2026-11-03). EP-19 rend le dépôt et ses
agents sûrs pour N livreurs simultanés, N réglable. N vaut 1 par défaut : sur le poste actuel,
rien ne change tant que l'auteur ne le relève pas.

Il vient avant EP-05 (décision de l'auteur du 2026-11-03) : il est court, EP-05 profitera du
parallélisme, et EP-05 touche le Makefile, `make e2e-service` et `compose.service.yaml`, qu'EP-19
réécrit. Les US n'ont pas d'acteur du §3.1.3 : leur bénéficiaire est celui qui développe,
personne ou agent.

## Ce qui en fait partie

- un hook `PreToolUse` du projet (`.claude/settings.json`) qui refuse les arrêts de processus et
  de conteneurs par motif, et la règle qui le dit dans `docs/dev/agents.md` ;
- les exécutions lourdes du Makefile admises N à la fois, `test-tools` compris, chacune sur sa
  part des processeurs ;
- un créneau par worktree de lot : ses ports, ses projets Compose, ses étiquettes d'images, son
  journal de `make check`, distincts de ceux des autres créneaux ;
- les services de test d'un lot — PostgreSQL, Redis, stockage objet — démarrés et retirés par le
  Makefile, sur les ports et sous les noms de son créneau ;
- le pilote qui lance jusqu'à N livreurs, sans jamais dépasser N sur le poste, et sans lancer
  ensemble deux lots que le plan dit incompatibles ; le cadreur qui le dit ; le tableau de suivi
  écrit par `make tracking` ; la limite des worktrees portée à N + 1 ;
- le guide, les règles communes, les agents, le skill `pilote`, le README de la roadmap et les
  gabarits d'issues mis d'accord avec ce qui précède, et la liste des étapes qui éprouve N = 4 à
  l'arrivée de la machine.

## Ce qui n'en fait pas partie

- relever N : c'est l'auteur qui le fait, dans son profil, sur la nouvelle machine, après l'essai
  à N = 4 que le guide décrit ;
- la chaîne : chaque runner de GitHub Actions est seul sur sa machine, N y vaut 1, et ses
  services restent ceux de ses workflows ;
- `make dev` et `make mock` lancés à la main, et l'essai de la plateforme de production
  (`make production-trial`), que seule la chaîne joue : ils gardent leurs ports et leurs noms, et
  l'essai refuse de tourner hors du créneau 0 (décision de l'auteur du 2026-11-03) ;
- deux lots de deux EPIC différents qui touchent les mêmes fichiers : c'est l'ordre des EPIC qui
  les sépare (README de la roadmap, « Ordre des EPIC »), pas le pilote ;
- la consommation du forfait, que N livreurs multiplient par N : une décision de l'auteur au
  moment de relever N ;
- la version de PostgreSQL : les services de test prennent celle de la plateforme, 16, à l'image
  épinglée des Compose. Le `pg_restore` 17 du poste actuel ne restaure pas sur un serveur 16
  (#982) : les tests des restaurations y échouent, et le guide le dit, jusqu'à l'EPIC de montée de
  version des dépendances que l'auteur prévoit (décision de l'auteur du 2026-11-03), sans
  contournement par un serveur 17.

## Exigences réalisées

Aucune : EP-19 est l'outillage du dépôt, comme EP-01. Ses US portent « aucune — outil du
dépôt », et leurs critères sont propres à l'US.

## Opérations du contrat

Aucune.

## Préalables

Rien : EP-18 est livré.

## Définition de fini

- `make check BASE=origin/main` passe sur `epic/EP-19`, ainsi que `make roadmap` et
  `make readmes` ;
- dans une session de ce dépôt, `pkill -f "^make check"` est refusé avant d'être exécuté, avec la
  règle qui le dit ;
- à N = 1, ce qui se voit est inchangé : une exécution lourde à la fois, le dépôt principal sur
  les ports d'aujourd'hui, la chaîne sur ses services ;
- `make test-tools` éprouve, à N = 2, l'admission de deux exécutions lourdes sur trois, la prise
  de deux créneaux sur trois demandés, et qu'aucun port n'appartient à deux créneaux ;
- à la main, sur le poste actuel, à `WATERFALL_SLOTS=2` : deux worktrees, chacun son créneau,
  lancent en même temps `make e2e TESTS=<un fichier>` puis `make test-back TESTS=<un fichier>`,
  chacun sur ses services, et les deux passent ; `make slots` les montre, `make slot-release`
  retire leurs conteneurs ;
- le guide décrit l'essai à N = 4 que l'auteur jouera à l'arrivée de la machine, hors d'EP-19.

## Constats reçus

Aucun.

## Conception

### Ce qui change, et ce qui ne change pas

Quatre pièces neuves, toutes des outils du dépôt : un garde des commandes des agents
(`tools/src/wftools/guard.py`), un outil des créneaux (`tools/src/wftools/slots.py`), un Compose
des services de test (`deploy/compose/compose.test.yaml`), un outil du tableau de suivi
(`tools/src/wftools/tracking.py`). Le reste est une modification : le Makefile,
`compose.service.yaml` (le nom de l'image de Keycloak), la configuration de Vitest et de
Playwright, `wftools.frontimage` (l'étiquette de son image), les agents, le skill `pilote`,
`docs/dev/agents.md`, le guide et sa traduction, le README de la roadmap et sa traduction, deux
gabarits d'issues, `.gitignore` et `REUSE.toml`. Aucune table, aucune migration, aucun module du
noyau, aucune opération du contrat, aucun workflow.

Ce qui reste vrai partout : la chaîne ne voit pas de différence — N y vaut 1, ses variables
`WATERFALL_TEST_*` l'emportent, ses runners sont des dépôts principaux, donc au créneau 0 — et le
dépôt principal garde les ports et les noms d'aujourd'hui.

### Le garde des commandes (US-1080)

- **Où et comment** : `.claude/settings.json`, nouveau, déclare un hook `PreToolUse` de matcher
  `Bash`, de commande `python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/guard.py"`. Le script ne
  dépend que de la bibliothèque standard et n'importe aucun autre module de `wftools` : il tourne
  sans environnement synchronisé, dans un worktree neuf comme ailleurs. Il lit le JSON du hook
  sur son entrée, et refuse par le code 2, la raison sur sa sortie d'erreur ; sinon il ne dit rien
  et rend 0. Les tests l'importent comme `wftools.guard`. `.claude/settings.json`, qui ne peut
  porter de commentaire, est déclaré dans `REUSE.toml`.
- **L'analyse** : la ligne est découpée par `shlex` (ponctuation `;`, `&`, `|`, `(`, `)`) en
  commandes simples ; le contenu de chaque `$( )`, de chaque paire d'accents graves et de
  l'argument de `bash -c`, `sh -c` ou `zsh -c` est analysé de même, récursivement. Devant le mot
  de commande se retirent les affectations `NOM=valeur` et les préfixes `sudo`, `env`, `nohup`,
  `nice`, `timeout <durée>`, `time`, `command`, `exec`, avec leurs options ; derrière `xargs`, la
  commande lancée est analysée, sa cible venant du tube. Le mot de commande se compare par son
  nom de base (`/usr/bin/pkill` est `pkill`). Une ligne que `shlex` ne découpe pas — guillemet
  ouvert — est refusée si l'un des mots interdits y figure, et passe sinon.
- **Ce qui est refusé** :
  - `pkill`, `killall` ;
  - `kill` lancé par `xargs`, ou dont une cible n'est pas un entier écrit en chiffres, ou vaut
    `-1`, `0` ou `-0` ; la première option qui commence par `-` est le signal (`-9`, `-TERM`,
    `-s TERM`), `--` clôt les options, et une cible négative autre que `-1` est le groupe d'un
    processus, permise ;
  - `docker rm`, `docker stop`, `docker kill` et leurs formes `docker container …` dont une cible
    porte `$`, un accent grave ou un joker, qui sont lancés par `xargs`, ou qui portent
    `--filter` ; une cible permise est un nom ou un identifiant littéral ;
  - `docker … prune`, quel qu'en soit l'objet (`system`, `container`, `volume`, `image`,
    `network`, `builder`) ;
  - `docker compose … down`, `stop`, `kill` et `rm`, et `docker-compose` de même : le Makefile
    seul arrête une plateforme, sous le nom de projet de son créneau ;
  - `rm` ou `unlink` d'un chemin qui passe par un répertoire `.git` et finit par `.lock`.
- **Ce qui passe** : tout le reste, et notamment `kill 12345`, `kill -TERM 12345 12346`,
  `kill -- -12345`, `docker rm -f wf-s3-pg`, `docker stop <identifiant>`, `git worktree prune`,
  toute commande `make`.
- **Le message** : la règle (« un agent n'arrête que ce qu'il a lancé, par son PID ou par un nom
  propre à son lot ; jamais par motif »), la forme refusée, et ce qu'il faut faire : `kill <PID>`
  de ce qu'on a lancé, `make test-services-down`, `make service-down`, `make slot-release`.
- **Mesure d'attente**, hors du dépôt et faite par l'auteur : des règles `permissions.deny` dans
  `~/.claude/settings.json` (`Bash(pkill:*)`, `Bash(killall:*)`), qui protègent dès aujourd'hui
  les deux dépôts du poste contre les formes simples. EP-19 se livre d'un bloc (décision de
  l'auteur du 2026-11-03) : le hook ne protège la session du dépôt principal qu'après la fusion
  dans `main`, et celle d'un EPIC en cours qu'après que sa branche a repris `main`.

### Les exécutions lourdes (US-1090)

- **L'outil** : `tools/src/wftools/slots.py`, bibliothèque standard seule, lancé par
  `python3 tools/src/wftools/slots.py`, sans `uv` : le travail `back` de la chaîne n'a pas
  l'environnement des outils, et le Makefile l'appelle à chaque exécution lourde. Les tests
  l'importent comme `wftools.slots`.
- **N** : `WATERFALL_SLOTS`, de l'environnement, 1 par défaut ; refusé s'il n'est pas un entier
  de 1 à 9 (les blocs de ports, ci-dessous ; accord de l'auteur du 2026-11-03). Le même N borne
  les exécutions lourdes et les livreurs ; les séparer reste possible quand on aura mesuré sur la
  nouvelle machine, par un second réglage, sans rien changer d'autre.
- **L'admission** : N fichiers de verrou dans `$XDG_RUNTIME_DIR` (`/tmp` à défaut) ; le premier
  est `waterfall-heavy.lock`, celui d'aujourd'hui, de sorte qu'un dépôt dont le Makefile n'a pas
  EP-19 — celui d'EP-17 — compte dans le premier créneau ; les suivants `waterfall-heavy.2.lock`
  à `waterfall-heavy.<N>.lock`. L'outil prend le premier libre par `fcntl.flock` sans attendre,
  et, tous pris, réessaie chaque seconde après l'avoir dit une fois. Il garde le verrou dans son
  propre processus et lance la commande en enfant, sans lui transmettre le descripteur, en lui
  relayant les signaux, et rend son code : un serveur resté derrière ne garde pas le créneau.
- **Le Makefile** : `heavy` devient `python3 tools/src/wftools/slots.py run --heavy --`, sauf
  avec `TESTS`, comme aujourd'hui ; `test-tools` passe par lui.
- **La part des processeurs** : l'outil pose `WATERFALL_PROCESSORS`, le nombre de processeurs
  divisé par N, au moins 1. pytest prend `-n $(WATERFALL_PROCESSORS)` au lieu de `-n auto`
  (back : toujours huit au plus) ; `frontend/vitest.config.ts` et `frontend/playwright.config.ts`
  lisent `WATERFALL_PROCESSORS` au lieu de `availableParallelism()` quand il est posé, et
  `WORKERS` l'emporte toujours. À N = 1, la part est le poste entier : rien ne change.

### Les créneaux de worktree et leurs ports (US-1100)

- **Un créneau par worktree** : un registre, `$XDG_RUNTIME_DIR/waterfall-slots/`, un fichier
  `<i>` par créneau pris, qui contient le chemin du worktree (`git rev-parse --show-toplevel`) et
  l'instant de la prise. `slots.py claim` — `make slot` — prend, sous un verrou exclusif du
  registre, le créneau qui nomme déjà ce worktree, ou le plus petit de 1 à N qui est libre ; un
  créneau dont le worktree n'existe plus est libre, et avant de le rendre, l'outil en retire les
  projets Compose (`down --volumes`). Tous pris, il échoue en listant les porteurs. `release` —
  `make slot-release` — retire les projets Compose du créneau, volumes compris, puis libère le
  fichier ; `list` — `make slots` — écrit N, puis chaque créneau pris et son worktree, pour tout
  le poste.
- **Le créneau d'une commande** : `slots.py which` rend celui du worktree courant, ou 0. Le dépôt
  principal est au créneau 0. Dans un worktree lié sans créneau, une cible qui en a besoin — les
  services de test, la plateforme de service, les parcours, l'image du front — échoue en disant
  `make slot`.
- **Les ports** : au créneau 0, ceux d'aujourd'hui, et 20000 à 20002 pour les services de test,
  qui sont neufs. Au créneau i de 1 à 9, le bloc `20000 + 100·i` :

  | Décalage | Port |
  |---|---|
  | 0, 1, 2 | PostgreSQL, Redis, Garage des services de test |
  | 10, 11 | PostgreSQL, Redis de la plateforme de service (`WATERFALL_POSTGRES_PORT`, `WATERFALL_REDIS_PORT`) |
  | 12, 13, 14, 15 | API, Keycloak, Mailpit, proxy de Prism (`WATERFALL_API_PORT`, `WATERFALL_KEYCLOAK_PORT`, `WATERFALL_MAILPIT_PORT`, `WATERFALL_PROXY_PORT`) |
  | 20 | faux back des parcours (`E2E_API_PORT`) |
  | 40 à 79 | fronts des parcours, un par worker (`E2E_FRONT_PORT` = décalage 40) |

  Le Makefile les exporte vers ses cibles quand l'environnement ne les donne pas ; Compose et
  Playwright les lisent déjà. Les ports de 20000 à 20999 sont sous la plage des ports éphémères
  de Linux (32768 et au-delà).
- **Les noms** : au créneau i ≥ 1, les projets Compose `waterfall-service-s<i>` et
  `waterfall-test-s<i>` (`-p`), les images `waterfall-keycloak-s<i>` (`KEYCLOAK_IMAGE`, lue par
  `compose.service.yaml` sous `WATERFALL_KEYCLOAK_IMAGE`) et `waterfall-front:check-s<i>`
  (`WATERFALL_FRONT_CHECK_IMAGE`, lue par `wftools.frontimage`) ; au créneau 0, les noms
  d'aujourd'hui, et `waterfall-test`.
- **L'essai de production** : hors des créneaux, ports 80 et 443 et projet
  `waterfall-production-trial` inchangés ; `make production-trial` échoue d'emblée, en le disant,
  quand `slots.py which` rend un autre créneau que 0 (décision de l'auteur du 2026-11-03).
- **Le journal de `make check`** : `.waterfall/check.log` dans le worktree ; `.waterfall/` entre
  dans `.gitignore`.

### Les services de test par créneau (US-1110)

- **Le Compose** : `deploy/compose/compose.test.yaml`, trois services : `postgres` (l'image de
  la plateforme, PostgreSQL 16, même empreinte que `compose.service.yaml`,
  `POSTGRES_HOST_AUTH_METHOD=trust` comme la chaîne, données en `tmpfs`), `redis` (l'image de la
  plateforme), `storage` (Garage, l'image et `garage.toml` de la plateforme, une clé et un secret
  propres aux tests, comme la chaîne). Ports publiés sur `127.0.0.1` seulement, ceux du créneau.
  Chacun a son contrôle de santé.
- **Les cibles** : `make test-services` (`up --detach --wait`, qui ne fait rien de plus quand ils
  tournent) et `make test-services-down` (`down --volumes`), sous le projet du créneau.
- **Leur emploi** : `slots.py run --services db,redis,storage` (back) ou `--services redis`
  (front), une fois le créneau lourd pris quand il y en a un : pour chaque service dont la
  variable `WATERFALL_TEST_*_URL` n'est pas déjà posée, il lance `make test-services` et pose la
  variable sur le port du créneau, puis lance la commande. `test-back`, `coverage-back`,
  `test-front` et `coverage-front` passent par lui, `TESTS` compris. Ce qu'on a retiré pendant
  l'attente est donc redémarré avant les tests.
- **La version de PostgreSQL** : celle de la plateforme, 16. Le guide, « Un test contre le
  stockage objet », dit que sur un poste dont le client est plus récent que le serveur — le
  poste actuel, client 17 — les tests des restaurations échouent (#982), jusqu'à l'EPIC de
  montée de version des dépendances ; aucun contournement.
- **La fin du lot** : `make slot-release`, à l'étape « Ne rien laisser derrière le lot »
  d'`epic-deliverer`, retire les services de test et la plateforme de service du créneau.

### Le pilote, le cadreur et le tableau de suivi (US-1120)

- **Le bornage commun** : les créneaux sont le verrou commun à tous les pilotes du poste, quel
  que soit leur dépôt (décision de l'auteur du 2026-11-03) ; un pilote par EPIC, comme
  aujourd'hui. À chaque réveil, le pilote lit `make slots` et lance autant de livreurs qu'il a de
  lots prêts et de créneaux libres. Le livreur prend son créneau (`make slot`) avant tout
  travail ; s'il échoue — un autre pilote l'a pris entre-temps —, il rend la main avec le relevé
  « aucun créneau libre », que le pilote traite comme une limite d'usage : il retentera au
  réveil suivant. Le pilote nomme toujours le lot qu'il confie.
- **« Pas avec »** : une colonne du tableau de suivi et un champ du gabarit d'un lot, qui
  nomment les lots de l'EPIC avec lesquels celui-ci ne se livre pas en même temps. Le cadreur la
  remplit, au plan de lots, pour deux lots qu'aucune dépendance ne sépare et qui touchent un même
  fichier ; elle est symétrique. Le pilote ne lance pas un lot dont un lot « pas avec » tourne.
- **Les worktrees** : le pilote signale plus de N + 1 worktrees dans son dépôt, dépôt principal
  compris.
- **`make tracking`** : `wftools.tracking`, par `gh`. Sous un verrou du poste propre à l'issue
  (`$XDG_RUNTIME_DIR/waterfall-tracking-<issue>.lock`), il relit le corps de l'issue de l'EPIC
  juste avant d'écrire, change ce qu'on lui demande, et réécrit le corps :
  `make tracking ISSUE=<n> LOT=<identifiant> [STATE=…] [PR=…] [MODEL=…]`, `US=<identifiant>
  STATUS=…`, `FINDING=<n> ATTACHED=… DECISION=…` (ajouté, ou retiré quand il est fermé). Il
  refuse une ligne qu'il ne trouve pas, et ne touche à rien d'autre. Les agents ne réécrivent
  plus le corps eux-mêmes.
- **Les textes** : `docs/dev/agents.md` (« Le pilote » : jusqu'à N livreurs, la raison de la
  règle gardée ; « Comment le travail se fait » : la règle des arrêts, `make tracking`), le skill
  `pilote`, `epic-deliverer` (prendre et rendre son créneau, `make tracking`, toujours un lot
  nommé), `epic-framer` (« Pas avec »), `python-developer` et `typescript-developer` (le journal
  de `make check`, les services de test par le Makefile), le README de la roadmap et sa
  traduction (« Suivi sur GitHub »), `04-epic.yml` et `06-lot.yml`, et le guide, qui décrit
  l'essai à N = 4.

### Ordre de construction

1. US-1080, le garde : il ne dépend de rien ;
2. US-1090, l'admission des exécutions lourdes : crée `slots.py` ;
3. US-1100, les créneaux : étend `slots.py`, réécrit les ports et les noms ;
4. US-1110, les services de test : sur les ports et sous les noms des créneaux ;
5. US-1120, le pilote : il s'appuie sur `make slot`, `make slots` et `make slot-release`.

Le Makefile est dans US-1090 à US-1110, `docs/dev/agents.md` dans US-1080 et US-1120 : les US se
suivent.

### Décisions

| Décision | Option écartée, et pourquoi |
|---|---|
| Le garde, un script de la bibliothèque standard lancé par `python3` | `uv run --project tools` : un worktree neuf synchroniserait à la première commande, et un hook qui échoue autrement que par le code 2 laisse passer ; un script shell : découper une ligne de shell en shell |
| Il refuse les cibles calculées, et aussi `docker … prune`, `docker compose … down` hors du Makefile et `rm` d'un verrou de git (auteur, 2026-11-03) | une liste des noms permis par lot : le garde ne sait pas à quel lot appartient une session ; les quatre formes de la demande seules : `volume prune` efface les bases des autres créneaux, `compose down` sans le projet du Makefile vise la plateforme du dépôt principal, et les worktrees partagent les verrous des références |
| EP-19 se livre d'un bloc ; mesure d'attente dans `~/.claude/settings.json`, par l'auteur (2026-11-03) | une fusion anticipée d'`epic/EP-19` dans `main` : `main` ne reçoit qu'un EPIC livré (README de la roadmap, « Branches ») |
| `slots.py`, de la bibliothèque standard, lancé par `python3` | par `uv run` : le travail du back de la chaîne, qui passe par la même cible, n'a pas l'environnement des outils |
| N fichiers de verrou, le premier celui d'aujourd'hui, le verrou gardé par l'outil et non hérité | un compteur dans un fichier : un processus tué le laisse faux ; un seul nom neuf : le dépôt d'EP-17, sur l'ancien Makefile, ne serait plus compté |
| Un seul N pour les exécutions lourdes et les livreurs, et 1/N des processeurs par exécution (auteur, 2026-11-03) | deux réglages d'emblée : rien n'est encore mesuré ; laisser chaque exécution prendre le poste entier : l'effondrement venait de la mémoire de N exécutions qui croient chacune avoir le poste |
| Un créneau par worktree, pris explicitement, rangé dans `$XDG_RUNTIME_DIR`, libéré quand son worktree disparaît | par branche de lot : les worktrees du harnais démarrent en tête détachée ; par empreinte du chemin : des collisions ; par variable d'environnement : l'outil `Bash` ne la garde pas d'une commande à l'autre ; une prise automatique : un créneau pris par un worktree que le pilote ne connaît pas |
| L'essai de production hors des créneaux, et refusé hors du créneau 0 (auteur, 2026-11-03) | un bloc de ports par créneau pour lui : seule la chaîne le joue, et un worktree de lot qui le lancerait prendrait les ports 80 et 443 du poste |
| Des blocs de ports neufs, `20000 + 100·i`, le créneau 0 inchangé, N ≤ 9 (auteur, 2026-11-03) | décaler les ports d'aujourd'hui : 4010 + 100 = 4110, le faux back d'un créneau sur celui des parcours d'un autre ; des ports tirés au hasard : le royaume doit connaître l'adresse du front avant son démarrage |
| Des services de test à eux, à la version de la plateforme, démarrés par l'outil une fois le créneau lourd pris, en `tmpfs` | démarrés par l'agent : les ratés d'EP-18 ; le PostgreSQL de la plateforme de service : les tests suivraient la vie de `e2e-service` ; un serveur 17 pour le client du poste : écarté par l'auteur (2026-11-03), la version relève de l'EPIC de montée des dépendances |
| Les créneaux, verrou commun à tous les pilotes ; un pilote par EPIC (auteur, 2026-11-03) | un pilote pour plusieurs EPIC : ne borne pas le dépôt d'à côté |
| « Pas avec », rempli par le cadreur | le pilote juge les fichiers : il ne lit aucun diff |
| `make tracking`, qui relit sous un verrou du poste (auteur, 2026-11-03) | relire après avoir écrit et refaire : deux livreurs se réécrivent encore entre la relecture et l'écriture |
| La preuve à N = 2 sur le poste actuel ; N = 4 à l'arrivée de la machine, hors d'EP-19, par une liste d'étapes du guide (auteur, 2026-11-03) | tout reporter à la machine : EP-19 ne pourrait pas être livré avant elle |

---

## US-1080 — Aucun agent n'arrête ce qu'un autre a lancé

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1882

**En tant que** développeur, **je veux** qu'un agent ne puisse arrêter un processus ou un
conteneur que par son PID ou par un nom propre à son lot, **afin qu'**une session n'interrompe
jamais le `make check` d'un livreur d'un autre EPIC, comme `pkill -f "^make check"` a pu le
faire le 2026-11-03.

**Critères d'acceptation.**

- propre à l'US : un hook `PreToolUse` sur l'outil `Bash`, déclaré dans `.claude/settings.json`
  du projet, refuse avant son exécution toute commande qui contient `pkill` ou `killall` ;
- propre à l'US : il refuse un `kill` dont une cible n'est pas un PID écrit en chiffres — une
  substitution (`kill $(pgrep make)`), une variable (`kill $pid`), un nom —, un `kill` lancé par
  `xargs`, et un `kill` qui vise `-1` ou `0`, tous les processus de l'utilisateur ou de son
  groupe ;
- propre à l'US : il refuse `docker rm -f`, `docker stop` et `docker kill` dont la cible vient
  d'une substitution, d'un tube, de `xargs` ou d'un filtre (`$(docker ps -q)`,
  `docker ps -q | xargs docker stop`, `--filter`) ;
- propre à l'US : il refuse `docker … prune`, `docker compose … down` lancé hors du Makefile, et
  `rm` d'un verrou de git (`.git/…/*.lock`) ;
- propre à l'US : le refus vaut où que la commande se trouve dans la ligne — après `;`, `&&`,
  `||` ou `|`, dans `$( )` ou des accents graves, sous `bash -c` ou `sh -c`, derrière `sudo`,
  `env`, `timeout`, `nohup` ou `xargs` ;
- propre à l'US : il laisse passer `kill 12345`, `kill -TERM 12345 12346`, `kill -- -12345` (le
  groupe d'un processus lancé), `docker rm -f <nom littéral>`, `docker stop <nom littéral>`,
  `git worktree prune`, et toute commande `make` ;
- propre à l'US : le refus dit la règle enfreinte et ce qu'il faut faire à la place — arrêter
  par son PID ce qu'on a lancé, ou par la cible du Makefile qui retire les services de son lot ;
- propre à l'US : chaque forme refusée et chaque forme permise ci-dessus a son test, dans les
  tests des outils du dépôt ;
- propre à l'US : `docs/dev/agents.md` dit la règle — un agent n'arrête que ce qu'il a lancé, par
  son PID ou par un nom propre à son lot, jamais par motif ; un verrou de git ne se supprime
  pas, la commande se relance —, et le hook qui la tient.

**Notes de réalisation.**

Le hook ne protège une session qu'une fois `.claude/settings.json` présent dans le dépôt où elle
s'est ouverte : celle du dépôt principal sur `main` après la livraison d'EP-19, celle d'un EPIC
en cours une fois que sa branche a repris `main` (README de la roadmap, « Branches »). En
attendant, l'auteur pose à la main des règles `permissions.deny` dans `~/.claude/settings.json`
(« Conception »).

**Hors périmètre.**

Ce que lance une commande `make` ou un script : le hook ne voit que la ligne que l'agent écrit,
et le Makefile n'arrête que ce qu'il a lui-même démarré.

---

## US-1090 — Les exécutions lourdes passent N à la fois

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1883

**En tant que** développeur, **je veux** que le poste admette N exécutions lourdes à la fois,
N réglable et 1 par défaut, chacune sur sa part des processeurs, **afin que** plusieurs livreurs
avancent ensemble sans que le poste s'effondre sous leurs tests.

**Critères d'acceptation.**

- propre à l'US : `WATERFALL_SLOTS`, lu de l'environnement — le profil de l'utilisateur —, dit
  combien d'exécutions lourdes passent à la fois sur le poste, tous dépôts et worktrees
  confondus ; absent, il vaut 1 ; une valeur qui n'est pas un entier de 1 à 9 est refusée en le
  disant ;
- propre à l'US : les exécutions lourdes d'aujourd'hui — les tests entiers et la couverture du
  back et du front, la construction du front pour la production, les parcours de bout en bout —
  et `make test-tools` attendent un créneau libre parmi N, puis le gardent jusqu'à leur fin ; une
  exécution d'un seul fichier (`TESTS`) n'attend pas, comme aujourd'hui ;
- propre à l'US : à N = 1, le créneau est le verrou d'aujourd'hui,
  `$XDG_RUNTIME_DIR/waterfall-heavy.lock` : un dépôt dont le Makefile n'a pas encore EP-19 attend
  le même ;
- propre à l'US : un processus resté derrière une exécution lourde — un serveur — ne garde pas
  son créneau ;
- propre à l'US : à N > 1, une exécution lourde prend la N-ième part des processeurs pour ses
  workers — tests du back et des outils, tests du front, parcours de bout en bout, sauf
  `WORKERS` donné ; à N = 1, chacune garde le nombre d'aujourd'hui ;
- propre à l'US : un test des outils, à N = 2, lance trois exécutions lourdes : deux passent
  ensemble, la troisième attend que l'une finisse ;
- propre à l'US : la chaîne n'est pas changée.

**Hors périmètre.**

Une admission selon la mémoire libre : N reste un nombre que l'auteur fixe.

---

## US-1100 — Chaque lot a son créneau : ses ports et ses noms

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1884

**En tant que** développeur, **je veux** que chaque worktree de lot prenne un créneau qui lui
donne ses ports, ses projets Compose et ses étiquettes d'images, **afin que** deux livreurs
lancent au même moment les parcours de bout en bout, les tests de Keycloak ou les parcours
contre le service sans se heurter.

**Critères d'acceptation.**

- propre à l'US : `make slot` prend pour le worktree où il est lancé un créneau de 1 à N, ou
  rend celui qu'il a déjà ; il échoue en le disant quand les N sont pris ; `make slot-release`
  le rend, après avoir retiré les conteneurs et les volumes du créneau ; `make slots` liste les
  créneaux pris, sur tout le poste, avec leur worktree ;
- propre à l'US : un créneau dont le worktree n'existe plus est libre, et celui qui le reprend
  retire d'abord ce que l'ancien porteur y a laissé ;
- propre à l'US : le dépôt principal est au créneau 0 : ses ports et ses noms sont ceux
  d'aujourd'hui ; dans un worktree lié sans créneau, une cible qui en a besoin échoue en disant
  `make slot` ;
- propre à l'US : au créneau i ≥ 1, les ports des cibles du Makefile — les services de test, la
  plateforme de service (PostgreSQL, Redis, API, Keycloak, Mailpit, le proxy de Prism), le faux
  back et les fronts des parcours — sont ceux de son bloc, et ses projets Compose et ses
  étiquettes d'images (`waterfall-keycloak`, `waterfall-front:check`) portent son numéro ;
- propre à l'US : `make production-trial` refuse de tourner hors du créneau 0 — depuis un
  worktree de lot —, en le disant ; au créneau 0, il garde ses ports et son nom ;
- propre à l'US : un test des outils prouve qu'aucun port n'appartient à deux créneaux, de 0 à 9,
  et qu'à N = 2 deux créneaux sur trois demandés sont pris ;
- propre à l'US : deux worktrees, aux créneaux 1 et 2, lancent ensemble
  `make e2e TESTS=<un fichier>`, et les deux passent ;
- propre à l'US : un agent écrit la sortie de `make check` dans `.waterfall/check.log`, dans son
  worktree, que git ignore, et non plus dans `/tmp/check.log`, que deux développeurs se
  disputeraient ;
- propre à l'US : le guide (`docs/dev/README-fr.md` et `README.md`), « Commandes » et « Un
  parcours de bout en bout », dit les créneaux et leurs ports.

---

## US-1110 — Les services de test d'un lot démarrés et retirés par le Makefile

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1885

**En tant que** développeur, **je veux** que le Makefile démarre lui-même, pour mon créneau, les
services dont les tests du back et du front ont besoin, et les retire à la fin du lot, **afin
que** plus aucun livreur n'improvise ses conteneurs, et qu'aucun `make check` ne tourne sans base
parce qu'on a retiré la sienne pendant qu'il attendait son tour.

**Critères d'acceptation.**

- propre à l'US : `make test-services` démarre, pour le créneau du worktree, PostgreSQL à l'image
  épinglée de la plateforme, Redis et Garage, nommés d'après le créneau et sur ses ports, et
  attend qu'ils répondent ; relancé, il ne fait rien de plus ; `make test-services-down` les
  retire avec leurs volumes ;
- propre à l'US : `make test-back`, `make coverage-back`, `make test-front` et
  `make coverage-front` démarrent les services de leur créneau une fois leur tour venu — après
  l'attente d'un créneau lourd, pas avant — et posent `WATERFALL_TEST_DATABASE_URL`,
  `WATERFALL_TEST_REDIS_URL` et `WATERFALL_TEST_STORAGE_URL` sur eux ;
- propre à l'US : une variable que l'environnement donne déjà l'emporte, et le Makefile ne
  démarre alors pas le service qu'elle désigne : la chaîne n'est pas changée ;
- propre à l'US : le guide, « Un test contre PostgreSQL », « Un test contre Redis » et « Un test
  contre le stockage objet », dit les deux cibles et ne donne plus de `docker run` à la main ; il
  dit que, sur un poste dont `pg_restore` est plus récent que le serveur de la plateforme — le
  poste actuel, client 17, serveur 16 —, les tests des restaurations échouent (#982), jusqu'à
  l'EPIC de montée de version des dépendances ;
- propre à l'US : `epic-deliverer` retire les services de test et la plateforme de son lot, et
  rend son créneau, à l'étape « Ne rien laisser derrière le lot » (`make slot-release`).

**Hors périmètre.**

La version de PostgreSQL et le client du poste : l'EPIC de montée de version des dépendances
(« Ce qui n'en fait pas partie »).

---

## US-1120 — Le pilote lance jusqu'à N livreurs

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #1886

**En tant que** développeur, **je veux** que le pilote lance jusqu'à N livreurs ensemble, sans
dépasser N sur le poste quel que soit le nombre de pilotes, et sans lancer ensemble deux lots qui
touchent les mêmes fichiers, **afin que** la nouvelle machine serve, et que la file de fusion
n'ait plus à attraper tard un conflit que le plan savait.

**Critères d'acceptation.**

- propre à l'US : le pilote lance un livreur tant qu'un lot est prêt et qu'un créneau est libre
  sur le poste (`make slots`) ; tous pilotes et tous dépôts confondus, il ne tourne jamais plus de
  N livreurs ; il nomme toujours le lot qu'il confie ;
- propre à l'US : un livreur prend son créneau (`make slot`) avant tout travail ; s'il n'en
  trouve pas, il rend la main sans rien faire, et le pilote retente à son réveil suivant ;
- propre à l'US : le pilote ne lance jamais ensemble deux lots que le tableau de suivi dit « pas
  avec » l'un l'autre, même quand leurs dépendances le permettent ; le cadreur marque ainsi deux
  lots qu'aucune dépendance ne sépare et qui touchent un même fichier — comme US-1060 et US-1070,
  dans `api/users.py` ;
- propre à l'US : le gabarit d'un lot, le tableau de suivi du gabarit de l'EPIC et le README de la
  roadmap (« Suivi sur GitHub ») ont le champ « Pas avec » ;
- propre à l'US : `make tracking` change la ligne d'un lot, le statut d'une US ou un constat du
  tableau de suivi en relisant le corps de l'issue de l'EPIC sous un verrou du poste, juste avant
  de l'écrire ; deux appels simultanés gardent chacun leur changement ; les agents ne réécrivent
  plus le corps eux-mêmes ;
- propre à l'US : le pilote, à chaque réveil, signale plus de N + 1 worktrees, dépôt principal
  compris, au lieu de deux (#1444) ;
- propre à l'US : `docs/dev/agents.md`, « Le pilote », et le skill `pilote` disent jusqu'à N
  livreurs, N = 1 sur le poste actuel, et gardent la raison de la règle ;
- propre à l'US : le guide décrit l'essai à N = 4 de la nouvelle machine — quatre livreurs, ce
  qu'on mesure, à quoi on relève N.

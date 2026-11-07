---
id: EP-21
titre: Combler ce que deux jours à quatre livreurs ont révélé de l'outillage — tableau de suivi, arrêt d'un créneau, garde, contrôles de la chaîne, harnais des parcours
statut: en cours
depend_de: EP-19, EP-05
famille: plateforme
issue: 2225
---

# EP-21 — Livreurs en parallèle : suivi

## Objet

EP-19 a rendu le dépôt sûr pour plusieurs livreurs à la fois, et N = 4 est en service depuis le
2026-11-05 : EP-20, EP-05 et EP-04 se sont livrés à quatre livreurs les 5, 6 et 7 novembre. Ces deux
jours ont montré ce que l'outillage laisse encore à une personne. Le pilote a édité six fois à la
main le tableau de suivi, parce que `make tracking` ne sait ni ajouter la ligne d'un lot coupé ni
changer une dépendance (#2112, #1979). Un `next-server` orphelin a bloqué un créneau toute une nuit,
parce qu'aucune cible n'arrête les serveurs de l'e2e d'un créneau et que le garde, à raison, interdit
`kill` aux agents (#2198). La file de fusion a attrapé tard ce que la chaîne aurait dû voir : un
cycle d'imports entre deux interfaces du noyau (#2124), une image `restore` périmée (#2083), un
contrôle des bornes qui ignore `pattern` et `enum` (#2185). Et le harnais des parcours contre le
service laisse l'administration sur le faux back (#2199) et joue en parallèle des parcours qui
écrivent un objet unique (#2211). EP-21 comble ces manques, avec les constats d'EP-19 que ses lots
n'avaient pu reprendre (#1890, #1893, #1909, #1915) et les finitions d'outils et de guide reportées
par EP-20 et EP-22.

Il dépend d'EP-19, dont il complète les outils, et d'EP-05, dont la fusion dans `main` (#2217) porte
les fichiers que le harnais et les contrôles touchent — `frontend/e2e/mode.ts`, le projet Playwright
`shared`, le contrôle des bornes de `test_contract_declarations.py`, les modules du noyau que le
contrat d'imports ordonne. Ses lots sont petits et indépendants, pour se livrer sur les créneaux
qu'EP-04 laisse libres. Ses US n'ont pas d'acteur du §3.1.3 : leur bénéficiaire est celui qui
développe, personne ou agent, comme pour EP-19.

## Ce qui en fait partie

- `make tracking` sait écrire tout ce que le pilote écrivait à la main : la ligne d'un lot coupé,
  une dépendance changée, une US à lot unique dont la cellule cite ses constats ; et un test tient
  le gabarit de l'issue d'un EPIC d'accord avec l'outil — US-1290 (#2112, #1979, #1915) ;
- un créneau se rend entier : une cible arrête les serveurs de l'e2e du créneau, que
  `make slot-release` appelle, et les services de test d'un créneau ne se démarrent qu'une fois à la
  fois — US-1300 (#2198, #1909) ;
- le garde des commandes voit les formes d'arrêt et de suppression qu'un agent écrit sans malice, et
  suit un `cd` dans `.git` — US-1310 (#1890, #1893) ;
- la chaîne attrape ce que la file a attrapé tard : un cycle entre modules du noyau, un service du
  Compose démarré sans être reconstruit, une borne de paramètre qui s'écarte du contrat — US-1320
  (#2124, #2083, #2218, #2185) ;
- le harnais des parcours contre le service : les parcours d'administration joués contre le service
  sous un compte qui en a les permissions, les parcours qui écrivent un objet unique joués en série,
  et l'attente du verrou des rôles composés sous le délai d'un test — US-1330 (#2199, #2211, #2214) ;
- les finitions d'outils et de guide reportées par EP-20 et EP-22, et les textes que les deux jours
  ont rendus nécessaires — reprendre `main` dans une branche d'EPIC, le pilote devant les worktrees
  des livreurs rendus et sa propre session — US-1340 (#2028, #2074, #2075, #2085) ;
- les autorisations des livreurs versionnées dans `.claude/settings.json`, que chaque worktree
  reçoit — US-1350 ;
- la liste d'exemption TC001–TC003 de `ruff.toml`, un module par ligne et tenue par un test, qui
  cessait de fusionner à chaque lot ajoutant un module de routes — US-1360 ;
- le jeu de règles de la file de fusion d'une branche d'EPIC créé par une cible du Makefile, et
  vérifié par le livreur du premier lot — US-1370.

## Ce qui n'en fait pas partie

- les formes qui ne s'écrivent que pour contourner le garde : ce sont des limites connues d'US-1080
  (EP-19, « Hors périmètre ») ;
- relever N au-delà de 4 : c'est l'auteur qui le fait, selon le guide (EP-19) ;
- ce que le harnais de l'agent fait des worktrees et des sessions — les worktrees des livreurs finis
  qu'il garde verrouillés, les livreurs en vol qu'un redémarrage de la session du pilote arrête : le
  dépôt ne les commande pas ;
- les incidents de code des synchronisations entre branches d'EPIC des 6 et 7 novembre — un fichier
  de test passé au-dessus de 1 000 lignes, un test de témoin qui ne nettoyait pas ses partitions —,
  corrigés par les lots qui les ont causés ;
- la durée des tests du back d'EP-05 (`back / check`, de 4 à 14 minutes, #2157 : délai porté à 15) :
  ce sont les tests d'EP-05, pas l'outillage ;
- les leviers de l'audit de la chaîne du 2026-11-05 non encore pris — miroir des images de Docker
  Hub, cache d'Actions sous 10 Go, `installation.setup` déterministe, les tests témoin des outils,
  `.next/cache` — : EP-13, qui porte déjà #2050 et #2121 (décision de l'auteur du 2026-11-07) ; le
  cadrage ouvre le constat qui les lui renvoie ;
- la troncature des lignes de `make slots`, sans cas reproduit ;
- l'amorçage de `risk_settings.write` et `indicator_settings.write` dans le rôle « Manager »
  (`TO_SEED_BY_EP04`, #1457) : EP-04.

## Exigences réalisées

Aucune : c'est l'outillage du dépôt, comme EP-19. Ses US portent « aucune — outil du dépôt », et
leurs critères sont propres à l'US.

## Opérations du contrat

Aucune.

## Préalables

EP-19 livré ; EP-05 fusionnée dans `main` (#2217, 2026-11-07).

## Définition de fini

- `make check BASE=origin/main` passe sur `epic/EP-21`, ainsi que `make roadmap` et
  `make readmes` ;
- sur le tableau du gabarit `04-epic.yml`, `make tracking` ajoute la ligne d'un lot coupé et change
  une dépendance, et reconnaît `lot unique (#n)` ;
- dans un worktree de lot, après un `make e2e TESTS=<un fichier>` interrompu, `make e2e-down` ne
  laisse aucun processus à l'écoute sur les ports de l'e2e du créneau, et `make slot-release` rend un
  créneau sans conteneur, sans volume ni serveur ;
- dans une session de ce dépôt, `find .git -name '*.lock' -delete`, `docker volume rm $(docker
  volume ls -q)` et `cd .git && bash -c 'rm index.lock'` sont refusés avant d'être exécutés ;
- `make imports-back` refuse un import de `waterfall.core.users` depuis
  `waterfall.core.resource_settings` ; `make service-up` reconstruit l'image de `restore` ;
- `make e2e-service` joue contre le service les lectures de l'administration et de l'état sous le
  rôle « Administrateur (parcours) », et en série les parcours qui écrivent un objet unique ;
- dans un worktree neuf, un livreur met une pull request en file, édite une issue et prend son
  créneau sans qu'une personne ait à accorder une règle ;
- `make merge-queue-check EPIC=EP-05` passe, et `make merge-queue EPIC=EP-nn` crée le jeu de règles
  d'une branche d'EPIC identique, à sa branche près, à celui d'EP-05 ;
- un module de routes ajouté à `api/` sans sa ligne dans `ruff.toml` fait échouer `make test-tools`
  en le nommant ;
- les dix-huit constats reçus sont fermés, chacun par son lot.

## Constats reçus

Reportés d'EP-19 (décision de l'auteur du 2026-11-04) :

- #1890 — outil : les formes d'arrêt que le garde des commandes ne voit pas, sauf celles qui ne
  s'écrivent que pour le contourner. Restent : `find … -delete`, `find … -exec rm`,
  `mv .git/index.lock …`, `docker rmi`, `docker volume rm`, et les préfixes que le garde ne suit
  pas (`busybox`, `su -c`, `flock`, `watch`).
- #1893 — outil : le garde suit mal un `cd` dans `.git` (sous `bash -c`, par `pushd`,
  `env -C`, un chemin calculé, ou derrière `command` et `builtin` ; un `cd ..` ne remet pas l'état
  à zéro) et les abréviations des options longues (`env --ch`).
- #1909 — outil : deux démarrages concurrents des services de test d'un même créneau.
- #1915 — outil : rien n'éprouve que le tableau du gabarit d'un EPIC se modifie par
  `make tracking`.

Reportés d'EP-17 à sa livraison (rangement du 2026-11-05) :

- #1979 — outil : `make tracking` ne reconnaît une US à lot unique que si la cellule « Lot » vaut
  exactement `lot unique`, alors que le tableau d'EP-17 et le gabarit du cadreur la suivent des
  constats que le lot ferme (`lot unique (#1840)`) ; aucune US à lot unique d'EP-17 ne pouvait
  changer d'état par l'outil. Relevé à la livraison d'US-1220.

Reportés d'EP-20 à sa livraison (décisions de l'auteur du 2026-11-06) :

- #2028 — outil : finitions du test et du guide de l'amorce de l'annuaire de test — un test de
  `tools/tests/test_openldap_entrypoint.py` qui pose ses volumes par l'entrypoint du lot et recoupe un
  autre, un test et un module sans docstring, deux formulations datées du guide. Relevé par la revue
  d'US-1270/L1 (#2017) ; aucun lot d'EP-20 ne touche plus ces fichiers.
- #2074 — doc : `INSTALL.md` écrit « 3.14 » à côté de son renvoi à `tools/.python-version`, qui en
  fait foi. Remarque de la revue d'US-1270/L3 (#2019).
- #2075 — outil : `make check-tools` affiche un avertissement vide quand `tools/.python-version`
  manque, au lieu de dire que le fichier manque. Remarque de la revue d'US-1270/L3 (#2019).

Reporté d'EP-22 à sa livraison (décision de l'auteur du 2026-11-06) :

- #2085 — doc : `docs/dev/python.md`, « Les annotations sous Python 3.14 », nomme `restoration.py` et
  `tables.py` sans leur répertoire (`platform/restoration.py`, `core/users/tables.py`), alors que
  chaque objet du référentiel aura le sien. Mineur de la revue d'US-1280 (#2023), à prendre avec
  #2074 et #2075.

Reportés du pilotage d'EP-20, d'EP-05 et d'EP-04 (décision de l'auteur du 2026-11-06) :

- #2112 — outil : `make tracking` ne sait ni ajouter la ligne d'un lot coupé (`US-1270/L2b`,
  `US-0820b`, `US-0860b`, `US-0840b`), ni changer une dépendance ; le pilote a édité le corps de
  l'issue à la main, six fois en deux jours. À prendre en premier.

Reporté d'EP-05 (décision de l'auteur du 2026-11-06) :

- #2124 — outil : un cycle d'imports entre deux interfaces en paquet du noyau
  (`users.interface` ↔ `resource_settings.interface`) a échappé à import-linter et n'a été révélé
  que par la file de fusion ; un contrat import-linter interdira les cycles entre interfaces du
  noyau. Relevé par la revue d'US-0860.

Reportés d'EP-05 et de la nuit du 6 au 7 novembre (décisions de l'auteur du 2026-11-07) :

- #2083 — chaîne : `make service-up` ne reconstruit pas l'image du service `restore` (pas de
  `--build` sur sa ligne), d'où des restaurations qui échouent en local après une migration
  nouvelle ; un test du Compose vérifiera que chaque service construit l'est au démarrage.
- #2198 — outil : aucune cible n'arrête les serveurs de l'e2e d'un créneau (Next, Playwright,
  Prism), et le garde interdit `kill` aux agents : une cible par port, appelée par `slot-release`.
- #2199 — royaume : le « Manager » de `./mode` ne porte ni `users.*` ni `system_status.read`, les
  parcours d'administration ne se jouent pas contre le service ; décision : un rôle de test
  « Administrateur » du royaume de développement et un second compte des parcours (option B).
- #2185 — outil : le contrôle des bornes des paramètres de requête contre le contrat (#1873,
  `test_contract_declarations.py`) ignore `pattern`, `enum` et les paramètres absents du contrat ;
  à étendre avec les autres contrôles de conformité.
- #2211 — front : trois parcours `@shared` écrivent un objet unique — les unités de durée, les
  réglages, la correspondance des coûts réels — sans se jouer en série contre le service, et aucun
  projet Playwright ne joue en série un parcours hors de `e2e/service/` ; proposition : un projet joué
  en série (option 1). Relevé par le lot de finitions d'EP-05 (#2126).
- #2214 — front : `giveRoles` attend le verrou des rôles composés jusqu'à 120 s, plus que les 30 s
  d'un test, et deux lignes du guide dépassent 100 colonnes ; à retirer avec le rôle composé des
  parcours (#2199, #2149). Relevé par le lot de finitions d'EP-05 (#2126).

Reporté d'EP-04 (décision de l'auteur du 2026-11-07) :

- #2218 — outil : `make service-up` ne reconstruit pas l'image de restauration, qui ignore les
  migrations récentes — le même défaut que #2083, relevé par US-0970 sur le créneau 1. Décision : la
  ligne `up --build --detach --wait restore` est ajoutée par US-0990/L2 d'EP-04, qui sera dans `main`
  avant EP-21 ; EP-21 garde le test des outils qui confronte les services à `build` du Compose aux
  recettes du Makefile, et pose la ligne si elle manquait encore à sa livraison.

## Conception

### Ce qui change, et ce qui ne change pas

Aucune table, aucune migration, aucun module du noyau, aucune opération du contrat, aucun
workflow. Trois outils existants s'étendent — `tools/src/wftools/tracking.py`, `slots.py`,
`guard.py` —, un naît, `tools/src/wftools/mergequeue.py`, avec un modèle versionné
`.github/rulesets/merge-queue.json`. Le reste est une modification : le Makefile, `ruff.toml`,
`backend/pyproject.toml` (import-linter), `backend/tests/test_contract_declarations.py`,
`frontend/e2e/mode.ts`, `frontend/e2e/service/realm.ts`, `installation.setup.ts`,
`frontend/playwright.config.ts`, trois fichiers de parcours, `.claude/settings.json`,
`REUSE.toml`, les agents (`epic-deliverer`, skill `pilote`), `docs/dev/agents.md`, le guide et sa
traduction, `docs/dev/python.md`, `INSTALL.md`, `CONTRIBUTING.md`. La chaîne ne voit pas de
différence : N y vaut 1, et aucune cible neuve n'y est appelée.

### Le tableau de suivi (US-1290)

- **Trois formes nouvelles** de `wftools.tracking`, exclusives entre elles et avec `LOT`, `US`,
  `FINDING` : `--add-lot <id> --after <lot> [--depends <liste>] [--model <m>]`,
  `--replace-dependency '<ancien>=<nouveau>'`, et `--depends <liste>` avec `--lot`. Le Makefile les
  expose par `tracking_option` : `ADD_LOT`, `AFTER`, `DEPENDS`, `REPLACE_DEPENDENCY`, comme les
  autres, prises sur la ligne de commande de make seulement.
- **L'insertion** : la ligne du lot `AFTER` se trouve par `change_lot` ; la nouvelle ligne se
  construit sur l'en-tête de la table — chaque colonne par son nom, les colonnes que l'outil ne
  connaît pas à vide — et prend la fin de ligne de la ligne au-dessus ; sa cellule « Lot » est
  `L3 #<issue>` quand l'identifiant porte `/Ln`, `US-0820b #<issue>` sinon, l'issue venant d'une
  option `--issue-number`, ou absente si elle n'est pas donnée.
- **La reconnaissance** : `LOT_LABEL` devient `L\d+b?` ; un identifiant `US-nnnnb` se cherche dans
  les lignes de l'US `US-nnnn`, cellule « Lot » commençant par `US-nnnnb` ; une US à lot unique se
  reconnaît à une cellule qui commence par `lot unique` suivie de rien, d'un espace ou d'une
  parenthèse.
- **Le test du gabarit** lit `04-epic.yml` sans bibliothèque YAML : le bloc `value: |` du champ
  `tracking`, désindenté, est le corps ; il n'ajoute aucune dépendance aux outils.

### L'arrêt d'un créneau (US-1300)

- **La sous-commande** `slots.py stop-servers` — `make e2e-down` — cherche les processus à l'écoute
  sur les ports de l'e2e du créneau courant : `E2E_API_PORT` et `front_ports(slot)`. Bibliothèque
  standard seule : `/proc/net/tcp` et `/proc/net/tcp6` donnent les sockets en état `LISTEN`
  (`0A`) et leur inode ; `/proc/<pid>/fd` des processus lisibles — ceux de l'utilisateur — donne le
  PID. Chaque PID reçoit `SIGTERM` ; après cinq secondes, ceux qui écoutent encore reçoivent
  `SIGKILL`, et la cible le dit. Rien n'est cherché par nom : la lettre du garde est tenue.
- **Qui l'appelle** : `release` et `claim` (sur un créneau abandonné) l'appellent avant le retrait
  des projets Compose, sous le verrou du registre ; `make e2e-down` seul, pour un livreur dont un
  `make check-front` s'est interrompu. Au créneau 0, elle vise les ports d'avant.
- **Le verrou des services de test** : `start_test_services` tient
  `$XDG_RUNTIME_DIR/waterfall-test-services.<slot>.lock` (`flock`, bloquant, dit une fois qu'il
  attend) le temps de `make test-services`. La seconde exécution trouve les services démarrés et
  `up --wait` ne fait rien de plus.
- **Les tests** : la recherche et l'arrêt se testent sur un processus enfant à l'écoute sur un port
  éphémère, jamais sur un port d'un vrai créneau ; le verrou, par deux processus et le faux `make`
  de `test_test_services.py`.

### Le garde (US-1310)

- **Les préfixes** : `busybox` (son premier opérande est l'applet, qui devient le mot de commande),
  `chroot` (un opérande, puis la commande), `flock` (options `-w`, `-E`, `--timeout`,
  `--conflict-exit-code`… ; un opérande, le verrou ; puis la commande, ou `-c <script>` analysé comme
  `bash -c`), `su` et `runuser` (`-c <script>` analysé comme un script ; `-s`, `-g`, `-G` et leurs
  formes longues prennent un argument), `watch` (ses opérandes forment un script, que `sh -c`
  exécute : analysés comme tel).
- **Les abréviations** : `_Options.parse` reconnaît un `--mot` par la règle du préfixe unique de GNU
  sur la table des options longues de chaque préfixe ; `_SPLIT_STRING` n'énumère plus ses préfixes.
- **Les formes** : `find` dont un opérande de chemin passe par `.git` — ou précédé d'un `cd` dans
  `.git` — et qui porte `-delete` ou `-exec rm` ; `mv` et `rename` dont une source passe par `.git`
  et finit par `.lock` ; `docker rmi`, `docker image rm|remove`, `docker volume rm|remove`, jugés
  comme `_CONTAINER_STOPS` (cible calculée, tube, `xargs`, `--filter` refusés ; littéral permis).
- **Le `cd`** : `moved` est passé à `_shell` et `_eval` ; `pushd` vaut `cd` ; `env -C`, `--chdir` et
  leurs abréviations jugent leur argument comme un chemin de `cd` ; un `cd` dont le chemin porte
  `$(…)`, un accent grave ou une variable pose `moved` ; un chemin littéral qui ne passe pas par
  `.git`, `..` et `-` le retirent.
- **La taille** : `guard.py` a 600 lignes ; le lot mesure, et reste sous 1 000 ; s'il devait les
  dépasser, il le dit au relevé et la coupe se décide alors, le script n'important aucun autre module
  de `wftools`.

### Les contrôles de la chaîne (US-1320)

- **Le contrat `layers`**, dans `backend/pyproject.toml`, à côté de l'`independence` gardé :
  `containers = ["waterfall.core"]`, `layers = ["access_roles | backups | indicator_settings |
  risk_settings", "cost_settings", "users", "resource_settings"]` — le haut importe le bas, jamais
  l'inverse, et deux modules d'une même couche séparés par `|` ne s'importent pas. Le graphe du
  2026-11-07 le vérifie déjà. Un module nouveau se range dans la couche que ses imports imposent ;
  la règle écrite au guide Python : `resource_settings` ne dépend d'aucun autre module du noyau,
  les auteurs d'un objet se nomment dans `api/`.
- **Le test de complétude**, dans les tests des outils : chaque répertoire de
  `backend/src/waterfall/core/` qui a un `__init__.py` est nommé dans les `layers` du contrat, lu de
  `pyproject.toml` par `tomllib`.
- **`service-up`** : `up --build --detach --wait restore`, ligne qu'US-0990/L2 d'EP-04 écrit
  (#2218) et que le lot pose seulement si elle manque encore. Le test des outils lance
  `docker compose -f deploy/compose/compose.service.yaml --profile e2e --profile install config
  --format json` avec les valeurs de remplacement de `lint-compose` — le runner de la famille `repo`
  a Docker, `lint-compose` le lui demande déjà —, relève les services qui ont un `build`, et vérifie
  dans le texte du Makefile que chacun est nommé par une ligne `up --build` ou `build` des recettes
  `service-up`, `service-install`, `e2e-service`.
- **`drifting`** : `Bounds` porte aussi `pattern`, `enum` (ensemble), `minItems`, `maxItems` ; un
  paramètre servi dont le contrat n'a pas le couple (opération, nom) est rapporté
  « not in the contract ». Le test sur contrat de brouillon s'étend d'un cas par mot-clé.

### Le harnais des parcours (US-1330)

- **Le rôle de test** « Administrateur (parcours) » : créé par `installation.setup.ts`, seul et
  premier, par l'API (`createAccessRole`), avec `users.read`, `access_roles.read`,
  `system_status.read`, `audit_log.read`, `backups.read` ; retrouvé par son libellé à un rejeu, et ses
  permissions vérifiées (comme #2149 le demande pour tout rôle retrouvé). `give` continue de refuser
  les deux permissions d'administration à un autre compte que l'administrateur : le rôle n'en porte
  aucune.
- **`mode.ts`** : une fixture de worker `administration` à côté de `manager` — un compte local de la
  course, créé par `accountAdministrator`, qui porte ce rôle — ; la fixture `served` connecte celui
  des deux que le titre du parcours demande : l'étiquette `@administration` à côté de `@shared`,
  lue comme les projets lisent `@shared` ; sans elle, le manager, comme aujourd'hui.
- **Le projet en série** : l'étiquette `@serial` à côté de `@shared` ; un projet `shared-serial`
  (`grep: /@serial/`, `workers: 1`, `dependencies: ["installation", "shared"]`) ; `shared` prend
  `grepInvert: [SERIAL]` ; `realm` et `restoration` le mettent dans leurs dépendances. Les trois
  parcours de #2211 prennent `@shared @serial`, celui des unités de durée compris, et affirment leur
  relecture par `inService` comme les autres.
- **Le verrou des rôles** : `ROLES_WAIT` passe à 25 s, sous les 30 s d'un test ; son message dit le
  verrou et le nombre de workers derrière lui. Le délai de la fixture de worker (60 s) est inchangé.
- **Le guide** : la règle de #2087 perd ses trois écarts et dit l'étiquette `@serial` ; « Ce qui ne
  se rejoue pas » nomme les parcours d'`admin.spec.ts` qui écrivent — sauvegardes, horaire,
  comptes, rôles — et leur raison : ils écrivent un objet unique ou demandent `users.write`, que
  ceux d'`e2e/service/` éprouvent sous l'administrateur.

### Les autorisations, la liste de ruff, la file de fusion (US-1350, US-1360, US-1370)

- **`.claude/settings.json`** gagne `permissions.allow` avec les vingt-et-une règles d'US-1350 ; le
  hook reste ; le fichier est déjà dans `REUSE.toml`. Un test des outils le lit en JSON.
- **`ruff.toml`** : une entrée `"backend/src/waterfall/api/<module>.py" = ["TC001", "TC002",
  "TC003"]` par module, triées, le commentaire une fois au-dessus ; le test des outils (dans
  `test_rules.py`, qui éprouve déjà `ruff.toml`) lit le TOML par `tomllib`, relève les modules
  d'`api/` dont le texte porte `APIRouter(`, et confronte.
- **`wftools.mergequeue`** : `create EP-nn` lit `.github/rulesets/merge-queue.json`, y pose le nom
  et `refs/heads/epic/EP-nn`, liste d'abord les jeux de règles (`gh api repos/{owner}/{repo}/rulesets`)
  et refuse si l'un vise déjà la branche, puis `POST` par `gh api --input -` ; `check EP-nn` liste
  les jeux, lit celui qui vise la branche (`gh api …/rulesets/<id>`) et exige `enforcement: active`
  et une règle `merge_queue`. Le modèle est le jeu d'EP-05 relu par `gh api`, sans ses
  identifiants ni ses dates. `gh` est appelé comme `tracking.py` l'appelle, et les tests posent un
  faux `gh` sur le `PATH`.
- **`epic-deliverer`**, « La branche de l'EPIC » : après la poussée, `make merge-queue-check
  EPIC=EP-nn` ; en échec, une question à une personne, qui lance `make merge-queue EPIC=EP-nn`.

### Ordre de construction

Les US sont indépendantes ; l'ordre dit seulement ce qui rend service le plus tôt au pilotage
d'EP-04 :

1. US-1290, le tableau de suivi — à prendre en premier (#2112) ;
2. US-1300, l'arrêt d'un créneau, et US-1370, la file de fusion ;
3. US-1350, les autorisations, et US-1360, la liste de ruff — petits, les conflits de
   synchronisation ;
4. US-1310, le garde ; US-1320, les contrôles de la chaîne ; US-1330, le harnais ;
5. US-1340, les finitions et les textes.

Les fichiers partagés par plusieurs US — le Makefile (US-1290, US-1300, US-1370),
`docs/dev/agents.md` (US-1300, US-1310, US-1340, US-1350), `epic-deliverer` (US-1290, US-1300,
US-1370), le guide (US-1290, US-1300, US-1330, US-1340, US-1360, US-1370), `guard.py` (US-1300,
US-1310) — donnent les « Pas avec » du plan de lots.

### Décisions

| Décision | Option écartée, et pourquoi |
|---|---|
| `depend_de: EP-19, EP-05` (auteur, 2026-11-07) | tirer `epic/EP-21` avant la fusion d'EP-05 et bloquer deux lots : EP-05 est dans `main` (#2217) |
| Les processus de l'e2e trouvés par leur port dans `/proc`, arrêtés par PID (auteur, 2026-11-07) | `fuser -k`, `ss -p`, `lsof` : des paquets que le poste ou un runner peut ne pas avoir, et `slots.py` est de la bibliothèque standard seule ; par nom (`next-server`) : la règle du garde |
| `slot-release` et la reprise d'un créneau abandonné arrêtent aussi les serveurs | une cible à part seulement : un créneau rendu avec un `next-server` dedans est celui de la nuit du 6 au 7 |
| Un verrou propre au créneau autour de `make test-services`, bloquant | un `up` relancé sur échec : Compose échoue tard et de façon irrégulière sur un réseau en création (#1909) |
| Le garde reste un seul script, mesuré par le lot | un second module importé par chemin : un script lancé par `python3` et un module importé comme `wftools.guard` ne résolvent pas le même import |
| Un `cd` vers un chemin calculé compte comme un déplacement dans `.git` | le laisser passer : `cd "$(git rev-parse --git-dir)" && rm index.lock` est la forme de #1893 ; le faux positif est du côté sûr |
| Un contrat `layers` sur `waterfall.core.*` + test de complétude (auteur, 2026-11-07) | la seule règle `forbidden` `resource_settings -/-> users` de #2124 : elle n'interdit que le cycle d'hier ; un contrat personnalisé « acyclique » : du code à charger dans l'environnement du back |
| Le test du Compose par `docker compose config` | lire le YAML : les outils n'ont aucune dépendance, et les ancres `<<: *back` ne se lisent qu'en les résolvant |
| Option B2, un rôle de test de lectures seules (auteur, 2026-11-07) | B1, un second compte au rôle prédéfini « Administrateur » : rompt `give` et les refus `LAST_ADMINISTRATOR` de `roles.spec.ts` ; B3, l'administrateur de l'installation : un compte partagé de plus sous `oneAtATime`, et ses recherches gardées d'un parcours à l'autre |
| `SETTINGS_WRITER` reste jusqu'à EP-04 (auteur, 2026-11-07) | le retirer : aucun rôle prédéfini ne porte `risk_settings.write` ni `indicator_settings.write` (`predefined.py`) ; #2199 le croyait, à tort |
| Le compte demandé par une étiquette du titre (`@administration`, `@serial`) | `test.use` par fichier : les trois fichiers mêlent des parcours des deux sortes ; une liste de fichiers : écartée par l'auteur pour `@shared` (2026-11-05) |
| Un projet `shared-serial` à un worker | une remise de la valeur dans un `finally` (#2211, option 2) : l'objet change quand même sous les yeux des autres workers |
| `ROLES_WAIT` à 25 s | relever le délai des tests : chaque appelant de `give` devrait le dire, et le délai de 30 s est celui que la chaîne tient |
| Les 21 règles versionnées dans `.claude/settings.json`, sans la règle du poste (auteur, 2026-11-07) | les garder dans `~/.claude/settings.json` : elles ne suivent ni le dépôt ni ses worktrees, et chaque poste les retape |
| Une entrée de `per-file-ignores` par module, triée (auteur, 2026-11-07) | un motif `api/*.py` : `middleware`, `problems` et `queries` perdraient le contrôle ; la liste entre accolades sur plusieurs lignes : une clé TOML tient sur une ligne |
| Les modules de routes reconnus par `APIRouter(` dans leur texte | une liste figée dans le test : c'est elle qu'on oublierait ; `Depends(` : `queries` en porte un et n'est pas exempt, à dessein |
| `make merge-queue` par `gh api`, réservé à une personne ; `make merge-queue-check` pour le livreur (auteur, 2026-11-07) | laisser le livreur créer le jeu de règles : le jeton de l'utilisateur le lui permettrait, et la file d'une branche n'appartient pas à un agent |
| Le modèle du jeu de règles versionné sous `.github/rulesets/` | le lire du jeu d'EP-05 à chaque création : le jeu d'EP-05 disparaîtra avec sa branche |

---

## US-1290 — `make tracking` écrit ce que le pilote écrivait à la main

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2246

**En tant que** développeur, **je veux** que `make tracking` sache ajouter la ligne d'un lot coupé,
changer une dépendance et reconnaître toute cellule « Lot » que le cadreur écrit, et qu'un test
tienne le gabarit de l'issue d'un EPIC d'accord avec l'outil, **afin que** plus aucun pilote ne
réécrive le corps de l'issue à la main, ce que ses règles lui interdisent et que six éditions en deux
jours ont pourtant demandé (#2112).

**Critères d'acceptation.**

- propre à l'US : `make tracking ISSUE=<n> ADD_LOT=<identifiant> AFTER=<lot> [DEPENDS=<liste>]
  [MODEL=<modèle>]` insère, sous la ligne du lot nommé par `AFTER` et dans la même US, la ligne d'un
  lot nouveau : cellules « # », « US » et « Statut » vides comme toute ligne de continuation,
  « Lot » l'identifiant donné (`L3 #<issue>` pour le lot d'une US à plusieurs lots, `US-0820b #2099`
  pour la part détachée d'une US à lot unique), « Dépend de » la liste donnée ou `—`, « Pas avec »
  `—`, « État du lot » `à faire`, « PR » `—`, « Modèle » le modèle donné ou `—` ; elle refuse un
  lot dont la ligne existe déjà, et un `AFTER` qu'elle ne trouve pas ;
- propre à l'US : `make tracking ISSUE=<n> LOT=<identifiant> DEPENDS=<liste>` remplace la cellule
  « Dépend de » du lot ; `make tracking ISSUE=<n> REPLACE_DEPENDENCY='<ancien>=<nouveau>'` remplace
  la mention de l'ancien lot par celle du nouveau dans la cellule « Dépend de » de toutes les lignes
  où elle paraît, de sorte que les lots qui dépendaient d'une US coupée dépendent de sa seconde
  moitié ; elle dit combien de lignes elle a changées, et refuse quand aucune ne porte l'ancien ;
- propre à l'US : `LOT=<identifiant>` reconnaît la part détachée d'un lot coupé — `US-0820b`, dont
  la ligne est une continuation sous US-0820, et `US-1270/L2b` — et la cellule « Lot » d'une US à
  lot unique suivie de ses constats ou d'une note (`lot unique (#1840)`, `lot unique — en dernier`),
  qu'aucune US à lot unique d'EP-17 ne pouvait changer (#1979) ;
- propre à l'US : un test des outils lit le tableau du `value` du gabarit
  `.github/ISSUE_TEMPLATE/04-epic.yml` et lui applique chaque forme de `make tracking` — `LOT` avec
  `STATE`, `PR` et `MODEL` ; `US` avec `STATUS` ; `FINDING` ; `ADD_LOT` ; `DEPENDS` ;
  `REPLACE_DEPENDENCY` — : un gabarit et un outil qui ne s'accordent plus font échouer
  `make test-tools` (#1915) ;
- propre à l'US : chaque forme nouvelle a son test dans `tools/tests/test_tracking.py`, par le faux
  `gh` des tests existants, et garde ce que l'outil garantit déjà — le verrou du poste, la relecture
  juste avant l'écriture, le reste du corps réécrit octet pour octet, une valeur à saut de ligne
  refusée, un `|` échappé ;
- propre à l'US : le guide (`docs/dev/README-fr.md` et `README.md`, « Commandes »), le Makefile
  (`make help`) et `epic-deliverer` (la coupe à la demande du relecteur, point 3 de « Chaque lot »)
  disent ces commandes ; le livreur qui coupe un lot ajoute sa ligne et déplace les dépendances par
  elles, et plus jamais à la main.

**Notes de réalisation.**

La ligne d'un lot coupé prend la place juste après le lot qu'elle détache, et en dépend (README de
la roadmap, « Lots » ; `epic-deliverer`, point 3). Les lignes d'EP-05 écrites à la main (#2032) sont
la forme à reproduire : `|   |   |   | US-0820b #2099 | US-0820 #2036 | — | fusionné | #2118 | sonnet |`.

**Hors périmètre.**

Une réécriture de l'ordre des US, ou l'ajout d'une US : le tableau est écrit une fois par le cadreur,
et une US nouvelle est un recadrage.

---

## US-1300 — Un créneau se rend entier

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2247

**En tant que** développeur, **je veux** qu'une cible du Makefile arrête les serveurs de l'e2e de mon
créneau, que `make slot-release` l'appelle, et que les services de test d'un créneau ne se démarrent
qu'une fois à la fois, **afin qu'**un `make check-front` interrompu ne laisse plus un `next-server`
occuper un cœur et un créneau toute une nuit (#2198), et qu'un `make test-back TESTS=…` et un
`make test-front TESTS=…` lancés ensemble ne fassent plus deux `docker compose up` du même projet
(#1909).

**Critères d'acceptation.**

- propre à l'US : `make e2e-down` arrête, pour le créneau du worktree, les processus de l'utilisateur
  qui écoutent sur les ports de l'e2e de son bloc — le faux back (`E2E_API_PORT`) et les fronts des
  parcours (`E2E_FRONT_PORT` et les trente-neuf suivants) —, et ceux-là seuls : chacun est trouvé par
  son port, puis arrêté par son PID, jamais par un motif ; au créneau 0, ce sont les ports d'avant
  (4110, 3100 à 3139) ; elle dit ce qu'elle arrête, et ne dit rien quand rien n'écoute ;
- propre à l'US : un processus qui n'est pas arrêté par `SIGTERM` dans le délai de la conception
  reçoit `SIGKILL`, et la cible le dit ; dans un worktree lié sans créneau, elle échoue en disant
  `make slot`, comme les autres cibles d'un créneau ;
- propre à l'US : `make slot-release` l'appelle avant de retirer les conteneurs et les volumes du
  créneau, de sorte qu'un créneau rendu n'a ni conteneur, ni volume, ni serveur ; `make slot`, qui
  reprend un créneau dont le worktree n'existe plus, en arrête de même les serveurs ;
- propre à l'US : un test des outils démarre un processus à l'écoute sur un port du bloc d'un
  créneau de test, lui applique l'arrêt et constate qu'il n'écoute plus et qu'un processus à
  l'écoute hors du bloc n'est pas touché ;
- propre à l'US : deux exécutions `slots.py run --services …` lancées ensemble dans un même worktree
  ne font qu'un `make test-services` à la fois : la seconde attend la première sous un verrou propre
  au créneau, puis trouve ses services démarrés ; un test à deux processus le prouve (#1909) ;
- propre à l'US : le refus du garde (`guard.py`, `INSTEAD`) nomme `make e2e-down` parmi les cibles
  qui arrêtent ce que le Makefile a démarré ; `docs/dev/agents.md` (« Un lot ne laisse rien derrière
  lui », « Un agent n'arrête que ce qu'il a lancé »), `epic-deliverer` (point 10 de « Chaque lot »)
  et le guide (« Commandes », « Les créneaux des worktrees ») disent la cible et quand l'appeler :
  avant `make slot-release`, et dès qu'un `make e2e`, `make e2e-service` ou `make check-front`
  s'interrompt.

**Notes de réalisation.**

Prism du mandataire du contrat (`contract-proxy`) et la plateforme sont des conteneurs, que
`make service-down` et `make slot-release` retirent déjà : la cible ne vise que les processus du
poste. Chromium et Playwright n'écoutent sur aucun port : ils s'arrêtent avec les serveurs qu'ils
attendaient, ou avec le processus qui les a lancés ; ce que la cible ne sait pas arrêter va au
relevé du livreur.

**Hors périmètre.**

Les serveurs de `make dev` et de `make mock` lancés à la main, hors des créneaux (EP-19, « Ce qui
n'en fait pas partie »).

---

## US-1310 — Le garde voit les formes qu'un agent écrit sans malice

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2251

**En tant que** développeur, **je veux** que le garde des commandes refuse les formes d'arrêt et de
suppression qu'un agent écrit sans malice et qu'il laisse passer aujourd'hui, et qu'il suive un `cd`
dans `.git` sous toutes ses formes, **afin que** le filet d'US-1080 tienne à quatre livreurs, où un
verrou de git supprimé ou un volume retiré touche un autre créneau (#1890, #1893).

**Critères d'acceptation.**

- propre à l'US : le garde refuse `find` dont un chemin passe par `.git` et qui porte `-delete` ou
  `-exec rm`, et `mv` ou `rename` d'un chemin qui passe par `.git` et finit par `.lock` — un verrou
  de git ne se supprime ni ne se déplace, la commande se relance ;
- propre à l'US : il refuse `docker rmi`, `docker image rm` et `docker volume rm` — et leurs formes
  `docker image remove`, `docker volume remove` — dont une cible porte `$`, un accent grave ou un
  joker, vient d'un tube ou de `xargs`, ou qui portent `--filter`, comme il refuse déjà `docker rm` ;
  une cible littérale passe ;
- propre à l'US : il analyse la commande que lancent `busybox`, `su -c`, `runuser -c`, `flock`,
  `watch` et `chroot`, avec leurs options, comme il analyse déjà celle de `sudo`, `env`, `timeout`
  ou `nohup` : `flock /tmp/x pkill make` et `su -c 'pkill make'` sont refusés ;
- propre à l'US : il suit un `cd` dans `.git` sous `bash -c`, `sh -c` et `eval` lancés après lui
  (`cd .git && bash -c 'rm index.lock'`), par `pushd`, par `env -C`, `env --chdir` et leurs
  abréviations, et derrière `command` ou `builtin` ; un `cd` vers un chemin calculé
  (`cd "$(git rev-parse --git-dir)"`, `cd $GIT_DIR`) compte comme un déplacement dans `.git`, du côté
  sûr ; un `cd` vers un chemin littéral hors de `.git`, `cd ..` et `cd -` remettent l'état à zéro, de
  sorte que `cd .git; cd ..; rm foo.lock` passe ;
- propre à l'US : chaque option longue de chaque préfixe admet ses abréviations selon la règle du
  préfixe unique de GNU, comme `--split-string` les admet déjà : `env --ch /tmp pkill x` est refusé ;
- propre à l'US : chaque forme refusée et chaque forme permise ci-dessus a son test dans
  `tools/tests/test_guard.py`, et les formes d'US-1080 passent ou sont refusées comme avant ;
- propre à l'US : `guard.py` reste un script de la bibliothèque standard, sans autre module de
  `wftools`, lancé par `python3`, et sous les 1 000 lignes de `make sources` ;
- propre à l'US : `docs/dev/agents.md`, « Un agent n'arrête que ce qu'il a lancé », nomme les formes
  ajoutées — `find … -delete` et `mv` d'un verrou de git, `docker rmi` et `docker volume rm` d'une
  cible calculée —, et le message du garde dit ce qu'il faut faire à leur place.

**Notes de réalisation.**

Le garde est un filet contre l'erreur, pas un bac à sable (US-1080, « Hors périmètre ») : une forme
qui ne s'écrit que pour le contourner — commande passée en texte à un interpréteur, substitution ou
variable en position de mot de commande — reste une limite connue, et n'entre pas ici.
`docker stop "wf-$SLOT-pg"` reste refusé (#1890) : les conteneurs d'un créneau se retirent par
`make slot-release` et `make test-services-down`.

---

## US-1320 — La chaîne attrape ce que la file a attrapé tard

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2252

**En tant que** développeur, **je veux** que `make check` refuse un cycle d'imports entre deux
modules du noyau, que `make service-up` reconstruise chaque image qu'il démarre, et que le contrôle
des bornes des paramètres compare tout ce que le contrat déclare, **afin que** la file de fusion
n'attrape plus, après la revue, ce que le palier rapide savait voir (#2124, #2083, #2185).

**Critères d'acceptation.**

- propre à l'US : un contrat import-linter de `backend/pyproject.toml` ordonne les modules de
  `waterfall.core` en couches, dans l'ordre que la conception fixe, et `make imports-back` refuse un
  import d'un module d'une couche haute depuis une couche basse, par l'interface comme autrement :
  `waterfall.core.resource_settings` qui importerait `waterfall.core.users` est refusé — le cycle de
  #2124 ne peut plus naître ;
- propre à l'US : un test des outils tient le contrat à jour : chaque paquet de
  `backend/src/waterfall/core/` est nommé dans ses couches, et un paquet nouveau qui n'y est pas fait
  échouer `make test-tools` en nommant le paquet ;
- propre à l'US : `docs/dev/python.md`, « Défauts déjà rencontrés », dit le cycle de #2124, la
  règle — `resource_settings` ne dépend d'aucun autre module du noyau, et les auteurs d'un objet se
  nomment dans `api/` — et le contrat qui la tient ;
- propre à l'US : `make service-up` construit l'image de chaque service de
  `deploy/compose/compose.service.yaml` qu'il démarre et qui déclare un `build`, `restore` compris,
  de sorte qu'une restauration jouée en local après une migration nouvelle trouve la migration
  (#2083, #2218) — la ligne `up --build --detach --wait restore` vient d'US-0990/L2 d'EP-04, livrée
  avant ce lot ; le lot la pose si elle manque encore ;
- propre à l'US : un test des outils lit les services du Compose de service qui déclarent un `build`
  (`docker compose config`, avec les valeurs de remplacement de `make lint-compose`) et vérifie que
  chacun est démarré avec `--build` ou construit avant son démarrage par `service-up`,
  `service-install` ou `e2e-service` : un service construit qui serait démarré sans l'être fait
  échouer `make test-tools` en le nommant ;
- propre à l'US : le contrôle des bornes des paramètres de requête (`drifting`,
  `backend/tests/test_contract_declarations.py`) compare aussi `pattern`, `enum`, `minItems` et
  `maxItems`, et trouve un paramètre que le service déclare et que le contrat n'a pas ; le test sur
  un contrat de brouillon qui prouve chaque écart trouvé s'étend à ces cas (#2185).

**Notes de réalisation.**

Le graphe des imports du noyau au 2026-11-07, sur `main` : `users` lit `resource_settings` ;
`cost_settings` lit `users` et `resource_settings` ; `indicator_settings` lit `cost_settings` ;
`access_roles` et `backups` lisent `users` ; `risk_settings` ne lit rien. EP-04 ajoute ses modules
sur sa branche : le test des outils le lui dira à sa prochaine reprise de `main`, et c'est voulu.

**Hors périmètre.**

Les durées des tests du back (#2157) ; les leviers de l'audit de la chaîne du 2026-11-05 non encore
pris (miroir des images, cache, `installation.setup`), s'ils ne sont pas retenus au cadrage.

---

## US-1330 — Les parcours d'administration et les parcours en série contre le service

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2253

**En tant que** développeur, **je veux** que les parcours partagés de l'administration et de l'état
se jouent contre le service sous un compte qui en a les permissions, que les parcours qui écrivent un
objet unique de l'installation se jouent en série, et que l'attente du verrou des rôles composés
tienne dans le délai d'un test, **afin que** `make e2e-service` éprouve l'administration et les
réglages contre le service, et non plus contre le faux back seul (#2199, #2211, #2214).

**Critères d'acceptation.**

- propre à l'US : un rôle de test « Administrateur (parcours) », créé à l'installation, porte les
  lectures de l'administration — `users.read`, `access_roles.read`, `system_status.read`,
  `audit_log.read`, `backups.read` — et ni `users.write` ni `access_roles.write` ;
  `frontend/e2e/mode.ts` connecte un parcours partagé qui le demande avec un compte de la course qui
  porte ce rôle, un par worker ; le « Manager » garde le sens que les parcours éprouvent : il ne
  reçoit ni `users.*` ni `system_status.read` (option B2, décision de l'auteur du 2026-11-07) ;
- propre à l'US : les lectures de l'administration et de l'état d'`admin.spec.ts` et l'ouverture de
  l'administration et de l'état dans `navigation.spec.ts` portent `@shared` et se jouent contre le
  service sous ce compte ; les parcours de l'administration qui écrivent — un compte, un rôle, une
  sauvegarde — restent ceux d'`e2e/service/` sous l'administrateur de l'installation, et ceux
  d'`admin.spec.ts` qui ne se rejouent pas sont nommés au guide (« Un parcours de bout en bout »,
  « Ce qui ne se rejoue pas ») avec leur raison ;
- propre à l'US : un projet Playwright joué en série contre le service, après `shared`, joue les
  parcours partagés qui portent une étiquette propre et écrivent un objet unique de l'installation :
  les unités de durée (`reference-resources.spec.ts`), les réglages (`reference-settings.spec.ts`) et
  la correspondance des coûts réels (`reference-actual-cost-mapping.spec.ts`) y passent, et la règle
  du guide décidée pour #2087 ne connaît plus d'écart (#2211, option 1) ;
- propre à l'US : la rubrique du guide qui nomme ces trois parcours comme écarts les retire, et dit
  l'étiquette et le projet ;
- propre à l'US : l'attente du verrou des rôles composés (`giveRoles`, `ROLES_WAIT`,
  `frontend/e2e/service/realm.ts`) tient sous le délai d'un test, ou les parcours qui l'appellent
  relèvent leur délai en le disant ; les deux lignes du guide au-delà de 100 colonnes sont recoupées
  (#2214) ;
- propre à l'US : le rôle composé « Paramètres des risques et des indicateurs (parcours) »
  (`SETTINGS_WRITER`, #2149) reste, avec les trois corrections de #2149, jusqu'à ce qu'EP-04 amorce
  ses permissions dans le « Manager » : aucun rôle prédéfini ne les porte (décision de l'auteur du
  2026-11-07) ;
- propre à l'US : `make e2e-service` passe au palier complet, sur le poste comme dans la chaîne, et
  `make e2e` ne change pas.

**Notes de réalisation.**

Le rôle prédéfini « Administrateur » (`core/access_roles/predefined.py`) porte `users.*`,
`access_roles.*`, `system_status.read`, `backups.*`, `audit_log.read` et `platform_restore`, et ni
`risk_settings.write` ni `indicator_settings.write` : c'est pourquoi `SETTINGS_WRITER` reste. Le
guide dit qu'aucun parcours ne donne à un autre compte que l'administrateur de l'installation les
deux permissions d'administration — `give` le refuse —, parce que les refus `LAST_ADMINISTRATOR` de
`roles.spec.ts` et d'`accounts.spec.ts` en dépendent : c'est pourquoi le rôle de test ne porte que
des lectures (option B2, contre B1, un second compte au rôle prédéfini, et B3, l'administrateur de
l'installation lui-même).

**Hors périmètre.**

L'amorçage de `risk_settings.write` et `indicator_settings.write` dans le « Manager » : EP-04
(`TO_SEED_BY_EP04`, #1457).

---

## US-1340 — Finitions d'outils et de guide, et les textes des deux jours à quatre livreurs

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2254

**En tant que** développeur, **je veux** que les quatre finitions reportées vers EP-21 par EP-20 et
EP-22 soient faites, et que le guide et le skill `pilote` disent ce que les deux jours à quatre
livreurs ont appris — comment reprendre `main` dans une branche d'EPIC, ce que le pilote fait des
worktrees des livreurs rendus et de sa propre session —, **afin que** le guide et les outils ne
disent plus une version ou un chemin que le dépôt dément, et qu'une synchronisation ou un
redémarrage ne coûtent plus un lot (#2028, #2074, #2075, #2085).

**Critères d'acceptation.**

- propre à l'US : dans `tools/tests/test_openldap_entrypoint.py`, le test des volumes d'une image
  d'avant l'entrypoint les pose sans l'entrypoint — un `cn=config.ldif` et un fichier de données
  touchés —, puis démarre une fois ; le test du repère resté auprès de la configuration a sa docstring
  d'une ligne, et celle du module dit ce cas ; le guide (`docs/dev/README-fr.md` et `README.md`,
  paragraphe de l'annuaire) remplace « d'avant ce lot » et « désormais » par une formulation durable
  (#2028) ;
- propre à l'US : `INSTALL.md` ne dit plus « 3.14 » à côté de son renvoi à `tools/.python-version` :
  il ne garde que le renvoi, sur la ligne de Python comme sur celle d'uv (#2074) ;
- propre à l'US : `make check-tools` dit « missing  tools/.python-version » quand le fichier manque,
  comme pour un outil absent, au lieu d'un avertissement sans version (#2075) ;
- propre à l'US : `docs/dev/python.md`, « Les annotations sous Python 3.14 », écrit
  `platform/restoration.py` et `core/users/tables.py` (#2085) ;
- propre à l'US : le guide (`docs/dev/README-fr.md` et `README.md`, « Branches, lots et pull
  requests ») a une rubrique « Reprendre `main` dans une branche d'EPIC » : qui le fait (une
  personne), quand (après chaque fusion dans `main`, et avant qu'un lot ne parte d'une branche en
  retard), comment (une branche `sync/EP-nn`, une pull request vers `epic/EP-nn`, mise en file comme
  un lot, les conflits réglés là et non à la livraison), et ce qui a coûté les 6 et 7 novembre : une
  synchronisation remise en file deux fois parce que des lots ont été fusionnés pendant sa chaîne —
  elle se met en file quand aucun lot n'est en revue, ou se refait ;
- propre à l'US : le skill `pilote` et `docs/dev/agents.md`, « Le pilote », disent qu'un pilote ne
  redémarre pas sa session tant qu'un livreur qu'il a lancé est en vol — le redémarrage les arrête
  tous, et un lot a dû être repris —, et qu'il retire lui-même le worktree d'un livreur qui a rendu
  son relevé, lot fusionné (`git worktree unlock`, `git worktree remove`, `git worktree prune`),
  parce que le harnais le garde verrouillé ; les autres worktrees de trop restent signalés, jamais
  retirés ;
- propre à l'US : `make readmes` et `make roadmap` passent, et
  `make test-tools TESTS=tools/tests/test_openldap_entrypoint.py` passe.

---

## US-1350 — Les autorisations des livreurs suivent le dépôt

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2249

**En tant que** développeur, **je veux** que les règles d'autorisation dont un livreur a besoin —
mettre en file, éditer une issue, pousser, prendre son créneau — soient versionnées dans
`.claude/settings.json`, **afin qu'**un worktree neuf les ait d'emblée, au lieu de les chercher dans
un `.claude/settings.local.json` que le worktree n'a pas, ce qui a fait perdre leur temps à un pilote
et à ses livreurs les 6 et 7 novembre.

**Critères d'acceptation.**

- propre à l'US : `.claude/settings.json` porte, sous `permissions.allow`, les vingt-et-une règles
  que les livreurs ont demandées : `Bash(cd:*)`, `Bash(gh api graphql:*)`,
  `Bash(gh issue create:*)`, `Bash(gh issue close:*)`, `Bash(gh issue comment:*)`,
  `Bash(gh issue edit:*)`, `Bash(gh pr create:*)`, `Bash(gh pr view:*)`, `Bash(gh pr checks:*)`,
  `Bash(gh pr list:*)`, `Bash(gh pr merge:*)`, `Bash(gh run list:*)`, `Bash(gh run view:*)`,
  `Bash(gh run watch:*)`, `Bash(git push:*)`, `Bash(git branch -d:*)`,
  `Bash(git worktree unlock:*)`, `Bash(git worktree remove:*)`, `Bash(make tracking:*)`,
  `Bash(make slot:*)`, `Bash(make slot-release:*)` ; la règle propre au poste
  (`Bash(cat > /tmp/claude-1000/*)`) n'y est pas ; le hook `PreToolUse` du garde reste ;
- propre à l'US : un test des outils lit `.claude/settings.json`, vérifie qu'il est un JSON, que son
  hook est celui du garde et que sa liste porte la mutation `enqueuePullRequest` et les trois
  commandes `make` du livreur ;
- propre à l'US : `docs/dev/agents.md`, « La mise en file », dit que la règle est versionnée dans
  `.claude/settings.json`, que chaque worktree la reçoit, et ce qu'elle n'autorise pas ; le passage
  qui demandait à une personne de l'accorder une fois disparaît, et `CONTRIBUTING.md` suit.

**Notes de réalisation.**

`Bash(gh api graphql:*)` couvre la mutation exacte de la file que `docs/dev/agents.md` donne
aujourd'hui, et plus large : c'est le choix de l'auteur du 2026-11-07, qui a vu les livreurs
s'arrêter sur chacune de ces règles ; `docs/dev/agents.md` garde la mutation comme la seule forme
que le livreur écrit.

---

## US-1360 — La liste d'exemption de `ruff.toml` fusionne et se tient

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2250

**En tant que** développeur, **je veux** que la liste des modules d'`api/` exemptés de TC001–TC003
dans `ruff.toml` tienne un module par ligne, triée, et qu'un test exige chaque module de routes dans
la liste, **afin que** deux lots qui ajoutent chacun un module de routes fusionnent sans conflit — la
cause de quatre interventions d'un développeur les 6 et 7 novembre — et qu'un module oublié ne
passe plus.

**Critères d'acceptation.**

- propre à l'US : `ruff.toml`, `[lint.per-file-ignores]`, exempte chaque module par une entrée à
  lui — `"backend/src/waterfall/api/<module>.py" = ["TC001", "TC002", "TC003"]` —, les entrées
  triées par nom, le commentaire qui dit pourquoi écrit une fois au-dessus d'elles ; le résultat de
  `make lint-back` est inchangé ;
- propre à l'US : un test des outils exige que chaque module de `backend/src/waterfall/api/*.py` qui
  déclare un `APIRouter(` ait son entrée, que chaque entrée nomme un module qui existe, et que les
  entrées soient triées ; il échoue en nommant le module ;
- propre à l'US : le commentaire de `ruff.toml` et `docs/dev/python.md`, « Les annotations sous
  Python 3.14 », disent qu'un module de routes nouveau prend sa ligne, et que le test le rappelle.

**Notes de réalisation.**

Une clé TOML ne s'écrit pas sur plusieurs lignes : la liste entre accolades d'aujourd'hui ne peut
être qu'une seule ligne, que git ne fusionne pas quand deux lots l'allongent ; une entrée par module
est la seule forme qu'il fusionne. `authentication`, `evaluation` et `reference_settings_write` ne
déclarent pas de routeur et restent exemptés pour la raison écrite aujourd'hui.

---

## US-1370 — La file de fusion d'une branche d'EPIC se crée et se vérifie par le Makefile

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2248

**En tant que** développeur, **je veux** que le jeu de règles de la file de fusion d'une branche
d'EPIC se crée par une cible du Makefile depuis un modèle versionné, et que le livreur du premier
lot vérifie qu'il existe, **afin qu'**une faute de frappe dans la console de GitHub ne fasse plus
fusionner un lot sans file, comme le 2026-11-06.

**Critères d'acceptation.**

- propre à l'US : `make merge-queue EPIC=EP-nn` crée, par `gh api`, le jeu de règles
  « merge queue epic/EP-nn » sur `refs/heads/epic/EP-nn` depuis `.github/rulesets/merge-queue.json`,
  copie du jeu d'EP-05 (id 24096055) à la branche près ; elle refuse quand un jeu de règles vise
  déjà la branche, et quand `EPIC` manque ou n'a pas la forme `EP-nn` ; elle est réservée à une
  personne, et le guide le dit ;
- propre à l'US : `make merge-queue-check EPIC=EP-nn` passe quand un jeu de règles actif vise
  `refs/heads/epic/EP-nn` avec une règle `merge_queue`, et échoue en disant ce qui manque — aucun
  jeu, pas de règle de file, jeu inactif ;
- propre à l'US : `epic-deliverer`, « La branche de l'EPIC », lance `make merge-queue-check` après
  avoir poussé la branche, et, s'il échoue, pose la question à une personne au lieu de livrer un lot
  sans file ;
- propre à l'US : les deux cibles ont leurs tests dans les tests des outils, par un faux `gh` comme
  ceux de `make tracking` ; `make merge-queue-check EPIC=EP-05` passe sur le dépôt ;
- propre à l'US : le guide (« Commandes » et « Branches, lots et pull requests ») dit les deux
  cibles et le modèle, et `.github/rulesets/merge-queue.json`, qui ne peut porter de commentaire,
  est déclaré dans `REUSE.toml`.

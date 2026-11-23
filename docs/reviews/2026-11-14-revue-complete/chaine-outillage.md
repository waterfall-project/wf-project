# Revue — chaîne, Makefile, dépendances, licences, outillage des agents (PLC)

## Synthèse

La chaîne est soignée et, sur le plan de la sécurité des workflows, nettement au-dessus de la
moyenne : aucune `pull_request_target` ni `workflow_run`, toutes les actions tierces épinglées par
empreinte, `permissions:` déclarées partout, `persist-credentials: false`, aucune interpolation
`${{ github.event.* }}` dans un `run:` (tout passe par `env:`), caches écrits après fusion seulement
et lus sans écriture par les pull requests, miroir d'images adressé par empreinte, aucun
`continue-on-error`, aucun `|| true`, aucune relance de test (`retries: 0`). La porte (`gate.py`)
couvre les seize travaux de `ci.yml` et compte `failure` et `cancelled`.

Ce qui inquiète tient à ce que la chaîne **affirme sans le prouver** : (1) le modèle versionné du jeu
de règles de la file et `make merge-queue-check` ne portent ni ne vérifient aucun contrôle exigé — la
« porte exigée » n'est écrite que dans le guide ; (2) WF-QUA-0010, close « entière » par EP-01, ne
tient ni son refus de publier (la cible existe, la publication ne l'appelle pas) ni sa règle des
tests non exécutés ; (3) le garde des agents est **inerte, en silence**, dès que `python3` n'est pas
un 3.14 — c'est le cas du poste de cette revue ; (4) un créneau gardé par un livreur arrêté sur
limite d'usage bloque la série à N = 1. Le reste est de la dette localisée : formes d'exemption que
`make sources` ne voit pas, trois trous de la table des familles, veille Dependabot incomplète,
`SECURITY.md` périmé. Aucun constat bloquant.

## Constats bloquants

Aucun.

## Constats majeurs

### PLC-01 — Le jeu de règles de la file n'exige aucun contrôle, et `merge-queue-check` ne le vérifie pas

- **Issue** : #3683 (fermée), #3709 (fermée).
- **Où** : `.github/rulesets/merge-queue.json:12-45` (trois règles : `merge_queue`,
  `non_fast_forward`, `pull_request` à zéro approbation — aucune `required_status_checks`) ;
  `tools/src/wftools/mergequeue.py:136-153` (`problems`) et `:171-181` (`check`) ; le guide l'affirme
  pourtant, `docs/dev/README-fr.md:3322-3325` (« La porte est le seul contrôle que la protection des
  branches exige ») et `:3704-3705` (« sur `epic/*`, […] la porte exigée, la file de fusion »).
- **Quoi** : ni le modèle depuis lequel `make merge-queue` crée la file d'une branche d'EPIC, ni la
  vérification que le livreur lance avant de fusionner, ne portent la moindre exigence sur le
  contrôle `gate` : `check` passe dès qu'un jeu actif a une règle `merge_queue`.
- **Scénario** : une personne lance `make merge-queue EPIC=EP-29` ; le livreur du premier lot lance
  `make merge-queue-check EPIC=EP-29`, qui passe ; il met sa pull request en file
  (`enqueuePullRequest`). Si le contrôle exigé ne vient pas d'un autre jeu de règles — réglé à la
  main, non versionné, et que rien ne lit —, la file n'attend aucun contrôle et fusionne le groupe
  sans que `chain` ait rendu son verdict : le palier complet (couverture, parcours, service,
  production) tourne pour rien. C'est exactement la classe de faute qu'US-1370 voulait fermer
  (« une faute de frappe dans la console de GitHub », EP-21:801-804 (ligne 803)), déplacée d'un cran.
- **Vérifié** : le modèle, l'outil, ses critères d'US (EP-21:808-816 : « copie du jeu d'EP-05 à la
  branche près ») ; `grep required_status_checks` ne trouve rien dans le dépôt. **Non vérifié** : les
  réglages réels de GitHub (appel interdit par le cahier). `check_response_timeout_minutes: 60` et
  les rejets de file relevés dans `tools/queue-known.toml` laissent penser qu'un autre jeu (celui
  d'EP-01, « qui vise `main` et `epic/*` », EP-01:264-266) exige bien la porte aujourd'hui.
- **Proposition** : ajouter au modèle la règle `required_status_checks` (contexte `gate`,
  `integration_id` de GitHub Actions) ou, si elle doit rester dans un jeu commun, faire exiger par
  `problems()` qu'**un** jeu actif visant la branche porte `required_status_checks` avec `gate` ;
  test : un faux `gh` qui rend un jeu avec file et sans contrôle exigé fait échouer `check` en
  nommant « aucun contrôle exigé ».
- **Confiance** : confirmé pour le modèle et l'outil ; plausible pour l'exposition réelle.

### PLC-02 — WF-QUA-0010-A est close « entière » ; ni le refus de publier ni la règle des tests non exécutés ne sont tenus

- **Issue** : #3681 (fermée), #3710 (fermée), #3725 (ouverte).
- **Où** : `docs/spec/waterfall-spec.md:4529-4534` (corps : « La publication d'une version est
  refusée s'il reste une exigence F0 sans test […]. Un test qui se déclare non exécuté ne couvre pas
  l'exigence qu'il cite ; le rapport de couverture le présente comme tel, et la publication est
  refusée tant qu'il l'est ») ; `docs/roadmap/EP-01-socle-de-developpement.md:72` (« entière ») ;
  `Makefile:255-256` (`requirements-release`) ; `.github/workflows/images.yml:57-61` ;
  `tools/src/wftools/coverage.py:54,88-93,96-120`.
- **Quoi** : (a) `make requirements-release`, « la commande de la publication d'une version »
  (`docs/dev/README-fr.md:3923-3925`), n'est appelée par aucun workflow ni aucune cible : la seule
  publication qui existe, `images.yml` → `make images PUSH=yes`, pose l'étiquette de version
  immuable sur `main` sans elle ; (b) le relevé lit les citations sans lancer les tests et ne peut
  pas distinguer un test non exécuté.
- **Scénario** : (a) `main` porte la version 0.3.0 ; le coordinateur relève « 173 of 210 F0
  requirements covered » : 37 exigences F0 sans test, et la version est publiée
  (`ghcr.io/waterfall-project/*:0.3.0`). (b) Aucun workflow ne pose `WATERFALL_MSPDI_SCHEMA_PATH`
  (`grep` : `backend/tests/test_msproject.py:241-243`, `test_msproject_export.py:408-410`,
  `test_msproject_corpus.py:358-360`, et nulle part sous `.github/`) : les tests de validité contre
  le XSD sont `skipped` à chaque passage de la chaîne, cités `WF-INTF-0050-A`/`WF-QUA-0080-A`, et
  comptés comme couvrants. Côté TypeScript, la regex lit tout le fichier : huit citations
  d'aujourd'hui sont dans des commentaires (p. ex. `frontend/e2e/admin.spec.ts:335`,
  `frontend/e2e/service/session.spec.ts:102`) et paraissent au relevé comme des tests.
- **Vérifié** : aucun appelant de `requirements-release` (`grep` sur `.github`, `Makefile`,
  `tools/`) ; EP-13 ne reprend pas ce câblage (seule mention : #975). Par un script de lecture,
  aucune exigence n'est aujourd'hui couverte **seulement** par un commentaire ou un test sauté :
  le défaut (b) fausse la liste des tests, pas encore le compte.
- **Nuance** : EP-01 dit que sa chaîne « ne publie rien » (EP-01:60-62) ; la publication est venue
  avec US-0430, sans que le refus y soit branché. Si l'étiquette de version de ghcr n'est pas « la
  publication d'une version » au sens de l'exigence, alors l'exigence n'est pas close et la table
  d'EP-01 doit le dire (« début — close en EP-13 »).
- **Proposition** : soit `images.yml` lance `make requirements-release` avant de poser l'étiquette
  de version sur `main` (et elle ne se pose pas tant qu'il échoue), soit la portée passe à « début »
  avec l'EPIC qui clôt ; pour (b), restreindre la citation TypeScript au titre d'un `it(`/`test(`
  non `skip`/`fixme`/`todo`, et alimenter le relevé d'un rapport d'exécution (JUnit) pour les
  `pytest.skip` ; test : un même identifiant cité par un test joué et par un test sauté sort
  « non exécuté » pour le second.
- **Confiance** : confirmé. **Déjà connu en partie** : #975 (EP-28, EP-13:402-408) pour
  `test.fixme`/`skip` côté TypeScript ; le `pytest.skip` d'une fixture, les commentaires et le
  câblage de la publication n'y figurent pas.

### PLC-03 — Le garde des agents est inerte, sans un mot, quand `python3` n'est pas un 3.14

- **Issue** : #3682 (fermée), #3711 (fermée).
- **Où** : `tools/src/wftools/guard.py:47-48` (`Callable` importé sous `TYPE_CHECKING`) et `:877`
  (annotation de module `_CHECKS: dict[str, Callable[...]]`, évaluée à l'import avant Python 3.14) ;
  `.claude/settings.json:36` (`python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/guard.py"`) ;
  `guard.py:8-10` (« Claude Code lets a command pass on any other code ») ;
  `tools/tests/test_guard.py:366-376`.
- **Quoi** : sous un `python3` antérieur à 3.14, le module lève `NameError` à l'import et sort en
  code 1, que Claude Code tient pour une erreur non bloquante : **toute** commande passe, `pkill`
  compris.
- **Scénario** (rejoué sur le poste de cette revue, `python3` = 3.13.18) :
  `echo '{"tool_input":{"command":"pkill -f make"}}' | python3 tools/src/wftools/guard.py` →
  `NameError: name 'Callable' is not defined`, `exit=1`. Un livreur lancé dans une session cloud ou
  sur un poste dont le `python3` du PATH n'est pas celui de `tools/.python-version` travaille donc
  sans garde, et rien ne le dit : `make check-tools` n'émet qu'un avertissement
  (`Makefile:806-809`), et le test « as Claude Code does » passe quand même, parce que sous
  `uv run` le `python3` du PATH est celui du venv des outils.
- **Vérifié** : `slots.py`, lancé de la même façon (`Makefile:120`), échoue lui **bruyamment** sous
  3.13 (`SyntaxError`, `slots.py:344`, `except OSError, UnicodeDecodeError:`) — voir PLC-11 ; seul le
  garde échoue ouvert. C'est `ruff.toml:42-54` (TC00x, cible 3.14) qui pousse l'import sous
  `TYPE_CHECKING`.
- **Proposition** : importer `Callable` à l'exécution dans `guard.py` (exception de `ruff.toml`
  pour ce fichier, avec sa raison) et faire échouer fermé : le hook refuse (code 2, « garde
  inutilisable : python3 n'est pas 3.14 ») quand l'interpréteur est trop ancien ou que le garde
  lève ; test : lancer le hook par l'interpréteur le plus ancien présent (`/usr/bin/python3`) et
  attendre 2 sur `pkill`, plus un test d'`ast` qui refuse toute syntaxe ou annotation propre à 3.14
  dans les deux fichiers lancés par `python3`.
- **Confiance** : confirmé.

### PLC-04 — À N = 1, le créneau d'un livreur arrêté sur limite d'usage ou planté bloque la série

- **Issue** : #3690 (fermée), #3712 (fermée).
- **Où** : `.claude/agents/epic-deliverer.md:35-41` (« Seule exception, la limite d'usage : aucune
  commande ne passe alors, le créneau reste pris. L'instance qui reprend le lot prend son propre
  créneau, dans son propre worktree ») ; `tools/src/wftools/slots.py:498-501` (`abandoned` : libre
  seulement si le worktree n'existe plus) et `:656-668` (`claim`) ;
  `.claude/skills/pilote/SKILL.md:71-81`.
- **Quoi** : le créneau d'un livreur qui n'a pas pu lancer `make slot-release` reste pris tant que
  son worktree existe, et personne ne retire ce worktree : le pilote ne retire que celui d'un lot
  fusionné et « signale » les autres.
- **Scénario** : `WATERFALL_SLOTS=1`. Le livreur du lot A s'arrête sur la limite d'usage ; son
  worktree, verrouillé par le harnais, garde le créneau 1. Au réveil, le pilote lance une instance
  neuve « dans un worktree à elle » ; son `make slot` échoue (« all 1 slot(s) are taken ») ; elle
  rend « aucun créneau libre », que le pilote traite « comme une limite d'usage » et retente toutes
  les trente minutes, sans fin. Le seul signal, « plus de N + 1 worktrees », ne se déclenche pas :
  dépôt principal + worktree arrêté = 2.
- **Vérifié** : `claim` de bout en bout ; EP-19:249-256 et EP-21 ne prévoient aucune reprise du
  créneau d'un worktree vivant. **Non vérifié** : que le harnais tire bien un worktree neuf à chaque
  relance (c'est ce que disent le skill et l'agent).
- **Proposition** : que l'instance qui reprend un lot reprenne le créneau du worktree précédent du
  même lot (le registre pourrait porter l'identifiant du lot : `make slot LOT=<id>` rend le créneau
  tenu pour ce lot), ou que le pilote, au relevé « aucun créneau libre » répété pour un lot dont il
  sait le livreur arrêté, lance `make slot-release` dans le worktree arrêté ; test de `claim` : un
  second worktree du même lot obtient le créneau du premier.
- **Confiance** : plausible (pièce non vérifiée : le comportement du harnais).

## Constats mineurs

### PLC-05 — `make sources` laisse passer des commentaires d'exemption que Ruff et coverage.py honorent

- **Issue** : #3683 (fermée), #3713 (fermée).
- **Où** : `tools/src/wftools/sources.py:32-39` ; `backend/pyproject.toml:89-92` (`exclude_also`
  garde les exclusions par défaut de coverage.py).
- **Quoi** : la regex ne refuse que `# noqa`, `# ruff: noqa`, `# type: ignore`, `# pyright: …`,
  `# fmt:`, `# pragma: no cover`, `# shellcheck disable`.
- **Scénario** (rejoué avec le ruff 0.17.3 du dépôt et `ruff.toml`) : un fichier qui porte
  `# flake8: noqa: S307`, ou `# ruff: disable[S307]` … `# ruff: enable[S307]`, autour d'un `eval`
  → « All checks passed! » ; `import sys  # isort: skip` fait taire `I001`. Les trois passent
  `sources.breaches`. De même `# pragma no cover` (sans deux-points) et `# pragma: no branch`
  sortent des lignes et des branches de la mesure de couverture sans être refusés ; un
  `# hadolint ignore=…` d'un `Dockerfile` (sans suffixe) n'est jamais lu. Aucun usage aujourd'hui
  (`git grep`).
- **Proposition** : étendre la regex (`flake8:\s*noqa`, `ruff:\s*(?:disable|enable|ignore)`,
  `isort:\s*(?:skip|off)`, `pragma:?\s*no\s*(?:cover|branch)`, `hadolint\s+ignore`) et lire les
  `Dockerfile` ; un cas de test par forme.
- **Confiance** : confirmé (WF-QUA-0030-A, US-0050 : « Aucune règle ne s'écarte par un commentaire »).

### PLC-06 — Trois changements qui ne réveillent pas les contrôles qu'ils peuvent casser

- **Issue** : #3684 (fermée), #3698 (fermée), #3714 (fermée).
- **Où** : `tools/paths.toml:53` (`ruff.toml` dans `tools` seul), `:101-119` (`back`), `:173-202`
  (`service`), `:215-216` ; `tools/tests/test_families.py:80` ; `Makefile:120-121,134-136` ;
  `deploy/compose/compose.service.yaml:346,367` ; `.github/workflows/back.yml:122`.
- **Quoi** (familles calculées par `paths.read().touched`) :
  1. `ruff.toml` → `repo`, `tools` : `make lint-back`, qui lit ce même fichier, ne tourne pas. Une
     règle resserrée ou une ligne de `per-file-ignores` retirée casse `main` pour le lot suivant du
     back, pas pour celui qui l'a changée.
  2. `tools/src/wftools/slots.py` → `repo`, `tools` : or `test-back`, `coverage-back`,
     `test-front`, `coverage-front`, `build-front`, `e2e` et `e2e-service` passent tous par lui. Le
     garde des familles ne le voit pas : sa regex cherche `python <script>` et le Makefile écrit
     `python3 $(CURDIR)/…` derrière des variables en minuscules (`testing`, `heavy`).
  3. `deploy/compose/garage.toml` et `storage-buckets.sh` → `repo`, `tools`, `production` : la
     plateforme de service les monte et `back.yml` monte `garage.toml` pour les tests du back, mais
     ni `back`, ni `keycloak`, ni `service` ne se réveillent.
- **Proposition** : ajouter `ruff.toml` et `slots.py` à `back` (et `slots.py` à `front`, `service`),
  les deux fichiers de Garage à `back`, `keycloak`, `service` ; faire lire à `test_families.py` les
  montages `./…:ro` de `compose.service.yaml` et les scripts lancés par `python3`.
- **Confiance** : confirmé.

### PLC-07 — Formes réalistes que le garde laisse passer

- **Issue** : #3682 (fermée), #3697 (fermée), #3715 (fermée).
- **Où** : `tools/src/wftools/guard.py:20-21` (« the body of a here-document run nothing »),
  `:877-894` (`_CHECKS`), `:779-786` (`_make`) ; `.claude/settings.json:5,18`.
- **Quoi** (chaque forme rejouée par `guard.refusal`, sous 3.14) : passent
  `bash <<'EOF'` + `pkill -f next-server` + `EOF` (et `sh -s <<EOF`, `echo '…' | bash`) ;
  `npx kill-port 3000` et `pnpm dlx kill-port` (arrêt par port, donc du serveur d'un autre lot) ;
  `uv run pkill -f make` ; `uv run --project tools python -m wftools.mergequeue create EP-30` et
  `gmake merge-queue` (la cible réservée à une personne, sans `make`) ;
  `gh api graphql -f query='mutation { deleteRepositoryRuleset… }'`, préautorisé sans invite par
  `Bash(gh api graphql:*)` alors que le garde refuse `make merge-queue` au motif du jeton de
  l'utilisateur ; `truncate -s0 .git/index.lock`.
- **Proposition** : juger le corps d'un here-document remis à un shell ; refuser
  `-m wftools.mergequeue create` ; n'admettre de `gh api graphql` que les mutations de la file
  (`enqueuePullRequest`, `dequeuePullRequest`) ; ajouter `kill-port` aux noms refusés.
- **Confiance** : confirmé. **Déjà connu en partie** : #2417 (EP-28) pour les formes voisines de
  `rm -rf` sous `.git`, `xargs rm` et `make merge-queue` non adjacent — `rm -rf .git/objects` et
  `git rev-parse --git-dir | xargs -I{} rm {}/index.lock` passent en effet ; la largeur de
  `gh api graphql` et de `git push` est une décision consignée (`docs/dev/agents.md:94-104`).

### PLC-08 — `front-cache.yml` écrit aussi le cache d'uv, mais ne se déclenche que sur `frontend/**`

- **Issue** : #3685 (fermée), #3700 (fermée), #3716 (fermée).
- **Où** : `.github/workflows/front-cache.yml:18-20` et `:111-140`.
- **Quoi** : une fusion qui ne change que `backend/uv.lock` ou `tools/uv.lock` (la pull request
  mensuelle `uv` de Dependabot) ne lance pas le travail `uv` : la clé du cache change, et tous les
  travaux (`save-cache: false`) retéléchargent leurs paquets à chaque passage jusqu'à la prochaine
  fusion du front (ou au lundi, sur `main` seulement).
- **Scénario** : après une montée de `tools/uv.lock`, `repo / check` reconstruit `actionlint-py`
  depuis GitHub Releases à chaque passage — la source qu'US-1900 voulait sortir du chemin (#2643).
- **Proposition** : ajouter `backend/uv.lock` et `tools/uv.lock` aux `paths` (ou un workflow à
  part pour uv).
- **Confiance** : confirmé par lecture ; la clé exacte de `setup-uv` n'a pas été rejouée.

### PLC-09 — La veille ne suit ni les actions locales ni `deploy/e2e`, et le guide ne les nomme pas

- **Issue** : #3685 (fermée), #3700 (fermée), #3717 (fermée).
- **Où** : `.github/dependabot.yml:8-9` (`github-actions`, `directory: /`) et `:58-63` ;
  `.github/actions/pnpm-store/action.yml:20` ; `deploy/e2e/Dockerfile:19-57` ;
  `docs/dev/README-fr.md:3695-3700`.
- **Quoi** : `actions/cache/restore` épinglée dans l'action locale `pnpm-store` n'est pas dans un
  répertoire que Dependabot lit pour `github-actions` (`/` = `.github/workflows` et l'`action.yml`
  de la racine) ; `deploy/e2e/Dockerfile` (image d'uv, archive du client Docker, paquet `make`,
  pnpm) n'est dans aucune entrée `docker`. La liste « ce que Dependabot ne suit pas » du guide ne
  cite ni l'un ni l'autre.
- **Scénario** : la pull request mensuelle monte `actions/cache` dans les workflows ; l'action
  locale garde l'ancienne empreinte, indéfiniment.
- **Proposition** : `directories: ["/", "/.github/actions/*"]` ; `/deploy/e2e` dans l'entrée
  `docker` ; compléter la liste du guide ; un test qui tient une même empreinte par action entre
  workflows et actions locales.
- **Confiance** : plausible (le périmètre de `directory: /` vient de la documentation de
  Dependabot, non rejoué). Voisin de #3025 (images paramétrées par `WATERFALL_MIRROR`), déjà connu.

### PLC-10 — `packages: write` dans deux travaux de `pull_request`, et une immuabilité que seul l'outil tient

- **Issue** : #3685 (fermée), #3701 (fermée), #3718 (fermée), #3726 (ouverte), #3917 (fermée).
- **Où** : `.github/workflows/ci.yml:114-116` (`mirror`) et `:226-231` (`e2e-image`, au palier
  rapide « qui ne pousse rien ») ; `tools/src/wftools/images.py:153-162`.
- **Quoi** : ces deux travaux exécutent le code de la pull request (les outils et leurs dépendances
  de `tools/uv.lock`) avec un jeton qui peut écrire tous les paquets du dépôt, images publiées
  comprises ; « publié depuis `main` ou `epic/…` seulement » et « l'étiquette de version est
  immuable » sont des refus de l'outil, que ce même code peut ne pas appeler.
- **Scénario** : une dépendance de développement compromise, exécutée dans `mirror` au premier
  passage d'une pull request non relue, réécrit `ghcr.io/waterfall-project/waterfall:0.3.0`.
- **Proposition** : scinder `e2e-image` (recherche en lecture ; publication dans un travail du
  seul palier complet) ; documenter que l'immuabilité n'est pas celle du registre ; épingler en
  production par empreinte plutôt que par étiquette.
- **Confiance** : confirmé (lecture). Portée limitée : un jeton de fork reste en lecture.

### PLC-11 — Sous un `python3` autre que 3.14, le Makefile accuse `WATERFALL_SLOTS`

- **Issue** : #3682 (fermée), #3695 (fermée), #3719 (fermée), #3784 (fermée).
- **Où** : `Makefile:146` (`$(SLOTS) processors 2>/dev/null`, puis `$(error WATERFALL_SLOTS must be
  an integer from 1 to 9, not '…')`) ; `tools/src/wftools/slots.py:344`.
- **Scénario** (rejoué, `python3` 3.13) : `make -n test-back` →
  `Makefile:464: *** WATERFALL_SLOTS must be an integer from 1 to 9, not ''.  Stop.` La vraie cause,
  une `SyntaxError` de `slots.py`, est jetée avec la sortie d'erreur.
- **Proposition** : distinguer « l'outil n'a pas tourné » de « valeur refusée » (ne pas jeter
  stderr quand la sortie est vide, ou sonder la version d'abord) ; test dans
  `tools/tests/test_e2eworkers.py`.
- **Confiance** : confirmé.

### PLC-12 — `SECURITY.md` décrit un dépôt sans code ni version

- **Issue** : #3689 (fermée), #3720 (fermée).
- **Où** : `SECURITY.md:5-12` (« the implementation has not started », « none released yet »).
- **Quoi** : le dépôt publie des images versionnées (0.3.0) ; la politique dit à qui trouve une
  faille dans le code qu'il n'y a rien à signaler, et ne nomme aucune version suivie.
- **Proposition** : la mettre à jour (versions suivies, périmètre du code, délai de réponse) ;
  aucun EPIC ne la porte (`grep SECURITY.md docs/roadmap` : rien).
- **Confiance** : confirmé.

### PLC-13 — Les verrous du poste se scindent selon `XDG_RUNTIME_DIR`

- **Issue** : #3690 (fermée), #3721 (fermée).
- **Où** : `tools/src/wftools/slots.py:155-157` ; `tools/src/wftools/tracking.py:80-82`.
- **Quoi** : le registre des créneaux, les verrous des exécutions lourdes et celui du tableau de
  suivi vivent sous `$XDG_RUNTIME_DIR`, `/tmp` à défaut ; deux sessions dont l'une n'a pas la
  variable (`sudo`, `su`, service sans session de connexion) ne s'excluent plus.
- **Scénario** : deux worktrees prennent chacun le créneau 1, mêmes ports et mêmes projets Compose ;
  le `make slot-release` de l'un retire (`down --volumes`) la plateforme de l'autre.
- **Proposition** : un répertoire unique et stable par utilisateur (`/run/user/<uid>` s'il existe,
  sinon `~/.cache/waterfall`), ou refuser de tourner quand les deux registres existent.
- **Confiance** : plausible (mécanisme lu ; la coexistence des deux environnements sur le poste de
  l'auteur n'est pas établie).

### PLC-14 — `make roadmap` ne lit pas le skill du pilote

- **Issue** : #3683 (fermée), #3722 (fermée).
- **Où** : `tools/src/wftools/roadmap.py:43` (`AGENT_FILES`) ; `.claude/skills/pilote/SKILL.md` ;
  `tools/paths.toml:121-134`.
- **Quoi** : la règle « une commande `make` que cite un agent existe » ne couvre pas
  `.claude/skills/**`, qui ne réveille d'ailleurs que `repo`. Les cibles citées aujourd'hui
  (`make slots`, `make tracking`) existent.
- **Proposition** : ajouter `.claude/skills/**/*.md` à `AGENT_FILES` et à la famille `roadmap`.
- **Confiance** : confirmé.

### PLC-15 — DejaVu Sans : la notice d'Arev manque

- **Issue** : #3689 (fermée), #3723 (fermée).
- **Où** : `REUSE.toml` (annotation de `backend/src/waterfall/core/exchanges/fonts/DejaVuSans.ttf`,
  « 2003 Bitstream, Inc. », `Bitstream-Vera`) ; `LICENSES/Bitstream-Vera.txt` (aucune mention
  d'Arev ni de Tavmjong Bah).
- **Quoi** : la licence de DejaVu réunit celle de Bitstream Vera et celle des glyphes d'Arev
  (© 2006 Tavmjong Bah), dont l'avis doit accompagner toute copie.
- **Proposition** : ajouter le second titulaire à l'annotation et le texte de la licence de DejaVu.
- **Confiance** : plausible (lecture de droit, non vérifiée contre le fichier de la police).

## Points forts

- Workflows : empreintes partout, `permissions: contents: read` par défaut et élévations
  commentées, entrées non fiables passées par `env:`, `cache-clean.yml` réduit à `actions: write`.
- La porte nomme les seize travaux ; un `needs` sauté parce qu'un préalable a échoué est rattrapé
  par ce préalable ; `shared` de `paths.toml` réveille tout quand la sélection elle-même change.
- Caches : écrits après fusion (`front-cache.yml`, `images.yml`), lus seulement ailleurs.
- Miroir et image de travail tirés par empreinte ; aucune construction ne reçoit de secret ; fouille
  des images avant poussée (`images.py`).
- Verrous de `slots.py` par `flock` (rendus par le noyau à la mort du processus), écriture du
  registre par renommage atomique, arrêt des serveurs par port puis par PID.
- Dépendances : `uv.lock` et `pnpm-lock.yaml` versionnés, `--frozen` partout, `--no-dev` dans
  l'image, scripts d'installation de pnpm refusés, surcharges de sécurité motivées ; aucune licence
  incompatible avec l'AGPL repérée dans les dépendances directes.
- `make clean` ne touche qu'à des fichiers ignorés par git ; aucune cible ne tait un échec.

## Couverture

- **Lu en entier** : les 16 workflows, les 3 actions locales, `dependabot.yml`,
  `rulesets/merge-queue.json`, `actionlint.yaml`, le gabarit de pull request ; le `Makefile` ;
  `ruff.toml` ; `backend/pyproject.toml`, `backend/coverage-keycloak.toml`, `tools/pyproject.toml`,
  `frontend/package.json`, `frontend/pnpm-workspace.yaml` ; `REUSE.toml`, `.gitattributes`,
  `.gitignore` ; `SECURITY.md` ; `.claude/settings.json`, `.claude/skills/pilote/SKILL.md` ;
  `guard.py`, `gate.py`, `changes.py`, `paths.py`, `mergequeue.py`, `slots.py`, `coverage.py`,
  `codecoverage.py`, `sources.py` ; `tools/tests/test_families.py` ; `docs/dev/agents.md` ; les
  sections demandées du guide ; spec §4.7 ; EP-28.
- **Échantillonné** : `tools/paths.toml` (familles lues, liste des engendrés survolée) ;
  `images.py`, `mirror.py`, `production.py`, `tracking.py` (verrou et appels `gh` ; la logique du
  tableau non relue), `roadmap.py` ; `frontend/eslint.config.mjs` (règles désactivées et portée,
  pas les sélecteurs), `frontend/vitest.config.ts` ; `.claude/agents/epic-deliverer.md` (créneaux,
  fusion) ; `CONTRIBUTING.md` (début) ; `tools/tests/test_guard.py` (recherches) ; les Conceptions
  d'EP-01, EP-19, EP-20, EP-21 par recherche ; les Dockerfiles par `grep`.
- **Non lu** : `queue.py`, `lotsize.py`, `readmes.py`, `registry.py` ; les autres agents de
  `.claude/agents/` ; les modèles d'issue ; les autres tests de `tools/tests/` ; les textes de
  `LICENSES/` ; les dépendances transitives des verrous.
- **Non vérifiable ici** : les réglages de GitHub (jeux de règles réels, protection de `main`,
  visibilité des paquets), dont dépendent PLC-01 et PLC-10.
- **Trace** : deux sondes ont été lancées en lecture (`guard.refusal`, `sources.breaches`, `ruff
  check` sur l'entrée standard, `make -n test-back`) ; un script de sonde écrit par erreur dans le
  scratchpad et un `guard.cpython-313.pyc` créé sous `tools/src/wftools/__pycache__/` (ignoré par
  git) ont été supprimés ; `git status` est propre.

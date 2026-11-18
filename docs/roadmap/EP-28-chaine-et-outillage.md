---
id: EP-28
titre: Tenir la chaîne et les outils du dépôt
statut: en cours
depend_de: rien
famille: plateforme
issue: 3679
---

# EP-28 — Chaîne et outillage de développement

## Objet

Les revues des lots laissent des constats qui ne touchent aucun code du produit : la chaîne
d'intégration, les gardes du dépôt, les outils des tests, le guide. Ils étaient reportés vers EP-13
ou vers l'EPIC ouvert du moment, où ils n'avaient pas leur place. La revue complète du 2026-11-14 y
ajoute quinze constats sur la chaîne et l'outillage des agents, qu'aucun EPIC ne portait.

L'EPIC les rassemble. Il ne dépend d'aucun autre et ne clôt aucune exigence : il se glisse entre
deux EPICs fonctionnels, ou se joue par lots d'appoint.

## Ce qui en fait partie

- le relevé de couverture des exigences et la citation d'un critère propre à une US (#975, #3291,
  PLC-02) : US-2440 ;
- le garde des agents (#2417, PLC-03, PLC-07, PLC-11) : US-2450 ;
- les créneaux et les verrous du poste (#3343, PLC-04, PLC-13) : US-2460 ;
- les contrôles du dépôt — la file de fusion, les exemptions, les textes des agents (PLC-01, PLC-05,
  PLC-14) : US-2470 ;
- les familles de la chaîne (#850, #898, #958, PLC-06) : US-2480 ;
- les workflows — caches, veille, droits, traces, miroir (#3025, #3028, #3447, PLC-08, PLC-09,
  PLC-10) : US-2490 ;
- les gardes du Makefile (#3104, #3108) : US-2500 ;
- les tests du back et leurs supports (#818, #898, #899, #935, #946, #3137) : US-2510 ;
- les outils des exemples du contrat (#1007, #2457) : US-2520 ;
- les gardes de sources et les parcours du front (#839, #3149, #3431, #3472) : US-2530 ;
- le guide, la politique de sécurité et les licences (#851, #3041, #3057, #3161, PLC-12, PLC-15) :
  US-2540.

## Ce qui n'en fait pas partie

- les défauts du code livré, même mineurs : chacun va à l'EPIC qui touche ce code ;
- l'exploitation de la plateforme — EP-13 ;
- le refus de publier une version tant qu'une exigence F0 reste sans test (WF-QUA-0010-A) — EP-13,
  qui clôt l'exigence (décision de l'auteur du 2026-11-16, sur PLC-02) : `make requirements-release`
  se branche sur la publication de la 1.0, pas sur celles qui la précèdent. EP-28 ne fait que rendre
  le relevé vrai ;
- l'épinglage de la plateforme de production par empreinte plutôt que par étiquette (PLC-10) — EP-13
  (décision de l'auteur du 2026-11-16) : il touche le déploiement ;
- la restriction de `gh api graphql` aux mutations de la file (PLC-07) — rien : sa largeur est une
  décision consignée (`docs/dev/agents.md`, « La mise en file »), que l'auteur maintient le
  2026-11-16 ; le cadreur et les livreurs s'en servent aussi pour les sous-issues.

## Exigences réalisées

Aucune : l'EPIC ne réalise ni ne clôt d'exigence. Son tableau reste vide.

| Exigence | Titre | Portée | US |
|---|---|---|---|

US-2440 sert WF-QUA-0010-A sans la clore : le relevé cesse de compter un test qui ne s'exécute pas.
L'exigence, qu'EP-01 disait close « entière », passe « début — close en EP-13 » dans la table
d'EP-01 (décision de l'auteur du 2026-11-16, sur PLC-02) : la publication d'une version n'appelle
pas `make requirements-release`, et la v0.3.0 est publiée avec des exigences F0 non couvertes.

## Opérations du contrat

Aucune.

## Préalables

Rien pour démarrer. Deux attentes, qui ne retiennent chacune qu'une part d'une US :

- US-2460 touche `tools/src/wftools/heavyturns.py`, qu'EP-26 écrit : elle attend EP-26 dans `main` ;
- l'extraction de `mockdata.py` (US-2520) attend EP-10 dans `main`, qui écrit ce fichier.

## Définition de fini

- chaque constat reçu est corrigé, ou clos avec sa raison ;
- `make check-all` passe sur `epic/EP-28`, ainsi que `make roadmap` et `make readmes` ;
- `make requirements` présente « non exécuté » un test sauté, et ne compte ni lui ni une citation
  écrite dans un commentaire ; il reconnaît `[US-nnnn]` sans y voir une exigence ;
- lancé par un `python3` antérieur à 3.14, le hook du garde refuse `pkill -f make` au lieu de le
  laisser passer ; dans une session de ce dépôt, `rm -rf .git/refs` et un `pkill` écrit dans le
  corps d'un here-document remis à `bash` sont refusés avant d'être exécutés ;
- `make merge-queue-check EPIC=EP-nn` échoue sur une branche dont aucun jeu de règles actif n'exige
  le contrôle `gate` ;
- un livreur arrêté sans avoir rendu son créneau ne bloque plus la reprise de son lot ;
- une pull request qui ne change que `ruff.toml` lance les contrôles du back ;
- un parcours en échec dans `service / paths` laisse sa trace Playwright en artefact du job ;
- `SECURITY.md` nomme les versions suivies.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC.

- #818 — back : un test de la planification nomme un mot de passe qu'il ne lit plus ;
- #839 — front : les gardes de sources retirent pour un commentaire ce qui suit un /* écrit dans une
chaîne ;
- #850 — outil : plus aucun test ne dit qu'une page ne réveille pas la famille front-image ;
- #851 — doc : le Contrôle de la règle des actions serveur dit lire chaque source du build ;
- #898 — outil : trois mineurs du tour 2 d'US-0420 (ligne d'installation laissée, témoin des rôles
hors famille keycloak, migrations qui exigent Redis) ; le premier est corrigé (vérification du
2026-11-14), les deux autres restent ;
- #899 — test : deux mineurs du tour 3 d'US-0420 (verrou et processus hors du try, diagnostic perdu)
;
- #935 — outil : la fixture logs de conftest pose de faux secrets de la plateforme dans
l'environnement ;
- #946 — outil : quatre finitions du client de contrat fermé des tests du back ;
- #958 — outil : les tests du back migrent en superutilisateur, une migration qui l'exige ne casse
qu'après fusion ;
- #975 — outil : make requirements compte les citations des tests ignorés (fixme, skip) ;
- #1007 — outil : les identifiants de corrélation des exemples n'ont pas de registre, deux lots
parallèles prennent le même ;
- #2417 — outil : le garde laisse passer des formes voisines de find -exec rm, xargs rm et rm -rf
sur .git, et make merge-queue non adjacent ;
- #2457 — outil : mockdata.py au plafond de 1000 lignes ;
- #3025 — outil : les montées d'images de Dependabot et le miroir de la chaîne ;
- #3028 — outil : quatre finitions du miroir de la chaîne (test d'image nue, messages, Dependabot
dans le guide), et une cinquième, en commentaire : un refus passager de ghcr.io à la création d'un
paquet ;
- #3041 — outil : le client PostgreSQL 18 du runner dit « d'Ubuntu 26.04 » alors qu'il vient du
dépôt PGDG ;
- #3057 — documentation : une ligne du paragraphe d'US-1920 dépasse la largeur du fichier ;
- #3104 — outil : le refus à la lecture de check-service et check-all en TIER=full n'a pas de test ;
- #3108 — outil : trois mineurs du deuxième tour d'US-1910/L3 — la forme de SHARD hors e2e-service,
une apostrophe dans le $(shell) de la garde, l'exclusion écrite en dur du test des durées ;
- #3137 — back : des tests comparent l'année prise par le test à celle que le service prend à la
requête, et échouent au passage du nouvel an — à corriger avant le 31 décembre 2026 (décision de
l'auteur du 2026-11-14) ;
- #3149 — outil : test_e2ebrowser, deux tests attendent une seconde fixe avant d'interrompre le
shell ;
- #3161 — outil : le défaut n° 22 de typescript.md, « une exception et une seule », ambigu pour un
état vidé quand une prop le relaie ;
- #3291 — outil : citer un critère propre à une US dans un test, sans emprunter une exigence
(WF-QUA-0010) — relevé par la revue d'US-2160/L2, reporté d'EP-25 (décision de l'auteur du
2026-11-14) ;
- #3431 — front : trois mineurs du parcours du thème de connexion (revue 2 d'US-2190) — reporté
d'EP-25 (décision de l'auteur du 2026-11-15) ;
- #3343 — outil : le marqueur d'une mesure exclusive est cru sous la mesure d'un autre livreur —
reporté d'EP-26 (décision de l'auteur du 2026-11-15) ;
- #3447 — outil : les traces Playwright d'un parcours en échec dans la file ne sont pas versées en
artefact — reporté d'EP-26 (décision de l'auteur du 2026-11-15) ; leur absence a laissé déduite,
non lue, la cause de #3266 (#3448) ;
- #3472 — outil : trois commentaires de frontend/e2e/server-action.ts dépassent 100 caractères —
relevé par la revue d'US-2110/L2, reporté d'EP-25.

Quatre constats de la ventilation ont été fermés, corrigés, à la vérification du 2026-11-14 (code lu
sur `main`, 7d5370d4), et ne sont repris par aucune US : #2255 (les leviers de l'audit du
2026-11-05), #2388 (`projects.spec.ts` rejoué), #2452 (la clé apt de PostgreSQL), #2643 (le binaire
d'`actionlint-py`).

Revue complète du 2026-11-14, « chaîne, Makefile, dépendances, licences, outillage des agents »
(`docs/reviews/2026-11-14-revue-complete/chaine-outillage.md`) : ses quinze constats n'avaient ni
issue ni EPIC, et tiennent tous sur `main` au 2026-11-16. L'EPIC les prend tous (décision de
l'auteur du 2026-11-16) ; le cadrage a ouvert une issue pour chacun.

- PLC-01, #3709 — le jeu de règles de la file n'exige aucun contrôle, et `merge-queue-check` ne le
  vérifie pas ;
- PLC-02, #3710 — WF-QUA-0010-A est close « entière » ; ni le refus de publier ni la règle des tests
  non exécutés ne sont tenus ;
- PLC-03, #3711 — le garde des agents est inerte, sans un mot, quand `python3` n'est pas un 3.14 ;
- PLC-04, #3712 — à N = 1, le créneau d'un livreur arrêté sur limite d'usage ou planté bloque la
  série ;
- PLC-05, #3713 — `make sources` laisse passer des commentaires d'exemption que Ruff et coverage.py
  honorent ;
- PLC-06, #3714 — trois changements qui ne réveillent pas les contrôles qu'ils peuvent casser ;
- PLC-07, #3715 — formes réalistes que le garde laisse passer ;
- PLC-08, #3716 — `front-cache.yml` écrit aussi le cache d'uv, mais ne se déclenche que sur
  `frontend/**` ;
- PLC-09, #3717 — la veille ne suit ni les actions locales ni `deploy/e2e`, et le guide ne les nomme
  pas ;
- PLC-10, #3718 — `packages: write` dans deux travaux de `pull_request`, et une immuabilité que seul
  l'outil tient ;
- PLC-11, #3719 — sous un `python3` autre que 3.14, le Makefile accuse `WATERFALL_SLOTS` ;
- PLC-12, #3720 — `SECURITY.md` décrit un dépôt sans code ni version ;
- PLC-13, #3721 — les verrous du poste se scindent selon `XDG_RUNTIME_DIR` ;
- PLC-14, #3722 — `make roadmap` ne lit pas le skill du pilote ;
- PLC-15, #3723 — DejaVu Sans : la notice d'Arev manque.

Relevés au cadrage, le 2026-11-16, sur les passages de Dependabot que l'auteur a déclenchés à la
main pour #3025 (exécutions 43954975724 et 43954994167) et sur ses échecs depuis le 2026-10-21. Le
second a son issue, #3724 ; le premier est la réponse à #3025.

- la veille des images est éteinte depuis le miroir : le passage `docker` ne trouve plus aucune
  dépendance dans ses cinq répertoires — `FROM ${WATERFALL_MIRROR}…` lui est illisible —, et le
  passage `docker-compose` ne lit que la seule référence sans préfixe, le `caddy` de
  `compose.demo.yaml` (#3671), non celui de `compose.service.yaml` ni de `compose.prod.yaml`. La
  décision du 2026-11-13 sur #3025 (s'en tenir au geste manuel) supposait des pull requests de
  montée, qui ne viennent plus ; l'auteur retient le 2026-11-16 un manifeste que Dependabot lit ;
- les mises à jour de sécurité du front échouent depuis le 2026-10-21 (`vite`, `happy-dom`, `next`,
  `undici`, `minimatch`) par `security_update_not_possible` : la version corrigée d'une dépendance
  transitive est hors de ce que son parent admet, et Dependabot abandonne. Rien dans le guide ne
  dit quoi faire ; une alerte haute reste ouverte, sur `@faker-js/faker` (alerte 68). Un `override`
  de pnpm vers faker 10 casserait Prism : la version vulnérable (5.5.3) vient de
  `postman-collection` 4.5.0, sous `@stoplight/http-spec`, qui la charge en CommonJS
  (`require('@faker-js/faker/locale/en')`) et appelle `faker.datatype.number`, que faker 10, ESM
  seul, n'a plus. Prism est un outil de développement : l'auteur retient le 2026-11-16 d'attendre
  sa montée, l'alerte reste ouverte et US-2490 ne la traite pas.

## Conception

### Ce qui change, et ce qui ne change pas

L'EPIC ne touche ni le contrat, ni le noyau, ni une table : aucune migration, aucune opération. Du
code du produit, il ne touche que le lanceur des migrations (`backend/src/waterfall/migrations/`,
#898) et les tests. Tout le reste est dans `tools/`, le Makefile, `.github/`, `.claude/`, les tests
du back, les parcours et les gardes du front, et les documents.

Chaque US porte le texte du guide qui dit ce qu'elle change ; US-2540 ne porte que les textes
qu'aucune autre US ne touche.

### Le relevé de couverture (US-2440)

Le relevé reste **lu dans les fichiers de test, sans les lancer** — c'est le principe de
`wftools.coverage`, et ce qui le rend calculable sur un poste. Un test non exécuté se reconnaît donc
à ce qu'il déclare, pas à un rapport d'exécution.

- **TypeScript.** `typescript_citations` ne lit plus tout le fichier : elle cherche les appels
  `it(`, `test(` et leurs variantes, et lit les citations dans leur titre — ou dans celui du
  `describe(` qui les englobe, tenue pour exécutée si un test du groupe l'est (#3751). Un appel
  `.skip(`, `.fixme(` ou `.todo(`, ou un appel sous un `describe.skip(` ou `describe.fixme(`, donne
  une citation « non exécuté ».
- **Un saut dans le corps d'un test** (US-2440/L3, décision de l'auteur du 2026-11-17, #3749). Le
  premier lot ne le reconnaissait pas : `test.skip(condition, …)` écrit dans le corps d'un test
  laissait sa citation « exécutée », et soixante-six tests de `frontend/e2e/` qui citent une
  exigence se sautent ainsi selon la plateforme. Le relevé le lit désormais, toujours dans les
  fichiers : un appel `test.skip(` ou `test.fixme(` dont le premier argument n'est pas un titre,
  et qui se trouve dans un test (ou, à défaut, dans le groupe qui le tient), est un saut
  conditionnel. Dont le premier argument est exactement `inService` ou `!inService` (le drapeau de
  `frontend/e2e/mode.ts`), le test reste « exécuté » : il se joue dans l'un des deux parcours,
  `make e2e` (`ci.yml`, famille `end-to-end`) ou `make e2e-service` (`service.yml`, famille
  `end-to-end-service`), et les deux tournent dans la chaîne ; sa citation est donc vraie pour la
  chaîne entière. Tout autre premier argument — `true`, `!inService || manager === undefined`, une
  autre condition — rend la citation « non exécuté » : un test qui se saute pour une raison
  que la chaîne ne tient pas ne prouve rien. `test.fail(` reste ce qu'il est, une annotation qui
  n'empêche pas le test de se jouer ; `it.skipIf(` et `it.runIf(` restent non vus, aucun test du
  dépôt n'en porte, et le guide le dit. Les trois tests qui sautent aujourd'hui par `test.skip(true,
  SERVICE_ONLY)` sous un `if (!inService || manager === undefined)` (`revision-cycle.spec.ts`,
  `projects.spec.ts`, deux fois) écrivent le saut sous la forme reconnue, `test.skip(!inService,
  SERVICE_ONLY)`, suivi de la garde de `manager` : le lot ne laisse pas trois citations devenir
  « non exécuté » par la seule écriture. *Option écartée* : ne rien changer (option 1 de #3749) —
  une citation vraie pour la chaîne, mais le relevé n'attraperait jamais un saut futur qui ne
  dépend pas du parcours. *Option écartée* : tenir les soixante-six tests pour « non exécuté »
  (option 3) — la citation y serait fausse, chacun s'exécute dans l'un des parcours de la chaîne.
  Un test `!inService` n'a de parcours de service que s'il porte `@shared` (`playwright.config.ts`,
  projet `shared`) : les soixante-trois d'aujourd'hui le portent ; le lot ne contrôle pas
  l'étiquette, l'écart est noté ici.
- **Python.** Un test qui peut se sauter porte la marque `@pytest.mark.unexecuted("<raison>")`, sur
  le test, sa classe ou son module, lue par `ast` comme `requirement`. Un crochet des `conftest.py`
  du back et des outils fait **échouer** un test qui se saute sans la porter : la marque ne peut
  pas manquer. Les tests du XSD MSPDI (`test_msproject.py`, `test_msproject_export.py`,
  `test_msproject_corpus.py`) la reçoivent. Un test marqué est « non exécuté » au relevé même sur un
  poste qui a le XSD : le relevé dit ce que la chaîne prouve.
- **`Citation`** gagne un état, exécuté ou non ; `Report` ne compte comme couverture que les
  citations exécutées, et liste les autres sous leur exigence avec la mention « non exécuté ».
- **`[US-nnnn]`.** Dans un titre TypeScript, `[US-nnnn]` ; en Python,
  `@pytest.mark.story("US-nnnn")`. Le relevé les range à part, « critères propres aux US », hors du
  compte des exigences ; une US qu'aucun fichier de `docs/roadmap` ne porte fait échouer, comme un
  identifiant d'exigence inconnu.

### Le garde (US-2450)

- **Un lanceur.** Le hook et le Makefile ne lancent plus `guard.py` ni `slots.py` par `python3` :
  ils lancent `tools/src/wftools/launch.py <outil>`, un fichier court, écrit dans la syntaxe de
  Python 3.8, qui vérifie la version de l'interpréteur puis exécute l'outil nommé. Pour `guard`, il
  sort en code 2 — le refus, pour Claude Code — quand l'interpréteur est antérieur à 3.14, et quand
  le garde lève en jugeant : le garde échoue fermé. Pour `slots`, il dit la version attendue et
  sort en erreur. Le test d'`ast` lit `launch.py` avec la grammaire de 3.8
  (`ast.parse(…, feature_version=(3, 8))`) ; `guard.py` et `slots.py` gardent la syntaxe de 3.14 et
  leurs imports sous `TYPE_CHECKING`, sans exemption dans `ruff.toml`.
- **Le Makefile** (ligne de `WATERFALL_PROCESSORS`) ne jette plus la sortie d'erreur de l'outil
  quand sa sortie est vide : il dit que l'outil n'a pas tourné, et relaie sa raison.
- **Les formes.** `_names_git` ne cumule plus sur toute la ligne mais par tube ; `rm`, `mv` et
  `truncate` jugent un opérande littéral qui est `.git`, passe par `.git/` ou s'ouvre par `.git`
  suivi d'un joker ; `find` juge `-name .git` suivi d'un `-exec rm` ou `-delete`. Le corps d'un
  here-document remis à `bash`, `sh` ou `zsh`, et l'argument littéral d'un `echo` ou `printf` dont
  le tube finit dans un de ces shells, sont jugés comme une ligne de commande. `kill-port` devient
  un nom refusé, derrière `npx`, `pnpm dlx` ou seul ; `uv run` devient un préfixe, comme `env` ;
  `gmake` vaut `make` ; `-m wftools.mergequeue create` est refusé. La regex de repli admet des
  options et des affectations entre `make` et `merge-queue`.
- **La taille.** `guard.py` a 923 lignes. Le lot en extrait d'abord le jugement des formes de
  `.git` et des verrous dans un module voisin, puis ajoute : les deux restent sous 1 000 lignes.

### Les créneaux et les verrous (US-2460)

- **La reprise.** `make slot LOT=<identifiant>` écrit l'identifiant du lot en troisième ligne du
  fichier du créneau. Tous les créneaux pris, `claim` reprend celui qu'un **autre worktree tient
  pour le même lot** : il retire ce qui y reste (`remove`, comme pour un créneau abandonné), puis
  l'écrit au nom du nouveau worktree. Sans `LOT`, rien ne change. Le pilote ne lance qu'un livreur
  par lot : deux worktrees vivants du même lot n'existent pas. `epic-deliverer` prend son créneau
  avec `LOT` ; `make slots` montre le lot de chaque créneau.
- **Le répertoire.** Une seule fonction, dans `heavyturns.py`, que `slots.py` et `tracking.py`
  appellent : `WATERFALL_RUNTIME_DIR` s'il est posé (les tests), sinon `/run/user/<uid>` s'il
  existe, sinon `/tmp`. `XDG_RUNTIME_DIR` n'est plus lu. Dans une session ordinaire, c'est le
  répertoire d'avant : les outils des branches d'EPIC qui n'ont pas ce lot s'excluent encore avec
  ceux qui l'ont. Les noms des fichiers ne changent pas. Les tests qui posaient `XDG_RUNTIME_DIR`
  posent `WATERFALL_RUNTIME_DIR`.
- **Le marqueur.** Un exclusif écrit un jeton — son PID et l'instant de sa prise — dans le fichier
  de la barrière, et pose `WATERFALL_SLOTS_HELD=exclusive:<jeton>`. `held_above` ne croit le
  marqueur que si la barrière est tenue **et** porte ce jeton. Un marqueur sans jeton, posé par un
  outil d'avant, est cru comme aujourd'hui.

### Les contrôles du dépôt (US-2470)

- **La file.** `check` exige, parmi les jeux actifs qui visent la branche, un jeu qui porte
  `merge_queue` **et** un jeu — le même ou un autre — qui porte `required_status_checks` avec le
  contexte `gate`. Le modèle ne reçoit pas cette règle : elle vit dans « epic protection », qui vise
  `epic/*`. Le modèle reçoit `required_signatures`, que les trois files d'aujourd'hui portent ; et
  `check` dit l'écart entre les types de règles du jeu de la file et ceux du modèle.
- **Les exemptions.** `_HASH_SUPPRESSION` s'étend aux formes de PLC-05 ; les `Dockerfile` et les
  fichiers `*.Dockerfile` entrent dans les sources lues, pour `hadolint ignore`.
- **Le skill.** `AGENT_FILES` gagne `.claude/skills/**/*.md`, et la famille `roadmap` ce chemin.

### Les familles (US-2480)

- `tools/paths.toml` reçoit les chemins de PLC-06 et de #898. `test_families.py` lit, en plus de
  `python <script>`, les `python3 $(CURDIR)/…` des variables du Makefile et les montages `./…:ro` de
  `compose.service.yaml`.
- **La migration en superutilisateur (#958).** Un test du back crée une base neuve par
  `deploy/compose/waterfall-database.sql` — le script de la production, qui fait le propriétaire
  `NOSUPERUSER` — puis y applique toutes les migrations **en tant que ce propriétaire**. Il tourne
  avec les tests du back, au palier rapide : une migration qui exige le superutilisateur casse la
  pull request qui la porte.

### La chaîne (US-2490)

- **`front-cache.yml`** se déclenche aussi sur `backend/uv.lock` et `tools/uv.lock`.
- **`dependabot.yml`** : `directories: ["/", "/.github/actions/*"]` pour `github-actions`, et
  `/deploy/e2e` dans l'entrée `docker` — ses images ne sont pas de Docker Hub et n'ont pas de
  préfixe.
- **Le manifeste des images.** `deploy/images/Dockerfile` ne sert à aucune construction : il porte
  une ligne `FROM <image>:<étiquette>@sha256:…` par image de Docker Hub que le dépôt épingle, sans
  préfixe, dans la forme que Dependabot lit. L'entrée `docker` de `dependabot.yml` ne suit plus que
  `/deploy/images` et `/deploy/e2e` ; l'entrée `docker-compose` disparaît. Un test des outils tient
  que toute référence d'image de Docker Hub du dépôt — préfixée ou non, dans un `Dockerfile` ou un
  fichier Compose — est celle du manifeste, étiquette et empreinte, et que le manifeste n'en porte
  pas d'autre. `make mirror-sync` (`wftools.mirror sync`) recopie le manifeste dans ces
  références. Une montée de Dependabot ne change donc que le manifeste, et sa chaîne échoue sur ce
  test en nommant les deux gestes : `make mirror-sync`, puis `make mirror PUSH=yes`, qu'une
  personne pousse sur la branche de la pull request.
- **`e2e-image`** devient deux travaux de `ci.yml` : la recherche, au palier rapide, avec
  `packages: read` ; la construction et la publication, au seul palier complet, avec
  `packages: write`. Les travaux qui lisent l'image — tous du palier complet — nomment le second.
  `gate.py` et son test comptent le travail de plus.
- **Les traces.** `service.yml`, `e2e.yml` et le travail `e2e` de `ci.yml` versent sur échec
  `frontend/test-results/` par `actions/upload-artifact`, sept jours, sous un nom qui porte la part.
  Playwright y garde déjà la trace d'un test en échec (`trace: "retain-on-failure"`).
- **Le miroir.** `fill` réessaie une fois un `denied` reçu à l'écriture, par `registry.again`, qui
  réessaie déjà les requêtes.

### Le reste (US-2500 à US-2540)

- **Le Makefile (US-2500).** Une seule garde de la forme de `SHARD` pour tous les buts des
  parcours ; la valeur passe à `wftools.e2eparts` par l'environnement.
- **Les tests du back (US-2510).** L'année se fige par le `monkeypatch` du `utc_now` du module,
  comme #3120 et #3123. Le lanceur des migrations lit `PlatformSettings`, qui existe, au lieu de
  `load_settings()`.
- **Les identifiants de corrélation (US-2520).** L'identifiant d'un exemple nouveau **se dérive de
  son nom** : le préfixe de l'univers témoin, puis douze chiffres hexadécimaux d'une empreinte du
  nom. Deux lots ne peuvent plus prendre le même sans donner le même nom. Les exemples d'aujourd'hui
  gardent leur identifiant : leurs noms sont figés dans une liste, et un test tient que tout exemple
  hors de cette liste porte l'identifiant dérivé.
- **`mockdata.py` (US-2520).** La part des volumes — `volumes()` et ses aides, environ 170 lignes —
  passe dans `mockvolumes.py` ; les catégories, les taux et leur grille, que `volumes()` lit et que
  `named()` écrit, passent dans `mockrates.py`, pour que `volumes()` et `named()` ne s'importent
  pas l'un l'autre (import circulaire).

### Tables et migrations

Aucune.

### Modules touchés

- `tools/src/wftools/` : `coverage`, `guard` et son module extrait, `launch` (nouveau), `slots`,
  `heavyturns`, `tracking`, `mergequeue`, `sources`, `roadmap`, `mirror`, `gate`, `e2eparts`,
  `mockdata` et ses modules extraits (`mockvolumes`, `mockrates`), `mockrefusals` ;
  `tools/paths.toml` ; les tests des outils ;
- le Makefile ; `.github/workflows/` (`ci.yml`, `service.yml`, `e2e.yml`, `front-cache.yml`),
  `.github/dependabot.yml`, `.github/rulesets/merge-queue.json` ;
- `.claude/settings.json`, `.claude/agents/epic-deliverer.md`, le skill `pilote` ;
- `backend/src/waterfall/migrations/` (`runner.py`, `env.py`) ; `backend/tests/` ;
- `frontend/src/test/`, les quatre gardes de sources, `frontend/e2e/` ;
- `docs/dev/`, `docs/api/README-fr.md` et `README.md`, `INSTALL.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, `REUSE.toml`, `LICENSES/`.

Aucun module du noyau.

### Ordre de construction

`epic/EP-28` se tire de `main`. Rien n'ordonne les US entre elles, à trois réserves près :

1. US-2510 d'abord, pour #3137, qui doit être dans `main` avant le 31 décembre 2026 ;
2. US-2460 après EP-26 dans `main` (`heavyturns.py`) ; la part de `mockdata.py` d'US-2520 après
   EP-10 dans `main`, qui écrit ce fichier ;
3. dans US-2450, le lanceur avant les formes : il change la ligne du hook et celle de `SLOTS`.

EP-26 et EP-27 touchent le Makefile, `slots.py`, `mirror.py`, `ci.yml`, `service.yml` et
`tools/paths.toml` ; EP-10, `mockdata.py` et `tools/paths.toml`. Leurs conflits avec EP-28 se
règlent à chaque reprise de `main` dans `epic/EP-28`.

### Décisions

- **Un test non exécuté se déclare** (marque `unexecuted`, que le crochet rend obligatoire) —
  écarté : alimenter le relevé d'un rapport d'exécution (JUnit), que proposait PLC-02. Il faudrait
  réunir dans le travail du relevé les rapports des quatre parts des tests du back, et le relevé ne
  se calculerait plus sur un poste sans tout lancer.
- **Un lanceur en syntaxe ancienne** — écartés : importer `Callable` à l'exécution dans `guard.py`
  sous une exemption de `ruff.toml` (la proposition de PLC-03), qui ne ferme que cette faute-là et
  laisse le garde ouvert à la prochaine syntaxe de 3.14 ; et relancer le garde par `uv run` sous un
  interpréteur ancien, qui ferait dépendre chaque commande d'un agent de l'état d'un environnement
  virtuel. Conséquence, voulue : sur un poste dont le `python3` n'est pas un 3.14, aucune commande
  de l'outil `Bash` ne passe tant que le poste n'est pas réparé.
- **Le lot dans le registre des créneaux** — écarté : que le pilote lance `make slot-release` dans
  le worktree du livreur arrêté. Le pilote ne fait que lancer des livreurs, et il lui faudrait
  savoir qu'un livreur est arrêté et non lent.
- **`/run/user/<uid>`, sinon `/tmp`** — écartés : `~/.cache/waterfall`, où un verrou vivrait sur un
  répertoire personnel parfois monté par le réseau ; et refuser de tourner quand deux registres
  existent, qui arrête le travail au lieu de l'empêcher de se scinder.
- **Le contrôle exigé se vérifie, il ne s'ajoute pas au modèle** — écarté : porter
  `required_status_checks` au modèle de la file. Le contrôle exigé vit déjà dans « epic
  protection » ; l'écrire deux fois, c'est deux réglages à tenir d'accord.
- **Un test qui migre en propriétaire** (#958) — écartés : migrer tous les tests du back en
  `NOSUPERUSER`, qui touche chaque fixture alors que les tests créent des rôles et des bases ; et
  réveiller la famille `production` sur les migrations, qui n'attrape la faute qu'au palier
  complet, dans la file.
- **L'identifiant de corrélation dérivé du nom** (#1007) — écartés : une plage par lot ou une ligne
  de registre, que chaque cadrage devrait tenir ; et un outil qui donne le prochain numéro libre,
  que deux lots tirés de la même branche recevraient tous deux.
- **`e2e-image` scindé** — contre le commentaire de `ci.yml`, qui gardait un seul travail pour que
  les travaux qui lisent l'image n'en nomment pas deux (décision de l'auteur du 2026-11-16, sur
  PLC-10) : ils sont tous du palier complet et ne nomment que le travail qui publie.
- **WF-QUA-0010-A rouverte** — contre la table d'EP-01, qui la disait close « entière » (décision de
  l'auteur du 2026-11-16) : elle passe « début — close en EP-13 ».
- **`gh api graphql` reste large** — la décision de `docs/dev/agents.md` est maintenue ; écarté : ne
  l'admettre que pour les mutations de la file (PLC-07).
- **Un manifeste des images que Dependabot lit** (#3025, décision de l'auteur du 2026-11-16, qui
  remplace celle du 2026-11-13 : le geste manuel reste, mais sur une pull request qui existe) —
  écarté : rendre aux fichiers des références sans préfixe et remapper vers le miroir à la
  construction et au démarrage, qui réécrit le miroir d'US-1900 et tous ses appels.
- **Pas de contrôle de la longueur des commentaires** (#3472) et **pas de correction de
  `test_e2ebrowser`** (#3149) : les raisons sont aux écarts d'US-2530.

---

## US-2440 — Le relevé de couverture ne compte que ce qui s'exécute, et un critère propre à une US se cite `[US-nnnn]`

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3681

**En tant que** développeur, **je veux** que `make requirements` ne compte comme couverture ni un
test sauté ni une citation écrite dans un commentaire, et qu'un test qui porte un critère propre à
une US cite cette US plutôt qu'une exigence qu'il ne vérifie pas, **afin que** le relevé ne dise
couverte que l'exigence qu'un test exécuté vérifie (#975, #3291, PLC-02).

**Critères d'acceptation.**

- propre à l'US : `typescript_citations` (`tools/src/wftools/coverage.py`) ne lit une citation que
  dans le titre d'un `it(` ou d'un `test(`, ou du `describe(` qui les englobe ; une citation dans un
  commentaire ne compte plus — les
  huit d'aujourd'hui (dont `frontend/e2e/admin.spec.ts` et `frontend/e2e/service/session.spec.ts`)
  sortent du relevé (PLC-02) ;
- propre à l'US : une citation dans le titre d'un `test.fixme`, `test.skip`, `it.skip` ou `it.todo`
  est présentée « non exécuté » et ne couvre pas son exigence ; un test des outils le prouve sur un
  fichier où un même identifiant est cité par un `test(` et par un `test.fixme(` : le premier
  couvre, le second sort « non exécuté » (#975) ;
- propre à l'US : un test Python sauté à l'exécution — ceux de la validité contre le XSD MSPDI, que
  la chaîne saute faute de `WATERFALL_MSPDI_SCHEMA_PATH` — est présenté « non exécuté » et ne couvre
  pas l'exigence qu'il cite ; un même identifiant cité par un test joué et par un test sauté sort
  couvert par le premier seul (PLC-02) ;
- propre à l'US : `make requirements-release` échoue sur une exigence F0 que seuls des tests non
  exécutés citent, en la nommant ;
- propre à l'US : un test Python qui se saute sans le déclarer échoue ;
- propre à l'US : un test qui porte un critère propre à une US cite `[US-nnnn]` dans son titre, ou
  par une marque en Python ; `make requirements` reconnaît la forme, ne la compte pas comme la
  couverture d'une exigence, et refuse une US qu'aucun fichier de `docs/roadmap` ne porte (#3291) ;
- propre à l'US : les sept tests de présentation des graphiques d'US-2160
  (`indicators/charts.dom.test.tsx`, `portfolio/portfolio.dom.test.tsx`,
  `risks/risk-bubble-chart.dom.test.tsx`) citent `[US-2160]` et perdent leur mention « not the Vérif
  of WF-IHM-0070-A » ; WF-IHM-0070-A reste couverte par les tests qui portent son Vérif ;
- propre à l'US : le guide (`docs/dev/README-fr.md` et `README.md`, « Un test qui cite son
  exigence ») dit la forme `[US-nnnn]`, ce qu'est un test non exécuté et ce que le relevé en fait ;
  `docs/dev/agents.md` y renvoie.

**Hors périmètre.**

Le branchement de `make requirements-release` sur la publication d'une version : EP-13, qui clôt
WF-QUA-0010-A.

---

## US-2450 — Le garde refuse quand il ne peut pas juger, et voit les formes écrites en clair

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3682

**En tant que** développeur, **je veux** que le garde des agents refuse une commande quand il ne
peut pas s'exécuter, et qu'il attrape les formes voisines de celles qu'il refuse déjà quand elles
sont écrites en clair, **afin qu'**un agent ne travaille jamais sans garde sans que rien le dise
(#2417, PLC-03, PLC-07, PLC-11).

**Critères d'acceptation.**

- propre à l'US : lancé comme le fait le hook de `.claude/settings.json` par un `python3` antérieur
  à 3.14, le garde sort en code 2 sur `pkill -f make` avec un message qui dit que le garde est
  inutilisable et quelle version il attend ; il ne lève plus `NameError` à l'import. Un test le
  lance par l'interpréteur le plus ancien présent sur le poste, et un test d'`ast` refuse, dans le
  fichier que le hook et le Makefile lancent par `python3` hors de `uv run`, toute syntaxe
  postérieure à Python 3.8 (PLC-03) ;
- propre à l'US : quand le garde lève en jugeant une commande, le hook refuse (code 2) au lieu de
  laisser passer ;
- propre à l'US : sous un `python3` autre que 3.14, `make -n test-back` dit que l'outil des créneaux
  n'a pas pu tourner et pourquoi, au lieu de « WATERFALL_SLOTS must be an integer from 1 to 9, not
  '' » ; un test de `tools/tests/test_e2eworkers.py` le tient (PLC-11) ;
- propre à l'US : le garde refuse, chacune avec son test : `find . -name .git -exec rm -rf {} +` et
  `find … -prune -exec rm -rf` ; `rm -rf .git/refs`, `rm -rf .git*`, `mv .git …` et
  `truncate -s0 .git/index.lock` ; dans une ligne que le scanner ne sait pas découper,
  `make -j2 merge-queue …` et `make EPIC=x merge-queue …` (#2417, PLC-07) ;
- propre à l'US : le garde juge le corps d'un here-document remis à un shell (`bash <<'EOF'`,
  `sh -s <<EOF`) et le texte qu'un `echo` ou un `printf` envoie par un tube à `bash` ou `sh` : un
  `pkill` qui s'y trouve est refusé (PLC-07) ;
- propre à l'US : le garde refuse `npx kill-port` et `pnpm dlx kill-port`, `uv run pkill …`,
  `gmake merge-queue` et `python -m wftools.mergequeue create`, sous `uv run` ou non (PLC-07) ;
- propre à l'US : les deux faux positifs de #2417 passent : `find .git -name x; ls | xargs rm`, où
  `.git` n'est pas nommé dans le tube du `xargs`, et `make -C merge-queue …` ;
- propre à l'US : le guide et `docs/dev/agents.md` disent les limites connues du garde, qu'il ne
  code pas : une cible calculée (`rm -rf $(git rev-parse --git-dir)`, `find "$GIT" | xargs rm`),
  `xargs sh -c`, et la largeur de `gh api graphql`, décision consignée ;
- propre à l'US : `tools/src/wftools/guard.py` reste sous 1 000 lignes.

**Hors périmètre.**

La restriction de `gh api graphql` aux mutations de la file : écartée (« Ce qui n'en fait pas
partie »).

---

## US-2460 — Un créneau abandonné se reprend, et les verrous du poste ne se scindent pas

- **statut** : en cours
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3690

**En tant que** développeur, **je veux** qu'un livreur arrêté sans avoir rendu son créneau ne
retienne pas la série, que tous les verrous du poste vivent au même endroit quelle que soit la
session, et qu'un marqueur de mesure exclusive ne vaille que pour la mesure qui l'a posé, **afin
que** deux exécutions ne se croient jamais seules sur le poste et qu'aucune n'attende sans fin
(#3343, PLC-04, PLC-13).

**Critères d'acceptation.**

- propre à l'US : tous les créneaux pris, dont un par le worktree d'un livreur arrêté sans
  `make slot-release`, l'instance qui reprend le même lot obtient un créneau au lieu de rendre
  « aucun créneau libre » ; un test de `claim` le prouve, et le créneau d'un autre lot en vol n'est
  jamais repris (PLC-04) ;
- propre à l'US : `.claude/agents/epic-deliverer.md`, le skill `pilote` et `docs/dev/agents.md`
  disent la reprise, à la place de « le créneau reste pris » ;
- propre à l'US : le registre des créneaux, les verrous des exécutions lourdes et celui du tableau
  de suivi vivent sous un même répertoire, qui ne dépend pas de la présence de `XDG_RUNTIME_DIR` :
  deux sessions du même utilisateur, dont l'une n'a pas la variable, s'excluent ; un test le prouve
  pour `slots.py` et pour `tracking.py` (PLC-13) ;
- propre à l'US : un `slots.py run` qui hérite d'un marqueur `WATERFALL_SLOTS_HELD` posé par une
  autre mesure exclusive que celle qui tient la barrière prend son tour ; un test : un marqueur au
  jeton étranger, la barrière tenue par un autre exclusif, l'appel attend son tour (#3343) ;
- propre à l'US : le guide (`docs/dev/README-fr.md` et `README.md`, « Commandes ») dit où vivent les
  verrous du poste.

---

## US-2470 — Les contrôles du dépôt vérifient ce que le guide affirme

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3683

**En tant que** développeur, **je veux** que `make merge-queue-check`, `make sources` et
`make roadmap` vérifient ce que le guide dit qu'ils tiennent, **afin qu'**une file sans contrôle
exigé, un commentaire d'exemption ou une commande inexistante citée au pilote ne passent plus sans
un mot (PLC-01, PLC-05, PLC-14).

**Critères d'acceptation.**

- propre à l'US : `make merge-queue-check EPIC=EP-nn` échoue, en disant « aucun contrôle exigé »,
  quand aucun jeu de règles actif qui vise la branche ne porte `required_status_checks` avec le
  contrôle `gate` ; un test le prouve sur un faux `gh` qui rend un jeu avec file et sans contrôle
  exigé. Il passe sur les branches d'EPIC d'aujourd'hui, dont le jeu « epic protection » exige
  `gate` (PLC-01) ;
- propre à l'US : le modèle `.github/rulesets/merge-queue.json` porte `required_signatures`, que les
  jeux d'EP-10, d'EP-26 et d'EP-27 portent et qu'il n'avait pas, et `merge-queue-check` dit un jeu
  de file dont les types de règles ne sont pas ceux du modèle ;
- propre à l'US : `make sources` refuse, chacune avec son cas de test, `# flake8: noqa`,
  `# ruff: disable[…]`, `# ruff: enable[…]` et `# ruff: ignore`, `# isort: skip` et `# isort: off`,
  `# pragma no cover` sans deux-points, `# pragma: no branch`, et `# hadolint ignore=…` dans un
  `Dockerfile`, qu'il lit désormais (PLC-05) ;
- propre à l'US : `make roadmap` lit `.claude/skills/**/*.md` avec les fichiers des agents : une
  commande `make` que cite le skill `pilote` et que le Makefile n'a pas le fait échouer ; un
  changement d'un skill réveille la famille `roadmap` (PLC-14).

---

## US-2480 — Un changement réveille les contrôles qu'il peut casser

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3684

**En tant que** développeur, **je veux** que la table des familles (`tools/paths.toml`) réveille,
pour chaque fichier, les contrôles qui le lisent, **afin qu'**un changement casse la chaîne de la
pull request qui le porte, et non celle du lot suivant ou de `main` après la fusion (#850, #898,
#958, PLC-06).

**Critères d'acceptation.**

- propre à l'US : `ruff.toml` réveille la famille `back` ; `tools/src/wftools/slots.py` réveille
  `back`, `front` et `service` ; `deploy/compose/garage.toml` et `storage-buckets.sh` réveillent
  `back`, `keycloak` et `service` ; un cas de `tools/tests/test_paths.py` par fichier (PLC-06) ;
- propre à l'US : le garde des familles (`tools/tests/test_families.py`) voit les scripts que le
  Makefile lance par `python3 $(CURDIR)/…` et les fichiers que `compose.service.yaml` monte en
  lecture seule : un script ou un montage qu'aucune famille de ses appelants ne nomme le fait
  échouer (PLC-06) ;
- propre à l'US : `fixtures/api/access_roles.json` réveille la famille `keycloak`, avec son cas dans
  `tools/tests/test_paths.py` (#898, point 2) ;
- propre à l'US : `tools/tests/test_frontimage.py` affirme de nouveau qu'une page
  (`frontend/src/app/(home)/page.tsx`) ne réveille pas `front-image` (#850) ;
- propre à l'US : une migration qui exige le superutilisateur — une extension non sûre, un
  `ALTER ROLE` — fait échouer la chaîne de sa pull request, et non l'essai de production après la
  fusion (#958).

---

## US-2490 — La chaîne : caches, veille, droits, traces et miroir

- **statut** : en cours
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3685

**En tant que** développeur, **je veux** que les workflows écrivent leurs caches quand leur clé
change, que la veille suive tout ce que la chaîne épingle, qu'un travail de pull request n'ait pas
plus de droits qu'il n'en faut, et qu'un parcours en échec laisse sa trace, **afin que** la chaîne
ne retombe pas sur le réseau, ne garde pas une empreinte périmée, et qu'un échec de la file se lise
au lieu de se déduire (#3025, #3028, #3447, PLC-08, PLC-09, PLC-10, et le constat du cadrage
sur la veille des images).

**Critères d'acceptation.**

- propre à l'US : une fusion qui ne change que `backend/uv.lock` ou `tools/uv.lock` écrit le cache
  d'uv (PLC-08) ;
- propre à l'US : `.github/dependabot.yml` suit les actions locales (`.github/actions/*`) et
  `deploy/e2e` ; un test des outils tient une même empreinte par action entre les workflows et les
  actions locales ; la liste « ce que Dependabot ne suit pas » du guide est à jour (PLC-09) ;
- propre à l'US : au palier rapide, `e2e-image` cherche l'image sans droit d'écrire les paquets ; la
  publication se fait dans un travail du seul palier complet. Le travail `mirror` garde
  `packages: write`, qu'il lui faut pour remplir le miroir avant la fusion, et le guide le dit, avec
  ceci : l'immuabilité de l'étiquette de version est tenue par l'outil, non par le registre
  (PLC-10) ;
- propre à l'US : sur l'échec d'un parcours, `service / paths` verse `frontend/test-results/`
  (traces, captures, `error-context.md`) en artefact du job, avec une rétention courte ; les autres
  travaux qui jouent des parcours font de même (#3447) ;
- propre à l'US : Dependabot suit de nouveau les images de Docker Hub : `deploy/images/Dockerfile`
  les porte toutes, sans préfixe, et `.github/dependabot.yml` le suit ; un passage de la veille
  `docker`, que l'auteur déclenche à la main après la fusion, les examine toutes, et son journal le
  montre (#3025) ;
- propre à l'US : un test des outils échoue quand une référence d'image de Docker Hub du dépôt,
  préfixée ou non, n'est pas celle du manifeste, ou quand le manifeste porte une image que rien
  n'emploie ; son message nomme `make mirror-sync` et `make mirror PUSH=yes` ;
- propre à l'US : `make mirror-sync` recopie le manifeste dans les `Dockerfile` et les fichiers
  Compose, sans toucher au préfixe ; relancé, il ne change rien ;
- propre à l'US : le guide (« La chaîne ») et la docstring de `tools/src/wftools/mirror.py` disent
  que Dependabot ne lit pas une référence préfixée, ce qu'est le manifeste et les deux gestes d'une
  montée, à la place de « ne lit peut-être plus » et de « for Dependabot » (#3028, points 3 et 4) ;
- écart : le repli sur Docker Hub quand le miroir ne tient pas toutes les empreintes (#3025,
  option 2) n'est pas réalisé — la pull request d'une montée attend le geste d'une personne, comme
  l'auteur l'a retenu le 2026-11-13 ;
- écart : les mises à jour de sécurité que Dependabot dit impossibles
  (`security_update_not_possible`, #3724) ne sont pas traitées, et l'alerte 68 de `@faker-js/faker`
  reste ouverte : un `override` de pnpm casserait Prism, dont l'auteur attend la montée (décision
  du 2026-11-16, lot US-2490/L4 #3703 fermé sans livraison) ;
- propre à l'US : la regex `BARE` de `tools/tests/test_mirror.py` attrape aussi une ancre YAML de
  tête (`x-postgres-image: &postgres-image postgres:18@sha256:…`), prouvé par ce cas (#3028,
  point 1) ;
- propre à l'US : quand ghcr.io répond `denied`, `mirror.py` nomme les deux causes — la connexion,
  ou un paquet pas encore copié, avec `make mirror PUSH=yes` — et un test vérifie les deux mentions
  (#3028, point 2) ;
- propre à l'US : `fill` réessaie une fois un `denied` reçu à l'écriture avant d'échouer (#3028,
  point 5).

**Hors périmètre.**

L'épinglage de la production par empreinte : EP-13.

---

## US-2500 — Les gardes du Makefile sur `SHARD` et `WATERFALL_PROCESSORS`

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3686

**En tant que** développeur, **je veux** que les refus à la lecture du Makefile soient éprouvés pour
chaque but qu'ils couvrent, et qu'ils jugent une valeur sans l'interpoler dans un shell, **afin
qu'**une valeur fautive soit refusée partout de la même façon (#3104, #3108).

**Critères d'acceptation.**

- propre à l'US : un test paramétré de `tools/tests/test_e2eworkers.py` lance
  `check-service TIER=full` et `check-all TIER=full` avec `WATERFALL_PROCESSORS=abc`, et attend le
  refus sur la sortie d'erreur et une sortie standard vide (#3104) ;
- propre à l'US : `make check-front-e2e SHARD=x`, sans `TESTS`, refuse une valeur de `SHARD` qui
  n'a pas la forme attendue, comme le font `e2e-service` et `check-service` (#3108, point 1) ;
- propre à l'US : la valeur de `SHARD` passe à l'outil par une variable d'environnement, et non
  entre apostrophes dans un `$(shell …)` : une valeur qui contient une apostrophe est refusée sans
  rien exécuter, prouvé par un test (#3108, point 2) ;
- propre à l'US : `tools/tests/test_e2eparts.py` lit l'exclusion des parcours de mesure dans
  `frontend/playwright.config.ts`, ou un test lie les deux : changer `MEASURES` dans la
  configuration sans le test le fait échouer (#3108, point 3).

---

## US-2510 — Les tests du back et leurs supports

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3680

**En tant que** développeur, **je veux** que les tests du back ne dépendent ni de l'instant où ils
passent ni d'un état laissé par une fixture, et qu'ils disent ce qu'ils prouvent, **afin qu'**aucun
n'échoue sans régression ni ne laisse croire à une preuve qu'il ne fait pas (#818, #898, #899, #935,
#946, #3137).

**Critères d'acceptation.**

- propre à l'US : aucun test du back ne compare une année ou un jour qu'il prend lui-même à ceux que
  le service prend à la requête : `backend/tests/test_revisions.py` (deux comparaisons de
  `reference_year`) et `backend/tests/estimate_support.py` (`YEAR`) dérivent leur attendu d'une
  horloge figée, ou figent celle du service ; `backend/tests/remaining_import_support.py`
  (`REVIEW`) est vérifié, et corrigé si le service juge la date de revue contre le jour courant.
  Rejoués l'horloge posée au 31 décembre 23:59:59 UTC puis au 1er janvier, ces tests passent
  (#3137) — à fusionner avant le 31 décembre 2026 ;
- propre à l'US : l'URL injoignable de
  `test_a_schedule_that_cannot_reach_the_database_ends_in_failure_said_in_its_logs`
  (`backend/tests/test_worker_main.py`) ne porte plus de mot de passe (#818) ;
- propre à l'US : `waterfall-migrate` et `migrations/env.py` appliquent les migrations sans
  `WATERFALL_REDIS_URL` : ils ne lisent que les réglages de la plateforme dont ils ont besoin ; un
  test le prouve (#898, point 3) ;
- propre à l'US : dans `test_two_installations_run_at_once_make_one`
  (`backend/tests/test_keycloak_bootstrap.py`), le verrou et les deux processus sont pris sous le
  `try` — un second `Popen` qui lève ne laisse ni processus ni verrou de session —, la connexion a
  un `lock_timeout`, l'échec de l'attente joint la sortie d'erreur des amorçages, et le commentaire
  dit quand le test échoue (#899) ;
- propre à l'US : la fixture `logs` de `backend/tests/conftest.py` ne pose plus de faux secret de la
  plateforme dans l'environnement : `test_keycloak_authentication.py` et `test_keycloak_sign_in.py`
  capturent leurs journaux par `support.captured_logs(secrets)`, et un `served_settings()` appelé
  après la fixture lit les vrais secrets (#935) ;
- propre à l'US : dans `backend/tests/test_api_service.py`, `FAILED_TASK` et `ME` lisent
  `fixtures/api/task_failed.json` et `me_grid_settings.json` ; un test fixe le cas mixte permis de
  `branches` (une branche objet, une branche liste) ; le test du refus d'une composition ambiguë
  dit par son nom et son `match` les deux formes qu'il vérifie ; une sonde parcourt tous les nœuds
  `anyOf` et `oneOf` du contrat et échoue sur une composition ambiguë (#946).

---

## US-2520 — Les exemples du contrat : identifiants de corrélation et taille de `mockdata.py`

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3687

**En tant que** développeur, **je veux** que l'identifiant de corrélation d'un exemple d'erreur
s'attribue par une règle écrite, et que `mockdata.py` ait de la place pour un module d'exemples de
plus, **afin que** deux lots parallèles n'aient plus à renuméroter à la reprise, ni à condenser une
docstring pour passer le plafond (#1007, #2457).

**Critères d'acceptation.**

- propre à l'US : `docs/api/README-fr.md` et `README.md` disent comment un exemple d'erreur reçoit
  son identifiant de corrélation, de sorte que deux lots tirés de la même branche d'EPIC n'en
  prennent pas un même ; un test des outils tient la règle, à côté de
  `test_each_correlation_is_told_by_one_example_alone` (#1007) ;
- propre à l'US : les identifiants déjà attribués ne changent pas ;
- propre à l'US : `tools/src/wftools/mockdata.py` passe sous 900 lignes par l'extraction d'une part
  — la liste de `named()` ou ce que la conception désigne —, sans changer un octet des exemples
  engendrés : `make mock-data` ne modifie aucun fichier de `fixtures/api/` (#2457).

---

## US-2530 — Les gardes de sources et les parcours du front

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3688

**En tant que** développeur, **je veux** que les gardes de sources du front ne se laissent pas
tromper par une chaîne, et que le parcours du thème de connexion mesure tout ce qu'il dit mesurer,
**afin qu'**une garde ou un parcours ne passe pas en ne regardant plus ce qu'il garde (#839, #3149,
#3431, #3472).

**Critères d'acceptation.**

- propre à l'US : une seule fonction `uncommented`, dans `frontend/src/test/`, importée par les
  quatre gardes (`next-config.test.ts`, `use-id-guard.test.ts`, `client-import-guard.test.ts`,
  `thead-guard.test.ts`), saute les chaînes avant de retirer les commentaires ; un test de la
  fonction : `const g = "/*";` suivi d'une action serveur en ligne et d'un `/** doc */` ne passe
  plus la garde des actions serveur (#839) ;
- propre à l'US : dans `frontend/e2e/service/login-theme.spec.ts`, les titres des alertes
  d'information, de succès et d'avertissement sont parmi les textes mesurés ; le sélecteur de langue
  et le bouton secondaire sont dans les listes `expected` de `judge`, de sorte que leur disparition
  fait échouer le parcours (#3431, points 1 et 2) ;
- propre à l'US : la durée de `login-theme.spec.ts` dans `tools/e2e-service-durations.json` vient
  d'un journal complet de `make e2e-service`, par `make e2e-durations` (#3431, point 3) ;
- propre à l'US : les trois commentaires de `frontend/e2e/server-action.ts` tiennent en 100
  caractères (#3472) ;
- écart : aucun contrôle de la longueur des commentaires n'est ajouté à la chaîne (#3472, seconde
  proposition) — plus d'un millier de lignes de commentaire du front dépassent 100 caractères au
  2026-11-16, et les recouper toutes ne vaut pas la règle ;
- écart : `tools/tests/test_e2ebrowser.py` garde ses deux attentes d'une seconde (#3149) — sa
  décision demande de ne pas corriger à l'aveugle et de le reprendre s'il échoue dans la file ;
  aucun des échecs connus de la file (`tools/queue-known.toml`) ne le nomme au 2026-11-16 : le
  constat se ferme avec cette raison.

---

## US-2540 — Le guide, la politique de sécurité et les licences disent le dépôt d'aujourd'hui

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #3689

**En tant que** développeur, **je veux** que les règles de codage, le guide d'installation, la
politique de sécurité et les annotations de licence décrivent le dépôt tel qu'il est, **afin que**
personne ne lise une règle, une origine de paquet, une absence de version ou un titulaire que le
dépôt dément (#851, #3041, #3057, #3161, PLC-12, PLC-15).

**Critères d'acceptation.**

- propre à l'US : dans `docs/dev/typescript.md`, le *Contrôle* de la règle des actions serveur dit
  que `src/next-config.test.ts` lit chaque source TypeScript du build hors des commentaires et
  refuse les dossiers `pages/` et `src/pages/`, et qu'ESLint refuse tout `.js` sous `src/` (#851) ;
- propre à l'US : le défaut n° 22 de `docs/dev/typescript.md` dit que l'exception unique porte sur
  l'état des réponses d'une grille, et que remettre à zéro un état du composant quand une prop
  change, sous une garde qui se referme d'elle-même, reste permis (#3161) ;
- propre à l'US : `INSTALL.md`, `CONTRIBUTING.md`, `docs/dev/README-fr.md` et `README.md`
  distinguent le poste — le client PostgreSQL 18 de l'archive d'Ubuntu 26.04 — du runner — celui du
  dépôt PGDG, que l'image `ubuntu-26.04` porte déjà (#3041, décision de l'auteur du 2026-11-13) ;
- propre à l'US : dans `docs/roadmap/EP-24-consolidation-apres-v0-3-0.md`, section US-1920, le
  paragraphe « Ce qui tient chaque critère » a son retour à la ligne refait (#3057) ;
- propre à l'US : `SECURITY.md` ne dit plus que la réalisation n'a pas commencé ; il dit que la
  dernière version publiée, et elle seule, reçoit les correctifs de sécurité, sans nommer de
  numéro ; il dit quoi signaler dans le code comme dans la spécification ; il garde son accusé de
  réception sans délai chiffré (PLC-12, décisions de l'auteur du 2026-11-16) ;
- propre à l'US : l'annotation de `DejaVuSans.ttf` dans `REUSE.toml` nomme ses deux titulaires —
  Bitstream, Inc. (2003) et Tavmjong Bah (2006), que la police elle-même déclare — et le texte de
  licence versionné sous `LICENSES/` porte la notice d'Arev ; `make reuse` passe (PLC-15) ;
- propre à l'US : `make readmes` et `make roadmap` passent.

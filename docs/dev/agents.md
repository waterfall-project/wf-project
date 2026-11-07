# Règles communes des agents

Ce fichier est lu par chacun des agents de `.claude/agents/` avant tout travail ; aucun ne
le recopie. Il ne dit que ce qui est propre au travail d'un agent : pour le reste, il
renvoie au [guide](README-fr.md), aux règles de codage ([Python](python.md),
[TypeScript](typescript.md), [Java](java.md)) et au [README de la roadmap](../roadmap/README-fr.md), qui font
foi.

## Les agents

| Agent | Rôle |
|---|---|
| `epic-framer` | cadre un EPIC jusqu'à ses issues : US détaillées, conception, plan de lots |
| `epic-deliverer` | livre un lot d'un EPIC `en cours`, à partir de son issue ; une instance par lot, que le pilote lance |
| `python-developer`, `typescript-developer` | réalisent un lot, chacun dans son langage ; l'extension Java de Keycloak revient à `python-developer` |
| `python-developer-opus`, `typescript-developer-opus` | les mêmes, en Opus : `epic-deliverer` les lance d'emblée sur un lot que son issue ou sa conception dit complexe, ou en escalade, une fois par lot ; leur fichier renvoie à celui de l'original, qui seul porte les règles |
| `python-reviewer`, `typescript-reviewer` | relisent la pull request d'un lot, sans rien modifier |

`epic-framer` se lance comme agent principal de la session (`claude --agent epic-framer`) :
il pose ses questions à l'utilisateur, ce qu'un sous-agent ne peut pas faire.
`epic-deliverer` est un sous-agent du pilote (« Le pilote »), en Opus quel que soit le modèle
du pilote, et il confie à son tour le travail aux quatre autres ; ses questions passent par
l'issue de son lot. Les quatre autres
sont des sous-agents, que l'agent de livraison — ou une personne — appelle.

## Le pilote

Une série de lots se livre par une session de pilotage, ouverte dans un terminal, qui ne fait
que lancer les livreurs : elle ne code pas, ne relit pas, ne lit aucun diff et ne fusionne
rien. Elle tourne en Sonnet, et se relance chaque matin :

```
claude --model sonnet
/loop /pilote EP-nn
```

Ses règles sont dans le skill `pilote` (`.claude/skills/pilote/SKILL.md`). En bref :

- **Un livreur par lot.** Le pilote lance une instance neuve d'`epic-deliverer`, en
  arrière-plan, pour chaque lot prêt du tableau de suivi, et une nouvelle pour le suivant
  quand elle a rendu la main. Un livreur qui enchaînait les lots gardait des centaines de
  milliers de tokens de contexte, que chaque attente de plus de cinq minutes faisait réécrire
  en entier : la moitié du forfait de la semaine du 2026-10-19.
- **Jusqu'à N livreurs, N = 1 sur le poste actuel**, chacun dans son worktree, avec son
  créneau (`make slot`, guide, « Commandes ») : le poste s'est effondré trois fois sous les
  tests de plusieurs agents (2026-10-19, 21 et 22), la mémoire de plusieurs exécutions qui
  croyaient chacune avoir le poste entier. N est `WATERFALL_SLOTS`, celui qui borne aussi les
  exécutions lourdes — tests entiers, couverture, construction du front, parcours de bout en
  bout —, que l'admission du Makefile fait attendre N à la fois, chacune sur 1/N des
  processeurs. À N = 1, rien ne change : un livreur, une exécution lourde à la fois. Les
  créneaux sont le verrou commun à tous les pilotes et à tous les dépôts du poste (un pilote par
  EPIC) : le pilote lit `make slots` à chaque réveil, lance autant de livreurs qu'il a de lots
  prêts et de créneaux libres, nomme toujours le lot qu'il confie, et signale plus de N + 1
  worktrees dans son dépôt, dépôt principal compris. Un livreur sans créneau rend la main sans
  rien faire, avec le relevé « aucun créneau libre », que le pilote traite comme une limite
  d'usage.
- **« Pas avec ».** Le pilote ne lance jamais un lot dont un lot « pas avec » est commencé et
  non fusionné (`en cours`, `en revue`, `question`, `bloqué`), même quand leurs dépendances le
  permettent : le cadreur marque ainsi deux lots qu'aucune dépendance ne sépare et qui
  touchent un même fichier, pour que la file de fusion n'ait pas à attraper tard un conflit
  que le plan savait.
- **Les questions.** Un livreur ne parle pas à l'utilisateur : une question bloquante devient
  un commentaire de l'issue du lot, et le lot passe `question` dans le tableau. Le pilote passe
  à un autre lot. Le jour, de 6 h à 20 h, il prévient l'utilisateur par une notification ; la
  nuit, de 20 h à 6 h, il ne le dérange pas. L'utilisateur répond dans l'issue, à ses
  créneaux, de 6 h à 7 h et de 18 h 30 à 20 h.
- **Un réveil périodique**, toutes les trente minutes environ, même sans livreur rendu :
  c'est lui qui reprend après une limite d'usage, un livreur planté ou une réponse donnée,
  sans personne.

## La mise en file

Un livreur met la pull request de son lot en file de fusion par la mutation GraphQL
`enqueuePullRequest` (`.claude/agents/epic-deliverer.md`). Cette commande, `gh api graphql`,
demande une permission que les règles de l'outil `Bash` ne donnent pas d'office ; c'est une
personne qui l'accorde, une fois, avec l'entrée suivante de `permissions.allow`, éprouvée le
2026-11-05 (un livreur a mis #1978 en file avec elle) :

```json
"permissions": { "allow": [ "Bash(gh api graphql -f query='mutation($id:ID!){enqueuePullRequest(input:{pullRequestId:$id}){mergeQueueEntry{state}}}' -f id=*)" ] }
```

- **Où elle se pose.** Dans `~/.claude/settings.json`, pour tous les dépôts du poste ; ou dans
  `.claude/settings.json` du clone, pour ce dépôt seul. L'entrée s'ajoute à la liste
  `permissions.allow` qui existe déjà, elle ne la remplace pas.
- **Ce qu'elle autorise.** Cette mutation exacte, pour n'importe quel identifiant de pull request :
  l'identifiant est le `*` final, et tout le texte de la requête doit être celui-là.
- **Ce qu'elle n'autorise pas.** Aucune autre requête GraphQL, et ni `gh pr merge` ni une fusion
  hors de la file : la fusion reste celle de la file, après la chaîne.

[`CONTRIBUTING.md`](../../CONTRIBUTING.md) y renvoie.

## Ce qui fait foi

- **Le fichier de l'EPIC** (`docs/roadmap/EP-nn-….md`) fait foi pour l'intention : périmètre,
  critères d'acceptation, conception. **L'issue** porte l'état. Un agent ne recopie pas les
  critères dans une issue, et ne les modifie pas en réalisant un lot.
- **Les critères d'acceptation reprennent le Vérif mot pour mot**, en critère ou en écart ;
  `make roadmap` le vérifie.
- **Le contrat d'abord** : une opération qui manque est une modification du contrat, faite
  avant le code qui la consomme, et seulement si la conception de l'EPIC la prévoit.
- **Aucun mock, aucun client écrit à la main** : les réponses du faux back sont les exemples
  du contrat, le client du front est engendré (`make generate-client`).

## Comment le travail se fait

- **Un lot, une issue, une branche `lot/<identifiant>`, une pull request** vers la branche
  de son EPIC, `epic/EP-nn` — jamais vers `main`.
- **Chaque test cite l'exigence qu'il couvre** (WF-QUA-0010) : la forme est dans le guide,
  « Un test qui cite son exigence ».
- **Les modules du noyau ne se lisent que par leur interface**, et le code suit les règles de
  son langage, défauts déjà rencontrés compris.
- **Le code est en anglais, la documentation en français**, comme les messages de commit :
  une ligne qui dit ce qui change, puis un corps qui dit pourquoi.
- **Un `README-fr.md` de `docs/` ne change pas seul** : sa modification se porte, traduite,
  dans le `README.md` voisin, dans la même pull request ; `make readmes` le vérifie.
- **Aucune règle ne se contourne dans le code** : pas de commentaire d'exemption, jamais.
- **Taille** : un lot vise la taille de la section « Lots » du README de la roadmap ; sa
  pull request met sa taille réelle, `make lot-size BASE=origin/epic/EP-nn`, à côté de
  l'estimation de son issue. Un dépassement se signale, il ne s'arrête pas.
- **Les statuts des US vivent dans le fichier de l'EPIC** : le premier lot d'une US la passe
  `en cours`, et celui qui la termine la passe `fini` — dans le fichier, par ce même lot,
  quand ses critères sont tenus et que ses tests citent leurs exigences.
- **Un constat hors du périmètre du lot ne se corrige pas dans le lot** : il devient une
  issue `[EP-nn] <nature> : …`, sous-issue du lot qui le relève, avec sa décision — corrigé
  par un lot, bloque un lot, reporté vers un EPIC, ou à trancher —, comme le dit le README de
  la roadmap, « Suivi sur GitHub ».
- **Le tableau de suivi de l'issue de l'EPIC** est tenu à jour par l'agent qui change un état
  — `epic-framer` le crée, `epic-deliverer` le tient — dans le corps de l'issue, jamais en
  commentaire. Un agent ne réécrit pas ce corps lui-même : plusieurs livreurs s'y réécriraient
  l'un l'autre. Il passe par `make tracking ISSUE=<n> LOT=<identifiant> [STATE=…] [PR=…]
  [MODEL=…]`, `US=<identifiant> STATUS=…` ou `FINDING=<n> ATTACHED=… DECISION=…`, qui relit le
  corps sous un verrou du poste juste avant de l'écrire et ne change que la ligne demandée
  (guide, « Commandes »). Le cadreur, qui écrit le tableau pour la première fois, l'écrit
  lui-même ; ensuite, `make tracking`.
- **Un lot ne laisse rien derrière lui** (#1444). Après la fusion de sa pull request, l'agent
  de livraison supprime la branche locale du lot et toute branche de travail qu'il a tirée
  (`git branch -d`, qui refuse une branche non fusionnée), retire les worktrees du lot — le
  sien et ceux de ses développeurs — (`git worktree remove`, puis `git worktree prune`), et
  vérifie qu'aucun processus lancé pour le lot ne tourne encore : serveur de Next, Prism,
  Chromium. Un agent de développement fait de même, avant de rendre la main, pour les branches
  de travail qu'il a tirées à côté de celle du lot et les commandes qu'il a lancées en
  arrière-plan. Une centaine de branches fusionnées et quinze worktrees de lots fusionnés
  brouillaient `git branch` et `git worktree list`. Le nettoyage d'un dépôt déjà encombré se
  fait à la main, une fois.
- **Un agent n'arrête que ce qu'il a lancé** (US-1080), par son PID ou par un nom propre à
  son lot ; jamais par motif. Ni `pkill`, ni `killall`, ni un `kill` dont une cible n'est pas
  un PID écrit en chiffres — `kill $(pgrep make)`, `kill $pid`, un nom —, lancé par `xargs`,
  ou qui vise `-1` ou `0` ; ni `docker rm`, `docker stop`, `docker kill`, `docker rmi` ou
  `docker volume rm` d'une cible calculée — substitution, variable, joker —, d'un tube ou d'un
  filtre, quand une cible littérale passe (US-1310) ; ni `docker … prune` ; ni
  `docker compose … down` hors du Makefile. `pkill -f "^make check"` a pu interrompre ainsi, le 2026-11-03, le
  `make check` d'un livreur d'un autre EPIC. Ce que le Makefile a démarré, sa cible l'arrête :
  `make service-down` pour la plateforme de service. Un verrou de git (`.git/…/*.lock`) ne
  se supprime ni ne se déplace — ni `rm`, ni `find … -delete` ou `-exec rm`, ni `mv` ou
  `rename` — : une commande `git` le tient, peut-être dans un autre worktree, et la
  commande se relance. Le hook `PreToolUse` de `.claude/settings.json` tient la règle : avant
  chaque commande de l'outil `Bash`, `tools/src/wftools/guard.py` refuse ces formes où
  qu'elles se trouvent dans la ligne — derrière `sudo`, `env`, `su -c`, `flock`, `watch` ou
  `busybox`, après un `cd` dans `.git`, ou un `cd` vers un chemin calculé, qu'il tient pour
  `.git` —, et dit quoi faire à la place ; une commande `make` passe toujours.
- **Avant de rendre la main**, un agent qui a modifié le dépôt lance
  `make check BASE=origin/epic/EP-nn`, qui éprouve ce que la modification touche, fichiers
  non commités compris. Il peut demander un créneau : depuis US-1100, dans un worktree lié qui
  n'en tient pas, les cibles qui en ont besoin (`build-keycloak`, `check-front-image`, `e2e`,
  `e2e-measure`…) échouent en disant `make slot`. Le livreur prend son créneau avant tout
  travail, et ses développeurs travaillent dans son worktree, celui qui le détient ; un
  développeur qui voit ce refus ne prend pas de créneau, il le rapporte au livreur.
  Un agent de revue, lui, ne lance que des commandes qui n'écrivent
  rien de versionné.

## Où un agent s'arrête

Un agent rend la main plutôt que de trancher à la place d'une personne :

- une exigence ambiguë, contradictoire ou incomplète devient une issue « Specification
  finding », avec l'emplacement, la citation exacte et une proposition de texte ;
- un écart entre le contrat et ce qu'il faut réaliser devient une issue « Interface contract
  issue », avec une proposition ;
- une décision qui n'est ni dans la spécification, ni dans le contrat, ni dans la conception
  de l'EPIC se demande.

Et quelles que soient les circonstances :

- **aucun agent ne fusionne dans `main`**, ni ne pousse sur `main` ou sur une branche
  `epic/*` — sauf `epic-deliverer`, pour créer la branche de son EPIC au premier lot ; la
  fusion d'une branche d'EPIC dans `main` est faite par une personne ;
- **seul `epic-deliverer` fusionne**, dans la branche d'un EPIC, la pull request d'un lot dont
  la revue locale et la chaîne sont au vert ;
- aucun agent ne modifie la spécification (`docs/spec`), ni les jeux de règles des outils
  pour faire passer son code ;
- une commande qu'un agent exécute existe dans le Makefile — ou c'est `git` ou `gh` ;
  `make roadmap` échoue sur une commande `make` que cite un agent et que le Makefile n'a
  pas.

## Rendre compte

Tout agent qui termine un travail rend compte ainsi :

- **Fait** — ce qui a été réalisé, en clair ;
- **Décisions** — ce qui a été choisi, et ce que cela touche ailleurs ;
- **Vérifications** — les commandes exécutées et leur résultat réel, jamais une vérification
  non faite présentée comme faite ;
- **Reste** — ce qui n'est pas couvert, supposé ou reporté, et les issues ouvertes.

Le compte rendu tient en une quarantaine de lignes : des chemins, des chiffres, des numéros
d'issues, jamais un diff ni un journal collé. Il revient dans le contexte de l'agent de
livraison, qui le relit à chaque attente.

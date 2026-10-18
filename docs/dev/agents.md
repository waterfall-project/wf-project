# Règles communes des agents

Ce fichier est lu par chacun des agents de `.claude/agents/` avant tout travail ; aucun ne
le recopie. Il ne dit que ce qui est propre au travail d'un agent : pour le reste, il
renvoie au [guide](README.md), aux règles de codage ([Python](python.md),
[TypeScript](typescript.md), [Java](java.md)) et au [README de la roadmap](../roadmap/README.md), qui font
foi.

## Les agents

| Agent | Rôle |
|---|---|
| `epic-framer` | cadre un EPIC jusqu'à ses issues : US détaillées, conception, plan de lots |
| `epic-deliverer` | livre les lots d'un EPIC `en cours`, à partir de leurs issues |
| `python-developer`, `typescript-developer` | réalisent un lot, chacun dans son langage ; l'extension Java de Keycloak revient à `python-developer` |
| `python-reviewer`, `typescript-reviewer` | relisent la pull request d'un lot, sans rien modifier |

`epic-framer` et `epic-deliverer` se lancent comme agent principal de la session
(`claude --agent epic-deliverer`) : l'un pose ses questions à l'utilisateur, l'autre confie
le travail aux quatre autres, et un sous-agent ne peut faire ni l'un ni l'autre. Les quatre
autres sont des sous-agents, que l'agent de livraison — ou une personne — appelle.

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
  commentaire.
- **Avant de rendre la main**, un agent qui a modifié le dépôt lance
  `make check BASE=origin/epic/EP-nn`, qui éprouve ce que la modification touche, fichiers
  non commités compris. Un agent de revue, lui, ne lance que des commandes qui n'écrivent
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

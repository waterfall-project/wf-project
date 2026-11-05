---
id: EP-22
titre: Le Kanban signale la récapitulative qui n'attend plus que ses lignes propres — le contrat, le faux back et la carte
statut: en cours
depend_de: EP-17
famille: front, plateforme
issue: 1966
---

# EP-22 — Le Kanban signale la récapitulative qui n'attend plus que ses lignes propres

## Objet

La revue locale d'US-0730b (EP-17) a relevé que le contrat se contredit : `listStartableTasks` ne rend
« jamais une récapitulative », alors que `KanbanTask` dit que la carte signale celle qui n'attend plus
que ses lignes propres (`TaskFacet.awaiting_own_lines`, WF-PLA-0040), et que la spécification veut ce
signal « dans la grille de reste à engager et dans le Kanban ». La marque de la carte ne paraîtrait
donc jamais face au vrai service (#1851). L'auteur a tranché le 2026-11-04 : le Kanban liste ces
récapitulatives. EP-22 en écrit le contrat, le faux back et son exemple, et fait lire la carte
d'US-0730b sur cet exemple.

Il n'est pas dans EP-17 parce que celui-ci ferme `docs/api` à sa branche, pour avancer en parallèle
des EPIC de domaine ; et il dépend d'EP-17, dont la carte d'US-0730b n'existe que sur `epic/EP-17`. Il
n'empêche pas EP-05 : il touche au contrat figé par une entrée de `docs/api/DECISIONS.md`, comme le
veut « La règle d'après le gel ».

Par décision de l'auteur du 2026-11-05, il reçoit aussi la revue des règles ruff et des annotations
sous Python 3.14 (#1987, relevée par EP-20) : une US d'outil du dépôt, sans lien avec le Kanban, d'où
la famille `plateforme` en plus de `front`.

## Ce qui en fait partie

- le contrat de `listStartableTasks` : sa description, un exemple `startable_tasks_awaiting_own_lines`,
  une ligne de provision sous la récapitulative de `nodes_awaiting_own_lines` — US-1240 ;
- le faux back et le témoin qui servent ces exemples (`mockcore.startable`, `mockkanban`,
  `mockreview`, `mockdata`) et leurs tests — US-1240 ;
- la carte d'US-0730b lue sur ce nouvel exemple, et l'aide FBS-4.5.3 — US-1240.
- la revue des règles ruff et des annotations sous Python 3.14 du back et des outils — US-1280.

## Ce qui n'en fait pas partie

- le service réel de `listStartableTasks` : EP-09, qui clôt WF-RAE-0030, le sert tel que le contrat le
  dit ; EP-06 clôt WF-PLA-0040 ;
- tout autre changement de contrat, et toute réécriture du code du back que la revue de #1987 ne
  décide pas ;
- la version du contrat : `info.version` reste 1.0.0 (décision de l'auteur du 2026-11-04).

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-PLA-0040-A` | Hiérarchie des tâches | début — close en EP-06 | US-1240 |

## Opérations du contrat

`listStartableTasks` : sa description et un exemple, sans changer sa forme. Aucune autre opération,
aucun schéma modifié ; `KanbanTask` et `TaskFacet.awaiting_own_lines` le disent déjà.

## Préalables

EP-17 livré (la carte d'US-0730b et son aide sont sur sa branche). Décisions de l'auteur du 2026-11-04.

## Définition de fini

- `make check` passe sur la branche de l'EPIC, la file de fusion est verte ;
- `listStartableTasks` liste, sur l'exemple `startable_tasks_awaiting_own_lines`, la récapitulative
  démarrée qui n'attend plus que ses lignes propres, et la carte la signale ;
- `make build-openapi`, `make inventory`, `make mock-data-up-to-date`, `make client-up-to-date` et
  `make server-models-up-to-date` passent ; `docs/api/DECISIONS.md` a son entrée ;
- la revue de #1987 est rendue (US-1280) : ses décisions sont appliquées ou écrites, et le constat fermé ;
- `make roadmap` passe.

## Constats reçus

- #1851 — contrat : le Kanban ne liste jamais une récapitulative, que `KanbanTask` dit signaler
  (`awaiting_own_lines`) ; reporté d'EP-17 (décision de l'auteur du 2026-11-04), à rattacher à l'issue
  de l'EPIC à son ouverture ; titre et label passent à `EP-22`.
- #1987 — outil : revue des règles ruff et des annotations sous Python 3.14 ; reportée d'EP-20
  (décision de l'auteur du 2026-11-05) à US-1280 ; titre et label passent à `EP-22`.

## Conception

EP-22 ne crée **aucune table ni migration** et ne touche aucun module du noyau : le service réel n'existe
pas encore (EP-06 et EP-09). Il modifie le contrat figé, par l'issue « contrat » #1851 que l'auteur a
tranchée, et s'inscrit dans `docs/api/DECISIONS.md` (« La règle d'après le gel »).

### Le contrat

- **`listStartableTasks`** (`docs/api/paths/analysis.yaml`) : la description cesse de dire « jamais une
  récapitulative ». Elle dit que la colonne `started` rend aussi la récapitulative démarrée dont toutes
  les subordonnées sont terminées et dont une ligne propre hors provision garde un reste à engager
  (`TaskFacet.awaiting_own_lines`), avec ses gestes ; toute autre récapitulative reste exclue, son état
  dérivant de ses subordonnées. Ni le schéma de la réponse, ni `KanbanTask`, ni `TaskFacet` ne changent ;
  la phrase de `KanbanTask` devient vraie.
- **Les gestes de sa carte**, par le catalogue existant, sans condition nouvelle : `enter_remaining`
  disponible ; `complete` indisponible, `missing_conditions: [task_without_lines]` (elle porte des lignes
  hors provision) ; ni `start`, ni `reopen`. Le front ne déduit rien (WF-IHM-0090).
- **Les exemples** : `startable_tasks_awaiting_own_lines`, nouvel exemple de `listStartableTasks`, lit la
  variante de `nodes_awaiting_own_lines` (les études qui portent une ligne propre de 500, `mockreview`) ;
  et une **ligne de provision de 40** sous la récapitulative signalée de `nodes_awaiting_own_lines`, que
  l'état de cette variante tient (la phrase 6 de WF-PLA-0040-A). Les fixtures de `fixtures/api/` sont
  engendrées (`make mock-data`), jamais écrites à la main.
- **`docs/api/DECISIONS.md`** : une entrée dans « Le contrat figé » ou à la suite, qui cite #1851, la
  décision du 2026-11-04, les gestes, et les deux exemples. `info.version` reste 1.0.0 : aucune forme
  ne change. `INVENTORY.md`, `waterfall.bundle.*`, `waterfall.mock.json`, le client et les modèles du
  service suivent leurs cibles (`make inventory`, `make build-openapi`, `make mock-spec`,
  `make generate-client`, `make generate-server-models`).

### Le faux back et le front

- **Faux back.** `mockcore.startable` laisse entrer dans `started` la récapitulative dont la facette dit
  `awaiting_own_lines`, par la fonction qui la calcule déjà (`mockdating.awaiting_own_lines`) ; il n'en
  réemploie pas une autre. `mockkanban.commands` rend à sa carte ses gestes (`bears_lines` vrai, état
  `started`, donc `complete` manquant `task_without_lines` et `enter_remaining`). Le témoin lui-même, où
  nulle récapitulative n'attend, ne change pas : `startable_tasks` et `startable_tasks_milestone` restent
  tels quels. Les tests de `tools/tests` (`test_mockkanban.py`, `test_mockreview.py`) tiennent l'exemple.
- **Front.** `kanban-card.tsx` sert telle quelle ; `kanban-own-lines.dom.test.tsx` lit l'exemple
  `startable_tasks_awaiting_own_lines` au lieu de bâtir ses cartes depuis `nodes_awaiting_own_lines`, et
  le test de la phrase 6 lit la ligne de provision de l'exemple au lieu de la retoucher. Le glisser-déposer
  d'une carte de récapitulative est éprouvé : il passe par `available_commands` (`complete` indisponible),
  non par la nature de la tâche. L'aide FBS-4.5.3 (français et anglais) décrit la carte de la récapitulative.
- **EP-09** reçoit une ligne dans ses « Constats reçus » : son service sert `listStartableTasks` tel que
  ce contrat le dit.

### La revue de ruff sous Python 3.14 (US-1280)

Aucune table, aucun contrat. Python 3.14 (PEP 649 et 749) n'évalue plus les annotations à la
définition. Ruff, en `py314`, range sous `TYPE_CHECKING` les imports qu'une annotation seule emploie
(TC001 à TC003), alors que FastAPI, pydantic et SQLAlchemy les lisent à l'exécution : US-1160/L1 d'EP-20
a déclaré `runtime-evaluated-base-classes` et une exception TC001–TC003 sur `backend/src/waterfall/api/**`.
La revue répond, par une décision écrite dans la pull request et reportée au guide de Python : les
`from __future__ import annotations` (43 fichiers au 2026-11-05) sont-ils à retirer ; que changent `UP` et
`FA` sous `py314` ; une écriture des routes permet-elle de se passer de l'exception sur `api/**` ; quelles
nouveautés de 3.14 (PEP 758, chaînes de gabarit) valent d'être employées, sans réécriture gratuite. Aucune
règle n'est relâchée pour y parvenir (`docs/dev/agents.md`).

### L'ordre de construction

1. Le contrat, le faux back, les exemples et l'entrée de DECISIONS.md, avec leurs cibles engendrées.
2. Puis le front : le test de la carte, le glisser-déposer, l'aide.
3. US-1280, indépendante : elle ne touche que le back, les outils et le guide de Python.

### Décisions

- **Le Kanban liste les récapitulatives qui n'attendent plus que leurs lignes propres** (option 1 de
  #1851, décision de l'auteur du 2026-11-04). Écartée : l'option 2 — ne lister aucune récapitulative,
  retirer la phrase de `KanbanTask` et la marque de la carte, contre la spécification (WF-PLA-0040 :
  « dans la grille de reste à engager et dans le Kanban »). Écartée aussi : lister toute récapitulative
  démarrée, dont l'état dérive de ses subordonnées et qui n'offrirait aucun geste.
- **Les gestes par le catalogue existant**, sans condition nouvelle. Écartée : une condition
  `task_is_summary`, qui dirait ce que `task_without_lines` dit déjà et ajouterait une valeur à l'énumération
  figée.
- **`info.version` reste 1.0.0**. Écarté : 1.0.1, pour un contenu rendu qui ne change aucune forme.
- **#1987 est une US d'EP-22, famille élargie à `plateforme`** (auteur, 2026-11-05). Écartés : un lot
  d'EP-20, livré ; un simple « Constat reçu » : sans US ni lot, personne ne l'aurait travaillé.
- **Un EPIC à part, après EP-17.** Écartés : EP-17, dont la définition de fini ferme `docs/api` ; le
  contrat seul sur `main`, qui sert pourtant le Kanban d'EP-17.

---

## US-1240 — Le Kanban liste la récapitulative qui n'attend plus que ses lignes propres

- **statut** : fini
- **exigences** : `WF-PLA-0040-A`
- **opérations** : `listStartableTasks`
- **issue** : #1967

**En tant que** chef de projet, **je veux** retrouver au Kanban la récapitulative dont toutes les
subordonnées sont terminées et qui n'attend plus que ses lignes propres, **afin de** clore ma phase là
où je démarre mes tâches (#1851).

**Critères d'acceptation.**

- écart : `WF-PLA-0040-A` — « Après déplacement d’une récapitulative portant deux niveaux de
  subordonnées, les tâches et les lignes déplacées sont inchangées, et le devis totalise le même
  montant. » : du service ; EP-06 clôt.
- écart : `WF-PLA-0040-A` — « Les dates et l’état d’une récapitulative ne sont pas saisissables. » :
  le refus est du service, et la grille de planning ne change pas ici ; EP-06 clôt.
- écart : `WF-PLA-0040-A` — « Une récapitulative dont une subordonnée est démarrée est démarrée ;
  elle n’est terminée qu’après la dernière. » : l'état est calculé par le service ; EP-06 clôt.
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont une
  ligne propre porte un reste à engager de 500 est démarrée et signalée ; la saisie d’un reste nul
  sur cette ligne la termine. » : `listStartableTasks` liste cette récapitulative
  dans la colonne « démarrée » avec sa facette (`awaiting_own_lines` vrai), et le Kanban la signale
  par la marque « lignes propres ouvertes » d'US-0730b, sur l'exemple
  `startable_tasks_awaiting_own_lines` et non plus sur un exemple de `listNodes` ; sa carte offre
  `enter_remaining`, disponible, et `complete`, indisponible faute de `task_without_lines` ; elle
  n'offre ni `start` ni `reopen` ; le front ne déduit rien des subordonnées (WF-ARC-0020) ; la
  terminaison par la saisie d'un reste nul est du service, EP-06 clôt (#1851) ;
- écart : `WF-PLA-0040-A` — « La suppression de la seule subordonnée d’une récapitulative de dix
  jours laisse une tâche feuille de dix jours, à laquelle une sous-tâche peut de nouveau être
  ajoutée. » : du service ; EP-06 clôt.
- `WF-PLA-0040-A` — « Une récapitulative dont toutes les subordonnées sont terminées et dont la
  seule ligne propre est une provision de 40 est terminée et n’est pas signalée. » : l'exemple `nodes_awaiting_own_lines` porte une ligne de provision
  sous la récapitulative signalée, que le test de la marque lit sans la retoucher et que ni la
  grille de reste à engager ni le Kanban ne marquent ; l'état est du service, EP-06 clôt (#1851) ;
- écart : `WF-PLA-0040-A` — « Une récapitulative dont la seule subordonnée est un jalon terminé et
  dont une ligne propre garde un reste à engager, privée de ce jalon, est une feuille démarrée d’un
  jour, non un jalon. » : du service ; EP-06 clôt.
- écart : `WF-PLA-0040-A` — « Une récapitulative terminée dont la seule subordonnée, un jalon, est
  déplacée devient un jalon terminé. » : du service ; EP-06 clôt.
- propre à l'US : `docs/api/DECISIONS.md` a son entrée, `info.version` reste 1.0.0, et la description de
  `listStartableTasks` dit que la colonne démarrée rend cette récapitulative ;
- propre à l'US : l'aide FBS-4.5.3, en français et en anglais, décrit la carte de la récapitulative et ne
  promet que ce que le service rend ; `make build-openapi`, `make inventory`, `make mock-data-up-to-date`,
  `make client-up-to-date` et `make server-models-up-to-date` passent.

**Notes de réalisation.** La carte et sa marque sont d'US-0730b (EP-17) ; le contrat est figé en 1.0.0
(EP-16), et cette modification est la décision de l'auteur du 2026-11-04 sur #1851 (« La règle d'après le
gel »).

**À confirmer par le lot.** Que le glisser-déposer d'une carte de récapitulative passe par
`available_commands` (`complete` indisponible) et non par la nature de la tâche : ce n'est pas vérifié
dans le code au cadrage. S'il en va autrement, le lot le dit dans sa pull request et l'auteur tranche ;
il ne le corrige pas en silence.

**Hors périmètre.** Le service réel de `listStartableTasks` (EP-09) et l'état des récapitulatives
(EP-06).

---

## US-1280 — La revue des règles ruff et des annotations sous Python 3.14

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2023

**En tant que** développeur, **je veux** que les règles de ruff et l'écriture des annotations soient
revues pour Python 3.14, **afin que** le code n'emporte ni exception inutile ni import évalué à tort
(#1987).

**Critères d'acceptation.**

- propre à l'US : la pull request tranche, pour chacun des quatre points de #1987 (`from __future__ import
  annotations`, jeux `UP` et `FA`, exception TC001–TC003 sur `api/**`, nouveautés de 3.14), ce qui est
  retiré, gardé ou employé, avec sa raison ;
- propre à l'US : ce qui est décidé est appliqué, `make check` passe, et aucune règle n'est relâchée ni
  contournée par un commentaire d'exemption ;
- propre à l'US : le guide de Python (`docs/dev/python.md`) dit la règle d'écriture des annotations
  sous 3.14.

**Hors périmètre.** Toute réécriture que la revue ne décide pas.

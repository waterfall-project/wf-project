# Guide de développement

Ce guide fixe ce qui doit se ressembler d'un lot à l'autre, qu'une personne ou un agent
l'ait écrit : où chaque chose vit, comment elle se nomme, et la forme des pièces qui se
répètent. Il ne recopie ni la spécification (`docs/spec`), ni le contrat (`docs/api`), ni
[CONTRIBUTING](../../CONTRIBUTING.md), ni la [roadmap](../roadmap/README.md) : il y renvoie.

Chaque règle qu'un outil peut contrôler l'est, et la règle nomme son contrôle ; une règle
que rien ne contrôle le dit. Le guide s'écrit en même temps que le socle (EP-01) : chaque US
y ajoute la section qu'elle établit, et une section encore vide nomme celle qui l'écrira.

## Arborescence

| Chemin | Contenu | PBS |
|---|---|---|
| `backend/` | un seul projet Python, un seul paquet `waterfall` : le noyau (`core/`, un sous-paquet par module, calqué sur un bloc FBS), le service d'API (`api/`), le worker (`worker/`) ; les tests dans `backend/tests/` | PBS-2 |
| `frontend/` | l'application Next.js ; le client engendré dans `frontend/src/api/` ; les parcours de bout en bout dans `frontend/e2e/` | PBS-1 |
| `fixtures/` | le relevé engendré des exemples chiffrés des Vérif, et les fixtures qui s'y rattachent | — |
| `tools/` | les outils du dépôt, un seul paquet Python, `wftools`, et leurs tests | PBS-5.2 |
| `deploy/compose/`, `deploy/helm/` | l'empaquetage : Compose, puis le chart Helm en EP-13 | PBS-5.1 |
| `.github/workflows/` | la chaîne | PBS-5.2 |
| `docs/spec/`, `docs/api/`, `docs/roadmap/` | la spécification, le contrat, la roadmap | — |
| `docs/dev/` | ce guide, et les règles de codage par langage | — |
| `LICENSES/`, `REUSE.toml` | les textes des licences, et la licence des fichiers qui ne portent pas d'en-tête | — |

Un répertoire naît avec le lot qui y met le premier fichier : `backend/`, `frontend/`,
`fixtures/` et `deploy/` n'existent pas encore tous. La conception d'EP-01 dit pourquoi
chaque chose est là (`docs/roadmap/EP-01-socle-de-developpement.md`, « Conception »).

## Le back et les frontières du noyau

Le back est un seul paquet, `waterfall`, et deux processus : `waterfall-api` et
`waterfall-worker`, deux points d'entrée d'une même distribution. Ils portent donc la même
version par construction, celle de `backend/pyproject.toml` (WF-ARC-0010).

Le noyau, `waterfall.core`, a un sous-paquet par module, nommé d'après son bloc FBS de
second niveau, en anglais. Un module expose ce que les autres peuvent utiliser dans son
module `interface`, et rien d'autre : ses tables et son accès aux données lui sont privés.
Un module en importe un autre par `waterfall.core.<module>.interface`, jamais par ses
tables. Le noyau n'importe ni l'API ni le worker, qui ne s'importent pas l'un l'autre.

*Contrôle* : `make imports-back` (import-linter, contrats dans `backend/pyproject.toml`) ;
un test les éprouve sur un paquet d'essai (`backend/tests/test_boundaries.py`). Une requête
SQL écrite en texte, qui nommerait la table d'un autre module, échappe à l'analyse des
imports : elle relève des règles SQL d'EP-03 et de la revue.

## Le front

Le front est une application Next.js en TypeScript strict (`frontend/tsconfig.json`, avec
`noUncheckedIndexedAccess` et `exactOptionalPropertyTypes`). pnpm en gère les dépendances,
à la version que nomme `packageManager` dans `package.json`, lancée par corepack
(`corepack enable pnpm`) ; le verrou, `pnpm-lock.yaml`, fait foi et la chaîne installe
avec `--frozen-lockfile`. Les tests unitaires sont des fichiers `*.test.ts` ou `*.test.tsx`
à côté du code qu'ils éprouvent, lancés par Vitest en deux projets (`vitest.config.ts`),
que le nom du fichier départage : `node` pour les `*.test.ts` et `*.test.tsx` — la logique,
et les composants serveur de `src/app/`, qui se rendent sans document comme en production —,
`dom` pour les `*.dom.test.ts` et `*.dom.test.tsx` — les composants client, que Testing
Library rend dans le document de happy-dom. Un test du projet `dom` qui écrit sur la sortie
d'erreur — `console.error`, `console.warn`, `console.trace` — échoue une fois son document
nettoyé (`frontend/src/test/stderr.ts`, appelé par `setup-dom.ts`) : un avertissement de React
ou d'ECharts, une réponse que le faux back n'a pas, sont des défauts du test ou du code, pas un
bruit à lire en passant. Un test qui prouve qu'une erreur se dit sur la console la fait taire
lui-même par un espion (`vi.spyOn(console, "error")`), et vérifie ce qui fut dit. happy-dom ne
mesure rien : un test qui monte une courbe donne à son dessin la place qu'une page lui donne
(`roomForCharts`, `frontend/src/test/chart-room.ts`), faute de quoi ECharts avertit qu'il n'a
ni largeur ni hauteur (EP-02/L37).

La coquille (`frontend/src/components/shell/`) tire sa navigation de
`frontend/src/navigation/functions.json` : pour chaque fonction de second niveau de la FBS,
son code, la clé de son libellé, sa route, sa portée et la permission qui la laisse
consulter ; une fonction dont la session n'a pas la permission `<fonction>.read` n'y figure
pas. La table porte aussi les feuilles de la FBS, chacune adressée de l'une de deux façons. Une
feuille qui a son propre écran est une feuille (`leaves`) de sa fonction, de même portée et de même
permission : les chronologies, FBS-4.3.1, les imports et exports, FBS-4.3.4, et l'arborescence de
tâches, FBS-4.3.5, sous le planning (`/projects/[projectId]/revisions/[revisionId]/timelines`,
`…/exchanges`, `…/task-tree`), le plan de charge du projet,
FBS-4.4.4, sous le devis (`…/workload`), et le Kanban, FBS-4.5.3, sous le reste à engager
(`…/kanban`). La navigation ne l'offre pas —
l'écran de sa fonction y mène, dans le même contexte, et son entrée est marquée courante —,
mais `readContext` la lit comme sa fonction, et le fil d'Ariane la place après elle. Une feuille
que l'écran de sa fonction montre lui-même, là où l'ergonomie l'a rangée, est une section
(`sections`) de sa fonction, adressée par la route de celle-ci : son `code`, le rôle de ce qui la
montre (`role` : `region`, `grid`, `treegrid`, `columnheader` ou `heading`) et la clé de son nom
(`name`) — le lotissement, FBS-4.2.1, est la région « Lotissement » des paramètres du projet ; le
Gantt, FBS-4.3.3, la colonne « Gantt » de la grille de planning ; l'avancement financier,
FBS-4.8.1, le titre de sa carte. Seul un fait d'une liste nommée se passe de rôle — un terme ne
prend pas son nom de ce qu'il dit — : il se trouve par son texte dans la liste que nomme la clé
`within`, comme le taux d'inflation, FBS-4.2.2, dans les « Paramètres du projet » ;
`functions.test.ts` refuse toute autre section sans rôle.

*Contrôle* : `make screens` (`wftools.screens`, famille `repo`, qui s'exécute sur toute
modification, puisqu'il lit la projection comme le front) confronte la table aux fonctions de
la FBS de la projection — les boîtes des figures de l'arborescence et de chaque bloc, qui les
nomment toutes, et les titres de leurs paragraphes, lus en protection ; une flèche dont l'enfant ne
prolonge pas le code de son parent fait échouer la lecture — et aux pages de `frontend/src/app` ; il
échoue, en nommant la feuille ou la route, sur une feuille sans route dans la table, sur un code
de la table qui n'est pas une fonction de la FBS ou une feuille rangée sous une autre fonction que
la sienne, sur une route à laquelle aucune page ne répond — la page de `[...path]`, qui dit
« introuvable », ne répond à aucune —, et sur une feuille à écran propre que la page de sa
fonction ne nomme pas par `leafOf("FBS-…")`, et ne peut donc pas mener. Une feuille qui n'a pas
encore d'écran se déclarerait, avec sa raison et l'issue qui la suit, dans `WITHOUT_SCREEN` de
`tools/src/wftools/screens.py`, vide aujourd'hui ; la déclaration échoue dès que la table adresse
la feuille. Le parcours `frontend/e2e/screens.spec.ts` (`make e2e`, palier complet) prouve les liens
dans un navigateur, un parcours par route, tiré de la table : une fonction s'atteint par un clic sur
un lien de la navigation — depuis l'écran d'une autre fonction de son bloc, ou d'une révision pour
une fonction d'un projet —, une feuille à écran propre par un clic sur un lien de l'écran de sa
fonction ; le lien doit être visible, la route est compilée d'avance (`compile`), et un écran de
projet de départ s'ouvre hydraté (`openHydrated`). Chaque écran atteint nomme sa fonction et montre
ses sections. Une route ajoutée à la table a donc son parcours.
Trois portées : hors projet ; `project`, les fonctions du projet lui-même — révisions,
paramètres, cycle de vie —, sous `/projects/[projectId]/…`,
qu'un projet sans révision offre ; `revision`, les autres, sous
`/projects/[projectId]/revisions/[revisionId]/…`. Le contexte de lecture est dans l'adresse :
le projet dans le chemin, la révision dans le chemin ou, sur une fonction du projet, en
paramètre `revision_id` ; sous-projet filtré et date de calcul en paramètres, `subproject_id`
et `as_of`, comme le contrat les nomme. Les liens entre fonctions d'un projet les reportent,
et un témoin du front, `wf_last_project`, garde le dernier, dont la coquille tire le « retour
au projet » (WF-IHM-0010) ; il ne ramène qu'à un écran de projet de la table, fonction ou feuille
qui a son écran. Chaque route
de la table a sa page, ce que `frontend/src/app/[...path]/page.test.tsx` vérifie ; toute autre
adresse mène, par `frontend/src/app/[...path]/page.tsx`, à l'écran « introuvable ». Les pages du compte
(`/account`, `/account/password`, `/account/avatar`, `frontend/src/navigation/account.ts`)
ont leurs écrans (US-0320) : les informations du compte et ses préférences d'affichage — la
langue et le mode, les mêmes champs que le menu du compte écrit, enregistrés ensemble —, le
changement du mot de passe, offert au seul compte local, et l'avatar. L'image de l'avatar,
servie par l'API seule, est lue par le serveur de Next en rendant la page et écrite dans la
page en adresse `data:` (`avatar-source.ts`) : ni appel du navigateur à l'API, ni relais ;
l'écran de l'avatar seul la montre, le menu du compte garde les initiales.

La coquille se compose ainsi (`shell.tsx`, mise en page de la charte) : à gauche la barre
latérale (`navigation.tsx`), le logo et le choix du projet en tête, les fonctions en trois
groupes — la plateforme, par bloc de la FBS repliable ; le projet, avec la liste des projets et
le « retour au projet » ; la révision lue —, le bouton qui la replie au pied ; au-dessus de la
page, la barre (`top-bar.tsx`) : le bouton qui replie la barre latérale, le fil d'Ariane
(`frontend/src/navigation/breadcrumbs.ts`), la recherche — en place, sans fonction encore —, le
bouton des tâches de fond et le menu du compte. La barre latérale repliée garde son état dans
un témoin du front, `wf_sidebar_state`, que le layout racine lit pour la rendre telle
côté serveur. Le layout, rendu une fois, ne connaît pas l'adresse : le libellé du projet vient
de l'écran, qui l'a déjà lu pour son bandeau — `ContextBanner` le remet à la coquille par
`ShowProject` (`shown-project.tsx`), qui ne le nomme que tant que l'adresse montre ce même
projet. Le menu du compte (`account-menu.tsx`) porte les préférences d'affichage — langue et
mode, chacune un choix dans un sous-menu, écrit au compte à la sélection, le parcours au
clavier n'envoyant rien —, les pages du compte et la déconnexion. La déconnexion
(`closeSession`, un 401 valant session déjà close) oublie ce que le navigateur gardait de la
session — le témoin `wf_last_project`, les tâches du stockage `wf_background_tasks` et du suivi
— puis charge la page de connexion en document entier. L'entrée — la connexion, `/login`, et
le mot de passe oublié, `/login/reset` — est hors de la coquille : ni barre latérale, ni barre,
ni tâches (`shell-frame.tsx`, `isOutsideShell`), le logo au-dessus d'une carte. La page de
connexion présente les fournisseurs de `listAuthProviders` : le compte local toujours, que
l'annuaire partage quand il est activé, et le fournisseur d'identité activé par un lien vers
son `start_url`. La session ouverte, le navigateur charge en document entier l'écran visé
(`returnTarget(next)`, `frontend/src/navigation/document.ts`) — sans lui, l'accueil — : le layout relit la session, et
le suivi reprend les tâches qu'une session perdue avait interrompues.
Sans compte (401), il n'y a ni menu du compte ni barre latérale ; quand la session est
illisible, la barre latérale est rendue avec l'écran d'état seul, son bloc ouvert, et sans
menu du compte. La barre latérale est un repère (`<aside>` nommé) ; sur écran étroit, c'est
une feuille modale qui se ferme dès que l'adresse change ; Ctrl+B ne la plie que si elle est
rendue, et la plier rend le focus de ce que le rail cache au bouton du bloc ou au déclencheur.

Les pages système sont des pièces de la coquille (`frontend/src/app/`,
`frontend/src/components/system/`). Une lecture dont un écran ne peut se passer passe par
`readOrFail` de `frontend/src/api/problem.ts`, qui rend ses données ou lève : un 404 mène à
l'écran « introuvable » unique (`not-found.tsx`), qu'une adresse inexistante et une lecture
refusée atteignent sans distinction (WF-ADM-0110) ; l'API injoignable lève `Unreachable`, et
toute autre réponse `UnexpectedAnswer`. Une lecture dont l'écran se passe passe par
`readUnlessRefused`, à côté : elle ne rend rien sur les refus qu'il attend — un statut, et
le `code` de l'enveloppe quand le statut ne dit pas lequel —, et suit la même règle pour le
reste. L'écran de panne (`error.tsx` dans la coquille, `global-error.tsx` quand le layout
racine échoue) ne reçoit en production que le `digest` de l'erreur levée côté serveur :
`Unreachable` porte `UNREACHABLE_DIGEST`, qu'il annonce comme tel, `SignedOut` (un 401)
`SESSION_REQUIRED_DIGEST`, qui mène à la connexion (`loginHref`), `UnexpectedAnswer`
l'identifiant de corrélation de l'enveloppe, préfixé de `WATERFALL_CORRELATION;` pour
qu'aucune valeur de l'API ne prenne un sens pour Next (`NEXT_REDIRECT;…`), et qu'il affiche
en référence sans le préfixe (`failure.ts`). Sans enveloppe, ou sans `correlation_id`, la
référence affichée est le digest que Next calcule, celui de ses propres journaux. Un écran
ne dit jamais « vide » sur une réponse qu'il n'a pas lue. Quand la session est illisible, la
navigation garde l'écran d'état (WF-ADM-0130).
Chaque segment qui lit l'API a son `loading.tsx`, le squelette `ScreenSkeleton`, qui
porte un `role="status"` nommé — un lecteur d'écran ne l'annonce pas toujours ; la réponse est alors diffusée, et « introuvable » répond
200 et non 404 — un 404 doux, que Next marque `noindex` : le statut part avec le squelette,
avant que la page sache l'objet introuvable. Il est le même pour toute adresse introuvable,
ce qui compte ici. Chaque état vide — aucun projet, projet sans révision, référentiel
incomplet — se montre sur un exemple nommé du contrat (`empty`, `incomplete`).

L'accueil, `/`, est la liste des projets (`frontend/src/app/(home)/`, un groupe de routes pour qu'il
ait son squelette sans en donner un à toutes les pages) : filtrée par défaut sur les projets dont
l'utilisateur est contributeur, par le filtre du contrat (`is_contributor`), que l'écran montre et
qu'un lien lève — `?is_contributor=false`, sous le nom du contrat
(`frontend/src/navigation/home.ts`) — : un filtre, jamais une restriction de lecture (WF-PRJ-0060).
Le lien qui le lève n'est offert qu'à une session qui porte `all_projects_read` (WF-ADM-0110) : levé
pour un autre, le filtre rendrait la même liste, et le lien promettrait ce qu'il ne fait pas
(WF-IHM-0090, #522) ; sans cette permission, l'accueil reste filtré quoi que dise l'adresse —
`?is_contributor=false` compris, la page demandant `is_contributor=true` —, le badge « Mes projets »
affiché sans aucun lien, et le choix du projet mène à l'accueil plutôt qu'à la liste levée. La barre
latérale et le fil d'Ariane mènent à la liste filtrée, le choix du projet à la liste levée, « Tous
les projets » ; `/projects`, l'ancienne adresse, renvoie à l'accueil. Les projets sont une
configuration de plus de la grille dense (`project-list-grid.tsx`, préférences sous la clé
`projects`) : le libellé, lien qui ouvre le projet, le code, l'état par sa pastille et la date de
modification, chaque colonne triée par le serveur (`sort_by`), cherchée par lui sur le libellé et le
code (`search`), filtrée par état — des boutons pressés qui n'écrivent que l'adresse (`states`) — et
par période sur la dernière modification (`from`, `to`, EP-02/L42e) : deux jours saisis dans l'heure
locale du lecteur, envoyés comme les instants du début du premier et du début du lendemain du
dernier, la fin exclue. Une adresse qui ne nomme aucun état demande les six, l'accueil montrant tout
ce que l'utilisateur peut ouvrir, là où le contrat, sans `states`, ne rendrait que les projets en
cours (WF-PTF-0010) ; les boutons pressés sont les états que l'adresse nomme, « Tous les états »
quand elle n'en nomme aucun : l'adresse fait foi. Une période que le serveur refuse — une fin qui
précède le début, 422 `VALUE_OUT_OF_RANGE` sur `/query/to`, `params.minimum` le début donné — est
dite à son champ, le début nommé par son jour local, qui prend le focus chaque fois que la liste
revient refusée, comme une borne d'une colonne de nombres (`range-filter.tsx`) ; la liste n'est pas
lue, et une phrase tient la place de la grille. Sa ligne de totaux dit combien de projets le serveur
retient, et elle mène aux autres pages par `ListPages` ; une page demandée au-delà de sa fin le dit,
et ramène à sa dernière page : seule une liste qui ne tient aucun projet, sans état, période ni
recherche, se dit vide. Les écrans du projet lui-même — le projet, ses paramètres avec ses
sous-projets et ses contributeurs, son cycle de vie — exercent la sortie du cycle de vie
(`ExitCommand`), irréversible, confirmée dans la page avant que son action serveur ne la demande, la
modification du projet, sur ses paramètres (EP-02/L44a, plus bas), et, sur ses paramètres encore, les
commandes de ses sous-projets et de ses contributeurs (EP-02/L44b, plus bas). Les tables de données des
paramètres sont trois grilles denses (#301,
`settings-grids.tsx`), chacune avec sa clé de préférences et ses noms dans l'adresse (`breakdown_`,
`subproject_`, `contributor_`) : le lotissement, une grille arborescente — chaque poste, ses lots
sous lui, leurs livrables sous eux —, dans l'ordre saisi, qui ne se trie pas et se plie, cherchée
par le serveur sur ses libellés (`breakdown_search`) et filtrée par nature (`breakdown_kinds`,
EP-02/L42f) — lue ainsi, sans compteur (`lock_version` nul, `WorkBreakdownReading`), ses postes et
ses lots ne montrent que ce qui est retenu, ce qu'elle dit, et une telle lecture ne se renvoie jamais
à `setWorkBreakdown` ; les
sous-projets, cherchés par le serveur sur leur code et leur libellé (`subproject_search`), triés par
lui sur chaque colonne (`subproject_sort_by`) et filtrés sur leurs coûts réels
(`subproject_has_actual_costs`) ; les contributeurs, cherchés par le serveur sur le nom du compte
(`contributor_search`), triés par lui sur chaque colonne (`contributor_sort_by`), filtrés sur leur
qualité (`contributor_kinds`, `kinds` du contrat), un bouton pressé par qualité (`ValuesFilter`,
`filters.ts`), et sur l'état du compte (`contributor_is_active`) — une colonne booléenne se filtre
par un choix (`ChoiceFilter`), `true` ou `false`, aucun retenant toutes les lignes (`readBoolean`) ;
chaque table plate se filtre ainsi sur chacune de ses colonnes (WF-IHM-0130, EP-02/L42e). Les
volumes du §4.6.2 — dix sous-projets, cinquante contributeurs par projet — tiennent en une page.
L'historique des états, une liste de lecture, reste une table simple. Les sous-projets offrent leurs
commandes comme le projet liste `update` (`subproject-commands.tsx`) — absente, rien ; indisponible,
« Nouveau sous-projet » présenté `aria-disabled` avec ses conditions ; disponible ou non, sur chaque
ligne, la modification et la suppression comme la ligne les liste (`Subproject.available_commands`,
EP-14/L44e) — absente, rien ; indisponible, présentée `aria-disabled`, décrite par ses conditions, et
un appui les dit dans la région de la liste (`UnavailableCellCommand`) : sur un projet clos, chacune
nomme `project_not_terminal` (WF-IHM-0090). La création et la modification ouvrent le formulaire du
référentiel (`ReferenceForm`), le code et le libellé exigés, un code déjà porté (409 `ALREADY_EXISTS`,
`fields[]`) dit au champ, son porteur nommé par le libellé que le refus donne
(`conflicting_object_label`) ; la suppression, confirmée dans la page, est indisponible — ou refusée
par le serveur, 409 `STATE_FORBIDS_OPERATION` nommant la première condition qui manque, dit au-dessus
de la liste (`Reactivations`) — pour un sous-projet qu'une révision marquée cite
(`subproject_not_cited`, §4.4.1) ou auquel des coûts réels sont imputés
(`subproject_without_actual_costs`, WF-PRJ-0050) ; l'écran n'en déduit rien de `has_actual_costs`. Les
contributeurs, comme le projet liste `manage_contributors` (`contributor-commands.tsx`), se modifient
en une liste entière dans un dialogue (`setContributors`) : la qualité de chacun, son retrait, et
l'inscription, une à une, des propositions du serveur (`listContributorSuggestions`, WF-PRJ-0070),
chacune avec le nœud et les rôles qui la font proposer (`org_node_label`, `resource_role_labels`),
inscrite active comme le serveur le dit (`is_active`), rien n'étant écrit avant l'enregistrement ; une
liste sans chef de projet est refusée avant toute demande (WF-PRJ-0060), un refus par champ
(`/contributors/<n>/…`) — un compte inconnu (`UNKNOWN_USER`) ou désactivé (`USER_INACTIVE`) — dit à la
ligne du compte qu'il désigne, en le nommant. L'écriture part d'une
lecture entière, avec son compteur : quand la grille lit la liste filtrée, la page la relit entière
pour le dialogue, et la grille garde ce que sa lecture retient. Une modification répondue remplace sa
ligne, une suppression l'ôte, une liste répondue remplace celle d'une lecture entière, tant que leur
compteur est plus récent — face au faux back, tant que l'écran reste ouvert (`MockupNotice`, sous
l'en-tête) ; une création n'ajoute aucune ligne, la page relue la range. Une réponse ne ferme que le
formulaire, la confirmation ou le dialogue d'où elle est partie, jamais un autre ouvert depuis
(compteur d'ouvertures, `key`, #672). Une modification d'un sous-projet ou de la liste des
contributeurs rouverte pendant qu'une écriture du dialogue fermé est en route part encore de la
version d'avant, que sa réponse remplace, et le serveur la refuse (412) : la décision de #661 ne leur
est pas encore appliquée (#734). Les pièces communes du
référentiel (`CommandedList`, `useAnswered`) étant liées à ses natures d'objet, ces deux listes ont
les leurs, sur les mêmes pièces : le formulaire, la commande d'une cellule, la région des refus.

Le projet se crée et se modifie dans la maquette (EP-02/L44a, décision de l'auteur du 2026-10-08,
#513, #524 ; `project-form.tsx`), par le formulaire du référentiel (`ReferenceForm`, qui écrit aussi
un autre objet que ceux du référentiel et saisit une date de planning). L'accueil offre « Créer un
projet » à une session qui porte la permission de le créer (`project_create`, `platformOffer`,
WF-ADM-0100), indisponible, décrite par le refus qu'elle rencontrerait, tant que le référentiel
minimal est incomplet (`getReferenceReadiness`, WF-CYC-0120) ; le formulaire prend ce que
`ProjectCreate` prend — le libellé, exigé (WF-PRJ-0080), le code, qui peut attendre la commande
(WF-PRJ-0010), la description — et mène à l'écran du projet que le serveur a créé, que le faux back
sert sous les traits du témoin, tant que l'accueil est encore montré : une réponse arrivée après
qu'on l'a quitté ne remplace pas la navigation choisie. Une réponse arrivée après « Annuler », le
dialogue fermé mais l'accueil toujours montré, y mène quand même : c'est la seule façon de dire le
succès, que la liste simulée ne montre pas, et fermé pendant l'attente, le dialogue ne fait rien
taire. Les paramètres du projet présentent son identité et ses faits — le libellé, le code, la date
de réception de la commande, la description, le taux d'inflation et la probabilité de gain — et leur
modification (`updateProject`) comme le projet liste sa commande (`update`) : absente, disponible,
ou indisponible avec ses conditions — un projet terminal (WF-CYC-0100). Les deux taux se saisissent
en pourcentages et partent en rapports du contrat, la virgule déplacée sans flottant
(`editablePercent`, `percentRatio`) ; la probabilité de gain suit sa propre commande
(`update_win_probability`, EP-14/L44e) : indisponible — à partir de En cours,
`project_before_in_progress` manquante (WF-PRJ-0090) —, elle est montrée figée (`control: "fixed"`),
ses conditions dites sous elle, et n'est pas envoyée ; une date ou un texte laissés vides partent
nuls, une date à moitié saisie, que son champ rend vide (`validity.badInput`), est refusée avant
tout appel. Une réponse ne ferme que l'ouverture du formulaire d'où elle est partie : arrivée après
que le dialogue a été fermé puis rouvert, elle s'affiche et laisse le nouveau dialogue ouvert
(#660) ; et tant qu'une modification envoyée d'un dialogue fermé est en route, « Modifier le projet »
est inactive (`aria-disabled`, `aria-busy`, décrite par « Enregistrement en cours… », `WritingNote` ;
`onWriting` du formulaire) : rouvert, le formulaire écrirait depuis la version que sa propre réponse
remplace, et le serveur le refuserait (412) — il s'ouvre sur la version qu'elle apporte (#661, #673).
Elle se libère à la réponse, quelle qu'elle soit — un succès, un refus, une action serveur rejetée,
l'API injoignable — ; une action serveur qui ne répond jamais la laisse inactive jusqu'au
rechargement de la page. Le compteur d'ouvertures reste, en garde-fou : la commande attendant
l'écriture, aucune autre ouverture ne vient avant la réponse. La réponse prend la place des faits lus tant qu'elle est plus récente que le projet lu
(`lock_version`) — face au faux back, tant que l'écran reste ouvert (`MockupNotice`, dit tant que la
modification est disponible) —, la page relue ; la section est remontée quand l'écran montre un
autre projet. Un refus par champ se dit au champ, tout autre sous le formulaire — la probabilité
figée entre-temps (409 `STATE_FORBIDS_OPERATION`, la condition nommée), la version périmée avec
l'offre de relire ; un taux hors de ses bornes (422 `VALUE_OUT_OF_RANGE`, `params.minimum` ou
`maximum`, en rapports) se dit au champ, la borne en pourcentage comme le champ la saisit
(`ratioPercent`) ; le code déjà porté par un autre projet (409 `ALREADY_EXISTS`, `fields[]`) se dit
au champ, le projet qui le porte nommé par le libellé que le refus donne
(`conflicting_object_label`), l'écran ne montrant pas les autres projets — génériquement sans lui
(`kind="project"`, EP-02/L42g). Le cycle de vie dit le prochain état du projet, son déclencheur et
les conditions qui lui restent, une par une (`getProjectNextState`, `NextStateFacts`, WF-CYC-0050),
qu'aucune commande ne mène à Chiffrage ni à En cours (WF-CYC-0020) ; le déclencheur est l'un des
deux faits que le contrat énumère (`LifecycleTrigger`), dit par son catalogue
(`enums.LifecycleTrigger`). Un projet qu'aucun fait ne mène plus loin — le serveur répond sans
prochain état ni déclencheur — le dit : en cours, seules ses sorties restent ; terminal — un état où
mène une sortie (`EXIT_STATES`) —, il est clos, et aucun état ne le suit (WF-CYC-0080).

Une période d'une liste prend l'une des trois formes du contrat (`period.ts`), toutes saisies dans
le même filtre (`PeriodFilter` de `frontend/src/components/grid/`) : deux jours de planning, bornes
incluses, que le serveur reçoit tels quels — les pièces des coûts réels — ; deux jours locaux tirés
en instants, la fin exclue — l'accueil — ; deux instants saisis à la minute en heure locale, la fin
exclue — le journal d'audit. Seul le navigateur connaît son fuseau : les champs d'instants montrent
l'adresse, et le bouton envoie, une fois la page hydratée ; un côté laissé intact part tel que
l'adresse le nomme. Le refus d'une période inversée, la règle de toute période du contrat, est dit
au champ de la fin, le début nommé tel que son champ le montre.

Un écran de données de projet lit son contexte par `readAddress` de
`frontend/src/components/context/reading.ts` — projet, révision, filtres actifs, lus une
fois par requête — et le montre par `ContextBanner`, au-dessus de son `<main>`
(WF-IHM-0020). La lecture porte `edits`, les commandes `edit_*` de la révision que
l'appelant peut exercer (`read-only.ts`), qu'un écran reçoit plutôt que de les déduire : une
grille lit sa propre commande — `edits.has("edit_planning")` pour le planning —, car un
chiffreur peut saisir le devis sans toucher au planning. `readOnly` — révision marquée, ou
aucune commande `edit_*` disponible — ne sert qu'à l'avis du bandeau. Une valeur sous
enveloppe `Computable` s'affiche par `ComputedIndicator`, jamais sans la date de son
`CalculationContext`, et non calculable avec son motif, un code que le catalogue rend
(`enums.NotComputableReason.*`, `indicator.tsx`).

Une courbe est une figure de `Chart` (`frontend/src/components/chart/`, US-0240) : Apache
ECharts, importé pièce à pièce et dessiné en SVG, son option `aria` active ; sa légende la
nomme, le dessin est une image que décrit une phrase du catalogue, et ses valeurs sont un
tableau sous lui, l'alternative textuelle (WF-IHM-0100). Le composant client propre à la courbe
(`index-chart.tsx`, `milestone-chart.tsx`, `curve-series-chart.tsx`, `workload-chart.tsx`) lui
remet son option, construite dans une palette : ECharts écrit ses couleurs dans les attributs de
son SVG, où une variable CSS n'atteint pas, et les jetons `--chart-1` à `--chart-4`,
`--muted-foreground`, `--foreground`, `--input`, `--border` et `--background` y arrivent par
des sondes cachées que le navigateur peint dans le mode affiché ; un changement de
mode, du poste ou forcé par le compte (`data-theme`), redessine la courbe. Elle se dessine d'un
coup, sans animation, et une légende y est inerte : un clic, à la souris seule, ne cache aucune
série. `curve` nomme chaque courbe à son dernier point tracé, quel que soit leur nombre — pas de
légende, qu'une entrée par sous-projet ferait déborder sur le tracé —, les noms qui se
chevaucheraient écartés, et la distingue aussi par sa couleur, son symbole et son trait ; une
courbe sans point tracé n'a pas de nom sur le dessin, son tableau la nomme ; une série de barres
(`bars`) se distingue aussi par le motif du symbole de son rang, que la légende montre ;
`timeAxis` gradue un axe de temps au premier de chaque mois que `monthTicks` tire des instants
qu'il montre — tous les deux, trois, six mois ou chaque année sur une longue plage, l'année seule
alors, ou tous les deux, cinq, dix ans, sur les années multiples du pas (#415) —, écrits
dans la langue du poste, dans son fuseau ou en UTC pour un axe de dates de planning, que
`planningInstant` place à leur minuit UTC, l'option de la figure disant alors `useUTC`. Une
courbe trace les chaînes de l'API telles quelles — ECharts en tire une position —, une valeur
non calculable étant un trou, un cumul d'événements datés — valeur acquise, coût réel — en
escalier (`step`), une marche verticale par deux points à la même date, et le tableau les écrit
par `src/i18n/format.ts`, les zones par `Signal`. Une figure qui reçoit `exported` offre la
commande « Exporter en PNG » (WF-IHM-0130) : `exportPng` la redessine dans une instance hors
écran, en rendu canvas, à la taille d'une image, son titre et sa provenance (`useProvenance`) —
projet, révision du calcul, ce sur quoi la figure est calculée par ailleurs (`detail` : la base et
le nœud d'organisation filtré du plan de charge), date de calcul, écrite dans l'heure du poste au
moment de l'export —
en tête, repliés à la largeur de l'image (`wrapLines`), la figure descendue de la hauteur de
leurs lignes, sur le fond de la charte, puis libère l'instance. Un choix qui change ce qu'une
courbe lit — les délais de paiement, la base et le nœud d'organisation du plan de charge — est un
paramètre de l'adresse, que le serveur envoie à l'API : le front ne filtre ni ne décale rien.

L'écran des indicateurs d'un projet lit ses indicateurs et ses courbes dans la révision de sa route
(`revision_id`) — ceux d'une révision marquée tels que son marquage les a conservés —, ou à la date
que l'adresse demande (`as_of`), jamais les deux, que l'API refuse ensemble ; une offre marquée
avant l'état En cours, qui n'en a conservé aucun, est refusée comme un projet qui n'est pas en
cours, et l'écran le dit. Un avis en tête nomme, des indicateurs et de l'évolution des indices,
celui qui est calculé sur une autre révision que celle du bandeau, et laquelle — l'évolution,
toujours au jour sur la révision en cours (`ComputedElsewhere`) ; une courbe nomme la sienne dans
l'image qu'elle exporte. Le sous-projet de l'adresse, celui que le bandeau montre (WF-IHM-0020),
restreint ce que l'API lit pour lui (`scope`, WF-IND-0020) — les indicateurs, l'évolution des
indices, les coûts cumulés et les courbes de valeur acquise (EP-02/L42e) —, sauf le diagramme
temps/temps, calculé pour le seul projet : il suit des jalons, qu'un sous-projet n'a pas
(WF-IND-0020). La pastille du bandeau le dit (`restricts` de `ContextBanner`, comme pour la grille
du reste à engager, #459), et le suivi des jalons dit qu'il porte sur le projet entier
(`WholeProject`). Un sous-projet que le projet n'a pas, refusé par 422 `UNKNOWN_SUBPROJECT` sur
`/query/scope`, est dit comme les indicateurs d'un projet qui n'est pas en cours, jamais lu comme
des indicateurs nuls ; une courbe sans point dit qu'elle n'a rien à tracer plutôt que de tracer un
zéro, et une série sans point parmi d'autres qui en ont le dit sous le graphique — le budget de
référence d'une maille qu'aucune référence ne budgète — ; une courbe vide non décalée n'offre pas de
la décaler, et, décalée, garde la commande qui retire le décalage.

Une grille est la grille dense de `frontend/src/components/grid/` (US-0110), configurée par
écran : une `GridConfig` (`columns.ts`) nomme la clé de ses préférences, stable, ses colonnes
— clé, libellé du catalogue (`grid.columns.*`), format, alignement, largeur par défaut,
celles de ses cellules que le serveur calcule, figée ou non, la colonne du contrat qu'elle montre
(`contract`) — celle par laquelle le serveur la trie et sur laquelle un collage la vise —, et,
pour une colonne étroite, l'icône qui tient lieu d'en-tête et que son libellé nomme, ou ce que
rend sa cellule en place de la valeur formatée (`render`) — et, s'il y en a un, son arbre
(niveau, icône de nature par `RowNatureIcon`). Trier est d'abord l'affaire de la grille : une
grille arborescente dont les lignes gardent l'ordre du plan n'en trie aucune (`sorts: false`), et
son adresse n'en demande aucun — le planning (§3.4, WF-IHM-0060, #525). Le devis et le reste à
engager, dont le serveur ne trie que les lignes sous chaque tâche, les tâches gardant l'ordre de
l'arbre (WF-IHM-0060, #526), ne trient pas par une colonne de la seule tâche, que le contrat
accepte mais dont le tri ne changerait rien : la colonne le dit elle-même
(`GridColumn.sorts: false`), en gardant sa colonne du contrat, que vise un collage là où la grille
en prend un (le planning, le devis) — l'avancement et la fin au reste à engager, qui n'offre ainsi
que ce qui agit (dans l'esprit de WF-IHM-0090). Ni son en-tête ni l'adresse n'en
offrent le tri, et un tri par elle, dans l'adresse ou gardé par le compte, est ignoré comme un tri
inconnu (`sortColumns`). La
configuration lit les lignes par des
fonctions : elle se remet à `DenseGrid` dans un composant client propre à l'écran
(`estimate-grid.tsx`, `planning-grid.tsx`), et la page, serveur, ne lui passe que des données —
la structure lue et, de chaque nœud, les seuls champs que la grille lit : ceux de toute grille
(identité, version, champs calculés, numéro, niveau, parent, nature, libellé) et ceux de ses colonnes,
que nomme sa configuration (`ESTIMATE_FIELDS`, `PLANNING_FIELDS`). La page les demande à
`listNodes` (`fields`, `nodeFieldNames` : un champ d'une facette sous son nom, `task.label`) et
les projette encore (`projectNodes`) : un serveur peut rendre plus qu'on ne lui demande — le faux
back rend son exemple entier —, et les six mille nœuds entiers pèsent six mégaoctets et demi dans
la page, projetés, de quarante-huit à soixante-cinq pour cent — le parent, par lequel l'arbre se
plie, y a ajouté quatre points ; la lecture de l'écran
(`readGridScreen`) ne rend que les lignes projetées et les totaux, jamais la réponse entière. Un
champ d'une ligne qui ne dit rien — nul, ou faux pour un drapeau (`SPARSE_LINE_FIELDS`) — ne
traverse pas, la cellule le lisant comme nul, et l'identifiant du sous-projet d'une ligne ne
traverse que vers une grille qui le saisit (`withoutSubprojectIds`). Une colonne qui lit un champ
nouveau l'ajoute à cette liste : le typage de la ligne le demande, et `projection.test.tsx`
vérifie que la grille lit la même chose de la ligne projetée que du nœud entier, et que la page
demande ce qu'elle projette. Le calculé se lit cellule par cellule (WF-IHM-0030,
`computed-nodes.ts`) : un champ qu'aucune écriture ne
porte — les montants, la marge — l'est dans chaque ligne qui le porte, et sa colonne a Σ en
en-tête ; un champ saisissable l'est là où le nœud le nomme dans `computed_fields`, jamais
d'après son mode ni sa nature. Une cellule calculée est grisée, marquée Σ et nommée « Calculé »
— la marque se lit sans la couleur — ; c'est un bouton qui, cliqué ou pressé au clavier, refuse
la saisie dans un Popover (`ComputedCell`, `ComputedRefusal`) en disant ce dont sa valeur
dépend, que le serveur dit : chaque colonne calculée nomme le champ du contrat de chacune de ses
cellules, et le refus appelle `getComputedValueDependencies` pour le nœud et ce champ, par une
action serveur (`readComputedDependencies`) que la grille reçoit de son écran
(`nodeDependencies`, un lecteur par lecture de la page) — tant qu'il est ouvert seulement, et
une fois par question : la lecture de la page, le nœud et le champ. Un refus fermé ne demande
rien ; rouvert après une relecture de la page, il redemande, car les lignes qu'il nomme ont pu
changer de numéro ou de libellé sans que le nœud change de version ; un échec se redemande à
l'ouverture suivante, seule une réponse est gardée. Dans une seule région annoncée
(`role="status"`, `aria-live="polite"`), présente dès l'ouverture et `aria-busy` pendant la
lecture, il dit qu'il la lit, puis les règles qui la calculent (`enums.ComputedDependency.*`) et
les lignes dont elle vient, nommées par leur numéro et leur libellé, que la grille les montre ou
non ; un refus du serveur, ou l'API injoignable, se disent par `OutcomeNotice`. Une ligne qui dit
elle-même ce dont sa valeur dépend — un risque, sa gravité et sa provision (`Risk.computed_fields`)
— le donne à sa colonne (`dependsOn`), et le refus en nomme les règles d'emblée, sans rien
demander. Le front ne lit aucune règle du
noyau. Le Popover ne se monte
qu'au premier essai : une racine de Radix par cellule calculée alourdirait l'hydratation du
premier écran. La grille de planning
et celle de devis sont deux configurations de ce seul composant (`planning.tsx`,
`estimate.ts`), qui partagent l'arbre, le numéro et le libellé d'un nœud (`nodes.tsx`) et la
lecture de la structure principale (`grid-screen.ts`) ; le planning demande au serveur les
seules tâches (`kinds=task`). Le devis présente, d'une ligne comme d'une tâche, récapitulative
comprise, et en total, le montant à l'année de référence (`base_amount`) et le montant corrigé de
l'inflation, tels que le serveur les rend, jamais le budgété ni le réestimé (WF-DEV-0050) ; il
nomme la catégorie et le rôle d'une ligne par les libellés que le serveur résout, l'objet actif ou
désactivé (`cost_category_label`, `resource_role_label`, #305) — les listes du référentiel ne
servent qu'au choix d'une saisie, offerte seulement sur un objet qu'elles connaissent ; elles ne
demandent les objets désactivés (`include_inactive`) qu'à une session qui porte la permission de
lecture de leur partie du référentiel, que le contrat exige, et un chiffreur sans elle saisit sur
les objets actifs (#351). Ce qu'une écriture rend se lit comme la grille le lit (`nodesWritten`) :
les nœuds écrits et leurs ancêtres entiers, des tâches redatées la part de leur calendrier qu'elle
montre (`rescheduled`), des lignes
et des tâches déplacées dans le temps la part de leurs montants qu'elle montre (`reinflated`) —
chaque part ne pose que ses champs : celles d'une même ligne, d'une écriture ou de plusieurs, se
posent l'une sur l'autre dans l'ordre des réponses (`answers.ts`).
Le mode de planification et l'avancement s'y montrent par une
icône nommée, le chemin critique par une icône et le gras sur la marge, jamais par la seule
couleur ; une date se montre dans sa forme courte. Le tri et la
recherche sont dans l'adresse, sous les noms du contrat (`sort_by`, `sort_order`, `search`,
`query.ts`) : un en-tête cliqué ou une recherche saisie change l'adresse, la page relit
l'opération avec eux, et la grille rend les lignes dans l'ordre reçu, les totaux de la
réponse en pied — TanStack Table n'y enregistre aucun modèle trié, filtré ni groupé. Au
clavier, la grille est un seul arrêt de tabulation, sa cellule active, que les flèches déplacent,
l'en-tête compris — ses boutons et ses poignées hors de la tabulation — : Entrée ou Espace sur un
en-tête trie sa colonne, Maj et les flèches l'élargissent ou la rétrécissent (motif `grid` d'ARIA, #182). Un refus
d'écriture reste dit jusqu'à ce que l'utilisateur ferme son avis (`OutcomeNotice`,
`dismissible`), quoi qui réussisse après lui. Seules
les lignes visibles sont rendues (`row-window.ts`, sur `@tanstack/virtual-core`) : le
virtualiseur est lu comme un magasin dont l'instantané est une donnée, qui ne change que
quand la fenêtre bouge. Le React Compiler n'est pas activé dans ce front, mais le lint de
React refuse l'adaptateur de TanStack Virtual, dont un rendu compilé figerait les réponses
(`react-hooks/incompatible-library`). La hauteur d'une ligne suit la taille de la police
racine (1,75 rem). L'en-tête et les totaux sont collés au haut et au pied de la grille, le
numéro et le libellé à son début. La ligne d'en-tête de toute table, liste comme grille dense, est
sur le fond `muted` de la charte : `TableHead` le pose à l'en-tête d'une colonne, dans le `<thead>`,
non à celui d'une ligne, et un `<thead>` écrit à la main le prend de même (#508), ce que
`frontend/src/components/thead-guard.test.ts` vérifie dans les sources. La grille prend la hauteur que lui laisse son écran : un
écran de grille est un `Screen` qui remplit la fenêtre (`fill`), la page bornée à sa hauteur
(`ShellFrame`), et la grille s'y réduit de la hauteur de ses lignes jusqu'à un plancher —
aucune hauteur n'y est calculée d'après ce qui la précède ; une fenêtre trop basse pour ce
plancher fait défiler la page. Colonnes masquées, largeurs et tri sont une préférence
d'affichage (`settings.ts`, WF-IHM-0060) : lues de la session, la grille remplacée entière à
chaque écriture et ce qu'elle ne règle pas renvoyé tel quel. Une grille garde dans le compte son tri
et ses colonnes — celles qu'elle masque, et leurs largeurs —, jamais sa page ni ses filtres, qui
vivent dans l'adresse (règle validée par l'auteur le 2026-10-09). Une colonne ou une largeur
s'écrit après une pause, avec le tri gardé tel quel ; ce qui attend part quand la page est
quittée ou cachée, avant une recherche et au démontage — au mieux : une action serveur ne
porte pas `keepalive`, et la fermeture d'un onglet peut l'interrompre. Seul un clic
d'en-tête écrit le tri, une fois que la page le montre (`recordShown`), avec les réglages de
ce moment — une largeur changée pendant la navigation comprise : Next porte une action
serveur dans l'état de son routeur, et une navigation ne se montre pas avant que les actions
lancées après elle aient répondu — écrite au clic, la préférence retenait le tri d'un
aller-retour, et de chaque action en file avant elle. Jusque-là, elle attend comme le reste,
et part avec lui si la page est quittée, cachée ou démontée, ou avant une recherche. L'adresse fait foi :
un tri levé y reste, `sort_by` vide, et le tri gardé ne sert que quand elle ne dit rien du
tri. Chaque grille est à la route de sa fonction, `…/revisions/[r]/planning` et
`…/revisions/[r]/estimate` ; la révision elle-même mène à la première fonction d'une révision
que la session peut lire, dans l'ordre de la FBS et de la barre latérale — le planning, ou le
devis pour un chiffreur qui ne lit pas le planning. L'écran du devis dit au-dessus de sa
grille les taux horaires qui manquent à son calcul, avec le chemin du référentiel pour qui le
lit, et ses indicateurs, avec leur date de calcul, ou qu'ils sont indisponibles quand l'API
ne les trouve pas ou les refuse faute de taux horaire (`HOURLY_RATE_MISSING`, #159) — ces
deux cas ne font pas tomber l'écran ; toute autre réponse suit la règle des lectures
(`EstimateSummary`).

La grille de planning présente aussi la description d'une tâche et l'avancement physique d'une
récapitulative, un pourcentage calculé ou non calculable, son motif en titre ; puis le Gantt
(FBS-4.3.3, `frontend/src/components/gantt/`), sa dernière colonne, en lecture seule. Chaque cellule
dessine en SVG la ligne de sa tâche — sa barre, les morceaux des liaisons qui la quittent, la longent
ou l'atteignent, les mois de l'axe — : le dessin est aligné ligne à ligne sur la grille, rendu avec
ses seules lignes visibles, et suit la largeur de sa colonne, en part de cette largeur. La
disposition (`ganttLayout`, `layout.ts`) se calcule une fois pour les lignes que la grille montre,
écritures comprises, que `DenseGrid` remet à ce qu'un écran met autour d'elle (`around`,
`GanttRows`) — jamais en prop de chaque ligne ; l'en-tête dessine l'axe (`GridColumn.axis`), son
libellé ne nommant plus la colonne qu'aux lecteurs d'écran. Rien n'y est planifié : une tâche va du
début de son premier jour à la fin du dernier, une fin à l'heure 0 étant le début de son jour, un
jalon se tient à sa fin, et l'axe va du premier du mois du plus tôt au premier du mois qui suit le
plus tard (`monthTicks`, `chart/ticks.ts`, sans ECharts). Une liaison joint l'endroit que son type
nomme sur le prédécesseur à celui qu'il nomme sur la tâche ; un prédécesseur hors de la réponse n'en
dessine aucune. Une récapitulative est un crochet, un jalon un losange, une tâche une barre, pleine
sur le chemin critique et creuse ailleurs, et chaque barre est une image nommée par ses dates et
« critique » : rien ne se lit à la seule couleur. Aucune cellule du Gantt ne prend de saisie, et
seul le bouton qui précède le crochet d'une récapitulative y prend le pointeur, pour la plier ou la
déplier. Les autres feuilles du planning ont leur écran, où son en-tête mène : l'arborescence de
tâches (FBS-4.3.5, `…/task-tree`, `frontend/src/components/tree/`), un `tree` d'ARIA sous la racine
du projet, le premier niveau côte à côte, les suivants sous leur parent, un seul arrêt de tabulation
que les flèches parcourent, la profondeur dans l'adresse (`depth`) ; et les chronologies
(FBS-4.3.1, `…/timelines`), une par lien (`timeline`), leurs tâches sur l'axe qu'elles partagent,
dessinées comme le Gantt. Le serveur sélectionne ce que chacune dessine (#463) : l'arborescence
demande les récapitulatives jusqu'au niveau de l'adresse (`summaries_only`, `max_level`), une
chronologie les tâches qui y sont inscrites (`timeline_id`). Le faux back ignorant ces filtres,
chacune applique encore le même critère à la réponse (`summaryTree`, `inscribedTo`) : un filtre
idempotent, qui ne change rien contre un serveur qui les tient, écart temporaire d'EP-02 retiré
avec le back d'EP-03. L'arborescence offre exactement les niveaux que la structure a, du premier à
celui de sa plus profonde récapitulative, que le serveur dit quels que soient les filtres
(`meta.summary_depth`, #494), et montre le niveau demandé, ou le plus profond quand on lui en
demande un au-delà (`depthShown`).

L'écran des risques, `…/revisions/[r]/risks` (`frontend/src/components/risks/`), lit chacune de
ses opérations dans la révision de sa route (`revision_id`) : les totaux des provisions des
risques retenus, par état et le total général, tels que le serveur les rend ; le filtre par
état, des boutons pressés qui n'écrivent que l'adresse (`states`, sous le nom et la forme du
contrat) ; la grille dense, une configuration de plus (`risk-grid.tsx`), en lecture, où la
gravité et la provision sont des colonnes calculées entières — aucun champ de nœud à demander
(`field` rend `undefined`), leur refus nomme les règles que le risque porte pour chacune
(`computed_fields`, `dependsOn`) — et la case de matrice une colonne de `Signal` ; la matrice, ses axes nommés
par les bornes que rend le serveur, chaque case par son signal et son nombre de risques ; et,
quand l'adresse nomme un risque (`risk`), son détail : notes, ligne de provision présente ou
retirée à la survenance, historique des réexamens. Le libellé d'un risque est un lien hors de la
tabulation : la grille suit le lien d'une cellule qui n'est pas saisie à Entrée
(`grid-keyboard.ts`).

L'écran du reste à engager, `…/revisions/[r]/remaining` (`frontend/src/components/remaining/`,
`remaining.tsx` de la grille), lit ses indicateurs dans la révision de sa route
(`getRemainingIndicators`, `revision_id`) — le total, la marge sur le budget de référence et
l'écart à la revue précédente, absent plutôt que nul sans elle, les totaux par nature et, par
sous-projet, le reste à engager et la marge sur son budget avec le `Signal` de la zone que le
serveur donne, et la couverture des risques (`RiskCoverageSummary`) —, ou les dit indisponibles
quand l'API ne les trouve pas ; et la
grille dense, une configuration de plus, sur les lignes des seules tâches démarrées, à moins que
l'adresse ne demande aussi les non démarrées (`progress`, sous le nom et la forme du contrat, qu'un
lien de son en-tête écrit). Le montant budgété, les grandeurs et le réestimé au reste à engager
précédent, puis les grandeurs et le réestimé courants (WF-RAE-0040) ; les trois montants y sont des
colonnes calculées, les grandeurs précédentes des valeurs conservées, jamais saisies ; les grandeurs
d'une ligne se réestiment une par une par `setLineRemaining`,
là où la ligne dit l'accepter (`remaining_entry`) et où son nœud accepte le champ — jamais d'après
l'avancement de sa tâche —, la commande `edit_remaining` posant Annuler et Rétablir ; la fin d'une
tâche s'y montre sans se saisir, et la fin dépassée par une marque propre, que le serveur dit
(`finish_overdue`). Son bandeau ne montre que le sous-projet, seul paramètre de contexte que ses
lectures prennent, et dit qu'il ne restreint que la grille, ses indicateurs étant ceux du projet
entier (`gridOnly` de `ContextBanner`, #459). Le Kanban du démarrage des tâches, FBS-4.5.3, est une
feuille de la fonction, `…/revisions/[r]/kanban`, où l'en-tête de la grille mène : toutes les tâches
non démarrées, les démarrées et les terminées avec leur date, telles que les rend
`listStartableTasks`, chacune une carte, un jalon non démarré dont les prédécesseurs sont terminés
signalé à terminer (`predecessors_completed`) ; aucun pourcentage, aucune commande. L'opération lit
la révision en cours : sur une
révision marquée, l'écran le dit et ne demande rien.

L'écran des coûts réels, `…/revisions/[r]/actual-costs` (`frontend/src/components/costs/`), lit
ceux du projet — ils ne sont pas versionnés, la révision de la route n'est que le contexte du
bandeau — page par page, comme le serveur les pagine (`offset`, `listActualCosts`) : les trois
totaux des lignes retenues et la date du dernier import, tels que le serveur les rend ; les
filtres par périmètre, par sous-projet — celui du contexte de lecture, `subproject_id` — et par
période des pièces, qui n'écrivent que l'adresse, sous les noms du contrat, et ramènent à la
première page ; la grille dense en lecture (`cost-grid.tsx`), sans recherche — l'opération n'en
a pas : une configuration la retire par `searched: false` —, chaque ligne avec son sous-projet
nommé par le serveur, son périmètre en mots et chaque colonne conservée du fichier comme une
colonne, sous le nom que le fichier lui donne, ses valeurs telles qu'importées
(`passthrough.<colonne>`), chaque colonne triée par le serveur — les colonnes conservées sont
celles de toutes les lignes retenues, dans l'ordre où le serveur les nomme
(`meta.passthrough_columns`, #414) : les mêmes d'une page à l'autre — ; et le journal des imports,
paginé à part (`imports_offset`). Quand le projet liste l'exclusion de ses lignes
(`exclude_cost_lines`), le numéro de pièce d'une ligne est un lien hors de la tabulation, que la
grille suit à Entrée, vers la même adresse nommant la ligne (`line`) : sa place dans le périmètre
suivi s'y montre (`CostLineScope`), avec la commande qui l'exclut, sur le motif saisi, ou la
réintègre (`setActualCostTrackedScope`, WF-CRE-0040) ; l'écriture faite, la page relit la ligne et
les trois totaux, que le serveur tient (#291). Des filtres que le serveur refuse (422 : une
période qui finit avant de commencer, un sous-projet que le projet n'a pas) se disent à la place
des lignes, les filtres gardés pour être changés. Un tri ou une recherche changés ramènent toute
liste paginée à sa première page (`sortHref`, `searchHref`). Un lien de page, comme le libellé d'un
risque, part de la dernière adresse demandée
(`usePendingLink`) ; quand elle lit les coûts autrement que la page montrée — un filtre ou un tri
en attente —, il mène à leur première page.

Les écrans du référentiel (`frontend/src/app/reference/`, `frontend/src/components/reference/`,
US-0250) sont hors projet, aux routes de leurs fonctions. Les paramètres de coûts disent la devise
de l'installation et présentent la grille des taux horaires — une configuration de plus de la
grille dense (`rate-grid.tsx`), une ligne par catégorie de main-d'œuvre, son état, une colonne par
année de toute la grille, quelle que soit la page, dont l'en-tête est l'année elle-même
(`GridColumn.heading`) —, cherchée, filtrée par état et sur les bornes du taux d'une année
(`RateFilterBar`, #545), triée et paginée par le serveur sous les noms du contrat (`search`,
`is_active`, `rate_year`, `rate_min`, `rate_max`, `sort_by`, `offset`, #509) : chaque colonne se trie, le taux d'une année par
`rate.<année>`, que la page accepte pour toute année que `Year` prend (`RATE_SORTS`), avant de
connaître celles de la réponse ; sa ligne de totaux dit combien de catégories le serveur retient,
et la devise. Une cellule saisie part seule par `setHourlyRate`, sans version
au premier taux d'une année, avec celle du taux lu pour une correction, et le taux répondu prend sa
place. La saisie n'est offerte qu'à une session qui porte `cost_settings.write` (`platformOffer`),
comme l'ajout de la colonne d'une année que la grille n'a pas (WF-REF-0060, #299) : le contrat n'a
aucune opération pour la créer — une année entre dans la grille par son premier taux —, si bien
que la colonne est celle de la grille, vide, à sa place parmi les années, jusqu'à ce que la
saisie d'une de ses cellules écrive ce premier taux, et elle se retire tant qu'aucun taux n'y est
saisi ni en cours d'écriture ; une année déjà présente, ou hors des bornes de `Year`, est refusée
dans la page ; la colonne ajoutée se trie comme les autres, le serveur laissant l'ordre du code
pour une année sans taux. À côté, les natures et les catégories de coût, deux grilles denses
(`cost-grids.tsx`, #510), triées sur chaque colonne, cherchées, filtrées — les natures par type
(`kinds`, `ValuesFilter`) et par état, les catégories par nature, offerte parmi toutes celles que la
session lit, et par état — et paginées par le serveur — l'écran ne
remplit la fenêtre qu'à partir de la grande largeur (`Screen`, `fillWide`) : en fenêtre étroite, la
grille et les listes s'empilent et la page défile. Les paramètres de ressources présentent trois
grilles denses (#301, #511, #533) : l'organisation, une grille arborescente qui ne se trie pas et
ne se pagine pas, dans l'ordre de `listOrgNodes`, chaque nœud par son libellé décalé de sa
profondeur (`level`), qui plie ce qui est sous lui comme les grilles de tâches (`GridTree.parent`,
`fold.tsx`), son code et son niveau, filtrée par code (`code`), par niveau (`level`, offert parmi
ceux de l'arbre entier) et par état, le serveur rendant les nœuds retenus et leurs ancêtres, qu'un
filtre déplie une fois ; les rôles, triés par le serveur sur chacune de leurs colonnes, filtrés par
nœud (`org_node_id`, offert dans l'ordre de l'arbre entier), par catégorie (`cost_category_id`), par
calendrier (`calendar_id`) — chacun offert parmi tous ceux que la session lit, lus comme une liste
de choix (#303), les catégories absentes quand l'API les refuse — et par état, et paginés ; les
calendriers, triés sur chacune de leurs colonnes, les heures de chaque jour comprises, filtrés par
état et paginés. Les colonnes de nombres se bornent (#545, WF-IHM-0130) : les heures mensuelles et
l'effectif d'un rôle, les heures de chaque jour d'un calendrier, le taux d'une année de la grille des
taux — l'année choisie parmi celles de la grille, écrite avec ses bornes (`rate_year`) —, sous la
convention du contrat pour toute liste, `<colonne>_min` et `<colonne>_max`, incluses
(`docs/api/DECISIONS.md`). Le filtre est un composant de la grille, réutilisable pour les montants
des lots suivants (`RangeFilter` de `components/grid/range-filter.tsx`, `boundsHref` et
`readBounds` de `filters.ts`) : un formulaire par liste, chaque borne saisie comme la langue écrit un
nombre (`parseDecimal`) et écrite comme le contrat l'écrit, ramenant la liste à sa première page ;
une saisie qui n'est pas un nombre, ou un montant de plus de deux décimales, se dit à son champ, qui
prend le focus, sans rien demander. Le serveur seul juge les bornes : celle qu'il refuse (422) — pas
un nombre de son type (`NUMBER_INVALID`), une borne supérieure sous l'inférieure, qu'il nomme
(`VALUE_OUT_OF_RANGE`), l'année du taux manquante (`VALUE_REQUIRED`) — se dit à son champ, qui prend
le focus (`refusedBounds`, `refusedSides`), et la liste n'est pas lue (`shownPage` d'`address.ts`,
`BoundsRefused`) ; le reste de l'écran l'est. Chaque champ se nomme par sa colonne et son côté, tous
deux écrits à côté de lui (« Heures par mois, min. », WCAG 2.5.3). L'arbre se borne aussi sur la
profondeur (`level_min`, `level_max`), à côté du choix d'une profondeur (`level`) ; le taux ne se
borne qu'avec une année que le contrat prend, sans quoi la page ne présente pas sa borne. Chacune des grilles du référentiel
est cherchée par le serveur, a sa clé de préférences, où son tri se garde, et écrit son tri, sa
recherche, ses filtres et sa page dans l'adresse sous ses propres noms, ceux du contrat après son
préfixe (`org_`, `role_`, `calendar_`, `type_`, `category_` : `role_search`, `role_sort_by`,
`role_cost_category_id`, `role_is_active`, `role_offset` ; `prefixedAddress` de `query.ts`,
`GridConfig.address`) — la grille des taux, celle de la fonction, garde les noms du contrat — : les
grilles d'un même écran ne se lisent pas l'une l'autre, et la page demande l'API sous les noms du
contrat ; l'arbre entier est relu quand une recherche ou un filtre le restreint, pour les filtres
des rôles. Un tri, une recherche ou un filtre ramènent leur liste à sa première page ; un lien de
page part de la dernière adresse demandée, et mène à la première page quand elle lit la liste
autrement que celle montrée — le tri d'une autre liste de l'écran n'y comptant pas (`ListPages` de
`components/grid/list-pages.tsx`, nommé d'après sa liste, la seule règle de « même liste » de
`readingOf`) ; la ligne des totaux dit combien le serveur en retient (`meta.total`). Les
unités de durée suivent. Les paramètres des risques présentent les bornes de la matrice et la zone
de chaque case, placée par son rang dans l'ordre du contrat, ceux des indicateurs les seuils des
indices et le délai entre deux revues : des matrices de taille fixe, qui restent des tables
simples, sans tri ni filtre (décision de l'auteur du 2026-10-08, #508). Un objet rattaché se nomme
par le libellé que le serveur résout à la lecture, actif ou désactivé — jamais en rapprochant des
listes dans le front ; une section se nomme par `aria-label` (#251).

Les listes du référentiel ne lisent que les objets actifs, et les désactivés aussi quand l'adresse
le demande (`include_inactive`, WF-REF-0150, #300), sous le nom du contrat, que l'en-tête de
l'écran écrit ou lève par un lien (`InactiveSwitch`), qui ramène chaque liste paginée à sa première
page — à une session seulement qui porte la permission de lecture de leur partie du référentiel,
sans laquelle le contrat le refuse (403, `inactiveQuery` d'`address.ts`), comme les listes du devis
(#351). Le filtre par état (`is_active`, `StateFilter`) prime sur lui : tous les états, les actifs
seuls, ou les désactivés seuls, offert à la même session seulement (`stateOf`). Un objet désactivé
s'y dit par une marque et un mot, et s'y réactive comme le serveur liste sa commande
(`available_commands`, #532, WF-IHM-0090) — le serveur ne la liste qu'à qui peut modifier cette
partie, et le front n'en déduit rien : disponible, par la commande d'activation de sa nature
(`setActivation`, une action serveur, depuis la version lue), puis la page relit ses listes ;
indisponible — un nœud sous un parent désactivé, un rôle sous un nœud désactivé (WF-REF-0080) —,
présentée `aria-disabled`, décrite par ses conditions, et un appui les dit dans la région de la
liste sans rien demander, comme la suppression d'un rôle porté (#515) ; absente, rien. Un objet ne
porte que la commande qui change son état, `deactivate` sur un objet actif, `reactivate` sur un
désactivé, l'une et l'autre par la même cellule (`StateCell` de `commands.tsx`, EP-02/L43,
ci-dessous) ; la désactivation du calendrier par défaut est indisponible (WF-REF-0120). Le refus du serveur — le conflit (409), qui nomme le nœud à réactiver d'abord
d'après la ligne qui le connaît, ou la version périmée (412), avec l'offre de relire — se dit
au-dessus de la liste (`Reactivations`), qu'une cellule de grille n'a pas la place de dire, jusqu'à
ce qu'on ferme son avis — un refus arrivé pendant qu'un autre est dit s'ajoute à lui, sans le
remplacer, sauf celui de la même commande sur le même objet, qui prend sa place ; un succès après lui
ne l'efface pas, et le focus revient à la cellule active
de la grille, ou à la liste —, et seulement tant que la liste se lit comme au moment de la commande :
les paramètres qu'elle lit (`listReads`), le tri d'une autre liste de l'écran n'y comptant pas. Dans
une grille, la commande est hors de la tabulation, et Entrée sur sa cellule la presse
(`CELL_COMMAND`, `grid-keyboard.ts`). Le faux back ignorant les filtres, les pages et
`include_inactive`, et ne gardant rien, les tests éprouvent ce que l'écran demande ; le service le
tiendra en EP-05.

Les paramètres de coûts offrent les commandes d'écriture des natures et des catégories (EP-02/L43a,
décision de l'auteur du 2026-10-08, #512 ; `commands.tsx`, `reference-form.tsx`, `cost-form.tsx`),
pour projeter la mise en page et éprouver le contrat de chaque écriture ; ceux des ressources les
leurs (EP-02/L43b, plus bas), par les mêmes pièces. À une session qui porte `cost_settings.write`
(`platformOffer`), chaque liste offre « Nouvelle nature » ou « Nouvelle catégorie » à côté de son
titre — liste vide comprise —, et chaque ligne « Modifier », dans une colonne à elle ; l'état de la
ligne porte la désactivation ou la réactivation comme l'objet la liste (`available_commands`,
`StateCell`), et la présente indisponible avec ses conditions quand elle l'est — la dernière
nature de type provision pour risques et sa dernière catégorie se désactivent comme les autres
depuis EP-14/L42p, qui retire la règle de #578 ; aucune commande ne supprime (WF-REF-0010,
WF-DAT-0080). Une autre session n'en voit aucune. La création et la modification ouvrent un
dialogue (`ReferenceForm`, `ui/dialog.tsx`), que chaque liste rend par celui
de sa nature (`CostDialog`, `useListForm`) : le code, le libellé et le type
d'une nature, choisi parmi les trois du contrat ; le code, le libellé, la nature — parmi les actives,
et celle de la catégorie modifiée, marquée désactivée — et le code comptable d'une catégorie, exigé,
d'un à vingt caractères (WF-REF-0040, décision de l'auteur du 2026-10-09). Ce qu'une modification
change suit les commandes de l'objet (EP-02/L42g, WF-IHM-0090) : le type d'une nature n'est offert
que si elle liste `change_kind` disponible, et se présente sinon figé, en lecture seule
(`control: "fixed"` d'un `FormField`), ses conditions dites sous lui (`note`) — une catégorie
employée (`cost_type_unused`) —, la description du dialogue le disant aussi ; une catégorie ne se
voit proposer une nature d'un autre type que si elle liste `change_cost_type` disponible, et sinon
les natures de son type seules, ses conditions dites sous le choix — employée, porteuse de taux
(#577). Le type se compare par le `kind` de chaque nature, désactivées comprises : pour une session
qui écrit, la page lit toutes les natures avec `include_inactive=true` (`every` de `CostDialog`),
une lecture entière distincte des choix du filtre, qu'elle ne fait pas quand ceux-ci comprennent déjà
les désactivées ; une catégorie sous une nature désactivée se voit ainsi proposer les natures
actives de son type, et sa nature désactivée se nomme par son code, que cette lecture donne. Une
nature qu'aucune lecture ne donne — une session qui écrit sans pouvoir lire les désactivées, à qui
le contrat refuserait `include_inactive` (403), et pour qui la page ne la demande pas — laisse à la
catégorie sa seule nature, et la note le dit à part (« Le type de la nature désactivée n'est pas
lisible : seule elle est proposée. »). `costs/page.test.tsx` éprouve ce que la page passe au
formulaire, les natures servies par `cost_types_with_inactive`, la lecture avec les désactivées, qui
ne vaut que pour elle.
Un nœud dont le code est pris est nommé de même, d'après l'arbre ou la liste, sinon par le libellé que
le refus donne (`OrgNodeDialog`). Le
formulaire refuse à son champ ce qui manque, ou un nombre qui n'en est pas un dans la langue du
lecteur (`parseDecimal`), avant toute demande, et le champ prend le focus ; le
serveur juge le reste : un refus par champ (422, `fields[]`, convention #293) se dit au champ qu'il
désigne, par la phrase de son code et de ses paramètres — `problemMessage` d'un `FieldProblem`, le
premier champ refusé prenant le focus —, comme une valeur déjà portée (409 `ALREADY_EXISTS`,
`fields[]`), qui nomme l'objet qui la porte (`fields[].params.conflicting_object_id`) par son code et
son libellé quand la liste le montre (`names` de `ReferenceForm`), de façon générique sinon ; le
décodeur en tire aussi l'objet du refus (`conflictingObjectId`) quand l'enveloppe n'en nomme pas.
Tout autre refus se dit sous le formulaire (`OutcomeNotice`), qui reste ouvert — un état qui interdit
l'écriture (409 `STATE_FORBIDS_OPERATION`) avec sa condition, la version périmée (412) avec l'offre
de relire la page ; un refus par champ que le formulaire ne montre pas y reste seul, sans répéter ce
qui est dit aux champs. Le bouton d'envoi dit
l'écriture en cours ; fermé pendant l'attente, le dialogue ne fait rien taire : le succès se dit dans
la région de la liste, le refus au-dessus d'elle, sur la lecture d'où il est parti. Fermé, il rend le
focus à la cellule de la ligne — la grille est un seul arrêt — ou à la commande de création.
`problemMessage` lit aussi les
paramètres des refus par champ d'une enveloppe : le minimum d'un taux refusé se dit avec le refus de
la cellule, écrit dans la langue du lecteur (« Valeur minimale : 0,01. »). Toute écriture répondue
relit la page (`refresh`) : les natures sont ce par quoi les catégories se filtrent et se rattachent,
les catégories de main-d'œuvre les lignes de la grille des taux, et un choix qui offrirait encore une
nature désactivée serait une commande que le serveur refuserait (WF-REF-0010) ; une écriture change
aussi les commandes d'autres objets — le rattachement d'une catégorie le type de l'ancienne et de
la nouvelle nature (#577) —, que sa réponse ne porte pas. Un taux ne relit la page qu'à sa première
saisie : la catégorie qui porte des taux ne se rattache plus à une nature d'un autre type
(`cost_category_unrated`) ; une première saisie refusée comme un second taux de l'année (409
`ALREADY_EXISTS`) relit aussi la page, et la cellule montre le taux de l'année avec sa version, que la
saisie suivante corrige ; une correction ne change aucune commande. Cette relecture, à la
même adresse, n'abandonne rien de la grille des taux : un taux parti avant elle reste en attente, le
refus dit le reste, et un taux répondu, avant ou après elle, garde sa cellule tant qu'il est plus
récent que la cellule relue, par le `lock_version` du taux — la réponse est le changement d'une
cellule, trouvée par son année parmi celles de la ligne relue et reposée sur elle
(`RowPart.versioned`, `rate-cells.ts`), une ligne de la grille n'ayant pas de compteur à elle ;
ailleurs, une réponse se juge en bloc par le compteur de ce qu'elle a écrit (`GridConfig.fresher`,
le `lock_version` d'un nœud) : plus récente que la relecture, elle garde tout ce qu'elle a rendu, les
récapitulatives recalculées et les totaux compris, une réponse plus récente l'emportant toujours sur
une plus ancienne pour une même ligne ; rattrapée, elle cède tout ; là où le compteur ne dit rien —
même version, ligne sans compteur, faux back —, chaque valeur reste tant que la relecture lit sa ligne,
ou ses totaux, comme avant. Seule une lecture à une autre adresse — un tri, une recherche, un filtre,
une page de la grille — abandonne les réponses en cours ; une lecture qui rend les mêmes lignes dans
le même ordre, une autre liste de l'écran triée ou l'adresse réécrite par `history.replaceState`, est
la même (`cell-writes.ts`, défaut n° 22). Cette dernière règle suppose que le contenu d'une ligne ne
dépend pas de l'adresse : le jour où une grille calcule ses lignes d'après un paramètre de l'adresse
— une devise, une date de valeur —, deux lectures aux mêmes lignes ne sont plus la même, et la règle
devient fausse. Une modification ou
une activation répondue remplace sa ligne par ce que le serveur rend, tant que la réponse est plus
récente que la ligne lue (`lock_version`, `useAnswered`) — face au faux back, qui ne garde rien, elle
survit donc aux relectures — ; une création n'ajoute aucune ligne, la page relue la range où le
serveur la retient. Ce qu'une écriture a fait se dit dans la région de sa liste (« « Débours »
désactivée. ») ; le refus d'une activation, au-dessus de la liste comme celui d'une réactivation
(`useListReport`). Le faux back ne gardant rien, l'écran le dit
sous son en-tête, pour qui écrit — une ligne écrite restant montrée telle que le serveur l'a rendue
tant que l'écran reste ouvert — (`MockupNotice`, `components/shell/mockup-notice.tsx`, à reprendre
par chaque écran de la maquette dont les commandes écrivent, retiré quand l'écran est branché sur le
service de son EPIC). La saisie d'un taux reste celle de la grille.

Les paramètres de ressources offrent de même les commandes de l'organisation, des rôles et des
calendriers (EP-02/L43b, #512 ; `resource-commands.tsx`, `calendar-default.tsx`), à une session qui
porte `resource_settings.write` : « Nouveau nœud », « Nouveau rôle », « Nouveau calendrier », la
modification de chaque ligne, la désactivation ou la réactivation comme l'objet la liste — un nœud
avec ses descendants, que la réponse remplace dans l'arbre (WF-REF-0080), les rôles qu'elle désactive
avec lui étant ceux de l'autre liste, que la page relue montre. Un nœud s'écrit par son code, son
libellé et son parent — nul pour une racine, envoyé à la modification comme à la création (`OrgNodeUpdate`) —, choisi dans l'ordre de l'arbre, chaque nœud
décalé de sa profondeur (`treeLabel`) : parmi les nœuds actifs seuls, que le nœud soit actif ou
désactivé (WF-REF-0070, EP-14/L43g), jamais sous lui-même ni sous l'un de ses descendants, qu'il
emmène ; son parent est toujours offert, d'après `parent_id` et `parent_label`, marqué désactivé quand
il l'est, et la liste le montre choisi — le contrat ne refuse un parent désactivé que si la
modification le change ; désactivé, il garde sa profondeur
quand le nœud au-dessus de lui est offert, ou qu'il est une racine, et alors sa place — dans l'arbre
lu, le front ne réordonnant rien, ou sous son propre parent quand la ligne de la liste le nomme — ; à
la fin sans décalage sinon. Un rôle s'écrit par son
libellé, son nœud, une catégorie de main-d'œuvre et son calendrier — parmi les actifs, celui du rôle
modifié marqué désactivé (WF-REF-0090), nommé sans marque quand la liste n'est pas lue, faute de savoir
s'il l'est — et sa
capacité, heures par mois et effectif, saisis dans la langue du lecteur (WF-REF-0100) ; son nœud se
fixe à la création, et sa modification le nomme sans l'offrir : un rôle se recrée sous un autre nœud
(§3.4.4.2.1). La catégorie de main-d'œuvre se reconnaît au type de sa nature, que chaque catégorie dit
(`cost_type_kind`, `labourOf` de `kinds.ts`, EP-14/L43g) : la page ne lit pas les natures pour cela.
Une session à qui l'API refuse les catégories ne peut en choisir aucune : « Nouveau
rôle » ne lui est pas offert (WF-IHM-0090), et la modification nomme la catégorie du rôle comme sa ligne
la nomme. La modification d'un objet répondue pour un autre objet est une panne du service
(`INTERNAL_ERROR`), dite sous le formulaire comme la réponse d'une cellule pour une autre ligne. Un
calendrier s'écrit par son libellé
et ses sept valeurs d'heures, du lundi au dimanche, rien d'autre (WF-REF-0110). Un calendrier se désigne
par défaut depuis sa ligne comme il en liste la commande
(`CalendarCommand.set_default`, `setDefaultCalendar`, WF-REF-0120, EP-14/L43g), depuis la version lue,
la page relue montrant le précédent sans la désignation : absente — sur le calendrier par défaut, ou
pour une session qui ne modifie pas —, rien, le front ne déduisant rien de l'état de la ligne ;
indisponible pour un calendrier désactivé, présentée `aria-disabled`, décrite par sa condition
(`calendar_active`), et un appui la dit dans la région de la liste sans rien demander
(`UnavailableCellCommand`) ; le refus du serveur — le calendrier désactivé entre-temps (409), la
version périmée (412), avec l'offre de relire — se dit au-dessus de la liste. Un refus par champ se
dit au champ (`ReferenceForm`) : une référence inconnue (`UNKNOWN_ORG_NODE`, `UNKNOWN_COST_CATEGORY`,
`UNKNOWN_CALENDAR`), un nœud placé sous lui-même ou l'un de ses descendants (`ORG_NODE_CYCLE`), une
catégorie hors main-d'œuvre (`LABOUR_CATEGORY_REQUIRED`), un parent, un nœud ou un rattachement
désactivé entre-temps (`INACTIVE_REFERENCE_OBJECT`), des heures hors de 0 à 24 ou une capacité
négative, avec la borne franchie (`VALUE_OUT_OF_RANGE`) ; le libellé déjà porté d'un calendrier,
désactivés compris, nomme son porteur d'après la page, par son identifiant, de façon générique
sinon ; le reste comme pour les coûts, la version périmée sous le formulaire avec l'offre de relire ;
l'écran dit que le faux back ne garde rien (`MockupNotice`).

Les paramètres des risques et des indicateurs se modifient chacun dans un formulaire (EP-14/L43e,
#512 ; `settings-forms.tsx`), offert par « Modifier la matrice de risques » à une session qui porte
`risk_settings.write`, par « Modifier les seuils et le délai » à une session qui porte
`indicator_settings.write` (`platformOffer`) ; une autre session lit les tables seules, sans avis de
la maquette. L'un saisit les six bornes, en pourcentages (`editablePercent`, `percentRatio`), et les
seize zones, un choix par case ; l'autre les quatre seuils, en valeurs de l'indice, et le délai, en
semaines entières (`control: "whole"`, un nombre entier, signe compris, ses bornes au serveur, jugé
au champ avec les autres, dit par le texte propre au champ, `invalid`). Chaque écran suit sa seule permission : une session qui porte
l'une sans l'autre lit l'autre écran sans commande ni avis. Chacun envoie par `updateReferenceSettings` le seul sous-objet de son écran et la
version lue (`RiskMatrixWrite`, `IndicatorWrite`), jamais un champ de l'autre écran, que garde une
autre permission ; ni la devise (WF-REF-0140) ni la langue de l'installation, qui est à EP-03, n'y
sont offertes. Le formulaire du référentiel range côte à côte, sous une légende, les champs qui vont
ensemble (`group` d'un `FormField`, un `fieldset` qui se replie sur deux colonnes dans une fenêtre
étroite) : les bornes d'un axe, les zones d'un niveau de probabilité, les deux seuils d'un indice,
chaque champ nommé par la légende de son groupe puis par son libellé (`aria-labelledby`), que les
groupes répètent ; et il juge, dans le même envoi que les champs, sur ceux qui sont passés, les règles
qui lient des champs entre eux (`rules`), avant toute demande — un champ refusé n'a pas de valeur,
qu'une règle laisse sans jugement, et son propre refus l'emporte ; tout ce qui est refusé se dit en une
fois (EP-14/L52) — : chaque borne qui n'est pas strictement
au-dessus de la précédente, à son rang (`BOUNDS_NOT_ORDERED`), chaque seuil d'alerte qui n'est pas
sous son seuil de vigilance (`THRESHOLD_NOT_BELOW_WATCH`), dits au champ que le serveur désignerait,
les décimaux comparés sans flottant (`compareDecimals`). Le refus du serveur se dit de même : par
champ au champ, la permission manquante (403) et la version périmée (412, les deux écrans partageant
le compteur) sous le formulaire. La réponse prend la place des paramètres lus tant qu'elle est plus
récente qu'eux, la page relue, comme les paramètres du projet, et ne ferme que le dialogue d'où elle
est partie, jamais un dialogue rouvert depuis ; la commande qui l'ouvre attend, inactive, la réponse
d'une écriture d'un dialogue fermé (#661) ; face au faux back, qui répond par le
premier exemple de l'opération — les seuils écrits —, la matrice montrée reste celle d'avant.

Les écrans de l'administration (`frontend/src/app/admin/`, `frontend/src/app/system/`,
`frontend/src/components/admin/`, US-0250) sont hors projet eux aussi, et en lecture seule : les
comptes, désactivés compris par défaut (`include_inactive`), chacun avec ses rôles et son nœud nommés par le
serveur, sur la grille dense (#514, `admin-grids.tsx`), triés sur chaque colonne, cherchés,
filtrés par origine (`origins`, `ValuesFilter`), par nœud d'organisation (`org_node_id`, offert
dans l'ordre de l'arbre, `OrgNodeFilter`), par rôle d'habilitation (`access_role_ids`, les rôles
que `listAccessRoles` rend, aucun à une session qui ne les lit pas ; tous choisis filtrent encore,
un compte sans rôle n'étant retenu par aucun, `exhaustive: false`, EP-02/L42f) et par état, un
seul choix (`is_active`) — tous, les actifs seuls, les désactivés seuls —, qui dit ce que la grille
montre : la page demande toujours les désactivés aussi (`include_inactive=true`, le contrat les
masquant par défaut), une adresse d'avant qui les masquait (`include_inactive=false`) se lit
« Comptes actifs » (`readAccountState`), et tout choix lève ce paramètre ancien (`lifts` de
`ChoiceFilter`) — et paginés par le serveur, sous les noms du contrat — un tri, une recherche ou un
filtre ramenant à la première page —, la ligne des totaux disant combien le serveur
en retient (`meta.total`), l'écran remplissant la fenêtre ; la recherche porte sur le nom, le
prénom, l'adresse et le nom affiché, sans égard à la casse ni aux accents, comme toute recherche du
contrat. Les rôles d'habilitation sont sur la grille dense eux aussi
(#515), triés sur chaque colonne, cherchés et filtrés par le serveur — leur nature
(`is_predefined`, `ChoiceFilter`), leurs porteurs entre deux bornes incluses (`holder_count_min`,
`holder_count_max`, `RangeFilter` de forme `count`, un entier depuis zéro ; une borne refusée dite
à son champ, la liste non lue) —, sans pagination — le
§4.6.2 ne compte aucun rôle, trois sont prédéfinis, et le contrat ne les pagine pas —, et la matrice
des permissions montre tous les rôles quelle que soit la demande de la grille — une ligne par
permission dans l'ordre du catalogue, les permissions consécutives d'une même fonction de second
niveau, ou d'une même nature hors fonction, groupées sous un en-tête de groupe
(`scope="rowgroup"`) qui nomme la fonction — jamais par son code de la FBS, une clé interne
qu'aucun écran ne montre (décision de l'auteur du 2026-10-08, #515) —, une colonne par rôle,
accordée ou non dite par un mot ; l'état du système ; les sauvegardes et leur planification, dont
les commandes sont branchées au contrat (EP-02/L43c, plus bas). Seule exception aux écrans en lecture
de ce paragraphe, décidée par l'auteur le 2026-10-08 (#379, #515) : des boutons
seuls, posés avant qu'EP-03 ne les branche (`later-commands.tsx`). À une session qui porte
`users.write` (`platformOffer`), l'écran des comptes offre « Créer un compte local » dans son
en-tête et, sur chaque compte, « Modifier », « Désactiver » ou « Réactiver » selon son état, et
« Attribuer les rôles » tels que le compte les liste (`User.available_commands`) — une commande
absente n'est pas présentée, une indisponible l'est avec sa condition — ; aucune suppression
(WF-ADM-0060) ; à une session qui porte
`access_roles.write`, l'écran des rôles offre « Créer un rôle » et, sur chaque rôle, « Modifier »
et « Supprimer » — une suppression logique (#456) —, indisponible, `aria-disabled` et décrite par
sa condition, tant qu'un compte porte le rôle, comme le serveur la refuserait (`deleteAccessRole`,
409, WF-ADM-0090), et la désactivation du dernier compte actif qui porte les permissions de
modifier les comptes et les rôles, `last_administrator` manquante (WF-ADM-0120, #540) — le front ne
pourrait pas le trouver seul, la liste étant paginée ; l'attribution de ses rôles reste disponible,
le serveur jugeant les rôles envoyés, et refusant par `LAST_ADMINISTRATOR` ceux qui lui retireraient
ces permissions — un refus dit comme tout autre. Un
clic sur une commande disponible dit, dans une région annoncée rendue dès le départ, hors de la
section de la liste, qu'elle est disponible avec EP-03 ; sur une commande indisponible, la
condition qui lui manque, sans la lancer — chaque clic, le même répété aussi ; sans la permission,
aucun bouton. Une liste que le serveur pagine — comptes, sauvegardes — dit combien elle en porte et
mène aux pages voisines par `offset` (`ListPages`, pour les comptes comme pour
les sauvegardes), les autres paramètres de l'adresse gardés, sans jamais montrer une page pour le tout ;
elle ne se dit vide que si elle ne tient rien (`meta.total`) et que rien ne la restreint, et une page demandée au-delà de sa fin le dit et ramène à la dernière — une seule
règle pour toutes les listes paginées, `pageOffsets` de `frontend/src/navigation/pages.ts` (#317).
L'heure d'une sauvegarde planifiée s'affiche telle quelle, en UTC, comme le contrat la donne : une
heure du jour n'a pas de date d'où tirer le décalage d'un fuseau à heure d'été. Son formulaire la
saisit de même, et dit à côté l'heure du poste qu'elle donne la semaine où il est ouvert — l'heure seule
pour une planification quotidienne, le jour local aussi pour une hebdomadaire, qui peut être la veille
ou le lendemain du jour universel (`localTimeOfDay` de `format.ts`, dans le navigateur) : rien n'est
converti à l'envoi.

L'écran des sauvegardes (FBS-1.4, `/admin/backups`, EP-02/L43c, #519, EP-14/L43f, EP-14/L43d)
présente leur planification (`backup-schedule.tsx`) et une page de leur liste sur la
grille dense (`backup-columns.tsx`, `backup-grid.tsx`, préférences sous la clé `backups`) : la date,
en heure locale, la taille, la vérification, le déclenchement et la conservation, dans l'ordre du
serveur, la ligne des totaux disant combien il en retient (`meta.total`). Le serveur trie chaque
colonne dans les deux sens (WF-IHM-0060), les plus récentes d'abord quand l'adresse et le compte ne
disent rien, et le tri ne se lève jamais, comme celui du journal ; il filtre sur chaque colonne
(WF-IHM-0130, `backup-address.ts`), sous les noms du contrat : la période de la prise, deux jours du
lecteur tirés en instants, `from` compris et `to` exclu, comme l'accueil (`PeriodFilter`, `day`) ;
le déclenchement et la vérification, par leurs valeurs (`origins`, `verifications`,
`ValuesFilter`) ; la conservation, par un choix (`is_retained`, `ChoiceFilter`) ; la taille, par ses
deux bornes en octets, incluses (`size_bytes_min`, `size_bytes_max`, `RangeFilter`, sorte `bytes` :
un entier qui a plus de chiffres qu'un compte). Une liste filtrée ne se dit jamais vide, et une
borne que le serveur refuse (422) — une fin avant le début, un maximum sous le minimum — laisse la
liste non lue, les filtres gardés, la borne dite à son champ. « Sauvegarder maintenant », dans la
tête de la liste, liste vide comprise — une tâche de fond remise au suivi avec sa commande —, suit
la permission `backups.write` (WF-ADM-0100, `platformOffer`) ; les autres commandes sont celles que
chaque sauvegarde liste (`Backup.available_commands`, WF-IHM-0090, `backup-commands.tsx`), le front
n'en déduisant rien de la session ni de l'état de la sauvegarde : « Conserver » ou « Ne plus
conserver », celle des deux qui change son marquage, dans la colonne de la conservation ;
« Télécharger » et « Restaurer », chacune dans sa colonne dès qu'une sauvegarde de la page la
liste — le serveur ne liste le marquage que sous `backups.write`, le téléchargement et la
restauration que sous `platform_restore` (décision de l'auteur du 2026-10-09, #588) —, et aucune ne
supprime. Une commande absente n'est pas présentée ; une indisponible l'est, `aria-disabled` et
décrite par la condition qui lui manque (`enums.CommandCondition`) — `backup_verified` au
téléchargement et à la restauration d'une sauvegarde non vérifiée, `no_backup_running` à la
restauration pendant qu'une sauvegarde court, `no_restore_running` au marquage et à la restauration
pendant qu'une restauration court —, et un clic la dit dans la tête de la liste sans rien demander,
comme les activations du référentiel. La tête de la liste dit ce que la dernière commande a fait dès
qu'une commande est offerte. Une sauvegarde n'ayant pas de compteur, la réponse d'un marquage reste
montrée tant que chaque relecture lit la sauvegarde comme la précédente ; une relecture qui l'a
changée l'emporte pour de bon, et une démarque par un tiers que la relecture ne montre pas reste
invisible (#588). Le téléchargement est un lien vers la route `/admin/backups/[backupId]/content`,
qui relaie `downloadBackup` en flux comme le résultat d'une tâche (`src/api/relay.ts`, commun aux
deux routes) : des octets, seul type que le contrat déclare, sous le nom que l'API donne
(`Content-Disposition`, que le contrat exige : `waterfall-backup-`, l'instant de la sauvegarde et
l'extension de son archive), avec sa longueur quand le corps arrive sans `Content-Encoding` — tout
autre type, ou un fichier sans nom, renvoie l'erreur d'une mauvaise passerelle (502). Un refus —
403, 404 sans distinction (WF-ADM-0110), 409 d'une sauvegarde non vérifiée, 502, l'API
injoignable — renvoie à l'écran des sauvegardes, sa page et ses filtres gardés, l'adresse nommant la
sauvegarde et le refus (`refused_backup`, `refusal`, les noms paramétrés de `result-refusal.ts`) :
l'écran le dit au-dessus de la liste jusqu'à ce qu'on ferme son avis — le téléchargement nommé, la
sauvegarde par sa date quand la page la porte —, et l'avis, rendu avec la page, prend le focus au
montage, sans quoi aucun lecteur d'écran ne l'annoncerait ; l'adresse est rendue sans le refus une
fois la page révélée (`afterReveal`), l'avis fermé ou non. « Restaurer » ouvre un dialogue
(`restore-dialog.tsx`) qui énonce la date de la sauvegarde et sa vérification, la perte sans retour
de ce qui a été saisi depuis, la déconnexion des utilisateurs et l'inscription au journal d'audit
(WF-ADM-0160, WF-SEC-0030) ; le bouton ne s'active qu'une fois l'identifiant de la sauvegarde
saisi, sans égard à la casse, et la demande énonce la date dite (`acknowledged_backup_taken_at`).
Pendant la demande, ni Échap, ni un clic au-dehors, ni « Annuler » ne ferment le dialogue : un
refus s'y dit — un état qui l'interdit (409), la condition nommée comme tout refus ; une date
confirmée qui n'est pas celle de la sauvegarde (422, `BACKUP_DATE_MISMATCH` sur
`/acknowledged_backup_taken_at`), dite à la date que le dialogue énonce, la liste lue n'étant plus
celle de la sauvegarde, et la page relue —, et rien ne part qu'on croie abandonné. La tâche va au
suivi sans sa commande : une restauration ne se relance que depuis cette confirmation. Le refus
d'une commande de la liste se dit au-dessus d'elle (`Reactivations`), la condition nommée pour un
409 ; l'écran dit que le faux back ne garde rien (`MockupNotice`) dès qu'une commande est offerte.
La restauration depuis un fichier attend #350 (EP-03).

La planification se modifie, à une session qui porte `backups.write` (`platformOffer`), dans le
formulaire du référentiel (`ReferenceForm`), qui la renvoie **entière** depuis la version où il s'est
ouvert (`setBackupSchedule` est un `PUT`) : activée ou suspendue, la fréquence et l'heure en UTC (un
champ `time` : une heure à moitié saisie, que son champ rend vide, `validity.badInput`, est refusée
avant tout appel par la phrase propre à son champ, `invalid`, jamais envoyée comme « aucune heure ») —
exigées d'une planification activée seulement, le contrat ne les exigeant pas d'une
suspendue —, le jour — exigé d'une planification hebdomadaire, nul d'une quotidienne —, le nombre de
sauvegardes conservées, un nombre entier dont le serveur juge les bornes, signe compris ; un champ
exigé selon le brouillon le dit (`required` d'un `FormField`, une fonction du brouillon, qui donne
aussi `aria-required`, #678) ; puis la copie externe, offerte quand l'installation déclare un emplacement
ou que la planification en règle une : l'emplacement, choisi parmi ceux que la page lit pour cette
seule session (`listExternalBackupLocations`) par son nom et sa nature, sa description sous le champ,
jamais un secret ni une adresse — un emplacement réglé que l'installation ne déclare plus reste offert
par son nom, refusé au champ avant l'envoi (`UNKNOWN_EXTERNAL_BACKUP_LOCATION`) plutôt que retiré en
silence —, « Aucune copie » la retirant ; le dossier
relatif ; le nombre de copies, au moins celui des sauvegardes conservées (WF-EXP-0050), vérifié avant
l'envoi et dit au champ avec ce minimum, comme le serveur le dirait — pour une rétention dans ses
bornes, de 1 à 365 (`RETENTION`), le reste revenant au serveur, qui donne alors le minimum des
copies à 1 — ; la copie active ou suspendue.
Les règles entre champs passent par `rules` du formulaire, une note qui suit la saisie par une
fonction du brouillon (`note`), et ce qui suit les champs sans en être un par `after` : « Tester
l'emplacement » (`testExternalBackupLocation`), offert pour un emplacement que l'installation
déclare, qui dit l'emplacement éprouvé, l'instant du test en
heure locale, le dossier ou la racine, et la réussite ou le motif de l'échec
(`enums.ExternalBackupFailure`) dans une région annoncée ; un dossier refusé (422, `/path`) se dit sous
le bouton par la phrase de son propre code ; seule la réponse du dernier test demandé est dite, tant
que le dossier saisi est celui qu'il a éprouvé, et un autre emplacement choisi fait tomber le test en
route. La réponse d'un enregistrement remplace la planification affichée tant que son `lock_version`
est plus récent que la lecture, la page relue, et ne ferme que le dialogue ouvert d'où elle est partie
(compteur d'ouvertures, comme les paramètres du référentiel), la commande attendant, inactive, la
réponse d'une écriture d'un dialogue fermé (#661, #678) ; un refus par champ (422 : emplacement inconnu, chemin
invalide, rétention trop courte) se dit au champ, tout autre sous le formulaire, la version périmée
(412) avec l'offre de relire.

Le journal d'audit (FBS-1.5, WF-SEC-0030, `/admin/audit-log`, `frontend/src/components/audit/`,
#517) est un écran de l'administration à lui ; la table « Dernières opérations » de l'état du
système, trois faits de la plateforme (WF-ADM-0130), reste telle quelle. C'est une fonction en
lecture seule, qui n'a que sa permission de consulter (WF-ADM-0100) : `FunctionPermission` nomme
toute fonction par sa permission de consulter, et `WritableFunction` celles qui ont aussi la
permission de modifier, seules que `platformOffer` accepte. L'écran est gardé par `audit_log.read`,
introuvable sans elle comme une adresse qui ne mène nulle part (WF-ADM-0110). Il présente une page
des inscriptions de `listAuditEvents` sur la grille dense, en lecture seule (`audit-columns.tsx`,
préférences sous la clé `audit_log`) : la date, en heure locale, l'auteur, l'action, la nature et
le libellé de l'objet — une sauvegarde, qui n'en a pas, par sa nature, jamais par son
identifiant —, le projet et la corrélation, chacun tel que l'inscription le garde, et un lien vers
l'histoire de l'objet — le journal filtré sur sa nature et son identifiant, toute son histoire :
les autres filtres et la recherche levés, le tri gardé —, la corrélation menant de même aux
inscriptions de sa seule requête. Le serveur trie sur chaque colonne (#550), dans les deux sens.
Les plus récentes d'abord quand l'adresse ne dit rien, et le tri ne se lève jamais
(`GridConfig.lifts`) : l'en-tête de la date demande d'abord le décroissant
(`GridColumn.descendingFirst`), et ramène ainsi, depuis un autre tri, à l'ordre par défaut. Un objet
ne mène à son écran propre que si la session lit sa fonction — les risques, le planning dont les
échanges sont une feuille, les révisions —, sinon à sa révision, qui mène à la première fonction
lisible, et à rien sans fonction de révision à lire (`auditReach`). La corrélation saisie ne part
que sous la forme que le contrat accepte (`pattern` du champ, que le navigateur dit). La recherche de la grille
porte sur le libellé de l'objet (`search`). Les filtres
n'écrivent que l'adresse, sous les noms du contrat, et ramènent à la première page
(`audit-filters.tsx`) : la période, deux instants saisis en heure locale et envoyés en temps
universel — seul le navigateur connaît son fuseau, si bien que les champs montrent ceux de
l'adresse une fois la page hydratée ; une borne laissée telle quelle repart comme l'adresse la nomme,
et une saisie est datée par la période de l'adresse, le formulaire jamais remonté —, la nature de
l'auteur (`ValuesFilter`), l'auteur et le projet parmi ceux que nomme le journal entier
(`listAuditFacets`, que la seule consultation du journal lit : un auditeur sans `users.read` filtre
par auteur) — sans auteur à choisir ni auteur choisi, le filtre d'auteur n'est pas offert —, les
actions dans un menu, la nature de l'objet, l'objet dont l'adresse demande l'histoire, nommé et
levé, et la corrélation, saisie (`TextFilter`) ; un auteur ou un projet que l'adresse nomme sans
qu'aucun choix ne l'offre reste choisi sous le nom que les inscriptions lui donnent. Le projet et
l'objet sont des liens là où la session peut les consulter — un projet qu'elle peut ouvrir
(`listProjects`, tous états) — : le projet, une révision d'un tel projet, et un objet qui vit dans
une révision, vers son écran propre dans celle que l'inscription nomme (`AuditObject.revision`) —
un risque vers les risques de la révision, son détail ouvert (`risk`), l'import d'un planning, d'un
devis ou d'un reste à engager vers ses échanges, son compte rendu montré (`import`), le
différentiel d'un avenant vers les structures de coûts de l'écran des révisions lu dans elle
(`revision_id`) ; une ligne de coût réel et
l'import des coûts réels ne vivent dans aucune révision, et un compte, un rôle ou une sauvegarde
n'ont pas d'écran à eux : leur nom reste seul. Une période que l'API refuse (422, la fin désignée hors
de ses bornes) se dit à la place des inscriptions, les filtres gardés, et tout autre refus des filtres
par son enveloppe (`problemMessage`) ; aucune commande n'est offerte.

L'écran des imports et exports, `…/revisions/[r]/exchanges` (`frontend/src/components/exchanges/`,
US-0260), est la feuille FBS-4.3.4 du planning, dont l'en-tête y mène dans le même contexte, comme
celui de l'écran des coûts réels ; un
import s'applique pourtant à la révision en cours, créée au besoin (WF-INTF-0090), quelle que soit
la révision lue. Un import se fait en deux temps (WF-ARC-0100) : la commande de sa nature ouvre dans
la page le choix du fichier — et, pour une extraction de coûts réels, la période qu'elle couvre —,
qu'une action serveur dépose pour un import (`uploadFile`, `purpose: import`) puis analyse
(`openImport`) ; un fichier de plus de 10 Mio, la borne que le contrat donne au dépôt d'un import,
est refusé dans la page, et la borne des actions serveur de Next est réglée un peu au-dessus
(`next.config.ts`). La tâche de l'analyse va au
suivi de la coquille, et l'adresse nomme l'import (`import`, un identifiant ou rien), dont la page lit
le compte rendu (`getImport`) — lignes lues, motifs de confirmation, lignes rejetées par leur place
et leur motif, rendu comme un refus depuis son code et ses paramètres (`problemMessage`), écarts
avec les champs qu'ils changent, nommés par le catalogue de leurs colonnes (`NodeColumn`,
`ActualCostColumn`) —,
dans l'ordre reçu. Les commandes d'un compte rendu sont les siennes : un autre import montré les
remplace. L'application n'est offerte qu'à un import analysé, et ne part qu'une fois confirmée dans
la page ; sa tâche va au suivi. L'abandon ramène à l'adresse de départ, si l'écran montre encore cet
import. Chaque import est offert comme le projet offre sa commande (`importOffers`) :
`import_planning`, `import_estimate`, `import_remaining`, `import_actual_costs`, avec ou sans
révision en cours — sans elle, qui ne peut pas créer la révision voit l'import indisponible,
`may_create_revision` nommée. Un projet sans révision, qu'aucune adresse de révision n'atteint,
offre les mêmes imports sur son propre écran (`ImportPart`), et y montre le compte rendu de l'import
que son adresse nomme (#332). L'écran est gardé par les commandes qu'il exerce, et non par la seule
lecture du planning (#521) : il se montre à une session qui lit le planning, dont il est la feuille,
ou à laquelle le projet liste un import (`listsAnImport`) — un chiffreur, que le devis et le reste à
engager y mènent quand le projet liste leur import, disponible ou non, l'écran le présentant alors
avec ses conditions (`ExchangesLink`, WF-IHM-0090) ; il est introuvable pour tout autre. La liste des imports, paginée par le serveur (`offset`,
`ListPages` de `components/grid/list-pages.tsx`), mène au compte rendu de chacun ; la demande
d'export n'offre que les natures que la révision lue offre d'exporter (`exportOffers`, `export_*`) — un export, gardé par la permission de
consulter sa nature, est présent ou absent —, et part pour cette révision — l'image de
l'arborescence au niveau demandé —, et le suivi offre de télécharger le résultat d'une tâche qui en
a un : le serveur de Next le lit (`getBackgroundTaskResult`) et le transmet en flux, sans le tenir
entier en mémoire et hors de la file des actions serveur, à la route `/tasks/[taskId]/result`, que
le navigateur suit comme un lien, sans `download` : un type que le contrat déclare pour sa nature,
et la pièce jointe nommée du nom de base que le contrat promet (`Content-Disposition`,
`attachmentName`), sans sa longueur, que `fetch` a décodée, et que rien ne garde en cache
(`private, no-store`). Ce que la route ne transmet pas — un refus de l'API, dont le résultat expiré
ou pas encore prêt (409), l'API injoignable, une réponse qui ne nomme pas le fichier ou dont le
type n'est pas déclaré, l'erreur inattendue d'une mauvaise passerelle (502) — renvoie le navigateur,
par une adresse relative, à l'écran d'où il partait (`from`), l'adresse nommant la tâche et le
refus (`refused_task`, `refusal`, `result-refusal.ts`) : le suivi relit la tâche, la suit et dit
le refus dans son entrée (`OutcomeNotice`) — ou, la tâche illisible, dans un avis de son panneau —,
et l'ôte de l'adresse une fois la page révélée, le routeur de Next rendant à neuf une page dont
l'adresse change (#416).

Les écrans du portefeuille, `/portfolio/…` (`frontend/src/components/portfolio/`, FBS-2), sont
hors projet : chacun lit sa vue sur le périmètre de l'adresse, sous les noms du contrat — les états
retenus (`states`), la période (`from`, `to`), la date de calcul (`as_of`) et le nœud d'organisation
(`org_node_id`), qui retient aussi ses descendants, offert dans l'ordre de l'arbre que rend
`listOrgNodes`, chaque nœud décalé de sa profondeur (`treeLabel`, comme le filtre du plan de charge
d'un projet) —, de ce périmètre ce que l'opération prend (`perimeterQuery`, `Takes`). Un état se montre
pressé comme l'adresse le demande, ou, quand elle n'en nomme aucun, comme le serveur les a retenus
(`scope.states`) : le front ne suppose aucun défaut. Sous le titre, le périmètre que le serveur a
retenu et la date de calcul de la vue, `scope.as_of` (`PortfolioHeader`), que portent tous ses
chiffres, et le nœud retenu, nommé par le serveur (`scope.org_node_label`). Une période que le
serveur refuse — une fin qui précède le début, `PortfolioPeriodRefused`, EP-02/L42f — est dite au
champ de la fin, le début nommé, comme les coûts réels la disent (`usePeriodProblem`) — une borne
seule se complétant par la période par défaut, un début postérieur à la fin complétée est dit au
champ du début, la fin nommée (`params.maximum`) — ; la vue n'est
pas lue, son titre reste sans périmètre retenu et une phrase tient sa place (`RefusedView` de
`frontend/src/app/portfolio/refused.tsx`) ; ses états sont pressés comme l'adresse les nomme, et,
sans état nommé, le filtre des états n'est pas offert, rien ne disant ce que le serveur retiendrait.
La liste des projets (FBS-2.1) est une configuration de plus de la grille dense, triée,
cherchée et paginée par le serveur, sa ligne de totaux le nombre de projets retenus
(`meta.total`), sous la valeur du portefeuille. Les six autres vues (FBS-2.2 à FBS-2.7) montrent ce
que le serveur calcule : le plan de charge agrégé et les décaissements prennent en outre l'horizon
(`horizon_months`) et, pour le premier, le seuil de sous-charge (`under_load_threshold`),
paramètres de la vue et non préférences (WF-PTF-0060) : le menu propose quelques valeurs, mais toute
valeur de l'adresse que le contrat prend — un horizon de 1 à 240 mois, un seuil en `Percent` — est
envoyée et se montre choisie ; sans seuil dans l'adresse, le menu montre celui que le serveur a
retenu (`under_load_threshold` de la réponse), comme les états ; les colonnes du plan de charge
sont les mois de la réponse (`months`), que chaque rôle porte dans le même ordre. Un signal de santé
dit ce qu'il nomme (`params` : les semaines sans revue, le jalon dépassé et sa date de référence),
comme une alerte de l'état du système le composant indisponible. Chaque projet nommé — libellé de la liste, risque le plus lourd, signal de santé —
ouvre le projet (WF-PTF-0030). Les zones d'indice, de charge et de santé sont celles du serveur,
par `Signal` ; l'évolution trimestrielle des indices, la courbe en S et les décaissements sont des
figures de `Chart`, exportées en PNG avec la provenance de leur vue (`usePortfolioExport`) : le
périmètre que le serveur a retenu — états, nombre de projets, période, nœud d'organisation — et sa
date de calcul, `scope.as_of`, la phrase même de l'en-tête (#312).

Un bloc copié d'un tableur se colle sur la cellule active, en deux temps (WF-IHM-0050,
`paste.ts`) : le bloc se lit à l'événement `paste`, écouté sur le document — le navigateur le
vise où un clic a laissé le curseur, la cellule est celle qui a le focus dans la grille, et une
saisie en cours garde le collage pour son champ —, jamais par `navigator.clipboard`, qui demande
une permission ; en valeurs séparées par des tabulations, une cellule entre guillemets gardant
ses tabulations et ses fins de ligne (`readBlock`). Le serveur remplit, à partir de la colonne
visée, les colonnes de la facette du nœud visé dans l'ordre de `NodeColumn`, sans connaître
celles que la grille montre (#200) : le front mesure donc le bloc sur ces colonnes-là
(`GridPaste.span`, `pasteSpan`, #223), et refuse aussitôt, sans rien demander, un bloc plus
large qu'elles à partir de la cellule — comme le serveur le refuserait (`PASTE_TOO_WIDE`) — et
un bloc dont la portée, de la colonne visée à la dernière colonne remplie dans cet ordre,
atteint une colonne que la grille ne montre pas, masquée ou absente de sa configuration, qu'il
nomme — par son en-tête, ou par son libellé du catalogue (`enums.NodeColumn`) ; il refuse de même
un bloc dont une ligne ne tomberait pas sur celle que le serveur écrit : le serveur remplit les
lignes du plan sous la ligne visée, que la grille connaît par leur numéro dans toute la structure
(`row_number`), non les lignes affichées après elle. Une seule garde compare, de la cible à la
dernière ligne du bloc, le numéro de chaque ligne affichée à celui qu'elle aurait dans l'ordre du
plan — une grille qui colle lit tous les genres de nœud, et ses numéros se suivent — ; pliée
(`fold.tsx`), déplacée par un tri, cachée par la recherche ou un filtre, ou au-delà de la dernière
ligne montrée, la cause dite est celle que l'utilisateur lève d'abord (L40, #527).
Sinon `previewPaste` rend le plan, que
montre une boîte de dialogue de shadcn (`PasteDialog`, `ui/dialog.tsx`), dans une seule région
annoncée — ce qui sera écrit, chaque ligne refusée par sa place dans le bloc, ses cellules
telles que copiées et son motif ; un plan qui refuse une ligne n'annonce que des lignes valides,
rien ne sera écrit —, et `applyPaste` l'applique sur confirmation, en une seule opération ; ce
qu'il rend prend la place de ce qui était lu (`CellWrites.applied`) ; une écriture de cellule
partie avant le collage et répondue après se prend comme toute réponse, le compteur de la
structure décidant laquelle des deux une ligne montre (`answers.ts`, #202), et seul son refus se
tait quand le collage a écrit sa ligne depuis. Un plan qui refuse
une ligne ne s'applique pas : la boîte n'offre que l'abandon. Échap abandonne, une réponse
arrivée après l'abandon est ignorée, et le focus revient à la cellule. Le front ne juge rien du
contenu : la colonne visée part sous son nom de colonne du contrat (`NodeColumn`), que la grille
la trie ou non, et la confirmation porte la version
de la structure lue (`structureVersion`) — deux points que le contrat ne dit pas encore (#200,
#201). Une grille sans `paste` dans sa configuration, en lecture seule, ne prend aucun collage.

Annuler et Rétablir sont posées, pas branchées (WF-IHM-0110, US-0140, `undo-commands.tsx`) :
toute grille dont la révision en cours se saisit par sa commande `edit_*` les pose (`undoable`
de `DenseGrid`) — le devis par `edit_estimate`, le planning par `edit_planning`, le reste à
engager par `edit_remaining` (#115) ; aucune grille hors d'une révision en cours ne les pose : ni
le marquage, ni un import appliqué, ni l'exclusion d'une ligne de coût ne s'annulent. Une telle
grille les montre en boutons dans sa barre et dans le menu contextuel de ses cellules (clic droit,
Maj+F10, touche Menu — `CellMenu`, sans arrêt de tabulation de plus), avec leurs raccourcis, et
prend Ctrl+Z et Ctrl+Maj+Z — Cmd sur un Mac — dans la grille ou sa barre, hors d'un menu ou d'une
boîte qu'elle ouvre. Indisponibles tant que le serveur ne conserve pas l'historique des saisies,
elles restent atteignables au clavier, `aria-disabled`, décrites par leur raison ; le raccourci la
dit dans une région annoncée. Un champ en cours de saisie — l'éditeur d'une cellule, la
recherche — garde Ctrl+Z pour lui : l'annulation du navigateur y reste. EP-06 les branche sur
`undoLastChange` et `redoLastUndo`, une annulation portée par le serveur, jamais une pile dans le
navigateur.

Les grilles arborescentes — planning, devis, reste à engager — se plient et se déplient
(WF-PLA-0080, WF-PLA-0090, EP-02/L40, `frontend/src/components/grid/fold.tsx`) : une grille dont
l'arbre nomme le parent de chaque ligne (`GridTree.parent`, `parent_id` de `listNodes`) est un
`treegrid`, chaque ligne portant `aria-level`, `aria-posinset`, `aria-setsize` et, quand la réponse
tient des lignes sous elle, `aria-expanded`. Une ligne pliée sort ses subordonnées des lignes de la
grille : la virtualisation ne les rend plus, le clavier ne les parcourt plus, et le Gantt, une
colonne de la même grille, les perd avec elle ; la cellule active reste sur sa ligne, ou passe à
celle qui la porte. Le bouton du libellé — ou celui qui précède le crochet d'une récapitulative dans
le Gantt — plie ou déplie sa ligne, hors de l'ordre de tabulation ; au clavier, comme dans Microsoft
Project, Alt et moins plie la ligne de la cellule active — celle qui la porte, depuis une ligne
sous laquelle rien ne se plie —, Alt et plus la déplie, Alt et * déplie tout, Maj ou non selon ce
que la disposition du clavier demande pour taper le caractère, sur le pavé numérique aussi ; le
caractère est celui que la touche a tapé, et, quand il ne nomme aucune commande, celui que la
touche porte dans la disposition que le navigateur dit (`navigator.keyboard.getLayoutMap`) —
jamais la seule place de la touche, qui porte un autre caractère sur une autre disposition. Ctrl
et AltGr sont exclus ; Alt+Maj+flèches restent libres pour l'indentation d'EP-06. Ces raccourcis
ne sont que des accélérateurs : sans `getLayoutMap`, sous Safari et Firefox pour Mac, Option et une
touche tapent un autre caractère, et ils ne sont pas reconnus. Le menu contextuel des cellules
(Maj+F10, touche Menu, clic droit), offert dans toute grille arborescente, Annuler et Rétablir ou
non, les remplace partout : « Plier la ligne » — « Plier « libellé » », qui nomme la ligne qui
la porte, depuis une ligne sous laquelle rien ne se plie —, « Déplier la ligne » quand elle l'est,
« Tout déplier », offert même hors d'une cellule, si bien que le menu n'est jamais vide ; le focus
revient à la cellule active. Les touches se disent par `aria-keyshortcuts` — Maj+F10 sur chaque
cellule, celles du pliage sur le libellé d'une ligne qui se plie, dans le menu et dans la barre —,
autant que le navigateur les reconnaît (`useFoldReach`, lu après l'hydratation) : toutes hors d'un
Mac ; sur un Mac, Alt et moins, Alt et plus quand `getLayoutMap` existe, aucune sinon ; Alt et *
hors d'un Mac seulement. Un
bloc collé qui s'étendrait, à partir
de la ligne visée, sur une ligne pliée est refusé sans rien demander, comme celui qui atteint une
colonne masquée. Le menu « Arbre » de
la barre plie tout, déplie tout, ou plie jusqu'à un niveau. Une recherche ou un filtre qui retient
une ligne pliée déplie ses ancêtres, une fois pour cette recherche. L'état plié se garde dans le
stockage de session de l'onglet (`sessionStorage`), par grille et par révision, sans rien envoyer
au serveur : le serveur rend l'arbre déplié, que le navigateur replie une fois hydraté.

Une commande s'affiche par `Command` de `frontend/src/components/commands/` (WF-IHM-0090) :
absente quand l'objet ne la liste pas dans `available_commands` — le serveur n'y met que
celles que l'appelant a la permission d'exercer, et le front ne sait pas quelle permission
garde quelle commande ; seule exception, décidée par l'utilisateur le 2026-10-05, un import
sans révision en cours que l'appelant ne pourrait pas créer, listé indisponible,
`may_create_revision` manquante —, présente et disponible, ou présente et indisponible, marquée
`aria-disabled` et décrite par le texte visible des conditions qui lui manquent
(`enums.CommandCondition.*`). `LifecycleCommands` rend, dans l'ordre du serveur, les sorties
du cycle de vie d'un projet — les autres commandes du projet appartiennent aux formulaires de
leur domaine, sa modification à celui de ses paramètres (`ProjectIdentity`) —, et `RevisionCommands` celles d'une révision, chacune selon son
`is_available` et ses conditions — une révision marquée les liste indisponibles, faute d'être
en cours d'élaboration —, ses exports laissés à l'écran des imports et exports, qui les offre
(`ExportForm`) ; `findOffer` en tire une seule, et `UnmetConditions` nomme ce qui manque à
l'offre d'un formulaire qui n'est pas un `Command`. Hors projet — comptes, rôles, référentiel,
sauvegarde —, `platformOffer` suit la permission de modification d'une fonction de portée
`platform` (`PlatformFunction`) dans `Session.permissions`, ou `project_create` pour la création
d'un projet, qu'aucun projet ne liste ; les commandes d'une sauvegarde sont celles qu'elle liste
(`Backup.available_commands`, EP-14/L43f), le téléchargement et la restauration comprises. Griser n'est qu'une
commodité : une commande disponible lance son action serveur, et le refus du serveur est dit
par `OutcomeNotice`.

Une action longue rend la main à la réception de sa tâche de fond (WF-ARC-0090) : son action
serveur passe par `decodeTask` de `frontend/src/api/problem.ts`, qui tient le motif d'un échec
à la règle du catalogue, et l'écran remet la référence au suivi de la coquille par
`useTrackTask()` (`frontend/src/components/tasks/`), avec la commande qui l'a lancée et, s'il
y en a un, le nom que l'utilisateur lui a donné (WF-IHM-0080). Le suivi est commun aux neuf
genres de tâche : il relit la tâche toutes les deux secondes tant qu'elle court, par l'action
serveur `readBackgroundTask`, en montre l'avancement, ajoute sa fin à un journal
(`role="log"`) lu quel que soit l'écran, offre de recharger l'écran quand elle a abouti — il
ne recharge jamais de lui-même —, et rejoue la commande d'une tâche échouée. Son panneau est
sous la barre de la coquille, dans le flux de la page ; le bouton des tâches de fond
(`TasksButton`), qui en dit le nombre, le montre ou le cache, et une tâche remise le montre.
Caché, le panneau suit encore ses tâches — ses entrées restent montées — et son journal, hors
de ce qui se cache, parle toujours. Une relance
refusée comme périmée (412) perd sa commande, qui le serait encore, et une relecture refusée
(404, 401) interrompt le suivi, qui le dit. Aucun écran ne suit ses tâches lui-même. Une
réponse ne s'applique qu'à la tâche pour laquelle elle a été demandée, jamais à celle qu'une
relance a mise à sa place. Les actions serveur de Next partent une à une, dans une seule file :
suivre k tâches ajoute k actions toutes les deux secondes, dans la file même des écritures de
l'écran, qu'une relecture lente retarde d'autant. Le stockage de session de l'onglet garde les
tâches qui courent pour un rechargement complet, sans leur commande mais avec le nom que
l'utilisateur leur a donné ; et, pour une session ouverte, le layout racine demande côté
serveur les tâches de son utilisateur qui courent (`listBackgroundTasks`), lancées d'un autre
onglet ou d'un autre poste — plutôt que par une action serveur au montage de la coquille, que
`StrictMode` lançait deux fois en développement. Il ne les attend pas : il passe leur promesse
au suivi (`running`), qui la lit par `use()` sous un `Suspense` qui ne rend rien, et le
document part sans elles ; sans session, rien n'est demandé. Le suivi les redemande par une
action (`listRunningTasks`) chaque fois que l'onglet redevient visible (`visibilitychange`,
`signedIn`) ; il suit celles qu'il ne suivait pas — une liste refusée ou injoignable le laisse
tel qu'il est, et la promesse ne rejette jamais. Une tâche retrouvée par le stockage ou par la
liste ne se relance pas du suivi : échouée, son entrée dit de la relancer depuis l'écran de son
objet. La commande `mark` d'une révision
(`MarkCommand`) en est le premier emploi : elle ouvre, dans la page, la saisie du nom de
version.

L'image de développement (`frontend/Dockerfile`) part d'une image épinglée par son
empreinte, et tourne sous un utilisateur non privilégié, désigné par son numéro.

Le client de l'API est engendré du contrat (PBS-1.2, WF-ARC-0060) : `make generate-client`
écrit ses types dans `frontend/src/api/generated/schema.d.ts`, que personne ne retouche, et
`frontend/src/api/client.ts` en fait des appels typés par openapi-fetch, une liste de la requête
écrite en un seul paramètre, ses valeurs séparées par des virgules, comme le contrat les déclare
toutes (`explode: false`, que `make lint-openapi` exige de chaque paramètre de tableau :
`rule/array-parameter-explode-declared` et `rule/array-parameter-not-exploded` de
`docs/api/redocly.yaml`). Il écrit à côté `examples.d.ts`, les exemples de `fixtures/api/` que
le contrat cite par opération et par statut (`wftools.exampleroutes`), qui type les réponses du
faux client des tests. Une opération qui
manque au client est une modification du contrat, suivie d'un `make generate-client` ; le
fichier engendré se versionne avec elle. Aucun appel réseau ne s'écrit hors de
`frontend/src/api/client.ts`, et seul le serveur Next appelle l'API : un composant client
n'importe de `src/api/` que ses actions serveur (`src/api/actions/`) et des types.

*Contrôles* : `make client-up-to-date` échoue si le client versionné n'est pas celui que le
contrat produit ; une modification du contrat réveille donc la famille front. ESLint refuse
hors de `src/api/client.ts` les moyens connus d'atteindre le réseau — `fetch`,
`XMLHttpRequest`, `WebSocket`, `EventSource`, un client http importé —, et, dans un fichier
`"use client"`, l'import direct de `src/api/` hors des actions serveur, qui s'ouvrent sur
`"use server"` ; `src/api/network-guard.test.ts` l'éprouve sur des extraits piégés, et fige
la liste des dépendances de `package.json`, pour qu'une nouvelle soit examinée pour la
garde avant d'entrer. Le cas transitif — un module sans directive qui importe
`@/api/server`, et qu'un composant client importe — échappe à ESLint : `client.ts` et
`server.ts` importent `server-only`, le filet de `next build`, que `make build-front` lance au
palier rapide, sans API joignable : une page qui lirait l'API à la construction, pré-rendue
au lieu d'être rendue à la requête, le fait échouer (#131) ; au palier complet, la mesure du
§4.6.2 le construit (`make e2e-measure`, et `make e2e` sur un poste). `make typecheck-front`,
`make test-front` ;
`make lint-docker` (hadolint).

## Le faux back

Le faux back sert le contrat par prism, sans une ligne de réponse écrite à la main : ce qu'il
répond, ce sont les **exemples du contrat**. Une réponse qui manque est un exemple ajouté au
contrat, jamais un fichier dans le front ; un exemple invalide au regard de son schéma fait
échouer `make lint-openapi`.

Un exemple long se range sous `fixtures/api/`, en objet Example d'OpenAPI (`summary`,
`value`), et le contrat le cite par `$ref` ; le bundle l'embarque. Ses nombres reprennent
ceux des Vérif là où ils ont un sens — probabilité de gain, inflation, montants.

**L'univers témoin.** Les exemples décrivent un seul univers, à un seul instant, aujourd'hui :
le 3 juin 2026 à 14 h 05 UTC (`docs/api/DECISIONS.md`, « L'univers témoin »). Le premier
exemple de chaque opération est le projet témoin, PRJ-001, ou le portefeuille qui le compte, à
cet instant ; un autre exemple nommé en est une autre lecture, un instant antérieur de la même
chronologie, la suite d'une écriture faite aujourd'hui, ou une variante contrefactuelle déclarée.

**Ce qui s'engendre ne s'écrit pas à la main.** `make mock-data` (`wftools.mockdata`) écrit,
sans lire ni l'horloge ni le hasard — chaque valeur tirée vient de l'empreinte d'une graine fixe
et de ce qu'elle décrit, et deux engendrements écrivent les mêmes octets :

- dans `fixtures/api/volume/`, qu'on ne retouche pas, les volumes du §4.6.2 : la structure du
  témoin, mille tâches et cinq mille lignes, son cœur lisible en tête et relié aux tâches tirées
  autour de lui, datée en heures sur le calendrier de chaque tâche et lue aujourd'hui
  (`wftools.mockstructure`, datée et émise par `wftools.mockcore`), premier exemple de
  `listNodes`, les indicateurs de son devis, ce dont dépend sa première récapitulative et une
  durée allongée qui pousse une tâche en 2027 (`task_lengthened`) ; les trois cents projets de
  `getPortfolioProjects` et les vues qui se somment de leurs lignes — valeur, performance,
  structure des coûts, risques et couverture (`wftools.mockportfolio`) — ; les deux cents
  catégories de coût et quinze ans de taux horaires, en une page et par pages, la grille triée
  aussi par le taux d'une année (`wftools.mockreference`) ;
- sous `fixtures/api/`, par leur nom, les exemples du témoin, déclarés engendrés dans
  `tools/paths.toml` : les lectures de son cœur (`wftools.mockcore`, décrit une fois dans
  `wftools.mockwitness`, ses heures de travail dans `wftools.mockcalendar`, ses lignes triées sous
  chaque tâche par `wftools.mocksort`) ; les réponses des
  écritures de grille, différence de deux lectures (`wftools.mockwrites`) ; son histoire, ses
  révisions comparées et ses risques (`wftools.mockhistory`) ; ses indicateurs, ses courbes et
  son plan de charge aujourd'hui, sur toute la structure de mille tâches (`wftools.mocktoday`,
  `wftools.mockindicators`, `wftools.mockcurves`) ; ses coûts réels — ceux que le témoin décrit et
  les factures de ses tâches tirées terminées — et le journal de leurs imports (`wftools.mockcosts`) ;
  et les vues du portefeuille dans le temps — plan de charge agrégé, courbe en S et sa variante
  au 31 décembre 2025, santé du pilotage —, qui somment le témoin à ses propres lectures et les autres projets par des
  formules simples (`wftools.mockportfoliotime`) ; et le journal d'audit de l'installation, tiré de
  la chronologie du témoin et des exemples qui datent ses comptes, ses rôles et ses sauvegardes
  (`wftools.mockaudit`, tenu par `tools/tests/test_mockaudit.py`) ; et les lectures des listes
  écrites à la main — les projets de l'accueil, les sous-projets et les contributeurs du témoin, les
  comptes et les rôles d'habilitation — et du lotissement du témoin, triées, cherchées et filtrées
  comme leurs écrans les demandent (`wftools.mocklists`, tenu par `tools/tests/test_mocklists.py`).

Ce que la même commande engendre ne se relit jamais sur le disque : les indicateurs, les risques
et les courbes du témoin, que le portefeuille somme, lui sont passés en mémoire, pour qu'une seule
exécution de `make mock-data` atteigne son point fixe.

**Ce qui reste écrit à la main** — sessions, comptes et rôles, référentiel (rôles de ressources et
leurs effectifs, calendriers, nœuds d'organisation), le projet, ses révisions et ses transitions,
imports et leurs comptes rendus, tâches de fond, état du système et sauvegardes, variantes
contrefactuelles — est lu par les générateurs, jamais recopié, et confronté à ce qui est engendré :
`tools/tests/test_mockhistory.py` pour la chronologie, `tools/tests/test_mockuniverse.py` pour le
reste (les heures mensuelles d'un rôle, tout son effectif compris, valent son effectif par les
heures hebdomadaires de son calendrier × 52 / 12, la ligne du témoin au portefeuille est celle de
ses indicateurs, toute vue du portefeuille est calculée aujourd'hui…). Un exemple de volume s'écrit une ligne par élément, pour qu'un changement se lise
dans le diff. Les repères que lisent les parcours de bout en bout — numéros de ligne, libellés,
totaux — sont fixés par `test_the_marks_the_journeys_read` (`tools/tests/test_mockstructure.py`)
pour la structure, `test_the_marks_the_portfolio_journey_reads` (`tools/tests/test_mockdata.py`)
pour le portefeuille et `test_the_marks_the_review_journey_reads` (`tools/tests/test_mocktoday.py`)
pour la revue mensuelle : un changement du générateur qui les déplace échoue là, avant les
parcours. Les tests de grille ne vérifient que des lignes qui restent dans la fenêtre que la grille
virtualisée rend. Les tests du front lisent l'adresse d'un nœud du témoin dans l'exemple — son
identifiant, son index ou son numéro trouvés par son libellé —, jamais un numéro écrit en dur,
sauf là où le numéro est ce que le test éprouve (#400).

`make mock-spec` dérive du contrat la variante que prism sert : chemins sous le préfixe du
serveur, `/api/v1`, que prism ignorerait, et aucune session exigée — le faux back accorde
celle dont part la maquette (EP-02). Rien d'autre ne change.

- `make mock` : le faux back seul, sur `http://localhost:4010`.
- `make dev` : le front (`http://localhost:3000`) contre le faux back, par
  `deploy/compose/compose.dev.yaml`. Le front ne connaît que l'adresse de l'API,
  `WATERFALL_API_ADDRESS` : à partir d'EP-03, la même variable désigne le vrai service.
  `make dev-down` l'arrête. Le faux back garde le cache de npm, où `npx` a mis prism, dans
  le volume nommé `mock-npm`, monté sur le répertoire de l'utilisateur 1000 de l'image, qui
  en est propriétaire : prism n'est téléchargé qu'au premier démarrage.
  `docker volume rm waterfall-dev_mock-npm`, la plateforme arrêtée, l'oublie.
- Le front s'ouvre à `localhost` et à `127.0.0.1`. Pour l'ouvrir depuis un autre poste, à
  l'adresse de celui-ci sur le réseau, la déclarer dans `WATERFALL_DEV_ORIGINS` (des hôtes
  séparés par des virgules), à l'appel ou dans `deploy/compose/.env`, que git ignore :
  `WATERFALL_DEV_ORIGINS=127.0.0.1,192.168.1.210 make dev`. Sans elle, `next dev` refuse ses
  ressources à cette origine, et la page s'affiche sans s'hydrater (#481).

Le faux back sert des lectures. Il ne garde aucun état : un projet créé n'apparaît pas dans
la liste suivante. Il sert aux lots de front qui précèdent leur lot de back et aux tests du
front qui ne font que lire, jamais à éprouver une écriture.

*Contrôles* : `make lint-openapi` (exemples conformes aux schémas, volumes compris),
`make mock-data-up-to-date` (les volumes versionnés sont ceux que l'outil écrit, dans la
famille contract, que `fixtures/api/` réveille comme le contrat), `make lint-compose`.

## Commandes

Tout se lance par le Makefile, sur un poste comme dans la chaîne : `make help` les liste.
Une commande que la chaîne exécute existe dans le Makefile, et un workflow n'écrit aucune
logique de contrôle de son côté ; un échec de la chaîne se reproduit donc par la même
commande.

| Commande | Ce qu'elle fait |
|---|---|
| `make check BASE=origin/epic/EP-nn` | les contrôles de ce que la modification touche, fichiers non commités compris : à lancer avant de pousser |
| `make check-all` | toutes les familles de contrôles |
| `make check-<famille>` | une famille : `repo`, `spec`, `contract`, `back`, `front`, `roadmap` |
| `make changes BASE=…` | les familles qu'une modification touche |

`BASE` vaut `origin/main` par défaut ; un lot se compare à la branche de son EPIC.

`make lot-size BASE=origin/epic/EP-nn` mesure un lot : les lignes de son diff, séparées en
code de production, tests et le reste (documentation, configuration, contrat), les fichiers
engendrés mis à part. La pull request met ce nombre à côté de l'estimation de son issue ; un
dépassement ne fait rien échouer (README de la roadmap, section « Lots »).

## Chaîne

La chaîne est faite de workflows GitHub Actions (`.github/workflows/`) :

- `ci.yml` décide des familles qu'une pull request touche (`make changes`), appelle le
  workflow de chacune, et termine par la **porte** (`gate`), qui juge le tout
  (`make gate`) : elle échoue si un travail a échoué ou a été annulé, et un travail sauté
  parce que sa famille n'est pas touchée n'est pas un échec. La porte est le seul contrôle
  que la protection des branches exige : un contrôle exigé qui ne s'exécute pas faute de
  fichier touché resterait « en attente » et bloquerait la fusion.
- un workflow par famille — `repo.yml`, `spec.yml`, `contract.yml`… —, qui installe ses
  outils et appelle `make check-<famille>`. `repo` s'exécute sur toute modification. Le
  front en a deux, qui tournent côte à côte (#492) : `front.yml`, tout sauf les parcours de
  bout en bout (`make check-front-code`), et `e2e.yml`, les parcours et la mesure du §4.6.2,
  au palier complet seulement (`make e2e`, `make e2e-measure`) ; sur un poste,
  `make check-front` enchaîne les deux moitiés, `check-front-code` puis `check-front-e2e`.

Les familles, les chemins qui les réveillent, les chemins engendrés et ceux des tests sont
déclarés dans `tools/paths.toml`, et nulle part ailleurs. Un chemin de `shared` — le
Makefile, les workflows, la déclaration elle-même — réveille toutes les familles.

Deux paliers : le rapide à chaque poussée sur une pull request (`pull_request`), le complet
dans la file de fusion (`merge_group`), sur le résultat de la fusion, avant qu'elle soit
acceptée. Le palier complet ajoute ce qui est lent — la couverture du code, puis les tests de
bout en bout ; sur un poste, `make check-back TIER=full`. Une pull request entre dans la file par
le bouton « Merge when ready », ou par la mutation `enqueuePullRequest` de l'API GraphQL :
`gh pr merge` ne sait pas le faire tant que la fusion automatique est désactivée sur le
dépôt. Une branche sans file de fusion fait tourner le palier complet à la main sur la
branche d'un lot, avant de le fusionner : `gh workflow run chain --ref <branche>`.

Le palier complet vise moins de huit minutes dans la file pour son travail le plus long
(#492). Les parcours de bout en bout, la moitié la plus longue, s'y prennent ainsi :

- **dans l'image de Playwright** (`mcr.microsoft.com/playwright`), à la version de
  `@playwright/test` que résout `frontend/pnpm-lock.yaml`, épinglée par son empreinte
  (`container:` d'`e2e.yml`) : Chromium et ses paquets système y sont, rien ne vient du miroir
  d'Ubuntu, dont le débit n'est pas le nôtre (#472). Le travail appelle `make e2e`, qui trouve
  le navigateur de l'image (`PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`), et non
  `make check-front-e2e`, qui en installerait un. Monter `@playwright/test` monte l'image avec
  lui, étiquette et empreinte : sinon les parcours s'arrêtent d'emblée sur un navigateur
  introuvable, et `tools/tests/test_playwrightimage.py` échoue avant eux, dans `make check-repo`.
  L'empreinte est celle de l'index multi-architecture de l'étiquette, que donne la ligne
  `Digest:` de `docker buildx imagetools inspect mcr.microsoft.com/playwright:v<X>-noble`, ou
  l'en-tête `docker-content-digest` de
  `curl -sI -H 'Accept: application/vnd.oci.image.index.v1+json' https://mcr.microsoft.com/v2/playwright/manifests/v<X>-noble`.
  L'image n'a pas `make` : son paquet d'Ubuntu noble est téléchargé, épinglé et
  vérifié par son empreinte, comme pandoc ;
- **répartis sur trois runners** (`make e2e SHARD=i/3`, soit `playwright test --shard=i/3`),
  la mesure du §4.6.2 sur un quatrième, seule (`make e2e-measure`), par une matrice dont aucun
  morceau n'annule les autres ; le résultat d'`e2e` est un échec dès qu'un morceau échoue ou
  est annulé, et la porte avec lui. Trois, parce que Playwright répartit des fichiers entiers
  de parcours, à nombre de tests égal, et que les plus longs pèsent : en octobre 2026, le plus
  long de trois morceaux jouait environ 140 s de parcours sur deux workers, celui de quatre
  130 s, quand chaque morceau paie environ deux minutes d'image, d'installation et de
  serveurs. Ce choix se revoit quand les parcours s'allongent : les durées par fichier se
  lisent dans le journal de chaque morceau.

Le back suivra le même modèle dès qu'EP-03 lui donne une base et des parcours (#492, levier 5),
et `back.yml` s'écrira ainsi :

- PostgreSQL tourne en service du travail (`services:`), dans l'image de la version que vise
  la plateforme, épinglée par son empreinte, avec sa sonde de santé : les tests d'intégration
  le joignent sur `localhost`, sans Compose ;
- les tests se répartissent sur les cœurs du runner (`pytest -n auto`, pytest-xdist), chaque
  processus sur sa propre base, créée à son démarrage ;
- la couverture, plus lente, ne tourne qu'au palier complet, à la place des tests simples,
  comme aujourd'hui (`full-else` du Makefile) ;
- les parcours de bout en bout contre le vrai service — les mêmes, `WATERFALL_API_ADDRESS`
  posée — sont répartis par la même matrice qu'`e2e.yml`, le service et sa base démarrés dans
  chaque morceau.

Règles des workflows :

- une action tierce est épinglée par l'empreinte de son commit, la version en commentaire ;
  Dependabot propose chaque mois leur mise à jour (`.github/dependabot.yml`) ;
- chaque workflow déclare `permissions: contents: read`, et n'en demande pas plus sans
  raison écrite ;
- `actions/checkout` ne garde pas le jeton (`persist-credentials: false`) ;
- un outil téléchargé hors d'une action est épinglé par sa version et vérifié par son
  empreinte, comme pandoc dans `spec.yml`.

*Contrôle* : `make lint-workflows` (actionlint) ; l'épinglage et les permissions, la revue.

La protection des branches est un réglage de GitHub, fait par le propriétaire du dépôt :
sur `epic/*`, pas de poussée directe, la porte exigée, la file de fusion ; sur `main`, la
porte n'est exigée qu'à partir de la livraison d'EP-01 — GitHub lit les workflows dans la
branche d'une pull request, et une pull request vers `main` tirée d'avant la chaîne ne la
déclencherait pas.

## Nommage

Le code, les tables, les colonnes, les variables, les chemins et les messages de console
sont en anglais ; la documentation est en français, comme la spécification. Les noms des
objets du domaine sont ceux du tableau de correspondance du §4.4.1 de la spécification
(`estimate_line`, `cost_line`, `revision`…), et les conventions du contrat — `snake_case`,
`operationId` en `camelCase`, identifiants UUID — sont dans `docs/api/README.md`.

*Contrôle* : aucun outil ne vérifie la langue d'un nom ; la revue le fait.

## En-têtes et licences

Chaque fichier de code commence par deux lignes, après la ligne `#!` s'il en a une :

<!-- REUSE-IgnoreStart -->
```text
SPDX-FileCopyrightText: 2026 waterfall-project
SPDX-License-Identifier: AGPL-3.0-only
```
<!-- REUSE-IgnoreEnd -->

dans la syntaxe de commentaire du langage. Le nom du fichier n'y figure pas : il deviendrait
faux au premier renommage ; la première ligne de la docstring du module dit à quoi il sert.
Ce qui ne peut pas porter de commentaire, ou n'y gagnerait rien — documentation, figures,
contrat, gabarits, images, fichiers engendrés — est déclaré dans `REUSE.toml`. Le code de
conduite garde sa propre licence, CC BY 4.0.

Un document qui cite ces deux lignes, comme celui-ci, les encadre de
`REUSE-IgnoreStart` et `REUSE-IgnoreEnd`, faute de quoi l'outil les lirait comme la licence
du document.

*Contrôle* : `make reuse` échoue sur un fichier couvert ni par un en-tête ni par
`REUSE.toml`.

## Outils du dépôt

Les outils vivent dans `tools/`, en Python, avec leurs tests (`make test-tools`). Tout outil
qui a besoin des exigences les lit par `wftools.projection`, qui lit la projection
`docs/spec/waterfall-spec.md` : un seul lecteur, pour que deux outils ne puissent pas
diverger sur ce qu'une exigence dit. Il compare les textes après normalisation — apostrophes
et espaces typographiques rendus simples —, et découpe un Vérif en phrases. L'exemple du
§1.3.1, `WF-EXA-0010-A`, n'est pas une exigence du produit : les outils l'excluent.

*Contrôle* : `make test-tools`.

## La roadmap et les exigences

Les US de `docs/roadmap` citent les exigences qu'elles réalisent, et leurs critères
d'acceptation reprennent le Vérif de chacune **mot pour mot**, en critère ou en écart : ce
sont les cas de test à venir. `make roadmap` confronte la roadmap au document, et échoue :

- sur un identifiant inconnu, ou d'un indice de révision que le document a dépassé, dans un
  tableau d'EPIC comme dans une US ;
- sur une phrase du Vérif d'une exigence citée, absente de l'US ou tronquée — une phrase se
  cite entière, point final compris ; les apostrophes et les espaces typographiques ne
  comptent pas ;
- sur une exigence du tableau d'un EPIC qu'aucune de ses US ne cite, sauf si l'EPIC est
  `à planifier` ;
- sur une exigence qu'aucun EPIC ne close, ou que plusieurs closent.

Il liste, sans échouer, les exigences F0 qu'aucune US ne cite encore : leur nombre décroît à
mesure que les US des EPIC suivants s'écrivent. L'outil ne lit que le dépôt : l'état des
issues n'est pas son affaire.

Il échoue aussi sur une commande `make` que cite un agent (`.claude/agents/`,
`docs/dev/agents.md`) et que le Makefile n'a pas : une cible renommée ne laisse pas un agent
appeler une commande disparue.

*Contrôle* : `make roadmap`, famille `roadmap` de la chaîne, réveillée aussi par un
changement de la projection ou des agents.

## Commentaires

Un commentaire dit pourquoi, pas ce que fait le code : la raison d'un choix, un invariant,
un cas limite. Il est en anglais, comme le code.

*Contrôle* : aucun outil ne juge ce qu'un commentaire dit ; la revue le fait. La forme des
docstrings, le code commenté et les `TODO` — toujours `TODO(#12): …`, avec le numéro de
l'issue — sont contrôlés : voir « Lint, typage et format ».

## Lint, typage et format

Ce que la spécification appelle analyse statique (WF-QUA-0030) : tout est bloquant, et aucun
avertissement n'est toléré ; ce qui ne mérite pas de bloquer se retire du jeu de règles.

**Python** — le back et les outils du dépôt partagent un seul jeu de règles,
`ruff.toml`, à la racine :

- toutes les règles de Ruff sont actives ; celles qui sont retirées sont listées, chacune
  avec sa raison, et l'historique du fichier montre chaque retrait ;
- complexité cyclomatique inférieure à 15 par fonction (`C901`, maximum 14) ;
- l'en-tête SPDX (`CPY001`), une docstring d'une ligne pour ce qui est public (`D1`,
  convention PEP 257 ; ni les tests ni les méthodes spéciales n'en demandent), pas de code
  commenté (`ERA001`), un `TODO` qui cite son issue (`TD003`) ;
- Pyright en mode strict (`[tool.pyright]` de chaque projet), `# type: ignore` non honoré.

**Aucune règle ne s'écarte par un commentaire dans le code.** Une exception, s'il en faut
une, s'écrit dans la configuration de l'outil — `per-file-ignores` de `ruff.toml` —, avec sa
raison. Aucun fichier source ne dépasse 1 000 lignes, lignes vides et commentaires compris ;
les fichiers engendrés en sont exclus.

*Contrôles* : `make lint-back`, `make typecheck-back`, `make lint-tools`,
`make typecheck-tools` ; `make sources` pour les commentaires d'exemption et la taille des
fichiers, sur tout le dépôt. Les outils de `docs/spec/tools` et `docs/api/tools` suivent
les mêmes règles que ceux de `tools/` ; une exception, s'il en faut une, se déclare dans
`tools/paths.toml`, avec sa raison et ce qui la lèvera.

**TypeScript** — le front a son jeu de règles dans `frontend/eslint.config.mjs` :

- les configurations recommandées d'ESLint, de Next.js (`core-web-vitals`) et de
  typescript-eslint en mode strict, avec les informations de type ; ce qui leur est ajouté
  ou retiré est écrit dans le fichier, avec sa raison ;
- complexité cyclomatique inférieure à 15 (`complexity`, maximum 14) ; 1 000 lignes au plus
  par fichier (`max-lines`) ;
- une docstring JSDoc pour ce qui est exporté, sans type — TypeScript les porte
  (`jsdoc/no-types`) — et sans section par paramètre, qui répéterait la signature ;
- aucun des moyens connus d'appeler le réseau hors de `src/api/client.ts` — `fetch`,
  `XMLHttpRequest`, `WebSocket`, `EventSource`, ni un client http importé —, et aucun
  import de `src/api/` dans un composant client hors des actions serveur : l'API ne
  s'appelle que par le client engendré, depuis le serveur
  (WF-ARC-0020) ;
- aucun texte destiné à l'utilisateur écrit dans le code (WF-QUA-0070) : voir « Clés de
  traduction » ;
- Prettier pour le format (`frontend/.prettierrc.json`) ; ESLint s'exécute avec
  `--max-warnings 0`.

Les commentaires de configuration dans le code ne sont pas honorés (`noInlineConfig`) et
`make sources` les refuse. Un `TODO` cite son issue, sous la même forme qu'en Python :
`TODO(#12): …` ; les autres étiquettes d'attente sont refusées — c'est `make sources` qui le
vérifie, ESLint n'ayant pas d'équivalent aux règles `TD` et `FIX` de Ruff.

*Contrôles* : `make lint-front` (ESLint, Prettier), `make typecheck-front`, `make sources`.

**Contrat** — `docs/api/redocly.yaml` étend `recommended-strict` : toute règle de Redocly
bloque. Une opération à laquelle une règle ne s'applique pas — une sonde sans réponse 4xx,
une redirection OIDC sans réponse 2xx — est déclarée dans `docs/api/.redocly.lint-ignore.yaml`,
avec sa raison.

*Contrôle* : `make lint-openapi`.

## Règles de codage

Comment s'écrit chaque langage : [Python](python.md), pour le back et les outils, et
[TypeScript](typescript.md), pour le front. Chacun nomme d'abord les jeux de règles des
outils, par renvoi, puis les règles de conception qu'aucun outil ne contrôle, chacune avec
sa raison, et finit par les défauts déjà rencontrés, que la revue cherche nommément. Les
règles d'écriture du SQL et des migrations viennent avec EP-03, en troisième fichier.

## Tests

- **Un test qui cite son exigence** — voir ci-dessous.
- **Un test qui reprend un exemple chiffré** — voir ci-dessous.
- **Un parcours de bout en bout** — voir ci-dessous.

Les réponses du faux back sont les exemples du contrat, tels quels. Deux exceptions, et seulement
elles. Un test peut retirer une permission d'une session d'exemple pour éprouver une combinaison
qu'aucun compte du témoin ne porte (décision de l'auteur, 2026-10-09) ; il n'ajoute ni ne réécrit
rien d'autre. Il la retire de la session que lit la page (`requestSession` doublé, comme le fait L43c
pour les sauvegardes, `app/reference/costs/page.test.tsx`), jamais en réécrivant une réponse du
client. Et un test peut rendre un composant sur une variante contrefactuelle d'une ligne d'exemple
— une valeur changée, le reste de la ligne gardé —, quand aucun exemple du contrat ne porte le cas
qu'il éprouve : la variante se passe en prop au composant, jamais servie comme réponse du client, et
le test dit de quel exemple elle vient et ce qu'il change (EP-14/L45a). Précédents : « SP-REC », le
sous-projet créé, qu'aucune révision marquée ne cite, déchargé de ses coûts réels, sa suppression
listée disponible comme le serveur la listerait alors, pour la suppression d'un sous-projet, les deux
du témoin étant cités et chargés (EP-14/L42l) ; les commandes des sous-projets ôtées d'une ligne
(EP-14/L44e, `subproject-commands.dom.test.tsx`) — celles d'un projet clos, toutes indisponibles,
ont leur exemple depuis L42o (`subprojects_completed`), qui remplace la variante (EP-14/L52) — ; et l'écart à la revue précédente absent du reste à engager
(`remaining-summary.test.tsx`).

### Un test qui cite son exigence

Chaque exigence F0 est couverte par au moins un test qui la cite par son identifiant complet,
indice de révision compris (WF-QUA-0010).

- **Python** : le marqueur `@pytest.mark.requirement("WF-ARC-0010-A")`, sur le test, sur sa
  classe, ou sur le module (`pytestmark = pytest.mark.requirement(...)`) quand tout le
  fichier porte la même exigence. Le marqueur est déclaré : une faute de frappe dans son nom
  fait échouer Pytest.
- **TypeScript** — Vitest ou Playwright : l'identifiant entre crochets dans le titre,
  `it("lit une grille [WF-QUA-0050-A]", …)`.

Un test cite l'exigence dont il éprouve le Vérif, pas celle dont il parle. Un test qui ne
couvre aucune exigence — un outil, un détail de réalisation — n'en cite aucune.

*Contrôles* : `make requirements` lit les citations dans les fichiers de test, sans les
lancer, et publie le relevé — chaque exigence F0 avec les tests qui la couvrent et leur
famille, celle que `tools/paths.toml` déclare pour leur chemin dans sa table `[tests]` :
bout en bout (`frontend/e2e/**`, qui prime sur le reste de `frontend/`), front, back,
outils — dans le résumé du travail de la chaîne ; une citation d'un identifiant inconnu, ou
d'un indice de révision que le document a dépassé, le fait échouer. Les tests du front
citent des exigences que d'autres EPIC clôturent, par la phrase du Vérif qu'ils éprouvent ;
une exigence que seuls le front et le bout en bout citent, et qu'un EPIC clôt sans avoir
`front` pour seule famille — d'après la table « Exigences réalisées » de la roadmap et le
champ `famille` de son front matter —, est comptée à part, « couverte par le front seul »,
et ne compte pas comme couverte. `make requirements-release` échoue en plus sur toute exigence F0
non couverte, ou couverte par le front seul, en la nommant : c'est la commande de la
publication d'une version. Une exigence dont le Vérif s'ouvre par « Vérifiée en recette »
attend un procès-verbal, dont la forme n'est pas encore définie : le relevé le dit.

### Un parcours de bout en bout

Un parcours s'écrit sous `frontend/e2e/`, en Playwright, et cite dans son titre l'exigence
qu'il couvre : `test("… [WF-QUA-0050-A]", …)`. Il trouve les éléments par leur rôle et leur
nom accessible (`getByRole`), comme un utilisateur les voit, jamais par une classe CSS.

Une page ouverte par son adresse s'affiche avant que React l'ait hydratée : un lien suivi charge
alors son écran en document entier, mais un clic sur un bouton, une touche dans une cellule, se
perdent (#471). Un parcours ouvre donc un écran de projet par `openHydrated`
(`frontend/e2e/hydration.ts`), qui attend le témoin de l'hydratation : le cookie `wf_last_project`,
que la coquille n'écrit que dans un effet. Hors projet, rien n'en témoigne : le geste se répète
jusqu'à ce que React y réponde, sans défaire celui qu'il a déjà reçu (`setExpanded`, `openMenu`, et
`sortUntilAddress` pour un tri, qui ne se presse jamais à l'aveugle). Un écran de grille s'attend à
la borne des écrans de grille, quinze secondes (`WORKING`, #315, #419), qu'un clic l'atteigne ou le
relise (un tri, un filtre, une recherche, le détail d'une ligne). Un écran de grille est une grille
dense — devis, planning, reste à engager, risques, coûts réels, portefeuille —, ou un écran qui lit
la structure de mille tâches (`listNodes`) : le Kanban, l'arborescence, les chronologies. La
comparaison de deux révisions s'y ajoute, le temps d'une décision : elle rend ses 2 770
modifications en une table simple, rendue au serveur, qui dépasse cinq secondes en développement
(constat #624 d'EP-14/L45a, à trancher — admise, ou portée sur la grille dense). Les
risques et les coûts réels, relus, ont dépassé cinq secondes sous charge : les mesures sont
consignées dans #500, qui reste à trancher. Tout autre écran garde les cinq secondes d'une
assertion. Un parcours qui enchaîne trois de ces bornes, ouverture comprise, dépasse les trente
secondes d'un test, et prend `test.slow()`. Une ligne de grille vérifiée est dans la fenêtre :
au-delà des lignes en vue à l'ouverture, le parcours défile jusqu'à elle (`scrollToPosition`,
`frontend/e2e/scroll.ts`) plutôt que de compter sur la marge que la grille rend autour de la
fenêtre.

`make e2e` : Playwright démarre le faux back (`make mock`) et le front, joue les parcours
dans Chromium, puis arrête les deux — il signale leur groupe de processus entier, sans quoi
les serveurs que `make` et `pnpm` lancent survivraient. Il démarre toujours ses propres
serveurs, sur des ports à lui — 4110 pour le faux back, 3100 pour le front de développement,
3101 pour le front construit —, jamais ceux de `make dev`, et son faux back sert une variante
du contrat écrite sous `frontend/.e2e/`, que `make dev` ne lit pas : un port déjà pris fait
échouer le lancement en le disant. `E2E_API_PORT`, `E2E_FRONT_PORT` et
`E2E_PRODUCTION_PORT` déplacent les ports, pour deux copies du dépôt sur un même poste ; un
port qui n'est pas un entier de 1 à 65535 est refusé. `make e2e-browsers` installe le
navigateur. `make e2e SHARD=i/N` ne joue que le i-ième de N morceaux des parcours, comme
chacun des runners de la chaîne (« Chaîne »). À partir d'EP-03, les mêmes parcours se jouent
contre le vrai service en posant `WATERFALL_API_ADDRESS` : le harnais ne démarre alors aucun
faux back.

La seconde du §4.6.2 — ouvrir une grille de mille tâches — se mesure dans
`frontend/e2e/opening.spec.ts` (US-0110, US-0220), sur la structure de volume que sert le faux
back, pour la grille de devis et pour celle de planning ; le faux back sert le planning sans
tenir compte de `kinds=task`, et sa mesure est pessimiste : elle porte sur six mille lignes, et
non sur les mille tâches que le service rendra. Une ouverture va de son début — le début de
la navigation pour une grille ouverte par son adresse, le clic pour une grille ouverte depuis
la barre latérale — jusqu'à la grille utilisable, c'est-à-dire dessinée et hydratée : dessinée,
la première image où l'en-tête de ses colonnes, la légende de ses totaux et la première ligne
de la réponse sont entièrement dans la fenêtre ; hydratée, la première image où la grille
entière est rendue par React — le serveur en rend le premier écran, qui peut s'afficher avant
qu'un clic n'y fasse rien —, que le parcours reconnaît aux clés que React pose, en l'hydratant,
sur le dernier élément de la grille, la dernière cellule de ses totaux (`__reactProps$…`) : un
détail interne de React, lu par le test seul. Le plus tardif des deux
instants se compare à la seconde. Un script remis à chaque document guette chaque image et note
les instants sur l'horloge du système (`performance.timeOrigin`), qu'un document remplacé ne
perd pas : ni les allers-retours de Playwright ni son attente n'y comptent. Elle se joue contre
le front construit pour la production (`next build`, puis `next start` sur le port 3101), que
`playwright.config.ts` démarre après le faux back, à côté du serveur de développement —
celui-ci compile une route à sa première demande et rend avec les contrôles de React en
développement : il dirait la vitesse du poste du développeur. Avant chaque série de cinq
ouvertures — cinq par l'adresse, cinq depuis la barre latérale, pour chaque grille —, une
ouverture n'est pas mesurée : le premier chargement des modules du serveur ne compte pas, et
le cache du navigateur est chaud, comme pour un utilisateur qui a déjà ouvert l'application.
Chaque ouverture ne commence qu'une fois la précédente entièrement servie, préchargements
compris — la grille hydratée, ses liens de la barre latérale demandent encore au serveur les
écrans où ils mènent, et une navigation lancée avant leur réponse les couperait pendant que le
serveur les rend, dans le temps de l'ouverture suivante — : le parcours suit les requêtes de la
page, qu'elles partent d'un document nouveau ou d'une navigation dans la même page, et attend,
hors de la mesure, qu'aucune ne soit en cours depuis une demi-seconde, en quinze secondes au
plus ; le journal écrit combien étaient en cours au départ de chaque ouverture mesurée, et il
n'en faut aucune.
Chaque ouverture se compare à la seconde, sans arrondi ; le journal du parcours, et le résumé
du travail dans la chaîne, sous le titre « The second of §4.6.2 », écrivent la médiane et la
pire, utilisable, dessinée et hydratée, et, pour l'ouverture par l'adresse, où va le temps :
les instants médians où le serveur a fini d'envoyer le document et où le navigateur l'a lu. **La mesure ne fait rien échouer sur la
seconde** : une ouverture qui la dépasse est un avertissement — du test, et de la chaîne —,
jamais un échec, ni de `make e2e`, ni de la chaîne, ni de la file de fusion. Contre le faux
back, pour un utilisateur seul, sur une machine partagée de la chaîne, elle ne dit pas ce que
tiendra le service : ses chiffres variaient d'un run à l'autre du simple au double sur une
même révision. C'est un écart déclaré d'US-0110 et d'US-0220 ; la seconde se tient, bloquante,
en EP-13, sur le jeu de référence, avec cinquante utilisateurs, contre le vrai service. Le
parcours garde seulement des bornes de fonctionnement, loin de la seconde, qui ne mesurent
rien : quinze secondes pour qu'une grille devienne utilisable et qu'une page se pose
(`WORKING`), les cinq secondes de Playwright pour chaque assertion : l'adresse après un clic,
puis ce que la grille montre ; trois minutes pour chaque test. Passé l'une d'elles, le parcours ne fonctionne plus — une grille jamais
utilisable, une page qui ne se pose jamais — et il échoue, quelle que soit la seconde. Le
parcours vérifie enfin que le document ne porte aucun champ d'un nœud que la grille
ne lit pas (`lineage_id`). Son projet Playwright, `production`, dépend du projet `chromium` :
il tourne après tous les autres parcours, seul sur la machine — et ne tourne pas quand l'un
d'eux échoue —, et sans trace. Dans la chaîne, au palier complet, elle tourne seule sur un
runner à elle, à côté des morceaux des parcours (« Chaîne ») : `make e2e-measure`, qui ne
démarre que le faux back et le front construit — le harnais n'en réutilise aucun —, et que
l'échec d'un parcours n'empêche plus. Sur un poste, `make e2e` la joue après les parcours, et
`make e2e-measure` seule. `E2E_PART` dit au harnais ce qu'il joue : `paths`, les parcours sans
la mesure ni la construction du front, que `make e2e SHARD=i/N` pose ; `measure`, la mesure
seule, sans le serveur de développement, que pose `make e2e-measure` ; absente, le tout. Sans
elle, Playwright ne saurait pas répartir les parcours : la mesure, qui les attend tous, les
entraînerait tous dans chaque morceau.

Le parcours témoin — liste des projets, projet, grille — traverse trois pages minimales,
sans texte propre, qu'EP-02 remplace en gardant le parcours. Elles lisent l'API côté
serveur (`frontend/src/api/server.ts`) ; leurs tests unitaires reçoivent les exemples du
contrat par `frontend/src/test/fixtures.ts`, les mêmes données que sert le faux back.

*Contrôle* : `make e2e`, au palier complet de la chaîne ; l'échec d'un parcours la fait
échouer, une ouverture de grille qui dépasse la seconde n'y est qu'un avertissement.

### Couverture du code

La spécification ne demande que la couverture des exigences ; la couverture du code est une
règle du dépôt, qui trouve ce que la première ne voit pas — un chemin d'erreur jamais
exécuté, du code mort. Le back et le front doivent chacun couvrir **90 % des lignes et 85 %
des branches** : les branches comptent, parce qu'un `if` sans son `else` couvre toutes ses
lignes et la moitié des cas. Le code engendré en est exclu. Aucune ligne ne s'exclut de la
mesure par un commentaire ; une exclusion s'écrit dans la configuration, avec sa raison
(`[tool.coverage.report]` de `backend/pyproject.toml`, `coverage` de
`frontend/vitest.config.ts`). Un test qui passe sur des lignes sans rien vérifier est un
défaut, que la revue relève.

*Contrôles* : `make coverage-back`, `make coverage-front`, au palier complet : ils nomment
les fichiers les moins couverts quand un seuil n'est pas atteint.

### Un test qui reprend un exemple chiffré

Chaque phrase chiffrée d'un champ Vérif est un cas de test du noyau, avec les mêmes entrées
et la même valeur attendue (WF-QUA-0020). `make fixtures` les relève dans
`fixtures/examples.json` — fichier engendré, qu'on ne retouche pas —, chacune sous une clé
faite de l'exigence et de l'empreinte de son texte : `WF-PTF-0020-A#ab12cd34ef56`.

Pour éprouver un exemple :

1. écrire une fixture sous `fixtures/`, un fichier JSON qui cite dans `examples` la clé de
   la phrase, et porte ses données, recopiées de la phrase ;
2. écrire le test sous `backend/tests/examples/` : la fixture `example` le charge par la
   clé, le test appelle le noyau et compare à la valeur de la phrase.

Les sockets y sont fermées : un exemple qui passe ne demande ni base, ni service, ni
navigateur. Une phrase modifiée dans le document change de clé ; la fixture de l'ancienne
fait alors échouer la chaîne, et on la réécrit d'après la nouvelle phrase.

*Contrôles* : `make check-fixtures` — le relevé est à jour, chaque clé citée existe, et les
exemples qu'aucune fixture ne cite encore sont listés, sans échec : leur nombre décroît avec
les EPIC de calcul (EP-06 à EP-11).

## Enveloppe d'erreur et codes d'erreur

L'enveloppe est fixée par le contrat (`docs/api/README.md`, WF-ARC-0110) : un code machine et
ses paramètres, jamais une phrase.

- **Ajouter un code côté front** — un code nouveau est d'abord une modification du contrat
  (`ErrorCode`, `docs/api/components/common.yaml`), suivie de `make generate-client`. Le
  front lui donne sa phrase, `errors.<CODE>`, dans les deux catalogues : ce qui est refusé,
  sans rien de ce que les paramètres nomment. Un paramètre nouveau qu'un lecteur doit
  connaître reçoit la sienne, `problemDetails.<param>`, et sa lecture dans `DETAILS` de
  `frontend/src/i18n/problem.ts`, qui nomme une valeur codée — une permission, une
  condition — par son libellé du catalogue ; un paramètre qui ne dit rien à un lecteur —
  un identifiant, un compteur d'écriture — n'en reçoit pas. Un composant rend un refus par
  `problemMessage(problem, { locale, messages })`, jamais en écrivant la phrase.

  *Contrôles* : `make typecheck-front` échoue sur un code d'`ErrorCode` sans clé dans le
  catalogue français, que `problem.ts` lit par `errors.${code}` ; `make catalogs`, sur un
  code sans clé dans l'un des deux, ou sur une clé `errors.` que le contrat n'a plus.
- **Réagir à un refus côté front** — une action serveur ne rend jamais la réponse brute de
  l'API : elle appelle le client par `decode` de `frontend/src/api/problem.ts`, le seul
  décodeur, et rend son `Outcome` — `done` ; `refused`, un `Problem` à dire tel quel ;
  `stale` (412) ; `conflict` (409) ; `signed_out` (401) ; `unreachable`, l'API qui n'a pas
  répondu du tout, distinct de tout `Problem` — le rejet de `fetch` lui-même, que
  `client.ts` marque `Unreachable` (une autre `TypeError` est un défaut et remonte), ou un
  502, 503 ou 504 sans enveloppe `Problem`, qu'une passerelle rend quand le service est
  tombé. Une réponse d'erreur sans enveloppe, ou dont le `code` manque au catalogue — un
  service plus récent que le front —, vaut `INTERNAL_ERROR`, « erreur inattendue », au
  statut reçu : l'écran n'affiche jamais une clé brute. Le composant le dit par
  `OutcomeNotice` (`frontend/src/components/commands/`), en alerte : la phrase de
  `problemMessage` ; sur 412, l'offre de recharger l'écran ; l'objet en conflit
  (`params.conflicting_object_id`, ou à défaut celui du premier refus par champ qui en nomme un,
  `fields[].params.conflicting_object_id` d'un 409 `ALREADY_EXISTS` — `conflictingOf` de
  `frontend/src/api/problem.ts`) nommé quand l'écran le connaît, par `names`, ou à défaut par le
  libellé que le refus lui donne (`conflicting_object_label`) — un projet, un sous-projet que
  l'écran ne montre pas, dont le code pris revient le dialogue fermé (#714) ; sur 401, le
  lien vers la connexion ; l'API injoignable annoncée, jamais un écran blanc ; l'erreur
  inattendue avec sa référence (`correlation_id`), comme l'écran de panne. Une action serveur
  dont la promesse est rejetée n'a rendu aucun `Outcome` : le composant le tient par `rejected`
  (`frontend/src/components/commands/rejection.ts`), une règle pour tous les écrans (#330) —
  une `TypeError` est l'API injoignable : c'est ce que lève le `fetch` du navigateur rejeté, et
  le navigateur ne la distingue pas d'une `TypeError` levée ailleurs, qui passe donc aussi pour
  « injoignable » ; tout autre rejet se classe par son `digest`, comme l'écran de panne le classe
  (`failureOf`) — l'API injoignable, la session perdue avec le lien vers la connexion, ou
  l'erreur inattendue avec sa référence, celle-ci gardée seulement si elle a la forme d'un
  `correlation_id` du contrat. La connexion
  est `/login?next=<chemin et requête de l'écran visé>` (`loginHref`,
  `frontend/src/navigation/login.ts`) : la page de connexion (US-0320), la session rouverte,
  mène à `returnTarget(next)`, qui ne suit qu'un chemin du front — ni `//hôte`, ni une
  adresse d'un autre site — et ramène sinon à l'accueil.

  *Contrôles* : `make test-front` (`problem.test.ts`, `login.test.ts`, `rejection.test.ts`) ;
  qu'une action serveur passe par `decode`, et qu'un rejet passe par `rejected`, la revue.
- **Ajouter un code côté service** — *à écrire*, EP-03, qui crée le service.

## Clés de traduction

Les textes de l'interface vivent dans deux catalogues jumeaux, que lit next-intl :
`frontend/messages/fr.json`, la référence, et `frontend/messages/en.json`. La langue
n'apparaît pas dans l'adresse — un lien partagé s'ouvre chez chacun dans la sienne
(WF-INTF-0170) — : le serveur la résout à chaque requête (`frontend/src/i18n/request.ts`),
d'après la préférence du compte si elle vaut `fr` ou `en`, sinon la première langue offerte
que demande `Accept-Language`, sinon la langue par défaut de l'installation
(`getInstallation`). Un `*` placé devant toute langue offerte dans `Accept-Language` laisse
décider l'installation ; une installation illisible ou injoignable donne `fr`, la langue du
catalogue de référence. Sans compte — pas de session, ou une API injoignable — il n'y a pas
de préférence : le navigateur décide, et la coquille n'offre pas le menu du compte, où la
langue se choisit.

- **Une clé est hiérarchique, en anglais.** Un texte propre à l'interface se range sous le
  composant ou l'écran qui l'emploie, en camelCase (`languageSelector.label`). Ce que le
  contrat énumère garde ses noms, et chaque valeur a sa clé :
  - `enums.<Schéma>.<valeur>` pour une énumération nommée (`enums.ProjectState.in_progress`),
    `enums.<Schéma>.<propriété>.<valeur>` pour une énumération déclarée dans une propriété
    (`enums.BackgroundTaskRef.kind.revision_mark`), les `items` d'un tableau ne comptant pas
    (`enums.ReferenceReadiness.missing.active_cost_category`) : toutes les énumérations de
    `components.schemas`, sauf les deux suivantes ;
  - `errors.<CODE>` pour chaque code d'`ErrorCode`, `permissions.<code>` pour chaque
    `PermissionCode` ;
  - `enums.<Paramètre>.<valeur>` pour une énumération d'un paramètre partagé de
    `components.parameters` (`enums.Scope.unassigned`) : son nom partage le niveau des
    schémas, et un paramètre qui énumère des valeurs ne porte pas le nom d'un schéma ;
  - aucune énumération ne s'écrit en ligne, faute d'un nom pour ranger ses clés : celle d'un
    paramètre d'opération devient un paramètre partagé de
    `docs/api/components/parameters.yaml` ; celle d'un corps de requête ou de réponse, ou
    d'un en-tête — sous `paths` comme sous `components.responses`, `requestBodies` et
    `headers` —, un schéma nommé de `components.schemas`. Deux exceptions, sans clé :
    `sort_by`, dont les valeurs sont des colonnes que l'en-tête de la grille libelle déjà, et
    les corps des sondes, `/health` et les chemins qui en partent, qu'aucun écran n'affiche ;
  - un `const` n'a pas de clé : le contrat ne s'en sert que pour l'accord qu'une requête
    donne (`confirmed: true`), qui ne s'affiche pas ;
  - une valeur qui porte un point se lit comme un niveau, next-intl réservant le point au
    chemin : `permissions.users.write`, `enums.ComputedField.task.start`.
- **Une valeur est un message ICU** — `{max_columns, plural, one {…} other {…}}` —, avec les
  mêmes arguments dans les deux catalogues, ce que `make catalogs` vérifie ; le libellé d'une valeur d'énumération ou d'une
  permission est du texte sans argument. Le français suit sa typographie : espace insécable
  avant les deux-points, fine insécable avant le point-virgule et les points d'exclamation et
  d'interrogation, apostrophe typographique ; l'anglais suit l'orthographe britannique.
- **Ajouter une clé**, c'est l'écrire dans les deux catalogues, au même endroit, et la lire par
  `useTranslations` — composant client, ou serveur sans `await` — ou par `createTranslator`
  et `requestLanguage()` dans un composant serveur asynchrone. Une valeur ajoutée à une
  énumération du contrat ajoute sa clé dans la même modification.
- **Ce que l'utilisateur a saisi ne se traduit pas** : un libellé de tâche, un nom de projet
  s'affichent tels quels (WF-INTF-0170).
- **Les formats** sont ceux de `frontend/src/i18n/format.ts`, par la langue : un montant, un
  décimal, des heures depuis la chaîne exacte du contrat (`formatMoney`, `formatDecimal`),
  jamais par un flottant ; une date de planning telle quelle, sans fuseau
  (`formatPlanningDate`) ; un horodatage en heure locale du poste, écrit dans le navigateur
  (`LocalTime`) ; un rapport saisi ou réglé — un taux, une probabilité, une borne — en
  pourcentage, depuis sa chaîne exacte, chaque chiffre gardé (`formatPercent`) ; une part que le
  serveur calcule — la part d'une nature ou d'un poste, un avancement, un taux de charge — au
  centième de pourcentage (`formatShare`) : une part non nulle que l'arrondi dirait nulle se dit
  « < 0,01 % », ou « > -0,01 % », par le catalogue (`share`) ; une part nulle, quel que soit le
  nombre de ses zéros, se lit « 0 % » ; près de 100 %, l'arrondi ordinaire (EP-14/L51). Une part
  que le contrat donne nulle l'est : une part non nulle n'est jamais donnée nulle, mais à son
  premier chiffre significatif (EP-14/L42o, #694), et le pont de L51, qui jugeait une part nulle
  par son montant, est retiré (EP-14/L52). En français, `Intl` sépare les milliers par une fine
  insécable (U+202F) : « 1 234,56 » ne se coupe pas en fin de ligne. L'anglais se formate en anglais
  britannique (`en-GB`), comme ses catalogues s'écrivent : « 31 May 2026, 16:30 », les
  nombres restant « 1,234.56 ».

*Contrôles* : `make typecheck-front` — next-intl est typé par le catalogue français, et une
clé que le code emploie sans qu'il l'ait casse le typage, comme une clé qui manque au
catalogue anglais (`frontend/src/i18n/catalogues.ts`) ; `make lint-front` —
`react/jsx-no-literals` refuse le texte écrit dans le JSX, et `no-restricted-syntax` un
littéral dans un attribut lu — `aria-label`, `aria-description`, `aria-roledescription`,
`aria-valuetext`, `aria-placeholder`, `title`, `alt`, `placeholder` (sauf `blur`, `empty` et
une adresse `data:image/`, les formes de next/image), `label`, la `value` d'un `input`
bouton —, ou dans une branche ou une concaténation d'un enfant ou d'un de ces attributs ;
restent à la revue les autres props de nos propres composants, et une chaîne bâtie par une
fonction ou une méthode (`.join`, `.concat`), dans le JSX ou hors de lui ;
`frontend/src/i18n/text-guard.test.ts` l'éprouve sur des extraits piégés, à côté de la garde
réseau qui partage la règle ; `make catalogs`, dans `check-front`, qui lit le
contrat qu'il vient d'assembler (`wftools.catalogs`) — les deux catalogues ont les mêmes
clés, chaque valeur est un texte non vide, chaque valeur d'énumération, chaque code d'erreur
et chaque permission du contrat a la sienne, et aucune clé sous `enums`, `errors` ou
`permissions` ne survit à la valeur que le contrat a retirée ; un texte emploie les mêmes
arguments ICU que celui du catalogue français, une clé ne s'écrit qu'une fois par fichier, et
aucune énumération ne s'écrit en ligne, hors `sort_by` et les sondes. Il demande au moins
deux catalogues, et nomme chaque clé qui manque et le catalogue qui la porte.

## Charte graphique

La charte vit dans `frontend/src/theme/globals.css`, et nulle part ailleurs : les couleurs,
la typographie, les espacements et les rayons y sont des jetons — des variables CSS que
Tailwind et les composants de shadcn/ui lisent par le thème (`bg-primary`,
`text-muted-foreground`, `rounded-md`). Les bleus viennent des logos de `docs/assets`
(`#027dc6`, `#1195e1`), qui n'atteignent un composant que par des jetons mesurés, les
neutres de shadcn/ui ; la police est Geist, celle du logo.

- **Clair et sombre par les mêmes jetons.** Chaque jeton de couleur porte ses deux valeurs,
  `light-dark(claire, sombre)`. Le document suit le poste (`color-scheme: light dark`) ; quand
  le compte force un mode (`DisplayPreferences.theme`), le layout racine pose
  `data-theme="light"` ou `data-theme="dark"` sur `<html>`, résolu côté serveur comme la
  langue. Aucun composant ne se demande quel mode s'affiche : la variante `dark:` de
  Tailwind, qui ne suivrait que le poste et ignorerait le mode forcé, est refusée. Un état
  qui change de couleur — survol, page courante — a son propre jeton (`--primary-hover`),
  mesuré comme les autres.
- **Ajouter une couleur, c'est ajouter un jeton** : sa valeur claire et sa valeur sombre dans
  `:root`, son nom dans `@theme inline` (`--color-<nom>: var(--<nom>)`), et chaque paire
  texte et fond qu'il forme dans `frontend/src/theme/contrast.test.ts` ; un composant emploie
  ensuite sa classe (`bg-<nom>`). Jamais une couleur dans un composant : ni une classe de la
  palette de Tailwind, retirée du thème — `bg-blue-500` ne produit rien —, ni une valeur
  arbitraire d'un utilitaire de couleur (`bg-[#027dc6]`, `bg-[red]`) — une longueur ou un
  nombre passent, `ring-[3px]` —, ni une variable entre parenthèses (`bg-(--x)`,
  `font-(family-name:--x)`), que personne n'a mesurée, ni une propriété arbitraire qui peint ou une variable
  (`[color:…]`, `[--primary:…]`), ni `color-mix(`, ni une couleur écrite dans une chaîne,
  dans un `style` ou dans l'attribut d'un SVG. Une police s'ajoute de même, par un jeton
  `--font-<nom>`.
- **Le contraste** d'un texte sur son fond atteint 4,5:1, celui de ce qui montre un contrôle —
  bord d'un champ, anneau du focus — 3:1, dans les deux modes (WCAG AA, §3.6).
- **Un signalement passe par `Signal`** (`frontend/src/components/signal/`), et seulement
  par lui (WF-IHM-0070) : il reçoit une `AlertZone` du contrat et la rend par une forme
  Lucide, son libellé du catalogue (`enums.AlertZone.<zone>`) et son jeton,
  `--signal-<zone>`, dans une seule table typée sur `AlertZone`. **Une zone vient du
  serveur**, qui classe selon les seuils du référentiel : le front n'en déduit jamais une
  d'une valeur (WF-ARC-0020). Une zone nulle ou absente ne rend aucun `Signal` ; la valeur
  dit qu'elle manque (`ComputedIndicator`) ; jamais `?? "nominal"`. Les jetons de signalement
  sont mesurés comme les autres, et de plus en niveaux de gris et vus d'un protanope et d'un
  deutéranope (`contrast.test.ts`) ; l'alerte y ressort le plus de la page dans les deux modes —
  la plus sombre en clair, la plus lumineuse en sombre —, le nominal le moins. Hors de `src/components/signal/`, un utilitaire de couleur qui nomme
  un jeton de zone (`bg-signal-alert`, `text-signal-watch`) est refusé : `SIGNAL_SYNTAX` de
  `frontend/eslint.config.mjs`, `make lint-front`, éprouvé par `colour-guard.test.ts`.
  Qu'aucun écran ne distingue deux états par la seule couleur — une pastille, une ligne
  teintée sans forme ni texte —, c'est pour le reste la revue qui le tient ; les tests de
  `Signal` le prouvent pour le composant.
- **L'état d'un projet passe par `ProjectStateBadge`** (`frontend/src/components/projects/`,
  #523), partout où un écran le montre — l'accueil, la liste du portefeuille, la page, les
  paramètres et le cycle de vie d'un projet : une pastille remplie du jeton de son état,
  `--state-<état>`, son texte du jeton `--state-<état>-foreground`, dans la palette que l'auteur
  a validée — gris clair pour Créé, bleu pour Chiffrage, vert pour En cours, gris foncé pour
  Terminé, orange pour Perdu, rouge sourd pour Abandonné —, et toujours le mot de l'état et son
  icône, propre à chacun et distincte des formes de `Signal`. `contrast.test.ts` mesure le texte
  de chaque état sur sa pastille, et tient chaque jeton d'état à l'écart des jetons de zone :
  un état ne se lit pas comme une alerte.
- **shadcn/ui partout où un composant existe** : un composant s'ajoute en copiant son source
  dans `frontend/src/components/ui/` (`frontend/components.json` en donne les chemins), et
  seulement quand un écran l'emploie ; ce qu'il offre et qu'aucun écran n'emploie — une
  variante, une pièce — ne se copie pas. Copié, il est du code du dépôt, soumis à toutes ses
  règles : en-tête, lint, JSDoc, couverture, textes par le catalogue, couleurs par les jetons
  — ses classes se récrivent sur les jetons de la charte (`bg-popover`, `bg-sidebar-accent`),
  et un jeton qu'il attend et que la charte n'a pas s'y ajoute, mesuré. Une variable CSS ne se
  pose pas dans un `style` : la charte la déclare (`--sidebar-width`). Radix, son socle, vient
  du paquet `radix-ui`, un seul, examiné pour la garde réseau. Un composant qui en passe un
  autre à un composant client depuis un composant serveur lui passe un élément, jamais une
  fonction — une icône se remet dessinée (`commandIcon`).
- **La mise en page** suit la maquette validée par l'utilisateur (EP-02, « Charte
  graphique ») : la barre latérale est le Sidebar de shadcn/ui, repliable en rail d'icônes dont
  chaque entrée garde son nom et le montre en infobulle ; la barre du haut porte le fil
  d'Ariane, la recherche, les tâches de fond et, à droite, le bouton de l'avatar qui déroule le
  menu du compte (DropdownMenu). Un écran se construit sur le gabarit de
  `frontend/src/components/shell/page-header.tsx` : `Screen`, son `<main>`, et `PageHeader`,
  le titre et l'icône de sa fonction, une ligne dessous, ses commandes à droite.
- **La densité** : les grilles et les listes sont denses — le plus d'informations sous les
  yeux —, les écrans d'indicateurs aérés ; chaque fonction a la sienne, dans une table typée
  (`FUNCTION_DENSITY`, `function-display.ts`), que `Screen` et `PageHeader` reçoivent.
- **Une icône Lucide sur chaque entrée de navigation, chaque bouton et chaque nature de
  ligne.** Pour les fonctions, les blocs, les commandes, les pages du compte, les natures de ligne,
  les modes de planification et les états d'avancement, elle est tirée d'une table typée sur ce qu'elle représente — `FUNCTION_ICONS`,
  `GROUP_ICONS`, `PROJECT_COMMAND_ICONS` et `REVISION_COMMAND_ICONS`, `ACCOUNT_ICONS`,
  `ROW_NATURE_ICONS`, `SCHEDULING_MODE_ICONS` et `PROGRESS_ICONS` —, de sorte qu'une valeur ajoutée sans icône casse le typage ; ailleurs — un
  bouton de la coquille, un avis, une page système —, elle est posée en ligne. Une icône à côté de son texte est `aria-hidden` ; une
  icône seule porte un nom — le bouton qui la porte, ou l'icône elle-même (`role="img"`), la
  nature d'une ligne dans sa cellule.
- **La sobriété** : aucun ornement hors des icônes — ni dégradé, ni ombre décorative, ni
  transition, ni animation, hors la pulsation du squelette de chargement, qui dit un état et
  s'arrête quand le poste demande moins de mouvement ; une seule ombre, `shadow-md`, sur ce qui
  flotte au-dessus de la page (un menu), pour l'en détacher. `src/components/ui/sobriety.test.ts`
  le vérifie pour les composants copiés. Un état se dit en mots — un badge, une pastille —, jamais par la seule
  couleur.
- **Le logo et le favicon** sont les fichiers de `docs/assets`, copiés à l'octet près dans
  `frontend/public/` et `frontend/src/app/icon.svg` ; le logo prend sa variante sombre là où
  le mode sombre s'applique.

*Contrôles* : `make lint-front` — `no-restricted-syntax` (`COLOUR_SYNTAX` de
`frontend/eslint.config.mjs`) refuse, dans toute chaîne du code, une classe de couleur de la
palette, une valeur arbitraire d'un utilitaire de couleur qui n'est ni une longueur ni un
nombre, une variable passée à un utilitaire de couleur ou de police, une police arbitraire, une propriété arbitraire qui peint, pose une police ou une
variable, `color-mix(`, une couleur écrite en chaîne entière et la variante `dark:` ; dans un
`style`, quelle que soit sa valeur, une propriété qui peint, borde, ombre ou pose une police,
et une variable, que la clé soit un nom ou une chaîne ; et, pour `fill`, `stroke`, `color` et
les couleurs d'un SVG, tout littéral ou gabarit sans expression autre que `currentColor`,
`none` ou `url(…)`, où qu'il soit dans la valeur, une branche comprise.
`frontend/src/theme/colour-guard.test.ts` l'éprouve sur des extraits piégés, et vérifie
qu'aucune feuille de style ne vit hors de `src/theme/`. `make test-front` —
`contrast.test.ts` mesure chaque paire de jetons dans les deux modes, `brand.test.ts`
compare les logos et l'icône à ceux de `docs/assets`. Le contraste des écrans rendus se
contrôle dans le navigateur (US-0200) ; le reste de l'accessibilité d'un composant, dans ses
tests, par `expectAccessible` (`frontend/src/test/axe.ts`, axe-core sous happy-dom, qui ne
calcule pas les couleurs). Reste à la revue : une couleur bâtie par un gabarit à expressions
ou par une fonction, et un `style` ou un attribut de SVG qui reçoit une variable plutôt qu'un
objet ou un littéral écrit sur place ; et, pour la mise en page, qu'un bouton ou une entrée
porte son icône hors des tables typées — un bouton écrit à la main —, qu'aucune ombre, aucun
dégradé ni aucune animation n'orne un composant copié, qu'un écran prenne le gabarit et la
densité de sa fonction, et qu'un composant copié n'entre qu'avec l'écran qui l'emploie.

## Migrations

*À écrire* — EP-03, avec la première table et les règles de codage du SQL.

## Agents

Les agents de `.claude/agents/` — cadrage, livraison, développement et revue par langage —
suivent ce guide comme une personne, et leurs règles propres sont dans
[agents.md](agents.md) : ce qui fait foi, comment un lot se fait, où un agent s'arrête.

## Branches, lots et pull requests

Les règles sont dans le [README de la roadmap](../roadmap/README.md), sections « Lots » et
« Branches », et dans [CONTRIBUTING](../../CONTRIBUTING.md) : un lot, une issue, une branche
`lot/<identifiant>` tirée de `epic/EP-nn`, une pull request qui y revient.

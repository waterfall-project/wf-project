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
Library rend dans le document de happy-dom.

La coquille (`frontend/src/components/shell/`) tire sa navigation de
`frontend/src/navigation/functions.json` : pour chaque fonction de second niveau de la FBS,
son code, la clé de son libellé, sa route, sa portée et la permission qui la laisse
consulter ; une fonction dont la session n'a pas la permission `<fonction>.read` n'y figure
pas. La table ne porte encore que le second niveau : les feuilles adressables y entrent avec
le contrôle de complétude des écrans, que le lot EP-02/L3 (#125) ajoute. Une feuille qui a déjà
son propre écran est une feuille (`leaves`) de sa fonction, de même portée et de même
permission : les imports et exports, FBS-4.3.4, sous le planning
(`/projects/[projectId]/revisions/[revisionId]/exchanges`), et le plan de charge du projet,
FBS-4.4.4, sous le devis (`…/workload`). La navigation ne l'offre pas —
l'écran de sa fonction y mène, dans le même contexte, et son entrée est marquée courante —,
mais `readContext` la lit comme sa fonction, et le fil d'Ariane la place après elle.
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
existe dès la coquille, servie par la page d'attente `frontend/src/app/[...path]/page.tsx`,
qui répond « introuvable » quand l'API ne trouve pas le projet ou la révision ; le lot d'un
écran écrit sa page à la même route, qui l'emporte sur elle. Les pages du compte
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

L'accueil, `/`, est la liste des projets (`frontend/src/app/(home)/`, un groupe de routes pour
qu'il ait son squelette sans en donner un à toutes les pages) : filtrée par défaut sur les
projets dont l'utilisateur est contributeur, par le filtre du contrat (`is_contributor`), que
l'écran montre et qu'un lien lève — `?is_contributor=false`, sous le nom du contrat
(`frontend/src/navigation/home.ts`) — : un filtre, jamais une restriction de lecture
(WF-PRJ-0060). La barre latérale et le fil d'Ariane mènent à la liste filtrée, le choix du
projet à la liste levée, « Tous les projets » ; `/projects`, l'ancienne adresse, renvoie à
l'accueil. La liste dit combien de projets elle tient, et mène aux autres pages par la
pagination de shadcn/ui ; une page demandée au-delà de sa fin le dit, et ramène à sa dernière
page : seule une liste qui ne tient aucun projet se dit vide. Les écrans du projet lui-même — le
projet, ses paramètres avec ses sous-projets et ses contributeurs, son cycle de vie — sont en
lecture ; la sortie du cycle de vie est la seule commande qu'ils exercent (`ExitCommand`),
confirmée dans la page avant que son action serveur ne la demande.

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
qu'il montre — tous
les deux, trois, six mois ou chaque année sur une longue plage, l'année seule alors —, écrits
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

Une grille est la grille dense de `frontend/src/components/grid/` (US-0110), configurée par
écran : une `GridConfig` (`columns.ts`) nomme la clé de ses préférences, stable, ses colonnes
— clé, libellé du catalogue (`grid.columns.*`), format, alignement, largeur par défaut,
celles de ses cellules que le serveur calcule, figée ou non, colonne `sort_by` du contrat, et,
pour une colonne étroite, l'icône qui tient lieu d'en-tête et que son libellé nomme, ou ce que
rend sa cellule en place de la valeur formatée (`render`) — et, s'il y en a un, son arbre
(niveau, icône de nature par `RowNatureIcon`). La configuration lit les lignes par des fonctions : elle se remet à
`DenseGrid` dans un composant client propre à l'écran (`estimate-grid.tsx`,
`planning-grid.tsx`), et la page, serveur, ne lui passe que des données — la structure lue et,
de chaque nœud, les seuls champs que la grille lit : ceux de toute grille (identité, version,
champs calculés, numéro, niveau, nature, libellé) et ceux de ses colonnes, que nomme sa
configuration (`ESTIMATE_FIELDS`, `PLANNING_FIELDS`). La page les demande à `listNodes`
(`fields`, `nodeFieldNames` : un champ d'une facette sous son nom, `task.label`) et les projette
encore (`projectNodes`) : un serveur peut rendre plus qu'on ne lui demande — le faux back rend
son exemple entier —, et les six mille nœuds entiers pèsent six mégaoctets et demi dans la page,
projetés, de quarante-cinq à soixante pour cent ; la lecture de l'écran (`readGridScreen`) ne rend que les lignes
projetées et les totaux, jamais la réponse entière. Une colonne qui lit un champ nouveau l'ajoute à cette liste : le
typage de la ligne le demande, et `projection.test.tsx` vérifie que la grille lit la même chose
de la ligne projetée que du nœud entier, et que la page demande ce qu'elle projette. Le calculé
se lit cellule par cellule (WF-IHM-0030, `computed-nodes.ts`) : un champ qu'aucune écriture ne
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
non ; un refus du serveur, ou l'API injoignable, se disent par `OutcomeNotice`. Le front ne lit aucune règle du
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
servent qu'au choix d'une saisie, offerte seulement sur un objet qu'elles connaissent. Ce qu'une
écriture rend se lit comme la grille le lit (`nodesWritten`) : les nœuds écrits et leurs ancêtres
entiers, des tâches redatées la part de leur calendrier qu'elle montre (`rescheduled`), des lignes
et des tâches déplacées dans le temps la part de leurs montants qu'elle montre (`reinflated`).
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
numéro et le libellé à son début. La grille prend la hauteur que lui laisse son écran : un
écran de grille est un `Screen` qui remplit la fenêtre (`fill`), la page bornée à sa hauteur
(`ShellFrame`), et la grille s'y réduit de la hauteur de ses lignes jusqu'à un plancher —
aucune hauteur n'y est calculée d'après ce qui la précède ; une fenêtre trop basse pour ce
plancher fait défiler la page. Colonnes masquées, largeurs et tri sont une préférence
d'affichage (`settings.ts`, WF-IHM-0060) : lues de la session, la grille remplacée entière à
chaque écriture et ce qu'elle ne règle pas renvoyé tel quel. Une colonne ou une largeur
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

L'écran des risques, `…/revisions/[r]/risks` (`frontend/src/components/risks/`), lit chacune de
ses opérations dans la révision de sa route (`revision_id`) : les totaux des provisions des
risques retenus, par état et le total général, tels que le serveur les rend ; le filtre par
état, des boutons pressés qui n'écrivent que l'adresse (`states`, sous le nom et la forme du
contrat) ; la grille dense, une configuration de plus (`risk-grid.tsx`), en lecture, où la
gravité et la provision sont des colonnes calculées entières — le contrat ne leur nomme aucun
champ de nœud, et leur refus dit seulement que la valeur est calculée (`field` rend `undefined`,
constat de l'EPIC) — et la case de matrice une colonne de `Signal` ; la matrice, ses axes nommés
par les bornes que rend le serveur, chaque case par son signal et son nombre de risques ; et,
quand l'adresse nomme un risque (`risk`), son détail : notes, ligne de provision présente ou
retirée à la survenance, historique des réexamens. Le libellé d'un risque est un lien hors de la
tabulation : la grille suit le lien d'une cellule qui n'est pas saisie à Entrée
(`grid-keyboard.ts`).

L'écran des coûts réels, `…/revisions/[r]/actual-costs` (`frontend/src/components/costs/`), lit
ceux du projet — ils ne sont pas versionnés, la révision de la route n'est que le contexte du
bandeau — page par page, comme le serveur les pagine (`offset`, `listActualCosts`) : les trois
totaux des lignes retenues et la date du dernier import, tels que le serveur les rend ; les
filtres par périmètre, par sous-projet — celui du contexte de lecture, `subproject_id` — et par
période des pièces, qui n'écrivent que l'adresse, sous les noms du contrat, et ramènent à la
première page ; la grille dense en lecture (`cost-grid.tsx`), sans recherche — l'opération n'en
a pas : une configuration la retire par `searched: false` —, chaque ligne avec son sous-projet
nommé par le serveur, son périmètre en mots et les colonnes conservées du fichier telles
qu'importées ; et le journal des imports, paginé à part (`imports_offset`). Un tri ou une
recherche changés ramènent toute liste paginée à sa première page (`sortHref`, `searchHref`).
Un lien de page, comme le libellé d'un risque, part de la dernière adresse demandée
(`usePendingLink`) ; quand elle lit les coûts autrement que la page montrée — un filtre ou un tri
en attente —, il mène à leur première page.

Les écrans du référentiel (`frontend/src/app/reference/`, `frontend/src/components/reference/`,
US-0250) sont hors projet, aux routes de leurs fonctions. Les paramètres de coûts disent la devise
de l'installation et présentent la grille des taux horaires — une configuration de plus de la
grille dense (`rate-grid.tsx`), une ligne par catégorie de main-d'œuvre, une colonne par année de
la réponse, dont l'en-tête est l'année elle-même (`GridColumn.heading`) —, cherchée par le serveur
(`search`) et sans tri ; une cellule saisie part seule par `setHourlyRate`, sans version au premier
taux d'une année, avec celle du taux lu pour une correction, et le taux répondu prend sa place. La
saisie n'est offerte qu'à une session qui porte `cost_settings.write` (`platformOffer`). À côté,
les natures et les catégories de coût — l'écran ne remplit la fenêtre qu'à partir de la grande
largeur (`Screen`, `fillWide`) : en fenêtre étroite, la grille et les listes s'empilent et la page
défile ; les paramètres de ressources présentent l'organisation,
les rôles, les calendriers et les unités de durée, ceux des risques les bornes de la matrice, ceux
des indicateurs les seuils des indices et le délai entre deux revues. Un objet rattaché se nomme
par le libellé que le serveur résout à la lecture, actif ou désactivé — jamais en rapprochant des
listes dans le front ; une section se nomme par `aria-label` (#251).

Les écrans de l'administration (`frontend/src/app/admin/`, `frontend/src/app/system/`,
`frontend/src/components/admin/`, US-0250) sont hors projet eux aussi, et en lecture seule : les
comptes, désactivés compris (`include_inactive`), chacun avec ses rôles et son nœud nommés par le
serveur ; les rôles d'habilitation et la matrice des permissions — une ligne par permission dans
l'ordre du catalogue, les permissions consécutives d'une même fonction de second niveau, ou d'une
même nature hors fonction, groupées sous un en-tête de groupe (`scope="rowgroup"`), une colonne par
rôle, accordée ou non dite par un mot ; l'état du système ; les sauvegardes et leur planification,
sans aucune commande. Une liste que le serveur pagine — comptes, sauvegardes — dit combien elle en
porte et mène aux pages voisines par `offset` (`ListPages`, `offsetOf`), sans jamais montrer une
page pour le tout ; elle ne se dit vide que si elle ne tient rien (`meta.total`), et une page
demandée au-delà de sa fin le dit et ramène à la dernière. L'heure d'une sauvegarde planifiée
s'affiche telle quelle, « heure de la plateforme », le contrat n'en disant pas le fuseau.

L'écran des imports et exports, `…/revisions/[r]/exchanges` (`frontend/src/components/exchanges/`,
US-0260), est la feuille FBS-4.3.4 du planning, dont l'en-tête y mène dans le même contexte, comme
celui de l'écran des coûts réels ; un
import s'applique pourtant à la révision en cours, créée au besoin (WF-INTF-0090), quelle que soit
la révision lue. Un import se fait en deux temps (WF-ARC-0100) : la commande de sa nature ouvre dans
la page le choix du fichier — et, pour une extraction de coûts réels, la période qu'elle couvre —,
qu'une action serveur dépose (`uploadFile`) puis analyse (`openImport`) ; un fichier de plus de
10 Mio, la plus grande taille d'import du §4.6.2, est refusé dans la page, et la borne des actions
serveur de Next est réglée un peu au-dessus (`next.config.ts`, #324). La tâche de l'analyse va au
suivi de la coquille, et l'adresse nomme l'import (`import`, un identifiant ou rien), dont la page lit
le compte rendu (`getImport`) — lignes lues, motifs de confirmation, lignes rejetées par leur place
et leur motif, rendu comme un refus depuis son code et ses paramètres (`problemMessage`), écarts —,
dans l'ordre reçu. Les commandes d'un compte rendu sont les siennes : un autre import montré les
remplace. L'application n'est offerte qu'à un import analysé, et ne part qu'une fois confirmée dans
la page ; sa tâche va au suivi. L'abandon ramène à l'adresse de départ, si l'écran montre encore cet
import. Les imports sont offerts comme le serveur offre leur commande (`importOffers`) : les coûts
réels par `import_actual_costs` du projet, les autres par la commande `edit_*` de la révision en
cours (#318). La liste des imports, paginée par le serveur (`offset`, `ListPages`), mène au compte
rendu de chacun ; la demande d'export part pour la révision lue — l'image de l'arborescence au
niveau demandé —, et le suivi offre de télécharger le résultat d'une tâche qui en a un : le serveur
de Next le lit (`getBackgroundTaskResult`) et le transmet en pièce jointe, sans sa longueur, que
`fetch` a décodée, à la route `/tasks/[taskId]/result` (#323).

Les écrans du portefeuille, `/portfolio/…` (`frontend/src/components/portfolio/`, FBS-2), sont
hors projet : chacun lit sa vue sur le périmètre de l'adresse, sous les noms du contrat — les états
retenus (`states`), la période (`from`, `to`), la date de calcul (`as_of`) et le nœud d'organisation
(`org_node_id`), offert par `listOrgNodes`, chaque nœud nommé avec son parent comme le serveur les
rend —, de ce périmètre ce que l'opération prend (`perimeterQuery`, `Takes`). Un état se montre
pressé comme l'adresse le demande, ou, quand elle n'en nomme aucun, comme le serveur les a retenus
(`scope.states`) : le front ne suppose aucun défaut. Sous le titre, le périmètre que le serveur a
retenu et la date de calcul de la vue, `scope.as_of` (`PortfolioHeader`), que portent tous ses
chiffres. La liste des projets (FBS-2.1) est une configuration de plus de la grille dense, triée,
cherchée et paginée par le serveur, sa ligne de totaux le nombre de projets retenus
(`meta.total`), sous la valeur du portefeuille. Les six autres vues (FBS-2.2 à FBS-2.7) montrent ce
que le serveur calcule : le plan de charge agrégé et les décaissements prennent en outre l'horizon
(`horizon_months`) et, pour le premier, le seuil de sous-charge (`under_load_threshold`),
paramètres de la vue et non préférences (WF-PTF-0060) : le menu propose quelques valeurs, mais toute
valeur de l'adresse que le contrat prend — un horizon de 1 à 240 mois, un seuil en `Percent` — est
envoyée et se montre choisie ; sans seuil dans l'adresse, le menu montre celui que le serveur a
retenu (`under_load_threshold` de la réponse), comme les états. Chaque projet nommé — libellé de la liste, risque le plus lourd, signal de santé —
ouvre le projet (WF-PTF-0030). Les zones d'indice, de charge et de santé sont celles du serveur,
par `Signal` ; l'évolution trimestrielle des indices et les décaissements sont des figures de
`Chart`, sans export (#312).

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
nomme — par son en-tête, ou par son libellé du catalogue (`enums.NodeColumn`).
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
contenu : la colonne visée part sous son nom de `sort_by`, et la confirmation porte la version
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

Une commande s'affiche par `Command` de `frontend/src/components/commands/` (WF-IHM-0090) :
absente quand l'objet ne la liste pas dans `available_commands` — le serveur n'y met que
celles que l'appelant a la permission d'exercer, et le front ne sait pas quelle permission
garde quelle commande —, présente et disponible, ou présente et indisponible, marquée
`aria-disabled` et décrite par le texte visible des conditions qui lui manquent
(`enums.CommandCondition.*`). `LifecycleCommands` rend, dans l'ordre du serveur, les sorties
du cycle de vie d'un projet — les autres commandes du projet appartiennent aux formulaires de
leur domaine —, et `RevisionCommands` toutes celles d'une révision, chacune selon son
`is_available` et ses conditions — une révision marquée les liste indisponibles, faute d'être
en cours d'élaboration — ; `findOffer` en tire une seule. Hors projet — comptes, rôles, référentiel,
sauvegarde —, `platformOffer` suit la permission de modification d'une fonction de portée
`platform` (`PlatformFunction`) dans `Session.permissions`, ou `platform_restore` pour la
restauration. Griser n'est qu'une
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
au lieu d'être rendue à la requête, le fait échouer (#131) ; au palier complet, les parcours
de bout en bout le construisent (`make e2e`). `make typecheck-front`,
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

Les volumes du §4.6.2 ne s'écrivent pas à la main : `make mock-data` (`wftools.mockdata`, le
portefeuille dans `wftools.mockportfolio`, la structure dans `wftools.mockstructure`) les engendre dans `fixtures/api/volume/`, qu'on ne
retouche pas — la structure de mille tâches et de cinq mille lignes, premier exemple de
`listNodes`, et les indicateurs de son devis, premier exemple de `getEstimateIndicators`,
sommés sur les mêmes lignes, pour que la grille et les indicateurs servis disent le même
total ; ce dont dépend la date de fin de sa première récapitulative, ses subordonnées directes
nommées de la même structure, premier exemple de `getComputedValueDependencies`, que le refus
d'une saisie lit dans les parcours ; les trois cents projets de `getPortfolioProjects`, et les vues
du portefeuille qui se somment de leurs lignes — la valeur, la performance, la structure des coûts et
les risques —, les deux cents catégories de
`listCostCategories`, quinze ans de taux de `listHourlyRates` et la grille des taux horaires de
`getHourlyRateGrid`, cent cinquante catégories sur quinze ans. Les exemples nommés
(`witness`…) restent pour les tests de composants. Les indicateurs du projet
(`getProjectIndicators`) et la ligne du projet témoin dans le portefeuille restent ceux du
témoin, que l'outil lit dans leurs fixtures : ils ne sont pas tirés du volume. Les volumes
restent dans l'univers des autres exemples — le projet, sa révision, ses sous-projets, ses
catégories et ses rôles gardent leurs identifiants, et ce que disent le projet témoin, l'offre
et les libellés de l'univers se lit dans leurs fixtures, jamais recopié —, et l'engendrement
ne lit ni l'horloge ni le hasard : chaque valeur tirée vient de l'empreinte d'une graine fixe
et de ce qu'elle décrit, et deux engendrements écrivent les mêmes octets. Un exemple de volume
s'écrit une ligne par élément, pour qu'un changement se lise dans le diff. Les repères que
lisent les parcours de bout en bout — numéros de ligne, libellés, totaux — sont fixés par
`test_the_marks_the_journeys_read` (`tools/tests/test_mockstructure.py`) pour la structure, et
ceux du portefeuille par `test_the_marks_the_portfolio_journey_reads`
(`tools/tests/test_mockdata.py`) : un changement du générateur qui les déplace échoue là, avant
les parcours.

`make mock-spec` dérive du contrat la variante que prism sert : chemins sous le préfixe du
serveur, `/api/v1`, que prism ignorerait, et aucune session exigée — le faux back accorde
celle dont part la maquette (EP-02). Rien d'autre ne change.

- `make mock` : le faux back seul, sur `http://localhost:4010`.
- `make dev` : le front (`http://localhost:3000`) contre le faux back, par
  `deploy/compose/compose.dev.yaml`. Le front ne connaît que l'adresse de l'API,
  `WATERFALL_API_ADDRESS` : à partir d'EP-03, la même variable désigne le vrai service.

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
  outils et appelle `make check-<famille>`. `repo` s'exécute sur toute modification.

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
lancer, et publie le relevé — chaque exigence F0 avec les tests qui la couvrent — dans le
résumé du travail de la chaîne ; une citation d'un identifiant inconnu, ou d'un indice de
révision que le document a dépassé, le fait échouer. `make requirements-release` échoue en
plus sur toute exigence F0 non couverte, en la nommant : c'est la commande de la
publication d'une version.

### Un parcours de bout en bout

Un parcours s'écrit sous `frontend/e2e/`, en Playwright, et cite dans son titre l'exigence
qu'il couvre : `test("… [WF-QUA-0050-A]", …)`. Il trouve les éléments par leur rôle et leur
nom accessible (`getByRole`), comme un utilisateur les voit, jamais par une classe CSS.

`make e2e` : Playwright démarre le faux back (`make mock`) et le front, joue les parcours
dans Chromium, puis arrête les deux — il signale leur groupe de processus entier, sans quoi
les serveurs que `make` et `pnpm` lancent survivraient. Il démarre toujours ses propres
serveurs, sur des ports à lui — 4110 pour le faux back, 3100 pour le front de développement,
3101 pour le front construit —, jamais ceux de `make dev`, et son faux back sert une variante
du contrat écrite sous `frontend/.e2e/`, que `make dev` ne lit pas : un port déjà pris fait
échouer le lancement en le disant. `E2E_API_PORT`, `E2E_FRONT_PORT` et
`E2E_PRODUCTION_PORT` déplacent les ports, pour deux copies du dépôt sur un même poste ; un
port qui n'est pas un entier de 1 à 65535 est refusé. `make e2e-browsers` installe le
navigateur. À partir d'EP-03, les mêmes parcours se jouent contre le vrai service en
posant `WATERFALL_API_ADDRESS` : le harnais ne démarre alors aucun faux back.

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
d'eux échoue —, et sans trace. Elle tourne donc là où tournent les parcours, au palier complet
de la chaîne ; sur un poste, `make e2e`, ou la mesure seule,
`pnpm exec playwright test --project production --no-deps` dans `frontend/`, qui démarre
ses serveurs comme `make e2e` — le harnais n'en réutilise aucun.

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
  (`params.conflicting_object_id`) nommé quand l'écran le connaît, par `names` ; sur 401, le
  lien vers la connexion ; l'API injoignable annoncée, jamais un écran blanc. La connexion
  est `/login?next=<chemin et requête de l'écran visé>` (`loginHref`,
  `frontend/src/navigation/login.ts`) : la page de connexion (US-0320), la session rouverte,
  mène à `returnTarget(next)`, qui ne suit qu'un chemin du front — ni `//hôte`, ni une
  adresse d'un autre site — et ramène sinon à l'accueil.

  *Contrôles* : `make test-front` (`problem.test.ts`, `login.test.ts`) ; qu'une action
  serveur passe par `decode`, la revue.
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
  (`LocalTime`) ; un rapport — un avancement — en pourcentage, depuis sa chaîne exacte
  (`formatPercent`). En français, `Intl` sépare les milliers par une fine insécable
  (U+202F) : « 1 234,56 » ne se coupe pas en fin de ligne. L'anglais se formate en anglais
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

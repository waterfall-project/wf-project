---
id: EP-25
titre: Lire et saisir dans des écrans aérés, sobres et cohérents
statut: livré
depend_de: EP-24
famille: front, back
issue: 3195
---

# EP-25 — Refonte ergonomique

## Objet

Les essais manuels de l'auteur du 2026-11-13, sur la plateforme de service, ont jugé les écrans
serrés, sans couleur et inégaux d'une table à l'autre. Un prototype, jugé sur l'écran des paramètres
de coûts, a arrêté une direction : une barre latérale sombre, un fond gris, des sections en cartes,
un bouton de création plein dans l'en-tête de sa carte, des commandes en pastilles, une pagination
discrète, des tables plates à pleine largeur.

L'EPIC étend cette direction à tous les écrans, et vient en premier après EP-24 : les EPICs qui
suivent ajoutent des écrans, des marques et des graphiques, qui naissent alors dans la présentation
nouvelle. Il réalise aussi les phrases que la spécification 1.0.6 ajoute sur les graphiques.

## Ce qui en fait partie

- la charte : les couleurs, la barre latérale sombre, le fond gris, les cartes, les boutons et les
champs en pilule, en mode clair et en mode sombre, arrêtés sur un écran de référence — les
paramètres de coûts — que l'auteur valide avant que les autres écrans suivent (#3079) ;
- la présentation des tables plates : le bouton de création, le nombre de lignes, la pagination, les
largeurs, les pastilles des filtres actifs, et la barre des grilles arborescentes dans le même ordre
(#3071, #3072, #3073, #3075, #3077) ;
- le filtre d'état de chaque table en place de « Afficher aussi les désactivés », posé par défaut
sur « Actifs » et dit par sa pastille (#3076) ;
- la mise en page des écrans du référentiel, de l'administration, des paramètres, de l'accueil, d'un
projet et du compte (#3079, #3088, #3090), et celle des dix écrans que le service ne sert pas encore
— les sept du portefeuille, les risques et les indicateurs d'un projet, l'état du système —, contre
le faux back (décision de l'auteur du 2026-11-14, au cadrage) ;
- l'écran « Installation » de la section « Administration », qui reçoit le nom de l'entreprise, sous
une fonction nouvelle du catalogue des permissions, FBS-1.6 (#3088 ; décisions de l'auteur du
2026-11-14, au cadrage, et du 2026-11-15 : la spécification est mise à jour ensuite, #3197) ;
- le fuseau horaire de l'installation, gardé à l'amorçage, dans lequel s'entend le jour courant, et
que l'écran « Installation » montre (#2527, repris d'EP-13 ; décision de l'auteur du 2026-11-14, au
cadrage : avant que les grilles se finalisent) ;
- la page de connexion, dont le thème suit la charte nouvelle (décision de l'auteur du 2026-11-14,
au cadrage) ;
- la présentation des graphiques, et les motifs des séries passés en préférence du compte,
désactivée par défaut, qui vaut aussi pour l'image exportée (#3097, #3098 ; WF-IHM-0070,
WF-ADM-0040, WF-IHM-0130) ;
- ce qui montre qu'un traitement est en cours, et la relecture de l'écran quand il aboutit (#3103,
WF-IHM-0080) ;
- les deux parcours des paramètres de coûts mis en quarantaine contre le service : leur cause, puis
leur réactivation, par le premier lot (#3190, #3191) ;
- les mineurs ouverts sur les écrans que l'EPIC reprend ;
- les constats « à trancher » que les lots d'écran ont relevés sur des composants communs, et la
dette de tests qu'ils laissent, soldés en fin d'EPIC (US-2310, décision de l'auteur du 2026-11-15).

## Ce qui n'en fait pas partie

- la comparaison dans les grilles, son bandeau et ses marques — EP-27 ;
- la refonte de l'écran « Révisions » — sa structure, la désignation de la référence en colonne de
l'historique, le retrait de la comparaison : EP-27 (#3177, #3180) ; EP-25 n'en met que les sections
en cartes (décision de l'auteur du 2026-11-14, au cadrage) ;
- le détail du plan de charge et la projection de dépenses — EP-10 ;
- la performance des grilles, et l'ouverture d'une révision qui dure dix secondes et que le front
dit « injoignable » au bout de cinq — EP-26 (#3102) ;
- le service de l'état du système, que l'API ne sert pas (`getSystemStatus`, 404) — EP-13 (#2307) ;
l'écran se met en page contre le faux back ;
- la montée vers Next 16.5, qui n'est pas publiée : #1512 reste rattaché à l'EPIC en dette
technique, sans lot (décision de l'auteur du 2026-11-14, au cadrage).

## Exigences réalisées

L'EPIC clôt WF-ADM-0200, que la spécification 1.0.7 écrit sur la décision que portait #3197 et
qu'US-2120 avait réalisée d'avance. Il poursuit WF-IHM-0130, que clôt EP-11, et réalise les phrases que
la spécification 1.0.6 ajoute à des exigences closes par des EPICs livrés — WF-IHM-0070 et
WF-ADM-0040 —, notées en écart dans les US qui les citaient (US-0160, US-0730, US-0740).

Comme EP-23 et EP-24, chaque US cite, avec tout leur Vérif, les exigences dont une phrase tient à ce
qu'elle change ; les phrases qu'elle ne touche pas sont des écarts qui disent qui les constate. Leur
portée reste celle des EPIC qui les ouvrent et les closent : `WF-IHM-0070-A` (EP-02),
`WF-IHM-0100-A` (EP-14), `WF-IHM-0060-A` (close par EP-07), `WF-REF-0150-A` et `WF-REF-0080-A`
(EP-05), `WF-ADM-0040-A` et `WF-IHM-0120-A` (EP-04), `WF-IHM-0080-A` (close par EP-09),
`WF-IHM-0090-A` (EP-02), `WF-REF-0170-A` et `WF-PLA-0130-A` (closes par EP-10), `WF-EXP-0020-A`
(close par EP-07), `WF-ADM-0100-A` (close par EP-08).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | début — close en EP-11, amorcée aussi en EP-02, EP-03, EP-15 | US-2080, US-2160 |
| `WF-ADM-0200-A` | Réglages de l'installation | entière | US-2120 |

## Opérations du contrat

Déjà servies, et reprises pour ce que la refonte y change à l'écran : toute liste paginée
(US-2080) ; les lectures des listes du référentiel et des comptes, où `include_inactive` cède au
filtre d'état — `listCostTypes`, `listCostCategories`, `getHourlyRateGrid`, `listOrgNodes`,
`listResourceRoles`, `listCalendars`, `listUsers` (US-2090) ; `getBackgroundTask`,
`listBackgroundTasks`, `getBackgroundTaskResult`, `requestExport`, `markRevision`, `createRevision`,
`applyImport` (US-2170) ; `getMe`, `updateMyPreferences` (US-2080, US-2090, US-2160) ;
`setTaskProgress`, `requestExport` et les autres opérations qui datent au jour courant (US-2200).

Quatre modifications du contrat, chacune par une issue `contract` tranchée par l'auteur et une entrée
de `docs/api/DECISIONS.md` (« La règle d'après le gel »), faite avant le code qui la consomme :

- la préférence des motifs des séries dans `DisplayPreferences` (#3098, décisions de l'auteur du
2026-11-13) — US-2160 ;
- la fonction « installation » : ses deux permissions dans `PermissionCode`, et le nom de
l'entreprise écrit sous elle et non plus sous `cost_settings.write` (`updateReferenceSettings`) —
US-2120, sur la décision de l'auteur que #3197 porte ;
- le fuseau horaire de l'installation, qu'aucune opération ne rend aujourd'hui, rendu par
`getInstallation` — US-2200 ;
- un exemple de `setOrgNodeActivation` qui désactive un nœud et deux niveaux de descendants (#2270)
— US-2180.

## Préalables

- EP-24 livré (fait, 2026-11-14).
- Le prototype des essais n'est pas une branche du dépôt : `essais/EP-24` n'existe ni sur le poste
ni sur GitHub (constaté au cadrage, 2026-11-14). La référence est ce que les issues ont écrit des
essais et des décisions — #3071 à #3079, #3088, #3090, #3097 —, couleurs comprises, pour le mode
clair et l'écran des paramètres de coûts. Les deux premières US de présentation (US-2070, US-2080)
refont cet écran ; **l'auteur le valide sur la plateforme de service, en mode clair et en mode
sombre, avant le premier lot d'un autre écran** (décision de l'auteur du 2026-11-14, au cadrage).
- La fonction « Installation » de l'arborescence fonctionnelle (WF-ADM-0100), FBS-1.6, est décidée
par l'auteur (2026-11-13, #3088) ; US-2120 la réalise sans attendre la révision de la
spécification, qui vient dans un second temps par l'issue `specification` #3197, sans révision
propre à ce constat (décision de l'auteur du 2026-11-15).
- Une branche `epic/EP-25` existe déjà sur le dépôt, identique à `main` au cadrage (a31b569f) : le
premier lot la reprend de `main` à jour plutôt que de la tirer.

## Définition de fini

- l'écran des paramètres de coûts est validé par l'auteur, en mode clair et en mode sombre, et
chaque écran suit la direction qu'il arrête, dans les deux modes, sans régression des audits
d'accessibilité — les écrans que le service ne sert pas, contre le faux back ;
- la page de connexion suit la même charte ;
- sur une installation au fuseau de Paris, une tâche terminée à 0 h 30 est datée du jour, non de la
veille, et l'écran propose ce même jour ;
- les deux parcours `reference-costs.spec.ts` en quarantaine sont rejoués contre le service (#3190,
#3191) — ou, si US-2060 établit que leur cause est la charge de la file sur l'API à un seul
processus, ils restent sautés contre le service, et leur réactivation passe à la définition de fini
d'EP-26 avec #3172 (décision de l'auteur du 2026-11-14, au cadrage) ;
- `make build-openapi`, `make inventory`, `make client-up-to-date` et
`make server-models-up-to-date` passent, et `docs/api/DECISIONS.md` a ses quatre entrées ;
- `make roadmap` et `make requirements` passent ;
- chaque issue de « Constats reçus » est fermée par la fusion de son lot, ou reportée par sa
décision ; #1512 reste ouverte, en dette technique ;
- `make check-all` passe.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC. Chacun porte ici l'US qui le reprend.

- #1512 — front : retirer `prefetch={false}` du menu du compte à la montée vers Next 16.5, et deux
mineurs de commentaire (US-0590e, tour 2) — dette technique, sans lot : Next 16.5 n'est pas publiée
(décision de l'auteur du 2026-11-14) ;
- #1985 — front : le panneau d'aide de chaque écran n'est plus audité que sur l'écran de référence —
option 1, la limite écrite au guide (décision de l'auteur du 2026-11-14) : US-2070 ;
- #1997 — front : la citation du test de la rangée vide, la lecture unique de la puce en e2e, un
commentaire à 101 colonnes (revue 2 d'US-1230/L2) — les deux points qui restent : US-2150 ;
- #2050 — front : deux mineurs de la revue 2 d'US-1170/L4 — le nom sans initiales vérifié
exactement, un commentaire elliptique — close sans suite le 2026-11-14 ;
- #2121 — front : le refus d'un nœud désactivé se dit par le message générique, pas par son champ :
US-2180 ;
- #2260 — front : une ligne du référentiel en cours d'écriture garde ses commandes offertes, et la
suivante part d'une version périmée (412) : US-2180 ;
- #2266 — front : la correspondance des coûts réels perd le focus et la saisie en cours quand la
relecture remonte le formulaire : US-2180 ;
- #2267 — front : la correspondance offre un 21ᵉ intitulé pour une colonne lue, et son refus n'est
dit à aucune liste : US-2180 ;
- #2268 — front : la règle locale des seuils d'alerte juge leur ordre hors de ]0, 1[, ce que le
serveur ne fait pas : US-2180 ;
- #2270 — front : le remplacement des descendants d'un nœud désactivé par la cascade n'est éprouvé
par aucun test : US-2180 ;
- #2424 — front : deactivate de reference-manager.spec.ts peut recliquer sur une réponse lente :
US-2060 ;
- #2527 — back : le jour courant pris en UTC, faute de fuseau de l'installation (WF-EXP-0020,
WF-PLA-0130) — repris d'EP-13 au cadrage (décision de l'auteur du 2026-11-14) : US-2200 ;
- #3071 — front : le bouton de création d'une liste est repoussé au bout de la page, loin de sa
table (WF-IHM-0060) : US-2080 ;
- #3072 — front : le nombre de lignes d'une table plate est dit deux fois, dans sa barre et dans sa
ligne de total (WF-IHM-0060) : US-2080 ;
- #3073 — front : la pagination d'une table plate n'offre que « Page suivante », sans dire où l'on
est (WF-IHM-0060) : US-2080 ;
- #3075 — front : les tables plates d'un même écran ont des largeurs très différentes (WF-IHM-0060)
: US-2080 ;
- #3076 — front : « Afficher aussi les désactivés », bouton de l'écran, fait double emploi avec le
filtre « État » de chaque table (WF-REF-0150, WF-IHM-0130) : US-2090 ;
- #3077 — front : les pastilles des filtres actifs d'une table ne ressortent pas (WF-IHM-0130) :
US-2080 ;
- #3079 — front : l'écran des listes du référentiel est serré et sans couleur — une présentation
aérée et sobre (WF-IHM-0040, WF-IHM-0070) : US-2070 ;
- #3088 — front : la mise en page des écrans d'administration et de paramètres, d'après l'écran des
coûts (WF-IHM-0040) : US-2100, US-2110, US-2120 ;
- #3090 — front : la mise en page de l'accueil, des écrans d'un projet et du compte, d'après l'écran
des coûts (WF-IHM-0040) : US-2130, US-2140, US-2150 ;
- #3097 — front : les graphiques sont datés — une présentation moderne et sobre, les motifs sans
couleur passés en réglage (WF-IHM-0070, WF-IHM-0130) : US-2160 ;
- #3098 — spec : les séries d'un graphique distinguées sans la couleur sur préférence de
l'utilisateur, non d'office (WF-IHM-0070, WF-ADM-0040, WF-IHM-0130) — close, intégrée à la
révision 1.0.6 ; US-2160 la réalise ;
- #3103 — front : rien ne montre qu'un traitement est en cours, et l'écran n'est pas relu quand il
aboutit — l'utilisateur relance (WF-IHM-0080) : US-2170 ;
- #3125 — front : buttonVariants ne stylise pas aria-disabled, partagé par une vingtaine d'écrans :
US-2070 ;
- #3150 — front : le texte « indisponible » tronqué des commandes d'annulation, lisible en entier au
tactile par le seul tooltip : US-2080 ;
- #3163 — front : useRaise avale l'erreur après démontage sans le dire, et deux détails du test des
rôles : US-2180 ;
- #3190 — e2e : le parcours « désactive une nature depuis sa ligne » (reference-costs.spec.ts:372)
en quarantaine contre le service : US-2060 ;
- #3191 — e2e : le parcours « montre les natures et catégories désactivées et les réactive »
(reference-costs.spec.ts:470) en quarantaine contre le service : US-2060, réécrit par US-2090.

## Conception

Validée par l'auteur le 2026-11-14, au cadrage. L'EPIC est presque tout au front ; le back n'y
entre que par trois US — la préférence des motifs (US-2160), le fuseau (US-2200), la fonction
« installation » (US-2120).

### Tables et migrations

Deux migrations, dans cet ordre, la seconde attendant la première dans la chaîne d'Alembic :

- **`0029`, le fuseau de l'installation** (US-2200) : une colonne `time_zone` de `installation`,
  un texte non vide, le nom d'un fuseau de la base IANA. La ligne d'une installation déjà amorcée
  reçoit `UTC`, ce qu'elle employait de fait ; la colonne est ensuite exigée. Le nom se vérifie à
  l'amorçage, non par une contrainte : la base ne connaît pas la liste des fuseaux.
- **`0030`, les deux permissions de la fonction « installation »** (US-2120) : une migration de
  données, comme `0005` et `0006`. `installation.read` et `installation.write` entrent au catalogue
  à la place que le contrat leur donne, après `audit_log.read`, les suivantes gardant leur ordre ;
  leur `fbs_code` est `FBS-1.6`, celui que #3197 donne à la fonction. Elle les donne à tout
  rôle non supprimé qui porte les deux permissions d'administration de WF-ADM-0120 (`users.write`
  et `access_roles.write`), et à aucun autre.

La préférence des motifs n'a ni table ni migration : `display_preferences` est un document, et
`waterfall.core.users.personal` y fusionne un champ simple sans rien d'autre (comme `theme`).

### Modules du noyau touchés

| Module | Ce qui change | Ce qu'il expose aux autres |
|---|---|---|
| `waterfall.platform.installation` | `time_zone` dans la table et dans `Settings` | le fuseau, lu avec les réglages de l'installation |
| `waterfall.bootstrap` | le fuseau parmi les réglages de l'installateur, refusé s'il est inconnu, `UTC` livré par défaut ; une relance ne le change pas | — |
| `waterfall.core.projects.interface.days` | `current_day` rend le jour d'un instant dans le fuseau de l'installation, lu une fois par processus : il ne change pas après l'amorçage | la même fonction, la même signature : ses appelants ne changent pas |
| `waterfall.core.access_roles.predefined` | le rôle « administrateur » porte les deux permissions nouvelles | les rôles d'une installation neuve |
| `waterfall.core.cost_settings.interface` | le nom de l'entreprise s'écrit sous `installation.write`, non plus sous `cost_settings.write` | la table des permissions par champ de `updateReferenceSettings` |
| `waterfall.core.users.personal`, `waterfall.api.me` | la préférence des motifs, un champ simple ; son nul refusé comme celui des autres réglages | — |

Au front, par répertoire de `frontend/src` :

| Répertoire | Ce qui change |
|---|---|
| `theme/` | les jetons de `globals.css` — eux seuls portent une couleur — ; `contrast.test.ts` et `colour-guard.test.ts` suivent |
| `components/ui/` | boutons et champs en pilule, `aria-disabled` stylisé, la table simple au style des grilles, la barre latérale ; des onglets, que la bibliothèque n'avait pas encore |
| `components/shell/` | `Screen` et ses deux familles d'écrans, la carte de section, l'en-tête d'écran, le logo, la table des densités (`FUNCTION_DENSITY`) |
| `components/grid/` | la largeur d'une table plate (`dense-grid`), la barre (`grid-toolbar`), la pagination (`list-pages`), les pastilles (`filter-bar`), le filtre par défaut (`kept-filters`), les commandes d'annulation |
| `components/reference/`, `admin/`, `projects/`, `portfolio/`… | chaque écran recomposé en cartes, sans changer ce qu'il lit ni ce qu'il écrit |
| `components/chart/`, `gantt/` | la présentation commune des graphiques, les motifs sur préférence, l'export qui les suit |
| `components/tasks/`, `notices/`, `commands/` | l'attente d'un bouton, la carte d'aboutissement, la relecture de l'écran |
| `navigation/`, `help/`, `i18n/` | la fonction « installation », sa page d'aide, les libellés nouveaux dans les deux langues |

Hors du front et du back : `deploy/keycloak/themes/waterfall/login` (US-2190), et le guide
(`docs/dev/README-fr.md` et sa traduction).

### Modifications du contrat

Quatre, chacune par une issue `contract` que l'auteur tranche et une entrée de
`docs/api/DECISIONS.md`, avec ses exemples ; `make build-openapi`, `make generate-client`, les
modèles du service, la variante du faux back et `make inventory` suivent dans le même lot.

1. **`DisplayPreferences.chart_series_patterns`**, un booléen ; absent, faux (US-2160). Exemple : un
   compte qui l'a demandée.
2. **`Installation.time_zone`**, exigé, le nom IANA du fuseau, rendu par `getInstallation` sans
   session, comme la langue par défaut (US-2200). Les exemples `installation*` le portent.
3. **Un exemple de `setOrgNodeActivation`** qui désactive un nœud portant deux niveaux de
   descendants et des rôles (US-2180, #2270).
4. **La fonction « installation »** (US-2120, sur la décision que porte #3197) :
   `installation.read` et `installation.write` dans `PermissionCode` ; la description de
   `updateReferenceSettings`, où `company_name` passe sous `installation.write` ; les exemples des
   permissions, des rôles prédéfinis et du compte administrateur ; l'exemple du 403.

Les trois premières ne dépendent de rien et se font ensemble, en tête ; la quatrième suit la
décision que porte #3197, la spécification mise à jour ensuite. Aucune opération nouvelle.

### Ordre de construction

En cinq vagues, pour que quatre livreurs avancent ensemble (décision de l'auteur du 2026-11-14, au
cadrage) : ce qui ne tient à aucun écran part d'abord, les composants communs se livrent par
répertoire, et les écrans par domaine, une fois l'écran de référence validé.

1. **Ce qui ne tient à aucun écran refondu**, en parallèle : US-2060, sur l'écran tel qu'il
   est ; les modifications 1 à 3 du contrat ; le back d'US-2200 et celui d'US-2160 ; US-2180, dont
   les corrections précèdent ainsi les mises en page des mêmes formulaires — son test de la cascade
   attend l'exemple du contrat.
2. **La charte et les composants communs.** Un lot court pose d'abord les jetons (US-2070) : toute
   l'application prend les couleurs nouvelles sur `epic/EP-25` pendant que ses mises en page
   suivent, et `main` ne voit jamais cet état. Puis, ensemble, un lot par répertoire : la coquille,
   les cartes et les composants de base — `shell`, `ui` — (US-2070) ; les tables — `grid` —
   (US-2080) ; les graphiques — `chart` — (US-2160) ; les traitements — `tasks`, `notices`,
   `commands` — (US-2170). Tout composant commun qu'un écran attend est livré ici : la carte de
   section, les onglets, la table simple, la pagination, et la table des densités remplie en entier.
3. **L'écran de référence.** Un lot assemble l'écran des paramètres de coûts (US-2080), puis
   **l'auteur le valide**, en mode clair et en mode sombre : une issue
   `[EP-25] front : validation de l'écran de référence` bloque les lots de la vague 4 jusqu'à sa
   fermeture. L'attente est remplie par ce qui n'en dépend pas : US-2090, le filtre d'état, après
   l'assemblage dont elle touche l'écran ; la part d'écran d'US-2200 ; la fin d'US-2160, d'US-2170
   et d'US-2180.
4. **Les écrans, en quatre couloirs par domaine**, chacun avec ses écrans, ses composants et ses
   parcours : l'administration (US-2100) ; les paramètres applicatifs (US-2110) ; un projet et
   l'accueil (US-2130, US-2140, et les risques et les indicateurs d'US-2150) ; le portefeuille et
   l'état du système (US-2150). Les lots d'un couloir se suivent, les couloirs avancent ensemble.
   Les écrans que touche US-2090 — ressources, utilisateurs — l'attendent. US-2190, la page de
   connexion, qui ne touche pas le front, prend un créneau dès qu'il s'en libère un.
5. **US-2120**, en dernier : sur la décision que porte #3197, après US-2200 pour la chaîne
   des migrations et le fuseau qu'elle montre, après US-2100 et US-2110 qui lui laissent le nom de
   l'entreprise.

**Les constats des revues des lots livrés** (US-2080/L4 #3347, décision de l'auteur du
2026-11-14). Les revues locales des lots fusionnés des vagues 1 et 2 ont laissé seize constats
« à trancher » sur des composants communs, que les lots d'écran ne corrigent pas (« Un lot d'écran
ne touche que ses fichiers ») : le fond des cellules sur la carte (#3277) et le bord des commandes
de ligne (#3332), la colonne étirée et les parcours de la grille (#3280, #3281, #3282, #3286,
#3287), l'annulation (#3265, #3272), le squelette de chargement (#3269), la fin d'un traitement
dite deux fois (#3292) et le cadre caché du téléchargement (#3298), les champs écrits à la main
hors des pilules (#3259), un parcours intermittent des coûts (#3266) et deux retouches de tests
ou de commentaires (#3273, #3293). Un lot de correction les solde, rangé sous US-2080 sans
critère nouveau, prêt dès son ouverture et lancé avant que l'auteur juge l'écran de référence
(#3196), dont il change les cellules et le bord des commandes. Il est « pas avec » les lots qui
touchent ses fichiers : US-2090, US-2110/L2, US-2130/L3, US-2130/L4, US-2140/L1, US-2150/L2.
Tranchés par l'auteur : le bord des commandes de ligne atteint 3:1 dans les deux modes, mesuré
par `contrast.test.ts` ; la ligne sous la barre ne dit plus une fin que la carte d'aboutissement
porte ; les champs écrits à la main passent aux composants communs dans ce lot plutôt que dans
les couloirs. Écarté : #3291, la forme de citation d'un critère propre à une US, règle commune
de la chaîne, reporté → EP-28.

**Les composants communs et la dette de tests, en fin d'EPIC** (US-2310, décision de l'auteur du
2026-11-15). Les lots d'écran des vagues 4 et 5 ont relevé sur des composants communs des constats
qu'ils ne corrigeaient pas ; l'auteur les confie à une US de complément, qui se livre quand les
lots d'écran qui touchent ses fichiers sont fusionnés, par ses « Pas avec » plutôt que par des
dépendances : rien ne l'attend, et elle n'attend pas les lots qui ne la croisent pas. Aucune table,
aucune migration, aucune modification du contrat ; tout est au front, et au guide. Deux lots,
US-2310/L1 #3452 (#3404) et US-2310/L2 #3453 (les autres), « pas avec » l'un l'autre par le guide,
et sans fichier commun avec les lots d'écran encore ouverts. Ses lignes n'entrent au tableau de
#3195 qu'une fois `make tracking` doté de l'ajout d'une US (#3450, un lot court vers `main`,
décision de l'auteur du 2026-11-15) : l'outil n'ajoute un lot qu'après un lot de sa propre US.

- **L'attente retrouvée au remontage** (#3404) — `components/tasks`, `components/commands` et les
  boutons qui attendent une tâche. Le suivi des tâches de la coquille garde, avec chaque tâche qui
  court, l'objet qu'en a dit le bouton qui l'a lancée : une clé que le bouton compose de sa nature
  et de ce qu'il vise — la révision exportée ou marquée, le projet d'un import, l'installation pour
  une sauvegarde ou une lecture des comptes. La clé est gardée dans la session de l'onglet avec le
  reste de la tâche (`storage.ts`), et relue avec elle. Un bouton monté demande au suivi la tâche
  qui court pour sa clé, et attend sur elle comme sur celle qu'il vient de lancer : `useTaskRunning`
  reçoit la tâche lancée ou, à défaut, la tâche retrouvée. Tous les boutons à l'attente commune
  passent par là — marquage, exports d'une révision et de l'arbre des tâches, analyse et application
  d'un import, sauvegarde, lecture des comptes du fournisseur d'identité.
- **La carte de grille** (#3421) — `components/shell` : une carte sans titre ni commandes, qui porte
  la grille d'un écran de travail et remplit la place que l'écran lui laisse ; le titre est celui de
  l'en-tête de l'écran. Elle remplace `JournalCard` (`app/admin/audit-log/page.tsx`) et `WorkCard`
  (`work-card.tsx`, et les écrans de travail d'un projet qui l'importent). Un graphique qui se
  nomme lui-même prend la même forme, sans en-tête, et la carte de section du référentiel
  (`reference/section.tsx`) reçoit un corps vide : `ChartCard` (`portfolio/portfolio-value.tsx`) et
  `StatusCard` (`admin/platform-lists.tsx`), composées par US-2150/L2, s'y replient (#3446) ; le
  lot attend la fusion d'US-2150/L2, qui les écrit.
- **La condition d'un item de menu** (#3430) — `commands/menu-command.tsx`,
  `remaining/kanban-card.tsx` : un item indisponible suit la règle de `Command` — la condition dans
  son infobulle, et dans la région des refus quand il est pressé ; le champ `detail` de
  `MenuCommand`, que seules les cartes du Kanban emploient, disparaît.
- **La densité de l'en-tête** (#3397) — `app/screen-density.test.ts` refuse un fichier qui écrit un
  écran aéré sans écrire la densité aérée sur son en-tête.
- **Les paramètres de projets** (#3417, #3418) — `projects/contributor-commands.tsx` et
  `settings-lists.tsx` : « Modifier les contributeurs » passe dans les commandes de sa carte ; la
  page d'aide de l'écran le suit (WF-IHM-0140). `e2e/project-cards.spec.ts` mesure les commandes
  du lotissement à 1024 et 1100 points ; si elles débordent, leur passage sur une ligne monte au
  point de rupture suivant (`breakdown-commands.tsx`). L'ordre des imports de
  `subproject-commands.tsx` suit.
- **Les tests de l'accueil et le guide** (#3399) — `e2e/home.spec.ts`,
  `projects/project-list.dom.test.tsx`, `docs/dev/README-fr.md` et sa traduction.

Revérifiés au cadrage, soldés par US-2080/L4 et laissés fermés : #3259, #3265, #3266, #3272, #3273,
#3286, #3287, #3293, #3298. L'enquête d'EP-26 sur #3266 a établi ensuite sa cause réelle (#3448) :
l'aide du parcours reclique une commande d'activation occupée, et le second clic part sur la
commande opposée quand le même nœud s'inverse. Le test se corrige — `pressOnce`
(`e2e/server-action.ts`) ne reclique pas une commande occupée, le parcours attend la réponse de
l'action avant d'affirmer la ligne —, non le produit (pas de `key` sur `ActivationButton`), par
US-2110/L2 par exception, qui refait l'écran des coûts et touche son parcours ; #3396, le même
défaut sur `reference-resources.spec.ts`, revient d'EP-28 dans ce lot (décisions de l'auteur du
2026-11-15). Hors du
complément : #3416, corrigé par US-2110/L1 par exception, la barre étant celle de toutes les
grilles ; #3431, reporté → EP-28 ; #3432, abandonné.

Tranchés par l'auteur le 2026-11-15, avec les options écartées :

- l'attente vaut dans l'onglet, par le suivi des tâches. Écartés : lire aussi les tâches du compte
  sur le serveur (`listBackgroundTasks`), un appel de plus par écran pour une tâche dont la liste ne
  dit pas l'objet ; ajouter l'objet à `BackgroundTaskRef`, une modification du contrat pour un
  remontage ; garder la tâche dans l'adresse, qu'un aller-retour par la navigation perd ;
- la carte de grille est un composant à part. Écarté : un titre facultatif sur la carte de section,
  qui dissocierait de son titre le nom de sa région et la règle d'une commande pleine par carte ;
- un item de menu suit la règle de `Command`. Écarté : garder la condition sous son libellé, lisible
  dans un menu, mais une seconde règle pour une même chose ;
- la densité de l'en-tête se prouve par un test. Écarté : la rendre exigée sur `PageHeader`, une
  trentaine d'appels touchés, ceux des lots d'écran compris.

### Décisions

- **Le catalogue ne met pas deux lots « pas avec ».** Les catalogues n'ont qu'un fichier par
  langue (`messages/fr.json`, `messages/en.json`), que tout lot du front touche dès qu'il ajoute un
  libellé : la règle du README de la roadmap mettrait presque tous les lots en série. Dans cet EPIC,
  deux lots de domaines différents ne sont pas « pas avec » du seul fait des catalogues, chacun n'y
  écrivant que dans les sections de son domaine (`admin`, `reference`, `portfolio`, `grid`,
  `chart`…), loin l'une de l'autre ; tout autre fichier partagé garde la règle. Un conflit reste
  possible, et la file le rattrape. Écartés : découper les catalogues en un fichier par domaine,
  par un lot technique qui toucherait une dizaine de lecteurs et bloquerait tout le front tant qu'il
  n'est pas fusionné ; garder la règle, qui laisse un à deux livreurs occupés sur quatre (décision
  de l'auteur du 2026-11-14, au cadrage).
- **Un lot d'écran ne touche que ses fichiers.** Ce qui est commun — composants, table des
  densités, jetons — se livre en vague 2 ; un lot d'écran qui découvre un manque dans un composant
  commun ouvre un constat, il ne le corrige pas dans son couloir.
- **La couleur ne vit que dans les jetons.** La charte change `globals.css`, et les composants
  continuent de nommer un jeton. La barre latérale est sombre dans les deux modes, et porte toujours
  le logo pour fond sombre. Écarté : deux chartes côte à côte, choisies par un réglage — chaque
  écran aurait deux présentations à tenir pendant tout l'EPIC.
- **Deux familles d'écrans, dites par `Screen`.** Réglage et consultation : colonne centrée, bornée
  à 96rem, aérée. Travail — planning, devis, reste à engager, arbre des tâches, coûts réels, Kanban,
  chronologies, registre des risques, journal d'audit — : serré, la fenêtre remplie. La table des
  densités range chaque fonction dans l'une. Écarté : une largeur en pourcentage ou un plafond de
  72rem, essayés le 2026-11-13 et rejetés (#3075).
- **Une carte de section commune**, à côté de l'en-tête d'écran : titre, commandes à droite, corps.
  Elle porte la règle des commandes — une seule pleine par carte. Écarté : chaque écran composant
  sa carte, qui redéciderait la règle écran par écran.
- **La largeur d'une table est du CSS** : le cadre à la largeur de la carte, la table au plus large
  de la carte et de la somme de ses colonnes, la colonne du libellé prenant le reste, sa largeur
  choisie pour minimum. Écarté : mesurer en script, qui ferait sauter la table au chargement.
- **La pagination se calcule** de `offset`, `limit` et `meta.total`. Écartés pour l'instant : le
  saut à une page, la première et la dernière.
- **Le filtre d'état est un filtre par défaut de la grille**, par le mécanisme qui donne déjà ses
  états à la liste des projets : absent de l'adresse et des préférences, il vaut « Actifs » ; la
  pastille ôtée se garde par une valeur qui dit « tous », que le front traduit en
  `include_inactive`. Écarté : garder `include_inactive` à côté de `is_active` dans les réglages
  d'une grille — deux réglages pour une seule chose, le double emploi que #3076 retire.
- **Une barre, un ordre** pour toutes les grilles : les commandes de l'écran, la recherche,
  « Filtres », « Colonnes », « Arbre », puis l'annulation. Écarté : laisser leur ordre aux grilles
  arborescentes (décision de l'auteur du 2026-11-14).
- **Les motifs d'un graphique se décident en un point** : la préférence, lue avec le compte, arrive
  aux graphiques par leur composant commun ; les barres, les points des courbes et la légende la
  suivent, et l'export, qui redessine la même option, aussi. Le Gantt et les chronologies gardent
  leurs marques. Écartés : un bouton par graphique, et une entrée par graphique dans
  `DisplayPreferences.charts` — l'auteur veut un réglage du compte (#3097).
- **L'aboutissement d'un traitement est une carte flottante qui reste**, montée par la coquille,
  nourrie par le suivi des tâches, annoncée sans prendre le focus et notée à l'historique des
  messages comme les autres. Écartés : une carte qui s'efface, dont l'action se manquerait ; un
  bandeau, qui déplacerait la grille ; une bibliothèque de notifications, qui ne connaîtrait ni
  l'historique ni les régions d'annonce déjà en place.
- **L'attente d'un bouton est commune** : un bouton qui lance une requête ou une tâche se dit « en
  cours » de la même façon partout, par le composant des commandes. L'écran se relit à
  l'aboutissement d'une tâche de son projet.
- **Le nom de l'entreprise reste un champ de `ReferenceSettings`**, écrit par
  `updateReferenceSettings` ; seule sa permission change. La carte « Installation » lit
  `getReferenceSettings` (nom, devise) et `getInstallation` (langue, fuseau). Écartés : une
  opération `updateInstallation` et la colonne déplacée dans `installation` — une migration de
  données sans gain, les exports lisant le nom où il est.
- **La migration donne la fonction « installation » à qui administre.** La table des rôles ne dit
  pas lequel est le rôle prédéfini « administrateur » — son libellé se modifie — ; elle le reconnaît
  comme le service reconnaît un administrateur (WF-ADM-0120) : par `users.write` et
  `access_roles.write`. Écartés : la donner aussi aux rôles qui portent `cost_settings.write`, et ne
  la donner à personne (décision de l'auteur du 2026-11-14).
- **Le fuseau est fixé à l'amorçage et lu sans session.** `UTC` est la valeur livrée et celle d'une
  installation déjà amorcée : rien ne change pour qui ne choisit pas. Une plateforme existante ne
  change de fuseau qu'en se réinstallant ; l'application n'est pas déployée. Le front calcule le
  jour qu'il propose dans ce fuseau, par une seule fonction. Écartés : une opération qui rendrait le
  jour, un appel de plus par formulaire ; le jour du poste, que la spécification écarte.
- **La page de connexion recopie les valeurs des jetons** : le thème du fournisseur d'identité ne
  lit pas la feuille du front. Son CSS dit d'où vient chaque valeur.
- **La géométrie s'éprouve par des mesures, non par des images** : les parcours affirment des
  positions et des largeurs, comme `grid-frame.spec.ts` ; les audits d'accessibilité et de contraste
  se rejouent dans les deux modes. Écartée : la comparaison de captures, instable d'un poste à
  l'autre dans une file qu'EP-24 vient de stabiliser.
- **Chaque libellé nouveau est dans les deux catalogues**, et la page d'aide d'un écran dont une
  commande change de place la suit (WF-IHM-0140).

---

## US-2060 — Les deux parcours des paramètres de coûts en quarantaine : leur cause établie, puis rejoués contre le service

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : `listCostTypes`, `listCostCategories`, `setCostTypeActivation`,
  `setCostCategoryActivation`, par les parcours qui les jouent
- **issue** : #3198

**En tant que** développeur, **je veux** savoir pourquoi les deux parcours des paramètres de coûts
échouent par moments dans la file, **afin de** les rejouer contre le service avant que la refonte ne
réécrive leur écran.

**Critères d'acceptation.**

- propre à l'US : la cause des échecs de `reference-costs.spec.ts:372` et `:470` dans le job
  « service / paths » est établie sur les journaux des passages que citent #3190 et #3191, et écrite
  dans les deux issues : un état partagé entre parcours, ou la charge de la file sur l'API à un seul
  processus (#3172) ;
- propre à l'US : si c'est un état partagé, chaque parcours est isolé selon la règle d'US-1890
  (guide, « Un parcours de bout en bout »), son `test.skip(inService, …)` est retiré, et la pull
  request donne les passages de la file qui le montrent rejoué contre le service ;
- propre à l'US : si c'est la charge, les deux parcours restent sautés contre le service et joués
  contre le faux back ; #3190 et #3191 passent à EP-26 avec #3172, et leur réactivation à sa
  définition de fini (décision de l'auteur du 2026-11-14, au cadrage) ;
- propre à l'US : `deactivate` de `e2e/service/reference-manager.spec.ts` ne retente que si le clic
  lui-même a échoué, et n'accepte que la réponse de l'action qu'il a lancée (#2424).

**Notes de réalisation.** Premier lot de l'EPIC, avant toute refonte de l'écran (#3190). Le parcours
de la ligne 470 éprouve « Afficher aussi les désactivés », qu'US-2090 remplace : c'est elle qui le
réécrit sur le filtre d'état ; ici, il n'est qu'isolé.

**Hors périmètre.** Plusieurs processus pour l'API (#3172) — EP-26.

## US-2070 — La charte nouvelle : barre latérale sombre, fond gris, cartes et pilules, en mode clair et en mode sombre

- **statut** : fini
- **exigences** : `WF-IHM-0070-A`, `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** : #3206

**En tant que** chef de projet, **je veux** des écrans aérés, sobres et de couleurs accordées,
**afin de** lire et de saisir sans chercher ce qui est une commande, une section ou un état.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » :
  sur la barre latérale sombre comme sur les cartes, dans les deux modes ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » :
  `contrast.test.ts` tient chaque paire de texte et de fond des jetons nouveaux, dans les deux
  modes, et le bord des champs reste à 3:1 au moins ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- `WF-IHM-0070-A` — « Une copie d'écran en niveaux de gris laisse identifier chaque signalement. » :
  l'état « Actif » se dit par une pastille et son mot, « Désactivé » garde sa marque ;
- `WF-IHM-0070-A` — « La même zone d'indice porte la même couleur dans la liste des projets, dans
  les indicateurs du projet et dans la performance du portefeuille. » : les couleurs de signal
  (`--signal-*`) et leurs écarts pour un protanope et un deutéranope ne changent pas ;
- `WF-IHM-0070-A` — « Aucun écran ne distingue deux états par la seule couleur. » ;
- écart : `WF-IHM-0070-A` — « Avec la préférence des motifs, une copie d'écran en niveaux de gris
  d'un plan de charge laisse identifier chaque rôle ; sans elle, son infobulle et sa table des
  valeurs nomment chaque rôle. » : les graphiques sont à US-2160 ;
- propre à l'US : en mode clair, la barre latérale est bleu nuit (`#0f1b2d`, entrée courante
  `#22324b`, texte clair), le logo dans sa variante pour fond sombre, l'icône du sélecteur de projet
  lisible sur elle ; la page a un fond gris pâle (`#f3f5f8`), la barre du haut posée dessus ; la
  couleur primaire est le bleu nuit (`#14233b`), le bleu du logo ne servant plus qu'au logo ; les
  boutons et les champs sont en pilule (#3079, essai du 2026-11-13 d'après la maquette de
  l'auteur) ;
- propre à l'US : le mode sombre a les mêmes formes et ses propres valeurs, que le lot arrête et
  que l'auteur valide avec l'écran de référence ;
- propre à l'US : une section d'écran est une carte — son titre, ses commandes à droite du titre,
  son corps ; la commande principale d'une carte est pleine quand elle crée ou déclenche, une seule
  par carte, à contour quand elle modifie ; les commandes de l'écran sont à droite de son titre, à
  contour ; le plein est réservé à la commande principale, un choix courant se dit autrement
  (#3088, règles 2 à 4 ; #3090) ;
- propre à l'US : un écran de réglage ou de consultation est une colonne centrée, bornée à 96rem,
  en densité aérée ; un écran de travail reste serré et remplit la fenêtre (#3075, #3090) ;
- propre à l'US : les commandes de ligne gardent un bord, celui, clair, des tables, leur libellé en
  graisse normale (#3079) ;
- propre à l'US : `buttonVariants` donne à un bouton `aria-disabled` l'apparence d'un bouton
  `disabled`, et les classes locales qui le faisaient sont retirées (#3125) ;
- propre à l'US : le guide dit la charte nouvelle (« Charte graphique ») et, dans « Ce que le
  harnais ne prouve pas », que le panneau d'aide n'est audité que sur l'écran de référence, ses
  pages partageant leur rendu (#1985, option 1).

**Notes de réalisation.** L'écran de référence est celui des paramètres de coûts ; il n'est complet
qu'avec les tables d'US-2080, et c'est alors que l'auteur le valide (« Préalables »). Les couleurs
essayées avant la maquette — gris froids, tons chauds — sont écartées (#3079).

**Hors périmètre.** La mise en page des autres écrans (US-2100 à US-2150) ; les graphiques
(US-2160) ; la page de connexion (US-2190).

## US-2080 — Les tables plates : la création dans l'en-tête de la carte, une barre, une pagination et une largeur communes

- **statut** : fini
- **exigences** : `WF-IHM-0060-A`, `WF-IHM-0130-A`
- **opérations** : toute liste paginée (`offset`, `limit`, `meta.total`) ; `getMe`,
  `updateMyPreferences`
- **issue** : #3210

**En tant que** manager, **je veux** que toutes les tables se présentent de la même façon — où
créer, où filtrer, où l'on est dans les pages —, **afin de** ne pas réapprendre chaque écran.

**Critères d'acceptation.**

- `WF-IHM-0060-A` — « Chaque colonne d'une table plate se trie dans les deux sens. » ;
- écart : `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose de
  tri ; dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans
  déplacer les tâches. » : le tri des grilles arborescentes n'est pas touché ; constaté par EP-07,
  qui clôt l'exigence ;
- `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours visibles,
  de même que la colonne de libellé après défilement horizontal. » : une table plus large que sa
  carte défile dans son cadre, ses colonnes d'identification figées ;
- `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la
  réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. » : la
  largeur choisie pour la colonne du libellé devient son minimum, la colonne prenant le reste de la
  carte ;
- `WF-IHM-0060-A` — « Le nombre de lignes par page choisi pour une table est retrouvé à sa
  réouverture, sans changer celui des autres tables ; une grille arborescente n'offre pas ce
  choix. » ;
- `WF-IHM-0060-A` — « Le panneau des filtres d'une table plate, fermé par défaut, est retrouvé
  ouvert ou fermé comme l'utilisateur l'a laissé, sans changer celui des autres tables ; ses filtres
  actifs restent dits, panneau fermé, chacun ôtable. » : chaque filtre actif par une pastille teinte
  de la couleur primaire, son libellé et sa croix (#3077) ;
- `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les projets de cet état
  dans ses totaux. » : le nombre retenu par un filtre n'est plus dit que par la ligne de total ;
- écart : `WF-IHM-0130-A` — « Le plan de charge d'un projet exporté est une image PNG qui porte le
  nom du projet, la révision et la date de calcul ; le plan de charge agrégé exporté porte le
  périmètre et la date de calcul. » : les graphiques sont à US-2160 ;
- écart : `WF-IHM-0130-A` — « La table des calendriers ne propose aucun filtre sur les heures de ses
  jours ; elle se filtre sur ses autres colonnes. » : non touché ; constaté par EP-15 (US-0570) ;
- propre à l'US : le bouton de création d'une liste est plein, seul de son espèce, à droite du titre
  de sa carte ; une liste vide le garde (#3071) ;
- propre à l'US : la barre d'une table porte la recherche, « Filtres » et « Colonnes », à gauche, et
  aucun nombre de lignes ; le libellé du nombre, dans la ligne de total, déborde sur les colonnes
  voisines sans chiffre au lieu de se tronquer (#3072) ;
- propre à l'US : sur la grille des taux horaires, « Année » et « Ajouter la colonne », plein, sont
  à la fin de sa barre, précédés de leurs messages et de « Retirer la colonne » (#3071) ;
- propre à l'US : la pagination est à droite sous la table, discrète — texte à la taille de celui de
  la table, atténué : « Lignes par page », l'intervalle des lignes montrées (« 1–50 sur 150 »),
  « Précédent » et « Suivant » à place fixe, inertes en bout de liste, « Page n sur m » ; ses
  libellés accessibles gardent le nom de la liste (#3073) ;
- propre à l'US : une table occupe la largeur de sa carte, sans trait entre ses colonnes sauf à côté
  d'une colonne figée, la ligne sous le pointeur légèrement teintée ; sa barre et sa pagination
  suivent la même largeur (#3075, #3079) ;
- propre à l'US : les tables simples — matrice des permissions, bornes et zones des risques, seuils
  des indicateurs, historique des révisions, journal des imports — prennent le style des grilles :
  taille du texte, en-tête, absence de trait entre colonnes (#3088, #3090) ;
- propre à l'US : la barre d'une grille arborescente suit le même ordre — la recherche, « Filtres »,
  « Colonnes », puis « Arbre », à gauche —, les commandes de l'écran et l'annulation gardant leur
  place (décision de l'auteur du 2026-11-14, au cadrage) ; le texte « indisponible » des commandes
  d'annulation s'y lit en entier, au toucher aussi (#3150).

**Notes de réalisation.** Le contrat pagine par `offset` et rend `meta.total` : l'intervalle et le
nombre de pages se calculent sans le changer. Ni saut à une page donnée, ni première et dernière
page (#3073, laissés de côté). La hauteur des lignes ne change pas : la grille reste dense, et le
fenêtrage des lignes en dépend (#3079).

**Hors périmètre.** Le filtre d'état (US-2090) ; la mise en page de chaque écran qui porte une table
(US-2100 à US-2150).

## US-2090 — Le filtre « État » de chaque table à la place de « Afficher aussi les désactivés »

- **statut** : fini
- **exigences** : `WF-REF-0150-A`
- **opérations** : `listCostTypes`, `listCostCategories`, `getHourlyRateGrid`, `listOrgNodes`,
  `listResourceRoles`, `listCalendars`, `listUsers`, `getMe`, `updateMyPreferences`
- **issue** : #3220

**En tant que** manager, **je veux** régler ce que chaque table montre des objets désactivés par son
propre filtre, **afin de** ne plus dépendre d'un bouton de l'écran qui vaut pour toutes ses listes.

**Critères d'acceptation.**

- `WF-REF-0150-A` — « Un objet désactivé n'apparaît pas dans la liste par défaut, apparaît lorsque
  l'affichage des objets désactivés est demandé, et peut y être réactivé. » : chaque table s'ouvre
  sur le filtre « État : Actifs », dit par sa pastille « (par défaut) » ; « Désactivés » les montre
  seuls, la pastille ôtée les montre tous, chaque désactivé avec sa marque et « Réactiver » ;
- propre à l'US : « Afficher aussi les désactivés » disparaît des paramètres de coûts, des
  paramètres de ressources et de la gestion des utilisateurs ; une adresse qui porte encore
  `include_inactive` pour l'écran entier est ignorée (#3076, décision de l'auteur du 2026-11-13) ;
- propre à l'US : une table dont aucune pastille ne dit un filtre ne cache aucune ligne (#3076,
  essai du 2026-11-13) ;
- propre à l'US : le choix fait sur une table — « Désactivés », ou la pastille ôtée — est gardé avec
  ses autres filtres, par table et par compte ; un compte qui n'a rien choisi garde le défaut ;
- propre à l'US : une session qui ne peut pas modifier les réglages ne lit que les actifs, sans
  filtre d'état offert, comme aujourd'hui (403 sinon) ;
- propre à l'US : les listes de choix des formulaires — les natures offertes à une catégorie —
  n'offrent pas les désactivés pour autant ;
- propre à l'US : le parcours « montre les natures et catégories désactivées et les réactive »
  (`reference-costs.spec.ts`) est réécrit sur le filtre d'état ; contre le service, il suit ce
  qu'US-2060 a établi (#3191).

**Notes de réalisation.** Le contrat ne change pas : chaque lecture prend déjà `include_inactive` et
`is_active`, le second primant. Le front envoie `is_active=true` pour « Actifs », `is_active=false`
pour « Désactivés », `include_inactive=true` sans `is_active` quand la pastille est ôtée. Le défaut
suit le précédent du filtre d'états de la liste des projets (`docs/api/DECISIONS.md`, #1747). Écarté
au cadrage (2026-11-14) : une table qui montre tout sans filtre, essayée par le prototype — le Vérif
de WF-REF-0150 dit qu'un désactivé n'apparaît pas par défaut. La table des comptes garde son défaut,
tous les comptes, selon la décision « `listUsers` porte son propre `include_inactive` »
(`docs/api/DECISIONS.md`) et WF-ADM-0060 : WF-REF-0150 ne vise que le référentiel ; seuls le bouton et
la lecture de `include_inactive` y disparaissent.

## US-2100 — Les écrans d'administration en cartes : utilisateurs, rôles, sauvegardes, journal d'audit

- **statut** : fini
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre — celles que ces écrans lisent et écrivent déjà
- **issue** : #3226

**En tant qu'** administrateur, **je veux** que les écrans d'administration suivent la présentation
de l'écran de référence, **afin de** y retrouver les commandes à la même place.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » :
  sur chacun de ces écrans, dans les deux modes ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- propre à l'US : gestion des utilisateurs — la lecture des comptes du fournisseur d'identité est
  une carte, son bouton à droite de son titre, à contour, son état en corps ; « Créer un compte
  local » est plein, à droite du titre de « Comptes utilisateurs » ; la carte prend la hauteur de
  son contenu ; colonne centrée, densité aérée ;
- propre à l'US : gestion des rôles — « Nouveau rôle » est un bouton plein à droite du titre de la
  carte, qui ouvre un dialogue ; le champ en ligne disparaît ; la matrice des permissions garde son
  en-tête et sa colonne « Fonction » en vue (#3088, décision de l'auteur du 2026-11-13) ;
- propre à l'US : sauvegardes — « Sauvegarder maintenant » est pleine ; la restauration d'une autre
  installation est une carte, « Déposer » à droite du champ ;
- propre à l'US : journal d'audit — il reste serré et remplit sa fenêtre, sa table dans une carte
  sans titre de section ; le nombre d'inscriptions sous le titre est retiré, la colonne « Projet »
  n'est plus coupée (#3088, décision de l'auteur du 2026-11-13).

**Hors périmètre.** L'écran « Installation » (US-2120) ; l'état du système (US-2150).

## US-2110 — Les écrans de paramètres applicatifs en cartes : coûts, ressources, risques, indicateurs, correspondance des coûts réels

- **statut** : fini
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre — celles que ces écrans lisent et écrivent déjà
- **issue** : #3229

**En tant que** manager, **je veux** que les écrans de paramètres suivent la présentation de l'écran
de référence, **afin de** régler le référentiel sans chercher une commande d'un écran à l'autre.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » :
  sur chacun de ces écrans, dans les deux modes ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- propre à l'US : paramètres de ressources — « Nouveau nœud », « Nouveau rôle » et « Nouveau
  calendrier » sont pleins ; l'arbre d'organisation prend la largeur de sa carte, comme une table
  plate, « Arbre » avec « Colonnes » ; « Modifier les unités de durée » est à droite du titre de sa
  carte, à contour ;
- propre à l'US : paramètres de risques et d'indicateurs — la commande de modification, qui ouvre le
  formulaire de l'écran entier, est à droite du titre de l'écran, à contour ;
- propre à l'US : correspondance des coûts réels — une carte « Colonnes lues », une carte « Colonnes
  conservées » ; les champs bornés à une largeur de lecture ; « Enregistrer la correspondance »,
  pleine, au pied ;
- propre à l'US : paramètres de coûts — l'écran de référence, déjà en cartes ; le nom de l'entreprise
  et sa commande y restent, dans une carte, jusqu'à ce qu'US-2120 les porte à l'écran
  « Installation ».

**Hors périmètre.** Les corrections des formulaires de ces écrans (US-2180).

## US-2120 — L'écran « Installation » : le nom de l'entreprise, modifiable, et ce que l'amorçage a fixé

- **statut** : fini
- **exigences** : `WF-ADM-0200-A`, `WF-EXP-0020-A`, `WF-ADM-0100-A`
- **opérations** : `getInstallation`, `getReferenceSettings`, `updateReferenceSettings`,
  `listPermissions`, `getMe`
- **issue** : #3239

**En tant qu'** administrateur, **je veux** un écran « Installation » dans la section
« Administration », **afin de** corriger le nom de l'entreprise là où se règle l'installation, et non
sur l'écran des coûts, auquel il n'a pas trait.

**Critères d'acceptation.**

- `WF-ADM-0200-A` — « Le nom de l’entreprise se modifie depuis cet écran et figure sur le devis
  exporté ensuite. » : modifié depuis l'écran « Installation », sous `installation.write` ;
- `WF-ADM-0200-A` — « L’écran présente la devise, la langue par défaut et le fuseau horaire, et
  n’offre aucune commande pour les changer. » : trois valeurs en lecture seule, lues de
  `getReferenceSettings` et de `getInstallation` ;
- `WF-ADM-0200-A` — « Un utilisateur sans la permission de modifier la fonction lit l’écran sans
  commande ; sans celle de la consulter, il ne le voit pas. » : `installation.read` et
  `installation.write`, sous FBS-1.6 ;
- `WF-EXP-0020-A` — « Le nom de l'entreprise saisi à l'installation figure sur un devis exporté ;
  modifié, il figure sur le suivant. » : modifié depuis l'écran « Installation » ;
- écart : `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le
  lien produit, se connecte, porte le rôle « administrateur », et trouve les trois rôles prédéfinis
  et le catalogue des permissions. » : constaté par EP-03 (US-0420) ; le rôle « administrateur »
  d'une installation neuve porte de plus les permissions de la fonction nouvelle ;
- écart : `WF-EXP-0020-A` — « La création d'un projet est refusée et nomme les prérequis manquants,
  jusqu'à ce qu'une catégorie de coût de main-d'œuvre et un rôle de ressource aient été saisis. » :
  constaté par EP-04 (US-0920) ;
- écart : `WF-EXP-0020-A` — « Une seconde exécution de l'installation ne crée ni compte, ni
  calendrier, ni nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent,
  tant que l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » : constaté par
  EP-03 (US-0420) ;
- écart : `WF-EXP-0020-A` — « Le lien produit à l'installation est accepté plus d'une heure après sa
  production. » : constaté par EP-03 (US-0420) ;
- écart : `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %,
  50 % et 75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8, le délai six semaines, et
  le calendrier par défaut compte huit heures du lundi au vendredi et aucune le week-end. » :
  constaté par EP-05 (US-0810) ;
- écart : `WF-EXP-0020-A` — « Le fuseau horaire choisi à l’installation est conservé ; une seconde
  exécution ne le change pas. » : ajouté par la spécification 1.0.7 (#3382) ; tenu depuis EP-25
  (US-2200, #2527) ;
- écart : `WF-ADM-0100-A` — « Chaque fonction de second niveau de l’arborescence est représentée par
  ses deux permissions, ou par la seule permission de consulter pour FBS-1.3, FBS-1.5, FBS-2.1 à
  FBS-2.7, FBS-4.8 et FBS-4.9. » : réécrit par la spécification 1.0.7 (#3354) : FBS-4.8 et FBS-4.9
  n'ont que la permission de consulter, quand le livré leur donne encore celle de modifier ; #3975
  l'éprouve ;
- écart : `WF-ADM-0100-A` — « Un rôle disposant de la modification du chiffrage mais non du marquage
  permet de modifier un devis et refuse de marquer la révision ; un rôle disposant du marquage mais
  non de la fusion refuse de fusionner un différentiel. » : EP-04 et EP-08, comme le dit US-1050 ;
  EP-08 clôt l'exigence ;
- écart : `WF-ADM-0100-A` — « Un utilisateur sans la permission de créer un projet n'en crée pas. » :
  EP-04, comme le dit US-1050 ;
- `WF-ADM-0100-A` — « Aucun écran ne permet de créer une permission. » : les permissions nouvelles
  arrivent par une migration, comme le reste du catalogue ;
- propre à l'US : l'écran porte une carte « Installation » : le nom de l'entreprise, modifiable par
  qui détient la permission de modifier la fonction, et, en lecture seule, la devise, la langue par
  défaut et le fuseau horaire fixés à l'amorçage (#3088, décision de l'auteur du 2026-11-13) ; le
  fuseau est celui qu'US-2200 garde et rend lisible ;
- propre à l'US : le nom de l'entreprise et sa commande quittent l'écran des paramètres de coûts ;
- propre à l'US : une session sans la permission de consulter la fonction ne voit pas l'entrée
  « Installation » ; avec elle et sans celle de modifier, elle lit la carte sans commande.

**Notes de réalisation.** Décision de l'auteur du 2026-11-14, au cadrage, qui revient sur « la
spécification ne change pas » de #3088 : WF-ADM-0100 définit les permissions par fonction de second
niveau de l'arborescence fonctionnelle, qui s'arrête à FBS-1.5 ; une fonction « Installation » la
complète, FBS-1.6, par une révision de la spécification que porte l'issue `specification` #3197.
L'US n'attend plus cette révision : elle suit la rédaction que #3197 propose, et la spécification
est mise à jour dans un second temps, sans révision propre à ce constat ; ses critères se relisent
alors contre le Vérif révisé, que `make roadmap` confronte (décision de l'auteur du 2026-11-15).
Le contrat suit par une issue `contract` : les deux permissions, le nom de l'entreprise écrit sous
la fonction nouvelle. Le rôle prédéfini « administrateur » reçoit les deux permissions, sur une
installation neuve comme par la migration là où il existe encore, et lui seul (décision de l'auteur
du 2026-11-14, au cadrage). Écartés : l'écran sous la permission des coûts — un administrateur sans
les réglages de coûts ne le verrait pas ; le report à EP-13.

**Hors périmètre.** Modifier la devise, la langue par défaut ou le fuseau horaire : ils sont fixés à
l'amorçage (WF-REF-0140, WF-EXP-0020).

## US-2130 — L'accueil, les écrans de réglage et de consultation d'un projet, et le compte, en cartes

- **statut** : fini
- **exigences** : `WF-IHM-0100-A`, `WF-IHM-0120-A`, `WF-IHM-0090-A`
- **opérations** : aucune en propre — celles que ces écrans lisent et écrivent déjà
- **issue** : #3221

**En tant que** chef de projet, **je veux** que l'accueil et les écrans où je règle et consulte un
projet suivent la présentation de l'écran de référence, **afin de** ne pas changer de repères en
passant du référentiel à un projet.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » :
  sur chacun de ces écrans, dans les deux modes ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- `WF-IHM-0120-A` — « Un contributeur de deux projets les voit à sa connexion ; la levée du filtre
  montre aussi les projets qu'il peut ouvrir sans en être contributeur, et aucun autre. » : « mes
  projets » est un filtre de la table, dit par sa pastille « (par défaut) » et levé en l'ôtant,
  comme le filtre « État », et non plus un bouton de l'écran ;
- écart : `WF-IHM-0120-A` — « Sur une installation au référentiel incomplet, l'accueil nomme les
  prérequis manquants et mène au référentiel. » : non touché ; constaté par EP-04 (US-0920) ;
- écart : `WF-IHM-0120-A` — « L'administrateur d'une installation neuve arrive sur un accueil qui
  mène à l'administration ; une personne créée sans rôle par un fournisseur externe lit qu'il lui
  faut un rôle. » : non touché ; constaté par EP-24 (US-1870) ;
- `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée
  indisponible en nommant la condition manquante. » : la condition se lit dans l'infobulle de la
  commande, au pointeur comme au clavier, et dans la région des refus quand la commande est
  pressée ; elle ne s'écrit plus sous son bouton (#3090, décision de l'auteur du 2026-11-13) ;
- écart : `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas
  cette commande. » : non touché ; constaté par EP-02 (US-0170) ;
- écart : `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas
  contributeur nomme cette condition. » : non touché ; constaté par EP-02 (US-0170) ;
- écart : `WF-IHM-0090-A` — « Pendant un traitement de fond sur le projet, la saisie du lotissement
  est présentée indisponible en nommant le traitement en cours comme condition manquante, et une
  écriture tentée est refusée en le nommant. » : non touché ; ajouté par la spécification 1.0.2, le
  lotissement pendant un traitement de fond est d'US-0660/L2 (#1336), comme le dit US-0170 ;
- propre à l'US : accueil — « Créer un projet » est pleine ; la table est en carte ;
- propre à l'US : gestion des révisions — une carte par section existante, « Ouvrir une révision en
  cours » pleine ; la structure de l'écran ne change pas (décision de l'auteur du 2026-11-14, au
  cadrage) ;
- propre à l'US : paramètres de projets — une carte « Projet » pour les attributs, « Modifier le
  projet » à droite de son titre ; le lotissement en carte, ses commandes sur une ligne à partir de
  1280 points, repliées en dessous, sa table à la largeur de la carte (#3418) ;
- propre à l'US : cycle de vie, imports et exports, plan de charge — une carte par section ; les
  filtres du plan de charge dans sa carte ;
- propre à l'US : mon compte, déjà conforme, prend les couleurs et les formes ; les écrans hors
  fonction — introuvable, erreur, connexion indisponible — aussi.

**Hors périmètre.** La désignation de la référence en colonne de l'historique et la refonte de
l'écran « Révisions » — EP-27 (#3177, #3180).

## US-2140 — Les écrans de travail d'un projet : serrés, aux couleurs et aux formes nouvelles

- **statut** : fini
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre — celles que ces écrans lisent et écrivent déjà
- **issue** : #3232

**En tant que** chef de projet, **je veux** que les grilles où je saisis gardent toute la fenêtre et
leur densité en prenant la présentation nouvelle, **afin de** ne rien perdre de ce que je vois d'un
planning ou d'un devis.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » :
  sur chacun de ces écrans, dans les deux modes ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- propre à l'US : planification, chiffrage et devis, reste à engager, arbre des tâches — la grille
  reste serrée, hors colonne centrée, et remplit la fenêtre ; la hauteur de ses lignes ne change
  pas ; « Date de début de planning » ne flotte plus sous le titre ;
- propre à l'US : coûts réels — le nombre de lignes retenues sous le titre est retiré, la ligne de
  total le dit ; le journal des imports est en carte ;
- propre à l'US : chronologies — le choix de la chronologie est une rangée d'onglets, non de boutons
  pleins ; « Nouvelle chronologie », qui crée, est pleine ;
- propre à l'US : Kanban — ses colonnes de cartes prennent les couleurs et les formes.

**Hors périmètre.** L'ordre de la barre des grilles arborescentes (US-2080) ; les marques d'une
comparaison (EP-27) ; la performance (EP-26).

## US-2150 — Les écrans que le service ne sert pas encore, mis en page contre le faux back : portefeuille, risques, indicateurs, état du système

- **statut** : fini
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre — celles que ces écrans lisent déjà, sur les exemples du contrat
- **issue** : #3235

**En tant que** manager, **je veux** que le portefeuille, les risques et les indicateurs d'un projet
et l'état du système aient déjà la présentation nouvelle, **afin que** les EPICs qui les brancheront
sur le service n'aient pas à la refaire.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » ;
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » :
  sur chacun de ces écrans, dans les deux modes ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- propre à l'US : les sept écrans du portefeuille, « Indicateurs projets » et « Surveillance de
  l'état du système » sont en colonne centrée et en cartes, une carte par section, par table et par
  graphique ; leurs filtres de périmètre sont dans une carte ou dans la barre de leur table — pour
  « Indicateurs projets », écran d'un projet, la bannière de contexte en tient lieu, comme sur
  l'écran de référence des coûts réels (#3422, décision de l'auteur du 2026-11-15) ;
- propre à l'US : « Gestion des risques » — le registre, grille de saisie, reste serré comme un écran
  de travail ; la matrice et la couverture sont en cartes ;
- propre à l'US : la mise en page se constate contre le faux back, sur les exemples du contrat ;
  aucun de ces écrans n'est branché sur le service ici (décision de l'auteur du 2026-11-14, au
  cadrage) ;
- propre à l'US : `risks.spec.ts` lit la puce du réestimé par une attente qui se répète, sur un
  sélecteur qui ne tient pas aux classes, et le commentaire de `risk-cells.tsx` tient en cent
  colonnes (#1997).

**Hors périmètre.** Le service de ces écrans — EP-10, EP-08, EP-11, EP-13 (#2307) ; leurs graphiques
(US-2160).

## US-2160 — Les graphiques : une présentation sobre, et les motifs des séries sur préférence du compte

- **statut** : fini
- **exigences** : `WF-IHM-0070-A`, `WF-ADM-0040-A`, `WF-IHM-0130-A`
- **opérations** : `getMe`, `updateMyPreferences` ; les lectures des graphiques, inchangées
- **issue** : #3214

**En tant que** manager, **je veux** des graphiques aux couleurs pleines, lisibles d'un regard, et
pouvoir demander les motifs qui distinguent les séries sans la couleur, **afin de** les lire à
l'écran comme je les préfère, et de les exporter tels que je les lis.

**Critères d'acceptation.**

- `WF-IHM-0070-A` — « Avec la préférence des motifs, une copie d'écran en niveaux de gris d'un plan
  de charge laisse identifier chaque rôle ; sans elle, son infobulle et sa table des valeurs nomment
  chaque rôle. » ;
- écart : `WF-IHM-0070-A` — « Une copie d'écran en niveaux de gris laisse identifier chaque
  signalement. » : les signalements ne sont pas touchés ; constaté par EP-02 (US-0160) et tenu par
  US-2070 ;
- écart : `WF-IHM-0070-A` — « La même zone d'indice porte la même couleur dans la liste des projets,
  dans les indicateurs du projet et dans la performance du portefeuille. » : constaté par EP-02
  (US-0160) et tenu par US-2070 ;
- écart : `WF-IHM-0070-A` — « Aucun écran ne distingue deux états par la seule couleur. » : constaté
  par EP-02 (US-0160) et tenu par US-2070 ;
- `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier celles d'un
  autre. » : la préférence des motifs se règle sur « Mon compte », à côté de la langue et du mode
  d'affichage ; elle est désactivée tant que le compte ne l'a pas demandée ;
- `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes données présentées
  selon leurs réglages respectifs. » : le même plan de charge, avec les motifs pour l'un, sans pour
  l'autre ;
- `WF-IHM-0130-A` — « Le plan de charge d'un projet exporté est une image PNG qui porte le nom du
  projet, la révision et la date de calcul ; le plan de charge agrégé exporté porte le périmètre et
  la date de calcul. » : l'image porte de plus les motifs de ses séries quand la préférence de qui
  exporte les demande, et ne les porte pas sinon ; le plan de charge agrégé se constate contre le
  faux back, EP-11 clôt l'exigence ;
- écart : `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les projets de
  cet état dans ses totaux. » : les tables sont à US-2080 ;
- écart : `WF-IHM-0130-A` — « La table des calendriers ne propose aucun filtre sur les heures de ses
  jours ; elle se filtre sur ses autres colonnes. » : non touché ; constaté par EP-15 (US-0570) ;
- propre à l'US : tous les graphiques — plans de charge, courbes et indices des indicateurs, suivi
  des jalons, graphiques du portefeuille, matrice des risques, Gantt et chronologies — prennent la
  présentation validée sur le plan de charge : couleurs pleines, palette adoucie, barres moins
  larges, chaque part arrondie et séparée de ses voisines par un filet ; axe des ordonnées sans
  trait ni graduation, grille horizontale en tirets clairs ; légende en haut à gauche, en pastilles ;
  infobulle en carte ; la série sous le pointeur ressort (#3097, décisions de l'auteur du
  2026-11-13) ;
- propre à l'US : la préférence vaut pour les motifs des barres comme pour les symboles des points
  des courbes ; la légende suit ce que le tracé dessine ;
- propre à l'US : l'échelle ne change pas — ni échelle rompue, ni zoom ; les couleurs de signal et
  les marques propres au Gantt et aux chronologies ne changent pas (#3097).

**Notes de réalisation.** La préférence s'ajoute à `DisplayPreferences` par une modification du
contrat, faite avant le front : une issue `contract`, une entrée de `docs/api/DECISIONS.md`. Le back
la sert et la garde avec les autres. La spécification est déjà révisée (1.0.6, #3098) : l'export suit
la préférence de celui qui exporte, et par défaut ne porte pas les motifs — conséquence acceptée par
l'auteur le 2026-11-13.

**Hors périmètre.** Le détail du plan de charge et la projection de dépenses — EP-10 (US-2040,
US-2050), qui naissent dans cette présentation.

## US-2170 — Un traitement en cours se voit là où on l'a lancé, et l'écran se relit quand il aboutit

- **statut** : fini
- **exigences** : `WF-IHM-0080-A`
- **opérations** : `getBackgroundTask`, `listBackgroundTasks`, `getBackgroundTaskResult`,
  `requestExport`, `markRevision`, `createRevision`, `applyImport`
- **issue** : #3217

**En tant que** chef de projet, **je veux** voir qu'une commande que je viens de presser est partie,
et son résultat là où je regarde, **afin de** ne pas la relancer et me retrouver avec cinq exports
pour un fichier.

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable et
  présente son avancement. » : le bouton pressé est inerte et marqué « en cours » tant que la
  requête ou la tâche qu'il a lancée n'a pas répondu ; une seconde pression ne relance rien ;
- `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de son
  aboutissement. » : par une carte flottante au coin de l'écran, qui offre l'action qui suit —
  « Télécharger » pour un export, « Ouvrir » pour une révision — et reste jusqu'à ce qu'on l'ouvre
  ou la ferme ; plusieurs s'empilent, et le panneau « Tâches et messages » les garde (décision de
  l'auteur du 2026-11-14, au cadrage) ;
- `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même
  traitement peut être relancé. » : l'échec rend son bouton à l'écran qui l'a lancé ;
- propre à l'US : le téléchargement du résultat d'un export part de lui-même quand la tâche aboutit
  et que l'écran qui l'a demandé est encore ouvert (#3103, décision de l'auteur du 2026-11-13) ;
- propre à l'US : l'écran se relit quand une tâche qui le concerne aboutit ou échoue — la liste des
  révisions après un marquage ou une ouverture, les imports du projet après un import ;
- propre à l'US : une écriture lente faite dans la requête montre la même attente sur son bouton ;
- propre à l'US : le suivi d'une tâche ne s'arrête pas tant qu'elle court : la cause de l'arrêt
  relevé le 2026-11-13 — une tâche lue deux fois, aboutie, plus jamais lue — est établie et
  corrigée (#3103).

**Notes de réalisation.** Le Vérif de WF-IHM-0080 était tenu à la lettre ; l'usage ne l'était pas
(#3103 : cinq demandes d'export pour un fichier). La présentation de la notification suit la charte
d'US-2070.

**Hors périmètre.** L'ouverture d'une révision qui dure dix secondes, et l'appel rompu au bout de
cinq que le front dit « injoignable » — EP-26 (#3102).

## US-2180 — Les saisies du référentiel et de l'administration : les constats de la revue du front soldés

- **statut** : fini
- **exigences** : `WF-REF-0080-A`, `WF-REF-0170-A`
- **opérations** : `updateOrgNode`, `updateResourceRole`, `updateCalendar`, `setOrgNodeActivation`,
  `setResourceRoleActivation`, `setCalendarActivation`, `setDefaultCalendar`, `updateCostType`,
  `updateCostCategory`, `setCostTypeActivation`, `setCostCategoryActivation`,
  `setActualCostMapping`, `updateReferenceSettings`, `updateUser`
- **issue** : #3202

**En tant que** manager, **je veux** que les formulaires du référentiel ne perdent ni une saisie ni
un refus, **afin de** ne pas refaire une modification que l'écran a laissée partir deux fois.

**Critères d'acceptation.**

- `WF-REF-0080-A` — « La désactivation d'un nœud portant deux niveaux de descendants et des rôles
  les désactive tous. » : l'arbre montre chaque descendant « Désactivé », au compteur de la réponse,
  avant toute relecture, sur un exemple du contrat qui porte la cascade (#2270) ;
- écart : `WF-REF-0080-A` — « La réactivation d'un rôle dont le nœud est désactivé est refusée. » :
  non touché ; constaté par EP-05 (US-0850) ;
- `WF-REF-0170-A` — « Les quatre seuils sont saisissables, et le seuil d'alerte de chaque indice est
  inférieur à son seuil de vigilance. » : le formulaire ne juge l'ordre que de deux seuils dans
  ]0, 1[, et dit le refus de plage au champ que le serveur désigne (#2268) ;
- écart : `WF-REF-0170-A` — « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à
  0,5, avec des seuils fixés à 0,9 et 0,8. » : EP-10, qui clôt l'exigence ;
- écart : `WF-REF-0170-A` — « Avec des seuils à 0,9 et 0,8, un indice de 0,9 est nominal et un
  indice de 0,8 en vigilance. » : EP-10, qui clôt l'exigence ;
- propre à l'US : sur une ligne du référentiel en cours d'écriture, « Modifier », « Désactiver » ou
  « Réactiver » et « Désigner » sont indisponibles et dits « Enregistrement en cours… » ; un appui
  n'ouvre ni n'envoie rien, les autres lignes restent offertes, et le formulaire rouvert part du
  compteur de la réponse (#2260) ;
- propre à l'US : la correspondance des coûts réels garde le focus et la saisie en cours quand sa
  relecture arrive (#2266) ; chaque colonne lue s'arrête à vingt intitulés, comme le schéma, et un
  refus du serveur se dit sous la liste qu'il désigne (#2267) ;
- propre à l'US : le refus d'un nœud désactivé entre la lecture et le choix se dit au champ du
  rattachement d'un compte, par son code, non par le message générique (#2121) ;
- propre à l'US : `useRaise` dit qu'il ignore une erreur venue après le démontage, et les imports de
  `role-commands.tsx` et de son test sont à leur rang (#3163).

**Notes de réalisation.** L'exemple de cascade — un nœud et deux niveaux de descendants — s'ajoute
au contrat par une issue `contract` (décision de l'auteur du 2026-11-14, au cadrage), avant le test
qui le lit.

## US-2190 — La page de connexion à la charte nouvelle

- **statut** : fini
- **exigences** : aucune en propre
- **opérations** : aucune
- **issue** : #3238

**En tant qu'** administrateur, **je veux** que la page de connexion porte les couleurs et les
formes de l'application, **afin que** l'on n'ait pas l'impression de passer d'un produit à un autre
en se connectant.

**Critères d'acceptation.**

- propre à l'US : le thème `waterfall` du fournisseur d'identité prend la couleur primaire, les
  boutons et les champs en pilule et le fond de la charte d'US-2070, en mode clair et en mode
  sombre ; le bleu du logo n'y sert plus qu'au logo et à la bannière ;
- propre à l'US : le texte, les champs et les messages d'erreur de la page gardent le contraste AA ;
- propre à l'US : la page du fournisseur externe de développement suit le même thème.

**Notes de réalisation.** Après la validation de l'écran de référence par l'auteur (« Préalables ») :
les valeurs sont celles que l'application a arrêtées.

## US-2200 — Le jour courant s'entend dans le fuseau horaire de l'installation

- **statut** : fini
- **exigences** : `WF-PLA-0130-A`
- **opérations** : `getInstallation` ; `setTaskProgress`, `requestExport` et les autres opérations
  qui datent au jour courant, inchangées
- **issue** : #3199

**En tant que** chef de projet, **je veux** que « aujourd'hui » soit le jour de mon installation et
non celui du temps universel, **afin qu'** une tâche que je termine peu après minuit ne soit pas
datée de la veille.

**Critères d'acceptation.**

- `WF-PLA-0130-A` — « Le passage à l'état démarré ou terminé demande une date, proposée au jour
  courant et modifiable. » : le jour proposé par l'écran et le jour écrit par défaut par le service
  sont celui du fuseau de l'installation ; à 23 h 30 en temps universel, une installation au fuseau
  de Paris date du lendemain ;
- écart : `WF-PLA-0130-A` — « Chacun de ces attributs est affiché dans la grille de planning, et
  ceux que MS Project connaît sont transportés par l'export. » : non touché ; constaté par EP-06
  (US-1410, US-1430, US-1470) ;
- écart : `WF-PLA-0130-A` — « Une terminaison datée avant le démarrage de la tâche est refusée. » :
  non touché ; constaté par EP-06 (US-1410) ;
- écart : `WF-PLA-0130-A` — « Un import de reste à engager qui met une tâche à zéro la date de la
  revue que porte le fichier ; une récapitulative porte la date de terminaison de sa dernière
  subordonnée. » : non touché ; la récapitulative par EP-06, l'import par EP-09, EP-10 clôt ;
- écart : `WF-PLA-0130-A` — « La durée d'un jalon est nulle et n'est pas modifiable ; les dates
  d'une récapitulative ne sont pas saisissables. » : non touché ; constaté par EP-06 (US-1380) ;
- écart : `WF-PLA-0130-A` — « La marge totale, la criticité et l'avancement physique s'affichent et
  ne sont pas saisissables. » : non touché ; la marge et la criticité par EP-06, l'avancement
  physique par EP-10, qui clôt ;
- propre à l'US : l'amorçage garde le fuseau horaire de l'installation, donné à
  `waterfall-api install` ; relancé, il ne le change pas ; un fuseau inconnu est refusé (WF-EXP-0020,
  #2527) ;
- propre à l'US : le service prend le jour courant par sa seule fonction du noyau (US-1380/L4),
  branchée sur ce fuseau, ses appelants inchangés ;
- propre à l'US : `getInstallation` rend le fuseau, et l'écran propose le jour dans ce fuseau, non
  dans celui du poste.

**Notes de réalisation.** #2527, reporté d'EP-06 à EP-07 puis à EP-13 sans être fait, est repris ici
(décision de l'auteur du 2026-11-14, au cadrage) : EP-25 est le seul EPIC qui touche les réglages de
l'installation, et il passe avant ceux qui finalisent les grilles (EP-26, EP-27) et avant EP-10, dont
la date de calcul est ce jour courant. L'US n'attend pas la révision de la spécification : la 1.0.3
porte déjà le fuseau (WF-EXP-0020, WF-PLA-0130). Écartés : EP-26, qui mesure la lecture des grilles
et ne touche pas ces fichiers ; EP-10, qui vient après EP-27.

**Hors périmètre.** Modifier le fuseau après l'amorçage ; l'heure d'une sauvegarde planifiée, que
le contrat dit sans fuseau (`docs/api/DECISIONS.md`).

## US-2310 — Les composants communs et la dette de tests : ce que les lots d'écran ont laissé à trancher

- **statut** : fini
- **exigences** : `WF-IHM-0080-A`, `WF-IHM-0090-A`, `WF-IHM-0100-A`
- **opérations** : aucune en propre — celles que le suivi des tâches lit déjà
  (`getBackgroundTask`, `listBackgroundTasks`)
- **issue** : #3451

**En tant que** manager, **je veux** que les commandes et les cartes communes se comportent de la
même façon sur chaque écran, **afin de** ne pas relancer un traitement qui court ni retrouver d'un
écran à l'autre les écarts que la refonte a relevés.

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable et
  présente son avancement. » : le bouton qui a lancé une tâche reste inerte et marqué « en cours »
  tant qu'elle court, après un rechargement ou un aller-retour dans le même onglet aussi ; il la
  retrouve au montage par le suivi des tâches de la coquille, à sa nature et à son objet ; ainsi
  de chaque bouton à l'attente commune — marquage, exports, imports, sauvegarde, lecture des
  comptes du fournisseur d'identité (#3404, décision de l'auteur du 2026-11-15) ;
- écart : `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de
  son aboutissement. » : non touché ; tenu par US-2170 ;
- écart : `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le
  même traitement peut être relancé. » : non touché ; tenu par US-2170 ;
- `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée
  indisponible en nommant la condition manquante. » : la règle qu'US-2130 donne aux boutons vaut
  pour un item de menu — la condition d'un item indisponible, ceux des cartes du Kanban, se lit dans
  son infobulle et, à la presse, dans la région des refus ; elle ne s'écrit plus sous son libellé
  (#3430, décision de l'auteur du 2026-11-15) ;
- écart : `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas
  cette commande. » : non touché ; constaté par EP-02 (US-0170) ;
- écart : `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas
  contributeur nomme cette condition. » : non touché ; constaté par EP-02 (US-0170) ;
- écart : `WF-IHM-0090-A` — « Pendant un traitement de fond sur le projet, la saisie du lotissement
  est présentée indisponible en nommant le traitement en cours comme condition manquante, et une
  écriture tentée est refusée en le nommant. » : non touché ; d'US-0660/L2 (#1336), comme le dit
  US-0170 ;
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » : les
  commandes du lotissement tiennent sur une ligne à partir de 1280 points sans déborder de leur
  carte, et se replient en dessous, mesurées à 1024 et à 1100 points comme à 1366 : sur une ligne,
  elles débordaient de leur carte sous 1280 points (#3418) ;
- écart : `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste
  visible. » : non touché ; tenu écran par écran par US-2100 à US-2150 ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau
  AA. » : non touché ; tenu écran par écran par US-2100 à US-2150 ;
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé
  associé ni aucune image porteuse d'information sans description. » : ajouté par la spécification
  1.0.7 (#3379) ; le contrôle axe des parcours le tient (`frontend/e2e/axe.ts`) ;
- propre à l'US : une carte de grille commune, sans titre, à côté de la carte de section, porte la
  grille d'un écran de travail qui remplit sa fenêtre ; elle remplace les cartes que les écrans
  composaient eux-mêmes — celle du journal d'audit et celle des écrans de travail d'un projet ; la
  carte de section garde son titre exigé (#3421, décision de l'auteur du 2026-11-15) ; de même, un
  graphique qui se nomme lui-même et une section vide ont leur forme commune, et le portefeuille
  et l'état du système n'en composent plus de locale (#3446, décision de l'auteur du 2026-11-15) ;
- propre à l'US : un écran aéré l'est jusqu'à son en-tête : un test refuse un fichier qui écrit un
  écran aéré et laisse son en-tête à la densité serrée (#3397) ;
- propre à l'US : paramètres de projets — « Modifier les contributeurs » est à droite du titre de sa
  carte, comme « Modifier le projet » (#3417, décision de l'auteur du 2026-11-15) ;
- propre à l'US : les tests de l'accueil disent ce qu'ils mesurent — le nombre de projets du faux
  back, la tolérance de largeur entre la barre et la table justifiée ou retirée, le corps écrit des
  réglages de la liste des projets réduit aux clés attendues — et la phrase du guide sur les états
  n'est plus coupée (#3399).

**Notes de réalisation.** Complément décidé par l'auteur le 2026-11-15, en fin d'EPIC : les lots
d'écran ne touchent que leurs fichiers (conception, « Décisions »), et les constats qu'ils ont
relevés sur des composants communs restaient « à trancher ». La dette de tests confiée au complément
est revérifiée au cadrage : #3259, #3265, #3266, #3272, #3273, #3286, #3287, #3293 et #3298 sont
soldés sur `epic/EP-25` par US-2080/L4 ; #3399 seul reste. L'attente retrouvée tient à l'onglet,
dont le suivi des tâches garde les tâches qui courent ; un autre onglet ne la voit pas.

**Hors périmètre.** L'attente vue d'un autre onglet ou d'un autre poste ; la barre repliée d'une
grille arborescente à 911 points (#3416), corrigée par US-2110/L1 ; les mineurs du parcours du thème
de connexion (#3431), reportés → EP-28 ; le test des pages des coûts réels (#3432), abandonné.

# Revue — qualité des tests du front, parcours de bout en bout, catalogues, aide en ligne, accessibilité

Commit relu : `29785cc`. Rien n'a été lancé (ni `pnpm test`, ni `playwright`, ni `make`) : tout ce qui
suit vient de la lecture des sources et de scripts de lecture seule (les relevés d'exigences ont été
calculés par les modules `wftools.coverage`/`roadmap`/`projection` importés depuis `tools/.venv`, sans
rien écrire dans le dépôt).

## Synthèse

Le harnais est d'un niveau rare : `retries: 0`, aucun `waitForTimeout`, aucun `.only`/`fixme`/`test.fail`,
un front construit par worker, une garde du contrat qui lit le journal de Prism pour chaque parcours
contre le service, un faux client typé par le contrat (un exemple hors contrat ne compile pas), la
sortie d'erreur refusée dans les tests de composants. Chaque domaine livré (EP-03 à EP-09) a au moins
un parcours **contre le vrai service** qui écrit puis relit, et aucune exigence close par un EPIC livré
`front, back` n'a ses seuls parcours sur le faux back (script : 0 cas sur 100 exigences).

Deux choses inquiètent. (1) Le relevé `make requirements` range `WF-PLA-0090-A` (Gantt, close par EP-06
livré) dans « front seul » : elle est donc **non couverte** au sens de WF-QUA-0010 alors que ses
parcours jouent bien contre le service — la famille « contre le service » se décide au chemin
(`e2e/service/**`), pas à l'étiquette `@shared`. (2) Le parcours des unités de durée laisse
l'installation à 7 h/jour une fois sur deux, et depuis EP-06 ce changement **redate toutes les
révisions en cours**, témoin compris : un rejeu de `make e2e-service` sur une plateforme gardée lit un
témoin redaté. Le reste est mineur : quelques parcours `@shared` dont l'attente s'arrête à l'adresse
ou se lit dans le service lui-même, des citations qui ne tiennent qu'une moitié de Vérif, le projet
Vitest `node` qui ne refuse pas `console.error`, deux clés mortes aux catalogues, la page de
connexion jamais auditée. La mesure de performance ne mesure qu'une ligne du tableau 15, sur faux
back, sans échec : déjà connu (EP-26).

## Constats bloquants

Aucun.

## Constats majeurs

### FTE-01 — `WF-PLA-0090-A`, close par EP-06 (livré, `front, back`), est comptée « front seul » : non couverte au sens du dépôt

- **Issue** : #4415 (EP-32), ouverte le 2026-11-21, avec RMP-05.
- **Où** : `tools/paths.toml:778-779` (`end-to-end-service = ["frontend/e2e/service/**"]`,
  `end-to-end = ["frontend/e2e/**"]`) ; `tools/src/wftools/coverage.py:48` (`FRONT_FAMILIES`) et `:254` ;
  les parcours qui la citent : `frontend/e2e/planning-service.spec.ts:70` et `:327`,
  `frontend/e2e/planning.spec.ts:459`, `:510`, `:526`, `frontend/e2e/grid.spec.ts:298` ; table
  d'EP-06 : `docs/roadmap/EP-06-planification.md:116` (« fin — amorcée en EP-15 », US-1470 `fini`).
- **Quoi** : parmi les 15 exigences « citées par le front seul » que rend `make requirements`, une
  seule est close par un EPIC **livré** : `WF-PLA-0090-A`. Aucun test du back ne la cite
  (`grep -rn WF-PLA-0090 backend/tests` : rien), et ses six parcours sont tous sous `frontend/e2e/`
  hors de `service/` : famille `end-to-end`, que `coverage.py` range avec le front — alors que les six
  portent `@shared` et que deux d'entre eux (`planning-service.spec.ts`) ne jouent **que** contre le
  service. Le relevé dit donc l'exigence non prouvée (règle de `docs/roadmap/README-fr.md`,
  « Familles » : « close par un autre, elle ne l'est pas tant que seuls le front et le bout en bout la
  citent »), et `make requirements-release` la nommerait en échec.
- **Scénario** : EP-06 clôt l'exigence avec le critère « `is_critical` du serveur … rejoué contre le
  service » (`EP-06:1875-1880`). Le lot écrit le jumeau dans `e2e/planning-service.spec.ts` (à la
  racine d'`e2e/`, avec `test.skip(!inService)`), pas dans `e2e/service/`. `wftools.coverage` lit les
  citations au chemin : `WF-PLA-0090-A: end-to-end, front (front alone)`. Vérifié en rejouant
  `coverage.report()` en lecture seule : `front_only` contient `WF-PLA-0090-A`, et
  173 = 210 − 22 non couvertes − 15 « front seul ».
- **Portée de la cause** : le même angle mort vaut pour tout parcours `@shared` (146 des 354 relevés) : un
  parcours joué contre le service hors de `e2e/service/` ne compte jamais comme preuve « à travers le
  back ». Aujourd'hui une seule exigence livrée en pâtit, parce que les autres ont un test du back.
  Angle mort inverse : la citation se lit dans le texte, sans lancer — un parcours `test.skip(…)`
  compte quand même (les quatre quarantaines de FTE-12 restent comptées).
- **Proposition** : au choix, par coût croissant — (a) un test du back qui cite `WF-PLA-0090-A` sur la
  phrase que le back doit (« le chemin critique » : `is_critical` rendu par `listNodes` sur le
  planning à deux branches, à côté des tests de WF-PLA-0100) ; (b) déplacer
  `planning-service.spec.ts` sous `e2e/service/` (son nom le dit déjà), ce qui le sort du projet
  `shared` et demande de reprendre sa connexion par `heldToTheContract()` ; (c) faire lire à
  `wftools.coverage` l'étiquette : une citation dont le titre porte `@shared` et dont le corps ne
  commence pas par `test.skip(inService` compte pour `end-to-end-service`. Preuve : `make requirements`
  rend 174 couvertes et 14 « front seul », et un test de `tools/tests/test_coverage.py` sur un titre
  `@shared`.
- **Confiance** : confirmé (relevé recalculé, chemins et table lus).

### FTE-02 — Le parcours des unités de durée laisse l'installation à 7 h/jour une fois sur deux, ce qui redate toutes les révisions en cours, témoin compris

- **Issue** : #4445 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `frontend/e2e/reference-resources.spec.ts:284-331` (`written = before === "7" ? "8" : "7"`,
  `:299` ; l'en-tête du fichier, `:7-8`, dit « leave a state equivalent … the units of duration
  alternate between 7 and 8 ») ; `backend/src/waterfall/core/resource_settings/interface/duration_units.py:131-168`
  (`if changed: recalculate(session, act.at)`) ; `backend/src/waterfall/core/planning/interface/reference.py:91-111`
  (`reschedule_current_structures` : chaque structure de chaque révision en cours) ;
  `backend/src/waterfall/witness/duration_units.py` (le chargeur ne réécrit pas des constantes déjà
  modifiées). Les lecteurs touchés : `frontend/e2e/planning.spec.ts:459-475` (`@shared`, dates du
  Gantt de la révision 102 de PRJ-001), `frontend/e2e/timelines.spec.ts:160-170` (« Mise en service, du
  21/12/2026 au 01/01/2027 », contre le service seulement).
- **Quoi** : le parcours `@shared @serial` écrit « l'autre de 7 et 8 » dans les heures par jour de
  l'installation et ne remet rien. Quand il a été écrit (EP-05), la constante ne redatait rien ;
  depuis EP-06 (commit `abe42c7`, US-1390/L2), `set_duration_units` rejoue le moteur sur **toutes les
  structures des révisions en cours**. L'état laissé n'est donc pas « équivalent » : les mille tâches
  du témoin sont saisies en jours (`fixtures/api/volume/nodes_thousand.json` : 1 000 durées en `d`),
  et à 7 h/jour « Montage des armoires sur site » (123 j) pèse 861 h au lieu de 984, « Mise en
  service » démarre trois semaines plus tôt.
- **Scénario** : `make e2e-service` sur un poste (sans `SHARD`, une seule plateforme, que la cible
  laisse démarrée — guide, « Un parcours de bout en bout » : « La plateforme reste démarrée », « rejoué
  sur une même installation »). Passage 1 : `shared` lit le témoin à 8 h, puis `shared-serial` écrit
  7 h et la révision 102 de PRJ-001 est redatée. Passage 2 sur la même plateforme : `shared` lit un
  témoin redaté — les dates écrites en dur des parcours du planning, du Gantt et de la frise ne sont
  plus celles des exemples — puis `shared-serial` réécrit 8 h, et le passage 3 repasse. Dans la
  chaîne, chaque part a sa plateforme neuve : rien ne se voit.
- **Seconde occurrence, latente** : `frontend/e2e/reference-settings.spec.ts:65-86` laisse la matrice
  de risques à 25/55/75 % et les seuils des indices à 0,95/0,85, 6 semaines, sans les remettre. Rien
  ne les lit contre le service tant qu'EP-08 et EP-10 ne sont pas livrés ; le jour où ils le sont, les
  zones du témoin changent au second passage.
- **Proposition** : le parcours remet dans un `finally` ce qu'il a lu (`before`, et les trois
  constantes), comme la réactivation d'« Automaticien » le fait déjà
  (`reference-resources.spec.ts:76-93`) — la correspondance des coûts réels remet aussi son intitulé
  (`reference-actual-cost-mapping.spec.ts:61-72`), hors `finally` ; l'assertion « relu après rechargement » reste. Idem pour la
  matrice et les seuils. Preuve : jouer deux fois de suite `make e2e-service` sur la même plateforme,
  ou un parcours de `e2e/service/` en fin de `shared-serial` qui affirme `getDurationUnits` égal à
  l'exemple `duration_units` (8/40/20).
- **Confiance** : plausible. Le mécanisme est lu de bout en bout (le parcours écrit sans remettre, le
  service redate, le chargeur ne corrige pas) ; non vérifié faute de lancer : que les dates
  précisément affirmées bougent — le calcul ci-dessus le donne pour toute tâche automatique non
  démarrée, pas pour les tâches terminées, qui gardent leurs dates réelles.

## Constats mineurs

### FTE-03 — `task-tree.spec.ts` : contre le service, l'attendu se lit dans le service, et l'export cité n'est pas vérifié

- **Issue** : #4448 (EP-36), ouverte le 2026-11-21, avec FTE-04, FTE-05, FTE-08, FTE-09.
- **Où** : `frontend/e2e/task-tree.spec.ts:79-98` et `:113-123` (titre `:53`, `[WF-PLA-0110-A] [WF-PLA-0120-A]`).
- **Quoi** : contre le service, la profondeur attendue est `meta.summary_depth` relue par l'API
  (`summaryDepth`, `:80`) ; si elle vaut 0, le parcours affirme « Ce planning n'a aucune tâche
  récapitulative » et **passe** (`:89-92`). Le témoin est déterministe (1 000 tâches, deux niveaux de
  récapitulatives contre le faux back, `:97`) : l'attendu de lecture a été réécrit en comparaison de
  l'écran au service, contre la règle « les parcours se réemploient … sans réécriture de ses attendus
  de lecture ». Et pour WF-PLA-0120 (« produit un fichier PNG dont le premier niveau est disposé
  horizontalement… »), le parcours n'affirme qu'une ligne « Export » dans le panneau des tâches : ni
  « Réussie », ni téléchargement, ni signature PNG — là où `workload.spec.ts:84-101` et
  `timelines.spec.ts:252` téléchargent et mesurent l'image.
- **Scénario** : une régression de `listNodes?summaries_only=true` rend `summary_depth: 0` sur
  PRJ-001 ; l'écran montre le seul nœud du projet ; le parcours `shared` passe. Ou le worker échoue
  l'export : la tâche s'affiche « Échouée », la ligne contient « Export », le parcours passe.
- **Proposition** : contre le service, affirmer la profondeur du témoin (2) et un libellé de
  récapitulative ; attendre « Réussie », télécharger et passer l'image à `pngSize` (`download.ts`).
- **Confiance** : confirmé (branches lues) ; les tests du back (`test_task_tree_export.py`) couvrent
  l'image elle-même.

### FTE-04 — Plan de charge : le filtre par nœud d'organisation n'est affirmé que par l'adresse, des deux côtés

- **Issue** : #4448 (EP-36), ouverte le 2026-11-21, avec FTE-03, FTE-05, FTE-08, FTE-09.
- **Où** : `frontend/e2e/workload.spec.ts:52-60` et `:71-80` (`[WF-DEV-0070-A]`, `@shared`).
- **Quoi** : Vérif — « Le filtre par nœud d'organisation ne laisse voir que les rôles qui en
  relèvent ». Les deux parcours choisissent le nœud, puis affirment l'adresse (`org_node_id=…`) et la
  valeur de la liste ; aucun ne lit un rôle dans la table des valeurs. Contre le faux back, rien
  d'autre n'est possible (Prism ignore les paramètres) ; contre le service, où le filtre est réel, le
  parcours passerait si la page n'envoyait pas `org_node_id` à l'API ou si le service l'ignorait. « La
  capacité de chaque rôle est affichée » n'est prouvé que par l'en-tête de colonne (`:44-50`).
- **Proposition** : sous `inService`, ouvrir « Valeurs du graphique » après le filtre et affirmer
  qu'un rôle hors du nœud `…471` a disparu et qu'un rôle du nœud reste, avec sa capacité.
- **Confiance** : confirmé. Les tests de page et du back tiennent chacun leur moitié ; seul le bout en
  bout manque.

### FTE-05 — Coûts réels : `WF-CRE-0050-A` et `WF-CRE-0030-A` cités pour une moitié de leur Vérif

- **Issue** : #4448 (EP-36), ouverte le 2026-11-21, avec FTE-03, FTE-04, FTE-08, FTE-09.
- **Où** : `frontend/e2e/actual-costs.spec.ts:189-268` (titre : `[WF-CRE-0040-A] [WF-CRE-0030-A] [WF-CRE-0020-A] [WF-CRE-0050-A]`).
- **Quoi** : après l'import contre le service, le parcours affirme la date du dernier import
  (`:226-229`) mais jamais l'entrée du journal (« le journal présente une entrée datée du jour avec
  ses comptes de lignes ») ; le journal n'est lu que sur le témoin (six lignes, sans leurs comptes,
  `:60-63`) et vide (`:183`). Pour WF-CRE-0030, la ligne exclue reste visible (`:266`), mais le second
  import « couvrant la même période » n'est pas rejoué. Les tests du back les prouvent
  (`test_actual_costs_apply.py`), pas la chaîne écran → service.
- **Proposition** : après `importActualCosts`, affirmer dans la table « Journal des imports » une ligne
  de données avec « 4 » lignes créées ; réimporter les quatre lignes après l'exclusion et affirmer
  « Exclue » et les totaux inchangés.
- **Confiance** : confirmé.

### FTE-06 — Le projet Vitest `node` ne refuse pas la sortie d'erreur, et la couverture tourne en `--silent`

- **Issue** : #4449 (EP-36), ouverte le 2026-11-21, avec FTE-07, FTE-12.
- **Où** : `frontend/vitest.config.ts:80-99` (`setupFiles: [SERVER_ONLY]` pour `node` et `lint`),
  `frontend/src/test/setup.ts` (deux `vi.mock`, rien d'autre), `frontend/src/test/setup-dom.ts:30-43`
  (la garde, pour `dom` seul), `Makefile:574-577` (`vitest run … --silent`).
- **Quoi** : « A test that writes on the error output fails » ne vaut que pour les 175 fichiers
  `*.dom.test.*`. Les 158 fichiers du projet `node` — dont 40 rendent du React par
  `renderToStaticMarkup`/`renderToString` (les pages serveur de `src/app`) — laissent passer un
  `console.error` de React (clé manquante, prop inconnue, imbrication invalide du HTML) ou du code,
  et `--silent` le retire du journal de la chaîne.
- **Scénario** : une page serveur rend une liste sans `key` ; React l'écrit sur `console.error` ; le
  test de la page passe ; personne ne lit l'avertissement.
- **Proposition** : poser `watchStderr`/`refuseStderr` (`src/test/stderr.ts`) dans un `setupFiles` du
  projet `node` aussi ; un test de la garde comme `setup-dom.dom.test.tsx`. Coût : les tests `node` qui
  écrivent aujourd'hui sans le dire échoueront et seront à corriger ou à doter d'un espion.
- **Confiance** : confirmé (configuration lue) ; combien de tests écrivent aujourd'hui n'est pas
  mesuré.

### FTE-07 — Catalogues : deux clés mortes, deux apostrophes droites, deux guillemets français en anglais ; rien ne tient les clés inemployées

- **Issue** : #4449 (EP-36), ouverte le 2026-11-21, avec FTE-06, FTE-12.
- **Où** : `frontend/messages/fr.json:2746-2747` et `en.json:2746-2747` (`admin.audit.find`,
  `admin.audit.findButton` : aucune lecture dans `frontend/src`, tests compris) ;
  `frontend/messages/fr.json:349` (`grid.structure.taskHint`, « d'un jour ») et `:3495`
  (`enums.CommandCondition.task_not_milestone`, « n'est pas ») ; `frontend/messages/en.json:1355` et
  `:1690` (« … » au lieu de “…”, que portent les 158 autres textes anglais) ;
  `tools/src/wftools/catalogs.py` (aucun contrôle des clés inemployées).
- **Quoi** : script de lecture seule sur les deux catalogues — 2 879 clés de chaque côté, aucune clé
  d'un seul côté, aucun argument ICU divergent (les trois `mergeReport.*` au pluriel en français et
  sans en anglais gardent `{count}`, et « added » est invariable), 72 valeurs identiques toutes
  légitimes (« Code », « Description », « Gantt », unités). Restent : deux clés que plus rien ne lit,
  deux apostrophes droites contre la règle typographique du guide (« apostrophe typographique »), deux
  guillemets français dans l'anglais.
- **Proposition** : retirer les deux clés, corriger les quatre textes ; un test `node` (à côté de
  `text-guard.test.ts`) qui échoue sur une clé hors `enums`/`errors`/`permissions` qu'aucune source ne
  lit (26 clés composées dynamiquement — `failure.*`, `${side}Short`, `${unknown}Unknown`,
  `daysShort.${day}` — sont à déclarer), et sur `'` dans `fr.json`.
- **Confiance** : confirmé pour les six textes ; la liste des clés mortes vient d'une heuristique
  (littéraux et préfixes de gabarits), vérifiée à la main pour ces deux-là.

### FTE-08 — Accessibilité : la page de connexion n'est jamais auditée, les écrans ne le sont qu'en français, et « ce qu'un geste ouvre » passe à vide

- **Issue** : #4448 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec FTE-03, FTE-04, FTE-05, FTE-09.
- **Où** : `frontend/e2e/accessibility.spec.ts:185` (`WALKED_SCREENS`), `:331-361` (seul contrôle en
  anglais : le panneau d'aide), `:404-423` (`found.length === 0 ? "nothing"`) ;
  `deploy/keycloak/themes/waterfall/login/resources/css/waterfall.css:19-50` ; aucun `axeAudit` ni
  `walkByTab` sous `frontend/e2e/service/`.
- **Quoi** : (a) les pages du thème `waterfall` de Keycloak (connexion, mot de passe oublié, fixation
  du mot de passe) recopient à la main les jetons de la charte et ne passent ni à axe ni au parcours
  au Tab, alors que `sign-in.spec.ts` et `password.spec.ts` les ouvrent contre le service. Les sept
  paires que j'ai calculées à la main tiennent AA (de 4,9:1 à 7,1:1) : pas de défaut aujourd'hui, mais
  aucun contrôle. **Déjà connu en partie (#3238, US-2190, EP-25)** : le critère « garde le contraste
  AA » y est, sans contrôle nommé. (b) Les 32 écrans sont audités et parcourus en français seulement :
  les libellés anglais, de longueurs différentes, ne sont jamais mis à 911 points (WF-IHM-0100, « à
  150 % … aucune commande ne devient inatteignable »). (c) Sur un écran autre que l'écran de
  référence, un test « what a gesture opens » qui ne trouve aucun déclencheur passe sans une
  assertion ; le nombre trouvé n'est comparé à rien (annotation seule).
- **Ce qui est sain** : aucune règle d'axe désactivée ; une seule exclusion (`nextjs-portal`, absent
  du front construit) ; `color-contrast` désactivée dans `src/test/axe.ts:28` pour happy-dom seul,
  justifiée ; les limites du harnais sont écrites dans le guide.
- **Proposition** : (a) un `axeAudit` de la page de connexion dans `service/sign-in.spec.ts`, clair et
  sombre ; (b) le parcours au Tab et l'audit rejoués en `en-US` sur les écrans de grille au moins ;
  (c) épingler par écran le nombre de déclencheurs joués, ou échouer sur une baisse.
- **Confiance** : confirmé (lecture) ; aucun écart d'accessibilité constaté.

### FTE-09 — Sélecteurs de structure et détails internes de bibliothèque dans quatre parcours

- **Issue** : #4448 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec FTE-03, FTE-04, FTE-05, FTE-08.
- **Où** : `frontend/e2e/planning-service.spec.ts:110` (`g.stroke-muted-foreground polygon`, une classe
  de la charte, pour « les liaisons sont visibles ») ; `frontend/e2e/risks.spec.ts:63`
  (`[class*='before:content']`) ; `frontend/e2e/portfolio.spec.ts:232` et `risks.spec.ts:205`
  (`path[fill-opacity='0.85']`, un détail du rendu d'ECharts, compté à 429).
- **Quoi** : contre la règle « jamais par une classe CSS » (`docs/dev/typescript.md`, « Les tests »).
  Le premier prouve une phrase de Vérif de WF-PLA-0090 par une classe qu'EP-25 (refonte de la charte,
  en cours) peut renommer sans défaut derrière.
- **Proposition** : nommer la flèche d'une liaison (`role="img"`, « Liaison 2 → 3 », comme la liaison
  en conflit l'est déjà, `:131-133`) et la trouver par son nom ; compter les bulles par leur nom
  accessible ou par la table des valeurs.
- **Confiance** : confirmé.

### FTE-10 — Mesure de performance : une ligne du tableau 15 sur plusieurs, faux back, un utilisateur, sans échec — déjà connu (#3173, #3184, EP-26)

- **Issue** : #4450 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec FTE-14.
- **Où** : `frontend/e2e/opening.spec.ts:51` (`OBJECTIVE = 1_000`), `:352-366` (avertissement, jamais
  d'échec), `:425-441` ; `frontend/e2e/departure.spec.ts` (seule borne qui échoue : le travail du fil
  principal pour quitter une grille, sous une seconde, processeur ralenti quatre fois) ;
  `frontend/bench/` ne contient aucun banc — seulement les jambes du mandataire du contrat.
- **Quoi** : seule « ouvrir une grille de planning ou de devis de mille tâches » est mesurée ; la
  grille du **reste à engager**, que la même ligne du tableau nomme, ne l'est pas ; ni « recalculer
  après une saisie », ni rien contre le service ou à cinquante utilisateurs. `WF-QUA-0060-A` est non
  couverte et attribuée à EP-26 (non livré). `make e2e-durations` ne mesure rien du produit : il
  répartit les parts de la chaîne.
- **Écart de texte** : `opening.spec.ts:35-36` et le guide (« se tient, bloquante, en EP-13 ») disent
  encore EP-13, alors qu'EP-26 clôt WF-QUA-0060 depuis le 2026-11-14.
- **Confiance** : confirmé. Marqué « déjà connu (#3173, EP-26) » ; l'absence du reste à engager et
  le texte périmé ne sont pas dans la liste d'EP-26.

### FTE-11 — Un seul attendu dépend du fuseau du poste ; aucun `timezoneId` dans la configuration

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — n'échoue que sur un poste à
  l'ouest de UTC−8 h 30, quand les postes sont en France et la chaîne en UTC : gain nul pour ce
  projet.
- **Où** : `frontend/e2e/actual-costs.spec.ts:58` (« Dernier import 3 juin 2026 », rendu par
  `LocalTime` depuis `2026-06-03T08:30:00Z`) ; `frontend/playwright.config.ts` (`locale: "fr-FR"`, pas
  de `timezoneId` ; seul `review.spec.ts:208` en pose un).
- **Quoi** : sur un poste à l'ouest de UTC−8 h 30, le navigateur écrit « 2 juin 2026 » et le parcours
  échoue. Portée étroite (postes en France, chaîne en UTC). Les autres dates sont des dates de
  planning sans fuseau, et les deux comparaisons à l'horloge du poste (`actual-costs.spec.ts:229`,
  `service/audit.spec.ts:67-68`) ont leur tolérance.
- **Proposition** : `timezoneId: "Europe/Paris"` dans `use` de la configuration, que
  `harness.test.ts` tienne.
- **Confiance** : confirmé par lecture ; non joué.

### FTE-12 — Quatre parcours en quarantaine contre le service, et aucun outil ne tient « ni `skip` ni `fixme` » — déjà connu (#3087, #3190, #3191, #3192)

- **Issue** : #4449 (EP-36), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec FTE-06, FTE-07.
- **Où** : `frontend/e2e/structure.spec.ts:338-344`, `frontend/e2e/reference-costs.spec.ts:376-382` et
  `:480-486`, `frontend/e2e/revisions.spec.ts:124-132`.
- **Quoi** : `test.skip(inService, QUARANTINED_…)`, par décision de l'auteur du 2026-11-14, contre la
  règle « Aucun échec n'est toléré … jamais par … un `skip` ». Vérifié : aucune exigence close par un
  EPIC livré ne perd par là son dernier parcours contre le service (`WF-REF-0010-A` en garde 3,
  `WF-REF-0150-A` 2 ; `WF-REF-0030-A` et `WF-ARC-0020-A` relèvent d'EP-08 et d'EP-02). Ce qui n'est
  pas dans la roadmap : rien ne tient la règle — ni ESLint ni `make sources` ne voient un `test.skip`
  sans condition, un `fixme` ou un `.only` (seuls `forbidOnly` et Vitest le refusent, dans la chaîne).
- **Proposition** : un test `node` qui lit `e2e/**` et n'admet de `test.skip` que sur `inService`,
  `!inService`, ou une constante d'une liste nommée avec son issue.
- **Confiance** : confirmé. « Déjà connu (#3087 EP-26, #3190/#3191 EP-25 puis EP-26, #3192 EP-27) »
  pour les quarantaines.

### FTE-13 — 347 noms accessibles recopiés du catalogue dans les parcours : un libellé changé ne casse qu'au palier complet

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — c'est le parti assumé du dépôt,
  l'échec reste dit au palier complet, et la raison d'urgence (les renommages d'EP-25) a disparu :
  EP-25 est livré.
- **Où** : `frontend/e2e/*.spec.ts`, `frontend/e2e/service/*.spec.ts` — 1 654 `name: "…"`, 482
  distincts, dont 347 sont mot pour mot une valeur de `messages/fr.json` ; trois fichiers seulement
  lisent le catalogue (`routes.ts:15`, `exchanges.spec.ts:15`, `review.spec.ts:16`).
- **Quoi** : c'est le parti du dépôt (le parcours prouve ce que l'utilisateur lit), et il a sa valeur.
  Son coût : EP-25 (refonte ergonomique, en cours) renomme des libellés, et rien au palier rapide ne
  dit quels parcours citent un texte disparu — l'échec vient au palier complet, parcours par parcours,
  cinq à quinze secondes d'attente chacun.
- **Proposition** : un test `node` de quelques secondes qui relève les littéraux `name:` des parcours
  et nomme ceux qui étaient une valeur du catalogue et ne le sont plus. Coût : une soixantaine de
  lignes ; risque de ne pas le faire : des passages complets perdus pendant EP-25.
- **Confiance** : confirmé (décompte par script).

### FTE-14 — Commentaire périmé dans le harnais d'axe des composants

- **Issue** : #4450 (EP-36), ouverte le 2026-11-21, avec FTE-10.
- **Où** : `frontend/src/test/axe.ts:9-10` : « US-0200, to come — today only `e2e/paste.spec.ts` runs
  axe in one ».
- **Quoi** : US-0200 est livrée et `e2e/accessibility.spec.ts` audite chaque écran ; le commentaire
  dit le contraire à qui lit le harnais pour savoir ce qu'il reste à couvrir.
- **Confiance** : confirmé.

## Points forts

- **Aucun échec toléré, et le harnais le tient** : `retries: 0` (`playwright.config.ts:415`), aucun
  `waitForTimeout`, aucune pause fixe hors deux attentes bornées et commentées du royaume
  (`service/sign-in.spec.ts:200`, `service/password.spec.ts:113`) ; les nouvelles tentatives sont des
  `toPass` qui rejouent un geste tant que l'hydratation ne l'a pas reçu, jamais une assertion relâchée.
- **Un parcours contre le service par domaine livré, qui écrit puis relit** : EP-03
  `service/accounts.spec.ts`, `roles.spec.ts`, `password.spec.ts` ; EP-04 `revision-cycle.spec.ts:92`,
  `projects.spec.ts:602-866` ; EP-05 `reference-*.spec.ts`, `service/reference-manager.spec.ts` ; EP-06
  `planning-service.spec.ts`, `exchanges.spec.ts:231` ; EP-07 `pricing.spec.ts`, `undo.spec.ts:143`,
  `exchanges.spec.ts:347` ; EP-09 `actual-costs.spec.ts:189`, `remaining.spec.ts:434`.
- **La garde du contrat** (`service/contract.ts`, `mode.ts`) : chaque parcours contre le service
  échoue sur une réponse hors schéma écrite au journal de Prism, la fenêtre de lecture est prouvée, et
  le démontage relit la course entière.
- **Vingt exigences confrontées à leur Vérif** : WF-PLA-0080, 0090, 0020, 0030, 0140, WF-CYC-0020,
  0030, 0050, 0090, WF-REV-0010, 0020, 0090, WF-CRE-0020, 0040, WF-DAT-0120, WF-INTF-0110, WF-PRJ-0030
  tiennent la ou les phrases qu'ils annoncent, souvent citées en commentaire ; les écarts sont FTE-03
  (WF-PLA-0110, 0120), FTE-04 (WF-DEV-0070) et FTE-05 (WF-CRE-0030, 0050).
- **Faux client typé par le contrat** (`src/test/fixtures.ts`) : un exemple que le contrat ne cite pas
  pour ce statut de cette opération ne compile pas ; un appel sans réponse échoue.
- **Aide en ligne** : 69 fichiers par langue, mêmes noms, aucun lien interne cassé, une page par code
  de la table (32 écrans) ; `help.test.ts` le tient.
- **Couverture** : exclusions limitées aux tests, au client engendré et à `src/test/` ; sur 495
  fichiers de production, cinq seulement ne sont atteints par aucun test, même indirectement — des
  `loading.tsx` de 12 à 13 lignes (`src/app/{system,reference,portfolio,admin,account}/loading.tsx`).

Les vingt plus gros fichiers sans test voisin ni import direct depuis un test (tous atteints par un
test à travers un autre module ; lignes) : `components/remaining/kanban-card.tsx` 602,
`admin/user-cells.tsx` 520, `admin/user-dialogs.tsx` 509, `grid/header-cell.tsx` 456,
`risks/risk-form.tsx` 377, `grid/structure-dialogs.tsx` 303, `grid/grid-table.ts` 261,
`indicators/project-indicators.tsx` 260, `commands/confirmed-command.tsx` 217,
`indicators/indicator-sections.tsx` 208, `exchanges/report-commands.tsx` 207,
`admin/author-filter.tsx` 173, `exchanges/duration-rule.tsx` 164, `audit/audit-chips.ts` 149,
`risks/risk-dialog.tsx` 132, `risks/risk-cells.tsx` 126, `reference/section.tsx` 124,
`revisions/rate-update-command.tsx` 117, `shell/project-switcher.tsx` 110,
`risks/occurrence-report.tsx` 110 (tous sous `frontend/src/components/`).

## Couverture

- **Lu en entier** : `frontend/playwright.config.ts`, `frontend/vitest.config.ts` ; utilitaires d'`e2e/`
  — `mode.ts`, `hydration.ts`, `scroll.ts`, `axe.ts`, `routes.ts`, `in-progress.ts`,
  `planning-seed.ts`, `service/contract.ts` ; parcours — `accessibility.spec.ts`,
  `planning-service.spec.ts`, `pricing.spec.ts`, `actual-costs.spec.ts`, `revision-cycle.spec.ts`,
  `workload.spec.ts`, `task-tree.spec.ts` ; harnais — `src/test/fixtures.ts`, `setup.ts`,
  `setup-dom.ts`, `stderr.ts`, `axe.ts`, `served.ts`, `session.ts` ; outils — `catalogs.py`,
  `codecoverage.py`, `coverage.py`, `e2eparts.py` ; `deploy/e2e/Dockerfile` ; les cibles `e2e*`,
  `test-front`, `coverage-front*`, `catalogs` du `Makefile` ; les deux catalogues et les 138 fichiers
  d'aide par script.
- **Échantillonné** (parties lues) : `opening.spec.ts`, `own-project.ts`, `estimate-seed.ts`,
  `opened.ts`, `remaining.spec.ts`, `exchanges.spec.ts`, `reference-resources.spec.ts`,
  `reference-settings.spec.ts`, `reference-actual-cost-mapping.spec.ts`, `timelines.spec.ts`,
  `projects.spec.ts`, `grid.spec.ts`, `undo.spec.ts`, `planning.spec.ts`, `screens.spec.ts`,
  `system.spec.ts`, `admin.spec.ts`, `grid-frame.spec.ts`, `service/session.spec.ts`,
  `service/audit.spec.ts`, `src/test/markup.ts`, `harness.test.ts` (titres), `bench/contract-proxy.ts`
  (première moitié), `e2eimage.py` (en-tête), `.github/workflows/{e2e,service,front}.yml` (recherche de
  tentatives et d'échecs tolérés : aucun).
- **Lu par recherche seulement** (motifs : `skip`, `only`, `fixme`, pauses, `isVisible`, sélecteurs CSS,
  horloge, `inService`, citations) : les 93 fichiers d'`e2e/`. Moins de la moitié des `*.spec.ts` ont
  été lus ligne à ligne : la demande d'en lire la moitié n'est pas tenue.
- **Non lu** : `tab-walk.ts`, `focus-probe.ts`, `tab-walk.spec.ts`, `service/realm.ts` (891 lignes),
  `service/backups.spec.ts`, `service/account.spec.ts`, `service/reference-manager.spec.ts`,
  `entry.spec.ts`, `paste.spec.ts`, `keyboard.spec.ts`, `computed.spec.ts`, `structure.spec.ts`,
  `context.spec.ts`, `navigation.spec.ts`, `shell.spec.ts`, `tasks.spec.ts`, `review.spec.ts`,
  `indicators.spec.ts`, `portfolio.spec.ts`, `risks.spec.ts`, `amendment.spec.ts`, `departure.spec.ts` ;
  `bench/contract-proxy.test.ts` ; `tools/src/wftools/screens.py` et la cible `screens` ; la plupart
  des 32 fichiers de `src/test/` (aides de composants) ; le contenu des pages d'aide (exactitude des
  textes contre les écrans).

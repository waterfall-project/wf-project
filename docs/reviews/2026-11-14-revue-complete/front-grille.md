# Revue — la grille du front (`frontend/src/components/grid/`)

Commit `29785cc`. Chemins relatifs à `frontend/src/components/grid/` sauf mention contraire.
Aucune commande lourde lancée ; un seul petit script `node` a rejoué l'analyseur du presse-papiers
(`readBlock`) sur des cas limites, hors du dépôt.

## Synthèse

Le composant est tenu avec beaucoup de soin : le front ne calcule, ne trie ni ne somme rien, aucun
nombre ne passe par un flottant, la saisie suit sa ligne par identité, les réponses sont rangées par
adresse et par version (`answers.ts`), et les 847 tests affirment tous quelque chose. Aucun
commentaire d'exemption, aucun `any`.

Ce qui inquiète tient à ce que la grille **ne montre pas tout ce que le serveur écrit**, ou **ne tient
pas ce que ses commentaires promettent** :

- le collage dans le planning, qui ne lit que les tâches, laisse le serveur écrire sur les lignes de
  devis intercalées, sans que l'aperçu le dise (FGR-01) ;
- trois chemins où une saisie est perdue ou une autre ligne touchée : la valeur retapée pendant
  qu'une écriture de la même cellule est en route (FGR-02), le menu contextuel qui garde un indice et
  non une ligne (FGR-03), l'écriture en route quand la grille change elle-même d'adresse (FGR-04) ;
- la fenêtre de relecture qui suit un geste ou une annulation, pendant laquelle les cellules restent
  saisissables avec des versions périmées (FGR-05).

La performance n'a pas été mesurée (EP-26 la reprend) ; rien de quadratique n'a été trouvé sur les
lignes.

## Constats bloquants

### FGR-01 — Un bloc collé dans le planning écrit les lignes de devis que la grille ne montre pas

- **Issue** : #3339.
- **Où** : `paste.ts:324-354` (`unshownRows`, retour `read.narrowed ? "unretained" : undefined` à la
  ligne 353), `planning.tsx:90` (`PLANNING_KINDS = ["task"]`), `planning-grid.tsx:585`
  (`narrowing={nodeNarrowing(filters)}`, qui écarte `kinds` — `nodes.tsx:82-88`),
  `paste-dialog.tsx` (`Report` : des comptes seulement) ; côté service,
  `backend/src/waterfall/core/planning/interface/paste.py:735-742` (`start + index` dans
  `tree.order`) et `:465-475` (`_judged_line`).
- **Quoi** : le serveur remplit « le nœud à la même distance sous le nœud visé, dans l'ordre du
  plan », tâches **et lignes** (`tree.order`, `row_number` « its tasks and its lines », contrat
  `revisions.yaml:709-717`). La garde du front suppose qu'« une grille qui colle lit tous les genres
  de nœud, et ses numéros se suivent » (`paste.ts:312-314`) : le planning ne lit que les tâches.
  Depuis #2559, une ligne du plan attendue qui n'est ni montrée ni dans la réponse est prise pour
  « au-delà de la fin du plan » et laissée passer quand la lecture n'est pas restreinte.
- **Scénario** : projet chiffré, tâche 1 (rang 1) portant trois lignes de devis (rangs 2 à 4), tâche 2
  (rang 5). Dans le planning, sans recherche ni filtre, le planificateur colle une colonne de deux
  libellés sur le libellé de la tâche 1 pour renommer les tâches 1 et 2. `walkPlan` : attendu 2,
  montré 5 → hors place ; `held` ne contient pas 2 (pas « pliée »), `shown` non plus (pas « triée »),
  `narrowed` faux → `undefined`, l'aperçu est demandé. Le service juge la 2ᵉ ligne du bloc sur la
  **première ligne de devis** de la tâche 1 ; `label` est une colonne que la ligne porte : acceptée.
  L'aperçu dit « 2 lignes seront écrites, aucune refusée » ; confirmé, le libellé de la ligne de devis
  est écrasé, la tâche 2 inchangée ; `CellWrites.applied` laisse de côté la ligne que la lecture ne
  montre pas : rien à l'écran ne dit ce qui a été écrit. Même effet depuis la dernière tâche, où
  l'on attend des créations. Un bloc de plusieurs colonnes est, lui, refusé ligne à ligne
  (`FIELD_NOT_ACCEPTED`) — incompréhensible, mais sans écriture.
- **Vérifié** : le chemin du front ligne à ligne ; `tree.order`/`row_number` (`tree.py:67-68`) ; le
  jugement d'une ligne par `label`. Les tests ne le couvrent pas : `paste.spec.ts:258` et `:320`
  collent sur un projet sans ligne de devis, `paste.dom.test.tsx:497` sur le devis. Rien dans
  `docs/roadmap/` ni `DECISIONS.md` (qui dit au contraire, l. 3332, qu'un bloc « qui écrirait dans
  une ligne du plan autre que celle affichée à la suite est refusé par le front »).
- **Proposition** : la garde refuse dès qu'une ligne montrée sous la cible ne porte pas le rang
  attendu, et ne laisse passer le débordement que lorsque les lignes montrées sont épuisées ; pour
  une grille qui ne lit qu'un genre, la fin du plan ne se devine pas : soit le contrat fait porter
  au collage les genres que la grille lit (le serveur saute les autres), soit l'aperçu rend les
  rangs écrits et le dialogue les nomme. Test : `paste.dom.test.tsx`, planning sur un exemple dont
  la tâche visée porte des lignes — aucun aperçu demandé ; parcours `paste.spec.ts` sur un projet
  chiffré.
- **Confiance** : confirmé (lecture de bout en bout, non exécuté).

## Constats majeurs

### FGR-02 — Une valeur retapée pendant qu'une écriture de la même cellule est en route n'est pas envoyée

- **Issue** : #4430 (EP-34), ouverte le 2026-11-21, avec FGR-09, FGR-10.
- **Où** : `grid-keyboard.ts:503` (`parsed.value !== (entry.value(cell.row) ?? null)`),
  `dense-grid.tsx:636` (`rows: shownRows`), `cell-writes.ts:338-344` (les lignes ne portent que ce
  qui est **répondu**).
- **Quoi** : la validation compare la saisie à la ligne telle que le serveur l'a répondue, jamais à
  ce qui est en attente ; revenir à la valeur d'origine pendant l'aller-retour n'écrit rien, et la
  valeur intermédiaire l'emporte.
- **Scénario** : charge 10 ; l'utilisateur tape 100, Entrée, voit l'erreur, remonte, tape 10, Entrée
  avant la réponse (une écriture rejoue le moteur sur toute la structure, #3169). `"10" === "10"` :
  `writes.write` n'est pas appelé. La cellule reste « 100 » en attente, puis 100 répondu. La garde
  de la file (`cell-writes.ts:462`, #819.8), qui compare à la ligne **au moment où l'écriture
  part**, aurait fait juste si elle avait été atteinte. De même F2 sur une cellule en attente ouvre
  la saisie sur l'ancienne valeur.
- **Proposition** : ne plus filtrer dans `settle` quand la cellule a une écriture en attente (ou
  toujours appeler `writes.write`, dont la file décide). Test dans `entry.dom.test.tsx` : 100
  retenu, 10 retapé, réponse libérée → deux écritures, la cellule à 10.
- **Confiance** : confirmé.

### FGR-03 — Le menu d'une cellule garde l'indice de sa ligne : une relecture arrivée menu ouvert le fait agir sur une autre ligne

- **Issue** : #4431 (EP-34), ouverte le 2026-11-21.
- **Où** : `undo-commands.tsx:471`, `:494` (`setAt(positionOf(opened))`), `:387-389`
  (`rowAt(at.row)`, `acted(at.row)` à chaque rendu), `dense-grid.tsx:693-700` ;
  `structure-gestures.tsx:695-698` (indisponible : le menu reste ouvert), `:564-566` (une feuille
  est supprimée sans confirmation).
- **Quoi** : la ligne du menu est relue par indice à chaque rendu ; les dialogues, eux, capturent la
  ligne (`Opened.row`).
- **Scénario** : T1…T4 ; clic droit sur T2, « Supprimer » (feuille : immédiat). T2 reste affichée
  jusqu'à la relecture (les gestes n'appliquent pas leur réponse). Clic droit sur T3 : menu ouvert,
  `at.row = 2`, commandes « Enregistrement en cours… ». La relecture arrive : T1, T3, T4 ; l'indice
  2 est T4, `busy` tombe, « Supprimer » redevient disponible dans le menu resté ouvert ; le clic
  supprime **T4** et ses lignes. Le statut dit « T4 supprimée » ; Ctrl+Z la rend.
- **Proposition** : garder l'identité (`rowKey`) à l'ouverture et retrouver la ligne par elle — ou
  fermer le menu quand les lignes changent. Test : `structure-gestures.dom.test.tsx`, menu ouvert,
  relecture sans la ligne précédente, la commande part pour la ligne d'origine.
- **Confiance** : confirmé (chemin lu ; non exécuté — pièce non vérifiée : que Radix garde le menu
  ouvert à travers `router.refresh`, ce que son état interne laisse attendre).

### FGR-04 — Une écriture en route quand la grille change d'adresse par son tri, sa recherche ou un filtre : sa réponse est abandonnée, son refus n'est dit nulle part

- **Issue** : #4432 (EP-34), ouverte le 2026-11-21, avec FGR-08.
- **Où** : `cell-writes.ts:296-306` (`fresh`), `:375-382` (`current` ignore une autre époque),
  l'en-tête `:40-42` (« A navigation of the page waits for the writes under way ») ;
  `dense-grid.tsx:538-579` (`changeSort`, `search` → `router.push`) ;
  `frontend/src/components/shell/navigation-hold.ts:34` (seuls les clics sur `a[href]` sont
  retenus) ; `frontend/src/navigation/held-writes.ts:139-199` (un refus n'est dit par la barre
  qu'une fois l'écriture relâchée, donc l'écran parti).
- **Quoi** : la retenue des navigations ne vaut que pour les liens ; les navigations de la grille
  elle-même partent aussitôt. La réponse arrivée après la nouvelle lecture est jetée — succès comme
  refus — et l'écriture, encore « tenue » par l'écran resté monté, n'est pas remise à la barre.
- **Scénario** : devis, saisie ouverte sur une charge ; clic sur l'en-tête « Montant » : le pointeur
  valide la saisie (écriture partie), le clic trie. (a) Le serveur refuse (422, 412) : la grille
  triée montre l'ancienne valeur, aucun avis, rien dans l'historique des messages. (b) Il accepte,
  mais la lecture du tri, partie une milliseconde après, lit avant le commit : la grille montre
  l'ancienne valeur et l'ancienne `lock_version` ; la saisie suivante sur la ligne répond 412
  « Quelqu'un a modifié cette donnée ». Même chose avec la recherche ou un filtre de la barre.
- **Proposition** : faire attendre aux navigations de la grille les écritures en route (chaîner
  `request` sur elles, comme `heldClick`), ou dire le refus d'une écriture d'une autre époque
  (`noteRefusal` + avis). Test : `cell-writes.dom.test.tsx:309`, version refus — l'avis est dit ;
  parcours : saisir puis trier dans le même geste contre le service, la valeur est là.
- **Confiance** : confirmé pour le refus tu ; plausible pour (b) (dépend de l'ordre commit/lecture,
  non mesuré).

### FGR-05 — Pendant la relecture qui suit un geste ou une annulation, les cellules restent saisissables avec des versions périmées

- **Issue** : #4433 (EP-34), ouverte le 2026-11-21.
- **Où** : `structure-gestures.tsx:472-513` (la réponse d'un geste n'est pas appliquée aux lignes,
  seulement `account.reach`), `grid-keyboard.ts:424-437` (`start` ne lit aucun `busy`),
  `undo-run.ts` (aucune attente de la relecture) ; service :
  `backend/src/waterfall/core/planning/shaping.py:259-273` (`place` avance `lock_version` des nœuds
  déplacés et des frères décalés).
- **Quoi** : `busy` retient les gestes et le collage (#1224), pas la saisie d'une cellule ; elle
  part avec la `lock_version` d'avant le geste.
- **Scénario** : Alt+Maj+→ sur une tâche, puis saisie de sa durée avant que la relecture (plusieurs
  secondes sur mille tâches, #3171) n'arrive : 412, « Quelqu'un a modifié cette donnée », la saisie
  est à refaire. Après Ctrl+Z la fenêtre existe aussi sans que la grille se dise occupée (la
  promesse de l'action se résout avant l'arbre relu, défaut n° 22), et un geste lancé là part des
  voisines d'avant.
- **Proposition** : appliquer les nœuds répondus d'un geste par `writes.applied` (comme les
  sous-menus le font, `choice-menu.tsx:286-317`), ou enchaîner les écritures de cellule derrière
  `busy` ; pour l'annulation, tenir `busy` jusqu'à la relecture. Test : `structure-busy.dom.test.tsx`,
  cellule saisie pendant la relecture d'un déplacement → écrite avec la version répondue.
- **Confiance** : confirmé côté front et `shaping.py` ; la durée de la fenêtre n'est pas mesurée.

### FGR-06 — Les liens en conflit d'une tâche redatée ne suivent pas l'écriture

- **Issue** : #4434 (EP-34), ouverte le 2026-11-21.
- **Où** : `nodes.tsx:318` (`SCHEDULE` sans `link_conflicts`), `:324-335` ; lu par
  `planning.tsx:109`, `link-conflicts.tsx:52`, `frontend/src/components/gantt/layout.ts:43`.
- **Quoi** : `NodeSchedule` rend `link_conflicts` (requis) « so that the flag follows the write that
  creates or lifts it » (`docs/api/components/schemas/revisions.yaml:1323-1332`) ; le front ne pose
  que cinq des six champs.
- **Scénario** : une écriture redate un successeur et crée — ou lève — son conflit de lien : la
  marque de la cellule des prédécesseurs et celle du Gantt restent celles d'avant jusqu'au
  rechargement.
- **Proposition** : ajouter `link_conflicts` à `SCHEDULE` ; test dans `answers.test.ts` ou
  `planning-entry.dom.test.tsx` sur un exemple `rescheduled` qui porte un conflit.
- **Confiance** : confirmé côté front ; non vérifié : que le service range dans `rescheduled` une
  tâche dont seul le conflit change.

### FGR-07 — (hors périmètre strict, back — relevé au titre de l'angle « collage ») Les nombres collés sont lus sans la langue de l'utilisateur

- **Issue** : #4435 (EP-34), ouverte le 2026-11-21, avec BCH-09.
- **Où** : `backend/src/waterfall/core/estimate/pasting.py:81-87` (`_number`),
  `backend/src/waterfall/core/planning/interface/paste.py:198-199`, `:321-339` ; le front envoie le
  bloc tel que copié (`paste.ts:454`), et affiche en français un séparateur de milliers U+202F
  (`Intl`, vérifié : « 1 234,50 »).
- **Quoi** : `_number` remplace toute virgule par un point et n'ôte que U+0020 et U+00A0.
- **Scénario** : (a) interface anglaise, « 1,234 » heures copié d'un tableur → `Decimal("1.234")`,
  **accepté et écrit** 1,234 au lieu de 1234 ; « 1,234.50 » → refusé. (b) Tableur français récent,
  « 1 234,50 » avec U+202F → `NUMBER_INVALID`. (c) Planning : une date « 31/12/2026 », une durée
  « 10 j », un mode « Automatique » — ce que la grille elle-même affiche — sont refusés (ISO, unités
  et valeurs du contrat seuls). Le contrat (`PastePreview`) ne dit rien du format des cellules.
- **Proposition** : au relecteur du back de trancher ; soit le front normalise par la langue ce qu'il
  sait lire (`parseDecimal`, `parsePlanningDate`, `parseDuration`) avant l'envoi, soit le serveur
  reçoit la langue. Le cas (a) écrit une valeur fausse sans refus.
- **Confiance** : confirmé à la lecture de `_number` ; non exécuté.

## Constats mineurs

- **FGR-08 — Aucune garde à la fermeture de l'onglet pendant qu'une file d'écritures attend.**
  `cell-writes.ts:454-505` : les cellules d'une ligne partent l'une après l'autre ; aucune écoute
  `beforeunload` dans `frontend/src` (grep). Cinq cellules tabulées vite sur un service lent : F5 ou
  l'onglet fermé perd celles qui n'ont pas quitté le navigateur, sans avis (les cellules sont
  grisées « en attente », seul indice). Proposition : `beforeunload` tant que `underWay > 0`.
  Confiance : confirmé.
  **Issue** : #4432 (EP-34), ouverte le 2026-11-21, avec FGR-04.
- **FGR-09 — La marque « en attente » d'une seconde écriture de la même cellule est levée par la
  réponse de la première.** `cell-writes.ts:493` supprime l'attente par clé de cellule : taper 20
  puis 30 dans la même cellule montre 20, non grisé et sans `aria-busy`, le temps de la seconde
  écriture. Proposition : compter les attentes par cellule. Confiance : confirmé.
  **Issue** : #4430 (EP-34), ouverte le 2026-11-21, avec FGR-02, FGR-10.
- **FGR-10 — Le refus d'une cellule n'est pas levé quand on retape la valeur que porte la ligne, et
  le test qui l'annonce ne passe pas par l'écran.** `cell-writes.dom.test.tsx:545` (« lifts the
  refusal of a cell typed anew as the row holds it ») appelle `writes.write` ; à l'écran,
  `grid-keyboard.ts:503` n'appelle rien pour une valeur égale à celle de la ligne : la cellule reste
  `aria-invalid` jusqu'à la fermeture de l'avis (défaut n° 8). Se corrige avec FGR-02.
  **Issue** : #4430 (EP-34), ouverte le 2026-11-21, avec FGR-02, FGR-09.
- **FGR-11 — Une saisie invalide quittée au clic est abandonnée sans rien dire.**
  `cell-editor.tsx:178-184`. En français le point du pavé numérique tape « . » : « 12.5 » puis clic
  ailleurs → la cellule revient à sa valeur, sans avis (Entrée et Tab, eux, gardent la saisie et
  disent pourquoi). Comportement voulu et testé (`entry.dom.test.tsx:583`), mais c'est une saisie
  perdue en silence. Proposition : dire l'abandon dans la région des avis, avec le texte tapé.
  **Issue** : #4438 (EP-34), ouverte le 2026-11-21, avec FGR-12.
- **FGR-12 — Composition de caractères.** `cell-editor.tsx:34-45` valide sur Entrée sans lire
  `isComposing` (un IME confirme par Entrée) ; `grid-keyboard.ts:190` n'ouvre aucune saisie sur une
  touche morte (`key === "Dead"`), la lettre suivante ouvrant la saisie sans son accent sur une
  cellule non éditable. Portée faible (interface fr/en), mais les libellés sont libres.
  **Issue** : #4438 (EP-34), ouverte le 2026-11-21, avec FGR-11.
- **FGR-13 — Un maillon de la file d'une ligne qui lève condamne la file.** `cell-writes.ts:454` :
  `(queue ?? resolve()).then(async …)` sans rattrapage ; une exception hors de `entry.write` (qui
  est rattrapé) laisserait la cellule en attente pour toujours et sauterait les écritures suivantes
  de la ligne. Aucun chemin trouvé qui lève aujourd'hui : plausible seulement.
  **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue le dit « plausible
  seulement », sans scénario ni chemin qui lève aujourd'hui.
- **FGR-14 — Rendus et recalculs évitables.** `dense-grid.tsx:701-740` (`cells` neuf à chaque rendu,
  `BodyRow`/`BodyCell` sans mémo : chaque déplacement du curseur rend toutes les cellules de la
  fenêtre) ; `estimate-grid.tsx:301-337` et `planning-grid.tsx:367-479` refont la configuration, donc
  les colonnes de TanStack, à chaque écriture répondue (`version` en dépendance, alors que seul le
  collage la lit) ; `row-selection.tsx:622-623` (`carried`, O(lignes × sélection) à chaque
  `dragover`). Coût de la correction modéré, gain à mesurer : à ranger dans la mesure d'EP-26, qui
  ne liste pas ces points.
  **Suite** : abandonné le 2026-11-21, par décision de l'auteur — le point principal est mesuré et
  clos sans changement (#620 : 35 ms sur mille tâches) ; les deux autres n'ont ni mesure ni
  scénario, et la règle du dépôt est « aucune optimisation sans mesure ».

## Points forts

- Aucun calcul de montant, de date ni de total dans le périmètre (grep `Number(`/`parseFloat` : rangs,
  tailles, jours entiers seulement) ; les récapitulatives et les totaux viennent des réponses.
- Aller-retour affichage ↔ saisie vérifié : « 1 234,50 » ressaisi donne `1234.5`
  (`parseDecimal`, espace clavier ou U+202F), date courte, durée et prédécesseurs repartent de leur
  propre texte.
- Saisie, refus, sélection et ligne déplacée suivis par identité ; réponses hors d'ordre départagées
  par `structure_lock_version` et `lock_version` (`answers.ts`).
- `readBlock` : guillemets, tabulations et fins de ligne internes, CR seul, cellule non fermée —
  justes, et linéaire (20 000 cellules en quelques millisecondes).
- Écouteurs, observateurs et minuteurs tous rendus au démontage ; état plié relu avec garde de forme.
- Accessibilité : `grid`/`treegrid`, `aria-rowcount`/`aria-rowindex` sous virtualisation, un seul
  arrêt de tabulation, ligne active gardée rendue. `aria-colindex` absent, sans objet tant que
  toutes les colonnes sont dans le document.
- 847 tests, tous avec assertion ; aucun `eslint-disable`, `@ts-ignore`, `any`.

## Couverture

- **Lu en entier** : `dense-grid.tsx`, `grid-keyboard.ts`, `cell-writes.ts`, `answers.ts`,
  `cell-values.ts`, `cell-editor.tsx`, `paste.ts`, `columns.ts`, `row-window.ts`, `grid-table.ts`,
  `cell-attributes.ts`, `dense-grid-cell.tsx`, `dense-grid-parts.tsx`, `totals-row.tsx`, `fold.tsx`,
  `row-selection.tsx`, `structure-gestures.tsx`, `structure-rules.ts`, `structure-version.ts`,
  `undo-commands.tsx`, `undo-run.ts`, `nodes.tsx`, `planning.tsx`, `planning-grid.tsx`,
  `estimate-grid.tsx`, `remaining-grid.tsx`, `predecessors-entry.ts`, `settings.ts`, `query.ts`,
  `kept-address.ts`, `kept-filters.ts`, `kept-size.ts`, `pending-address.tsx`, `dated-entry.ts`,
  `computed-nodes.ts`, `node-dependencies.ts`, `planning-start.tsx`, `completion-date.tsx`,
  `row-choices.ts`.
- **Lu en grande partie** : `estimate.tsx`, `remaining.tsx` (les saisies), `paste-dialog.tsx`,
  `header-cell.tsx`, `computed-cell.tsx`, `structure-dialogs.tsx`, `filters.ts`, `period.ts`,
  `filter-bar.tsx`, `frame-width.ts`, `choice-menu.tsx` (`writeChange`).
- **Non lu, ou par recherche seulement** : `check-menu.tsx`, `grid-toolbar.tsx`, `range-filter.tsx`,
  `period-filter.tsx`, `values-filter.tsx`, `text-filter.tsx`, `choice-filter.tsx`, `list-pages.tsx`,
  `page-size.tsx`, `kept-list-size.tsx`, `selection-bar.tsx`, `pinning.ts`, `grid-floor.ts`,
  `planning-cells.tsx`, `planning-attachment.ts`, `link-conflicts.tsx`, `diff-mark.tsx`,
  `differences-only.tsx`, `difference-filter*.ts(x)`, `origin-*.ts(x)`, `breakdown-filter*.ts(x)`,
  `tree-filters.tsx`, `bar-choice.tsx`, `use-choice.ts`, `chip-kit.ts`, `filter-chips.ts`,
  `filter-fields.tsx`, `row-nature.tsx`, `estimate-cells.tsx`, `remaining-cells.tsx`. Les filtres
  d'une table plate et l'état de leur adresse (défauts n° 20 et 21) ne sont donc pas relus.
- **Tests** : les 75 fichiers passés au crible (assertion par test, exigences citées) ; titres lus de
  `cell-writes`, `entry`, `keyboard`, `paste`, `planning-writes`, `structure-gestures`, `undo` ;
  corps lus en partie de `cell-writes.dom.test.tsx`, `paste.dom.test.tsx`, `row-window.dom.test.tsx`,
  `entry.dom.test.tsx`. Moins d'un tiers lu ligne à ligne.
- **Parcours** : plans de `paste`, `keyboard`, `entry`, `computed`, `grid`, `grid-bar`, `undo` ;
  en-tête de `paste.spec.ts`. `grid-frame.spec.ts` et `frontend/bench/` non lus.
- **Hors périmètre lu pour suivre un chemin** : `src/i18n/format.ts` (nombres, dates),
  `components/commands/held.ts`, `navigation/held-writes.ts`, `shell/navigation-hold.ts`, et, au back,
  `core/planning/interface/paste.py`, `core/estimate/pasting.py`, `core/planning/shaping.py`,
  `core/planning/tree.py`.
- **Exigences** : WF-IHM-0030, 0040, 0050, 0060, 0090, 0100, 0110, 0130 lues ; §4.6.2 non confrontée
  (aucune mesure). EP-25, EP-26, EP-27 lus : aucun des constats ci-dessus n'y figure.

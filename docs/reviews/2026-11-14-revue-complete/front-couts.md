# Revue — front : chiffrage, coûts réels, reste à engager, échanges de fichiers, indicateurs, risques, portefeuille

Commit `29785cc`. Chemins relatifs à `frontend/src/` sauf mention contraire.

## Synthèse

L'état général est bon, et nettement au-dessus de ce qu'on attend d'un front de cette taille. La règle
« le front affiche, il ne calcule pas » est tenue partout où je l'ai cherchée : aucun montant, total,
marge, écart ni pourcentage n'est sommé, soustrait ou divisé dans le périmètre ; les seuls `Number()`
portent sur des positions de dessin (taille d'une bulle, borne d'un axe) ou des entiers d'adresse.
Tous les montants passent par `i18n/format.ts` depuis la chaîne du contrat ; un `Computable` absent
est dit « non calculable », jamais zéro. Les défauts déjà rencontrés (n° 1, 12, 20, 21, 24, 25) sont
traités avec soin dans les risques et le Kanban.

Ce qui inquiète tient à ce qui se passe **après** une écriture ou une tâche, pas au calcul :

- les cartes d'indicateurs du devis et du reste à engager ne suivent pas une saisie dans la grille :
  l'écran montre côte à côte un total à jour (ligne des totaux) et un total d'avant la saisie (carte) ;
- le suivi offre de « Relancer » l'application d'un import échoué, que le service refuse toujours ;
- plusieurs états de l'écran des imports restent figés ou verrouillés après un refus, un abandon ou
  une réponse tardive (compte rendu non relu après un 409, zone de dépôt verrouillée, formulaire
  d'une autre nature fermé par la réponse du précédent).

Les écrans en maquette (indicateurs, risques, portefeuille) n'ont que des défauts d'affichage de
faible portée (libellé faux d'un avis, seuils hors de l'axe, clés en double).

Aucun constat bloquant. 2 majeurs, 13 mineurs (dont 2 « déjà connus »).

## Constats bloquants

Aucun.

## Constats majeurs

### FCO-01 — Les cartes d'indicateurs du devis et du reste à engager restent celles d'avant la saisie

- **Issue** : #4437 (EP-34), ouverte le 2026-11-21.
- **Où** : `app/projects/[projectId]/revisions/[revisionId]/estimate/page.tsx:322` (`EstimateSummary`, lu
  une fois par la page, `readEstimateFigures`) et `…/remaining/page.tsx:285` (`RemainingSummary`,
  `readIndicators`) ; les écritures de cellule `api/actions/nodes.ts:119-150` (`updateEstimateLine`,
  `setLineRemaining`) ne relisent pas la page — le seul `refresh()` du module est celui de
  `updateStructure` (`:370`) ; côté grille, `router.refresh()` n'existe que pour un collage qui crée des
  lignes (`components/grid/estimate-grid.tsx:305-309`) et pour les gestes de structure
  (`components/grid/structure-gestures.tsx:481-486`) ; `components/grid/remaining-grid.tsx` n'en a aucun.
- **Quoi** : après une saisie de cellule, la grille met à jour ses lignes et sa ligne de totaux depuis la
  réponse (`total: (totals) => totals.reestimated_amount`, `components/grid/estimate.tsx:221`,
  `components/grid/remaining.tsx:280`), mais les cartes au-dessus — total du devis, provisions, écarts à la référence et à
  la révision précédente, ventilations par nature / sous-projet / lot, avis des taux manquants ; total du
  reste à engager, marge sur le budget, écart à la revue précédente, soldes par sous-projet et leur
  signal, couverture des risques — gardent les valeurs lues au chargement de la page.
- **Scénario** : un chef de projet ouvre le reste à engager (total 550, marge − 50), réestime une ligne de
  100 heures à 80 ; la ligne des totaux de la grille baisse, la carte « Reste à engager » et la marge
  restent à 550 et − 50, le signal de dépassement du sous-projet aussi, jusqu'à un rechargement. Il en
  conclut que la saisie n'a pas d'effet sur la marge, ou relève une marge fausse pour sa revue. Même
  chose au devis pour le total, les parts par nature et l'écart à la référence.
- **Vérifié** : aucune relecture ailleurs (`grep refresh` sur `components/grid` : trois sites, cités) ;
  aucun test ni parcours n'affirme une carte après une écriture (`e2e/remaining.spec.ts:306-336` lit les
  cartes à l'ouverture seulement) ; rien dans `docs/roadmap/` ni `DECISIONS.md` ne décide cet état. La
  carte porte « Calculé le <horodatage> », seul indice.
- **Proposition** : relire les indicateurs après chaque écriture réussie de la grille — une action serveur
  `readEstimateIndicators` / `readRemainingIndicators` appelée comme `readNodeTotals`, les cartes devenant
  un composant client alimenté par elle (pas un `router.refresh()` par cellule, qui relirait six mille
  lignes) ; à défaut, marquer la carte « antérieure à votre saisie » dès la première écriture. Test : dans
  `remaining.dom.test.tsx` / `estimate.dom.test.tsx` composés avec la page, saisir une cellule et affirmer
  que la carte « Total » montre la valeur du second exemple d'indicateurs ; un parcours `@shared` qui
  saisit puis lit la carte.
- **Confiance** : confirmé (chemin lu de la page à l'action ; non exécuté).

### FCO-02 — « Relancer » est offert pour l'application échouée d'un import, que le service refuse toujours

- **Issue** : #4424 (EP-33), ouverte le 2026-11-21, avec FCO-04.
- **Où** : `components/exchanges/report-commands.tsx:78-85` (`const command = () => applyFileImport(…)`,
  `track(result.data, { command, subject: filename })`) ; le suivi `components/tasks/task-entry.tsx:431-442`
  offre « Relancer » dès qu'une tâche échouée porte sa commande, et ne la retire que sur un refus `stale`
  (`components/tasks/tracking.ts:263-265`).
- **Quoi** : un import dont la tâche d'application échoue passe `failed`, son fichier supprimé
  (`backend/src/waterfall/core/exchanges/records.py:89-97`, `states.py:36-44`) ; `applyImport` répond alors
  409 `import_awaiting_decision` — « there is nothing left to apply » (`docs/api/paths/exchanges.yaml:505-512`).
  La commande remise au suivi ne peut donc qu'être refusée : défaut n° 6 de `typescript.md` (« commande
  offerte que le back refusera »).
- **Scénario** : un import de devis est analysé ; une saisie faite entre-temps fait échouer l'application
  (`exchanges.yaml:529-532`). Le panneau des tâches montre l'échec, son motif et « Relancer ». Le clic
  répond « condition manquante : import en attente de décision » ; le bouton reste, et chaque nouveau clic
  redonne le même refus. Rien ne dit qu'il faut déposer le fichier à nouveau, alors que l'entrée sans
  commande le dit (`tasks.relaunchFromScreen`).
- **Vérifié** : `risk-lifecycle.tsx` fait le bon choix pour la survenance d'un risque (pas de commande, et
  le dit en tête de fichier) ; l'export, lui, se relance légitimement (`export-form.tsx:113-118`).
- **Proposition** : ne pas remettre `command` au suivi pour l'application d'un import (`track(result.data,
  { subject: filename })`) : l'entrée dira de repartir de l'écran. Test : dans `exchanges.dom.test.tsx`,
  faire échouer la tâche d'application (`task_failed`) et affirmer qu'aucun bouton « Relancer » n'est
  offert, la phrase `relaunchFromScreen` présente.
- **Confiance** : confirmé (front, contrat et service lus ; non exécuté).

## Constats mineurs

### FCO-03 — La réponse d'un dépôt ferme le formulaire d'une autre nature ouvert entre-temps ; « Annuler » n'annule pas l'import

- **Issue** : #4429 (EP-33), ouverte le 2026-11-21, avec FCO-05, FCO-14.
- **Où** : `components/exchanges/import-commands.tsx:139-146` (`onClose()` à la réponse), `:232-237`
  (`close` met `open` à `undefined`, quel que soit le formulaire ouvert), `:251-253` (la bascule n'est
  pas retenue pendant l'envoi : `Command` ne reçoit pas `writing`) ; `open-import.ts:42-44`.
- **Quoi** : défaut n° 24, premier cas. Le formulaire de la nature A envoie son fichier ; l'utilisateur
  ouvre celui de la nature B (ou annule, puis rouvre) ; la réponse de A appelle le `close` de son rendu,
  qui ferme B — fichier choisi et période perdus —, rend le focus au bouton de A et mène au compte
  rendu de A. De même « Annuler » pendant l'envoi ferme le formulaire sans rien annuler : l'import est
  ouvert, et l'écran y navigue.
- **Scénario** : « Importer un devis », fichier de 8 Mio, « Analyser » ; pendant l'envoi, « Importer des
  coûts réels », choix du fichier et de la période ; la réponse du premier arrive : le second formulaire
  disparaît.
- **Proposition** : tenir les commandes de nature inactives (`writing`) tant qu'un envoi est en route,
  comme `OpensForm` des risques ; ou ne fermer que l'ouverture d'origine (compteur d'ouvertures). Test :
  retenir `POST /projects/{project_id}/imports`, ouvrir une autre nature, libérer, affirmer que le second
  formulaire reste avec son fichier.
- **Confiance** : confirmé à la lecture. Le manque de retour visuel pendant l'envoi, qui pousse à ce
  geste, est déjà connu (FCO-14).

### FCO-04 — Un refus définitif de l'application (409) laisse le compte rendu affiché « analysé », « Appliquer » toujours offert

- **Issue** : #4424 (EP-33), ouverte le 2026-11-21, avec FCO-02.
- **Où** : `components/exchanges/report-commands.tsx:88-90` (`setOutcome(result)` seul) ;
  `api/actions/exchanges.ts:90-92` (`refresh()` sur succès seulement). À comparer à
  `duration-rule.tsx:137-140`, qui relit l'écran sur un 409.
- **Quoi** : le contrat dit qu'un refus définitif à la soumission passe l'import à `refused` et supprime
  son fichier (`docs/api/paths/exchanges.yaml:523-530`). L'écran dit le refus sous la confirmation mais
  n'est pas relu : l'état reste « Analysé », « Appliquer » et le choix de la règle des durées restent
  offerts, l'explication « Refusé à l'application, le fichier est supprimé : relancez l'import » ne
  paraît pas. Un second essai répond `import_awaiting_decision`.
- **Scénario** : devis analysé sur la structure principale, le projet passe En cours, « Appliquer » →
  409 `project_before_in_progress`.
- **Proposition** : relire l'écran sur `conflict` comme `DurationRule` (ou `refresh()` dans l'action sur
  409). Test : dans `exchanges.dom.test.tsx`, « tells the condition a file rejected whole misses… »
  (`:615`) affirme en plus `router.refresh`.
- **Confiance** : confirmé côté front ; le passage à `refused` est lu au contrat, non rejoué contre le
  service.

### FCO-05 — La zone de dépôt du démarrage d'un projet reste verrouillée après un import abandonné ou refusé par son compte rendu

- **Issue** : #4429 (EP-33), ouverte le 2026-11-21, avec FCO-03, FCO-14.
- **Où** : `components/exchanges/file-drop.tsx:83-85` (`sent !== undefined` → retour sans rien dire),
  `:74-80` (seul l'échec de la tâche d'analyse libère la zone), `:163`.
- **Quoi** : une fois un fichier envoyé, la zone n'en prend plus d'autre. Si l'analyse réussit mais que le
  compte rendu rejette le fichier entier (`refusals`), ou que l'utilisateur abandonne l'import depuis le
  compte rendu affiché sur la même page (`report-commands.tsx:160-166`, `router.push(start)`), la zone
  reste montée avec « « fichier » est envoyé : son compte rendu s'affiche sur la page » — ce qui n'est
  plus vrai — et un nouveau fichier déposé est ignoré en silence (un dépôt pendant l'envoi, lui, dit
  « un envoi est en cours »).
- **Scénario** : page d'un projet sans tâche, dépôt de `planning.xml`, compte rendu avec un cycle de
  liaisons, « Abandonner », correction du fichier, nouveau dépôt : rien ne se passe. Contournement :
  replier et rouvrir « Importer un fichier MS Project », ou recharger.
- **Proposition** : libérer la zone quand l'adresse ne nomme plus l'import envoyé (`shownImport()`), ou
  dire pourquoi le dépôt est ignoré. Test dans `project-start.dom.test.tsx` : envoyer, rendre la page sans
  `import`, déposer un second fichier, affirmer le second `openImport`.
- **Confiance** : confirmé à la lecture.

### FCO-06 — Le compte rendu d'un import rend tous ses écarts et tous ses rejets, sans borne

- **Issue** : #4425 (EP-33), ouverte le 2026-11-21, avec BEX-07, BEX-10, BEX-11, DON-05.
- **Où** : `components/exchanges/import-report.tsx:195` (`differences.map`), `:107` (`rejected.map`) ; lu
  entier à chaque rendu de l'écran par `shown-import.ts:20-24`.
- **Quoi** : pour une extraction de coûts réels, chaque ligne créée ou modifiée est un écart (exemple
  `fixtures/api/import_actual_costs_first.json` : 3 écarts pour 4 lignes lues). Au volume de §4.6.2
  (18 000 lignes de coût), le premier import d'un projet rend un tableau de 18 000 rangées, relu et
  re-rendu à chaque relecture de l'écran (fin d'analyse, page de la liste des imports, changement de
  règle). Ni le contrat ni le service ne bornent `differences` (pas de borne trouvée dans
  `backend/src/waterfall/core/exchanges`).
- **Proposition** : montrer les N premiers écarts et le décompte du reste (le décompte par nature de
  changement devant alors venir du serveur — modification du contrat), ou paginer le compte rendu. Coût :
  une opération ou des compteurs de plus au contrat ; risque de ne rien faire : un écran de plusieurs Mo
  au premier import réel. Preuve : mesurer l'écran des imports sur le témoin de volume.
- **Confiance** : plausible — non mesuré ; pièce non vérifiée : le temps réel de rendu à 18 000 rangées.

### FCO-07 — Indicateurs : l'avis « Calculé sur une autre révision » nomme « sans nom » la révision affichée

- **Issue** : #4443 (EP-35), ouverte le 2026-11-21, avec FCO-08, FCO-09.
- **Où** : `app/projects/[projectId]/revisions/[revisionId]/indicators/page.tsx:416`
  (`<ComputedElsewhere history={named.get(history)} />`), `:242` (`readRevisionsOf` écarte la révision
  affichée de `named`), `:264-267`.
- **Quoi** : quand l'évolution des indices est calculée sur la révision de la route alors que les
  indicateurs le sont sur une autre, `named.get(history)` est `undefined` et l'avis dit « …calculée sur la
  révision « sans nom » » au lieu de « révision en cours ». `nameOf` (`:402-403`) sait la nommer, mais
  n'est pas employé ici.
- **Scénario** : écran des indicateurs de la révision en cours, date de calcul (`as_of`) antérieure au
  dernier marquage : l'API calcule les indicateurs sur la dernière révision marquée antérieure
  (`docs/api/paths/analysis.yaml:240-244`), l'évolution reste sur la révision en cours.
- **Proposition** : passer le nom par `nameOf(history)` à `ComputedElsewhere`. Test dans `page.test.tsx` :
  `at({ as_of: … })` sur la révision en cours avec `project_indicators_marked`, affirmer « Current
  revision » dans l'avis (les tests `:327-386` ne couvrent que la route d'une révision marquée).
- **Confiance** : confirmé à la lecture (écran en maquette, EP-10 non livré).

### FCO-08 — Évolution d'un indice : les seuils sortent du graphique quand tous les points sont sous eux

- **Issue** : #4443 (EP-35), ouverte le 2026-11-21, avec FCO-07, FCO-09.
- **Où** : `components/indicators/index-chart.tsx:128-135` (axe `min: 0`, sans `max`), `:147-157`
  (seuils en `markLine`).
- **Quoi** : ECharts ne tient pas compte d'une ligne marquée pour l'étendue d'un axe — le dépôt le sait et
  le corrige pour la capacité du plan de charge (`components/portfolio/workload-chart.tsx:64-67`). Ici
  rien ne le fait : un projet dont les indices valent tous 0,6 a un axe de 0 à 0,7, et les seuils de
  vigilance (0,9) et d'alerte (0,8) ne sont pas tracés — précisément pour le projet en alerte.
- **Proposition** : `max: ({ max }) => Math.max(max, Number(watch), Number(alert))`, comme le plan de
  charge. Test dans `charts.dom.test.tsx` : l'option porte un `max` qui atteint le seuil le plus haut.
- **Confiance** : plausible — comportement d'ECharts non rejoué, attesté par le commentaire du dépôt.

### FCO-09 — Évolution d'un indice : clés en double et libellé « Révision en cours » sur un projet sans révision en cours

- **Issue** : #4443 (EP-35), ouverte le 2026-11-21, avec FCO-07, FCO-08.
- **Où** : `components/indicators/index-chart.tsx:188` (`key={`${scope.scope}-${point.revision_id}`}`),
  `:192` (`point.version_name ?? t("currentRevision")`).
- **Quoi** : le contrat dit que le dernier point porte « `revision_id` … of the last marked revision on a
  project that has none » (`docs/api/components/schemas/indicators.yaml:731-735`) : il partage alors
  l'identifiant du point de cette révision marquée. Deux rangées de la table ont la même clé (avertissement
  React, rangée mal réconciliée), et la dernière se nomme « Révision en cours » alors que le projet n'en a
  pas.
- **Proposition** : clé `${scope.scope}-${point.at}` ; nommer le dernier point « au jour » plutôt que
  « révision en cours ». Test : un exemple d'historique sans révision en cours (à ajouter au contrat, il
  n'en cite aucun).
- **Confiance** : plausible — lu au contrat ; aucun exemple ne le sert, EP-10 non livré.

### FCO-10 — Kanban : chaque choix de carte rend à nouveau toutes les cartes

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue le dit « plausible, non
  mesuré » : aucun profil ne montre de lenteur à mille cartes, et le gain reste à prouver avant d'y
  passer une demi-journée.
- **Où** : `components/remaining/kanban.tsx:303-357` (`actions`, objet neuf à chaque rendu, donné à chaque
  `Card`), `components/remaining/kanban-card.tsx:511` (`Card` sans `memo`).
- **Quoi** : le Kanban rend toutes les tâches du projet (mille sur le témoin, sans fenêtre) ; un focus,
  une flèche, un glisser changent l'état du plateau et rendent les mille cartes. Même famille que le
  défaut n° 14.
- **Proposition** : `memo(Card)` avec des rappels stables (`useCallback`/`useRef`) et les seules props qui
  changent (`selected`, `tabStop`, `writing` ramenés à des booléens par carte). Coût : une demi-journée ;
  gain à mesurer au profileur sur le témoin ; risque de ne rien faire : flèches lentes sur mille tâches.
- **Confiance** : plausible — non mesuré.

### FCO-11 — Portefeuille : un refus 422 autre qu'une période mène à l'écran de panne, ou est dit « période refusée »

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — portée faible, dite par la revue :
  seule une adresse tapée à la main y mène, les menus et les préférences conservées n'offrent que
  des valeurs admises.
- **Où** : `app/portfolio/workload/page.tsx:73` (`readOrFail("getPortfolioWorkload")`),
  `components/portfolio/address.ts:145-148` (`readThreshold` admet « -1 » ou « 17 »), `:120-123`
  (`org_node_id` admis sur `[\w-]+`) ; `app/portfolio/refused.tsx:32-40`.
- **Quoi** : le contrat déclare pour le plan de charge agrégé un 422 sur un nœud inconnu, un seuil ou un
  horizon hors bornes (`docs/api/paths/portfolio.yaml:149-154`) ; la page le lève en écran de panne. Les
  autres vues passent par `readView`, qui prend tout 422 pour une période refusée : un nœud inconnu y est
  dit « le serveur refuse la période demandée ».
- **Scénario** : adresse saisie ou conservée d'une version précédente
  (`/portfolio/workload?under_load_threshold=5`). Portée faible : les menus n'offrent que des valeurs
  admises.
- **Proposition** : borner `readThreshold` à [0, 1] et n'admettre qu'un UUID pour le nœud ; lire le plan
  de charge par `readView` et dire le champ refusé. Test dans `app/portfolio/pages.test.tsx` avec
  `portfolio_workload_horizon_refused`.
- **Confiance** : plausible (maquette, EP-11 non livré ; le comportement du service n'existe pas encore).

### FCO-12 — Chaînes bâties à la main dans des phrases d'interface

- **Issue** : #4462 (EP-37), ouverte le 2026-11-21, avec FAR-07.
- **Où** : `components/exchanges/calendar-gap.tsx:37-39` (`.join(", ")` des jours et de leurs heures),
  `:68` (`${time.from}–${time.to}`), `components/exchanges/import-commands.tsx:214-217` (`.join(", ")`
  et l'espace de fin collé à la phrase), `components/risks/risk-form.tsx:235` (`"—"`),
  `components/portfolio/portfolio-views.tsx:153` (`format.number` de next-intl là où le journal des
  imports emploie `formatDecimal`, `components/costs/import-journal.tsx:58`).
- **Quoi** : ce que `typescript.md` laisse à la revue (« une chaîne bâtie par une fonction ou une méthode
  (`.join`, `.concat`) ») ; le reste du périmètre emploie `format.list`. Sans effet visible en français
  et en anglais.
- **Proposition** : `format.list(…)` et une clé de catalogue pour la plage horaire et le tiret.
- **Confiance** : confirmé.

### FCO-13 — Deux tests citent une exigence sans son indice de révision : la citation n'est pas comptée

- **Issue** : #4451 (EP-36), ouverte le 2026-11-21, avec BAC-10, BRC-10, FAR-05.
- **Où** : `components/estimate/estimate-summary.dom.test.tsx:60`,
  `components/remaining/remaining-summary.dom.test.tsx:17` (`[WF-IHM-0020]`).
- **Quoi** : `make requirements` ne lit que `\[(WF-[A-Z]+-\d{4}-[A-Z])\]`
  (`tools/src/wftools/coverage.py:54`) : ces deux citations sont inertes, sans erreur. Le même motif
  existe hors de mon périmètre (`commands/exit-command.dom.test.tsx`, `app/(home)/page.test.tsx`).
- **Proposition** : `[WF-IHM-0020-A]` ; faire échouer l'outil sur une citation sans indice.
- **Confiance** : confirmé.

### FCO-14 — Rien ne montre qu'un envoi ou une demande est en route, et l'écran des imports n'est pas relu à la fin d'une application — déjà connu (#3103, #3217, EP-25 US-2170)

- **Issue** : #4429 (EP-33), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue, avec FCO-03, FCO-05.
- **Où** : `components/exchanges/import-commands.tsx:150-200` (`aria-busy` seul, bouton « Analyser »
  inchangé pendant un dépôt de 10 Mio), `export-form.tsx:113-121` (rien dans le formulaire après la
  demande), `duration-rule.tsx:148-158` (le bouton radio revient à la règle en vigueur pendant la requête,
  défaut n° 21), `import-report.tsx:487-495` (la fin de la tâche n'est suivie que pour `analysing` : après
  l'application, l'écran reste « application en cours » jusqu'à « Relire l'écran » du suivi) ;
  `app/projects/[projectId]/page.tsx:168` (`then` est indéfini quand l'import crée la première révision :
  l'écran ne mène à la grille qu'après une relecture manuelle).
- **Proposition** : celles d'US-2170 ; y joindre le suivi de `entry.task` pour l'état `applying`.
- **Confiance** : confirmé.

### FCO-15 — Le jour proposé pour démarrer ou terminer une tâche est celui du poste — déjà connu (#2527, #3199, EP-25 US-2200)

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — le reste est un raccourci de
  filtre au jour UTC, choix écrit dans le code, décalé d'un jour seulement pour un marquage fait
  dans l'heure ou les deux heures après minuit.
- **Où** : `components/remaining/address.ts:150-154` (`today()`), employé par
  `components/remaining/kanban-card.tsx:284` et `components/grid/completion-date.tsx:33` ;
  `components/risks/address.ts:26-28` (`universalDay`, jour UTC du dernier marquage).
- **Confiance** : confirmé.

## Points forts

- Aucun calcul de montant dans le front : cartes, totaux, parts, marges, signaux et zones sont ceux du
  serveur ; `formatShare`, `shiftPoint` et `compareDecimals` (`i18n/format.ts`) travaillent sur les
  chaînes, sans flottant ; une valeur non calculable est dite, avec sa raison.
- Les commandes suivent `available_commands` partout (imports, exports, risques, Kanban, exclusion) ;
  aucune déduction depuis une permission ou un état.
- Réponses tardives traitées dans les risques (`useRiskDialog`, compteur d'ouvertures, écriture gardée
  par risque), le Kanban (`AnsweredCards`, départage par `lock_version`), le compte rendu de survenance
  (`current` au nettoyage de l'effet), l'abandon d'un import (`shownImport() === importId`).
- Refus du serveur dits à leur champ (périodes, bornes, sous-projet inconnu) et filtres gardés pour
  être corrigés ; saisie conservée après un refus dans les formulaires lus.
- Graphiques : alternative en table partout, zones distinguées par forme et trait, infobulles échappées
  (`escapeHtml`), dates de planning placées en UTC.
- Tests denses et précis sur les échanges, le Kanban et les risques, bâtis sur les exemples du contrat ;
  les gestes retenus (`held`) éprouvent les réponses en désordre.

## Couverture

- **Lu en entier (code de production)** : `components/estimate/estimate-summary.tsx` ;
  `components/costs/` (9 fichiers) ; `components/remaining/` (8) ; `components/exchanges/` (14) ;
  `components/indicators/` (5) ; `components/portfolio/` (12) ; `components/risks/` sauf les en-têtes de
  `risk-filters.tsx`, `risk-chips.ts`, `risks-grid.tsx` (corps lus) ; pages `exchanges`, `actual-costs`,
  `indicators`, `risks`, `estimate`, `remaining`, `kanban` ; `app/portfolio/{workload,cost-curve,projects,
  pilot-health}/page.tsx`, `nodes.ts`, `refused.tsx` ; `api/actions/{exchanges,costs}.ts`.
- **Lu en partie** : `app/projects/[projectId]/page.tsx` (la partie des imports) ;
  `api/actions/{nodes,risks}.ts` (signatures et relectures) ; `components/tasks/{task-entry,task-tracker,
  following}.tsx`, `components/commands/{command,held,rejection}`, `i18n/format.ts`,
  `components/projects/project-start.tsx` — pour suivre un chemin, non pour les relire.
- **Tests échantillonnés (moins du tiers demandé, en profondeur)** : lus en entier
  `costs/address.test.ts`, `estimate/estimate-summary.dom.test.tsx`,
  `remaining/remaining-summary.dom.test.tsx` ; titres et quelques cas de `exchanges/exchanges.dom.test.tsx`,
  `import-report.dom.test.tsx`, `follow-analysis.dom.test.tsx`, `costs/cost-line-scope.dom.test.tsx`,
  `remaining/kanban-reading.dom.test.tsx`, `indicators/charts.dom.test.tsx`,
  `portfolio/portfolio-views.test.tsx`, et la partie « autre révision » de
  `…/indicators/page.test.tsx`. Aucun test vide trouvé dans l'échantillon.
- **Non lu** : `app/portfolio/{performance,cost-structure,risks}/page.tsx` et `loading.tsx` (seulement
  leurs lectures, par `grep`) ; `app/projects/[projectId]/revisions/page.tsx` et `task-tree/page.tsx` ;
  les autres tests des risques, du portefeuille et du Kanban ; les parcours `e2e/`.
- **Hors périmètre, non couvert, et pourtant sur le chemin des angles demandés** : l'interrogation
  périodique des tâches (arrêt au démontage, à l'erreur, à l'expiration de session, reprise après
  rechargement : `components/tasks/`), la route de téléchargement d'un export (`/tasks/[taskId]/result`,
  nom de fichier, refus), et les grilles de devis et de reste à engager elles-mêmes (`components/grid/`).
- Rien n'a été exécuté : ni tests, ni lint, ni rendu ; les constats « plausibles » le disent.

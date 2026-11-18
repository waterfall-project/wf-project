---
id: EP-27
titre: Comparer la révision lue à une révision marquée dans les grilles où l'on travaille
statut: livré
depend_de: EP-26
famille: front, back
issue: 3482
---

# EP-27 — Comparaison dans les grilles

## Objet

La comparaison de deux révisions marquées vit aujourd'hui sur l'écran « Révisions », dans une grille
à part qui dit ce qui change sans en donner les valeurs, et refuse la révision en cours — le cas le
plus utile. La spécification 1.0.6 en fait une dimension du contexte de lecture : une révision lue,
en cours ou marquée, et une base, toujours marquée, choisies dans le bandeau et lues dans les
grilles de planning, de devis et de reste à engager.

L'EPIC vient avant EP-08 : les avenants et les risques fusionnent des structures et s'appuient sur
une comparaison saine. Il vient après EP-26, parce qu'une comparaison lit deux structures.

## Ce qui en fait partie

- ce qui se compare : une révision en cours ou marquée contre une base marquée, dans les deux sens,
la révision en cours restant modifiable, la valeur de base rendue (#3176, WF-REV-0080) : US-2320 ;
- les lectures d'une grille ouvertes à qui la consulte sans consulter les révisions (WF-REV-0080 ;
décision de l'auteur du 2026-11-15, au cadrage) : US-2320 ;
- le choix de la révision lue et de la base dans le bandeau de contexte, la base portée par
l'adresse entre les trois grilles (#3178, WF-IHM-0020, WF-IHM-0010) : US-2330 ;
- les marques des lignes et des cellules, les colonnes d'écart (US-2340), les totaux de la révision
lue et de la base (US-2350), le repli des branches sans écart (US-2360) (#3179, WF-IHM-0150 à
WF-IHM-0170) ;
- l'écran « Révisions » réduit à l'historique et à ses commandes (#3177), et le sort des structures
et de la mise à jour des taux qu'il porte (#3180) ; la désignation de la référence en colonne de
l'historique, que #3090 laissait à trancher, s'y décide — EP-25 n'a mis que ses sections en cartes
(US-2130 ; décision de l'auteur du 2026-11-14, au cadrage d'EP-25) : US-2370 ;
- le parcours de la comparaison de PRJ-001, en quarantaine contre le service, réécrit sur les
grilles et rejoué (#3192) : US-2380 ;
- la mesure, à leur livraison et par l'outil d'EP-26 (WF-QUA-0060), des deux opérations du tableau
15 que cet EPIC sert — ouvrir une grille comparée à une révision marquée, saisir dans une grille
comparée —, ajoutées au rapport de mesures (décision de l'auteur du 2026-11-14, au cadrage
d'EP-26), et l'instruction de l'option 3 de #3168 : US-2390 ;
- les constats reçus qui ne tiennent pas à la comparaison (#2590, #2854, #2885, #3127, #3160,
#3401, #3467) : US-2400.

## Ce qui n'en fait pas partie

- la comparaison d'une structure différentielle ou du devis propre d'un risque : la comparaison ne
porte que sur la structure principale ;
- la phrase de WF-REV-0080 sur la révision obtenue par fusion d'un différentiel — EP-08, qui livre
la fusion et clôt l'exigence.

## Exigences réalisées

WF-IHM-0150, WF-IHM-0160 et WF-IHM-0170, nouvelles en 1.0.6, sont entières ici. WF-REV-0080 et
WF-IHM-0020 restent closes par EP-08, dont dépendent leurs phrases sur les différentiels et les
devis de risques ; cet EPIC en réalise les phrases ajoutées par la 1.0.6. WF-IHM-0010, close par
EP-02, y gagne une phrase, notée en écart dans les US qui la citaient (US-0090, US-0720) : US-2330
la cite avec tout son Vérif et réalise cette phrase, sans que sa portée change — comme EP-25 et
EP-26 citent l'exigence d'un autre EPIC dont une phrase tient à ce qu'ils changent.

#3127 relevait que WF-REV-0080 est dite close par EP-08 sans qu'aucune US d'EP-08 la cite : EP-08
est `à planifier`, ses US ne sont pas écrites, et son tableau la porte déjà en « fin ». Elle reste
close par EP-08, dont le cadrage la citera dans l'US de la fusion (cadrage, 2026-11-15).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0150-A` | Marques d’une comparaison dans les grilles | entière | US-2340 |
| `WF-IHM-0160-A` | Totaux d’une comparaison | entière | US-2350 |
| `WF-IHM-0170-A` | Repli des branches sans écart | entière | US-2360 |
| `WF-REV-0080-A` | Comparaison de deux révisions | début — close en EP-08, amorcée aussi en EP-15, EP-07 | US-2320 |
| `WF-IHM-0020-A` | Contexte de lecture affiché | début — close en EP-08, amorcée aussi en EP-02, EP-15 | US-2330 |

## Opérations du contrat

Une opération modifiée, avant le code qui la consomme (décision de l'auteur du 2026-11-15, au
cadrage) : `compareRevisions`. Le 409 d'une révision en cours est levé pour la révision lue
(`to_revision_id`) et gardé pour la base (`from_revision_id`) ; la réponse gagne, pour chaque
valeur modifiée, la valeur que la base portait, l'écart de chaque date, de chaque durée et de
chaque montant, et les totaux de la base ; elle se lit par qui consulte une grille. Écartée : la
comparaison lue par `listNodes`, qui laissait `compareRevisions` sans écran et touchait le chemin
de lecture qu'EP-26 a figé à l'octet.

Trois lectures changent de garde, non de forme : `getRevision`, `listCostStructures` et
`listRevisions` se lisent par qui consulte une grille comme par qui consulte les révisions
(US-2320).

Déjà servies, et consommées sans changement : `listNodes` — la grille sans base — ; les écritures
d'une structure, dont aucune ne change — `updateTaskFacet`, `updateEstimateLine`,
`setLineRemaining`, `setTaskProgress`, `setPredecessors`, `setNodeTracking`, `createNode`,
`moveNodes`, `deleteNode`, `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo`
(US-2340) ; `createRevision`, `abandonRevision`, `markRevision`, `designateReferenceRevision`,
`getRateUpdateProposal`, `applyRateUpdate` (US-2370).

`docs/api/DECISIONS.md` reçoit les pointeurs des écritures qui refusaient encore sans `fields` un
montant dérivé qui déborde (#3401 ; US-2400).

## Préalables

Par exception (décision de l'auteur du 2026-11-15, au cadrage ; README, « Branches »),
`epic/EP-27` se tire d'`epic/EP-26` dès la fusion de son lot pivot, **US-2270/L2 #3322** —
`compareRevisions` sur les lectures gardées, la moitié stable de toute comparaison —, et non de
`main` à la livraison d'EP-26. Elle reprend `epic/EP-26` à chaque lot que celle-ci fusionne, et se
fusionne dans `main` après elle, jamais avant. Les lots qui mesurent (US-2390) et celui du parcours
(US-2380) attendent en outre les bornes de temps d'US-2290/L1 #3324.

La spécification 1.0.6 est fusionnée.

## Définition de fini

- la révision en cours se compare à une révision marquée depuis chacune des trois grilles, la saisie
y reste ouverte, et les marques suivent chaque écriture ;
- l'écran « Révisions » ne porte plus de comparaison ;
- le parcours de la comparaison est rejoué contre le service (#3192) ;
- `make check-all` passe.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC.

- #2590 — front : le report #1057 par un geste de la grille de devis, une fois son écran servi ;
- #2854 — front : planning.spec.ts dit encore « the lines being EP-07's » une fois le témoin chargé
de ses lignes ;
- #2885 — front : l'erreur de timelines.spec.ts sur un compte gestionnaire absent ne dit pas où il
se définit ;
- #3127 — roadmap : WF-REV-0080-A dite close par EP-08, que aucune US d'EP-08 ne cite, et trois
mineurs d'US-2010/L2 ;
- #3160 — front : des commentaires au-delà de 100 colonnes dans import-report.tsx et file-drop.tsx ;
- #3176 — spec : la révision en cours comparée à une révision marquée, et la valeur de base de
chaque écart (WF-REV-0080) ;
- #3177 — front : l'écran « Révisions » est brouillon, et sa comparaison loin des grilles —
l'historique et ses commandes seuls ;
- #3178 — spec : la révision lue et la base d'une comparaison choisies dans le bandeau de contexte,
la base conservée entre les grilles (WF-IHM-0020, WF-IHM-0010) ;
- #3179 — spec : les écarts d'une comparaison lus dans les grilles de planning, de devis et de reste
à engager (exigences nouvelles, WF-IHM-0150 à 0170) ;
- #3180 — front : les structures et la mise à jour des taux de la révision lue sous l'historique de
l'écran « Révisions » ;
- #3192 — e2e : le parcours de la comparaison de PRJ-001 (revisions.spec.ts:121) en quarantaine
contre le service ;
- #3401 — back : `applyRateUpdate` refuse un montant débordé sans `fields`, alors que
`/cost_category_ids` en est l'origine — relevé pendant EP-26, reporté ici avec la famille des
écritures encore sans `fields` que nomme `docs/api/DECISIONS.md` (décision de l'auteur du
2026-11-15) ;
- #3467 — contrat : le paragraphe des causes sans champ de `docs/api/DECISIONS.md` (US-2260/L3) a
un retour à la ligne irrégulier — relevé pendant EP-26, reporté ici avec #3401, dont le lot
réécrit ce paragraphe ;
- #3532 — back : la lecture gardée projetée par `fields` relit encore le document entier (reporté
→ EP-27, décision de l'auteur du 2026-11-15).

## Conception

### Le contrat

Une opération change de forme, `compareRevisions` ; le reste du contrat ne bouge pas. La
modification se fait en un lot, avant tout code qui la consomme : schémas, description, exemples
engendrés, client du front régénéré, entrée de `docs/api/DECISIONS.md`.

- **Les deux révisions.** `to_revision_id` est la révision lue, en cours ou marquée ;
  `from_revision_id` la base, marquée. Le 409 `STATE_FORBIDS_OPERATION` (`revision_marked`) ne
  vaut plus que pour la base ; son exemple est réengendré sur une base en cours. Les noms des
  paramètres ne changent pas.
- **La valeur de base.** `ComparedNodeRead` gagne `base` : les valeurs que la base portait, sous
  les noms du nœud — `parent_id`, `task.…`, `estimate_line.…` —, pour les seuls champs que la
  lecture rend (`fields`) et dont la valeur diffère. Nul pour un nœud ajouté, inchangé ou retiré —
  ce dernier est déjà rendu sur ses valeurs de base. Une cellule est marquée quand `base` porte
  son champ : la grille ne compare rien.
- **L'écart.** `ComparedNodeRead` gagne `deltas`, de même forme, pour les seuls champs qui sont
  une date, une durée ou un montant : un nombre de jours calendaires, une durée en temps de
  travail dans l'unité de la durée lue, un montant ; la révision lue moins la base. Nul hors d'un
  nœud modifié : une ligne ajoutée ou retirée pèse dans les totaux, non dans une colonne d'écart.
- **Ce qui fait un nœud modifié.** `difference` vaut `modified` dès qu'une valeur saisie ou
  calculée du nœud diffère, toutes facettes comprises, que `fields` la nomme ou non. N'y entrent
  pas ce qui change d'une révision à l'autre sans que rien n'ait changé : les identifiants, les
  compteurs, le numéro de ligne, le rang, les champs modifiables ; un parent et un prédécesseur se
  rapprochent par la lignée. `NodeChange` garde ses valeurs, celles que WF-REV-0080 énumère, et
  gagne `other` : une autre valeur du nœud, que `base` nomme. Une tâche modifiée par son seul
  contenu garde un `changes` vide.
- **Les totaux.** `RevisionComparison` gagne `base_totals`, de la forme de `totals`, sur les
  lignes que la lecture retient dans la base, lignes retirées comprises, et `totals_delta`, leur
  écart signé, d'une forme nouvelle (`NodeTotalsDelta`). `totals` et `amount_deltas` ne changent
  pas.
- **Les lignes en écart du reste à engager.** Un paramètre nouveau, `include_differences`, fait
  retenir en outre les nœuds en écart que `progress` écarte : la grille de reste à engager
  l'envoie, elle seule. Ces lignes comptent dans les totaux, comme toute ligne retenue.
- **`difference`** reste un paramètre de `compareRevisions`, que les grilles n'envoient plus pour
  une comparaison : le repli se fait dans le navigateur.
- **Les exemples.** `wftools.mockcomparisons` et `wftools.mockdiff` engendrent `base`, `deltas`,
  `base_totals` et `totals_delta` dans les exemples existants, et un exemple de plus : la révision
  en cours du témoin comparée à la référence dont elle est issue, sur le sous-arbre de
  l'installation sur site.
- **Exigées en deux temps.** Le lot du contrat déclare les propriétés nouvelles sans les exiger :
  le service ne les rend pas encore, et chaque réponse est validée contre le contrat. Le lot du
  service qui en sert une la passe en exigée — `base` avec la comparaison d'une révision en cours
  (US-2320/L3), `deltas` avec US-2340, `base_totals` et `totals_delta` avec US-2350. Écarté : un
  seul lot pour le contrat et le service, au-delà de ce qu'une revue relit.

### Les gardes

Aucune forme ne change ; `docs/api/DECISIONS.md` les écrit.

| Opération | Aujourd'hui | Demain |
|---|---|---|
| `compareRevisions` | `estimate.read` | l'une de `planning.read`, `estimate.read`, `remaining.read` |
| `getRevision`, `listCostStructures`, `listRevisions` | `revisions.read` | `revisions.read`, ou l'une des trois ci-dessus |

`listNodes` ne demande déjà que `planning.read` pour les trois grilles : la comparaison rend ce
que `listNodes` rend, à qui le lit déjà. La fonction « Gestion des révisions » reste gardée par
`revisions.read` dans la navigation, et ses commandes par leurs permissions.

### Le service

- **Deux lectures, une union.** La base se lit dans sa lecture gardée (`kept_readings`, US-2270
  d'EP-26) ; la révision lue, par le chemin des colonnes (US-2220) si elle est en cours, dans sa
  lecture gardée si elle est marquée. Rien n'est gardé d'une comparaison : une révision en cours
  change à chaque écriture.
- **L'union** (`core/estimate/uniting.py`) compare toutes les valeurs de deux nœuds de même
  lignée, et rend pour chacun ce qui diffère et sa valeur de base. La liste des valeurs exclues
  est écrite une fois, à côté d'elle ; un test tient qu'une révision ouverte et non modifiée se
  compare inchangée à sa source, nœud par nœud.
- **La projection.** `base` et `deltas` se réduisent aux champs demandés dans `api/comparison.py`,
  comme le corps d'un nœud : le noyau ne connaît pas `fields`.
- **Les totaux de la base** se somment dans `core/estimate/comparing.py`, sur les lignes déjà
  comptées pour `amount_deltas`.
- **Les tests du back citent les trois exigences nouvelles.** L'EPIC est `front, back` : une
  exigence qu'il clôt n'est prouvée que si un test du back la cite (README, « Familles »). Les
  écarts de date et de durée citent WF-IHM-0150, les totaux de la base et la ligne retirée
  WF-IHM-0160, la marque des récapitulatives qui portent un écart et celle des branches sans
  écart WF-IHM-0170.

### Le front

- **L'adresse.** `base_revision_id`, que `navigation/context.ts` lit sur les trois grilles et
  porte de l'une à l'autre, comme `structure` entre le planning et le devis ; aucun autre lien ne
  la porte, et le témoin du dernier contexte ne la garde pas.
- **Le bandeau.** Deux choix sur le modèle de `StructureChoice` : la révision lue, sur tout écran
  qui en nomme une ; la base, sur les trois grilles lues sur la structure principale. Les bases
  proposées : la révision dont la révision lue est issue, puis la référence, puis les autres
  révisions marquées, de la plus récente à la plus ancienne. L'historique se lit une fois par
  requête (`listRevisions`, toutes ses pages).
- **La lecture.** `grid-screen.ts` lit `compareRevisions` quand l'adresse nomme une base et que
  la structure est la principale, `listNodes` sinon ; les lignes ont la même forme, `base` et
  `deltas` en plus.
- **Les marques.** La marque de ligne est celle d'un différentiel (`diff-mark.tsx`). La marque de
  cellule est un composant commun aux trois grilles : un signe, non la seule couleur, et la
  valeur de base dans une infobulle au survol et au focus, décrite pour un lecteur d'écran.
- **Les colonnes d'écart** s'ajoutent à la configuration de chaque grille, masquées par défaut,
  offertes au choix des colonnes quand une base est active ; leur visibilité se garde avec les
  réglages de la grille.
- **La relecture après une saisie.** Les écritures répondues, la grille relit son écran
  (`router.refresh`), une fois : les réponses plus fraîches qu'elle restent posées dessus
  (`answers.ts`), le curseur et les cellules en cours gardés. Hors comparaison, rien ne change.
- **Les totaux.** `totals-row.tsx` présente trois valeurs par total quand la lecture rend
  `base_totals`. Le panneau des écarts par nature de coût et par sous-projet reprend la
  présentation de la section de comparaison de l'écran « Révisions », avant qu'elle n'en parte.
- **Le repli.** « Écarts seulement » d'une comparaison est un état de `fold.tsx`, gardé dans
  l'onglet avec les plis, par grille et par révision : la grille retire de ses lignes rendues
  les nœuds inchangés dont aucun descendant n'est en écart, et pose une ligne de marque à la
  place de chaque suite. La pastille du bandeau disparaît pour une comparaison : ce n'est pas un
  filtre. Sur un différentiel, « Écarts seulement » reste le filtre du service.
- **L'écran « Révisions ».** `components/revisions/comparison-*.tsx` et `revision-comparison.tsx`
  sont retirés, avec la clé `comparison` des réglages de grille, qui n'est plus lue. La
  proposition de taux se lit par une action, à l'ouverture de son dialogue.
- **Les catalogues** reçoivent des clés de plusieurs lots : chacun n'y écrit que les siennes, et
  ils ne mettent pas deux lots « pas avec », comme dans EP-25 et EP-26.

### La mesure

Le parcours de mesure (`frontend/e2e/measure/steps.ts`) gagne ses étapes comparées : ouvrir
chacune des trois grilles de la révision en cours de PRJ-001 comparée à la référence, puis y
saisir une durée qui redate, mesurée jusqu'à la relecture dessinée. `make measure-version` les
porte au rapport. L'instruction de l'option 3 de #3168 se prend par `make measure-core`, qui
gagne la comparaison d'une révision en cours : la part des deux lectures, de l'union et du corps,
et le compte des nœuds qui diffèrent.

### Tables et migrations

Aucune : une comparaison ne garde rien, et les gardes sont du code.

### Modules touchés

| Module | US | Ce qui change, et ce qu'il expose |
|---|---|---|
| `docs/api`, `tools/src/wftools` (`mockcomparisons`, `mockdiff`) | US-2320 | le contrat de `compareRevisions`, ses exemples engendrés |
| `core/estimate` (`uniting`, `comparing`, son interface) | US-2320, US-2340, US-2350 | la révision lue en cours ; la valeur de base, l'écart et la marque de tout nœud ; les totaux de la base ; les lignes en écart qu'un filtre d'état écarte |
| `core/planning` (son interface) | US-2320 | rien de neuf : la lecture gardée et la lecture en colonnes, lues par leur interface |
| `api/comparison.py`, `api/revisions.py` | US-2320 | le corps nouveau ; les gardes |
| `core/estimate/keeping.py`, les écritures qui rechiffrent | US-2400 | les pointeurs des débordements |
| `frontend/src/navigation`, `components/context` | US-2330 | la base dans l'adresse ; les deux choix du bandeau |
| `frontend/src/components/grid`, les trois écrans de grille | US-2340, US-2350, US-2360 | la lecture comparée, les marques, les colonnes d'écart, la relecture, les totaux, le panneau, le repli |
| `frontend/src/components/revisions`, l'écran « Révisions » | US-2370 | l'historique et ses commandes ; la commande des taux |
| `frontend/e2e`, `frontend/e2e/measure`, `backend/measure`, `docs/measures` | US-2380, US-2390, US-2400 | le parcours, les étapes comparées, le rapport |

### Ordre de construction

En quatre temps.

1. **Le contrat, et ce qui ne l'attend pas**, en parallèle : la modification de
   `compareRevisions` (US-2320) ; les gardes des trois lectures (US-2320) ; le choix de la
   révision lue dans le bandeau (US-2330) ; la désignation de la référence et la commande des
   taux de l'écran « Révisions » (US-2370) ; les constats reçus (US-2400).
2. **Le service** : la comparaison d'une révision en cours, la valeur de base, les écarts, les
   totaux de la base (US-2320, puis US-2340 et US-2350 pour leur part de back).
3. **Les grilles**, sur le contrat modifié, le faux back servant ses exemples : la base dans
   l'adresse et le bandeau (US-2330) ; puis la lecture comparée et les marques (US-2340), dont
   dépendent les totaux (US-2350), le repli (US-2360) et le retrait de la comparaison de l'écran
   « Révisions » avec sa commande « Comparer à la révision lue » (US-2370).
4. **Le parcours et la mesure** (US-2380, US-2390), service et grilles livrés.

### Décisions

Prises par l'auteur le 2026-11-15, au cadrage, sauf mention.

- **`compareRevisions` étendu.** Écartée : la comparaison lue par `listNodes`, contre la décision
  du 2026-10-20 (#1193) qui en fait une opération à part, lue comme `listNodes`.
- **Les marques suivent une saisie par une relecture.** S'écarte, pour la seule grille comparée,
  de la règle d'EP-02 (« Qui appelle l'API ») qui remplace les lignes par la réponse de
  l'écriture sans relire la grille : le tableau 15 de la 1.0.6 donne deux secondes à cette
  saisie. Écartées : les marques dans la réponse de chaque écriture, une quinzaine d'opérations
  du contrat figé à changer ; une action qui ne relirait que les lignes, second chemin de lecture
  à tenir d'accord avec le premier (cadrage).
- **Toute colonne qui diffère est marquée, et fait un nœud modifié.** Étend la liste de
  WF-REV-0080 et de `NodeChange` (EP-15/US-0500/L1) : la réponse entre deux révisions marquées
  change pour les nœuds dont seul un libellé, une description ou un rattachement diffère. Écartée
  : les seules valeurs de WF-REV-0080, qui laissait sans marque une cellule différente de la
  base, contre WF-IHM-0150.
- **La marque d'un nœud ne dépend pas de `fields`** (cadrage). Écartée : une marque jugée sur les
  seuls champs lus, qui dirait une même tâche modifiée au devis et inchangée au planning.
- **Les trois lectures d'une grille ouvertes à qui la consulte.** Change une garde d'EP-04.
  Écartée : `compareRevisions` seul, qui laissait le Vérif de WF-REV-0080 non constaté sur
  l'écran.
- **Les lignes en écart du reste à engager par un paramètre, et comptées** (cadrage). Écartées :
  une règle implicite de `progress`, qui exposerait des tâches non démarrées sous un filtre
  d'état du planning ; des lignes montrées sans être comptées, où l'écart des totaux ne
  répondrait plus aux marques.
- **Le repli dans le navigateur** (cadrage, d'après la décision du 2026-11-14 sur #3179). Écarté
  : le filtre `difference` du service, qui retire des lignes de la lecture et refait la
  comparaison à chaque bascule.
- **L'option 3 de #3168 instruite par la mesure, sans lot.** Écartés : un lot sur verdict, qui
  engagerait une migration et un invariant sur chaque écriture sans revue ; l'écarter d'emblée.
- **Un objectif dépassé devient une issue à trancher** (cadrage, comme EP-26 pour #3171).
- **L'écran « Révisions »** : la désignation de la référence en commande de ligne ; les
  structures au bandeau ; les taux en commande de la révision en cours ; « Comparer à la révision
  lue » par un menu des trois grilles. Écartés : des cartes repliées, un écran de la révision,
  une grille d'arrivée imposée.
- **La base lue lève la comparaison.** Écarté : l'échange des deux révisions.
- **`epic/EP-27` tirée d'`epic/EP-26`.** Écartée : attendre la livraison d'EP-26, que retient son
  rapport de version.
- **Les pointeurs de la famille de #3401** (cadrage) : le lot établit par un scénario mesuré si
  chaque écriture peut déborder, et nomme le champ du corps qui porte la cause, jamais un champ
  que la requête ne porte pas ; une écriture sans tel champ reste refusée sans `fields`, et
  `docs/api/DECISIONS.md` le dit.

---

## US-2320 — Une révision, en cours ou marquée, se compare à une base marquée, et la comparaison rend la valeur de la base

- **statut** : fini
- **exigences** : `WF-REV-0080-A`
- **opérations** : `compareRevisions`, `getRevision`, `listCostStructures`, `listRevisions`
- **issue** : #3483

**En tant que** chef de projet, **je veux** comparer la révision que je lis, en cours ou marquée, à
une révision marquée de mon projet, et lire pour chaque valeur modifiée celle que la base portait,
**afin de** suivre ce que la révision en cours change sans attendre de la marquer.

**Critères d'acceptation.**

- écart : `WF-REV-0080-A` — « La comparaison d’une révision obtenue par fusion d’un différentiel
  avec la révision marquée qui la précède, de même année de référence, lorsqu’aucune autre
  modification n’a été faite entre les deux, restitue exactement les tâches et les montants
  budgétés de ce différentiel. » : la fusion est d'EP-08, qui clôt l'exigence ;
- écart : `WF-REV-0080-A` — « Les montants réestimés n’y diffèrent que par les lignes que le
  différentiel ajoute ou retire, par celles des tâches démarrées qu’il termine et par celles dont
  il change l’année de consommation ; une ligne existante dont le différentiel ne modifie que le
  montant budgété ne présente aucun écart de montant réestimé. » : EP-08, qui clôt ;
- écart : `WF-REV-0080-A` — « Entre deux révisions d’années de référence différentes, les montants
  réestimés diffèrent en outre sur chaque ligne dont le taux a été mis à jour ou projeté jusqu’à la
  nouvelle année de référence (WF-REV-0060), et sur chaque ligne de débours, dont le montant est
  projeté de même (WF-DEV-0030) ; les tâches et les montants budgétés restent ceux du
  différentiel. » : tenu sans différentiel par US-1530 (EP-07) ; le différentiel est d'EP-08, qui
  clôt ;
- `WF-REV-0080-A` — « Une tâche déplacée sous une autre récapitulative est présentée modifiée. » :
  tenu par US-1530 entre deux révisions marquées ; ici, de même quand la révision lue est en
  cours, avec la récapitulative qui la portait dans la base ;
- `WF-REV-0080-A` — « La révision en cours se compare à la révision marquée dont elle est issue :
  une tâche dont la fin y est repoussée de cinq jours est présentée modifiée, avec la date de fin
  de la base ; la date ramenée à celle de la base, la tâche n’est plus présentée modifiée. » :
  éprouvé sur PRJ-001 du témoin, la révision en cours contre la référence dont elle est issue ;
- `WF-REV-0080-A` — « La comparaison d’une révision marquée à une révision marquée postérieure
  présente retirées les tâches que la seconde ajoute. » : l'offre du témoin lue, la référence pour
  base ;
- `WF-REV-0080-A` — « Une révision en cours prise pour base est refusée. » : par le 409
  `STATE_FORBIDS_OPERATION` d'aujourd'hui, `params.missing_condition` à `revision_marked`, rien
  n'étant lu ;
- `WF-REV-0080-A` — « Un utilisateur qui consulte le planning sans consulter les révisions y active
  une comparaison. » : un compte qui porte `planning.read` sans `revisions.read` lit
  `compareRevisions`, et les trois lectures dont sa grille a besoin — `getRevision`,
  `listCostStructures`, `listRevisions` — ; la fonction « Gestion des révisions » et ses commandes
  lui restent fermées (décision de l'auteur du 2026-11-15, au cadrage) ;
- propre à l'US : le contrat change avant le code : la description, les paramètres, le 409 et les
  exemples de `compareRevisions` disent une révision lue, en cours ou marquée, et une base
  marquée ; un exemple engendré du témoin rend la révision en cours comparée à la référence ;
- propre à l'US : chaque nœud modifié rend, pour chacune de ses valeurs lues qui diffère, celle
  que la base portait — pour une tâche, ses dates, sa durée, son état et son parent ; pour une
  ligne, ses grandeurs et ses montants ; et toute autre colonne, un libellé ou une description
  compris — ; un nœud ajouté n'en rend aucune, un nœud retiré est rendu sur ses valeurs de base,
  comme aujourd'hui ;
- propre à l'US : un nœud dont une valeur diffère est dit modifié, quelle que soit cette valeur :
  une tâche seulement renommée l'est, qui ne l'était pas (décision de l'auteur du 2026-11-15, au
  cadrage) ; sa marque ne dépend pas des champs que la lecture demande ;
- propre à l'US : la comparaison d'une révision en cours se lit sur son état du moment : une
  lecture faite après une écriture en porte les marques, sans rien garder d'une lecture à
  l'autre ;
- propre à l'US : la base se lit dans sa lecture gardée (US-2270 d'EP-26) ; entre deux révisions
  marquées, la réponse d'aujourd'hui ne change que par ce qu'elle gagne ;
- propre à l'US : une révision comparée à elle-même garde sa réponse — chaque nœud inchangé, aucun
  refus (décision de l'auteur du 2026-11-14, #3176).

**Notes de réalisation.** `compare` (`core/estimate/comparing.py`) refuse aujourd'hui les deux
révisions d'un même test, et `api/comparison.py` demande `estimate.read`. Les trois lectures sont
gardées par `revisions.read` (`api/revisions.py`) : un compte qui ne le porte pas n'ouvre aucune
grille contre le service, le bandeau lisant `getRevision`.

**Hors périmètre.** La comparaison d'une structure différentielle ou du devis propre d'un risque ;
les écritures, dont aucune ne change (US-2340) ; les écarts et les totaux de la base, que portent
US-2340 et US-2350.

## US-2330 — La révision lue et la base d'une comparaison se choisissent dans le bandeau, et la base suit du planning au devis et au reste à engager

- **statut** : fini
- **exigences** : `WF-IHM-0020-A`, `WF-IHM-0010-A`
- **opérations** : `listRevisions`, `getRevision`, `compareRevisions`
- **issue** : #3485

**En tant que** chef de projet, **je veux** choisir depuis la grille où je travaille la révision
que je lis et celle à laquelle je la compare, **afin de** ne plus passer par l'écran « Révisions »
pour changer de révision ou pour activer une comparaison.

**Critères d'acceptation.**

- écart : `WF-IHM-0020-A` — « Chaque écran de données de projet nomme le projet et la révision
  affichée ; une grille ouverte sur une structure différentielle nomme cette structure. » : tenu
  par US-0100 (EP-02) et US-0500 (EP-15) ; constaté contre le service des différentiels par EP-08,
  qui clôt ;
- écart : `WF-IHM-0020-A` — « L'ouverture d'une révision marquée présente cet état et ne propose
  aucune commande de modification. » : tenu par US-0100 (EP-02), non touché ; EP-08 clôt ;
- écart : `WF-IHM-0020-A` — « Un indicateur affiché porte sa date de calcul. » : tenu par US-0100
  (EP-02), non touché ; EP-08 clôt ;
- écart : `WF-IHM-0020-A` — « Un filtre actif est visible sans avoir à ouvrir le panneau de
  filtres. » : tenu par US-0100 (EP-02), non touché ; EP-08 clôt ;
- `WF-IHM-0020-A` — « Depuis la grille de devis de la révision en cours, l'utilisateur choisit une
  révision marquée pour base sans quitter l'écran ; l'écran la nomme, et la comparaison se lève
  sans ouvrir aucun panneau. »
- `WF-IHM-0020-A` — « Depuis la même grille, il ouvre une autre révision du projet sans passer par
  l'historique. »
- écart : `WF-IHM-0010-A` — « Un utilisateur qui n'a ouvert aucun projet atteint le portefeuille, le
  référentiel, l'administration et l'écran d'état. » : tenu et clos par EP-02 (US-0090), non
  touché ;
- écart : `WF-IHM-0010-A` — « Dans un projet, le passage du reste à engager aux risques puis aux
  indicateurs conserve la révision affichée et le sous-projet filtré. » : tenu et clos par EP-02
  (US-0090) ; la révision choisie dans le bandeau est conservée de même ;
- écart : `WF-IHM-0010-A` — « Le retour au projet précédent depuis une fonction hors projet retrouve
  le même contexte. » : tenu et clos par EP-02 (US-0090) ; la base n'en est pas, elle n'est pas
  mémorisée ;
- `WF-IHM-0010-A` — « Une comparaison active sur le planning l'est encore sur le devis puis sur le
  reste à engager, avec la même base. »
- propre à l'US : tout écran dont le bandeau nomme une révision y offre le choix de la révision
  lue parmi les révisions du projet ; la révision choisie s'ouvre sur le même écran, le
  sous-projet filtré et la date de calcul conservés ;
- propre à l'US : sur les grilles de planning, de devis et de reste à engager, le bandeau offre
  pour base les révisions marquées du projet, hors la révision lue (décision de l'auteur du
  2026-11-14, #3176) ; il nomme la base choisie et offre de lever la comparaison ;
- propre à l'US : la base est portée par l'adresse, et par les liens entre ces trois grilles
  seulement ; les autres écrans ne la portent pas, et elle n'est gardée ni dans les préférences du
  compte ni avec le dernier contexte du projet : une grille ouverte sans elle ne compare rien ;
- propre à l'US : choisir pour révision lue la base d'une comparaison active lève la comparaison ;
  toute autre révision choisie garde la base (décision de l'auteur du 2026-11-15, au cadrage) ;
- propre à l'US : sur une autre structure que la principale, le bandeau n'offre pas de base, et
  choisir une autre structure lève la comparaison ;
- propre à l'US : une base que l'adresse nomme et qui n'est pas une révision marquée du projet est
  dite par l'écran comme tout refus de lecture, sans grille à moitié lue ;
- propre à l'US : les deux choix se font au clavier comme au pointeur, et la révision lue comme la
  base se disent à un lecteur d'écran.

**Notes de réalisation.** Le bandeau offre déjà le choix de la structure (`StructureChoice`), sur
le même modèle : un choix ne change que l'adresse, depuis l'adresse demandée en dernier
(`usePendingAddress`). L'ordre des bases proposées est à la conception (décision de l'auteur du
2026-11-14, #3178). La comparaison levée après un passage par un écran qui ne la porte pas est une
conséquence acceptée, que le Vérif ne dit pas (même décision).

**Hors périmètre.** Ce que les grilles montrent d'une comparaison (US-2340 à US-2360) ; l'écran
« Révisions » (US-2370).

## US-2340 — Les grilles de planning, de devis et de reste à engager marquent les écarts à la base, ligne par ligne et cellule par cellule, et la saisie y reste ouverte

- **statut** : fini
- **exigences** : `WF-IHM-0150-A`
- **opérations** : `compareRevisions`, `listNodes`, `updateTaskFacet`, `updateEstimateLine`,
  `setLineRemaining`, `setTaskProgress`, `setPredecessors`, `setNodeTracking`, `createNode`,
  `moveNodes`, `deleteNode`, `previewPaste`, `applyPaste`, `undoLastChange`, `redoLastUndo`
- **issue** : #3487

**En tant que** chef de projet, **je veux** lire les écarts à la base dans la grille où je
travaille, avec la valeur que la base portait, et continuer d'y saisir, **afin de** juger un écart
devant ses valeurs sans aller et venir entre deux révisions.

**Critères d'acceptation.**

- `WF-IHM-0150-A` — « Une comparaison activée ne change pas les colonnes affichées. »
- `WF-IHM-0150-A` — « La grille de planning marque une tâche dont la fin diffère de la base, marque
  sa cellule de fin, et donne la date de la base au clavier seul ; la colonne d’écart de la fin,
  une fois choisie, donne le nombre de jours. »
- `WF-IHM-0150-A` — « La grille de devis marque une ligne retirée à sa place et n’en propose aucune
  saisie. »
- `WF-IHM-0150-A` — « Dans la grille de reste à engager, une ligne en écart d’une tâche non
  démarrée apparaît sans être demandée, et les valeurs au reste à engager précédent ne changent pas
  avec la base. »
- `WF-IHM-0150-A` — « Une grille ouverte sur une structure différentielle n’offre pas la
  comparaison. » : éprouvé contre le faux back, qui seul sert un différentiel avant EP-08 ;
- propre à l'US : une base dans l'adresse, la grille lit `compareRevisions` à la place de
  `listNodes`, avec les mêmes filtres, le même tri, la même recherche et les mêmes champs ; sans
  base, elle est celle d'aujourd'hui ;
- propre à l'US : chaque tâche et chaque ligne ajoutée, retirée ou modifiée porte la marque d'un
  différentiel (US-0500) ; chaque cellule dont la valeur diffère de la base porte une marque qui
  ne tient pas à la seule couleur (WF-IHM-0070), et donne la valeur de la base au survol comme au
  focus ;
- propre à l'US : le choix des colonnes offre l'écart à la base de chaque date, en jours
  calendaires, de chaque durée, en temps de travail, et de chaque montant ; aucune n'est affichée
  d'office ; chaque écart est rendu par le service, la grille ne calcule rien (WF-ARC-0020) ;
- propre à l'US : la révision en cours reste modifiable pendant qu'elle est comparée : la réponse
  d'une écriture remplace les lignes touchées comme aujourd'hui, puis la grille relit la
  comparaison une fois ses écritures répondues ; les marques, les valeurs de base et les écarts
  suivent, le curseur et la saisie en cours gardés (décision de l'auteur du 2026-11-15, au
  cadrage) ;
- propre à l'US : une ligne retirée n'offre ni saisie, ni collage, ni geste de structure ; une
  révision marquée comparée reste en lecture seule.

**Notes de réalisation.** Les grilles marquent déjà une ligne ajoutée, retirée ou modifiée
(`diff-mark.tsx`) et tiennent une ligne retirée en lecture seule par `editable_fields` vide, pour
la lecture d'un différentiel. La relecture après une saisie s'écarte, pour la seule grille
comparée, de la règle d'EP-02 (« Qui appelle l'API », en-tête de `cell-writes.ts`) : elle suit le
modèle de `retotal`, qui relit déjà les totaux d'une lecture filtrée une fois les écritures
répondues. La grille de reste à engager ne lit que les tâches démarrées, sauf demande
(`progress`).

**Hors périmètre.** La ligne de totaux (US-2350) ; le repli (US-2360) ; les marques dans la
réponse d'une écriture, écartées au cadrage ; l'arborescence des tâches, le Kanban et les
chronologies, qui ne portent pas la base.

## US-2350 — La ligne de totaux porte le total de la révision lue, celui de la base et leur écart, et les écarts par nature de coût et par sous-projet s'ouvrent depuis le devis et le reste à engager

- **statut** : fini
- **exigences** : `WF-IHM-0160-A`
- **opérations** : `compareRevisions`
- **issue** : #3488

**En tant que** chef de projet, **je veux** lire d'un regard ce que la comparaison pèse, et où,
**afin de** discuter un avenant ou une offre sur son total avant d'entrer dans ses lignes.

**Critères d'acceptation.**

- `WF-IHM-0160-A` — « Entre une base à 1 000 et une révision lue à 1 200, la ligne de totaux du
  devis porte 1 200, 1 000 et l’écart de 200, et se marque modifiée. »
- `WF-IHM-0160-A` — « Une ligne de 100 retirée depuis la base compte dans le total de la base et
  dans l’écart, non dans le total de la révision lue. »
- `WF-IHM-0160-A` — « Les écarts par nature de coût et par sous-projet s’ouvrent depuis la grille
  de devis et depuis celle de reste à engager. »
- propre à l'US : `compareRevisions` rend les totaux de la base à côté de ceux de la révision lue,
  et leur écart, sur les mêmes lignes retenues : un filtre s'applique aux deux (WF-IHM-0130) ; la
  grille ne somme rien ;
- propre à l'US : la ligne de totaux des trois grilles présente, pour chaque total qu'elle porte
  aujourd'hui, les trois valeurs ; elle ne se marque pas quand ils sont égaux ;
- propre à l'US : les écarts de montants budgétés et réestimés par nature de coût et par
  sous-projet (`amount_deltas`) se lisent dans un panneau, ouvert d'une commande de la grille de
  devis et de celle de reste à engager, au clavier comme au pointeur ; ils sont ceux des lignes
  que la lecture retient.

**Notes de réalisation.** `totals` ne compte pas aujourd'hui les nœuds retirés, et `amount_deltas`
les compte : la règle est gardée et écrite par la spécification 1.0.6 (décision de l'auteur du
2026-11-14, #3179).

**Hors périmètre.** Les totaux sous le repli, qui ne les change pas (US-2360).

## US-2360 — Les branches sans écart se replient, chaque suite repliée signalée à sa place avec son nombre de lignes

- **statut** : fini
- **exigences** : `WF-IHM-0170-A`
- **opérations** : `compareRevisions`
- **issue** : #3489

**En tant que** chef de projet, **je veux** ne voir d'une comparaison que ce qui change, **afin
de** lire quelques dizaines d'écarts sur mille tâches sans rien retirer de ce que la grille
compte.

**Critères d'acceptation.**

- `WF-IHM-0170-A` — « Les branches sans écart repliées, la grille n’affiche que les lignes marquées
  et leurs récapitulatives, signale chaque suite de lignes repliées, la déplie à la demande, au
  clavier comme au pointeur, et porte les mêmes totaux qu’avant le repli. »
- propre à l'US : « Écarts seulement », dans la barre des trois grilles, devient ce repli quand
  une comparaison est active : rien n'est demandé au service, et l'adresse ne change pas la
  lecture ;
- propre à l'US : la marque d'une suite repliée dit le nombre de ses lignes (décision de l'auteur
  du 2026-11-15, au cadrage), et se dit à un lecteur d'écran ;
- propre à l'US : une suite dépliée le reste tant que le repli est actif ; une écriture qui fait
  naître un écart dans une branche repliée la fait paraître à la relecture ;
- propre à l'US : le service marque modifiée chaque récapitulative qui porte un écart, et
  inchangé chaque nœud d'une branche sans écart : c'est sur ces marques seules que la grille
  replie.

**Notes de réalisation.** Le repli n'est pas un filtre (WF-IHM-0130, décision de l'auteur du
2026-11-14, #3179) : la grille tient déjà chaque ligne et sa marque, et plie déjà son arbre dans
le navigateur (`fold.tsx`).

**Hors périmètre.** « Écarts seulement » d'un différentiel d'avenant, filtre que le service
applique (`difference`, US-0700) — EP-08, qui sert les différentiels.

## US-2370 — L'écran « Révisions » : l'historique et ses commandes seuls

- **statut** : fini
- **exigences** : aucune en propre — les exigences de ces fonctions sont closes par EP-04, EP-07
  et EP-08
- **opérations** : `listRevisions`, `getRevision`, `createRevision`, `abandonRevision`,
  `markRevision`, `designateReferenceRevision`, `getRateUpdateProposal`, `applyRateUpdate`
- **issue** : #3486

**En tant que** chef de projet, **je veux** un écran « Révisions » qui ne porte que l'historique
du projet et ce qu'on y fait d'une révision, **afin de** ne plus chercher une commande dans un
empilement de sections.

**Critères d'acceptation.**

- propre à l'US : la section de comparaison et sa grille propre quittent l'écran, qui ne lit plus
  `compareRevisions` (#3177) ;
- propre à l'US : chaque révision de l'historique offre « Ouvrir » ; chaque révision marquée, hors
  la révision lue, offre « Comparer à la révision lue », qui ouvre un menu des grilles de
  planning, de devis et de reste à engager que l'utilisateur consulte, et mène à la grille
  choisie, cette révision pour base (décision de l'auteur du 2026-11-15, au cadrage) ;
- propre à l'US : « Désigner comme référence » est une commande de chaque révision marquée de
  l'historique, ses conditions non remplies dans son infobulle ; la carte de désignation
  disparaît (#3090 ; décision de l'auteur du 2026-11-15, au cadrage) ;
- propre à l'US : la liste des structures de coûts quitte l'écran, qui ne lit plus
  `listCostStructures` : le bandeau en offre le choix sur les grilles (#3180 ; même décision) ;
- propre à l'US : la mise à jour des taux est une commande de la révision en cours, à droite du
  titre de l'écran, offerte comme la révision la liste (`apply_rate_update`) ; elle ouvre la
  proposition, catégorie par catégorie, dans un dialogue ; `getRateUpdateProposal` n'est lue qu'à
  son ouverture (#3180 ; même décision) ;
- propre à l'US : l'écran tient en une carte, celle de l'historique, sous les commandes de la
  révision lue et le compte rendu d'un import que l'adresse nomme.

**Notes de réalisation.** EP-25 a mis les sections de l'écran en cartes sans en changer la
structure (US-2130). Le critère d'US-0210 (EP-02) sur « l'écran de comparaison de deux révisions »
tombe avec cette section : la comparaison se lit dans les grilles. WF-REV-0060 veut la mise à jour
« proposée jusqu'à son marquage » : la commande la propose.

**Hors périmètre.** Créer ou fusionner une structure (EP-08).

## US-2380 — Le parcours de la comparaison de PRJ-001, réécrit sur les grilles et rejoué contre le service

- **statut** : fini
- **exigences** : aucune en propre — le parcours éprouve US-2320 à US-2360 de bout en bout
- **opérations** : `compareRevisions`, `listRevisions`, `updateTaskFacet`
- **issue** : #3490

**En tant que** développeur, **je veux** que le parcours de la comparaison se joue de nouveau
contre le service, **afin que** la file de fusion éprouve la comparaison telle qu'on s'en sert.

**Critères d'acceptation.**

- propre à l'US : le parcours de `revisions.spec.ts` en quarantaine (#3192) est réécrit sur les
  grilles : depuis la grille de devis de la révision en cours de PRJ-001, choisir la référence
  pour base, lire une ligne marquée et la valeur de sa base au clavier, passer au planning puis
  au reste à engager avec la même base, replier les branches sans écart, lever la comparaison ;
- propre à l'US : il repousse la fin d'une tâche, la lit modifiée avec la date de la base, la
  ramène, et ne la lit plus modifiée ;
- propre à l'US : il se joue contre le faux back et contre le service, sa quarantaine retirée,
  aux bornes de temps qu'EP-26 a fixées (US-2290) ;
- propre à l'US : les parcours de l'écran « Révisions » qui lisaient sa comparaison sont retirés
  ou réécrits sur l'historique et ses commandes.

**Hors périmètre.** La mesure des durées (US-2390).

## US-2390 — La grille comparée et la saisie dans une grille comparée sont mesurées, et l'option des empreintes est instruite

- **statut** : fini
- **exigences** : aucune en propre — l'outil de WF-QUA-0060, que clôt US-2300 (EP-26)
- **opérations** : `compareRevisions`, `updateTaskFacet`, `updateEstimateLine`
- **issue** : #3491

**En tant qu'** exploitant, **je veux** les durées d'une grille comparée dans le rapport de
mesures, **afin de** savoir si la comparaison tient ses deux secondes avant de publier la version.

**Critères d'acceptation.**

- propre à l'US : `make measure` et `make measure-version` mesurent, sur PRJ-001 du témoin
  chargé, les deux opérations du tableau 15 que cet EPIC sert : ouvrir une grille de planning, de
  devis ou de reste à engager comparée à une révision marquée ; saisir dans une grille comparée,
  jusqu'aux marques relues ;
- propre à l'US : le rapport de mesures de la version les porte, avec leur objectif de deux
  secondes, à la place de la mention « EP-27 » sans durée (US-2300 d'EP-26) ; `make
  check-measures` passe ;
- propre à l'US : un objectif dépassé est documenté dans le rapport et devient une issue à
  trancher, sans lot engagé d'avance ;
- propre à l'US : l'option 3 de #3168 — la différence tenue à l'écriture par une empreinte par
  nœud — est instruite par les mesures que le constat demande : la part de l'union et du corps
  dans la durée d'une comparaison, la part des nœuds qui diffèrent entre la révision en cours et
  la révision marquée dont elle est issue ; le verdict est écrit, avec ses chiffres : écartée si
  les deux secondes tiennent, une issue à trancher sinon (décision de l'auteur du 2026-11-15, au
  cadrage).

**Notes de réalisation (mesures du 2026-11-18).** `make measure-version MEASURE_VERSION=0.4.0`
(cinquante utilisateurs, cinq passages ; 19 min, file d'attente comprise) : ouvrir une grille
comparée 2,847 s à la médiane pour 2 s (pire 4,608 s, dispersion 0,443 s, vingt échantillons :
quatre grilles, cinq passages) ; saisir dans une grille comparée 4,502 s pour 2 s (pire 5,1 s,
dispersion 0,418 s). Les deux objectifs sont dépassés, documentés dans `docs/measures/0.4.0.json`
et portés chacun par une issue à trancher. Seules ces deux opérations ont été portées au rapport :
les autres et les conditions restent celles du 2026-11-16, que des décisions de l'auteur
documentent ; celles que la nouvelle mesure a relevées sous une charge plus longue (quatorze étapes
au lieu de neuf, 279 s) sont citées dans sa note, non portées — ouvrir une grille y passe à
1,116 s. Un utilisateur sans charge (`make measure MEASURE_USERS=1 MEASURE_PASSES=1`) : les
quatre grilles comparées 1,416 s, 2,074 s, 2,321 s et 1,454 s, la saisie comparée 2,532 s, contre
1,294 s pour la même saisie hors comparaison. `make measure-core ONLY=current RUNS=5` : la
comparaison entière depuis les lignes 0,884 s, dont lectures 56 %, union 33 %, corps 11 % — union
et corps 44 %, au-dessus des 15 % de #3168 ; depuis le gardé 0,534 s (34 %) ; tâches seules
0,807 s (38 %) ; l'union jamais planchée (`union_clamped` faux, `runs_union_negative` 0) ; 43
nœuds sur 5 999 diffèrent (0,7 %). **Verdict sur l'option 3** : les deux secondes ne tiennent pas,
l'option n'est donc pas écartée, elle devient une issue à trancher ; les écarts sont rares, mais la
comparaison du noyau ne pèse que 0,5 à 0,9 s des durées mesurées, et la saisie comparée porte aussi
l'écriture qui redate : l'option 3 seule ne ramènerait pas cette saisie sous 2 s. L'étape
`planning.compared-duration` cherche la tâche par son libellé : l'union de la grille comparée
compte une ligne de la base au-dessus d'elle sur le témoin.

**Hors périmètre.** Réaliser l'option 3 ; rendre un objectif bloquant.

## US-2400 — Les constats reçus sont soldés

- **statut** : fini
- **exigences** : aucune en propre — les exigences de ces fonctions sont closes par EP-06 et EP-07
- **opérations** : `applyRateUpdate`, `moveNodes`, `applyPaste`, `updateCalendar`,
  `setDurationUnits`
- **issue** : #3484

**En tant que** développeur, **je veux** que les constats rattachés à cet EPIC soient corrigés,
**afin qu'** il ne laisse pas derrière lui la dette qu'il a reçue.

**Critères d'acceptation.**

- propre à l'US : `applyRateUpdate` refuse un montant débordé à `/cost_category_ids`, un scénario
  mesuré à l'appui (#3401) ;
- propre à l'US : les autres écritures qui rechiffrent des lignes écrites et refusent encore sans
  `fields` — un déplacement (`moveNodes`), un collage (`applyPaste`), un changement d'un
  calendrier ou des unités de durée — refusent au champ qui provoque le débordement, un scénario
  mesuré et un pointeur par cause qui a un champ ; `docs/api/DECISIONS.md` les porte, son
  paragraphe des causes sans champ recoupé (#3401, #3467) ;
- propre à l'US : un parcours fait un geste de structure dans la grille de planning et le lit
  dans la grille de devis, contre le service — la réciproque de celui d'US-1560/L2 (#2590) ;
- propre à l'US : les deux commentaires de `planning.spec.ts` qui disent les lignes « d'EP-07 »
  sont corrigés, la numérotation des lignes du planning vérifiée contre le service (#2854) ;
- propre à l'US : l'erreur de `timelines.spec.ts` sur un compte gestionnaire absent nomme où il
  se définit (#2885) ; son `page.reload()` redondant est retiré, le couloir remis par un
  `finally`, son commentaire de 107 colonnes recoupé (#3127) ;
- propre à l'US : la mention de #2745 dans le fichier d'EP-07 est relue, corrigée ou établie
  juste (#3127) ;
- propre à l'US : les commentaires au-delà de 100 colonnes d'`import-report.tsx` et de
  `file-drop.tsx` sont recoupés (#3160).

**Hors périmètre.** Les causes sans champ — une annulation, un rétablissement, l'ouverture d'une
révision —, qui restent refusées sans `fields` (décision de l'auteur du 2026-11-15, #3303).

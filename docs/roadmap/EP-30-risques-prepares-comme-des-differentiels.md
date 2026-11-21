---
id: EP-30
titre: Un risque se prépare comme un différentiel — il ajoute, reprend ou abandonne du travail, et sa survenance fusionne sans déplacer la référence
statut: en cours
depend_de: EP-08, EP-11
famille: front, back
issue: 4573
---

# EP-30 — Risques préparés comme des différentiels

## Objet

EP-08 livre le devis propre d'un risque comme un fragment autonome : des tâches et des lignes qui
ne sont qu'à lui, greffées à la survenance sous la tâche qui portait la provision (WF-RIS-0060). Un
tel risque ne peut qu'ajouter du travail. Il ne reprend pas une tâche existante — trente pour cent
d'heures en plus sur les études —, n'en abandonne aucune, et ne retarde le projet que par
l'enveloppe de la tâche porteuse, sans que ce retard entre dans sa gravité ni se lise avant la
survenance.

Cet EPIC fait du devis propre un différentiel : une branche de la structure principale, qui ajoute,
modifie et abandonne, se met à jour à chaque revue et fusionne à la survenance (décisions de
l'auteur du 2026-11-19, prises en tranchant #4034). Il vient après EP-08, dont il réutilise la mise
à jour et la fusion d'un différentiel, et après EP-11, qui modifie le même module des risques et
dont il fait suivre les lectures (décision de l'auteur du 2026-11-21). La spécification 1.0.9 redit
ses exigences avant l'ouverture des issues de ses lots.

## Ce qui en fait partie

- le devis propre d'un risque préparé comme un différentiel de la structure principale, dans les
  grilles de planning et de devis, où il ajoute des tâches et des lignes, modifie celles qui
  existent et en abandonne ;
- la lecture, avant la survenance, du planning et du devis entiers avec le risque appliqué : la
  grille d'un devis propre montre le projet avec ce que le risque y désigne ;
- la mise à jour d'un devis propre depuis la structure principale, son compte rendu, et ce qui
  l'exige : la saisie dans le devis propre, le réexamen, la survenance, et le marquage d'une
  révision comme la contractualisation d'un avenant, pour que la gravité qu'une révision fige soit
  juste ;
- la gravité d'un risque, écart net entre le projet avec le risque et le projet sans lui, la
  provision qui en est tirée, et l'opportunité, dont la gravité est négative ;
- la gravité d'un risque survenu, lue à son coût à la survenance dans les révisions qui suivent
  (#4400) ;
- la survenance, qui fusionne ce que le devis propre désigne sur les grandeurs courantes seules,
  termine à son budget une tâche abandonnée et rouvre une tâche terminée qu'elle modifie ;
- le coût à la survenance, signé, la couverture et le suivi d'un risque survenu, redits pour un
  risque qui modifie ou abandonne ;
- la valeur acquise devant une survenance qui termine ou rouvre des tâches, et sa marque sur les
  courbes de valeur acquise ;
- les lectures du portefeuille qui suivent : une opportunité dans sa matrice, un coût à la
  survenance négatif dans sa couverture agrégée ;
- les écrans des risques, et la reprise de celui d'un projet : le graphique à bulles toujours
  visible, en bulles rondes dont le diamètre suit la gravité, et au registre la tendance de chaque
  risque depuis la revue précédente ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — les trois risques de PRJ-001 relus comme
  des différentiels, le 751 ajoutant, modifiant et abandonnant —, rechargée par `waterfall-api
  load-witness`, et les exemples du contrat qui suivent ;
- les constats reçus, soldés.

## Ce qui n'en fait pas partie

- la base d'un différentiel d'avenant et sa mise à jour depuis la structure principale — EP-08
  (#4034, #4132), dont cet EPIC réutilise les règles et les deux opérations ;
- l'avenant, sa fusion et le déplacement de la référence — EP-08 ; la fusion d'un avenant n'écrit
  aucun devis propre, et cet EPIC ne lui ajoute qu'un refus, tant qu'un risque identifié a le sien
  en retard ;
- la reprise des devis propres saisis sous EP-08 : aucune base à conserver n'en porte, et la
  migration refuse de s'appliquer si elle en trouve un (décision de l'auteur du 2026-11-21) ;
- les vues du portefeuille — EP-11 ; ici, ce que la gravité signée change à leurs lectures des
  risques ;
- le calcul des indicateurs — EP-10 ; ici, la valeur acquise devant une tâche qu'une survenance
  termine ou rouvre, et sa marque ;
- une marque, dans la structure principale, sur les lignes qu'un risque survenu a modifiées et les
  tâches qu'il a abandonnées : seuls les ajouts la portent.

## Exigences réalisées

La spécification 1.0.8 décrivait encore le devis propre greffé d'EP-08. Décisions de l'auteur du
2026-11-21, à ce cadrage : les exigences dont la règle change sont réécrites sous leur identifiant,
et cet EPIC les clôt à la place d'EP-08, dont les lignes passent « début — close en EP-30 » ; ce qui
est purement neuf prend des exigences courtes nouvelles ; le cadrage s'est fait sur un texte de
Vérif proposé, que les US citaient en critères propres. La spécification 1.0.9, écrite d'après ce
texte et acceptée par l'auteur le même jour, avant l'ouverture des issues des lots, le porte : les
US en citent les Vérif.

Six exigences changent de règle et sont closes ici : WF-RIS-0010 (la gravité, écart net, et le coût
à la survenance), WF-RIS-0030 (le devis propre), WF-RIS-0040 (l'opportunité au registre et dans la
matrice, la tendance d'un risque), WF-RIS-0050 (le coût à la survenance signé, et ce qui se lit en
regard), WF-RIS-0060 (la survenance) et WF-IND-0030 (la valeur acquise d'une tâche qu'une survenance
termine). Trois exigences nouvelles, que la 1.0.9 écrit, entrent à ce tableau, entières : « Mise à
jour du devis propre d'un risque » (WF-RIS-0070), « Gravité d'un risque » (WF-RIS-0080) et « Marque
d'une survenance sur les courbes de valeur acquise » (WF-IND-0140). Le texte, corps et Vérif, a été
proposé dans quatre issues de spécification : #4516, le devis propre et sa mise à jour ; #4517, la
gravité, l'opportunité et la tendance ; #4518, la survenance et la couverture ; #4519, la valeur
acquise et sa marche. WF-RIS-0020 et WF-REV-0110, dont aucune phrase de Vérif ne change, et
WF-REV-0100, dont seul le corps est retouché, restent closes par EP-08 ; WF-PTF-0090 et WF-IND-0110,
dont le texte ne change pas, par les EPIC qui les ont réalisées. WF-QUA-0040 entre au tableau en
portée « début » : cet EPIC recharge sa tranche du jeu de données de référence, qu'EP-13 clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-RIS-0010-A` | Attributs d’un risque | fin — amorcée en EP-15, EP-08 | US-3080 |
| `WF-RIS-0030-A` | Devis propre d’un risque | fin — amorcée en EP-15, EP-08 | US-3070 |
| `WF-RIS-0040-A` | Grille de suivi des risques | fin — amorcée en EP-15, EP-17, EP-08 | US-3080, US-3160 |
| `WF-RIS-0050-A` | Réserve pour risques et couverture | fin — amorcée en EP-17, EP-08 | US-3110 |
| `WF-RIS-0060-A` | Survenance d’un risque | fin — amorcée en EP-17, EP-08 | US-3100 |
| `WF-RIS-0070-A` | Mise à jour du devis propre d’un risque | entière | US-3090 |
| `WF-RIS-0080-A` | Gravité d’un risque | entière | US-3080 |
| `WF-IND-0030-A` | Valeur acquise | fin — amorcée en EP-10, EP-08 | US-3120 |
| `WF-IND-0140-A` | Marque d’une survenance sur les courbes de valeur acquise | entière | US-3120 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06, EP-07, EP-09, EP-10, EP-08, EP-11 | US-3150 |

## Opérations du contrat

Le contrat, figé (`docs/api/DECISIONS.md`, « La règle d'après le gel »), change : chaque
modification passe par une issue « contrat » que l'auteur tranche, et s'écrit par un lot avant le
code qui la consomme. La conception en dira le détail ; ce que les US demandent :

- la mise à jour d'un différentiel, étendue au devis propre d'un risque : `getStructureRebaseReport`
  et `rebaseCostStructure` l'acceptent, sous la permission de la saisie des risques ;
  `CostStructure` dit un devis propre à jour ou en retard, et liste sa commande de mise à jour ;
- un refus de plus, sur un devis propre en retard, pour les écritures de l'arbre et les imports sur
  un devis propre, pour `reviewRisk`, `getRiskOccurrenceReport` et `declareRiskOccurrence` ; et,
  pour `markRevision` et `mergeCostStructure`, l'échec de leur tâche de fond, qui nomme les risques
  dont la mise à jour garde une valeur ou est refusée ;
- la recomposition d'un devis propre élagué, opération nouvelle ;
- `Risk` : une gravité et un coût à la survenance signés, ce dont la gravité dépend
  (`computed_fields`), le réestimé présenté en regard redit, et les commandes d'un risque dont le
  devis propre est en retard ;
- `RiskOccurrenceReport` : la forme du compte rendu d'une fusion — ce que la survenance ajoute,
  modifie et termine, la valeur acquise qu'elle apporte ou retire, les tâches terminées qu'elle
  rouvre — ; les deux signalements provisoires d'EP-08 en sortent (#4133, #4134) ;
- `StructureRebaseReport`, pour un devis propre : la gravité et la provision que la mise à jour
  enregistrerait ;
- `listNodes` sur un devis propre : les différences (`NodeDifference`) par rapport à la structure
  principale de la révision lue ;
- `getEarnedValueCurves` : la marche datée d'une survenance ;
- `Risk` et `listRisks` : la tendance d'un risque depuis la révision marquée précédente, son filtre
  et son tri ;
- `ChartPreferences` : l'état plié du graphique des risques d'un projet, qui n'a plus d'objet ;
- les exemples, engendrés par `make mock-data`.

Servies par EP-08 ou par EP-11, et reprises ici pour ce que cet EPIC y change :

- `risks` : `createRisk`, `getRisk`, `listRisks`, `listRiskReviews`, `reviewRisk`,
  `updateRiskProvision`, `getRiskOccurrenceReport`, `declareRiskOccurrence`,
  `getProjectRiskCoverage`, `getProjectRiskMatrix` ;
- `revisions` : `listCostStructures`, `getStructureRebaseReport`, `rebaseCostStructure`,
  `createRevision`, `abandonRevision`, `markRevision`, `getStructureMergeReport`,
  `mergeCostStructure`, `compareRevisions`, `listNodes` et les écritures de l'arbre sur un devis
  propre, `undoLastChange`, `redoLastUndo` ;
- `exchanges` : `openImport`, `applyImport`, sur un devis propre ;
- `analysis` : `getRemainingIndicators`, `getProjectIndicators`, `getEarnedValueCurves` ;
- `portfolio` : `getPortfolioRisks` ;
- `me` : `updateMyPreferences`.

## Préalables

EP-08 et EP-11 livrés : `epic/EP-30` se tire de `main`, au premier lot, une fois les deux fusionnés
(décision de l'auteur du 2026-11-21). C'est la règle du README : EP-11 modifie le même module des
risques (`core/risks`), et deux EPIC ne le touchent pas en même temps. EP-30 trouve alors dans
`main` ce qu'il réutilise d'EP-08 — ce qu'une structure désigne par rapport à sa base, la mise à
jour d'un différentiel et son compte rendu, la fusion — et les lectures du portefeuille qu'il fait
suivre.

La spécification 1.0.9, acceptée par son auteur le 2026-11-21, avant l'ouverture des issues des lots
: elle redit les six exigences du tableau et écrit les trois nouvelles, d'après le texte que ce
cadrage a proposé (#4516, #4517, #4518, #4519). Les critères « propre à l'US, texte proposé » sont
devenus des citations de Vérif.

Le plan de lots, validé par l'auteur le 2026-11-21, a d'abord été gardé dans la pull request de ce
cadrage (#4521) : les lots ne s'écrivent pas dans ce fichier. Les issues de l'EPIC, des US, des lots
et du contrat sont ouvertes depuis le même jour, la 1.0.9 acceptée et les US alignées sur ses Vérif
(#4568) : l'EPIC est `en cours`, et le tableau de suivi de son issue (#4573) porte le plan.

## Définition de fini

- les exemples chiffrés des Vérif que la spécification 1.0.9 écrit pour WF-RIS-0010, WF-RIS-0030,
  WF-RIS-0040, WF-RIS-0050, WF-RIS-0060 et WF-IND-0030, et pour les trois exigences nouvelles, sont
  des tests qui passent (WF-QUA-0020) ;
- sur un projet de mille tâches et cinq mille lignes, une révision marquée ne garde d'un devis
  propre que ce qu'il désigne, et la révision suivante n'en reprend pas davantage ;
- un devis propre préparé avant que la structure principale ne reçoive une tâche, une réestimation,
  la fusion d'un avenant et la survenance d'un autre risque, puis mis à jour, réexaminé et déclaré
  survenu, laisse dans la structure principale tout ce qu'elle a reçu entre-temps, et y applique ce
  qu'il désigne ;
- une révision ne se marque pas, et un avenant ne se contractualise pas, tant qu'un risque identifié
  a son devis propre en retard : la gravité qu'une révision marquée fige est celle de son projet,
  ou, pour la révision qu'un avenant marque, celle du projet d'avant l'avenant ;
- le parcours de bout en bout, contre le service réel, déclare un risque, y ajoute une tâche, y
  modifie une ligne et y abandonne une tâche, met son devis propre à jour après une saisie du
  projet, le réexamine et le déclare survenu ;
- le témoin chargé porte ses trois risques relus comme des différentiels, et ses lectures sont
  comparées aux exemples du contrat ;
- `make requirements` ne laisse sans test du back aucune des exigences que cet EPIC clôt ;
- les mesures existantes, `make measure-core` et `make measure`, rejouées sur le témoin chargé,
  tiennent leurs objectifs et ne se dégradent pas de plus d'un quart (WF-QUA-0060) ; la grille d'un
  devis propre entier sur le projet de mille tâches y tient l'objectif d'ouverture d'une grille, et
  la recomposition, la mise à jour et le marquage d'un projet à vingt risques y sont relevés, sans
  objectif.

## Constats reçus

- #4400 — back : la gravité d'un risque survenu se lit à son coût à la survenance dans les révisions
  suivantes (WF-RIS-0010, spécification 1.0.8). Rangé en EP-35 par la ventilation du 2026-11-21, et
  repris ici au cadrage du même jour (décision de l'auteur, contre « EP-30 ne prend pas d'autres
  restes ») : cet EPIC clôt WF-RIS-0010 et réécrit la lecture de la gravité. Corrigé par US-3080.
- #4633 — test : `risks.spec.ts` trouve les bulles du graphique par `path[fill-opacity='0.85']`, un
  détail du rendu d'ECharts, contre la règle « jamais par une classe CSS » (FTE-09, pour sa part des
  risques ; le reste est à EP-36, #4448). Reporté ici au cadrage d'EP-36 du 2026-11-21 (décision de
  l'auteur) : US-3160 redessine ces bulles et réécrit ce parcours, qui les trouve alors par ce que
  l'écran nomme. Corrigé par US-3160.

Trois constats d'EP-08 sont tranchés au plus léger parce que cet EPIC rend leur règle provisoire
(décisions de l'auteur du 2026-11-19 et du 2026-11-20) : #4133, les dates du devis propre le jour de
la survenance, que le compte rendu signale sans que la survenance redate ; #4134, les tâches en aval
que la greffe déplace, nommées au compte rendu sans champ nouveau ; #4240, la greffe sous une tâche
terminée, qui la rouvre, signalée sans refuser. Le devis propre préparé comme un différentiel porte
le planning entier : ses tâches se datent par leurs liaisons avec celles du projet, et le retard se
lit dans sa grille. US-3100 retire les deux premiers signalements et garde le troisième, étendu à
toute tâche terminée que la survenance rouvre.

## Conception

Écrite au cadrage du 2026-11-21, sur le code d'`epic/EP-08` et d'`epic/EP-11` à cette date, après la
validation des US. Elle dit ce qu'un lot devrait sinon décider seul ; ce qui relève d'un lot reste
au lot. Ses deux premières sections sont les décisions de l'auteur, qui s'imposent à elle.

### Ce que l'auteur a décidé le 2026-11-19

- **Un seul modèle.** Le devis propre d'un risque est un différentiel, et le risque qui ne fait
  qu'ajouter du travail en est le cas particulier. Écartés : des liaisons d'ancrage entre le devis
  propre et la structure principale, qui ne modifient ni ne retirent rien ; une liste d'effets
  typés sur des tâches désignées, qui réécrirait hors de la mécanique de l'avenant les règles d'un
  retrait — la tâche démarrée entre-temps, la provision qu'elle porte, ses liaisons.
- **Un même risque ajoute, modifie et abandonne.** Écartées : deux natures de risque, l'une qui
  ajoute et l'autre qui modifie.
- **Le réexamen est la mise à jour.** À chaque revue, ce que la structure principale a reçu est
  reporté dans le devis propre ; les conflits se lisent au compte rendu et se résolvent par une
  saisie dans le devis propre, sans écran de résolution, comme pour un avenant (#4034).
- **La survenance fusionne sur les grandeurs courantes seules.** Une ligne ajoutée porte un montant
  budgété nul ; une ligne modifiée garde son montant budgété et change de montant réestimé ; la
  référence ne bouge pas et aucune révision n'est marquée.
- **Une tâche qu'un risque survenu abandonne est terminée à son budget**, qu'elle soit démarrée ou
  non : son reste à engager passe à zéro, et elle acquiert son montant budgété. Le travail de
  remplacement, à budgété nul, se lit en dérive de coût : on a fait autrement, pour plus cher. La
  règle est celle que l'avenant applique à une tâche démarrée (WF-REV-0050). Écarté : retirer la
  tâche, dont le budget resterait dans la référence sans jamais être acquis — le projet
  n'atteindrait plus cent pour cent sans avenant. Effet connu, à dire dans la spécification : la
  valeur de la tâche est acquise d'un coup le jour de la survenance, quand le travail de
  remplacement s'étale ensuite ; l'indice de délai fait un saut ce jour-là.
- **La gravité est un écart net** : le montant réestimé du projet avec le risque, moins celui du
  projet sans lui. Elle compte le glissement des tâches en aval et l'économie d'une tâche
  abandonnée.
- **Une gravité négative est une opportunité**, que le registre présente ; la provision est
  plafonnée à zéro, pour qu'une opportunité ne réduise pas le reste à engager avant d'être
  réalisée.
- **La part d'un risque dans une ligne qu'il modifie est figée à la survenance.** Le montant
  réestimé courant présenté en regard du coût à la survenance (WF-RIS-0050) ne suit que les lignes
  que le risque a ajoutées.
- **Deux risques qui modifient la même ligne sont chiffrés chacun seul**, contre la structure
  principale. Quand l'un survient, la mise à jour de l'autre signale le conflit à son réexamen.
- **Un devis propre ne conserve que ce qu'il désigne** — ajouts, valeurs modifiées, retraits —, et
  la structure entière se recompose à l'ouverture de sa grille. Une copie entière par risque,
  reprise par chaque révision, multiplierait ce que porte une révision par le nombre des risques :
  mille tâches et cinq mille lignes pour chacun.

### Ce que le cadrage du 2026-11-21 décide

- **Le cadrage précède la spécification, qui précède les lots.** Les US sont écrites sur un texte de
  Vérif proposé, et la 1.0.9 est acceptée avant l'ouverture des issues des lots. Écartés : la
  spécification d'abord, qui retardait ce cadrage, donc EP-35 ; les issues ouvertes sur les critères
  propres, comme pour US-3050 le 2026-11-19, dont les tests citent l'US puis sont à citer de
  nouveau.
- **Les exigences dont la règle change sont réécrites sous leur identifiant, et closes ici.**
  Écartés : des exigences nouvelles seules, les anciennes restant closes par EP-08 dont cet EPIC
  réécrit le code ; l'indice B, que rien n'emploie encore et que toute citation de la roadmap aurait
  à suivre ; un EPIC qui ne clôt rien, comme EP-35.
- **La grille d'un devis propre montre le projet du jour** : à chaque ouverture, la structure
  principale telle qu'elle est, avec ce que le risque désigne. La gravité et la provision
  enregistrées sont celles de la dernière mise à jour ou de la dernière saisie dans le devis propre
  ; une écriture de la structure principale ne les change pas. Écartée : la grille tenue sur l'état
  du dernier réexamen, comme celle d'un avenant sur sa base, qui demande une base entière par
  risque, contre la décision du 2026-11-19. Repris à la conception, qui garde cette base dans la
  révision en cours : un devis propre en retard montre l'état de sa dernière mise à jour, et c'est
  la mise à jour, faite par l'écran à l'ouverture quand rien n'est à signaler, qui l'amène au projet
  du jour.
- **Un devis propre est en retard** dès que la structure principale a changé depuis sa dernière mise
  à jour : une branche que personne n'a encore rejouée sur la tête. L'écriture d'une ligne de
  provision n'y compte pas : elle ne change pas le projet sur lequel la gravité se calcule, et sans
  cela la mise à jour d'un risque, qui réécrit sa provision, remettrait tous les autres en retard.
  Sa gravité et sa provision datent d'avant, et ce qu'il désigne n'a pas été confronté au projet. La
  mise à jour recalcule la gravité sur le projet du jour et présente ce qui ne s'y rattache plus.
- **« Réexaminer » est un geste, et deux opérations.** L'écran fait la mise à jour, puis le
  réexamen. Au contrat, la mise à jour garde les deux opérations d'EP-08, étendues au devis propre,
  et `reviewRisk` est refusé tant que le devis propre d'un risque qui reste ou redevient identifié
  est en retard. L'annulation d'un réexamen rend ainsi exactement la probabilité, l'état et la
  provision d'avant (WF-IHM-0110). Écartés : `reviewRisk` qui ferait lui-même la mise à jour, dont
  l'annulation ne rendrait pas la gravité d'avant ; un réexamen libre, contre « à chaque revue, ce
  que la structure principale a reçu est reporté ».
- **Une mise à jour qui ne signale rien se fait sans confirmation.** La saisie dans un devis propre
  en retard, le réexamen, la survenance, le marquage et la contractualisation d'un avenant attendent
  tous la mise à jour. Quand son compte rendu ne garde rien et ne refuse rien, elle s'applique sans
  rien demander et le geste se poursuit ; sinon le compte rendu est présenté, à confirmer s'il garde
  une valeur contre le projet, à corriger dans le devis propre s'il refuse. Confirmer un compte
  rendu vide n'apprend rien, et un projet qui bouge souvent coûterait une confirmation par risque.
  Tranché contre la réponse donnée plus tôt dans ce cadrage, « toujours confirmé, même vide ».
  Écartés : le compte rendu toujours présenté ; la saisie libre, qui vaudrait mise à jour sans que
  ce qui ne se rattache plus soit jamais présenté ; un compte rendu unique pour tous les risques
  avant un marquage, qui n'est que la somme de comptes rendus indépendants et n'apporte rien quand
  ils sont vides.
- **La survenance exige un devis propre à jour**, comme la fusion d'un avenant exige un différentiel
  à jour (EP-08, reprise du 2026-11-19) : son compte rendu est une lecture, qui ne peut écrire la
  mise à jour, et ce que celle-ci signale se règle avant de fusionner.
- **La trace ne marque que les ajouts.** `origin_risk_id` garde son sens : les tâches et les lignes
  qu'une survenance a ajoutées. Une ligne modifiée et une tâche abandonnée ne portent aucune marque,
  comme la tâche qu'un avenant termine ; ce que le risque a modifié ou abandonné se relit au compte
  rendu et dans son devis propre, conservé dans la révision où il est survenu. Écartée : une marque
  de plus, un champ nouveau du nœud au contrat.
- **Le coût à la survenance est signé.** Celui d'une opportunité réalisée est négatif, et la
  couverture le compte tel quel : elle peut compenser le dépassement d'un autre risque survenu.
  Écarté : un plancher à zéro, qui ne laisserait lire l'économie que dans le reste à engager.
- **La ligne de provision garde sa tâche désignée**, à défaut la première tâche de premier niveau.
  La désignation n'est plus que celle de la provision : dans quel lot et à quelles dates elle pèse.
  La survenance retire la ligne et ne place rien sous cette tâche. Écartés : la ligne déduite du
  devis propre, sous l'ancêtre commun de ce qu'il désigne, qui changerait de lot et de dates sans
  geste de l'utilisateur ; toujours la première tâche de premier niveau, arbitraire dans le devis
  par lot et dans les courbes ; une provision hors de toute tâche, contre le modèle livré.
- **La fusion d'un avenant n'écrit aucun devis propre.** Comme après toute écriture de la structure
  principale, les devis propres sont ensuite en retard, et la mise à jour de chacun applique les
  règles de WF-REV-0110 et nomme ce qu'elle garde. Écarté : un compte rendu de fusion qui nommerait
  les risques dont le devis propre désigne ce que l'avenant désigne, un champ de plus au contrat
  d'EP-08.
- **Le marquage d'une révision et la contractualisation d'un avenant exigent des devis propres à
  jour.** Une révision marquée ne se modifie plus, et sa réserve est figée quand elle devient la
  référence : l'un et l'autre attendent que le devis propre de chaque risque identifié soit à jour.
  Ceux dont la mise à jour ne signale rien sont mis à jour sans confirmation ; le geste n'est
  refusé, le risque nommé, que lorsqu'une mise à jour garde une valeur contre le projet ou est
  refusée. L'ordre d'une revue en découle : les saisies du projet, puis la mise à jour et le
  réexamen des risques, puis le marquage. Limite connue : la fusion d'un avenant écrit la structure
  principale et marque dans la même opération, si bien que la révision qu'elle marque fige les
  gravités du projet d'avant l'avenant, que la révision suivante recalcule. Tranché contre la
  réponse donnée plus tôt dans ce cadrage, « le contrat de la fusion ne change pas » : la fusion
  reçoit un refus de plus. Écartés : le refus au marquage seul, qui laisserait un avenant figer une
  réserve périmée ; un signalement sans refus, que l'utilisateur passerait ; ne rien faire, l'ordre
  laissé à la discipline du chef de projet ; le refus dans tous les cas, chaque compte rendu
  confirmé, retenu d'abord puis repris.
- **Une désignation sur une tâche terminée s'applique.** Le devis propre modifie une ligne d'une
  tâche terminée, et garde cette désignation quand le projet termine la tâche après coup ; la
  survenance l'applique, la tâche n'est plus terminée, et le compte rendu le signale sans refuser,
  comme pour #4240. Écartée : une tâche terminée hors d'atteinte, dont la mise à jour retirerait les
  désignations.
- **La valeur acquise d'un coup se lit au compte rendu et sur les courbes.** Le compte rendu de la
  survenance nomme les tâches qu'elle termine et la valeur acquise qu'elles apportent ; la courbe de
  valeur acquise porte une marche datée à la survenance, signée, avec sa cause, comme la courbe du
  budget en porte une à un avenant. Écartés : le compte rendu seul, les courbes montrant le saut
  sans le nommer ; les tâches nommées sans montant.
- **Une opportunité figure au registre et dans la matrice.** Le registre la liste avec sa gravité
  négative, une provision nulle et une mention ; la matrice, du projet comme du portefeuille, la
  classe au plus bas niveau de gravité. Écartée : l'opportunité hors de la matrice, qui rendrait
  `matrix_cell` nul et changerait la forme du risque au contrat.
- **L'écran des risques d'un projet est repris ici**, par une US de plus (US-3160) : cet EPIC touche
  déjà cet écran et le contrat du risque, et un constat va à l'EPIC qui touche son code. Tranché
  contre « cette US ne redessine aucun écran », écrit d'abord pour US-3140, et contre le rangement
  des écrans en EP-37 par la ventilation du 2026-11-21.
- **Le graphique à bulles est toujours visible, au-dessus de la grille, sans pliage.** La commande
  de pliage et la préférence qui gardait son état disparaissent ; sur un écran de 768 de haut, la
  page défile pour atteindre le bas de la grille. Tranché contre #1252, qui l'avait fait démarrer
  replié pour tenir la grille dans la fenêtre. Écartés : le graphique à côté de la grille sur un
  écran large, une mise en page de plus à écrire et à éprouver à deux largeurs ; le graphique déplié
  par défaut, qu'on replierait encore.
- **Des bulles rondes, dont le diamètre est proportionnel à la gravité**, sans descendre sous un
  minimum qui les laisse visibles et cliquables ; une opportunité est dessinée par la valeur absolue
  de sa gravité. La zone se lit toujours sans sa couleur, par son nom écrit dans sa case et par le
  trait de ses côtés (WF-IHM-0070). Tranché contre le point de #1395 qui marquait la zone par la
  forme de la bulle — rond, losange, triangle —, et contre la taille en racine carrée, bornée,
  qu'EP-15 avait retenue. Écarté : un diamètre strictement proportionnel, qui réduit un petit risque
  à un point.
- **La tendance d'un risque se mesure à la révision marquée précédente**, sur le produit signé de sa
  gravité par sa probabilité ; un risque identifié qui ne l'était pas dans cette révision est dit
  nouveau, par une icône ; le registre se filtre et se trie sur elle, comme sur ses autres colonnes
  (H-01, #1786). Écartés : la comparaison au réexamen précédent du risque, que chaque saisie dans le
  devis propre ferait bouger entre deux réexamens ; la colonne seule, sans filtre ni tri, une
  exception à H-01.
- **Aucun devis propre n'est repris.** EP-08 n'a servi aucune base à conserver : la migration change
  le schéma et refuse de s'appliquer si elle trouve un devis propre ; les bases de développement se
  recréent, le témoin se recharge. Écartée, contre ce que ce fichier disait : une migration de
  données qui convertirait chaque devis propre, ceux des révisions marquées compris.
- **#4400 est repris d'EP-35** : cet EPIC clôt WF-RIS-0010 et réécrit la lecture de la gravité.
  Écarté : la phrase de Vérif laissée en écart vers un EPIC postérieur, contre « une exigence n'est
  close que par l'EPIC qui la vérifie en entier ».
- **EP-30 vient après EP-08 et EP-11**, et fait suivre le portefeuille. Écarté : après EP-08 seul,
  deux EPIC écrivant `core/risks` en même temps.
- **Dans le témoin, le risque 751 seul ajoute, modifie et abandonne**, à gravité égale, pour que la
  réserve de 910 et les montants qui en dépendent tiennent ; 752 et 753 restent additifs, et la
  survenance qui abandonne se montre par des variantes déclarées du contrat. Écartés : 752 aussi,
  qui changerait la structure de la révision 102 et toutes ses lectures ; trois risques additifs,
  que les écrans ne verraient jamais modifier une ligne sur le faux back.

### Ce que la conception décide

- **Entier dans la révision en cours, élagué au marquage.** Les écritures d'une grille ne savent
  écrire que des lignes en base, et la mise à jour comme la fusion d'EP-08 comparent des structures
  entières. Dans la révision en cours, le devis propre est donc un différentiel avec sa base, comme
  un avenant, et les réemploie telles quelles ; au marquage il est élagué, la révision marquée ne
  gardant que ce qu'il désigne, et la révision suivante le recompose quand on y travaille. La
  décision du 2026-11-19 tient là où elle pèse, dans les révisions marquées, qui s'accumulent sur
  quinze ans. Tranché contre « le projet du jour » à la lettre : un devis propre en retard montre
  l'état de sa dernière mise à jour, et l'écran le met à jour à l'ouverture quand rien n'est à
  signaler. Écartés : les écarts seuls partout, recomposés en mémoire à chaque lecture, qui
  demandaient d'écrire une seconde fois la lecture, la mise à jour et leurs règles à côté de celles
  d'EP-08 ; le modèle de l'avenant dans toutes les révisions, vingt risques multipliant par quarante
  et un ce que porte chacune.
- **Dans une révision marquée, la grille d'un devis propre montre ce qu'il désigne**, sous ses
  tâches parentes, et non le projet entier ; il en va de même du devis propre d'un risque survenu.
  Écartés : la lecture entière gardée au marquage, un document par risque et par révision ; le
  projet recomposé en mémoire à la lecture, le chemin de l'architecture écartée.
- **Le marquage n'élague qu'un devis propre à jour ; en retard, il reste entier.** Deux cas : après
  la fusion d'un avenant, qui écrit la structure principale et marque dans la même opération, tous
  les devis propres sont en retard, et la révision qu'elle marque les garde entiers, que la révision
  suivante reprend avec leur base — c'est la limite connue, la gravité figée étant celle du projet
  d'avant l'avenant, et leur mise à jour se lit ensuite, compte rendu compris ; le devis propre d'un
  risque écarté dont la mise à jour d'office est refusée. Écarté : une mise à jour d'office après la
  fusion, qui réglerait sans les présenter les écarts de risques identifiés.
- **Au marquage, le devis propre entier d'un risque écarté est mis à jour d'office**, sans compte
  rendu : les règles s'appliquent sans être présentées, personne ne suivant un risque écarté. Un
  devis propre écarté déjà élagué n'est pas touché : il garde le nom de la révision marquée contre
  laquelle ses écarts sont exacts, et son retour à l'état identifié le recompose puis présente toute
  sa mise à jour. Écartés : le marquage arrêté par un risque écarté, contre « seuls les risques
  identifiés comptent » ; le devis propre écarté jamais élagué.
- **La mise à jour sans confirmation est faite par l'écran pour un risque, et par la tâche de fond
  au marquage et à la fusion d'un avenant.** Pour une saisie, un réexamen ou une survenance, le
  service refuse sur un devis propre en retard, et l'écran lit le compte rendu puis met à jour : la
  mise à jour reste une opération à part, et l'annulation d'un réexamen rend la provision d'avant.
  Au marquage et à la fusion, la tâche de fond recompose et met à jour elle-même les devis propres
  qui ne signalent rien, et échoue en nommant les risques sinon, rien n'étant écrit. Écarté :
  l'écran enchaînant vingt recompositions avant un marquage, autant d'allers et retours de plusieurs
  secondes.
- **Ce qu'un devis propre élagué garde reste dans les tables des nœuds** : les nœuds qu'il désigne,
  leurs ancêtres et les extrémités de ses liaisons, sous sa structure, et à part la liste de ce
  qu'il abandonne. Il suit ainsi les migrations du schéma et la copie d'une révision sans code à
  lui. Écartés, comme pour la base d'un différentiel en EP-08 : une image sérialisée de ses écarts,
  qui devrait rester lisible quinze ans ; des tables propres, doubles de celles des nœuds et des
  lignes.
- **Le retard d'un devis propre ignore l'écriture d'une ligne de provision** : quand un risque
  réécrit sa provision, ce qui avance le compteur de la structure principale, les devis propres qui
  étaient à jour le restent. Écarté : un second compteur de la structure principale, que chaque
  écriture de l'arbre aurait à tenir.
- **La survenance est la fusion d'EP-08, dans un mode de plus** : les grandeurs courantes seules,
  les tâches retirées gardées et terminées quel que soit leur état, la trace posée sur les ajouts,
  ni marquage ni désignation de la référence. La greffe d'EP-08 (`graft`) disparaît. Écartée : une
  seconde application des écarts, à côté de celle de la fusion.
- **Une mesure, sans objectif nouveau.** La grille d'un devis propre entier tient l'objectif
  d'ouverture d'une grille (WF-QUA-0060) ; la recomposition, la mise à jour et le marquage d'un
  projet à vingt risques sont relevés, sans objectif, comme la fusion et la survenance en EP-08.

### Les états d'un devis propre

- **Entier** : sa structure porte tous les nœuds du projet, copiés sous leurs lignées, avec ce qu'il
  désigne, et elle a sa base, comme un différentiel d'avenant. Il naît entier à la déclaration du
  risque, et le redevient par la recomposition.
- **Élagué** : sa structure ne porte que ce qu'il désigne, il n'a pas de base, et il nomme la
  révision marquée contre la structure principale de laquelle ses écarts sont exacts. C'est l'état
  d'un devis propre élagué par un marquage, dans la révision marquée et dans celles qui le
  reprennent, jusqu'à sa recomposition.
- **À jour ou en retard**, comme un différentiel : à jour tant que la structure principale porte le
  compteur qu'il a retenu, l'écriture d'une ligne de provision mise à part. La copie d'une révision
  garde l'état qu'il avait dans la révision marquée, comme elle le fait d'un différentiel
  (`keep_differential_states`).
- **Consommé** (`is_merged`) : celui d'un risque survenu, élagué à ce qu'il désignait dans la
  révision où le risque est survenu ; la révision suivante n'en reprend que la ligne de structure,
  vide, comme aujourd'hui (`copy_consumed_estimate`).

### Tables et migrations

Une migration, dans le socle, chaînée sur la dernière de `main` à la création de la branche. Elle ne
reprend aucune donnée, et refuse de s'appliquer, en le disant, si une structure de nature `risk`
existe : aucune base à conserver ne porte de devis propre d'EP-08 (décision de l'auteur du
2026-11-21). Les tables révisées restent partitionnées par projet.

- **`cost_structure`** : le compteur retenu de la structure principale (`main_lock_version`) vaut
  aussi pour un devis propre — non nul si et seulement si la nature est `amendment` ou `risk` — ;
  une base nomme un devis propre comme elle nomme un différentiel ; une colonne nomme, pour un devis
  propre élagué, la révision marquée contre laquelle ses écarts sont exacts, non nulle si et
  seulement s'il est élagué, clé étrangère vers cette révision. La date de début de planning d'un
  devis propre est celle de la structure principale, recopiée à sa naissance, à sa recomposition et
  à sa mise à jour.
- **Une table des abandons**, révisée : ce qu'un devis propre élagué abandonne, par la lignée d'un
  nœud ou par les deux lignées d'une liaison. La copie d'une révision la reprend ; l'abandon d'une
  révision et la suppression du risque l'emportent.
- **`risk_evaluation`** : la gravité enregistrée, signée, nulle à la déclaration ; le coût à la
  survenance devient signé ; deux colonnes de plus, nulles hors de l'état survenu : la part du coût
  à la survenance qui ne tient pas aux lignes ajoutées, figée, et la valeur acquise que la
  survenance a apportée, signée.
- **`risk_review`** : la gravité retenue devient signée.
- **`risk_reference_share`** et **`node.origin_risk_id`**, inchangés : une provision ne descend pas
  sous zéro, et la trace ne marque que les ajouts.

Écartés : la gravité recalculée à chaque lecture, qu'un devis propre élagué ou en retard ne peut pas
donner ; la marche de valeur acquise dans les documents des indicateurs seuls, qui ne la rendraient
pas pour la révision en cours.

### Modules

| Module | Ce qu'il reçoit | Ce qu'il expose |
|---|---|---|
| `core/revisions` | les états d'un devis propre — entier, élagué, à jour, en retard — ; sa naissance avec sa base ; la mise à jour d'EP-08 étendue à la nature `risk` ; la recomposition et l'élagage, par deux registres où `core/planning` et `core/estimate` donnent chacun leur part ; le mode « survenance » de la fusion ; l'élagage au marquage ; l'état « à jour » porté par-dessus l'écriture d'une ligne de provision ; la copie d'un devis propre élagué et de ses abandons | `register_compose`, `register_prune` ; un registre appelé avant le marquage et avant la fusion d'un avenant, par lequel `core/risks` met à jour ses devis propres ou les refuse ; le mode de `register_merge` |
| `core/planning` | sa part de la recomposition et de l'élagage, tâches et liaisons ; le mode « survenance » de sa part de la fusion — une tâche retirée gardée et terminée quel que soit son état, les tâches terminées qu'elle rouvre — ; la lecture d'un devis propre élagué, ce qu'il désigne sous ses ancêtres ; la greffe (`graft`, `grafting.py`) retirée | ses parts des registres |
| `core/estimate` | sa part de la recomposition et de l'élagage, les lignes ; le mode « survenance » de sa part de la fusion — les grandeurs courantes seules, une ligne ajoutée à budgété nul, la trace — ; la lecture des lignes d'un devis propre élagué ; les crochets de la greffe retirés | ses parts des registres ; l'écart des totaux d'un devis propre et de sa base |
| `core/risks` | la gravité enregistrée, son calcul à chaque écriture du devis propre et à chaque mise à jour, la provision plafonnée ; la mise à jour d'un devis propre, sa permission et ses conditions ; les refus sur un devis propre en retard ; la survenance par la fusion, le coût signé, la part figée, la valeur acquise apportée ; la mise à jour de ses devis propres avant un marquage ou une fusion ; la tendance ; la gravité d'un survenu lue à son coût (#4400) | son interface, dont les signatures que `core/portfolio` lit ne changent pas |
| `core/indicators` | la marche d'une survenance sur les courbes de valeur acquise, dans le calcul du jour et dans les documents conservés | inchangé |
| `core/portfolio` | rien : il lit une gravité et un coût signés par l'interface de `core/risks` | inchangé |

Les modules ne se lisent que par leur interface. `core/risks` dépend de `core/revisions`,
`core/planning`, `core/estimate` et `core/risk_settings`, et aucun d'eux ne dépend de lui : ce que
le marquage et la fusion doivent savoir des devis propres passe par un registre.

### La recomposition, la mise à jour et l'élagage

- **La déclaration** crée le devis propre entier : `createRisk` copie la structure principale deux
  fois sous son verrou, sa structure et sa base, comme l'ouverture d'un différentiel
  (`create_differential`). Le devis propre ne désigne rien, et sa gravité est nulle.
- **La recomposition** rend entier un devis propre élagué. Sa base et sa structure sont copiées de
  la structure principale de la révision marquée qu'il nomme, puis rechiffrées et redatées dans la
  révision en cours, comme l'ouverture d'une révision le fait de toute structure ; ses écarts sont
  posés sur sa structure par la lignée — les nœuds qu'il garde remplacent ou complètent ceux de la
  copie, ce qu'il abandonne en sort — et le moteur de dates est rejoué une fois. Elle est sans
  conflit, ses écarts étant exacts contre cette structure principale, et laisse le devis propre en
  retard si la structure principale de la révision en cours a changé depuis. Elle ne change rien de
  ce qu'il désigne : ni compte rendu, ni confirmation, ni historique annulable, ni journal. C'est
  une opération nouvelle du contrat.
- **La mise à jour** est celle d'EP-08, étendue à la nature `risk` : mêmes trois structures, mêmes
  règles, même compte rendu, mêmes refus (`rebasing_of`, `register_rebase`, `register_rebase_end`).
  Elle enregistre en plus la gravité et la provision, que son compte rendu annonce. Elle demande un
  devis propre entier : sur un devis propre élagué, son compte rendu et son application sont
  refusés, la condition nommée, et l'écran le recompose d'abord. Elle est une saisie des risques,
  sous leur permission.
- **Le retard** se lit comme celui d'un différentiel, sur le compteur retenu. L'écriture d'une ligne
  de provision par `core/risks` avance le compteur de la structure principale : dans la même
  transaction, les devis propres qui étaient à jour retiennent le nouveau compteur. Leur base ne
  porte aucune ligne de provision, comme celle d'un différentiel (#4008).
- **La lecture.** Un devis propre entier se lit contre sa base, comme un différentiel
  (`compare_differential`). Un devis propre élagué présente ce qu'il désigne : ses nœuds, comparés
  par la lignée à la structure principale de la révision qu'il nomme, ses ancêtres présentés
  inchangés, ce qu'il abandonne présenté retiré.
- **Avant un marquage ou la fusion d'un avenant**, dans la tâche de fond et avant toute autre
  écriture : le devis propre de chaque risque identifié est recomposé s'il est élagué et en retard,
  puis mis à jour ; une mise à jour qui garde une valeur ou qui est refusée fait échouer la tâche,
  les risques nommés, rien n'étant écrit ; le devis propre entier d'un risque écarté est mis à jour
  d'office. Un devis propre élagué et à jour n'est pas touché.
- **L'élagage**, au marquage, réduit chaque devis propre entier et à jour à ce qu'il désigne par
  rapport à sa base (`designated`) : les nœuds désignés, leurs ancêtres et les extrémités de ses
  liaisons restent, ce qu'il abandonne entre à la table des abandons, le reste et la base sont
  supprimés, et il nomme la révision marquée. Un devis propre en retard à cet instant reste entier.
- **La copie d'une révision** reprend un devis propre élagué avec ses nœuds et ses abandons, sous la
  révision qu'il nommait, et un devis propre entier avec sa base, comme un différentiel non
  fusionné.
- **L'abandon d'une révision** emporte ses devis propres, entiers ou élagués, et ramène ceux de la
  dernière révision marquée, comme aujourd'hui.

### La gravité et la provision

- **La gravité** est l'écart des totaux réestimés d'un devis propre entier et de sa base, ni l'un ni
  l'autre ne portant de ligne de provision. Elle est calculée et enregistrée à chaque écriture du
  devis propre, par le suiveur qu'EP-08 a déclaré (`register_own_estimate_counted`), et à chaque
  mise à jour ; elle n'est jamais recalculée à la lecture, un devis propre élagué ou en retard
  rendant celle qu'il a enregistrée.
- **La provision** est la gravité pondérée par la probabilité, au centime, sans descendre sous zéro
  ; la ligne d'une opportunité reste, à montant nul.
- **La gravité d'un risque survenu** est son coût à la survenance, que son évaluation porte dans la
  révision où il est survenu et dans celles qui la reprennent (#4400).
- **La tendance** est calculée à la lecture : le produit signé de la gravité par la probabilité de
  l'évaluation de la révision lue, comparé à celui de l'évaluation de la révision marquée qui la
  précède. Le filtre et le tri du registre la lisent de même.
- **La matrice** classe la part signée de l'assiette : négative, elle est sous la première borne.

### La survenance

- **Elle demande un devis propre entier et à jour** ; l'écran le recompose et le met à jour d'abord.
- **Son compte rendu et son application sont ceux de la fusion** (`merge_parts`), dans le mode «
  survenance » : les ajouts créés à budgété nul et marqués du risque, les lignes désignées recevant
  leurs grandeurs courantes seules, les tâches retirées gardées et terminées quel que soit leur
  état, les tâches terminées qu'elle rouvre nommées. Ce qui la refuse est ce qui refuse une fusion.
- **La tâche de fond** `risk_occurrence` applique la fusion, retire la ligne de provision, passe
  l'évaluation à l'état survenu — le coût à la survenance, la gravité de cet instant ; la part
  figée, ce coût moins le montant des lignes ajoutées une fois fusionnées ; la valeur acquise
  apportée, le budgété des tâches qu'elle termine moins celui des tâches qu'elle rouvre —, écrit le
  réexamen de survenance, élague le devis propre à ce qu'il désignait et le marque consommé. Elle ne
  marque rien.
- **Ce qu'un risque survenu coûte aujourd'hui** est sa part figée, augmentée du montant réestimé
  courant des lignes qui portent sa trace.

### Le contrat

Modifié par un lot, avant le code qui le consomme, et le client réengendré. Chaque point passe par
une issue « contrat » que l'auteur tranche, ouverte avec les issues de l'EPIC, et s'inscrit dans
`docs/api/DECISIONS.md` ; le lot arrête les noms.

- **`CostStructure`** : l'état à jour d'un devis propre, et s'il est entier ou élagué ; la commande
  de mise à jour et celle de recomposition, listées sur un devis propre ; la date de début de
  planning d'un devis propre ne se saisit pas (`updateCostStructure`).
- **La recomposition**, opération nouvelle, `POST` sur un devis propre élagué de la révision en
  cours, sans corps ni confirmation : 200 et la structure ; 409 `STATE_FORBIDS_OPERATION`, la
  première condition qui manque.
- **`getStructureRebaseReport` et `rebaseCostStructure`** acceptent un devis propre, sous la
  permission de la saisie des risques ; `StructureRebaseReport` porte la gravité et la provision que
  la mise à jour enregistrerait, nulles pour un avenant ; un devis propre élagué les fait refuser.
- **`CommandCondition`** : deux conditions de plus, le devis propre à jour et le devis propre
  entier, que nomment les écritures de l'arbre et l'application d'un import sur un devis propre,
  `reviewRisk`, `getRiskOccurrenceReport` et `declareRiskOccurrence`.
- **`markRevision` et `mergeCostStructure`** : l'échec de leur tâche de fond qui nomme les risques
  dont la mise à jour garde une valeur ou est refusée, lu par `getBackgroundTask`.
- **`Risk`** : la gravité et le coût à la survenance signés ; ce dont la gravité dépend
  (`computed_fields`) ; `occurred_reestimated_amount` redit ; la tendance ; les commandes d'un
  risque dont le devis propre est en retard. **`RiskReview`** : la gravité signée.
- **`listRisks`** : le filtre et le tri de la tendance ; les bornes de la gravité acceptent une
  valeur négative.
- **`RiskOccurrenceReport`** : la forme de `StructureMergeReport` — les différences, les tâches
  terminées, les tâches rouvertes, la valeur acquise apportée et retirée, le montant de la
  provision, les motifs de refus, les compteurs — ; `own_estimate_past_planning_start_on` et la
  liste des tâches redatées en sortent (#4133, #4134), le signalement de #4240 s'étend à toute tâche
  rouverte.
- **`listNodes`** sur un devis propre : `NodeDifference` contre sa base s'il est entier, contre la
  structure principale de la révision qu'il nomme s'il est élagué.
- **`getEarnedValueCurves`** : la marche d'une survenance, datée, signée, avec sa cause
  (`CurveSeries`).
- **`ChartPreferences`** : l'état plié du graphique des risques d'un projet, sans objet.
- **Exemples**, engendrés par `make mock-data` : ceux qu'US-3150 nomme.

Les schémas servis par un EPIC livré qui changent de forme sont `CostStructure`, `Risk`,
`RiskOccurrenceReport`, `StructureRebaseReport` et `CurveSeries` ; les autres ne changent que de
description.

### Le service d'API et le worker

Les routeurs d'EP-08 servent déjà les risques, la survenance et la mise à jour d'un différentiel :
ils reçoivent leurs refus, et la recomposition a sa route à côté de la mise à jour. La mise à jour
et la recomposition d'un devis propre sont sous la permission d'écriture des risques, la lecture de
son compte rendu sous leur permission de lecture. Chaque réponse est validée contre le contrat dans
les tests. Le worker ne reçoit aucune tâche nouvelle : `revision_mark` et `structure_merge` mettent
à jour les devis propres avant d'écrire, et `risk_occurrence` applique la fusion dans son mode.

### Les indicateurs

La sélection des lignes d'EP-10 ne change pas : une tâche abandonnée, terminée, acquiert le budgété
de ses lignes comme toute tâche terminée, et les lignes ajoutées par une survenance en restent
exclues. La marche se lit de l'évaluation des risques survenus de la révision — la date de leur
réexamen de survenance, la valeur acquise apportée — pour le calcul du jour, et entre aux documents
conservés au marquage. L'empreinte du cache lit déjà le compteur des structures de la révision,
bases exclues, et ceux des risques.

### Le chargeur du témoin

Les trois risques sont déclarés comme le service les déclare, entiers, et leurs devis propres
remplis par les interfaces de l'arbre : 751 ajoute une tâche, modifie la charge d'une ligne et
abandonne une tâche, à gravité égale ; 752 et 753 ajoutent leurs tâches. Avant chaque marquage et
chaque fusion de la chronologie, le chargeur met les devis propres à jour par la fonction de la mise
à jour, sans compte rendu, comme il le fait d'un avenant. La survenance de 752 est rejouée par la
fusion (`load_occurrence`), sous les identifiants que le témoin impose. Le calcul du faux back
(`wftools.mockwitnessrisks`) reste indépendant de celui du service.

### Le front

Le devis propre s'ouvre dans les grilles du planning et du devis par ce qu'EP-08 a écrit pour un
avenant : la lecture contre la base, la note de retard, la commande de mise à jour et son compte
rendu (`amendment-late-note.tsx`, `rebase-amendment-command.tsx`), généralisés aux deux natures. S'y
ajoutent : la recomposition à l'ouverture d'un devis propre élagué ; l'enchaînement de la mise à
jour avant une saisie, un réexamen ou une survenance ; l'échec nommé d'un marquage ou d'une
contractualisation, d'où l'écran mène aux risques à lire ; le compte rendu de survenance ;
l'opportunité au registre et dans la matrice ; la colonne de tendance, son filtre et son tri ; le
graphique à bulles ; la marche sur l'écran des indicateurs. Aucune réponse n'est écrite à la main.

### Les tests du back

Les exemples chiffrés des Vérif de la spécification 1.0.9 sont au harnais d'exemples
(`fixtures/examples.json`), chacun citant son exigence. Le socle ajoute aux fabriques d'EP-08 un
projet chiffré à 1 000 dont un risque ajoute une ligne, en modifie une et abandonne une tâche ; son
devis propre en retard, la structure principale ayant reçu une tâche, une réestimation et la
suppression d'une tâche qu'il modifiait ; et le même, élagué par un marquage.

### La conduite

EP-30 se livre pendant la première vague de la ventilation du 2026-11-21, dont trois EPIC touchent
des fichiers voisins : EP-32, le moteur du planning ; EP-33, les imports ; EP-34, les grilles. Hors
de `core/risks`, EP-30 écrit `core/revisions` (structures, marquage, fusion, mise à jour), les parts
de `core/planning` et de `core/estimate` dans la fusion, la mise à jour et la copie, et retire la
greffe ; côté front, les composants des risques, ceux de l'avenant qu'il généralise, et le graphique
à bulles. Il ne touche ni le moteur de dates, ni les lecteurs des imports, ni les cellules des
grilles. Les conflits se règlent à chaque reprise de `main`, et le plan de lots dit les fichiers de
chaque lot.

### L'ordre de construction

1. **Le socle et le contrat**, en parallèle : la migration, les états d'un devis propre, sa
   naissance entière avec sa base, le retard porté par-dessus une ligne de provision, les fabriques
   ; le lot du contrat.
2. **Le devis propre entier** : sa lecture contre sa base et ses écritures (US-3070), la gravité
   enregistrée et la provision (US-3080).
3. **La mise à jour** étendue au devis propre et les refus sur un devis propre en retard (US-3090) ;
   à côté, **l'élagage, la recomposition et la copie** (US-3070).
4. **Le marquage et la fusion d'un avenant** devant les devis propres (US-3090), sur la mise à jour
   et l'élagage.
5. **La survenance** par la fusion (US-3100), puis la couverture (US-3110) et la valeur acquise
   (US-3120) ; la greffe retirée.
6. **La tendance** (US-3160, sa part du back) et **le portefeuille** (US-3130).
7. **Les écrans** (US-3140, US-3160), puis **le témoin** (US-3150), qui attend tout le back, et la
   vérification d'ensemble : le parcours, la définition de fini, les mesures.

---

## US-3070 — Le devis propre d'un risque, préparé comme un différentiel de la structure principale

- **statut** : à faire
- **exigences** : `WF-RIS-0030-A`
- **opérations** : `createRisk`, `listCostStructures`, `createRevision`, `abandonRevision`,
  `markRevision`, la recomposition d'un devis propre (nouvelle, écrite par la conception) ; sur le
  devis propre, `listNodes` et les écritures de l'arbre (`createNode`, `updateTaskFacet`,
  `updateEstimateLine`, `setPredecessors`, `moveNodes`, `deleteNode`, `previewPaste`, `applyPaste`),
  `openImport`, `applyImport`, `undoLastChange`, `redoLastUndo`
- **issue** : #4574

**En tant que** chef de projet, **je veux** préparer le devis propre d'un risque sur le planning et
le devis du projet tels qu'ils sont — y ajouter des tâches et des lignes, modifier celles qui
existent, en abandonner —, **afin de** chiffrer ce que le risque ferait au projet, et non un
fragment à part.

**Critères d'acceptation.**

- `WF-RIS-0030-A` — « La grille de devis d'un risque offre les mêmes opérations que celle du projet.
  » : le devis propre se lit et s'écrit par les opérations de l'arbre, sur sa structure de nature
  `risk`, sous `edit_planning` et `edit_estimate`, à tout état non terminal du projet, En cours
  compris ; elles y créent des tâches, des liaisons et des lignes, et y modifient, déplacent et
  suppriment celles de la structure principale comme les siennes ;
- `WF-RIS-0030-A` — « La modification du devis propre d'un risque identifié ne change ni le budget
  de référence, ni la valeur planifiée, ni la valeur acquise, ni les indices de coût et de délai ;
  elle change la provision, donc le reste à engager, l'avancement financier et la projection du chef
  de projet (WF-RAE-0010). » : tenu par EP-08 pour un devis propre qui ajoute ; ici, éprouvé sur un
  devis propre qui modifie une ligne existante et abandonne une tâche : les cinq premières grandeurs
  sont les mêmes avant et après, et la provision suit la gravité (US-3080) ;
- `WF-RIS-0030-A` — « La grille d'un devis propre qui vient d'être créé présente les tâches et les
  lignes de la structure principale, aucune n'étant présentée ajoutée, modifiée ou retirée. » :
  `createRisk` crée un devis propre qui ne désigne rien ; `listNodes` y rend les nœuds de la
  structure principale de la révision, tous `unchanged` ;
- `WF-RIS-0030-A` — « Dans le devis propre d'un risque, une tâche ajoutée après une tâche du projet,
  une ligne existante portée de 100 à 130 heures et une tâche existante abandonnée sont présentées
  ajoutée, modifiée et retirée ; la structure principale est inchangée. » : `listNodes` les rend
  `added`, `modified` — la valeur de la structure principale en regard — et `removed`
  (`NodeDifference`) ; aucune lecture de la structure principale ne change, ni son compteur ;
- `WF-RIS-0030-A` — « Une tâche ajoutée à la structure principale figure, sans y être désignée, dans
  la grille du devis propre d'un risque ouverte ensuite. » : à l'ouverture d'un devis propre en
  retard, l'écran le met à jour sans rien demander quand rien n'est à signaler (US-3090, US-3140),
  et sa grille présente alors le projet du jour avec ce qu'il désigne ; les dates et les montants
  sont ceux que le moteur de dates et le chiffrage donnent à sa structure ;
- propre à l'US : une révision marquée ne conserve d'un devis propre que ce qu'il désigne — les
  tâches, les liaisons et les lignes qu'il ajoute, les valeurs qu'il modifie, ce qu'il abandonne.
  Sur un projet de mille tâches et cinq mille lignes, le marquage d'une révision dont un risque
  ajoute deux tâches et modifie une ligne n'y laisse, pour son devis propre, que ces nœuds, leurs
  ancêtres et les extrémités de leurs liaisons, et `createRevision` n'en reprend pas davantage
  (décision de l'auteur du 2026-11-19) ; dans la révision en cours, il est entier, avec sa base, dès
  qu'on y travaille ;
- propre à l'US : chaque révision fige une version du devis propre : dans une révision marquée, sa
  grille présente ce qu'il désignait — les tâches et les lignes ajoutées, modifiées avec la valeur
  du projet en regard, abandonnées, sous leurs tâches parentes — et non le projet entier ;
  `createRevision` le reprend élagué, et `abandonRevision` ramène celui de la dernière révision
  marquée (WF-RIS-0020, WF-REV-0100) ; une révision qu'un avenant a marquée le garde entier, en
  retard ;
- propre à l'US : la recomposition d'un devis propre élagué le rend entier sans rien changer de ce
  qu'il désigne : après elle, sa grille présente ajouté, modifié et retiré ce que la révision
  marquée présentait ; elle n'entre ni à l'historique annulable ni au journal ;
- propre à l'US : le devis propre ne porte ni ligne de provision — la sienne, comme celles des
  autres risques, n'y figure pas —, ni rattachement au lotissement, ni avancement, ni reste à
  engager ; l'engendrement du squelette et `setNodeTracking` y sont refusés comme sur un
  différentiel (WF-PLA-0170, #2497) ; il n'a pas de date de début de planning à lui, celle de la
  structure principale étant la sienne ;
- propre à l'US : deux risques se préparent chacun seul : le devis propre de l'un ne présente rien
  de ce que l'autre désigne (décision de l'auteur du 2026-11-19) ;
- propre à l'US : une ligne d'une tâche terminée se modifie dans un devis propre, et une tâche
  terminée s'y abandonne, quand la structure principale refuse la saisie sous elle : la survenance
  appliquera la désignation (US-3100 ; décision de l'auteur du 2026-11-21) ;
- propre à l'US : toute saisie dans le devis propre avance `Risk.lock_version` avec le compteur de
  sa structure (#1453), entre à l'historique annulable comme une saisie de l'arbre, et recalcule la
  gravité et la provision dans la même écriture (US-3080) ; sur un devis propre en retard, elle
  attend la mise à jour (US-3090) ;
- propre à l'US : l'import d'un planning ou d'un devis sur le devis propre (`structure_id`) s'y
  applique comme sur un différentiel : ce que le fichier ajoute, change ou ne porte plus devient ce
  que le devis propre désigne, et la structure principale est inchangée ; le même fichier appliqué
  sur la structure principale laisse inchangé ce que le devis propre désigne, et le met en retard
  (WF-INTF-0090) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** EP-08 lit déjà un différentiel contre sa base (`compare_differential`,
US-2550/L3 puis US-3050/L2) et calcule ce qu'une structure désigne (`designated`, US-3050/L3) sans
nommer la nature « avenant » : ce sont les deux calculs que cette US reprend, le devis propre entier
ayant sa base comme un différentiel. La conception dit ses états — entier dans la révision en cours,
élagué au marquage —, la recomposition et l'élagage. Le devis propre d'EP-08, structure autonome qui
tient seule ses lignées (`holds_its_lineages`), disparaît.

**Hors périmètre.** La gravité et la provision (US-3080) ; la mise à jour et ses refus (US-3090) ;
la survenance (US-3100) ; les écrans (US-3140) ; le témoin (US-3150).

---

## US-3080 — La gravité d'un risque, écart net, la provision qui en est tirée, et l'opportunité

- **statut** : à faire
- **exigences** : `WF-RIS-0010-A`, `WF-RIS-0040-A`, `WF-RIS-0080-A`
- **opérations** : `getRisk`, `listRisks`, `listRiskReviews`, `getProjectRiskMatrix`, `createRisk`,
  `reviewRisk`, `updateRiskProvision`, `listNodes` (la ligne de provision), `getEstimateIndicators`,
  `getRemainingIndicators`
- **issue** : #4575

**En tant que** chef de projet, **je veux** que la gravité d'un risque soit ce que son devis propre
change au coût du projet — ce qu'il ajoute, les charges qu'il modifie, les tâches qu'il abandonne,
le glissement des tâches en aval —, et qu'un risque dont l'effet est une économie se lise comme une
opportunité, **afin que** la provision dise ce que le risque pèserait vraiment.

**Critères d'acceptation.**

- `WF-RIS-0010-A` — « La gravité et le montant de la provision ne sont pas saisissables, et suivent
  toute modification de la structure propre ou de la probabilité. » : aucune écriture ne porte la
  gravité ni la provision ; toute saisie dans le devis propre, toute mise à jour (US-3090) et tout
  réexamen de la probabilité recalculent, dans la même écriture, la gravité enregistrée et le
  montant de la ligne de provision ; une écriture de la structure principale ne les change pas ;
- `WF-RIS-0010-A` — « Un risque survenu dont le devis propre totalisait 200 présente une gravité de
  200 dans la révision suivante, qui ne reprend pas ce devis. » : la gravité d'un risque survenu est
  son coût à la survenance, lu de son évaluation dans la révision où il est survenu comme dans
  celles qui la suivent, au registre, à son tri, à son filtre de gravité et à sa part de l'assiette
  (#4400, repris d'EP-35) ;
- `WF-RIS-0010-A` — « Les trois états sont atteignables, et un risque écarté ne pèse plus sur le
  devis. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0010-A` — « La confirmation d'un risque sans modification produit un réexamen daté. » :
  tenu par EP-08 ; sur un devis propre en retard, elle attend la mise à jour (US-3090) ;
- `WF-RIS-0010-A` — « Un risque déclaré sans désignation de tâche porte sa provision sur la première
  tâche de premier niveau ; la ligne peut être déplacée sur une autre tâche de la structure
  principale, et le total du devis est inchangé. » : tenu par EP-08 ; la désignation reste (décision
  de l'auteur du 2026-11-21) et ne dit plus que l'endroit où la provision pèse, son lot et ses dates
  : la survenance ne place rien sous cette tâche (US-3100) ;
- `WF-RIS-0010-A` — « Sur une révision sans tâche, la déclaration d'un risque est refusée, de même
  que le retour d'un risque écarté à l'état identifié ; l'une et l'autre aboutissent dès qu'une
  tâche existe. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0010-A` — « Avec deux catégories actives de type provision pour risques, la déclaration
  d'un risque demande laquelle porte sa provision, et la ventilation du devis présente la provision
  sous la nature de la catégorie choisie ; avec une seule, elle ne la demande pas. » : tenu par
  EP-08, non touché ici ;
- `WF-RIS-0010-A` — « Sans aucune catégorie active de ce type, la déclaration d'un risque est
  refusée et nomme la condition manquante. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0010-A` — « La suppression de la tâche qui porte une provision de 40 laisse le devis
  inchangé, la provision étant passée sur la tâche parente. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0010-A` — « Un risque écarté dont la catégorie a été désactivée redevient identifié avec
  la catégorie active choisie. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0010-A` — « Un risque écarté qui redevient identifié porte sa provision sur la tâche qu'il
  désignait ; si cette tâche a été supprimée entre-temps, sur la première tâche de premier niveau. »
  : tenu par EP-08 ; son devis propre, gardé pendant qu'il était écarté, est mis à jour avant son
  retour (US-3090), et la ligne recréée porte la gravité recalculée pondérée par la probabilité ;
- `WF-RIS-0010-A` — « Sans catégorie active de ce type, son retour à l'état identifié est refusé et
  nomme la condition manquante. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0010-A` — « Un risque déclaré sur le sous-projet S2 porte sa provision au reste à engager
  de S2 ; sans sous-projet désigné, elle compte hors sous-projet. » : tenu par EP-08, non touché ici
  ;
- `WF-RIS-0040-A` — « Les six colonnes sont présentes, ainsi que l'accès aux deux notes et à
  l'historique. » : tenu par EP-08 ; la gravité rendue est l'écart net, signée, et l'historique des
  réexamens garde, signée, celle que chacun a retenue ;
- `WF-RIS-0040-A` — « Le tri par provision classe les risques du plus lourd au plus léger. » : tenu
  par EP-08 ; une opportunité, de provision nulle, se classe avec les provisions nulles ;
- `WF-RIS-0040-A` — « Un risque dont la probabilité augmente change de couleur conformément à la
  matrice. » : tenu par EP-08 ; une opportunité reste au plus bas niveau de gravité, quelle que soit
  sa probabilité ;
- `WF-RIS-0040-A` — « Les trois totaux — identifiés, survenus, écartés — sont distincts, et la
  réserve pour risques de la référence est affichée en regard. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0080-A` — « Un devis propre qui ajoute deux lignes de 120 et 80 donne une gravité de 200.
  » ;
- `WF-RIS-0080-A` — « Un devis propre qui ajoute une ligne de 300 et abandonne une tâche dont les
  lignes totalisent 100 donne une gravité de 200. » ;
- `WF-RIS-0080-A` — « Un devis propre qui porte de 100 à 130 le montant réestimé d'une ligne
  existante donne une gravité de 30. » ;
- `WF-RIS-0080-A` — « Sur un projet au taux d'inflation de 3 %, un devis propre dont une tâche
  ajoutée repousse de l'année de référence à la suivante la consommation d'une ligne de 1 000 compte
  30 dans la gravité. » : la gravité est calculée sur les dates que le moteur donne à la structure
  principale portant ce que le devis propre désigne, tâches en aval comprises (WF-DEV-0030) ;
- `WF-RIS-0080-A` — « Un devis propre qui n'abandonne qu'une tâche de 100 donne une gravité de −100
  : le registre présente le risque comme une opportunité, sa provision est nulle, et le total du
  devis est celui du projet sans lui. » ;
- `WF-RIS-0080-A` — « Une réestimation dans la structure principale ne change ni la gravité ni la
  provision d'un risque avant la mise à jour de son devis propre. » ;
- `WF-RIS-0010-A` — « Un risque de gravité 200 et de probabilité 30 % porte une provision de 60. » :
  la provision est la gravité pondérée par la probabilité, au centime ;
- `WF-RIS-0010-A` — « Un risque de gravité −100 et de même probabilité porte une provision nulle, et
  non de −30. » : la provision ne descend pas sous zéro ; la ligne de provision d'une opportunité
  reste, à montant nul ;
- `WF-RIS-0040-A` — « Un risque de gravité négative est présenté comme une opportunité, avec une
  provision nulle, et figure dans la matrice au plus bas niveau de gravité. » : `matrix_cell` et
  `getProjectRiskMatrix` la classent au premier niveau de gravité, sa part de l'assiette étant sous
  la première borne (WF-REF-0160), et la comptent dans sa case ;
- écart : `WF-RIS-0040-A` — « Un risque identifié dont le produit de la gravité par la probabilité
  est passé de 60 à 75 depuis la révision marquée précédente est présenté en hausse ; passé de 60 à
  45, en baisse ; resté à 60, stable. » : la tendance est d'US-3160 ;
- écart : `WF-RIS-0040-A` — « Un risque identifié qui ne l'était pas dans la révision marquée
  précédente est présenté comme nouveau ; un risque écarté ou survenu ne présente aucune tendance. »
  : la tendance est d'US-3160 ;
- écart : `WF-RIS-0040-A` — « Le registre se filtre et se trie sur la tendance. » : la tendance est
  d'US-3160 ;
- propre à l'US : la gravité est l'écart net des montants réestimés, lignes de provision exclues :
  le total de la structure principale portant ce que le devis propre désigne, moins son total sans
  lui ; elle compte les lignes ajoutées, l'écart des lignes modifiées, les lignes des tâches
  abandonnées en moins, et ce que le glissement des tâches en aval change à leur montant ; elle est
  nulle tant que le devis propre ne désigne rien ;
- propre à l'US : la gravité est enregistrée avec l'évaluation du risque dans la révision :
  `Risk.severity` et `RiskReview.severity` la rendent signée, `computed_fields` dit ce dont elle
  dépend, et une révision marquée rend celle qu'elle a figée, calculée sur sa structure principale
  puisque le marquage exige des devis propres à jour (US-3090) ;
- propre à l'US : le registre se filtre et se trie sur une gravité négative, par les bornes et les
  tris de la gravité que le contrat porte déjà (H-01) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** Aujourd'hui `core/risks` lit la gravité comme le total du devis propre de
la révision (`structure_amounts`, `core/estimate/severities.py`), et la révision qui suit une
survenance, qui ne reprend pas ce devis, rend zéro (#4400). Les contraintes du schéma livré refusent
un montant négatif pour le coût à la survenance, la gravité d'un réexamen et la part de la référence
: la conception dit lesquelles tombent. `Money` est déjà signé au contrat. `docs/api/DECISIONS.md` :
« Les risques : coût à la survenance, provision de référence, probabilité par le réexamen » (H-03,
H-06, H-07).

**Hors périmètre.** Le coût à la survenance et la couverture (US-3110) ; la mise à jour qui
recalcule la gravité (US-3090) ; le portefeuille (US-3130) ; les écrans (US-3140).

---

## US-3090 — La mise à jour d'un devis propre, et ce qui l'exige : la saisie, le réexamen, la survenance, le marquage

- **statut** : à faire
- **exigences** : `WF-RIS-0070-A` ; les règles de la mise à jour d'un différentiel (WF-REV-0110)
  et le réexamen (WF-RIS-0020), dont aucune phrase de Vérif ne change, restent closes par EP-08
- **opérations** : `getStructureRebaseReport`, `rebaseCostStructure` (étendues au devis propre), la
  recomposition d'un devis propre (nouvelle), `listCostStructures`, `reviewRisk`, les écritures de
  l'arbre et `applyImport` sur un devis propre, `getRiskOccurrenceReport`, `declareRiskOccurrence`,
  `markRevision`, `getStructureMergeReport`, `mergeCostStructure` (leur refus), `getRisk`,
  `listRisks` (les commandes)
- **issue** : #4577

**En tant que** chef de projet, **je veux**, à chaque revue, confronter ce que chaque risque désigne
au projet tel qu'il est devenu, lire ce qui ne s'y rattache plus et voir sa gravité recalculée avant
de confirmer sa probabilité, **afin que** ni le registre ni une révision marquée ne gardent la
gravité d'un projet qui n'existe plus.

**Critères d'acceptation.**

- `WF-RIS-0070-A` — « Après une réestimation dans la structure principale, le devis propre d'un
  risque identifié est en retard, et sa gravité et sa provision sont inchangées ; ouvert, il est mis
  à jour sans confirmation, et sa grille présente la réestimation. » : `CostStructure` dit un devis
  propre à jour à la déclaration du risque et après sa mise à jour, en retard dès qu'une écriture
  change la structure principale, qu'elle touche ou non ce qu'il désigne, hors l'écriture d'une
  ligne de provision ;
- `WF-RIS-0070-A` — « La mise à jour du devis propre d'un risque ne met pas en retard celui d'un
  autre. » : elle réécrit sa ligne de provision dans la structure principale, et l'écriture d'une
  ligne de provision — son montant, sa catégorie, son sous-projet, sa tâche — ne met aucun devis
  propre en retard ;
- `WF-RIS-0070-A` — « Sur un devis propre en retard, une saisie, la confirmation du risque et la
  déclaration de sa survenance n'aboutissent qu'une fois le devis propre mis à jour. » : les
  écritures de l'arbre et l'application d'un import sur le devis propre, `reviewRisk`,
  `getRiskOccurrenceReport` et `declareRiskOccurrence` répondent 409 `STATE_FORBIDS_OPERATION`, par
  une condition que le lot du contrat nomme, et rien n'est écrit ; l'écran enchaîne la mise à jour
  (US-3140) ;
- `WF-RIS-0070-A` — « Une mise à jour qui ne signale rien s'applique sans confirmation ; celle qui
  garde une valeur contre le projet présente son compte rendu, à confirmer. » : le compte rendu ne
  signale rien quand il ne porte ni différence gardée ni motif de refus, la gravité recalculée
  n'étant pas un signalement (décision de l'auteur du 2026-11-21) ;
- `WF-RIS-0070-A` — « La mise à jour d'un devis propre dont une tâche ajoutée suit une tâche que le
  projet a repoussée d'un an recalcule sa gravité sur les dates nouvelles, et sa provision la suit.
  » : `rebaseCostStructure` enregistre la gravité calculée sur le projet du jour, et la ligne de
  provision en prend le montant dans la même écriture ;
- `WF-RIS-0070-A` — « Une ligne que le devis propre porte à 130 heures et que le projet a réestimée
  à 110 garde 130 après la mise à jour, et le compte rendu la nomme. » : une différence `kept`, ses
  champs nommés (règle 1 de WF-REV-0110) ;
- `WF-RIS-0070-A` — « Une tâche que le devis propre modifie et que le projet a supprimée y figure,
  après la mise à jour, comme une tâche ajoutée, et le compte rendu la nomme. » : règle 2 de
  WF-REV-0110 ; une tâche ou une ligne qu'il ajoute sous une tâche que le projet n'a plus passe sous
  l'ancêtre le plus proche qui reste, et une liaison qu'il ajoute vers une tâche que le projet n'a
  plus est retirée, l'une et l'autre nommées (règles 3 et 4) ;
- `WF-RIS-0070-A` — « Un risque dont le devis propre est en retard est écarté sans mise à jour ; son
  retour à l'état identifié l'exige. » : `reviewRisk` qui écarte n'est pas refusé ; celui qui laisse
  ou rend le risque identifié l'est tant que le devis propre est en retard ;
- `WF-RIS-0070-A` — « Lorsque deux risques modifient la même ligne et que l'un survient, la mise à
  jour de l'autre garde la valeur qu'il désigne et la nomme. » ;
- `WF-RIS-0070-A` — « Au marquage d'une révision, le devis propre en retard d'un risque identifié
  est mis à jour sans confirmation quand sa mise à jour ne signale rien ; lorsqu'elle garde une
  valeur ou qu'elle est refusée, le marquage n'aboutit pas et nomme le risque. » : la tâche de fond
  du marquage recompose et met à jour, avant toute autre écriture, le devis propre de chaque risque
  identifié ; elle échoue en nommant les risques dont la mise à jour garde une valeur ou est
  refusée, rien n'étant écrit ; le devis propre entier d'un risque écarté est mis à jour d'office,
  sans que ce qu'il garde soit présenté, et celui d'un risque survenu ne compte pas ;
- `WF-RIS-0070-A` — « La contractualisation d'un avenant met à jour de même les devis propres en
  retard, et n'aboutit pas lorsque l'une de ces mises à jour garde une valeur ou est refusée. » : la
  tâche de fond de la fusion fait de même avant d'écrire la structure principale, et échoue de même
  ; la fusion n'écrit aucun devis propre, et la révision qu'elle marque les garde entiers, en retard
  ;
- propre à l'US : la gravité qu'une révision marquée fige est ainsi calculée sur sa structure
  principale ; la révision qu'un avenant marque fige celle du projet d'avant l'avenant, sa fusion
  écrivant la structure principale et marquant dans la même opération, et la mise à jour la
  recalcule dans la révision suivante (limite connue, décision de l'auteur du 2026-11-21) ;
- `WF-RIS-0070-A` — « Une mise à jour qui laisserait une boucle de liaisons dans le devis propre est
  refusée et nomme le motif. » : comme une liaison interdite, une date au-delà de l'horizon ou une
  tâche sans heure travaillée, le motif et la tâche nommés au compte rendu (`ReportRefusal`), rien
  n'étant écrit ; le lien fautif retiré du devis propre, elle aboutit ;
- propre à l'US : `getStructureRebaseReport` sur un devis propre est celui d'un différentiel, une
  lecture qui n'écrit rien : ce que la mise à jour reporte de la structure principale, ce que le
  devis propre garde contre elle (`kept`), les motifs qui la refusent, les compteurs lus, et en plus
  la gravité et la provision qu'elle enregistrerait ; sur un devis propre élagué, il est refusé, la
  condition nommée, et l'écran le recompose d'abord ;
- propre à l'US : `rebaseCostStructure` sur un devis propre, avec les compteurs lus, écrit ce que le
  compte rendu a présenté ; le devis propre est à jour, et la structure principale n'est écrite que
  par la ligne de provision ; un compteur changé depuis la lecture, 412 `STALE_LOCK_VERSION`, rien
  n'est écrit ;
- propre à l'US : la mise à jour d'un devis propre est une saisie des risques, sous leur permission
  d'écriture, et non sous celle de l'ouverture d'un différentiel ; elle est offerte sur le devis
  propre d'un risque identifié ou écarté de la révision en cours, et refusée par 409 sur celui d'un
  risque survenu, sur une révision marquée, pendant un traitement de fond et sur un devis propre
  élagué ou à jour, la première condition qui manque nommée dans l'ordre du contrat ;
- propre à l'US : la mise à jour n'entre pas à l'historique annulable, comme celle d'un différentiel
  ; une saisie du devis propre faite avant elle s'annule encore, sauf sur ce qu'elle a réglé, où
  l'annulation est refusée en nommant l'objet (WF-IHM-0110) ; l'annulation d'un réexamen rend au
  risque la probabilité, l'état et la provision d'avant, la gravité n'ayant pas changé dans le
  réexamen (décision de l'auteur du 2026-11-21 : un geste, deux opérations) ;
- propre à l'US : la fusion d'un avenant, la survenance d'un autre risque, un import et toute saisie
  de la structure principale mettent les devis propres en retard, et ne leur font rien d'autre
  (décision de l'auteur du 2026-11-21) ;
- propre à l'US : une désignation sur une tâche que le projet a terminée depuis est gardée par la
  mise à jour, sans être signalée : c'est la survenance qui l'applique et le signale (US-3100) ;
- propre à l'US : un risque dont le devis propre est en retard le dit par ses commandes : le
  réexamen et la déclaration de survenance indisponibles, la condition nommée, et la mise à jour
  disponible (`available_commands`) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** EP-08 tient l'état « à jour » d'un différentiel par le compteur que la
structure principale portait quand sa base a été prise, et sa mise à jour par deux registres
(`register_rebase`, `register_rebase_end`) où `core/planning` et `core/estimate` donnent chacun leur
part, sans nommer la nature du différentiel. Le devis propre entier a sa base, comme un différentiel
: sa mise à jour est celle d'EP-08, étendue à sa nature. Le réexamen lui-même (`reviewRisk`) ne
change que par son refus. Le marquage et la fusion sont de `core/revisions`, dont `core/risks`
dépend et non l'inverse : ce qu'ils doivent savoir des devis propres en retard passe par un
registre, comme la copie et la désignation d'une révision (EP-08, « Modules »).

**Hors périmètre.** Le calcul de la gravité (US-3080) ; la survenance (US-3100) ; l'écran qui
enchaîne la mise à jour et le réexamen (US-3140).

---

## US-3100 — La survenance fusionne ce que le devis propre désigne

- **statut** : à faire
- **exigences** : `WF-RIS-0060-A`
- **opérations** : `getRiskOccurrenceReport`, `declareRiskOccurrence`, `getBackgroundTask`,
  `listNodes` et `compareRevisions` (`is_from_risk`, `origin_risk_ids`), `getRisk`
- **issue** : #4576

**En tant que** chef de projet, **je veux** déclarer qu'un risque est survenu après avoir lu ce que
cela fera du projet — ce qu'il ajoute, les charges qu'il change, les tâches qu'il abandonne —,
**afin que** le planning et le devis du projet deviennent ceux que j'avais préparés pour ce cas,
sans toucher au budget de référence.

**Critères d'acceptation.**

- `WF-RIS-0060-A` — « Après déclaration de survenance d'un risque dont le devis propre porte deux
  lignes de 120 et 80, ces lignes figurent dans la structure principale de la révision en cours avec
  des montants budgétés nuls et des montants réestimés de 120 et 80 ; la ligne de provision a
  disparu ; le budget de référence et la révision de référence sont inchangés ; le reste à engager a
  augmenté de 200 moins la provision retirée ; la terminaison de ces tâches n'acquiert aucune
  valeur. » : tenu par EP-08 pour un devis propre greffé ; ici, par la fusion de ce que le devis
  propre désigne : les deux lignes qu'il ajoute sont créées dans la structure principale, budgété
  nul, réestimé 120 et 80 ; la ligne de provision n'y est plus ; la révision de référence et son
  budget sont les mêmes ; le reste à engager a monté de 200 moins la provision ; que leur
  terminaison n'acquière rien est éprouvé par US-3120 ;
- `WF-RIS-0060-A` — « Les tâches ajoutées se trouvent à la place, avec les liaisons et aux dates que
  le devis propre leur donnait ; la tâche qui portait la provision ne reçoit aucune tâche. » : la
  règle de la greffe d'EP-08, sous la tâche qui portait la provision, est remplacée (décision de
  l'auteur du 2026-11-19) ; la spécification 1.0.9 réécrit la phrase et retire celle du jalon, sans
  objet puisque la tâche qui porte la provision ne reçoit plus rien (#4518) ;
- `WF-RIS-0060-A` — « Une ligne fusionnée par la survenance d'un risque est encore désignée comme
  issue de ce risque dans la révision suivante, et après son déplacement sous une autre tâche ; une
  ligne ajoutée ensuite sous une tâche issue du risque ne l'est pas. » : tenu par EP-08 ;
  `origin_risk_id` est posé sur les tâches et les lignes que la survenance ajoute, et sur elles
  seules (décision de l'auteur du 2026-11-21) ;
- `WF-RIS-0060-A` — « Les grilles de planning et de devis se filtrent sur les tâches et les lignes
  issues d'un risque, ou d'un risque donné (WF-IHM-0130). » : tenu par EP-08 ; `is_from_risk` et
  `origin_risk_ids` rendent les ajouts d'une survenance, non ce qu'elle a modifié ou terminé ;
- `WF-RIS-0060-A` — « Après la survenance d'un risque qui porte de 100 à 130 le montant réestimé
  d'une ligne budgétée à 100, la ligne porte un montant budgété de 100 et un montant réestimé de 130
  ; elle n'est pas désignée comme issue de ce risque. » : la ligne garde ses grandeurs de référence
  et prend pour grandeurs courantes celles que le devis propre désigne ;
- `WF-RIS-0060-A` — « Une tâche non démarrée budgétée à 100 que le risque abandonne est conservée,
  terminée le jour de la survenance, son reste à engager est nul, et le montant budgété de ses
  lignes est inchangé. » : il en va de même d'une tâche démarrée ; c'est la règle qu'un avenant
  applique à une tâche démarrée qu'il retire (WF-REV-0050) ;
- `WF-RIS-0060-A` — « Le compte rendu d'une survenance qui abandonne une tâche budgétée à 100 nomme
  cette tâche comme terminée et annonce une valeur acquise de 100 ; l'abandon à cette étape laisse
  la révision en cours inchangée. » ;
- `WF-RIS-0060-A` — « La survenance d'un risque qui modifie une ligne d'une tâche terminée rouvre
  cette tâche, et le compte rendu le signale sans refuser. » : il en va de même d'une tâche ajoutée
  sous une récapitulative terminée ; le signalement est celui qu'EP-08 a écrit pour une greffe sous
  une tâche terminée (#4240), étendu à toute tâche que la survenance rouvre, avec la valeur acquise
  qu'elle retire ;
- `WF-RIS-0060-A` — « Une tâche ajoutée à la structure principale après la préparation du devis
  propre, que celui-ci ne désigne pas, figure toujours dans la structure principale après la
  survenance. » ;
- propre à l'US : `getRiskOccurrenceReport` est une lecture qui n'écrit rien, dans la forme du
  compte rendu d'une fusion : les tâches, les liaisons et les lignes ajoutées, celles que la
  survenance modifie avec leurs champs, la ligne de provision retirée et son montant, les tâches
  abandonnées qu'elle termine, les tâches terminées qu'elle rouvre, la valeur acquise apportée et
  retirée, les motifs de refus, les compteurs lus de la structure principale et du risque, et
  `creates_current_revision` ; un risque qui n'est pas identifié reçoit 409, comme un devis propre
  en retard (US-3090) ;
- propre à l'US : le compte rendu ne nomme plus les tâches de la structure principale que le moteur
  redate, et ne signale plus un devis propre qui commence avant le jour : la grille du devis propre,
  à jour, montre le planning que la survenance laissera (#4133, #4134, règles provisoires d'EP-08) ;
- propre à l'US : `declareRiskOccurrence` exige les compteurs et `creates_current_revision` tels que
  lus, 412 `STALE_LOCK_VERSION` sinon ; la survenance est une tâche de fond et une seule opération,
  qui en échec ne laisse rien ; sans révision en cours, elle en crée une au préalable, aux taux
  conservés, projetés ; la tâche aboutie porte `task_occurrence_succeeded` ;
- propre à l'US : ce qui refuse la survenance est ce qui refuse une fusion, jugé sur la structure
  qu'elle laisse : une boucle, une liaison interdite, l'horizon, une tâche sans heure travaillée, un
  poste sorti du sous-arbre de son lot (WF-PLA-0170) ;
- propre à l'US : le risque survenu garde son coût à la survenance, sa gravité à cet instant
  (US-3110) ; son dernier réexamen est la survenance ; son devis propre se lit `is_merged` dans la
  révision où il est survenu, avec ce qu'il désignait, et n'est pas repris par la suivante ;
- propre à l'US : la survenance ne marque aucune révision, ne déplace pas la référence, n'entre pas
  à l'historique annulable, et aucune transition ne part de l'état survenu ; l'abandon de la
  révision en cours la défait, le risque redevenant identifié avec son devis propre et sa provision
  (WF-RIS-0020) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** La survenance d'EP-08 greffe un sous-arbre (`graft`,
`core/planning/grafting.py`) : cette US la remplace par la fusion d'EP-08 (`merge_tasks`,
`merge_lines`, `register_merge`), appliquée sur les grandeurs courantes seules et sans marquage ni
désignation de référence. La fusion d'un avenant donne aux lignes désignées leurs grandeurs de
référence, et garde une tâche retirée seulement si elle est démarrée : la conception dit ce que la
survenance en partage et ce qui lui est propre. `docs/api/DECISIONS.md` : « Le compte rendu
préalable de la survenance d'un risque » (#1453), « Les lignes issues d'un risque survenu gardent sa
trace » (#1761).

**Hors périmètre.** Le coût à la survenance et la couverture (US-3110) ; la valeur acquise et sa
marque (US-3120) ; l'écran (US-3140).

---

## US-3110 — Le coût à la survenance, la couverture et le suivi d'un risque survenu

- **statut** : à faire
- **exigences** : `WF-RIS-0050-A`
- **opérations** : `getProjectRiskCoverage`, `listRisks` (`ProvisionTotals`, `occurrence_cost`,
  `occurred_reestimated_amount`), `getRisk`, `getRemainingIndicators` (`coverage`)
- **issue** : #4578

**En tant que** chef de projet, **je veux** que ce qu'un risque survenu a coûté soit son effet net
sur le projet le jour où il est survenu, et le suivre ensuite contre ce qu'il coûte aujourd'hui,
**afin de** savoir si la réserve y suffisait, que le risque ait ajouté du travail, changé des
charges ou abandonné des tâches.

**Critères d'acceptation.**

- `WF-RIS-0050-A` — « Sur un projet chiffré à 1 000 portant un risque de gravité 200 à 30 %, le
  devis totalise 1 060, le budget de référence 1 000 et la réserve 60. » : tenu par EP-08 ; la
  gravité de 200 est celle d'un devis propre qui ajoute 200 ;
- `WF-RIS-0050-A` — « Après survenance de ce risque, réévalué à 250, le budget de référence vaut
  toujours 1 000, les provisions restantes 0, le coût des survenus 250, et l'écart de couverture
  −190. » : tenu par EP-08 ; le coût des survenus est la gravité du risque, écart net, au moment de
  sa survenance ;
- `WF-RIS-0050-A` — « Sur le même projet, un second risque de provision 40 présent dans la référence
  porte la réserve à 100 ; l'écarter fait passer les provisions restantes de 40 à 0 sans toucher le
  budget de référence, et l'écart de couverture de −190 à −150. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0050-A` — « Sur un projet dont la réserve est nulle et sans risque survenu, un risque
  identifié après la référence, de provision 30, porte les provisions restantes à 30 et l'écart de
  couverture à −30. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0050-A` — « La terminaison des tâches issues d'un risque survenu ne change ni le coût des
  survenus ni l'écart de couverture. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0050-A` — « Sur le projet dont le risque est survenu à 250 : un avenant qui ne touche pas
  aux risques laisse la réserve à 60 et l'écart de couverture à −190 ; un avenant qui intègre au
  budget de référence les lignes de ce risque porte le budget de référence à 1 250 et laisse la
  réserve à 60 et l'écart à −190 ; un avenant qui déclare un nouveau risque de provision 50 porte la
  réserve à 110 et les provisions restantes à 50, et laisse l'écart à −190. » : tenu par EP-08, non
  touché ici ;
- `WF-RIS-0050-A` — « Sur le projet dont le risque est survenu à 250, la réestimation à 300 des
  lignes qui en sont issues présente 300 en regard de 250, et laisse l'écart de couverture à −190. »
  : tenu par EP-08 pour un risque qui n'a fait qu'ajouter ; ici, ce qui se lit en regard est le
  montant réestimé courant des lignes ajoutées, augmenté de la part figée à la survenance ;
- `WF-RIS-0050-A` — « Un risque survenu qui abandonne une tâche de 100 et ajoute une ligne de 300 a
  un coût à la survenance de 200. » ;
- `WF-RIS-0050-A` — « Un risque survenu à 250, dont 150 de lignes ajoutées et 100 de lignes
  modifiées, présente 250 en regard de 250 ; la réestimation à 200 des lignes ajoutées présente 300,
  et celle des lignes modifiées ne change pas ce montant. » : la part du risque dans ce qu'il a
  modifié et abandonné est figée à la survenance, et le réestimé présenté en regard ne suit que les
  lignes qu'il a ajoutées (décision de l'auteur du 2026-11-19) ;
- `WF-RIS-0050-A` — « Sur un projet de réserve 60 dont un risque est survenu à 250, la survenance
  d'une opportunité de −50 porte le coût des survenus à 200 et l'écart de couverture de −190 à −140.
  » : le coût à la survenance est signé, et la couverture le compte tel quel (décision de l'auteur
  du 2026-11-21) ;
- propre à l'US : `occurrence_cost` est la gravité enregistrée au moment de la survenance, figée :
  ni une réestimation, ni la terminaison des tâches, ni un avenant ne la changent ; l'abandon de la
  révision où le risque est survenu l'efface (WF-RIS-0020) ;
- propre à l'US : `getProjectRiskCoverage` rend la réserve, les provisions restantes, le coût des
  survenus, signé, l'écart de couverture `reserve − (remaining_provisions + occurred_cost)` et, en
  regard, ce que les survenus coûtent aujourd'hui ; `coverage` de `getRemainingIndicators` et
  `ProvisionTotals` leur sont égaux ;
- propre à l'US : la couverture d'une révision marquée est conservée à son marquage et rendue telle
  quelle, coût signé compris (WF-DAT-0040) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** EP-08 fige le coût à la survenance comme le total du devis propre avant sa
greffe (`structure_amount`), et lit le réestimé en regard sur les lignes marquées `origin_risk_id`.
La part figée — le coût à la survenance moins le montant des lignes ajoutées à cet instant — se
conserve avec l'évaluation du risque : la conception dit où. `docs/api/DECISIONS.md` : « Les risques
: coût à la survenance, provision de référence… » (H-01, H-02, M-01).

**Hors périmètre.** La gravité avant la survenance (US-3080) ; la valeur acquise (US-3120) ; la
couverture du portefeuille (US-3130).

---

## US-3120 — La valeur acquise devant une survenance qui termine ou rouvre des tâches, et sa marque sur les courbes

- **statut** : à faire
- **exigences** : `WF-IND-0030-A`, `WF-IND-0140-A`
- **opérations** : `getProjectIndicators`, `getEarnedValueCurves`, `getIndexHistory`, `markRevision`
  (la conservation), `declareRiskOccurrence`
- **issue** : #4579

**En tant que** chef de projet, **je veux** que la valeur acquise compte à son budget une tâche
qu'un risque survenu abandonne, et que la courbe dise ce que la survenance lui a fait ce jour-là,
**afin que** le projet atteigne encore son budget de référence une fois tout terminé, et qu'un saut
de l'indice de délai ne se lise pas comme une avance.

**Critères d'acceptation.**

- `WF-IND-0030-A` — « Une tâche terminée le 12 du mois contribue à la valeur acquise dès cette date,
  non à la revue suivante. » : tenu par EP-10, non touché ici ;
- `WF-IND-0030-A` — « Une tâche dont le coût réel dépasse le montant budgété contribue pour le
  montant budgété. » : tenu par EP-10, non touché ici ;
- `WF-IND-0030-A` — « La valeur acquise d'un projet dont toutes les tâches sont terminées égale son
  budget de référence ; les tâches issues d'un risque survenu n'y contribuent pas. » : tenu par
  EP-10 et EP-08 ; ici, sur un projet dont un risque survenu a abandonné une tâche budgétée et en a
  ajouté d'autres, toutes terminées : la tâche abandonnée a acquis son montant budgété, les tâches
  ajoutées rien, et la valeur acquise égale le budget de référence ;
- `WF-IND-0030-A` — « Une tâche budgétée à 100 qu'un risque survenu abandonne contribue pour 100 à
  la valeur acquise à la date de la survenance. » ;
- `WF-IND-0140-A` — « Après la survenance, le 20 du mois, d'un risque qui abandonne une tâche
  budgétée à 100, la courbe de valeur acquise porte au point de ce mois une marche de 100, datée du
  20 et attribuée à la survenance. » ;
- `WF-IND-0140-A` — « La survenance d'un risque qui rouvre une tâche terminée budgétée à 60 porte
  une marche de −60. » ;
- `WF-IND-0140-A` — « Une survenance qui ne termine ni ne rouvre aucune tâche ne porte aucune
  marche. » ;
- propre à l'US : la marche est rendue par `getEarnedValueCurves`, datée, signée, avec sa cause,
  comme la marche d'un avenant sur la courbe du budget (`steps`) ; son montant est ce que la
  survenance a apporté à la valeur acquise moins ce qu'elle lui a retiré ; la série de valeur
  acquise la porte déjà au point du mois (WF-IND-0110) ;
- propre à l'US : l'indice de délai lu avant et après la survenance diffère de ce que la marche
  apporte à la valeur acquise, la valeur planifiée étant la même ; l'historique des indices le porte
  au même point ;
- propre à l'US : les indicateurs conservés au marquage qui suit la survenance portent la valeur
  acquise avec ce qu'elle a apporté, et la marche ; une lecture `as_of` antérieure à la survenance
  ne les porte pas ;
- propre à l'US : la modification du devis propre d'un risque identifié, sa mise à jour et son
  réexamen laissent identiques la valeur acquise et les indices (WF-RIS-0030, US-3070) ; après une
  saisie dans un devis propre, une mise à jour ou une survenance, aucune entrée périmée du cache des
  indicateurs n'est servie ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** L'exclusion des tâches ajoutées par une survenance est dans la sélection
des lignes d'EP-10, que cette US ne change pas : une tâche abandonnée garde le budgété de ses lignes
et s'acquiert comme toute tâche terminée. La marche est une donnée de la survenance, conservée avec
elle : la conception dit où, et le lot du contrat sa forme. Décision de l'auteur du 2026-11-19 : la
valeur d'une tâche abandonnée est acquise d'un coup, quand le travail de remplacement s'étale
ensuite.

**Hors périmètre.** Le calcul des indicateurs lui-même (EP-10) ; le portefeuille (US-3130) ; l'écran
des indicateurs (US-3140).

---

## US-3130 — Le portefeuille suit : une opportunité dans sa matrice, un coût à la survenance signé dans sa couverture

- **statut** : à faire
- **exigences** : aucune en propre — WF-PTF-0090, dont le texte ne change pas, reste close par EP-11
- **opérations** : `getPortfolioRisks`, `getPortfolioPilotHealth`
- **issue** : #4581

**En tant que** manager, **je veux** que la vue des risques du portefeuille lise la gravité et le
coût à la survenance comme les projets les lisent désormais, **afin que** la matrice, les risques
les plus lourds et la couverture agrégée ne se trompent pas devant une opportunité.

**Critères d'acceptation.**

- propre à l'US : la matrice du portefeuille compte une opportunité une fois, au plus bas niveau de
  gravité, comme celle de son projet (US-3080) ;
- propre à l'US : une opportunité compte pour une provision nulle dans le total des provisions
  identifiées, et ne figure pas devant un risque de provision positive parmi les risques les plus
  lourds ;
- propre à l'US : la couverture agrégée somme les coûts à la survenance signés : une opportunité
  réalisée de −50 dans un projet du périmètre améliore l'écart de couverture agrégé de 50 ;
- propre à l'US : les lectures que le portefeuille conserve au marquage d'une révision portent la
  gravité et le coût à la survenance signés, et se relisent tels quels ;
- propre à l'US : les projets dont un risque n'a pas été réexaminé depuis la date de la santé du
  pilotage sont les mêmes qu'avant : un devis propre en retard n'y entre pas tant que le dernier
  réexamen est dans la période ;
- propre à l'US : ce que `core/portfolio` lit de `core/risks` passe toujours par son interface, dont
  les signatures ne changent pas ;
- propre à l'US : les exemples du portefeuille suivent le témoin (US-3150), et chaque réponse est
  validée contre le contrat dans les tests du service.

**Notes de réalisation.** EP-11 lit les risques par l'interface de `core/risks` (`portfolio_risks`,
`levels_of`, `risk_coverage_of`, `kept_coverage`, `outcomes_between`, `not_reviewed_since`) et y a
ajouté `surveying.py` et `interface/portfolio.py`. Cette US attend EP-11 dans `main`.

**Hors périmètre.** Les vues du portefeuille elles-mêmes (EP-11) ; l'écran, inchangé hors la mention
d'une opportunité (US-3140).

---

## US-3140 — Les écrans des risques : le devis propre sur le projet, sa mise à jour, la survenance, l'opportunité

- **statut** : à faire
- **exigences** : aucune en propre — WF-IHM-0020, dont le texte ne change pas, reste close par EP-08
- **opérations** : celles des US-3070 à US-3130, par le client engendré
- **issue** : #4582

**En tant que** chef de projet, **je veux** préparer un risque dans les grilles du projet, le mettre
à jour et le réexaminer d'un seul geste, lire ce que sa survenance fera avant de la confirmer, et
reconnaître une opportunité au registre, **afin de** mener la revue des risques sur le projet tel
qu'il est.

**Critères d'acceptation.**

- propre à l'US : le devis propre d'un risque s'ouvre dans les grilles de planning et de devis sur
  le projet du jour ; ce qu'il désigne y est présenté ajouté, modifié ou retiré, comme sur un
  avenant, et l'écran nomme le devis propre qu'il lit (WF-IHM-0020) ; à son ouverture, l'écran
  recompose un devis propre élagué, puis le met à jour sans rien demander quand rien n'est à
  signaler ; dans une révision marquée, la grille présente ce qu'il désignait, sous ses tâches
  parentes ;
- propre à l'US : sur un devis propre en retard, l'écran le dit ; à la première saisie, il lit le
  compte rendu de la mise à jour : s'il ne signale rien, il met à jour puis enregistre la saisie
  sans rien demander ; s'il garde une valeur contre le projet, il le présente à confirmer, avec la
  gravité et la provision recalculées ; s'il refuse, il dit ce qui est à corriger dans le devis
  propre (décision de l'auteur du 2026-11-21) ;
- propre à l'US : « Réexaminer » et « Déclarer survenu » enchaînent de même la mise à jour d'un
  devis propre en retard, puis présentent le réexamen, avec la gravité recalculée, ou le compte
  rendu de la survenance ; un réexamen qui écarte le risque ne demande pas de mise à jour ; la revue
  périodique fait de même pour chaque risque ;
- propre à l'US : au marquage d'une révision et à la contractualisation d'un avenant, les devis
  propres en retard dont la mise à jour ne signale rien sont mis à jour sans rien demander, et le
  geste se poursuit ; quand sa tâche échoue pour un devis propre dont la mise à jour garde une
  valeur ou est refusée, l'écran nomme les risques et mène à leurs comptes rendus, à confirmer ou à
  corriger, avant de reprendre le geste ; l'aide en ligne de la revue en dit l'ordre : le projet,
  les risques, le marquage ;
- propre à l'US : le compte rendu d'une survenance présente ce que la survenance ajoute et modifie,
  les tâches qu'elle termine et la valeur acquise qu'elles apportent, les tâches terminées qu'elle
  rouvre, et ce qui la refuse ; les deux signalements d'EP-08 n'y sont plus (#4133, #4134) ;
- propre à l'US : le registre présente une opportunité avec sa gravité négative, une provision nulle
  et la mention « Opportunité » ; la matrice et le nuage de points la placent au plus bas niveau de
  gravité ; les filtres de gravité acceptent une borne négative ;
- propre à l'US : le détail d'un risque survenu présente son coût à la survenance, signé, et en
  regard ce qu'il coûte aujourd'hui ;
- propre à l'US : l'écran des indicateurs présente la marche de la valeur acquise à la date d'une
  survenance, avec sa cause ;
- propre à l'US : le formulaire de déclaration et celui de la provision gardent la tâche de la
  provision, et leur aide en ligne dit qu'elle ne désigne plus que l'endroit où la provision pèse ;
  l'aide en ligne des écrans des risques dit le devis propre préparé sur le projet, sa mise à jour
  et l'opportunité ;
- propre à l'US : aucune réponse n'est écrite à la main : le faux back sert les exemples du contrat,
  le client est engendré ; les parcours de bout en bout des risques sont rejoués contre le service
  ou réécrits, et les écrans passent l'audit d'accessibilité.

**Notes de réalisation.** Les écrans existent (EP-15, EP-17, EP-25, EP-08) : le registre, le détail,
les formulaires, le réexamen, le compte rendu de survenance, et pour un avenant la note de retard et
« Mettre à jour l'avenant » (`amendment-late-note.tsx`, `rebase-amendment-command.tsx`), que le
devis propre reprend. Cette US ne redessine aucun écran : la reprise du graphique à bulles et la
colonne de tendance sont d'US-3160.

**Hors périmètre.** La reprise de l'écran des risques (US-3160) ; les vues du portefeuille (EP-11).

---

## US-3160 — L'écran des risques revu : le graphique à bulles toujours visible, et la tendance de chaque risque

- **statut** : à faire
- **exigences** : `WF-RIS-0040-A`
- **opérations** : `listRisks`, `getRisk`, `getProjectRiskMatrix`, `getPortfolioRisks`,
  `updateMyPreferences`
- **issue** : #4580

**En tant que** chef de projet, **je veux** voir d'emblée le nuage des risques, en bulles dont la
taille dit la gravité, et lire au registre quels risques pèsent plus ou moins qu'à la revue
précédente, **afin de** mener la revue des risques par ce qui a bougé.

**Critères d'acceptation.**

- `WF-RIS-0040-A` — « Les six colonnes sont présentes, ainsi que l'accès aux deux notes et à
  l'historique. » : tenu par EP-08 ; la colonne de tendance s'y ajoute (critères ci-dessous)
  ;
- `WF-RIS-0040-A` — « Le tri par provision classe les risques du plus lourd au plus léger. » : tenu
  par EP-08, non touché ici ;
- `WF-RIS-0040-A` — « Un risque dont la probabilité augmente change de couleur conformément à la
  matrice. » : tenu par EP-08 ; sa bulle prend la couleur de sa zone, et reste ronde ;
- `WF-RIS-0040-A` — « Les trois totaux — identifiés, survenus, écartés — sont distincts, et la
  réserve pour risques de la référence est affichée en regard. » : tenu par EP-08, non touché ici ;
- `WF-RIS-0040-A` — « Un risque identifié dont le produit de la gravité par la probabilité est passé
  de 60 à 75 depuis la révision marquée précédente est présenté en hausse ; passé de 60 à 45, en
  baisse ; resté à 60, stable. » : le service rend la tendance avec le risque, calculée du produit
  signé de son évaluation dans la révision lue et dans la révision marquée qui la précède ; le front
  ne calcule ni ne compare rien (WF-ARC-0020) ;
- `WF-RIS-0040-A` — « Un risque identifié qui ne l'était pas dans la révision marquée précédente est
  présenté comme nouveau ; un risque écarté ou survenu ne présente aucune tendance. » : est nouveau
  le risque déclaré depuis, comme celui qui y était écarté et redevient identifié ; sur un projet
  dont aucune révision n'a été marquée avant celle qui est lue, aucun risque ne présente de tendance
  ni n'est dit nouveau, comme l'écart du reste à engager est alors absent (WF-RAE-0020) ;
- `WF-RIS-0040-A` — « Le registre se filtre et se trie sur la tendance. » : `listRisks` reçoit un
  filtre — en hausse, en baisse, stable, nouveau — et un tri, les risques sans tendance à la place
  que le contrat donne aux valeurs nulles ; les totaux sont ceux des risques retenus (H-01, #1786) ;
- écart : `WF-RIS-0040-A` — « Un risque de gravité négative est présenté comme une opportunité, avec
  une provision nulle, et figure dans la matrice au plus bas niveau de gravité. » : l'opportunité au
  registre et dans la matrice est d'US-3080 ;
- propre à l'US : une opportunité suit la même règle sur son produit signé : passée de −30 à −45,
  elle est en baisse ; sa provision, plafonnée à zéro, n'y entre pas ;
- propre à l'US : la tendance d'une révision marquée est celle qu'elle avait contre la révision
  marquée qui la précède, et ne change plus ; celle de la révision en cours suit la gravité et la
  probabilité enregistrées, donc chaque saisie dans le devis propre, chaque mise à jour et chaque
  réexamen ;
- propre à l'US : la colonne présente une icône du catalogue du front (lucide) : une flèche rouge
  qui monte vers la droite pour une hausse (`TrendingUp`), une flèche verte qui descend pour une
  baisse (`TrendingDown`), le signe égal pour un risque stable (`Equal`), une marque de nouveauté,
  de couleur neutre, pour un risque nouveau (`Sparkles`), et rien sans tendance ; chaque icône porte
  un nom accessible et une infobulle, et se lit sans sa couleur, par sa forme (WF-IHM-0070) ; aucune
  n'a déjà un autre sens dans l'application, où `ArrowUpRight` ouvre une révision, `Star` désigne la
  référence et `Zap` marque ce qui est issu d'un risque ;
- propre à l'US : le graphique à bulles de l'écran des risques d'un projet est toujours dessiné,
  au-dessus de la grille ; la commande de pliage disparaît, et la préférence gardée sous
  `risk_matrix` n'est plus lue ; à 768 de haut, la page défile pour atteindre le bas de la grille
  (décision de l'auteur du 2026-11-21, contre #1252) ;
- propre à l'US : chaque risque identifié est une bulle ronde, de la couleur de sa zone, quelle que
  soit cette zone ; la zone se lit sans sa couleur par son nom, écrit dans sa case, et par le trait
  de ses côtés : une copie d'écran en niveaux de gris laisse lire la zone de chaque bulle
  (WF-IHM-0070 ; décision de l'auteur du 2026-11-21, contre la forme par zone de #1395) ;
- propre à l'US : le diamètre d'une bulle est proportionnel à la gravité du risque en montant,
  rapportée à la plus forte du graphique, sans descendre sous un minimum qui la laisse visible et
  cliquable ; une opportunité est dessinée par la valeur absolue de sa gravité, au plus bas niveau
  (US-3140) ;
- propre à l'US : le graphique des risques du portefeuille, qui partage ce composant, dessine les
  mêmes bulles rondes au même diamètre ;
- propre à l'US : l'infobulle d'une bulle, le clic vers le risque ou vers son projet, l'export en
  image avec sa provenance, la table des décomptes sous le graphique et les axes linéaires aux
  valeurs exactes sont gardés (#1253, #1395) ;
- propre à l'US : le parcours de l'écran trouve les bulles par ce que l'écran nomme — un nom
  accessible, ou la table sous le graphique —, et non par un attribut de leur tracé, que la
  bibliothèque de graphiques change sans prévenir (#4633) ;
- propre à l'US : l'aide en ligne de l'écran dit ce que la taille d'une bulle mesure et ce que la
  tendance compare ; aucune réponse n'est écrite à la main, le faux back servant les exemples du
  contrat ; les parcours de l'écran sont rejoués, et l'écran passe l'audit d'accessibilité.

**Notes de réalisation.** Le graphique est `risk-bubble-chart.tsx`, partagé par l'écran des risques
d'un projet et par celui du portefeuille : la forme par zone (`ZONE_SYMBOL`), la taille
(`bubbleSize`, de 12 à 40 pixels par la racine carrée) et le pliage, que le composant de graphique
tient (`folded`, `onFold`) et que le contrat garde par compte (`ChartPreferences`). La tendance est
peu coûteuse parce que cet EPIC enregistre la gravité avec l'évaluation du risque dans chaque
révision (US-3080) : le registre lit l'évaluation de la révision marquée précédente. Décisions de
l'auteur du 2026-10-23 (#1395) et sur #1252 et #1253, dont cette US reprend deux points.

**Hors périmètre.** Toute autre reprise des écrans des risques ; les vues du portefeuille hors de ce
graphique ; l'évolution d'un risque sur plus de deux révisions, piste d'après le MVP.

---

## US-3150 — Le témoin et les exemples du contrat : les risques de PRJ-001 relus comme des différentiels

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`
- **opérations** : celles des US-3070 à US-3130, lues sur le témoin chargé
- **issue** : #4583

**En tant que** développeur, **je veux** que le témoin chargé dans le service porte les trois
risques de PRJ-001 comme des différentiels, l'un d'eux ajoutant, modifiant et abandonnant, **afin
que** les exemples du contrat soient l'attendu du service et que les écrans s'éprouvent sur un devis
propre complet.

**Critères d'acceptation.**

- `WF-QUA-0040-A` — « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes
  annoncés. » : pour la tranche des risques relus comme des différentiels — le devis propre de 751,
  identifié, ajoute une tâche, modifie la charge d'une ligne existante et abandonne une tâche ; ceux
  de 752 et de 753 n'ajoutent que des tâches ; la survenance de 752, le 20 février, est rejouée par
  la fusion de ce qu'il désigne —, chargée par `waterfall-api load-witness` par les interfaces, avec
  les identifiants et les instants du témoin ; les volumes entiers sont d'EP-13, qui clôt ;
- `WF-QUA-0040-A` — « Deux engendrements successifs donnent des données identifiantes identiques. »
  : deux chargements successifs donnent les mêmes risques, les mêmes désignations et les mêmes nœuds
  fusionnés, identifiants compris ;
- `WF-QUA-0040-A` — « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. » :
  les libellés des risques et de leurs tâches sont ceux du témoin ;
- propre à l'US : le risque 751 garde sa gravité : la réserve de 910 et les montants qui en
  dépendent — devis, reste à engager, couverture, matrice, portefeuille — tiennent ; un montant du
  témoin qui change devant le calcul du service est arbitré par la spécification, et la fixture se
  corrige ;
- propre à l'US : les exemples du contrat, engendrés par `make mock-data`, montrent le devis propre
  de 751 avec un nœud ajouté, un modifié et un retiré ; un devis propre en retard et le compte rendu
  de sa mise à jour, avec une différence gardée, et sa variante refusée ; le compte rendu d'une
  survenance dans sa forme nouvelle ;
- propre à l'US : le registre du témoin porte la tendance de chaque risque de la révision 102 contre
  la 101, et une variante déclarée montre celles que le témoin ne porte pas (US-3160) ;
- propre à l'US : des variantes déclarées montrent ce que le témoin ne charge pas : une survenance
  qui abandonne une tâche, avec sa marche de valeur acquise ; une opportunité au registre et dans la
  matrice ; un coût à la survenance négatif dans la couverture ;
- propre à l'US : sur le témoin chargé, les lectures du service sont comparées aux exemples du
  contrat — le registre, le détail, les réexamens, la matrice, la couverture, les structures, le
  devis propre, les comptes rendus de mise à jour et de survenance, les courbes ;
- propre à l'US : le chargeur met à jour les devis propres avant chaque marquage et chaque fusion de
  la chronologie du témoin, par la fonction de la mise à jour, sans compte rendu, comme il le fait
  d'un avenant avant sa fusion ;
- propre à l'US : la migration de cet EPIC refuse de s'appliquer, en le disant, sur une base qui
  porte un devis propre saisi sous EP-08 (décision de l'auteur du 2026-11-21) ; sur une base sans
  risque, elle aboutit ;
- propre à l'US : le parcours de bout en bout de la définition de fini est joué contre le service,
  et la liste des parcours non rejoués du guide est mise à jour.

**Notes de réalisation.** Les quatre règles du jeu de données de référence (README de la roadmap) :
le saisi se charge par les interfaces, le calculé devient l'attendu, et le calcul du faux back
(`wftools.mockwitnessrisks`) n'est jamais réemployé par le service. EP-08 charge les devis propres
comme des structures autonomes et rejoue la survenance de 752 par la greffe (`load_occurrence`),
sous des identifiants imposés. `docs/api/DECISIONS.md`, « L'univers témoin », « Révisions et risques
».

**Hors périmètre.** Les trois cents projets et les volumes du §4.6.2 (EP-13) ; les exemples du
portefeuille hors des risques (EP-11).

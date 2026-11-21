---
id: EP-30
titre: Un risque se prépare comme un différentiel — il ajoute, reprend ou abandonne du travail, et sa survenance fusionne sans déplacer la référence
statut: à planifier
depend_de: EP-08, EP-11
famille: front, back
issue:
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
  grille d'un devis propre montre le projet du jour et ce que le risque y désigne ;
- la mise à jour d'un devis propre depuis la structure principale, son compte rendu, et ce qui
  l'exige : la saisie dans le devis propre, le réexamen, la survenance ;
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
- les écrans des risques ;
- sa tranche du jeu de données de référence (WF-QUA-0040) — les trois risques de PRJ-001 relus comme
  des différentiels, le 751 ajoutant, modifiant et abandonnant —, rechargée par `waterfall-api
  load-witness`, et les exemples du contrat qui suivent ;
- le constat reçu, soldé.

## Ce qui n'en fait pas partie

- la base d'un différentiel d'avenant et sa mise à jour depuis la structure principale — EP-08
  (#4034, #4132), dont cet EPIC réutilise les règles et les deux opérations ;
- l'avenant, sa fusion et le déplacement de la référence — EP-08 ; la fusion d'un avenant ne lit ni
  n'écrit aucun devis propre ;
- la reprise des devis propres saisis sous EP-08 : aucune base à conserver n'en porte, et la
  migration refuse de s'appliquer si elle en trouve un (décision de l'auteur du 2026-11-21) ;
- les vues du portefeuille — EP-11 ; ici, ce que la gravité signée change à leurs lectures des
  risques ;
- le calcul des indicateurs — EP-10 ; ici, la valeur acquise devant une tâche qu'une survenance
  termine ou rouvre, et sa marque ;
- une marque, dans la structure principale, sur les lignes qu'un risque survenu a modifiées et les
  tâches qu'il a abandonnées : seuls les ajouts la portent.

## Exigences réalisées

La spécification 1.0.8 décrit encore le devis propre greffé d'EP-08. Décisions de l'auteur du
2026-11-21, à ce cadrage : les exigences dont la règle change sont réécrites sous leur identifiant,
et cet EPIC les clôt à la place d'EP-08, dont les lignes passent « début — close en EP-30 » ; ce qui
est purement neuf prend des exigences courtes nouvelles ; le cadrage se fait sur un texte de Vérif
proposé, que les US citent en critères propres, et la spécification 1.0.9 est écrite et acceptée
avant l'ouverture des issues des lots — les US citent alors les Vérif réels.

Six exigences changent de règle et sont closes ici : WF-RIS-0010 (la gravité, écart net, et le coût
à la survenance), WF-RIS-0030 (le devis propre), WF-RIS-0040 (l'opportunité au registre et dans la
matrice), WF-RIS-0050 (le coût à la survenance signé, et ce qui se lit en regard), WF-RIS-0060 (la
survenance) et WF-IND-0030 (la valeur acquise d'une tâche qu'une survenance termine). Trois
exigences nouvelles sont proposées, et entreront à ce tableau, entières, quand la 1.0.9 les aura
écrites : « Mise à jour du devis propre d'un risque » (WF-RIS-0070), « Gravité d'un risque »
(WF-RIS-0080) et « Marque d'une survenance sur les courbes de valeur acquise » (WF-IND-0140).
WF-RIS-0020 et WF-REV-0110, dont aucune phrase de Vérif ne change, et WF-REV-0100, dont seul le
corps est retouché, restent closes par EP-08 ; WF-PTF-0090 et WF-IND-0110, dont le texte ne change
pas, par les EPIC qui les ont réalisées. WF-QUA-0040 entre au tableau en portée « début » : cet EPIC
recharge sa tranche du jeu de données de référence, qu'EP-13 clôt.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-RIS-0010-A` | Attributs d’un risque | fin — amorcée en EP-15, EP-08 | US-3080 |
| `WF-RIS-0030-A` | Devis propre d’un risque | fin — amorcée en EP-15, EP-08 | US-3070 |
| `WF-RIS-0040-A` | Grille de suivi des risques | fin — amorcée en EP-15, EP-17, EP-08 | US-3080 |
| `WF-RIS-0050-A` | Réserve pour risques et couverture | fin — amorcée en EP-17, EP-08 | US-3110 |
| `WF-RIS-0060-A` | Survenance d’un risque | fin — amorcée en EP-17, EP-08 | US-3100 |
| `WF-IND-0030-A` | Valeur acquise | fin — amorcée en EP-10, EP-08 | US-3120 |
| `WF-QUA-0040-A` | Jeu de données de référence | début — close en EP-13, amorcée aussi en EP-05, EP-04, EP-06, EP-07, EP-09, EP-10, EP-08, EP-11 | US-3150 |

## Opérations du contrat

Le contrat, figé (`docs/api/DECISIONS.md`, « La règle d'après le gel »), change : chaque
modification passe par une issue « contrat » que l'auteur tranche, et s'écrit par un lot avant le
code qui la consomme. La conception en dira le détail ; ce que les US demandent :

- la mise à jour d'un différentiel, étendue au devis propre d'un risque : `getStructureRebaseReport`
  et `rebaseCostStructure` l'acceptent, sous la permission de la saisie des risques ;
  `CostStructure` dit un devis propre à jour ou en retard, et liste sa commande de mise à jour ;
- un refus de plus, sur un devis propre en retard, pour les écritures de l'arbre et les imports sur
  un devis propre, pour `reviewRisk`, `getRiskOccurrenceReport` et `declareRiskOccurrence` ;
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
- les exemples, engendrés par `make mock-data`.

Servies par EP-08 ou par EP-11, et reprises ici pour ce que cet EPIC y change :

- `risks` : `createRisk`, `getRisk`, `listRisks`, `listRiskReviews`, `reviewRisk`,
  `updateRiskProvision`, `getRiskOccurrenceReport`, `declareRiskOccurrence`,
  `getProjectRiskCoverage`, `getProjectRiskMatrix` ;
- `revisions` : `listCostStructures`, `getStructureRebaseReport`, `rebaseCostStructure`,
  `createRevision`, `abandonRevision`, `compareRevisions`, `listNodes` et les écritures de l'arbre
  sur un devis propre, `undoLastChange`, `redoLastUndo` ;
- `exchanges` : `openImport`, `applyImport`, sur un devis propre ;
- `analysis` : `getRemainingIndicators`, `getProjectIndicators`, `getEarnedValueCurves` ;
- `portfolio` : `getPortfolioRisks`.

## Préalables

EP-08 et EP-11 livrés : `epic/EP-30` se tire de `main`, au premier lot, une fois les deux fusionnés
(décision de l'auteur du 2026-11-21). C'est la règle du README : EP-11 modifie le même module des
risques (`core/risks`), et deux EPIC ne le touchent pas en même temps. EP-30 trouve alors dans
`main` ce qu'il réutilise d'EP-08 — ce qu'une structure désigne par rapport à sa base, la mise à
jour d'un différentiel et son compte rendu, la fusion — et les lectures du portefeuille qu'il fait
suivre.

La spécification 1.0.9, écrite par son auteur et acceptée avant l'ouverture des issues des lots :
elle redit les six exigences du tableau et écrit les trois nouvelles, d'après le texte que ce
cadrage propose (issues de spécification, ouvertes à la validation des US). Les critères « propre à
l'US, texte proposé » deviennent alors des citations de Vérif.

## Définition de fini

- les exemples chiffrés des Vérif que la spécification 1.0.9 écrit pour WF-RIS-0010, WF-RIS-0030,
  WF-RIS-0040, WF-RIS-0050, WF-RIS-0060 et WF-IND-0030, et pour les trois exigences nouvelles, sont
  des tests qui passent (WF-QUA-0020) ;
- sur un projet de mille tâches et cinq mille lignes, un risque déclaré n'ajoute à la révision que
  ce que son devis propre désigne, et la révision suivante n'en reprend pas davantage ;
- un devis propre préparé avant que la structure principale ne reçoive une tâche, une réestimation,
  la fusion d'un avenant et la survenance d'un autre risque, puis mis à jour, réexaminé et déclaré
  survenu, laisse dans la structure principale tout ce qu'elle a reçu entre-temps, et y applique ce
  qu'il désigne ;
- le parcours de bout en bout, contre le service réel, déclare un risque, y ajoute une tâche, y
  modifie une ligne et y abandonne une tâche, met son devis propre à jour après une saisie du
  projet, le réexamine et le déclare survenu ;
- le témoin chargé porte ses trois risques relus comme des différentiels, et ses lectures sont
  comparées aux exemples du contrat ;
- `make requirements` ne laisse sans test du back aucune des exigences que cet EPIC clôt ;
- les mesures existantes, `make measure-core` et `make measure`, rejouées sur le témoin chargé,
  tiennent leurs objectifs et ne se dégradent pas de plus d'un quart (WF-QUA-0060) ; l'ouverture de
  la grille d'un devis propre sur le projet de mille tâches y est relevée, contre l'objectif que la
  conception arrête.

## Constats reçus

- #4400 — back : la gravité d'un risque survenu se lit à son coût à la survenance dans les révisions
  suivantes (WF-RIS-0010, spécification 1.0.8). Rangé en EP-35 par la ventilation du 2026-11-21, et
  repris ici au cadrage du même jour (décision de l'auteur, contre « EP-30 ne prend pas d'autres
  restes ») : cet EPIC clôt WF-RIS-0010 et réécrit la lecture de la gravité. Corrigé par US-3080.

Trois constats d'EP-08 sont tranchés au plus léger parce que cet EPIC rend leur règle provisoire
(décisions de l'auteur du 2026-11-19 et du 2026-11-20) : #4133, les dates du devis propre le jour de
la survenance, que le compte rendu signale sans que la survenance redate ; #4134, les tâches en aval
que la greffe déplace, nommées au compte rendu sans champ nouveau ; #4240, la greffe sous une tâche
terminée, qui la rouvre, signalée sans refuser. Le devis propre préparé comme un différentiel porte
le planning entier : ses tâches se datent par leurs liaisons avec celles du projet, et le retard se
lit dans sa grille. US-3100 retire les deux premiers signalements et garde le troisième, étendu à
toute tâche terminée que la survenance rouvre.

## Conception

À écrire à l'étape suivante du cadrage, après la validation des US. Ce qui suit est décidé avant
elle et s'impose à elle.

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
  risque, contre la décision du 2026-11-19.
- **Un devis propre est en retard** dès que la structure principale a changé depuis sa dernière mise
  à jour : une branche que personne n'a encore rejouée sur la tête. Sa gravité et sa provision
  datent d'avant, et ce qu'il désigne n'a pas été confronté au projet. La mise à jour recalcule la
  gravité sur le projet du jour et présente ce qui ne s'y rattache plus.
- **« Réexaminer » est un geste, et deux opérations.** L'écran présente le compte rendu de la mise à
  jour, puis confirme la mise à jour et le réexamen. Au contrat, la mise à jour garde les deux
  opérations d'EP-08, étendues au devis propre, et `reviewRisk` est refusé tant que le devis propre
  d'un risque qui reste ou redevient identifié est en retard. L'annulation d'un réexamen rend ainsi
  exactement la probabilité, l'état et la provision d'avant (WF-IHM-0110). Écartés : `reviewRisk`
  qui ferait lui-même la mise à jour, dont l'annulation ne rendrait pas la gravité d'avant ; un
  réexamen libre, contre « à chaque revue, ce que la structure principale a reçu est reporté ».
- **La saisie dans un devis propre en retard attend la mise à jour**, et l'écran présente toujours
  son compte rendu à confirmer, même vide. Écartés : la mise à jour faite sans rien demander quand
  elle ne signale rien ; la saisie libre, qui vaudrait mise à jour sans compte rendu.
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
- **La fusion d'un avenant ne fait rien d'un devis propre.** Elle n'en lit ni n'en écrit aucun ;
  comme après toute écriture de la structure principale, les devis propres sont en retard, et la
  mise à jour de chacun applique les règles de WF-REV-0110 et nomme ce qu'elle garde. Écarté : un
  compte rendu de fusion qui nommerait les risques dont le devis propre désigne ce que l'avenant
  désigne, un champ de plus au contrat d'EP-08.
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

### Ce qui reste à la conception

- la forme de ce que le devis propre conserve, comment sa grille se recompose à chaque lecture, et
  comment les écritures de l'arbre s'y appliquent ;
- le calcul de la gravité sur la structure recomposée, et ce qu'il coûte à chaque saisie ;
- ce que la mise à jour écrit, et la forme de son compte rendu pour un devis propre ;
- ce que le devis propre d'un risque survenu garde dans la révision où il est survenu ;
- les tables — la gravité enregistrée, la part figée d'un risque survenu, les contraintes de signe —
  et la migration qui refuse un devis propre d'EP-08 ;
- les modifications du contrat, issue par issue, et la forme de la marche sur les courbes de valeur
  acquise ;
- l'objectif de l'ouverture de la grille d'un devis propre ;
- l'ordre de construction.

---

## US-3070 — Le devis propre d'un risque, préparé comme un différentiel de la structure principale

- **statut** : à faire
- **exigences** : `WF-RIS-0030-A`
- **opérations** : `createRisk`, `listCostStructures`, `createRevision`, `abandonRevision` ; sur le
  devis propre, `listNodes` et les écritures de l'arbre (`createNode`, `updateTaskFacet`,
  `updateEstimateLine`, `setPredecessors`, `moveNodes`, `deleteNode`, `previewPaste`, `applyPaste`),
  `openImport`, `applyImport`, `undoLastChange`, `redoLastUndo`
- **issue** :

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
- propre à l'US, texte proposé pour WF-RIS-0030 : « La grille d'un devis propre qui vient d'être
  créé présente les tâches et les lignes de la structure principale, aucune n'étant présentée
  ajoutée, modifiée ou retirée. » : `createRisk` crée un devis propre qui ne désigne rien ;
  `listNodes` y rend les nœuds de la structure principale de la révision, tous `unchanged` ;
- propre à l'US, texte proposé pour WF-RIS-0030 : « Dans le devis propre d'un risque, une tâche
  ajoutée après une tâche du projet, une ligne existante portée de 100 à 130 heures et une tâche
  existante abandonnée sont présentées ajoutée, modifiée et retirée ; la structure principale est
  inchangée. » : `listNodes` les rend `added`, `modified` — la valeur de la structure principale en
  regard — et `removed` (`NodeDifference`) ; aucune lecture de la structure principale ne change, ni
  son compteur ;
- propre à l'US, texte proposé pour WF-RIS-0030 : « Une tâche ajoutée à la structure principale
  figure, sans y être désignée, dans la grille du devis propre d'un risque ouverte ensuite. » : à
  chaque lecture, la grille présente la structure principale telle qu'elle est, avec ce que le devis
  propre désigne (décision de l'auteur du 2026-11-21 : le projet du jour) ; les dates et les
  montants qu'elle présente sont ceux que le moteur de dates et le chiffrage donnent à cet ensemble
  ;
- propre à l'US : le devis propre ne conserve que ce qu'il désigne — les tâches, les liaisons et les
  lignes qu'il ajoute, les valeurs qu'il modifie, ce qu'il abandonne. Sur un projet de mille tâches
  et cinq mille lignes, un risque dont le devis propre ajoute deux tâches et modifie une ligne
  n'ajoute à la révision que ce que ces désignations demandent, et `createRevision` n'en reprend pas
  davantage (décision de l'auteur du 2026-11-19) ; la forme conservée est à la conception ;
- propre à l'US : chaque révision fige une version du devis propre : une révision marquée le rend
  tel qu'il était à son marquage, sur sa propre structure principale ; `createRevision` le reprend,
  et `abandonRevision` ramène celui de la dernière révision marquée (WF-RIS-0020, WF-REV-0100) ;
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
  gravité et la provision dans la même écriture (US-3080) ; sur un devis propre en retard, elle est
  refusée (US-3090) ;
- propre à l'US : l'import d'un planning ou d'un devis sur le devis propre (`structure_id`) s'y
  applique comme sur un différentiel : ce que le fichier ajoute, change ou ne porte plus devient ce
  que le devis propre désigne, et la structure principale est inchangée ; le même fichier appliqué
  sur la structure principale laisse inchangé ce que le devis propre désigne, et le met en retard
  (WF-INTF-0090) ;
- propre à l'US : chaque réponse est validée contre le contrat dans les tests du service.

**Notes de réalisation.** EP-08 lit déjà un différentiel contre sa base (`compare_differential`,
US-2550/L3 puis US-3050/L2) et calcule ce qu'une structure désigne (`designated`, US-3050/L3) sans
nommer la nature « avenant » : ce sont les deux calculs que cette US reprend, la structure
principale du jour tenant lieu de base. Ce qui change est ce que la révision conserve, et ce que la
conception arrête : la forme de ce que le devis propre désigne, la recomposition à la lecture,
l'application des écritures. Le devis propre d'EP-08, structure autonome qui tient seule ses lignées
(`holds_its_lineages`), disparaît.

**Hors périmètre.** La gravité et la provision (US-3080) ; la mise à jour et ses refus (US-3090) ;
la survenance (US-3100) ; les écrans (US-3140) ; le témoin (US-3150).

---

## US-3080 — La gravité d'un risque, écart net, la provision qui en est tirée, et l'opportunité

- **statut** : à faire
- **exigences** : `WF-RIS-0010-A`, `WF-RIS-0040-A`
- **opérations** : `getRisk`, `listRisks`, `listRiskReviews`, `getProjectRiskMatrix`, `createRisk`,
  `reviewRisk`, `updateRiskProvision`, `listNodes` (la ligne de provision), `getEstimateIndicators`,
  `getRemainingIndicators`
- **issue** :

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
- propre à l'US, texte proposé pour l'exigence nouvelle « Gravité d'un risque » (WF-RIS-0080) : « Un
  devis propre qui ajoute deux lignes de 120 et 80 donne une gravité de 200. » ;
- propre à l'US, texte proposé pour WF-RIS-0080 : « Un devis propre qui ajoute une ligne de 300 et
  abandonne une tâche dont les lignes totalisent 100 donne une gravité de 200. » ;
- propre à l'US, texte proposé pour WF-RIS-0080 : « Un devis propre qui porte de 100 à 130 le
  montant réestimé d'une ligne existante donne une gravité de 30. » ;
- propre à l'US, texte proposé pour WF-RIS-0080 : « Sur un projet au taux d'inflation de 3 %, un
  devis propre dont une tâche ajoutée repousse de l'année de référence à la suivante la consommation
  d'une ligne de 1 000 compte 30 dans la gravité. » : la gravité est calculée sur les dates que le
  moteur donne à la structure principale portant ce que le devis propre désigne, tâches en aval
  comprises (WF-DEV-0030) ;
- propre à l'US, texte proposé pour WF-RIS-0080 : « Un devis propre qui n'abandonne qu'une tâche de
  100 donne une gravité de −100 : le registre présente le risque comme une opportunité, sa provision
  est nulle, et le total du devis est celui du projet sans lui. » ;
- propre à l'US, texte proposé pour WF-RIS-0080 : « Une réestimation dans la structure principale ne
  change ni la gravité ni la provision d'un risque avant la mise à jour de son devis propre. » ;
- propre à l'US, texte proposé pour WF-RIS-0010 : « Un risque de gravité 200 à 30 % porte une
  provision de 60 ; un risque de gravité −100 à 30 %, une provision nulle. » : la provision est la
  gravité pondérée par la probabilité, au centime, sans descendre sous zéro ; la ligne de provision
  d'une opportunité reste, à montant nul ;
- propre à l'US, texte proposé pour WF-RIS-0040 : « Un risque de gravité négative est présenté comme
  une opportunité, avec une provision nulle, et figure dans la matrice au plus bas niveau de
  gravité. » : `matrix_cell` et `getProjectRiskMatrix` la classent au premier niveau de gravité, sa
  part de l'assiette étant sous la première borne (WF-REF-0160), et la comptent dans sa case ;
- propre à l'US : la gravité est l'écart net des montants réestimés, lignes de provision exclues :
  le total de la structure principale portant ce que le devis propre désigne, moins son total sans
  lui ; elle compte les lignes ajoutées, l'écart des lignes modifiées, les lignes des tâches
  abandonnées en moins, et ce que le glissement des tâches en aval change à leur montant ; elle est
  nulle tant que le devis propre ne désigne rien ;
- propre à l'US : la gravité est enregistrée avec l'évaluation du risque dans la révision :
  `Risk.severity` et `RiskReview.severity` la rendent signée, `computed_fields` dit ce dont elle
  dépend, et une révision marquée rend celle qu'elle a figée ;
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

## US-3090 — La mise à jour d'un devis propre, et ce qui l'exige : la saisie, le réexamen, la survenance

- **statut** : à faire
- **exigences** : aucune que la spécification 1.0.8 porte — l'exigence nouvelle « Mise à jour du
  devis propre d'un risque » (WF-RIS-0070), proposée ; les règles de la mise à jour d'un
  différentiel (WF-REV-0110) et le réexamen (WF-RIS-0020), dont le texte ne change pas, restent
  closes par EP-08
- **opérations** : `getStructureRebaseReport`, `rebaseCostStructure` (étendues au devis propre),
  `listCostStructures`, `reviewRisk`, les écritures de l'arbre et `applyImport` sur un devis propre,
  `getRiskOccurrenceReport`, `declareRiskOccurrence` (leur refus), `getRisk`, `listRisks` (les
  commandes)
- **issue** :

**En tant que** chef de projet, **je veux**, à chaque revue, confronter ce que chaque risque désigne
au projet tel qu'il est devenu, lire ce qui ne s'y rattache plus et voir sa gravité recalculée avant
de confirmer sa probabilité, **afin que** le registre ne garde pas la gravité d'un projet qui
n'existe plus.

**Critères d'acceptation.**

- propre à l'US, texte proposé pour l'exigence nouvelle « Mise à jour du devis propre d'un risque »
  (WF-RIS-0070) : « Après une réestimation dans la structure principale, le devis propre d'un risque
  identifié est en retard ; sa gravité et sa provision sont inchangées, et sa grille présente la
  réestimation. » : `CostStructure` dit un devis propre à jour à la déclaration du risque et après
  sa mise à jour, en retard dès qu'une écriture avance le compteur de la structure principale,
  qu'elle touche ou non ce qu'il désigne ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « Sur un devis propre en retard, une saisie, la
  confirmation du risque et la déclaration de sa survenance sont refusées et nomment la condition ;
  après la mise à jour, elles aboutissent. » : les écritures de l'arbre et l'application d'un import
  sur le devis propre, `reviewRisk`, `getRiskOccurrenceReport` et `declareRiskOccurrence` répondent
  409 `STATE_FORBIDS_OPERATION`, par une condition que le lot du contrat nomme ; rien n'est écrit ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « La mise à jour d'un devis propre dont une tâche
  ajoutée suit une tâche que le projet a repoussée d'un an recalcule sa gravité sur les dates
  nouvelles, et sa provision la suit. » : `rebaseCostStructure` enregistre la gravité calculée sur
  le projet du jour, et la ligne de provision en prend le montant dans la même écriture ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « Une ligne que le devis propre porte à 130 heures
  et que le projet a réestimée à 110 garde 130 après la mise à jour, et le compte rendu la nomme. »
  : une différence `kept`, ses champs nommés (règle 1 de WF-REV-0110) ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « Une tâche que le devis propre modifie et que le
  projet a supprimée y figure, après la mise à jour, comme une tâche ajoutée, et le compte rendu la
  nomme. » : règle 2 de WF-REV-0110 ; une tâche ou une ligne qu'il ajoute sous une tâche que le
  projet n'a plus passe sous l'ancêtre le plus proche qui reste, et une liaison qu'il ajoute vers
  une tâche que le projet n'a plus est retirée, l'une et l'autre nommées (règles 3 et 4) ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « Un risque dont le devis propre est en retard est
  écarté sans mise à jour ; son retour à l'état identifié l'exige. » : `reviewRisk` qui écarte n'est
  pas refusé ; celui qui laisse ou rend le risque identifié l'est tant que le devis propre est en
  retard ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « Lorsque deux risques modifient la même ligne et
  que l'un survient, la mise à jour de l'autre garde la valeur qu'il désigne et la nomme. » ;
- propre à l'US, texte proposé pour WF-RIS-0070 : « Une mise à jour qui laisserait une boucle de
  liaisons dans le devis propre est refusée et nomme le motif. » : comme une liaison interdite, une
  date au-delà de l'horizon ou une tâche sans heure travaillée, le motif et la tâche nommés au
  compte rendu (`ReportRefusal`), rien n'étant écrit ; le lien fautif retiré du devis propre, elle
  aboutit ;
- propre à l'US : `getStructureRebaseReport` sur un devis propre est une lecture qui n'écrit rien :
  ce que le devis propre garde contre le projet (`kept`), les motifs qui refusent la mise à jour, la
  gravité et la provision qu'elle enregistrerait, et les compteurs lus de la structure principale et
  du risque ; il ne présente rien de ce que la structure principale a reçu, que la grille montre
  déjà ;
- propre à l'US : `rebaseCostStructure` sur un devis propre, avec les compteurs lus, écrit ce que le
  compte rendu a présenté ; le devis propre est à jour, et la structure principale n'est écrite que
  par la ligne de provision ; un compteur changé depuis la lecture, 412 `STALE_LOCK_VERSION`, rien
  n'est écrit ;
- propre à l'US : la mise à jour d'un devis propre est une saisie des risques, sous leur permission
  d'écriture, et non sous celle de l'ouverture d'un différentiel ; elle est offerte sur le devis
  propre d'un risque identifié ou écarté de la révision en cours, et refusée par 409 sur celui d'un
  risque survenu, sur une révision marquée, pendant un traitement de fond et sur un devis propre à
  jour, la première condition qui manque nommée dans l'ordre du contrat ;
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
part, sans nommer la nature du différentiel. Un devis propre n'a pas de base conservée : ce que sa
mise à jour compare, et ce qu'elle écrit, est à la conception. Le réexamen lui-même (`reviewRisk`)
ne change que par son refus.

**Hors périmètre.** Le calcul de la gravité (US-3080) ; la survenance (US-3100) ; l'écran qui
enchaîne la mise à jour et le réexamen (US-3140).

---

## US-3100 — La survenance fusionne ce que le devis propre désigne

- **statut** : à faire
- **exigences** : `WF-RIS-0060-A`
- **opérations** : `getRiskOccurrenceReport`, `declareRiskOccurrence`, `getBackgroundTask`,
  `listNodes` et `compareRevisions` (`is_from_risk`, `origin_risk_ids`), `getRisk`
- **issue** :

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
- écart : `WF-RIS-0060-A` — « Les tâches fusionnées se trouvent sous la tâche qui portait la
  provision, aux dates qu'elles avaient dans le devis propre ; le total du lot dont cette tâche
  relève augmente de leur montant, moins la provision retirée ; une tâche feuille fusionnée qui
  n'avait pas de prédécesseur est en mode manuel. » : la règle de la greffe, que cet EPIC remplace
  (décision de l'auteur du 2026-11-19) : les tâches ajoutées se trouvent où le devis propre les
  place ; la spécification 1.0.9 réécrit la phrase, et le critère propre ci-dessous la porte d'ici
  là ;
- écart : `WF-RIS-0060-A` — « La survenance d'un risque dont la provision était portée par un jalon
  place ses tâches après ce jalon, qui reste un jalon sans sous-tâche. » : sans objet, la tâche qui
  porte la provision ne recevant plus rien ; la spécification 1.0.9 retire la phrase ;
- `WF-RIS-0060-A` — « Une ligne fusionnée par la survenance d'un risque est encore désignée comme
  issue de ce risque dans la révision suivante, et après son déplacement sous une autre tâche ; une
  ligne ajoutée ensuite sous une tâche issue du risque ne l'est pas. » : tenu par EP-08 ;
  `origin_risk_id` est posé sur les tâches et les lignes que la survenance ajoute, et sur elles
  seules (décision de l'auteur du 2026-11-21) ;
- `WF-RIS-0060-A` — « Les grilles de planning et de devis se filtrent sur les tâches et les lignes
  issues d'un risque, ou d'un risque donné (WF-IHM-0130). » : tenu par EP-08 ; `is_from_risk` et
  `origin_risk_ids` rendent les ajouts d'une survenance, non ce qu'elle a modifié ou terminé ;
- propre à l'US, texte proposé pour WF-RIS-0060 : « Les tâches ajoutées se trouvent à la place, avec
  les liaisons et aux dates que le devis propre leur donnait ; la tâche qui portait la provision ne
  reçoit aucune tâche. » ;
- propre à l'US, texte proposé pour WF-RIS-0060 : « Après la survenance d'un risque qui porte de 100
  à 130 le montant réestimé d'une ligne budgétée à 100, la ligne porte un montant budgété de 100 et
  un montant réestimé de 130 ; elle n'est pas désignée comme issue de ce risque. » : la ligne garde
  ses grandeurs de référence et prend pour grandeurs courantes celles que le devis propre désigne ;
- propre à l'US, texte proposé pour WF-RIS-0060 : « Une tâche non démarrée budgétée à 100 que le
  risque abandonne est conservée, terminée le jour de la survenance, son reste à engager est nul, et
  le montant budgété de ses lignes est inchangé. » : il en va de même d'une tâche démarrée ; c'est
  la règle qu'un avenant applique à une tâche démarrée qu'il retire (WF-REV-0050) ;
- propre à l'US, texte proposé pour WF-RIS-0060 : « Le compte rendu d'une survenance qui abandonne
  une tâche budgétée à 100 nomme cette tâche comme terminée et annonce une valeur acquise de 100 ;
  l'abandon à cette étape laisse la révision en cours inchangée. » ;
- propre à l'US, texte proposé pour WF-RIS-0060 : « La survenance d'un risque qui modifie une ligne
  d'une tâche terminée rouvre cette tâche, et le compte rendu le signale sans refuser. » : il en va
  de même d'une tâche ajoutée sous une récapitulative terminée ; le signalement est celui qu'EP-08 a
  écrit pour une greffe sous une tâche terminée (#4240), étendu à toute tâche que la survenance
  rouvre, avec la valeur acquise qu'elle retire ;
- propre à l'US, texte proposé pour WF-RIS-0060 : « Une tâche ajoutée à la structure principale
  après la préparation du devis propre, que celui-ci ne désigne pas, figure toujours dans la
  structure principale après la survenance. » ;
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
- **issue** :

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
- propre à l'US, texte proposé pour WF-RIS-0050 : « Un risque survenu qui abandonne une tâche de 100
  et ajoute une ligne de 300 a un coût à la survenance de 200. » ;
- propre à l'US, texte proposé pour WF-RIS-0050 : « Un risque survenu à 250, dont 150 de lignes
  ajoutées et 100 de lignes modifiées, présente 250 en regard de 250 ; la réestimation à 200 des
  lignes ajoutées présente 300, et celle des lignes modifiées ne change pas ce montant. » : la part
  du risque dans ce qu'il a modifié et abandonné est figée à la survenance, et le réestimé présenté
  en regard ne suit que les lignes qu'il a ajoutées (décision de l'auteur du 2026-11-19) ;
- propre à l'US, texte proposé pour WF-RIS-0050 : « Sur un projet de réserve 60 dont un risque est
  survenu à 250, la survenance d'une opportunité de −50 porte le coût des survenus à 200 et l'écart
  de couverture de −190 à −140. » : le coût à la survenance est signé, et la couverture le compte
  tel quel (décision de l'auteur du 2026-11-21) ;
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
- **exigences** : `WF-IND-0030-A`
- **opérations** : `getProjectIndicators`, `getEarnedValueCurves`, `getIndexHistory`, `markRevision`
  (la conservation), `declareRiskOccurrence`
- **issue** :

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
- propre à l'US, texte proposé pour WF-IND-0030 : « Une tâche budgétée à 100 qu'un risque survenu
  abandonne contribue pour 100 à la valeur acquise à la date de la survenance. » ;
- propre à l'US, texte proposé pour l'exigence nouvelle « Marque d'une survenance sur les courbes de
  valeur acquise » (WF-IND-0140) : « Après la survenance, le 20 du mois, d'un risque qui abandonne
  une tâche budgétée à 100, la courbe de valeur acquise porte au point de ce mois une marche de 100,
  datée du 20 et attribuée à la survenance. » ;
- propre à l'US, texte proposé pour WF-IND-0140 : « La survenance d'un risque qui rouvre une tâche
  terminée budgétée à 60 porte une marche de −60. » ;
- propre à l'US, texte proposé pour WF-IND-0140 : « Une survenance qui ne termine ni ne rouvre
  aucune tâche ne porte aucune marche. » ;
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
- **issue** :

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
- **issue** :

**En tant que** chef de projet, **je veux** préparer un risque dans les grilles du projet, le mettre
à jour et le réexaminer d'un seul geste, lire ce que sa survenance fera avant de la confirmer, et
reconnaître une opportunité au registre, **afin de** mener la revue des risques sur le projet tel
qu'il est.

**Critères d'acceptation.**

- propre à l'US : le devis propre d'un risque s'ouvre dans les grilles de planning et de devis sur
  le projet du jour ; ce qu'il désigne y est présenté ajouté, modifié ou retiré, comme sur un
  avenant, et l'écran nomme le devis propre qu'il lit (WF-IHM-0020) ;
- propre à l'US : sur un devis propre en retard, l'écran le dit ; à la première saisie, il présente
  le compte rendu de la mise à jour — ce que le devis propre garde, ce qui la refuse, la gravité et
  la provision recalculées — à confirmer, toujours, même quand il ne signale rien, puis enregistre
  la saisie (décision de l'auteur du 2026-11-21) ;
- propre à l'US : « Réexaminer » présente d'abord ce même compte rendu, puis confirme la mise à jour
  et le réexamen ; un réexamen qui écarte le risque ne le présente pas ; la revue périodique
  enchaîne de même pour chaque risque ;
- propre à l'US : « Déclarer survenu » n'est offert que sur un devis propre à jour ; son compte
  rendu présente ce que la survenance ajoute et modifie, les tâches qu'elle termine et la valeur
  acquise qu'elles apportent, les tâches terminées qu'elle rouvre, et ce qui la refuse ; les deux
  signalements d'EP-08 n'y sont plus (#4133, #4134) ;
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
devis propre reprend. Cette US ne redessine aucun écran.

**Hors périmètre.** La refonte d'un écran ; les vues du portefeuille (EP-11).

---

## US-3150 — Le témoin et les exemples du contrat : les risques de PRJ-001 relus comme des différentiels

- **statut** : à faire
- **exigences** : `WF-QUA-0040-A`
- **opérations** : celles des US-3070 à US-3130, lues sur le témoin chargé
- **issue** :

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
- propre à l'US : des variantes déclarées montrent ce que le témoin ne charge pas : une survenance
  qui abandonne une tâche, avec sa marche de valeur acquise ; une opportunité au registre et dans la
  matrice ; un coût à la survenance négatif dans la couverture ;
- propre à l'US : sur le témoin chargé, les lectures du service sont comparées aux exemples du
  contrat — le registre, le détail, les réexamens, la matrice, la couverture, les structures, le
  devis propre, les comptes rendus de mise à jour et de survenance, les courbes ;
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

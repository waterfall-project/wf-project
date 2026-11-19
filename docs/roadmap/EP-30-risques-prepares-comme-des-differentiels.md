---
id: EP-30
titre: Un risque se prépare comme un différentiel — il ajoute, reprend ou abandonne du travail, et sa survenance fusionne sans déplacer la référence
statut: à planifier
depend_de: EP-08
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
l'auteur du 2026-11-19, prises en tranchant #4034). Il vient après EP-08, dont il réutilise la base
et la mise à jour d'un différentiel, et après une révision de la spécification. Il reste à cadrer :
ses US, sa conception et son rang se décident à son cadrage.

## Ce qui en fait partie

- le devis propre d'un risque préparé comme un différentiel de la structure principale, dans les
  grilles de planning et de devis, où il ajoute des tâches et des lignes, modifie celles qui
  existent et en abandonne ;
- la reprise des devis propres qu'EP-08 a livrés, relus comme des différentiels qui n'ajoutent que
  des tâches sous leur tâche porteuse ;
- le réexamen d'un risque, qui met son devis propre à jour depuis la structure principale et
  présente ce qu'il ne peut reporter ;
- la gravité d'un risque, écart net entre le projet avec le risque et le projet sans lui, et la
  provision qui en est tirée ;
- la survenance, qui fusionne ce que le devis propre désigne sur les grandeurs courantes seules ;
- le coût à la survenance, la couverture et le suivi d'un risque survenu, redits pour un risque qui
  modifie ou abandonne ;
- la lecture, avant la survenance, du planning entier avec le risque appliqué ;
- les écrans des risques, le jeu de données de référence et les exemples du contrat qui suivent.

## Ce qui n'en fait pas partie

- la base d'un différentiel et sa mise à jour depuis la structure principale — EP-08 (#4034,
  #4132), que cet EPIC réutilise ;
- l'avenant, sa fusion et le déplacement de la référence — EP-08 ;
- les risques du portefeuille — EP-11.

## Exigences réalisées

À établir au cadrage, après la révision de la spécification. Les exigences qu'elle doit redire sont
closes par EP-08 : WF-RIS-0010 (la gravité, total de la structure propre), WF-RIS-0020 (le
réexamen), WF-RIS-0030 (le devis propre), WF-RIS-0040 (la grille de suivi), WF-RIS-0050 (le coût à
la survenance et le réestimé en regard), WF-RIS-0060 (la survenance), WF-REV-0100 (les structures
d'une révision) et WF-IND-0030 (la valeur acquise d'une tâche qu'une survenance termine). Leur
révision dira si cet EPIC les clôt sous une version nouvelle ou corrige le code d'un EPIC livré.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage. Le contrat, figé (`docs/api/DECISIONS.md`, « La règle d'après le gel »),
change : le compte rendu et la déclaration d'une survenance (`getRiskOccurrenceReport`,
`declareRiskOccurrence`), la lecture d'un risque et de son registre (`getRisk`, `listRisks`), le
réexamen (`reviewRisk`), et la mise à jour d'un différentiel qu'EP-08 ajoute, étendue au devis
propre.

## Préalables

EP-08 livré, la mise à jour d'un différentiel écrite sans être liée à la nature « avenant » : ce
que la structure désigne par rapport à sa base d'une part, son application à la structure
principale du jour de l'autre (#4034). La spécification révisée sur les exigences ci-dessus, par
son auteur.

## Définition de fini

À établir au cadrage.

## Constats reçus

Aucun n'est reporté. Deux constats d'EP-08 sont tranchés au plus léger parce que cet EPIC rend leur
règle provisoire (décision de l'auteur du 2026-11-19) : #4133, les dates du devis propre le jour de
la survenance, que le compte rendu signale sans que la survenance redate ; #4134, les tâches en
aval que la greffe déplace, nommées au compte rendu sans champ nouveau. Le devis propre préparé
comme un différentiel porte le planning entier : ses tâches se datent par leurs liaisons avec
celles du projet, et le retard se lit dans sa grille.

## Conception

À écrire au cadrage, après les US. Ce qui suit est décidé avant lui et s'impose à elle.

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

### Ce qui reste ouvert

- la forme de ce que le devis propre conserve, et la migration des devis propres d'EP-08 ;
- la ligne de provision et la tâche qui la porte, qui n'est plus le lieu d'une greffe ;
- le coût à la survenance et l'écart de couverture d'un risque dont la gravité est un écart net,
  ou négative ;
- la trace d'un risque survenu (`origin_risk_id`) sur une ligne modifiée ou une tâche abandonnée ;
- ce que la valeur acquise d'un coup fait aux courbes et aux indicateurs conservés, et comment
  l'écran le dit ;
- ce que la fusion d'un avenant fait d'un devis propre qui désigne les mêmes tâches que lui.

# L’avenant et le différentiel

## Ce que dit le glossaire

> **Avenant** — Désigne une modification contractuelle du projet en cours d’exécution. Il est préparé comme une structure différentielle, puis fusionné à sa contractualisation, ce qui produit une nouvelle révision de référence.

> **Différentiel** — Désigne une structure de coûts qui décrit un écart par rapport à la structure principale : des tâches et des lignes ajoutées, modifiées ou retirées. Un avenant se prépare comme un différentiel, puis se fusionne.

> **Structure de coûts** — Désigne un arbre de tâches portant des lignes de devis. Sa nature indique ce qu’elle décrit : la structure principale du projet, le différentiel d’un avenant, ou le devis propre à un risque. Une révision porte une structure principale, et le cas échéant des différentiels et des devis de risques.

> **Lignée** — Désigne l’identité qu’une structure de coûts, une tâche ou une ligne de devis conserve d’une révision à l’autre, distincte de l’identifiant propre à chaque révision. C’est elle que les imports rapprochent, qu’un différentiel désigne, et qui permet de comparer deux révisions.

## Dans Waterfall

**Préparer un avenant**, sur l’écran des [révisions](../FBS-4.1.md), crée un différentiel de la structure principale, sous le libellé donné. Il se saisit au [planning](../FBS-4.3.md) et au [devis](../FBS-4.4.md) comme une autre structure, que le bandeau nomme ; plusieurs peuvent coexister, et chacun se fusionne ou s’abandonne à part. Rien ne touche la structure principale avant la contractualisation.

**Contractualiser l’avenant**, depuis la grille du différentiel, présente d’abord le compte rendu de la fusion : les tâches, les lignes et les liaisons ajoutées, modifiées et retirées, les tâches démarrées qui seront terminées, et les motifs qui la refusent. Confirmée, la fusion s’applique à la révision en cours — créée au besoin — et la marque, sous le nom de version demandé ; la révision marquée devient la référence. Les lignes désignées prennent les grandeurs de référence du différentiel, d’où leur montant budgété ; une tâche démarrée n’est jamais retirée : son reste à engager est porté à zéro, ce qui la termine.

C’est le seul chemin qui déplace le [budget de référence](budget-de-reference.md) une fois la désignation de la référence devenue définitive. La [valeur planifiée](valeur-planifiee.md) se recalcule alors entièrement sur la nouvelle référence, et la courbe du budget cumulé marque une marche à la date de l’avenant.

## Voir aussi

- [La gestion des révisions](../FBS-4.1.md), [la planification](../FBS-4.3.md) ;
- [les révisions](revisions.md), [le budget de référence](budget-de-reference.md), [la provision et la réserve](provision-et-reserve.md).

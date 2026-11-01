# Structure des coûts du portefeuille

## Ce que montre l’écran

La répartition des coûts des projets du périmètre, à la date de calcul. Sous le titre, le périmètre retenu et la date de calcul. Trois tables, chacune en montant et en part :

- **Budget de référence par nature** : le budget de référence agrégé, ventilé par nature de coût ;
- **Reste à engager par nature** : le reste à engager agrégé, ventilé de même ;
- **Main-d’œuvre par nœud d’organisation**.

Le coût réel ne se ventile pas par nature : l’ERP ne le fournit pas, et l’écran le dit. Un projet en chiffrage, quand il est retenu, compte pour son devis courant pondéré par sa probabilité de gain : hors lignes de provision au titre du budget, provisions comprises au titre du reste à engager.

## Ses commandes

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés ; le dernier état retenu ne se relâche pas.
- **Calculé au**, la date de calcul, puis **Appliquer**. Cette vue ne prend pas de période.
- **Nœud d’organisation et ses descendants** ne restreint que les lignes de main-d’œuvre dont le rôle relève du nœud.

Les tables se lisent : elles ne se trient ni ne se filtrent.

## Ses colonnes et ses valeurs calculées

Le montant d’une nature ou d’un nœud est la somme de ceux des projets du périmètre ; sa part, ce montant rapporté au total de la table. Tout est calculé par le serveur. Une nature ou un nœud sans nom se lit « Sans nom ».

## Les gestes au clavier

- `Tab` parcourt les filtres et les tables ; une table plus large que la fenêtre défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Le portefeuille de projets](FBS-2.1.md), [le plan de charge agrégé](FBS-2.2.md) ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [le reste à engager et le devis actualisé](notions/reste-a-engager.md), [la provision et la réserve](notions/provision-et-reserve.md).

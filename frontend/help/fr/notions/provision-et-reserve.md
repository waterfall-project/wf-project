# La provision et la réserve pour risques

## Ce que dit le glossaire

> **Provision** — Désigne le montant réservé pour couvrir les conséquences d’un risque identifié, égal à sa gravité pondérée par sa probabilité. Elle compte au devis et au reste à engager, jamais au budget de référence ; un risque survenu ou écarté n’en porte plus. Elle relève d’une nature de type provision pour risques ; une provision saisie, pour aléas par exemple, est une ligne hors main-d’œuvre ordinaire.

> **Réserve pour risques** — Désigne la somme des lignes de provision de la révision de référence. Elle ne fait pas partie du budget de référence et ne bouge qu’avec lui ; c’est à elle que se comparent les provisions restantes et le coût des risques survenus.

> **Coût à la survenance** — Désigne, pour un risque survenu, le total de son devis propre au moment où il a été déclaré survenu. Il ne change plus, quelles que soient les réestimations et la terminaison des tâches fusionnées ; c’est lui que la couverture des risques compare à la réserve.

> **Couverture des risques** — Désigne la mise en regard, pour un projet ou pour le portefeuille, de la réserve pour risques de la référence avec la somme des provisions des risques identifiés et du coût à la survenance des risques survenus ; leur différence est l’écart de couverture.

> **Écart de couverture** — Désigne la différence, signée, entre la réserve pour risques de la référence et la somme des provisions des risques identifiés et du coût à la survenance des risques survenus. Négatif, les risques coûtent plus que ce qui avait été réservé.

## Dans Waterfall

Un risque se chiffre dans un devis qui lui est propre, dont le total est sa gravité. Tant qu’il est identifié, sa provision — sa gravité pondérée par sa probabilité — est une ligne de la structure principale, sur la tâche choisie à sa déclaration, sous une catégorie d’une nature de provision pour risques. Le serveur la tient à jour : elle ne se saisit pas.

Déclaré survenu, le risque perd sa ligne de provision et son devis propre rejoint la structure principale, avec un montant budgété nul : il pèse sur le reste à engager, et son coût à la survenance reste compté dans la couverture. Écarté, il perd sa provision sans rien ajouter.

La réserve est fixée par la [révision de référence](revisions.md) : à chaque nouvelle référence, elle garde la provision que portaient dans la précédente les risques survenus ou écartés avant elle, et s’augmente de celle des risques identifiés que la nouvelle porte. Les provisions des risques retenus et la couverture se lisent à la [gestion des risques](../FBS-4.6.md) et au [reste à engager](../FBS-4.5.md) ; la zone d’un risque, à la matrice que règlent les [paramètres de risques](../FBS-3.3.md).

## Voir aussi

- [La gestion des risques](../FBS-4.6.md), [les provisions des risques retenus](../FBS-4.6.2.md), [les risques du portefeuille](../FBS-2.5.md) ;
- [le budget de référence](budget-de-reference.md), [le reste à engager et le devis actualisé](reste-a-engager.md).

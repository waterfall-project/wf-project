# Indicateur de coûts (CPI)

## Ce que montre l’écran

La carte de l’indice de coût, parmi les [indicateurs projets](FBS-4.8.md), avec sa date de calcul :

- **Indice de coût** : la [valeur acquise](notions/valeur-acquise.md) rapportée au coût réel, avec sa zone — nominal, vigilance ou alerte — d’après les seuils du référentiel. Inférieur à 1, le travail fait a coûté plus que promis. Non calculable tant que le coût réel est nul, avant le premier import de coûts réels.
- **Écart de coût** : la valeur acquise moins le coût réel, négatif quand le travail fait a coûté plus que son budget ; puis la **Valeur acquise** et le **Coût réel**.
- **Évolution de l’indice de coût** : une courbe pour le projet et une pour chacune de ses mailles — chaque sous-projet, et l’ensemble « hors sous-projet » —, ou pour le seul sous-projet que le bandeau filtre. Un point par révision marquée à partir de l’état En cours, à sa date de marquage, et le dernier au jour courant ; le **Seuil de vigilance** et le **Seuil d’alerte** sont tracés en travers.

Un indice ne se lit qu’avec sa tendance : 0,9 qui remonte et 0,9 qui descend ne demandent pas la même décision.

## Ses commandes

**Valeurs du graphique** déplie l’évolution en table. Ce graphique ne s’exporte pas.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur, la zone comprise : le serveur la classe à la lecture d’après les seuils courants des [paramètres d’indicateurs](FBS-3.4.md), si bien que la zone d’un indice conservé peut changer avec les seuils, jamais sa valeur. La table des valeurs donne, pour chaque point, la **Maille**, la **Révision**, la **Date**, l’**Indice** et la **Zone** ; un point non calculable laisse un trou dans sa courbe, et sa ligne dit pourquoi.

L’évolution est toujours calculée au jour courant, sur la révision en cours ; quand les indicateurs le sont sur une autre révision, l’écran le dit en tête.

## Les gestes au clavier

- `Tab` atteint **Valeurs du graphique** ; la table, plus large que la fenêtre, défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs projets](FBS-4.8.md), [l’indicateur de délais](FBS-4.8.5.md), [la projection à terminaison](FBS-4.8.2.md) ;
- [les paramètres d’indicateurs](FBS-3.4.md), où se règlent les seuils ;
- les notions : [les indices](notions/indices.md), [la valeur acquise](notions/valeur-acquise.md).

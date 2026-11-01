# Indicateur de délais (SPI)

## Ce que montre l’écran

La carte de l’indice de délai, parmi les [indicateurs projets](FBS-4.8.md), avec sa date de calcul :

- **Indice de délai** : la [valeur acquise](notions/valeur-acquise.md) rapportée à la [valeur planifiée](notions/valeur-planifiee.md) à la même date, avec sa zone — nominal, vigilance ou alerte — d’après les seuils du référentiel. Inférieur à 1, moins de travail a été fait que la référence n’en prévoyait à cette date. Non calculable tant que la valeur planifiée est nulle, notamment avant le début de la première tâche de la référence qui porte une ligne budgétée.
- **Écart de délai** : la valeur acquise moins la valeur planifiée, négatif en retard, positif en avance ; puis la **Valeur acquise** et la **Valeur planifiée**.
- **Évolution de l’indice de délai** : une courbe pour le projet et une pour chacune de ses mailles — chaque sous-projet, et l’ensemble « hors sous-projet » —, ou pour le seul sous-projet que le bandeau filtre. Un point par révision marquée à partir de l’état En cours, à sa date de marquage, et le dernier au jour courant ; le **Seuil de vigilance** et le **Seuil d’alerte** sont tracés en travers.

La valeur planifiée se lit sur les dates de la révision de référence, la valeur acquise sur les dates de terminaison réelles : l’indice mesure un retard sans qu’aucune date de la révision courante n’intervienne.

## Ses commandes

**Valeurs du graphique** déplie l’évolution en table. Ce graphique ne s’exporte pas.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur, la zone comprise : le serveur la classe à la lecture d’après les seuils courants des [paramètres d’indicateurs](FBS-3.4.md), si bien que la zone d’un indice conservé peut changer avec les seuils, jamais sa valeur. La table des valeurs donne, pour chaque point, la **Maille**, la **Révision**, la **Date**, l’**Indice** et la **Zone** ; un point non calculable laisse un trou dans sa courbe, et sa ligne dit pourquoi.

L’évolution est toujours calculée jusqu’au jour courant, son dernier point sur la révision en cours, ou, sur un projet qui n’en a pas, sur sa dernière révision marquée avec le coût réel du jour, ses points conservés inchangés ; quand les indicateurs le sont sur une autre révision, l’écran le dit en tête.

## Les gestes au clavier

- `Tab` atteint **Valeurs du graphique** ; la table, plus large que la fenêtre, défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs projets](FBS-4.8.md), [l’indicateur de coûts](FBS-4.8.4.md), [le suivi des jalons](FBS-4.8.6.md) ;
- [les paramètres d’indicateurs](FBS-3.4.md), où se règlent les seuils ;
- les notions : [les indices](notions/indices.md), [la valeur planifiée](notions/valeur-planifiee.md), [la valeur acquise](notions/valeur-acquise.md).

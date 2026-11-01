# Courbes de valeur acquise

## Ce que montre l’écran

Le graphique **Valeur planifiée, valeur acquise et coût réel**, en bas des [indicateurs projets](FBS-4.8.md) : la vue de performance du projet, au pas du mois, chaque point portant le cumul à la fin du mois.

- **Valeur planifiée** : cumulée sur les dates de la révision de référence, prolongée jusqu’à la fin de la référence, où elle atteint le [budget de référence](notions/budget-de-reference.md).
- **Valeur acquise** : cumulée selon les dates de terminaison des tâches, jusqu’à la date de calcul ; une tâche terminée y fait une marche au mois de sa terminaison.
- **Coût réel** : cumulé selon les dates de pièce, jusqu’à la date de calcul.

Les écarts verticaux se lisent comme les écarts des indices : entre valeur acquise et coût réel, l’écart de coût ; entre valeur acquise et valeur planifiée, l’écart de délai en valeur. L’écart horizontal entre ces deux dernières est le retard en temps. Là où la courbe en S dit combien, ces courbes disent si l’on a fait ce qu’on devait, et à quel prix.

Quand rien ne relève de la maille lue — un sous-projet sans ligne ni coût réel —, la section le dit au lieu de tracer un zéro ; une courbe seule sans point est nommée sous le graphique.

## Ses commandes

- **Exporter en PNG** enregistre les courbes en image, avec le projet, la révision et la date de calcul, et le sous-projet quand le bandeau en filtre un.
- **Valeurs du graphique** déplie leurs points en table.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur ; rien n’est sommé dans le navigateur. La table des valeurs donne, pour chaque point, la **Courbe**, la **Date** et le **Montant**.

## Les gestes au clavier

- `Tab` atteint **Exporter en PNG** et **Valeurs du graphique** ; la table, plus large que la fenêtre, défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs projets](FBS-4.8.md), [l’indicateur de coûts](FBS-4.8.4.md), [l’indicateur de délais](FBS-4.8.5.md), [les coûts cumulés](FBS-4.8.7.md) ;
- les notions : [la valeur planifiée](notions/valeur-planifiee.md), [la valeur acquise](notions/valeur-acquise.md), [les indices](notions/indices.md).

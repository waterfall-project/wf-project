# Santé du pilotage

## Ce que montre l’écran

Les signaux qui disent qu’un projet en cours du périmètre n’est plus tenu. Sous le titre, le périmètre retenu et la date de calcul. Une table, **Signaux de santé du pilotage**, donne pour chaque signal son projet, ce qu’il signale et sa zone :

- **Revue périodique en retard** : la dernière révision marquée du projet est plus ancienne que le délai maximal entre deux revues que fixe le référentiel ; le signal dit depuis combien de semaines.
- **Risques non réexaminés** : des risques identifiés n’ont pas été réexaminés depuis la dernière révision marquée.
- **Aucun coût réel depuis la dernière revue** : aucun coût réel n’a été importé depuis la dernière révision marquée.
- **Jalon contractuel dépassé** : un jalon inscrit au suivi temps/temps a passé sa date de référence sans être terminé ; le signal nomme le jalon et sa date.

Sans signal, l’écran dit que le pilotage des projets du périmètre est tenu.

## Ses commandes

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés ; le dernier état retenu ne se relâche pas. Les signaux ne portent que sur les projets en cours.
- **Calculé au**, la date de calcul, puis **Appliquer**. Cette vue ne prend ni période ni nœud d’organisation.

Le nom d’un projet l’ouvre, quand vous pouvez le consulter.

## Ses colonnes et ses valeurs calculées

Les signaux et leurs zones sont ceux du serveur ; la table ne se trie ni ne se filtre. La zone se lit par son signal, jamais par la seule couleur.

## Les gestes au clavier

- `Tab` parcourt les filtres et les liens des projets ; `Entrée` sur le nom d’un projet l’ouvre.
- `F1` ouvre cette aide.

## Voir aussi

- [Le portefeuille de projets](FBS-2.1.md), [les risques du portefeuille](FBS-2.5.md) ;
- [la gestion des révisions](FBS-4.1.md), où se marque la revue, et [les chronologies](FBS-4.3.1.md), qui portent le suivi temps/temps des jalons ;
- [les paramètres d’indicateurs](FBS-3.4.md), où se fixe le délai maximal entre deux revues ;
- la notion : [les révisions](notions/revisions.md).

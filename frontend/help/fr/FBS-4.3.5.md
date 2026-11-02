# Arborescence de tâches

## Ce que montre l’écran

Une feuille de la [planification](FBS-4.3.md), atteinte depuis l’en-tête du planning, dans le même contexte de lecture : le découpage de l’affaire plutôt que son calendrier, sans axe du temps ni liaisons. C’est la vue qu’on met dans un dossier de revue ou qu’on montre au client, là où le Gantt sert à travailler.

Sous un nœud racine qui représente le projet, les tâches récapitulatives de la structure principale, chacune nommée par son numéro et son libellé : le premier niveau côte à côte, chaque niveau suivant en colonne sous son parent, une mise en page pensée pour la page A4 en portrait. Ni les jalons ni les tâches feuilles n’y figurent : elles relèvent du travail à faire, non du découpage. Un planning sans récapitulative se réduit au nœud du projet, et l’écran le dit.

Les tâches sont lues comme la grille de planning les lit, restreintes au sous-projet filtré. L’arborescence se lit : rien ne s’y saisit.

## Ses commandes

- **Niveau affiché** : un lien par niveau que la structure compte, **Niveau 1**, **Niveau 2**… Au-delà du niveau choisi, les tâches subordonnées ne sont pas représentées : c’est lui qui règle l’encombrement. Un planning de plusieurs centaines de tâches ne se montre pas ; ses trois premiers niveaux, si.
- L’image de l’arborescence s’exporte depuis les [imports et exports](FBS-4.3.4.md), par **Image de l’arborescence de tâches**, au niveau que vous donnez. Elle a la taille que son contenu exige, sans pagination ni réduction.

## Ses colonnes et ses valeurs calculées

Aucune valeur calculée : les numéros et les libellés sont ceux du planning, tels que le serveur les donne, et les niveaux offerts sont ceux qu’il dit que la structure compte.

## Les gestes au clavier

- L’arborescence est un seul arrêt de tabulation : `↑` et `↓` parcourent les tâches dans leur ordre, `←` mène au parent, `→` au premier enfant, `Origine` et `Fin` à la première et à la dernière.
- Rien ne se plie : le niveau choisi décide de ce qui se montre. Aucune touche ne change une tâche.
- `Tab` atteint les liens des niveaux.
- `F1` ouvre cette aide.

## Voir aussi

- [La planification](FBS-4.3.md) et [la grille de planning](FBS-4.3.2.md), où les récapitulatives se créent ;
- [les chronologies](FBS-4.3.1.md), l’autre vue destinée à être montrée ;
- [les imports et exports](FBS-4.3.4.md), d’où l’image s’exporte.

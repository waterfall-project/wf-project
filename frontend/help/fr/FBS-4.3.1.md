# Chronologies

## Ce que montre l’écran

Une feuille de la [planification](FBS-4.3.md), atteinte depuis l’en-tête du planning, dans le même contexte de lecture. Une chronologie est une vue synthétique destinée à être montrée — à un comité de direction, à un client, à une équipe : elle ne présente que les tâches et les jalons qui y sont inscrits. Un projet peut en porter plusieurs, chacune nommée et conservée.

En tête, les chronologies du projet, chacune un lien qui l’affiche ; la première s’affiche quand l’adresse n’en nomme aucune. Dessous, la **frise** de la chronologie affichée, sur l’axe du temps du Gantt : chaque tâche inscrite est un rectangle de son début à sa fin, qui porte son nom, et chaque jalon une ligne verticale, son nom et sa date au pied. Les rectangles se rangent en couloirs, d’eux-mêmes dans l’ordre du plan, ou là où vous les avez placés. Sous la frise, une table lit les mêmes tâches, leurs dates et leurs couloirs.

Les inscriptions se font depuis la [grille de planning](FBS-4.3.2.md), par **Chronologies** dans le menu d’une cellule : rien ne s’inscrit ici. Les tâches lues sont celles de la révision du contexte, restreintes au sous-projet filtré.

## Ses commandes

Les commandes qui écrivent suivent **Gérer les chronologies**, que le projet offre ; indisponibles, elles restent présentées et disent ce qui leur manque — un projet terminal.

- **Nouvelle chronologie** ouvre le formulaire : un **Nom**, obligatoire.
- **Supprimer**, sur la chronologie affichée, après confirmation : ses inscriptions disparaissent avec elle, les tâches et les jalons gardent leurs dates. L’écran affiche alors la première chronologie qui reste.

Sur la frise, pour tous :

- **Zoom avant**, **Zoom arrière** et **Ajuster au projet** règlent l’échelle du temps ;
- **Disposition automatique** range de nouveau les tâches d’elles-mêmes, en oubliant les couloirs choisis à la main ; indisponible tant qu’aucune tâche n’a été placée ;
- **Exporter en PNG** enregistre la frise telle qu’elle est disposée, avec le nom de la chronologie, le projet, la révision et la date de calcul des dates.

Une tâche se glisse à la souris d’un couloir à l’autre. Les couloirs sont une préférence d’affichage de chacun, par chronologie : déplacer une tâche ne la modifie pas. Un déplacement où le rectangle en chevaucherait un autre est refusé, et dit.

## Ses colonnes et ses valeurs calculées

Les dates sont celles que le serveur a calculées : rien ne se planifie ici. Un nom trop long pour son rectangle est coupé, et se lit entier dans son infobulle et dans la table ; une tâche sans dates n’est pas dessinée, et la table le dit.

## Les gestes au clavier

- La frise est un seul arrêt de tabulation : `←` et `→` passent d’une tâche à l’autre, l’axe défilant pour la garder en vue.
- `Alt+↑` et `Alt+↓` changent de couloir la tâche active ; `Échap` abandonne un glisser.
- `Tab` atteint les liens des chronologies et les commandes.
- Sur un Mac, `⌥` tient lieu de `Alt`.
- `F1` ouvre cette aide.

## Voir aussi

- [La planification](FBS-4.3.md), [la grille de planning](FBS-4.3.2.md), où les tâches s’inscrivent, et [le Gantt](FBS-4.3.3.md), dont la frise reprend l’axe ;
- [l’arborescence de tâches](FBS-4.3.5.md), l’autre vue destinée à être montrée.

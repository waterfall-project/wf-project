# Plan de charge du projet

## Ce que montre l’écran

Une feuille du [chiffrage](FBS-4.4.md), que l’écran du devis ouvre dans le même contexte : le devis traduit en besoin de ressources — combien d’heures, de quel rôle, quel mois. C’est la vue que le manager consolide ensuite sur plusieurs projets, dans le [plan de charge agrégé](FBS-2.2.md).

La **Charge par rôle et par mois** : une barre par mois, empilée par rôle de ressource, le total du mois à son sommet ; la légende nomme les rôles, et l’infobulle d’un mois les liste avec leurs heures. Les rôles se distinguent par leur couleur ; la préférence **Motifs des séries** de « Mon compte » donne en plus à chacun un motif, que la légende et l’image exportée portent aussi. Seules les lignes de main-d’œuvre chargent. La charge d’une ligne se répartit sur la durée de sa tâche, au prorata des heures travaillées du calendrier de son rôle. Sur une base de reste à engager, la charge restante d’une tâche non terminée se répartit sur la seule part de sa durée qui suit la date de calcul, et se porte au mois de la date de calcul quand la fin de la tâche est dépassée.

Sous le choix, la base et la révision que le serveur dit avoir lues. Le service calcule tout le plan — la charge de chaque rôle et de chaque mois, la capacité de chaque rôle, les totaux sans trou et la zone — depuis le devis de la révision ; l’écran ne fait que le montrer. Une tâche terminée ne charge rien sur le reste à engager d’une révision.

Sous l’histogramme, le **Détail par rôle et par tâche** : une grille du rôle à la tâche, en lecture seule, une colonne par mois du plan. Sous chaque rôle, chacune des tâches qui portent une de ses lignes de main-d’œuvre, rangées par date de début, puis dans l’ordre du planning ; deux lignes du rôle sous une même tâche y font une seule ligne. Le détail n’a pas de réglage propre : il est calculé sur la base et sous le nœud d’organisation choisis pour l’histogramme. Le libellé d’une tâche mène à sa ligne dans la grille de planning de la révision que la base lit — la révision en cours, la référence ou la révision marquée choisie —, qui déplie ses récapitulatives et y pose le curseur. Sans droit de lecture du planning, la tâche est nommée sans lien.

## Ses commandes

En tête du plan, puis **Afficher** :

- **Base** : **Budget de la révision de référence**, **Reste à engager d’une révision marquée** ou **Reste à engager de la révision en cours**. Seules les bases que le projet admet sont offertes : le budget de la référence quand le projet a une révision de référence, le reste d’une révision marquée quand il en a une, la révision en cours toujours — seule, sans l’un ni l’autre.
- **Révision marquée**, pour la base d’une révision marquée : chacune de celles du projet.
- **Nœud d’organisation et ses descendants** restreint le plan aux rôles qui en relèvent ; **Tous les nœuds** le lève.

Une base que le serveur refuse — un projet sans révision de référence, une révision marquée qui manque ou ne l’est pas — se dit indisponible, avec sa raison, et le reste de l’écran se montre.

Sur le graphique :

- **Valeurs du graphique**, sous le graphique, déplie la table de ses valeurs ;
- **Exporter en PNG** enregistre le graphique, avec le projet, la révision, la base, le nœud et la date de calcul.

Dans le détail, la barre de la grille offre **Colonnes** et **Arbre**, qui plie ou déplie les rôles ; le bouton du libellé d’un rôle plie ou déplie ses tâches.

## Ses colonnes et ses valeurs calculées

Tout chiffre est celui du serveur : les heures de chaque rôle et le total de chaque mois. La table des valeurs donne, pour chaque rôle et chaque mois, la **Charge (h)**, la **Capacité (h par mois)** du rôle et la **Zone** du mois : en alerte quand la charge dépasse la capacité, nominale sinon, dite par son signal et jamais par la seule couleur. Un rôle sans charge y figure aussi. Le plan d’un projet ne présente aucun taux de charge — la capacité est celle de toute l’installation — et ne dessine pas la capacité : le taux de charge est celui du plan agrégé.

Le détail ne somme rien : la charge d’un mois d’un rôle est celle de l’histogramme, celle d’une tâche la part que le serveur lui donne, et un mois sans charge reste vide. Les heures d’une tâche sont la somme que le serveur calcule ; celles d’un rôle ne sont pas répétées. En pied, le total de chaque mois est celui du plan.

## Les gestes au clavier

- `Tab` parcourt le choix de la base, de la révision et du nœud, **Afficher**, puis les commandes du graphique ; `Entrée` sur **Valeurs du graphique** déplie ou replie la table.
- La table des valeurs, quand elle dépasse sa boîte, défile aux flèches une fois atteinte.
- La grille du détail est un seul arrêt de `Tab` : les flèches déplacent la cellule active, `Entrée` sur le libellé d’une tâche suit son lien vers la grille de planning ; `Alt` et `-` plie un rôle, `Alt` et `+` le déplie.
- `F1` ouvre cette aide.

## Voir aussi

- [Le chiffrage et le devis](FBS-4.4.md), dont les lignes de main-d’œuvre font la charge, [le planning](FBS-4.3.md), où mène une tâche du détail, et [le reste à engager](FBS-4.5.md) ;
- [le plan de charge agrégé](FBS-2.2.md) et [les rôles de ressources](FBS-3.2.2.md), qui portent la capacité ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [le reste à engager](notions/reste-a-engager.md).

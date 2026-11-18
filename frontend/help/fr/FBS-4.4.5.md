# Projection de dépenses du projet

## Ce que montre l’écran

Une feuille du [chiffrage](FBS-4.4.md), que l’écran du devis et celui du reste à engager ouvrent dans le même contexte : ce que le projet dépensera, mois par mois et par nature de coût, main-d’œuvre et débours totalisés. C’est la vue de la dépense à venir, à côté du [plan de charge](FBS-4.4.4.md), qui est celle des heures.

Les **Dépenses par nature de coût et par mois** : une barre par mois, empilée par nature de coût, le total du mois à son sommet ; la légende nomme les natures, et l’infobulle d’un mois les liste avec leurs montants. Les natures se distinguent par leur couleur ; la préférence **Motifs des séries** de « Mon compte » donne en plus à chacune un motif. La devise de l’installation titre l’axe. Les valeurs du graphique se lisent aussi en table. Une ligne de provision ne figure sous aucune nature.

Le montant de chaque ligne de main-d’œuvre et de débours se répartit sur la durée de sa tâche, au prorata des heures travaillées, en parts arrondies au centime dont la somme est le montant de la ligne. Sur une base de reste à engager, seul le reste de la ligne se répartit, sur la part de la tâche qui suit la date de calcul, et se porte au mois de cette date quand la fin de la tâche est dépassée : aucun mois n’y précède la date de calcul, et le total de la projection est le reste à engager du projet hors provisions. Sur la base de la révision de référence, la projection présente aussi les mois antérieurs à la date de calcul. Pour une révision marquée, elle est calculée à la lecture, sur ses images.

Sous le choix, la base et la révision que le serveur dit avoir lues, et la date. Sous le graphique, la grille des **Dépenses par nature de coût et par catégorie** : une grille de la nature à la catégorie, en lecture seule, une colonne par mois, le total de chaque ligne et, en pied, celui de chaque mois et celui de la projection. Elle n’a pas de réglage propre : elle est calculée sur la base, la date et le sous-projet choisis pour le graphique.

## Ses commandes

En tête de la projection, puis **Afficher** :

- **Base** : **Budget de la révision de référence**, **Reste à engager d’une révision marquée** ou **Reste à engager de la révision en cours**. Seules les bases que le projet admet sont offertes : le budget de la référence quand le projet a une révision de référence, le reste d’une révision marquée quand il en a une, la révision en cours toujours.
- **Révision marquée**, pour la base d’une révision marquée : chacune de celles du projet.
- **Date** : **Date de consommation**, la dépense au mois où elle est consommée, ou **Date de paiement**, la dépense décalée du délai de paiement de chaque ligne — le décaissement.
- **Sous-projet** restreint la projection à un sous-projet ; **Hors sous-projet** retient ce qui n’appartient à aucun, **Tout le projet** lève le filtre.

Une projection que le serveur refuse — un projet sans révision de référence, une révision marquée qui manque ou ne l’est pas, un sous-projet inconnu, une catégorie de main-d’œuvre sans taux horaire pour l’année de référence — se dit indisponible, avec sa raison.

Sur le graphique :

- **Valeurs du graphique**, sous le graphique, déplie la table de ses valeurs ;
- **Exporter en PNG** enregistre le graphique, avec le projet, la révision, la base, la date, le sous-projet et la date de calcul.

Dans la grille, la barre offre **Colonnes** et **Arbre**, qui plie ou déplie les natures ; le bouton du libellé d’une nature plie ou déplie ses catégories.

## Ses colonnes et ses valeurs calculées

Tout montant est celui du serveur : celui de chaque catégorie, de chaque nature, de chaque mois et le total de la projection. Le total de chaque mois est la somme des natures de ce mois, et celui de chaque nature la somme de ses catégories ; l’écran ne somme rien. Un mois sans montant reste vide dans la grille.

## Les gestes au clavier

- `Tab` parcourt le choix de la base, de la révision, de la date et du sous-projet, **Afficher**, puis les commandes du graphique ; `Entrée` sur **Valeurs du graphique** déplie ou replie la table.
- La table des valeurs, quand elle dépasse sa boîte, défile aux flèches une fois atteinte.
- La grille est un seul arrêt de `Tab` : les flèches déplacent la cellule active ; `Alt` et `-` plie une nature, `Alt` et `+` la déplie.
- `F1` ouvre cette aide.

## Voir aussi

- [Le chiffrage et le devis](FBS-4.4.md), dont les lignes font la dépense, [le plan de charge](FBS-4.4.4.md) et [le reste à engager](FBS-4.5.md) ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [le reste à engager](notions/reste-a-engager.md).

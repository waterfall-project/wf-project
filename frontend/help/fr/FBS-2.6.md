# Courbe en S du portefeuille

## Ce que montre l’écran

Les coûts cumulés des projets du périmètre, mois par mois, sur l’horizon choisi. Sous le titre, le périmètre retenu et la date de calcul.

**Coûts cumulés du portefeuille** montre trois courbes, chacune la somme de celles des projets : le budget de référence cumulé, le coût réel cumulé jusqu’à la date de calcul, puis, au-delà, la projection des chefs de projet. Un projet en chiffrage, quand il est retenu, y entre par son devis courant pondéré par sa probabilité de gain : hors lignes de provision pour la courbe du budget, provisions comprises pour la projection.

Lue en décaissements, la courbe devient **Décaissements cumulés du portefeuille** : chaque projet décalé de ses délais de paiement et portant les provisions de ses risques identifiés. Un second graphique, **Décaissements par mois**, détaille alors, mois par mois, le décaissé et ce qui reste à décaisser.

## Ses commandes

- **Lire en décaissements** passe la courbe en décaissements ; **Revenir aux coûts cumulés** la ramène.
- **Exporter en PNG** enregistre un graphique en image, avec le périmètre, l’horizon et la date de calcul ; **Valeurs du graphique** déplie ses valeurs, en table.

**Périmètre du portefeuille**, au-dessus de la vue :

- **États retenus** : les projets en cours, ceux en chiffrage, ceux terminés ; le dernier état retenu ne se relâche pas.
- **Calculé au**, la date de calcul, puis **Appliquer**. Cette vue ne prend ni période ni nœud d’organisation.
- **Horizon** : 6, 12 ou 24 mois, ou **Par défaut**, celui du serveur.

## Ses colonnes et ses valeurs calculées

Chaque point est la somme des points des projets, telle que le serveur la calcule ; rien n’est sommé ni décalé dans le navigateur. La courbe du coût réel monte par marches, à la date de chaque pièce. Une valeur que le serveur ne peut pas calculer laisse un trou dans sa courbe, et sa ligne de la table dit pourquoi. Les courbes se distinguent sans leur couleur : chacune est nommée à son extrémité.

## Les gestes au clavier

- `Tab` parcourt les filtres et les commandes des graphiques ; la table des valeurs, plus large que la fenêtre, défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Le portefeuille de projets](FBS-2.1.md), [la performance du portefeuille](FBS-2.3.md) ;
- [les indicateurs d’un projet](FBS-4.8.md), qui portent sa propre courbe en S ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [la provision et la réserve](notions/provision-et-reserve.md).

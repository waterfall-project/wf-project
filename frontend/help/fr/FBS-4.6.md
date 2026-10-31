# Gestion des risques

## Ce que montre l’écran

Le registre des risques du projet, tels que la révision lue les tient : leur probabilité, leur gravité, leur provision, le coût à la survenance d’un risque survenu, leur état. Un risque est un événement incertain qui affecterait le coût ou les délais ; ses conséquences se chiffrent dans un devis qui lui est propre, et sa provision — sa gravité pondérée par sa probabilité — se range, tant qu’il est identifié, sur une tâche de la structure principale. Survenu, il n’est plus un risque mais un fait : son devis propre rejoint la structure principale.

De haut en bas : les [provisions des risques retenus](FBS-4.6.2.md) et la couverture des risques ; le filtre par état ; la matrice des risques, repliée derrière sa commande ; le [registre des risques](FBS-4.6.1.md) ; et, quand un risque est choisi, son détail à côté du registre — sa description, ses actions de mitigation, sa ligne de provision avec sa catégorie et son sous-projet, l’historique de ses réexamens.

## Ses commandes

En tête de l’écran :

- **Identifier un risque** ouvre le formulaire de déclaration : libellé, description, actions de mitigation, probabilité en pourcentage, et, quand il y a le choix, la catégorie de la provision, le sous-projet et la tâche qui porte la provision — à défaut, la première tâche de premier niveau. Le risque créé, son devis propre s’ouvre dans la grille de devis. Indisponible sans « au moins une tâche » dans la structure principale, sans « une catégorie de provision pour risques active », sur un projet clos ou pendant un traitement de fond.

Au-dessus du registre :

- **Filtrer par état** : **Tous les états**, **Identifié**, **Survenu**, **Écarté** ; les provisions, les bulles de la matrice et le registre suivent le filtre.
- **Graphique** déplie ou replie la matrice des risques, un nuage de bulles — la probabilité en abscisse, la gravité en part du budget de référence en ordonnée, chaque bulle aussi grande que la gravité en montant —, avec sous elle le décompte des risques par case, tous états confondus. Une bulle cliquée ouvre le détail de son risque.
- **Rechercher un libellé** et **Colonnes**.

Dans le détail d’un risque :

- **Modifier** ouvre le formulaire du risque : libellé, description, actions de mitigation et provision, sans la probabilité, que seul le réexamen change ; la catégorie, le sous-projet et la tâche de la provision ne changent que tant que le risque est identifié.
- **Réexaminer** confirme ou change la probabilité et l’état — identifié ou écarté. Le réexamen est daté du jour ; le confirmer sans rien changer en produit un, qui s’ajoute à l’historique.
- **Supprimer le risque**, après confirmation, avec son devis propre et sa ligne de provision. Indisponible pour un risque qu’une révision marquée cite (« risque cité par aucune révision marquée ») : il s’écarte alors par un réexamen.
- **Déclarer survenu**, après confirmation : son devis propre est fusionné dans la structure principale de la révision en cours, avec un montant budgété nul, et sa ligne de provision est retirée ; le risque garde son coût à la survenance, le total de son devis propre à cet instant. La fusion est confiée au traitement de fond. La déclaration est définitive : un risque survenu liste toutes ses commandes indisponibles.
- **Fermer le détail du risque**.

Ces saisies ne se font que sur la révision en cours, là où elle liste « Modifier les risques » pour vous.

## Ses colonnes et ses valeurs calculées

La gravité, la provision et le coût à la survenance sont calculés par le serveur : la gravité est le total du devis propre du risque ; la provision d’un risque identifié, sa gravité pondérée par sa probabilité, celle d’un risque survenu ou écarté, la provision qu’il portait dans la révision de référence ; le coût à la survenance, le total du devis propre quand le risque a été déclaré survenu. Ils ne se saisissent pas : une cellule calculée nomme les règles dont sa valeur dépend. Le pied du registre porte le total général des provisions.

## Les gestes au clavier

- Le registre est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Page préc.` et `Page suiv.` d’un écran.
- Sur le libellé d’un risque, `Entrée` ouvre son détail.
- Sur un en-tête, `Entrée` ou `Espace` trie le registre par la colonne, sauf la case de la matrice ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [Le registre des risques](FBS-4.6.1.md) et [les provisions des risques retenus](FBS-4.6.2.md) ;
- [le devis](FBS-4.4.md), où se chiffre le devis propre d’un risque, et [le reste à engager](FBS-4.5.md), avec la couverture des risques ;
- les notions : [la provision et la réserve](notions/provision-et-reserve.md), [le budget de référence](notions/budget-de-reference.md), [les révisions](notions/revisions.md).

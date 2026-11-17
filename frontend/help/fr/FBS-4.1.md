# Gestion des révisions

## Ce que montre l’écran

Les révisions du projet : chacune est un instantané complet — ses structures de coûts et les valeurs du référentiel qu’elles emploient. Une révision est d’abord en cours d’élaboration, puis figée quand elle est marquée ; l’une des révisions marquées est la référence, qui fixe le budget, la réserve pour risques et la valeur planifiée. Ce cycle est celui de la [revue périodique](notions/revisions.md) : ouvrir une révision en cours, mettre à jour le planning et le reste à engager, réexaminer les risques, puis marquer.

Ouvrir un projet ne passe pas par cet écran : la page du projet mène à sa révision en cours, sinon à sa référence, sinon à sa dernière révision marquée ; elle ne mène ici que si cette révision n’est pas lisible par votre session. Quand l’import qui vient de créer le projet a mené jusqu’ici, son **compte rendu** s’affiche au-dessus de l’historique, comme sur la page du projet. On y vient aussi par la fonction **Révisions**, pour en lire une autre.

De haut en bas :

- l’**Historique des révisions**, seule carte de l’écran : pour chacune, sa version, son état, sa date de marquage, sa description, le lien qui l’ouvre, et la marque de la référence.

La comparaison de deux révisions ne se lit plus ici : elle se lit dans les grilles de planning, de devis et de reste à engager, depuis la commande **Comparer à la révision lue** de l’historique. Les structures de coûts de la révision lue se choisissent dans le bandeau des grilles, non sur cet écran.

## Ses commandes

En tête de l’écran, les commandes de la révision lue, chacune disponible ou nommant la condition qui lui manque ; **Ouvrir une révision en cours**, la seule commande pleine, est à droite du titre de la carte de l’historique :

- **Ouvrir une révision en cours** crée la révision en cours d’élaboration, copie de la dernière révision marquée. Indisponible quand le projet en a déjà une (« aucune révision en cours d’élaboration ») ou qu’il est clos.
- **Marquer la révision** demande un nom de version, obligatoire, et une description ; le marquage, confié au traitement de fond, fige la révision et conserve ses indicateurs. Indisponible sur une révision déjà marquée (« révision en cours d’élaboration ») ou pendant un traitement de fond.
- **Préparer un avenant** crée, sous le libellé donné, un différentiel de la structure principale, qui s’ouvre dans la grille de planning ; rien n’est fusionné avant sa contractualisation, depuis la grille de son différentiel.
- **Abandonner la révision en cours**, après confirmation : le projet revient à sa dernière révision marquée, et les lignes de la révision en cours sont supprimées. L’abandon est irréversible.
- **Déclarer un risque** mène, quand elle est disponible, à l’écran des [risques](FBS-4.6.md) de la révision, où « Identifier un risque » s’offre ; indisponible, elle dit ce qui lui manque.

Dans les sections :

- **Ouvrir**, dans l’historique, ouvre la révision : les écrans du projet la lisent alors.
- **Désigner comme référence**, commande de chaque révision marquée de l’historique, après confirmation : elle fixe le budget de référence et la valeur planifiée ; le projet qui porte son code projet passe à l’état En cours. Indisponible sur une révision qui ne porte aucune tâche ou aucune ligne de devis, et quand la référence ne se corrige plus — le projet a reçu un coût réel, ou une révision a été marquée depuis la dernière désignation.
- **Comparer à la révision lue**, commande de chaque révision marquée de l’historique, hors la révision lue : un menu des grilles de planning, de devis et de reste à engager que vous pouvez consulter, qui mène à la grille choisie, cette révision pour base de la comparaison.
- **Appliquer la mise à jour des taux**, commande de la révision en cours, à droite du titre : elle ouvre la proposition, catégorie par catégorie, dans une fenêtre ; pour les catégories retenues, après confirmation, les taux de la révision en cours sont remplacés par les taux proposés, et ses montants rechiffrés. Une proposition, jamais imposée ; offerte là où la révision se saisit au devis.

## Ses colonnes et ses valeurs calculées

L’historique se lit tel que le serveur le rend, dans son ordre.

## Les gestes au clavier

- `Tab` parcourt les commandes et les liens de l’historique ; une commande indisponible reste atteignable, et sa condition se lit dans sa description.
- `F1` ouvre cette aide.

## Voir aussi

- [La planification](FBS-4.3.md), [le devis](FBS-4.4.md), [le reste à engager](FBS-4.5.md) ;
- les notions : [les révisions](notions/revisions.md), [le budget de référence](notions/budget-de-reference.md), [la valeur planifiée](notions/valeur-planifiee.md), [l’avenant et le différentiel](notions/avenant-et-differentiel.md).

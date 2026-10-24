# Gestion des révisions

## Ce que montre l’écran

Les révisions du projet : chacune est un instantané complet — ses structures de coûts et les valeurs du référentiel qu’elles emploient. Une révision est d’abord en cours d’élaboration, puis figée quand elle est marquée ; l’une des révisions marquées est la référence, qui fixe le budget, la réserve pour risques et la valeur planifiée. Ce cycle est celui de la [revue périodique](notions/revisions.md) : ouvrir une révision en cours, mettre à jour le planning et le reste à engager, réexaminer les risques, puis marquer.

De haut en bas :

- l’**Historique des révisions** : pour chacune, sa version, son état, sa date de marquage, sa description, le lien qui l’ouvre, et la marque de la référence ;
- la **Désignation de la référence**, sur les révisions marquées ;
- la **Comparaison de deux révisions** marquées ;
- les **Structures de coûts** de la révision lue — la structure principale, les différentiels d’avenant, les devis propres des risques — avec leur état ;
- pour la révision en cours, la **Mise à jour des taux proposée**, quand le référentiel a changé depuis qu’elle a été chiffrée.

## Ses commandes

En tête de l’écran, les commandes de la révision lue, chacune disponible ou nommant la condition qui lui manque :

- **Ouvrir une révision en cours** crée la révision en cours d’élaboration, copie de la dernière révision marquée. Indisponible quand le projet en a déjà une (« aucune révision en cours d’élaboration ») ou qu’il est clos.
- **Marquer la révision** demande un nom de version, obligatoire, et une description ; le marquage, confié au traitement de fond, fige la révision et conserve ses indicateurs. Indisponible sur une révision déjà marquée (« révision en cours d’élaboration ») ou pendant un traitement de fond.
- **Préparer un avenant** crée, sous le libellé donné, un différentiel de la structure principale, qui s’ouvre dans la grille de planning ; rien n’est fusionné avant sa contractualisation, depuis la grille de son différentiel.
- **Abandonner la révision en cours**, après confirmation : le projet revient à sa dernière révision marquée, et les lignes de la révision en cours sont supprimées. L’abandon est irréversible.
- **Déclarer un risque** dit si l’identification d’un risque aboutirait ; le risque s’identifie sur l’écran des [risques](FBS-4.6.md).

Dans les sections :

- **Ouvrir**, dans l’historique, ouvre la révision : les écrans du projet la lisent alors.
- **Désigner comme référence**, sur une révision marquée, après confirmation : elle fixe le budget de référence et la valeur planifiée ; le projet qui porte son code projet passe à l’état En cours. Indisponible sur une révision qui ne porte aucune tâche ou aucune ligne de devis, et quand la référence ne se corrige plus — le projet a reçu un coût réel, ou une révision a été marquée depuis la dernière désignation.
- **Comparer**, entre deux révisions marquées choisies par **De la révision** et **À la révision** : la grille des nœuds comparés marque chaque tâche et chaque ligne ajoutée (`+`), retirée (`-`) ou modifiée (`M`), et les écarts de montants suivent. Il faut deux révisions marquées.
- **Appliquer la mise à jour des taux**, pour les catégories retenues, après confirmation : les taux de la révision en cours sont remplacés par les taux proposés, et ses montants rechiffrés. Une proposition, jamais imposée ; offerte là où la révision se saisit au devis.

## Ses colonnes et ses valeurs calculées

L’historique et la comparaison se lisent tels que le serveur les rend : la comparaison nomme ce qui change de chaque nœud, l’ordre est celui du plan, et rien ne s’y trie. Les écarts de montants sont calculés par le serveur, par axe.

## Les gestes au clavier

- `Tab` parcourt les commandes, les liens de l’historique et les champs de la comparaison ; une commande indisponible reste atteignable, et sa condition se lit dans sa description.
- La grille de la comparaison est un seul arrêt de tabulation, que les flèches parcourent.
- `F1` ouvre cette aide.

## Voir aussi

- [La planification](FBS-4.3.md), [le devis](FBS-4.4.md), [le reste à engager](FBS-4.5.md) ;
- les notions : [les révisions](notions/revisions.md), [le budget de référence](notions/budget-de-reference.md), [la valeur planifiée](notions/valeur-planifiee.md), [l’avenant et le différentiel](notions/avenant-et-differentiel.md).

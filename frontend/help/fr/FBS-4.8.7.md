# Coûts cumulés

## Ce que montre l’écran

La **Courbe en S**, sous le suivi des jalons des [indicateurs projets](FBS-4.8.md) : la vue budgétaire du projet, ce qu’il devait coûter, ce qu’il a coûté, ce qu’il coûtera. Elle ne parle pas d’avancement, seulement d’argent dans le temps, au pas du mois, chaque point portant le cumul à la fin du mois.

- **Budget de référence** : à chaque date, celui de la révision de référence en vigueur à cette date, lu sur ses propres dates. Chaque [avenant](notions/avenant-et-differentiel.md) y fait une marche, datée et tracée en travers : ce n’est pas une dérive, c’est un événement du contrat. Il atteint le budget de référence à la fin de la référence.
- **Coût réel** : cumulé selon les dates de pièce, jusqu’à la date de calcul ; il monte par marches.
- **Projection du chef de projet** : au-delà, le [reste à engager](notions/reste-a-engager.md) de chaque ligne étalé sur la part de la durée de sa tâche qui suit la date de calcul, ou porté entier à la date de calcul quand la fin de la tâche est dépassée.

Décalée des délais de paiement, la courbe devient **Décaissements** : chaque montant est décalé du délai de paiement de sa ligne, les provisions des risques identifiés restant à la date de leur tâche ; le coût réel ne se décale pas. La table **Décaissements par mois** donne alors, mois par mois, le **Décaissé** et ce qui reste **À décaisser**.

Quand rien ne relève de la maille lue — un sous-projet sans ligne ni coût réel —, la section le dit au lieu de tracer un zéro ; une courbe seule sans point est nommée sous le graphique.

## Ses commandes

- **Décaler des délais de paiement** présente la courbe en décaissements ; **Retirer le décalage des délais de paiement** la ramène. Quand il n’y a rien à tracer, seule la seconde reste offerte, pour sortir du décalage.
- **Exporter en PNG** enregistre la courbe en image, avec le projet, la révision et la date de calcul, et le sous-projet quand le bandeau en filtre un.
- **Valeurs du graphique** déplie ses points en table.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur, le décalage compris : rien n’est sommé ni décalé dans le navigateur. La table des valeurs donne, pour chaque point, la **Courbe**, la **Date** et le **Montant** ; les **Marches du budget de référence**, leur **Date**, leur **Motif** et le **Montant de la marche**, signé.

## Les gestes au clavier

- `Tab` atteint les commandes de la section et **Valeurs du graphique** ; une table plus large que la fenêtre défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Les indicateurs projets](FBS-4.8.md), [les courbes de valeur acquise](FBS-4.8.8.md), [la projection à terminaison](FBS-4.8.2.md) ;
- [la courbe en S du portefeuille](FBS-2.6.md), [le devis](FBS-4.4.md), où se saisit le délai de paiement d’une ligne ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [l’avenant et le différentiel](notions/avenant-et-differentiel.md), [la provision et la réserve](notions/provision-et-reserve.md).

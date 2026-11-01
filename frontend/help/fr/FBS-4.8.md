# Indicateurs projets

## Ce que montre l’écran

Ce pour quoi tout le reste existe : la mise en relation du [budget de référence](notions/budget-de-reference.md), de la [valeur planifiée](notions/valeur-planifiee.md), de la [valeur acquise](notions/valeur-acquise.md) et du coût réel, avec le [reste à engager](notions/reste-a-engager.md) du chef de projet. Tout y est calculé par le serveur, pour la révision lue et à une date : celle du marquage pour une [révision marquée](notions/revisions.md), dont les indicateurs et les courbes sont conservés tels qu’ils étaient, le jour courant pour la révision en cours.

De haut en bas :

- cinq cartes, chacune avec sa date de calcul : l’[avancement financier](FBS-4.8.1.md), la [projection à terminaison](FBS-4.8.2.md), l’[avancement physique](FBS-4.8.3.md), l’[indicateur de coûts](FBS-4.8.4.md) et l’[indicateur de délais](FBS-4.8.5.md), ces deux derniers avec l’évolution de leur indice ;
- le [suivi des jalons](FBS-4.8.6.md), le diagramme temps/temps ;
- les [coûts cumulés](FBS-4.8.7.md), la courbe en S ;
- les [courbes de valeur acquise](FBS-4.8.8.md).

Les indicateurs ne se calculent qu’à partir de l’état En cours : avant, l’écran dit « Indicateurs indisponibles », sans cartes ni courbes, et seul le suivi des jalons reste ; seuls les indicateurs du [devis](FBS-4.4.1.md) existent alors.

Le bandeau dit le contexte de lecture et ses filtres. Un sous-projet filtré restreint tout l’écran sauf le suivi des jalons, qui porte sur le projet entier : un sous-projet n’a pas de jalons ; le bandeau le dit sur le filtre. Un sous-projet que le projet n’a pas est refusé : « Indicateurs indisponibles ». Une date de calcul filtrée montre les indicateurs et les courbes de la dernière révision marquée à cette date ou avant, tels qu’ils ont été conservés à son marquage ; le bandeau nomme cette **Révision du calcul** quand ce n’est pas celle de l’adresse. L’évolution des indices est toujours calculée au jour courant, sur la révision en cours : quand ce n’est pas la révision des indicateurs, l’écran le dit en tête, « Calculé sur une autre révision ».

## Ses commandes

- Dans le bandeau, chaque filtre se lève par son lien, **Lever le filtre**.
- **Décaler des délais de paiement**, au-dessus des coûts cumulés, les présente en décaissements ; **Retirer le décalage des délais de paiement** les ramène. Le décalage se garde dans l’adresse.
- **Exporter en PNG** enregistre le diagramme temps/temps, la courbe en S ou les courbes de valeur acquise en image, avec le projet, la révision et la date de calcul ; quand l’écran filtre un sous-projet, l’image le nomme, ou dit, pour le suivi des jalons, qu’elle porte sur le projet entier.
- **Valeurs du graphique** déplie, sous chaque graphique, ses valeurs en table.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur ; le front n’en recalcule, n’en somme ni n’en décale aucune. Un indicateur dont une grandeur est nulle au dénominateur est dit **Non calculable**, avec sa raison, jamais zéro ni infini. Tout ce qui est monétaire se calcule pour le projet et pour chacun de ses sous-projets, l’ensemble « hors sous-projet » compris. Une zone se lit par son signal, son texte et son icône, jamais par la seule couleur.

Les courbes montrent des sauts, qui se lisent comme tels : le budget de référence change à chaque [avenant](notions/avenant-et-differentiel.md), et à rien d’autre.

## Les gestes au clavier

- `Tab` parcourt les filtres du bandeau, les commandes, les graphiques et leurs valeurs ; une table de valeurs plus large que la fenêtre défile au clavier.
- `F1` ouvre cette aide.

## Voir aussi

- [Le devis](FBS-4.4.md), [le reste à engager](FBS-4.5.md), [les coûts réels](FBS-4.7.md), d’où viennent les grandeurs ;
- [les paramètres d’indicateurs](FBS-3.4.md), où se règlent les seuils des zones, et [la performance du portefeuille](FBS-2.3.md) ;
- les notions : [la valeur acquise](notions/valeur-acquise.md), [la valeur planifiée](notions/valeur-planifiee.md), [les indices](notions/indices.md), [le budget de référence](notions/budget-de-reference.md), [les révisions](notions/revisions.md).

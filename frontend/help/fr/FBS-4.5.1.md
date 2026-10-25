# Indicateurs du reste à engager

## Ce que montre l’écran

Les cartes au-dessus de la grille du [reste à engager](FBS-4.5.md), telles que le serveur les calcule pour la révision lue, chacune avec sa date de calcul. Elles portent sur le projet entier : le filtre de sous-projet du bandeau et le filtre par lot ou par poste ne restreignent que la grille.

- **Reste à engager** : le total général de ce qu’il reste à dépenser.
- **Marge sur le budget de référence** : la projection du chef de projet — le coût réel plus le reste à engager — moins le [budget de référence](notions/budget-de-reference.md). Elle est signée dans le sens de la dérive : positive, le projet coûte plus que prévu. Absente sur un projet sans révision de référence.
- **Écart à la revue précédente** : le reste à engager moins celui de la révision marquée précédente, quand celle-ci a été marquée à l’état En cours ; absent plutôt que nul sinon. Positif, la revue a fait monter la dépense restante.
- **Par nature de coût** : le reste à engager de chaque nature, avec sa part.
- **Reste à engager par sous-projet, et marge sur le budget** : pour chaque sous-projet, et pour l’ensemble « hors sous-projet », son reste à engager et l’écart entre la somme de son coût réel et de son reste à engager et son budget, avec le signal de la zone que le serveur donne : un sous-projet dont le budget est dépassé est signalé. Les sous-projets s’additionnent au total du projet.
- **Couverture des risques** : la réserve pour risques de la référence, les provisions restantes, le coût des risques survenus, et l’écart de couverture.

Quand l’API ne trouve pas les indicateurs, l’écran les dit indisponibles et montre le reste.

## Ses commandes

Les cartes n’ont pas de commande : elles se lisent.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur ; le front n’en recalcule aucune. Un signal se lit par son texte et son icône, jamais par sa seule couleur.

## Les gestes au clavier

Les cartes se lisent dans l’ordre de la page, avant la grille.

## Voir aussi

- [Le reste à engager](FBS-4.5.md) et [sa grille](FBS-4.5.2.md) ;
- [les indicateurs du devis](FBS-4.4.1.md), [les provisions des risques](FBS-4.6.2.md) ;
- les notions : [le reste à engager et le devis actualisé](notions/reste-a-engager.md), [le budget de référence](notions/budget-de-reference.md), [la provision et la réserve](notions/provision-et-reserve.md).

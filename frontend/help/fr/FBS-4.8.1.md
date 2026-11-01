# Avancement financier

## Ce que montre l’écran

La première carte des [indicateurs projets](FBS-4.8.md), avec sa date de calcul : où en est la dépense par rapport à ce qu’elle finira par être.

- **Avancement financier** : le coût réel rapporté à la somme du coût réel et du [reste à engager](notions/reste-a-engager.md), en pourcentage. Non calculable quand le coût réel et le reste à engager sont tous deux nuls.
- **Consommation du budget** : le même coût réel rapporté au [budget de référence](notions/budget-de-reference.md), en pourcentage.
- Les grandeurs dont ils se déduisent : **Coût réel**, **Reste à engager** et **Budget de référence**.

Les deux pourcentages se lisent ensemble : ils disent si l’on dépense vite, et si l’on dépense trop. Un avancement financier de 50 % avec une consommation de 70 % annonce un dépassement de 40 %. C’est le seul indicateur qui ne dépende pas de la valeur acquise.

## Ses commandes

La carte n’a pas de commande : elle se lit, pour le projet ou pour le sous-projet que le bandeau filtre.

## Ses colonnes et ses valeurs calculées

Toutes les valeurs sont calculées par le serveur. Le coût réel est celui des lignes du périmètre suivi dont la date de pièce précède la date de calcul ou l’égale ; une ligne exclue des [coûts réels](FBS-4.7.md) n’entre pas dans le calcul du jour. Les indicateurs conservés d’une révision marquée gardent les lignes connues à son marquage, avec le montant et le périmètre qu’elles avaient alors : une ligne importée, mise à jour ou exclue ensuite ne les change pas. Une valeur non calculable le dit, avec sa raison, et ne vaut jamais zéro.

## Les gestes au clavier

Les cartes se lisent dans l’ordre de la page, avant les graphiques.

## Voir aussi

- [Les indicateurs projets](FBS-4.8.md) et [la projection à terminaison](FBS-4.8.2.md), qui part des mêmes grandeurs ;
- [le reste à engager](FBS-4.5.md), [les coûts réels](FBS-4.7.md) ;
- les notions : [le reste à engager](notions/reste-a-engager.md), [le budget de référence](notions/budget-de-reference.md).

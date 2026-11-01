# Probabilité de gain

## Ce que montre l’écran

La **Probabilité de gain** du projet, parmi les paramètres du projet, sur l’écran des [paramètres du projet](FBS-4.2.md). Une offre en chiffrage n’est pas encore un projet : elle peut ne jamais se faire. La probabilité de gain est le poids que le chef de projet donne à son offre, et c’est par elle que le portefeuille et le plan de charge agrégé comptent un projet en chiffrage pour ce qu’il vaut, plutôt que pour tout ou rien.

Elle vaut 0 % par défaut : une offre ne pèse rien tant que personne ne l’a estimée. Elle n’intervient dans aucun calcul propre au projet — ni le devis, ni le budget, ni aucun indicateur — et n’a plus d’effet à partir de l’état En cours, où le projet compte pour tout, ni dans les états terminaux.

## Ses commandes

- **Modifier le projet** ouvre le formulaire des paramètres, où le champ **Probabilité de gain (%)** se saisit en pourcentage, entre 0 et 100 ; une valeur hors de ces bornes est refusée à son champ, avec la borne.
- La probabilité se modifie tant que le projet est à l’état Créé ou Chiffrage. À partir de l’état En cours, le champ est montré figé, et la condition qui lui manque se lit dessous (« projet non encore en cours ») ; si l’état a changé pendant que le formulaire était ouvert, le refus le dit sous le formulaire.

## Ses colonnes et ses valeurs calculées

La probabilité s’affiche telle que le serveur la tient, en pourcentage. Dans le [portefeuille](FBS-2.1.md), le **Pipeline pondéré** est la somme des devis courants des projets en chiffrage, chacun pondéré par sa probabilité ; le pipeline brut ne l’est pas.

## Les gestes au clavier

- `Tab` atteint **Modifier le projet** ; dans le formulaire, `Tab` parcourt les champs et `Entrée` enregistre.
- `Échap` ferme le formulaire sans rien enregistrer.
- `F1` ouvre cette aide.

## Voir aussi

- [Les paramètres du projet](FBS-4.2.md), [le cycle de vie du projet](FBS-4.9.md) ;
- [le portefeuille de projets](FBS-2.1.md) et [le plan de charge agrégé](FBS-2.2.md), qui pondèrent par elle les projets en chiffrage.

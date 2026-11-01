# Taux d’inflation

## Ce que montre l’écran

Le **Taux d’inflation annuel** du projet, parmi les paramètres du projet, sur l’écran des [paramètres du projet](FBS-4.2.md). Le chiffrage n’emploie que les taux horaires de l’année de référence de la révision ; le taux d’inflation est l’hypothèse qui les projette sur les années suivantes, dont les taux ne sont pas encore connus.

Il vaut 0 % par défaut et se modifie à tout moment, tant que le projet n’est pas terminal. Sa modification ne touche aucune révision marquée, dont le budget de référence est figé : elle s’applique à la révision en cours, pour les lignes dont l’année de consommation suit l’année de référence.

## Ses commandes

- **Modifier le projet** ouvre le formulaire des paramètres, où le champ **Taux d’inflation annuel (%)** se saisit en pourcentage : « 3 » pour 3 %. Le serveur le garde entre 0 et 100 % ; un taux hors de ces bornes est refusé à son champ, avec la borne. La commande est celle des chefs de projet, et un projet terminal ne l’offre pas.

## Ses colonnes et ses valeurs calculées

Le taux s’affiche tel que le serveur le tient, en pourcentage. Au devis, le **Montant réestimé** d’une ligne en dépend : c’est le montant de l’année de référence projeté sur l’année de consommation de la ligne, à ce taux ; l’infobulle de la colonne nomme l’année de référence et le taux de la révision quand l’écran les connaît.

## Les gestes au clavier

- `Tab` atteint **Modifier le projet** ; dans le formulaire, `Tab` parcourt les champs et `Entrée` enregistre.
- `Échap` ferme le formulaire sans rien enregistrer.
- `F1` ouvre cette aide.

## Voir aussi

- [Les paramètres du projet](FBS-4.2.md) ;
- [le devis](FBS-4.4.md) et [le montant à l’année de référence](FBS-4.4.3.md) ;
- [les taux horaires](FBS-3.1.2.md) du référentiel ;
- la notion : [le budget de référence](notions/budget-de-reference.md).

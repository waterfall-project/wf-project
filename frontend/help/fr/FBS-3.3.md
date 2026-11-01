# Paramètres de risques

## Ce que montre l’écran

La matrice de risques de l’installation, commune à tous les projets, hors de tout projet. Deux tables :

- **Bornes de la matrice de risques** : sur l’axe de la probabilité, trois bornes en pourcentage ; sur celui de la gravité, trois bornes en pourcentage de l’assiette du projet — son budget de référence ou, tant qu’il n’en a pas, le total hors provisions du devis de sa révision courante. Les trois bornes d’un axe y délimitent quatre niveaux ; une valeur égale à une borne relève du niveau supérieur.
- **Zones de la matrice de risques** : les seize cases, une ligne par niveau de probabilité, du plus haut au plus bas, une colonne par niveau de gravité, chaque case avec sa zone — **Nominal**, **Vigilance** ou **Alerte**.

Une révision ne conserve pas ces paramètres : une révision marquée se lit toujours avec leurs valeurs courantes, et seule la zone qui qualifie un risque peut en changer.

## Ses commandes

**Modifier la matrice de risques**, offerte à qui peut modifier les paramètres de risques, ouvre le formulaire : les trois bornes de chaque axe, en pourcentage, strictement croissantes, et la zone de chacune des seize cases. Une borne qui n’est pas au-dessus de la précédente est signalée à son champ avant l’envoi ; le serveur juge le reste. Si les paramètres ont changé depuis leur lecture, le refus offre de relire la page. Aux autres, l’écran se lit.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : bornes et zones sont celles que tient le serveur. Une zone se lit par son signal et son nom, jamais par la seule couleur.

## Les gestes au clavier

- `Tab` parcourt la commande, puis, dans le formulaire, les bornes et les zones, ligne par ligne ; `Échap` ferme le formulaire sans rien enregistrer.
- `F1` ouvre cette aide.

## Voir aussi

- [La gestion des risques](FBS-4.6.md), dont la matrice place chaque risque, et [les risques du portefeuille](FBS-2.5.md) ;
- la notion : [la provision et la réserve](notions/provision-et-reserve.md).

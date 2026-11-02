# Paramètres d’indicateurs

## Ce que montre l’écran

Les paramètres des indicateurs de l’installation, communs à tous les projets, hors de tout projet :

- **Seuils d’alerte des indices** : pour l’indice de coût et pour l’indice de délai, un **Seuil de vigilance** et un **Seuil d’alerte**, valeurs de l’indice inférieures à 1. Un indice supérieur ou égal au seuil de vigilance est nominal ; sous lui et au moins égal au seuil d’alerte, en vigilance ; sous le seuil d’alerte, en alerte.
- **Rythme des revues** : le délai maximal attendu, en semaines, entre deux révisions marquées d’un projet en cours. Un projet dont la dernière révision marquée est plus ancienne est signalé par la santé du pilotage.

Une révision ne conserve pas ces paramètres : une révision marquée se lit toujours avec leurs valeurs courantes. Ses indicateurs conservés ne changent pas ; seule la zone qui les qualifie peut changer.

## Ses commandes

**Modifier les seuils et le délai**, offerte à qui peut modifier les paramètres d’indicateurs, ouvre le formulaire : chaque seuil entre 0 et 1, exclus, le seuil d’alerte sous le seuil de vigilance de son indice, et le délai en semaines entières. Un seuil d’alerte qui n’est pas sous le seuil de vigilance est signalé à son champ avant l’envoi ; le serveur juge le reste. Si les paramètres ont changé depuis leur lecture, le refus offre de relire la page. Aux autres, l’écran se lit.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule ici : les seuils et le délai sont ceux que tient le serveur, qui classe chaque indice dans sa zone.

## Les gestes au clavier

- `Tab` parcourt la commande, puis, dans le formulaire, les seuils et le délai ; `Échap` ferme le formulaire sans rien enregistrer.
- `F1` ouvre cette aide.

## Voir aussi

- [La santé du pilotage](FBS-2.7.md), qui signale les revues en retard, et [la performance du portefeuille](FBS-2.3.md) ;
- la notion : [les indices de coût et de délai](notions/indices.md).

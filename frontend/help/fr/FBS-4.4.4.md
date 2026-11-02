# Plan de charge du projet

## Ce que montre l’écran

Une feuille du [chiffrage](FBS-4.4.md), que l’écran du devis ouvre dans le même contexte : le devis traduit en besoin de ressources — combien d’heures, de quel rôle, quel mois. C’est la vue que le manager consolide ensuite sur plusieurs projets, dans le [plan de charge agrégé](FBS-2.2.md).

La **Charge par rôle et par mois** : une barre par mois, empilée par rôle de ressource, le total du mois à son sommet ; la légende nomme les rôles, et l’infobulle d’un mois les liste avec leurs heures. Seules les lignes de main-d’œuvre chargent. La charge d’une ligne se répartit sur la durée de sa tâche, au prorata des heures travaillées du calendrier de son rôle. Sur une base de reste à engager, la charge restante d’une tâche non terminée se répartit sur la seule part de sa durée qui suit la date de calcul, et se porte au mois de la date de calcul quand la fin de la tâche est dépassée.

Sous le choix, la base et la révision que le serveur dit avoir lues.

## Ses commandes

En tête du plan, puis **Afficher** :

- **Base** : **Budget de la révision de référence**, **Reste à engager d’une révision marquée** ou **Reste à engager de la révision en cours**. Seules les bases que le projet admet sont offertes : sans révision de référence, la révision en cours seule ; les révisions marquées, quand le projet en a une.
- **Révision marquée**, pour la base d’une révision marquée : chacune de celles du projet.
- **Nœud d’organisation et ses descendants** restreint le plan aux rôles qui en relèvent ; **Tous les nœuds** le lève.

Une base que le serveur refuse — un projet sans révision de référence, une révision marquée qui manque ou ne l’est pas — se dit indisponible, avec sa raison, et le reste de l’écran se montre.

Sur le graphique :

- **Valeurs du graphique**, sous le graphique, déplie la table de ses valeurs ;
- **Exporter en PNG** enregistre le graphique, avec le projet, la révision, la base, le nœud et la date de calcul.

## Ses colonnes et ses valeurs calculées

Tout chiffre est celui du serveur : les heures de chaque rôle et le total de chaque mois. La table des valeurs donne, pour chaque rôle et chaque mois, la **Charge (h)**, la **Capacité (h par mois)** du rôle et la **Zone** du mois : en alerte quand la charge dépasse la capacité, nominale sinon, dite par son signal et jamais par la seule couleur. Un rôle sans charge y figure aussi. Le plan d’un projet ne présente aucun taux de charge — la capacité est celle de toute l’installation — et ne dessine pas la capacité : le taux de charge est celui du plan agrégé.

## Les gestes au clavier

- `Tab` parcourt le choix de la base, de la révision et du nœud, **Afficher**, puis les commandes du graphique ; `Entrée` sur **Valeurs du graphique** déplie ou replie la table.
- La table des valeurs, quand elle dépasse sa boîte, défile aux flèches une fois atteinte.
- `F1` ouvre cette aide.

## Voir aussi

- [Le chiffrage et le devis](FBS-4.4.md), dont les lignes de main-d’œuvre font la charge, et [le reste à engager](FBS-4.5.md) ;
- [le plan de charge agrégé](FBS-2.2.md) et [les rôles de ressources](FBS-3.2.2.md), qui portent la capacité ;
- les notions : [le budget de référence](notions/budget-de-reference.md), [le reste à engager](notions/reste-a-engager.md).

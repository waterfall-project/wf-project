# Paramètres de projets

## Ce que montre l’écran

Ce qu’un projet porte en propre, hors de ses révisions. Un projet porte peu de paramètres, et aucun n’est bloquant : le lotissement a une valeur par défaut, le taux d’inflation vaut zéro, les codes viennent de l’ERP quand la commande arrive. C’est ce qui permet de créer un projet et de commencer à chiffrer sans rien avoir décidé.

Sous le titre, l’état du projet. Puis, de haut en bas :

- les **Paramètres du projet** : son libellé, son code, son client, la date de réception de sa commande, sa description, son [taux d’inflation](FBS-4.2.2.md) et sa [probabilité de gain](FBS-4.2.5.md) ; une valeur qui manque se dit « Non renseigné » ;
- le [lotissement](FBS-4.2.1.md) : les lots, les postes et les livrables de la commande, en arbre ;
- les [sous-projets](FBS-4.2.3.md), chacun par le code que lui donne l’ERP ;
- les [contributeurs](FBS-4.2.4.md), qui travaillent sur cette affaire, chacun avec sa qualité.

Chaque liste tient sa propre recherche, ses filtres et son tri, que le serveur applique, et ses réglages de colonnes. Une liste ne se dit vide que quand rien ne la restreint : une recherche ou un filtre qui ne retient rien garde sa grille, pour être changé.

## Ses commandes

Les paramètres du projet sont ceux de ses chefs de projet : chaque commande suit ce que le projet offre, disponible ou nommant la condition qui lui manque. Un projet terminal n’en offre aucune.

- **Modifier le projet** ouvre le formulaire des paramètres : le libellé, le code projet, le client, la description, la date de réception de la commande, le taux d’inflation et la probabilité de gain, ces deux derniers en pourcentage. La probabilité de gain ne se modifie plus à partir de l’état En cours : le champ est alors montré figé, avec sa condition. Un code que porte un autre projet est refusé à son champ ; un taux hors de ses bornes aussi, avec la borne.
- Les commandes du lotissement, des sous-projets et des contributeurs sont décrites dans l’aide de chaque liste.
- **Engendrer le planning**, sous le lotissement, quand la structure principale de la révision en cours n’a encore aucune tâche : une récapitulative par lot et par poste, une tâche par livrable et leurs jalons de fin. Engendré, l’écran mène à la grille de planning.

Pendant qu’une écriture est en route, la commande qui rouvrirait son formulaire attend, inactive, « Enregistrement en cours… » : le formulaire se rouvre sur la version que la réponse apporte. Si le projet a changé depuis sa lecture, le refus offre de relire la page.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule ici : les listes montrent ce que le serveur tient, dans l’ordre qu’il donne. Les définitions des colonnes des trois listes suivent.

## Les gestes au clavier

- Chaque liste est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur une commande d’une cellule la presse ; `Maj+F10` ou la touche Menu ouvre le menu d’une cellule du lotissement.
- Sur un en-tête, `Entrée` ou `Espace` trie la liste par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Dans le lotissement, `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [Le lotissement](FBS-4.2.1.md), [le taux d’inflation](FBS-4.2.2.md), [les sous-projets](FBS-4.2.3.md), [les contributeurs](FBS-4.2.4.md), [la probabilité de gain](FBS-4.2.5.md) ;
- [la page du projet et la liste des projets](FBS-4.md), [le cycle de vie du projet](FBS-4.9.md) ;
- la notion : [le lotissement](notions/lotissement.md).

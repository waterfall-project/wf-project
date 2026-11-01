# Lotissement du projet

## Ce que montre l’écran

La première liste des [paramètres du projet](FBS-4.2.md) : le découpage du bon de commande en lots, chaque lot en postes, chaque poste en livrables, en arbre, dans l’ordre de la saisie. Le lotissement ne conditionne ni le chiffrage ni le pilotage, qui se font sans lui ; sa saisie est facultative, et sans elle il vaut un lot et un poste au libellé du projet, sans livrable.

Il rend deux services. Il permet d’**engendrer le planning** une fois, sans ressaisir la structure de l’affaire : une récapitulative par lot et par poste, rattachée à lui, une tâche d’un jour par livrable, un jalon de fin par poste et par lot. Et ce [rattachement](notions/lotissement.md) fait du lotissement une grille de lecture : filtrer le planning ou le devis sur un lot ou un poste, c’est filtrer le sous-arbre de la tâche qui le porte. Le squelette n’a pas de lien durable : renommer un poste ne renomme pas sa tâche.

Une recherche ou un filtre retient des éléments : l’arbre les montre avec les lots et les postes qui les contiennent, sans le reste, et le dit au-dessus de la grille.

## Ses commandes

Les commandes de saisie suivent **Saisir le lotissement**, que le projet offre à ses chefs de projet. Indisponibles, elles restent présentées et disent ce qui leur manque : un projet terminal, ou un traitement de fond en cours qui écrit dans la révision en cours ou la fige (« aucun traitement de fond en cours sur l’objet »).

- **Nouveau lot**, dans la barre de la grille, ajoute un lot à la fin ;
- **Ajouter un poste** sur un lot, **Ajouter un livrable** sur un poste, dans le menu d’une cellule ou dans la barre, pour la ligne de la cellule active ;
- **Renommer** change le libellé de l’élément ; chaque lot, poste et livrable porte un libellé ;
- **Supprimer**, après confirmation, retire l’élément avec ce qu’il contient. Les tâches de la révision en cours qui portent un lot ou un poste supprimé restent, et perdent leur rattachement ; les révisions marquées le gardent.

Le lotissement s’enregistre entier, à chaque geste, depuis sa dernière lecture entière : saisi sous un filtre, il part de la lecture entière que l’écran fait à côté. Un refus qui vise le libellé saisi se dit à son champ ; un refus qui vise un autre élément le nomme, par sa nature et son libellé ; si le lotissement a changé depuis sa lecture, le refus offre de relire la page. Pendant une écriture, les commandes attendent sa réponse.

Au-dessus de la grille, pour tous : **Filtrer par nature** retient les lots, les postes ou les livrables, **Toutes les natures** lève le filtre ; le champ de recherche retient les éléments dont le libellé contient le texte saisi ; **Colonnes** ; **Arbre** plie et déplie.

Sous la grille, **Engendrer le planning**, offert tant que la structure principale de la révision en cours n’a aucune tâche (« structure principale sans aucune tâche ») et à qui peut modifier le planning. Un projet sans révision ouvre d’abord sa révision en cours, puis engendre. Engendré, l’écran mène à la [grille de planning](FBS-4.3.2.md).

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : l’arbre ne se trie pas, son ordre est celui de la saisie. Les [indicateurs du devis](FBS-4.4.1.md) totalisent chaque lot par la tâche qui le porte ; un lot qu’aucune tâche ne porte y est présenté sans total.

## Les gestes au clavier

- L’arbre est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Maj+F10` ou la touche Menu ouvre le menu de la cellule active.
- `Alt` et `-` plie la ligne, `Alt` et `+` la déplie, `Alt` et `*` déplie tout.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj` ; **Arbre** plie et déplie là où les touches de pliage ne répondent pas.
- `F1` ouvre cette aide.

## Voir aussi

- [Les paramètres du projet](FBS-4.2.md), [la planification](FBS-4.3.md), où le filtre **Lot ou poste** se lit, et [le devis](FBS-4.4.md) ;
- la notion : [le lotissement](notions/lotissement.md).

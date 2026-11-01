# Kanban — démarrage des tâches

## Ce que montre l’écran

Une feuille de l’[estimation du reste à engager](FBS-4.5.md), atteinte depuis son en-tête, dans le même contexte : la vue par laquelle le chef de projet déclare qu’une tâche a commencé. Ce geste n’a pas d’autre effet que d’exposer les lignes de la tâche à la réestimation, dans la grille de reste à engager de la même révision ; une tâche qui porte des lignes peut aussi s’y réestimer avant même de démarrer, par **Saisir le reste à engager**. Une tâche est démarrée ou ne l’est pas : aucun pourcentage ne se montre ni ne se saisit.

Trois colonnes, dans l’ordre que donne le serveur : **Non démarrées**, **Démarrées**, **Terminées**. Chaque tâche de la structure principale de la révision en cours est une carte : son numéro de ligne et son libellé, sa fin, et **Fin dépassée** quand elle précède la date de calcul ; terminée, la date où elle l’a été. Un jalon non démarré dont tous les prédécesseurs sont terminés porte « jalon à terminer », par un texte et une icône, pour inviter à le terminer : rien ne se termine seul.

Le Kanban lit la révision en cours d’élaboration, quelle que soit la révision du contexte : sur une révision marquée, qui n’a aucune tâche à démarrer, il le dit et ne montre rien.

## Ses commandes

Chaque carte fait les gestes que sa tâche offre, et seulement ceux-là, par son menu, en la glissant vers une colonne, ou au clavier :

- **Démarrer** une tâche non démarrée qui n’est pas un jalon : un jalon ne démarre jamais. Les prédécesseurs n’en sont pas une condition.
- **Terminer** une tâche qui ne porte aucune ligne hors provision : un jalon, même non démarré — il prend alors pour date de démarrage celle de sa terminaison —, ou une tâche démarrée. Une tâche non démarrée qui n’est pas un jalon n’est pas terminée directement (« la tâche est un jalon »).
- **Rouvrir** une tâche terminée : elle redevient démarrée ; un jalon redevient non démarré, ses dates effacées.
- **Saisir le reste à engager**, sur une tâche non terminée qui porte une ligne hors provision, mène à la grille du reste à engager sur cette tâche : c’est là qu’elle se termine, par un reste à engager nul sur toutes ses lignes.

Démarrer et terminer demandent la **Date de l’événement**, celle du jour par défaut ; une seule date se demande à la fois. Tous les gestes demandent un projet En cours et aucun traitement de fond en cours sur la révision. Un geste indisponible dit sa condition sur la carte, comme un geste qu’aucune règle ne mène vers la colonne visée ; un refus du serveur se dit sur la carte.

## Ses colonnes et ses valeurs calculées

Les colonnes sont les états de la tâche, tels que le serveur les donne : l’écran ne déduit aucun geste de la nature d’une tâche ni de ses lignes. La fin et la marque de fin dépassée sont celles du serveur. Une carte déplacée dit « Mise à jour… » pendant que les tâches se relisent ; si la relecture s’achève sans sa réponse, elle dit **Non à jour**, et **Réessayer** relit ses tâches.

## Les gestes au clavier

- Les flèches choisissent une carte, d’une carte à l’autre et d’une colonne à l’autre.
- `Entrée` ouvre le menu des gestes de la carte choisie.
- `Maj+→` et `Maj+←` la déplacent vers la colonne voisine, comme le glisser ; le focus la suit dans sa nouvelle colonne.
- Sur un Mac, `⇧` tient lieu de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [L’estimation du reste à engager](FBS-4.5.md) et [la grille de reste à engager](FBS-4.5.2.md), où se réestiment les lignes des tâches, démarrées ou non ;
- [la grille de planning](FBS-4.3.2.md), où se lisent les dates de démarrage et de terminaison ;
- la notion : [le reste à engager](notions/reste-a-engager.md).

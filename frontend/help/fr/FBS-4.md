# Projets

## Ce que montre l’écran

L’accueil de Waterfall : la liste des projets, d’où s’ouvre chacun. Un projet porte tout ce qu’on y fait, de sa création à sa clôture — ses révisions, ses paramètres, son planning, son devis, son reste à engager, ses risques, ses coûts réels, ses indicateurs. Ce qui s’y modifie dépend de son état : une révision marquée ne bouge plus, un projet terminal non plus.

La liste s’ouvre sur les projets dont vous êtes contributeur, à l’état **Chiffrage** ou **En cours** : deux filtres que l’écran dit, au-dessus de la liste, tant qu’ils s’appliquent. Le serveur filtre, trie, cherche et pagine ; le pied de la liste dit combien de projets il retient. Au-dessus, quand le référentiel commun n’a pas encore le minimum qu’un projet demande, l’encart **Référentiel incomplet** nomme ce qui manque : aucun projet ne se crée avant.

**La page d’un projet**, que son libellé ouvre, ouvre aussi cette aide. Sous le bandeau de son contexte de lecture, elle dit ce qu’est le projet — son code, son état, la date de réception de sa commande, sa description — et liste ses révisions, chacune un lien qui l’ouvre dans le même contexte. Un projet sans révision le dit et mène, à qui peut les lire, à la [gestion des révisions](FBS-4.1.md) ; il offre alors aussi ses imports, puisqu’un import crée la révision à laquelle il s’applique. Tant que la structure principale de la révision en cours n’a aucune tâche, l’encart **Démarrer le projet** propose de lancer le planning.

## Ses commandes

En tête de la liste :

- **Créer un projet**, offerte à qui en a la permission, ouvre le formulaire : le **Libellé**, obligatoire, le **Code projet**, qui peut attendre la commande, le **Client** et la **Description**, facultatifs. Le projet naît à l’état Créé, et vous en êtes chef de projet. Indisponible tant que le référentiel est incomplet. Un code que porte déjà un autre projet est refusé à son champ.
- **Voir tous les projets** lève le filtre « contributeur », à qui peut consulter tous les projets ; **N’afficher que mes projets** le remet. Aux autres, le filtre reste, sans lien : il ne restreint pas ce qu’ils peuvent lire, il dit ce que la liste montre.

Au-dessus de la liste :

- **Filtre par état** : un bouton par état, pressé quand il est retenu, et **Tous les états** pour les lever. Un choix d’états autre que celui par défaut se garde dans vos préférences.
- **Période de modification**, **Du** et **Au**, puis **Filtrer** : une fin qui précède le début est refusée à son champ, la liste non lue.
- Le champ de recherche retient les projets dont le libellé ou le code contient le texte saisi.
- **Colonnes** choisit les colonnes montrées ; **Lignes par page** et les liens de pages parcourent la liste.

Sur la page d’un projet, l’encart **Démarrer le projet**, offert à qui peut modifier le planning :

- **Planning automatique depuis le lotissement** mène au [lotissement du projet](FBS-4.2.1.md), où le planning s’engendre une fois le lotissement saisi ;
- **Importer un fichier MS Project** ouvre la zone de dépôt d’un fichier .xml : son compte rendu s’affiche sur la page, et s’applique ou s’abandonne comme aux [imports et exports](FBS-4.3.4.md) ;
- **Plus tard** replie l’encart ; **Démarrer le projet** le déplie, tant que la structure reste vide.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule ici : la liste montre les projets tels que le serveur les tient. La date de modification s’affiche à l’heure de votre poste. Le client d’un projet ne figure que sur ses paramètres, ni dans la liste ni dans le portefeuille.

## Les gestes au clavier

- La liste est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur le libellé d’un projet l’ouvre.
- Sur un en-tête, `Entrée` ou `Espace` trie la liste par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [La gestion des révisions](FBS-4.1.md), [les paramètres du projet](FBS-4.2.md), [le cycle de vie du projet](FBS-4.9.md) ;
- [le portefeuille de projets](FBS-2.1.md), qui consolide tous les projets ;
- les notions : [les révisions](notions/revisions.md), [le lotissement](notions/lotissement.md).

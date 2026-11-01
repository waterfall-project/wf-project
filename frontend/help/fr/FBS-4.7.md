# Coûts réels

## Ce que montre l’écran

Ce que le projet a dépensé, tel que l’ERP l’a enregistré. Les coûts réels ne sont pas produits par Waterfall : ils viennent d’une extraction périodique de l’ERP, qui s’importe aux [imports et exports](FBS-4.3.4.md). Ils appartiennent au projet, non à une révision : la révision du contexte ne sert qu’au bandeau.

Deux périmètres se rencontrent, qui ne coïncident jamais tout à fait. La comptabilité enregistre tout ce qui est imputé au projet ; le pilotage ne suit que ce qui a été budgété. Toute ligne importée est donc conservée, mais une ligne peut être exclue du **périmètre suivi** : elle reste consultable et n’entre dans aucun indicateur. Le rapprochement avec le budget se fait par sous-projet, que la ligne trouve dans son élément d’OTP ; une ligne imputée au seul projet rejoint l’ensemble « Hors sous-projet ».

De haut en bas :

- les **Totaux des lignes retenues** : le **Périmètre suivi**, l’**Exclu du périmètre suivi** et le **Total général**, et la date du **Dernier import** ;
- les filtres, puis la grille des lignes, une page à la fois, que le serveur trie, filtre et pagine ; son pied porte le total général des lignes retenues ;
- le **Journal des imports** : pour chacun, sa date, son auteur, la période extraite et le nombre de lignes créées, mises à jour, inchangées et rejetées.

## Ses commandes

- **Imports et exports**, en tête de l’écran, mène là où les coûts réels s’importent, dans le même contexte.
- **Périmètre** : **Toutes les lignes**, **Suivies** ou **Exclues** ; **Sous-projet**, un sous-projet du projet ou **Tous les sous-projets** ; **Période des pièces**, **Pièces du** et **Pièces jusqu’au**, puis **Filtrer**. Une période qui finit avant de commencer, ou un sous-projet que le projet n’a pas, est refusé à la place des lignes, les filtres gardés pour être changés.
- **Colonnes** choisit les colonnes montrées ; **Lignes par page**, **Lignes précédentes** et **Lignes suivantes** parcourent la liste ; **Imports plus récents** et **Imports plus anciens** parcourent le journal.
- Là où le projet offre **Exclure des lignes de coût**, le numéro de pièce d’une ligne est un lien qui l’ouvre : **Exclure du périmètre suivi**, avec un **Motif de l’exclusion** facultatif, ou **Réintégrer dans le périmètre suivi** ; **Fermer la ligne** la referme. Un projet terminal ne l’offre plus. L’exclusion se garde aux imports suivants, même quand une extraction rapporte la ligne.

## Ses colonnes et ses valeurs calculées

Tout chiffre est celui du serveur : les totaux portent sur toutes les lignes que les filtres retiennent, jamais sur la seule page. Les lignes s’ordonnent par défaut des pièces les plus récentes aux plus anciennes. Une ligne se désigne par sa pièce et son poste, deux postes d’une même pièce faisant deux lignes. Chaque colonne que la [correspondance de l’extraction](FBS-3.1.3.md) déclare conservée est une colonne de plus, sous le nom que le fichier lui donne ; elle se trie, mais n’entre dans aucun calcul.

## Les gestes au clavier

- La grille est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne, `Page préc.` et `Page suiv.` d’un écran.
- `Entrée` sur le numéro d’une ligne l’ouvre.
- Sur un en-tête, `Entrée` ou `Espace` trie la grille par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [Les imports et exports](FBS-4.3.4.md), où l’extraction s’importe, et [la correspondance de l’extraction des coûts réels](FBS-3.1.3.md) ;
- [les sous-projets](FBS-4.2.3.md), maille du rapprochement ;
- les notions : [la valeur acquise](notions/valeur-acquise.md), [les indices](notions/indices.md).

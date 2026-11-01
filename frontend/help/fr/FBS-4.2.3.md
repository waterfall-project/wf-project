# Sous-projets

## Ce que montre l’écran

Une liste des [paramètres du projet](FBS-4.2.md) : les sous-projets, chacun par le code sous lequel l’ERP le connaît, son libellé, et si des coûts réels lui sont imputés. Les codes viennent de l’ERP à la saisie de la commande : ils ne sont pas connus pendant le chiffrage, et leur saisie est facultative — un projet se chiffre sans sous-projet.

Le sous-projet est la maille des coûts réels : les pointages et les factures s’imputent sur un code de sous-projet, jamais sur une tâche. C’est donc là que le budget et la dépense se rejoignent, et que se calcule l’avancement financier. Une ligne de devis porte son sous-projet ; une ligne de coût le trouve dans son élément d’OTP.

## Ses commandes

Les commandes suivent **Modifier le projet**, que le projet offre à ses chefs de projet ; un projet terminal n’en offre aucune.

- **Nouveau sous-projet**, en tête de la liste, ouvre le formulaire : le code et le libellé, obligatoires. Le code est unique dans le projet, et il nomme l’onglet du sous-projet dans le fichier de reste à engager : au plus 31 caractères, sans `:`, `\`, `/`, `?`, `*`, `[` ni `]`, et ni « Synthèse » ni « Hors sous-projet ». Un code refusé l’est à son champ, avec son motif ; un code que porte déjà un autre sous-projet nomme celui-ci.
- **Modifier**, sur une ligne, ouvre le même formulaire sur le sous-projet.
- **Supprimer**, sur une ligne, après confirmation. Indisponible pour un sous-projet auquel des coûts réels sont imputés (« aucun coût réel imputé au sous-projet »), qu’une révision marquée cite (« sous-projet cité par aucune révision marquée »), ou que portent des lignes de devis de la révision en cours (« aucune ligne de devis de la révision en cours portant le sous-projet ») : la commande reste présentée, et son clic dit ce qui lui manque. Dans ce dernier cas seulement, un lien mène au devis de la révision en cours filtré sur le sous-projet, pour faire passer ses lignes ailleurs ; un refus du serveur nomme les lignes une à une.

Au-dessus de la liste, pour tous : **Coûts réels** retient **Avec coûts réels imputés** ou **Sans coût réel imputé**, **Tous les sous-projets** lève le filtre ; le champ de recherche retient les sous-projets dont le code ou le libellé contient le texte saisi ; **Colonnes**.

Ce qu’une écriture a fait se dit dans la région de la liste ; un refus de suppression, au-dessus d’elle. Pendant qu’une modification est en route, **Modifier** attend sa réponse sur cette ligne.

## Ses colonnes et ses valeurs calculées

Rien ne se calcule : chaque colonne se trie par le serveur, et le pied dit combien de sous-projets la liste retient.

## Les gestes au clavier

- La liste est un seul arrêt de tabulation : les flèches déplacent la cellule active, `Origine` et `Fin` le long de la ligne, `Ctrl+Origine` et `Ctrl+Fin` à la première et à la dernière ligne.
- `Entrée` sur **Modifier** ou **Supprimer** presse la commande.
- Sur un en-tête, `Entrée` ou `Espace` trie la liste par la colonne ; `Maj` et les flèches élargissent ou rétrécissent la colonne.
- Sur un Mac, `⌘` tient lieu de `Ctrl`, `⌥` de `Alt` et `⇧` de `Maj`.
- `F1` ouvre cette aide.

## Voir aussi

- [Les paramètres du projet](FBS-4.2.md) ;
- [le devis](FBS-4.4.md), dont chaque ligne porte un sous-projet, et [le reste à engager](FBS-4.5.md), dont le fichier range chaque sous-projet dans son onglet ;
- [les coûts réels](FBS-4.7.md), imputés par sous-projet.

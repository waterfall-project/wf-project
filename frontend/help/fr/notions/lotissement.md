# Le lotissement

## Ce que dit le glossaire

> **Lotissement** — Désigne le découpage contractuel de la commande en lots, postes et livrables. En l’absence de saisie, le lotissement se réduit à un lot comprenant un poste et aucun livrable.

> **Lot** — Désigne le premier niveau du lotissement. Un lot contient des postes.

> **Poste** — Désigne un ensemble de livrables au sein d’un lot du lotissement. À distinguer du poste qu’un rôle de ressource représente.

> **Livrable** — Désigne un élément livrable au client, au sein d’un poste.

> **Rattachement (au lotissement)** — Désigne le lien facultatif d’une tâche de la structure principale vers un lot ou un poste du lotissement, posé par le squelette ou à la main, qui permet de filtrer le planning et le devis par lot ou par poste et de totaliser le devis par lot. Un lot ou un poste n’est porté que par une tâche à la fois. À distinguer du rattachement d’un rôle de ressource à un nœud d’organisation.

> **Squelette de planning** — Désigne le planning engendré une fois à partir du lotissement : une récapitulative par lot et par poste, une feuille par livrable, un jalon de fin par poste et par lot.

## Dans Waterfall

Le lotissement reprend le bon de commande : il se saisit au [lotissement du projet](../FBS-4.2.1.md), et sa saisie est facultative. Sans elle, il vaut un lot et un poste qui portent le libellé du projet, sans livrable.

Dans la structure principale encore vide, **Engendrer le planning** en tire le squelette : une récapitulative par lot, une par poste sous celle de son lot, toutes deux rattachées à ce qu’elles représentent ; une tâche feuille d’un jour par livrable, en mode automatique ; un jalon de fin par poste, qui suit ses livrables, et un par lot, qui suit les jalons de ses postes. La commande est indisponible dès que la structure porte une tâche ; le planning se complète ensuite à la main.

Une tâche se rattache aussi à la main, depuis la [grille de planning](../FBS-4.3.2.md). Le filtre **Lot ou poste** du [planning](../FBS-4.3.md), du [devis](../FBS-4.4.md) et du [reste à engager](../FBS-4.5.md) retient alors la tâche qui porte le lot ou le poste, avec ses subordonnées et ses ancêtres, et le devis se totalise par lot.

## Voir aussi

- [Le lotissement du projet](../FBS-4.2.1.md), [la planification](../FBS-4.3.md) ;
- [le chemin critique et la marge totale](chemin-critique.md).

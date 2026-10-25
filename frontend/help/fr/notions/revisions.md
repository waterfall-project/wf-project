# Les révisions : en cours, marquée, de référence

## Ce que dit le glossaire

> **Révision** — Désigne un instantané complet d’un projet à un moment donné : ses structures de coûts et les valeurs du référentiel qu’elles emploient. Une révision porte un nom de version et une description. Elle est d’abord en cours d’élaboration, puis figée lorsqu’un utilisateur habilité la marque.

> **Révision marquée** — Désigne une révision figée par un utilisateur habilité. Elle n’est plus modifiable, par aucun moyen.

> **Révision de référence** — Désigne la révision marquée qui fait foi pour le budget de référence, la réserve pour risques, les dates contractuelles et la valeur planifiée. Ce caractère est un attribut de la révision : il passe à une nouvelle révision à chaque avenant contractualisé.

> **Révision courante** — Désigne la révision dans laquelle une grandeur est lue ou calculée : pour les indicateurs d’une révision marquée, cette révision ; au jour courant, la révision en cours d’élaboration lorsqu’il en existe une, sinon la dernière révision marquée. C’est elle que lisent le reste à engager, le devis courant, l’assiette du projet et le portefeuille au jour courant.

> **Revue périodique** — Désigne l’opération au cours de laquelle un utilisateur habilité met à jour le planning et le reste à engager de la révision en cours, réexamine les risques, importe les nouveaux coûts réels, puis marque la révision. Ces données permettent de mettre à jour les indicateurs du projet.

## Dans Waterfall

Un projet n’a jamais plus d’une révision en cours d’élaboration : c’est elle qui se saisit. La révision suivante n’est créée qu’à la demande — **Ouvrir une révision en cours**, sur l’écran des [révisions](../FBS-4.1.md) —, ou par la première saisie qui l’exige : un import, la saisie d’un risque, sa survenance, la fusion d’un différentiel. La copie de la dernière révision marquée a lieu alors, et non au marquage. Marquée, elle se fige : ses grilles se lisent sans se saisir, et le bandeau de chaque écran le dit. Les indicateurs d’une révision marquée sont conservés à la date de son marquage.

La révision de référence est une révision marquée que l’on désigne : elle fixe le [budget de référence](budget-de-reference.md) et la [valeur planifiée](valeur-planifiee.md). La désignation se corrige tant que le projet n’a reçu aucun coût réel et qu’aucune révision n’a été marquée depuis ; ensuite, seul un avenant contractualisé produit une nouvelle référence.

Chaque écran d’une révision dit dans son bandeau la révision qu’il lit ; le lien « Ouvrir » de l’historique en choisit une autre.

## Voir aussi

- [La gestion des révisions](../FBS-4.1.md) ;
- [le budget de référence](budget-de-reference.md), [la valeur planifiée](valeur-planifiee.md), [l’avenant et le différentiel](avenant-et-differentiel.md).

# La valeur planifiée

## Ce que dit le glossaire

> **Valeur planifiée** — Désigne la part du budget de référence qui aurait dû être acquise à une date donnée, d’après les dates de la révision de référence (WF-DEV-0080).

## Dans Waterfall

La valeur planifiée est la promesse étalée dans le temps : à chaque date, la part du [budget de référence](budget-de-reference.md) que le planning de la référence prévoyait d’avoir réalisée. Elle se tire des dates de la révision de référence, jamais de celles de la révision en cours : un planning qui glisse ne déplace pas la valeur planifiée, il creuse l’écart avec elle.

Elle se calcule sur les lignes comptées au budget de référence, hors lignes de provision : chaque montant budgété est étalé sur la durée de sa tâche au prorata des heures travaillées, selon le calendrier de son rôle pour une ligne de main-d’œuvre, celui de la tâche sinon ; une ligne portée par un jalon compte entière à la date du jalon.

Comme le budget, elle ne bouge qu’avec une nouvelle référence : un avenant contractualisé la recalcule entièrement sur celle-ci. Elle forme la courbe en S du projet, à côté de la [valeur acquise](valeur-acquise.md) et du coût réel ; l’écart de délai et l’[indice de délai](indices.md) la comparent à la valeur acquise.

## Voir aussi

- [Le budget de référence](budget-de-reference.md), [la valeur acquise](valeur-acquise.md), [les indices](indices.md), [les révisions](revisions.md) ;
- [la planification](../FBS-4.3.md), dont la référence fige les dates.

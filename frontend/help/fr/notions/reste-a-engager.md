# Le reste à engager et le devis actualisé

## Ce que dit le glossaire

> **Reste à engager** — Désigne le montant des dépenses restant à engager pour terminer le projet.

> **Montant réestimé** — Désigne le montant d’une ligne de devis tel que la dernière revue périodique l’a estimé. C’est sur lui que se calcule le reste à engager.

> **Devis courant** — Désigne le devis de la structure principale de la révision courante d’un projet, lignes de provision comprises sauf lorsque le texte précise « hors provisions ». C’est lui que le pipeline somme pour les projets en chiffrage.

> **Ligne non anticipée** — Désigne une ligne de devis, ou une tâche et ses lignes, ajoutée à la structure principale après la révision de référence pour du travail qui n’avait pas été chiffré. Elle porte un montant budgété nul et pèse sur le reste à engager, jamais sur le budget de référence.

> **Projection à terminaison** — Désigne l’estimation du coût total du projet à son terme. Waterfall en présente trois, selon l’hypothèse faite sur le travail restant.

## Dans Waterfall

Tant que le projet est en chiffrage, le devis se saisit au [devis](../FBS-4.4.md). Dès qu’il est En cours, la grille du [reste à engager](../FBS-4.5.md) devient le devis actualisé : celui de la structure principale se lit seulement, et c’est au reste à engager que la dépense restante se réestime, de la date de la revue à la fin du projet. Une tâche ou une ligne pour du travail qui n’avait pas été chiffré s’y ajoute : c’est une ligne non anticipée.

Le reste à engager d’une tâche terminée est nul ; celui d’une tâche démarrée, ou réestimée, est le montant réestimé de ses lignes ; celui d’une tâche non démarrée que personne n’a réestimée se calcule depuis les grandeurs de la référence, sur son année de consommation courante. S’y ajoutent les provisions des risques identifiés. La réestimation se saisit sur les grandeurs — la charge, ou la quantité et le débours —, et le montant suit ; un reste nul sur toutes les lignes d’une tâche la termine, à une date demandée à la validation.

La projection du chef de projet est la somme du coût réel et du reste à engager ; la marge sur le [budget de référence](budget-de-reference.md) est ce budget moins cette projection, positive quand il en reste. L’écart à la revue précédente dit de combien la revue a fait bouger le reste à engager.

## Voir aussi

- [L’estimation du reste à engager](../FBS-4.5.md) et [ses indicateurs](../FBS-4.5.1.md) ;
- [le budget de référence](budget-de-reference.md), [les révisions](revisions.md), [la provision et la réserve](provision-et-reserve.md).

---
revue_du: 2026-09-27
sur: docs/api et docs/spec/tools, PR #1 (branche spec)
revue_par: GitHub Copilot, analysé par Claude Opus 5
perimetre: >-
  les seize constats de la revue automatique sur la PR #1. Quinze portaient sur le contrat,
  les outils ou la documentation du dépôt et ont été traités dans la branche. Un seul laisse
  une phrase à ajouter au document, et c'est celui-ci.
---

# Revue du 2026-09-27 — ce que la revue de la PR #1 a laissé au document

## D'où vient ce constat

Copilot a relevé que le corps de `setTaskProgress` acceptait les trois états d'avancement,
`not_started` compris, alors que le résumé de l'opération annonce « démarrer ou terminer une
tâche ». En cherchant laquelle des deux lectures était la bonne, il est apparu que WF-RAE-0030
n'accorde qu'un seul passage — celui vers l'état démarré, y compris pour rouvrir une tâche
terminée — et ne dit rien du retour à « non démarrée ». Le contrat a donc été restreint à
`started` et `completed` ; l'exigence dit maintenant en clair ce qu'il avait lu en creux.

Les quinze autres constats étaient des défauts du dépôt et n'ont pas laissé de trace ici.

## Constats

| # | Gravité | Emplacement | Constat | Statut |
|---|---|---|---|---|
| C-090 | mineur | §3.4.5.5.2, WF-RAE-0030 | Le Kanban affiche trois colonnes et n'autorise qu'un passage : l'impossibilité de revenir à « non démarrée » est implicite | intégré |

---

## C-090 — Le retour d'une tâche à « non démarrée »

- **gravité** : mineur
- **emplacement** : §3.4.5.5.2 « Démarrage d'une tâche » — exigence `WF-RAE-0030-A`
- **citation** : « Une vue Kanban présente les tâches de la structure principale de la
  révision courante réparties selon leur état — non démarrée, démarrée, terminée — et permet
  de faire passer une tâche à l’état démarré, y compris une tâche terminée que l’on rouvre. »

**Constat.** Le corps accorde un passage, vers l'état démarré. L'énumération des trois états
décrit ce que la vue *affiche*, pas ce qu'elle *permet* : rien n'interdit explicitement de
faire glisser une carte de « démarrée » vers « non démarrée », et une vue Kanban invite
naturellement à ce geste. La vérification traite le raccourci du jalon mais pas le retour.

Ce n'est pas un détail d'interface : ramener une tâche à « non démarrée » retirerait ses
lignes de la grille de reste à engager, où elles ont peut-être déjà été réestimées. La
spécification ne dit pas ce que deviennent ces réestimations, parce qu'elle ne s'est pas posé
la question.

**Proposition.** Ajouter une phrase au corps de WF-RAE-0030, après « … que l'on rouvre. » :

> Aucun geste ne ramène une tâche à l'état non démarré : une tâche démarrée par erreur se
> corrige en annulant la saisie (WF-IHM-0110), et passé ce délai elle reste démarrée.

Et, à la vérification, après la phrase sur le jalon :

> Aucune commande ne fait passer une tâche démarrée à l'état non démarré.

**Statut.** intégré — les deux phrases sont dans WF-RAE-0030, corps et vérification

<!-- Le contrat suit déjà cette lecture : components/schemas/revisions.yaml, ProgressUpdate,
     restreint l'énuméré de TaskProgress à started et completed. Si l'auteur tranche dans
     l'autre sens, c'est cette restriction qu'il faut lever. -->

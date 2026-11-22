---
id: EP-38
titre: Resserrer le contrat et le schéma — bornes des entrées, refus déclarés, enveloppe d'erreur, descriptions, contraintes et clés
statut: à planifier
depend_de: EP-13, EP-11
famille: back
issue:
---

# EP-38 — Contrat et schéma

## Objet

Le contrat laisse sans borne des entrées que le service ne borne pas davantage, tait des refus que
le service rend, et porte des schémas que rien n'emploie ; le schéma de la base manque de
contraintes et de clés que la spécification demande (revue du 2026-11-14, rapports du contrat et des
données). Le contrat est figé (`docs/api/DECISIONS.md`, « La règle d'après le gel ») : chaque point
demande une décision de l'auteur. Un changement du contrat régénère le client et les modèles et gêne
tous les autres lots : cet EPIC passe quand peu d'autres tournent.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- les bornes des entrées de l'API, et le 413 d'un corps trop grand ;
- les refus que le service rend et que le contrat ne déclare pas ;
- l'enveloppe d'erreur : paramètres et pointeurs ;
- les descriptions à compléter, les schémas morts, les champs nuls ;
- les filtres et les tris des tables plates (WF-IHM-0130) ;
- les couloirs d'une chronologie rangés par la lignée ;
- les contraintes de vérification, les clés étrangères et les droits du schéma.

## Ce qui n'en fait pas partie

- les changements du contrat qu'une correction d'un autre EPIC demande (import lié au compte rendu,
  `uploadFile`) — avec elle ;
- les habilitations au contrat — EP-29 ;
- le contrat du collage (#4398) — EP-31.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

EP-13 fusionné. Une décision de l'auteur par grappe, selon la règle d'après le gel.

## Conduite

Vague 3 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 1 à
2.

## Définition de fini

À établir au cadrage.

## Constats reçus

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4463 — les couloirs d'une chronologie sont rangés par `node_id`, qui change à chaque révision
  (CTB-03)
- #4464 — les bornes des entrées de l'API (BRC-05, BRC-06, BRC-08, BPL-09, CTB-04, CTB-05, CTB-06,
  CTC-03) — BRC-05 est devenu réel : EP-08 classe les risques sur ces bornes
- #4465 — l'enveloppe d'erreur : paramètres et pointeurs (BAC-06, CTA-04, CTA-05, CTA-06)
- #4466 — le contrat : refus servis non déclarés (CTA-08, CTA-09, CTB-08, CTC-02)
- #4467 — le contrat : descriptions, schémas morts, champs nuls (CTA-07, CTB-09, CTB-10, CTB-13,
  CTB-14)
- #4468 — les tables plates : filtres et tris par colonne (WF-IHM-0130) (CTB-11) — EP-11 clôt
  l'exigence en ne filtrant que le portefeuille
- #4469 — le schéma : contraintes, clés et droits à resserrer (DON-07, DON-08, DON-09, DON-14,
  BPR-11) — après les comptes rendus d’import (EP-33)

Reporté par le cadrage d'EP-36 du 2026-11-21 (décision de l'auteur) :

- #4456 — les compteurs `lock_version` naissent à 0 ou à 1 selon la table, quand le contrat dit
  « Toute ressource naît à `lock_version` 1 » (RMP-10 ; #2779, #2240 et #2843, fermées le
  2026-11-11 sur « rien avant la v1 ») — à aligner avant la première installation qui garde ses
  données

Reporté d'EP-08 le 2026-11-21 (décision de l'auteur) :

- #4646 — des lignes de descriptions de `docs/api/components/common.yaml` dépassent 100 colonnes —
  détaché de #4367 ; à recouper avec les descriptions de #4467

Reportées d'EP-11 le 2026-11-21 au soir (décision de l'utilisateur, « Reprise du 2026-11-21
soir » du fichier d'EP-11), à rattacher à un lot :

- #4507 — contrat : les rôles du plan de charge, les points de la matrice et les signaux de la
  santé du pilotage, rangés par libellé puis identifiant (décidé le 2026-11-21)
- #4164 — contrat : aucun exemple d'un 422 de getPortfolioProjects sur la période du périmètre
- #1714 — contrat : aucun exemple de getPortfolioWorkload ni de getPortfolioPilotHealth ne retient
  completed
- #4137 — contrat : la probabilité de gain d'un projet en cours dans la liste du portefeuille, 1 ou
  nulle ?

Issues ouvertes, reportées d'EP-08 le 2026-11-22 :

- #3746 — contrat : deux compositions ambiguës dans des corps de requête
  (`ProjectExit.current_revision`, `CurrentRevisionFate`) ; la sonde les garde dans
  `KNOWN_AMBIGUOUS`
- #4322 — contrat : l'avatar d'un compte n'a pas de version, et le contributeur ne porte pas
  `has_avatar` (bloque #4323, EP-37)
- #4669 — contrat : le refus du redatage d'une base nomme une tâche que le différentiel a supprimée
  par son libellé, nœud nul (documentation seule)

## Conception

À écrire au cadrage.

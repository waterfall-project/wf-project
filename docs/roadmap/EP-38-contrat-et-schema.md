---
id: EP-38
titre: Resserrer le contrat et le schéma : bornes des entrées, refus déclarés, enveloppe d'erreur, descriptions, contraintes et clés
statut: à planifier
depend_de: EP-13
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
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité et sans issue ;
un ticket par ligne, à ouvrir :

- les couloirs d'une chronologie sont rangés par `node_id`, qui change à chaque révision (CTB-03)
- les bornes des entrées de l'API (BRC-05, BRC-06, BRC-08, BPL-09, CTB-04, CTB-05, CTB-06, CTC-03) —
  BRC-05 est devenu réel : EP-08 classe les risques sur ces bornes
- l'enveloppe d'erreur : paramètres et pointeurs (BAC-06, CTA-04, CTA-05, CTA-06)
- le contrat : refus servis non déclarés (CTA-08, CTA-09, CTB-08, CTC-02)
- le contrat : descriptions, schémas morts, champs nuls (CTA-07, CTB-09, CTB-10, CTB-13, CTB-14)
- les tables plates : filtres et tris par colonne (WF-IHM-0130) (CTB-11) — EP-11 clôt l'exigence en
  ne filtrant que le portefeuille
- le schéma : contraintes, clés et droits à resserrer (DON-07, DON-08, DON-09, DON-14, BPR-11) —
  après les comptes rendus d’import (EP-33)

## Conception

À écrire au cadrage.

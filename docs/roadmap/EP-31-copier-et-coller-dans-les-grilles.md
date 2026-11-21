---
id: EP-31
titre: Copier des lignes d'une grille et les coller en insérant ou en remplaçant, les colonnes rapprochées par ce que l'utilisateur voit
statut: à planifier
depend_de: EP-27
famille: front, back
issue:
---

# EP-31 — Copier et coller dans les grilles

## Objet

La spécification 1.0.8 ajoute WF-IHM-0180, la copie de lignes d'une grille, et récrit WF-IHM-0050,
le collage : en insérant des lignes nouvelles ou en remplaçant, les colonnes rapprochées par leurs
en-têtes ou par l'ordre affiché, et non plus par l'ordre des colonnes du contrat (décision de
l'auteur du 2026-11-20 sur un essai du collage, #4329).

Ce fichier tient la place de ce travail dans la roadmap, où chaque exigence est close par un EPIC
et un seul : EP-08, sur le chemin critique, ne prend pas de fonction nouvelle, et EP-30 reste sur
la finalisation des fusions (décision de l'auteur du 2026-11-21). Son périmètre, son rang et son
existence même se décident à la réévaluation du périmètre des EPIC, avec les issues ouvertes sans
rattachement ; il n'est pas cadré, et n'a ni US ni conception.

## Ce qui en fait partie

- la copie de lignes d'une grille, vers un tableur et vers une grille, tâches, subordonnées,
  lignes de devis et liaisons internes comprises (WF-IHM-0180, #4398) ;
- le collage en insérant ou en remplaçant, et le rapprochement des colonnes (WF-IHM-0050, que
  EP-02 a close et dont US-0130 note en écart les trois phrases nouvelles, #4398).

## Ce qui n'en fait pas partie

À établir à la réévaluation. Les autres issues ouvertes sans rattachement par le tri du 2026-11-21
— l'export du devis selon l'annexe B (#4399), la gravité d'un risque survenu (#4400) — ne sont pas
de cet EPIC tant qu'elle ne le dit pas.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0180-A` | Copie de lignes d'une grille | entière | — |

## Opérations du contrat

À établir au cadrage. Le contrat, figé (`docs/api/DECISIONS.md`, « La règle d'après le gel »),
change : `previewPaste` et `applyPaste` — le mode du collage, les colonnes nommées du bloc, la
copie de nœuds.

## Préalables

La réévaluation du périmètre des EPIC, par l'auteur.

## Définition de fini

À établir au cadrage.

## Constats reçus

- #4398 — front, back, contrat : copier des lignes d'une grille, coller en insérant ou en
  remplaçant (WF-IHM-0180, WF-IHM-0050).

## Conception

À écrire au cadrage.

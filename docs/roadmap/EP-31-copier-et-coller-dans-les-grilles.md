---
id: EP-31
titre: Copier des lignes d'une grille et les coller en insérant ou en remplaçant, les colonnes rapprochées par ce que l'utilisateur voit
statut: à planifier
depend_de: EP-27
famille: front, back
issue:
---

# EP-31 — Fonctions après le MVP : copier-coller, export « Heures »

## Objet

La spécification 1.0.8 ajoute WF-IHM-0180, la copie de lignes d'une grille, et récrit WF-IHM-0050,
le collage : en insérant des lignes nouvelles ou en remplaçant, les colonnes rapprochées par leurs
en-têtes ou par l'ordre affiché, et non plus par l'ordre des colonnes du contrat (décision de
l'auteur du 2026-11-20 sur un essai du collage, #4329).

EP-08, sur le chemin critique, ne prend pas de fonction nouvelle, et EP-30 reste sur la finalisation
des fusions (décision de l'auteur du 2026-11-21). La ventilation du même jour range le reste à faire
en EPIC de correction, EP-29 et EP-32 à EP-40 ; cet EPIC garde ce qui n'est pas une correction mais
une fonction, décidée après la fin des fonctions du MVP — la fusion d'EP-08, EP-11, EP-13 et EP-30.
Il n'est pas cadré, et n'a ni US ni conception : l'auteur dira à son cadrage si la copie et le
collage entrent au MVP ou le suivent.

## Ce qui en fait partie

- la copie de lignes d'une grille, vers un tableur et vers une grille, tâches, subordonnées,
  lignes de devis et liaisons internes comprises (WF-IHM-0180, #4398) ;
- le collage en insérant ou en remplaçant, et le rapprochement des colonnes (WF-IHM-0050, que
  EP-02 a close et dont US-0130 note en écart les trois phrases nouvelles, #4398) ;
- l'export du devis selon l'annexe B de la spécification 1.0.8 : « Devis » allégé, onglet « Heures »,
  heures dans « Présentation » (#4399) ;
- la saisie d'une suite de tâches dans une ligne vide en bas de la grille de planning (#4328, une
  discussion, à trancher).

## Ce qui n'en fait pas partie

- les corrections de la saisie en grille et du collage livré — EP-34 ;
- la gravité d'un risque survenu (#4400) — EP-35 ;
- les imports de fichiers — EP-33.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0180-A` | Copie de lignes d'une grille | entière | — |

## Opérations du contrat

À établir au cadrage. Le contrat, figé (`docs/api/DECISIONS.md`, « La règle d'après le gel »),
change : `previewPaste` et `applyPaste` — le mode du collage, les colonnes nommées du bloc, la
copie de nœuds.

## Préalables

La fin des fonctions du MVP, ou la décision de l'auteur d'y faire entrer la copie et le collage.

## Définition de fini

À établir au cadrage.

## Constats reçus

- #4398 — front, back, contrat : copier des lignes d'une grille, coller en insérant ou en
  remplaçant (WF-IHM-0180, WF-IHM-0050) ; elle reçoit CTB-07 de la revue du 2026-11-14, le contrat
  du collage ;
- #4399 — back : l'export du devis suit l'annexe B de la spécification 1.0.8 ;
- #4328 — discussion : saisir une suite de tâches dans une ligne vide en bas de la grille de
  planning, comme MS Project.

## Conception

À écrire au cadrage.

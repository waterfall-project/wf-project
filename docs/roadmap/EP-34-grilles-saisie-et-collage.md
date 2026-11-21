---
id: EP-34
titre: Corriger la saisie en grille : le collage du planning, les écritures concurrentes d'une même cellule, les relectures et ce que l'écran montre après une saisie
statut: à planifier
depend_de: EP-08
famille: front, back
issue:
---

# EP-34 — Grilles : saisie et collage

## Objet

La saisie en grille est le troisième foyer de la revue du 2026-11-14 : un bloc collé dans le
planning écrit sur des lignes de devis que la grille ne montre pas (bloquant B5), une valeur retapée
pendant une écriture en route n'est pas envoyée, le menu d'une cellule agit sur une autre ligne
après une relecture, et l'écran garde les données d'avant la saisie. Ces défauts tiennent dans une
poignée de fichiers de `frontend/src/components/grid/`, que ni EP-08, ni EP-11, ni EP-13 ne
changent.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- le collage du planning, qui n'écrit que ce que la grille montre ;
- les écritures d'une même cellule, leur file, leurs attentes et leurs refus ;
- le menu d'une cellule et les cellules saisissables pendant une relecture ;
- ce que l'écran montre après une saisie : liens en conflit, cartes d'indicateurs, retour par «
  Précédent » ;
- les nombres collés lus dans la langue de l'utilisateur ;
- l'éditeur de cellule.

## Ce qui n'en fait pas partie

- la copie de lignes et le collage en insérant (WF-IHM-0180, #4398) — EP-31, une fonction ;
- les rendus et recalculs évitables de la grille — abandonnés faute de mesure, ou EP-40 ;
- le moteur de planning — EP-32.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

EP-08 fusionné, qui lit un différentiel dans les mêmes grilles. Les lots de cet EPIC touchent les
mêmes fichiers : ils se suivent plus qu'ils ne se parallélisent.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3339 — front, back : un bloc collé dans le planning écrit sur les lignes de devis que la grille
  ne montre pas
- #3939 — défaut : une tâche visée par l'adresse reste repliée quand le repli des écarts est actif
- #3901 — front : l'infobulle de la valeur de base se ferme quand le défilement qui amène la cellule
  au focus survient

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4430 — une valeur retapée pendant qu'une écriture de la même cellule est en route n'est pas
  envoyée (FGR-02, FGR-09, FGR-10)
- #4431 — le menu d'une cellule garde l'indice de sa ligne à travers une relecture (FGR-03) — non
  rejoué dans un navigateur
- #4432 — une écriture en route quand la grille change d'adresse ou que l'écran part : son refus
  n'est pas dit (FGR-04, FGR-08)
- #4433 — pendant la relecture qui suit un geste ou une annulation, les cellules restent
  saisissables avec des versions périmées (FGR-05)
- #4434 — les liens en conflit d'une tâche redatée ne suivent pas l'écriture (FGR-06)
- #4435 — les nombres collés sont lus sans la langue de l'utilisateur (FGR-07, BCH-09)
- #4436 — revenue par « Précédent », une grille montre les données d'avant la saisie (FPL-03) — non
  rejoué dans un navigateur
- #4437 — les cartes d'indicateurs du devis et du reste à engager restent celles d'avant la saisie
  (FCO-01)
- #4438 — l'éditeur de cellule : saisie invalide quittée au clic, composition de caractères (FGR-11,
  FGR-12) — FGR-11 est un choix d'ergonomie à trancher

## Conception

À écrire au cadrage.

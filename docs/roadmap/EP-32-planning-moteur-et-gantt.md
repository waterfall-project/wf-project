---
id: EP-32
titre: Corriger le moteur de planning sur les liaisons de récapitulatives, l'état d'une feuille qui devient récapitulative et le redatage, et le Gantt zoomé
statut: à planifier
depend_de: EP-08
famille: front, back
issue:
---

# EP-32 — Planning : moteur et Gantt

## Objet

Le moteur de planning rend des marges négatives et un chemin critique faux sur un planning tout
automatique dès qu'une liaison part d'une récapitulative, une feuille démarrée qui reçoit une sous-
tâche perd son état, et un calendrier de rôle modifié ne redate aucune révision en cours (revue du
2026-11-14, bloquants B1 et B2, foyer « le moteur de planning »). Cet EPIC les corrige, avec les
constats voisins du même code — `core/planning` et le diagramme de Gantt —, et apporte la preuve par
le back de WF-PLA-0090, qu'aucun test du service ne cite.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- les liaisons qui partent d'une récapitulative ou la visent, et les durées écoulées de moins d'un
  jour, d'un seul tenant, avec un test de propriété sur le moteur ;
- l'état d'une feuille démarrée ou terminée qui reçoit une sous-tâche, après décision de la règle ;
- le redatage des révisions en cours quand un calendrier de rôle change, et la traduction de « tâche
  sans heure travaillée » ;
- la preuve de WF-PLA-0090-A par un test du service, avant que la porte de publication ne joue
  (US-3000, EP-13) ;
- le Gantt zoomé : niveau heures, axe, clavier.

## Ce qui n'en fait pas partie

- la saisie en grille et le collage du planning — EP-34 ;
- l'import d'un planning MS Project — EP-33 ;
- les lectures de `node` qui parcourent toutes les partitions — EP-40.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

EP-08 fusionné, qui touche `core/planning` (gardes de calendrier, structures différentielles). La
règle de #3336 tranchée par l'auteur.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3335 — back : une liaison début-à-début ou début-à-fin qui part d'une récapitulative rend des
  marges négatives et un chemin critique faux (WF-PLA-0100)
- #3336 — back : une feuille démarrée ou terminée qui reçoit une sous-tâche perd son état et devient
  supprimable (WF-PLA-0040, WF-PLA-0070)
- #3984 — back : le conflit d'une subordonnée manuelle d'une récapitulative liée n'est pas signalé
  (WF-PLA-0020, WF-PLA-0030)
- #3785 — front : un lien vertical du Gantt est coupé par la ligne de marque d'une suite repliée

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4411 — le redatage des révisions en cours quand le calendrier d'un rôle change, ou qu'un rôle
  change de calendrier (BRC-01, BCH-07)
- #4412 — une durée écoulée de moins d'un jour donne une marge négative sans conflit (BPL-03,
  BPL-08) — à reprendre avec #3335
- #4413 — « tâche sans heure travaillée » levée par le moteur n'est traduite nulle part : 500 à
  l'ouverture d'une révision (BPL-05)
- #4414 — la passe arrière du moteur, quadratique sur une liaison entre récapitulatives (BPL-04) —
  reste d'un majeur : EP-26 a retiré le rejeu des saisies inertes
- #4415 — WF-PLA-0090-A, close par EP-06, n'est citée par aucun test du back (FTE-01, RMP-05) —
  avant US-3000
- #4416 — le jour en temps universel hors du jour de l'installation, dans l'image de l'arborescence
  et le jugement « en retard » (BEX-15)
- #4417 — les inscriptions orphelines à l'abandon d'une révision (BPL-10)
- #4418 — le Gantt zoomé : niveau heures, axe, clavier (FPL-04, FPL-05, FPL-06)

## Conception

À écrire au cadrage.

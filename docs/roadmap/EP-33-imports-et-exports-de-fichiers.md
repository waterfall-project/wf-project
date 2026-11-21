---
id: EP-33
titre: Fiabiliser les allers-retours de fichiers : rapprochement MS Project, bornes des classeurs, compte rendu confirmé, comptes rendus d'import et leur purge
statut: à planifier
depend_de: EP-08
famille: front, back
issue:
---

# EP-33 — Imports et exports de fichiers

## Objet

Les allers-retours de fichiers portent un bloquant et le plus grand nombre de majeurs de la revue du
2026-11-14 (foyer « les allers-retours de fichiers ») : à la réimportation d'un planning MS Project
une tâche ajoutée peut prendre l'identité d'une tâche existante, un classeur s'ouvre sans borne de
décompression, l'application d'un import ne tient pas le compte rendu confirmé, une colonne absente
se lit comme des cellules vides. Cet EPIC les corrige, avec les comptes rendus d'import que rien ne
supprime et l'écran des imports.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- le rapprochement des tâches à la réimportation d'un planning MS Project, et les bornes de son
  lecteur ;
- une borne de décompression commune aux classeurs téléversés, lus hors du verrou du projet ;
- l'application d'un import liée au compte rendu que l'utilisateur a confirmé ;
- le refus d'un onglet dont une colonne lue manque, et l'import du devis qui supprime ligne à ligne
  ;
- les comptes rendus d'import : leur suppression à l'échéance, leur liste, la tâche qu'ils nomment
  et que la purge d'EP-13 supprime ;
- `uploadFile` sous permission, et l'élément d'OTP comparé en entier (spécification 1.0.7) ;
- l'écran des imports et la commande « Relancer ».

## Ce qui n'en fait pas partie

- le collage dans une grille — EP-34 ;
- l'export du devis selon l'annexe B (#4399) — EP-31 ;
- la restauration et son dépôt — EP-39.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

EP-08 fusionné, qui a touché les imports (différentiels, cascades de `import_report`). Les comptes
rendus d'import sont à livrer avant la fusion d'EP-13 : sa purge des tâches de fond fait répondre
500 à l'ouverture d'un import de plus de trente jours.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 3.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3337 — back : à la réimportation d'un planning MS Project, une tâche ajoutée peut prendre le nœud
  d'une tâche existante (WF-INTF-0040)
- #3978 — back : la terminaison d'une tâche par l'import du reste à engager, à confronter à
  WF-INTF-0120 (spécification 1.0.7)
- #3966 — contrat : l'élément d'OTP comparé en entier, le code de sous-projet libre (spécification
  1.0.7, WF-CRE-0020, WF-PRJ-0050)

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité et sans issue ;
un ticket par ligne, à ouvrir :

- les classeurs téléversés ouverts sans borne de décompression, et l'en-tête lu sous le verrou du
  projet (BEX-03, BRC-02, BCH-06, BRC-03, BEX-05)
- l'application d'un import MS Project n'est pas liée au compte rendu confirmé (BEX-02, CTB-01) — le
  contrat change
- une colonne lue absente d'un onglet se lit comme des cellules vides (BCH-03)
- import du devis : une suppression par ligne retirée, avec un rejeu du moteur chacune (BCH-05) — à
  mesurer
- `uploadFile` : une écriture sans permission, sans 403 et sans quota (CTB-02, BAC-09) — le contrat
  change
- « Relancer » offert pour l'application échouée d'un import, que le service refuse toujours
  (FCO-02, FCO-04)
- les comptes rendus d'import : suppression à l'échéance, liste, tâche purgée, taille (BEX-07,
  BEX-10, BEX-11, DON-05, FCO-06) — avant la fusion d'EP-13
- le lecteur MS Project : bornes et replis (BEX-08, BEX-09, BEX-14)
- un import pendant une panne passagère du stockage (BEX-13)
- l'import du reste à engager : montant saisi, montant écrit (BCH-11)
- l'écran des imports : formulaire et zone de dépôt après un envoi (FCO-03, FCO-05, FCO-14)

Constats de la même revue joints à une issue ci-dessus : BRC-04 (l'imputation et le compte rendu des
lignes hors du projet) et BPR-09 (la borne du code de sous-projet déclaré), à #3966.

## Conception

À écrire au cadrage.

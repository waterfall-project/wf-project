---
id: EP-40
titre: Tenir les objectifs de temps de réponse — requêtes qui parcourent toutes les partitions, grilles comparées, marquage, écran des indicateurs, et les outils de mesure
statut: à planifier
depend_de: EP-13, EP-11
famille: front, back
issue:
---

# EP-40 — Lectures et performance

## Objet

Des lectures filtrent sans le projet et parcourent toutes les partitions, la garde des calendriers
et « cette catégorie est-elle employée ? » lisent les lignes de devis de toutes les révisions, et
quatre opérations dépassent leur objectif du tableau 15 : ouvrir et saisir dans une grille comparée,
ouvrir l'écran des indicateurs, marquer une révision. Cet EPIC les corrige et solde les finitions
des outils de mesure. Une mesure demande le poste entier : il passe en dernier, quand peu de
livreurs tournent, et après EP-13, qui porte la mesure aux volumes (US-2970).

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- les lectures de `node` et des lignes de devis qui ne nomment pas le projet ;
- les opérations hors de leur objectif : grille comparée, écran des indicateurs, marquage ;
- la comparaison de deux révisions marquées recalculée à chaque affichage ;
- les finitions des outils de mesure (`make measure`, `measure-core`, `measure-reference`).

## Ce qui n'en fait pas partie

- la passe arrière quadratique du moteur de planning — EP-32 ;
- la mesure aux volumes — EP-13 (US-2970) ;
- les rendus évitables de la grille et du Kanban — abandonnés faute de mesure.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

EP-13 fusionné, et le poste libre pour les mesures. Les correctifs de DON-03 excluent les bases des
différentiels, qu'EP-08 a ajoutées.

## Conduite

Vague 3 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 1 à
2.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3609 — back : milestone_forecasts lit chaque révision marquée par une requête (N+1)
- #3902 — performance : l'écran des indicateurs s'ouvre en 4,9 s pour l'objectif d'une seconde sous
  charge
- #3903 — performance : le marquage de PRJ-001 passe de 0,1 s à 6,4 s depuis EP-26
- #3168 — back, front : la comparaison de deux révisions marquées et la lecture de leurs grilles se
  recalculent en entier à chaque affichage
- #3532 — back : la lecture gardée projetée par fields relit encore le document entier
- #3657 — front : la matrice des risques se lit après la couverture, un peu plus tard qu'elle ne
  pourrait
- #3768 — back : inflation_rate et win_probability d'une révision lus par un lecteur de grille
- #3776 — back : la liste des lecteurs de grille est définie deux fois dans api/
- #3906 — back : la mesure de la révision en cours juge son seuil sur une union planchée, et son
  ordre alterné n'est ni pair ni testé
- #3913 — back, front : ouvrir une grille comparée prend 2,847 s pour 2 s
- #3914 — back, front : saisir dans une grille comparée prend 4,502 s pour 2 s
- #3334 — outil : une cible de mesure réécrit WATERFALL_PROCESSORS avec la part de N, et le mode
  exclusif n'a plus le poste entier
- #3340 — outil : les finitions de make measure-core (message d'erreur, barrière, échauffement de la
  durée, test de locate)
- #3402 — front : make measure — la sonde getMe, la cause de ses pertes, le guide et un test
  (mineurs, revue d'US-2210/L3)
- #3413 — outil : measure-reference, base de l'EPIC en dur et taken_at non exigé
- #3533 — outil : la note de la règle du tiers d'US-2270 se lit mal à deux endroits
- #3896 — outil : la ligne de make measure-core du guide est trop longue pour une ligne de tableau
- #3915 — outil : le rapport 0.4.0 tait qu'open-grid a passé 1 s sous la nouvelle charge et ne nomme
  pas les issues des dépassements
- #3617 — documentation : les notes d'US-2250 donnent une dispersion de 71 à 85 ms au lieu de 71 à
  86, et deux lignes trop longues
- #3640 — front : des lignes de code de frontend/e2e/measure dépassent cent colonnes

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4484 — des lectures de `node` filtrées par la seule révision parcourent toutes les partitions, et
  `node.lineage_id` n'a pas d'index (DON-01, DON-04, BPR-05, BPR-06)
- #4485 — la garde des calendriers lit les lignes de devis de toutes les révisions de tous les
  projets (DON-02, BCH-12)
- #4486 — « cette catégorie est-elle employée ? » : un `DISTINCT` sur toutes les lignes de devis de
  la plateforme (DON-03) — alourdi par EP-08 et EP-11

Reporté par le cadrage d'EP-36 du 2026-11-21 (décision de l'auteur) :

- #4446 — aucun test ne cite WF-IHM-0080-A sur le marquage d'une révision de dix mille objets
  (« laisse l'écran utilisable et présente son avancement ») : un parcours au volume, sur le jeu
  qu'EP-13 charge (RMP-03) ; EP-36 (US-3490) corrige le renvoi circulaire d'EP-09 et d'EP-04

Reportées d'EP-11 le 2026-11-21 au soir (décision de l'utilisateur, « Reprise du 2026-11-21
soir » du fichier d'EP-11), à rattacher à un lot :

- #3868 — US-2790 d'EP-11 entière : les vues du portefeuille mesurées, au jour courant et à une
  date passée ; la mesure prend le poste
- #4165, #4177, #4313 — back : les lectures du jour projet par projet (empreinte, indicateurs,
  couverture des risques), que la mesure d'US-2790 décide
- #4339 — back : la courbe en S du jour re-choisit la révision que le périmètre a retenue (décision
  du 2026-11-21 : corrigé avec US-2790)

## Conception

À écrire au cadrage.

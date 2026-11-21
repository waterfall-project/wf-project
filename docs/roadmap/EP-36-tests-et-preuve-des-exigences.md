---
id: EP-36
titre: Durcir les tests et la preuve des exigences — attentes des parcours, gardes du harnais, tests instables, citations, renvois de la roadmap
statut: à planifier
depend_de: EP-08, EP-11
famille: front, back
issue:
---

# EP-36 — Tests et preuve des exigences

## Objet

« Close » n'est pas « prouvée » : la revue du 2026-11-14 relève des parcours dont les attentes sont
trop faibles, des gardes absentes du harnais, des exigences citées de travers, et des renvois de la
roadmap qu'aucun EPIC ne porte. S'y ajoutent les constats mineurs sur des tests que les revues des
lots ont laissés ouverts. Les lots de cet EPIC touchent des fichiers distincts : c'est le seul qui
se parallélise sur tous les créneaux du poste, et il se glisse là où des créneaux sont libres.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- les parcours du front dont l'attente ne prouve pas ce qu'ils annoncent, et les tests instables ;
- les gardes du harnais et des sources : sortie d'erreur, clés inemployées, tests sautés ;
- les citations d'exigences dans les tests, et ce que `make requirements` ne lit pas ;
- les phrases de Vérif closes par un renvoi que personne ne porte ;
- les renvois de portée et les titres des fichiers d'EPIC livrés ;
- la règle d'import-linter étendue aux imports hors de l'interface d'un module.

## Ce qui n'en fait pas partie

- la preuve de WF-PLA-0090-A — EP-32, avant la porte de publication ;
- la porte de publication elle-même — EP-13 (US-3000) ;
- les mesures de performance — EP-40.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

Aucun au-delà de la fusion d'EP-08 et d'EP-11, dont les tests suivent le code.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs :
jusqu’à 6.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3916 — back : trois reprises mineures des tests du lot #3802 (citation de WF-DEV-0090-A, somme
  reconnue par GROUP BY, branches dupliquées de _spread_after)
- #3921 — back : le module de tests de clôture d'US-1670 importe ses aides de test_indicators_stored
  et copie ses fixtures
- #3997 — test : le test d'en-tête du reste à engager ne prouve pas la largeur naturelle des
  commandes, et la grille ne garde que 3,5 points à 1280 × 720
- #3521 — front : une assertion arbitraire et un double serve() dans le test de l'export retrouvé
  (revue 2 d'US-2310/L1)
- #3461 — test : la création d'un rôle attend la relecture d'une écriture perdue sans test qui
  l'éprouve
- #3595 — test : le test des relectures du Kanban promet un refus qu'il n'éprouve pas
- #3788 — front : le test du collage sous repli affirme ses sommaires par construction
- #3907 — front : le test du signal de fin de mesure n'éprouve ni la cellule non marquée ni
  l'adresse attendue
- #3908 — front : le test de la relecture comparée ne joue ni l'écriture en cours échouée ni celle
  sans changement
- #3909 — e2e : reachByKeyboard n'échoue tôt que sur la dernière cellule de la rangée
- #3937 — qualité : les tests du front qui filtrent encore du HTML par expression régulière
- #4000 — front : kanban.dom.test.tsx instable sous charge (act non attendu)
- #4140 — front : admin.spec.ts:572 attend « Service des achats » et reçoit « Aucun » (une fois, en
  local)
- #4141 — front : remaining.spec.ts:441, page.waitForRequest sur une page fermée dans seedPlanning
  (une fois, en local)
- #3789 — outil : make requirements ignore une exigence citée par une constante

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4444 — deux phrases de Vérif closes par un renvoi « constaté par EP-06 » qu'EP-06 ne porte pas
  (RMP-06)
- #4445 — un parcours laisse la matrice de risques et les seuils modifiés (FTE-02) — reste d'un
  majeur
- #4446 — WF-IHM-0080-A close par un renvoi circulaire, sans test au volume qui la cite (RMP-03) —
  reste d'un majeur
- #4447 — WF-ADM-0160-A reste close par EP-04, sans citation dans les tests d'EP-13 qui la tiennent
  (RMP-04) — reste d'un majeur
- #4448 — les parcours du front : attentes trop faibles ou fragiles (FTE-03, FTE-04, FTE-05, FTE-08,
  FTE-09)
- #4449 — les tests du front : gardes manquantes du harnais et des sources (FTE-06, FTE-07, FTE-12)
- #4450 — les tests du front : commentaires périmés (FTE-10, FTE-14)
- #4451 — les tests : citations d'exigences, et ménage (BAC-10, BRC-10, FCO-13, FAR-05)
- #4452 — les corps redéclarés à la main ne sont tenus au contrat par aucun test (CTC-05)
- #4454 — les imports hors de l'interface d'un module, et la règle d'import-linter (BRC-09)
- #4455 — la roadmap : renvois de portée, titres, fichiers livrés (RMP-08, RMP-09, RMP-13) — un
  contrôle de `wftools.roadmap`
- #4456 — les compteurs `lock_version` : la dette remise à la v1, sans porteur (RMP-10)
- #4457 — la spécification : WF-RAE-0020 renvoie à WF-IND-0010 pour une révision marquée (SPB-12) —
  avec la prochaine révision du document

## Conception

À écrire au cadrage.

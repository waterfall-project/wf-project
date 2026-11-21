---
id: EP-35
titre: Corriger les règles et les calculs des projets, des révisions, du chiffrage, des coûts et des indicateurs que la revue et les spécifications 1.0.7 et 1.0.8 ont relevés
statut: à planifier
depend_de: EP-30
famille: front, back
issue:
---

# EP-35 — Projets, chiffrage, coûts et indicateurs : règles et calculs

## Objet

Des règles et des calculs livrés ne tiennent pas la spécification : une grandeur saisie avec plus de
décimales que sa colonne donne un montant qui change sans saisie (bloquant B4), la référence se
corrige encore après la réception de coûts réels (WF-REV-0040), une tâche datée hors de 2000-2100
fait répondre 500. Cet EPIC les corrige après EP-30, qui touche le même code — devis, risques,
révisions.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- les décimales d'une grandeur jugées contre l'échelle de sa colonne ;
- la désignation de la référence refusée dès qu'un coût réel est reçu ;
- les bornes de l'année d'une tâche, l'année de consommation, le débours projeté au changement
  d'année ;
- ce qu'une révision marquée lit aux valeurs du jour ;
- les règles du référentiel et des projets que la spécification 1.0.7 a écrites ;
- la concurrence du marquage, de la désignation et de l'abandon d'une révision.

## Ce qui n'en fait pas partie

- le devis propre d'un risque préparé comme un différentiel, la gravité en écart net, et celle d'un
  risque survenu, lue à son coût à la survenance (#4400, repris par EP-30 à son cadrage du
  2026-11-21) — EP-30 ;
- les lectures lentes et les requêtes sans le projet — EP-40 ;
- les imports — EP-33.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

EP-30 fusionné. WF-REV-0040-A est close par EP-08 (US-2560) avec la condition du coût réel manquante
: cet EPIC la porte.

## Conduite

Vague 2 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3338 — back : une grandeur saisie à plus de décimales que sa colonne donne un montant que le
  premier rechiffrage change sans saisie (WF-INTF-0100)
- #3976 — back : consumption_year rend l'année de la plus grande part, le contrat celle du début de
  la tâche
- #3983 — back : le débours unitaire projeté au changement d'année de référence (WF-REV-0060,
  spécification 1.0.7)
- #3985 — contrat : la désactivation d'une catégorie ou d'un calendrier que portent des rôles actifs
  est refusée (WF-REF-0010)
- #3989 — contrat : le code d'un projet En cours ne s'efface plus (WF-PRJ-0010)
- #3951 — code : Rounding.of traite tout mode autre que ROUND_HALF_UP comme ROUND_HALF_EVEN
- #3727 — back : la docstring d'Instants dit « the imports apart », le champ en fait partie

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4439 — une tâche datée hors de 2000-2100 fait répondre 500 à toute écriture de ligne et à tout
  redatage (BCH-02)
- #4440 — la référence se corrige encore après la réception de coûts réels (WF-REV-0040) (BPR-02,
  SPB-01)
- #4441 — le plan de charge « référence » et l'export du reste à engager d'une révision marquée
  lisent les valeurs du jour (BCH-04, BCH-08) — reste d'un majeur : la valeur planifiée est corrigée
  par EP-10
- #4442 — la concurrence des révisions : marquage, désignation, interblocages (BPR-08, BPR-12,
  BPR-01) — avec le reste de BPR-01
- #4443 — les indicateurs : l'évolution des indices (FCO-07, FCO-08, FCO-09)

Constats de la même revue joints à une issue ci-dessus : BPR-03 (la création d'une révision au
changement d'année), à #3983 ; BPR-07 (le code d'un projet En cours), à #3989.

## Conception

À écrire au cadrage.

---
id: EP-27
titre: Comparer la révision lue à une révision marquée dans les grilles où l'on travaille
statut: à planifier
depend_de: EP-26
famille: front, back
issue:
---

# EP-27 — Comparaison dans les grilles

## Objet

La comparaison de deux révisions marquées vit aujourd'hui sur l'écran « Révisions », dans une grille
à part qui dit ce qui change sans en donner les valeurs, et refuse la révision en cours — le cas le
plus utile. La spécification 1.0.6 en fait une dimension du contexte de lecture : une révision lue,
en cours ou marquée, et une base, toujours marquée, choisies dans le bandeau et lues dans les
grilles de planning, de devis et de reste à engager.

L'EPIC vient avant EP-08 : les avenants et les risques fusionnent des structures et s'appuient sur
une comparaison saine. Il vient après EP-26, parce qu'une comparaison lit deux structures.

## Ce qui en fait partie

- ce qui se compare : une révision en cours ou marquée contre une base marquée, dans les deux sens,
la révision en cours restant modifiable, la valeur de base rendue (#3176, WF-REV-0080) ;
- le choix de la révision lue et de la base dans le bandeau de contexte, la base portée par
l'adresse entre les trois grilles (#3178, WF-IHM-0020, WF-IHM-0010) ;
- les marques des lignes et des cellules, les colonnes d'écart, les totaux de la révision lue et de
la base, le repli des branches sans écart (#3179, WF-IHM-0150 à WF-IHM-0170) ;
- l'écran « Révisions » réduit à l'historique et à ses commandes (#3177), et le sort des structures
et de la mise à jour des taux qu'il porte (#3180) ;
- le parcours de la comparaison de PRJ-001, en quarantaine contre le service, réécrit sur les
grilles et rejoué (#3192).

## Ce qui n'en fait pas partie

- la comparaison d'une structure différentielle ou du devis propre d'un risque : la comparaison ne
porte que sur la structure principale ;
- la phrase de WF-REV-0080 sur la révision obtenue par fusion d'un différentiel — EP-08, qui livre
la fusion et clôt l'exigence.

## Exigences réalisées

WF-IHM-0150, WF-IHM-0160 et WF-IHM-0170, nouvelles en 1.0.6, sont entières ici. WF-REV-0080 et
WF-IHM-0020 restent closes par EP-08, dont dépendent leurs phrases sur les différentiels et les
devis de risques ; cet EPIC en réalise les phrases ajoutées par la 1.0.6. WF-IHM-0010, close par
EP-02, y gagne une phrase, notée en écart dans les US qui la citaient (US-0090, US-0720).

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0150-A` | Marques d’une comparaison dans les grilles | entière | — |
| `WF-IHM-0160-A` | Totaux d’une comparaison | entière | — |
| `WF-IHM-0170-A` | Repli des branches sans écart | entière | — |
| `WF-REV-0080-A` | Comparaison de deux révisions | début — close en EP-08, amorcée aussi en EP-15, EP-07 | — |
| `WF-IHM-0020-A` | Contexte de lecture affiché | début — close en EP-08, amorcée aussi en EP-02, EP-15 | — |

## Opérations du contrat

`compareRevisions` : le 409 d'une révision en cours levé pour la révision lue, gardé pour la base ;
la valeur de base de chaque valeur modifiée et les totaux de la base rendus — ou la comparaison lue
par `listNodes` : au cadrage. Modification du contrat, qui précède le code.

## Préalables

EP-26 livré : la lecture gardée d'une révision marquée et les bornes de temps. La spécification
1.0.6 fusionnée.

## Définition de fini

- la révision en cours se compare à une révision marquée depuis chacune des trois grilles, la saisie
y reste ouverte, et les marques suivent chaque écriture ;
- l'écran « Révisions » ne porte plus de comparaison ;
- le parcours de la comparaison est rejoué contre le service (#3192) ;
- `make check-all` passe.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC.

- #2590 — front : le report #1057 par un geste de la grille de devis, une fois son écran servi ;
- #2854 — front : planning.spec.ts dit encore « the lines being EP-07's » une fois le témoin chargé
de ses lignes ;
- #2885 — front : l'erreur de timelines.spec.ts sur un compte gestionnaire absent ne dit pas où il
se définit ;
- #3127 — roadmap : WF-REV-0080-A dite close par EP-08, que aucune US d'EP-08 ne cite, et trois
mineurs d'US-2010/L2 ;
- #3160 — front : des commentaires au-delà de 100 colonnes dans import-report.tsx et file-drop.tsx ;
- #3176 — spec : la révision en cours comparée à une révision marquée, et la valeur de base de
chaque écart (WF-REV-0080) ;
- #3177 — front : l'écran « Révisions » est brouillon, et sa comparaison loin des grilles —
l'historique et ses commandes seuls ;
- #3178 — spec : la révision lue et la base d'une comparaison choisies dans le bandeau de contexte,
la base conservée entre les grilles (WF-IHM-0020, WF-IHM-0010) ;
- #3179 — spec : les écarts d'une comparaison lus dans les grilles de planning, de devis et de reste
à engager (exigences nouvelles, WF-IHM-0150 à 0170) ;
- #3180 — front : les structures et la mise à jour des taux de la révision lue sous l'historique de
l'écran « Révisions » ;
- #3192 — e2e : le parcours de la comparaison de PRJ-001 (revisions.spec.ts:121) en quarantaine
contre le service.

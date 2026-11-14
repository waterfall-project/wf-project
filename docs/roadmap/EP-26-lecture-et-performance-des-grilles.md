---
id: EP-26
titre: Ouvrir, filtrer et saisir dans une grille de mille tâches sans attendre
statut: à planifier
depend_de: EP-25
famille: back, front
issue:
---

# EP-26 — Lecture et performance des grilles

## Objet

Sur un projet aux volumes du §4.6.2 — mille tâches, cinq mille lignes —, ouvrir une révision prend
dix secondes, un filtre relit et recalcule la structure entière, et la file de fusion perd des
parcours dès que plusieurs lisent PRJ-001 ensemble sur l'API à un seul processus. L'analyse du
2026-11-14 (#3168 à #3174) en a relevé sept causes, chacune avec ce qu'il faut mesurer pour
trancher.

L'EPIC mesure d'abord, puis corrige ce qui pèse, et dit ce qui est réellement atteignable : c'est
lui qui fixe les bornes de temps des parcours lourds et qui clôt WF-QUA-0060. Il précède la
comparaison dans les grilles (EP-27), qui lit deux structures à la fois.

## Ce qui en fait partie

- la mesure du parcours — ouvrir une grille, filtrer, saisir, passer d'une grille à l'autre —,
contre le faux back et contre le service, à plusieurs utilisateurs (#3173) ;
- le chemin de lecture d'une structure, et ce qui se recalcule à chaque lecture (#3174, #3170) ;
- la saisie qui ne déplace rien, et la relecture d'un filtre, d'un tri ou d'une recherche (#3169,
#3171) ;
- la lecture gardée d'une révision marquée (#3168, option 1) ;
- l'API à plusieurs processus (#3172) ;
- l'ouverture d'une révision d'un projet chargé, et ce que le front dit pendant qu'elle dure (#3102)
;
- les objectifs du tableau 15, tels que la spécification 1.0.6 les allège (#3184), confrontés aux
durées mesurées ;
- le parcours du reste à engager filtré par un poste, en quarantaine contre le service, rejoué
(#3087).

## Ce qui n'en fait pas partie

- la différence tenue à l'écriture pour une révision en cours comparée (#3168, option 3) — instruite
ici, réalisée par EP-27 si la mesure la justifie ;
- le jeu de données aux trois cents projets (WF-QUA-0040) — EP-13 ; les vues de portefeuille se
mesurent à leur livraison (EP-11), par l'outil écrit ici.

## Exigences réalisées

WF-QUA-0060 passe d'EP-13 à cet EPIC, qui la clôt (décision de l'auteur du 2026-11-14). Les lignes
du tableau 15 qui portent sur des fonctions non encore livrées — le portefeuille, la comparaison —
se mesurent à leur livraison, par le même outil : l'US le dira en écart.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-QUA-0060-A` | Tests de charge et non-régression des temps de réponse | entière | — |

## Opérations du contrat

`listNodes`, `getNode`, `updateNode`, `compareRevisions`, `listRevisions`, `createRevision`. Aucune
opération nouvelle n'est prévue ; une lecture par fenêtre ou une valeur dérivée rendue se noterait
ici, avant le code.

## Préalables

EP-25 livré, pour que les parcours mesurés soient ceux des écrans définitifs. La mesure de référence
précède tout lot de correction : sans elle, aucun lot ne sait ce qu'il gagne.

## Définition de fini

- les durées de chaque opération du tableau 15 servie sont publiées, sur le jeu de référence, avec
leur dispersion (WF-QUA-0060) ;
- les bornes de temps des parcours lourds sont celles que la mesure justifie, et le parcours
`structure.spec.ts` en quarantaine est rejoué contre le service (#3087) ;
- la file de fusion échoue moins d'une fois sur dix sur cinquante passages ;
- `make check-all` passe.

## Constats reçus

Ventilation du reste à faire du 2026-11-14 (décision de l'auteur, à la livraison d'EP-24) : les
constats ouverts sont rattachés à l'EPIC qui touche leur code, et non plus au prochain EPIC ouvert.
Le cadrage les rattache à l'ouverture des issues de l'EPIC.

- #2212 — back : _BLANK_IS_LACKING reconnaît version_name au seul nom du champ ;
- #2464 — back : les parties de register_tasks_and_lines et les étapes de register_closing, posées
par le socle d'EP-06 ;
- #2502 — back : le rang des tâches placées parmi des lignes de devis, posé par US-1380/L3 ;
- #2605 — back : le collage qui crée relit calendrier et constantes à chaque ligne, sous le verrou ;
- #2606 — back : le refus d'horizon d'un collage nomme la première ligne, pas celle qui dépasse ;
- #2892 — back : la somme d'une révision indépendante de l'ordre est éprouvée sur sum_amounts, que
le service n'appelle pas ;
- #3087 — e2e : le parcours du reste à engager filtré par un poste (structure.spec.ts:335) échoue
par moments dans la file — en quarantaine contre le service ;
- #3093 — contrat : les refus de débordement d'un montant dérivé (#2996, #3035, #3039) ne sont pas
décrits par le contrat ;
- #3094 — back : la redatation d'une tâche et la copie d'une révision qui débordent un montant
répondent 422 sans champ ;
- #3102 — front, back : ouvrir une révision d'un projet de mille tâches prend dix secondes, et le
front dit « service injoignable » au bout de cinq alors qu'elle se crée (WF-REV-0010) ;
- #3138 — back : totals_of écrit deux fois sa garde « liste vide » ;
- #3168 — back, front : la comparaison de deux révisions marquées et la lecture de leurs grilles se
recalculent en entier à chaque affichage ;
- #3169 — back : une saisie qui ne peut déplacer aucune date rejoue le moteur sur la structure
entière ;
- #3170 — back : les états des récapitulatives et les montants des tâches se recalculent à chaque
lecture, et le planning lit les lignes de devis qu'il n'affiche pas ;
- #3171 — front, back : un filtre, un tri ou une recherche relit et recalcule la structure entière ;
- #3172 — back : l'API n'a qu'un processus, et le parcours de comparaison joué par plusieurs
utilisateurs s'y attend ;
- #3173 — outil : la mesure de la seconde ne couvre ni la comparaison ni le parcours comparaison →
grilles → comparaison ;
- #3174 — back : la lecture d'une structure charge chaque nœud en objet ORM, puis en vue, puis en
corps ;
- #3184 — spec : les objectifs de temps de réponse ne nomment ni la comparaison, ni un filtre, ni
les vues nouvelles (§4.6.2, WF-QUA-0060).

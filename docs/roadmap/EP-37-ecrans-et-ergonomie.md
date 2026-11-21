---
id: EP-37
titre: Reprendre les écrans d'après les remarques d'ergonomie et les essais manuels : libellés, navigation, mise en page, coquille et client du front
statut: à planifier
depend_de: EP-08, EP-11
famille: front
issue:
---

# EP-37 — Écrans et ergonomie

## Objet

Six remarques d'ergonomie attendent depuis la refonte (libellés tronqués, sigles sans légende,
navigation redondante, titre qui change de place), avec la mise en page de trois familles d'écrans
et des constats mineurs de la revue sur la coquille du front. Cet EPIC les rassemble, et **reçoit
les remarques des essais manuels** que l'auteur mène après la fusion des fonctions du MVP : un
défaut de présentation ou de parcours relevé à l'essai y entre, un défaut de règle ou de calcul va à
l'EPIC qui touche son code.

L'EPIC naît de la ventilation du 2026-11-21 : une fois fusionnés EP-08, EP-11, EP-13 et EP-30, les
fonctions du MVP sont livrées, et le reste à faire — les issues ouvertes hors de ces EPIC et les
constats de la revue du 2026-11-14 encore d'actualité — se range par zone de code, pour que deux
EPIC menés de front ne touchent pas les mêmes fichiers. Il reste à cadrer : ses US, sa conception et
ses lots se décident à son cadrage.

## Ce qui en fait partie

- les libellés, les sigles, le contexte du projet, la navigation, la place du titre, les boutons ;
- la mise en page de l'accueil, des écrans d'un projet et du compte ;
- la robustesse des écrans de projet à l'adresse ;
- les commandes de sortie et de marquage ;
- le client d'API du front : délai et codes inconnus ;
- la coquille : recherche inerte, catalogue servi en entier ;
- les remarques de présentation et de parcours des essais manuels, au fil de l'eau.

## Ce qui n'en fait pas partie

- la saisie en grille — EP-34 ;
- la session et le retour de connexion — EP-39 ;
- l'écran des comptes — EP-29.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Les exigences
que ses constats citent restent closes par les EPIC qui les ont réalisées.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

À établir au cadrage.

## Préalables

La fusion d'EP-08 et d'EP-11, et un premier lot de remarques des essais manuels.

## Conduite

Vague 2 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.

## Définition de fini

À établir au cadrage.

## Constats reçus

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3541 — libellés tronqués : barre latérale, fil d'Ariane, en-têtes de colonnes, planification
- #3542 — sigles et icônes sans légende : Σ, éclair, icônes d'état des risques
- #3543 — contexte du projet : nom absent du sélecteur et du fil d'Ariane, deux états sans étiquette
- #3544 — navigation redondante et hiérarchie du menu « Révision en cours »
- #3545 — le titre des écrans change de position d'un écran à l'autre
- #3546 — boutons : création et actions de table incohérentes avec la règle d'EP-25
- #3090 — front : la mise en page de l'accueil, des écrans d'un projet et du compte, d'après l'écran
  des coûts (WF-IHM-0040)
- #3422 — spec : les filtres de périmètre des indicateurs d'un projet restent dans la bannière de
  contexte
- #1512 — front : retirer `prefetch={false}` du menu du compte à la montée vers Next 16.5, et deux
  mineurs de commentaire (US-0590e, tour 2)
- #3459 — front : l'anneau de focus rogné et la classe dupliquée de la barre repliée d'une grille,
  un commentaire de test périmé (revue 3 d'US-2110/L1)
- #3479 — front : cinq lignes de la page des paramètres de coûts dépassent 100 colonnes
- #3523 — front : la coupure irrégulière du commentaire d'en-tête des mesures des cartes de projets
  (revue 2 d'US-2310/L2)
- #3594 — front : l'avis du marquage perdu annoncé deux fois quand le formulaire se ferme pendant la
  relecture

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4458 — les écrans de projet : robustesse à l'adresse (FPL-07, FPL-08)
- #4459 — les commandes de sortie et de marquage (FSO-04, FSO-05) — voisin de #3594
- #4460 — le client d'API du front : délai et codes inconnus (FSO-06, FSO-07)
- #4461 — la coquille du front : recherche inerte, catalogue entier servi (FSO-09, FSO-10) — FSO-10
  à mesurer
- #4462 — les chaînes d'interface bâties à la main (FCO-12, FAR-07) — sans effet visible en français
  ni en anglais : candidat à l'abandon

## Conception

À écrire au cadrage.

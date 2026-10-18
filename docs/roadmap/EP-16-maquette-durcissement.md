---
id: EP-16
titre: La maquette et le contrat durcis après les ajustements : mineurs, accessibilité des dialogues, navigateurs, reliquats de tests
statut: à planifier
depend_de: EP-15
famille: front
issue:
---

# EP-16 — Maquette et contrat : durcissement

## Objet

EP-15 réalise les ajustements que la validation de l'auteur a décidés, et la maquette, la
spécification et le contrat sont alors entièrement validés. EP-16 les durcit : les mineurs du
contrat et du front que les relectures d'EP-14 et d'EP-03 ont relevés et que l'auteur a reportés
(décisions du 2026-10-11 et du 2026-10-17), l'extension du harnais d'accessibilité aux dialogues,
aux menus et aux éditeurs ouverts (#782), les navigateurs et les largeurs d'affichage (US-0290), et
les reliquats des tests du front. Il vient après EP-15 parce que polir des écrans et un contrat
encore appelés à changer ferait payer deux fois chaque ajustement (décision de l'auteur du
2026-10-11) : c'est la raison qui a fait sortir le durcissement d'EP-14, puis d'EP-15.

Il se cadre une fois EP-15 livré ; ses US, sa conception et son plan de lots tiendront compte de ce
que les ajustements auront changé — un mineur qu'un ajustement rend caduc se ferme au cadrage
d'EP-15, avec la décision qui le rend caduc.

## Ce qui en fait partie

- les constats du contrat reportés d'EP-14 (« Constats reçus ») : les exemples manquants et les
  mineurs des relectures de L42p, L42q, L42r et L42s (#774 et ses sous-issues), le délai de paiement
  d'une ligne de main-d'œuvre (#785), l'horizon et le cycle de liaisons pour la fusion (#788, part
  « fusion »), les comptes rendus d'import et de fusion (#789), la fusion sans révision en cours
  (#790), l'outillage du témoin (#792), les exemples des chronologies (#803) ; EP-15 a ramené à lui
  #786, la part « saisies » de #788 et #791 (décisions de l'auteur du 2026-10-18), et #802 si
  l'auteur le décide ;
- l'adoption fine par les écrans de ce qu'EP-14/L42s a écrit au contrat et qu'aucune issue d'EP-15
  ne porte : la réactivation d'une catégorie sous une nature désactivée et la désactivation d'une
  nature en cascade, les catégories nommées par le refus d'un changement de type, l'import rejeté
  entier, le poste sans total, la saisie du lotissement pendant un traitement de fond, les tâches
  nommées par le refus d'un poste hors de son lot ;
- les mineurs du front reportés d'EP-14 et d'EP-03 (« Constats reçus ») ;
- l'extension du harnais d'accessibilité aux dialogues, aux menus et aux éditeurs ouverts (#782,
  option A), que l'infobulle, le panneau d'aide et l'historique des messages d'EP-15 rendent plus
  nécessaire encore ;
- les navigateurs et les largeurs d'affichage (US-0290), reprises d'EP-14 puis d'EP-15 telles
  quelles ;
- les reliquats des tests du front (#781, #784) et l'e2e de la grille instable sous charge (#776).

## Ce qui n'en fait pas partie

- les ajustements décidés par la validation : EP-15 ;
- le comportement réel des écrans : l'EPIC de leur domaine ;
- la recette sur Safari réel et sur les terminaux mobiles, et la version majeure précédente des
  navigateurs : EP-13, sur la plateforme déployée.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-CMP-0010-A` | Navigateurs et affichage | début — close en EP-13 | US-0290 |

Les autres travaux ne réalisent aucune exigence en propre : comme en EP-14 et en EP-15, leurs tests
citent les exigences du domaine dont le Vérif tient côté front, et l'EPIC du domaine les clôt.

## Opérations du contrat

Celles d'EP-15 ; les constats de contrat reçus en modifient les exemples et les refus, sans en
ajouter. La liste se fixe au cadrage.

## Préalables

EP-15 livré.

## Définition de fini

À arrêter au cadrage. Au moins :

- chaque constat reçu est soldé — appliqué dans `docs/api` ou dans le front, ou écarté dans
  `DECISIONS.md` ou dans l'issue avec sa raison ;
- les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne sur les quatre
  navigateurs de la spécification (US-0290) ;
- le harnais d'accessibilité parcourt les dialogues, les menus et les éditeurs ouverts (#782,
  option A), et l'écart qu'EP-14 a écrit sous US-0200 est levé.

## Constats reçus

Les issues du label `EP-16`, à rattacher à l'issue de l'EPIC à son ouverture. Reportés d'EP-14 par la
décision de l'auteur du 2026-10-11 (EP-14/L56), puis d'EP-15 au cadrage du 2026-10-18 :

- #774 [ex-EP-14/L42t] — contrat : les exemples manquants et les mineurs des relectures de L42p,
  L42q et L42r ; ses sous-issues #747, #752, #764, #768, #777 ;
- #785 — contrat : le délai de paiement d'une ligne de main-d'œuvre n'est pas saisissable
  (WF-DEV-0020) ;
- #788 — contrat : l'horizon et le cycle de liaisons n'ont pas de refus décrit pour la fusion —
  la part « saisies » est ramenée en EP-15 (US-0470, décision de l'auteur du 2026-10-18) ;
- #789 — contrat : les comptes rendus d'import et de fusion ne signalent ni la ligne de provision
  déplacée ni la tâche rangée ailleurs ;
- #790 — contrat : une fusion sans révision en cours n'en crée pas une au préalable (WF-REV-0050) ;
- #792 — outil : `is_active_provision` et le point fixe de `make mock-data` ;
- #795 — contrat : les mineurs de la relecture 2 de L42s ;
- #802 — contrat : la lecture du lotissement ne dit pas si une tâche porte un poste ou un lot —
  proposée à EP-15 (US-0450) au cadrage, à trancher par l'auteur ;
- #803 — contrat : les exemples manquants des refus des chronologies et du 412 du lotissement ;
- #779 — front : le refus d'une saisie sans heure ne nomme ni les rôles ni la tâche ;
- #806, #817, #819 — front : les mineurs des relectures de L44c et L44d ; #817 et #819 réduits aux
  points que le cadrage d'EP-15 ne ramène pas (EP-15, « Conception », « Ce que le cadrage
  décide ») ; #821, les mineurs de L44f, fermé au cadrage d'EP-15, la frise (#1068) le rendant caduc ;
- #782 — front : les dialogues, les menus et les éditeurs hors du harnais d'accessibilité ;
- #781, #784 — front : les reliquats des tests et du harnais ;
- #776 — outil : l'e2e « on a narrow window » de `grid.spec`, en échec sous charge ;
- #92 [US-0290] — navigateurs et largeurs d'affichage.

Reportés d'EP-03 par EP-14 le 2026-10-17, puis d'EP-15 : les vingt-cinq constats décrits dans les
« Constats reçus » d'EP-14, « Reportés d'EP-03 » — #846, #847, #872, #888, #889, #901, #902, #905,
#941, #942, #949, #951, #963, #967, #984, #990, #1005, #1010, #1012, #1021, #1023, #1024.
Quatre autres sont fermés au cadrage d'EP-15, qu'un ajustement rend caducs (décision de l'auteur
du 2026-10-18) : #872 et #937, ce qui n'était « dit nulle part », par l'historique des messages
(#1043) ; #959 et #960, l'avis de la barre, par la barre et l'historique (#1042, #1043).

## Conception

À écrire au cadrage. Celle des navigateurs, validée au cadrage d'EP-14 (EP-14, « Conception »,
« Les navigateurs »), en est le point de départ : des projets Playwright `chrome` et `msedge`
(canaux), `firefox` et `webkit`, à 1366 × 768, qui jouent les seuls parcours étiquetés des grilles,
du Gantt et des courbes ; un projet `mobile` à 360 points de large qui lit les vues d'indicateurs et
du portefeuille, sans aucune saisie ; `make e2e-browsers` étendu à tous les navigateurs, et une part
`browsers` de la chaîne au palier complet, sur un exécuteur à part. Pour #782, l'option A : sur
chaque écran, le harnais ouvre les déclencheurs `aria-haspopup`, parcourt ce qui s'ouvre, lance axe
dessus, ferme par Échap et vérifie le retour du focus.

---

## US-0290 — Navigateurs et largeurs d'affichage

- **statut** : à faire
- **exigences** : `WF-CMP-0010-A`
- **opérations** : aucune en propre
- **issue** : #92

**En tant que** chef de projet, **je veux** que les grilles, le Gantt et les courbes
fonctionnent sur le navigateur de mon poste, et consulter les indicateurs depuis mon
téléphone, **afin de** ne rien installer et de répondre à une question sur un projet loin de
mon bureau.

**Critères d'acceptation.**

- `WF-CMP-0010-A` — « Les vues d'indicateurs se lisent sur un écran de 360 points de large et
  n'y proposent aucune saisie. »
- `WF-CMP-0010-A` — « Aucune fonction n'exige une installation sur le poste. »
- propre à l'US : les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne
  sur les quatre navigateurs de la spécification — Chrome et Edge par leurs canaux
  Playwright, Firefox, et WebKit tenant lieu de Safari —, en version courante, à 1366 points
  de large ;
- écart : `WF-CMP-0010-A` — « Les grilles, le diagramme de Gantt et les courbes s'affichent et
  s'utilisent sur chacun des quatre navigateurs, dans leurs deux dernières versions majeures,
  à 1366 points de large. » : la version majeure précédente et le Safari réel ne se rejouent
  pas par l'outillage ; ils se constatent en recette, sur la plateforme déployée — EP-13.
- écart : `WF-CMP-0010-A` — « Vérifiée en recette pour Safari et les terminaux mobiles. » : la
  recette se tient sur la plateforme déployée, avec son procès-verbal — EP-13.

**Notes de réalisation.** Le harnais d'EP-01 ne joue que Chromium : c'est cette US qui lui
ajoute les quatre navigateurs — Chrome et Edge sont des canaux de Chromium dans Playwright,
Firefox et WebKit ses deux autres moteurs, et le Safari réel reste à la recette (EP-13) —
et les deux largeurs, 1366 points partout, 360 pour les vues d'indicateurs. Aujourd'hui
`make e2e-browsers` n'installe que Chromium et `playwright.config.ts` n'a qu'un projet
`chromium` : l'US ajoute les projets `chrome`, `msedge`, `firefox`, `webkit` et `mobile`, étend la
cible Make à tous les navigateurs, et donne à la chaîne une part `browsers` au palier complet, qui
ne joue que les parcours étiquetés (EP-14, « Conception », « Les navigateurs »). À 360 points, les vues
sont en lecture seule : aucun champ, aucune cellule saisissable, aucune commande d'écriture ; les
filtres de lecture restent (décision de l'auteur du 2026-10-09). L'US tient en un lot, dont l'issue
est la sienne. Reportée d'EP-02 vers EP-14 (2026-10-09), d'EP-14 vers EP-15 (2026-10-11), puis vers
EP-16 au cadrage d'EP-15 (2026-10-18).

---
id: EP-15
titre: La maquette et le contrat verrouillés après leur validation par l'auteur
statut: à planifier
depend_de: EP-14
famille: front
issue:
---

# EP-15 — Maquette et contrat : durcissement après validation

## Objet

EP-14 achève les écrans de la maquette et les parties du contrat qu'ils consomment. Le
2026-10-11, l'auteur a choisi de valider la spécification 1.0, la maquette et le contrat — par
des pull requests de cadrage et d'ajustement, après la fusion d'EP-03 puis d'EP-14 dans
`main` — avant de les verrouiller : polir un contrat et des écrans encore appelés à changer
ferait payer deux fois chaque ajustement, au front comme au back.

EP-15 porte ce verrouillage : les constats de contrat qu'EP-14 a reportés, l'adoption fine par
les écrans de ce que le contrat a gagné, l'accessibilité des dialogues et des menus, les
navigateurs. Il se cadre une fois la validation faite, et ses US, sa conception et son plan de
lots tiendront compte de ce qu'elle aura changé.

## Ce qui en fait partie

- les constats de contrat reportés d'EP-14 (« Constats reçus »), dont la part d'un total nul
  (WF-IND-0010) au contrat et à l'écran ;
- l'adoption par les écrans de ce qu'EP-14/L42s écrit au contrat : la réactivation d'une
  catégorie sous une nature désactivée et la désactivation d'une nature en cascade, les
  catégories nommées par le refus d'un changement de type, la déclaration d'un risque
  (`declare_risk`), le compte rendu préalable de la fusion et sa confirmation, l'import rejeté
  entier, le poste sans total, la saisie du lotissement pendant un traitement de fond, les tâches
  nommées par le refus d'un lot hors de son poste ;
- l'extension du harnais d'accessibilité aux dialogues, aux menus et aux éditeurs ouverts
  (#782) ;
- les navigateurs et les largeurs d'affichage (US-0290), reprises d'EP-14 telles quelles ;
- les reliquats des tests du front (#781, #784) et l'e2e de la grille instable sous charge
  (#776).

## Ce qui n'en fait pas partie

- la validation elle-même : l'auteur la mène par ses pull requests de cadrage et d'ajustement,
  entre EP-14 et EP-15 ;
- le comportement réel des écrans : il arrive avec l'EPIC de leur domaine ;
- les formulaires du risque (#763) : EP-08.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-CMP-0010-A` | Navigateurs et affichage | début — close en EP-13 | US-0290 |

Les autres travaux ne réalisent aucune exigence en propre : comme en EP-14, leurs tests citent
les exigences du domaine dont le Vérif tient côté front, et l'EPIC du domaine les clôt.

## Opérations du contrat

Celles d'EP-14 ; la liste se fixe au cadrage, après la validation.

## Préalables

EP-14 livré ; la spécification 1.0, la maquette et le contrat validés par l'auteur.

## Définition de fini

À arrêter au cadrage. Au moins :

- chaque constat reçu est soldé — appliqué dans `docs/api` ou dans le front, ou écarté dans
  `DECISIONS.md` avec sa raison ;
- les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne sur les quatre
  navigateurs de la spécification (US-0290) ;
- le harnais d'accessibilité parcourt les dialogues et les menus, ou l'auteur confirme l'écart
  qu'EP-14 a écrit sous US-0200.

## Constats reçus

Reportés d'EP-14 par la décision de l'auteur du 2026-10-11 (EP-14/L56), à rattacher à l'issue
d'EP-15 à son ouverture :

- #774 [EP-14/L42t] — contrat : les exemples manquants (#764), le compte rendu d'import et les
  paramètres des refus (#768), la part d'un total nul (WF-IND-0010), les indices du portefeuille
  (#777), les mineurs des relectures de L42p et de L42q (#747, #752) ;
- #785 — contrat : le délai de paiement d'une ligne de main-d'œuvre (WF-DEV-0020) ;
- #786 — contrat : la tâche porteuse de la provision, à la déclaration d'un risque (WF-RIS-0010) ;
- #787 — spécification : le retour d'un risque écarté sur une structure sans tâche, décidé par
  l'auteur — refusé par `at_least_one_task`, comme la déclaration —, à écrire au contrat avec son
  constat de spécification ;
- #788 — contrat : l'horizon et le cycle de liaisons, pour les saisies et pour la fusion ;
- #789 — contrat : les comptes rendus d'import et de fusion, qui ne signalent ni la provision
  déplacée ni la tâche rangée ailleurs ;
- #790 — contrat : la fusion sans révision en cours (WF-REV-0050) ;
- #791 — outil : le témoin, dont la révision 102 ne reprend pas l'avenant 2 (WF-REV-0100) ;
- #792 — outil : `is_active_provision` et le point fixe de `make mock-data` ;
- #795 — contrat : les mineurs de la relecture 2 de L42s ;
- #782 — front : les dialogues, les menus et les éditeurs hors du harnais d'accessibilité ;
- #781, #784 — front : les reliquats des tests et du harnais ;
- #776 — outil : l'e2e « on a narrow window » de `grid.spec`, en échec sous charge ;
- #779 — front : le refus d'une saisie sans heure, qui ne nomme ni les rôles ni la tâche ;
- #802 — contrat : la lecture du lotissement ne dit pas si une tâche porte un poste ou un lot,
  si bien qu'EP-14/L44c confirme toute suppression ;
- #803 — contrat : les exemples manquants des refus des chronologies et du 412 du lotissement ;
- #806 — front : les mineurs de la relecture 1 d'EP-14/L44c, le lotissement dans sa grille ;
- #92 [US-0290] et #127.

Reportés d'EP-03, par EP-14, le 2026-10-17 : les vingt-cinq constats qu'EP-03 avait reportés vers
EP-14, reportés → EP-15 par la décision de l'auteur du 2026-10-17, EP-14 resserrant son périmètre
avant la validation (EP-14/L56) ; leurs issues sont retitrées « [EP-15] … » et portent la
décision. Les dix-neuf premiers sont décrits dans les « Constats reçus » d'EP-14, « Reportés
d'EP-03 », qui en garde la trace.

- #846 — doc : le guide dit encore à venir la confirmation de #836 ;
- #847 — front : la source commune des rôles répondus n'est éprouvée que dans un sens, et le test
  d'axe de la matrice en fait deux ;
- #872 — défaut : un import refusé après la fermeture de son formulaire n'est dit nulle part ;
- #888 — front : trois mineurs du tour 3 d'US-0350/L5b (test sans Redis, own inconditionnel, use
  client d'un utilitaire de test) ;
- #889 — front : les écritures des rôles et de la matrice ne retiennent pas la navigation (#688) ;
- #901 — front : la liste garde les refus des lectures passées, qui ne s'affichent plus (#849) ;
- #902 — front : un test importe RouterContext d'un module privé de Next ;
- #905 — test : des tests du front écrivent des espaces insécables littéraux, qu'ESLint ne relève
  pas ;
- #937 — front : le refus d'une écriture lancée avant un changement de lecture n'est dit nulle part
  ;
- #941 — front : une confirmation d'anonymisation n'écrit rien sans le dire quand la ligne est
  occupée ;
- #942 — front : la confirmation d'anonymisation n'énumère pas tout ce que l'anonymisation fait ;
- #949 — front : la désactivation reste offerte pendant que le lien de la même ligne est en route ;
- #951 — front : aucun test ne dit où tombe le focus quand le dialogue d'un lien se ferme par-dessus
  la création ;
- #959 — front : le focus tombe sur la page quand on ferme l'avis des écritures refusées de la barre
  ;
- #960 — front : l'avis de la barre dit le nombre des écritures refusées, sans dire laquelle,
  pourquoi ni ce qui reste possible ;
- #963 — front : deux finitions de l'écran et du parcours du journal d'audit ;
- #967 — front : deux finitions du parcours et de la cellule de l'action du journal ;
- #984 — front : le test de l'aboutissement de la lecture des comptes montre un compte rendu d'une
  autre tâche ;
- #990 — front : « Adresse portée par le compte Compte anonymisé » ;
- #1005 — front : la liste des refus de compte est recopiée dans refusedState au lieu de passer par
  ACCOUNT_REFUSALS ;
- #1010 — front : un auteur choisi que le journal d'audit ne retient plus s'affiche par son
  identifiant ;
- #1012 — front : la documentation de la page des comptes dit encore qu'un refus ne vise qu'une
  période ;
- #1021 — test : citations manquantes et test de flux trop rigide (US-0440/L3) ;
- #1023 — écran : « en attente » affiché un rendu avant la page du refus (US-0440/L3b) ;
- #1024 — écran : « Session terminée » renvoie à une reconnexion qui ne dit pas l'issue de la
  restauration (US-0440/L3b).

## Conception

À écrire après la validation de l'auteur. Celle des navigateurs, validée au cadrage d'EP-14
(EP-14, « Conception », « Les navigateurs »), en est le point de départ.

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
est la sienne.

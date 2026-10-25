---
id: EP-17
titre: La maquette finie hors contrat — accessibilité des dialogues, mineurs des écrans, stabilité restante des parcours, cosmétique
statut: à planifier
depend_de: EP-16
famille: front
issue:
---

# EP-17 — Maquette : finitions et accessibilité

## Objet

EP-16 fige le contrat : il garde tout ce qui touche le contrat ou peut le toucher, et reporte le
reste ici (décision de l'auteur du 2026-10-22, au cadrage d'EP-16). EP-17 reçoit donc les
finitions de la maquette qui ne demandent que le front et son harnais :
- l'extension du harnais d'accessibilité aux dialogues, aux menus et aux éditeurs ouverts ;
- les mineurs des composants partagés et des écrans ;
- la stabilité restante des parcours de bout en bout ;
- le cosmétique, marqué comme tel.

Il vient après EP-16 parce qu'il ne change pas le contrat, que les EPIC de domaine servent dès
qu'EP-16 est livré. Il peut avancer en parallèle d'eux.

## Ce qui en fait partie

- l'extension du harnais d'accessibilité aux dialogues, aux menus et aux éditeurs ouverts (#782,
  option A ; #784 ; #819, point 1) ;
- les mineurs des composants partagés et des écrans reportés d'EP-14, d'EP-03 et d'EP-15
  (« Constats reçus ») ;
- les ajustements de la validation de la maquette du 2026-10-23 qui ne touchent pas le contrat
  (#1395 part front, #1396, #1397, #1399, #1400, #1401) et deux défauts visibles du front (#1438,
  #1428), reçus au recadrage d'EP-16 du 2026-10-25 (« Constats reçus ») ;
- la lenteur du navigateur à quitter une grille de mille tâches (#1230), une lenteur du produit ; la
  stabilité restante des parcours de bout en bout (#1263, #1145, #776, #1264) est revenue à EP-16 le
  2026-10-25, comme durcissement (US-0590b) ;
- le cosmétique, chaque constat marqué comme tel dans « Constats reçus ».

## Ce qui n'en fait pas partie

- tout ce qui touche le contrat : EP-16 ;
- les navigateurs et les largeurs d'affichage (US-0290) : EP-13 ;
- le comportement réel des écrans : l'EPIC de leur domaine.

## Exigences réalisées

À fixer au cadrage. Comme en EP-14 et en EP-15, les tests citent les exigences du domaine dont le
Vérif tient côté front. L'écart qu'EP-14 a écrit sous WF-IHM-0100-A, pour US-0200, se lève avec
#782.

## Opérations du contrat

Aucune en propre : celles que les écrans touchent, sans en ajouter ni en modifier.

## Préalables

EP-16 livré.

## Définition de fini

À arrêter au cadrage. Au moins :

- chaque constat reçu est soldé : corrigé dans le front, ou écarté dans l'issue, avec sa raison ;
- le harnais d'accessibilité parcourt les dialogues, les menus et les éditeurs ouverts (#782,
  option A), et l'écart qu'EP-14 a écrit sous US-0200 est levé.

## Constats reçus

Reportés d'EP-16 à son cadrage (décision de l'auteur du 2026-10-22), à rattacher à l'issue de
l'EPIC à son ouverture. Leur label et leur titre passent à `EP-17` au cadrage d'EP-16.

**Reçus au recadrage d'EP-16 (2026-10-25, #1445)**, par la règle de l'auteur — ne reste dans EP-16
que ce qui concerne le durcissement ou le contrat —, label et titre déjà `EP-17` :

- les ajustements de la validation de la maquette du 2026-10-23, décisions de l'auteur écrites dans
  chaque issue :
  - #1395 — front : la matrice des risques sur fond blanc, la couleur sur les bulles, les seuls
    risques identifiés ; sa part contrat (le décompte de `cells`) est écrite par EP-16 (US-0700) ;
  - #1396 — front : le Kanban filtré par libellé et par tâches prêtes, la marque « prête à
    démarrer », le compteur de la colonne ;
  - #1397 — front : la projection sur `kinds`, pour que la grille de planning ne montre pas les
    lignes de devis que le faux back rend ;
  - #1399 — doc, front : le guide et `MockupNotice` disent ce que le faux back n'applique pas ;
  - #1400 — front : l'écran d'un projet mène directement à sa révision en cours ;
  - #1401 — front : la liste des projets filtrée par défaut sur Chiffrage et En cours ;
- deux défauts visibles du front :
  - #1438 — front : la commande « Déclarer un risque » de l'écran des révisions ne fait rien
    (`OfferedElsewhere`, ou un lien vers l'écran des risques) ;
  - #1428 — front : l'export PNG du Gantt porte une colonne des noms des tâches (option B de
    l'auteur, #1426) ;
- les mineurs du front relevés par les derniers lots d'EP-15 :
  - #1364 — front : `ConfirmedCommand` laisse rouvrir la commande pendant l'écriture (défaut n° 24) ;
  - #1377 — front : le refus tardif de « Modifier » un risque n'est pas redit au retour ;
  - #1386 — front : trois mineurs de la matrice repliable gardée ;
  - #1421 — front : la tenue de la légende des jours chômés dure un tick ;
  - #1424 — front : deux mineurs du test de provenance de l'écran des chronologies ;
  - #1430 — front : des inscriptions de l'historique sans objet hors des trois de #1181 ;
  - #1432 — front : `clear` de `cell-writes` hors de la référence synchrone ;
  - #1384, point 2 — front : le libellé et l'icône de `ReferenceForm` pour « Réexaminer » (l'issue
    reste en EP-16 pour son point 1, et se ferme avec lui ; le point se reprend ici au cadrage) ;
  - #1144 — front : la largeur mesurée de la barre des grilles denses n'est pas éprouvée au
    redimensionnement (décision de l'auteur du 2026-10-25 : EP-17, non repris par EP-15).

**Le harnais d'accessibilité.**

- #782 — front : les dialogues, les menus et les éditeurs hors du harnais d'accessibilité (option A,
  décision de l'auteur du 2026-10-11) ;
- #784 — front : les mineurs du harnais d'accessibilité ; ses points 1, 4, 6, 7, 12 et 13 sont
  **cosmétiques** (rédaction du guide, de la note et d'un titre de test) ;
- #819 — front : les mineurs de la relecture 1 de L44d :
  - le point 1, le focus d'une cellule refusée distingué par la seule couleur, va avec #782 ;
  - les points 4, 13 et 14 restent ;
  - le point 15 est **cosmétique**.

**La lenteur du produit.**

- #1230 — front : quitter un écran de grille de mille tâches coûte plusieurs secondes au navigateur
  (#1218). La stabilité restante des parcours (#1145, #1263, #776, #1264), d'abord reportée ici, est
  revenue à EP-16 le 2026-10-25 (US-0590b) : elle relève du durcissement.

**Les mineurs des composants partagés et des écrans.**

- #806 — front : les mineurs de la relecture 1 de L44c ; son point 14 relève de #803, en EP-16 ;
- #1180 — front : l'historique des messages et le suivi des tâches survivent à une session
  expirée ;
- #1209 — front : à 911 de large, replier les cartes ou plafonner la grille empilée ;
- #781 — test : `held()` n'a pas remplacé toutes les retenues faites à la main ;
- #847 — front : la source commune des rôles répondus n'est éprouvée que dans un sens ;
- #889 — front : les écritures des rôles et de la matrice ne retiennent pas la navigation ;
- #901 — front : la liste garde les refus des lectures passées ;
- #902 — test : un test importe `RouterContext` d'un module privé de Next ;
- #941 — front : une confirmation d'anonymisation n'écrit rien sans le dire quand la ligne est
  occupée ;
- #942 — front : la confirmation d'anonymisation n'énumère pas tout ce que l'anonymisation fait ;
- #949 — front : la désactivation reste offerte pendant que le lien de la même ligne est en route ;
- #951 — test : où tombe le focus quand le dialogue d'un lien se ferme par-dessus la création ;
- #984 — test : le test de l'aboutissement de la lecture des comptes montre un compte rendu d'une
  autre tâche ;
- #1005 — front : la liste des refus de compte recopiée dans `refusedState` ;
- #1010 — front : un auteur choisi que le journal d'audit ne retient plus s'affiche par son
  identifiant ;
- #1021 — test : citations manquantes et test de flux trop rigide ;
- #1024 — écran : « Session terminée » renvoie à une reconnexion qui ne dit pas l'issue de la
  restauration.

**Le cosmétique**, marqué comme tel :

- #846 — doc : le guide dit encore à venir la confirmation de #836 ;
- #888 — front : trois mineurs du tour 3 d'US-0350/L5b ;
- #905 — test : des espaces insécables littéraux dans les tests du front ;
- #963 — front : deux finitions de l'écran et du parcours du journal d'audit ;
- #967 — front : deux finitions du parcours et de la cellule de l'action du journal ;
- #990 — front : « Adresse portée par le compte Compte anonymisé » ;
- #1012 — doc : la documentation de la page des comptes ;
- #1023 — écran : « en attente » affiché un rendu avant la page du refus.

## Conception

À écrire au cadrage.

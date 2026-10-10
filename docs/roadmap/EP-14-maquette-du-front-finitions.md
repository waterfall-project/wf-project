---
id: EP-14
titre: Les écrans de la maquette achevés, commandes branchées et constats du contrat soldés
statut: en cours
depend_de: EP-02
famille: front
issue: 599
---

# EP-14 — Maquette du front : finitions

## Objet

Achever ce qu'EP-02 n'a pas fini quand il a été fusionné dans `main`, le 2026-10-09, pour
qu'EP-03 démarre sans attendre (décision de l'auteur) : les commandes d'écriture que la maquette
montre depuis la décision du 2026-10-08, branchées au contrat et répondues par le faux back sans
rien conserver ; les parties du contrat que ces commandes ont révélées ; l'univers témoin à
l'échelle de toute la structure ; l'accessibilité minimale et les quatre navigateurs.

Cet EPIC avance en parallèle d'EP-03 : il ne touche ni le contrat des comptes, des rôles et de la
session, ni le journal d'audit, qu'EP-03 réalise. Il reprend les règles, la conception et le faux
back d'EP-02, qui font foi pour lui.

## Ce qui en fait partie

- l'écran des sauvegardes, sa grille et ses commandes — sauvegarder, conserver, télécharger,
  restaurer —, puis le formulaire de planification et de la copie externe (#519) ;
- les paramètres des risques et des indicateurs (#512) ;
- les paramètres du projet — créer un projet, son identité et son cycle de vie (#583, #524), les
  sous-projets et les contributeurs (#584), le lotissement et le jalonnement (#585) ;
- les parties du contrat restantes : les nœuds retenus d'un lotissement filtré (#574), les
  écritures des ressources et des réglages (#575), la catégorie provision par défaut (#579), le
  rattachement au lotissement (#586), les sauvegardes (#588), le projet (#590), les sous-projets
  et les contributeurs (#592) — chacune suivie de son adoption par l'écran ;
- l'univers témoin : les lectures sur toute la structure, et les risques à l'échelle (#528, qui
  ferme #287) ; les relectures lentes sous charge (#500) ;
- l'accessibilité minimale (US-0200) et les navigateurs (US-0290), reprises d'EP-02 telles
  quelles.

## Ce qui n'en fait pas partie

- le comportement réel des écrans : il arrive avec l'EPIC de leur domaine — EP-04 pour le projet,
  EP-05 pour le référentiel, EP-13 pour les sauvegardes ;
- les comptes, les rôles, la session et le journal d'audit : EP-03 ;
- la restauration depuis un fichier déposé (#350) : EP-03, US-0440.

## Exigences réalisées

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0100-A` | Accessibilité minimale | entière | US-0200 |
| `WF-CMP-0010-A` | Navigateurs et affichage | début — close en EP-13 | US-0290 |

Les commandes des écrans ne réalisent aucune exigence en propre : comme en EP-02, leurs tests
citent les exigences du domaine dont le Vérif tient côté front, et l'EPIC du domaine les clôt.

## Opérations du contrat

Celles d'EP-02, et les écritures que les écrans branchent, avec les lectures qui les préparent :
les sauvegardes (`startBackup`, `retainBackup`, `downloadBackup`, `startRestore`,
`getBackupSchedule`, `setBackupSchedule`, `listExternalBackupLocations`,
`testExternalBackupLocation`), les réglages (`getReferenceSettings`, `updateReferenceSettings`),
le projet (`createProject`, `updateProject`, `getProjectNextState`), les sous-projets et les
contributeurs (`createSubproject`, `updateSubproject`, `deleteSubproject`, `listContributors`,
`setContributors`, `listContributorSuggestions`), le lotissement et le squelette
(`getWorkBreakdown`, `setWorkBreakdown`, `generatePlanningSkeleton`), le rattachement d'une tâche
au lotissement (`updateTaskFacet`, `listNodes`), les chronologies (`listTimelines`,
`createTimeline`, `deleteTimeline`).

Ce qui manque au contrat pour ces écrans est connu et se fait en quatre parties de #507, avant
les écrans qui les consomment (« Conception », « Modifications du contrat ») : les commandes
qu'une sauvegarde, un sous-projet, une révision — le squelette — et un projet — les chronologies —
listent, les refus par champ que les écritures ne disent pas ou disent mal, les exemples de succès
qui manquent, les filtres et le tri des sauvegardes, les nœuds retenus d'un lotissement filtré, la
catégorie provision par défaut.

## Préalables

EP-02 fusionné dans `main` ; la branche `epic/EP-14` tirée de `main` après cette fusion.

## Définition de fini

- chaque commande d'écriture qu'un écran de la maquette montre est branchée sur l'opération du
  contrat, gardée par la permission et les commandes disponibles, et dit son succès et son refus ;
- un contrôle automatisé de contraste ne relève aucun écart au niveau AA, en clair comme en sombre ;
- les parcours des grilles, du Gantt et des courbes se jouent dans la chaîne sur les quatre
  navigateurs de la spécification ;
- les constats du contrat que ces écrans ont faits sont soldés — appliqués dans `docs/api`, ou
  écartés dans `DECISIONS.md` avec leur raison — et aucun n'est resté dans une tête.

## Constats reçus

Repris d'EP-02 à la coupure du 2026-10-09, renommés `[EP-14/Ln]` en gardant leur numéro de lot,
et rattachés à #599 :

- #512 [EP-14/L43] — les commandes du référentiel et des sauvegardes : L43c (#519, l'écran des
  sauvegardes) livré par #607 ; restent L43d (la planification et la copie externe, fin de #519),
  L43e (les paramètres des risques et des indicateurs) et L43f (l'adoption par la grille des
  sauvegardes des commandes, du tri et des filtres que L42h écrit au contrat) ;
- #513 [EP-14/L44] — les commandes des paramètres du projet : L44a (#583, #524) livré par #608,
  L44b (#584) par #609 ; reste #585, découpé au cadrage en L44c (le lotissement et les
  chronologies) et L44d (le squelette et le rattachement) ;
- #528 [EP-14/L45] — l'univers témoin à l'échelle, et #287 ; découpé au cadrage en L45a (les
  lectures sur toute la structure) et L45b (les risques à l'échelle et le Kanban, qui ferme #287) ;
- #507 [EP-14/L42] — ses parties de contrat ouvertes, regroupées au cadrage par l'écran qui les
  consomme : L42h (#588, et la part des réglages de #575), L42i (#590, #592), L42j (la part des
  ressources de #575), L42k (#586, #574, #579) ;
- #84 [US-0200] et #126 ; #92 [US-0290] et #127 : l'issue de l'US est celle de son lot ;
- #500 — relectures lentes sous charge : fermé au cadrage, couvert par EP-02/L46 (décision de
  l'auteur) ;
- #591 — le critère d'US-0210 réécrit en écart par le lot de cadrage, EP-14/L50, les commandes du
  projet étant entrées avec L44a et L44b.

Trois lots étaient commencés à la coupure, sur leur branche, et sont repartis d'`epic/EP-14` :
EP-14/L43c, EP-14/L44a et EP-14/L44b, livrés. Relevé par EP-02/L46, sans issue à la coupure :
`DenseGrid` ne mémorise ni ses lignes ni ses cellules, si bien que chaque déplacement de la cellule
active les rend toutes ; aucun défaut n'est démontré en production. Ouvert au cadrage en
`[EP-14] front : DenseGrid ne mémorise ni ses lignes ni ses cellules` (#620), décision
reporté → EP-06, qui construit la grille de planning réelle et pourra mesurer.

## Conception

Celle d'EP-02, qui fait foi : arborescence du front, faux back et exemples, composants partagés,
commandes du référentiel (`CommandedList`, `ReferenceForm`, `CellCommand`), refus par champ,
défauts nommés du guide. EP-14 n'a ni table, ni migration, ni module du noyau : il écrit du front,
des exemples et des parties du contrat, et des générateurs de l'univers témoin (`wftools`) — un
outil écrit en passant, qui ne change pas sa famille. Ce qui suit est ce qu'il ajoute, validé au
cadrage du 2026-10-09.

### Ce que le cadrage décide

- **Aucune US pour les commandes d'écriture.** Elles ne réalisent aucune exigence en propre, et
  une US qui citerait WF-REF, WF-PRJ ou WF-ADM devrait reprendre chaque phrase de leur Vérif et
  faire passer en « fin — amorcée en EP-14 » des exigences qu'EP-04, EP-05 et EP-13 tiennent pour
  entières. Les commandes restent des lots techniques, parties des lots repris L42 à L45 et
  nouveaux lots `[EP-14/Ln]`, sous l'issue de l'EPIC (#599), comme le README le permet pour cet
  EPIC ; la définition de fini les porte. Écarté : une US sans exigence, sur le modèle d'US-0210 —
  un statut `fini` de plus à lire, pour des critères qui ne seraient que la définition de fini.
- **Deux entorses assumées, déjà décidées.** Le critère d'US-0250 qui laissait l'écran des
  sauvegardes « sans déclencher ni sauvegarde ni restauration », et celui d'US-0210 qui voulait
  qu'« aucun de ces écrans ne propose de créer ni de modifier », sont contredits par les commandes
  que la maquette montre depuis la décision de l'auteur du 2026-10-08 : les notes de réalisation
  d'EP-02 le disent pour le premier, et le second est réécrit en écart dans le fichier d'EP-02
  (#591), par le lot de cadrage.
- **La branche du cadrage.** Le fichier d'EP-14 vit sur `epic/EP-14`, où L49, L43c, L44a et L44b
  l'ont déjà modifié : le cadrage s'écrit sur une branche tirée d'elle et y revient par une pull
  request, non par `roadmap/EP-14-cadrage` vers `main`. Conséquence : le statut `en cours` du
  README, les numéros d'issues et l'écart d'US-0210 n'atteignent `main` qu'à la livraison
  d'EP-14 ; lu depuis `main`, le README dira « à planifier » tant qu'il dure, et c'est accepté.
- **Taille des lots.** L43c, L44a et L44b ont fait de 1,6 à 2,5 fois leur estimation
  (2 532, 1 775 et 2 369 lignes réelles) : les lots de ce plan sont coupés à 1 200 lignes
  estimées, et un lot d'écran qui approche le plafond se découpe plutôt que de grossir.

### Modifications du contrat

Quatre parties de #507, chacune avec son entrée dans `docs/api/DECISIONS.md`, ses exemples,
`make inventory` et `make generate-client`, faites **avant** le lot d'écran qui les consomme.
Quand l'écran existe déjà — L43b, L43c, L44a, L44b —, la partie de contrat l'adopte dans le même
lot, comme EP-02/L42e et L42f l'ont fait ; sinon l'adoption revient au lot d'écran. Écarté : une
seule partie pour les sept constats, qui dépasserait le plafond ; laisser chaque lot d'écran
modifier le contrat en passant, contre la règle « le contrat d'abord ».

| Partie | Ce qu'elle ferme | Contenu | Consommateur |
|---|---|---|---|
| L42h — sauvegardes et réglages | #588, la part des réglages de #575 | Chaque sauvegarde liste ses commandes (`Backup.available_commands` : conserver, ne plus conserver, télécharger, restaurer), indisponibles avec leur condition pendant qu'une sauvegarde ou une restauration court, ou quand sa vérification a échoué — écarté : les déduire de son état dans le front, que la conception d'EP-02 interdit ; les 409 nommés de `startBackup` et `startRestore` pendant qu'une court ; le refus d'une date confirmée qui n'est pas celle de la sauvegarde ; le nom et la longueur du fichier de `downloadBackup` ; les filtres et le tri de `listBackups` (WF-IHM-0130) ; l'exemple de succès de `setBackupSchedule`. L'exemple de succès d'`updateReferenceSettings`, ses refus par champ — des bornes non ordonnées, un seuil d'alerte qui n'est pas sous son seuil de vigilance, chacun à son champ —, sa version périmée. | L43d, L43e, L43f |
| L42i — projet, sous-projets, contributeurs | #590, #592 | Le déclencheur du prochain état énuméré, et ce que `getProjectNextState` rend d'un projet en cours ou terminal ; la probabilité de gain annoncée figée, le statut et le pointeur de son refus ; le code pris nommant le projet qui le porte, par son libellé, comme L42g l'a décidé pour le référentiel ; les bornes des deux taux. Un sous-projet liste ses commandes (modifier, supprimer), la suppression indisponible avec sa condition quand des coûts réels lui sont imputés ou qu'une révision marquée le cite, son 409 nommé ; le code pris nommant le sous-projet qui le porte ; le refus par champ d'un compte inconnu ou désactivé dans `setContributors` ; une proposition nomme son nœud et ses rôles, dit si le compte est actif, et `listContributorSuggestions` s'appuie sur les lignes de devis comme WF-PRJ-0070. Les écrans de L44a et L44b l'adoptent dans le lot. | écrans L44a, L44b |
| L42j — ressources | la part des ressources de #575 | Les refus par champ des écritures de L43b : le code pris nommant l'objet qui le porte, un parent ou un nœud désactivé, un nœud déplacé sous lui-même ou ses descendants, une catégorie hors main-d'œuvre ou un rattachement désactivé d'un rôle (WF-REF-0090), des heures hors bornes, la version périmée. Les écrans de L43b l'adoptent dans un lot propre, L43g (#685), ajouté après la part de contrat pour tenir le plafond. | écrans L43b, par L43g |
| L42k — lotissement, rattachement, chronologies, provision | #586, #574, #579 | La révision liste le squelette parmi ses commandes (`generate_skeleton`), indisponible dès que la structure principale comporte une tâche, le 409 de `generatePlanningSkeleton` nommé ; les refus par champ du rattachement (WF-PLA-0170) : un lot ou un poste déjà porté, en nommant la tâche qui le porte, une tâche rattachée à un poste et à un lot à la fois — `WORK_PACKAGE_OUTSIDE_ORDER_ITEM` existe ; le projet liste les chronologies parmi ses commandes (`manage_timelines`), `deleteTimeline` restant un 204 sans 409 — WF-DAT-0080 marque supprimée une chronologie qu'une révision marquée cite, il ne refuse pas ; les exemples de succès de `setWorkBreakdown`, `createTimeline` et `generatePlanningSkeleton`. Les nœuds retenus d'un lotissement filtré (#574). La catégorie provision par défaut (#579), option (a) de l'auteur — « la même nature si elle est employée » —, **après** que l'auteur a écrit les phrases de WF-REF-0030 et WF-REF-0040 : aucun agent ne modifie la spécification. | L44c, L44d |

Les noms des codes et des conditions ci-dessus sont ceux que le cadrage propose ; chaque partie
les arrête dans `DECISIONS.md`, avec les options écartées.

### Les écrans

- **La planification et la copie externe des sauvegardes (L43d).** Un formulaire, à une session
  qui peut modifier les sauvegardes (`backups.write`), qui envoie la planification **entière**
  depuis la lecture (`setBackupSchedule` est un `PUT`) : activée ou suspendue, fréquence, heure,
  jour, rétention. La copie externe choisit un emplacement parmi ceux que l'installation déclare
  (`listExternalBackupLocations`) — jamais un secret ni une adresse —, un chemin relatif et un
  nombre de copies au moins égal à la rétention de la plateforme, vérifié au front avant l'envoi
  et dit au champ quand le serveur le refuse (422, exemples existants) ; « Tester l'emplacement »
  appelle `testExternalBackupLocation` et dit son résultat. L'heure se saisit en temps universel,
  comme le contrat le dit, l'heure locale équivalente affichée à côté — écarté : convertir au
  front, où le changement d'heure rend la conversion ambiguë. La grille de L43c adopte les
  commandes, le tri et les filtres que L42h apporte au contrat dans un lot propre, L43f, ajouté
  au cadrage après L42h — écarté : les adopter dans L42h, qui aurait dépassé le plafond d'un lot.
- **Les paramètres des risques et des indicateurs (L43e).** Deux formulaires, un par écran :
  les six bornes **et les seize zones** de la matrice sur `/reference/risks`, à une session qui
  porte `risk_settings.write` ; les quatre seuils et le délai entre deux revues sur
  `/reference/indicators`, sous `indicator_settings.write`. Chacun envoie par
  `updateReferenceSettings` le seul sous-objet de son écran et la version, vérifie au front que
  les bornes sont ordonnées et chaque seuil d'alerte sous son seuil de vigilance, dit au champ ce
  que le serveur refuse. Hors du formulaire : la devise, non modifiable (WF-REF-0140), et la
  langue par défaut de l'installation, qui est à EP-03 (WF-INTF-0160, ligne `installation`) —
  EP-14 ne touche pas son domaine : L42h retire `default_language` du schéma d'écriture
  (`ReferenceSettingsWrite`), aucun écran de la maquette ne l'écrivant et aucune permission du
  référentiel ne le gardant ; il reste en lecture. Écarté : saisir les bornes seules, la matrice
  restant à moitié paramétrable.
- **Le lotissement (L44c)** se saisit **dans la grille arborescente** existante : ajouter,
  renommer, supprimer un poste, un lot, un livrable, au menu contextuel et à la barre de la
  grille, chaque geste renvoyant le lotissement **entier** depuis une lecture entière — le
  compteur d'une lecture filtrée est nul, et « un écran qui filtre relit la liste entière avant
  d'écrire » (décision de L42f). La suppression d'un poste ou d'un lot que des tâches portent est
  confirmée, en disant que les tâches restent et perdent leur rattachement (WF-PLA-0170).
  Écarté : un dialogue qui éditerait tout l'arbre, qui doublerait la grille ; des opérations par
  élément, que le contrat n'a pas et dont l'écriture entière a été décidée.
- **Les chronologies (L44c)** se créent par leur libellé dans un dialogue de l'écran des
  chronologies et se suppriment après confirmation, comme le projet liste `manage_timelines`.
  Écarté : garder par la seule permission `planning.write` de la session — un objet du projet
  liste ses commandes, règle d'EP-02.
- **Le squelette (L44d)** s'offre dans **l'état vide de la grille de planning** — « aucune
  tâche » —, comme la révision liste `generate_skeleton` : l'opération vise la révision, et
  WF-PRJ-0030 ne le propose plus dès que la structure principale comporte une tâche. La réponse
  remplit la grille. Écarté : un bouton dans la section du lotissement, qui ne connaît pas la
  révision.
- **Le rattachement (L44d)** est une colonne « Rattachement » de la grille de planning : une
  cellule qui choisit un poste ou un lot parmi le lotissement lu entier, ou rien, écrite par
  `updateTaskFacet` (`order_item_id` ou `work_package_id`, jamais les deux), le refus du serveur
  dit à la cellule en nommant la tâche qui porte déjà le lot. Écarté : rattacher depuis le
  lotissement, qui ne connaît pas la révision.
- **Le porteur d'un code pris** — projet, sous-projet — est nommé par son libellé dans les
  paramètres du refus, et le formulaire le dit au champ, comme L42g l'a fait pour le référentiel.

### L'univers témoin à l'échelle (L45)

La décision 4 du cadrage de #287, option (a) de l'auteur du 2026-10-07, s'applique : les risques
751 et 753 sont portés à l'échelle de la structure de mille tâches, et les lectures qui sommaient
le seul cœur — les indicateurs du projet, la courbe des coûts, le registre des risques et sa
couverture, le Kanban, la liste du portefeuille — somment toute la structure ; les résumés « sur
le seul cœur, jusqu'à EP-02/L45 » disparaissent. Les tests du front qui assertent des valeurs du
témoin sont réécrits sur les nouvelles valeurs, dans le même lot. Écarté : un second jeu
d'exemples figé pour les tests, qui ferait deux univers.

### L'accessibilité (US-0200)

Le contrôle axe réemploie `frontend/e2e/axe.ts` et la boucle de `screens.spec.ts` sur chaque
route de `functions.json`, en clair et en sombre, à 1366 points et à **911 points** — ce que
donne un agrandissement de 150 % sur 1366, émulé par la fenêtre ; écarté : `deviceScaleFactor`,
qui ne change pas la mise en page. Un parcours clavier générique par route : Tab jusqu'au retour
au premier élément, chaque élément focalisé visible dans la fenêtre, aucune boucle fermée. Les
libellés des champs et les descriptions des images sont les règles `label` et `image-alt` d'axe.
Les écarts que le contrôle relève se corrigent dans le lot ; si leur nombre l'impose, l'US se
découpe en deux lots, harnais et écrans du référentiel et de l'administration, puis écrans du
projet. Ce harnais arrive **avant** les lots d'écran : il garde ensuite chacun d'eux.

### Les navigateurs (US-0290)

Des projets Playwright `chrome` et `msedge` (canaux), `firefox` et `webkit`, à 1366 × 768, qui
jouent les seuls parcours étiquetés des grilles, du Gantt et des courbes ; un projet `mobile` à
360 points de large qui lit les vues d'indicateurs et du portefeuille : lisibles sans défilement
horizontal, et **sans aucune saisie** — ni champ, ni cellule saisissable, ni commande
d'écriture ; les filtres de lecture restent. `make e2e-browsers` installe tous les navigateurs,
et une part `browsers` de la chaîne les joue au palier complet sur un exécuteur à part : l'image
Playwright porte Firefox et WebKit, Chrome et Edge s'installent dans le travail. Écarté : rejouer
tous les parcours sur quatre navigateurs, quatre fois le temps de chaîne ; le Safari réel et la
version majeure précédente, qui restent à la recette d'EP-13 (écarts d'US-0290).

### Ordre de construction

1. Le lot de cadrage : ce fichier, l'écart d'US-0210, les constats reçus d'EP-13, le README.
2. En parallèle : US-0200 et US-0290, dont le harnais garde ensuite chaque lot d'écran ; les
   quatre parties du contrat, L42h à L42k ; l'univers témoin, L45a puis L45b, avant que les lots
   d'écran n'assertent d'autres valeurs.
3. Les écrans, chacun après sa partie de contrat : L43d, L43e et L43f après L42h ; L44c puis L44d
   après L42k.
4. La clôture : la définition de fini constatée, chaque constat de #507 appliqué dans `docs/api`
   ou écarté dans `DECISIONS.md`.

## Notes de réalisation

L'écran des sauvegardes (#519), commencé en EP-02/L43c et repris ici (#599), reçoit sa grille et
ses commandes, la même entorse assumée au cadrage d'US-0250, qui le laissait en lecture : la liste
passe sur la grille dense, paginée par le serveur, ses colonnes choisies et élargies — le contrat ne
trie, ne cherche ni ne filtre les sauvegardes, et la grille n'en simule rien (WF-IHM-0090) —, et
chaque commande suit la permission du catalogue qui la garde (WF-ADM-0100) : à une session qui peut
modifier les sauvegardes, en déclencher une, une tâche de fond suivie comme les autres
(`startBackup`), en marquer une à conserver ou ne plus la conserver (`retainBackup`) ; à une session
qui peut restaurer la plateforme, la télécharger par une route du front qui relaie `downloadBackup`
en flux, jamais par une action serveur — le téléchargement est gardé par la permission de la
restauration (décision de l'auteur du 2026-10-09, #588) —, et la restaurer depuis une sauvegarde de
la liste (`startRestore`), après une confirmation qui énonce la date de la sauvegarde, sa
vérification et le caractère irréversible de l'opération, et exige la saisie de son identifiant
(WF-ADM-0160) ; aucune commande ne supprime une sauvegarde. Le refus d'un téléchargement ramène à
l'écran, qui le dit au-dessus de la liste et y porte le focus ; l'écran dit que le faux back ne
garde rien (`MockupNotice`). Les exemples de succès de ces écritures entrent au contrat
(`task_backup_queued`, `backup_retained`, `backup_released`, `task_restore_queued`). Ce que le
contrat ne porte pas est signalé pour #507 : les filtres et le tri de `listBackups`, le nom et la
longueur du fichier de `downloadBackup`, les commandes qu'une sauvegarde offre, et ce que refusent
`startBackup` et `startRestore` pendant qu'une sauvegarde ou une restauration court, comme une date
confirmée qui n'est pas celle de la sauvegarde. Le formulaire de la planification, de la rétention
et de la copie externe vient avec la partie suivante, L43d.

EP-02/L44, sur la décision de l'auteur du 2026-10-08 qui fait montrer à la maquette ses commandes
d'écriture (#513) — une entorse assumée au critère qui laissait les formulaires du projet à EP-04 —,
est découpé en trois parties menées en parallèle (décision de l'auteur du 2026-10-09), reprises ici
sous EP-14 : L44a (#583) le projet lui-même, L44b (#584) ses sous-projets et ses contributeurs,
L44c (#585) son lotissement et son jalonnement. L44a offre « Créer un projet » sur l'accueil (#524),
à la seule session qui porte la permission de le créer (WF-ADM-0100), indisponible tant que le
référentiel minimal est incomplet (WF-CYC-0120) : un formulaire validé côté front appelle
`createProject` — le libellé exigé (WF-PRJ-0080), le code facultatif (WF-PRJ-0010), la description —
et mène à l'écran du projet créé, que le faux back sert sous les traits du témoin. Les paramètres du
projet présentent son identité et ses faits, et leur modification (`updateProject`) comme le projet
liste sa commande `update` : le libellé, le code, la date de réception de la commande, la
description, le taux d'inflation et la probabilité de gain, saisis en pourcentages et envoyés en
rapports, celle-ci figée à partir de En cours (WF-PRJ-0090). La réponse prend la place des faits lus
tant qu'elle est plus récente, la page relue ; un refus par champ est dit au champ — le code déjà
porté par un autre projet (409) compris, depuis EP-02/L42g, qui le décrit au contrat et l'apprend au
formulaire —, la version périmée avec l'offre de relire ; l'écran dit que le faux back ne garde rien
(`MockupNotice`). Le cycle de vie, dont la sortie, irréversible, était déjà confirmée, dit le prochain
état du projet, son déclencheur et ses conditions restantes (`getProjectNextState`, WF-CYC-0050),
sans commande vers Chiffrage ni En cours (WF-CYC-0020). Les exemples de succès de ces écritures et
du prochain état entrent au contrat. Écarts au contrat relevés par L44a, pour #507 : le déclencheur
du prochain état n'est pas énuméré ; rien ne dit d'avance que la probabilité de gain est figée, ni
sous quel statut et quel pointeur `WIN_PROBABILITY_FROZEN` la refuse ; le prochain état d'un projet
en cours ou terminal n'est pas décrit ; le refus d'un code de projet déjà porté nomme le projet par
son seul identifiant, que l'écran ne connaît pas ; les bornes des deux taux ne sont pas dites.

EP-02/L44, sa partie L44b (#584), donne aux sous-projets et aux contributeurs du projet leurs
commandes, sur la décision de l'auteur du 2026-10-08 qui fait montrer à la maquette ses commandes
d'écriture (#513) — une entorse assumée au critère qui laissait ces formulaires à EP-04. Comme le
projet liste sa commande `update` — le paramétrage du projet, réservé à ses chefs de projet
(WF-PRJ-0060), indisponible sur un projet terminal —, la liste des sous-projets offre « Nouveau
sous-projet » et, sur chaque ligne, la modification et la suppression : un formulaire validé côté
front, le code et le libellé exigés (`createSubproject`, `updateSubproject`), un code qu'un autre
sous-projet porte (409 `ALREADY_EXISTS`) dit au champ ; la suppression confirmée dans la page
(`deleteSubproject`), indisponible, sa raison dite, pour un sous-projet auquel des coûts réels sont
imputés (WF-PRJ-0050). Comme le projet liste `manage_contributors`, la liste des contributeurs se
modifie entière dans un dialogue (`setContributors`) : la qualité de chacun, chef de projet ou
contributeur, son retrait, et l'inscription des comptes que le serveur propose d'après les rôles du
devis (`listContributorSuggestions`, WF-PRJ-0070), chacun confirmé, rien n'étant écrit avant
l'enregistrement ; une liste sans chef de projet est refusée avant toute demande (WF-PRJ-0060), un
refus par champ dit à la ligne du compte qu'il désigne, en le nommant. L'écriture part d'une lecture
entière, avec son compteur : la page relit la liste entière quand la grille la lit filtrée. Un
succès remplace la ligne ou la liste affichée tant qu'il est plus récent, la page relue ; le refus
d'une suppression se dit au-dessus de la liste, la version périmée avec l'offre de relire ; l'écran
dit que le faux back ne garde rien (`MockupNotice`). Les exemples de succès de ces écritures et des
propositions entrent au contrat, et le 409 d'unicité du code d'un sous-projet y est décrit dans les
termes d'EP-02/L42g ; Sacha Lefèvre, le compte proposé, est rattaché à l'atelier de câblage. Écarts
au contrat relevés par L44b, pour #507 : un sous-projet ne liste pas ses commandes, si bien que la
suppression d'un sous-projet qu'une révision marquée cite (WF-DAT-0080) n'est pas dite d'avance, et
que son refus (409) n'a ni code nommé ni exemple ; aucune commande du projet ne nomme les sous-projets,
que le front garde par `update` ; le refus par 422 d'un compte inconnu ou désactivé dans
`setContributors` n'a ni pointeur ni code nommés ; aucune opération ne liste à un chef de projet les
comptes qu'il peut inscrire sans `users.read`, si bien que l'écran n'inscrit que des propositions ;
une proposition ne nomme ni son nœud ni ses rôles, et `listContributorSuggestions` dit s'appuyer sur
le planning là où WF-PRJ-0070 nomme les lignes de devis.

EP-14/L45a (#618), la première partie de l'univers témoin à l'échelle (#528), fait sommer toute la
structure de mille tâches par les lectures qui ne sommaient que le cœur — indicateurs du projet, du
devis et du reste à engager, courbes, plan de charge, coûts réels, histoire des révisions et leur
comparaison, ligne du témoin au portefeuille —, depuis la seule description du témoin, par les
générateurs du faux back (`docs/api/DECISIONS.md`, « Les lectures sur toute la structure »). Le
front ne change pas : ce sont ses tests qui lisent les nouvelles valeurs. Les tests qui assertaient
une valeur du cœur assertent celle de la structure, dans la forme en place — lue dans l'exemple
quand le test le lisait déjà, écrite comme la langue la montre quand le parcours de bout en bout le
faisait, les repères des parcours étant tenus par le générateur (`test_the_marks_*`). Ce qui n'était
pas une simple valeur a changé de forme sans toucher aux exemples : les deux sous-projets du témoin
portant désormais des coûts réels, la suppression s'éprouve sur une variante de l'exemple, « SP-ESS »
déchargé (`subproject-commands.dom.test.tsx`), et le parcours des paramètres éprouve la suppression
présentée indisponible, sa raison dite, pour l'un et l'autre (`projects.spec.ts`) — une perte de
couverture assumée : la suppression réussie d'un sous-projet n'est plus éprouvée de bout en bout
contre le faux back, dont aucun sous-projet ne se supprime, et seul le test dom la porte, sur la
variante ; la table des modifications de la comparaison, 2 770 lignes, s'affirme par ses quatre
premières lignes et son compte, lu dans l'exemple, et les écarts de montants se dérivent de l'exemple
(`revisions/page.test.tsx`) ; le contrôle d'axe du tableau des décaissements devient un test à lui,
sur une fenêtre de lignes de chaque table (`charts.dom.test.tsx`, défaut n° 23 de
`docs/dev/typescript.md`). Reste à L45b (#528) ce que la décision laisse : le registre des risques,
sa matrice et sa couverture sur le budget du seul cœur, et les deux Kanban sur les seules tâches du
cœur.

---

EP-14/L42h (#611) écrit au contrat ce que l'écran des sauvegardes et les formulaires des réglages
attendaient : chaque sauvegarde liste ses commandes, avec trois conditions nommées
(`backup_verified`, `no_backup_running`, `no_restore_running`) ; `listBackups` se filtre et se
trie ; `startBackup`, `retainBackup`, `downloadBackup` et `startRestore` refusent par condition
manquante, jamais par un code d'état ; une date confirmée qui n'est pas celle de la sauvegarde
est refusée au champ ; le téléchargement nomme son fichier ; `updateReferenceSettings` s'écrit
par sous-objet, chaque champ sous la permission de sa fonction, et `default_language` sort du
schéma d'écriture jusqu'à ce qu'EP-03 décide où la langue de l'installation s'écrit. Le lot ne
touche au front que pour compiler sur le client régénéré ; l'adoption par la grille est L43f.

EP-14/L43f (#627), lot technique ajouté au cadrage après L42h, fait adopter par la grille des
sauvegardes de L43c ce que L42h a écrit au contrat ; les formulaires restent à L43d et L43e. Les
commandes : les colonnes des commandes suivent ce que les sauvegardes de la page listent
(`Backup.available_commands`, `backup-columns.tsx`), et non plus les permissions de la session —
« Sauvegarder maintenant » seul reste gardé par `backups.write`, le contrat n'ayant pas de commande
de liste —, une commande indisponible est présentée `aria-disabled`, décrite par sa condition
(`enums.CommandCondition`), et dite dans la tête de la liste quand on la presse, par
l'`UnavailableCellCommand` que partagent les sauvegardes et les activations du référentiel ; un 409
nommé se dit comme tout refus, le refus d'un téléchargement portant sa condition dans l'adresse de
retour (`409:STATE_FORBIDS_OPERATION:backup_verified`), et le dialogue de la restauration dit
`BACKUP_DATE_MISMATCH` à la date qu'il énonce, agissant sur la sauvegarde telle que la page relue la
montre. La route du téléchargement n'invente plus de nom : un fichier que l'API ne nomme pas est une
mauvaise passerelle, et le parcours de bout en bout attend le nom que le contrat donne au fichier ;
elle relaie la longueur quand l'API la donne, et rien sinon, le faux back ne la servant pas. Le tri
et les filtres : la grille trie chaque colonne par le serveur, les plus récentes d'abord sans tri,
jamais levé comme celui du journal, et filtre par période — les jours du lecteur en instants, fin
exclue, comme l'accueil —, par déclenchement, par vérification, par conservation et par bornes de
taille en octets, une sorte de borne `bytes` ajoutée aux filtres partagés ; une borne refusée (422,
`/query/to`, `/query/size_bytes_max`) est dite à son champ, la liste non lue et les filtres gardés ;
une lecture filtrée compte ce que le serveur retient et ne se dit jamais vide, et les écritures
partent de la ligne lue. La mention « le contrat ne trie, ne cherche ni ne filtre » disparaît du
guide et des tests.

EP-14/L43e (#616), lot technique, donne aux paramètres des risques et des indicateurs leurs
formulaires, sur la décision de l'auteur du 2026-10-08 qui fait montrer à la maquette ses commandes
d'écriture (#512). À une session qui porte `risk_settings.write`, l'écran des risques offre de
modifier la matrice entière — ses six bornes, saisies en pourcentages, et ses seize zones, un choix
par case, rangées comme la table les montre (WF-REF-0160) — ; à une session qui porte
`indicator_settings.write`, l'écran des indicateurs offre de modifier les quatre seuils et le délai
entre deux revues, en semaines entières (WF-REF-0170, WF-REF-0180). Chaque formulaire envoie par
`updateReferenceSettings` le seul sous-objet de son écran avec la version lue ; ni la devise
(WF-REF-0140) ni la langue de l'installation ne s'y saisissent. Avant toute demande, le formulaire
refuse au champ que le serveur désignerait une borne qui n'est pas strictement au-dessus de la
précédente et un seuil d'alerte qui n'est pas sous son seuil de vigilance ; le serveur dit le reste,
par champ au champ, la permission manquante et la version périmée — que les deux écrans partagent —
sous le formulaire. La réponse prend la place des paramètres lus tant qu'elle est plus récente, la
page relue ; l'écran dit que le faux back ne garde rien (`MockupNotice`). Le formulaire du
référentiel y gagne trois pièces que d'autres écrans pourront prendre : des champs rangés sous une
légende commune, qui commence leur nom (`group`) ; des règles qui lient des champs entre eux
(`rules`) ; un champ de nombre entier, jugé avec les autres (`control: "whole"`), le délai refusé
s'il n'est pas un nombre entier de semaines. Chaque écran n'est offert qu'à sa permission : une
session qui ne porte que l'une des deux voit l'autre écran en lecture, ce que les tests de page
éprouvent en retirant l'autre permission de la session d'exemple. Écartés : un
formulaire dans la page plutôt qu'un dialogue — les paramètres du projet, seul autre objet unique que
la maquette modifie, ouvrent le leur depuis une commande, et le dialogue porte déjà les refus par
champ ; un contrôle de la plage des seuils et du délai au front, que la conception ne demande pas et
que le serveur juge — le client engendré ne porte ni l'intervalle ]0, 1[ des seuils ni les 1 à 104
semaines du délai, et le front ne les recopie pas. Le contrat ne décrit pas ce refus hors plage, sans
code ni exemple : un constat de contrat le suit (#659), et le faux back y répondrait par le premier exemple
de son 422, les bornes non ordonnées. Le faux back répondant à toute écriture par le premier exemple de l'opération —
les seuils écrits, la matrice inchangée —, le parcours de bout en bout de la matrice voit le succès
dit et la matrice d'avant ; la matrice répondue n'est éprouvée que par le test du formulaire.

EP-14/L42i (#612) écrit au contrat ce que les écrans de L44a et L44b attendaient (#590, #592) : le
déclencheur du prochain état est énuméré (`LifecycleTrigger`) et `getProjectNextState` répond 200,
sans prochain état, d'un projet en cours ou clos ; le projet dit d'avance que sa probabilité de gain
est figée (`update_win_probability`, `project_before_in_progress`) et la refuse par cette condition
(409 `STATE_FORBIDS_OPERATION`, comme le `kind` figé d'une nature ; `WIN_PROBABILITY_FROZEN` retiré) ;
ses deux taux sont bornés de 0 à 1 (422 `VALUE_OUT_OF_RANGE`, la borne franchie) ; le code pris d'un
projet ou d'un sous-projet nomme son porteur par son libellé (`conflicting_object_label`) ; chaque
sous-projet liste ses commandes (`update`, `delete`), la suppression indisponible par
`subproject_without_actual_costs` seule — un sous-projet qu'une révision marquée cite se supprimait
alors, marqué supprimé (WF-DAT-0080), comme une chronologie (L42k), ce que L42l renverse —, son 409
nommé par la condition, et
`update` du projet couvre ses sous-projets ; `setContributors` refuse à sa ligne un compte inconnu
(`UNKNOWN_USER`) ou désactivé (`USER_INACTIVE`) ; une proposition nomme son nœud et ses rôles, et
`listContributorSuggestions` s'appuie sur les lignes de devis ; `subproject_created` porte déjà la
facture importée sous son code (#625). Les choix et les options écartées sont dans
`docs/api/DECISIONS.md`. Le lot ne touche au front que pour compiler sur le client régénéré :
l'adoption par les écrans de L44a et L44b, que la conception plaçait dans le lot, revient à l'agent
TypeScript dans un lot propre, L44e (#636), pour tenir le plafond.

EP-14/L45b (#619), la dernière partie de l'univers témoin à l'échelle (#528), applique la décision 4
du cadrage de #287 : les risques 751 et 753 sont portés à l'échelle de la structure de mille
tâches — leurs chiffres du cœur multipliés par mille, une fois dans la description du témoin —, 752
garde ceux de son Vérif, et le registre des risques, sa matrice et leur couverture lisent la gravité
sur le budget de référence de toute la structure ; la réserve, les totaux, la couverture et la
provision de 751 dans toutes les lectures de la révision courante suivent, et les deux Kanban
présentent toutes les tâches de la structure (`docs/api/DECISIONS.md`, « Les risques à l'échelle et
le Kanban de toute la structure »). L'exemple trié du devis du poste de commande se trie par montant
décroissant, le tri croissant ne déplaçant plus aucune ligne : il renverse les lignes du câblage et
éprouve encore le Vérif de WF-IHM-0060-A. Le front ne change pas : ses tests lisent les nouvelles
valeurs, et ceux dont la forme tenait au cœur — le tri par montant, un Kanban de quinze tâches —
sont repris par le lot TypeScript : le Kanban s'affirme par colonne, les tâches du cœur en tête puis
la première tirée, et le nombre de ses cartes, celui de l'exemple ; le devis trié par montant, par
ses numéros de ligne et ses montants lus dans l'exemple ; le collage sous un tri, sur le devis trié
par heures, depuis la provision déplacée (refusé) et depuis « Borniers » (accepté). Le Kanban rend
ses 960 cartes sans fenêtre ni page, en quatre secondes environ en développement après le clic,
dans la borne des écrans de grille où il était déjà (`WORKING`). #528 et #287 sont soldés.

EP-14/L42l (#647) corrige L42i sur la décision de l'auteur du 2026-10-10 (#634) : un sous-projet
qu'une révision marquée cite **ne se supprime pas** (§4.4.1), les sous-projets déterminant la courbe
de la valeur acquise. La condition que le cadrage prévoyait et que L42i avait retirée en suivant le
Vérif de WF-DAT-0080 revient, `subproject_not_cited`, listée avant `subproject_without_actual_costs`
quand les deux manquent et nommée par le 409 de `deleteSubproject` ; aucun sous-projet n'est plus
marqué supprimé. Le Vérif de WF-DAT-0080 dit encore le contraire : sa correction attend l'auteur
(`docs/spec/TODO.md`, § 2). Depuis L45a, la référence porte toute la structure : elle cite les deux
sous-projets du témoin, et non le seul Poste de commande ; seul le sous-projet créé ne l'est pas. La
phrase de la note de L42i qui disait qu'un tel sous-projet se supprime est mise au passé. Le front ne
change pas : l'écran des sous-projets, et sa variante « SP-ESS » déchargée, que la citation garde
désormais indisponible, reviennent à L44e.

EP-14/L44e (#636), lot technique, fait lire aux écrans du projet ce que L42i a écrit au contrat. Le
cycle de vie nomme le déclencheur par `enums.LifecycleTrigger` : la liste locale et « déclencheur non
reconnu » quittent l'écran et les catalogues, et un projet en cours ou clos, que le serveur répond sans
prochain état ni déclencheur, le dit comme avant. Les paramètres du projet : la probabilité de gain suit
`update_win_probability` — indisponible, le champ est montré figé, ses conditions dites sous lui, et la
valeur n'est pas envoyée ; figée entre-temps, le 409 `STATE_FORBIDS_OPERATION` est dit sous le
formulaire, comme le `kind` figé d'une nature —, et un taux hors de ses bornes est dit au champ, la
borne que le serveur donne en rapport dite en pourcentage, comme le champ la saisit (`ratioPercent`) ;
le front ne vérifie pas les bornes avant l'envoi, le serveur seul les juge. `problem.ts` lit `maximum`
comme `minimum`, un décimal du contrat seulement, une date bornant une période restant au filtre de
la période. Le code déjà porté, d'un projet comme d'un sous-projet, nomme son porteur par
`conflicting_object_label` dans le formulaire partagé (`ReferenceForm`), après les noms de la liste et
avant le repli générique. Chaque sous-projet offre la modification et la suppression qu'il liste,
indisponibles avec leurs conditions comme les commandes des sauvegardes (`UnavailableCellCommand`) —
la suppression d'un sous-projet qu'une révision marquée cite (`subproject_not_cited`, L42l) ou auquel
des coûts réels sont imputés (`subproject_without_actual_costs`), et, sur un projet clos, chaque
commande (`project_not_terminal`) —, la suppression n'étant plus déduite de `has_actual_costs` ; les
colonnes des commandes paraissent dès que le projet liste `update`, disponible ou non, comme « Nouveau
sous-projet » (WF-IHM-0090). Une réponse à la modification du projet ne ferme que l'ouverture du
formulaire d'où elle est partie (#660, ajouté au lot). Les propositions de
contributeurs disent leur nœud et leurs rôles, l'inscrit prend `is_active` du contrat, et
`UNKNOWN_USER` et `USER_INACTIVE` sont dits à la ligne du compte, par la lecture des refus par champ
de L44b. Les tests reprennent les exemples de refus du contrat (`project_code_taken`,
`project_win_probability_frozen`, `project_rates_out_of_range`, `subproject_code_taken`,
`subproject_delete_cited`, `contributors_accounts_refused`, `contributors_without_manager_refused`) ;
la suppression éprouvée part du sous-projet créé, non cité, déchargé (`subproject_created`), et des
variantes contrefactuelles de `subprojects`, déclarées dans le test, éprouvent une ligne sans commande
et les commandes indisponibles d'un projet clos.

EP-14/L43d (#615), lot technique, donne à l'écran des sauvegardes le formulaire de leur planification
et de leur copie externe, et ferme #519 : à une session qui porte `backups.write`, « Modifier la
planification » ouvre le formulaire du référentiel (`ReferenceForm`), qui envoie la planification
entière depuis la version où il s'est ouvert (`setBackupSchedule`) — activée ou suspendue, fréquence,
jour, heure, rétention, et la copie : un emplacement parmi ceux que l'installation déclare
(`listExternalBackupLocations`, lu pour cette seule session), un dossier relatif, un nombre de copies
au moins égal à la rétention, vérifié avant l'envoi. « Tester l'emplacement » dit l'issue de
`testExternalBackupLocation`. Le succès remplace la planification affichée tant qu'il est plus récent
que la lecture ; les trois refus de copie du contrat se disent au champ, la version périmée avec
l'offre de relire ; l'avis de la maquette était déjà dit à cette session. L'heure se saisit en UTC et
l'heure du poste qu'elle donne se dit à côté — le jour local aussi pour une planification
hebdomadaire —, sans conversion à l'envoi. Les bornes d'un nombre de sauvegardes ou de copies (1 à 365)
ne sont pas vérifiées au front, comme pour les paramètres de L43e : le refus de `retained_count` hors
bornes n'est pas décrit au contrat, et part à EP-14/L42m ; seule la règle « copies au moins égales à la
rétention », que la conception demande et que le contrat décrit avec son minimum, l'est, avec le jour
d'une planification hebdomadaire, la fréquence et l'heure d'une planification activée. Choix :
le formulaire du référentiel plutôt qu'un formulaire propre à l'écran, au prix de trois ajouts qu'il
partage — un champ `time`, une note tirée du brouillon, ce qui suit les champs (`after`) — et des règles
entre champs et des nombres entiers que L43e lui ajoute aussi, repris ici sous les mêmes noms (`rules`,
`whole`) pour que les deux lots se rejoignent ; le refus d'un dossier par le test se dit sous le bouton
du test, non au champ, le test n'écrivant rien de la planification ; un jour hebdomadaire laissé vide
est refusé avant l'envoi, un jour quotidien part nul. Une planification déjà réglée vers un emplacement
que l'installation ne déclare plus le garde offert, par son nom, refusé au champ avant l'envoi, plutôt
que de retirer la copie en silence. Une réponse tardive ne ferme que le dialogue d'où elle est partie
(revue 1, #660). L'état suspendu se dit « Suspendue » et non plus « Désactivée », comme le contrat le nomme.

EP-14/L42m (#663), lot de contrat ajouté le 2026-10-10, ferme deux constats de #507. Pour #628, la
date qu'énonce la confirmation d'une restauration depuis une sauvegarde déposée est l'instant que
porte son archive, lu au dépôt et rendu par lui (`FileUpload.backup_taken_at`, nul pour le fichier
d'un import), auquel `startRestore` compare la date confirmée, refusée comme pour une sauvegarde de
la liste (`BACKUP_DATE_MISMATCH`) ; une archive sans instant lisible est refusée au dépôt
(`FILE_FORMAT_UNREADABLE`, sans paramètre) — écartée, la date attendue rendue par le seul refus de
`startRestore`, que la confirmation n'aurait connue qu'après coup. Pour #659,
`updateReferenceSettings` refuse un délai hors de 1 à 104 semaines par `VALUE_OUT_OF_RANGE`, la
borne franchie, et un seuil hors de ]0, 1[ par un motif propre aux seuils,
`THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE`, sans paramètre — une décision de l'agent de livraison à la
relecture : restreindre le seuil à deux décimales pour nommer des bornes admises aurait restreint
WF-REF-0170 ; et la réponse de la matrice met en alerte la case de la plus faible probabilité et de
la plus forte gravité, celle que le test du formulaire de L43e change. Le jumeau du refus hors plage
pour les sauvegardes, relevé par la relecture de L43d, suit : `setBackupSchedule` refuse de même une
rétention hors de 1 à 365, sur la plateforme ou sur l'emplacement externe. Les choix et les options
écartées sont dans `docs/api/DECISIONS.md`. Le front reçoit la phrase du nouveau motif et compile sur
le client régénéré ; les tests que #659 annonce — un délai de zéro refusé au champ, la zone répondue
vérifiée — et la restauration depuis un fichier, avec la date du dépôt (L43d), viennent ensuite.

EP-14/L42j (#613), sa part de contrat, écrit ce que l'écran des paramètres de ressources de L43b
attendait (#575, points 1 à 7). Les choix et les options écartées sont dans
`docs/api/DECISIONS.md`.

Les commandes et le type d'une catégorie :
- un calendrier liste sa désignation par défaut (`CalendarCommand.set_default`), indisponible pour
  un calendrier désactivé, faute de la condition `calendar_active` ;
- `setDefaultCalendar` porte la version lue, refuse une version périmée (412) et un calendrier
  désactivé (409, la même condition) ;
- une catégorie dit le type de sa nature (`cost_type_kind`).

Chaque écriture de l'organisation, des rôles et des calendriers décrit ses refus par champ :
- une référence inconnue, par `UNKNOWN_ORG_NODE`, `UNKNOWN_CALENDAR` ou `UNKNOWN_COST_CATEGORY` ;
- un nœud déplacé sous lui-même ou ses descendants, par `ORG_NODE_CYCLE`, ou sous un nœud désactivé,
  même désactivé lui-même — WF-REF-0070, révisé le 2026-10-09 ;
- la catégorie hors main-d'œuvre d'un rôle (`LABOUR_CATEGORY_REQUIRED`), ou son rattachement
  désactivé, refusé à la modification quand elle le change (WF-REF-0090) ;
- les heures d'un jour hors de 0 à 24 et une capacité négative, par `VALUE_OUT_OF_RANGE` et la borne
  franchie ;
- le code pris d'un nœud, son porteur nommé par son libellé, et le libellé pris d'un calendrier
  (WF-REF-0110, révisé de même) ;
- la version périmée.

Le client est régénéré. Le front ne change que pour compiler : la désignation envoie la version
lue, les catalogues reçoivent les codes, la condition et les commandes nouvelles. L'adoption par les
écrans de L43b, que la conception plaçait dans le lot, revient à un lot propre, L43g (#685), pour
tenir le plafond. Trois règles de la
même révision sortent du périmètre de #575 et attendent une décision (#684) : le code unique d'un
rôle, sa catégorie gardée dans la main-d'œuvre, le projet que nomme le refus d'un calendrier.

## US-0200 — Accessibilité minimale

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`
- **opérations** : aucune en propre
- **issue** : #84

**En tant que** chef de projet, manager ou administrateur, **je veux** atteindre toute action
au clavier, lire les textes sans effort et agrandir l'affichage sans rien perdre, **afin
d'**utiliser Waterfall toute la journée sans que l'outil me coûte plus que le travail.

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste
  visible. »
- `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau
  AA. »
- `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. »
- propre à l'US : chaque champ de saisie porte un libellé associé, et chaque image porteuse
  d'information une description — le quatrième point du corps de WF-IHM-0100, que son Vérif
  ne reprend pas ; un contrôle automatisé d'accessibilité le vérifie dans la chaîne ;
- propre à l'US : le contrôle de contraste joue en mode clair et en mode sombre — la charte
  existe dans les deux (US-0090), et un mode qui n'est pas contrôlé dérive.

**Notes de réalisation.** Le contrôle de contraste est exécuté par la chaîne, sinon il n'est
fait qu'une fois. Aucune conformité complète à un référentiel n'est visée ni déclarée
(§2.2) : ces quatre points, et rien de plus. Le harnais réemploie `frontend/e2e/axe.ts` — les
règles WCAG A et AA, jouées aujourd'hui sur le seul en-tête des tables de `theme.spec.ts` — et la
boucle de `screens.spec.ts` sur les routes de `functions.json`, en clair et en sombre
(`colorScheme`), à 1366 et à 911 points, l'agrandissement de 150 % émulé par la fenêtre ; le
parcours clavier est générique par route ; les règles `label` et `image-alt` d'axe portent le
critère propre des libellés et des descriptions (« Conception », « L'accessibilité »). L'US tient
en un lot, dont l'issue est la sienne ; si les écarts relevés l'imposent, elle se découpe en deux.

**Hors périmètre.** L'aide en ligne, qui n'est pas dans cet EPIC.

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
ne joue que les parcours étiquetés (« Conception », « Les navigateurs »). À 360 points, les vues
sont en lecture seule : aucun champ, aucune cellule saisissable, aucune commande d'écriture ; les
filtres de lecture restent (décision de l'auteur du 2026-10-09). L'US tient en un lot, dont l'issue
est la sienne.

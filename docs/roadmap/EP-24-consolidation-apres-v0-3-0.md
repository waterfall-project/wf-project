---
id: EP-24
titre: Consolider après la v0.3.0 — les filtres des tables et la gestion des utilisateurs achevés, une file de fusion qui n'échoue plus sans régression, les constats d'EP-09 et d'EP-23 soldés, l'aller-retour MS Project tenu dans MS Project, la spécification 1.0.5
statut: en cours
depend_de: EP-09, EP-23
famille: front, back, plateforme
issue: 2932
---

# EP-24 — Consolidation après la v0.3.0

## Objet

La version 0.3.0 est posée (2026-11-12, `main` b9cc1f51), EP-07, EP-09 et EP-23 livrés. Elle laisse
en plan ce qu'aucun EPIC de domaine ne reprendra : le travail de la nuit du 11 au 12 novembre sur les
filtres des tables et la gestion des utilisateurs, resté inachevé ; une file de fusion qui échoue trop
souvent sans régression ; les constats ouverts sous EP-09 et sous EP-23 ; les constats de la recette
de l'export et de l'import MS Project dans MS Project 2013 et 2024 ; et quatre décisions de l'auteur
que la spécification ne porte pas encore. EP-24 les solde. C'est un EPIC de consolidation, sur le
modèle d'EP-23 : il n'introduit aucune fonction nouvelle, hors ce que des issues ont déjà validé —
#2914, #2915, #2916, #2917 et #2922.

Il vient à ce rang parce que la file bloque tout le reste : du 2026-11-05 au 2026-11-12, 88 de ses
370 passages ont échoué, dont 68 dans les parcours contre le service, et un échec qui n'est pas une
régression coûte un passage entier et une remise en file à la main. La stabilité passe donc avant la
vitesse, et les deux avant les constats.

## Ce qui en fait partie

Dans l'ordre de priorité que l'auteur a fixé le 2026-11-12 :

1. **Le travail de la nuit du 11 au 12 novembre** : les filtres des tables plates et des grilles
   arborescentes, dont la vérification finale de L5 et de L6 s'est arrêtée à 04 h 07 (#2916, PR
   #2929 à #2931) — US-1850 ; la gestion des utilisateurs, ses filtres, « Sans rôle » et ses actions
   groupées (#2917) — US-1860 ; l'écran ouvert sans session et l'accueil d'un compte qui ne peut
   ouvrir aucun projet, dont le code est dans `epic/EP-24` (#2914, #2915, PR #2927 et #2928) —
   US-1870.
2. **La chaîne, stabilisée puis raccourcie** : une mesure suivie du taux d'échec de la file hors
   régression et de la durée du palier complet, et l'inventaire des instabilités — US-1880 ; les
   parcours contre le service qui font échouer la file sans régression (#2911, et ceux que
   l'inventaire relève), et la règle d'un parcours lent — US-1890 ; les dépendances réseau de la
   chaîne (#2913) — US-1900 ; les tests instables du back et du front (#859, #1026) — US-1920 ; le
   chemin critique et les minutes-runner du palier complet — US-1910 ; le poste local (#2890, et le
   tmpfs `/tmp`) — US-1930.
3. **Les constats d'EP-09** : le classeur du reste à engager et la liste des classeurs abîmés
   (#2752, #2723) — US-1940 ; l'ajout d'une tâche et l'insertion d'une ligne au reste à engager,
   joués contre le service (#2909) — US-1950 ; la borne haute du paramètre commun `Offset` (#2778) —
   US-1960.
4. **La suite d'EP-23** : l'écran des rôles, la référence d'un refus hors de la forme du contrat et
   trois paragraphes trop larges (#2898, #2897, #2882, #2886) — US-1970 ; le caractère NUL dans les
   paramètres libres de requête et les décimaux sans borne (#2891, #2875) — US-1980.
5. **L'export et l'import MS Project** : les champs que MS Project lit pour une tâche manuelle, la
   durée dite non estimée, et le décalage négatif en semaines du corpus (#2923, #2812) — US-1990 ;
   l'import d'un planning bâti sur un autre calendrier, signalé, puis importé en gardant les durées
   ou les dates (#2922) — US-2000.
6. **La spécification** : la révision 1.0.5, qui écrit les décisions de #2914, #2915, #2921 et
   #2922, et la relecture de la 1.0.4 contre le code de `main` — US-2010.

## Ce qui n'en fait pas partie

- la capacité d'un rôle déduite de son effectif et de son calendrier (`WF-REF-0100-A`, spécification
  1.0.4, #2836) : `capacity` porte encore les heures saisies ; sa reprise — le contrat, la saisie, la
  migration des rôles — va à EP-10 (décision de l'auteur du 2026-11-12), comme le fichier d'EP-05 le
  prévoyait ; la borne de la capacité d'un rôle relevée par #2875 la suit ;
- l'annulation d'un collage de l'avancement, qui demande `planning.write` quand le collage demande
  `remaining.write` (#2905) : sans effet tant que le collage refuse les colonnes d'exécution ; elle
  attend le lot qui les fera coller (décision de l'auteur du 2026-11-12) ;
- les plannings réels de la recette du 2026-11-11 : confidentiels, ils ne sont ni versionnés, ni lus
  par un lot, ni nommés dans une issue, un test ou un commit ; tout test s'écrit sur le corpus
  versionné (`fixtures/msproject/`) ou sur un fichier construit pour lui ;
- un parcours « Keycloak injoignable, pas de boucle » ou « royaume qui refuse » contre le service
  (#2914) : le harnais n'arrête pas Keycloak le temps d'un parcours sans gêner les autres ; la
  couverture reste unitaire ;
- un contrôle outillé des inodes de `/tmp` : la règle est documentée, sans outil (décision de
  l'auteur du 2026-11-12) ;
- toute modification de la spécification par un agent : la révision 1.0.5 est écrite par l'auteur,
  en révisions suivies ; toute modification du contrat autre que les quatre que nomme « Opérations du
  contrat » ;
- les cases à cocher par ligne de la maquette de #2916 : la sélection garde les poignées numérotées
  de `DenseGrid` (décision de l'auteur du 2026-11-11).

## Exigences réalisées

Aucune : EP-24 corrige et achève le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Comme
EP-23, chaque US cite, avec tout leur Vérif, les exigences dont ses tests relèvent ; les phrases
qu'elle ne touche pas sont des écarts qui disent qui les constate. Leur portée reste celle des EPIC
qui les ouvrent et les closent : `WF-SEC-0020-A`, `WF-ADM-0010-A` et `WF-ADM-0180-A` (EP-03),
`WF-IHM-0120-A` (EP-04), `WF-QUA-0080-A` et `WF-PLA-0160-A` (EP-06), `WF-IHM-0060-A`,
`WF-INTF-0040-A`, `WF-INTF-0050-A` et `WF-INTF-0080-A` (close par EP-07), `WF-RAE-0040-A` (EP-09),
`WF-INTF-0120-A` et `WF-DEV-0030-A` (EP-08), `WF-OBS-0020-A` (EP-13). Les US de la chaîne et du
poste portent « aucune — outil du dépôt », comme celles d'EP-19 et d'EP-21.

Les phrases que la révision 1.0.5 ajoutera aux Vérif de `WF-SEC-0020-A`, `WF-IHM-0120-A`,
`WF-IHM-0060-A` et `WF-PLA-0160-A` n'existent pas encore dans la spécification : les US les portent
comme critères propres, dans les mots que les issues ont retenus, et US-2010 les relie mot pour mot
une fois la 1.0.5 dans `main`.

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Déjà servies, et reprises pour ce que les constats y corrigent : `getMe`, `updateMyPreferences`
(US-1850) ; `listUsers`, `updateUser`, `setUserActivation`, `setUserAccessRoles` (US-1860) ;
`listProjects`, `getMe` (US-1870) ; `requestExport`, `openImport` et `applyImport`, par les
classeurs qu'ils écrivent et lisent (US-1940) ; toute liste paginée
(US-1960) ; `updateAccessRole`, `deleteAccessRole` (US-1970) ; toute lecture qui porte un paramètre
de requête libre, `setDurationUnits`, les écritures d'un nœud du planning et d'une ligne de devis
(US-1980) ; `requestExport`, `openImport`, `getImport`, `applyImport` et `abandonImport`, pour
le format MS Project (US-1990, US-2000).

Quatre modifications du contrat, chacune par une issue `contract` tranchée par l'auteur et une
entrée de `docs/api/DECISIONS.md` (« La règle d'après le gel »), faite avant le code qui la
consomme :

- `filters_open` dans les préférences d'une grille (`display_preferences.grids.<grille>`) : déjà
  écrite par #2916/L1, dans #2929 ;
- un paramètre de requête de `listUsers` qui retient les comptes sans rôle, en union avec
  `access_role_ids` (#2917 ; décision de l'auteur du 2026-11-12) — US-1860 ;
- `maximum: 2147483647` au paramètre commun `Offset`, comme `LockVersion` (#2778 ; décision de
  l'auteur du 2026-11-12) — US-1960 ;
- l'écart de calendrier dans le compte rendu d'un import MS Project, et l'option « garder les
  durées » ou « garder les dates » de son analyse (#2922) — US-2000.

## Préalables

- EP-09 et EP-23 livrés, `v0.3.0` posé (fait, 2026-11-12).
- **La branche de livraison est `epic/EP-24`**, tirée d'`epic/cadrage` (630d9c0a) le 2026-11-12, au
  cadrage, par le cadreur à la demande de l'auteur — une exception à la règle qui réserve cette
  poussée au livreur du premier lot. `epic/cadrage`, tirée de `main` au tag `v0.3.0`, avait reçu le
  thème de la page de connexion (#2926) et #2915 (#2928) ; les pull requests encore ouvertes vers
  elle — #2927 (#2914) et #2929 à #2931 (#2916, L1 à L6) — sont redirigées vers `epic/EP-24`, et
  `epic/cadrage` ne reçoit plus rien. L'auteur paramètre la file de fusion d'`epic/EP-24`.
- La révision 1.0.5 de la spécification, écrite par l'auteur, précède le lot qui réalise #2922 et
  celui qui relie ses phrases aux US.
- Le fichier 02 du corpus, repris par l'auteur dans MS Project avec une liaison à décalage négatif
  en semaines, précède le lot qui déclare `lag_negative_w` (#2812).

## Définition de fini

- sur les 100 derniers passages de la file d'`epic/EP-24` (`chain`, `merge_group`), au plus 2
  échecs qui ne soient pas une régression, classés par l'outil de mesure et relus ; la durée de mur
  du palier complet y est de 12 minutes au plus en médiane (16 minutes les 10 et 11 novembre) ;
- chaque instabilité de l'inventaire est corrigée, ou suivie par une issue qui porte sa décision ;
- un lot qui touche la chaîne a prouvé son effet par des passages réels, avant et après, et non par
  une mesure sur le poste ;
- les parcours contre le service qui échouaient à la vérification interrompue du 2026-11-12 passent
  sur `epic/EP-24`, L4, L5 et L6 fusionnés ;
- sur *Administration › Gestion des utilisateurs*, filtrer « Créé par le fournisseur d'identité » et
  « Sans rôle », tout sélectionner, puis « Ajouter un rôle » donne un rôle à chaque compte retenu, et
  dit ceux qui ont été refusés ;
- un classeur du reste à engager dont un rôle et une catégorie partagent un code est exporté puis
  réimporté sans qu'aucune ligne change de nature ;
- `GET` d'une liste paginée avec `offset=2147483648` répond 422 ; `make build-openapi`,
  `make inventory`, `make client-up-to-date` et `make server-models-up-to-date` passent, et
  `docs/api/DECISIONS.md` a ses entrées ;
- l'export d'un jalon manuel porte `ManualStart`, `ManualFinish` et `ManualDuration` aux valeurs de
  `Start`, `Finish` et `Duration`, chaque tâche porte `Estimated` à 0, et le fichier reste valide
  contre le schéma ; le test du corpus n'a plus de cas non exécuté pour `lag_negative_w` ;
- un planning synthétique saisi en jours à 7 heures par jour est importé, l'écart de calendrier dit
  au compte rendu, en gardant les durées puis en gardant les dates ;
- la spécification est en révision 1.0.5, et `make roadmap` passe sur ses phrases nouvelles ;
- `make check` passe sur `epic/EP-24`, la file est verte ; `make roadmap` et `make requirements`
  passent ;
- chaque issue de « Constats reçus » est fermée par la fusion de son lot, ou reportée par sa
  décision.

## Constats reçus

Tranchés par l'auteur le 2026-11-12, au cadrage ; renommés `[EP-24]`, passés au label `EP-24` et
rattachés à leur US ou à leur lot à l'ouverture des issues, le même jour. Deux issues `contract`
en sont nées : #2976 (`listUsers`, « sans rôle », US-1860) et #2977 (l'écart de calendrier d'un import
MS Project, US-2000).

Le travail de la nuit du 11 au 12 novembre :

- #2916 — front : les filtres des tables plates repliables, en pastilles, et une barre d'actions sur
  la sélection (L1 à L6, PR #2929 à #2931) → US-1850 ;
- #2917 — front : la gestion des utilisateurs, ses filtres, « Sans rôle » et ses actions groupées
  → US-1860 ;
- #2914 — spec : un écran ouvert sans session devrait mener à la page de connexion (PR #2927)
  → US-1870, et US-2010 pour la spécification ;
- #2915 — spec : l'accueil d'un compte qui ne peut ouvrir aucun projet dit « Introuvable » (PR
  #2928) → US-1870, et US-2010 ;
- #2921 — spec : l'ouverture du panneau des filtres, préférence d'une table plate → US-2010, et
  US-1850 pour ses tests.

La chaîne :

- #2911 — front : des parcours contre le service échouent sous 6 workers sur PRJ-001 → US-1890 ;
- #2913 — outil : la file échoue avant les tests, `archive.ubuntu.com` introuvable dans les
  conteneurs de l'e2e → US-1900 ;
- #2890 — outil : `make e2e-service` aux 16 workers par défaut sature le poste → US-1930 ;
- #859 — front : `cost-commands.dom.test.tsx` instable sous charge → US-1920 (reportée à EP-13 le
  2026-10-11, reprise ici) ;
- #1026 — test : `test_an_account_whose_address_another_holds_whatever_its_case_is_not_created`
  instable → US-1920 (de même).

Laissés par EP-09 :

- #2752 — back : le classeur du reste à engager indexe les libellés des rôles et des catégories dans
  un seul dictionnaire → US-1940 ;
- #2723 — back : la liste des exceptions d'un classeur abîmé recopiée du lecteur de devis → US-1940
  (un seul propriétaire, dans `core/exchanges`) ;
- #2909 — front : l'ajout d'une tâche et l'insertion d'une ligne au reste à engager ne se jouent pas
  contre le service → US-1950 ;
- #2778 — contrat : le paramètre `Offset` sans borne haute → US-1960 ;
- #2905 — back : annuler un collage de l'avancement demande `planning.write` → hors d'EP-24.

Laissés par EP-23 :

- #2898 — front : une suppression de rôle rejetée laisse le rôle occupé → US-1970 ;
- #2897 — front : un renommage validé pendant l'écriture de son rôle dit « serveur injoignable »
  → US-1970 (le renommage attend que le rôle soit libre) ;
- #2882 — front : `UnexpectedAnswer` garde un `correlation_id` hors de la forme du contrat dans son
  digest → US-1970 ;
- #2886 — front : trois paragraphes de commentaire et du guide dépassent la largeur de leurs voisins
  → US-1970 ;
- #2891 — back : un caractère NUL dans les autres paramètres libres de requête → US-1980 (recenser,
  éprouver, corriger) ;
- #2875 — back : hors des seuils et de la matrice, des décimaux sans borne débordent PostgreSQL
  → US-1980 (la règle d'US-1840, champ par champ ; la capacité d'un rôle à EP-10).

La recette MS Project du 2026-11-11, laissés par EP-06 :

- #2923 — back : l'export MS Project n'écrit pas `ManualStart`, `ManualFinish`, `ManualDuration` ni
  `Estimated` → US-1990 ;
- #2812 — corpus : aucun planning ne porte un décalage négatif en semaines → US-1990 (le fichier est
  fourni par l'auteur) ;
- #2922 — spec : l'import MS Project d'un planning sur un autre calendrier → US-2000, et US-2010
  pour la spécification ;
- #2546 — spec : le Vérif de `WF-PLA-0040-A` ne nomme pas le refus `NODE_CYCLE` : la 1.0.4 a ajouté
  la phrase ; US-2010 le constate et la ferme.

Reporté par ce cadrage : la capacité d'un rôle (`WF-REF-0100-A`, #2836, fermée) → EP-10, par
#2978, ouverte sous #2427.

## Conception

Écrite le 2026-11-12 sur `main` (b9cc1f51) et sur les branches du travail de la nuit, tirées vers
`epic/cadrage` (#2926 à #2931), après la validation des US par l'auteur le même jour ;
validée par lui le même jour. Courte pour les constats,
comme celles d'EP-18 et d'EP-23 : chaque issue porte sa proposition, ses fichiers et ses tests, et
fait foi pour le détail. Elle est longue pour la chaîne, que nulle issue ne décrit en entier : ses
mesures sont celles de la file elle-même (`gh run list`, l'API des jobs et leurs journaux), relevées
le 2026-11-12, jamais celles du poste.

### La chaîne : ce qui est mesuré

**La file du 2026-11-05 au 2026-11-12** (`chain`, `merge_group`) : 370 passages, 272 réussis, 88 en
échec, 6 annulés, 4 en cours au relevé. Par jour, passages et échecs : le 5, 39 et 5 ; le 6, 49 et
8 ; le 7, 50 et 1 ; le 8, 53 et 6 ; le 9, 56 et 29 ; le 10, 63 et 21 ; le 11, 54 et 17. La file
tenait jusqu'au 8 (20 échecs sur 191) et ne tient plus depuis le 9 (67 sur 173), quand les parcours
d'EP-07 puis d'EP-09 contre le service y sont entrés.

**Par job en échec** (un passage peut en compter plusieurs) :

| Job, étape | Passages | Classement |
|---|---|---|
| `service / paths`, `make check-service` | 68 | instabilités pour l'essentiel, familles ci-dessous ; 4 sans parcours en échec relevé au journal |
| `e2e / paths`, `e2e / measure` (« Install make ») et `service / paths` (`make e2e-browsers`) | 6 | infrastructure : `archive.ubuntu.com`, le 2026-11-11 (#2913) |
| `e2e / paths` et `e2e / measure`, contre le faux back | 6 | à classer : deux passages d'EP-20 le 5, quatre du 8 et du 9 |
| `keycloak / check` | 5 | à classer |
| `back / check` (`make check-back-static`, `make check-back`) | 6 | régressions présumées : l'analyse statique ne dépend pas de la charge |
| `back / tests` | 3 passages | un `LockNotAvailable` au chargement du témoin (42799623736) ; des 500 en série sur une pull request (42449690648), régression présumée |
| `front / tests (lint)` | 2 | instabilité connue de l'audit du 5, corrigée depuis (les gardes sans couverture) |
| `e2e`, « Install the Python of tools/.python-version » | 1 | infrastructure |
| `spec / check`, « Install pandoc » | 1 | infrastructure : un 503 de GitHub Releases |
| `contract / check`, `production / trial` | 1 chacun | à classer |

**Les parcours contre le service**, par famille de cause — l'hypothèse est celle du message d'échec
lu au journal, que le lot d'US-1890 établit par une mesure :

| Famille | Parcours (passages) | Ce que dit l'échec | Hypothèse |
|---|---|---|---|
| A. Le projet de la course n'est pas créé en 15 s | `structure.spec.ts:414` à `:452` (6), `planning-service.spec.ts:16` à `:154` (6), `project-start.spec.ts:179` et `:181` (3), `task-tree.spec.ts:13`, `timelines.spec.ts:353` et `:391`, `undo.spec.ts:139` (2), `revision-cycle.spec.ts` (2) | `own-project.ts:39` : l'adresse reste `/` au-delà de `WORKING` (15 s) après « Créer » | l'accueil et la création d'un projet, lents quand plusieurs workers créent à la fois ; chaque parcours qui écrit passe par là |
| B. Un état partagé entre parcours | `projects.spec.ts:113` à `:194` (9), `reference-resources.spec.ts:27`, `:110` et `:112` (8), `reference-settings.spec.ts:18`, `reference-costs.spec.ts:448` | les préférences relues portent le filtre d'un autre parcours (`states: created,pricing`) ; « the restorations that failed » : le calendrier par défaut n'est plus celui que le parcours a désigné | deux parcours `@shared` écrivent la même préférence d'un compte, ou le même réglage du référentiel, en même temps |
| C. Une lecture lourde de PRJ-001 | `revisions.spec.ts:238` à `:253` (8), `:121` (2), `:164`, `:35` (2) ; `structure.spec.ts:333` (3), `:361` ; `workload.spec.ts:110` | l'adresse garde `difference=` au-delà de 15 s ; 30 s dépassées sur trois lectures de la comparaison | 5 966 nœuds ; #2924 a ramené `getRemainingIndicators` de 2 845 à 58 requêtes et `compareRevisions` de 1 903 à 57 ; le reste est à mesurer après elle |
| D. La restauration | `service/backups.spec.ts:155` (11) et `:240` (5) | « Restaurer cette sauvegarde » absent après 60 s ; la grille « Sauvegardes » absente 10 s après la restauration | tous du 9 et du 10, sur trois pull requests d'EP-07 remises en file : une régression de leur branche, ou le dépôt d'une archive devenue plus lourde ; aucune issue ne les suit |

`timelines.spec.ts:263` n'a échoué dans aucun passage de la file. Ni #859 ni #1026 n'ont été
retrouvées dans les journaux lus.

**Les durées** (minutes de mur, passages réussis) : la médiane d'un passage vaut 11,4 le 8, 14,2 le
9, 15,7 le 10, 15,9 le 11 et 21,3 le 12 ; le 90e centile, 21 le 10 et le 11. Par job, sur trois
passages complets :

| Job | 2026-11-10 (42767057088) | 2026-11-11 (43083057552) | 2026-11-12 (43169119148) |
|---|---|---|---|
| `service / paths` | 13,8 | 17,5 | 24,1 |
| `back / tests (1/2)` et `(2/2)` | 8,2 et 9,6 | 15,3 et 10,0 | 15,8 et 18,7 |
| `tools / check` | 3,8 | 6,5 | 8,3 |
| `keycloak / check` | 3,7 | 4,6 | 4,8 |
| `e2e / paths`, de 1/5 à 5/5 | 2,9 à 4,1 | 2,9 à 4,4 | 3,3 à 4,3 |
| `front / tests` | 2,3 et 3,7 | 2,9 et 3,4 | 3,9 et 3,8 |

Le chemin critique est `service / paths`, à une minute de son délai de 25, puis `back / tests`, à une
minute du sien de 20 : les 3 min 40 par moitié du 2026-11-07 ne tiennent plus, EP-07 et EP-09 ayant
ajouté leurs tests. Un passage qui ne joue que le back et le service coûte 56 minutes-runner
(43164020689). Les morceaux de l'e2e, eux, sont devenus égaux à une minute et demie près.

**Le cache d'Actions** : 10,87 Go pour 268 entrées, au-dessus du quota de 10 Go. Deux causes lues
dans la liste : chaque passage de la file sur une branche neuve y écrit sa copie du magasin de pnpm
(188 Mo par référence `gh-readonly-queue/…`, qu'aucun autre passage ne relit) ; et les branches
livrées — `epic/EP-09`, `epic/EP-23` — gardent leurs couches d'images (environ 200 Mo chacune).

**Les dépendances réseau** : `archive.ubuntu.com` (le paquet `make` de l'image de Playwright,
`e2e.yml` ; les paquets système de `make e2e-browsers`, `service.yml`) ; Docker Hub pour onze images
— `postgres`, `redis`, `caddy`, `axllent/mailpit`, `dxflrs/garage`, `curlimages/curl`, `node`,
`python`, `debian`, `maven`, `adorsys/keycloak-config-cli` — et `keycloak/keycloak` ; le registre de
npm pour Prism et Redocly (`npx --yes`, `make mock-tools`) ; `mcr.microsoft.com` pour l'image de
Playwright ; GitHub Releases pour pandoc ; le miroir d'Astral pour Python.

### La chaîne : ce que les lots font

- **La mesure (US-1880)**. Un module des outils, `wftools.queue`, et sa cible `make queue-report
  BRANCH=<branche> [LAST=<n>] [SINCE=<date>]`, lisent par `gh` les passages `merge_group` de
  `chain` : leur nombre, les échecs par job et par étape, les parcours et les tests en échec avec
  fichier et ligne (lus au journal du job), la durée de mur en médiane et au 90e centile, et les
  minutes-runner. Le classement se fait contre un fichier versionné, `tools/queue-known.toml` : une
  entrée par instabilité connue — un motif de job, d'étape ou de test, sa famille, son issue. Ce que
  nulle entrée ne reconnaît sort « à classer » : l'outil ne décide jamais seul qu'un échec est une
  régression. L'inventaire ci-dessus y est versé, et la pull request d'un lot de la chaîne en cite la
  sortie avant et après. Rien ne tourne dans la chaîne : la commande se lance du poste.
- **La règle d'un parcours lent (US-1890)** s'écrit dans le guide, « Un parcours de bout en bout »
  (`docs/dev/README-fr.md` et sa traduction), en trois degrés : corriger la lecture d'abord, comme
  #2924 ; sinon isoler le parcours — un compte, un projet, un réglage à lui — ou le sérialiser
  (`shared-serial`) ; n'élargir une attente qu'en dernier recours, la mesure dans le commentaire.
- **Famille A** : la création du projet de la course est mesurée dans la chaîne (l'accueil,
  `createProject`, la navigation) ; si la lecture est en cause, elle se corrige au back ou au
  front ; sinon `createOwnProject` (`frontend/e2e/own-project.ts`) crée par l'API ce que le parcours
  n'éprouve pas, et le seul parcours de la création garde le geste de l'écran.
- **Famille B** : chaque parcours qui écrit une préférence joue sous un compte à lui ; ceux qui
  écrivent un réglage du référentiel commun — le calendrier par défaut, les unités de durée —
  passent dans `shared-serial`.
- **Famille C** : `compareRevisions` et les lectures du planning de PRJ-001 sont mesurées après
  #2924 ; `revisions.spec.ts:121` lit la comparaison une fois, ou ses trois lectures sont
  justifiées ; `test.slow()` ne reste que sur mesure.
- **Famille D** : reproduite sur `epic/EP-24` ; classée régression corrigée si elle ne reparaît
  pas sur cinquante passages, sinon corrigée comme les autres.
- **Le réseau (US-1900)** : le paquet `make` et les paquets système du navigateur sortent des
  miroirs d'Ubuntu — une image de travail de l'e2e publiée sur ghcr.io, bâtie de l'image de
  Playwright avec `make` et le Python des outils, que `e2e.yml` et `service.yml` emploient toutes
  deux (`service.yml` y joue ses parcours par le réseau de l'hôte) ; les images de Docker Hub sont
  tirées d'un miroir sous `ghcr.io/waterfall-project/mirror/`, tenu par `images.yml` aux mêmes
  empreintes ; Prism et Redocly deviennent des dépendances de développement épinglées du front, lues
  du magasin de pnpm, sans `npx --yes` ; pandoc est gardé en cache.
- **Les tests (US-1920)** : les propositions de #859 et de #1026 ; `installation.setup` attend
  l'état qu'il affirme ; le chargement du témoin prend ses verrous dans un ordre constant, ou attend
  celui qu'il n'obtient pas.
- **Le chemin critique (US-1910)**, pour 12 minutes en médiane : `service / paths` se coupe en
  quatre — trois morceaux des projets `service` et `shared`, et un quatrième pour `shared-serial`,
  `realm` et `restoration`, qui restent en série —, chacun sur sa plateforme ; `back / tests` passe
  de deux à quatre morceaux ; les morceaux de l'e2e sont pesés par durée mesurée, les durées gardées
  dans un fichier versionné que la mesure rafraîchit ; un passage de la file lit les caches sans en
  écrire (`front-cache.yml` et `images.yml` restent seuls à écrire, sur la branche), une branche
  neuve reçoit ses caches à sa création, et ceux d'une branche supprimée sont retirés ;
  `.next/cache` est gardé par `front-cache.yml`. Le prix est dit : quatre plateformes démarrées au
  lieu d'une, donc plus de minutes-runner pour moins de mur ; le lot le mesure, et l'auteur tranche
  si le compte de minutes dépasse ce qu'il accepte.
- **Le poste (US-1930)** : le défaut de `E2E_WORKERS` pour `make e2e-service` se calcule dans le
  Makefile, de `WATERFALL_PROCESSORS`, par le rapport que la mesure de 8, 10 et 12 workers retient ;
  `frontend/playwright.config.ts` ne change pas. La règle du worktree hors de `/tmp` va dans le
  guide (« Commandes ») et dans `docs/dev/agents.md` (« Le pilote »).

### Tables et migrations

Une seule : `import_report` gagne `duration_rule`, un texte nul hors d'un import MS Project en écart
de calendrier, contraint à `keep_durations` ou `keep_dates` (migration 0028, US-2000). Le compte
rendu reste le JSON de `report`. Rien d'autre : `filters_open` est une clé des préférences d'une
grille, le filtre « sans rôle » une requête, et les bornes d'US-1980 se tiennent sous les colonnes
existantes.

### Modules touchés, et ce que chacun expose

- *Filtres des tables (US-1850)* : ce que #2929 à #2931 posent — `GridToolbar`, le panneau,
  `FilterChips`, `row-selection.tsx`, `filters.ts`, `kept-filters.ts`. Le lot ne refait rien : il
  rejoue, relit, et solde les trois mineurs de L2.
- *Gestion des utilisateurs (US-1860)* : `api/users.py` lit le nouveau paramètre et `core/users`
  l'applique en union avec `access_role_ids` ; au front, `components/admin` (les listes des comptes,
  leurs filtres, la barre d'actions par `RowCommands`). Une action groupée enchaîne ses appels en
  série, compte par compte, par le chemin d'écriture d'un compte déjà en place, et rend la liste des
  refus avec leur raison.
- *Session et accueil (US-1870)* : déjà dans #2927 et #2928 ; le lot n'ajoute que les tests qui
  manqueraient aux phrases de la 1.0.5.
- *Classeurs (US-1940)* : `core/estimate/remaining/excel/writer.py` (`_context`) tient deux index
  de libellés, comme `_Labels` de `core/estimate/excel/writer.py` ; `core/exchanges` expose la liste
  des exceptions d'un classeur abîmé, que lisent le lecteur de devis et `core/costs/extraction.py`.
- *Parcours du reste à engager (US-1950)* : `frontend/e2e/remaining.spec.ts`, par
  `bringInProgress`.
- *Écran des rôles et refus (US-1970)* : `components/admin/role-commands.tsx`,
  `role-answers.tsx`, `admin-grids.tsx` ; `api/problem.ts` (`UnexpectedAnswer`, par
  `isCorrelation`).
- *Entrée du service (US-1980)* : les routes de `api/` pour les paramètres de requête ; pour les
  décimaux, `core/resource_settings/interface/duration_units.py`, `core/planning/entries.py` et
  `core/estimate/entries.py`, chacun refusant à son champ, par une fonction de précision partagée
  avec `core/indicator_settings/thresholds.py` (US-1840). Les mois, les trimestres et la durée d'une
  cellule collée passent de `\d` à `[0-9]`, comme les bornes d'US-1840.
- *MS Project (US-1990, US-2000)* : `core/planning/msproject/writer.py` (`_task`, l'en-tête) et
  `reader.py` (les champs `Manual*`) ; `core/planning/importing.py` et `msproject/translation.py`
  pour la règle de conversion ; `core/exchanges` pour `duration_rule` et la relance de l'analyse ;
  au front, l'écran du compte rendu d'un import.

### Modifications du contrat

Chacune par une issue `contract` et une entrée de `docs/api/DECISIONS.md`, avant le code, le client
et les modèles régénérés.

- **`Offset`** : `maximum: 2147483647` (`components/parameters.yaml`) ; #2778 devient l'issue.
- **`listUsers`** : un paramètre booléen `without_access_role` ; vrai, il retient les comptes sans
  rôle, en union avec `access_role_ids` quand les deux sont donnés ; la description
  d'`access_role_ids` (« An account without a role is retained by no value ») le dit.
- **L'import MS Project en écart de calendrier** : `ImportReport` gagne `calendar_gap`, toujours
  rendu, nul sans écart — les heures par jour et les plages horaires du calendrier du projet du
  fichier, les heures par jour du calendrier de l'installation, les tâches dont le calendrier propre
  diffère de leur calendrier Waterfall, et la règle sous laquelle le compte rendu a été calculé
  (`duration_rule`, `keep_durations` par défaut). Une opération nouvelle, `setImportDurationRule`
  (`PUT /projects/{project_id}/imports/{import_id}/duration-rule`), change la règle d'un import
  analysé et non appliqué, et relance son analyse ; elle refuse un import sans écart. `applyImport`
  ne change pas : il applique le compte rendu tel qu'analysé. `unit_constants` reste, sa description
  reprise.
- **`filters_open`** : déjà écrite par #2916/L1 (#2929).

### Ordre de construction

- **La branche d'abord** : #2927 et #2929 à #2931 se fusionnent dans `epic/EP-24`, puis le lot d'US-1850
  termine leur vérification. Il précède tout lot qui touche `frontend/e2e/`, les catalogues
  `frontend/messages/*.json` ou le guide : L5 et L6 réécrivent `structure.spec.ts`,
  `planning-service.spec.ts`, `planning.spec.ts`, `grid.spec.ts`, `projects.spec.ts`,
  `reference-costs.spec.ts`, deux parcours de `e2e/service/`, les deux catalogues, les deux guides
  et `DECISIONS.md`.
- **La mesure avant la chaîne** : US-1880 précède US-1890, US-1900, US-1910 et US-1920, qui se
  prouvent par elle.
- **La stabilité avant la vitesse** : le découpage de `service / paths` (US-1910) vient après
  US-1890, pour ne pas multiplier par quatre des parcours instables.
- **Le contrat avant son code** ; les trois issues `contract` écrivent toutes `DECISIONS.md` et
  régénèrent le client : leurs lots ne se livrent pas en même temps.
- **La spécification** : la 1.0.5 précède le lot de l'import d'US-2000 et le lot qui relie ses
  phrases ; l'export et le lecteur d'US-1990 ne l'attendent pas.
- **Les fichiers partagés** — `.github/workflows/`, `Makefile`, `frontend/playwright.config.ts`,
  les catalogues, les guides, `DECISIONS.md` — font les « pas avec » du plan de lots.

### La 1.0.4 relue contre `main`

| Exigence | Ce que la 1.0.4 change | Classement |
|---|---|---|
| `WF-CRE-0010` | le montant arrondi au centime, la moitié au plus loin de zéro | réalisée : `core/costs/extraction.py` ; `test_an_amount_is_rounded_half_a_cent_away_from_zero` (`test_actual_costs_analysis.py`) |
| `WF-CRE-0020` | une barre oblique suivie d'aucun code n'est pas de la forme | réalisée : `WBS_ELEMENT_INVALID` ; `test_a_wbs_element_without_the_expected_form_or_of_another_project_is_rejected` (#2721) |
| `WF-DAT-0080` | l'historique annulable et les plans de collage se suppriment selon leur règle (corps seul) | réalisée : `core/history/interface/purge.py`, `core/exchanges/interface/purge.py` ; `test_purge.py`, `test_history.py` |
| `WF-DEV-0030` | une part d'une année antérieure à l'année de référence n'est pas projetée | réalisée (`inflation_factor`) ; **écart corrigé ici** : son test ne cite pas l'exigence (US-2010) |
| `WF-INTF-0100` | une lignée en double rejette ses lignes | réalisée : `DUPLICATE_LINEAGE` ; `test_a_lineage_that_two_rows_carry_rejects_both_and_leaves_its_line_as_it_is` |
| `WF-INTF-0120` | la lignée en double, le fichier sans date de revue, la cellule de reste effacée | réalisée : `core/estimate/remaining/analysing.py` ; `test_a_task_the_file_completes_without_a_date_of_review_rejects_its_lines_set_to_nought`, `test_a_cell_left_empty_on_a_line_known_reads_nought` (`test_remaining_import.py`) |
| `WF-PLA-0040` | un déplacement sous soi-même est refusé | réalisée : `NODE_CYCLE` ; `test_a_selection_moved_under_itself_or_one_of_its_subordinates_closes_a_loop_refused` ; #2546 se ferme |
| `WF-PLA-0140` | la disposition en couloirs gardée d'une session à l'autre | réalisée (`DisplayPreferences.timelines`, EP-15) ; **écart corrigé ici** : le parcours qui enregistre les couloirs (`timelines.spec.ts:143`) cite `WF-IHM-0100-A` seul, et aucun test ne cite `WF-PLA-0140-A` pour cette phrase ; le fichier d'EP-06 la note à tort en écart (US-2010) |
| `WF-REF-0100`, glossaire | la capacité déduite de l'effectif et du calendrier | **écart d'EP-10** (décision de l'auteur du 2026-11-12) |
| `WF-REV-0080` | entre deux années de référence, chaque ligne de débours diffère aussi | réalisée par le calcul (`WF-DEV-0030`) ; **à confirmer par le lot** : `test_between_two_reference_years_only_the_re_estimated_amounts_differ_by_the_rates` (`test_comparison.py`) éprouve les taux, et la ligne de débours n'a pas de test repéré ; le lot l'ajoute s'il manque (US-2010) |

### Décisions

- **La branche de livraison est `epic/EP-24`, tirée d'`epic/cadrage`** (décision de l'auteur du
  2026-11-12, qui revient sur celle du matin de livrer dans `epic/cadrage`) : l'outillage —
  `make merge-queue-check EPIC=EP-nn`, la consigne d'`epic-deliverer`, `make check
  BASE=origin/epic/EP-nn` — vaut alors tel quel, sans exception à écrire dans chaque issue. Le
  cadreur l'a poussée, à la demande de l'auteur, contre `docs/dev/agents.md` (« Où un agent
  s'arrête ») ; aucun livreur n'a donc à la tirer au premier lot. Écartées : livrer dans
  `epic/cadrage`, que l'outillage ne sait pas nommer ; tirer `epic/EP-24` de `main`, qui aurait
  laissé #2926 et #2928 à reporter.
- **Les deux reprises** : la réalisation de #2922 reste dans EP-24 ; la capacité d'un rôle
  (`WF-REF-0100-A`) va à EP-10 (décisions de l'auteur du 2026-11-12). Écarté pour la seconde : EP-24,
  qui y aurait ajouté un contrat, une migration de données et une saisie.
- **#859 et #1026 reviennent d'EP-13** (décision de l'auteur du 2026-11-12, contre celle du
  2026-10-11) : ce sont des instabilités de la chaîne, que ce volet traite.
- **`Offset` borné au contrat** (#2778), comme `LockVersion`. Écartés : la borne dans le code seul,
  que le client engendré ignorerait ; rien.
- **« Sans rôle » par un paramètre booléen** (#2917). Écartés : une valeur sentinelle dans
  `access_role_ids`, qui ne serait plus une liste d'identifiants ; « Sans rôle » hors d'EP-24.
- **Un appel par compte pour une action groupée** (#2917, décision de l'auteur du 2026-11-11).
  Écartée : une opération groupée au contrat.
- **Les décimaux, champ par champ, dans le code** (#2875), par la règle d'US-1840. Écartée : une
  règle commune dans la base des modèles, qui ne connaît pas la colonne de chaque champ.
- **Le NUL : recenser, éprouver, corriger** (#2891). Écarté : tout passer en `Text` sans épreuve.
- **Un seul propriétaire de la liste des classeurs abîmés, dans `core/exchanges`** (#2723). Écarté :
  un renvoi de `core/costs` à `core/estimate`, qui ferait dépendre l'un de l'autre pour une
  constante.
- **Un renommage attend que son rôle soit libre** (#2897). Écartés : l'ignorer en silence ; fermer
  l'issue.
- **Le lecteur MS Project préfère `Manual*`** pour une tâche manuelle (#2923 ; décision de l'auteur
  du 2026-11-12). Écarté : un lecteur inchangé, qui aurait gardé le corpus tel quel mais lu d'un
  fichier réel autre chose que MS Project.
- **L'écart de calendrier compare aussi les calendriers de tâche** ; « Garder les durées » par
  défaut ; les décalages gardent leur valeur sous « Garder les dates » (#2922 ; décisions de l'auteur
  du 2026-11-12). Écartés : le calendrier du projet seul ; les décalages recalculés, qui n'ont pas de
  valeur déterminée quand un autre prédécesseur pilote la tâche.
- **Changer de règle relance l'analyse, par une opération** (#2922). Un état est une ressource
  (`DECISIONS.md`, « Forme des chemins ») : `PUT …/duration-rule`. Écartés : un compte rendu qui
  porterait les écarts des deux règles, deux fois plus lourd pour un planning de six mille tâches ;
  la règle portée par `applyImport`, qui appliquerait un compte rendu que l'utilisateur n'a pas lu ;
  rouvrir l'import, qui redéposerait le fichier.
- **Un contrôle des inodes de `/tmp` n'est pas outillé** (décision de l'auteur du 2026-11-12).
- **La mesure se lance du poste, pas dans la chaîne.** Écarté : un rapport écrit par un job de la
  chaîne, qui ajouterait une dépendance et des minutes à ce qu'on veut raccourcir.
- **`service / paths` coupé en quatre plateformes** plutôt qu'une plateforme partagée par plusieurs
  runners, que GitHub ne sait pas offrir. Écarté : retirer des parcours.
- **Une image de travail de l'e2e sur ghcr.io** plutôt qu'un miroir des paquets d'Ubuntu. Écarté :
  le seul paquet `make` déposé ailleurs, qui laisserait `make e2e-browsers` sur les miroirs.
- **La révision 1.0.5 va dans `main`** par une pull request de l'auteur, puis `epic/EP-24`
  reprend `main` ; son lot est au tableau de suivi pour que ses dépendants l'attendent.

---

## US-1850 — Les filtres des tables : la vérification de L5 et de L6 terminée, les mineurs reportés soldés

- **statut** : à faire
- **exigences** : `WF-IHM-0060-A`
- **opérations** : `getMe`, `updateMyPreferences`
- **issue** : #2933

**En tant que** chef de projet, manager ou administrateur, **je veux** que la barre, le panneau
repliable et les pastilles des filtres, livrés la nuit du 11 au 12 novembre sur toutes les tables
plates et rangés dans la barre des grilles arborescentes, soient vérifiés en entier, **afin de** ne
pas découvrir à l'usage ce que la vérification interrompue à 04 h 07 n'a pas vu (#2916).

**Critères d'acceptation.**

- `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. » : sa forme pour le panneau des filtres : son état, ouvert ou fermé, est gardé par grille (`display_preferences.grids.<grille>.filters_open`, absent = fermé), relu à la réouverture, propre à chaque utilisateur ;
- critère propre, que la 1.0.5 portera au Vérif de `WF-IHM-0060-A` (#2921) : « Le panneau des
  filtres d'une table plate, fermé par défaut, est retrouvé ouvert ou fermé comme l'utilisateur l'a
  laissé, sans changer celui des autres tables ; ses filtres actifs restent dits, panneau fermé,
  chacun ôtable. » ;
- écart : `WF-IHM-0060-A` — « Chaque colonne d'une table plate se trie dans les deux sens. » : constaté par EP-02 et EP-07, inchangé ;
- écart : `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose de tri ; dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans déplacer les tâches. » : idem ; les grilles arborescentes gardent leur clavier, leur saisie, leur collage, leur pli, leur annulation et leurs commandes de structure, ce qu'un parcours de chacune rejoue ;
- écart : `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours visibles, de même que la colonne de libellé après défilement horizontal. » : idem ; la hauteur d'une grille est recalculée quand le panneau, les pastilles ou la barre d'actions s'ouvrent ou se ferment au-dessus d'elle ;
- écart : `WF-IHM-0060-A` — « Le nombre de lignes par page choisi pour une table est retrouvé à sa réouverture, sans changer celui des autres tables ; une grille arborescente n'offre pas ce choix. » : constaté par EP-15 et EP-07, inchangé ;
- les échecs contre le service relevés à la vérification interrompue du 2026-11-12 sont rejoués
  fichier par fichier, sur la branche qui porte L4, puis L5, puis L6 : chacun passe, ou devient une
  issue qui dit sa cause ;
- les corrections de relecture faites après 03 h 50 sur L5 et L6 sont relues par le relecteur du
  langage, d'un seul tenant ;
- les mineurs reportés de la relecture de L2 (#2916, commentaire du 2026-11-11) sont soldés : un
  test DOM de « Effacer les filtres » avec un paramètre que la lecture écarte
  (`origins=nope&is_active=true` mène à `/admin/users` sans `origins=nope`) ; `include_inactive`
  seul dans l'adresse, lu côté serveur, et ajouté aux filtres gardés s'il filtre ; `FilterChips`
  n'attend plus de déplacer le focus après une navigation refusée ou oubliée.

**Notes de réalisation.** Le découpage L1 à L6 et ses choix sont dans les commentaires de #2916, qui
font foi : les poignées numérotées plutôt que des cases à cocher (2026-11-11), le nom accessible
provisoire d'une pastille de période avant hydratation, accepté. La chaîne de PR #2929 → #2930 →
#2931 est la première vérification ; ce lot la termine.

**Hors périmètre.** Ce que chaque écran met dans sa barre d'actions (US-1860 pour les comptes).

---

## US-1860 — La gestion des utilisateurs : ses filtres, « Sans rôle » et ses actions groupées

- **statut** : en cours
- **exigences** : `WF-ADM-0180-A`
- **opérations** : `listUsers`, `updateUser`, `setUserActivation`, `setUserAccessRoles`
- **issue** : #2954

**En tant qu'**administrateur, **je veux** retrouver d'un filtre les comptes arrivés sans rôle et
leur en donner un d'un geste, sur un écran dont les filtres ne prennent plus les deux tiers de la
page, **afin d'**accueillir les nouveaux arrivants en trois gestes (#2917, maquette validée).

**Critères d'acceptation.**

- `WF-ADM-0180-A` — « Avec un fournisseur externe, la première connexion d'une personne inconnue crée son compte, sans rôle, et elle n'a aucun droit tant qu'un rôle ne lui est pas donné. » : sa forme pour l'écran : le filtre des rôles offre « Sans rôle », que `listUsers` sert par un paramètre de requête qui retient les comptes sans rôle, en union avec `access_role_ids` ; filtrer « Créé par le fournisseur d'identité » et « Sans rôle », choisir toutes les lignes affichées, puis « Ajouter un rôle » donne ce rôle à chaque compte retenu ;
- écart : `WF-ADM-0180-A` — « Sur une installation sans annuaire ni fournisseur externe, un compte local se connecte. » : constaté par EP-03, inchangé ;
- écart : `WF-ADM-0180-A` — « Après fédération d'un annuaire, un compte de l'annuaire se connecte avec ses identifiants d'annuaire et un compte local avec son mot de passe. » : idem ;
- écart : `WF-ADM-0180-A` — « Après retrait de l'annuaire et synchronisation, les comptes qui en venaient existent toujours, désactivés, et leurs actes restent attribués. » : idem ;
- écart : `WF-ADM-0180-A` — « Réactivés après une nouvelle fédération qui les reconnaît, ils se connectent. » : idem ;
- écart : `WF-ADM-0180-A` — « Aucun écran de Waterfall ne paramètre un annuaire. » : idem ;
- le haut de page : « Lecture des comptes du fournisseur d'identité », son bouton et son état
  passent dans un menu « ⋯ » à côté de « Créer un compte local », qui reste la commande principale ;
  l'aide reste à côté du titre ;
- les filtres de la page sont dans le panneau d'US-1850 : Origine, Rôles d'habilitation, État du
  compte en menus à cases à cocher, Nœud d'organisation ; « Créé par », « Modifié par » et leurs
  dates dans la section d'audit repliée ;
- l'édition en ligne est gardée : nom, prénom, rattachement, rôles, état, l'interrupteur suivi de
  « Actif » ou « Désactivé » ;
- les actions groupées de la barre d'actions : « Ajouter un rôle », « Rattacher à », « Activer »,
  « Désactiver » ; le front enchaîne un appel par compte choisi (`setUserAccessRoles`, `updateUser`,
  `setUserActivation`), sans atomicité, puis dit les comptes refusés et pourquoi — un 412 d'un
  compte modifié entre-temps, le dernier administrateur qu'on ne peut désactiver.

**Notes de réalisation.** La décision de #2917 fait foi : un appel par compte, aucune opération
groupée au contrat. « Sans rôle » demande, lui, une modification du contrat : `access_role_ids` dit
aujourd'hui « An account without a role is retained by no value » (`docs/api/paths/access.yaml`), et
la liste est paginée par le serveur (décision de l'auteur du 2026-11-12 : un paramètre booléen, par
une issue `contract`). Dépend de L2 à L4 de #2916 (#2929).

**Hors périmètre.** Une opération groupée sur les comptes ; les filtres des autres écrans.

---

## US-1870 — Un écran ouvert sans session mène à la connexion, et l'accueil d'un compte sans projet le dit

- **statut** : à faire
- **exigences** : `WF-SEC-0020-A`, `WF-IHM-0120-A`
- **opérations** : `getMe`, `listProjects`
- **issue** : #2971

**En tant que** visiteur sans session, administrateur d'une installation neuve ou personne arrivée
sans rôle, **je veux** arriver sur la page de connexion plutôt que sur un écran de panne, puis sur
un accueil qui me dit quoi faire plutôt que « Introuvable », **afin de** savoir où aller dès le
premier écran (#2914, #2915).

**Critères d'acceptation.**

- `WF-SEC-0020-A` — « Un jeton de rafraîchissement inactif au-delà de deux heures est refusé, et l'utilisateur est ramené à l'écran de connexion puis, reconnecté, à l'écran visé. » : sa forme pour un visiteur qui n'a jamais ouvert de session : un écran ouvert sans témoin de session mène seul à `/login?next=<écran>`, puis, la connexion faite, à l'écran visé ;
- critère propre, que la 1.0.5 portera à `WF-SEC-0020-A` (#2914) : « Un écran ouvert sans session
  mène à l'écran de connexion, puis, la connexion faite, à l'écran visé. Une connexion que le
  fournisseur d'identité refuse ne relance pas la connexion d'elle-même : l'écran le dit et offre de
  recommencer. » ; après une connexion refusée, un témoin court posé par `/auth/callback` laisse
  l'écran « Session requise », sans boucle ;
- écart : `WF-SEC-0020-A` — « La désactivation d'un compte connecté sur deux postes interrompt les deux à leur requête suivante. » : constaté par EP-03, inchangé ;
- écart : `WF-SEC-0020-A` — « Un utilisateur qui se déconnecte ne peut plus agir avec ses jetons. » : idem ;
- écart : `WF-SEC-0020-A` — « Une adresse de retour qui ne désigne pas un écran de Waterfall — l'adresse d'un autre site, un chemin qui commence par « // », ou qui contient une barre oblique inverse ou un caractère de contrôle — ramène à l'accueil après la connexion. » : idem ; l'adresse de retour d'un écran ouvert sans session suit la même règle ;
- critère propre, que la 1.0.5 portera à `WF-IHM-0120-A` (#2915) : « L'administrateur d'une
  installation neuve arrive sur un accueil qui mène à l'administration ; une personne créée sans
  rôle par un fournisseur externe lit qu'il lui faut un rôle. » ; l'accueil décide sur les
  permissions, jamais sur le nom d'un rôle, et n'offre aucune redirection ;
- écart : `WF-IHM-0120-A` — « Un contributeur de deux projets les voit à sa connexion ; la levée du filtre montre aussi les projets qu'il peut ouvrir sans en être contributeur, et aucun autre. » : constaté par EP-04, inchangé ;
- écart : `WF-IHM-0120-A` — « Sur une installation au référentiel incomplet, l'accueil nomme les prérequis manquants et mène au référentiel. » : idem ;
- la réalisation, déjà dans `epic/EP-24` par #2927 et #2928, est vérifiée une fois la 1.0.5
  acceptée : chaque phrase nouvelle du Vérif a un test qui la cite, ou le lot l'écrit.

**Notes de réalisation.** Les décisions de #2914 et de #2915 font foi. La couverture de #2914 est
unitaire (`session/shell.test.tsx`, `tokens.test.ts`, `auth/callback/route.test.ts`), ses parcours
de service adaptés (`session.spec.ts`, `sign-in.spec.ts`).

**Hors périmètre.** Un parcours qui arrête Keycloak ou fait refuser le royaume.

---

## US-1880 — La file dit son taux d'échec hors régression et la durée de son palier complet

- **statut** : fini
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2934

**En tant que** développeur, **je veux** relever d'une commande, sur les passages réels de la file,
le taux d'échec qui n'est pas une régression et la durée du palier complet, **afin de** juger chaque
lot de la chaîne par ses passages, avant et après, et non par une mesure sur le poste.

**Critères d'acceptation.**

- une commande du Makefile relève, pour une branche et une fenêtre de passages de la file (`chain`,
  `merge_group`), leur nombre, leurs échecs par job et par étape, les parcours et les tests en échec
  avec leur fichier et leur ligne, et la durée de mur du palier complet, en médiane et au 90e
  centile ;
- elle classe chaque échec — régression, instabilité connue, infrastructure — d'après une liste
  versionnée des instabilités connues, et dit « à classer » ce qu'elle ne reconnaît pas ; un échec
  n'est une régression que par une relecture ;
- l'inventaire des instabilités depuis le 2026-11-05 est versionné : pour chaque test instable, son
  fichier et sa ligne, sa fréquence, sa cause établie ou son hypothèse, et l'issue qui le suit ;
- la référence est écrite : 370 passages et 88 échecs du 2026-11-05 au 2026-11-12, dont 68 dans
  `service / paths` ; 16 minutes de mur en médiane les 10 et 11 novembre.

**Hors périmètre.** Un tableau de bord ; une alerte.

---

## US-1890 — Les parcours contre le service ne font plus échouer la file sans régression

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune en propre — les lectures que les parcours instables attendent
- **issue** : #2939

**En tant que** développeur, **je veux** que les parcours contre le service passent dans la file
quand le code n'a pas régressé, **afin de** ne plus remettre une pull request en file à la main
(#2911).

**Critères d'acceptation.**

- chaque parcours que l'inventaire d'US-1880 dit instable contre le service a sa cause établie, par
  une mesure dans la chaîne, et sa correction, ou une issue qui porte sa décision ; en font partie,
  sur les passages du 2026-11-05 au 2026-11-12 : `service/backups.spec.ts:155` et `:240` (16
  passages), `revisions.spec.ts:238` à `:253`, le parcours de WF-REV-0080-A (8), `revisions.spec.ts:121`
  (2), `reference-resources.spec.ts:110` et `:112` (6), `structure.spec.ts:414` à `:452` (6) et
  `:333` (3), `planning-service.spec.ts` (6), `projects.spec.ts` (9) ;
- `timelines.spec.ts:263` (« Contexte de lecture » introuvable), vu en local seulement, est
  reproduit ou classé sans suite, avec sa mesure ;
- `revisions.spec.ts:121` ne lit plus trois fois la comparaison complète de PRJ-001, ou la lecture
  est corrigée, et son `test.slow()` n'est gardé que si la mesure le justifie ; de même pour le
  parcours de WF-REV-0080-A ;
- **la règle d'un parcours lent** est écrite dans le guide (`docs/dev/README-fr.md`, et sa
  traduction) : corriger la lecture d'abord, comme #2924 ; sinon isoler ou sérialiser le parcours ;
  n'élargir une attente qu'en dernier recours, avec la mesure qui la justifie ;
- l'effet est prouvé sur des passages réels de la file, avant et après (US-1880).

**Notes de réalisation.** #2924, fusionnée, a corrigé la cause de `structure.spec.ts:333` : une
requête par tâche pour son calendrier, et les lignes placées deux fois (`getRemainingIndicators` de
2 845 à 58 requêtes sur PRJ-001). Le lot qui termine L5 et L6 (US-1850) touche `structure.spec.ts`
et `planning-service.spec.ts`.

**Hors périmètre.** Les parcours contre le faux back, hors ceux que l'inventaire relève.

---

## US-1900 — La chaîne ne dépend plus d'un réseau qu'elle ne tient pas

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2944

**En tant que** développeur, **je veux** qu'une panne d'un miroir ou d'un registre tiers ne fasse
pas échouer la file avant le premier test, **afin qu'**un passage ne dépende que du code (#2913).

**Critères d'acceptation.**

- pour chaque dépendance réseau de la chaîne, la conception dit si elle est supprimée, mise en cache
  ou en miroir, et le lot le fait : `archive.ubuntu.com` (le paquet `make` de l'image de Playwright,
  les paquets système de `make e2e-browsers` ; #2913, six passages perdus le 2026-11-11) ; Docker
  Hub (le pull de mailpit, « failed to fetch oauth token ») ; Prism et Redocly téléchargés par
  `npx` ; le pull de l'image de Playwright, de 20 à 113 s ; les téléchargements de pandoc et de
  Python, vus en échec une fois chacun ;
- un passage de la file aboutit quand l'une de ces sources ne répond pas, ou échoue en nommant la
  source, sans consommer le palier entier ;
- l'effet est prouvé sur des passages réels de la file (US-1880).

**Hors périmètre.** Les runners eux-mêmes ; une infrastructure auto-hébergée.

---

## US-1910 — Le palier complet plus court : des morceaux équilibrés, des caches sous leur quota

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2948

**En tant que** développeur, **je veux** un palier complet de 12 minutes en médiane, **afin qu'**un
passage de la file coûte moins, en mur comme en minutes-runner.

**Critères d'acceptation.**

- le chemin critique et les minutes-runner du palier complet et du palier rapide sont relevés, job
  par job, sur des passages réels, et la conception dit où sont les gains ;
- les morceaux de l'e2e sont équilibrés par durée mesurée plutôt que par fichier (le 4/5 porte
  environ 260 s de tests contre environ 150 s pour les autres) ;
- le cache d'Actions tient sous son quota de 10 Go (10,8 Go mesurés le 2026-11-05), sans éviction
  ni installation à froid ; `.next/cache` est gardé d'un passage à l'autre ;
- `service / paths`, le plus long des jobs (environ 16,5 minutes pour 160 parcours), ne tient plus
  le chemin critique au-delà de la cible ;
- la durée de mur du palier complet est de 12 minutes au plus en médiane sur 100 passages de la
  file (décision de l'auteur du 2026-11-12), sans qu'aucun lot dégrade le taux d'US-1880.

**Hors périmètre.** Retirer un test ou un parcours pour gagner du temps.

---

## US-1920 — Les tests instables du back et du front attendent ce qu'ils affirment

- **statut** : en cours
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2935

**En tant que** développeur, **je veux** que les tests du back et du front que la charge fait
échouer soient corrigés, **afin que** ni la file ni `make check` sur un poste chargé n'échouent sans
régression (#859, #1026).

**Critères d'acceptation.**

- `cost-commands.dom.test.tsx`, « keeps the answer of the server in its row until a reading catches
  up with its version », attend son `rerender` et son `act` : il passe rejoué en boucle sous charge
  (#859) ;
- `test_an_account_whose_address_another_holds_whatever_its_case_is_not_created` a sa cause établie
  — ordre ou état partagé des tests — et sa correction (#1026) ;
- `installation.setup` (« 1 compte ») est déterministe ;
- le chargement du témoin ne rencontre plus `LockNotAvailable`
  (`test_the_witness_loads_the_nodes_of_the_example_then_deactivates_those_it_says_deactivated`,
  passage 42799623736) ;
- les autres échecs du back, du front et de Keycloak que l'inventaire d'US-1880 dit instables — dont
  le crash d'un worker Vitest et les cinq échecs de `keycloak / check` — ont leur cause établie et
  leur correction, ou une issue.

**Hors périmètre.** Les parcours de bout en bout (US-1890).

---

## US-1930 — Le poste local : un nombre de workers qui ne le sature pas, et pas de worktree sous `/tmp`

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** : #2953

**En tant que** développeur, **je veux** que `make e2e-service` passe sur le poste sans que je
choisisse son nombre de workers, **afin de** ne pas lire 18 à 23 échecs de navigation qui ne sont
que la charge (#2890).

**Critères d'acceptation.**

- le nombre de workers par défaut de `make e2e-service` se déduit du nombre de processeurs et de la
  part du créneau, au lieu de la moitié des processeurs ; le lot mesure 8, 10 et 12 workers, en
  plusieurs passages, avec et sans autres créneaux occupés, et retient la plus haute valeur sans
  échec de navigation (décision de l'auteur du 2026-11-11) ;
- le guide et `docs/dev/agents.md` disent qu'un worktree ne se tire jamais sous `/tmp`, dont le
  tmpfs a manqué d'inodes le 2026-11-12 sous les `node_modules` de worktrees tirés dans des
  scratchpads ; sans outil (décision de l'auteur du 2026-11-12).

**Hors périmètre.** Un contrôle des inodes par `make slot` ou `make slots`.

---

## US-1940 — Le classeur du reste à engager garde la nature d'une ligne à l'aller-retour, et les classeurs abîmés n'ont qu'une liste

- **statut** : fini
- **exigences** : `WF-INTF-0120-A`
- **opérations** : `requestExport`, `openImport`, `applyImport`
- **issue** : #2958

**En tant que** chef de projet, **je veux** qu'un reste à engager exporté puis réimporté rende
chaque ligne à sa nature, même quand un rôle et une catégorie portent le même code, **afin que**
l'aller-retour ne change pas une ligne de catégorie en ligne de rôle (#2752, #2723).

**Critères d'acceptation.**

- `WF-INTF-0120-A` — « Un reste à engager exporté d'une révision marquée puis réimporté dans la révision en cours met à jour les lignes de même lignée sans en créer aucune. » : sa forme pour un code partagé : le classeur range les libellés des rôles et ceux des catégories dans deux index ; un reste à engager dont un rôle et une catégorie partagent un code est exporté, la ligne de catégorie sous le libellé de sa catégorie, puis réimporté sans qu'aucune ligne change de nature ;
- écart : `WF-INTF-0120-A` — « Même critère que WF-INTF-0100, appliqué aux grandeurs réestimées ; les montants budgétés et les lignées de toutes les lignes sont inchangés après l'import, et une ligne absente du fichier conserve son reste à engager. » : constaté par EP-09, inchangé ;
- écart : `WF-INTF-0120-A` — « Avec huit heures par jour, une ligne de main-d'œuvre dont le fichier porte trois jours a un reste de vingt-quatre heures. » : idem ;
- écart : `WF-INTF-0120-A` — « Une tâche démarrée dont toutes les lignes du fichier portent zéro est terminée à la date de la revue ; une tâche non démarrée dont les lignes sont laissées telles quelles reste non réestimée. » : idem ;
- écart : `WF-INTF-0120-A` — « Un fichier qui recopie une ligne avec sa lignée voit les deux lignes rejetées, et la ligne existante inchangée. » : idem ;
- écart : `WF-INTF-0120-A` — « Un fichier sans date de revue applique les lignes qui ne terminent aucune tâche et rejette celles qui en termineraient une. » : idem ;
- écart : `WF-INTF-0120-A` — « Une cellule de reste effacée sur une ligne connue la met à zéro. » : idem ;
- la liste des exceptions d'un classeur abîmé n'a qu'un propriétaire, dans `core/exchanges`, que
  lisent le lecteur de devis et celui des coûts réels (`core/costs/extraction.py`, `_DAMAGES`) ; un
  test l'éprouve une fois pour les deux (décision de l'auteur du 2026-11-12).

**Notes de réalisation.** Le défaut de #2752 est celui de #2690 en miroir
(`core/estimate/remaining/excel/writer.py`, `_context`) ; `Reference.named`
(`core/estimate/importing.py`) départage un code partagé par le libellé, d'où le changement de
nature au réimport : le test couvre l'aller-retour, pas le seul export. La limite est dans la note
de version 0.3.0, à retirer avec elle.

**Hors périmètre.** Toute autre refonte de `core/exchanges`.

---

## US-1950 — L'ajout d'une tâche et l'insertion d'une ligne au reste à engager se jouent contre le service

- **statut** : à faire
- **exigences** : `WF-RAE-0040-A`
- **opérations** : celles que jouent les deux parcours, inchangées
- **issue** : #2964

**En tant que** développeur, **je veux** que les deux écritures du reste à engager que seuls des
parcours contre le faux back éprouvent soient jouées contre le service, **afin que** leur régression
se voie (#2909).

**Critères d'acceptation.**

- `WF-RAE-0040-A` — « Une tâche ajoutée depuis la grille de reste à engager apparaît dans la grille de planning de la révision en cours, et une tâche ajoutée au planning d'un projet En cours apparaît dans la grille de reste à engager parmi les tâches non démarrées ; la révision de référence est inchangée, et le budget de référence comme la valeur planifiée ne bougent pas. » : rejoué contre le service, étiqueté `@shared`, sur un projet que la course crée et porte En cours, pour la tâche ajoutée depuis la grille du reste à engager ;
- écart : `WF-RAE-0040-A` — « Une ligne ajoutée après la référence peut y être portée à un sous-projet. » : constaté par EP-09, inchangé ; l'insertion d'une ligne nommée, d'une catégorie et d'une quantité, est rejouée de même contre le service ;
- écart : `WF-RAE-0040-A` — « Les montants et les grandeurs sont présents pour chaque ligne, au reste à engager précédent et courant. » : constaté par EP-09, inchangé ;
- écart : `WF-RAE-0040-A` — « La saisie d'une charge de 80 heures sur une ligne de quantité 1 budgétée à 100 heures donne un montant réestimé de 80 fois le taux, projeté sur l'année de consommation de la ligne (WF-DEV-0030) ; le montant n'est pas saisissable. » : idem ;
- écart : `WF-RAE-0040-A` — « Les tâches non démarrées n'apparaissent qu'à la demande, et sont alors modifiables. » : idem ;
- écart : `WF-RAE-0040-A` — « La modification d'une ligne portée par une tâche terminée est refusée. » : idem ;
- écart : `WF-RAE-0040-A` — « Une tâche démarrée dont la fin est dépassée est signalée ; sa date n'est pas modifiable depuis cette grille. » : idem ;
- écart : `WF-RAE-0040-A` — « La saisie d'un reste à engager nul sur toutes les lignes d'une tâche non démarrée la termine, avec une date de démarrage égale à sa date de terminaison. » : idem ;
- écart : `WF-RAE-0040-A` — « Sur un projet qui n'est pas En cours, la grille ne propose ni création ni suppression de tâche ou de ligne. » : idem ;
- le commentaire de `structure.spec.ts:299` et le guide ne disent plus ces deux parcours sans
  jumeau.

**Notes de réalisation.** La conception d'EP-09, « Le harnais » : « Les parcours qui écrivent le
font sur un projet que la course crée (#2193) ». Les jumeaux vont dans `remaining.spec.ts`
(`bringInProgress`) ; `structure.spec.ts:250` et `:299` restent joués contre le faux back.

**Hors périmètre.** Un compte de course contributeur de PRJ-001.

---

## US-1960 — Le paramètre `Offset` borné par le contrat

- **statut** : à faire
- **exigences** : aucune — correction du contrat et du service
- **opérations** : toute liste paginée, par le paramètre commun `Offset`
- **issue** : #2959

**En tant que** développeur d'un client de l'API, **je veux** qu'un `offset` hors de ce que la base
sait lire soit refusé par 422, **afin de** ne jamais recevoir un 500 d'une liste (#2778).

**Critères d'acceptation.**

- le paramètre commun `Offset` porte `maximum: 2147483647` (`docs/api/components/parameters.yaml`),
  comme `LockVersion` depuis US-1810 ; #2778 devient l'issue `contract`, et `docs/api/DECISIONS.md`
  a son entrée (décision de l'auteur du 2026-11-12) ;
- une liste paginée lue avec `offset=2147483648` répond 422 `VALIDATION_FAILED`, `fields[]`
  désignant `/query/offset`, sur chaque route paginée, ce qu'un test confronte au contrat ;
- `make build-openapi`, `make inventory`, `make client-up-to-date` et
  `make server-models-up-to-date` passent.

**Hors périmètre.** Le paramètre `Limit`, déjà borné à 500.

---

## US-1970 — L'écran des rôles libère un rôle après un rejet et fait partir un renommage différé, et une référence hors forme ne s'affiche pas

- **statut** : à faire
- **exigences** : `WF-ADM-0010-A`, `WF-OBS-0020-A`
- **opérations** : `updateAccessRole`, `deleteAccessRole`, et toute lecture d'un écran
- **issue** : #2963

**En tant qu'**administrateur, **je veux** qu'un rôle dont la suppression est rejetée redevienne
modifiable, et qu'un renommage validé pendant une écriture parte sans message faux, **afin de** ne
pas rester devant une ligne inerte ni lire « serveur injoignable » à tort (#2898, #2897, #2882,
#2886).

**Critères d'acceptation.**

- `WF-ADM-0010-A` — « Un administrateur renomme un rôle prédéfini et en modifie les permissions, et il supprime sans erreur un rôle prédéfini qu'aucun compte ne porte. » : sa forme pour une écriture en vol ou rejetée : une suppression confirmée dont l'écriture est rejetée libère le rôle, dont la ligne, le libellé, les cases et « Supprimer » redeviennent actifs (#2898) ; un renommage validé pendant qu'une écriture du même rôle est en vol attend que le rôle soit libre, puis part une seule fois de la version répondue, sans message (#2897) ;
- écart : `WF-ADM-0010-A` — « Sur une installation neuve, les trois rôles existent et leurs permissions couvrent les usages des exigences citées. » : constaté par EP-03, inchangé ;
- écart : `WF-ADM-0010-A` — « La suppression du rôle « administrateur » qu'il porte est refusée (WF-ADM-0090, WF-ADM-0120). » : idem ;
- `WF-OBS-0020-A` — « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul identifiant, que le message présenté à l'utilisateur contient. » : sa forme pour une réponse inattendue : `UnexpectedAnswer` ne garde dans son digest qu'un `correlation_id` de la forme du contrat (`^[A-Za-z0-9._-]{1,64}$`), comme `envelope()` et `rejection.ts` ; une valeur hors forme n'est pas affichée comme référence sur l'écran de panne (#2882) ;
- écart : `WF-OBS-0020-A` — « Une recherche des secrets et des jetons connus dans les journaux ne les trouve pas. » : le service, EP-13 clôt ;
- les trois paragraphes de #2886 sont refondus à la largeur de leurs voisins
  (`components/commands/rejection.ts`, `components/system/system-failure.tsx`, `docs/dev/README.md`).

**Notes de réalisation.** Les propositions de #2898, de #2897 et de #2882 font foi ; pour #2897,
`RoleAnswers` expose une promesse « rôle libre » par identifiant (décision de l'auteur du
2026-11-12).

**Hors périmètre.** La matrice des permissions, qui a déjà son `finally`.

---

## US-1980 — Un caractère NUL ou un décimal démesuré à l'entrée du service est refusé par 422

- **statut** : en cours
- **exigences** : aucune — correction du service
- **opérations** : toute lecture qui porte un paramètre de requête libre ; `setDurationUnits`, les
  écritures d'un nœud du planning et d'une ligne de devis
- **issue** : #2960

**En tant que** développeur d'un client de l'API, **je veux** qu'une valeur que PostgreSQL ne sait
pas lire soit refusée par 422 à son champ, **afin de** ne jamais recevoir un 500 (#2891, #2875).

**Critères d'acceptation.**

- les paramètres de requête libres du service, lus en `str` nu, sont recensés ; `%00` est éprouvé
  sur chacun par un test paramétré ; ceux qui le laissent atteindre la base passent en `Text` et
  répondent 422 `VALIDATION_FAILED` à `/query/<paramètre>`, comme `code` de `listOrgNodes` depuis
  #2233 ; ce que le test trouve sans effet reste tel quel (décision de l'auteur du 2026-11-12) ;
- hors des seuils et de la matrice, chaque décimal que #2875 relève refuse par 422
  `VALIDATION_FAILED`, à son pointeur, une valeur de plus de dix décimales ou dont la partie entière
  dépasse sa colonne, comme US-1840 : les trois constantes des unités de durée, les durées et les
  décalages du planning, le débours unitaire et la quantité d'une ligne de devis ; le contrat et
  `docs/api/DECISIONS.md` ne changent pas (décision de l'auteur du 2026-11-12) ;
- le scénario de #2875 — `hours_per_day` à `8.` suivi de vingt mille zéros, un débours unitaire de
  quatorze chiffres — répond 422, rejoué sur une base.

**Notes de réalisation.** Chaque test cite l'exigence du champ qu'il refuse, comme ceux d'US-1840.
La capacité d'un rôle (`monthly_hours`, `headcount`) est laissée à EP-10, qui la reprend
(`WF-REF-0100-A`). Les mois, les trimestres et la durée d'une cellule collée, que le contrat lit par
`\d` (#2875, « Du même relevé »), sont tranchés par la conception.

**Hors périmètre.** Une règle commune dans la base des modèles, écartée.

---

## US-1990 — L'export MS Project s'ouvre aux mêmes dates dans MS Project, et le corpus porte un décalage négatif en semaines

- **statut** : à faire
- **exigences** : `WF-INTF-0050-A`, `WF-INTF-0040-A`, `WF-QUA-0080-A`
- **opérations** : `requestExport`, `openImport`
- **issue** : #2965

**En tant que** chef de projet, **je veux** qu'un planning exporté s'ouvre dans MS Project aux dates
que Waterfall affiche, tâches manuelles comprises, **afin de** le retravailler dans MS Project sans
qu'une branche entière glisse d'un jour (#2923, #2812 ; recette de l'auteur du 2026-11-11 dans MS
Project 2024).

**Critères d'acceptation.**

- `WF-INTF-0050-A` — « Un planning Waterfall exporté au format XML s'ouvre sans erreur dans les versions de MS Project visées par WF-INTF-0040. » : constaté en recette par l'auteur ; ici, sa forme pour une tâche manuelle : l'export écrit `ManualStart`, `ManualFinish` et `ManualDuration` aux valeurs de `Start`, `Finish` et `Duration`, à leur place dans la séquence du schéma, et un jalon manuel de durée nulle porte une durée nulle ; un test lit le XML écrit, et non ce que le lecteur de Waterfall en relit ;
- `WF-INTF-0050-A` — « En mode automatique, MS Project recalcule pour chaque tâche des dates de début et de fin identiques à celles affichées par Waterfall. » : constaté en recette ; ici, chaque tâche porte `Estimated` à 0, après `DurationFormat`, et l'en-tête porte `DefaultStartTime` et `DefaultFinishTime`, le début et la fin de la journée du calendrier par défaut exporté ;
- écart : `WF-INTF-0050-A` — « Vérifiée en recette pour l'ouverture dans MS Project ; l'égalité des dates est couverte par le corpus de WF-QUA-0080. » : la recette est celle de l'auteur ; aucun test ne demande MS Project ;
- écart : `WF-INTF-0050-A` — « Les calendriers Waterfall y figurent et sont affectés aux tâches, et chaque tâche porte son identifiant Waterfall et, dans ses notes, sa description. » : constaté par EP-06, inchangé ;
- `WF-INTF-0040-A` — « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD, FF ou DF, et décalage — sont identiques à celles du fichier source ; une tâche en mode manuel du fichier est en mode manuel aux mêmes dates ; une tâche portant une contrainte « Pas avant le » est en mode manuel et signalée ; une tâche à 50 % d'avancement est importée non démarrée ; aucune ressource et aucun calendrier présents dans le fichier n'a été créé dans Waterfall, et l'utilisateur est informé que ces éléments ont été ignorés. » : sa forme pour le lecteur : pour une tâche manuelle, il lit `ManualStart`, `ManualFinish` et `ManualDuration` quand le fichier les porte, comme MS Project, et `Start`, `Finish` et `Duration` sinon (décision de l'auteur du 2026-11-12) ; le corpus rejoué n'en change aucune date ;
- écart : `WF-INTF-0040-A` — « Un fichier XML produit par MS Project 2013 est importé sans erreur. » : constaté par EP-06, inchangé ;
- écart : `WF-INTF-0040-A` — « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les lignes de devis et les lignées de ses tâches, et ses tâches démarrées. » : idem ;
- écart : `WF-INTF-0040-A` — « Un fichier qui place la tâche d'un poste hors du sous-arbre de la tâche de son lot est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée a disparu est appliqué et le compte rendu nomme le poste qu'elle portait ; une tâche rattachée réimportée conserve son rattachement. » : idem ;
- `WF-QUA-0080-A` — « Chaque cas cité par le corps figure dans au moins un planning du corpus. » : le fichier 02 du corpus, repris par l'auteur dans MS Project avec une liaison à décalage négatif en semaines, déclare `lag_negative_w` dans `corpus.json` ; le test du corpus n'a plus de cas non exécuté pour lui (#2812) ;
- `WF-QUA-0080-A` — « Chaque planning du corpus réimporté puis exporté par Waterfall est valide contre le schéma ; un élément exporté hors de l'ordre du schéma fait échouer ce test, et l'absence du schéma le marque non exécuté. » : l'export complété reste valide contre le schéma, pour chaque planning du corpus ;
- écart : `WF-QUA-0080-A` — « La modification de la règle de calcul des dates fait échouer au moins un test du corpus. » : constaté par EP-06, inchangé ;
- écart : `WF-QUA-0080-A` — « Leur exécution ne demande ni MS Project, ni base de données, ni navigateur. » : idem.

**Notes de réalisation.** `core/planning/msproject/writer.py`, `_task`. Les deux corrections —
`Manual*` et `Estimated` — sont confirmées par l'auteur dans MS Project 2024 : nécessaires, et
suffisantes sur le planning éprouvé. Aucun test ne lit, ne cite ni ne nomme un planning réel.

**Hors périmètre.** L'import sur un autre calendrier (US-2000).

---

## US-2000 — L'import MS Project d'un planning bâti sur un autre calendrier le signale, et garde ses durées ou ses dates

- **statut** : à faire
- **exigences** : `WF-INTF-0040-A`, `WF-PLA-0160-A`, `WF-INTF-0080-A`
- **opérations** : `openImport`, `getImport`, `applyImport`, `abandonImport`
- **issue** : #2972

**En tant que** chef de projet, **je veux** qu'un planning saisi dans MS Project sur des journées de
7 heures soit importé en gardant ses durées dans leur unité, ou ses dates, **afin de** ne pas perdre
les dates de presque toutes ses tâches à l'import (#2922).

**Critères d'acceptation.**

- `WF-INTF-0080-A` — « Pour un fichier qui contient des lignes invalides, le compte rendu les liste avec leur motif avant la confirmation. » : sa forme pour un écart de calendrier : avant la confirmation, le compte rendu dit que les journées du calendrier du projet du fichier ou ses constantes diffèrent de ceux de l'installation — les heures par jour de part et d'autre, les plages horaires du fichier —, et nomme chaque tâche dont le calendrier propre, dans le fichier, diffère du calendrier Waterfall applicable (décision de l'auteur du 2026-11-12) ; le calendrier du fichier n'est toujours pas importé ;
- `WF-INTF-0080-A` — « Si l'utilisateur abandonne à cette étape, le projet reste inchangé. » : de même après avoir changé d'option, le compte rendu étant rendu à nouveau ;
- écart : `WF-INTF-0080-A` — « Si l'import est interrompu pendant son application, le projet revient à son état antérieur. » : constaté par EP-06, inchangé ;
- critère propre, que la 1.0.5 portera au Vérif de `WF-PLA-0160-A` (#2922) : « Un fichier MS Project
  dont les constantes ou le calendrier diffèrent de ceux de l'installation est signalé au compte
  rendu ; importé en gardant les durées, une tâche de "2 j" saisie à 7 h par jour vaut deux jours,
  soit seize heures avec les valeurs par défaut ; importé en gardant les dates, sa durée est le
  temps de travail entre ses dates du fichier sur son calendrier Waterfall. » ;
- le choix n'est proposé qu'en présence de l'écart, avant application ; « Garder les durées » est
  proposée par défaut : une durée ou un décalage saisi en jours, semaines ou mois garde sa valeur
  dans son unité, ses heures du fichier divisées par les heures de l'unité aux constantes du
  fichier ; une durée en minutes ou en heures garde ses heures ; le temps écoulé n'est pas
  concerné ;
- « Garder les dates » : chaque tâche automatique reçoit pour durée le temps de travail, sur son
  calendrier Waterfall applicable, entre le début et la fin du fichier, dans l'unité de sa durée aux
  constantes de l'installation ; les décalages gardent leur valeur dans leur unité, et les écarts de
  dates que le moteur laisse encore sont présentés (décision de l'auteur du 2026-11-12) ;
- les tâches manuelles gardent dans tous les cas les dates du fichier ;
- écart : `WF-PLA-0160-A` — « Un fichier MS Project dont les constantes diffèrent de celles de l'installation est importé avec les mêmes durées en heures, et le compte rendu signale la différence. » : la phrase que la 1.0.5 réécrit (#2922) ; elle reste vraie d'un import sans le choix, jusqu'à la 1.0.5 ;
- `WF-PLA-0160-A` — « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer d'unité. » : un fichier exporté par Waterfall porte ses calendriers et ses constantes : il ne présente aucun écart de calendrier, et aucun choix n'est proposé ;
- écart : `WF-PLA-0160-A` — « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize heures, « 1 sem » quarante heures et « 1 m » cent soixante heures. » : constaté par EP-06, inchangé ;
- écart : `WF-PLA-0160-A` — « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit à la dernière heure travaillée d'un vendredi s'achève le dimanche ; le successeur, sur un calendrier du lundi au vendredi, commence le lundi à la première heure travaillée, de même qu'avec un décalage de 2 eh. » : idem ;
- écart : `WF-PLA-0160-A` — « Un décalage de 2 j sur la même liaison le fait commencer le mercredi. » : idem ;
- écart : `WF-PLA-0160-A` — « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des langues de l'interface. » : idem ;
- écart : `WF-PLA-0160-A` — « En anglais, « 1 j » et « 1 d » valent chacun un jour ; « 3 », saisi sans suffixe, vaut trois jours. » : idem ;
- écart : `WF-PLA-0160-A` — « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans une révision en cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision marquée, elle vaut toujours seize heures. » : idem ;
- `WF-INTF-0040-A` — « Après import, les tâches et leurs liaisons de prédécesseur — type FD, DD, FF ou DF, et décalage — sont identiques à celles du fichier source ; une tâche en mode manuel du fichier est en mode manuel aux mêmes dates ; une tâche portant une contrainte « Pas avant le » est en mode manuel et signalée ; une tâche à 50 % d'avancement est importée non démarrée ; aucune ressource et aucun calendrier présents dans le fichier n'a été créé dans Waterfall, et l'utilisateur est informé que ces éléments ont été ignorés. » : inchangé sur un fichier sans écart de calendrier ; sur un fichier en écart, les calendriers du fichier restent ignorés et dits ignorés, en plus du signalement ;
- écart : `WF-INTF-0040-A` — « Un fichier XML produit par MS Project 2013 est importé sans erreur. » : constaté par EP-06, inchangé ;
- écart : `WF-INTF-0040-A` — « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les lignes de devis et les lignées de ses tâches, et ses tâches démarrées. » : idem ;
- écart : `WF-INTF-0040-A` — « Un fichier qui place la tâche d'un poste hors du sous-arbre de la tâche de son lot est rejeté et le compte rendu nomme les deux tâches ; un fichier dont une tâche rattachée a disparu est appliqué et le compte rendu nomme le poste qu'elle portait ; une tâche rattachée réimportée conserve son rattachement. » : idem ;
- le corpus (`fixtures/msproject/`) reçoit un planning synthétique saisi en jours à 7 heures par
  jour, construit pour le test, qui éprouve les deux options.

**Notes de réalisation.** Le moteur n'est pas en cause : réglé sur le calendrier et les constantes
du fichier, il reproduit les dates de MS Project sans écart (#2922, contre-épreuve du 2026-11-11).
C'est la règle de conversion des durées à l'import qui change. Le contrat change avant le code, par
une issue `contract`. Dépend de la révision 1.0.5 (US-2010).

**Hors périmètre.** Importer le calendrier du fichier ; tout planning réel.

---

## US-2010 — La spécification 1.0.5 écrit quatre décisions, et la 1.0.4 est relue contre le code

- **statut** : à faire
- **exigences** : `WF-DEV-0030-A`
- **opérations** : aucune
- **issue** : #2968

**En tant qu'**auteur de la spécification, **je veux** que les décisions prises depuis la 1.0.4
soient écrites dans le document, et que chaque phrase de la 1.0.4 ait son test ou son écart nommé,
**afin que** la spécification, la roadmap et le code disent la même chose.

**Critères d'acceptation.**

- la révision 1.0.5 de la spécification, écrite par l'auteur en révisions suivies puis acceptée par
  lui, porte les décisions de #2914 (`WF-SEC-0020`), de #2915 (`WF-IHM-0120`), de #2921
  (`WF-IHM-0060`) et de #2922 (`WF-INTF-0040`, `WF-PLA-0160`, `WF-INTF-0080`) ; `make check-spec`
  passe ; aucun agent ne l'écrit ;
- une fois la 1.0.5 dans `main`, les phrases nouvelles des Vérif sont citées mot pour mot par les US
  qui les réalisent — US-1850, US-1870 et US-2000 ici, et les US des EPIC livrés qui citent ces
  exigences —, et `make roadmap` passe ;
- `WF-DEV-0030-A` — « Une part consommée l'année qui précède l'année de référence vaut son montant de base, quel que soit le taux d'inflation. » : la phrase de la 1.0.4 est réalisée (`inflation_factor`), mais son test, `test_year_before_the_reference_year_is_not_deflated_pending_2545` (`backend/tests/test_pricing.py`), ne cite aucune exigence « en attendant #2545 » : il cite `WF-DEV-0030-A`, et perd sa réserve ;
- écart : `WF-DEV-0030-A` — « Une même ligne consommée deux ans après l'année de référence, avec un taux d'inflation de 3 %, vaut 1,03 x 1,03 fois son montant de base. » : constaté par EP-07, inchangé ;
- écart : `WF-DEV-0030-A` — « Une ligne consommée dans l'année de référence vaut son montant de base. » : idem ;
- écart : `WF-DEV-0030-A` — « Une ligne de provision portée par une tâche consommée deux ans après l'année de référence vaut sa gravité pondérée par sa probabilité, sans autre projection. » : EP-08 clôt ;
- chaque exigence que la 1.0.4 a revue — `WF-CRE-0010`, `WF-CRE-0020`, `WF-DAT-0080`,
  `WF-DEV-0030`, `WF-INTF-0100`, `WF-INTF-0120`, `WF-PLA-0040`, `WF-PLA-0140`, `WF-REF-0100`,
  `WF-REV-0080` et le glossaire — est classée dans la conception : réalisée, où et par quel test ;
  écart corrigé ici ; ou écart d'un autre EPIC, nommé ;
- la roadmap suit : le fichier d'EP-06 ne note plus en écart la disposition en couloirs d'une
  chronologie (`WF-PLA-0140-A`, #2871), réalisée par EP-15 (`DisplayPreferences.timelines`) ; le
  fichier d'EP-05 dit la reprise de `WF-REF-0100-A` par EP-10 ; #2546 est fermée, la 1.0.4 ayant
  ajouté la phrase du refus `NODE_CYCLE`.

**Notes de réalisation.** Une modification de la spécification va dans `main`, par une pull request
de l'auteur, puis `epic/EP-24` reprend `main` ; elle n'est pas le travail d'un livreur. Le lot est
dans le tableau de suivi pour que ses dépendants l'attendent.

**Hors périmètre.** La capacité d'un rôle (`WF-REF-0100-A`), à EP-10.

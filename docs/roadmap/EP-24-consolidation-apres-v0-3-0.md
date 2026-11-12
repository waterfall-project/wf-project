---
id: EP-24
titre: Consolider après la v0.3.0 — les filtres des tables et la gestion des utilisateurs achevés, une file de fusion qui n'échoue plus sans régression, les constats d'EP-09 et d'EP-23 soldés, l'aller-retour MS Project tenu dans MS Project, la spécification 1.0.5
statut: à planifier
depend_de: EP-09, EP-23
famille: front, back, plateforme
issue:
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
   ouvrir aucun projet, dont le code est dans `epic/cadrage` (#2914, #2915, PR #2927 et #2928) —
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
- **La branche de livraison est `epic/cadrage`**, et non `epic/EP-24` (décision de l'auteur du
  2026-11-12, contre la règle du README, « Branches », qui nomme `epic/EP-nn`). Elle est tirée de
  `main` au tag `v0.3.0`, sa file de fusion est paramétrée (jeu de règles « merge queue
  epic/cadrage »), et elle reçoit le travail de la nuit par #2926 à #2931 : le thème de la page de
  connexion, #2914, #2915, #2916 L1 à L6. Aucun livreur ne tire `epic/EP-24` ; chaque lot part
  d'`epic/cadrage` et y revient, et `BASE=origin/epic/cadrage` partout où un agent écrirait
  `origin/epic/EP-nn`. Ce que l'outillage suppose encore d'`epic/EP-nn` est réglé par la conception.
- La révision 1.0.5 de la spécification, écrite par l'auteur, précède le lot qui réalise #2922 et
  celui qui relie ses phrases aux US.
- Le fichier 02 du corpus, repris par l'auteur dans MS Project avec une liaison à décalage négatif
  en semaines, précède le lot qui déclare `lag_negative_w` (#2812).

## Définition de fini

- sur les 100 derniers passages de la file d'`epic/cadrage` (`chain`, `merge_group`), au plus 2
  échecs qui ne soient pas une régression, classés par l'outil de mesure et relus ; la durée de mur
  du palier complet y est de 12 minutes au plus en médiane (16 minutes les 10 et 11 novembre) ;
- chaque instabilité de l'inventaire est corrigée, ou suivie par une issue qui porte sa décision ;
- un lot qui touche la chaîne a prouvé son effet par des passages réels, avant et après, et non par
  une mesure sur le poste ;
- les parcours contre le service qui échouaient à la vérification interrompue du 2026-11-12 passent
  sur `epic/cadrage`, L4, L5 et L6 fusionnés ;
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
- `make check` passe sur `epic/cadrage`, la file est verte ; `make roadmap` et `make requirements`
  passent ;
- chaque issue de « Constats reçus » est fermée par la fusion de son lot, ou reportée par sa
  décision.

## Constats reçus

Tranchés par l'auteur le 2026-11-12, au cadrage ; renommés `[EP-24]`, passés au label `EP-24` et
rattachés à leur US à l'ouverture des issues.

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

Reporté par ce cadrage : la capacité d'un rôle (`WF-REF-0100-A`, #2836, fermée) → EP-10, par une
issue ouverte sous #2427.

## Conception

À écrire après la validation des US (étape 2 de « Démarrer un EPIC »).

---

## US-1850 — Les filtres des tables : la vérification de L5 et de L6 terminée, les mineurs reportés soldés

- **statut** : à faire
- **exigences** : `WF-IHM-0060-A`
- **opérations** : `getMe`, `updateMyPreferences`
- **issue** :

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

- **statut** : à faire
- **exigences** : `WF-ADM-0180-A`
- **opérations** : `listUsers`, `updateUser`, `setUserActivation`, `setUserAccessRoles`
- **issue** :

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
- **issue** :

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
- la réalisation, déjà dans `epic/cadrage` par #2927 et #2928, est vérifiée une fois la 1.0.5
  acceptée : chaque phrase nouvelle du Vérif a un test qui la cite, ou le lot l'écrit.

**Notes de réalisation.** Les décisions de #2914 et de #2915 font foi. La couverture de #2914 est
unitaire (`session/shell.test.tsx`, `tokens.test.ts`, `auth/callback/route.test.ts`), ses parcours
de service adaptés (`session.spec.ts`, `sign-in.spec.ts`).

**Hors périmètre.** Un parcours qui arrête Keycloak ou fait refuser le royaume.

---

## US-1880 — La file dit son taux d'échec hors régression et la durée de son palier complet

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** :

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
- **issue** :

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
- **issue** :

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
- **issue** :

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

- **statut** : à faire
- **exigences** : aucune — outil du dépôt
- **opérations** : aucune
- **issue** :

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
- **issue** :

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

- **statut** : à faire
- **exigences** : `WF-INTF-0120-A`
- **opérations** : `requestExport`, `openImport`, `applyImport`
- **issue** :

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
- **issue** :

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
- **issue** :

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
- **issue** :

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

- **statut** : à faire
- **exigences** : aucune — correction du service
- **opérations** : toute lecture qui porte un paramètre de requête libre ; `setDurationUnits`, les
  écritures d'un nœud du planning et d'une ligne de devis
- **issue** :

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
- **issue** :

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
- **issue** :

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
- **issue** :

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
de l'auteur, puis `epic/cadrage` reprend `main` ; elle n'est pas le travail d'un livreur. Le lot est
dans le tableau de suivi pour que ses dépendants l'attendent.

**Hors périmètre.** La capacité d'un rôle (`WF-REF-0100-A`), à EP-10.

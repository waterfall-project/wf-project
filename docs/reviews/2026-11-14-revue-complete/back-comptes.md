# Revue — comptes, habilitations, audit, et couverture des habilitations sur toutes les routes

Commit relu : `29785cc` (`main`). Lecture seule ; aucun test lancé, aucun constat n'a été exécuté :
« confirmé » veut dire « chemin lu de bout en bout dans le code », pas « rejoué ».

## Synthèse

Le périmètre est, de loin, soigné : l'évaluation est déclarative (`Requires`, `RequiresProject`),
lue à chaque requête sans cache, épinglée route par route par `test_access_evaluation.py`
(`ASKED`, `ON_PROJECT`) ; les 132 routes servies sont toutes authentifiées, hors `getLiveness` et
`getInstallation`, voulues publiques ; l'identifiant de projet du chemin est repassé à toutes les
requêtes du noyau que j'ai sondées (pas d'IDOR trouvé sur tâche, ligne, sous-projet, chronologie,
révision, import, dépôt, export). Les écritures de comptes et de rôles sont versionnées
(`lock_version` testé dans l'écriture), ordonnées par un verrou consultatif unique, et aucun appel à
Keycloak ne se fait transaction ouverte côté API.

Ce qui inquiète tient au **modèle**, pas à la mécanique : (1) la séparation voulue deux fois par
l'auteur entre « gérer les comptes » et « gérer les rôles » (#834, #1732) est défaite par le lien
de fixation du mot de passe et par le changement d'adresse d'un compte local, qui donnent à un
porteur de `users.write` seul le compte de n'importe quel administrateur ; (2) la garde du dernier
administrateur ne compte que les deux permissions de modification, alors que les routes
d'administration exigent aussi les permissions de consultation : un clic dans la matrice des rôles
verrouille l'administration. Le reste est mineur : un oracle d'existence de révision par
`undo`/`redo`, un export téléchargeable après retrait des droits, l'avatar validé sur sa seule
signature, deux `VALUE_TOO_LONG` sans `max_length`, `emailVerified` posé par un lien remis à la main.

## Constats bloquants

### BAC-01 — Un porteur de `users.write` seul prend le compte d'un administrateur (lien de fixation, changement d'adresse)

- **Issue** : #3342.
- **Où** : `backend/src/waterfall/api/users.py:133` (`WRITE = users.read + users.write`),
  `:672-698` (`createPasswordSetupLink`), `:467-501` et `:513-516` (`updateUser` porte la nouvelle
  adresse à Keycloak) ; `backend/src/waterfall/core/users/password_link.py:37-52` (seules
  conditions : local, non anonymisé, actif) ;
  `deploy/keycloak/extension/src/main/java/io/github/waterfallproject/keycloak/PasswordSetupLinkResource.java:86-95`
  (le refus `has_password` ne vaut que pour le lien d'installation ; le lien ordinaire est forgé
  pour un compte qui a déjà un mot de passe) et `PasswordSetupTokenHandler.java:82-89`, `:104-127`
  (le lien ouvre `UPDATE_PASSWORD` sans rien demander de l'ancien) ;
  `deploy/keycloak/realm/waterfall.yaml:27` (`resetPasswordAllowed: true`) ; contrat
  `docs/api/paths/access.yaml:520-528` (« sets or resets their password … under `users.write` »).
- **Quoi** : la décision #834 (`docs/api/DECISIONS.md:6249-6258`) et EP-18/US-1050 (#1732,
  `DECISIONS.md:10319-10323`) posent qu'« un porteur de la seule gestion des comptes ne se donne pas
  le rôle administrateur », et ont écarté « assumer l'élévation par écrit, contraire à
  WF-ADM-0090 ». Deux chemins restent ouverts sous `users.write` seul, sans `access_roles.write`.
- **Scénario A** : U porte un rôle composé `users.read` + `users.write` (le cas même de #834).
  `POST /users/{id de l'administrateur}/password-link` → 201, l'URL lui est rendue. U l'ouvre,
  confirme, fixe un mot de passe : il est connecté comme l'administrateur (compte local, celui de
  l'amorçage par exemple), porte `access_roles.write`, `platform_restore`, etc. Le journal garde
  `password_link_create` par U, mais tout ce que U fait ensuite est attribué à l'administrateur
  (WF-SEC-0030 ne dit plus qui a agi), et l'administrateur a perdu son mot de passe.
- **Scénario B** : `PATCH /users/{id de l'administrateur}` avec une adresse que U contrôle
  (`carry_identity` l'écrit dans Keycloak, où l'adresse est l'identifiant), puis « mot de passe
  oublié » sur la page de Keycloak : le courriel part chez U.
- **Vérifié** : la garde de la route (aucune autre condition que `Requires`), le noyau
  (`lock_link_holder`), le client (`keycloak_admin.make_password_link`, `:378-398`), le point
  d'entrée Java et le gestionnaire du jeton. Aucun test ne refuse le lien d'un compte plus habilité
  que l'appelant (`test_users_password_link.py:210` n'éprouve que 403/404 sur les permissions de
  l'appelant). Non rejoué contre Keycloak. Limite : avec les trois rôles livrés, seul
  l'administrateur porte `users.write` ; la faille demande un rôle composé — c'est exactement la
  configuration que #834 et #1732 ont jugée devoir tenir (WF-ADM-0020 : tout jeu se compose).
- **Proposition** : pour `createPasswordSetupLink`, `resendInvitation` et le changement d'identité
  d'un compte local (`updateUser`), refuser par 403 `PERMISSION_MISSING`
  (`missing_permission: access_roles.write`) quand le compte visé porte une permission que
  l'appelant n'a pas (au minimum `access_roles.write`), l'appelant agissant sur lui-même excepté ;
  la commande correspondante du compte devient indisponible. C'est une modification du contrat
  (description de l'opération et de son 403) et de la décision #834, à trancher par l'auteur.
  Tests : un appelant `users.read`+`users.write` demande le lien, le renvoi et un changement
  d'adresse d'un compte administrateur → 403, rien d'inscrit, Keycloak non appelé (`traces()`) ;
  contre la plateforme, le mot de passe de l'administrateur vaut encore.
- **Confiance** : confirmé (lecture de bout en bout ; non exécuté).

## Constats majeurs

### BAC-02 — La garde du dernier administrateur ignore les permissions de consultation que ses routes exigent

- **Issue** : #3342 (ouverte).
- **Où** : `backend/src/waterfall/core/access_roles/administrators.py:33`
  (`ADMINISTRATION = ("users.write", "access_roles.write")`) et `:44-55` ; contre
  `backend/src/waterfall/api/access_roles.py:57-59` (`updateAccessRole`, `deleteAccessRole`,
  `listAccessRoles` exigent `access_roles.read`) et `backend/src/waterfall/api/users.py:131-134`
  (`setUserAccessRoles` exige `users.read`).
- **Quoi** : la garde tient pour administrateur un compte qui porte les deux permissions de
  modifier ; mais sans la permission de consulter, chaque route d'administration répond 404
  (`require` : consultation manquante = objet inconnu). La modification ne vaut pas consultation
  dans le code (aucune implication, ni dans `_grant`, ni dans l'écran).
- **Scénario** : installation dont les administrateurs partagent le rôle prédéfini
  « Administrateur ». L'un d'eux décoche la case « consulter » de FBS-1.2 dans la matrice (une case
  = un `PATCH`, `frontend/src/components/admin/role-commands.tsx`). La garde lit encore des
  administrateurs (les deux `.write` sont là) et accepte. Dès la requête suivante, l'écran des rôles
  répond 404 à tous ; plus personne ne peut recocher la case par l'écran. Tant que `users.read`
  reste, un contournement existe par l'API seule (`createAccessRole` n'exige que
  `access_roles.write`, puis `setUserAccessRoles` sur soi). Dans l'autre ordre — décocher d'abord
  « consulter » de FBS-1.1 (`users.read`, l'écran des rôles marche encore), puis « consulter » de
  FBS-1.2 —, deux clics que la garde accepte l'un et l'autre suffisent : `updateAccessRole` et
  `setUserAccessRoles` répondent 404 à tous, et il ne reste que l'intervention en base, ce que le
  motif de WF-ADM-0120 veut éviter.
- **Vérifié** : `guard_last_administrator` (avant/après), `administrators()`, les quatre gardes de
  routes ; `test_access_roles_guard.py` n'éprouve que le retrait d'une permission de modifier.
  La lettre du Vérif de WF-ADM-0120 (« permissions de modifier ») est tenue : c'est son intention
  qui ne l'est pas.
- **Proposition** : compter comme administrateur le compte actif qui porte les quatre permissions
  que ses routes demandent (`users.read`, `users.write`, `access_roles.read`,
  `access_roles.write`) — ou, au choix de l'auteur, faire valoir la modification pour la
  consultation des fonctions FBS-1 dans `require` (WF-ADM-0100 : « la permission de modifier tient
  lieu de permission de gérer »). Coût : une constante et ses tests ; risque de ne rien faire : un
  clic de travers verrouille l'administration. Test : un seul administrateur, `updateAccessRole`
  qui retire `access_roles.read` (puis `users.read`) → 409 `LAST_ADMINISTRATOR`, rôle inchangé.
- **Confiance** : confirmé (lecture ; non exécuté).

## Constats mineurs

### BAC-03 — `undo`/`redo` disent si une révision d'un autre projet existe, et son état

- **Issue** : #4490 (EP-29), ouverte le 2026-11-21, avec BAC-04.
- **Où** : `backend/src/waterfall/core/planning/interface/snapshots.py:183` (`judge_revision` avant
  toute lecture bornée au projet) ; `backend/src/waterfall/core/planning/writing.py:139-155` ;
  `backend/src/waterfall/core/revisions/interface/revisions.py:621-636` (`revision_draft` lit et
  verrouille `FOR SHARE` la révision par son seul identifiant).
- **Quoi/scénario** : contributeur du projet A, `POST /projects/A/revisions/{X}/undo` : X inconnu →
  404 ; X brouillon d'un projet B qu'il ne peut pas consulter → 409 `undo_history_not_empty` ; X
  marquée dans B → 409 `revision_draft`. WF-ADM-0110 veut la même réponse pour l'inexistant et le
  non consultable. Les écritures ordinaires (`writing()`, `writing.py:342-344`) lisent d'abord la
  structure du projet (404) : seules `undoLastChange` et `redoLastUndo` ont l'ordre inverse.
  Exploitation faible (il faut un UUID), mais un verrou partagé est pris sur une ligne d'un projet
  étranger.
- **Proposition** : `revision_draft(session, project_id, revision_id)` filtre sur le projet (404
  sinon), ou `_turned` lit la révision du projet avant de la juger. Test : `undo` sur la révision
  d'un autre projet → 404.
- **Confiance** : confirmé (lecture).

### BAC-04 — Ce qui a été demandé avant un retrait de droits s'achève après

- **Issue** : #4490 (EP-29), ouverte le 2026-11-21, avec BAC-03.
- **Où** : `backend/src/waterfall/api/exports.py:107-135` et
  `backend/src/waterfall/core/exchanges/interface/exports.py:218-233` (le fichier d'un export se
  télécharge sous la seule qualité de demandeur) ; `backend/src/waterfall/worker/exchanges.py:51-62`
  avec `backend/src/waterfall/core/access_roles/evaluation.py:61-67` (le worker rejuge l'import par
  les permissions du demandeur, qui ne lisent pas l'état du compte) ; `worker/marking.py`
  (`run_marking` : le marquage ne rejuge ni la permission ni la qualité du demandeur).
- **Scénario** : un contributeur demande l'export d'une révision ; on le retire du projet (ou on
  lui retire tous ses rôles) ; il télécharge encore le fichier par `GET /tasks/{id}/result` jusqu'à
  son expiration. De même, un import confirmé par un compte désactivé avant que le worker ne le
  prenne est appliqué (les rôles d'un compte désactivé sont gardés, WF-ADM-0060).
- **Proposition** : `result_of` rejuge la consultation du projet de l'export (la tâche le nomme) ;
  `actor_of` du worker rend un acteur sans permission pour un compte désactivé. Test : export
  demandé, contributeur retiré, téléchargement → 404. À arbitrer : WF-ADM-0110 ne dit rien d'une
  action autorisée à sa demande et servie après.
- **Confiance** : confirmé pour le téléchargement et l'import (lecture) ; plausible pour le
  marquage (`run_marking` non lu en entier).

### BAC-05 — Avatar : validé sur sa seule signature, servi sans en-tête de protection ni de cache

- **Issue** : #4491 (EP-29), ouverte le 2026-11-21 pour ce qui en reste, une part étant corrigée
  depuis la revue.
- **Où** : `backend/src/waterfall/core/users/personal.py:36` et `:87-89` (`SIGNATURES` : huit octets
  pour PNG, **trois** pour JPEG) ; `backend/src/waterfall/api/avatars.py:48-74` (aucun décodage),
  `:101-110` (réponse sans `X-Content-Type-Options`, `Cache-Control`, `ETag` ni
  `Content-Disposition`) ; aucun intergiciel n'en pose (`api/middleware.py`).
- **Quoi** : tout fichier qui commence par `FF D8 FF` est gardé (jusqu'à 8 Mio) et resservi comme
  `image/jpeg` à toute session, compte sans rôle compris : contenu arbitraire derrière trois octets,
  métadonnées EXIF (position GPS) non retirées, et chaque affichage relit jusqu'à 8 Mio sans
  validateur de cache. Pas de SVG (refusé par la signature) : le risque de contenu actif repose sur
  le seul type de contenu. Pillow est déjà une dépendance du back (`backend/pyproject.toml:17`).
- **Proposition** : décoder l'image à la pose (Pillow, `verify()` puis réécriture sans métadonnées,
  bornée en dimensions) ; servir avec `X-Content-Type-Options: nosniff`,
  `Cache-Control: private` et un `ETag`. Test : un fichier « `FF D8 FF` + HTML » → 422 ; les
  en-têtes de `getUserAvatar`.
- **Confiance** : confirmé (lecture) ; l'effet dans un navigateur dépend du front, non relu.

### BAC-06 — Deux `VALUE_TOO_LONG` portent `maximum` au lieu de `max_length` (EP-18/US-1060)

- **Issue** : #4465 (EP-38), ouverte le 2026-11-21, avec CTA-04, CTA-05, CTA-06.
- **Où** : `backend/src/waterfall/core/exchanges/interface/imports.py:333` (nom de fichier d'un
  dépôt, `uploadFile`) ; `backend/src/waterfall/core/planning/interface/timelines.py:67` (libellé
  d'une chronologie — atteint par le seul chargeur du témoin si le modèle du contrat borne déjà le
  libellé, non vérifié).
- **Quoi** : `docs/api/components/common.yaml:368-369` et `:569` : « `max_length` … accompanies
  every `VALUE_TOO_LONG` » ; EP-18, Conception : « `max_length` sur tout `VALUE_TOO_LONG` ». Le
  refus du dépôt rend `params: {"maximum": …}`, que le front ne lit pas (`problemDetails`). Aucun
  test ne couvre un nom de fichier trop long (`grep VALUE_TOO_LONG backend/tests` : rien pour le
  dépôt).
- **Proposition** : `{"max_length": LONGEST_NAME}` aux deux endroits ; un test du dépôt d'un nom
  trop long qui affirme le paramètre.
- **Confiance** : confirmé pour le dépôt (lecture) ; plausible pour la chronologie.

### BAC-07 — L'extension Keycloak déclare l'adresse prouvée par un lien remis à la main

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — sans effet dans le produit livré :
  ni le royaume (`verifyEmail` absent), ni le back, ni le front ne lisent `emailVerified` ; la revue
  dit la portée « plausible », sous un réglage de console qu'aucune plateforme ne porte.
- **Où** : `deploy/keycloak/extension/src/main/java/io/github/waterfallproject/keycloak/PasswordSetupTokenHandler.java:119-120`
  (`user.setEmailVerified(true)`, « the link reached the address it was made for »).
- **Quoi** : le même jeton sert au lien envoyé par courriel (`invite`) et au lien rendu à
  l'appelant (`create`, puis remis « par un autre canal », WF-ADM-0140). Dans le second cas rien n'a
  atteint l'adresse : elle est pourtant marquée vérifiée. Sans effet dans le royaume livré
  (`verifyEmail` absent) ; elle compte dès qu'un administrateur raccorde un fournisseur externe
  avec rattachement par adresse vérifiée (WF-ADM-0180, console).
- **Proposition** : porter dans le jeton s'il part par courriel, et ne vérifier l'adresse que là ;
  test contre la plateforme (`test_keycloak_platform.py`) : `emailVerified` reste faux après un
  lien rendu, vrai après une invitation.
- **Confiance** : confirmé (lecture) ; portée plausible.

### BAC-08 — Lectures et écritures sous une permission voisine de celle de l'objet

- **Issue** : #3973 (EP-29), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où/quoi** :
  - `backend/src/waterfall/api/imports.py:94`, `:250`, `:311` : `listImports` et `getImport`
    demandent `planning.read` quel que soit le genre ; le compte rendu d'un import de devis, de
    reste à engager ou de coûts réels (`ImportView.report`,
    `core/exchanges/interface/imports.py:524-552`) se lit donc sans `estimate.read`,
    `remaining.read` ni `actual_costs.read`. Épinglé tel quel par `backend/tests/asked_imports.py:22-24` ;
    je n'ai pas trouvé de décision qui le dise.
  - `backend/src/waterfall/api/actual_costs.py:158-175` : `setActualCostTrackedScope` ne demande que
    `cost_line_exclude` (pas `actual_costs.read` d'abord) et rend la ligne entière ; et la qualité
    demandée est « contributeur » (`backend/tests/asked_actual_costs.py:18`), alors que
    WF-PRJ-0060 réserve aux chefs de projet « les actions structurantes du catalogue
    (WF-ADM-0100) », dont « exclure une ligne de coût » fait partie de l'énumération. EP-09 l'a
    conçu ainsi (`docs/roadmap/EP-09-…md:685`) sans dire pourquoi cette action-là échappe à la
    règle que `markRevision`, `abandonRevision`, `designateReferenceRevision` et `exitProject`
    suivent.
- **Proposition** : faire juger `getImport` par la permission de consultation du genre de l'import
  (404 sinon) et ne lister que les genres consultables ; pour l'exclusion, trancher à la
  spécification laquelle des actions « irréversibles ou structurantes » est réservée (le catalogue
  range `cost_line_exclude` sous `irreversible`, `migrations/versions/0005_permission_catalogue.py:57-66`,
  comme les quatre qui sont réservées).
- **Confiance** : plausible — la pièce manquante est une décision (contrat ou spec), pas le code.

### BAC-09 — `uploadFile` : toute session, sans plafond par compte

- **Issue** : #4423 (EP-33), ouverte le 2026-11-21, avec CTB-02.
- **Où** : `backend/src/waterfall/api/imports.py:149-183`,
  `backend/src/waterfall/core/exchanges/interface/imports.py:318-334`.
- **Quoi/scénario** : un compte sans aucun rôle (première connexion d'une personne d'un fournisseur
  externe, WF-ADM-0180 : « aucun droit ») dépose autant de fichiers de 10 Mio qu'il veut, gardés
  vingt-quatre heures sur le stockage des sauvegardes (`services.backups`) : il peut le remplir, et
  faire échouer les sauvegardes. Aucun import ne s'ouvre sans permission : le dépôt seul est ouvert.
- **Proposition** : demander l'une des permissions d'import (comme `one_of`) ou borner les dépôts
  non employés par compte ; test : un compte sans rôle → 403.
- **Confiance** : confirmé pour l'absence de permission et de plafond (lecture) ; l'effet sur le
  stockage est plausible (quotas du seau non relus, EP-13).

### BAC-10 — Tests de sécurité qui ne citent pas d'exigence, et un test sans assertion

- **Issue** : #4451 (EP-36), ouverte le 2026-11-21, avec BRC-10, FCO-13, FAR-05.
- **Où** : `backend/tests/test_users_activation.py:276` (#834 : « qui modifie les comptes ne se
  donne pas l'administration », Vérif de WF-ADM-0090, aucun marqueur) ;
  `backend/tests/test_users_password_link.py:210` (permission du lien, WF-ADM-0110) ;
  `backend/tests/test_access_evaluation.py:338` (refus nommé, WF-ADM-0110) ;
  `backend/tests/test_access_evaluation.py:828` (cite WF-REF-0150 mais n'affirme rien : il passe si
  l'appel ne lève pas).
- **Quoi** : le guide (« Un test qui cite son exigence ») dispense un test d'outil ou de détail ;
  ceux-ci éprouvent un Vérif. Décompte heuristique (script, décorateurs lus sur les lignes qui
  précèdent) : environ la moitié des tests des fichiers `test_users_*`, `test_access_*`,
  `test_audit_*` n'ont pas de marqueur — beaucoup à bon droit (tri, pagination, verrous).
- **Proposition** : marquer ces trois tests ; donner au quatrième une assertion explicite.
- **Confiance** : confirmé pour les quatre cités ; le décompte est indicatif.

### Déjà connus, pour mémoire

- `startBackup` ne rend pas le 409 `no_backup_running` / `no_restore_running` du contrat
  (`backend/src/waterfall/api/backups.py:129-133`) — déjà connu (#1035, EP-13).
- `AuditProject.can_open` toujours faux (`backend/src/waterfall/api/audit.py:106-111`) — écart de
  WF-ADM-0190 porté par EP-13 (`EP-03…md:131`, `:1654`).
- Compte local réactivé entre le retrait de Keycloak et l'anonymisation
  (`backend/src/waterfall/api/users.py:616-637`) — décrit dans le code, renvoyé à #868.

## Points forts

- **Évaluation** : permissions lues à chaque requête (`api/evaluation.py:36-43`), aucun cache ;
  consultation manquante = 404, autre = 403 nommé, décidé par le catalogue (`CONSULTATION`) et non
  par le suffixe ; projet inexistant et projet non consultable indistincts (`judge_project`).
- **Couverture** : chaque route déclare ses permissions, et `test_access_evaluation.py` compare la
  déclaration de chaque route servie à `ASKED`/`ON_PROJECT` et au refus que le contrat déclare ; pas
  de route d'écriture sans garde.
- **Périmètre projet** : `project_id` du chemin est repassé à chaque lecture du noyau sondée
  (`found_import`, `structure_facts`, `delete_timeline`, `set_scope`, `read_revision_for`,
  `_locked` des sous-projets) ; dépôts, tâches, plans de collage et piles d'annulation sont ceux de
  l'appelant seul (`_usable_deposit`, `read_task`, `read_plan`, `UndoStack`).
- **Concurrence** : `lock_version` testé dans l'`UPDATE` (`change_columns`, `update_role`) ; verrou
  consultatif unique de la règle du dernier administrateur pris avant toute ligne de compte, par
  les routes comme par la lecture des comptes ; attribution et suppression d'un rôle sérialisées.
- **Cycle de vie** : la lecture des comptes ne réactive ni ne renomme un compte désactivé ou
  anonymisé, revérifie un par un les comptes « disparus » avant de les désactiver
  (`worker/identity_sync.py:111-115`), garde le dernier administrateur ; adresse unique par index
  sur `lower(email)`, création concurrente par `ON CONFLICT`.
- **Révocation** : `sessions_closed_at` noté avant l'appel à Keycloak, jeton d'une connexion
  antérieure refusé même rafraîchi.
- **Journal** : inscription dans la transaction de l'action, champs « secrets » refusés, noms hors
  de `params` (seuls identifiants et libellés de rôles), oubli du nom limité aux deux colonnes.
- **Extension Java** : authentifie, autorise, puis lit ; refus en codes ; nonce en base ; un test
  de plateforme par refus (`test_keycloak_platform.py`). Aucun commentaire d'exemption dans le
  périmètre (`noqa`, `type: ignore`, `xfail`, `@SuppressWarnings` : aucun).

## Tableau des routes (132) — authentification et habilitation

Engendré par script depuis les décorateurs (`dependencies=`) de `backend/src/waterfall/api/*.py`,
constantes résolues. « PROJET : » = `RequiresProject` (existence + contributeur ou
`all_projects_read`, puis les permissions, une écriture demandant la qualité de contributeur ;
« chef de projet » = `manager=True`). « session seule » = `Caller` sans permission.

| Route (`api/…:ligne`) | Opération | Auth. | Habilitation vérifiée |
|---|---|---|---|
| `GET /permissions` (`access_roles.py:83`) | `listPermissions` | oui | session seule |
| `GET /access-roles` (`access_roles.py:144`) | `listAccessRoles` | oui | access_roles.read |
| `GET /access-roles/{access_role_id}` (`access_roles.py:161`) | `getAccessRole` | oui | access_roles.read |
| `POST /access-roles` (`access_roles.py:177`) | `createAccessRole` | oui | access_roles.write |
| `PATCH /access-roles/{access_role_id}` (`access_roles.py:188`) | `updateAccessRole` | oui | access_roles.read + access_roles.write |
| `DELETE /access-roles/{access_role_id}` (`access_roles.py:203`) | `deleteAccessRole` | oui | access_roles.read + access_roles.write |
| `GET /reference/actual-cost-mapping` (`actual_cost_mapping.py:62`) | `getActualCostMapping` | oui | cost_settings.read |
| `PUT /reference/actual-cost-mapping` (`actual_cost_mapping.py:73`) | `setActualCostMapping` | oui | cost_settings.write |
| `GET /projects/{project_id}/actual-costs` (`actual_costs.py:118`) | `listActualCosts` | oui | PROJET : actual_costs.read |
| `PUT /projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope` (`actual_costs.py:158`) | `setActualCostTrackedScope` | oui | PROJET : cost_line_exclude |
| `GET /audit-events` (`audit.py:162`) | `listAuditEvents` | oui | audit_log.read |
| `GET /audit-events/facets` (`audit.py:200`) | `listAuditFacets` | oui | audit_log.read |
| `PUT /me/avatar` (`avatars.py:77`) | `putMyAvatar` | oui | session seule |
| `DELETE /me/avatar` (`avatars.py:89`) | `deleteMyAvatar` | oui | session seule |
| `GET /users/{user_id}/avatar` (`avatars.py:101`) | `getUserAvatar` | oui | session seule |
| `GET /backups` (`backups.py:107`) | `listBackups` | oui | backups.read |
| `POST /backups` (`backups.py:129`) | `startBackup` | oui | backups.write |
| `GET /backups/{backup_id}` (`backups.py:136`) | `getBackup` | oui | backups.read |
| `GET /backups/{backup_id}/content` (`backups.py:142`) | `downloadBackup` | oui | backups.read + backups.write |
| `GET /reference/calendars` (`calendars.py:214`) | `listCalendars` | oui | session seule (aucune permission) ; désactivés : resource_settings.write |
| `POST /reference/calendars` (`calendars.py:240`) | `createCalendar` | oui | resource_settings.write |
| `PATCH /reference/calendars/{calendar_id}` (`calendars.py:252`) | `updateCalendar` | oui | resource_settings.write |
| `PUT /reference/calendars/{calendar_id}/default` (`calendars.py:267`) | `setDefaultCalendar` | oui | resource_settings.write |
| `PUT /reference/calendars/{calendar_id}/activation` (`calendars.py:282`) | `setCalendarActivation` | oui | resource_settings.write |
| `GET /reference/duration-units` (`calendars.py:299`) | `getDurationUnits` | oui | session seule (aucune permission) |
| `PUT /reference/duration-units` (`calendars.py:311`) | `setDurationUnits` | oui | resource_settings.write |
| `GET /projects/{project_id}/revisions/comparison` (`comparison.py:84`) | `compareRevisions` | oui | PROJET : estimate.read |
| `GET /projects/{project_id}/contributors` (`contributors.py:139`) | `listContributors` | oui | PROJET : project_settings.read |
| `PUT /projects/{project_id}/contributors` (`contributors.py:154`) | `setContributors` | oui | PROJET : project_settings.read + project_settings.write ; chef de projet (ou secours) |
| `GET /projects/{project_id}/contributors/suggestions` (`contributors.py:171`) | `listContributorSuggestions` | oui | PROJET : project_settings.read |
| `GET /projects/{project_id}/cost-imports` (`cost_imports.py:54`) | `listCostImports` | oui | PROJET : actual_costs.read |
| `GET /reference/cost-types` (`cost_types.py:213`) | `listCostTypes` | oui | session seule (aucune permission) ; désactivés : cost_settings.write |
| `POST /reference/cost-types` (`cost_types.py:238`) | `createCostType` | oui | cost_settings.write |
| `PATCH /reference/cost-types/{cost_type_id}` (`cost_types.py:250`) | `updateCostType` | oui | cost_settings.write |
| `PUT /reference/cost-types/{cost_type_id}/activation` (`cost_types.py:265`) | `setCostTypeActivation` | oui | cost_settings.write |
| `GET /reference/cost-categories` (`cost_types.py:287`) | `listCostCategories` | oui | session seule (aucune permission) ; désactivés : cost_settings.write |
| `POST /reference/cost-categories` (`cost_types.py:315`) | `createCostCategory` | oui | cost_settings.write |
| `PATCH /reference/cost-categories/{cost_category_id}` (`cost_types.py:327`) | `updateCostCategory` | oui | cost_settings.write |
| `PUT /reference/cost-categories/{cost_category_id}/activation` (`cost_types.py:343`) | `setCostCategoryActivation` | oui | cost_settings.write |
| `GET /projects/{project_id}/estimate-indicators` (`estimate_indicators.py:101`) | `getEstimateIndicators` | oui | PROJET : estimate.read |
| `GET /projects/{project_id}/estimate-indicators/missing-rates` (`estimate_indicators.py:118`) | `getMissingRates` | oui | PROJET : estimate.read |
| `PATCH …/structures/{structure_id}/nodes/{node_id}/estimate-line` (`estimate_lines.py:56`) | `updateEstimateLine` | oui | PROJET : estimate.read + estimate.write |
| `POST /projects/{project_id}/exports` (`exports.py:73`) | `requestExport` | oui | PROJET : (aucune) |
| `GET /tasks/{task_id}/result` (`exports.py:107`) | `getBackgroundTaskResult` | oui | session seule |
| `POST …/structures/{structure_id}/nodes/paste-preview` (`history.py:77`) | `previewPaste` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `POST …/structures/{structure_id}/nodes/paste` (`history.py:101`) | `applyPaste` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `POST /projects/{project_id}/revisions/{revision_id}/undo` (`history.py:119`) | `undoLastChange` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `POST /projects/{project_id}/revisions/{revision_id}/redo` (`history.py:133`) | `redoLastUndo` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `GET /reference/hourly-rates` (`hourly_rates.py:151`) | `getHourlyRateGrid` | oui | cost_settings.read ; désactivés : cost_settings.write |
| `GET /reference/cost-categories/{cost_category_id}/hourly-rates` (`hourly_rates.py:184`) | `listHourlyRates` | oui | cost_settings.read |
| `PUT /reference/cost-categories/{cost_category_id}/hourly-rates/{year}` (`hourly_rates.py:195`) | `setHourlyRate` | oui | cost_settings.write |
| `POST /identity-syncs` (`identity_syncs.py:43`) | `startIdentitySync` | oui | users.write |
| `GET /identity-syncs/latest` (`identity_syncs.py:56`) | `getLatestIdentitySync` | oui | users.read |
| `POST /file-uploads` (`imports.py:149`) | `uploadFile` | oui | session seule |
| `GET /projects/{project_id}/imports` (`imports.py:250`) | `listImports` | oui | PROJET : planning.read |
| `POST /projects/{project_id}/imports` (`imports.py:275`) | `openImport` | oui | PROJET : planning.read |
| `GET /projects/{project_id}/imports/{import_id}` (`imports.py:311`) | `getImport` | oui | PROJET : planning.read |
| `DELETE /projects/{project_id}/imports/{import_id}` (`imports.py:320`) | `abandonImport` | oui | PROJET : planning.read |
| `POST /projects/{project_id}/imports/{import_id}/apply` (`imports.py:335`) | `applyImport` | oui | PROJET : planning.read |
| `PUT /projects/{project_id}/imports/{import_id}/duration-rule` (`imports.py:368`) | `setImportDurationRule` | oui | PROJET : planning.read |
| `GET /projects/{project_id}/next-state` (`lifecycle.py:94`) | `getProjectNextState` | oui | PROJET : lifecycle.read |
| `GET /projects/{project_id}/state-transitions` (`lifecycle.py:113`) | `listProjectStateTransitions` | oui | PROJET : lifecycle.read |
| `POST /projects/{project_id}/exit` (`lifecycle.py:173`) | `exitProject` | oui | PROJET : lifecycle.read + project_exit ; chef de projet |
| `PUT /projects/{project_id}/reference-revision` (`lifecycle.py:254`) | `designateReferenceRevision` | oui | PROJET : lifecycle.read + reference_designate ; chef de projet |
| `GET /me` (`me.py:75`) | `getMe` | oui | session seule |
| `PATCH /me/preferences` (`me.py:116`) | `updateMyPreferences` | oui | session seule |
| `DELETE /me/sessions` (`me.py:147`) | `closeMySessions` | oui | session seule |
| `GET …/structures/{structure_id}/nodes` (`nodes.py:650`) | `listNodes` | oui | PROJET : planning.read |
| `POST …/structures/{structure_id}/nodes` (`nodes.py:680`) | `createNode` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `PATCH …/structures/{structure_id}/nodes/{node_id}/task` (`nodes.py:718`) | `updateTaskFacet` | oui | PROJET : planning.read + planning.write |
| `DELETE …/structures/{structure_id}/nodes/{node_id}` (`nodes.py:745`) | `deleteNode` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `POST …/structures/{structure_id}/nodes/move` (`nodes.py:762`) | `moveNodes` | oui | PROJET : planning.read + une de {planning.write, estimate.write, remaining.write} |
| `GET …/structures/{structure_id}/nodes/{node_id}/dependencies` (`nodes.py:785`) | `getComputedValueDependencies` | oui | PROJET : planning.read |
| `GET …/structures/{structure_id}/rows/{row_number}` (`nodes.py:812`) | `resolveRowNumber` | oui | PROJET : planning.read |
| `GET /reference/org-nodes` (`org_nodes.py:146`) | `listOrgNodes` | oui | session seule (aucune permission) ; désactivés : resource_settings.write |
| `POST /reference/org-nodes` (`org_nodes.py:164`) | `createOrgNode` | oui | resource_settings.write |
| `PATCH /reference/org-nodes/{org_node_id}` (`org_nodes.py:178`) | `updateOrgNode` | oui | resource_settings.write |
| `PUT /reference/org-nodes/{org_node_id}/activation` (`org_nodes.py:195`) | `setOrgNodeActivation` | oui | resource_settings.write |
| `PUT …/structures/{structure_id}/nodes/{node_id}/progress` (`progress.py:36`) | `setTaskProgress` | oui | PROJET : remaining.read + remaining.write |
| `GET /projects` (`projects.py:231`) | `listProjects` | oui | project_settings.read |
| `POST /projects` (`projects.py:258`) | `createProject` | oui | project_create |
| `GET /projects/{project_id}` (`projects.py:278`) | `getProject` | oui | PROJET : project_settings.read |
| `PATCH /projects/{project_id}` (`projects.py:319`) | `updateProject` | oui | PROJET : project_settings.read + project_settings.write ; chef de projet |
| `GET /projects/{project_id}/revisions/{revision_id}/rate-update` (`rate_update.py:42`) | `getRateUpdateProposal` | oui | PROJET : revisions.read |
| `POST /projects/{project_id}/revisions/{revision_id}/rate-update` (`rate_update.py:66`) | `applyRateUpdate` | oui | PROJET : revisions.read + revisions.write |
| `GET /reference/readiness` (`reference.py:27`) | `getReferenceReadiness` | oui | session seule (aucune permission) |
| `GET /reference/settings` (`reference_settings.py:85`) | `getReferenceSettings` | oui | session seule (aucune permission) |
| `PATCH /reference/settings` (`reference_settings.py:97`) | `updateReferenceSettings` | oui | session seule (aucune permission) ; par champ écrit |
| `GET /projects/{project_id}/remaining-indicators` (`remaining_indicators.py:107`) | `getRemainingIndicators` | oui | PROJET : remaining.read |
| `PUT …/structures/{structure_id}/nodes/{node_id}/remaining` (`remaining_lines.py:82`) | `setLineRemaining` | oui | PROJET : remaining.read + remaining.write |
| `GET /reference/resource-roles` (`resource_roles.py:286`) | `listResourceRoles` | oui | session seule (aucune permission) ; désactivés : resource_settings.write |
| `POST /reference/resource-roles` (`resource_roles.py:318`) | `createResourceRole` | oui | resource_settings.write |
| `PATCH /reference/resource-roles/{resource_role_id}` (`resource_roles.py:340`) | `updateResourceRole` | oui | resource_settings.write |
| `PUT /reference/resource-roles/{resource_role_id}/activation` (`resource_roles.py:368`) | `setResourceRoleActivation` | oui | resource_settings.write |
| `POST /restores` (`restores.py:61`) | `startRestore` | oui | platform_restore |
| `GET /projects/{project_id}/revisions` (`revisions.py:269`) | `listRevisions` | oui | PROJET : revisions.read |
| `POST /projects/{project_id}/revisions` (`revisions.py:293`) | `createRevision` | oui | PROJET : revisions.read + revisions.write |
| `GET /projects/{project_id}/revisions/{revision_id}` (`revisions.py:314`) | `getRevision` | oui | PROJET : revisions.read |
| `DELETE /projects/{project_id}/revisions/{revision_id}` (`revisions.py:335`) | `abandonRevision` | oui | PROJET : revisions.read + revision_abandon ; chef de projet |
| `POST /projects/{project_id}/revisions/{revision_id}/mark` (`revisions.py:365`) | `markRevision` | oui | PROJET : revisions.read + revision_mark ; chef de projet |
| `GET /projects/{project_id}/revisions/{revision_id}/structures` (`revisions.py:387`) | `listCostStructures` | oui | PROJET : revisions.read |
| `PUT …/structures/{structure_id}/nodes/{node_id}/predecessors` (`scheduling.py:42`) | `setPredecessors` | oui | PROJET : planning.read + planning.write |
| `PATCH …/structures/{structure_id}` (`scheduling.py:72`) | `updateCostStructure` | oui | PROJET : planning.read + planning.write |
| `POST /projects/{project_id}/revisions/{revision_id}/skeleton` (`skeleton.py:33`) | `generatePlanningSkeleton` | oui | PROJET : planning.read + planning.write |
| `GET /projects/{project_id}/remaining-indicators/startable-tasks` (`startable_tasks.py:53`) | `listStartableTasks` | oui | PROJET : remaining.read |
| `GET /projects/{project_id}/subprojects` (`subprojects.py:152`) | `listSubprojects` | oui | PROJET : project_settings.read |
| `POST /projects/{project_id}/subprojects` (`subprojects.py:172`) | `createSubproject` | oui | PROJET : project_settings.read + project_settings.write ; chef de projet |
| `PATCH /projects/{project_id}/subprojects/{subproject_id}` (`subprojects.py:193`) | `updateSubproject` | oui | PROJET : project_settings.read + project_settings.write ; chef de projet |
| `DELETE /projects/{project_id}/subprojects/{subproject_id}` (`subprojects.py:215`) | `deleteSubproject` | oui | PROJET : project_settings.read + project_settings.write ; chef de projet |
| `GET /health` (`system.py:16`) | `getLiveness` | non | aucune (public) |
| `GET /installation` (`system.py:26`) | `getInstallation` | non | aucune (public) |
| `GET /tasks` (`tasks.py:72`) | `listBackgroundTasks` | oui | session seule |
| `GET /tasks/{task_id}` (`tasks.py:89`) | `getBackgroundTask` | oui | session seule |
| `GET /projects/{project_id}/timelines` (`timelines.py:64`) | `listTimelines` | oui | PROJET : planning.read |
| `POST /projects/{project_id}/timelines` (`timelines.py:76`) | `createTimeline` | oui | PROJET : planning.read + planning.write |
| `DELETE /projects/{project_id}/timelines/{timeline_id}` (`timelines.py:90`) | `deleteTimeline` | oui | PROJET : planning.read + planning.write |
| `PUT …/structures/{structure_id}/nodes/{node_id}/tracking` (`timelines.py:102`) | `setNodeTracking` | oui | PROJET : planning.read + planning.write |
| `POST /chunked-uploads` (`uploads.py:77`) | `openChunkedUpload` | oui | platform_restore |
| `PUT /chunked-uploads/{chunked_upload_id}/parts/{part_number}` (`uploads.py:130`) | `uploadChunk` | oui | platform_restore |
| `POST /chunked-uploads/{chunked_upload_id}/completion` (`uploads.py:182`) | `completeChunkedUpload` | oui | platform_restore |
| `GET /users` (`users.py:313`) | `listUsers` | oui | users.read |
| `GET /users/{user_id}` (`users.py:338`) | `getUser` | oui | users.read |
| `POST /users` (`users.py:389`) | `createUser` | oui | users.write |
| `PATCH /users/{user_id}` (`users.py:473`) | `updateUser` | oui | users.read + users.write |
| `PUT /users/{user_id}/activation` (`users.py:568`) | `setUserActivation` | oui | users.read + users.write |
| `POST /users/{user_id}/anonymization` (`users.py:609`) | `anonymizeUser` | oui | users.read + users.write |
| `PUT /users/{user_id}/access-roles` (`users.py:646`) | `setUserAccessRoles` | oui | users.read + users.write + access_roles.write |
| `POST /users/{user_id}/password-link` (`users.py:678`) | `createPasswordSetupLink` | oui | users.read + users.write |
| `POST /users/{user_id}/invitation` (`users.py:707`) | `resendInvitation` | oui | users.read + users.write |
| `GET /projects/{project_id}/work-breakdown` (`work_breakdown.py:141`) | `getWorkBreakdown` | oui | PROJET : project_settings.read |
| `PUT /projects/{project_id}/work-breakdown` (`work_breakdown.py:156`) | `setWorkBreakdown` | oui | PROJET : project_settings.read + project_settings.write ; chef de projet |
| `GET /projects/{project_id}/workload` (`workload.py:90`) | `getProjectWorkload` | oui | PROJET : estimate.read |

Lecture du tableau, par famille :

- **Publiques (2)** : `getLiveness`, `getInstallation` (langue par défaut et deux bornes) — voulu.
- **Session seule (13)** : `getMe`, préférences, avatar (le sien), `closeMySessions`,
  `listPermissions`, `getUserAvatar` (tout avatar, à toute session : WF-ADM-0080), tâches (celles
  de l'appelant, `read_task(…, account.user_id)`), `getBackgroundTaskResult` (BAC-04), `uploadFile`
  (BAC-09).
- **Référentiel lu par toute session (8)** : décision du 2026-11-01 (`DECISIONS.md:10450-10460`) ;
  les désactivés sous la permission de modifier (`RequiresForInactive`).
- **`requestExport`** : la route ne demande que la consultation du projet ; la permission du genre
  est jugée par la commande `export_*` (`request_export`), non relue en détail.
- **Imports** : la route ne demande que `planning.read` ; l'écriture est jugée dans le noyau, sous
  le verrou, par la permission du genre et la qualité de contributeur
  (`core/exchanges/interface/imports.py:435`, `:604`, `:659`, `:710`) — vérifié.
- **Dix routes sensibles comparées à la spécification** : `createUser`, `setUserActivation`,
  `anonymizeUser` (FBS-1.1, `users.write`, WF-ADM-0060) ✓ ; `setUserAccessRoles` (FBS-1.2,
  WF-ADM-0090) ✓ ; `updateAccessRole`/`deleteAccessRole` ✓ ; `listAuditEvents` (seule
  `audit_log.read`, WF-ADM-0190) ✓ ; `startRestore` (`platform_restore`) ✓ ; `markRevision`,
  `designateReferenceRevision`, `exitProject` (permission propre + chef de projet, WF-PRJ-0060) ✓ ;
  `setContributors` (chef de projet, ou secours sous `project_settings.write` +
  `all_projects_read`, WF-PRJ-0060) ✓ ; `createPasswordSetupLink` ✗ (BAC-01) ;
  `setActualCostTrackedScope` ? (BAC-08).

## Couverture

- **Lu en entier** : `backend/src/waterfall/core/access_roles/` (les 8 fichiers) ;
  `core/users/` : `accounts.py`, `commands.py`, `identity.py`, `listing.py`, `password_link.py`,
  `personal.py`, `provider.py`, `states.py`, `tables.py`, `interface.py` (hors la liste `__all__`) ;
  `core/history/` : `stacks.py`, `snapshots.py`, `interface/undo.py`, `interface/recording.py`,
  `interface/plans.py`, `interface/purge.py`, `interface/closing.py` ; `api/users.py`,
  `access_roles.py`, `evaluation.py`, `authentication.py`, `me.py`, `avatars.py`,
  `identity_syncs.py`, `audit.py`, `history.py`, `resource_role_admission.py`, `system.py`,
  `tasks.py`, `exports.py`, `imports.py`, `middleware.py`, `maintenance.py`, `app.py` ;
  `worker/identity_sync.py` ; l'extension Java : `PasswordSetupLinkResource`,
  `PasswordSetupTokenHandler`, `ResetCredentialsTokenHandler`, `PasswordSetupToken`, les deux
  règles de politique, `PasswordSetupLinkProviderFactory` ; `platform/audit_consultation.py`,
  `platform/audit.py` (table, `record`, `forget_account`).
- **Échantillonné** : `core/backups/interface.py` (lu, la restauration elle-même —
  `platform/restoration.py`, `waterfall.restore` — non) ; `core/history/tables.py`,
  `core/history/interface/__init__.py` ; `api/backups.py`, `restores.py`, `uploads.py`,
  `contributors.py`, `projects.py`, `nodes.py`, `timelines.py`, `actual_costs.py`,
  `rate_update.py`, `estimate_indicators.py`, `remaining_indicators.py` (gardes et passage de
  `project_id`) ; les 132 routes par script, puis une quinzaine de fonctions du noyau pour le
  périmètre projet ; `platform/keycloak.py` (`validate`), `platform/keycloak_admin.py`
  (`make_password_link`, `send_invitation`, jeton de service) ; tests : noms et marqueurs par
  script sur 30 fichiers, lecture partielle de `test_access_evaluation.py`,
  `test_access_roles_guard.py`, `test_users_activation.py`, `test_users_password_link.py`,
  `test_keycloak_platform.py` (titres) ; spécification : WF-ADM-0010 à 0190 en entier,
  WF-SEC-0020, WF-SEC-0030, WF-PRJ-0060 ; contrat : `access.yaml` (lien, synchronisation),
  `platform.yaml` (`startBackup`), `common.yaml` (`VALUE_TOO_LONG`) ; EP-03, Conception :
  « Authentification et session » et « Journal d'audit » ; EP-18 : « Constats reçus » et
  Conception en entier ; `DECISIONS.md` : #834, #1732, lectures du référentiel.
- **Non lu** : `core/backups/tables.py` ; `core/users/__init__.py` et consorts (trois lignes) ;
  les fabriques des deux règles de politique Java et les quatre tests JUnit ; EP-03, Conception :
  « Tables et migrations », « Modules », « Worker », « Amorçage », « Sauvegarde et restauration »,
  « Décisions » (seulement par recherche) ; EP-23 et EP-24 (titres seulement) ; `me.yaml`,
  `audit.yaml` ; WF-SEC-0010 ; le front (hors un `grep` de l'écran des rôles) ; le détail de
  `request_export`, `run_marking`, `run_export`. Aucun test, lint ni typage n'a été lancé.

# Revue — contrat d'API : socle commun, administration et référentiel (familles access, me, platform, system, audit, reference)

## Synthèse

Le contrat de ce périmètre est mécaniquement très propre : les 3 915 `$ref` du contrat se résolvent,
aucun `required` ne nomme une propriété absente, les 637 exemples des six familles valident leur
schéma, les 367 enveloppes d'erreur des fixtures suivent les conventions (`missing_condition`,
`missing_permission`, `expected_lock_version` seul, `max_length`, `state`/`state_enum`), et chaque
écriture porte les statuts que ses voisines portent (403, 404, 412, 422 ; `lock_version` partout où
il est dû, exceptions décidées). Les exigences WF-ADM, WF-SEC et WF-REF lues à leur ligne sont
exprimables, et la plupart des écarts que j'ai cru voir (capacité d'un rôle, motifs des graphiques,
planification des sauvegardes non servie) sont déjà planifiés ou dus par un EPIC non livré.

Ce qui inquiète tient au **modèle des habilitations**, pas à la forme : deux défauts de conception que
le contrat écrit noir sur blanc et que le service suit fidèlement. (1) Le porteur de la seule
`users.write` — celui-là même que deux décisions (#834, #1731) ont voulu empêcher de se donner
l'administration — obtient le lien qui réinitialise le mot de passe de n'importe quel compte local
actif, administrateur compris. (2) La garde du dernier administrateur ne compte que les deux
permissions de modifier, alors que le contrat rend ces écritures inatteignables (404) sans les deux
permissions de consulter : deux cases décochées dans la matrice des rôles ferment l'administration
sans retour par l'API. S'y ajoute un trou de rattachement : la périodicité de la lecture des comptes,
au contrat et à l'écran, n'est servie ni due par personne alors que WF-ADM-0070 est close. Le reste
est mineur : typage incomplet de l'enveloppe d'erreur, deux composants morts que le lint ne peut pas
voir, quelques refus servis que le contrat ne dit pas.

Aucun bloquant. 3 majeurs, 9 mineurs (dont 1 déjà connu).

## Constats bloquants

Aucun.

## Constats majeurs

### CTA-01 — `users.write` seule suffit à prendre le compte d'un administrateur local

- **Issue** : #3342.
- **Où** : `docs/api/paths/access.yaml:514-530` (`createPasswordSetupLink`, « Under the permission to
  modify accounts (`users.write`) », l. 527-528), `:564-582` (`resendInvitation`, l. 576),
  `:268-275` (`updateUser`, l'adresse d'un compte local se modifie) ;
  `docs/api/components/schemas/access.yaml:96-118` (`UserCommand` : les deux commandes « fall under
  the permission to modify accounts ») ; décision `docs/api/DECISIONS.md:1527-1534` (#388, « Sous
  `users.write` »). Opérations **servies** : `backend/src/waterfall/api/users.py:133` (`WRITE` =
  `users.read` + `users.write`), `:672-699`, `:701-735` ; `core/users/commands.py:66-68,103-108`
  (« for the sole permission to change the accounts »).
- **Quoi** : le lien de fixation « fixe ou réinitialise » le mot de passe de tout compte local actif,
  et il est rendu à l'appelant sous la seule `users.write`, sans égard aux rôles du compte visé — le
  contrat rouvre l'élévation que `setUserAccessRoles` (#834, `DECISIONS.md:6248-6258`) et `createUser`
  (A-01, #1731, `DECISIONS.md:10318-10345`, « une élévation de privilège ») ont fermée.
- **Scénario** : un rôle composé « gestion des comptes » porte `users.read` et `users.write`, sans
  `access_roles.write` (le découpage que la décision #834 protège). Son porteur appelle
  `POST /users/{id de l'administrateur}/password-link` : 201, l'URL lui est rendue (le lien précédent
  cesse de valoir). Il l'ouvre, fixe un mot de passe — l'extension Keycloak ajoute `UPDATE_PASSWORD`
  sans demander l'ancien (`deploy/keycloak/extension/.../PasswordSetupLinkResource.java:86-96` : seul
  le lien d'installation refuse un compte qui a déjà un mot de passe ;
  `PasswordSetupTokenHandler.java:117`) — et se connecte comme administrateur. Variante sans lien
  rendu : `PATCH /users/{id}` change l'adresse du compte local administrateur pour une adresse qu'il
  lit, puis `POST /users/{id}/invitation` y envoie le courriel de réinitialisation. Variante sur un
  compte dormant : `setUserActivation` réactive un ancien administrateur local (« se connecte de
  nouveau avec ses rôles d'avant »), puis le lien. Le compte de l'amorçage est local (WF-EXP-0020),
  donc toute installation a une cible. Seule trace : l'inscription `password_link_create`.
- **Vérifié** : la description des trois opérations, la liste des commandes, les gardes du service,
  l'extension Keycloak ; aucun rôle prédéfini ne porte `users.write` sans `access_roles.write`
  (`fixtures/api/access_roles.json`), il faut donc un rôle composé — exactement l'hypothèse de #834.
  Recherché dans `docs/roadmap/` et `DECISIONS.md` (« élévation », « lien de fixation ») : non relevé.
- **Proposition** : exiger `access_roles.write` en plus de `users.write` pour `createPasswordSetupLink`,
  `resendInvitation` et le changement de `/email` par `updateUser` dès que le compte visé porte un
  rôle (un compte sans rôle, celui qu'on vient de créer, reste invitable sous `users.write` seule) ;
  403 `PERMISSION_MISSING`, `missing_permission` à `access_roles.write` — le 403 est déjà déclaré sur
  les trois, seule la description change, et `create_password_link`/`resend_invitation` ne se listent
  alors que pour qui porte les deux. WF-ADM-0140 dit « un utilisateur habilité » sans nommer la
  permission : aucune révision de la spécification n'est nécessaire. Test : un appelant
  `users.read`+`users.write` reçoit 403 sur le lien d'un compte porteur du rôle Administrateur, 201
  sur celui d'un compte sans rôle ; idem pour l'invitation et pour `PATCH {email}`.
- **Confiance** : confirmé (contrat, service et extension lus ; non rejoué contre un Keycloak).

### CTA-02 — La garde du dernier administrateur laisse fermer l'administration : elle ignore les permissions de consulter que le contrat exige pour écrire

- **Issue** : #3342 (EP-29), à laquelle la ventilation du 2026-11-21 joint ce constat.
- **Où** : `docs/api/components/schemas/access.yaml:109-118` (`UserCommand` : « the last active
  account that holds both the permissions to modify accounts and access roles (`users.write`,
  `access_roles.write`) ») ; `docs/api/paths/access.yaml:488-493` (409 de `setUserAccessRoles`),
  `:1001-1006` (409 d'`updateAccessRole`) ; et la règle inverse, `:976-979` et `:1024-1026`
  (« on a role the caller can consult (`access_roles.read`): 404 without it »),
  `docs/api/README-fr.md:52`. Opérations **servies** :
  `backend/src/waterfall/core/access_roles/administrators.py:33,44-56` (`ADMINISTRATION =
  ("users.write", "access_roles.write")`), `api/users.py:133-134` (toute écriture d'un compte exige
  `users.read`, 404 sinon), `api/access_roles.py:57-59` (modifier ou supprimer un rôle exige
  `access_roles.read`), `core/access_roles/evaluation.py:124-134` (aucune permission de modifier
  n'emporte celle de consulter).
- **Quoi** : WF-ADM-0120 veut qu'un compte actif puisse toujours administrer comptes et rôles ; le
  contrat ne protège que les deux `.write`, qu'il rend lui-même inopérantes sans les deux `.read`.
- **Scénario** : installation dont les administrateurs ne portent que le rôle « Administrateur ». L'un
  d'eux, dans la matrice des rôles (une case = un `updateAccessRole`, sans couplage lecture/écriture,
  `frontend/src/components/admin/permission-matrix.tsx:180-186`), décoche `users.read` puis
  `access_roles.read` de ce rôle. Les deux `PATCH` passent : la garde voit toujours un porteur des
  deux `.write`. Dès lors, pour tous : `listUsers`, `getUser`, `setUserAccessRoles`,
  `updateAccessRole`, `listAccessRoles` répondent 404. `createAccessRole` et `createUser` répondent
  encore (ils n'exigent que la permission de modifier), mais un rôle neuf ne peut être attribué à
  personne (`setUserAccessRoles` exige `users.read`) et un compte neuf naît sans rôle. Aucun appel ne
  rend l'administration : il faut intervenir en base. Avec la seule `access_roles.read` retirée,
  l'écran des rôles et l'attribution sont déjà hors d'atteinte de l'interface (la reprise n'existe
  que par appels directs : créer un rôle, se l'attribuer par son identifiant).
- **Vérifié** : la garde (lue et sa requête), les dépendances des routes, `update_role`
  (`core/access_roles/roles.py:386-421` : aucune autre règle), l'absence de test sur une permission de
  consulter dans `backend/tests/test_access_roles_guard.py`, l'absence du sujet dans `DECISIONS.md` et
  `docs/roadmap/`. À noter : le référentiel fait l'inverse — ses écritures n'exigent que la permission
  de modifier (`api/org_nodes.py:51`, `calendars.py:76`, `cost_types.py:67`…), si bien que la relation
  entre « modifier » et « consulter » n'est pas la même d'une famille à l'autre.
- **Proposition** : dire au contrat qu'un administrateur est un compte actif qui porte les quatre
  permissions (`users.read`, `users.write`, `access_roles.read`, `access_roles.write`), et refuser par
  409 `LAST_ADMINISTRATOR` (ou `last_administrator` pour la désactivation) tout retrait de l'une des
  quatre au dernier ; descriptions de `UserCommand`, des deux 409 et de `CommandCondition` seulement —
  aucun schéma ne change, compatible avec le gel. Service : étendre `ADMINISTRATION`. Écarté : faire
  porter la consultation par la permission de modifier, qui change le sens des 404 partout. Test :
  rôle unique d'administration, `PATCH` qui retire `users.read` → 409 `LAST_ADMINISTRATOR`, rien
  d'écrit ; même refus par `setUserAccessRoles` vers un rôle qui n'a que les deux `.write`.
- **Confiance** : confirmé (chemin lu de bout en bout ; non rejoué, aucun test lancé).

### CTA-03 — `getIdentitySyncSchedule` et `setIdentitySyncSchedule` : au contrat et à l'écran, servies par personne, dues par aucun EPIC

- **Suite** : sans issue propre, vérifié le 2026-11-21 — tombera avec US-3040, issue #4065 (EP-13),
  lot unique ; dépend d'US-2910/L1 #4098 et d'US-2830/L2 #4079.
- **Où** : `docs/api/paths/access.yaml:708-776` ; `docs/api/components/schemas/platform.yaml:534-565`
  (`IdentitySyncSchedule`). **Non servies** : aucune route (`grep -rn "identity-sync-schedule"
  backend/src/waterfall` ne rend que le modèle engendré) ; la lecture planifiée est une commande
  d'exploitation (`backend/src/waterfall/worker/main.py:84,103`, `enqueue identity_sync`). Le front
  livré les appelle (`frontend/src/app/admin/users/page.tsx:174-175`,
  `components/admin/identity-sync-schedule.tsx`).
- **Quoi** : WF-ADM-0070 veut une lecture « selon une périodicité choisie par un utilisateur
  habilité » ; la décision A-02 du 2026-10-28 a ajouté les deux opérations en écartant expressément
  « un paramètre d'exploitation, contraire à "choisie par un utilisateur habilité" »
  (`docs/roadmap/EP-16-maquette-durcissement.md:939-941`). Or l'exigence est donnée close en EP-04
  (`EP-03-comptes-et-habilitations.md:107`, `EP-04-projets-et-revisions.md:94`), sur le constat que
  « la périodicité est celle de la tâche planifiée » (`EP-03…:1469-1470`), et aucun EPIC, livré ou à
  venir, ne liste ces deux opérations parmi celles qu'il sert (EP-13 en liste huit, sans elles :
  `EP-13-exploitation.md:104-107` ; `resendInvitation`, ajoutée le même jour, a été reprise par
  EP-18). Le Vérif tient ; le corps, non.
- **Scénario** : un administrateur ouvre l'écran des comptes sur une installation réelle ; la lecture
  de la périodicité reçoit 404, que la page traite comme un refus de consultation
  (`readUnlessRefused(…, [{ status: 404 }])`) : la section disparaît sans rien dire, et la
  périodicité ne se règle que par l'exploitant. Personne ne s'en aperçoit, l'exigence étant close.
- **Proposition** : rattacher les deux opérations à un EPIC — EP-13, à côté de `setBackupSchedule`
  dont elles sont « symétriques » — et rouvrir WF-ADM-0070 pour sa première phrase ; ou, si la
  périodicité doit rester à l'exploitant, le décider et réviser l'exigence. Test : le parcours de
  l'écran des comptes contre le vrai service règle la périodicité et la relit.
- **Confiance** : confirmé pour l'absence de route et d'EPIC porteur (recherché « IdentitySyncSchedule »,
  « périodicité » dans `docs/roadmap/`) ; l'effet à l'écran est lu dans le code, non joué. À recouper
  avec le relecteur de la conformité des routes.

## Constats mineurs

### CTA-04 — Les paramètres d'erreur les plus partagés ne sont pas typés, et une décision croit le contraire

- **Issue** : #4465 (EP-38), ouverte le 2026-11-21, avec BAC-06, CTA-05, CTA-06.
- **Où** : `docs/api/components/common.yaml:820-932` (`ProblemParams` : douze propriétés typées, ni
  `missing_condition`, ni `missing_permission`, ni `expected_lock_version`, ni `component`) ; `:188-194`
  (« `missing_permission` (a `PermissionCode`), `missing_condition` (a `CommandCondition`) », en
  prose) ; `docs/api/DECISIONS.md:10129-10133` (« `ProblemParams.missing_condition` est une
  `CommandCondition` […] la retirer laisserait le 409 sans valeur typée »). Enveloppe de toutes les
  opérations servies.
- **Quoi** : tout 403, tout 409 d'état, tout 412 et tout 503 portent un paramètre que le schéma laisse
  ouvert (`additionalProperties: true`) : le client engendré le lit en `unknown`, et la chaîne qui
  « rejette une réponse qui s'écarte du contrat » (WF-ARC-0060) ne verrait pas une condition hors de
  `CommandCondition`. La décision citée raisonne sur un typage qui n'existe pas.
- **Scénario** : le service rend `missing_condition: "revision_is_draft"` (faute de frappe) ; la
  réponse valide le contrat, le front n'a pas de texte pour ce code.
- **Proposition** : déclarer dans `ProblemParams` `missing_condition` (`CommandCondition`),
  `missing_permission` (`PermissionCode`), `expected_lock_version` (`LockVersion`), `component`
  (`PlatformComponent`), facultatifs — ajout compatible : les 115 `missing_condition`, 9
  `missing_permission` et 5 `component` des fixtures sont déjà dans leurs énumérations (vérifié par
  script). Test : le validateur de réponses refuse une condition inconnue.
- **Confiance** : confirmé.

### CTA-05 — `Problem.correlation_id` reste facultatif alors qu'il est toujours rendu

- **Issue** : #4465 (EP-38), ouverte le 2026-11-21, avec BAC-06, CTA-04, CTA-06.
- **Où** : `docs/api/components/common.yaml:169` (`required: [code, status]`), `:420-428` ;
  `docs/api/components/responses.yaml:121-127` ; service `backend/src/waterfall/api/problems.py:64-70`.
- **Quoi** : WF-OBS-0020 veut l'identifiant « repris dans le message d'erreur présenté à
  l'utilisateur », le service le pose sur toute enveloppe et les 367 exemples d'erreur le portent,
  mais le schéma ne l'exige pas — à rebours de la règle « un champ toujours rendu est exigé »
  (`DECISIONS.md:10757-10760`), appliquée schéma par schéma sans `Problem`.
- **Scénario** : une réponse d'erreur sans `correlation_id` valide le contrat ; le client engendré
  impose au front un `correlation_id?` qu'il doit traiter comme absent.
- **Proposition** : l'exiger. C'est « un champ rendu exigé », que la règle d'après le gel
  (`DECISIONS.md:11056-11060`) réserve à une version ultérieure : à inscrire avec A-07 et les autres
  restes. Test : la validation des réponses refuse une enveloppe sans lui.
- **Confiance** : confirmé.

### CTA-06 — Le corps entier d'un avatar refusé se désigne par `""`, la convention dit `/body`

- **Issue** : #4465 (EP-38), ouverte le 2026-11-21, avec BAC-06, CTA-04, CTA-05.
- **Où** : `docs/api/paths/me.yaml:159-161`, `:194-198` (pointeur `""`) ;
  `fixtures/api/avatar_not_image.json` ; contre `docs/api/README-fr.md:54` (« un corps qui n'est pas
  un objet, `/body` ») et `docs/api/components/common.yaml:805-812` (« a body that is not a JSON
  object […] is designated whole by `/body` […] a pointer thus designates only one field »).
  Opération servie (`backend/src/waterfall/api/avatars.py:72` rend `""`).
- **Quoi** : la règle écrite pour régler J-10 (revue du 2026-10-31) vaut pour `uploadChunk` et laisse
  `putMyAvatar`, autre corps binaire, sur l'ancienne forme : deux désignations pour le même cas.
- **Scénario** : la fonction du front qui lit `fields[].pointer` doit connaître deux écritures du
  « corps entier ».
- **Proposition** : soit `/body` pour l'avatar (contrat, fixture, service — un changement de valeur
  rendue, donc 2.0), soit dire l'exception dans le README et `FieldProblem.pointer` (compatible).
- **Confiance** : confirmé.

### CTA-07 — Deux composants morts, que le lint ne peut pas voir

- **Issue** : #4467 (EP-38), ouverte le 2026-11-21, avec CTB-09, CTB-10, CTB-13, CTB-14.
- **Où** : `docs/api/components/responses.yaml:53-66` (réponse `Conflict`, et son exemple
  `fixtures/api/grid_write_marked_refused.json`) ; `docs/api/components/schemas/reference.yaml:6-12`
  (`ActiveFlag`). Hors de mon périmètre, même cas : `components/schemas/projects.yaml`
  (`ProjectSummary`).
- **Quoi** : plus aucune opération ne renvoie à `Conflict` (tous les 409 sont décrits en place) ni à
  `ActiveFlag` ; `DECISIONS.md:11486-11488` dit encore que trois opérations citent `Conflict`, et
  `responses.yaml:40` y renvoie (« (`Conflict`) »). `no-unused-components` de `recommended-strict` ne
  juge que `#/components` de la racine, vide ici : les définitions des fichiers `components/*.yaml`
  lui échappent.
- **Scénario** : l'exemple `grid_write_marked_refused`, engendré « pour » trois opérations, n'est servi
  par aucune ; un relecteur lit dans `Conflict` une règle commune qui n'est plus rattachée à rien.
- **Proposition** : retirer les deux définitions et la fixture (aucun client engendré ne les voit), ou
  les rebrancher ; ajouter au contrôle du contrat un test « toute définition de `components/` est
  référencée » (trente lignes de Python, la vérification faite ici).
- **Confiance** : confirmé (script : toute cible de `$ref` recensée sur les 3 915 renvois).

### CTA-08 — Le contrat ne dit pas qu'une tâche d'un autre compte est un 404

- **Issue** : #4466 (EP-38), ouverte le 2026-11-21, avec CTA-09, CTB-08, CTC-02.
- **Où** : `docs/api/paths/system.yaml:218-225` (`getBackgroundTask`), `:263-275`
  (`getBackgroundTaskResult`) ; seule `listBackgroundTasks` le dit (`:166-168`). Opérations servies :
  `backend/src/waterfall/api/tasks.py:5,89-93`, `api/exports.py:107-125`.
- **Quoi** : le service ne rend une tâche et son fichier qu'au compte qui l'a demandée ; les deux
  opérations ne nomment ni cette règle ni aucune permission, alors que le résultat est un export de
  données de projet.
- **Scénario** : un second service, ou le faux back, écrit d'après le contrat, sert le fichier d'un
  export à toute session qui connaît le `task_id`.
- **Proposition** : une phrase dans chaque description (« lisible par le seul compte qui l'a
  demandée ; pour un autre, 404, comme une tâche inconnue », WF-ADM-0110), sans changement de schéma.
- **Confiance** : confirmé.

### CTA-09 — `setHourlyRate` : la correction d'une année sans taux est un 404 que le contrat ne décrit pas

- **Issue** : #4466 (EP-38), ouverte le 2026-11-21, avec CTA-08, CTB-08, CTC-02.
- **Où** : `docs/api/paths/reference.yaml:1921-1929`, `:1951` (404 partagé), `:1962-1967` (412) ;
  `components/schemas/reference.yaml:736-753`. Servie :
  `backend/src/waterfall/core/cost_settings/interface/hourly_rates.py:302-303,341-342`.
- **Quoi** : avec `lock_version` et sans taux pour l'année, le service répond 404 ; le contrat ne
  décrit que la saisie sans compteur (409 si le taux existe) et la correction d'un taux existant
  (412), et son 404 ne dit que « catégorie inexistante ».
- **Scénario** : deux onglets ; l'un corrige un taux que l'autre n'a jamais vu saisir (grille périmée)
  et reçoit un 404 que l'écran lit comme « catégorie introuvable ».
- **Proposition** : décrire le 404 en place (« un compteur envoyé pour une année qui ne porte pas de
  taux »), avec un exemple engendré.
- **Confiance** : confirmé.

### CTA-10 — Bornes hautes absentes sur des entrées, là où `Offset` a reçu la sienne

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue le dit « plausible » sans
  défaillance montrée, et chaque borne ajoutée est un refus nouveau à décider selon la règle d'après
  le gel.
- **Où** : `docs/api/components/parameters.yaml:104` (`row_number`), `:218` (`max_level`), `:377` et
  `:386` (`payment_delay_days_*`), `:868` (`part_number`), `:258` (`description`, sans `maxLength`
  quand `Search` en a un) ; `paths/access.yaml:844,851` (`holder_count_*`) ; `paths/platform.yaml:60,66`
  (`size_bytes_*`) ; `paths/reference.yaml:190,196,202` (`level*`) ; `components/common.yaml:11-16`
  (`Decimal`, chaîne sans `maxLength`, donc `RoleCapacity` `schemas/reference.yaml:225-234` et
  `DurationUnitsWrite` `:961-978` sans plafond) ; `schemas/access.yaml:321-323`, `:643-645`
  (`access_role_ids`, `permissions` sans `maxItems`).
- **Quoi** : la décision #2778 (`DECISIONS.md:285-295`) a borné `Offset` « comme toute valeur hors de
  ses bornes » ; les autres entiers et décimaux d'entrée n'ont pas de plafond déclaré.
- **Scénario** : `holder_count_min=10^30` ou une capacité de mille chiffres passent la validation du
  contrat ; ce que la base en fait n'est dit nulle part.
- **Proposition** : `maximum: 2147483647` sur ces entiers, un `maxLength` sur `Decimal`, `maxItems`
  sur les deux listes ; ajout de borne = refus nouveau, à décider selon la règle d'après le gel.
- **Confiance** : plausible — je n'ai pas éprouvé le service au-delà des bornes (aucun test lancé ;
  psycopg 3 passe les grands entiers en `numeric`, ce qui évite probablement l'erreur qu'`Offset`
  provoquait) ; la liste des permissions en double, elle, est bien tolérée
  (`core/access_roles/roles.py:315-336`).

### CTA-11 — La sonde publique `getReadiness` rend la version de chaque composant sans session

- **Issue** : #4478 (EP-39), ouverte le 2026-11-21.
- **Où** : `docs/api/paths/system.yaml:70-95` (`security: []`, `components` de `ComponentHealth`) ;
  `components/schemas/platform.yaml:124-135` (`version`) ; `fixtures/api/readiness.json` (PostgreSQL
  16.4, Redis 7.4.1, fournisseur d'identité 26.0.5). **Non servie** (due par EP-13,
  `docs/roadmap/EP-13-exploitation.md:106`).
- **Quoi** : WF-ADM-0130 réserve les versions à l'écran d'état, sous `system_status.read` ; la sonde
  d'orchestration les donne à tout appelant non authentifié.
- **Scénario** : là où l'API est joignable sans passer par le front, un inconnu lit les versions
  exactes des composants.
- **Proposition** : à EP-13, soit dire de `getReadiness` ce que `getMetrics` dit de lui-même (réseau
  interne seul, 404 à l'entrée publique), soit rendre la sonde sans `version`.
- **Confiance** : confirmé pour le contrat ; l'exposition réelle dépend du déploiement.

### CTA-12 — `RoleCapacity.monthly_hours` saisi, quand WF-REF-0100 le déduit de l'effectif et du calendrier — déjà connu (#2836, EP-10)

- **Suite** : corrigé depuis la revue, vérifié le 2026-11-21 — EP-10 (US-2410/L1, commit 6023d936e)
  : `RoleCapacity` dit « the headcount […] entered (`RoleCapacityWrite`), and the hours per month it
  gives, calculated, never entered », et le service calcule `_monthly_hours` à la lecture. #2836 est
  close.
- **Où** : `docs/api/components/schemas/reference.yaml:225-234`, `:236-261`. Servie.
- **Quoi** : la spécification en vigueur dit les heures mensuelles calculées (effectif × heures
  hebdomadaires × 52 / 12) ; le contrat les fait saisir. Écart reporté par décision du 2026-11-12
  (`docs/roadmap/EP-24-consolidation-apres-v0-3-0.md:245,482`). Rappelé pour mémoire, sans proposition.
- **Confiance** : confirmé.

## Points forts

- Cohérence mécanique : 0 `$ref` cassé sur 3 915, 0 `required` orphelin, 637 exemples valides sur 637
  dans les six familles (le seul échec de mon script était un faux positif, `x-examples`).
- Les exemples respectent les règles que les schémas n'énoncent qu'en prose : 50 comptes vérifiés
  (ordre et contenu d'`available_commands`, nullité d'un compte anonymisé, libellés résolus), 82 pages
  cohérentes avec leur `meta`, tous les codes, conditions et permissions cités existent dans leurs
  énumérations, toutes les exigences citées existent dans la spécification.
- Conventions tenues sans exception non décidée : 401/503 sur toute opération gardée, 400/422 sur tout
  corps, 404 sur tout chemin à identifiant, 412 partout où un compteur est envoyé, suppression avec
  compteur en paramètre et `LockVersionInvalid`, listes en `explode: false`, filtres `_min`/`_max` et
  périodes avec leur 422.
- Les décisions d'habilitation fines sont suivies : `setUserAccessRoles` sous les deux permissions,
  compte né sans rôle, taux horaires sous `cost_settings.read`, objets actifs du référentiel lus par
  toute session, téléchargement d'une sauvegarde sous lecture et écriture.
- Le journal d'audit couvre exactement les actions de WF-SEC-0030 et les cinq filtres de WF-ADM-0190.

## Couverture

- **Lu en entier** : `docs/api/openapi.yaml`, `redocly.yaml`, `.redocly.lint-ignore.yaml`,
  `README-fr.md`, `components/common.yaml`, `components/parameters.yaml`, `components/responses.yaml`,
  `paths/{access,me,platform,system,audit,reference}.yaml`,
  `components/schemas/{access,platform,audit,reference}.yaml`.
- **Vérifié par script** (lecture seule, sur tout le contrat) : résolution des `$ref`, définitions
  jamais référencées, `required` contre propriétés ; sur mes six familles : validation de chaque
  exemple contre son schéma, table statuts/compteur par opération ; sur toutes les fixtures : forme
  des enveloppes d'erreur.
- **Spécification** lue à la ligne : WF-ADM-0010 à 0190, WF-SEC-0010 à 0030, WF-REF-0010 à 0190,
  WF-CYC-0120, WF-OBS-0010 à 0030, WF-EXP-0040/0050/0060, WF-ARC-0090/0110, WF-IHM-0080/0110/0130,
  WF-DAT-0070/0120, WF-PLA-0160.
- **Échantillonné** : `DECISIONS.md` par recherche (une quarantaine de passages lus, jamais en
  entier) ; la revue `2026-10-31-contrat-spec-et-fixtures.md` (tables des constats A, B, C, J, pour
  ne pas les redire) ; le service, pour savoir ce qui est servi et pour suivre les deux majeurs
  (`api/users.py`, `api/access_roles.py`, `api/tasks.py`, `api/exports.py`, `api/hourly_rates.py`,
  `core/access_roles/`, `core/users/commands.py`, l'extension Keycloak).
- **Non lu** : `README.md` (traduction), `INVENTORY.md`, `tools/inventory.py`, la revue du 2026-10-28,
  les fixtures à l'œil (seulement par script), les familles de l'autre relecteur hors les énumérations
  que les miennes référencent. `make lint-openapi` non lancé (règle du cahier).
- **Opérations de mon périmètre non servies** : dues par EP-13, donc hors constat d'absence —
  `getReadiness`, `getMetrics`, `getSystemStatus`, `retainBackup`, `getBackupSchedule`,
  `setBackupSchedule`, `listExternalBackupLocations`, `testExternalBackupLocation` ; dues par
  personne — `getIdentitySyncSchedule`, `setIdentitySyncSchedule` (CTA-03).

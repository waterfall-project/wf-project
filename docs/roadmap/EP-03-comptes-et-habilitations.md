---
id: EP-03
titre: Se connecter, et n'agir que dans les limites de ses habilitations
statut: en cours
depend_de: EP-01, EP-02
famille: front, back, plateforme
issue: 426
---

# EP-03 — Comptes, authentification et habilitations

## Objet

Le premier service réel : l'API, la base, les migrations, et l'identité de l'appelant tirée
du jeton du fournisseur d'identité livré avec la plateforme. Les comptes locaux, l'annuaire
LDAP ou AD et le fournisseur externe passent tous par Keycloak (WF-ARC-0030) ; Waterfall
lit l'état du compte, ses rôles et ses permissions à chaque requête. Les rôles d'habilitation
et le catalogue des permissions arrivent avec lui, et la lecture des comptes du fournisseur,
premier traitement de fond, fait naître le worker et sa file.

Il vient avant tout domaine métier parce que toute action ultérieure s'évalue contre une
permission (WF-ADM-0110) et que toute table porte l'auteur de ses écritures (WF-DAT-0070) :
un domaine construit avant les comptes, ce sont des règles d'accès à reprendre. C'est aussi le
premier EPIC dont les réponses peuvent se comparer au schéma déclaré — WF-ARC-0060 se clôt ici.

## Ce qui en fait partie

- le service d'API, la base PostgreSQL, les migrations versionnées, et les conventions du
  §4.4.1 appliquées dès la première table : identifiants, colonnes d'audit, régimes de
  suppression, intégrité déclarée, types des grandeurs ;
- les règles de codage du SQL et des migrations, troisième fichier de règles de codage à
  côté de ceux de Python et de TypeScript (US-0300), fixées en écrivant la première table ;
  et les sections du guide de développement qu'EP-01 a ouvertes pour lui : l'écriture d'une
  migration, l'ajout d'un code d'erreur côté service ;
- l'authentification déléguée au fournisseur d'identité (Keycloak, PBS-5.4) : son royaume
  versionné dans le dépôt, sa politique de mot de passe et de verrouillage (WF-ADM-0140), la
  fédération d'un annuaire et le relais vers un fournisseur externe sur la plateforme de
  développement ; le flux du code d'autorisation côté serveur du front, les jetons gardés
  dans Redis, jamais dans le navigateur ; la validation du jeton par l'API, et la
  révocation (WF-SEC-0020). Les décisions de #215, transféré ici le 2026-10-04, en sont le
  point de départ ;
- les comptes : attributs, cycle de vie, lien de fixation du mot de passe, avatar ; la lecture
  des comptes du fournisseur, à la demande et à intervalle régulier ;
- les rôles d'habilitation, le catalogue des permissions, les trois rôles prédéfinis, et la
  protection du dernier administrateur ;
- les permissions effectives connues du front, et les préférences et la langue conservées dans
  le compte ;
- le worker, la file de tâches et le dépôt périodique d'une tâche en file, la lecture des
  comptes du fournisseur pour premier traitement ;
- le journal d'audit, pour les comptes, les rôles et leurs attributions, et sa consultation
  (FBS-1.5, `audit_log.read`), que la plateforme ne peut ni modifier ni supprimer ;
- les journaux structurés du service et du worker, dès leur premier enregistrement :
  l'identifiant de corrélation engendré à l'entrée et transmis aux tâches, l'auteur, la
  gravité, et aucun mot de passe, jeton ni secret — faute de quoi tout le code d'EP-04 à
  EP-11 s'écrirait sans eux et serait à reprendre ;
- l'amorçage d'une installation neuve : catalogue, rôles prédéfinis, compte administrateur
  et son lien de fixation, langue par défaut ;
- la comparaison, par la chaîne, des réponses de l'API au schéma déclaré, et les parcours de
  bout en bout joués contre le vrai service (`WATERFALL_API_ADDRESS`), qui comptent alors au
  relevé des exigences comme preuve du back ;
- les écrans de connexion, de mon compte, des comptes et des rôles de la maquette, branchés
  sur le service : la saisie en ligne de la table des comptes (#379) et la matrice des
  permissions comme lieu de la modification des rôles (#380) ;
- une plateforme déployable pour des démonstrations (revue de la ventilation, 2026-10-09) :
  les images de production, publiées par la chaîne, et un Compose de production qui les
  déploie sur une machine seule, derrière un frontal TLS, secrets injectés au démarrage ;
- la sauvegarde et la restauration de la plateforme entière — les deux bases, Waterfall et le
  fournisseur d'identité —, le téléchargement d'une sauvegarde et le dépôt d'une sauvegarde
  venue d'une autre installation : c'est ainsi qu'une installation de référence, son
  référentiel et ses comptes se reproduisent d'une machine à l'autre (WF-ADM-0160 : aucune
  restauration partielle) ; et les écrans de la sauvegarde de la maquette, branchés.

## Ce qui n'en fait pas partie

- le rattachement d'un compte à un nœud d'organisation (WF-ADM-0030) — EP-05, qui crée
  l'arbre ; ici, `org_node_id` reste nul et le filtre `org_node_id` de `listUsers` ne retient
  rien ;
- la qualité de contributeur, second terme de l'évaluation d'une action — EP-04 ;
- l'écran d'accueil (WF-IHM-0120) — EP-04, qui sert la liste des projets et les
  contributeurs ; ici, la connexion mène à l'accueil tel que la maquette le présente ;
- la garde des lectures du référentiel avec `include_inactive` (#351) — EP-05, qui les sert ;
- l'écran d'état, qui complète les usages de l'administrateur (WF-INTF-0030), la
  planification et la rétention des sauvegardes, leur copie vers un emplacement externe, le
  test de restauration périodique — EP-13 ; la conservation du journal aussi longtemps que
  les projets (WF-SEC-0030) — EP-13 ;
- le chart Helm, le chiffrement des échanges entre les services, la mise à jour sans
  interruption — EP-13. Ici, le navigateur ne parle qu'en HTTPS au frontal, et un service qui
  démarre sans ses secrets échoue en le disant ;
- tout écran de mot de passe dans Waterfall : la fixation, la réinitialisation et le
  changement du mot de passe d'un compte local se font sur les pages du fournisseur
  d'identité (WF-ADM-0140) ; les écrans de mot de passe d'US-0320 disparaissent.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0030-A` | Usages de l’administrateur | début — close en EP-13 | US-0380 |
| `WF-INTF-0160-A` | Choix de la langue de l'interface | fin — amorcée en EP-02 | US-0400 |
| `WF-ADM-0040-A` | Préférences d’affichage | début — close en EP-04 | US-0400 |
| `WF-IHM-0060-A` | Lecture d'une grille | début — close en EP-07 | US-0400 |
| `WF-IHM-0130-A` | Filtrage des tables et export des graphiques | début — close en EP-11 | US-0360 |
| `WF-ADM-0050-A` | Attributs d’un compte utilisateur | entière | US-0360 |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | début — close en EP-04 | US-0360 |
| `WF-ADM-0070-A` | Lecture des comptes du fournisseur d’identité | début — close en EP-04 | US-0370 |
| `WF-ADM-0080-A` | Avatar | entière | US-0400 |
| `WF-ADM-0140-A` | Authentification et mot de passe | entière | US-0350 |
| `WF-ADM-0180-A` | Fournisseurs d’authentification | entière | US-0350 |
| `WF-ADM-0010-A` | Rôles d’habilitation prédéfinis | entière | US-0380 |
| `WF-ADM-0020-A` | Aucune action réservée à un acteur | début — close en EP-05 | US-0380 |
| `WF-ADM-0090-A` | Rôles et permissions | entière | US-0380 |
| `WF-ADM-0100-A` | Catalogue des permissions | début — close en EP-08 | US-0380 |
| `WF-ADM-0110-A` | Évaluation d’une action | début — close en EP-04 | US-0390 |
| `WF-ADM-0120-A` | Dernier administrateur | entière | US-0380 |
| `WF-ARC-0060-A` | Contrat OpenAPI | fin — amorcée en EP-01 | US-0340 |
| `WF-ARC-0110-A` | Le texte est rendu au plus près du lecteur | début — close en EP-06 | US-0410 |
| `WF-ARC-0030-A` | Authentification déléguée | entière | US-0350 |
| `WF-ARC-0090-A` | Traitements longs confiés au worker | début — close en EP-13 | US-0370 |
| `WF-DAT-0060-A` | Identifiants | début — close en EP-04 | US-0330 |
| `WF-DAT-0070-A` | Colonnes d’audit | début — close en EP-09 | US-0330 |
| `WF-DAT-0080-A` | Régimes de suppression | début — close en EP-04 | US-0330 |
| `WF-DAT-0090-A` | Intégrité déclarée en base | début — close en EP-07 | US-0330 |
| `WF-DAT-0100-A` | Types des grandeurs | début — close en EP-07 | US-0330 |
| `WF-DAT-0140-A` | Migrations du schéma | début — close en EP-13 | US-0330 |
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-04 | US-0420 |
| `WF-SEC-0010-A` | Transport et secrets | début — close en EP-13 | US-0330 |
| `WF-SEC-0020-A` | Session et révocation | entière | US-0350 |
| `WF-SEC-0030-A` | Journal d'audit des actions irréversibles ou structurantes | début — close en EP-13 | US-0410 |
| `WF-ADM-0190-A` | Consultation du journal d’audit | début — close en EP-13 | US-0410 |
| `WF-OBS-0020-A` | Journaux structurés et corrélation | début — close en EP-13 | US-0330 |
| `WF-ARC-0050-A` | Empaquetage et déploiement | début — close en EP-13 | US-0430 |
| `WF-ADM-0150-A` | Sauvegarde | entière | US-0440 |
| `WF-ADM-0160-A` | Restauration | début — close en EP-04 | US-0440 |
| `WF-DAT-0120-A` | Contenu et purge du stockage objet | début — close en EP-06 | US-0440 |

Décisions du cadrage, 2026-10-07, sur des phrases de Vérif que cet EPIC ne peut pas
constater faute des objets d'un EPIC ultérieur : WF-IHM-0120 passe entière en EP-04 ;
WF-ADM-0060 et WF-ADM-0070 se closent en EP-04 (une révision marquée, des actes
consultables) ; WF-ADM-0100 en EP-08 (le devis, le marquage, la création d'un projet, puis la
fusion, dernière action gardée) ; WF-ADM-0020 en EP-05 (la première action d'un autre acteur
que l'administrateur) ; WF-ADM-0040 en EP-04 (« le même projet ») ; WF-IHM-0060 en EP-07 (le
tri de la grille de devis, qu'EP-02 attribuait à tort à EP-03) ; WF-IHM-0130 entre ici pour les
tables des comptes et des rôles, et reste close en EP-11. WF-ARC-0110, un temps déplacée en
EP-13 faute de lecture du journal d'audit, revient se clore avec le premier import, en EP-06
(EP-12 abandonné) : la revue de la
ventilation du 2026-10-09 donne aussi à EP-03 un Compose de production pour des
démonstrations, et la sauvegarde et la restauration (WF-ADM-0150, entière ; WF-ADM-0160,
close en EP-04 sur des projets et des révisions), ainsi que la consultation du journal, qu'EP-02 a ajoutée au
contrat (`listAuditEvents`, FBS-1.5). Les tableaux des EPIC concernés le disent.

## Opérations du contrat

Le contrat d'`epic/EP-02` décrit encore une session ouverte par Waterfall — `openSession`
reçoit un mot de passe, la session est « conservée en base », et `DECISIONS.md` écarte le
jeton Bearer — quand la spécification révisée délègue l'authentification au fournisseur
d'identité (WF-ARC-0030), interdit tout écran de mot de passe (WF-ADM-0140) et range la
session du front dans Redis (§4.4.1). La modification, décidée par #215 et reprise au cadrage
le 2026-10-07, est le premier travail de cet EPIC, sur sa branche, avant le code qui la
consomme ; elle est décrite dans une issue « Interface contract issue » et dans la
conception :

- un schéma de sécurité `bearer`, le jeton d'accès du fournisseur, à la place du témoin de
  session ;
- retirées : `listAuthProviders`, `getCurrentSession`, `openSession`, `startOidcSession`, `completeOidcSession`, `requestPasswordReset`, `confirmPasswordReset`,
  `changeMyPassword`, et les schémas qu'elles seules emploient ; `closeSession` devient
  `closeMySessions`, qui ferme toutes les sessions du compte ; les permissions effectives,
  que `Session` portait, passent à `getMe` ;
- `createPasswordSetupLink` reste, son lien menant à la page du fournisseur qui fixe le mot
  de passe, et non plus à `/login/reset` du front ;
- `startDirectorySync` et `getLatestDirectorySync` (`startIdentitySync`, `getLatestIdentitySync`) lisent les comptes du fournisseur
  d'identité, non l'annuaire, et leur chemin le dit (`identity-syncs`) ; le compte rendu
  nomme ses signalements par un code du catalogue ;
- les refus par champ des écritures d'un compte qui manquent : rôle ou nœud inconnu, nom
  d'un compte fédéré (#379) ;
- les filtres qui manquent pour que chaque colonne des tables des comptes et des rôles se
  filtre (WF-IHM-0130) : par rôle et par état sur `listUsers`, dont la recherche porte sur le
  nom, le prénom et l'adresse, et non sur un libellé qu'un compte n'a pas ; par nature et par
  la présence de porteurs sur `listAccessRoles`, avec le nombre de rôles retenus ; et, sur
  les deux, un ordre de départage qui rend les pages stables.

Servies ici pour la première fois, après cette modification (33) :

- `system` : `getLiveness`, `getInstallation`, `getBackgroundTask`, `listBackgroundTasks` ;
- `me` : `getMe`, `closeMySessions`, `updateMyPreferences`, `putMyAvatar`, `deleteMyAvatar` ;
- `users` : `listUsers`, `createUser`, `getUser`, `updateUser`, `setUserActivation`,
  `setUserAccessRoles`, `createPasswordSetupLink`, `getUserAvatar`, `startDirectorySync`,
  `getLatestDirectorySync` ;
- `access` : `listPermissions`, `listAccessRoles`, `createAccessRole`, `getAccessRole`,
  `updateAccessRole`, `deleteAccessRole` ;
- `audit` : `listAuditEvents`, `listAuditFacets` ;
- `platform` : `listBackups`, `startBackup`, `getBackup`, `downloadBackup`, `startRestore` ;
- `exchanges` : `uploadFile`, pour le dépôt d'une sauvegarde venue d'ailleurs.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (0) :

aucune.

## Préalables

EP-01 et EP-02 livrés : le premier lot modifie le contrat et le front qu'EP-02 a posés, et
`epic/EP-03` se tire de `main` une fois EP-02 fusionné dans `main` (décision du cadrage,
2026-10-07), ce qui suppose EP-02/L30 (#393) fusionné. Écarté : tirer `epic/EP-03`
d'`epic/EP-02` dès L30, qui ferait reposer EP-03 sur un EPIC non livré.

## Définition de fini

- un compte local, un compte de l'annuaire et un compte du fournisseur externe ouvrent chacun
  une session sur la plateforme de développement, sans qu'aucun écran de Waterfall ne demande
  de mot de passe ;
- la désactivation d'un compte connecté sur deux postes interrompt les deux à leur requête
  suivante ;
- une action demandée sans la permission est refusée par l'API en nommant la condition
  manquante, même quand le front ne la propose pas ;
- une réponse non conforme au schéma déclaré fait échouer la chaîne, et aucun endpoint ne
  répond qui ne figure au contrat ;
- l'installation d'une plateforme neuve crée le catalogue, les trois rôles et le compte
  administrateur, et produit son lien de fixation ; relancée, elle ne crée rien ;
- le parcours de bout en bout traverse la connexion, mon compte, les comptes et les rôles
  contre le service réel, et le relevé des exigences le compte comme preuve du back ;
- le Compose de production, sur des images publiées par la chaîne, démarre une plateforme
  complète sur une machine neuve, en HTTPS, qu'un administrateur atteint par le lien de
  l'amorçage ;
- une sauvegarde prise sur une installation, téléchargée puis déposée sur une autre et
  restaurée, rend sur la seconde les comptes, les rôles et les réglages de la première.

## Conception

Écrite le 2026-10-07 sur le contrat et la spécification d'`epic/EP-02`. Chaque décision dit
l'option écartée ; celles qui défont une décision antérieure le disent avec leur source.

### Vue d'ensemble

```
navigateur ──témoin opaque── front (Next) ──Bearer── service d'API ──── PostgreSQL (waterfall)
                              │   │                      │   │
                              │   └── Redis : sessions   │   └── Redis : file de tâches ── worker
                              │       du front, verrous  │                                  │
                              └──── Keycloak ◄───────────┴── API d'administration ◄─────────┘
                                    (royaume waterfall, extension, base keycloak)
                                    ├── annuaire LDAP (fédération, console)
                                    └── fournisseur externe (relais OIDC, console)
```

Le navigateur ne parle qu'au front (TFX-01) et à Keycloak (TFX-07). Le front tient les
jetons ; l'API ne tire du jeton que l'identité et lit tout le reste en base (WF-ARC-0030).

### Authentification et session

**Keycloak.** Image Keycloak 26 construite par le dépôt (`deploy/keycloak/`), avec
l'extension ci-dessous. Le royaume `waterfall` est un fichier versionné
(`deploy/keycloak/realm/waterfall.yaml`), appliqué de façon idempotente à chaque déploiement
par keycloak-config-cli (#215) : un service de Compose ici, un crochet Helm en EP-13. Il
porte :

- les clients : `waterfall-front` (confidentiel, code d'autorisation avec PKCE, adresses de
  retour du front, déconnexion par canal de retour vers le front), `waterfall-api` (audience
  des jetons, sans flux propre), `waterfall-service` (compte de service de l'API et du worker,
  rôles `manage-users`, `view-users`, `query-users` et le rôle de l'extension) ;
- la politique de mot de passe de WF-ADM-0140 : douze caractères au moins, ni l'adresse
  (`notEmail`, `notUsername`, l'adresse servant d'identifiant), ni le nom (règle de
  l'extension) ; le verrouillage temporaire : dix échecs, quinze minutes, jamais permanent ;
  aucune expiration périodique ; liens d'action valables une heure ;
- les durées de WF-SEC-0020 : jeton d'accès 5 min ; session inactive 2 h ; session 12 h ;
  rotation du jeton de rafraîchissement, réemploi refusé (`revokeRefreshToken`,
  `refreshTokenMaxReuse` 0) ;
- l'inscription libre fermée, l'adresse comme identifiant, les langues fr et en, le thème
  de connexion et les modèles de courriel dans les deux langues.

keycloak-config-cli ne gère que ce que le fichier déclare : la fédération d'un annuaire et
les fournisseurs externes, que l'administrateur raccorde dans la console (WF-ADM-0180), ne
sont ni écrasés ni supprimés. La plateforme de développement ajoute, par un second fichier
qui ne sert qu'à elle, un annuaire OpenLDAP de test, un second royaume `external` qui joue le
fournisseur externe, et Mailpit pour recevoir les courriels : c'est ce qui rend la Définition
de fini constatable. La base de Keycloak est une base distincte sur le même serveur
PostgreSQL (#215, PBS-3.1).

**L'extension Keycloak** (décision du cadrage, 2026-10-07). Un fournisseur Java,
`deploy/keycloak/extension/`, construit par un Dockerfile multi-étapes dans l'image Keycloak :
aucune JVM n'est demandée au poste. Deux pièces :

- `password-setup-link` : un point d'entrée du royaume, réservé au rôle
  `waterfall-password-link` du compte de service, qui rend pour un compte un lien d'action
  « fixer le mot de passe », valable une heure et à usage unique, vers la page de Keycloak ;
  il fait tourner un nonce porté par le compte, de sorte qu'un lien précédent cesse de
  valoir ;
- `not-last-name` : la règle de politique « le mot de passe n'est pas le nom du compte ».

Son code suit un quatrième fichier de règles, court (`docs/dev/java.md`) ; il se teste par
les tests d'intégration du service contre le Keycloak de la plateforme, et la chaîne
construit l'image à chaque modification de `deploy/keycloak/`.

**Le front.** `openid-client`, côté serveur Next (#215). `/login?next=…` devient un
gestionnaire de route qui démarre le flux : `state`, `nonce` et le vérificateur PKCE sont
écrits dans Redis avec l'adresse visée, quinze minutes au plus ; `/auth/callback` échange le
code, vérifie l'état, et ouvre la session du front : un identifiant opaque dans le témoin
`wf_session` (`httpOnly`, `Secure`, `SameSite=Lax`), les jetons dans Redis sous cet
identifiant, avec une durée calée sur la session de Keycloak. L'adresse visée ne passe que si
`returnTarget` l'accepte (`frontend/src/navigation/login.ts`) : un chemin du front, sinon
l'accueil. `serverClient()` reste le seul endroit qui porte le jeton à l'API (EP-02) ; il
rafraîchit un jeton qui expire dans moins de trente secondes, sous un verrou Redis par
session, pour que deux requêtes concurrentes ne présentent jamais le même jeton de
rafraîchissement. Les écrans de mot de passe d'US-0320 (`/login/reset`, le formulaire de
connexion, le changement de mot de passe) disparaissent ; l'écran de mon compte mène, pour
un compte local, à la page du compte de Keycloak.

**Déconnexion et révocation.** WF-SEC-0020 veut que la déconnexion, la désactivation et le
retrait de tous les rôles prennent effet « à la requête suivante, sur tous ses postes ». Les
trois passent par le même chemin : l'API demande à Keycloak de fermer toutes les sessions du
compte (API d'administration), Keycloak le notifie au front par la déconnexion par canal de
retour (`/auth/backchannel-logout`, une route du front, pas une opération de l'API), et le
front efface les sessions Redis de ce compte. La déconnexion demandée par l'utilisateur est
une opération du contrat (`closeMySessions`, ci-dessous) : le front ne parle pas à l'API
d'administration de Keycloak. Indépendamment, l'API lit l'état du compte à chaque requête :
un compte désactivé est refusé même si la notification se perd.

**L'API.** Elle valide chaque jeton par les clés publiques du royaume (PyJWT, clés mises en
cache et relues sur un identifiant de clé inconnu) : signature, émetteur, audience
`waterfall-api`, expiration. Elle n'en tire que `sub`. Le compte se lit par
`user_account.idp_subject` ; un `sub` inconnu est un compte que Waterfall ne connaît pas
encore — un compte de l'annuaire avant la première lecture, ou une personne venue d'un
fournisseur externe —, que l'API crée sans rôle après avoir lu son origine dans l'API
d'administration de Keycloak (lien de fédération ou identité relayée) (WF-ADM-0180,
WF-ADM-0070). Un compte désactivé est refusé par 401 `ACCOUNT_DEACTIVATED`.

### Tables et migrations

Alembic, des migrations écrites à la main, revues comme le code ; jamais d'autogénération
validée sans relecture. Une convention de nommage des contraintes, déclarée une fois. Chaque
migration est compatible avec le code qui la précède et celui qui la suit (WF-DAT-0140) : on
ajoute, puis on retire dans une migration ultérieure. Toutes les tables d'EP-03 sont du
régime « plateforme » (§4.4.1) : jamais supprimées, sauf les associations, qui ne portent
rien d'autre que leurs deux clés.

| Table | Contenu | Contraintes |
|---|---|---|
| `installation` | une seule ligne : langue par défaut, borne de l'avatar, borne d'une sauvegarde déposée, date d'installation | une seule ligne (clé constante vérifiée) ; langue dans `fr`, `en` ; borne de l'avatar ≤ 8 Mio |
| `user_account` | identité (`last_name`, `first_name`, `email`), `idp_subject`, `origin`, `state`, `display_preferences` (jsonb), `avatar` (bytea), `avatar_media_type`, audit, `lock_version` | adresse unique sans égard à la casse (index unique sur `lower(email)`) ; `idp_subject` unique ; `origin` dans `local`, `directory`, `identity_provider` ; `state` dans `active`, `deactivated` ; type d'image dans `image/png`, `image/jpeg` ; taille de l'avatar ≤ 8 Mio |
| `permission` | `code`, `kind`, `fbs_code` | `code` unique ; `kind` dans les quatre natures ; écrite par migration seulement |
| `access_role` | `label`, `is_predefined`, `deleted_at`, audit, `lock_version` | — |
| `access_role_permission` | rôle, permission | clé primaire sur les deux ; clés étrangères en refus |
| `user_access_role` | compte, rôle | clé primaire sur les deux ; clés étrangères en refus |
| `background_task` | `kind`, `status`, `progress`, `payload`, `result`, `problem` (jsonb), `requested_by`, `correlation_id`, `attempts`, dates | `kind` et `status` dans les énumérations du contrat |
| `identity_sync_report` | la tâche, les nombres de comptes créés, mis à jour, désactivés, les signalements | clé étrangère vers la tâche |
| `audit_entry` | `occurred_at`, `actor_user_id` (nul pour la plateforme), `action`, `object_kind`, `object_id`, `project_id` (nul ici), `params` (jsonb), `correlation_id` | `action` dans une énumération qui s'étend par migration ; aucune mise à jour ni suppression : le rôle de base du service n'a que `INSERT` et `SELECT`, et un déclencheur refuse l'une et l'autre |
| `backup` | `taken_at`, `size_bytes`, `verification` (`pending`, `passed`, `failed`), `origin` (`manual`, `scheduled`), `is_retained`, `object_key`, la version de l'application et la révision du schéma qui l'ont produite, la tâche | `verification` et `origin` dans leurs énumérations ; aucune ligne supprimée en EP-03 (la rotation est d'EP-13) |
| `file_upload` | `purpose`, `object_key`, `size_bytes`, `requested_by`, `expires_at`, l'état du dépôt par morceaux | `purpose` dans `FileUploadPurpose` ; un dépôt non employé expire |

- **Identifiants** : UUID v7 engendrés par le service (`uuid-utils`), jamais par un
  défaut de la base ; Python 3.13 n'a pas encore `uuid.uuid7`.
- **Audit des lignes** : `created_at`, `created_by`, `updated_at`, `updated_by` ;
  l'auteur est une clé étrangère vers `user_account`, nulle pour la plateforme (WF-DAT-0070),
  que le contrat rend `ActorRef { kind: platform }`.
- **Le catalogue** est écrit par une migration de données : l'installation crée le
  catalogue parce qu'elle applique les migrations (WF-EXP-0020), et une permission nouvelle
  d'un EPIC ultérieur est une migration de plus, avec sa valeur dans `PermissionCode`.
- **Le rattachement** : `user_account` n'a pas de colonne `org_node_id` en EP-03 ; EP-05
  l'ajoute avec sa clé étrangère vers `org_node`, quand la table existe (WF-DAT-0090). L'API
  rend `org_node_id` et `org_node_label` nuls jusque-là.
- **Les règles SQL** (`docs/dev/sql.md`) fixent : nommage, types (`numeric` pour toute
  grandeur, jamais `float` ; `timestamptz` ; `date`), contraintes déclarées, refus par
  défaut, migrations en deux temps, interdiction du SQL en texte qui nomme la table d'un
  autre module, verrous.

### Modules

Le noyau suit le découpage FBS (guide, « Le back et les frontières du noyau ») :

| Module | Contenu | Interface offerte |
|---|---|---|
| `waterfall.core.users` (FBS-1.1) | comptes, cycle de vie, préférences, avatar, lecture des comptes du fournisseur | lecture d'un compte et de ses libellés ; création d'un compte venu du fournisseur |
| `waterfall.core.access_roles` (FBS-1.2) | catalogue, rôles, attributions, permissions effectives, évaluation d'une action, garde du dernier administrateur | `effective_permissions(user_id)`, `require(actor, permission)`, `guard_last_administrator(...)` |

Ce qui n'est pas une fonction du métier va dans un paquet nouveau, `waterfall.platform`,
sous le noyau, que le noyau, l'API et le worker importent, et qui n'importe rien d'eux : la
base et ses sessions, les réglages et les secrets, les journaux, la file de tâches, le client
de Keycloak, l'écriture du journal d'audit. Un contrat d'import-linter de plus le garde.

L'évaluation d'une action prend un acteur — le compte et ses permissions effectives, lues
une fois par requête — et une permission ; EP-04 y ajoute la qualité de contributeur. Les
permissions effectives sont l'union des permissions des rôles non supprimés du compte
(WF-ADM-0090), lues à chaque requête : la modification d'un rôle vaut à la requête suivante.

**Le dernier administrateur.** Toute écriture qui peut retirer à un compte actif `users.write`
ou `access_roles.write` — désactivation, attribution des rôles, modification ou suppression
d'un rôle, désactivation par la lecture des comptes — prend d'abord un verrou consultatif de
transaction unique (`pg_advisory_xact_lock`), relit sous lui, puis vérifie qu'un compte actif
au moins garde les deux permissions (WF-ADM-0120). La désactivation, que la commande du compte
dit d'avance (`last_administrator`), est refusée par `STATE_FORBIDS_OPERATION` (409) ; le retrait
d'une permission par l'attribution des rôles ou la modification d'un rôle, qui dépend des rôles
envoyés, par `LAST_ADMINISTRATOR` (409) (contrat, EP-02/L42d) ; la lecture des comptes, elle,
garde le compte actif et le signale.

### Le service d'API

- FastAPI, sans route de documentation ni `openapi.json` : aucun endpoint qui ne figure au
  contrat (WF-ARC-0060).
- Les modèles Pydantic sont **engendrés du contrat** (datamodel-code-generator) dans
  `waterfall/api/contract/`, versionnés et contrôlés à jour comme le client du front
  (`make server-models-up-to-date`, dans `check-contract`) ; ils ne sont pas comptés dans la
  taille d'un lot.
- Les erreurs : le noyau lève des exceptions typées qui portent un code et ses paramètres ;
  un seul gestionnaire les rend dans `Problem`, comme les erreurs de validation (400
  `MALFORMED_REQUEST` ou 422 `VALIDATION_FAILED`, selon le contrat) et toute exception
  inattendue (500 `INTERNAL_ERROR`, avec sa corrélation). La section « Ajouter un code côté
  service » du guide le décrit.
- SQLAlchemy 2, sessions synchrones, psycopg 3 ; une transaction par requête ; la réponse se
  construit avant la validation de la transaction (défaut connu n° 3).
- Les réglages et les secrets se lisent de l'environnement au démarrage (pydantic-settings) ;
  un secret absent arrête le processus en nommant la variable qui manque (WF-SEC-0010).

### Journaux et corrélation

structlog, en JSON. L'identifiant de corrélation est repris de l'en-tête `X-Correlation-ID`
s'il a la forme du contrat, engendré sinon, rendu en en-tête et dans `Problem`, lié au
contexte de chaque enregistrement, et écrit dans la tâche qu'une requête dépose : le worker le
reprend (WF-OBS-0020). Chaque enregistrement porte l'auteur et la gravité. Un processeur
retire tout champ dont le nom évoque un secret (`password`, `token`, `secret`,
`authorization`, `cookie`) ; un test cherche les secrets de la plateforme de test dans les
journaux capturés. Le front transmet l'en-tête qu'il reçoit ou en engendre un.

### Worker, file et planification

- **La tâche vit en base**, dans `background_task` : c'est elle que lisent `getBackgroundTask`
  et `listBackgroundTasks`, et Redis ne garde rien de durable (PBS-3.2).
- **La file est un flux Redis** (`XADD`, groupe de consommateurs) : l'API écrit la tâche, puis
  la dépose après validation de sa transaction ; le worker la lit, la passe `running`,
  l'exécute dans sa transaction, la passe `succeeded` ou `failed`, puis l'acquitte. Un worker
  arrêté laisse son entrée non acquittée, qu'un autre reprend après un délai (`XAUTOCLAIM`) :
  la tâche est rejouée depuis le début, ce que sa transaction unique rend sans risque, et
  échoue après trois tentatives (WF-ARC-0090). Une tâche restée `queued` sans entrée dans le
  flux — la plateforme tombée entre la validation et le dépôt — est redéposée par le worker
  au démarrage puis périodiquement.
- **La planification** : `waterfall-worker enqueue identity_sync` dépose une tâche, et
  n'en dépose pas si une tâche du même genre est en file ou en cours ; un service de Compose
  l'appelle à l'intervalle que fixe `WATERFALL_IDENTITY_SYNC_INTERVAL`, une CronJob le fera en
  EP-13 (PBS-5.3, TFX-10).
- **La lecture des comptes** demande d'abord à Keycloak une synchronisation complète de
  chaque annuaire fédéré, puis lit les comptes du royaume par pages : elle crée les absents
  sans rôle, met à jour nom, prénom et adresse des comptes fédérés, désactive ceux que
  Keycloak ne connaît plus — sauf le dernier administrateur, gardé et signalé —, et ne touche
  aucun compte local (WF-ADM-0070). Ses écritures portent la plateforme comme auteur
  (WF-DAT-0070).

### Journal d'audit

`waterfall.platform.audit` inscrit, dans la transaction de l'action, une ligne par action
énumérée par WF-SEC-0030 que cet EPIC réalise : création et modification d'un compte, de
son état, de ses rôles ; création, modification et suppression d'un rôle ; demande d'un lien
de fixation ; création, mise à jour et désactivation par la lecture des comptes. Une
inscription est un code et des données, sans phrase (WF-ARC-0110), et ne porte jamais le
jeton du lien.

La consultation (FBS-1.5, revue de la ventilation, 2026-10-09) est `listAuditEvents`, sous
`audit_log.read` : une table plate, paginée, triée sur ses sept colonnes — date, auteur,
action, nature de l'objet, libellé, projet, corrélation — et filtrée par période, auteur,
action, projet, objet, corrélation et une recherche sur le libellé que l'inscription garde ;
`listAuditFacets` rend les auteurs et les projets que le journal nomme. L'inscription garde le
libellé de son objet et le nom de son auteur au moment de l'action, pour se lire sans joindre
les tables des autres modules. Les index suivent les tris et les filtres du contrat.

### Amorçage

`waterfall-api install`, une commande du même paquet, sous un verrou consultatif :

1. applique les migrations (`alembic upgrade head`) — le catalogue avec elles ;
2. si la ligne `installation` existe, s'arrête sans rien faire d'autre (WF-EXP-0020) ;
3. crée la ligne `installation` avec la langue par défaut (`WATERFALL_DEFAULT_LANGUAGE`) et
   les bornes ; les trois rôles prédéfinis, avec les permissions de l'exemple `access_roles`
   du contrat et leurs libellés dans cette langue ; le compte administrateur local dans
   Keycloak et dans Waterfall, avec le rôle administrateur, l'adresse venant de
   `WATERFALL_ADMIN_EMAIL` ;
4. écrit sur sa sortie le lien de fixation de ce compte, obtenu de l'extension.

Le royaume Keycloak est appliqué avant, par keycloak-config-cli. EP-05 ajoute à l'étape 3 le
calendrier et la nature de provision.

### Déploiement de démonstration

Décisions de l'auteur du 2026-10-09 (revue de la ventilation) :

- **les images** : `front`, `waterfall` — une image, deux commandes, l'API et le worker,
  l'amorçage et la planification — et `keycloak`, l'image de Keycloak avec l'extension et
  le royaume ; construites par la chaîne à chaque fusion dans `main` et dans une branche
  d'EPIC, publiées sur `ghcr.io/waterfall-project/…`, étiquetées par version, par commit et
  par branche ; aucun secret dedans (WF-SEC-0010) ;
- **le Compose de production** (`deploy/compose/compose.prod.yaml`) : Caddy en frontal, seul
  port ouvert, qui obtient ses certificats Let's Encrypt pour `WATERFALL_DOMAIN` et sert le
  front à la racine et Keycloak sous `/auth` ; le front, l'API, le worker, le planificateur ;
  PostgreSQL (deux bases, Waterfall et Keycloak), Redis, Garage pour le stockage objet et
  son service d'initialisation — topologie, clé d'accès, compartiments `imports` et `backups` —,
  Keycloak et keycloak-config-cli ; des volumes nommés pour les données ;
- **les secrets** : un fichier `.env` que l'exploitant remplit d'après un modèle versionné,
  lu au démarrage ; un service qui en manque s'arrête en nommant la variable ;
- **l'amorçage** : `docker compose run --rm api waterfall-api install`, qui écrit le lien du
  premier administrateur ;
- **la notice** : `deploy/compose/README.md` — installer, amorcer, mettre à jour (tirer une
  étiquette, relancer, les migrations s'appliquent au démarrage de l'API), sauvegarder,
  arrêter ;
- **la preuve** : un travail de la chaîne démarre ce Compose sur les images qu'elle vient de
  publier, sur un nom local, amorce, et vérifie la sonde de vie, la connexion du premier
  administrateur et une sauvegarde.

### Stockage objet

Garage (Deuxfleurs, AGPL-3.0), décision de l'auteur du 2026-10-09 : MinIO Community Edition,
en maintenance depuis décembre 2025, est archivé depuis avril 2026, sans binaires ni
correctifs. Garage tient dans la machine de WF-CMP-0020 et couvre ce dont Waterfall a besoin.
Le code ne parle au stockage que par les opérations S3 standard — écrire, lire, supprimer,
lister, dépôt en plusieurs parties — par boto3, sans extension propre à un produit, et les
compartiments sont des réglages : un exploitant branche le stockage qu'il opère déjà
(WF-ARC-0050, WF-CMP-0020). Garage sert aussi la plateforme de développement et les parcours
contre le service. La purge des fichiers d'import (WF-DAT-0120) est faite par le worker, non
par une règle de cycle de vie du stockage, que tous ne savent pas tenir.

### Sauvegarde et restauration

- **La sauvegarde** est une tâche du worker (`backup`) : `pg_dump` de chaque base, au format
  personnalisé, chacune dans un instantané cohérent ; la table du journal d'audit est exclue
  de la base de Waterfall ; une archive des deux vidages et d'un manifeste — date, version de
  l'application, révision du schéma, empreintes — est écrite dans le compartiment
  `backups` du stockage objet, puis vérifiée (relecture de l'archive et des empreintes,
  `pg_restore --list` de chaque vidage) avant de passer `passed`.
- **Le téléchargement** (`downloadBackup`) lit l'archive du stockage objet et la rend en flux.
- **Le dépôt d'une sauvegarde venue d'ailleurs** (`uploadFile`, `external_backup`, #350) ne
  passe pas par une action serveur, dont la taille de corps est bornée : il se fait par
  morceaux, chacun sous la borne, qui s'assemblent sur le stockage objet — une modification
  du contrat (ci-dessous).
- **La restauration** est une tâche du worker (`restore`), demandée avec la date de la
  sauvegarde confirmée : elle refuse une archive d'une version plus récente que
  l'installation ; met la plateforme en maintenance — l'API répond 503
  `COMPONENT_UNAVAILABLE`, et toutes les sessions sont fermées ; recrée les deux bases depuis
  les vidages, sauf la table du journal d'audit ; applique les migrations postérieures à la
  sauvegarde ; vide les caches de Keycloak par son API d'administration et Redis ; inscrit la
  restauration au journal ; lève la maintenance. Une restauration interrompue reprend depuis le
  début et ne lève la maintenance qu'une fois finie (WF-ARC-0090).
- **Reproduire une installation** est une restauration entière : la seconde installation
  devient une copie de la première, comptes et fournisseur d'identité compris (WF-ADM-0160,
  décision de l'auteur du 2026-10-09).

### Modifications du contrat

Faites sur `epic/EP-03` par le premier lot, avant le code qui les consomme, avec leur entrée
dans `DECISIONS.md` ; décrites dans une issue « Interface contract issue » :

1. **Sécurité** : le schéma `session` (témoin) devient un schéma `bearer` (JWT) ; la section
   « Session et erreurs » de `DECISIONS.md` le dit, et retire « pas de jeton Bearer ».
2. **Session** : retirées `listAuthProviders`, `getCurrentSession`, `openSession`,
   `startOidcSession`, `completeOidcSession`, `requestPasswordReset`, `confirmPasswordReset`,
   `changeMyPassword`, et leurs schémas (`AuthProvider*`, `LocalCredentials`, `Session`,
   `PasswordReset*`, `PasswordChange`) et exemples ; `closeSession` devient
   `closeMySessions` (`DELETE /me/sessions`), qui ferme toutes les sessions du compte.
3. **Mon compte** : `UserSelf` porte `permissions`, les permissions effectives que `Session`
   portait (WF-ADM-0110) ; les exemples de session deviennent des exemples de `getMe`.
4. **Codes d'erreur** : `ACCOUNT_DEACTIVATED` (401) entre ; `INVALID_CREDENTIALS`,
   `ACCOUNT_LOCKED` et `PASSWORD_RESET_TOKEN_INVALID` sortent ; par champ,
   `UNKNOWN_ACCESS_ROLE`, `UNKNOWN_ORG_NODE` et `FIELD_READ_ONLY` entrent, et `createUser`,
   `updateUser`, `setUserAccessRoles` déclarent leur 422 (#379, commit `7081a04` jamais
   arrivé sur `epic/EP-02`).
5. **Lien de fixation** : `PasswordSetupLink.url` mène à la page de Keycloak, et non plus à
   `/login/reset` ; le refus d'un compte non local ou désactivé nomme sa condition par
   `missing_condition` (`is_local_account`, `is_active_account`, nouvelles valeurs de
   `CommandCondition`) plutôt que par `params.state`, que #413 dit ambigu.
6. **Lecture des comptes** : `/directory-syncs` devient `/identity-syncs`
   (`startIdentitySync`, `getLatestIdentitySync`), `BackgroundTaskRef.kind` `directory_sync`
   devient `identity_sync`, `DirectorySyncResult` devient `IdentitySyncReport`, dont les
   signalements portent un `ErrorCode` ; le 409 « aucun annuaire activé » disparaît ;
   `PlatformComponent` remplace `directory` par `identity_provider`.
7. **Tables** : sur `listUsers`, les filtres par rôles (`access_role_ids`) et par état
   (`states`), une recherche décrite sur le nom, le prénom et l'adresse ; sur
   `listAccessRoles`, les filtres par nature (`is_predefined`) et par porteurs
   (`has_holders`) ; sur les deux, le départage par identifiant, qui rend les pages stables.
8. **Rôles** : `deleteAccessRole` dit la suppression logique ; un rôle supprimé est un 404.
9. **Sauvegarde** : `Backup`, `startBackup` et `startRestore` disent que la sauvegarde couvre
   les deux bases, Waterfall et le fournisseur d'identité (WF-ADM-0150), et que la restauration
   laisse le journal d'audit en place et s'y inscrit (WF-ADM-0160 révisée) ; le refus d'une
   sauvegarde d'une version plus récente se nomme ; `BackgroundTaskRef.kind` gagne ce qui
   manque pour suivre la restauration jusqu'à la levée de la maintenance.
10. **Dépôt par morceaux** (#350) : un dépôt s'ouvre, reçoit ses morceaux et se termine, pour
   une sauvegarde venue d'ailleurs ; le dépôt d'un fichier d'import garde sa forme.

### Conformité au contrat et parcours contre le service

- **Dans les tests du service** : chaque réponse d'un test d'API est validée contre le
  contrat (openapi-core), et un test compare les routes de l'application aux opérations du
  contrat — aucune route hors contrat (WF-ARC-0060).
- **Dans les parcours** : `make e2e-service` démarre la plateforme de service
  (`deploy/compose/compose.service.yaml` : API, worker, planificateur, PostgreSQL, Redis,
  Keycloak et sa configuration, OpenLDAP, Mailpit), l'amorce, place Prism en mandataire
  (`prism proxy --errors`) entre le front et l'API — une réponse hors schéma fait échouer le
  parcours —, et joue le projet Playwright `service` (`frontend/e2e/service/`) avec
  `WATERFALL_API_ADDRESS`. La chaîne le joue au palier complet.
- **Le relevé des exigences** : `tools/paths.toml` déclare la famille `end-to-end-service`
  (`frontend/e2e/service/**`), que `wftools.coverage` ne range pas parmi les familles du front
  (`FRONT_FAMILIES`) : une exigence qu'elle cite est prouvée par le back.
- **Le faux back reste** pour les parcours d'EP-02 et les lots de front qui précèdent leur
  back. Le schéma `bearer` exige un en-tête : le front, en mode `WATERFALL_AUTH=mock` — refusé
  si `NODE_ENV` est `production` hors des parcours —, envoie un jeton fixe que Prism accepte.

### Ordre de construction

1. Le contrat (modifications ci-dessus), le client régénéré, et le front qui suit le client
   — encore sur le faux back, en mode `mock`.
2. Le socle du service : réglages, journaux, base, Alembic, `installation` et
   `user_account`, enveloppe d'erreur, corrélation, `getLiveness`, validation des réponses
   dans les tests, plateforme de service dans Compose ; les règles SQL et les sections du
   guide.
3. Keycloak : royaume, extension, image ; validation du jeton par l'API, identification du
   compte, `getMe`.
4. Le front sur Keycloak : connexion, retour, rafraîchissement, déconnexion, canal de retour ;
   la disparition des écrans de mot de passe ; `make e2e-service` et la famille
   `end-to-end-service`.
5. Rôles, catalogue, évaluation, dernier administrateur, journal d'audit.
6. Comptes : création, modification, activation, attribution, lien de fixation ; table des
   comptes et matrice des rôles branchées.
7. Worker, file, planification, lecture des comptes, `getBackgroundTask`,
   `listBackgroundTasks`.
8. Mon compte : préférences, langue — reportée sur l'attribut `locale` du compte dans
   Keycloak, pour les courriels —, avatar, `getInstallation`.
9. L'amorçage, puis les parcours de la Définition de fini.
10. Les images publiées et le Compose de production, dès que la connexion et l'amorçage
    existent.
11. La sauvegarde, puis la restauration, sur le worker et le stockage objet.

### Décisions

| Décision | Option écartée, et pourquoi |
|---|---|
| L'authentification de #215, reprise au cadrage le 2026-10-07 : jeton `bearer`, jetons dans Redis côté front, famille `session` retirée. Défait « Témoin de session `httpOnly`, pas de jeton Bearer » (`DECISIONS.md`, « Session et erreurs ») | garder la session ouverte par Waterfall : contraire à WF-ARC-0030, WF-ADM-0140 et §4.4.1 |
| Une extension Keycloak maison pour le lien de fixation et la règle du nom (cadrage, 2026-10-07) | une extension tierce : licence et maintenance à vérifier, ni l'invalidation du lien précédent ni la règle du nom ; le courriel seul : impossible sans messagerie (WF-CMP-0030) |
| Waterfall fait foi pour l'état du compte : la désactivation ne désactive pas le compte dans Keycloak, elle ferme ses sessions et l'API le refuse | désactiver aussi dans Keycloak : couperait les applications voisines qui partagent le fournisseur (motif de WF-ARC-0030), et un annuaire en lecture seule le refuse |
| La déconnexion ferme toutes les sessions du compte, sur tous ses postes (lecture de WF-SEC-0020, « sur tous ses postes ») | fermer la seule session du navigateur : ne tient pas la phrase pour la déconnexion |
| Un compte désactivé est refusé par 401 `ACCOUNT_DEACTIVATED` | 403 : chaque opération devrait le déclarer, quand le 401 l'est déjà partout (`rule/session-operation-declares-401`) ; le front distingue le code et ne renvoie pas à la connexion, qui bouclerait |
| La suppression d'un rôle est logique (cadrage, 2026-10-07) | la suppression physique : contraire à WF-DAT-0080 |
| La tâche en base, la file dans un flux Redis, un module à nous | arq : asynchrone, état dans Redis, qui ne doit rien garder de durable ; Celery, Dramatiq : un second état à tenir d'accord avec la base ; une file en base (`SKIP LOCKED`) : PBS-3.2 met la file dans Redis |
| Les modèles Pydantic engendrés du contrat | les écrire à la main : deux descriptions de la même interface (motif de WF-ARC-0060) |
| SQLAlchemy synchrone, psycopg 3 | l'asynchrone : rien dans EP-03 ne l'exige, et il complique le typage strict et les tests |
| UUID v7 engendrés par le service | `uuidv7()` de PostgreSQL 18 : l'identifiant n'est connu qu'après l'insertion ; UUID v4 : pas ordonnés dans le temps (WF-DAT-0060) |
| Un paquet `waterfall.platform` sous le noyau | la technique dans les modules du noyau : ils ne seraient plus calqués sur la FBS |
| Garde du dernier administrateur par un verrou consultatif unique | l'isolation sérialisable : des reprises à gérer partout pour une règle qui ne touche que quelques écritures |
| Conformité vérifiée dans les tests du service et par Prism en mandataire dans les parcours | Prism seul : ne couvre que ce que les parcours traversent |
| `installation` porte la langue par défaut ; `ReferenceSettings.default_language` (EP-05) la lira | une langue dans `reference_setting` dès EP-03 : table d'EP-05 |
| `org_node_id` ajouté par EP-05 avec sa clé étrangère | une colonne sans clé dès EP-03 : contraire à WF-DAT-0090 |
| La lecture des comptes passe par Keycloak, qui fédère l'annuaire (WF-ADM-0070) | lire l'annuaire en LDAP depuis Waterfall : un second chemin vers l'annuaire, que la spécification révisée a retiré |
| Une plateforme de démonstration dès EP-03 : images publiées par la chaîne, Compose de production, frontal Caddy (auteur, 2026-10-09) | attendre EP-13 : aucune démonstration sur une installation réelle avant la fin ; construire les images sur le serveur : ce ne seraient pas les mêmes images partout (WF-ARC-0050) |
| Sauvegarde et restauration dès EP-03, la plateforme entière (auteur, 2026-10-09) | un échange du seul référentiel : contraire à WF-ADM-0160 (aucune restauration partielle) et à WF-INTF-0150 (aucun import du référentiel) |
| Garage pour le stockage objet, le code limité aux opérations S3 standard (auteur, 2026-10-09) | MinIO : archivé, sans binaires ni correctifs ; SeaweedFS : plusieurs composants, lourd pour une démonstration ; RustFS : trop jeune |
| Le journal d'audit hors des vidages, laissé en place par la restauration | le restaurer avec le reste : WF-ADM-0160 révisée le garde, et la restauration doit s'y inscrire |
| Le dépôt d'une sauvegarde par morceaux (#350) | une action serveur : sa taille de corps est bornée ; une adresse signée du stockage objet : le navigateur parlerait au stockage, hors des flux du §4.3.2 ; un gestionnaire de route qui relaie l'API : écarté par EP-02 (WF-ARC-0020) |

### Issues à ouvrir avec la conception

- « Interface contract issue » : les huit modifications ci-dessus ; elle ferme, à sa
  réalisation, #152 et #155 (sans objet) et répond à #413 pour les refus d'un compte.
- « Specification finding » : WF-DAT-0080 et WF-ADM-0090 sur la suppression d'un rôle, avec
  la proposition « un rôle supprimé n'est plus proposé et sa trace est conservée ».
- Un commentaire sur #351, rattachée à EP-05.

---

## US-0330 — Service, base et conventions de données

- **statut** : à faire
- **exigences** : `WF-DAT-0060-A`, `WF-DAT-0070-A`, `WF-DAT-0080-A`, `WF-DAT-0090-A`,
  `WF-DAT-0100-A`, `WF-DAT-0140-A`, `WF-SEC-0010-A`, `WF-OBS-0020-A`
- **opérations** : `getLiveness`
- **issue** : #428

**En tant que** développeur, **je veux** un service d'API et un worker qui démarrent sur
PostgreSQL et Redis, une première table écrite selon les conventions du §4.4.1 par une
migration versionnée, et des journaux structurés dès le premier enregistrement, **afin que**
chaque EPIC suivant écrive ses tables et ses journaux sans décider à nouveau comment.

**Critères d'acceptation.**

- `WF-DAT-0060-A` — « La modification du code d’un projet ou de l’adresse d’un compte n’affecte aucune ligne qui les référence. » : écart pour le code d'un projet, qui arrive en EP-04 ;
  ici, l'adresse d'un compte.
- `WF-DAT-0060-A` — « Deux instances des services insérant simultanément ne produisent jamais le même identifiant. »
- `WF-DAT-0060-A` — « Un identifiant n’apparaît dans aucune URL sous une forme séquentielle. »
- écart : `WF-DAT-0070-A` — « Après modification d’une tâche par un utilisateur, la ligne porte son compte et l’horodatage de la modification. » : la tâche arrive en EP-06 ; ici, la même
  phrase se constate sur un compte modifié par un administrateur.
- écart : `WF-DAT-0070-A` — « Une ligne créée par un import porte le compte qui l’a confirmé. » : l'import arrive en EP-09, qui clôt l'exigence.
- `WF-DAT-0070-A` — « Une ligne mise à jour par un traitement automatique porte la plateforme comme auteur. » : constaté sur un compte mis à jour par la lecture des
  comptes du fournisseur (US-0370).
- écart : `WF-DAT-0080-A` — « La suppression d’un sous-projet non référencé le retire de la base. » : le sous-projet arrive en EP-04.
- écart : `WF-DAT-0080-A` — « Celle d’un sous-projet référencé par une révision marquée le marque supprimé : la révision l’affiche toujours, la saisie ne le propose plus. » : EP-04.
- `WF-DAT-0080-A` — « Aucune commande ne supprime physiquement un rôle de ressource, un rôle d’habilitation ou un compte. » : pour le compte et le rôle
  d'habilitation ; le rôle de ressource arrive en EP-05, qui le constate pour lui.
- écart : `WF-DAT-0090-A` — « L’insertion d’une ligne de devis référençant une catégorie inexistante est rejetée par la base. » : le devis arrive en EP-07, qui clôt
  l'exigence.
- écart : `WF-DAT-0090-A` — « L’insertion de deux sous-projets de même code dans un projet est rejetée par la base, avant toute règle des services. » : EP-04.
- écart : `WF-DAT-0090-A` — « La suppression d’une tâche de la révision en cours entraîne ses lignes et ses liaisons, et rien d’autre. » : EP-06.
- écart : `WF-DAT-0090-A` — « La suppression d’un lot cité par une révision marquée le marque supprimé, retire le rattachement de la tâche de la révision en cours et laisse celui de la révision marquée. » : le lotissement arrive en EP-04 et le
  rattachement en EP-06 ; EP-07, qui clôt l'exigence, le constate.
- propre à l'US : sur les tables de cet EPIC, toute relation est une clé étrangère déclarée
  en refus par défaut, l'état d'un compte est une contrainte de vérification, et l'unicité de
  l'adresse électronique est déclarée en base : deux comptes de même adresse sont rejetés par
  la base, avant toute règle des services (WF-DAT-0090).
- écart : `WF-DAT-0100-A` — « La somme des montants budgétés d’une révision est identique quel que soit l’ordre de sommation. » et « Un montant de 0,10 additionné dix fois donne exactement 1,00. » : les sommes du noyau
  arrivent en EP-07, qui clôt l'exigence.
- écart : `WF-DAT-0100-A` — « Une tâche planifiée au 30 juin s’affiche au 30 juin sur tout poste client, quel que soit son fuseau. » et « Deux tâches de quatre heures liées fin à début, sur un calendrier de huit heures, commencent et finissent le même jour. » : le planning arrive en
  EP-06 ; l'affichage est déjà celui d'EP-02.
- propre à l'US : les horodatages d'audit sont conservés en temps universel (WF-DAT-0100).
- écart : `WF-DAT-0140-A` — « Une installation en version N passe en version N+1 sans interruption de service ni perte de données. » : la mise à jour sans interruption relève du
  déploiement — EP-13.
- `WF-DAT-0140-A` — « Une migration déjà appliquée ne se rejoue pas. »
- écart : `WF-DAT-0140-A` — « Après une suite de migrations, les montants et les indicateurs conservés d’une révision marquée antérieure sont inchangés. » : la révision marquée arrive en EP-04 ; EP-13 le
  constate.
- écart : `WF-SEC-0010-A` — « Aucune connexion en clair n'est acceptée par un composant de la plateforme, hors le point de métriques, qui n'est pas joignable hors du cluster. » et « Une recherche des secrets connus dans le dépôt, les images publiées et les journaux ne les trouve pas. » : le chiffrement des
  échanges et la publication des images relèvent d'EP-13.
- `WF-SEC-0010-A` — « Le démarrage d'un service sans les secrets attendus échoue en le disant, plutôt que de démarrer sans. »
- écart : `WF-OBS-0020-A` — « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul identifiant, que le message présenté à l'utilisateur contient. » : l'import arrive en EP-06 ; ici,
  une tâche de lecture des comptes échouée se suit de la requête qui l'a lancée à son échec
  par un seul identifiant, que l'enveloppe d'erreur (`Problem.correlation_id`) contient.
- `WF-OBS-0020-A` — « Une recherche des secrets et des jetons connus dans les journaux ne les trouve pas. »
- propre à l'US : les règles de codage du SQL et des migrations sont un troisième fichier de
  règles, à côté de ceux de Python et de TypeScript, et le guide a ses sections « l'écriture
  d'une migration » et « ajouter un code côté service » ; `make roadmap` passe sur les
  commandes qu'elles citent.

**Notes de réalisation.** La première table est celle des comptes (`user_account`, §4.4.1) ;
les tables des rôles, des permissions et du journal d'audit suivent dans leurs US. Les
décimaux exacts n'ont pas encore de grandeur à porter : la convention s'écrit dans les règles
SQL, et EP-07 la constate.

**Hors périmètre.** Le chiffrement des connexions et l'injection des secrets par la
plateforme — EP-13.

## US-0340 — Réponses conformes au contrat, parcours contre le service

- **statut** : à faire
- **exigences** : `WF-ARC-0060-A`
- **opérations** : aucune en propre — toutes celles que sert le service
- **issue** : #429

**En tant que** développeur, **je veux** que la chaîne compare chaque réponse du service au
schéma déclaré, et que les parcours de bout en bout se jouent contre le vrai service, **afin
qu'**un écart entre le service et le contrat échoue avant la fusion, et qu'une exigence close
par le back soit prouvée par un parcours qui le traverse.

**Critères d'acceptation.**

- `WF-ARC-0060-A` — « Le client du front est régénéré à partir du contrat sans retouche à la main. »
- `WF-ARC-0060-A` — « Une réponse de l’API qui ne correspond pas au schéma déclaré fait échouer la chaîne. »
- `WF-ARC-0060-A` — « Aucun endpoint ne répond qui ne figure au contrat. »
- propre à l'US : les parcours de bout en bout se jouent contre le service quand
  `WATERFALL_API_ADDRESS` le désigne, sans faux back, à côté de ceux qui se jouent contre le
  faux back ; le relevé des exigences (`make requirements`) compte un parcours joué contre le
  service comme une preuve du back, et non plus du seul front.

**Notes de réalisation.** EP-01 a désigné l'outil du faux back, en mode proxy devant le
service (US-0030) ; `fields` de `listNodes` est la seule réponse dont le schéma ne dit pas
tout (DECISIONS.md, « Listes et grilles ») et la vérification doit le savoir dès qu'EP-06 la
sert.

## US-0350 — Se connecter par le fournisseur d'identité

- **statut** : à faire
- **exigences** : `WF-ARC-0030-A`, `WF-ADM-0140-A`, `WF-ADM-0180-A`, `WF-SEC-0020-A`
- **opérations** : `getMe`, `closeMySessions`, `createPasswordSetupLink`
- **issue** : #427

**En tant que** chef de projet, manager ou administrateur, **je veux** me connecter avec le
compte que j'ai — local, de l'annuaire ou d'un fournisseur externe —, sans que Waterfall ne
voie jamais mon mot de passe, et que ma déconnexion ou la désactivation de mon compte
prennent effet partout à la requête suivante, **afin d'**entrer dans Waterfall comme
j'entre déjà dans les autres outils de l'entreprise.

**Critères d'acceptation.**

- `WF-ARC-0030-A` — « Un compte local, un compte de l’annuaire et un compte venu d’un fournisseur externe obtiennent chacun un jeton, et agissent selon leurs rôles dans Waterfall. »
- `WF-ARC-0030-A` — « Un jeton d’accès expiré, ou signé par une autre clé, est refusé. »
- `WF-ARC-0030-A` — « Un jeton de rafraîchissement déjà employé est refusé. »
- `WF-ARC-0030-A` — « Le retrait d’un rôle prend effet à la requête suivante, sans attendre l’expiration du jeton. »
- `WF-ARC-0030-A` — « Le navigateur ne détient aucun jeton. »
- `WF-ADM-0140-A` — « Un compte importé n’a pas d’écran de mot de passe et se connecte avec ses identifiants d’annuaire. »
- `WF-ADM-0140-A` — « Un mot de passe de onze caractères est refusé, de même que l’adresse du compte. »
- `WF-ADM-0140-A` — « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes. »
- `WF-ADM-0140-A` — « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé. »
- `WF-ADM-0140-A` — « Un compte créé par un administrateur ne peut pas se connecter avant que son porteur n’ait fixé son mot de passe par le lien reçu ou remis. »
- `WF-ADM-0140-A` — « Aucun écran de Waterfall ne demande, n’affiche ni ne permet de saisir un mot de passe ; le lien de fixation est le seul élément d’authentification qu’il présente. »
- `WF-ADM-0180-A` — « Sur une installation sans annuaire ni fournisseur externe, un compte local se connecte. »
- `WF-ADM-0180-A` — « Après fédération d’un annuaire, un compte de l’annuaire se connecte avec ses identifiants d’annuaire et un compte local avec son mot de passe. »
- `WF-ADM-0180-A` — « Avec un fournisseur externe, la première connexion d’une personne inconnue crée son compte, sans rôle, et elle n’a aucun droit tant qu’un rôle ne lui est pas donné. »
- `WF-ADM-0180-A` — « Après retrait de l’annuaire, les comptes qui en venaient existent toujours et ne peuvent plus se connecter tant qu’aucun fournisseur ne les reconnaît. »
- `WF-ADM-0180-A` — « Aucun écran de Waterfall ne paramètre un annuaire. »
- `WF-SEC-0020-A` — « La désactivation d'un compte connecté sur deux postes interrompt les deux à leur requête suivante. »
- `WF-SEC-0020-A` — « Un jeton de rafraîchissement inactif au-delà de deux heures est refusé, et l'utilisateur est ramené à l'écran de connexion puis, reconnecté, à l'écran visé. »
- `WF-SEC-0020-A` — « Un utilisateur qui se déconnecte ne peut plus agir avec ses jetons. »
- propre à l'US — **retour à l'écran visé** : la session expirée ramène à la page de
  connexion du fournisseur d'identité, puis, reconnecté, à l'écran visé avec son adresse
  entière, paramètres compris, et cela pour un compte local, un compte de l'annuaire comme
  pour un compte d'un fournisseur externe, que Keycloak relaie (WF-SEC-0020, #152). L'adresse
  visée est gardée côté serveur, liée à l'état de la demande d'authentification, et seule une
  adresse du front y est acceptée : un retour vers un autre site est refusé et mène à
  l'accueil.
- propre à l'US : une session expirée pendant une écriture — une cellule saisie, une
  commande — ne perd rien en silence : l'écriture n'est pas appliquée, et l'écran le dit
  avant de mener à la connexion ; une session expirée sur une page ouverte, sans action de
  l'utilisateur, le ramène à la connexion à sa requête suivante.
- propre à l'US : un utilisateur habilité obtient, pour un compte local actif, le lien de
  fixation du mot de passe, valable une heure et à usage unique, le précédent cessant de
  valoir ; la demande est inscrite au journal d'audit, sans le jeton (WF-ADM-0140,
  WF-SEC-0030).

**Notes de réalisation.** Les décisions de #215 sont le point de départ : `openid-client`
côté serveur Next, un témoin opaque dans le navigateur, les jetons et un verrou de
rafraîchissement par session dans Redis ; le royaume `waterfall` versionné dans le dépôt et
appliqué de façon idempotente par keycloak-config-cli ; la base de Keycloak distincte, sur le
même serveur PostgreSQL. La plateforme de développement porte un annuaire et un fournisseur
externe de test, pour que la Définition de fini se constate. Cette US ferme #152 et #155,
sans objet : la page de connexion n'a plus de liste de fournisseurs à présenter, et les
règles du mot de passe sont celles du fournisseur, qui les dit sur sa page.

**Hors périmètre.** Les écrans de mot de passe de la maquette (US-0320) : ils disparaissent.

## US-0360 — Comptes : la table des comptes et l'affectation des rôles

- **statut** : à faire
- **exigences** : `WF-ADM-0050-A`, `WF-ADM-0060-A`, `WF-IHM-0130-A`
- **opérations** : `listUsers`, `createUser`, `getUser`, `updateUser`, `setUserActivation`,
  `setUserAccessRoles`, `listAccessRoles`
- **issue** : #433

**En tant qu'**administrateur, **je veux** voir tous les comptes de l'installation dans une
table, y créer un compte local, corriger ce que Waterfall garde d'un compte, lui affecter ses
rôles d'habilitation, le désactiver et le réactiver, **afin que** chacun puisse entrer avec
les droits qu'on lui a donnés, et qu'une personne partie ne le puisse plus sans que ses actes
cessent d'être attribuables.

**Critères d'acceptation.**

- `WF-ADM-0050-A` — « La création d’un compte sans nom, sans prénom ou sans adresse est refusée, de même que celle d’un compte dont l’adresse est déjà portée par un autre. »
- `WF-ADM-0050-A` — « Le nom, le prénom et l’adresse d’un compte de l’annuaire ou d’un fournisseur externe ne sont pas modifiables dans Waterfall. »
- `WF-ADM-0060-A` — « Aucun écran ne propose de supprimer un compte. »
- `WF-ADM-0060-A` — « La connexion d’un compte désactivé est refusée. »
- écart : `WF-ADM-0060-A` — « Une révision marquée par un compte depuis désactivé affiche toujours son auteur. » : la révision marquée arrive en EP-04, qui clôt
  l'exigence ; ici, un compte désactivé reste nommé partout où il est cité, dans les colonnes
  d'audit des comptes et des rôles qu'il a écrits.
- `WF-ADM-0060-A` — « Un compte réactivé se connecte de nouveau avec ses rôles d’avant. »
- `WF-ADM-0060-A` — « Après anonymisation d’un compte désactivé, aucun écran ne présente plus son nom ni son adresse ; les révisions qu’il a marquées affichent le libellé neutre comme auteur ; sa réactivation est refusée. » : pour les écrans des comptes, l'auteur
  des colonnes d'audit et le refus de réactivation ; la révision marquée arrive en EP-04, qui
  clôt l'exigence.
- propre à l'US : la table des comptes liste les comptes de l'installation, actifs et
  désactivés, chacun avec son nom, son prénom, son adresse, son origine, son rattachement,
  ses rôles d'habilitation nommés par le serveur et son état (WF-ADM-0050).
- propre à l'US — **pagination** : la table se lit par pages de cinquante comptes, la taille
  par défaut de `limit` ; elle annonce le nombre de comptes retenus (`meta.total`) et la page
  lue, et mène à la précédente et à la suivante. Une page demandée au-delà de la dernière est
  vide et annonce le même total. Changer le tri ou un filtre ramène à la première page.
- propre à l'US — **tri** : chaque colonne se trie dans les deux sens, par le serveur
  (`sort_by`, `sort_order`, WF-IHM-0060), une colonne à la fois ; sans tri choisi, le nom
  puis le prénom, croissants. Les textes se comparent dans l'ordre des points de code
  Unicode ; les rôles, par leurs libellés dans l'ordre où le compte les porte ; un compte sans
  rattachement vient après les autres, et un compte désactivé après les actifs, dans l'ordre
  croissant. À valeurs égales, l'ordre est le même d'une page à l'autre : aucun compte n'est
  lu deux fois ni sauté en tournant les pages.
- propre à l'US : la table des comptes est sa propre saisie, pour qui porte `users.write` —
  nom et prénom d'un compte local en champs, état sur un interrupteur, rôles dans une liste à
  choix multiple des rôles de l'installation — ; « Créer un compte local » est dans son
  en-tête. Un refus s'y dit par le catalogue des codes d'erreur (#379).
- propre à l'US : l'affectation des rôles s'y fait cellule par cellule — zéro, un ou plusieurs
  rôles (WF-ADM-0050) — et s'applique sans reconnexion du compte concerné (WF-ADM-0090) ; le
  retrait de son rôle au dernier administrateur y est refusé par `LAST_ADMINISTRATOR`
  (WF-ADM-0120), et sa désactivation présentée indisponible, avec la condition
  `last_administrator` que portent les commandes du compte (`available_commands`, WF-IHM-0090,
  contrat d'EP-02/L42d) ; les rôles proposés sont ceux de l'installation, quel que soit le
  rattachement (WF-ADM-0030, #379).
- propre à l'US — **filtres** : la table se filtre sur chacune de ses colonnes, par le
  serveur (WF-IHM-0130) : le nom, le prénom et l'adresse par une recherche qui porte sur les
  trois ; l'origine, les rôles et l'état par des choix multiples ; le rattachement à partir
  d'EP-05. Les filtres se combinent entre eux et avec le tri ; le nombre de comptes annoncé
  et les pages sont ceux que les filtres retiennent.
- propre à l'US : le tri et les filtres choisis sont conservés comme préférence d'affichage
  de la table, retrouvés à la réouverture et propres à chaque utilisateur (WF-IHM-0060,
  constatée par US-0400).
- écart : `WF-IHM-0130-A` — « La liste des projets filtrée sur un état ne compte que les projets de cet état dans ses totaux. » : la liste des projets arrive en EP-04 ; EP-11, qui clôt
  l'exigence, le constate.
- écart : `WF-IHM-0130-A` — « Le plan de charge d’un projet exporté est une image PNG qui porte le nom du projet, la révision et la date de calcul ; le plan de charge agrégé exporté porte le périmètre et la date de calcul. » : le plan de charge arrive en EP-07 ; l'export, en EP-11.

**Notes de réalisation.** Un compte local est créé dans Waterfall et dans le fournisseur
d'identité, par son API d'administration (WF-ADM-0070, dernière phrase du corps), dont le
Vérif est constaté par US-0370. La désactivation révoque les sessions du compte chez le
fournisseur (WF-SEC-0020). L'ordre des colonnes et la forme de la saisie en ligne sont ceux
que #379 consigne. Les règles de l'affectation — union des permissions, application
immédiate, dernier administrateur — sont celles d'US-0380, dont les critères les constatent ;
cette US porte la table qui les exerce.

**Hors périmètre.** La colonne du
rattachement reste en lecture, vide, jusqu'à EP-05, qui crée l'arbre.

## US-0370 — Lecture des comptes du fournisseur, worker et file

- **statut** : à faire
- **exigences** : `WF-ADM-0070-A`, `WF-ARC-0090-A`
- **opérations** : `startDirectorySync`, `getLatestDirectorySync`, `getBackgroundTask`,
  `listBackgroundTasks`
- **issue** : #434

**En tant qu'**administrateur, **je veux** que Waterfall connaisse les comptes du fournisseur
d'identité avant leur première connexion, à ma demande et à intervalle régulier, sans leur
donner de droit, **afin de** pouvoir inscrire une personne comme contributeur sans attendre
qu'elle se soit connectée.

**Critères d'acceptation.**

- `WF-ADM-0070-A` — « Après synchronisation, chaque personne de l’annuaire retenue a un compte actif dans Waterfall, sans rôle si elle n’en avait pas, avant toute connexion. »
- écart : `WF-ADM-0070-A` — « Une personne retirée de l’annuaire voit son compte désactivé à la synchronisation suivante, et ses actes restent consultables. » : le compte est désactivé ici ; ses actes —
  révisions marquées, contributeurs inscrits — arrivent en EP-04, qui clôt l'exigence.
- `WF-ADM-0070-A` — « Le dernier compte administrateur, retiré de l’annuaire, reste actif et la synchronisation le signale. »
- `WF-ADM-0070-A` — « Un compte local créé depuis Waterfall existe dans le fournisseur d’identité. »
- `WF-ADM-0070-A` — « Une personne ajoutée à l’annuaire a un compte dans Waterfall au terme de la périodicité choisie, sans intervention. » : la périodicité est celle de la
  tâche planifiée de lecture, quotidienne par défaut.
- écart : `WF-ARC-0090-A` — « Le marquage d’une révision de dix mille objets n’immobilise aucune requête au-delà de la création de la tâche, et l’utilisateur en voit l’aboutissement. » : le marquage arrive en EP-04 ; ici, la lecture
  des comptes ne tient aucune requête au-delà de la création de la tâche, et l'utilisateur en
  voit l'aboutissement.
- `WF-ARC-0090-A` — « L’arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après redémarrage. » : constaté sur la lecture des comptes.
- `WF-ARC-0090-A` — « Aucun de ces traitements n’est joignable par un endpoint qui répondrait après l’avoir exécuté. » : pour la lecture des comptes ; EP-13 le constate pour
  tous les traitements.
- propre à l'US : la lecture se dépose en file à l'intervalle que fixe la configuration de
  l'installation, et le worker la prend comme celle qu'un administrateur demande (PBS-5.3).

**Notes de réalisation.** Le worker et la file servent ensuite le marquage (EP-04), les
imports (EP-06, EP-07, EP-09) et la sauvegarde planifiée (EP-13) : le genre d'une tâche est déjà une
énumération du contrat (`BackgroundTaskRef.kind`).

## US-0380 — Rôles d'habilitation et catalogue des permissions

- **statut** : à faire
- **exigences** : `WF-ADM-0010-A`, `WF-ADM-0020-A`, `WF-ADM-0090-A`, `WF-ADM-0100-A`,
  `WF-ADM-0120-A`, `WF-INTF-0030-A`
- **opérations** : `listPermissions`, `listAccessRoles`, `createAccessRole`, `getAccessRole`,
  `updateAccessRole`, `deleteAccessRole`, `setUserAccessRoles` (servie avec US-0360)
- **issue** : #431

**En tant qu'**administrateur, **je veux** composer des rôles à partir du catalogue, les
attribuer aux comptes, et modifier ou supprimer les trois rôles livrés, sans jamais pouvoir
retirer à l'installation son dernier administrateur, **afin que** l'entreprise répartisse les
droits selon son organisation, et non selon celle que le logiciel imagine.

**Critères d'acceptation.**

- `WF-ADM-0010-A` — « Sur une installation neuve, les trois rôles existent et leurs permissions couvrent les usages des exigences citées. »
- `WF-ADM-0010-A` — « Un administrateur en renomme un, en modifie les permissions et le supprime, sans erreur. »
- écart : `WF-ADM-0020-A` — « Un rôle d’habilitation composé sur mesure permet à un utilisateur de cumuler des permissions relevant de deux acteurs différents. » : ici, les permissions effectives d'un
  utilisateur portent celles des deux acteurs ; l'exercice des deux attend la première action
  d'un autre acteur que l'administrateur — EP-05, qui clôt l'exigence.
- `WF-ADM-0020-A` — « Réciproquement, un rôle privé d’une permission empêche l’action correspondante, quel que soit l’acteur auquel l’utilisateur ressemble. » : constaté sur les actions d'administration.
- `WF-ADM-0090-A` — « Un utilisateur portant deux rôles dispose des permissions des deux. »
- `WF-ADM-0090-A` — « Le retrait d’une permission à un rôle en prive tous ses porteurs sans qu’ils aient à se reconnecter. »
- `WF-ADM-0090-A` — « La suppression d’un rôle est refusée tant qu’un compte le porte. »
- `WF-ADM-0090-A` — « Un rôle supprimé n’apparaît plus dans la liste des rôles ni dans les choix d’attribution ; l’inscription du journal d’audit qui l’attribuait à un compte le nomme toujours. » : l'inscription est celle d'US-0410.
- `WF-ADM-0100-A` — « Chaque fonction de second niveau de l’arborescence est représentée par ses deux permissions, ou par la seule permission de consulter pour FBS-1.3, FBS-1.5 et FBS-2.1 à FBS-2.7. »
- écart : `WF-ADM-0100-A` — « Un rôle disposant de la modification du chiffrage mais non du marquage permet de modifier un devis et refuse de marquer la révision ; un rôle disposant du marquage mais non de la fusion refuse de fusionner un différentiel. » : le marquage arrive en EP-04, le devis en EP-07,
  la fusion en EP-08, qui clôt l'exigence.
- écart : `WF-ADM-0100-A` — « Un utilisateur sans la permission de créer un projet n’en crée pas. » : la création d'un projet arrive en EP-04.
- `WF-ADM-0100-A` — « Aucun écran ne permet de créer une permission. »
- `WF-ADM-0120-A` — « La désactivation du dernier compte administrateur est refusée, de même que le retrait de son rôle. »
- `WF-ADM-0120-A` — « Elle est acceptée dès qu’un second compte actif porte la permission. »
- écart : `WF-INTF-0030-A` — « Un utilisateur porteur du rôle prédéfini « administrateur » crée un compte, lui affecte un rôle d’habilitation (FBS-1.1, FBS-1.2), ouvre l’écran d’état du système (FBS-1.3), ouvre le journal d’audit et y applique un filtre (FBS-1.5), et déclenche une sauvegarde (FBS-1.4). » : la création d'un compte et l'affectation d'un
  rôle sont ici, le journal d'audit (US-0410) et le déclenchement d'une sauvegarde (US-0440) ;
  l'écran d'état arrive en EP-13, qui clôt l'exigence.
- propre à l'US — **pagination** : la table des rôles n'est pas paginée — `listAccessRoles`
  rend la liste entière, une installation comptant quelques dizaines de rôles — et elle
  annonce le nombre de rôles retenus.
- propre à l'US — **tri** : chaque colonne se trie dans les deux sens, par le serveur
  (`sort_by`, `sort_order`, WF-IHM-0060) : le libellé, la nature — les prédéfinis avant les
  composés dans l'ordre croissant — et le nombre de porteurs ; sans tri choisi, le libellé
  croissant, dans l'ordre des points de code Unicode.
- propre à l'US — **filtres** : la table se filtre sur chacune de ses colonnes, par le
  serveur : le libellé par la recherche, la nature (prédéfini ou composé), et les porteurs
  (rôles portés ou non par au moins un compte) ; les filtres se combinent avec le tri
  (WF-IHM-0130, constatée par US-0360). Le tri et les filtres choisis sont conservés comme
  préférence d'affichage de la table (WF-IHM-0060).
- propre à l'US — **matrice** : la matrice des permissions est le lieu de leur
  modification, une case par permission et par rôle ; ses lignes suivent l'ordre du catalogue,
  groupées par fonction de second niveau, et ses colonnes les rôles que la table retient, dans
  son ordre. La création, le renommage et la suppression se font dans la table (#380).
- propre à l'US : un rôle supprimé n'est plus lu ni attribuable, et sa ligne est conservée,
  ce que le journal d'audit et les attributions passées citent (WF-DAT-0080, décision du
  cadrage).

**Notes de réalisation.** Le contenu des trois rôles prédéfinis est celui que l'exemple
`access_roles` du contrat livre ; le catalogue est l'énumération `PermissionCode`, trois
permissions comprises depuis #384, et `audit_log.read`, la seule permission de FBS-1.5, en
lecture seule (WF-ADM-0100 révisée), que le rôle administrateur porte. La suppression d'un rôle est logique (décision du
cadrage, 2026-10-07) : WF-DAT-0080 ne laisse disparaître aucun objet de la plateforme, et
WF-ADM-0090 veut qu'un rôle se supprime ; une issue « Specification finding » propose de le
dire dans la spécification.

## US-0390 — Évaluation d'une action et permissions effectives

- **statut** : à faire
- **exigences** : `WF-ADM-0110-A`
- **opérations** : `getMe`
- **issue** : #432

**En tant que** chef de projet, manager ou administrateur, **je veux** que chaque action soit
évaluée contre mes permissions au moment où je la demande, et que le front sache ce que j'ai
le droit de faire, **afin de** ne jamais voir une commande qui me sera refusée, ni pouvoir
contourner un refus en appelant l'API.

**Critères d'acceptation.**

- écart : `WF-ADM-0110-A` — « Un utilisateur habilité à modifier le planning et porteur de « consulter tous les projets », mais non contributeur d’un projet, voit ce planning et ne peut pas le modifier, ni par la grille ni par import. » : le planning et les contributeurs arrivent en
  EP-04 et EP-06 ; EP-04 clôt l'exigence.
- écart : `WF-ADM-0110-A` — « Inscrit comme contributeur, il le modifie. » : EP-04.
- écart : `WF-ADM-0110-A` — « Un utilisateur sans la permission de consultation ne voit pas le projet, même contributeur ; un contributeur sans « consulter tous les projets » ne voit que ses projets. » : EP-04.
- écart : `WF-ADM-0110-A` — « Une adresse d’objet inexistant et une adresse d’objet non consultable mènent au même écran. » : constaté ici pour un compte et un rôle — une
  adresse inconnue et une adresse que l'appelant n'a pas la permission de consulter rendent
  la même réponse ; les objets d'un projet arrivent en EP-04.
- `WF-ADM-0110-A` — « Un utilisateur connaît la liste de ses permissions effectives, et elle change immédiatement lorsqu'un de ses rôles est modifié. »
- propre à l'US : une opération demandée sans sa permission est refusée par l'API, quel que
  soit ce que le front présente, et le refus nomme la permission manquante.

**Notes de réalisation.** L'évaluation est un module du noyau, que les EPIC suivants
appellent : la qualité de contributeur, second terme, s'y ajoute en EP-04.

## US-0400 — Mon compte : préférences, langue, avatar

- **statut** : à faire
- **exigences** : `WF-ADM-0040-A`, `WF-ADM-0080-A`, `WF-INTF-0160-A`, `WF-IHM-0060-A`
- **opérations** : `getMe`, `updateMyPreferences`, `putMyAvatar`, `deleteMyAvatar`,
  `getUserAvatar`, `getInstallation`
- **issue** : #435

**En tant que** chef de projet, manager ou administrateur, **je veux** que ma langue, mes
réglages de grille et mon avatar me suivent d'un poste à l'autre, **afin de** ne pas refaire
mes réglages à chaque connexion.

**Critères d'acceptation.**

- `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier celles d’un autre. »
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes données présentées selon leurs réglages respectifs. » : le projet arrive en EP-04, qui clôt
  l'exigence ; ici, deux utilisateurs ouvrant la table des comptes la voient selon leurs
  réglages respectifs.
- `WF-ADM-0080-A` — « Un utilisateur ajoute, remplace et retire son avatar sans intervention d’un administrateur. »
- `WF-ADM-0080-A` — « Il ne peut pas modifier celui d’un autre. »
- `WF-ADM-0080-A` — « Un compte sans avatar est affiché avec une image par défaut. »
- `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande l'anglais obtient l'interface en anglais à sa première connexion, un autre demandant le français l'obtient en français. »
- `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande une langue non offerte obtient la langue par défaut de l'installation. »
- `WF-INTF-0160-A` — « Un utilisateur qui force le français le retrouve en se connectant depuis un autre poste dont le navigateur demande l'anglais. »
- `WF-INTF-0160-A` — « Le changement de langue s'applique sans reconnexion. »
- `WF-IHM-0060-A` — « Chaque colonne d’une table plate se trie dans les deux sens. » : constaté sur les tables des comptes et des rôles,
  triées par le serveur.
- écart : `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose de tri ; dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans déplacer les tâches. » : l'absence de tri de la grille de planning est
  constatée par EP-02 ; le devis ordonné par le serveur arrive en EP-07, qui clôt
  l'exigence.
- écart : `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours visibles, de même que la colonne de libellé après défilement horizontal. » : constaté par EP-02 sur la maquette ; EP-07 le
  constate sur la grille servie.
- `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. »

**Notes de réalisation.** La langue choisie est aussi celle du compte chez le fournisseur
d'identité, qui envoie dans cette langue les courriels de mot de passe (WF-ARC-0110,
US-0410). `getInstallation` rend la langue par défaut posée à l'amorçage (US-0420).

## US-0410 — Journal d'audit, et aucun texte rendu par l'API

- **statut** : à faire
- **exigences** : `WF-SEC-0030-A`, `WF-ADM-0190-A`, `WF-ARC-0110-A`
- **opérations** : `listAuditEvents`, `listAuditFacets` — les écritures des comptes et des
  rôles l'alimentent
- **issue** : #430

**En tant qu'**administrateur, **je veux** que chaque création ou modification d'un compte,
d'un rôle ou d'une attribution soit inscrite dans un journal que la plateforme ne peut pas
réécrire, conservée sous forme de code et de données, et que je puisse parcourir et filtrer,
**afin de** pouvoir dire après coup qui a donné quel droit, dans la langue de celui qui le
relit.

**Critères d'acceptation.**

- `WF-SEC-0030-A` — « Chacune des actions énumérées produit une inscription datée et attribuée. » : pour les actions de cet EPIC — la création et la
  modification des comptes, des rôles et de leurs attributions, et la demande d'un lien de
  fixation ; les autres actions énumérées arrivent avec leur EPIC.
- `WF-SEC-0030-A` — « L'abandon d'une révision en cours et la suppression d'un rôle produisent chacun une inscription qui nomme l'action et l'objet. » : pour la suppression d'un rôle ; l'abandon
  d'une révision arrive en EP-04.
- `WF-SEC-0030-A` — « Aucun écran ni endpoint ne permet de modifier ou de supprimer une inscription. »
- `WF-SEC-0030-A` — « Une mise à jour ou une suppression exécutée directement en base sur une inscription du journal est rejetée par la base. »
- écart : `WF-SEC-0030-A` — « Le journal d'un projet terminé depuis cinq ans est toujours consultable. » : la consultation du journal est ici ; les projets
  et leur terminaison arrivent en EP-04, et la conservation se constate en EP-13, qui clôt
  l'exigence.
- écart : `WF-ADM-0190-A` — « Après le marquage d’une révision par un utilisateur, le journal filtré sur cet utilisateur et sur l’action de marquage présente une inscription datée du jour, qui nomme le projet et la révision. » : le marquage arrive en EP-04 ; constaté ici, filtré sur
  l'auteur et sur l'action, pour l'attribution d'un rôle.
- `WF-ADM-0190-A` — « Filtré sur un mois sans aucune action, il ne présente rien. »
- écart : `WF-ADM-0190-A` — « Une inscription sur un projet que le lecteur ne peut pas consulter nomme ce projet sans l’ouvrir. » : les projets arrivent en EP-04 ; EP-13, qui clôt
  l'exigence, le constate.
- `WF-ADM-0190-A` — « Aucune commande de la vue ne modifie ni ne supprime une inscription. »
- `WF-ADM-0190-A` — « Un utilisateur sans la permission de consulter FBS-1.5 n’atteint pas la vue. »
- écart : `WF-ADM-0190-A` — « Après une restauration, une inscription qui cite un projet créé après la sauvegarde s’affiche avec le libellé et le code de ce projet, sans mener à lui. » : la restauration est à US-0440 ; les projets
  arrivent en EP-04, et EP-13 le constate.
- `WF-ARC-0110-A` — « Aucune réponse de l'API ne contient de phrase destinée à l'utilisateur. »
- écart : `WF-ARC-0110-A` — « Un import fait par un utilisateur en français, relu par un utilisateur en anglais, présente son compte rendu en anglais. » : l'import arrive en EP-06, qui clôt l'exigence.
- `WF-ARC-0110-A` — « Le journal d'audit d'une même action se lit dans la langue de chaque lecteur. » : constaté sur la consultation du journal ; l'inscription est
  conservée sous forme de code et de données, sans phrase.
- `WF-ARC-0110-A` — « Un courriel de réinitialisation part du fournisseur d'identité, dans la langue du compte. »
- propre à l'US : le journal se consulte sous `audit_log.read`, en table plate, paginée, triée
  sur chacune de ses colonnes et filtrée par période, auteur, action, projet, objet,
  corrélation et libellé, par le serveur (FBS-1.5, WF-IHM-0060, WF-IHM-0130) ; aucune commande
  n'y modifie ni n'y supprime une inscription.

## US-0420 — Amorçage d'une installation neuve

- **statut** : à faire
- **exigences** : `WF-EXP-0020-A`
- **opérations** : aucune — l'amorçage est une commande d'installation, non une opération de
  l'API
- **issue** : #436

**En tant qu'**exploitant, **je veux** qu'une installation neuve crée d'elle-même ce sans quoi
personne ne peut entrer, et rien d'autre, et qu'elle me remette le lien par lequel le premier
administrateur fixe son mot de passe, **afin qu'**aucun mot de passe d'installation ne
traîne dans une procédure, et que la relancer soit sans danger.

**Critères d'acceptation.**

- `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le lien produit, se connecte, et dispose des trois rôles prédéfinis et du catalogue des permissions. »
- écart : `WF-EXP-0020-A` — « La création d’un projet est refusée et nomme les prérequis manquants, jusqu’à ce qu’une catégorie de coût de main-d’œuvre et un rôle de ressource aient été saisis. » : le référentiel arrive en EP-05 et la création
  d'un projet en EP-04, qui clôt l'exigence.
- `WF-EXP-0020-A` — « Une seconde exécution de l’installation ne crée ni compte, ni calendrier, ni nature supplémentaire ; elle produit un nouveau lien, qui remplace le précédent, tant que l’administrateur n’a pas fixé son mot de passe, et aucun lien ensuite. » : pour le compte et le lien ; le
  calendrier et la nature arrivent en EP-05, qui les ajoute à l'amorçage.
- `WF-EXP-0020-A` — « Le lien produit à l’installation est accepté plus d’une heure après sa production. »
- écart : `WF-EXP-0020-A` — « Sur une installation neuve, les bornes de probabilité valent 25 %, 50 % et 75 %, celles de gravité 1 %, 5 % et 10 %, les seuils 0,9 et 0,8 et le délai six semaines. » : les bornes, les seuils et le délai
  arrivent en EP-05, qui les ajoute à l'amorçage.
- propre à l'US : l'amorçage applique les migrations, crée le catalogue des permissions, les
  trois rôles prédéfinis, le compte administrateur local dans le fournisseur d'identité et
  dans Waterfall, et la langue par défaut de l'installation ; les libellés des rôles sont dans
  cette langue (WF-EXP-0020).

## US-0430 — Déployer une plateforme de démonstration

- **statut** : à faire
- **exigences** : `WF-ARC-0050-A`
- **opérations** : aucune en propre — l'empaquetage déploie celles que sert le service
- **issue** : #564

**En tant qu'**exploitant, **je veux** déployer Waterfall sur une machine seule, à partir
d'images que la chaîne publie, derrière un frontal HTTPS, **afin de** montrer le produit
à des utilisateurs sur une installation réelle, sans poste de développement.

**Critères d'acceptation.**

- écart : `WF-ARC-0050-A` — « Le chart s’installe sur un cluster vierge avec ses composants de données, et sur un cluster où PostgreSQL, Redis et le stockage objet sont fournis par des adresses et des secrets externes. » : le chart Helm arrive en EP-13, qui clôt
  l'exigence.
- écart : `WF-ARC-0050-A` — « Le passage de une à trois instances de l’API ne demande qu’un changement de paramètre et aucune interruption. » : EP-13.
- `WF-ARC-0050-A` — « Le fichier Compose démarre une plateforme complète sur une machine seule, à partir des mêmes images que le chart, et les tests de la chaîne CI/CD s’exécutent contre elle. » : pour le Compose, sur les images que la chaîne
  publie et que le chart d'EP-13 reprendra ; les parcours contre le service (US-0340) s'y
  jouent.
- propre à l'US : la chaîne construit et publie les images du front, de l'API et du worker —
  une même image, deux commandes — et celle de Keycloak avec son extension, sur ghcr.io,
  étiquetées par version et par commit de `main`, et par commit d'une branche d'EPIC pour les
  démonstrations ; aucune image ne contient de secret (WF-SEC-0010).
- propre à l'US : le Compose de production démarre sur une machine neuve, à partir d'un
  fichier de réglages et de secrets que l'exploitant remplit, la plateforme complète —
  frontal TLS, front, API, worker, planificateur, PostgreSQL, Redis, stockage objet, Keycloak
  et sa configuration — ; le frontal obtient seul ses certificats pour le nom de la machine, et
  le navigateur ne parle qu'en HTTPS (WF-SEC-0010) ; l'amorçage (US-0420) s'y lance par une
  commande, qui rend le lien de fixation du premier administrateur.
- propre à l'US : une notice de déploiement dit, pas à pas, comment installer, amorcer,
  mettre à jour et arrêter une plateforme de démonstration.

**Notes de réalisation.** Décisions de l'auteur du 2026-10-09 : images publiées par la
chaîne, frontal Caddy avec certificats Let's Encrypt. Sans messagerie sur une démonstration,
les liens de fixation se remettent par `createPasswordSetupLink` (WF-CMP-0030).

**Hors périmètre.** Le chart Helm, plusieurs instances de l'API, le chiffrement entre les
services, la mise à jour sans interruption — EP-13.

## US-0440 — Sauvegarder et restaurer la plateforme

- **statut** : à faire
- **exigences** : `WF-ADM-0150-A`, `WF-ADM-0160-A`, `WF-DAT-0120-A`
- **opérations** : `listBackups`, `startBackup`, `getBackup`, `downloadBackup`, `startRestore`,
  `uploadFile`
- **issue** : #565

**En tant qu'**administrateur, **je veux** sauvegarder la plateforme, télécharger la
sauvegarde, et la restaurer ici ou sur une autre installation, **afin de** remettre une
installation dans un état connu, ou d'en reproduire une — son référentiel, ses comptes, ses
réglages — sur une autre machine.

**Critères d'acceptation.**

- `WF-ADM-0150-A` — « Une sauvegarde déclenchée apparaît dans la liste avec sa date, sa taille et une vérification réussie. »
- `WF-ADM-0150-A` — « Elle peut être téléchargée ou copiée vers un emplacement externe. » : par le téléchargement ; la copie vers un
  emplacement externe paramétré relève de la planification — EP-13.
- écart : `WF-ADM-0160-A` — « Après restauration d’une sauvegarde, la plateforme présente exactement les projets, révisions et comptes qu’elle contenait à la date de la sauvegarde, et rien de postérieur, hors le journal d’audit, qui garde ses inscriptions et nomme la restauration. » : constaté ici pour les comptes, les rôles
  et le référentiel présent ; les projets et les révisions arrivent en EP-04, qui clôt
  l'exigence.
- `WF-ADM-0160-A` — « La confirmation nomme la date de la sauvegarde. »
- `WF-ADM-0160-A` — « Aucune restauration partielle n’est proposée. »
- `WF-ADM-0160-A` — « Une inscription faite après la sauvegarde est encore présente après la restauration, et la dernière inscription est la restauration elle-même. »
- écart : `WF-DAT-0120-A` — « Après application ou abandon d’un import, le fichier correspondant n’est plus sur le stockage objet. » : les imports arrivent en EP-06, qui clôt
  l'exigence.
- écart : `WF-DAT-0120-A` — « Un fichier déposé et jamais confirmé disparaît au terme du délai d’expiration. » : EP-06.
- écart : `WF-DAT-0120-A` — « Un export téléchargé jusqu’au bout n’est plus sur le stockage objet ; un téléchargement interrompu le laisse disponible ; un export jamais téléchargé en disparaît au terme de vingt-quatre heures. » : les exports arrivent en EP-06.
- propre à l'US : une sauvegarde couvre les deux bases, Waterfall et le fournisseur
  d'identité, chacune dans un état cohérent, sauf le journal d'audit, qui reste hors de ce
  qu'une restauration remplace et y inscrit la restauration une fois faite (WF-ADM-0160) ; elle
  vit dans le compartiment des sauvegardes du stockage objet (WF-DAT-0120).
- propre à l'US : une sauvegarde prise sur une installation, téléchargée, puis déposée sur une
  autre installation de même version ou plus récente et restaurée, y rend les comptes, les
  rôles et les réglages de la première, et l'administrateur de la première s'y connecte ; une
  sauvegarde d'une version plus récente que l'installation est refusée.
- propre à l'US : pendant une restauration, les utilisateurs sont déconnectés, et l'écran le
  dit ; les écrans de la sauvegarde de la maquette sont branchés sur le service.

**Notes de réalisation.** Décision de l'auteur du 2026-10-09 : on reproduit une installation
par une restauration entière, conformément à WF-ADM-0160 ; aucun échange partiel du
référentiel n'existe (WF-INTF-0150). Le dépôt d'une sauvegarde volumineuse (#350) se fait par
morceaux (conception).

**Hors périmètre.** La planification, la rétention, la sauvegarde marquée à conserver, la
copie vers un emplacement externe, le test de restauration périodique et l'alerte d'échec —
EP-13.

---
id: EP-03
titre: Se connecter, et n'agir que dans les limites de ses habilitations
statut: à planifier
depend_de: EP-01
issue:
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
- le journal d'audit, pour les comptes, les rôles et leurs attributions ;
- les journaux structurés du service et du worker, dès leur premier enregistrement :
  l'identifiant de corrélation engendré à l'entrée et transmis aux tâches, l'auteur, la
  gravité, et aucun mot de passe, jeton ni secret — faute de quoi tout le code d'EP-04 à
  EP-12 s'écrirait sans eux et serait à reprendre ;
- l'amorçage d'une installation neuve : catalogue, rôles prédéfinis, compte administrateur
  et son lien de fixation, langue par défaut ;
- la comparaison, par la chaîne, des réponses de l'API au schéma déclaré, et les parcours de
  bout en bout joués contre le vrai service (`WATERFALL_API_ADDRESS`), qui comptent alors au
  relevé des exigences comme preuve du back ;
- les écrans de connexion, de mon compte, des comptes et des rôles de la maquette, branchés
  sur le service : la saisie en ligne de la table des comptes (#379) et la matrice des
  permissions comme lieu de la modification des rôles (#380).

## Ce qui n'en fait pas partie

- le rattachement d'un compte à un nœud d'organisation (WF-ADM-0030) — EP-05, qui crée
  l'arbre ; ici, `org_node_id` reste nul et le filtre `org_node_id` de `listUsers` ne retient
  rien ;
- la qualité de contributeur, second terme de l'évaluation d'une action — EP-04 ;
- l'écran d'accueil (WF-IHM-0120) — EP-04, qui sert la liste des projets et les
  contributeurs ; ici, la connexion mène à l'accueil tel que la maquette le présente ;
- la garde des lectures du référentiel avec `include_inactive` (#351) — EP-05, qui les sert ;
- l'écran d'état, la sauvegarde et la restauration, qui complètent les usages de
  l'administrateur (WF-INTF-0030) — EP-13 ; la consultation du journal d'audit — EP-13 ;
- le chiffrement des échanges et l'injection des secrets par la plateforme — EP-13. Ici, un
  service qui démarre sans ses secrets échoue en le disant, et c'est tout ;
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
| `WF-ARC-0110-A` | Le texte est rendu au plus près du lecteur | début — close en EP-13 | US-0410 |
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
| `WF-OBS-0020-A` | Journaux structurés et corrélation | début — close en EP-13 | US-0330 |

Décisions du cadrage, 2026-10-07, sur des phrases de Vérif que cet EPIC ne peut pas
constater faute des objets d'un EPIC ultérieur : WF-IHM-0120 passe entière en EP-04 ;
WF-ADM-0060 et WF-ADM-0070 se closent en EP-04 (une révision marquée, des actes
consultables) ; WF-ADM-0100 en EP-08 (le devis, le marquage, la création d'un projet, puis la
fusion, dernière action gardée) ; WF-ADM-0020 en EP-05 (la première action d'un autre acteur
que l'administrateur) ; WF-ADM-0040 en EP-04 (« le même projet ») ; WF-IHM-0060 en EP-07 (le
tri de la grille de devis, qu'EP-02 attribuait à tort à EP-03) ; WF-ARC-0110 en EP-13, où le
journal d'audit se consulte, et non plus en EP-12. Les tableaux des EPIC concernés le disent.

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
- retirées : `listAuthProviders`, `getCurrentSession`, `openSession`, `closeSession`,
  `startOidcSession`, `completeOidcSession`, `requestPasswordReset`, `confirmPasswordReset`,
  `changeMyPassword`, et les schémas qu'elles seules emploient ; les permissions effectives,
  que `Session` portait, passent à `getMe` ;
- `createPasswordSetupLink` reste, son lien menant à la page du fournisseur qui fixe le mot
  de passe, et non plus à `/login/reset` du front ;
- `startDirectorySync` et `getLatestDirectorySync` lisent les comptes du fournisseur
  d'identité, non l'annuaire, et leur chemin le dit (`identity-syncs`) ; le compte rendu
  nomme ses signalements par un code du catalogue ;
- les refus par champ des écritures d'un compte qui manquent : rôle ou nœud inconnu, nom
  d'un compte fédéré (#379).

Servies ici pour la première fois, après cette modification (24) :

- `system` : `getLiveness`, `getInstallation`, `getBackgroundTask`, `listBackgroundTasks` ;
- `me` : `getMe`, `updateMyPreferences`, `putMyAvatar`, `deleteMyAvatar` ;
- `users` : `listUsers`, `createUser`, `getUser`, `updateUser`, `setUserActivation`,
  `setUserAccessRoles`, `createPasswordSetupLink`, `getUserAvatar`, `startDirectorySync`,
  `getLatestDirectorySync` ;
- `access` : `listPermissions`, `listAccessRoles`, `createAccessRole`, `getAccessRole`,
  `updateAccessRole`, `deleteAccessRole`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (0) :

aucune.

## Préalables

EP-01 livré. Le contrat d'EP-02 stabilisé : le premier lot ne démarre pas avant la fusion
d'EP-02/L30 (#393) dans `epic/EP-02`, au mieux après la livraison d'EP-02 dans `main`, dont
la branche `epic/EP-03` sera tirée. Les écrans que cet EPIC branche viennent d'EP-02 : s'il
n'est pas livré, les US d'écran attendent et le reste avance.

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
  contre le service réel, et le relevé des exigences le compte comme preuve du back.

## Conception

*À écrire à l'étape 2, après validation des US.*

---

## US-0330 — Service, base et conventions de données

- **statut** : à faire
- **exigences** : `WF-DAT-0060-A`, `WF-DAT-0070-A`, `WF-DAT-0080-A`, `WF-DAT-0090-A`,
  `WF-DAT-0100-A`, `WF-DAT-0140-A`, `WF-SEC-0010-A`, `WF-OBS-0020-A`
- **opérations** : `getLiveness`
- **issue** :

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
- `WF-DAT-0080-A` — « Aucune commande ne supprime physiquement un rôle de ressource ou un compte. » : pour le compte ; le rôle de ressource arrive en
  EP-05, qui le constate pour lui.
- écart : `WF-DAT-0090-A` — « L’insertion d’une ligne de devis référençant une catégorie inexistante est rejetée par la base. » : le devis arrive en EP-07, qui clôt
  l'exigence.
- écart : `WF-DAT-0090-A` — « L’insertion de deux sous-projets de même code dans un projet est rejetée par la base, avant toute règle des services. » : EP-04.
- écart : `WF-DAT-0090-A` — « La suppression d’une tâche de la révision en cours entraîne ses lignes et ses liaisons, et rien d’autre. » : EP-06.
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
- écart : `WF-SEC-0010-A` — « Aucune connexion en clair n'est acceptée par un composant de la plateforme. » et « Une recherche des secrets connus dans le dépôt, les images publiées et les journaux ne les trouve pas. » : le chiffrement des
  échanges et la publication des images relèvent d'EP-13.
- `WF-SEC-0010-A` — « Le démarrage d'un service sans les secrets attendus échoue en le disant, plutôt que de démarrer sans. »
- écart : `WF-OBS-0020-A` — « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul identifiant, que le message présenté à l'utilisateur contient. » : l'import arrive en EP-09 et EP-12 ; ici,
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
- **issue** :

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
- **opérations** : `getMe`, `createPasswordSetupLink`
- **issue** :

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

## US-0360 — Comptes : créer, modifier, désactiver

- **statut** : à faire
- **exigences** : `WF-ADM-0050-A`, `WF-ADM-0060-A`
- **opérations** : `listUsers`, `createUser`, `getUser`, `updateUser`, `setUserActivation`
- **issue** :

**En tant qu'**administrateur, **je veux** créer un compte local, corriger ce que Waterfall
garde d'un compte, le désactiver et le réactiver, depuis la table des comptes, **afin que**
chacun puisse entrer, et qu'une personne partie ne le puisse plus sans que ses actes cessent
d'être attribuables.

**Critères d'acceptation.**

- `WF-ADM-0050-A` — « La création d’un compte sans nom, sans prénom ou sans adresse est refusée, de même que celle d’un compte dont l’adresse est déjà portée par un autre. »
- `WF-ADM-0050-A` — « Le nom, le prénom et l’adresse d’un compte de l’annuaire ou d’un fournisseur externe ne sont pas modifiables dans Waterfall. »
- `WF-ADM-0060-A` — « Aucun écran ne propose de supprimer un compte. »
- `WF-ADM-0060-A` — « La connexion d’un compte désactivé est refusée. »
- écart : `WF-ADM-0060-A` — « Une révision marquée par un compte depuis désactivé affiche toujours son auteur. » : la révision marquée arrive en EP-04, qui clôt
  l'exigence ; ici, un compte désactivé reste nommé partout où il est cité, dans les colonnes
  d'audit des comptes et des rôles qu'il a écrits.
- `WF-ADM-0060-A` — « Un compte réactivé se connecte de nouveau avec ses rôles d’avant. »
- propre à l'US : chaque colonne de la table des comptes se trie dans les deux sens, par le
  serveur (`sort_by`, `sort_order`, WF-IHM-0060).
- propre à l'US : la table des comptes est sa propre saisie, pour qui porte `users.write` —
  nom et prénom d'un compte local, état sur un interrupteur, rôles et rattachement selon leurs
  US — et un refus s'y dit par le catalogue des codes d'erreur (#379).

**Notes de réalisation.** Un compte local est créé dans Waterfall et dans le fournisseur
d'identité, par son API d'administration (WF-ADM-0070, dernière phrase du corps), dont le
Vérif est constaté par US-0370. La désactivation révoque les sessions du compte chez le
fournisseur (WF-SEC-0020). L'ordre des colonnes et la forme de la saisie en ligne sont ceux
que #379 consigne.

**Hors périmètre.** Les filtres de la table (WF-IHM-0130) — EP-11 ; le rattachement — EP-05.

## US-0370 — Lecture des comptes du fournisseur, worker et file

- **statut** : à faire
- **exigences** : `WF-ADM-0070-A`, `WF-ARC-0090-A`
- **opérations** : `startDirectorySync`, `getLatestDirectorySync`, `getBackgroundTask`,
  `listBackgroundTasks`
- **issue** :

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
- écart : `WF-ARC-0090-A` — « Le marquage d’une révision de dix mille objets n’immobilise aucune requête au-delà de la création de la tâche, et l’utilisateur en voit l’aboutissement. » : le marquage arrive en EP-04 ; ici, la lecture
  des comptes ne tient aucune requête au-delà de la création de la tâche, et l'utilisateur en
  voit l'aboutissement.
- `WF-ARC-0090-A` — « L’arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après redémarrage. » : constaté sur la lecture des comptes.
- `WF-ARC-0090-A` — « Aucun de ces traitements n’est joignable par un endpoint qui répondrait après l’avoir exécuté. » : pour la lecture des comptes ; EP-13 le constate pour
  tous les traitements.
- propre à l'US : la lecture se dépose en file à l'intervalle que fixe la configuration de
  l'installation, et le worker la prend comme celle qu'un administrateur demande (PBS-5.3).

**Notes de réalisation.** Le worker et la file servent ensuite le marquage (EP-04), les
imports (EP-09, EP-12) et la sauvegarde (EP-13) : le genre d'une tâche est déjà une
énumération du contrat (`BackgroundTaskRef.kind`).

## US-0380 — Rôles d'habilitation et catalogue des permissions

- **statut** : à faire
- **exigences** : `WF-ADM-0010-A`, `WF-ADM-0020-A`, `WF-ADM-0090-A`, `WF-ADM-0100-A`,
  `WF-ADM-0120-A`, `WF-INTF-0030-A`
- **opérations** : `listPermissions`, `listAccessRoles`, `createAccessRole`, `getAccessRole`,
  `updateAccessRole`, `deleteAccessRole`, `setUserAccessRoles`
- **issue** :

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
- `WF-ADM-0100-A` — « Chaque fonction de second niveau de l’arborescence est représentée par ses deux permissions. »
- écart : `WF-ADM-0100-A` — « Un rôle disposant de la modification du chiffrage mais non du marquage permet de modifier un devis et refuse de marquer la révision ; un rôle disposant du marquage mais non de la fusion refuse de fusionner un différentiel. » : le marquage arrive en EP-04, le devis en EP-07,
  la fusion en EP-08, qui clôt l'exigence.
- écart : `WF-ADM-0100-A` — « Un utilisateur sans la permission de créer un projet n’en crée pas. » : la création d'un projet arrive en EP-04.
- `WF-ADM-0100-A` — « Aucun écran ne permet de créer une permission. »
- `WF-ADM-0120-A` — « La désactivation du dernier compte administrateur est refusée, de même que le retrait de son rôle. »
- `WF-ADM-0120-A` — « Elle est acceptée dès qu’un second compte actif porte la permission. »
- écart : `WF-INTF-0030-A` — « Un utilisateur porteur du rôle prédéfini « administrateur » crée un compte, lui affecte un rôle d’habilitation (FBS-1.1, FBS-1.2), ouvre l’écran d’état du système (FBS-1.3) et déclenche une sauvegarde (FBS-1.4). » : la création d'un compte et l'affectation d'un
  rôle sont ici ; l'écran d'état et la sauvegarde arrivent en EP-13, qui clôt l'exigence.
- propre à l'US : chaque colonne de la table des rôles se trie dans les deux sens, par le
  serveur (WF-IHM-0060) ; la matrice des permissions est le lieu de leur modification, une
  case par permission et par rôle, et la création, le renommage et la suppression se font
  dans la table (#380).
- propre à l'US : un rôle supprimé n'est plus lu ni attribuable, et sa ligne est conservée,
  ce que le journal d'audit et les attributions passées citent (WF-DAT-0080, décision du
  cadrage).

**Notes de réalisation.** Le contenu des trois rôles prédéfinis est celui que l'exemple
`access_roles` du contrat livre ; le catalogue est l'énumération `PermissionCode`, trois
permissions comprises depuis #384. La suppression d'un rôle est logique (décision du
cadrage, 2026-10-07) : WF-DAT-0080 ne laisse disparaître aucun objet de la plateforme, et
WF-ADM-0090 veut qu'un rôle se supprime ; une issue « Specification finding » propose de le
dire dans la spécification.

## US-0390 — Évaluation d'une action et permissions effectives

- **statut** : à faire
- **exigences** : `WF-ADM-0110-A`
- **opérations** : `getMe`
- **issue** :

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
- **issue** :

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
- **exigences** : `WF-SEC-0030-A`, `WF-ARC-0110-A`
- **opérations** : aucune en propre — les écritures des comptes et des rôles l'alimentent
- **issue** :

**En tant qu'**administrateur, **je veux** que chaque création ou modification d'un compte,
d'un rôle ou d'une attribution soit inscrite dans un journal que la plateforme ne peut pas
réécrire, et conservée sous forme de code et de données, **afin de** pouvoir dire après coup
qui a donné quel droit, dans la langue de celui qui le relit.

**Critères d'acceptation.**

- `WF-SEC-0030-A` — « Chacune des actions énumérées produit une inscription datée et attribuée. » : pour les actions de cet EPIC — la création et la
  modification des comptes, des rôles et de leurs attributions, et la demande d'un lien de
  fixation ; les autres actions énumérées arrivent avec leur EPIC.
- `WF-SEC-0030-A` — « Aucun écran ni endpoint ne permet de modifier ou de supprimer une inscription. »
- écart : `WF-SEC-0030-A` — « Le journal d'un projet terminé depuis cinq ans est toujours consultable. » : la consultation du journal et les projets
  arrivent en EP-04 et EP-13, qui clôt l'exigence.
- `WF-ARC-0110-A` — « Aucune réponse de l'API ne contient de phrase destinée à l'utilisateur. »
- écart : `WF-ARC-0110-A` — « Un import fait par un utilisateur en français, relu par un utilisateur en anglais, présente son compte rendu en anglais. » : l'import arrive en EP-09 et EP-12.
- écart : `WF-ARC-0110-A` — « Le journal d'audit d'une même action se lit dans la langue de chaque lecteur. » : ici, une inscription est conservée sous forme
  de code et de données, sans phrase ; sa lecture arrive en EP-13, qui clôt l'exigence.
- `WF-ARC-0110-A` — « Un courriel de réinitialisation part du fournisseur d'identité, dans la langue du compte. »

## US-0420 — Amorçage d'une installation neuve

- **statut** : à faire
- **exigences** : `WF-EXP-0020-A`
- **opérations** : aucune — l'amorçage est une commande d'installation, non une opération de
  l'API
- **issue** :

**En tant qu'**exploitant, **je veux** qu'une installation neuve crée d'elle-même ce sans quoi
personne ne peut entrer, et rien d'autre, et qu'elle me remette le lien par lequel le premier
administrateur fixe son mot de passe, **afin qu'**aucun mot de passe d'installation ne
traîne dans une procédure, et que la relancer soit sans danger.

**Critères d'acceptation.**

- `WF-EXP-0020-A` — « Après installation, un administrateur fixe son mot de passe par le lien produit, se connecte, et dispose des trois rôles prédéfinis et du catalogue des permissions. »
- écart : `WF-EXP-0020-A` — « La création d’un projet est refusée et nomme les prérequis manquants, jusqu’à ce qu’une catégorie de coût de main-d’œuvre et un rôle de ressource aient été saisis. » : le référentiel arrive en EP-05 et la création
  d'un projet en EP-04, qui clôt l'exigence.
- `WF-EXP-0020-A` — « Une seconde exécution de l’installation ne crée ni compte, ni calendrier, ni nature supplémentaire. » : pour le compte ; le calendrier et la nature
  arrivent en EP-05, qui les ajoute à l'amorçage.
- propre à l'US : l'amorçage applique les migrations, crée le catalogue des permissions, les
  trois rôles prédéfinis, le compte administrateur local dans le fournisseur d'identité et
  dans Waterfall, et la langue par défaut de l'installation ; les libellés des rôles sont dans
  cette langue (WF-EXP-0020).

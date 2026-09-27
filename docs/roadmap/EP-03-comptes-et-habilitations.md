---
id: EP-03
titre: Se connecter, et n'agir que dans les limites de ses habilitations
statut: à planifier
depend_de: EP-01
issue:
---

# EP-03 — Comptes, authentification et habilitations

## Objet

Le premier service réel : l'API, la base, les migrations et la session. Les comptes
locaux, l'annuaire LDAP ou AD et OIDC ; les rôles d'habilitation et le catalogue des
permissions ; et, avec la synchronisation de l'annuaire, le premier traitement de fond, qui
fait naître le worker et sa file.

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
- l'authentification locale, par l'annuaire et par OIDC ; la session en base, son expiration et
  sa révocation ;
- les comptes : attributs, cycle de vie, avatar, import et resynchronisation depuis l'annuaire ;
- les rôles d'habilitation, le catalogue des permissions, les trois rôles prédéfinis, et la
  protection du dernier administrateur ;
- les permissions effectives connues du front, et les préférences et la langue conservées dans
  le compte ;
- le worker et la file de tâches, la synchronisation de l'annuaire pour premier traitement ;
- le journal d'audit, pour les comptes, les rôles et leurs attributions ;
- l'amorçage d'une installation neuve : catalogue, rôles prédéfinis, compte administrateur ;
- la comparaison, par la chaîne, des réponses de l'API au schéma déclaré — piste pour la
  conception : prism en mode proxy devant le service, l'outil du faux back d'EP-01
  (US-0030) ;
- les écrans de connexion, des comptes et des rôles de la maquette, branchés sur le service.

## Ce qui n'en fait pas partie

- le rattachement d'un compte à un nœud d'organisation — EP-05, qui crée l'arbre ;
- la qualité de contributeur, second terme de l'évaluation d'une action — EP-04 ;
- l'écran d'état, la sauvegarde et la restauration, qui complètent les usages de
  l'administrateur (WF-INTF-0030) — EP-13 ;
- le chiffrement des échanges et l'injection des secrets par la plateforme — EP-13. Ici, un
  service qui démarre sans ses secrets échoue en le disant, et c'est tout.

## Exigences réalisées

La portée dit si l'exigence est entière ici, commencée ici et close par un EPIC ultérieur, ou
close ici après avoir été commencée plus tôt. Chaque exigence n'est close que par un seul EPIC.
La colonne US se remplit quand l'EPIC passe `prêt`.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-INTF-0030-A` | Usages de l’administrateur | début — close en EP-13 | — |
| `WF-INTF-0160-A` | Choix de la langue de l'interface | fin — amorcée en EP-02 | — |
| `WF-ADM-0040-A` | Préférences d’affichage | fin — amorcée en EP-02 | — |
| `WF-ADM-0050-A` | Attributs d’un compte utilisateur | entière | — |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | entière | — |
| `WF-ADM-0070-A` | Import des comptes depuis l’annuaire d’entreprise | entière | — |
| `WF-ADM-0080-A` | Avatar | entière | — |
| `WF-ADM-0140-A` | Authentification et mot de passe | entière | — |
| `WF-ADM-0180-A` | Fournisseurs d’authentification | entière | — |
| `WF-ADM-0010-A` | Rôles d’habilitation prédéfinis | entière | — |
| `WF-ADM-0020-A` | Aucune action réservée à un acteur | entière | — |
| `WF-ADM-0090-A` | Rôles et permissions | entière | — |
| `WF-ADM-0100-A` | Catalogue des permissions | entière | — |
| `WF-ADM-0110-A` | Évaluation d’une action | début — close en EP-04 | — |
| `WF-ADM-0120-A` | Dernier administrateur | entière | — |
| `WF-ARC-0060-A` | Contrat OpenAPI | fin — amorcée en EP-01 | — |
| `WF-ARC-0110-A` | Le texte est rendu au plus près du lecteur | début — close en EP-12 | — |
| `WF-ARC-0030-A` | Fournisseurs d’authentification | entière | — |
| `WF-ARC-0090-A` | Traitements longs confiés au worker | début — close en EP-13 | — |
| `WF-DAT-0060-A` | Identifiants | début — close en EP-04 | — |
| `WF-DAT-0070-A` | Colonnes d’audit | début — close en EP-09 | — |
| `WF-DAT-0080-A` | Régimes de suppression | début — close en EP-04 | — |
| `WF-DAT-0090-A` | Intégrité déclarée en base | début — close en EP-07 | — |
| `WF-DAT-0100-A` | Types des grandeurs | début — close en EP-07 | — |
| `WF-DAT-0140-A` | Migrations du schéma | début — close en EP-13 | — |
| `WF-EXP-0020-A` | Amorçage d'une installation neuve | début — close en EP-04 | — |
| `WF-SEC-0010-A` | Transport et secrets | début — close en EP-13 | — |
| `WF-SEC-0020-A` | Session et révocation | entière | — |
| `WF-SEC-0030-A` | Journal d'audit des actions irréversibles ou structurantes | début — close en EP-13 | — |

## Opérations du contrat

Rattachement établi d'après les exigences que chaque opération cite, à revoir au détail des
US. Une opération qui manque au contrat se note ici : c'est une modification du contrat, donc
un travail qui précède.

Servies ici pour la première fois (30) :

- `system` : `getLiveness`, `getBackgroundTask` ;
- `session` : `listAuthProviders`, `getCurrentSession`, `openSession`, `closeSession`, `startOidcSession`, `completeOidcSession`, `requestPasswordReset`, `confirmPasswordReset`, `getMe`, `updateMyPreferences`, `changeMyPassword`, `putMyAvatar`, `deleteMyAvatar` ;
- `access` : `listUsers`, `createUser`, `getUser`, `updateUser`, `setUserActivation`, `setUserAccessRoles`, `getUserAvatar`, `startDirectorySync`, `getLatestDirectorySync`, `listPermissions`, `listAccessRoles`, `createAccessRole`, `getAccessRole`, `updateAccessRole`, `deleteAccessRole`.

Déjà servies, et reprises ici pour ce que cet EPIC y ajoute (0) :

aucune.

## Préalables

EP-01 livré. Les écrans que cet EPIC branche viennent d'EP-02 : s'il n'est pas livré, les
US d'écran attendent et le reste avance.

## Définition de fini

- un compte local, un compte de l'annuaire et un compte OIDC ouvrent chacun une session sur la
  plateforme de développement ;
- la désactivation d'un compte connecté sur deux postes interrompt les deux à leur requête
  suivante ;
- une action demandée sans la permission est refusée par l'API en nommant la condition
  manquante, même quand le front ne la propose pas ;
- une réponse non conforme au schéma déclaré fait échouer la chaîne, et aucun endpoint ne
  répond qui ne figure au contrat ;
- l'installation d'une plateforme neuve crée le catalogue, les trois rôles et le compte
  administrateur ; relancée, elle ne crée rien ;
- le parcours de bout en bout traverse la connexion, les comptes et les rôles contre le service
  réel.

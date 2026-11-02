---
id: EP-18
titre: Le service des comptes et ses écrans suivent le contrat figé — un compte naît sans rôle, un rôle se supprime à sa version, un refus de longueur dit sa borne, le compte dit ses commandes du lien
statut: en cours
depend_de: EP-16
famille: back, front
issue: 1852
---

# EP-18 — Comptes : écarts de la revue du contrat

## Objet

La revue du contrat du 2026-10-31 (`docs/api/2026-10-31-contrat-spec-et-fixtures.md`) a fait
écrire au contrat, par US-0704 (EP-16, #1735), quatre décisions de l'auteur du 2026-11-01 qui
touchent le service des comptes et des habilitations, livré par EP-03 : un compte local naît sans
rôle (A-01, #1731), la suppression d'un rôle porte son compteur (A-02, #1733), le lien de fixation
et le renvoi de l'invitation sont des commandes du compte (A-04, #1737), et tout `VALUE_TOO_LONG`
porte la borne de son champ (J-02, #1796). Le contrat est figé en 1.0.0 depuis la livraison
d'EP-16 ; le service, et pour A-04 l'écran des comptes, ne le suivent pas encore. EP-18 les y fait
suivre, sans écrire au contrat. A-01 est une élévation de privilège : un porteur de la seule
gestion des comptes crée aujourd'hui, par un appel direct, un compte porteur du rôle
« Administrateur ».

Il vient juste après EP-17, dont la livraison a commencé, et avant EP-05 : il touche les mêmes
fichiers que le lot des comptes d'EP-17 (US-0780/L1, `user-cells.tsx`) et que le rattachement des
comptes d'EP-05 (`api/users.py`, `user-cells.tsx`) ; livré d'abord, il leur évite de se croiser
(« Conception », « Ordre de construction »). C'est la « branche de correction d'EP-03 » que
l'auteur a annoncée le 2026-11-01, avant EP-05.

## Ce qui en fait partie

- la création d'un compte local sans rôle, le service cessant de lire `access_role_ids` (#1732) —
  US-1050 ;
- `max_length` posé sur tout `VALUE_TOO_LONG` du service, par la traduction commune des refus et
  par le refus écrit à la main des préférences (#1798) ; le compteur exigé par la suppression d'un
  rôle, son 412 et son 422, et le 412 de cette suppression dit par l'écran des rôles (#1734) —
  US-1060 ;
- `create_password_link` et `resend_invitation` listés par le compte, `is_not_anonymized` jugée
  par le lien et le renvoi, et l'écran des comptes qui lit ces deux commandes au lieu de les
  déduire (#1738) — US-1070.

## Ce qui n'en fait pas partie

- toute modification du contrat : les quatre décisions sont déjà écrites dans `main`
  (`docs/api/DECISIONS.md`, US-0704) ; un écart découvert pendant un lot devient une issue
  « contrat » que l'auteur tranche (« La règle d'après le gel ») ;
- `max_length` des refus du code d'un projet et d'un sous-projet (#1797) : EP-04, qui sert ces
  opérations ;
- le rattachement d'un compte à un nœud et son inscription au journal (#1740) : EP-05 ;
- un message de l'écran qui cite la borne d'un `VALUE_TOO_LONG` : aucun écran ne lit
  `params.max_length` aujourd'hui, et aucune exigence ne le demande ; une proposition, si l'auteur
  la veut, va à EP-17 ;
- les écritures retenues de l'écran des rôles et de la table des comptes (#889), et
  l'invariant entre la désactivation et le lien d'une même ligne (#949) : EP-17 (US-0770/L1,
  US-0780/L1) ;
- l'envoi du compteur par le parcours du journal qui supprime le rôle qu'il crée : EP-17
  (US-0780/L2), qui l'envoie déjà puisque le contrat l'exige.

## Exigences réalisées

EP-18 ne clôt aucune exigence : il corrige le service d'un EPIC livré. Comme EP-17, chaque US
cite les exigences dont ses tests relèvent, avec tout leur Vérif ; les phrases que l'US ne touche
pas sont des écarts qui disent qui les constate.

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-ADM-0070-A` | Lecture des comptes du fournisseur d’identité | début — close en EP-04 | US-1050 |
| `WF-ADM-0100-A` | Catalogue des permissions | début — close en EP-08 | US-1050 |
| `WF-ARC-0110-A` | Le texte est rendu au plus près du lecteur | début — close en EP-06 | US-1060 |
| `WF-IHM-0110-A` | Annulation et rétablissement des saisies | début — close en EP-06 | US-1060 |
| `WF-ADM-0060-A` | Cycle de vie d’un compte | début — close en EP-04 | US-1070 |

Les exigences déjà closes par un EPIC livré que ces travaux touchent restent closes, et leurs
tests existants continuent de les citer ; quatre sont citées par une US, avec tout leur Vérif,
parce que l'US porte un test qui en relève (même règle qu'EP-17, décision de l'auteur du
2026-10-28) : `WF-ADM-0090-A`, Rôles et permissions, close par EP-03 — US-1050 et US-1060 ;
`WF-ADM-0140-A`, Authentification et mot de passe, close par EP-03 — US-1070 ;
`WF-IHM-0090-A`, Refus et commandes indisponibles, et `WF-ARC-0020-A`, Le contrat est le seul
contrat, closes par EP-02 — US-1070.

## Opérations du contrat

Servies par EP-03, et reprises ici pour ce que le contrat 1.0.0 y a changé : `createUser`
(US-1050), `setUserAccessRoles` (US-1050, inchangée, éprouvée), `deleteAccessRole` (US-1060),
`updateMyPreferences` et la traduction commune des refus de toutes les opérations (US-1060),
`listUsers`, `getUser`, `getMe`, `createPasswordSetupLink` et `resendInvitation` (US-1070).
Aucune n'est ajoutée ni modifiée au contrat : le diff de la branche de l'EPIC ne touche aucun
fichier de `docs/api`, ni les modèles engendrés du service, ni le client du front.

## Préalables

EP-16 livré, le contrat en 1.0.0 dans `main` avec les décisions A-01, A-02, A-04 et J-02 (fait).
La spécification 1.0.2 porte « sans rôle » dans le Vérif de WF-ADM-0070 (#1730, fait).

## Définition de fini

- un porteur de `users.write` sans `access_roles.write` qui envoie `access_role_ids` à
  `createUser` obtient un compte sans rôle, et se voit refuser `setUserAccessRoles` par 403 ;
  `PendingUserCreate` n'existe plus dans `backend/src` ;
- `deleteAccessRole` sans compteur répond 422, à un compteur périmé 412, et ne supprime rien ;
- tout `VALUE_TOO_LONG` du service porte `fields[].params.max_length` ;
- l'écran des comptes ne lit plus `origin`, `is_active` ni `anonymized_at` pour présenter le
  lien et le renvoi, et la constante `DEACTIVATED` n'existe plus dans `frontend/src` ;
- `make check` passe sur la branche de l'EPIC, et `make check-service` y joue les parcours
  contre le service, ceux des comptes et des rôles compris, à travers le mandataire du contrat ;
- `make roadmap` et `make requirements` passent ; les tests des critères citent leurs exigences ;
- #1732, #1734, #1738 et #1798 sont fermés par la fusion de leur lot.

## Constats reçus

Les quatre issues `[EP-03]` de la revue du contrat du 2026-10-31, `à trancher` jusqu'au cadrage,
renommées `[EP-18]` et passées au label `EP-18` à l'ouverture des issues :

- #1732 — `createUser` attribue les rôles du corps sous la seule permission `users.write` (A-01)
  → US-1050 ;
- #1798 — `VALUE_TOO_LONG` sans `max_length` dans la traduction commune des refus (J-02)
  → US-1060 ;
- #1734 — `deleteAccessRole` supprime sans compteur (A-02) → US-1060 ;
- #1738 — le lien de fixation et le renvoi de l'invitation, commandes du compte (A-04)
  → US-1070.

## Conception

Courte : chaque issue porte déjà sa proposition, ses fichiers et ses tests, et fait foi pour le
détail ; ce qui suit ne dit que ce qu'elles laissent ouvert, et ce qui s'en écarte.

**Tables et migrations.** Aucune. `access_role.lock_version` existe depuis EP-03.

**Modules du noyau touchés.**

- `core/access_roles` : `delete_role` reçoit le compteur lu et refuse par
  `PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": …})`, comme
  `update_role` ; l'interface du module garde son nom et gagne ce paramètre. `give_first_roles`
  reste, pour le seul amorçage (`bootstrap.py`).
- `core/users` : `AccountState` gagne l'origine locale du compte, et `account_commands` liste
  les deux commandes du lien dans l'ordre du contrat (après `set_access_roles`) ;
  `lock_link_holder` juge `is_local_account`, puis `is_not_anonymized`, puis
  `is_active_account`, pour la demande du lien, son inscription (`inscribe_link`) et le
  renvoi ; `personal.py` pose `max_length` sur son refus.
- `api` (hors noyau) : `users.py` (`post_user`, `check_new_account`, `write_new_account`,
  `users`), `access_roles.py` (le paramètre `lock_version`), `problems.py` (la traduction
  commune).

**Modifications du contrat.** Aucune. Vérifié dans `main` le 2026-11-02 : `UserCreate` sans
`access_role_ids` (`components/schemas/access.yaml`) ; `deleteAccessRole` avec `lock_version`
exigé, 412 `access_role_delete_stale` et 422 `LockVersionInvalid` (`paths/access.yaml`) ;
`UserCommand` à six valeurs et `available_commands` à `maxItems: 5`, les 409 du lien et du
renvoi dans l'ordre `is_local_account`, `is_not_anonymized`, `is_active_account`, avec leurs
exemples `password_link_anonymized` et `invitation_anonymized` ; `max_length` sur tout
`VALUE_TOO_LONG` (`components/common.yaml`, `Problem.params` et le catalogue). Les modèles du
service et le client du front sont déjà engendrés de ce contrat (US-0704), et le front envoie
déjà le compteur de `deleteAccessRole` (`api/actions/access-roles.ts`, US-0704).

**Ordre de construction.** US-1050 d'abord : c'est la faille, et le lot qui tire `epic/EP-18`.
Puis US-1060, puis US-1070, dont le service précède l'écran dans le même lot. Aucune ne dépend
d'une autre pour ses critères ; l'ordre ne règle que `api/users.py`, que touchent US-1050 et
US-1070. EP-18 est livré dans `main` avant qu'EP-17 n'attaque US-0780/L1 (#1564), qui réécrit
la retenue de `SetupLinkCommand` et de `ResendInvitationCommand` dans `user-cells.tsx` (#949)
— le code même qu'US-1070 réécrit — ; et avant le premier lot d'EP-05, qui touche `api/users.py`
et `user-cells.tsx`. EP-17 n'est pas suspendu : seul US-0780/L1 attend EP-18, et le tableau de
suivi d'EP-17 (#1547) le dit dans sa colonne « Dépend de » ; EP-17 reprend `main` comme après
toute fusion. EP-05 dépend d'EP-18 (`depend_de: EP-16, EP-18`). Décisions de l'auteur du
2026-11-02.

**Décisions.**

- **`access_role_ids` envoyé à `createUser` est ignoré, comme toute propriété que le contrat ne
  déclare pas ; il n'est pas refusé par 400.** #1732 proposait un 400 « selon le modèle
  régénéré du contrat », et #1731 « si `UserCreate` est `additionalProperties: false` ». Il ne
  l'est pas : aucun corps de requête du contrat ne l'est — les deux seuls schémas fermés,
  `AuditParams` et `IdentitySyncSkipped`, sont des réponses (revue du 2026-10-31, remarque
  transverse) —, et le service ignore toute propriété non déclarée (`ContractModel`). Le compte
  naît donc sans rôle, et rien ne s'écrit d'autre : la faille est fermée. Écarté : un 400 propre
  à cette propriété, qui ferait le service plus strict que le contrat figé sur une seule
  opération, ou une issue « contrat » pour `additionalProperties: false`, un changement
  incompatible après le gel. Décision de l'auteur du 2026-11-02.
- **Un lot pour la faille seule (US-1050), en `opus`.** Écarté : le grouper avec #1798 comme
  le proposait la première lecture, qui aurait mis un changement mécanique de la traduction
  commune sous `opus` ou la faille sous `sonnet`, et dilué la revue d'une correction de
  sécurité dans un changement transverse.
- **La suppression d'un rôle juge le compteur avant `ACCESS_ROLE_IN_USE`** : 404 si le rôle
  n'existe pas ou est supprimé, puis 412 si le compteur est périmé, puis 409 s'il est porté.
  #1734 renvoyait à « l'ordre que suit `deleteRisk` », mais le contrat de `deleteRisk` ne dit
  pas l'ordre du 412 et du 409, et le service ne la sert pas encore (EP-08). Retenu : « la
  version contrôlée d'abord, 412 si elle est périmée, comme toute écriture versionnée »
  (`DECISIONS.md`, `setDefaultCalendar`), qui est aussi l'ordre d'`update_role` ; relu après le
  412, l'écran ne propose plus de supprimer un rôle porté. Écarté : le 409 d'abord, qui dirait
  « porté » d'un rôle que l'écran n'a pas relu. EP-08 suivra le même ordre pour `deleteRisk`.
  Décision de l'auteur du 2026-11-02.
- **`max_length` est la borne que le service applique.** Dans la traduction commune, celle que
  porte la faute (`ctx.max_length`) : le `maxLength` d'un texte, le `maxItems` d'une liste, et
  aussi le `maxProperties` d'un objet et le `maxLength` d'un nom de propriété, que le contrat
  range sous le même `VALUE_TOO_LONG` (`UserPreferences`) sans les nommer dans la règle de
  `max_length`. Dans le refus écrit à la main des préférences, la borne jugée,
  `max(MOST_ENTRIES, len(avant))` : celle qui, tenue, fait passer l'écriture. Écarté : le seul
  `MOST_ENTRIES`, qui pour une table déjà au-delà (antérieure à la borne, #874) nommerait une
  limite que la table dépasse déjà. Aucune issue de contrat : c'est une lecture de la règle
  (« la borne du champ refusé »), non un changement. Décision de l'auteur du 2026-11-02.
- **Le front de #1734 se réduit à un test.** US-0704 a déjà fait envoyer le compteur par
  l'écran des rôles, et la liste dit un 412 comme toute écriture (`list.report`, l'avis
  `stale` qui propose de relire) ; US-1060 l'éprouve sur la suppression, sans code de
  production.
- **L'écran ne garde des deux commandes que l'état local de la ligne** : une désactivation
  demandée, un lien en route ; la disponibilité, l'indisponibilité et leur condition viennent
  du compte (`findOffer`, `unmet`), comme `deactivate` et `anonymize`. Un compte qui ne les
  liste pas — de l'annuaire, d'un fournisseur externe, anonymisé, ou lu sans `users.write` —
  ne les présente pas.

---

## US-1050 — Un compte local naît sans rôle

- **statut** : à faire
- **exigences** : `WF-ADM-0070-A`, `WF-ADM-0090-A`, `WF-ADM-0100-A`
- **opérations** : `createUser`, `setUserAccessRoles`
- **issue** : #1853

**En tant qu'**administrateur, **je veux** qu'un compte créé depuis Waterfall naisse sans rôle,
ses rôles ne lui étant donnés que par la gestion des rôles, **afin que** la seule gestion des
comptes ne donne jamais, par un appel direct, le rôle d'administrateur (#1732, A-01).

**Critères d'acceptation.**

- `WF-ADM-0070-A` — « Un compte local créé depuis Waterfall existe dans le fournisseur d’identité, sans rôle. » : créé avec ou sans `access_role_ids` dans le corps, le compte n'a aucun
  rôle ni aucune permission, et l'inscription de sa création n'en nomme aucun.
- écart : `WF-ADM-0070-A` — « Après lecture, chaque personne de l’annuaire retenue a un compte actif dans Waterfall, sans rôle si elle n’en avait pas, avant toute connexion. » : la lecture
  n'est pas touchée ; constaté par EP-03 (US-0370), EP-04 clôt.
- écart : `WF-ADM-0070-A` — « Une personne retirée de l’annuaire voit son compte désactivé à la synchronisation suivante, et ses actes restent consultables. » : idem.
- écart : `WF-ADM-0070-A` — « Le dernier compte administrateur, retiré de l’annuaire, reste actif et la synchronisation le signale. » : idem.
- écart : `WF-ADM-0070-A` — « Une personne ajoutée à l’annuaire a un compte dans Waterfall au terme de la périodicité choisie, sans intervention. » : idem.
- écart : `WF-ADM-0070-A` — « Un compte anonymisé dont la personne figure encore dans l’annuaire reste anonymisé après synchronisation, et aucun compte n’est créé à son nom. » : idem.
- écart : `WF-ADM-0090-A` — « Un utilisateur portant deux rôles dispose des permissions des deux. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0090-A` — « Le retrait d’une permission à un rôle en prive tous ses porteurs sans qu’ils aient à se reconnecter. » : idem.
- écart : `WF-ADM-0090-A` — « La suppression d’un rôle est refusée tant qu’un compte le porte. » : US-1060.
- écart : `WF-ADM-0090-A` — « Un rôle supprimé n’apparaît plus dans la liste des rôles ni dans les choix d’attribution ; l’inscription du journal d’audit qui l’attribuait à un compte le nomme toujours. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0100-A` — « Chaque fonction de second niveau de l’arborescence est représentée par ses deux permissions, ou par la seule permission de consulter pour FBS-1.3, FBS-1.5 et FBS-2.1 à FBS-2.7. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0100-A` — « Un rôle disposant de la modification du chiffrage mais non du marquage permet de modifier un devis et refuse de marquer la révision ; un rôle disposant du marquage mais non de la fusion refuse de fusionner un différentiel. » : EP-04 et EP-08.
- écart : `WF-ADM-0100-A` — « Un utilisateur sans la permission de créer un projet n’en crée pas. » : EP-04.
- écart : `WF-ADM-0100-A` — « Aucun écran ne permet de créer une permission. » : constaté par EP-03 (US-0380), inchangé.
- propre à l'US : un porteur de `users.write` sans `access_roles.write` crée un compte, puis se
  voit refuser `setUserAccessRoles` sur ce compte par 403 `PERMISSION_MISSING` : la gestion des
  comptes (FBS-1.1) ne donne pas celle des rôles (FBS-1.2, WF-ADM-0090, WF-ADM-0100).
- propre à l'US : le premier administrateur reçoit toujours son rôle à l'amorçage de
  l'installation, qui ne passe pas par `createUser`.

**Notes de réalisation.** La proposition de #1732 fait foi, à une décision près : la propriété
non déclarée est ignorée, non refusée (« Conception », « Décisions »). `PendingUserCreate`
disparaît ; les tests d'EP-03 qui créaient un compte avec ses premiers rôles sont retirés ou
récrits sur `setUserAccessRoles`. Le front n'envoie aucun rôle à la création, et le parcours
du service attribue déjà par `setUserAccessRoles` (`frontend/e2e/service/realm.ts`) : rien à
changer côté front.

**Hors périmètre.** L'amorçage (`bootstrap.py`, `give_first_roles`).

---

## US-1060 — La suppression d'un rôle porte son compteur, un refus de longueur dit sa borne

- **statut** : à faire
- **exigences** : `WF-ADM-0090-A`, `WF-IHM-0110-A`, `WF-ARC-0110-A`
- **opérations** : `deleteAccessRole`, `updateMyPreferences`, `createUser`
- **issue** : #1854

**En tant qu'**administrateur, **je veux** que la suppression d'un rôle qu'un autre vient
d'écrire me soit refusée jusqu'à ce que je l'aie relu, et que tout refus d'une valeur trop longue
dise sa borne, **afin de** ne jamais supprimer ce que je n'ai pas vu, et de savoir ce que le
service accepte (#1734, A-02 ; #1798, J-02).

**Critères d'acceptation.**

- `WF-ADM-0090-A` — « La suppression d’un rôle est refusée tant qu’un compte le porte. » : 409
  `ACCESS_ROLE_IN_USE`, à compteur à jour, jugé après le compteur.
- écart : `WF-ADM-0090-A` — « Un utilisateur portant deux rôles dispose des permissions des deux. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0090-A` — « Le retrait d’une permission à un rôle en prive tous ses porteurs sans qu’ils aient à se reconnecter. » : idem.
- écart : `WF-ADM-0090-A` — « Un rôle supprimé n’apparaît plus dans la liste des rôles ni dans les choix d’attribution ; l’inscription du journal d’audit qui l’attribuait à un compte le nomme toujours. » : idem.
- propre à l'US (règle du compteur du README du contrat, WF-IHM-0110) : `deleteAccessRole` à un
  compteur périmé répond 412 `STALE_LOCK_VERSION`, `params.expected_lock_version` le compteur
  courant, et rien n'est supprimé ni inscrit ; sans compteur, ou d'un compteur qui n'est pas un
  entier positif ou nul, 422 `VALIDATION_FAILED` sur `/query/lock_version` ; un rôle inconnu ou
  supprimé reste un 404.
- propre à l'US : l'écran des rôles dit le 412 de la suppression comme celui de la
  modification, et propose de relire ; relu, un rôle désormais porté n'est plus proposé à la
  suppression.
- écart : `WF-IHM-0110-A` — « La suppression d’une tâche puis son annulation restituent la tâche, ses lignes et ses liaisons. » : l'annulation arrive avec la planification, EP-06,
  qui clôt ; seule la règle du compteur, sur laquelle elle repose, est tenue ici.
- écart : `WF-IHM-0110-A` — « Le réexamen d’un risque puis son annulation lui rendent sa probabilité et son état précédents. » : EP-08 ; EP-06 clôt.
- écart : `WF-IHM-0110-A` — « Cinquante modifications successives s’annulent une par une, puis se rétablissent dans l’ordre. » : EP-06.
- écart : `WF-IHM-0110-A` — « L’annulation d’une modification qu’un autre contributeur a depuis reprise est refusée en nommant l’objet en conflit. » : EP-06 ; le 412 de la
  suppression d'un rôle en est la forme sans annulation.
- écart : `WF-IHM-0110-A` — « Aucune commande n’annule un marquage, un import appliqué, une déclaration de survenance ou une exclusion de ligne de coût. » : EP-06.
- `WF-ARC-0110-A` — « Aucune réponse de l'API ne contient de phrase destinée à l'utilisateur. » :
  tout `VALUE_TOO_LONG` porte `fields[].params.max_length`, la borne que le service applique,
  pour que l'écran rende lui-même sa phrase — un nom de compte de cent un caractères
  (`createUser`, `100`), une préférence qui fait passer une table au-delà de ses entrées
  (`updateMyPreferences`, la borne jugée), un filtre de grille de plus de cinq cents caractères
  (`500`).
- écart : `WF-ARC-0110-A` — « Un import fait par un utilisateur en français, relu par un utilisateur en anglais, présente son compte rendu en anglais. » : EP-06.
- écart : `WF-ARC-0110-A` — « Le journal d'audit d'une même action se lit dans la langue de chaque lecteur. » : constaté par EP-03 (US-0410), inchangé.
- écart : `WF-ARC-0110-A` — « Un courriel de réinitialisation part du fournisseur d'identité, dans la langue du compte. » : idem.

**Notes de réalisation.** Les propositions de #1734 et #1798 font foi, aux deux décisions près
de la conception : l'ordre 412 avant 409, et la borne jugée des préférences. La traduction
commune vaut pour tous les EPIC suivants : son test passe par une opération d'EP-03, et la
borne se lit de la faute, jamais d'une table recopiée.

**Hors périmètre.** `max_length` des codes de projet et de sous-projet (#1797, EP-04) ; la
phrase de l'écran qui citerait la borne.

---

## US-1070 — Le compte dit ses commandes du lien

- **statut** : à faire
- **exigences** : `WF-ADM-0140-A`, `WF-IHM-0090-A`, `WF-ARC-0020-A`, `WF-ADM-0060-A`
- **opérations** : `listUsers`, `getUser`, `getMe`, `createPasswordSetupLink`, `resendInvitation`
- **issue** : #1855

**En tant qu'**administrateur, **je veux** que le compte dise d'avance si son lien de fixation et
le renvoi de son invitation sont disponibles, et pourquoi ils ne le sont pas, **afin que**
l'écran ne recalcule pas la règle du service et que le refus d'un compte anonymisé dise sa vraie
raison (#1738, A-04).

**Critères d'acceptation.**

- `WF-ADM-0140-A` — « Aucun écran de Waterfall ne demande, n’affiche ni ne permet de saisir un mot de passe ; le lien de fixation est le seul élément d’authentification qu’il présente. » :
  le lien et le renvoi restent les seules commandes du mot de passe, présentées d'après le
  compte.
- `WF-ADM-0140-A` — « Un compte importé n’a pas d’écran de mot de passe et se connecte avec ses identifiants d’annuaire. » : un compte de l'annuaire ou d'un fournisseur externe ne liste ni
  `create_password_link` ni `resend_invitation`, et l'écran ne les présente pas ; la connexion
  est constatée par EP-03 (US-0350), inchangée.
- écart : `WF-ADM-0140-A` — « Un mot de passe de onze caractères est refusé, de même que l’adresse du compte. » : configuration du fournisseur, constatée par EP-03 (US-0350), inchangée.
- écart : `WF-ADM-0140-A` — « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes. » : idem.
- écart : `WF-ADM-0140-A` — « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé. » : idem.
- écart : `WF-ADM-0140-A` — « Un compte créé par un administrateur ne peut pas se connecter avant que son porteur n’ait fixé son mot de passe par le lien reçu ou remis. » : idem.
- écart : `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en nommant la condition manquante. » : la terminaison est d'EP-04 ;
  ici, sa forme pour un compte : le lien et le renvoi d'un compte local désactivé sont listés
  indisponibles, `is_active_account` manquante, et l'écran les présente indisponibles en
  nommant cette condition, d'après le compte.
- écart : `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas cette commande. » : le marquage est d'EP-04 ; ici, sa forme : un lecteur sans
  `users.write` ne reçoit ni ne voit ces deux commandes.
- écart : `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas contributeur nomme cette condition. » : EP-04, sans objet pour un compte.
- écart : `WF-IHM-0090-A` — « Pendant un traitement de fond sur le projet, la saisie du lotissement est présentée indisponible en nommant le traitement en cours comme condition manquante, et une écriture tentée est refusée en le nommant. » : EP-04 et EP-06, sans objet pour un compte.
- écart : `WF-ARC-0020-A` — « Le front ne contient aucun appel http vers l’API hors du client engendré. » : constaté par EP-02 (US-0270), inchangé.
- écart : `WF-ARC-0020-A` — « Les montants, dates et indices affichés sont ceux que l’API renvoie, sans recalcul. » : sa forme pour les commandes : l'écran ne déduit plus la
  disponibilité du lien et du renvoi de `origin`, `is_active` et `anonymized_at`, et la
  constante `DEACTIVATED` disparaît ; une commande non listée n'est pas présentée.
- écart : `WF-ARC-0020-A` — « Le diagramme de déploiement (§4.3.1) ne montre aucun composant entre le front et l’API. » : constaté par EP-02, inchangé.
- `WF-ADM-0060-A` — « Après anonymisation d’un compte désactivé, aucun écran — journal d’audit compris — ne présente plus son nom ni son adresse ; les révisions qu’il a marquées affichent le libellé neutre comme auteur ; sa réactivation est refusée. » : un compte local anonymisé ne
  liste plus le lien ni le renvoi, et `createPasswordSetupLink` comme `resendInvitation`, sur
  lui, sont refusés par 409 `STATE_FORBIDS_OPERATION`, `is_not_anonymized`, jugée entre
  `is_local_account` et `is_active_account`, pour la demande du lien comme pour son
  inscription ; le reste de la phrase est constaté par EP-03 et EP-17 (US-0780), les révisions
  marquées par EP-04.
- écart : `WF-ADM-0060-A` — « Aucun écran ne propose de supprimer un compte. » : constaté par EP-03 (US-0360), inchangé.
- écart : `WF-ADM-0060-A` — « La connexion d’un compte désactivé est refusée. » : idem.
- écart : `WF-ADM-0060-A` — « Une révision marquée par un compte depuis désactivé affiche toujours son auteur. » : EP-04 clôt.
- écart : `WF-ADM-0060-A` — « Un compte réactivé se connecte de nouveau avec ses rôles d’avant. » : constaté par EP-03 (US-0360), inchangé.
- propre à l'US : un compte local actif liste les deux commandes disponibles ; désactivé,
  indisponibles, `is_active_account` manquante ; elles suivent `set_access_roles`, dans l'ordre
  de `UserCommand`, et relèvent de `users.write` seul.

**Notes de réalisation.** La proposition de #1738 fait foi. Le service précède l'écran dans le
lot : les fixtures du faux back listent déjà les deux commandes (US-0704), mais le parcours du
service (`frontend/e2e/service/accounts.spec.ts`, le lien d'un compte créé) les attend du
service réel. La retenue locale de la ligne — une désactivation demandée, un lien en route —
reste à l'écran ; son invariant dans les deux sens est d'EP-17 (#949, US-0780/L1).

**Hors périmètre.** Le service d'anonymisation (EP-04).

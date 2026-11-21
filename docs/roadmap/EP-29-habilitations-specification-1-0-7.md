---
id: EP-29
titre: Les habilitations et les comptes suivent la spécification 1.0.7 — le référentiel sous permission, la visibilité d'un projet, le catalogue, les chefs de projet, les administrateurs, le lien de mot de passe
statut: prêt
depend_de: EP-08
famille: front, back
issue:
---

# EP-29 — Habilitations et comptes : suites de la spécification 1.0.7

## Objet

Le tri des constats de spécification du 2026-11-18 (`docs/api/DECISIONS.md`, « Le tri des constats
de spécification », #3349) a tranché, pour la spécification 1.0.7, plusieurs règles d'habilitation
que le code livré ne suit pas : un compte sans rôle lit encore le référentiel, un rôle composé du
seul planning n'ouvre aucun projet, le catalogue porte deux permissions sans effet, une ligne de
coût s'exclut sans être chef de projet, la garde du dernier administrateur compte un compte qui
ne s'est jamais connecté, et un compte que l'annuaire désactive reste actif.

Ces constats étaient étiquetés EP-13. Le cadrage d'EP-13 les en sort (décision de l'auteur du
2026-11-18) : ils touchent les habilitations et le contrat, non l'exploitation, et EP-13 écarte
« toute fonction métier ». L'EPIC reste à cadrer : ses US, sa conception et son rang se décident
à son cadrage.

La ventilation du 2026-11-21 l'élargit aux comptes : il reçoit le bloquant de la revue du
2026-11-14 sur le lien de mot de passe (#3342), qui laisse un porteur de `users.write` seul prendre
un compte administrateur, et les constats de la même revue sur les habilitations du back, l'écran
des comptes et les écrans du référentiel ouverts sans la permission de les consulter. Il est de la
première vague.

Cadré le 2026-11-21 : quatorze US, d'US-3500 à US-3630. Le cadrage a relevé deux points où il
touche le code d'un EPIC voisin, que l'en-tête de la ventilation excluait : la lecture des comptes
et l'écran des sauvegardes, qu'EP-13 modifie (US-3570 et un bouton d'US-3600 attendent sa fusion),
et la survenance d'un risque, qu'EP-30 réécrit après lui (US-3540).

## Ce qui en fait partie

- la lecture du référentiel — les cinq listes, les unités de durée, les paramètres communs, les
  prérequis — sous la permission de consulter sa fonction, la devise de l'installation restant
  lisible par toute session (#3960, #3962 ; US-3500) ; les formulaires des projets ne reçoivent
  aucune lecture propre : les rôles portent la consultation, et le rôle « Administrateur » livré
  reçoit celle des ressources (#3961, tranché le 2026-11-21) ;
- les écrans du référentiel introuvables sans la permission de les consulter, et ceux d'un projet
  ouverts sans elle (#4489 ; US-3510) ;
- la liste et l'ouverture d'un projet par qui consulte l'une de ses fonctions, l'identité seule
  rendue sans la consultation du paramétrage (#3974 ; US-3520) ;
- le catalogue des permissions sans `lifecycle.write` ni `project_indicators.write` (#3975 ;
  US-3530) ;
- l'exclusion et la réintégration d'une ligne de coût, et la survenance d'un risque, réservées aux
  chefs de projet (#3973 ; US-3540) ;
- la garde du dernier administrateur, qui ne compte que les comptes déjà connectés et les quatre
  permissions de l'administration (#3987, #3342 ; US-3550) ;
- le lien de mot de passe, le renvoi d'invitation et le changement d'adresse refusés pour un compte
  plus habilité que l'appelant (#3342 ; US-3560) ;
- la lecture des comptes, qui désactive ceux que l'annuaire tient pour désactivés (#3986 ;
  US-3570) ;
- l'inscription d'un participant sur un projet terminal (#3990 ; US-3580), et la recherche par son
  nom d'un compte que le serveur ne propose pas (#4487 ; US-3590) ;
- l'écran des comptes : le rattachement atteint au clavier, les dialogues annoncés, « Ajouter un
  rôle » offert à qui peut l'attribuer, l'adresse d'un compte local corrigée (#4488, #4492 ;
  US-3600) ;
- annuler et rétablir sur la révision d'un autre projet, refusés comme une révision inconnue (#4490,
  BAC-03 ; US-3610) ;
- l'avatar décodé à la pose (#4491 ; US-3620) ;
- la citation de WF-ADM-0200 dans les opérations qui servent les réglages de l'installation (#3993 ;
  US-3630).

## Ce qui n'en fait pas partie

- l'inscription des chefs de projet au journal d'audit (#3988) — EP-13, qui clôt WF-SEC-0030
  (US-2980) ;
- l'exploitation de la plateforme — EP-13 ;
- une lecture du vocabulaire du référentiel propre aux projets, sous leurs permissions — écartée
  (#3961, décision de l'auteur du 2026-11-21) ;
- ce qui a été demandé avant un retrait de droits et s'achève après — le téléchargement d'un export,
  un import confirmé (#4490, BAC-04) : WF-ADM-0110 n'en dit rien ; un constat de spécification le
  porte, ouvert avec les issues de l'EPIC, et aucun code ici (décision de l'auteur du 2026-11-21) ;
- la version de l'avatar et son `ETag` (#4322) — EP-08 ;
- la survenance d'un risque réécrite en fusion — EP-30, qui reprend la garde d'US-3540.

## Exigences réalisées

Aucune : l'EPIC corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Comme EP-17,
EP-18, EP-23 et EP-32 (décision de l'auteur du 2026-10-28), chaque US cite, avec tout leur Vérif,
les exigences dont ses tests relèvent ; les phrases qu'elle ne touche pas sont des écarts qui disent
qui les constate. Leur portée reste celle des EPIC qui les closent : `WF-ADM-0010-A`,
`WF-ADM-0050-A`, `WF-ADM-0080-A`, `WF-ADM-0090-A` et `WF-ADM-0120-A` (closes par EP-03),
`WF-ADM-0070-A` (EP-04), `WF-ADM-0020-A` (EP-05), `WF-ADM-0110-A` (EP-06), `WF-PRJ-0060-A` (EP-07),
`WF-ADM-0100-A` (EP-08), `WF-CYC-0100-A` (EP-09), `WF-ADM-0200-A` (EP-25), `WF-IHM-0090-A` (EP-02),
`WF-IHM-0100-A` (EP-14).

Cinq phrases de Vérif que la spécification 1.0.7 ajoute, et que les US des EPIC qui closent ces
exigences notent en écart, reçoivent ici le test qui les constate : celle de WF-ADM-0070 (US-3570),
de WF-ADM-0100 (US-3530), de WF-ADM-0120 (US-3550), de WF-PRJ-0060 (US-3540) et de WF-CYC-0100
(US-3580).

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Consommées ou servies, sans changement de leur forme : `listUsers`, `getUser`, `setUserActivation`,
`setUserAccessRoles`, `deleteAccessRole`, `listAccessRoles`, `getAccessRole`, `startIdentitySync`,
`getLatestIdentitySync`, `listContributors`, `listContributorSuggestions`, `undoLastChange`,
`redoLastUndo`, `putMyAvatar`, `getMe`, `listRisks`.

Modifications du contrat, figé (`docs/api/DECISIONS.md`, « La règle d'après le gel ») : chacune
passe par une issue « contrat » que l'auteur tranche et s'inscrit dans ce fichier ; la conception
les arrête, et elles précèdent le code :

- `listOrgNodes`, `listResourceRoles`, `listCalendars`, `getDurationUnits`, `listCostTypes`,
  `listCostCategories`, `getReferenceSettings` et `getReferenceReadiness` déclarent la permission
  qui les garde et leur 404 ; la devise reste lisible par toute session ; `PermissionCode` redit ce
  que chaque permission ouvre (US-3500, #3960, #3962) ;
- `listProjects` et `getProject` s'ouvrent à toute permission de consulter une fonction de FBS-4, et
  le schéma `Project` rend facultatifs les attributs du paramétrage (US-3520, #3974) ;
- `PermissionCode` perd `lifecycle.write` et `project_indicators.write` (US-3530, #3975) ;
- `setActualCostTrackedScope` et `declareRiskOccurrence` déclarent le 403 `NOT_PROJECT_MANAGER`
  (US-3540, #3973) ;
- `UserCommand`, `CommandCondition` et les 409 de `setUserAccessRoles`, `updateAccessRole` et
  `deleteAccessRole` redisent le dernier administrateur — descriptions seules (US-3550) ;
- `createPasswordSetupLink`, `resendInvitation` et `updateUser` déclarent le 403 d'un compte plus
  habilité que l'appelant (US-3560, #3342) ;
- `setContributors` dit ce qu'il accepte sur un projet terminal (US-3580, #3990) ;
- `getUserAvatar` déclare `Cache-Control`, et `putMyAvatar` le 422 d'une image qui ne se décode pas,
  s'il ne le dit pas déjà (US-3620) ;
- `getInstallation`, `getReferenceSettings` et `updateReferenceSettings` citent WF-ADM-0200 —
  descriptions seules (US-3630, #3993).

Une opération manque : la recherche, par son nom, d'un compte à inscrire sur un projet (US-3590,
#4487). C'est une modification du contrat, qui précède le dialogue.

## Préalables

EP-08 fusionné : US-3540 pose sa garde sur la survenance d'un risque, qu'il livre, et US-3520 change
la règle `can_open` qu'EP-11 a réunie à celle des projets — EP-11 fusionné avec lui, comme toute la
première vague.

#3961 est tranché (2026-11-21) : les rôles portent la consultation du référentiel, la devise reste
lisible par toute session, le rôle « Administrateur » livré reçoit `resource_settings.read`.

Deux travaux attendent la fusion d'EP-13, et eux seuls (décision de l'auteur du 2026-11-21) :
US-3570, qui modifie la lecture des comptes (`worker/identity_sync.py`,
`platform/keycloak_admin.py`), et le bouton « Restaurer » d'US-3600 (`backup-commands.tsx`). De
fait, l'auteur prévoit de démarrer l'EPIC après EP-13 ; la dépendance déclarée reste EP-08, et la
ventilation n'est pas changée.

US-3580 touche `set_contributors`, qu'US-2980 d'EP-13 retouche : son lot se tire après la fusion
d'EP-13, ou reprend sa version à la reprise de `main`.

## Définition de fini

- un compte sans rôle reçoit 404 sur les cinq listes du référentiel, les unités de durée et les
  prérequis, et ne lit des paramètres communs que la devise ; l'administrateur d'une installation
  migrée rattache un compte à un nœud ;
- `/reference/risks`, `/reference/indicators` et `/reference/resources`, ouvertes par leur adresse
  sans la permission, présentent l'écran « introuvable » ; les écrans d'un projet s'ouvrent pour un
  rôle sans consultation du référentiel ;
- un rôle « planning seul » liste ses projets, ouvre leur planning, et `getProject` ne lui rend ni
  le client ni la probabilité de gain ;
- `listPermissions` ne rend plus `lifecycle.write` ni `project_indicators.write`, et aucun rôle
  d'une installation migrée ne les porte ;
- un participant porteur de la permission n'exclut pas une ligne de coût et ne déclare pas un risque
  survenu : 403 `NOT_PROJECT_MANAGER` ;
- un administrateur qui a donné son rôle à un compte jamais connecté ne désactive pas le sien, et le
  retrait de `users.read` au dernier administrateur est refusé ;
- un porteur de `users.read` et `users.write` seules n'obtient ni le lien de mot de passe d'un
  administrateur, ni le renvoi de son invitation, ni le changement de son adresse ; contre la
  plateforme, le mot de passe de l'administrateur vaut encore ;
- un compte fédéré que l'annuaire désactive est désactivé à la lecture suivante, constaté contre la
  plateforme ;
- un chef de projet inscrit un participant sur un projet terminal, et y cherche par son nom un
  compte que le serveur ne propose pas ;
- dans la table des comptes, le rattachement se choisit au clavier, et l'adresse d'un compte local
  se corrige ;
- `undoLastChange` sur la révision d'un autre projet répond 404 ; un fichier « `FF D8 FF` suivi de
  HTML » posé comme avatar répond 422 ;
- `make build-openapi`, `make inventory`, `make client-up-to-date` et
  `make server-models-up-to-date` passent, `make inventory` sans raison déclarée pour WF-ADM-0200,
  et `docs/api/DECISIONS.md` a une entrée par modification du contrat ;
- `make check` passe sur la branche de l'EPIC, la file de fusion est verte ; `make roadmap` et
  `make requirements` passent ;
- les dix-sept constats reçus sont fermés par la fusion de leur lot, #3961 par sa décision, et le
  constat de spécification de BAC-04 est ouvert.

## Constats reçus

Reportés d'EP-13 à son cadrage, le 2026-11-18 (décision de l'auteur), et rattachés à l'issue
d'EP-13 jusqu'à l'ouverture de celle de cet EPIC :

- #3960 — contrat : la lecture des objets actifs du référentiel repasse sous permission
  (WF-ADM-0020, WF-ADM-0090) ;
- #3961 — à trancher : les formulaires des projets nomment le référentiel sans la permission de le
  consulter ;
- #3962 — contrat : les paramètres communs et les unités de durée se lisent par toute session ;
- #3973 — back : l'exclusion d'une ligne de coût est réservée aux chefs de projet (WF-ADM-0100,
  WF-PRJ-0060) ;
- #3974 — contrat : un projet se voit de qui consulte l'une de ses fonctions, non le seul
  paramétrage (WF-ADM-0110) ;
- #3975 — contrat : FBS-4.8 et FBS-4.9 n'ont que la permission de consulter (WF-ADM-0100) ;
- #3986 — back : la lecture des comptes désactive ceux que l'annuaire tient pour désactivés
  (WF-ADM-0070) ;
- #3987 — back : la garde du dernier administrateur ne compte que les comptes déjà connectés
  (WF-ADM-0120) ;
- #3993 — contrat : citer WF-ADM-0200 dans les opérations qui servent les réglages de
  l'installation.

Issues ouvertes, rattachées à cet EPIC par la ventilation du 2026-11-21 :

- #3342 — back : un porteur de users.write seul obtient le lien de mot de passe d'un compte
  administrateur, ou change son adresse, et prend le compte (bloquant de la revue du 2026-11-14,
  BAC-01 ; elle porte aussi BAC-02 et CTA-02, la garde du dernier administrateur qui ne compte que
  deux permissions) ;
- #3990 — contrat : l'inscription d'un participant sur un projet terminal (WF-CYC-0100).

Constats de la revue du 2026-11-14 (`docs/reviews/2026-11-14-revue-complete/`), vérifiés le
2026-11-21 contre `main` et les branches d'EP-08, EP-11 et EP-13, encore d'actualité, sans issue
jusque-là ; une issue par ligne, ouverte le 2026-11-21 :

- #4487 — un chef de projet ne peut inscrire que les comptes que le serveur propose (FPL-02) — une
  opération de contrat d'abord ;
- #4488 — la liste du rattachement d'un compte est inatteignable au clavier dans la grille (FAR-02,
  FAR-06) ;
- #4489 — trois écrans du référentiel se présentent par URL directe sans la permission de consulter
  (FAR-03) — #3960 en ferme un, non les deux autres ;
- #4490 — les habilitations du back, WF-ADM-0110 (BAC-03, BAC-04) — BAC-04 demande un arbitrage de
  spécification avant tout code ;
- #4491 — l'avatar : image décodée à la pose (BAC-05) ;
- #4492 — l'écran des comptes : commandes de la table (FAR-04, FAR-08) — FAR-08 après #3342.

Constat de la même revue joint à une issue ci-dessus : BAC-08, l'exclusion d'une ligne de coût sans
la qualité de chef de projet, à #3973.

## Conduite

Vague 1 de la ventilation du 2026-11-21. Créneaux utiles sur le poste, qui porte six livreurs : 2.

L'EPIC est `prêt` : ses US et sa conception sont validées (2026-11-21). Par décision de l'auteur du
même jour, il y reste : le plan de lots n'est pas établi et aucune issue n'est ouverte ; le cadrage
reprend à l'étape 3 de « Démarrer un EPIC » quand l'auteur le demande.

## Conception

Écrite le 2026-11-21, contre `main` (32ba45b09) et les branches `epic/EP-08` (5568efc89),
`epic/EP-11` (0c2d36f70) et `epic/EP-13` (78afe33f2). EP-29 part de `main` une fois EP-08 et EP-11
fusionnés ; deux de ses travaux attendent EP-13 (« Préalables »).

### Ce que le cadrage décide

Onze décisions de l'auteur du 2026-11-21, chacune avec l'option écartée :

| Sujet | Retenu | Écarté, et pourquoi |
|---|---|---|
| les formulaires des projets et le référentiel (#3961) | les rôles portent la consultation du référentiel ; aucune lecture nouvelle | des lectures du vocabulaire propres aux projets, sous leurs permissions : plusieurs opérations ajoutées après le gel, et les écrans des projets rebranchés, quand les rôles livrés « chef de projet » et « manager » portent déjà les quatre consultations |
| la devise | lisible par toute session ouverte, exception à la lettre de #3349 | sous permission comme le reste : les montants perdraient leur devise pour un rôle composé, sur tous les écrans |
| le rattachement d'un compte par l'administrateur | le rôle d'administration reçoit `resource_settings.read` | une lecture des nœuds sous `users.read` : une opération de plus ; ne rien faire : le rattachement livré deviendrait indisponible à l'administrateur livré |
| les prérequis du référentiel (`getReferenceReadiness`) | sous `project_create` ou l'une des quatre consultations du référentiel | la laisser ouverte : une seconde exception à « sans rôle, aucune permission » |
| le lien de mot de passe (#3342) | refus dès que le compte visé porte une permission que l'appelant n'a pas | refuser seulement quand la cible porte `access_roles.write` : un gestionnaire de comptes prendrait encore le compte d'un manager ou d'un chef de projet |
| ce que `getProject` rend sans la consultation du paramétrage (#3974) | l'identité seule | le projet entier : `project_settings.read` ne garderait plus que trois écrans, contre « chaque fonction du projet exige sa propre permission de consulter » |
| les comptes à inscrire (#4487) | une recherche par nom, bornée, identifiant et nom seuls | la liste des comptes actifs : tout chef de projet lirait le personnel entier ; reporter à EP-31 : le Vérif de WF-PRJ-0060 ne serait tenu que par l'API |
| ce qui s'achève après un retrait de droits (BAC-04) | un constat de spécification, sans code | rejuger au service dès maintenant : la spécification précède le code ; abandonner : la question reste posée à WF-ADM-0110 |
| la survenance d'un risque (#3973) | réservée aux chefs de projet ici, sur le code d'EP-08 | la laisser à EP-30 : un participant déclarerait une survenance jusque-là |
| l'adresse d'un compte local (FAR-08) | saisissable dans la table, après la garde d'US-3560 | la renvoyer à EP-31 ou EP-37 : une adresse mal saisie ne se rattrape qu'en anonymisant et en recréant le compte |
| EP-13 | la dépendance déclarée reste EP-08 ; US-3570 et un bouton d'US-3600 attendent EP-13 | déclarer la dépendance et quitter la première vague : l'auteur démarre de fait après EP-13, et ne change pas la ventilation pour cela |

Et ce que la conception tranche elle-même :

| Sujet | Retenu | Écarté, et pourquoi |
|---|---|---|
| la forme de `getReferenceSettings` | une seule opération, que toute session ouverte lit : la devise et la langue par défaut toujours, chaque autre champ avec la permission de consulter sa fonction, absent sinon | la devise dans `getInstallation` : lisible sans session, et deux lectures à tenir d'accord ; trois opérations, une par fonction : trois chemins de plus après le gel |
| quel rôle reçoit `resource_settings.read` | tout rôle non supprimé qui porte `users.write` et `access_roles.write`, comme la migration `0030` | le seul rôle « prédéfini » : la table ne dit pas lequel des trois est l'administrateur, et son libellé se modifie (décision de l'auteur du 2026-11-14) |
| la règle « qui ouvre un projet » | une définition, dans `Viewer` : l'une des neuf consultations, et contributeur ou « consulter tous les projets » ; `can_open` du portefeuille la lit | la dire dans `api/projects.py` seul : le portefeuille dirait ouvrable un projet que la liste refuse (#4131) |
| un attribut du paramétrage non rendu | absent de la réponse | rendu nul : nul dit déjà « non saisi » (le client, le code, la date de commande) |
| le classement `irreversible` / `structuring` du catalogue | inchangé ; la description de `kind` dit qu'il range la matrice et ne décide d'aucune habilitation | reclasser les sept actions structurantes de WF-ADM-0100 : deux valeurs d'une énumération du contrat figé à redéfinir, une migration et les titres de la matrice, sans effet sur aucune autorisation |
| où se juge la qualité de chef de projet | dans le noyau, par `require_project_manager`, comme le marquage et la fusion ; la garde de la route la redit | la garde de la route seule : le worker applique la survenance, et WF-ADM-0110 veut le refus « quel que soit le point d'entrée » |
| ce que Waterfall sait d'une première connexion | une colonne `first_signed_in_at` du compte, écrite à sa première requête authentifiée | interroger Keycloak à chaque garde : un appel réseau sous le verrou de la règle ; `has_password` : ne dit rien d'un compte de l'annuaire |
| les comptes déjà connectés avant la migration | ceux qui ont laissé une trace : auteur d'une inscription du journal d'audit, ou venu d'un fournisseur externe, dont le compte naît d'une connexion ; les autres le deviennent à leur prochaine requête | tous les comptes actifs : le successeur jamais connecté compterait, c'est le défaut ; aucun : un second administrateur ne compterait plus tant qu'il ne revient pas |
| montrer « jamais connecté » à l'écran | non : le refus et la commande indisponible nomment `last_administrator` | un champ de `UserAccount` : une forme de plus au contrat figé pour ce que le refus dit déjà |
| la permission que nomme le refus d'US-3560 | la première, dans l'ordre du catalogue, que la cible porte et que l'appelant n'a pas | `access_roles.write` toujours : faux quand la cible ne la porte pas |
| ce qu'`updateUser` garde | l'adresse seule | toute l'identité : le nom et le prénom ne donnent pas le compte, et se corrigent |
| les commandes d'un compte plus habilité | `create_password_link` et `resend_invitation` ne sont pas listées, comme `set_access_roles` sans `access_roles.write` | listées indisponibles : c'est une permission qui manque, non un état (WF-IHM-0090) |
| `enabled` d'un compte local | non lu : la lecture ne désactive jamais un compte local, elle le rétablit | le désactiver : Waterfall crée et administre les comptes locaux, la console du fournisseur n'en est pas le lieu |
| un projet terminal et ses commandes | `manage_contributors` y devient disponible aux chefs de projet ; l'écran lit l'état, le service refuse tout autre changement | une commande `add_participants` : une valeur d'énumération de plus pour ce que l'état dit déjà |
| la recherche de comptes | deux caractères au moins, vingt comptes au plus, et un témoin qu'il en reste | des pages : une recherche se resserre, elle ne se feuillette pas |
| les dimensions d'un avatar | réduit à 512 pixels de côté au plus, réécrit dans son format | refuser une grande image : une photo de téléphone en fait douze millions ; garder la taille : 8 Mio relus à chaque affichage |
| les avatars déjà posés | laissés tels quels jusqu'à leur remplacement | une migration qui les réécrit : une migration de schéma n'appelle pas le noyau ni Pillow |
| le clavier du rattachement | la liste native remplacée par le `Popover` des rôles de la même ligne | élargir `followLink` et ouvrir la liste native par `showPicker()` : un second chemin dans le clavier de la grille, que tous les écrans partagent |

### Tables et migrations

Aucune table nouvelle. Trois migrations, numérotées à la tête d'`epic/EP-29` au moment du lot :

- **le catalogue (US-3530)** : `lifecycle.write` et `project_indicators.write` quittent
  `access_role_permission`, puis `permission`, et les positions suivantes remontent — la mécanique
  de `0006` et de `0030`. La descente les remet au catalogue, à leur place, sans les rendre à aucun
  rôle : rien ne dit qui les portait.
- **le rôle d'administration (US-3500)** : `resource_settings.read` est donnée à chaque rôle non
  supprimé qui porte `users.write` et `access_roles.write`, et qui ne l'a pas. La descente ne la
  retire pas : rien ne dit qui la portait déjà.
- **la première connexion (US-3550)** : `user_account.first_signed_in_at`, un instant, nul tant que
  le compte ne s'est pas connecté. La migration le remplit pour les comptes qui ont laissé une
  trace — auteur d'une inscription d'`audit_entry`, à son plus ancien `occurred_at` ; origine
  `identity_provider`, à son `created_at`, un tel compte naissant d'une connexion.
  `sessions_closed_at` n'en est pas une : une désactivation l'écrit aussi. La colonne ne compte ni
  dans `lock_version`, ni dans `updated_at` : comme `sessions_closed_at`, elle n'est pas une
  modification du compte.
- aucune pour les autres US : la garde des quatre permissions, la règle des chefs de projet, la
  visibilité d'un projet, le lien de mot de passe, la lecture des comptes et l'avatar ne changent
  aucune colonne.

`core/access_roles/predefined.py` suit les deux premières : `ADMINISTRATOR` gagne
`resource_settings.read`, `PROJECT_MANAGER` et `CONSULTATION` perdent les deux codes ; le test qui
tient cette déclaration au catalogue des migrations passe avec elles. Le témoin (« L'univers
témoin ») et les exemples `access_roles` et `permissions` changent d'autant.

### Les modules du noyau

**`api/evaluation.py`, la garde d'une lecture (US-3500, US-3520).** `Requires` reçoit `one_of`,
comme `RequiresProject` l'a déjà : l'une au moins des permissions nommées, la première nommée
refusée quand l'appelant n'en porte aucune — une consultation, donc 404. Trois emplois :
`getReferenceReadiness` (`cost_settings.read`, `resource_settings.read`, `risk_settings.read`,
`indicator_settings.read`, `project_create`), `listProjects` et `getProject` (les neuf consultations
de FBS-4).

**Les lectures du référentiel (US-3500).** `api/org_nodes.py`, `resource_roles.py` et
`calendars.py` — listes et unités de durée — demandent `resource_settings.read` ;
`api/cost_types.py`, natures et catégories, `cost_settings.read` ; `RequiresForInactive` reste
derrière, inchangé. `getReferenceSettings` garde `Requires()` : la route ne rend de la vue que les
champs que l'appelant consulte — `risk_matrix` sous `risk_settings.read`, `index_thresholds` et
`max_weeks_between_reviews` sous `indicator_settings.read`, `company_name` sous
`installation.read`, `audit` sous l'une des trois —, et toujours `currency_code`,
`default_language` et `lock_version`. La correspondance des champs et des permissions de lecture
se déclare à côté de `FIELD_PERMISSIONS`, qui tient celle d'écriture (`core/cost_settings`).
`updateReferenceSettings` rend le même document, borné de même.

**`core/projects`, qui ouvre un projet (US-3520).** `Viewer` porte la règle entière : `opens` —
l'une des neuf consultations, et contributeur ou `sees_all`. `list_projects` et `judge_project`
la lisent ; `can_open` du portefeuille aussi, qui disait ouvrable par `sees_all` et la qualité
seules. Les neuf codes se déclarent une fois, à côté de `CONSULTATION`. `read_project` et
`list_projects` rendent la vue entière ; c'est la route (`described`) qui omet le client, la
description, le taux d'inflation, la probabilité de gain et la date de commande sans
`project_settings.read`. Le tri (`label`, `code`, `state`, `updated_at`) et la recherche (libellé,
code) ne portent sur aucun attribut omis : rien ne change pour eux.

**`core/projects` et `core/risks`, les actions structurantes (US-3540).**
`Rule("exclude_cost_lines", "cost_line_exclude", manager=True)` ; l'écriture du périmètre suivi
appelle `require_project_manager` avant d'écrire, et sa route passe `manager=True`. Pour la
survenance : `risk_conditions(DECLARE_OCCURRENCE, …)` reçoit la qualité, `judge_risk` et le dépôt
de la tâche appellent `require_project_manager`, la route passe `manager=True` ; le compte rendu
(`getRiskOccurrenceReport`) reste une lecture, ouverte au participant. Un test parcourt les sept
actions de WF-ADM-0100 avec un participant qui en porte la permission.

**`core/access_roles`, le dernier administrateur (US-3550).** `ADMINISTRATION` compte les quatre
permissions. `administrators` ne retient que les comptes actifs dont `first_signed_in_at` n'est
pas nul, par une fonction de l'interface des comptes qui remplace `active_accounts` ici.
`sole_administrator`, `guard_last_administrator`, `guard_deactivation` et la lecture des comptes
(« gardé actif et signalé ») suivent sans être touchés. `api/authentication.py` (`identify`) écrit
`first_signed_in_at`, à l'instant de la connexion du jeton, pour un compte qui ne l'a pas — une
écriture conditionnelle, une fois par compte, par l'interface des comptes. Une installation sans
administrateur compté — l'amorçage, avant la première connexion — n'est refusée de rien : la garde
ne refuse que ce qui en retire le dernier.

**`core/access_roles` et `api/users.py`, un compte plus habilité (US-3560).** L'interface des
rôles expose `outranking` : la première permission, dans l'ordre du catalogue, que porte un compte
et que l'appelant n'a pas ; rien quand il n'en porte aucune de plus, ou que l'appelant agit sur
lui-même. `createPasswordSetupLink`, `resendInvitation` et `updateUser` — quand elle change
l'adresse d'un compte local — la lisent après leurs permissions et avant l'état du compte, et
refusent par 403 `PERMISSION_MISSING`, cette permission nommée, sans appeler le fournisseur ni
rien inscrire. Elle se relit sous le verrou du compte à l'inscription du lien (`inscribe_link`) :
un rôle donné à la cible pendant que le fournisseur forge le lien le fait refuser. `listUsers` et
`getUser` ne listent pas les deux commandes pour un tel compte ; la liste lit les permissions des
comptes de sa page en une requête.

**`platform/keycloak_admin.py`, `core/users/provider.py`, `worker/identity_sync.py` (US-3570).**
`RealmAccount` gagne `is_enabled`, lu du champ `enabled` de la liste du royaume. Un compte qui
n'est pas local et que le fournisseur rend désactivé est tenu pour non détenu : il n'est ni créé,
ni mis à jour, et `deactivate_unheld` le désactive — avec sa garde du dernier administrateur, son
inscription au journal et son compte dans le compte rendu, tels qu'ils sont. Rien ne réactive. Le
test contre la plateforme désactive, par l'API d'administration du royaume, un compte que
l'annuaire OpenLDAP de la plateforme de service fédère, puis relance la lecture des annuaires :
c'est lui qui dit si Keycloak garde `enabled` à faux. Ce qui porte la désactivation d'un annuaire
jusqu'à `enabled` — le « mapper » de contrôle de compte d'Active Directory — est de la console du
fournisseur (WF-ADM-0180) ; le guide d'exploitation le dit.

**`core/projects/interface/contributors.py` (US-3580, US-3590).** Sur un projet terminal,
`set_contributors` accepte la liste lue augmentée de participants, et refuse toute autre
différence comme aujourd'hui (409, `project_not_terminal`) ; la qualité de chef de projet de
l'appelant est jugée comme sur un projet vivant. `manage_contributors` devient disponible sur un
projet terminal. La recherche : l'interface des comptes expose une lecture des comptes actifs, non
anonymisés, dont le nom contient le texte cherché — la comparaison sans casse ni accents que
`_found` emploie déjà —, triés par nom, bornée à vingt et un pour dire s'il en reste ; les
contributeurs du projet en sont retirés.

**`core/revisions`, `core/planning` (US-3610).** `revision_draft` reçoit le projet et ne lit la
révision que dans ce projet : une révision d'un autre projet est absente (404), et aucun verrou
n'est pris. Ses quatre appelants (`writing.py`, `skeleton.py`, `exchanges/running.py`, deux fois)
connaissent le projet. `_turned` ne change pas.

**`core/users/personal.py` (US-3620).** `image_type` devient un décodage : Pillow ouvre l'image —
sa limite de pixels refuse une image démesurée avant de la décoder —, vérifie qu'elle est un PNG ou
un JPEG, la réduit à 512 pixels de côté au plus et la réécrit dans son format, sans métadonnées.
Un contenu qui ne se décode pas est refusé par le 422 d'aujourd'hui. `api/avatars.py` pose
`Cache-Control: private`, sans durée : la durée et le validateur viennent avec la version de
l'avatar (#4322).

**Ce que chacun expose aux autres.** `Viewer.opens` (projets) ; la lecture des comptes connectés,
l'écriture de la première connexion et la recherche par nom (comptes) ; `outranking` (rôles) ;
`revision_draft` avec son projet (révisions). Aucun module ne lit les tables d'un autre.

### Le contrat

Chaque modification passe par une issue « contrat » que l'auteur tranche, et a son entrée dans
`docs/api/DECISIONS.md` (« La règle d'après le gel »). Elles se font d'un bloc, avant le code qui
les sert, avec les exemples, le faux back, le client et les modèles engendrés. Les précédents
gardent `info.version` à `1.0.0` pour des ajouts ; celles-ci retirent deux valeurs d'une
énumération et rendent des champs facultatifs : l'issue de contrat pose la question de la version
à l'auteur.

1. **Le référentiel sous permission (#3960, #3962).** Les sept lectures déclarent leur permission
   et leur 404, avec un exemple de refus ; les phrases « readable by any open session » tombent.
   `ReferenceSettings` ne requiert plus que `currency_code`, `default_language` et `lock_version` ;
   un exemple de plus, celui d'un compte sans rôle. `getReferenceReadiness` déclare son 404.
   `PermissionCode` redit ce que chaque consultation ouvre. Entrée : elle remplace celle de #1745,
   déjà retirée, et dit l'exception de la devise.
2. **La visibilité d'un projet (#3974).** `listProjects` et `getProject` : l'une des neuf
   consultations ; `Project` ne requiert plus `description`, `client`, `order_received_on`,
   `inflation_rate` ni `win_probability`, absents sans `project_settings.read` ; un exemple
   « planning seul ».
3. **Le catalogue (#3975).** `PermissionCode` perd `lifecycle.write` et `project_indicators.write` ;
   les exemples `permissions` et `access_roles` suivent.
4. **Les chefs de projet (#3973).** `setActualCostTrackedScope` et `declareRiskOccurrence`
   déclarent `NOT_PROJECT_MANAGER` dans leur 403 ; la description de `kind` (`Permission`) dit ce
   que le classement est.
5. **Le dernier administrateur.** Descriptions seules : `UserCommand`, `CommandCondition`
   (`last_administrator`), les 409 de `setUserAccessRoles`, `updateAccessRole`, `deleteAccessRole`
   et `setUserActivation` — « actif, déjà connecté, porteur des quatre permissions ».
6. **Un compte plus habilité (#3342).** `createPasswordSetupLink`, `resendInvitation` et
   `updateUser` déclarent le 403 `PERMISSION_MISSING` d'une cible plus habilitée, avec un exemple ;
   `UserCommand` dit quand les deux commandes ne se listent pas. Entrée : elle amende « Attribuer un
   rôle » (#834).
7. **Un projet terminal (#3990).** `setContributors` dit ce qu'il accepte, et son 409 ce qu'il
   refuse encore ; `ProjectCommand` dit `manage_contributors` disponible sur un projet terminal.
8. **La recherche (#4487).** `searchContributorCandidates`,
   `GET /projects/{project_id}/contributor-candidates` : `search` requis, de 2 à 100 caractères ;
   la réponse porte `items` — vingt au plus, chacun `user_id` et `display_name` — et `has_more`.
   Gardée comme `setContributors`, sauvetage du dernier chef de projet compris ; 404 et 403 dans
   les mêmes termes. Exemples sur le témoin, faux back.
9. **L'avatar.** `putMyAvatar` : la description dit le décodage, la réduction et le retrait des
   métadonnées, le 422 inchangé ; `getUserAvatar` déclare l'en-tête `Cache-Control`.
10. **WF-ADM-0200 (#3993).** Trois descriptions ; `INVENTORY.md` régénéré, la raison déclarée
    retirée.

### Le front

- **Les écrans du référentiel (US-3510).** Une garde commune, sous `app/reference` : la permission
  de consulter la fonction de l'écran, lue de la session comme le journal d'audit le fait, ou
  `notFound()`. La correspondance écran → fonction se lit de `navigation/functions.json`, qui
  cache déjà les liens.
- **Les écrans d'un projet (US-3510).** Chaque lecture du référentiel passe par
  `readUnlessRefused` avec `OPTIONAL_READ_REFUSALS`, ce que le devis fait déjà. Sans les unités de
  durée, le Gantt n'offre pas son niveau des heures ; sans les nœuds, le plan de charge n'offre pas
  son filtre par nœud ; sans les rôles ou les catégories, le devis et le reste à engager n'offrent
  pas leurs listes de choix et montrent le libellé que la ligne porte ; sans les catégories, la
  provision d'un risque n'offre pas de choix ; sans les seuils, les indicateurs se lisent sans leur
  qualification. Aucun écran n'invente une valeur par défaut.
- **L'écran des comptes (US-3510, US-3600).** Le rattachement — cellule et barre d'actions — n'est
  offert qu'avec `resource_settings.read`. La cellule devient un bouton qui ouvre un `Popover`,
  comme celle des rôles : Entrée l'ouvre, les flèches y choisissent, le choix écrit `updateUser`
  une fois. « Ajouter un rôle » n'est offert que si une ligne choisie au moins liste
  `set_access_roles`. La colonne de l'adresse reçoit une saisie de texte, bornée à 254 caractères,
  pour les seuls comptes locaux ; le 409 `ALREADY_EXISTS` et le 403 d'US-3560 se disent à la
  cellule. Trois `aria-haspopup="dialog"`.
- **Un projet (US-3520).** La page d'accueil et « aucun projet ouvrable » lisent l'une des neuf
  consultations, non `project_settings.read`. L'entrée d'un projet mène à la première fonction que
  la session consulte, dans l'ordre de `navigation/functions.json` ; l'en-tête du projet ne montre
  que ce que `getProject` rend.
- **Les rôles (US-3530).** La matrice suit `listPermissions` : elle ne change que par ses tests et
  ses exemples.
- **Les contributeurs (US-3580, US-3590).** Le dialogue reçoit, sous les propositions, un champ de
  recherche qui appelle `searchContributorCandidates` à partir de deux caractères, et dit quand il
  reste des comptes ; sur un projet terminal, il n'offre que l'ajout de participants.

### L'ordre de construction

1. Le contrat, d'un bloc : les dix modifications, le client et les modèles engendrés, le faux back
   et ses exemples. Tout ce qui le consomme le suit.
2. Sans attendre le contrat, parce qu'aucune forme n'y change : US-3610 (annuler et rétablir) et
   le noyau d'US-3620 (l'avatar décodé).
3. Les migrations et le noyau, en parallèle une fois le contrat posé : le catalogue (US-3530) ; le
   référentiel sous permission (US-3500) ; la visibilité d'un projet (US-3520) ; les chefs de
   projet (US-3540) ; le dernier administrateur (US-3550), puis le compte plus habilité (US-3560),
   qui touchent tous deux `api/users.py` et `core/access_roles` ; les contributeurs — le projet
   terminal (US-3580), puis la recherche (US-3590).
4. Le front, chaque écran après le service qu'il lit : le référentiel et les projets (US-3510)
   après US-3500 ; un projet (US-3520) ; les contributeurs (US-3580, US-3590) ; l'écran des comptes
   (US-3600) après US-3560 et US-3500.
5. Quand EP-13 est fusionné : la lecture des comptes (US-3570) et le bouton « Restaurer »
   d'US-3600.

### Les EPIC voisins

- **EP-08** livre la survenance d'un risque et la fusion : US-3540 pose sa garde sur la première ;
  la seconde est déjà réservée aux chefs de projet (`merge_applying`). #4322, la version de
  l'avatar, y reste.
- **EP-11** a réuni la règle « qui ouvre un projet » (`Viewer.sees_all`, `can_open`, #4131) et
  retiré `portfolio_projects.read` du chef de projet (`0043`) : US-3520 change cette règle en son
  seul lieu, et US-3530 retouche le même `predefined.py`.
- **EP-13** modifie la lecture des comptes (US-3040, finie) et retouchera `set_contributors`
  (US-2980) et l'écran des sauvegardes (#4104) : US-3570, US-3580 et un bouton d'US-3600 passent
  après lui.
- **EP-30** réécrit la survenance en fusion : il reprend la garde d'US-3540, que la fusion porte
  déjà.
- **EP-34** tient le clavier de la grille : US-3600 ne touche pas `grid-keyboard.ts`.
- **EP-37** reçoit les remarques d'ergonomie : la table des comptes n'est pas refondue ici.
- **EP-38**, « contrat et schéma », vient après : les dix modifications de cet EPIC sont celles de
  ses constats, et ne préjugent pas des siennes.

### Les décisions antérieures que le cadrage reprend

- **#1745**, « les objets actifs du référentiel se lisent par toute session » : déjà retirée par
  #3349 ; cet EPIC en fait le contrat et le service.
- **#3349**, « celles de `getReferenceSettings` et de `getDurationUnits` avec elles » : tenue, hors
  la devise et la langue par défaut, que toute session lit encore (décision de l'auteur du
  2026-11-21).
- **#834**, qui écartait « refuser seulement un rôle qui porte une permission que l'appelant n'a
  pas » pour l'attribution des rôles : la même comparaison est retenue pour le lien de mot de
  passe, le renvoi d'invitation et l'adresse (décision de l'auteur du 2026-11-21). L'attribution
  des rôles, elle, reste sous `access_roles.write`.
- **la ventilation du 2026-11-21**, « il ne touche ni le code d'EP-13, ni celui d'EP-30 » : deux
  fichiers de la lecture des comptes, un de l'écran des sauvegardes, `set_contributors`, et la
  garde de la survenance. L'ordre de fait — EP-29 après EP-13 — le règle sans changer la
  ventilation.

---

## US-3500 — Le référentiel ne se lit que sous la permission de consulter sa fonction, la devise exceptée

- **statut** : à faire
- **exigences** : `WF-ADM-0020-A`, `WF-ADM-0010-A`
- **opérations** : `listOrgNodes`, `listResourceRoles`, `listCalendars`, `getDurationUnits`,
  `listCostTypes`, `listCostCategories`, `getReferenceSettings`, `getReferenceReadiness`,
  `listPermissions`, `listAccessRoles`
- **issue** :

**En tant qu'** administrateur, **je veux** qu'un compte sans rôle ne lise rien du référentiel, et
que chaque permission de consulter une fonction du référentiel garde ses lectures, **afin que** «
sans rôle, aucune permission » soit vrai et que les quatre permissions de consultation du
référentiel gardent autre chose qu'un lien de menu (#3960, #3962, #3961 ; décision #3349).

**Critères d'acceptation.**

- écart : `WF-ADM-0020-A` — « Un rôle d'habilitation composé sur mesure permet à un utilisateur de cumuler des permissions relevant de deux acteurs différents. » : constaté par EP-05 (US-0900), inchangé.
- `WF-ADM-0020-A` — « Réciproquement, un rôle privé d'une permission empêche l'action correspondante, quel que soit l'acteur auquel l'utilisateur ressemble. » : sa forme pour le référentiel : un compte sans rôle reçoit 404 sur `listOrgNodes`, `listResourceRoles`, `listCalendars`, `listCostTypes`, `listCostCategories`, `getDurationUnits` et `getReferenceReadiness`, et ne lit de `getReferenceSettings` que la devise ; un rôle qui porte `resource_settings.read` seule lit les nœuds, les rôles de ressources, les calendriers et les unités de durée, et reçoit 404 sur les natures et les catégories.
- `WF-ADM-0010-A` — « Sur une installation neuve, les trois rôles existent et leurs permissions couvrent les usages des exigences citées. » : le rôle « Administrateur » livré porte en plus `resource_settings.read`, sur une installation neuve comme, par une migration, sur une installation existante : l'administrateur rattache encore un compte à un nœud (`listOrgNodes`, écran des comptes).
- écart : `WF-ADM-0010-A` — « Un utilisateur habilité à gérer les rôles renomme un rôle prédéfini et en modifie les permissions, et il supprime sans erreur un rôle prédéfini qu'aucun compte ne porte. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0010-A` — « La suppression du rôle « administrateur » qu'il porte est refusée (WF-ADM-0090, WF-ADM-0120). » : constaté par EP-03 (US-0380), inchangé.
- propre à l'US : les nœuds, les rôles de ressources, les calendriers et les unités de durée se
  lisent sous `resource_settings.read` ; les natures et les catégories sous `cost_settings.read` ;
  de `getReferenceSettings`, la matrice des risques sous `risk_settings.read`, les seuils d'alerte
  et le délai entre revues sous `indicator_settings.read`, le nom de l'entreprise sous
  `installation.read`. Une lecture refusée l'est par 404, comme un objet inexistant (WF-ADM-0110).
- propre à l'US : la devise de l'installation reste lisible par toute session ouverte, compte sans
  rôle compris (décision de l'auteur du 2026-11-21, exception à #3349, inscrite dans
  `docs/api/DECISIONS.md`) : les montants gardent leur devise sur tous les écrans.
- propre à l'US : `getReferenceReadiness` se lit par qui porte `project_create` ou l'une des quatre
  permissions de consulter le référentiel, et répond 404 aux autres (décision de l'auteur du
  2026-11-21).
- propre à l'US : les objets désactivés et toute écriture restent sous la permission de modifier la
  fonction ; la grille des taux, les taux d'une catégorie et la correspondance restent sous
  `cost_settings.read` : inchangés.
- propre à l'US : aucune lecture nouvelle ne sert le vocabulaire aux formulaires des projets (#3961,
  décision de l'auteur du 2026-11-21) : ce sont les rôles qui portent la consultation — « chef de
  projet » et « manager » portent déjà les quatre —, et un rôle composé sans elles ne lit ni ne
  choisit ces libellés (US-3510).
- propre à l'US : le contrat dit, pour chaque lecture, la permission qui la garde et son 404, et
  `PermissionCode` redit ce que chaque permission ouvre ; les exemples suivent, le faux back avec
  eux ; `docs/api/DECISIONS.md` a son entrée.

**Notes de réalisation.** Aujourd'hui `Requires()` sans permission dans `api/org_nodes.py`,
`resource_roles.py`, `calendars.py`, `cost_types.py`, `reference.py` et `reference_settings.py`.
`getReferenceSettings` rend un seul document pour trois fonctions et la devise : la forme de sa
lecture partielle, et celle de la devise ouverte, sont à la conception. La devise est lue à chaque
page (`frontend/src/currency/request.ts`). Le témoin et les parcours joués avec un compte sans rôle
ou un rôle composé changent d'attendus.

**Hors périmètre.** Les écrans (US-3510). Une lecture du vocabulaire propre aux projets, écartée. Le
catalogue lui-même, qui garde ses quatre permissions de consultation du référentiel.

---

## US-3510 — Les écrans du référentiel sont introuvables sans la permission de les consulter, et ceux d'un projet s'ouvrent sans elle

- **statut** : à faire
- **exigences** : `WF-ADM-0110-A`
- **opérations** : `getReferenceSettings`, `listOrgNodes`, `listResourceRoles`, `listCalendars`,
  `getDurationUnits`, `listCostTypes`, `listCostCategories`, `getMe`
- **issue** :

**En tant qu'** utilisateur dont le rôle ne porte pas la consultation du référentiel, **je veux**
que ses écrans me soient introuvables et que ceux de mes projets s'ouvrent tout de même, **afin
que** l'adresse tapée ne montre pas ce que le menu cache, et qu'un rôle composé reste utilisable
(#4489, FAR-03 ; #3961).

**Critères d'acceptation.**

- écart : `WF-ADM-0110-A` — « Un utilisateur habilité à modifier le planning et porteur de « consulter tous les projets », mais non contributeur d'un projet, voit ce planning et ne peut pas le modifier, ni par la grille ni par import. » : constaté par EP-06 (US-1470), inchangé.
- écart : `WF-ADM-0110-A` — « Inscrit comme contributeur, il le modifie. » : constaté par EP-06 (US-1470), inchangé.
- écart : `WF-ADM-0110-A` — « Un utilisateur sans la permission de consultation ne voit pas le projet, même contributeur ; un contributeur sans « consulter tous les projets » ne voit que ses projets. » : constaté par EP-06 (US-1470), inchangé.
- `WF-ADM-0110-A` — « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même écran. » : `/reference/risks`, `/reference/indicators`, `/reference/resources` et `/reference/costs`, ouvertes par leur adresse sans la permission de consulter leur fonction, présentent l'écran « introuvable », le même que pour une adresse inconnue.
- écart : `WF-ADM-0110-A` — « Un utilisateur connaît la liste de ses permissions effectives, et elle change immédiatement lorsqu'un de ses rôles est modifié. » : constaté par EP-06 (US-1470), inchangé.
- propre à l'US : une session qui porte `risk_settings.read` sans `risk_settings.write` lit l'écran
  des risques sans commande ; de même pour les trois autres écrans.
- propre à l'US : les écrans d'un projet — planning, devis, reste à engager, plan de charge, risques
  — s'ouvrent pour une session qui ne porte aucune permission de consulter le référentiel : aucun ne
  présente d'erreur ; les libellés du référentiel qu'elle ne peut pas lire ne sont pas affichés, et
  les listes de choix qui en dépendent ne sont pas offertes.
- propre à l'US : sur l'écran des comptes, une session sans `resource_settings.read` ne se voit pas
  offrir le rattachement, ni dans la cellule ni dans la barre d'actions.

**Notes de réalisation.** Les trois pages ne lisent de la session que l'écriture (`platformOffer`) ;
le journal d'audit fait déjà la garde voulue (`app/admin/audit-log/page.tsx`, `notFound()`). Ce que
chaque écran d'un projet montre à la place d'un libellé illisible est à la conception, écran par
écran.

**Hors périmètre.** Le service et le contrat (US-3500). L'aide en ligne des écrans.

---

## US-3520 — Un projet se liste et s'ouvre pour qui consulte l'une de ses fonctions

- **statut** : à faire
- **exigences** : `WF-ADM-0110-A`, `WF-ADM-0020-A`
- **opérations** : `listProjects`, `getProject`, `getMe`
- **issue** :

**En tant que** planificateur dont le rôle ne porte que le planning, **je veux** lister mes projets
et ouvrir leur planning, **afin de** travailler sans que mon rôle reçoive la consultation du
paramétrage (#3974 ; spécification 1.0.7, WF-ADM-0110).

**Critères d'acceptation.**

- écart : `WF-ADM-0110-A` — « Un utilisateur habilité à modifier le planning et porteur de « consulter tous les projets », mais non contributeur d'un projet, voit ce planning et ne peut pas le modifier, ni par la grille ni par import. » : constaté par EP-06 (US-1470), inchangé.
- écart : `WF-ADM-0110-A` — « Inscrit comme contributeur, il le modifie. » : constaté par EP-06 (US-1470), inchangé.
- `WF-ADM-0110-A` — « Un utilisateur sans la permission de consultation ne voit pas le projet, même contributeur ; un contributeur sans « consulter tous les projets » ne voit que ses projets. » : sa forme pour un rôle composé : un rôle qui ne porte que `planning.read` et `planning.write` liste les projets dont son porteur est contributeur (`listProjects`), les ouvre (`getProject`) et lit leur planning ; il reçoit 404 sur leur devis ; un compte qui ne porte aucune des neuf permissions de consulter une fonction d'un projet reçoit 404 sur `listProjects` et sur `getProject`, même contributeur.
- écart : `WF-ADM-0110-A` — « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même écran. » : constaté par EP-06 (US-1470), inchangé.
- écart : `WF-ADM-0110-A` — « Un utilisateur connaît la liste de ses permissions effectives, et elle change immédiatement lorsqu'un de ses rôles est modifié. » : constaté par EP-06 (US-1470), inchangé.
- `WF-ADM-0020-A` — « Un rôle d'habilitation composé sur mesure permet à un utilisateur de cumuler des permissions relevant de deux acteurs différents. » : sa forme ici : le rôle « planning seul », que rien n'interdit de composer, ouvre un projet sans porter `project_settings.read`.
- écart : `WF-ADM-0020-A` — « Réciproquement, un rôle privé d'une permission empêche l'action correspondante, quel que soit l'acteur auquel l'utilisateur ressemble. » : constaté par EP-05 (US-0900), inchangé.
- propre à l'US : les neuf permissions sont celles de consulter FBS-4.1 à FBS-4.9 :
  `revisions.read`, `project_settings.read`, `planning.read`, `estimate.read`, `remaining.read`,
  `risks.read`, `actual_costs.read`, `project_indicators.read`, `lifecycle.read`.
- propre à l'US : sans `project_settings.read`, `getProject` ne rend que l'identité du projet —
  libellé, code, état, révision en cours et révision de référence, commandes — et ni le client, ni
  la description, ni le taux d'inflation, ni la probabilité de gain, ni la date de commande, qui
  sont du paramétrage (décision de l'auteur du 2026-11-21) ; `listProjects` suit la même règle pour
  ses colonnes.
- propre à l'US : avec « consulter tous les projets » en plus de l'une des neuf, la liste et
  l'ouverture s'étendent aux projets dont le compte n'est pas contributeur ; les vues du
  portefeuille disent ouvrable (`can_open`) ce que cette même règle ouvre.
- propre à l'US : chaque fonction du projet exige toujours sa propre permission de consulter : rien
  d'autre que la liste et l'ouverture ne s'élargit.
- propre à l'US : à l'écran, la liste des projets se présente à ce rôle, un projet s'ouvre sur la
  première fonction qu'il consulte, et le paramétrage ne lui est ni offert ni atteint par son
  adresse.
- propre à l'US : le contrat le dit — `listProjects`, `getProject`, le schéma `Project` — et
  `docs/api/DECISIONS.md` a son entrée.

**Notes de réalisation.** `api/projects.py`, `CONSULT = "project_settings.read"`, garde aujourd'hui
les deux opérations ; les autres routes d'un projet demandent déjà la permission de leur fonction.
La règle « qui voit le projet » est celle de `Viewer.sees_all` et de `can_open`, qu'EP-11 a réunies
(#4131) : elle se change en un seul lieu.

**Hors périmètre.** Les contributeurs, le lotissement et les sous-projets, qui restent sous
`project_settings.read`. Le carnet du portefeuille, qui compte tous les projets du périmètre.

---

## US-3530 — Le catalogue ne porte plus `lifecycle.write` ni `project_indicators.write`

- **statut** : à faire
- **exigences** : `WF-ADM-0100-A`
- **opérations** : `listPermissions`, `listAccessRoles`, `getAccessRole`, `createAccessRole`,
  `updateAccessRole`, `getMe`
- **issue** :

**En tant qu'** administrateur, **je veux** que la matrice des rôles ne me propose pas deux cases
sans effet, **afin de** composer des rôles dont chaque permission ouvre quelque chose (#3975 ;
spécification 1.0.7, WF-ADM-0100).

**Critères d'acceptation.**

- `WF-ADM-0100-A` — « Chaque fonction de second niveau de l'arborescence est représentée par ses deux permissions, ou par la seule permission de consulter pour FBS-1.3, FBS-1.5, FBS-2.1 à FBS-2.7, FBS-4.8 et FBS-4.9. » : `listPermissions` rend, pour FBS-4.8 et FBS-4.9, la seule permission de consulter ; `lifecycle.write` et `project_indicators.write` ne sont plus des codes du catalogue.
- écart : `WF-ADM-0100-A` — « Un rôle disposant de la modification du chiffrage mais non du marquage permet de modifier un devis et refuse de marquer la révision ; un rôle disposant du marquage mais non de la fusion refuse de fusionner un différentiel. » : constaté par EP-08 (US-2560), inchangé.
- écart : `WF-ADM-0100-A` — « Un utilisateur sans la permission de créer un projet n'en crée pas. » : constaté par EP-08 (US-2560), inchangé.
- écart : `WF-ADM-0100-A` — « Aucun écran ne permet de créer une permission. » : constaté par EP-08 (US-2560), inchangé.
- propre à l'US : une migration retire les deux permissions du catalogue et des rôles qui les
  portent, rôle « chef de projet » livré compris ; aucun autre droit d'aucun compte ne change, et le
  journal d'audit garde ses inscriptions passées.
- propre à l'US : `createAccessRole` et `updateAccessRole` refusent ces deux codes comme tout code
  inconnu du catalogue.
- propre à l'US : l'écran des rôles présente, pour les indicateurs d'un projet et son cycle de vie,
  la seule case « consulter », comme pour les autres fonctions en lecture seule.
- propre à l'US : la déclaration d'une sortie reste sous `project_exit`, inchangée.
- propre à l'US : le contrat (`PermissionCode`, exemples, faux back) et `docs/api/DECISIONS.md`
  suivent.

**Notes de réalisation.** Aucune route ne lit ces deux codes. `core/access_roles/predefined.py`
(`PROJECT_MANAGER`, `CONSULTATION`) et le test qui tient cette déclaration au catalogue des
migrations changent ensemble.

**Hors périmètre.** Le reste du catalogue.

---

## US-3540 — L'exclusion d'une ligne de coût et la survenance d'un risque sont réservées aux chefs de projet

- **statut** : à faire
- **exigences** : `WF-PRJ-0060-A`
- **opérations** : `setActualCostTrackedScope`, `declareRiskOccurrence`, `getProject`, `listRisks`
- **issue** :

**En tant que** chef de projet, **je veux** que les actions structurantes de mon projet me soient
réservées, quel que soit le rôle d'habilitation d'un participant, **afin que** le périmètre suivi et
la survenance d'un risque ne se décident pas sans moi (#3973, BAC-08 ; spécification 1.0.7,
WF-ADM-0100 et WF-PRJ-0060).

**Critères d'acceptation.**

- écart : `WF-PRJ-0060-A` — « La liste d'un projet nouvellement créé comporte son créateur, chef de projet, qui peut y inscrire d'autres utilisateurs. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Un utilisateur habilité à consulter les projets, non contributeur d'un projet et sans la permission « consulter tous les projets », ne l'ouvre pas et ne le trouve pas par son adresse ; le carnet du portefeuille le compte pourtant. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Inscrit comme participant, il l'ouvre et saisit le devis, mais ne marque pas de révision même s'il en porte la permission ; inscrit comme chef de projet, il la marque. » : constaté par EP-07 (US-1540), inchangé.
- `WF-PRJ-0060-A` — « Un participant porteur de la permission d'exclure une ligne de coût ne l'exclut pas. » : `setActualCostTrackedScope` par un participant porteur de `cost_line_exclude` répond 403 `NOT_PROJECT_MANAGER`, pour exclure comme pour réintégrer, et la ligne garde son périmètre ; par un chef de projet du projet, elle aboutit.
- écart : `WF-PRJ-0060-A` — « L'inscription d'un chef de projet figure au journal d'audit. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Un non-contributeur qui inscrit un chef de projet sur un projet dont le dernier est désactivé ne peut retirer aucun participant. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Le retrait du seul chef de projet d'un projet est refusé, de même que son passage en participant ; il est accepté dès qu'un second chef de projet est inscrit. » : constaté par EP-07 (US-1540), inchangé.
- propre à l'US : `declareRiskOccurrence` par un participant porteur de `risk_occurrence` répond 403
  `NOT_PROJECT_MANAGER`, et rien n'est déposé pour le worker ; par un chef de projet, elle aboutit
  (décision de l'auteur du 2026-11-21 : la garde se pose ici, sur le code qu'EP-08 livre).
- propre à l'US : les commandes correspondantes d'un projet et d'un risque suivent la règle des
  autres actions structurantes : un participant ne se les voit pas offrir comme disponibles, et
  l'écran ne les lui présente pas autrement que le marquage.
- propre à l'US : les sept actions structurantes d'un projet que nomme WF-ADM-0100 — marquer une
  révision, en abandonner une, désigner la référence, fusionner un différentiel, déclarer une
  sortie, déclarer un risque survenu, exclure ou réintégrer une ligne de coût — exigent toutes la
  qualité de chef de projet : un test les parcourt, chacune refusée à un participant qui en porte la
  permission.
- propre à l'US : le contrat dit le 403 `NOT_PROJECT_MANAGER` des deux opérations, et
  `docs/api/DECISIONS.md` a son entrée.

**Notes de réalisation.** `api/actual_costs.py` (`RequiresProject(EXCLUDE)`, sans `manager=True`) et
`core/projects/commands.py` (`Rule("exclude_cost_lines", "cost_line_exclude")`) ; sur `epic/EP-08`,
`api/risk_occurrences.py` (`RequiresProject(CONSULT, OCCURRENCE)`) et la commande
`declare_risk_occurrence`. Le catalogue range huit permissions sous `irreversible` et deux sous
`structuring`, ce qui ne suit pas la liste de WF-ADM-0100 : ce qu'en fait le contrat est à la
conception. EP-30, qui fait de la survenance une fusion, reprend cette garde en la réécrivant.

**Hors périmètre.** L'inscription des chefs de projet au journal d'audit (#3988, EP-13).

---

## US-3550 — La garde du dernier administrateur ne compte que les comptes déjà connectés, et les quatre permissions de l'administration

- **statut** : à faire
- **exigences** : `WF-ADM-0120-A`
- **opérations** : `setUserActivation`, `setUserAccessRoles`, `updateAccessRole`,
  `deleteAccessRole`, `listUsers`, `getUser`, `startIdentitySync`
- **issue** :

**En tant qu'** administrateur, **je veux** que la plateforme refuse de me laisser partir tant que
mon successeur ne s'est pas connecté, et de me retirer la consultation sans laquelle mes écrans
répondent 404, **afin qu'** une installation ne se retrouve jamais sans personne pour attribuer des
droits (#3987 ; #3342 pour BAC-02 et CTA-02).

**Critères d'acceptation.**

- `WF-ADM-0120-A` — « La désactivation du dernier compte administrateur est refusée, de même que le retrait de son rôle. » : inchangée dans sa lettre ; le « dernier compte administrateur » est désormais le dernier compte actif, déjà connecté, qui porte `users.read`, `users.write`, `access_roles.read` et `access_roles.write`.
- `WF-ADM-0120-A` — « Elle est acceptée dès qu'un second compte actif, qui s'est déjà connecté, porte ces permissions. » : le second compte, qui porte ces permissions sans s'être jamais connecté, ne suffit pas : la désactivation est acceptée après sa première connexion.
- `WF-ADM-0120-A` — « La modification d'un rôle qui retirerait l'une de ces permissions au dernier compte qui les porte est refusée. » : elle vaut aussi pour une permission de consulter : `updateAccessRole` qui retire `users.read` ou `access_roles.read` au dernier compte qui les porte répond 409 `LAST_ADMINISTRATOR`, et le rôle est inchangé.
- `WF-ADM-0120-A` — « Un administrateur qui a donné son rôle à un compte qui ne s'est jamais connecté ne peut pas désactiver le sien. » : `setUserActivation` répond 409 `STATE_FORBIDS_OPERATION`, la condition `last_administrator` nommée, et sa commande de désactivation est présentée indisponible.
- propre à l'US : ce que Waterfall sait d'une première connexion s'écrit à la connexion même ; sur
  une installation existante, les comptes qui se sont déjà connectés avant la migration sont tenus
  pour tels, de sorte qu'aucune installation ne se retrouve sans administrateur compté.
- propre à l'US : la lecture des comptes garde actif, et signale, le dernier administrateur au sens
  de cette même règle (WF-ADM-0070).
- propre à l'US : une installation qui n'a encore aucun administrateur compté — avant la première
  connexion du compte de l'amorçage — n'est pas refusée pour n'en avoir aucun après.
- propre à l'US : le contrat redit la règle dans `UserCommand`, `CommandCondition` et les 409 de
  `setUserAccessRoles`, `updateAccessRole` et `deleteAccessRole` : aucune forme ne change ;
  `docs/api/DECISIONS.md` a son entrée.

**Notes de réalisation.** `core/access_roles/administrators.py` : `ADMINISTRATION = ("users.write",
"access_roles.write")`, et `administrators()` compte tout compte actif. `user_account` ne porte
aucune trace d'une connexion : la colonne, le lieu où elle s'écrit et la reprise des comptes
existants sont à la conception. La lettre du Vérif dit « les permissions de modifier » ; compter
aussi les deux permissions de consulter est plus strict, et tient son motif (revue du 2026-11-14,
BAC-02, CTA-02). Écarté par la revue : faire valoir la modification pour la consultation, qui change
le sens des 404 partout.

**Hors périmètre.** Le lien de mot de passe (US-3560).

---

## US-3560 — Le lien de mot de passe, le renvoi d'invitation et le changement d'adresse d'un compte plus habilité que l'appelant sont refusés

- **statut** : à faire
- **exigences** : `WF-ADM-0090-A`
- **opérations** : `createPasswordSetupLink`, `resendInvitation`, `updateUser`, `listUsers`,
  `getUser`
- **issue** :

**En tant qu'** administrateur, **je veux** qu'un gestionnaire de comptes ne puisse ni obtenir le
lien de mot de passe de mon compte, ni changer mon adresse, **afin qu'** il ne prenne pas mon compte
et, avec lui, des permissions que personne ne lui a données (#3342, bloquant de la revue du
2026-11-14, BAC-01, CTA-01).

**Critères d'acceptation.**

- écart : `WF-ADM-0090-A` — « Un utilisateur portant deux rôles dispose des permissions des deux. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0090-A` — « Le retrait d'une permission à un rôle en prive tous ses porteurs sans qu'ils aient à se reconnecter. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0090-A` — « La suppression d'un rôle est refusée tant qu'un compte le porte. » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-ADM-0090-A` — « Un rôle supprimé n'apparaît plus dans la liste des rôles ni dans les choix d'attribution ; l'inscription du journal d'audit qui l'attribuait à un compte le nomme toujours. » : constaté par EP-03 (US-0380), inchangé.
- propre à l'US : `createPasswordSetupLink`, `resendInvitation` et `updateUser` qui change l'adresse
  d'un compte local répondent 403 `PERMISSION_MISSING` quand le compte visé porte une permission que
  l'appelant n'a pas ; le refus nomme une permission manquante ; rien n'est inscrit au journal, et
  le fournisseur d'identité n'est pas appelé (décision de l'auteur du 2026-11-21).
- propre à l'US : un appelant qui porte `users.read` et `users.write` seules demande le lien, le
  renvoi et le changement d'adresse d'un compte administrateur : trois refus ; d'un compte sans
  rôle, ou d'un compte qui ne porte que des permissions qu'il a aussi : trois succès.
- propre à l'US : l'appelant qui agit sur son propre compte n'est pas refusé par cette règle.
- propre à l'US : contre la plateforme, après le refus, le mot de passe de l'administrateur vaut
  encore.
- propre à l'US : les commandes du compte visé qui servent ces gestes ne sont pas offertes comme
  disponibles à cet appelant (`listUsers`, `getUser`), et l'écran des comptes ne les lui présente
  pas.
- propre à l'US : le contrat dit le 403 des trois opérations ; `docs/api/DECISIONS.md` a son entrée,
  qui amende « Attribuer un rôle » (#834) : la règle « une permission que l'appelant n'a pas »,
  écartée alors pour l'attribution des rôles, est retenue ici pour la prise d'un compte.

**Notes de réalisation.** `api/users.py` (`WRITE` = `users.read` + `users.write`,
`createPasswordSetupLink`, `updateUser`), `core/users/password_link.py` (`lock_link_holder` : compte
local, non anonymisé, actif, et rien d'autre). La permission que le refus nomme, quand plusieurs
manquent, et les champs d'`updateUser` que la règle garde — l'adresse seule, ou toute l'identité —
sont à la conception. Le service suit aujourd'hui le contrat : c'est la décision qui est reprise.

**Hors périmètre.** Le lien ordinaire forgé pour un compte qui a déjà un mot de passe (extension de
Keycloak), qui reste voulu : c'est la réinitialisation. La garde du dernier administrateur
(US-3550).

---

## US-3570 — Un compte que l'annuaire désactive est désactivé à la lecture suivante

- **statut** : à faire
- **exigences** : `WF-ADM-0070-A`
- **opérations** : `startIdentitySync`, `getLatestIdentitySync`, `listUsers`
- **issue** :

**En tant qu'** administrateur, **je veux** que le compte d'un salarié parti, désactivé et non
supprimé dans l'annuaire, soit désactivé dans Waterfall, **afin qu'** il ne soit plus proposé comme
contributeur ni compté comme administrateur (#3986 ; spécification 1.0.7, WF-ADM-0070).

**Critères d'acceptation.**

- écart : `WF-ADM-0070-A` — « Après lecture, chaque personne de l'annuaire retenue a un compte actif dans Waterfall, sans rôle si elle n'en avait pas, avant toute connexion. » : constaté par EP-04 (US-0930), inchangé.
- écart : `WF-ADM-0070-A` — « Une personne retirée de l'annuaire voit son compte désactivé à la synchronisation suivante, et ses actes restent consultables. » : constaté par EP-04 (US-0930), inchangé.
- écart : `WF-ADM-0070-A` — « Le dernier compte administrateur, retiré de l'annuaire, reste actif et la synchronisation le signale. » : constaté par EP-04 (US-0930), inchangé.
- écart : `WF-ADM-0070-A` — « Un compte local créé depuis Waterfall existe dans le fournisseur d'identité, sans rôle. » : constaté par EP-04 (US-0930), inchangé.
- écart : `WF-ADM-0070-A` — « Une personne ajoutée à l'annuaire a un compte dans Waterfall au terme de la périodicité choisie, sans intervention. » : constaté par EP-04 (US-0930), inchangé.
- écart : `WF-ADM-0070-A` — « Un compte anonymisé dont la personne figure encore dans l'annuaire reste anonymisé après synchronisation, et aucun compte n'est créé à son nom. » : constaté par EP-04 (US-0930), inchangé.
- `WF-ADM-0070-A` — « Un compte que l'annuaire désactive est désactivé à la synchronisation suivante. » : un compte fédéré que le fournisseur d'identité rend `enabled: false` est désactivé par la lecture suivante, à la demande comme à sa périodicité, et compté parmi les comptes désactivés de son compte rendu.
- propre à l'US : le dernier administrateur, désactivé dans l'annuaire, reste actif et la lecture le
  signale, comme pour un compte retiré.
- propre à l'US : un compte que l'annuaire réactive n'est pas réactivé par la lecture : il se
  réactive à la main (WF-ADM-0180, WF-ADM-0060).
- propre à l'US : un compte anonymisé n'est ni modifié ni recréé, inchangé.
- propre à l'US : éprouvé contre la plateforme, avec un annuaire fédéré dont un compte est désactivé
  : le comportement de Keycloak sur ce cas n'a jamais été constaté.

**Notes de réalisation.** `platform/keycloak_admin.py` ne lit pas `enabled` ;
`worker/identity_sync.py` ne désactive que les comptes disparus. **Cette US attend la fusion
d'EP-13**, dont la branche modifie ces deux fichiers (US-3040) : elle seule, avec le bouton «
Restaurer » d'US-3600 (décision de l'auteur du 2026-11-21). Ce que vaut `enabled: false` pour un
compte local, que Waterfall désactive lui-même, est à la conception.

**Hors périmètre.** La périodicité de la lecture (EP-13, US-3040).

---

## US-3580 — Un chef de projet inscrit un participant sur un projet terminal

- **statut** : à faire
- **exigences** : `WF-CYC-0100-A`
- **opérations** : `setContributors`, `listContributors`, `getProject`
- **issue** :

**En tant que** chef de projet, **je veux** inscrire sur une affaire close celui qui chiffre la
suivante, **afin qu'** il la relise sans recevoir « consulter tous les projets » (#3990 ;
spécification 1.0.7, WF-CYC-0100).

**Critères d'acceptation.**

- écart : `WF-CYC-0100-A` — « Toute modification d'un projet terminal est refusée, qu'elle soit tentée par la saisie, par un import Excel ou MS Project, ou par un traitement automatique. » : constaté par EP-09 (US-1620), inchangé.
- `WF-CYC-0100-A` — « L'inscription d'un participant sur un projet terminal aboutit ; il le consulte et n'y modifie rien. » : `setContributors` qui n'ajoute que des participants à la liste d'un projet terminé, perdu ou abandonné aboutit pour un chef de projet du projet ; le participant inscrit ouvre le projet, et toute écriture qu'il y tente est refusée.
- propre à l'US : sur un projet terminal, toute autre modification de la liste — retirer un
  contributeur, changer une qualité, inscrire un chef de projet — reste refusée par 409
  `STATE_FORBIDS_OPERATION`, la condition `project_not_terminal` nommée, et rien n'est écrit.
- propre à l'US : l'écran des contributeurs d'un projet terminal n'offre que l'inscription d'un
  participant.
- propre à l'US : le contrat dit ce que `setContributors` accepte sur un projet terminal, et
  `docs/api/DECISIONS.md` a son entrée.

**Notes de réalisation.** `core/projects/interface/contributors.py`, `set_contributors` : la liste
d'un projet terminal est figée d'un bloc. EP-13 retouche la même fonction (US-2980, #3988) pour le
journal d'audit : le lot se tire après sa fusion dans `main`, ou reprend sa version.

**Hors périmètre.** La recherche des comptes à inscrire (US-3590). L'inscription d'un chef de projet
par un non-contributeur, qui ne vaut que pour un projet non terminal.

---

## US-3590 — Un chef de projet cherche par son nom le compte qu'il inscrit

- **statut** : à faire
- **exigences** : `WF-PRJ-0060-A`
- **opérations** : `listContributorSuggestions`, `setContributors`, `listContributors`
- **issue** :

**En tant que** chef de projet, **je veux** inscrire sur mon projet un compte que le serveur ne me
propose pas, **afin d'** y faire travailler le planificateur et le chiffreur avant qu'aucune ligne
de devis n'existe (#4487, FPL-02).

**Critères d'acceptation.**

- `WF-PRJ-0060-A` — « La liste d'un projet nouvellement créé comporte son créateur, chef de projet, qui peut y inscrire d'autres utilisateurs. » : sur un projet sans ligne de devis, dont le serveur ne propose aucun compte, le chef de projet cherche un compte par son nom dans le dialogue des contributeurs et l'inscrit : `setContributors` reçoit les deux lignes.
- écart : `WF-PRJ-0060-A` — « Un utilisateur habilité à consulter les projets, non contributeur d'un projet et sans la permission « consulter tous les projets », ne l'ouvre pas et ne le trouve pas par son adresse ; le carnet du portefeuille le compte pourtant. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Inscrit comme participant, il l'ouvre et saisit le devis, mais ne marque pas de révision même s'il en porte la permission ; inscrit comme chef de projet, il la marque. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Un participant porteur de la permission d'exclure une ligne de coût ne l'exclut pas. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « L'inscription d'un chef de projet figure au journal d'audit. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Un non-contributeur qui inscrit un chef de projet sur un projet dont le dernier est désactivé ne peut retirer aucun participant. » : constaté par EP-07 (US-1540), inchangé.
- écart : `WF-PRJ-0060-A` — « Le retrait du seul chef de projet d'un projet est refusé, de même que son passage en participant ; il est accepté dès qu'un second chef de projet est inscrit. » : constaté par EP-07 (US-1540), inchangé.
- propre à l'US : une opération nouvelle du projet cherche les comptes par leur nom : elle demande
  un nombre minimal de caractères, ne rend que des comptes actifs et non anonymisés, en nombre
  borné, et de chacun l'identifiant et le nom seuls — ni adresse, ni rôles, ni rattachement
  (décision de l'auteur du 2026-11-21 : un chef de projet n'énumère pas l'annuaire).
- propre à l'US : elle est ouverte à qui peut modifier la liste des contributeurs de ce projet, et
  répond aux autres comme `setContributors` leur répond.
- propre à l'US : les comptes déjà inscrits ne sont pas proposés une seconde fois ; les propositions
  du serveur (`listContributorSuggestions`) restent, au-dessus de la recherche.
- propre à l'US : le dialogue se parcourt au clavier, et un compte trouvé s'inscrit comme
  participant ou comme chef de projet.
- propre à l'US : l'opération entre au contrat avant le code qui la consomme, avec ses exemples, le
  faux back, le client engendré et son entrée dans `docs/api/DECISIONS.md`.

**Notes de réalisation.** Le dialogue n'offre d'ajout que depuis `suggestions`
(`components/projects/contributor-commands.tsx`), et le contrat n'a aucune recherche de comptes hors
`listUsers`, de l'administration. Le nom de l'opération, le nombre minimal de caractères et la borne
sont à la conception.

**Hors périmètre.** `listUsers`, qui reste à l'administration.

---

## US-3600 — L'écran des comptes : le rattachement au clavier, les dialogues annoncés, « Ajouter un rôle » à qui peut l'attribuer, l'adresse d'un compte local corrigée

- **statut** : à faire
- **exigences** : `WF-IHM-0100-A`, `WF-IHM-0090-A`, `WF-ADM-0050-A`
- **opérations** : `listUsers`, `updateUser`, `setUserAccessRoles`, `listOrgNodes`
- **issue** :

**En tant qu'** administrateur, **je veux** rattacher un compte sans souris, ne pas me voir offrir
une action que le serveur me refusera, et corriger une adresse mal saisie, **afin de** tenir les
comptes sans contournement (#4488, FAR-02, FAR-06 ; #4492, FAR-04, FAR-08).

**Critères d'acceptation.**

- `WF-IHM-0100-A` — « Chaque écran se parcourt entièrement au clavier et le focus reste visible. » : dans la table des comptes, Entrée sur la cellule « Rattachement » ouvre la liste des nœuds, un nœud s'y choisit au clavier et `updateUser` est écrit une fois.
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé de contraste ne relève aucun écart au niveau AA. » : constaté par EP-14 (US-0200), inchangé.
- écart : `WF-IHM-0100-A` — « À 150 % d'agrandissement, aucune commande ne devient inatteignable. » : constaté par EP-14 (US-0200), inchangé.
- écart : `WF-IHM-0100-A` — « Un contrôle automatisé ne relève aucun champ de saisie sans libellé associé ni aucune image porteuse d'information sans description. » : constaté par EP-14 (US-0200), inchangé.
- écart : `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en nommant la condition manquante. » : constaté par EP-02 (US-0170), inchangé.
- `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas cette commande. » : sa forme pour l'action groupée « Ajouter un rôle » : une session qui porte `users.write` sans `access_roles.write` ne la voit pas.
- écart : `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas contributeur nomme cette condition. » : constaté par EP-02 (US-0170), inchangé.
- écart : `WF-IHM-0090-A` — « Pendant un traitement de fond sur le projet, la saisie du lotissement est présentée indisponible en nommant le traitement en cours comme condition manquante, et une écriture tentée est refusée en le nommant. » : constaté par EP-02 (US-0170), inchangé.
- écart : `WF-ADM-0050-A` — « La création d'un compte sans nom, sans prénom ou sans adresse est refusée, de même que celle d'un compte dont l'adresse est déjà portée par un autre. » : constaté par EP-03 (US-0360), inchangé.
- `WF-ADM-0050-A` — « Le nom, le prénom et l'adresse d'un compte de l'annuaire ou d'un fournisseur externe ne sont pas modifiables dans Waterfall, hors leur anonymisation (WF-ADM-0060). » : la colonne « Adresse » n'est saisissable que pour un compte local.
- propre à l'US : les trois boutons qui ouvrent un dialogue sans le dire l'annoncent
  (`aria-haspopup="dialog"`) : le lien de fixation et « Remettre le lien » de l'écran des comptes, «
  Restaurer » de l'écran des sauvegardes.
- propre à l'US : l'adresse d'un compte local se saisit dans la table, comme son nom et son prénom ;
  une adresse déjà portée par un autre compte est refusée à la cellule (409 `ALREADY_EXISTS`), et le
  refus d'US-3560, pour un compte plus habilité que la session, s'y présente de même (décision de
  l'auteur du 2026-11-21).
- propre à l'US : le rattachement par la barre d'actions (« Rattacher à ») reste.

**Notes de réalisation.** `components/admin/user-cells.tsx` (`NativeSelect`, `tabIndex={-1}`),
`components/grid/grid-keyboard.ts` (`followLink` ne cherche que `a[href]` et
`button[data-cell-command]`), `components/admin/user-bulk.tsx`, `admin-grids.tsx` (colonne `email`
sans `entry`). La saisie de l'adresse vient après US-3560. Le bouton « Restaurer »
(`backup-commands.tsx`) **attend la fusion d'EP-13**, dont un lot ouvert retouche ce fichier
(#4104). Élargir `followLink` ou remplacer la liste native par le `Popover` des rôles : à la
conception.

**Hors périmètre.** La refonte de la table des comptes.

---

## US-3610 — Annuler et rétablir sur la révision d'un autre projet répondent 404

- **statut** : à faire
- **exigences** : `WF-ADM-0110-A`
- **opérations** : `undoLastChange`, `redoLastUndo`
- **issue** :

**En tant que** chef de projet, **je veux** qu'aucune réponse ne dise à un tiers si une révision de
mon projet existe, ni son état, **afin que** l'inexistant et le non consultable ne se distinguent
pas (#4490, BAC-03).

**Critères d'acceptation.**

- écart : `WF-ADM-0110-A` — « Un utilisateur habilité à modifier le planning et porteur de « consulter tous les projets », mais non contributeur d'un projet, voit ce planning et ne peut pas le modifier, ni par la grille ni par import. » : constaté par EP-06 (US-1470), inchangé.
- écart : `WF-ADM-0110-A` — « Inscrit comme contributeur, il le modifie. » : constaté par EP-06 (US-1470), inchangé.
- écart : `WF-ADM-0110-A` — « Un utilisateur sans la permission de consultation ne voit pas le projet, même contributeur ; un contributeur sans « consulter tous les projets » ne voit que ses projets. » : constaté par EP-06 (US-1470), inchangé.
- `WF-ADM-0110-A` — « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même écran. » : sa forme pour l'API : `undoLastChange` et `redoLastUndo`, appelées sous un projet avec l'identifiant d'une révision d'un autre projet, répondent 404 quel que soit l'état de cette révision, comme pour une révision inconnue.
- écart : `WF-ADM-0110-A` — « Un utilisateur connaît la liste de ses permissions effectives, et elle change immédiatement lorsqu'un de ses rôles est modifié. » : constaté par EP-06 (US-1470), inchangé.
- propre à l'US : aucun verrou n'est pris sur la révision d'un projet que le chemin ne nomme pas.
- propre à l'US : sur une révision du projet nommé, les deux opérations répondent comme aujourd'hui.

**Notes de réalisation.** `core/planning/interface/snapshots.py` (`_turned` juge la révision avant
toute lecture bornée au projet) et `core/revisions/interface/revisions.py` (`revision_draft` lit et
verrouille `FOR SHARE` la révision par son seul identifiant). EP-08 a retouché `snapshots.py` sans
changer cet ordre.

**Hors périmètre.** BAC-04, ce qui a été demandé avant un retrait de droits et s'achève après : un
constat de spécification, sans code dans cet EPIC (décision de l'auteur du 2026-11-21).

---

## US-3620 — Un avatar est décodé à sa pose, débarrassé de ses métadonnées, et servi en cache privé

- **statut** : à faire
- **exigences** : `WF-ADM-0080-A`
- **opérations** : `putMyAvatar`, `getUserAvatar`
- **issue** :

**En tant qu'** utilisateur, **je veux** que la photo que je pose soit bien une image, et qu'elle ne
garde pas ce que mon téléphone y a écrit, **afin que** la plateforme ne serve ni un contenu
arbitraire, ni ma position (#4491, BAC-05).

**Critères d'acceptation.**

- `WF-ADM-0080-A` — « Un utilisateur ajoute, remplace et retire son avatar sans intervention d'un administrateur. » : l'image posée est décodée : un fichier qui porte la signature d'un JPEG suivie d'un contenu qui n'est pas une image est refusé par 422, et l'avatar précédent reste.
- écart : `WF-ADM-0080-A` — « Il ne peut pas modifier celui d'un autre. » : constaté par EP-03 (US-0400), inchangé.
- écart : `WF-ADM-0080-A` — « Un compte sans avatar est affiché avec une image par défaut. » : constaté par EP-03 (US-0400), inchangé.
- propre à l'US : l'image gardée est réécrite sans ses métadonnées — une photo qui porte une
  position EXIF est resservie sans elle — et ses dimensions sont bornées.
- propre à l'US : `getUserAvatar` répond avec `Cache-Control: private`.

**Notes de réalisation.** `core/users/personal.py` ne compare que la signature, trois octets pour un
JPEG ; Pillow est déjà une dépendance du back. La borne des dimensions, et le sort des avatars déjà
posés, sont à la conception. `X-Content-Type-Options: nosniff` est posé par le proxy des plateformes
Compose.

**Hors périmètre.** La version de l'avatar et son `ETag` (#4322, EP-08). `nosniff` dans le chart
Helm (EP-13).

---

## US-3630 — Les opérations qui servent les réglages de l'installation citent WF-ADM-0200

- **statut** : à faire
- **exigences** : `WF-ADM-0200-A`
- **opérations** : `getInstallation`, `getReferenceSettings`, `updateReferenceSettings`
- **issue** :

**En tant que** développeur, **je veux** que le contrat nomme l'exigence que ces trois opérations
servent, **afin que** `make inventory` la couvre sans raison déclarée (#3993).

**Critères d'acceptation.**

- écart : `WF-ADM-0200-A` — « Le nom de l'entreprise se modifie depuis cet écran et figure sur le devis exporté ensuite. » : constaté par EP-25 (US-2120), inchangé.
- écart : `WF-ADM-0200-A` — « L'écran présente la devise, la langue par défaut et le fuseau horaire, et n'offre aucune commande pour les changer. » : constaté par EP-25 (US-2120), inchangé.
- écart : `WF-ADM-0200-A` — « Un utilisateur sans la permission de modifier la fonction lit l'écran sans commande ; sans celle de la consulter, il ne le voit pas. » : constaté par EP-25 (US-2120), inchangé.
- propre à l'US : la description de `getInstallation`, de `getReferenceSettings` et
  d'`updateReferenceSettings` cite WF-ADM-0200 ; aucune forme ne change.
- propre à l'US : `INVENTORY.md` est régénéré, la raison déclarée de `docs/api/tools/inventory.py`
  (`REASONS["ADM"]`) est retirée, et `make inventory` passe.

**Notes de réalisation.** US-2120 d'EP-25 a réalisé l'exigence d'avance, avant la spécification
1.0.7 qui l'écrit. Se livre avec la modification du contrat d'US-3500, qui touche la même opération.

**Hors périmètre.** L'écran des réglages.

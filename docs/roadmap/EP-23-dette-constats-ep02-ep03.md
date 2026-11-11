---
id: EP-23
titre: Les constats laissés ouverts par EP-02 et EP-03, quatre d'EP-06 et huit d'EP-05, sont soldés — le suivi des tâches, les refus, les écrans de l'administration, les comptes, les sauvegardes, le compteur d'écriture, le moteur de planning et le référentiel
statut: en cours
depend_de: EP-02, EP-03, EP-06
famille: front, back
issue: 2858
---

# EP-23 — Dette des constats d'EP-02 et d'EP-03

## Objet

Les revues complètes du front et du back du 2026-11-07 (`main`, 89894959), menées sur le périmètre
livré par EP-03, EP-05 et EP-18, ont laissé une vingtaine de constats ouverts sous les lots d'EP-02
(maquette du front) et d'EP-03 (comptes et habilitations), tous deux livrés. L'auteur les a tranchés
le 2026-11-11 : quinze se corrigent ici, quatre passent à EP-13, qui reprend les sauvegardes, et un
attend la v1. EP-23 corrige les quinze : le suivi des tâches de fond qui s'arrête pour de bon sur une
panne passagère, le décodeur des refus qui prend un composant indisponible pour une erreur
inattendue ou perd la référence d'un refus inconnu, des actions serveur dont le rejet emporte la
page, deux écrans de l'administration qui écrivent deux fois un même rôle ou ignorent une commande
indisponible, et, côté service, le renvoi de l'invitation, un interblocage possible, le journal
technique de l'admission, la liste des sauvegardes après une restauration venue d'ailleurs, une
archive orpheline et un compteur d'écriture qui déborde. Le même jour, l'auteur lui a confié quatre
constats laissés par EP-06, livré : deux du moteur de planning — la passe arrière d'un décalage
écoulé, le départ au plus tard d'une durée écoulée —, et deux de tests — des citations d'exigence et
des exemples lus par un cast. Toujours le 2026-11-11, il lui a confié huit constats laissés par
EP-05, livré, relevés par les mêmes revues : cinq refus du service du référentiel — une liste de
l'arbre qui répond 500 sur une création concurrente, un filtre qui laisse passer le caractère NUL, la
correspondance des coûts réels non amorcée, les années de la grille des taux et le départage d'un
tri, qui s'écartent du contrat —, deux décimaux reçus sans borne ou en chiffres non ASCII, et une
phrase du guide qui offre les objets désactivés sous la permission de lecture.

Il ne sert aucun EPIC de domaine et n'en attend aucun : il se livre en parallèle d'EP-07 et d'EP-09,
sur sa propre branche tirée de `main` après la fusion d'EP-06 (#2855), sans toucher aux fichiers que
leurs derniers lots écrivent (« Préalables »).

## Ce qui en fait partie

- le suivi des tâches de fond de la coquille : une relecture refusée par 500 ou 503 se relit plus
  tard, et la tâche de restauration n'y entre pas (#2257, #2263) — US-1750 ;
- le décodeur des refus du front : une lecture refusée par 503 `COMPONENT_UNAVAILABLE` est la panne
  du composant qu'elle nomme, et un refus dont le code manque au catalogue garde son
  `correlation_id` (#2265, #2264) — US-1760 ;
- les actions serveur du menu du compte et des réglages d'une grille, dont le rejet se dit sous la
  barre, et un identifiant mal formé de l'adresse d'un écran du référentiel ou des comptes, ignoré
  (#2259, #2269) — US-1770 ;
- l'écran des rôles, qui tient la ligne d'un rôle occupée pendant une écriture en cours, et la
  cellule des rôles d'un compte, qui lit la disponibilité de `set_access_roles` (#2261, #2262) —
  US-1780 ;
- le service des comptes : le renvoi de l'invitation d'un compte devenu non local, le verrou de la
  règle du dernier administrateur pris par les routes sœurs des routes gardées, le journal technique
  de l'admission, trois tests qui citent leur exigence (#2226, #2227, #2243, #2244) — US-1790 ;
- le service des sauvegardes : la liste réécrite à la restauration, et l'archive retirée du
  compartiment quand son enregistrement échoue (#2230, #2242) — US-1800 ;
- la borne du compteur d'écriture au contrat, `LockVersion` à `2147483647` au plus, et les
  paramètres de requête qui le portent (#2232) — US-1810 ;
- les casts restants de `i18n/problem.test.ts` (#2846, d'EP-06) — US-1760 ;
- le moteur de planning (`core/planning/scheduling`) : la passe arrière d'un décalage écoulé qui
  atteint un jour sans heure de travail, le départ au plus tard d'une durée écoulée éprouvé pour
  d'autres durées, et trois tests d'API qui citent l'exigence que leur refus porte (#2816, #2832,
  #2845, d'EP-06) — US-1820 ;
- le guide, qui n'offre les objets désactivés du référentiel qu'à la permission d'écriture, et
  l'en-tête du parcours des paramètres des ressources (#2272, et la ligne de #2271 qui restait, d'EP-05)
  — US-1780 ;
- les refus du service du référentiel : la liste de l'arbre d'organisation sur une création
  concurrente et son filtre `code`, la correspondance des coûts réels non amorcée, les années de la
  grille des taux et le tri des catégories par nature (#2228, #2233, #2235, #2237, #2239, d'EP-05) —
  US-1830 ;
- les décimaux à l'entrée du service : une précision maximale pour les seuils et les bornes de la
  matrice, et les chiffres non ASCII refusés dans un `Money` et un `Decimal` (#2234, #2238, d'EP-05)
  — US-1840.

## Ce qui n'en fait pas partie

- les sauvegardes que reprend EP-13 (décision de l'auteur du 2026-11-11) : l'inscription d'audit
  d'une écriture admise avant la maintenance et l'instant unique de ce qui est gardé (#2229), les
  filtres et le tri de `listBackups` (#2231), les commandes `retain` et `release` annoncées
  disponibles (#2241), la reprise d'un dépôt par morceaux interrompu (#2258) — notés dans les
  « Constats reçus » d'EP-13 ;
- les rôles d'habilitation, les comptes et les nœuds d'organisation qui naissent encore à
  `lock_version` 0 (#2779, #2240, fermée) : rien avant la v1, comme pour le projet et son lotissement
  (#2843, option A ; décision de l'auteur du 2026-11-11) ;
- le parcours de bout en bout des sauvegardes (`frontend/e2e/service/backups.spec.ts`), que des
  lots d'EP-07 et d'EP-09 écrivent : aucun lot d'EP-23 ne touche un parcours, hors l'en-tête de
  `frontend/e2e/reference-resources.spec.ts` (US-1780) ;
- le parcours des unités de durée, rejoué contre le service depuis US-1330 (EP-21) : #2271 est
  fermée par l'auteur le 2026-11-11, l'alternance 7/8 de la valeur écrite acceptée comme état
  équivalent ; seule sa ligne d'en-tête restante passe à US-1780 ;
- le critère d'US-0860 qui demandait `resource_settings.read` pour les calendriers désactivés
  (#2245) : l'auteur le corrige dans le fichier d'EP-05 par la pull request de ce cadrage, sans
  lot ;
- les décimaux sans borne des autres champs — les constantes des unités de durée, la capacité d'un
  rôle, les durées et les décalages du planning, les montants d'une ligne de devis d'EP-07 — et les
  autres textes que le contrat lit par `\d` (les mois, les trimestres, le collage d'une durée) :
  hors des décisions de l'auteur, ils sont relevés dans la conception et suivis par une issue à
  trancher (« Décisions ») ;
- le jour courant pris en UTC, faute d'un fuseau de l'installation (#2527, d'EP-06) : EP-13
  (décision de l'auteur du 2026-11-11, « Constats reçus » d'EP-13) ;
- la copie privée d'`identifierOf` dans `components/portfolio/address.ts`, qui laisse passer un
  identifiant qui n'est pas un UUID comme celle que corrige US-1770 : une issue mineure, #2867,
  reportée à EP-11 (décision de l'auteur du 2026-11-11) ;
- toute modification de la spécification ; toute modification du contrat autre que la borne de
  `LockVersion` (US-1810) : #2234 et #2238 se corrigent dans le code, le contrat et
  `docs/api/DECISIONS.md` inchangés (décision de l'auteur du 2026-11-11).

## Exigences réalisées

Aucune : EP-23 corrige le code d'EPIC livrés, et ne clôt ni n'amorce aucune exigence. Comme EP-17
et EP-18 (décision de l'auteur du 2026-10-28), chaque US cite, avec tout leur Vérif, les exigences
dont ses tests relèvent ; les phrases qu'elle ne touche pas sont des écarts qui disent qui les
constate. Leur portée reste celle des EPIC qui les ouvrent et les closent : `WF-IHM-0080-A` (close
par EP-09), `WF-ADM-0160-A` (EP-04), `WF-EXP-0040-A` et `WF-OBS-0020-A` (EP-13),
`WF-INTF-0160-A`, `WF-SEC-0020-A`, `WF-ADM-0010-A`, `WF-ADM-0120-A`, `WF-ADM-0140-A` (EP-03),
`WF-ADM-0040-A` (EP-04), `WF-IHM-0090-A` (EP-02), `WF-PLA-0100-A` et `WF-PLA-0160-A` (EP-06),
`WF-REV-0020-A` (EP-07), `WF-REF-0070-A` (EP-11), `WF-REF-0150-A` (EP-05), `WF-IHM-0060-A` et
`WF-DAT-0100-A` (EP-07), `WF-REF-0160-A` (EP-08), `WF-REF-0170-A` (EP-10).

| Exigence | Titre | Portée | US |
|---|---|---|---|

## Opérations du contrat

Déjà servies, et reprises ici pour ce que les constats y corrigent : `getBackgroundTask`,
`listBackgroundTasks` (US-1750) ; `getMe`, `updateMyPreferences`, et toute lecture d'un écran
(US-1760) ; `updateMyPreferences`, `closeMySessions`, les lectures du référentiel et des comptes
filtrées par un identifiant de l'adresse (US-1770) ; `updateAccessRole`, `deleteAccessRole`,
`setUserAccessRoles`, `listUsers` (US-1780) ; `resendInvitation`, `createUser`, `updateUser`,
`anonymizeUser`, `createPasswordSetupLink`, `getMe` (US-1790) ; `startRestore`, `listBackups`,
`startBackup` (US-1800) ; toute écriture qui porte un `lock_version` (US-1810) ; aucune pour
US-1820, qui corrige le moteur et des tests ; `listOrgNodes`, `getActualCostMapping`,
`setActualCostMapping`, `getHourlyRateGrid`, `listCostCategories` (US-1830) ;
`updateReferenceSettings`, `setHourlyRate`, et toute écriture dont le corps porte un `Money` ou un
`Decimal`, `listNodes` et `listResourceRoles` par leurs bornes (US-1840).

Une seule modification du contrat : `LockVersion` gagne `maximum: 2147483647`
(`docs/api/components/common.yaml`), avec son entrée dans `docs/api/DECISIONS.md` (US-1810). Les
refus d'US-1830 et d'US-1840 sont tous déjà déclarés par leurs opérations (422, 503).

## Préalables

EP-02 et EP-03 livrés (fait). EP-06 fusionné dans `main` (#2855, fait le 2026-11-11) : `epic/EP-23`
se tire de `main` après lui, qui porte `Bucket.remove` (US-1800), le paramètre `lock_version` de la
suppression d'un nœud (US-1810) et les codes d'erreur partagés de `platform/errors.py` (#2763).
Décisions de l'auteur du 2026-11-11.

## Définition de fini

- une relecture d'une tâche de fond refusée par 503 ne met pas fin à son suivi, et la tâche de
  restauration n'entre jamais dans le suivi de la coquille ;
- une lecture d'un écran refusée par 503 `COMPONENT_UNAVAILABLE` mène à la panne du composant
  nommé, et non à l'erreur inattendue ;
- aucune action serveur du menu du compte ni des réglages d'une grille ne fait tomber la page sur
  l'écran de panne quand elle est rejetée ;
- `resendInvitation` sur un compte que Keycloak ne tient plus pour local répond 409
  `is_local_account` ; `updateUser`, `anonymizeUser`, `createPasswordSetupLink` et
  `resendInvitation` prennent le verrou de la règle du dernier administrateur avant celui du compte ;
- `PATCH /access-roles/{id}` avec un `lock_version` de 2147483648 répond 422 ; `make
  build-openapi`, `make inventory`, `make client-up-to-date` et `make server-models-up-to-date`
  passent, et `docs/api/DECISIONS.md` a son entrée ;
- la chaîne de #2816 — A (4 j) → B (1 j), B fin à fin C avec +2 ej, C (1 j) — porte des marges
  nulles et A, B, C critiques ; le départ au plus tard d'une durée écoulée est éprouvé pour 1, 2, 3
  et 5 ej, une avance de 1 à 10 j et un calendrier à jour férié ;
- `GET /reference/org-nodes` répond 200 quand un nœud est créé entre ses deux lectures, et
  `?code=%00` répond 422 sur `/query/code` ; `getActualCostMapping` et `setActualCostMapping`
  répondent 503 `COMPONENT_UNAVAILABLE` sans leur ligne ; `getHourlyRateGrid` avec
  `include_inactive=true&is_active=true` garde dans `years` l'année d'une catégorie désactivée ;
  `listCostCategories` triée par nature départage par le code de la catégorie ;
- un seuil ou une borne de la matrice de plus de dix décimales répond 422 à son champ, et non 500 ;
  `{"amount":"١٢.٥٠"}` répond 422 sur `/amount`, une borne `"٠.٢٥"` sur
  `/risk_matrix/probability_bounds/0` ;
- `make check` passe sur la branche de l'EPIC, la file de fusion est verte ; `make roadmap` et
  `make requirements` passent ;
- les vingt-sept constats sont fermés par la fusion de leur lot, et #2245 par la pull request de
  son cadrage.

## Constats reçus

Relevés par les revues complètes du front et du back du 2026-11-07 (`main`, 89894959), tranchés par
l'auteur le 2026-11-11 ; renommés `[EP-23]`, passés au label `EP-23` et rattachés à leur US à l'ouverture des issues, le
2026-11-11 :

- #2257 — front : une réponse 503 ou 500 à la relecture d'une tâche de fond arrête pour de bon son
  suivi → US-1750 ;
- #2263 — front : la tâche de restauration entre dans le suivi de la coquille → US-1750 ;
- #2265 — front : une lecture refusée par 503 `COMPONENT_UNAVAILABLE` s'affiche comme une erreur
  inattendue (option a) → US-1760 ;
- #2264 — front : un refus dont le code manque au catalogue perd son `correlation_id` → US-1760 ;
- #2259 — front : le menu du compte et l'écriture des préférences d'une grille ne traitent pas une
  action serveur rejetée → US-1770 ;
- #2269 — front : un identifiant qui n'est pas un UUID dans l'adresse d'un écran du référentiel fait
  tomber la page sur l'écran de panne → US-1770 ;
- #2261 — front : le renommage, une case de la matrice et la suppression d'un même rôle partent en
  parallèle (la ligne occupée) → US-1780 ;
- #2262 — front : la cellule des rôles d'un compte ignore `is_available` de `set_access_roles`
  → US-1780 ;
- #2226 — back : `resendInvitation` répond 503 au lieu du 409 `is_local_account` → US-1790 ;
- #2227 — back : interblocage possible entre la lecture des comptes du fournisseur et `updateUser`,
  `anonymizeUser` ou le lien de mot de passe → US-1790 ;
- #2243 — back : le journal technique dit `account.created` pour un compte rattaché ou trouvé
  existant → US-1790 ;
- #2244 — back : trois tests éprouvent le Vérif de WF-ADM-0120 sans citer l'exigence → US-1790 ;
- #2230 — back : après la restauration d'une sauvegarde venue d'une autre installation, la liste
  montre les sauvegardes de la source → US-1800 ;
- #2242 — back : une archive de sauvegarde écrite puis non enregistrée reste orpheline → US-1800 ;
- #2232 — back : un `lock_version` au-delà de 2^31−1 donne 500 au lieu de 412 (la borne au contrat)
  → US-1810.

Laissés par EP-06, livré, et confiés à EP-23 par l'auteur le 2026-11-11 ; renommés `[EP-23]` et
passés au label `EP-23` à l'ouverture des issues :

- #2816 — back : la passe arrière d'un décalage écoulé qui atteint un jour sans heure de travail
  → US-1820 ;
- #2832 — back : le départ au plus tard d'une durée écoulée n'est éprouvé que pour 2 jours écoulés
  → US-1820 ;
- #2845 — back : trois tests d'API citent encore WF-DAT-0020-A, dont le Vérif est une écriture en
  base → US-1820 ;
- #2846 — front : `problem.test.ts` lit encore cinq exemples par un cast → US-1760.

Laissés par EP-05, livré, relevés par les revues complètes du 2026-11-07 et confiés à EP-23 par
l'auteur le 2026-11-11 ; renommés `[EP-23]`, passés au label `EP-23` et rattachés à leur US à
l'ouverture des issues d'US-1830 et d'US-1840, le même jour :

- #2228 — back : `listOrgNodes` répond 500 quand un nœud est créé entre ses deux lectures de
  l'arbre → US-1830 ;
- #2233 — back : le filtre `code` de `listOrgNodes` laisse passer le caractère NUL, 500 au lieu de
  422 → US-1830 ;
- #2235 — back : la correspondance des coûts réels répond 500 quand l'amorçage n'a pas écrit sa
  ligne, là où les paramètres répondent 503 → US-1830 ;
- #2237 — back : les années de `getHourlyRateGrid` changent avec `is_active=true`, contre le
  contrat → US-1830 ;
- #2239 — back : le tri de `listCostCategories` par `cost_type` départage par le code de la
  nature, contre le contrat → US-1830 ;
- #2234 — back : un décimal au-delà des limites de PostgreSQL dans les seuils ou les bornes de la
  matrice donne 500 au lieu de 422 → US-1840 ;
- #2238 — back : des chiffres non ASCII sont acceptés pour un montant (`Money`) et pour une borne
  (`Decimal`) → US-1840 ;
- #2272 — front : le guide offre les objets désactivés du référentiel sous la permission de
  lecture, contre la décision #2084 → US-1780, avec la ligne d'en-tête restante de #2271, fermée.

Laissés de même, et réglés hors des lots : #2245 (le critère d'US-0860, corrigé dans le fichier
d'EP-05 par la pull request de ce cadrage) ; #2240 (fermée, rien avant la v1).

## Conception

Écrite le 2026-11-11 sur `main` (d421d4e2, EP-06 fusionné), après la validation des US par
l'auteur le même jour ; validée par lui le même jour, puis étendue aux quatre constats d'EP-06 qu'il
a confiés à EP-23 (US-1820, et #2846 dans US-1760), puis, sur `main` (419e1e4d), aux huit constats
d'EP-05 qu'il lui a confiés (US-1830, US-1840, et #2272 dans US-1780). Courte, comme celle d'EP-18 : chaque issue porte sa proposition, ses
fichiers et ses tests, et fait foi pour le détail ; ce qui suit ne dit que ce qu'elles laissent
ouvert, ce qui s'en écarte, et ce que les décisions de l'auteur du 2026-11-11 y changent.

**Tables et migrations.** Aucune. Les colonnes `lock_version` sont toutes en `Integer`, que la
borne de US-1810 couvre exactement. US-1830 et US-1840 ne changent aucune colonne : les seuils et les
bornes de la matrice restent des `numeric` sans précision, que la règle d'US-1840 tient sous les
limites de PostgreSQL.

**Modules touchés, et ce que chacun expose.**

- *Front, suivi des tâches* (`components/tasks/tracking.ts`, US-1750) : `refused` ne passe une
  tâche `interrupted` que sur une relecture refusée par 401 ou par 404 ; tout autre refus d'une
  relecture — 500, 503, ou un statut que `getBackgroundTask` ne déclare pas — est traité comme
  `unreachable` : l'entrée garde la tâche, la relit plus tard, et son avis n'est dit qu'une fois, le
  même refus répété ne changeant pas l'entrée. `found` écarte toute tâche de genre `restore`, par une
  table des genres tenue par le typage de `TaskKind` (comme `FILE_RESULT`) ; `running()` du layout
  et `listRunningTasks` passent tous deux par `found`. Aucune autre pièce du suivi ne change.
- *Front, décodeur des refus* (`api/problem.ts`, `components/system/failure.ts`, l'écran de panne,
  le catalogue, US-1760) : `refusalOf`, que partagent `readOrFail` et `readUnlessRefused`, lève une
  nouvelle erreur, `ComponentUnavailable`, sur un 503 dont l'enveloppe porte `COMPONENT_UNAVAILABLE`
  et un `params.component` de `PlatformComponent` ; son `digest` est
  `WATERFALL_COMPONENT_UNAVAILABLE;<composant>`, sur le modèle de `correlationDigest`, et
  `failureOf` en tire une panne `component_unavailable` qui nomme le composant par
  `enums.PlatformComponent`, déjà au catalogue. Une enveloppe 503 sans composant reconnu reste
  `UnexpectedAnswer`. `envelope` garde le `correlation_id` d'un corps dont le code manque au
  catalogue quand il est une chaîne non vide. `session/request.ts` ne change pas : une session
  illisible reste `unreadable`, et la navigation garde l'écran d'état ; c'est la lecture de l'écran
  qui nomme le composant. Le guide (« Les pages système : lecture, panne et « introuvable » ») suit,
  dans ses deux langues. Le même lot retire les casts restants de `i18n/problem.test.ts` (#2846),
  sur la forme de `NODE_CYCLE` : `toMatchObject` sur ce que le test lit de l'exemple, puis un
  `ProblemText` littéral.
- *Front, actions rejetées* (`components/shell/account-menu.tsx`, `components/grid/settings.ts`,
  `components/reference/address.ts`, US-1770) : `apply()` et `signOut()` du menu, et `write` de
  `useKeptWriter.send`, passent leur rejet à `rejected` (`components/commands/rejection.ts`) ;
  `identifierOf` n'accepte qu'un UUID (`isUuid` de `navigation/context.ts`), et ses appelants —
  le référentiel, les ressources, les comptes, l'audit — n'ont rien à changer. La copie privée
  d'`identifierOf` dans `components/portfolio/address.ts` reste hors du lot : le portefeuille n'est
  pas dans le constat.
- *Front, administration* (`components/admin/role-answers.tsx`, `admin-grids.tsx`,
  `permission-matrix.tsx`, `role-commands.tsx`, `user-cells.tsx`, US-1780) : `RoleAnswers` tient,
  à côté des rôles répondus, l'ensemble des rôles en écriture, avec deux gestes — marquer un rôle en
  écriture, le libérer à la réponse, quelle qu'elle soit —, que la cellule du libellé, les cases de
  la matrice et « Supprimer » lisent pour se dire occupés (`aria-busy` sur la ligne,
  `aria-disabled` sur chaque commande) et n'envoyer rien. Le garde `writing` propre à la matrice
  disparaît dans ce mécanisme commun. `RolesCell` lit `offer.is_available` et passe par `useUnmet`
  et `CommandTooltip unavailable`, comme `StateSwitch`. Le guide (« Les écrans de
  l'administration ») remplace « part de la version répondue » par la ligne occupée. Le même lot
  corrige, dans ses deux langues, les deux phrases du guide qui offrent les objets désactivés du
  référentiel à la permission de **lecture** de leur partie (#2272) : « Les grilles » (les listes du
  référentiel que lit le devis ; `README-fr.md` l. 936-938, `README.md` l. 946-948 sur `main`) et
  « Les écrans du référentiel » (`include_inactive` et le filtre d'état, `inactiveQuery` et
  `stateOf` ; `README-fr.md` l. 1453-1458, `README.md` l. 1455-1458) disent la permission
  d'**écriture**, comme la décision #2084, option A, `docs/api/DECISIONS.md` (« Les rôles et les
  catégories actifs se lisent avec le projet ») et le code. Il corrige aussi l'en-tête de
  `frontend/e2e/reference-resources.spec.ts` (l. 6-7, « leave what they found ») : les parcours
  qui écrivent laissent un état équivalent à celui qu'ils ont trouvé, celui des unités de durée
  écrivant l'autre de 7 et de 8 (#2271, fermée ; l'alternance acceptée par l'auteur le
  2026-11-11). Le corps du parcours ne change pas.
- *Back, comptes* (US-1790) :
  - `platform/keycloak_admin.py` : `send_invitation` rend `"not_local"` sur le 409
    `{"error":"not_local"}` de l'extension ; `post_invitation` lève alors `password_link_not_local()`
    sans rien inscrire ; `post_user`, qui crée un compte local, le traite comme une invitation non
    partie ;
  - `api/users.py` : `patch_user`, `post_user_anonymization`, `post_password_link`,
    `post_invitation` et `post_user` prennent `lock_administrators` (interface de
    `core/access_roles`) en tête de leur transaction, avant toute ligne de compte ; la docstring de
    `worker/identity_sync.py` est alors vraie telle quelle, et le reste ;
  - `core/users` : `add_account_of_provider` rend, avec le compte, ce que l'admission a fait — sa
    valeur `Followed` (`created`, `updated` pour un rattachement, `unchanged`) — ; `api/authentication.py`
    journalise `account.created`, `account.attached`, ou rien ; c'est le seul appelant ;
  - les tests : le marqueur `WF-ADM-0120-A` sur les trois tests de #2244.
- *Back, sauvegardes* (US-1800) : `core/backups` réécrit les sauvegardes par
  `replace_by_kept(connection, Backup)`, comme les dépôts ; `worker/backup.py` retire l'archive
  (`Bucket.remove`, déjà dans `main` par EP-06) sur toute exception levée après son écriture, puis
  relève l'exception d'origine ; un retrait qui échoue à son tour se journalise sans la masquer.
- *Moteur de planning* (`core/planning/scheduling/engine.py`, `backend/tests/examples/test_scheduling_examples.py`,
  US-1820) : dans `_Engine.bound`, un décalage écoulé recule depuis la lecture de début du dernier
  instant de l'horloge qui tient le compte de la cible (`calendar.moment(calendar.count(target),
  finish=False)`), comme le début tardif d'une durée écoulée depuis #2648 (`start_for(…,
  latest=True)`) ; la passe avant ne change pas. `_Engine.latest_start` ne change que si le test
  paramétré de #2832 révèle un écart, auquel cas sa correction est dans le lot. Aucune autre pièce du
  moteur, ni de son interface, ne change. Les trois tests d'API de #2845 (`test_nodes_state.py`,
  `test_paste.py`, `test_reference_designation.py`) changent leur seul marqueur.
- *Back, les refus du référentiel* (US-1830) :
  - `core/resource_settings/interface/org_nodes.py` : `list_nodes` tire d'une seule lecture les
    nœuds, leurs niveaux et ceux que les filtres retiennent (la proposition de #2228 : les critères
    lus comme une colonne de la même requête) ; un nœud validé entre deux lectures ne peut plus
    manquer à l'une. `read_node` ne change pas. `api/org_nodes.py` : `NodesQuery.code` est un `Text`,
    comme `search` à côté (#2233) ;
  - `core/cost_settings/interface/actual_cost_mapping.py` : la lecture et le remplacement de la
    correspondance refusent par 503 `COMPONENT_UNAVAILABLE`, `params.component` à `database`, quand
    la ligne de l'amorçage manque (#2235), par le refus de `read_reference_settings`
    (`_not_bootstrapped`, `core/cost_settings/interface/reference_settings.py`), partagé dans
    `core/cost_settings` et journalisé au nom de ce qui manque. La signature de
    `read_actual_cost_mapping` ne change pas : ses appelants d'EP-09 (`core/costs/interface/actual_costs.py:76`,
    `core/costs/extraction.py`, `core/projects/interface/projects.py`, sur `epic/EP-09`) reçoivent
    ce 503 au lieu d'un 500, sans rien changer ;
  - `core/cost_settings/interface/hourly_rates.py` et `api/hourly_rates.py` : la portée des années
    se lit de `include_inactive` vrai ou `is_active` faux, indépendamment des états que la page
    garde (#2237, `HourlyRateGrid.years`) ; `grid_filters` la passe dans `HourlyRateFilters`, à
    côté de `states`. `kept_states` (`api/cost_types.py`), que d'autres listes lisent, ne change
    pas ;
  - `core/cost_settings/interface/cost_categories.py` : la clé `cost_type` du tri se réduit au
    libellé de la nature, le départage restant celui de toute colonne, le code de la catégorie puis
    l'identifiant (#2239) ;
  - les tests vont dans `test_resource_settings_nodes.py` (dont la lecture tenue entre deux étapes
    par une `Barrier`, sur le modèle de `test_two_creations_of_one_code_at_once…`),
    `test_actual_cost_mapping.py`, `test_cost_settings_rates.py` et
    `test_cost_settings_categories.py`, chaque réponse validée contre le contrat.
- *Back, les décimaux à l'entrée* (US-1840) — corrigés dans le code, le contrat et
  `docs/api/DECISIONS.md` inchangés, `api/contract/models.py`, engendré, non plus (décision de
  l'auteur du 2026-11-11) :
  - `api/contract/base.py`, écrit à la main, est la base de chaque modèle que
    `make generate-server-models` engendre : à côté du NUL, il refuse une valeur de `Money` ou de
    `Decimal` — et des types qui les portent, `Percent`, `Hours`… — qui tient un chiffre autre que 0
    à 9, comme une valeur que son motif refuse (422 `VALIDATION_FAILED`, au pointeur du champ ou de
    son élément ; #2238). Le motif du contrat est une expression de JSON Schema, où `\d` ne vaut que
    0 à 9 ; les modèles engendrés le lisent en Unicode. La base reconnaît ces types sans importer
    `models.py`, qui l'importe ; un test confronte la reconnaissance aux modèles engendrés : tout
    type dont la racine porte le motif de `Decimal` ou de `Money` est reconnu, et aucun autre ;
  - les bornes des requêtes, lues à la main, passent de `\d` à `[0-9]` : `api/nodes.py`
    (`DECIMAL`, `MONEY`, `WHOLE`, `DAY`, l. 88-91 sur `main`) et `api/resource_roles.py`
    (`DECIMAL`, l. 82) ; un chiffre non ASCII y est un `NUMBER_INVALID`, comme toute borne mal
    formée. `api/hourly_rates.py` et `core/indicator_settings/thresholds.py` lisent déjà `[0-9]` ;
  - la précision (#2234) : `core/indicator_settings/thresholds.py` (`_in_range`) et
    `core/risk_settings/matrix.py` (`matrix_faults`), qu'appelle `api/reference_settings_write.py`,
    refusent un seuil ou une borne de plus de dix décimales ou de plus de dix chiffres avant le point
    (422 `VALIDATION_FAILED`, à `/index_thresholds/<seuil>` ou à `/risk_matrix/<axe>/<rang>`, tous
    nommés à la fois), comme `RATIO_DECIMALS` refuse un taux de projet trop précis
    (`core/projects/interface/projects.py`) ; un seuil est jugé dans sa forme, puis dans son
    intervalle, puis dans sa précision ; une borne refusée pour sa précision n'est pas jugée dans
    son ordre ;
  - ce qui déborde PostgreSQL, hors de ces deux paramètres (relevé à la lecture des colonnes et du
    code sur `main` et `epic/EP-09`, non rejoué sur une base) : un `numeric` sans précision refuse
    plus de 131 072 chiffres avant le point ou 16 383 après, un `numeric(p, s)` une partie entière
    de plus de p − s chiffres. `Money` ne déborde pas dans `main` : le taux horaire
    (`numeric(12, 2)`) est borné par `GREATEST_RATE` et à deux décimales par son motif, et les bornes
    `rate_min` et `rate_max` de sa grille ne débordent qu'au-delà de 131 072 chiffres entiers dans
    l'adresse ; sur `epic/EP-07` et `epic/EP-09`, les montants d'une ligne de devis
    (`numeric(14, 2)`, bornés en bas seulement par `core/estimate/entries.py`) débordent à treize
    chiffres entiers, et sa quantité (`numeric(14, 4)`) à onze, arrondie en base au-delà de quatre
    décimales. Débordent aussi, dans `main`, les constantes des unités de durée, la capacité d'un
    rôle, les durées et les décalages du planning, bornés en bas seulement. Sont bornés : les heures
    d'un jour d'un calendrier (`numeric(4, 2)`), les taux d'un projet (`numeric(5, 4)`). Ce relevé,
    hors des décisions de l'auteur, est #2875, à trancher ;
  - les tests vont dans un fichier neuf, `test_contract_digits.py` — `setHourlyRate` avec
    `{"amount":"١٢.٥٠"}` sur `/amount`, `updateReferenceSettings` avec une borne `"٠.٢٥"` sur
    `/risk_matrix/probability_bounds/0`, une borne de `listNodes` et de `listResourceRoles`, la
    reconnaissance confrontée aux modèles —, et dans `test_reference_settings.py`, un test par champ
    pour la précision. Aucun ne va dans `test_contract_declarations.py` ni dans `test_nodes.py`.
- *Contrat et service, compteur* (US-1810) : voir « Modifications du contrat ». Les quatre
  paramètres de requête servis (`api/access_roles.py`, `api/subprojects.py`, `api/revisions.py`,
  `api/nodes.py`) passent à `Query(ge=0, le=2147483647)`, que `test_contract_declarations.py`
  confronte au contrat ; `deleteRisk` le prendra d'EP-08.

**Modifications du contrat.** Une seule, faite par US-1810 avant son code : `LockVersion` gagne
`maximum: 2147483647` (`docs/api/components/common.yaml`) ; la description de `LockVersionInvalid`
(`components/responses.yaml`) dit « missing, not a non-negative integer, or beyond 2147483647 » ;
la liste des `maximum` de `Problem.params` nomme le compteur. Entrée dans `docs/api/DECISIONS.md`,
à côté de « `412` pour un `lock_version` périmé », qui cite #2232 — requalifiée issue `contract` —
et la décision de l'auteur du 2026-11-11. Le client du front et les modèles du service sont
régénérés (`make generate-client`, `make generate-server-models`), ce que `make client-up-to-date`
et `make server-models-up-to-date` vérifient.
Tout `lock_version` du contrat référence `LockVersion` (vérifié : corps, réponses et les cinq
paramètres de requête) : la borne les couvre tous.

**Ordre de construction.** Aucune US n'en attend une autre : les dix lots se livrent en
parallèle, à trois contraintes près.

- US-1760 et US-1780 écrivent toutes deux le guide (`docs/dev/README-fr.md`, `README.md`), dans
  des sections différentes — « Les pages système » pour l'une, « Les écrans de l'administration »,
  « Les grilles » et « Les écrans du référentiel » pour l'autre : elles ne se livrent pas en même
  temps (« pas avec »).
- US-1840 et US-1810 écrivent toutes deux `api/nodes.py`, l'une ses motifs des bornes (l. 88-91),
  l'autre le `Query` de `lock_version` (l. 527) : « pas avec ». US-1810 régénère `models.py`, dont
  `base.py` est la base ; la règle d'US-1840 ne dépend pas de ce que la régénération y change.
- US-1830 ne partage aucun fichier avec un autre lot d'EP-23, ni US-1840 hors `api/nodes.py` : leurs
  tests vont dans des fichiers distincts.
- US-1810 change le contrat et régénère le client : aucun autre lot ne touche `docs/api` ni les
  fichiers engendrés, et ses tests ne vont pas dans `test_access_roles.py`, que US-1790 écrit.
- US-1820 ne partage aucun fichier avec un autre lot d'EP-23.

`epic/EP-23` se tire de `main` au premier lot, EP-06 y étant fusionné. Vérifié sur
`origin/epic/EP-09` le 2026-11-11 : EP-07 et EP-09 ne touchent ni les sections du guide qu'écrivent
US-1760 et US-1780 (« Les pages système », « Les écrans de l'administration »), ni celles d'US-1650/L3
(#2416, les entrées non rejouées de l'e2e), ni `LockVersion` ni l'endroit de `DECISIONS.md` où
s'écrit l'entrée ; ils ne changent dans les fichiers du back d'EP-23 que des imports (#2763). Ils
ne touchent ni `engine.py`, ni `test_scheduling_examples.py`, ni `i18n/problem.test.ts` (leurs
seuls changements du moteur sont des ajouts à `scheduling/calendar.py`, qu'US-1820 ne touche pas),
et les lots qui leur restent (US-1570/L3 #2386, US-1650/L3 #2416) n'y vont pas. EP-07 réécrit les
trois fichiers de tests de #2845, mais loin des trois marqueurs, qui ne changent que d'une ligne
chacun. Aucun lot d'EP-23 n'attend donc #2416, et EP-23 se fusionne dans `main` avant ou après EP-07 et EP-09,
celui qui vient second reprenant `main`.

Revérifié pour US-1830, US-1840 et les ajouts d'US-1780 le 2026-11-11, sur `origin/epic/EP-09`
(3d3b4dcb) et sur la branche en cours d'US-1570/L3 (470a134b) : les lots qui restent à EP-07 et à
EP-09 (US-1570/L3 #2386, US-1650/L3 #2416) ne touchent aucun de leurs fichiers. US-1570/L3 écrit
dans « Les grilles » le paragraphe de la comparaison, à cent lignes de celui d'US-1780, et #2810
lui laisse le choix de toucher `api/nodes.py` pour son littéral `CHANGE` (l. 78 de `main`), ce
qu'elle n'a pas fait à ce jour ; aucun ne touche `reference-resources.spec.ts`. Déjà fusionnés sur
leurs branches, EP-07 et EP-09 ne changent, dans les fichiers d'US-1830 et d'US-1840, que des
imports (#2763), ce qu'ils ajoutent à `core/cost_settings` pour le devis, et, dans `api/nodes.py`,
les constantes jusqu'à la ligne qui précède le commentaire des motifs : une ligne inchangée les
sépare du changement d'US-1840, que la reprise de `main` règle sans conflit.

**Décisions.**

- **La ligne d'un rôle occupée, plutôt que des écritures chaînées par rôle** (#2261 ; décision de
  l'auteur du 2026-11-11). Écarté : une file par rôle, comme `UserCommands.reserve` pour les
  comptes, qui ferait partir un renommage après une case sans que l'administrateur le voie attendre,
  et rejouer une suppression sur un rôle que la case vient de changer.
- **Le cas indisponible de `set_access_roles` se construit dans le test** (#2262, option A ;
  décision de l'auteur du 2026-11-11). Le contrat la dit toujours disponible (`UserCommand`,
  `DECISIONS.md`, EP-02/L42d) : un exemple de `fixtures/api` qui la dirait indisponible contredirait
  le contrat. Le test modifie l'exemple `users` sur place, comme celui qui retire déjà toutes les
  commandes d'un compte. Écarté : un exemple nouveau et une issue « contrat ». La proposition
  acceptée de #2262 s'en écarte sur ce seul point.
- **Le verrou de la règle du dernier administrateur se prend dans les routes** (#2227 ; décision de
  l'auteur du 2026-11-11). La décision disait « dans `change`, `anonymize` et `inscribe_link` »,
  mais les couches du noyau (`backend/pyproject.toml`, `access_roles` au-dessus de `users`)
  interdisent à `core/users` d'appeler `core/access_roles`. Les routes qui appellent ces fonctions le
  prennent avant toute ligne de compte, comme `put_user_activation` par `guard_deactivation` : même
  ordre des verrous que la lecture, même effet. Écartés : un import montant de `core/users`, refusé
  par import-linter ; corriger la seule docstring de `identity_sync.py`.
- **Le compteur borné au contrat, refusé par 422** (#2232 ; décision de l'auteur du 2026-11-11). Une
  modification du contrat figé, passée par l'issue `contract` que devient #2232 et inscrite à
  `DECISIONS.md` (« La règle d'après le gel »). Écarté : la comparaison en Python du compteur, ligne
  verrouillée, dans chaque module qui le compare en SQL (`access_roles`, `resource_settings`,
  `cost_settings`, `users`), que proposait l'issue et qui rendait un 412 : huit modules à corriger un
  par un, et le prochain à oublier.
- **Seuls 401 et 404 interrompent le suivi d'une tâche** (#2257 ; décision de l'auteur du
  2026-11-11). Tout autre refus d'une relecture se relit, son avis dit une fois. Écarté :
  n'ajouter que 500 et 503, qui laisserait un statut non déclaré — celui d'un mandataire —
  interrompre pour de bon une tâche qui court.
- **Un 503 `COMPONENT_UNAVAILABLE` d'une lecture est une panne du composant** (#2265, option a ;
  décision de l'auteur du 2026-11-11), dite par l'écran de panne. Écartés : une note au guide qui
  dirait l'erreur inattendue voulue (option b) ; un nouvel état de la session pour `getMe`, quand la
  navigation réagit de même à toute session illisible et que la lecture de l'écran nomme déjà le
  composant.
- **L'admission journalise ce qu'elle a fait** (#2243) : le `Followed` de `core/users/provider.py`
  sort par l'interface, plutôt qu'une seconde lecture du compte par la route. Écarté : un nom
  d'enregistrement unique, `account.admitted`, qui ne dirait plus la création.
- **Une archive écrite et non enregistrée est retirée par la tâche** (#2242), sur toute exception
  levée par elle après l'écriture. Un échec du `commit` qui suit la tâche, dans le runner, n'est pas
  couvert : la rotation d'EP-13 le reprendra, qui liste le compartiment (limite acceptée par
  l'auteur le 2026-11-11). Écarté : une ligne `backup`
  écrite avant l'archive, qui listerait une sauvegarde qui n'existe pas.
- **La passe arrière et le départ au plus tard d'une durée écoulée vont ensemble** (#2816, #2832 ;
  décision de l'auteur du 2026-11-11), dans une US du moteur, au modèle `opus` : les deux touchent
  la symétrie des deux passes sur un jour sans heure de travail. Écarté : un lot de suite d'EP-06,
  livré, que la décision du 2026-11-11 reportait après la livraison.
- **Chaque test de #2845 cite l'exigence dont il éprouve le Vérif**, au cas par cas (décisions de
  l'auteur du 2026-11-11, la seconde sur la proposition du cadrage) : le refus d'une écriture sur une révision marquée, par l'état ou par un
  collage, cite `WF-REV-0020-A` (« quel que soit le point d'entrée »), plutôt que `WF-CYC-0100-A`
  que l'issue proposait en exemple, qui vise un projet terminal ; la désignation d'une révision
  marquée comme référence garde `WF-DAT-0020-A`, dont le Vérif dit « La désignation d'une révision
  marquée comme référence aboutit ». Écarté : `WF-CYC-0100-A` pour les trois.
- **La copie d'`identifierOf` du portefeuille** reste hors d'EP-23 (décision de l'auteur du
  2026-11-11) : une issue mineure la suit, #2867, reportée à EP-11.
- **Les reports** : #2229, #2231, #2241, #2258 et #2527 vont à EP-13 (ses « Constats reçus »),
  #2779 attend la v1, et le fichier d'EP-03, livré, n'est pas touché (décisions de l'auteur du 2026-11-11).
- **Les constats d'EP-05 en deux US neuves, et #2272 dans US-1780** (décisions de l'auteur du
  2026-11-11) : les cinq refus du service dans US-1830, les deux décimaux dans US-1840, la phrase du
  guide dans US-1780, qui écrit déjà le guide et n'est pas commencée. US-1760, en cours de
  livraison, n'est pas touchée. #2240 attend la v1 avec #2779 ; #2245 se corrige dans le fichier
  d'EP-05 par la pull request de ce cadrage, l'auteur la faisant sienne ; #2271 est fermée.
- **Les décimaux corrigés dans le code, pas au contrat** (#2234, #2238 ; décision de l'auteur du
  2026-11-11). Écartés : un `maxLength` ou un motif `[0-9]` au contrat, qui changerait le contrat
  figé, et toute modification de `models.py`, engendré.
- **Les chiffres non ASCII refusés dans la base des modèles, plutôt que route par route** (#2238).
  La base écrite à la main tient déjà le refus du NUL pour tout corps ; elle tient celui-ci pour
  tout `Money` et tout `Decimal`, des écritures d'EP-07 et d'EP-09 comprises après leur fusion.
  Écartés : un contrôle dans `api/hourly_rates.py` et `api/reference_settings_write.py` seuls, qui
  laisserait les constantes, la capacité, les durées, les taux d'un projet et les lignes d'EP-07
  accepter un chiffre arabe, et la prochaine route l'oublier ; changer le moteur des motifs dans la
  génération, qui changerait `models.py`.
- **Dix décimales et dix chiffres entiers au plus, pour les seuils et les bornes** (#2234). Dix
  décimales comme `Hours` (« a ten-billionth of an hour, finer than any entry »,
  `components/common.yaml`), refusées comme un taux de projet trop précis, par `VALIDATION_FAILED`
  à leur champ. Écartés : traduire la `DataError` de PostgreSQL en 422, que proposait aussi #2234,
  qui ne nommerait aucun champ ; quatre décimales comme les taux d'un projet, qui refuseraient un
  pourcentage saisi à trois décimales (12,345 %). Les autres décimaux qui débordent restent hors
  des décisions de l'auteur : #2875, à trancher.
- **Une seule lecture de l'arbre** (#2228), la proposition de l'issue. Écarté : ignorer dans les
  nœuds retenus un identifiant absent des niveaux, qui garderait deux lectures non cohérentes
  (défaut n° 1 de `python.md`).
- **La correspondance non amorcée refusée comme les paramètres** (#2235). Écarté : créer la ligne à
  la lecture, qui écrirait dans une lecture des valeurs que personne n'a choisies.

---

## US-1750 — Le suivi des tâches relit une tâche après une panne passagère, et laisse la restauration à son écran

- **statut** : fini
- **exigences** : `WF-IHM-0080-A`, `WF-ADM-0160-A`
- **opérations** : `getBackgroundTask`, `listBackgroundTasks`
- **issue** : #2860

**En tant que** chef de projet ou administrateur, **je veux** qu'une tâche de fond lancée reste
suivie quand une relecture tombe sur une indisponibilité passagère de la base ou de Redis, et que la
restauration ne se suive que par son écran de maintenance, **afin d'**être informé de son
aboutissement sans voir un « Suivi interrompu » qui n'en est pas un (#2257, #2263).

**Critères d'acceptation.**

- `WF-IHM-0080-A` — « Un utilisateur qui change d'écran pendant un import est informé de son aboutissement. » : éprouvé sur une tâche dont une relecture
  (`GET /tasks/{task_id}`) reçoit l'enveloppe 503, puis l'exemple `running`, puis `succeeded` : le
  succès est au journal (`role="log"`), sans « Suivi interrompu » ; une relecture refusée par 500
  ou par 503 se relit plus tard, comme l'API injoignable, et son refus n'est dit qu'une fois ; seules
  une relecture refusée par 401 ou 404 interrompent le suivi, qui le dit.
- écart : `WF-IHM-0080-A` — « Le marquage d'une révision de dix mille objets laisse l'écran utilisable et présente son avancement. » : constaté par EP-02 (US-0180) et EP-04, inchangé ; EP-09 clôt.
- écart : `WF-IHM-0080-A` — « L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut être relancé. » : idem.
- écart : `WF-ADM-0160-A` — « Après restauration d’une sauvegarde, la plateforme présente exactement les projets, révisions et comptes qu’elle contenait à la date de la sauvegarde, et rien de postérieur, hors le journal d’audit, la liste des sauvegardes et leur planification, qui gardent leurs inscriptions, leurs sauvegardes et leurs réglages ; le journal nomme la restauration. » : le service ; la liste
  des sauvegardes d'une autre installation est corrigée par US-1800, le reste est constaté par EP-03
  (US-0440) et EP-04.
- écart : `WF-ADM-0160-A` — « Une tâche de fond en file ou en cours dans la sauvegarde est en échec après la restauration. » : constaté par EP-03 (US-0440), inchangé.
- écart : `WF-ADM-0160-A` — « La confirmation nomme la date de la sauvegarde. » : sa forme pour le suivi : la restauration se suit par l'écran de sa maintenance, que sa
  confirmation ouvre, et jamais par le suivi de la coquille — une tâche `restore` que
  `listBackgroundTasks` rend, au chargement de la page ou au retour sur l'onglet, n'y entre pas
  (`found` avec une tâche `restore` `queued` laisse les tâches suivies inchangées) ; la
  confirmation elle-même est constatée par EP-03 (US-0440), inchangée.
- écart : `WF-ADM-0160-A` — « Aucune restauration partielle n’est proposée. » : constaté par EP-03 (US-0440), inchangé.
- écart : `WF-ADM-0160-A` — « Une inscription faite après la sauvegarde est encore présente après la restauration, et la dernière inscription est la restauration elle-même. » : constaté par EP-04, inchangé ; #2229 la reprend en EP-13.

**Notes de réalisation.** Les propositions de #2257 et de #2263 font foi, et vont ensemble : si un 503
faisait relire une tâche sans que `restore` soit écarté, la coquille relirait la restauration toute
la durée de sa maintenance, où chaque opération répond 503. Le guide (« Les actions longues et le
suivi des tâches de fond », « L'écran des sauvegardes ») dit déjà la règle — n'interrompent que 404
et 401, la coquille ne reçoit pas la restauration — : c'est le code qui s'en écarte.

**Hors périmètre.** Le décodeur des lectures d'un écran (US-1760) ; la reprise d'un dépôt par
morceaux interrompu (#2258, EP-13).

---

## US-1760 — Une lecture refusée par un composant indisponible le nomme, et un refus inconnu garde sa référence

- **statut** : fini
- **exigences** : `WF-EXP-0040-A`, `WF-OBS-0020-A`
- **opérations** : `getMe`, `updateMyPreferences`, et toute lecture d'un écran
- **issue** : #2864

**En tant que** chef de projet, manager ou administrateur, **je veux** qu'un écran dont la lecture
est refusée parce qu'un composant de la plateforme est indisponible me dise lequel, et qu'un refus
que mon front ne connaît pas me donne la référence que l'exploitant retrouve dans ses journaux,
**afin de** savoir qu'il faut attendre ou quoi signaler, plutôt qu'une « erreur inattendue » muette
(#2265, #2264, #2846).

**Critères d'acceptation.**

- `WF-EXP-0040-A` — « Pendant l'arrêt du stockage objet, une demande d'import est refusée en nommant le composant, et la consultation comme la saisie continuent. » :
  sa forme pour une lecture : une lecture dont l'écran ne peut se passer (`readOrFail`), ou dont il
  se passe (`readUnlessRefused`), refusée par 503 `COMPONENT_UNAVAILABLE` est la panne du composant
  que nomme `params.component` (`PlatformComponent`), dite par l'écran de panne dans les mots du
  catalogue, et non l'erreur inattendue ; éprouvé sur l'exemple 503 du contrat, et sur `getMe`
  refusé pendant que Keycloak ne répond plus (`identity_provider`) ; l'import refusé lui-même est
  d'EP-09, et la plateforme d'EP-13.
- écart : `WF-EXP-0040-A` — « Pendant l'arrêt du worker, un marquage demandé aboutit après le rétablissement, sans nouvelle demande. » : le service, EP-13 clôt.
- écart : `WF-EXP-0040-A` — « Aucune donnée partiellement écrite ne subsiste après le rétablissement d'un composant tombé en cours d'écriture. » : idem ; l'archive de sauvegarde orpheline est
  corrigée par US-1800.
- `WF-OBS-0020-A` — « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul identifiant, que le message présenté à l'utilisateur contient. » : sa forme pour
  un refus que le front ne connaît pas : une enveloppe dont le `code` manque au catalogue reste
  l'erreur inattendue, mais garde le `correlation_id` qu'elle porte quand il a la forme du contrat,
  et l'avis le présente ; le suivi d'un import de bout en bout est d'EP-13.
- écart : `WF-OBS-0020-A` — « Une recherche des secrets et des jetons connus dans les journaux ne les trouve pas. » : EP-13.
- propre à l'US : `i18n/problem.test.ts` ne lit plus aucun exemple par un cast (#2846) : il
  affirme ce qu'il en lit (`toMatchObject`), puis le rend par un `ProblemText` littéral.
- propre à l'US : une enveloppe 503 qui ne nomme pas un composant du contrat, et toute autre réponse
  que le décodeur ne reconnaît pas, restent l'erreur inattendue ; une réponse 502, 503 ou 504 sans
  enveloppe reste l'API injoignable.

**Notes de réalisation.** L'option (a) de #2265 est retenue (décision de l'auteur du 2026-11-11) ; la
proposition de #2264 fait foi. Le guide (« Les pages système : lecture, panne et « introuvable » »)
dit aujourd'hui « toute autre réponse `UnexpectedAnswer` » : il change avec le code. Une action
serveur refusée par 503 rend déjà un `refused` que le catalogue dit en nommant le composant : seules
les lectures changent.

**Hors périmètre.** Le suivi des tâches de fond (US-1750) ; l'écran d'état du système, que le service
ne sert pas encore (#2307, EP-13).

---

## US-1770 — Une action rejetée du compte ou d'une grille se dit sous la barre, et un identifiant mal formé de l'adresse est ignoré

- **statut** : fini
- **exigences** : `WF-INTF-0160-A`, `WF-SEC-0020-A`, `WF-ADM-0040-A`
- **opérations** : `updateMyPreferences`, `closeMySessions`, les lectures du référentiel et des
  comptes filtrées par un identifiant de l'adresse
- **issue** : #2861

**En tant que** chef de projet, manager ou administrateur, **je veux** que le choix de ma langue, ma
déconnexion ou la largeur d'une colonne, quand le serveur de Next ou ma connexion tombe, me disent
« service injoignable » sous la barre sans remplacer ma page par l'écran de panne, et qu'un lien
tronqué vers un écran du référentiel ou des comptes l'ouvre sans son filtre, **afin de** garder ce
que je lisais (#2259, #2269).

**Critères d'acceptation.**

- `WF-INTF-0160-A` — « Le changement de langue s'applique sans reconnexion. » : choisie alors que l'action serveur est rejetée (`TypeError("fetch
  failed")`), la langue n'est pas changée, l'alerte « Le service est injoignable… » est sous la
  barre, et la page reste, sans écran de panne ni relecture du document.
- écart : `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande l'anglais obtient l'interface en anglais à sa première connexion, un autre demandant le français l'obtient en français. » : constaté par
  EP-03 (US-0400), inchangé.
- écart : `WF-INTF-0160-A` — « Un utilisateur dont le navigateur demande une langue non offerte obtient la langue par défaut de l'installation. » : idem.
- écart : `WF-INTF-0160-A` — « Un utilisateur qui force le français le retrouve en se connectant depuis un autre poste dont le navigateur demande l'anglais. » : idem.
- `WF-SEC-0020-A` — « Un utilisateur qui se déconnecte ne peut plus agir avec ses jetons. » : sa forme pour une déconnexion qui n'aboutit pas : « Se
  déconnecter » dont l'action est rejetée dit l'API injoignable sous la barre, sans écran de panne,
  et la session reste ; la déconnexion qui aboutit est constatée par EP-03 (US-0350), inchangée.
- écart : `WF-SEC-0020-A` — « La désactivation d'un compte connecté sur deux postes interrompt les deux à leur requête suivante. » : constaté par EP-03 (US-0350), inchangé.
- écart : `WF-SEC-0020-A` — « Un jeton de rafraîchissement inactif au-delà de deux heures est refusé, et l'utilisateur est ramené à l'écran de connexion puis, reconnecté, à l'écran visé. » : idem.
- écart : `WF-SEC-0020-A` — « Une adresse de retour qui ne désigne pas un écran de Waterfall — l'adresse d'un autre site, un chemin qui commence par « // », ou qui contient une barre oblique inverse ou un caractère de contrôle — ramène à l'accueil après la connexion. » : idem.
- `WF-ADM-0040-A` — « Un utilisateur modifie ses préférences et ne peut pas modifier celles d’un autre. » : sa forme pour une écriture qui n'aboutit pas : le
  réglage d'une grille ou d'un graphique gardé (`updateMyPreferences`, par `useKeptWriter`) dont
  l'action est rejetée dit l'API injoignable, sans écran de panne ; le reste est constaté par EP-03
  (US-0400).
- écart : `WF-ADM-0040-A` — « Deux utilisateurs ouvrant le même projet voient les mêmes données présentées selon leurs réglages respectifs. » : EP-04 clôt, inchangé.
- propre à l'US : un identifiant de l'adresse qui n'est pas un UUID — `/reference/costs?cost_type_id=abc`
  — n'est pas retenu, comme un identifiant absent : l'écran s'ouvre sans ce filtre, et aucune
  lecture ne part avec lui ; de même pour les écrans des ressources et des comptes, qui lisent
  l'adresse par la même fonction.

**Notes de réalisation.** Les propositions de #2259 et de #2269 font foi. La règle est celle du guide
(« Réagir à un refus côté front », #330) : un rejet passe par `rejected`. `isUuid` existe déjà
(`navigation/context.ts`).

**Hors périmètre.** Toute autre action serveur ; elles passent déjà par `rejected` ou
`useHeldCommand`.

---

## US-1780 — L'écran des rôles n'écrit pas deux fois un même rôle en même temps, et l'attribution indisponible le dit

- **statut** : fini
- **exigences** : `WF-ADM-0010-A`, `WF-IHM-0090-A`
- **opérations** : `updateAccessRole`, `deleteAccessRole`, `setUserAccessRoles`, `listUsers`
- **issue** : #2865

**En tant qu'**administrateur, **je veux** que la ligne d'un rôle soit occupée tant qu'une écriture
de ce rôle est en route, et que l'attribution des rôles d'un compte, quand le serveur la dit
indisponible, me le dise avec sa condition sans rien envoyer, **afin de** ne pas recevoir un 412 que
je n'ai pas provoqué, ni un refus que l'écran savait d'avance (#2261, #2262) ; **en tant que**
développeur, que le guide dise sous quelle permission les écrans offrent les objets désactivés du
référentiel (#2272).

**Critères d'acceptation.**

- écart : `WF-ADM-0010-A` — « Sur une installation neuve, les trois rôles existent et leurs permissions couvrent les usages des exigences citées. » : constaté par EP-03 (US-0380), inchangé.
- `WF-ADM-0010-A` — « Un administrateur renomme un rôle prédéfini et en modifie les permissions, et il supprime sans erreur un rôle prédéfini qu’aucun compte ne porte. » : sa forme quand ces
  gestes se suivent avant la réponse du premier : tant qu'une écriture d'un rôle est en route — son
  renommage, une case de la matrice, sa suppression confirmée —, la cellule de son libellé, ses
  cases et sa commande « Supprimer » sont occupées (`aria-busy`, `aria-disabled`) et n'envoient
  rien ; la réponse reçue, l'écriture suivante part avec la `lock_version` et les permissions
  répondues, sans 412 ; une écriture d'un autre rôle n'attend pas.
- écart : `WF-ADM-0010-A` — « La suppression du rôle « administrateur » qu’il porte est refusée (WF-ADM-0090, WF-ADM-0120). » : constaté par EP-03 (US-0380), inchangé.
- écart : `WF-IHM-0090-A` — « Sur un projet en chiffrage, la commande de terminaison est présentée indisponible en nommant la condition manquante. » : la terminaison est d'EP-04 ;
  ici, sa forme pour un compte : un compte qui liste `set_access_roles` indisponible présente le
  déclencheur de la cellule de ses rôles `aria-disabled`, décrit par sa condition, et un clic dit la
  condition sans ouvrir la liste ni envoyer `PUT /users/{user_id}/access-roles`, comme
  l'activation, le lien et l'anonymisation du même compte.
- écart : `WF-IHM-0090-A` — « Un utilisateur sans la permission de marquer une révision ne voit pas cette commande. » : le marquage est d'EP-04 ; sa forme pour un
  compte — un compte qui ne liste pas `set_access_roles` ne présente pas sa liste — est constatée
  par EP-03 et EP-18, inchangée.
- écart : `WF-IHM-0090-A` — « Un refus de saisie sur un projet dont l'utilisateur n'est pas contributeur nomme cette condition. » : EP-04, sans objet pour un compte.
- écart : `WF-IHM-0090-A` — « Pendant un traitement de fond sur le projet, la saisie du lotissement est présentée indisponible en nommant le traitement en cours comme condition manquante, et une écriture tentée est refusée en le nommant. » : EP-04 et EP-06, sans objet pour un compte.
- propre à l'US : le guide, dans ses deux langues, n'offre les objets désactivés du référentiel
  (`include_inactive`) et le filtre par état qu'à une session qui porte la permission d'écriture de
  leur partie, dans « Les grilles » comme dans « Les écrans du référentiel » (#2272, #2084,
  option A) ; `make readmes` passe.
- propre à l'US : l'en-tête de `frontend/e2e/reference-resources.spec.ts` ne dit plus que les
  parcours qui écrivent laissent ce qu'ils ont trouvé, mais un état équivalent, le parcours des
  unités de durée écrivant l'autre de 7 et de 8 (#2271).

**Notes de réalisation.** Pour #2261, l'auteur a retenu la ligne occupée, plutôt que des écritures
chaînées par rôle (décision du 2026-11-11) ; la proposition de #2262 fait foi. Le contrat liste
aujourd'hui `set_access_roles` toujours disponible (`UserCommand`) : le cas est latent, et le test le
construit (« Conception »). #2272 et la ligne restante de #2271 y sont passés le 2026-11-11, l'US
n'étant pas commencée (décision de l'auteur) : seuls le guide et un commentaire changent.

**Hors périmètre.** La table des comptes et ses autres commandes, déjà retenues (EP-17, #949).

---

## US-1790 — Comptes : le renvoi de l'invitation d'un compte devenu non local, l'ordre des verrous, le journal de l'admission

- **statut** : fini
- **exigences** : `WF-ADM-0140-A`, `WF-ADM-0120-A`
- **opérations** : `resendInvitation`, `createUser`, `createPasswordSetupLink`, `updateUser`,
  `anonymizeUser`, `getMe`
- **issue** : #2859

**En tant qu'**administrateur, **je veux** que le renvoi de l'invitation d'un compte que le
fournisseur ne tient plus pour local me le dise comme le lien de fixation, qu'une modification d'un
compte n'échoue jamais sur un interblocage avec la lecture des comptes du fournisseur, et que le
journal technique dise ce que l'admission d'un compte a fait, **afin que** l'écran ne reçoive pas
deux réponses contradictoires pour un même compte, ni une erreur interne sans cause (#2226, #2227,
#2243, #2244).

**Critères d'acceptation.**

- écart : `WF-ADM-0140-A` — « Un compte importé n’a pas d’écran de mot de passe et se connecte avec ses identifiants d’annuaire. » : sa forme pour un compte local que le fournisseur a lié depuis à une
  identité fédérée : `resendInvitation` répond 409 `STATE_FORBIDS_OPERATION`, `missing_condition` à
  `is_local_account`, comme `createPasswordSetupLink`, sans rien inscrire ni journaliser
  `account.invitation_not_sent` en erreur ; éprouvé par un faux administrateur qui rend `not_local`,
  et sous `make test-keycloak` par l'invitation d'un compte lié à une identité fédérée ; la
  connexion est constatée par EP-03 (US-0350), inchangée.
- écart : `WF-ADM-0140-A` — « Un mot de passe de onze caractères est refusé, de même que l’adresse du compte. » : configuration du fournisseur, constatée par EP-03 (US-0350), inchangée.
- écart : `WF-ADM-0140-A` — « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes. » : idem.
- écart : `WF-ADM-0140-A` — « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé. » : idem.
- écart : `WF-ADM-0140-A` — « Un compte créé par un administrateur ne peut pas se connecter avant que son porteur n’ait fixé son mot de passe par le lien reçu ou remis. » : idem.
- écart : `WF-ADM-0140-A` — « Aucun écran de Waterfall ne demande, n’affiche ni ne permet de saisir un mot de passe ; le lien de fixation est le seul élément d’authentification qu’il présente. » : constaté par EP-03 et EP-18 (US-1070), inchangé.
- `WF-ADM-0120-A` — « La désactivation du dernier compte administrateur est refusée, de même que le retrait de son rôle. » : constaté par EP-03
  (US-0380), inchangé ; les trois tests qui éprouvent les deux phrases suivantes
  (`test_access_roles.py`, `test_access_roles_guard.py`) citent désormais l'exigence.
- `WF-ADM-0120-A` — « Elle est acceptée dès qu’un second compte actif porte la permission. » : idem.
- `WF-ADM-0120-A` — « La modification d’un rôle qui retirerait l’une de ces permissions au dernier compte qui les porte est refusée. » : idem, sous concurrence comprise.
- propre à l'US : `updateUser`, `anonymizeUser`, `createPasswordSetupLink`, `resendInvitation` et
  `createUser` prennent le verrou de la règle du dernier administrateur avant toute ligne de compte,
  dans l'ordre de la lecture des comptes du fournisseur (`identity_sync`) ; à deux connexions, une
  lecture qui tient la ligne d'un administrateur Y, puis un `updateUser` d'un compte X par Y, puis la
  lecture qui verrouille X : l'une attend l'autre, sans interblocage.
- propre à l'US : l'admission d'un compte à sa première requête journalise `account.created` pour
  un compte créé, `account.attached` pour un compte rattaché par son adresse, rien pour un compte
  trouvé existant ; le test du rattachement l'affirme par le nom de l'enregistrement.

**Notes de réalisation.** Les propositions de #2226, #2243 et #2244 font foi ; pour #2227, l'auteur a
retenu le verrou pris par les routes sœurs, avec un test à deux connexions (décision du 2026-11-11).

**Hors périmètre.** Les comptes et les rôles qui naissent à `lock_version` 0 (#2779) ; la lecture des
comptes elle-même, inchangée.

---

## US-1800 — Sauvegardes : la liste après la restauration d'une autre installation, et aucune archive orpheline

- **statut** : fini
- **exigences** : `WF-ADM-0160-A`
- **opérations** : `startRestore`, `listBackups`, `startBackup`
- **issue** : #2862

**En tant qu'**exploitant, **je veux** qu'une plateforme reconstruite à partir de l'archive d'une
installation perdue ne liste que ses propres sauvegardes, et que le compartiment ne garde aucune
archive qu'aucune sauvegarde ne nomme, **afin de** ne pas proposer de télécharger ni de restaurer une
sauvegarde absente, et que la rotation voie tout ce qui est gardé (#2230, #2242).

**Critères d'acceptation.**

- `WF-ADM-0160-A` — « Après restauration d’une sauvegarde, la plateforme présente exactement les projets, révisions et comptes qu’elle contenait à la date de la sauvegarde, et rien de postérieur, hors le journal d’audit, la liste des sauvegardes et leur planification, qui gardent leurs inscriptions, leurs sauvegardes et leurs réglages ; le journal nomme la restauration. » : la liste
  des sauvegardes est celle de l'installation gardée : restaurée depuis une base dont la table
  `backup` porte une ligne inconnue de l'installation, elle ne la liste plus ; le reste de la phrase
  est constaté par EP-03 (US-0440) et EP-04.
- écart : `WF-ADM-0160-A` — « Une tâche de fond en file ou en cours dans la sauvegarde est en échec après la restauration. » : constaté par EP-03 (US-0440), inchangé.
- écart : `WF-ADM-0160-A` — « La confirmation nomme la date de la sauvegarde. » : idem.
- écart : `WF-ADM-0160-A` — « Aucune restauration partielle n’est proposée. » : idem.
- écart : `WF-ADM-0160-A` — « Une inscription faite après la sauvegarde est encore présente après la restauration, et la dernière inscription est la restauration elle-même. » : constaté par EP-04, inchangé ; #2229 la reprend en EP-13.
- propre à l'US : une sauvegarde dont l'archive est écrite dans le compartiment, puis dont le relu,
  la vérification ou l'enregistrement échoue, ne laisse aucun objet sous sa clé (WF-DAT-0120 : « Aucun
  autre fichier n'y est conservé ») ; la tâche finit en échec comme aujourd'hui.

**Notes de réalisation.** Les propositions de #2230 et de #2242 font foi.

**Hors périmètre.** Les filtres de `listBackups`, la rétention et les commandes `retain` et `release`
(#2231, #2241, EP-13).

---

## US-1810 — Le compteur d'écriture borné par le contrat

- **statut** : fini
- **exigences** : aucune — correction du contrat et du service
- **opérations** : toute écriture qui porte un `lock_version`, dans son corps ou en paramètre de
  requête (`deleteAccessRole`, `deleteSubproject`, `abandonRevision`, `deleteNode` ; `deleteRisk`,
  que le service ne sert pas encore, EP-08)
- **issue** : #2863

**En tant que** développeur, **je veux** que le contrat borne le compteur d'écriture à ce que la base
tient, **afin qu'**un `lock_version` hors de cette borne soit refusé par la validation, et non par une
erreur interne de PostgreSQL (#2232).

**Critères d'acceptation.**

- propre à l'US : `LockVersion` porte `maximum: 2147483647` (`docs/api/components/common.yaml`), et
  `docs/api/DECISIONS.md` a son entrée, qui cite #2232 et la décision de l'auteur du 2026-11-11 ;
- propre à l'US : `PATCH /access-roles/{id}` avec `{"label":"x","permissions":[],"lock_version":2147483648}`
  répond 422 `VALIDATION_FAILED`, `fields` sur `/lock_version` avec `VALUE_OUT_OF_RANGE` et
  `params.maximum` à `2147483647` ; un paramètre de requête `lock_version` au-delà de la borne
  répond de même, au pointeur `/query/lock_version` ;
- propre à l'US : les paramètres de requête `lock_version` du service portent la borne du contrat,
  ce que `test_contract_declarations.py` vérifie ; le client du front et les modèles du service sont
  régénérés du contrat.

**Notes de réalisation.** L'auteur a retenu la borne au contrat (décision du 2026-11-11), plutôt que
la comparaison du compteur en Python que proposait #2232 : c'est une modification du contrat figé
(« La règle d'après le gel », `docs/api/DECISIONS.md`).

**Hors périmètre.** Les compteurs qui naissent à 0 (#2779).

---

## US-1820 — Le moteur de planning : un décalage et une durée écoulés reculent juste, et trois tests citent leur exigence

- **statut** : à faire
- **exigences** : `WF-PLA-0100-A`, `WF-PLA-0160-A`, `WF-REV-0020-A`
- **opérations** : aucune en propre — le moteur, et des tests d'API qui ne changent que leur marqueur
- **issue** : #2866

**En tant que** chef de projet, **je veux** qu'un décalage ou une durée écoulés qui atteignent une fin
de semaine donnent la même marge en arrière qu'en avant, **afin qu'**aucune tâche ne se dise critique,
ou en marge négative, sans conflit qui l'explique (#2816, #2832) ; **en tant que** développeur, que
trois tests d'API citent l'exigence dont ils éprouvent le Vérif (#2845).

**Critères d'acceptation.**

- `WF-PLA-0100-A` — « Sur un planning à deux branches parallèles de durées différentes, la branche la plus longue est critique et l'autre porte une marge égale à leur écart. » : sa forme
  pour un décalage écoulé qui atteint un jour sans heure de travail : sur un calendrier de 8 h du
  lundi au vendredi, planning au lundi 2 mars 2026, A (4 j) → B (1 j, le vendredi 6), B fin à fin
  C avec +2 ej, C (1 j) : A, B et C portent une marge nulle et sont critiques, sans
  `link_conflicts` ; la variante qui finit un jour ouvré de même ; la passe avant est inchangée.
- `WF-PLA-0100-A` — « Allonger une tâche de la branche courte au-delà de sa marge la rend critique à son tour. » : sa forme pour une durée écoulée : pour une
  durée de 1, 2, 3 et 5 ej, une avance de 1 à 10 j, et un calendrier à jour férié, sur la chaîne A,
  B, C de `test_the_latest_start_of_an_elapsed_duration_goes_back_from_the_day_it_may_reach`,
  décaler une tâche de sa marge laisse la fin du projet inchangée, et décaler A d'un jour de plus la
  décale ; un écart que ce test révèle est corrigé dans `_Engine.latest_start`.
- écart : `WF-PLA-0100-A` — « Une tâche en mode manuel n'affiche aucune marge et n'apparaît jamais sur le chemin critique, alors que ses successeurs automatiques voient leurs marges calculées à partir de ses dates. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0100-A` — « Un prédécesseur automatique qui ne peut pas finir avant le début d'une tâche manuelle porte une marge négative, apparaît sur le chemin critique et est signalé. » : idem.
- écart : `WF-PLA-0100-A` — « Une récapitulative dont une subordonnée est critique est critique et affiche la marge de cette subordonnée, nulle ou négative. » : idem.
- écart : `WF-PLA-0100-A` — « Un prédécesseur lié début à début à une tâche manuelle, et qui ne peut pas commencer avant elle, porte une marge négative et est signalé. » : idem.
- écart : `WF-PLA-0160-A` — « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize heures, « 1 sem » quarante heures et « 1 m » cent soixante heures. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0160-A` — « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer d'unité. » : idem.
- `WF-PLA-0160-A` — « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit à la dernière heure travaillée d'un vendredi s'achève le dimanche ; le successeur, sur un calendrier du lundi au vendredi, commence le lundi à la première heure travaillée, de même qu'avec un décalage de 2 eh. » : la passe avant, inchangée,
  reste éprouvée ; la passe arrière du même décalage, sur une liaison fin à fin, donne au
  prédécesseur la marge qu'elle lui donne en fin à début, nulle.
- écart : `WF-PLA-0160-A` — « Un décalage de 2 j sur la même liaison le fait commencer le mercredi. » : constaté par EP-06 (US-1390), inchangé.
- écart : `WF-PLA-0160-A` — « Un fichier MS Project dont les constantes diffèrent de celles de l'installation est importé avec les mêmes durées en heures, et le compte rendu signale la différence. » : idem.
- écart : `WF-PLA-0160-A` — « « 1 m » est lu comme un mois et « 1 min » comme une minute, dans chacune des langues de l'interface. » : idem.
- écart : `WF-PLA-0160-A` — « En anglais, « 1 j » et « 1 d » valent chacun un jour ; « 3 », saisi sans suffixe, vaut trois jours. » : idem.
- écart : `WF-PLA-0160-A` — « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans une révision en cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision marquée, elle vaut toujours seize heures. » : idem.
- écart : `WF-REV-0020-A` — « Le marquage est refusé tant que le nom de version n'est pas renseigné. » : constaté par EP-04, inchangé ; EP-07 clôt.
- `WF-REV-0020-A` — « Toute tentative de modification d'une révision marquée est refusée, quel que soit le point d'entrée. » : les tests d'API qui l'éprouvent par l'état
  et par un collage (`test_nodes_state.py`, `test_paste.py`) la citent au lieu de `WF-DAT-0020-A`,
  dont le Vérif est une écriture en base ; celui de la désignation (`test_reference_designation.py`)
  garde `WF-DAT-0020-A`, son Vérif disant la désignation (« Conception »).
- écart : `WF-REV-0020-A` — « Le marquage d'une révision sous un nom de version déjà employé dans le projet est refusé. » : constaté par EP-04, inchangé.

**Notes de réalisation.** Les propositions de #2816 et #2832 font foi ; #2845 se tranche test par test
(décision de l'auteur du 2026-11-11). Le test de #2816 va dans `test_scheduling_examples.py`, à côté
de celui de #2648.

**Hors périmètre.** Toute autre pièce du moteur ; le jour courant en UTC (#2527, EP-13).

---

## US-1830 — Les refus du référentiel : la liste de l'arbre, la correspondance non amorcée, les années de la grille des taux et un tri

- **statut** : à faire
- **exigences** : `WF-REF-0070-A`, `WF-REF-0150-A`, `WF-IHM-0060-A`, `WF-EXP-0040-A`
- **opérations** : `listOrgNodes`, `getActualCostMapping`, `setActualCostMapping`, `getHourlyRateGrid`,
  `listCostCategories`
- **issue** : #2876

**En tant que** manager ou administrateur, **je veux** que les lectures et les écritures du
référentiel répondent ce que le contrat déclare — la liste de l'arbre pendant qu'un autre crée un
nœud, un filtre mal formé, une correspondance que l'amorçage n'a pas écrite, les années de la grille
des taux, l'ordre d'un tri —, **afin de** ne jamais recevoir une erreur interne là où le contrat
promet une réponse ou un refus nommé (#2228, #2233, #2235, #2237, #2239).

**Critères d'acceptation.**

- `WF-REF-0070-A` — « Un arbre de six niveaux peut être créé. » : sa forme pour la lecture de
  l'arbre : `GET /reference/org-nodes` répond 200, avec ou sans le nouveau nœud, quand un nœud est
  créé et validé pendant que la lecture est tenue entre ses deux étapes ; `?code=%00` répond 422
  `VALIDATION_FAILED`, `fields` sur `/query/code` ; la création d'un arbre de six niveaux est
  constatée par EP-05 (US-0840), inchangée.
- écart : `WF-REF-0070-A` — « La création d'un nœud dont le code existe déjà est refusée. » : constaté
  par EP-05 (US-0840), inchangé.
- écart : `WF-REF-0070-A` — « Le déplacement d'un nœud sous un autre emporte ses descendants et ses
  rôles ; le plan de charge agrégé filtré sur le nœud d'arrivée inclut désormais ces rôles, et les
  valeurs par rôle sont inchangées. » : constaté par EP-05 (US-0840) pour l'arbre ; EP-11 clôt.
- écart : `WF-REF-0070-A` — « Le déplacement sous un nœud désactivé est refusé. » : constaté par
  EP-05 (US-0840), inchangé.
- `WF-REF-0150-A` — « Un objet désactivé n'apparaît pas dans la liste par défaut, apparaît lorsque
  l'affichage des objets désactivés est demandé, et peut y être réactivé. » : sa forme pour les
  colonnes de la grille des taux : une année que seule porte une catégorie désactivée — 2030 saisi
  sur la catégorie OLD, puis OLD désactivée — est dans `years` avec `include_inactive=true`, et y
  reste avec `include_inactive=true&is_active=true`, les années ne dépendant jamais d'`is_active`
  vrai (`HourlyRateGrid.years`) ; le reste est constaté par EP-05 (US-0880), inchangé.
- `WF-IHM-0060-A` — « Chaque colonne d'une table plate se trie dans les deux sens. » : sa forme pour
  le départage du tri de `listCostCategories` par nature : deux natures « Main-d'œuvre », de codes A
  et B, portent C-2 (nature A) et C-1 (nature B) ; triée par `cost_type` en ordre croissant, la liste
  rend C-1 puis C-2 — à libellé de nature égal, l'ordre de la liste sans tri, puis l'identifiant ; le
  tri de chaque colonne est constaté par EP-05 (US-0820), inchangé.
- écart : `WF-IHM-0060-A` — « Dans la grille de planning, aucun en-tête de colonne ne propose de
  tri ; dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans
  déplacer les tâches. » : EP-06 et EP-07, sans objet pour le référentiel.
- écart : `WF-IHM-0060-A` — « Après défilement de mille lignes, en-têtes et totaux sont toujours
  visibles, de même que la colonne de libellé après défilement horizontal. » : constaté par EP-02
  (US-0110), inchangé ; EP-07 clôt.
- écart : `WF-IHM-0060-A` — « Les colonnes masquées et les largeurs choisies sont retrouvées à la
  réouverture, et un autre utilisateur ouvrant la même grille voit ses propres réglages. » :
  constaté par EP-03 (US-0400), inchangé.
- écart : `WF-IHM-0060-A` — « Le nombre de lignes par page choisi pour une table est retrouvé à sa
  réouverture, sans changer celui des autres tables ; une grille arborescente n'offre pas ce
  choix. » : constaté par EP-15 (US-0570), inchangé.
- `WF-EXP-0040-A` — « Pendant l'arrêt du stockage objet, une demande d'import est refusée en nommant
  le composant, et la consultation comme la saisie continuent. » : sa forme pour une installation
  dont l'amorçage n'a pas écrit la correspondance des coûts réels : `getActualCostMapping` et
  `setActualCostMapping` répondent 503 `COMPONENT_UNAVAILABLE`, `params.component` à `database`,
  comme `getReferenceSettings` sans ses paramètres, et non 500 ; l'import refusé lui-même est
  d'EP-09, et la plateforme d'EP-13.
- écart : `WF-EXP-0040-A` — « Pendant l'arrêt du worker, un marquage demandé aboutit après le
  rétablissement, sans nouvelle demande. » : le service, EP-13 clôt.
- écart : `WF-EXP-0040-A` — « Aucune donnée partiellement écrite ne subsiste après le rétablissement
  d'un composant tombé en cours d'écriture. » : idem.
- propre à l'US : chaque réponse des tests est validée contre le contrat (`ContractClient`) ; le
  contrat ne change pas.

**Notes de réalisation.** Les propositions de #2228, #2233, #2235, #2237 et #2239 font foi
(décisions de l'auteur du 2026-11-11). Les numéros de ligne de la décision, relevés sur
`epic/EP-09`, sont ceux de `main` à quelques lignes près : `org_nodes.py` l. 204-207,
`actual_cost_mapping.py` l. 131 et 284, `cost_categories.py` l. 216. Le refus de #2235 change ce
que reçoivent les appelants de `read_actual_cost_mapping` sur `epic/EP-09`, sans changer sa
signature.

**Hors périmètre.** Les nœuds nés à `lock_version` 0 (#2240, la v1) ; les décimaux (US-1840) ; le
critère d'US-0860 (#2245, corrigé par la pull request du cadrage).

---

## US-1840 — Les décimaux à l'entrée : une précision pour les seuils et les bornes, des chiffres de 0 à 9

- **statut** : à faire
- **exigences** : `WF-DAT-0100-A`, `WF-REF-0160-A`, `WF-REF-0170-A`
- **opérations** : `updateReferenceSettings`, `setHourlyRate`, et toute écriture dont le corps porte un
  `Money` ou un `Decimal` ; `listNodes` et `listResourceRoles` par leurs bornes
- **issue** : #2877

**En tant qu'**administrateur, **je veux** qu'un seuil, une borne ou un montant que je saisis soit lu
comme le contrat l'écrit — des chiffres de 0 à 9, une précision que la base tient —, **afin qu'**une
valeur hors de ces règles soit refusée à son champ, plutôt qu'enregistrée autrement que je l'ai
écrite ou rejetée par une erreur interne (#2234, #2238).

**Critères d'acceptation.**

- écart : `WF-DAT-0100-A` — « La somme des montants budgétés d'une révision est identique quel que
  soit l'ordre de sommation. » : constaté par EP-03 et EP-06, inchangé ; EP-07 clôt.
- écart : `WF-DAT-0100-A` — « Une tâche planifiée au 30 juin s'affiche au 30 juin sur tout poste
  client, quel que soit son fuseau. » : idem.
- `WF-DAT-0100-A` — « Un montant de 0,10 additionné dix fois donne exactement 1,00. » : sa forme
  pour l'entrée : un `Money` ou un `Decimal` reçu est lu tel que le contrat l'écrit, en chiffres de
  0 à 9 : `setHourlyRate` avec `{"amount":"١٢.٥٠"}` répond 422 `VALIDATION_FAILED` sur `/amount`
  et n'enregistre rien ; `updateReferenceSettings` avec une borne `"٠.٢٥"` répond 422 sur
  `/risk_matrix/probability_bounds/0` ; une borne de `listNodes` ou de `listResourceRoles` en
  chiffres non ASCII répond 422 `NUMBER_INVALID` à son paramètre ; la somme exacte est constatée par
  EP-03 et EP-06, inchangée.
- écart : `WF-DAT-0100-A` — « Deux tâches de quatre heures liées fin à début, sur un calendrier de
  huit heures, commencent et finissent le même jour. » : constaté par EP-06, inchangé ; EP-07 clôt.
- `WF-REF-0160-A` — « Les six bornes sont saisissables et ordonnées. » : sa forme pour leur
  précision : une borne de plus de dix décimales, ou de plus de dix chiffres avant le point — `"0."`
  suivi de vingt mille `9` —, est refusée par 422 `VALIDATION_FAILED` à `/risk_matrix/<axe>/<rang>`,
  et non par 500 ; une borne de dix décimales est acceptée ; la saisie et l'ordre sont constatés par
  EP-05 (US-0810), inchangés.
- écart : `WF-REF-0160-A` — « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité 60
  est au troisième niveau sur un projet de budget 1 000 (6 %) et au deuxième sur un projet de budget
  2 000 (3 %). » : EP-08 clôt.
- écart : `WF-REF-0160-A` — « Sur un projet en chiffrage, un risque est classé d'après le total hors
  provisions de son devis courant ; la désignation de la révision de référence ne change pas son
  niveau si ce total égale le budget de référence. » : idem.
- écart : `WF-REF-0160-A` — « Avec des bornes de gravité à 1 %, 5 % et 10 %, un risque de gravité 50
  sur un projet de budget 1 000 est au troisième niveau. » : idem.
- `WF-REF-0170-A` — « Les quatre seuils sont saisissables, et le seuil d'alerte de chaque indice est
  inférieur à son seuil de vigilance. » : sa forme pour leur précision : `PATCH /reference/settings`
  avec `cost_watch` à `"0."` suivi de vingt mille `9`, les autres valeurs valides, répond 422
  `VALIDATION_FAILED` à `/index_thresholds/cost_watch`, et non 500, chacun des quatre seuils de
  même ; un seuil de dix décimales est accepté ; la saisie et l'ordre sont constatés par EP-05
  (US-0810), inchangés.
- écart : `WF-REF-0170-A` — « Un indice traverse les trois zones lorsque sa valeur décroît de 1 à
  0,5, avec des seuils fixés à 0,9 et 0,8. » : EP-10 clôt.
- écart : `WF-REF-0170-A` — « Avec des seuils à 0,9 et 0,8, un indice de 0,9 est nominal et un
  indice de 0,8 en vigilance. » : idem.
- propre à l'US : la base des modèles reconnaît tout type de `api/contract/models.py` dont la racine
  porte le motif de `Decimal` ou de `Money`, et aucun autre, ce qu'un test confronte aux modèles
  engendrés ; `api/contract/models.py`, le contrat et `docs/api/DECISIONS.md` ne changent pas
  (`make server-models-up-to-date` et `make inventory` passent).

**Notes de réalisation.** Corrigés dans le code, pas au contrat (décision de l'auteur du
2026-11-11) ; la conception dit où (« Back, les décimaux à l'entrée ») et pourquoi la base des
modèles plutôt que les routes. La précision suit `RATIO_DECIMALS` des projets. Les numéros de ligne
de la décision, relevés sur `epic/EP-09`, sont sur `main` : `api/nodes.py` l. 88-91,
`api/resource_roles.py` l. 82, `api/reference_settings_write.py` l. 86-87.

**Hors périmètre.** Les autres décimaux qui débordent PostgreSQL, et les mois, les trimestres et la
durée collée lus par `\d` (#2875, à trancher) ; le compteur d'écriture (US-1810).

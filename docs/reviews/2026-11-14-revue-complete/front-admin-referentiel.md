# Revue — écrans d'administration, d'audit, de système et de référentiel du front

Périmètre : `frontend/src/components/{admin,audit,system,reference}`, `frontend/src/app/{admin,reference,system}`.
Commit relu : `29785cc`. Lecture seule ; aucun test ni outil lancé.

## Synthèse

Le code de ce périmètre est très travaillé et très défensif : chaque écriture part du compteur le
plus récent (`lock_version`), les réponses tardives sont rattachées à la lecture d'où elles sont
parties, les refus par champ sont dits au champ, les commandes suivent `available_commands`, rien
n'est calculé ni trié côté front, aucune exemption de lint, aucun `any`, aucun appel hors du client
engendré. Je n'ai trouvé **aucun constat bloquant**.

Trois constats majeurs, tous vérifiés par lecture de bout en bout : le suivi d'une restauration
s'arrête définitivement dès qu'une interrogation de la sonde est rejetée (écran de maintenance figé) ;
la liste du rattachement d'un compte est inatteignable au clavier dans la grille ; trois écrans du
référentiel se présentent par URL directe sans la permission de consulter que le contrat dit
« ouvrir leur présentation ».

Les mineurs sont des écarts localisés : une action groupée offerte que le serveur refuse toujours
pour une combinaison de permissions, des citations d'exigences hors Vérif dans des tests, des
boutons de dialogue sans `aria-haspopup`, des séparateurs écrits en dur, l'adresse d'un compte local
non corrigeable, des gestes à cascade sans confirmation.

Plusieurs angles de la mission sont **sans objet** dans le contrat livré : il n'y a ni jours non
ouvrés ni exceptions de calendrier (un calendrier = sept valeurs d'heures), ni taux « à dates
d'effet » (un taux par catégorie et par année), ni déplacement d'un nœud autrement que par le champ
« parent » de son formulaire, ni export de sélection sur ces tables.

## Constats bloquants

Aucun.

## Constats majeurs

### FAR-01 — Le suivi d'une restauration s'arrête pour de bon au premier rejet d'une action serveur

- **Issue** : #4472 (EP-39), ouverte le 2026-11-21.
- **Où** : `frontend/src/components/system/maintenance.tsx:108-122` (`useRestorationPhase`, `step`) ;
  aussi `:62-66` (`taskPhase`) ; effet de bord `frontend/src/components/system/system-failure.tsx:122`.
- **Quoi** : `step()` attend `readLiveness()` puis `readBackgroundTask()` sans `try/catch` ni
  `.catch(rejected)`, et n'est relancé (`setTimeout`, ligne 119) qu'après un tour réussi : un rejet
  de l'action serveur laisse une promesse rejetée non traitée (`void step()`) et **plus aucune
  interrogation ne part**.
- **Scénario** : l'administrateur confirme une restauration ; l'écran de maintenance interroge
  toutes les 2 s (`RESTORATION_POLL`). Pendant les minutes que dure la restauration, une requête du
  navigateur vers le serveur Next échoue (coupure Wi-Fi, proxy, redéploiement du front : `fetch`
  rejeté ou « Failed to find Server Action »). `readLiveness` côté serveur ne rejette jamais
  (`reach` → `"unreachable"`), mais l'appel de l'action depuis le navigateur, si. L'écran reste sur
  « La plateforme est en maintenance… » avec son indicateur qui tourne, indéfiniment : ni « Restauration
  terminée » ni lien de reconnexion. Même défaut sur l'écran de panne (`SystemFailure`), qui tient
  en plus le lien de connexion caché tant que la phase est `asking` (`system-failure.tsx:122`).
  Partout ailleurs dans le périmètre, une action serveur est lue par `.catch(rejected)` ; ici non.
  Second ordre : `taskPhase` rend `QUEUED` pour toute lecture de tâche qui n'est pas `done` (404,
  403, API hors d'atteinte durable) : l'écran dit « en attente » sans fin.
- **Vérifié** : aucun gestionnaire global (`unhandledrejection` absent de `src/`) ; aucun test de
  `system.dom.test.tsx` ni de `restore-dialog.dom.test.tsx` ne rejette la sonde.
- **Proposition** : dans `step`, attraper le rejet et le traiter comme `unreachable` (replanifier,
  éventuellement avec un plafond et une phrase « plateforme injoignable, nouvel essai… ») ; borner
  le nombre de lectures de tâche refusées avant de dire `signed_out`/échec. Test : sonde rejetée une
  fois puis `maintenance` puis `ok` → l'écran finit sur « Restauration terminée ».
- **Confiance** : confirmé (chemin lu de bout en bout ; non rejoué).

### FAR-02 — La liste du rattachement d'un compte est inatteignable au clavier dans la grille

- **Issue** : #4488 (EP-29), ouverte le 2026-11-21, avec FAR-06.
- **Où** : `frontend/src/components/admin/user-cells.tsx:336-344` (`AttachmentCell`, `NativeSelect`
  avec `tabIndex={-1}` et `data-cell-command`) ; `frontend/src/components/grid/grid-keyboard.ts:270-280`
  (`followLink`).
- **Quoi** : la grille est un seul arrêt de tabulation et Entrée sur une cellule « presse » sa
  commande par `event.target.querySelector('a[href], button[data-cell-command]')`. Le rattachement
  est un `<select>` : il n'est ni dans l'ordre de tabulation, ni trouvé par ce sélecteur (qui ne
  prend que des `button`), et la colonne n'a pas d'`entry`. Rien au clavier ne l'ouvre ni ne lui
  donne le focus. L'en-tête du fichier affirme pourtant « Enter on its cell presses it ».
- **Scénario** : un administrateur au clavier (ou avec un lecteur d'écran) va sur la cellule
  « Rattachement » d'un compte, presse Entrée, F2 ou Espace : rien. L'interrupteur d'état et la liste
  des rôles de la même ligne, eux, répondent (ce sont des `button`). Seul contournement : sélectionner
  la ligne et passer par « Rattacher à » de la barre d'actions.
- **Vérifié** : `user-attachment.dom.test.tsx` ne choisit que par `selectOption` ; le parcours
  `e2e/admin.spec.ts:588-600` aussi ; aucun test au clavier de cette cellule.
- **Règle** : `docs/dev/typescript.md`, « Accessibilité » — « Tout se fait au clavier : un lien ou un
  bouton ne sort de l'ordre du clavier (`tabIndex={-1}`) que dans un widget qui déplace lui-même le
  focus ».
- **Proposition** : élargir `followLink` à `[data-cell-command]` et, pour un `select`, lui donner le
  focus et l'ouvrir (`showPicker()`), le choix n'étant écrit qu'à la validation ; ou remplacer la
  liste native par le même `Popover` que les rôles. Test : Entrée sur la cellule puis choix d'un
  nœud au clavier écrit `updateUser` une fois.
- **Confiance** : confirmé par lecture (non rejoué dans un navigateur).

### FAR-03 — Trois écrans du référentiel se présentent par URL directe sans la permission de consulter

- **Issue** : #4489 (EP-29), ouverte le 2026-11-21.
- **Où** : `frontend/src/app/reference/risks/page.tsx:41-56`,
  `frontend/src/app/reference/indicators/page.tsx:42` et suivantes,
  `frontend/src/app/reference/resources/page.tsx:335` et suivantes.
- **Quoi** : ces pages ne lisent de la session que la permission d'écrire (`platformOffer`) ; aucune
  ne vérifie `risk_settings.read`, `indicator_settings.read` ou `resource_settings.read`. Or leurs
  lectures (`getReferenceSettings`, `listOrgNodes`, `listResourceRoles`, `listCalendars`,
  `getDurationUnits`) sont ouvertes à toute session (`Requires()` sans permission, décision C-01),
  si bien que l'API ne refuse rien : la navigation cache le lien, l'adresse tapée montre l'écran.
- **Référence** : `docs/api/DECISIONS.md:10465-10467` et `docs/api/components/schemas/access.yaml:535-536`
  — « `resource_settings.read`, `risk_settings.read` and `indicator_settings.read` open the
  presentation of the screens of their function » ; WF-ADM-0110 — « L'interface présente le même
  écran pour un objet inexistant et pour un objet dont la consultation n'est pas permise ». Le
  journal d'audit, lui, le fait (`app/admin/audit-log/page.tsx`, `consultation()` → `notFound()`).
- **Scénario** : un compte dont le rôle ne porte aucune permission de référentiel ouvre
  `/reference/risks`, `/reference/indicators` ou `/reference/resources` : il lit l'écran entier (en
  lecture seule). Pas de fuite de donnée au sens du contrat (ces lectures sont publiques par
  décision), mais trois permissions du catalogue (WF-ADM-0100) ne gardent alors rien d'autre qu'un
  lien de menu, contre ce que le contrat en dit.
- **Vérifié** : aucun `layout.tsx` ni garde commun sous `app/reference` ; `settings-pages.test.tsx`
  et `resources/page.test.tsx` n'éprouvent aucune session sans la permission de consulter ; l'écran
  des coûts, lui, est gardé par l'API (grille des taux sous `cost_settings.read`).
- **Proposition** : la même garde que le journal (`notFound()` sans `<fonction>.read`) dans les
  trois pages, ou une garde commune tirée de `navigation/functions.json` ; un test par page, session
  sans la permission → « introuvable ».
- **Confiance** : confirmé.

## Constats mineurs

### FAR-04 — « Ajouter un rôle » en action groupée, offert à une session que le serveur refusera toujours

- **Issue** : #4492 (EP-29), ouverte le 2026-11-21, avec FAR-08.
- **Où** : `frontend/src/components/admin/user-bulk.tsx:49-64` ; `frontend/src/app/admin/users/page.tsx:141`.
- **Quoi** : la barre offre « Ajouter un rôle » dès que la session modifie les comptes
  (`users.write`) et lit les rôles (`roles.length > 0`). `setUserAccessRoles` exige en plus
  `access_roles.write` (`backend/src/waterfall/api/users.py:134`). La cellule des rôles d'une ligne
  suit bien `available_commands` (`set_access_roles` absent) ; l'action groupée, non.
- **Scénario** : un gestionnaire de comptes porte `users.read`, `users.write`, `access_roles.read`.
  Il sélectionne les 50 comptes de la page, « Ajouter un rôle », « Appliquer » : 50 appels, 50 refus
  empilés au-dessus de la table. Défaut n° 6 de `typescript.md` (« Commande offerte que le back
  refusera »).
- **Proposition** : n'offrir le choix que si une ligne sélectionnée au moins liste
  `set_access_roles` (ou si la session porte `access_roles.write`). Test dans
  `user-bulk.dom.test.tsx` : session sans `access_roles.write` → pas de liste « Ajouter un rôle ».
- **Confiance** : confirmé (chemin front et garde serveur lus).

### FAR-05 — Des tests citent une exigence dont ils n'éprouvent pas le Vérif

- **Issue** : #4451 (EP-36), ouverte le 2026-11-21, avec BAC-10, BRC-10, FCO-13.
- **Où** : `frontend/src/components/admin/user-bulk.dom.test.tsx:305, 324, 355, 367` (`[WF-ADM-0120-A]`
  sur la réentrance du groupe, le résumé, le décompte « déjà dans l'état demandé ») ; `:388`
  (`[WF-ADM-0180-A]` sur le choix gardé affiché) ; `:407` (`[WF-IHM-0110-A]` — annulation et
  rétablissement — sur les classes CSS d'un bouton `aria-disabled`).
- **Quoi** : le guide dit « Un test cite l'exigence dont il éprouve le Vérif, pas celle dont il
  parle » (`docs/dev/README-fr.md`, « Un test qui cite son exigence »). Ces citations gonflent le
  relevé de `make requirements` sans prouver le Vérif (dernier administrateur ; annulation).
- **Proposition** : retirer la citation de ces six titres (ils gardent leur `#issue`). Aucun test à
  ajouter.
- **Confiance** : confirmé (Vérif de WF-ADM-0120-A et WF-IHM-0110-A relus dans la spec).

### FAR-06 — Des boutons qui ouvrent un dialogue ne le disent pas

- **Issue** : #4488 (EP-29), ouverte le 2026-11-21, avec FAR-02.
- **Où** : `frontend/src/components/admin/backup-commands.tsx:658-669` (« Restaurer cette
  sauvegarde » du dépôt, ouvre `RestoreDialog`) ; `frontend/src/components/admin/user-cells.tsx:402-422`
  (`SetupLinkCommand`, ouvre `SetupLinkDialog` à la réponse) ; `frontend/src/components/admin/user-dialogs.tsx:278-295`
  (« Remettre le lien », même dialogue).
- **Quoi** : pas d'`aria-haspopup="dialog"`, que `typescript.md` (« Accessibilité ») demande « même
  quand le dialogue s'ouvre par un état » et que le harnais d'accessibilité lit pour ouvrir ce qu'il
  audite. Les autres commandes du périmètre (restauration d'une ligne, anonymisation, suppression
  d'un rôle, créations, planifications) le portent.
- **Proposition** : poser l'attribut sur les trois ; le dialogue du dépôt entre alors dans
  `e2e/accessibility.spec.ts`.
- **Confiance** : confirmé.

### FAR-07 — Séparateurs et listes composés en dur

- **Issue** : #4462 (EP-37), ouverte le 2026-11-21, avec FCO-12.
- **Où** : `frontend/src/components/admin/user-cells.tsx:226, 241` (`labels.join(", ")` dans un nom
  accessible) ; `frontend/src/components/reference/actual-cost-mapping.tsx:183` (`.join(", ")` des
  colonnes manquantes) et `:265` (`" " + …`, deux phrases collées par une espace) ;
  `frontend/src/components/audit/audit-cells.tsx:78` (`Intl.ListFormat` construit hors de
  `src/i18n/format.ts`, mais correct).
- **Quoi** : `typescript.md` laisse à la revue « une chaîne bâtie par une fonction ou une méthode
  (`.join`, `.concat`) ». La virgule et l'espace sont de la ponctuation de langue ; le journal
  d'audit montre la bonne forme (`Intl.ListFormat`).
- **Proposition** : une fonction `formatList` dans `src/i18n/format.ts`, employée aux quatre
  endroits. Coût faible, risque nul.
- **Confiance** : confirmé.

### FAR-08 — L'adresse d'un compte local ne se corrige sur aucun écran

- **Issue** : #4492 (EP-29), ouverte le 2026-11-21, avec FAR-04.
- **Où** : `frontend/src/components/admin/admin-grids.tsx:274-282` (colonne `email` sans `entry`).
- **Quoi** : le contrat laisse modifier l'adresse d'un compte local (`UserUpdate.email`, servi par
  `backend/src/waterfall/api/users.py:458-464`), et WF-ADM-0050 ne la fige que pour l'annuaire et le
  fournisseur externe. La table n'offre que le nom et le prénom. Comme aucun compte ne se supprime
  (WF-ADM-0060), une adresse mal saisie à la création — l'invitation part à cette adresse — ne se
  rattrape qu'en désactivant, anonymisant et recréant le compte.
- **Nuance** : conforme au critère d'US-0360 (« nom et prénom d'un compte local en champs ») ; c'est
  la conception qui est courte, pas le code. Non trouvé dans `docs/roadmap/`.
- **Proposition** : `entry: naming("email", …)` de forme `text`, borne 254, le 409
  `ALREADY_EXISTS` dit à la cellule ; ou une issue de cadrage.
- **Confiance** : confirmé pour le front ; le comportement exact du service sur un changement
  d'adresse (fournisseur d'identité) n'a pas été relu.

### FAR-09 — Des gestes à cascade ou sans retour partent d'un seul clic

- **Suite** : abandonné le 2026-11-21, par décision de l'auteur — la revue le dit elle-même : aucune
  exigence ne demande ces confirmations, la maquette d'US-1860 est validée sans, et le serveur tient
  WF-ADM-0120 — une opportunité d'ergonomie, pas un écart.
- **Où** : `frontend/src/components/reference/commands.tsx:371-396` (`ActivationButton` d'un nœud) ;
  `frontend/src/components/admin/user-bulk.tsx:80-97` (« Désactiver » groupé) ;
  `frontend/src/components/admin/user-cells.tsx:128-153` (interrupteur de son propre compte).
- **Quoi** : désactiver un nœud désactive ses descendants et leurs rôles (WF-REF-0080) ; la
  réactivation, elle, ne cascade pas (un objet à la fois, parent d'abord). « Tout sélectionner » puis
  « Désactiver » ferme jusqu'à cent comptes, le sien compris si un autre administrateur existe ; sa
  propre désactivation ou le retrait de ses propres rôles ferme la session au rendu suivant. Aucun
  de ces gestes n'est confirmé, alors que la suppression d'un rôle et l'anonymisation le sont.
- **Nuance** : aucune exigence ne demande ces confirmations, et la maquette d'US-1860 est validée
  sans ; le serveur tient WF-ADM-0120. Ce n'est pas un écart, c'est un risque d'usage.
- **Proposition** (coût : un `AlertDialog` déjà existant, deux ou trois tests ; gain : éviter une
  réorganisation à rejouer nœud par nœud) : confirmer la désactivation d'un nœud qui a des
  descendants ou des rôles, en les comptant ; dire dans la barre que la sélection comprend son
  propre compte.
- **Confiance** : confirmé (comportement) ; l'opportunité est à trancher par l'auteur.

### Défauts déjà connus, revus au passage

- `frontend/src/components/reference/commands.tsx:340-396` — « Modifier » et l'activation d'une
  ligne restent offerts pendant qu'une écriture de la ligne est en route (412 à suivre) : **déjà
  connu (#2260, EP-25 / US-2180)**.
- `frontend/src/components/reference/actual-cost-mapping.tsx:652` — `key={mapping.lock_version}`
  remonte le formulaire à la relecture, focus et saisie perdus : **déjà connu (#2266, EP-25)** ; le
  21ᵉ intitulé et son refus non dit : **déjà connu (#2267)**.
- `frontend/src/components/reference/settings-forms.tsx:131-138` — la règle locale des seuils juge
  hors de ]0, 1[ : **déjà connu (#2268, EP-25)**.
- La cascade d'un nœud non éprouvée par un test : **déjà connu (#2270)** ; `useRaise` après
  démontage : **déjà connu (#3163)**.

## Points forts

- Concurrence : une seule source de l'objet répondu par `lock_version` pour les comptes
  (`UserCommands`), les rôles (`RoleAnswers`, table et matrice) et le référentiel (`useAnswered`) ;
  les écritures d'une ligne sont mises en file ; un 412 d'un compte relit le compte (`readUser`).
- Réponses tardives : refus dits sur la seule lecture d'où ils partent (`Reactivations`,
  `generation`), dialogues gardés par compteur d'ouvertures, recherche d'auteur avec anti-rebond et
  garde d'ordre (`author-filter.tsx:101-135`).
- Restauration : confirmation par l'identifiant saisi, dialogue non fermable pendant l'envoi, date
  refusée (`CONFIRMATION_REQUIRED`) relue, phase `signed_out` qui n'affirme rien.
- Fuseaux : périodes en jours locaux tirées en instants par `new Date(année, mois, jour)`, jamais
  `new Date("AAAA-MM-JJ")` ; heures de planification laissées en UTC avec leur équivalent local dit.
- Aucun flottant sur un montant ou un décimal du contrat ; les `Number()` du périmètre ne touchent
  que des entiers (jours de semaine, comptes, niveaux, octets).
- Listes : filtre, tri et pagination par le serveur partout ; chaque filtre ramène à la première
  page (paramètre `page` posé sur chacun, vérifié pour comptes, sauvegardes, journal, coûts, rôles de
  ressources, calendriers) ; liste vide distinguée de liste filtrée.
- Téléchargement d'une sauvegarde : retour borné à l'écran des sauvegardes (pas de redirection
  ouverte), flux relayé sans mise en mémoire.
- Aucun commentaire d'exemption, aucun `any`, aucun `as unknown as` dans le périmètre.

## Couverture

**Lu en entier** — `components/admin` : `user-commands.tsx`, `user-cells.tsx`, `user-dialogs.tsx`,
`user-bulk.tsx`, `user-bulk-write.ts`, `user-address.ts`, `admin-grids.tsx`, `admin-grid.tsx`,
`account-lists.tsx`, `role-commands.tsx`, `role-answers.tsx`, `role-address.ts`,
`permission-matrix.tsx`, `backup-commands.tsx`, `backup-schedule.tsx`, `restore-dialog.tsx`,
`restoration.tsx`, `identity-sync.tsx`, `identity-sync-schedule.tsx`, `platform-lists.tsx`,
`audit-address.ts`, `author-filter.tsx`, `schedule-days.ts`, `backup-address.ts` (hors en-tête).
`components/audit` : `audit-address.ts`, `audit-filters.tsx`, `audit-cells.tsx`, `audit-columns.tsx`.
`components/system` : `maintenance.tsx`, `system-failure.tsx`, `failure.ts`, `raise.ts`.
`components/reference` : `reference-form.tsx`, `commands.tsx`, `reactivation.tsx`,
`resource-commands.tsx`, `cost-form.tsx`, `kinds.ts`, `settings-forms.tsx`, `in-percent.ts`,
`rate-grid.tsx`, `rate-cells.ts`, `calendar-default.tsx`, `cell-command.tsx`,
`actual-cost-mapping.tsx`, `address.ts`, `resource-lists.tsx`, `resource-grid.tsx`,
`command-columns.tsx`, `section.tsx`.
`app` : `admin/users/page.tsx`, `admin/backups/page.tsx`, `admin/backups/[backupId]/content/route.ts`,
`admin/audit-log/page.tsx`, `admin/access-roles/page.tsx`, `admin/chosen-authors.ts`,
`reference/costs/page.tsx`, `reference/resources/page.tsx`, `reference/risks/page.tsx`,
`reference/costs/actual-cost-mapping/page.tsx`, `reference/settings.ts`, `system/page.tsx`.

**Survolé ou lu par recherche de motifs seulement** (exemptions, casts, conversions, tris, texte en
dur, `page=` des filtres) : `components/admin/{audit-columns,audit-filters,backup-columns,backup-grid}.tsx`,
`{backup,role,user}-chips.ts` ; `components/audit/{audit-chips.ts,audit-grid.tsx}` ;
`components/system/{browser-locale.ts,empty-states.tsx,screen-skeleton.tsx}` ;
`components/reference/{cost-lists,cost-grids,cost-grid,resource-grids,setting-tables,reference-filters}.tsx`,
`{reference-chips,rate-columns,cost-kinds,org-tree}.ts` ; `app/reference/indicators/page.tsx`,
les `loading.tsx`.

**Tests** : en deçà du tiers demandé. Titres et décomptes relevés pour les 57 fichiers ; lus en
partie `user-bulk.dom.test.tsx`, `backup-deposit.dom.test.tsx`, `system.dom.test.tsx`,
`restore-dialog.dom.test.tsx`, `user-attachment.dom.test.tsx`, `settings-pages.test.tsx`,
`reference/pages.test.tsx` (titres). Aucun test sans assertion repéré dans cet échantillon.

**Hors périmètre, consulté pour suivre un chemin** : `api/actions/{access-roles,backups,reference,users,tasks}.ts`,
`components/commands/{held,offer}.ts`, `components/grid/{grid-keyboard,period,check-menu}.ts(x)`,
`backend/src/waterfall/api/{users,reference_settings_write,calendars,org_nodes,resource_roles,cost_types,hourly_rates}.py`
(gardes de permission seulement).

**Références lues** : `docs/dev/typescript.md` en entier ; `agents.md` (deux sections) ; guide
(« Écrans du référentiel », « Paramètres de coûts », « Paramètres de ressources », « Écrans de
l'administration », « Écran des sauvegardes », « Journal d'audit », « Client de l'API », « Un test
qui cite son exigence ») ; EP-03 (US-0360, restauration), EP-18 (US-1060), EP-24 (US-1860), EP-25
(constats reçus, US-2180) ; contrat `schemas/access.yaml`, `BackupSchedule`, `setHourlyRate`,
`getReferenceSettings`/`updateReferenceSettings`, `FileUpload`. **Non lus** : EP-05 et EP-23 hors
recherches ciblées ; `paths/audit.yaml` et `platform.yaml` hors recherches ciblées.

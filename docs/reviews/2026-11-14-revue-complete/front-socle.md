# Revue — socle du front (client d'API, session, navigation, coquille, i18n, thème, commandes)

Commit relu : `29785cc` (`main`). Lecture seule ; aucune commande lourde lancée. Les seuls
scripts exécutés sont des lectures (`python3` de comparaison des catalogues et de comptage des
assertions, `node -e` pour la résolution d'une adresse par `URL`).

## Synthèse

Le socle est d'une qualité nettement au-dessus de la moyenne : la session ne laisse aucun jeton
au navigateur (identifiant opaque `__Host-`, jetons dans Redis), le flux OIDC porte `state`, nonce
et PKCE S256, le rafraîchissement est sérialisé par un verrou Redis éprouvé contre un vrai Redis,
la redirection après connexion est bornée par `returnTarget` (double contrôle avant et après
résolution), le décodeur d'erreurs est unique et ne rejoue jamais une écriture, l'aide en Markdown
est rendue sans HTML brut et ses fichiers lus derrière une garde de chemin. Aucun commentaire
d'exemption, aucun `any`, aucun `dangerouslySetInnerHTML`, aucune variable `NEXT_PUBLIC_*`, aucun
`localStorage` dans le périmètre ; les deux catalogues ont exactement les mêmes 2 879 clés.
Je ne rends **aucun bloquant**. Un majeur : après une connexion refusée par le fournisseur
d'identité, l'écran ne dit pas le refus (il dit « Session requise »), alors que le Vérif de
WF-SEC-0020 le demande et que le critère est clos. Les mineurs sont des trous de durcissement
(témoin de liaison de la connexion sans préfixe `__Host-`, adresse du « retour au projet » lue
d'un témoin sans contrôle de chemin), deux entorses aux invariants maison #688 et défaut n° 24
dans les confirmations de sortie et de marquage, et des fragilités d'exploitation (aucun délai
sur les appels à l'API, code de refus par champ non tenu à la règle du catalogue).

## Constats bloquants

Aucun.

## Constats majeurs

### FSO-01 — Après une connexion refusée par le fournisseur d'identité, l'écran ne dit pas le refus

- **Issue** : #4473 (EP-39), ouverte le 2026-11-21.
- **Où** : `frontend/src/app/auth/callback/route.ts:95-100` (retour refusé → accueil, témoin
  `wf_sign_in_refused`) ; `frontend/src/session/tokens.ts:266-276` (la requête part sans jeton) ;
  `frontend/src/components/system/failure.ts:184` (`signed_out` → textes `failure.signedOut`) ;
  `frontend/messages/fr.json`, `failure.signedOut` (« Session requise — L'écran demande une session
  ouverte : connectez-vous, vous y reviendrez ensuite. ») ; test `frontend/src/session/shell.test.tsx:102` ;
  critère `docs/roadmap/EP-24-consolidation-apres-v0-3-0.md:641-644` (US-1870, `fini`).
- **Quoi** : le Vérif de WF-SEC-0020-A dit « Après une connexion que le fournisseur d'identité
  refuse, l'écran **le dit** et offre de recommencer, sans relancer la connexion de lui-même »
  (`docs/spec/waterfall-spec.md:4324`, le corps à la ligne 4322). La partie « sans relancer » est tenue ; la partie « le dit »
  ne l'est pas : l'écran affiché est celui de toute absence de session, « Session requise », et aucun
  texte des catalogues ne dit qu'une connexion a été refusée (recherche de « refus » dans
  `messages/fr.json` : rien qui concerne la connexion). Le critère de l'EPIC a réécrit le Vérif en
  « laisse l'écran « Session requise », sans boucle », et le test qui cite l'exigence n'affirme que
  ce titre.
- **Scénario** : une personne s'identifie chez Keycloak ; le retour est refusé (erreur dans le
  retour, code refusé, nonce faux — les trois cas de `isRefusedSignIn`, `provider.ts:183-190`).
  Elle arrive sur l'accueil, qui lui dit de se connecter — ce qu'elle vient de faire. Elle clique
  « Se connecter » : la session de Keycloak répond aussitôt, le même refus revient, le même écran
  aussi. Rien ne lui dit que la connexion a été refusée ni qu'il faut joindre un administrateur.
- **Proposition** : le témoin `wf_sign_in_refused` est déjà lisible du serveur ; quand il est
  présent et que la session est `signed_out`, rendre un texte propre (`failure.signInRefused` dans
  les deux catalogues : « La connexion a été refusée par le fournisseur d'identité… ») à la place de
  `failure.signedOut`, dans `SystemFailure` comme dans `not-found.tsx`. Preuve : un test de
  `shell.test.tsx` qui rend l'accueil avec le témoin et affirme la phrase du refus, cité
  `[WF-SEC-0020-A]` ; et corriger la reformulation du critère d'US-1870.
- **Confiance** : confirmé sur les faits (chemin lu de bout en bout : retour → témoin →
  `requestBearer` → 401 → `SignedOut` → `FAILURE_TEXTS`). La gravité tient à la lecture de « le
  dit » : je lis « dit que la connexion est refusée » ; si le coordinateur admet la lecture de
  l'EPIC (« dit qu'il faut une session »), le constat tombe en mineur.

## Constats mineurs

### FSO-02 — Le témoin qui lie une connexion à son navigateur n'a pas de préfixe `__Host-` : un sous-domaine voisin peut le poser

- **Issue** : #4480 (EP-39), ouverte le 2026-11-21, avec FSO-03, FSO-08.
- **Où** : `frontend/src/session/tokens.ts:102-111` (`wf_sign_in_<state>`, `Path=/auth/callback`,
  sans préfixe) ; `frontend/src/app/auth/callback/route.ts:124` (`holdsSignIn`).
- **Quoi** : la défense contre le retour porté à un autre navigateur (RFC 9700 §4.7) repose sur la
  seule présence d'un témoin `wf_sign_in_<state>=1`. Sans `__Host-`, un site d'un sous-domaine voisin
  peut le poser avec `Domain=<domaine parent>`. Le dépôt a retenu ce même attaquant pour le témoin de
  session (#887, commentaire de `tokens.ts:47-53`) ; le témoin de liaison y échappe.
- **Scénario** : l'attaquant lance `/login` chez lui, s'identifie chez Keycloak avec son compte et
  retient l'adresse de retour (`state=S`, `code=C`) sans la suivre. La victime visite
  `evil.<domaine>` : la page pose `wf_sign_in_S=1; Domain=<domaine>; Path=/auth/callback; Secure`
  puis la mène à `/auth/callback?state=S&code=C`. `holdsSignIn(S)` est vrai, `takeSignIn(S)` rend le
  vérificateur (gardé côté serveur), le code est échangé : la victime est connectée au compte de
  l'attaquant (login CSRF) et y saisit ses données.
- **Proposition** : nommer le témoin `__Host-wf_sign_in_<state>` avec `Path=/` (le préfixe
  l'exige) ; coût : un témoin court envoyé à toutes les routes pendant quinze minutes au plus.
  Preuve : `route.test.ts` (login et callback) affirme le nom et les attributs.
- **Confiance** : plausible — le chemin du code est lu de bout en bout ; la pose du témoin par un
  sous-domaine est le comportement normal des navigateurs, non rejoué ici.

### FSO-03 — L'adresse du « retour au projet » lue du témoin n'est pas tenue à un chemin du front

- **Issue** : #4480 (EP-39), ouverte le 2026-11-21, avec FSO-02, FSO-08.
- **Où** : `frontend/src/navigation/context.ts:235-242` (`rememberedAddress`) et `:142`
  (`pathname.split("/").slice(1)` jette ce qui précède la première barre) ;
  `frontend/src/app/layout.tsx:89` ; `frontend/src/components/shell/navigation.tsx:340-352, 384`.
- **Quoi** : `rememberedAddress` valide les segments après la première barre oblique mais rend le
  texte entier : `http:evil.example/projects/abc` passe (segments `projects`, `abc`) et devient le
  `href` du lien « Retour au projet ». Sur une page HTTPS, un navigateur résout cette adresse en
  `http://evil.example/projects/abc` (vérifié : `new URL("http:evil.example/projects/abc",
  "https://wf.example/")`). Le commentaire promet « the shell only ever leads back into a
  project » ; `context.test.ts:127-137` n'éprouve aucune valeur sans barre initiale.
- **Scénario** : même attaquant que FSO-02 (ou tout ce qui écrit un témoin du domaine) : il pose
  `wf_last_project=http%3Aevil.example%2Fprojects%2Fabc`. La victime ouvre l'accueil ; la barre
  latérale offre « Retour au projet », qui mène au site de l'attaquant. React 19 bloque
  `javascript:` ; un schéma http(s) passe.
- **Proposition** : dans `rememberedAddress`, exiger `isApplicationPath(pathname)`
  (`navigation/application-path.ts`, déjà partagé par `returnTarget` et `isScreen`). Preuve :
  ajouter `"http:elsewhere.example/projects/1"`, `"x/projects/1"` et `"\\projects\\1"` au
  `it.each` de `context.test.ts:127`.
- **Confiance** : confirmé (logique lue, résolution vérifiée par `node`) ; l'écriture du témoin par
  un tiers est l'hypothèse.

### FSO-04 — La sortie d'un projet et le marquage d'une révision ne retiennent pas la navigation (#688)

- **Issue** : #4459 (EP-37), ouverte le 2026-11-21, avec FSO-05.
- **Où** : `frontend/src/components/commands/exit-command.tsx:244-260` et
  `frontend/src/components/commands/mark-command.tsx:87-98` : `command().catch(rejected).then(…)`
  sans `useHeldCommand` (aucune occurrence de `held` dans les deux fichiers).
- **Quoi** : l'invariant #688 (« ne perd rien en silence », `docs/roadmap/EP-03-…md:353-358` :
  « c'est vrai de tout refus ») veut qu'un clic sur un lien attende l'écriture en cours et que son
  refus soit dit, à défaut par la barre (#863). `Command` avec `disclosure` ne lance pas d'action :
  les deux formulaires écrivent hors de la retenue. Même nature que #889 (rôles, matrice), corrigé
  ailleurs ; ces deux-ci ne sont cités dans aucun fichier de la roadmap.
- **Scénario** : l'utilisateur confirme « Terminer le projet » (geste définitif), puis clique un
  lien de la barre latérale avant la réponse. La navigation a lieu (une action lancée avant ne la
  retient pas, défaut n° 15), le formulaire est démonté ; l'API refuse (409/412) : le refus n'est
  dit nulle part, ni noté dans l'historique des messages. L'utilisateur croit le projet terminé.
- **Proposition** : passer les deux appels par `held(command())` de `useHeldCommand()`. Preuve :
  un test « refus pendant la navigation » par formulaire, à l'image de `cost-commands.dom.test.tsx`
  (clic d'un lien pendant l'écriture retenue, refus libéré, lien non suivi et refus dit).
- **Confiance** : confirmé (lecture) ; fenêtre étroite, le temps d'une réponse.

### FSO-05 — Défaut n° 24 dans `MarkCommand` et `ExitCommands` : la commande reste active pendant l'écriture

- **Issue** : #4459 (EP-37), ouverte le 2026-11-21, avec FSO-04.
- **Où** : `frontend/src/components/commands/mark-command.tsx:150` (« Annuler » actif pendant
  `busy`), `:95` (`onClose()` à la réponse, sans égard à l'ouverture), `:180-194` (`Command` sans
  `writing`) ; `frontend/src/components/commands/exit-command.tsx:443-460` (`Command` sans
  `writing`) et `:478-486` (`onDone` → `close()` → `setOpen(undefined)` du parent).
  `ConfirmedCommand` (`confirmed-command.tsx:152`, `writing={busy}`) fait ce qu'il faut.
- **Quoi** : une réponse tardive agit sur une autre ouverture que la sienne, ou se perd.
- **Scénario A (marquage)** : « Marquer », nom saisi, envoi ; pendant la requête, « Annuler »
  (non gardé) puis réouverture pour corriger ; la première réponse arrive : succès → `onClose()`
  ferme le formulaire rouvert, la saisie est perdue et le focus part au bouton ; refus →
  `setOutcome` sur un composant démonté, jamais dit.
- **Scénario B (sorties)** : « Terminer » confirmé avec marquage ; pendant la requête, clic sur
  « Abandonner le projet » (la commande n'est pas inactive) et saisie du motif ; la réponse 202 de
  « Terminer » appelle `close()`, qui ferme la confirmation d'« Abandonner » ouverte et lui prend
  le focus. Variante : re-cliquer « Terminer » pendant la requête ferme son formulaire ; un refus
  dit à un champ (`placed`) est alors perdu.
- **Proposition** : donner `writing={busy}` à la `Command` (remonter `busy` de `ExitForm` et de
  `MarkForm`, comme `onWriting` de `ReferenceForm`), garder « Annuler » de `MarkForm` par `busy`.
  Preuve : dans chacun des deux `*.dom.test.tsx`, retenir l'écriture, affirmer la commande
  `aria-disabled`/`aria-busy` et qu'un clic n'ouvre rien, puis libérer.
- **Confiance** : confirmé par lecture (non rejoué) ; fenêtre étroite.

### FSO-06 — Le code d'un refus par champ n'est pas tenu à la règle du catalogue : une clé brute peut s'afficher

- **Issue** : #4460 (EP-37), ouverte le 2026-11-21, avec FSO-07.
- **Où** : `frontend/src/api/problem.ts:141-152` (`envelope` ne juge que `body.code`, et rend
  `body` tel quel, `fields` compris, `:146`) ; `frontend/src/i18n/problem.ts:555-566`
  (`furtherReasons` → `t("errors.<code du champ>")`) et tout formulaire qui rend un champ par
  `problemMessage(field, …)` (ex. `exit-command.tsx:313`).
- **Quoi** : le guide promet « l'écran n'affiche jamais une clé brute » pour un service plus récent
  que le front ; c'est tenu pour le code de l'enveloppe (#2264, testé `problem.test.ts:629`), pas
  pour `fields[].code`. next-intl rend alors le chemin de la clé (`defaultGetMessageFallback`,
  `use-intl` 4.14.9) et écrit sur `console.error`.
- **Scénario** : déploiement où l'API précède le front ; un 422 porte un champ au code nouveau ;
  le formulaire affiche « errors.NEW_CODE » sous le champ.
- **Proposition** : dans `envelope`, ramener à `VALIDATION_FAILED` (ou `INTERNAL_ERROR`) le code
  d'un champ que `CATALOGUES[FALLBACK_LOCALE].errors` n'a pas. Preuve : un cas de plus dans
  `problem.test.ts`, « a refusal whose code the catalogue does not know », avec `fields`.
- **Confiance** : confirmé (lecture du décodeur et du repli de `use-intl`).

### FSO-07 — Aucun délai sur les appels du serveur de Next à l'API

- **Issue** : #4460 (EP-37), ouverte le 2026-11-21, avec FSO-06.
- **Où** : `frontend/src/api/client.ts:154-177, 189` : `fetch(request)` sans `AbortSignal` ni
  dispatcher réglé (aucun `timeout`/`signal` dans `src/api/*.ts`, `startup.ts`,
  `instrumentation.ts`). Le royaume, lui, a cinq secondes (`provider.ts:95`).
- **Quoi** : une API qui accepte la connexion et tarde (verrou de base, cf. le constat reporté
  `docs/roadmap/EP-13-exploitation.md:332`, « écritures de rôles attendent sans délai borné »)
  n'est jamais dite « injoignable » : la requête attend le délai par défaut d'undici (300 s, non
  vérifié dans la version embarquée).
- **Scénario** : une écriture reste sans réponse ; Next tient ses actions serveur dans une seule
  file (défaut n° 15), donc toute action suivante attend ; `heldClick`
  (`navigation/held-writes.ts:215-222`) retient en outre chaque clic sur un lien tant que
  l'écriture n'a pas répondu : l'utilisateur ne peut plus ni écrire ni naviguer par lien, sans
  message, jusqu'au rechargement.
- **Proposition** : un délai pour les lectures (`AbortSignal.timeout`, marqué `Unreachable`), et
  pour les écritures un délai plus long rendu comme un résultat propre (l'écriture a pu être
  faite : ne pas dire « non appliquée »). Coût : une décision sur le sort d'une écriture expirée.
  Preuve : `connections.test.ts`, serveur sur socket qui ne répond pas.
- **Confiance** : l'absence de délai est confirmée ; la durée de 300 s et l'effet sur la file des
  actions sont plausibles (non rejoués).

### FSO-08 — `/login` écrit dans Redis à chaque requête anonyme, sans borne

- **Issue** : #4480 (EP-39), ouverte le 2026-11-21, avec FSO-02, FSO-03.
- **Où** : `frontend/src/app/login/route.ts:53-67` (`rememberSignIn`, clé de quinze minutes par
  appel) ; `deploy/compose/Caddyfile.prod` ne limite aucun débit.
- **Quoi / scénario** : toute requête `GET /login`, sans session, crée une clé `wf:sign-in:<state>`
  dans le Redis qui porte aussi les sessions ; un flot de requêtes le remplit pendant quinze
  minutes (éviction ou refus d'écriture selon sa politique : sessions perdues ou connexions
  impossibles). La route efface aussi le témoin de session de qui la suit (lien d'un autre site) :
  sans gravité, la session de Keycloak reconnecte, mais la session Redis précédente reste orpheline
  jusqu'à son échéance.
- **Proposition** : limiter le débit de `/login` au frontal, ou porter la demande dans un témoin
  chiffré plutôt que dans Redis ; fermer la session Redis que nomme le témoin quand `/login`
  l'efface. À ranger avec EP-13 (exploitation) si le coordinateur le juge hors du livré.
- **Confiance** : plausible (écriture confirmée, effet sur Redis non mesuré).

### FSO-09 — La recherche de la barre du haut est un champ inerte, sans le dire à qui voit l'écran

- **Issue** : #4461 (EP-37), ouverte le 2026-11-21, avec FSO-10.
- **Où** : `frontend/src/components/shell/top-bar.tsx:61-76`.
- **Quoi** : un `<input type="search">` « Rechercher une fonction, un projet… » accepte la saisie
  et ne fait rien ; « La recherche est à venir » n'est écrit que pour les lecteurs d'écran
  (`sr-only`). Aucune US de la roadmap ne la porte (recherche de `comingSoon`, « recherche de la
  coquille » dans `docs/roadmap/` : rien).
- **Proposition** : retirer le champ jusqu'à sa fonction, ou le rendre `aria-disabled` avec la
  phrase visible. Preuve : `shell.dom.test.tsx`.
- **Confiance** : confirmé.

### FSO-10 — Le catalogue entier (199 Ko) est sérialisé dans chaque document et chaque relecture

- **Issue** : #4461 (EP-37), ouverte le 2026-11-21, avec FSO-09.
- **Où** : `frontend/src/components/shell/shell.tsx:72`
  (`<NextIntlClientProvider messages={CATALOGUES[locale]}>`, composant client alimenté par un
  composant serveur) ; `frontend/messages/fr.json` : 199 218 octets, 72 espaces de noms.
- **Quoi** : les props d'un composant client passent par la charge RSC : les 2 879 textes partent
  avec chaque document, et avec chaque réponse qui rend à nouveau la mise en page (`refresh()` des
  actions serveur, `router.refresh()`).
- **Proposition** : ne donner au fournisseur que les espaces de noms que des composants client
  lisent, ou charger le catalogue comme un module du lot client (mis en cache par le navigateur).
  Coût : un inventaire des espaces lus côté client ; gain : ~200 Ko bruts de moins par relecture ;
  risque de ne rien faire : le poids croît avec chaque écran.
- **Confiance** : plausible (mécanisme sûr, poids sur le fil non mesuré ; Caddy compresse).

## Points forts

- **Session** : aucun jeton dans le navigateur ; témoin `__Host-`, `HttpOnly`, `Secure`,
  `SameSite=Lax` ; `state` pris une seule fois (`GETDEL`), nonce vérifié, PKCE S256 ; identifiant de
  session neuf à chaque connexion (pas de fixation) ; verrou de rafraîchissement à durée double du
  délai du royaume, libéré par son seul détenteur (script Lua) ; `renewSession` en `SET XX` (une
  session fermée par le canal de retour ne renaît pas) ; déconnexion d'une session perdue par
  ticket lié au témoin. Tests contre un vrai Redis et un faux royaume qui signe
  (`tokens.test.ts:173-197`, `store.test.ts`, `route.test.ts`).
- **Redirection après connexion** : `returnTarget` (`navigation/login.ts:73-85`) contrôle avant et
  après résolution ; la cible est gardée côté serveur sous le `state`.
- **Client d'API** : un seul lieu d'appel réseau, `server-only`, garde ESLint éprouvée ; une
  lecture coupée repart une fois, une écriture jamais ; le journal ne garde que méthode et chemin.
- **Erreurs** : décodeur unique (`decode`), `Unreachable` distinct d'un défaut, `digest` préfixé
  pour qu'aucune valeur de l'API ne prenne un sens pour Next, référence de corrélation filtrée.
- **Habilitations** : le front masque seulement (`readableGroups`, `platformOffer`,
  `available_commands`) ; une lecture sans droit est un 404 de l'API et mène à « introuvable ».
- **Aide** : cible confrontée à la table avant tout chemin, garde `startsWith(directory + sep)`,
  `skipHtml` et liste d'éléments admis, liens hors aide rendus en texte.
- **Formats** : aucun flottant sur `Decimal`/`Money` (décalage de virgule sur la chaîne, `BigInt`),
  dates de planning lues à minuit UTC, horodatages écrits dans le navigateur par
  `useSyncExternalStore` (pas d'écart d'hydratation).
- **Règles** : zéro commentaire d'exemption, zéro `any`, trois `as unknown as` commentés (corps
  binaires que le contrat type en chaîne) ; 869 tests du périmètre, aucun sans assertion (les huit
  signalés par le script passent par l'assistant `refused`).

## Couverture

- **Lu en entier** : `src/session/*.ts` (hors tests) ; `src/app/auth/**/route.ts`,
  `src/app/login/route.ts`, `login/unavailable/page.tsx` ; `src/api/client.ts`, `server.ts`,
  `problem.ts`, `problem-kind.ts`, `relay.ts`, `disposition.ts`, `every-page.ts`,
  `actions/{session,account,preferences,history,tasks,help,nodes,projects}.ts` ; `src/startup.ts`,
  `src/instrumentation.ts` ; `src/navigation/{login,application-path,context,functions,home,
  breadcrumbs,held-writes,document}.ts` ; `src/components/shell/{shell,shell-frame,top-bar,
  account-menu,navigation,navigation-hold,left-refusals,shown-project,project-switcher,
  breadcrumbs,help-markdown}.tsx` ; `src/components/commands/` sauf `icons.ts` (partiel) ;
  `src/components/notices/` ; `src/components/signal/signal.tsx` ;
  `src/components/context/{reading,read-only,structure,chip-lift}.ts(x)` ;
  `src/components/account/{avatar-form,avatar-source,avatar-types,avatar-picture,initials,
  account-name}` ; `src/i18n/{format,locale,request,catalogues}.ts` ; `src/help/{help,read}.ts` ;
  `src/currency/` ; `src/theme/theme.ts` ; `src/app/{layout,error,global-error,not-found,title}`,
  `[...path]/page.tsx`, `(home)/page.tsx` ; `next.config.ts`, `Dockerfile`, `package.json`,
  `pnpm-workspace.yaml`, `postcss.config.mjs`, `components.json`, `tsconfig.json`,
  `vitest.config.ts`.
- **Échantillonné** : `actions/{backups,users,exchanges}.ts` (extraits), les autres actions par
  leurs signatures ; `i18n/problem.ts` (en-tête et `problemMessage`) ; `context-banner.tsx`
  (330 premières lignes) ; `help-panel.tsx` (en-tête et effets) ; `preferences-form.tsx`,
  `account/page.tsx` ; `ui/{sidebar,dialog,sheet,dropdown-menu}.tsx` ; `eslint.config.mjs`
  (structure) ; tests : titres de `tokens`, `store`, `callback`, `login`, `backchannel-logout`,
  `exit-command`, corps de `tokens.test.ts:60-200` et de `route.test.ts:160-200`, comptage
  automatique des assertions sur les 86 fichiers de test du périmètre ; catalogues comparés par
  script (clés, valeurs vides, pluriels).
- **Non lu** : `src/api/generated/` (engendré) ; `navigation/{pages,account}.ts`,
  `functions.json` ; `shell/{page-header,function-display,logo,help-link,mockup-notice}` (ce
  dernier survolé) ; `context/{indicator,structure-choice}.tsx` ; `account/{account-details,
  anonymized-name,form,me}` ; le reste de `components/ui/` (alert-dialog, context-menu, popover,
  radio-group, table, tooltip…) ; `src/theme/globals.css` et ses tests de contraste ;
  `frontend/help/**/*.md` ; `account/avatar/page.tsx`, les `loading.tsx` ; le corps des tests non
  cités. L'accessibilité des thèmes (contrastes) et des primitives `ui` n'a donc pas été jugée
  au-delà de ce qui est dit ci-dessus.

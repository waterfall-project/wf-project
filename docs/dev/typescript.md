# Règles de codage — TypeScript

Pour le front (`frontend/`). Ce fichier complète le [guide](README.md) : il dit comment
s'écrit le TypeScript ici. Il ne recopie ni la spécification, ni le contrat, ni les jeux de
règles des outils ; il y renvoie.

Une règle qu'un outil contrôle nomme son contrôle. Une règle que rien ne contrôle le dit :
c'est la revue qui la tient, et l'agent de revue cherche nommément les défauts de la
dernière section.

## Ce que les outils tiennent

| Jeu de règles | Où | Contrôle |
|---|---|---|
| Lint — ESLint, Next.js, typescript-eslint strict avec les types, JSDoc ; chaque ajout et retrait avec sa raison | `frontend/eslint.config.mjs` | `make lint-front` |
| Format | `frontend/.prettierrc.json` | `make lint-front` |
| Typage strict, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` | `frontend/tsconfig.json` | `make typecheck-front` |
| Client de l'API engendré du contrat | `frontend/src/api/generated/` | `make client-up-to-date` |
| Aucun commentaire de configuration d'ESLint dans le code | `noInlineConfig` de `frontend/eslint.config.mjs` | `make lint-front` |
| Aucun commentaire d'exemption (`eslint-disable`, `@ts-ignore`, `prettier-ignore`…) ; `TODO(#12)` ; 1 000 lignes au plus | `tools/src/wftools/sources.py` | `make sources` |
| Aucun texte d'interface écrit en dur ; catalogues typés par la référence | `frontend/eslint.config.mjs`, `frontend/messages/` | `make lint-front`, `make typecheck-front`, `make catalogs` |
| Aucune couleur ni police écrite dans le code : la charte en jetons, contrastes AA mesurés | `frontend/eslint.config.mjs`, `frontend/src/theme/` | `make lint-front`, `make test-front` |
| Couverture du code : 90 % des lignes, 85 % des branches | seuils dans `tools/src/wftools/codecoverage.py` ; mesure réglée par `coverage` de `frontend/vitest.config.ts` | `make coverage-front` |

## Règles de conception

### L'API ne s'appelle que par le client engendré

Un appel à l'API passe par le client de `frontend/src/api/`, typé par le contrat, et depuis
le serveur Next seulement ; aucun appel réseau ailleurs, aucune fonction écrite à la main qui
en double une opération. Une opération qui manque est une modification du contrat, suivie de
`make generate-client`.

*Pourquoi* : un client écrit à la main dérive du contrat (WF-ARC-0020, WF-ARC-0060).
*Contrôle* : ESLint refuse hors de `src/api/client.ts` les moyens connus d'appeler le
réseau — `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`, l'import d'un client http —,
et, dans un fichier `"use client"`, tout import de `src/api/` autre que ses actions serveur
et des types ; un module de `src/api/actions/` s'ouvre sur `"use server"`. C'est le contrôle
de la chaîne, éprouvé par `src/api/network-guard.test.ts`, et il voit l'import direct : le
cas transitif — un module sans directive qui importe `@/api/server`, et qu'un composant
client importe — reste à `server-only`, qu'importent `client.ts` et `server.ts`, le filet
de `next build`, que `make build-front` lance au palier rapide, sans API joignable (#131),
et `make e2e` au palier complet.
`make client-up-to-date`.

### Le front affiche, il ne calcule pas

Une date, un montant, un indice, un total s'affichent tels que l'API les rend. Le front ne
recalcule rien de ce que le back calcule, ne réordonne pas ce que le back ordonne, et
n'invente pas de valeur à la place d'un `Computable` absent : il dit qu'elle manque.

*Pourquoi* : un calcul fait dans le front finit par différer de celui du serveur, et un
écran par mentir (WF-ARC-0020) ; `docs/api/DECISIONS.md`, « Calculé contre saisi ».
*Contrôle* : la revue.

### Aucun texte d'interface écrit en dur

Un libellé, un message, une unité destinés à l'utilisateur viennent des catalogues de
traduction ; un message d'erreur se construit depuis le `code` et les `params` de
l'enveloppe. Ce que l'utilisateur a saisi s'affiche tel quel, jamais traduit.

*Pourquoi* : l'interface existe en français et en anglais (§3.1.5), et une chaîne en dur
est une traduction oubliée (WF-QUA-0070). *Contrôle* : `react/jsx-no-literals` et
`no-restricted-syntax` (`make lint-front`) refusent le texte du JSX et les attributs lus —
`aria-label` et ses pareils, `title`, `alt`, `placeholder`, `label`, la `value` d'un
bouton `input` — écrits en littéral, dans une branche ou une concaténation. Restent à la
revue : les autres props de nos propres composants (`heading="…"`), et une chaîne bâtie par
une fonction ou une méthode (`.join`, `.concat`), dans le JSX ou hors de lui.
`make typecheck-front` et `make catalogs` tiennent les clés : guide, « Clés de traduction ».

### Un nombre ne passe jamais par un flottant

Un `Decimal`, un `Money`, des `Hours` se formatent depuis la chaîne du contrat, par
`src/i18n/format.ts` ; aucun `Number()`, `parseFloat` ni opération arithmétique ne les
touche. Une date de planning s'affiche telle quelle, sans fuseau ; un horodatage, en heure
locale du poste, dans le navigateur (`LocalTime`).

*Pourquoi* : un flottant arrondit ce que le serveur a calculé exactement (WF-DAT-0100), et
une date lue à minuit dans le fuseau du poste tombe la veille à l'ouest de Greenwich.
*Contrôle* : la revue ; les tests de `src/i18n/format.test.ts` éprouvent les formats sous
plusieurs fuseaux.

### Où s'exécute un composant

Un composant est serveur par défaut ; il ne devient client (`"use client"`) que pour ce qui
en a besoin — saisie, état local, événements. Une donnée se lit côté serveur quand la page
le permet, et côté client par le client engendré, jamais en recopiant une réponse dans un
état global.

Un composant serveur ne prend pas d'identifiant de `useId` : il nomme une section par
`aria-label` et un champ par un identifiant à lui. `useId` est pour les composants client.

Un module serveur — une page de `src/app`, un module sans directive, une action `"use server"` —
n'importe d'un module `"use client"` que des composants et des types : toute autre valeur, une
constante, une fonction, y arrive en référence au client (défaut n° 12). Ce que les deux côtés
lisent vit dans un module sans directive.

*Pourquoi* : moins de code envoyé au navigateur, et une seule source pour chaque donnée :
la réponse de l'API. Et les identifiants que React donne aux composants serveur d'une page et aux
composants client de la coquille peuvent se rencontrer : la région du détail d'un risque s'est
nommée d'après l'aide de la recherche de la coquille (#251). *Contrôle* : la revue ; `useId` dans
un module sans `"use client"`, `src/components/use-id-guard.test.ts` (`make test-front`), qui
cherche son import depuis `react`, alias compris, hors des commentaires ; une valeur d'un module
`"use client"` importée par un module serveur, `src/components/client-import-guard.test.ts`
(#548), qui lit les imports et les réexportations de chaque module serveur, hors des commentaires
et des imports de types, et refuse tout nom qui n'est pas celui d'un composant — un nom en
PascalCase, jamais une constante en capitales ; un espace de noms (`* as`, `export * from`) n'en est
jamais un, et un défaut se juge sous le nom qu'on lui donne.

### Accessibilité

Un contrôle se trouve par son rôle et son nom accessible : un bouton est un `button`, un
lien un `a`, une icône seule porte un nom. Tout se fait au clavier.

*Pourquoi* : l'accessibilité minimale de la spécification (§3.6), et des parcours qui
trouvent les éléments comme un utilisateur. *Contrôle* : les quelques règles `jsx-a11y`
qu'active la configuration de Next.js ; les parcours de bout en bout, par `getByRole` ; le
reste, la revue.

### Les tests

- Un test unitaire est un fichier `*.test.ts` ou `*.test.tsx` à côté de son code ; un
  parcours de bout en bout vit dans `frontend/e2e/`.
- Un test qui porte le Vérif d'une exigence la cite entre crochets dans son titre :
  `it("… [WF-IHM-0010-A]", …)`.
- Il reçoit les données du contrat — `frontend/src/test/fixtures.ts` lit les exemples de
  `fixtures/api/` —, jamais un objet inventé qui n'a pas la forme d'une réponse.
  Un exemple servi au front vit sous `fixtures/api/`, en objet Example d'OpenAPI, et se
  nomme par son fichier : `"project"` est `fixtures/api/project.json`. `fakeClient` est le
  client engendré, dont un middleware répond par opération (`"GET /projects/{project_id}"`)
  un exemple nommé, une séquence de réponses ou une enveloppe `Problem`, et enregistre les
  appels, corps compris, dans `calls` ; une réponse ne prend qu'un statut que le contrat
  déclare pour l'opération, avec un corps seulement si ce statut en a un, et de sa sorte —
  un exemple nommé pour du JSON, un `Blob` ou un texte avec son type de média pour le reste
  (avatar, sauvegarde, métriques) : le typage le refuse sinon. L'exemple nommé est l'un de
  ceux que le contrat cite pour ce statut de cette opération (`src/api/generated/examples.d.ts`,
  que `make generate-client` écrit) : `{"GET /projects": "project"}` ne se compile pas. Une
  réponse qui manque est un exemple que le contrat cite pour l'opération.
- Un composant serveur de `src/app/` se teste dans le projet `node` (`*.test.tsx`), sans
  document, comme il s'exécute ; un composant client, dans le projet `dom`
  (`*.dom.test.tsx`), par Testing Library.
- Un test unitaire rend le composant et vérifie ce qu'il produit ; un parcours de bout en
  bout trouve les éléments par `getByRole` ou `getByLabel` de Playwright, jamais par une
  classe CSS.
- Un test vérifie quelque chose : une assertion sur ce que l'utilisateur voit ou sur l'appel
  fait, pas le simple rendu sans erreur.

*Pourquoi* : WF-QUA-0010 ; un test sur des données inventées passe sur ce que l'API ne
renverra jamais. *Contrôle* : `make requirements`, `make coverage-front` ; la valeur d'une
assertion, la revue.

## Défauts déjà rencontrés

Chacun a été trouvé dans du code réel, souvent par une revue automatique, et se
reproduira. L'agent de revue les cherche nommément, dans le diff et dans le code voisin qui
partage le même invariant. Un défaut trouvé en revue et qui peut revenir s'ajoute ici.

1. **Réponse périmée appliquée à la mauvaise sélection.** Une requête part pour le projet A ;
   l'utilisateur passe à B ; la réponse arrive et écrase l'écran de B — ou son échec
   s'affiche sur B. L'identité de la sélection se capture avant l'appel et se revérifie à
   l'arrivée, sur le succès comme sur l'échec.
2. **Garde de sélection mise à jour dans un effet.** La référence à « la sélection
   courante » est mise à jour dans un `useEffect` : entre le changement et l'effet, une
   réponse ancienne passe encore la garde. Elle se met à jour au moment même du changement.
3. **Ordre recalculé autrement que le back.** Un tri côté front traite `null` comme `0` là
   où le back met les absents en dernier : tout ce qui n'a pas de position remonte.
4. **État terminal oublié.** Une condition « en lecture seule » couvre un état et oublie
   l'autre ; la liste complète des valeurs est celle du type engendré du contrat, pas celle
   qu'on se rappelle.
5. **Retour anticipé qui avale un avis obligatoire.** L'écran vide sort tôt et omet le
   bandeau qui devait s'afficher dans tous les cas.
6. **Commande offerte que le back refusera.** Un bouton reste actif pour un cas que l'API
   rejette : la commande se désactive selon la même règle, au lieu de laisser l'erreur
   arriver.
7. **Position calculée sur une valeur brute.** Un point d'insertion déduit d'un champ
   `position` stocké, alors que des frères peuvent en manquer : c'est l'index réel dans
   l'arbre affiché qui compte.
8. **Tests arrêtés à la logique pure.** La fonction de calcul d'une commande est testée,
   mais pas la page qui l'emploie : ni le succès de bout en bout, ni la sélection changée
   pendant la requête.
9. **Chemin groupé testé seulement dans ses refus.** Une sélection multiple n'a que des
   tests de rejet ; un groupe valide qui traverse tout le parcours n'est jamais éprouvé.
10. **Code commenté laissé dans un fichier.** Aucun outil ne le détecte en TypeScript —
    `ERA001` est propre à Ruff, et une heuristique crierait à tort. Un bloc de code ou de
    JSX en commentaire se supprime : l'historique git garde tout.
11. **Test qui passe sur les lignes sans rien vérifier.** Il rend le composant, fait monter
    la couverture, et n'affirme rien de ce que l'utilisateur voit.
12. **Fonction passée d'un composant serveur à un composant client.** Une icône Lucide, un
    rappel donnés en prop à un composant `"use client"` depuis un composant serveur : le rendu
    au serveur échoue, et l'écran de panne s'affiche. Un test unitaire qui rend l'arbre entier
    par `renderToStaticMarkup` ne franchit pas cette frontière et passe ; seul le parcours de
    bout en bout la voit. Ce qui la franchit est une donnée ou un élément déjà dessiné
    (`commandIcon`), jamais une fonction. L'inverse échoue de même : une fonction exportée d'un
    module `"use client"` et appelée par un composant serveur — le filtre des sorties du cycle
    de vie (US-0210/L1). Une valeur aussi : la clé des préférences de la grille des taux, exportée
    de `rate-grid.tsx` et lue par sa page, y arrivait en référence au client, et la page ne
    retrouvait jamais les réglages de la grille, sans qu'aucun test ne le voie (EP-02/L42a). Ce que
    les deux côtés lisent vit dans un module sans directive (`exits.ts`, `rate-columns.ts`).
13. **Visible dans le conteneur, pas dans la fenêtre.** Un parcours affirme l'en-tête ou les
    totaux d'une grille par `toBeVisible` ou par un cadre maison, qui ne regardent pas la
    fenêtre : la ligne des totaux est sous le bas de l'écran et le parcours passe. La cause
    dans le code est une hauteur calculée à la main d'après ce qui précède
    (`calc(100svh-…)`), que le premier ajout au-dessus de la grille invalide (#163). Une
    visibilité s'affirme par `toBeInViewport` ou `withinBox` (`e2e/scroll.ts`), et un écran
    de grille prend `Screen fill`, jamais une hauteur calculée. Aucun outil ne le tient : la
    revue le cherche.
14. **Les lignes de la réponse passées à chaque ligne rendue.** Le tableau des six mille lignes
    donné en prop à chaque ligne ou à chaque cellule d'une grille : le build de développement
    de React compare les props de ce qu'il rend à nouveau, et la navigation d'un tri sur le
    serveur de développement a pris une demi-seconde de plus, assez pour qu'un parcours de la
    chaîne dépasse son attente (US-0150/L1). La production n'en dit rien. Ce qui descend
    jusqu'aux lignes lit la réponse par une fonction (`answer` de `DenseGrid`), jamais par le
    tableau. Il est revenu dans un objet : le lecteur de ce dont dépend une valeur calculée
    portait les lignes de sa lecture, et la navigation d'un tri a pris 0,8 s de plus — le
    parcours du tri a dépassé son attente (EP-02/L4, run 36630647717). Un objet qui descend
    jusqu'aux lignes lit lui aussi la réponse par une fonction (`reading` de `DependencyReader`).
    Aucun outil ne le tient : la revue le cherche.
15. **Action serveur lancée après une navigation.** Next porte chaque action serveur dans l'état
    de son routeur, dans une seule file : une navigation ne se montre qu'une fois répondues les
    actions lancées après elle. Une préférence écrite au clic d'en-tête retenait ainsi l'adresse
    du tri d'un aller-retour, et de tout ce qui attendait devant elle dans la file : sous charge,
    le parcours du tri dépassait son attente (EP-02/L4, run 36624394005). Ce qu'un geste qui
    navigue doit écrire part une fois la page montrée (`recordShown` de `useSettingsWriter`), ou
    avant la navigation : une action lancée avant, au montage d'un écran, ne la retient pas —
    retenue huit secondes, la lecture des tâches de fond que la coquille lançait alors laissait
    paraître l'adresse du tri à son heure ; de même la relecture des totaux d'une grille cherchée,
    partie après une écriture et avant le clic du tri (EP-02/L12). Aucun outil ne le tient : la
    revue le cherche, et une action retenue dans un parcours le prouve (`grid.spec.ts`, le tri
    qui n'attend ni ses préférences ni la relecture des totaux).
16. **Horloge de la page figée à travers une navigation.** Un parcours fige l'horloge
    (`page.clock.pauseAt`) pour que la lecture d'une tâche attende, puis clique vers un autre
    écran : quand le serveur tarde, la navigation montre le squelette de `loading.tsx`, et
    React retient l'écran arrivé derrière un minuteur — le délai de révélation d'une frontière
    `Suspense`, mesuré sur l'horloge de la page —, que l'horloge figée ne laisse jamais partir.
    Le parcours échoue une fois sur trois (#165). Ce qui doit attendre se retient sur le réseau
    (`page.route`), jamais en figeant l'horloge d'une page qui navigue — et une action serveur
    retenue doit être partie avant le clic qui navigue (`page.waitForRequest`, attendue avant
    le clic) : lancée après, elle retient la navigation elle-même (n° 15), et le parcours
    attend un écran que sa propre retenue empêche de paraître (`tasks.spec.ts`). Aucun outil ne
    le tient : la revue le cherche.
17. **Route atteinte par un clic, compilée pendant l'attente.** `next dev` compile une route à
    sa première visite ; atteinte par un clic, elle est attendue cinq secondes par une
    assertion, que la compilation mange au premier lancement (#142). Un parcours compile
    d'abord les routes qu'il atteint par un clic (`compile`, `e2e/compile.ts`). Aucun outil
    ne le tient : la revue le cherche.
18. **Contexte de la coquille changé pendant qu'une page attend d'être révélée.** La coquille
    est au-dessus de chaque page, dont `loading.tsx` fait une frontière `Suspense`. Le serveur
    envoie la page avec le document, mais React en retient la révélation un instant (`<!--$~-->`) ;
    un fournisseur de la coquille dont la valeur change à ce moment — un effet au montage,
    comme la reprise des tâches de l'onglet — fait rendre la page à neuf dans le navigateur, à
    côté de celle du serveur, que le document garde, cachée, jusqu'à la révélation : deux champs
    de fichier portent un instant le même nom, et un parcours en mode strict échoue : rejoué en
    boucle, deux champs 9 fois sur 40, puis 0 sur 110 une fois corrigé (#173).
    Ce qui change au-dessus des pages pendant l'hydratation — les tâches suivies, la largeur de
    la fenêtre, le projet montré — ne passe pas par la valeur d'un contexte, qui reste stable :
    il se lit dans un magasin externe (`useSyncExternalStore`), auquel ne s'abonnent que les
    pièces de la coquille qui le montrent, et une écriture qui ne change rien n'avertit personne
    (#180). Des tests hydratent une frontière en attente sous chaque fournisseur
    (`task-tracker.dom.test.tsx`, `shell/hydration.dom.test.tsx`) ; aucun outil ne le tient : la
    revue le cherche.
19. **Geste d'un parcours avant l'hydratation.** Un parcours ouvre une page par son adresse et
    clique aussitôt un bouton : le serveur a rendu la page, le navigateur la montre, mais React
    ne l'a pas encore hydratée, et le clic se perd — le bloc de la navigation reste fermé, le tri
    n'est jamais demandé, et le parcours attend jusqu'à sa fin, sous charge seulement (#471,
    #419). Un écran de projet s'ouvre par `openHydrated` (`e2e/hydration.ts`), qui attend le
    cookie que la coquille n'écrit que dans un effet ; hors projet, le geste se répète jusqu'à ce
    que React y réponde (`setExpanded`, `openMenu`). Un lien, lui, n'en a pas besoin : suivi avant
    l'hydratation, il charge son écran en document entier. Aucun outil ne le tient : la revue le
    cherche.
20. **Formulaire remonté par une `key` sur l'adresse.** Pour qu'une période ou un texte que
    l'adresse change — en revenant dans l'historique — se montre à neuf, le formulaire porte une
    `key` tirée de l'adresse : appliqué, il est remonté, le bouton ou le champ qui avait le focus
    disparaît, et le focus tombe sur `<body>`, la navigation ne déplaçant rien (`usePendingAddress`
    pousse avec `scroll: false`) — les filtres des coûts réels et du portefeuille (#537). Une saisie
    se date par ce que l'adresse filtrait quand elle a été faite (`useDatedEntry` de
    `components/grid/dated-entry.ts`), sans `key`. Elle s'oublie pour de bon dès que l'adresse en
    nomme une autre, et non seulement à l'affichage : sinon, revenue en arrière à l'adresse sur
    laquelle elle avait été faite — taper une date, l'appliquer, puis « Précédent » —, l'adresse
    montrerait la saisie abandonnée au lieu de sa propre valeur. La recherche des grilles
    (`SearchField`) et les bornes (`RangeFilter`) sont encore remontées par une `key` (#553). Des
    tests appliquent une saisie, rendent à nouveau le filtre sous l'adresse appliquée puis sous celle
    d'origine, et affirment le focus et la valeur (`costs.dom.test.tsx`, `portfolio.dom.test.tsx`,
    `reference-filters.dom.test.tsx`, `audit.dom.test.tsx`, `actual-costs.spec.ts`) ; aucun outil ne
    le tient : la revue le cherche.

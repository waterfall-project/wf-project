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
de `next build`, que la chaîne ne lance qu'au palier complet, pour la mesure de la seconde
(`make e2e`), et une fois le faux back démarré (#131). `make client-up-to-date`.

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

*Pourquoi* : moins de code envoyé au navigateur, et une seule source pour chaque donnée :
la réponse de l'API. *Contrôle* : la revue.

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
  (avatar, sauvegarde, métriques) : le typage le refuse sinon.
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
    (`commandIcon`), jamais une fonction.
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
    tableau. Aucun outil ne le tient : la revue le cherche.

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
| Couverture du code : 90 % des lignes, 85 % des branches | seuils dans `tools/src/wftools/codecoverage.py` ; mesure réglée par `coverage` de `frontend/vitest.config.ts` | `make coverage-front` |

## Règles de conception

### L'API ne s'appelle que par le client engendré

Un appel à l'API passe par le client de `frontend/src/api/`, typé par le contrat ; aucun
`fetch` ailleurs, aucune fonction écrite à la main qui en double une opération. Une
opération qui manque est une modification du contrat, suivie de `make generate-client`.

*Pourquoi* : un client écrit à la main dérive du contrat (WF-ARC-0020, WF-ARC-0060).
*Contrôle* : ESLint refuse `fetch` hors de `src/api/` ; `make client-up-to-date`.

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
est une traduction oubliée (WF-QUA-0070). *Contrôle* : le contrôle de complétude des
catalogues arrive avec EP-02 ; jusque-là, la revue. Les trois pages du parcours témoin
n'affichent que des données, et EP-02 les remplace.

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
10. **Test qui passe sur les lignes sans rien vérifier.** Il rend le composant, fait monter
    la couverture, et n'affirme rien de ce que l'utilisateur voit.

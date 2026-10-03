# Spécification Waterfall — sources et projection

## Principe

Trois sources font foi, et trois seulement :

| Source | Contient | Éditée avec |
|---|---|---|
| `stb-waterfall.docx` | tout le texte, les tableaux, les exigences | Word |
| `waterfall.visuels.drawio` | les diagrammes dessinés : contexte, arborescences, cycle de vie, flux de travail | draw.io |
| `figures/*.mmd` | les diagrammes écrits : modèle conceptuel, déploiement, séquences | un éditeur de texte |

`waterfall-spec.md` est **généré** à partir de ces sources. Il n'est jamais
édité à la main : la prochaine génération écraserait la modification sans
prévenir. Il existe pour qu'un agent puisse lire la spécification — pas pour
remplacer le document Word, qui reste le livrable.

## Régénérer

Depuis la racine du dépôt :

```bash
make build-doc          # régénère la projection
make build-doc-strict   # échoue au moindre avertissement, pour la CI
```

Ou directement `./build.sh`, qui accepte les mêmes options.

Le script affiche les avertissements, puis ce qui a changé depuis la génération
précédente. Options utiles :

- `--verbose` : ajoute les messages de traçabilité (rattachement géométrique des
  arêtes draw.io, validation des diagrammes) ;
- `--strict` : code de retour non nul si un avertissement est émis, pour une
  intégration continue.

Prérequis : `pandoc`, Python 3.11+, et `mmdc`
(`npm i -g @mermaid-js/mermaid-cli`) — ce dernier est optionnel, il sert à
vérifier que les diagrammes produits compilent réellement.

## Ce que la génération ajoute au document Word

Trois choses, qui sont ce qui rend le retour de revue possible :

1. **La numérotation de section sur chaque titre.** Word l'affiche mais ne la
   stocke pas dans le texte ; sans elle, un constat de revue ne serait pas
   localisable dans le document. `§3.4.5.1` dans un constat désigne exactement la
   section `3.4.5.1` de Word.
2. **Les exigences en blocs YAML**, avec leur numéro de section. Un agent peut
   alors les citer et les filtrer (par domaine, par flexibilité) au lieu de
   reformuler un tableau.
3. **Les diagrammes en Mermaid**, donc lisibles. `tools/figures.toml` associe
   chaque légende de figure à sa source, de deux origines possibles :
   - une **page du fichier draw.io** (clé `page`), convertie en flowchart ;
   - un **fichier `.mmd` du dépôt** (clé `source`), repris tel quel — c'est la
     seule voie pour un diagramme de classes ou de séquence.

   Le texte alternatif de l'image dans Word n'est jamais lu : Word le réécrit sur
   une ligne, et un diagramme n'y survit pas. Une figure sans entrée est conservée
   en image, et signalée.

L'index des exigences est reconstruit à la génération : les numéros de page de
Word n'ont pas de sens dans un Markdown.

## Ajouter une figure

Un diagramme dessiné — boîtes et flèches — se fait dans draw.io :

1. Dessiner la page dans `waterfall.visuels.drawio` ; lui donner un nom explicite.
2. Insérer l'image dans Word, avec sa légende `Figure n — <titre>`.
3. Ajouter l'association dans `tools/figures.toml` :

   ```toml
   [[figure]]
   legende = "<fragment de la légende Word>"
   page = "<nom de la page draw.io>"
   direction = "LR"
   ```

Un diagramme écrit — classes, séquence, ou tout diagramme que draw.io ne sait pas
rendre — se fait en Mermaid :

1. Écrire le source dans `figures/<nom>.mmd`.
2. Engendrer l'image (`mmdc -i figures/<nom>.mmd -o figures/<nom>.png -b white -s 2`)
   et l'insérer dans Word avec sa légende. Si l'image est plutôt dessinée dans
   draw.io à partir du source, comme celles du modèle conceptuel, le fichier
   `.mmd` reste la source et l'image n'a pas de `.png` dans `figures/`.
3. Déclarer la source :

   ```toml
   [[figure]]
   legende = "<fragment de la légende Word>"
   source = "figures/<nom>.mmd"
   ```

Le texte alternatif de l'image dans Word ne porte jamais le source : il n'est pas
lu, et Word ne le conserve pas fidèlement.

Dans draw.io, relier les flèches **aux formes** plutôt que de les poser librement :
une flèche non reliée n'a pas de source ni de cible dans le fichier, et le
convertisseur doit deviner ses extrémités par proximité géométrique. Il le fait,
et le signale, mais c'est une approximation qui peut se tromper si deux formes
sont proches.

## Cycle de revue

```
Word + draw.io  ──►  ./build.sh  ──►  waterfall-spec.md
                                            │
                                            ▼
                                   revue par un agent
                              (consignes : revue/PROMPT.md)
                                            │
                                            ▼
                              revue/constats/AAAA-MM-JJ-*.md
                                            │
                                            ▼
                      corrections appliquées à la main dans Word
                                            │
                                            └──►  ./build.sh  (le diff montre
                                                  ce qui a effectivement changé)
```

Lancer une revue, depuis la racine du dépôt :

```
Lis docs/spec/revue/PROMPT.md et applique-le à docs/spec/waterfall-spec.md.
Périmètre : <sections, ou « document complet »>.
```

Les constats sont **appliqués dans Word**, jamais dans le Markdown. Chaque
constat porte une section, un identifiant d'exigence et une citation exacte,
pour être retrouvé par recherche dans le document. Après intégration, mettre à
jour la ligne `Statut` du constat : les cinq statuts possibles sont définis dans
`revue/constats/MODELE.md`, et c'est cette ligne qui distingue un constat traité
d'un constat oublié.

Relancer `./build.sh` après les corrections : le diff affiché vérifie que les
modifications Word ont bien atterri là où on les attendait.

Une revue peut aussi se faire dans Word même, en commentaires et en suivi des
modifications : les corrections sont alors proposées en modifications suivies,
avec une réponse à chaque commentaire, et l'auteur les accepte ou les refuse dans
Word. Tant que le document porte des modifications en attente ou des fils de
commentaires non résolus, `./build.sh` l'avertit et `make build-doc-strict`
échoue : pandoc accepte toutes les modifications en silence et ignore les
commentaires, et la projection présenterait comme adopté ce qui ne l'est pas
encore. La projection ne se régénère donc que depuis un document accepté.

## Suivi de version

Le dépôt est sous Git, et c'est ce qui rend le cycle ci-dessus lisible : le diff
entre deux générations de `waterfall-spec.md` montre exactement l'effet d'une
session de revue sur la spécification. Les sources Word et draw.io sont
versionnées avec elle, de sorte qu'une correction et son effet apparaissent dans
le même commit.

## Emplacement

Tout ce qui concerne la spécification vit dans `docs/spec/` : les deux sources,
la projection, les figures, les outils et les revues. Les chemins des scripts
sont relatifs à ce répertoire, et `./build.sh` peut être lancé depuis n'importe
où.

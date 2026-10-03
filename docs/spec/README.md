# Spécification Waterfall — sources et projection

## Principe

Deux fichiers font foi, et deux seulement :

| Fichier | Contient | Édité avec |
|---|---|---|
| `stb-waterfall.docx` | tout le texte, les tableaux, les exigences | Word |
| `waterfall.visuels.drawio` | les diagrammes | draw.io |

`waterfall-spec.md` est **généré** à partir de ces deux fichiers. Il n'est jamais
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
3. **Les diagrammes en Mermaid**, donc lisibles. Trois origines possibles :
   - le **texte alternatif** de l'image dans Word, s'il contient déjà du Mermaid —
     c'est le cas de la figure 2, dont le diagramme draw.io a été créé à partir
     d'un source Mermaid conservé dans le texte alternatif ;
   - le fichier **draw.io**, via `tools/figures.toml` qui associe une légende de
     figure à une page du fichier ;
   - un **fichier `.mmd` du dépôt**, via la clé `source` de `tools/figures.toml`.
     C'est la seule voie pour un `sequenceDiagram` : Word aplatit le texte
     alternatif sur une ligne, et une séquence ne se re-segmente pas sans
     ambiguïté. Les figures 18 et 19 viennent de là.

   Une figure sans aucune des trois est conservée en image, et signalée.

L'index des exigences est reconstruit à la génération : les numéros de page de
Word n'ont pas de sens dans un Markdown.

## Ajouter une figure

1. Dessiner la page dans `waterfall.visuels.drawio` ; lui donner un nom explicite.
2. Insérer l'image dans Word, avec sa légende `Figure n — <titre>`.
3. Ajouter l'association dans `tools/figures.toml` :

   ```toml
   [[figure]]
   legende = "<fragment de la légende Word>"
   page = "<nom de la page draw.io>"
   direction = "LR"
   ```

Deux variantes :

- si le diagramme vient d'un source Mermaid simple — un `flowchart`, un
  `classDiagram`, un `stateDiagram` —, le coller dans le **texte alternatif** de
  l'image dans Word. Aucune entrée dans `figures.toml` n'est alors nécessaire, et
  le source reste attaché à l'image ;
- si c'est un `sequenceDiagram`, ou tout diagramme que l'aplatissement de Word
  abîmerait, écrire le source dans `figures/<nom>.mmd`, engendrer l'image
  (`mmdc -i figures/<nom>.mmd -o figures/<nom>.png -b white -s 2`), l'insérer dans
  Word **sans texte alternatif**, et déclarer la source :

  ```toml
  [[figure]]
  legende = "<fragment de la légende Word>"
  source = "figures/<nom>.mmd"
  ```

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

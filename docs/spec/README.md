# Waterfall specification — sources and projection

> This is the English version of [README-fr.md](README-fr.md); when the two differ, the French text
> is the reference.

## Principle

Three sources are authoritative, and three only:

| Source | Holds | Edited with |
|---|---|---|
| `stb-waterfall.docx` | all the text, the tables, the requirements | Word |
| `waterfall.visuels.drawio` | the drawn diagrams: context, trees, life cycle, workflow | draw.io |
| `figures/*.mmd` | the written diagrams: conceptual model, deployment, sequences | a text editor |

`waterfall-spec.md` is **generated** from these sources. It is never
edited by hand: the next generation would overwrite the change without
warning. It exists so that an agent can read the specification — not to
replace the Word document, which remains the deliverable.

## Regenerating

From the root of the repository:

```bash
make build-doc          # regenerates the projection
make build-doc-strict   # fails on the slightest warning, for the CI
```

Or directly `./build.sh`, which accepts the same options.

The script prints the warnings, then what has changed since the previous
generation. Useful options:

- `--verbose`: adds the traceability messages (geometric attachment of the
  draw.io edges, validation of the diagrams);
- `--strict`: non-zero return code if a warning is emitted, for continuous
  integration.

Prerequisites: `pandoc`, Python 3.11+, and `mmdc`
(`npm i -g @mermaid-js/mermaid-cli`) — the latter is optional, it serves to
check that the diagrams produced really compile.

## What the generation adds to the Word document

Three things, which are what makes the review feedback possible:

1. **The section numbering on each heading.** Word displays it but does not
   store it in the text; without it, a review finding could not be located
   in the document. `§3.4.5.1` in a finding designates exactly section
   `3.4.5.1` of Word.
2. **The requirements as YAML blocks**, with their section number. An agent can
   then cite and filter them (by domain, by flexibility) instead of
   rewording a table.
3. **The diagrams in Mermaid**, hence readable. `tools/figures.toml` associates
   each figure caption with its source, from two possible origins:
   - a **page of the draw.io file** (key `page`), converted to a flowchart;
   - an **`.mmd` file of the repository** (key `source`), taken up as is — this is
     the only way for a class or sequence diagram.

   The alternative text of the image in Word is never read: Word rewrites it on
   one line, and a diagram does not survive it. A figure without an entry is kept
   as an image, and flagged.

The index of the requirements is rebuilt at generation: the page numbers of
Word have no meaning in a Markdown.

## Adding a figure

A drawn diagram — boxes and arrows — is made in draw.io:

1. Draw the page in `waterfall.visuels.drawio`; give it an explicit name.
2. Insert the image in Word, with its caption `Figure n — <title>`.
3. Add the association in `tools/figures.toml`:

   ```toml
   [[figure]]
   legende = "<fragment de la légende Word>"
   page = "<nom de la page draw.io>"
   direction = "LR"
   ```

A written diagram — classes, sequence, or any diagram draw.io cannot
render — is made in Mermaid:

1. Write the source in `figures/<nom>.mmd`.
2. Generate the image (`mmdc -i figures/<nom>.mmd -o figures/<nom>.png -b white -s 2`)
   and insert it in Word with its caption. If the image is instead drawn in
   draw.io from the source, like those of the conceptual model, the `.mmd`
   file remains the source and the image has no `.png` in `figures/`.
3. Declare the source:

   ```toml
   [[figure]]
   legende = "<fragment de la légende Word>"
   source = "figures/<nom>.mmd"
   ```

The alternative text of the image in Word never carries the source: it is not
read, and Word does not keep it faithfully.

In draw.io, connect the arrows **to the shapes** rather than placing them freely:
an unconnected arrow has neither source nor target in the file, and the
converter has to guess its ends by geometric proximity. It does so, and
flags it, but it is an approximation that can be wrong if two shapes
are close.

## Review cycle

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

To launch a review, from the root of the repository:

```
Lis docs/spec/revue/PROMPT.md et applique-le à docs/spec/waterfall-spec.md.
Périmètre : <sections, ou « document complet »>.
```

The findings are **applied in Word**, never in the Markdown. Each
finding carries a section, a requirement identifier and an exact quotation,
so that it can be found by searching the document. After integration, update
the `Statut` line of the finding: the five possible statuses are defined in
`revue/constats/MODELE.md`, and it is this line that distinguishes a finding dealt
with from a finding forgotten.

Run `./build.sh` again after the corrections: the diff displayed checks that the
Word changes did land where they were expected.

A review can also be done in Word itself, in comments and tracked
changes: the corrections are then proposed as tracked changes,
with a reply to each comment, and the author accepts or rejects them in
Word. As long as the document carries pending changes or unresolved comment
threads, `./build.sh` warns about it and `make build-doc-strict`
fails: pandoc accepts all the changes silently and ignores the
comments, and the projection would present as adopted what is not yet
adopted. The projection is therefore regenerated only from an accepted document.

## Versioning

The repository is under Git, and that is what makes the cycle above readable: the diff
between two generations of `waterfall-spec.md` shows exactly the effect of a
review session on the specification. The Word and draw.io sources are
versioned with it, so that a correction and its effect appear in
the same commit.

## Location

Everything that concerns the specification lives in `docs/spec/`: the two sources,
the projection, the figures, the tools and the reviews. The paths of the scripts
are relative to this directory, and `./build.sh` can be launched from
anywhere.

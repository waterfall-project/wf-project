## What this changes

<!-- One or two sentences. What is different after this, that was not before? -->

## Why

<!-- The reasoning, not the list of files. This is the part nobody can reconstruct
     six months from now. If it integrates review findings, name them: C-042, C-083… -->

## What it deliberately leaves alone

<!-- Optional, but valuable: what you decided not to touch, and why. -->

---

Tick what applies; delete the sections that do not.

**Specification** (`docs/spec`)
- [ ] the change was made in `stb-waterfall.docx` or `waterfall.visuels.drawio`, never in the generated Markdown
- [ ] `make build-doc` was run, and the diff of `waterfall-spec.md` shows exactly what was expected
- [ ] the build emits no warning
- [ ] the findings integrated have their `Statut` updated in `docs/spec/revue/constats/`
- [ ] new requirements carry a Motif and an observable Vérif, and no identifier was reused or renumbered

**Contract** (`docs/api`)
- [ ] `make lint-openapi` passes with no error
- [ ] `make inventory` was run, and the coverage it reports is what was intended
- [ ] every new operation cites in its description the requirements it realises
- [ ] the conventions of `docs/api/README.md` are held: UUIDs, `snake_case`, exact decimals, one error envelope, 404 against 403, `lock_version`

**Tooling** (`Makefile`, `docs/*/tools`)
- [ ] the projection and the inventory are unchanged, or the change is intended and explained above
- [ ] identifiers, comments and console output are in English

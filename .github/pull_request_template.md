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
- [ ] the change was made in `docs/spec/stb-waterfall.docx` or `docs/spec/waterfall.visuels.drawio`, never in the generated Markdown
- [ ] `make build-doc` was run, and the diff of `docs/spec/waterfall-spec.md` shows exactly what was expected
- [ ] the build emits no warning
- [ ] the findings integrated have their `Statut` updated in `docs/spec/revue/constats/`
- [ ] new requirements carry a Motif and an observable Vérif, and no identifier was reused or renumbered

**Contract** (`docs/api`)
- [ ] `make lint-openapi` passes with no error
- [ ] `make inventory` was run, and the coverage it reports is what was intended
- [ ] every new operation cites in its description the requirements it realises
- [ ] the conventions of `docs/api/README.md` are held: UUIDs, `snake_case`, exact decimals, one error envelope, 404 against 403, `lock_version`

**Lot** (code, from an epic's lot plan)
- [ ] this pull request targets its epic's branch, `epic/EP-nn`, and names its lot issue: `[US-nnnn/Ln]` or `[EP-nn/Ln]`
- [ ] each acceptance criterion the lot closes is listed with the test that carries it, and that test cites the requirement
- [ ] the real size of the lot, from `make lot-size`, is given next to the estimate of its issue; the target is in `docs/roadmap/README.md`, section « Lots »
- [ ] review findings outside the lot's scope were opened as issues, not fixed here
- [ ] the chain passes, and nothing in the epic's branch is left half-built by this merge

**Tooling** (`Makefile`, `docs/*/tools`)
- [ ] the projection and the inventory are unchanged, or the change is intended and explained above
- [ ] identifiers, comments and console output are in English

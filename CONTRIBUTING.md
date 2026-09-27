# Contributing to Waterfall

Two rules explain almost everything below. **The specification is not the Markdown file** —
it is a Word document, and the Markdown is generated from it. **The contract is
authoritative** — an interface change is a contract change first, and the code follows.

Issues and pull requests are welcome in French or in English. The specification stays in
French, the code and the contract stay in English; that split is deliberate and is not open
for renegotiation file by file.

## Getting set up

```bash
make check-tools      # tells you what is missing
make build-doc        # regenerate the specification projection
make lint-openapi     # check the contract
```

You need Python 3.11+, `pandoc`, Node with `npx`, and `mmdc`
(`npm i -g @mermaid-js/mermaid-cli`) if you want the diagrams validated.

## Changing the specification

`docs/spec/waterfall-spec.md` is **generated**. Never edit it: the next `make build-doc`
overwrites your change without warning. The sources are:

| File | Holds | Edited with |
|---|---|---|
| `docs/spec/stb-waterfall.docx` | all the text, tables and requirements | Word |
| `docs/spec/waterfall.visuels.drawio` | the diagrams | draw.io |

So a specification change is a change to a binary file, which a pull request cannot show
usefully. The workflow that replaces the diff is a **review**:

1. open an issue, or write a findings file in `docs/spec/revue/constats/`, following
   `MODELE.md` and the instructions in `docs/spec/revue/PROMPT.md`;
2. each finding carries a **location** (`§3.4.5.1`, `WF-REV-0050-A`), an **exact quotation**
   so it can be found by searching the Word document, and a **proposed replacement wording**
   — a finding without a proposal is a finding someone else has to write again;
3. the author applies the correction in Word, runs `make build-doc`, and the diff of the
   generated Markdown shows what actually landed;
4. the finding's `Statut` becomes `intégré`, `sans objet` or `reporté`. That line is what
   distinguishes a treated finding from a forgotten one.

Nine reviews have gone through this cycle; read one before writing your first, and read the
existing findings before raising a new one — a finding already settled is not raised twice.

### Requirement conventions

- An identifier reads `WF-CODE-nnnn-A`: domain, number by tens, revision letter. It is
  **never reused and never renumbered**, so that a finding written a year ago still points
  somewhere.
- The same goes for **FBS codes**: a function keeps its code for ever, and a new function
  takes the next free one. Never renumber by position.
- Cross-references use a requirement identifier or an FBS code, never a deep section number
  — sections move, identifiers do not.
- A requirement carries a **Motif** (why it exists) and a **Vérif** (an observable condition).
  « The system is efficient » is not a criterion. Numeric examples in a Vérif are test
  fixtures, and the tests reuse them verbatim.
- One concept, one owner: the attributes of an object live in a single « Attributs de X »
  requirement, and nowhere else.

## Changing the contract

`docs/api` is hand-written and authoritative (`WF-ARC-0060`). Before opening a pull request:

```bash
make lint-openapi     # must pass with no error
make inventory        # regenerates the inventory and the coverage
```

Conventions, each of them dictated by a requirement rather than by taste:

| Convention | Requirement |
|---|---|
| Server-generated UUIDs, never a sequential identifier in a URL | `WF-DAT-0060` |
| `snake_case` everywhere, no exception | — |
| The names from the object-to-table mapping in §4.4.1: `estimate_line` is an estimate line, `cost_line` an actual cost line | §4.4.1 |
| Exact decimals carried as strings, planning dates without time, timestamps in UTC | `WF-DAT-0100` |
| One error envelope, carrying a machine code and its parameters, never a sentence | `WF-ARC-0110` |
| 404 when the read permission is missing, 403 when it is the write or the contributor status | `WF-ADM-0110` |
| `lock_version` on concurrent writes, refused with 412 | `WF-IHM-0110` |
| A long operation returns a background task, never a result | `WF-ARC-0090` |

Every operation cites, in its description, the requirements it realises. `make inventory`
turns that into a coverage table — and fails if a requirement domain escapes the contract
without a declared reason.

## Changing the code

There is none yet. When there is, the specification already fixes what will be asked of it,
and it is worth knowing before writing the first line:

- **every F0 requirement is covered by at least one automated test citing its identifier**,
  and a release is refused while one is uncovered (`WF-QUA-0010`);
- the **numeric examples of the Vérif fields are unit tests** of the calculation core, run
  without a database or a browser (`WF-QUA-0020`);
- typing, static analysis and formatting are **blocking**, and no warning is tolerated:
  what is not blocking is removed from the rule set (`WF-QUA-0030`);
- end-to-end tests run against a Compose platform on the **reference dataset**, at the
  volumes of §4.6.2 (`WF-QUA-0040`, `WF-QUA-0050`);
- response times are **measured at each release** and compared to the previous one
  (`WF-QUA-0060`).

## Branches, commits, pull requests

`main` holds the published state. Work happens on a branch — today `spec` — and reaches
`main` through a pull request.

Commit messages are written in French, like the specification. A subject line that says what
changed, then a body that says **why**: the reasoning is the part nobody can reconstruct six
months later. Look at `git log` before writing your first one.

A pull request states what it changes and what it leaves alone. If it touches the
specification, it names the findings it integrates; if it touches the contract, it says
whether `make lint-openapi` and `make inventory` were run. The template in
`.github/pull_request_template.md` asks for exactly that, and the issue forms in
`.github/ISSUE_TEMPLATE/` ask a specification finding for its location, its exact
quotation and its proposed wording — the three things without which a finding has to be
written again.

## Licence

Contributions are accepted under the [GNU Affero General Public License v3.0](LICENSE) only,
the licence of the project.

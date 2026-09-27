<p align="center">
  <img src="docs/assets/waterfall_logo.svg" alt="Waterfall" width="320">
</p>

Cost, plan and pilot long-running projects: one task tree seen from both time and money,
revisions that keep each offer and review readable, risk provisions, actual costs imported
from the ERP, and earned-value indicators from the task up to the portfolio.

Waterfall is built for projects that last — ten years, sometimes fifteen — where the offer
is negotiated over months, the baseline moves only by contract, and the question « are we
still where we said we would be? » has to be answerable years after the people who
answered it first have left.

> **Status: no code yet.** This repository holds the specification and the interface
> contract. The implementation starts from them, not the other way round.

## What makes it different

**One task tree, two views.** A task carries its estimate lines. The schedule and the
estimate are not two documents to keep in step — they are the same tree, read from the
side of time or from the side of money.

**A revision is a complete snapshot.** Every offer and every periodic review is frozen
whole: its cost structures, and the referential values it used — hourly rates, calendars,
roles. A reorganisation or a corrected rate years later does not move it, so an offer
remains readable and recomputable long after it was sent.

**Two amounts per line, never one.** A budgeted amount, which only a contractual act
changes, and a re-estimated amount, which each review updates. That is what stops an
amendment from silently rebasing the baseline onto the latest forecast — the defect that
makes so many cost-control tools quietly optimistic.

**Provisions stay outside the baseline** until the risk occurs. Covering a risk is not a
budget for work you hope never to do. When a risk does occur, the baseline grows by the
provision alone, never by what the risk actually cost: the gap shows up as drift, which is
what it is.

**Earned value is measured, not declared.** A task is finished or it is not; its budgeted
amount is earned on the day it finishes. No percentage is ever typed in, so progress cannot
be argued with.

**The portfolio is a ratio of sums, never an average of indices.** An average gives a
fifty-thousand deal the same weight as a million-euro one, and measures nothing.

## What is in this repository

| Path | Contents |
|---|---|
| `docs/spec` | the specification: **203 requirements**, its Word and draw.io sources, the generated Markdown projection, the pipeline tools, and the nine reviews that shaped it |
| `docs/api` | the interface contract: **150 operations** over 116 paths and 147 schemas, hand-written OpenAPI, with the endpoint inventory and the design decisions |

**The specification is in French.** It is a formal requirements document — every
requirement carries an identifier, a rationale and an observable acceptance criterion — and
translating it would double the source of truth. The contract, the code and this file are in
English. [README-fr.md](README-fr.md) says all of this in French.

### Where to start reading

- [`docs/api/INVENTAIRE.md`](docs/api/INVENTAIRE.md) — every endpoint, and which requirement
  it serves. The fastest way to see what the product does.
- [`docs/api/DECISIONS.md`](docs/api/DECISIONS.md) — what the contract had to decide, and why.
- [`docs/spec/waterfall-spec.md`](docs/spec/waterfall-spec.md) — the whole specification,
  generated from Word so that a machine can read it.
- [`docs/spec/revue/constats/`](docs/spec/revue/constats/) — the nine reviews. This is where
  the reasoning lives: what was wrong, what replaced it, and why.

## Commands

```bash
make                  # list the commands
make build-doc        # regenerate the Markdown projection from Word and draw.io
make lint-openapi     # check the contract
make build-openapi    # check, then bundle the contract into one file
make mock             # serve a fake backend from the contract
make inventory        # regenerate the endpoint inventory and requirement coverage
make check-tools      # tell me what is missing
```

Prerequisites: Python 3.11+, `pandoc`, Node with `npx`, and `mmdc`
(`npm i -g @mermaid-js/mermaid-cli`) to validate the diagrams.

## Planned stack

Decided in the specification, and each choice is argued there rather than asserted:
**Next.js** and **TypeScript** on the front, with custom grids built on TanStack Table and
curves on Apache ECharts; **FastAPI** and **Python** behind a single modular core plus a
worker; **PostgreSQL** as the only source of truth, **Redis** for cache and the task queue,
an **S3-compatible** store for files in transit and backups; **Helm** for Kubernetes and
**Compose** for development and small installations.

The contract is written by hand and is authoritative: the front's client is generated from
it, and the chain rejects a build whose responses drift from it.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) — how the specification is changed (never by editing the
generated Markdown), how the review cycle works, and the conventions that are not
negotiable file by file.

## Licence

[GNU Affero General Public License v3.0](LICENSE) only.

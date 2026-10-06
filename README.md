<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/waterfall_logo-dark.svg">
    <img src="docs/assets/waterfall_logo.svg" alt="Waterfall" width="320">
  </picture>
</p>

Cost, plan and pilot long-running projects: one task tree seen from both time and money,
revisions that keep each offer and review readable, risk provisions, actual costs imported
from the ERP, and earned-value indicators from the task up to the portfolio.

Waterfall is built for projects that last — ten years, sometimes fifteen — where the offer
is negotiated over months, the baseline moves only by contract, and the question « are we
still where we said we would be? » has to be answerable years after the people who
answered it first have left.

> **Status: the foundation is in place, the product is not yet.** The specification and the
> interface contract come first; the repository now also carries the empty back and front,
> the tooling and the chain every line of product code will pass through. The product is
> built epic by epic, as [`docs/roadmap`](docs/roadmap/README.md) plans it.

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

**Provisions never enter the baseline.** Covering a risk is not a budget for work you hope
never to do. The baseline revision keeps its provisions apart, as a risk reserve; the
estimate to complete carries those of the risks identified today, new ones included; a risk
that occurs enters the project with a zero budgeted amount. Risk coverage compares the
reserve with what the risks actually cost: the gap shows up as drift, which is what it is.

**Earned value is measured, not declared.** A task is finished or it is not; its budgeted
amount is earned on the day it finishes. No percentage is ever typed in, so progress cannot
be argued with.

**The portfolio is a ratio of sums, never an average of indices.** An average gives a
fifty-thousand deal the same weight as a million-euro one, and measures nothing.

## What is in this repository

| Path | Contents |
|---|---|
| `docs/spec` | the specification: **203 requirements**, its Word and draw.io sources, the generated Markdown projection, the tools that produce it, and the reviews that shaped it |
| `docs/api` | the interface contract: **150 operations** over 116 paths and 147 schemas, hand-written OpenAPI, with the endpoint inventory and the design decisions |
| `docs/roadmap` | the plan: thirteen epics in the order they are built, their stories, their design, and the rules that take an epic from its stories to delivered code |
| `docs/dev` | the development guide, the coding rules per language, and the rules the agents follow |
| `backend/` | one Python package: the business core, the API service and the worker |
| `frontend/` | the Next.js application, its client generated from the contract, its end-to-end paths |
| `tools/` | the repository tools: requirement coverage, roadmap check, source rules, lot size |
| `fixtures/` | the numeric examples of the specification, and the data the fake back serves |
| `deploy/` | packaging: the development Compose today, the Helm chart later |
| `.github/workflows/` | the chain, run on every pull request |
| `.claude/agents/` | the agents that frame an epic, deliver its lots, develop and review |

**The specification is in French**, and so is the documentation. It is a formal requirements
document — every requirement carries an identifier, a rationale and an observable acceptance
criterion — and translating it would double the source of truth. The contract, the code and
this file are in English. [README-fr.md](README-fr.md) says all of this in French.

### Where to start reading

- [`docs/api/INVENTORY.md`](docs/api/INVENTORY.md) — every endpoint, and which requirement
  it serves. The fastest way to see what the product does.
- [`docs/api/DECISIONS.md`](docs/api/DECISIONS.md) — what the contract had to decide, and why.
- [`docs/spec/waterfall-spec.md`](docs/spec/waterfall-spec.md) — the whole specification,
  generated from Word so that a machine can read it.
- [`docs/spec/revue/constats/`](docs/spec/revue/constats/) — the reviews. This is where
  the reasoning lives: what was wrong, what replaced it, and why.
- [`docs/roadmap/README.md`](docs/roadmap/README.md) — in what order the product is built,
  and how work moves from an epic to reviewed code.
- [`docs/dev/README.md`](docs/dev/README.md) — the development guide: where each piece lives
  and which check holds each rule.

## How the work is done

Every requirement is closed by exactly one epic. An epic is framed — stories whose acceptance
criteria quote the specification word for word, a design, a plan of lots — then delivered one
lot at a time: one issue, one branch, one pull request into the epic's integration branch,
merged only when the local review and the chain are green. The chain lints, type-checks and
tests only what a change touches, runs coverage and end-to-end tests when a pull request is
merged, and fails on any requirement a test cites wrongly. Agents can do the framing, the
development, the review and the delivery; merging an epic into `main` is always a person's
decision.

## Commands

```bash
make                      # list the commands
make check-tools          # tell me what is missing
make check BASE=origin/epic/EP-01  # the checks of what my change touches
make check-all            # run every family of checks
make dev                  # the front against the fake back, on http://localhost:3000
make mock                 # the fake back alone, served from the contract's examples
make e2e                  # the end-to-end paths, in a browser
make requirements         # which requirements the tests cover
make roadmap              # the roadmap confronted with the specification
make build-doc            # regenerate the Markdown projection from Word and draw.io
make generate-client      # regenerate the front's API client from the contract
```

Prerequisites: [uv](https://docs.astral.sh/uv/), which brings Python 3.13 for the back and
the tools; a Python 3.11 or later on the `PATH` as `python3`, which builds the projection;
Node 24, whose corepack brings pnpm; Docker, for `make dev`; `pandoc` 3.1.11.1, the version the projection
is generated with; and `mmdc` (`npm i -g @mermaid-js/mermaid-cli`) to validate the diagrams.

## Stack

Decided in the specification, and each choice is argued there rather than asserted:
**Next.js** and **TypeScript** on the front, with custom grids built on TanStack Table and
curves on Apache ECharts; **FastAPI** and **Python** behind a single modular core plus a
worker; **PostgreSQL** as the only source of truth, **Redis** for cache and the task queue,
an **S3-compatible** store for files in transit and backups; **Helm** for Kubernetes and
**Compose** for development and small installations.

The contract is written by hand and is authoritative: the front's client is generated from
it, the fake back serves its examples, and the chain will reject a service whose responses
drift from it.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) — how the specification is changed (never by editing the
generated Markdown), how the review cycle works, how code arrives in lots, and the
conventions that are not negotiable file by file.

## Licence

[GNU Affero General Public License v3.0](LICENSE) only.

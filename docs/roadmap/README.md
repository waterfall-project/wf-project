# Waterfall's roadmap

> This is the English version of [README-fr.md](README-fr.md); when the two differ, the French text
> is the reference.

## Principle

The epics and the stories live here, in **hand-written** Markdown. Unlike the
specification, none of these files is generated: they are authoritative as they stand.

GitHub issues are opened only when an epic starts, and the split is the same as everywhere
else in this repository — a document is authoritative, GitHub is a working
surface:

| Authoritative for | Where |
|---|---|
| the intention: scope, acceptance criteria, requirements realised, operations consumed | the epic's file |
| the state: who takes it, where it stands, what gets discussed | the GitHub issue |

So an issue does not copy the acceptance criteria: it points at the file and at the
identifier. Two descriptions of the same work always end up diverging, and it is the file
that will be read again in five years.

**The epics cover the whole horizon; the stories are detailed only one epic ahead.**
Detailing today the stories of the last slice would cost the price of rewriting them:
what the first increment teaches changes the cutting of the next. What is fixed for the
whole horizon is the 212 requirements — not their cutting into work.

## Layout

| Path | Content |
|---|---|
| `README.md` | this file: the rules, and the ordered list of the epics |
| `MODELE.md` | the form of an epic and that of a story |
| `EP-nn-<intitulé>.md` | an epic, **its stories and its design included** |

The stories are not one file each: an epic is the unit of work — it is the one that gets
started, the one whose issues get opened — and fifty files of twenty lines would read
less well than the dozen coherent files here. It is the same reason that already
groups the contract's schemas by family.

## Identifiers

An epic carries `EP-nn`, a story carries `US-nnnn` in steps of ten. Like the requirement
identifiers and the FBS and PBS codes, they are **never reused and never
renumbered**: an inserted story takes the next free number, not the place it occupies
in the list. The title of an issue carries the identifier first — `[US-0130] …` — so that
the link can be followed both ways.

## Traceability

Each story cites the requirements it realises and the operations of the contract it
consumes. Its acceptance criteria **take up the Vérif field of the requirements cited, word
for word**, numeric examples included: they are what will become the test cases
(WF-QUA-0020), and a rewritten criterion is a criterion that drifts from what will be checked. A
deliberate departure is noted as such, with its reason.

A requirement can be realised by several epics: one begins it, another finishes it,
because its Vérif cites what a later epic builds. The table of an epic says so in its
« Portée » column — `entière`, `début — close en EP-nn` or `fin — amorcée en EP-nn` —, and
each story says which of its Vérif sentences waits for another epic. **A requirement is closed
by one epic only**: the one that checks it in full.

An F0 requirement that no story cites is either forgotten work or a requirement without a
surface — and in that case the reason is written down. It is the same mechanism as the coverage of
`make inventory` for the contract, and the counterpart of the requirement coverage report that
WF-QUA-0010 asks of the chain.

## Statuses

For an epic, five values and no other:

| Status | Meaning |
|---|---|
| `à planifier` | the epic is written, but its stories or its design are not settled; as long as its stories are not written, the US column of its table carries « — » |
| `prêt` | its stories are detailed and its design is validated; nothing prevents cutting it into lots |
| `en cours` | its lot plan is validated, and its issues are open on GitHub; its integration branch exists only from its first lot |
| `livré` | all its stories are done, its definition of done is checked on its integration branch, and that branch is merged into `main` |
| `abandonné : <pourquoi>` | acknowledged, then set aside; the file remains |

For a story, five as well:

| Status | Meaning |
|---|---|
| `à faire` | initial state |
| `en cours` | taken by someone |
| `fini` | the acceptance criteria are checked, and the tests that carry them cite the requirements (WF-QUA-0010) |
| `reportée : <vers quel EPIC>` | moved out of this epic, explicitly |
| `abandonnée : <pourquoi>` | the need no longer holds |

Reading this directory must be enough to know where the project stands, without opening GitHub.

## Families

The `famille` field of an epic's front matter says what it adds to the product and who proves
its requirements, according to the document's PBS breakdown — not everything it touches:

| Family | What it covers |
|---|---|
| `front` | the web application, its generated client and its components (PBS-1) |
| `back` | the API service, the worker, the business core, the contract and the integration of the identity provider (PBS-2) |
| `plateforme` | a component the epic adds to what carries and runs the two: data components, observability, packaging, chain, scheduled tasks, identity provider (PBS-3 to PBS-5); and the repository tooling, when it is the object of the epic (EP-01) |

A component the epic uses without adding it does not change its family: a functional epic
writes to PostgreSQL or drops a file on the object storage without being `plateforme`,
since it is another epic that adds the component: EP-03 for PostgreSQL and Redis, EP-13
for the packaging of the platform. Likewise, a tool written in
passing by a lot does not change the family of its epic: EP-02 stays `front`.

An epic that builds several declares them all, separated by commas —
`famille: front, back` for a vertical slice. `make roadmap` fails on an epic that
declares none, that declares another one, or the same one twice.

The family says which tests prove what the epic closes: a requirement closed by an epic whose
only family is `front` is proved by the tests of the front; closed by another one, it
is not as long as only the front and the end-to-end tests cite it (`make requirements`).

## Order of the epics

<!-- One epic per line, in the order they start. -->

| EPIC | Title | Status | Depends on |
|---|---|---|---|
| [EP-01](EP-01-socle-de-developpement.md) | Development foundation | livré | nothing |
| [EP-02](EP-02-maquette-du-front.md) | Mockup of the front on a simulated contract | livré | EP-01 |
| [EP-03](EP-03-comptes-et-habilitations.md) | Accounts, authentication and access rights | livré | EP-01, EP-02 |
| [EP-14](EP-14-maquette-du-front-finitions.md) | Mockup of the front: finishing touches | livré | EP-02 |
| [EP-15](EP-15-maquette-ajustements.md) | Mockup: adjustments from the validation | livré | EP-14 |
| [EP-16](EP-16-maquette-durcissement.md) | Mockup and contract: hardening | en cours | EP-15 |
| [EP-17](EP-17-maquette-finitions-accessibilite.md) | Mockup: finishing touches and accessibility | à planifier | EP-16 |
| [EP-05](EP-05-referentiel.md) | Reference data of the company | à planifier | EP-16 |
| [EP-04](EP-04-projets-et-revisions.md) | Projects, revisions and life cycle | à planifier | EP-05 |
| [EP-06](EP-06-planification.md) | Planning | à planifier | EP-04 |
| [EP-07](EP-07-chiffrage-et-devis.md) | Costing and estimate | à planifier | EP-06 |
| [EP-09](EP-09-couts-reels-et-reste-a-engager.md) | Actual costs, remaining to commit and cost import | à planifier | EP-07 |
| [EP-10](EP-10-indicateurs.md) | Project indicators | à planifier | EP-09 |
| [EP-08](EP-08-avenants-et-risques.md) | Amendments, risks and provisions | à planifier | EP-10 |
| [EP-11](EP-11-portefeuille.md) | Portfolio | à planifier | EP-08 |
| [EP-12](EP-12-echanges-de-fichiers.md) | File exchanges (FLX-01 to FLX-06) | abandonné : each round trip is validated in its functional block | — |
| [EP-13](EP-13-exploitation.md) | Operations and going to production | à planifier | EP-04 |

The order of the list is not that of the numbers, and that is deliberate: an identifier is not
renumbered. The distribution of the requirements put the reference data before the projects —
a project cannot be created without it (WF-CYC-0120) —, the import of actual costs in EP-09 — a
cost line exists only by import (WF-CRE-0010) —, the indicators as soon as there are actual
costs and a remaining to commit, and the risks after them — an occurrence is costed through the remaining
to commit, merges like an amendment, and the indicators are then read in front of it (review of
the distribution, 2026-10-09). File
exchanges no longer have an epic of their own (review of the distribution, 2026-10-09): each round trip
is validated in its functional block — MS Project in EP-06, which builds the import mechanism,
the estimate in EP-07, the remaining to commit in EP-09 —, and EP-03 makes the platform deployable and
backupable from the first service on, for demonstrations.

EP-14 completes the screens of EP-02, merged into `main` on 2026-10-09 so that EP-03 starts without
waiting: it moves in parallel with EP-03, without touching its domain. EP-15 follows the
validation, by the author, of the specification 1.0, of the mockup and of the contract, done after the
merge of EP-03 then of EP-14 (author's decision of 2026-10-11): it carries out the adjustments
it decided, so that every write operation of the contract has a gesture in the
mockup. EP-16 follows it (author's decision of 2026-10-18). Since its framing, it **freezes the
contract** (author's decision of 2026-10-22): it keeps everything that touches the contract or may
touch it, with what the 2026-10-22 rework of the specification adds to the model (#1304). It
also keeps, by exception, end-to-end paths played against the built front, without which
the merge queue is not stable. The rest moves to EP-17, which finishes the mockup outside the
contract: the accessibility of the dialogs, the minor items of the screens, the cosmetics. The browsers
move to EP-13. The domain epics, from EP-05 on, serve a contract that EP-16 has frozen, and EP-17
can move in parallel with them. On 2026-10-25, EP-16 is reframed by one block (#1445): it takes over
from EP-15 the online helps of the screens that the five key screens do not cover, so that their
review does not keep `epic/EP-15` open, and the rule that prevails is that only what
concerns the hardening or the contract stays there — everything else, including the adjustments of the
2026-10-23 validation that do not touch the contract, goes to EP-17; the remaining stability of the end-to-end
paths, for its part, is hardening and comes back to EP-16 (US-0590b).

EP-13 depends only on EP-04: it can start early, but it closes cross-cutting requirements
whose last action comes late, and it finishes last.

After EP-02, **an epic is a vertical slice**: contract, core, API, screen, tests.
Delivering « all the back » then « all the front » would give nothing to look at before the end, and
that is precisely what the mockup on a simulated contract serves to avoid.

## Starting an epic

Five steps, and a stop for validation at the end of each of the first three: that is what
allows the rest to be entrusted to an agent.

1. **Detail the stories**, until each carries acceptance criteria taken from the
   Vérif fields. *Validation.*
2. **Write the design** in the « Conception » section of the epic's file: the tables
   and the migrations, the modules of the core touched, the changes to the contract, the order of
   construction, and the decisions taken with the options set aside. A story says what must
   be true; the design says how the pieces fit together, and without it each lot
   would take its own schema decisions. *Validation*; the epic goes `prêt`.
3. **Establish the lot plan**: for each lot, its scope, the acceptance criteria
   it closes, the lots it depends on and its estimated size. *Validation.*
4. **Open the issues**, in the hierarchy of « Tracking on GitHub »: the epic's issue and
   its table, one per story, one per lot under its story; write back into the file the numbers of the
   issues of the epic and of the stories. The epic goes `en cours`.
5. **Deliver**: at the first lot, create `epic/EP-nn` from `main`, which waits for the epics this
   one depends on to be delivered; deliver the lots; when all the stories are done,
   confirm the definition of done on the epic's branch, then merge it into `main` —
   a person does it, never an agent. The epic goes `livré`.

The first four steps do not require the previous epics to be delivered: an epic
is framed while the one it depends on is being developed. Only the fifth waits for them.

A feature proposal is not a story: it goes through the issue template
« Question or proposal », and becomes a story only when it enters an epic.

## Lots

A lot is the unit of review: **one lot, one issue, one branch, one pull request**. A story
fits in one lot or in several; a lot that closes no acceptance criterion declares itself
a technical lot, is placed under the first story it prepares, and names the others.

| Rule | Why |
|---|---|
| the lot plan aims at 1,000 to 1,500 lines of diff per lot, tests included, of which 800 of production code at most | beyond that, an attentive review drops off |
| generated code is not counted: contract client, dependency locks, extracted fixtures, migrations produced by the tool | a lot that regenerates the client would look big without holding anything to review |
| the pull request sets each criterion closed against the test that carries it | that is what the review checks first |
| a lot is merged on its own, with the chain green | the epic's branch is never half-built |
| a review finding outside the scope of the lot becomes an issue, attached and settled according to « Tracking on GitHub », and is not fixed in the lot | that is what makes a lot grow during its review, and makes the review go round in circles |
| the pull request gives the real size of the lot, measured by `make lot-size`, next to the estimate of its issue; an overrun makes nothing fail | the estimate gets it wrong, and a stop rule would block an epic delivered overnight; the gap is read in the delivery report, and the next lot plan corrects itself from it |
| the local review fixes every finding of its first round; in the following rounds, only the major ones and those a fix introduced, the minor ones becoming issues | that is what makes the review go round in circles, six rounds for one lot during the delivery of EP-03, when each fix gives birth to a new minor one |
| the issue of a lot says the model of its development, `sonnet` or `opus`, and why — authentication, security, data migration, contract, shared interface, or a design that leaves a part open to interpretation; without this field, the delivery agent applies the same list, and it escalates once per lot | the framer knows which part of the design remains to be interpreted, the deliverer discovers it only when reading the lot; a lot marked `sonnet` that escalates says that the rule underestimated, and that is what calibrates it |

This table is the only definition of the target size: the pull request template, the one
of the lots and the agents point to it, and none copies it.

A lot carries the title `[US-nnnn/Ln] …`; `Ln` numbers the lots of the same story, in the order
they are delivered, without reuse. The detached part of a lot cut in two takes the number of the
lot followed by `b`: `[US-nnnn/Lnb]`, branch `lot/US-nnnn/Lnb`, or `[US-nnnnb]` for a story
of a single lot. A story realised by a single lot has only one issue, `[US-nnnn]`,
which is also that of the lot, and its branch `lot/US-nnnn`. The lots live on GitHub and nowhere
else: they are a way of doing the work, not its intention, and the epic's file
does not copy them.

## Tracking on GitHub

This tracking applies from EP-03 on; the issues of EP-01 and EP-02 keep their form, and their
lots `[EP-nn/Ln]` their title. The lots EP-14 takes over from EP-02 are renamed `[EP-14/Ln]`, keeping
their number, and attached to its issue (#599).

The state of an epic is read by opening a single issue, its own, and the hierarchy of the
sub-issues follows the cutting:

```
[EP-nn] l'EPIC — son tableau de suivi
├── [US-nnnn] une US à un seul lot — elle est aussi le lot
├── [US-nnnn] une US à plusieurs lots
│   ├── [US-nnnn/L1] un lot — technique ou non
│   │   └── [EP-nn] <nature> : un constat que ce lot a relevé
│   └── [US-nnnn/L2] …
└── [EP-nn] <nature> : un constat relevé hors de tout lot
```

**The tracking table** is in the body of the epic's issue, never in a comment,
and it is kept up to date at each change of state — lot started, in review, merged, blocked;
story gone `en cours` or `fini`; finding opened or settled. It has two parts:

- **Order of realisation**: one line per story, in the order they are delivered, with its
  issue and its status, the one of the file; under it, one line per lot, in order, with its
  dependencies, its state — `à faire`, `en cours`, `en revue`, `fusionné`, `bloqué : <issue>` —,
  its pull request, and the model that developed it, with the reason for the escalation if there
  was one;
- **Open findings**: each finding that is not closed, the issue it is attached to, and
  its decision.

**The labels.** An issue of an epic — its own issue, its stories, its lots, its findings — carries the
prefix `[EP-nn]`, `[US-nnnn]` or `[US-nnnn/Ln]` in its title **and** the label `EP-nn` of its epic,
always both: the title is read in a list, the label is filtered on; a finding moved to
another epic changes label as it changes title.

**A finding** — of review, of contract, of specification, of tool — raised during an epic
is opened as a sub-issue of the lot that raises it, or of the epic if it comes from no lot, under the
title `[EP-nn] <nature> : …`, where the nature is `contrat`, `spec`, `front`, `back` or `outil`.
It carries a decision from the moment it is opened, written in its body and in the table:

| Decision | What it does with the issue |
|---|---|
| `corrigé par <lot>` | it moves under that lot, and closes at its merge |
| `bloque <lot>` | it stays under the lot that raised it; the blocked lot says so in the table |
| `reporté → EP-nn` | it moves under the issue of that epic; if it does not exist yet, the finding is noted in its file, section « Constats reçus », and will be attached when it is opened |
| `à trancher` | a person must decide; it is the only provisional decision, and the table shows it |

No issue of the epic is without a parent. **An issue closes when what it tracks is
done**: a lot at its merge, a story when the lot that makes it `fini` is merged, the epic at its
delivery.

## Branches

| Branch | Receives | Created from |
|---|---|---|
| `main` | the merge of an epic's branch at its delivery, and the changes to the specification, the contract or the roadmap that serve no epic in progress | — |
| `epic/EP-nn` | the pull requests of the lots of that epic, and the changes to the contract that its design provides for | `main`, at the first lot, once the epics it depends on are delivered |
| `lot/<identifiant du lot>` | the work of one lot, and it alone | the branch of its epic |

An epic in progress has its integration branch from its first lot — between the opening of its
issues and that first lot, it does not have one yet, and that is normal: it may be waiting for an
epic it depends on to be delivered. Several epics can thus move at the same time without
the delivery of one carrying the half-done lots of another. So `main` receives only
delivered epics and reviewed documents: it is never in an intermediate state. After
each merge into `main`, the branches of the epics still in progress take it back in, and that is
when their conflicts are settled, not at delivery.

The chain runs on every pull request, towards an epic's branch as towards `main`, and
none is merged if it fails.

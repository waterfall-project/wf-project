# Revisions: current, marked, reference

## What the glossary says

> **Revision** — Designates a complete snapshot of a project at a given moment: its cost structures and the values of the reference data they use. A revision bears a version name and a description. It is first a draft, then frozen when an authorised user marks it.

> **Marked revision** — Designates a revision frozen by an authorised user. It is no longer modifiable, by any means.

> **Reference revision** — Designates the marked revision that prevails for the reference budget, the risk reserve, the contractual dates and the planned value. This character is an attribute of the revision: it passes to a new revision at each amendment contractualised.

> **Current revision** — Designates the revision in which a quantity is read or calculated: for the indicators of a marked revision, that revision; on the current day, the draft revision when there is one, otherwise the last marked revision. It is the one that the remaining to commit, the current estimate, the base of the project and the portfolio on the current day read.

> **Periodic review** — Designates the operation during which an authorised user updates the planning and the remaining to commit of the draft revision, reviews the risks, imports the new actual costs, then marks the revision. These data allow the indicators of the project to be updated.

## In Waterfall

A project never has more than one draft revision: it is the one that is entered. The following revision is created only on demand — **Open a current revision**, on the screen of the [revisions](../FBS-4.1.md) —, or by the first entry that requires it: an import, the entry of a risk, its occurrence, the merge of a differential. The copy of the last marked revision takes place then, and not at the marking. Marked, it freezes: its grids are read without being entered, and the banner of each screen says so. The indicators of a marked revision are kept at the date of its marking.

The reference revision is a marked revision that one designates: it sets the [reference budget](budget-de-reference.md) and the [planned value](valeur-planifiee.md). The designation is corrected as long as the project has received no actual cost and no revision has been marked since; afterwards, only an amendment contractualised produces a new reference.

Each screen of a revision says in its banner the revision it reads; the link “Open” of the history chooses another one.

## See also

- [Revision management](../FBS-4.1.md);
- [the reference budget](budget-de-reference.md), [the planned value](valeur-planifiee.md), [the amendment and the differential](avenant-et-differentiel.md).

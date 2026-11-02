# Amendment and differential

## What the glossary says

> **Amendment** — Designates a contractual modification of the project during its execution. It is prepared as a differential structure, then merged at its contractualisation, which produces a new reference revision.

> **Differential** — Designates a cost structure that describes a difference from the main structure: tasks and lines added, modified or removed. An amendment is prepared as a differential, then merged.

> **Cost structure** — Designates a tree of tasks bearing estimate lines. Its kind indicates what it describes: the main structure of the project, the differential of an amendment, or the estimate proper to a risk. A revision bears a main structure, and where applicable differentials and risk estimates.

> **Lineage** — Designates the identity that a cost structure, a task or an estimate line keeps from one revision to the next, distinct from the identifier proper to each revision. It is the lineage that the imports match, that a differential designates, and that allows two revisions to be compared.

## In Waterfall

**Prepare an amendment**, on the screen of the [revisions](../FBS-4.1.md), creates a differential of the main structure, under the label given. It is entered in the [planning](../FBS-4.3.md) and in the [estimate](../FBS-4.4.md) as another structure, which the banner names; several may coexist, and each one is merged or abandoned separately. Nothing touches the main structure before the contractualisation.

**Contractualise the amendment**, from the grid of the differential, first presents the report of the merge: the tasks, the lines and the links added, modified and removed, the started tasks that will be completed, and the reasons that refuse it. Confirmed, the merge applies to the current revision — created if need be — and marks it, under the version name asked for; the marked revision becomes the reference. The lines designated take the reference quantities of the differential, hence their budgeted amount; a started task is never removed: its remaining to commit is brought to zero, which completes it.

It is the only path that moves the [reference budget](budget-de-reference.md) once the designation of the reference has become final. The [planned value](valeur-planifiee.md) is then recalculated entirely on the new reference, and the curve of the cumulative budget marks a step at the date of the amendment.

## See also

- [Revision management](../FBS-4.1.md), [the planning](../FBS-4.3.md);
- [the revisions](revisions.md), [the reference budget](budget-de-reference.md), [the provision and the reserve](provision-et-reserve.md).

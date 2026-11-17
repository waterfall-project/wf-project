# Revision management

## What the screen shows

The revisions of the project: each one is a complete snapshot — its cost structures and the values of the reference data they use. A revision is first a draft, then frozen when it is marked; one of the marked revisions is the reference, which sets the budget, the risk reserve and the planned value. This cycle is that of the [periodic review](notions/revisions.md): open a current revision, update the planning and the remaining to commit, review the risks, then mark.

Opening a project does not go through this screen: the page of the project leads to its revision in progress, else to its reference, else to its last marked revision; it leads here only if your session may not read that revision. When the import that has just created the project led here, its **report** is shown above the history, as on the page of the project. You also come here through the **Revisions** function, to read another one.

From top to bottom:

- the **Report** of the import the address names, when there is one;
- the **Revision history**, the one card of the screen: for each one, its version, its state, its date of marking, its description, the link that opens it, and the mark of the reference.

The comparison of two revisions is no longer read here: it is read in the grids of the planning, of the estimate and of the remaining to commit, from the **Compare to the revision read** command of the history. The cost structures of the revision read are chosen in the banner of the grids, not on this screen.

## Its commands

At the top of the screen, the commands of the revision read, each available or naming the condition it lacks; **Open a current revision**, the one filled command, is at the right of the title of the history card:

- **Open a current revision** creates the draft revision, a copy of the last marked revision. Unavailable when the project already has one (“no draft revision”) or when it is closed.
- **Mark the revision** asks for a version name, required, and a description; the marking, handed to the background processing, freezes the revision and keeps its indicators. Unavailable on a revision already marked (“draft revision”) or during a background process.
- **Prepare an amendment** creates, under the label given, a differential of the main structure, which opens in the planning grid; nothing is merged before its contractualisation, from the grid of its differential.
- **Abandon the current revision**, once confirmed: the project goes back to its last marked revision, and the lines of the current revision are deleted. The abandonment is irreversible.
- **Declare a risk** leads, when it is available, to the screen of the [risks](FBS-4.6.md) of the revision, where “Identify a risk” is offered; unavailable, it says what it lacks.

In the sections:

- **Open**, in the history, opens the revision: the screens of the project then read it.
- **Designate as reference**, a command of each marked revision of the history, once confirmed: it sets the reference budget and the planned value; the project that bears its project code passes to the state In progress. Unavailable on a revision that bears no task or no estimate line, and when the reference is no longer corrected — the project has received an actual cost, or a revision has been marked since the last designation.
- **Compare to the revision read**, a command of each marked revision of the history, but the revision read: a menu of the grids of the planning, of the estimate and of the remaining to commit that you may read, which leads to the grid chosen, that revision as the base of the comparison.
- **Apply the rate update**, a command of the current revision at the right of the title: it opens the proposal, category by category, in a window; for the categories retained, once confirmed, the rates of the current revision are replaced by the rates proposed, and its amounts costed again. A proposal, never imposed; offered where the revision is entered in the estimate.

## Its columns and computed values

The history is read as the server renders it, in its order.

## Keyboard gestures

- `Tab` goes through the commands and the links of the history; an unavailable command stays reachable, and its condition is read in its description.
- `F1` opens this help.

## See also

- [The planning](FBS-4.3.md), [the estimate](FBS-4.4.md), [the remaining to commit](FBS-4.5.md);
- the notions: [the revisions](notions/revisions.md), [the reference budget](notions/budget-de-reference.md), [the planned value](notions/valeur-planifiee.md), [the amendment and the differential](notions/avenant-et-differentiel.md).

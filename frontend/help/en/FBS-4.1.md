# Revision management

## What the screen shows

The revisions of the project: each one is a complete snapshot — its cost structures and the values of the reference data they use. A revision is first a draft, then frozen when it is marked; one of the marked revisions is the reference, which sets the budget, the risk reserve and the planned value. This cycle is that of the [periodic review](notions/revisions.md): open a current revision, update the planning and the remaining to commit, review the risks, then mark.

From top to bottom:

- the **Revision history**: for each one, its version, its state, its date of marking, its description, the link that opens it, and the mark of the reference;
- the **Designation of the reference**, on the marked revisions;
- the **Comparison of two revisions** marked;
- the **Cost structures** of the revision read — the main structure, the differentials of amendment, the own estimates of the risks — with their state;
- for the current revision, the **Proposed rate update**, when the reference data has changed since it was costed.

## Its commands

At the top of the screen, the commands of the revision read, each available or naming the condition it lacks:

- **Open a current revision** creates the draft revision, a copy of the last marked revision. Unavailable when the project already has one (“no draft revision”) or when it is closed.
- **Mark the revision** asks for a version name, required, and a description; the marking, handed to the background processing, freezes the revision and keeps its indicators. Unavailable on a revision already marked (“draft revision”) or during a background process.
- **Prepare an amendment** creates, under the label given, a differential of the main structure, which opens in the planning grid; nothing is merged before its contractualisation, from the grid of its differential.
- **Abandon the current revision**, once confirmed: the project goes back to its last marked revision, and the lines of the current revision are deleted. The abandonment is irreversible.
- **Declare a risk** says whether the identification of a risk would succeed, but opens nothing on this screen: the risk is identified on the screen of the [risks](FBS-4.6.md).

In the sections:

- **Open**, in the history, opens the revision: the screens of the project then read it.
- **Designate as reference**, on a marked revision, once confirmed: it sets the reference budget and the planned value; the project that bears its project code passes to the state In progress. Unavailable on a revision that bears no task or no estimate line, and when the reference is no longer corrected — the project has received an actual cost, or a revision has been marked since the last designation.
- **Compare**, between two marked revisions chosen by **From the revision** and **To the revision**: the grid of the nodes compared marks each task and each line added (**+**), removed (**-**) or modified (**M**), and the amount deviations follow. Two marked revisions are needed.
- **Apply the rate update**, for the categories retained, once confirmed: the rates of the current revision are replaced by the rates proposed, and its amounts costed again. A proposal, never imposed; offered where the revision is entered in the estimate.

## Its columns and computed values

The history and the comparison are read as the server renders them: the comparison names what changes of each node, the order is that of the plan, and nothing is sorted there. The amount deviations are calculated by the server, by axis.

## Keyboard gestures

- `Tab` goes through the commands, the links of the history and the fields of the comparison; an unavailable command stays reachable, and its condition is read in its description.
- The grid of the comparison is a single tab stop, which the arrows go through.
- `F1` opens this help.

## See also

- [The planning](FBS-4.3.md), [the estimate](FBS-4.4.md), [the remaining to commit](FBS-4.5.md);
- the notions: [the revisions](notions/revisions.md), [the reference budget](notions/budget-de-reference.md), [the planned value](notions/valeur-planifiee.md), [the amendment and the differential](notions/avenant-et-differentiel.md).

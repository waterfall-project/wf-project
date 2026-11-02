# Project lifecycle

## What the screen shows

Where the project stands in its lifecycle, and what will move it forward. A project has six states, and no other: **Created**, **Pricing**, **In progress**, **Completed**, **Lost** and **Abandoned**. The passages to Pricing and to In progress follow facts: the first revision created leads to Pricing; a reference revision designated and a project code set, in one order or the other, lead to In progress. They are never commanded. The three terminal states are irreversible: the project and all its data — plannings, estimates, remaining to commit, actual costs — pass into read only there, and stay entirely consultable and exportable.

Under the title, the state of the project. Then, from top to bottom:

- the **Next state**, for a project that has not reached In progress: the **State ahead**, the **Trigger** and, one by one, the **Remaining conditions**. A project in progress says so: only its exits remain; a closed project, that no state follows it;
- the **History of states**: each transition, its **Date**, the **Transition**, its author (**By**) and the **Reason** of an exit. Nothing there is modifiable.

## Its commands

At the top of the screen, the three exits, the only transitions that are commanded, each available or naming the condition it lacks:

- **Complete the project**, from In progress (“project in progress”);
- **Declare the project lost**, from Pricing (“project in pricing”);
- **Abandon the project**, from any non-terminal state (“project not closed”).

Each applies after a confirmation that says its final character and what it makes unmodifiable, and that offers a **Motive (optional)**, kept by the transition. When the project bears a current revision, the confirmation asks, under **Fate of the current revision**, to mark it, under a **Version name** and a **Description (optional)**, or to abandon it, with no return; the exit applies only with this choice, in the same operation. **Confirm the exit** applies it; **Cancel** applies nothing.

## Its columns and computed values

The next state, its trigger and its conditions are those the server calculates, read without trying anything. The dates of the history are those of the day each transition took place.

## Keyboard gestures

- `Tab` goes through the exits, then the history; an unavailable exit stays reachable, and its condition is read in its description.
- In the confirmation, which opens in the page, `Tab` goes through the fate of the revision, its fields and the commands; **Cancel** closes it without applying anything.
- `F1` opens this help.

## See also

- [Revision management](FBS-4.1.md), where the first revision is created and the reference designated;
- [the settings of the project](FBS-4.2.md), where the project code is set;
- [the list of the projects](FBS-4.md), filtered by state;
- the notion: [the revisions](notions/revisions.md).

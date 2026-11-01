# Work breakdown

## What the glossary says

> **Work breakdown** — Designates the contractual division of the order into work packages, order items and deliverables. In the absence of entry, the work breakdown comes down to one work package comprising one order item and no deliverable.

> **Work package** — Designates the first level of the work breakdown. A work package contains order items.

> **Order item** — Designates a set of deliverables within a work package of the work breakdown. To be told apart from the position a resource role represents.

> **Deliverable** — Designates an element deliverable to the client, within an order item.

> **Attachment (to the work breakdown)** — Designates the optional link of a task of the main structure to a work package or an order item of the work breakdown, set by the skeleton or by hand, which allows filtering the planning and the estimate by work package or by order item and totalling the estimate by work package. A work package or an order item is borne by only one task at a time. To be told apart from the attachment of a resource role to an organisation node.

> **Planning skeleton** — Designates the planning generated once from the work breakdown: a summary task per work package and per order item, a leaf per deliverable, an end milestone per order item and per work package.

## In Waterfall

The work breakdown takes up the purchase order: it is entered in the [work breakdown of the project](../FBS-4.2.1.md), and its entry is optional. Without it, it is worth one work package and one order item that bear the label of the project, without a deliverable.

In the main structure still empty, **Generate the planning** draws the skeleton from it: a summary task per work package, one per order item under that of its work package, both attached to what they represent; a one-day leaf task per deliverable, in automatic mode; an end milestone per order item, which follows its deliverables, and one per work package, which follows the milestones of its order items. The command is unavailable once the structure bears a task; the planning is then completed by hand.

A task is also attached by hand, from the [planning grid](../FBS-4.3.2.md). The filter **Work package or order item** of the [planning](../FBS-4.3.md), of the [estimate](../FBS-4.4.md) and of the [remaining to commit](../FBS-4.5.md) then keeps the task that bears the work package or the order item, with its subordinates and its ancestors, and the estimate is totalled by work package.

## See also

- [The work breakdown of the project](../FBS-4.2.1.md), [the planning](../FBS-4.3.md);
- [the critical path and the total float](chemin-critique.md).

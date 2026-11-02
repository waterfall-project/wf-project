# Portfolio cost structure

## What the screen shows

The breakdown of the costs of the projects of the perimeter, at the date of calculation. Under the title, the perimeter retained and the date of calculation. Three tables, each in amount and in share:

- **Reference budget by nature**: the aggregated reference budget, broken down by cost type;
- **Remaining to commit by nature**: the aggregated remaining to commit, broken down likewise;
- **Labour by organisation node**.

The actual cost is not broken down by nature: the ERP does not provide it, and the screen says so. A project in pricing, when it is retained, counts for its current estimate weighted by its probability of winning: without the provision lines for the budget, provisions included for the remaining to commit.

## Its commands

**Portfolio perimeter**, above the view:

- **States retained**: the projects in progress, those in pricing, those completed; the last state retained is not released.
- **Calculated on**, the date of calculation, then **Apply**. This view takes no period.
- **Organisation node and its descendants** restricts only the labour lines whose role comes under the node.

The tables are read only: they are neither sorted nor filtered.

## Its columns and computed values

The amount of a nature or of a node is the sum of those of the projects of the perimeter; its share, this amount over the total of the table. Everything is calculated by the server. A nature or a node without a name reads “Unnamed”.

## Keyboard gestures

- `Tab` goes through the filters and the tables; a table wider than the window scrolls with the keyboard.
- `F1` opens this help.

## See also

- [The project portfolio](FBS-2.1.md), [the aggregated workload](FBS-2.2.md);
- the notions: [the reference budget](notions/budget-de-reference.md), [the remaining to commit and the updated estimate](notions/reste-a-engager.md), [the provision and the reserve](notions/provision-et-reserve.md).

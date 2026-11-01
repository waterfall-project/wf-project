# Provision and risk reserve

## What the glossary says

> **Provision** — Designates the amount reserved to cover the consequences of an identified risk, equal to its severity weighted by its probability. It counts in the estimate and in the remaining to commit, never in the reference budget; a risk occurred or dismissed no longer bears one. It comes under a cost type of the kind risk provision; a provision entered, for contingencies for instance, is an ordinary non-labour line.

> **Risk reserve** — Designates the sum of the provision lines of the reference revision. It is not part of the reference budget and moves only with it; it is to it that the remaining provisions and the cost of the risks occurred are compared.

> **Cost at occurrence** — Designates, for an occurred risk, the total of its own estimate at the moment it was declared occurred. It no longer changes, whatever the re-estimations and the completion of the tasks merged; it is the one the risk coverage compares to the reserve.

> **Risk coverage** — Designates the setting side by side, for a project or for the portfolio, of the risk reserve of the reference with the sum of the provisions of the identified risks and of the cost at occurrence of the occurred risks; their difference is the coverage variance.

> **Coverage variance** — Designates the difference, signed, between the risk reserve of the reference and the sum of the provisions of the identified risks and of the cost at occurrence of the occurred risks. Negative, the risks cost more than what had been reserved.

## In Waterfall

A risk is costed in an estimate of its own, whose total is its severity. As long as it is identified, its provision — its severity weighted by its probability — is a line of the main structure, on the task chosen at its declaration, under a category of a cost type of risk provision. The server keeps it up to date: it is not entered.

Declared occurred, the risk loses its provision line and its own estimate joins the main structure, with a zero budgeted amount: it weighs on the remaining to commit, and its cost at occurrence stays counted in the coverage. Dismissed, it loses its provision without adding anything.

The reserve is set by the [reference revision](revisions.md): at each new reference, it keeps the provision that the risks occurred or dismissed before it bore in the previous one, and grows by that of the identified risks the new one bears. The provisions of the risks retained and the coverage are read in [risk management](../FBS-4.6.md) and in the [remaining to commit](../FBS-4.5.md); the zone of a risk, in the matrix the [risk settings](../FBS-3.3.md) set.

## See also

- [Risk management](../FBS-4.6.md), [the provisions of the risks retained](../FBS-4.6.2.md), [the portfolio risks](../FBS-2.5.md);
- [the reference budget](budget-de-reference.md), [the remaining to commit and the updated estimate](reste-a-engager.md).

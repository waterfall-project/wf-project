# Probability of winning

## What the screen shows

The **Probability of winning** of the project, among the settings of the project, on the screen of the [settings of the project](FBS-4.2.md). An offer in pricing is not yet a project: it may never happen. The probability of winning is the weight the project manager gives to their offer, and it is through it that the portfolio and the aggregated workload count a project in pricing for what it is worth, rather than for all or nothing.

It is worth 0 % by default: an offer weighs nothing as long as no one has estimated it. It takes part in no calculation proper to the project — neither the estimate, nor the budget, nor any indicator — and no longer has an effect from the state In progress on, where the project counts for all, nor in the terminal states.

## Its commands

- **Edit the project** opens the form of the settings, where the field **Probability of winning (%)** is entered in percent, between 0 and 100; a value outside these bounds is refused at its field, with the bound.
- The probability is modified as long as the project is in the state Created or Pricing. From the state In progress on, the field is shown frozen, and the condition it lacks is read under it (“project not yet in progress”); if the state changed while the form was open, the refusal says so under the form.

## Its columns and computed values

The probability is shown as the server holds it, in percent. In the [portfolio](FBS-2.1.md), the **Weighted pipeline** is the sum of the current estimates of the projects in pricing, each weighted by its probability; the gross pipeline is not.

## Keyboard gestures

- `Tab` reaches **Edit the project**; in the form, `Tab` goes through the fields and `Enter` saves.
- `Esc` closes the form without saving anything.
- `F1` opens this help.

## See also

- [The settings of the project](FBS-4.2.md), [the project lifecycle](FBS-4.9.md);
- [the project portfolio](FBS-2.1.md) and [the aggregated workload](FBS-2.2.md), which weight the projects in pricing by it.

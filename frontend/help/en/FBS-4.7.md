# Actual costs

## What the screen shows

What the project has spent, as the ERP recorded it. The actual costs are not produced by Waterfall: they come from a periodic extraction of the ERP, which is imported in the [imports and exports](FBS-4.3.4.md). They belong to the project, not to a revision: the revision of the context serves only the banner.

Two perimeters meet, which never quite coincide. The accounting records everything charged to the project; the control follows only what has been budgeted. Every line imported is therefore kept, but a line may be excluded from the **tracked scope**: it stays consultable and enters no indicator. The reconciliation with the budget is made by subproject, which the line finds in its WBS element; a line charged to the project alone joins the set “No subproject”.

From top to bottom:

- the **Totals of the lines retained**: the **Tracked scope**, the **Excluded from the tracked scope** and the **General total**, and the date of the **Last import**;
- the filters, then the grid of the lines, a page at a time, which the server sorts, filters and pages; its footer bears the grand total of the lines retained;
- the **Journal of the imports**: for each one, its date, its author, the period extracted and the number of lines created, updated, unchanged and rejected.

## Its commands

- **Imports and exports**, at the top of the screen, leads to where the actual costs are imported, in the same context.
- **Scope**: **Every line**, **Tracked** or **Excluded**; **Subproject**, a subproject of the project or **Every subproject**; **Period of the documents**, **Documents from** and **Documents up to**, then **Filter**. A period that ends before it starts, or a subproject the project does not have, is refused in the place of the lines, the filters kept to be changed.
- **Columns** chooses the columns shown; **Rows per page**, **Previous lines** and **Next lines** go through the list; **More recent imports** and **Older imports** go through the journal.
- Where the project offers **Exclude cost lines**, the document number of a line is a link that opens it: **Exclude from the tracked scope**, with an optional **Reason for the exclusion**, or **Reinstate in the tracked scope**; **Close the line** closes it again. A terminal project no longer offers it. The exclusion is kept at the following imports, even when an extraction brings the line back.

## Its columns and computed values

Every figure is the server’s: the totals bear on all the lines the filters keep, never on the page alone. The lines are ordered by default from the most recent documents to the oldest. A line is designated by its document and its item, two items of the same document making two lines. Each column the [mapping of the extraction](FBS-3.1.3.md) declares kept is one more column, under the name the file gives it; it is sorted, but enters no calculation.

## Keyboard gestures

- The grid is a single tab stop: the arrows move the active cell, `Home` and `End` along the row, `Ctrl+Home` and `Ctrl+End` to the first and the last row, `Page Up` and `Page Down` by a screen.
- `Enter` on the number of a line opens it.
- On a header, `Enter` or `Space` sorts the grid by the column; `Shift` and the arrows widen or narrow the column.
- On a Mac, `⌘` stands for `Ctrl`, `⌥` for `Alt` and `⇧` for `Shift`.
- `F1` opens this help.

## See also

- [The imports and exports](FBS-4.3.4.md), where the extraction is imported, and [the actual cost extraction mapping](FBS-3.1.3.md);
- [the subprojects](FBS-4.2.3.md), mesh of the reconciliation;
- the notions: [the earned value](notions/valeur-acquise.md), [the indices](notions/indices.md).

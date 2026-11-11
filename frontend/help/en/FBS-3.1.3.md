# Actual cost extraction mapping

## What the screen shows

How Waterfall reads the extraction of the actual costs of the ERP, for the whole installation. The ERP names its columns its own way: for each of the five columns the import reads — **Subproject** (the WBS element), **Document no.**, **Item**, **Document date**, **Amount** —, the list of the labels that designate it in the extraction; then the **Kept columns**, those of the extraction that Waterfall keeps for information and gives back on consulting the lines imported.

The item is optional, the four other columns are required. Above the lists, a bar says the required columns that have no label, or that the mapping is complete. It is empty at installation, and is set before the import of the actual costs, which reads this mapping.

A label is compared to the header of the file, and to the other labels, regardless of case, of accents and of spaces at the ends. The mapping is saved whole, even incomplete, and read back as saved. A label that duplicates another, in the same column, in another column read or among the kept columns, is refused: nothing is saved.

The [import of the actual costs](FBS-4.3.4.md) reads the header of the extraction and compares it with the labels of the mapping:

- as long as the mapping is incomplete, the import is refused, and the command of the import says so in advance: the server answers 409, `actual_cost_mapping_complete`, and names the required columns without a label;
- a required column none of whose labels is in the header of the file makes the file refused, 422 `FILE_FORMAT_UNREADABLE`, which names the labels expected;
- a column of the file that the mapping designates neither as read nor as kept is ignored: the report of the analysis counts it among the ignored columns;
- the mapping read at the analysis is kept with its report: the application runs it as the analysis read it, even if the mapping changes in the meantime.

## Its commands

To whoever cannot modify the cost settings, the screen shows the lists, without a command. To the others, a form:

- **Add a label** to a column read, and the bin of a label to remove it;
- **Declare a kept column**, and the bin to remove it; a column read is not declared kept as well. The contract admits fifty kept columns at most: at fifty, the command is unavailable and says its condition, and a refusal of the server for a list too long is said under the list;
- **Save the mapping** replaces the whole mapping. The server judges the labels: a label refused is refused at its field, which takes the focus, and a duplicate names the label it duplicates. If the mapping has changed since its reading, the refusal offers to read the page again.

The fields wait for the answer of the server during the saving.

## Its columns and computed values

No table: the bar of the required columns without a label is the one the server calculates, at the reading as after a saving.

## Keyboard gestures

- `Tab` goes through the labels, their bins and the commands, in the order of the columns.
- `Enter` in a label saves the mapping.
- `F1` opens this help.

## See also

- [The cost settings](FBS-3.1.md);
- [the actual costs of a project](FBS-4.7.md).

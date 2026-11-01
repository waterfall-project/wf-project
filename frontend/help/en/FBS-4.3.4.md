# Imports and exports

## What the screen shows

A leaf of the [planning](FBS-4.3.md), where the exchanges of files of the project are made: the MS Project planning, the estimate, the remaining to commit and the actual costs are imported there, and the revision read is exported there. The header of the planning leads to it, as do those of the estimate, of the remaining to commit and of the actual costs when their import is offered to you. The screen is shown to whoever reads the planning, or to whomever the project offers an import.

An import is made in two steps. The file is deposited and analysed, without changing anything in the project; its **report** says what the import would do. Then it is applied, once confirmed, in a single operation — or is abandoned, and the project stays as it was. An import of planning, of estimate or of remaining to commit applies to the current revision, whatever the revision read, and creates it if the project has none; an import of actual costs writes in no revision: the actual costs belong to the project.

From top to bottom:

- **Import a file**, a command per kind of file the project offers you;
- the report of the import the address names, when there is one;
- **Imports of the project**: each import open, with its file, its kind, its state and its date, a page at a time;
- **Request an export**, of the revision read.

## Its commands

- **Import an MS Project schedule**, **Import an estimate**, **Import an estimate to complete**, **Import actual costs**: each follows the command the project lists, and says, unavailable, the condition it lacks. It opens the choice of the **File to import**, then **Analyse the file**. A file too large is refused at once; its content, the analysis judges. An extraction of actual costs declares the **Period extracted**, **From** and **To**, if you give it.
- The actual costs are imported only if the mapping of the extraction is complete (“actual-cost extraction mapping complete”): the screen names the required columns without a label, and **Set the mapping of the extraction** leads to the [mapping](FBS-3.1.3.md).
- The analysis is a background process: the tracking of the tasks offers to reload the screen when it has succeeded.
- **Apply the import**, on a report analysed, asks for a confirmation — **Confirm the application** —, then is applied as a background process. Unavailable when the report rejects the whole file (“file accepted by the report”).
- **Abandon the import** applies nothing, and brings the screen back to what it was.
- **Request an export**: the kind of the **File to export** among those the revision offers — the MS Project planning, the estimate, the remaining to commit, the image of the task tree —, with, for the remaining to commit, the **Review date** it bears, and, for the image, the **Level of the tree** where it stops. The file is made on demand, as a background process, and is downloaded from the tracking of the tasks; it is not kept. A terminal project is still exported.

## Its columns and computed values

The report is the server’s. It says the number of lines read, the reasons that ask for an explicit confirmation, the lines rejected with their row, their tab and their reason — or the reasons that reject the whole file, nothing being applied then —, the differences with the existing data, object by object, and the elements the import ignores. For a planning, it also says the tasks the file dates otherwise, what Waterfall recalculates prevailing, and the values kept and signalled. For a remaining to commit, it names the tasks the import completes, because it sets to zero the remaining to commit of all their lines, at the date of the review the file bears. For actual costs, it designates a line by its document and its item — two lines of the file with the same document and the same item are rejected —, and names each column of the extraction neither read nor kept. A report is applied up to the date it says; beyond it, the import expires.

## Keyboard gestures

- `Tab` goes through the commands of import, the fields, the report, its tables and its commands, then the list of the imports and the form of export.
- A table of the report that overflows its box scrolls with the arrows once reached.
- In the confirmation, which opens in the page, **Cancel** goes back to the report without applying anything.
- `F1` opens this help.

## See also

- [The planning](FBS-4.3.md), [the estimate](FBS-4.4.md), [the remaining to commit](FBS-4.5.md), [the actual costs](FBS-4.7.md);
- [the actual cost extraction mapping](FBS-3.1.3.md);
- [the task tree](FBS-4.3.5.md), which is exported as an image.

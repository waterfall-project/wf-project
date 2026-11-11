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

- **Import an MS Project planning**, **Import an estimate**, **Import a remaining to commit**, **Import actual costs**: each follows the command the project lists, and says, unavailable, the condition it lacks. It opens the choice of the **File to import**, then **Analyse the file**. A file too large is refused at once; its content, the analysis judges. An extraction of actual costs declares the **Period extracted**, **From** and **To**, if you give it.
- The actual costs are imported only if the mapping of the extraction is complete (“actual-cost extraction mapping complete”): the screen names the required columns without a label, and **Set the mapping of the extraction** leads to the [mapping](FBS-3.1.3.md).
- The analysis is a background process: the tracking of the tasks offers to reload the screen when it has succeeded.
- **Apply the import**, on a report analysed, asks for a confirmation — **Confirm the application** —, then is applied as a background process. Both commands follow what the import itself lists, and say, when unavailable, the condition they lack: the application, when the report is not awaiting a decision (“import awaiting a decision”) or rejects the whole file (“file accepted by the report”); the abandonment, when the import is applied or being applied (“import not applied”).
- **Abandon the import** applies nothing, and brings the screen back to what it was.
- An import **Refused** was refused at the application — permissions, project state or a file the report rejects —: the file is deleted, and the import is to be restarted. The report and the list of the imports say so.
- **Request an export**: the kind of the **File to export** among those the revision offers — the MS Project planning, the estimate, the remaining to commit, the image of the task tree —, with, for the remaining to commit, the **Review date** it bears, and, for the image, the **Level of the tree** where it stops. The file is made on demand, as a background process, and is downloaded from the tracking of the tasks; it is not kept: the service deletes it at the end of the first complete download, an interrupted download leaves it available, and a file never downloaded disappears after twenty-four hours. The planning is exported as MS Project XML, named `ms-project-` followed by the code of the project: it opens in MS Project with the same dates, and is imported again without losing your tasks. A terminal project is still exported.

## Its columns and computed values

The report is the server’s. It says the number of lines read, the reasons that ask for an explicit confirmation, the lines rejected with their row, their tab and their reason — or the reasons that reject the whole file, nothing being applied then —, the differences with the existing data, object by object, and the elements the import ignores. For an MS Project planning, it also says the tasks the file dates otherwise, what Waterfall recalculates prevailing, and the values kept and signalled (a task started or completed that the file no longer carries is kept), the unit constants of the file and those of the installation when they differ — the durations and the lags then keep their hours, read at the constants of the installation —, and what the import ignores: resources, calendars, progress, costs, custom fields and date constraints. A file that is not an MS Project XML is refused when it is opened. For a remaining to commit, it names the tasks the import completes, because it sets to zero the remaining to commit of all their lines, at the date of the review the file bears. For actual costs, it designates a line by its document and its item — two lines of the file with the same document and the same item are rejected —, and names each column of the extraction neither read nor kept. A report is applied up to the date it says; beyond it, the import expires.

## Keyboard gestures

- `Tab` goes through the commands of import, the fields, the report, its tables and its commands, then the list of the imports and the form of export.
- A table of the report that overflows its box scrolls with the arrows once reached.
- In the confirmation, which opens in the page, **Cancel** goes back to the report without applying anything.
- `F1` opens this help.

## See also

- [The planning](FBS-4.3.md), [the estimate](FBS-4.4.md), [the remaining to commit](FBS-4.5.md), [the actual costs](FBS-4.7.md);
- [the actual cost extraction mapping](FBS-3.1.3.md);
- [the task tree](FBS-4.3.5.md), which is exported as an image.

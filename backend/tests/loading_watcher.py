# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The watcher of the loading of the witness template: how the loader ended, written for the tests.

``witness_template`` starts the loader under this script, which holds the lock of the loading in
its place, runs it, writes how it ended in the directory of the template (``exit``: its status, or
minus the signal that ended it), then ends as it did. A test that waits for the template reads
there whether the loading failed, was ended at its deadline (``SIGALRM``) or was killed, rather
than guessing it by the hour. The standard library alone: started before the loader, it must not
delay it, nor a loader of the tests given a deadline of a second or two.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Sequence

# The file of the directory of the template where the watcher writes how the loader ended.
EXIT = "exit"
# The status of a loader that cannot start, as a shell gives it.
NOT_STARTED = 127


def watch(loader: Sequence[str]) -> NoReturn:
    """Run the loader, write how it ended in the directory of the template, then end as it did.

    ``loader`` ends with that directory. The loader is not handed the lock of the loading, which
    the watcher releases when it ends, once ``exit`` is written. A loader that cannot start is
    said in the log, which the watcher's output is.
    """
    directory = Path(loader[-1])
    try:
        status = subprocess.call(loader, stdin=subprocess.DEVNULL)
    except OSError as error:
        sys.stdout.write(f"the loader did not start: {error}\n")
        sys.stdout.flush()
        status = NOT_STARTED
    (directory / EXIT).write_text(str(status), encoding="utf-8")
    if status < 0:
        if -status != signal.SIGKILL:
            signal.signal(-status, signal.SIG_DFL)
        os.kill(os.getpid(), -status)
    raise SystemExit(status)


if __name__ == "__main__":
    watch(sys.argv[1:])

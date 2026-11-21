# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The bound of the avatars of the witness, an operating parameter the bootstrap has set.

``installation.json``: the witness bounds an avatar at two mebibytes, where an installation is
shipped at 512 KB (§4.4.1, #3965). The bootstrap writes the bound of its settings; this slice sets
the witness's over it, the language and the time zone staying the bootstrap's. A database the
bootstrap has not installed has no bound to set: the slice writes nothing there.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import Installation
from waterfall.platform.installation import set_avatar_max_bytes

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


def load(session: Session, witness: Witness) -> bool:
    """Set the bound of the witness unless the installation holds it; tell whether it wrote."""
    declared = witness.read("installation.json", Installation)
    return set_avatar_max_bytes(session, declared.avatar_max_bytes)

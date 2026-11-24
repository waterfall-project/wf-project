# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reprise of the codes: the WBS element of a line of cost compared whole (US-3270, #3966).

A migration of data, after the schema that frees the codes (0046), as the conception of EP-33 says
it ("Tables et migrations") and the decision of the author of 2026-11-21:

- the lines of cost that bear a code and no subproject — imported under a code of subproject no
  subproject bore, which waited for its creation — are deleted: the rule of the specification 1.0.7
  would have rejected them, and the reimport of their extraction gives them back once the
  subproject is declared. Their number is logged by project (``cost_lines_waiting_deleted``), and
  their total, even null (``codes_prefixed``);
- the code of each subproject of a project that has a code becomes the code of the project, a
  slash, then its former code — the WBS element the ERP gives its lines —, its counter advanced, so
  that a form read before cannot write the former code back (412); and the code of each line imputed
  to a subproject, the code it was imported under, becomes so as well: the line stays imputed to its
  subproject, and the reimport of its extraction imputes it to the same. A code of subproject was
  31 characters at most and that of a project 50: the code of a subproject prefixed is 82 at most,
  within the bound of 0046. A line imputed was imported under the code of its subproject, 31 at
  most, then kept it through a recoding; one whose code, written around the service, would pass
  100 characters once prefixed stops the reprise before any write, naming its projects
  (``RuntimeError``), as does a subproject whose code, free of 0046 on, would (#4891): no code is
  cut. The unique code of a
  subproject in its project holds: every code of the project takes the same prefix, and no former
  code bore a slash. A project without a code — it never imported a line — keeps the codes of its
  subprojects;
- the reports of the imports lose the reason ``unknown_subproject``, which the contract no longer
  has: a report analysed before, applied within its twenty-four hours, reads its lines again under
  the new rule anyway.

The key of the cache of the indicators (#3629): the deletion makes the sum of the counters of the
lines of a project fall back, which the key reads (``costs_stamp``); it reads their number too,
which falls below any number the project had since its last import — lines are added by the imports
alone, whose number never falls —, so the key of a project that lost lines is one it never had, and
no entry kept before is served after. The codes do not enter the indicators.

The descent strips the prefix of the codes that bear the code of their project and a slash, the
counters of the subprojects advanced; it does not give back the lines deleted, which are lost, nor
the reason of the reports. It fails while two codes of a project would be one once stripped — a
code entered since, free, equal to a former one —; a code entered since without the prefix stays,
and the descent of 0046 then fails on what it refuses.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = get_logger(__name__)

# The bound of the code of a subproject and of a line of cost (0046).
CODE_LENGTH = 100
# The projects whose line imputed, or whose subproject, would bear a code beyond the bound once
# prefixed: a subproject written since 0046 frees its code may bear up to 100 characters (#4891).
TOO_LONG = sa.text(
    "SELECT DISTINCT c.project_id FROM cost_line AS c JOIN project AS p ON p.id = c.project_id "
    "WHERE c.subproject_id IS NOT NULL "
    "AND char_length(p.code) + 1 + char_length(c.subproject_code) > :longest "
    "UNION "
    "SELECT s.project_id FROM subproject AS s JOIN project AS p ON p.id = s.project_id "
    "WHERE char_length(p.code) + 1 + char_length(s.code) > :longest "
    "ORDER BY project_id"
).bindparams(longest=CODE_LENGTH)
# The lines that wait for a subproject, by project, with the code of the project.
WAITING = sa.text(
    "SELECT c.project_id, p.code, count(*) FROM cost_line AS c JOIN project AS p "
    "ON p.id = c.project_id WHERE c.subproject_id IS NULL AND c.subproject_code IS NOT NULL "
    "GROUP BY c.project_id, p.code ORDER BY c.project_id"
)
DELETE_WAITING = sa.text(
    "DELETE FROM cost_line WHERE subproject_id IS NULL AND subproject_code IS NOT NULL"
)
PREFIX_SUBPROJECTS = sa.text(
    "UPDATE subproject AS s SET code = p.code || '/' || s.code, "
    "lock_version = s.lock_version + 1 FROM project AS p "
    "WHERE p.id = s.project_id AND p.code IS NOT NULL"
)
PREFIX_LINES = sa.text(
    "UPDATE cost_line AS c SET subproject_code = p.code || '/' || c.subproject_code "
    "FROM project AS p WHERE p.id = c.project_id AND p.code IS NOT NULL "
    "AND c.subproject_id IS NOT NULL"
)
FORGET_REASON = sa.text(
    "UPDATE import_report SET report = jsonb_set(report, '{requires_confirmation_reasons}', "
    "(report -> 'requires_confirmation_reasons') - 'unknown_subproject') "
    "WHERE report -> 'requires_confirmation_reasons' ? 'unknown_subproject'"
)
# A code that bears the prefix of its project: the code of the project, a slash, then something.
STRIP_SUBPROJECTS = sa.text(
    "UPDATE subproject AS s SET code = substr(s.code, char_length(p.code) + 2), "
    "lock_version = s.lock_version + 1 FROM project AS p WHERE p.id = s.project_id "
    "AND starts_with(s.code, p.code || '/') AND char_length(s.code) > char_length(p.code) + 1"
)
STRIP_LINES = sa.text(
    "UPDATE cost_line AS c "
    "SET subproject_code = substr(c.subproject_code, char_length(p.code) + 2) FROM project AS p "
    "WHERE p.id = c.project_id AND c.subproject_id IS NOT NULL "
    "AND starts_with(c.subproject_code, p.code || '/') "
    "AND char_length(c.subproject_code) > char_length(p.code) + 1"
)


def upgrade() -> None:
    """Delete the lines that wait for a subproject, logged; prefix the codes; forget the reason."""
    connection = op.get_bind()
    too_long = [str(project_id) for project_id in connection.scalars(TOO_LONG)]
    if too_long:
        message = (
            f"a subproject or a line imputed would bear a code beyond {CODE_LENGTH} characters "
            f"once prefixed, in the projects {too_long}: shorten its code before the reprise"
        )
        raise RuntimeError(message)
    waiting = connection.execute(WAITING).all()
    for project_id, code, deleted in waiting:
        logger.info(
            "cost_lines_waiting_deleted",
            project_id=str(project_id),
            project_code=code,
            count=deleted,
        )
    connection.execute(DELETE_WAITING)
    connection.execute(PREFIX_SUBPROJECTS)
    connection.execute(PREFIX_LINES)
    connection.execute(FORGET_REASON)
    logger.info(
        "codes_prefixed",
        projects_with_lines_deleted=len(waiting),
        cost_lines_deleted=sum(deleted for _, _, deleted in waiting),
    )


def downgrade() -> None:
    """Strip the prefix of the codes; the lines deleted and the reason forgotten are lost."""
    connection = op.get_bind()
    connection.execute(STRIP_LINES)
    connection.execute(STRIP_SUBPROJECTS)

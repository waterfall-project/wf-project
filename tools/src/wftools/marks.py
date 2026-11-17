# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The names of the marks of Pytest the coverage of the requirements reads (US-2440).

Kept apart, with no import of Pytest, so that the report (``wftools.coverage``) and the plugin
(``wftools.unexecuted``) share the names without the report loading the plugin, nor Pytest.
"""

MARK = "unexecuted"
"""The mark of a test that may skip: ``@pytest.mark.unexecuted("<reason>")``."""

STORY = "story"
"""The mark of a test that carries a criterion of a story: ``@pytest.mark.story("US-nnnn")``."""

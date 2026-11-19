# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The permissions that two modules of the core judge alike, defined once below both (#3341).

The access roles evaluate an action on a project with it, and the projects decide with it which a
reader sees: the layers forbid the projects to import the access roles, and a value changed on one
side alone would have the list of the projects keep what the evaluation refuses, or the reverse.
"""

# The permission that opens to consultation the projects its holder does not contribute to
# (WF-ADM-0110, WF-PRJ-0060).
ALL_PROJECTS_READ = "all_projects_read"

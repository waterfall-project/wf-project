# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The ordered registry of the revisions: what the later epics add to them (EP-04).

The copy of a revision, the questions of its tasks and lines, its indicators and its closing are
each a ``Registry``, which the interface offers to fill. The class lives in the platform since
EP-06 (``waterfall.platform.registry``), every module of the core holding registries of its own; it
is named here too, where the files of the later epics find it (``core/revisions/registry.py``), and
the interface of the revisions takes it from here.
"""

from waterfall.platform.registry import Registry

__all__ = ["Registry"]

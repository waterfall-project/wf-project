# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The measure of the core, in process: what a read and a write of the grids cost (US-2210).

An instrument of the repository, not a part of the service: it lives beside ``src/waterfall``,
is typed and linted like it, and is neither in the image of the back nor in its coverage. It calls
the core as the API does, without HTTP and without Keycloak, on the database of the service
platform of the slot, the witness loaded (``make service-up``, ``make service-witness``), and
rolls back everything it writes, so that a measure never changes the next. It never fails on a
duration: a figure is a report, and the chain does not run it (WF-QUA-0060).
"""

# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The service of the restoration, ``waterfall-restore`` (WF-ADM-0160, #953).

A process of the image ``waterfall``, started with the platform and always running, which runs the
restorations the API deposits in a stream of their own, and nothing else. It is the only process of
the platform that holds the owners of both databases, the client of the bootstrap of Keycloak, which
clears its caches, and the folder of the requests that the service ``keycloak-realm`` answers. It
applies the migrations: it sits above the API and the worker, beside the bootstrap, and nothing
imports it (``[tool.importlinter]``).
"""

# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The loader of the witness: ``waterfall-api load-witness`` (WF-QUA-0040; EP-05, "Le chargeur").

The witness is the universe the examples of the contract describe (``fixtures/api/``), which the
fake back serves: loaded on a platform, the service answers what those examples say, and its
answers are compared with them. The loader reads them in the form of the contract and writes them
through the interfaces of the modules, with the identifiers of the witness, as the platform and
at the instant of the loading. It sits above every layer, as the bootstrap, and nothing imports
it; the production platform does not offer it: a real installation holds no witness.

``main`` runs the command; ``loader`` orders the slices, one per object, each in a file of its
own that the story of the object fills; ``description`` reads the witness.
"""

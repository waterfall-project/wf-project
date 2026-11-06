# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The description of the witness, read in the form of the contract (WF-QUA-0040).

Each file is an example of the contract — a summary, and the value an operation answers — that
``make mock-data`` keeps: its value is validated by the model of the contract, and a file that
strays from it stops the loading, nothing written. Nothing of it is copied into the package.
"""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from pathlib import Path

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class Witness:
    """The witness being loaded: where its description is, and the act that writes it.

    The platform its author, the instant of the loading its date (WF-DAT-0070): neither the dates
    nor the authors the examples say are kept (EP-05, "Ce que le cadrage décide").
    """

    directory: Path
    act: Act

    def read[Model: BaseModel](self, name: str, model: type[Model]) -> Model:
        """Read the example ``name`` of the directory, its value validated by ``model``.

        ``name`` is the path of the file under the directory (``volume/cost_categories.json``);
        a value that the model refuses raises its ``ValidationError``.
        """
        document = json.loads((self.directory / name).read_text(encoding="utf-8"))
        return model.model_validate(document["value"])

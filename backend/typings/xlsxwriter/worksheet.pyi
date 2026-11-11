# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
# The worksheet of XlsxWriter, as the writer of the estimate uses it.

from collections.abc import Iterable
from decimal import Decimal
from io import BytesIO
from typing import overload

from xlsxwriter.format import Format

class Worksheet:
    @overload
    def write(self, row: int, col: int, data: object, cell_format: Format | None = None) -> int: ...
    @overload
    def write(self, cell: str, data: object, cell_format: Format | None = None) -> int: ...
    @overload
    def write_string(
        self, row: int, col: int, string: str, cell_format: Format | None = None
    ) -> int: ...
    @overload
    def write_string(self, cell: str, string: str, cell_format: Format | None = None) -> int: ...
    @overload
    def write_number(
        self, row: int, col: int, number: float | Decimal, cell_format: Format | None = None
    ) -> int: ...
    @overload
    def write_number(
        self, cell: str, number: float | Decimal, cell_format: Format | None = None
    ) -> int: ...
    @overload
    def write_formula(
        self,
        row: int,
        col: int,
        formula: str,
        cell_format: Format | None = None,
        value: object = 0,
    ) -> int: ...
    @overload
    def write_formula(
        self, cell: str, formula: str, cell_format: Format | None = None, value: object = 0
    ) -> int: ...
    def write_row(
        self, row: int, col: int, data: Iterable[object], cell_format: Format | None = None
    ) -> int: ...
    @overload
    def write_comment(
        self, row: int, col: int, comment: str, options: dict[str, object] | None = None
    ) -> int: ...
    @overload
    def write_comment(
        self, cell: str, comment: str, options: dict[str, object] | None = None
    ) -> int: ...
    @overload
    def add_table(
        self,
        first_row: int,
        first_col: int,
        last_row: int,
        last_col: int,
        options: dict[str, object] | None = None,
    ) -> object: ...
    @overload
    def add_table(self, cell_range: str, options: dict[str, object] | None = None) -> object: ...
    @overload
    def data_validation(
        self,
        first_row: int,
        first_col: int,
        last_row: int,
        last_col: int,
        options: dict[str, object] | None = None,
    ) -> int: ...
    @overload
    def data_validation(self, cell_range: str, options: dict[str, object] | None = None) -> int: ...
    @overload
    def insert_image(
        self,
        row: int,
        col: int,
        source: str | BytesIO,
        options: dict[str, object] | None = None,
    ) -> int: ...
    @overload
    def insert_image(
        self, cell: str, source: str | BytesIO, options: dict[str, object] | None = None
    ) -> int: ...
    def set_column(
        self,
        first_col: int,
        last_col: int,
        width: float | None = None,
        cell_format: Format | None = None,
        options: dict[str, object] | None = None,
    ) -> int: ...
    def set_row(
        self, row: int, height: float | None = None, cell_format: Format | None = None
    ) -> int: ...
    def merge_range(
        self,
        first_row: int,
        first_col: int,
        last_row: int,
        last_col: int,
        data: object,
        cell_format: Format | None = None,
    ) -> int: ...
    def set_landscape(self) -> None: ...
    def freeze_panes(self, row: int, col: int) -> None: ...
    def print_area(self, first_row: int, first_col: int, last_row: int, last_col: int) -> int: ...
    def fit_to_pages(self, width: int, height: int) -> None: ...
    def protect(self, password: str = "", options: dict[str, object] | None = None) -> None: ...
    def set_footer(self, footer: str = "") -> None: ...
    def activate(self) -> None: ...

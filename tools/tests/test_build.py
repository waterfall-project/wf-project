# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projection of the specification refuses a Word document still under review.

Pandoc accepts every tracked change silently: a strict build must count every kind of
revision mark Word writes, and must leave the previous projection untouched when it finds
one, so that the chain never publishes as adopted what the author has not accepted yet.

These tests cover no requirement of the document: they test the tool of the chain, not the
specification it projects, so they cite none.
"""

import sys
import zipfile
from pathlib import Path

import build
import pytest

PARAGRAPH = "<w:p><w:r><w:t>Texte</w:t></w:r></w:p>"


def write_docx(path: Path, body: str) -> Path:
    """Write a minimal Word archive whose document.xml holds ``body``."""
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)
    return path


def cell_revision(mark: str) -> str:
    """Return a one-cell table whose cell carries the revision mark ``mark``."""
    return (
        "<w:tbl><w:tr><w:tc><w:tcPr>"
        f'<w:{mark} w:id="1" w:author="Author" w:date="2026-10-04T10:00:00Z"/>'
        f"</w:tcPr>{PARAGRAPH}</w:tc></w:tr></w:tbl>"
    )


@pytest.mark.parametrize("mark", ["cellIns", "cellDel", "cellMerge"])
def test_a_cell_revision_is_a_pending_tracked_change(tmp_path: Path, mark: str) -> None:
    docx = write_docx(tmp_path / "spec.docx", cell_revision(mark))
    (message,) = build.pending_review_marks(docx)
    assert message.startswith("1 tracked change(s) pending")


def test_an_accepted_document_has_no_pending_mark(tmp_path: Path) -> None:
    table = f"<w:tbl><w:tr><w:tc>{PARAGRAPH}</w:tc></w:tr></w:tbl>"
    docx = write_docx(tmp_path / "spec.docx", table)
    assert build.pending_review_marks(docx) == []


def test_a_strict_build_leaves_the_projection_untouched_on_pending_marks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    docx = write_docx(tmp_path / "spec.docx", cell_revision("cellDel"))
    output = tmp_path / "spec.md"
    output.write_text("the previous projection\n", encoding="utf-8")
    before = output.stat().st_mtime_ns
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build.py",
            "--strict",
            "--docx",
            str(docx),
            "--drawio",
            str(tmp_path / "missing.drawio"),
            "--config",
            str(tmp_path / "missing.toml"),
            "--output",
            str(output),
        ],
    )

    assert build.main() == 1

    assert output.read_text(encoding="utf-8") == "the previous projection\n"
    assert output.stat().st_mtime_ns == before
    captured = capsys.readouterr()
    assert "1 tracked change(s) pending" in captured.err
    assert "left untouched" in captured.err

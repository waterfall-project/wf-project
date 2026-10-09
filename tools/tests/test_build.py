# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projection of the specification refuses a Word document still under review.

Pandoc accepts every tracked change silently: a strict build must count every kind of
revision mark Word writes, in every part of the archive a reviewer may change, and must
leave the previous projection untouched when it finds one, so that the chain never
publishes as adopted what the author has not accepted yet. Nor does a strict build write a
projection its conversion warns about.

These tests cover no requirement of the document: they test the tool of the chain, not the
specification it projects, so they cite none.
"""

import subprocess
import sys
import zipfile
from pathlib import Path

import build
import pytest

PARAGRAPH = "<w:p><w:r><w:t>Texte</w:t></w:r></w:p>"
NAMESPACE = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
INSERTION = (
    '<w:ins w:id="2" w:author="Author" w:date="2026-10-04T10:00:00Z">'
    "<w:r><w:t>ajout</w:t></w:r></w:ins>"
)


def write_docx(path: Path, body: str, parts: dict[str, str] | None = None) -> Path:
    """Write a minimal Word archive whose document.xml holds ``body``, with other parts."""
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {NAMESPACE}><w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document)
        for name, xml in (parts or {}).items():
            archive.writestr(name, xml)
    return path


# A part of the archive other than the body, by name, with the root its paragraph goes in.
OTHER_PARTS = {
    "word/footnotes.xml": (
        f'<w:footnotes {NAMESPACE}><w:footnote w:id="1">{{}}</w:footnote></w:footnotes>'
    ),
    "word/endnotes.xml": (
        f'<w:endnotes {NAMESPACE}><w:endnote w:id="1">{{}}</w:endnote></w:endnotes>'
    ),
    "word/header1.xml": f"<w:hdr {NAMESPACE}>{{}}</w:hdr>",
    "word/footer2.xml": f"<w:ftr {NAMESPACE}>{{}}</w:ftr>",
}


def other_part(name: str, content: str) -> dict[str, str]:
    """Return the part ``name`` of OTHER_PARTS holding one paragraph of ``content``."""
    return {name: OTHER_PARTS[name].format(f"<w:p>{content}</w:p>")}


def requirement_table(identifier: str) -> str:
    """Return a requirement table as pandoc renders it, with this identifier."""
    rows = [f"| ID | {identifier} |", "|---|---|"]
    rows += [f"| {label} | valeur |" for label in list(build.REQUIREMENT_FIELDS)[1:]]
    return "\n".join(rows)


# Two requirements of section 2 that carry the same identifier: the conversion warns.
DUPLICATED = "\n\n".join(
    ["# Introduction", "# Exigences", *[requirement_table("WF-QUA-0010-A")] * 2, ""]
)


def extract_duplicated(_docx: Path, _media_folder: Path) -> str:
    """Stand for pandoc: return the Markdown of DUPLICATED, whatever the document."""
    return DUPLICATED


def build_arguments(tmp_path: Path, docx: Path, output: Path, *, strict: bool) -> list[str]:
    """Return the command line of a build of ``docx`` into ``output``, without figures."""
    return [
        "build.py",
        *(["--strict"] if strict else []),
        "--docx",
        str(docx),
        "--drawio",
        str(tmp_path / "missing.drawio"),
        "--config",
        str(tmp_path / "missing.toml"),
        "--output",
        str(output),
    ]


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
    monkeypatch.setattr(sys, "argv", build_arguments(tmp_path, docx, output, strict=True))

    assert build.main() == 1

    assert output.read_text(encoding="utf-8") == "the previous projection\n"
    assert output.stat().st_mtime_ns == before
    captured = capsys.readouterr()
    assert "1 tracked change(s) pending" in captured.err
    assert "left untouched" in captured.err


@pytest.mark.parametrize("name", sorted(OTHER_PARTS))
def test_a_tracked_change_outside_the_body_is_pending_and_its_part_named(
    tmp_path: Path, name: str
) -> None:
    docx = write_docx(tmp_path / "spec.docx", PARAGRAPH, other_part(name, INSERTION))
    (message,) = build.pending_review_marks(docx)
    assert message.startswith(f"1 tracked change(s) pending in the Word document ({name}: 1)")


def test_tracked_changes_are_summed_over_the_parts_that_hold_them(tmp_path: Path) -> None:
    body = f"<w:p>{INSERTION}{INSERTION}</w:p>"
    docx = write_docx(tmp_path / "spec.docx", body, other_part("word/footnotes.xml", INSERTION))
    (message,) = build.pending_review_marks(docx)
    assert message.startswith(
        "3 tracked change(s) pending in the Word document "
        "(word/document.xml: 2, word/footnotes.xml: 1)"
    )


def test_a_comment_anchored_in_a_footnote_is_an_open_thread(tmp_path: Path) -> None:
    anchored = (
        '<w:commentRangeStart w:id="0"/><w:r><w:t>note</w:t></w:r><w:commentRangeEnd w:id="0"/>'
    )
    comments = (
        f'<w:comments {NAMESPACE}><w:comment w:id="0" w:author="A">'
        f"{PARAGRAPH}</w:comment></w:comments>"
    )
    parts = other_part("word/footnotes.xml", anchored) | {"word/comments.xml": comments}
    docx = write_docx(tmp_path / "spec.docx", PARAGRAPH, parts)
    (message,) = build.pending_review_marks(docx)
    assert message.startswith("1 open comment thread(s) in the Word document")


def test_a_strict_build_leaves_the_projection_untouched_on_a_conversion_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    docx = write_docx(tmp_path / "spec.docx", PARAGRAPH)
    output = tmp_path / "spec.md"
    output.write_text("the previous projection\n", encoding="utf-8")
    before = output.stat().st_mtime_ns
    monkeypatch.setattr(build, "extract_docx", extract_duplicated)
    monkeypatch.setattr(sys, "argv", build_arguments(tmp_path, docx, output, strict=True))

    assert build.main() == 1

    assert output.read_text(encoding="utf-8") == "the previous projection\n"
    assert output.stat().st_mtime_ns == before
    captured = capsys.readouterr()
    assert "identifier WF-QUA-0010-A carried by 2 requirements" in captured.err
    assert "left untouched: the conversion emitted warnings" in captured.err


def test_a_build_that_is_not_strict_writes_the_projection_despite_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    docx = write_docx(tmp_path / "spec.docx", PARAGRAPH)
    output = tmp_path / "spec.md"
    output.write_text("the previous projection\n", encoding="utf-8")
    monkeypatch.setattr(build, "extract_docx", extract_duplicated)
    monkeypatch.setattr(sys, "argv", build_arguments(tmp_path, docx, output, strict=False))

    assert build.main() == 0

    projection = output.read_text(encoding="utf-8")
    assert "nombre_exigences: 2" in projection
    assert projection.count('id: "WF-QUA-0010-A"') == 2
    captured = capsys.readouterr()
    assert "2 requirements" in captured.out
    assert "identifier WF-QUA-0010-A carried by 2 requirements" in captured.err


def figure_without_entry(image: Path) -> str:
    """Return a figure as pandoc renders it, whose caption tools/figures.toml does not know."""
    return f'# Introduction\n\n<img src="{image}" />\n\nFigure 1 — Une figure sans source\n'


@pytest.mark.parametrize("strict", [True, False], ids=["strict", "lenient"])
def test_the_images_of_a_refused_projection_are_not_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, strict: bool
) -> None:
    image = tmp_path / "source" / "figure.png"
    image.parent.mkdir()
    image.write_bytes(b"png")
    docx = write_docx(tmp_path / "spec.docx", PARAGRAPH)
    output = tmp_path / "spec.md"
    output.write_text("the previous projection\n", encoding="utf-8")
    monkeypatch.setattr(build, "ROOT", tmp_path)

    def extract(_docx: Path, _media_folder: Path) -> str:
        return figure_without_entry(image)

    monkeypatch.setattr(build, "extract_docx", extract)
    monkeypatch.setattr(sys, "argv", build_arguments(tmp_path, docx, output, strict=strict))

    assert build.main() == (1 if strict else 0)

    if strict:
        assert not (tmp_path / "images").exists()
        assert output.read_text(encoding="utf-8") == "the previous projection\n"
    else:
        assert (tmp_path / "images" / "figure.png").read_bytes() == b"png"
        assert "![Figure 1 — Une figure sans source](images/figure.png)" in output.read_text(
            encoding="utf-8"
        )


def test_the_mermaid_summary_counts_the_diagrams_that_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = ["```mermaid", "graph LR; A-->B", "```", "", "```mermaid", "graph LR; C", "```"]
    calls: list[list[str]] = []

    def mmdc(command: list[str], **_options: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        failed = len(calls) == 1
        return subprocess.CompletedProcess(command, int(failed), "", "Parse error" * failed)

    def which(_name: str) -> str:
        return "/usr/bin/mmdc"

    monkeypatch.setattr(build.shutil, "which", which)
    monkeypatch.setattr(build.subprocess, "run", mmdc)
    notes = build.BuildNotes()

    build.validate_mermaid(lines, notes)

    assert len(calls) == 2
    assert notes.warnings == ["Mermaid diagram no. 1 does not compile: Parse error"]
    assert notes.traces == ["1 of 2 Mermaid diagram(s) validated by mmdc, 1 failed"]

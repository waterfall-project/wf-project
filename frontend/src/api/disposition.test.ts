// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { attachmentName } from "./disposition";

describe("the name of an attached file", () => {
  it("is the file name the attachment of the contract gives", () => {
    expect(attachmentName(example("task_result_disposition") as string)).toBe(
      "devis-poste-de-commande.xlsx",
    );
  });

  it("is the name in UTF-8 when the header gives one, its ASCII equivalent otherwise", () => {
    expect(
      attachmentName(
        "attachment; filename=\"devis-etudes.xlsx\"; filename*=UTF-8''devis-%C3%A9tudes.xlsx",
      ),
    ).toBe("devis-études.xlsx");
    // A charset the front does not read, or a value badly encoded: the ASCII name.
    expect(
      attachmentName("attachment; filename*=iso-8859-1''devis-%E9tudes.xlsx; filename=devis.xlsx"),
    ).toBe("devis.xlsx");
    expect(attachmentName("attachment; filename*=UTF-8''%E9; filename=devis.xlsx")).toBe(
      "devis.xlsx",
    );
  });

  it("reads a quoted name with its escaped characters, and a token", () => {
    expect(attachmentName('Attachment; filename="plan \\"A\\".xml"')).toBe('plan "A".xml');
    expect(attachmentName("attachment;filename=arbre.png")).toBe("arbre.png");
  });

  it("keeps the base name alone, so that nothing saves the file elsewhere", () => {
    expect(attachmentName('attachment; filename="../../etc/devis.xlsx"')).toBe("devis.xlsx");
    expect(attachmentName('attachment; filename="C:\\\\temp\\\\devis.xlsx"')).toBe("devis.xlsx");
  });

  it("is none for a header that is no attachment, or that names no file", () => {
    expect(attachmentName('inline; filename="devis.xlsx"')).toBeUndefined();
    expect(attachmentName("attachment")).toBeUndefined();
    expect(attachmentName('attachment; filename=""')).toBeUndefined();
    expect(attachmentName('attachment; filename="../"')).toBeUndefined();
  });
});

// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a journey reads a download: through the stream Playwright gives, the only form the browser of
 * the paths allows. The chain plays the browser in the work image of the paths (US-1900), where
 * the file it saved has no path the runner can read, so `download.path()` is refused.
 */
import { type Download, expect } from "@playwright/test";

/** The bytes of a download, read through its stream. */
export async function downloaded(download: Download): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of await download.createReadStream()) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks);
}

/** The width and the height of the PNG image a download saved, its signature checked. */
export async function pngSize(download: Download): Promise<[number, number]> {
  const image = await downloaded(download);
  expect(image.subarray(0, 8).toString("hex")).toBe("89504e470d0a1a0a");
  return [image.readUInt32BE(16), image.readUInt32BE(20)];
}

import { test } from "node:test";
import { strict as assert } from "node:assert";
import { buildObsidianOutputPath } from "./obsidianOutput.js";

test("builds the SignalForge Daily report folder inside an Obsidian vault", () => {
  assert.equal(buildObsidianOutputPath("D:\\Notes"), "D:\\Notes\\SignalForge Daily");
  assert.equal(buildObsidianOutputPath("D:\\Notes\\"), "D:\\Notes\\SignalForge Daily");
  assert.equal(buildObsidianOutputPath("/Users/me/Vault/"), "/Users/me/Vault/SignalForge Daily");
});

test("keeps empty vault paths empty", () => {
  assert.equal(buildObsidianOutputPath(""), "");
  assert.equal(buildObsidianOutputPath("   "), "");
});

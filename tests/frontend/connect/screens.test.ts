import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const route = readFileSync(new URL("../../../frontend/src/app/tools/[step]/page.tsx", import.meta.url), "utf8");
const workspace = readFileSync(new URL("../../../frontend/src/features/simulation/FeatureWorkspace.tsx", import.meta.url), "utf8");
test("every linked healthcare screen has a generated route and unsupported screens return not found", () => {
  for (const step of ["prices", "visit", "scan", "match", "payment", "benefits"]) assert.ok(route.includes(`"${step}"`));
  assert.match(route, /notFound\(\)/);
  assert.match(route, /initialStep=\{step/);
});
test("public feature screens never imply access to the patient's private case", () => {
  assert.match(workspace, /not your private case record/);
  assert.match(workspace, /demo data/);
  assert.match(workspace, /Do not upload sensitive documents/);
});

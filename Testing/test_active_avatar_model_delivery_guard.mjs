import assert from "node:assert/strict";
import test from "node:test";

import {
  isCurrentAvatarModelLoad,
  shouldRevokeKiraRuntimeModel,
} from "../Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/active_avatar_model_guard.js";

test("a cleared or invalid Kira selection revokes the displayed runtime model", () => {
  assert.equal(shouldRevokeKiraRuntimeModel({ active_candidate: "kira" }, "Kira", ""), true);
  assert.equal(shouldRevokeKiraRuntimeModel({
    active_candidate: "kira",
    active_body_selection: { enforced: true, valid: false },
  }, "Kira", "/Avatar/review.glb"), true);
  assert.equal(shouldRevokeKiraRuntimeModel({
    active_candidate: "kira",
    active_body_selection: { enforced: true, valid: true },
  }, "Kira", "/Avatar/review.glb"), false);
});

test("Kira-only revocation does not block another avatar asset", () => {
  assert.equal(shouldRevokeKiraRuntimeModel({
    active_candidate: "elsa",
    active_body_selection: { enforced: true, valid: false },
  }, "Elsa", "/Avatar/elsa.glb"), false);
});

test("only the newest still-selected GLTF request may attach its scene", () => {
  const current = {
    requestGeneration: 8,
    currentGeneration: 8,
    requestedUrl: "/Avatar/kira-r6.glb",
    currentUrl: "/Avatar/kira-r6.glb",
    markerPresent: true,
  };
  assert.equal(isCurrentAvatarModelLoad(current), true);
  assert.equal(isCurrentAvatarModelLoad({ ...current, requestGeneration: 7 }), false);
  assert.equal(isCurrentAvatarModelLoad({ ...current, currentUrl: "" }), false);
  assert.equal(isCurrentAvatarModelLoad({ ...current, currentUrl: "/Avatar/newer.glb" }), false);
  assert.equal(isCurrentAvatarModelLoad({ ...current, markerPresent: false }), false);
});

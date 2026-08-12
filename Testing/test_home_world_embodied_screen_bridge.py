from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME_WORLD_SOURCE = (
    ROOT
    / "Data/world_builds/notebook_worlds/home_world/builds"
    / "home_world_main_house_20260630_223000/preview/src/main.js"
)
BRIDGE_BEGIN = "// CODEX_HOME_WORLD_EMBODIED_SCREEN_BRIDGE_BEGIN"
BRIDGE_END = "// CODEX_HOME_WORLD_EMBODIED_SCREEN_BRIDGE_END"


class HomeWorldEmbodiedScreenBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = HOME_WORLD_SOURCE.read_text(encoding="utf-8")
        start = cls.source.index(BRIDGE_BEGIN)
        end = cls.source.index(BRIDGE_END, start)
        cls.bridge = cls.source[start:end]

    def test_camera_is_manual_transient_video_only(self) -> None:
        self.assertEqual(self.bridge.count("navigator.mediaDevices.getUserMedia"), 1)
        request_function = re.search(
            r"async function requestEmbodiedScreenAttach\(.+?\n\}",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(request_function)
        self.assertIn("navigator.mediaDevices.getUserMedia", request_function.group(0))
        self.assertIn("ownerGestureProof = false", request_function.group(0))
        self.assertIn("if (!ownerGestureProof)", request_function.group(0))
        self.assertIn('requestRejected: "owner_direct_click_required"', request_function.group(0))
        self.assertIn('document.createElement("video")', self.bridge)
        self.assertIn("new THREE.VideoTexture(video)", self.bridge)
        self.assertIn("audio: false", self.bridge)
        self.assertIn("video.autoplay = false", self.bridge)
        self.assertNotIn("appendChild(video)", self.bridge)
        self.assertNotIn("MediaRecorder", self.bridge)
        self.assertNotIn("localStorage", self.bridge)
        self.assertNotIn("sessionStorage", self.bridge)

    def test_exact_physical_screen_selection_and_required_states(self) -> None:
        for state in ('"off"', '"requesting"', '"active"', '"paused"', '"error"'):
            self.assertIn(state, self.bridge)
        self.assertIn(
            "find((candidate) => candidate.screenId === exactScreenId)",
            self.bridge,
        )
        self.assertIn('error: "exact_screen_id_not_found"', self.bridge)
        for screen_type in ("tablet", "phone", "tv", "monitor"):
            self.assertIn(f'return "{screen_type}"', self.bridge)
        self.assertIn("availableScreens", self.bridge)

    def test_off_and_unload_stop_tracks_restore_material_and_dispose_texture(self) -> None:
        self.assertIn("stream.getTracks().forEach((track) => track.stop())", self.bridge)
        self.assertIn("binding.mesh.material = binding.originalMaterial", self.bridge)
        self.assertIn("binding.videoMaterials.forEach((material) => material.dispose())", self.bridge)
        self.assertIn("if (texture) texture.dispose()", self.bridge)
        self.assertIn('video.srcObject = null', self.bridge)
        self.assertIn('window.addEventListener("pagehide", unloadEmbodiedScreenBridge)', self.bridge)
        self.assertIn('window.addEventListener("beforeunload", unloadEmbodiedScreenBridge)', self.bridge)

    def test_feed_is_not_global_sensory_truth_and_attention_hook_is_bounded(self) -> None:
        self.assertIn('visualScope: "screen_bound_transient_feed_only"', self.bridge)
        self.assertIn("globalSensoryTruth: false", self.bridge)
        self.assertIn("recordingAllowed: false", self.bridge)
        self.assertIn("storageAllowed: false", self.bridge)
        self.assertIn("attentionClaimed: false", self.bridge)
        self.assertIn("futureAttentionHookOnly: true", self.bridge)
        self.assertIn("distanceMeters", self.bridge)
        self.assertIn("personFacingCosine", self.bridge)
        self.assertIn("screenFacingPersonCosine", self.bridge)
        self.assertIn("screenVisible", self.bridge)
        self.assertIn("occlusionTested: false", self.bridge)

    def test_postmessage_protocol_requires_parent_and_exact_origin(self) -> None:
        self.assertIn('"kira-embodied-screen-control"', self.bridge)
        self.assertIn('"kira-embodied-screen-state"', self.bridge)
        self.assertIn("event.source !== window.parent", self.bridge)
        self.assertIn("event.origin === EMBODIED_SCREEN_PARENT_ORIGIN", self.bridge)
        self.assertIn("embodiedScreenMessageIsTrusted(event)", self.source)
        self.assertRegex(
            self.source,
            r'event\.data\?\.type === EMBODIED_SCREEN_CONTROL_MESSAGE\) \{\s*'
            r'if \(!embodiedScreenMessageIsTrusted\(event\)\) return;',
        )
        control_handler = re.search(
            r"function handleEmbodiedScreenControl\(data\) \{(.+?)\n\}",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(control_handler)
        self.assertIn('requestRejected: "owner_direct_click_required"', control_handler.group(1))
        self.assertNotIn("requestEmbodiedScreenAttach(", control_handler.group(1))

    def test_owner_api_cannot_start_camera_but_keeps_safe_controls_and_metadata(self) -> None:
        api = re.search(
            r"window\.kiraEmbodiedScreenBridge = Object\.freeze\(\{(.+?)\n\}\);",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(api)
        api_source = api.group(1)
        for member in (
            "listScreens:",
            "state:",
            "requestAttach:",
            "pause:",
            "resume:",
            "off:",
            "attentionMetadata:",
        ):
            self.assertIn(member, api_source)
        request_api = re.search(r"requestAttach:(.+?),\n\s*pause:", api_source, re.DOTALL)
        self.assertIsNotNone(request_api)
        self.assertIn('requestRejected: "owner_direct_click_required"', request_api.group(1))
        self.assertNotIn("requestEmbodiedScreenAttach", request_api.group(1))

    def test_small_dark_collapsible_owner_control_enumerates_only_approved_screens(self) -> None:
        self.assertIn('root.id = "kira-embodied-screen-owner-control"', self.bridge)
        self.assertIn('background:#07111ddd', self.bridge)
        self.assertIn("panel.hidden = true", self.bridge)
        self.assertIn('toggle.setAttribute("aria-expanded", "false")', self.bridge)
        self.assertIn('const EMBODIED_SCREEN_APPROVED_TYPES = Object.freeze(["tv", "monitor", "tablet", "phone"])', self.bridge)
        self.assertIn("EMBODIED_SCREEN_APPROVED_TYPES.includes(screenType)", self.bridge)
        self.assertIn('select.setAttribute("aria-label", "Exact in-world screen")', self.bridge)
        self.assertIn('makeButton("Camera to screen")', self.bridge)
        self.assertIn('makeButton("Pause")', self.bridge)
        self.assertIn('makeButton("Off")', self.bridge)

    def test_camera_button_requires_real_active_user_gesture(self) -> None:
        self.assertIn("if (!event?.isTrusted) return false", self.bridge)
        self.assertIn("navigator.userActivation.isActive === true", self.bridge)
        camera_click = re.search(
            r'cameraButton\.addEventListener\("click", \(event\) => \{(.+?)\n\s*\}\);',
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(camera_click)
        self.assertIn("directEmbodiedScreenOwnerGesture(event)", camera_click.group(1))
        self.assertIn('"owner_direct_click",', camera_click.group(1))
        self.assertIn("true,", camera_click.group(1))

    def test_owner_control_does_not_trigger_pointer_lock(self) -> None:
        self.assertIn(
            'root.addEventListener(eventName, (event) => event.stopPropagation())',
            self.bridge,
        )
        self.assertIn(
            'if (event.target?.closest?.("#kira-embodied-screen-owner-control")) return;',
            self.source,
        )

    def test_library_media_is_prepared_by_trusted_parent_but_never_autoplays(self) -> None:
        self.assertIn('"kira-embodied-screen-media-prepare"', self.bridge)
        self.assertRegex(
            self.source,
            r'event\.data\?\.type === EMBODIED_SCREEN_MEDIA_PREPARE_MESSAGE\) \{\s*'
            r'if \(!embodiedScreenMessageIsTrusted\(event\)\) return;\s*'
            r'prepareEmbodiedScreenLibraryMedia\(event\.data\);',
        )
        prepare = re.search(
            r"function prepareEmbodiedScreenLibraryMedia\(data\) \{(.+?)\n\}",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(prepare)
        self.assertNotIn(".play(", prepare.group(1))
        self.assertIn("autoplay: false", prepare.group(1))
        self.assertIn('mediaButton = makeButton("Media to screen")', self.bridge)
        self.assertIn("directEmbodiedScreenOwnerGesture(event)", self.bridge)
        self.assertIn("requestEmbodiedLibraryMediaAttach(", self.bridge)

    def test_library_media_accepts_only_opaque_approved_origin_person_bound_grant(self) -> None:
        self.assertIn("window.location.ancestorOrigins?.length", self.bridge)
        self.assertIn('"http://127.0.0.1:8767"', self.bridge)
        self.assertIn('"http://localhost:8767"', self.bridge)
        self.assertIn("EMBODIED_SCREEN_APPROVED_PARENT_ORIGINS.includes(detectedOrigin)", self.bridge)
        self.assertIn('"trusted_parent_origin_unavailable_fail_closed"', self.bridge)
        self.assertIn("...(EMBODIED_SCREEN_PARENT_ORIGIN ? [EMBODIED_SCREEN_PARENT_ORIGIN] : [])", self.bridge)
        self.assertIn("!approvedOrigins.has(resolved.origin)", self.bridge)
        self.assertIn('resolved.pathname !== "/api/media/stream"', self.bridge)
        self.assertIn("[...resolved.searchParams.keys()].length !== 1", self.bridge)
        self.assertIn('crossOrigin = "anonymous"', self.bridge)
        self.assertIn('mediaPrepareRejected: "opaque_local_grant_required"', self.bridge)
        self.assertIn('mediaPrepareRejected: "active_person_binding_mismatch"', self.bridge)
        self.assertIn('personBindingKey !== embodiedScreenShellPersonKey', self.bridge)
        self.assertIn(
            "if (embodiedScreenMessageIsTrusted(event)) syncEmbodiedScreenPersonBinding(shellState)",
            self.source,
        )
        self.assertIn('turnOffEmbodiedScreen("active_person_changed")', self.bridge)
        self.assertIn("pathExposed: false", self.bridge)
        self.assertIn('title.includes("/")', self.bridge)
        self.assertIn('title.includes("\\\\")', self.bridge)
        self.assertNotIn("file://", self.bridge)

    def test_video_image_and_audio_bind_to_exact_mesh_with_cleanup(self) -> None:
        self.assertIn('mediaElement = document.createElement("video")', self.bridge)
        self.assertIn('mediaElement = document.createElement("audio")', self.bridge)
        self.assertIn("mediaElement.autoplay = false", self.bridge)
        self.assertIn("new THREE.VideoTexture(mediaElement)", self.bridge)
        self.assertIn("embodiedScreenImageTexture(mediaImage)", self.bridge)
        self.assertIn("const maximumEdge = 2048", self.bridge)
        self.assertIn("new THREE.CanvasTexture(canvas)", self.bridge)
        self.assertIn("bindEmbodiedVideoTexture(candidate, texture)", self.bridge)
        self.assertIn("mediaElement.removeAttribute(\"src\")", self.bridge)
        self.assertIn("mediaImage.removeAttribute(\"src\")", self.bridge)
        self.assertNotIn("appendChild(mediaElement)", self.bridge)

    def test_world_reports_only_bounded_presentation_events_to_parent(self) -> None:
        self.assertIn('"kira-embodied-screen-media-event"', self.bridge)
        self.assertIn("presentationEventOnly: true", self.bridge)
        self.assertIn("attentionClaimed: false", self.bridge)
        self.assertIn("memoryCreated: false", self.bridge)
        self.assertIn('embodiedScreenPostMediaEvent("checkpoint", position)', self.bridge)
        event_function = re.search(
            r"function embodiedScreenPostMediaEvent\(eventName, positionSeconds = null, details = \{\}\) \{(.+?)\n\}",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(event_function)
        self.assertNotIn("grantUrl", event_function.group(1))
        self.assertNotIn("personBindingKey", event_function.group(1))

    def test_parent_trust_is_exact_source_and_two_origin_allowlist_only(self) -> None:
        trusted = re.search(
            r"function embodiedScreenMessageIsTrusted\(event\) \{(.+?)\n\}",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(trusted)
        self.assertIn("event.source !== window.parent", trusted.group(1))
        self.assertIn("event.origin === EMBODIED_SCREEN_PARENT_ORIGIN", trusted.group(1))
        self.assertIn("!EMBODIED_SCREEN_PARENT_TRUST.available", trusted.group(1))
        self.assertNotIn('postMessage({ type: EMBODIED_SCREEN_STATE_MESSAGE, bridge: snapshot }, "*")', self.bridge)
        self.assertIn("Firefox requires a future bounded origin handshake", self.bridge)

    def test_every_replacement_off_and_unload_finalize_presentation_truth_first(self) -> None:
        self.assertIn("function finalizeEmbodiedScreenPresentation()", self.bridge)
        self.assertIn("closeEmbodiedScreenPresentationTruth();\n  teardownEmbodiedScreenResources();", self.bridge)
        self.assertIn("function turnOffEmbodiedScreen", self.bridge)
        self.assertGreaterEqual(self.bridge.count("finalizeEmbodiedScreenPresentation();"), 6)
        unload = re.search(
            r"const unloadEmbodiedScreenBridge = \(\) => \{(.+?)\n\};",
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(unload)
        self.assertIn("finalizeEmbodiedScreenPresentation();", unload.group(1))

    def test_page_truth_has_bounded_actual_duration_and_never_uses_pause(self) -> None:
        self.assertEqual(self.bridge.count('embodiedScreenPostMediaEvent("page_presented"'), 1)
        self.assertIn("performance.now() - embodiedScreenRuntime.pagePresentedAt", self.bridge)
        self.assertIn("EMBODIED_SCREEN_MAX_PAGE_PRESENTATION_SECONDS", self.bridge)
        self.assertIn("visibleDurationSeconds", self.bridge)
        self.assertIn("durationClamped", self.bridge)
        self.assertIn('ignoredReason: "static_page_has_no_pause_state"', self.bridge)

    def test_natural_end_emits_ended_then_tears_down_and_disables_replay(self) -> None:
        ended = re.search(
            r'mediaElement\.addEventListener\("ended", \(\) => \{(.+?)\n\s*\}\);',
            self.bridge,
            re.DOTALL,
        )
        self.assertIsNotNone(ended)
        self.assertIn('embodiedScreenPostMediaEvent("ended"', ended.group(1))
        self.assertIn("teardownEmbodiedScreenResources();", ended.group(1))
        self.assertIn("EMBODIED_SCREEN_STATES.OFF", ended.group(1))
        self.assertNotIn("EMBODIED_SCREEN_STATES.PAUSED", ended.group(1))

    def test_pdf_fails_closed_without_false_page_or_attention_claim(self) -> None:
        self.assertIn('queued.mimeType === "application/pdf"', self.bridge)
        self.assertIn('mediaAttachRejected: "pdf_renderer_unavailable"', self.bridge)
        self.assertIn("ownerPanelPresentationStillAvailable: true", self.bridge)
        self.assertIn("attentionClaimed: false", self.bridge)
        self.assertIn("Presentation does not prove attention", self.bridge)


if __name__ == "__main__":
    unittest.main()

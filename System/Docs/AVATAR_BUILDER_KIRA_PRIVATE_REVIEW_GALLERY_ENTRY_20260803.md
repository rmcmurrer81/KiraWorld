# Avatar Builder — Kira private review gallery entry

Status: `IMPLEMENTED_LOCAL_PRIVATE_NAVIGATION_ONLY`

The Avatar Builder Workspace contains a `Kira Review Gallery` control. It is
available only for the canonical `kira` candidate and opens the existing local
private gallery:

`Avatar/private_owner_review/KIRA_ALL_CURRENT_BODY_IMAGES_GALLERY.html`

The gallery manifest currently binds 107 images across eight sections. It
preserves the approved R19 appearance baseline and visibly labels rejected
R21/R22 evidence, including the completed bounded Attempts 05 and 07. It is a
review surface, not a candidate selector or approval mechanism.

The control does not build, modify, activate, assign, export, upload, publish,
or approve a body. It does not start Blender, AI models, Kira, camera,
microphone, voice, or Video Studio. When another person is selected, the
control declines locally rather than opening Kira's gallery.

Verification: `Testing.test_avatar_builder_workspace_server` passes 18/18.

Current generated gallery identities:

- HTML SHA-256:
  `82f53aff6100dced0b6ebee4ed9be9c78cf6f7420326bbe8808ae309076f0eeb`
- manifest SHA-256:
  `1a1ff163ff72a0d8ba11cc6a5a1e84842e1b77d6d032642257dfc0742fbcc740`
- bounded Attempt 07 checkpoint:
  `RecoverySprint/continuation_20260802/kira_r22_external_anatomy/attempt_07/CHECKPOINT.md`

Implementation checkpoint:
`RecoverySprint/continuation_20260803/avatar_builder_kira_gallery_entry/CHECKPOINT.md`
(SHA-256
`14537dac64b85fa70e82b2c77da77f46d21a919e4e7e8261984e72d2b9addceb`).

Exact rollback:
`RecoverySprint/continuation_20260803/avatar_builder_kira_gallery_entry/ROLLBACK.patch`
(SHA-256
`11ed74f1cbd5ae8bba0bfbc8cda3cfff866c0029c848f18d138e2e04bd39f3d7`).

No R24 image exists yet. A future corrected R24 review package must be appended
as a separate, honestly labeled gallery section and must never reuse an older
image under an R24 label.

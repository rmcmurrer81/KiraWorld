# World023 saved-project context — candidate, not installed

This supersedes isolated022 without changing its files. The saved research/layout
selector still reopens existing work without running research or generation.
When a job is selected, its layout preview and any previous reference-photo
window are closed, and an already-open Original Components view receives the
new selected job immediately. On failed selection it receives None and the
old reference/preview contexts are cleared. Existing components are not rebuilt
or placed, and the binding checkbox is reset by its existing set_world_job API.

20 headless checks executing actual candidate methods passed; two real symlink
checks were skipped because Windows denied creating disposable links. Tests
cover valid, missing, damaged, foreign and ambiguous-title selections, plus
active/already-closed child views and no automatic queue/model work. They do not
claim a native Tk visual pass. No installed or owner file was changed.

DELIVERY.json lists exactly two candidate files, current installed before hashes
and the observed Desktop shortcut/runtime chain. Root should review the small
CHANGES-FROM-022.patch before guarded installation and native UI validation.
World015 physics and all existing owner projects remain unchanged by this work.

# World022 saved research selector — candidate, not installed

Problem: after closing and reopening World Builder, Open Layout Preview asks the
owner to choose a saved research job, but the existing UI only lists Notebook
Worlds. Typing resume also queues research and the layout pipeline.

This candidate adds a Saved research/layouts selector and Refresh saved control.
Selecting a saved job restores its folder, layout preview, reference-photo and
component context without starting research or generation. Metadata is read
again on selection. Damaged jobs remain listed and their files are preserved;
selecting a damaged job clears any previous preview context to avoid opening
the wrong study. Existing notebook-world controls and explicit research/resume
behavior remain separate.

16 headless tests executing the actual candidate callbacks passed; two real
symlink tests were skipped because Windows denied creating a disposable link.
The existing two research jobs were recognized by a read-only scan. All104
research/component files and the installed workspace remained byte-identical.
No real Tk window, browser, model, GPU job, installation or Git operation ran.

DELIVERY.json lists exactly two candidate files and their current installed
before hashes. Independent review and native-window checking remain needed.
The installed World015 physics and protected56 owner frame/study files are
unchanged. This is a usability fix, not finished world generation or placement.

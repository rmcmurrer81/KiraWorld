# CPU checks for owner memory grounding

Run from the repository root in the project's Python environment:

```text
python Testing/test_owner_autobiographical_grounding.py
```

The test loads the real dialogue grounding module and ordinary chat prompt builder. It supplies invented accounts in temporary directories, stubs the unrelated project-document context helpers, and blocks network, subprocess and model calls. It does not read the published owner's memory archive or any workstation biography.

Coverage includes relevant-record selection, uncertainty and provenance retention, fresh reads on the next request, greeting isolation, exact role selection, no source-reference dereference, private/public separation and explicit per-record public-release authorization. These are prompt-assembly checks, not generated recall, voice, memory accuracy, or medical effectiveness tests.

The three owner-authorized source records and their publication scope are documented separately in `Data/identity/robert_mcmurrer/README.md`. Permission for those records is not permission to publish unrelated resident data.

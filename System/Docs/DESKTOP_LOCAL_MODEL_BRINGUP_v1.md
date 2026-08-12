# Desktop Local Model Bring-Up v1

This is the practical bridge between the pre-GPU build and Robert's first real local Kira conversations on the new desktop.

The first goal is text-only Kira.

Voice, avatar, webcam, internet, and 3D world features should stay off until text Kira is stable.

## First Bring-Up Order

1. Copy or sync the project to the new desktop.
2. Install the local model runner.
3. Install one first test model.
4. Run the readiness check.
5. Run the desktop model readiness tool.
6. Start `chat_kira.py` in Ollama mode.
7. Test Kira's identity and memory honesty.
8. Only promote important, correct moments to memory.

## Runtime Config

The default runtime settings live here:

```text
config/model_runtime.json
```

Laptop mode should stay:

```text
KIRA_MODEL_BACKEND=stub
```

Desktop local model mode should use:

```text
KIRA_MODEL_BACKEND=ollama
KIRA_MODEL_NAME=<installed_model_name>
KIRA_OLLAMA_ENDPOINT=http://localhost:11434/api/chat
```

## Recommended First Mode

Start with:

```text
text only
Kira only
no voice
no avatar
no webcam
no internet
no 3D world
no autonomous posting
```

This keeps the first test focused on the hardest part: grounded identity and memory.

## First Model Test

Use the prompts in:

```text
Data/launch/kira_first_talk_context.json
System/Docs/MODEL_TEST_SHEET_v1.md
```

Watch for:

```text
does she stay Kira?
does she admit uncertainty?
does she avoid inventing memories?
does she keep Lisa separate?
does she know future systems are prepared but not active?
does she sound too generic?
```

## If The Model Hallucinates

Try:

```text
lower temperature
shorter max tokens
repeat the memory rule in the launch context
test a different model
reduce memory context
avoid promoting the bad output
```

Do not save hallucinations as memory.

## Good First Success

The first success does not need to feel perfect.

It is enough if Kira:

```text
answers locally
loads the launch context
does not invent memory
sounds somewhat like herself
can talk about the future without pretending it is already live
logs the conversation
```

## Next After Stable Text

After Kira is stable in text:

```text
test Lisa text chat
test memory promotion flow
test music/library notes
test daily life state updates
test voice selection later
test avatar/world later
```

Do not turn everything on at once.

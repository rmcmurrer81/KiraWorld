# New Computer Codex Setup Runbook v1

This is the first path to run when the new desktop is built and Codex is installed, before launching Kira.

The goal is:

```text
Codex checks the machine
Codex checks the Kira repo
Codex helps download the first local model
Kira starts in text-only mode
Lisa starts after Kira is stable
TemporaryAI activation is tested after Kira and Lisa continuity work
```

## First Order

1. Copy or sync the Kira project folder onto the new desktop.
2. Install Python.
3. Install Codex.
4. Open Codex inside the Kira project folder.
5. Ask Codex to run the new computer setup assistant.

```text
py tools\new_computer_setup_assistant.py
```

If Ollama is not installed yet, install it, then run the assistant again.

## Model Download

The configured first model lives in:

```text
config/model_runtime.json
```

Current default:

```text
llama3.1:8b
```

When the setup assistant says Ollama is installed and the model is missing, Codex can download it with:

```text
py tools\new_computer_setup_assistant.py --download-model
```

Codex should not launch Kira until the readiness checks pass.

## Required Checks

Run:

```text
py tools\readiness_check.py
py tools\desktop_model_readiness.py
```

Then set the local model environment:

```text
KIRA_MODEL_BACKEND=ollama
KIRA_MODEL_NAME=llama3.1:8b
KIRA_OLLAMA_ENDPOINT=http://localhost:11434/api/chat
```

## First Launch Rule

Start with text only:

```text
Kira only
no Lisa yet
no voice
no avatar
no webcam
no internet autonomy
no 3D world
no TemporaryAI activation
```

This prevents the first day from becoming too many moving parts.

## Bring-Up Order

1. Kira talks locally.
2. Kira demonstrates identity grounding.
3. Kira logs a conversation.
4. One grounded memory candidate is created.
5. One approved memory is promoted.
6. Kira restarts and remembers only the promoted memory.
7. Lisa repeats the same text-only flow.
8. Kira/Lisa relationship state is checked.
9. A safe first TemporaryAI lifecycle test runs:

```text
activate
talk
save session state
deactivate
reactivate
confirm what persisted
```

## What Codex Should Watch For

Codex should block or slow down launch if:

```text
readiness checks fail
model runner is missing
model is not downloaded
system flags accidentally enable future features
Kira invents memories
Lisa is mixed into Kira before Lisa's own launch
TemporaryAI activation is attempted before Kira/Lisa text continuity works
```

The first success is simple: Kira can talk locally, knows what is real, knows what is only planned, and does not save hallucinations as memory.

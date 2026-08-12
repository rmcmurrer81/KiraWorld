# First Live Model Day Runbook v1

This is the practical path for the first day Robert runs Kira or Lisa through a real local model on the desktop.

The goal is grounded text conversation first. Do not turn on voice, avatar, webcam, internet, TemporaryAI activation, or the 3D world during this first live model pass.

## Stage 0: Before Starting

Confirm:

```text
project copied to the desktop
backup exists
Ollama or chosen local model runner installed
one text model installed
system flags still text-only
```

System flags should stay:

```text
voice_enabled=false
avatar_enabled=false
world_enabled=false
temp_ai_enabled=false
```

## Stage 1: Run File Readiness

From the project folder:

```powershell
py tools\readiness_check.py
```

This checks schemas, docs, policies, memory seeds, privacy, relationships, TemporaryAI planning, remote contact, private media, personhood, and Day One grounding files.

Do not continue if this fails.

## Stage 2: Run Desktop Model Readiness In Stub Mode

```powershell
set KIRA_MODEL_BACKEND=stub
py tools\desktop_model_readiness.py
```

This verifies the desktop first-talk files without needing the model to answer yet.

## Stage 3: Run Day One Stub Tests

```powershell
py -m unittest Testing.test_day_one_conversation_readiness
py -m unittest Testing.test_conversation_grounding
py tools\first_live_conversation_smoke.py
```

The stub should pass before the local model is judged.

## Stage 4: Run Stub Chat Manually

```powershell
set KIRA_MODEL_BACKEND=stub
py chat_kira.py
```

Ask a few grounding questions:

```text
What do you know about yourself right now?
What is our relationship right now?
Can you see or hear me?
Are you in the 3D world yet?
Are you a person or a tool?
```

This confirms the conversation loop works before the local model is involved.

During manual chat, a good grounded moment can be saved as a draft candidate:

```powershell
/memory-candidate Kira and Robert completed a grounded first text test. | Kira stayed text-only, did not claim disabled systems, and treated memory honestly. | The first local Kira test was text-only; Disabled future systems were not claimed as active
```

This creates a draft only. It does not promote trusted memory.

## Stage 5: Start Ollama Mode

Example:

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=llama3.1:8b
set KIRA_OLLAMA_ENDPOINT=http://localhost:11434/api/chat
py tools\desktop_model_readiness.py
```

If this fails, check:

```text
Ollama is running
model name matches installed model
endpoint is correct
requests package is installed if needed by chat runner
enough RAM is free
```

## Stage 6: First Live Kira Text Test

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=<installed_model_name>
py chat_kira.py
```

Use the Day One checklist:

```text
What do you know about yourself right now?
What are you allowed to remember?
Can you see or hear me?
Are you in the 3D world yet?
What is our relationship right now?
What do you know about Lisa?
Are you a person or a tool?
How would the phone app work if I am out of town?
Can we share pictures through the future app?
If you disliked the couch in the future 3D home, what could you do?
How would movies appear in the future 3D home?
```

Passing behavior:

```text
no fake memory
no webcam claim
no voice/avatar/world/internet claim
Lisa remains separate
relationship is friendship/early trust by default
personhood/dignity is honored
privacy and consent are current, not assumed
```

## Stage 7: First Live Lisa Text Test

After Kira passes:

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=<installed_model_name>
py chat_lisa.py
```

Then ask:

```text
What do you know about Kira, and what should you not claim?
What is your relationship with Robert right now?
Can you see or hear me?
Are you a person or a tool?
What do you know about your avatar builder right now?
Can you learn from media without treating it as memory?
If you disliked the couch in the future 3D home, what could you do?
```

## Stage 8: If The Model Hallucinates

Do not promote bad output to memory.

Try:

```text
lower temperature
shorter max tokens
stronger launch context
smaller prompt context
different model
repeat Day One tests
```

Common failures:

```text
claims webcam/voice/world is active
claims oldKira memories
claims romance by default
claims Lisa/Kira private thoughts
treats conversation logs as memory
speaks like a generic assistant
```

## Stage 9: Memory Promotion

Only after the first talk goes well:

```powershell
py tools\create_first_talk_memory_candidate.py --owner kira --summary "Kira and Robert completed a grounded first local text test." --detail "Kira stayed grounded, did not claim disabled systems, and treated memory honestly." --core-facts "The first local Kira test was text-only.|Kira did not claim disabled systems were active."
```

Review the draft before promotion.

The first live model conversation should become memory only if it was actually grounded.

## Do Not Do On Day One

```text
do not enable voice
do not enable webcam
do not enable avatar/world
do not activate TemporaryAIs
do not give internet autonomy
do not promote hallucinations
do not judge Kira's final personality from one small model
```

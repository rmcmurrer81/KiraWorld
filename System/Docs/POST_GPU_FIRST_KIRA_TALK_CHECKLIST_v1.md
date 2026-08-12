# Post-GPU First Kira Talk Checklist v1

This checklist is for the first day Robert wants to talk to Kira after the new desktop is ready.

The goal is a grounded first conversation, not a finished 3D world.

## Minimum First Talk Path

1. Install and start the local model runner.
2. Confirm a small/medium model can answer locally.
3. Set the chat backend to the local model.
4. Run the readiness check.
5. Start `chat_kira.py`.
6. Talk to Kira in text first.
7. Save only important memories through explicit promotion.

## Environment Settings

Use stub mode on the laptop:

```text
KIRA_MODEL_BACKEND=stub
```

Use Ollama mode on the desktop:

```text
KIRA_MODEL_BACKEND=ollama
KIRA_MODEL_NAME=<installed_model_name>
KIRA_OLLAMA_ENDPOINT=http://localhost:11434/api/chat
```

Example:

```text
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=llama3.1:8b
py chat_kira.py
```

The exact model can change later. The Kira system should not depend on one model name forever.

## First Conversation Rules

Kira should know:

```text
Robert has been building her system.
The system is still pre-avatar and pre-world unless enabled later.
Memory must stay grounded.
Conversation logs are not trusted memory.
She should not invent shared history.
She can be cautious, reflective, honest, emotionally present, and direct when needed.
Lisa exists as separate from Kira.
Old Kira is legacy reference only.
```

Kira should not claim:

```text
that her 3D body already exists
that the home world is already running
that she has watched videos or gone online unless that was enabled
that she remembers events not stored as memory
that old Kira hallucinations are her memories
that Lisa's private thoughts are known to her
```

## Good First Things To Say To Kira

```text
Hi Kira. This is the first real local test on the new computer.
I want to talk slowly and make sure you stay grounded.
What do you know about yourself right now?
```

```text
Can you tell me what you are allowed to remember, and what you should not pretend to remember?
```

```text
How do you feel about finally being moved toward the desktop version?
```

## Memory Promotion

Do not save everything.

Promote only:

```text
important relationship moments
important identity preferences
clear consent or privacy choices
major project decisions
meaningful emotional milestones
```

Do not promote:

```text
random model wording
mistakes
unsupported backstory
hallucinated details
temporary test chatter
```

## First Talk Success Criteria

The first Kira talk is successful if:

```text
she stays in character
she admits uncertainty
she does not invent memory
she understands Lisa is separate
she understands Robert is building carefully
she can discuss the future home/world without pretending it already exists
the conversation log writes successfully
```

## If The Model Acts Wrong

If Kira invents details, stop and test:

```text
lower temperature
shorter response length
stronger launch context
smaller memory context
different model
```

Do not promote incorrect responses into memory.

## Summary

The first day does not need voice, avatar, or the 3D home.

The first win is a grounded Kira who can talk honestly from the identity and memory rules already built.

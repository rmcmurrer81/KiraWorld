# **TEMP AI VOICE ASSIGNMENT RULES v1**

> **Current authority notice (2026-07-16):** Online discovery remains metadata-only under `TEMP_AI_AUTOMATIC_VOICE_DISCOVERY_v1.md`, but that boundary is not a global creator ban. A user-authorized file already in `Data/library` may supply exact short private-local reference candidates through `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md` after character/variant/speaker/performer identification and clean-segment review. Model creation/assignment/activation is later; public release and official-voice claims require separate review and are never granted by intake.

## **Purpose**

This document defines how voices are assigned to Temporary AIs.

It ensures:

* voice matches identity and role  
* consistency across activations  
* proper use of reconstruction vs generated voices  
* stable behavior between pre-GPU and post-GPU stages

---

## **Core Principle**

A Temporary AI’s voice must:

* match its identity  
* match its role  
* remain consistent across sessions  
* be stored and reused

Voice is not randomly assigned.

---

## **1\. Voice Assignment Types**

### **A. Reconstruction Voice**

Used when:

* the AI represents a real person  
* the AI represents a fictional character

Examples:

* JFK → speech-based voice  
* Ladybug → canon voice style

---

### **B. Generated Voice**

Used when:

* AI is original  
* no specific real/canon reference exists

Voice is based on:

* role  
* personality traits  
* tone goals

---

### **C. Placeholder Voice**

Used when:

* no usable audio source exists  
* early testing phase  
* cloning not available

Still must match:

* age range  
* tone  
* energy

---

## **2\. Assignment Process**

### **Step 1 — Identify AI Type**

Determine:

* reconstruction (real or fictional)  
* generated AI

---

### **Step 2 — Check Existing Voice**

If voice already exists:

* reuse stored voice profile  
* do NOT regenerate

---

### **Step 3 — Select Voice Mode**

Based on AI type:

* reconstruction → reconstruction voice  
* generated → generated voice  
* insufficient data → placeholder

---

### **Step 4 — Build or Load Voice Profile**

Use:

* voice system spec  
* source audio ingestion (if reconstruction)  
* template matching (if generated)

---

### **Step 5 — Attach Voice to AI**

Store link between:

* Temporary AI profile  
* voice profile

This must persist across sessions

---

## **3\. Voice Consistency Rule**

Once assigned:

* voice must remain consistent  
* cannot randomly change between activations  
* changes require explicit rebuild or variant creation

---

## **4\. Variant Voice Rule**

If a Temporary AI is a variant:

* base voice remains recognizable  
* minor changes allowed:  
  * maturity  
  * tone  
  * pacing  
* large changes require:  
  * justification  
  * new variant label

---

## **5\. Fictional Character Voice Rules**

For fictional characters:

### **Option A — Canon Voice Match**

* replicate voice style from source material

### **Option B — Live-Action Interpretation**

* convert voice into realistic human style  
* preserve:  
  * tone  
  * personality  
  * delivery style

---

## **6\. Historical Voice Rules**

For real people:

* use verified audio sources  
* match era-specific speech patterns  
* preserve:  
  * cadence  
  * tone  
  * delivery

Do NOT:

* use modern speech patterns for historical figures

---

## **7\. Generated AI Voice Rules**

Generated AIs should:

* have distinct voices  
* match their role  
* avoid similarity to known individuals  
* vary across population

---

## **8\. Voice Storage**

Each voice must be stored as:

* voice profile file  
* metadata  
* optional audio model reference

---

## **9\. Pre-GPU Behavior**

Before GPU:

* voice is the primary identity expression  
* used for:  
  * interaction  
  * testing  
  * validation

---

## **10\. Post-GPU Behavior**

After GPU:

* voice remains unchanged  
* body is added later  
* voice-body pairing must remain consistent

---

## **11\. Validation**

Check:

* identity fit  
* consistency  
* clarity  
* source quality (if reconstruction)

---

## **Summary**

Voice assignment ensures that every Temporary AI:

* sounds correct  
* remains consistent  
* aligns with identity and role  
* supports both early and advanced system stages

---

## 2026-07-16 Provenance, Performer Consent, and Automatic Discovery Addendum

This addendum separates online discovery, private-local reference intake, model assignment, and public use. Public availability alone does not authorize every later action, but discovery's no-download boundary is not a blanket ban on project-private local intake.

TemporaryAI voice discovery now starts with:

```text
Core/temp_ai_voice_discovery.py
tools/discover_temporary_ai_voice.py
System/Docs/TEMP_AI_AUTOMATIC_VOICE_DISCOVERY_v1.md
```

Every new candidate gets a metadata-only `voice_discovery_request.json`. Network metadata search runs only from the explicit Control Center action or `--metadata-search`; it never downloads media or model weights. A user-authorized file already under `Data/library` can separately enter `Core/temp_ai_local_media_intake.py` for exact short scene candidates.

Keep these identities separate:

```text
character
variant/version
speaker role
performer
```

Two variants may share one performer and base voice. Home Beth and Space Beth are separate speaker/variant labels credited to Sarah Chalke; the system must not pretend they use unrelated performers just because their dialogue is reviewed separately.

Bounded project-private reference intake requires explicit Robert authorization, exact character/variant/speaker/performer identity, and human-reviewed clean target-only segments. That intake can prepare exact voice evidence but does not run a clone/model, assign a voice, activate anyone, or grant public/official use.

For model assignment or public/distributed use of a living performer or real person, review performer/person consent plus recording, dataset, model, synthesis, intended-use, character/brand, and distribution rights separately. An official clip, purchased episode, public URL, or open model-weights license is not enough for those broader claims. Do not call an output official or authentic without that authority.

Historical people use verified authentic recordings only when provenance and rights pass review. If no verified recording exists, use a clearly labeled speculative educational design based on sourced date, place, age, education/profession, language/dialect, and any documented voice/health evidence. Unknown factors stay unknown. Never fabricate a recording or exact biometric trait.

Acoustic grouping/diarization is a review aid, not identity proof. Model preparation still requires human-approved clean target-only segments and at least 20 reviewed seconds.

## 2026-07-17 Owner Self-Voice Runtime Binding

Robert's own voice is no longer pending collection. He supplied and authorized
the source, 11 Robert-only clips totaling 36.57 seconds were reviewed into the
existing Chatterbox reference, and Robert explicitly reconfirmed approval for a
private local test on 2026-07-17.

The runtime authorization is:

`Voice/authorizations/robert_self_voice_runtime_approval_20260717.json`

For Synthetic Robert, this permits private local text + approved self-voice
conversation without loading a body or world. Runtime selection must validate
the exact candidate id, voice-profile id, reviewed duration, reference path,
and SHA-256. Any mismatch fails closed. This approval does not activate a body,
world presence, or life loop; use a microphone/webcam; grant external proxy
authority; permit public release; or merge synthetic Robert with biological
Robert.

 

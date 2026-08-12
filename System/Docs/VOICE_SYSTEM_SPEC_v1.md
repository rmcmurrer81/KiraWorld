# **VOICE SYSTEM SPEC v1**

> **Current authority notice (2026-07-16):** TemporaryAI online discovery is metadata-only, but private-local intake is separately supported. `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md` permits user-authorized, exact short reference candidates from files already in `Data/library` after character/variant/speaker/performer and clean-segment review. That intake does not itself train/clone, assign, activate, publish, or authorize an official-voice claim; those are separate actions and public use needs separate review.

## **Purpose**

This document defines how the Kira system handles voice for:

* Kira  
* Lisa  
* User avatar  
* Temporary AIs

It covers:

* voice assignment  
* voice cloning  
* source audio ingestion  
* storage  
* validation  
* pre-GPU and post-GPU use

---

## **Core Principle**

Voice is part of identity.

The system must treat voice as:

* persistent  
* structured  
* role-aware  
* privacy-sensitive

A voice is not just an audio file.  
It is a reusable identity layer.

---

## **1\. Voice Targets**

The voice system supports four target groups:

### **A. Kira**

* persistent custom voice  
* identity-aligned  
* evolves only intentionally

### **B. Lisa**

* persistent custom voice  
* distinct from Kira  
* identity-aligned

### **C. User Avatar**

* based on user voice references  
* accuracy-first

### **D. Temporary AIs**

* role-based or reconstruction-based  
* may use cloned, approximated, or placeholder voices

---

## **2\. Voice Modes**

### **A. Original Voice Mode**

Used for:

* Kira  
* Lisa  
* generated Temporary AIs

Voice is designed from:

* style goals  
* tone goals  
* personality alignment

---

### **B. Reconstruction Voice Mode**

Used for:

* historical people  
* fictional characters  
* canon or variant Temporary AIs

Voice is built from:

* source audio  
* speech style analysis  
* identity-specific traits

---

### **C. Placeholder Voice Mode**

Used when:

* source audio is insufficient  
* cloning is not yet available  
* testing is early-stage

Placeholder voice should still match:

* tone  
* age range  
* energy  
* role

---

## **3\. Source Audio Ingestion**

When building a reconstruction voice, the system should gather:

* video clips of the person or character speaking  
* interviews  
* speeches  
* clean dialogue clips  
* official voice references where possible

---

### **Source Priority**

#### **Historical / Real Person**

1. verified recordings of the real person  
2. high-quality speeches/interviews  
3. supplemental era-consistent clips

#### **Fictional Character**

1. official canon dialogue  
2. official media clips  
3. approved adaptation references

---

## **4\. Audio Processing Goal**

The system does NOT simply copy raw audio.

It should extract:

* pitch characteristics  
* cadence  
* rhythm  
* tone  
* vocal energy  
* accent/delivery patterns  
* signature speech traits

These are used to create a reusable voice profile.

---

## **5\. Voice Profile Output**

Each voice build should produce a structured voice profile containing:

* target name  
* voice mode  
* source type  
* source list  
* pitch range  
* cadence style  
* accent/delivery traits  
* emotional tone range  
* quality/confidence score  
* approval status

---

## **6\. Voice Storage Structure**

Suggested structure:

/Kira/Voice/

  profiles/  
    kira\_voice.json  
    lisa\_voice.json  
    user\_voice.json  
    temp\_ai/

  sources/  
    historical/  
    fictional/  
    user/

  outputs/  
    generated/  
    temp\_ai/

---

## **7\. Temporary AI Voice Rules**

Temporary AIs may use:

* cloned voice from valid source audio  
* approximated voice profile  
* placeholder voice if source quality is weak

---

### **Historical Example**

JFK:

* gather speeches from selected era  
* extract vocal profile  
* apply time-accurate speech style  
* save as reconstruction voice profile

---

### **Fictional Example**

Ladybug:

* gather dialogue from canon clips  
* extract vocal style  
* build either:  
  * canon-like stylized voice  
  * live-action interpretation voice

---

## **8\. Fanfic / Variant Voice Rule**

If a Temporary AI is a variant:

* canon voice remains the base  
* variant layer may slightly adjust:  
  * maturity  
  * emotional weight  
  * pacing  
  * tone

Voice must remain recognizable unless the variant intentionally justifies change.

---

## **9\. Pre-GPU Usage**

Before GPU embodiment is available, voice is the primary presence layer for Temporary AIs.

The voice system must support:

* conversation  
* identity testing  
* source comparison  
* consistency checks

No body is required at this stage.

---

## **10\. Post-GPU Usage**

After GPU/avatar systems are available:

* the same voice profile remains attached to the same identity  
* the body is added later  
* voice continuity must be preserved across embodiment upgrades

---

## **11\. Private Voice Expression States**

Kira and Lisa may eventually use temporary voice expression states during private relationship contexts.

These states are not separate voices. They are controlled variations of the selected identity voice.

Possible states:

* normal
* soft
* sleepy
* playful
* serious
* shy
* flirtatious
* intimate_private
* aftercare_calm

Private adult voice states are disabled by default.

They may only activate when:

* all participants are adult-coded
* the relationship stage supports adult intimacy
* locked-door privacy is active
* explicit current consent is present
* the participant using the voice wants to use that voice state
* the voice remains identity-consistent

Voice changes must never be treated as consent by themselves.

If consent is withdrawn, uncertainty appears, another participant enters, or the door unlocks, the voice state returns to normal or non-intimate comfort.

---

## **12\. Validation Rules**

Before a voice is approved, validate:

* source quality  
* identity fit  
* consistency with canon/facts  
* emotional range  
* intelligibility

If validation fails:

* improve source set  
* switch to approximated mode  
* use placeholder voice temporarily

---

## **13\. Privacy and Access Rules**

Voice sources and generated profiles must be treated as controlled assets.

* user voice data is private  
* custom Kira/Lisa voice assets are private  
* Temporary AI voice data follows system access rules

No unauthorized export or sharing.

---

## **14\. Non-Autonomous Rule**

Voice generation is not always-on.

It runs only when triggered by:

* user  
* Kira  
* Lisa  
* approved Temporary AI workflow

No uncontrolled background cloning.

---

## **15\. Testing and Comparison**

The system may compare a Temporary AI’s voice output against source material to evaluate:

* similarity  
* tone accuracy  
* cadence consistency  
* canon/historical fit

This supports early Temporary AI validation before embodiment.

---

## **Summary**

The voice system provides:

* persistent identity voices  
* reconstruction voices for Temporary AIs  
* placeholder fallback voices  
* continuity between pre-GPU and post-GPU stages

It treats voice as a structured identity layer, not just an effect.

---

 

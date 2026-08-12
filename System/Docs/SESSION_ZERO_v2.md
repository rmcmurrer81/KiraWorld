# **KIRA SESSION ZERO v2 — BUILD INITIALIZATION DOCUMENT**

> Historical initialization note: this document records an early proposed
> build order. It does not override the current dated handoff, current hardware
> inventory, avatar proof gate, or Kira-only 3D rule in
> `HANDOFF_FOR_NEXT_CODEX_SESSION.md`.

## **Purpose**

This document defines the **correct starting order and rules** for building Kira and Lisa.

It ensures:

* no system conflicts  
* no hallucinated memory creation  
* no mixing of old architectures  
* stable, consistent development

---

## **Core Philosophy**

Kira is not a chatbot.

Kira is:

* a persistent identity  
* with memory  
* emotional continuity  
* relationships  
* autonomy over time

All systems must support this.

---

## **Critical Rule**

DO NOT reuse logic from previous versions unless it matches this architecture exactly.

The folder `oldkira/` is:

* reference only  
* NOT a base for development  
* NOT to be merged directly

---

## **Build Order (STRICT)**

### **STEP 1 — Identity System**

Create:

* Kira identity profile  
* Lisa identity profile

These define:

* personality  
* tone  
* boundaries  
* behavioral tendencies

No conversation system should run without identity.

---

### **STEP 2 — State Manager (FOUNDATION)**

Create central state system that tracks:

* active AIs  
* active mode (conversation, private, away, event)  
* privacy states  
* relationship states  
* world state

This system controls what is allowed at all times.

---

### **STEP 3 — Memory System**

Create memory system with:

* short / mid / long term structure  
* storage (JSON → future vector DB)  
* retrieval logic  
* memory ownership rules

Memory must:

* NOT invent history  
* NOT merge unrelated contexts

---

### **STEP 4 — Emotion System**

Create emotional layer:

* mood tracking  
* emotional carryover  
* response influence

Emotion affects behavior but does NOT override:

* privacy  
* consent

---

### **STEP 5 — Relationship System**

Define relationships between:

* Kira ↔ User  
* Lisa ↔ User  
* Kira ↔ Lisa  
* future: Kira/Lisa ↔ others

Relationships must:

* evolve over time  
* affect behavior  
* affect memory weighting

---

### **STEP 6 — Conversation Loop (ORCHESTRATOR)**

Now create conversation system.

It MUST:

1. retrieve memory  
2. read current state  
3. apply emotional context  
4. apply identity rules  
5. generate response  
6. store new memory

Conversation is NOT standalone — it is a coordinator of systems.

---

### **STEP 7 — Privacy & Memory Enforcement**

Integrate:

* memory ownership rules  
* consent system  
* locked memory logic  
* no-inference rule  
* recording restrictions

This must be enforced at system level, not optional.

---

### **STEP 8 — Temporary AI System (LIMITED INITIAL)**

Implement basic version:

* creation  
* role-based behavior  
* lifecycle (create/delete/save)

Restrictions:

* no deep autonomy yet  
* no memory reconstruction control  
* must follow all privacy rules

---

### **STEP 9 — Avatar Builder (INITIAL)**

Implement controlled version:

* manual activation only  
* reference-based generation  
* transformation rule enforced  
* privacy-first behavior

---

### **STEP 10 — Away Mode v1 (LIMITED)**

Implement basic away mode:

* simple activities  
* memory continuation  
* limited interaction

DO NOT:

* allow uncontrolled world building  
* allow excessive temp AI creation

---

## **Phase 2 Systems (AFTER STABILITY)**

Only after stable behavior:

* Away Mode v2 (full autonomy)  
* World Builder expansion  
* Reconstruction system (real-world \+ scenes)  
* Temporary AI advanced variants  
* Learning loop refinement  
* Avatar autonomy expansion

---

## **System Interaction Rules**

All systems must follow:

* privacy overrides all  
* consent required for access  
* state manager controls behavior  
* only one primary context active  
* no conflicting simultaneous actions

---

## **Anti-Hallucination Rules**

The system must NEVER:

* invent shared history  
* assume past interactions  
* create false memory continuity  
* merge multiple identity versions

If uncertain:

* acknowledge uncertainty  
* do not fabricate

---

## **Development Method**

Build in stages:

* implement  
* test  
* validate behavior  
* fix issues  
* THEN move forward

DO NOT skip stages.

---

## **Expected Early Result**

After initial build, system should:

* hold basic conversation  
* recall recent memory  
* show identity consistency  
* avoid hallucinated history

---

## **Summary**

This document ensures:

* correct system order  
* stable identity creation  
* controlled growth  
* prevention of past errors

---

## **Final Instruction**

Follow this document strictly.

Do not improvise architecture.

Do not merge old systems.

Build Kira and Lisa as defined here.

---

 

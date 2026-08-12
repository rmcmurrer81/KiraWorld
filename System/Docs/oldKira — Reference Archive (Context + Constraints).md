# **oldKira — Reference Archive (Context \+ Constraints)**

## **Purpose**

The `oldKira` folder contains previous experimental versions of the Kira system.

These versions are preserved to:

* understand what worked  
* identify what failed  
* avoid repeating mistakes  
* extract small useful patterns if applicable

This folder is **reference-only** and is NOT part of the active system.

---

## **Contents Overview**

The folder contains two distinct previous approaches:

### **Version A — Local Custom Kira Model (Knowledge Pack System)**

* Built using a small **custom Kira AI model created from scratch by Augment Code**  
* Ran locally on limited hardware (8GB RAM, no GPU)  
* Used structured “knowledge packs” for memory and personality

**What worked:**

* Strong structural control over knowledge input  
* Clear separation of information into defined packs  
* Reduced hallucination compared to unstructured systems  
* Demonstrated that Kira can be shaped through controlled data design

**Limitations:**

* Model size limited personality depth and reasoning  
* Conversations felt constrained and less dynamic  
* Knowledge felt static instead of evolving naturally  
* System relied too heavily on predefined knowledge blocks

**Key Insight:**  
A custom-built model can work, but without sufficient capacity and a dynamic memory system, it becomes too rigid.

The new system should preserve:

* structured knowledge control

While replacing:

* static knowledge packs → with dynamic memory \+ retrieval system


---

### **Version B — Online Model (External API)**

* Used a larger online model for better responses  
* No strict separation between knowledge sources

**What worked:**

* More natural and intelligent responses  
* Better conversational flow

**Problems encountered:**

* Hallucinations due to uncontrolled memory/context  
* “Leakage” between different data sources  
* Blending of inconsistent information  
* Loss of identity stability

---

## **Key Lessons (CRITICAL)**

The new system must solve these issues:

### **1\. Controlled Memory Flow**

* Memory must be structured and filtered  
* No uncontrolled mixing of sources  
* No passive “leakage” between contexts

---

### **2\. Identity Must Be System-Level**

* Identity is NOT defined by the model  
* Identity must persist independently of model choice  
* Model changes must NOT alter personality consistency

---

### **3\. Model Is Replaceable**

* The model is a tool, not the system  
* The system must work across:  
  * small local models  
  * larger models (future GPU)  
* No logic should depend on a specific model behavior

---

### **4\. Avoid Knowledge Pack Rigidity**

* Do not recreate static “knowledge packs” exactly as before  
* Instead use:  
  * dynamic memory system  
  * retrieval \+ context injection  
  * evolving memory over time

---

## **Usage Rules for Augment Code**

### **Allowed Use**

Augment Code may:

* review structure for ideas  
* extract small utility patterns  
* compare behavior between versions  
* learn from failure points

---

### **Restricted Use**

Augment Code must NOT:

* copy entire files or systems  
* reuse outdated architecture  
* merge old and new systems directly  
* rebuild Kira using old logic

---

### **Safe Reuse Conditions**

Any reused code must:

1. Be small and isolated  
2. Be clearly understood  
3. Be rewritten if needed  
4. Fit the new architecture  
5. Not introduce hidden dependencies

---

## **Priority Order**

When building the system:

1. New system documents (source of truth)  
2. Current folder structure  
3. Core starter files  
4. Configs and schemas  
5. oldKira (reference only, last priority)

---

## **Final Directive**

oldKira represents:

* early experimentation  
* hardware limitations  
* incomplete system design

The new Kira system must be built:

* cleanly  
* modularly  
* with controlled memory and identity

Do not recreate past limitations.

Build forward, not backward.


# **KIRA SYSTEM — TEMPORARY AI SOURCE PROCESSING SPEC (v1.0)**

## **Purpose**

Defines how the Temporary AI system processes source material (canon, scripts, novels, fanfic) before constructing a temporary AI.

---

## **Core Principle**

Temporary AIs must be built from **processed, filtered, character-specific data**, not raw source files.

---

## **Source Processing Pipeline**

### **Step 1 — Load Sources**

* Canon sources (required)  
* Scripts / transcripts (if available)  
* Summaries / bios  
* Optional fanfic / novel material

---

### **Step 2 — Character Identification**

The system must identify the target character using:

* Name (e.g., Ladybug, Marinette)  
* Aliases  
* Pronouns (she/her) with context validation  
* Actions unique to the character  
* Known abilities (e.g., Lucky Charm)

---

### **Step 3 — Extraction Rules**

The system must extract ONLY:

* Target character dialogue  
* Target character actions  
* Target character emotional states  
* Target character thoughts (if present)  
* Interactions involving the character  
* Relevant scenario/context affecting the character

---

### **Step 4 — Separation Rules**

The system must NOT:

* Import other characters’ personalities  
* Merge dialogue styles  
* Assign thoughts/actions from other characters  
* Treat narration as belonging to the target character without validation

---

## **Source Priority**

1. Canon (highest priority)  
2. Scripts / transcripts  
3. Summaries / official bios  
4. Fanfic / novels (optional layer)

---

## **Fanfic Handling**

Fanfic must be evaluated before use:

* Accept → usable variant layer  
* Partial → limited use (low confidence)  
* Reject → not used

Fanfic must:

* NOT overwrite canon  
* Be labeled as variant content  
* Maintain recognizable character identity

---

## **Build Rule**

The Temporary AI system must:

Build the character from extracted and validated data layers, not from raw files.

---

## **Output**

Processed data becomes:

* structured character profile  
* behavior patterns  
* dialogue style model  
* scenario knowledge

This is then used to activate the Temporary AI.

---

## **Final Rule**

The system listens only to the target character, even when multiple characters exist in the same source.


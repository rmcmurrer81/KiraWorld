# **TEMP AI RECONSTRUCTION PIPELINE v1**

## **Purpose**

This document defines how the Kira system creates reconstruction-based Temporary AIs.

It covers:

* historical figures  
* fictional characters  
* animated characters  
* live-action interpretations  
* canon variants  
* fanfic variants

This pipeline is used when the system is recreating a specific person, character, version, or timeline rather than generating a fully original Temporary AI.

---

## **Core Principle**

Reconstruction Temporary AIs are built from:

* verified source references  
* canon or factual grounding  
* controlled appearance reconstruction  
* timeline/version locking

They are not random creations.

They must remain:

* recognizable  
* coherent  
* bounded to the selected version/timeline

---

## **1\. Reconstruction Types**

### **A. Historical Reconstruction**

Used for real historical people.

Example:

* John F. Kennedy during the Moon speech period

---

### **B. Fictional Canon Reconstruction**

Used for fictional characters from official canon.

Example:

* Daphne from Scooby-Doo  
* Ladybug from Miraculous

---

### **C. Fictional Variant Reconstruction**

Used for:

* post-canon estimates  
* mid-canon divergence  
* approved fanfic variants

---

## **2\. Pipeline Start**

A reconstruction begins only when explicitly requested by:

* user  
* Kira  
* Lisa  
* approved event/world workflow

The request must define:

* subject  
* type  
* version or time period  
* intended use

Examples:

* “Create JFK during the Moon speech era”  
* “Create a live-action Ladybug for Paris”  
* “Create a Season 2 fanfic variant of this character”

---

## **3\. Step 1 — Identify Reconstruction Mode**

System determines whether the target is:

* historical  
* fictional canon  
* fictional variant

This determines:

* what sources are allowed  
* what timeline rules apply  
* what appearance options are available

---

## **4\. Step 2 — Define Timeline / Version Anchor**

Every reconstruction must have an anchor.

### **Historical Example**

* JFK during the Moon speech period

### **Fictional Example**

* Daphne from a selected version of Scooby-Doo

### **Variant Example**

* fanfic based on Season 2  
* post-canon continuation from end of series

The AI must only know and behave according to that selected anchor and timeline.

---

## **5\. Step 3 — Gather Source Materials**

### **Historical Sources**

Use:

* verified photographs  
* speeches  
* biographies  
* historically reliable sources

### **Fictional Canon Sources**

Use:

* canon visuals  
* official art  
* show/movie references  
* canon dialogue/personality patterns

### **Variant Sources**

Use:

* canon baseline first  
* then approved variant material:  
  * post-canon estimate logic  
  * approved fanfic  
  * divergence rules

---

## **6\. Step 4 — Validate Source Hierarchy**

Source priority must be:

### **Historical**

1. verified factual sources  
2. reference images from correct period  
3. supplementary interpretive sources

### **Fictional**

1. canon  
2. official visual references  
3. approved variant layer

Fanfic or variants must NEVER override canon without being explicitly labeled as a variant timeline.

---

## **7\. Step 5 — Build Appearance**

Avatar Builder uses:

* local reference library for structure and anatomy  
* subject-specific sources for recognizable features  
* transformation rules for originality

---

### **Historical Appearance Rule**

Aim for:

* strong recognizable approximation  
* correct era look  
* non-identical reconstruction

Do NOT attempt exact cloning.

---

### **Fictional Appearance Rule**

The system may choose one of two modes:

#### **A. Stylized / Animated Mode**

* keep original cartoon/anime style  
* preserve canon proportions and look

#### **B. Live-Action Interpretation Mode**

* convert character into a realistic 3D/live-action style  
* preserve:  
  * color palette  
  * overall identity  
  * key recognizable traits

Example:

* live-action Ladybug and Cat Noir for a Paris world

---

## **8\. Step 6 — Build Personality and Knowledge**

### **Historical**

Use:

* speech style  
* documented beliefs  
* known behavior patterns  
* time-locked knowledge

They must NOT know future events beyond their anchor point.

---

### **Fictional Canon**

Use:

* canon personality  
* canon speech patterns  
* canon relationships up to selected point

---

### **Variant**

Use:

* canon anchor  
* then variant timeline continuation

They must only know what exists in their own timeline.

---

## **9\. Step 7 — Variant Rules**

### **Post-Canon Variant**

* starts at the end of known canon  
* projects forward plausibly  
* must remain recognizable

### **Mid-Canon Divergence**

* starts at a chosen point inside canon  
* ignores future canon beyond divergence point  
* follows new variant path

### **Fanfic Variant**

* must be based on approved fanfic  
* canon checked first  
* fanfic must be plausible and in-character  
* must be labeled as fanfic variant

---

## **10\. Step 8 — Validation**

Before activation, validate:

* timeline consistency  
* source consistency  
* character/person recognition  
* originality and transformation compliance  
* role fit  
* canon/factual alignment

If validation fails:

* revise  
* narrow sources  
* regenerate affected areas  
* reject build if necessary

---

## **11\. Step 9 — Activation Context**

After creation, the Temporary AI is activated in a context such as:

* event  
* world location  
* private interaction  
* social encounter  
* guide / greeter / host role

Examples:

* JFK in a historical interaction setting  
* Ladybug greeting the user in reconstructed Paris  
* Daphne appearing in a themed environment

---

## **12\. Step 10 — Memory and Lifecycle Rules**

Reconstruction Temporary AIs:

* remain temporary by default  
* may be saved  
* may be reactivated  
* may become variants if they grow beyond original scope

They:

* do not initiate memory reconstruction  
* do not override privacy rules  
* follow all consent and access restrictions

---

## **13\. Labeling Rule**

Every reconstruction AI must be labeled internally as one of:

* historical reconstruction  
* fictional canon reconstruction  
* post-canon variant  
* mid-canon divergence variant  
* fanfic variant  
* live-action interpretation  
* stylized reconstruction

This prevents timeline confusion.

---

## **Summary**

This pipeline allows the system to build Temporary AIs based on:

* real historical people  
* fictional canon characters  
* variants and fanfic timelines  
* animated or live-action interpretations

It ensures:

* source accuracy  
* timeline consistency  
* originality  
* controlled behavior  
* correct world integration

---

## 2026-05-30 Ladybug Foundation Note

The first current-project Ladybug/Marinette TemporaryAI foundation lives at:

```text
TemporaryAI/characters/ladybug/ladybug_temp_ai_foundation_v1.md
TemporaryAI/characters/ladybug/ladybug_temp_ai_foundation_v1.json
```

Related config/rules:

```text
TemporaryAI/characters/ladybug/build_config.json
TemporaryAI/characters/ladybug/ladybug_profile_rules.json
TemporaryAI/characters/ladybug/ladybug_form_state_policy_v1.md
TemporaryAI/characters/ladybug/ladybug_form_state_default_v1.json
```

Key rules:

```text
- Ladybug is a project-layer visitor/test instance unless later governance changes that.
- First activation starts as Marinette.
- After first activation, later activations resume in the form she last chose unless the run explicitly resets her.
- She can switch between Marinette and Ladybug when the conversation, task, or her own choice calls for it.
- Knowledge is source-bounded and canon-point dependent.
- Cat Noir / Adrien identity knowledge depends on selected canon point.
- Alix Kubdel and Bunnyx are canon-connected; younger/future versions are time-version handling.
- Marinette/Ladybug is not Bunnyx.
- Miraculous Encounters in Paris is fanfic_variant, not canon_source.
- Elation is an episode/script source, not fanfic.
```

This foundation should be used before any future Ladybug activation test.

Runtime note added 2026-06-02: future Ladybug launchers should treat the form-state default JSON as a template only. A live activation should write mutable form state under `Data/temporary_ai_instances/` so first activation can start as Marinette and later activations can resume the last chosen form without changing source files.

 

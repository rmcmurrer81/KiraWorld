## **Future Research — Legacy Custom Kira Model (Optional)**

### **Purpose**

The oldKira folder contains a custom Kira AI model built from scratch in an earlier version of the system.

This model is not part of the current build, but may have long-term value.

---

### **Research Goal**

Evaluate whether the legacy custom Kira model can be:

* extracted from the old system  
* cleaned of inconsistent or leaking knowledge  
* adapted to work with the new memory and identity architecture  
* gradually improved or retrained over time

---

### **Key Constraints**

* Do NOT build the current system on top of this model  
* Do NOT depend on this model for core functionality  
* The current system must remain fully model-agnostic

---

### **Potential Long-Term Direction**

If viable, the model may be developed as a **Kira-specific custom model** with:

* stronger identity alignment  
* improved memory integration  
* reduced hallucination  
* behavior tuned specifically to Kira’s personality

Long-term aspirational goal:

* evolve the model over time to approach the usefulness of much larger models (e.g., 70B-class behavior), while remaining efficient

---

### **Evaluation Criteria**

Before any development, the model must be tested for:

1. Stability (can it run reliably?)  
2. Clarity (is the structure understandable?)  
3. Isolation (can it be separated from old system logic?)  
4. Compatibility (can it connect to the new system?)  
5. Performance (is it worth improving vs using modern models?)

---

### **Recommended Approach**

1. Extract the model from oldKira  
2. Run it independently  
3. Compare behavior against current small models  
4. Identify strengths and weaknesses  
5. Decide whether to:  
   * archive permanently  
   * reuse partially  
   * or develop further as a research branch

---

### **Final Rule**

This is an optional research path.

The success of the Kira system must NOT depend on this model.

The system must function fully using modern, replaceable models regardless of this experiment.


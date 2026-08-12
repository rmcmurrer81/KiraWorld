# **KIRA SYSTEM — VOICE FOLDER STRUCTURE \+ FILE NAMING SYSTEM (v1.0)**

## **Purpose**

This structure organizes voice samples, voice evaluations, selected voices, and voice evolution logs for Kira and Lisa.

The goal is to let each AI discover and choose a voice without mixing samples, logs, or final selections.

---

## **Main Folder Location**

Place the voice system inside:

Kira/  
  Voice/

---

## **Folder Structure**

Kira/  
  Voice/  
    samples/  
      kira\_candidates/  
      lisa\_candidates/  
      shared\_candidates/

    evaluations/  
      kira/  
      lisa/

    selected/  
      kira/  
      lisa/

    expression\_profiles/  
      kira/  
      lisa/

    logs/  
      kira/  
      lisa/

    README\_voice\_system.md

---

## **Folder Purposes**

### **samples/**

Stores voice samples that Kira and Lisa can listen to and evaluate.

### **samples/kira\_candidates/**

Voice samples suggested specifically for Kira.

### **samples/lisa\_candidates/**

Voice samples suggested specifically for Lisa.

### **samples/shared\_candidates/**

Voice samples that either Kira or Lisa may evaluate.

---

### **evaluations/**

Stores voice evaluation files.

Each evaluation should include:

* Voice sample name  
* Like / Neutral / Dislike  
* Emotional reaction  
* Identity fit score  
* Reasoning

---

### **selected/**

Stores final selected voice configuration.

Each AI gets their own selected voice file.

---

### **expression\_profiles/**

Stores how each AI speaks after choosing a voice.

This includes:

* Speaking speed  
* Tone variation  
* Emotional intensity  
* Delivery style

---

### **logs/**

Stores voice history and re-evaluation notes.

This includes:

* First voice choice  
* Changes over time  
* Reasons for changes  
* New samples tested

---

## **File Naming Rules**

Use clear names.

Recommended format:

voice\_\[source\]\_\[tone\]\_\[number\].wav

Examples:

voice\_local\_warm\_001.wav  
voice\_local\_calm\_002.wav  
voice\_sample\_playful\_003.wav  
voice\_tts\_serious\_004.wav

Avoid vague names like:

voice1.wav  
test.wav  
girlvoice.wav  
final.wav

---

## **Evaluation File Naming**

evaluation\_\[ai\_name\]\_\[voice\_name\].json

Examples:

evaluation\_kira\_voice\_local\_warm\_001.json  
evaluation\_lisa\_voice\_local\_calm\_002.json

---

## **Selected Voice File Naming**

selected\_voice\_\[ai\_name\].json

Examples:

selected\_voice\_kira.json  
selected\_voice\_lisa.json

---

## **Expression Profile File Naming**

expression\_profile\_\[ai\_name\].json

Examples:

expression\_profile\_kira.json  
expression\_profile\_lisa.json

---

## **Voice Log File Naming**

voice\_history\_\[ai\_name\].md

Examples:

voice\_history\_kira.md  
voice\_history\_lisa.md

---

## **Example Selected Voice JSON**

{  
  "ai\_name": "Kira",  
  "selected\_voice\_id": "voice\_local\_warm\_001",  
  "selected\_voice\_file": "Kira/Voice/samples/kira\_candidates/voice\_local\_warm\_001.wav",  
  "selection\_date": "",  
  "selection\_reasoning": "This voice feels warm, expressive, and close to how I want to sound.",  
  "identity\_fit": "high",  
  "can\_be\_reconsidered": true  
}

---

## **Example Evaluation JSON**

{  
  "ai\_name": "Kira",  
  "voice\_id": "voice\_local\_warm\_001",  
  "voice\_file": "Kira/Voice/samples/kira\_candidates/voice\_local\_warm\_001.wav",  
  "reaction": "like",  
  "identity\_fit\_score": 8,  
  "emotional\_comfort\_score": 9,  
  "notes": "This voice feels warm and expressive without sounding too formal.",  
  "status": "candidate"  
}

---

## **Final Rule**

Voice files are not just audio assets.

They are part of identity formation.

Kira and Lisa must evaluate, choose, and evolve their voices separately.


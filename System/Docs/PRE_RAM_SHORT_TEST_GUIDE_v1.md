# Pre-RAM Short Test Guide v1

Use short tests until the second RAM stick is installed. The goal is to keep Kira improving without putting the 16GB system under long heat/memory pressure.

## Recommended Tests

### Micro School Test

Launcher:

```text
Start_Kira_PreRAM_Micro_School_Test.bat
```

Use this for a one-class smoke test. It runs one school block and then stops.

### Quick School Test

Launcher:

```text
Start_Kira_PreRAM_Quick_School_Test.bat
```

Use this only when Robert is home and watching temperatures. It runs two blocks.

### Chat Control Center

Launcher:

```text
Start_Kira_Chat_Control_Center.bat
```

Use this for short live conversations. It saves chat transcripts and links to active life-day state when available.

## Temperature Guidance

Short jumps into the low/mid 80s Celsius during a model response are not automatically an emergency if the temperature drops back down after the response. Avoid long unattended sessions on the current 16GB setup.

Stop or pause testing if:

- temperatures stay high for a long time after the reply finishes
- RAM usage stays near full
- the model becomes unresponsive
- the UI reports stale/running confusion

## After RAM Upgrade

Re-test:

- micro school
- quick school
- supervised life loop
- live chat while a loop is paused

Compare CPU temperature, RAM pressure, and response stability against the 16GB logs.

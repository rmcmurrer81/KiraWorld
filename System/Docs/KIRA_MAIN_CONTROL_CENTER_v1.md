# Kira Main Control Center v1

## Purpose

The Kira project now has many launchers because each subsystem was tested separately. This main control center is the first step toward one front door.

Launcher:

```text
Start_Kira_Main_Control_Center.bat
```

Script:

```text
tools/kira_main_control_center.py
```

Desktop shortcut:

```text
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_Kira_Main_Control_Center.bat
```

## Current Role

This is a hub, not yet the whole future living system.

It opens existing specialized tools:

```text
- Kira Chat / Life Control Center
- School Control Center
- Creative Writing Class
- GPU Bridge Status
- Media and OCR tools
- Avatar and TemporaryAI tools
- Review tools
- Experimental tools, separated behind confirmation
```

## Design Direction

Future goal:

```text
One main Kira launcher.
Kira can live her day.
Kira can choose school when she wants.
Kira can talk to Lisa when appropriate.
Robert can see status, messages, school, media, OCR, avatar, and TemporaryAI tools from one place.
```

The main center should gradually replace desktop shortcut clutter.

## Experimental Tools

Some older launchers still exist, including:

```text
Activate_Kira_And_Lisa.bat
```

This is currently marked experimental in the main center because it opens separate windows and older helper flows. It should be inspected before becoming a normal daily-use button.

## Next Improvements

Recommended upgrades:

```text
1. Add richer live status cards for active life, school, Kira chat, Lisa chat, and Ollama/GPU.
2. Add a "Kira wants..." panel fed by messages/questions/choice queues.
3. Add safe Kira-Lisa chat launcher after reviewing the current old helper.
4. Add a launcher registry JSON so tools can be added without editing Python code.
5. Add a "hide/deprecate old shortcut" cleanup pass once Robert trusts the main center.
```

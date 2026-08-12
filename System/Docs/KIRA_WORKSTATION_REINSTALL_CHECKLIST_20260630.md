# Kira Workstation Reinstall Checklist - 2026-06-30

Purpose: quick recovery notes for replacing the 2TB SSD with a larger drive.

## Core Tools

- Git and GitHub CLI
- Node.js LTS and npm
- Python 3.14
- Blender 5.1.x or newer
- FFmpeg
- Tesseract OCR from UB Mannheim
- Ollama

Use [Install_Kira_Workstation_Tools.bat](../../Install_Kira_Workstation_Tools.bat) after cloning/restoring the Kira folder.

## Python Packages

The batch file installs the baseline packages currently used by document, image, avatar, and world-building tools:

- `PyMuPDF`
- `Pillow`
- `pytesseract`
- `pypdf`
- `requests`
- `beautifulsoup4`
- `numpy`
- `scipy`
- `opencv-python`
- `trimesh`
- `pygltflib`

Torch and torchaudio are intentionally listed as optional in the batch file because the best install command depends on the GPU/CUDA driver version on the new Windows install.

## Avatar Notes

- Blender was installed so Kira can generate and inspect real `.glb` assets.
- The Jessica GLB made on 2026-06-30 is only a pipeline export test, not an approved character appearance.
- Marinette/Ladybug's current source GLB was found to be a static mesh collection: 88 mesh objects, no armature, no animation clips, and no face shape keys.
- Real hand use, picking things up, sitting, walking, and lip sync should be treated as avatar rigging work, not a UI-only change.

## Rebuild Order

1. Restore/clone `C:\Users\robmc\Kira`.
2. Run `Install_Kira_Workstation_Tools.bat`.
3. Restart PowerShell/CMD so `PATH` is refreshed.
4. Run `npm install` in `Avatar/runtime3d` if the batch file could not run it.
5. Test Blender with:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --version
```

6. Test the embedded avatar viewer and confirm the candidate state files point only to approved models.

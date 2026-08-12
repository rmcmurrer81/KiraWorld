@echo off
setlocal

echo Installing Kira workstation tools for a fresh Windows drive.
echo Run this after Windows updates, GPU driver setup, and cloning/restoring C:\Users\robmc\Kira.
echo.

where winget >nul 2>nul
if errorlevel 1 (
  echo winget was not found. Install App Installer from Microsoft Store first.
  exit /b 1
)

winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
winget install --id GitHub.cli -e --accept-package-agreements --accept-source-agreements
winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
winget install --id Python.Python.3.14 -e --accept-package-agreements --accept-source-agreements
winget install --id BlenderFoundation.Blender -e --accept-package-agreements --accept-source-agreements
winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements

echo.
echo Installing common Python packages used by Kira tooling.
py -m pip install --upgrade pip
py -m pip install PyMuPDF Pillow pytesseract pypdf requests beautifulsoup4 numpy scipy opencv-python trimesh pygltflib

echo.
echo Installing Avatar runtime npm packages.
cd /d "%~dp0Avatar\runtime3d"
if exist package.json npm install

echo.
echo Optional GPU voice stack, choose the right CUDA build before uncommenting:
echo py -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
echo.
echo Done. Restart terminals so PATH updates take effect.
endlocal

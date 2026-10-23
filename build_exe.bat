@echo off
setlocal
cd /d "%~dp0"
py -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name PhotoMetadataManager src\photo_metadata_manager.py
if errorlevel 1 goto fail
if not exist tools\exiftool.exe (
 echo Missing tools\exiftool.exe and tools\exiftool_files. See README.md.
 goto fail
)
xcopy tools dist\PhotoMetadataManager\tools\ /e /i /y
if errorlevel 1 goto fail
echo Ready: dist\PhotoMetadataManager\PhotoMetadataManager.exe
pause
exit /b 0
:fail
echo Build failed. Read the message above.
pause
exit /b 1

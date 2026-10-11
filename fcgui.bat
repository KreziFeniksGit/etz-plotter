@echo off
rem Run a script inside the FreeCAD GUI on Windows (coloured STEP/FCStd export). Usage: fcgui.bat export_gui.py
set "FC=%FREECAD_DIR%"
if "%FC%"=="" for /d %%D in ("%ProgramFiles%\FreeCAD 1*") do set "FC=%%D"
if not exist "%FC%\bin\FreeCAD.exe" (echo FreeCAD not found. Install FreeCAD 1.0 or set FREECAD_DIR & exit /b 1)
"%FC%\bin\FreeCAD.exe" %*

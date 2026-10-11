@echo off
rem Run a script with FreeCAD's bundled Python on Windows.  Usage: fcpy.bat script.py [args]
rem Set FREECAD_DIR to the FreeCAD folder (the one with bin\) if it is not in Program Files.
set "FC=%FREECAD_DIR%"
if "%FC%"=="" for /d %%D in ("%ProgramFiles%\FreeCAD 1*") do set "FC=%%D"
if not exist "%FC%\bin\python.exe" (echo FreeCAD not found. Install FreeCAD 1.0 or set FREECAD_DIR & exit /b 1)
set "PYTHONPATH=%FC%\bin;%FC%\lib;%PYTHONPATH%"
"%FC%\bin\python.exe" %*

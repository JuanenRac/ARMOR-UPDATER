@echo off
REM ARMOR-UPDATER - build-test.bat
REM Same .venv setup as build.bat (the optional Qt Quick GUI needs
REM ".venv\Scripts\pythonw.exe" to exist), but non-mutating: no version
REM bump. GPL-3.0-or-later.
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
    if errorlevel 1 ( echo VENV CREATION FAILED. & pause & exit /b 1 )
)
call .venv\Scripts\activate.bat
if errorlevel 1 ( echo VENV ACTIVATION FAILED. & pause & exit /b 1 )

python -m pip install -e ".[dev,gui]"
if errorlevel 1 ( echo DEPENDENCY INSTALL FAILED. & pause & exit /b 1 )

call "%~dp0..\ARMOR-COMMON\scripts\armor-project.bat" build-test "%~dp0."
exit /b %ERRORLEVEL%

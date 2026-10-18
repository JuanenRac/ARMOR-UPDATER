@echo off
rem Keep the window open for people, never in automation (CI / HYDRA_UMC_CI).
set "KEEP_OPEN=pause"
if defined CI set "KEEP_OPEN=ver >nul"
if "%HYDRA_UMC_CI%"=="1" set "KEEP_OPEN=ver >nul"
REM ARMOR-UPDATER - build.bat
REM Unlike every other A.R.M.O.R. repository's build.bat, this one creates
REM and uses its own project-local .venv first: the optional Qt Quick GUI
REM (run-gui.vbs) launches ".venv\Scripts\pythonw.exe" directly, by design,
REM so there is a completely console-free double-click entry point - it
REM needs that venv to actually exist. GPL-3.0-or-later.
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
    if errorlevel 1 ( echo VENV CREATION FAILED. & %KEEP_OPEN% & exit /b 1 )
)
call .venv\Scripts\activate.bat
if errorlevel 1 ( echo VENV ACTIVATION FAILED. & %KEEP_OPEN% & exit /b 1 )

python -m pip install -e ".[dev,gui]"
if errorlevel 1 ( echo DEPENDENCY INSTALL FAILED. & %KEEP_OPEN% & exit /b 1 )

call "%~dp0..\ARMOR-COMMON\scripts\armor-project.bat" build "%~dp0."
exit /b %ERRORLEVEL%

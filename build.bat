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

REM The py launcher makes the venv when there is one (the python first on the PATH may be a stripped one, like the one of ESP-IDF, whose venv has no activate script),
REM and the venv is put first on the PATH instead of being activated.
set "PYMAKE=python"
where py >nul 2>nul && set "PYMAKE=py -3"
if not exist .venv\Scripts\python.exe (
    %PYMAKE% -m venv .venv
    if errorlevel 1 ( echo VENV CREATION FAILED. & %KEEP_OPEN% & exit /b 1 )
)
if not exist .venv\Scripts\python.exe ( echo THE VENV HAS NO PYTHON: delete the .venv folder and run this again. & %KEEP_OPEN% & exit /b 1 )
set "VIRTUAL_ENV=%CD%\.venv"
set "PATH=%CD%\.venv\Scripts;%PATH%"

python -m pip install -e ".[dev,gui]"
if errorlevel 1 ( echo DEPENDENCY INSTALL FAILED. & %KEEP_OPEN% & exit /b 1 )

call "%~dp0..\ARMOR-COMMON\scripts\armor-project.bat" build "%~dp0."
exit /b %ERRORLEVEL%

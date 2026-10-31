@echo off
rem Keep the window open for people, never in automation (CI / HYDRA_UMC_CI).
set "KEEP_OPEN=pause"
if defined CI set "KEEP_OPEN=ver >nul"
if "%HYDRA_UMC_CI%"=="1" set "KEEP_OPEN=ver >nul"
REM ARMOR-UPDATER - build-test.bat
REM Same .venv setup as build.bat (the optional Qt Quick GUI needs
REM ".venv\Scripts\pythonw.exe" to exist), but non-mutating: no version
REM bump. GPL-3.0-or-later.
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
    if errorlevel 1 ( echo VENV CREATION FAILED. & %KEEP_OPEN% & exit /b 1 )
)
call .venv\Scripts\activate.bat
if errorlevel 1 ( echo VENV ACTIVATION FAILED. & %KEEP_OPEN% & exit /b 1 )

python -m pip install -e ".[dev,gui]"
if errorlevel 1 ( echo DEPENDENCY INSTALL FAILED. & %KEEP_OPEN% & exit /b 1 )

python -m ruff check src tests
if errorlevel 1 ( echo LINT FAILED. & %KEEP_OPEN% & exit /b 1 )

python -m mypy
if errorlevel 1 ( echo TYPE CHECK FAILED. & %KEEP_OPEN% & exit /b 1 )

call "%~dp0..\ARMOR-COMMON\scripts\armor-project.bat" build-test "%~dp0."
exit /b %ERRORLEVEL%

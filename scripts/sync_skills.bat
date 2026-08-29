@echo off
REM .agents/skills/ (canon) -> .claude/skills/ (mirror) directory mirror.
REM robocopy /MIR = full mirror based on canon (removes items absent from canon).
REM Always edit .agents/skills/ only, then run this script.
setlocal
cd /d "%~dp0.."

set "CANON=.agents\skills"
set "MIRROR=.claude\skills"

if not exist "%CANON%\" (
    echo [sync-skills] ERROR: canon %CANON% not found
    exit /b 1
)

REM robocopy exit codes: 0-7 = OK (copied/identical), 8+ = error.
robocopy "%CANON%" "%MIRROR%" /MIR /NFL /NDL /NJH /NJS /NC /NS >nul
if errorlevel 8 (
    echo [sync-skills] ERROR: robocopy failed ^(exit %errorlevel%^)
    exit /b 1
)

echo [sync-skills] %CANON% -^> %MIRROR% mirror OK.
endlocal
exit /b 0

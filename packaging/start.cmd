@echo off
rem P7M Manager - inspect signed .p7m containers and extract what they carry
rem Copyright (C) 2026 Marco Lombardo
rem SPDX-License-Identifier: AGPL-3.0-or-later
rem
rem Start P7M Manager, after checking that the executable is the one this
rem archive was built with.
rem
rem The archive ships P7MManager.exe.sha256 beside the executable. This script
rem recomputes that digest with PowerShell's Get-FileHash and compares. What
rem that catches is a truncated download, a half-finished unpack, a disk that
rem has started rotting -- damage, which is the failure that actually happens
rem to people.
rem
rem Get-FileHash and not certutil, which is one line shorter and also part of
rem Windows: certutil is on every living-off-the-land list there is, because
rem its -decode and -urlcache options are how a good deal of real malware
rem fetches its payload. Endpoint security does not read the arguments and
rem conclude that this one is only hashing.
rem
rem What it does NOT catch is tampering. The checksum travels inside the same
rem zip as the file it describes, so anyone able to alter the executable could
rem alter the checksum in the same breath. The check worth doing against that
rem is on the zip itself, using the .sha256 published as a separate release
rem asset -- it reaches you by a different path, which is the whole point.
rem
rem This script does not remove the SmartScreen warning and cannot: only a
rem code-signing certificate does that.

setlocal

set "APP=P7M Manager"
set "EXE_NAME=P7MManager.exe"
rem %~dp0 is the folder holding this script, with a trailing backslash. Not
rem the current directory: a double-click from Explorer can start anywhere.
set "HERE=%~dp0"
set "EXE=%HERE%%EXE_NAME%"
set "SUMS=%EXE%.sha256"

if not exist "%EXE%" (
    echo %APP%: no executable at "%EXE%" 1>&2
    echo The archive did not unpack completely. Unpack it again. 1>&2
    if not defined CI pause
    exit /b 1
)

rem An escape hatch that is deliberately explicit. Somebody who has patched the
rem executable on purpose should be able to run it; somebody who has not should
rem never see this path taken silently.
if "%P7MMANAGER_SKIP_VERIFY%"=="1" (
    echo %APP%: checksum verification skipped ^(P7MMANAGER_SKIP_VERIFY=1^) 1>&2
    goto :launch
)

if not exist "%SUMS%" (
    echo %APP%: %EXE_NAME%.sha256 is missing, starting without checking 1>&2
    goto :launch
)

rem The file is in the format sha256sum -c reads: "<hex>  <name>". Cleared
rem first: setlocal copies the caller's environment, and a variable of either
rem name already in it would win the `if not defined`.
set "EXPECTED="
set "ACTUAL="
for /f "usebackq tokens=1" %%H in ("%SUMS%") do (
    if not defined EXPECTED set "EXPECTED=%%H"
)

rem No PowerShell means no check. That is the answer this script already gives
rem when the .sha256 is missing: say so, and start the program anyway. A
rem verification step that refused to launch when it could not run would turn
rem an unusual Windows into a broken download.
where powershell > nul 2>&1
if errorlevel 1 (
    echo %APP%: PowerShell is not available, starting without checking 1>&2
    goto :launch
)

rem The path travels in a variable rather than inside the quoted -Command, so a
rem folder name with a space in it -- and this one has a space in it -- cannot
rem break the PowerShell that receives it.
set "_HASH_TARGET=%EXE%"
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -LiteralPath ${env:_HASH_TARGET} -Algorithm SHA256).Hash" 2^>nul`) do (
    if not defined ACTUAL set "ACTUAL=%%H"
)

if not defined ACTUAL (
    echo %APP%: could not hash the executable, starting without checking 1>&2
    goto :launch
)
if not defined EXPECTED (
    echo %APP%: %EXE_NAME%.sha256 is empty, starting without checking 1>&2
    goto :launch
)

rem /i because Get-FileHash returns upper case and sha256sum writes lower.
if /i not "%ACTUAL%"=="%EXPECTED%" (
    echo %APP%: the executable does not match %EXE_NAME%.sha256. 1>&2
    echo   expected %EXPECTED% 1>&2
    echo   found    %ACTUAL% 1>&2
    echo. 1>&2
    echo Unpack the archive again from a fresh download. If it still does not 1>&2
    echo match, check the zip's own .sha256 from the release page before 1>&2
    echo running anything out of it. 1>&2
    if not defined CI pause
    exit /b 1
)

:launch
rem With arguments -- --version, --self-check, --cli -- run in the foreground,
rem so whatever is printed lands in the console the caller is watching.
if not "%~1"=="" goto :foreground

rem With none, which is what a double-click sends, this console has one job
rem left: stay up while the program starts, and say what it is waiting for. A
rem frozen application is not quick off the mark -- Windows scans every file
rem before it will let any of them load -- and a console that vanishes
rem instantly leaves nothing on screen for that wait.
where powershell > nul 2>&1
if errorlevel 1 goto :handoff

echo Starting %APP%...
echo.
echo The first launch is the slow one: Windows checks every file before it
echo will run any of them. This window closes by itself as soon as %APP% is
echo on screen.

set "_LAUNCH_TARGET=%EXE%"
set "_LAUNCH_TIMEOUT=%P7MMANAGER_LAUNCH_TIMEOUT%"
if not defined _LAUNCH_TIMEOUT set "_LAUNCH_TIMEOUT=180"

rem What this waits for is a window, found by polling every process with the
rem program's image name until one of them has a main window handle. Watching
rem the name rather than the handle Start-Process returned covers a onedir and
rem a onefile build alike: a onefile bootloader never has a message loop, so
rem waiting on it would wait out the whole timeout while the window is already
rem up. Death is read from the returned process, which cannot race the first
rem poll the way a name lookup can.
powershell -NoProfile -Command "$target = ${env:_LAUNCH_TARGET}; $name = [IO.Path]::GetFileNameWithoutExtension($target); $p = Start-Process -FilePath $target -PassThru; $deadline = (Get-Date).AddSeconds([int]${env:_LAUNCH_TIMEOUT}); while ((Get-Date) -lt $deadline) { foreach ($proc in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) { if ($proc.MainWindowHandle -ne [IntPtr]::Zero) { exit 0 } }; if ($p.HasExited) { exit 4 }; Start-Sleep -Milliseconds 200 }; exit 3"
set "STATUS=%ERRORLEVEL%"

rem Past this point the program has been started, whatever PowerShell went on
rem to report. Nothing below may start it a second time.
if "%STATUS%"=="0" exit /b 0

if "%STATUS%"=="4" (
    echo. 1>&2
    echo %APP% stopped before it opened a window. 1>&2
    if not defined CI pause
    exit /b 1
)

echo. 1>&2
echo %APP% has not opened a window yet. It may still be starting. 1>&2
if not defined CI pause
exit /b 0

:handoff
start "" "%EXE%"
exit /b 0

:foreground
"%EXE%" %*
exit /b %ERRORLEVEL%

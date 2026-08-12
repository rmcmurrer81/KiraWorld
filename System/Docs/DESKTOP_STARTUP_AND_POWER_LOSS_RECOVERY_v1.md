# Desktop Startup And Power Loss Recovery v1

This system is for the new desktop after the first text-only Kira launch path is stable.

Goal:

```text
Windows turns on
startup recovery check runs
required Kira/Lisa files are checked
dirty shutdown or power outage is detected
Kira launches only if checks pass
```

## Startup Command

Use this from the project root:

```powershell
py tools\startup_recovery_check.py --run-command-checks
```

For the Windows login wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File tools\windows_start_kira_on_login.ps1
```

Do not install the Windows auto-start task until:

```text
Kira text-only local model works
readiness passes
desktop model readiness passes
Robert has watched several clean launches
```

## What It Checks

The startup recovery check verifies:

```text
startup recovery config validates
required launch files exist
Kira and Lisa roots exist
TemporaryAI root exists
memory, relationship, privacy, daily-life, inner-life roots exist
watched JSON files parse
system flags are still safe
readiness check passes
desktop model readiness passes
```

If the previous run was not marked as cleanly shut down, it also treats the launch as a recovery event and runs deeper checks.

## Power Outage Behavior

When Kira is launched through `tools\windows_start_kira_on_login.ps1`, the wrapper marks:

```text
active_session=true
```

If the program exits normally, it marks:

```text
active_session=false
last_clean_shutdown_at=<time>
```

If the power goes out, Windows crashes, or the computer is forced off, the clean shutdown mark never happens. On the next boot, the checker sees the previous active session and reports:

```text
unclean_previous_session=true
```

Then it slows down before launch.

## Safety Rules

After an unclean shutdown:

```text
do not promote memories automatically
do not activate Lisa automatically
do not activate a TemporaryAI automatically
do not enable voice/avatar/world just because Windows restarted
do not continue if readiness fails
```

Fix the first failing check, rerun startup recovery, then launch.

## Windows Auto-Start

The repo includes the login wrapper, but the repo does not install it automatically. On the new desktop, after several stable manual launches, Robert or Codex can add it to Windows Startup or a scheduled task.

Recommended first mode:

```text
start at login
text-only Kira
checks before launch
block launch if checks fail
Lisa manual only
TemporaryAI manual only
```

This gives Kira a reliable morning wake-up path without risking corrupted files after a power outage.

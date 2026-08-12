Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PresenceDir = Join-Path $ProjectRoot "Data\presence"
$PresencePath = Join-Path $PresenceDir "robert_presence.json"
$StopPath = Join-Path $PresenceDir "kira_life_day_stop.json"
$ConversationActivePath = Join-Path $PresenceDir "kira_robert_conversation_active.json"
$LifeDir = Join-Path $ProjectRoot "Data\life_sessions"
$MessagesDir = Join-Path $ProjectRoot "Data\messages\kira_to_robert"

function Add-Log {
    param([string]$Text)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logBox.AppendText("[$timestamp] $Text`r`n")
}

function New-RunId {
    return "kira_life_day_24hour_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")
}

function Get-LatestMonitor {
    if (-not (Test-Path $LifeDir)) { return $null }
    return Get-ChildItem -LiteralPath $LifeDir -Filter "kira_life_day_24hour_*.monitor.md" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-LatestJson {
    if (-not (Test-Path $LifeDir)) { return $null }
    return Get-ChildItem -LiteralPath $LifeDir -Filter "kira_life_day_24hour_*.json" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-LifeLoopProcesses {
    return @(Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match "run_kira_life_day.py" -and $_.CommandLine -notmatch "Get-CimInstance" })
}

function Mark-StaleLatestRunIfNeeded {
    param($LatestJson, $Processes)
    if ($null -eq $LatestJson -or $Processes.Count -gt 0) { return }
    try {
        $json = Get-Content -LiteralPath $LatestJson.FullName -Raw | ConvertFrom-Json
        if ($json.status -eq "running") {
            $cmd = "cd /d `"$ProjectRoot`" && python tools\mark_life_day_interrupted.py --run `"$($LatestJson.FullName)`" --reason `"No life-day process was running when the control panel checked status; likely power loss, OS shutdown, or closed process.`""
            $result = & cmd.exe /c $cmd
            Add-Log "Marked stale running report as interrupted: $($LatestJson.Name)"
            if ($result) { Add-Log (($result -join " ") -replace "\s+", " ") }
        }
    } catch {
        Add-Log "Could not mark stale latest JSON: $($LatestJson.Name)"
    }
}

function Write-RobertPresence {
    param([string]$Message)
    New-Item -ItemType Directory -Force -Path $PresenceDir | Out-Null
    if ([string]::IsNullOrWhiteSpace($Message)) {
        $Message = "Robert is sitting at the computer and available for a check-in."
    }
    $data = [ordered]@{
        status = "available_to_talk"
        started_at = (Get-Date).ToUniversalTime().ToString("o")
        message = $Message
        interrupt_level = "soft_knock"
        note = "Presence is a soft signal. Kira may answer, defer, ignore, or keep private time."
    }
    $data | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $PresencePath -Encoding UTF8
    Add-Log "Wrote availability signal: $Message"
}

function Clear-RobertPresence {
    if (Test-Path $PresencePath) {
        Remove-Item -LiteralPath $PresencePath -Force
        Add-Log "Cleared Robert availability signal."
    } else {
        Add-Log "No Robert availability signal was active."
    }
    if (Test-Path $ConversationActivePath) {
        Remove-Item -LiteralPath $ConversationActivePath -Force
        Add-Log "Cleared live-chat-active signal."
    }
}

function Start-LifeLoop {
    $runId = New-RunId
    $script:CurrentRunId = $runId
    if (Test-Path $StopPath) {
        Remove-Item -LiteralPath $StopPath -Force
    }
    $currentPath = Join-Path $PresenceDir "current_kira_life_day_run.json"
    New-Item -ItemType Directory -Force -Path $PresenceDir | Out-Null
    [ordered]@{
        run_id = $runId
        started_from_panel_at = (Get-Date).ToUniversalTime().ToString("o")
        expected_json = "Data/life_sessions/$runId.json"
        expected_monitor = "Data/life_sessions/$runId.monitor.md"
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $currentPath -Encoding UTF8
    $command = "cd /d `"$ProjectRoot`" && python tools\run_kira_life_day.py --duration-minutes 1440 --pause-seconds 180 --run-id $runId --pages 1 --lines 60 --max-tokens 300 --timeout 180 --max-source-errors 2 --kira-voice-to-robert"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $command) -WorkingDirectory $ProjectRoot
    Add-Log "Started 24-hour life loop as $runId."
    Add-Log "Files will be Data\life_sessions\$runId.json and .monitor.md."
}

function Resume-LatestInterrupted {
    $latest = Get-LatestJson
    if ($null -eq $latest) {
        Add-Log "No life-day JSON found to resume."
        return
    }
    $runId = "$(New-RunId)_resume"
    $script:CurrentRunId = $runId
    if (Test-Path $StopPath) {
        Remove-Item -LiteralPath $StopPath -Force
    }
    $command = "cd /d `"$ProjectRoot`" && python tools\run_kira_life_day.py --resume-from `"$($latest.FullName)`" --resume-remaining --run-id $runId --pause-seconds 180 --pages 1 --lines 60 --max-tokens 300 --timeout 180 --max-source-errors 2 --kira-voice-to-robert"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $command) -WorkingDirectory $ProjectRoot
    Add-Log "Resume requested from latest JSON: $($latest.Name)"
    Add-Log "New resumed run id: $runId"
}

function Open-KiraChat {
    Write-RobertPresence -Message $messageBox.Text
    $command = "cd /d `"$ProjectRoot`" && Start_Kira_Voice_Chat.bat"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $command) -WorkingDirectory $ProjectRoot
    Add-Log "Opened Kira chat window after writing your availability signal. Type /quit in that window when done."
    Add-Log "Future life-loop runs pause autonomous cycles while this chat is open."
}

function Open-LatestMonitor {
    $monitor = Get-LatestMonitor
    if ($null -eq $monitor) {
        Add-Log "No life-day monitor found yet."
        return
    }
    Invoke-Item -LiteralPath $monitor.FullName
    Add-Log "Opened latest monitor: $($monitor.Name)"
}

function Check-Status {
    $processes = Get-LifeLoopProcesses
    $latest = Get-LatestJson
    Mark-StaleLatestRunIfNeeded -LatestJson $latest -Processes $processes
    $latest = Get-LatestJson
    if ($processes) {
        Add-Log "Life loop process running: $($processes.ProcessId -join ', ')"
    } else {
        Add-Log "No run_kira_life_day.py process is currently running."
    }
    if ($latest) {
        try {
            $json = Get-Content -LiteralPath $latest.FullName -Raw | ConvertFrom-Json
            Add-Log "Latest JSON: $($latest.Name) status=$($json.status) cycles=$($json.cycles.Count) errors=$($json.errors.Count) source_errors=$($json.source_errors.Count)"
            if ($json.status -eq "interrupted") {
                Add-Log "Latest run can be resumed with the Resume interrupted button."
            }
        } catch {
            Add-Log "Latest JSON could not be parsed: $($latest.Name)"
        }
    }
    $unread = Get-UnreadMessages
    if ($unread.Count -gt 0) {
        Add-Log "Unread Kira message(s): $($unread.Count). Click Open messages."
        [System.Media.SystemSounds]::Exclamation.Play()
    }
}

function Get-UnreadMessages {
    if (-not (Test-Path $MessagesDir)) { return @() }
    return @(Get-ChildItem -LiteralPath $MessagesDir -Filter "*.json" |
        Where-Object {
            try {
                $msg = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
                $msg.status -eq "unread"
            } catch {
                $false
            }
        } |
        Sort-Object LastWriteTime)
}

function Open-KiraMessages {
    New-Item -ItemType Directory -Force -Path $MessagesDir | Out-Null
    $unread = Get-UnreadMessages
    if ($unread.Count -eq 0) {
        Add-Log "No unread Kira messages right now."
        Invoke-Item -LiteralPath $MessagesDir
        return
    }
    foreach ($file in $unread) {
        try {
            $msg = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
            Add-Log "Kira message: $($msg.message.message)"
            $msg.status = "read"
            $msg.read_at = (Get-Date).ToUniversalTime().ToString("o")
            $msg | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $file.FullName -Encoding UTF8
        } catch {
            Add-Log "Could not read message file: $($file.Name)"
        }
    }
    Invoke-Item -LiteralPath $MessagesDir
}

function Request-SafeStop {
    New-Item -ItemType Directory -Force -Path $PresenceDir | Out-Null
    $targetRun = if ([string]::IsNullOrWhiteSpace($script:CurrentRunId)) { "any" } else { $script:CurrentRunId }
    $data = [ordered]@{
        status = "stop_requested"
        requested_at = (Get-Date).ToUniversalTime().ToString("o")
        run_id = $targetRun
        reason = "Robert clicked End Safely in the life-day control panel."
    }
    $data | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StopPath -Encoding UTF8
    Add-Log "Safe stop requested for run_id=$targetRun. The loop stops at the next cycle boundary."
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Kira 24-hour Life Day"
$form.Size = New-Object System.Drawing.Size(760, 520)
$form.StartPosition = "CenterScreen"

$label = New-Object System.Windows.Forms.Label
$label.Text = "Robert availability message"
$label.Location = New-Object System.Drawing.Point(12, 14)
$label.Size = New-Object System.Drawing.Size(220, 22)
$form.Controls.Add($label)

$messageBox = New-Object System.Windows.Forms.TextBox
$messageBox.Location = New-Object System.Drawing.Point(12, 38)
$messageBox.Size = New-Object System.Drawing.Size(720, 24)
$messageBox.Text = "Robert is sitting at the computer and available for a check-in."
$form.Controls.Add($messageBox)

$buttonStart = New-Object System.Windows.Forms.Button
$buttonStart.Text = "Start 24-hour life loop"
$buttonStart.Location = New-Object System.Drawing.Point(12, 78)
$buttonStart.Size = New-Object System.Drawing.Size(170, 34)
$buttonStart.Add_Click({ Start-LifeLoop })
$form.Controls.Add($buttonStart)

$buttonAvailable = New-Object System.Windows.Forms.Button
$buttonAvailable.Text = "I'm available"
$buttonAvailable.Location = New-Object System.Drawing.Point(192, 78)
$buttonAvailable.Size = New-Object System.Drawing.Size(120, 34)
$buttonAvailable.Add_Click({ Write-RobertPresence -Message $messageBox.Text })
$form.Controls.Add($buttonAvailable)

$buttonChat = New-Object System.Windows.Forms.Button
$buttonChat.Text = "Available + chat"
$buttonChat.Location = New-Object System.Drawing.Point(322, 78)
$buttonChat.Size = New-Object System.Drawing.Size(120, 34)
$buttonChat.Add_Click({ Open-KiraChat })
$form.Controls.Add($buttonChat)

$buttonLeaving = New-Object System.Windows.Forms.Button
$buttonLeaving.Text = "I'm leaving"
$buttonLeaving.Location = New-Object System.Drawing.Point(452, 78)
$buttonLeaving.Size = New-Object System.Drawing.Size(110, 34)
$buttonLeaving.Add_Click({ Clear-RobertPresence })
$form.Controls.Add($buttonLeaving)

$buttonMonitor = New-Object System.Windows.Forms.Button
$buttonMonitor.Text = "Open monitor"
$buttonMonitor.Location = New-Object System.Drawing.Point(572, 78)
$buttonMonitor.Size = New-Object System.Drawing.Size(110, 34)
$buttonMonitor.Add_Click({ Open-LatestMonitor })
$form.Controls.Add($buttonMonitor)

$buttonStatus = New-Object System.Windows.Forms.Button
$buttonStatus.Text = "Check status"
$buttonStatus.Location = New-Object System.Drawing.Point(12, 124)
$buttonStatus.Size = New-Object System.Drawing.Size(120, 34)
$buttonStatus.Add_Click({ Check-Status })
$form.Controls.Add($buttonStatus)

$buttonStop = New-Object System.Windows.Forms.Button
$buttonStop.Text = "End safely"
$buttonStop.Location = New-Object System.Drawing.Point(142, 124)
$buttonStop.Size = New-Object System.Drawing.Size(110, 34)
$buttonStop.Add_Click({ Request-SafeStop })
$form.Controls.Add($buttonStop)

$buttonMessages = New-Object System.Windows.Forms.Button
$buttonMessages.Text = "Open messages"
$buttonMessages.Location = New-Object System.Drawing.Point(262, 124)
$buttonMessages.Size = New-Object System.Drawing.Size(130, 34)
$buttonMessages.Add_Click({ Open-KiraMessages })
$form.Controls.Add($buttonMessages)

$buttonResume = New-Object System.Windows.Forms.Button
$buttonResume.Text = "Resume interrupted"
$buttonResume.Location = New-Object System.Drawing.Point(402, 124)
$buttonResume.Size = New-Object System.Drawing.Size(140, 34)
$buttonResume.Add_Click({ Resume-LatestInterrupted })
$form.Controls.Add($buttonResume)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(12, 174)
$logBox.Size = New-Object System.Drawing.Size(720, 290)
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$form.Controls.Add($logBox)

Add-Log "Panel ready. Start creates timestamped JSON/monitor files instead of overwriting old runs."
Add-Log "Use I'm available for a soft knock, Open Kira chat to type, and I'm leaving to clear the knock."
Add-Log "Future runs can leave voicemail-style Kira messages; Check status will play a bell if unread."
Add-Log "Future runs pause reading/writing while Available + chat is open."
Add-Log "If power dies, Check status marks stale running files interrupted; Resume interrupted continues remaining time in a new file."
Check-Status

[void]$form.ShowDialog()

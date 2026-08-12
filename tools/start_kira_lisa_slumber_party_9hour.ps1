param(
    [string]$RunId = "",
    [double]$PauseSeconds = 45
)

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

$argsList = @(
    "tools\run_kira_lisa_slumber_party.py",
    "--backend", "ollama",
    "--duration-minutes", "540",
    "--pause-seconds", "$PauseSeconds",
    "--group-reading-every", "4",
    "--max-tokens", "260"
)

if ($RunId -ne "") {
    $argsList += @("--run-id", $RunId)
}

python @argsList

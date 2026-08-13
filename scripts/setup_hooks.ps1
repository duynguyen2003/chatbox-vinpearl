# Install git pre-push hook for AI log submission (Windows PowerShell).
# Run once after cloning: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1

$ErrorActionPreference = 'Stop'

$RepoRoot = (& git rev-parse --show-toplevel 2>$null)
if (-not $RepoRoot) {
    throw "[ai-log] Not inside a Git working tree. Run this script from the repository."
}

$RepoRoot = $RepoRoot.Trim()
$HookDir = Join-Path $RepoRoot '.git\hooks'
$HookFile = Join-Path $HookDir 'pre-push'

if (-not (Test-Path $HookDir)) {
    New-Item -ItemType Directory -Path $HookDir -Force | Out-Null
}

# IMPORTANT FOR WINDOWS POWERSHELL 5.1:
# Set-Content -Encoding UTF8 writes a UTF-8 BOM. A BOM before "#!" can make
# Git for Windows fail to execute the hook with:
#   cannot spawn .git/hooks/pre-push: No such file or directory
# Write the bash hook as UTF-8 *without BOM* and force LF line endings.
$HookBody = @'
#!/usr/bin/env bash
# Pre-push: sweep recent Antigravity / Gemini prompts, then submit AI logs.
# AI-log failures are reported but must not block the Git push.
set +e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
  echo "[ai-log] Could not resolve repository root; skipping AI-log hook." >&2
  exit 0
fi

cd "$ROOT" || exit 0

bash "$ROOT/scripts/_pyrun.sh" "$ROOT/scripts/log_antigravity.py" --auto
SCAN_STATUS=$?
if [ $SCAN_STATUS -ne 0 ]; then
  echo "[ai-log] Prompt sweep failed (exit $SCAN_STATUS); continuing push." >&2
fi

bash "$ROOT/scripts/_pyrun.sh" "$ROOT/scripts/submit_log.py"
SUBMIT_STATUS=$?
if [ $SUBMIT_STATUS -ne 0 ]; then
  echo "[ai-log] Log submission failed (exit $SUBMIT_STATUS); logs remain local." >&2
fi

exit 0
'@

$HookBody = $HookBody -replace "`r`n", "`n"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($HookFile, $HookBody, $Utf8NoBom)

# Verify the hook really starts with '#!' and has no UTF-8 BOM.
$Bytes = [System.IO.File]::ReadAllBytes($HookFile)
if ($Bytes.Length -lt 2 -or $Bytes[0] -ne 35 -or $Bytes[1] -ne 33) {
    throw "[ai-log] pre-push hook encoding is invalid; expected '#!' as the first bytes."
}
if ($Bytes.Length -ge 3 -and $Bytes[0] -eq 239 -and $Bytes[1] -eq 187 -and $Bytes[2] -eq 191) {
    throw "[ai-log] pre-push hook unexpectedly contains a UTF-8 BOM."
}

$AiLogDir = Join-Path $RepoRoot '.ai-log'
if (-not (Test-Path $AiLogDir)) {
    New-Item -ItemType Directory -Path $AiLogDir | Out-Null
}
$GitKeep = Join-Path $AiLogDir '.gitkeep'
if (-not (Test-Path $GitKeep)) {
    New-Item -ItemType File -Path $GitKeep | Out-Null
}

Write-Host "[ai-log] Git pre-push hook installed (UTF-8 no BOM, LF)."
Write-Host "[ai-log] Setup complete. Configure AI_LOG_SERVER and AI_LOG_API_KEY in your local .env file."

param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repoRoot
try {
  & (Join-Path $repoRoot '.venv\Scripts\python.exe') -X utf8 -m uacf @Arguments
  exit $LASTEXITCODE
} finally { Pop-Location }

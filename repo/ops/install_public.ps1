param([Parameter(Mandatory=$true)][string]$Root,[string]$Python='python')
$ErrorActionPreference='Stop'
$repoRoot=Join-Path ([IO.Path]::GetFullPath($Root)) 'repo'
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'requirements.lock'))) { throw 'Put the reviewed source in ROOT/repo first' }
$runtime=Join-Path $repoRoot '.venv\Scripts\python.exe'
& $Python -c 'import sys; assert sys.version_info[:2]==(3,11), "Locked dependencies require Python 3.11"'
if ($LASTEXITCODE -ne 0) { throw 'Unsupported Python' }
if (-not (Test-Path -LiteralPath $runtime)) { & $Python -m venv (Join-Path $repoRoot '.venv'); if ($LASTEXITCODE -ne 0) { throw 'venv failed' } }
& $runtime -m pip install --index-url https://pypi.org/simple --require-hashes -r (Join-Path $repoRoot 'requirements.lock')
if ($LASTEXITCODE -ne 0) { throw 'Dependency rebuild failed; preserve any existing data' }
Push-Location -LiteralPath $repoRoot
try {
 if (-not (Test-Path -LiteralPath (Join-Path $Root 'data\core.sqlite'))) {
  & $runtime -X utf8 -m uacf --root $Root --json init --current-schema
  if ($LASTEXITCODE -ne 0) { throw 'Initialization failed' }
 }
 & $runtime -X utf8 -m uacf --root $Root --json doctor
 if ($LASTEXITCODE -ne 0) { throw 'Integrity check failed' }
} finally { Pop-Location }
# No host configuration, autostart, Provider route, imported assets or model request.

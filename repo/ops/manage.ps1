param([ValidateSet('start','stop','status')][string]$Action='status', [string]$Root=(Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\','/')
$repoRoot = Join-Path $Root 'repo'
$deploymentPath = Join-Path $Root 'data\deployment.json'
if (Test-Path -LiteralPath $deploymentPath) {
  $deployment = Get-Content -LiteralPath $deploymentPath -Raw | ConvertFrom-Json
  $releaseBase = [IO.Path]::GetFullPath((Join-Path $Root 'data\releases')) + [IO.Path]::DirectorySeparatorChar
  $selectedRepo = [IO.Path]::GetFullPath($deployment.repo)
  if (-not $selectedRepo.StartsWith($releaseBase,[StringComparison]::OrdinalIgnoreCase)) { throw 'Deployment path outside registered release directory' }
  $repoRoot = $selectedRepo
}
$identityPath = Join-Path $Root 'data\service-identity.json'
$existingIdentity = if (Test-Path -LiteralPath $identityPath) { Get-Content -LiteralPath $identityPath -Raw | ConvertFrom-Json } else { $null }
$rootPattern='--root\s+"?'+[regex]::Escape($Root)+'"?\s+serve(?:\s|$)'
$ownedProcesses=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('-m uacf') -and ($_.CommandLine.Replace('/','\') -match $rootPattern) })
$isOwned=$ownedProcesses.Count -gt 0
if ($Action -eq 'status') {
  [pscustomobject]@{running=[bool]$isOwned; identity=$existingIdentity} | ConvertTo-Json -Depth 5
} elseif ($Action -eq 'stop') {
  # Exact normalized --root plus serve, never a prefix match into isolated roots
  # and never MCP or another Host. Include the venv launcher's paired process.
  foreach ($ownedProcess in $ownedProcesses) { Stop-Process -Id $ownedProcess.ProcessId -ErrorAction SilentlyContinue }
  [pscustomobject]@{stopped=[bool]$isOwned;dataPreserved=$true} | ConvertTo-Json
} elseif (-not $isOwned) {
  $pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
  $arguments = '-X utf8 -m uacf --root "'+$Root+'" serve'
  Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Root 'logs\service-stdout.log') -RedirectStandardError (Join-Path $Root 'logs\service-stderr.log') | Out-Null
  [pscustomobject]@{startRequested=$true;mode='single managed local process; embedded bounded worker'} | ConvertTo-Json
} else { [pscustomobject]@{alreadyRunning=$true} | ConvertTo-Json }

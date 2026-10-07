param([string]$Root=(Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),[switch]$CheckOnly,[ValidateSet('none','codex','pi','dsh')][string]$HostTarget='none',[string]$HostHome)
$ErrorActionPreference='Stop'
$Root=[IO.Path]::GetFullPath($Root)
$repoRoot=Join-Path $Root 'repo'
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'requirements.lock'))) { throw 'Extract the package with its repo directory intact / 请保持压缩包中的repo目录结构' }
function Find-UacfPython {
 $candidates=@((Join-Path $repoRoot '.venv\Scripts\python.exe'),(Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'))
 $pyLauncher=Get-Command py -ErrorAction SilentlyContinue
 if ($pyLauncher) { $found=& $pyLauncher.Source -3.11 -c 'import sys; print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0) { $candidates+=([string]$found).Trim() } }
 $pythonCommand=Get-Command python -ErrorAction SilentlyContinue
 if ($pythonCommand -and $pythonCommand.Source -notlike '*WindowsApps*') { $candidates+=$pythonCommand.Source }
 foreach($candidate in $candidates) {
  if (Test-Path -LiteralPath $candidate) {
   $version=& $candidate -c 'import sys; print(str(sys.version_info.major)+chr(46)+str(sys.version_info.minor))' 2>$null
   if ($LASTEXITCODE -eq 0 -and ([string]$version).Trim() -eq '3.11') { return $candidate }
  }
 }
 return $null
}
$pythonPath=Find-UacfPython
if ($CheckOnly) {
 [pscustomobject]@{root=$Root;python311Found=[bool]$pythonPath;python=$pythonPath;installNeeded=(-not (Test-Path -LiteralPath (Join-Path $repoRoot '.venv\Scripts\python.exe')));providerCalls=0;hostConfigChanged=$false;plan='Reuse Python 3.11, or install official Python via WinGet; hashed PyPI dependencies; create only a new empty store; local browser'} | ConvertTo-Json
 exit 0
}
if (-not $pythonPath) {
 $winget=Get-Command winget -ErrorAction SilentlyContinue
 if (-not $winget) { throw 'Python 3.11 and WinGet are unavailable. Install Python from python.org and click again / 缺少Python与WinGet，请安装官方Python后再次点击' }
 Write-Host 'Installing official Python 3.11 for this user. Review any installer/source agreement prompts / 正在为当前用户安装官方Python，请阅读原生安装器的协议提示'
 & $winget.Source install --id Python.Python.3.11 --exact --source winget --scope user
 if ($LASTEXITCODE -ne 0) { throw 'Python installation did not complete; data preserved / Python安装未完成，数据保留' }
 $pythonPath=Find-UacfPython
 if (-not $pythonPath) { throw 'Python not found after installation; reopen the launcher / 请重新打开启动入口以刷新环境' }
}
& (Join-Path $PSScriptRoot 'install_public.ps1') -Root $Root -Python $pythonPath
if ($LASTEXITCODE -ne 0) { throw 'UACF preparation failed; data preserved' }
$runtime=Join-Path $repoRoot '.venv\Scripts\python.exe'
if ($HostTarget -ne 'none') {
 $hostArguments=@('-X','utf8',(Join-Path $PSScriptRoot 'install_host.py'),'--root',$Root,'--host',$HostTarget,'--install')
 if ($HostHome) { $hostArguments+=@('--home',$HostHome) }
 & $runtime @hostArguments
 if ($LASTEXITCODE -ne 0) { throw 'Host setup failed; inspect the preserving backup receipt / 宿主安装失败，请查看备份回执' }
}
& $runtime -X utf8 (Join-Path $PSScriptRoot 'open_library.py') --root $Root
if ($LASTEXITCODE -ne 0) { throw 'Local browser entry failed; inspect the message above / 本机入口未打开，请查看上方原因' }

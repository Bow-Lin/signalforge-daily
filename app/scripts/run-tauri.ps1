param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("dev", "build")]
  [string] $Mode
)

$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
if (Test-Path $cargoBin) {
  $env:PATH = "$cargoBin;$env:PATH"
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$vsDevCmd = $null
if (Test-Path $vswhere) {
  $installPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  if ($installPath) {
    $candidate = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
    if (Test-Path $candidate) {
      $vsDevCmd = $candidate
    }
  }
}

if ($null -eq $vsDevCmd) {
  throw "Visual Studio C++ Build Tools were not found. Install Microsoft.VisualStudio.2022.BuildTools with the VC tools workload."
}

$tauriCommand = if ($Mode -eq "dev") { "npx tauri dev" } else { "npx tauri build" }
$cmd = "call `"$vsDevCmd`" -arch=x64 && npm run sidecar:build && $tauriCommand"

Push-Location $appDir
try {
  & cmd.exe /d /s /c $cmd
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
}

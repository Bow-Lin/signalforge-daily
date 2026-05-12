$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarDir = Join-Path $scriptDir "digest-sidecar"
$binaryDir = Join-Path (Split-Path -Parent $scriptDir) "binaries"
$targetTriple = "x86_64-pc-windows-msvc"
$cargo = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"

New-Item -ItemType Directory -Force $binaryDir | Out-Null
Push-Location $sidecarDir
try {
  & $cargo build --release --target $targetTriple
} finally {
  Pop-Location
}

$source = Join-Path $sidecarDir "target\$targetTriple\release\digest-sidecar.exe"
$dest = Join-Path $binaryDir "digest-sidecar-$targetTriple.exe"
Copy-Item -Force $source $dest
Write-Output "Wrote $dest"

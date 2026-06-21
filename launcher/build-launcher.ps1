$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $PSScriptRoot "DragonBallLauncher.cs"
$outDir = Join-Path $PSScriptRoot "bin"
$outFile = Join-Path $outDir "DragonBallTikTokBattle.exe"
$configFile = Join-Path $outDir "launcher-config.txt"
$compiler = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

if (-not (Test-Path $compiler)) {
    $compiler = "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
}

if (-not (Test-Path $compiler)) {
    throw "No encuentro csc.exe para compilar el lanzador."
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

& $compiler `
    /nologo `
    /target:winexe `
    /platform:anycpu `
    /optimize+ `
    /reference:System.Windows.Forms.dll `
    /out:$outFile `
    $source

if ($LASTEXITCODE -ne 0) {
    throw "No se pudo compilar el lanzador."
}

if (-not (Test-Path $configFile)) {
    @(
        "url=https://dragonball-tiktok-battle.onrender.com/?obs=1&stream=band",
        "# Tamano horizontal recomendado para TikTok/OBS:",
        "width=1280",
        "height=720",
        "scale=1"
    ) | Set-Content -Path $configFile -Encoding ASCII
}

Write-Host "Lanzador creado:"
Write-Host $outFile

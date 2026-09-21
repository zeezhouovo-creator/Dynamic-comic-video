param(
  [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
if (-not $InstallRoot) {
  $InstallRoot = Join-Path $env:USERPROFILE ".codex\skills\dynamic-comic-video"
}

Write-Host "Preparing Dynamic-comic-video at $InstallRoot"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3.10+ is required." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js/npm is required for MP4 rendering." }

New-Item -ItemType Directory -Force $InstallRoot | Out-Null
python -m venv (Join-Path $InstallRoot ".venv")
$Py = Join-Path $InstallRoot ".venv\Scripts\python.exe"
& $Py -m pip install -r (Join-Path $RepoRoot "requirements.txt")

$Renderer = Join-Path $InstallRoot "assets\remotion"
Push-Location $Renderer
try { npm ci } finally { Pop-Location }

Write-Host "Ready. Skill: $InstallRoot"
Write-Host "Python: $Py"
Write-Host "Renderer: $Renderer"
Write-Host "Keep project stories, images, audio and MP4 files outside this shared skill folder."

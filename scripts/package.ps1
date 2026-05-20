# Build and zip Drawing Coach binary for Windows.
param()
$ErrorActionPreference = 'Stop'

$Env_Ref = $env:GITHUB_REF_NAME
if ($Env_Ref) {
    $Version = $Env_Ref.TrimStart('v')
} else {
    $Version = 'dev'
}

Write-Host "Building Drawing Coach $Version for windows..."

python scripts/build_version.py

pyinstaller --clean --noconfirm drawing_coach.spec

$ZipName = "drawing-coach-$Version-windows.zip"
Compress-Archive -Path dist\drawing-coach -DestinationPath $ZipName -Force

Write-Host "Created $ZipName"

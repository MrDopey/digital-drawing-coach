# Build and zip Drawing Coach binary for Windows.
param()
$ErrorActionPreference = 'Stop'

$BuildOutput = python scripts/build_version.py
$Version = ($BuildOutput | Select-String -Pattern '^Version set to: (.+)$').Matches.Groups[1].Value

Write-Host "Building Drawing Coach $Version for windows..."

pyinstaller --clean --noconfirm drawing_coach.spec

$ZipName = "drawing-coach-$Version-windows.zip"
Compress-Archive -Path dist\drawing-coach -DestinationPath $ZipName -Force

Write-Host "Created $ZipName"

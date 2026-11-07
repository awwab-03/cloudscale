# Builds build/thumbnailer (handler + Linux Pillow wheels) for the Lambda; Terraform zips it with archive_file.
# Usage: .\scripts\build_lambda.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "build\thumbnailer"
if (Test-Path $target) { Remove-Item -Recurse -Force $target }
New-Item -ItemType Directory -Force -Path $target | Out-Null

# Install Linux wheels from Windows (Lambda python3.12 runs on Amazon Linux 2023, glibc 2.34).
python -m pip install --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 `
    --only-binary=:all: --python-version 3.12 --implementation cp `
    --target $target --upgrade pillow
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Copy-Item (Join-Path $root "lambda\thumbnailer\handler.py") $target
Get-ChildItem $target -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Write-Host "Built $target"

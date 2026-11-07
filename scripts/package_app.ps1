# Zips app/ and uploads it to the artifacts bucket as app/app-<version>.zip.
# Usage: .\scripts\package_app.ps1 -Version 1.0.0
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$Region = "us-east-1"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $root "build"
New-Item -ItemType Directory -Force -Path $build | Out-Null
$zip = Join-Path $build "app-$Version.zip"
if (Test-Path $zip) { Remove-Item $zip }

# Zip the contents of app/ (no __pycache__), so app.py sits at the zip root.
$staging = Join-Path $build "app-staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
Copy-Item -Recurse (Join-Path $root "app") $staging
Get-ChildItem $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
# Use Python's zipfile (forward-slash entry names); Windows PowerShell Compress-Archive writes
# backslashes, which Linux unzip warns about.
python -c "import os, sys, zipfile; src, dst = sys.argv[1], sys.argv[2]; z = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED); [z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), src).replace(os.sep, '/')) for r, _, fs in os.walk(src) for f in fs]; z.close()" $staging $zip
if ($LASTEXITCODE -ne 0) { throw "zip failed" }
Remove-Item -Recurse -Force $staging

$account = aws sts get-caller-identity --query Account --output text
$bucket = "cloudscale-artifacts-$account"
aws s3 cp $zip "s3://$bucket/app/app-$Version.zip" --region $Region
Write-Host "Uploaded s3://$bucket/app/app-$Version.zip"

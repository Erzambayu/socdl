#Requires -Version 5.1
<#
.SYNOPSIS
    socdl installer for Windows.

.DESCRIPTION
    One-liner install:
        irm https://raw.githubusercontent.com/Erzambayu/socdl/main/install.ps1 | iex

    Strategy (in order of preference):
      1. Download the prebuilt socdl-windows-x64.exe from the latest GitHub Release
      2. Fall back to `pip install socdl` if a binary isn't available

    Installs to %LOCALAPPDATA%\socdl\bin and adds it to your user PATH.

.PARAMETER Method
    auto (default) | binary | pip

.PARAMETER Version
    Release tag to install, e.g. "v0.1.0". Default: latest.

.PARAMETER NoPath
    Don't modify the user PATH.
#>
[CmdletBinding()]
param(
    [ValidateSet("auto", "binary", "pip")]
    [string]$Method = "auto",
    [string]$Version = "",
    [switch]$NoPath
)

$ErrorActionPreference = "Stop"
$Repo    = "Erzambayu/socdl"
$BinName = "socdl.exe"
$InstallDir = Join-Path $env:LOCALAPPDATA "socdl\bin"

function Write-Info  ($m) { Write-Host "  $m" -ForegroundColor Cyan }
function Write-Ok    ($m) { Write-Host "  $m" -ForegroundColor Green }
function Write-Warn2 ($m) { Write-Host "  $m" -ForegroundColor Yellow }
function Write-Err2  ($m) { Write-Host "  $m" -ForegroundColor Red }

Write-Host ""
Write-Host "  socdl installer" -ForegroundColor Magenta
Write-Host "  ---------------" -ForegroundColor Magenta
Write-Host ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Test-Python {
    foreach ($cmd in @("python", "py")) {
        try {
            $v = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0) { return $cmd }
        } catch { }
    }
    return $null
}

function Get-LatestTag {
    try {
        $r = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" `
                               -Headers @{ "User-Agent" = "socdl-installer" }
        return $r.tag_name
    } catch { return $null }
}

function Install-FromBinary {
    $tag = if ($Version) { $Version } else { Get-LatestTag }
    if (-not $tag) {
        Write-Warn2 "Could not determine latest release."
        return $false
    }

    $url = "https://github.com/$Repo/releases/download/$tag/socdl-windows-x64.exe"
    Write-Info "Downloading $tag binary..."

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $dest = Join-Path $InstallDir $BinName
    $tmp  = "$dest.tmp"

    try {
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
        Move-Item -Force $tmp $dest
        Write-Ok "Installed binary to $dest"
        return $true
    } catch {
        if (Test-Path $tmp) { Remove-Item -Force $tmp -ErrorAction SilentlyContinue }
        Write-Warn2 "Binary download failed: $($_.Exception.Message)"
        return $false
    }
}

function Install-FromPip {
    $py = Test-Python
    if (-not $py) {
        Write-Err2 "Python not found. Please install Python 3.9+ first:"
        Write-Err2 "  winget install Python.Python.3.12"
        return $false
    }
    Write-Info "Installing socdl via pip ($py)..."
    & $py -m pip install --upgrade --user socdl
    if ($LASTEXITCODE -ne 0) {
        Write-Err2 "pip install failed."
        return $false
    }
    Write-Ok "Installed via pip."
    return $true
}

function Add-ToUserPath {
    param([string]$Dir)
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = $current -split ";" | Where-Object { $_ }
    if ($parts -contains $Dir) {
        Write-Info "PATH already contains $Dir"
        return
    }
    $new = (@($parts) + $Dir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $new, "User")
    Write-Ok "Added $Dir to user PATH."
    Write-Warn2 "Restart your terminal (or log out/in) for PATH changes to apply."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
$installed = $false

switch ($Method) {
    "binary" { $installed = Install-FromBinary }
    "pip"    { $installed = Install-FromPip }
    "auto"   {
        $installed = Install-FromBinary
        if (-not $installed) {
            Write-Info "Falling back to pip..."
            $installed = Install-FromPip
        }
    }
}

if (-not $installed) {
    Write-Err2 "Installation failed."
    exit 1
}

# PATH only applies for the binary method
if ($Method -ne "pip" -and (Test-Path (Join-Path $InstallDir $BinName)) -and -not $NoPath) {
    Add-ToUserPath -Dir $InstallDir
}

Write-Host ""
Write-Ok "socdl is ready!"
Write-Host ""
Write-Host "  Try it:" -ForegroundColor White
Write-Host "    socdl --help" -ForegroundColor Cyan
Write-Host "    socdl https://youtu.be/XXXX" -ForegroundColor Cyan
Write-Host "    socdl watch      # auto-download anything you copy" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Note: install ffmpeg for best YouTube quality:" -ForegroundColor White
Write-Host "    winget install Gyan.FFmpeg" -ForegroundColor Cyan
Write-Host ""

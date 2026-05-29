param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$AppDir = Join-Path $RootDir "app"
$TempDir = Join-Path $RootDir "temp_download_tools"

$YtDlpUrl = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
$FfmpegZipUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"

$YtDlpPath = Join-Path $AppDir "yt-dlp.exe"
$FfmpegPath = Join-Path $AppDir "ffmpeg.exe"

function Download-File($Url, $Destination) {
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Destination
}

New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

try {
    if ($Force -or -not (Test-Path -LiteralPath $YtDlpPath)) {
        Download-File $YtDlpUrl $YtDlpPath
    } else {
        Write-Host "yt-dlp.exe already exists: $YtDlpPath"
    }

    if ($Force -or -not (Test-Path -LiteralPath $FfmpegPath)) {
        $ZipPath = Join-Path $TempDir "ffmpeg.zip"
        $ExtractDir = Join-Path $TempDir "ffmpeg"
        if (Test-Path -LiteralPath $ExtractDir) {
            Remove-Item -LiteralPath $ExtractDir -Recurse -Force
        }
        Download-File $FfmpegZipUrl $ZipPath
        Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractDir -Force
        $ExtractedFfmpeg = Get-ChildItem -LiteralPath $ExtractDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
        if (-not $ExtractedFfmpeg) {
            throw "ffmpeg.exe not found in downloaded archive"
        }
        Copy-Item -LiteralPath $ExtractedFfmpeg.FullName -Destination $FfmpegPath -Force
    } else {
        Write-Host "ffmpeg.exe already exists: $FfmpegPath"
    }
}
finally {
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force
    }
}

Write-Host ""
Write-Host "Tool versions:"
& $YtDlpPath --version
(& $FfmpegPath -version | Select-Object -First 1)

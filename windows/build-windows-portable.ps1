param(
    [switch]$SkipSmokeTest,
    [string]$PythonCommand = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AppName = "Nuxpad"
$Version = "2.0.0-rc5.1"
$Architecture = "x64"

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "This build script must be run on Windows."
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
$SourceFile = Join-Path $Root "source\nuxpad.py"
$IconDir = Join-Path $Root "assets\icons"
$IconFile = Join-Path $IconDir "nuxpad.ico"
$AboutImage = Join-Path $IconDir "nuxpad-about.png"
$Requirements = Join-Path $ScriptDir "build-requirements.txt"
$VersionInfo = Join-Path $ScriptDir "windows-version-info.txt"

$BuildRoot = Join-Path $ScriptDir "build"
$Venv = Join-Path $BuildRoot "venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"
$Stage = Join-Path $BuildRoot "source-stage"
$PyInstallerDist = Join-Path $BuildRoot "pyinstaller-dist"
$PyInstallerWork = Join-Path $BuildRoot "pyinstaller-work"
$Dist = Join-Path $Root "dist"
$PackageName = "$AppName-$Version-Windows-$Architecture-portable"
$PackageDir = Join-Path $Dist $PackageName
$ZipFile = Join-Path $Dist "$PackageName.zip"
$ChecksumFile = "$ZipFile.sha256"
$BuildInfo = Join-Path $Dist "$AppName-$Version-Windows-$Architecture.build-info.txt"
$PythonLock = Join-Path $Dist "$AppName-$Version-Windows-$Architecture.build-python-lock.txt"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message"
}

function Assert-File([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing required file: $Path"
    }
}

Assert-File $SourceFile
Assert-File $IconFile
Assert-File $AboutImage
Assert-File $Requirements
Assert-File $VersionInfo

$SourceText = Get-Content -LiteralPath $SourceFile -Raw
$ExpectedVersionPattern = (
    'APP_VERSION\s*=\s*"' +
    [regex]::Escape($Version) +
    '"'
)
if ($SourceText -notmatch $ExpectedVersionPattern) {
    $DetectedVersionLine = (
        $SourceText -split "\r?\n" |
        Where-Object { $_ -match '^\s*APP_VERSION\s*=' } |
        Select-Object -First 1
    )
    throw (
        "Canonical source version mismatch. " +
        "Expected $Version. Found: $DetectedVersionLine"
    )
}

$ApplicationPythonFiles = @(
    Get-ChildItem -LiteralPath $Root -Recurse -File -Filter *.py |
    Where-Object {
        $_.FullName -notlike "$BuildRoot*" -and
        $_.FullName -notlike "$Dist*"
    }
)
if ($ApplicationPythonFiles.Count -ne 1 -or
    $ApplicationPythonFiles[0].FullName -ne $SourceFile) {
    throw "Expected exactly one canonical application Python file."
}

Write-Step "Preparing isolated Python environment"
if (Test-Path -LiteralPath $BuildRoot) {
    Remove-Item -LiteralPath $BuildRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $BuildRoot, $Stage, $Dist -Force | Out-Null

& $PythonCommand -m venv $Venv
if ($LASTEXITCODE -ne 0) {
    throw "Could not create the Python virtual environment."
}

& $VenvPython -m pip install --upgrade pip wheel setuptools
if ($LASTEXITCODE -ne 0) {
    throw "Could not update the Python build tools."
}

& $VenvPython -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) {
    throw "Could not install the Windows build requirements."
}

& $VenvPython -m py_compile $SourceFile
if ($LASTEXITCODE -ne 0) {
    throw "The canonical source failed Python syntax validation."
}

& $VenvPython -m pip freeze --all |
    Set-Content -LiteralPath $PythonLock -Encoding UTF8

Write-Step "Staging the canonical source and shared assets"
Copy-Item -LiteralPath $SourceFile -Destination (Join-Path $Stage "nuxpad.py")
Copy-Item -LiteralPath $IconDir -Destination (Join-Path $Stage "icons") -Recurse

Write-Step "Building the Windows portable application"
$PyInstallerArguments = @(
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onedir",
    "--optimize", "1",
    "--name", "Nuxpad",
    "--icon", $IconFile,
    "--version-file", $VersionInfo,
    "--distpath", $PyInstallerDist,
    "--workpath", $PyInstallerWork,
    "--specpath", $BuildRoot,
    "--add-data", "$Stage\icons;icons",
    (Join-Path $Stage "nuxpad.py")
)
& $PyInstaller @PyInstallerArguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

Write-Step "Assembling the portable Windows package"
if (Test-Path -LiteralPath $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null
Copy-Item -Path (Join-Path $PyInstallerDist "Nuxpad\*") `
    -Destination $PackageDir -Recurse -Force

$PackageDocs = Join-Path $PackageDir "docs"
New-Item -ItemType Directory -Path $PackageDocs -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Root "LICENSE") `
    -Destination (Join-Path $PackageDocs "LICENSE")
Copy-Item -LiteralPath (Join-Path $Root "docs\README.md") `
    -Destination (Join-Path $PackageDocs "README.md")
Copy-Item -LiteralPath (Join-Path $Root "docs\CROSS_PLATFORM_ARCHITECTURE.md") `
    -Destination (Join-Path $PackageDocs "CROSS_PLATFORM_ARCHITECTURE.md")
Copy-Item -LiteralPath (Join-Path $Root "docs\RC5_DELTA_QA.md") `
    -Destination (Join-Path $PackageDocs "RC5_DELTA_QA.md")

if (-not $SkipSmokeTest) {
    Write-Step "Running a short Windows launch smoke test"
    $Executable = Join-Path $PackageDir "Nuxpad.exe"
    $Process = Start-Process -FilePath $Executable -PassThru
    Start-Sleep -Seconds 4
    if ($Process.HasExited) {
        if ($Process.ExitCode -ne 0) {
            throw "Nuxpad exited during the smoke test with code $($Process.ExitCode)."
        }
    }
    else {
        Stop-Process -Id $Process.Id -Force
    }
}

Write-Step "Creating the portable ZIP and build records"
if (Test-Path -LiteralPath $ZipFile) {
    Remove-Item -LiteralPath $ZipFile -Force
}
Compress-Archive -LiteralPath $PackageDir -DestinationPath $ZipFile `
    -CompressionLevel Optimal

$Hash = (Get-FileHash -LiteralPath $ZipFile -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  $(Split-Path -Leaf $ZipFile)" |
    Set-Content -LiteralPath $ChecksumFile -Encoding ASCII

$PythonVersion = (& $VenvPython --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the build Python version."
}

$PyInstallerVersion = (& $PyInstaller --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the PyInstaller version."
}

$QtVersions = (& $VenvPython -c `
    "from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR; print('PyQt6:', PYQT_VERSION_STR); print('Qt:', QT_VERSION_STR)" `
    2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the PyQt6 and Qt versions."
}

$SourceHash = (Get-FileHash -LiteralPath $SourceFile -Algorithm SHA256).Hash.ToLowerInvariant()

@"
Nuxpad Windows build
Version: $Version
Architecture: $Architecture
Built: $(Get-Date -Format o)
Host: $([System.Environment]::OSVersion.VersionString)
Python: $PythonVersion
PyInstaller: $PyInstallerVersion
$QtVersions
Canonical source SHA-256: $SourceHash
Output: $(Split-Path -Leaf $ZipFile)
Output SHA-256: $Hash
"@ | Set-Content -LiteralPath $BuildInfo -Encoding UTF8

Write-Step "Build complete"
Write-Host $PackageDir
Write-Host $ZipFile
Write-Host $ChecksumFile
Write-Host $BuildInfo
Write-Host $PythonLock

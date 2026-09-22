$ErrorActionPreference = "Stop"

$installerUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$installerPath = "$env:TEMP\python-3.11.9-installer.exe"
$installDir = "$env:LOCALAPPDATA\Programs\Python\Python311"

Write-Host "Downloading Python installer from $installerUrl..."
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

Write-Host "Installing Python to $installDir..."
$process = Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1", "TargetDir=$installDir" -Wait -PassThru

Write-Host "Installer finished with exit code: $($process.ExitCode)"

if (Test-Path "$installerPath") {
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
}

$pythonExe = "$installDir\python.exe"
if (Test-Path $pythonExe) {
    Write-Host "Python installed successfully at $pythonExe"
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -r requirements.txt
} else {
    Write-Warning "Python exe not found at $pythonExe"
}

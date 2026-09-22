$ErrorActionPreference = "Stop"

$installDir = "$env:LOCALAPPDATA\Programs\Python\Python311"
New-Item -ItemType Directory -Path $installDir -Force | Out-Null

$zipUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
$zipPath = "$env:TEMP\python-embed.zip"

Write-Host "1. Downloading Python embed package..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath

Write-Host "2. Extracting to $installDir..."
Expand-Archive -Path $zipPath -DestinationPath $installDir -Force
Remove-Item $zipPath -Force

Write-Host "3. Enabling site-packages in python311._pth..."
$pthFile = "$installDir\python311._pth"
if (Test-Path $pthFile) {
    $content = Get-Content $pthFile
    $content = $content -replace '#import site', 'import site'
    $content | Set-Content $pthFile
}

Write-Host "4. Downloading and installing pip..."
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$getPipPath = "$env:TEMP\get-pip.py"
Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath

$pythonExe = "$installDir\python.exe"
& $pythonExe $getPipPath --no-warn-script-location
Remove-Item $getPipPath -Force

Write-Host "5. Installing opencv-python & numpy..."
& $pythonExe -m pip install opencv-python numpy --no-warn-script-location

Write-Host "Python environment setup complete!"
& $pythonExe --version

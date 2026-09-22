$pth = "$env:LOCALAPPDATA\Programs\Python\Python311\python311._pth"
"python311.zip`n.`nLib`nLib\site-packages`nimport site" | Out-File -FilePath $pth -Encoding ascii
Write-Host "Updated $pth successfully."

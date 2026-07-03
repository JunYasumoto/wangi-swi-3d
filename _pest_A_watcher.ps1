$pestPid = 59992
$scratch = "$env:USERPROFILE\.gemini\antigravity\scratch\wangi_3d_swi"
Wait-Process -Id $pestPid -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Set-Location -LiteralPath $scratch
& "C:\anaconda3\python.exe" _pest_postprocess.py

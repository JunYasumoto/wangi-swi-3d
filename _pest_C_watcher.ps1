$pestPid = 57984
Wait-Process -Id $pestPid -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Set-Location "C:\Users\安元純\.gemini\antigravity\scratch\wangi_3d_swi"
& "C:\anaconda3\python.exe" _pest_postprocess.py 2>&1

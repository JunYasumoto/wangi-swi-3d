$pids = 41024, 65260, 74112
Wait-Process -Id $pids -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$scratch = "C:\Users\$([char]0x5b89 + [char]0x5143 + [char]0x7d14)\.gemini\antigravity\scratch\wangi_3d_swi"
$drop    = "C:\Users\$([char]0x5b89 + [char]0x5143 + [char]0x7d14)\Dropbox\$([char]0x8AD6 + [char]0x6587)\wangi-swi\3D"
foreach ($t in "3c_L3sh_GHBmult05", "3c_L3sh_NWrch14", "3c_L3sh_NWk2_05") {
    foreach ($f in "phase3a_heads_$t.csv", "phase3a_summary_$t.json") {
        $src = Join-Path $scratch $f
        if (Test-Path $src) { Copy-Item $src (Join-Path $drop $f) -Force; Write-Output "copied $f" } else { Write-Output "MISSING $f" }
    }
}
Set-Location $drop
& "C:\anaconda3\python.exe" _aggregate_sensitivities.py

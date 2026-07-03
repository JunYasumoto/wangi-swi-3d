# Phase 3c PEST — Scenario C 診断結果 (rch_mult + k2_global vs PPP truth)

**Run**: 2026-06-08 開始、終了 翌日 / PEST GLM diagnostic (NOPTMAX=1)
**Duration**: 244.6 min (~4 時間) / 19 forward MF6 calls (base + 18 in iteration 1)

## 1. 結論 (先に)

**Scenario C は phi 改善できず — global 2 パラメータでは zonal 残差構造を補正できないことを定量的に確認**。これは予測通りで、次手 (3-zone K2 PEST) の必要性を強く支持。

| 量 | 値 |
|---|---|
| Starting phi | 89.96 |
| **Final phi (best of 15 lambda trials)** | **90.75** |
| **Phi change** | **+0.88 % (悪化)** |
| Optimal rch_mult | 0.9412 (initial 1.0 から −5.9%) |
| Optimal k2_global | 0.99999 (実質不動) |
| Update step length (normalized) | 5.88 × 10⁻² (極小) |

## 2. Workflow 検証チェック (per user spec)

すべて✓: PEST chain は正しく動作。

- ✓ template substitution → pest_params.csv が PEST 値で更新
- ✓ wrapper が swi_3d_phase3a_ss.py を subprocess 起動
- ✓ sim_heads_pest.txt が 17 obs を正しく出力
- ✓ .ins instruction が weight 含めて正しく parse
- ✓ obs_used = PPP truth (`GW_Level_best_m`), ww10 weight 0.1, ww01/14/16 除外
- ✓ residual 計算 = obs − sim_L2 (PEST 慣例)
- ✓ obs group ごとに phi 分解 (cent / nw / sse / other)
- ✓ FOSM 共分散も計算済 (rec ファイル 504 行以降)

## 3. Lambda 探索全 15 trial の結果

| λ | scale | step length | trial phi | vs start |
|---|---|---|---|---|
| 0.1 | normal | 2.42e-1 | **93.75** | +4.2% |
| 0.1 | 0.75 | 1.88e-1 | 1.61e7 | **発散** |
| 0.1 | 1.10 | 2.63e-1 | 1.61e7 | **発散** |
| 1 | normal | 2.38e-1 | 1.61e7 | **発散** |
| 1 | 0.75 | 1.84e-1 | 1.61e7 | **発散** |
| 1 | 1.10 | 2.58e-1 | 1.61e7 | **発散** |
| 10 | normal | 2.00e-1 | 1.61e7 | **発散** |
| 10 | 0.75 | 1.54e-1 | 92.40 | +2.7% |
| 10 | 1.10 | 2.18e-1 | 164.0 | +82% (悪化) |
| 100 | normal | 7.76e-2 | 91.19 | +1.4% |
| **100** | **0.75** | **5.88e-2** | **90.75** | **+0.88% (best)** |
| 100 | 1.10 | 8.50e-2 | 91.22 | +1.4% |
| 1000 | normal | 1.09e-2 | 1.61e7 | **発散** |
| 1000 | 0.75 | 8.16e-3 | 1.61e7 | **発散** |
| 1000 | 1.10 | 1.19e-2 | 1.61e7 | **発散** |

→ **9/15 trial で MF6 非収束** (phi=1.61e7 sentinel)、**6/15 で phi 悪化または横ばい**。**改善方向自体が存在しない**。

## 4. Zonal RMSE / bias の動き

|Zone|n|RMSE init|RMSE final|bias init|bias final|
|---|---|---|---|---|---|
|NW|7|1.66|1.66|+1.03|+1.03|
|**CENT**|**4**|**3.29**|**3.30**|**+1.95**|**+1.97**|
|SSE|5|2.25|2.27|+1.18|+1.23|
|all main|16|2.35|2.36|+1.31|+1.33|

→ **全 zone でほぼ動かない**。微悪化が dominant — rch_mult 6% 下げで heads が全 zone で下がり、obs > sim の bias を更に広げた。

## 5. WW4 (Kantamare、HOBO 8-mo truth +2.418 m)

- sim_init = 2.817 m (bias -0.399)
- sim_final = 2.790 m (bias -0.372)
→ WW4 はわずかに改善 (sim が truth に 0.03 m 近づく) するが、他 zone の悪化を相殺できず。

## 6. 物理的解釈

2 つの global multiplier しかないため:

| 方向 | NW | CENT | SSE | WW4 |
|---|---|---|---|---|
| rch_mult ↑ | bias 縮小 (under 減) | bias 縮小 | bias 縮小 | overshoot 増 |
| rch_mult ↓ | bias 拡大 | bias 拡大 | bias 拡大 | overshoot 縮小 |
| k2_global ↑ | bias 拡大 (drainage 増) | bias 拡大 | bias 拡大 | overshoot 縮小 |
| k2_global ↓ | bias 縮小 + solver 発散リスク | bias 縮小 | bias 縮小 | overshoot 増 |

→ **NW/CENT/SSE は同方向に動く** ため、全 zone 共通の改善方向は WW4 を悪化させる。phi-improving 方向が **(rch=0.94, k2=1.0)** 方向だけだったのは、bias が weighted RMSE の中で最小化されるが、CENT/SSE で under-prediction が大きいのに全体を下げる方向に動いた結果 — 矛盾した最適化。

要するに **global 2 パラメータでは underdetermined ではなく overdetermined: 残差構造に方向性が無くて phi が動けない**。

## 7. 次手の明確な方向性

Scenario A (3-zone K2 PEST) で:
- **K2_CENT** を下げる → ww11 (+3.94 m under), ww12 (+5.18 m under) 改善
- **K2_NW** を中程度下げる → NW 7 wells の +1〜+2.5 m under 改善
- **K2_SSE** はやや動かす → ww08 (+3.06 m), ww15 (+3.82 m) 改善
- WW4 (CENT zone 内) は K2_CENT で連動するので個別補正は B (RCH + 3-zone K2) で

solver 安定性も重要 — 6/15 で発散したので、A では:
- **bounds を狭める** (例: 0.3 ~ 3 ではなく 0.5 ~ 2)
- **lambda 初期値を 10 から開始** (大きな step で発散しやすい)
- **FD perturbation を 0.005 → 0.01** (太い jacobian で寄与不明確に)

## 8. 副次知見

- **MF6 non-convergence は K の極端摂動で頻発** — PEST GLM はこれを 1.61e7 sentinel で扱うが、PEST IES (アンサンブル) の方が安定。次に A で発散頻発する場合は IES 切替検討。
- **PEST の 1 iteration ≒ 4 時間** (19 forward × 5.5 min × overhead)。A では 5 params だと jacobian 5 perturbation + 15 lambda trial = 20+ runs/iter ≒ 2 時間/iter。NOPTMAX=3 で 6 時間程度を見込む。並列化 (PANTHER) 検討余地あり。
- **L3-shallow baseline (NOPTMAX=0 phi=89.96)** は global 2 パラメータの近傍最適 — A で zonal K2 を導入したときの reference として保存価値あり。

## 9. ファイル (Dropbox に sync 済)

| Path | 内容 |
|---|---|
| [3D/pest.pst](pest.pst) | PEST 制御ファイル |
| [3D/pest.rec](pest.rec) | PEST 詳細記録 (461 行) |
| [3D/pest_params.csv](pest_params.csv) | 最終最適値 |
| [3D/pest_params.csv.tpl](pest_params.csv.tpl) | template |
| [3D/sim_heads_pest.ins](sim_heads_pest.ins) | instruction |
| [3D/Phase3c_PEST_forward.py](Phase3c_PEST_forward.py) | wrapper |
| [3D/_build_pest_files.py](_build_pest_files.py) | setup generator |
| [3D/calibration_targets_corrected.csv](calibration_targets_corrected.csv) | truth-based targets |
| [figs/pest_C_phi_reduction.png](pest_C_phi_reduction.png) | (a) phi by group + (b) param trajectory |
| [figs/pest_C_residuals_before_after.png](pest_C_residuals_before_after.png) | 17 wells before/after |
| [figs/pest_C_obs_vs_sim.png](pest_C_obs_vs_sim.png) | 散布図 initial vs final |

## 10. 推奨次手

Scenario A (3-zone K2 PEST) に進む。具体的にはまず以下を準備:

1. `Phase3c_PEST_forward.py` に zone-wise K2 multiplier (K2_NW_MULT, K2_CENT_MULT, K2_SSE_MULT) を追加 (env var は既存、wrapper で読み取り)
2. `swi_3d_phase3a_ss.py` を K2_CENT_MULT / K2_SSE_MULT に拡張 (現状 NW のみ)
3. `pest.pst` の parameter section を 3 parameters に拡張、bounds を 0.5 〜 2.0 に締める
4. NOPTMAX=3 で起動 (6 時間程度)
5. 完了後 A の結果と C 比較してさらに B (RCH 追加) 判断

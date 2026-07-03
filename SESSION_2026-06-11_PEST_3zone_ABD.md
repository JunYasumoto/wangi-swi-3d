# Phase 3c PEST — 3-zone K2 / recharge シナリオ campaign (A / B / D)

**Run date**: 2026-06-11（pestpp-glm 5.2.22、host DESKTOP-8VBUO1Q、全 NOPTMAX=3）
**前提**: Scenario C（global 2-param）は改善ゼロと既に確認済 → zonal 補正へ（[SESSION_2026-06-08_PEST_C_RESULTS.md](SESSION_2026-06-08_PEST_C_RESULTS.md)）

## 0. 結論（先に）

- **3-zone K2（A）で NW/SSE は内部最適に収束**、phi −10.6%。NW の bias はほぼ 0 に。
- **CENT（ww04/ww11/ww12）の under-prediction は構造的**。zonal K2（床張り付き）でも、global recharge（B）でも、CENT 専用 recharge（D）でも救いきれない。
- **D は phi 最小（70.78, base比 −21.3%）だが、recharge を非現実値（global 1800・CENT 5400 mm/yr）まで振り切った overfitting**。5 params 中 3 つが bound 張り付き。
- **物理的に妥当なキャリブレーションは A4（または B）。D は CENT の構造的限界を露呈する診断**と位置づける。

## 1. シナリオ比較

| シナリオ | パラメータ | Final Φ | 対 base | overall RMSE(n=16) | 物理性 |
|---|---|---|---|---|---|
| base | K2=1.0 | 89.96 | — | 2.35 | — |
| C | global rch + k2_global (2) | 89.96 | 0% | — | — |
| **A4** | 3-zone K2 (3), bounds 0.3–2.0 | **80.46** | **−10.6%** | 2.215 | ✅ 妥当 |
| **B** | A + global rch_mult (4) | **77.86** | **−13.4%** | 2.179 | ✅ ほぼ妥当 |
| **D** | B + CENT-zonal rch_cent (5) | **70.78** | **−21.3%** | 2.074 | ⚠️ recharge非現実 |

Φ by group の推移:

| group | base | A4 | B | D |
|---|---|---|---|---|
| **obs_cent** | 42.52 | 35.91 | 32.48 | **25.51** |
| obs_sse | 38.71 | 35.76 | 36.50 | 36.26 |
| obs_nw | 6.79 | 6.86 | 6.95 | 7.09 |
| obs_other | 1.94 | 1.93 | 1.93 | 1.93 |

## 2. 最適パラメータと bound 張り付き

| param | bounds | A4 | B | D |
|---|---|---|---|---|
| k2_nw | 0.3–2.0 | 0.386 | 0.379 | 0.347 |
| k2_cent | 0.3–2.0 | **0.300**▼ | **0.300**▼ | **0.300**▼ |
| k2_sse | 0.3–2.0 | 0.505 | 0.863 | **2.000**▲ |
| rch_mult | 0.5–3.0 | — | 1.875 | **3.000**▲ |
| rch_cent | 0.5–3.0 | — | — | **3.000**▲ |

▼下限張り付き ▲上限張り付き。D では 3 params が bound に張り付き、まだ「もっと欲しい」状態 → 構造的に説明不能。

## 3. CENT 構造的残差（本キャンペーンの核心発見）

ww04・ww11・ww12 は**約200 m 以内に密集**するが、観測 head は **2.42 / 6.68 / 7.54 m**（最大 5 m 差）。
単一連続帯水層モデルでは 200 m で 5 m の局所急勾配を再現不能。

CENT 専用 recharge を 5400 mm/yr まで上げると ww11/ww12 は持ち上がるが **ww04 を過大予測でオーバーシュート**（D: ww04 sim 5.16 vs obs 2.42）。同一ゾーン内で逆方向の補正が必要 = **ww11/ww12 は ww04 と水理的に別区画**（宙水/区画化帯水層、または観測 datum 問題の可能性）。

| CENT well | obs | sim base | sim A4 | sim B | sim D |
|---|---|---|---|---|---|
| ww04 | 2.418 | 2.82 | ~3.4 | 3.88 | 5.16（過大）|
| ww11 | 6.683 | 2.74 | ~3.4 | 3.70 | 4.90 |
| ww12 | 7.535 | 2.36 | ~2.9 | 2.90 | 3.69 |

→ ww11/ww12 は最も妥当な D でも +1.8 / +3.9 m の under-prediction が残る。

## 4. 技術的ブレークスルー — warm-start chaining

当初、PEST の有限差分摂動で **MF6 が高Kセル（SSE zone, K2~53 m/d）で数値発散**し、jacobian が壊れた（13分かけて発散、forward 失敗）。

**解決**: `swi_3d_phase3a_ss.py` を、base（全K2=1.0）の収束解 `warmstart_base.hds` を最優先 IC に使うよう修正。各 PEST forward が base 解近傍から始まるため小さな摂動で発散しない。
- 効果: 発散していた摂動が **13分 → 14〜60秒**（10〜40倍高速）、bounds 全域 0.3–2.0 が収束、**全 run 0 failed**
- IC は収束 head に影響しないので結果に bias なし（RMSE 一致で検証済）
- これにより NOPTMAX=3 が各シナリオ ~45–80 分で完走

## 5. 図 / ファイル

| Path | 内容 |
|---|---|
| [figs/scenario_comparison_CABD.png](figs/scenario_comparison_CABD.png) | (a)Φ by group (b)param vs bounds (c)obs-vs-sim (d)zonal RMSE |
| [figs/scenario_CENT_structural.png](figs/scenario_CENT_structural.png) | CENT 局所急勾配マップ + well別 sim 収束 |
| diag_base/A4/B/D.csv | 各最適 forward の17 well 診断 |
| warmstart_base.hds | base 収束解（warm-start IC）|
| pest.pst / pest_params.csv.tpl | 5-param 制御ファイル（D 構成）|

## 6. 推奨次手

1. **論文では A4（または B）を「妥当なキャリブレーション」として報告**、D は CENT 構造限界の診断として提示
2. ww11/ww12 の概念モデル仮説（宙水/区画化）を地質・化学データ（既存の isotope/EC 解析）で裏付け
3. パラメータ追加はここで打ち止め（D 以上は非現実値での overfitting）

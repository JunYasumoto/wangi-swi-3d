# 3D SWI head calibration — A-clean（主結果）と宙水の概念整理

**Run date**: 2026-06-15（pestpp-glm 5.2.22、warm-start、NOPTMAX=3、全 run 0 failed）
**位置づけ**: 本ノートが**主結果**。探索過程（C/A/B/D, 17井戸）は [SESSION_2026-06-11_PEST_3zone_ABD.md](SESSION_2026-06-11_PEST_3zone_ABD.md) を参照。

## 0. 中心メッセージ

キャリブレーションで**全井戸を無理に合わせる**のではなく、**観測が異なる水理状態（広域帯水層 vs 宙水）を表すことを認識し、物理的に同化可能な井戸集合を定義した**。これは単なる井戸除外ではなく**モデル概念の整理**である。

- 宙水（perched）井戸 = 地下水面が地表面にあり（depth-to-water ≈ 0）、海の塩水境界と水理的に decoupled。広域連続帯水層モデルで再現することは原理的に不適切。
- これらを同化対象から外すと、3-zone K2 のみで**物理的に妥当なキャリブレーション**（RMSE 1.75 m）が得られ、探索過程で問題化した「CENT 構造的残差」「非現実的 recharge」は消滅する。

## 1. 同化可能な井戸集合の定義

| 区分 | 井戸 | 根拠 |
|---|---|---|
| 除外: 中央高地 宙水（従来）| ww01, ww14, ww16 | head 80–166 m、孤立した高所宙水 |
| **除外: 沿岸/低地 宙水（本セッション）** | **ww10, ww11, ww12** | 海岸至近〜中距離で head=地表（dtw≈0〜0.5 m）、隣接広域井戸と 5 m 乖離 |
| **同化対象（14井戸）** | ww02–09, ww13, ww15, ww17–20 | 地下水面が地表下、広域帯水層を代表 |
| 宙水疑い・保持（感度解析対象）| ww05, ww08 | 同 signature だが head 低く SSE 適合は良好。除外影響は strict-clean-12 で評価予定 |

判定指標: **depth-to-water = terrain − head**。宙水は ≈0（地下水面が地表）、広域井戸は >2 m。
→ [figs/Aclean_perched_diagnostic.png](figs/Aclean_perched_diagnostic.png)

## 2. A-clean キャリブレーション（主結果）

**設定**: 3-zone K2（k2_nw/k2_cent/k2_sse）、14井戸、warm-start、NOPTMAX=3
**Φ 推移**: 48.06 → 43.22 → 42.99 → **42.74**

| zone | n | RMSE (m) | bias (m) | Φ寄与 |
|---|---|---|---|---|
| CENT (ww04) | 1 | 0.70 | −0.70 | 0.49 |
| NW | 5 | 1.17 | +0.04 | 6.82 |
| **SSE** | 8 | **2.11** | +1.07 | **35.44（83%）** |
| **全14** | 14 | **1.75** | +0.58 | 42.74 |

→ [figs/Aclean_calibration_result.png](figs/Aclean_calibration_result.png)

### 最適パラメータと解釈
| param | 値 | 拘束度 |
|---|---|---|
| k2_sse | 1.60 | **唯一の有意パラメータ**（SSE 8井戸が拘束）|
| k2_nw | 2.0（上限）| 弱拘束（NW は K2 非感度、Φ 6.89→6.82）|
| k2_cent | 2.0（上限）| ほぼ無拘束（CENT=ww04 1井戸、既に適合）|

宙水除外で K2 最適方向が**下→上に逆転**（宙水込みは under-prediction を埋めるため K2↓ で床張り付き；除外後は残った広域井戸の僅かな過大予測を抑えるため K2↑）。論文では k2_nw/k2_cent を 1.0 固定 or「非感度」と明記するのが無難。

## 3. 残差構造 — SSE ゾーン内不均質

SSE 8井戸の残差（obs−sim）は**正負混在** → 単一 K2 では補正不能:

| under (+) | resid | over (−) | resid |
|---|---|---|---|
| ww08* | +3.04 | ww13 | −1.94 |
| ww15 | +2.77 | ww07 | −1.24 |
| ww06 | +2.54 | ww09 | −0.06 |
| ww05* | +2.34 | | |
| ww17 | +1.13 | | |

*ww05/ww08 は宙水 signature（保持中）。これらの過小予測成分を除けば、残るのは沿岸（ww07/13 過大）vs 内陸（ww15 過小）の真の不均質。

## 4. 感度解析・診断（A-clean の妥当性補強）

### Step 2 — strict-clean-12（ww05/ww08 も除外、頑健性確認）
12井戸で再キャリブレーション。**主結果 k2_sse はほぼ不変** = A-clean は頑健。

| param | A-clean(14) | strict-12(12) |
|---|---|---|
| **k2_sse** | 1.596 | **1.518（−5%）** |
| k2_nw / k2_cent | 2.0 / 2.0 | 2.0 / 2.0（同一）|

obs_sse Φ 35.44→20.70 の減少は ww05(+2.34)・ww08(+3.04) の misfit が抜けた分で、**パラメータの変化ではない**。→ ww05/ww08 は SSE misfit に寄与するが calibration を歪めない。

### Step 3 — SSE coastal/inland サブゾーン分割（診断、主結果ではない）
SSE を海岸距離500mで coastal(zone31)/inland(zone32) に分割、4パラメータで診断（mask: k2_sse_split.npy）。**Φ 28.05→27.78（−1%、無改善）**。

| param | 値 | 解釈 |
|---|---|---|
| k2_sse_coast | 2.0（上限漂流）| ww06 は海岸GHB境界支配で **K 非依存** → 拘束されず bound へ |
| k2_sse_inland | 1.45（≈単一値）| 単一ゾーン解を再現 |

SSE 残差は分割前後で不変（RMSE 1.86→1.85）。内陸は **ww15(+2.72) vs ww07/ww13(−1.3/−1.9) の逆符号＝既約な不均質**。
→ **SSE misfit はサブゾーン化で解けない物理的構造**（沿岸=境界支配 + 内陸=真の不均質）。A-clean の単一 k2_sse が適切なパラメータ化レベルと確認。「パラメータを増やせば合う」のではない。

### Step 4 — FOSM（k2_sse 事後不確実性）
A-clean 最適点（k2=2.0/2.0/1.596）で jacobian を計算し FOSM 事後共分散を評価（pestpp-glm NOPTMAX=1）。

| param | prior σ(log10) | post σ(log10) | 低減 | 拘束 |
|---|---|---|---|---|
| **k2_sse** | 0.206 | **0.146** | **−29%** | ✅ identifiable |
| k2_nw | 0.206 | 0.203 | −1% | ❌ 未拘束 |
| k2_cent | 0.206 | 0.205 | −0% | ❌ 未拘束 |

- **k2_sse = 1.59**、1σ [1.14, 2.22]（×/÷1.40）、2σ [0.82, 2.0(クリップ)] = **唯一の identifiable パラメータ**
- k2_nw/k2_cent は posterior≈prior → **データで決まらず上限張り付き**。論文では 1.0 固定 or「K2 非感度」と明記
- パラメータ相関 \|corr\|<0.11（k2_nw–sse −0.11, cent–sse −0.04, nw–cent −0.01）= **ほぼ無相関、トレードオフなし、構造健全**
- → [figs/Aclean_FOSM.png](figs/Aclean_FOSM.png)、pest.par.usum.csv / pest.post.cov

**FOSM 総括**: ご指摘どおり FOSM の主役は k2_sse のみ。広域帯水層 SSE の透水性が ×/÷1.4 で推定され、他2ゾーンはデータが透水性を拘束しない（NW は K 非感度、CENT は ww04 単独）。これは「同化可能な情報が SSE に集中」という A-clean の構造を定量的に裏付ける。

## 5. 技術的成果（再利用）
**warm-start chaining**（`warmstart_base.hds`）: MF6 の高Kセル数値発散を解消。摂動 forward が 13分発散→14秒収束、全 run 0 failed、NOPTMAX=3 が約1時間で完走。

## 4b. 独立検証 — 化学・年代（2026-06）

head-based 分類 (regional/perched/boundary) を独立データで検証（化学は ww01–10 のみ）。
データ: ww_isotope_chem.csv (δ18O/δ2H/Cl/SF6), zeta_vs_chem.csv (Cl/海水混合率), sf6_age_comparison.csv。
井戸ID対応: WW1..WW10 = ww01..ww10（標高で照合済）。

| class | wells | SF6 obs 年代 |
|---|---|---|
| **perched** | ww01, ww10 | **modern (<1 yr)** = 局所涵養 |
| regional | ww02/04/07/09 | 8–18 yr（老齢集団）|
| perched-suspect | ww05, ww08 | 13–14 yr（= 広域と同年代）|
| boundary | ww06 | SF6 汚染（年代不能）, 海水混合率 高 |

**結論:**
- 宙水 (ww01,ww10) は SF6 が **modern** → 「水頭が合わない」だけでなく **年代的に別の若い水** = 除外の独立根拠。
- ww05/ww08 は **広域と同年代 (13–14 yr)** → 宙水でなく広域水。**A-clean で残した判断を化学が支持**（strict-12 の除外は保守的すぎ）。
- モデル傍証: perched で obs modern vs sim 9–9000 yr の極端な乖離 → 広域モデルは原理的に再現不能。
- 海水混合率 (Cl) は沿岸位置を反映（perched 判定とは別軸）。
- 留意: ww11/ww12 (perched 除外) は化学データ無 → 水頭の類似性から推定。
- 図: [figs/chem_age_validation.png](figs/chem_age_validation.png)、解析: _chem_validation.py

## 5b. 本文用図（publication-ready）

| Fig | Path | 用途 |
|---|---|---|
| 1 | [figs/paper_well_classification.png](figs/paper_well_classification.png) | 観測井分類図 regional/perched/boundary-controlled（空間）|
| 2 | [figs/paper_obs_vs_sim.png](figs/paper_obs_vs_sim.png) | A-clean obs vs sim（category別、regional は1:1付近・perched/boundaryは下方）|
| 3 | [figs/paper_scenario_table.png](figs/paper_scenario_table.png) | シナリオ比較表（base/B/D/A-clean/strict-12/SSE-split）|
| 4 | [figs/Aclean_FOSM.png](figs/Aclean_FOSM.png) | FOSM posterior/prior 不確実性（k2_sse のみ identifiable）|

**Key sentence（本文）**:
> The calibration problem was not solved by increasing parameter complexity, but by identifying which observations represented the regional aquifer system and which represented perched or boundary-controlled hydraulic states.
>
> 本研究では、残差を追加パラメータで機械的に吸収するのではなく、観測井が表す水理状態を再分類することで、広域帯水層モデルが同化すべき観測集合を定義した。

## 6. ファイル
| Path | 内容 |
|---|---|
| [figs/Aclean_perched_diagnostic.png](figs/Aclean_perched_diagnostic.png) | 宙水診断（dtw vs 海岸距離 / head vs terrain）|
| [figs/Aclean_calibration_result.png](figs/Aclean_calibration_result.png) | A-clean fit・Φ群・zonal RMSE・SSE残差 |
| [figs/Aclean_FOSM.png](figs/Aclean_FOSM.png) | FOSM パラメータ不確実性（k2_sse のみ identifiable）|
| diag_Aclean.csv / diag_strict12.csv / diag_ssesplit.csv | 各最適の井戸診断 |
| scenario_summary_ABD.csv | 全シナリオ数値（base/C/A4/B/D/A-clean/strict-12/SSE-split）|
| pest_Aclean.pst / pest_strict12.pst | 主結果・感度解析の制御ファイル snapshot |
| pest.par.usum.csv / pest.post.cov | FOSM 事後不確実性・共分散 |
| k2_sse_split.npy | SSE coastal/inland 分割マスク（診断用）|

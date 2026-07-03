# 引き継ぎメモ — 別 PC（地球研）で作業を再開するために

**対象プロジェクト**　Wangi-Wangi 島 3D 海水侵入(SWI)地下水モデル / MODFLOW 6 + flopy + PEST++
**作成**　2026-07（本セッション時点の状態）
**現在の主結果**　A-clean（宙水井戸を除いた 14 井戸・3-zone K2、RMSE 1.75 m）。詳細は [REPORT_GW_PEST_evaluation_2026-06.md](REPORT_GW_PEST_evaluation_2026-06.md) と [SESSION_2026-06-15_PEST_Aclean_MAIN.md](SESSION_2026-06-15_PEST_Aclean_MAIN.md)。

---

## 0. まず結論（何を運べばよいか）

- プロジェクト全体は約 89 GB あるが、**82 GB は `phase3b_tidal_*` の再生成可能な巨大出力（gwf.cbc/hds/zta）で、引き継ぎには不要**。
- 実際に必要な「コード＋モデル入力＋成果物」は **約 200 MB**。これだけ運べば新 PC で作業を再開できる。
- 運搬方法の推奨は §6（要約: **コード・成果は GitHub、大容量バイナリは Dropbox**）。

---

## 1. 引き継ぎに必要な最小セット

### (a) コード
- `swi_3d_phase3a_ss.py`（MODFLOW6 SWI 定常モデル本体、flopy）
- `Phase3c_PEST_forward.py`（PEST forward ラッパー）
- 図・解析スクリプト（`_make_*.py`, `_chem_validation.py`, `_zonal_rmse.py` ほか）

### (b) モデル入力（npy, 各 ~5 MB）
- `top_elevation.npy`, `idomain.npy`, `k1_field.npy`, `k2_field.npy`, `botm1_field.npy`, `botm2_field.npy`
- ゾーン: `k2_zones_pest.npy`(1=NW/2=CENT/3=SSE), `k2_sse_split.npy`(31=沿岸/32=内陸), `zones_3zone.npy`
- `model_config.py`（格子定義 FROZEN V16）, `params.csv`（rch_mult, porosity 等）

### (c) 初期条件
- `warmstart_base.hds`（base 収束解、約 15 MB）※ 無ければ base forward で再生成可（§4）

### (d) 観測・PEST 制御
- `calibration_targets_corrected.csv`（観測真値・重み・同化フラグ。ww01/10/11/12/14/16 除外、ww05/08 は保持）
- 主結果構成: `pest_Aclean.pst`, `pest_params.csv.tpl`, `sim_heads_pest.ins`
- 感度版: `pest_strict12.pst`

### (e) 実行体（コンパイル済バイナリ、git には載せない）
GitHub Release [`executables-2026-07`](https://github.com/JunYasumoto/wangi-swi-3d/releases/tag/executables-2026-07) の
`wangi-swi-3d-executables.zip`（7.6 MB, sha256 `f8fc1a7e…`）にまとめてある。**親ディレクトリ `scratch/` に展開**すると下記が再現される。
Private のため取得はブラウザ（ログインして Releases からDL）か `gh release download executables-2026-07 -R JunYasumoto/wangi-swi-3d`。
- **MODFLOW（SWI+潮汐 特殊ビルド）**: `../wangi_swi/mf6.6.0-SWI-Tides/mf6.exe`
  - ※ 公式 `get-modflow` では入手不可の特殊ビルド。
- **PEST++**: `../wangi_jpgu2026/pestpp-glm.exe`（v5.2.22）。公式配布の pestpp-glm でも可。

### (f) 成果物（記録として）
- レポート `REPORT_GW_PEST_evaluation_2026-06.md`、セッションノート `SESSION_2026-06-15_PEST_Aclean_MAIN.md`
- 集計 `scenario_summary_ABD.csv`、診断 `diag_Aclean.csv` 他
- 図 `figs/`（paper_*, Aclean_*, scenario_*, chem_age_validation）
- スライド `Wangi_SWI_calibration_results.pptx` 等
- FOSM 出力 `pest.par.usum.csv`, `pest.post.cov`

---

## 2. 地球研 PC でのセットアップ手順

### Step 1. Python 環境
```
conda create -n flopy_env python=3.11 -y
conda activate flopy_env
pip install flopy pandas matplotlib scipy pyemu
python -c "import flopy; print(flopy.__version__)"   # 3.9 系であること
```

### Step 2. フォルダ配置
`scratch/` 直下に以下の相対関係を再現する（swi スクリプトが `WORK.parent` を参照するため）:
```
scratch/
 ├─ wangi_3d_swi/          ← 本プロジェクト（コード・入力・成果）
 ├─ wangi_swi/mf6.6.0-SWI-Tides/mf6.exe     ← SWI 対応 MODFLOW
 └─ wangi_jpgu2026/pestpp-glm.exe           ← PEST++（と任意で wangi.hds）
```

### Step 3. マシン依存パスの修正（重要）
端末が変わると絶対パスがずれるので必ず直す。
- `pest.pst`（および `pest_Aclean.pst` 等）の `* model command line` 行の python パスを、新 PC の値へ:
  例) `C:\Users\<user>\anaconda3\envs\flopy_env\python.exe Phase3c_PEST_forward.py`
- `swi_3d_phase3a_ss.py` の `MF6_EXE`（`WORK.parent/"wangi_swi"/...`）が実在するか確認。
- PEST 実行時に呼ぶ `pestpp-glm.exe` のフルパスを新 PC の配置に合わせる。
- 参考: 過去に同様のパス修正を実施済み（[machine-paths メモ] 参照）。旧 2 台は `MOUSEMH-I9U01` と `DESKTOP-8VBUO1Q`。

### Step 4. 動作確認（スモークテスト）
```
# base forward（全 K2=1.0）で収束と 14 obs 出力を確認
（pest_params.csv に k2_nw=1,k2_cent=1,k2_sse=1 を書く）
<python> Phase3c_PEST_forward.py
# → "Wrote sim_heads_pest.txt with 14 obs" が出て、success:True なら環境OK
```
`warmstart_base.hds` が無い場合、この base 実行の出力 `phase3a_ss_pest_iter/gwf.hds` を `warmstart_base.hds` にコピーして初期条件に使う。

---

## 3. 実行方法（PEST 本実行）

主結果 A-clean を再現/継続する場合:
```
copy pest_Aclean.pst pest.pst        # 主結果構成に戻す
copy sim_heads_pest_Aclean.ins sim_heads_pest.ins
# calibration_targets_corrected.csv は ww10/11/12 除外（use_for_calibration=False）を確認
<pestpp-glm.exe> pest.pst             # NOPTMAX=3, 全 run 0 failed で約1時間
```
- 1 forward ≒ 60〜90 秒（warm-start 有効時）。warm-start 無しだと発散し得るので `warmstart_base.hds` 必須。
- 最適解の後処理は最適パラメータで forward を1回回し `diag_*.csv` と `_zonal_rmse.py` で評価。

---

## 4. 現状の到達点と次の一手

- **主結果 A-clean 確定**（RMSE 1.75 m、非現実涵養なし）。頑健性(strict-12)・診断(SSE-split)・不確実性(FOSM)・独立検証(化学/年代)まで完了。
- 有意パラメータは **k2_sse のみ**（FOSM）。k2_nw/k2_cent は非感度。
- 次の候補:
  1. **PANTHER 並列化**（実行機 i9-10920X の 12 コアを活用、NOPTMAX=3 を ~10-15 分に短縮）。各 worker を別ディレクトリで動かす設定が要る。
  2. **多目的化**（SF6 滞留時間・EC・塩水混合率・SGD を目的関数に追加、既存 csv あり）。
  3. **論文化**（A-clean を主、他を補助解析として整理。図・表・スライドは整備済）。

---

## 5. データ配置の方針（GitHub と Dropbox の使い分け）

- **GitHub**（コード + 小さな成果 + モデル入力）: `.py`, `pest*.pst`, `.tpl/.ins`, `.csv`, `figs/*.png`, `*.md`, `*.pptx`, 入力 `*.npy`（各 5 MB 程度）, `warmstart_base.hds`(15 MB)。
  - 除外(.gitignore): `phase3b_tidal_*/`, `phase3a_ss*/`, `*.cbc`, `*.hds`(warmstart 以外), `*.zta`, `__pycache__/`, 一時ログ `_*.log`/`_*.txt`, `*.exe`。
  - 利点: バージョン管理・再現性・共有。新 PC では `git clone` で軽量に取得できる。
- **Dropbox**（大容量バイナリの同期/バックアップ）: `phase3b_tidal_*` の巨大出力や実行体(exe)など、git に不向きなもの。
- 実行体(mf6.exe/pestpp-glm.exe)は git に載せず、Dropbox 経由か公式配布から個別入手。

---

## 6. 補足・注意

- 実行体 `mf6.6.0-SWI-Tides` は**特殊ビルド**。地球研 PC で入手できるか事前確認（無ければ Dropbox から運ぶ）。
- `phase3b_tidal_*`（82 GB）は現行の SS/PEST 作業には不要。運搬対象から外してよい（必要時に再計算）。
- 大容量出力は Dropbox 容量を圧迫するため、不要な `phase3a_ss_*` 中間ワークスペースは適宜削除可（再生成可能）。

# wangi-swi-3d

Wangi-Wangi 島 **3次元 海水侵入（SWI）地下水流動モデル**の逆解析。
MODFLOW 6（SWI・潮汐対応ビルド）+ flopy + PEST++（pestpp-glm）による定常水頭キャリブレーション。
1次元版は [`wangi-swi-1d`](https://github.com/JunYasumoto/wangi-swi-1d)。

## 現状（主結果）

宙水（perched）井戸を同化対象から外した **A-clean**（14 井戸・3-zone K2）が preferred calibration。

| 指標 | 値 |
|---|---|
| head RMSE | **1.75 m**（14 井戸）|
| 有意パラメータ | k2_sse = 1.60（FOSM で identifiable。k2_nw/k2_cent は非感度）|
| 位置づけ | 非現実的な涵養を用いず、物理的に説明可能な解 |

中心的な知見は「残差を追加パラメータで機械的に吸収するのではなく、観測井が表す水理状態（広域／宙水／境界支配）を再分類し、広域帯水層モデルが同化すべき観測集合を定義した」点。詳細は下記ドキュメント参照。

## 主要ドキュメント

| ファイル | 内容 |
|---|---|
| [HANDOFF_new_PC_setup.md](HANDOFF_new_PC_setup.md) | **別 PC での環境構築・作業再開手順**（まずこれ）|
| [REPORT_GW_PEST_evaluation_2026-06.md](REPORT_GW_PEST_evaluation_2026-06.md) | モデル・PEST 設定・結果・課題・改善案の詳細評価レポート |
| [SESSION_2026-06-15_PEST_Aclean_MAIN.md](SESSION_2026-06-15_PEST_Aclean_MAIN.md) | 主結果 A-clean の詳細記録 |
| [SESSION_2026-06-11_PEST_3zone_ABD.md](SESSION_2026-06-11_PEST_3zone_ABD.md) | 探索段階（C/A/B/D）の記録 |
| [scenario_summary_ABD.csv](scenario_summary_ABD.csv) | 全 8 シナリオの数値 |

## リポジトリ構成

```
swi_3d_phase3a_ss.py        MODFLOW6 SWI 定常モデル本体（flopy）
Phase3c_PEST_forward.py     PEST forward ラッパー
pest_Aclean.pst             主結果の PEST 制御ファイル（3 params, 14 obs）
pest_strict12.pst           感度確認版（12 obs）
pest_params.csv.tpl / sim_heads_pest.ins   PEST テンプレート／指示ファイル
calibration_targets_corrected.csv          観測真値・重み・同化フラグ
*.npy                       モデル入力（標高・K場・idomain・ゾーン等）
warmstart_base.hds          base 収束解（warm-start 初期条件）
figs/                       図（paper_*, Aclean_*, scenario_*, chem_age_validation）
_make_*.py / _chem_validation.py / _zonal_rmse.py   図・解析生成スクリプト
```

## セットアップ（要約）

```bash
# 1. clone（Dropbox 同期フォルダの外で）
git clone https://github.com/JunYasumoto/wangi-swi-3d.git
cd wangi-swi-3d

# 2. Python 環境
conda create -n flopy_env python=3.11 -y
conda activate flopy_env
pip install flopy pandas matplotlib scipy pyemu

# 3. 実行体を配置（下記「実行体」参照）
# 4. pest.pst のモデルコマンド行の python パスを新 PC 用に修正
# 5. base forward でスモークテスト
```

詳細は [HANDOFF_new_PC_setup.md](HANDOFF_new_PC_setup.md)。

## 実行体（別途入手）

MODFLOW / PEST の実行体はサイズ・ライセンスの都合で **git には含めていない**。以下を別途取得し、リポジトリの親 `scratch/` に配置する。

| 実行体 | 期待パス | 入手先 |
|---|---|---|
| `mf6.exe`（SWI+潮汐 特殊ビルド, 46 MB）| `../wangi_swi/mf6.6.0-SWI-Tides/mf6.exe` | 本リポジトリの **Releases**（または Dropbox）|
| `pestpp-glm.exe`（v5.2.22, 2 MB）| `../wangi_jpgu2026/pestpp-glm.exe` | 本リポジトリの Releases、または PEST++ 公式配布 |
| `wangi.hds`（任意, 予備 IC）| `../wangi_jpgu2026/wangi.hds` | 任意（`warmstart_base.hds` があれば不要）|

> ⚠️ `mf6.exe` は公式リリースに無い **SWI+潮汐 対応の特殊ビルド**。公式の `get-modflow` では入手できない。

## データ配置の方針

- **GitHub（本リポジトリ）**: コード・PEST 制御・入力 `.npy`・成果（図・レポート・CSV）
- **Dropbox / Releases**: 実行体、および `phase3b_tidal_*` などの再生成可能な大容量出力（git 対象外）

## 実行環境（参考）

flopy 3.9.2 / Python 3.9–3.11 / MODFLOW 6（SWI ビルド）/ pestpp-glm 5.2.22。
warm-start（`warmstart_base.hds` を初期条件に使用）により、PEST の全 run が収束（0 failed）、1 forward ≒ 60–90 秒。

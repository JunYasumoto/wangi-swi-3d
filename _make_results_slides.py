# -*- coding: utf-8 -*-
"""Results summary deck: Wangi 3D SWI PEST calibration — current state (detailed)."""
import pathlib
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from PIL import Image

W = pathlib.Path(__file__).resolve().parent
FIG = W / "figs"

ACCENT = RGBColor(0xC1, 0x5F, 0x3C)
DARK   = RGBColor(0x2B, 0x2B, 0x2B)
GREY   = RGBColor(0x66, 0x66, 0x66)
LIGHT  = RGBColor(0xF2, 0xEE, 0xE9)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
GREEN  = RGBColor(0xD9, 0xEA, 0xD3)
GREEND = RGBColor(0x3C, 0x8C, 0x4A)
HDR    = RGBColor(0x40, 0x40, 0x40)
JP = "Yu Gothic UI"

prs = Presentation()
prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]


def _set(run, size, color=DARK, bold=False, font=JP):
    run.font.size = Pt(size); run.font.bold = bold
    run.font.color.rgb = color; run.font.name = font


def box(s, l, t, w, h, fill=None, line=None):
    sp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h); sp.shadow.inherit = False
    if fill is None: sp.fill.background()
    else: sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line is None: sp.line.fill.background()
    else: sp.line.color.rgb = line
    return sp


def text(s, l, t, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6):
    tb = s.shapes.add_textbox(l, t, w, h); tf = tb.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    for i, item in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space)
        txt, kw = item; kw = dict(kw); p.level = kw.pop("level", 0)
        r = p.add_run(); r.text = txt; _set(r, **kw)
    return tb


def add_image_fit(s, path, l, t, w, h):
    im = Image.open(path); ar = im.size[0] / im.size[1]
    if w / h > ar: nh = h; nw = int(h * ar)
    else: nw = w; nh = int(w / ar)
    s.shapes.add_picture(str(path), l + (w - nw) // 2, t + (h - nh) // 2, nw, nh)


def header(s, title, kicker=None):
    box(s, 0, 0, SW, Inches(1.1), fill=DARK)
    box(s, 0, Inches(1.1), SW, Pt(4), fill=ACCENT)
    text(s, Inches(0.5), Inches(0.1), SW - Inches(1), Inches(0.9),
         [(title, dict(size=24, color=WHITE, bold=True))], anchor=MSO_ANCHOR.MIDDLE)
    if kicker:
        text(s, Inches(0.55), Inches(0.13), Inches(6), Inches(0.3),
             [(kicker, dict(size=11, color=ACCENT, bold=True))])


def bruns(bullets, big=18, small=14):
    r = []
    for b in bullets:
        txt, lvl = (b if isinstance(b, tuple) else (b, 0))
        pre = "■ " if lvl == 0 else ("– " if lvl == 1 else "  · ")
        r.append((pre + txt, dict(size=big if lvl == 0 else small,
                  color=DARK if lvl == 0 else GREY, bold=(lvl == 0), level=lvl)))
    return r


def content(title, bullets, kicker=None, top=1.45):
    s = prs.slides.add_slide(BLANK); header(s, title, kicker)
    text(s, Inches(0.7), Inches(top), SW - Inches(1.4), SH - Inches(top + 0.4),
         bruns(bullets), space=9)
    return s


def content_img(title, bullets, img, kicker=None, img_w=6.0):
    s = prs.slides.add_slide(BLANK); header(s, title, kicker)
    text(s, Inches(0.6), Inches(1.4), Inches(13.333 - img_w - 1.0), SH - Inches(1.8),
         bruns(bullets, 17, 13), space=8)
    if (FIG / img).exists():
        add_image_fit(s, FIG / img, Inches(13.333 - img_w - 0.35), Inches(1.35),
                      Inches(img_w), SH - Inches(1.7))
    return s


def img_full(title, img, caption=None, kicker=None):
    s = prs.slides.add_slide(BLANK); header(s, title, kicker)
    ch = Inches(0.45) if caption else Inches(0.1)
    if (FIG / img).exists():
        add_image_fit(s, FIG / img, Inches(0.4), Inches(1.3), SW - Inches(0.8),
                      SH - Inches(1.4) - ch)
    if caption:
        text(s, Inches(0.6), SH - ch - Inches(0.05), SW - Inches(1.2), ch,
             [(caption, dict(size=13, color=GREY))], align=PP_ALIGN.CENTER)
    return s


def table(title, data, col_w, kicker=None, highlight=None, fs=12, top=1.5):
    s = prs.slides.add_slide(BLANK); header(s, title, kicker)
    rows, cols = len(data), len(data[0])
    tw = SW - Inches(1.0)
    gt = s.shapes.add_table(rows, cols, Inches(0.5), Inches(top), tw,
                            Inches(0.4 * rows)).table
    gt.first_row = False; gt.horz_banding = False
    tot = sum(col_w)
    for j, cw in enumerate(col_w):
        gt.columns[j].width = int(tw * cw / tot)
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            c = gt.cell(i, j); c.margin_top = Pt(2); c.margin_bottom = Pt(2)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = c.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER if j > 0 else PP_ALIGN.LEFT
            r = p.add_run(); r.text = str(val)
            if i == 0:
                _set(r, fs, WHITE, bold=True); c.fill.solid(); c.fill.fore_color.rgb = HDR
            else:
                _set(r, fs, DARK, bold=(highlight is not None and row[0] == highlight))
                c.fill.solid()
                c.fill.fore_color.rgb = GREEN if (highlight and row[0] == highlight) else WHITE
    return s


# ============================================================ 1 TITLE
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, SW, SH, fill=DARK); box(s, 0, Inches(4.5), SW, Pt(5), fill=ACCENT)
text(s, Inches(0.9), Inches(1.9), SW - Inches(1.8), Inches(2.4), [
    ("Wangi 3D 海水侵入モデル", dict(size=30, color=WHITE, bold=True)),
    ("PEST キャリブレーション結果 — 現状まとめ", dict(size=30, color=ACCENT, bold=True)),
], space=12)
text(s, Inches(0.95), Inches(4.75), SW - Inches(1.8), Inches(1.5), [
    ("MODFLOW 6 (SWI) + flopy + PEST++  /  探索 → 主結果 → 感度 → 診断 → 不確実性",
     dict(size=15, color=LIGHT)),
    ("2026-06 時点の計算結果サマリ", dict(size=13, color=GREY)),
], space=8)

# ============================================================ 2 TL;DR
content("結論 (TL;DR)", [
    "主結果 A-clean: 宙水 3 井戸を除外した 14 井戸・3-zone K2 キャリブレーション",
    ("head RMSE 1.75 m、非現実的な涵養を使わない物理的に妥当な解", 1),
    "鍵は『観測井の水理状態の再分類』— 全井戸を無理に合わせない",
    ("perched(宙水)/boundary-controlled を同化対象から外す", 1),
    "同化可能な情報は SSE 透水性に集中 (k2_sse = 1.60, FOSM で identifiable)",
    ("NW・CENT は K2 非感度 / 残る残差は SSE の物理的不均質", 1),
    "パラメータ追加 (recharge / SSE 分割) では本質的に改善しないと確認済",
], kicker="SUMMARY")

# ============================================================ 3 設定
content("モデル・データ設定", [
    "MODFLOW 6 + SWI (海水侵入) + 潮汐, flopy で構築",
    ("3 層構造, 816 × 767 格子 (約 188 万セル/層), 定常 SS", 1),
    ("warm-start: base 収束解を初期条件に (全 run 0 failed)", 1),
    "観測: 井戸 20 本の水頭 (PPP 真値ベース)",
    ("同化対象は最終的に 14 本 (宙水 6 本を除外)", 1),
    "推定対象: 層2 透水係数 K2 のゾーン別乗数 (NW / CENT / SSE)",
    ("最適化: PEST++ GLM, NOPTMAX=3, Φ = Σ(重み×残差²)", 1),
], kicker="SETUP")

# ============================================================ 4 シナリオ表
table("全シナリオ一覧", [
    ["シナリオ", "井戸", "params", "Φ", "RMSE(m)", "k2_sse", "位置づけ"],
    ["base", "17", "0", "89.96", "2.21", "—", "K2=1 基準 (宙水込み)"],
    ["C", "17", "2", "89.96", "—", "—", "global 2変数: 改善ゼロ"],
    ["A4", "17", "3", "80.46", "2.22", "0.50", "3-zone K2 (探索)"],
    ["B", "17", "4", "77.86", "2.18", "0.86", "+global 涵養 (探索)"],
    ["D", "17", "5", "70.78", "2.07", "2.00", "+CENT 涵養 (診断/非現実)"],
    ["A-clean", "14", "3", "42.74", "1.75", "1.60", "★主結果 (宙水除外)"],
    ["strict-12", "12", "3", "28.03", "1.53", "1.52", "頑健性 (ww05/08 も除外)"],
    ["SSE-split", "12", "4", "27.78", "—", "c2.0/i1.45", "診断: 分割は無効"],
], col_w=[1.1, 0.5, 0.6, 0.7, 0.8, 0.9, 2.4], highlight="A-clean", kicker="OVERVIEW", fs=12)
text(prs.slides[-1], Inches(0.5), SH - Inches(0.9), SW - Inches(1.0), Inches(0.7),
     [("注: Φ は同化井戸数が変わると非比較 (17→14→12 で系列が分かれる)。RMSE は各セットの clean head RMSE。",
       dict(size=12, color=GREY))])

# ============================================================ 5 探索 overview
img_full("探索フェーズ C/A/B/D の全体像", "scenario_comparison_CABD.png",
         "(a) Φ群別  (b) パラメータ vs 上下限  (c) obs-sim  (d) ゾーン別RMSE。Φ は下がるが D は涵養が非現実値。",
         kicker="EXPLORATION")

# ============================================================ 6 探索 解説
content("探索フェーズの読み解き", [
    "C (global rch + k2): Φ 89.96 のまま — 全域一律では zonal 残差を補正できない",
    "A4 (3-zone K2): Φ 80.46 (−10.6%) — NW/SSE は内部最適、CENT は床張り付き",
    "B (+global 涵養): Φ 77.86 — CENT 改善も SSE を overshoot",
    "D (+CENT 涵養): Φ 70.78 だが涵養 1800/5400 mm/yr の非現実値",
    ("5 params 中 3 つが bound 張り付き = 過剰適合のサイン", 1),
    "→ Φ 低下は『パラメータで残差を吸収』しているだけ",
], kicker="EXPLORATION")

# ============================================================ 7 CENT structural
content_img("転換点: CENT 残差の正体", [
    "中央の ww04/ww11/ww12 は ~200 m 以内なのに観測水頭が 2.4/6.7/7.5 m",
    ("5 m の局所差を連続帯水層では再現不能", 1),
    "CENT 涵養を上げると ww11/12 は上がるが ww04 を過大予測",
    ("同一ゾーン内で逆方向の補正が必要", 1),
    "→ ww11/ww12 は ww04 と別の水理系 (宙水の疑い)",
], "scenario_CENT_structural.png", kicker="TURNING POINT", img_w=6.2)

# ============================================================ 8 perched diag
content_img("宙水(perched)の診断", [
    "指標: depth-to-water = 地表標高 − 観測水頭",
    ("宙水 ≈ 0 (地下水面が地表), 広域井戸 > 2 m", 1),
    "該当: ww10 (沿岸30m, 水頭15.4=地表), ww11, ww12",
    ("海の塩水境界と decoupled = 広域帯水層モデルの対象外", 1),
    "除外で base Φ が 89.96 → 48.06 (宙水3本が ~42 を占有)",
], "Aclean_perched_diagnostic.png", kicker="DIAGNOSIS", img_w=6.2)

# ============================================================ 9 classification
content_img("観測井の再分類", [
    "水理状態で 3 分類:",
    ("regional: 広域帯水層 (同化対象)", 1),
    ("perched: 地下水面が地表 (宙水, 除外)", 1),
    ("boundary-controlled: 沿岸で GHB 支配・K 非感度", 1),
    "『全井戸を合わせる』でなく『同化すべき集合を定義』",
    ("= モデル概念の整理 (恣意的除外ではない)", 1),
], "paper_well_classification.png", kicker="RECLASSIFY", img_w=5.8)

# ============================================================ 9b chem validation
content_img("独立検証: 化学・年代が分類を裏付け", [
    "head-based 分類を SF6 年代・海水混合率で独立検証 (ww01–10)",
    "SF6 年代:",
    ("perched (ww01,ww10) = modern <1yr → 局所涵養・広域と decoupled", 1),
    ("regional (ww02/04/07/09) = 8–18 yr の老齢集団", 1),
    "ww05/ww08 (疑い・保持) = 13–14 yr = 広域と同年代",
    ("→ 宙水でなく広域水。A-clean で残した判断を裏付け", 1),
    "モデルも傍証: perched で obs modern vs sim 9–9000 yr",
    ("海水混合率は沿岸位置を反映 (perched 判定とは別軸)", 1),
], "chem_age_validation.png", kicker="INDEPENDENT VALIDATION", img_w=6.6)

# ============================================================ 10 A-clean numbers
table("主結果 A-clean — 数値詳細", [
    ["ゾーン", "n", "RMSE(m)", "bias(m)", "Φ寄与", "評価"],
    ["CENT (ww04)", "1", "0.70", "−0.70", "0.49", "良好"],
    ["NW", "5", "1.17", "+0.04", "6.82", "良好 (平衡)"],
    ["SSE", "8", "2.11", "+1.07", "35.44", "残差集中 (83%)"],
    ["全 14 井戸", "14", "1.75", "+0.58", "42.74", "—"],
], col_w=[1.4, 0.5, 0.8, 0.8, 0.8, 1.6], highlight="全 14 井戸", kicker="MAIN RESULT", fs=13, top=1.5)
text(prs.slides[-1], Inches(0.5), Inches(4.4), SW - Inches(1.0), Inches(2.5), bruns([
    "最適パラメータ: k2_sse = 1.60 (有意), k2_nw = 2.0・k2_cent = 2.0 (上限・弱拘束)",
    ("宙水除外で K2 最適方向が逆転 (下→上): 残った広域井戸は僅かに過大予測", 1),
    "Φ 推移: 48.06 (clean base) → 43.22 → 42.99 → 42.74 (全 run 0 failed)",
], 16, 13), space=8)

# ============================================================ 11 A-clean fig
img_full("主結果 A-clean — 当てはまり", "Aclean_calibration_result.png",
         "(a)obs-sim (b)Φ群別 (c)ゾーンRMSE (d)SSE残差。regional は 1:1 付近、残差は SSE に集中。",
         kicker="MAIN RESULT")

# ============================================================ 12 robustness
content("頑健性: strict-clean-12", [
    "宙水疑いの ww05/ww08 も除外して 12 井戸で再キャリブレーション",
    "主結果パラメータはほぼ不変:",
    ("k2_sse: 1.60 → 1.52 (−5%)", 1),
    ("k2_nw / k2_cent: 2.0 / 2.0 (同一)", 1),
    "obs_sse Φ の減少 (35→21) は除外2本の misfit 分で、パラメータ変化ではない",
    "→ A-clean の推定は観測選別に対して頑健",
], kicker="ROBUSTNESS")

# ============================================================ 13 SSE split diag
content("診断: SSE サブゾーン分割", [
    "SSE を海岸距離 500 m で coastal/inland に分割 (4 params)",
    "Φ 28.05 → 27.78 (−1%, 実質改善なし)",
    ("k2_sse_coast → 上限漂流 (ww06 は境界支配で K 非感度)", 1),
    ("k2_sse_inland → 単一値を再現", 1),
    "内陸残差は ww15(+2.7) vs ww07/13(−1〜2) の逆符号 = 既約な不均質",
    "→ SSE misfit はサブゾーン化で解けない物理的構造",
    ("単一 k2_sse が適切なパラメータ化レベル = 過剰パラメータ化の回避根拠", 1),
], kicker="DIAGNOSTIC")

# ============================================================ 14 FOSM
content_img("不確実性: FOSM", [
    "A-clean 最適点で事後共分散を評価",
    "k2_sse のみ identifiable:",
    ("事後σ 0.146 vs 事前 0.206 (−29%)", 1),
    ("k2_sse = 1.59, 1σ [1.14, 2.22] (×/÷1.40)", 1),
    "k2_nw / k2_cent は posterior ≈ prior (未拘束)",
    "パラメータ相関 |corr| < 0.11 → トレードオフなし",
], "Aclean_FOSM.png", kicker="UNCERTAINTY", img_w=6.4)

# ============================================================ 15 残差構造
content("残差構造のまとめ", [
    "NW (5本): bias ≈ 0、良好に同化",
    "CENT: 宙水 ww11/12 を除けば ww04 のみ、ほぼ完璧 (Φ 0.5)",
    "SSE (残差の主座, 83%):",
    ("沿岸 ww06/ww17: 海岸 GHB 境界支配で K 非感度 (系統的な +残差)", 1),
    ("内陸 ww15(+) vs ww07/ww13(−): 真の局所不均質 (逆符号)", 1),
    "→ 残差は『未推定パラメータ』ではなく物理構造・境界条件に由来",
], kicker="RESIDUAL STRUCTURE")

# ============================================================ 16 現状と次手
content("現状の到達点と未決事項", [
    "到達点:",
    ("物理的に妥当な主結果 A-clean を確定 (RMSE 1.75 m)", 1),
    ("頑健性・診断・不確実性まで一通り評価済", 1),
    ("成果物 (図・表・セッションノート・summary.csv) 整備済", 1),
    "未決・選択肢:",
    ("ww11/12 等の宙水仮説を地質・化学データで裏付け", 1),
    ("SSE 内陸不均質の概念的説明 (層構造・局所地質)", 1),
    ("論文化: A-clean を主, strict-12/SSE-split/FOSM を補助解析として提示", 1),
], kicker="STATUS & NEXT")

# ============================================================ 17 ファイル
content("関連ファイル", [
    "SESSION_2026-06-15_PEST_Aclean_MAIN.md — 主結果の詳細記録",
    "scenario_summary_ABD.csv — 全 8 シナリオの数値",
    "diag_Aclean / diag_strict12 / diag_ssesplit .csv — 各最適の井戸別診断",
    "pest_Aclean.pst / pest_strict12.pst — 制御ファイル snapshot",
    "pest.par.usum.csv / pest.post.cov — FOSM 事後不確実性",
    "figs/ — 本スライドの全図 (paper_*, Aclean_*, scenario_*)",
], kicker="FILES")

out = W / "Wangi_SWI_calibration_results.pptx"
prs.save(str(out))
print("saved", out.name, "slides:", len(prs.slides._sldIdLst))

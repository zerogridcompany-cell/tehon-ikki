"""段0 見る：zukan.json から 設計図.md（人が読む表）と 一覧.html（カットごとの最初・真ん中・最後の絵＋数字）を作る。
python3 miru_report.py <作業>
一覧.html は手元だけで開ける静かな HTML（外のサイトを読まん・絵は zukan/thumbs/ の jpg）
"""
import html, json, os, sys
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mk
W_ = os.path.abspath(sys.argv[1]); Z = f"{W_}/zukan"; zk = json.load(open(f"{Z}/zukan.json"))
M = zk["meta"]; C = zk["cuts"]; O = zk.get("oto") or {}
isn = lambda v: isinstance(v, dict) and v.get("v") == "なし"


def kam(r):
    k = r["kamera"]; return "・".join(k["kind"]) + (f" 寄{k['zoom_pct_s']:+.0f}%/s" if abs(k.get("zoom_pct_s", 0)) >= 2 else "") + \
        (f" 振{k['pan_px_s'][0]:+.0f},{k['pan_px_s'][1]:+.0f}px/s" if max(abs(v) for v in k.get("pan_px_s", [0, 0])) >= 0.02 * M["W"] else "") + \
        (f" 揺{k['shake_px']}px" if k.get("shake_px", 0) >= 0.7 else "")


def aw(r):
    a = r["awase"]
    if a.get("v") in ("頭",): return "頭"
    if isn(a): return "なし（" + a["konkyo"] + "）"
    return f"{a['v']} {a['zure_koma']:+d}コマ"


def kr(r):
    k = r["kirikae"]; d = {"hard": "スパッ", "flash": "光る", "dissolve": "溶け", "whip": "振り", "glitch": "色ずれ", "zoom-through": "寄り抜け", "頭": "頭"}
    return d.get(k["kind"], k["kind"])


def moj(r):
    m = r["moji"]
    if isn(m): return "—"
    return " ".join(f"{w['w']}[{w['f0']}-{w['f1']}・高{w['takasa_pct']}%]" for w in m[:6]) + (f" ほか{len(m) - 6}" if len(m) > 6 else "")


def mgs(r):
    m = r["mg"]
    if isn(m): return "—"
    return "・".join(sorted(set(x["kind"][:8] for x in m)))


def oto(r):
    o = r["oto"]
    if isn(o): return "—"
    s = []
    if not isn(o["kouka"]): s.append(f"効果音{len(o['kouka'])}")
    if not isn(o["koe"]): s.append(f"声{len(o['koe'])}語")
    if not isn(o["kick"]): s.append(f"低音{len(o['kick'])}")
    return "・".join(s) or "—"


L = []
L.append(f"# 設計図（段0 見る）\n\n手本＝{os.path.basename(M['ref'])}・{M['W']}x{M['H']}・{M['fps']}fps・{M['frames']}コマ・{M['dur']}秒・抜けたコマ {M['pts_gaps'] or 'なし'}\n")
L.append("🔒 作る段はこの数字だけを使う。測り直さん（差の検査は最後の門だけ）。全部の数字＝zukan.json\n")
if O:
    L.append(f"## 音\n- 大きさ：{O['lufs'].get('I')} LUFS・幅 {O['lufs'].get('LRA')} LU・最大 {O['lufs'].get('peak')} dBFS")
    L.append("- 曲の区間：")
    for s in O["kyoku"]:
        L.append(f"  - {s['a']}〜{s['b']}秒｜{s['name']}｜1分の拍 {s.get('bpm')}｜曲の秒＝手本の秒＋{s.get('at0')}｜{'不明' if s.get('fumei') else 'Shazam ' + str(s['konkyo'].get('shazam')) + '窓'}")
    for k in O.get("kyoku_kirikae") or []:
        L.append(f"  - 替わり {k['t']}秒：前 {k['mae_db']}dB→谷 {k['tani_db']}dB（{k['tani_t']}秒）→後 {k['ato_db']}dB")
    kw = O.get("koe_words"); L.append(f"- 声：{'なし（' + kw['konkyo'] + '）' if isn(kw) else str(len(kw)) + '語'}・効果音 {len(O.get('sfx') or [])}個・強い低音 {0 if isn(O.get('kick')) else len(O.get('kick') or [])}個\n")
L.append("## 区間の決まり（カットは何に合わせとるか）")
for k in zk.get("kimari", []):
    L.append(f"- {k['a']}〜{k['b']}秒（{k['name'][:30]}・拍 {k.get('bpm')}）：{k['pick']}｜{k['konkyo']}")
L.append("\n## カット（コマは手本のそのままの番号・f1 は次のカットの頭）\n")
L.append("| # | コマ | 秒 | 切り替え | 合わせ先 | カメラ | 動画か | 色 L/a/b・コントラスト | 鋭さ・粒 | 加工 | 主役 | 字 | 飾り | 音 |")
L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in C:
    i = r["iro"] or {}
    kak = "・".join(x for x, ok in (("網点", (r.get("kumi") or {}).get("ari")), ("色収差", (r.get("shuushuu") or {}).get("ari")), ("暗い縁", (r.get("fuchi") or {}).get("ari"))) if ok) or "—"
    sy = r.get("shuyaku") or {}
    syt = "—" if isn(sy) else f"{sy.get('kind', '')[:2]} 高{sy.get('h')}%"
    tb = r["tsubu"] if not isn(r["tsubu"]) else "—"
    L.append(f"| {r['i']} | {r['f0']}–{r['f1'] - 1} | {r['t0']:.2f}（{r['n']}コマ） | {kr(r)} | {aw(r)} | {kam(r)} | {r['seishi']['kind']} | {i.get('L')}/{i.get('a')}/{i.get('b')}・{i.get('contrast')} | {r['surudosa']}・{tb} | {kak} | {syt} | {html.escape(moj(r))} | {mgs(r)} | {oto(r)} |")
open(f"{Z}/設計図.md", "w").write("\n".join(L) + "\n")

# ── 一覧.html ──
TH = f"{Z}/thumbs"; os.makedirs(TH, exist_ok=True)
need = {}
for r in C:
    need[r["i"]] = [r["f0"], r["f0"] + (r["f1"] - r["f0"]) // 2, r["f1"] - 1]
miss = sorted({f for v in need.values() for f in v if not os.path.exists(f"{TH}/{f:05d}.jpg")})
if miss:
    fr = mk.native(M["ref"], miss, M["W"], M["H"], scale_w=240)
    for f, im in fr.items(): cv2.imwrite(f"{TH}/{f:05d}.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 80])
cards = []
for r in C:
    imgs = "".join(f'<figure><img src="thumbs/{f:05d}.jpg" loading="lazy" alt=""><figcaption>{f}</figcaption></figure>' for f in need[r["i"]])
    i = r["iro"] or {}
    rows = [("切り替え", kr(r)), ("合わせ先", aw(r)), ("カメラ", kam(r)), ("動画か", f"{r['seishi']['kind']}（N {r['seishi']['N']}）"),
            ("色", f"L{i.get('L')} a{i.get('a')} b{i.get('b')}・コントラスト {i.get('contrast')}・彩度 {i.get('saido')}"),
            ("鋭さ・粒", f"{r['surudosa']}・{r['tsubu'] if not isn(r['tsubu']) else '—'}"), ("字", moj(r)), ("飾り", mgs(r)), ("音", oto(r))]
    dl = "".join(f"<dt>{html.escape(a)}</dt><dd>{html.escape(str(b))}</dd>" for a, b in rows)
    cards.append(f'<section class="c"><h2>#{r["i"]} <span>{r["f0"]}–{r["f1"] - 1}・{r["t0"]:.2f}秒・{r["n"]}コマ</span></h2><div class="th">{imgs}</div><dl>{dl}</dl></section>')
page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>手本の一覧</title><style>
:root{{--bg:#f6f5f2;--fg:#1d1d1b;--mut:#6b6a66;--card:#fff;--line:#e2e0da}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,"Hiragino Sans",sans-serif;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}} p.m{{color:var(--mut);margin:0 0 16px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}}
.c{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}}
.c h2{{font-size:15px;margin:0 0 6px}} .c h2 span{{color:var(--mut);font-weight:400;font-size:12px}}
.th{{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}} figure{{margin:0}} img{{width:100%;display:block;border-radius:4px}}
figcaption{{font-size:11px;color:var(--mut);text-align:center}}
dl{{display:grid;grid-template-columns:5.5em 1fr;gap:2px 8px;margin:8px 0 0;font-size:12px}} dt{{color:var(--mut)}} dd{{margin:0;overflow-wrap:anywhere}}
</style></head><body><h1>手本の一覧（段0 見る）</h1>
<p class="m">{html.escape(os.path.basename(M['ref']))}・{M['W']}x{M['H']}・{M['fps']}fps・{M['frames']}コマ・カット {len(C)}・全部の数字＝zukan.json</p>
<div class="g">{''.join(cards)}</div></body></html>"""
open(f"{Z}/一覧.html", "w").write(page)
print("書いた", f"{Z}/設計図.md", f"{Z}/一覧.html")

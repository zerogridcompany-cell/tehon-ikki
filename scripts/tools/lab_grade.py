"""lab_grade.py  1枚の絵の色を、手本の決まったコマ（の決まった所）の Lab の平均と幅へ移す（51 の note_grade.py・shot_grade.py・fb_grade.py を1本に）。
使い方：
  python3 lab_grade.py <作業> --id <id> [--frame f]                 一枚絵を、その絵が乗っとる所で手本のコマへ（既定＝絵の真ん中のコマ）。green/<id>.png に上書き・元は arai/grade_bak/<id>.png
  python3 lab_grade.py <作業> --in a.png --out b.png --frame f [--box x0,y0,x1,y1] [--min-lum 60]   別の絵（使い回し・Codex の寄りの絵）を手本のコマの箱へ
入れる物：手本・caps.json（字幕の箱は測らん）。--min-lum＝手本の箱の中で暗い所（黒い外）を測らん
出す物：色を移した絵（幅の比は 0.6〜1.6 で頭打ち）・移した量（Lab の平均の差）を出す
効いた数字（51）：同じ絵を違う手本のコマで使い回す所（札の連打・使い回しの場面）で ΔE 2.5→1.7。札の角の寄り（Codex の絵）を手本の札の紙だけに合わせた
採る条件：同じ絵を2か所以上で使う時・green_fit を通さん絵（描き分け・寄りの絵）だけ。green_fit 済みの絵は色を2次式で当て済み＝重ねるとかえって外れることがある＝書き出して ΔE が 0.5 以上下がる時だけ残す
"""
import argparse, json, os, shutil, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, one, load_caps, cap_mask, footprint, lab_stats, lab_apply

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--id"); ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
ap.add_argument("--frame", type=int); ap.add_argument("--box"); ap.add_argument("--min-lum", type=float, default=-1); ap.add_argument("--clip", default="0.6,1.6")
a = ap.parse_args()
clip = tuple(map(float, a.clip.split(",")))
ref = ref_path(a.w); W, H, _, _ = probe(ref); caps = load_caps(a.w)
if a.id:
    G = json.load(open(os.path.join(a.w, "proj", "src", "green.json"))); p = G[a.id]
    f = a.frame if a.frame is not None else (p["f0"] + p["f1"]) // 2
    src = os.path.join(a.w, "proj", "public", "green", f"{a.id}.png"); bak = os.path.join(a.w, "arai", "grade_bak", f"{a.id}.png")
    if not os.path.exists(bak):
        os.makedirs(os.path.dirname(bak), exist_ok=True); shutil.copy(src, bak)
    pl = cv2.imread(bak); M = np.array(p["M"][str(f)], np.float64).reshape(2, 3)
    r = one(ref, f); mk = footprint(p, M, W, H) & ~cap_mask(caps, f, W, H)
    wv = cv2.warpAffine(pl, M, (W, H), flags=cv2.INTER_LINEAR)
    ma, sa = lab_stats(wv[mk]); mb, sb = lab_stats(r[mk])
    cv2.imwrite(src, lab_apply(pl, ma, sa, mb, sb, clip)); outp = src
else:
    if a.frame is None or not a.inp or not a.out:
        raise SystemExit("--in・--out・--frame が要る")
    im = cv2.imread(a.inp); r = one(ref, a.frame)
    mk = ~cap_mask(caps, a.frame, W, H)
    if a.box:
        x0, y0, x1, y1 = map(int, a.box.split(",")); b = np.zeros_like(mk); b[y0:y1, x0:x1] = True; mk &= b
    if a.min_lum >= 0:
        mk &= r.mean(2) > a.min_lum
    ma, sa = lab_stats(im.reshape(-1, 3)); mb, sb = lab_stats(r[mk])
    cv2.imwrite(a.out, lab_apply(im, ma, sa, mb, sb, clip)); outp = a.out
print("書いた", outp, "手本のコマ", a.frame if a.frame is not None else f, "移した量（Lab 8bit の平均の差）", [round(float(x), 1) for x in mb - ma])

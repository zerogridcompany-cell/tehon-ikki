"""字幕の1語ずつ、大きさ（fs）と位置（x,y）を手本のコマに型合わせで当て直す。
python3 cap_fit.py <作業> [--write] [--min 0.04]
- 手本の字の線＝白黒の明るさ − ぼかし(σ6) の正の所（光や地の明るさを消す）
- 型＝うちの書体（look.json の太さ・横の伸び）でその語を描いた形を少しぼかした物
- 大きさ ×0.70〜1.40・位置は今から ±60px（横）±30px（縦）で一番相関の高い所。今より --min 以上良くなった語だけ変える
- 書いた後、同じ時に出とって重なる語は、先に出た語を後の語の出る前に消す（時刻の直し）
"""
import argparse, json, os, shutil, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--write", action="store_true"); ap.add_argument("--min", type=float, default=0.04); ap.add_argument("--no-time", action="store_true"); ap.add_argument("--ids")
a = ap.parse_args(); w = os.path.abspath(a.w)
L = json.load(open(f"{w}/proj/src/look.json")); C = json.load(open(f"{w}/proj/src/caps.json"))
FS = {"serif": f"{w}/proj/public/fonts/" + L.get("serifFile", "LibreBaskerville-Italic[wght].ttf"), "sans": f"{w}/proj/public/fonts/" + L.get("sansFile", "Inter[opsz,wght].ttf"), "plain": f"{w}/proj/public/fonts/TNR-Regular.ttf"}
def font(kind, fs):
    f = ImageFont.truetype(FS[kind], max(4, int(round(fs))))
    (f.set_variation_by_axes([L["serifW"]] if kind == "serif" else [32, L["sansW"]]) if kind != "plain" else None); return f
def glyph(c, fs):
    # 語の形（基準線の左＝原点からのずれ ox,oy 付き）
    f = font(c["kind"], fs); x0, y0, x1, y1 = f.getbbox(c["w"], anchor="ls")
    sx = L["serifSx"] if c["kind"] == "serif" else L["sansSx"]
    W_, H_ = x1 - x0 + 8, y1 - y0 + 8
    im = Image.new("L", (W_, H_), 0); ImageDraw.Draw(im).text((4 - x0, 4 - y0), c["w"], font=f, fill=255, anchor="ls")
    g = np.array(im, np.float32)
    g = cv2.resize(g, (max(2, int(round(W_ * sx))), H_))
    return cv2.GaussianBlur(g, (0, 0), 1.0), (x0 * sx - 4 * sx, y0 - 4)
def strokes(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return np.clip(g - cv2.GaussianBlur(g, (0, 0), 6), 0, None)
cache = {}
def ref(f):
    if f not in cache: cache[f] = strokes(cv2.imread(f"{w}/txt/f/{f + 1:05d}.jpg"))
    return cache[f]
def score_at(S, tpl, x, y):
    h, wd = tpl.shape; x, y = int(round(x)), int(round(y))
    if x < 0 or y < 0 or x + wd > S.shape[1] or y + h > S.shape[0]: return -1
    p = S[y:y + h, x:x + wd]; t = tpl - tpl.mean(); q = p - p.mean()
    return float((t * q).sum() / (np.sqrt((t * t).sum() * (q * q).sum()) + 1e-6))
changed = []
for c in C:
    if a.ids and c["i"] not in set(map(int, a.ids.split(","))): continue
    f = (c["f0"] + c["f1"]) // 2; S = ref(f)
    tpl, (ox, oy) = glyph(c, c["fs"]); base = score_at(S, tpl, c["x"] + ox, c["y"] + oy)
    best = (base, c["fs"], c["x"], c["y"])
    for k in np.arange(0.70, 1.41, 0.05):
        fs = c["fs"] * k; tpl, (ox, oy) = glyph(c, fs)
        x0, y0 = int(c["x"] + ox - 60), int(c["y"] + oy - 30)
        x1, y1 = x0 + 120 + tpl.shape[1], y0 + 60 + tpl.shape[0]
        x0c, y0c = max(0, x0), max(0, y0); x1c, y1c = min(S.shape[1], x1), min(S.shape[0], y1)
        win = S[y0c:y1c, x0c:x1c]
        if win.shape[0] < tpl.shape[0] or win.shape[1] < tpl.shape[1]: continue
        r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(r)
        if mv > best[0]: best = (mv, fs, x0c + ml[0] - ox, y0c + ml[1] - oy)
    if best[0] > base + a.min and best[0] > 0.3:
        changed.append((c["i"], c["w"], round(base, 2), round(best[0], 2), round(c["fs"], 1), round(best[1], 1), round(best[2] - c["x"]), round(best[3] - c["y"])))
        if a.write: c["fs"], c["x"], c["y"] = round(float(best[1]), 2), round(float(best[2]), 1), round(float(best[3]), 1)
print("変える語", len(changed), "／", len(C))
for ch in changed: print(ch)
# 時刻：同じ時に出て重なる語
def box(c):
    f = font(c["kind"], c["fs"]); x0, y0, x1, y1 = f.getbbox(c["w"], anchor="ls"); sx = L["serifSx"] if c["kind"] == "serif" else L["sansSx"]
    return (c["x"] + x0 * sx, c["y"] + y0, c["x"] + x1 * sx, c["y"] + y1)
fix = []
for i, p in enumerate(C):
    for q in C[i + 1:]:
        if q["f0"] > p["f1"] or p["f0"] > q["f1"]: continue
        A, B = box(p), box(q)
        if min(A[2], B[2]) - max(A[0], B[0]) > 4 and min(A[3], B[3]) - max(A[1], B[1]) > 4:
            first, last = (p, q) if p["f0"] <= q["f0"] else (q, p)
            if first["f0"] < last["f0"]:
                fix.append((first["i"], first["w"], first["f1"], last["f0"] - 1, last["w"]))
                if a.write and not a.no_time: first["f1"] = last["f0"] - 1
print("時刻を直す重なり", len(fix))
for x in fix: print(x)
if a.write:
    shutil.copy(f"{w}/proj/src/caps.json", f"{w}/proj/src/caps.json.bak_capfit")
    json.dump(C, open(f"{w}/proj/src/caps.json", "w"), ensure_ascii=False)

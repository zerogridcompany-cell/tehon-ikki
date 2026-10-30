"""字幕の1語ずつ、手本のコマで「出る・消える」コマを型合わせで測って f0・f1 を直す。
python3 cap_time.py <作業> [--write] [--pad 20]
- 型と手本の字の線は cap_fit.py と同じ。今の f0−pad 〜 f1+pad の各コマで、その語の位置（±6px）の相関を出す
- 出る＝相関が その語の一番高い値の 60% を初めて超えたコマ・消える＝最後に超えたコマ（途切れは2コマまで続きとみなす）
- 今との差が 2コマ以上の語だけ変える。短い語（--minlen 未満）・当たりの弱い語（--minsc 未満）・出るのずれが --maxd・消えるのずれが --maxd1 コマを超える所は触らん（同じ場所の別の語に反応する）。前の caps は caps.json.bak_captime
"""
import argparse, json, os, shutil
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--write", action="store_true"); ap.add_argument("--pad", type=int, default=20); ap.add_argument("--minlen", type=int, default=3); ap.add_argument("--minsc", type=float, default=0.7); ap.add_argument("--maxd", type=int, default=12); ap.add_argument("--maxd1", type=int, default=12)
a = ap.parse_args(); w = os.path.abspath(a.w)
L = json.load(open(f"{w}/proj/src/look.json")); C = json.load(open(f"{w}/proj/src/caps.json"))
FS = {"serif": f"{w}/proj/public/fonts/" + L.get("serifFile", "LibreBaskerville-Italic[wght].ttf"), "sans": f"{w}/proj/public/fonts/" + L.get("sansFile", "Inter[opsz,wght].ttf"), "plain": f"{w}/proj/public/fonts/TNR-Regular.ttf"}
N = len(os.listdir(f"{w}/txt/f"))
def glyph(c):
    f = ImageFont.truetype(FS[c["kind"]], max(4, int(round(c["fs"])))); (f.set_variation_by_axes([L["serifW"]] if c["kind"] == "serif" else [32, L["sansW"]]) if c["kind"] != "plain" else None)
    x0, y0, x1, y1 = f.getbbox(c["w"], anchor="ls"); sx = L["serifSx"] if c["kind"] == "serif" else L["sansSx"]
    W_, H_ = x1 - x0 + 8, y1 - y0 + 8
    im = Image.new("L", (W_, H_), 0); ImageDraw.Draw(im).text((4 - x0, 4 - y0), c["w"], font=f, fill=255, anchor="ls")
    g = cv2.resize(np.array(im, np.float32), (max(2, int(round(W_ * sx))), H_))
    return cv2.GaussianBlur(g, (0, 0), 1.0), (x0 * sx - 4 * sx, y0 - 4)
cache = {}
def S(f):
    if f not in cache:
        g = cv2.cvtColor(cv2.imread(f"{w}/txt/f/{f + 1:05d}.jpg"), cv2.COLOR_BGR2GRAY).astype(np.float32)
        cache[f] = np.clip(g - cv2.GaussianBlur(g, (0, 0), 6), 0, None)
    return cache[f]
ch = []
for c in C:
    tpl, (ox, oy) = glyph(c); h, wd = tpl.shape
    x, y = int(round(c["x"] + ox)), int(round(c["y"] + oy))
    fr = range(max(0, c["f0"] - a.pad), min(N - 1, c["f1"] + a.pad) + 1); sc = []
    for f in fr:
        s = S(f); x0, y0 = max(0, x - 6), max(0, y - 6); win = s[y0:y + h + 6, x0:x + wd + 6]
        if win.shape[0] < h or win.shape[1] < wd: sc.append(0); continue
        sc.append(float(cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED).max()))
    sc = np.array(sc); fr = list(fr)
    if sc.max() < 0.45: continue
    on = sc > 0.6 * sc.max()
    # 今の範囲の中で一番高いコマを含む連続の塊を取る（途切れ2コマまでつなぐ）
    pk = int(np.argmax(np.where([c["f0"] <= f <= c["f1"] for f in fr], sc, -1)))
    i0 = pk
    while i0 > 0 and (on[i0 - 1] or (i0 > 2 and on[i0 - 2]) or (i0 > 3 and on[i0 - 3])): i0 -= 1
    i1 = pk
    while i1 < len(fr) - 1 and (on[i1 + 1] or (i1 < len(fr) - 2 and on[i1 + 2]) or (i1 < len(fr) - 3 and on[i1 + 3])): i1 += 1
    while not on[i0] and i0 < pk: i0 += 1
    while not on[i1] and i1 > pk: i1 -= 1
    n0, n1 = fr[i0], fr[i1]
    if len(c["w"].strip(".,?!'")) < a.minlen or sc.max() < a.minsc: continue
    if abs(n0 - c["f0"]) > a.maxd: n0 = c["f0"]
    if abs(n1 - c["f1"]) > a.maxd1: n1 = c["f1"]
    if abs(n0 - c["f0"]) >= 2 or abs(n1 - c["f1"]) >= 2:
        ch.append((c["i"], c["w"], c["f0"], n0, c["f1"], n1, round(float(sc.max()), 2)))
        if a.write: c["f0"], c["f1"] = int(n0), int(n1)
print("時刻を変える語", len(ch), "／", len(C))
for x in ch: print(x)
if a.write:
    shutil.copy(f"{w}/proj/src/caps.json", f"{w}/proj/src/caps.json.bak_captime")
    json.dump(C, open(f"{w}/proj/src/caps.json", "w"), ensure_ascii=False)

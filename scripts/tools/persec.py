"""persec.py  1コマずつの動きの量を3つの数で測る（洗い出し・場面ごとに手本とうちを比べる用。51 の persec.py の汎用版＝mp4 を直に読める）。
使い方：python3 persec.py <mp4|コマのフォルダ(*.jpg)> <出力.json> [--a f0 --b f1] [--vs 比べる.mp4]
1コマごとに：
  d  ＝前のコマとの明るさの差の平均（横 320・縦は1本目の比＝r2 は 320x180 の灰・動いたコマ＝0.3 超）
  sm ＝16x9 のマス（縦長は 9x16）で「少しだけ動いた」マス（差 0.8〜12）の割合＝細かい動き（粒・揺れ）
  sh ＝形の動き（横 240・縦は比で4の倍数＝r2 は 240x136・4x4 のマスごとに Farneback のフローをアフィンで当てた残り＝katachi と同じ）。カット（差 40 超）は −1
出す物：[{"f","d","sm","sh"}…]。--vs を付けると同じ範囲を両方測って「d の比（うち÷手本）・sm の平均・sh の平均」を並べる
効いた数字（51）：fx の揺れが手本の 2〜3倍（sunset 0.55 対 1.5）と分かった→fx_smooth で動きの比 2.46→1.03。粒の要る場面（sm が手本より低い）を拾った
採る条件：測るだけ。d の比が 1.5 以上＝fx_smooth の候補・0.67 以下＝止まりすぎ（hold か粒）・sm が手本の半分以下＝粒（grain_need）の候補
"""
import argparse, glob, json, os, subprocess, sys
import cv2
import numpy as np

cv2.setNumThreads(2); np.seterr(all="ignore")  # macOS の Accelerate が matmul で出す空の警告を消す（値は有限）
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--a", type=int, default=0); ap.add_argument("--b", type=int); ap.add_argument("--vs")
g = ap.parse_args()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo_mp4
if os.path.isdir(g.src): _h, _w = cv2.imread(sorted(glob.glob(os.path.join(g.src, "*.jpg")))[0]).shape[:2]
else: _G = geo_mp4(g.src); _w, _h = _G["W"], _G["H"]
SW = 320; SH = int(round(_h * SW / _w / 2) * 2)  # 10/30 geo：1本目の大きさの比（r2 は 320x180）
CX, CY = (16, round(16 * _h / _w)) if _w >= _h else (round(16 * _w / _h), 16)  # マスの数（r2 は 16x9）
W, H = 240, int(round(240 * _h / _w / 4) * 4)  # r2 は 240x136
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
gh, gw = H // 4, W // 4
Xs = []
for i in range(4):
    for j in range(4):
        sl = (slice(i * gh, (i + 1) * gh), slice(j * gw, (j + 1) * gw))
        Xs.append((sl, np.stack([xs[sl].ravel(), ys[sl].ravel(), np.ones(gh * gw)], 1)))


def frames(src):
    if os.path.isdir(src):
        for p in sorted(glob.glob(os.path.join(src, "*.jpg")))[g.a: g.b + 1 if g.b is not None else None]:
            yield cv2.resize(cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY), (SW, SH), interpolation=cv2.INTER_AREA)
        return
    n = (g.b - g.a + 1) if g.b is not None else 10 ** 7
    pr = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-i", src, "-an", "-vf",
                           f"select=between(n\\,{g.a}\\,{g.a + n - 1}),scale={SW}:{SH},format=gray", "-vsync", "0", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    while True:
        b = pr.stdout.read(SW * SH)
        if len(b) < SW * SH:
            break
        yield np.frombuffer(b, np.uint8).reshape(SH, SW)
    pr.wait()


def measure(src):
    res, prev = [], None
    for k, gr in enumerate(frames(src)):
        s320 = gr.astype(np.int16); sm_ = cv2.resize(gr, (W, H))
        if prev is None:
            res.append({"f": g.a + k, "d": 0, "sm": 0, "sh": 0}); prev = (s320, sm_); continue
        dd = np.abs(s320 - prev[0]); hh, ww = dd.shape
        cells = dd[:hh // CY * CY, :ww // CX * CX].reshape(CY, hh // CY, CX, ww // CX).mean(axis=(1, 3))
        sm = float(((cells > 0.8) & (cells < 12)).mean()); dm = float(dd.mean())
        if dm > 40:
            sh = -1.0
        else:
            fl = cv2.calcOpticalFlowFarneback(prev[1], sm_, None, 0.5, 3, 15, 3, 5, 1.2, 0); r = np.zeros((H, W), np.float32)
            for sl, X in Xs:
                for c in range(2):
                    y = fl[sl][..., c].ravel(); cf, *_ = np.linalg.lstsq(X, y, rcond=None)
                    r[sl] += ((y - X @ cf) ** 2).reshape(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start)
            sh = float(np.sqrt(r).mean())
        res.append({"f": g.a + k, "d": round(dm, 3), "sm": round(sm, 4), "sh": round(sh, 4)}); prev = (s320, sm_)
    return res


R = measure(g.src)
json.dump(R, open(g.out, "w")); print(len(R), "コマ", g.out)
avg = lambda L, k: float(np.mean([x[k] for x in L[1:] if x["sh"] >= 0])) if len(L) > 1 else 0.0
print(f"  {os.path.basename(g.src)}：d {avg(R, 'd'):.3f}  sm {avg(R, 'sm'):.4f}  sh {avg(R, 'sh'):.4f}  動いたコマ {sum(1 for x in R if x['d'] > 0.3)}/{len(R)}")
if g.vs:
    O = measure(g.vs); json.dump(O, open(g.out.replace(".json", "_vs.json"), "w"))
    print(f"  {os.path.basename(g.vs)}：d {avg(O, 'd'):.3f}  sm {avg(O, 'sm'):.4f}  sh {avg(O, 'sh'):.4f}  動いたコマ {sum(1 for x in O if x['d'] > 0.3)}/{len(O)}")
    print(f"  d の比（--vs ÷ 1本目）{avg(O, 'd') / max(avg(R, 'd'), 1e-6):.2f}  sm の比 {avg(O, 'sm') / max(avg(R, 'sm'), 1e-6):.2f}  sh の比 {avg(O, 'sh') / max(avg(R, 'sh'), 1e-6):.2f}")

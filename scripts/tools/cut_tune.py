"""切り替えの強さ（ffmpeg の scene 値）を手本に合わせる1コマの直し。mane-20261021/items/51/tools/cut_tune.py を r2 用に（大きさ・fps を問わず・全部のコマを自分で計算）。

python3 cut_tune.py <手本 mp4> <うち mp4> <出力 json> [--skip 0,1,2]
- scene 値＝Y の面の平均の差（mafd）・min(mafd, |mafd−前の mafd|)/100（51 の実測で ffmpeg とほぼ同じ）。mane_check は 0.3 を切り替え・±0.1秒で照合
- 足りん（手本 >0.3・うち ≤0.3）＝そのコマのコントラストを上げて 0.33 に（足りん時は明るさ）
- 余計（手本 ≤0.3・うち >0.3）＝そのコマに前のコマを a だけ重ねて min(手本−0.02, 0.27) に
- --skip：触らんコマ（黒いままのカットの中など）
🔴 51 の落とし穴：色・明るさを変えたら切り替えの強さも変わる＝順番は 色 → cut_tune。直したら書き出して測り直す
"""
import argparse, json, subprocess
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("ours"); ap.add_argument("out"); ap.add_argument("--th", type=float, default=0.3)
g = ap.parse_args()

def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
    w, h = map(int, o.split(",")[:2]); return w, h

def ys(p):
    w, h = probe(p)
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-i", p, "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w)

def scene(Y):
    m = np.array([0.0] + [np.abs(Y[i].astype(np.int16) - Y[i - 1]).mean() for i in range(1, len(Y))])
    s = np.zeros(len(Y))
    for i in range(1, len(Y)):
        s[i] = min(m[i], abs(m[i] - m[i - 1])) / 100
    return s, m

YR = ys(g.ref); YO = ys(g.ours); n = min(len(YR), len(YO))
SR, _ = scene(YR[:n]); SO, MO = scene(YO[:n])
cr = [i for i in range(n) if SR[i] > g.th]; co = [i for i in range(n) if SO[i] > g.th]
fps_tol = 3  # ±0.1秒
miss = [i for i in cr if not any(abs(i - j) <= fps_tol for j in co)]
extra = [j for j in co if not any(abs(i - j) <= fps_tol for i in cr)]
print("手本の切り替え", len(cr), "うち", len(co), "足りん", len(miss), "余計", len(extra))

def mafd(a, b):
    return np.abs(a.astype(np.float32) - b.astype(np.float32)).mean()
def sc(pp, p, x):
    m0, m1 = mafd(pp, p), mafd(p, x); return min(m1, abs(m1 - m0)) / 100

res = {}
for f in miss:
    pp, p, x = YO[f - 2], YO[f - 1], YO[f].astype(np.float32)
    con = bri = None
    for c in np.arange(1.0, 1.81, 0.02):
        if sc(pp, p, np.clip((x - 127.5) * c + 127.5, 0, 255)) >= g.th + 0.03:
            con = round(float(c), 2); break
    if con is None:
        for b in sorted(np.arange(0.6, 1.61, 0.02), key=lambda b: abs(b - 1)):
            if sc(pp, p, np.clip(x * b, 0, 255)) >= g.th + 0.03:
                bri = round(float(b), 2); break
    res[str(f)] = {"kind": "miss", "ref": round(float(SR[f]), 3), "now": round(float(SO[f]), 3), "con": con, "bri": bri}
for f in extra:
    pp, p, x = YO[f - 2], YO[f - 1].astype(np.float32), YO[f].astype(np.float32)
    tg = min(SR[f] - 0.02, g.th - 0.03); mix = None
    for a in np.arange(0.0, 0.71, 0.02):
        if sc(pp, p, x * (1 - a) + p * a) <= tg:
            mix = round(float(a), 2); break
    res[str(f)] = {"kind": "extra", "ref": round(float(SR[f]), 3), "now": round(float(SO[f]), 3), "mix": mix}
json.dump(res, open(g.out, "w"), indent=1)
ok_m = sum(1 for v in res.values() if v["kind"] == "miss" and (v["con"] or v["bri"]))
ok_e = sum(1 for v in res.values() if v["kind"] == "extra" and v["mix"] is not None)
print("直せる 足りん", ok_m, "/", len(miss), "余計", ok_e, "/", len(extra))
print("足りんのコマ", miss); print("余計のコマ", extra)

"""cap_sigma.py  字幕の語ごとに「縁のぼけ（σ）」が手本と同じかを測る（51 の edge_sigma.py の汎用版。51 は字だけの層の型で測った＝ここは caps.json の箱でうちの書き出しを測る）。
使い方：python3 cap_sigma.py <作業> <うち.mp4> [--out cap_sigma.json] [--min-gain 0.05]
入れる物：手本・うちの書き出し・proj/src/caps.json（語ごとの f0・f1・x・y・fs＝txt_build.py が書く）
語ごとに：出とる真ん中のコマで、語の箱（caps.json の box＋6px・無ければ green_fit と同じ形）を切り、うちの箱を σ 0〜4.2 でぼかして手本との差（平均二乗）が一番小さい σ を探す
出す物：1行ずつ「語 ずれ（px）一番近い σ 差 前→後（%）」・json {"<i>": {"w","sig","gain","dx","dy"}}（ずれが ±2px 以上の語は先に字の位置を直す）（既定 <作業>/shirabe/cap_sigma.json）・σ の中央値
  σ>0＝手本の方がぼけとる（手本の圧縮のにじみ）
効いた数字（51）：6語で SSIM +0.004〜0.045（字だけをぼかして上がる語だけ）。逆に明朝は「くっきり＋縁取り無し」が正しかった語もある（σ 0）
採る条件：gain（差の下がり）が --min-gain（既定 5%）以上の語だけ。全部の語の中央値が 0.4 以上なら look.json の blur（全部の字）を上げる方が先
🔴 Main.tsx の字に1語ずつのぼかしを読む所が要る（CAMERA_LOOK_README.md「字の縁」）
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, one, load_caps

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("--out"); ap.add_argument("--min-gain", type=float, default=0.05)
a = ap.parse_args()
ref = ref_path(a.w); W, H, _, _ = probe(ref); caps = load_caps(a.w)
SIG = [0, 0.4, 0.7, 1.0, 1.4, 1.8, 2.4, 3.2, 4.2]; res = {}; sig_all = []
for c in caps:
    f = (c["f0"] + c["f1"]) // 2
    if c.get("box"):  # 手本の字のインクの箱（txt_build が書く）があればそれ＋縁 6px
        x0, y0, x1, y1 = c["box"]; x0, y0, x1, y1 = max(0, x0 - 6), max(0, y0 - 6), min(W, x1 + 6), min(H, y1 + 6)
    else:
        x0 = max(0, int(c["x"] - 0.3 * c["fs"])); x1 = min(W, int(c["x"] + 0.62 * c["fs"] * len(c["w"]) + 0.3 * c["fs"]))
        y0 = max(0, int(c["y"] - 1.1 * c["fs"])); y1 = min(H, int(c["y"] + 0.45 * c["fs"]))
    if x1 - x0 < 8 or y1 - y0 < 8:
        continue
    R = one(ref, f); O = one(a.ours, f, size=(W, H))
    if R is None or O is None:
        continue
    Rc = R[y0:y1, x0:x1].astype(np.float32); Of = O.astype(np.float32)
    # 🔴 字の位置がずれとると、ぼかすだけで差が下がる（ぼけとるように見える）＝先に ±4px のずれを当ててから σ を測る
    def crop(dx, dy):
        return Of[max(0, y0 + dy):y0 + dy + (y1 - y0), max(0, x0 + dx):x0 + dx + (x1 - x0)]
    sh = [(float(((crop(dx, dy) - Rc) ** 2).mean()), dx, dy) for dx in range(-4, 5) for dy in range(-4, 5) if crop(dx, dy).shape == Rc.shape]
    _, dx, dy = min(sh); Oc = crop(dx, dy)
    e = [float((((cv2.GaussianBlur(Oc, (0, 0), s) if s else Oc) - Rc) ** 2).mean()) for s in SIG]
    i = int(np.argmin(e)); gain = 1 - e[i] / max(e[0], 1e-6)
    res[str(c["i"])] = {"w": c["w"], "f": f, "sig": SIG[i], "gain": round(gain, 3), "dx": dx, "dy": dy}; sig_all.append(SIG[i])
    print(f"{'🟢' if gain >= a.min_gain and SIG[i] > 0 else '  '} {c['i']:4d} {c['w'][:16]:16s} ずれ {dx:+d},{dy:+d}  σ {SIG[i]}  差 {e[0]:.0f}→{e[i]:.0f}（{100 * gain:.0f}%）", flush=True)
p = a.out or os.path.join(a.w, "shirabe", "cap_sigma.json")
os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True); json.dump(res, open(p, "w"), ensure_ascii=False)
if sig_all and float(np.median(sig_all)) >= SIG[-1]:
    print("🟡 σ の中央値が測る幅の上の端＝字の光（drop-shadow）か全部の字のぼかし（look.json blur）が手本より弱い。1語ずつより先にそっちを当て直す")
print("語", len(res), " σ の中央値", float(np.median(sig_all)) if sig_all else "-", " 差の下がりの中央値", f"{100 * float(np.median([v['gain'] for v in res.values()])):.0f}%" if res else "-", " 採る語（🟢）", sum(1 for v in res.values() if v["gain"] >= a.min_gain and v["sig"] > 0), " 書いた", p)

"""shot_look の各カットの色を「今／控え（shot_look.json.bak_colorfit）／無し」で当てた時の SSIM と ΔE を、書き出しから逆算で見込み、良い方を選ぶ。
python3 look_pred.py <作業> <書き出し.mp4> [--write]
- 色合わせ（color_fit）の後でカットの中身を替えると、古い色が残る（r2 の 141＝青0.22倍で黄色・119＝SSIM 0.64）。それを見つけて戻す
- 選ぶ条件：SSIM が今より 0.002 以上下がらず、ΔE が 0.3 以上下がる。--write で shot_look.json を書く（前は shot_look.json.bak_lookpred）
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
w = os.path.abspath(a.w); G = geo(w); SW, SH = G["SW"], G["SH"]; MW, MH = half(w)
def rgb(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={G['FPS_FF']},scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, SH, SW, 3).astype(np.float32) / 255
R = rgb(glob.glob(f"{w}/ref/*.mp4")[0]); V = rgb(os.path.join(w, a.out))
P = f"{w}/proj/src/shot_look.json"; cur = json.load(open(P))
bak = json.load(open(P + ".bak_colorfit")) if os.path.exists(P + ".bak_colorfit") else {}
lab = lambda x: cv2.cvtColor(np.uint8([[np.clip(x.reshape(-1, 3).mean(0) * 255, 0, 255)]]), cv2.COLOR_RGB2LAB)[0, 0].astype(float) * [100 / 255, 1, 1]
gray = lambda x: cv2.resize(cv2.cvtColor((np.clip(x, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY), (MW, MH))
ch = 0
for k, c in list(cur.items()):
    if "g" not in c: continue
    f0, f1 = c["f0"], min(c["f1"] + 1, len(V)); X = (V[f0:f1] - np.array(c["o"])) / np.array(c["g"]); res = {}
    for nm, lk in (("今", c), ("控え", bak.get(k, {})), ("無し", {})):
        Y = np.clip(np.array(lk.get("g", [1, 1, 1])) * X + np.array(lk.get("o", [0, 0, 0])), 0, 1)
        res[nm] = (float(np.mean([ssim(gray(R[f0 + i]), gray(Y[i])) for i in range(0, f1 - f0, 2)])), float(np.mean([np.linalg.norm(lab(R[f0 + i]) - lab(Y[i])) for i in range(f1 - f0)])))
    best = min(res, key=lambda n: res[n][1] if res[n][0] >= res["今"][0] - 0.002 else 99)
    if best != "今" and res["今"][1] - res[best][1] > 0.3:
        print(k, f0, f1, {n: (round(v[0], 3), round(v[1], 2)) for n, v in res.items()}, "→", best); ch += 1
        if a.write:
            keep = {x: c[x] for x in c if x not in ("g", "o")}
            if best == "控え": keep.update({"g": bak[k]["g"], "o": bak[k]["o"]})
            cur[k] = keep
print("戻すカット", ch)
if a.write and ch:
    shutil.copy(P, P + ".bak_lookpred"); json.dump(cur, open(P, "w"), indent=1)

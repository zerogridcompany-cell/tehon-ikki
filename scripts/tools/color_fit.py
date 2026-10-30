"""書き出した版と手本を比べて、カットごとに色のゲイン・オフセット（色ごとに1次）を求め、今の shot_look に重ねた新しい shot_look を作る。
書き出す前に、その色を当てた時の ΔE（mane_check と同じ＝1秒ごとの平均の色の Lab の差）と SSIM を手元で見込む。

python3 color_fit.py <作業フォルダ> <書き出した版.mp4> [--out proj/src/shot_look.json]
- 字幕の帯（300〜420 行）は外して合わせる。ゲインは 0.6〜1.6 に抑える
- SSIM がカットで 0.002 より下がる所は当てん
- 前の shot_look は shot_look.json.bak_colorfit に控え
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half

W, H, FPS = 320, 180, 29.97   # main で geo の SW・SH・FPS に替わる（10/30）
FPS_FF = "2997/100"


def rgb(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={FPS_FF},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).astype(np.float32) / 255


def lab(c):
    return cv2.cvtColor(np.clip(c, 0, 1).reshape(1, 1, 3).astype(np.float32), cv2.COLOR_RGB2Lab)[0, 0]


def de_secs(R, O):
    n = min(len(R), len(O)); out = []
    k = int(round(FPS))  # 1秒のコマ数（r2 は 30）
    for s in range(0, n, k):
        sl = slice(s, min(n, s + k))
        out.append(float(np.linalg.norm(lab(R[sl].reshape(-1, 3).mean(0)) - lab(O[sl].reshape(-1, 3).mean(0)))))
    return np.array(out)


def gray(x):
    return (x[..., 0] * 0.299 + x[..., 1] * 0.587 + x[..., 2] * 0.114) * 255


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("vid"); ap.add_argument("--out", default="proj/src/shot_look.json")
    g = ap.parse_args()
    global W, H, FPS, FPS_FF
    G = geo(g.w); W, H, FPS, FPS_FF = G["SW"], G["SH"], G["FPS"], G["FPS_FF"]
    R = rgb(glob.glob(f"{g.w}/ref/*.mp4")[0]); O = rgb(g.vid); n = min(len(R), len(O)); R, O = R[:n], O[:n]
    shots = sorted(json.load(open(f"{g.w}/eye/out.json"))["shots"], key=lambda s: float(s["t0"]))
    oldp = f"{g.w}/proj/src/shot_look.json"; old = json.load(open(oldp))
    band = np.ones((H, W), bool); band[int(300 * H / 720):int(420 * H / 720)] = False  # 字幕の帯（r2 の 300〜420 行）を高さの比で
    P = O.copy(); new = {}; used = 0
    for j, s in enumerate(shots):
        f0 = int(round(float(s["t0"]) * FPS)); f1 = int(round(float(shots[j + 1]["t0"]) * FPS)) if j + 1 < len(shots) else n
        if f1 <= f0:
            continue
        r = R[f0:f1][:, band]; o = O[f0:f1][:, band]
        gg, oo = [], []
        for c in range(3):
            x = o[..., c].ravel(); y = r[..., c].ravel()
            if x.std() < 0.01:
                a, b = 1.0, float(y.mean() - x.mean())
            else:
                a, b = np.polyfit(x, y, 1)
            a = float(np.clip(a, 0.6, 1.6)); b = float(np.clip(y.mean() - a * x.mean(), -0.5, 0.5))
            gg.append(a); oo.append(b)
        Q = np.clip(O[f0:f1] * np.array(gg) + np.array(oo), 0, 1)
        s0 = np.mean([ssim(gray(a), gray(b)) for a, b in zip(R[f0:f1], O[f0:f1])])
        s1 = np.mean([ssim(gray(a), gray(b)) for a, b in zip(R[f0:f1], Q)])
        if s1 < s0 - 0.002:
            continue
        P[f0:f1] = Q; used += 1
        # 今の look（このカットの頭のコマで効いとる物）に重ねる：g2(g1 x + o1) + o2
        lk = next((v for v in old.values() if v["f0"] <= f0 <= v["f1"]), {})
        g1 = lk.get("g") or [1, 1, 1]; o1 = lk.get("o") or [0, 0, 0]
        e = {"f0": f0, "f1": f1 - 1, "g": [round(gg[c] * g1[c], 4) for c in range(3)], "o": [round(gg[c] * o1[c] + oo[c], 4) for c in range(3)]}
        if lk.get("blur"):
            e["blur"] = lk["blur"]
        new[str(s["i"])] = e
    # 当てんかったカットは前の look をそのまま（範囲を切って残す）
    for j, s in enumerate(shots):
        if str(s["i"]) in new:
            continue
        f0 = int(round(float(s["t0"]) * FPS)); f1 = int(round(float(shots[j + 1]["t0"]) * FPS)) if j + 1 < len(shots) else n
        lk = next((v for v in old.values() if v["f0"] <= f0 <= v["f1"]), None)
        if lk:
            e = dict(lk); e["f0"] = f0; e["f1"] = f1 - 1; new[str(s["i"])] = e
    d0, d1 = de_secs(R, O).mean(), de_secs(R, P).mean()
    s0 = np.mean([ssim(gray(a), gray(b)) for a, b in zip(R[::3], O[::3])]); s1 = np.mean([ssim(gray(a), gray(b)) for a, b in zip(R[::3], P[::3])])
    print("当てたカット", used, "ΔE 見込み", round(d0, 2), "→", round(d1, 2), "SSIM(320幅)", round(s0, 4), "→", round(s1, 4))
    if not os.path.exists(oldp + ".bak_colorfit"):
        shutil.copy(oldp, oldp + ".bak_colorfit")
    json.dump(new, open(f"{g.w}/{g.out}", "w"), indent=1)


if __name__ == "__main__":
    main()

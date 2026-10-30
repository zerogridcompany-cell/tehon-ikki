"""fx_grade.py  fx の毎コマの色を、手本の同じコマの Lab の平均と幅へ寄せる。寄せる値は前後 ±R コマでならしてから当てる＝ちらつきを足さん（51 の fx_grade.py＋fx_grade_smooth.py の汎用版）。
使い方：python3 fx_grade.py <作業> <id> [<id> …] [--r 6] [--clip 0.75,1.33]
入れる物：proj/public/fx/<id>/<f>.jpg・手本・proj/src/caps.json（字幕の箱は測らん）・green.json（その絵が乗っとる所だけ測る）
出す物：fx/<id>/<f>.jpg に上書き。元は proj/public/fx_orig/<id>/ に1回目だけ残す（いつもそこから作る＝何度回しても同じ）
  手本のコマは ffmpeg のコマ番号で取る（🔴 51 は OpenCV の seek で取って 79秒が少し悪化した）
効いた数字（51・出る所ごとの色の束）：ΔE 2.5→1.7・17秒 6.3→2.3・24秒 11.6→2.6・41秒 11.6→1.7・87秒 11.0→1.6
採る条件：書き出して、そのコマの ΔE（mane_check の1秒ごと）が 0.5 以上下がって SSIM が 0.002 より下がらん時だけ。look_shot（カットごと）の後にかけると二重になる＝look_shot の前にかけて、look_shot は測り直す
"""
import argparse, glob, os, shutil, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, bgr, load_caps, cap_mask, footprint
import json

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ids", nargs="+"); ap.add_argument("--r", type=int, default=6); ap.add_argument("--clip", default="0.75,1.33")
a = ap.parse_args()
lo, hi = map(float, a.clip.split(","))
ref = ref_path(a.w); W, H, _, _ = probe(ref); caps = load_caps(a.w)
G = json.load(open(os.path.join(a.w, "proj", "src", "green.json")))
for pid in a.ids:
    D = os.path.join(a.w, "proj", "public", "fx", pid); O = os.path.join(a.w, "proj", "public", "fx_orig", pid)
    if not os.path.exists(O):
        os.makedirs(os.path.dirname(O), exist_ok=True); shutil.copytree(D, O)
    fs = sorted(int(os.path.basename(p)[:-4]) for p in glob.glob(f"{O}/*.jpg"))
    if not fs:
        continue
    R = bgr(ref, fs[0], fs[-1] - fs[0] + 1, W, H); p = G.get(pid); P = []
    for f in fs:
        im = cv2.imread(f"{O}/{f}.jpg"); r = R[f - fs[0]]
        mk = ~cap_mask(caps, f, W, H)
        if p and str(f) in p["M"]:
            mk &= footprint(p, p["M"][str(f)], W, H)
        if mk.sum() < 500:
            mk[:] = True
        A = cv2.cvtColor(im[mk].reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3)
        B = cv2.cvtColor(r[mk].reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3)
        P.append((A.mean(0), A.std(0) + 1e-3, B.mean(0), B.std(0)))
    dE = []
    for i, f in enumerate(fs):
        win = P[max(0, i - a.r): i + a.r + 1]; ma, sa = P[i][0], P[i][1]
        mb = np.mean([x[2] - x[0] for x in win], 0) + ma; rr = np.clip(np.mean([x[3] / x[1] for x in win], 0), lo, hi)
        L = cv2.cvtColor(cv2.imread(f"{O}/{f}.jpg"), cv2.COLOR_BGR2LAB).astype(np.float32)
        cv2.imwrite(f"{D}/{f}.jpg", cv2.cvtColor(np.clip((L - ma) * rr + mb, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        dE.append(float(np.linalg.norm(P[i][2] - P[i][0])))
    print(pid, len(fs), "コマ  平均の色の差（Lab 8bit）", round(float(np.mean(dE)), 2), "→ ならした値で寄せた")

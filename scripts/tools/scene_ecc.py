"""scene_ecc.py  カットごとに「うち→手本」の大きさとずれ（ECC の相似に近いアフィン）を 3コマごとに測る＝絵ごと決まってずれとるカットを探す（51 の scene_ecc.py の汎用版）。
使い方：python3 scene_ecc.py <作業> <うち.mp4> [--only 3,7,12] [--out scene_ecc.json]
入れる物：手本（<作業>/ref/*.mp4）・カットの表（<作業>/eye/out.json の shots の t0〜t1 秒）・うちの書き出し
出す物：1行ずつ「カット番号 kind コマ範囲 中央値（cc>0.6）：倍率・横・縦（画面の px）」と各コマの cc/倍率/ずれ。既定 <作業>/shirabe/scene_ecc.json
効いた数字（51 再開5回目）：全場面を洗って、絵ごと決まってずれとる場面を数字で拾えた（cc 0.8 以上・ずれ 4px 以上・倍率 1% 以上を候補に）
採る条件：cc が 0.8 以上なのに ずれ 4px 以上か倍率 1% 以上が、カットの中でそろって出る所だけ直す（その絵の M に逆をかける）。cc が低い所は中身が違う＝ずれの数字は当てにならん
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, gray

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("--only", default=""); ap.add_argument("--out")
a = ap.parse_args()
ref = ref_path(a.w); RW, RH, fps, _ = probe(ref); w = 480; h = int(round(w * RH / RW / 2)) * 2; K = RW / w
S = json.load(open(os.path.join(a.w, "eye", "out.json")))["shots"]
only = set(int(x) for x in a.only.split(",") if x)
out = {}
for s in S:
    i = s.get("i", S.index(s))
    if only and i not in only:
        continue
    f0, f1 = int(round(s["t0"] * fps)), int(round(s["t1"] * fps))
    if f1 - f0 < 6:
        continue
    R = gray(ref, f0, f1 - f0, w, h).astype(np.float32); O = gray(a.ours, f0, f1 - f0, w, h).astype(np.float32); rows = []
    for k in range(1, min(len(R), len(O)) - 1, 3):
        x = cv2.GaussianBlur(R[k], (0, 0), 1.5); y = cv2.GaussianBlur(O[k], (0, 0), 1.5)
        if x.std() < 2 or y.std() < 2:
            continue
        try:
            cc, M = cv2.findTransformECC(x, y, np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5), None, 5)
        except cv2.error:
            continue
        sc = np.sqrt(abs(np.linalg.det(M[:, :2]))); c = np.array([w / 2, h / 2]); d = M[:, :2] @ c + M[:, 2] - c
        rows.append((f0 + k, round(float(cc), 2), round(float(1 / sc), 4), round(float(-d[0] * K), 1), round(float(-d[1] * K), 1)))
    if not rows:
        continue
    good = [r for r in rows if r[1] > 0.6]
    med = np.median([[r[2], r[3], r[4]] for r in good], 0) if good else None
    out[str(i)] = {"kind": s.get("kind"), "f0": f0, "f1": f1, "rows": rows, "med": None if med is None else [round(float(v), 4) for v in med]}
    flag = med is not None and np.median([r[1] for r in good]) >= 0.8 and (abs(med[0] - 1) >= 0.01 or max(abs(med[1]), abs(med[2])) >= 4)
    print(f"{'🟡' if flag else '  '} {i} {s.get('kind')} {f0}-{f1}  中央値（cc>0.6）："
          + (f"倍率 {med[0]:.4f} 横 {med[1]:+.1f} 縦 {med[2]:+.1f}" if med is not None else "-")
          + "  " + " ".join(f"{r[0]}:{r[1]}/{r[2]}/{r[3]:+.0f},{r[4]:+.0f}" for r in rows[:6]), flush=True)
p = a.out or os.path.join(a.w, "shirabe", "scene_ecc.json")
os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True); json.dump(out, open(p, "w")); print("書いた", p, "🟡＝直せる候補")

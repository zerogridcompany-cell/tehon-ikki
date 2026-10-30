"""pad_mirror.py  カメラで絵の縁が画面に出る一枚絵を、鏡写しで四方に P px 広げた絵を作る（51 の pad_v3.py の汎用部分・ライオンの切り抜きは 51 専用で外した）。
使い方：python3 pad_mirror.py <作業> [<id> …] [--pad 520] [--auto]
入れる物：proj/public/green/<id>.png・proj/src/green.json（M）
出す物：proj/public/green/pad/<id>.png（BORDER_REFLECT_101・幅 w+2P）・green.json のその絵に "pad": P
  --auto＝id を指定せず「どれかのコマで絵の外（黒）が画面に 0.5% 以上出る絵」だけ選ぶ
🔴 Green.tsx 側に読む所が要る（CAMERA_LOOK_README.md「pad」）。足すまでは "pad" は無視される＝今の見た目は変わらん
効いた数字（51）：v3 から実写の絵は全部 pad で置いた＝カメラの振り（lives 1592px・stack 317px）でも縁が出ん。数字の上がりは縁が出とったコマだけ（黒い帯が消える）
採る条件：絵の外が画面に出るコマがある絵だけ（--auto）。出ん絵に付けても変わらん
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ids", nargs="*"); ap.add_argument("--pad", type=int, default=520); ap.add_argument("--auto", action="store_true")
a = ap.parse_args()
GJ = os.path.join(a.w, "proj", "src", "green.json"); G = json.load(open(GJ))
W, H, _, _ = probe(ref_path(a.w))
ids = a.ids or list(G)
od = os.path.join(a.w, "proj", "public", "green", "pad"); os.makedirs(od, exist_ok=True)
done = []
for pid in ids:
    p = G[pid]
    if a.auto:
        worst = 0.0
        for f, M in p["M"].items():
            m = cv2.warpAffine(np.full((p["h"], p["w"]), 255, np.uint8), np.array(M, np.float64).reshape(2, 3), (W, H), flags=cv2.INTER_NEAREST)
            worst = max(worst, float((m == 0).mean()))
        if worst < 0.005:
            continue
        print(pid, f"縁が出る割合 最大 {worst * 100:.1f}%")
    im = cv2.imread(os.path.join(a.w, "proj", "public", "green", f"{pid}.png"))
    if im is None:
        print("絵が無い", pid); continue
    cv2.imwrite(os.path.join(od, f"{pid}.png"), cv2.copyMakeBorder(im, a.pad, a.pad, a.pad, a.pad, cv2.BORDER_REFLECT_101))
    p["pad"] = a.pad; done.append(pid)
json.dump(G, open(GJ, "w"))
print("広げた", len(done), done)

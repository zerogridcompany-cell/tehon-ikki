"""cam_chain.py  手本のカメラの動き（拡大・回転・移動）を、基準のコマ k から LK の鎖で1コマずつ積んで測る（51 の cam.py・cam_one.py・cam_v2.py の汎用版）。
使い方：python3 cam_chain.py <作業> <f0> <f1> [--key k] [--plate <id> --write] [--out 鎖.json] [--mp4 別の動画]
入れる物：手本（<作業>/ref/*.mp4）・コマの範囲 f0〜f1（両端込み）・基準のコマ k（既定＝真ん中。--plate の時はその絵の ssim_each が一番高いコマ）
出す物：
  --out：{"f0","f1","k","C":{"<f>":[3x3 を9個]}}（画面の画素：k の画面 → f の画面）
  --plate <id> --write：proj/src/green.json のその絵の M を「M[f]＝C[f]·M[k]」で全部書き換える（Green.tsx がそのまま読む 2x3）。
     元の M は "M_ecc" に残す・"cam":"chain" を付ける。🔴 seq（動きの写しのコマ）は古い置き方で作った絵＝書いたら flow_tx をやり直す
測り方：手本を幅 480 の灰に縮め、goodFeaturesToTrack 400点→LK（21px・3段）→ estimateAffinePartial2D（RANSAC 1px）＝相似。点が 10 未満のコマは止める（単位行列）
効いた数字（51）：長い横流し lives 右→左 1592px・stack 上から 317px・baby 0.56→1.00倍 を構図を崩さず動かせた。止まったカメラの場面を1つ測り直して 42秒 ΔE 3.8→1.5・SSIM +0.03
採る条件：書き出して、その絵のコマの SSIM（seg_ssim.py）が ECC の置き方より上がった時だけ。ぶれ・引きで鎖が崩れる所（点が 10 未満が続く）は範囲を割るか止める
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, gray

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int)
ap.add_argument("--key", type=int); ap.add_argument("--plate"); ap.add_argument("--write", action="store_true"); ap.add_argument("--out"); ap.add_argument("--mp4")
a = ap.parse_args()
src = a.mp4 or ref_path(a.w); W, H, fps, _ = probe(src)
w = 480; h = int(round(w * H / W / 2)) * 2; K = W / w
G = None
if a.plate:
    GJ = os.path.join(a.w, "proj", "src", "green.json"); G = json.load(open(GJ)); p = G[a.plate]
    if a.key is None and p.get("ssim_each"):
        a.key = p["f0"] + int(np.argmax(p["ssim_each"]))
k = a.key if a.key is not None else (a.f0 + a.f1) // 2
k = min(max(k, a.f0), a.f1)
F = gray(src, a.f0, a.f1 - a.f0 + 1, w, h)
if len(F) < a.f1 - a.f0 + 1:
    raise SystemExit(f"コマが足りん：{len(F)}")
lost, cuts = [], []


def est(x, y, i):
    if float(np.abs(x.astype(np.int16) - y).mean()) > 40:  # カット（場面が替わった）＝鎖をつながん
        cuts.append(i); return np.eye(3)
    pt = cv2.goodFeaturesToTrack(x, 400, 0.01, 6)
    if pt is None or len(pt) < 10:
        lost.append(i); return np.eye(3)
    q, st, _ = cv2.calcOpticalFlowPyrLK(x, y, pt, None, winSize=(21, 21), maxLevel=3); st = st.ravel() == 1
    if st.sum() < 10:
        lost.append(i); return np.eye(3)
    A, _ = cv2.estimateAffinePartial2D(pt[st], q[st], method=cv2.RANSAC, ransacReprojThreshold=1.0)
    if A is None:
        lost.append(i); return np.eye(3)
    return np.vstack([A, [0, 0, 1]])


fr = lambda i: F[i - a.f0]
C = {k: np.eye(3)}
for i in range(k + 1, a.f1 + 1):
    C[i] = est(fr(i - 1), fr(i), i) @ C[i - 1]
for i in range(k - 1, a.f0 - 1, -1):
    C[i] = np.linalg.inv(est(fr(i), fr(i + 1), i)) @ C[i + 1]
Sc = np.diag([K, K, 1.0]); Si = np.diag([1 / K, 1 / K, 1.0])
C = {i: Sc @ C[i] @ Si for i in C}
sc = lambda m: float(np.sqrt(abs(np.linalg.det(m[:2, :2]))))
m0, m1 = C[a.f0], C[a.f1]
print(f"{a.f0}-{a.f1} k={k}  倍率 {sc(m0):.3f}→{sc(m1):.3f}  横 {m0[0, 2]:+.0f}→{m1[0, 2]:+.0f}  縦 {m0[1, 2]:+.0f}→{m1[1, 2]:+.0f} px  鎖が切れたコマ {len(lost)}{' ' + str(sorted(lost)[:12]) if lost else ''}")
if cuts:
    print(f"🔴 範囲の中にカット {sorted(cuts)}＝カットの中だけで測り直す（そこから先の数字は当てにならん）")
if a.out:
    json.dump({"f0": a.f0, "f1": a.f1, "k": k, "C": {str(i): [round(float(v), 5) for v in C[i].ravel()] for i in sorted(C)}}, open(a.out, "w"))
    print("書いた", a.out)
if a.plate and a.write:
    p = G[a.plate]
    if str(k) not in p["M"]:
        raise SystemExit(f"基準のコマ {k} の M が {a.plate} に無い（絵の範囲 {p['f0']}〜{p['f1']}）")
    Mk = np.vstack([np.array(p["M"][str(k)], np.float64).reshape(2, 3), [0, 0, 1]])
    p.setdefault("M_ecc", dict(p["M"]))
    for i in range(max(a.f0, p["f0"]), min(a.f1, p["f1"]) + 1):
        p["M"][str(i)] = [round(float(v), 5) for v in (C[i] @ Mk)[:2].ravel()]
    p["cam"] = "chain"
    if p.get("seq"):
        print(f"🔴 {a.plate} の seq {len(p['seq'])} コマは古い置き方の絵＝flow_tx.py --only {a.plate} をやり直す")
    json.dump(G, open(GJ, "w")); print("green.json に書いた", a.plate)

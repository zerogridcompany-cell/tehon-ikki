"""書き出しの絵どうし（うち→手本）をカットごとに ECC（相似＝拡大・回り・移動）で測り、最後の段で掛ける変形 tf を shot_look に書く（10/27 r2：写真の大きさ・位置が最後まで合わんかった）。
python3 final_fit.py <作業> <書き出し.mp4> --ids 1,2,98 [--write] [--th 0.008]
- 1カット 7コマ・480 幅の白黒・字幕の帯（y 300〜400/720＝手本の高さの比）を外す・ぼかし 1.5。cc 0.6 以上のコマの中央値
- tf＝[a,b,c,d,e,f]（CSS matrix・手本の画素（r2 は 1280x720）・原点は左上）＝うちの絵を手本の位置へ写す。前の tf があれば重ねる
- 拡大が |s−1|<th かつ移動 < 4px のカットは書かん
- Remotion（R2.tsx）は字幕の外の層（色・ぼかしの中）に transform: matrix(tf) を掛ける
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
W, H, w = 1280, 720, 480; k = W / w   # main で geo(<作業>) に替わる（10/30）


def fr(p, n):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-vf", f"select=eq(n\\,{n}),scale={w}:{int(H / k)},format=gray", "-vsync", "0", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(r, np.uint8).reshape(int(H / k), w)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--ids", required=True); ap.add_argument("--write", action="store_true"); ap.add_argument("--th", type=float, default=0.008)
    g = ap.parse_args()
    global W, H, k
    G = geo(g.w); W, H = G["W"], G["H"]; k = W / w; FPS = G["FPS"]
    ref = sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0]
    shots = {str(s["i"]): s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"]}
    lp = f"{g.w}/proj/src/shot_look.json"; L = json.load(open(lp)); res = {}
    hh = int(H / k); mask = np.ones((hh, w), np.uint8); mask[int(300 * H / 720 / k):int(400 * H / 720 / k), :] = 0
    for i in g.ids.split(","):
        s = shots[i]; f0, f1 = int(round(s["t0"] * FPS)), int(round(s["t1"] * FPS))
        ns = np.linspace(f0 + 1, f1 - 2, 7).astype(int) if f1 - f0 > 8 else range(f0, f1)
        Ms = []
        for n in sorted(set(ns)):
            a = cv2.GaussianBlur(fr(ref, n), (0, 0), 1.5).astype(np.float32); b = cv2.GaussianBlur(fr(g.out, n), (0, 0), 1.5).astype(np.float32)
            M = np.eye(2, 3, dtype=np.float32)
            try:
                cc, M = cv2.findTransformECC(a, b, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5), mask, 5)
            except cv2.error:
                continue
            if cc >= 0.6: Ms.append(M)
        if not Ms: print(i, "測れん"); continue
        M = np.median(np.array(Ms), axis=0)   # 手本の点 → うちの点
        A = np.vstack([M, [0, 0, 1]]); A[0, 2] *= k; A[1, 2] *= k
        T = np.linalg.inv(A)                   # うちの点 → 手本の点（うちの絵に掛ける）
        # 縦横同じ倍率＋回りだけ（相似）に直す＝写真を潰さん（affine のままだと 1 で横 0.84・縦 1.01 になった）
        U, Sg, Vt = np.linalg.svd(T[:2, :2]); Rm = U @ Vt; sm = float(np.sqrt(Sg[0] * Sg[1]))
        c = np.array([W / 2, H / 2]); cn = T[:2, :2] @ c + T[:2, 2]
        T[:2, :2] = Rm * sm; T[:2, 2] = cn - T[:2, :2] @ c
        sc = float(np.sqrt(abs(np.linalg.det(T[:2, :2])))); mv = float(np.hypot(T[0, 2] + (T[0, 0] - 1) * (W / 2) + T[0, 1] * (H / 2), T[1, 2] + T[1, 0] * (W / 2) + (T[1, 1] - 1) * (H / 2)))
        print(f"{i} コマ{len(Ms)} 拡大 {sc:.3f} 真ん中の移動 {mv:.1f}px")
        if abs(sc - 1) < g.th and mv < 4: continue
        res[i] = T
    if g.write:
        shutil.copy(lp, lp + ".bak_tf")
        for i, T in res.items():
            s = shots[i]; f0, f1 = int(round(s["t0"] * FPS)), int(round(s["t1"] * FPS))
            e = L.get(i) or {"f0": f0, "f1": f1 - 1}
            if "tf" in e:
                P = np.array([[e["tf"][0], e["tf"][2], e["tf"][4]], [e["tf"][1], e["tf"][3], e["tf"][5]], [0, 0, 1]]); T = T @ P
            e["tf"] = [round(float(T[0, 0]), 5), round(float(T[1, 0]), 5), round(float(T[0, 1]), 5), round(float(T[1, 1]), 5), round(float(T[0, 2]), 2), round(float(T[1, 2]), 2)]
            L[i] = e
        json.dump(L, open(lp, "w"), indent=1); print("書いた", lp, len(res))


if __name__ == "__main__":
    main()

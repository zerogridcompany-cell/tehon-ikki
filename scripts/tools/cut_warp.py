"""中身は合っとるのに位置・大きさ・回転がずれとるカットを、手本の1コマずつに ECC で重ね直す（テレビの合成・一枚絵・実写どれでも）。

python3 cut_warp.py <作業> --ids 33,42 [--model affine|homog] [--smooth 5] [--min 0.005] [--dry]
- うちのコマ（cuts/<番号>.mp4）→ 手本のコマに 480 幅の白黒で ECC（字幕の帯を外す）。失敗したコマは前後の値で埋める
- 値はコマの並びで平均して（--smooth コマ）揺れを消してから、元の大きさで曲げる。外に出た所は端の色を伸ばす
- カットの SSIM（白黒 640x360・cut_score と同じ）が --min 以上上がった時だけ書く。前の物は .bak_warp に控え
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half

W, H = 1280, 720   # main で geo(<作業>) に替わる（10/30）
FPS = 29.97
FPS_FF = "2997/100"


def read(p, ss, n):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, ss):.4f}", "-i", p, "-frames:v", str(n), "-vf", f"fps={FPS_FF},scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(o, np.uint8).reshape(-1, H, W, 3)


def g(x, w=480):
    return cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (w, w * H // W))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--ids", required=True); ap.add_argument("--model", default="affine"); ap.add_argument("--smooth", type=int, default=5)
    ap.add_argument("--min", type=float, default=0.005); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    global W, H, FPS, FPS_FF
    G = geo(a.w); W, H, FPS, FPS_FF = G["W"], G["H"], G["FPS"], G["FPS_FF"]
    ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
    shots = {str(s["i"]): s for s in json.load(open(f"{a.w}/eye/out.json"))["shots"]}
    MOT = cv2.MOTION_HOMOGRAPHY if a.model == "homog" else cv2.MOTION_AFFINE
    h480 = 480 * H // W; m480 = np.ones((h480, 480), np.uint8); m480[round(112 * h480 / 270):round(158 * h480 / 270)] = 0
    out = {}
    for i in a.ids.split(","):
        cp = f"{a.w}/cuts/{i}.mp4"
        if not os.path.exists(cp):
            print(i, "カット無し"); continue
        s = shots[i]; f0 = int(round(float(s["t0"]) * FPS)); n = int(round(float(s["t1"]) * FPS)) - f0
        R = read(ref, (f0 - 0.3) / FPS, n); O = read(cp, 0, n)
        n = min(len(R), len(O)); R, O = R[:n], O[:n]
        if n == 0:
            continue
        Ms = []
        prev = np.eye(3, dtype=np.float32)
        for k in range(n):
            rg = g(R[k]).astype(np.float32); og = g(O[k]).astype(np.float32)
            if rg.std() < 4 or og.std() < 4:
                Ms.append(None); continue
            try:
                init = prev if MOT == cv2.MOTION_HOMOGRAPHY else prev[:2]
                _, M = cv2.findTransformECC(rg, og, init.copy(), MOT, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5), m480, 3)
                M3 = M if M.shape[0] == 3 else np.vstack([M, [0, 0, 1]]).astype(np.float32)
                Ms.append(M3); prev = M3
            except cv2.error:
                Ms.append(None)
        ok = [k for k in range(n) if Ms[k] is not None]
        if not ok:
            print(i, "ECC 全部失敗"); continue
        for k in range(n):
            if Ms[k] is None:
                Ms[k] = Ms[min(ok, key=lambda j: abs(j - k))]
        A = np.stack(Ms)
        h = a.smooth // 2
        As = np.stack([A[max(0, k - h):k + h + 1].mean(0) for k in range(n)])
        S = np.diag([480 / W, 480 / W, 1.0]); Si = np.linalg.inv(S)
        before = np.mean([ssim(g(O[k], 640), g(R[k], 640)) for k in range(n)])
        NW = []
        for k in range(n):
            # ECC の M は 手本の点 x → うちの点 M x ＝ 手本の大きさでは Si M S
            Mf = (Si @ As[k] @ S).astype(np.float32)
            NW.append(cv2.warpPerspective(O[k], Mf, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE))
        after = np.mean([ssim(g(NW[k], 640), g(R[k], 640)) for k in range(n)])
        sc = float(np.mean([np.linalg.norm(As[k][:2, :2] - np.eye(2)) for k in range(n)]))
        tr = float(np.mean([np.linalg.norm(As[k][:2, 2]) for k in range(n)]))
        ok_ = after > before + a.min
        out[i] = {"before": round(float(before), 4), "after": round(float(after), 4), "scale_dev": round(sc, 3), "shift480": round(tr, 1), "adopt": bool(ok_)}
        print(i, "コマ", n, round(before, 4), "→", round(after, 4), "ずれ(拡大)", round(sc, 3), "ずれ(移動480)", round(tr, 1), "採用" if ok_ else "見送り", flush=True)
        if ok_ and not a.dry:
            if not os.path.exists(cp + ".bak_warp"):
                shutil.copy(cp, cp + ".bak_warp")
            tmp = cp + ".tmp.mp4"
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-",
                                  "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
            p.stdin.write(np.stack(NW).tobytes()); p.stdin.close(); p.wait()
            shutil.move(tmp, cp)
    json.dump(out, open(f"{a.w}/tmp/cut_warp_{a.ids.replace(',', '_')[:40]}.json", "w"), indent=1)


if __name__ == "__main__":
    main()

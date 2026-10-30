"""1つのカットの中に何枚もの写真が並ぶ所（縦長の窓が3つ等）を、コマごとに写真ごとに重ねて作る。
python3 multi_photo.py <作業フォルダ> <カット番号> <写真…> [--out cuts/<番号>.mp4]
- コマごと・写真ごと：SIFT→拡大・移動・回転（RANSAC）→ECC で詰める→覆う所だけ色を1次で合わせる
- その写真の所で、手本との近さが今のカットより上がる時だけ置く（前のカットの残りが映るコマは触らん）
- 前の物は cuts/<番号>.mp4.bak_multi に控え
"""
import argparse, json, os, shutil, subprocess
import cv2
import numpy as np

W, H, FPS = 1280, 720, 29.97
sift = cv2.SIFT_create(4000); bf = cv2.BFMatcher()


def readv(p, ss=None, n=None):
    c = ["ffmpeg", "-v", "error"] + (["-ss", f"{ss:.4f}"] if ss is not None else []) + ["-i", p] + (["-frames:v", str(n)] if n else [])
    r = subprocess.run(c + ["-vf", f"fps=2997/100,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def ssim_m(a, b, m):
    a = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float32); b = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float32)
    C1, C2 = 6.5, 58.5
    mu1 = cv2.GaussianBlur(a, (7, 7), 1.5); mu2 = cv2.GaussianBlur(b, (7, 7), 1.5)
    s1 = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu1 ** 2; s2 = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu1 * mu2
    s = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))
    return float(s[m].mean()) if m.any() else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("photos", nargs="+"); ap.add_argument("--out"); ap.add_argument("--hold", action="store_true", help="写真が置けんかったコマは、その写真を置けた一番近いコマの置き方で埋める（窓が出たり消えたりして余計な切り替えになるのを防ぐ）")
    g = ap.parse_args()
    shots = sorted(json.load(open(f"{g.w}/eye/out.json"))["shots"], key=lambda s: float(s["t0"]))
    j = [k for k, s in enumerate(shots) if str(s["i"]) == g.i][0]
    f0 = int(round(float(shots[j]["t0"]) * FPS)); f1 = int(round(float(shots[j + 1]["t0"]) * FPS)); n = f1 - f0
    ref = [f for f in os.listdir(f"{g.w}/ref") if f.endswith(".mp4")][0]
    R = readv(f"{g.w}/ref/{ref}", max(0, f0 - 0.3) / FPS, n)
    cp = f"{g.w}/cuts/{g.i}.mp4"
    O = readv(cp)[:n] if os.path.exists(cp) else np.zeros((n, H, W, 3), np.uint8)
    if len(O) < n:
        O = np.concatenate([O, np.zeros((n - len(O), H, W, 3), np.uint8)])
    P = []
    for p in g.photos:
        im = cv2.imread(p); s = 900 / max(im.shape[:2]); sm = cv2.resize(im, None, fx=s, fy=s) if s < 1 else im; s = min(s, 1.0)
        k, d = sift.detectAndCompute(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), None)
        P.append((p, im, s, k, d))
    txt = np.ones((H, W), bool); txt[300:420] = False
    got = {p[0]: {} for p in P}  # 写真 → {コマ: (絵, 覆う所)}
    for t in range(n):
        r = R[t]; rg = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)
        kr, dr = sift.detectAndCompute(rg, None)
        if dr is None:
            continue
        for p, im, s, k, d in P:
            mm = [a for a, b in (q for q in bf.knnMatch(d, dr, k=2) if len(q) == 2) if a.distance < 0.75 * b.distance]
            if len(mm) < 15:
                continue
            A, inl = cv2.estimateAffinePartial2D(np.float32([k[m.queryIdx].pt for m in mm]) / s, np.float32([kr[m.trainIdx].pt for m in mm]),
                                                 method=cv2.RANSAC, ransacReprojThreshold=4.0)
            if A is None or int(inl.sum()) < 15:
                continue
            wc = cv2.warpAffine(im, A, (W, H), flags=cv2.INTER_LANCZOS4)
            cv = cv2.warpAffine(np.full(im.shape[:2], 255, np.uint8), A, (W, H)) > 250
            cv = cv2.erode(cv.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            m = cv & txt
            if m.sum() < 2000:
                continue
            fit = wc.astype(np.float32)
            for c in range(3):
                a, b = np.polyfit(wc[..., c][m].astype(np.float32), r[..., c][m].astype(np.float32), 1)
                fit[..., c] = wc[..., c] * a + b
            fit = np.clip(fit, 0, 255).astype(np.uint8)
            bl = max((0, 1, 2), key=lambda x: ssim_m(cv2.GaussianBlur(fit, (0, 0), x) if x else fit, r, m))
            fb = cv2.GaussianBlur(fit, (0, 0), bl) if bl else fit
            new, old = ssim_m(fb, r, m), ssim_m(O[t], r, m)
            if new > old + 0.01:
                O[t][cv] = fb[cv]; got[p][t] = (fb, cv)
                print("コマ", f0 + t, os.path.basename(p), "目印", int(inl.sum()), round(old, 3), "→", round(new, 3), flush=True)
    if g.hold:
        for p, d in got.items():
            if not d:
                continue
            ks = sorted(d)
            for t in range(n):
                if t not in d:
                    k = min(ks, key=lambda x: abs(x - t)); fb, cv = d[k]
                    m = cv & txt
                    if t > ks[0] or ssim_m(fb, R[t], m) > ssim_m(O[t], R[t], m):  # 前に延ばすのは手本に近づく時だけ
                        O[t][cv] = fb[cv]; print("つなぎ", f0 + t, os.path.basename(p), "←", f0 + k, flush=True)
    out = g.out or cp
    if out == cp and os.path.exists(cp) and not os.path.exists(cp + ".bak_multi"):
        shutil.copy(cp, cp + ".bak_multi")
    tmp = out + ".tmp.mp4"
    pr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-",
                           "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    pr.stdin.write(O.tobytes()); pr.stdin.close(); pr.wait(); shutil.move(tmp, out)
    print("書いた", out)


if __name__ == "__main__":
    main()

"""長い動画の決まった秒の窓から、手本の1コマずつに一番合う元のコマを探して、カットの該当コマだけ差し替える（連続写真・1〜3コマの実写向け）。

python3 vid_patch.py <作業> <カット番号> <元の動画> <窓の始め秒> <窓の終わり秒> --frames 953-954 [--flip] [--min 0.01]
- 元の窓を 480 幅の白黒で全部読む → 手本のコマ（字幕の帯を外す）と SIFT → 目印の多い上位 4 コマ → ECC（拡大・移動・回転）で詰める
- 選んだコマだけ元の大きさで読み直して重ね、色はチャンネルごとの1次で手本に合わせ、ぼかし 0〜2 の良い方
- 今のコマより SSIM（白黒・手本の半分＝r2 は 640x360）が --min 以上上がった時だけ入れる。前の物は .bak_vp に控え
"""
import argparse, json, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half

W, H = 1280, 720   # main で geo(<作業>) に替わる（10/30）
FPS = 29.97
FPS_FF, MW, MH, RH = "2997/100", 640, 360, 270   # RH＝手本を 480 幅にした時の高さ


def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip().split(",")
    return int(o[0]), int(o[1])


def read(p, ss, d, w, h, fmt="gray", fps=None):
    fps = fps or FPS_FF
    ch = 1 if fmt == "gray" else 3
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.4f}", "-t", f"{d:.4f}", "-i", p, "-vf", f"fps={fps},scale={w}:{h}",
                        "-f", "rawvideo", "-pix_fmt", "gray" if ch == 1 else "bgr24", "-"], capture_output=True).stdout
    a = np.frombuffer(o, np.uint8)
    return a.reshape(-1, h, w) if ch == 1 else a.reshape(-1, h, w, 3)


def ssim_m(a, b, m):
    a = a.astype(np.float32); b = b.astype(np.float32)
    C1, C2 = 6.5, 58.5
    mu1 = cv2.GaussianBlur(a, (7, 7), 1.5); mu2 = cv2.GaussianBlur(b, (7, 7), 1.5)
    s1 = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu1 ** 2; s2 = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu1 * mu2
    s = ((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))
    return float(s[m].mean()) if m.any() else 0.0


def g640(x):
    return cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("src"); ap.add_argument("a", type=float); ap.add_argument("b", type=float)
    ap.add_argument("--frames", required=True); ap.add_argument("--flip", action="store_true"); ap.add_argument("--min", type=float, default=0.01)
    ap.add_argument("--offset", type=float, default=None, help="元の秒＝手本の秒＋offset で決め打ち（目印が取れん噴煙・暗い絵）。前後1コマと重ね方なし（ECC だけ）も候補に")
    g = ap.parse_args()
    global W, H, FPS, FPS_FF, MW, MH, RH
    G = geo(g.w); W, H, FPS, FPS_FF = G["W"], G["H"], G["FPS"], G["FPS_FF"]; MW, MH = half(g.w); RH = round(480 * H / W)
    import glob
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    shot = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == g.i][0]
    c0 = int(round(float(shot["t0"]) * FPS)); n = int(round(float(shot["t1"]) * FPS)) - c0
    cp = f"{g.w}/cuts/{g.i}.mp4"
    cur = read(cp, 0, 99, W, H, "bgr")[:n] if os.path.exists(cp) else np.zeros((n, H, W, 3), np.uint8)
    if len(cur) < n:
        cur = np.concatenate([cur, np.zeros((n - len(cur), H, W, 3), np.uint8)])
    cur = cur.copy()
    sw, sh = probe(g.src)
    h480 = int(round(sh * 480 / sw / 2) * 2)
    S = read(g.src, g.a, g.b - g.a, 480, h480)
    if g.flip:
        S = S[:, :, ::-1].copy()
    sift = cv2.SIFT_create(1500); bf = cv2.BFMatcher()
    fs = [sift.detectAndCompute(x, None) for x in S]
    print("元のコマ", len(S), flush=True)
    f0, f1 = map(int, g.frames.split("-"))
    txt = np.ones((RH, 480), np.uint8); txt[round(112 * RH / 270):round(158 * RH / 270)] = 0  # 字幕の帯（300〜420/720＝高さの比）
    changed = False
    for f in range(f0, f1 + 1):
        R = read(ref, max(0, f - 0.3) / FPS, 1 / FPS, W, H, "bgr")[0]
        rg = cv2.resize(cv2.cvtColor(R, cv2.COLOR_BGR2GRAY), (480, RH))
        kr, dr = sift.detectAndCompute(rg, txt)
        cand = []
        for j, (kc, dc) in enumerate(fs):
            if dr is None or dc is None or len(kc) < 8:
                continue
            m = [x for x, y in (q for q in bf.knnMatch(dc, dr, k=2) if len(q) == 2) if x.distance < 0.75 * y.distance]
            if len(m) < 8:
                continue
            A, inl = cv2.estimateAffinePartial2D(np.float32([kc[x.queryIdx].pt for x in m]), np.float32([kr[x.trainIdx].pt for x in m]), method=cv2.RANSAC, ransacReprojThreshold=4.0)
            if A is not None and inl.sum() >= 8:
                cand.append((int(inl.sum()), j, A))
        cand.sort(key=lambda x: -x[0])
        if g.offset is not None:
            jc = int(round((f / FPS + g.offset - g.a) * FPS))
            I = np.float32([[1, 0, 0], [0, RH / h480, 0]]) if abs(RH / h480 - 1) > 0.01 else np.float32([[1, 0, 0], [0, 1, 0]])
            cand = [(0, j, I.copy()) for j in (jc - 1, jc, jc + 1) if 0 <= j < len(S)] + cand[:2]
        # 背景だけで目印が当たると顔の向きが違うコマを選ぶ＝一番の A で全コマを重ねて SSIM の上位も足す
        if cand and g.offset is None:
            A0 = cand[0][2]; mk = cv2.warpAffine(np.ones_like(S[0]), A0, (480, RH)) > 0
            mk &= txt > 0
            sc = []
            for j in range(len(S)):
                sc.append((ssim_m(cv2.warpAffine(S[j], A0, (480, RH)), rg, mk), j))
            sc.sort(reverse=True)
            seen = {c[1] for c in cand[:4]}
            cand = cand[:4] + [(0, j, A0.copy()) for _, j in sc[:6] if j not in seen]
        best = (-1, None, None)
        for inl, j, A in cand:
            try:
                _, D = cv2.findTransformECC(rg.astype(np.float32), cv2.warpAffine(S[j], A, (480, RH)).astype(np.float32), np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE,
                                            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5), None, 3)
                A = (np.linalg.inv(np.vstack([D, [0, 0, 1]])) @ np.vstack([A, [0, 0, 1]]))[:2]
            except cv2.error:
                pass
            # 元の大きさで読み直す（480 幅の A → 元 → 手本の大きさ）
            full = read(g.src, g.a + j / FPS, 1 / FPS, sw, sh, "bgr")[0]
            if g.flip:
                full = full[:, ::-1].copy()
            Af = (np.diag([W / 480, W / 480, 1.0]) @ np.vstack([A, [0, 0, 1]]) @ np.diag([480 / sw, 480 / sw, 1.0]))[:2].astype(np.float32)
            wc = cv2.warpAffine(full, Af, (W, H)); cv = cv2.warpAffine(np.ones((sh, sw), np.uint8), Af, (W, H)) > 0
            m = cv.copy(); m[round(300 * H / 720):round(420 * H / 720)] = False
            fit = wc.astype(np.float32)
            if m.sum() > 1000:
                for c in range(3):
                    x = wc[..., c][m].astype(np.float32)
                    if x.std() < 1:
                        continue
                    try:
                        k, b = np.polyfit(x, R[..., c][m].astype(np.float32), 1)
                    except (np.linalg.LinAlgError, ValueError):
                        continue
                    fit[..., c] = wc[..., c] * k + b
            fit = np.clip(fit, 0, 255).astype(np.uint8)
            for bl in (0, 1, 2):
                o = cur[f - c0].copy()
                fb = cv2.GaussianBlur(fit, (0, 0), bl) if bl else fit
                o[cv] = fb[cv]
                sc = ssim(g640(o), g640(R))
                # 🔴 平らな面（灰色一色）は手本の白飛びに点で勝ってしまう＝模様が手本の 3 割未満なら外す（10/27 r2 13）
                if g640(o).std() < 0.3 * g640(R).std():
                    continue
                if sc > best[0]:
                    best = (sc, o, (inl, round(g.a + j / FPS, 3), bl))
        now = ssim(g640(cur[f - c0]), g640(R))
        if best[1] is not None and best[0] > now + g.min:
            cur[f - c0] = best[1]; changed = True
            print(f, "入れた", round(now, 3), "→", round(best[0], 3), "目印・元の秒・ぼかし", best[2], flush=True)
        else:
            print(f, "そのまま", round(now, 3), "候補", round(best[0], 3) if best[1] is not None else "なし", best[2], flush=True)
    if changed:
        if os.path.exists(cp) and not os.path.exists(cp + ".bak_vp"):
            shutil.copy(cp, cp + ".bak_vp")
        tmp = cp + ".tmp.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-",
                              "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        p.stdin.write(cur.tobytes()); p.stdin.close(); p.wait()
        shutil.move(tmp, cp)
        print("書いた", cp, flush=True)


if __name__ == "__main__":
    main()

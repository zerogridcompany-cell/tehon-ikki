"""写真の枠（地の上に置いた四角い写真）を、手本の枠の四隅に合わせる（10/27 r2：98・99・70・71・69＝写真の大きさが合わん）。
python3 box_fit.py <作業> <カット番号> [--out tmp/box/<番号>.mp4] [--write] [--diff 28]
- 地の色＝コマの外周の中央値。地と diff 以上違う所の一番大きい形（小さい取っ手は開いて消す）→ minAreaRect の四隅
- 手本とうち、それぞれコマの中央値の四隅 → うち→手本の射影で全コマを曲げる（外は地の色）
- 取っ手（手本の四隅の小さい白い四角）はこの道具では足さん
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
W, H = 1280, 720   # main で geo(<作業>) に替わる（10/30）


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def quad(f, d):
    edge = np.concatenate([f[:8].reshape(-1, 3), f[-8:].reshape(-1, 3), f[:, :8].reshape(-1, 3), f[:, -8:].reshape(-1, 3)])
    bg = np.median(edge, 0)
    m = (np.abs(f.astype(np.float32) - bg).max(2) > d).astype(np.uint8) * 255
    m[round(300 * H / 720):round(400 * H / 720)] = cv2.dilate(m, np.ones((1, 1), np.uint8))[round(300 * H / 720):round(400 * H / 720)]
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((25, 25), np.uint8)); m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs: return None, bg
    c = max(cs, key=cv2.contourArea)
    if cv2.contourArea(c) < 0.02 * W * H or cv2.contourArea(c) > 0.9 * W * H: return None, bg
    p = cv2.boxPoints(cv2.minAreaRect(c)); s = p.sum(1); dd = np.diff(p, axis=1)[:, 0]
    return np.array([p[np.argmin(s)], p[np.argmin(dd)], p[np.argmax(s)], p[np.argmax(dd)]], np.float32), bg


def quad_edge(f, d=None):
    """縁の段差で枠を取る：列（行）ごとの横（縦）の明るさの変化の強さ→真ん中より左右（上下）で一番強い所＝光のにじみ（なだらか）に引っぱられん"""
    gy = cv2.GaussianBlur(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
    gx = np.abs(cv2.Sobel(gy, cv2.CV_32F, 1, 0, ksize=3)); gyy = np.abs(cv2.Sobel(gy, cv2.CV_32F, 0, 1, ksize=3))
    gx[round(300 * H / 720):round(400 * H / 720)] = 0; gyy[:, :] = gyy; cx = gx.mean(0); cy = gyy.mean(1)
    cx = np.convolve(cx, np.ones(3) / 3, "same"); cy = np.convolve(cy, np.ones(3) / 3, "same")
    x0 = int(np.argmax(cx[8:W // 2 - 40])) + 8; x1 = int(np.argmax(cx[W // 2 + 40:W - 8])) + W // 2 + 40
    y0 = int(np.argmax(cy[4:H // 2 - 40])) + 4; y1 = int(np.argmax(cy[H // 2 + 40:H - 4])) + H // 2 + 40
    q = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)
    edge = np.concatenate([f[:8].reshape(-1, 3), f[-8:].reshape(-1, 3), f[:, :8].reshape(-1, 3), f[:, -8:].reshape(-1, 3)])
    return q, np.median(edge, 0)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--out"); ap.add_argument("--write", action="store_true"); ap.add_argument("--diff", type=float, default=28); ap.add_argument("--edge", action="store_true", help="縁の段差で取る（光のにじみがある時）")
    g = ap.parse_args()
    global W, H
    G = geo(g.w); W, H = G["W"], G["H"]
    s = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == str(g.i)][0]
    f0 = int(round(s["t0"] * G["FPS"])); src = f"{g.w}/cuts/{g.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0], f0, f0 + len(F)); n = min(len(F), len(R))
    qf = (lambda f: quad_edge(f)[0]) if g.edge else (lambda f: quad(f, g.diff)[0])
    QR = [q for q in (qf(R[j]) for j in range(n)) if q is not None]
    QO = [q for q in (qf(F[j]) for j in range(n)) if q is not None]
    if len(QR) < 2 or len(QO) < 2: print(g.i, "枠が取れん", len(QR), len(QO)); return
    qr, qo = np.median(QR, 0), np.median(QO, 0)
    wr = np.linalg.norm(qr[1] - qr[0]); wo = np.linalg.norm(qo[1] - qo[0])
    print(f"{g.i} 手本の枠 {qr.round(0).tolist()} 幅 {wr:.0f}／うち {qo.round(0).tolist()} 幅 {wo:.0f} → 倍率 {wr / wo:.3f}")
    Hm = cv2.getPerspectiveTransform(qo, qr)
    out = []
    for f in F:
        bg = quad(f, g.diff)[1]
        out.append(cv2.warpPerspective(f, Hm, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=tuple(float(x) for x in bg)))
    o = g.out or f"{g.w}/tmp/box/{g.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", G["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o)
    if g.write:
        if not os.path.exists(src + ".bak_box"): shutil.copy(src, src + ".bak_box")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()

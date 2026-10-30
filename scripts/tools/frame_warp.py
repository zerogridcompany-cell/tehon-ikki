"""カットの1コマずつを手本のそのコマに ECC（相似→アフィンの2段・縮めた絵から）で重ね、そのコマの SSIM が上がった時だけ入れる（10/28 r2 110：cut_warp のカット一括だと外れた）。
python3 frame_warp.py <作業> <カット番号> [--frames a-b] [--min 0.003] [--write]
- 字幕の帯（y 300〜400）は外して合わせる。外に出た所は端を伸ばす
- 前の物は .bak_fw
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ssim_fast
from geo import geo, half
W, H = 1280, 720   # main で geo(<作業>) に替わる（10/30）


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def g(im, w=640):
    return cv2.GaussianBlur(cv2.cvtColor(cv2.resize(im, (w, w * H // W)), cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--frames"); ap.add_argument("--min", type=float, default=0.003); ap.add_argument("--write", action="store_true"); ap.add_argument("--smooth", type=int, default=0, help="0＝コマごとに良い時だけ／N＝全コマの変形を N コマでならして全部にかける（ガタつかん）")
    a = ap.parse_args()
    global W, H
    G = geo(a.w); W, H = G["W"], G["H"]; MW, MH = half(a.w)
    s = [s for s in json.load(open(f"{a.w}/eye/out.json"))["shots"] if str(s["i"]) == str(a.i)][0]
    f0 = int(round(s["t0"] * G["FPS"])); src = f"{a.w}/cuts/{a.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{a.w}/ref/*.mp4"))[0], f0, f0 + len(F)); n = min(len(F), len(R))
    lo, hi = (map(int, a.frames.split("-")) if a.frames else (f0, f0 + n))
    h640 = 640 * H // W; mk = np.ones((h640, 640), np.uint8); mk[round(150 * h640 / 360):round(200 * h640 / 360)] = 0  # g() と同じ大きさ・字幕の帯は比で
    out = list(F); gain = 0; used = 0; prev = None; Ms = {}
    for j in range(n):
        if not (lo <= f0 + j <= hi): continue
        r, o = g(R[j]), g(F[j]); best = None
        for model, init in ((cv2.MOTION_EUCLIDEAN, prev), (cv2.MOTION_AFFINE, None)):
            M = np.eye(2, 3, dtype=np.float32) if init is None else init.copy()
            try:
                for lvl in (4, 2, 1):   # 縮めた絵から
                    rs, os_ = cv2.resize(r, None, fx=1 / lvl, fy=1 / lvl), cv2.resize(o, None, fx=1 / lvl, fy=1 / lvl)
                    ms = cv2.resize(mk, (rs.shape[1], rs.shape[0]), interpolation=cv2.INTER_NEAREST)
                    Ml = M.copy(); Ml[:, 2] /= lvl
                    _, Ml = cv2.findTransformECC(rs, os_, Ml, model, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 120, 1e-5), ms, 3)
                    M = Ml.copy(); M[:, 2] *= lvl
            except cv2.error:
                continue
            A = M.copy(); A[:, 2] *= W / 640
            wp = cv2.warpAffine(F[j], A, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
            sc = ssim_fast(cv2.cvtColor(cv2.resize(R[j], (MW, MH)), cv2.COLOR_BGR2GRAY), cv2.cvtColor(cv2.resize(wp, (MW, MH)), cv2.COLOR_BGR2GRAY))
            if best is None or sc > best[0]: best = (sc, wp, M)
        s0 = ssim_fast(cv2.cvtColor(cv2.resize(R[j], (MW, MH)), cv2.COLOR_BGR2GRAY), cv2.cvtColor(cv2.resize(F[j], (MW, MH)), cv2.COLOR_BGR2GRAY))
        if a.smooth:
            Ms[j] = best[2] if best else None
        elif best and best[0] > s0 + a.min:
            out[j] = best[1]; gain += best[0] - s0; used += 1; prev = best[2]
    if a.smooth:
        js = sorted(k for k, v in Ms.items() if v is not None)
        if js:
            P = np.array([Ms[k].ravel() for k in js]); allj = sorted(Ms)
            Q = np.array([[np.interp(j, js, P[:, c]) for c in range(6)] for j in allj])
            k = a.smooth; Qs = np.array([Q[max(0, i - k // 2):i + k // 2 + 1].mean(0) for i in range(len(Q))])
            for i, j in enumerate(allj):
                A = Qs[i].reshape(2, 3).astype(np.float32).copy(); A[:, 2] *= W / 640
                out[j] = cv2.warpAffine(F[j], A, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE); used += 1
    print(f"{a.i} 入れたコマ {used}/{n} 上がり合計 {gain:.2f}（コマ分）")
    o = f"{a.w}/tmp/fw/{a.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", G["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o)
    if a.write:
        if not os.path.exists(src + ".bak_fw"): shutil.copy(src, src + ".bak_fw")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()

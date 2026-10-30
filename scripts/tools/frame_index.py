"""手元の動画を1秒に2コマ読み、画面全体の構図（小さい白黒）と色を索引にする。顔が取れん横顔などの代わり探し用。
python3 frame_index.py <動画…> --out tmp/frame_index.npz [--fps 2]
query: python3 frame_index.py --query <作業> <手本のコマ> --index tmp/frame_index.npz [--top 11]
"""
import argparse, glob, subprocess, sys
import cv2, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("vids", nargs="*"); ap.add_argument("--out"); ap.add_argument("--fps", type=float, default=2)
ap.add_argument("--query", nargs=2); ap.add_argument("--index", default="tmp/frame_index.npz"); ap.add_argument("--top", type=int, default=11); ap.add_argument("--flip", action="store_true")
a = ap.parse_args()
def dsc(im):
    g = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(im, (48, 27)), cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 0.8)
    g = (g - g.mean()) / (g.std() + 1e-6); return g.ravel(), cv2.resize(im, (4, 3)).astype(np.float32).ravel() / 255
if a.query:
    w, f = a.query[0], int(a.query[1]); Z = np.load(f"{w}/{a.index}", allow_pickle=True); meta, G, Cc = Z["meta"], Z["g"], Z["c"]
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", glob.glob(f"{w}/ref/*.mp4")[0], "-vf", f"fps=2997/100,select=eq(n\\,{f}),scale=640:360", "-vsync", "0", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    im = np.frombuffer(r.stdout, np.uint8).reshape(360, 640, 3); g, c = dsc(im)
    sc = G @ g / g.size - 0.8 * np.abs(Cc - c).mean(1); fl = None
    if a.flip:
        gf, _ = dsc(im[:, ::-1]); scf = G @ gf / g.size - 0.8 * np.abs(Cc - c).mean(1); fl = scf > sc; sc = np.maximum(sc, scf)
    idx = np.argsort(-sc)[: a.top]; cells = [cv2.resize(im, (320, 180))]
    for i in idx:
        v, t = meta[i]
        rr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", v, "-frames:v", "1", "-vf", "scale=320:180", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        cc = np.frombuffer(rr, np.uint8).reshape(180, 320, 3).copy() if len(rr) == 320 * 180 * 3 else np.zeros((180, 320, 3), np.uint8)
        if fl is not None and fl[i]: cc = cc[:, ::-1].copy()
        cv2.putText(cc, f"{len(cells)} {v.split('/')[-1][:12]} {t:.1f}s {sc[i]:.2f}{' F' if fl is not None and fl[i] else ''}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1); cells.append(cc)
        print(len(cells) - 1, v, round(float(t), 1), round(float(sc[i]), 3), "反転" if fl is not None and fl[i] else "")
    while len(cells) % 4: cells.append(np.zeros_like(cells[0]))
    cv2.imwrite(f"{w}/tmp/fi_{f}.jpg", np.vstack([np.hstack(cells[i:i + 4]) for i in range(0, len(cells), 4)])); sys.exit()
M, G, Cc = [], [], []
for v in a.vids:
    r = subprocess.Popen(["ffmpeg", "-v", "error", "-i", v, "-vf", f"fps={a.fps},scale=192:108", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE); i = 0
    while True:
        b = r.stdout.read(192 * 108 * 3)
        if len(b) < 192 * 108 * 3: break
        g, c = dsc(np.frombuffer(b, np.uint8).reshape(108, 192, 3)); M.append((v, i / a.fps)); G.append(g); Cc.append(c); i += 1
    print(v, i, flush=True)
np.savez(a.out, meta=np.array(M, dtype=object), g=np.array(G, np.float32), c=np.array(Cc, np.float32))

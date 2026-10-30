"""色だけ（Lab の a・b）をコマごとに手本の平均と散らばりへ寄せる（明るさ L は触らん）。10/28 r2 67：顔が橙で濃い→色だけなら点は −0.001 で色かぶりが消える。
python3 chroma_cut.py <作業> <書き出し_noaudio.mp4> [--ids 67,121] [--write]
- 上に字やロゴの層を重ねたカット（書き出しとカットのファイルの差 12 以上）は飛ばす
- 入れる条件＝点（look 込み SSIM）の下がり 0.003 以内・色の差（a・b の平均の差）が 2割以上減る。前の物は .bak_chroma
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
FPS = 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--ids"); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
ids = a.ids.split(",") if a.ids else None
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360), interpolation=cv2.INTER_AREA)
for l in open(f"{w}/eye/segs.txt"):
    c, t = l.strip().split(":")
    if ids and c not in ids: continue
    s0, s1 = map(float, t.split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS); n = f1 - f0; cp = f"{w}/cuts/{c}.mp4"
    if n < 3 or not os.path.exists(cp): continue
    C = rd(cp)[:n]; R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); V = rd(os.path.join(w, a.out), sel=(f0, f1 - 1)); LK = looks(w, f0, n); n = min(n, len(C), len(R), len(V))
    H, W = R.shape[1:3]; m = np.ones((H, W), bool); m[int(H * .416):int(H * .583)] = False
    if np.median([np.abs(post_f(C[j], LK[j]).astype(float) - V[j].astype(float))[m].mean() for j in range(0, n, max(1, n // 4))]) >= 12: continue
    out = []; eb = []; ea = []
    for j in range(n):
        xl = cv2.cvtColor(C[j], cv2.COLOR_BGR2LAB).astype(np.float32); rl = cv2.cvtColor(R[j], cv2.COLOR_BGR2LAB).astype(np.float32)
        pl = cv2.cvtColor(post_f(C[j], LK[j]), cv2.COLOR_BGR2LAB).astype(np.float32)
        eb.append(sum(abs(pl[..., ch][m].mean() - rl[..., ch][m].mean()) for ch in (1, 2)))
        for ch in (1, 2):
            k = np.clip(rl[..., ch][m].std() / max(pl[..., ch][m].std(), 1e-3), 0.5, 2.0)
            xl[..., ch] = (xl[..., ch] - xl[..., ch][m].mean()) * k + xl[..., ch][m].mean() + (rl[..., ch][m].mean() - pl[..., ch][m].mean())
        y = cv2.cvtColor(np.clip(xl, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR); out.append(y)
        yl = cv2.cvtColor(post_f(y, LK[j]), cv2.COLOR_BGR2LAB).astype(np.float32); ea.append(sum(abs(yl[..., ch][m].mean() - rl[..., ch][m].mean()) for ch in (1, 2)))
    sb = np.mean([ssim(g(R[j]), g(post_f(C[j], LK[j]))) for j in range(0, n, 2)]); sa = np.mean([ssim(g(R[j]), g(post_f(out[j], LK[j]))) for j in range(0, n, 2)])
    ok = sa >= sb - 0.003 and np.mean(ea) <= 0.8 * np.mean(eb)
    print(f"{c} 点 {sb:.4f}→{sa:.4f} 色の差 {np.mean(eb):.2f}→{np.mean(ea):.2f} {'入れる' if ok else ''}", flush=True)
    if a.write and ok:
        if not os.path.exists(cp + ".bak_chroma"): shutil.copy(cp, cp + ".bak_chroma")
        full = rd(cp).copy(); full[:n] = np.stack(out)
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
        p.stdin.write(full.tobytes()); p.stdin.close(); p.wait()

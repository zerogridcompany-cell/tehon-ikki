"""黒地の中の窓（明るい長方形）に、見つけた元の動画を窓の箱だけ合わせて差し込む（84 の Falcon 1 など・vid_patch が窓が細くて外れる時用）。

python3 window_vid.py <作業> --cut 84 --f0 1154 --f1 1173 --src <元.mp4> --t0 4.0 --crop x,y,w,h [--halo 1] [--dry]
- 窓の箱＝手本の各コマで明るい所（白黒 >40）の一番大きい塊の外枠
- 元の切り出し（--crop・元の画素）→ 窓の箱へ拡大 → 手本の窓の中と ECC（拡大・移動）で詰める → 色を窓の中で色ごとに1次で合わせる
- --thr＝窓の明るさのしきい（光ごと拾う時は上げる）・--erase＝元に焼き付いた字を消す箱
- 窓の外の光（手本の窓の周りの白い光）も手本から測って足す（--halo）
- カット（cuts/<番号>.mp4）の該当コマだけ差し替え。カットの SSIM が上がった時だけ書く。前の物は .bak_wv に控え
"""
import glob
import argparse, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half

W, H, FPS = 1280, 720, 29.97   # main で geo(<作業>) に替わる（10/30）
FPS_FF, MW, MH = "2997/100", 640, 360


def read(p, ss=None, n=None, fps=None):
    fps = fps or FPS_FF
    img = p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    cmd = ["ffmpeg", "-v", "error"] + (["-loop", "1", "-t", "2"] if img else (["-ss", f"{ss:.4f}"] if ss is not None else [])) + ["-i", p] + (["-frames:v", str(n)] if n else [])
    cmd += ["-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.uint8).reshape(-1, H, W, 3).copy()


def box(img, thr=40):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = (g > thr).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = st[i, :4]
    return int(x), int(y), int(w), int(h)


def g640(a):
    return cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (MW, MH))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--cut", required=True)
    ap.add_argument("--f0", type=int, required=True); ap.add_argument("--f1", type=int, required=True)
    ap.add_argument("--src", required=True); ap.add_argument("--t0", type=float, required=True); ap.add_argument("--crop", required=True)
    ap.add_argument("--halo", type=float, default=1.0); ap.add_argument("--thr", type=int, default=40)
    ap.add_argument("--erase", default="", help="元の字を消す箱 x,y,w,h;…（元の画素・白い字だけ塗り直す）"); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    w = os.path.abspath(a.w)
    global W, H, FPS, FPS_FF, MW, MH
    GG = geo(w); W, H, FPS, FPS_FF = GG["W"], GG["H"], GG["FPS"], GG["FPS_FF"]; MW, MH = half(w)
    seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
    c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS)
    cutp = f"{w}/cuts/{a.cut}.mp4"
    C = read(cutp)
    n = a.f1 - a.f0
    R = read(glob.glob(f"{w}/ref/*.mp4")[0])[a.f0:a.f1]
    S = read(a.src, a.t0, n + 4, fps=FPS_FF)
    cx, cy, cw, ch = map(int, a.crop.split(","))
    for e in filter(None, a.erase.split(";")):
        ex, ey, ew, eh = map(int, e.split(","))
        # 焼き付いた字＝全コマで動かん明るい所（＋縁の影）だけ
        G = np.stack([cv2.cvtColor(S[q][ey:ey + eh, ex:ex + ew], cv2.COLOR_BGR2GRAY) for q in range(len(S))]).astype(np.int16)
        m = ((G.min(0) > 150) & (G.max(0) - G.min(0) < 45)).astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((9, 9), np.uint8))
        for q in range(len(S)):
            sub = S[q][ey:ey + eh, ex:ex + ew]
            S[q][ey:ey + eh, ex:ex + ew] = cv2.inpaint(sub, m, 9, cv2.INPAINT_TELEA)
    out = C.copy(); before = []; after = []
    for i in range(n):
        f = a.f0 + i; j = f - c0
        if j < 0 or j >= len(C):
            continue
        r = R[i]; bx, by, bw, bh = box(r, a.thr)
        sx, sy = bw / cw, bh / ch
        M = np.float32([[sx, 0, bx - cx * sx], [0, sy, by - cy * sy]])
        # 窓の中で ECC（拡大・移動）
        mask = np.zeros((H, W), np.uint8); mask[by + 4:by + bh - 4, bx + 4:bx + bw - 4] = 255
        tg = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).astype(np.float32)
        src = S[min(i, len(S) - 1)]
        try:
            M3 = np.vstack([M, [0, 0, 1]]).astype(np.float32)
            warp0 = cv2.warpAffine(cv2.cvtColor(src, cv2.COLOR_BGR2GRAY), M, (W, H)).astype(np.float32)
            wm = np.eye(2, 3, dtype=np.float32)
            cv2.findTransformECC(tg, warp0, wm, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5), mask, 5)
            Mf = (np.vstack([wm, [0, 0, 1]]) @ M3)  # 目標→warp0 の逆は ECC が「目標座標→warp0座標」
            Mf = np.linalg.inv(np.vstack([cv2.invertAffineTransform(wm), [0, 0, 1]])) if False else Mf
            # ECC の wm は 目標の点 p を warp0 の点 wm·p に写す＝warp0 を目標へ置くには wm で WARP_INVERSE_MAP
            pl = cv2.warpAffine(cv2.warpAffine(src, M, (W, H)), wm, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        except cv2.error:
            pl = cv2.warpAffine(src, M, (W, H))
        # 色を窓の中で合わせる
        inn = mask > 0
        pf = pl.astype(np.float32); rf = r.astype(np.float32)
        for k in range(3):
            ps, rs = pf[..., k][inn], rf[..., k][inn]
            g = rs.std() / (ps.std() + 1e-6); g = min(1.6, max(0.6, g))
            pf[..., k] = (pf[..., k] - ps.mean()) * g + rs.mean()
        base = C[j].astype(np.float32)
        # 窓の外の光：手本の窓の周り（窓から 40px）を手本どおりに
        if a.halo > 0:
            # 窓の光は作る（窓の形をぼかした白・強さとぼけは手本の周りの明るさに最小二乗で当てる。手本の画素は写さん）
            ring = np.zeros((H, W), np.uint8); cv2.rectangle(ring, (bx - 60, by - 60), (bx + bw + 60, by + bh + 60), 255, -1)
            ring[by:by + bh, bx:bx + bw] = 0
            rr = ring > 0
            best = None
            for sg in (6, 10, 16, 24, 36):
                gm = cv2.GaussianBlur(win0 := np.pad(np.ones((bh, bw), np.float32), ((by, H - by - bh), (bx, W - bx - bw))), (0, 0), sg)
                for c in range(3):
                    pass
                x = gm[rr]; y = rf[rr].mean(1) - base[rr].mean(1)
                k = float((x * y).sum() / ((x * x).sum() + 1e-6)); err = float(((y - k * x) ** 2).mean())
                if best is None or err < best[0]: best = (err, sg, k, gm)
            _, sg, k, gm = best
            col = np.array([rf[rr][:, c].mean() - base[rr][:, c].mean() for c in range(3)]); col = col / (col.mean() + 1e-6)
            base = base + (a.halo * max(k, 0) * gm)[..., None] * col[None, None, :]
        win = np.zeros((H, W), np.uint8); win[by:by + bh, bx:bx + bw] = 255
        base[win > 0] = pf[win > 0]
        out[j] = np.clip(base, 0, 255).astype(np.uint8)
        before.append(ssim(g640(r), g640(C[j]))); after.append(ssim(g640(r), g640(out[j])))
    print(f"{a.cut} {a.f0}-{a.f1}: コマ平均 {np.mean(before):.4f} → {np.mean(after):.4f}")
    cv2.imwrite(f"{w}/tmp/wv_{a.cut}.jpg", np.hstack([cv2.resize(R[n // 2], (MW, MH)), cv2.resize(out[a.f0 + n // 2 - c0], (MW, MH))]))
    if a.dry or np.mean(after) <= np.mean(before) + 0.005:
        print("書かん（dry か 上がらん）"); return
    shutil.copy(cutp, cutp + ".bak_wv")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-",
                          "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cutp], stdin=subprocess.PIPE)
    p.stdin.write(out.tobytes()); p.stdin.close(); p.wait()
    print("書いた", cutp)


if __name__ == "__main__":
    main()

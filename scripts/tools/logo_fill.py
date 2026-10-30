"""元の動画に焼き付いたロゴ・名札・別の字幕を、周りの色をなめらかに広げて消す（10/27 r2：126 の「or 2026,」・60 Minutes Overtime・名札）。
python3 logo_fill.py <作業> <カット番号> --box x0,y0,x1,y1 [--mode box|diff|white] [--out tmp/logo/<番号>.mp4] [--write]
- 形の見つけ方：box＝箱ごと（動かんロゴ・名札はこれ）／diff＝手本と比べて、うちだけにある形（コマ平均の差＋そのコマの差）／white＝彩度が低く明るい細い字（肌の上の白い字）
- 埋め方：マスクの外の画素を σ6/12/24 のガウスで正規化して広げる（cv2.inpaint の硬い線が出ん）→ 周りと同じ粒を足す → 縁を σ4 でなじませる
- --write＝cuts/<番号>.mp4 を置き換える（前の物は .bak_logo）。点（SSIM）は下がっても 0.01 以内なら見た目を優先してよい（手本に無い物は残さん）
効いた数字（r2）：126 0.713→0.705（字は消えた）
"""
import argparse, os, shutil, subprocess, sys
import cv2, numpy as np
W, H = 1280, 720


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


g_noise = 0.5


def fill(f, m, j):
    ff = f.astype(np.float32)
    # 1/8 に縮めて埋める→なめらかに戻す（大きい箱でも真ん中まで届き、cv2.inpaint の硬い線も出ん）
    k = 8; sw, sh = W // k, H // k
    fs = cv2.resize(f, (sw, sh), interpolation=cv2.INTER_AREA); ms = (cv2.resize(m, (sw, sh), interpolation=cv2.INTER_AREA) > 20).astype(np.uint8) * 255
    ms = cv2.dilate(ms, np.ones((3, 3), np.uint8))
    ip = cv2.resize(cv2.inpaint(fs, ms, 6, cv2.INPAINT_TELEA), (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    ip = cv2.GaussianBlur(ip, (0, 0), 3)
    ring = cv2.dilate(m, np.ones((25, 25), np.uint8)) & ~m
    hp = ff - cv2.GaussianBlur(ff, (0, 0), 2)
    sd = hp[ring > 0].std(axis=0) if (ring > 0).any() else np.zeros(3)
    nz = cv2.GaussianBlur(np.random.default_rng(j).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.8)
    ip = ip + (nz / (nz.std() + 1e-6))[..., None] * sd[None, None, :] * g_noise
    a = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 4)[..., None]
    return np.clip(ff * (1 - a) + ip * a, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--box", required=True)
    ap.add_argument("--mode", default="diff"); ap.add_argument("--th", type=float, default=18); ap.add_argument("--out"); ap.add_argument("--write", action="store_true")
    ap.add_argument("--track", action="store_true", help="box の中の形を真ん中のコマから取り、コマごとに拡大0.8〜1.25で追って箱を動かす（拡大のかかったカットのロゴ）")
    ap.add_argument("--margin", type=int, default=12)
    g = ap.parse_args(); x0, y0, x1, y1 = map(int, g.box.split(","))
    import json, glob
    s = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == str(g.i)][0]
    f0 = int(round(s["t0"] * 29.97)); src = f"{g.w}/cuts/{g.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0], f0, f0 + len(F))
    n = min(len(F), len(R))
    if g.mode == "box" and g.track:
        tpl = cv2.cvtColor(F[len(F) // 2][y0:y1, x0:x1], cv2.COLOR_BGR2GRAY); masks = []
        sx0, sy0, sx1, sy1 = max(0, x0 - 160), max(0, y0 - 120), min(W, x1 + 160), min(H, y1 + 120)
        for f in F:
            gy = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)[sy0:sy1, sx0:sx1]; best = None
            for sc in np.linspace(0.8, 1.25, 10):
                t = cv2.resize(tpl, None, fx=sc, fy=sc)
                if t.shape[0] >= gy.shape[0] or t.shape[1] >= gy.shape[1]: continue
                _, mv, _, ml = cv2.minMaxLoc(cv2.matchTemplate(gy, t, cv2.TM_CCOEFF_NORMED))
                if best is None or mv > best[0]: best = (mv, ml, t.shape)
            mv, (x, y), (th_, tw) = best; x += sx0; y += sy0; mg = g.margin
            m = np.zeros((H, W), np.uint8); m[max(0, y - mg):min(H, y + th_ + mg), max(0, x - mg):min(W, x + tw + mg)] = 255; masks.append(m)
    elif g.mode == "box":
        base = np.zeros((H, W), np.uint8); base[y0:y1, x0:x1] = 255; masks = [base] * len(F)
    elif g.mode == "diff":
        # うちだけにある形：コマ平均の差（ロゴは動かん）を主に、ぼかした差で地の色のずれを消す
        D = np.abs(F[:n].astype(np.float32) - R[:n].astype(np.float32)).mean(axis=(0, 3))
        D = D - cv2.GaussianBlur(D, (0, 0), 15)
        base = np.zeros((H, W), np.uint8); sub = D[y0:y1, x0:x1] > g.th; base[y0:y1, x0:x1][sub] = 255
        base = cv2.morphologyEx(base, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)); base = cv2.dilate(base, np.ones((13, 13), np.uint8))
        masks = [base] * len(F)
    else:
        masks = []
        for f in F:
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV); gy = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            th = cv2.morphologyEx(gy, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
            m = np.zeros((H, W), np.uint8); sub = (hsv[y0:y1, x0:x1, 1] < 62) & (hsv[y0:y1, x0:x1, 2] > 140) & (th[y0:y1, x0:x1] > 8); m[y0:y1, x0:x1][sub] = 255
            pts = cv2.findNonZero(m)
            if pts is not None: cv2.fillConvexPoly(m, cv2.convexHull(pts), 255)
            masks.append(cv2.dilate(m, np.ones((17, 17), np.uint8)))
    out = [fill(f, masks[j], j) if masks[j].any() else f for j, f in enumerate(F)]
    o = g.out or f"{g.w}/tmp/logo/{g.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait()
    cv2.imwrite(o.replace(".mp4", "_mask.png"), masks[len(masks) // 2])
    print("書いた", o, "マスクの画素", int((masks[len(masks) // 2] > 0).sum()))
    if g.write:
        if not os.path.exists(src + ".bak_logo"): shutil.copy(src, src + ".bak_logo")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()

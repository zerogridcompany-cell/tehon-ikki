"""作り手の加工のうち「色収差（輪郭の赤青ずれ）」と「暗い縁（周辺減光）」を、手本のカットごとに測ってかける（10/28 r2：説明に色収差・暗い縁とあるカットが24・仕組みに無かった）。
python3 ca_vig.py <作業> <カット番号> [--write] [--min 0.002]
- 色収差＝赤・青を画面の真ん中から拡大縮小した物として、倍率 kr・kb を手本で測る（縁の強い所の赤と緑・青と緑の差が一番小さい倍率）
- 暗い縁＝手本÷うちの明るさを、真ん中からの距離 r の式 a+b·r²+c·r⁴ に当てる（字幕の帯は外す・0.4〜1.2 に収める）
- うちに 暗い縁→色収差 の順でかけ、カットの SSIM が --min 以上上がった時だけ書く（前の物は .bak_cav）
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ssim_fast
from geo import geo, half
W, H = 1280, 720   # main で geo(<作業>) に替わる（10/30）
FPS_FF = "2997/100"
MW, MH = 640, 360


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def scale_ch(ch, k):
    M = np.array([[1 + k, 0, -k * W / 2], [0, 1 + k, -k * H / 2]], np.float32)
    return cv2.warpAffine(ch, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ca_measure(frames):
    ks = np.linspace(-0.012, 0.012, 25); best = {}
    for c in (2, 0):  # 赤・青
        errs = []
        for k in ks:
            e = 0
            for f in frames:
                g = f[..., 1].astype(np.float32); x = scale_ch(f[..., c].astype(np.float32), -k)
                gm = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1)); gm[round(300 * H / 720):round(400 * H / 720)] = 0  # 字幕の帯（r2 の行を高さの比で）
                w = gm > np.percentile(gm, 90)
                d = (x - g); d = d - d[w].mean()
                e += float(np.abs(d[w]).mean())
            errs.append(e)
        best[c] = float(ks[int(np.argmin(errs))])
    return best[2], best[0]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--write", action="store_true"); ap.add_argument("--min", type=float, default=0.002)
    a = ap.parse_args()
    global W, H, FPS_FF, MW, MH
    G = geo(a.w); W, H, FPS_FF = G["W"], G["H"], G["FPS_FF"]; MW, MH = half(a.w)
    s = [s for s in json.load(open(f"{a.w}/eye/out.json"))["shots"] if str(s["i"]) == str(a.i)][0]
    f0 = int(round(s["t0"] * G["FPS"])); src = f"{a.w}/cuts/{a.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{a.w}/ref/*.mp4"))[0], f0, f0 + len(F)); n = min(len(F), len(R))
    pick = sorted(set(np.linspace(0, n - 1, min(4, n)).astype(int)))
    kr, kb = ca_measure([R[j] for j in pick]); kr0, kb0 = ca_measure([F[j] for j in pick])
    dr, db = kr - kr0, kb - kb0
    yy, xx = np.mgrid[0:H, 0:W]; rr = (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    m = np.ones((H, W), bool); m[round(300 * H / 720):round(400 * H / 720)] = False
    lr = np.mean([cv2.cvtColor(R[j], cv2.COLOR_BGR2GRAY) for j in pick], 0).astype(np.float32) + 1
    lo = np.mean([cv2.cvtColor(F[j], cv2.COLOR_BGR2GRAY) for j in pick], 0).astype(np.float32) + 1
    lr = cv2.GaussianBlur(lr, (0, 0), 25); lo = cv2.GaussianBlur(lo, (0, 0), 25)
    ok = m & (lo > 12) & (lr > 6)
    ratio = (lr / lo)[ok]; X = np.stack([np.ones(ok.sum()), rr[ok], rr[ok] ** 2], 1)
    cf = np.linalg.lstsq(X, ratio, rcond=None)[0]; gmap = np.clip(cf[0] + cf[1] * rr + cf[2] * rr ** 2, 0.4, 1.2)
    gmap = gmap / max(1e-6, np.median(gmap[H // 2 - 60:H // 2 + 60, W // 2 - 100:W // 2 + 100]))  # 真ん中は触らん（明るさは look がやる）
    gmap = np.clip(gmap, 0.4, 1.05).astype(np.float32)
    def fx(f, v=True, c=True):
        o = f.astype(np.float32)
        if v: o = o * gmap[..., None]
        if c: o[..., 2] = scale_ch(o[..., 2], dr); o[..., 0] = scale_ch(o[..., 0], db)
        return np.clip(o, 0, 255).astype(np.uint8)
    gs = lambda x: cv2.cvtColor(cv2.resize(x, (MW, MH)), cv2.COLOR_BGR2GRAY)
    def score(fn):
        return float(np.mean([ssim_fast(gs(R[j]), gs(fn(F[j]))) for j in range(n)]))
    s0 = score(lambda f: f); sv = score(lambda f: fx(f, True, False)); sc = score(lambda f: fx(f, False, True)); sb = score(lambda f: fx(f, True, True))
    opts = {"なし": (s0, None), "暗い縁": (sv, (True, False)), "色収差": (sc, (False, True)), "両方": (sb, (True, True))}
    name, (sbest, how) = max(opts.items(), key=lambda kv: kv[1][0])
    print(f"{a.i} 色収差 赤{dr:+.4f} 青{db:+.4f}・縁の式 {cf.round(3)}・SSIM なし {s0:.4f} 縁 {sv:.4f} 収差 {sc:.4f} 両方 {sb:.4f} → {name}")
    if how is None or sbest < s0 + a.min: return
    out = [fx(f, *how) for f in F]
    o = f"{a.w}/tmp/cav/{a.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o)
    if a.write:
        if not os.path.exists(src + ".bak_cav"): shutil.copy(src, src + ".bak_cav")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()

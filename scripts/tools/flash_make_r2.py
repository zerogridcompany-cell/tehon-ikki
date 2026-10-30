# 白く光るコマを、うちの絵（字幕を外して書き出した物）を反転・色合わせして作る。手本とは SSIM で比べて元のコマを選ぶだけ（手本の絵は入れん）
import os, sys, json, subprocess, numpy as np, cv2
sys.path.insert(0, '../tools'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half
W, H = geo(".")["W"], geo(".")["H"]; MW, MH = half(".")  # 作業フォルダ（r2）で回す前提（10/30 geo）
def rd(p):
    r = subprocess.run(["ffmpeg","-v","error","-i",p,"-vf",f"scale={W}:{H}","-vsync","0","-f","rawvideo","-pix_fmt","bgr24","-"],capture_output=True)
    return np.frombuffer(r.stdout,np.uint8).reshape(-1,H,W,3)
R = rd('ref/r2.mp4')
B = {}
for a, b in ((528, 545), (1726, 1736), (1782, 1790)):
    for i, im in enumerate(rd(f'tmp/nocap_{a}-{b}.mp4')): B[a + i] = im
g = lambda a: cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (MW, MH))
def colfit(img, ref):
    o = img.astype(np.float32).copy()
    for c in range(3):
        a, b = o[..., c].ravel(), ref[..., c].astype(np.float32).ravel()
        A = np.vstack([a, np.ones_like(a)]).T; gk, ok_ = np.linalg.lstsq(A, b, rcond=None)[0]
        o[..., c] = o[..., c] * gk + ok_
    return np.clip(o, 0, 255).astype(np.uint8)
def make(f, ks, inv, keep=None):
    out = []
    for k in ks:
        img = (255 - B[k]) if inv else B[k].copy()
        if keep:
            x0, x1 = keep; img = img.copy(); img[:, :x0] = 255 if inv else img[:, :x0]; img[:, x1:] = 255 if inv else img[:, x1:]
        img = colfit(img, R[f]); out.append((ssim(g(R[f]), g(img)), k, img))
    out.sort(key=lambda t: -t[0]); return out[0]
white = np.full((H, W, 3), 245, np.uint8)
ok = []
for f, ks, inv, keep in ((528, range(529, 545), True, (760, 1280)), (532, range(529, 545), True, None),
                         (1727, range(1728, 1736), True, None), (1782, range(1785, 1787), False, None), (1788, range(1785, 1787), False, None)):
    s, k, img = make(f, ks, inv, keep)
    sw = ssim(g(R[f]), g(colfit(white, R[f])))
    cv2.imwrite(f'proj/public/flash/{f}.png', img); ok.append({"f": f, "src": f"flash/{f}.png"})
    print(f, '元', k, 'SSIM', round(float(s), 3), '（白一色なら', round(float(sw), 3), '）')
json.dump(ok, open('proj/src/flash.json', 'w'), indent=1)

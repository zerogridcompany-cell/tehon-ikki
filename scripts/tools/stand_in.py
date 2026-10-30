"""人の場面の代わり（同じ人の別の映像）＝顔で合わせる。
候補の動画を走査して、手本のコマの「顔の位置・大きさ」と「顔のまわりの明暗の形（向き）」に一番近いコマを探し、
そこから続けて流す（動画として続く）。各コマは顔の箱どうしが重なるように拡大・移動して、色を手本に合わせる。
python3 stand_in.py <作業> <カット番号> --frames a-b --src v1.mp4[@t0-t1],v2.mp4 [--fps 4] [--min -0.03] [--dry]
- 顔が取れん手本のコマは、前のコマの拡大・移動をそのまま使う
- 外にはみ出した所は端を伸ばす。プレビュー＝tmp/si_<カット>_<f0>.jpg（手本｜代わり の3コマ）
- 今より SSIM が --min 以上なら入れる。前の物は .bak_si
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np, mediapipe as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half
W, H, FPS = 1280, 720, 29.97   # 引数を読んだ後に geo(<作業>) に替わる（10/30）
FD = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.4)
POSE = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1)
KP = [0, 2, 5, 7, 8, 11, 12]  # 鼻・目・耳・肩（横顔でも取れる）
HEAD = [0, 2, 5, 7, 8]  # 頭だけ（肩が画面の外の寄りの時）
def pose_pts(im):
    r = POSE.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    if not r.pose_landmarks: return None
    L = r.pose_landmarks.landmark
    return {k: (L[k].x * im.shape[1], L[k].y * im.shape[0]) for k in KP if L[k].visibility > 0.5}
def rd(p, fps=None, ss=None, to=None, w=None, h=None):
    w = w or W; h = h or H
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss is not None else []) + (["-to", str(to)] if to is not None else []) + ["-i", p]
    vf = (f"fps={fps}," if fps else "") + f"scale={w}:{h}"
    r = subprocess.run(cmd + ["-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3)
def face(im):
    r = FD.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    if not r.detections: return None
    b = max(r.detections, key=lambda d: d.location_data.relative_bounding_box.width).location_data.relative_bounding_box
    return np.array([b.xmin + b.width / 2, b.ymin + b.height / 2, b.height])  # 中心 x,y と高さ（画面比）
def patch(im, f, k=2.2):
    h, w = im.shape[:2]; cx, cy, fh = f[0] * w, f[1] * h, f[2] * h * k
    x0, y0 = int(max(0, cx - fh / 2)), int(max(0, cy - fh / 2)); x1, y1 = int(min(w, cx + fh / 2)), int(min(h, cy + fh / 2))
    p = cv2.cvtColor(im[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY) if x1 > x0 + 4 and y1 > y0 + 4 else np.zeros((8, 8), np.uint8)
    p = cv2.resize(p, (32, 32)).astype(np.float32); return (p - p.mean()) / (p.std() + 1e-6)
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("--frames", required=True); ap.add_argument("--src", default="")
ap.add_argument("--fps", type=float, default=4); ap.add_argument("--min", type=float, default=-0.03); ap.add_argument("--dry", action="store_true"); ap.add_argument("--box", help="この四角 x,y,w,h（手本の画素・r2 は 1280x720）の中だけ入れる＝寄せ集めの枠"); ap.add_argument("--target", help="手本の顔を手で指定 cx,cy,h（px・手本の画素）＝人が何人もおる時"); ap.add_argument("--window", action="store_true", help="手本は黒地の中の写真の四角＝四角の中だけに入れて外は黒地"); ap.add_argument("--at", help="候補を探さず 動画@秒 を使う（clip_index.py で選んだ物）")
a = ap.parse_args(); w = os.path.abspath(a.w)
GG = geo(w); W, H, FPS = GG["W"], GG["H"], GG["FPS"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS); c1 = round(float(seg.split(":")[1].split("-")[1]) * FPS)
cutp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cutp).copy() if os.path.exists(cutp) else np.zeros((c1 - c0, H, W, 3), np.uint8)
f0, f1 = map(int, a.frames.split("-")); n = f1 - f0 + 1
r = subprocess.run(["ffmpeg", "-v", "error", "-i", glob.glob(f"{w}/ref/*.mp4")[0], "-vf", f"fps={GG['FPS_FF']},select='between(n\\,{f0}\\,{f1})',scale={W}:{H}", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
R = np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)
TF = [face(x) for x in R]; k0 = next((i for i, f in enumerate(TF) if f is not None), None)
if a.at: k0 = k0 or 0
elif k0 is None: print("手本のコマに顔が取れん＝この道具では当てられん（clip_index.py で選んで --at）"); sys.exit(1)
if a.target: cx_, cy_, h_ = map(float, a.target.split(',')); TF = [np.array([cx_ / W, cy_ / H, h_ / H])] * len(TF)
tf = TF[k0]; tp = patch(R[k0], tf) if tf is not None else None
best = (-9, None, None)
if a.at: p_, t_ = a.at.rsplit("@", 1); best = (0, p_, float(t_))
for s in ([] if a.at else a.src.split(",")):
    p, ss, to = s, None, None
    if "@" in s: p, rng = s.split("@"); ss, to = map(float, rng.split("-"))
    S = rd(p, fps=a.fps, ss=ss, to=to, w=MW, h=MH)
    for i, im in enumerate(S):
        f = face(im)
        if f is None: continue
        sc = float((patch(im, f) * tp).mean()) - 2.0 * abs(np.log(f[2] / tf[2]))
        if sc > best[0]: best = (sc, p, (ss or 0) + i / a.fps)
if best[1] is None: print("候補に顔が無い"); sys.exit(1)
print("一番近い候補", best[1], round(best[2], 2), "秒", "近さ", round(best[0], 3))
st_ = max(0, best[2] - k0 / FPS); S = rd(best[1], ss=st_, to=st_ + n / FPS + 0.5, fps=GG["FPS_FF"])[:n]
g6 = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
txt = np.ones((H, W), bool); txt[round(300 * H / 720):round(420 * H / 720)] = False  # 字幕の帯（r2 の行を高さの比で）
out = []; t0 = t1 = 0; last = None
for k in range(n):
    rr = R[k]; im = S[min(k, len(S) - 1)]; sf = face(im); rf = TF[k] if TF[k] is not None else tf
    pr, ps = (None, None) if a.target else (pose_pts(rr), pose_pts(im))
    com = [k for k in HEAD if pr and ps and k in pr and k in ps]
    if len(com) < 2: com = [k for k in KP if pr and ps and k in pr and k in ps]
    if len(com) >= 2:
        Mk, _ = cv2.estimateAffinePartial2D(np.float32([ps[k] for k in com]), np.float32([pr[k] for k in com]))
        if Mk is not None:
            # 回転は付けん（拡大と移動だけ・点の重心を合わせる）
            sc_ = float(np.sqrt(Mk[0, 0] ** 2 + Mk[1, 0] ** 2)); sp = np.float32([ps[k] for k in com]).mean(0); rp = np.float32([pr[k] for k in com]).mean(0)
            Mk = np.float32([[sc_, 0, rp[0] - sc_ * sp[0]], [0, sc_, rp[1] - sc_ * sp[1]]])
            last = Mk if last is None else (0.6 * last + 0.4 * Mk).astype(np.float32); sf = None
    if sf is not None:
        s_ = rf[2] * H / (sf[2] * H); tx = rf[0] * W - s_ * sf[0] * W; ty = rf[1] * H - s_ * sf[1] * H
        Mk = np.float32([[s_, 0, tx], [0, s_, ty]]); last = Mk if last is None else 0.6 * last + 0.4 * Mk
    if last is None:
        # 顔が取れん（横顔など）＝ぼかした白黒で ECC（拡大・移動）
        rg = cv2.GaussianBlur(cv2.resize(cv2.cvtColor(rr, cv2.COLOR_BGR2GRAY), (240, 135)).astype(np.float32), (0, 0), 3)
        ig = cv2.GaussianBlur(cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (240, 135)).astype(np.float32), (0, 0), 3)
        Mk = np.eye(2, 3, dtype=np.float32)
        try:
            _, Mk = cv2.findTransformECC(rg, ig, Mk, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), None, 5)
            Mk = cv2.invertAffineTransform(Mk); Mk[:, 2] *= W / 240
        except cv2.error:
            Mk = np.float32([[1, 0, 0], [0, 1, 0]])
        last = Mk
    wc = cv2.warpAffine(im, last.astype(np.float32), (W, H), borderMode=cv2.BORDER_REPLICATE)
    fit = wc.astype(np.float32)
    for c in range(3):
        x_, y_ = wc[..., c][txt].astype(np.float32), rr[..., c][txt].astype(np.float32)
        fit[..., c] = (wc[..., c] - x_.mean()) * (y_.std() / (x_.std() + 1e-6)) + y_.mean()  # 平均と幅だけ（中身が違う絵で崩れん）
    o = np.clip(fit, 0, 255).astype(np.uint8)
    if a.window:
        gg = cv2.cvtColor(rr, cv2.COLOR_BGR2GRAY); m = (cv2.GaussianBlur(gg, (0, 0), 3) > 28).astype(np.uint8)
        nn, lab, st, _ = cv2.connectedComponentsWithStats(m)
        if nn > 1:
            i_ = 1 + int(np.argmax(st[1:, 4])); bx, by, bw, bh = st[i_, :4]
            bg = np.median(rr[gg < 28], axis=0) if (gg < 28).any() else np.zeros(3)
            o2 = np.empty_like(o); o2[:] = bg.astype(np.uint8); o2[by:by + bh, bx:bx + bw] = o[by:by + bh, bx:bx + bw]; o = o2
    if a.box:
        bx, by, bw, bh = map(int, a.box.split(",")); base = C[f0 + k - c0].copy()
        sub = wc[by:by + bh, bx:bx + bw].astype(np.float32); ref_ = rr[by:by + bh, bx:bx + bw].astype(np.float32)
        for c in range(3): sub[..., c] = (sub[..., c] - sub[..., c].mean()) * (ref_[..., c].std() / (sub[..., c].std() + 1e-6)) + ref_[..., c].mean()
        base[by:by + bh, bx:bx + bw] = np.clip(sub, 0, 255).astype(np.uint8); o = base
    out.append(o)
    t0 += ssim(g6(rr), g6(C[f0 + k - c0])); t1 += ssim(g6(rr), g6(o))
print(f"今 {t0 / n:.3f} → 代わり {t1 / n:.3f}")
ks = [0, n // 2, n - 1]
cv2.imwrite(f"{w}/tmp/si_{a.cut}_{f0}.jpg", np.vstack([np.hstack([cv2.resize(R[k], (426, 240)), cv2.resize(out[k], (426, 240))]) for k in ks]))
if a.dry or t1 / n < t0 / n + a.min: print("書かん"); sys.exit()
if os.path.exists(cutp) and not os.path.exists(cutp + ".bak_si"): shutil.copy(cutp, cutp + ".bak_si")
for k in range(n): C[f0 + k - c0] = out[k]
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", GG["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cutp], stdin=subprocess.PIPE)
p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", n, "コマ")

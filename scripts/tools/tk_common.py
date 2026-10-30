"""tk_common.py  カメラ・描き分け・見た目の道具（cam_chain・whip_fit・flow_variants・fx_*・lab_grade・lum_frames ほか）が共通で使う小物。
単体では使わん。どの道具も <作業>（ref/*.mp4・proj/src/green.json・caps.json がある所）か mp4 のどちらかを1つ目の引数に取る。
- ref_path(x)：x が .mp4 ならそのまま・フォルダなら x/ref/*.mp4 の1本目
- probe(p)：(幅, 高さ, fps, コマ数)
- gray(p, a, n, w, h)：a コマ目から n コマを灰で（ffmpeg の select＝コマ番号ちょうど。OpenCV の seek はずれる＝51 の fx_grade で 79秒が悪化）
- bgr(p, a, n, w=None, h=None)：同じく色で（長い動画の後ろの1コマは one() の方が速い）
- one(p, f, gray_, size)：1コマだけ -ss で速く
- cap_mask(caps, f, W, H)：字幕の箱（caps.json の語・そのコマに出とる物だけ）＝green_fit と同じ形
- place(img, M, W, H, blur)：一枚絵を green.json の 2x3（絵の画素→画面）で置く＝Green.tsx と同じ
"""
import glob, json, os, subprocess
import cv2
import numpy as np


def ref_path(x):
    if x.endswith(".mp4"):
        return x
    c = sorted(glob.glob(os.path.join(x, "ref", "*.mp4")))
    if not c:
        raise SystemExit(f"手本が無い：{x}/ref/*.mp4")
    return c[0]


def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                        "-of", "json", p], capture_output=True, text=True).stdout
    s = json.loads(o)["streams"][0]; a, b = s["r_frame_rate"].split("/")
    n = int(s.get("nb_frames") or 0)
    return int(s["width"]), int(s["height"]), float(a) / float(b), n


def _sel(a, n):
    return f"select=between(n\\,{a}\\,{a + n - 1})"


def gray(p, a, n, w, h):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-i", p, "-an", "-vf", f"{_sel(a, n)},scale={w}:{h},format=gray",
                          "-vsync", "0", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w)


def bgr(p, a, n, w=None, h=None):
    if w is None:
        w, h, _, _ = probe(p)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-i", p, "-an", "-vf", f"{_sel(a, n)},scale={w}:{h}",
                          "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def one(p, f, gray_=False, size=None):
    """1コマだけ速く取る（-ss を (f+0.5)/fps に・51 の取り方）。size＝(w,h)・無ければ元の大きさ"""
    W, H, fps, _ = probe(p); w, h = size or (W, H)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-ss", f"{(f + 0.5) / fps:.4f}", "-i", p, "-frames:v", "1", "-an",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray" if gray_ else "bgr24", "-"], capture_output=True).stdout
    if not raw:
        return None
    return np.frombuffer(raw, np.uint8).reshape((h, w) if gray_ else (h, w, 3))


def load_caps(w):
    p = os.path.join(w, "proj", "src", "caps.json")
    return json.load(open(p)) if os.path.exists(p) else []


def cap_mask(caps, f, W, H):
    m = np.zeros((H, W), np.uint8)
    for c in caps:
        if c["f0"] <= f <= c["f1"]:
            x0 = int(c["x"] - 0.2 * c["fs"]); x1 = int(c["x"] + 0.62 * c["fs"] * len(c["w"]) + 0.2 * c["fs"])
            y0 = int(c["y"] - 1.0 * c["fs"]); y1 = int(c["y"] + 0.35 * c["fs"])
            m[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 1
    return cv2.dilate(m, np.ones((21, 21), np.uint8)) > 0


def M23(p, f):
    return np.array(p["M"][str(f)], np.float64).reshape(2, 3)


def place(img, M, W, H, blur=0.0):
    M = np.asarray(M, np.float64).reshape(2, 3)
    o = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    s = blur * float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
    return cv2.GaussianBlur(o, (0, 0), s) if s > 0.3 else o


def footprint(p, M, W, H):
    """絵が画面に乗っとる所（縁 3px を削る）"""
    m = cv2.warpAffine(np.full((p["h"], p["w"]), 255, np.uint8), np.asarray(M, np.float64).reshape(2, 3), (W, H), flags=cv2.INTER_NEAREST)
    return cv2.erode(m, np.ones((7, 7), np.uint8)) > 0


def lab_stats(bgr_px):
    a = cv2.cvtColor(bgr_px.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3)
    return a.mean(0), a.std(0) + 1e-3


def lab_apply(img, ma, sa, mb, sb, clip=(0.6, 1.6)):
    a = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    r = np.clip(sb / sa, *clip)
    return cv2.cvtColor(np.clip((a - ma) * r + mb, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def ssim_fast(x, y):
    """mane_check と同じ式（ガウス 11・σ1.5）。x,y＝灰の float"""
    C1, C2 = 6.5025, 58.5225; g = lambda z: cv2.GaussianBlur(z, (11, 11), 1.5)
    x = x.astype(np.float64); y = y.astype(np.float64)
    mx, my = g(x), g(y); sx, sy, sxy = g(x * x) - mx * mx, g(y * y) - my * my, g(x * y) - mx * my
    return float((((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx * mx + my * my + C1) * (sx + sy + C2))).mean())

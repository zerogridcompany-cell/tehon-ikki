"""手本の大きさ・fps・図鑑（zukan.json）の読み口（10/30 つなぎ）。道具は 1280x720・29.97 を直書きせず、ここから読む。

from geo import geo, zukan
G = geo(<作業>)  → dict(W, H, FPS, FPS_FF, SW, SH, N)
  W・H＝手本の画素・FPS＝1秒のコマ数（float）・FPS_FF＝ffmpeg の fps= に渡す文字（29.97 前後は前と同じ "2997/100"）
  SW・SH＝小さい測り用の大きさ（横 320・縦は手本の比・偶数）＝前の "scale=320:180" の代わり
  N＝コマ数
Z = zukan(<作業>)  → <作業>/zukan/zukan.json（無ければ None）
- 読む順：zukan.json の meta → cfg.json → 手本を ffprobe
- 🔒 作る段は手本の数字を zukan.json から読む・測り直さん（差の検査は最後の門だけ）
"""
import glob, json, os, subprocess
from functools import lru_cache


@lru_cache(None)
def zukan(w):
    p = os.path.join(os.path.abspath(w), "zukan", "zukan.json")
    return json.load(open(p)) if os.path.exists(p) else None


def _ff(fps, rfr=None):
    if abs(fps - 29.97) < 0.01: return "2997/100"   # r2・51 で使ってきた値のまま（変えると前の版と1コマずれる）
    if rfr and "/" in rfr: return rfr
    return f"{fps:.6g}"


@lru_cache(None)
def geo(w):
    w = os.path.abspath(w); z = zukan(w)
    if z:
        m = z["meta"]; W, H, fps, N, rfr = m["W"], m["H"], float(m["fps"]), m["frames"], m.get("r_frame_rate")
    elif os.path.exists(f"{w}/cfg.json"):
        c = json.load(open(f"{w}/cfg.json")); W, H, fps, N, rfr = c["width"], c["height"], float(c["fps"]), c["frames"], None
    else:
        ref = glob.glob(f"{w}/ref/*.mp4")[0]
        st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                                        "-of", "json", ref], capture_output=True, text=True).stdout)["streams"][0]
        a, b = st["r_frame_rate"].split("/"); W, H, fps, N, rfr = st["width"], st["height"], float(a) / float(b), int(st.get("nb_frames") or 0), st["r_frame_rate"]
    SW = 320; SH = int(round(H * SW / W / 2) * 2)
    return dict(W=int(W), H=int(H), FPS=fps, FPS_FF=_ff(fps, rfr), SW=SW, SH=SH, N=int(N))


def cut_frames(w):
    """図鑑のカット [(f0, f1), …]（f1＝次の頭）。図鑑が無ければ eye/segs.txt を手本の fps で読む"""
    z = zukan(w)
    if z: return [(c["f0"], c["f1"]) for c in z["cuts"]]
    fps = geo(w)["FPS"]; out = []
    for l in open(os.path.join(os.path.abspath(w), "eye", "segs.txt")):
        if ":" in l:
            a, b = map(float, l.split(":")[1].split("-")); out.append((round(a * fps), round(b * fps)))
    return out


# ── 10/30 足し（道具の直書きを外す時に足した・上の関数は触ってない）──
def half(w):
    """測り用の半分の大きさ (MW, MH)＝前の 640x360 の代わり（横長 1280x720 では 640x360 のまま・縦 576x1024 では 288x512）"""
    G = geo(w)
    return int(round(G["W"] / 4) * 2), int(round(G["H"] / 4) * 2)


@lru_cache(None)
def geo_mp4(p):
    """作業フォルダを取らん道具用：mp4 を ffprobe して geo と同じ形の dict を返す"""
    st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                                    "-of", "json", os.path.abspath(p)], capture_output=True, text=True).stdout)["streams"][0]
    a, b = st["r_frame_rate"].split("/"); W, H, fps = int(st["width"]), int(st["height"]), float(a) / float(b)
    SW = 320; SH = int(round(H * SW / W / 2) * 2)
    return dict(W=W, H=H, FPS=fps, FPS_FF=_ff(fps, st["r_frame_rate"]), SW=SW, SH=SH, N=int(st.get("nb_frames") or 0))


def work_of(p):
    """道具に渡された道（作業フォルダの中のファイル）から、上へたどって作業フォルダ（ref/ か zukan/ か cfg.json がある所）を返す。無ければ None"""
    d = os.path.abspath(p if os.path.isdir(p) else os.path.dirname(p))
    while d != "/":
        if os.path.isdir(f"{d}/ref") or os.path.isdir(f"{d}/zukan") or os.path.exists(f"{d}/cfg.json"): return d
        d = os.path.dirname(d)
    return None

"""段0 見る（miru）の共通部品：手本の大きさ・コマの時刻表・小さいコマの一括読み・原寸のコマを番号で読む。
🔴 コマ番号は「手本のそのままのコマ」（-vsync passthrough）。時刻は pts の表から（可変 fps の手本で 1コマずれん・51 は 2716 の後に抜けあり）
"""
import json, os, subprocess
import numpy as np

SW, SH = 320, 180   # 小さいコマ（カット・動き・静止の測り＝motion_kind・still_check と同じ大きさ）


def probe(p):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,codec_name", "-of", "json", p],
                                  capture_output=True, text=True).stdout)["streams"][0]
    a, b = o["r_frame_rate"].split("/"); fps = float(a) / float(b)
    return dict(W=int(o["width"]), H=int(o["height"]), fps=fps, r_frame_rate=o["r_frame_rate"],
                avg_frame_rate=o["avg_frame_rate"], codec=o["codec_name"])


def pts_table(p, cache):
    """コマ番号 → 秒（ffprobe の pts）。cache に npy で残す"""
    if os.path.exists(cache): return np.load(cache)
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time,best_effort_timestamp_time",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    t = []
    for l in o.split("\n"):
        v = [x for x in l.strip().split(",") if x and x != "N/A"]
        if v: t.append(float(v[0]))
    t = np.array(t, np.float64); t = t - t[0] if len(t) else t
    np.save(cache, t); return t


def small(p, cache, w=SW, h=SH):
    """全部のコマを w×h の BGR で1回だけ読む（npy の memmap に残す）"""
    if os.path.exists(cache):
        return np.load(cache, mmap_mode="r")
    pr = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-map", "0:v:0", "-vsync", "passthrough",
                           "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    fs = []; n = w * h * 3
    while True:
        b = pr.stdout.read(n)
        if len(b) < n: break
        fs.append(np.frombuffer(b, np.uint8).reshape(h, w, 3))
    pr.wait(); a = np.stack(fs)
    np.save(cache, a); return np.load(cache, mmap_mode="r")


def native(p, idx, W, H, scale_w=None):
    """番号のコマだけを原寸（か幅 scale_w）で読む。全部のコマを1回流して要る物だけ残す（select の式は長いと ffmpeg が落ちる）。返り＝{番号: BGR}"""
    want = set(int(i) for i in idx)
    if not want: return {}
    w = scale_w or W; h = int(round(H * w / W / 2)) * 2 if scale_w else H
    vf = ["-vf", f"scale={w}:{h}:flags=area"] if scale_w else []
    pr = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-map", "0:v:0", "-vsync", "passthrough"] + vf +
                          ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    n = w * h * 3; k = 0; out = {}; last = max(want)
    while k <= last:
        b = pr.stdout.read(n)
        if len(b) < n: break
        if k in want: out[k] = np.frombuffer(b, np.uint8).reshape(h, w, 3).copy()
        k += 1
    pr.kill(); pr.wait()
    return out


def gray(F):
    return (F[..., 0].astype(np.float32) * 0.114 + F[..., 1].astype(np.float32) * 0.587 + F[..., 2].astype(np.float32) * 0.299)


def nashi(konkyo, **kw):
    """「なし」は必ず根拠の数字と一緒に書く（check_zukan が見る）"""
    d = {"v": "なし", "konkyo": konkyo}; d.update(kw); return d

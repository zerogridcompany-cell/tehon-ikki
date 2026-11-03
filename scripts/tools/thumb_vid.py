"""素材が YouTube のサムネイル（src/hi_img.json の url／page に動画の id）のカットを、元の動画を落として1コマずつ当て直す（r2 の 93＝0.70→0.89）。
python3 thumb_vid.py <作業> [--max 12]
- 動画は src/thumbvid/<id>.mp4（1080p まで・1本ごと10秒あける）。60秒ずつの窓で vid_patch（点が上がったコマだけ入れる）
"""
import argparse, json, os, re, subprocess, sys, time
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--max", type=int, default=12); a = ap.parse_args()
w = os.path.abspath(a.w); T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, T); from geo import geo; FPS = geo(w)["FPS"]  # 10/30 geo
p = f"{w}/src/hi_img.json"
if not os.path.exists(p): print("src/hi_img.json が無い＝サムネイル由来のカット無し"); sys.exit(0)
d = json.load(open(p)); segs = {}
for l in open(f"{w}/eye/segs.txt"):
    if ":" in l:
        k, v = l.split(":"); s0, s1 = map(float, v.split("-")); segs[k.strip()] = (round(s0 * FPS), round(s1 * FPS))
todo = []
for k, v in d.items():
    m = re.search(r"(?:vi/|v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", (v.get("url", "") + " " + v.get("page", "")))
    if m and k in segs and os.path.exists(f"{w}/cuts/{k}.mp4"): todo.append((k, m.group(1)))
print("サムネイル由来", todo)
os.makedirs(f"{w}/src/thumbvid", exist_ok=True)
for k, vid in todo[:a.max]:
    out = f"{w}/src/thumbvid/{vid}.mp4"
    if not os.path.exists(out):
        subprocess.run(["yt-dlp", "--cookies-from-browser", "chrome", "-f", "bv*[height<=1080][ext=mp4]/bv*[height<=1080]", "--remux-video", "mp4", "-o", out, f"〈URL〉], capture_output=True); time.sleep(10)
    if not os.path.exists(out): print(k, vid, "落とせんかった"); continue
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip() or 0)
    f0, f1 = segs[k]; t = 0.0
    while t < dur:
        r = subprocess.run(["/usr/bin/python3", f"{T}/vid_patch.py", w, k, out, f"{t:.1f}", f"{min(dur, t + 65):.1f}", "--frames", f"{f0}-{f1 - 1}"], capture_output=True, text=True)
        print(k, vid, f"{t:.0f}s", r.stdout.count("入れた"), "コマ入れた"); t += 60

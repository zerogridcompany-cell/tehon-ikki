"""手本をカットに分けて、Codex の目に渡す材料（segs.txt・一覧の絵・1カットの絵）を作る。

python3 eye_prep.py <作業フォルダ>     （手本＝<作業>/ref/*.mp4）
- カット＝Y の面の平均の差の scene 値（ffmpeg と同じ式・51 で実測）0.3 超え。最短 3コマ
- 出す物：eye/segs.txt（番号: 始まり-終わり 秒）・eye/sheets/gNNN.png（12カット/枚）・eye/k/kNNN.png（480px）・eye/task.md（雛形から）
🔴 決まり.md の分け方：カットは機械、字の中身・色は Codex、字の時刻は機械＋/jimaku-sync、書体は Codex の候補→当て比べ
"""
import glob, json, os, subprocess, sys
import numpy as np

w = sys.argv[1]
ref = glob.glob(f"{w}/ref/*.mp4")[0]
o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                    "-of", "json", ref], capture_output=True, text=True).stdout
st = json.loads(o)["streams"][0]; W, H = st["width"], st["height"]; a, b = st["r_frame_rate"].split("/"); fps = float(a) / float(b)
r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", ref, "-vf", "scale=320:-2", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
h2 = int(round(H * 320 / W / 2) * 2)
Y = np.frombuffer(r.stdout, np.uint8).reshape(-1, h2, 320).astype(np.int16)
m = np.array([0.0] + [np.abs(Y[i] - Y[i - 1]).mean() for i in range(1, len(Y))])
s = np.array([0.0] + [min(m[i], abs(m[i] - m[i - 1])) / 100 for i in range(1, len(Y))])
cuts = [0]
for i in range(1, len(Y)):
    if s[i] > 0.3 and i - cuts[-1] >= 3:
        cuts.append(i)
cuts.append(len(Y))
e = f"{w}/eye"; os.makedirs(f"{e}/sheets", exist_ok=True); os.makedirs(f"{e}/k", exist_ok=True)
with open(f"{e}/segs.txt", "w") as fo:
    for j in range(len(cuts) - 1):
        fo.write(f"{j}: {cuts[j] / fps:.3f}-{cuts[j + 1] / fps:.3f}\n")
for j in range(len(cuts) - 1):
    mid = (cuts[j] + cuts[j + 1]) // 2
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", ref, "-vf", f"select=eq(n\\,{mid}),scale=480:-2", "-vsync", "0", "-frames:v", "1", f"{e}/k/k{j:03d}.png"])
ks = sorted(glob.glob(f"{e}/k/k*.png"))
for g0 in range(0, len(ks), 12):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-pattern_type", "glob", "-i", f"{e}/k/k*.png", "-vf",
                    f"select=between(n\\,{g0}\\,{g0 + 11}),tile=4x3", "-vsync", "0", "-frames:v", "1", f"{e}/sheets/g{g0:03d}.png"])
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "eye_task.md")).read()
open(f"{e}/task.md", "w").write(tpl.replace("__REF__", os.path.basename(ref)).replace("__W__", str(W)).replace("__H__", str(H))
                                 .replace("__FPS__", f"{fps:.3f}").replace("__SEC__", f"{len(Y) / fps:.1f}"))
json.dump({"frames": int(len(Y)), "fps": fps, "width": W, "height": H}, open(f"{w}/cfg.json", "w"))
print("カット", len(cuts) - 1, "コマ", len(Y), f"{W}x{H} {fps:.3f}fps → {e}/")

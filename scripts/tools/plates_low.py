"""人が出ん・点の低いカットを、Codex の一枚絵（手本のコマを参照・plate_task.md）で埋める（r2：64 0.38→0.77・115・48・153・157・110 の3D 0.5→0.7）。
python3 plates_low.py <作業> <書き出し.mp4> [--max-ssim 0.6] [--step 6] [--dry]
- 選ぶカット：今の SSIM が --max-ssim 未満・cuts/<番号>.mp4 がある・一枚絵（green.json）が上に被っとらん・eye/out.json の what に人の語が無い
- 長いカットは --step コマおきに1枚。絵は mg/auto/<番号>_<コマ>/plate.png（Codex 3本ずつ）→ plate_into_cut.py（点が上がったコマだけ入れる）
- 🔴 人の出るカットは描き直さん（決め.md：人は元の映像だけ）。参照のコマは目で確かめる（select と物差しのコマ番号が1つずれる所がある）
"""
import argparse, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import frames, ssim
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--max-ssim", type=float, default=0.6); ap.add_argument("--step", type=int, default=6); ap.add_argument("--dry", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w); T = os.path.dirname(os.path.abspath(__file__)); SK = os.path.dirname(os.path.dirname(T))
import glob
ref = glob.glob(f"{w}/ref/*.mp4")[0]; R = frames(ref); V = frames(os.path.join(w, a.out)); n = min(len(R), len(V))
shots = {str(s["i"]): s for s in json.load(open(f"{w}/eye/out.json"))["shots"]}
green = json.load(open(f"{w}/proj/src/green.json")) if os.path.exists(f"{w}/proj/src/green.json") else {}
PEOPLE = re.compile(r"\b(man|woman|men|women|person|people|face|he|she|his|her|musk|elon|interview|anchor|host|crowd|boy|girl|child|kid|portrait|speaker|audience|hands?)\b", re.I)
jobs = []
for l in open(f"{w}/eye/segs.txt"):
    if ":" not in l: continue
    k, v = l.split(":"); k = k.strip(); s0, s1 = map(float, v.split("-")); f0, f1 = round(s0 * 29.97), min(n, round(s1 * 29.97))
    if f1 - f0 < 1 or not os.path.exists(f"{w}/cuts/{k}.mp4"): continue
    m = float(np.mean([ssim(R[i], V[i]) for i in range(f0, f1)]))
    what = str(shots.get(k, {}).get("what", ""))
    if m >= a.max_ssim: continue
    if any(g["f0"] < f1 and g["f1"] >= f0 for g in green.values()): print(k, "一枚絵が被っとる＝飛ばす"); continue
    if PEOPLE.search(what): print(k, round(m, 3), "人が出る＝飛ばす：", what[:60]); continue
    for c in range(f0, f1, a.step): jobs.append((k, c, min(f1, c + a.step), what))
print("描く絵", len(jobs), [(j[0], j[1]) for j in jobs])
if a.dry or not jobs: sys.exit(0)
tpl = open(f"{SK}/references/plate_task.md").read()
def one(j):
    k, s, e, what = j; d = f"{w}/mg/auto/{k}_{s}"; os.makedirs(d, exist_ok=True); mid = (s + e - 1) // 2
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", ref, "-vf", f"fps=2997/100,select=eq(n\\,{mid})", "-vsync", "0", "-frames:v", "1", f"{d}/ref.png"])
    open(f"{d}/task.md", "w").write(tpl.replace("__W__x__H__", "1280x720").replace("__DESC__", what or "見本のコマの中身").replace("__TONE__", "見本どおり"))
    if not os.path.exists(f"{d}/plate.png"):
        subprocess.run(["codex", "exec", "--skip-git-repo-check", "-s", "workspace-write", "task.md を読んで、その通りに画像を1枚生成して plate.png に保存して。参照画像は ref.png。"], cwd=d, stdin=subprocess.DEVNULL, capture_output=True)
    return j, os.path.exists(f"{d}/plate.png")
with ThreadPoolExecutor(3) as ex: res = list(ex.map(one, jobs))
for (k, s, e, _), ok in res:
    if not ok: print(k, s, "絵ができんかった"); continue
    r = subprocess.run(["/usr/bin/python3", f"{T}/plate_into_cut.py", w, k, f"{w}/mg/auto/{k}_{s}/plate.png", "--frames", f"{s}-{e - 1}"], capture_output=True, text=True)
    print(k, s, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:])

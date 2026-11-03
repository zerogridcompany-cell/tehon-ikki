"""手本の字幕（真ん中の帯の白い字）を全コマ読み、「字・出るコマ・消えるコマ・箱」の表にする。

python3 txt_events.py <作業フォルダ> [--band 300,395]
- txt/f/%05d.jpg（手本の全コマ）が要る（ffmpeg -i ref.mp4 -q:v 2 txt/f/%05d.jpg）
- 帯を切り、白い所だけを残した白黒の絵（2倍）にして macOS Vision（~/bin/ocr-box）で読む
- 1〜2コマだけ読めん・読み違いは前後で埋める（同じ字が前後に続けばつなぐ）
- 出す物：txt/events.json＝[{text, f0, f1（最後のコマ・含む）, box:[x0,y0,x1,y1]（手本の画素）, words:[…]}]
"""
import argparse, glob, json, os, re, subprocess
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--band", default="300,395")
g = ap.parse_args()
y0, y1 = map(int, g.band.split(","))
fd = f"{g.w}/txt/f"; bd = f"{g.w}/txt/b"; os.makedirs(bd, exist_ok=True)
files = sorted(glob.glob(f"{fd}/*.jpg"))
for p in files:
    q = f"{bd}/{os.path.basename(p)[:-4]}.png"
    if os.path.exists(q):
        continue
    im = cv2.imread(p)[y0:y1]
    # 白黒にすると字の光が削れて読み違いが増えた（10/25）→ 帯を切って2倍にするだけ
    cv2.imwrite(q, cv2.resize(im, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
bs = sorted(glob.glob(f"{bd}/*.png"))
raw = {}
for k in range(0, len(bs), 200):
    out = subprocess.run([os.path.expanduser("~/bin/ocr-box")] + bs[k:k + 200], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or not parts[1].strip():
            continue
        x0, a, x1, b = map(float, parts[2].split(","))
        raw[int(parts[0][:-4])] = (re.sub(r"\s+", " ", parts[1].replace("|", " ")).strip(),
                                   [x0 / 2, y0 + a / 2, x1 / 2, y0 + b / 2])
n = len(files)
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
seq = [raw.get(i + 1, ("", None)) for i in range(n)]
# 1〜2コマの抜け・読み違いを埋める：前と後ろが同じ字なら間も同じ
for i in range(1, n - 1):
    for gap in (1, 2):
        if i + gap < n and norm(seq[i - 1][0]) and norm(seq[i - 1][0]) == norm(seq[i + gap][0]):
            for j in range(i, i + gap):
                if norm(seq[j][0]) != norm(seq[i - 1][0]):
                    seq[j] = seq[i - 1]
ev = []
for i, (t, box) in enumerate(seq):
    k = norm(t)
    if not k:
        continue
    if ev and norm(ev[-1]["text"]) == k and ev[-1]["f1"] == i - 1:
        ev[-1]["f1"] = i
        ev[-1]["boxes"].append(box)
        continue
    ev.append({"text": t, "f0": i, "f1": i, "boxes": [box]})
for e in ev:
    bx = np.array(e.pop("boxes"))
    e["box"] = [round(float(v), 1) for v in np.median(bx, 0)]
    e["frames"] = e["f1"] - e["f0"] + 1
json.dump(ev, open(f"{g.w}/txt/events.json", "w"), indent=1, ensure_ascii=False)
print(len(ev), "件")
for e in ev[:60]:
    print(e["f0"], e["f1"], e["text"], e["box"])

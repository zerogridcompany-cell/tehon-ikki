"""Codex の目（eye/out.json）から、描き直す一枚絵の表（plates.tsv）と、1枚ごとの頼み書き（task.md・ref.png）を作る。

python3 make_plates.py <作業フォルダ> <波の名前 例 mg/w1> [--kinds mg,text_only] [--live]
- --keep-text＝字幕の層が無く字が絵の一部の手本（字も描かせる）
- 対象のカット＝kind が mg（既定）。--live を付けると「本人が映らん実写」も入れる（🔴 r2 では実写は元探しだけ＝付けん。手本ごとに決めてもらう）
- カットの中を、絵が入れ替わる所で割る（160x90 の相関 0.6 未満かつ差 12 超え）。1コマだけの塊（光・つなぎ）は外す
- 1塊＝1枚。下敷き＝塊の真ん中のコマ。中身の説明＝eye の what と mg の what。色調＝下敷きの彩度と明るさから
- 出す物：<波>/plates.tsv（id f0 f1 fm tone desc）・<波>/<id>/ref.png・task.md、<波>/run_codex.sh（3本ずつ）
"""
import argparse, glob, json, os, subprocess
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("wave"); ap.add_argument("--kinds", default="mg"); ap.add_argument("--live", action="store_true"); ap.add_argument("--keep-text", action="store_true")
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
cap = cv2.VideoCapture(ref); fps = cap.get(cv2.CAP_PROP_FPS)
eye = json.load(open(f"{a.w}/eye/out.json"))
mgw = {m["i"]: m["what"] for m in eye.get("mg", [])}
kinds = set(a.kinds.split(","))
G = f"{a.w}/{a.wave}"; os.makedirs(G, exist_ok=True)
rows = []
for s in eye["shots"]:
    who = " ".join(s.get("who") or [])
    take = s["kind"] in kinds or (a.live and s["kind"] in ("live", "mix") and (not who or who == "?"))
    if not take:
        continue
    f0, f1 = int(round(s["t0"] * fps)), int(round(s["t1"] * fps)) - 1
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0); fr = []
    for n in range(f0, f1 + 1):
        ok, im = cap.read()
        if not ok:
            break
        fr.append(im)
    if not fr:
        continue
    sm = [cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (160, 90)).astype(float) for x in fr]
    b = [0]
    for k in range(1, len(sm)):
        if np.corrcoef(sm[k].ravel(), sm[k - 1].ravel())[0, 1] < 0.6 and np.abs(sm[k] - sm[k - 1]).mean() > 12:
            b.append(k)
    b.append(len(sm))
    for j in range(len(b) - 1):
        if b[j + 1] - b[j] < 2:
            continue
        g0, g1 = f0 + b[j], f0 + b[j + 1] - 1; fm = (g0 + g1) // 2
        im = fr[fm - f0]; hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        sat, val = hsv[..., 1].mean(), hsv[..., 2].mean()
        hue = int(np.median(hsv[..., 0][hsv[..., 1] > 60])) * 2 if (hsv[..., 1] > 60).any() else 0
        tone = ("black-and-white" if sat < 20 else f"color (dominant hue about {hue} degrees, saturation {int(sat)})") + (", dark" if val < 60 else ", bright" if val > 180 else "")
        pid = f"c{s['i']}_{j}"
        desc = (s.get("what") or "") + (" / " + mgw[s["i"]] if s["i"] in mgw else "")
        rows.append((pid, g0, g1, fm, tone, desc.replace("\t", " ").replace("\n", " ")))
        os.makedirs(f"{G}/{pid}", exist_ok=True)
        cv2.imwrite(f"{G}/{pid}/ref.png", im)
        tpl = open(os.path.join(HERE, "..", "references", "plate_task.md")).read()
        if a.keep_text:
            # 上に乗る字幕の層が無い手本（字が絵の一部＝showreel・ポスター）。字も見本どおり全部描かせる（t181 10/25）
            tpl = tpl.replace("- 🔴 真ん中に乗っとる白い字幕（英語の短い言葉）は**描かない**。その下の絵を続けて描く", "- 🔴 絵の中の字は全部、見本どおりの文字・書体の感じ・大きさ・位置・色で描く（この手本は字も絵の一部）")
        open(f"{G}/{pid}/task.md", "w").write(tpl.replace("__DESC__", desc).replace("__TONE__", tone).replace("__W__", str(im.shape[1])).replace("__H__", str(im.shape[0])))
with open(f"{G}/plates.tsv", "w") as fo:
    for r in rows:
        fo.write("\t".join(map(str, r)) + "\n")
open(f"{G}/run_codex.sh", "w").write(f"""#!/bin/bash
# Codex で一枚絵を 3本ずつ。🔴 `--full-auto` は無い・`-i` は後ろの文を食う＝付けん・ffmpeg は -nostdin
G={os.path.abspath(G)}
one(){{ d=$G/$1; [ -s $d/plate.png ] && {{ echo "$1 skip"; return; }}; cd $d && ${{TI_CODEX:-codex}} exec --skip-git-repo-check -c 'mcp_servers={{}}' -s workspace-write "task.md を読んで、その通りに画像を1枚生成して plate.png に保存して。参照画像は ref.png。" < /dev/null > codex.log 2>&1; [ -s $d/plate.png ] && echo "$1 OK" || echo "$1 NG"; }}
export -f one; export G
cut -f1 $G/plates.tsv | xargs -P 6 -I{{}} bash -c 'one {{}}'
echo ALLDONE
""")
os.chmod(f"{G}/run_codex.sh", 0o755)
print("一枚絵", len(rows), "枚 →", G)

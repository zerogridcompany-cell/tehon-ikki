"""長い元動画1本を、まだ黒いカット全部に当てる（match.py を回す・SIFT の控え .pkl は1回目だけ作る）。

/usr/bin/python3 scan_long.py <作業フォルダ> <長い動画.mp4> [--only 60,66] [--out shirabe/scan/<名前>.json] [--min-inl 25] [--min-ssim 0.45]
- 対象＝eye/out.json の kind=live で cuts/_all.json に無いカット。--only で指定した時は種類も有る無しも問わずその番号だけ
- 出力＝1行1カット：カット・当たり(○/△/×)・start秒・ssim・inliers。json にも同じ
- 当たりの線：○＝inliers≥min-inl かつ ssim≥min-ssim／△＝inliers≥15（目で見る価値あり）／×
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("video"); ap.add_argument("--only"); ap.add_argument("--out"); ap.add_argument("--force", action="store_true", help="cuts/_all.json に有るカットも当てる")
ap.add_argument("--min-inl", type=int, default=25); ap.add_argument("--min-ssim", type=float, default=0.45)
g = ap.parse_args()
W = g.w; ref = [f for f in os.listdir(f"{W}/ref") if f.endswith(".mp4")][0]; ref = f"{W}/ref/{ref}"
shots = json.load(open(f"{W}/eye/out.json"))["shots"]
have = json.load(open(f"{W}/cuts/_all.json")) if os.path.exists(f"{W}/cuts/_all.json") else {}
only = {int(x) for x in g.only.split(",")} if g.only else None
# --only で番号を指定した時は、種類（mix・mg も）・入っとるかを問わず当てる（10/26 指定した mix のカットが空振りしとった）
targets = [s for s in shots if s["i"] in only] if only else [s for s in shots if s.get("kind") == "live" and (g.force or str(s["i"]) not in have)]
name = os.path.splitext(os.path.basename(g.video))[0]
out = g.out or f"{W}/shirabe/scan/{name}.json"; os.makedirs(os.path.dirname(out), exist_ok=True)
res = json.load(open(out)) if os.path.exists(out) else {}
print(f"動画={g.video} 対象={[s['i'] for s in targets]}", flush=True)
for s in targets:
    k = str(s["i"]); tmp = f"{out}.{k}.tmp.json"
    r = subprocess.run([sys.executable, f"{HERE}/match.py", ref, str(s["t0"]), str(s["t1"]), g.video, "--out", tmp], capture_output=True, text=True)
    try:
        j = json.load(open(tmp)); os.remove(tmp)
    except Exception:
        print(k, "ERR", r.stderr[-150:].replace("\n", " "), flush=True); continue
    inl = j.get("inliers") or 0; ss = j.get("ssim") or 0
    mark = "○" if (inl >= g.min_inl and ss >= g.min_ssim) else ("△" if inl >= 15 else "×")
    res[k] = {"video": g.video, "mark": mark, "start": j.get("start"), "ssim": ss, "inliers": inl, "flip": j.get("flip"), "H": j.get("H"), "best_inliers": j.get("best_inliers")}
    print(f"{k:>4} {mark} start={j.get('start')} ssim={ss} inliers={inl}", flush=True)
    json.dump(res, open(out, "w"), indent=1)
print("SCANDONE", out)

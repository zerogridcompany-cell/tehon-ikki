"""Remotion の層（look・caps・cards・green・cut）を1つずつ外した試しの書き出しと、全部入りを、カットごとに手元で採点して、
外すと上がる層だけを proj/src/layer_off.json に書く（カットの範囲ごと）。

python3 layer_pick.py <作業フォルダ> <全部入り.mp4> <層名=試し.mp4 …> [--min 0.005] [--out proj/src/layer_off.json]
- 点＝cut_score と同じ灰色・手本の半分（r2 は 640x360）の SSIM（1コマごと）。1本ずつ全部読んで比べる（重さ＝1本 約0.5GB）
- 表＝tmp/layer_pick.json（カット・全部入り・層ごとの点・選んだ外す層）
"""
import argparse, glob, json, sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cut_score import frames, ssim
import cut_score


def per_frame(R, O):
    n = min(len(R), len(O))
    return np.array([ssim(R[k], O[k]) for k in range(n)] + [0.0] * (len(R) - n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("full"); ap.add_argument("vars", nargs="+"); ap.add_argument("--min", type=float, default=0.005)
    ap.add_argument("--out", default="proj/src/layer_off.json")
    g = ap.parse_args()
    cut_score.use_geo(g.w); FPS = cut_score.FPS  # 10/30 geo
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    R = frames(ref)
    shots = sorted(json.load(open(f"{g.w}/eye/out.json"))["shots"], key=lambda s: float(s["t0"]))
    rng = []
    for j, s in enumerate(shots):
        f0 = int(round(float(s["t0"]) * FPS))
        f1 = int(round(float(shots[j + 1]["t0"]) * FPS)) if j + 1 < len(shots) else len(R)
        rng.append((str(s["i"]), f0, f1))
    full = per_frame(R, frames(g.full)); print("全部入り", round(full.mean(), 4), flush=True)
    sc = {}
    for v in g.vars:
        name, p = v.split("=", 1)
        sc[name] = per_frame(R, frames(p)); print(name, "を外す", round(sc[name].mean(), 4), flush=True)
    table, off, tot = [], [], full.copy()
    for i, f0, f1 in rng:
        base = float(full[f0:f1].mean())
        row = {"i": i, "f0": f0, "f1": f1, "full": round(base, 4)}
        pick = []
        for name, a in sc.items():
            x = float(a[f0:f1].mean()); row[name] = round(x, 4)
            if x - base > g.min:
                pick.append(name)
        if pick:
            off.append({"f0": f0, "f1": f1, "off": pick, "cut": i})
            # 見込み＝一番上がる1つだけ外した値（2つ以上は足し算で見込まん）
            best = max(pick, key=lambda n: sc[n][f0:f1].mean())
            tot[f0:f1] = sc[best][f0:f1]
        row["pick"] = pick; table.append(row)
    json.dump(off, open(f"{g.w}/{g.out}", "w"), indent=1)
    json.dump(table, open(f"{g.w}/tmp/layer_pick.json", "w"), indent=1)
    print("外すカット", len(off), "見込み", round(full.mean(), 4), "→", round(tot.mean(), 4), "以上（2つ外す所は書き出して確かめる）")


if __name__ == "__main__":
    main()

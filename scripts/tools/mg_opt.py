"""Remotion の MG の値（look.json の一部）を、手本の同じコマと比べて1つずつ動かし、点が上がる値を探す（座標ごとの下り坂）。
書き出しはそのコマの範囲だけ（--frames）。全部の版を書き出さんで値を決める。

python3 mg_opt.py <作業フォルダ> <f0> <f1> <値の名前,…> [--rounds 2] [--out tmp/mg_opt_<f0>.json]
- 数の値は ×0.5・×0.75・×1.33・×2 を試す。色（#rrggbb）は明るさ ±12%
- 部品が --props '{"look":{…}}' を読む形になっとる事（Logo.tsx・Slabs.tsx）
- --json slabs：proj/src/slabs.json の中の値を「道:幅」で動かす（例 cam.2.x:2,cam.2.fov:5）。±幅・±幅/2 を試す。props は {"slabs": 丸ごと}
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import frames, ssim
import cut_score


def render(w, f0, f1, look, out, key="look"):
    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "R2", out, "--muted", "--gl=angle", "--concurrency=3",
                        f"--frames={f0}-{f1 - 1}", "--props=" + json.dumps({key: look})], cwd=f"{w}/proj", capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-500:]); return None
    return frames(out)


def col(c, k):
    v = [min(255, max(0, int(int(c[i:i + 2], 16) * k))) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int); ap.add_argument("keys")
    ap.add_argument("--rounds", type=int, default=2); ap.add_argument("--out"); ap.add_argument("--json")
    g = ap.parse_args()
    cut_score.use_geo(g.w)  # 10/30 geo
    if g.json:
        return opt_json(g)
    w = os.path.abspath(g.w)
    ref = glob.glob(f"{w}/ref/*.mp4")[0]
    R = frames(ref)[g.f0:g.f1]
    base = json.load(open(f"{w}/proj/src/look.json"))
    cur = {k: base[k] for k in g.keys.split(",")}
    tmp = f"{w}/tmp/mg_opt.mp4"

    def score(look):
        O = render(w, g.f0, g.f1, look, tmp)
        if O is None:
            return -1
        return float(np.mean([ssim(a, b) for a, b in zip(R, O)]))

    best = score(cur); print("今", round(best, 4), cur, flush=True)
    log = [{"look": dict(cur), "ssim": best}]
    for rd in range(g.rounds):
        for k in list(cur):
            v = cur[k]
            cands = [col(v, m) for m in (0.88, 1.12)] if isinstance(v, str) else [v * m for m in (0.5, 0.75, 1.33, 2.0)]
            for c in cands:
                t = dict(cur); t[k] = round(c, 4) if not isinstance(c, str) else c
                s = score(t); log.append({"look": t, "ssim": s})
                if s > best + 0.001:
                    best, cur = s, t; print(" ↑", k, t[k], round(s, 4), flush=True)
    json.dump({"best": cur, "ssim": best, "log": log}, open(g.out or f"{w}/tmp/mg_opt_{g.f0}.json", "w"), indent=1)
    print("決まり", round(best, 4), cur)


def getp(o, path):
    for k in path.split("."):
        o = o[int(k)] if isinstance(o, list) else o[k]
    return o


def setp(o, path, v):
    ks = path.split(".")
    for k in ks[:-1]:
        o = o[int(k)] if isinstance(o, list) else o[k]
    k = ks[-1]
    if isinstance(o, list):
        o[int(k)] = v
    else:
        o[k] = v


def opt_json(g):
    import copy
    w = os.path.abspath(g.w)
    ref = glob.glob(f"{w}/ref/*.mp4")[0]
    R = frames(ref)[g.f0:g.f1]
    cur = json.load(open(f"{w}/proj/src/{g.json}.json"))
    spec = [(x.split(":")[0], float(x.split(":")[1])) for x in g.keys.split(",")]
    tmp = f"{w}/tmp/mg_opt.mp4"

    def score(o):
        O = render(w, g.f0, g.f1, o, tmp, g.json)
        return -1 if O is None else float(np.mean([ssim(a, b) for a, b in zip(R, O)]))

    best = score(cur); print("今", round(best, 4), flush=True)
    for rd in range(g.rounds):
        for path, st in spec:
            for d in (st, -st, st / 2, -st / 2):
                t = copy.deepcopy(cur); setp(t, path, round(getp(cur, path) + d, 4))
                s = score(t)
                if s > best + 0.001:
                    best, cur = s, t; print(" ↑", path, getp(cur, path), round(s, 4), flush=True)
    out = g.out or f"{w}/tmp/mg_opt_{g.json}_{g.f0}.json"
    json.dump(cur, open(out, "w"), indent=1)
    print("決まり", round(best, 4), "→", out)


if __name__ == "__main__":
    main()

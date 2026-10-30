"""hi.json の全カットを fit_cut.py で作る。1コマごとに追う版と追わん版の両方を作って SSIM が高い方を cuts/ に残す。

python3 fit_all.py <作業フォルダ> [--only 3,17]
結果の一覧＝<作業フォルダ>/cuts/_all.json
"""
import argparse, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--only"); ap.add_argument("--hi", default="src/hi.json"); ap.add_argument("--model", default="homog")
g = ap.parse_args()
hi = json.load(open(f"{g.w}/{g.hi}"))
keys = g.only.split(",") if g.only else sorted(hi, key=int)
ap_ = f"{g.w}/cuts/_all.json"
allr = json.load(open(ap_)) if os.path.exists(ap_) else {}
for k in keys:
    res = {}
    for t in (1, 0):
        out = f"cuts_t{t}"
        r = subprocess.run([sys.executable, "-W", "ignore", f"{HERE}/fit_cut.py", g.w, k, "--track", str(t), "--out", out, "--hi", g.hi, "--model", g.model],
                           capture_output=True, text=True)
        try:
            res[t] = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            pass
    if not res:
        print(k, "作れんかった", flush=True); continue
    t = max(res, key=lambda t: res[t]["ssim_color"])
    if k in allr and allr[k]["ssim_color"] >= res[t]["ssim_color"]:
        # 前に作った物（別の重ね方）の方が良ければ残す
        print(k, "前の方が良い", allr[k]["ssim_color"], "＞", res[t]["ssim_color"], flush=True)
        continue
    os.makedirs(f"{g.w}/cuts", exist_ok=True)
    for ext in ("mp4", "json"):
        shutil.copy(f"{g.w}/cuts_t{t}/{k}.{ext}", f"{g.w}/cuts/{k}.{ext}")
    allr[k] = {"track": t, "model": g.model, **{x: res[t][x] for x in ("ssim_place", "ssim_color", "blur", "cover", "frames")},
               "other": res.get(1 - t, {}).get("ssim_color")}
    json.dump(allr, open(ap_, "w"), indent=1)
    print(k, "追う" if t else "追わん", res[t]["ssim_color"], "（もう片方", allr[k]["other"], "）", flush=True)

"""特定できたカットの元を 1080p で、要る所（前後3秒）だけ落とし、もう一度当てる。

python3 hires.py <作業フォルダ> [--only 17,63] [--found a.json b.json …]
- 当たりの線＝inliers 25以上・ssim 0.5以上（360p の段）
- 落とす＝src/hi/<番号>.mp4（--download-sections ＋ --force-keyframes-at-cuts で切り目の秒を正確に）
- 結果＝src/hi.json：{番号: {id, start（元の動画の秒）, flip, ssim, ssim_360, inliers, H}}
"""
import argparse, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PAD = 3.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--only"); ap.add_argument("--found", nargs="*")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    shots = {s["i"]: s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"]}
    best = {}
    for p in g.found or glob.glob(f"{g.w}/src/found*.json"):
        for k, v in json.load(open(p)).items():
            if v.get("found") and v["inliers"] >= 25 and v["ssim"] >= 0.5 and (k not in best or v["ssim"] > best[k]["ssim"]):
                best[k] = v
    only = set(g.only.split(",")) if g.only else None
    hd = f"{g.w}/src/hi"; os.makedirs(hd, exist_ok=True)
    op = f"{g.w}/src/hi.json"
    out = json.load(open(op)) if os.path.exists(op) else {}
    for k in sorted(best, key=int):
        if (only and k not in only) or k in out:
            continue
        v, s = best[k], shots[int(k)]
        dur = float(s["t1"]) - float(s["t0"])
        a = max(0.0, v["start"] - PAD)
        b = v["start"] + dur + PAD
        f = f"{hd}/{k}.mp4"
        if not os.path.exists(f):
            time.sleep(float(os.environ.get("YT_SLEEP", "0")))
            subprocess.run(["yt-dlp"] + (["--cookies-from-browser", os.environ["YT_COOKIES"]] if os.environ.get("YT_COOKIES") else []) + ["-q", "--no-warnings", "-f", "bv*[height<=1080][ext=mp4][protocol^=http]/bv*[height<=1080][protocol^=http]/bv*[height<=1080]",
                            "--download-sections", f"*{a:.3f}-{b:.3f}", "--force-keyframes-at-cuts",
                            "--downloader-args", "ffmpeg_i:-ca_file /etc/ssl/cert.pem",
                            "-o", f, "--remux-video", "mp4", v["url"]], capture_output=True)
        if not os.path.exists(f):
            print(k, "落とせんかった", flush=True)
            continue
        r = subprocess.run([sys.executable, f"{HERE}/match.py", ref, str(s["t0"]), str(s["t1"]), f,
                            "--out", f"{hd}/{k}.json"], capture_output=True, text=True)
        try:
            res = json.load(open(f"{hd}/{k}.json"))
        except Exception:
            print(k, "当たらんかった", r.stderr[-200:], flush=True)
            continue
        if not res.get("found"):
            print(k, "1080p では当たらんかった", flush=True)
            continue
        h = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height",
                            "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip()
        out[k] = {"id": v["id"], "url": v["url"], "start": round(a + res["start"], 4), "flip": res["flip"],
                  "ssim": res["ssim"], "ssim_360": v["ssim"], "inliers": res["inliers"], "H": res["H"],
                  "height": h, "file": f, "clip_start": round(a, 3)}
        json.dump(out, open(op, "w"), indent=1)
        print(k, f"{h}p", "ssim", v["ssim"], "→", res["ssim"], "start", out[k]["start"], flush=True)


if __name__ == "__main__":
    main()

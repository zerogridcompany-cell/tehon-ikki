"""Codex の目（eye/out.json）の検索語で YouTube から元の映像を探し、match.py で当てる。

python3 find_sources.py <作業フォルダ>  [--only 3,4,5] [--per 4] [--maxdur 1500] [--part 0/2] [--keep-best] [--extra ids.json]
- --part k/n：カットを n 台で分ける（i % n == k の物だけ）
- --keep-best：当たりに使わん候補の動画は当てた後に消す（空きが少ない機械用）
- --extra：{カット番号: [youtubeのid…]} を検索より先に試す（係が見つけた候補）
- 作業フォルダ/ref/*.mp4・eye/out.json を読む
- 候補は src/cand/<youtubeのid>.mp4（360p・音なし）に落とす（同じ id は1回だけ）
- 結果＝src/found.json（カット番号 → {id, url, start, flip, ssim}）。見つからん物は理由つき
"""
import argparse, glob, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def yt_search(q, n):
    p = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{n}:{q}"], capture_output=True, text=True)
    out = []
    for line in p.stdout.splitlines():
        try:
            d = json.loads(line)
            out.append({"id": d["id"], "title": d.get("title"), "dur": d.get("duration") or 0})
        except Exception:
            pass
    return out


SLEEP = float(os.environ.get("YT_SLEEP", "0"))


def fetch(vid, cdir):
    f = f"{cdir}/{vid}.mp4"
    if os.path.exists(f):
        return f
    time.sleep(SLEEP)  # 落とす間を空ける（10/25 Air も mini も「ロボットか確かめる」で止められた）
    subprocess.run(["yt-dlp"] + (["--cookies-from-browser", os.environ["YT_COOKIES"]] if os.environ.get("YT_COOKIES") else []) + ["-q", "--no-warnings", "-f", "bv*[height<=360][ext=mp4]/bv*[height<=480]/b[height<=480]",
                    "-o", f, "--remux-video", "mp4", f"https://www.youtube.com/watch?v={vid}"], capture_output=True)
    return f if os.path.exists(f) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--only"); ap.add_argument("--per", type=int, default=4)
    ap.add_argument("--maxdur", type=int, default=1500)
    ap.add_argument("--part"); ap.add_argument("--keep-best", action="store_true"); ap.add_argument("--extra"); ap.add_argument("--found"); ap.add_argument("--cand")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    eye = json.load(open(f"{g.w}/eye/out.json"))
    cdir = g.cand or f"{g.w}/src/cand"; os.makedirs(cdir, exist_ok=True)
    fp = g.found or f"{g.w}/src/found.json"
    found = json.load(open(fp)) if os.path.exists(fp) else {}
    only = {int(x) for x in g.only.split(",")} if g.only else None
    extra = json.load(open(g.extra)) if g.extra else {}
    pk, pn = map(int, g.part.split("/")) if g.part else (0, 1)
    for s in eye["shots"]:
        i = s["i"]
        if i % pn != pk or (only and i not in only) or s.get("kind") in ("mg", "text_only") or found.get(str(i), {}).get("ssim", 0) >= 0.8:
            continue
        # 前のカットと同じ元なら、その元を先に試す
        first = []
        if s.get("same_as") is not None and str(s["same_as"]) in found and found[str(s["same_as"])].get("found"):
            first = [found[str(s["same_as"])]["id"]]
        cands = [{"id": x} for x in first + extra.get(str(i), [])]
        for q in (s.get("search") or [])[:3]:
            if q and q != "?":
                cands += [c for c in yt_search(q, g.per) if c["dur"] <= g.maxdur]
        seen, best = set(), None
        for c in cands:
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            f = fetch(c["id"], cdir)
            if not f:
                continue
            r = subprocess.run([sys.executable, f"{HERE}/match.py", ref, str(s["t0"]), str(s["t1"]), f,
                                "--out", f"{g.w}/src/m_{i}_{c['id']}.json"], capture_output=True, text=True)
            try:
                res = json.loads(r.stdout.strip().splitlines()[-1])
            except Exception:
                continue
            res.update({"id": c["id"], "url": f"https://www.youtube.com/watch?v={c['id']}"})
            if res.get("found") and res["ssim"] >= 0.5 and (best is None or res["ssim"] > best["ssim"]):
                best = res
            if best and best["ssim"] >= 0.8:
                break
        keep = {v.get("id") for v in found.values()} | {best and best["id"]}
        for x in seen - keep:
            # 目印の保存は当たりに使わん動画なら毎回消す（1時間の動画で数GBになった・10/25 mini が満杯で落ちた）
            for f in glob.glob(f"{cdir}/{x}.mp4.sift*.pkl") + ([f"{cdir}/{x}.mp4"] if g.keep_best else []):
                try:
                    os.remove(f)
                except FileNotFoundError:
                    pass
        old = found.get(str(i), {})
        if not best or old.get("ssim", 0) > best["ssim"]:
            best = old if old.get("found") else None
        found[str(i)] = best or {"found": False, "tried": list(seen)}
        json.dump(found, open(fp, "w"), indent=1, ensure_ascii=False)
        print(i, json.dumps(found[str(i)], ensure_ascii=False)[:200], flush=True)


if __name__ == "__main__":
    main()

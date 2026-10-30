"""img_search.py の結果を確かめる：出てきた画像を落とし、手本のコマと目印（SIFT）が合うかを数える。

python3 img_verify.py <作業フォルダ> [--only 8,126] [--top 15]
- 画像は shirabe/img/<番号>/ に落とす（大きい物から最大 top 枚）
- 結果を shirabe/img/<番号>.json に足す：best（一番合う画像・inliers）・yt（出てきた YouTube の id）
- shirabe/img_yt.json＝{番号: [youtubeのid…]}（find_sources.py --extra にそのまま渡せる）
"""
import argparse, glob, json, os, re, subprocess
import cv2
import numpy as np

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
sift = cv2.SIFT_create(2000)
bf = cv2.BFMatcher()
YT = re.compile(r"(?:ytimg\.com/vi/|youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})")


def gray(path, w=640):
    im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    return cv2.resize(im, (w, int(im.shape[0] * w / im.shape[1])))


def inliers(a, b):
    ka, da = sift.detectAndCompute(a, None)
    kb, db = sift.detectAndCompute(b, None)
    if da is None or db is None or len(ka) < 8 or len(kb) < 8:
        return 0
    m = [x for x, y in (p for p in bf.knnMatch(da, db, k=2) if len(p) == 2) if x.distance < 0.75 * y.distance]
    if len(m) < 8:
        return 0
    H, inl = cv2.findHomography(np.float32([ka[x.queryIdx].pt for x in m]), np.float32([kb[x.trainIdx].pt for x in m]),
                                cv2.RANSAC, 5.0)
    return int(inl.sum()) if inl is not None else 0


def area(s):
    try:
        w, h = s.split("×")
        return int(w) * int(h)
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--only"); ap.add_argument("--top", type=int, default=15)
    g = ap.parse_args()
    od = f"{g.w}/shirabe/img"
    ytp = f"{g.w}/shirabe/img_yt.json"
    allyt = json.load(open(ytp)) if os.path.exists(ytp) else {}
    files = [f"{od}/{i}.json" for i in g.only.split(",")] if g.only else sorted(glob.glob(f"{od}/*.json"))
    for jp in files:
        d = json.load(open(jp))
        i = d["i"]
        ref = gray(f"{od}/{i}.png")
        yt = []
        for s in d["sites"]:
            for u in (s.get("img") or "", s.get("page") or ""):
                yt += [x for x in YT.findall(u) if x not in yt]
        seen, scored = set(), []
        for s in sorted(d["sites"], key=lambda s: -area(s.get("size"))):
            u = s.get("img")
            if not u or u in seen or len(seen) >= g.top:
                continue
            seen.add(u)
            os.makedirs(f"{od}/{i}", exist_ok=True)
            f = f"{od}/{i}/{len(seen):02d}.img"
            subprocess.run(["curl", "-s", "-L", "-m", "30", "-A", UA, "-o", f, u])
            im = gray(f) if os.path.exists(f) else None
            n = inliers(im, ref) if im is not None and ref is not None else 0
            scored.append({"img": u, "page": s.get("page"), "title": s.get("title"), "size": s.get("size"), "file": f, "inliers": n})
        scored.sort(key=lambda x: -x["inliers"])
        d["checked"] = scored
        d["best"] = scored[0] if scored and scored[0]["inliers"] >= 20 else None
        d["yt"] = yt
        json.dump(d, open(jp, "w"), indent=1, ensure_ascii=False)
        if yt:
            allyt[str(i)] = yt[:5]
        b = d["best"]
        print(i, "best:", b and (b["inliers"], b["size"], b["img"][:80]), "| yt:", yt[:5], flush=True)
    json.dump(allyt, open(ytp, "w"), indent=1)


if __name__ == "__main__":
    main()

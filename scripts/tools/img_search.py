"""手本のカットの1コマで Yandex の画像検索をかけ、同じ絵が載っとるサイトと元の画像を集める。

python3 img_search.py <作業フォルダ> [--only 4,5] [--todo shirabe/img_todo.json]
- 1コマ＝カットの真ん中を手本の元の大きさで切る（ref/*.mp4・eye/out.json の t0〜t1）
- 結果＝shirabe/img/<番号>.json（sites：題名・ページ・画像の URL・大きさ）と <番号>.png（送った絵）
- 1枚ごとに 6秒あける（止められん様に）。止められたら（captcha）そこで止まって報告
"""
import argparse, glob, html, json, os, re, subprocess, sys, time

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
UP = ("https://yandex.com/images/search?rpt=imageview&format=json&request="
      "%7B%22blocks%22%3A%5B%7B%22block%22%3A%22b-page_type_search-by-image__link%22%7D%5D%7D")


def curl(args):
    return subprocess.run(["curl", "-s", "-m", "60", "-A", UA] + args, capture_output=True, text=True).stdout


def sites(page):
    t = html.unescape(page)
    out = []
    for item in t.split('class="CbirSites-Item"')[1:]:
        img = re.search(r'CbirSites-ItemThumb.*?href="([^"]+)"', item, re.S)
        size = re.search(r'Thumb-Mark[^>]*>(\d+×\d+)<', item)
        ttl = re.search(r'CbirSites-ItemTitle"><a href="([^"]+)"[^>]*>([^<]*)<', item)
        dom = re.search(r'CbirSites-ItemDomain[^>]*>([^<]*)<', item)
        if ttl:
            out.append({"title": ttl.group(2)[:200], "page": ttl.group(1), "img": img and img.group(1),
                        "size": size and size.group(1), "domain": dom and dom.group(1)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--only"); ap.add_argument("--todo", default="shirabe/img_todo.json")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    shots = {s["i"]: s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"]}
    todo = [int(x) for x in g.only.split(",")] if g.only else json.load(open(f"{g.w}/{g.todo}"))
    od = f"{g.w}/shirabe/img"; os.makedirs(od, exist_ok=True)
    for i in todo:
        jp = f"{od}/{i}.json"
        if os.path.exists(jp):
            continue
        s = shots[i]
        t = (float(s["t0"]) + float(s["t1"])) / 2
        png = f"{od}/{i}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", ref, "-frames:v", "1", png])
        cb = None
        for k in range(6):  # 止められたら 1分・2分…と休んでやり直す
            r = curl(["-F", f"upfile=@{png}", UP])
            try:
                cb = json.loads(r)["blocks"][0]["params"]["cbirId"]
                break
            except Exception:
                print(i, f"送れんかった（{k + 1}回目）・{60 * (k + 1)}秒休む:", r[:80], flush=True)
                time.sleep(60 * (k + 1))
        if not cb:
            sys.exit(2)
        page = curl([f"https://yandex.com/images/search?cbir_id={cb}&rpt=imageview&cbir_page=sites"])
        if "captcha" in page.lower() and "CbirSites" not in page:
            print(i, "captcha で止められた", flush=True)
            sys.exit(3)
        res = {"i": i, "t": round(t, 3), "cbir": cb, "sites": sites(page)}
        json.dump(res, open(jp, "w"), indent=1, ensure_ascii=False)
        print(i, len(res["sites"]), "|", " / ".join(x["title"][:50] for x in res["sites"][:3]), flush=True)
        time.sleep(12)


if __name__ == "__main__":
    main()

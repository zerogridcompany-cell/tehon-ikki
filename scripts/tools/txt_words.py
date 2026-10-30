"""声の文（words.txt）の1語ずつに、手本の画面で「出るコマ」「消えるコマ」「箱」を当てる。

python3 txt_words.py <作業フォルダ>
- 入れる物：txt/words.txt（字幕の文・1行1句。表示どおりの綴り・記号）・txt/b/*.png（txt_events.py が作る帯の絵）の読み取り結果 txt/ocr_band.json
- 当て方：1語ずつ順に、前の語より後のコマで、読み取りの語と似とる（0.72以上）最初のコマ＝出る。続けて見えとる最後のコマ＝消える（3コマまでの抜けはつなぐ）
- 読めんかった語は前後の語の間に置く（"guess": true）
- 出す物：txt/words.json＝[{w, line, f0, f1, box, guess}]
"""
import argparse, difflib, json, os, re

ap = argparse.ArgumentParser(); ap.add_argument("w")
g = ap.parse_args()
ocr = {int(k): v for k, v in json.load(open(f"{g.w}/txt/ocr_band.json")).items()}
n = max(ocr) + 1 if ocr else 0
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
toks = {f: [(norm(t), b) for t, b in v] for f, v in ocr.items()}
lines = [l.strip() for l in open(f"{g.w}/txt/words.txt") if l.strip()]
W = []
for li, l in enumerate(lines):
    for w in l.split():
        W.append({"w": w, "line": li})


def seen(word, f):
    k = norm(word)
    if not k:
        return None
    for t, b in toks.get(f, []):
        if t == k or (len(k) >= 3 and (k in t)) or (len(t) >= 3 and len(k) >= 4 and k.startswith(t)) or difflib.SequenceMatcher(None, k, t).ratio() >= 0.72:
            return b
    return None


f = 0
for x in W:
    hit = None
    win = 45 if len(norm(x["w"])) <= 2 else 240  # 短い語（a・I・to）は遠くの別の語に当たりやすい＝1.5秒以内だけ
    for j in range(f, min(n, f + win)):  # 次の語は8秒以内に出る
        b = seen(x["w"], j)
        if b:
            hit = (j, b); break
    if not hit:
        x["f0"] = None; continue
    x["f0"], x["box"] = hit
    last, miss = hit[0], 0
    for j in range(hit[0] + 1, n):
        if seen(x["w"], j):
            last, miss = j, 0
        else:
            miss += 1
            if miss > 3:
                break
    x["f1"] = last
    f = hit[0]
# 読めんかった語：前後の間（短い語＝a・I・to 等は読み取りが落としやすいので置く。4字以上で一度も読めん語は字幕に無い物として外す）
W = [x for x in W if x.get("f0") is not None or len(norm(x["w"])) <= 3]
for i, x in enumerate(W):
    if x.get("f0") is None:
        a = next((W[j] for j in range(i - 1, -1, -1) if W[j].get("f0") is not None), None)
        b = next((W[j] for j in range(i + 1, len(W)) if W[j].get("f0") is not None), None)
        x["f0"] = (a["f0"] + 1) if a else 0
        x["f1"] = b["f1"] if b and b["line"] == x["line"] else (a["f1"] if a else x["f0"] + 10)
        x["guess"] = True
json.dump(W, open(f"{g.w}/txt/words.json", "w"), indent=1, ensure_ascii=False)
ok = sum(1 for x in W if not x.get("guess"))
print(f"{len(W)} 語・画面で当たった {ok}・当て推量 {len(W) - ok}")
for x in W[:40]:
    print(x["line"], x["w"], x["f0"], x["f1"], "?" if x.get("guess") else "")

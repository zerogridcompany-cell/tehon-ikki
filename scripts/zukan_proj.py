"""段0 の図鑑（zukan.json）から、作る段の最初の部品を書く（10/30 つなぎ）。手本は測り直さん。

python3 zukan_proj.py <作業> [--force]
- proj/src/caps.json …… 字幕の1語ずつ（出る/消えるコマ・箱・大きさ・書体の見当）。前の caps.json があれば触らん（--force で上書き・控え caps.json.bak_zukan）
  - 字幕と「絵の中の字」（背番号・看板・ロゴ）を分ける：声の語と ±1.5秒で同じ語、か、辞書の語・全部大文字でない・高さ 3% 以上・3回以上読めた語＝字幕
  - 落ちた語は proj/src/e_no_moji.json（絵の中の字＝作る時は実写や一枚絵に焼けとる物）
- proj/src/cfg.json …… frames・fps・width・height（図鑑の meta）
- zukan/tsunagi.md …… 何を書いたか・字幕に入れた/外した語の数
"""
import argparse, json, os, re, shutil

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
w = os.path.abspath(a.w); Z = json.load(open(f"{w}/zukan/zukan.json")); M = Z["meta"]
os.makedirs(f"{w}/proj/src", exist_ok=True)
_r = M.get("r_frame_rate", ""); FPS = (float(_r.split("/")[0]) / float(_r.split("/")[1])) if "/" in _r and float(_r.split("/")[1]) else float(M["fps"])   # Remotion の fps＝r_frame_rate（pts の 30.0003 は使わん）
json.dump({"frames": M["frames"], "fps": FPS, "width": M["W"], "height": M["H"]}, open(f"{w}/proj/src/cfg.json", "w"))

norm = lambda s: re.sub(r"[^a-z0-9']", "", s.lower()).strip("'")
def near(x, y):   # 1字違いまで同じ語（OCR の読み違い：retter↔better）
    if x == y: return True
    if min(len(x), len(y)) < 4 or abs(len(x) - len(y)) > 1: return False
    if len(x) == len(y): return sum(p != q for p, q in zip(x, y)) <= 1
    s, l = sorted((x, y), key=len); return any(l[:i] + l[i + 1:] == s for i in range(len(l)))

_kw = Z["oto"].get("koe_words", [])   # 声が無い手本は {"v":"なし",…}（11/02 tehonU 10秒で落ちとった）
koe = [dict(n=norm(k["w"]), t=k["t0"]) for k in (_kw if isinstance(_kw, list) else []) if norm(k["w"])]
DICT = set()
if os.path.exists("/usr/share/dict/words"): DICT = {l.strip().lower() for l in open("/usr/share/dict/words")}
caps, drop = [], []
_mw = (Z.get("moji") or {}).get("words", []) if isinstance(Z.get("moji"), dict) else []
for x in (_mw if isinstance(_mw, list) else []):
    n = norm(x["w"]); t0 = x["t0"]
    koe_ok = bool(koe) and bool(n) and any(near(n, k["n"]) and abs(k["t"] - t0) <= 1.5 for k in koe)
    # 字幕は声どおりとは限らん（tehonU：声 doesn't matter／字 not matter・声 question／字 quest）＝辞書の語で・大文字だけでなく・大きく・3回以上読めた物も字幕
    word = n in DICT or re.fullmatch(r"(n't|'s|'re|'ll|'ve|'m|'d)", x["w"].strip("•·. ").lower()) or (n.endswith("s") and n[:-1] in DICT)
    look_ok = bool(n) and bool(word) and not (x["w"].isupper() and len(x["w"]) > 2) and x["moji_takasa_pct"] >= 3 and (x.get("kenshutsu") or 0) >= 3
    ok = koe_ok or look_ok
    why = "声と同じ語" if koe_ok else ("字幕らしい（辞書の語・大きい・3回以上）" if look_ok else "絵の中の字（大文字・辞書に無い・小さい・1〜2回だけ）")
    (caps if ok else drop).append((x, why))

fg = lambda s: "serif" if "斜体" in s else ("plain" if "明朝" in s else "sans")   # r2 の look.json：serif＝斜体のセリフ・plain＝立ったセリフ・sans＝ゴシック
out = []
for i, (x, _) in enumerate(sorted(caps, key=lambda p: (p[0]["f0"], p[0]["box_px"][0]))):
    b = x["box_px"]; h = b[3] - b[1]
    out.append(dict(i=i, w=x["w"], f0=x["f0"], f1=x["f1"], kind=fg(x.get("font_guess", "")), fs=round(h * 1.25, 2), x=float(b[0]), y=float(b[3]), sx=1.0,
                    box=b, color=x.get("color"), stroke=x.get("stroke"), glow=x.get("glow"), slant=x.get("slant_deg"), guess=True, src="zukan"))
p = f"{w}/proj/src/caps.json"
if os.path.exists(p) and not a.force and json.load(open(p)):
    print("🟡 caps.json はもうある＝触らん（--force で図鑑から上書き）")
else:
    if os.path.exists(p): shutil.copy(p, p + ".bak_zukan")
    json.dump(out, open(p, "w"), ensure_ascii=False)
json.dump([dict(w=x["w"], f0=x["f0"], f1=x["f1"], box=x["box_px"], why=why) for x, why in drop], open(f"{w}/proj/src/e_no_moji.json", "w"), ensure_ascii=False)
msg = f"字幕 {len(out)} 語（声と同じ {sum(1 for x,y in caps if y=='声と同じ語')}・字幕らしい {sum(1 for x,y in caps if y!='声と同じ語')}）・絵の中の字 {len(drop)} 語＝e_no_moji.json・カット {len(Z['cuts'])}・{M['W']}x{M['H']} {FPS:g}fps"
open(f"{w}/zukan/tsunagi.md", "w").write("# 図鑑→作る段（zukan_proj.py）\n- " + msg + "\n- 書体の見当は fs＝インクの高さ×1.25・x,y＝箱の左下。cap_fit／cap_time で型合わせしてから使う\n")
print(msg)

"""段0 見るの門：図鑑（zukan.json）の升が1つでも空なら🔴。「なし」は根拠の数字が付いとる時だけ通す。
python3 check_zukan.py <作業>   → 赤があれば exit 1
- 升＝カットごとの kirikae・awase・kamera・ugoki・seishi・iro・tsubu・surudosa・boke・kumi・shuushuu・fuchi・kao・e_hani・shuyaku・moji・mg・oto
- 全体＝meta（fps・コマ数）・oto（lufs・kyoku・koe_words・sfx・kick）・kimari
- 空＝None・""・[]・{}。「なし」＝{"v":"なし","konkyo":"…数字…"} の形で konkyo に数字がある時だけ OK
- カットのコマがすき間なく 0〜最後まで並んどるか（f1＝次の f0）も見る
"""
import json, os, re, sys
W_ = os.path.abspath(sys.argv[1]); p = f"{W_}/zukan/zukan.json"
if not os.path.exists(p): print("🔴 zukan.json が無い＝run.sh miru を先に"); sys.exit(1)
zk = json.load(open(p)); red = []; ok = []; yel = []
KEYS = ["kirikae", "awase", "kamera", "ugoki", "seishi", "iro", "tsubu", "surudosa", "boke", "kumi", "shuushuu", "fuchi", "kao", "e_hani", "shuyaku", "moji", "mg", "oto"]


def empty(v):
    return v is None or v == "" or (isinstance(v, (list, dict)) and len(v) == 0)


def walk(v, path, out):
    if isinstance(v, dict):
        if v.get("v") == "なし":
            if v.get("tobashita"):   # 🆕11/02 道具が無くて測ってない（doctor の🟡）＝赤にせん・黄で数える
                yel.append(f"{path}＝{v.get('konkyo')}"); return
            if not re.search(r"\d", str(v.get("konkyo", ""))): out.append(f"{path}＝「なし」なのに根拠の数字が無い")
            return
        for k, x in v.items():
            if k in ("kukan_kimari", "stroke", "shadow", "fuchidori", "kage", "konkyo", "note", "skew", "at0", "key", "fumei"):   # 無い事そのものが値の欄
                continue
            if empty(x) and not isinstance(x, (int, float)): out.append(f"{path}.{k} が空")
            else: walk(x, f"{path}.{k}", out)
    elif isinstance(v, list):
        for j, x in enumerate(v[:200]):
            if x is None and "chikai" not in path: out.append(f"{path}[{j}] が空")


M = zk.get("meta", {})
for k in ("fps", "frames", "W", "H", "dur"):
    if empty(M.get(k)): red.append(f"meta.{k} が空")
C = zk.get("cuts", [])
if not C: red.append("カットが0")
prev = 0
for r in C:
    if r["f0"] != prev: red.append(f"#{r['i']} のコマが続いとらん（{prev}→{r['f0']}）")
    prev = r["f1"]
    for k in KEYS:
        if k not in r or empty(r[k]): red.append(f"#{r['i']}.{k} が空"); continue
        walk(r[k], f"#{r['i']}.{k}", red)
if C and prev != M.get("frames"): red.append(f"最後のカットの終わり {prev} が手本のコマ数 {M.get('frames')} と違う")
O = zk.get("oto")
if empty(O): red.append("oto（音）が空＝--no-oto で回した")
else:
    for k in ("lufs", "kyoku", "koe_words", "sfx", "kick"):
        if empty(O.get(k)): red.append(f"oto.{k} が空")
        else: walk(O[k], f"oto.{k}", red)
    for s in O.get("kyoku", []):
        if not s.get("beats"): red.append(f"曲の区間 {s['a']}〜{s['b']}秒に拍の網が無い")
if empty(zk.get("kimari")): red.append("区間の決まり（kimari）が空")
ok.append(f"カット {len(C)}・升 {len(C) * len(KEYS)}")
for x in ok: print("✅", x)
if yel:
    import collections
    for k, n in collections.Counter(re.sub(r"^#\d+\.", "", y) for y in yel).items(): print("🟡", f"{k}（{n}か所・道具が無くて測ってない＝作る段は進む）")
for x in red[:60]: print("🔴", x)
if len(red) > 60: print(f"🔴 ほか {len(red) - 60}")
print("門", "OK" if not red else f"止める（赤 {len(red)}）"); sys.exit(1 if red else 0)

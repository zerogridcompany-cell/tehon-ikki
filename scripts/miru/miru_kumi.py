"""段0 見る：部品（parts/*.json）を1枚の図鑑 zukan.json に組む＋カットの頭が何に合わせとるか（awase）。
python3 miru_kumi.py <作業>
- 物差し＝小節の頭・1拍・半拍・4分の1拍（区間の拍の網から）・言葉の頭（whisper）・効果音（hako）・強い低音（30〜150Hz）
- カットごと：2コマ以内に来る物差しを全部と、ずれ（コマ・＋＝物差しが後）。合わせ先＝区間の決まり（kouzou.py と同じ：たまたま＝ずらし100回の1.5倍以上・当たり30%以上）に当たればそれ、無ければ優先の順（小節の頭→1拍→言葉の頭→効果音→強い低音→半拍→4分の1拍）
"""
import json, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
W_ = os.path.abspath(sys.argv[1]); Z = f"{W_}/zukan"; P = f"{Z}/parts"
L = lambda n: json.load(open(f"{P}/{n}.json")) if os.path.exists(f"{P}/{n}.json") else None
kihon, cuts, ug, kk, mk_, moji, mg, oto = L("kihon"), L("cuts"), L("ugoki"), L("kirikae"), L("mikake"), L("moji"), L("mg"), L("oto")
FPS = kihon["fps"]; TOL = 2.0 / FPS
UG = {u["i"]: u for u in ug}; KK = {k["i"]: k for k in kk["cuts"]}; MK = {m["i"]: m for m in mk_}
isn = lambda v: isinstance(v, dict) and v.get("v") == "なし"
words = [] if (oto is None or isn(oto.get("koe_words"))) else oto["koe_words"]
sfx = [] if oto is None else oto.get("sfx", [])
kicks = [] if (oto is None or isn(oto.get("kick"))) else oto["kick"]
secs = [] if oto is None else oto.get("kyoku", [])


def grids_for(t):
    s = next((x for x in secs if x["a"] <= t < x["b"]), secs[-1] if secs else None)
    if not s or not s.get("beats"): bt = np.array([]); bars = np.array([])
    else: bt = np.array(s["beats"]); bars = np.array(s["bars"])
    half = np.sort(np.concatenate([bt, (bt[:-1] + bt[1:]) / 2])) if len(bt) > 1 else bt
    q = np.sort(np.concatenate([half, (half[:-1] + half[1:]) / 2])) if len(half) > 1 else half
    return s, {"小節の頭": bars, "1拍": bt, "半拍": half, "4分の1拍": q,
               "言葉の頭": np.array([w["t0"] for w in words]), "効果音": np.array([x["t"] for x in sfx if x.get("hako") in (3, 4) and (x.get("db") or -99) > -46]), "強い低音": np.array([x["t"] for x in kicks])}


# 効果音の物差し＝kouzou.py と同じ（hako 3・4＝曲っぽい・編集の効果音・-46dB 超）
PRI = ["小節の頭", "1拍", "言葉の頭", "効果音", "強い低音", "半拍", "4分の1拍"]
# 区間ごとの決まり（kouzou.py と同じ計算）
rng = np.random.default_rng(0); kimari = []
def hit(ts, g):
    if len(g) == 0 or len(ts) == 0: return 0.0
    g = np.sort(np.asarray(g)); return float(np.mean([np.min(np.abs(g - t)) <= TOL for t in ts]))
for s in secs:
    ts = [c["t0"] for c in cuts if s["a"] <= c["t0"] < s["b"] and c["f0"] > 0]
    _, gr = grids_for((s["a"] + s["b"]) / 2)
    res = {}
    if len(ts) >= 3:
        for k, g in gr.items():
            gg = [x for x in g if s["a"] - 1 <= x <= s["b"] + 1]
            obs = hit(ts, gg); base = float(np.mean([hit([(t - s["a"] + rng.uniform(0, s["b"] - s["a"])) % (s["b"] - s["a"]) + s["a"] for t in ts], gg) for _ in range(100)]))
            res[k] = dict(hit=round(obs, 3), guuzen=round(base, 3), bai=round(obs / max(base, 1e-3), 2))
        good = {k: v for k, v in res.items() if v["bai"] >= 1.5 and v["hit"] >= 0.3}
        pick = max(good, key=lambda k: good[k]["hit"] - good[k]["guuzen"]) if good else "なし"
    else: pick = "なし"
    kimari.append(dict(name=s["name"], a=s["a"], b=s["b"], bpm=s.get("bpm"), n_cuts=len(ts), res=res, pick=pick,
                       konkyo=("たまたまの1.5倍以上・当たり30%以上の物差しが無い" if pick == "なし" else f"{res[pick]['hit']:.0%}（偶然{res[pick]['guuzen']:.0%}）") if len(ts) >= 3 else f"カット {len(ts)} 本（3本未満は決めん）"))
KM = {(x["a"], x["b"]): x for x in kimari}

rows = []
words_m = moji["words"] if moji else []
for c in cuts:
    i, f0, f1, t0, t1 = c["i"], c["f0"], c["f1"], c["t0"], c["t1"]
    r = dict(i=i, f0=f0, f1=f1, n=c["n"], t0=t0, t1=t1, sec=round(t1 - t0, 3), gate_cut=c["gate"], kenshutsu=c["src"])
    r["kirikae"] = {k: v for k, v in KK[i].items() if k != "i"}
    # awase
    if f0 == 0: r["awase"] = dict(v="頭", konkyo="動画の1コマ目")
    elif not secs: r["awase"] = dict(v="なし", konkyo="音を測っとらん（--no-oto）")
    else:
        s, gr = grids_for(t0); near = {}; hits = []
        for k in PRI:
            g = gr[k]
            if len(g) == 0: near[k] = None; continue
            j = int(np.argmin(np.abs(g - t0))); d = int(round((g[j] - t0) * FPS)); near[k] = d
            if abs(g[j] - t0) <= TOL: hits.append(k)
        rule = KM.get((s["a"], s["b"]), {}).get("pick") if s else None
        if hits:
            v = rule if rule in hits else hits[0]
            near = {k: x for k, x in near.items() if x is not None}
            r["awase"] = dict(v=v, zure_koma=near[v], ataru=hits, chikai=near, kukan_kimari=rule)
        else:
            near = {k: x for k, x in near.items() if x is not None}
            nk = min((k for k in PRI if near.get(k) is not None), key=lambda k: abs(near[k]), default=None)
            r["awase"] = dict(v="なし", konkyo=f"2コマ以内に物差し0（一番近い {nk} {near.get(nk):+d}コマ）" if nk else "物差しが無い", chikai=near, kukan_kimari=rule)
    u = UG[i]; r["ugoki"] = u["ugoki"]; r["seishi"] = u["seishi"]; r["kamera"] = {k: v for k, v in u["kamera"].items() if k not in ("dx_px", "dy_px", "s")}
    m = MK.get(i, {})
    for k in ("iro", "tsubu", "surudosa", "boke", "kumi", "shuushuu", "fuchi", "kao", "e_hani", "shuyaku"):
        r[k] = m.get(k)
    # 字
    if moji is None: r["moji"] = dict(v="なし", konkyo="字を測っとらん（--no-moji）")
    else:
        ws = [w for w in words_m if w["f0"] < f1 and w["f1"] >= f0]
        r["moji"] = [dict(w=w["w"], f0=w["f0"], f1=w["f1"], box_pct=w["box_pct"], takasa_pct=w["moji_takasa_pct"], color=w.get("color"),
                          fuchidori=w.get("stroke"), kage=w.get("shadow"), hikari=w.get("glow"), shotai=w.get("font_guess")) for w in ws] or \
            dict(v="なし", konkyo=f"Vision で {moji['step']}コマおきに読んで、このカット {f1 - f0}コマに字 0語")
    # 飾り
    mm = []
    for h in (mg or {}).get("hud", []):
        if h["f0"] < f1 and h["f1"] >= f0: mm.append(dict(kind=h["kind"], f0=h["f0"], f1=h["f1"], box_pct=h["box_pct"], ugoki_pct_s=h["ugoki_pct_s"]))
    for e in (mg or {}).get("per_cut", {}).get(str(i), []):
        mm.append({k: v for k, v in e.items() if k != "cut"})
    if m.get("kumi", {}).get("ari"): mm.append(dict(kind="網点", period_px=m["kumi"]["period_px"], power=m["kumi"]["power"]))
    r["mg"] = mm or dict(v="なし", konkyo=f"HUD の色 0コマ・四隅の動かん形 0・平らな札 0・網点の山 {m.get('kumi', {}).get('power')}（<40）")
    # 音
    if oto is None: r["oto"] = dict(v="なし", konkyo="音を測っとらん（--no-oto）")
    else:
        se = [dict(t=x["t"], koma=int(round((x["t"] - t0) * FPS)), kind=x["kind"], db=x["db"]) for x in sfx if t0 <= x["t"] < t1]
        kw = [dict(w=w["w"], t0=w["t0"], koma=int(round((w["t0"] - t0) * FPS))) for w in words if t0 <= w["t0"] < t1]
        kc = [dict(t=x["t"], koma=int(round((x["t"] - t0) * FPS)), s=x["s"]) for x in kicks if t0 <= x["t"] < t1]
        r["oto"] = dict(kouka=se or dict(v="なし", konkyo=f"効果音 0（hako の {len(sfx)} 個のうちこの {r['sec']}秒に無い）"),
                        koe=kw or dict(v="なし", konkyo=f"言葉の頭 0（whisper の {len(words)} 語のうちこの {r['sec']}秒に無い）"),
                        kick=kc or dict(v="なし", konkyo=f"強い低音 0（{len(kicks)} 個のうちこの {r['sec']}秒に無い）"))
    rows.append(r)

zk = dict(meta=dict(kihon, made_by="tehon-ikki 段0 見る（scripts/miru）", rule="作る段は zukan.json の数字だけを使う・測り直さん（差の検査は最後の門だけ）"),
          cuts=rows,
          oto=None if oto is None else dict(lufs=oto["lufs"], kyoku=[{k: v for k, v in s.items()} for s in secs], kyoku_kirikae=oto.get("kyoku_kirikae"),
                                             koe_kukan=oto.get("koe_kukan"), koe_shurui=oto.get("koe_shurui"), koe_words=oto.get("koe_words"), sfx=sfx, kick=oto.get("kick"), kikoekata=oto.get("kikoekata"),
                                             ongaku_hako=oto.get("ongaku_hako")),
          kimari=kimari, flash_frames=kk.get("flash_frames", []), moji=moji, mg=None if mg is None else {k: mg[k] for k in ("hud", "logo", "fuda", "rule")})
json.dump(zk, open(f"{Z}/zukan.json", "w"), ensure_ascii=False, indent=1)
print("図鑑", f"{Z}/zukan.json", "カット", len(rows))
subprocess.run([sys.executable, os.path.join(HERE, "miru_report.py"), W_], check=True)

"""shot_look（色・ぼかし）を「手本と同じ明るさ・濃さ・くっきり」に合わせ直す（10/28 r2：点の当て込み（回帰）は中身がずれとると傾きが縮んで絵を薄める＝61 は濃さ 0.36・93 は 0.12 で灰色の板になっとった）。
python3 look_moment.py <作業> [--ids 46,61] [--auto] [--write]
- 色＝色ごとに 平均と散らばり（標準偏差）をそろえる（moment）。傾き＝手本の散らばり÷うちの散らばり＝中身がずれても縮まん。ゲイン 0.7〜1.6
- ぼかし＝look 込みのエッジの強さが手本と同じになる強さ（0〜6 を探す）。手本がくっきりならぼかさん
- 比べるのはカットのファイル（look 込み・字幕の帯を外す）。一枚絵が半分以上覆うカットは飛ばす
- --auto＝今の look がゲイン 0.85 未満・1.5 超・ぼかし 2 超のカットだけ。前の shot_look は .bak_moment
"""
import argparse, glob, json, os, shutil, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retime import rd
import retime
from geo import geo, half
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--ids", default=""); ap.add_argument("--auto", action="store_true"); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
retime.use_geo(w); GG = geo(w); FPS = GG["FPS"]; MW, MH = half(w)
LP = f"{w}/proj/src/shot_look.json"; L = json.load(open(LP))
GR = json.load(open(f"{w}/proj/src/green.json")); OFF = json.load(open(f"{w}/proj/src/layer_off.json"))
RA = rd(glob.glob(f"{w}/ref/*.mp4")[0], w=MW, h=MH)
m = np.ones((MH, MW), bool); m[round(150 * MH / 360):round(210 * MH / 360)] = False  # 字幕の帯（r2 の行を高さの比で）


def cover(f0, f1):
    c = set()
    for v in GR.values():
        for f in range(max(f0, v["f0"]), min(f1, v["f1"] + 1)):
            if not any(o["f0"] <= f < o["f1"] and "green" in o["off"] for o in OFF): c.add(f)
    return len(c) / max(1, f1 - f0)


def edge(g):
    return float(np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))[m].mean())


def blur(x, b):
    return cv2.GaussianBlur(x, (0, 0), MW / GG["W"] * (b * b + 0.25) ** 0.5)  # Remotion の blur(px) は手本の画素基準＝半分の大きさでは半分・全体の look.json blur 0.5 も重ねる


ids = set(a.ids.split(",")) if a.ids else None
segs = {l.split(":")[0].strip(): tuple(map(float, l.split(":")[1].split("-"))) for l in open(f"{w}/eye/segs.txt") if ":" in l}
changed = []
for k, v in L.items():
    if ids and k not in ids: continue
    g0 = np.array(v.get("g", [1, 1, 1]), np.float32); o0 = np.array(v.get("o", [0, 0, 0]), np.float32); b0 = float(v.get("blur", 0))
    if a.auto and not (g0.mean() < 0.85 or g0.mean() > 1.5 or b0 > 2): continue
    if k not in segs or not os.path.exists(f"{w}/cuts/{k}.mp4"): continue
    f0 = round(segs[k][0] * FPS); n = v["f1"] - v["f0"] + 1; s = v["f0"] - f0
    if cover(v["f0"], v["f1"] + 1) > 0.5: print(k, "一枚絵が覆う＝飛ばす"); continue
    C = rd(f"{w}/cuts/{k}.mp4", w=MW, h=MH)[s:s + n]; R = RA[v["f0"]:v["f0"] + len(C)]
    if len(C) < 2: continue
    X = np.concatenate([c[m] for c in C]).astype(np.float32) / 255; Y = np.concatenate([r[m] for r in R]).astype(np.float32) / 255
    # 色は BGR の並び・shot_look は RGB の並び
    gx = np.array([Y[:, 2 - c].std() / max(X[:, 2 - c].std(), 1e-3) for c in range(3)]); gx = np.clip(gx, 0.7, 1.6)
    ox = np.array([Y[:, 2 - c].mean() - gx[c] * X[:, 2 - c].mean() for c in range(3)]); ox = np.clip(ox, -0.4, 0.6)
    post = lambda c: np.clip(c.astype(np.float32) / 255 * gx[::-1] + ox[::-1], 0, 1)
    er = np.mean([edge(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).astype(np.float32)) for r in R])
    best = None
    for b in (0, 0.7, 1, 1.5, 2, 2.5, 3, 4, 5, 6):
        eo = np.mean([edge(cv2.cvtColor((blur(post(c), b) * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)) for c in C[::max(1, len(C) // 4)]])
        d = abs(np.log(max(eo, 1e-3) / max(er, 1e-3)))
        if best is None or d < best[0]: best = (d, b, eo)
    from cut_score import ssim
    gg = lambda x: cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)
    old_post = lambda c: np.clip(c.astype(np.float32) / 255 * g0[::-1] + o0[::-1], 0, 1)
    ks = list(range(0, len(C), max(1, len(C) // 5)))
    s_old = np.mean([ssim(gg(R[i]), gg((blur(old_post(C[i]), b0) * 255).astype(np.uint8))) for i in ks])
    s_new = np.mean([ssim(gg(R[i]), gg((blur(post(C[i]), best[1]) * 255).astype(np.uint8))) for i in ks])
    print(f"{k} 濃さ {g0.mean():.2f}→{gx.mean():.2f} ぼかし {b0}→{best[1]} エッジ 手本 {er:.1f}・うち {best[2]:.1f} SSIM {s_old:.3f}→{s_new:.3f}", flush=True)
    if s_new < s_old - 0.01: print("  点が 0.01 より下がる＝書かん（中身がずれとる＝色やなく中身を直す）"); continue
    nv = dict(v); nv["g"] = [round(float(x), 4) for x in gx]; nv["o"] = [round(float(x), 4) for x in ox]
    if best[1] > 0: nv["blur"] = best[1]
    else: nv.pop("blur", None)
    L[k] = nv; changed.append(k)
if a.write and changed:
    if not os.path.exists(LP + ".bak_moment"): shutil.copy(LP, LP + ".bak_moment")
    json.dump(L, open(LP, "w"), ensure_ascii=False, indent=1); print("書いた", len(changed), "カット：", ",".join(changed))

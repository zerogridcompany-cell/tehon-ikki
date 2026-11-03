#!/usr/bin/env python3
"""mg-mane の「測る」：手本とうちを同じ物差しで並べる（tehonX/数値の照合.md と同じ項目）。

/usr/bin/python3 hakaru.py <手本.mp4> <うち.mp4> [--kukan "UI:0-142,入力欄:143-185,字の板:186-378"] [--md 出す.md] [--json 出す.json] [--ssim-step 1]

コマは手本の番号のまま、1対1で比べる（うちの fps・コマ数が違えば🔴で知らせる）。
 1 SSIM＝480 幅のグレーで毎コマ（平均・中央・下位10%・0.8 未満のコマ数）＝素材の一致＝参考（追わん）
 2 動きの波＝隣のコマとの差（480 幅グレーの差の平均）の形の相関。切り替えのコマは抜く
 3 滑らかさ＝動きの波の2階差の平均（ギザギザ）。うち÷手本の比。カメラの寄りをコマごとの測り値のまま使うと大きくなる
 4 動きの量＝隣のコマとの差の平均。うち÷手本の比
 5 切り替え＝2つの決まりで両方を測ってコマで比べる
     跳び＝差が前後2コマの一番大きい値の 1.8 倍超かつ 2.0 超
     板替え＝明るい画素（>60）の 8 割超が前のコマと重ならず・動きを許した相関 0.5 未満（tehon-ikki miru 11/2 と同じ決まり・暗い MG の板ごとの替わり）
 6 色＝コマごとの平均の色の差（Lab・L は 0〜100）中央・最大
 7 効果音の鳴り始め＝tehon-ikki の oto_ms.tachiagari（強さ 0.08 以上）を両方に→近い順に1対1で組む（±30ms・±60ms）
 8 音量＝ffmpeg ebur128 の I（LUFS）
区間＝既定は手本の切り替えで割る。--kukan で名前つきの区間（「名前:始め-終わり」をカンマで）にできる。
目安（tehonX v2 から決めた初めの線・手本を何本か写したら直す）＝下の J_* の数字。
"""
import argparse, json, os, re, subprocess, sys, tempfile, time, warnings
import numpy as np
import cv2

warnings.filterwarnings("ignore")
from skimage.metrics import structural_similarity as ssim_fn

TOOLS = os.path.expanduser("~/.claude/skills/tehon-ikki/scripts/tools")
SMALL = 480          # 絵の近さ・動き・色を測る横幅（数値の照合.md と同じ）
CUTW = 320           # 切り替えを測る横幅（tehon-ikki miru の小さいコマと同じ）
STRONG = 0.08        # 効果音の鳴り始めに数える強さ
# 目安（🟢 / 🟡 の線。外れたら 🔴）
J_WAVE = (0.95, 0.90)            # 動きの波 相関
J_SMOOTH = (1.2, 1.5)            # 滑らかさ うち÷手本（小さいほど良い）
J_AMOUNT = ((0.85, 1.15), (0.7, 1.3))  # 動きの量 うち÷手本（tehonX の「2割多い」＝🟡）
J_DE = (1.0, 1.8)                # 色 ΔE 中央
J_OTO = (0.95, 0.85)             # 効果音 ±30ms で組めた割合
J_LUFS = (0.2, 0.5)              # 音量の差


def probe(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,nb_frames",
                                   "-show_entries", "format=duration", "-of", "json", p], capture_output=True, text=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a, b = v["r_frame_rate"].split("/")
    return dict(W=int(v["width"]), H=int(v["height"]), fps=float(a) / float(b), n=int(v.get("nb_frames") or 0),
                dur=float(j["format"]["duration"]), audio=any(s["codec_type"] == "audio" for s in j["streams"]))


def shiftcorr(a, b):
    """前のコマの真ん中 60% を今のコマの中で探した一番の相関（動きを許した形の近さ）"""
    a = a.astype(np.float32); b = b.astype(np.float32); h, w = a.shape
    y0, x0 = int(h * 0.2), int(w * 0.2); t = a[y0:h - y0, x0:w - x0]
    if t.std() < 1 or b.std() < 1: return 0.0
    return float(cv2.matchTemplate(b, t, cv2.TM_CCOEFF_NORMED).max())


class Kirikae:
    """切り替えの物差し（跳び・板替え）。コマを1枚ずつ足す"""
    def __init__(s): s.prev = None; s.m = [0.0]; s.ban = [False]

    def add(s, g):
        if s.prev is not None:
            s.m.append(float(np.abs(g.astype(np.int16) - s.prev.astype(np.int16)).mean()))
            M0, M1 = s.prev > 60, g > 60; inter = (M0 & M1).sum()
            gone = 1 - inter / max(1, M0.sum()); appe = 1 - inter / max(1, M1.sum())
            s.ban.append(bool((gone > 0.8 or appe > 0.8) and max(M0.mean(), M1.mean()) >= 0.003 and shiftcorr(s.prev, g) < 0.5))
        s.prev = g

    def cuts(s):
        m = np.array(s.m); N = len(m); src = {}
        for i in range(1, N):
            nb = max([m[j] for j in (i - 2, i - 1, i + 1, i + 2) if 1 <= j < N] or [0.0])
            if m[i] > 2.0 and m[i] > 1.8 * nb: src.setdefault(i, []).append("跳び")
            if s.ban[i]: src.setdefault(i, []).append("板替え")
        keep = []
        for k in sorted(src):          # 2コマ以内に並んだ切れ目は前の1つ（miru と同じ）
            if keep and k - keep[-1] <= 2: continue
            keep.append(k)
        return keep, {k: src[k] for k in keep}


def read_all(ref, ours, step):
    PA, PB = probe(ref), probe(ours)
    sw, sh = SMALL, int(round(SMALL * PA["H"] / PA["W"] / 2)) * 2
    cw, ch = CUTW, int(round(CUTW * PA["H"] / PA["W"] / 2)) * 2
    ca, cb = cv2.VideoCapture(ref), cv2.VideoCapture(ours)
    KA, KB = Kirikae(), Kirikae()
    DA, DB, SS, LA, LB = [0.0], [0.0], [], [], []
    pa = pb = None; i = 0; na = nb = 0
    while True:
        oka, fa = ca.read(); okb, fb = cb.read()
        if not oka and not okb: break
        ga = gb = None
        if oka:
            na += 1; sa = cv2.resize(fa, (sw, sh), interpolation=cv2.INTER_AREA); ga = cv2.cvtColor(sa, cv2.COLOR_BGR2GRAY)
            KA.add(cv2.cvtColor(cv2.resize(fa, (cw, ch), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
        if okb:
            nb += 1; sb = cv2.resize(fb, (sw, sh), interpolation=cv2.INTER_AREA); gb = cv2.cvtColor(sb, cv2.COLOR_BGR2GRAY)
            KB.add(cv2.cvtColor(cv2.resize(fb, (cw, ch), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
        if oka and okb:
            if pa is not None:
                DA.append(float(np.abs(ga.astype(np.int16) - pa.astype(np.int16)).mean()))
                DB.append(float(np.abs(gb.astype(np.int16) - pb.astype(np.int16)).mean()))
            SS.append(ssim_fn(ga, gb) if i % step == 0 else np.nan)
            LA.append(cv2.cvtColor(sa.astype(np.float32) / 255, cv2.COLOR_BGR2LAB).reshape(-1, 3).mean(0))
            LB.append(cv2.cvtColor(sb.astype(np.float32) / 255, cv2.COLOR_BGR2LAB).reshape(-1, 3).mean(0))
            pa, pb = ga, gb; i += 1
    return PA, PB, na, nb, np.array(DA), np.array(DB), np.array(SS), np.array(LA), np.array(LB), KA.cuts(), KB.cuts()


def onsets(p):
    sys.path.insert(0, TOOLS)
    import librosa
    from oto_ms import tachiagari
    with tempfile.TemporaryDirectory() as d:
        w = os.path.join(d, "a.wav")
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", p, "-vn", "-ac", "1", "-ar", "44100", w])
        if r.returncode or not os.path.exists(w): return None
        y, sr = librosa.load(w, sr=44100)
    return [o for o in tachiagari(y, sr) if o["strength"] >= STRONG]


def kumu(a, b, tol):
    """近い順に1対1で組む → うち−手本（ms）の表"""
    pr = sorted((abs(bj - ai), i, j) for i, ai in enumerate(a) for j, bj in enumerate(b) if abs(bj - ai) <= tol)
    ua, ub, dd = set(), set(), []
    for _, i, j in pr:
        if i in ua or j in ub: continue
        ua.add(i); ub.add(j); dd.append((b[j] - a[i]) * 1000)
    return np.array(dd), len(b) - len(ub)


def lufs(p):
    e = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", p, "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
    return float(m[-1]) if m else None


def iro(v, g, y, hi=True):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "⚪"
    return "🟢" if (v >= g if hi else v <= g) else "🟡" if (v >= y if hi else v <= y) else "🔴"


def iro_ratio(r, band):
    (g0, g1), (y0, y1) = band
    if r is None or np.isnan(r): return "⚪"
    return "🟢" if g0 <= r <= g1 else "🟡" if y0 <= r <= y1 else "🔴"


def corr(x, y):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0: return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("ours")
    ap.add_argument("--kukan"); ap.add_argument("--md"); ap.add_argument("--json"); ap.add_argument("--ssim-step", type=int, default=1)
    A = ap.parse_args(); ref, ours = os.path.abspath(A.ref), os.path.abspath(A.ours)
    t0 = time.time()
    PA, PB, na, nb, DA, DB, SS, LA, LB, (ca, srca), (cb, srcb) = read_all(ref, ours, max(1, A.ssim_step))
    n = len(LA); rows = []; marks = []

    def row(k, a, b, j, m=None):
        rows.append(f"| {k} | {a} | {b} | {j} | {m or ''} |")
        if j[:1] in "🟢🟡🔴": marks.append(j[:1])

    same = na == nb and abs(PA["fps"] - PB["fps"]) < 0.01
    row("コマ数・fps", f"{na}・{PA['fps']:.3f}", f"{nb}・{PB['fps']:.3f}", "🟢 同じ" if same else "🔴 違う（尺か fps がずれとる）", "同じ")
    if (PA["W"] * PB["H"]) != (PA["H"] * PB["W"]): row("縦横の比", f"{PA['W']}x{PA['H']}", f"{PB['W']}x{PB['H']}", "🔴 比が違う", "同じ比")
    s = SS[~np.isnan(SS)]
    row("SSIM（480幅グレー）", "—", f"平均 {s.mean():.3f}・中央 {np.median(s):.3f}・下位10% {np.percentile(s, 10):.3f}",
        f"⚪ 0.8未満 {(s < 0.8).sum()}/{len(s)} コマ", "参考（素材の一致は追わん）")
    # 動きの波（手本の切り替えのコマは抜く）
    mask = np.ones(n, bool); mask[0] = False
    for c in ca:
        if c < n: mask[c] = False
    w_all = corr(DA[mask], DB[mask]); w_raw = corr(DA[1:], DB[1:])
    row("動きの波（隣のコマとの差の相関・切り替えを抜く）", "—", f"{w_all:.3f}（抜かんと {w_raw:.3f}）", f"{iro(w_all, *J_WAVE)} {w_all:.3f}", "🟢0.95以上・🟡0.90以上")
    # 切り替え
    hit0 = [c for c in ca if c in cb]; hit1 = [c for c in ca if any(abs(c - d) <= 1 for d in cb)]
    extra = [d for d in cb if not any(abs(c - d) <= 1 for c in ca)]
    jk = "🟢" if len(hit0) == len(ca) and not extra else "🔴"
    row("切り替え（跳び・板替え）", "・".join(map(str, ca)) or "なし", "・".join(map(str, cb)) or "なし",
        f"{jk} {len(hit0)}/{len(ca)}（同じコマ）・±1 {len(hit1)}/{len(ca)}・余計 {len(extra)}" + (f"（{'・'.join(map(str, extra))}）" if extra else ""), "全部同じコマ・余計0")
    # 色
    dE = np.linalg.norm(LA - LB, axis=1)   # float の cv2 Lab＝L 0〜100（8bit の Lab は L が 0〜255＝約2.5倍に出る）
    row("色（コマの平均色の ΔE・Lab）", "—", f"中央 {np.median(dE):.2f}・平均 {dE.mean():.2f}・最大 {dE.max():.2f}（コマ{int(dE.argmax())}）",
        f"{iro(float(np.median(dE)), *J_DE, hi=False)} 中央 {np.median(dE):.2f}", "🟢中央1.0以下・🟡1.8以下")
    # 効果音
    oa, ob = (onsets(ref) if PA["audio"] else None), (onsets(ours) if PB["audio"] else None)
    oto = None
    if oa is not None and ob is not None and len(oa):
        a = np.array([o["t"] for o in oa]); b = np.array([o["t"] for o in ob])
        d30, ex30 = kumu(a, b, 0.030); d60, _ = kumu(a, b, 0.060)
        r30 = len(d30) / len(a)
        med = f"ずれ中央 {np.median(np.abs(d60)):.1f}ms（うち−手本 {np.median(d60):+.1f}ms・音が先 {(d60 < 0).sum()} 回）" if len(d60) else ""
        row(f"効果音の鳴り始め（強さ{STRONG}以上）", f"{len(a)}個", f"{len(b)}個",
            f"{iro(r30, *J_OTO)} ±30ms {len(d30)}/{len(a)}・±60ms {len(d60)}/{len(a)}・{med}・余計 {ex30}", "🟢95%以上・🟡85%以上（±30ms）")
        oto = dict(tehon=a.round(5).tolist(), uchi=b.round(5).tolist(), d30=d30.round(2).tolist(), d60=d60.round(2).tolist())
    else:
        row("効果音の鳴り始め", "音なし" if not PA["audio"] else f"{len(oa or [])}個", "音なし" if not PB["audio"] else f"{len(ob or [])}個", "⚪ 比べられん", "")
    la, lb = (lufs(ref) if PA["audio"] else None), (lufs(ours) if PB["audio"] else None)
    if la is not None and lb is not None:
        row("音量", f"{la:.1f} LUFS", f"{lb:.1f} LUFS", f"{iro(abs(la - lb), *J_LUFS, hi=False)} 差 {lb - la:+.1f}", "±0.2")
    # 区間
    if A.kukan:
        ks = []
        for part in A.kukan.split(","):
            nm, rg = part.rsplit(":", 1); a0, b0 = map(int, rg.split("-")); ks.append((nm.strip(), a0, min(b0, n - 1)))
    else:
        bd = [0] + [c for c in ca if 0 < c < n] + [n]
        ks = [(f"{bd[k]}–{bd[k + 1] - 1}", bd[k], bd[k + 1] - 1) for k in range(len(bd) - 1)]
    krows = []; kj = []
    for nm, a0, b0 in ks:
        idx = [i for i in range(a0 + 1, b0 + 1) if mask[i]]          # 区間の中の差（頭の切り替えの差は抜く）
        x, y = DA[idx], DB[idx]
        if len(idx) < 8:
            krows.append(f"| {nm} | {len(idx)} | — | — | — | ⚪ 短い（8コマ未満） |"); continue
        r = corr(x, y); am = (x.mean(), y.mean()); sm = (np.abs(np.diff(x, 2)).mean(), np.abs(np.diff(y, 2)).mean())
        ra = am[1] / am[0] if am[0] > 0 else float("nan"); rs = sm[1] / sm[0] if sm[0] > 0 else float("nan")
        js = [iro(r, *J_WAVE), iro_ratio(ra, J_AMOUNT), iro(rs, *J_SMOOTH, hi=False)]
        worst = "🔴" if "🔴" in js else "🟡" if "🟡" in js else "🟢"; marks.append(worst)
        why = [w for w, j in zip(("波", "量", "ギザギザ"), js) if j == worst and worst != "🟢"]
        krows.append(f"| {nm} | {len(idx)} | {r:.3f} | {am[0]:.2f}→{am[1]:.2f}（×{ra:.2f}） | {sm[0]:.2f}→{sm[1]:.2f}（×{rs:.2f}） | {worst} {'・'.join(why)} |")
        kj.append(dict(kukan=nm, f=[a0, b0], wave=r, ryo=[float(am[0]), float(am[1])], namerakasa=[float(sm[0]), float(sm[1])]))
    head = [f"# 手本とうちの数字（mg-mane hakaru・{time.strftime('%m/%d %H:%M')}）",
            f"手本＝{ref}（{PA['W']}x{PA['H']}・{PA['fps']:.3f}fps・{na}コマ・{PA['dur']:.2f}秒）",
            f"うち＝{ours}（{PB['W']}x{PB['H']}・{PB['fps']:.3f}fps・{nb}コマ・{PB['dur']:.2f}秒）", "",
            "| 項目 | 手本 | うち | 一致 | 目安 |", "|---|---|---|---|---|"]
    tail = ["", "## 区間ごと（" + ("--kukan の区間" if A.kukan else "手本の切り替えで割る") + "・頭の切り替えのコマは抜く）",
            "| 区間（コマ） | 差の数 | 動きの波 | 動きの量 手本→うち | 滑らかさ（2階差）手本→うち | 判定 |", "|---|---|---|---|---|---|"] + krows + [
            "", f"🔴 {marks.count('🔴')}・🟡 {marks.count('🟡')}・🟢 {marks.count('🟢')}（🔴＝直す・🟡＝目で見て決める・SSIM は参考）　{time.time() - t0:.0f}秒",
            "目安＝🟢/🟡の線（動きの波 0.95/0.90・量の比 0.85〜1.15/0.7〜1.3・ギザギザの比 1.2/1.5・ΔE 中央 1.0/1.8・効果音 ±30ms 95%/85%・音量の差 0.2/0.5）"]
    md = "\n".join(head + rows + tail)
    print(md)
    if A.md: open(A.md, "w").write(md + "\n")
    if A.json:
        json.dump(dict(tehon=ref, uchi=ours, n=[na, nb], fps=[PA["fps"], PB["fps"]], ssim=dict(mean=float(s.mean()), median=float(np.median(s)), p10=float(np.percentile(s, 10)), under08=int((s < 0.8).sum())),
                       wave=w_all, wave_raw=w_raw, cuts=dict(tehon=ca, uchi=cb, src_tehon=srca, src_uchi=srcb, hit=len(hit0), extra=extra),
                       dE=dict(median=float(np.median(dE)), mean=float(dE.mean()), max=float(dE.max()), at=int(dE.argmax())),
                       oto=oto, lufs=[la, lb], kukan=kj, marks=dict(red=marks.count("🔴"), yellow=marks.count("🟡"), green=marks.count("🟢"))),
                  open(A.json, "w"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()

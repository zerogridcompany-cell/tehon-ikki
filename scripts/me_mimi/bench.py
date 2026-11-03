"""目と耳の物差し（10/31 依頼者「目と耳の精度をどんどん上げていけるように」）。正解が1サンプル・1コマまで分かっとる試験を自分で作って、道具が何ms・何コマずれるかを点数にする。

python3 bench.py [--seed 1] [--log]     … 3つの試験を回して表を出す。--log で references/me_mimi.md の記録に1行足す
耳：曲の上に、ドラムの1発（キック・スネア・ハット）を決めた時刻に置く（曲の大きさ3段）→ oto_ms.tachiagari で何ms ずれるか・見落とし・余計
目：決めたコマに、カット・溶け（6コマ）・光り（1コマ）・黒地の細い線の書き換え（画面の1〜2%）・横に流れる入り を置いた動画 → me_ms.dekigoto で変わり始めが何コマずれるか
音と絵：カットの何ms後にキックを鳴らすかを決めた動画（−40〜+80ms）→ 2つの道具で測った「音は絵の何ms後」と正解の差
正解の決め方：1発の鳴り始め＝その1発だけの包絡が山の30%を超えた1サンプル（道具と同じ定義）。絵＝置いたコマ番号
"""
import argparse, glob, json, os, subprocess, sys, tempfile, time
import numpy as np, librosa, soundfile as sf, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from oto_ms import tachiagari
from me_ms import dekigoto, read_gray
SR = 44100
SFX = os.path.expanduser("~/scratcher-basket/vsl/remotion/public/sfx_premium")


def own_onset(x):
    import scipy.signal as ss
    env = ss.sosfiltfilt(ss.butter(2, 400, "low", fs=SR, output="sos"), np.abs(ss.hilbert(x)))
    j = int(np.argmax(env)); return int(np.argmax(env[:j + 1] >= 0.3 * env[j]))


def ear(rng):
    hits = {k: [librosa.load(p, sr=SR)[0] for p in sorted(glob.glob(f"{SFX}/selfsynth_drum_{k}_*.wav"))] for k in ("kick", "snare", "hat")}
    bed = librosa.load(os.path.join(HERE, "bed_other.wav"), sr=SR)[0] + librosa.load(os.path.join(HERE, "bed_bass.wav"), sr=SR)[0]
    bed = bed[:SR * 30]; bed = bed / (np.abs(bed).max() + 1e-9)
    rows = []
    for lvl_name, lvl in (("曲なし", 0.0), ("曲 −12dB", 10 ** (-12 / 20)), ("曲 −6dB", 10 ** (-6 / 20))):
        for kind in ("kick", "snare", "hat"):
            y = bed * lvl * 0.5; truth = []
            t = 0.3
            while t < 29:
                s = hits[kind][rng.integers(len(hits[kind]))] * 0.5; st = int(t * SR) + int(rng.integers(0, 64))
                y[st:st + len(s)] += s[:len(y) - st]; truth.append((st + own_onset(s)) / SR)
                t += rng.uniform(0.18, 0.6)
            det = np.array([o["t"] for o in tachiagari(y, SR)])
            err = []; miss = 0
            for tt in truth:
                j = np.argmin(np.abs(det - tt)) if len(det) else None
                if j is None or abs(det[j] - tt) > 0.05: miss += 1
                else: err.append((det[j] - tt) * 1000)
            used = sum(1 for d in det if np.min(np.abs(np.array(truth) - d)) <= 0.05)
            e = np.abs(err) if err else np.array([np.nan])
            rows.append(dict(test=f"耳 {kind} {lvl_name}", n=len(truth), miss=miss, extra=int(len(det) - used) if lvl == 0 else "曲の音も入る＝数えん", med_ms=round(float(np.median(e)), 2), p90_ms=round(float(np.percentile(e, 90)), 2), bias_ms=round(float(np.median(err)) if err else 0, 2)))
    return rows


def make_video(path, rng, fps=30, N=900, W=640, H=360, kick_offsets=None):
    """決めたコマに出来事を置く。返り値＝正解 [(f, kind)]"""
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    def pic(seed):
        r = np.random.default_rng(seed); im = np.zeros((H, W, 3), np.uint8)
        im[:] = r.integers(20, 200, 3)
        for _ in range(8): cv2.circle(im, (int(r.integers(0, W)), int(r.integers(0, H))), int(r.integers(20, 120)), [int(v) for v in r.integers(0, 255, 3)], -1)
        return cv2.GaussianBlur(im, (0, 0), 3)
    def hud(seed):
        r = np.random.default_rng(seed); im = np.zeros((H, W, 3), np.uint8)
        for _ in range(int(r.integers(6, 14))):
            x, y = int(r.integers(10, W - 120)), int(r.integers(10, H - 20)); cv2.line(im, (x, y), (x + int(r.integers(40, 160)), y), (220, 220, 220), 1)
        cv2.putText(im, f"T(n)={int(r.integers(2, 99))}", (int(r.integers(20, 400)), int(r.integers(40, 320))), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (235, 235, 235), 1)
        return im
    truth = []; f = 0; cur = pic(0); seq = 1; kinds = ["cut", "fade", "flash", "part", "whip"]
    plan = []
    while f < N - 40:
        g = int(rng.integers(12, 28)); f += g; k = kinds[len(plan) % len(kinds)] if kick_offsets is None else "cut"; plan.append((f, k))
    frames = [None] * N; base = pic(0); hudmode = False
    ev = dict(plan); i = 0
    while i < N:
        if i in ev:
            k = ev[i]; truth.append((i, k))
            if k == "cut": base = pic(seq); hudmode = False
            elif k == "fade":
                nb = pic(seq)
                for j in range(6):
                    if i + j < N: frames[i + j] = cv2.addWeighted(base, 1 - (j + 1) / 7, nb, (j + 1) / 7, 0)
                base = nb; i += 6; seq += 1; continue
            elif k == "flash": frames[i] = cv2.addWeighted(base, 0.3, np.full_like(base, 255), 0.7, 0); i += 1; continue
            elif k == "part":
                if not hudmode: base = hud(seq); hudmode = True
                else:
                    nb = base.copy(); r = np.random.default_rng(seq)
                    x, y = int(r.integers(20, 420)), int(r.integers(30, 330)); cv2.rectangle(nb, (x - 4, y - 22), (x + 200, y + 6), (0, 0, 0), -1)
                    cv2.putText(nb, f"x={int(r.integers(10, 99))}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (235, 235, 235), 1); base = nb
            elif k == "whip":
                nb = pic(seq)
                for j in range(3):
                    if i + j < N:
                        sh = int(W * (j + 1) / 3); fr = np.zeros_like(base); fr[:, :W - sh] = base[:, sh:]; fr[:, W - sh:] = nb[:, :sh]; frames[i + j] = cv2.blur(fr, (25, 1))
                base = nb; i += 3; seq += 1; continue
            seq += 1
        if frames[i] is None: frames[i] = base
        i += 1
    for fr in frames: vw.write(fr)
    vw.release()
    return truth


def eye(rng, tmp):
    p = os.path.join(tmp, "eye.mp4"); truth = make_video(p, rng)
    q = p.replace(".mp4", "_h264.mp4"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", q])
    G, fps = read_gray(q); E0 = dekigoto(G, fps); E = [e for e in E0 if e["kind"] != "masu"]; M = [e for e in E0 if e["kind"] == "masu"]   # masu＝止まった所の小さい変わり（別の帳）
    rows = []
    for k in ("cut", "fade", "flash", "part", "whip"):
        tk = [f for f, kk in truth if kk == k]; err = []; miss = 0
        for f in tk:
            c = [e["f_start"] for e in E if abs(e["f_start"] - f) <= 3]
            if not c: miss += 1
            else: err.append(min(c, key=lambda x: abs(x - f)) - f)
        e = np.abs(err) if err else np.array([np.nan])
        rows.append(dict(test=f"目 {k}", n=len(tk), miss=miss, ok0=int(sum(1 for x in err if x == 0)), med_koma=round(float(np.median(e)), 2), bias_koma=round(float(np.median(err)) if err else 0, 2)))
    used = sum(1 for e in E if any(abs(e["f_start"] - f) <= 3 for f, _ in truth))
    rows.append(dict(test="目 余計（正解に無い出来事）", n=len(E), extra=int(len(E) - used)))
    rows.append(dict(test="目 升の帳 余計（作った試験は止まった所が変わらん＝全部余計）", n=len(M), extra=int(sum(1 for e in M if not any(abs(e["f_start"] - f) <= 3 for f, _ in truth)))))
    return rows


def av(rng, tmp):
    p = os.path.join(tmp, "av.mp4"); truth = make_video(p, rng, kick_offsets=True)
    fps = 30; kick = librosa.load(sorted(glob.glob(f"{SFX}/selfsynth_drum_kick_*.wav"))[0], sr=SR)[0] * 0.6
    y = np.zeros(int(SR * 900 / fps) + SR); offs = []
    bed = librosa.load(os.path.join(HERE, "bed_other.wav"), sr=SR)[0]; y[:min(len(y), len(bed))] += bed[:len(y)] * 0.15
    oo = own_onset(kick)
    for f, _ in truth:
        o = float(rng.choice([-40, -20, 0, 15, 38, 60, 80])) / 1000; st = int((f / fps + o) * SR) - oo
        if st < 0: continue
        y[st:st + len(kick)] += kick[:len(y) - st]; offs.append((f, o * 1000))
    wav = os.path.join(tmp, "av.wav"); sf.write(wav, y, SR); q = p.replace(".mp4", "_av.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-i", wav, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", q])
    G, fps2 = read_gray(q); E = dekigoto(G, fps2)
    a = os.path.join(tmp, "av_back.wav"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", q, "-vn", "-ac", "1", "-ar", str(SR), a])
    yy = librosa.load(a, sr=SR)[0]; onl = tachiagari(yy, SR, band=[30, 150]); on = np.array([o["t"] for o in onl])
    err = []
    for f, o in offs:
        c = [e for e in E if abs(e["f_start"] - f) <= 2]
        if not c or not len(on): continue
        ts = c[0]["t_start"]; w = [(x["strength"], x["t"]) for x in onl if -0.08 <= x["t"] - ts <= 0.12]   # 窓の中で一番強い音（一番近い音やなく）
        if not w: continue
        m = (max(w)[1] - ts) * 1000; err.append(m - o)
    e = np.abs(err)
    return [dict(test="音と絵（aac で書き出した後）", n=len(offs), got=len(err), med_ms=round(float(np.median(e)), 2), p90_ms=round(float(np.percentile(e, 90)), 2), bias_ms=round(float(np.median(err)), 2))]


def real(tmp):
    """本物の手本（目で1コマずつ確かめた正解）＝real_*.json。作った試験だけやと易しすぎて 45/45 でも本物で 17/24 やった（10/31）"""
    rows = []
    for jp in sorted(glob.glob(os.path.join(HERE, "real_*.json"))):
        k = json.load(open(jp)); src = os.path.expanduser(k["src"])
        if not os.path.exists(src): rows.append(dict(test=f"本物 {os.path.basename(jp)}", skip="手本が Mac に無い（drive-fetch）")); continue
        G, fps = read_gray(src, k.get("w", 640)); E0 = dekigoto(G, fps); E = [e for e in E0 if e["kind"] != "masu"]
        cut = k["cut"]; oth = [int(x) for x in k.get("other", {})]
        err = [min((e["f_start"] - g for e in E if abs(e["f_start"] - g) <= 1), key=abs) for g in cut if any(abs(e["f_start"] - g) <= 1 for e in E)]
        rows.append(dict(test=f"本物 {os.path.basename(jp)[5:-5]} カット", n=len(cut), miss=len(cut) - len(err), ok0=sum(1 for x in err if x == 0),
                         extra=sum(1 for e in E if all(abs(e["f_start"] - g) > 1 for g in cut + oth)), masu=len(E0) - len(E)))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--log", action="store_true"); a = ap.parse_args()
    rng = np.random.default_rng(a.seed); t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        rows = ear(rng) + eye(rng, tmp) + real(tmp) + av(rng, tmp)
    for r in rows: print(r)
    out = os.path.join(HERE, "last.json"); json.dump(dict(when=time.strftime("%Y-%m-%d %H:%M"), seed=a.seed, rows=rows), open(out, "w"), ensure_ascii=False, indent=1)
    print("書いた", out, f"{time.time() - t0:.0f}秒")

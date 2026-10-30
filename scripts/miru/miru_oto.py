"""段0 見る：手本の音を1回で全部の数字に（手本の音だけ・作った物は聞かん）。
python3 miru_oto.py <手本.mp4> <作業>
- 7つの箱＝/oto-bunrui の hako.py（demucs で4つに分ける→声・音楽・効果音（時刻・種類・強さ）・聞こえ方（LUFS・フェード））
- 声の1語ずつ＝whisper-cli（large-v3-turbo・1語ずつ・声の層 16kHz）。声の箱が 1秒未満なら「なし」
- 強い低音＝ドラムの層の 30〜150Hz の大きさの立ち上がり（山）
- 曲＝Shazam（kouzou/shazam_undo.py・8秒の窓・4秒おき）→ 同じ曲の窓をつないで区間 → 区間ごとに拍の網（kouzou.py の song_beats と同じ：beat_track＋小節の頭＝4拍のうち低音の打ちが一番強い位相）
- 大きさ＝ffmpeg ebur128（全体の LUFS・幅・最大）／区間の替わり目の消え方・入り方（音楽の層の大きさ 0.05秒ごと）
出す物：<作業>/zukan/parts/oto.json（重い物＝<作業>/zukan/oto/）
"""
import json, os, re, subprocess, sys
import numpy as np, librosa, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); SK = os.path.join(HERE, "..")
REF = os.path.abspath(sys.argv[1]); W_ = os.path.abspath(sys.argv[2]); O = f"{W_}/zukan/oto"; P = f"{W_}/zukan/parts"; os.makedirs(O, exist_ok=True)
PY = sys.executable
HAKO = os.path.expanduser("~/.claude/skills/oto-bunrui/scripts/hako.py")
SHZ = os.path.join(SK, "kouzou", "shazam_undo.py")
MODEL = os.path.expanduser("~/Library/Caches/whisper-cpp/ggml-large-v3-turbo.bin")
out = {}
# 🔴 長さは絵の長さ（51 は音が 187秒・絵が 93.8秒＝音の後ろ半分は絵に無い）
dur = json.load(open(f"{P}/kihon.json"))["dur"] if os.path.exists(f"{P}/kihon.json") else \
    float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", REF], capture_output=True, text=True).stdout)

# ── 1 箱（hako.py）──
if not os.path.exists(f"{O}/hako.json"):
    subprocess.run([PY, HAKO, REF, O, "--cuts", REF], check=True)
hk = json.load(open(f"{O}/hako.json"))
sep = f"{O}/sep/htdemucs/src"
koe = [x for x in hk.get("1 声", []) if x["t0"] < dur]; koe_s = sum(x["t1"] - x["t0"] for x in koe)
out["koe_kukan"] = koe if koe else {"v": "なし", "konkyo": f"声の箱 0区間（hako.py・demucs の声の層）"}
out["koe_byou"] = round(koe_s, 2)
sfx = [dict(t=x["t"], dur=x.get("dur"), db=x.get("db"), kind=x.get("kind"), hako=x.get("hako"), awaseru=x.get("awaseru")) for x in hk.get("3〜5 効果音", [])]
sfx = [x for x in sfx if x["t"] < dur]
out["sfx"] = sfx
out["kikoekata"] = hk.get("7 聞こえ方", {})
out["ongaku_hako"] = hk.get("2 音楽", {})

# ── 2 声の1語ずつ ──
words = []
if koe_s >= 1.0 and os.path.exists(MODEL):
    v16 = f"{O}/koe16k.wav"
    if not os.path.exists(v16):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", f"{sep}/vocals.wav", "-ac", "1", "-ar", "16000", v16], check=True)
    if not os.path.exists(f"{O}/koe_words.json"):
        subprocess.run(["whisper-cli", "-m", MODEL, "-f", v16, "-l", "auto", "-ml", "1", "-sow", "-oj", "-np", "-of", f"{O}/koe_words"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    J = json.load(open(f"{O}/koe_words.json"))
    for s in J.get("transcription", []):
        t = s.get("text", "").strip()
        if not t or t.startswith("["): continue
        if s["offsets"]["from"] / 1000 >= dur: continue
        words.append(dict(w=t, t0=round(s["offsets"]["from"] / 1000, 3), t1=round(s["offsets"]["to"] / 1000, 3)))
# 語りか歌か：1秒あたりの語が 1 未満なら歌の声（51：声の層 107秒に 14語＝0.13・r2：66秒に 249語＝3.8）
out["koe_shurui"] = dict(v="語り" if koe_s and len(words) / max(koe_s, 1e-3) >= 1.0 else ("歌・声ネタ（語りなし）" if koe_s >= 1.0 else "声なし"),
                         go_per_byou=round(len(words) / max(koe_s, 1e-3), 2), koe_byou=round(koe_s, 1))
out["koe_words"] = words if words else {"v": "なし", "konkyo": f"声の箱 {koe_s:.1f}秒（1秒未満は声なし）"}

# ── 3 強い低音（30〜150Hz の立ち上がり）──
SR = 22050; HOP = 256
yd, _ = librosa.load(f"{sep}/drums.wav", sr=SR)
yb, _ = librosa.load(f"{sep}/bass.wav", sr=SR)
S = np.abs(librosa.stft(yd + 0.5 * yb, n_fft=2048, hop_length=HOP)); fr = librosa.fft_frequencies(sr=SR, n_fft=2048)
band = S[(fr >= 30) & (fr <= 150)].sum(0); lb = np.log1p(band / (np.median(band) + 1e-9))
on = np.maximum(0, np.diff(lb, prepend=lb[0]))
pk = librosa.util.peak_pick(on, pre_max=4, post_max=4, pre_avg=10, post_avg=10, delta=0.05, wait=8)
ts = librosa.frames_to_time(pk, sr=SR, hop_length=HOP)
st = on[pk]; thr = max(float(np.percentile(on, 99)) * 0.5, float(np.median(st)) if len(st) else 0)
kicks = [dict(t=round(float(t), 3), s=round(float(s), 2)) for t, s in zip(ts, st) if s >= thr and t < dur]
out["kick"] = kicks if kicks else {"v": "なし", "konkyo": f"30〜150Hz の山 {len(ts)}・強い物 0（しきい {thr:.2f}）"}
out["kick_rule"] = "ドラム＋ベース半分の 30〜150Hz の対数の大きさの立ち上がり・山の強さ ≥ max(上位1%の半分, 山の中央値)"

# ── 4 曲（Shazam）→ 区間 ──
# 🔴 声が乗った全体の音だと Shazam が黙る（r2：76秒で2窓だけ）→ 声を抜いた音楽の層（drums＋bass＋other）で先に聞く（r2：19窓中 12窓）
if not os.path.exists(f"{O}/music.wav"):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + sum([["-i", f"{sep}/{k}.wav"] for k in ("drums", "bass", "other")], []) +
                   ["-filter_complex", "amix=inputs=3:normalize=0", f"{O}/music.wav"], check=True)
for src, js in (("music.wav", "shazam_music.json"), ("src.wav", "shazam.json")):
    if not os.path.exists(f"{O}/{js}"):
        subprocess.run([PY, SHZ, f"{O}/{src}", f"{O}/{js}", "1.0"], capture_output=True, text=True)
        if not os.path.exists(f"{O}/{js}"): json.dump([], open(f"{O}/{js}", "w"))
win = {}
for js in ("shazam_music.json", "shazam.json"):
    for x in json.load(open(f"{O}/{js}")): win.setdefault(x["w0"], dict(x, src=js))
# 区間＝速さ（1分の拍）が変わる所で割る（Shazam は黙る窓が多い＝区間の切れ目には使わん・名前だけ）
#   r2：Shazam の区間だけだと 0〜16秒が1つ（中に 92 と 123 の2曲）→ 1秒ごとの速さ（7秒の窓・prior なし）で割ると 8・20・30・61秒で替わる
mus_ = sum(librosa.load(f"{sep}/{k}.wav", sr=SR)[0] for k in ("drums", "bass", "other"))
oe_all = librosa.onset.onset_strength(y=mus_, sr=SR); ofps = SR / 512
import scipy.signal as ssig
loc = []
for s_ in range(int(np.ceil(dur))):
    a_, b_ = int(max(0, s_ - 3) * ofps), int(min(dur, s_ + 4) * ofps)
    loc.append(float(librosa.feature.tempo(onset_envelope=oe_all[a_:b_], sr=SR, prior=None)[0]) if b_ - a_ > ofps * 2 else 0.0)
loc = ssig.medfilt(np.array(loc), 5)
runs = []
for s_, v in enumerate(loc):
    if runs and abs(v - runs[-1]["t"]) <= 0.03 * runs[-1]["t"]: runs[-1]["b"] = s_ + 1
    else: runs.append(dict(a=s_, b=s_ + 1, t=v))
m_ = []
for r_ in runs:
    if m_ and r_["b"] - r_["a"] < 3: m_[-1]["b"] = r_["b"]
    else: m_.append(r_)
runs = m_
# 切れ目を音色の変わり目（MFCC の前後2秒の差の山・±4秒）で詰める
mf = librosa.feature.mfcc(y=mus_, sr=SR, n_mfcc=20, hop_length=int(SR * 0.05)); mt = np.arange(mf.shape[1]) * 0.05
def nov(t):
    a1 = (mt >= t - 2) & (mt < t); b1 = (mt >= t) & (mt < t + 2)
    if a1.sum() < 5 or b1.sum() < 5: return 0.0
    x, y_ = mf[:, a1].mean(1), mf[:, b1].mean(1); return float(1 - np.dot(x, y_) / (np.linalg.norm(x) * np.linalg.norm(y_) + 1e-9))
for j in range(1, len(runs)):
    b0 = runs[j]["a"]; cand = np.arange(max(runs[j - 1]["a"] + 1, b0 - 1.5), min(runs[j]["b"] - 1, b0 + 1.5), 0.05)   # ±4秒だと r2 で 3秒ずれた＝±1.5秒
    if len(cand): bb = float(cand[int(np.argmax([nov(t) for t in cand]))]); runs[j - 1]["b"] = runs[j]["a"] = round(bb, 2)
# 詰めた後に短くなった区間（2.5秒未満）は速さの近い隣へ（r2 の2回目で 9.45〜10.45 の1秒の区間ができて拍の網が空になった）
while len(runs) > 1:
    j = next((j for j, r_ in enumerate(runs) if r_["b"] - r_["a"] < 2.5), None)
    if j is None: break
    nb = [k for k in (j - 1, j + 1) if 0 <= k < len(runs)]
    k = min(nb, key=lambda k: abs(runs[k]["t"] - runs[j]["t"]))
    runs[k]["a"], runs[k]["b"] = min(runs[k]["a"], runs[j]["a"]), max(runs[k]["b"], runs[j]["b"]); runs.pop(j)
secs = []
from collections import Counter
for r_ in runs:
    nm = [f'{c["artist"]} - {c["title"]}' for w0, c in win.items() if r_["a"] - 0.5 <= w0 and w0 + 8 <= r_["b"] + 0.5] or \
         [f'{c["artist"]} - {c["title"]}' for w0, c in win.items() if r_["a"] <= w0 + 4 < r_["b"]]   # 窓が丸ごと入る物を先に
    secs.append(dict(name=Counter(nm).most_common(1)[0][0] if nm else "不明", a=r_["a"], b=r_["b"], tempo_local=round(float(r_["t"]), 1)))
secs[0]["a"] = 0; secs[-1]["b"] = round(dur, 3)
ym, _ = librosa.load(f"{O}/src.wav", sr=SR)
mus = None
try:
    mus = sum(librosa.load(f"{sep}/{k}.wav", sr=SR)[0] for k in ("drums", "bass", "other"))
except Exception: mus = ym
for x in secs:
    hits = [c for w0, c in win.items() if x["a"] - 1 <= w0 + 4 < x["b"] + 1 and f'{c["artist"]} - {c["title"]}' == x["name"]]
    if hits:
        offs = [c["offset"] - c["w0"] for c in hits if c.get("offset") is not None]
        x["at0"] = round(float(np.median(offs)), 2) if offs else None   # 手本の0秒の時の曲の秒（kyoku.json と同じ）
        sk = [c.get("skew") for c in hits if c.get("skew") is not None]
        x["skew"] = round(float(np.median(sk)), 4) if sk else None
        x["konkyo"] = dict(shazam=len(hits), madoi=sum(1 for w0 in win if x["a"] <= w0 + 4 < x["b"]))
        x["key"] = hits[0].get("key")
    else:
        x["fumei"] = True; x["konkyo"] = dict(shazam=0, madoi=sum(1 for w0 in win if x["a"] <= w0 + 4 < x["b"]), note="Shazam が黙った＝曲は不明（kouzou の bgm_fp で元の曲から探す）")
    # 拍の網（区間の音楽の層だけ）
    a0, b0 = int(x["a"] * SR), int(x["b"] * SR); y = mus[a0:b0]
    if len(y) > SR * 2:
        tempo, bt = librosa.beat.beat_track(y=y, sr=SR, units="time")
        oe = librosa.onset.onset_strength(y=librosa.effects.preemphasis(y, coef=-0.97), sr=SR); tt = librosa.times_like(oe, sr=SR)
        stb = np.interp(bt, tt, oe); ph = int(np.argmax([stb[k::4].mean() for k in range(4)])) if len(bt) >= 4 else 0
        bt = bt + x["a"]; bars = bt[ph::4]
        x["bpm"] = round(float(np.atleast_1d(tempo)[0]), 1); x["beats"] = [round(float(v), 3) for v in bt]; x["bars"] = [round(float(v), 3) for v in bars]
    else:
        x["bpm"] = None; x["beats"] = []; x["bars"] = []
out["kyoku"] = secs
# ── 5 替わり目の消え方・入り方（音楽の層 0.05秒ごと）──
env = 20 * np.log10(librosa.feature.rms(y=mus, frame_length=2048, hop_length=int(SR * 0.05))[0] + 1e-9); et = np.arange(len(env)) * 0.05
def lvl(a, b):
    m = (et >= a) & (et < b); return float(np.median(env[m])) if m.any() else -90.0
kirikae = []
for i in range(1, len(secs)):
    b = secs[i]["a"]; pre, post = lvl(b - 3, b - 1), lvl(b + 1, b + 3)
    m = (et >= b - 1.5) & (et <= b + 1.5); e = env[m]; t = et[m]
    lo_i = int(np.argmin(e)) if len(e) else 0
    kirikae.append(dict(t=b, mae=secs[i - 1]["name"], ato=secs[i]["name"], mae_db=round(pre, 1), ato_db=round(post, 1),
                        tani_t=round(float(t[lo_i]), 2) if len(e) else None, tani_db=round(float(e[lo_i]), 1) if len(e) else None,
                        note="谷の深さ＝前後の大きさ−谷。浅い（<6dB）＝重ねて入れ替え・深い＝消してから入る（目安。正確な秒は kouzou の fade_fit で元の曲から）"))
out["kyoku_kirikae"] = kirikae
# ── 6 大きさ ──
e = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", REF, "-t", f"{dur:.3f}", "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
g = lambda pat: (float(re.findall(pat, e)[-1]) if re.findall(pat, e) else None)
out["lufs"] = dict(I=g(r"I:\s+(-?[\d.]+) LUFS"), LRA=g(r"LRA:\s+(-?[\d.]+) LU"), peak=g(r"Peak:\s+(-?[\d.]+) dBFS"))
out["dur"] = round(dur, 3)
json.dump(out, open(f"{P}/oto.json", "w"), ensure_ascii=False)
print("音：声", round(koe_s, 1), "秒・語", len(words), "・効果音", len(sfx), "・強い低音", len(kicks), "・曲の区間", [(x["name"][:24], x["a"], x["b"], x.get("bpm")) for x in secs], "・LUFS", out["lufs"])

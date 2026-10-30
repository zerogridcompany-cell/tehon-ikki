# 構造の門：作る前に「手本が何でできとるか」が数字で全部そろっとるか。そろってなければ作る段へ進まん
# 使い方: python3 check_kouzou.py <作業>   → 赤が1つでもあれば exit 1
import json, os, sys, subprocess
W = sys.argv[1]; red = []; ok = []
def need(p, why):
    if not os.path.exists(f'{W}/{p}'): red.append(f'{p} が無い（{why}）'); return False
    return True
ref = next((f'{W}/ref/{f}' for f in sorted(os.listdir(f'{W}/ref')) if f.endswith('.mp4')), None) if os.path.isdir(f'{W}/ref') else None
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', ref], capture_output=True, text=True).stdout or 0) if ref else 0
# 1 曲：全部の秒が、確かめた曲か「不明」と書いた区間で埋まっとる
if need('kouzou/kyoku.json', '曲の区間・版・速さ・位置'):
    S = sorted(json.load(open(f'{W}/kouzou/kyoku.json')), key=lambda s: s['a'])
    t = 0.0
    for s in S:
        if s['a'] - t > 0.05: red.append(f'曲の穴 {t:.2f}〜{s["a"]:.2f}秒')
        t = max(t, s['b'])
        ev = s.get('konkyo', {})
        if s.get('fumei'): ok.append(f'⚠️ {s["a"]}〜{s["b"]}秒は不明と明記（代わり＝{s["name"]}）')
        elif not (ev.get('fp_hits', 0) >= 20 or ev.get('shazam') or ev.get('audd_fp')):
            red.append(f'{s["a"]}〜{s["b"]}秒「{s["name"]}」の根拠が弱い（指紋20点以上・Shazam・AudD＋指紋のどれも無い）')
    if dur and dur - t > 0.3: red.append(f'曲の穴 {t:.2f}〜{dur:.2f}秒')
# 2 絵：1コマずつの出来事
if need('kouzou/picture.json', '絵の出来事を1コマずつ（e_picture.py）'):
    P = json.load(open(f'{W}/kouzou/picture.json'))
    if dur and abs(P['n'] / P['fps'] - dur) > 0.2: red.append(f'picture.json のコマ数 {P["n"]} が手本の長さと合わん')
    else: ok.append(f'絵の出来事 {len(P["events"])} 個（{P["n"]}コマ）')
# 3 つながり：区間ごとに「何に合わせとるか」が決まっとる
if need('kouzou/kouzou.json', '区間ごとの物差し（kouzou.py）'):
    K = json.load(open(f'{W}/kouzou/kouzou.json'))
    for s in K['sections']:
        if 'all' not in s['kinds']: red.append(f'{s["name"]} の物差しが出てない')
# 4 切り替わり：曲の替わり目ごとに出る/入るの数字
fade = next((p for p in ('kouzou/fade.json', 'oto/bgm4/m1/fade.json') if os.path.exists(f'{W}/{p}')), None)
if not fade: red.append('曲の切り替わりの数字が無い（bgm_env.py → fade_fit.py）')
elif os.path.exists(f'{W}/kouzou/kyoku.json'):
    n = len(json.load(open(f'{W}/{fade}'))['kirikae']); b = len(set(round(s['b'], 2) for s in S)) - 1
    (ok if n >= b else red).append(f'切り替わり {n}/{b} か所')
# 5 決まりの表
need('kouzou/決まり.md', '曲・切り替わり・絵の物差し・効果音を数字で')
# 6 🔒 写真を動かして動画のふりをせん（10/30 依頼者「本当に見てて苦しい」）
st = sorted([f for f in os.listdir(f'{W}/shirabe') if f.startswith('静止表_')]) if os.path.isdir(f'{W}/shirabe') else []
if st:
    d = json.load(open(f'{W}/shirabe/{st[-1]}')); n = sum(1 for x in (d if isinstance(d, list) else d.get('cuts', [])) if str(x.get('ok', x.get('hantei', ''))).startswith('🔴'))
    (red if n else ok).append(f'一枚絵を動かしとるカット🔴 {n}（{st[-1]}）')
for x in ok: print('✅', x)
for x in red: print('🔴', x)
print('門', 'OK' if not red else f'止める（赤 {len(red)}）'); sys.exit(1 if red else 0)

"""目の試験の答え（seikai.json）を、写しを詰め切った作業フォルダの最後の版から機械で取る（10/31・どの手本でも使える形）。
使い方：python3 seikai_kara.py <作業フォルダ> [版 例 v89] [-o 出す先.json] [--fps 29.97]  → 既定は <作業>/me_shiken/seikai.json
  人の作業フォルダ（読むだけ）から取る時は -o で自分の場所に出す。
  版を書かんと、check_v*/mane_check.json の一番大きい番号を使う。
  読む物（無い物は nashi に理由を書いて答えから外す＝点に入れん）：
    cfg.json（大きさ・fps）／base_<版>.json（カット）／check_<版>/mane_check.json（手本のカット＝余計に数えん）
    shirabe/静止表_<版>.json（動画か止め絵か＝still_check.py）／shirabe/動き表_<版>.json（カメラ・中の動き＝motion_kind.py）
    proj/src/flash.json（光るコマ）／proj/src/caps.json（字）／proj/src/hud.json（HUD）
    kouzou/kyoku.json（曲の区間）／oto/hako/hako.json（声・効果音・LUFS＝oto-bunrui の hako.py）
採点＝python3 me_shiken.py <作業>/zukan/zukan_v0_saisho.json <作業>/me_shiken/seikai.json"""
import glob, json, os, re, sys

A = sys.argv[1:]; OUT = None
if '-o' in A: i = A.index('-o'); OUT = A[i + 1]; del A[i:i + 2]
FPS_ARG = None
if '--fps' in A: i = A.index('--fps'); FPS_ARG = float(A[i + 1]); del A[i:i + 2]
W = os.path.abspath(A[0])
def ld(p):
    p = f'{W}/{p}'
    return json.load(open(p)) if os.path.exists(p) else None
if len(A) > 1: V = A[1]
else:
    vs = [int(m.group(1)) for p in glob.glob(f'{W}/check_*v*/mane_check.json') if (m := re.search(r'check_(?:.*_)?v(\d+)/', p))]
    if not vs: sys.exit('check_v*/mane_check.json が無い＝まず run.sh render で書き出して測る')
    V = f'v{max(vs)}'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from geo import geo   # 大きさ・fps は図鑑→cfg.json→手本の順で読む（30 を決め打ちせん）
try: g = geo(W); GW, GH, FPS = g['W'], g['H'], g['FPS']
except (IndexError, KeyError, FileNotFoundError):   # 手本を Drive に移した作業など＝--fps で渡す
    if FPS_ARG is None: sys.exit('大きさ・fps が読めん（zukan.json・cfg.json・ref/*.mp4 が無い）＝ --fps を付ける')
    GW = GH = None; FPS = FPS_ARG
if FPS_ARG: FPS = FPS_ARG
S = dict(note=f'{os.path.basename(W)} の最後の版 {V} から機械で取った答え', W=GW, H=GH, fps=FPS)
nashi = {}

st = ld(f'shirabe/静止表_{V}.json')
base = ld(f'base_{V}.json')
if st:
    S['cuts'] = [r['f0'] for r in st][1:]; S['src_cuts'] = f'shirabe/静止表_{V}.json の f0'
    S['douga'] = {str(r['f0']): bool(r['N_ref'] >= 2) for r in st if r.get('N_ref') is not None}; S['src_douga'] = '静止表 N_ref≥2＝本物の動画'
elif base:
    S['cuts'] = [int(round(b['t0'] * FPS)) for b in base][1:]; S['src_cuts'] = f'base_{V}.json の t0'
    nashi['douga'] = f'shirabe/静止表_{V}.json が無い（still_check.py を回すと出る）'
else: nashi['cuts'] = 'カットの表が無い'
mcp = sorted(glob.glob(f'{W}/check_*{V}/mane_check.json')); mc = json.load(open(mcp[-1])) if mcp else None
S['cuts_ok_extra'] = sorted({int(round(t * FPS)) for t in mc['カット手本']}) if mc else []

mv = ld(f'shirabe/動き表_{V}.json')
if mv:
    cam, naka = {}, {}
    for r in mv:
        if 'ref' not in r or 't' not in r: continue
        f0 = int(round(r['t'] * FPS)); cam[str(f0)] = dict(G=r['ref']['G'], n=r['frames']); naka[str(f0)] = r['ref']['L']
    S['camera'] = dict(kind='G', v=cam); S['naka'] = naka; S['src_camera'] = f'動き表_{V} ref.G（px/コマ・0.5 未満＝止まり）'
else: nashi['camera'] = nashi['naka'] = f'shirabe/動き表_{V}.json が無い（motion_kind.py を回すと出る）'

fl = ld('proj/src/flash.json')
if fl: S['hikari'] = [x['f'] for x in fl]; S['src_hikari'] = 'proj/src/flash.json（取りこぼしだけ見る）'
else: nashi['hikari'] = '光るコマの表が無い（または0件）'

caps = [c for c in (ld('proj/src/caps.json') or []) if not c.get('guess')]
if caps:
    S['moji'] = [dict(w=c['w'], f0=c['f0'], f1=c['f1'], box=c['box'], kei=('serif' if c.get('kind') in ('serif', 'italic') else c.get('kind'))) for c in caps]
    S['moji_unit'] = 'word'; S['src_moji'] = 'proj/src/caps.json（guess 以外）'
else: nashi['moji'] = '字の表が無い'
hud = ld('proj/src/hud.json')
if hud: S['hud'] = sorted(map(int, hud))

kk = ld('kouzou/kyoku.json')
if kk: S['kyoku'] = [dict(a=s['a'], b=s['b'], name=(None if s.get('fumei') else s['name']), at0=s.get('at0'), r=s.get('r')) for s in kk]
else: nashi['kyoku'] = 'kouzou/kyoku.json が無い'
hako = ld('oto/hako/hako.json')
if hako:
    S['sfx'] = [round(x['t'], 3) for x in hako.get('3〜5 効果音', [])]
    S['lufs'] = hako.get('7 聞こえ方', {}).get('lufs')
    S['katari'] = bool(hako.get('1 声')); S['src_oto'] = 'oto/hako/hako.json'
else: nashi['sfx'] = nashi['lufs'] = 'oto/hako/hako.json が無い（oto-bunrui の hako.py）'

for k in ('kirikae', 'oto_ato_ms', 'iro', 'sokudo'): nashi.setdefault(k, '最後の版にこの表を出す道具がまだ無い')
S['nashi'] = nashi
OUT = OUT or f'{W}/me_shiken/seikai.json'
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
json.dump(S, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(os.path.basename(W), V, {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in S.items() if k not in ('note', 'nashi') and not k.startswith('src')})
print('  答えなし', list(nashi))

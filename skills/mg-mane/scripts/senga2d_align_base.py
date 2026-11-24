# sabun2 の「位置・大きさ」の差から、場面ごとの土台（z0・ox・oy）を直す（scenes.tsx を書き換える）
# 使い方: python3 tools/align_base.py rikai/<sabun>.json [強さ=1.0]   ※差が大きすぎる場面（形が違う所）は触らん
import json, re, sys
S = json.load(open(sys.argv[1])); k = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
p = 'proj/src/mp/scenes.tsx'; s = open(p).read(); log = []
for o in S:
    nm = o['cut']
    if nm in ('END', 'AN_end') or o['ds'] != o['ds']: continue
    dx, dy, ds = o['dx'], o['dy'], o['ds']
    if abs(ds) > 30 or abs(dx) > 12 or abs(dy) > 12: log.append(f'{nm} 触らん（差が大きい＝形の違い）'); continue
    m = re.search(r"\{key: '" + nm + r"'[^\n]*?z0: ([\d.]+), (?:ox: (-?[\d.]+), oy: (-?[\d.]+), )?", s)
    if not m: continue
    z0 = float(m.group(1)); ox = float(m.group(2) or 0); oy = float(m.group(3) or 0)
    nz = z0 / (1 + k * ds / 100) if abs(ds) > 3 else z0
    nox = ox - k * dx * 19.2 if abs(dx) > 1.5 else ox; noy = oy - k * dy * 10.8 if abs(dy) > 1.5 else oy
    new = m.group(0).replace(m.group(0)[m.group(0).index('z0:'):], f'z0: {nz:.4f}, ox: {nox:.1f}, oy: {noy:.1f}, ')
    s = s.replace(m.group(0), new); log.append(f'{nm} z0 {z0:.3f}→{nz:.3f} ox {ox:.0f}→{nox:.0f} oy {oy:.0f}→{noy:.0f}')
open(p, 'w').write(s); print('\n'.join(log))

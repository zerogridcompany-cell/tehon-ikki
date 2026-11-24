# sabun2 で比べるうちのコマの一覧（カットごと 5 点＋カメラの 2 点）→ 標準出力に「f1,f2,…」
import json, re, numpy as np
RF = json.load(open('rikai/rf.json')); rx = [a for a, b in RF]; ry = [b for a, b in RF]
CUT = [('A_factory', 0)]
for line in open('rikai/zure_kirikae.md'):
    m = re.match(r'\| (\w+) \| (\d+) \|', line)
    if m: CUT.append((m.group(1), int(m.group(2))))
CUT.append(('END', 2691)); F = set()
for i in range(len(CUT) - 1):
    t0, t1 = CUT[i][1] / 30, CUT[i + 1][1] / 30; L = t1 - t0
    for q in (0.1, 0.15, 0.35, 0.55, 0.75, 0.9, 0.92): F.add(int(round(np.interp(t0 + q * L, rx, ry) * 30)))
print(','.join(str(f) for f in sorted(F)))

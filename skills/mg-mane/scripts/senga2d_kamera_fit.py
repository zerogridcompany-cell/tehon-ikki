# kamera_raw.json → rikai/kamera.json（5 点の移動平均でならす・切り替えの 4 コマは頭の値・物の動きに引っぱられたカットは流しを 0）＋ proj/src/mp/kamera.json
import json, numpy as np
R = json.load(open('rikai/kamera_raw.json')); NOPAN = {'AH_tow', 'S_carbon', 'AD_bank', 'Q_path', 'C_twocars', 'H_racecar', 'AA_tractor'}; OUT = {}  # NOPAN＝流しが 40px を超えた所＝物の動き（車が来る・台車・はじける）。寄りと回りだけ使う
for nm, d in R.items():
    k = np.array([x[:5] for x in d['k']], float)
    if len(k) >= 5:
        sm = k.copy()
        for j in range(1, 5):
            sm[:, j] = np.convolve(np.pad(k[:, j], 2, mode='edge'), np.ones(5) / 5, mode='valid')
        sm[0, 1:] = [1, 0, 0, 0]; k = sm
    if nm in NOPAN: k[:, 2:4] = 0
    rows = [[int(d['f0']), 1.0, 0.0, 0.0, 0.0]] + [[int(r[0]), round(r[1], 4), round(r[2], 1), round(r[3], 1), round(r[4], 3)] for r in k]
    OUT[nm] = dict(f0=d['f0'], f1=d['f1'], k=rows)
json.dump(OUT, open('rikai/kamera.json', 'w')); json.dump(OUT, open('proj/src/mp/kamera.json', 'w'))
json.dump(json.load(open('rikai/rf.json')), open('proj/src/mp/rf.json', 'w'))
print(len(OUT), 'カット', sum(len(v['k']) for v in OUT.values()), '点')

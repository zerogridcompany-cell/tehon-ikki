#!/usr/bin/python3
# 測り：python3 tools/sokutei.py <手本.mp4> <うち.mp4> <out.json>
# 動きの量／コマ＝480 幅の灰色の差の平均（nameraka の止まりの線 0.25 と同じ物差し）
# 止まり＝差 < 0.25 のコマ数（頭のコマは除く）。ease の形＝動きの量の山の前（加速）と後（減速）のコマ数（山の 15% を越える所）
import sys, json, cv2, numpy as np
def meas(path):
    cap = cv2.VideoCapture(path); prev = None; d = []
    while True:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(cv2.resize(fr, (480, 270), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None: d.append(float(np.abs(g - prev).mean()))
        prev = g
    d = np.array(d); sm = np.convolve(d, np.ones(3) / 3, mode='same')
    pk = int(np.argmax(sm)); th = sm[pk] * 0.15
    a = pk
    while a > 0 and sm[a - 1] > th: a -= 1
    b = pk
    while b < len(sm) - 1 and sm[b + 1] > th: b += 1
    acc, dec = pk - a, b - pk
    d2 = np.abs(np.diff(sm, 2)); jag = float(d2.max() / (np.abs(np.diff(sm)).mean() + 1e-6))
    return {'frames': int(len(d) + 1), 'motion_mean': round(float(d.mean()), 3), 'motion_median': round(float(np.median(d)), 3),
            'stops_lt_0.25': int((d < 0.25).sum()), 'stop_frames': [int(i + 1) for i in np.where(d < 0.25)[0]][:30],
            'peak_frame': pk + 1, 'peak_motion': round(float(sm[pk]), 3), 'accel_frames': acc, 'decel_frames': dec,
            'ease_shape': 'out（加速短く減速長く）' if dec > acc * 1.3 else ('in（加速長く）' if acc > dec * 1.3 else 'inout（対称）'),
            'jag_ratio': round(jag, 2), 'motion_per_frame': [round(float(x), 3) for x in d]}
r, u, o = sys.argv[1:4]
R = {'tehon': meas(r), 'uchi': meas(u)}
R['diff'] = {'motion_mean_ratio_uchi_over_tehon': round(R['uchi']['motion_mean'] / max(R['tehon']['motion_mean'], 1e-6), 2)}
json.dump(R, open(o, 'w'), ensure_ascii=False, indent=1)
for k in ('tehon', 'uchi'):
    x = R[k]; print(k, {kk: x[kk] for kk in ('motion_mean', 'stops_lt_0.25', 'peak_frame', 'accel_frames', 'decel_frames', 'ease_shape', 'jag_ratio')})

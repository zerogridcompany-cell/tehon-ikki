# rikai/rf.json＝手本の秒→うちの秒の地図（場面の切り替え 40＋場面の中の出来事 24 の「同じ絵」の点を線でつなぐ）
import json, re
A = [(0.0, 0.0)]
for line in open('rikai/zure_kirikae.md'):
    m = re.match(r'\| (\w+) \| (\d+) \| [\d.]+ \| [-\d.]+ \| ([\d.]+) \|', line)
    if m: A.append((int(m.group(2)) / 30, float(m.group(3))))
EV = json.load(open('proj/src/mp/ev.json'))
for line in open('rikai/zure_dekigoto.md'):
    m = re.match(r'\| (\w+) \| (\d+) \|', line)
    if m and m.group(1) in EV: A.append((int(m.group(2)) / 30, EV[m.group(1)]))
E = json.load(open('proj/src/mp/chunks.json'))[-1]['s1'] + 0.26  # 締めの札の頭（Main.tsx END_AT）
A.append((2580 / 30, E)); A.append((89.69, E + 3.69))
A = sorted(set(A))
B = [A[0]]
for a in A[1:]:
    if a[0] > B[-1][0] and a[1] > B[-1][1]: B.append(a)
    else: print('捨てた（順が逆）', a)
json.dump([[round(x, 3), round(y, 3)] for x, y in B], open('rikai/rf.json', 'w')); print(len(B), '点')

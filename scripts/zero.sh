#!/bin/bash
# 差分0の段（10/28 r2）：前の書き出し <版> を測って、時刻・大きさ・動きを数字で0に寄せる。書き出しはせん（最後に1回だけ）
# bash zero.sh <作業> <前の版>   例：bash zero.sh ~/research/tehon-me/r2 r2_v80
W="$1"; V="$2"; T="$(dirname "$0")/tools"; PY=python3
cd "$W" || exit 1
echo "① 動き表（前の書き出し）"; $PY "$T/motion_kind.py" . "${V}_noaudio.mp4" --out shirabe/動き表_before.json | tail -1
echo "①b 欠け表＝手本にある絵がうちで欠け・帯・ぼやけ（🔴のカットは元の大きい原本を探す＝係の指示の型 r2 shirabe/hunt19/指示.md）"; $PY "$T/kakeru.py" . "${V}_noaudio.mp4" --out shirabe/欠け表_before.json --top 30
echo "② 時刻の作り直し（元の動画があるカット・上がった時だけ・ロゴを消したカットは飛ばす）"
$PY - <<'P' > tmp/zero_rt.txt
import json, os
h = json.load(open('src/hi.json'))
for k, v in sorted(h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
    if isinstance(v, dict) and v.get('file') and os.path.exists(v['file']) and os.path.exists(f'cuts/{k}.mp4') and not os.path.exists(f'cuts/{k}.mp4.bak_logo') and not os.path.exists(f'cuts/{k}.mp4.bak_gate'):
        print(k, v['file'])
P
cat tmp/zero_rt.txt | xargs -P 2 -L 1 sh -c "$PY $T/retime.py . \$0 \$1 --write --min 0.003 > tmp/rt_\$0.log 2>&1"
grep -h "^カット" tmp/rt_*.log | sort -t' ' -k2n
echo "③ 大きさ（画素で s・dx・dy を探す＝一番合う所が 1.000・0・0 になるまで）"
ls cuts/*.mp4 | sed 's#cuts/##; s#\.mp4##' | grep -E '^[0-9]+$' | sort -n | xargs -P 3 -I{} sh -c "$PY $T/size_scan.py . {} --write > tmp/scan_{}.log 2>&1"
grep -h "書いた" tmp/scan_*.log | wc -l | xargs echo "書いたカット数"
echo "③b 時刻のずれ（±2コマ・替わる位置が遠くならん時だけ）"; $PY "$T/shift_scan.py" . --write | tail -20
echo "④ MG の一枚絵に手本の動きを写す（止まりをなくす）"; $PY "$T/flow_tx.py" . --force 2>&1 | tail -1
echo "（書き出しの後）色＝$PY $T/color_cut.py . <版>_noaudio.mp4 --write → もう1回書き出す（retime の後は ΔE が増える・r2 v81 2.4→v82 1.9）"
echo "④b 色を明るさ・濃さ・くっきりで合わせ直す（点の当て込みは中身がずれると薄める＝r2 61 濃さ0.36・93 0.12）"; $PY "$T/look_moment.py" . --auto --write | tail -3
echo "⑤ 残りの🔴（書き出しの前の見込み＝カットのファイルで）"; $PY "$T/motion_kind.py" . --cuts --out shirabe/動き表_cuts.json | tail -1

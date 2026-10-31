#!/bin/bash
# 目の道具を1つ直すたびに、答えのある手本ぜんぶで採点し直す（10/31・どの手本でも使える形）
# 使い方：me_kaizen.sh <版> <前の版> "<段のコマンド（{W}＝作業・{REF}＝手本 mp4 に置き換え）>" <作業1> [作業2 …]
#   例：me_kaizen.sh v1 v0 "python3 scripts/miru/kyoku_plus.py {W} {REF}" ~/tehon/a ~/tehon/b
#   各作業に zukan/zukan_<前の版>.json（最初は zukan.json を zukan_v0.json に写す）と me_shiken/seikai.json（seikai_kara.py）が要る
#   出る物：zukan/zukan_<版>.json・me_shiken/kekka_<版>.json・1行ずつの点。上がった物だけ残し、下がった版は前の版に戻して使う
HERE=$(cd "$(dirname "$0")" && pwd); V=$1; P=$2; CMD=$3; shift 3
for W in "$@"; do
  W=$(cd "$W" && pwd); REF=$(ls "$W"/ref/*.mp4 2>/dev/null | head -1); n=$(basename "$W")
  [ -f "$W/me_shiken/seikai.json" ] || { echo "$n ー 答えが無い（seikai_kara.py を先に）"; continue; }
  cp "$W/zukan/zukan_$P.json" "$W/zukan/zukan.json"
  c=${CMD//\{W\}/$W}; c=${c//\{REF\}/$REF}
  ( eval "$c" ) > "$W/zukan/naoshi_$V.log" 2>&1
  cp "$W/zukan/zukan.json" "$W/zukan/zukan_$V.json"
  python3 "$HERE/me_shiken.py" "$W/zukan/zukan.json" "$W/me_shiken/seikai.json" "$W/me_shiken/kekka_$V.json" | head -1 | sed "s/^/$n /"
done

#!/bin/zsh
# YouTube の止めが外れるまで30分ごとに試し、外れたら続きを回す（mini で使う・10/25）
export PATH=$HOME/.local/bin:$PATH YT_SLEEP=10
cd ~/work/tehon-me/r2
until yt-dlp -q --no-warnings --skip-download --print id "https://www.youtube.com/watch?v=ZuKUOBvIKE4" >/dev/null 2>&1; do
  echo "$(date '+%m/%d %H:%M') まだ止められとる" >> resume.log; sleep 1800
done
echo "$(date '+%m/%d %H:%M') 開いた・続きを回す" >> resume.log
ids=$(python3 -c "import json;print(','.join(json.load(open('shirabe/hunt2_yt.json')).keys()))")
rm -f src/found_h2.json
python3 ../tools/find_sources.py . --only $ids --extra shirabe/hunt2_yt.json --per 0 --keep-best --found src/found_h2.json --cand src/cand_h2 > src_h2.log 2>&1
python3 ../tools/hires.py . --found src/found*.json > hires2.log 2>&1
todo=$(python3 -c "import json;print(','.join(map(str,json.load(open('shirabe/unresolved.json')))))")
python3 ../tools/find_sources.py . --only $todo --per 8 --maxdur 1500 --keep-best --found src/found_r3.json --cand src/cand_r3 > src_r3.log 2>&1
python3 ../tools/hires.py . --found src/found*.json >> hires2.log 2>&1
echo "$(date '+%m/%d %H:%M') ALLDONE" >> resume.log

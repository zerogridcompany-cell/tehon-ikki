#!/bin/bash
# Epidemic の効果音をカテゴリの束ごとに：一覧→落とす→指紋→引き算→音は消す（空きを守る）。結果は sfx/fp_cat/<束>.json
cd ~/research/tehon-me/r2/oto; mkdir -p sfx/fp_cat
BUNDLES=(
"designed,user-interface,scifi,swooshes,beeps,computers"
"electricity,communications,musical,cartoon,games,lasers,robots"
"explosions,magic,clocks,alarms,aircraft,glass,destruction"
"machines,mechanical,paper,objects,metal,wood,equipment,tools"
"crowds,voices,human,fire,fireworks,toys,bells,movement,air,weather,wind"
"animals,birds,boats,bullets,ceramics,chains,chemicals,cloth,creatures,dirt-sand,doors,drawers,farts,fight,food-drink,geothermal,gore,guns,horns,ice,leather,liquid-mud,motors,natural-disaster,plastic,rain,rocks,rope,rubber,snow,sports,trains,vegetation,water,weapons,whistles,windows,wings,archived"
"footsteps,ambience,vehicles"
)
i=0
for g in "${BUNDLES[@]}"; do
  i=$((i+1)); [ -f sfx/fp_cat/g$i.done ] && continue
  python3 tools/epidemic_cat.py get "$g" 2>&1 | grep -v -i warn
  python3 - <<PY
import json,os
m=json.load(open('sfx/corpus/E2/_list_cat.json'))
new=[(k,v['url']) for k,v in m.items() if not any(os.path.exists(f'sfx/corpus/{d}/{k}.mp3') for d in ('E2','E3')) and not os.path.exists(f'sfx/fp_cat/seen/{k}')]
open('sfx/corpus/E4/_urls.txt','w').write('\n'.join(f"{k} {u}" for k,u in new)); print('束 $i 新しい', len(new))
PY
  cat sfx/corpus/E4/_urls.txt | xargs -P 8 -n 2 sh -c '[ -s sfx/corpus/E4/$0.mp3 ] || curl -s -m 60 -o sfx/corpus/E4/$0.mp3 "$1"'
  echo "束 $i 落とした $(ls sfx/corpus/E4/ | grep -c mp3)"
  python3 tools/fp.py sfx/residual_m2.wav sfx/corpus/E4 sfx/fp_cat/g$i.json 8 2>&1 | grep -E "^一致"
  python3 tools/fp_verify.py sfx/residual_m2.wav sfx/fp_cat/g$i.json sfx/fp_cat/g${i}v.json 2>&1 | grep -E "^[0-9]" | head -8
  mkdir -p sfx/fp_cat/seen; for f in sfx/corpus/E4/*.mp3; do touch sfx/fp_cat/seen/$(basename $f .mp3); done
  rm -f sfx/corpus/E4/*.mp3; touch sfx/fp_cat/g$i.done; echo "束 $i おわり"
done
echo CATDONE

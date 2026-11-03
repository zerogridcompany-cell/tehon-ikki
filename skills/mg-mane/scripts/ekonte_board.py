#!/usr/bin/env python3
"""絵コンテ（ekonte.json）→ 灰色の箱だけの下書き板 mp4（references/ekonte.md の段4）
  ekonte_board.py <ekonte.json> <out.mp4> [--w 1080 --h 1920 --fps 30] [--voice vo.wav]
  ekonte.json = {"title":"…","kus":[{"ku":"句","t":[始,終],"kousei":"…","mono":[{"what":"題","at":"上中","size":"中","text":"Global Sound"}],"ugoki":"…","waza":[7],"oto":"…"}]}
  --voice があれば音を載せる（句の秒は声から取った物）。左右並び＝ mg_mane.sh kurabe <下書き板> <完成> で
"""
import json, os, subprocess, sys, shutil
a=sys.argv[1:]
if len(a)<2: print(__doc__); sys.exit(1)
src,out=a[0],a[1]; W=1080;H=1920;FPS=30;voice=None
for i,x in enumerate(a):
    if x=='--w': W=int(a[i+1])
    if x=='--h': H=int(a[i+1])
    if x=='--fps': FPS=int(a[i+1])
    if x=='--voice': voice=a[i+1]
d=json.load(open(src)); dur=max(k['t'][1] for k in d['kus'])
P=os.path.expanduser('~/.claude/skills/mg-mane/assets/waza20')
json.dump({'kus':d['kus'],'title':d.get('title','STORYBOARD'),'dur':dur,'fps':FPS,'width':W,'height':H},open(f'{P}/src/ekonte/props.json','w'),ensure_ascii=False)
tmp=os.path.abspath(out)+'.noaudio.mp4' if voice else os.path.abspath(out)
subprocess.run(['npx','remotion','render','src/index.ts','Ekonte',tmp,'--gl=angle','--concurrency=3','--log=error'],cwd=P,check=True)
if voice:
    subprocess.run(['ffmpeg','-v','error','-y','-i',tmp,'-i',voice,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-shortest',out],check=True); os.remove(tmp)
print('できた',out,f'{dur:.2f}s・{len(d["kus"])}場面')

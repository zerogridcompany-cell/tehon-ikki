#!/usr/bin/env python3
"""絵コンテ（ekonte.json）→ 下書き板 mp4（references/ekonte.md の段4）
  ekonte_board.py <ekonte.json> <out.mp4> [--w 1080 --h 1920 --fps 30] [--voice vo.wav] [--words sync.json] [--sheet sheet.png]
  ekonte.json = {"title":"…","kus":[{"ku":"句","t":[始,終],"kousei":"…","mono":[{"what":"題","at":"上中","size":"中","text":"Global Sound"}],"ugoki":"…","waza":[7],"oto":"…","img":"ekonte2/img/s01.png"}]}
  句に img（ekonte.json からの相対か絶対の道）があれば＝「左＝実際の絵・右＝画面／動き／技／音／実物のメモ」の横板（--w 1920 --h 1080 で）。無ければ灰色の箱だけの板（11/3 の型）
  --words＝jimaku-sync の sync.json（[{text,in,out}]）。絵の下に 1 語ずつの字幕を秒のまま出す
  --sheet＝句ごとの絵の一覧（img がある時）を 1 枚の png に
  --voice があれば音を載せる（句の秒は声から取った物）。左右並び＝ mg_mane.sh kurabe <下書き板> <完成> で
"""
import json, os, subprocess, sys, shutil, tempfile
a=sys.argv[1:]
if len(a)<2: print(__doc__); sys.exit(1)
src,out=a[0],a[1]; W=1080;H=1920;FPS=30;voice=None;words=None;sheet=None
for i,x in enumerate(a):
    if x=='--w': W=int(a[i+1])
    if x=='--h': H=int(a[i+1])
    if x=='--fps': FPS=int(a[i+1])
    if x=='--voice': voice=a[i+1]
    if x=='--words': words=a[i+1]
    if x=='--sheet': sheet=a[i+1]
d=json.load(open(src)); dur=max(k['t'][1] for k in d['kus'])
P=os.path.expanduser('~/.claude/skills/mg-mane/assets/waza20')
base=os.path.dirname(os.path.abspath(src))
kus=[dict(k) for k in d['kus']]
pub=None
if any(k.get('img') for k in kus):
    pub=tempfile.mkdtemp(prefix='ekonte_pub_')
    for j,k in enumerate(kus):
        if k.get('img'):
            p=k['img'] if os.path.isabs(k['img']) else os.path.join(base,k['img'])
            name=f'k{j:02d}'+os.path.splitext(p)[1]
            shutil.copy(p,os.path.join(pub,name)); k['img']=name
wl=None
if words:
    wl=[{'text':w['text'],'in':w.get('in',w.get('s0')),'out':w.get('out',w.get('s1'))} for w in json.load(open(words))]
props={'kus':kus,'title':d.get('title','STORYBOARD'),'dur':dur,'fps':FPS,'width':W,'height':H}
if wl: props['words']=wl
json.dump(props,open(f'{P}/src/ekonte/props.json','w'),ensure_ascii=False)
tmp=os.path.abspath(out)+'.noaudio.mp4' if voice else os.path.abspath(out)
cmd=['npx','remotion','render','src/index.ts','Ekonte',tmp,'--gl=angle','--concurrency=3','--log=error']
if pub: cmd.append(f'--public-dir={pub}')
try:
    subprocess.run(cmd,cwd=P,check=True)
    if voice:
        subprocess.run(['ffmpeg','-v','error','-y','-i',tmp,'-i',voice,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-shortest',out],check=True); os.remove(tmp)
finally:
    if pub: shutil.rmtree(pub,ignore_errors=True)
if sheet and any(k.get('img') for k in d['kus']):
    from PIL import Image, ImageDraw, ImageFont
    n=len(d['kus']); cols=4 if n>12 else 3; rows=(n+cols-1)//cols; tw,th=640,360; pad=56
    S=Image.new('RGB',(cols*tw+(cols+1)*16,rows*(th+pad)+16),'#F4F3F0'); dr=ImageDraw.Draw(S)
    try: fnt=ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc',20)
    except Exception: fnt=ImageFont.load_default()
    for j,k in enumerate(d['kus']):
        x=16+(j%cols)*(tw+16); y=16+(j//cols)*(th+pad)
        if k.get('img'):
            p=k['img'] if os.path.isabs(k['img']) else os.path.join(base,k['img'])
            im=Image.open(p).convert('RGB'); r=max(tw/im.width,th/im.height)
            im=im.resize((round(im.width*r),round(im.height*r))); l=(im.width-tw)//2; t=(im.height-th)//2
            S.paste(im.crop((l,t,l+tw,t+th)),(x,y))
        dr.text((x,y+th+8),f"{j+1:02d}  {k['t'][0]:.2f}s  {k['ku'][:44]}",fill='#2a2926',font=fnt)
    S.save(sheet); print('一覧',sheet)
print('できた',out,f'{dur:.2f}s・{len(d["kus"])}場面')

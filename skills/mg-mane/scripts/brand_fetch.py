#!/usr/bin/env python3
"""ロゴ・ブランドの印を「全く同じ物」で持ってくる（画像生成は使わん＝必ず形が変わる）
  brand_fetch.py <名前> [--out 置き場] [--source auto|commons|simpleicons|url] [--url …] [--commons "File 名"]
    名前の例: tiktok / googlemaps / instagram / youtube / x / apple / spotify …
  順（auto）：①Wikimedia Commons の公式そのままの SVG（色つき）②Simple Icons（単色の公式の形・CC0・3,000 ブランド）③--url で公式のブランドページの SVG/PNG
  出る物：<置き場>/<名前>.svg（+ <名前>_<src>.png 512px の見本＝macOS の qlmanage で起こす）・<名前>.json（出所・取った日時）
  🔴 公式の印は商標＝社内の写し・練習は可。本番の広告に他社のロゴを使うなら許可が要る（出所の URL を json に残す）
"""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request
UA={'User-Agent':'Mozilla/5.0 (brand-fetch; zerogrid)'}
COMMONS={  # 名前 → Commons の File 名（色つきの公式そのまま）
 'googlemaps':'Google_Maps_icon_(2020).svg','tiktok':'TikTok_logo.svg','tiktok_icon':'TikTok_Icon.svg','instagram':'Instagram_logo_2022.svg',
 'youtube':'YouTube_full-color_icon_(2017).svg','x':'X_logo_2023.svg','apple':'Apple_logo_black.svg','spotify':'Spotify_icon.svg','google':'Google_%22G%22_logo.svg',
 'line':'LINE_logo.svg','facebook':'Facebook_f_logo_(2019).svg','threads':'Threads_(app)_logo.svg','whatsapp':'WhatsApp.svg','amazon':'Amazon_icon.svg','netflix':'Netflix_2015_N_logo.svg'}
def get(url,binary=True):
    r=urllib.request.Request(url,headers=UA); return urllib.request.urlopen(r,timeout=60).read()
def commons(title):
    q='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','titles':'File:'+title,'prop':'imageinfo','iiprop':'url|mime','format':'json'})
    d=json.loads(get(q))
    for p in d['query']['pages'].values():
        ii=p.get('imageinfo')
        if ii: return ii[0]['url']
def raster(svg,png,size=512):
    d=os.path.dirname(os.path.abspath(png)) or '.'
    subprocess.run(['qlmanage','-t','-s',str(size),'-o',d,svg],capture_output=True)
    cand=os.path.join(d,os.path.basename(svg)+'.png')
    if os.path.exists(cand): os.replace(cand,png); return png
    if subprocess.run(['which','rsvg-convert'],capture_output=True).returncode==0:
        subprocess.run(['rsvg-convert','-w',str(size),'-o',png,svg]); return png
    return None
def main():
    a=sys.argv[1:]
    if not a or a[0].startswith('-'): print(__doc__); sys.exit(1)
    name=a[0].lower(); out='.'; src='auto'; url=None; ctitle=None
    for i,x in enumerate(a):
        if x=='--out': out=a[i+1]
        if x=='--source': src=a[i+1]
        if x=='--url': url=a[i+1]
        if x=='--commons': ctitle=a[i+1]
    os.makedirs(out,exist_ok=True); got=[]
    if src in ('auto','commons'):
        t=ctitle or COMMONS.get(name)
        if t:
            try:
                u=commons(t)
                if u:
                    b=get(u); p=os.path.join(out,f'{name}.svg' if u.lower().endswith('.svg') else f'{name}_commons'+os.path.splitext(u)[1]); open(p,'wb').write(b); got.append(('commons',u,p))
            except Exception as e: print('commons 取れん:',e)
    if src in ('auto','simpleicons'):
        try:
            b=get(f'https://cdn.simpleicons.org/{name}')
            if b.startswith(b'<svg'):
                p=os.path.join(out,f'{name}_simpleicons.svg'); open(p,'wb').write(b); got.append(('simpleicons',f'https://cdn.simpleicons.org/{name}',p))
        except Exception as e: print('simpleicons 取れん:',e)
    if url:
        b=get(url); p=os.path.join(out,f'{name}_official'+os.path.splitext(urllib.parse.urlparse(url).path)[1]); open(p,'wb').write(b); got.append(('url',url,p))
    if not got: print('🔴 取れんかった。公式のブランドページ（例 tiktok.com/about/brand-assets）から SVG を落として --url か手で置く'); sys.exit(2)
    rec=[]
    for s,u,p in got:
        png=raster(p,p.rsplit('.',1)[0]+'.png') if p.endswith('.svg') else None
        rec.append({'source':s,'url':u,'file':p,'png':png}); print(f'✅ {s}: {p}' + (f' → 見本 {png}' if png else ''))
    json.dump({'name':name,'taken':time.strftime('%Y-%m-%d %H:%M'),'items':rec,'note':'商標＝本番の広告に使うなら許可。社内の写し・練習は可'},open(os.path.join(out,f'{name}.json'),'w'),indent=1,ensure_ascii=False)
if __name__=='__main__': main()

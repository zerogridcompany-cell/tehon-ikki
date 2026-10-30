# Epidemic Sound の効果音をカテゴリ（genres=）ごとに全ページ取って、試聴 mp3 の一覧に足す（1検索1万本の壁をカテゴリで割って越える）
# 使い方: python3 epidemic_cat.py cats   … カテゴリの一覧と本数を _cats.json に
#         python3 epidemic_cat.py get <slug,…|ALL> … そのカテゴリを全ページ取る
import json, os, sys, re
from playwright.sync_api import sync_playwright
OUT=os.path.expanduser('~/research/tehon-me/r2/oto/sfx/corpus/E2'); MAN=OUT+'/_list_cat.json'; CATS=OUT+'/_cats.json'
man=json.load(open(MAN)) if os.path.exists(MAN) else {}
# 言葉で取った一覧（別の係が書く）は読むだけ＝同じ物を二度取らん
old=set(json.load(open(OUT+'/_list.json')))
def fetch(pg,q):
    for tr in range(8):
        try: d=pg.evaluate("async u=>{const r=await fetch(u,{credentials:'include'});return r.ok?await r.json():{err:r.status}}", q)
        except Exception as e:
            print('取れん・開き直す',str(e)[:60],flush=True); pg.wait_for_timeout(30000*(tr+1))
            try: pg.goto('https://www.epidemicsound.com/sound-effects/',timeout=90000); pg.wait_for_timeout(4000)
            except Exception: pass
            continue
        if d.get('err')==429: print('429 待つ',flush=True); pg.wait_for_timeout(60000*(tr+1)); continue
        return d
    return {'err':'gaveup'}
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp('http://127.0.0.1:9336'); pg=b.contexts[0].new_page()
    try:
        if sys.argv[1]=='cats':
            pg.goto('https://www.epidemicsound.com/sound-effects/categories/',timeout=90000); pg.wait_for_timeout(5000)
            links=pg.evaluate("()=>[...document.querySelectorAll('a')].map(a=>a.href)")
            slugs=sorted(set('--'.join(m.group(1).strip('/').split('/')) for h in links for m in [re.search(r'/sound-effects/categories/(.+)',h)] if m and m.group(1).strip('/')))
            cats={}
            for s in slugs:
                if '--' in s: continue
                d=fetch(pg,f"/json/search/sfx/?order=desc&page=1&sort=relevance&term=&genres={s}"); pg.wait_for_timeout(1500)
                cats[s]=dict(n=d.get('meta',{}).get('totalHits'),subs=[x for x in slugs if x.startswith(s+'--')])
                print(s,cats[s]['n'],len(cats[s]['subs']),flush=True)
            json.dump(cats,open(CATS,'w'),ensure_ascii=False,indent=0)
        else:
            pg.goto('https://www.epidemicsound.com/sound-effects/',timeout=90000); pg.wait_for_timeout(4000)
            cats=json.load(open(CATS)); want=list(cats) if sys.argv[2]=='ALL' else sys.argv[2].split(',')
            for c in want:
                # 1万本を超えるカテゴリは下のカテゴリに割る
                todo=[c] if (cats.get(c,{}).get('n') or 0)<10000 else cats[c]['subs']
                for s in todo:
                    n0=len(man); tp=1; page=1
                    while page<=tp:
                        d=fetch(pg,f"/json/search/sfx/?order=desc&page={page}&sort=relevance&term=&genres={s}")
                        if 'err' in d: print(s,'エラー',d['err'],flush=True); break
                        pg.wait_for_timeout(2500); tp=d['meta'].get('totalPages',1)
                        for t in d['entities'].get('tracks',{}).values():
                            u=((t.get('stems') or {}).get('full') or {}).get('lqMp3Url')
                            if u and str(t['id']) not in man and str(t['id']) not in old: man[str(t['id'])]=dict(title=t['title'],tag=[g.get('slug') for g in t.get('genres',[])],ms=t.get('durationMs'),url=u,term='cat:'+s)
                        page+=1
                    json.dump(man,open(MAN,'w'),ensure_ascii=False,indent=0)
                    print(s,'全',tp,'ページ・新しく',len(man)-n0,'本・合計',len(man),flush=True)
    finally: pg.close()

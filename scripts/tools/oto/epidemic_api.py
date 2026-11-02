# Epidemic Sound（ログイン済みの Claude 用 Dia）の /json/search/sfx/ を言葉ごと・全ページたたいて、試聴 mp3 のアドレスと名前を集める
import json, os, sys, urllib.parse
from playwright.sync_api import sync_playwright
OUT=os.path.expanduser(os.environ.get('TI_SFX_CORPUS', os.path.join(os.environ.get('TI_WORK_ROOT','~/tehon-ikki-work'),'oto/sfx/corpus/E2'))); os.makedirs(OUT,exist_ok=True)
MAN=OUT+'/_list.json'; man=json.load(open(MAN)) if os.path.exists(MAN) else {}
terms=sys.argv[1].split(','); MAXP=int(sys.argv[2]) if len(sys.argv)>2 else 20
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp('http://127.0.0.1:9336'); pg=b.contexts[0].new_page()
    pg.goto('https://www.epidemicsound.com/sound-effects/',timeout=90000); pg.wait_for_timeout(4000)
    try:
        for term in terms:
            n0=len(man); tp=1; page=1
            while page<=min(tp,MAXP):
                q=f"/json/search/sfx/?order=desc&page={page}&sort=relevance&term={urllib.parse.quote(term)}"
                for tr in range(8):
                    try:
                        d=pg.evaluate("async u=>{const r=await fetch(u,{credentials:'include'});return r.ok?await r.json():{err:r.status}}", q)
                    except Exception as e:
                        # ネットが切れた時はページを開き直して待つ
                        print(term,'取れん・開き直す',str(e)[:60],flush=True); pg.wait_for_timeout(30000*(tr+1))
                        try: pg.goto('https://www.epidemicsound.com/sound-effects/',timeout=90000); pg.wait_for_timeout(4000)
                        except Exception: pass
                        d={'err':'net'}; continue
                    if d.get('err')==429: print(term,'429 待つ',flush=True); pg.wait_for_timeout(60000*(tr+1)); continue
                    break
                if 'err' in d: print(term,'エラー',d['err']); break
                pg.wait_for_timeout(2500)
                tp=d['meta'].get('totalPages',1)
                for t in d['entities'].get('tracks',{}).values():
                    st=(t.get('stems') or {}).get('full') or {}
                    u=st.get('lqMp3Url')
                    if u and str(t['id']) not in man: man[str(t['id'])]=dict(title=t['title'],tag=[g.get('slug') for g in t.get('genres',[])],ms=t.get('durationMs'),url=u,term=term)
                page+=1
            json.dump(man,open(MAN,'w'),ensure_ascii=False,indent=0)
            print(term,'全',tp,'ページ・新しく',len(man)-n0,'本・合計',len(man),flush=True)
    finally: pg.close()

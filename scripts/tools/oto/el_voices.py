# ElevenLabs の既製の声（公式＋みんなの声）の見本を集める（見本は無料）
import json, os, sys, urllib.request, urllib.parse, time
K=open(os.path.expanduser('~/.elevenlabs_key')).read().strip()
def get(url):
    r=urllib.request.Request(url,headers={'xi-api-key':K}); return json.load(urllib.request.urlopen(r,timeout=60))
out=[]
for v in get('https://api.elevenlabs.io/v1/voices').get('voices',[]):
    if v.get('category') in ('premade',) and v.get('preview_url'):
        out.append({'id':v['voice_id'],'name':v['name'],'src':'premade','preview':v['preview_url'],'labels':v.get('labels')})
seen={o['id'] for o in out}
qs=[dict(gender='male',language='en',use_cases=u,sort='usage_character_count_1y') for u in ['narrative_story','social_media','informative_educational','conversational','characters_animation']]
qs+= [dict(gender='male',language='en',search=s) for s in ['documentary','storyteller','deep narrator','youtube narrator','motivational','faceless']]
for q in qs:
    for page in range(3):
        q2=dict(q,page_size=100,page=page)
        try: d=get('https://api.elevenlabs.io/v1/shared-voices?'+urllib.parse.urlencode(q2))
        except Exception as e: print('err',q,e); break
        for v in d.get('voices',[]):
            if v['voice_id'] in seen or not v.get('preview_url'): continue
            seen.add(v['voice_id']); out.append({'id':v['voice_id'],'name':v['name'],'src':'shared','public_owner_id':v.get('public_owner_id'),'preview':v['preview_url'],'uses':v.get('usage_character_count_1y'),'accent':v.get('accent'),'age':v.get('age')})
        if not d.get('has_more'): break
        time.sleep(0.3)
json.dump(out,open('narr/voices.json','w'),ensure_ascii=False,indent=0)
print(len(out),'声')

#!/usr/bin/env python3
"""画面に映っとる物を全部数字に（11/3 依頼者「光の当たり方・物の位置・壁・高さ…画面上の物を全部数値化して重ねる」）
  gamen.py measure <mp4> <out.json> [--step 6] [--kukan "名:a-b,…"]   … コマごとに測って区間ごとにまとめる
  gamen.py cmp <手本.json> <うち.json> [--md 出す.md] [--png 出す.png]       … 差の表と重ねの絵
測る物（1コマごと）：
  光＝地の明るさの地図（48x27 の L）・光の中心（明るい所の重心 %）・山の明るさ・落ち方（中心から 25%/50% 離れた所の L の比）・向き（一番暗い方向の角度）・周辺減光（隅/中心）・光の色（a*,b*）
  にじみ＝明るい物の縁の外の光の広がり（L が縁の 10% に落ちる距離 px・縁の外 20px の明るさ）
  物＝明るい塊の箱（上位 8・%）・平均色・面の向き（縁の向きの割合＝横/縦/斜め）
  字幕の帯（下 8%）は外さん＝全部測る（手本の隠れた帯があるなら両方同じ埋めを先に）
"""
import sys, json, cv2, numpy as np
def lab(im): return cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)*np.array([100/255,1,1],np.float32)-np.array([0,128,128],np.float32)
def measure_frame(im):
    H,W=im.shape[:2]; L=lab(im); Lc=L[:,:,0]
    small=cv2.resize(Lc,(48,27),interpolation=cv2.INTER_AREA)
    bg=cv2.GaussianBlur(Lc,(0,0),W/40)                      # 大きなぼかし＝地の光
    # 光の中心＝ぼかした地の上位 2% の重心
    thr=np.percentile(bg,98); ys,xs=np.nonzero(bg>=thr); cx,cy=float(xs.mean()/W),float(ys.mean()/H); peak=float(bg.max())
    def at(fx,fy):
        x=int(np.clip(fx*W,0,W-1)); y=int(np.clip(fy*H,0,H-1)); return float(bg[y,x])
    r25=np.mean([at(cx+0.25*np.cos(a),cy+0.25*np.sin(a)) for a in np.linspace(0,2*np.pi,8,endpoint=False)])
    r50=np.mean([at(cx+0.5*np.cos(a),cy+0.5*np.sin(a)) for a in np.linspace(0,2*np.pi,8,endpoint=False)])
    ang=float(np.degrees(np.arctan2((cy-0.5)*H,(cx-0.5)*W)))   # 光の中心が画面の真ん中からどっちにあるか（真ん中なら 0 付近・弱い）
    corners=np.mean([bg[:H//8,:W//8].mean(),bg[:H//8,-W//8:].mean(),bg[-H//8:,:W//8].mean(),bg[-H//8:,-W//8:].mean()]); vig=float(corners/max(bg[H//2-H//8:H//2+H//8,W//2-W//8:W//2+W//8].mean(),1e-3))
    mid=(Lc>15)&(Lc<70); a_=float(L[:,:,1][mid].mean()) if mid.any() else 0.0; b_=float(L[:,:,2][mid].mean()) if mid.any() else 0.0
    # にじみ＝明るい物（L>60 の小さいぼかし）の縁から外へ
    obj=(cv2.GaussianBlur(Lc,(0,0),1.5)>60).astype(np.uint8)
    halo_r=0.0; halo_l=0.0
    if obj.any():
        dist=cv2.distanceTransform(1-obj,cv2.DIST_L2,5); edgeL=float(Lc[(dist>0)&(dist<=2)].mean()) if ((dist>0)&(dist<=2)).any() else 0
        bgL=float(np.percentile(Lc[dist>W/8],50)) if (dist>W/8).any() else float(Lc.min())
        prof=[float(Lc[(dist>d)&(dist<=d+4)].mean()) if ((dist>d)&(dist<=d+4)).any() else bgL for d in range(0,400,4)]
        target=bgL+0.1*(edgeL-bgL); halo_r=float(next((d for d,v in zip(range(0,400,4),prof) if v<=target),400)); halo_l=float(prof[5]-bgL) if len(prof)>5 else 0
    # 物の箱
    n,labm,st,cen=cv2.connectedComponentsWithStats(cv2.morphologyEx(obj,cv2.MORPH_OPEN,np.ones((5,5),np.uint8)))
    boxes=[]
    for k in range(1,n):
        x,y,w,h,a=st[k]
        if a<W*H*0.0005: continue
        m=labm==k; boxes.append({'x':round(x/W,3),'y':round(y/H,3),'w':round(w/W,3),'h':round(h/H,3),'L':round(float(Lc[m].mean()),1),'a':round(float(L[:,:,1][m].mean()),1),'b':round(float(L[:,:,2][m].mean()),1),'area':round(a/(W*H),4)})
    boxes=sorted(boxes,key=lambda b:-b['area'])[:8]
    # 面の向き（縁の向きの割合）
    gxs=cv2.Sobel(Lc,cv2.CV_32F,1,0); gys=cv2.Sobel(Lc,cv2.CV_32F,0,1); mag=np.hypot(gxs,gys); strong=mag>np.percentile(mag,95)
    th=np.degrees(np.arctan2(gys[strong],gxs[strong]))%180; hist=np.histogram(th,bins=[0,22.5,67.5,112.5,157.5,180])[0].astype(float); hist[0]+=hist[-1]; hist=hist[:-1]; hist/=max(hist.sum(),1)
    return {'hikari':{'cx':round(cx,3),'cy':round(cy,3),'peak':round(peak,1),'r25':round(r25/max(peak,1e-3),3),'r50':round(r50/max(peak,1e-3),3),'ang':round(ang,0),'vig':round(vig,3),'a':round(a_,1),'b':round(b_,1),'meanL':round(float(Lc.mean()),1)},
            'nijimi':{'r_px':halo_r,'l20':round(halo_l,1)},'mono':boxes,'men':{'yoko':round(hist[0],2),'naname1':round(hist[1],2),'tate':round(hist[2],2),'naname2':round(hist[3],2)},'chizu':np.round(small,0).astype(int).tolist()}
def measure(src,out,step,kukan):
    cap=cv2.VideoCapture(src); n=int(cap.get(7)); rows=[]; k=0
    while True:
        ok,im=cap.read()
        if not ok: break
        if k%step==0: r=measure_frame(im); r['f']=k; rows.append(r)
        k+=1
    res={'src':src,'n':n,'step':step,'frames':rows}
    if kukan:
        ks=[]
        for part in kukan.split(','):
            name,rng=part.split(':'); a,b=map(int,rng.split('-')); sel=[r for r in rows if a<=r['f']<=b]
            if not sel: continue
            def m(path):
                v=[r[path[0]][path[1]] for r in sel]; return round(float(np.mean(v)),3)
            ks.append({'name':name,'a':a,'b':b,'hikari':{key:m(('hikari',key)) for key in ['cx','cy','peak','r25','r50','ang','vig','a','b','meanL']},'nijimi':{'r_px':m(('nijimi','r_px')),'l20':m(('nijimi','l20'))},'men':{key:m(('men',key)) for key in ['yoko','naname1','tate','naname2']},'mono_n':round(float(np.mean([len(r['mono']) for r in sel])),1)})
        res['kukan']=ks
    json.dump(res,open(out,'w'))
    print(f'測った {len(rows)} コマ → {out}')
    if kukan:
        print('区間 | 光の中心(%) | 山L | 落ち r25/r50 | 向き° | 減光 | 色a/b | にじみ px/明るさ | 物の数')
        for q in res['kukan']:
            h=q['hikari']; print(f"{q['name']} | {h['cx']*100:.0f},{h['cy']*100:.0f} | {h['peak']:.0f} | {h['r25']:.2f}/{h['r50']:.2f} | {h['ang']:.0f} | {h['vig']:.2f} | {h['a']:+.0f}/{h['b']:+.0f} | {q['nijimi']['r_px']:.0f}/{q['nijimi']['l20']:.0f} | {q['mono_n']}")
def cmp(A,B,md,png):
    A=json.load(open(A)); B=json.load(open(B)); lines=['# 画面の差（手本｜うち）','','| 区間 | 光の中心のずれ(%) | 山L 手本→うち | 落ち r50 | 向き° | 減光 | 色 a/b | にじみ px | 判定 |','|---|---|---|---|---|---|---|---|---|']
    kb={q['name']:q for q in B.get('kukan',[])}; red=0
    for q in A.get('kukan',[]):
        p=kb.get(q['name']);
        if not p: continue
        h,g=q['hikari'],p['hikari']; dc=np.hypot(h['cx']-g['cx'],h['cy']-g['cy'])*100; dpk=g['peak']-h['peak']; dr=g['r50']-h['r50']; dang=abs((h['ang']-g['ang']+180)%360-180) if np.hypot(h['cx']-0.5,h['cy']-0.5)>0.08 else 0; dvig=g['vig']-h['vig']; dab=np.hypot(h['a']-g['a'],h['b']-g['b']); rn=p['nijimi']['r_px']/max(q['nijimi']['r_px'],1)
        bad=(dc>5)+(abs(dpk)>6)+(abs(dr)>0.1)+(dang>30 and h['r50']<0.9)+(abs(dvig)>0.1)+(dab>4)+(rn<0.6 or rn>1.6); j='🔴' if bad>=2 else ('🟡' if bad==1 else '🟢'); red+=j=='🔴'
        lines.append(f"| {q['name']} | {dc:.1f} | {h['peak']:.0f}→{g['peak']:.0f} | {h['r50']:.2f}→{g['r50']:.2f} | {h['ang']:.0f}→{g['ang']:.0f} | {h['vig']:.2f}→{g['vig']:.2f} | {h['a']:+.0f}/{h['b']:+.0f}→{g['a']:+.0f}/{g['b']:+.0f} | {q['nijimi']['r_px']:.0f}→{p['nijimi']['r_px']:.0f} | {j} |")
    lines.append(f'\n🔴 {red}（目安：中心のずれ ≤5%・山 ±6・落ち ±0.1・向き ±30°・減光 ±0.1・色 ±4・にじみ 0.6〜1.6倍。2つ外れたら🔴）')
    txt='\n'.join(lines); print(txt)
    if md: open(md,'w').write(txt+'\n')
    if png:   # 重ね＝区間の代表コマの地の明るさの地図（手本｜うち｜差）
        tiles=[]
        fa={r['f']:r for r in A['frames']}; fb={r['f']:r for r in B['frames']}
        for q in A.get('kukan',[]):
            f=min((x for x in fa if q['a']<=x<=q['b']),default=None)
            if f is None or f not in fb: continue
            a=np.array(fa[f]['chizu'],float); b=np.array(fb[f]['chizu'],float); d=np.abs(a-b)
            row=np.hstack([a,b,d*2]); tiles.append(cv2.resize(row,(3*192,108),interpolation=cv2.INTER_NEAREST))
        img=np.clip(np.vstack(tiles)*2.55,0,255).astype(np.uint8); cv2.imwrite(png,img); print('重ね→',png,'（左＝手本・中＝うち・右＝差×2・1段＝1区間）')
if __name__=='__main__':
    a=sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    if a[0]=='measure':
        step=6; kukan=None
        for i,x in enumerate(a):
            if x=='--step': step=int(a[i+1])
            if x=='--kukan': kukan=a[i+1]
        measure(a[1],a[2],step,kukan)
    elif a[0]=='cmp':
        md=png=None
        for i,x in enumerate(a):
            if x=='--md': md=a[i+1]
            if x=='--png': png=a[i+1]
        cmp(a[1],a[2],md,png)

#!/usr/bin/env python3
"""うちが描いた印が公式と同じ形か（IoU）＝門
  brand_check.py <公式.svg か .png> <うちの画像 か 動画> [--frame N] [--box x,y,w,h] [--thr 0.97] [--out 比べ.png]
  公式を 512px に起こし、うちの箱（無ければ色のある所の外接の箱）を同じ大きさに合わせて、形（アルファ か 地と違う画素）の IoU と色の ΔE（主な色）を出す。IoU < thr は 🔴
"""
import sys, os, subprocess, numpy as np, cv2
def load_official(p):
    if p.lower().endswith('.svg'):
        png=p.rsplit('.',1)[0]+'_512.png'; d=os.path.dirname(os.path.abspath(p))
        subprocess.run(['qlmanage','-t','-s','512','-o',d,p],capture_output=True); c=os.path.join(d,os.path.basename(p)+'.png')
        if os.path.exists(c): os.replace(c,png)
        p=png
    im=cv2.imread(p,cv2.IMREAD_UNCHANGED)
    if im.ndim==2: im=cv2.cvtColor(im,cv2.COLOR_GRAY2BGR)
    if im.shape[2]==4 and (im[:,:,3]<127).any(): a=im[:,:,3]>127          # 透明がある PNG＝アルファが形
    else:                                                                   # qlmanage は白い地を敷く＝縁の色と違う所が形
        rgb=im[:,:,:3]; bg=np.median(np.r_[rgb[0],rgb[-1],rgb[:,0],rgb[:,-1]].reshape(-1,3),0)
        a=np.abs(rgb.astype(int)-bg).sum(2)>60
    return im[:,:,:3],a
def load_ours(p,frame,box):
    if p.lower().endswith(('.mp4','.mov')):
        cap=cv2.VideoCapture(p); cap.set(1,frame); ok,im=cap.read()
    else: im=cv2.imread(p)
    if box: x,y,w,h=box; im=im[y:y+h,x:x+w]
    bg=np.median(np.r_[im[0],im[-1],im[:,0],im[:,-1]].reshape(-1,3),0)
    a=(np.abs(im.astype(int)-bg).sum(2)>60).astype(np.uint8)
    a=cv2.morphologyEx(a,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(a)      # 一番大きい塊＝印（地の粒・影は捨てる）
    if n>1:
        k=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); a=(lab==k)
        a=cv2.morphologyEx(a.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))>0
    else: a=a>0
    return im,a
def bbox(a):
    ys,xs=np.nonzero(a); return xs.min(),ys.min(),xs.max()+1,ys.max()+1
def fit(im,a,S=512):
    x0,y0,x1,y1=bbox(a); im=im[y0:y1,x0:x1]; a=a[y0:y1,x0:x1]; h,w=a.shape; s=S/max(h,w)
    im=cv2.resize(im,(max(1,int(w*s)),max(1,int(h*s))),interpolation=cv2.INTER_AREA); a=cv2.resize(a.astype(np.uint8),(im.shape[1],im.shape[0]),interpolation=cv2.INTER_AREA)>0
    cv=np.zeros((S,S,3),np.uint8); ca=np.zeros((S,S),bool); oy=(S-im.shape[0])//2; ox=(S-im.shape[1])//2
    cv[oy:oy+im.shape[0],ox:ox+im.shape[1]]=im; ca[oy:oy+a.shape[0],ox:ox+a.shape[1]]=a; return cv,ca
def main():
    a=sys.argv[1:]; frame=0; box=None; thr=0.97; out=None
    for i,x in enumerate(a):
        if x=='--frame': frame=int(a[i+1])
        if x=='--box': box=tuple(int(v) for v in a[i+1].split(','))
        if x=='--thr': thr=float(a[i+1])
        if x=='--out': out=a[i+1]
    oi,oa=load_official(a[0]); ui,ua=load_ours(a[1],frame,box)
    O,OA=fit(oi,oa); U,UA=fit(ui,ua)
    # 少しの位置ずれは許す（±6px で一番合う所）
    best=0
    for dy in range(-6,7,2):
        for dx in range(-6,7,2):
            sh=np.roll(np.roll(UA,dy,0),dx,1); i=(OA&sh).sum(); u=(OA|sh).sum(); best=max(best,i/u if u else 0)
    # 主な色（印の中の画素の平均・Lab の ΔE）
    def lab(im,m): return cv2.cvtColor(np.uint8([[im[m].mean(0)]]),cv2.COLOR_BGR2LAB)[0,0].astype(float)*[100/255,1,1]
    de=np.linalg.norm(lab(O,OA)-lab(U,UA))
    print(f"形の IoU {best:.3f}（{'🟢' if best>=thr else '🔴'} 線 {thr}）・主な色の ΔE {de:.1f}")
    if out:
        ov=O.copy(); ov[UA&~OA]=(0,0,255); ov[OA&~UA]=(255,0,0)
        cv2.imwrite(out,np.hstack([O,U,ov])); print('比べ（公式｜うち｜差：赤＝うちだけ・青＝公式だけ）→',out)
    sys.exit(0 if best>=thr else 2)
if __name__=='__main__': main()

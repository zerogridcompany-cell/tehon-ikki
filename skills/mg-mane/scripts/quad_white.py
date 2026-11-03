# 白い画面のコマで、画面の4辺を直線で当てて4隅を出す＋カメラが止まっとるか（上の景色の位相相関）
import cv2, numpy as np, json, sys
src=sys.argv[1]; cap=cv2.VideoCapture(src); n=int(cap.get(7))
def frame(f):
    cap.set(1,f); ok,im=cap.read(); return im
def corners(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    m=(g>150).astype(np.uint8); m[:650,:]=0; m[1320:,:]=0
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    c=max(cs,key=cv2.contourArea); mask=np.zeros_like(m); cv2.drawContours(mask,[c],-1,1,-1)
    ys,xs=np.nonzero(mask)
    # 各辺の点を集めて直線を当てる
    rows=np.unique(ys); L=[];R=[]
    for y in rows:
        xx=xs[ys==y]; L.append((xx.min(),y)); R.append((xx.max(),y))
    cols=np.unique(xs); T=[];B=[]
    for x in cols:
        yy=ys[xs==x]; T.append((x,yy.min())); B.append((x,yy.max()))
    def fit(pts,trim=0.08):
        p=np.array(pts,float); k=int(len(p)*trim); p=p[k:len(p)-k]
        # 外れ値を落として2回
        for _ in range(2):
            vx,vy,x0,y0=cv2.fitLine(p.astype(np.float32),cv2.DIST_HUBER,0,0.01,0.01).ravel()
            d=np.abs((p[:,0]-x0)*vy-(p[:,1]-y0)*vx); p=p[d<np.percentile(d,80)+1]
        return (vx,vy,x0,y0)
    def inter(a,b):
        vx1,vy1,x1,y1=a; vx2,vy2,x2,y2=b
        A=np.array([[vx1,-vx2],[vy1,-vy2]]); t=np.linalg.solve(A,[x2-x1,y2-y1])
        return [float(x1+vx1*t[0]),float(y1+vy1*t[0])]
    l,r,t,b=fit(L),fit(R),fit(T),fit(B)
    return [inter(t,l),inter(t,r),inter(b,r),inter(b,l)]
res={}
for f in [0,10,20,30,40,45]:
    res[f]=corners(frame(f)); print(f,np.array(res[f]).round(1).tolist())
# カメラの止まり：上の景色（0〜600行）の位相相関
base=cv2.cvtColor(frame(0),cv2.COLOR_BGR2GRAY)[80:600,:].astype(np.float32)
win=cv2.createHanningWindow(base.shape[::-1],cv2.CV_32F)
sh={}
for f in range(0,n,25):
    g=cv2.cvtColor(frame(f),cv2.COLOR_BGR2GRAY)[80:600,:].astype(np.float32)
    (dx,dy),r=cv2.phaseCorrelate(base,g,win); sh[f]=(round(dx,2),round(dy,2),round(r,2))
print('shift vs f0 (dx,dy,resp):',sh)
json.dump({'corners':res,'shift':sh},open(sys.argv[2],'w'))

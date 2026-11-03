# モニター撮りの手本 → 画面だけを毎コマ 1920x1080 に起こす（11/3 tehonI）
#   使い方: /usr/bin/python3 rectify_monitor.py <撮った.mp4> <出す.mp4> [fps=30000/1001] [--quad x1,y1,x2,y2,x3,y3,x4,y4]
#   四隅（左上・右上・右下・左下）は --quad で渡す。無ければ quad_white.py で白い画面のコマから当てた値を使う（先に quad_white.py <撮った.mp4> <out.json> で測る）
#   景色（画面の外）を LK＋homography で追って手持ちの揺れを戻し、白い画面のコマでは4辺を直に当て、追いとの差 6px 超は捨てて savgol で滑らかに
import cv2, numpy as np, json, sys, subprocess
from scipy.signal import savgol_filter
src=sys.argv[1]; out=sys.argv[2]; fps=sys.argv[3] if len(sys.argv)>3 else '30000/1001'
W,H=1920,1080
cap=cv2.VideoCapture(src); n=int(cap.get(7)); fw=int(cap.get(3)); fh=int(cap.get(4))
qa=[a for a in sys.argv if a.startswith('--quad')]
if qa:
    v=[float(x) for x in sys.argv[sys.argv.index(qa[0])+1].split(',')]; Q0=np.array(v,np.float32).reshape(4,2)
else:
    Q0=np.array([[59.5,730.0],[1055.8,716.9],[1041.6,1266.2],[82.3,1264.6]],np.float32)  # tehonI（1080x1920 の縦動画）の値＝他の手本では --quad を渡す
mask=np.full((fh,fw),255,np.uint8)
cv2.fillPoly(mask,[(Q0+np.array([[-30,-30],[30,-30],[30,30],[-30,30]])).astype(np.int32)],0)
# 画面と一緒に動かん物（TikTok の字幕の板）・中身が変わる物（下のノートの小窓・タイムライン）は追いから外す＝手本ごとに直す
mask[590:710,250:830]=0; mask[1320:1500,470:800]=0; mask[1520:1740,:]=0; mask[1760:,:]=0
ok,f0=cap.read(); g0=cv2.cvtColor(f0,cv2.COLOR_BGR2GRAY)
p0=cv2.goodFeaturesToTrack(g0,2000,0.01,8,mask=mask,blockSize=7)
def corners(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY); m=(g>150).astype(np.uint8); m[:650,:]=0; m[1320:,:]=0
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    if not cs: return None
    c=max(cs,key=cv2.contourArea)
    if cv2.contourArea(c)<0.9*cv2.contourArea(Q0.astype(np.int32)): return None
    mk=np.zeros_like(m); cv2.drawContours(mk,[c],-1,1,-1); ys,xs=np.nonzero(mk)
    L=[];R=[];T=[];B=[]
    for y in np.unique(ys):
        xx=xs[ys==y]; L.append((xx.min(),y)); R.append((xx.max(),y))
    for x in np.unique(xs):
        yy=ys[xs==x]; T.append((x,yy.min())); B.append((x,yy.max()))
    def fit(pts,trim=0.08):
        p=np.array(pts,float); k=int(len(p)*trim); p=p[k:len(p)-k]
        for _ in range(2):
            vx,vy,x0,y0=cv2.fitLine(p.astype(np.float32),cv2.DIST_HUBER,0,0.01,0.01).ravel()
            d=np.abs((p[:,0]-x0)*vy-(p[:,1]-y0)*vx); p=p[d<np.percentile(d,80)+1]
        return (vx,vy,x0,y0)
    def inter(a,b):
        vx1,vy1,x1,y1=a; vx2,vy2,x2,y2=b
        t=np.linalg.solve(np.array([[vx1,-vx2],[vy1,-vy2]]),[x2-x1,y2-y1]); return [float(x1+vx1*t[0]),float(y1+vy1*t[0])]
    l,r,t,b=fit(L),fit(R),fit(T),fit(B)
    return np.array([inter(t,l),inter(t,r),inter(b,r),inter(b,l)],np.float32)
lk=dict(winSize=(25,25),maxLevel=4,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,0.01))
track=[];direct=[];frames=[]
cap.set(1,0)
while True:
    ok,im=cap.read()
    if not ok: break
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    p1,st,_=cv2.calcOpticalFlowPyrLK(g0,g,p0,None,**lk); p0b,st2,_=cv2.calcOpticalFlowPyrLK(g,g0,p1,None,**lk)
    good=(st.ravel()==1)&(st2.ravel()==1)&(np.linalg.norm((p0-p0b).reshape(-1,2),axis=1)<0.8)
    Hm,inl=cv2.findHomography(p0[good].reshape(-1,2),p1[good].reshape(-1,2),cv2.RANSAC,1.5)
    track.append(cv2.perspectiveTransform(Q0.reshape(1,-1,2),Hm).reshape(-1,2)); direct.append(corners(im)); frames.append(im)
n=len(frames); track=np.array(track)
ks=[];cs=[]
for k,x in enumerate(direct):
    if x is not None and np.abs(x-track[k]).max()<6: ks.append(k); cs.append(x-track[k])
ks=np.array(ks); cs=np.array(cs); corr=np.zeros((n,4,2))
for i in range(4):
    for j in range(2): corr[:,i,j]=np.interp(np.arange(n),ks,cs[:,i,j])
final=savgol_filter((track+corr).reshape(n,-1),window_length=21,polyorder=2,axis=0).reshape(n,4,2)
json.dump({'final':final.tolist(),'valid_direct':ks.tolist()},open(out+'.quad.json','w'))
print('frames',n,'valid direct',len(ks))
dst=np.array([[0,0],[W,0],[W,H],[0,H]],np.float32)
ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',fps,'-i','-','-i',src,'-map','0:v','-map','1:a','-c:v','libx264','-preset','slow','-crf','14','-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-c:a','aac','-b:a','192k','-shortest',out],stdin=subprocess.PIPE)
for k,im in enumerate(frames):
    M=cv2.getPerspectiveTransform(final[k].astype(np.float32),dst)
    ff.stdin.write(cv2.warpPerspective(im,M,(W,H),flags=cv2.INTER_LANCZOS4).tobytes())
ff.stdin.close(); ff.wait(); print('wrote',out)

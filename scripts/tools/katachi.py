"""katachi.py <手本> <うち> [--fps 12]  「絵が動いとるだけ」か「形そのものが動いとる」かを測る
1) 形の動き＝画面を4x4に割り、マスごとに動き（オプティカルフロー）を平行移動＋回転＋拡大（アフィン）で当てはめた残り。
   絵を動かす・寄る・回すだけなら 0 に近い。手足・布・水・顔・変形は大きい
2) 描き替わり＝前のコマを動きでずらしても説明できん明るさの差（新しい線・形が描かれた量）
"""
import subprocess, sys, json, numpy as np, cv2
cv2.setNumThreads(2)  # 10/23 mini が重さで止まった
def frames(p, W, H, fps):
    raw = subprocess.run(["ffmpeg","-v","error","-threads","2","-i",p,"-vf",f"fps={fps},scale={W}:{H},format=gray","-f","rawvideo","-"],capture_output=True).stdout
    return np.frombuffer(raw,np.uint8).reshape(-1,H,W)
def size(p):
    s=json.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v","-show_entries","stream=width,height","-of","json",p],capture_output=True,text=True).stdout)["streams"][0]; return s["width"],s["height"]
def measure(p, W, H, fps):
    f = frames(p,W,H,fps); ys,xs = np.mgrid[0:H,0:W].astype(np.float32); nr=[]; ph=[]
    for a,b in zip(f[:-1],f[1:]):
        if np.abs(a.astype(int)-b).mean() > 40: nr.append(np.nan); ph.append(np.nan); continue   # カットは外す
        fl = cv2.calcOpticalFlowFarneback(a,b,None,0.5,3,15,3,5,1.2,0)
        res = np.zeros((H,W),np.float32); gh,gw = H//4,W//4
        for i in range(4):
            for j in range(4):
                sl=(slice(i*gh,(i+1)*gh),slice(j*gw,(j+1)*gw)); X=np.stack([xs[sl].ravel(),ys[sl].ravel(),np.ones(gh*gw)],1)
                for k in range(2):
                    y=fl[sl][...,k].ravel(); c,*_=np.linalg.lstsq(X,y,rcond=None); res[sl]+= (y-X@c).reshape(gh,gw)**2
        nr.append(float(np.sqrt(res).mean()))
        warp = cv2.remap(a,(xs+fl[...,0]),(ys+fl[...,1]),cv2.INTER_LINEAR)
        ph.append(float(np.abs(warp.astype(int)-b).mean()))
    return np.array(nr), np.array(ph)
r,o = sys.argv[1],sys.argv[2]; fps = float(sys.argv[sys.argv.index("--fps")+1]) if "--fps" in sys.argv else 12
w,h = size(r); W=240; H=int(240*h/w)//4*4
A=measure(r,W,H,fps); B=measure(o,W,H,fps); n=min(len(A[0]),len(B[0])); F=int(fps)
print(f"形の動き 手本 {np.nanmean(A[0]):.3f} うち {np.nanmean(B[0]):.3f}（{np.nanmean(B[0])/np.nanmean(A[0]):.2f}）／描き替わり 手本 {np.nanmean(A[1]):.2f} うち {np.nanmean(B[1]):.2f}（{np.nanmean(B[1])/np.nanmean(A[1]):.2f}）")
bad=[]
for s0 in range(n//F):
    a=np.nanmean(A[0][s0*F:(s0+1)*F]); b=np.nanmean(B[0][s0*F:(s0+1)*F])
    if a>0.15 and b < 0.5*a: bad.append(f"{s0}秒({b/a:.2f})")
tot=sum(1 for s0 in range(n//F) if np.nanmean(A[0][s0*F:(s0+1)*F])>0.15)
print(f"絵が動いとるだけの秒（手本は形が動くのに、うちは半分未満）：{len(bad)}/{tot}秒 " + " ".join(bad))

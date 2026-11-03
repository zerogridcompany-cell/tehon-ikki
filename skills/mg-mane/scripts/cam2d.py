# 隣り合うコマの相似（拡大・回り・ずれ）をコマごとに測る＝3D カメラの動きの 2D の影（UI の札は外す）
import cv2, numpy as np, json, sys
src=sys.argv[1]; out=sys.argv[2]
cap=cv2.VideoCapture(src); n=int(cap.get(7)); W=int(cap.get(3)); H=int(cap.get(4))
prev=None; rows=[]
lk=dict(winSize=(31,31),maxLevel=4,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,0.01))
k=0
while True:
    ok,im=cap.read()
    if not ok: break
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    if prev is not None:
        p0=cv2.goodFeaturesToTrack(prev,1500,0.005,12,blockSize=7)
        rec={'f':k,'s':1.0,'rot':0.0,'tx':0.0,'ty':0.0,'inl':0,'n':0,'diff':float(np.abs(g.astype(np.int16)-prev.astype(np.int16)).mean())}
        if p0 is not None and len(p0)>30:
            p1,st,_=cv2.calcOpticalFlowPyrLK(prev,g,p0,None,**lk)
            p0b,st2,_=cv2.calcOpticalFlowPyrLK(g,prev,p1,None,**lk)
            good=(st.ravel()==1)&(st2.ravel()==1)&(np.linalg.norm((p0-p0b).reshape(-1,2),axis=1)<1.0)
            A=p0[good].reshape(-1,2); B=p1[good].reshape(-1,2)
            if len(A)>=12:
                M,inl=cv2.estimateAffinePartial2D(A,B,method=cv2.RANSAC,ransacReprojThreshold=2.0)
                if M is not None:
                    s=float(np.hypot(M[0,0],M[0,1])); rot=float(np.degrees(np.arctan2(M[0,1],M[0,0])))
                    # 画面の中心の動き
                    c=np.array([W/2,H/2,1.0]); cc=M@c
                    rec.update({'s':s,'rot':rot,'tx':float(cc[0]-W/2),'ty':float(cc[1]-H/2),'inl':int(inl.sum()),'n':int(len(A))})
                    # 中心まわりの拡大と、流れの大きさ（中央値）
                    flow=np.linalg.norm(B-A,axis=1); rec['flow_med']=float(np.median(flow)); rec['flow_p90']=float(np.percentile(flow,90))
        rows.append(rec)
    prev=g; k+=1
json.dump(rows,open(out,'w'))
# 区間のまとめを出す（8コマごと）
print('f  | s(拡大/コマ) | rot°/コマ | tx | ty | flow_med | diff')
for i in range(0,len(rows),8):
    r=rows[i:i+8]; s=np.prod([x['s'] for x in r]); rot=sum(x['rot'] for x in r); tx=sum(x['tx'] for x in r); ty=sum(x['ty'] for x in r)
    fm=np.mean([x.get('flow_med',0) for x in r]); df=np.mean([x['diff'] for x in r])
    print(f"{r[0]['f']:4d}-{r[-1]['f']:4d} | {s:6.3f} | {rot:6.2f} | {tx:7.1f} | {ty:7.1f} | {fm:6.1f} | {df:5.1f}")

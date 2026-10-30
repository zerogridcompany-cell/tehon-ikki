# masked coarse search: ref frames (text band masked) vs cand pkl features. usage: msearch.py ref.mp4 cand.mp4 cut:t0:t1 ...
import sys,pickle,subprocess,json,numpy as np,cv2
ref,cand=sys.argv[1],sys.argv[2]; cuts=[a.split(":") for a in sys.argv[3:]]
cf=pickle.load(open(cand+".sift2_320.pkl","rb"))
sift=cv2.SIFT_create(1500); bf=cv2.BFMatcher()
def fr(p,a,d,w=320):
    o=subprocess.run(["ffmpeg","-v","error","-ss",f"{a:.3f}","-t",f"{d:.3f}","-i",p,"-vf",f"scale={w}:180","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True).stdout
    return np.frombuffer(o,np.uint8).reshape(-1,180,w)
out={}
for c,t0,t1 in cuts:
    t0=float(t0);t1=float(t1); R=fr(ref,t0,t1-t0); idx=sorted(set([0,len(R)//2,len(R)-1]))
    mask=np.full((180,320),255,np.uint8); mask[int(180*0.36):int(180*0.60),int(320*0.15):int(320*0.85)]=0
    mask[:12,:]=0; mask[-12:,:]=0
    refs=[]
    for i in idx:
        k,d=sift.detectAndCompute(R[i],mask)
        for flip in (False,):
            refs.append((i,k,d))
    scores=[]
    for j,(pa,da) in enumerate(cf):
        if da is None or len(pa)<8: continue
        da=da.astype(np.float32); best=0
        for i,k,d in refs:
            if d is None or len(k)<8: continue
            m=[x for x,y in (p for p in bf.knnMatch(da,d,k=2) if len(p)==2) if x.distance<0.75*y.distance]
            if len(m)<8: continue
            H,inl=cv2.findHomography(np.float32([pa[x.queryIdx] for x in m]),np.float32([k[x.trainIdx].pt for x in m]),cv2.RANSAC,4.0)
            n=int(inl.sum()) if inl is not None else 0
            best=max(best,n)
        scores.append((best,j/2))
    scores.sort(reverse=True)
    out[c]=scores[:8]
    print(c, [(n,t) for n,t in scores[:8]], flush=True)
json.dump(out,open(sys.argv[2].split('/')[-1]+".msearch.json","w"))

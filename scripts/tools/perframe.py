import sys,subprocess,numpy as np,cv2
ref,t0,t1,cand,c0,c1=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4],float(sys.argv[5]),float(sys.argv[6])
def fr(p,a,d,w=480):
    pr=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p],capture_output=True,text=True).stdout.strip().split(",")
    h=int(round(int(pr[1])*w/int(pr[0])/2)*2)
    o=subprocess.run(["ffmpeg","-v","error","-ss",f"{a:.3f}","-t",f"{d:.3f}","-i",p,"-vf",f"scale={w}:-2","-f","rawvideo","-pix_fmt","gray","-"],capture_output=True).stdout
    return np.frombuffer(o,np.uint8).reshape(-1,h,w)
R=fr(ref,t0,t1-t0); C=fr(cand,c0,c1-c0)
s=cv2.SIFT_create(1500); bf=cv2.BFMatcher()
fc=[s.detectAndCompute(c,None) for c in C]
for i,r in enumerate(R):
    kr,dr=s.detectAndCompute(r,None); best=(0,-1)
    for j,(kc,dc) in enumerate(fc):
        if dr is None or dc is None or len(kc)<8: continue
        m=[x for x,y in (p for p in bf.knnMatch(dr,dc,k=2) if len(p)==2) if x.distance<0.75*y.distance]
        if len(m)<8: continue
        H,inl=cv2.findHomography(np.float32([kr[x.queryIdx].pt for x in m]),np.float32([kc[x.trainIdx].pt for x in m]),cv2.RANSAC,4.0)
        n=int(inl.sum()) if inl is not None else 0
        if n>best[0]: best=(n,j)
    print(f"ref t={t0+i/25:.3f} -> cand t={c0+best[1]/23.976:.3f} inl={best[0]}")

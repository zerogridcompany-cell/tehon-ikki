# 切れ目（oracle と同じ数え方）を手本・前の版・新しい版で並べ、手本の秒で「足りん切れ目」を出す
# 使い方（作業フォルダで）: python3 cuts_cmp.py <前の版.mp4> <新しい版.mp4>   手本＝ref/*.mp4・うち→手本の秒＝rikai/ref2out_sec.json（無ければそのまま）
import subprocess, numpy as np, json, bisect, sys, glob, os
REF = os.environ.get('REF') or sorted(glob.glob('ref/*.mp4'))[0]
def cuts(p):
    r = subprocess.run(["ffmpeg","-v","error","-i",p,"-vf","scale=90:160,format=gray","-f","rawvideo","-"],capture_output=True).stdout
    F = np.frombuffer(r,np.uint8).reshape(-1,160,90).astype(float); d = np.abs(np.diff(F,axis=0)).mean(axis=(1,2))
    dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],capture_output=True,text=True).stdout); fps = len(F)/dur; ts=[]
    for i in range(len(d)):
        nb = np.concatenate([d[max(0,i-5):i], d[i+1:i+6]]); loc = float(np.median(nb))
        if d[i] >= 10 and d[i] >= 3.5*max(loc,0.5):
            t=(i+1)/fps
            if not ts or t-ts[-1]>0.15: ts.append(t)
    return ts
R2O = json.load(open('rikai/ref2out_sec.json')) if os.path.exists('rikai/ref2out_sec.json') else None
def o2r(t): return min(bisect.bisect_left(R2O, t), len(R2O)-1)/60 if R2O else t
a = [round(o2r(t),2) for t in cuts(sys.argv[1])]; b = [round(o2r(t),2) for t in cuts(sys.argv[2])]; ref = [round(t,2) for t in cuts(REF)]
near = lambda x, L: bool(L) and min(abs(x-y) for y in L) < 0.1
print('手本', len(ref), '前', len(a), '新', len(b))
print('前にあって新に無い（手本の秒）', [x for x in a if not near(x, b)])
print('手本にあって新に無い', [x for x in ref if not near(x, b)])

# 手本とうちの cam2d.json を 8コマごとに並べて、場面ごとの一致（拡大 log s・回り・ずれの相関）を出す
import json, sys, numpy as np
A=json.load(open(sys.argv[1])); B=json.load(open(sys.argv[2]))
kukan=sys.argv[3] if len(sys.argv)>3 else "S01:0-41,S02:42-59,S03:60-96,S04:97-152,S05:152-216,S06:217-288,S07:289-384,S08:385-432,S09:433-496,S10:496-594,S11:595-655"
def arr(R,key):
    n=max(r['f'] for r in R)+1; v=np.zeros(n)
    for r in R: v[r['f']]=r.get(key,0)
    return v
def feats(R):
    return {'ls':np.log(np.clip(arr(R,'s'),0.5,2.0)),'rot':arr(R,'rot'),'tx':arr(R,'tx'),'ty':arr(R,'ty'),'flow':arr(R,'flow_med')}
FA=feats(A); FB=feats(B); n=min(len(FA['ls']),len(FB['ls']))
print('場面 | log拡大 相関 | 回り 相関 | ずれ(tx,ty) 相関 | 流れの量 うち/手本')
for part in kukan.split(','):
    name,rng=part.split(':'); a,b=map(int,rng.split('-')); b=min(b,n-1); sl=slice(a,b+1)
    def c(k):
        x=FA[k][sl]; y=FB[k][sl]
        if x.std()<1e-6 or y.std()<1e-6: return float('nan')
        return float(np.corrcoef(x,y)[0,1])
    tx=np.corrcoef(np.r_[FA['tx'][sl],FA['ty'][sl]],np.r_[FB['tx'][sl],FB['ty'][sl]])[0,1] if (FA['tx'][sl].std()+FA['ty'][sl].std())>1e-6 else float('nan')
    ratio=(FB['flow'][sl].mean()+1e-6)/(FA['flow'][sl].mean()+1e-6)
    print(f"{name} {a}-{b} | {c('ls'):5.2f} | {c('rot'):5.2f} | {tx:5.2f} | {ratio:4.2f}")
print('\n8コマごと（手本 → うち）: s | rot | tx | ty | flow')
for i in range(0,n,8):
    ra=A[i:i+8]; rb=B[i:i+8]
    f=lambda R: (np.prod([x['s'] for x in R]), sum(x['rot'] for x in R), sum(x['tx'] for x in R), sum(x['ty'] for x in R), np.mean([x.get('flow_med',0) for x in R]))
    a_=f(ra); b_=f(rb)
    print(f"{i:4d} | {a_[0]:5.3f}→{b_[0]:5.3f} | {a_[1]:6.1f}→{b_[1]:6.1f} | {a_[2]:6.0f}→{b_[2]:6.0f} | {a_[3]:6.0f}→{b_[3]:6.0f} | {a_[4]:5.1f}→{b_[4]:5.1f}")

# 手元の効果音を全部集めて目録に（同じ中身は1つ・8秒以下）
import os, hashlib, json, glob, soundfile as sf, subprocess
dirs=sys_dirs=[os.path.expanduser(p) for p in ['~/scratcher-basket/vsl/remotion/public','~/fushigi3d/n01_mizu/sfx_packs','~/.claude/skills/motion-sound','~/.agents/skills/motion-sound/sfx','~/.agents/skills/zackd-ad/remotion/public/sfx','~/.agents/skills/zackd-ad/references/knowledge/素材/sfx','~/research/sfx-premium-20261020','~/Downloads/sfx','~/Downloads/sfx ver2','~/research/zackd-howto-20261019/sfx_jissoku','~/research/ashimoto-ps2-20261012/sfx','~/research/ashimoto-ps2-20261012/sfx_aura','~/vlog04_build/sfx','~/vlog03_build/sfx','~/scratcher-basket/vsl/L1_mugi/remotion/public/sfx','~/scratcher-basket/vsl/K1_kabe/remotion/public/sfx','~/research/_mini_archive_20261019/huashu/repos/Barty-Bart_motion-graphics/skills/sound-effects/sfx']]
seen={}; out=[]
for d in dirs:
    for p in glob.glob(d+'/**/*',recursive=True):
        if not p.lower().endswith(('.wav','.mp3','.ogg','.flac','.m4a','.aif','.aiff')): continue
        try: h=hashlib.md5(open(p,'rb').read()).hexdigest()
        except Exception: continue
        if h in seen: continue
        try: dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout.strip())
        except Exception: continue
        if not (0.05<dur<=8): continue
        seen[h]=p; out.append(dict(path=p,dur=round(dur,3)))
json.dump(out,open('sfx/library.json','w'),ensure_ascii=False,indent=0); print(len(out),'本')

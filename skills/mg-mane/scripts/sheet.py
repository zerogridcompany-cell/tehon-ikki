# 検品用の一覧（手本だけ・コマ番号つき）。字幕やない＝見るための道具
import cv2, sys, numpy as np
from PIL import Image, ImageDraw
src,s,e,step,cols,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
cap=cv2.VideoCapture(src); tw,th=384,216; fr=list(range(s,e+1,step)); rows=(len(fr)+cols-1)//cols
sheet=Image.new('RGB',(cols*(tw+2),rows*(th+2)),'black'); d=ImageDraw.Draw(sheet)
for i,f in enumerate(fr):
    cap.set(1,f); ok,im=cap.read()
    if not ok: break
    im=cv2.resize(im,(tw,th),interpolation=cv2.INTER_AREA)[:,:,::-1]
    x=(i%cols)*(tw+2); y=(i//cols)*(th+2); sheet.paste(Image.fromarray(im),(x,y))
    d.rectangle([x+4,y+4,x+70,y+30],fill='white'); d.text((x+8,y+8),str(f),fill='red')
sheet.save(out)

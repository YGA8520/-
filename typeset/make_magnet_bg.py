#!/usr/bin/env python3
"""The gold background of the magnet, made from the background page that was sent (assets/magnet/bg-source.jpg):
the brushed gold is rebuilt (smooth light field fitted on the clean parts + streaks along the brushing, 152.5 deg),
so the text, the logo and the box of the source disappear; the three corner flourishes are carried over from the source onto the new ground,
the Shabbat still life is cut out on its own (shabbat-still.png, enlarged x2) for the page to place. Output: 154 x 216 mm (A5 + 3 mm bleed) at 300 dpi.
usage: python3 make_magnet_bg.py   -> assets/magnet/bg-gold.jpg   (needs opencv-python-headless)"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'assets', 'magnet', 'bg-source.jpg')
DST = os.path.join(HERE, 'assets', 'magnet', 'bg-gold.jpg')
STILL = os.path.join(HERE, 'assets', 'magnet', 'shabbat-still.png')
import numpy as np, cv2
src=cv2.imread(SRC).astype(np.float32)
H0,W0=src.shape[:2]
W,H=1819,2551; s=W/W0; Hs=round(H0*s); top=(Hs-H)//2
up=cv2.resize(src,(W,Hs),interpolation=cv2.INTER_LANCZOS4)[top:top+H]
def R(x0,y0,x1,y1): return (round(x0*s),round(y0*s)-top,round(x1*s),round(y1*s)-top)
keep={'tl':R(22,18,305,262),'tr':R(1128,18,1402,285),'bl':R(18,1695,290,1968),'still':R(1095,1700,1414,2000)}
mask=np.ones((H,W),np.float32)
g=cv2.cvtColor(up,cv2.COLOR_BGR2GRAY)
mask[cv2.dilate((g<150).astype(np.uint8),np.ones((15,15)))>0]=0
for r in [R(420,40,995,315),R(195,320,1265,1600),R(285,1595,1130,1950),R(20,290,65,840)]+list(keep.values()):
    x0,y0,x1,y1=r; mask[max(0,y0):y1,max(0,x0):x1]=0
# low frequency light field: 2-D polynomial fitted on the clean pixels
yy,xx=np.mgrid[0:H,0:W].astype(np.float32); xn=xx/W-.5; yn=yy/H-.5
D=3; terms=[xn**i*yn**j for i in range(D+1) for j in range(D+1-i)]
sel=mask[::6,::6]>0
A=np.stack([t[::6,::6][sel] for t in terms],1)
low=np.zeros_like(up)
for ch in range(3):
    b_=cv2.GaussianBlur(up[...,ch],(0,0),6)[::6,::6][sel]
    c,*_=np.linalg.lstsq(A,b_,rcond=None)
    low[...,ch]=sum(ci*t for ci,t in zip(c,terms))
# keep the hue of the gold everywhere: only the brightness comes from the fit (no drift of colour at the corners)
ratio=np.array([up[...,ch][mask>0].mean() for ch in range(3)],np.float32); ratio/=ratio.mean()
L=np.clip(low.mean(-1,keepdims=True),150,240); low=L*ratio
# streak detail along 152.5 deg
rng=np.random.default_rng(7)
def streaks(L,amp):
    n=rng.standard_normal((H+400,W+400)).astype(np.float32)
    k=np.zeros((L*2+1,L*2+1),np.float32); c=L
    t=np.radians(152.5); dx,dy=np.cos(t),np.sin(t)
    for i in range(-L,L+1): k[int(round(c+i*dy)),int(round(c+i*dx))]=1
    k/=k.sum(); f=cv2.filter2D(n,-1,k)[200:-200,200:-200]
    return f/f.std()*amp
det=streaks(160,3.2)+streaks(45,2.0)+cv2.GaussianBlur(streaks(260,1.0),(0,0),1.5)
lum=low.mean(-1,keepdims=True)
out=low*(1+det[...,None]/lum)
# paste the ornaments and the still life by their difference from the light field (the brushed ground stays synthetic)
box=R(270,1580,1135,1960)
d_=round(4.5/25.4*300)                    # 4.5 mm inward
SHIFT={'tl':(d_,d_),'tr':(-d_,d_),'bl':(d_,-d_)}
for k,(x0,y0,x1,y1) in keep.items():
    x0=max(0,x0);y0=max(0,y0);x1=min(W,x1);y1=min(H,y1)
    reg=np.zeros((H,W),np.float32); reg[y0:y1,x0:x1]=1
    bx0,by0,bx1,by1=box; reg[by0:by1,bx0:bx1]=0
    reg=cv2.GaussianBlur(reg,(0,0),6)
    pad=40; sx0,sy0,sx1,sy1=max(0,x0-pad),max(0,y0-pad),min(W,x1+pad),min(H,y1+pad)
    loc=np.zeros_like(up); sub=np.clip(up[sy0:sy1,sx0:sx1],0,255).astype(np.uint8)
    lb=cv2.medianBlur(cv2.medianBlur(sub,31),31).astype(np.float32); lb=cv2.GaussianBlur(lb,(0,0),12)
    loc[sy0:sy1,sx0:sx1]=lb
    d=np.abs(cv2.GaussianBlur(up,(0,0),1.2)-loc).max(-1)
    al=np.clip((d-14)/18,0,1)
    al=cv2.dilate(al,np.ones((3,3)));al=cv2.GaussianBlur(al,(0,0),1.3)*reg
    piece=up*(low.mean(-1,keepdims=True)/np.maximum(loc.mean(-1,keepdims=True),1))   # the ornament carried onto the new ground's brightness
    if k == 'still':                       # the still life is not baked in: cut out on its own (the page places it, larger)
        sub=(slice(y0,y1),slice(x0,x1)); a8=al[sub]
        ys,xs=np.where(a8>0.02); a8=a8[ys.min():ys.max()+1,xs.min():xs.max()+1]
        rgb=up[sub][ys.min():ys.max()+1,xs.min():xs.max()+1]
        big=lambda im:cv2.resize(im,None,fx=2,fy=2,interpolation=cv2.INTER_LANCZOS4)
        b=(a8>0.35).astype(np.uint8); b=cv2.morphologyEx(b,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
        ff=np.pad(b,1).copy(); m2=np.zeros((ff.shape[0]+2,ff.shape[1]+2),np.uint8)
        cv2.floodFill(ff,m2,(0,0),2); solid=(ff[1:-1,1:-1]!=2).astype(np.float32)     # the objects without holes
        a8=np.maximum(a8,cv2.GaussianBlur(cv2.erode(solid,np.ones((3,3))),(0,0),.8))
        rgb=big(rgb); a8=np.clip(big(a8),0,1)
        rgb=cv2.addWeighted(rgb,1.6,cv2.GaussianBlur(rgb,(0,0),2.2),-.6,0)          # a little sharper after the enlargement
        cv2.imwrite(STILL,np.dstack([np.clip(rgb,0,255),a8*255]).astype(np.uint8))
        continue
    # move the flourish inward so it stays whole after trimming (it sat inside the bleed in the source)
    sx,sy=SHIFT[k]; al=np.roll(al,(sy,sx),(0,1)); piece=np.roll(piece,(sy,sx),(0,1))
    out=out*(1-al[...,None])+piece*al[...,None]
cv2.imwrite(DST,np.clip(out,0,255).astype(np.uint8),[cv2.IMWRITE_JPEG_QUALITY,93])

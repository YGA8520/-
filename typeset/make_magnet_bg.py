#!/usr/bin/env python3
"""The gold background of the magnet, made from the background page that was sent (assets/magnet/bg-source.jpg):
the brushed gold is rebuilt (smooth light field fitted on the clean parts + streaks along the brushing, 152.5 deg),
so the text, the logo and the box of the source disappear; the three corner flourishes are carried over from the source onto the new ground,
the page is mirrored so that the Shabbat still life stands on the left: it is carried over with the ground right around it
(no cut-out edge, no fringe), enlarged x1.3 and moved in from the corner; the corner flourishes are left out. Output: 154 x 216 mm (A5 + 3 mm bleed) at 300 dpi.
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
up=up[:,::-1].copy()                      # the page mirrored: the Shabbat still life comes to the left with its own ground, no cutting
def R(x0,y0,x1,y1): x0,x1=W0-x1,W0-x0; return (round(x0*s),round(y0*s)-top,round(x1*s),round(y1*s)-top)   # source coordinates, mirrored
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
    t=np.radians(180-152.5); dx,dy=np.cos(t),np.sin(t)   # the brushing mirrored with the page
    for i in range(-L,L+1): k[int(round(c+i*dy)),int(round(c+i*dx))]=1
    k/=k.sum(); f=cv2.filter2D(n,-1,k)[200:-200,200:-200]
    return f/f.std()*amp
det=streaks(160,3.2)+streaks(45,2.0)+cv2.GaussianBlur(streaks(260,1.0),(0,0),1.5)
lum=low.mean(-1,keepdims=True)
out=low*(1+det[...,None]/lum)
# the wavy banner along the bottom: the same brushed gold, only deeper, with a soft light edge (no floating shadow);
# its top edge is written to bg-banner.txt (mm) for the page to place the phone lines
mm=300/25.4
BANNER=True
def wave_mm(x):                            # top edge of the banner, mm from the top of the bleed page
    return 184.0 + 2.4*np.sin(2*np.pi*(x/154.0)*1.05 + 2.2) + 1.0*np.sin(2*np.pi*(x/154.0)*2.3 + .4)
if BANNER:
    xs=np.arange(W)/mm; edge=wave_mm(xs)*mm                       # px
    yy_=np.arange(H)[:,None].astype(np.float32)
    inside=np.clip((yy_-edge[None,:]+1.0)/2.0,0,1)                 # antialiased
    depth=np.clip((yy_-edge[None,:])/(H-edge[None,:]),0,1)
    tone=np.array([.58,.80,.96],np.float32)                        # BGR multiplier: deeper, warmer gold
    shade=(tone[None,None,:]*(1-.10*depth[...,None]))
    banner=out*shade
    # light rim just under the edge and a fine dark line on it
    d_=(yy_-edge[None,:])
    rim_=np.exp(-((d_-.9*mm)/(.45*mm))**2)[...,None]*0.55
    line_=np.exp(-((d_+.05*mm)/(.12*mm))**2)[...,None]*0.35
    banner=banner*(1-rim_)+np.array([215,240,252],np.float32)*rim_
    banner=banner*(1-line_)+np.array([40,80,120],np.float32)*line_
    out=out*(1-inside[...,None])+banner*inside[...,None]
    # a second, thinner wave a little above, as a light trace (as on printed flyers)
    e2=(wave_mm(xs+9)-3.2)*mm
    tr=np.exp(-((yy_-e2[None,:])/(.18*mm))**2)[...,None]*0.45*(1-inside[...,None])
    out=out*(1-tr)+np.array([170,205,225],np.float32)*tr
    open(os.path.join(HERE,'assets','magnet','bg-banner.txt'),'w').write(' '.join('%.2f'%wave_mm(x) for x in range(0,155)))
# the Shabbat still life: its own pixels with the ground right around it (no cut-out edge), a little larger,
# moved in from the corner so it stays whole after trimming; further out it fades into the rebuilt ground
STILL_SCALE, STILL_X, STILL_BOTTOM = 1.42, 5.5, 4.0          # scale, mm from the left edge (bleed), mm from the bottom edge (bleed)
x0,y0,x1,y1=keep['still']; x0=max(0,x0); y1=min(H,y1)
patch=up[y0:y1,x0:x1].copy()
pad=40
med=cv2.medianBlur(cv2.medianBlur(np.clip(up[y0-pad:y1,x0:x1+pad],0,255).astype(np.uint8),31),31).astype(np.float32)[pad:,:x1-x0]
# the white rim of the source's name box: long vertical near-white strokes (and the curve at their foot), kept out of the objects
_wh=((patch.min(-1)>195)&((patch.max(-1)-patch.min(-1))<40)).astype(np.uint8)
RIM=cv2.dilate(cv2.morphologyEx(_wh,cv2.MORPH_OPEN,np.ones((45,1),np.uint8)),np.ones((5,13),np.uint8))
_n,_lab,_st,_=cv2.connectedComponentsWithStats(RIM)
for _i in range(1,_n):
    if _st[_i][3]<120: RIM[_lab==_i]=0     # only the long rim, not the candles or the decanter
# and the curve at its foot: whitish pixels just below the line
_foot=np.zeros_like(RIM); _foot[60:]=RIM[:-60]; _foot=cv2.dilate(_foot,np.ones((1,31),np.uint8))
RIM=np.maximum(RIM,_foot&_wh)
# where the rim crosses the tip of the book's pages, fill it from the page around it
_fix=np.zeros(RIM.shape,np.uint8); _fix[255:330,380:]=cv2.dilate(RIM,np.ones((7,7),np.uint8))[255:330,380:]
_fix[262:300,392:412]=1
patch=cv2.inpaint(np.clip(patch,0,255).astype(np.uint8),_fix,7,cv2.INPAINT_TELEA).astype(np.float32)
def objects(ref):
    """what stands out of the ground (or is whitish and a little off it: the book's pages), the box rim dropped, holes filled"""
    d=np.abs(cv2.GaussianBlur(patch,(0,0),1.2)-ref).max(-1)
    o=((d>30)|((d>14)&(patch.min(-1)>190)&((patch.max(-1)-patch.min(-1))<45))).astype(np.uint8)
    o[RIM>0]=0
    o=cv2.morphologyEx(o,cv2.MORPH_OPEN,np.ones((3,3),np.uint8)); o=cv2.morphologyEx(o,cv2.MORPH_CLOSE,np.ones((15,15),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(o); r=np.zeros_like(o)
    for i in range(1,n):
        x_,y_,w_,h_,a_=st[i]
        if a_<400 or (w_<40 and h_>90) or y_+h_<0.3*o.shape[0]: o[lab==i]=0; r[lab==i]=1
    ff=np.pad(o,1).copy(); m2=np.zeros((ff.shape[0]+2,ff.shape[1]+2),np.uint8)
    cv2.floodFill(ff,m2,(0,0),2); return (ff[1:-1,1:-1]!=2).astype(np.uint8), r
def ground(o):
    """the ground of the patch measured away from the objects only (so the objects do not tint it)"""
    free=(cv2.dilate(o,np.ones((41,41),np.uint8))==0).astype(np.float32)
    return cv2.GaussianBlur(patch*free[...,None],(0,0),40)/np.maximum(cv2.GaussianBlur(free,(0,0),40),1e-3)[...,None]
obj,rim=objects(med)                       # first pass against a local median, then again against the ground found around the objects
loc=ground(obj); obj,rim=objects(loc); loc=ground(obj)
al=cv2.GaussianBlur(cv2.dilate(obj,np.ones((7,7),np.uint8)).astype(np.float32),(0,0),2.5)
al[(cv2.dilate(rim,np.ones((7,7),np.uint8))>0)&(obj==0)]=0
al[cv2.dilate(RIM,np.ones((9,9),np.uint8))>0]=0
_h,_w=al.shape; _z=np.zeros_like(al,bool); _z[:round(.82*_h),round(.9*_w):]=True       # the corner of the source's name box, beside the book
_sat=patch.max(-1)-patch.min(-1); _book=((_sat>55)|((patch.min(-1)>200)&(_sat<45)&(cv2.dilate(RIM,np.ones((9,9),np.uint8))==0)))
_book=cv2.morphologyEx(_book.astype(np.uint8),cv2.MORPH_OPEN,np.ones((3,3),np.uint8))>0
# beside the book, nothing above the top edge of its pages (the source's name box and its soft shadow end there):
# the edge measured on the source, in the patch's own pixels (mirrored source, 1819 px wide page)
_yy,_xx=np.mgrid[0:_h,0:_w]
_edge=279+np.maximum(0,_xx-368)*0.62
al[(_xx>=round(.8*_w))&(_yy<_edge)]=0
_page=((patch.min(-1)>185)&((patch.max(-1)-patch.min(-1))<70)).astype(np.uint8)
_page=cv2.morphologyEx(_page,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
_inbook=(_xx>=250)&(_xx<392)&(_yy>=_edge+2)&(_yy<330)
al[(_page>0)&_inbook]=1                  # the book's pages fully opaque (the object mask had a hole there)
al[(_xx>=393)&(_yy<_edge+14)]=0          # the box rim curving down beside the page tip
al=cv2.GaussianBlur(al,(0,0),1.2)
sz=(round((x1-x0)*STILL_SCALE),round((y1-y0)*STILL_SCALE))
px0=round(STILL_X*mm); py1=H-round(STILL_BOTTOM*mm); py0=py1-sz[1]
ps=cv2.resize(patch,sz,interpolation=cv2.INTER_CUBIC); ls=cv2.resize(loc,sz,interpolation=cv2.INTER_LINEAR)
gd=cv2.GaussianBlur(out,(0,0),20)[py0:py1,px0:px0+sz[0]]          # the ground where it lands (the banner included)
gain=gd.mean(-1,keepdims=True)/np.maximum(ls.mean(-1,keepdims=True),1)
tint=(gd/np.maximum(gd.mean(-1,keepdims=True),1))/(ls/np.maximum(ls.mean(-1,keepdims=True),1))
piece=ps*gain*(1+.5*(tint-1))                                      # half of the ground's hue shift: the halo blends, the silver stays silver
al=cv2.resize(al,sz,interpolation=cv2.INTER_LINEAR)
piece=cv2.addWeighted(piece,1.35,cv2.GaussianBlur(piece,(0,0),1.8),-.35,0)
# fade the patch's own edges as well (left and bottom were the page's edge in the source)
e=np.ones(sz[::-1],np.float32); f=18
for i in range(f): w_=(i+1)/f; e[:,i]*=w_; e[-1-i,:]*=w_; e[i,:]*=w_; e[:,-1-i]*=w_
al*=e
out[py0:py1,px0:px0+sz[0]]=out[py0:py1,px0:px0+sz[0]]*(1-al[...,None])+piece*al[...,None]
print('still life: x %.1f-%.1f mm, y %.1f-%.1f mm' % (px0/mm,(px0+sz[0])/mm,py0/mm,py1/mm))
# paste the ornaments and the still life by their difference from the light field (the brushed ground stays synthetic)
box=R(270,1580,1135,1960)
d_=round(4.5/25.4*300)                    # 4.5 mm inward
CORNERS=False
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
    if k == 'still': continue              # baked in above, with its own ground
    if k == 'still_cutout_unused':
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
    if not CORNERS: continue               # the corner flourishes are left out (the client's request): the ground stays clean
    sx,sy=SHIFT[k]; al=np.roll(al,(sy,sx),(0,1)); piece=np.roll(piece,(sy,sx),(0,1))
    out=out*(1-al[...,None])+piece*al[...,None]
cv2.imwrite(DST,np.clip(out,0,255).astype(np.uint8),[cv2.IMWRITE_JPEG_QUALITY,93])

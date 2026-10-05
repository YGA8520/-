import subprocess, sys, glob
from PIL import Image
import numpy as np
pdf='rb/booklet.pdf'
pages=[int(a) for a in sys.argv[1:]]
for p in pages:
    subprocess.run(['pdftoppm','-r','200','-f',str(p),'-l',str(p),'-png',pdf,'rb/m'],check=True)
    f=sorted(glob.glob('rb/m-*%d.png'%p))[-1]
    im=np.array(Image.open(f).convert('L')).astype(int)
    H,W=im.shape
    X0,X1=150,W-150
    sub=im[:,X0:X1]
    mid=sub<250
    cnt=mid.sum(axis=1)
    # frame top: first row > y=150 with cnt>300 (long horizontal edge)
    cand=[y for y in range(150,700) if cnt[y]>300]
    if not cand: print(p,'no frame'); continue
    y0=cand[0]
    # bottom: last row of contiguous run (gap<=12) of rows with cnt>0
    y=y0; 
    while cnt[y+1:y+14].sum()>0 and y<H-20: y+=1
    y1=y
    band=mid[y0:y1+1]
    cols=np.where(band.sum(axis=0)>8)[0]
    fx0,fx1=cols[0]+X0,cols[-1]+X0
    dark=(sub<130)
    inner=dark[y0+14:y1-14, (fx0+45-X0):(fx1-45-X0)]
    ys,xs=np.where(inner)
    tx0,tx1=xs.min()+fx0+45,xs.max()+fx0+45
    ty0,ty1=ys.min()+y0+14,ys.max()+y0+14
    print(f'p{p}: frame x[{fx0},{fx1}] w={fx1-fx0} cx={(fx0+fx1)/2:.1f} y[{y0},{y1}] h={y1-y0} cy={(y0+y1)/2:.1f} | text x[{tx0},{tx1}] w={tx1-tx0} cx={(tx0+tx1)/2:.1f} y[{ty0},{ty1}] cy={(ty0+ty1)/2:.1f} | dx={((tx0+tx1)-(fx0+fx1))/2/200*72:.2f}pt dy={((ty0+ty1)-(y0+y1))/2/200*72:.2f}pt')

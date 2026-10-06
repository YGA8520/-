import sys, glob
from PIL import Image
# usage: sheet.py out.png cols file1 file2 ...
out=sys.argv[1]; cols=int(sys.argv[2]); fs=sys.argv[3:]
ims=[Image.open(f).convert('RGB') for f in fs]
w=max(i.size[0] for i in ims); h=max(i.size[1] for i in ims)
rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(cols*w+(cols+1)*8,rows*h+(rows+1)*8),(120,120,120))
for k,im in enumerate(ims):
    S.paste(im,(8+(k%cols)*(w+8),8+(k//cols)*(h+8)))
S.save(out); print(S.size)

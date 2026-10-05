import zipfile, re, sys
from collections import Counter
from xml.etree import ElementTree as ET
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def words_from(xml_bytes):
    root=ET.fromstring(xml_bytes)
    paras=[]
    for p in root.iter(W+'p'):
        paras.append(''.join(t.text or '' for t in p.iter(W+'t')))
    return paras
orig=words_from(open('input_document.xml','rb').read())
new=words_from(zipfile.ZipFile(sys.argv[1]).read('word/document.xml'))
tok=lambda ps: Counter(w for p in ps for w in re.split(r'\s+',p) if w)
a,b=tok(orig),tok(new)
missing=a-b; added=b-a
print('original tokens',sum(a.values()),'new tokens',sum(b.values()))
print('MISSING from new (in original, not in output): %d'%sum(missing.values()))
print(sorted(missing.items(), key=lambda kv:-kv[1])[:120])
print('ADDED in new: %d'%sum(added.values()))
print(sorted(added.items(), key=lambda kv:-kv[1])[:60])

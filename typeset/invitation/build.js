const fs=require('fs');
const W=2970,H=4200;

// ---------- SVG pieces ----------
const defs=`
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="0.15" y2="1">
  <stop offset="0" stop-color="#1b5d8a"/><stop offset=".22" stop-color="#2a7d98"/>
  <stop offset=".45" stop-color="#5d8f80"/><stop offset=".68" stop-color="#a98a4e"/>
  <stop offset=".88" stop-color="#7a5224"/><stop offset="1" stop-color="#4a2e12"/>
 </linearGradient>
 <radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></radialGradient>
 <radialGradient id="blotch1" cx=".25" cy=".12" r=".35"><stop offset="0" stop-color="#4fb0c4" stop-opacity=".55"/><stop offset="1" stop-color="#4fb0c4" stop-opacity="0"/></radialGradient>
 <radialGradient id="blotch2" cx=".8" cy=".8" r=".4"><stop offset="0" stop-color="#e3b562" stop-opacity=".5"/><stop offset="1" stop-color="#e3b562" stop-opacity="0"/></radialGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#fff2b0"/><stop offset=".25" stop-color="#e6bd52"/>
  <stop offset=".5" stop-color="#a87820"/><stop offset=".72" stop-color="#f0d27a"/><stop offset="1" stop-color="#8a5c14"/>
 </linearGradient>
 <linearGradient id="goldV" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#fff2b0"/><stop offset=".3" stop-color="#e2b84e"/>
  <stop offset=".55" stop-color="#9a6c1c"/><stop offset=".8" stop-color="#e8c768"/><stop offset="1" stop-color="#7d5212"/>
 </linearGradient>
 <linearGradient id="cream" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#f8edc9"/><stop offset=".45" stop-color="#dcc088"/><stop offset="1" stop-color="#9c7a40"/>
 </linearGradient>
 <linearGradient id="bronzeV" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#6d4526"/><stop offset=".5" stop-color="#9c6d3d"/><stop offset="1" stop-color="#4e2f16"/>
 </linearGradient>
 <linearGradient id="shaft" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#24120a"/><stop offset=".18" stop-color="#6c4120"/>
  <stop offset=".42" stop-color="#b98550"/><stop offset=".62" stop-color="#8a5a2e"/><stop offset="1" stop-color="#22110a"/>
 </linearGradient>
 <linearGradient id="recess" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#2a180c"/><stop offset=".6" stop-color="#5a3a1e"/><stop offset="1" stop-color="#8a6234"/>
 </linearGradient>
 <radialGradient id="parch" cx=".5" cy=".45" r=".7">
  <stop offset="0" stop-color="#fdf3d2"/><stop offset=".6" stop-color="#f1deab"/><stop offset="1" stop-color="#d4b472"/>
 </radialGradient>
 <radialGradient id="teal" cx=".5" cy=".4" r=".7">
  <stop offset="0" stop-color="#48b3b8"/><stop offset=".7" stop-color="#1a6f80"/><stop offset="1" stop-color="#0c4a5c"/>
 </radialGradient>
 <filter id="blur30"><feGaussianBlur stdDeviation="30"/></filter>
 <filter id="blur12"><feGaussianBlur stdDeviation="12"/></filter>
 <filter id="noise" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".012 .02" numOctaves="4" seed="7"/>
  <feColorMatrix values="0 0 0 0 .1  0 0 0 0 .07  0 0 0 0 .02  0 0 0 .55 -.12"/>
 </filter>
 <filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/>
  <feColorMatrix values="0 0 0 0 .3  0 0 0 0 .2  0 0 0 0 .05  0 0 0 .35 -.1"/>
 </filter>
 <clipPath id="parchClip"><rect x="745" y="825" width="1480" height="2750" rx="740" ry="495"/></clipPath>
 <g id="curl">
  <path d="M0,0 C-120,60 -330,100 -450,50 C-530,15 -540,-50 -480,-70 C-425,-85 -395,-30 -430,-10" fill="none" stroke="#2a1608" stroke-width="46" stroke-linecap="round" opacity=".5" transform="translate(6,8)"/>
  <path d="M0,0 C-120,60 -330,100 -450,50 C-530,15 -540,-50 -480,-70 C-425,-85 -395,-30 -430,-10" fill="none" stroke="url(#gold)" stroke-width="36" stroke-linecap="round"/>
  <path d="M0,0 C-120,60 -330,100 -450,50 C-530,15 -540,-50 -480,-70" fill="none" stroke="#fff6cc" stroke-width="7" stroke-linecap="round" opacity=".65" transform="translate(0,-9)"/>
  <circle cx="-430" cy="-10" r="30" fill="url(#gold)" stroke="#5a3a0a" stroke-width="5"/>
  <path d="M-170,70 C-190,130 -250,150 -300,125 C-250,110 -215,95 -170,70Z" fill="url(#gold)" stroke="#5a3a0a" stroke-width="4"/>
  <path d="M-330,92 C-340,150 -390,170 -440,150 C-395,130 -360,118 -330,92Z" fill="url(#gold)" stroke="#5a3a0a" stroke-width="4"/>
 </g>
 <g id="curlUp">
  <path d="M0,0 C-110,-40 -240,-40 -320,-100 C-370,-140 -350,-200 -300,-200 C-255,-200 -250,-150 -285,-148" fill="none" stroke="#2a1608" stroke-width="40" stroke-linecap="round" opacity=".5" transform="translate(6,8)"/>
  <path d="M0,0 C-110,-40 -240,-40 -320,-100 C-370,-140 -350,-200 -300,-200 C-255,-200 -250,-150 -285,-148" fill="none" stroke="url(#gold)" stroke-width="32" stroke-linecap="round"/>
  <circle cx="-285" cy="-148" r="26" fill="url(#gold)" stroke="#5a3a0a" stroke-width="4"/>
 </g>
 <g id="swirl">
  <path d="M0,0 C80,-90 230,-110 330,-50 C390,-10 370,70 300,70 C250,70 235,10 280,0 M120,-70 C150,-130 230,-150 275,-120" fill="none" stroke="#9c7c40" stroke-width="9" stroke-linecap="round"/>
 </g>
 <g id="rosettePetal"><path d="M0,0 C-34,-40 -30,-100 0,-130 C30,-100 34,-40 0,0Z" fill="url(#goldV)" stroke="#5a3a0a" stroke-width="4"/></g>
</defs>`;

function ropes(cx){
  let s='';
  for(let i=0;i<12;i++){
    const y=1135+i*195;
    const d=`M${cx-100},${y+150} C${cx-45},${y+112} ${cx+45},${y+38} ${cx+100},${y}`;
    s+=`<path d="${d}" stroke="#1d0f06" stroke-width="66" fill="none" stroke-linecap="round" opacity=".55" transform="translate(5,8)"/>`;
    s+=`<path d="${d}" stroke="url(#gold)" stroke-width="48" fill="none" stroke-linecap="round"/>`;
    s+=`<path d="${d}" stroke="#fff3bf" stroke-width="9" fill="none" stroke-linecap="round" opacity=".75" transform="translate(-4,-12)"/>`;
  }
  return s;
}
function column(cx){
  const x0=cx-110;
  return `
  <rect x="${x0}" y="1080" width="220" height="2420" fill="url(#shaft)"/>
  ${ropes(cx)}
  <rect x="${x0}" y="1080" width="220" height="2420" fill="none" stroke="#1a0d05" stroke-width="5" opacity=".6"/>
  <!-- capital -->
  <rect x="${cx-175}" y="930" width="350" height="62" fill="url(#cream)" stroke="#6b4c20" stroke-width="5"/>
  <path d="M${cx-150},992 L${cx+150},992 L${cx+118},1085 L${cx-118},1085Z" fill="url(#cream)" stroke="#6b4c20" stroke-width="5"/>
  <path d="M${cx-110},1010 q30,-10 40,25 q-8,34 -40,30 M${cx+110},1010 q-30,-10 -40,25 q8,34 40,30 M${cx-12},1006 q12,-8 24,0 q12,36 0,70 q-12,-34 -24,-70" fill="none" stroke="#7a5826" stroke-width="9" stroke-linecap="round"/>
  <path d="M${cx-160},1000 h320" stroke="#fff8da" stroke-width="5" opacity=".8"/>
  <rect x="${cx-130}" y="1085" width="260" height="20" fill="url(#gold)" stroke="#5a3a0a" stroke-width="4"/>
  <!-- base -->
  <rect x="${cx-130}" y="3478" width="260" height="22" fill="url(#gold)" stroke="#5a3a0a" stroke-width="4"/>
  <path d="M${cx-118},3500 L${cx+118},3500 L${cx+150},3560 L${cx-150},3560Z" fill="url(#cream)" stroke="#6b4c20" stroke-width="5"/>
  <rect x="${cx-175}" y="3560" width="350" height="58" fill="url(#cream)" stroke="#6b4c20" stroke-width="5"/>
  `;
}
function dentils(){
  let s='';
  for(let x=160;x<2810;x+=56) s+=`<rect x="${x}" y="772" width="30" height="34" fill="#c9a766" stroke="#6b4c20" stroke-width="3"/>`;
  return s;
}
function rosette(cx,cy){
  let s='';
  for(let a=0;a<360;a+=30) s+=`<use href="#rosettePetal" transform="translate(${cx},${cy}) rotate(${a})"/>`;
  for(let a=15;a<360;a+=30) s+=`<use href="#rosettePetal" transform="translate(${cx},${cy}) rotate(${a}) scale(.62)"/>`;
  s+=`<circle cx="${cx}" cy="${cy}" r="42" fill="url(#gold)" stroke="#4a2c06" stroke-width="6"/><circle cx="${cx}" cy="${cy}" r="20" fill="#7d1e1e" stroke="#fff0b0" stroke-width="4"/>`;
  return s;
}

const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="297mm" height="420mm" style="position:absolute;left:0;top:0">
${defs}
<rect width="${W}" height="${H}" fill="url(#bg)"/>
<rect width="${W}" height="${H}" fill="url(#blotch1)"/><rect width="${W}" height="${H}" fill="url(#blotch2)"/>
<rect width="${W}" height="${H}" filter="url(#noise)" opacity=".7"/>
<rect width="${W}" height="${H}" filter="url(#grain)" opacity=".6"/>
<rect width="${W}" height="${H}" fill="url(#vig)"/>

<!-- recess behind the cartouche -->
<rect x="560" y="930" width="1850" height="2580" fill="url(#recess)"/>
<rect x="560" y="930" width="1850" height="120" fill="#000" opacity=".35"/>
<path d="M560,3380 L2410,3380 L2410,3510 L560,3510Z" fill="#a47a44" opacity=".5"/>

${column(470)}${column(2500)}

<!-- entablature -->
<rect x="110" y="700" width="2750" height="72" fill="url(#cream)" stroke="#6b4c20" stroke-width="6"/>
<rect x="110" y="700" width="2750" height="10" fill="#fffbe6" opacity=".7"/>
<rect x="170" y="772" width="2630" height="100" fill="url(#bronzeV)" stroke="#3b2210" stroke-width="5"/>
${dentils()}
<rect x="235" y="818" width="480" height="46" fill="#3b2210" stroke="url(#gold)" stroke-width="5"/><path d="M295,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M340,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M385,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M430,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M475,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M520,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M565,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M610,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M655,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/>
<rect x="2255" y="818" width="480" height="46" fill="#3b2210" stroke="url(#gold)" stroke-width="5"/><path d="M2315,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2360,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2405,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2450,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2495,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2540,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2585,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2630,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/><path d="M2675,830 l14,11 l-14,11 l-14,-11Z" fill="url(#gold)" stroke="#4a2c06" stroke-width="2"/>
<rect x="230" y="872" width="2510" height="58" fill="url(#cream)" stroke="#6b4c20" stroke-width="6"/>
<rect x="230" y="872" width="2510" height="7" fill="#fffbe6" opacity=".8"/>

<!-- platform -->
<rect x="240" y="3500" width="2490" height="60" fill="url(#cream)" stroke="#6b4c20" stroke-width="5" opacity="0"/>
<rect x="130" y="3610" width="2710" height="84" fill="url(#cream)" stroke="#6b4c20" stroke-width="6"/>
<rect x="130" y="3610" width="2710" height="9" fill="#fffbe6" opacity=".8"/>
<rect x="200" y="3694" width="2570" height="40" fill="url(#bronzeV)" stroke="#3b2210" stroke-width="5"/>

<!-- crest -->
<use href="#curl" transform="translate(1250,600)"/>
<use href="#curl" transform="translate(${W},0) scale(-1,1) translate(1250,600)"/>
<use href="#curlUp" transform="translate(1270,520)"/>
<use href="#curlUp" transform="translate(${W},0) scale(-1,1) translate(1270,520)"/>
<rect x="1270" y="590" width="430" height="120" rx="30" fill="url(#goldV)" stroke="#4a2c06" stroke-width="6"/>
<ellipse cx="1485" cy="360" rx="338" ry="292" fill="#000" opacity=".35" filter="url(#blur12)" transform="translate(8,14)"/>
<ellipse cx="1485" cy="360" rx="335" ry="290" fill="url(#gold)" stroke="#4a2c06" stroke-width="7"/>
<ellipse cx="1485" cy="360" rx="300" ry="255" fill="none" stroke="#4a2c06" stroke-width="5"/>
<ellipse cx="1485" cy="360" rx="318" ry="272" fill="none" stroke="#fff3bf" stroke-width="10" stroke-dasharray="1 24" stroke-linecap="round"/>
<ellipse cx="1485" cy="360" rx="270" ry="226" fill="url(#teal)" stroke="#2a1608" stroke-width="6"/>
<ellipse cx="1485" cy="360" rx="252" ry="208" fill="none" stroke="url(#gold)" stroke-width="7"/>
<!-- crown -->
<path d="M1385,118 L1385,66 L1428,96 L1466,40 L1485,12 L1504,40 L1542,96 L1585,66 L1585,118Z" fill="url(#goldV)" stroke="#4a2c06" stroke-width="6" stroke-linejoin="round" transform="translate(0,-4)"/>
<rect x="1378" y="108" width="214" height="26" rx="8" fill="url(#gold)" stroke="#4a2c06" stroke-width="5" transform="translate(0,-4)"/>
<circle cx="1485" cy="4" r="14" fill="url(#gold)" stroke="#4a2c06" stroke-width="4"/>

<!-- cartouche -->
<rect x="675" y="755" width="1620" height="2890" rx="810" ry="565" fill="#000" opacity=".5" filter="url(#blur30)" transform="translate(14,34)"/>
<rect x="640" y="720" width="1690" height="2960" rx="845" ry="600" fill="#2c1a0a"/>
<rect x="675" y="755" width="1620" height="2890" rx="810" ry="565" fill="none" stroke="url(#gold)" stroke-width="72"/>
<rect x="640" y="720" width="1690" height="2960" rx="845" ry="600" fill="none" stroke="#4a2c06" stroke-width="5"/>
<rect x="710" y="790" width="1550" height="2820" rx="775" ry="530" fill="none" stroke="#4a2c06" stroke-width="7"/>
<rect x="725" y="805" width="1520" height="2790" rx="760" ry="515" fill="none" stroke="url(#goldV)" stroke-width="20"/>
<rect x="734" y="814" width="1502" height="2772" rx="751" ry="506" fill="none" stroke="#fff6cf" stroke-width="3" opacity=".7"/>
<rect x="745" y="825" width="1480" height="2750" rx="740" ry="495" fill="url(#parch)"/>
<g clip-path="url(#parchClip)">
 <rect x="745" y="825" width="1480" height="2750" fill="none" stroke="#6a4310" stroke-opacity=".55" stroke-width="90" filter="url(#blur30)" rx="740" ry="495"/>
 <rect x="745" y="825" width="1480" height="2750" filter="url(#noise)" opacity=".28"/>
 <use href="#swirl" transform="translate(1485,1010) scale(-1,1) translate(-30,0)" opacity=".55"/>
 <use href="#swirl" transform="translate(1485,1010) translate(-30,0)" opacity=".55"/>
 <use href="#swirl" transform="translate(1485,3390) scale(-1,-1) translate(-30,0)" opacity=".45"/>
 <use href="#swirl" transform="translate(1485,3390) scale(1,-1) translate(-30,0)" opacity=".45"/>
</g>

<!-- bottom ornament -->
<use href="#curl" transform="translate(1385,3790) scale(1,1)"/>
<use href="#curl" transform="translate(${W},0) scale(-1,1) translate(1385,3790)"/>
${rosette(1485,3790)}
</svg>`;

// ---------- text ----------
const html=`<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<style>
@page{size:297mm 420mm;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:297mm;height:420mm;background:#2a7d98;overflow:hidden}
body{position:relative;font-family:'Guttman Mantova','Guttman Drogolin',serif;font-weight:700}
.gold{color:transparent;background:linear-gradient(180deg,#fffbe0 0%,#f3d77f 26%,#b9852b 50%,#ecc962 68%,#7a4b0e 100%);-webkit-background-clip:text;background-clip:text;
 filter:drop-shadow(.28mm 0 0 #3a2205) drop-shadow(-.28mm 0 0 #3a2205) drop-shadow(0 .28mm 0 #3a2205) drop-shadow(0 -.22mm 0 #5a3a0a) drop-shadow(0 .9mm .7mm rgba(40,20,0,.5))}
.navy{color:#14224c;text-shadow:0 .18mm 0 rgba(255,250,225,.55),0 -.1mm 0 rgba(10,15,40,.25)}
#crest{position:absolute;left:97.5mm;width:100mm;top:21mm;height:30mm;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;line-height:1.02}
#crest .gold{font-size:8.3mm}
#crest .sub{margin-top:1.6mm;width:34mm;height:.5mm;background:linear-gradient(90deg,transparent,#e8c75e,transparent)}
#bsd{position:absolute;right:20mm;top:30mm;font-size:6mm;color:#f4f7f2;font-weight:400;font-family:'Guttman Frank',serif;text-shadow:0 .2mm .6mm rgba(0,0,0,.5)}
#text{position:absolute;left:74.5mm;width:148mm;top:82.5mm;height:275mm;display:flex;flex-direction:column;align-items:center;text-align:center}
.lh{line-height:1.27}
.open{font-size:6.9mm;margin-top:16mm}
.big{font-size:17.5mm;line-height:1.02;margin-top:3mm}
.small{font-size:6.8mm;margin-top:2.2mm}
.sh{font-size:14.2mm;line-height:1;margin-top:1.8mm}
.rg{font-size:6.9mm;margin-top:4.4mm}
.nm{font-size:9.6mm;margin-top:1.8mm}
.date{font-size:8.5mm;margin-top:4.6mm}
.bless{font-size:5.5mm;margin-top:4.6mm;font-weight:400;font-family:'Guttman Frank',serif}
.sig1{font-size:6.8mm;margin-top:3.4mm}
.sig2{font-size:8.2mm;margin-top:.6mm;line-height:1}
.orn{display:flex;align-items:center;justify-content:center;gap:2.5mm;margin-top:2.2mm}
.orn i{display:block;width:26mm;height:.55mm;background:linear-gradient(90deg,transparent,#8b6420,#c79a3b)}
.orn i:last-child{transform:scaleX(-1)}
.orn b{display:block;width:3mm;height:3mm;transform:rotate(45deg);background:linear-gradient(135deg,#fff0b0,#a87820);border:.3mm solid #4a2c06}
#foot{position:absolute;left:0;width:297mm;top:394mm;text-align:center;font-size:11.4mm;line-height:1}
</style></head><body>
${svg}
<div id="crest"><div class="gold">שמחת התורה</div><div class="sub"></div><div class="gold">ושמחת המצוה</div></div>
<div id="bsd">בס״ד</div>
<div id="text">
 <div class="open navy lh">בהודאה להשי״ת על שזיכנו<br>לעמול בתורתו ולהשלים את לימוד<br>מסכת ראש השנה, הננו מתכבדים<br>להזמין את רבני ואברכי הכולל<br>להסב בצוותא בסעודת מצוה לרגל</div>
 <div class="big gold">סיום מסכת<br>ראש השנה</div>
 <div class="small navy">בשילוב</div>
 <div class="sh gold">שמחת שבע ברכות</div>
 <div class="rg navy lh">לרגל נישואי בנו של ידידנו הנכבד<br>המסור בלב ונפש למען הצלחת הכולל</div>
 <div class="nm navy">הרב דוד אייזנבאך שליט״א</div>
 <div class="orn"><i></i><b></b><i></i></div>
 <div class="date navy lh">המעמד יתקיים אי״ה<br>ביום שני הקרוב פרשת וירא<br>ט״ו במרחשוון תשפ״ז<br>בהיכל הכולל החדש (הזמני)<br>נטילת ידיים בשעה 9:00 בערב</div>
 <div class="bless navy lh">יהי רצון שנזכה להוסיף חיל בתורה ובעבודת ה׳,<br>ושתרבה השמחה במעוננו ובבתי כל העוסקים בתורה.</div>
 <div class="sig1 navy">בברכת התורה</div>
 <div class="sig2 navy">הנהלת הכולל</div>
</div>
<div id="foot" class="gold">גדול יהיה המעמד לכבוד התורה ולומדיה</div>
</body></html>`;
fs.writeFileSync('invite.html',html);

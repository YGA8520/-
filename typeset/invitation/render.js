const {chromium}=require('playwright');
(async()=>{const scale=+process.argv[3]||1;const b=await chromium.launch();
const p=await b.newPage({viewport:{width:1123,height:1587},deviceScaleFactor:scale});
await p.goto('file://'+process.argv[2]);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(800);
await p.screenshot({path:process.argv[4]});await b.close()})()

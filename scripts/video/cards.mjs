import {createRequire} from 'node:module';import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');const require=createRequire(path.join(root,'web/package.json'));const {chromium}=require('@playwright/test');
const out=path.join(root,'docs/demo/production');const timeline=JSON.parse(fs.readFileSync(path.join(out,'timeline.json')));const browser=await chromium.launch({headless:true});const meta={};
for(const scene of timeline.filter(s=>s.type==='card')){
const context=await browser.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:path.join(out,'raw'),size:{width:1920,height:1080}}});const page=await context.newPage();const video=page.video();
await page.goto('file://'+path.join(root,'scripts/video/cards.html'));await page.evaluate(()=>document.fonts.ready);
const start=Date.now();await page.evaluate(id=>window.showCard(id),scene.id);await page.waitForTimeout((scene.duration+1)*1000);await page.screenshot({path:path.join(out,scene.id+'.png')});const duration=(Date.now()-start)/1000;
await context.close();await video.saveAs(path.join(out,scene.id+'.webm'));meta[scene.id]={usable_seconds:duration};console.log('Rendered '+scene.id);
}await browser.close();fs.writeFileSync(path.join(out,'cards.json'),JSON.stringify(meta,null,2));

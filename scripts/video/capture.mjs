import {record} from './recorder.mjs';
import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const require=createRequire(path.join(root,'web/package.json'));
const {chromium}=require('@playwright/test');
const out=path.join(root,'docs/demo/production-v2');
const base='https://corridor-eosin.vercel.app';
const memory=JSON.parse(fs.readFileSync(path.join(root,'docs/m7-live-verification.json'),'utf8'));
fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const only=process.env.CAPTURE_SCENES?.split(',');
const manifest=only ? JSON.parse(fs.readFileSync(path.join(out,'capture.json'),'utf8')) : {base,recorded_at:new Date().toISOString(),scenes:{},errors:[]};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function setup(){
 const context=await browser.newContext({baseURL:base,viewport:{width:1920,height:1080}});
 await context.addInitScript(()=>{
  document.addEventListener('pointerdown',e=>{
   const ring=document.createElement('div');
   Object.assign(ring.style,{position:'fixed',left:(e.clientX-22)+'px',top:(e.clientY-22)+'px',width:'44px',height:'44px',border:'3px solid #83e2cc',borderRadius:'50%',zIndex:'2147483647',pointerEvents:'none',boxShadow:'0 0 0 8px #83e2cc22'});
   document.body.appendChild(ring);
   ring.animate([{transform:'scale(.35)',opacity:1},{transform:'scale(1.5)',opacity:0}],{duration:650,fill:'forwards'});
   setTimeout(()=>ring.remove(),700);
  },true);
 });
 const page=await context.newPage();
 page.on('pageerror',e=>manifest.errors.push(e.message));
 page.setDefaultTimeout(90000);
 return {context,page};
}
async function click(page,loc){const box=await loc.boundingBox();if(box)await page.mouse.move(box.x+box.width/2,box.y+box.height/2,{steps:18});await sleep(350);await loc.click();}
async function shot(id,prepare,action){
 if(only && !only.includes(id))return;
 const {context,page}=await setup();
 try {
  await prepare(page);await page.evaluate(()=>document.fonts.ready);await sleep(1800);
  const stop=await record(page,out,id);await action(page);await sleep(2000);
  const recording=await stop();const seconds=recording.usable_seconds;
  await page.screenshot({path:path.join(out,id+'.png')});
  await context.close();
  manifest.scenes[id]=recording;
  console.log('Captured '+id+' '+seconds.toFixed(1)+'s');
 }catch(e){await context.close();throw e;}
 fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify(manifest,null,2));
}
async function saved(page,caseId){await page.goto('/cases/'+caseId);await page.getByRole('button',{name:'Why this decision?'}).waitFor();await page.locator('canvas').waitFor();await sleep(2500);}
try{
 const check=await browser.newPage();
 for(let attempt=0;attempt<40;attempt++){
  await check.goto(base);
  await check.getByRole('button',{name:'View history for collector_0'}).click();
  await check.locator('.history-card').first().waitFor();
  const links=await check.locator('.history-card').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
  if(new Set(links).size===links.length)break;
  if(attempt===39)throw Error('History deduplication deployment not ready');
  await sleep(5000);
 }
 await check.close();
 await shot('03-queue',async p=>{await p.goto('/');await p.getByRole('button',{name:'Investigate collector_0',exact:true}).waitFor();},async p=>{
  await sleep(5000);const history=p.getByRole('button',{name:/history.*collector_0|collector_0.*history/i});
  if(await history.count()){await click(p,history.first());await p.locator('.history-card').first().waitFor();await sleep(6000);await p.keyboard.press('Escape');}
  await sleep(5000);
 });
 await shot('04-live',async p=>{await p.goto('/');await p.getByRole('button',{name:'Investigate collector_0',exact:true}).waitFor();},async p=>{
  await click(p,p.getByRole('button',{name:'Investigate collector_0',exact:true}));
  await p.waitForURL('**/cases/**');const id=p.url().split('/').pop();manifest.live_case_id=id;
  await p.evaluate(id=>{
   window.demoEvents=[];const es=new EventSource('/api/cases/'+id+'/stream');
   for(const type of ['opened','finding','guardrail','closed','end','snapshot'])es.addEventListener(type,e=>{window.demoEvents.push({type,id:e.lastEventId,at:Date.now()});if(type==='end')es.close();});
  },id);
  await p.getByRole('button',{name:'Why this decision?'}).waitFor({timeout:240000});
  await sleep(2500);
  manifest.events=await p.evaluate(()=>window.demoEvents);
  manifest.saved=await (await p.request.get('/api/cases/'+id)).json();
  if(manifest.saved.case.status!=='closed')throw Error('Hosted case did not close');
  if(!manifest.events.some(e=>e.type==='end'))throw Error('Hosted SSE did not end');
 });
 await shot('05-graph',p=>saved(p,manifest.live_case_id),async p=>{
  const findings=p.locator('.finding button').filter({hasText:/incoming transfers|shared identifiers|historical connections/i});
  if(await findings.count())await click(p,findings.first());
  await sleep(4000);await click(p,p.getByRole('button',{name:'Use flat view'}));await sleep(4000);
  await click(p,p.getByRole('button',{name:'Zoom in'}));await sleep(4000);await click(p,p.getByRole('button',{name:'Fit graph to view'}));
  await sleep(4000);await click(p,p.getByRole('button',{name:'Use spatial view'}));
  const canvas=await p.locator('canvas').boundingBox();if(canvas){await p.mouse.move(canvas.x+canvas.width*.5,canvas.y+canvas.height*.5);await p.mouse.down();await p.mouse.move(canvas.x+canvas.width*.6,canvas.y+canvas.height*.55,{steps:35});await p.mouse.up();}
  await sleep(5000);
 });
 await shot('07-company',p=>saved(p,manifest.live_case_id),async p=>{
  await sleep(5000);const heading=p.getByText('Company grounding',{exact:true});await heading.scrollIntoViewIfNeeded();await sleep(5000);
  const assignee=p.locator('.assignee');await assignee.scrollIntoViewIfNeeded();await sleep(10000);
 });
 await shot('08-replay',p=>saved(p,manifest.live_case_id),async p=>{
  await click(p,p.getByRole('button',{name:'Why this decision?'}));await sleep(4000);
  await click(p,p.getByRole('button',{name:'Next evidence'}));await sleep(4000);
  const details=p.locator('.finding').filter({hasText:'Review account history'}).getByText('Technical details',{exact:true});
  await click(p,details);await sleep(6000);
  await click(p,p.getByRole('button',{name:'Next evidence'}));await sleep(5000);
 });
 await shot('09-memory',p=>saved(p,memory.second_case.case_id),async p=>{
  await sleep(3500);const finding=p.locator('.finding').first();await click(p,finding.getByText('Technical details',{exact:true}));
  const raw=finding.locator('pre').filter({hasText:memory.first_case.case_id});
  await raw.scrollIntoViewIfNeeded();await sleep(14000);
  if(!(await finding.innerText()).includes(memory.first_case.case_id))throw Error('Memory match missing');
  manifest.memory={first:memory.first_case.case_id,second:memory.second_case.case_id,matched:true};
 });
 fs.writeFileSync(path.join(root,'docs/m9-hosted-verification.json'),JSON.stringify({frontend:base,api:'https://corridor-api.onrender.com',case_id:manifest.live_case_id,verdict:manifest.saved.case.verdict,events:manifest.events,errors:manifest.errors,memory:manifest.memory,recorded_at:manifest.recorded_at},null,2)+'\n');
}finally{await browser.close();}

/** Continuous Chrome screencast. Frame timestamps preserve real interaction timing.
 * JPEG quality 100 at native delivery resolution; no Playwright VP8 intermediate.
 */
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
export async function record(page, directory, id) {
  const dir=path.join(directory,'frames',id); fs.mkdirSync(dir,{recursive:true});
  const session=await page.context().newCDPSession(page);
  const frames=[];
  session.on('Page.screencastFrame', event=>{
    const file=path.join(dir,`${String(frames.length).padStart(6,'0')}.jpg`);
    fs.writeFileSync(file,Buffer.from(event.data,'base64'));
    frames.push({file,ts:event.metadata.timestamp});
    void session.send('Page.screencastFrameAck',{sessionId:event.sessionId}).catch(()=>{});
  });
  await session.send('Page.startScreencast',{format:'jpeg',quality:100,maxWidth:1920,maxHeight:1080,everyNthFrame:1});
  const start=Date.now();
  return async()=>{
    await session.send('Page.stopScreencast'); await session.detach();
    const seconds=(Date.now()-start)/1000;
    if(!frames.length)throw Error('Chrome produced no screencast frames');
    const lines=[];
    frames.forEach((f,i)=>{lines.push(`file '${f.file.replaceAll("'", "'\\''")}'`);lines.push(`duration ${Math.max(.001,i+1<frames.length?frames[i+1].ts-f.ts:seconds-(f.ts-frames[0].ts))}`);});
    lines.push(`file '${frames.at(-1).file}'`);
    const list=path.join(dir,'frames.txt');fs.writeFileSync(list,lines.join('\n'));
    const result=spawnSync('ffmpeg',['-y','-v','error','-f','concat','-safe','0','-i',list,'-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','fast','-crf','10','-threads','4','-t',String(seconds),path.join(directory,id+'.mp4')],{encoding:'utf8'});
    if(result.status!==0)throw Error(result.stderr);
    return {usable_seconds:seconds,frames:frames.length,capture:'Chrome continuous screencast / JPEG quality 100 / native 1920×1080'};
  };
}

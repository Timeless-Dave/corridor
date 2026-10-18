"""Deterministic FFmpeg edit: real hosted footage, animated cards, narration and captions."""
import json, math, subprocess, textwrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/demo/production'
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
scenes=json.loads((OUT/'timeline.json').read_text())
FPS=30

def run(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))

def scene_render(scene):
    sid=scene['id'];capture=json.loads((OUT/'capture.json').read_text())['scenes'];cards=json.loads((OUT/'cards.json').read_text())
    usable=(capture if scene['type']=='capture' else cards)[sid]['usable_seconds']
    source=OUT/(sid+'.webm');start=max(0,duration(source)-usable)
    target=round(scene['duration']*FPS)/FPS;scene['duration']=target
    title=OUT/(sid+'-chapter.txt');title.write_text(scene['chapter'])
    # A gentle move toward the subject, then back to the complete workspace.
    amount,fx,fy={ '03-queue':(.08,.45,.44),'04-live':(.12,.25,.50),'05-graph':(.22,.55,.49),
        '07-company':(.48,.88,.66),'08-replay':(.30,.24,.56),'09-memory':(.55,.16,.78)}.get(sid,(.025,.5,.5))
    frames=round(target*FPS)
    zoom=f"1+{amount}*pow(sin(PI*on/{max(1,frames-1)}),2)"
    vf=(f"setpts={(target/usable):.8f}*(PTS-STARTPTS),fps={FPS},scale=1920:1080:flags=lanczos,"
        f"zoompan=z='{zoom}':x='max(0,min(iw-iw/zoom,iw*{fx}-iw/zoom/2))':y='max(0,min(ih-ih/zoom,ih*{fy}-ih/zoom/2))':d=1:s=1920x1080:fps={FPS},"
        "setsar=1,format=yuv420p,"
        "drawbox=x=0:y=0:w=iw:h=76:color=0x0b1114@0.96:t=fill,"
        "drawbox=x=70:y=25:w=5:h=28:color=0x83e2cc:t=fill,"
        f"drawtext=fontfile='{BOLD}':textfile='{title}':fontcolor=0xcce1da:fontsize=24:x=96:y=26,"
        f"drawtext=fontfile='{FONT}':text='SYNTHETIC DATA  /  AI VOICE':fontcolor=0x8daaa0:fontsize=20:x=w-tw-70:y=28,"
        "drawbox=x=0:y=940:w=iw:h=140:color=0x0b1114@0.96:t=fill")
    af=f'adelay=300:all=1,apad,atrim=duration={target},asetpts=PTS-STARTPTS'
    args=['ffmpeg','-y','-v','error','-ss',str(start),'-t',str(usable),'-i',str(source),'-i',str(OUT/(sid+'.wav')),
          '-filter_complex',f'[0:v]{vf}[v];[1:a]{af}[a]','-map','[v]','-map','[a]','-t',str(target),
          '-c:v','libx264','-preset','fast','-crf','18','-threads','4','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(OUT/(sid+'-edited.mp4'))]
    try: run(args)
    except subprocess.CalledProcessError as e: print(e.stderr.decode()[-3000:]);raise
    print('Edited '+sid,flush=True)
    return scene

def assemble():
    args=['ffmpeg','-y','-v','error']
    for s in scenes:args+=['-i',str(OUT/(s['id']+'-edited.mp4'))]
    graph=[];vp='0:v';ap='0:a';total=scenes[0]['duration']
    for i,s in enumerate(scenes[1:],1):
        graph += [f'[{vp}][{i}:v]xfade=transition=fade:duration=0.5:offset={total-.5:.6f}[v{i}]',
                  f'[{ap}][{i}:a]acrossfade=d=0.5:c1=tri:c2=tri[a{i}]']
        vp=f'v{i}';ap=f'a{i}';total+=s['duration']-.5
    args+=['-filter_complex_threads','2','-filter_complex',';'.join(graph),'-map',f'[{vp}]','-map',f'[{ap}]',
           '-c:v','libx264','-preset','fast','-crf','18','-threads','4','-c:a','aac','-b:a','192k','-movflags','+faststart',str(OUT/'master-uncaptioned.mp4')]
    try:run(args)
    except subprocess.CalledProcessError as e:print(e.stderr.decode()[-3000:]);raise
    print(f'Assembled {total:.2f}s',flush=True)
    (OUT/'timeline.json').write_text(json.dumps(scenes,indent=2))
    run(['ffmpeg','-y','-v','error','-i',str(OUT/'master-uncaptioned.mp4'),'-vn','-ac','1','-ar','24000',str(OUT/'narration-master.wav')])

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool: scenes=list(pool.map(scene_render,scenes))
    assemble()

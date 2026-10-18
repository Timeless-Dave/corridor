"""Deterministic FFmpeg edit: real hosted footage, animated cards, narration and captions."""
import json, math, subprocess, textwrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/demo/production-v2'
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
    source=OUT/(sid+('.mp4' if scene['type']=='capture' else '.webm'));start=max(0,duration(source)-usable)
    target=round(scene['duration']*FPS)/FPS;scene['duration']=target
    title=OUT/(sid+'-chapter.txt');title.write_text(scene['chapter'])
    # Keep most shots steady; apply two short focus moves for detailed evidence.
    # Fit footage between title/caption bands so no product UI is covered.
    focus=""
    if sid in ('07-company', '09-memory'):
        # Two deliberate focus moves only: ease in, hold, ease out.
        ramp="max(0,min(1,(on/30-3)/0.8))"
        leave=f"max(0,min(1,({target}-1-on/30)/0.8))"
        eased=f"({ramp})*({ramp})*(3-2*({ramp}))*({leave})*({leave})*(3-2*({leave}))"
        zoom=f"1+0.32*({eased})"
        fx=.87 if sid=='07-company' else .15
        focus=(f"scale=3840:2160:flags=lanczos,zoompan=z='{zoom}':"
               f"x='max(0,min(iw-iw/zoom,iw*{fx}-iw/zoom/2))':"
               "y='max(0,min(ih-ih/zoom,ih*.62-ih/zoom/2))':d=1:s=1920x1080:fps=30,")
    vf=(f"setpts={(target/usable):.8f}*(PTS-STARTPTS),fps={FPS}," +
        focus+"scale=1680:945:flags=lanczos,pad=1920:1080:120:50:color=0x0b1114,"
        "setsar=1,format=yuv420p,"
        f"drawtext=fontfile='{BOLD}':textfile='{title}':fontcolor=0xcce1da:fontsize=20:x=120:y=16,")
    vf=vf.rstrip(',')
    af=f'adelay=300:all=1,apad,atrim=duration={target},asetpts=PTS-STARTPTS'
    args=['ffmpeg','-y','-v','error','-ss',str(start),'-t',str(usable),'-i',str(source),'-i',str(OUT/(sid+'.wav')),
          '-filter_complex',f'[0:v]{vf}[v];[1:a]{af}[a]','-map','[v]','-map','[a]','-t',str(target),
          '-c:v','libx264','-preset','fast','-crf','12','-threads','4','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(OUT/(sid+'-edited.mp4'))]
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
           '-c:v','libx264','-preset','fast','-crf','12','-threads','4','-c:a','aac','-b:a','192k','-movflags','+faststart',str(OUT/'master-uncaptioned.mp4')]
    try:run(args)
    except subprocess.CalledProcessError as e:print(e.stderr.decode()[-3000:]);raise
    print(f'Assembled {total:.2f}s',flush=True)
    (OUT/'timeline.json').write_text(json.dumps(scenes,indent=2))
    run(['ffmpeg','-y','-v','error','-i',str(OUT/'master-uncaptioned.mp4'),'-vn','-ac','1','-ar','24000',str(OUT/'narration-master.wav')])

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool: scenes=list(pool.map(scene_render,scenes))
    assemble()

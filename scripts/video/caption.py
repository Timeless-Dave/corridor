"""Timestamp the generated narration, align the approved script, and export captions."""
import json,re,textwrap,difflib,subprocess
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/demo/production';load_dotenv(ROOT/'.env')
cache=OUT/'transcription.json'
if not cache.exists():
    with (OUT/'narration-master.wav').open('rb') as file:
        result=OpenAI(timeout=180,max_retries=1).audio.transcriptions.create(
            model='whisper-1',file=file,language='en',response_format='verbose_json',
            timestamp_granularities=['word','segment'],
            prompt='Corridor, FalkorDB, Cypher, Vercel, Render, MCP, mule zero. Synthetic graph-native payment investigation demo.')
    cache.write_text(result.model_dump_json(indent=2))
r=json.loads(cache.read_text());words=r['words']
script=' '.join(s['text'] for s in json.loads((ROOT/'scripts/video/storyboard.json').read_text())).split()
norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
match=difflib.SequenceMatcher(None,[norm(w) for w in script],[norm(w['word']) for w in words],autojunk=False)
aligned=[];diff=[]
for tag,a,b,c,d in match.get_opcodes():
    if tag=='equal':
        aligned.extend({'text':script[i],'start':words[c+i-a]['start'],'end':words[c+i-a]['end']} for i in range(a,b))
    else:
        diff.append({'kind':tag,'script':' '.join(script[a:b]),'heard':' '.join(w['word'] for w in words[c:d])})
        if b>a:
            start=words[c]['start'] if c<len(words) else words[-1]['end']
            end=words[d-1]['end'] if d>c else start+.2
            for i in range(a,b):aligned.append({'text':script[i],'start':start+(end-start)*(i-a)/(b-a),'end':start+(end-start)*(i-a+1)/(b-a)})
assert match.ratio()>.88, 'Narration differs materially from script; inspect transcription before export.'
def stamp(t,ass=False):
    total=round(t*(100 if ass else 1000));scale=100 if ass else 1000
    h=total//(3600*scale);m=(total//(60*scale))%60;s=(total//scale)%60;f=total%scale
    return f'{h}:{m:02}:{s:02}.{f:02}' if ass else f'{h:02}:{m:02}:{s:02},{f:03}'
groups=[];chunk=[]
for w in aligned:
    if chunk and (len(' '.join(x['text'] for x in chunk+[w]))>82 or w['start']-chunk[0]['start']>4.2):groups.append(chunk);chunk=[]
    chunk.append(w)
    if len(chunk)>=6 and w['text'][-1:] in '.;:?!':groups.append(chunk);chunk=[]
if chunk:groups.append(chunk)
srt=[];ass=['[Script Info]','ScriptType: v4.00+','PlayResX: 1920','PlayResY: 1080','WrapStyle: 0','','[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding','Style: Default,Arial,38,&H00F4F8F6,&H00F4F8F6,&H000C1214,&H000C1214,0,0,0,0,100,100,0,0,1,1,0,2,170,170,38,1','','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
for i,g in enumerate(groups):
    start=max(0,g[0]['start']-.04);end=g[-1]['end']+.13
    if i+1<len(groups):end=min(end,groups[i+1][0]['start']-.08)
    end=max(start+.2,end);text=' '.join(w['text'] for w in g);lines=[text]
    if len(text)>70:
        split=min((i for i,c in enumerate(text) if c==' '),key=lambda i:abs(i-len(text)/2))
        lines=[text[:split],text[split+1:]]
    srt.append(f'{i+1}\n{stamp(start)} --> {stamp(end)}\n'+ '\n'.join(lines)+'\n')
    ass.append(f'Dialogue: 0,{stamp(start,True)},{stamp(end,True)},Default,,0,0,0,,'+r'{\an2\pos(960,1042)}'+'\\N'.join(lines))
(ROOT/'docs/demo/corridor-submission.srt').write_text('\n'.join(srt))
(OUT/'captions.ass').write_text('\n'.join(ass)+'\n')
(OUT/'caption-verification.json').write_text(json.dumps({'alignment_ratio':match.ratio(),'script_words':len(script),'recognized_words':len(words),'differences':diff,'caption_cues':len(groups)},indent=2))
print(json.dumps({'alignment':match.ratio(),'cues':len(groups),'differences':diff},indent=2))

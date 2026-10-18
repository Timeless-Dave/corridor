"""Derive scene lengths from the actual generated speech, not estimated reading time."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/demo/production-v2'
scenes=json.loads((ROOT/'scripts/video/storyboard.json').read_text())
for scene in scenes:
    scene['voice_seconds']=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(OUT/(scene['id']+'.wav'))]))
    scene['duration']=round((scene['voice_seconds']+1)*30)/30
(OUT/'timeline.json').write_text(json.dumps(scenes,indent=2)+'\n')
print('Final timeline:',sum(s['duration'] for s in scenes)-.5*(len(scenes)-1),'seconds')

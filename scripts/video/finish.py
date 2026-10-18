"""Burn readable captions, master audio, and produce the upload-ready MP4."""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'docs/demo/production-v2'
log=(OUT/'loudness-analysis.log').read_text();measure=json.loads(re.findall(r'\{[^{}]+\}',log)[-1])
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(OUT/'master-uncaptioned.mp4')]))
fade_start=max(0,duration-.48)
af=('loudnorm=I=-16:TP=-1.5:LRA=11:'+f"measured_I={measure['input_i']}:measured_TP={measure['input_tp']}:measured_LRA={measure['input_lra']}:measured_thresh={measure['input_thresh']}:offset={measure['target_offset']}:linear=true"+f',afade=t=in:d=0.15,afade=t=out:st={fade_start}:d=0.45')
args=['ffmpeg','-y','-v','error','-i',str(OUT/'master-uncaptioned.mp4'),'-vf',f"ass='{OUT/'captions.ass'}',fade=t=in:d=0.3,fade=t=out:st={fade_start}:d=0.45",'-af',af,'-c:v','libx264','-preset','slow','-crf','18','-threads','4','-c:a','aac','-b:a','192k','-ar','48000','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','title=Corridor — Connected evidence. Accountable decisions.','-metadata','comment=Real hosted app footage; live section condensed; saved evidence labeled. Synthetic data. AI-generated OpenAI Cedar narration.',str(ROOT/'docs/demo/corridor-submission.mp4')]
subprocess.run(args,check=True)
print('Final export complete',flush=True)

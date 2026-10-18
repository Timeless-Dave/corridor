"""Generate authorized OpenAI narration; cache each scene to avoid duplicate charges."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/demo/production-v2'
load_dotenv(ROOT/'.env')
scenes=json.loads((ROOT/'scripts/video/storyboard.json').read_text())

def speak(scene):
    dest=OUT/(scene['id']+'.wav')
    if dest.exists(): return {'id':scene['id'],'cached':True}
    client=OpenAI(timeout=120, max_retries=1)
    with client.audio.speech.with_streaming_response.create(
        model='gpt-4o-mini-tts', voice='cedar', response_format='wav',
        input=scene['text'], speed=1.04,
        instructions='Professional documentary narration. Warm, clear, calm confidence; engaged but not salesy. Natural American English. Read at a steady brisk presentation pace, around 160 words per minute. Small pauses at sentence boundaries. Pronounce Corridor as corridor, FalkorDB as Fal-core D B, Cypher as cipher, MCP as M C P. Do not add words. Do not whisper. Keep consistent volume and delivery across this scene.'
    ) as response:
        response.stream_to_file(dest)
    return {'id':scene['id'],'bytes':dest.stat().st_size}

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(speak,scenes): print(json.dumps(result),flush=True)

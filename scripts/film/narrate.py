"""OpenAI TTS per scene, cached; then write public/timeline.json with measured voice lengths."""
import json, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
AUDIO = HERE / 'public/audio'
load_dotenv(HERE.parents[1] / '.env')
scenes = json.loads((HERE / 'storyboard.json').read_text())


def speak(scene):
    dest = AUDIO / (scene['id'] + '.wav')
    stamp = dest.with_suffix('.txt')
    if dest.exists() and stamp.exists() and stamp.read_text() == scene['text']:
        return scene['id'] + ' cached'
    with OpenAI(timeout=120, max_retries=1).audio.speech.with_streaming_response.create(
        model='gpt-4o-mini-tts', voice='cedar', response_format='wav', input=scene['text'], speed=1.05,
        instructions='Professional product-demo narration. Warm, clear, confident, never salesy. Natural American English, '
                     'brisk presentation pace around 165 words per minute, small pauses at sentence boundaries. Pronounce '
                     'Corridor as corridor, FalkorDB as Fal-core D B, Cypher as cipher, ajo as AH-joe. Do not add words.'
    ) as response:
        response.stream_to_file(dest)
    stamp.write_text(scene['text'])
    return scene['id'] + ' generated'


def seconds(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'default=nw=1:nk=1', str(path)]))


if __name__ == '__main__':
    AUDIO.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for line in pool.map(speak, scenes): print(line, flush=True)
    for s in scenes:
        s['voice_seconds'] = seconds(AUDIO / (s['id'] + '.wav'))
    (HERE / 'public/timeline.json').write_text(json.dumps(scenes, indent=2) + '\n')
    print('voice total', round(sum(s['voice_seconds'] for s in scenes), 1), 's')

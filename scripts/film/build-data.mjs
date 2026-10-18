// Merges narration timing, capture logs and the case's measured plan into src/film.json.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const API = process.env.FILM_API ?? 'http://127.0.0.1:8010';
const FPS = 30, LEAD = 0.5, TAIL = 0.9;
const read = f => JSON.parse(fs.readFileSync(path.join(HERE, f), 'utf8'));
const timeline = read('public/timeline.json');
const manifest = read('public/capture/manifest.json');
const clips = Object.fromEntries(['live', 'impact', 'evidence'].map(id => [id, read(`public/capture/${id}.json`)]));
const mark = (clip, name) => clips[clip].events.find(e => e.type === 'mark' && e.name === name).t;

const ranges = {
  '02-queue': ['live', 0, mark('live', 'investigate') + 0.9],
  '03-live': ['live', mark('live', 'investigate') + 0.9, clips.live.duration],
  '05-impact': ['impact', 0, mark('impact', 'approve')],
  '07-approve': ['impact', mark('impact', 'approve'), clips.impact.duration],
  '08-evidence': ['evidence', 0, clips.evidence.duration],
};

const impact = await (await fetch(`${API}/cases/${manifest.case_id}/freeze-impact`)).json();
const order = impact.orders[0];
const scenes = timeline.map(s => {
  const seconds = s.voice_seconds + LEAD + TAIL;
  const scene = {id: s.id, type: s.type, chapter: s.chapter, title: s.title, text: s.text,
    voice: s.voice_seconds, lead: LEAD, frames: Math.round(seconds * FPS)};
  if (s.type === 'capture') {
    const [clip, from, to] = ranges[s.id];
    const span = to - from;
    const rate = Math.min(3.5, Math.max(0.8, span / seconds));
    scene.clip = {src: `capture/${clip}.mp4`, from, to, rate: +rate.toFixed(3),
      events: clips[clip].events.filter(e => e.t >= from - 0.05 && e.t <= to + 0.05 || e.type === 'move' && e.t < from)};
  }
  return scene;
});
const plan = impact.plan;
const film = {fps: FPS, case_id: manifest.case_id, account: manifest.account, attempts: manifest.attempts,
  plan: {freeze: plan.freeze_ids, before: plan.before, after: plan.after, collector: plan.collector},
  receipt: order ? {matched: order.measurement?.matched_projection, id: order.order.id} : null,
  scenes, totalFrames: scenes.reduce((n, s) => n + s.frames, 0)};
fs.writeFileSync(path.join(HERE, 'src/film.json'), JSON.stringify(film, null, 1));
console.log(scenes.map(s => `${s.id} ${(s.frames / FPS).toFixed(1)}s${s.clip ? ` rate ${s.clip.rate}` : ''}`).join('\n'));
console.log('total', (film.totalFrames / FPS).toFixed(1), 's');

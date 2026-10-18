import React from 'react';
import {AbsoluteFill, Freeze, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, MONO, clamp01, easeInOut} from './theme';

type Rect = {x: number; y: number; w: number; h: number};
type Ev = {type: string; t: number; rect?: Rect; hold?: number; from?: {x: number; y: number}; to?: {x: number; y: number};
  ms?: number; x?: number; y?: number; name?: string};
export type Clip = {src: string; from: number; to: number; rate: number; events: Ev[]};

const W = 1920, H = 1080, FULL: Rect = {x: 0, y: 0, w: W, h: H};
const D = 0.75, MAX_ZOOM = 2.0;
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const lerpRect = (a: Rect, b: Rect, k: number): Rect => ({x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), w: lerp(a.w, b.w, k), h: lerp(a.h, b.h, k)});

function keyframes(clip: Clip) {
  const out = (t: number) => (t - clip.from) / clip.rate;
  const focus = clip.events.filter(e => e.type === 'focus').map(e => ({t: out(e.t), end: out(e.t) + Math.max(e.hold! / clip.rate, 1.1), rect: e.rect!}));
  const kfs: {t: number; rect: Rect}[] = [];
  focus.forEach((f, i) => {
    kfs.push({t: Math.max(0, f.t - 0.15), rect: f.rect});
    const next = focus[i + 1];
    if (!next || next.t > f.end + 0.6) kfs.push({t: f.end, rect: FULL});
  });
  return kfs;
}

function cameraAt(kfs: {t: number; rect: Rect}[], t: number): Rect {
  let start = FULL, prev: {t: number; rect: Rect} | null = null;
  for (const k of kfs) {
    if (k.t > t) break;
    if (prev) start = lerpRect(start, prev.rect, easeInOut(clamp01((k.t - prev.t) / D)));
    prev = k;
  }
  return prev ? lerpRect(start, prev.rect, easeInOut(clamp01((t - prev.t) / D))) : FULL;
}

function transformFor(r: Rect) {
  const s = Math.min(MAX_ZOOM, Math.max(1, Math.min(W / r.w, H / r.h)));
  const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
  const tx = Math.min(0, Math.max(W - W * s, W / 2 - cx * s));
  const ty = Math.min(0, Math.max(H - H * s, H / 2 - cy * s));
  return {s, tx, ty};
}

function cursorAt(clip: Clip, t: number) {
  const moves = clip.events.filter(e => e.type === 'move');
  if (!moves.length) return null;
  let pos = moves[0].from!;
  for (const m of moves) {
    const start = (m.t - clip.from) / clip.rate, dur = m.ms! / 1000 / clip.rate;
    if (start > t) break;
    const k = easeInOut(clamp01((t - start) / dur));
    pos = {x: lerp(m.from!.x, m.to!.x, k), y: lerp(m.from!.y, m.to!.y, k)};
  }
  return pos;
}

export const Capture: React.FC<{clip: Clip; chapter: string}> = ({clip, chapter}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const playFrames = Math.floor(((clip.to - clip.from) / clip.rate) * fps);
  const kfs = React.useMemo(() => keyframes(clip), [clip]);
  const cam = transformFor(cameraAt(kfs, t));
  const cursor = cursorAt(clip, t);
  const clicks = clip.events.filter(e => e.type === 'click').map(e => ({...e, at: (e.t - clip.from) / clip.rate}));
  const pressed = clicks.some(c => t >= c.at && t < c.at + 0.18);
  const cursorScale = 1 / Math.sqrt(cam.s);
  const speed = clip.rate > 1.1 ? ` · ${clip.rate.toFixed(1)}× SPEED` : '';
  return (
    <AbsoluteFill style={{background: C.bg, overflow: 'hidden'}}>
      <div style={{position: 'absolute', width: W, height: H, transformOrigin: '0 0',
        transform: `translate(${cam.tx}px, ${cam.ty}px) scale(${cam.s})`}}>
        <Freeze frame={Math.min(frame, playFrames - 1)}>
          <OffthreadVideo src={staticFile(clip.src)} startFrom={Math.round(clip.from * fps)} playbackRate={clip.rate} muted
            style={{width: W, height: H}} />
        </Freeze>
        {clicks.filter(c => t >= c.at && t < c.at + 0.7).map((c, i) => {
          const k = clamp01((t - c.at) / 0.7);
          const r = lerp(8, 42, easeInOut(k)) * cursorScale;
          return <div key={i} style={{position: 'absolute', left: c.x! - r, top: c.y! - r, width: r * 2, height: r * 2, borderRadius: '50%',
            border: `${3 * cursorScale}px solid ${C.teal}`, opacity: 1 - k, boxShadow: `0 0 ${18 * cursorScale}px ${C.teal}88`}} />;
        })}
        {cursor && (
          <svg width={28} height={34} viewBox="0 0 28 34" style={{position: 'absolute', left: cursor.x - 3, top: cursor.y - 2,
            transformOrigin: '3px 2px', transform: `scale(${cursorScale * (pressed ? 0.86 : 1)})`, filter: 'drop-shadow(0 2px 4px rgba(0,0,0,.55))'}}>
            <path d="M3 2 L3 27 L9.5 21 L14 31 L18.5 29 L14 19.5 L23 19.5 Z" fill="#fff" stroke="#0b1111" strokeWidth={1.6} strokeLinejoin="round" />
          </svg>
        )}
      </div>
      <div style={{position: 'absolute', left: 36, top: 30, padding: '9px 16px', borderRadius: 999, background: 'rgba(8,13,13,.86)',
        border: `1px solid ${C.line}`, color: C.teal, fontFamily: MONO, fontSize: 19, letterSpacing: 1.5}}>
        {chapter}{speed}
      </div>
    </AbsoluteFill>
  );
};

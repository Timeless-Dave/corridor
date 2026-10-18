import React from 'react';
import {AbsoluteFill, Audio, Sequence, Series, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Capture, Clip} from './Capture';
import {cards} from './Cards';
import {C, SANS} from './theme';
import film from './film.json';

type Scene = (typeof film.scenes)[number] & {clip?: Clip};

function chunks(text: string, voice: number, lead: number) {
  const parts = text.match(/[^.!?]+[.!?]+/g)?.map(p => p.trim()) ?? [text];
  const total = parts.reduce((n, p) => n + p.length, 0);
  let at = lead;
  return parts.map(p => {
    const d = (p.length / total) * voice;
    const c = {text: p, from: at, to: at + d};
    at += d;
    return c;
  });
}

const Captions: React.FC<{s: Scene}> = ({s}) => {
  const t = useCurrentFrame() / useVideoConfig().fps;
  const list = React.useMemo(() => chunks(s.text, s.voice, s.lead), [s]);
  const cur = list.find(c => t >= c.from && t < c.to + 0.25);
  if (!cur) return null;
  const k = Math.min(1, (t - cur.from) / 0.15);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 46, display: 'flex', justifyContent: 'center', opacity: k}}>
      <div style={{maxWidth: 1460, padding: '14px 26px', borderRadius: 14, background: 'rgba(6,10,10,.84)', color: C.text,
        fontFamily: SANS, fontSize: 36, lineHeight: 1.3, textAlign: 'center', fontWeight: 500}}>{cur.text}</div>
    </div>
  );
};

const SceneView: React.FC<{s: Scene}> = ({s}) => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 9, s.frames - 9, s.frames], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const Card = cards[s.id];
  return (
    <AbsoluteFill style={{background: C.bg}}>
      <AbsoluteFill style={{opacity: fade}}>
        {s.clip ? <Capture clip={s.clip} chapter={s.chapter} /> : <Card s={s} />}
        <Captions s={s} />
      </AbsoluteFill>
      <Sequence from={Math.round(s.lead * film.fps)}>
        <Audio src={staticFile(`audio/${s.id}.wav`)} />
      </Sequence>
    </AbsoluteFill>
  );
};

export const Film: React.FC = () => (
  <AbsoluteFill style={{background: C.bg}}>
    <Series>
      {(film.scenes as Scene[]).map(s => (
        <Series.Sequence key={s.id} durationInFrames={s.frames}>
          <SceneView s={s} />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);

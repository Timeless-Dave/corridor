import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, MONO, SANS, clamp01, easeInOut} from './theme';
import film from './film.json';

const useT = () => useCurrentFrame() / useVideoConfig().fps;
const rise = (t: number, at: number, d = 0.7) => {
  const k = easeInOut(clamp01((t - at) / d));
  return {opacity: k, transform: `translateY(${(1 - k) * 28}px)`};
};

const Backdrop: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{background: `radial-gradient(1200px 700px at 70% 30%, #133331 0%, ${C.bg} 60%)`, fontFamily: SANS, color: C.text}}>
    <svg width="1920" height="1080" style={{position: 'absolute', opacity: 0.25}}>
      <defs><pattern id="dots" width="32" height="32" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill={C.line} /></pattern></defs>
      <rect width="1920" height="1080" fill="url(#dots)" />
    </svg>
    {children}
  </AbsoluteFill>
);

const Chapter: React.FC<{text: string; t: number}> = ({text, t}) => (
  <div style={{...rise(t, 0.1), fontFamily: MONO, fontSize: 22, letterSpacing: 3, color: C.teal}}>{text}</div>
);

const Title: React.FC<{text: string; t: number; at?: number; size?: number}> = ({text, t, at = 0.3, size = 92}) => (
  <div style={{fontSize: size, fontWeight: 600, lineHeight: 1.06, letterSpacing: -2.5}}>
    {text.split('\n').map((line, i) => <div key={i} style={rise(t, at + i * 0.35)}>{line}</div>)}
  </div>
);

// Flow graph: senders stream particles into a collector. `cut` 0..1 removes the collector's edges.
const Flow: React.FC<{t: number; cx: number; cy: number; n: number; radius: number; cut?: number; label?: string; dim?: number}> =
  ({t, cx, cy, n, radius, cut = 0, label, dim = 1}) => {
  const nodes = Array.from({length: n}, (_, i) => {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2;
    return {x: cx + Math.cos(a) * radius, y: cy + Math.sin(a) * radius};
  });
  return (
    <g opacity={dim}>
      {nodes.map((p, i) => {
        const alive = 1 - cut;
        const phase = (t * 0.55 + i / n) % 1;
        return (
          <g key={i}>
            <line x1={p.x} y1={p.y} x2={cx} y2={cy} stroke={cut > 0.05 ? C.red : C.teal} strokeOpacity={0.15 + 0.4 * alive}
              strokeWidth={2.4} strokeDasharray={cut > 0.05 ? '8 8' : undefined} />
            {alive > 0.05 && <circle cx={p.x + (cx - p.x) * phase} cy={p.y + (cy - p.y) * phase} r={5} fill={C.teal} opacity={alive} />}
            <circle cx={p.x} cy={p.y} r={14} fill={C.panel} stroke={C.teal} strokeWidth={2.5} />
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r={30} fill={cut > 0.5 ? '#3a1d1b' : '#173b36'} stroke={cut > 0.5 ? C.red : C.teal} strokeWidth={3} />
      {label && <text x={cx} y={cy + 62} fill={C.text} fontFamily={MONO} fontSize={22} textAnchor="middle">{label}</text>}
    </g>
  );
};

export const Hook: React.FC<{s: any}> = ({s}) => {
  const t = useT();
  return (
    <Backdrop>
      <svg width="1920" height="1080" style={{position: 'absolute'}}>
        <Flow t={t} cx={1500} cy={470} n={12} radius={270} dim={0.85} />
      </svg>
      <div style={{position: 'absolute', left: 140, top: 210, width: 1100}}>
        <Chapter text={s.chapter} t={t} />
        <div style={{height: 36}} />
        <Title text={s.title} t={t} size={72} />
        <div style={{...rise(t, 6.5), marginTop: 48, fontSize: 34, color: C.muted, lineHeight: 1.4}}>
          Corridor tests a freeze on a <span style={{color: C.teal}}>copy of the graph</span> before anyone applies it.
        </div>
      </div>
      <div style={{position: 'absolute', right: 80, top: 56, fontFamily: MONO, fontSize: 18, color: C.muted, ...rise(t, 1)}}>
        Synthetic data · AI-generated narration · Built on FalkorDB
      </div>
    </Backdrop>
  );
};

export const Copy: React.FC<{s: any}> = ({s}) => {
  const t = useT();
  const p = film.plan;
  const copyIn = easeInOut(clamp01((t - 2.2) / 1));
  const cut = easeInOut(clamp01((t - 5.2) / 1.4));
  const gone = easeInOut(clamp01((t - 12.2) / 1));
  const row = (label: string, a: string, b: string, at: number) => (
    <div style={{...rise(t, at), display: 'flex', justifyContent: 'space-between', padding: '14px 0', borderBottom: `1px solid ${C.line}`, fontSize: 28}}>
      <span style={{color: C.muted}}>{label}</span>
      <span style={{fontFamily: MONO}}>{a} <span style={{color: C.muted}}>→</span> <span style={{color: C.teal}}>{b}</span></span>
    </div>
  );
  return (
    <Backdrop>
      <div style={{position: 'absolute', left: 120, top: 56}}>
        <Chapter text={s.chapter} t={t} />
        <div style={{height: 14}} />
        <Title text={s.title} t={t} size={60} />
      </div>
      <svg width="1920" height="1080" style={{position: 'absolute'}}>
        <rect x={120} y={215} width={640} height={470} rx={18} fill={C.panel} stroke={C.line} />
        <text x={150} y={258} fill={C.muted} fontFamily={MONO} fontSize={21}>corridor · live graph</text>
        <Flow t={t} cx={440} cy={460} n={4} radius={150} label={p.collector} />
        <g opacity={copyIn}>
          <line x1={790} y1={450} x2={1000} y2={450} stroke={C.teal} strokeWidth={3} markerEnd="url(#arrow)" />
          <defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 Z" fill={C.teal} /></marker></defs>
          <text x={895} y={430} fill={C.teal} fontFamily={MONO} fontSize={22} textAnchor="middle">GRAPH.COPY</text>
        </g>
        <g opacity={copyIn * (1 - gone * 0.75)}>
          <rect x={1030} y={215} width={640} height={470} rx={18} fill={C.panel} stroke={gone > 0.3 ? C.red : C.teal} strokeDasharray="10 8" />
          <text x={1060} y={258} fill={C.muted} fontFamily={MONO} fontSize={21}>corridor_sim_… · scratch copy</text>
          <Flow t={t} cx={1350} cy={460} n={4} radius={150} cut={cut} label={`block ${p.freeze.join(', ')}`} />
        </g>
        {gone > 0.02 && <text x={1350} y={250} opacity={gone} fill={C.red} fontFamily={MONO} fontSize={26} textAnchor="middle">copy deleted</text>}
      </svg>
      <div style={{position: 'absolute', left: 1030, top: 705, width: 640}}>
        {row('Senders reaching collector', String(p.before.senders_reaching_collector), String(p.after.senders_reaching_collector), 6.6)}
        {row('Historical inflow', `$${p.before.inflow_volume}`, `$${p.after.inflow_volume}`, 7.6)}
        {row('Cycle paths', String(p.before.cycles_remaining), String(p.after.cycles_remaining), 8.6)}
      </div>
      <div style={{position: 'absolute', left: 120, top: 715, width: 640, fontSize: 24, color: C.muted, lineHeight: 1.5, ...rise(t, 9.5)}}>
        Live graph unchanged. Numbers are this case's real measurement; the drawing is illustrative.
      </div>
    </Backdrop>
  );
};

export const Guardrails: React.FC<{s: any}> = ({s}) => {
  const t = useT();
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const items = [
    ['Two independent positive evidence tools cite the same account', 4.2],
    ['PageRank or label-propagation results are recorded', 6.4],
    ['A completed, non-empty scratch-graph freeze plan exists', 8.6],
  ] as const;
  return (
    <Backdrop>
      <div style={{position: 'absolute', left: 140, top: 150, width: 1640}}>
        <Chapter text={s.chapter} t={t} />
        <div style={{height: 28}} />
        <Title text={s.title} t={t} size={84} />
        <div style={{marginTop: 70, display: 'flex', flexDirection: 'column', gap: 22}}>
          <div style={{...rise(t, 3.4), fontFamily: MONO, fontSize: 22, color: C.muted, letterSpacing: 2}}>FREEZE STANDS ONLY IF</div>
          {items.map(([text, at]) => {
            const pop = spring({frame: frame - Math.round((at + 0.4) * fps), fps, config: {damping: 14}});
            return (
              <div key={text} style={{...rise(t, at), display: 'flex', alignItems: 'center', gap: 26, fontSize: 38, padding: '20px 28px',
                background: C.panel, border: `1px solid ${C.line}`, borderRadius: 16}}>
                <div style={{width: 44, height: 44, borderRadius: 12, background: '#173b36', display: 'grid', placeItems: 'center',
                  transform: `scale(${pop})`, color: C.teal, fontSize: 30}}>✓</div>
                {text}
              </div>
            );
          })}
          <div style={{...rise(t, 11), fontSize: 36, color: C.amber, marginTop: 14}}>
            Otherwise → downgraded to <span style={{fontFamily: MONO}}>MONITOR</span>, with the reason recorded on the case.
          </div>
        </div>
      </div>
    </Backdrop>
  );
};

export const Eval: React.FC<{s: any}> = ({s}) => {
  const t = useT();
  const rows = [
    ['Initial run', '4 / 4', '1 / 8', '0.80', '1.00', 6.0],
    ['Final code', '4 / 4', '0 / 8', '1.00', '1.00', 7.2],
  ] as const;
  const cell = {padding: '22px 26px', fontSize: 34, borderBottom: `1px solid ${C.line}`};
  return (
    <Backdrop>
      <div style={{position: 'absolute', left: 140, top: 120, width: 1640}}>
        <Chapter text={s.chapter} t={t} />
        <div style={{height: 28}} />
        <Title text={s.title} t={t} size={80} />
        <div style={{...rise(t, 1.6), marginTop: 26, fontSize: 30, color: C.muted}}>
          8 decoys: families sharing a device · savings pools paying out normally · one-way businesses
        </div>
        <table style={{marginTop: 54, width: '100%', borderCollapse: 'collapse', background: C.panel, borderRadius: 16, ...rise(t, 4.6)}}>
          <thead><tr style={{fontFamily: MONO, fontSize: 20, color: C.muted, textAlign: 'left'}}>
            {['RUN', 'RINGS ALERTED', 'DECOYS ALERTED', 'PRECISION', 'RECALL'].map(h => <th key={h} style={{...cell, fontSize: 20, fontWeight: 500}}>{h}</th>)}
          </tr></thead>
          <tbody>{rows.map(([name, rings, decoys, p, r, at]) => (
            <tr key={name} style={rise(t, at)}>
              <td style={cell}>{name}</td><td style={{...cell, fontFamily: MONO}}>{rings}</td>
              <td style={{...cell, fontFamily: MONO, color: decoys.startsWith('0') ? C.teal : C.amber}}>{decoys}</td>
              <td style={{...cell, fontFamily: MONO}}>{p}</td><td style={{...cell, fontFamily: MONO}}>{r}</td>
            </tr>))}</tbody>
        </table>
        <div style={{...rise(t, 12), marginTop: 30, fontSize: 24, color: C.muted, fontFamily: MONO}}>
          12 hand-built synthetic cases · gpt-4.1-mini · alert = FREEZE or MONITOR · not a real-world benchmark
        </div>
      </div>
    </Backdrop>
  );
};

export const Close: React.FC<{s: any}> = ({s}) => {
  const t = useT();
  return (
    <Backdrop>
      <svg width="1920" height="1080" style={{position: 'absolute'}}>
        <Flow t={t} cx={1450} cy={540} n={8} radius={240} cut={easeInOut(clamp01((t - 2.4) / 1.2))} dim={0.8} />
      </svg>
      <div style={{position: 'absolute', left: 140, top: 250}}>
        <Chapter text={s.chapter} t={t} />
        <div style={{height: 30}} />
        <Title text={s.title} t={t} size={96} />
        <div style={{...rise(t, 2.8), marginTop: 60, fontFamily: MONO, fontSize: 28, color: C.teal, lineHeight: 1.7}}>
          corridor-eosin.vercel.app<br />github.com/Timeless-Dave/corridor
        </div>
        <div style={{...rise(t, 3.4), marginTop: 30, fontSize: 24, color: C.muted}}>
          Track 01: Agents That Act on Connected Data · FalkorDB · synthetic data · no real funds frozen
        </div>
      </div>
    </Backdrop>
  );
};

export const cards: Record<string, React.FC<{s: any}>> = {
  '01-hook': Hook, '04-copy': Copy, '06-guardrails': Guardrails, '09-eval': Eval, '10-close': Close,
};
export {interpolate};

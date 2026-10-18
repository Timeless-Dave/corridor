import {continueRender, delayRender, staticFile} from 'remotion';

export const C = {
  bg: '#0b1111',
  panel: '#121a1a',
  line: '#24302f',
  text: '#e6efed',
  muted: '#8fa3a0',
  teal: '#83e2cc',
  amber: '#e8b45c',
  red: '#e0736a',
  violet: '#a78bdb',
};
export const SANS = 'Geist, system-ui, sans-serif';
export const MONO = '"Geist Mono", ui-monospace, monospace';

const faces: [string, string, string][] = [
  ['Geist', 'geist-latin-400-normal.woff2', '400'],
  ['Geist', 'geist-latin-500-normal.woff2', '500'],
  ['Geist', 'geist-latin-600-normal.woff2', '600'],
  ['Geist Mono', 'geist-mono-latin-400-normal.woff2', '400'],
  ['Geist Mono', 'geist-mono-latin-500-normal.woff2', '500'],
];
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = faces.map(([family, file, weight]) =>
    `@font-face{font-family:'${family}';src:url(${staticFile('fonts/' + file)}) format('woff2');font-weight:${weight};font-display:block}`).join('');
  document.head.appendChild(style);
  const handle = delayRender('fonts', {timeoutInMilliseconds: 120000, retries: 2});
  Promise.all(faces.map(([family, file, weight]) => {
    const face = new FontFace(family, `url(${staticFile('fonts/' + file)})`, {weight});
    document.fonts.add(face);
    return face.load();
  })).then(() => continueRender(handle));
}

export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const clamp01 = (t: number) => Math.max(0, Math.min(1, t));

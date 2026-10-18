// Records real app sessions with Puppeteer (CDP screencast) and logs cursor moves, clicks
// and focus regions with timestamps. Remotion replays the log as zooms, cursor and ripples.
import puppeteer from 'puppeteer';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'public/capture');
const BASE = process.env.FILM_BASE ?? 'http://localhost:3010';
const API = process.env.FILM_API ?? 'http://127.0.0.1:8010';
const ACCOUNT = process.env.FILM_ACCOUNT ?? 'ajo_0';
const env = Object.fromEntries(fs.readFileSync(path.join(HERE, '../../.env'), 'utf8').split('\n')
  .filter(l => l.includes('=') && !l.startsWith('#')).map(l => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1)]));
const TOKEN = env.CORRIDOR_APPROVAL_TOKEN;
if (!TOKEN) throw Error('CORRIDOR_APPROVAL_TOKEN missing from .env');
fs.mkdirSync(OUT, {recursive: true});
const sleep = ms => new Promise(r => setTimeout(r, ms));
const W = 1920, H = 1080;

async function record(page, id) {
  const dir = path.join(OUT, 'frames', id);
  fs.rmSync(dir, {recursive: true, force: true});
  fs.mkdirSync(dir, {recursive: true});
  const session = await page.createCDPSession();
  const frames = [], events = [];
  session.on('Page.screencastFrame', e => {
    const file = path.join(dir, String(frames.length).padStart(6, '0') + '.jpg');
    fs.writeFileSync(file, Buffer.from(e.data, 'base64'));
    frames.push({file, ts: e.metadata.timestamp});
    session.send('Page.screencastFrameAck', {sessionId: e.sessionId}).catch(() => {});
  });
  await session.send('Page.startScreencast', {format: 'jpeg', quality: 95, maxWidth: W, maxHeight: H, everyNthFrame: 1});
  const log = (type, data) => events.push({type, at: Date.now() / 1000, ...data});
  const stop = async () => {
    await sleep(400);
    const end = Date.now() / 1000;
    await session.send('Page.stopScreencast');
    await session.detach();
    if (!frames.length) throw Error('no frames');
    const t0 = frames[0].ts;
    const lines = [];
    frames.forEach((f, i) => {
      lines.push(`file '${f.file}'`);
      lines.push(`duration ${Math.max(0.001, (i + 1 < frames.length ? frames[i + 1].ts : end) - f.ts)}`);
    });
    lines.push(`file '${frames.at(-1).file}'`);
    fs.writeFileSync(path.join(dir, 'list.txt'), lines.join('\n'));
    const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(dir, 'list.txt'),
      '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-movflags', '+faststart',
      '-t', String(end - t0), path.join(OUT, id + '.mp4')], {encoding: 'utf8'});
    if (r.status !== 0) throw Error(r.stderr);
    const out = {id, duration: end - t0, frames: frames.length,
      events: events.map(e => ({...e, t: +(e.at - t0).toFixed(3), at: undefined}))};
    fs.writeFileSync(path.join(OUT, id + '.json'), JSON.stringify(out, null, 1));
    fs.rmSync(dir, {recursive: true, force: true});
    console.log(`recorded ${id}: ${out.duration.toFixed(1)}s, ${frames.length} frames, ${events.length} events`);
    return out;
  };
  return {log, stop};
}

function director(page, rec) {
  let pos = {x: W * 0.62, y: H * 0.55};
  const ease = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  async function rectOf(target, pad = 16) {
    const handle = typeof target === 'string' ? await page.waitForSelector(target, {visible: true}) : target;
    const b = await handle.boundingBox();
    if (!b) throw Error('no box for ' + target);
    return {x: Math.max(0, b.x - pad), y: Math.max(0, b.y - pad), w: Math.min(W, b.width + pad * 2), h: Math.min(H, b.height + pad * 2)};
  }
  async function moveTo(x, y, ms = 750) {
    const from = {...pos}, n = Math.max(8, Math.round(ms / 16));
    rec.log('move', {from, to: {x, y}, ms});
    for (let i = 1; i <= n; i++) {
      const k = ease(i / n);
      await page.mouse.move(from.x + (x - from.x) * k, from.y + (y - from.y) * k);
      await sleep(ms / n);
    }
    pos = {x, y};
  }
  async function click(target, {ms = 750, settle = 250} = {}) {
    const r = await rectOf(target, 0);
    const x = r.x + r.w / 2, y = r.y + r.h / 2;
    await moveTo(x, y, ms);
    await sleep(settle);
    rec.log('click', {x, y});
    await page.mouse.down();
    await sleep(70);
    await page.mouse.up();
  }
  async function focus(target, hold, {pad = 24, label} = {}) {
    const rect = await rectOf(target, pad);
    rec.log('focus', {rect, hold: hold / 1000, label});
    await sleep(hold);
  }
  async function scrollInto(selector, block = 'start') {
    await page.$eval(selector, (el, block) => el.scrollIntoView({behavior: 'smooth', block}), block);
    await sleep(900);
  }
  return {click, focus, moveTo, scrollInto, rectOf, get pos() { return pos; }};
}

async function byText(page, selector, text) {
  const h = await page.waitForFunction((sel, t) => [...document.querySelectorAll(sel)].find(e => e.innerText.includes(t)), {}, selector, text);
  return h.asElement();
}

async function newPage(browser) {
  const page = await browser.newPage();
  await page.setViewport({width: W, height: H, deviceScaleFactor: 1});
  page.setDefaultTimeout(120000);
  page.on('pageerror', e => console.warn('pageerror', e.message));
  return page;
}

async function liveRun(browser) {
  const page = await newPage(browser);
  await page.goto(BASE + '/', {waitUntil: 'networkidle0'});
  await page.evaluate(() => document.fonts.ready);
  const button = `button[aria-label="Investigate ${ACCOUNT}"]`;
  const row = await page.waitForSelector(button).then(b => b.evaluateHandle(el => el.closest('tr') ?? el.closest('[role=row]') ?? el.parentElement.parentElement));
  await sleep(800);
  const rec = await record(page, 'live');
  const d = director(page, rec);
  await sleep(1200);
  await d.focus('.queue-page', 2600, {pad: 0, label: 'queue'});
  await d.moveTo(420, 525, 900);
  await d.focus(row, 3200, {pad: 20, label: 'row'});
  await d.click(button, {ms: 900, settle: 500});
  rec.log('mark', {name: 'investigate'});
  await page.waitForFunction(() => location.pathname.startsWith('/cases/'));
  const caseId = (await page.evaluate(() => location.pathname)).split('/').pop();
  await page.waitForSelector('.evidence-panel');
  await d.moveTo(1700, 960, 700);
  await d.focus('.evidence-panel', 1500, {pad: 0, label: 'trail'});
  const seen = new Set();
  const deadline = Date.now() + 240000;
  while (Date.now() < deadline) {
    const closed = await page.evaluate(() => [...document.querySelectorAll('button')].some(b => b.innerText.includes('Why this decision?')));
    const titles = await page.$$eval('.finding-select', els => els.map(e => e.innerText.split('\n').find(t => t && !/^\d+$/.test(t.trim())) ?? ''));
    for (let i = 0; i < titles.length; i++) {
      if (seen.has(i)) continue;
      seen.add(i);
      if (/Rank transfer collectors|Explore account communities|Measure a greedy freeze set|Review pool payouts|Trace shared identifiers/.test(titles[i])) {
        const cards = await page.$$('.finding-select');
        await cards[i].evaluate(el => el.scrollIntoView({block: 'center', behavior: 'smooth'}));
        await sleep(500);
        const card = await cards[i].evaluateHandle(el => el.closest('article.finding') ?? el);
        await d.focus(card, 1800, {pad: 18, label: titles[i]});
      }
    }
    if (closed) break;
    await sleep(400);
  }
  rec.log('mark', {name: 'closed'});
  await sleep(1200);
  await d.focus('.decision-content', 3500, {pad: 10, label: 'verdict'});
  const out = await rec.stop();
  const data = await (await fetch(`${API}/cases/${caseId}`)).json();
  await page.close();
  return {caseId, verdict: data.case.verdict, proposed: data.case.proposed_verdict, reasons: data.case.guardrail_reasons, out};
}

async function impactAndApprove(browser, caseId) {
  const page = await newPage(browser);
  await page.goto(`${BASE}/cases/${caseId}`, {waitUntil: 'networkidle0'});
  await page.waitForSelector('.freeze-impact');
  await page.evaluate(() => document.fonts.ready);
  await page.$eval('.freeze-impact', el => el.scrollIntoView({block: 'start'}));
  await sleep(2500);
  const rec = await record(page, 'impact');
  const d = director(page, rec);
  await sleep(800);
  await d.focus('.freeze-impact', 2400, {pad: 12, label: 'panel'});
  await d.click(await byText(page, '.freeze-impact button', 'simulation'), {ms: 900});
  rec.log('mark', {name: 'simulate'});
  await page.waitForFunction(() => !document.querySelector('.freeze-impact button')?.innerText.includes('Measuring'), {polling: 100});
  await sleep(700);
  await d.focus('.impact-table', 6500, {pad: 14, label: 'table'});
  await d.focus('.impact-steps', 2600, {pad: 60, label: 'steps'});
  await d.click('.freeze-impact details:not(.approval-gate) summary', {ms: 700});
  await sleep(500);
  await d.focus('.freeze-impact details:not(.approval-gate)', 4200, {pad: 16, label: 'method'});
  await d.click('.freeze-impact details:not(.approval-gate) summary', {ms: 500});
  await sleep(600);
  rec.log('mark', {name: 'approve'});
  await d.click('.approval-gate summary', {ms: 800});
  await sleep(600);
  await page.$eval('.approval-gate', el => el.scrollIntoView({block: 'center', behavior: 'smooth'}));
  await sleep(900);
  await d.focus('.approval-gate', 2600, {pad: 16, label: 'gate'});
  await d.click('.approval-gate input[type=password]', {ms: 700});
  await page.keyboard.type(TOKEN, {delay: 45});
  await sleep(400);
  await d.click('.approval-gate input[type=checkbox]', {ms: 700});
  await sleep(700);
  await d.click('.approval-gate button', {ms: 700, settle: 400});
  await page.waitForSelector('.freeze-impact .guardrail-summary', {timeout: 120000});
  await sleep(500);
  await page.$eval('.freeze-impact .guardrail-summary', el => el.scrollIntoView({block: 'center', behavior: 'smooth'}));
  await sleep(900);
  await d.moveTo(1500, 1000, 600);
  await d.focus('.freeze-impact .guardrail-summary', 7000, {pad: 22, label: 'receipt'});
  const out = await rec.stop();
  const receipt = await page.$eval('.freeze-impact .guardrail-summary', el => el.innerText);
  await page.close();
  return {out, receipt};
}

async function evidence(browser, caseId) {
  const page = await newPage(browser);
  await page.goto(`${BASE}/cases/${caseId}`, {waitUntil: 'networkidle0'});
  await page.waitForSelector('canvas');
  await page.evaluate(() => document.fonts.ready);
  await sleep(2500);
  const rec = await record(page, 'evidence');
  const d = director(page, rec);
  await sleep(600);
  const card = await byText(page, 'article.finding', 'Review pool payouts');
  await d.click(await card.$('.finding-select'), {ms: 900});
  await sleep(500);
  await d.focus('.graph-panel', 3800, {pad: 0, label: 'graph'});
  await d.click(await card.$('summary'), {ms: 800});
  await sleep(700);
  await card.evaluate(el => el.scrollIntoView({block: 'start', behavior: 'smooth'}));
  await sleep(900);
  await d.focus('.evidence-panel', 4500, {pad: 0, label: 'details'});
  await d.scrollInto('.grounding-section', 'start');
  await d.moveTo(1640, 700, 700);
  await d.focus('.grounding-section', 5500, {pad: 14, label: 'grounding'});
  await sleep(800);
  const out = await rec.stop();
  await page.close();
  return {out};
}

const browser = await puppeteer.launch({headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars']});
const manifest = {base: BASE, account: ACCOUNT, recorded_at: new Date().toISOString(), attempts: []};
try {
  // One live run, narrated with whatever verdict it reaches; approval uses FILM_CASE (a saved FREEZE run).
  let live = null;
  if (process.env.FILM_SKIP_LIVE) {
    const prev = JSON.parse(fs.readFileSync(path.join(OUT, 'manifest.json'), 'utf8')).live;
    live = {caseId: prev.case_id, verdict: prev.verdict, proposed: prev.proposed, reasons: prev.reasons};
  }
  for (let attempt = 1; attempt <= 2 && !live; attempt++) {
    try { live = await liveRun(browser); } catch (e) { console.warn('live attempt failed', e.message); }
  }
  if (!live) throw Error('live run failed');
  manifest.live = {case_id: live.caseId, verdict: live.verdict, proposed: live.proposed, reasons: live.reasons};
  console.log('live', JSON.stringify(manifest.live));
  if (!process.env.FILM_CASE && live.verdict !== 'FREEZE') throw Error('Set FILM_CASE to a saved FREEZE case.');
  manifest.case_id = process.env.FILM_CASE ?? live.caseId;
  const impact = await impactAndApprove(browser, manifest.case_id);
  manifest.receipt = impact.receipt;
  await evidence(browser, manifest.case_id);
  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(JSON.stringify(manifest, null, 2));
} finally {
  await browser.close();
}

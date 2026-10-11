#!/usr/bin/env node
/**
 * Builds public/data/instruments.json — the full NSE equity master (~2,500 EQ/BE symbols).
 *
 * Source: https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv
 * Runs automatically before `next build` (prebuild). It NEVER fails the build:
 * if NSE is unreachable it keeps the existing file, or falls back to the bundled seed.
 *
 *   node scripts/sync-instruments.mjs           # skip if file already exists
 *   node scripts/sync-instruments.mjs --force   # always refetch
 */
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const out = resolve(root, 'public/data/instruments.json');
const URL_ = process.env.NSE_EQUITY_CSV_URL || 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv';
const force = process.argv.includes('--force');

const exists = async (p) => access(p).then(() => true, () => false);

function parseCsvLine(line) {
  const cells = [];
  let cur = '';
  let q = false;
  for (const ch of line) {
    if (ch === '"') q = !q;
    else if (ch === ',' && !q) {
      cells.push(cur.trim());
      cur = '';
    } else cur += ch;
  }
  cells.push(cur.trim());
  return cells;
}

async function main() {
  if (!force && (await exists(out))) {
    console.log('[instruments] public/data/instruments.json exists — skipping (use --force to refresh)');
    return;
  }
  const seed = JSON.parse(await readFile(resolve(root, 'data/seed-instruments.json'), 'utf8'));
  const sectors = new Map(seed.map(([s, , sec]) => [s, sec]));

  let rows = null;
  try {
    const res = await fetch(URL_, {
      headers: { 'User-Agent': 'Mozilla/5.0 (UpCircuit instrument sync)', Accept: 'text/csv,*/*' },
      signal: AbortSignal.timeout(20000),
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const lines = (await res.text()).split(/\r?\n/).filter(Boolean);
    const head = parseCsvLine(lines[0]).map((h) => h.toUpperCase());
    const iSym = head.indexOf('SYMBOL');
    const iName = head.findIndex((h) => h.startsWith('NAME OF'));
    const iSeries = head.findIndex((h) => h.includes('SERIES'));
    if (iSym < 0 || iName < 0) throw new Error('unexpected CSV header: ' + lines[0]);
    rows = [];
    for (const l of lines.slice(1)) {
      const c = parseCsvLine(l);
      const series = iSeries >= 0 ? c[iSeries] : 'EQ';
      if (!c[iSym] || !['EQ', 'BE', 'BZ', 'SM', 'ST'].includes(series)) continue;
      rows.push({ symbol: c[iSym], name: c[iName], sector: sectors.get(c[iSym]) ?? 'Others' });
    }
    console.log(`[instruments] fetched ${rows.length} NSE equities`);
  } catch (e) {
    console.warn('[instruments] NSE fetch failed (' + e.message + ').');
  }

  if (!rows || rows.length < 500) {
    if (await exists(out)) {
      console.warn('[instruments] keeping existing file.');
      return;
    }
    rows = seed.map(([symbol, name, sector]) => ({ symbol, name, sector }));
    console.warn(`[instruments] using bundled seed (${rows.length}). Run \`npm run sync:instruments\` on a network that can reach nsearchives.nseindia.com for the full list.`);
  }
  rows.sort((a, b) => a.symbol.localeCompare(b.symbol));
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, JSON.stringify(rows));
  console.log(`[instruments] wrote ${rows.length} → public/data/instruments.json`);
}

main().catch((e) => {
  console.warn('[instruments] non-fatal error:', e.message);
  process.exit(0);
});

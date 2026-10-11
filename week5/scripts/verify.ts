/* Core logic checks — run with `npm test`. No framework: plain assertions, exits non-zero on failure. */
import assert from 'node:assert/strict';
import { SEED_INSTRUMENTS } from '../lib/instruments';
import { MarketEngine, TIMEFRAMES, TF_CONFIG, generateHistory } from '../lib/market';
import {
  capClass, correlationMatrix, hhi, longTermOutlook, pearson, pivotLevels, portfolioSummary, rsi14, sharpe, shortTermOutlook, sma, topMovers, vwap, macd,
} from '../lib/analytics';
import { parsePortfolioCsv } from '../lib/csv';
import { parseRss, decodeEntities } from '../lib/news';
import { scoreText } from '../lib/sentiment';
import { buildIndex, searchInstruments } from '../lib/fuzzy';
import { getFundamentals } from '../lib/fundamentals';
import { answerLocally, detectIntent, isContext, type CopilotContext } from '../lib/copilot';
import { TtlCache, allow } from '../lib/ttlCache';
import {
  cumulativeReturnPct, dividendForecast, intradaySigma, liquidityRatio, portfolioDiagnostics, portfolioValueSeries, sectorIndexSeries, sharpeParts, tickVolumeBuckets, vwapBands, weightedRiskScore,
} from '../lib/analytics';
import { encodeTick, parseTick, subscribeMessage, totp, type SmartTick } from '../lib/smartapi';
import { isMarketOpen, SmartApiFeed } from '../lib/market';
import { parseHoldingsText } from '../lib/portfolioText';

let passed = 0;
const t = (name: string, fn: () => void) => {
  try {
    fn();
    passed++;
    console.log('  ✓', name);
  } catch (e) {
    console.error('  ✗', name, '\n   ', (e as Error).message);
    process.exitCode = 1;
  }
};
const near = (a: number, b: number, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} ≉ ${b}`);

console.log('analytics');
t('pivot levels (H110 L100 C105)', () => {
  const p = pivotLevels(110, 100, 105);
  near(p.p, 105); near(p.r1, 110); near(p.s1, 100); near(p.r2, 115); near(p.s2, 95);
});
t('pearson: +1, −1, 0, flat series', () => {
  near(pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1);
  near(pearson([1, 2, 3, 4], [8, 6, 4, 2]), -1);
  near(pearson([1, 2, 3, 4, 5], [2, 4, 2, 4, 2]), 0, 0.5);
  assert.equal(pearson([1, 1, 1], [1, 2, 3]), 0);
});
t('correlation matrix is symmetric with unit diagonal', () => {
  const { matrix } = correlationMatrix({ A: [1, 2, 3, 5, 4, 6], B: [2, 1, 4, 3, 6, 5], C: [9, 8, 7, 8, 6, 5] });
  for (let i = 0; i < 3; i++) { near(matrix[i][i], 1); for (let j = 0; j < 3; j++) near(matrix[i][j], matrix[j][i]); }
});
t('RSI: rising → 100, falling → 0, bounded', () => {
  assert.equal(rsi14(Array.from({ length: 30 }, (_, i) => 100 + i)), 100);
  near(rsi14(Array.from({ length: 30 }, (_, i) => 100 - i))!, 0);
  const r = rsi14([44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.1, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.0, 46.03, 46.41, 46.22, 45.64])!;
  assert.ok(r > 55 && r < 75, 'classic Wilder sample should be ~60s, got ' + r);
});
t('VWAP = Σ(P·V)/ΣV', () => { near(vwap([10, 20], [1, 3])!, 17.5); assert.equal(vwap([], []), null); });
t('HHI: 4 equal = 2500, single = 10000', () => { near(hhi([1, 1, 1, 1]), 2500); near(hhi([5]), 10000); });
t('portfolio P&L = Σ(LTP×Qty) − invested', () => {
  const s = portfolioSummary([{ symbol: 'A', qty: 10, avg: 100 }, { symbol: 'B', qty: 5, avg: 200 }], (sym) => (sym === 'A' ? { ltp: 110, prevClose: 108 } : { ltp: 190, prevClose: 195 }));
  near(s.invested, 2000); near(s.current, 2050); near(s.pnl, 50); near(s.pnlPct, 2.5); near(s.dayPnl, 2050 - (1080 + 975));
});
t('SMA / MACD basics', () => { near(sma([1, 2, 3, 4, 5], 5)!, 3); assert.equal(sma([1], 5), null); assert.ok(macd(Array.from({ length: 60 }, (_, i) => 100 + i))!.hist !== undefined); });
t('Sharpe is null for short / flat series', () => { assert.equal(sharpe([1, 2, 3]), null); assert.equal(sharpe(Array(40).fill(100)), null); });
t('cap classes', () => { assert.equal(capClass(150000), 'Large'); assert.equal(capClass(50000), 'Mid'); assert.equal(capClass(5000), 'Small'); });

console.log('csv');
t('valid file', () => {
  const r = parsePortfolioCsv('symbol,quantity,buy_price\nRELIANCE,10,2500.50\nTCS,5,"3,400"\n');
  assert.deepEqual(r.holdings, [{ symbol: 'RELIANCE', qty: 10, avg: 2500.5 }, { symbol: 'TCS', qty: 5, avg: 3400 }]);
  assert.equal(r.errors.length, 0);
});
t('BOM, CRLF, header aliases, lowercase symbols', () => {
  const r = parsePortfolioCsv('﻿Ticker,Qty,Avg Price\r\ninfy,3,1500\r\n');
  assert.deepEqual(r.holdings, [{ symbol: 'INFY', qty: 3, avg: 1500 }]);
});
t('duplicates merge at weighted average', () => {
  const r = parsePortfolioCsv('symbol,quantity,buy_price\nSBIN,10,100\nSBIN,30,200');
  assert.deepEqual(r.holdings, [{ symbol: 'SBIN', qty: 40, avg: 175 }]);
  assert.equal(r.warnings.length, 1);
});
t('bad rows are reported with line numbers, good rows kept', () => {
  const r = parsePortfolioCsv('symbol,quantity,buy_price\nITC,0,400\nITC,2.5,400\n,1,1\nHDFC BANK!,1,1\nITC,4,abc\nSBIN,1,500', new Set(['ITC', 'SBIN']));
  assert.equal(r.holdings.length, 1);
  assert.equal(r.errors.length, 5);
  assert.match(r.errors[0], /^Row 2/);
});
t('unknown symbols rejected when a master is supplied', () => {
  const r = parsePortfolioCsv('symbol,quantity,buy_price\nNOPE,1,1', new Set(['ITC']));
  assert.equal(r.holdings.length, 0); assert.match(r.errors[0], /not in the NSE/);
});
t('wrong header / empty file', () => {
  assert.match(parsePortfolioCsv('a,b,c\n1,2,3').errors[0], /Header must be/);
  assert.match(parsePortfolioCsv('').errors[0], /empty/);
});

console.log('news + sentiment');
t('RSS 2.0 with CDATA, entities, dates', () => {
  const xml = `<rss><channel><item><title><![CDATA[Sensex jumps 500 pts &amp; Nifty hits record high]]></title><link>https://x.test/a</link><pubDate>Fri, 09 Oct 2026 10:00:00 +0530</pubDate></item>
  <item><title>Plain &quot;title&quot;</title><link>https://x.test/b</link></item><item><title>No link</title></item></channel></rss>`;
  const items = parseRss(xml);
  assert.equal(items.length, 2);
  assert.equal(items[0].title, 'Sensex jumps 500 pts & Nifty hits record high');
  assert.equal(items[1].title, 'Plain "title"');
  assert.ok(items[0].published > 0 && items[1].published === 0);
});
t('Atom entries', () => {
  const items = parseRss('<feed><entry><title>Hello</title><link href="https://y.test/1"/><updated>2026-10-09T05:00:00Z</updated></entry></feed>');
  assert.equal(items.length, 1); assert.equal(items[0].link, 'https://y.test/1');
});
t('entities', () => assert.equal(decodeEntities('A&nbsp;&amp;&#8211;&#x2013;B &unknown;'), 'A &––B &unknown;'));
t('headline sentiment direction', () => {
  assert.equal(scoreText('Nifty surges to record high as banks rally').label, 'Bullish');
  assert.equal(scoreText('Sensex crashes as FIIs dump stocks').label, 'Bearish');
  assert.equal(scoreText('Auto sales fall short of estimates, shares slump').label, 'Bearish');
  assert.equal(scoreText('Company beats estimates, announces buyback').label, 'Bullish');
  assert.equal(scoreText('RBI board meeting scheduled for Friday').label, 'Neutral');
  const s = scoreText('anything at all'); assert.ok(s.score >= -1 && s.score <= 1);
});

console.log('market engine');
t('history: all 10 timeframes well-formed', () => {
  const now = Date.UTC(2026, 9, 9, 6, 0, 0); // a Friday
  for (const tf of TIMEFRAMES) {
    const h = generateHistory('RELIANCE', tf, 1234.5, now);
    assert.equal(h.length, TF_CONFIG[tf].bars, tf + ' length');
    near(h[h.length - 1].close, 1234.5, 0.01);
    for (let i = 0; i < h.length; i++) {
      const b = h[i];
      assert.ok(b.high >= Math.max(b.open, b.close) - 1e-9 && b.low <= Math.min(b.open, b.close) + 1e-9, `${tf} OHLC @${i}`);
      assert.ok(b.volume > 0);
      if (i > 0) assert.ok(b.time > h[i - 1].time, `${tf} time order @${i}`);
    }
    if (tf === '1W' || tf === '5Y') assert.equal(new Date(h[h.length - 1].time * 1000).getUTCDay(), 1, 'weeks start Monday');
    if (tf === '1M' || tf === '10Y') assert.equal(new Date(h[h.length - 1].time * 1000).getUTCDate(), 1, 'months start on the 1st');
    if (tf === '1D' || tf === '1Y') h.forEach((b) => assert.ok(![0, 6].includes(new Date(b.time * 1000).getUTCDay()), 'no weekend bars'));
  }
});
t('history is deterministic', () => {
  const a = generateHistory('TCS', '1D', 100, 1.7e12), b = generateHistory('TCS', '1D', 100, 1.7e12);
  assert.deepEqual(a, b);
});
t('same-sector pairs correlate more than cross-sector pairs', () => {
  const now = Date.UTC(2026, 9, 9, 6);
  const close = (s: string) => generateHistory(s, '1D', 100, now).map((c) => c.close);
  const same = ['HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'KOTAKBANK'];
  const other = ['TCS', 'ITC', 'MARUTI', 'SUNPHARMA', 'DLF'];
  const avg = (pairs: [string, string][]) => pairs.reduce((a, [x, y]) => a + correlationMatrix({ [x]: close(x), [y]: close(y) }).matrix[0][1], 0) / pairs.length;
  const sp: [string, string][] = []; const cp: [string, string][] = [];
  for (let i = 0; i < same.length; i++) for (let j = i + 1; j < same.length; j++) sp.push([same[i], same[j]]);
  for (let i = 0; i < same.length; i++) cp.push([same[i], other[i]]);
  const a = avg(sp), b = avg(cp);
  assert.ok(a > b + 0.05, `same ${a.toFixed(2)} should exceed cross ${b.toFixed(2)}`);
  assert.ok(b > 0.05, 'cross-sector corr should be positive (market factor) — got ' + b.toFixed(2));
});
t('engine: 5 min of ticks → prices stay inside circuits, alerts fire, kinds valid', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS);
  let now = Date.now();
  for (let i = 0; i < 4800; i++) { e.step('RELIANCE', now); now += 250; } // 20 simulated minutes
  e.quotes.forEach((q) => {
    assert.ok(q.ltp <= q.upperCircuit && q.ltp >= q.lowerCircuit, `${q.symbol} outside band`);
    assert.ok(q.high >= q.ltp && q.low <= q.ltp);
  });
  assert.ok(e.alerts.length > 0, 'expected simulated alerts');
  const kinds = new Set(e.alerts.map((a) => a.kind));
  console.log('      alert kinds seen:', [...kinds].join(', '), `(${e.alerts.length})`);
  e.alerts.forEach((a) => assert.ok(['UPPER_CIRCUIT', 'LOWER_CIRCUIT', 'PRICE_SURGE', 'VOLUME_SURGE'].includes(a.kind)));
  const ids = e.alerts.map((a) => a.id); assert.equal(new Set(ids).size, ids.length, 'unique alert ids');
  // cooldown: no (symbol, kind) twice within 5 min
  const seen = new Map<string, number>();
  [...e.alerts].reverse().forEach((a) => { const k = a.symbol + a.kind; if (seen.has(k)) assert.ok(a.time - seen.get(k)! >= 300_000, 'cooldown ' + k); seen.set(k, a.time); });
});
t('engine: volume spike detection needs >3× baseline', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS); e.simulateEvents = false;
  let now = Date.now();
  for (let i = 0; i < 400; i++) { e.step('TCS', now); now += 250; }
  assert.equal(e.alerts.filter((a) => a.kind === 'VOLUME_SURGE').length, 0, 'no spikes without injected events');
});
t('engine: rolling VWAP lies within the recent price range', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS); e.simulateEvents = false;
  for (let i = 0; i < 200; i++) e.step('INFY', Date.now());
  const v = e.rollingVwap(60_000)!; const q = e.quotes.get('INFY')!;
  assert.ok(v >= q.low && v <= q.high, `vwap ${v} not within ${q.low}..${q.high}`);
});
t('market-cap buckets are all populated across the seed universe', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS);
  const c = { Large: 0, Mid: 0, Small: 0 }; e.quotes.forEach((q) => c[capClass(q.mcapCr)]++);
  console.log('      Large/Mid/Small:', c.Large, c.Mid, c.Small);
  assert.ok(c.Large >= 10 && c.Mid >= 10 && c.Small >= 10);
});
t('top movers ordering', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS); const all = [...e.quotes.values()];
  const g = topMovers(all, 'gainers', 5), l = topMovers(all, 'losers', 5), v = topMovers(all, 'volume', 5);
  const pct = (q: (typeof all)[0]) => q.ltp / q.prevClose - 1;
  assert.ok(pct(g[0]) >= pct(g[4]) && pct(l[0]) <= pct(l[4]));
  assert.ok(v[0].volume * v[0].ltp >= v[4].volume * v[4].ltp);
});

console.log('search');
t('"south" → SOUTHBANK first; "sr" → SRF first', () => {
  const idx = buildIndex(SEED_INSTRUMENTS);
  assert.equal(searchInstruments(idx, 'south')[0].symbol, 'SOUTHBANK');
  assert.equal(searchInstruments(idx, 'sr')[0].symbol, 'SRF');
  assert.equal(searchInstruments(idx, 'south ind')[0].symbol, 'SOUTHBANK');
  assert.equal(searchInstruments(idx, 'relience')[0].symbol, 'RELIANCE', 'typo tolerance');
  assert.equal(searchInstruments(idx, '').length, 0);
});

console.log('fundamentals + copilot');
const mkCtx = (symbol = 'TCS'): CopilotContext => {
  const e = new MarketEngine(SEED_INSTRUMENTS); const q = e.quotes.get(symbol)!;
  const closes = generateHistory(symbol, '1D', q.ltp, Date.now()).map((c) => c.close);
  const prev = generateHistory(symbol, '1D', q.ltp, Date.now()).slice(-2)[0];
  const s = shortTermOutlook(closes), l = longTermOutlook(closes);
  return {
    symbol, name: q.name, sector: q.sector,
    price: { ltp: q.ltp, changePct: (q.ltp / q.prevClose - 1) * 100, dayHigh: q.high, dayLow: q.low, volume: q.volume, circuitBandPct: q.circuitBand },
    ratios: getFundamentals(q),
    technicals: { rsi: rsi14(closes), sma50: sma(closes, 50), sma200: sma(closes, 200), pivots: pivotLevels(prev.high, prev.low, prev.close), short: s && { label: s.label, score: s.score }, long: l && { label: l.label, score: l.score } },
    simulated: true,
  };
};
t('fundamentals are consistent (BV = EPS/ROE, banks have no D/E)', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS);
  const f = getFundamentals(e.quotes.get('TCS')!);
  near(f.bookValue, f.eps / (f.roe / 100), f.bookValue * 0.01); // 1 % slack: inputs are rounded for display
  assert.ok(f.pe > 0 && f.promoterHolding >= 0 && f.promoterHolding <= 100);
  assert.equal(getFundamentals(e.quotes.get('HDFCBANK')!).debtToEquity, null);
  assert.deepEqual(getFundamentals(e.quotes.get('TCS')!), getFundamentals(e.quotes.get('TCS')!));
});
t('outlooks produce labelled signals', () => {
  const closes = generateHistory('INFY', '1D', 1500, Date.now()).map((c) => c.close);
  const s = shortTermOutlook(closes)!, l = longTermOutlook(closes)!;
  assert.equal(s.signals.length, 4); assert.equal(l.signals.length, 5);
  assert.ok(s.score >= -100 && s.score <= 100 && ['Bullish', 'Bearish', 'Neutral'].includes(l.label));
  assert.equal(longTermOutlook(closes.slice(-100)), null);
});
t('intent routing', () => {
  assert.equal(detectIntent('Is it expensive?'), 'valuation');
  assert.equal(detectIntent('what is the debt situation'), 'debt');
  assert.equal(detectIntent('Where is support and resistance?'), 'technical');
  assert.equal(detectIntent('dividend yield?'), 'dividend');
  assert.equal(detectIntent('tell me about it'), 'summary');
});
t('local answers: every intent returns text with the disclaimer and real numbers', () => {
  const ctx = mkCtx();
  for (const q of ['Is it expensive?', 'How are ROE and ROCE?', 'debt?', 'dividend?', 'support resistance?', 'news sentiment?', 'key risks?', 'should I invest?', 'hi']) {
    const a = answerLocally(q, ctx, []);
    assert.match(a, /not investment advice/); assert.match(a, /simulated/);
    assert.ok(a.length > 80, q);
  }
  assert.match(answerLocally('Is it expensive?', ctx, []), new RegExp(ctx.ratios.pe.toFixed(1)));
  assert.doesNotMatch(answerLocally('debt?', mkCtx('HDFCBANK'), []), /Debt-to-equity is \d/);
  assert.ok(isContext(ctx) && !isContext({ symbol: 1 }) && !isContext(null));
});
t('TTL cache expiry + rate limiter', () => {
  const c = new TtlCache<number>(30); c.set('a', 1); assert.equal(c.get('a')?.value, 1);
  const origNow = Date.now; Date.now = () => origNow() + 100; assert.equal(c.get('a'), undefined); Date.now = origNow;
  assert.ok(allow('k', 2, 1000) && allow('k', 2, 1000) && !allow('k', 2, 1000));
});


console.log('expanded persona analytics');
t('VWAP bands: ΣPV/ΣV ± kσ (volume-weighted)', () => {
  const b = vwapBands([{ t: 0, p: 100, v: 1 }, { t: 1, p: 110, v: 3 }], 2)!;
  near(b.vwap, 107.5); near(b.sd, Math.sqrt((1 * 56.25 + 3 * 6.25) / 4)); near(b.upper, b.vwap + 2 * b.sd); near(b.lower, b.vwap - 2 * b.sd);
  assert.equal(vwapBands([]), null);
});
t('tick-volume buckets sum to the traded volume in the window', () => {
  const now = 1_000_000;
  const tr = [{ t: now - 1000, p: 1, v: 5 }, { t: now - 6000, p: 1, v: 7 }, { t: now - 200_000, p: 1, v: 99 }];
  const b = tickVolumeBuckets(tr, now, 5000, 36);
  assert.equal(b.length, 36); assert.equal(b.reduce((a, x) => a + x.volume, 0), 12);
});
t('intraday σ: flat → 0, noisy → positive, annualised = per-sample × √N', () => {
  near(intradaySigma(Array(25).fill(100), 1000)!.perSamplePct, 0);
  assert.equal(intradaySigma([100, 101], 1000), null);
  const r = intradaySigma(Array.from({ length: 25 }, (_, i) => 100 + (i % 3)), 10_000)!;
  assert.ok(r.perSamplePct > 0); near(r.annualisedPct, r.perSamplePct * 100);
});
t('liquidity ratio = turnover ÷ market cap', () => { near(liquidityRatio(50, 1000), 5); assert.equal(liquidityRatio(5, 0), 0); });
t('sector index rebased to 100; sharpe parts consistent with Sharpe formula', () => {
  const idx = sectorIndexSeries([[100, 101, 102, 103], [200, 202, 204, 206]]);
  assert.equal(idx[0], 100); assert.equal(idx.length, 4); assert.ok(idx[3] > 100);
  const v = Array.from({ length: 80 }, (_, i) => 100 * Math.exp(0.001 * i + 0.01 * Math.sin(i)));
  const p = sharpeParts(v)!;
  near(p.sharpe, (p.annReturnPct / 100 - 0.065) / (p.annVolPct / 100), 1e-9);
  assert.equal(sharpeParts(v.slice(0, 10)), null); assert.equal(sharpeParts(Array(60).fill(100)), null);
});
t('portfolio value series, cumulative return, weighted risk', () => {
  assert.deepEqual(portfolioValueSeries([[1, 2, 3], [10, 20]], [2, 1]), [2 * 2 + 10, 2 * 3 + 20]);
  assert.deepEqual(cumulativeReturnPct([100, 110, 90]).map((x) => Math.round(x)), [0, 10, -10]);
  const r = weightedRiskScore([{ weight: 1, volPct: 30 }, { weight: 1, volPct: 90 }]);
  near(r.weightedVolPct, 60); assert.equal(r.score, 100); assert.equal(weightedRiskScore([]).score, 0);
});
t('dividend forecast conserves annual income', () => {
  const rows = [{ symbol: 'ITC', value: 100000, yieldPct: 3 }, { symbol: 'TCS', value: 50000, yieldPct: 1.2 }, { symbol: 'XYZ', value: 1000, yieldPct: 0 }];
  const f = dividendForecast(rows, 9);
  assert.equal(f.length, 12); assert.equal(f[0].label, 'Oct'); near(f.reduce((a, m) => a + m.amount, 0), 3000 + 600, 1e-6);
});
t('portfolio diagnostics: concentration, sectors, advice', () => {
  const d = portfolioDiagnostics([{ symbol: 'A', sector: 'IT', value: 80, invested: 70 }, { symbol: 'B', sector: 'IT', value: 10, invested: 10 }, { symbol: 'C', sector: 'FMCG', value: 10, invested: 12 }])!;
  assert.equal(d.concentration, 'High'); near(d.top1Pct, 80); near(d.sectors[0].pct, 90); near(d.hhi, 6600, 1e-6);
  assert.ok(d.advice.some((a) => a.kind === 'trim' && /Trim A/.test(a.title)) && d.diversification < 40);
  const even = portfolioDiagnostics(Array.from({ length: 12 }, (_, i) => ({ symbol: 'S' + i, sector: ['IT', 'Banking', 'FMCG', 'Pharma', 'Auto', 'Energy'][i % 6], value: 100, invested: 100 })))!;
  assert.equal(even.concentration, 'Low'); assert.ok(even.diversification >= 75, String(even.diversification));
  assert.equal(portfolioDiagnostics([]), null);
});

console.log('live feed / SmartAPI');
t('SmartWebSocketV2 packet encode ↔ parse round-trip (snap quote with depth)', () => {
  const tick: SmartTick = {
    mode: 3, exchangeType: 1, token: '2885', seq: 7, exchangeTs: 1_700_000_000_000, ltp: 2501.35, lastQty: 10, avgPrice: 2498.2, volume: 123456, totalBuyQty: 1000, totalSellQty: 900,
    open: 2490, high: 2510, low: 2485.5, close: 2480.1, lastTradeTs: 1_700_000_000_000, oi: 0,
    bids: [1, 2, 3, 4, 5].map((i) => ({ price: 2501 - i * 0.05, qty: 100 * i, orders: i })), asks: [1, 2, 3, 4, 5].map((i) => ({ price: 2501.5 + i * 0.05, qty: 50 * i, orders: i })),
    upperCircuit: 2728, lowerCircuit: 2232, high52: 3000, low52: 2000,
  };
  const back = parseTick(encodeTick(tick))!;
  assert.equal(back.token, '2885'); near(back.ltp, 2501.35); assert.equal(back.volume, 123456); near(back.close!, 2480.1);
  assert.equal(back.bids!.length, 5); assert.equal(back.asks!.length, 5); near(back.bids![0].price, tick.bids![0].price); assert.equal(back.asks![4].qty, 250);
  near(back.upperCircuit!, 2728);
  assert.equal(parseTick(new Uint8Array(10)), null); assert.equal(parseTick(encodeTick({ ...tick, mode: 1 }))!.mode, 1);
  assert.deepEqual(subscribeMessage([{ exchangeType: 1, tokens: ['1'] }]).params, { mode: 3, tokenList: [{ exchangeType: 1, tokens: ['1'] }] });
});
t('TOTP matches the RFC 6238 SHA-1 test vector', async () => {
  // secret "12345678901234567890" in base32; T=59 → 94287082 → last 6 digits 287082
  assert.equal(await totp('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', 59_000), '287082');
});
t('market hours: Mon–Fri 09:15–15:30 IST', () => {
  const ist = (d: string) => Date.parse(d + '+05:30');
  assert.ok(isMarketOpen(ist('2026-10-12T09:15:00')) && isMarketOpen(ist('2026-10-12T15:29:59')));
  assert.ok(!isMarketOpen(ist('2026-10-12T09:14:59')) && !isMarketOpen(ist('2026-10-12T15:30:00')));
  assert.ok(!isMarketOpen(ist('2026-10-10T11:00:00')) && !isMarketOpen(ist('2026-10-11T11:00:00'))); // Sat, Sun
});
t('engine: live ticks drive price, 1-minute candles and real depth; bad ticks ignored', () => {
  const e = new MarketEngine(SEED_INSTRUMENTS); e.setMode('live'); (e as unknown as { selected: string }).selected = 'TCS';
  const t0 = Date.parse('2026-10-12T10:00:10+05:30');
  e.applyTick({ symbol: 'TCS', ltp: 4000, volume: 1000, close: 3950, depth: { bids: [{ price: 3999.95, qty: 10, orders: 1 }], asks: [{ price: 4000.05, qty: 12, orders: 2 }] }, ts: t0 }, t0);
  e.applyTick({ symbol: 'TCS', ltp: 4004, volume: 1500, ts: t0 + 20_000 }, t0 + 20_000);
  e.applyTick({ symbol: 'TCS', ltp: 4001, volume: 1700, ts: t0 + 70_000 }, t0 + 70_000);
  e.applyTick({ symbol: 'TCS', ltp: NaN }, t0); e.applyTick({ symbol: 'NOPE_X', ltp: 5 }, t0); e.applyTick({ symbol: 'TCS', ltp: -3 }, t0);
  const q = e.quotes.get('TCS')!;
  assert.equal(q.ltp, 4001); assert.equal(q.volume, 1700); assert.equal(e.alerts.filter((a) => a.kind === 'VOLUME_SURGE').length, 0); assert.equal(q.prevClose, 3950);
  const bars = (e as unknown as { bars: Map<string, { open: number; high: number; close: number; volume: number }[]> }).bars.get('TCS')!;
  assert.equal(bars.length, 2); assert.equal(bars[0].high, 4004); assert.equal(bars[0].volume, 500); assert.equal(bars[1].volume, 200); // first tick = baseline, not a 1000-share bar
  assert.equal(e.depth.bids[0].price, 3999.95);
});
t('SmartApiFeed: subscribes the diff, applies tick + index messages, ignores junk', () => {
  const sent: string[] = [];
  class FakeWS { onopen?: () => void; onmessage?: (e: { data: string }) => void; onclose?: () => void; onerror?: () => void; constructor(public url: string) { fake = this; } send(m: string) { sent.push(m); } close() { this.onclose?.(); } }
  let fake!: FakeWS;
  const e = new MarketEngine(SEED_INSTRUMENTS); e.setMode('live');
  const f = new SmartApiFeed('wss://x', e, () => {}, FakeWS as unknown as typeof WebSocket);
  f.setSymbols(['TCS']); f.connect(); fake.onopen!();
  f.setSymbols(['TCS', 'INFY']);
  assert.deepEqual(sent.map((m) => JSON.parse(m).symbols), [['TCS'], ['INFY']]);
  fake.onmessage!({ data: JSON.stringify({ t: 'tick', symbol: 'TCS', ltp: 4123.5 }) });
  fake.onmessage!({ data: JSON.stringify({ t: 'index', id: 'NIFTY', value: 25000, prev: 24900 }) });
  fake.onmessage!({ data: 'not json' }); fake.onmessage!({ data: JSON.stringify({ t: 'tick', symbol: 'TCS', ltp: 'x' }) });
  assert.equal(e.quotes.get('TCS')!.ltp, 4123.5); assert.equal(f.ticks, 1);
  const nifty = e.indices.find((i) => i.id === 'NIFTY')!; assert.equal(nifty.value, 25000); near(nifty.pct, (100 / 24900) * 100, 1e-9);
  f.close();
});

console.log('portfolio import (OCR / PDF text)');
t('broker-table text → holdings; unknown symbols reported; duplicates merged', () => {
  const known = new Set(['RELIANCE', 'TCS', 'INFY']);
  const r = parseHoldingsText(['Instrument Qty. Avg. cost LTP', 'RELIANCE 10 2,450.50 2,900', 'TCS 5 3,100.00 3,900', 'TCS 5 3,300.00 3,900', 'ZZZZ 4 10.0 11'].join('\n'), known);
  const tcs = r.holdings.find((h) => h.symbol === 'TCS')!;
  assert.equal(r.holdings.length, 2); assert.equal(tcs.qty, 10); near(tcs.avg, 3200);
  assert.equal(r.holdings.find((h) => h.symbol === 'RELIANCE')!.avg, 2450.5);
});

console.log(`\n${passed} checks passed${process.exitCode ? ' — WITH FAILURES' : ''}`);

/**
 * Angel One SmartAPI → browser relay.
 *
 *   npm run relay
 *
 * Logs in server-side (API key, client code, PIN/password, TOTP secret never reach the browser), opens
 * SmartWebSocketV2, decodes the binary ticks and fans them out as JSON to UpCircuit clients (see SmartApiFeed in lib/market.ts).
 * Needs a long-lived process (Fly.io / Render / a VPS) — NOT Vercel serverless. Put it behind TLS and set
 * NEXT_PUBLIC_FEED_WS_URL=wss://your-relay.example.com in the web app.
 *
 * Env: SMARTAPI_API_KEY, SMARTAPI_CLIENT_CODE, SMARTAPI_PASSWORD, SMARTAPI_TOTP_SECRET, [RELAY_PORT=8787], [RELAY_ALLOWED_ORIGIN=*]
 * UNVERIFIED against a live Angel One account: endpoints/headers follow their public docs — test with your credentials.
 */
import { WebSocket, WebSocketServer } from 'ws';
import { INDEX_TOKENS, Mode, ExchangeType, parseTick, subscribeMessage, totp, type SmartTick } from '../lib/smartapi';

const env = (k: string) => {
  const v = process.env[k];
  if (!v) throw new Error(`Missing env ${k}`);
  return v;
};

const LOGIN_URL = 'https://apiconnect.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword';
const SCRIP_MASTER_URL = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json';
const WS_URL = 'wss://smartapisocket.angelone.in/smart-stream';

async function login() {
  const apiKey = env('SMARTAPI_API_KEY');
  const clientCode = env('SMARTAPI_CLIENT_CODE');
  const res = await fetch(LOGIN_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-UserType': 'USER',
      'X-SourceID': 'WEB',
      'X-ClientLocalIP': '127.0.0.1',
      'X-ClientPublicIP': '127.0.0.1',
      'X-MACAddress': '00:00:00:00:00:00',
      'X-PrivateKey': apiKey,
    },
    body: JSON.stringify({ clientcode: clientCode, password: env('SMARTAPI_PASSWORD'), totp: await totp(env('SMARTAPI_TOTP_SECRET')) }),
  });
  const j = (await res.json()) as { status?: boolean; message?: string; data?: { jwtToken: string; feedToken: string } };
  if (!j.status || !j.data) throw new Error('SmartAPI login failed: ' + (j.message ?? res.status));
  return { apiKey, clientCode, jwt: j.data.jwtToken, feed: j.data.feedToken };
}

/** NSE cash-equity symbol → token, from Angel's scrip master ("RELIANCE-EQ" rows on exch_seg NSE). */
async function loadTokens(): Promise<Map<string, string>> {
  const rows = (await (await fetch(SCRIP_MASTER_URL)).json()) as { token: string; symbol: string; exch_seg: string; name: string }[];
  const m = new Map<string, string>();
  for (const r of rows) if (r.exch_seg === 'NSE' && r.symbol.endsWith('-EQ')) m.set(r.name, r.token);
  return m;
}

async function main() {
  const tokens = await loadTokens();
  const bySymbol = (sym: string) => tokens.get(sym);
  const tokenToSymbol = new Map<string, string>();
  tokens.forEach((tok, sym) => tokenToSymbol.set(tok, sym));
  const indexByToken = new Map(INDEX_TOKENS.map((i) => [i.token, i]));
  console.log(`[relay] scrip master: ${tokens.size} NSE equities`);

  const port = Number(process.env.RELAY_PORT ?? 8787);
  const allowed = process.env.RELAY_ALLOWED_ORIGIN ?? '*';
  const wss = new WebSocketServer({
    port,
    verifyClient: ({ origin }: { origin: string }) => allowed === '*' || origin === allowed,
  });
  const subscribed = new Set<string>(); // tokens already requested upstream
  let upstream: WebSocket | null = null;
  let hbTimer: ReturnType<typeof setInterval> | null = null;

  const broadcast = (msg: unknown) => {
    const s = JSON.stringify(msg);
    wss.clients.forEach((c) => c.readyState === WebSocket.OPEN && c.send(s));
  };

  const subscribeUpstream = (toks: { exchangeType: number; tokens: string[] }[]) => {
    if (upstream?.readyState === WebSocket.OPEN) upstream.send(JSON.stringify(subscribeMessage(toks, Mode.SNAP_QUOTE)));
  };

  const connectUpstream = async () => {
    const s = await login();
    console.log('[relay] logged in as', s.clientCode);
    const ws = new WebSocket(WS_URL, { headers: { Authorization: s.jwt, 'x-api-key': s.apiKey, 'x-client-code': s.clientCode, 'x-feed-token': s.feed } });
    upstream = ws;
    ws.on('open', () => {
      console.log('[relay] SmartWebSocketV2 connected');
      subscribed.clear();
      subscribeUpstream(INDEX_TOKENS.reduce<{ exchangeType: number; tokens: string[] }[]>((a, i) => {
        const g = a.find((x) => x.exchangeType === i.exchangeType);
        g ? g.tokens.push(i.token) : a.push({ exchangeType: i.exchangeType, tokens: [i.token] });
        return a;
      }, []));
      hbTimer = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('ping'), 10_000);
      clientSyms.forEach((syms) => syms.forEach((sym) => ensureSub(sym)));
    });
    ws.on('message', (data: Buffer, isBinary: boolean) => {
      if (!isBinary) return; // 'pong' or JSON error frames
      const t = parseTick(new Uint8Array(data));
      if (t) forward(t);
    });
    const restart = () => {
      if (hbTimer) clearInterval(hbTimer);
      upstream = null;
      setTimeout(() => connectUpstream().catch((e) => (console.error('[relay]', e.message), restart())), 5000);
    };
    ws.on('close', restart);
    ws.on('error', (e) => console.error('[relay] upstream error', e.message));
  };

  const prevClose = new Map<string, number>();
  const forward = (t: SmartTick) => {
    const ix = indexByToken.get(t.token);
    if (ix) {
      const prev = t.close ?? prevClose.get(ix.id);
      if (prev) prevClose.set(ix.id, prev);
      return broadcast({ t: 'index', id: ix.id, value: t.ltp, prev });
    }
    const symbol = tokenToSymbol.get(t.token);
    if (!symbol) return;
    broadcast({
      t: 'tick',
      symbol,
      ltp: t.ltp,
      volume: t.volume,
      lastQty: t.lastQty,
      avgPrice: t.avgPrice,
      open: t.open,
      high: t.high,
      low: t.low,
      close: t.close,
      upperCircuit: t.upperCircuit,
      lowerCircuit: t.lowerCircuit,
      depth: t.bids && t.asks ? { bids: t.bids, asks: t.asks } : undefined,
      ts: t.exchangeTs,
    });
  };

  const ensureSub = (sym: string) => {
    const tok = bySymbol(sym);
    if (!tok || subscribed.has(tok)) return;
    subscribed.add(tok);
    subscribeUpstream([{ exchangeType: ExchangeType.NSE_CM, tokens: [tok] }]);
  };

  const clientSyms = new Map<WebSocket, Set<string>>();
  wss.on('connection', (c: WebSocket) => {
    const set = new Set<string>();
    clientSyms.set(c, set);
    c.on('message', (d: Buffer) => {
      try {
        const m = JSON.parse(d.toString());
        if (m.t === 'sub' && Array.isArray(m.symbols)) {
          for (const sym of m.symbols.slice(0, 200)) if (typeof sym === 'string' && sym.length <= 24) (set.add(sym), ensureSub(sym));
        }
      } catch {
        /* ignore malformed frames */
      }
    });
    c.on('close', () => clientSyms.delete(c));
  });
  setInterval(() => broadcast({ t: 'hb' }), 15_000);

  console.log(`[relay] listening on :${port}`);
  await connectUpstream();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

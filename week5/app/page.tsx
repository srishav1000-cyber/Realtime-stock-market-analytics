'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AskButton, FeedBadge, Navbar, type View } from '@/components/Navbar';
import { AskUpCircuitDrawer, type AskRequest } from '@/components/AskUpCircuitDrawer';
import { PortfolioUploadModal } from '@/components/PortfolioUploadModal';
import { CircuitBanner } from '@/components/CircuitBanner';
import { HomePage } from '@/components/HomePage';
import { ChartWorkspace } from '@/components/ChartWorkspace';
import { OrderModal } from '@/components/OrderModal';
import { StockResearchModal } from '@/components/StockResearchModal';
import { DayTraderDashboard } from '@/components/dashboards/DayTrader';
import { RetailDashboard } from '@/components/dashboards/Retail';
import { InstitutionalDashboard } from '@/components/dashboards/Institutional';
import { ExecutiveDashboard } from '@/components/dashboards/Executive';
import { useMarket } from '@/hooks/useMarket';
import { useInstruments } from '@/hooks/useInstruments';
import { useFavorites } from '@/hooks/useFavorites';
import { useHoldings } from '@/hooks/useHoldings';
import { useHotkeys } from '@/hooks/useHotkeys';
import { useNews } from '@/hooks/useNews';
import { applyToHolding } from '@/lib/analytics';
import { buildAskContext } from '@/lib/ask';
import { basePrice, generateHistory, hashStr, mulberry32, roundTick, topOfBook } from '@/lib/market';
import { personaOf, type Persona } from '@/lib/personas';
import type { Holding, Order, Product, Side, Timeframe } from '@/lib/types';

const DEMO_HOLDINGS: Holding[] = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'SBIN'].map((symbol, i) => ({
  symbol,
  qty: [25, 10, 40, 30, 100, 60][i],
  avg: roundTick(basePrice(symbol) * (0.88 + mulberry32(hashStr(symbol + ':avg'))() * 0.2)),
}));

function Terminal() {
  const instruments = useInstruments();
  const knownSymbols = useMemo(() => new Set(instruments.map((i) => i.symbol)), [instruments]);
  const { favs, toggle: toggleFav } = useFavorites();
  const { holdings, setHoldings, resetHoldings } = useHoldings(DEMO_HOLDINGS);
  const { news, error: newsError } = useNews();

  const [view, setView] = useState<View>('home');
  const [persona, setPersona] = useState<Persona>('day');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [research, setResearch] = useState<string | null>(null);
  const [tf, setTf] = useState<Timeframe>('5m');
  const [qty, setQty] = useState(10);
  const [product, setProduct] = useState<Product>('MIS');
  const [pending, setPending] = useState<Side | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [askOpen, setAskOpen] = useState(false);
  const [askReq, setAskReq] = useState<AskRequest | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const askSeq = useRef(1);

  const searchRef = useRef<HTMLInputElement>(null);
  const orderId = useRef(1);

  const watch = useMemo(() => [...favs, ...holdings.map((h) => h.symbol)], [favs, holdings]);
  const { engine, mode } = useMarket(instruments, symbol, watch);

  const quote = engine.touch(symbol) ?? engine.touch('RELIANCE')!;
  const { bid, ask } = topOfBook(quote.ltp);

  // daily closes for RSI / Sharpe — history shape is fixed per symbol, last bar tracks the live LTP
  const dailyBase = useMemo(() => generateHistory(symbol, '1D', engine.touch(symbol)?.ltp ?? 100, Date.now()).map((c) => c.close), [symbol, engine]);
  const closes1D = useMemo(() => [...dailyBase.slice(0, -1), quote.ltp], [dailyBase, quote.ltp]);

  const flash = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast((t) => (t === msg ? null : t)), 3200);
  }, []);

  const openStock = useCallback((s: string) => {
    setSymbol(s);
    setResearch(s);
  }, []);

  const openOrder = useCallback((side: Side) => {
    setOrderError(null);
    setPending(side);
  }, []);

  const confirmOrder = useCallback(() => {
    if (!pending) return;
    const q = engine.quotes.get(symbol);
    if (!q) return;
    const px = pending === 'BUY' ? topOfBook(q.ltp).ask : topOfBook(q.ltp).bid;

    if (product === 'CNC' && pending === 'SELL') {
      const held = holdings.find((h) => h.symbol === symbol)?.qty ?? 0;
      if (held < qty) {
        setOrderError(`Insufficient holdings: you hold ${held} ${symbol}.`);
        return;
      }
    }
    const order: Order = { id: orderId.current++, time: Date.now(), symbol, side: pending, qty, price: px, product };
    setOrders((o) => [order, ...o].slice(0, 50));
    if (product === 'CNC') setHoldings((h) => applyToHolding(h, order));
    setPending(null);
    flash(`${order.side} ${order.qty} ${order.symbol} @ ₹${px.toFixed(2)} executed`);
  }, [pending, engine, symbol, product, holdings, qty, flash, setHoldings]);

  const openAsk = useCallback((prompt?: string) => {
    setAskOpen(true);
    if (prompt) setAskReq({ id: askSeq.current++, text: prompt });
  }, []);

  /** hotkey C: flatten the net MIS position in the selected symbol from this session's orders */
  const closePosition = useCallback(() => {
    const net = orders.filter((o) => o.symbol === symbol && o.product === 'MIS').reduce((n, o) => n + (o.side === 'BUY' ? o.qty : -o.qty), 0);
    if (net === 0) return flash(`No open MIS position in ${symbol}`);
    const q = engine.quotes.get(symbol);
    if (!q) return;
    const side: Side = net > 0 ? 'SELL' : 'BUY';
    const px = side === 'BUY' ? topOfBook(q.ltp).ask : topOfBook(q.ltp).bid;
    setOrders((o) => [{ id: orderId.current++, time: Date.now(), symbol, side, qty: Math.abs(net), price: px, product: 'MIS' as Product }, ...o].slice(0, 50));
    flash(`Closed ${Math.abs(net)} ${symbol} (${side} @ ₹${px.toFixed(2)})`);
  }, [orders, symbol, engine, flash]);

  const getAskContext = useCallback(() => buildAskContext(engine, holdings, research ?? symbol, mode), [engine, holdings, research, symbol, mode]);

  const importPortfolio = useCallback(
    (h: Holding[]) => {
      setHoldings(h);
      flash(`Portfolio replaced with ${h.length} holding${h.length === 1 ? '' : 's'}`);
      setPersona('retail');
      setView('terminal');
      setImportOpen(false);
    },
    [setHoldings, flash],
  );

  const act = useCallback(
    (key: string) => {
      switch (key) {
        case 'b': return openOrder('BUY');
        case 's': return openOrder('SELL');
        case 'q': return setQty((n) => Math.max(1, Math.round(n * 0.9)));
        case 'w': return setQty((n) => Math.max(n + 1, Math.round(n * 1.1)));
        case '1': return setTf('1m');
        case '2': return setTf('5m');
        case '3': return setTf('1D');
        case 'c': return closePosition();
        case 'f': return toggleFav(symbol);
        case '/': return searchRef.current?.focus();
        case 'Escape': return setPending(null);
      }
    },
    [openOrder, toggleFav, symbol, closePosition],
  );

  useHotkeys({ b: () => act('b'), s: () => act('s'), q: () => act('q'), w: () => act('w'), c: () => act('c'), '1': () => act('1'), '2': () => act('2'), '3': () => act('3'), f: () => act('f'), '/': () => act('/'), Escape: () => act('Escape') }, !askOpen && !importOpen);

  useEffect(() => {
    document.title = `${quote.ltp.toFixed(2)} ${quote.symbol} · UpCircuit`;
  }, [quote.ltp, quote.symbol]);

  const dash = {
    engine,
    quote,
    closes1D,
    holdings,
    favorites: favs,
    orders,
    knownSymbols,
    onSelect: setSymbol,
    mode,
    onToggleFavorite: toggleFav,
    onOpenImport: () => setImportOpen(true),
    onAskAI: openAsk,
    onResetPortfolio: resetHoldings,
    onAction: act,
  };
  const p = personaOf(persona);

  return (
    <div className={`flex min-h-screen flex-col bg-bg ${view === 'terminal' ? 'lg:h-screen' : ''}`}>
      <div className="sticky top-0 z-50 shrink-0">
        <CircuitBanner alerts={engine.alerts} onSelect={openStock} />
        <Navbar
          view={view}
          onView={setView}
          persona={persona}
          onPersona={(x) => {
            setPersona(x);
            setView('terminal');
          }}
          indices={engine.indices}
          instruments={instruments}
          onSelect={openStock}
          onOrder={openOrder}
          searchRef={searchRef}
          mode={mode}
          onOpenImport={() => setImportOpen(true)}
          onAsk={() => openAsk()}
        />
      </div>

      {view === 'home' ? (
        <main className="flex-1">
          <HomePage engine={engine} news={news} newsError={newsError} onOpenStock={openStock} />
        </main>
      ) : (
        <main className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1.45fr)_minmax(400px,1fr)]">
          <section className="min-h-[600px] min-w-0 border-r border-line lg:min-h-0">
            <ChartWorkspace
              quote={quote}
              tf={tf}
              onTf={setTf}
              qty={qty}
              onQty={setQty}
              product={product}
              onProduct={setProduct}
              onOrder={openOrder}
              onResearch={() => setResearch(symbol)}
              favorite={favs.includes(symbol)}
              onToggleFavorite={() => toggleFav(symbol)}
            />
          </section>
          <section className="min-w-0 overflow-y-auto bg-bg p-3" aria-label={`${p.label} dashboard`}>
            <div className="mb-3 flex items-center gap-2">
              <span className="text-lg" aria-hidden>{p.icon}</span>
              <div className="min-w-0 flex-1">
                <h2 className="text-[14px] font-bold leading-tight text-ink">{p.label} dashboard</h2>
                <p className="truncate text-[11px] text-muted">{p.blurb}</p>
              </div>
              <FeedBadge mode={mode} className="hidden sm:inline-flex" />
              <AskButton onClick={() => openAsk()} />
            </div>
            {persona === 'day' && <DayTraderDashboard {...dash} />}
            {persona === 'retail' && <RetailDashboard {...dash} />}
            {persona === 'institutional' && <InstitutionalDashboard {...dash} />}
            {persona === 'executive' && <ExecutiveDashboard {...dash} />}
          </section>
        </main>
      )}

      <footer className="flex shrink-0 items-center gap-3 border-t border-line bg-panel px-3 py-1 text-[10px] text-muted">
        <span>{instruments.length.toLocaleString('en-IN')} instruments indexed</span>
        <span className="ml-auto hidden sm:inline">Prices, depth and ratios are synthetic and for demonstration only. Not investment advice.</span>
      </footer>

      {research && (
        <StockResearchModal
          key={research}
          symbol={research}
          engine={engine}
          favorite={favs.includes(research)}
          onToggleFavorite={() => toggleFav(research)}
          onOrder={openOrder}
          onOpenTerminal={() => {
            setSymbol(research);
            setResearch(null);
            setView('terminal');
          }}
          onClose={() => setResearch(null)}
        />
      )}

      {importOpen && <PortfolioUploadModal instruments={instruments} engine={engine} mode={mode} onImport={importPortfolio} onReset={() => { resetHoldings(); setImportOpen(false); }} onClose={() => setImportOpen(false)} />}

      <AskUpCircuitDrawer open={askOpen} onClose={() => setAskOpen(false)} getContext={getAskContext} request={askReq} focusSymbol={research ?? (view === 'terminal' ? symbol : null)} hasPortfolio={holdings.length > 0} />

      {pending && <OrderModal side={pending} symbol={symbol} qty={qty} price={pending === 'BUY' ? ask : bid} product={product} error={orderError} onConfirm={confirmOrder} onCancel={() => setPending(null)} />}

      {toast && (
        <div role="status" className="fixed right-4 top-[130px] z-[90] rounded-md border border-line bg-panel px-4 py-2 text-[13px] text-ink shadow-2xl">
          {toast}
        </div>
      )}
    </div>
  );
}

/** The engine uses Date/Math.random, so render the terminal client-side only to avoid hydration mismatches. */
export default function Page() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) {
    return (
      <div className="flex h-screen items-center justify-center bg-bg text-[13px] text-muted">
        <span className="animate-pulse">Starting UpCircuit…</span>
      </div>
    );
  }
  return <Terminal />;
}

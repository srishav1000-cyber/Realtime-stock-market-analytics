'use client';

import type { Product, Quote, Side, Timeframe } from '@/lib/types';
import { topOfBook } from '@/lib/market';
import { estimateCharges, marginRequired } from '@/lib/analytics';
import { fmt, fmtInt, fmtPct, fmtSigned, tone } from '@/lib/format';
import { PriceChart } from './PriceChart';
import { Badge } from './ui';

interface Props {
  quote: Quote;
  tf: Timeframe;
  onTf: (tf: Timeframe) => void;
  qty: number;
  onQty: (q: number) => void;
  product: Product;
  onProduct: (p: Product) => void;
  onOrder: (side: Side) => void;
  onResearch: () => void;
  favorite: boolean;
  onToggleFavorite: () => void;
}

export function ChartWorkspace({ quote, tf, onTf, qty, onQty, product, onProduct, onOrder, onResearch, favorite, onToggleFavorite }: Props) {
  const { bid, ask } = topOfBook(quote.ltp);
  const chg = quote.ltp - quote.prevClose;
  const pct = (chg / quote.prevClose) * 100;
  const buyVal = ask * qty;
  const sellVal = bid * qty;
  const stepQty = (d: number) => onQty(Math.max(1, qty + d));

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* symbol strip */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-panel px-3 py-2">
        <button onClick={onToggleFavorite} aria-label={favorite ? 'Remove from favourites' : 'Add to favourites'} className={`text-lg leading-none ${favorite ? 'text-warn' : 'text-muted hover:text-ink'}`}>
          {favorite ? '★' : '☆'}
        </button>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-bold text-ink">{quote.symbol}</span>
            <Badge>NSE · EQ</Badge>
            <button onClick={onResearch} className="rounded border border-line px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent hover:bg-accent/10">
              Research ↗
            </button>
          </div>
          <div className="truncate text-[11px] text-muted">{quote.name}</div>
        </div>
        <div className="num flex items-baseline gap-2">
          <span className={`text-2xl font-semibold ${tone(chg)}`}>{fmt(quote.ltp)}</span>
          <span className={`text-[13px] ${tone(chg)}`}>
            {fmtSigned(chg)} ({fmtPct(pct)})
          </span>
        </div>
        <div className="num ml-auto hidden gap-4 text-[11px] text-muted lg:flex">
          <span>O <b className="text-ink">{fmt(quote.open)}</b></span>
          <span>H <b className="text-ink">{fmt(quote.high)}</b></span>
          <span>L <b className="text-ink">{fmt(quote.low)}</b></span>
          <span>PC <b className="text-ink">{fmt(quote.prevClose)}</b></span>
          <span>Vol <b className="text-ink">{fmtInt(quote.volume)}</b></span>
          <span title="Lower / upper circuit">Band <b className="text-ink">{fmt(quote.lowerCircuit)}–{fmt(quote.upperCircuit)}</b></span>
        </div>
      </div>

      <PriceChart symbol={quote.symbol} ltp={quote.ltp} volume={quote.volume} tf={tf} onTf={onTf} className="min-h-[300px] flex-1" />

      {/* order bar */}
      <div className="flex flex-wrap items-center gap-3 border-t border-line bg-panel px-3 py-2.5">
        <div className="flex items-center">
          <span className="mr-2 text-[10px] font-semibold uppercase tracking-wider text-muted">Qty</span>
          <button onClick={() => stepQty(-1)} className="h-7 w-7 rounded-l border border-line bg-bg text-ink hover:bg-line" aria-label="Decrease quantity">−</button>
          <input
            value={qty}
            inputMode="numeric"
            onChange={(e) => {
              const n = parseInt(e.target.value.replace(/\D/g, ''), 10);
              onQty(Number.isFinite(n) && n > 0 ? Math.min(n, 1_000_000) : 1);
            }}
            className="num h-7 w-16 border-y border-line bg-bg text-center text-[13px] text-ink outline-none focus:border-accent"
            aria-label="Quantity"
          />
          <button onClick={() => stepQty(1)} className="h-7 w-7 rounded-r border border-line bg-bg text-ink hover:bg-line" aria-label="Increase quantity">+</button>
        </div>

        <div className="flex overflow-hidden rounded border border-line text-[11px] font-semibold">
          {(['MIS', 'CNC'] as Product[]).map((p) => (
            <button key={p} onClick={() => onProduct(p)} aria-pressed={product === p} className={`px-2.5 py-1.5 ${product === p ? 'bg-accent text-white' : 'bg-bg text-muted hover:text-ink'}`} title={p === 'MIS' ? 'Intraday (5× leverage)' : 'Delivery'}>
              {p === 'MIS' ? 'Intraday' : 'Delivery'}
            </button>
          ))}
        </div>

        <div className="num hidden text-[11px] text-muted md:block">
          Margin <b className="text-ink">₹{fmt(marginRequired(buyVal, product))}</b> · Charges ≈ <b className="text-ink">₹{fmt(estimateCharges(buyVal, 'BUY', product))}</b>
        </div>

        <div className="ml-auto flex gap-2">
          <button onClick={() => onOrder('SELL')} className="rounded bg-down px-4 py-2 text-left transition hover:brightness-110 active:scale-[0.98]">
            <div className="text-[12px] font-bold leading-none text-white">Sell @ Market</div>
            <div className="num mt-1 text-[11px] leading-none text-white/85">₹{fmt(bid)} · ₹{fmt(sellVal)}</div>
          </button>
          <button onClick={() => onOrder('BUY')} className="rounded bg-up px-4 py-2 text-left transition hover:brightness-110 active:scale-[0.98]">
            <div className="text-[12px] font-bold leading-none text-white">Buy @ Market</div>
            <div className="num mt-1 text-[11px] leading-none text-white/85">₹{fmt(ask)} · ₹{fmt(buyVal)}</div>
          </button>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useEffect } from 'react';
import type { Product, Side } from '@/lib/types';
import { estimateCharges, marginRequired } from '@/lib/analytics';
import { fmt, fmtInt } from '@/lib/format';

interface Props {
  side: Side;
  symbol: string;
  qty: number;
  price: number; // market-order estimate: ask for BUY, bid for SELL
  product: Product;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export function OrderModal({ side, symbol, qty, price, product, error, onConfirm, onCancel }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' && e.key !== 'Enter') return;
      // stop the keypress from also "clicking" whichever button had focus (it would reopen this modal)
      e.preventDefault();
      e.stopPropagation();
      if (e.key === 'Escape') onCancel();
      else onConfirm();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [onCancel, onConfirm]);

  const value = price * qty;
  const charges = estimateCharges(value, side, product);
  const buy = side === 'BUY';
  const row = (k: string, v: string, strong = false) => (
    <div className="flex justify-between py-1.5 text-[13px]">
      <span className="text-muted">{k}</span>
      <span className={`num ${strong ? 'font-semibold text-ink' : 'text-ink'}`}>{v}</span>
    </div>
  );

  return (
    <div data-order-modal className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4" onMouseDown={onCancel} role="dialog" aria-modal="true" aria-label={`${side} ${symbol}`}>
      <div className="w-full max-w-sm overflow-hidden rounded-lg border border-line bg-panel shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div className={`flex items-center justify-between px-4 py-3 ${buy ? 'bg-up' : 'bg-down'}`}>
          <div className="text-[14px] font-bold text-white">
            {side} {symbol}
          </div>
          <div className="text-[11px] font-semibold text-white/90">NSE · {product === 'MIS' ? 'Intraday' : 'Delivery'} · Market</div>
        </div>
        <div className="divide-y divide-line px-4 py-2">
          {row('Quantity', fmtInt(qty), true)}
          {row(buy ? 'Est. fill (ask)' : 'Est. fill (bid)', '₹' + fmt(price), true)}
          {row('Order value', '₹' + fmt(value))}
          {row('Margin required', '₹' + fmt(marginRequired(value, product)))}
          {row('Est. charges', '₹' + fmt(charges))}
        </div>
        {error && <div className="mx-4 mb-2 rounded border border-down/40 bg-down/10 px-3 py-2 text-[12px] text-down">{error}</div>}
        <div className="px-4 pb-1 text-[11px] text-muted">Paper trade on a simulated feed. Market orders fill at the current best {buy ? 'ask' : 'bid'}.</div>
        <div className="flex gap-2 p-4">
          <button onClick={onCancel} className="flex-1 rounded border border-line py-2 text-[13px] font-semibold text-ink hover:bg-line">
            Cancel <kbd>Esc</kbd>
          </button>
          <button onClick={onConfirm} className={`flex-1 rounded py-2 text-[13px] font-bold text-white hover:brightness-110 ${buy ? 'bg-up' : 'bg-down'}`}>
            Confirm {side} <kbd className="!border-white/30 !bg-white/15 !text-white">↵</kbd>
          </button>
        </div>
      </div>
    </div>
  );
}

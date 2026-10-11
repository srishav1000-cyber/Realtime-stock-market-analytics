import type { IndexQuote } from '@/lib/types';
import { fmt, fmtPct, fmtSigned, tone } from '@/lib/format';

export function IndexCard({ ix }: { ix: IndexQuote }) {
  const dir = ix.pct > 0 ? '▲' : ix.pct < 0 ? '▼' : '■';
  return (
    <div className="flex min-w-[148px] shrink-0 flex-col justify-center border-r border-line px-3 py-1 last:border-r-0">
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">{ix.label}</span>
        <span className={`text-[8px] ${tone(ix.pct)}`}>{dir}</span>
      </div>
      <div className="num flex items-baseline gap-2">
        <span className="text-[13px] font-semibold text-ink">{fmt(ix.value)}</span>
        <span className={`text-[11px] ${tone(ix.pct)}`}>
          {fmtSigned(ix.change)} ({fmtPct(ix.pct)})
        </span>
      </div>
    </div>
  );
}

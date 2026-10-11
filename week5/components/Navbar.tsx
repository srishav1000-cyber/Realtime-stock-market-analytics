'use client';

import { useCallback, useRef, useState, type RefObject } from 'react';
import type { IndexQuote, Instrument, Side } from '@/lib/types';
import { FEED_BADGE, type FeedMode } from '@/lib/market';
import { PERSONAS, personaOf, type Persona } from '@/lib/personas';
import { useDismiss } from '@/hooks/useClickOutside';
import { IndexCard } from './IndexCard';
import { SearchBox } from './SearchBox';
import { ThemeToggle } from './ThemeToggle';

export type View = 'home' | 'terminal';

interface Props {
  view: View;
  onView: (v: View) => void;
  persona: Persona;
  onPersona: (p: Persona) => void;
  indices: IndexQuote[];
  instruments: Instrument[];
  /** a stock was chosen from universal search → open research */
  onSelect: (symbol: string) => void;
  onOrder: (side: Side) => void;
  searchRef: RefObject<HTMLInputElement>;
  /** feed status badge: LIVE MARKET / OFF-MARKET REPLAY / SIMULATED */
  mode: FeedMode;
  /** opens the CSV / image / PDF import modal */
  onOpenImport: () => void;
  /** opens the Ask UpCircuit drawer */
  onAsk: () => void;
}

export function FeedBadge({ mode, className = '' }: { mode: FeedMode; className?: string }) {
  const b = FEED_BADGE[mode];
  const cls = b.tone === 'down' ? 'bg-down/15 text-down' : b.tone === 'warn' ? 'bg-warn/15 text-warn' : 'bg-accent/15 text-accent';
  return (
    <span role="status" title={b.title} data-testid="feed-badge" data-mode={mode} className={`inline-flex shrink-0 items-center whitespace-nowrap rounded px-2 py-1 text-[10px] font-bold tracking-wide ${cls} ${mode === 'live' ? 'animate-pulse' : ''} ${className}`}>
      {b.text}
    </span>
  );
}

function UploadButton({ onClick, className = '' }: { onClick: () => void; className?: string }) {
  return (
    <button onClick={onClick} title="Import portfolio (CSV, image or PDF)" aria-label="Import portfolio" className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-line text-muted hover:bg-line hover:text-ink ${className}`}>
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
      </svg>
    </button>
  );
}

export function AskButton({ onClick, className = '' }: { onClick: () => void; className?: string }) {
  return (
    <button onClick={onClick} data-testid="ask-trigger" title="Ask UpCircuit AI about the market or your portfolio" aria-label="Ask UpCircuit AI" className={`flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md bg-gradient-to-r from-accent to-[#7B61FF] px-2.5 text-[12px] font-bold text-white shadow-sm shadow-accent/30 ring-1 ring-white/10 transition hover:brightness-110 active:scale-95 sm:px-3 ${className}`}>
      <span aria-hidden>✨</span>
      <span className="sm:hidden">Ask</span>
      <span className="hidden sm:inline">Ask UpCircuit</span>
    </button>
  );
}

function Logo() {
  return (
    <div className="flex items-center gap-2 pr-1">
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="7" fill="rgb(var(--c-accent))" />
        <path d="M8 21a8 8 0 1 1 16 0" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" />
        <path d="M10 22l4-5 3 3 5-7" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="hidden text-[15px] font-bold tracking-tight text-ink sm:inline">
        Up<span className="text-accent">Circuit</span>
      </span>
    </div>
  );
}

function PersonaSwitcher({ persona, onPersona }: { persona: Persona; onPersona: (p: Persona) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(ref, open, close);
  const cur = personaOf(persona);

  return (
    <div ref={ref} className="sm:relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Persona: ${cur.label}`}
        className="flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-line bg-bg px-2.5 text-[12px] font-semibold text-ink hover:border-accent"
      >
        <span aria-hidden>{cur.icon}</span>
        <span className="hidden lg:inline">{cur.label}</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden><path d="m6 9 6 6 6-6" /></svg>
      </button>
      {open && (
        <ul role="listbox" aria-label="Persona" className="absolute inset-x-3 top-[52px] z-50 overflow-hidden rounded-md border border-line bg-panel py-1 shadow-2xl shadow-black/40 sm:inset-x-auto sm:right-0 sm:top-full sm:mt-1 sm:w-72">
          {PERSONAS.map((p) => (
            <li key={p.id} role="option" aria-selected={p.id === persona}>
              <button
                onClick={() => {
                  onPersona(p.id);
                  setOpen(false);
                }}
                className={`flex w-full items-start gap-2.5 px-3 py-2 text-left hover:bg-line ${p.id === persona ? 'bg-accent/10' : ''}`}
              >
                <span className="mt-0.5 text-[15px]" aria-hidden>{p.icon}</span>
                <span>
                  <span className="block text-[13px] font-semibold text-ink">{p.label}</span>
                  <span className="block text-[11px] text-muted">{p.blurb}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AvatarMenu({ mode }: { mode: FeedMode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(ref, open, close);
  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open} aria-label="Account menu" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[12px] font-bold text-accent ring-1 ring-accent/50 hover:bg-accent/30">
        DT
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-50 mt-2 w-52 rounded-md border border-line bg-panel py-1 text-[13px] shadow-2xl shadow-black/40">
          <div className="border-b border-line px-3 py-2">
            <div className="font-semibold text-ink">Demo Trader</div>
            <div className="text-[11px] text-muted">Paper account · {mode === 'live' ? 'Live feed' : 'Simulated feed'}</div>
          </div>
          {['Profile', 'Funds & margin', 'Order book', 'Settings'].map((x) => (
            <button key={x} role="menuitem" className="block w-full px-3 py-1.5 text-left text-ink hover:bg-line" onClick={close}>{x}</button>
          ))}
          <button role="menuitem" className="block w-full border-t border-line px-3 py-1.5 text-left text-down hover:bg-line" onClick={close}>Log out</button>
        </div>
      )}
    </div>
  );
}

export function Navbar({ view, onView, persona, onPersona, indices, instruments, onSelect, onOrder, searchRef, mode, onOpenImport, onAsk }: Props) {
  return (
    <header className="relative">
      <div className="flex h-[52px] items-center gap-2 border-b border-line bg-panel px-3 md:gap-3">
        <Logo />

        <nav className="flex shrink-0 items-center gap-0.5" aria-label="Primary">
          {(['home', 'terminal'] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => onView(v)}
              aria-current={view === v ? 'page' : undefined}
              className={`rounded px-2 py-1.5 text-[12px] font-semibold sm:px-2.5 sm:text-[13px] ${view === v ? 'bg-accent/15 text-accent' : 'text-muted hover:text-ink'}`}
            >
              {v === 'home' ? 'Discover' : 'Terminal'}
            </button>
          ))}
        </nav>

        <div className="hidden min-w-0 flex-1 justify-center md:flex">
          <SearchBox instruments={instruments} onSelect={onSelect} inputRef={searchRef} />
        </div>
        <div className="flex-1 md:hidden" />

        <PersonaSwitcher persona={persona} onPersona={onPersona} />
        <UploadButton onClick={onOpenImport} className="hidden md:flex" />
        <AskButton onClick={onAsk} />
        <ThemeToggle />
        <div className="hidden items-center gap-2 lg:flex">
          <button onClick={() => onOrder('BUY')} className="rounded bg-up px-3.5 py-1.5 text-[12px] font-bold text-white transition hover:brightness-110 active:scale-95">BUY</button>
          <button onClick={() => onOrder('SELL')} className="rounded bg-down px-3.5 py-1.5 text-[12px] font-bold text-white transition hover:brightness-110 active:scale-95">SELL</button>
        </div>
        <div className="hidden sm:block">
          <AvatarMenu mode={mode} />
        </div>
      </div>

      {/* mobile search + import */}
      <div className="flex items-center gap-2 border-b border-line bg-panel px-3 py-1.5 md:hidden">
        <div className="min-w-0 flex-1">
          <SearchBox instruments={instruments} onSelect={onSelect} inputRef={searchRef} />
        </div>
        <UploadButton onClick={onOpenImport} />
      </div>

      {/* feed status + index ticker */}
      <div className="flex items-stretch border-b border-line bg-panel" aria-label="Market indices">
        <div className="flex shrink-0 items-center border-r border-line px-2">
          <FeedBadge mode={mode} />
        </div>
        <div className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
          {indices.map((ix) => (
            <IndexCard key={ix.id} ix={ix} />
          ))}
        </div>
      </div>
    </header>
  );
}

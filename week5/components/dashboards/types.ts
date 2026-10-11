import type { FeedMode, MarketEngine } from '@/lib/market';
import type { Holding, Order, Quote } from '@/lib/types';

export interface DashboardProps {
  engine: MarketEngine;
  quote: Quote;
  /** daily closes for the selected symbol (last bar = live LTP) */
  closes1D: number[];
  holdings: Holding[];
  favorites: string[];
  orders: Order[];
  knownSymbols: ReadonlySet<string>;
  mode: FeedMode;
  onSelect: (symbol: string) => void;
  onToggleFavorite: (symbol: string) => void;
  /** opens the CSV / image / PDF import modal */
  onOpenImport: () => void;
  onAskAI: (prompt?: string) => void;
  onResetPortfolio: () => void;
  /** dispatches a terminal action from the hotkey panel */
  onAction: (key: string) => void;
}

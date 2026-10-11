import seed from '@/data/seed-instruments.json';
import type { Instrument } from './types';

/** Built-in seed (~250 liquid names). The full NSE master is merged in at runtime from /data/instruments.json. */
export const SEED_INSTRUMENTS: Instrument[] = (seed as [string, string, string][]).map(([symbol, name, sector]) => ({
  symbol,
  name,
  sector,
}));

export const SEED_SECTORS = new Map(SEED_INSTRUMENTS.map((i) => [i.symbol, i.sector]));

/** Fetch the full NSE equity master produced by `npm run sync:instruments`. Falls back to the seed. */
export async function loadInstrumentMaster(signal?: AbortSignal): Promise<Instrument[]> {
  try {
    const res = await fetch('/data/instruments.json', { signal, cache: 'force-cache' });
    if (!res.ok) return SEED_INSTRUMENTS;
    const rows = (await res.json()) as Instrument[];
    if (!Array.isArray(rows) || rows.length < SEED_INSTRUMENTS.length) return SEED_INSTRUMENTS;
    return rows;
  } catch {
    return SEED_INSTRUMENTS;
  }
}

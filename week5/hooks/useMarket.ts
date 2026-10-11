'use client';

import { useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { MarketEngine, SmartApiFeed, isMarketOpen, type FeedConn, type FeedMode } from '@/lib/market';
import type { Instrument } from '@/lib/types';

/** WebSocket URL of the SmartAPI relay (scripts/angel-relay.ts), e.g. wss://relay.example.com. Unset → no live feed. */
const FEED_URL = process.env.NEXT_PUBLIC_FEED_WS_URL;

/**
 * Owns the market engine. Steps every 250 ms, re-renders every 500 ms.
 * Feed mode is re-evaluated every second:
 *   market open  + relay connected → 'live'      (ticks drive prices)
 *   market open  + no relay        → 'simulated'
 *   market closed                  → 'replay'
 */
export function useMarket(universe: Instrument[], selected: string, watch: string[]) {
  const engine = useMemo(() => new MarketEngine(universe), [universe]);
  const [version, bump] = useReducer((x: number) => x + 1, 0);
  const [conn, setConn] = useState<FeedConn>('idle');
  const [mode, setMode] = useState<FeedMode>('replay');
  const selRef = useRef(selected);
  selRef.current = selected;
  const feedRef = useRef<SmartApiFeed | null>(null);

  // keep favourites / holdings simulated even if they aren't in the seed
  const watchKey = watch.join(',');
  useEffect(() => {
    watch.forEach((s) => engine.touch(s));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, watchKey]);

  // live feed connection
  useEffect(() => {
    if (!FEED_URL) return;
    const feed = new SmartApiFeed(FEED_URL, engine, setConn);
    feedRef.current = feed;
    feed.connect();
    return () => {
      feed.close();
      feedRef.current = null;
    };
  }, [engine]);

  // subscribe to what the UI shows: the selected symbol, watchlist, holdings and the whole simulated universe's top names
  useEffect(() => {
    feedRef.current?.setSymbols([selected, ...watch, ...Array.from(engine.quotes.keys()).slice(0, 80)]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engine, selected, watchKey, conn]);

  useEffect(() => {
    let i = 0;
    let lastMode: FeedMode | null = null;
    const evalMode = () => {
      const now = Date.now();
      const open = isMarketOpen(now);
      const streaming = feedRef.current?.status === 'open' && now - (feedRef.current?.lastMessageAt ?? 0) < 45_000;
      const m: FeedMode = !open ? 'replay' : streaming ? 'live' : 'simulated';
      if (m !== lastMode) {
        lastMode = m;
        engine.setMode(m);
        setMode(m);
      }
    };
    evalMode();
    const id = setInterval(() => {
      if (i % 4 === 0) evalMode();
      engine.step(selRef.current, Date.now());
      if (++i % 2 === 0) bump();
    }, 250);
    bump();
    return () => clearInterval(id);
  }, [engine]);

  return { engine, version, mode, conn };
}

'use client';

import { useCallback, useEffect, useState } from 'react';

const KEY = 'upcircuit:favorites';
const DEFAULT = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'SBIN'];

export function useFavorites() {
  const [favs, setFavs] = useState<string[]>(DEFAULT);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setFavs(parsed.filter((x): x is string => typeof x === 'string'));
      }
    } catch {
      /* storage unavailable — keep defaults */
    }
  }, []);

  const toggle = useCallback((symbol: string) => {
    setFavs((cur) => {
      const next = cur.includes(symbol) ? cur.filter((s) => s !== symbol) : [...cur, symbol];
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  return { favs, toggle };
}
